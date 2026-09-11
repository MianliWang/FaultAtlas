from __future__ import annotations

import ast
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
import uuid
import zipfile
from collections.abc import Callable
from pathlib import Path
from typing import Any, cast

import pytest
from pydantic import BaseModel, ConfigDict, RootModel, ValidationError

import faultatlas
import faultatlas.domain
import faultatlas.domain.fault_interpretation as interpretation_module
from faultatlas.domain.fault import (
    FaultInstanceIdentity,
    FaultOccurrenceIdentity,
    FaultReportIdentity,
    FaultRepositoryContext,
    FaultScenarioIdentity,
    SuppliedFaultReport,
)
from faultatlas.domain.fault_interpretation import (
    FaultExpectedPropertyIdentity,
    FaultExplanationIdentity,
    FaultHypothesisIdentity,
    SuppliedFaultExpectedProperty,
    SuppliedFaultExplanation,
    SuppliedFaultHypothesis,
)
from faultatlas.domain.fault_repair import FaultRepairCandidateIdentity
from faultatlas.domain.fault_test import (
    FaultTestMaterialIdentity,
    FaultTestRunIdentity,
)
from faultatlas.domain.identity import (
    ProviderKey,
    ProviderRepositoryId,
    RepositoryIdentity,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
INTERPRETATION_SOURCE = (
    REPOSITORY_ROOT / "src/faultatlas/domain/fault_interpretation.py"
)
CHECKOUT_SOURCE_ROOT = REPOSITORY_ROOT / "src"
ROADMAP = REPOSITORY_ROOT / "docs/roadmap.md"

# Every identifier below is fixed synthetic supplied data. The retained pytest
# #4412 case supplies no explanation, hypothesis, or expected-property
# identifier, so each is invented here.
SUPPLIED_FAULT_TEXT = "12345678-1234-4234-8234-123456789abc"
SUPPLIED_FAULT = uuid.UUID(SUPPLIED_FAULT_TEXT)
SECOND_FAULT = uuid.UUID("aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee")
SUPPLIED_REPORT_TEXT = "87654321-4321-4abc-8def-0123456789ab"
SUPPLIED_REPORT = uuid.UUID(SUPPLIED_REPORT_TEXT)
SECOND_REPORT = uuid.UUID("11111111-2222-4333-8444-555555555555")
SUPPLIED_EXPLANATION_TEXT = "3e3e3e3e-4f4f-4a5a-8b6b-7c7c7c7c7c7c"
SUPPLIED_EXPLANATION = uuid.UUID(SUPPLIED_EXPLANATION_TEXT)
SECOND_EXPLANATION = uuid.UUID("9d9d9d9d-8e8e-4f7f-8060-515151515151")
SUPPLIED_HYPOTHESIS_TEXT = "6a6a6a6a-7b7b-4c8c-89d9-0e0e0e0e0e0e"
SUPPLIED_HYPOTHESIS = uuid.UUID(SUPPLIED_HYPOTHESIS_TEXT)
SECOND_HYPOTHESIS = uuid.UUID("42424242-5353-4646-8757-686868686868")
SUPPLIED_PROPERTY_TEXT = "1f1f1f1f-2020-4313-8424-535353535353"
SUPPLIED_PROPERTY = uuid.UUID(SUPPLIED_PROPERTY_TEXT)
SECOND_PROPERTY = uuid.UUID("cdcdcdcd-bebe-4faf-80b0-c1c1c1c1c1c1")
NIL_UUID = uuid.UUID("00000000-0000-0000-0000-000000000000")
MAX_UUID = uuid.UUID("ffffffff-ffff-ffff-ffff-ffffffffffff")

# Fixed lexemes covering several UUID generation versions plus the two special
# values. None is generated during the run, and none carries an ordering, time,
# or generation-version promise in this contract.
ADMITTED_UUID_TEXT: tuple[tuple[str, int | None], ...] = (
    ("c232ab00-9414-11ec-b3c8-9e6bdeced846", 1),
    ("6fa459ea-ee8a-3ca4-894e-db77e160355e", 3),
    (SUPPLIED_EXPLANATION_TEXT, 4),
    ("886313e1-3b8a-5372-9b90-0c9aee199e5d", 5),
    ("018f2c9e-1a2b-7c3d-8e4f-5a6b7c8d9e0f", 7),
    ("00000000-0000-8000-8000-00000000002a", 8),
    ("00000000-0000-0000-0000-000000000000", None),
    ("ffffffff-ffff-ffff-ffff-ffffffffffff", None),
)

RETAINED_PROVIDER = "github"
RETAINED_REPOSITORY_ID = "37489525"
OTHER_REPOSITORY_ID = "37489526"

PROBLEM_STATEMENT = "Instrumentation can change callback behavior."
BEHAVIORAL_DEVIATION = "The supplied transformed path invokes one callback twice."
SECOND_PROBLEM_STATEMENT = "A cached rewrite may be reused after the source changes."
SECOND_BEHAVIORAL_DEVIATION = "The supplied stale rewrite reports the wrong line."

# Case-calibrated prose, supplied by a caller for this one report. None of it is
# a FaultAtlas finding, and none is a quotation promoted to historical fact.
EXPLANATION_STATEMENT = (
    "The caller accounts for the deviation by the rewritten assertion "
    "evaluating the side-effecting expression a second time."
)
SECOND_EXPLANATION_STATEMENT = (
    "The caller accounts for the deviation by the comparison operand being "
    "rebuilt rather than reused during rewriting."
)
HYPOTHESIS_STATEMENT = (
    "The caller proposes, tentatively, that a stale rewrite cache is reused "
    "after the source changes."
)
SECOND_HYPOTHESIS_STATEMENT = (
    "The caller proposes, tentatively, that the deviation appears only when "
    "the module is imported twice."
)
EXPECTED_PROPERTY_STATEMENT = (
    "For this report, rewriting should preserve the relevant expression's "
    "evaluation count and execution order."
)
SECOND_EXPECTED_PROPERTY_STATEMENT = (
    "For this report, the reported callback should be invoked exactly once."
)

EXPLANATION_FIELDS = ("explanation", "report", "explanation_statement")
HYPOTHESIS_FIELDS = ("hypothesis", "report", "hypothesis_statement")
EXPECTED_PROPERTY_FIELDS = (
    "expected_property",
    "report",
    "expected_property_statement",
)
EXPECTED_EXPORTS = [
    "FaultExplanationIdentity",
    "SuppliedFaultExplanation",
    "FaultHypothesisIdentity",
    "SuppliedFaultHypothesis",
    "FaultExpectedPropertyIdentity",
    "SuppliedFaultExpectedProperty",
]
TEXT_LIMIT = 4096

# Each names an authority this Slice does not have, a resolution these records
# may not carry, or a generalization that belongs to `S1.P07`. None may become a
# field of any published model here.
FORBIDDEN_INTERPRETATION_IDENTIFIERS = (
    "accepted",
    "acceptance_criterion",
    "asserted",
    "certainty",
    "claim_kind",
    "confidence",
    "confirmed",
    "correct",
    "correctness",
    "disproved",
    "established",
    "evidence",
    "evidence_record",
    "falsified",
    "interpretation_kind",
    "invariant",
    "kind",
    "lifecycle",
    "likelihood",
    "observed",
    "outcome",
    "pattern",
    "precedence",
    "probability",
    "promoted",
    "proof",
    "proves",
    "refuted",
    "rejected",
    "repair_candidate",
    "replaces",
    "review",
    "reviewed",
    "root_cause",
    "scenario",
    "scope",
    "source",
    "state",
    "status",
    "strength",
    "superseded",
    "supersedes",
    "supported",
    "test_material",
    "test_run",
    "universal",
    "verification",
    "verified",
)
REFUSED_EXTRA_KEYS = (*FORBIDDEN_INTERPRETATION_IDENTIFIERS, "schema_version")

# The seven predecessor `S1.P06` UUID-rooted identities. The three published
# here are an eighth, ninth and tenth, and all ten must stay distinct on one
# shared scalar.
PREDECESSOR_UUID_IDENTITIES: tuple[type[RootModel[uuid.UUID]], ...] = (
    FaultInstanceIdentity,
    FaultReportIdentity,
    FaultScenarioIdentity,
    FaultOccurrenceIdentity,
    FaultRepairCandidateIdentity,
    FaultTestMaterialIdentity,
    FaultTestRunIdentity,
)
S07_UUID_IDENTITIES: tuple[type[RootModel[uuid.UUID]], ...] = (
    FaultExplanationIdentity,
    FaultHypothesisIdentity,
    FaultExpectedPropertyIdentity,
)


def _repository(identifier: str = RETAINED_REPOSITORY_ID) -> RepositoryIdentity:
    return RepositoryIdentity(
        provider=ProviderKey(RETAINED_PROVIDER),
        provider_repository_id=ProviderRepositoryId(identifier),
    )


def _context(
    fault: uuid.UUID = SUPPLIED_FAULT,
    repository: str = RETAINED_REPOSITORY_ID,
) -> FaultRepositoryContext:
    return FaultRepositoryContext(
        fault=FaultInstanceIdentity(fault),
        repository=_repository(repository),
    )


def _report(
    report: uuid.UUID = SUPPLIED_REPORT,
    fault: uuid.UUID = SUPPLIED_FAULT,
    repository: str = RETAINED_REPOSITORY_ID,
    problem_statement: str = PROBLEM_STATEMENT,
    behavioral_deviation: str = BEHAVIORAL_DEVIATION,
) -> SuppliedFaultReport:
    return SuppliedFaultReport(
        report=FaultReportIdentity(report),
        context=_context(fault, repository),
        problem_statement=problem_statement,
        behavioral_deviation=behavioral_deviation,
    )


def _second_report() -> SuppliedFaultReport:
    return _report(
        report=SECOND_REPORT,
        fault=SECOND_FAULT,
        problem_statement=SECOND_PROBLEM_STATEMENT,
        behavioral_deviation=SECOND_BEHAVIORAL_DEVIATION,
    )


def _explanation(
    explanation: uuid.UUID = SUPPLIED_EXPLANATION,
    report: SuppliedFaultReport | None = None,
    explanation_statement: str = EXPLANATION_STATEMENT,
) -> SuppliedFaultExplanation:
    return SuppliedFaultExplanation(
        explanation=FaultExplanationIdentity(explanation),
        report=_report() if report is None else report,
        explanation_statement=explanation_statement,
    )


def _hypothesis(
    hypothesis: uuid.UUID = SUPPLIED_HYPOTHESIS,
    report: SuppliedFaultReport | None = None,
    hypothesis_statement: str = HYPOTHESIS_STATEMENT,
) -> SuppliedFaultHypothesis:
    return SuppliedFaultHypothesis(
        hypothesis=FaultHypothesisIdentity(hypothesis),
        report=_report() if report is None else report,
        hypothesis_statement=hypothesis_statement,
    )


def _expected_property(
    expected_property: uuid.UUID = SUPPLIED_PROPERTY,
    report: SuppliedFaultReport | None = None,
    expected_property_statement: str = EXPECTED_PROPERTY_STATEMENT,
) -> SuppliedFaultExpectedProperty:
    return SuppliedFaultExpectedProperty(
        expected_property=FaultExpectedPropertyIdentity(expected_property),
        report=_report() if report is None else report,
        expected_property_statement=expected_property_statement,
    )


def _typed_explanation_mapping(**overrides: object) -> dict[str, Any]:
    mapping: dict[str, Any] = {
        "explanation": FaultExplanationIdentity(SUPPLIED_EXPLANATION),
        "report": _report(),
        "explanation_statement": EXPLANATION_STATEMENT,
    }
    mapping.update(overrides)
    return mapping


def _typed_hypothesis_mapping(**overrides: object) -> dict[str, Any]:
    mapping: dict[str, Any] = {
        "hypothesis": FaultHypothesisIdentity(SUPPLIED_HYPOTHESIS),
        "report": _report(),
        "hypothesis_statement": HYPOTHESIS_STATEMENT,
    }
    mapping.update(overrides)
    return mapping


def _typed_expected_property_mapping(**overrides: object) -> dict[str, Any]:
    mapping: dict[str, Any] = {
        "expected_property": FaultExpectedPropertyIdentity(SUPPLIED_PROPERTY),
        "report": _report(),
        "expected_property_statement": EXPECTED_PROPERTY_STATEMENT,
    }
    mapping.update(overrides)
    return mapping


BUILDERS: dict[type[BaseModel], Callable[..., dict[str, Any]]] = {
    SuppliedFaultExplanation: _typed_explanation_mapping,
    SuppliedFaultHypothesis: _typed_hypothesis_mapping,
    SuppliedFaultExpectedProperty: _typed_expected_property_mapping,
}
RECORD_CASES = (
    pytest.param(SuppliedFaultExplanation, EXPLANATION_FIELDS, id="explanation"),
    pytest.param(SuppliedFaultHypothesis, HYPOTHESIS_FIELDS, id="hypothesis"),
    pytest.param(
        SuppliedFaultExpectedProperty,
        EXPECTED_PROPERTY_FIELDS,
        id="expected-property",
    ),
)
IDENTITY_CASES = (
    pytest.param(FaultExplanationIdentity, SUPPLIED_EXPLANATION, id="explanation"),
    pytest.param(FaultHypothesisIdentity, SUPPLIED_HYPOTHESIS, id="hypothesis"),
    pytest.param(
        FaultExpectedPropertyIdentity, SUPPLIED_PROPERTY, id="expected-property"
    ),
)


def _payload(value: BaseModel) -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(value.model_dump_json()))


