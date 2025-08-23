#!/usr/bin/env zsh
for N in *.app
do
    codesign --force --verify --verbose --deep --sign - "$N"
done
