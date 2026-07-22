# FaultAtlas

FaultAtlas is an early governed contract prototype for reliable fault-analysis
evidence. Its current product-domain capability is limited to the provisional
internal `SourceLocator` and `ArtifactSnapshot` models. The command-line
interface currently provides only help and version behavior.

FaultAtlas does not yet implement source ingestion, persistence, retrieval,
graphs, RAG, model routing, or artifact generation. See the
[project roadmap](docs/roadmap.md) for the authoritative current status and
Stage numbering.

## Requirements

- WSL or Linux (the canonical development workflow is VS Code/Codex in WSL)
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
