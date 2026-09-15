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
authorship, evidence support, verified transfer or repair correctness. P09 provides
the bounded library review below; its remaining scope requires separate planning.

## Supplied assessment reviews

Given an existing typed `SuppliedAssessment`, supply a review and inspect the
complete target and all review declarations:

```python
from faultatlas.assessment_review import inspect_assessment_reviews
from faultatlas.domain.assessment import AssessmentAttribution, SuppliedAssessment
from faultatlas.domain.assessment_review import SuppliedAssessmentReview


def review_view(assessment: SuppliedAssessment) -> str:
    review = SuppliedAssessmentReview(
        assessment=assessment,
        scope="Only the supplied condition inventory was examined.",
        judgment="Unknown: no independent material access is claimed.",
        attribution=AssessmentAttribution(
            supplier="Record supplier",
            rationale="The attributed reviewer identity is not established.",
        ),
    )
    return inspect_assessment_reviews(assessment, (review,))
```

The [review contract](docs/contracts/s1-p09-s01-supplied-review.md) defines full
target matching, declared scope and supplied attribution. Up to 32 records retain
their order and duplicates. Inspection does not verify coverage, referenced
material access, reviewer identity, freshness or approval. These library values
do not add reviews to the selected assessment file format or CLI.

## Supplied review attribution

For an existing review, supply a separate attribution declaration:

```python
from faultatlas.assessment_review_attribution import inspect_assessment_review_attributions
from faultatlas.domain.assessment import AssessmentAttribution
from faultatlas.domain.assessment_review import SuppliedAssessmentReview
from faultatlas.domain.assessment_review_attribution import SuppliedAssessmentReviewAttribution


def attribution_view(review: SuppliedAssessmentReview) -> str:
    declaration = SuppliedAssessmentReviewAttribution(
        review=review,
        reviewer=None,
        source=None,
        attribution=AssessmentAttribution(
            supplier="Attribution supplier",
            rationale="The reviewer is unknown; no source record is supplied.",
        ),
    )
    return inspect_assessment_review_attributions(review, (declaration,))
```

The [attribution contract](docs/contracts/s1-p09-s02-review-attribution.md)
separates the existing review supplier, new assertion supplier and attributed
reviewer label. It accepts up to eight declarations, preserves competing and
duplicate records, and matches the complete review value. An optional source is
a complete supplied evidence-record reference; it is not loaded or verified as
support. Unknown reviewer, missing source association and unavailable source
bytes are distinct concepts. No account identity, source-availability verdict,
authentication, confidence or lifecycle is inferred.

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
