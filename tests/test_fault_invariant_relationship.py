"""Synthetic S04 association, full-member and owning-schema witnesses."""

from __future__ import annotations

import ast
import hashlib
import json
import os
import subprocess
import sys
import uuid
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from pydantic import BaseModel, ValidationError

import faultatlas.domain.invariant_relationship as relation_module
from faultatlas.domain.evidence import (
    ArtifactByteLength,
    ArtifactSha256Digest,
    DurableEvidenceRecordReference,
    EvidenceCanonicalization,
    EvidenceRecordFormat,
    EvidenceVersion,
)
from faultatlas.domain.fault import (
    FaultInstanceIdentity,
    FaultReportIdentity,
    FaultRepositoryContext,
    SuppliedFaultReport,
)
from faultatlas.domain.fault_evidence_link import FaultInstanceEvidenceLink
from faultatlas.domain.fault_instance import FaultInstance
from faultatlas.domain.fault_interpretation import (
    FaultExpectedPropertyIdentity,
    FaultHypothesisIdentity,
    SuppliedFaultExpectedProperty,
    SuppliedFaultHypothesis,
)
from faultatlas.domain.identity import (
    ProviderKey,
    ProviderRepositoryId,
    RepositoryIdentity,
)
from faultatlas.domain.invariant import FaultInvariantIdentity, SuppliedFaultInvariant
from faultatlas.domain.invariant_relationship import (
    FaultInvariantExpectedPropertyAssociation,
    FaultPatternInvariantAssociation,
)
from faultatlas.domain.pattern import FaultPatternIdentity, SuppliedFaultPattern
from faultatlas.domain.pattern_exemplar import FaultPatternExemplarAssociation

ROOT = Path(__file__).resolve().parents[1]
MODULE = "src/faultatlas/domain/invariant_relationship.py"
PATTERN_COMPOSITION_MODULE = "src/faultatlas/domain/pattern_composition.py"
PATTERN_TEXT = "A supplied  重复 callback pattern."
INVARIANT_TEXT = "If condition A holds,\n preserve  count and order."
PROPERTY_TEXT = "This report expects exactly one evaluation."
MEMBERSHIP_ERROR = "expected_property is not a full-record member of fault_instance.expected_properties"
MODELS: tuple[tuple[type[BaseModel], tuple[str, ...]], ...] = (
    (FaultPatternInvariantAssociation, ("pattern", "invariant")),
    (
        FaultInvariantExpectedPropertyAssociation,
        ("invariant", "fault_instance", "expected_property"),
    ),
)
POSITIONS = tuple((model, field) for model, fields in MODELS for field in fields)
# Explicit predecessor wire positions: no expected schema is derived from a dump.
EMPTY_COLLECTIONS = (
    "scenarios",
    "occurrences",
    "source_object_associations",
    "history_fact_associations",
    "repair_candidates",
    "repair_revision_associations",
    "repair_change_set_associations",
    "test_materials",
    "test_runs",
    "test_outcomes",
    "test_run_revision_associations",
    "test_comparisons",
    "explanations",
    "hypotheses",
)


def _pattern(text: str = PATTERN_TEXT, identifier: int = 1) -> SuppliedFaultPattern:
    return SuppliedFaultPattern(
        pattern=FaultPatternIdentity(uuid.UUID(int=identifier)), pattern_statement=text
    )


def _invariant(
    text: str = INVARIANT_TEXT, identifier: int = 2
) -> SuppliedFaultInvariant:
    return SuppliedFaultInvariant(
        invariant=FaultInvariantIdentity(uuid.UUID(int=identifier)),
        invariant_statement=text,
    )


def _report(
    repository: str = "synthetic-a", identifier: int = 11, fault: int = 10
) -> SuppliedFaultReport:
    return SuppliedFaultReport(
        report=FaultReportIdentity(uuid.UUID(int=identifier)),
        context=FaultRepositoryContext(
            fault=FaultInstanceIdentity(uuid.UUID(int=fault)),
            repository=RepositoryIdentity(
                provider=ProviderKey("github"),
                provider_repository_id=ProviderRepositoryId(repository),
            ),
        ),
        problem_statement="A caller describes changed evaluation behavior.",
        behavioral_deviation="The caller reports repeated side effects.",
    )


