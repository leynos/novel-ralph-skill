MDLINT ?= markdownlint-cli2
# `make fmt` and `make check-fmt` call mdtablefix directly. `--git` selects the
# Markdown files Git tracks and `--include-untracked` adds the untracked files
# Git does not ignore, so a new document is formatted before it is staged.
# Both modes need mdtablefix 0.6.1 or later; CI pins the version at the
# install-mdtablefix step.
MDTABLEFIX ?= mdtablefix
MDTABLEFIX_SELECT = --git --include-untracked
MDTABLEFIX_RULES = --wrap --renumber --breaks --ellipsis --fences
NIXIE ?= nixie
export PATH := $(HOME)/.local/bin:$(HOME)/.bun/bin:$(PATH)
# Every uv call goes through the vendored helper, which cleans the environment,
# uses the global uv cache, runs offline first and goes online at most once. See
# https://github.com/leynos/shared-actions/tree/main/uv_gate for the contract.
UV_GATE ?= python3 scripts/uv_gate.py
UV ?= $(shell command -v uv 2>/dev/null || printf '%s/.local/bin/uv' "$$HOME")
# The helper finds uv on PATH, so a caller's UV=/path/to/uv is honoured by putting
# that uv's directory first on PATH for every recipe.
export PATH := $(if $(findstring /,$(UV)),$(patsubst %/,%,$(dir $(UV))):)$(PATH)
USER_CARGO := $(HOME)/.cargo/bin/cargo
USER_WHITAKER := $(HOME)/.local/bin/whitaker
USER_BIN_PATH := $(HOME)/.cargo/bin:$(HOME)/.local/bin:$(HOME)/.bun/bin
TOOLS = $(MDLINT)
VENV_TOOLS = pytest
export PYO3_USE_ABI3_FORWARD_COMPATIBILITY := 1
WITH_ACT ?= 0
ACT_TEST_ENV = $(if $(filter 1 true yes on,$(WITH_ACT)),RUN_ACT_VALIDATION=1,)
PYTEST_XDIST_WORKERS ?= auto
PYTHON_TARGETS ?= novel_ralph_skill tests
PYLINT_PYTHON ?= pypy@3.12
PYLINT_VERSION ?= 4.0.9
PYLINT_TARGETS ?= $(PYTHON_TARGETS)
PYLINT = $(UV_GATE) tool --managed-python --python $(PYLINT_PYTHON) --from 'pylint==$(PYLINT_VERSION)' -- pylint

# why: git worktree/checkout/rebase rewrites source-file mtimes, which can make a
# stale timestamp-validated __pycache__/*.pyc in the tracked tree compare as
# fresh; CPython then imports old bytecode under the editable install (observed
# once as a wide first-run envelope field-order failure that healed on later
# runs). Purging tracked-tree bytecode caches in `build` settles the editable
# install so `test` always imports the source as written. Scoped to
# $(PYTHON_TARGETS); never touches .venv or the uv cache.
PURGE_TREE_BYTECODE = $(UV_GATE) run -- python -c "import pathlib, shutil, sys; [shutil.rmtree(d, ignore_errors=True) for t in sys.argv[1:] for d in pathlib.Path(t).rglob('__pycache__')]" $(PYTHON_TARGETS)


.PHONY: prepare help all audit clean build build-release lint lint-python fmt check-fmt \
        markdownlint spelling nixie test typecheck $(TOOLS) $(VENV_TOOLS)

prepare: ## Install the locked development environment, offline first
	$(UV_GATE) prepare --group dev

.DEFAULT_GOAL := all

all: build check-fmt lint typecheck test spelling

define ensure_uv
	@command -v $(UV) >/dev/null 2>&1 || { \
	  printf "Error: uv is required, but '%s' was not found or is not executable\n" "$(UV)" >&2; \
	  exit 1; \
	}
endef

.venv: pyproject.toml
	$(call ensure_uv)

