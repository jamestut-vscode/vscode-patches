SHELL := /usr/bin/env zsh
.SECONDEXPANSION:

LINUX_PLATFORMS := linux-legacy-arm64 linux-legacy-x64 linux-arm64 linux-x64 alpine-arm64 linux-alpine

BASE_COMMIT := $(shell scripts/get-base-commit.sh)
MACOS_DOTAPP_NAME := $(shell scripts/get-app-name.py)

alltargets: $$(LINUX_REH_TARGETS) $$(MACOS_ARCHIVE_TARGETS)

# basic folders
work out:
	mkdir $@

# npm dependencies
VSCODE_REPO_BASE := ../vscode
NPM_DEP_IND := $(VSCODE_REPO_BASE)/npm-ran

# base macOS targets
MACOS_APP_TARGET_NAME := VSCode-darwin-arm64
MACOS_APP_TARGET_UNPACKED := $(addprefix ../, $(MACOS_APP_TARGET_NAME))
MACOS_APP_TARGET_IND := $(MACOS_APP_TARGET_UNPACKED)/built
MACOS_APP_TARGET_SIGN_IND := $(MACOS_APP_TARGET_UNPACKED)/signed
MACOS_APP_TARGET_ARCHIVE := $(addprefix out/, $(addsuffix .zip, $(MACOS_APP_TARGET_NAME)))
MACOS_REH_TARGET_NAME := vscode-reh-darwin-arm64
MACOS_REH_TARGET_UNPACKED := $(addprefix ../, $(MACOS_REH_TARGET_NAME))
MACOS_REH_TARGET_IND := $(MACOS_REH_TARGET_UNPACKED)/bin/code-server-oss
MACOS_REH_TARGET_ARCHIVE := $(addprefix out/, $(addsuffix .zip, $(MACOS_REH_TARGET_NAME)))
LINUX_REH_TARGET_NAME := vscode-reh-linux-arm64
LINUX_REH_TARGET_UNPACKED := $(addprefix ../, $(LINUX_REH_TARGET_NAME))
LINUX_REH_TARGET_IND := $(LINUX_REH_TARGET_UNPACKED)/bin/code-server-oss
UNPACKED_TARGETS := $(MACOS_REH_TARGET_UNPACKED) $(MACOS_APP_TARGET_UNPACKED) $(LINUX_REH_TARGET_UNPACKED)
MACOS_ARCHIVE_TARGETS := $(MACOS_REH_TARGET_ARCHIVE) $(MACOS_APP_TARGET_ARCHIVE)

# official release REH download
REL_REH_WORKDIR := rel-reh/$(BASE_COMMIT)
REL_REH_CHANNEL := stable
REL_REH_TARGETS := $(addsuffix .tgz, $(addprefix $(REL_REH_WORKDIR)/vscode-server-, $(LINUX_PLATFORMS)))

$(REL_REH_WORKDIR)/vscode-server-%.tgz:
	mkdir -p $(REL_REH_WORKDIR)
	curl -L https://update.code.visualstudio.com/commit:$(BASE_COMMIT)/server-$*/$(REL_REH_CHANNEL) > $@

# Linux REH
LINUX_REH_TARGETS := $(addprefix out/vscode-reh-, $(addsuffix .zip, $(LINUX_PLATFORMS)))
out/vscode-reh-%.zip: $(REL_REH_WORKDIR)/vscode-server-%.tgz $(LINUX_REH_TARGET_IND) | work out
	scripts/package-linux-reh.sh $(LINUX_REH_TARGET_UNPACKED) $< $@

# build VSCode
$(NPM_DEP_IND):
	cd ../vscode; npm install
	touch $@

$(MACOS_REH_TARGET_IND): $(NPM_DEP_IND)
	scripts/build-vscode.sh ../vscode reh

$(MACOS_REH_TARGET_UNPACKED): $(MACOS_REH_TARGET_IND)

$(LINUX_REH_TARGET_IND): $(NPM_DEP_IND)
	scripts/build-vscode.sh ../vscode linux-reh

$(LINUX_REH_TARGET_UNPACKED): $(LINUX_REH_TARGET_IND)

$(MACOS_APP_TARGET_IND): $(NPM_DEP_IND)
	scripts/build-vscode.sh ../vscode app
	touch $@

$(MACOS_APP_TARGET_SIGN_IND): .signenv | $(MACOS_APP_TARGET_IND)
	scripts/sign-vscode.sh $(dir $@)
	touch $@

$(MACOS_APP_TARGET_UNPACKED): $(MACOS_APP_TARGET_SIGN_IND)

# macOS archives
$(MACOS_REH_TARGET_ARCHIVE): $(MACOS_REH_TARGET_IND) | out
	scripts/create-archive.sh $(MACOS_REH_TARGET_UNPACKED) $@

$(MACOS_APP_TARGET_ARCHIVE): $(MACOS_APP_TARGET_UNPACKED) | out
	scripts/create-archive.sh "$</$(MACOS_DOTAPP_NAME)" $@

# avoid parallelism on these targets, otherwise results will be incorrect
.NOTPARALLEL:

# begin phony rules
.PHONY: clean alltargets

clean:
	@echo "Cleaning build artefacts and working files"
	rm -rf work out
	rm -rf $(UNPACKED_TARGETS)

.PRECIOUS: $(REL_REH_TARGETS)
