"""Pure complete inspection of supplied attribution at an exact review value."""

import json
from typing import cast

from faultatlas.assessment_review import inspect_assessment_reviews
from faultatlas.domain.assessment_review import SuppliedAssessmentReview
from faultatlas.domain.assessment_review_attribution import (
    SuppliedAssessmentReviewAttribution,
)

__all__ = ["inspect_assessment_review_attributions"]

_MAX_VIEW_BYTES = 9 * 1024 * 1024


def _quoted(value: object) -> str:
    return json.dumps(value, ensure_ascii=True, separators=(",", ":")).replace(
        "\x7f", "\\u007f"
    )


def inspect_assessment_review_attributions(
    review: SuppliedAssessmentReview,
    attributions: tuple[SuppliedAssessmentReviewAttribution, ...],
) -> str:
    """Return all declarations in order, without inferring identity or support."""
    if not isinstance(cast(object, review), SuppliedAssessmentReview):
        raise ValueError("review must be a SuppliedAssessmentReview")
    if type(cast(object, attributions)) is not tuple:
        raise ValueError("attributions must be a tuple")
    if len(attributions) > 8:
        raise ValueError(
            "attributions must contain at most 8 supplied attribution declarations"
        )
    requested = SuppliedAssessmentReview.model_validate(review)
    validated: list[SuppliedAssessmentReviewAttribution] = []
    for index, assertion in enumerate(attributions):
        if not isinstance(cast(object, assertion), SuppliedAssessmentReviewAttribution):
            raise ValueError(
                f"attribution at index {index} must be a SuppliedAssessmentReviewAttribution"
            )
        value = SuppliedAssessmentReviewAttribution.model_validate(assertion)
        if value.review != requested:
            raise ValueError(
                f"attribution at index {index} target does not match requested review"
            )
        validated.append(value)

    prefix = (
        "Supplied review attributions - non-authoritative inspection\n"
        "Complete review value:\n"
        + inspect_assessment_reviews(requested.assessment, (requested,))
    )
    lines = [f"Attribution declarations: {len(validated)}"]
    if not validated:
        lines.append("Attributions: none supplied; no reviewer inferred")
    else:
        lines.append(
            "Attribution targets: all declarations match the complete requested review value"
        )
    for index, assertion in enumerate(validated, 1):
        lines.extend(
            [
                f"Attribution {index}",
                "Attribution assertion supplier: "
                + _quoted(assertion.attribution.supplier),
                "Attribution assertion rationale: "
                + _quoted(assertion.attribution.rationale),
                "Attributed reviewer: "
                + (
                    "explicitly unknown"
                    if assertion.reviewer is None
                    else _quoted(assertion.reviewer)
                ),
                "Source record association: "
                + (
                    "none supplied; availability not asserted"
                    if assertion.source is None
                    else _quoted(assertion.source.model_dump(mode="json"))
                ),
            ]
        )
    lines.extend(
        [
            "Attribution labels are supplied claims; account identity, authorship and independence are not verified.",
            "Source records are associated by declaration; bytes are not retrieved or verified as support.",
            "Equality identifies the supplied review value, not a particular repeated occurrence.",
            "No availability status, approval, confidence or review lifecycle is inferred.",
            "End of complete review attribution view",
        ]
    )
    view = prefix + "\n".join(lines) + "\n"
    if len(view.encode("utf-8")) > _MAX_VIEW_BYTES:
        raise ValueError(
            "P09 review attribution inspection output budget exceeded (9 MiB)"
        )
    return view