def _property(
    report: SuppliedFaultReport | None = None,
    text: str = PROPERTY_TEXT,
    identifier: int = 12,
) -> SuppliedFaultExpectedProperty:
    return SuppliedFaultExpectedProperty(
        expected_property=FaultExpectedPropertyIdentity(uuid.UUID(int=identifier)),
        report=_report() if report is None else report,
        expected_property_statement=text,
    )


def _case() -> FaultInstance:
    report = _report()
    return FaultInstance(
        fault=report.context.fault,
        reports=(report,),
        expected_properties=(_property(report),),
    )


def _fields(value: BaseModel) -> dict[str, Any]:
    return {name: getattr(value, name) for name in type(value).model_fields}


def _values(model: type[BaseModel]) -> dict[str, Any]:
    if model is FaultPatternInvariantAssociation:
        return {"pattern": _pattern(), "invariant": _invariant()}
    case = _case()
    return {
        "invariant": _invariant(),
        "fault_instance": case,
        "expected_property": case.expected_properties[0],
    }


def _errors(error: ValidationError) -> list[tuple[tuple[str | int, ...], str]]:
    return [(item["loc"], item["type"]) for item in error.errors()]


def _authored_wire(model: type[BaseModel]) -> dict[str, Any]:
    invariant = {
        "invariant": str(uuid.UUID(int=2)),
        "invariant_statement": INVARIANT_TEXT,
    }
    if model is FaultPatternInvariantAssociation:
        return {
            "pattern": {
                "pattern": str(uuid.UUID(int=1)),
                "pattern_statement": PATTERN_TEXT,
            },
            "invariant": invariant,
        }
    report = {
        "report": str(uuid.UUID(int=11)),
        "context": {
            "fault": str(uuid.UUID(int=10)),
            "repository": {
                "schema_version": 1,
                "provider": "github",
                "provider_repository_id": "synthetic-a",
            },
        },
        "problem_statement": "A caller describes changed evaluation behavior.",
        "behavioral_deviation": "The caller reports repeated side effects.",
    }
    expected = {
        "expected_property": str(uuid.UUID(int=12)),
        "report": report,
        "expected_property_statement": PROPERTY_TEXT,
    }
    case = {
        "fault": str(uuid.UUID(int=10)),
        "reports": [report],
        **{name: [] for name in EMPTY_COLLECTIONS},
        "expected_properties": [expected],
    }
    return {
        "invariant": invariant,
        "fault_instance": case,
        "expected_property": expected,
    }


@pytest.mark.parametrize("model,fields", MODELS)
def test_exact_surface_config_and_authored_full_wire(
    model: type[BaseModel], fields: tuple[str, ...]
) -> None:
    assert relation_module.__all__ == [
        "FaultPatternInvariantAssociation",
        "FaultInvariantExpectedPropertyAssociation",
    ]
    assert model.__bases__ == (BaseModel,)
    assert tuple(model.model_fields) == fields
    assert all(
        field.is_required() and field.default_factory is None and field.alias is None
        for field in model.model_fields.values()
    )
    assert dict(model.model_config) == {
        "frozen": True,
        "extra": "forbid",
        "strict": True,
        "revalidate_instances": "always",
        "validate_default": True,
    }
    assert model.model_computed_fields == {} and model.__private_attributes__ == {}
    assert {name for name in dir(model) if not name.startswith("_")} <= set(
        dir(BaseModel)
    )
    values = _values(model)
    before = {key: value.model_dump_json() for key, value in values.items()}
    linked = model.model_validate(values)
    assert linked.model_dump(mode="json") == _authored_wire(model)
    assert list(json.loads(linked.model_dump_json())) == list(fields)
    assert model.model_validate_json(json.dumps(_authored_wire(model))) == linked
    assert model.model_validate_json(linked.model_dump_json()) == linked
    assert model.model_validate(linked) == linked
    assert {key: value.model_dump_json() for key, value in values.items()} == before
    for projection in (linked.model_dump(), json.loads(linked.model_dump_json())):
        with pytest.raises(ValidationError) as failure:
            model.model_validate(projection)
        assert _errors(failure.value) == [((field,), "value_error") for field in fields]


