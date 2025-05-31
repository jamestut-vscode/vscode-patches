#!/usr/bin/env python3
import sys
import os
import argparse
import subprocess
import shutil
import multiprocessing
import threading
import itertools
import json
from pathlib import Path
from contextlib import contextmanager

# constants
# mainline VSCode release channel
REL_REH_CHANNEL = 'stable'
# location of base (primary target) of the VSCode REH relative to repo dir
BASE_REH_PATH = "work/vscode-reh-darwin-arm64"
# location of VSCode repo path
BASE_VSCODE_PATH = "work/vscode"
# Linux container (e.g. for GNU binutils for stripping binaries)
CONT_NAME = "binutils:latest"
# location of podman Containerfile to build the container (relative to repo dir)
CONT_BLD_FILE = "scripts/containerfiles/binutils.containerfile"
# base work directory for REH derivation
BASE_DR_WORKDIR = "work/derivedreh"
# final output packaging dir
BASE_PACKAGING_DIR = "work/packaging"
# these binaries are not required to be present on Linux REHs
EXCLUDE_BINS = {'node_modules/node-pty/build/Release/spawn-helper'}
# strip ELF binaries (can be modified via command-line args)
STRIP = False
# commit hash to base for VSDA
VSDA_BASE_COMMIT = 'ddc367ed5c8936efe395cffeec279b04ffd7db78'

# dynamic constants
# for declaring dynamic constants
def dynconst(fn): return fn()

# base directory of the repository
@dynconst
def REPODIR() -> Path:
    cwd = Path(__file__).parent
    repodir = subprocess.check_output(['git', 'rev-parse', '--show-toplevel'], cwd=cwd)
    return Path(repodir.decode('utf8').rstrip())

# commit hash of our base VSCode repo
@dynconst
def BASE_COMMIT() -> str:
    rs = subprocess.check_output(['scripts/get-base-commit.sh'], cwd=REPODIR)
    return rs.rstrip().decode('ascii')

@dynconst
def REH_NODE_VERSION():
    npmrc_path = REPODIR/BASE_VSCODE_PATH/"remote/.npmrc"
    target, runtime = None, None
    with open(npmrc_path) as f:
        for l in f:
            k, v = l.split("=", maxsplit=1)
            if k == "target":
                target = eval(v)
            elif k == "runtime":
                runtime = eval(v)
    if runtime != "node":
        raise ValueError("Expected 'node' runtime for REH")
    if target is None:
        raise ValueError("Unknown node.js version for REH")
    return target

# lazy dynamic constants (only evaluated on first call)
def lazydynconst(fn):
    cached = None
    def wrapper():
        nonlocal cached
        if cached is None:
            cached = fn()
        return cached
    return wrapper

@lazydynconst
def REH_OBJ_LIST() -> list[Path]:
    return [fn for fn in find_macho(REPODIR/BASE_REH_PATH) if str(fn) not in EXCLUDE_BINS]

@lazydynconst
def VSDA_OBJ_SET() -> set[Path]:
    vsda_base_path = Path("node_modules/vsda")
    return {i for i in REH_OBJ_LIST() if i.is_relative_to(vsda_base_path)}

@lazydynconst
def VSCODE_PRODUCT_INFO() -> dict:
    with open(REPODIR/BASE_VSCODE_PATH/"product.json") as f:
        return json.load(f)

@lazydynconst
def SERVER_APP_NAME() -> str:
    return VSCODE_PRODUCT_INFO()['serverApplicationName']

# helper functions
def topath(p: str | Path) -> Path:
    return Path(p) if type(p) is not Path else p

def clonefile(src: str | Path, tgt: str | Path):
    '''
    Use macOS' "cp -c" to use clonefile for efficient copy
    '''
    tgt = topath(tgt)
    if tgt.exists(): return
    subprocess.check_output(["cp", "-c", "-R", src, tgt])

def replace_file(basefrom: str | Path, baseto: str | Path, fn: str | Path):
    basefrom, baseto = topath(basefrom), topath(baseto)
    os.unlink(baseto/fn)
    clonefile(basefrom/fn, baseto/fn)

