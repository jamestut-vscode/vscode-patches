#!/usr/bin/env zsh

# This script clones the upstream VSCode and applies our patches

set -e

WORKDIR="$(realpath ${0:a:h})"
cd "$WORKDIR"

VSCODE_REPO=work/vscode

# get some basic info about our base
BASE_TAG=$(scripts/get-base-commit.sh --no-resolve-hash)

# clone VSCode if not exist
if ! [ -d $VSCODE_REPO ]
then
    echo "vscode repository does not exist. cloning ..."
    git clone --depth 1 https://github.com/microsoft/vscode.git $VSCODE_REPO
fi

cd $VSCODE_REPO

# check if the desired tag exists in the repository
if ! git rev-list -n 0 ${BASE_TAG} -- 2>/dev/null
then
    # desired tag is not fetched
    echo "Fetching repository ..."
    git fetch --depth 1 origin ${BASE_TAG}
    # create local tag
    git tag ${BASE_TAG} FETCH_HEAD
fi

if ! [[ -z "$(git branch --list patched)" ]]
then
    echo "Deleting existing patched branch ..."
    git checkout main
    git branch -D patched
fi

cd "$WORKDIR"
echo "Applying patches ..."
spm/spm.py patches $VSCODE_REPO

echo "Applying doctor ..."
scripts/doctor-product-info.py --pre $VSCODE_REPO
cd $VSCODE_REPO
git add '*.json'
git commit --no-verify -m 'Doctor product.json and package.json'

echo "Updating submodules ..."
git submodule update --init

echo "Done! The custom VSCode is ready to be built!"
