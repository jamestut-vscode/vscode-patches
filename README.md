# James' Visual Studio Code

This fork contains my personal modifications to Visual Studio Code that are not approved by upstream maintainers.

## Changes Made

- **Updated built-in terminal.**  
  The built-in terminal now uses my own [xterm.js fork](https://github.com/jamestut/xterm.js). The differences are described there.
- **Enable proposed API for all extensions.**  
  All extensions can now use proposed APIs without having to run this version of VSCode with a special command line argument.
- **Reduced remote reconnecting timeout.**  
  When connection to remote fails, immediately shows the dialog that prompts user to reconnect or reload window. When reconnecting, connection timeout (initial TCP handshake) is reduced to just 3 seconds instead of 40 seconds.

## Build Instructions

- Run `build-repo.sh`. Running this script will perform these steps:
  - Download the latest version of my [Simple Patch Manager](https://github.com/jamestut/spm) script.
  - Clone the original [VSCode repo](https://github.com/microsoft/vscode) if it does not exists yet.
    - Fetch the repo otherwise if it already exists.
  - Applies the patches on top of the cloned repo using the Simple Patch Manager.
- Proceed with the usual [VSCode's build instructions](https://github.com/microsoft/vscode/wiki/How-to-Contribute).

### Build Prerequisite

In addition to [VSCode's build requirements](https://github.com/microsoft/vscode/wiki/How-to-Contribute), this repo also requires:

- Python 3.8 or newer is required for running the [Simple Patch Manager](https://github.com/jamestut/spm).
- The [zsh shell](https://www.zsh.org) and [curl](https://curl.se) is required for running `build-repo.sh`.
