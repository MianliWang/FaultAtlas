"""Complete pure inspection of supplied review declarations at an exact target."""

import json
from typing import cast

from faultatlas.assessment import inspect_assessment
from faultatlas.domain.assessment import SuppliedAssessment
from faultatlas.domain.assessment_review import SuppliedAssessmentReview

__all__ = ["inspect_assessment_reviews"]

_MAX_VIEW_BYTES = 16 * 1024 * 1024


def _quoted(value: str) -> str:
    return json.dumps(value, ensure_ascii=True).replace("\x7f", "\\u007f")


def inspect_assessment_reviews(
    assessment: SuppliedAssessment,
    reviews: tuple[SuppliedAssessmentReview, ...],
) -> str:
    """Inspect supplied records without inferring coverage, identity or authority."""
    if not isinstance(cast(object, assessment), SuppliedAssessment):
        raise ValueError("assessment must be a SuppliedAssessment")
    if type(cast(object, reviews)) is not tuple:
        raise ValueError("reviews must be a tuple")
    if len(reviews) > 32:
        raise ValueError("reviews must contain at most 32 supplied reviews")
    requested = SuppliedAssessment.model_validate(assessment)
    validated: list[SuppliedAssessmentReview] = []
    for index, review in enumerate(reviews):
        if not isinstance(cast(object, review), SuppliedAssessmentReview):
            raise ValueError(
                f"review at index {index} must be a SuppliedAssessmentReview"
            )
        value = SuppliedAssessmentReview.model_validate(review)
        if value.assessment != requested:
            raise ValueError(
                f"review at index {index} target does not match requested assessment"
            )
        validated.append(value)

    prefix = (
        "Supplied assessment reviews - non-authoritative inspection\n"
        "Complete target assessment:\n" + inspect_assessment(requested.basis, requested)
    )
    lines = [f"Supplied review records: {len(validated)}"]
    if not validated:
        lines.append("Reviews: none supplied; no review judgment inferred")
    else:
        lines.append(
            "Review targets: all supplied records match the complete requested assessment value"
        )
    for index, review in enumerate(validated, 1):
        lines.extend(
            [
                f"Review {index}",
                "Supplied scope (coverage declaration only): " + _quoted(review.scope),
                "Supplied judgment: " + _quoted(review.judgment),
                "Supplied record supplier: " + _quoted(review.attribution.supplier),
                "Supplied rationale: " + _quoted(review.attribution.rationale),
            ]
        )
    lines.extend(
        [
            "Scope is supplied prose; structural checks do not verify examination coverage.",
            "Attribution is supplied: the record supplier label need not name the reviewer; "
            "reviewer identity and independence are not established.",
            "Material names in review text are prose; no material selection, access or support is validated.",
            "A matching value does not establish freshness, withdrawal status or later-policy applicability.",
            "No authentication, approval, score, winner, review lifecycle or persistence is inferred.",
            "End of complete review view",
        ]
    )
    view = prefix + "\n".join(lines) + "\n"
    if len(view.encode("utf-8")) > _MAX_VIEW_BYTES:
        raise ValueError("P09 review inspection output budget exceeded (16 MiB)")
    return view
