# FaultAtlas

FaultAtlas is a governed Python foundation for reliable fault-analysis
evidence. The current package intentionally provides only metadata and a
minimal command-line entry point.

## Requirements

- WSL or Linux
- [uv](https://docs.astral.sh/uv/)
- uv-managed CPython 3.13

Conda and system Python are not used for the project environment.

## Setup

From the repository root:

```bash
uv python install 3.13
uv sync --locked --group dev
```

uv creates and maintains the repository-local `.venv` from `uv.lock`.

## CLI

```bash
uv run --frozen faultatlas --help
uv run --frozen faultatlas --version
uv run --frozen python -m faultatlas
```

## Validation

```bash
uv run --frozen ruff format --check .
uv run --frozen ruff check .
uv run --frozen pyright
uv run --frozen pytest
uv build
```
