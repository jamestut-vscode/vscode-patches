#!/usr/bin/env zsh

set -e

function show_help() {
    echo "Build VSCode for macOS ARM (server (REH) and client (app bundle) version)"
    echo "Usage: ${0:t} (VSCode Git repo) (app|reh)"
    exit 1
}

if [[ $# -ne 2 ]]
then
    show_help
fi

cd "$1"

# check if we want a regular build, or highly optimised minified build
if ! [[ -z "$VSCODE_MINIFY" ]]
then
    echo "VSCode build minification is enabled"
    DASHED_MINIFY="-min"
else
    echo "VSCode build minification is disabled"
    DASHED_MINIFY=
fi

case "$2" in
    app)
        TARGET=vscode-darwin-arm64$DASHED_MINIFY
        ;;
    reh)
        TARGET=vscode-reh-darwin-arm64$DASHED_MINIFY
        ;;
esac

if [[ -z $TARGET ]]
then
    show_help
fi

echo "Running yarn to update and install dependencies ..."
yarn

echo "Building VSCode $2 for macOS Arm64 ..."
yarn gulp $TARGET

# update timestamp for use as a marker for the Makefile
echo "Updating timestamp ..."
case "$2" in
    app)
        touch ../VSCode-darwin-arm64/built
        ;;
    reh)
        touch ../vscode-reh-darwin-arm64/bin/code-server-oss
        ;;
esac
