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
    for de in os.scandir(path.join(script_path, 'doctorplugins')):
        if de.name.endswith('.py') and de.is_file():
            spec = importlib.util.spec_from_file_location('doctorplugin', de.path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            ret.append(module)
    return ret

def main():
    ap = argparse.ArgumentParser(description="Replace VSCode's package.json's version number and product.json's commit hash with that of patches.list.")
    ap.add_argument('target', help='Base directory of built VSCode (macOS app or REH).')
    args = ap.parse_args()

    target_dir = path.realpath(args.target.rstrip('/'))

    script_path = path.realpath(path.dirname(sys.argv[0]))
    repo_path = path.join(script_path, '../..')
    os.chdir(repo_path)

    doctorplugins = scan_modules(script_path)

    if target_dir.endswith('.app'):
        # macOS app
        target_base_dir = 'Contents/Resources/app'
    else:
        # must be REH
        target_base_dir = ''

    @contextlib.contextmanager
    def doctor(json_name):
        pth = path.join(target_dir, target_base_dir, json_name)
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
        module.run(doctor)

if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        print(e)
        sys.exit(1)