def rimraf(target: str | Path):
    subprocess.check_output(["rm", "-rf", target])

def make_executable(target: str | Path):
    subprocess.check_output(["chmod", "+x", target])

def find_macho(basedir: str | Path):
    macho_magics = {
        b'\xCF\xFA\xED\xFE', # 64-bit LE
        b'\xCE\xFA\xED\xFE', # 32-bit LE
        b'\xFE\xED\xFA\xCF', # 64-bit BE
        b'\xFE\xED\xFA\xCE', # 32-bit BE
        b'\xCA\xFE\xBA\xBE', # universal/fat binary
    }
    if type(basedir) is not Path:
        basedir = Path(basedir)
    for dirpath, _, files in os.walk(basedir):
        for file in files:
            fn = Path(dirpath)/file
            with open(fn, 'rb') as f:
                magic_bytes = f.read(4)
            if magic_bytes in macho_magics:
                yield fn.relative_to(basedir)

def strip_elf_binaries(basedir: str | Path, files: list[str | Path]):
    '''
    Strip ELF binaries as specified in macho list using podman
    '''
    # check if the container exists
    if not STRIP:
        return
    basedir = topath(basedir).absolute()
    cont_basedir = Path('/target')
    try:
        subprocess.check_output(['podman', 'image', 'inspect', CONT_NAME], stderr=subprocess.DEVNULL)
    except subprocess.CalledProcessError:
        # build the container
        subprocess.check_call(['podman', 'build', '--tag', CONT_NAME, '--file', REPODIR/CONT_BLD_FILE])
        pass
    podman_args = ['podman', 'run', '--rm', '-v', f'{basedir}:{cont_basedir}', CONT_NAME, 'strip']
    files = [topath(p) for p in files]
    assert all(not p.is_absolute() for p in files)
    podman_args.extend(cont_basedir/fn for fn in files)
    subprocess.check_call(podman_args)

'''
List of classes to handle various REH targets. These classes must have these members:
- downloads: list of (url, target file)
- deps: list of dependencies to other targets
- output_name: name of the output REH
- run(workdir: Path, *args): *args = workdir of dependencies (order by deps)
'''
class LinuxGeneric:
    def __init__(self, target: str):
        _, kind, arch = target.split("-")
        if kind == 'gnu':
            out_name_suff = f"linux-{arch}"
        elif kind == 'alpine':
            out_name_suff = {'x64': 'linux-alpine', 'arm64': 'alpine-arm64'}[arch]
        else:
            raise NotImplementedError()
        self.extract_name = f"vscode-server-{out_name_suff}"
        self.tarball_name = f"server-{out_name_suff}.tarball"
        self.tarball_name_vsda = f"server-{out_name_suff}-vsda.tarball"

        self.output_name = f"vscode-reh-{out_name_suff}"
        self.deps = []
        self.downloads = [
            (f"https://update.code.visualstudio.com/commit:{BASE_COMMIT}/server-{out_name_suff}/{REL_REH_CHANNEL}", self.tarball_name),
            (f"https://update.code.visualstudio.com/commit:{VSDA_BASE_COMMIT}/server-{out_name_suff}/{REL_REH_CHANNEL}", self.tarball_name_vsda),
        ]

    def run(self, workdir: Path, *_):
        target_extract_dir = workdir/self.extract_name
        if not target_extract_dir.exists():
            print("  Extracting ...")
            subprocess.check_call(["tar", "-xf", self.tarball_name], cwd=workdir)
            print("  Stripping ELF binaries ...")
            strip_elf_binaries(target_extract_dir, REH_OBJ_LIST())
        vsda_work_dir = workdir/"reh-vsda"
        target_vsda_extract_dir = vsda_work_dir/self.extract_name
        if not target_vsda_extract_dir.exists():
            os.makedirs(vsda_work_dir, exist_ok=True)
            print("  Extracting REH for VSDA ...")
            subprocess.check_call(["tar", "-xf",
                workdir.relative_to(vsda_work_dir, walk_up=True)/self.tarball_name_vsda], cwd=vsda_work_dir)
            print("  Stripping VSDA ELF binaries ...")
            strip_elf_binaries(target_vsda_extract_dir, VSDA_OBJ_SET())
        print("  Processing ...")
        target_dir = workdir/self.output_name
        clonefile(REPODIR/BASE_REH_PATH, target_dir)
        # replace the `code-server-oss` script with the Linux version
        server_bootstrap_script_path = target_dir/"bin"/SERVER_APP_NAME()
        os.unlink(server_bootstrap_script_path)
        clonefile(REPODIR/BASE_VSCODE_PATH/"resources/server/bin/code-server-linux.sh",
            server_bootstrap_script_path)
        make_executable(server_bootstrap_script_path)
        # remove uneeded binaries
        for exclbin in EXCLUDE_BINS:
            os.unlink(target_dir/exclbin)
        for objfile in REH_OBJ_LIST():
            replace_file(
                target_vsda_extract_dir if objfile in VSDA_OBJ_SET() else target_extract_dir,
                target_dir, objfile)

