#!/usr/bin/env zsh

# This script clones the upstream VSCode and applies our patches

set -e

cd ${0:a:h}

if ! [ -e spm.py ]
then
    echo "Downloading Simple Patch Manager ..."
    curl -L https://raw.githubusercontent.com/jamestut/spm/main/spm.py > spm.py
    chmod +x spm.py
fi

# get some basic info about our base
BASE_TAG=$(packaging/scripts/get-base-commit.sh --no-resolve-hash)

# clone VSCode if not exist
if ! [ -d vscode ]
then
    echo "vscode repository does not exist. cloning ..."
    git clone --depth 1 https://github.com/microsoft/vscode.git vscode
fi

cd vscode

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

cd ..
echo "Applying patches ..."
./spm.py patches vscode

echo "Applying doctor ..."
packaging/scripts/doctor-product-info.py --pre
cd vscode
git add '*.json'
git commit -m 'Doctor product.json and package.json'

echo "Done! The custom VSCode is ready to be built!"