@pytest.mark.parametrize("model,field", POSITIONS)
@pytest.mark.parametrize(
    "kind",
    [
        "none",
        "uuid",
        "identity",
        "string",
        "mapping",
        "typed_mapping",
        "foreign",
        "attributes",
        "swapped",
    ],
)
def test_every_python_endpoint_requires_its_declared_type(
    model: type[BaseModel], field: str, kind: str
) -> None:
    class Foreign(BaseModel):
        value: object

    values = _values(model)
    endpoint = values[field]
    identity_field = {
        "pattern": "pattern",
        "invariant": "invariant",
        "fault_instance": "fault",
        "expected_property": "expected_property",
    }[field]
    swapped = _invariant() if field == "pattern" else _pattern()
    invalid: dict[str, object] = {
        "none": None,
        "uuid": uuid.UUID(int=1),
        "identity": getattr(endpoint, identity_field),
        "string": "supplied",
        "mapping": endpoint.model_dump(),
        "typed_mapping": _fields(endpoint),
        "foreign": Foreign(value=endpoint),
        "attributes": SimpleNamespace(**_fields(endpoint)),
        "swapped": swapped,
    }
    values[field] = invalid[kind]
    for attributes in (False, True):
        with pytest.raises(ValidationError) as failure:
            model.model_validate(values, from_attributes=attributes)
        assert _errors(failure.value) == [((field,), "value_error")]
    with pytest.raises(ValidationError) as failure:
        model(**values)
    assert _errors(failure.value) == [((field,), "value_error")]


@pytest.mark.parametrize("model,field", POSITIONS)
def test_missing_and_frozen_positions(model: type[BaseModel], field: str) -> None:
    values = _values(model)
    linked = model.model_validate(values)
    del values[field]
    with pytest.raises(ValidationError) as missing:
        model.model_validate(values)
    assert _errors(missing.value) == [((field,), "missing")]
    with pytest.raises(ValidationError) as frozen:
        setattr(linked, field, getattr(linked, field))
    assert _errors(frozen.value) == [((field,), "frozen_instance")]


@pytest.mark.parametrize("model,fields", MODELS)
@pytest.mark.parametrize(
    "extra",
    [
        "rationale",
        "relationship_id",
        "kind",
        "support",
        "confidence",
        "review",
        "status",
        "applicability",
        "violation",
        "predicate",
    ],
)
def test_extra_relationship_semantics_are_not_preallocated(
    model: type[BaseModel], fields: tuple[str, ...], extra: str
) -> None:
    values = _values(model)
    values[extra] = "supplied"
    with pytest.raises(ValidationError) as failure:
        model.model_validate(values)
    assert _errors(failure.value) == [((extra,), "extra_forbidden")]
    wire = _authored_wire(model) | {extra: "supplied"}
    with pytest.raises(ValidationError) as failure:
        model.model_validate_json(json.dumps(wire))
    assert _errors(failure.value) == [((extra,), "extra_forbidden")]
    assert tuple(model.model_fields) == fields


@pytest.mark.parametrize("model,fields", MODELS)
def test_ordinary_endpoint_subclasses_and_legal_constructed_values(
    model: type[BaseModel], fields: tuple[str, ...]
) -> None:
    class PatternChild(SuppliedFaultPattern):
        pass

    class InvariantChild(SuppliedFaultInvariant):
        pass

    class CaseChild(FaultInstance):
        pass

    class PropertyChild(SuppliedFaultExpectedProperty):
        pass

    children: dict[str, type[BaseModel]] = {
        "pattern": PatternChild,
        "invariant": InvariantChild,
        "fault_instance": CaseChild,
        "expected_property": PropertyChild,
    }
    values = _values(model)
    subclasses = {
        field: children[field](**_fields(value)) for field, value in values.items()
    }
    linked = model.model_validate(subclasses)
    assert linked == model.model_validate(values)
    for field in fields:
        assert type(getattr(linked, field)) is type(values[field])
    unchecked: dict[str, Any] = {}
    for field, value in values.items():
        endpoint: BaseModel = value
        unchecked[field] = type(endpoint).model_construct(**_fields(endpoint))
    assert model.model_validate(unchecked) == linked


@pytest.mark.parametrize("model,field", POSITIONS)
@pytest.mark.parametrize("constructed", [False, True])
def test_invalid_owner_values_fail_before_membership(
    model: type[BaseModel], field: str, constructed: bool
) -> None:
    changes: dict[str, tuple[str, object, str]] = {
        "pattern": ("pattern_statement", "a\ud800", "string_unicode"),
        "invariant": ("invariant_statement", "", "string_too_short"),
        "fault_instance": ("reports", (), "too_short"),
        "expected_property": ("expected_property_statement", " padded ", "value_error"),
    }
    child_field, bad, category = changes[field]
    values = _values(model)
    child: BaseModel = values[field]
    if constructed:
        payload = _fields(child)
        payload[child_field] = bad
        child = type(child).model_construct(**payload)
    else:
        # Corrupt only this endpoint, not an aliased member of the supplied case.
        child = type(child)(**_fields(child))
        object.__setattr__(child, child_field, bad)
    values[field] = child
    for candidate in (values, model.model_construct(**values)):
        with pytest.raises(ValidationError) as failure:
            model.model_validate(candidate)
        assert _errors(failure.value) == [((field, child_field), category)]