build: .venv prepare ## Build virtual-env and install deps
	$(PURGE_TREE_BYTECODE)

build-release: prepare ## Build artefacts (sdist & wheel)
	$(call ensure_uv)
	$(UV_GATE) run -- python -m build --sdist --wheel

clean: ## Remove build artifacts
	rm -rf build dist *.egg-info \
	  .mypy_cache .pytest_cache .coverage coverage.* \
	  lcov.info htmlcov .venv .uv-cache .uv-tools
	find . -type d -name '__pycache__' -print0 | xargs -0 -r rm -rf
	rm -f .typos-oxendict-base.json .typos-oxendict-base.toml

define ensure_tool
	@command -v $(1) >/dev/null 2>&1 || { \
	  printf "Error: '%s' is required, but not installed\n" "$(1)" >&2; \
	  exit 1; \
	}
endef

define ensure_tool_venv
	@$(UV_GATE) run -- which $(1) >/dev/null 2>&1 || { \
	  printf "Error: '%s' is required in the virtualenv, but is not installed\n" "$(1)" >&2; \
	  exit 1; \
	}
endef

ifneq ($(strip $(TOOLS)),)
$(TOOLS): ## Verify required CLI tools
	$(call ensure_tool,$@)
endif


ifneq ($(strip $(VENV_TOOLS)),)
.PHONY: $(VENV_TOOLS)
$(VENV_TOOLS): build ## Verify required CLI tools in venv
	$(call ensure_tool_venv,$@)
endif


fmt: build ## Format sources
	$(UV_GATE) run -- ruff format $(PYTHON_TARGETS)
	$(UV_GATE) run -- ruff check --select I --fix $(PYTHON_TARGETS)

	$(MDTABLEFIX) --in-place $(MDTABLEFIX_SELECT) $(MDTABLEFIX_RULES)
	$(MDLINT) --fix "**/*.md"

check-fmt: build ## Verify formatting
	$(UV_GATE) run -- ruff format --check $(PYTHON_TARGETS)

	$(MDTABLEFIX) --check $(MDTABLEFIX_SELECT) $(MDTABLEFIX_RULES)

lint: lint-python ## Run linters

lint-python: build ## Run Python linters
	$(UV_GATE) run -- ruff check $(PYTHON_TARGETS)
	$(UV_GATE) run -- interrogate $(PYTHON_TARGETS)
	$(PYLINT) $(PYLINT_TARGETS)


typecheck: build ## Run typechecking
	$(UV_GATE) run -- ty --version
	$(UV_GATE) run -- ty check $(PYTHON_TARGETS)

audit: build ## Audit dependencies for known vulnerabilities
	$(UV_GATE) run -- pip-audit


markdownlint: $(MDLINT) ## Lint Markdown files
	env -u NO_COLOR $(MDLINT) '**/*.md'
	+$(MAKE) spelling

TYPOS_VERSION ?= 1.48.0
TYPOS := $(UV_GATE) tool --from typos@$(TYPOS_VERSION) -- typos

spelling: prepare ## Enforce en-GB-oxendict spelling in Markdown prose
	$(UV_GATE) run -- python scripts/generate_typos_config.py
	find . -type f -name '*.md' -not -path './.venv/*' -print0 | \
		xargs -0 -r $(TYPOS) --config typos.toml --force-exclude

nixie: ## Validate Mermaid diagrams
	$(call ensure_tool,$(NIXIE))
	$(NIXIE) --no-sandbox

test: build $(VENV_TOOLS) ## Run tests
	$(ACT_TEST_ENV) $(UV_GATE) run -- pytest -v -n $(PYTEST_XDIST_WORKERS)


help: ## Show available targets
	@grep -E '^[a-zA-Z_-]+:.*?##' $(MAKEFILE_LIST) | \
	awk 'BEGIN {FS=":.*##"; printf "Available targets:\n"} {gsub(/^[[:space:]]+/, "", $$2); printf "  %-20s %s\n", $$1, $$2}'
