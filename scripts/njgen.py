#!/usr/bin/env python3
import argparse
import sys
import os
import json
import multiprocessing
from pathlib import Path
import subprocess
from ninja_syntax import Writer as NinjaWriter
from typing import Dict, List, Union, Optional

def append_to_kwargs(kwargs:Dict, key:str, value:str):
    '''
    Append to kwargs[key], converting it to a list of string first if it is of
    string type.
    '''
    if type(kwargs.setdefault(key, [])) is str:
        kwargs[key] = [kwargs[key]]
    kwargs[key].append(value)

def main():
    # constants
    # paths are relative to the base directory of the vscode-patches repo
    set_cwd()
    BASEDIR = Path("").absolute()
    WORKDIR =BASEDIR/"work"
    VSCODEDIR = WORKDIR/"vscode"
    PACKAGINGDIR = WORKDIR/"packaging"

    DARWIN_SELF_SIGN_SCRIPT = "macos-self-sign.sh"

    # paths relative to the build.ninja
    VSCODEDIR_REL = VSCODEDIR.relative_to(PACKAGINGDIR, walk_up=True)
    WORKDIR_REL = WORKDIR.relative_to(PACKAGINGDIR, walk_up=True)

    # get product info (for obtaining product names)
    with open(VSCODEDIR/"product.json", "r") as f:
        product_info = json.load(f)

    PRIMARY_TARGET = ('darwin', 'arm64')

    ap = argparse.ArgumentParser(
        description="Generate a Ninja build file to work/packaging for creating .zip archives of VSCode. "
        "The resulting work/packaging directory is ephemeral and must be deleted when attempting to package a new version.")
    ap.add_argument("--signcertname",
        help="Keychain certificate name for signing macOS app bundle.")
    ap.add_argument("--mangle", "-m", action='store_true',
        help="Enable JavaScript name mangling optimisation. "
        "This will significantly increase build time.")
    args = ap.parse_args()

    # output build ninja
    PACKAGINGDIR_REL = PACKAGINGDIR.relative_to(BASEDIR)
    print(f"Creating build.ninja in '{PACKAGINGDIR_REL}' ...")
    os.makedirs(PACKAGINGDIR_REL, exist_ok=True)
    with open(PACKAGINGDIR_REL/"build.ninja", "w") as f:
        wr = NinjaWriter(f)

        # variables
        wr.variable("cpucount", str(multiprocessing.cpu_count()))
        wr.variable("vscodedir", VSCODEDIR_REL)
        wr.variable("workdir", WORKDIR_REL)
        wr.newline()

        # rules
        wr.rule(
            "gulp",
            'cd $vscodedir && if ! [[ -z "$rimraf" ]]; then rm -rf "$rimraf"; fi && npx gulp $gulptarget && if ! [[ -z "$touchtarget" ]]; then find "$touchtarget" -exec touch {} +; fi',
            description="gulp $gulptarget"
        )
        wr.rule(
            "archive",
            'rm -rf $out; tar --uid 0 -C "$cwd" --gid 0 -cJ -f $out "$input"',
            description="archive $out"
        )
        wr.rule(
            "darwinsign",
            # update time before sign
            'codesign --force --verify --verbose --deep --sign "$certname" "$appbundle"',
            description="macOS app bundle sign"
        )
        wr.rule(
            "npmi",
            'cd $vscodedir && npm i',
            description="npm install"
        )
        wr.rule(
            "copyfile",
            'cp "$source" "$out"',
            description="copy file"
        )

        wr.newline()

        # common to all gulp targets
        npmi_target = "$vscodedir/node_modules"
        wr.build(npmi_target, "npmi")

        def add_gulp_build(
                outputs: Union[str, List[str]],
                gulptarget:str,
                rimraf:Optional[str]=None,
                touchtarget:Optional[str] = None,
                **kwargs):
            append_to_kwargs(kwargs, "order_only", npmi_target)
            variables:Dict = kwargs.setdefault("variables", {})
            variables["gulptarget"] = gulptarget
            if rimraf is not None:
                variables["rimraf"] = rimraf
            if touchtarget is not None:
                variables["touchtarget"] = touchtarget
            wr.build(outputs, "gulp", **kwargs)

        # common targets
        base_js_target = "$vscodedir/out-build"
        add_gulp_build(base_js_target, rimraf=base_js_target,
            gulptarget="compile-build-with-mangling" if args.mangle else "compile-build-without-mangling")
        ext_target = "$vscodedir/.build/extensions"
        add_gulp_build(ext_target, "compile-all-extensions", ext_target)

        # primary targets (REH and app for the primary target platform)
        target = '-'.join(PRIMARY_TARGET)
        for reh in [True, False]:
            # REH targets
            variant = 'reh' if reh else ''
            primary_js = f"$vscodedir/out-vscode{dashify(variant)}-min"
            add_gulp_build(primary_js, f"minify-vscode{dashify(variant)}",
                implicit=[base_js_target, ext_target])
            primary_target_prefix = "vscode-reh" if reh else "VSCode"
            primary_package = Path(f"$workdir/{primary_target_prefix}-{target}")
            primary_package_impl_dep = [primary_js]
            if reh:
                # node.js main binary
                node_target = f"$vscodedir/.build/node"
                add_gulp_build(node_target, f"node-{target}")
                primary_package_impl_dep.append(node_target)
            add_gulp_build(str(primary_package),
                rimraf=str(primary_package),
                gulptarget=f"package-vscode{dashify(variant)}-{target}",
                touchtarget=str(primary_package),
                implicit=primary_package_impl_dep)
            # macOS app bundle sign
            archive_implicit_dep = [str(primary_package)]
            if not reh and PRIMARY_TARGET[0] == 'darwin':
                if args.signcertname:
                    app_bundle_path = primary_package/f"{product_info['nameLong']}.app"
                    app_bundle_sign_target = app_bundle_path/"Contents/_CodeSignature"
                    wr.build(
                        str(app_bundle_sign_target), "darwinsign", inputs=[str(primary_package)],
                        variables={
                            "certname": args.signcertname,
                            "appbundle": str(app_bundle_path)
                        }
                    )
                    archive_implicit_dep.append(str(app_bundle_sign_target))
                else:
                    # copy the self-signing script
                    self_sign_target = str(primary_package/DARWIN_SELF_SIGN_SCRIPT)
                    wr.build(self_sign_target, "copyfile",
                        variables={"source": BASEDIR/"scripts"/DARWIN_SELF_SIGN_SCRIPT})
                    archive_implicit_dep.append(str(self_sign_target))
            primary_archive = os.path.basename(f'{primary_package}.tar.xz')
            wr.build(primary_archive, "archive", implicit=archive_implicit_dep, variables={
                "cwd": os.path.dirname(primary_package),
                "input": os.path.basename(primary_package),
            })
            wr.default(primary_archive)


def set_cwd():
    os.chdir(os.path.dirname(sys.argv[0]))
    # change to the base directory of the vscode-patches repo
    repodir = subprocess.check_output(['git', 'rev-parse', '--show-toplevel']).decode('utf8').rstrip()
    os.chdir(repodir)

def abspath(pth: str) -> str:
    return str(Path(pth).absolute())

def dashify(v: str) -> str:
    return "" if not v else f"-{v}"

if __name__ == "__main__":
    # check Python version
    if (sys.version_info.major, sys.version_info.minor) < (3, 12):
        print("This script requires Python 3.12 or newer.")
        sys.exit(1)
    main()
