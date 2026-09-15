"""Authored attribution values and strict public-child boundary checks."""

import copy
import json
from typing import Any

import pytest
from pydantic import ValidationError
from test_supplied_assessment import fields

import faultatlas
import faultatlas.domain as domain_package
import faultatlas.domain.assessment_review_attribution as module
from faultatlas.domain.assessment import AssessmentAttribution
from faultatlas.domain.assessment_review import SuppliedAssessmentReview
from faultatlas.domain.assessment_review_attribution import (
    SuppliedAssessmentReviewAttribution,
)
from faultatlas.domain.evidence import DurableEvidenceRecordReference
from faultatlas.domain.identity import ProviderGlobalId

# Literal design inputs from the accepted packet; never loaded from /tmp at runtime.
REVIEW_WIRE: dict[str, Any] = json.loads(r"""
{
  "assessment": {
    "attribution": {
      "supplier": "Assessment assembler",
      "rationale": "Synthetic assessment."
    },
    "basis": {
      "source": {
        "invariant": "00000000-0000-4000-8000-000000000002",
        "invariant_statement": "An expression is evaluated once."
      },
      "target": {
        "snapshot": {
          "repository": {
            "schema_version": 1,
            "provider": "github",
            "provider_repository_id": "1001"
          },
          "revision": {
            "schema_version": 1,
            "kind": "commit",
            "algorithm": "sha1",
            "full_digest": "1111111111111111111111111111111111111111"
          }
        },
        "declared_host": "github.com",
        "declared_visibility": "public",
        "scope": null
      },
      "context_statement": null,
      "conditions": [],
      "materials": null,
      "material_omission": null
    },
    "opinions": [],
    "conflicts": [],
    "overall_opinion": null
  },
  "scope": "Only the supplied statement was considered.",
  "judgment": "No execution evidence was assessed.",
  "attribution": {
    "supplier": "Review relay",
    "rationale": "Newly authored example judgment; no historical authorship is claimed."
  }
}
""")

DECLARATIONS: list[dict[str, Any]] = json.loads(r"""
[
  {
    "reviewer": "Lin",
    "source": {
      "schema_version": 1,
      "format_name": "attribution-example",
      "format_version": "1",
      "canonicalization": "json-sort-keys-compact-utf8-lf-v1",
      "sha256": "ad9d501dcfe631958d3ea1798db9b01b01783d5c97a46984a06fd926d890f2dd",
      "byte_length": 128
    },
    "attribution": {
      "supplier": "Attribution clerk",
      "rationale": "Fictional example: the supplied judgment is attributed to Lin."
    }
  },
  {
    "reviewer": null,
    "source": null,
    "attribution": {
      "supplier": "Archive clerk",
      "rationale": "No author of this supplied judgment is established; no source record is supplied."
    }
  },
  {
    "reviewer": "Mo",
    "source": null,
    "attribution": {
      "supplier": "Second clerk",
      "rationale": "Competing fictional attribution; no winner is inferred."
    }
  },
  {
    "reviewer": "Lin",
    "source": {
      "schema_version": 1,
      "format_name": "attribution-example",
      "format_version": "1",
      "canonicalization": "json-sort-keys-compact-utf8-lf-v1",
      "sha256": "ad9d501dcfe631958d3ea1798db9b01b01783d5c97a46984a06fd926d890f2dd",
      "byte_length": 128
    },
    "attribution": {
      "supplier": "Attribution clerk",
      "rationale": "Fictional example: the supplied judgment is attributed to Lin."
    }
  }
]
""")


def review_value() -> SuppliedAssessmentReview:
    return SuppliedAssessmentReview.model_validate_json(json.dumps(REVIEW_WIRE))


def assertion_wire(index: int = 0) -> dict[str, Any]:
    return {"review": copy.deepcopy(REVIEW_WIRE), **copy.deepcopy(DECLARATIONS[index])}


