# Contributing to injector-autowired

Thanks for your interest in improving `injector-autowired`. This guide covers
local setup, testing, and the checks a change should pass.

## Dev setup

We recommend [`uv`](https://docs.astral.sh/uv/) for dependency and environment
management. The Makefile wraps everything else.

```bash
git clone https://github.com/tylersuehr7/injector-autowired
cd injector-autowired
make install   # creates .venv, installs the package + dev extras
```

Without `uv`:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Running the checks

```bash
make test        # pytest
make lint        # ruff check
make format      # ruff format + fix
make typecheck   # mypy
make cov         # tests with coverage report
```

Every test runs in isolation — the autouse fixture in `tests/conftest.py`
clears the process-wide registry around each test. When you need a scan test to
re-run the decorators, evict the fixture package from `sys.modules` first (see
`tests/test_scan.py`).

## Coding conventions

- The core has one runtime dependency: `injector`. Keep it that way.
- Public API needs docstrings and type annotations; `make typecheck` must be clean.
- Prefer the `Scope` enum over raw scope strings in code and docs.
- New behavior needs tests and a `CHANGELOG.md` entry under `[Unreleased]`.

## PR checklist

- [ ] `make test` passes
- [ ] `make lint` clean
- [ ] `make typecheck` clean
- [ ] New public API has docstrings and tests
- [ ] `CHANGELOG.md` updated under `[Unreleased]`