def _failures(error: ValidationError) -> tuple[tuple[tuple[str | int, ...], str], ...]:
    return tuple((detail["loc"], detail["type"]) for detail in error.errors())


def _paths(error: ValidationError) -> tuple[tuple[str | int, ...], ...]:
    return tuple(detail["loc"] for detail in error.errors())


def _distinct_value_count(*values: object) -> int:
    return len({cast(Any, value) for value in values})


def _interpretation_tree() -> ast.Module:
    return ast.parse(
        INTERPRETATION_SOURCE.read_bytes(), filename=INTERPRETATION_SOURCE.name
    )


def _roadmap() -> str:
    return " ".join(ROADMAP.read_text(encoding="utf-8").split())


def _published_models() -> tuple[type[BaseModel], ...]:
    return (
        SuppliedFaultExplanation,
        SuppliedFaultHypothesis,
        SuppliedFaultExpectedProperty,
    )


# --- foreign, lookalike and subclass carriers --------------------------------


class ForeignUuidRoot(RootModel[uuid.UUID]):
    """A different published-shaped model over the same scalar content."""

    model_config = ConfigDict(
        frozen=True,
        strict=True,
        revalidate_instances="always",
        validate_default=True,
    )

    root: uuid.UUID


class ForeignSuppliedFaultExplanation(BaseModel):
    """A structurally identical record that is not the published type."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        strict=True,
        revalidate_instances="always",
        validate_default=True,
    )

    explanation: FaultExplanationIdentity
    report: SuppliedFaultReport
    explanation_statement: str


class ExplanationLookalike:
    """An attribute-backed object carrying the published field names."""

    def __init__(self) -> None:
        self.explanation = FaultExplanationIdentity(SUPPLIED_EXPLANATION)
        self.report = _report()
        self.explanation_statement = EXPLANATION_STATEMENT


class ReportLookalike:
    """An attribute-backed object carrying a published report's field names."""

    def __init__(self) -> None:
        published = _report()
        self.report = published.report
        self.context = published.context
        self.problem_statement = published.problem_statement
        self.behavioral_deviation = published.behavioral_deviation


class UntypedChildExplanationLookalike:
    """An attribute-backed top-level object whose report child is a mapping."""

    def __init__(self) -> None:
        self.explanation = FaultExplanationIdentity(SUPPLIED_EXPLANATION)
        self.report = _report().model_dump()
        self.explanation_statement = EXPLANATION_STATEMENT


class AttributeChildExplanationLookalike:
    """An attribute-backed top-level object whose report child is one too.

    This is the case only the before-guard can refuse: under
    `from_attributes=True` a mapping child is already refused by strict mode,
    but an attribute-backed child would otherwise be materialised into a
    published report the caller never constructed.
    """

    def __init__(self) -> None:
        self.explanation = FaultExplanationIdentity(SUPPLIED_EXPLANATION)
        self.report = ReportLookalike()
        self.explanation_statement = EXPLANATION_STATEMENT


class UnextendedSuppliedFaultHypothesis(SuppliedFaultHypothesis):
    """An ordinary hypothesis subclass that adds no field."""


class ExtendedSuppliedFaultHypothesis(SuppliedFaultHypothesis):
    """A hypothesis subclass that adds a field the base schema forbids."""

    note: str = "supplied"


class SuppliedText(str):
    """A str subclass carrying an ordinary value."""


# --- the three new identities -------------------------------------------------


@pytest.mark.parametrize(("identity", "supplied"), IDENTITY_CASES)
def test_each_identity_accepts_a_supplied_uuid_through_every_entry_path(
    identity: type[RootModel[uuid.UUID]],
    supplied: uuid.UUID,
) -> None:
    positional = identity(supplied)

    assert positional.root == supplied
    assert identity(root=supplied) == positional
    assert identity.model_validate(supplied) == positional
    assert identity.model_validate(positional) == positional
    # A root model is the scalar, not a one-key record over it.
    with pytest.raises(ValidationError):
        identity.model_validate({"root": supplied})


@pytest.mark.parametrize("identity", S07_UUID_IDENTITIES, ids=lambda i: i.__name__)
@pytest.mark.parametrize(("text", "version"), ADMITTED_UUID_TEXT)
def test_each_identity_admits_every_uuid_the_locked_validator_admits(
    identity: type[RootModel[uuid.UUID]],
    text: str,
    version: int | None,
) -> None:
    """Nil, Max and every generation version are ordinary admitted values."""
    supplied = uuid.UUID(text)
    assert supplied.version == version

    value = identity(supplied)

    assert value.root == supplied
    assert json.loads(value.model_dump_json()) == text
    assert identity.model_validate_json(json.dumps(text)) == value


@pytest.mark.parametrize("identity", S07_UUID_IDENTITIES, ids=lambda i: i.__name__)
@pytest.mark.parametrize(
    "supplied",
    (
        SUPPLIED_EXPLANATION_TEXT,
        SUPPLIED_EXPLANATION.bytes,
        SUPPLIED_EXPLANATION.int,
        None,
        1,
        1.0,
        ["12345678-1234-4234-8234-123456789abc"],
    ),
)
def test_each_identity_refuses_untyped_python_input(
    identity: type[RootModel[uuid.UUID]],
    supplied: object,
) -> None:
    with pytest.raises(ValidationError):
        identity(cast(Any, supplied))


@pytest.mark.parametrize(
    ("identity", "text"),
    (
        pytest.param(
            FaultExplanationIdentity, SUPPLIED_EXPLANATION_TEXT, id="explanation"
        ),
        pytest.param(
            FaultHypothesisIdentity, SUPPLIED_HYPOTHESIS_TEXT, id="hypothesis"
        ),
        pytest.param(
            FaultExpectedPropertyIdentity,
            SUPPLIED_PROPERTY_TEXT,
            id="expected-property",
        ),
    ),
)
def test_each_identity_round_trips_as_a_bare_scalar(
    identity: type[RootModel[uuid.UUID]],
    text: str,
) -> None:
    """The JSON form is the bare UUID string, with no wrapper and no adapter."""
    decoded = identity.model_validate_json(json.dumps(text))

    assert decoded.root == uuid.UUID(text)
    assert json.loads(decoded.model_dump_json()) == text
    assert identity.model_validate_json(decoded.model_dump_json()) == decoded


@pytest.mark.parametrize("identity", S07_UUID_IDENTITIES, ids=lambda i: i.__name__)
@pytest.mark.parametrize(
    "wrapper",
    (
        {"root": SUPPLIED_EXPLANATION_TEXT},
        {"value": SUPPLIED_EXPLANATION_TEXT},
        {"uuid": SUPPLIED_EXPLANATION_TEXT},
        {"id": SUPPLIED_EXPLANATION_TEXT},
    ),
)
def test_no_wrapper_object_json_form_is_published(
    identity: type[RootModel[uuid.UUID]],
    wrapper: dict[str, str],
) -> None:
    with pytest.raises(ValidationError):
        identity.model_validate_json(json.dumps(wrapper))


@pytest.mark.parametrize("identity", S07_UUID_IDENTITIES, ids=lambda i: i.__name__)
def test_each_identity_declares_the_published_value_profile(
    identity: type[RootModel[uuid.UUID]],
) -> None:
    assert identity.model_config == {
        "frozen": True,
        "strict": True,
        "revalidate_instances": "always",
        "validate_default": True,
    }


@pytest.mark.parametrize("identity", S07_UUID_IDENTITIES, ids=lambda i: i.__name__)
def test_each_identity_requires_its_root_and_declares_no_default(
    identity: type[RootModel[uuid.UUID]],
) -> None:
    """Nothing allocates an identifier, so nothing may supply one by default."""
    field = identity.model_fields["root"]

    assert field.is_required()
    assert field.default_factory is None
    with pytest.raises(ValidationError):
        identity()  # pyright: ignore[reportCallIssue, reportArgumentType]


@pytest.mark.parametrize(("identity", "supplied"), IDENTITY_CASES)
def test_each_identity_is_frozen_and_allocates_nothing(
    identity: type[RootModel[uuid.UUID]],
    supplied: uuid.UUID,
) -> None:
    value = identity(supplied)

    with pytest.raises(ValidationError):
        value.root = supplied
    assert identity(supplied).root == supplied
    assert identity(supplied) == value


def test_the_three_identities_are_not_subclasses_or_aliases_of_anything() -> None:
    everything = (*PREDECESSOR_UUID_IDENTITIES, *S07_UUID_IDENTITIES)

    assert len(everything) == 10
    for identity in S07_UUID_IDENTITIES:
        for other in everything:
            if other is identity:
                continue
            assert not issubclass(identity, other), (identity, other)
            assert not issubclass(other, identity), (other, identity)


@pytest.mark.parametrize("shared", (SUPPLIED_FAULT, NIL_UUID, MAX_UUID))
def test_all_ten_p06_identities_stay_distinct_on_one_shared_scalar(
    shared: uuid.UUID,
) -> None:
    """Ten names over one scalar are ten values, not one."""
    values = [
        identity(shared)
        for identity in (*PREDECESSOR_UUID_IDENTITIES, *S07_UUID_IDENTITIES)
    ]

    assert len(values) == 10
    assert _distinct_value_count(*values) == 10
    for value in values:
        assert value.root == shared
    assert len({json.loads(value.model_dump_json()) for value in values}) == 1


