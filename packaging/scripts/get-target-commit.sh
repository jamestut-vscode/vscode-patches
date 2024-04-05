#!/usr/bin/env zsh

# Retreives the target commit hash specified in patches.list

set -e
cd ${0:a:h}
cd ../..

PATCHLINE=$(grep -F 'final-commit:' patches/patches.list | head -1)
if [[ ${${(s: :)PATCHLINE}[1]} != "final-commit:" ]]
then
    echo "Error retreiving repo target commit" >&2
    exit 1
fi
TARGET_COMMIT=${${(s: :)PATCHLINE}[2]}
echo $TARGET_COMMIT
