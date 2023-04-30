#!/usr/bin/env zsh

# This script creates the following:
#  - VSCode client app for macOS
#  - VSCode REH (Remote Extension Host) server for:
#    - linux-x64
#    - linux-arm64
#    - darwin-arm64
# This script is currently only compatible with macOS on arm64.
# The resulting archive will be put in the "packaging/out" directory relative to this repo.

set -e
cd ${0:a:h}
cd ..

if [[ "$(uname -s -p)" != "Darwin arm" ]]
then
    echo "This script is currently hardcoded only to produce builds for arm version of macOS." >&2
    exit 1
fi

if ! where 7z
then
    echo "7z is not available. Cannot proceed." >&2
    exit 1
fi

# get the base commit: we will need this to download the appropriate 'node' and 'node_modules'
# from official Microsoft's VSCode REH builds
PATCHLINE=$(head -1 patches/patches.list)
if [[ ${${(s: :)PATCHLINE}[1]} != "base-commit:" ]]
then
    echo "Error retreiving VSCode base commit" >&2
    exit 1
fi

BASE_COMMIT=${${(s: :)PATCHLINE}[2]}
echo "VSCode base commit is $BASE_COMMIT"

# install deps
cd vscode
if ! [[ -d node_modules ]]
then
    echo "Running yarn to install dependencies ..."
    yarn
fi

# begin gulping!
if ! [[ -d ../VSCode-darwin-arm64 ]]
then
    echo "Building VSCode client for macOS arm"
    yarn gulp vscode-darwin-arm64-min
fi

if ! [[ -d ../vscode-reh-darwin-arm64 ]]
then
    echo "Building VSCode REH for macOS arm"
    yarn gulp vscode-reh-darwin-arm64-min
fi

# archive the easy part first: those targetting macOS
cd ..
echo "Creating archive for VSCode macOS ..."
packaging/create-archive.sh VSCode-darwin-arm64 packaging/out/VSCode-darwin-arm64.zip

echo "Creating archive for VSCode REH macOS ..."
packaging/create-archive.sh vscode-reh-darwin-arm64 packaging/out/vscode-reh-darwin-arm64.zip

# linux REH targets
cd packaging
mkdir -p reh-linux
cd reh-linux

LINUX_TARGETS=(arm64 x64)
for TGT in $LINUX_TARGETS
do
    echo "Downloading official VSCode server for Linux $TGT ..."
    DL_ARCHIVE=vscode-server-linux-$TGT.tar.gz
    curl -L https://update.code.visualstudio.com/commit:$BASE_COMMIT/server-linux-$TGT/stable > $DL_ARCHIVE

    echo "Extracting official package ..."
    tar -xf $DL_ARCHIVE

    SRC_DIR=vscode-server-linux-$TGT
    TARGET_DIR=vscode-reh-linux-$TGT

    echo "Preparing package for Linux $TGT ..."
    cp -r ../../vscode-reh-darwin-arm64 $TARGET_DIR
    rm -rf $TARGET_DIR/node $TARGET_DIR/node_modules

    cp $SRC_DIR/node $TARGET_DIR/node
    cp -r $SRC_DIR/node_modules $TARGET_DIR/node_modules

    # need to remove vsda as our REH is not signed
    rm -rf $TARGET_DIR/node_modules/vsda

    echo "Archiving VSCode REH for Linux $TGT ..."
    ../create-archive.sh $TARGET_DIR ../out/vscode-reh-linux-$TGT.zip
done

echo "Done creating packages!"