@pytest.mark.parametrize(("identity", "supplied"), IDENTITY_CASES)
def test_a_foreign_uuid_root_model_is_not_a_published_identity(
    identity: type[RootModel[uuid.UUID]],
    supplied: uuid.UUID,
) -> None:
    foreign = ForeignUuidRoot(supplied)

    assert foreign.root == identity(supplied).root
    assert foreign != identity(supplied)
    with pytest.raises(ValidationError):
        identity.model_validate(foreign)


@pytest.mark.parametrize(("identity", "supplied"), IDENTITY_CASES)
def test_equal_identities_hash_equally_and_carry_no_ordering(
    identity: type[RootModel[uuid.UUID]],
    supplied: uuid.UUID,
) -> None:
    first = identity(supplied)
    second = identity(supplied)

    assert first == second
    assert hash(first) == hash(second)
    assert _distinct_value_count(first, second) == 1
    with pytest.raises(TypeError):
        _ = first < second  # type: ignore[operator]


# --- the three records: shape, profile and round trip --------------------------


@pytest.mark.parametrize(("model", "fields"), RECORD_CASES)
def test_each_record_declares_exactly_its_fields_in_order(
    model: type[BaseModel],
    fields: tuple[str, ...],
) -> None:
    assert tuple(model.model_fields) == fields


@pytest.mark.parametrize(("model", "fields"), RECORD_CASES)
def test_each_json_payload_carries_exactly_the_declared_keys(
    model: type[BaseModel],
    fields: tuple[str, ...],
) -> None:
    value = model(**BUILDERS[model]())

    assert tuple(_payload(value)) == fields


@pytest.mark.parametrize("model", _published_models(), ids=lambda m: m.__name__)
def test_each_record_declares_the_published_value_profile(
    model: type[BaseModel],
) -> None:
    assert model.model_config == {
        "frozen": True,
        "extra": "forbid",
        "strict": True,
        "revalidate_instances": "always",
        "validate_default": True,
    }


@pytest.mark.parametrize("model", _published_models(), ids=lambda m: m.__name__)
def test_each_record_is_built_from_already_typed_values(
    model: type[BaseModel],
) -> None:
    value = model(**BUILDERS[model]())

    assert model.model_validate(value) == value
    # The fault subject stays reachable through the report, never restated.
    report = cast(SuppliedFaultReport, getattr(value, "report"))
    assert report.context.fault == FaultInstanceIdentity(SUPPLIED_FAULT)


@pytest.mark.parametrize("model", _published_models(), ids=lambda m: m.__name__)
def test_each_record_round_trips_through_json(model: type[BaseModel]) -> None:
    value = model(**BUILDERS[model]())

    assert model.model_validate_json(value.model_dump_json()) == value


@pytest.mark.parametrize(("model", "fields"), RECORD_CASES)
def test_each_record_refuses_its_own_python_dump(
    model: type[BaseModel],
    fields: tuple[str, ...],
) -> None:
    """Python and JSON are different input languages, deliberately."""
    value = model(**BUILDERS[model]())

    with pytest.raises(ValidationError) as failure:
        model.model_validate(value.model_dump())

    assert _paths(failure.value)[0] == (fields[0],)


@pytest.mark.parametrize(("model", "fields"), RECORD_CASES)
def test_no_record_declares_a_forbidden_field(
    model: type[BaseModel],
    fields: tuple[str, ...],
) -> None:
    for forbidden in FORBIDDEN_INTERPRETATION_IDENTIFIERS:
        assert forbidden not in model.model_fields, (model.__name__, forbidden)
    assert set(model.model_fields) == set(fields)


@pytest.mark.parametrize("model", _published_models(), ids=lambda m: m.__name__)
def test_no_record_json_payload_carries_a_forbidden_key(
    model: type[BaseModel],
) -> None:
    text = model(**BUILDERS[model]()).model_dump_json()

    for forbidden in FORBIDDEN_INTERPRETATION_IDENTIFIERS:
        assert f'"{forbidden}":' not in text, forbidden


@pytest.mark.parametrize(
    "model",
    (*_published_models(), *S07_UUID_IDENTITIES),
    ids=lambda m: m.__name__,
)
def test_no_field_declares_an_input_or_output_alias(
    model: type[BaseModel] | type[RootModel[uuid.UUID]],
) -> None:
    """An alias would publish a key the declared field name does not name.

    The three identities are swept too: an alias on a root field is inert in
    pydantic today, which is a reason it would go unnoticed, not a reason to
    leave the claim half-asserted.
    """
    for name, field in model.model_fields.items():
        assert field.alias is None, (model.__name__, name)
        assert field.validation_alias is None, (model.__name__, name)
        assert field.serialization_alias is None, (model.__name__, name)


@pytest.mark.parametrize(("model", "fields"), RECORD_CASES)
def test_the_aliased_dump_and_both_schemas_carry_the_declared_keys(
    model: type[BaseModel],
    fields: tuple[str, ...],
) -> None:
    """The default dump is not the whole published surface."""
    value = model(**BUILDERS[model]())

    assert tuple(json.loads(value.model_dump_json(by_alias=True))) == fields
    for mode in ("validation", "serialization"):
        schema = model.model_json_schema(mode=mode)  # pyright: ignore[reportArgumentType]
        assert tuple(schema["properties"]) == fields, mode
        assert set(schema["required"]) == set(fields), mode


@pytest.mark.parametrize(("model", "fields"), RECORD_CASES)
def test_no_field_is_optional_or_nullable(
    model: type[BaseModel],
    fields: tuple[str, ...],
) -> None:
    for name in fields:
        field = model.model_fields[name]
        assert field.is_required(), (model.__name__, name)
        assert field.default_factory is None, (model.__name__, name)
        assert "None" not in str(field.annotation), (model.__name__, name)


# --- child guards, omission, null, frozen, extras -------------------------------


@pytest.mark.parametrize(
    ("model", "field", "supplied", "label"),
    (
        pytest.param(
            SuppliedFaultExplanation,
            "explanation",
            SUPPLIED_EXPLANATION,
            "bare uuid",
            id="explanation-bare-uuid",
        ),
        pytest.param(
            SuppliedFaultExplanation,
            "explanation",
            SUPPLIED_EXPLANATION_TEXT,
            "uuid text",
            id="explanation-uuid-text",
        ),
        pytest.param(
            SuppliedFaultExplanation,
            "explanation",
            {"root": SUPPLIED_EXPLANATION},
            "mapping",
            id="explanation-mapping",
        ),
        pytest.param(
            SuppliedFaultExplanation,
            "explanation",
            ForeignUuidRoot(SUPPLIED_EXPLANATION),
            "foreign root",
            id="explanation-foreign",
        ),
        pytest.param(
            SuppliedFaultExplanation,
            "explanation",
            FaultHypothesisIdentity(SUPPLIED_EXPLANATION),
            "sibling identity",
            id="explanation-sibling",
        ),
        pytest.param(
            SuppliedFaultExplanation,
            "report",
            _report().model_dump(),
            "python dump",
            id="explanation-report-dump",
        ),
        pytest.param(
            SuppliedFaultExplanation,
            "report",
            ExplanationLookalike(),
            "lookalike",
            id="explanation-report-lookalike",
        ),
        pytest.param(
            SuppliedFaultHypothesis,
            "hypothesis",
            SUPPLIED_HYPOTHESIS,
            "bare uuid",
            id="hypothesis-bare-uuid",
        ),
        pytest.param(
            SuppliedFaultHypothesis,
            "hypothesis",
            FaultExplanationIdentity(SUPPLIED_HYPOTHESIS),
            "sibling identity",
            id="hypothesis-sibling",
        ),
        pytest.param(
            SuppliedFaultHypothesis,
            "report",
            _report().model_dump(),
            "python dump",
            id="hypothesis-report-dump",
        ),
        pytest.param(
            SuppliedFaultExpectedProperty,
            "expected_property",
            SUPPLIED_PROPERTY,
            "bare uuid",
            id="property-bare-uuid",
        ),
        pytest.param(
            SuppliedFaultExpectedProperty,
            "expected_property",
            FaultHypothesisIdentity(SUPPLIED_PROPERTY),
            "sibling identity",
            id="property-sibling",
        ),
        pytest.param(
            SuppliedFaultExpectedProperty,
            "report",
            ForeignSuppliedFaultExplanation(
                explanation=FaultExplanationIdentity(SUPPLIED_EXPLANATION),
                report=_report(),
                explanation_statement=EXPLANATION_STATEMENT,
            ),
            "foreign model",
            id="property-report-foreign",
        ),
    ),
)
def test_each_model_valued_position_is_closed_to_untyped_python_input(
    model: type[BaseModel],
    field: str,
    supplied: object,
    label: str,
) -> None:
    with pytest.raises(ValidationError) as failure:
        model(**BUILDERS[model](**{field: supplied}))

    assert _failures(failure.value) == (((field,), "value_error"),), label


@pytest.mark.parametrize(("model", "fields"), RECORD_CASES)
def test_a_top_level_mapping_still_guards_each_child(
    model: type[BaseModel],
    fields: tuple[str, ...],
) -> None:
    """`model_validate` over a typed mapping is admitted; a raw child is not."""
    builder = BUILDERS[model]

    assert model.model_validate(builder()) == model(**builder())
    with pytest.raises(ValidationError) as failure:
        model.model_validate(builder(**{fields[0]: {"root": SUPPLIED_EXPLANATION}}))

    assert _paths(failure.value)[0] == (fields[0],)


def test_from_attributes_reads_a_top_level_object_but_still_guards_its_children() -> (
    None
):
    """A relaxed top-level read is not a relaxed child read."""
    explanation = SuppliedFaultExplanation.model_validate(
        ExplanationLookalike(), from_attributes=True
    )

    assert explanation == _explanation()
    with pytest.raises(ValidationError) as failure:
        SuppliedFaultExplanation.model_validate(
            UntypedChildExplanationLookalike(), from_attributes=True
        )

    assert _failures(failure.value) == ((("report",), "value_error"),)


@pytest.mark.parametrize(
    ("model", "child_field"),
    (
        pytest.param(SuppliedFaultExplanation, "report", id="explanation"),
        pytest.param(SuppliedFaultHypothesis, "report", id="hypothesis"),
        pytest.param(SuppliedFaultExpectedProperty, "report", id="expected-property"),
    ),
)
def test_an_attribute_backed_child_is_refused_under_from_attributes(
    model: type[BaseModel],
    child_field: str,
) -> None:
    """The one case only the before-guard can refuse.

    Strict mode already refuses a mapping, a raw UUID, a string and a foreign
    model at a model-typed position. An attribute-backed child read through
    `from_attributes=True` is the case it does not cover: without the guard the
    lookalike is materialised into a published report the caller never built.
    """
    supplied = BUILDERS[model](**{child_field: ReportLookalike()})

    with pytest.raises(ValidationError) as failure:
        model.model_validate(supplied, from_attributes=True)

    assert _failures(failure.value) == (((child_field,), "value_error"),)


@pytest.mark.parametrize(("model", "fields"), RECORD_CASES)
def test_a_true_omission_fails_at_its_own_position(
    model: type[BaseModel],
    fields: tuple[str, ...],
) -> None:
    for omitted in fields:
        supplied = {
            name: value for name, value in BUILDERS[model]().items() if name != omitted
        }
        with pytest.raises(ValidationError) as failure:
            model(**supplied)

        assert _failures(failure.value) == (((omitted,), "missing"),), omitted


