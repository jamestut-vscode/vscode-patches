#!/usr/bin/env python3
import sys
import os
import argparse
import subprocess
import shutil
import multiprocessing
import threading
from pathlib import Path

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
def REH_OBJ_LIST() -> list[str]:
    return [fn for fn in find_macho(REPODIR/BASE_REH_PATH) if str(fn) not in EXCLUDE_BINS]

# helper functions
def topath(p: str | Path) -> Path:
    return Path(p) if type(p) is not Path else p

def clonefile(src: str | Path, tgt: str | Path):
    '''
    Use macOS' "cp -c" to use clonefile for efficient copy
    '''
    tgt = topath(tgt)
    if tgt.exists(): return
    subprocess.check_output(["cp", "-c", "-r", src, tgt])

def replace_file(basefrom: str | Path, baseto: str | Path, fn: str | Path):
    basefrom, baseto = topath(basefrom), topath(baseto)
    os.unlink(baseto/fn)
    clonefile(basefrom/fn, baseto/fn)

def rimraf(target: str | Path):
    subprocess.check_output(["rm", "-rf", target])

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

        self.output_name = f"vscode-reh-{out_name_suff}"
        self.deps = []
        self.downloads = [(
            f"https://update.code.visualstudio.com/commit:{BASE_COMMIT}/server-{out_name_suff}/{REL_REH_CHANNEL}",
            self.tarball_name)]

    def run(self, workdir: Path, *_):
        target_extract_dir = workdir/self.extract_name
        if not target_extract_dir.exists():
            print("  Extracting ...")
            subprocess.check_call(["tar", "-xf", self.tarball_name], cwd=workdir)
            print("  Stripping ELF binaries ...")
            strip_elf_binaries(workdir/self.extract_name, REH_OBJ_LIST())
        print("  Processing ...")
        clonefile(REPODIR/BASE_REH_PATH, workdir/self.output_name)
        # remove uneeded binaries
        for exclbin in EXCLUDE_BINS:
            os.unlink(workdir/self.output_name/exclbin)
        for objfile in REH_OBJ_LIST():
            replace_file(target_extract_dir, workdir/self.output_name, objfile)

class GnuLinuxLegacy:
    def __init__(self, target: str):
        _, _, self.arch = target.split("-")
        self.node_legacy_dir_name = f"node-v{REH_NODE_VERSION}-linux-{self.arch}-glibc-217"
        self.node_legacy_tarball_name = self.node_legacy_dir_name + ".tar.xz"

        self.output_name = f"vscode-reh-linux-legacy-{self.arch}"
        self.deps = [f'linux-gnu-{self.arch}']
        self.downloads = [(
            f"https://unofficial-builds.nodejs.org/download/release/v{REH_NODE_VERSION}/{self.node_legacy_tarball_name}",
            self.node_legacy_tarball_name
        )]

    def run(self, workdir: Path, *deps: list[Path]):
        legacy_node_extract_dir = workdir/self.node_legacy_dir_name
        legacy_node_bin_dir = legacy_node_extract_dir/"bin"
        if not legacy_node_extract_dir.exists():
            print("  Extracting legacy node.js package ...")
            subprocess.check_call(["tar", "-xf", self.node_legacy_tarball_name], cwd=workdir)
            print("  Stripping legacy node.js binary ...")
            strip_elf_binaries(legacy_node_bin_dir, ["node"])
        print("  Processing ...")
        depworkdir = deps[0]/f"vscode-server-linux-{self.arch}"
        clonefile(depworkdir, workdir/self.output_name)
        replace_file(legacy_node_bin_dir, workdir/self.output_name, "node")

targets = {
    # GNU/Linux targets officially supported by mainline VSCode
    'linux-gnu-x64': LinuxGeneric,
    'linux-gnu-arm64': LinuxGeneric,
    # alpine/MUSL targets
    'linux-alpine-x64': LinuxGeneric,
    'linux-alpine-arm64': LinuxGeneric,
    # legacy GNU/Linux targets (glibc 2.17 used in Enterprise Linux 7)
    'linux-gnulegacy-x64': GnuLinuxLegacy,
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
        print("building", tgt, "...")
        bldinst.do_build(tgt)
    for tgt in selected_targets:
        print("archive", tgt, "...")
        bldinst.do_archive(tgt, archiver)
    archiver.wait_all_jobs()

if __name__ == "__main__":
    sys.exit(main())
