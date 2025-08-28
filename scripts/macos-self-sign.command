#!/usr/bin/env zsh
cd "${0:a:h}"
for N in *.app
do
    codesign --force --verify --verbose --deep --sign - "$N"
done
