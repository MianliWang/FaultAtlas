"""Synthetic cross-instance examples, not observed recurrence or transfer proof.

All identifiers, repository contexts, prose and evidence references are invented.
Canonical means representative base-class values, not a durable byte format.
Detailed input limits and inventories remain with the existing focused owners.
"""

from __future__ import annotations

import json
import uuid
from typing import Any

import pytest
from pydantic import BaseModel, ValidationError

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
    SuppliedFaultExpectedProperty,
)
from faultatlas.domain.fault_test import (
    FaultTestMaterialIdentity,
    FaultTestRunIdentity,
    ReportedFaultTestOutcome,
    ReportedFaultTestOutcomeKind,
    ReportedFaultTestRun,
    SuppliedFaultTestMaterial,
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
from faultatlas.domain.pattern_composition import FaultPatternComposition
from faultatlas.domain.pattern_exemplar import FaultPatternExemplarAssociation

PATTERN = "Synthetic pattern: retry repeats a callback.\n保留  supplied spacing."
INVARIANT = "Synthetic invariant: each request invokes its callback once."
CASE_ROWS = (
    (
        "synthetic-a",
        "A retry repeats a debit.",
        "The debit callback runs twice.",
        "Synthetic A expects exactly one debit callback.",
    ),
    (
        "synthetic-b",
        "A retry repeats a notification.",
        "Two notifications arrive.",
        "Synthetic B permits two notification callbacks.",
    ),
    (
        "synthetic-c",
        "A retry repeats a write.",
        "The write callback runs twice.",
        "Synthetic C expects one write callback.",
    ),
)


def _case(index: int) -> FaultInstance:
    repository, problem, deviation, expectation = CASE_ROWS[index - 1]
    report = SuppliedFaultReport(
        report=FaultReportIdentity(uuid.UUID(int=index * 10 + 1)),
        context=FaultRepositoryContext(
            fault=FaultInstanceIdentity(uuid.UUID(int=index * 10)),
            repository=RepositoryIdentity(
                provider=ProviderKey("github"),
                provider_repository_id=ProviderRepositoryId(repository),
            ),
        ),
        problem_statement=problem,
        behavioral_deviation=deviation,
    )
    expected = SuppliedFaultExpectedProperty(
        expected_property=FaultExpectedPropertyIdentity(uuid.UUID(int=index * 10 + 2)),
        report=report,
        expected_property_statement=expectation,
    )
    return FaultInstance(
        fault=report.context.fault, reports=(report,), expected_properties=(expected,)
    )


def _values() -> dict[str, Any]:
    pattern = SuppliedFaultPattern(
        pattern=FaultPatternIdentity(uuid.UUID(int=100)), pattern_statement=PATTERN
    )
    invariant = SuppliedFaultInvariant(
        invariant=FaultInvariantIdentity(uuid.UUID(int=200)),
        invariant_statement=INVARIANT,
    )
    cases = (_case(1), _case(2))
    return {
        "pattern": pattern,
        "exemplar_associations": tuple(
            FaultPatternExemplarAssociation(pattern=pattern, fault_instance=case)
            for case in cases
        ),
        "invariants": (invariant,),
        "pattern_invariant_associations": (
            FaultPatternInvariantAssociation(pattern=pattern, invariant=invariant),
        ),
        "invariant_expected_property_associations": tuple(
            FaultInvariantExpectedPropertyAssociation(
                invariant=invariant,
                fault_instance=case,
                expected_property=case.expected_properties[0],
            )
            for case in cases
        ),
    }


def _fields(value: BaseModel) -> dict[str, Any]:
    # Typed Python inputs only; never used to author expected primitive payloads.
    return {name: getattr(value, name) for name in type(value).model_fields}


def _case_wire(index: int) -> dict[str, Any]:
    repository, problem, deviation, expectation = CASE_ROWS[index - 1]
    report = {
        "report": str(uuid.UUID(int=index * 10 + 1)),
        "context": {
            "fault": str(uuid.UUID(int=index * 10)),
            "repository": {
                "schema_version": 1,
                "provider": "github",
                "provider_repository_id": repository,
            },
        },
        "problem_statement": problem,
        "behavioral_deviation": deviation,
    }
    return {
        "fault": str(uuid.UUID(int=index * 10)),
        "reports": [report],
        "scenarios": [],
        "occurrences": [],
        "source_object_associations": [],
        "history_fact_associations": [],
        "repair_candidates": [],
        "repair_revision_associations": [],
        "repair_change_set_associations": [],
        "test_materials": [],
        "test_runs": [],
        "test_outcomes": [],
        "test_run_revision_associations": [],
        "test_comparisons": [],
        "explanations": [],
        "hypotheses": [],
        "expected_properties": [
            {
                "expected_property": str(uuid.UUID(int=index * 10 + 2)),
                "report": report,
                "expected_property_statement": expectation,
            }
        ],
    }


def _wire() -> dict[str, Any]:
    # Explicit primitive oracle, independent of production dumps and field discovery.
    pattern = {"pattern": str(uuid.UUID(int=100)), "pattern_statement": PATTERN}
    invariant = {"invariant": str(uuid.UUID(int=200)), "invariant_statement": INVARIANT}
    cases = (_case_wire(1), _case_wire(2))
    return {
        "pattern": pattern,
        "exemplar_associations": [
            {"pattern": pattern, "fault_instance": case} for case in cases
        ],
        "invariants": [invariant],
        "pattern_invariant_associations": [
            {"pattern": pattern, "invariant": invariant}
        ],
        "invariant_expected_property_associations": [
            {
                "invariant": invariant,
                "fault_instance": case,
                "expected_property": case["expected_properties"][0],
            }
            for case in cases
        ],
    }


def test_two_repository_composition_matches_authored_payload() -> None:
    values = _values()
    value = FaultPatternComposition(**values)
    restored = FaultPatternComposition.model_validate_json(json.dumps(_wire()))
    assert value.model_dump(mode="json") == _wire()
    assert restored == value
    assert FaultPatternComposition.model_validate_json(value.model_dump_json()) == value
    for name, expected in values.items():
        assert getattr(restored, name) == expected
    assert tuple(link.fault_instance for link in restored.exemplar_associations) == (
        _case(1),
        _case(2),
    )
    assert _case(1).fault != _case(2).fault
    assert (
        _case(1).reports[0].context.repository != _case(2).reports[0].context.repository
    )
    for link in restored.invariant_expected_property_associations:
        assert type(link.fault_instance.reports) is tuple
        assert link.fault_instance.expected_properties == (link.expected_property,)


def test_exemplars_and_expectation_chains_are_explicit() -> None:
    values = _values()
    third = _case(3)
    third_link = FaultInvariantExpectedPropertyAssociation(
        invariant=values["invariants"][0],
        fault_instance=third,
        expected_property=third.expected_properties[0],
    )
    values["invariant_expected_property_associations"] += (third_link,)
    value = FaultPatternComposition(**values)
    assert tuple(x.fault_instance for x in value.exemplar_associations) == (
        _case(1),
        _case(2),
    )
    assert value.invariant_expected_property_associations == (
        *_values()["invariant_expected_property_associations"],
        third_link,
    )
    # B remains a valid exemplar when its expectation chain is not supplied.
    values["invariant_expected_property_associations"] = (
        values["invariant_expected_property_associations"][0],
        third_link,
    )
    independent = FaultPatternComposition(**values)
    assert independent.exemplar_associations == value.exemplar_associations
    assert tuple(
        x.fault_instance for x in independent.invariant_expected_property_associations
    ) == (_case(1), third)


def test_equal_reconstructed_endpoints_qualify() -> None:
    original = _values()
    reconstructed = FaultPatternComposition.model_validate_json(json.dumps(_wire()))
    values = _fields(reconstructed) | {
        "pattern": original["pattern"],
        "invariants": original["invariants"],
    }
    assert reconstructed.pattern is not original["pattern"]
    assert reconstructed.invariants[0] is not original["invariants"][0]
    expected = SuppliedFaultExpectedProperty.model_validate_json(
        json.dumps(_case_wire(1)["expected_properties"][0])
    )
    case = _case(1)
    assert (
        expected == case.expected_properties[0]
        and expected is not case.expected_properties[0]
    )
    values["invariant_expected_property_associations"] = (
        FaultInvariantExpectedPropertyAssociation(
            invariant=reconstructed.invariants[0],
            fault_instance=case,
            expected_property=expected,
        ),
        reconstructed.invariant_expected_property_associations[1],
    )
    assert FaultPatternComposition(**values) == reconstructed


@pytest.mark.parametrize(
    ("collection", "endpoint", "message"),
    (
        ("exemplar_associations", "pattern", "has a different pattern"),
        ("pattern_invariant_associations", "pattern", "has a different pattern"),
        (
            "pattern_invariant_associations",
            "invariant",
            "references a nonmember invariant",
        ),
        (
            "invariant_expected_property_associations",
            "invariant",
            "references a nonmember invariant",
        ),
    ),
)
def test_same_identity_changed_proposition_is_rejected(
    collection: str,
    endpoint: str,
    message: str,
) -> None:
    values = _values()
    FaultPatternComposition(**values)  # The complete setup is valid first.
    link: BaseModel = values[collection][0]
    old: BaseModel = getattr(link, endpoint)
    changed = type(old).model_validate(
        _fields(old) | {f"{endpoint}_statement": "Synthetic competing proposition."}
    )
    assert getattr(changed, endpoint) == getattr(old, endpoint) and changed != old
    replacement = type(link).model_validate(_fields(link) | {endpoint: changed})
    values[collection] = (replacement, *values[collection][1:])
    with pytest.raises(ValidationError) as failure:
        FaultPatternComposition(**values)
    assert [(e["loc"], e["type"], e["msg"]) for e in failure.value.errors()] == [
        ((), "value_error", f"Value error, {collection}[0] {message}"),
    ]


@pytest.mark.parametrize("kind", ("same_identity_changed_text", "case_b_property"))
def test_wrong_case_property_fails_at_membership_owner(kind: str) -> None:
    values = _values()
    FaultPatternComposition(**values)
    link = values["invariant_expected_property_associations"][0]
    expected = (
        SuppliedFaultExpectedProperty.model_validate(
            _fields(link.expected_property)
            | {"expected_property_statement": "Synthetic A permits repeated debits."}
        )
        if kind == "same_identity_changed_text"
        else _case(2).expected_properties[0]
    )
    assert SuppliedFaultExpectedProperty.model_validate(expected) == expected
    assert FaultInstance.model_validate(link.fault_instance) == _case(1)
    if kind == "same_identity_changed_text":
        assert expected.expected_property == link.expected_property.expected_property
    else:
        assert expected in _case(2).expected_properties
    inputs: dict[str, Any] = _fields(link) | {"expected_property": expected}
    with pytest.raises(ValidationError) as owner:
        FaultInvariantExpectedPropertyAssociation(**inputs)
    assert [(e["loc"], e["type"], e["msg"]) for e in owner.value.errors()] == [
        (
            (),
            "value_error",
            "Value error, expected_property is not a full-record member of fault_instance.expected_properties",
        ),
    ]
    # Only this deliberately invalid association bypasses its constructor, to
    # prove that the enclosing composition re-enters the same membership owner.
    values["invariant_expected_property_associations"] = (
        FaultInvariantExpectedPropertyAssociation.model_construct(**inputs),
        values["invariant_expected_property_associations"][1],
    )
    with pytest.raises(ValidationError) as outer:
        FaultPatternComposition(**values)
    assert [(e["loc"], e["msg"]) for e in outer.value.errors()] == [
        (
            ("invariant_expected_property_associations", 0),
            owner.value.errors()[0]["msg"],
        ),
    ]


@pytest.mark.parametrize("kind", ("missing_attachment", "orphan"))
def test_missing_invariant_attachment_is_rejected(kind: str) -> None:
    values = _values()
    FaultPatternComposition(**values)
    if kind == "missing_attachment":
        values["pattern_invariant_associations"] = ()
    else:
        values["invariants"] += (
            SuppliedFaultInvariant(
                invariant=FaultInvariantIdentity(uuid.UUID(int=201)),
                invariant_statement="Synthetic unattached invariant.",
            ),
        )
    with pytest.raises(ValidationError) as failure:
        FaultPatternComposition(**values)
    assert [(e["loc"], e["msg"]) for e in failure.value.errors()] == [
        (
            (),
            "Value error, invariants contains a value not attached to the root pattern",
        ),
    ]


def test_repetition_order_and_separate_roots_remain_local() -> None:
    values, wire = _values(), _wire()
    for name in (
        "exemplar_associations",
        "pattern_invariant_associations",
        "invariant_expected_property_associations",
    ):
        values[name] += (values[name][0],)
        wire[name].append(wire[name][0])
    value = FaultPatternComposition(**values)
    assert value.model_dump(mode="json") == wire
    assert FaultPatternComposition.model_validate_json(json.dumps(wire)) == value
    for name in ("exemplar_associations", "invariant_expected_property_associations"):
        a, b, repeated = values[name]
        reordered = FaultPatternComposition.model_validate(
            values | {name: (b, a, repeated)}
        )
        assert getattr(reordered, name) == (b, a, repeated)
        assert reordered != value  # Supplied order, not priority or support.
    other_pattern = SuppliedFaultPattern(
        pattern=FaultPatternIdentity(uuid.UUID(int=101)),
        pattern_statement="Synthetic second pattern sharing an invariant and a case.",
    )
    other = FaultPatternComposition(
        pattern=other_pattern,
        invariants=value.invariants,
        pattern_invariant_associations=(
            FaultPatternInvariantAssociation(
                pattern=other_pattern,
                invariant=value.invariants[0],
            ),
        ),
        exemplar_associations=(
            FaultPatternExemplarAssociation(
                pattern=other_pattern,
                fault_instance=_case(1),
            ),
        ),
        invariant_expected_property_associations=(
            value.invariant_expected_property_associations[0],
        ),
    )
    assert other.pattern == other_pattern and other.pattern != value.pattern
    assert other.invariants == value.invariants
    assert other.exemplar_associations[0].fault_instance == _case(1)
    assert value.model_dump(mode="json") == wire


def test_association_cases_are_not_a_global_registry() -> None:
    values = _values()
    original = _case(1)
    changed = SuppliedFaultExpectedProperty.model_validate(
        _fields(original.expected_properties[0])
        | {"expected_property_statement": "Synthetic alternate case A permits retries."}
    )
    alternate = FaultInstance.model_validate(
        _fields(original) | {"expected_properties": (changed,)}
    )
    link = FaultInvariantExpectedPropertyAssociation(
        invariant=values["invariants"][0],
        fault_instance=alternate,
        expected_property=changed,
    )
    values["invariant_expected_property_associations"] += (link,)
    value = FaultPatternComposition(**values)
    assert original.fault == alternate.fault and original != alternate
    assert value.exemplar_associations[0].fault_instance == original
    assert value.invariant_expected_property_associations[-1] == link
    assert value.invariant_expected_property_associations[0].fault_instance == original
    assert FaultPatternComposition.model_validate_json(value.model_dump_json()) == value


def test_competing_claims_survive_composition() -> None:
    values, wire = _values(), _wire()
    case = _case(1)
    material = SuppliedFaultTestMaterial(
        material=FaultTestMaterialIdentity(uuid.UUID(int=300)),
        report=case.reports[0],
        test_statement="Synthetic procedure: retry one debit and count callbacks.",
    )
    run = ReportedFaultTestRun(
        run=FaultTestRunIdentity(uuid.UUID(int=301)),
        test_material=material,
        run_statement="Synthetic reported attempt; no execution occurred here.",
    )
    outcomes = tuple(
        ReportedFaultTestOutcome(
            run=run,
            outcome=kind,
            outcome_statement=text,
        )
        for kind, text in (
            (
                ReportedFaultTestOutcomeKind.FAILED,
                "Synthetic reporter X says two callbacks.",
            ),
            (
                ReportedFaultTestOutcomeKind.PASSED,
                "Synthetic reporter Y says one callback.",
            ),
        )
    )
    populated = FaultInstance.model_validate(
        _fields(case)
        | {
            "test_materials": (material,),
            "test_runs": (run,),
            "test_outcomes": outcomes,
        }
    )
    populated_wire = _case_wire(1)
    material_wire = {
        "material": str(uuid.UUID(int=300)),
        "report": populated_wire["reports"][0],
        "test_statement": "Synthetic procedure: retry one debit and count callbacks.",
    }
    run_wire = {
        "run": str(uuid.UUID(int=301)),
        "test_material": material_wire,
        "run_statement": "Synthetic reported attempt; no execution occurred here.",
    }
    populated_wire.update(
        test_materials=[material_wire],
        test_runs=[run_wire],
        test_outcomes=[
            {
                "run": run_wire,
                "outcome": "failed",
                "outcome_statement": "Synthetic reporter X says two callbacks.",
            },
            {
                "run": run_wire,
                "outcome": "passed",
                "outcome_statement": "Synthetic reporter Y says one callback.",
            },
        ],
    )
    for name in ("exemplar_associations", "invariant_expected_property_associations"):
        first: BaseModel = values[name][0]
        values[name] = (
            type(first).model_validate(_fields(first) | {"fault_instance": populated}),
            values[name][1],
        )
        wire[name][0]["fault_instance"] = populated_wire
    value = FaultPatternComposition(**values)
    restored = FaultPatternComposition.model_validate_json(json.dumps(wire))
    assert value.model_dump(mode="json") == wire and restored == value
    assert restored.exemplar_associations[0].fault_instance.test_outcomes == outcomes
    assert (
        restored.invariant_expected_property_associations[0].fault_instance == populated
    )
    assert restored.invariants[0].invariant_statement == INVARIANT
    assert tuple(
        x.expected_property.expected_property_statement
        for x in restored.invariant_expected_property_associations
    ) == (CASE_ROWS[0][3], CASE_ROWS[1][3])
    # Exact primitive equality above leaves no winner, verified invariant or
    # repair-correctness result; the competing prose is never evaluated.


def test_case_evidence_link_does_not_propagate() -> None:
    case = _case(1)
    evidence = DurableEvidenceRecordReference(
        format_name=EvidenceRecordFormat("synthetic-s06-record"),
        format_version=EvidenceVersion("1"),
        canonicalization=EvidenceCanonicalization("synthetic-v1"),
        sha256=ArtifactSha256Digest("a" * 64),
        byte_length=ArtifactByteLength(1),
    )
    bridge = FaultInstanceEvidenceLink(
        fault_instance=case,
        subject=case.expected_properties[0],
        evidence_record=evidence,
    )
    expected_bridge = {
        "fault_instance": _case_wire(1),
        "subject": _case_wire(1)["expected_properties"][0],
        "evidence_record": {
            "schema_version": 1,
            "format_name": "synthetic-s06-record",
            "format_version": "1",
            "canonicalization": "synthetic-v1",
            "sha256": "a" * 64,
            "byte_length": 1,
        },
    }
    assert bridge.model_dump(mode="json") == expected_bridge
    value = FaultPatternComposition(**_values())
    assert value.model_dump(mode="json") == _wire()
    assert bridge.model_dump(mode="json") == expected_bridge
    assert value.exemplar_associations[0].fault_instance == bridge.fault_instance
    assert (
        value.invariant_expected_property_associations[0].expected_property
        == bridge.subject
    )
    assert (
        FaultInstanceEvidenceLink.model_validate_json(json.dumps(expected_bridge))
        == bridge
    )
    # This supplied reference attests to no retained bytes, retrieval or support.


@pytest.mark.parametrize(
    ("kind", "location", "error_type"),
    (
        ("untyped_member", ("exemplar_associations", 0), "value_error"),
        (
            "list_collection",
            ("invariant_expected_property_associations",),
            "tuple_type",
        ),
    ),
)
def test_integrated_python_boundary(
    kind: str, location: tuple[str | int, ...], error_type: str
) -> None:
    values = _values()
    FaultPatternComposition(**values)
    if kind == "untyped_member":
        values["exemplar_associations"] = (
            _fields(values["exemplar_associations"][0]),
            values["exemplar_associations"][1],
        )
    else:
        values["invariant_expected_property_associations"] = list(
            values["invariant_expected_property_associations"]
        )
    with pytest.raises(ValidationError) as failure:
        FaultPatternComposition(**values)
    assert [(e["loc"], e["type"]) for e in failure.value.errors()] == [
        (location, error_type)
    ]


def test_invalid_nested_child_revalidates_at_its_owner() -> None:
    values = _values()
    FaultPatternComposition(**values)
    link = values["invariant_expected_property_associations"][1]
    invalid = link.expected_property.model_copy(
        update={"expected_property_statement": " padded synthetic text"}
    )
    with pytest.raises(ValidationError) as owner:
        SuppliedFaultExpectedProperty.model_validate(invalid)
    assert [(e["loc"], e["type"], e["msg"]) for e in owner.value.errors()] == [
        (
            ("expected_property_statement",),
            "value_error",
            "Value error, expected_property_statement must not have leading or trailing whitespace",
        ),
    ]
    values["invariant_expected_property_associations"] = (
        values["invariant_expected_property_associations"][0],
        link.model_copy(update={"expected_property": invalid}),
    )
    with pytest.raises(ValidationError) as outer:
        FaultPatternComposition(**values)
    assert [(e["loc"], e["msg"]) for e in outer.value.errors()] == [
        (
            (
                "invariant_expected_property_associations",
                1,
                "expected_property",
                "expected_property_statement",
            ),
            owner.value.errors()[0]["msg"],
        ),
    ]