def assertion_value(index: int = 0) -> SuppliedAssessmentReviewAttribution:
    return SuppliedAssessmentReviewAttribution.model_validate_json(
        json.dumps(assertion_wire(index))
    )


def test_exact_fields_and_authored_native_json_value() -> None:
    value = assertion_value()
    assert module.__all__ == ["SuppliedAssessmentReviewAttribution"]
    assert tuple(module.SuppliedAssessmentReviewAttribution.model_fields) == (
        "review",
        "reviewer",
        "source",
        "attribution",
    )
    assert value.model_dump(mode="json") == assertion_wire()
    assert SuppliedAssessmentReviewAttribution.model_validate(fields(value)) == value
    assert (
        SuppliedAssessmentReviewAttribution.model_validate_json(value.model_dump_json())
        == value
    )
    assert {
        k: value.model_config.get(k)
        for k in (
            "frozen",
            "strict",
            "extra",
            "revalidate_instances",
            "validate_default",
        )
    } == {
        "frozen": True,
        "strict": True,
        "extra": "forbid",
        "revalidate_instances": "always",
        "validate_default": True,
    }
    for field in module.SuppliedAssessmentReviewAttribution.model_fields.values():
        assert field.is_required()
        assert (
            field.alias is field.validation_alias is field.serialization_alias is None
        )
    with pytest.raises(ValidationError, match="frozen"):
        value.reviewer = "Changed"
    with pytest.raises(ValidationError, match="extra_forbidden"):
        SuppliedAssessmentReviewAttribution.model_validate(
            fields(value) | {"verified": True}
        )
    for package in (faultatlas, domain_package):
        assert not hasattr(package, "SuppliedAssessmentReviewAttribution")


@pytest.mark.parametrize("field", ("review", "reviewer", "source", "attribution"))
def test_nullable_fields_are_still_required(field: str) -> None:
    wire = assertion_wire(1)
    assert SuppliedAssessmentReviewAttribution.model_validate_json(json.dumps(wire))
    del wire[field]
    with pytest.raises(ValidationError) as failure:
        SuppliedAssessmentReviewAttribution.model_validate_json(json.dumps(wire))
    assert failure.value.errors()[0]["loc"] == (field,)
    assert failure.value.errors()[0]["type"] == "missing"


@pytest.mark.parametrize("field", ("review", "attribution"))
def test_nonnullable_children_reject_none(field: str) -> None:
    with pytest.raises(ValidationError) as failure:
        SuppliedAssessmentReviewAttribution.model_validate(
            fields(assertion_value()) | {field: None}
        )
    assert failure.value.errors()[0]["loc"][0] == field


@pytest.mark.parametrize(
    "label", (None, "x", "x" * 128, "\U0001f680" * 128, " Lin \n", "unknown")
)
def test_supplied_label_or_explicit_unknown_survives(label: str | None) -> None:
    value = SuppliedAssessmentReviewAttribution.model_validate(
        fields(assertion_value()) | {"reviewer": label}
    )
    assert value.reviewer == label
    assert value.review.attribution.supplier == "Review relay"
    assert value.attribution.supplier == "Attribution clerk"


@pytest.mark.parametrize("label", ("", " \t\n", "x" * 129, "\ud800", 7, True, [], {}))
def test_invalid_reviewer_text_is_refused(label: Any) -> None:
    with pytest.raises(ValidationError) as failure:
        SuppliedAssessmentReviewAttribution.model_validate(
            fields(assertion_value()) | {"reviewer": label}
        )
    assert failure.value.errors()[0]["loc"] == ("reviewer",)


@pytest.mark.parametrize("field", ("review", "source", "attribution"))
def test_python_children_are_not_coerced_from_valid_mappings(field: str) -> None:
    value = assertion_value()
    with pytest.raises(ValidationError, match="declared typed Python child"):
        SuppliedAssessmentReviewAttribution.model_validate(
            fields(value) | {field: assertion_wire()[field]}
        )


