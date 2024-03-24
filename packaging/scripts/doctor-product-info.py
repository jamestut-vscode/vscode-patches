#!/usr/bin/env python3
"""
Update commit hash of the resulting artefacts to match patches.list
"""

import sys
import os
import argparse
import contextlib
import json
from os import path
import importlib.util

def scan_modules(script_path):
    os.chdir(path.dirname(sys.argv[0]))
    ret = []
    for dir_to_scan in ('', 'external'):
        dir_to_scan = path.join(script_path, 'doctorplugins', dir_to_scan)
        for de in os.scandir(dir_to_scan):
            if de.name.endswith('.py') and de.is_file():
                spec = importlib.util.spec_from_file_location('doctorplugin', de.path)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                ret.append(module)
    return ret

def main():
    # base directory of this script
    script_path = path.realpath(path.dirname(sys.argv[0]))
    # target VSCode to be doctored
    target_base_dir = None
    # the actual path of the javascript root (the path that contains product.json and package.json)
    target_dir = None
    # base directory of this repo
    repo_path = path.realpath(path.join(script_path, '../..'))

    # function name of the module to run
    fn_name = None

    ap = argparse.ArgumentParser(description="Doctor various properties in package.json and product.json.")
    ap.add_argument('--pre', help='Specify to run prebuild doctoring.', action='store_true')
    ap.add_argument('--post', help='Specify to run postbuild doctoring.', action='store_true')
    ap.add_argument('target', help='Base directory (optional source code path for pre or built macOS app or REH for post).', nargs='?')
    args = ap.parse_args()

    if args.pre:
        fn_name = 'pre_run'
        target_base_dir = args.target or path.join(script_path, '../../vscode')
        target_dir = ''
    elif args.post:
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
    def doctor(json_name):
        pth = path.join(target_base_dir, target_dir, json_name)
        with open(pth, 'r') as f:
            d = json.load(f)
        # context manager user should set the 2nd element to True if the given
        # dictionary is edited.
        ret = [d, False]
        yield ret
        if ret[1]:
            with open(pth, 'w') as f:
                json.dump(d, f, indent='\t')

    for module in doctorplugins:
        if hasattr(module, fn_name):
            getattr(module, fn_name)(doctor)
            os.chdir(repo_path)

if __name__ == "__main__":
    sys.exit(main())
