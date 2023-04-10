#!/usr/bin/env zsh

# This script creates a zip file from the given folder

if [[ $# -ne 2 ]]
then
    echo "Usage: ${0:t} (folder to be archived) (output zip file)"
    exit 1
fi

NUMTHREADS=$(sysctl -n machdep.cpu.thread_count)
7z -mmt$NUMTHREADS a "$2" "$1"
