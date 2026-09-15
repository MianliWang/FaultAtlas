"""Supplied attribution assertions about one complete review judgment.

Reviewer labels and offered record references establish no identity, authorship,
source access, availability or support. The original review remains unchanged.
"""

import json
from typing import Annotated

from pydantic import (
    AfterValidator,
    BaseModel,
    BeforeValidator,
    ConfigDict,
    StringConstraints,
    ValidationInfo,
)

from faultatlas.domain.assessment import AssessmentAttribution
from faultatlas.domain.assessment_review import SuppliedAssessmentReview
from faultatlas.domain.evidence import DurableEvidenceRecordReference

__all__ = ["SuppliedAssessmentReviewAttribution"]


def _label(value: str) -> str:
    if not value.strip():
        raise ValueError("reviewer must not be whitespace-only")
    value.encode("utf-8")
    return value


_Reviewer = Annotated[
    str, StringConstraints(min_length=1, max_length=128), AfterValidator(_label)
]


def _review(value: object, info: ValidationInfo) -> object:
    if info.mode == "json" and isinstance(value, dict):
        return SuppliedAssessmentReview.model_validate_json(
            json.dumps(value, allow_nan=False)
        )
    if not isinstance(value, SuppliedAssessmentReview):
        raise ValueError("review requires its declared typed Python child")
    return value


def _source(value: object, info: ValidationInfo) -> object:
    if (
        info.mode == "python"
        and value is not None
        and not isinstance(value, DurableEvidenceRecordReference)
    ):
        raise ValueError("source requires its declared typed Python child")
    return value


def _attribution(value: object, info: ValidationInfo) -> object:
    if info.mode == "python" and not isinstance(value, AssessmentAttribution):
        raise ValueError("attribution requires its declared typed Python child")
    return value


class SuppliedAssessmentReviewAttribution(BaseModel):
    """Value-bound supplied attribution, without occurrence or actor identity."""

    model_config = ConfigDict(
        frozen=True,
        strict=True,
        extra="forbid",
        revalidate_instances="always",
        validate_default=True,
    )

    review: Annotated[SuppliedAssessmentReview, BeforeValidator(_review)]
    reviewer: _Reviewer | None
    source: Annotated[DurableEvidenceRecordReference | None, BeforeValidator(_source)]
    attribution: Annotated[AssessmentAttribution, BeforeValidator(_attribution)]