@pytest.mark.parametrize(("model", "fields"), RECORD_CASES)
def test_no_position_admits_null_in_either_input_language(
    model: type[BaseModel],
    fields: tuple[str, ...],
) -> None:
    """An absent claim is an absent record, never a null field."""
    for field in fields:
        with pytest.raises(ValidationError) as python_failure:
            model(**BUILDERS[model](**{field: None}))
        assert _paths(python_failure.value)[0] == (field,), field

        payload = _payload(model(**BUILDERS[model]()))
        payload[field] = None
        with pytest.raises(ValidationError) as json_failure:
            model.model_validate_json(json.dumps(payload))
        assert _paths(json_failure.value)[0] == (field,), field


@pytest.mark.parametrize(("model", "fields"), RECORD_CASES)
def test_each_record_is_frozen_against_assignment_and_deletion(
    model: type[BaseModel],
    fields: tuple[str, ...],
) -> None:
    value = model(**BUILDERS[model]())

    for field in fields:
        with pytest.raises(ValidationError):
            setattr(value, field, getattr(value, field))
        with pytest.raises((AttributeError, ValidationError)):
            delattr(value, field)


@pytest.mark.parametrize("model", _published_models(), ids=lambda m: m.__name__)
@pytest.mark.parametrize("extra", REFUSED_EXTRA_KEYS)
def test_an_extra_key_is_refused_in_python_input(
    model: type[BaseModel],
    extra: str,
) -> None:
    with pytest.raises(ValidationError) as failure:
        model(**BUILDERS[model](**{extra: "supplied"}))

    assert _failures(failure.value) == (((extra,), "extra_forbidden"),)


@pytest.mark.parametrize("extra", REFUSED_EXTRA_KEYS)
def test_an_extra_key_is_refused_in_json_input(extra: str) -> None:
    payload = _payload(_hypothesis())
    payload[extra] = "supplied"

    with pytest.raises(ValidationError) as failure:
        SuppliedFaultHypothesis.model_validate_json(json.dumps(payload))

    assert _failures(failure.value) == (((extra,), "extra_forbidden"),)


def test_an_extra_key_inside_the_embedded_report_is_refused_at_its_own_path() -> None:
    payload = _payload(_explanation())
    payload["report"]["verified"] = True

    with pytest.raises(ValidationError) as failure:
        SuppliedFaultExplanation.model_validate_json(json.dumps(payload))

    assert _failures(failure.value) == ((("report", "verified"), "extra_forbidden"),)


def _tamper_identity(payload: dict[str, Any]) -> None:
    payload["explanation"] = "not-a-uuid"


def _tamper_report_text(payload: dict[str, Any]) -> None:
    payload["report"]["problem_statement"] = " padded"


def _tamper_nested_provider(payload: dict[str, Any]) -> None:
    payload["report"]["context"]["repository"]["provider"] = ""


@pytest.mark.parametrize(
    ("path", "mutate"),
    (
        pytest.param(("explanation",), _tamper_identity, id="identity"),
        pytest.param(
            ("report", "problem_statement"), _tamper_report_text, id="report-text"
        ),
        pytest.param(
            ("report", "context", "repository", "provider"),
            _tamper_nested_provider,
            id="nested-provider",
        ),
    ),
)
def test_a_tampered_child_is_refused_under_its_own_published_schema(
    path: tuple[str, ...],
    mutate: Callable[[dict[str, Any]], None],
) -> None:
    payload = _payload(_explanation())
    mutate(payload)

    with pytest.raises(ValidationError) as failure:
        SuppliedFaultExplanation.model_validate_json(json.dumps(payload))

    assert path in _paths(failure.value)


def test_a_no_added_field_subclass_is_admitted_and_base_normalized() -> None:
    subclass = UnextendedSuppliedFaultHypothesis(**_typed_hypothesis_mapping())

    assert isinstance(subclass, SuppliedFaultHypothesis)
    assert SuppliedFaultHypothesis.model_validate(subclass) == _hypothesis()
    assert type(SuppliedFaultHypothesis.model_validate(subclass)) is (
        SuppliedFaultHypothesis
    )


def test_a_subclass_extra_field_remains_refused() -> None:
    extended = ExtendedSuppliedFaultHypothesis(**_typed_hypothesis_mapping())

    assert extended.note == "supplied"
    with pytest.raises(ValidationError) as failure:
        SuppliedFaultHypothesis.model_validate_json(extended.model_dump_json())

    assert _failures(failure.value) == ((("note",), "extra_forbidden"),)


# --- the three supplied-text fields --------------------------------------------

TEXT_POSITIONS: tuple[tuple[str, str, Callable[[str], BaseModel]], ...] = (
    (
        "explanation_statement",
        "SuppliedFaultExplanation",
        lambda supplied: _explanation(explanation_statement=supplied),
    ),
    (
        "hypothesis_statement",
        "SuppliedFaultHypothesis",
        lambda supplied: _hypothesis(hypothesis_statement=supplied),
    ),
    (
        "expected_property_statement",
        "SuppliedFaultExpectedProperty",
        lambda supplied: _expected_property(expected_property_statement=supplied),
    ),
)
TEXT_IDS = tuple(field for field, _, _ in TEXT_POSITIONS)


@pytest.mark.parametrize(("field", "owner", "build"), TEXT_POSITIONS, ids=TEXT_IDS)
@pytest.mark.parametrize(
    "supplied",
    (
        "x",
        "Multi\nline\naccount.",
        "Tab\tseparated account.",
        "Unicode: café — naïve — 変更 — 🛠",
        "a" * TEXT_LIMIT,
        "Inner  double  spaces stay.",
        "MiXeD CaSe Is PrEsErVeD.",
        "Composed é and decomposed é stay as supplied.",
    ),
)
def test_an_admitted_statement_is_preserved_exactly(
    field: str,
    owner: str,
    build: Callable[[str], BaseModel],
    supplied: str,
) -> None:
    value = build(supplied)

    assert getattr(value, field) == supplied
    assert _payload(value)[field] == supplied
    assert type(value).model_validate_json(value.model_dump_json()) == value
    assert type(value).__name__ == owner


@pytest.mark.parametrize(("field", "owner", "build"), TEXT_POSITIONS, ids=TEXT_IDS)
@pytest.mark.parametrize(
    "supplied",
    (
        "",
        " ",
        "\n",
        "\t",
        "   \n  ",
        " leading",
        "trailing ",
        "\nleading newline",
        "trailing newline\n",
        "a" * (TEXT_LIMIT + 1),
    ),
)
def test_a_refused_statement_is_refused_at_its_own_position(
    field: str,
    owner: str,
    build: Callable[[str], BaseModel],
    supplied: str,
) -> None:
    with pytest.raises(ValidationError) as failure:
        build(supplied)

    assert _paths(failure.value) == ((field,),), owner


@pytest.mark.parametrize(("field", "owner", "build"), TEXT_POSITIONS, ids=TEXT_IDS)
@pytest.mark.parametrize("supplied", (None, 1, 1.0, b"bytes", ["text"], SUPPLIED_FAULT))
def test_a_non_string_statement_is_refused(
    field: str,
    owner: str,
    build: Callable[[str], BaseModel],
    supplied: object,
) -> None:
    with pytest.raises(ValidationError) as failure:
        build(cast(Any, supplied))

    assert _paths(failure.value) == ((field,),), owner


@pytest.mark.parametrize(("field", "owner", "build"), TEXT_POSITIONS, ids=TEXT_IDS)
def test_an_unencodable_statement_is_refused_at_the_field(
    field: str,
    owner: str,
    build: Callable[[str], BaseModel],
) -> None:
    """Text that cannot encode as UTF-8 is refused where it is supplied."""
    with pytest.raises(ValidationError) as failure:
        build("lone surrogate \ud800")

    assert _failures(failure.value) == (((field,), "string_unicode"),), owner


@pytest.mark.parametrize(("field", "owner", "build"), TEXT_POSITIONS, ids=TEXT_IDS)
def test_padded_text_is_refused_rather_than_trimmed(
    field: str,
    owner: str,
    build: Callable[[str], BaseModel],
) -> None:
    """Trimming would silently publish prose the caller did not supply."""
    padded = f"  {EXPLANATION_STATEMENT}  "

    with pytest.raises(ValidationError) as failure:
        build(padded)

    assert _paths(failure.value) == ((field,),), owner
    # The unpadded form is admitted, so the refusal is about the padding.
    assert getattr(build(padded.strip()), field) == padded.strip()


def test_a_str_subclass_statement_normalizes_to_str() -> None:
    explanation = _explanation(
        explanation_statement=SuppliedText(EXPLANATION_STATEMENT)
    )

    assert explanation.explanation_statement == EXPLANATION_STATEMENT
    assert type(explanation.explanation_statement) is str


@pytest.mark.parametrize(
    ("owner", "field"),
    (
        ("SuppliedFaultExplanation", "explanation_statement"),
        ("SuppliedFaultHypothesis", "hypothesis_statement"),
        ("SuppliedFaultExpectedProperty", "expected_property_statement"),
    ),
)
def test_each_text_bound_is_declared_inline_on_its_own_field(
    owner: str,
    field: str,
) -> None:
    """The shared rule is restated per field, not shared through an alias.

    That no shared public prose type is exported is held by the `__all__` lock;
    this asserts only that the literal bound is declared where each field is.
    """
    (owner_class,) = [
        node
        for node in _interpretation_tree().body
        if isinstance(node, ast.ClassDef) and node.name == owner
    ]
    annotations = {
        node.target.id: ast.unparse(node.annotation)
        for node in owner_class.body
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name)
    }

    assert "StringConstraints(min_length=1, max_length=4096)" in annotations[field], (
        owner
    )


def test_no_prose_is_parsed_classified_or_scope_checked() -> None:
    """Breadth of phrasing is not breadth of claim.

    A caller may write a sweeping sentence in a case-local record. Nothing
    inspects it, so the sweeping and the narrow form are both admitted and both
    stored verbatim.
    """
    sweeping = "Every rewrite in every program must preserve evaluation count."
    narrow = "For this report, this rewrite should preserve evaluation count."

    for supplied in (sweeping, narrow):
        value = _expected_property(expected_property_statement=supplied)
        assert value.expected_property_statement == supplied
        assert _payload(value)["expected_property_statement"] == supplied
    # The two differ only in their prose; neither is reclassified.
    assert _expected_property(expected_property_statement=sweeping) != (
        _expected_property(expected_property_statement=narrow)
    )


# --- epistemic counterexamples -------------------------------------------------


def test_an_explanation_is_not_a_verified_root_cause() -> None:
    """A root-cause-shaped account establishes no root cause."""
    root_cause_shaped = (
        "The caller accounts for the deviation by the rewritten assertion "
        "evaluating the operand twice, which they say is the root cause."
    )
    explanation = _explanation(explanation_statement=root_cause_shaped)

    assert explanation.explanation_statement == root_cause_shaped
    # The prose may say "root cause"; the record carries no such field, no
    # verification, and no key by which a consumer could read one.
    assert tuple(SuppliedFaultExplanation.model_fields) == EXPLANATION_FIELDS
    for absent in ("root_cause", "verified", "established", "proof", "cause"):
        assert absent not in SuppliedFaultExplanation.model_fields, absent
        assert f'"{absent}":' not in explanation.model_dump_json(), absent
    assert SuppliedFaultExplanation.model_computed_fields == {}


def test_an_explanation_is_not_a_reviewed_interpretation() -> None:
    explanation = _explanation()

    for absent in ("review", "reviewed", "accepted", "approved", "reviewer"):
        assert absent not in SuppliedFaultExplanation.model_fields, absent
    assert tuple(_payload(explanation)) == EXPLANATION_FIELDS


