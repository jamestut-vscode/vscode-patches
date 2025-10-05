#!/usr/bin/env python3
import sys
import os
from os import path
import json
import subprocess
from urllib.request import urlopen

NPMRC_PATH = 'work/vscode/.npmrc'
ELECTRON_CHECKSUM_PATH = 'work/vscode/build/checksums/electron.txt'

def read_npmrc() -> dict[str, str]:
    data = {}
    with open(NPMRC_PATH) as f:
        for line in f:
            splt = line.rstrip().split('=', maxsplit=1)
            if len(splt) != 2:
                continue
            data[splt[0]] = splt[1]
    return data

def get_npmrc_electron_version(npmrc_data) -> str:
    assert 'electron' in npmrc_data.get('runtime')
    return eval(npmrc_data.get('target'))

def write_npmrc(data: dict[str, str]):
    with open(NPMRC_PATH, 'w') as f:
        for k, v in data.items():
            f.write(f"{k}={v}\n")

def update_electron_checksum(electron_version: str):
    url = f"https://github.com/electron/electron/releases/download/v{electron_version}/SHASUMS256.txt"

    # Perform GET request with redirect handling using urllib
    print(f"Downloading Electron checksums for v{electron_version} ...")
    response = urlopen(url)
    content = response.read().decode('utf-8')

    # Write the contents to the checksum file
    with open(ELECTRON_CHECKSUM_PATH, 'w') as f:
        f.write(content)
        f.write('\n')

def main():
    cwd = path.dirname(__file__)
    repodir = subprocess.check_output(['git', 'rev-parse', '--show-toplevel'], cwd=cwd)[:-1]
    os.chdir(repodir)

    if not os.path.exists(NPMRC_PATH):
        print("Please clone the vscode repo first by invoking 'build-repo.sh'.")
        sys.exit(1)

    with open('version.json') as f:
        version_info = json.load(f)
    target_electron_version = version_info.get('electronVersion')

    if target_electron_version is None:
        # use the default electron version
        sys.exit(0)

    npmrc_data = read_npmrc()
    if get_npmrc_electron_version(npmrc_data) == target_electron_version:
        # already updated, not proceeding
        sys.exit(0)

    # step 1: update npmrc
    npmrc_data['target'] = f'"{target_electron_version}"'
    write_npmrc(npmrc_data)

    # step 2: update checksum
    update_electron_checksum(target_electron_version)

if __name__ == "__main__":
    main()
