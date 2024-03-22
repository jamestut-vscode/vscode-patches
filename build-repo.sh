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

# clone VSCode if not exist
if ! [ -d vscode ]
then
    echo "vscode repository does not exist. cloning ..."
    git clone https://github.com/microsoft/vscode.git vscode
fi

cd vscode
echo "Fetching repository ..."
git fetch

echo "Checking repository for existing patches ..."
if ! [[ -z "$(git branch --list patched)" ]]
then
    echo "Deleting existing patched folder ..."
    git checkout main
    git branch -D patched
fi

cd ..
echo "Applying patches ..."
./spm.py patches vscode

echo "Applying doctor ..."
packaging/scripts/doctor-product-info.py --pre
cd vscode
git add package.json product.json
git commit -m 'Doctor product.json and package.json'

echo "Done! The custom VSCode is ready to be built!"