def test_an_explanation_is_not_more_probable_than_a_hypothesis() -> None:
    """Neither record carries a rank, a weight, or anything to compare."""
    explanation = _explanation()
    hypothesis = _hypothesis()

    for model in (SuppliedFaultExplanation, SuppliedFaultHypothesis):
        for absent in ("probability", "likelihood", "confidence", "strength", "rank"):
            assert absent not in model.model_fields, (model.__name__, absent)
    assert set(_payload(explanation)) & set(_payload(hypothesis)) == {"report"}
    # "More probable than" is a relation, so the records must not be rankable.
    with pytest.raises(TypeError):
        _ = explanation < hypothesis  # type: ignore[operator]
    with pytest.raises(TypeError):
        _ = hypothesis < explanation  # type: ignore[operator]
    assert explanation != hypothesis


def test_a_hypothesis_is_not_an_explanation_and_neither_converts() -> None:
    """There is no promotion, lifecycle, or transition between the two."""
    assert not issubclass(SuppliedFaultHypothesis, SuppliedFaultExplanation)
    assert not issubclass(SuppliedFaultExplanation, SuppliedFaultHypothesis)
    assert SuppliedFaultHypothesis is not SuppliedFaultExplanation

    hypothesis = _hypothesis()
    with pytest.raises(ValidationError):
        SuppliedFaultExplanation.model_validate(hypothesis)
    with pytest.raises(ValidationError):
        SuppliedFaultHypothesis.model_validate(_explanation())
    # Nothing on either type offers a conversion.
    for model in (SuppliedFaultExplanation, SuppliedFaultHypothesis):
        beyond = {name for name in dir(model) if not name.startswith("_")} - set(
            dir(BaseModel)
        )
        assert beyond == set(), model.__name__


def test_identical_prose_in_two_kinds_stays_two_distinct_records() -> None:
    """The same sentence in two epistemic roles is two claims, not one."""
    shared = "The supplied rewrite evaluates the operand twice."
    explanation = _explanation(explanation_statement=shared)
    hypothesis = _hypothesis(hypothesis_statement=shared)
    expected = _expected_property(expected_property_statement=shared)

    assert explanation.explanation_statement == shared
    assert hypothesis.hypothesis_statement == shared
    assert expected.expected_property_statement == shared
    assert _distinct_value_count(explanation, hypothesis, expected) == 3
    assert explanation.report == hypothesis.report == expected.report


def test_two_explanations_with_identical_prose_stay_two_records() -> None:
    first = _explanation()
    second = _explanation(explanation=SECOND_EXPLANATION)

    assert first.explanation_statement == second.explanation_statement
    assert first != second
    assert _distinct_value_count(first, second) == 2


def test_a_hypothesis_is_not_a_supported_hypothesis() -> None:
    """It stays explicitly tentative and cannot record its own resolution."""
    hypothesis = _hypothesis()

    for absent in (
        "confirmed",
        "rejected",
        "supported",
        "disproved",
        "refuted",
        "falsified",
        "probability",
        "confidence",
        "review",
        "evidence",
    ):
        assert absent not in SuppliedFaultHypothesis.model_fields, absent
        assert f'"{absent}":' not in hypothesis.model_dump_json(), absent
    assert tuple(SuppliedFaultHypothesis.model_fields) == HYPOTHESIS_FIELDS
    assert SuppliedFaultHypothesis.model_computed_fields == {}


def test_the_retained_stale_cache_fixture_is_framed_as_a_supplied_proposition() -> None:
    """Fixture discipline, asserted over this file's own case-calibrated prose.

    The retained case supports that a cache was suspected, not that it was the
    root cause, so the fixture must say so in its own words. This pins the
    fixture; the module-side claim that nothing promotes it is carried by
    `test_a_hypothesis_carries_no_position_for_a_later_result` and by the
    published-description pin.
    """
    assert "tentatively" in HYPOTHESIS_STATEMENT
    assert "The caller proposes" in HYPOTHESIS_STATEMENT
    for promoted in ("root cause", "confirmed", "established", "proves"):
        assert promoted not in HYPOTHESIS_STATEMENT.lower(), promoted
    assert type(_hypothesis()) is SuppliedFaultHypothesis


def test_an_expected_property_is_not_a_passing_test() -> None:
    """It records an expectation; nothing here executes or observes anything."""
    expected = _expected_property()

    for absent in (
        "passed",
        "outcome",
        "test_material",
        "test_run",
        "run",
        "result",
        "satisfied",
    ):
        assert absent not in SuppliedFaultExpectedProperty.model_fields, absent
        assert f'"{absent}":' not in expected.model_dump_json(), absent
    assert tuple(_payload(expected)) == EXPECTED_PROPERTY_FIELDS


def test_an_expected_property_is_not_a_universal_invariant_or_pattern() -> None:
    """Its carrier scopes it to exactly one supplied report.

    Cross-instance generalization is `S1.P07`. The scoping is structural: the
    record cannot be built without one report, and it holds no second one.
    """
    expected = _expected_property()

    assert expected.report == _report()
    assert tuple(SuppliedFaultExpectedProperty.model_fields) == (
        EXPECTED_PROPERTY_FIELDS
    )
    for absent in ("invariant", "pattern", "universal", "scope", "applies_to"):
        assert absent not in SuppliedFaultExpectedProperty.model_fields, absent
    # The same property text AND the same identity, on a second report, is a
    # second distinct record. Holding the identity constant is the point: the
    # report is what scopes the property, so it alone must separate them.
    other = _expected_property(report=_second_report())
    assert other.expected_property == expected.expected_property
    assert other.expected_property_statement == expected.expected_property_statement
    assert other.report != expected.report
    assert other != expected
    assert _distinct_value_count(other, expected) == 2


def test_an_expected_property_is_not_a_repair_acceptance_criterion() -> None:
    expected = _expected_property()

    for absent in (
        "acceptance_criterion",
        "repair_candidate",
        "accepted",
        "correct",
        "correctness",
    ):
        assert absent not in SuppliedFaultExpectedProperty.model_fields, absent
    assert tuple(_payload(expected)) == EXPECTED_PROPERTY_FIELDS


def test_an_expected_property_does_not_prove_the_current_behavior_is_wrong() -> None:
    """The report already states the deviation; the property adds no verdict."""
    expected = _expected_property()

    assert expected.report.behavioral_deviation == BEHAVIORAL_DEVIATION
    for absent in ("wrong", "violated", "proof", "proves", "verified"):
        assert absent not in SuppliedFaultExpectedProperty.model_fields, absent


@pytest.mark.parametrize(
    ("build", "identity_field", "second"),
    (
        pytest.param(_explanation, "explanation", SECOND_EXPLANATION, id="explanation"),
        pytest.param(_hypothesis, "hypothesis", SECOND_HYPOTHESIS, id="hypothesis"),
        pytest.param(
            _expected_property,
            "expected_property",
            SECOND_PROPERTY,
            id="expected-property",
        ),
    ),
)
def test_one_report_may_carry_several_records_of_one_kind(
    build: Callable[..., BaseModel],
    identity_field: str,
    second: uuid.UUID,
) -> None:
    """None, one, or several, with no winner chosen and no supersession."""
    first_record = build()
    second_record = build(second)
    model = type(first_record)

    assert getattr(first_record, "report") == getattr(second_record, "report")
    assert getattr(first_record, identity_field) != getattr(
        second_record, identity_field
    )
    assert _distinct_value_count(first_record, second_record) == 2
    for absent in ("supersedes", "superseded", "replaces", "precedence", "primary"):
        assert absent not in model.model_fields, absent


def test_one_report_may_carry_conflicting_explanations_with_no_winner() -> None:
    first = _explanation()
    second = _explanation(
        explanation=SECOND_EXPLANATION,
        explanation_statement=SECOND_EXPLANATION_STATEMENT,
    )

    assert first.report == second.report
    assert first.explanation_statement != second.explanation_statement
    # Nothing relates them, so nothing resolves them.
    assert _distinct_value_count(first, second) == 2
    assert "explanation" not in _payload(first)["report"]


def test_one_report_may_carry_conflicting_hypotheses_with_no_winner() -> None:
    first = _hypothesis()
    second = _hypothesis(
        hypothesis=SECOND_HYPOTHESIS, hypothesis_statement=SECOND_HYPOTHESIS_STATEMENT
    )

    assert first.report == second.report
    assert first.hypothesis_statement != second.hypothesis_statement
    assert _distinct_value_count(first, second) == 2


def test_the_three_kinds_are_counted_independently_for_one_report() -> None:
    """A report with hypotheses and no explanation is an ordinary state."""
    report = _report()
    hypotheses = (
        _hypothesis(report=report),
        _hypothesis(
            hypothesis=SECOND_HYPOTHESIS,
            report=report,
            hypothesis_statement=SECOND_HYPOTHESIS_STATEMENT,
        ),
    )

    assert _distinct_value_count(*hypotheses) == 2
    # The report itself holds no collection, so no count is recorded anywhere.
    for name, field in SuppliedFaultReport.model_fields.items():
        annotation = str(field.annotation).lower()
        for container in ("list", "tuple", "dict", "set"):
            assert container not in annotation, (name, container)
    assert "explanation" not in _payload(report)
    assert "expected_property" not in _payload(report)


def test_no_scenario_occurrence_candidate_run_or_evidence_is_required() -> None:
    """Every S07 record is complete with a report and nothing else."""
    for build in (_explanation, _hypothesis, _expected_property):
        value = build()
        payload = _payload(value)
        assert set(payload) == set(tuple(type(value).model_fields))
        for absent in (
            "scenario",
            "occurrence",
            "candidate",
            "repair_candidate",
            "test_material",
            "run",
            "outcome",
            "evidence",
            "source",
            "history",
        ):
            assert absent not in type(value).model_fields, absent
            assert absent not in payload, absent


MODULE_NON_CLAIMS = (
    "Nothing here is promoted by being represented.",
    "An explanation is a supplied explanatory claim, not a promoted fact.",
    "no `root_cause`, `accepted`, `verified`, `confidence`, or `review` field",
    "A hypothesis stays a hypothesis.",
    "An expected property is case-local.",
    "breadth of phrasing is not breadth of claim",
    "The three kinds do not convert into one another.",
    "this layer chooses no winner",
    "Nothing is inferred from the repair or test layers.",
    "The module performs no I/O.",
)
INVERTED_MODULE_CLAIMS = (
    "Everything is inferred",
    "makes an explanation true",
    "confirms the explanation",
    "verifies the expected property",
    "disproves every earlier hypothesis",
    "is promoted to an explanation",
    "establishes the root cause",
    "chooses the winner",
)


def test_the_module_docstring_states_its_non_claims_and_no_inversion() -> None:
    """`__doc__` is a published value, and nothing else here pins it.

    Class docstrings are pinned exactly because rewriting one changes no field,
    no key and no validator. The module docstring is the same kind of published
    prose and carries the longest statement of the Slice's non-claims, so each
    load-bearing sentence is asserted where it stands, and the inverted form of
    each is refused.
    """
    docstring = interpretation_module.__doc__
    assert docstring is not None
    flattened = " ".join(docstring.split())

    for sentence in MODULE_NON_CLAIMS:
        assert sentence in flattened, sentence
    for inverted in INVERTED_MODULE_CLAIMS:
        assert inverted not in flattened, inverted