@pytest.mark.parametrize(
    "bad",
    (
        "https://invalid.example/review",
        "a" * 64,
        123,
        ProviderGlobalId("123"),
        object(),
    ),
)
def test_source_does_not_coerce_locators_ids_or_lookalikes(bad: Any) -> None:
    with pytest.raises(ValidationError) as failure:
        SuppliedAssessmentReviewAttribution.model_validate(
            fields(assertion_value()) | {"source": bad}
        )
    assert failure.value.errors()[0]["loc"] == ("source",)


@pytest.mark.parametrize("field,limit", (("supplier", 128), ("rationale", 4096)))
def test_existing_attribution_owner_retains_its_bounds(field: str, limit: int) -> None:
    wire = assertion_wire()
    wire["attribution"][field] = "x" * limit
    assert SuppliedAssessmentReviewAttribution.model_validate_json(json.dumps(wire))
    wire["attribution"][field] += "x"
    with pytest.raises(ValidationError) as failure:
        SuppliedAssessmentReviewAttribution.model_validate_json(json.dumps(wire))
    assert failure.value.errors()[0]["loc"] == ("attribution", field)


def test_source_json_retains_all_owner_fields_and_errors() -> None:
    value = assertion_value()
    assert value.source is not None
    assert value.source.model_dump(mode="json") == DECLARATIONS[0]["source"]
    assert set(value.source.model_dump()) == {
        "schema_version",
        "format_name",
        "format_version",
        "canonicalization",
        "sha256",
        "byte_length",
    }
    for change in ({"schema_version": True}, {"byte_length": -1}, {"sha256": "bad"}):
        wire = assertion_wire()
        wire["source"].update(change)
        with pytest.raises(ValidationError) as failure:
            SuppliedAssessmentReviewAttribution.model_validate_json(json.dumps(wire))
        assert failure.value.errors()[0]["loc"][0] == "source"


def test_unchecked_review_reference_and_assertion_are_revalidated() -> None:
    value = assertion_value()
    bad_review = value.review.model_copy(update={"scope": ""})
    assert value.source is not None
    bad_source = value.source.model_copy(update={"schema_version": True})
    bad_attribution = AssessmentAttribution.model_construct(supplier="", rationale="r")
    for update, location in (
        ({"review": bad_review}, ("review", "scope")),
        ({"source": bad_source}, ("source", "schema_version")),
        ({"attribution": bad_attribution}, ("attribution", "supplier")),
        ({"reviewer": ""}, ("reviewer",)),
    ):
        with pytest.raises(ValidationError) as failure:
            SuppliedAssessmentReviewAttribution.model_validate(
                value.model_copy(update=update)
            )
        assert failure.value.errors()[0]["loc"] == location


def test_native_json_preserves_nested_review_tuple_language() -> None:
    from test_supplied_assessment_review import review_wire

    wire = assertion_wire()
    wire["review"] = review_wire()
    value = SuppliedAssessmentReviewAttribution.model_validate_json(json.dumps(wire))
    assert value.model_dump(mode="json") == wire
    assert isinstance(value.review.assessment.opinions, tuple)
    bad = value.review.assessment.model_copy(
        update={"opinions": list(value.review.assessment.opinions)}
    )
    with pytest.raises(ValidationError):
        SuppliedAssessmentReviewAttribution.model_validate(
            value.model_copy(
                update={"review": value.review.model_copy(update={"assessment": bad})}
            )
        )


def test_no_new_field_child_subtypes_follow_their_owners() -> None:
    class ReviewChild(SuppliedAssessmentReview):
        pass

    class SourceChild(DurableEvidenceRecordReference):
        pass

    value = assertion_value()
    assert value.source is not None
    child = SuppliedAssessmentReviewAttribution(
        review=ReviewChild.model_validate(fields(value.review)),
        reviewer=value.reviewer,
        source=SourceChild.model_validate(fields(value.source)),
        attribution=value.attribution,
    )
    assert child == value
