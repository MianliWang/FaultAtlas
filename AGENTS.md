# FaultAtlas repository guidance

FaultAtlas uses Python 3.13, a repository-local `.venv`, and uv as the only
project environment and dependency manager. Keep implementation small,
deterministic, offline at test time, and limited to the active gate.

## Gate workflow

- Gate 0 — Orient: inspect the repository, environment, and upstream state.
  This gate is read-only.
- Gate 1 — Plan: define the intended behavior, exact version-controlled file
  allowlist, validation commands, and stop conditions. This gate is read-only.
- Gate 2 — Implement: change only the approved allowlist, maintain dependencies
  and `uv.lock` with uv, and run focused validation before full validation.
- Gate 3 — Publish: stage, commit, push, or open a pull request only when the
  user explicitly authorizes those operations.

## Current Gate 2 allowlist

Only these version-controlled paths may change:

```text
AGENTS.md
.github/workflows/ci.yml
.gitignore
.python-version
README.md
pyproject.toml
uv.lock
src/faultatlas/__init__.py
src/faultatlas/__main__.py
src/faultatlas/cli.py
tests/test_package.py
tests/test_cli.py
```

Do not create speculative modules or future product surfaces. Do not stage or
publish Gate 2 work.

## Stop conditions

Stop and report instead of expanding scope when:

- the baseline, branch, or owned working-tree state is unexpected;
- a required change falls outside the exact allowlist;
- dependency resolution requires an unapproved package, private index,
  credentials, Conda, system-package installation, or system Python mutation;
- validation exposes a failure that cannot be fixed inside the approved scope;
- a command would disclose secrets or perform a write reserved for Gate 3.

Never weaken validation or edit `uv.lock` by hand to force a passing result.