def test_the_module_publishes_no_relation_to_the_repair_or_test_layers() -> None:
    """Co-presence in one repository manufactures no relation.

    A failed-to-passed comparison and a passing outcome may exist beside any of
    these records. The module imports neither layer and declares no field that
    could reference one, so no consumer can read a relation out of them.
    """
    # `from faultatlas.domain import fault_repair` records only the package as
    # `node.module`, so the member is resolved here too.
    reached: set[str] = set()
    for node in ast.walk(_interpretation_tree()):
        if isinstance(node, ast.Import):
            reached.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            module = cast(str, node.module)
            reached.add(module)
            reached.update(f"{module}.{alias.name}" for alias in node.names)

    for layer in (
        "faultatlas.domain.fault_repair",
        "faultatlas.domain.fault_test",
        "faultatlas.domain.fault_source_relationship",
        "faultatlas.domain.evidence",
        "faultatlas.domain.history",
        "faultatlas.domain.history_evidence_link",
        "faultatlas.domain.source",
    ):
        assert layer not in reached, layer

    # The whole file, docstring included: none of these names may appear at all.
    source = INTERPRETATION_SOURCE.read_text(encoding="utf-8")
    for forbidden in (
        "ReportedFaultTestOutcome",
        "ReportedFaultTestComparison",
        "SuppliedFaultRepairCandidate",
        "DurableEvidenceRecordReference",
        "FaultRepairCandidateIdentity",
        "FaultTestRunIdentity",
    ):
        assert forbidden not in source, forbidden


def test_a_failed_to_passed_comparison_verifies_no_expected_property() -> None:
    """The expected property has no field a comparison could ever fill.

    S06 publishes reported outcomes and comparisons. Nothing here reads one,
    and the record exposes no position where a verification result could land.
    """
    expected = _expected_property()

    assert tuple(_payload(expected)) == EXPECTED_PROPERTY_FIELDS
    assert SuppliedFaultExpectedProperty.model_computed_fields == {}
    beyond = {
        name for name in dir(SuppliedFaultExpectedProperty) if not name.startswith("_")
    } - set(dir(BaseModel))
    assert beyond == set()
    for absent in ("verified", "satisfied", "comparison", "outcome", "confirmed"):
        assert absent not in expected.model_dump_json(), absent


def test_a_hypothesis_carries_no_position_for_a_later_result() -> None:
    """`model_copy(update=...)` bypasses validation, and the surface holds.

    Pydantic's copy hatch attaches an arbitrary attribute without validating
    it. That reaches `getattr` and nothing else: the JSON payload, both
    schemas, equality and revalidation are all unchanged, so no consumer of the
    published contract can read a resolution out of it.
    """
    hypothesis = _hypothesis()
    smuggled = hypothesis.model_copy(update={"confirmed": True})

    assert getattr(smuggled, "confirmed", None) is True
    # Nothing published moves: payload, both schemas and equality are unchanged.
    assert _payload(smuggled) == _payload(hypothesis)
    assert smuggled == hypothesis
    for mode in ("validation", "serialization"):
        schema = SuppliedFaultHypothesis.model_json_schema(mode=mode)  # pyright: ignore[reportArgumentType]
        assert "confirmed" not in schema["properties"], mode
    # And the smuggled attribute does not survive a round trip through the
    # published contract, so no consumer of it can ever read the resolution.
    restored = SuppliedFaultHypothesis.model_validate_json(smuggled.model_dump_json())
    assert restored == hypothesis
    assert not hasattr(restored, "confirmed")


def test_a_later_success_disproves_no_earlier_hypothesis() -> None:
    """A hypothesis carries no place for a later result to change it."""
    hypothesis = _hypothesis()

    assert hypothesis == SuppliedFaultHypothesis.model_validate_json(
        hypothesis.model_dump_json()
    )
    # Frozen, with no resolution field: the value cannot be updated in place
    # and cannot be rebuilt into a resolved form.
    with pytest.raises(ValidationError):
        hypothesis.hypothesis_statement = SECOND_HYPOTHESIS_STATEMENT
    for absent in ("disproved", "rejected", "refuted", "falsified", "outcome"):
        assert absent not in SuppliedFaultHypothesis.model_fields, absent


# --- the module's own surface and boundaries ------------------------------------


def test_the_module_publishes_exactly_six_symbols_in_order() -> None:
    assert interpretation_module.__all__ == EXPECTED_EXPORTS
    assert [
        node.name
        for node in ast.walk(_interpretation_tree())
        if isinstance(node, ast.ClassDef)
    ] == EXPECTED_EXPORTS


DECLARED_VALIDATORS = (
    "_require_typed_python_explanation",
    "_require_typed_python_report",
    "_require_unpadded_text",
    "_require_typed_python_hypothesis",
    "_require_typed_python_report",
    "_require_unpadded_text",
    "_require_typed_python_expected_property",
    "_require_typed_python_report",
    "_require_unpadded_text",
)


def test_the_module_defines_only_the_declared_validators() -> None:
    """A promotion helper added anywhere in the module must fail here.

    `__all__` and the class-name list pin what is exported, not what exists: a
    classmethod turning a hypothesis into an explanation, or any other
    function, changes neither and would otherwise be invisible.
    """
    tree = _interpretation_tree()
    functions = [
        node.name
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)
    ]

    assert tuple(functions) == DECLARED_VALIDATORS
    for name in functions:
        assert name.startswith("_")
        assert name not in interpretation_module.__all__
    # A lambda carries no name, so the inventory above cannot see one. The
    # module declares none, which is what makes that inventory exhaustive.
    assert [node for node in ast.walk(tree) if isinstance(node, ast.Lambda)] == []


EXPECTED_MODULE_BINDINGS = frozenset(
    {
        *EXPECTED_EXPORTS,
        "uuid",
        "Annotated",
        "BaseModel",
        "ConfigDict",
        "RootModel",
        "StringConstraints",
        "ValidationInfo",
        "field_validator",
        "SuppliedFaultReport",
    }
)


def test_the_module_binds_no_name_beyond_its_exports_and_its_imports() -> None:
    """A hidden product symbol may also arrive as a plain module-level name.

    `__all__` pins what is exported and the class inventory pins what is
    defined; neither sees a module-level constant or an unexported model bound
    beside them. This pins the whole namespace instead.
    """
    bound = {
        name
        for name in vars(interpretation_module)
        if not name.startswith("__") and name.isidentifier()
    }

    assert bound == set(EXPECTED_MODULE_BINDINGS)


@pytest.mark.parametrize("model", _published_models(), ids=lambda m: m.__name__)
def test_no_record_publishes_an_attribute_beyond_its_fields(
    model: type[BaseModel],
) -> None:
    """A verdict may not arrive as a property or method either.

    Pydantic fields are not class attributes, so a clean value model adds no
    public name of its own. A `verified` or `is_root_cause` property would
    leave `model_fields` and the JSON payload untouched while still being
    reachable on the record.
    """
    beyond = {name for name in dir(model) if not name.startswith("_")} - set(
        dir(BaseModel)
    )

    assert beyond == set(), model.__name__
    assert model.model_computed_fields == {}


@pytest.mark.parametrize("identity", S07_UUID_IDENTITIES, ids=lambda i: i.__name__)
def test_no_identity_publishes_an_attribute_beyond_its_root(
    identity: type[RootModel[uuid.UUID]],
) -> None:
    beyond = {name for name in dir(identity) if not name.startswith("_")} - set(
        dir(RootModel)
    )

    assert beyond == set()
    assert identity.model_computed_fields == {}


EXPECTED_DESCRIPTIONS = {
    "FaultExplanationIdentity": (
        "Caller-assigned name for one supplied explanation record."
    ),
    "SuppliedFaultExplanation": (
        "Caller-supplied explanatory account of one published fault report."
    ),
    "FaultHypothesisIdentity": (
        "Caller-assigned name for one supplied hypothesis record."
    ),
    "SuppliedFaultHypothesis": (
        "Caller-supplied tentative proposition about one published fault report."
    ),
    "FaultExpectedPropertyIdentity": (
        "Caller-assigned name for one supplied expected-property record."
    ),
    "SuppliedFaultExpectedProperty": (
        "Caller-supplied case-local expectation for one published fault report."
    ),
}


@pytest.mark.parametrize(
    "name", tuple(EXPECTED_DESCRIPTIONS), ids=tuple(EXPECTED_DESCRIPTIONS)
)
def test_each_published_description_is_stated_as_supplied_not_established(
    name: str,
) -> None:
    """A class docstring is the `description` a consumer reads in the schema.

    Rewriting one to "verified root cause of the reported deviation" changes no
    field, no key and no validator, so nothing else here would see it. Each is
    pinned exactly, and every one attributes what it describes to the caller.
    """
    published = getattr(interpretation_module, name)

    assert published.__doc__ is not None
    assert published.__doc__.strip() == EXPECTED_DESCRIPTIONS[name]
    assert published.model_json_schema()["description"] == EXPECTED_DESCRIPTIONS[name]
    lowered = EXPECTED_DESCRIPTIONS[name].lower()
    assert lowered.startswith("caller-"), name
    for claim in ("verified", "established", "root cause", "reviewed", "confirmed"):
        assert claim not in lowered, (name, claim)


def test_the_module_is_not_re_exported_from_the_package_or_domain_root() -> None:
    assert faultatlas.__all__ == ["__version__"]
    assert not hasattr(faultatlas.domain, "__all__")
    for symbol in EXPECTED_EXPORTS:
        assert not hasattr(faultatlas, symbol)
        assert not hasattr(faultatlas.domain, symbol)


def test_the_module_imports_only_its_declared_predecessor() -> None:
    imported = {
        alias.name if isinstance(node, ast.Import) else cast(str, node.module)
        for node in ast.walk(_interpretation_tree())
        if isinstance(node, ast.Import | ast.ImportFrom)
        for alias in node.names
    }

    # An exact set: the repair, test, relationship, history and evidence layers
    # are excluded by this equality rather than by a name list.
    assert imported == {
        "uuid",
        "typing",
        "pydantic",
        "faultatlas.domain.fault",
    }


def test_no_predecessor_production_module_imports_this_one() -> None:
    """Every tracked predecessor, not a chosen few.

    The `S1.P06.S08` aggregate and the `S1.P06.S09` fault-evidence bridge are
    excluded because each is a successor rather than a predecessor:
    composing and associating the published values is what they publish, so
    they import this module by design.
    """
    predecessors = [
        name
        for name in EXPECTED_PRODUCTION_MODULES
        if name
        not in {
            "faultatlas/domain/fault_interpretation.py",
            "faultatlas/domain/fault_instance.py",
            "faultatlas/domain/fault_evidence_link.py",
        }
    ]

    assert len(predecessors) == 17
    for name in predecessors:
        source = (CHECKOUT_SOURCE_ROOT / name).read_text(encoding="utf-8")
        assert "fault_interpretation" not in source, name
        for symbol in EXPECTED_EXPORTS:
            assert symbol not in source, (name, symbol)


def test_the_tracked_production_inventory_is_twenty_modules() -> None:
    tracked = subprocess.run(  # noqa: S603 - literal argv, no shell
        ["git", "ls-files", "src/"],
        cwd=REPOSITORY_ROOT,
        capture_output=True,
        check=False,
    )
    assert tracked.returncode == 0, tracked.stderr
    observed = sorted(tracked.stdout.decode("utf-8").split())

    assert observed == [f"src/{name}" for name in EXPECTED_PRODUCTION_MODULES]
    assert len(observed) == 20
    assert "src/faultatlas/domain/fault_interpretation.py" in observed


