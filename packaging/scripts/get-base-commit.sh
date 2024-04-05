#!/usr/bin/env zsh

# Retreives the base commit hash specified in patches.list

set -e
cd ${0:a:h}
cd ../..

PATCHLINE=$(grep -F 'base-commit:' patches/patches.list | head -1)
if [[ ${${(s: :)PATCHLINE}[1]} != "base-commit:" ]]
then
    echo "Error retreiving VSCode base commit" >&2
    exit 1
fi
BASE_COMMIT=${${(s: :)PATCHLINE}[2]}

# resolve tag -> hash unless we're told to not do so
if [[ "${1}" != "--no-resolve-hash" ]]
then
    cd vscode
    BASE_COMMIT=$(git rev-list -n 1 ${BASE_COMMIT})
fi

echo $BASE_COMMIT
