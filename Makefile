# Build and install tdb from this checkout.
#
# `make install` prefers uv (an isolated tool install) and falls back to
# pip --user. Both put the `tdb` executable in ~/.local/bin.

PYTHON ?= python3
BIN_DIR ?= $(HOME)/.local/bin

.PHONY: help install reinstall uninstall check

help:
	@printf '%s\n' \
	  'Targets:' \
	  '  make install    Install tdb into $(BIN_DIR) (uv preferred, pip fallback)' \
	  '  make reinstall  Uninstall and install again' \
	  '  make uninstall  Remove the tdb tool and its executables' \
	  '  make check      Show the installed tdb location and tool paths'

install:
	@mkdir -p "$(BIN_DIR)"
	@if command -v uv >/dev/null 2>&1; then \
		echo "Installing with uv (editable) into $(BIN_DIR)"; \
		UV_TOOL_BIN_DIR="$(BIN_DIR)" uv tool install --force --editable .; \
	elif command -v pip3 >/dev/null 2>&1 || command -v pip >/dev/null 2>&1; then \
		PIP=$$(command -v pip3 || command -v pip); \
		echo "Installing with $$PIP --user (editable)"; \
		"$$PIP" install --user --upgrade --editable .; \
	else \
		echo "error: neither uv nor pip was found on PATH" >&2; \
		exit 1; \
	fi
	@if [ -x "$(BIN_DIR)/tdb" ]; then \
		echo "Installed: $(BIN_DIR)/tdb"; \
	else \
		echo "warning: $(BIN_DIR)/tdb was not created" >&2; \
	fi
	@case ":$$PATH:" in \
		*":$(BIN_DIR):"*) ;; \
		*) echo "warning: $(BIN_DIR) is not on PATH; add it to use tdb" >&2 ;; \
	esac

reinstall: uninstall install

uninstall:
	@if command -v uv >/dev/null 2>&1; then \
		uv tool uninstall textual-debugger >/dev/null 2>&1 || true; \
	fi
	@if command -v pip3 >/dev/null 2>&1 || command -v pip >/dev/null 2>&1; then \
		PIP=$$(command -v pip3 || command -v pip); \
		"$$PIP" uninstall -y textual-debugger >/dev/null 2>&1 || true; \
	fi
	@echo "tdb uninstalled"

check:
	@command -v tdb || true
	@tdb --info