EXPECTED_PRODUCTION_MODULES = [
    "faultatlas/__init__.py",
    "faultatlas/__main__.py",
    "faultatlas/cli.py",
    "faultatlas/domain/__init__.py",
    "faultatlas/domain/compatibility.py",
    "faultatlas/domain/evidence.py",
    "faultatlas/domain/fault.py",
    "faultatlas/domain/fault_evidence_link.py",
    "faultatlas/domain/fault_instance.py",
    "faultatlas/domain/fault_interpretation.py",
    "faultatlas/domain/fault_repair.py",
    "faultatlas/domain/fault_source_relationship.py",
    "faultatlas/domain/fault_test.py",
    "faultatlas/domain/history.py",
    "faultatlas/domain/history_evidence_link.py",
    "faultatlas/domain/identity.py",
    "faultatlas/domain/revision.py",
    "faultatlas/domain/snapshot.py",
    "faultatlas/domain/snapshot_evidence_link.py",
    "faultatlas/domain/source.py",
]


# --- the no-I/O behavioral witness ----------------------------------------------


def test_the_module_reaches_no_eventless_clock_or_environment_call() -> None:
    """The half an audit hook structurally cannot witness.

    CPython raises no audit event for `os.times`, `os.stat`, `os.environ` or
    anything in `time`, verified directly: a hook installed around them
    observes nothing. So the audit witness below cannot see a clock or
    environment read, and this screen carries that half instead.

    Every such call has to reach `os` somehow. The module imports it nowhere --
    which `test_the_module_imports_only_its_declared_predecessor` pins by exact
    set equality -- so the remaining route is an attribute on a module it does
    import, as in `uuid.os.times()`. That spelling is refused here, along with
    the clock and environment names themselves.
    """
    called = {
        node.func.id
        for node in ast.walk(_interpretation_tree())
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }

    assert not called & {"open", "eval", "exec", "compile", "__import__", "print"}
    body = " ".join(
        INTERPRETATION_SOURCE.read_text(encoding="utf-8").split('"""', 2)[-1].split()
    )
    for forbidden in (
        "import os",
        "import io",
        "import time",
        "Path(",
        "requests",
        "urllib",
        "now(",
        "subprocess",
        "getattr(",
        # Reach-through to an eventless call via an already-imported module.
        ".os.",
        "os.",
        "time.",
        "datetime",
        "environ",
        "getenv",
        "perf_counter",
        "monotonic",
    ):
        assert forbidden not in body, forbidden


NO_IO_PROBE = """
import json
import sys
import uuid

# Enumerating dangerous events misses whichever one is not listed --
# `os.utime`, `os.putenv`, `os.listdir` and `os.stat` are all real events that
# such a list forgets. The set is inverted instead: every event is recorded,
# and only the interpreter's own import and object machinery is allowed. The
# import phase additionally needs the filesystem scan the import system does;
# the use phase does not, so it allows no `os.` event at all.
IMPORT_PHASE_ALLOWED = frozenset(
    {
        "builtins.id", "compile", "exec", "import", "marshal.loads",
        "object.__getattr__", "object.__setattr__", "open", "os.listdir",
        "sys._getframe", "sys._getframemodulename",
    }
)
USE_PHASE_ALLOWED = frozenset(
    {
        "builtins.id", "compile", "exec", "import", "marshal.loads",
        "object.__getattr__", "object.__setattr__", "open",
        "sys._getframe", "sys._getframemodulename",
    }
)
WRITE_MODES = frozenset("wax+")
ENTROPY = ("/dev/urandom", "/dev/random")
INTERPRETER_ROOTS = tuple(
    sorted({sys.prefix, sys.base_prefix, sys.exec_prefix, sys.base_exec_prefix})
)
CHECKOUT_SOURCE_ROOT = sys.argv[6]
MODULE_SUFFIXES = (".py", ".pyc", ".pth", ".so")

violations = []
opened = []
allowed = IMPORT_PHASE_ALLOWED
recording = False


def hook(event, args):
    if not recording:
        return
    if event not in allowed:
        violations.append(event)
    if event == "open":
        path = str(args[0])
        mode = str(args[1] or "")
        if set(mode) & WRITE_MODES:
            opened.append((path, mode))
        elif path in ENTROPY or path.startswith(INTERPRETER_ROOTS):
            pass
        elif not (
            path.startswith(CHECKOUT_SOURCE_ROOT) and path.endswith(MODULE_SUFFIXES)
        ):
            opened.append((path, mode))


sys.addaudithook(hook)
recording = True

import faultatlas.domain.fault_interpretation as module
from faultatlas.domain.fault import (
    FaultInstanceIdentity,
    FaultReportIdentity,
    FaultRepositoryContext,
    SuppliedFaultReport,
)
from faultatlas.domain.identity import (
    ProviderKey,
    ProviderRepositoryId,
    RepositoryIdentity,
)

import_violations = list(violations)
violations.clear()
allowed = USE_PHASE_ALLOWED

report = SuppliedFaultReport(
    report=FaultReportIdentity(uuid.UUID(sys.argv[1])),
    context=FaultRepositoryContext(
        fault=FaultInstanceIdentity(uuid.UUID(sys.argv[2])),
        repository=RepositoryIdentity(
            provider=ProviderKey("github"),
            provider_repository_id=ProviderRepositoryId(sys.argv[3]),
        ),
    ),
    problem_statement="probe problem",
    behavioral_deviation="probe deviation",
)
explanation = module.SuppliedFaultExplanation(
    explanation=module.FaultExplanationIdentity(uuid.UUID(sys.argv[4])),
    report=report,
    explanation_statement="probe explanation",
)
hypothesis = module.SuppliedFaultHypothesis(
    hypothesis=module.FaultHypothesisIdentity(uuid.UUID(sys.argv[5])),
    report=report,
    hypothesis_statement="probe hypothesis",
)
expected = module.SuppliedFaultExpectedProperty(
    expected_property=module.FaultExpectedPropertyIdentity(uuid.UUID(sys.argv[7])),
    report=report,
    expected_property_statement="probe expectation",
)

for value, model in (
    (explanation, module.SuppliedFaultExplanation),
    (hypothesis, module.SuppliedFaultHypothesis),
    (expected, module.SuppliedFaultExpectedProperty),
):
    assert model.model_validate_json(value.model_dump_json()) == value
    model.model_validate(value)
    model.model_json_schema()
    try:
        model.model_validate(value.model_dump())
    except Exception:
        pass

recording = False
print(
    json.dumps(
        {
            "import_violations": sorted(set(import_violations)),
            "use_violations": sorted(set(violations)),
            "opened": opened,
        }
    )
)
"""


