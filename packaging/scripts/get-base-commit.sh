#!/usr/bin/env zsh

# Retreives the base commit hash specified in patches.list

set -e
cd ${0:a:h}
cd ../..

PATCHLINE=$(head -1 patches/patches.list)
if [[ ${${(s: :)PATCHLINE}[1]} != "base-commit:" ]]
then
    echo "Error retreiving VSCode base commit" >&2
    exit 1
fi
BASE_COMMIT=${${(s: :)PATCHLINE}[2]}
echo $BASE_COMMIT
