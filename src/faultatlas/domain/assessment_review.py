"""A supplied review declaration bound to one complete assessment value.

Scope declares examination; attribution labels the supplied record. Neither
establishes coverage, reviewer identity, authority, freshness or support.
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

from faultatlas.domain.assessment import AssessmentAttribution, SuppliedAssessment

__all__ = ["SuppliedAssessmentReview"]


def _text(value: str) -> str:
    if not value.strip():
        raise ValueError("text must not be whitespace-only")
    value.encode("utf-8")
    return value


_Text = Annotated[
    str, StringConstraints(min_length=1, max_length=4096), AfterValidator(_text)
]


def _assessment(value: object, info: ValidationInfo) -> object:
    if info.mode == "json" and isinstance(value, dict):
        # Preserve the public child's JSON language, including ordered arrays.
        return SuppliedAssessment.model_validate_json(
            json.dumps(value, allow_nan=False)
        )
    if not isinstance(value, SuppliedAssessment):
        raise ValueError("assessment requires its declared typed Python child")
    return value


def _attribution(value: object, info: ValidationInfo) -> object:
    if info.mode == "python" and not isinstance(value, AssessmentAttribution):
        raise ValueError("attribution requires its declared typed Python child")
    return value


class SuppliedAssessmentReview(BaseModel):
    """Opaque supplied judgment of a full target, without a review lifecycle."""

    model_config = ConfigDict(
        frozen=True,
        strict=True,
        extra="forbid",
        revalidate_instances="always",
        validate_default=True,
    )

    assessment: Annotated[SuppliedAssessment, BeforeValidator(_assessment)]
    scope: _Text
    judgment: _Text
    attribution: Annotated[AssessmentAttribution, BeforeValidator(_attribution)]