def test_the_module_starts_no_process_and_touches_no_file() -> None:
    """The closure is asserted as a property, not as a list of spellings.

    A list of dangerous event names misses whichever one is absent from it, so
    the set is inverted: every audit event raised is recorded, and only the
    interpreter's own import and object machinery is allowed through. An
    `os.utime`, an `os.putenv`, an `os.listdir` or a `subprocess.Popen` fails
    because it is not on the allowlist, however it is spelled and whichever
    already-imported module it is reached through.

    The hook is installed before the module is imported and covers import,
    construction, revalidation, serialization, refusal of a Python dump and
    schema generation, in an isolated interpreter so it cannot contaminate any
    other test. The import phase additionally allows the filesystem scan the
    import system itself performs; the use phase allows no `os` event at all.

    What this cannot witness: CPython raises no audit event for `os.times`,
    `os.stat`, `os.environ` or `time`, so clock and environment reads are
    invisible here and are carried by
    `test_the_module_reaches_no_eventless_clock_or_environment_call` instead.
    """
    environment = os.environ.copy()
    environment.pop("PYTHONPATH", None)
    result = subprocess.run(
        [
            sys.executable,
            "-I",
            "-B",
            "-c",
            NO_IO_PROBE,
            SUPPLIED_REPORT_TEXT,
            SUPPLIED_FAULT_TEXT,
            RETAINED_REPOSITORY_ID,
            SUPPLIED_EXPLANATION_TEXT,
            SUPPLIED_HYPOTHESIS_TEXT,
            str(CHECKOUT_SOURCE_ROOT),
            SUPPLIED_PROPERTY_TEXT,
        ],
        cwd=REPOSITORY_ROOT,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, (
        f"audit probe failed\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )
    reported: dict[str, Any] = json.loads(result.stdout.strip().splitlines()[-1])

    assert reported["import_violations"] == []
    assert reported["use_violations"] == []
    assert reported["opened"] == []


# --- the roadmap transition -------------------------------------------------


def _current_status_section() -> str:
    roadmap = _roadmap()
    start = roadmap.index("## Current status")
    end = roadmap.index("## Program stages")
    assert start < end
    return roadmap[start:end]


def test_the_current_status_section_states_exactly_the_live_lifecycle() -> None:
    """A direct structural witness over the section every Slice must migrate.

    `## Current status` is deliberately mutable and is not digest-protected, so
    it needs an oracle that reads it directly rather than a document-wide phrase
    search that another section could satisfy by coincidence.
    """
    section = _current_status_section()

    assert "`S1.P06` is active and incomplete" in section
    for index in range(1, 12):
        assert f"`S1.P06.S{index:02d}` is complete" in section, index
    assert "`S1.P06.S11` is complete" in section
    assert "`S1.P06.S12` is next and not started" in section
    assert "`S1.P07` through `S1.P10` remain not started" in section

    # Nothing beyond S10 may be claimed complete, and no superseded gate stands.
    for index in range(12, 13):
        assert f"`S1.P06.S{index:02d}` is complete" not in section, index
    for index in range(1, 12):
        assert f"`S1.P06.S{index:02d}` is next and not started" not in section, index
    assert "`S1.P06` is complete" not in section
    assert "`S1.P06` is `eligible_to_begin`" not in section


def test_the_roadmap_carries_exactly_one_live_gate() -> None:
    roadmap = _roadmap()

    live_next = re.findall(
        r"`(S1\.P\d\d(?:\.S\d\d)?)` is next and not started", roadmap
    )
    assert live_next, "the roadmap names no next gate"
    assert set(live_next) == {"S1.P06.S12"}, sorted(set(live_next))
    live_phases = re.findall(r"`(S1\.P\d\d)` is active and incomplete", roadmap)
    assert set(live_phases) == {"S1.P06"}, sorted(set(live_phases))
    for line in ROADMAP.read_text(encoding="utf-8").splitlines():
        if "next and not started" in line:
            assert "`S1.P06.S12`" in line, line


def test_the_roadmap_records_the_p06_s07_transition() -> None:
    raw = ROADMAP.read_text(encoding="utf-8")
    roadmap = _roadmap()
    mapping = roadmap.split("## Current-code mapping", 1)
    assert len(mapping) == 2, "roadmap must retain a current-code mapping section"
    current = mapping[1]

    assert "`S1.P06.S07` is complete" in roadmap
    assert "`S1.P06.S08` is complete" in roadmap
    assert "`S1.P06.S09` is complete" in roadmap
    assert "`S1.P06.S10` is complete" in roadmap
    assert "`S1.P06.S11` is complete" in roadmap
    assert "`S1.P06.S12` is next and not started" in roadmap
    assert (
        "`S1.P06.S07` — Case-Local Explanation, Hypothesis, and Expected "
        "Property (complete)" in roadmap
    )
    assert "The `S1.P06` route is provisional beyond `S1.P06.S11`." in roadmap

    assert "faultatlas.domain.fault_interpretation" in current
    for symbol in EXPECTED_EXPORTS:
        assert f"`{symbol}`" in current
    assert "Production Python sources are 20." in current

    # The superseded live gate and the provisional S07 title must be retired.
    assert "`S1.P06.S07` is next and not started" not in roadmap
    assert (
        "`S1.P06.S07` — Case-local explanation, hypothesis, and expected "
        "property (next, not started)" not in roadmap
    )
    assert "`S1.P06.S12` is complete" not in roadmap
    assert "Production Python sources are 17." not in roadmap
    assert "- **S1.P06 — Fault Instance Model**" not in raw


def test_the_roadmap_states_the_s07_decisions_and_non_claims() -> None:
    roadmap = _roadmap()

    assert "production Python sources move from 17 to 18" in roadmap
    assert "three different epistemic acts" in roadmap
    assert "An explanation is a supplied explanatory claim, not a promoted fact." in (
        roadmap
    )
    assert "A hypothesis stays explicitly tentative" in roadmap
    assert "An expected property is case-local." in roadmap
    assert "is `S1.P07` work and is not begun here" in roadmap
    assert "The three kinds do not convert into one another" in roadmap
    assert "this layer chooses no winner" in roadmap
    assert "Nothing is inferred from the repair or test layers." in roadmap
    assert "co-presence manufactures none" in roadmap
    assert "all ten `S1.P06` UUID-rooted identities stay" in roadmap
    assert "breadth of phrasing is not breadth of claim" in roadmap
    assert "became `S1.P06.S08` work" in roadmap


def test_the_roadmap_preserves_the_predecessor_history_as_written() -> None:
    roadmap = _roadmap()

    assert (
        "`S1.P06.S01` publishes one new production module, `faultatlas.domain.fault`, "
        "whose initial `__all__` is exactly `FaultInstanceIdentity` and "
        "`FaultRepositoryContext`." in roadmap
    )
    assert "production Python sources move from 16 to 17" in roadmap
    assert "`S1.P05` is complete" in roadmap
    assert "`S1.P06` was `eligible_to_begin`" in roadmap


# --- packaging and an isolated installed-wheel smoke --------------------------


ISOLATED_SMOKE = """
import json
import os
import sys
import uuid
from pathlib import Path

installed = Path(os.environ["INSTALLED_ROOT"]).resolve()
checkout = Path(os.environ["CHECKOUT_SOURCE_ROOT"]).resolve()
sys.path = [entry for entry in sys.path if Path(entry).resolve() != checkout]
sys.path.insert(0, str(installed))

import faultatlas.domain.fault_interpretation as interpretation_module
from faultatlas.domain.fault import (
    FaultInstanceIdentity,
    FaultReportIdentity,
    FaultRepositoryContext,
    SuppliedFaultReport,
)
from faultatlas.domain.fault_interpretation import (
    FaultExpectedPropertyIdentity,
    FaultExplanationIdentity,
    FaultHypothesisIdentity,
    SuppliedFaultExpectedProperty,
    SuppliedFaultExplanation,
    SuppliedFaultHypothesis,
)
from faultatlas.domain.identity import (
    ProviderKey,
    ProviderRepositoryId,
    RepositoryIdentity,
)

module = Path(interpretation_module.__file__).resolve()
assert module.is_relative_to(installed), module
assert not module.is_relative_to(checkout), module
assert interpretation_module.__all__ == [
    "FaultExplanationIdentity",
    "SuppliedFaultExplanation",
    "FaultHypothesisIdentity",
    "SuppliedFaultHypothesis",
    "FaultExpectedPropertyIdentity",
    "SuppliedFaultExpectedProperty",
]

report = SuppliedFaultReport(
    report=FaultReportIdentity(uuid.UUID(os.environ["REPORT_UUID"])),
    context=FaultRepositoryContext(
        fault=FaultInstanceIdentity(uuid.UUID(os.environ["FAULT_UUID"])),
        repository=RepositoryIdentity(
            provider=ProviderKey("github"),
            provider_repository_id=ProviderRepositoryId(os.environ["REPOSITORY_ID"]),
        ),
    ),
    problem_statement=os.environ["PROBLEM_STATEMENT"],
    behavioral_deviation=os.environ["BEHAVIORAL_DEVIATION"],
)
explanation = SuppliedFaultExplanation(
    explanation=FaultExplanationIdentity(uuid.UUID(os.environ["EXPLANATION_UUID"])),
    report=report,
    explanation_statement=os.environ["EXPLANATION_STATEMENT"],
)
hypothesis = SuppliedFaultHypothesis(
    hypothesis=FaultHypothesisIdentity(uuid.UUID(os.environ["HYPOTHESIS_UUID"])),
    report=report,
    hypothesis_statement=os.environ["HYPOTHESIS_STATEMENT"],
)
expected = SuppliedFaultExpectedProperty(
    expected_property=FaultExpectedPropertyIdentity(
        uuid.UUID(os.environ["PROPERTY_UUID"])
    ),
    report=report,
    expected_property_statement=os.environ["PROPERTY_STATEMENT"],
)

for value, model in (
    (explanation, SuppliedFaultExplanation),
    (hypothesis, SuppliedFaultHypothesis),
    (expected, SuppliedFaultExpectedProperty),
):
    assert model.model_validate_json(value.model_dump_json()) == value

print(
    json.dumps(
        {
            "module": str(module),
            "explanation_identity": FaultExplanationIdentity(
                uuid.UUID(os.environ["EXPLANATION_UUID"])
            ).model_dump_json(),
            "hypothesis_identity": FaultHypothesisIdentity(
                uuid.UUID(os.environ["HYPOTHESIS_UUID"])
            ).model_dump_json(),
            "property_identity": FaultExpectedPropertyIdentity(
                uuid.UUID(os.environ["PROPERTY_UUID"])
            ).model_dump_json(),
            "explanation": explanation.model_dump_json(),
            "hypothesis": hypothesis.model_dump_json(),
            "expected_property": expected.model_dump_json(),
        }
    )
)
"""


@pytest.fixture(scope="session")
def offline_distributions(
    tmp_path_factory: pytest.TempPathFactory,
) -> tuple[Path, Path]:
    uv = shutil.which("uv")
    assert uv is not None, "uv must be available to build the supported distributions"

    root = tmp_path_factory.mktemp("fault-interpretation-package")
    output = root / "distributions"
    output.mkdir()
    environment = os.environ.copy()
    environment.update(
        {
            "PYTHONDONTWRITEBYTECODE": "1",
            "UV_CACHE_DIR": str(root / "uv-cache"),
            "UV_NO_SYNC": "1",
            "UV_OFFLINE": "1",
        }
    )
    result = subprocess.run(
        [uv, "build", "--offline", "--no-create-gitignore", "--out-dir", str(output)],
        cwd=REPOSITORY_ROOT,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"offline build failed\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )
    wheels = tuple(output.glob("*.whl"))
    sdists = tuple(output.glob("*.tar.gz"))
    assert len(wheels) == 1, f"expected one wheel, found {wheels!r}"
    assert len(sdists) == 1, f"expected one sdist, found {sdists!r}"
    return wheels[0], sdists[0]


def test_the_wheel_ships_twenty_modules_and_no_corpus_or_test_material(
    offline_distributions: tuple[Path, Path],
) -> None:
    wheel, _ = offline_distributions
    with zipfile.ZipFile(wheel) as archive:
        names = tuple(info.filename for info in archive.infolist() if not info.is_dir())

    modules = sorted(name for name in names if name.endswith(".py"))
    assert modules == EXPECTED_PRODUCTION_MODULES
    assert len(modules) == 20
    for required in (
        "faultatlas/domain/fault.py",
        "faultatlas/domain/fault_instance.py",
        "faultatlas/domain/fault_interpretation.py",
        "faultatlas/domain/fault_repair.py",
        "faultatlas/domain/fault_source_relationship.py",
        "faultatlas/domain/fault_test.py",
    ):
        assert required in modules
    for name in names:
        assert "reference_corpus" not in name
        assert not name.startswith("tests/")
        assert not name.startswith("docs/")


def test_the_sdist_ships_twenty_modules_and_no_corpus_or_test_material(
    offline_distributions: tuple[Path, Path],
) -> None:
    _, sdist = offline_distributions
    with tarfile.open(sdist, "r:gz") as archive:
        names = tuple(member.name for member in archive.getmembers() if member.isfile())

    modules = sorted(
        name.split("/src/", 1)[1] for name in names if name.endswith(".py")
    )
    assert modules == EXPECTED_PRODUCTION_MODULES
    assert len(modules) == 20
    for required in (
        "faultatlas/domain/fault.py",
        "faultatlas/domain/fault_instance.py",
        "faultatlas/domain/fault_interpretation.py",
        "faultatlas/domain/fault_repair.py",
        "faultatlas/domain/fault_source_relationship.py",
        "faultatlas/domain/fault_test.py",
    ):
        assert required in modules
    for name in names:
        parts = Path(name).parts
        assert "reference_corpus" not in parts
        assert "tests" not in parts
        assert "docs" not in parts


def test_the_installed_wheel_exercises_all_six_new_symbols(
    offline_distributions: tuple[Path, Path],
    tmp_path: Path,
) -> None:
    """All six S07 symbols must run from the wheel copy, not the checkout."""
    wheel, _ = offline_distributions
    installed = tmp_path / "installed"
    installed.mkdir()
    with zipfile.ZipFile(wheel) as archive:
        archive.extractall(installed)

    assert (installed / "faultatlas/domain/fault_interpretation.py").is_file()

    environment = os.environ.copy()
    environment.update(
        {
            "INSTALLED_ROOT": str(installed),
            "CHECKOUT_SOURCE_ROOT": str(CHECKOUT_SOURCE_ROOT),
            "FAULT_UUID": SUPPLIED_FAULT_TEXT,
            "REPORT_UUID": SUPPLIED_REPORT_TEXT,
            "EXPLANATION_UUID": SUPPLIED_EXPLANATION_TEXT,
            "HYPOTHESIS_UUID": SUPPLIED_HYPOTHESIS_TEXT,
            "PROPERTY_UUID": SUPPLIED_PROPERTY_TEXT,
            "REPOSITORY_ID": RETAINED_REPOSITORY_ID,
            "PROBLEM_STATEMENT": PROBLEM_STATEMENT,
            "BEHAVIORAL_DEVIATION": BEHAVIORAL_DEVIATION,
            "EXPLANATION_STATEMENT": EXPLANATION_STATEMENT,
            "HYPOTHESIS_STATEMENT": HYPOTHESIS_STATEMENT,
            "PROPERTY_STATEMENT": EXPECTED_PROPERTY_STATEMENT,
            "PYTHONDONTWRITEBYTECODE": "1",
        }
    )
    environment.pop("PYTHONPATH", None)
    result = subprocess.run(
        [sys.executable, "-I", "-c", ISOLATED_SMOKE],
        cwd=tmp_path,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, (
        f"isolated wheel smoke failed\nstdout:\n{result.stdout}\n"
        f"stderr:\n{result.stderr}"
    )
    reported: dict[str, Any] = json.loads(result.stdout.strip().splitlines()[-1])
    assert Path(reported["module"]).is_relative_to(installed)
    assert not Path(reported["module"]).is_relative_to(CHECKOUT_SOURCE_ROOT)
    assert json.loads(reported["explanation_identity"]) == SUPPLIED_EXPLANATION_TEXT
    assert json.loads(reported["hypothesis_identity"]) == SUPPLIED_HYPOTHESIS_TEXT
    assert json.loads(reported["property_identity"]) == SUPPLIED_PROPERTY_TEXT
    assert json.loads(reported["explanation"]) == _payload(_explanation())
    assert json.loads(reported["hypothesis"]) == _payload(_hypothesis())
    assert json.loads(reported["expected_property"]) == _payload(_expected_property())
