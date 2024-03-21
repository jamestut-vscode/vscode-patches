# Packaging Instructions

1. Run `build-repo.sh` to fetch official VSCode repository and apply patches from this repository.
2. Run `make` on this `packaging` folder to build the artefacts.
   - The file `.signenv` must be put in this directory. This file will be sourced by the zsh build script to set the environment variables related to signing the VSCode client build for macOS. _To skip signing the macOS client app, make this file empty_. Following environment variables are required to sign the macOS build:
     - `VSCSIGN_CERTNAME`: The name of the certificate in local keychain that will be used for codesigning.
   - Set the `VSCODE_MINIFY=1` environment variable to build a minified and optimised version of VSCode. This will take much longer to finish the build.
3. To clean the artefacts, run `make clean`.