class LinuxPortable:
    def __init__(self, target: str):
        _, kind, self.arch = target.split("-")
        assert kind == 'portable'
        # alternative architecture name, commonly used in `uname -m`
        self.linux_arch_name = {'arm64': 'aarch64', 'x64': 'x86_64'}[self.arch]

        self.cont_name = 'vscode-portable-libs-' + self.arch

        out_name_suff = f'linux-{kind}-{self.arch}'
        self.output_name = f"vscode-reh-{out_name_suff}"

        dep = f'linux-alpine-{self.arch}'
        self.deps = [dep]

        # obtain dependency's output name
        self.dep_output_name = LinuxGeneric(dep).output_name

        patchelf_url = f'https://github.com/NixOS/patchelf/releases/download/0.18.0/patchelf-0.18.0-{self.linux_arch_name}.tar.gz'
        self.patchelf_archive = patchelf_url.rsplit('/', maxsplit=1)[-1]
        self.downloads = [(patchelf_url, self.patchelf_archive)]

    def _get_container_state(self):
        contstat = subprocess.check_output(['podman', 'container', 'inspect', self.cont_name], stderr=subprocess.DEVNULL)
        return json.loads(contstat)

    @contextmanager
    def _start_container(self):
        # check if it is already started
        try:
            contstat = self._get_container_state()
        except subprocess.CalledProcessError:
            # container does not exist
            self._maybe_create_container()
            contstat = self._get_container_state()

        if contstat[0]['State']['Status'] != 'running':
            subprocess.check_output(['podman', 'start', self.cont_name])
        try:
            yield
        finally:
            # stop the container afterwards
            subprocess.check_output(['podman', 'stop', self.cont_name])

    def _maybe_create_container(self):
        podman_platform = None
        if self.arch == 'arm64':
            # use the default platform
            pass
        elif self.arch == 'x64':
            podman_platform = 'linux/amd64'
        else:
            raise RuntimeError(f"Platform {self.arch} not supported")
        
        try:
            subprocess.check_output(['podman', 'container', 'inspect', self.cont_name], stderr=subprocess.DEVNULL)
            # container already exists
            return
        except subprocess.CalledProcessError:
            pass

        # container is not present, try building it
        # first, fetch the base image
        IMG_NAME_PREFIX = "alpine"
        img_name = f'{IMG_NAME_PREFIX}-{self.arch}'
        try:
            subprocess.check_output(['podman', 'image', 'inspect', img_name], stderr=subprocess.DEVNULL)
        except subprocess.CalledProcessError:
            # download the container
            pullcmd = ['podman', 'pull']
            if podman_platform:
                pullcmd.extend(['--platform', podman_platform])
            pullcmd.append(IMG_NAME_PREFIX)
            subprocess.check_call(pullcmd)
            # tag the container
            subprocess.check_call(['podman', 'tag', IMG_NAME_PREFIX, img_name])
        
        # proceed to run the container
        subprocess.check_call([
            'podman', 'run', '-d', '--stop-signal=SIGKILL', '--name', self.cont_name,
            img_name, 'sleep', 'infinity'
        ])

        # install dependencies
        subprocess.check_call(['podman', 'exec', self.cont_name, 'apk', 'add', 'libstdc++'])

    def _container_discover_symlink(self, target: Path):
        return subprocess.check_output(['podman', 'exec', self.cont_name, 'realpath', str(target)])[:-1].decode('utf8')
    
    def _copy_from_container(self, src: Path, target: Path):
        subprocess.check_call(['podman', 'cp', f'{self.cont_name}:{src}',str(target)])

    def run(self, workdir: Path, *deps: list[Path]):
        clonefile(deps[0]/self.dep_output_name, workdir/self.output_name)
        output_dir = workdir/self.output_name
        target_sysroot_dir = output_dir/"sysroot"
        
        ld_path = Path(f'/lib/ld-musl-{self.linux_arch_name}.so.1')
        libc_name = f'libc.musl-{self.linux_arch_name}.so.1'
        
        # copy alpine sysroot from container
        with self._start_container():
            os.makedirs(target_sysroot_dir, exist_ok=True)
            self._copy_from_container(ld_path, target_sysroot_dir/ld_path.name)
            os.symlink(ld_path.name, target_sysroot_dir/libc_name)
            self._copy_from_container('/usr/lib/libgcc_s.so.1', target_sysroot_dir/'libgcc_s.so.1')
            stdcpp_common_path = Path('/usr/lib/libstdc++.so.6')
            stdcpp_path = Path(self._container_discover_symlink(stdcpp_common_path))
            self._copy_from_container(stdcpp_path, target_sysroot_dir/stdcpp_path.name)
            os.symlink(stdcpp_path.name, target_sysroot_dir/stdcpp_common_path.name)
        
        # put patchelf
        patchelf_extract_dir = workdir/'patchelf'
        if not patchelf_extract_dir.exists():
            os.makedirs(patchelf_extract_dir, exist_ok=True)
            subprocess.check_call([ 'tar', '-C', patchelf_extract_dir.relative_to(workdir),
                '-xf', self.patchelf_archive], cwd=workdir)
        clonefile(patchelf_extract_dir/'bin/patchelf', output_dir/'patchelf')
        
        # patch 'launcher' and 'code-server-oss'
        with open(REPODIR/"scripts/reh-supplemental/portable-modifier.sh") as f:
            patch_in_script = f.read().replace("$$LD_NAME$$", ld_path.name)
        # put after the first encounter of ROOT=
        for fn in [VSCODE_PRODUCT_INFO()['serverApplicationName'], 'launcher']:
            fullpath = output_dir/"bin"/fn
            with open(fullpath) as f:
                original_script_lines = f.readlines()
            root_def_ln = None
            for i, l in enumerate(original_script_lines):
                if l.startswith('ROOT='):
                    root_def_ln = i + 1
                    break
            else:
                raise RuntimeError("Cannot find 'ROOT=' in the target script to patch")
            with open(fullpath, 'w') as f:
                f.writelines(itertools.chain(
                    original_script_lines[:root_def_ln], ['\n'],
                    (f'{line}\n' for line in patch_in_script.splitlines()), ['\n'],
                    original_script_lines[root_def_ln:]
                ))

