#!/usr/bin/env zsh
cd "${0:a:h}"

function show_help() {
    echo "Usage: ${0:a:t} [deep]"
    echo
    echo "Revert all modifications to the 'vscode' repository and also clean untracked files."
    echo "If 'deep' is specified, additionally clean files specified in '.gitignore'. These files includes build artefacts and 'node_modules'."
    echo "It is normally not necessary to perform a deep clean."
    exit 1
}

if ! [ -d vscode/.git ]
then
    echo "vscode repository does not exist. Nothing to do."
    exit
fi

if [[ $# -gt 0 ]]
then
    if [[ "$1" == "deep" ]]
    then
        DEEPCLEAN=1
    else
        show_help
    fi
fi

if [[ $DEEPCLEAN -eq 1 ]]
then
    echo "This will remove EVERYTHING from the 'vscode' repository, including build artefacts, node-modules, and untracked files."
else
    echo "This will clean all uncommited changes, including UNTRACKED files."
fi
read ANSWER\?"Type 'yes' to proceed: "

if [[ "$ANSWER" == 'yes' ]]
then
    echo "Cleaning repository ..."
    cd vscode
    if [[ $DEEPCLEAN -eq 1 ]]
    then
        echo "Cleaning ..."
        rm -rf $(ls -A | grep -v '^.git$')
        echo "Restoring from commit ..."
        git restore .
    else
        git reset --hard HEAD
        git clean -fd
    fi
else
    echo "Operation cancelled."
fi
