"""Finite review-value checks with authored inputs and public child validation."""

import copy
import json
from typing import Any

import pytest
from pydantic import ValidationError
from test_supplied_assessment import fields, rich_wire, typed_sample

import faultatlas
import faultatlas.domain as domain_package
import faultatlas.domain.assessment_review as module
from faultatlas.domain.assessment import AssessmentAttribution, SuppliedAssessment
from faultatlas.domain.assessment_review import SuppliedAssessmentReview


def review_wire() -> dict[str, Any]:
    return {
        "assessment": rich_wire(),
        "scope": " Only the supplied condition inventory. ",
        "judgment": "Unknown; no independent material access is claimed.",
        "attribution": {
            "supplier": "Record supplier",
            "rationale": "Attributed reviewer and authenticated identity are distinct.",
        },
    }


def review_value() -> SuppliedAssessmentReview:
    return SuppliedAssessmentReview.model_validate_json(json.dumps(review_wire()))


def test_exact_value_surface_and_native_json() -> None:
    value = review_value()
    assert module.__all__ == ["SuppliedAssessmentReview"]
    assert tuple(module.SuppliedAssessmentReview.model_fields) == (
        "assessment",
        "scope",
        "judgment",
        "attribution",
    )
    assert value.model_dump(mode="json") == review_wire()
    assert (
        SuppliedAssessmentReview.model_validate_json(value.model_dump_json()) == value
    )
    assert SuppliedAssessmentReview.model_validate(fields(value)) == value
    assert isinstance(value.assessment.opinions, tuple)
    assert value.scope == " Only the supplied condition inventory. "
    assert {
        key: value.model_config.get(key)
        for key in (
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
    for field in module.SuppliedAssessmentReview.model_fields.values():
        assert field.is_required()
        assert (
            field.alias is field.validation_alias is field.serialization_alias is None
        )
    for package in (faultatlas, domain_package):
        assert not hasattr(package, "SuppliedAssessmentReview")
    with pytest.raises(ValidationError, match="frozen"):
        value.scope = "changed"
    with pytest.raises(ValidationError, match="extra_forbidden"):
        SuppliedAssessmentReview.model_validate(fields(value) | {"status": "approved"})


@pytest.mark.parametrize("field", ("assessment", "scope", "judgment", "attribution"))
@pytest.mark.parametrize("change", ("missing", "null"))
def test_all_four_fields_are_required_and_nonnullable(field: str, change: str) -> None:
    wire = review_wire()
    if change == "missing":
        del wire[field]
    else:
        wire[field] = None
    with pytest.raises(ValidationError) as failure:
        SuppliedAssessmentReview.model_validate_json(json.dumps(wire))
    assert failure.value.errors()[0]["loc"][0] == field


@pytest.mark.parametrize("field", ("scope", "judgment"))
@pytest.mark.parametrize("bad", ("", " \t\n", "x" * 4097, "\ud800", 1, True, [], {}))
def test_strict_review_text_rejects_invalid_values(field: str, bad: Any) -> None:
    value = review_value()
    with pytest.raises(ValidationError) as failure:
        SuppliedAssessmentReview.model_validate(fields(value) | {field: bad})
    assert failure.value.errors()[0]["loc"][0] == field


@pytest.mark.parametrize("text", ("x", "x" * 4096, "\U0001f680" * 4096, " \ntext\t "))
def test_text_boundaries_and_surrounding_whitespace_survive(text: str) -> None:
    value = review_value()
    changed = SuppliedAssessmentReview.model_validate(
        fields(value) | {"scope": text, "judgment": text}
    )
    assert changed.scope == changed.judgment == text


@pytest.mark.parametrize("field", ("assessment", "attribution"))
def test_python_children_must_be_typed_even_when_mapping_is_valid(field: str) -> None:
    value = review_value()
    with pytest.raises(ValidationError, match="declared typed Python child"):
        SuppliedAssessmentReview.model_validate(
            fields(value) | {field: review_wire()[field]}
        )

    class Lookalike:
        pass

    with pytest.raises(ValidationError, match="declared typed Python child"):
        SuppliedAssessmentReview.model_validate(fields(value) | {field: Lookalike()})


@pytest.mark.parametrize("field,limit", (("supplier", 128), ("rationale", 4096)))
def test_reused_attribution_keeps_owner_bounds(field: str, limit: int) -> None:
    wire = review_wire()
    wire["attribution"][field] = "x" * limit
    assert SuppliedAssessmentReview.model_validate_json(json.dumps(wire))
    wire["attribution"][field] += "x"
    with pytest.raises(ValidationError) as failure:
        SuppliedAssessmentReview.model_validate_json(json.dumps(wire))
    assert failure.value.errors()[0]["loc"] == ("attribution", field)


def test_revalidation_reaches_unchecked_copied_and_nested_values() -> None:
    value = review_value()
    bad_attribution = AssessmentAttribution.model_construct(supplier="", rationale="r")
    bad_data = fields(value.assessment)
    bad_data["attribution"] = bad_attribution
    bad_target = SuppliedAssessment.model_construct(**bad_data)
    for altered, location in (
        (value.model_copy(update={"scope": ""}), ("scope",)),
        (
            value.model_copy(update={"attribution": bad_attribution}),
            ("attribution", "supplier"),
        ),
        (
            value.model_copy(update={"assessment": bad_target}),
            ("assessment", "attribution", "supplier"),
        ),
    ):
        with pytest.raises(ValidationError) as failure:
            SuppliedAssessmentReview.model_validate(altered)
        assert failure.value.errors()[0]["loc"] == location


def test_normal_child_subtypes_and_python_ordered_tuple_rules() -> None:
    class Child(SuppliedAssessment):
        pass

    value = typed_sample()
    child = Child.model_validate(fields(value))
    assert (
        SuppliedAssessmentReview(
            assessment=child,
            scope="s",
            judgment="j",
            attribution=AssessmentAttribution(supplier="s", rationale="r"),
        ).assessment
        == value
    )
    unchecked = value.model_copy(update={"opinions": list(value.opinions)})
    with pytest.raises(ValidationError):
        SuppliedAssessmentReview(
            assessment=unchecked,
            scope="s",
            judgment="j",
            attribution=AssessmentAttribution(supplier="s", rationale="r"),
        )
    wire = copy.deepcopy(review_wire())
    wire["assessment"]["opinions"][0]["condition"] = "once"
    with pytest.raises(ValidationError) as failure:
        SuppliedAssessmentReview.model_validate_json(json.dumps(wire))
    assert failure.value.errors()[0]["loc"][:3] == ("assessment", "opinions", 0)