targets = {
    # GNU/Linux targets officially supported by mainline VSCode
    'linux-gnu-x64': LinuxGeneric,
    'linux-gnu-arm64': LinuxGeneric,
    # alpine/MUSL targets
    'linux-alpine-x64': LinuxGeneric,
    'linux-alpine-arm64': LinuxGeneric,
    # portable targets based on alpine targets
    'linux-portable-x64': LinuxPortable,
    'linux-portable-arm64': LinuxPortable,
}

class ParallelArchiver:
    def __init__(self, njobs: int):
        self.sem = threading.Semaphore(njobs)
        self.allthreads: list[threading.Thread] = []

    def add_job(self, cwd: str | Path, src: str | Path, target: str | Path):
        '''
        jobs: list of (cwd, src, target)
        '''
        target = topath(target)
        if target.exists(): return
        self.sem.acquire(True)
        t = threading.Thread(target=lambda: self._job_thread(cwd, src, target))
        self.allthreads.append(t)
        t.start()

    def wait_all_jobs(self):
        for t in self.allthreads:
            t.join()
        self.allthreads.clear()

    def _job_thread(self, cwd: str | Path, src: str | Path, target: str | Path):
        args = ["tar", "--uid", "0", "--gid", "0", "-cJ", "-f", target, src]
        try:
            subprocess.check_call(args, cwd=cwd)
        finally:
            self.sem.release()

