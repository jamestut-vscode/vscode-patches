#!/usr/bin/env python3
"""
Update commit hash of the resulting artefacts to match patches.list
"""

import sys
import os
import argparse
import json
from os import path

def main():
    ap = argparse.ArgumentParser(description="Replace VSCode's product.json's commit hash with that of patches.list.")
    ap.add_argument('target', help='Base directory of built VSCode (macOS app or REH).')
    args = ap.parse_args()
    target_dir = path.realpath(args.target.rstrip('/'))

    base_path = path.split(sys.argv[0])[0]
    repo_path = path.join(base_path, '../..')
    os.chdir(repo_path)

    # get target commit hash
    chline = None
    src_str = 'final-commit:'
    with open('patches/patches.list', 'r') as f:
        for l in f:
            l = l.strip()
            if l.startswith(src_str):
                chline = l
                break

    if chline is None:
        raise ValueError("'final-commit' line not found.")

    target_hash = chline[len(src_str) + 1:].strip()

    if target_dir.endswith('.app'):
        # macOS app
        target_product_json = 'Contents/Resources/app/product.json'
    else:
        # must be REH
        target_product_json = 'product.json'
    target_product_json = path.join(target_dir, target_product_json)

    with open(target_product_json, 'r') as f:
        product_json = json.load(f)

    if 'commit' in product_json:
        if product_json['commit'] == target_hash:
            print("Commit hash already the same. Skipping.")
            return 0
        else:
            product_json['commit'] = target_hash
    else:
        print("Commit is not defined in product.json. Skipping.")
        return 0

    # save doctored product.json
    print("Saving modified JSON ...")
    with open(target_product_json, 'w') as f:
        json.dump(product_json, f, indent='\t')

if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        print(e)
        sys.exit(1)
