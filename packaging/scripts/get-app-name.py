#!/usr/bin/env python3
"""
Get the macOS .app name from the VSCode-darwin-arm64 folder
"""
import sys
import json
import os
from os import path

if __name__ == "__main__":
    base_dir = path.split(sys.argv[0])[0]
    os.chdir(path.join(base_dir, '../..'))
    with open('vscode/product.json', 'r') as f:
        d = json.load(f)
        print(f"{d['nameLong']}.app")