class Builder:
    def __init__(self):
        self.target_instances = {target: clazz(target) for target, clazz in targets.items()}
        self.prereqs_downloaded = set()
        self.targets_built = set()

    def download_prereqs(self, target):
        if target in self.prereqs_downloaded:
            return
        bldinst = self.target_instances[target]
        for d in bldinst.deps:
            self.download_prereqs(d)
        workdir = self.target_workdir(target)
        for url, filename in bldinst.downloads:
            target_file: Path = workdir/filename
            if target_file.exists():
                continue
            subprocess.check_call(["curl", "-L", "-o", target_file, url])
        self.prereqs_downloaded.add(target)

    def do_build(self, target):
        if target in self.targets_built:
            return
        print("building", target, "...")
        bldinst = self.target_instances[target]
        workdir = self.target_workdir(target)
        # skip if output directory already exists
        if not (workdir/bldinst.output_name).exists():
            # build the dependencies first
            depworkdirs = []
            for d in bldinst.deps:
                self.do_build(d)
                depworkdirs.append(self.target_workdir(d))
            bldinst.run(workdir, *depworkdirs)
        self.targets_built.add(target)

    def do_archive(self, target: str, archiver: ParallelArchiver):
        workdir = self.target_workdir(target)
        bldinst = self.target_instances[target]
        output_archive = REPODIR/BASE_PACKAGING_DIR/f"{bldinst.output_name}.tar.xz"
        archiver.add_job(workdir, bldinst.output_name, output_archive)

    @staticmethod
    def target_workdir(target: str) -> Path:
        ret = REPODIR/BASE_DR_WORKDIR/target
        os.makedirs(ret, exist_ok=True)
        return ret

def main():
    global STRIP

    ap = argparse.ArgumentParser()
    ap.add_argument("--no-strip-elf", action='store_true')
    ap.add_argument("--no-archive", action='store_true', help="Disable archiving (for debug)")
    ap.add_argument("--jobs", "-j", type=int, default=multiprocessing.cpu_count(),
        help="Max number of archival jobs")
    ap.add_argument("targets", choices=targets, nargs='*')
    args = ap.parse_args()

    if args.jobs < 1:
        print("Job numbers must be positive")
        return 1
    archiver = ParallelArchiver(args.jobs)

    # if request to strip, check if we have podman
    if not args.no_strip_elf:
        if not shutil.which("podman"):
            print("'podman' is required to strip ELF binaries.")
            print("Disable stripping using '--no-strip-elf' option or install podman.")
            return 1
        STRIP = True

    # check if base (primary target) REH has been built
    if not (REPODIR/BASE_REH_PATH).exists():
        print("primary REH must have been built first before additional REHs can be derived.")
        return 1

    selected_targets = set(args.targets) or targets.keys()
    bldinst = Builder()
    for tgt in selected_targets:
        print("prereqs download for", tgt, "...")
        bldinst.download_prereqs(tgt)
    for tgt in selected_targets:
        bldinst.do_build(tgt)
    if not args.no_archive:
        for tgt in selected_targets:
            print("archive", tgt, "...")
            bldinst.do_archive(tgt, archiver)
        archiver.wait_all_jobs()

if __name__ == "__main__":
    sys.exit(main())
