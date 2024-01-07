#!/usr/bin/env zsh

set -e

source .signenv

if [[ $# -ne 1 ]]
then
    echo "Usage: ${0:t} (folder containing Mach-O binaries)"
fi

if [[ -z "$VSCSIGN_CERTNAME" ]]
then
    echo "Keychain certificate name not specified in VSCSIGN_CERTNAME. Skipping signing."
    exit
fi

"${0:a:h}/macho-sign.py" "$1" "$VSCSIGN_CERTNAME"
