# FaultAtlas

FaultAtlas is a governed contract prototype for fault-analysis evidence. It models
supplied evidence, reusable patterns/invariants and attributed assessments. The CLI
inspects a selected assessment file and saves canonical JSON under a selected new
name. Supplied opinions remain claims, not applicability or repair certification.

See the [complete CLI example and limits](docs/contracts/s1-p08-s03-assessment-cli.md),
[S01 supplied model](docs/contracts/s1-p08-s01-supplied-assessment.md),
[S02 selected-file API](docs/contracts/s1-p08-s02-assessment-file.md), and
[project roadmap](docs/roadmap.md). Selected file operations require the supported
Linux/ext4 backend and private caller-owned paths. General persistence, ingestion,
retrieval, model routing and automated applicability are not implemented.

The [bounded P08 closure entry](docs/roadmap.md#s1p08-bounded-dispositions)
links the primary JSON and readable view, records the delivered supplied-model,
file and CLI integration, and retains the
original empirical/provider limitations. Structural success is not authenticated
authorship, evidence support, verified transfer or repair correctness. P09 requires
a separate product/architecture planning discussion.

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
uv run --frozen faultatlas assessment --help
```

## Validation

```bash
uv run --frozen ruff format --check .
uv run --frozen ruff check .
uv run --frozen pyright
uv run --frozen pytest
uv build
```
