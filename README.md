# James' Visual Studio Code

This repository contains my personal modifications to Visual Studio Code, particularly tailored to significantly enhance the remote development experience. Additionally, it includes numerous quality-of-life improvements that cannot be implemented as an extension and are not approved by the upstream maintainers.

Starting from `1.85.0-m2`, the released packages have additional private patches that are not in this public repository. Prerelease packages will have less optimization for their JavaScript code compared to the release version.

## Remote Development

Remote development is natively supported on this project, eliminating the need for additional extensions. Simply execute the REH component of this project on the remote computer you intend to use for development. Then, connect using one of the **REH Connector** commands from the command palette. For more detailed information on its usage, refer to [this document](https://github.com/jamestut-vscode/vscode-remote-resolver).

Some notable improvements to the remote development capabilities are:

- **Session persistence.**  
  The remote component of this project operates independently on the remote computer. Therefore, There is no need to reload your remote workspace's window after a disruption to the network's connectivity as all sessions are persisted.
- **Instant reconnection.**  
  Using operating system's native communication primitives instead of Chromium's, instantenous and reliable reconnection can be achieved.
- **User interface optimized for reconnection.**  
  The user interface is optimized for this project's remote development capabilities. Reconnection prompts are now minimal and do not steal focus.
- **Multiple transport method.**  
  It is possible to connect to the REH using several different connection methods. Refer to [this document](https://github.com/jamestut-vscode/vscode-remote-resolver) for more details.

## Other Changes

- **Updated built-in terminal.**  
  The built-in terminal uses [my fork of xterm.js](https://github.com/jamestut/xterm.js). The differences are described there.
- **Enable proposed API for all extensions.**  
  All extensions can now use proposed APIs without having to run this version of VSCode with a special command line argument.
- **Increase input polling to max 250 Hz.**  
  The maximum input polling rate has been increased to 250 Hz (up from 120 Hz previously). However, this change only affects the maximum polling rate; if your device has a 120 Hz display, it will still be capped at 120 Hz.
- **Non intrusive autocomplete.**  
  Just type or copy-paste the file or folder path you want to open, even on high latency connections to Remote Extension Host! The auto-complete feature won't interfere with what you've already typed or pasted!
- **No automatic expansion of minimized editor group**  
  When an editor group is at its minimum size, focusing on it won't automatically expand it.
- **Unified recently opened list**  
  The "recently opened" list is unified across all remotes. Selecting an item from that list will open it in the current window.
- **Allow extensions to access large files**  
  Extensions can now access large files. Enable the **Large File Sync** settings to activate this feature.
- **Server Daemon Support.**  
  Simply add the `--daemonize` option to start the REH server as a daemon.

## Build Instructions

This repo assumes that the host system is macOS arm64. Follow these instructions:

- Ensure that either Xcode or Command Line Developer Tools are installed.
- Recursive clone this repository so that the [`spm`](https://github.com/jamestut/spm) repo is cloned. If the repo is already shallow-cloned, run `git submodule --init --recursive` so that the `spm` repo is updated.
- Run `build-repo.sh`. Running this script will perform these steps:
  - Clone the original [VSCode repo](https://github.com/microsoft/vscode) if it does not exists yet.
    - Fetch the repo otherwise if it already exists.
  - Applies the patches on top of the cloned repo using the Simple Patch Manager.
- Proceed with the usual [VSCode's build instructions](https://github.com/microsoft/vscode/wiki/How-to-Contribute).

## Packaging Instructions

Packaging this project also requires additional dependencies:

- [Ninja build](https://github.com/ninja-build/ninja/releases)
- [Python](https://www.python.org/downloads/macos) 3.12 or newer  
  As of macOS 15, system Python version is 3.9, hence a newer Python version must be installed. Ensure that the `python3` binary from the official installer takes precedence over system's Python.
- [Podman](https://podman.io)  
  Podman is optional. It is required to run GNU binutils to strip ELF binaries in the derived Linux binaries.

As an alternative to installing those dependencies manually, macOS package managers such as [Homebrew](https://brew.sh) can be used instead.

The scripts to create the release packages are located in the `scripts` folder. After all the above dependencies are satisfied, the following scripts can be used.

The `njgen.py` will generate a ninja build script in `work/packaging` directory. Invoke `ninja` in that directory to generate these packages:

- Visual Studio Code app for macOS arm64.
- Visual Studio Code REH (Remote Extension Host) for macOS arm64.

After the above packages are built, the `derivedreh.py` will generate these additional REH packages:

- GNU/Linux arm64
- Alpine/musl Linux arm64
- GNU/Linux x64
- Legacy GNU/Linux x64 (Enterprise Linux 7, Ubuntu 18.04, etc.)
- Alpine/musl Linux x64

The `cleanpackaging.sh` can be used to clean all artefacts (including intermediate files) generated by those two scripts.
