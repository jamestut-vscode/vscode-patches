#!/usr/bin/env python3
import argparse
import sys
import os
import json
import multiprocessing
from pathlib import Path
import subprocess
from ninja_syntax import Writer as NinjaWriter

class NinjaWriterWrapper:
    def __init__(self, wr: NinjaWriter):
        self.wr = wr

def main():
    # constants
    # paths are relative to the base directory of the vscode-patches repo
    set_cwd()
    BASEDIR = Path("").absolute()
    WORKDIR =BASEDIR/"work"
    VSCODEDIR = WORKDIR/"vscode"
    PACKAGINGDIR = WORKDIR/"packaging"

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
    ap.add_argument("--mangle", "-m",
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
            f'cd $vscodedir && if [[ -z "$rimraf" ]]; then rm -rf "$rimraf"; fi && npx gulp $gulptarget',
            description="gulp $gulptarget"
        )
        wr.rule(
            "zip",
            'rm -rf $out; 7z -tzip -mmt$cpucount a $out $in',
            description="zip $out"
        )
        wr.rule(
            "darwinsign",
            'codesign --force --verify --verbose --deep --sign "$certname" "$appbundle"',
            description="macOS app bundle sign"
        )

        wr.newline()

        # common targets
        base_js_target = "$vscodedir/out-build"
        wr.build(base_js_target, "gulp", variables={
            "gulptarget": "compile-build-with-mangling" if args.mangle else "compile-build-without-mangling",
            "rimraf": base_js_target
        })
        ext_target = "$vscodedir/.build/extensions"
        wr.build(ext_target, "gulp", variables={
            "gulptarget": "compile-all-extensions",
            "rimraf": ext_target
        })

        # primary targets (REH and app for the primary target platform)
        target = '-'.join(PRIMARY_TARGET)
        for reh in [True, False]:
            # REH targets
            variant = 'reh' if reh else ''
            primary_js = f"$vscodedir/out-vscode{dashify(variant)}-min"
            wr.build(
                primary_js, "gulp",
                variables={"gulptarget": f"minify-vscode{dashify(variant)}"},
                implicit=[base_js_target, ext_target]
            )
            primary_target_prefix = "vscode-reh" if reh else "VSCode"
            primary_package = Path(f"$workdir/{primary_target_prefix}-{target}")
            wr.build(
                str(primary_package), "gulp",
                variables={
                    "gulptarget": f"package-vscode{dashify(variant)}-{target}",
                    "rimraf": str(primary_package)
                },
                implicit=[primary_js]
            )
            # macOS app bundle sign
            archive_implicit_dep = []
            if not reh and args.signcertname and PRIMARY_TARGET[0] == 'darwin':
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
            primary_archive = os.path.basename(f'{primary_package}.zip')
            wr.build(primary_archive, "zip", inputs=[str(primary_package)],
                implicit=archive_implicit_dep)
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
