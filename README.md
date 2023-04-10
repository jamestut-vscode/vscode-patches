# James' Visual Studio Code

This fork contains my personal modifications to Visual Studio Code that are not approved by upstream maintainers.

## Changes Made

- **Updated built-in terminal.**  
  The built-in terminal now uses my own [xterm.js fork](https://github.com/jamestut/xterm.js). The differences are described there.
- **Enable proposed API for all extensions.**  
  All extensions can now use proposed APIs without having to run this version of VSCode with a special command line argument.
- **Tweak reconnection timeout.**  
  When connection to remote fails, immediately shows the dialog that prompts user to reconnect or reload window. When reconnecting, the timeout is set to 15 seconds per stage instead of 40 seconds globally.
- **Disable shorten reconnect grace period.**  
  When there are ungracefully-disconnected client on VSCode's REH server, do not reduce their grace reconnection period when a new client is reconnected.

## Build Instructions

- Run `build-repo.sh`. Running this script will perform these steps:
  - Download the latest version of my [Simple Patch Manager](https://github.com/jamestut/spm) script.
  - Clone the original [VSCode repo](https://github.com/microsoft/vscode) if it does not exists yet.
    - Fetch the repo otherwise if it already exists.
  - Applies the patches on top of the cloned repo using the Simple Patch Manager.
- Proceed with the usual [VSCode's build instructions](https://github.com/microsoft/vscode/wiki/How-to-Contribute).

## Packaging Instructions

The script to create the release package is located in `packaging/package-vscode.sh`. **This script only runs on arm64 version of macOS** and will generate these packages:

- Visual Studio Code app for macOS arm64.
- Visual Studio Code REH (Remote Extension Host) for the following platforms:
  - macOS arm64
  - Linux x64
  - Linux arm64

Additionally, **this script requires `7z`** to be present to generate zip files.

### Build Prerequisite

In addition to [VSCode's build requirements](https://github.com/microsoft/vscode/wiki/How-to-Contribute), this repo also requires:

- Python 3.8 or newer is required for running the [Simple Patch Manager](https://github.com/jamestut/spm).
- The [zsh shell](https://www.zsh.org) and [curl](https://curl.se) is required for running `build-repo.sh`.
- For creating packages, the `7z` tool is required.
