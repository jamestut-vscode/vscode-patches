#!/usr/bin/env python3
"""
Update commit hash of the resulting artefacts to match patches.list
"""

import sys
import os
import argparse
import contextlib
import subprocess
import json
import typing
from os import path
import importlib.util

class DoctorContext:
    data: dict | list = {}
    modified: bool = False
    filepath: str = ""

    def __init__(self, data: dict | list, modified: bool, filepath: str):
        self.data = data
        self.modified = modified
        self.filepath = filepath

def scan_modules(script_path):
    os.chdir(path.dirname(sys.argv[0]))
    ret = []
    for dir_to_scan_name in ('', 'external'):
        dir_to_scan = path.join(script_path, 'doctorplugins', dir_to_scan_name)
        if not path.exists(dir_to_scan):
            if dir_to_scan_name:
                print(f"Directory '{dir_to_scan_name}' does not exist. Skipping.")
                continue
        for de in os.scandir(dir_to_scan):
            if de.name.endswith('.py') and de.is_file():
                spec = importlib.util.spec_from_file_location('doctorplugin', de.path)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                ret.append(module)
    return ret

def get_repo_path():
    return subprocess.check_output(['git', 'rev-parse', '--show-toplevel']).decode('utf8').rstrip()

def main():
    # base directory of this script
    script_path = path.realpath(path.dirname(sys.argv[0]))
    # target VSCode to be doctored
    target_base_dir = None
    # the actual path of the javascript root (the path that contains product.json and package.json)
    target_dir = None
    # base directory of this repo
    repo_path = get_repo_path()

    # function name of the module to run
    fn_name = None

    ap = argparse.ArgumentParser(description="Doctor various properties in package.json and product.json.")
    ap.add_argument('--pre', help='Specify to run prebuild doctoring.', action='store_true')
    ap.add_argument('--post', help='Specify to run postbuild doctoring.', action='store_true')
    ap.add_argument('target', help='Base directory (optional source code path for pre or built macOS app or REH for post).')
    args = ap.parse_args()

    if args.pre:
        fn_name = 'pre_run'
        target_base_dir = args.target
        target_dir = ''
    elif args.post:
        print("post run functionality is disabled for now.")
        return 1
        fn_name = 'post_run'
        target_base_dir = args.target
        if target_base_dir.endswith('.app'):
            # macOS app
            target_dir = 'Contents/Resources/app'
        else:
            # must be REH
            target_dir = ''
    else:
        print("Please specify --pre or --post.")
        return 1
    # must be done before we change directory to repo path
    target_base_dir = path.realpath(target_base_dir)

    # the plugins expect the path to be set to the base 'vscode-patches' repo
    os.chdir(repo_path)
    doctorplugins = scan_modules(script_path)

    @contextlib.contextmanager
    def doctor(json_name) -> typing.Generator[DoctorContext, None, None]:
        base_path = path.join(target_base_dir, target_dir)
        pth = path.join(base_path, json_name)
        with open(pth, 'r') as f:
            d = json.load(f)
        context = DoctorContext(d, False, pth)
        yield context
        if context.modified:
            with open(pth, 'w') as f:
                json.dump(d, f, indent='\t')

    for module in doctorplugins:
        if hasattr(module, fn_name):
            os.chdir(repo_path)
            getattr(module, fn_name)(doctor)

if __name__ == "__main__":
    sys.exit(main())
