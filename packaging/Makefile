SHELL := /usr/bin/env zsh
.SECONDEXPANSION:

LINUX_PLATFORMS := linux-arm64 linux-x64
REH_PLATFORMS := darwin-arm64 $(LINUX_PLATFORMS)

BASE_COMMIT := $(shell scripts/get-base-commit.sh)
MACOS_DOTAPP_NAME := $(shell scripts/get-app-name.py)

alltargets: $$(LINUX_REH_TARGETS) $$(MACOS_ARCHIVE_TARGETS)

# basic folders
work out:
	mkdir $@

# base macOS targets
MACOS_APP_TARGET_NAME := VSCode-darwin-arm64
MACOS_APP_TARGET_UNPACKED := $(addprefix ../, $(MACOS_APP_TARGET_NAME))
MACOS_APP_TARGET_IND := $(MACOS_APP_TARGET_UNPACKED)/built
MACOS_APP_TARGET_ARCHIVE := $(addprefix out/, $(addsuffix .zip, $(MACOS_APP_TARGET_NAME)))
MACOS_REH_TARGET_NAME := vscode-reh-darwin-arm64
MACOS_REH_TARGET_UNPACKED := $(addprefix ../, $(MACOS_REH_TARGET_NAME))
MACOS_REH_TARGET_IND := $(MACOS_REH_TARGET_UNPACKED)/bin/code-server-oss
MACOS_REH_TARGET_ARCHIVE := $(addprefix out/, $(addsuffix .zip, $(MACOS_REH_TARGET_NAME)))
MACOS_UNPACKED_TARGETS := $(MACOS_REH_TARGET_UNPACKED) $(MACOS_APP_TARGET_UNPACKED)
MACOS_ARCHIVE_TARGETS := $(MACOS_REH_TARGET_ARCHIVE) $(MACOS_APP_TARGET_ARCHIVE)

# official release REH download
REL_REH_WORKDIR := rel-reh/$(BASE_COMMIT)
REL_REH_CHANNEL := stable
REL_REH_TARGETS := $(addsuffix .tgz, $(addprefix $(REL_REH_WORKDIR)/vscode-server-, $(REH_PLATFORMS)))

$(REL_REH_WORKDIR)/vscode-server-%.tgz:
	mkdir -p $(REL_REH_WORKDIR)
	curl -L https://update.code.visualstudio.com/commit:$(BASE_COMMIT)/server-$*/$(REL_REH_CHANNEL) > $@

# Linux REH
LINUX_REH_TARGETS := $(addprefix out/vscode-reh-, $(addsuffix .zip, $(LINUX_PLATFORMS)))
out/vscode-reh-%.zip: $(REL_REH_WORKDIR)/vscode-server-%.tgz $(MACOS_REH_TARGET_IND)
	scripts/package-linux-reh.sh $(MACOS_REH_TARGET_UNPACKED) $< $@

# build VSCode
# add app bundle as dependency of REH so that the build is serialised
# we can't guarantee correctness if the builds are running in parallel
$(MACOS_REH_TARGET_IND): | $(MACOS_APP_TARGET_IND)
	scripts/build-vscode.sh ../vscode reh

$(MACOS_REH_TARGET_UNPACKED): $(MACOS_REH_TARGET_IND)

$(MACOS_APP_TARGET_IND): | .signenv work out
	scripts/build-vscode.sh ../vscode app
	scripts/sign-vscode.sh $(dir $@)
	touch $@

$(MACOS_APP_TARGET_UNPACKED): $(MACOS_APP_TARGET_IND)

# macOS archives
$(MACOS_REH_TARGET_ARCHIVE): $(MACOS_REH_TARGET_IND)
	scripts/create-archive.sh $(MACOS_REH_TARGET_UNPACKED) $@

$(MACOS_APP_TARGET_ARCHIVE): $(MACOS_APP_TARGET_IND)
	scripts/create-archive.sh "$(dir $<)/$(MACOS_DOTAPP_NAME)" $@

# begin phony rules
.PHONY: clean alltargets

clean:
	@echo "Cleaning build artefacts and working files"
	rm -rf work out
	rm -rf $(MACOS_UNPACKED_TARGETS)

.PRECIOUS: $(REL_REH_TARGETS)