def test_minimal_links_and_standalone_endpoints_create_no_missing_values(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def denied(*args: object, **kwargs: object) -> Any:
        raise AssertionError("unexpected endpoint or relation construction")

    with monkeypatch.context() as blocked:
        for model in (
            FaultInstance,
            SuppliedFaultExpectedProperty,
            FaultPatternExemplarAssociation,
            FaultInstanceEvidenceLink,
        ):
            blocked.setattr(model, "__init__", denied)
        pair = FaultPatternInvariantAssociation(
            pattern=_pattern(), invariant=_invariant()
        )
    case = _case()
    expected = case.expected_properties[0]
    with monkeypatch.context() as blocked:
        for model in (
            SuppliedFaultPattern,
            FaultPatternExemplarAssociation,
            FaultPatternInvariantAssociation,
            FaultInstanceEvidenceLink,
        ):
            blocked.setattr(model, "__init__", denied)
        qualified = FaultInvariantExpectedPropertyAssociation(
            invariant=_invariant(), fault_instance=case, expected_property=expected
        )
    assert pair.invariant == qualified.invariant
    assert all(getattr(case, field) == () for field in EMPTY_COLLECTIONS)
    assert SuppliedFaultExpectedProperty.model_validate(expected) == expected
    # Neither proposition or standalone expectation needs either new link.
    with monkeypatch.context() as blocked:
        blocked.setattr(FaultPatternInvariantAssociation, "__init__", denied)
        blocked.setattr(FaultInvariantExpectedPropertyAssociation, "__init__", denied)
        assert _pattern().pattern_statement == PATTERN_TEXT
        assert _invariant().invariant_statement == INVARIANT_TEXT
        assert _property().expected_property_statement == PROPERTY_TEXT


def test_full_record_equal_member_qualifies_without_object_identity() -> None:
    case = _case()
    expected = SuppliedFaultExpectedProperty.model_validate_json(
        json.dumps(
            _authored_wire(FaultInvariantExpectedPropertyAssociation)[
                "expected_property"
            ]
        )
    )
    assert (
        expected == case.expected_properties[0]
        and expected is not case.expected_properties[0]
    )
    link = FaultInvariantExpectedPropertyAssociation(
        invariant=_invariant(), fault_instance=case, expected_property=expected
    )
    assert link.expected_property == expected
    assert (
        FaultInvariantExpectedPropertyAssociation.model_validate_json(
            link.model_dump_json()
        )
        == link
    )


@pytest.mark.parametrize(
    "kind",
    [
        "empty",
        "absent_identity",
        "changed_statement",
        "changed_report",
        "changed_context",
        "report_present_only",
    ],
)
def test_full_member_refusal_is_not_identity_text_or_report_membership(
    kind: str,
) -> None:
    case = _case()
    expected = case.expected_properties[0]
    if kind == "empty":
        case = FaultInstance.model_validate(_fields(case) | {"expected_properties": ()})
    elif kind == "absent_identity":
        expected = _property(identifier=99)
    elif kind == "changed_statement":
        expected = _property(text="The opposite supplied expectation.")
    elif kind == "changed_report":
        report = SuppliedFaultReport.model_validate(
            _fields(expected.report)
            | {
                "problem_statement": "Different supplied content under the same report ID."
            }
        )
        expected = _property(report)
    elif kind == "changed_context":
        expected = _property(_report("synthetic-b"))
    else:
        other = _report("synthetic-b", identifier=21)
        expected = _property(other)
        case = FaultInstance.model_validate(
            _fields(case) | {"reports": (case.reports[0], other)}
        )
        assert expected.report in case.reports
    assert FaultInstance.model_validate(case) == case
    assert SuppliedFaultExpectedProperty.model_validate(expected) == expected
    before = case.model_dump_json()
    values = {
        "invariant": _invariant(),
        "fault_instance": case,
        "expected_property": expected,
    }
    for mode in ("python", "json"):
        with pytest.raises(ValidationError) as failure:
            if mode == "python":
                FaultInvariantExpectedPropertyAssociation.model_validate(values)
            else:
                FaultInvariantExpectedPropertyAssociation.model_validate_json(
                    json.dumps(
                        {
                            key: value.model_dump(mode="json")
                            for key, value in values.items()
                        }
                    )
                )
        assert _errors(failure.value) == [((), "value_error")]
        context = failure.value.errors()[0].get("ctx")
        assert context is not None
        assert str(context["error"]) == MEMBERSHIP_ERROR
    assert case.model_dump_json() == before


def _populated() -> FaultInstance:
    first, second = _report(), _report("synthetic-b", identifier=21)
    return FaultInstance(
        fault=first.context.fault,
        reports=(second, first),
        expected_properties=(_property(second, identifier=22), _property(first)),
        hypotheses=tuple(
            SuppliedFaultHypothesis(
                hypothesis=FaultHypothesisIdentity(uuid.UUID(int=i)),
                report=first,
                hypothesis_statement=text,
            )
            for i, text in (
                (32, "A causes the behavior."),
                (31, "A does not cause the behavior."),
            )
        ),
    )


def test_complete_value_equality_many_to_many_and_case_order() -> None:
    pair = FaultPatternInvariantAssociation(pattern=_pattern(), invariant=_invariant())
    same = FaultPatternInvariantAssociation(pattern=_pattern(), invariant=_invariant())
    assert pair == same and hash(pair) == hash(same)
    changed = FaultPatternInvariantAssociation(
        pattern=_pattern("A different proposition under the same ID."),
        invariant=_invariant(),
    )
    assert changed.pattern.pattern == pair.pattern.pattern and changed != pair
    other_i = FaultPatternInvariantAssociation(
        pattern=pair.pattern,
        invariant=_invariant("Every integer equals its successor.", identifier=3),
    )
    other_p = FaultPatternInvariantAssociation(
        pattern=_pattern(identifier=4), invariant=pair.invariant
    )
    assert other_i.pattern == pair.pattern and other_p.invariant == pair.invariant
    case = _populated()
    selected = case.expected_properties[0]
    qualified = FaultInvariantExpectedPropertyAssociation(
        invariant=pair.invariant, fault_instance=case, expected_property=selected
    )
    assert selected.report == case.reports[0]
    assert case.reports[0].context.repository != case.reports[1].context.repository
    altered = FaultInstance.model_validate(_fields(case) | {"hypotheses": ()})
    reordered = FaultInstance.model_validate(
        _fields(case) | {"reports": tuple(reversed(case.reports))}
    )
    for other_case in (altered, reordered):
        other = FaultInvariantExpectedPropertyAssociation(
            invariant=pair.invariant,
            fault_instance=other_case,
            expected_property=selected,
        )
        assert other.fault_instance.fault == qualified.fault_instance.fault
        assert (
            other.expected_property == qualified.expected_property
            and other != qualified
        )
    changed_i = FaultInvariantExpectedPropertyAssociation(
        invariant=_invariant("A competing proposition under the same ID."),
        fault_instance=case,
        expected_property=selected,
    )
    assert (
        changed_i.invariant.invariant == qualified.invariant.invariant
        and changed_i != qualified
    )
    same_i = FaultInvariantExpectedPropertyAssociation(
        invariant=pair.invariant,
        fault_instance=case,
        expected_property=case.expected_properties[1],
    )
    same_e = FaultInvariantExpectedPropertyAssociation(
        invariant=other_i.invariant, fault_instance=case, expected_property=selected
    )
    assert (
        same_i.invariant == qualified.invariant and same_e.expected_property == selected
    )
    elsewhere_report = _report("synthetic-c", identifier=41, fault=40)
    elsewhere_property = _property(elsewhere_report, identifier=42)
    elsewhere = FaultInstance(
        fault=elsewhere_report.context.fault,
        reports=(elsewhere_report,),
        expected_properties=(elsewhere_property,),
    )
    assert (
        FaultInvariantExpectedPropertyAssociation(
            invariant=pair.invariant,
            fault_instance=elsewhere,
            expected_property=elsewhere_property,
        ).invariant
        == pair.invariant
    )
    assert (
        FaultInvariantExpectedPropertyAssociation.model_validate(_fields(qualified))
        == qualified
    )
    assert hash(qualified) == hash(
        FaultInvariantExpectedPropertyAssociation.model_validate(_fields(qualified))
    )


def test_populated_native_json_preserves_every_tuple_and_conflicting_text() -> None:
    case = _populated()
    linked = FaultInvariantExpectedPropertyAssociation(
        invariant=_invariant(),
        fault_instance=case,
        expected_property=case.expected_properties[0],
    )
    restored = FaultInvariantExpectedPropertyAssociation.model_validate_json(
        linked.model_dump_json()
    )
    assert restored == linked
    for field in (*EMPTY_COLLECTIONS, "reports", "expected_properties"):
        assert type(getattr(restored.fault_instance, field)) is tuple
        assert getattr(restored.fault_instance, field) == getattr(case, field)
    assert [x.hypothesis.root.int for x in restored.fault_instance.hypotheses] == [
        32,
        31,
    ]
    assert restored.invariant.invariant_statement == INVARIANT_TEXT


@pytest.mark.parametrize("corruption", ["duplicate", "reference_mismatch", "bound"])
def test_inherited_case_errors_remain_at_the_endpoint(corruption: str) -> None:
    case = _populated()
    payload = case.model_dump(mode="json")
    if corruption == "duplicate":
        payload["expected_properties"].append(payload["expected_properties"][0])
    elif corruption == "reference_mismatch":
        payload["expected_properties"][0]["report"]["problem_statement"] = (
            "A changed report under the same ID."
        )
    else:
        payload["reports"] = [payload["reports"][0]] * 4097
    with pytest.raises(ValidationError) as owner:
        FaultInstance.model_validate_json(json.dumps(payload))
    expected_errors = (
        [(("reports",), "too_long")] if corruption == "bound" else [((), "value_error")]
    )
    assert _errors(owner.value) == expected_errors
    wire = {
        "invariant": {
            "invariant": str(uuid.UUID(int=2)),
            "invariant_statement": INVARIANT_TEXT,
        },
        "fault_instance": payload,
        "expected_property": case.expected_properties[0].model_dump(mode="json"),
    }
    with pytest.raises(ValidationError) as outer:
        FaultInvariantExpectedPropertyAssociation.model_validate_json(json.dumps(wire))
    assert _errors(outer.value) == [
        (("fault_instance", *loc), kind) for loc, kind in expected_errors
    ]
    assert [e["msg"] for e in outer.value.errors()] == [
        e["msg"] for e in owner.value.errors()
    ]


def test_explicit_p_i_f_e_and_evidence_links_do_not_infer_more_links(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pattern, invariant, case = (
        _pattern(),
        _invariant("Duplicated evaluations are permitted."),
        _case(),
    )
    expected = case.expected_properties[0]
    evidence = DurableEvidenceRecordReference(
        format_name=EvidenceRecordFormat("synthetic-case-record"),
        format_version=EvidenceVersion("1"),
        canonicalization=EvidenceCanonicalization("synthetic-v1"),
        sha256=ArtifactSha256Digest("a" * 64),
        byte_length=ArtifactByteLength(1),
    )
    bridge = FaultInstanceEvidenceLink(
        fault_instance=case, subject=expected, evidence_record=evidence
    )
    before = tuple(
        value.model_dump_json()
        for value in (pattern, invariant, case, expected, bridge)
    )

    def denied(*args: object, **kwargs: object) -> Any:
        raise AssertionError("an exemplar was inferred")

    with monkeypatch.context() as blocked:
        blocked.setattr(FaultPatternExemplarAssociation, "__init__", denied)
        pair = FaultPatternInvariantAssociation(pattern=pattern, invariant=invariant)
        qualified = FaultInvariantExpectedPropertyAssociation(
            invariant=invariant, fault_instance=case, expected_property=expected
        )
    explicit_exemplar = FaultPatternExemplarAssociation(
        pattern=pattern, fault_instance=case
    )
    assert explicit_exemplar.pattern == pair.pattern
    assert qualified.expected_property == bridge.subject
    assert set(pair.model_dump()) == {"pattern", "invariant"}
    assert set(qualified.model_dump()) == {
        "invariant",
        "fault_instance",
        "expected_property",
    }
    assert (
        tuple(
            value.model_dump_json()
            for value in (pattern, invariant, case, expected, bridge)
        )
        == before
    )
    for new_relation in (pair, qualified):
        with pytest.raises(ValidationError) as failure:
            FaultInstanceEvidenceLink.model_validate(
                {
                    "fault_instance": case,
                    "subject": new_relation,
                    "evidence_record": evidence,
                }
            )
        assert _errors(failure.value) == [(("subject",), "value_error")]


def test_exact_dependencies_and_preserved_predecessor_bytes() -> None:
    tree = ast.parse((ROOT / MODULE).read_bytes())
    assert {n.name for n in tree.body if isinstance(n, ast.ClassDef)} == set(
        relation_module.__all__
    )
    assert all(
        n.bases
        and len(n.bases) == 1
        and isinstance(n.bases[0], ast.Name)
        and n.bases[0].id == "BaseModel"
        for n in tree.body
        if isinstance(n, ast.ClassDef)
    )
    imports = {
        a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names
    }
    from_imports = {
        n.module: {a.name for a in n.names}
        for n in ast.walk(tree)
        if isinstance(n, ast.ImportFrom)
    }
    assert imports == {"json"}
    assert from_imports == {
        "typing": {"Self"},
        "pydantic": {
            "BaseModel",
            "ConfigDict",
            "ValidationInfo",
            "field_validator",
            "model_validator",
        },
        "faultatlas.domain.pattern": {"SuppliedFaultPattern"},
        "faultatlas.domain.invariant": {"SuppliedFaultInvariant"},
        "faultatlas.domain.fault_instance": {"FaultInstance"},
        "faultatlas.domain.fault_interpretation": {"SuppliedFaultExpectedProperty"},
    }
    assert all(n.level == 0 for n in ast.walk(tree) if isinstance(n, ast.ImportFrom))
    assert not {"__eq__", "__hash__", "__lt__", "__gt__"}.intersection(
        n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)
    )
    for path, digest in BASELINE_PRODUCTION.items():
        data = (ROOT / path).read_bytes()
        assert hashlib.sha256(data).hexdigest() == digest, path
        assert b"invariant_relationship" not in data, path


def test_value_entry_points_perform_no_io(monkeypatch: pytest.MonkeyPatch) -> None:
    import builtins
    import socket
    import time

    values = [(model, _values(model)) for model, _ in MODELS]

    def denied(*args: object, **kwargs: object) -> Any:
        raise AssertionError("value validation attempted an external operation")

    with monkeypatch.context() as blocked:
        for owner, name in (
            (builtins, "open"),
            (Path, "open"),
            (socket, "socket"),
            (subprocess, "Popen"),
            (os, "getenv"),
            (os, "stat"),
            (time, "time"),
            (uuid, "uuid4"),
        ):
            blocked.setattr(owner, name, denied)
        for model, endpoints in values:
            linked = model.model_validate(endpoints)
            assert model.model_validate_json(linked.model_dump_json()) == linked


def test_bounded_s04_roadmap_and_current_gate() -> None:
    text = (ROOT / "docs/roadmap.md").read_text()
    section = " ".join(
        text.split("### S1.P07.S04 — Explicit invariant associations\n", 1)[1]
        .split("### S1.P07.S05", 1)[0]
        .split("The `S1.P07` route", 1)[0]
        .split()
    )
    for phrase in (
        "FaultPatternInvariantAssociation",
        "FaultInvariantExpectedPropertyAssociation",
        "full-record-equal member",
        "expected_properties",
        "not semantic truth",
        "no inferred exemplar",
        "four named modules and seven exports",
    ):
        assert phrase in section, phrase


def test_uv_installed_wheel_both_records_outside_checkout(
    offline_distributions: tuple[Path, Path], tmp_path: Path
) -> None:
    installed = tmp_path / "installed"
    env = os.environ | {
        "UV_OFFLINE": "1",
        "UV_CACHE_DIR": str(tmp_path / "cache"),
        "PYTHONDONTWRITEBYTECODE": "1",
    }
    result = subprocess.run(
        [
            "uv",
            "pip",
            "install",
            "--offline",
            "--no-deps",
            "--target",
            str(installed),
            str(offline_distributions[0]),
        ],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    script = """
import json, sys
from pathlib import Path
installed = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(installed))
import faultatlas.domain.invariant_relationship as module
assert Path(module.__file__).resolve().is_relative_to(installed)
payloads = json.loads(sys.argv[2])
observed = []
for name, payload in payloads:
    model = getattr(module, name)
    value = model.model_validate_json(json.dumps(payload))
    assert model.model_validate_json(value.model_dump_json()) == value
    observed.append(value.model_dump(mode="json"))
print(json.dumps({"module": module.__file__, "values": observed}))
"""
    payloads = [(model.__name__, _authored_wire(model)) for model, _ in MODELS]
    result = subprocess.run(
        [sys.executable, "-I", "-c", script, str(installed), json.dumps(payloads)],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    receipt = json.loads(result.stdout)
    assert Path(receipt["module"]).is_relative_to(installed)
    assert not Path(receipt["module"]).is_relative_to(ROOT)
    assert receipt["values"] == [payload for _, payload in payloads]


# Immutable production bytes at the accepted S03 squash ce598cfc.
BASELINE_PRODUCTION = {
    "src/faultatlas/__init__.py": "7f88816f33b0efc700b25bfb7ad171ef00a3e5875d358e258d8e3d755e4d8489",
    "src/faultatlas/__main__.py": "97a5e95d8d541e00eb0ceb84e73a28f28c3007643d80d3814945e04bedc41800",
    "src/faultatlas/cli.py": "31e7edfea6a699fd75a4503a91beaf564b7257a4b69422acd6d81bfad59fd824",
    "src/faultatlas/domain/__init__.py": "5cae5f36fe402a284ee13c9757b8b8415d2951711107890ce8c6c038fa8b05b5",
    "src/faultatlas/domain/compatibility.py": "f4ef93d432da4fd0ebf05237c164e10d8f18eceaf538ff4ddc3372565b5c46db",
    "src/faultatlas/domain/evidence.py": "824ed6ad86d243ccf920f07fe66af5d6bf060d6d80fafb7d60588dec8244e7ba",
    "src/faultatlas/domain/fault.py": "f8b8bed37aff51b8848c303f2fbffde4e5e365216b5f46755b043fad2d254e26",
    "src/faultatlas/domain/fault_evidence_link.py": "d8b0b0c59f48d0eb45285cde96f27d1640953b310c94b6e2a8ef20b5f142c1c1",
    "src/faultatlas/domain/fault_instance.py": "4d505c837ab261e65886464e950ae6417bf4bf09702ec0c45fac9f6924bc9b1d",
    "src/faultatlas/domain/fault_interpretation.py": "02ae3034a6ebfef54e1785b48a619dcdb56bd03354a01d1cde79d9f8e3e4ee54",
    "src/faultatlas/domain/fault_repair.py": "3256c64c2defc2635604fd5628cc9efbd94bb0c1b222a4994d29dd35ad6d0648",
    "src/faultatlas/domain/fault_source_relationship.py": "470bd4438e0b740e9955cd828f67a1d8ec5749a36be92301673375cae4285d31",
    "src/faultatlas/domain/fault_test.py": "9487cf11ecf7f11922f9ecd6a10945e7f929009e048131ec0609e3ee70aab3d0",
    "src/faultatlas/domain/history.py": "e72454294c448e4edeec0d7cc044c205d6e3852df9c2c244b5e21cb579e22990",
    "src/faultatlas/domain/history_evidence_link.py": "8b69bc47dc53ae754359877f3e50289530b745c69508b4144e8bcf39a6696c86",
    "src/faultatlas/domain/identity.py": "e2d604f4e86a3b94c2b1b1875fa6e8f408778cbadd829b3fe9e934dd53f2d169",
    "src/faultatlas/domain/invariant.py": "58c9839419122c06d1e44aad7c1129fa05342d3d6ec2c388a830d2c62e6d1873",
    "src/faultatlas/domain/pattern.py": "590a4f2dcc2473415cc6c77dc4ce714b2995e1e3db35ea1fbe16ef5fcdfda4e3",
    "src/faultatlas/domain/pattern_exemplar.py": "b330f1187667843e7392e71d5efa8a6bd18fa0df43d7c5849266ca96b68fb770",
    "src/faultatlas/domain/revision.py": "7bea28086b345f6c1b4eeebe9c483924e60521e2f3e78954b272ab3c42acacaa",
    "src/faultatlas/domain/snapshot.py": "3807eb6e1552bfd97c3bedd7ca6fe8bfe7351f0ff3bc8205afdbad69c7f3e5fd",
    "src/faultatlas/domain/snapshot_evidence_link.py": "a87b7ed338a74127bd490803a958316bbc2598989cbbf3b0534174bc2b9cd59d",
    "src/faultatlas/domain/source.py": "034e53fd58212f0e34376bbc790fc3e74057031aaed4d7d89fb67904bdd380bf",
}
