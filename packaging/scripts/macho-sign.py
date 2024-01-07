#!/usr/bin/env python3
import sys
import os
import subprocess

_macho_headers = {
    b'\xfe\xed\xfa\xce',
    b'\xce\xfa\xed\xfe',
    b'\xfe\xed\xfa\xcf',
    b'\xcf\xfa\xed\xfe'
}

def is_macho(filename):
    with open(filename, 'rb') as file:
        header = file.read(4)
    return header in _macho_headers

def traverse_files(startdir):
    for root, _, files in os.walk(startdir):
        for file in files:
            fullpath = os.path.join(root, file)
            yield fullpath

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: macho-sign (directory to traverse) (codesign certificate name)")
        print("This app will traverse the given directory for Mach-O files "
            "and will run codesign on them. This app will stop for any failure.")
        sys.exit(1)
    
    targetdir, certname = sys.argv[1:3]

    for file in traverse_files(targetdir):
        if is_macho(file):
            print(f"Signing '{file}'")
            po = subprocess.run(['codesign', '-s', certname, file], capture_output=True, check=False)
            if po.returncode:
                errstr = po.stderr.decode('utf8').strip()
                if errstr.endswith('is already signed'):
                    # this is a bad hack to workaround that we don't support macOS framework's
                    # version symlinks as of now: binaries might be traversed more than once
                    # and as a result, they might have been signed already.
                    print(f"'{file}' is already signed, ignoring ...")
                else:
                    print(f"Failed signing '{file}'!")
                    print(po.stderr.decode('utf8'))
                    sys.exit(2)
