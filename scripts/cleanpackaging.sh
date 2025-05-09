#!/usr/bin/env zsh
cd "${0:a:h}"
cd "$(git rev-parse --show-toplevel)"

function rimraf {
    if [[ -e "$1" ]]
    then
        echo rm -rf "$1"
        rm -rf "$1"
    fi
}

rimraf work/packaging
for I in work/VSCode-*(N) work/vscode-*(N) work/vscode/out-*(N)
do
    rimraf "$I"
done
rimraf work/vscode/.build
