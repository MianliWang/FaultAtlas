from __future__ import annotations

import ast
import json
import os
import shutil
import subprocess
import sys
import tarfile
import uuid
import zipfile
from pathlib import Path
from typing import Any, cast

import pytest
from pydantic import BaseModel, ValidationError

import faultatlas
import faultatlas.domain
import faultatlas.domain.fault_instance as instance_module
from faultatlas.domain.fault import (
    FaultInstanceIdentity,
    FaultOccurrenceIdentity,
    FaultReportIdentity,
    FaultRepositoryContext,
    FaultScenarioIdentity,
    SuppliedFaultOccurrenceContext,
    SuppliedFaultReport,
    SuppliedFaultScenario,
)
from faultatlas.domain.fault_instance import FaultInstance
from faultatlas.domain.fault_interpretation import (
    FaultExpectedPropertyIdentity,
    FaultExplanationIdentity,
    FaultHypothesisIdentity,
    SuppliedFaultExpectedProperty,
    SuppliedFaultExplanation,
    SuppliedFaultHypothesis,
)
from faultatlas.domain.fault_repair import (
    FaultRepairCandidateChangeSetAssociation,
    FaultRepairCandidateIdentity,
    FaultRepairCandidateRevisionAssociation,
    SuppliedFaultRepairCandidate,
)
from faultatlas.domain.fault_source_relationship import (
    FaultReportHistoryFactAssociation,
    FaultReportSourceObjectAssociation,
)
from faultatlas.domain.fault_test import (
    FaultTestMaterialIdentity,
    FaultTestRunIdentity,
    FaultTestRunRevisionAssociation,
    ReportedFaultTestComparison,
    ReportedFaultTestOutcome,
    ReportedFaultTestOutcomeKind,
    ReportedFaultTestRun,
    SuppliedFaultTestMaterial,
)
from faultatlas.domain.history import (
    ChangedPathStatus,
    PullRequestChangedPath,
    PullRequestChangeSet,
    PullRequestRevisionRoleBinding,
)
from faultatlas.domain.identity import (
    NumberedSourceObjectIdentity,
    ProviderKey,
    ProviderRepositoryId,
    RepositoryIdentity,
    RepositoryScopedNumber,
    SourceObjectKind,
)
from faultatlas.domain.revision import (
    GitBlobIdentity,
    GitCommitIdentity,
    GitHashAlgorithm,
    GitObjectKind,
    GitRepositoryPath,
    RevisionRole,
    RevisionRoleAssignment,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
INSTANCE_SOURCE = REPOSITORY_ROOT / "src/faultatlas/domain/fault_instance.py"
CHECKOUT_SOURCE_ROOT = REPOSITORY_ROOT / "src"
ROADMAP = REPOSITORY_ROOT / "docs/roadmap.md"

# Fixed synthetic supplied data. The retained pytest #4412 case supplies no
# aggregate, so every identifier below is invented for this file and no
# statement is a historical quotation.
FAULT_TEXT = "12345678-1234-4234-8234-123456789abc"
FAULT = uuid.UUID(FAULT_TEXT)
OTHER_FAULT = uuid.UUID("aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee")
REPORT_TEXT = "87654321-4321-4abc-8def-0123456789ab"
REPORT = uuid.UUID(REPORT_TEXT)
SECOND_REPORT = uuid.UUID("11111111-2222-4333-8444-555555555555")
SCENARIO = uuid.UUID("2b2b2b2b-3c3c-4d4d-8e8e-9f9f9f9f9f9f")
OCCURRENCE = uuid.UUID("74747474-8585-4696-8a7a-b8b8b8b8b8b8")
CANDIDATE = uuid.UUID("5c5c5c5c-6d6d-4e7e-8f8f-909090909090")
SECOND_CANDIDATE = uuid.UUID("13131313-2424-4535-8646-757575757575")
MATERIAL = uuid.UUID("3e3e3e3e-4f4f-4a5a-8b6b-7c7c7c7c7c7c")
RUN = uuid.UUID("0a0a0a0a-1b1b-4c2c-8d3d-4e4e4e4e4e4e")
SECOND_RUN = uuid.UUID("5f5f5f5f-6060-4171-8282-939393939393")
EXPLANATION = uuid.UUID("6a6a6a6a-7b7b-4c8c-89d9-0e0e0e0e0e0e")
SECOND_EXPLANATION = uuid.UUID("9d9d9d9d-8e8e-4f7f-8060-515151515151")
HYPOTHESIS = uuid.UUID("42424242-5353-4646-8757-686868686868")
SECOND_HYPOTHESIS = uuid.UUID("1f1f1f1f-2020-4313-8424-535353535353")
PROPERTY = uuid.UUID("cdcdcdcd-bebe-4faf-80b0-c1c1c1c1c1c1")

PROVIDER = "github"
REPOSITORY_ID = "37489525"
OTHER_REPOSITORY_ID = "37489526"
PULL_REQUEST_NUMBER = "4414"
BASE_REVISION = "4c9cde74ab40027b5761ab9e002af116a4a20df3"
HEAD_REVISION = "690a63b9218f72662cd3a67c6c200b758c88ce12"
OTHER_REVISION = "1111111111111111111111111111111111111111"
CHANGED_PATH = "src/_pytest/assertion/rewrite.py"
CHANGED_BLOB = "7b9aa5006544c160f584f1e8fc3f7771ef6e5e99"

PROBLEM = "Instrumentation can change callback behavior."
DEVIATION = "The supplied transformed path invokes one callback twice."
OTHER_PROBLEM = "A cached rewrite may be reused after the source changes."
OTHER_DEVIATION = "The supplied stale rewrite reports the wrong line."

EXPECTED_FIELDS = (
    "fault",
    "reports",
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
    "expected_properties",
)
OPTIONAL_FIELDS = EXPECTED_FIELDS[2:]
DECLARED_BOUND = 4096

# Each names an authority this aggregate does not have, a resolution it may not
# perform, or a completeness claim it must not make.
FORBIDDEN_IDENTIFIERS = (
    "canonical",
    "causation",
    "complete",
    "completeness",
    "confidence",
    "conflict",
    "correct",
    "correctness",
    "dedupe",
    "duplicate",
    "evidence",
    "evidence_record",
    "exhaustive",
    "fully_observed",
    "fully_reproduced",
    "graph",
    "index",
    "inferred",
    "known_empty",
    "merged",
    "ordering",
    "primary",
    "priority",
    "registry",
    "resolved",
    "review",
    "root_cause",
    "sorted",
    "supported",
    "unavailable",
    "verified",
    "winner",
)


def _repository(identifier: str = REPOSITORY_ID) -> RepositoryIdentity:
    return RepositoryIdentity(
        provider=ProviderKey(PROVIDER),
        provider_repository_id=ProviderRepositoryId(identifier),
    )


def _report(
    report: uuid.UUID = REPORT,
    fault: uuid.UUID = FAULT,
    repository: str = REPOSITORY_ID,
    problem: str = PROBLEM,
    deviation: str = DEVIATION,
) -> SuppliedFaultReport:
    return SuppliedFaultReport(
        report=FaultReportIdentity(report),
        context=FaultRepositoryContext(
            fault=FaultInstanceIdentity(fault),
            repository=_repository(repository),
        ),
        problem_statement=problem,
        behavioral_deviation=deviation,
    )


def _scenario(
    scenario: uuid.UUID = SCENARIO,
    report: SuppliedFaultReport | None = None,
    statement: str = "Only when the rewritten assertion is instrumented.",
) -> SuppliedFaultScenario:
    return SuppliedFaultScenario(
        scenario=FaultScenarioIdentity(scenario),
        report=_report() if report is None else report,
        scenario_statement=statement,
    )


def _occurrence(
    occurrence: uuid.UUID = OCCURRENCE,
    scenario: SuppliedFaultScenario | None = None,
) -> SuppliedFaultOccurrenceContext:
    return SuppliedFaultOccurrenceContext(
        occurrence=FaultOccurrenceIdentity(occurrence),
        scenario=_scenario() if scenario is None else scenario,
        occurrence_context="Reported once by the caller on their own checkout.",
    )


def _commit(digest: str = HEAD_REVISION) -> GitCommitIdentity:
    return GitCommitIdentity(
        kind=GitObjectKind.COMMIT,
        algorithm=GitHashAlgorithm.SHA1,
        full_digest=digest,
    )


def _pull_request(repository: str = REPOSITORY_ID) -> NumberedSourceObjectIdentity:
    return NumberedSourceObjectIdentity(
        repository_identity=_repository(repository),
        kind=SourceObjectKind.PULL_REQUEST,
        repository_scoped_number=RepositoryScopedNumber(PULL_REQUEST_NUMBER),
    )


def _binding(
    role: RevisionRole, digest: str, repository: str = REPOSITORY_ID
) -> PullRequestRevisionRoleBinding:
    return PullRequestRevisionRoleBinding(
        pull_request=_pull_request(repository),
        role_assignment=RevisionRoleAssignment(role=role, revision=_commit(digest)),
    )


def _change_set(head: str = HEAD_REVISION) -> PullRequestChangeSet:
    return PullRequestChangeSet(
        base=_binding(RevisionRole.BASE, BASE_REVISION),
        head=_binding(RevisionRole.HEAD, head),
        changed_paths=(
            PullRequestChangedPath(
                path=GitRepositoryPath(CHANGED_PATH),
                head_object=GitBlobIdentity(
                    kind=GitObjectKind.BLOB,
                    algorithm=GitHashAlgorithm.SHA1,
                    full_digest=CHANGED_BLOB,
                ),
                status=ChangedPathStatus("modified"),
            ),
        ),
    )


def _source_association(
    report: SuppliedFaultReport | None = None,
    repository: str = REPOSITORY_ID,
) -> FaultReportSourceObjectAssociation:
    return FaultReportSourceObjectAssociation(
        report=_report() if report is None else report,
        source_object=_pull_request(repository),
    )


def _history_association(
    report: SuppliedFaultReport | None = None,
) -> FaultReportHistoryFactAssociation:
    return FaultReportHistoryFactAssociation(
        report=_report() if report is None else report,
        history_fact=_binding(RevisionRole.HEAD, HEAD_REVISION),
    )


def _candidate(
    candidate: uuid.UUID = CANDIDATE,
    report: SuppliedFaultReport | None = None,
    statement: str = "Evaluate the side-effecting expression once and reuse it.",
) -> SuppliedFaultRepairCandidate:
    return SuppliedFaultRepairCandidate(
        candidate=FaultRepairCandidateIdentity(candidate),
        report=_report() if report is None else report,
        repair_statement=statement,
    )


def _candidate_revision(
    candidate: SuppliedFaultRepairCandidate | None = None,
    digest: str = HEAD_REVISION,
) -> FaultRepairCandidateRevisionAssociation:
    return FaultRepairCandidateRevisionAssociation(
        candidate=_candidate() if candidate is None else candidate,
        revision=_commit(digest),
    )


def _candidate_change_set(
    candidate: SuppliedFaultRepairCandidate | None = None,
    head: str = HEAD_REVISION,
) -> FaultRepairCandidateChangeSetAssociation:
    return FaultRepairCandidateChangeSetAssociation(
        candidate=_candidate() if candidate is None else candidate,
        change_set=_change_set(head),
    )


def _material(
    material: uuid.UUID = MATERIAL,
    report: SuppliedFaultReport | None = None,
    statement: str = "A regression test asserting the callback runs exactly once.",
) -> SuppliedFaultTestMaterial:
    return SuppliedFaultTestMaterial(
        material=FaultTestMaterialIdentity(material),
        report=_report() if report is None else report,
        test_statement=statement,
    )


def _run(
    run: uuid.UUID = RUN,
    material: SuppliedFaultTestMaterial | None = None,
    statement: str = "Reported as run from a local checkout by the caller.",
) -> ReportedFaultTestRun:
    return ReportedFaultTestRun(
        run=FaultTestRunIdentity(run),
        test_material=_material() if material is None else material,
        run_statement=statement,
    )


def _outcome(
    run: ReportedFaultTestRun | None = None,
    kind: ReportedFaultTestOutcomeKind = ReportedFaultTestOutcomeKind.FAILED,
    statement: str = "Reported as ending with the assertion the caller described.",
) -> ReportedFaultTestOutcome:
    return ReportedFaultTestOutcome(
        run=_run() if run is None else run,
        outcome=kind,
        outcome_statement=statement,
    )


def _run_revision(
    run: ReportedFaultTestRun | None = None,
    digest: str = HEAD_REVISION,
) -> FaultTestRunRevisionAssociation:
    return FaultTestRunRevisionAssociation(
        run=_run() if run is None else run,
        revision=_commit(digest),
    )


def _explanation(
    explanation: uuid.UUID = EXPLANATION,
    report: SuppliedFaultReport | None = None,
    statement: str = "The caller accounts for it by a second evaluation.",
) -> SuppliedFaultExplanation:
    return SuppliedFaultExplanation(
        explanation=FaultExplanationIdentity(explanation),
        report=_report() if report is None else report,
        explanation_statement=statement,
    )


def _hypothesis(
    hypothesis: uuid.UUID = HYPOTHESIS,
    report: SuppliedFaultReport | None = None,
    statement: str = "The caller proposes, tentatively, a stale rewrite cache.",
) -> SuppliedFaultHypothesis:
    return SuppliedFaultHypothesis(
        hypothesis=FaultHypothesisIdentity(hypothesis),
        report=_report() if report is None else report,
        hypothesis_statement=statement,
    )


def _expected_property(
    expected_property: uuid.UUID = PROPERTY,
    report: SuppliedFaultReport | None = None,
    statement: str = "For this report, evaluation count should be preserved.",
) -> SuppliedFaultExpectedProperty:
    return SuppliedFaultExpectedProperty(
        expected_property=FaultExpectedPropertyIdentity(expected_property),
        report=_report() if report is None else report,
        expected_property_statement=statement,
    )


def _instance(**overrides: Any) -> FaultInstance:
    supplied: dict[str, Any] = {
        "fault": FaultInstanceIdentity(FAULT),
        "reports": (_report(),),
    }
    supplied.update(overrides)
    return FaultInstance(**supplied)


def _payload(value: BaseModel) -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(value.model_dump_json()))


def _failures(error: ValidationError) -> tuple[tuple[tuple[str | int, ...], str], ...]:
    return tuple((detail["loc"], detail["type"]) for detail in error.errors())


def _messages(error: ValidationError) -> str:
    return " ".join(detail["msg"] for detail in error.errors())


def _instance_tree() -> ast.Module:
    return ast.parse(INSTANCE_SOURCE.read_bytes(), filename=INSTANCE_SOURCE.name)


def _roadmap() -> str:
    return " ".join(ROADMAP.read_text(encoding="utf-8").split())


# The supporting collections each collection's members need in order to
# resolve. Composed here once so every reference test states only its own edge.
def _support(name: str) -> dict[str, Any]:
    scenario_support = {"scenarios": (_scenario(),)}
    candidate_support = {"repair_candidates": (_candidate(),)}
    material_support = {"test_materials": (_material(),)}
    run_support = {**material_support, "test_runs": (_run(),)}
    outcome_support = {**run_support, "test_outcomes": (_outcome(),)}
    return {
        "occurrences": scenario_support,
        "repair_revision_associations": candidate_support,
        "repair_change_set_associations": candidate_support,
        "test_runs": material_support,
        "test_outcomes": run_support,
        "test_run_revision_associations": run_support,
        "test_comparisons": outcome_support,
    }.get(name, {})


def _repeatable_record(name: str) -> Any:
    """One member for a collection that carries no subject identity."""
    return {
        "source_object_associations": _source_association(),
        "history_fact_associations": _history_association(),
        "repair_revision_associations": _candidate_revision(),
        "repair_change_set_associations": _candidate_change_set(),
        "test_outcomes": _outcome(),
        "test_run_revision_associations": _run_revision(),
    }[name]


# --- the minimal instance and empty-collection semantics ----------------------


def test_a_minimal_instance_is_one_identity_and_one_report() -> None:
    instance = _instance()

    assert instance.fault == FaultInstanceIdentity(FAULT)
    assert instance.reports == (_report(),)
    for name in OPTIONAL_FIELDS:
        assert getattr(instance, name) == (), name


def test_an_identity_alone_is_not_a_fault_instance() -> None:
    """`reports` carries a minimum of one, so identity alone cannot compose."""
    with pytest.raises(ValidationError) as failure:
        FaultInstance(fault=FaultInstanceIdentity(FAULT))  # pyright: ignore[reportCallIssue]

    assert _failures(failure.value) == ((("reports",), "missing"),)

    with pytest.raises(ValidationError) as empty:
        _instance(reports=())

    assert _failures(empty.value) == ((("reports",), "too_short"),)


@pytest.mark.parametrize("name", OPTIONAL_FIELDS)
def test_an_omitted_collection_equals_an_explicitly_empty_one(name: str) -> None:
    """Absence at this layer is membership, not a negative fact."""
    omitted = _instance()
    explicit = _instance(**{name: ()})

    assert omitted == explicit
    assert getattr(explicit, name) == ()
    assert _payload(omitted) == _payload(explicit)
    assert _payload(explicit)[name] == []


@pytest.mark.parametrize("name", OPTIONAL_FIELDS)
def test_an_empty_collection_creates_no_negative_fact_field(name: str) -> None:
    """No `None`, sentinel, or boolean stands beside an empty collection."""
    instance = _instance()

    assert None not in instance.model_dump().values()
    assert tuple(FaultInstance.model_fields) == EXPECTED_FIELDS
    for forbidden in FORBIDDEN_IDENTIFIERS:
        assert forbidden not in FaultInstance.model_fields, forbidden
    assert f'"{name}": null' not in instance.model_dump_json()


@pytest.mark.parametrize("name", OPTIONAL_FIELDS)
def test_an_explicit_none_is_refused(name: str) -> None:
    with pytest.raises(ValidationError) as failure:
        _instance(**{name: None})

    assert _failures(failure.value)[0][0] == (name,)


# --- one fault, several reports, several repositories -------------------------


def test_two_reports_for_one_fault_compose() -> None:
    first = _report()
    second = _report(SECOND_REPORT, problem=OTHER_PROBLEM, deviation=OTHER_DEVIATION)
    instance = _instance(reports=(first, second))

    assert instance.reports == (first, second)
    assert [report.context.fault for report in instance.reports] == [
        FaultInstanceIdentity(FAULT),
        FaultInstanceIdentity(FAULT),
    ]


def test_reports_for_one_fault_may_name_different_repositories() -> None:
    """Composing them claims no cross-repository applicability."""
    here = _report()
    elsewhere = _report(SECOND_REPORT, repository=OTHER_REPOSITORY_ID)
    instance = _instance(reports=(here, elsewhere))

    repositories = [report.context.repository for report in instance.reports]
    assert repositories[0] != repositories[1]
    assert tuple(FaultInstance.model_fields) == EXPECTED_FIELDS


def test_a_report_describing_another_fault_is_refused() -> None:
    with pytest.raises(ValidationError) as failure:
        _instance(reports=(_report(), _report(SECOND_REPORT, fault=OTHER_FAULT)))

    assert "reports[1] describes a different fault subject" in _messages(failure.value)


def test_the_composed_fault_is_not_taken_from_the_reports() -> None:
    """The aggregate's own identity is the subject, and it is checked."""
    with pytest.raises(ValidationError) as failure:
        FaultInstance(fault=FaultInstanceIdentity(OTHER_FAULT), reports=(_report(),))

    assert "reports[0] describes a different fault subject" in _messages(failure.value)


# --- primary subject identity uniqueness inside one composition ---------------

UNIQUENESS_CASES: tuple[tuple[str, Any, Any], ...] = (
    ("reports", _report(), _report(problem="A different problem statement.")),
    ("scenarios", _scenario(), _scenario(statement="A different scenario.")),
    ("occurrences", _occurrence(), None),
    ("repair_candidates", _candidate(), _candidate(statement="Different repair.")),
    ("test_materials", _material(), _material(statement="Different material.")),
    ("test_runs", _run(), _run(statement="Different run prose.")),
    ("explanations", _explanation(), _explanation(statement="Different account.")),
    ("hypotheses", _hypothesis(), _hypothesis(statement="Different proposition.")),
    (
        "expected_properties",
        _expected_property(),
        _expected_property(statement="A different expectation."),
    ),
)


@pytest.mark.parametrize(
    ("name", "record"),
    [(n, r) for n, r, _ in UNIQUENESS_CASES],
    ids=[n for n, _, _ in UNIQUENESS_CASES],
)
def test_one_subject_identity_appears_at_most_once(name: str, record: Any) -> None:
    """Identical records naming one subject are still a collision."""
    supplied = {**_support(name), name: (record, record)}

    with pytest.raises(ValidationError) as failure:
        _instance(**supplied)

    assert f"{name} names one subject identity more than once" in _messages(
        failure.value
    )


@pytest.mark.parametrize(
    ("name", "first", "second"),
    [(n, a, b) for n, a, b in UNIQUENESS_CASES if b is not None],
    ids=[n for n, _, b in UNIQUENESS_CASES if b is not None],
)
def test_conflicting_records_naming_one_subject_are_also_refused(
    name: str, first: Any, second: Any
) -> None:
    """Choosing between two contradictory records is not this layer's call."""
    assert first != second
    supplied = {**_support(name), name: (first, second)}

    with pytest.raises(ValidationError) as failure:
        _instance(**supplied)

    assert f"{name} names one subject identity more than once" in _messages(
        failure.value
    )


def test_one_uuid_scalar_may_name_several_nominal_identities() -> None:
    """Uniqueness is per identity type, never across the scalar space."""
    shared = FAULT
    report = _report(shared)
    scenario = _scenario(shared, report)
    instance = FaultInstance(
        fault=FaultInstanceIdentity(shared),
        reports=(report,),
        scenarios=(scenario,),
        test_materials=(_material(shared, report),),
    )

    assert instance.fault.root == shared
    assert instance.reports[0].report.root == shared
    assert instance.scenarios[0].scenario.root == shared
    assert instance.test_materials[0].material.root == shared


@pytest.mark.parametrize(
    "name",
    (
        "source_object_associations",
        "history_fact_associations",
        "repair_revision_associations",
        "repair_change_set_associations",
        "test_outcomes",
        "test_run_revision_associations",
    ),
)
def test_a_collection_without_its_own_subject_carries_no_uniqueness_rule(
    name: str,
) -> None:
    """Repetition there is a supplied claim rather than a collision."""
    record = _repeatable_record(name)
    instance = _instance(**{**_support(name), name: (record, record)})

    assert len(getattr(instance, name)) == 2


# --- reference integrity, by whole record rather than by identifier -----------

# Each edge names the collection under test, a valid member, a member whose
# reference is absent from the composition, and -- where the referenced value
# carries a subject identity -- a member whose reference shares that identity
# while differing in content. The last is what separates whole-record
# membership from scalar matching.
DIVERGENT_REPORT = _report(problem="A materially different problem statement.")
DIVERGENT_SCENARIO = _scenario(statement="A materially different scenario.")
DIVERGENT_CANDIDATE = _candidate(statement="A materially different repair.")
DIVERGENT_MATERIAL = _material(statement="Materially different test material.")
DIVERGENT_RUN = _run(statement="Materially different run prose.")

REFERENCE_EDGES: tuple[tuple[str, Any, Any, Any], ...] = (
    (
        "scenarios",
        _scenario(),
        _scenario(report=_report(SECOND_REPORT)),
        _scenario(report=DIVERGENT_REPORT),
    ),
    (
        "source_object_associations",
        _source_association(),
        _source_association(report=_report(SECOND_REPORT)),
        _source_association(report=DIVERGENT_REPORT),
    ),
    (
        "history_fact_associations",
        _history_association(),
        _history_association(report=_report(SECOND_REPORT)),
        _history_association(report=DIVERGENT_REPORT),
    ),
    (
        "repair_candidates",
        _candidate(),
        _candidate(report=_report(SECOND_REPORT)),
        _candidate(report=DIVERGENT_REPORT),
    ),
    (
        "test_materials",
        _material(),
        _material(report=_report(SECOND_REPORT)),
        _material(report=DIVERGENT_REPORT),
    ),
    (
        "explanations",
        _explanation(),
        _explanation(report=_report(SECOND_REPORT)),
        _explanation(report=DIVERGENT_REPORT),
    ),
    (
        "hypotheses",
        _hypothesis(),
        _hypothesis(report=_report(SECOND_REPORT)),
        _hypothesis(report=DIVERGENT_REPORT),
    ),
    (
        "expected_properties",
        _expected_property(),
        _expected_property(report=_report(SECOND_REPORT)),
        _expected_property(report=DIVERGENT_REPORT),
    ),
    (
        "occurrences",
        _occurrence(),
        _occurrence(scenario=_scenario(uuid.uuid5(SCENARIO, "x"))),
        _occurrence(scenario=DIVERGENT_SCENARIO),
    ),
    (
        "repair_revision_associations",
        _candidate_revision(),
        _candidate_revision(candidate=_candidate(SECOND_CANDIDATE)),
        _candidate_revision(candidate=DIVERGENT_CANDIDATE),
    ),
    (
        "repair_change_set_associations",
        _candidate_change_set(),
        _candidate_change_set(candidate=_candidate(SECOND_CANDIDATE)),
        _candidate_change_set(candidate=DIVERGENT_CANDIDATE),
    ),
    (
        "test_runs",
        _run(),
        _run(material=_material(uuid.uuid5(MATERIAL, "x"))),
        _run(material=DIVERGENT_MATERIAL),
    ),
    (
        "test_outcomes",
        _outcome(),
        _outcome(run=_run(SECOND_RUN)),
        _outcome(run=DIVERGENT_RUN),
    ),
    (
        "test_run_revision_associations",
        _run_revision(),
        _run_revision(run=_run(SECOND_RUN)),
        _run_revision(run=DIVERGENT_RUN),
    ),
)
EDGE_IDS = tuple(name for name, _, _, _ in REFERENCE_EDGES)


@pytest.mark.parametrize(
    ("name", "valid"), [(n, v) for n, v, _, _ in REFERENCE_EDGES], ids=EDGE_IDS
)
def test_a_resolved_reference_composes(name: str, valid: Any) -> None:
    instance = _instance(**{**_support(name), name: (valid,)})

    assert getattr(instance, name) == (valid,)


@pytest.mark.parametrize(
    ("name", "dangling"), [(n, d) for n, _, d, _ in REFERENCE_EDGES], ids=EDGE_IDS
)
def test_a_dangling_reference_is_refused(name: str, dangling: Any) -> None:
    """Refused rather than repaired: nothing is auto-inserted."""
    with pytest.raises(ValidationError) as failure:
        _instance(**{**_support(name), name: (dangling,)})

    assert "does not carry" in _messages(failure.value)


@pytest.mark.parametrize(
    ("name", "divergent"), [(n, d) for n, _, _, d in REFERENCE_EDGES], ids=EDGE_IDS
)
def test_a_reference_sharing_an_identity_but_not_the_record_is_refused(
    name: str, divergent: Any
) -> None:
    """Membership is by whole record, so a scalar match is not enough.

    Each referenced value here carries the same subject identity as the one the
    composition holds while disagreeing in its supplied content. Matching the
    embedded identifier would silently select one of the two.
    """
    with pytest.raises(ValidationError) as failure:
        _instance(**{**_support(name), name: (divergent,)})

    assert "does not carry" in _messages(failure.value)


def test_a_comparison_needs_both_outcomes_in_the_composition() -> None:
    material = _material()
    before_run = _run(RUN, material)
    after_run = _run(SECOND_RUN, material, statement="Reported as run again.")
    before = _outcome(before_run, ReportedFaultTestOutcomeKind.FAILED)
    after = _outcome(
        after_run,
        ReportedFaultTestOutcomeKind.PASSED,
        statement="Reported as ending without the described assertion.",
    )
    comparison = ReportedFaultTestComparison(
        before=before,
        after=after,
        comparison_statement="The caller reports the two attempts for comparison.",
    )
    support: dict[str, Any] = {
        "test_materials": (material,),
        "test_runs": (before_run, after_run),
    }

    composed = _instance(
        **support, test_outcomes=(before, after), test_comparisons=(comparison,)
    )
    assert composed.test_comparisons == (comparison,)

    # Holding only one of the two outcomes leaves the other end dangling.
    for held in ((before,), (after,)):
        with pytest.raises(ValidationError) as failure:
            _instance(**support, test_outcomes=held, test_comparisons=(comparison,))
        assert "test_comparisons." in _messages(failure.value)


def test_a_comparison_end_that_diverges_from_the_composed_outcome_is_refused() -> None:
    """Naming the same run is not being the same published outcome.

    This is the comparison edge's share of the whole-record rule the other
    fourteen edges get from `REFERENCE_EDGES`. Without it a composition
    carrying a `failed` outcome would accept a comparison whose `before` is a
    `passed` copy of that outcome, which is exactly the substitution the rule
    exists to refuse.
    """
    material = _material()
    before_run = _run(RUN, material)
    after_run = _run(SECOND_RUN, material, statement="Reported as run again.")
    before = _outcome(before_run, ReportedFaultTestOutcomeKind.FAILED)
    after = _outcome(
        after_run,
        ReportedFaultTestOutcomeKind.PASSED,
        statement="Reported as ending without the described assertion.",
    )
    support: dict[str, Any] = {
        "test_materials": (material,),
        "test_runs": (before_run, after_run),
        "test_outcomes": (before, after),
    }
    statement = "The caller reports the two attempts for comparison."

    # A copy diverging in the reported kind, and one diverging only in its
    # prose. Either is a different published record.
    divergent = {
        "before": _outcome(before_run, ReportedFaultTestOutcomeKind.PASSED),
        "after": _outcome(
            after_run,
            ReportedFaultTestOutcomeKind.PASSED,
            statement="Reported as ending with a differently worded account.",
        ),
    }
    for end, substitute in divergent.items():
        ends = {"before": before, "after": after} | {end: substitute}
        assert substitute not in (before, after)
        with pytest.raises(ValidationError) as failure:
            _instance(
                **support,
                test_comparisons=(
                    ReportedFaultTestComparison(**ends, comparison_statement=statement),
                ),
            )
        assert f"test_comparisons.{end}[0]" in _messages(failure.value)

    # The same shape with both ends as published is accepted, so the refusals
    # above are about divergence rather than about the case being built wrong.
    published = ReportedFaultTestComparison(
        before=before, after=after, comparison_statement=statement
    )
    composed = _instance(**support, test_comparisons=(published,))
    assert composed.test_comparisons == (published,)


def test_an_occurrence_does_not_insert_its_embedded_scenario() -> None:
    """The scenario must already be composed; the occurrence cannot add it."""
    with pytest.raises(ValidationError) as failure:
        _instance(occurrences=(_occurrence(),))

    assert "occurrences[0] references a value this composition does not carry" in (
        _messages(failure.value)
    )
    assert _instance(scenarios=(_scenario(),), occurrences=(_occurrence(),)).scenarios


def test_an_association_does_not_insert_its_embedded_candidate() -> None:
    with pytest.raises(ValidationError) as failure:
        _instance(repair_revision_associations=(_candidate_revision(),))

    assert "does not carry" in _messages(failure.value)
    resolved = _instance(
        repair_candidates=(_candidate(),),
        repair_revision_associations=(_candidate_revision(),),
    )
    assert len(resolved.repair_candidates) == 1


# --- conflicts this layer deliberately preserves ------------------------------


def test_two_conflicting_outcomes_for_one_run_coexist() -> None:
    """`S1.P06.S06` permits the disagreement; composing it resolves nothing."""
    material = _material()
    run = _run(RUN, material)
    failed = _outcome(run, ReportedFaultTestOutcomeKind.FAILED)
    passed = _outcome(
        run,
        ReportedFaultTestOutcomeKind.PASSED,
        statement="Reported as ending without the described assertion.",
    )
    instance = _instance(
        test_materials=(material,), test_runs=(run,), test_outcomes=(failed, passed)
    )

    assert instance.test_outcomes == (failed, passed)
    assert failed.run == passed.run
    assert failed.outcome is not passed.outcome
    for absent in ("winner", "flaky", "confidence", "conflict", "resolved"):
        assert absent not in FaultInstance.model_fields, absent


def test_conflicting_explanations_and_hypotheses_coexist() -> None:
    report = _report()
    explanations = (
        _explanation(EXPLANATION, report),
        _explanation(SECOND_EXPLANATION, report, statement="A contrary account."),
    )
    hypotheses = (
        _hypothesis(HYPOTHESIS, report),
        _hypothesis(SECOND_HYPOTHESIS, report, statement="A contrary proposition."),
    )
    instance = _instance(explanations=explanations, hypotheses=hypotheses)

    assert instance.explanations == explanations
    assert instance.hypotheses == hypotheses


def test_several_repair_candidates_may_address_one_report() -> None:
    report = _report()
    candidates = (
        _candidate(CANDIDATE, report),
        _candidate(SECOND_CANDIDATE, report, statement="A different repair."),
    )
    instance = _instance(repair_candidates=candidates)

    assert instance.repair_candidates == candidates


def test_several_source_and_history_associations_coexist() -> None:
    report = _report()
    instance = _instance(
        source_object_associations=(
            _source_association(report),
            _source_association(report, repository=OTHER_REPOSITORY_ID),
        ),
        history_fact_associations=(_history_association(report),) * 2,
    )

    assert len(instance.source_object_associations) == 2
    assert len(instance.history_fact_associations) == 2


# --- no coherence rule across independent supplied relations ------------------


def test_a_candidate_revision_need_not_equal_its_change_set_head() -> None:
    candidate = _candidate()
    instance = _instance(
        repair_candidates=(candidate,),
        repair_revision_associations=(
            _candidate_revision(candidate, digest=OTHER_REVISION),
        ),
        repair_change_set_associations=(
            _candidate_change_set(candidate, head=HEAD_REVISION),
        ),
    )

    associated = instance.repair_revision_associations[0].revision
    head = instance.repair_change_set_associations[0].change_set.head
    assert associated != head.role_assignment.revision


def test_a_run_revision_need_not_equal_a_repair_revision() -> None:
    candidate = _candidate()
    material = _material()
    run = _run(RUN, material)
    instance = _instance(
        repair_candidates=(candidate,),
        repair_revision_associations=(_candidate_revision(candidate, HEAD_REVISION),),
        test_materials=(material,),
        test_runs=(run,),
        test_run_revision_associations=(_run_revision(run, OTHER_REVISION),),
    )

    assert (
        instance.repair_revision_associations[0].revision
        != instance.test_run_revision_associations[0].revision
    )


def test_a_source_object_repository_need_not_equal_the_reports() -> None:
    report = _report(repository=REPOSITORY_ID)
    instance = _instance(
        reports=(report,),
        source_object_associations=(
            _source_association(report, repository=OTHER_REPOSITORY_ID),
        ),
    )

    source = instance.source_object_associations[0].source_object
    assert isinstance(source, NumberedSourceObjectIdentity)
    assert source.repository_identity != report.context.repository


def test_a_failed_to_passed_comparison_makes_no_repair_claim() -> None:
    """Composition adds no field a verdict could ever land in."""
    material = _material()
    before_run = _run(RUN, material)
    after_run = _run(SECOND_RUN, material, statement="Reported as run again.")
    before = _outcome(before_run, ReportedFaultTestOutcomeKind.FAILED)
    after = _outcome(
        after_run,
        ReportedFaultTestOutcomeKind.PASSED,
        statement="Reported as ending without the described assertion.",
    )
    comparison = ReportedFaultTestComparison(
        before=before,
        after=after,
        comparison_statement="The caller reports the two attempts for comparison.",
    )
    candidate = _candidate()
    instance = _instance(
        repair_candidates=(candidate,),
        test_materials=(material,),
        test_runs=(before_run, after_run),
        test_outcomes=(before, after),
        test_comparisons=(comparison,),
        expected_properties=(_expected_property(),),
    )

    assert tuple(_payload(instance)) == EXPECTED_FIELDS
    assert FaultInstance.model_computed_fields == {}
    text = instance.model_dump_json()
    for absent in ("verified", "correct", "supported", "caused", "confirmed"):
        assert f'"{absent}"' not in text, absent


# --- the collection boundary, ordering, and bounds -----------------------------


@pytest.mark.parametrize("name", ("reports", *OPTIONAL_FIELDS))
def test_a_python_list_is_refused_where_a_tuple_is_required(name: str) -> None:
    valid = {"reports": (_report(),), **{n: () for n in OPTIONAL_FIELDS}}
    member = {"reports": [_report()]}.get(name, [])
    with pytest.raises(ValidationError) as failure:
        _instance(**{**valid, name: member})

    assert _failures(failure.value)[0] == ((name,), "tuple_type")


@pytest.mark.parametrize(
    ("name", "member"),
    (
        ("reports", _report()),
        ("scenarios", _scenario()),
        ("repair_candidates", _candidate()),
        ("explanations", _explanation()),
    ),
)
def test_an_untyped_member_is_refused(name: str, member: Any) -> None:
    """Predecessor typed-child boundaries are not weakened by composition."""
    with pytest.raises(ValidationError) as failure:
        _instance(**{**_support(name), name: (member.model_dump(),)})

    assert _failures(failure.value)[0][0][:2] == (name, 0)


def test_the_composed_subject_must_already_be_a_published_identity() -> None:
    """The one position `strict=True` alone does not close.

    A `RootModel` field reconstructs from its own root type even under strict
    validation, so a bare `uuid.UUID` reaches `fault` unchallenged unless the
    module says otherwise. Composing means gathering values a caller already
    published; accepting the scalar inside an identity would let the aggregate
    mint one instead. Every predecessor closes its identity positions this way.
    """
    report = _report()

    for untyped in (FAULT, FAULT_TEXT):
        with pytest.raises(ValidationError) as failure:
            FaultInstance(fault=untyped, reports=(report,))
        assert "fault must be a FaultInstanceIdentity in Python input" in _messages(
            failure.value
        )

    composed = FaultInstance(fault=FaultInstanceIdentity(FAULT), reports=(report,))
    assert composed.fault == FaultInstanceIdentity(FAULT)


def test_the_composed_subject_still_reconstructs_from_json() -> None:
    """The Python guard must not close the JSON input language with it."""
    composed = _instance()
    payload = _payload(composed)

    assert payload["fault"] == FAULT_TEXT
    assert FaultInstance.model_validate_json(json.dumps(payload)) == composed


def test_a_semantic_json_round_trip_succeeds() -> None:
    instance = _instance(
        scenarios=(_scenario(),),
        occurrences=(_occurrence(),),
        repair_candidates=(_candidate(),),
        explanations=(_explanation(),),
    )

    assert FaultInstance.model_validate_json(instance.model_dump_json()) == instance


def test_a_json_array_reconstructs_the_tuple_members() -> None:
    instance = _instance(scenarios=(_scenario(),))
    payload = _payload(instance)

    assert isinstance(payload["scenarios"], list)
    restored = FaultInstance.model_validate_json(json.dumps(payload))
    assert isinstance(restored.scenarios, tuple)
    assert restored.scenarios[0] == _scenario()


def test_a_python_dump_reentry_is_not_required_to_succeed() -> None:
    """`model_dump` has already projected typed children to mappings."""
    instance = _instance()

    with pytest.raises(ValidationError):
        FaultInstance.model_validate(instance.model_dump())


def test_order_is_preserved_and_carries_no_meaning() -> None:
    first = _report()
    second = _report(SECOND_REPORT)
    forward = _instance(reports=(first, second))
    reversed_ = _instance(reports=(second, first))

    assert forward.reports == (first, second)
    assert reversed_.reports == (second, first)
    # Tuple equality includes order, and this layer does not canonicalise.
    assert forward != reversed_
    for absent in ("sorted", "canonical", "ordering", "priority"):
        assert absent not in FaultInstance.model_fields, absent


def test_the_declared_bound_is_pinned_on_every_collection() -> None:
    for name in EXPECTED_FIELDS[1:]:
        metadata = FaultInstance.model_fields[name].metadata
        maxima = [
            getattr(item, "max_length")
            for item in metadata
            if hasattr(item, "max_length") and item.max_length is not None
        ]
        assert maxima == [DECLARED_BOUND], name
    minima = [
        getattr(item, "min_length")
        for item in FaultInstance.model_fields["reports"].metadata
        if hasattr(item, "min_length") and item.min_length is not None
    ]
    assert minima == [1]


def test_the_bound_is_not_exported() -> None:
    assert instance_module.__all__ == ["FaultInstance"]
    assert not hasattr(instance_module, "MAX_MEMBERS")
    assert str(DECLARED_BOUND) in INSTANCE_SOURCE.read_text(encoding="utf-8")


def test_a_collection_accepts_the_bound_and_refuses_one_more() -> None:
    """Exercised on the cheapest collection rather than a deep nested graph."""
    report = _report()
    association = _source_association(report)
    at_bound = _instance(
        reports=(report,), source_object_associations=(association,) * DECLARED_BOUND
    )

    assert len(at_bound.source_object_associations) == DECLARED_BOUND

    with pytest.raises(ValidationError) as failure:
        _instance(
            reports=(report,),
            source_object_associations=(association,) * (DECLARED_BOUND + 1),
        )

    assert _failures(failure.value) == ((("source_object_associations",), "too_long"),)


# --- the module's own surface and boundaries -----------------------------------


def test_the_module_publishes_exactly_one_symbol() -> None:
    assert instance_module.__all__ == ["FaultInstance"]
    assert [
        node.name
        for node in ast.walk(_instance_tree())
        if isinstance(node, ast.ClassDef)
    ] == ["FaultInstance"]


def test_the_aggregate_declares_exactly_its_fields_in_order() -> None:
    assert tuple(FaultInstance.model_fields) == EXPECTED_FIELDS
    assert len(EXPECTED_FIELDS) == 17


def test_the_aggregate_declares_the_published_value_profile() -> None:
    assert FaultInstance.model_config == {
        "frozen": True,
        "extra": "forbid",
        "strict": True,
        "revalidate_instances": "always",
        "validate_default": True,
    }


def test_no_field_declares_an_input_or_output_alias() -> None:
    for name, field in FaultInstance.model_fields.items():
        assert field.alias is None, name
        assert field.validation_alias is None, name
        assert field.serialization_alias is None, name


def test_only_the_collections_are_optional_and_none_is_nullable() -> None:
    assert FaultInstance.model_fields["fault"].is_required()
    assert FaultInstance.model_fields["reports"].is_required()
    for name in OPTIONAL_FIELDS:
        field = FaultInstance.model_fields[name]
        assert not field.is_required(), name
        assert field.default == (), name
        assert field.default_factory is None, name
    for name, field in FaultInstance.model_fields.items():
        assert "None" not in str(field.annotation), name


def test_the_aggregate_publishes_no_attribute_beyond_its_fields() -> None:
    """A helper, factory, registry or computed field would be reachable here."""
    beyond = {name for name in dir(FaultInstance) if not name.startswith("_")} - set(
        dir(BaseModel)
    )

    assert beyond == set()
    assert FaultInstance.model_computed_fields == {}


@pytest.mark.parametrize(
    "prefix", ("add_", "resolve_", "infer_", "merge_", "dedupe_", "index_", "sort_")
)
def test_no_automatic_operation_is_published(prefix: str) -> None:
    for name in dir(FaultInstance):
        assert not name.startswith(prefix), name
    body = INSTANCE_SOURCE.read_text(encoding="utf-8").split('"""', 2)[-1]
    assert f"def {prefix}" not in body


DECLARED_VALIDATORS = (
    "_require_typed_python_fault",
    "_require_reports_name_the_composed_fault",
    "_require_unique_primary_subjects",
    "_require_report_references_are_members",
    "_require_layer_references_are_members",
)


def test_the_module_defines_only_the_declared_validators() -> None:
    """Any other function, however named, must fail here.

    `__all__` and the class list pin what is exported, not what exists: a
    resolver, a merger or a factory would change neither.
    """
    tree = _instance_tree()
    functions = [
        node.name
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)
    ]

    assert tuple(functions) == DECLARED_VALIDATORS
    for name in functions:
        assert name.startswith("_")
    assert [node for node in ast.walk(tree) if isinstance(node, ast.Lambda)] == []


EXPECTED_MODULE_BINDINGS = frozenset(
    {
        "FaultInstance",
        "uuid",
        "Annotated",
        "Self",
        "BaseModel",
        "ConfigDict",
        "Field",
        "ValidationInfo",
        "field_validator",
        "model_validator",
        "FaultInstanceIdentity",
        "SuppliedFaultOccurrenceContext",
        "SuppliedFaultReport",
        "SuppliedFaultScenario",
        "SuppliedFaultExpectedProperty",
        "SuppliedFaultExplanation",
        "SuppliedFaultHypothesis",
        "FaultRepairCandidateChangeSetAssociation",
        "FaultRepairCandidateRevisionAssociation",
        "SuppliedFaultRepairCandidate",
        "FaultReportHistoryFactAssociation",
        "FaultReportSourceObjectAssociation",
        "FaultTestRunRevisionAssociation",
        "ReportedFaultTestComparison",
        "ReportedFaultTestOutcome",
        "ReportedFaultTestRun",
        "SuppliedFaultTestMaterial",
    }
)


def test_the_module_binds_no_name_beyond_its_export_and_its_imports() -> None:
    """A registry or lookup table could also arrive as a module-level name."""
    bound = {
        name
        for name in vars(instance_module)
        if not name.startswith("_") and name.isidentifier()
    }

    assert bound == set(EXPECTED_MODULE_BINDINGS)


def test_the_module_is_not_re_exported_from_the_package_or_domain_root() -> None:
    assert faultatlas.__all__ == ["__version__"]
    assert not hasattr(faultatlas.domain, "__all__")
    assert not hasattr(faultatlas, "FaultInstance")
    assert not hasattr(faultatlas.domain, "FaultInstance")


def test_the_module_imports_only_the_layers_it_composes() -> None:
    imported = {
        alias.name if isinstance(node, ast.Import) else cast(str, node.module)
        for node in ast.walk(_instance_tree())
        if isinstance(node, ast.Import | ast.ImportFrom)
        for alias in node.names
    }

    # An exact set. The evidence layer, the history-evidence bridge and the
    # snapshot links are excluded by this equality rather than by a name list.
    assert imported == {
        "uuid",
        "typing",
        "pydantic",
        "faultatlas.domain.fault",
        "faultatlas.domain.fault_interpretation",
        "faultatlas.domain.fault_repair",
        "faultatlas.domain.fault_source_relationship",
        "faultatlas.domain.fault_test",
    }


def test_no_evidence_is_consumed() -> None:
    """The fault-evidence bridge is `S1.P06.S09` work."""
    source = INSTANCE_SOURCE.read_text(encoding="utf-8")

    for forbidden in (
        "faultatlas.domain.evidence",
        "faultatlas.domain.history_evidence_link",
        "faultatlas.domain.snapshot_evidence_link",
        "DurableEvidenceRecordReference",
        "PullRequestHistoryFactEvidenceLink",
    ):
        assert forbidden not in source, forbidden
    for absent in ("evidence", "evidence_record", "support", "supported"):
        assert absent not in FaultInstance.model_fields, absent


def test_the_tracked_production_inventory_is_nineteen_modules() -> None:
    tracked = subprocess.run(  # noqa: S603 - literal argv, no shell
        ["git", "ls-files", "src/"],
        cwd=REPOSITORY_ROOT,
        capture_output=True,
        check=False,
    )
    assert tracked.returncode == 0, tracked.stderr
    observed = sorted(tracked.stdout.decode("utf-8").split())

    assert observed == [f"src/{name}" for name in EXPECTED_PRODUCTION_MODULES]
    assert len(observed) == 19
    assert "src/faultatlas/domain/fault_instance.py" in observed


# --- the same four rules through the JSON input language ----------------------


# Each entry is a payload violating exactly one composition rule, the substitute
# that repairs it, and the message the rule raises. Building them from dumped
# records rather than from an invalid Python instance is the point: a payload
# this shape can arrive from a file or a request without ever having been a
# Python object, so the rule has to hold on the JSON path in its own right.
JSON_RULE_VIOLATIONS: tuple[tuple[str, dict[str, Any], dict[str, Any], str], ...] = (
    (
        "every report names the composed fault",
        {"reports": [_payload(_report(fault=OTHER_FAULT))]},
        {"reports": [_payload(_report())]},
        "reports[0] describes a different fault subject",
    ),
    (
        "a report identity appears once",
        {
            "reports": [
                _payload(_report()),
                _payload(_report(problem=OTHER_PROBLEM, deviation=OTHER_DEVIATION)),
            ]
        },
        {
            "reports": [
                _payload(_report()),
                _payload(
                    _report(
                        SECOND_REPORT, problem=OTHER_PROBLEM, deviation=OTHER_DEVIATION
                    )
                ),
            ]
        },
        "reports names one subject identity more than once",
    ),
    (
        "a referenced report is a member by whole record",
        {
            "reports": [_payload(_report())],
            "scenarios": [_payload(_scenario(report=DIVERGENT_REPORT))],
        },
        {
            "reports": [_payload(_report())],
            "scenarios": [_payload(_scenario())],
        },
        "scenarios[0] references a report this composition does not carry",
    ),
    (
        "a referenced layer value is a member",
        {
            "reports": [_payload(_report())],
            "occurrences": [_payload(_occurrence())],
        },
        {
            "reports": [_payload(_report())],
            "scenarios": [_payload(_scenario())],
            "occurrences": [_payload(_occurrence())],
        },
        "occurrences[0] references a value this composition does not carry",
    ),
)


@pytest.mark.parametrize(
    ("violation", "repair", "message"),
    [(v, r, m) for _, v, r, m in JSON_RULE_VIOLATIONS],
    ids=[name for name, _, _, _ in JSON_RULE_VIOLATIONS],
)
def test_each_composition_rule_holds_on_the_json_path(
    violation: dict[str, Any],
    repair: dict[str, Any],
    message: str,
) -> None:
    """A rule-violating payload is refused, and its repaired twin is accepted.

    The accepted half matters as much as the refused one: without it the test
    would still pass if JSON input were refused for some unrelated reason.
    """
    with pytest.raises(ValidationError) as failure:
        FaultInstance.model_validate_json(
            json.dumps({"fault": FAULT_TEXT, **violation})
        )

    assert message in _messages(failure.value)

    composed = FaultInstance.model_validate_json(
        json.dumps({"fault": FAULT_TEXT, **repair})
    )
    assert composed.fault == FaultInstanceIdentity(FAULT)


# --- the no-I/O behavioral witness ---------------------------------------------


# The whole attribute vocabulary the module's contract needs: the seventeen
# field names, the child fields it reads to check a reference, and `uuid.UUID`.
EXPECTED_ATTRIBUTE_VOCABULARY = {
    "UUID",
    "mode",
    "after",
    "before",
    "candidate",
    "context",
    "expected_properties",
    "expected_property",
    "explanation",
    "explanations",
    "fault",
    "history_fact_associations",
    "hypotheses",
    "hypothesis",
    "material",
    "occurrence",
    "occurrences",
    "repair_candidates",
    "repair_change_set_associations",
    "repair_revision_associations",
    "report",
    "reports",
    "root",
    "run",
    "scenario",
    "scenarios",
    "source_object_associations",
    "test_comparisons",
    "test_material",
    "test_materials",
    "test_outcomes",
    "test_run_revision_associations",
    "test_runs",
}


# The whole name vocabulary: the declared imports, the field and local names,
# and the six builtins the validators use.
EXPECTED_NAME_VOCABULARY = {
    "Annotated",
    "ValidationInfo",
    "classmethod",
    "field_validator",
    "info",
    "isinstance",
    "BaseModel",
    "ConfigDict",
    "FaultInstanceIdentity",
    "FaultRepairCandidateChangeSetAssociation",
    "FaultRepairCandidateRevisionAssociation",
    "FaultReportHistoryFactAssociation",
    "FaultReportSourceObjectAssociation",
    "FaultTestRunRevisionAssociation",
    "Field",
    "ReportedFaultTestComparison",
    "ReportedFaultTestOutcome",
    "ReportedFaultTestRun",
    "Self",
    "SuppliedFaultExpectedProperty",
    "SuppliedFaultExplanation",
    "SuppliedFaultHypothesis",
    "SuppliedFaultOccurrenceContext",
    "SuppliedFaultRepairCandidate",
    "SuppliedFaultReport",
    "SuppliedFaultScenario",
    "SuppliedFaultTestMaterial",
    "ValueError",
    "_MAX_MEMBERS",
    "__all__",
    "anchored",
    "edges",
    "enumerate",
    "expected_properties",
    "explanations",
    "fault",
    "history_fact_associations",
    "hypotheses",
    "identifiers",
    "index",
    "len",
    "members",
    "model_config",
    "model_validator",
    "name",
    "object",
    "occurrences",
    "record",
    "referenced",
    "repair_candidates",
    "repair_change_set_associations",
    "repair_revision_associations",
    "report",
    "reports",
    "scenarios",
    "self",
    "set",
    "source_object_associations",
    "str",
    "subjects",
    "test_comparisons",
    "test_materials",
    "test_outcomes",
    "test_run_revision_associations",
    "test_runs",
    "tuple",
    "uuid",
    "value",
}


def test_the_module_calls_no_builtin_that_opens_reads_or_executes() -> None:
    called = {
        node.func.id
        for node in ast.walk(_instance_tree())
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }

    assert not called & {"open", "eval", "exec", "compile", "__import__", "print"}


def test_the_module_names_no_identifier_beyond_its_published_vocabulary() -> None:
    """This closes the half an audit hook structurally cannot witness.

    CPython raises no audit event for `os.times`, `os.stat`, `os.environ` or
    anything in `time`, so the witness below cannot see a clock or environment
    read. Every such call has to reach `os` somehow, and the exact import set
    this module declares excludes importing it, so the remaining route is an
    attribute reached through a module it does import, or a name that fetches
    one.

    Screening for known-bad spellings is the wrong shape for that: whichever
    spelling is left off the list is the one that gets through. These two
    assertions pin the module's whole attribute and name vocabulary to what its
    published contract needs instead, so any identifier not in the contract --
    `uuid.os.times`, `getattr(uuid, "os")`, `__import__`, a `Path`, a
    `datetime` -- fails for being absent from it rather than for having been
    predicted.

    The cost of an exact pin is that an ordinary local-variable rename in the
    module fails here too. That is the intended trade: this file is a published
    contract, so its vocabulary changing at all is something a reader should be
    told about.
    """
    tree = _instance_tree()

    assert {
        node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute)
    } == EXPECTED_ATTRIBUTE_VOCABULARY
    assert {
        node.id for node in ast.walk(tree) if isinstance(node, ast.Name)
    } == EXPECTED_NAME_VOCABULARY


NO_IO_PROBE = """
import json
import sys
import uuid

# Every audit event is recorded and only the interpreter's own import and
# object machinery is allowed, so an unlisted call fails because it is not on
# the allowlist rather than because it was predicted.
IMPORT_PHASE_ALLOWED = frozenset({
    "builtins.id", "compile", "exec", "import", "marshal.loads",
    "object.__getattr__", "object.__setattr__", "open", "os.listdir",
    "sys._getframe", "sys._getframemodulename",
})
USE_PHASE_ALLOWED = IMPORT_PHASE_ALLOWED - {"os.listdir"}
WRITE_MODES = frozenset("wax+")
ENTROPY = ("/dev/urandom", "/dev/random")
INTERPRETER_ROOTS = tuple(
    sorted({sys.prefix, sys.base_prefix, sys.exec_prefix, sys.base_exec_prefix})
)
CHECKOUT_SOURCE_ROOT = sys.argv[1]
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

import faultatlas.domain.fault_instance as module
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
    report=FaultReportIdentity(uuid.UUID(sys.argv[2])),
    context=FaultRepositoryContext(
        fault=FaultInstanceIdentity(uuid.UUID(sys.argv[3])),
        repository=RepositoryIdentity(
            provider=ProviderKey("github"),
            provider_repository_id=ProviderRepositoryId(sys.argv[4]),
        ),
    ),
    problem_statement="probe problem",
    behavioral_deviation="probe deviation",
)
instance = module.FaultInstance(
    fault=FaultInstanceIdentity(uuid.UUID(sys.argv[3])), reports=(report,)
)
assert module.FaultInstance.model_validate_json(instance.model_dump_json()) == instance
module.FaultInstance.model_validate(instance)
module.FaultInstance.model_json_schema()
try:
    module.FaultInstance.model_validate(instance.model_dump())
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

    An audit hook is installed before the module is imported, in an isolated
    interpreter so it cannot contaminate any other test, and importing it,
    composing an instance, revalidating, serializing, refusing a Python dump
    and building the JSON schema must raise nothing outside the interpreter's
    own machinery.
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
            str(CHECKOUT_SOURCE_ROOT),
            REPORT_TEXT,
            FAULT_TEXT,
            REPOSITORY_ID,
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


# --- the roadmap transition ------------------------------------------------


def test_the_roadmap_records_the_p06_s08_transition() -> None:
    roadmap = _roadmap()
    mapping = roadmap.split("## Current-code mapping", 1)
    assert len(mapping) == 2, "roadmap must retain a current-code mapping section"
    current = mapping[1]

    assert "`S1.P06.S08` is complete" in roadmap
    assert "`S1.P06.S09` is next and not started" in roadmap
    assert (
        "`S1.P06.S08` — Bounded `FaultInstance` Composition and Reference "
        "Integrity (complete)" in roadmap
    )
    assert "The `S1.P06` route is provisional beyond `S1.P06.S08`." in roadmap

    assert "faultatlas.domain.fault_instance" in current
    assert "`FaultInstance`" in current
    assert "Production Python sources are 19." in current

    assert "`S1.P06.S08` is next and not started" not in roadmap
    assert "`S1.P06.S09` is complete" not in roadmap
    assert "Production Python sources are 18." not in roadmap


def test_the_roadmap_states_the_s08_decisions_and_non_claims() -> None:
    roadmap = _roadmap()

    for statement in (
        "production Python sources move from 18 to 19",
        "It is the first aggregate in the Phase",
        "The logical subject is the fault, not a report.",
        "claims no cross-repository applicability",
        "an identity alone is not a fault instance",
        "Reference integrity is by whole published record",
        "A dangling reference is refused rather than repaired",
        "local composition integrity and not a global registry",
        "Conflicts survive composition.",
        "creates no semantic edge a predecessor did not publish",
        "canonical durable ordering remains `S1.P10` work",
        "remains `S1.P06.S09` work",
    ):
        assert statement in roadmap, statement


def test_the_roadmap_preserves_the_predecessor_history_as_written() -> None:
    roadmap = _roadmap()

    assert "production Python sources move from 17 to 18" in roadmap
    assert "`S1.P06.S07.C01` correction" in roadmap
    assert "`S1.P05` is complete" in roadmap


# --- packaging and an isolated installed-wheel smoke --------------------------


EXPECTED_PRODUCTION_MODULES = [
    "faultatlas/__init__.py",
    "faultatlas/__main__.py",
    "faultatlas/cli.py",
    "faultatlas/domain/__init__.py",
    "faultatlas/domain/compatibility.py",
    "faultatlas/domain/evidence.py",
    "faultatlas/domain/fault.py",
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

import faultatlas.domain.fault_instance as instance_module
from faultatlas.domain.fault import (
    FaultInstanceIdentity,
    FaultOccurrenceIdentity,
    FaultReportIdentity,
    FaultRepositoryContext,
    FaultScenarioIdentity,
    SuppliedFaultOccurrenceContext,
    SuppliedFaultReport,
    SuppliedFaultScenario,
)
from faultatlas.domain.fault_instance import FaultInstance
from faultatlas.domain.fault_interpretation import (
    FaultExplanationIdentity,
    SuppliedFaultExplanation,
)
from faultatlas.domain.fault_repair import (
    FaultRepairCandidateIdentity,
    SuppliedFaultRepairCandidate,
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

module = Path(instance_module.__file__).resolve()
assert module.is_relative_to(installed), module
assert not module.is_relative_to(checkout), module
assert instance_module.__all__ == ["FaultInstance"]

fault = FaultInstanceIdentity(uuid.UUID(os.environ["FAULT_UUID"]))
report = SuppliedFaultReport(
    report=FaultReportIdentity(uuid.UUID(os.environ["REPORT_UUID"])),
    context=FaultRepositoryContext(
        fault=fault,
        repository=RepositoryIdentity(
            provider=ProviderKey("github"),
            provider_repository_id=ProviderRepositoryId(os.environ["REPOSITORY_ID"]),
        ),
    ),
    problem_statement=os.environ["PROBLEM"],
    behavioral_deviation=os.environ["DEVIATION"],
)

minimal = FaultInstance(fault=fault, reports=(report,))
assert minimal.scenarios == ()
assert FaultInstance.model_validate_json(minimal.model_dump_json()) == minimal

scenario = SuppliedFaultScenario(
    scenario=FaultScenarioIdentity(uuid.UUID(os.environ["SCENARIO_UUID"])),
    report=report,
    scenario_statement="probe scenario",
)
occurrence = SuppliedFaultOccurrenceContext(
    occurrence=FaultOccurrenceIdentity(uuid.UUID(os.environ["OCCURRENCE_UUID"])),
    scenario=scenario,
    occurrence_context="probe occurrence",
)
candidate = SuppliedFaultRepairCandidate(
    candidate=FaultRepairCandidateIdentity(uuid.UUID(os.environ["CANDIDATE_UUID"])),
    report=report,
    repair_statement="probe repair",
)
material = SuppliedFaultTestMaterial(
    material=FaultTestMaterialIdentity(uuid.UUID(os.environ["MATERIAL_UUID"])),
    report=report,
    test_statement="probe material",
)
run = ReportedFaultTestRun(
    run=FaultTestRunIdentity(uuid.UUID(os.environ["RUN_UUID"])),
    test_material=material,
    run_statement="probe run",
)
outcome = ReportedFaultTestOutcome(
    run=run,
    outcome=ReportedFaultTestOutcomeKind.FAILED,
    outcome_statement="probe outcome",
)
explanation = SuppliedFaultExplanation(
    explanation=FaultExplanationIdentity(uuid.UUID(os.environ["EXPLANATION_UUID"])),
    report=report,
    explanation_statement="probe explanation",
)

vertical = FaultInstance(
    fault=fault,
    reports=(report,),
    scenarios=(scenario,),
    occurrences=(occurrence,),
    repair_candidates=(candidate,),
    test_materials=(material,),
    test_runs=(run,),
    test_outcomes=(outcome,),
    explanations=(explanation,),
)
assert FaultInstance.model_validate_json(vertical.model_dump_json()) == vertical

print(
    json.dumps(
        {
            "module": str(module),
            "fields": list(FaultInstance.model_fields),
            "minimal": minimal.model_dump_json(),
            "vertical_keys": sorted(
                key
                for key, value in json.loads(vertical.model_dump_json()).items()
                if value
            ),
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

    root = tmp_path_factory.mktemp("fault-instance-package")
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


def test_the_wheel_ships_nineteen_modules_and_no_corpus_or_test_material(
    offline_distributions: tuple[Path, Path],
) -> None:
    wheel, _ = offline_distributions
    with zipfile.ZipFile(wheel) as archive:
        names = tuple(info.filename for info in archive.infolist() if not info.is_dir())

    modules = sorted(name for name in names if name.endswith(".py"))
    assert modules == EXPECTED_PRODUCTION_MODULES
    assert len(modules) == 19
    assert "faultatlas/domain/fault_instance.py" in modules
    for name in names:
        assert "reference_corpus" not in name
        assert not name.startswith("tests/")
        assert not name.startswith("docs/")


def test_the_sdist_ships_nineteen_modules_and_no_corpus_or_test_material(
    offline_distributions: tuple[Path, Path],
) -> None:
    _, sdist = offline_distributions
    with tarfile.open(sdist, "r:gz") as archive:
        names = tuple(member.name for member in archive.getmembers() if member.isfile())

    modules = sorted(
        name.split("/src/", 1)[1] for name in names if name.endswith(".py")
    )
    assert modules == EXPECTED_PRODUCTION_MODULES
    assert len(modules) == 19
    assert "faultatlas/domain/fault_instance.py" in modules
    for name in names:
        parts = Path(name).parts
        assert "reference_corpus" not in parts
        assert "tests" not in parts
        assert "docs" not in parts


def test_the_installed_wheel_composes_a_minimal_instance_and_a_vertical(
    offline_distributions: tuple[Path, Path],
    tmp_path: Path,
) -> None:
    """Both compositions must run from the wheel copy, not the checkout."""
    wheel, _ = offline_distributions
    installed = tmp_path / "installed"
    installed.mkdir()
    with zipfile.ZipFile(wheel) as archive:
        archive.extractall(installed)

    assert (installed / "faultatlas/domain/fault_instance.py").is_file()

    environment = os.environ.copy()
    environment.update(
        {
            "INSTALLED_ROOT": str(installed),
            "CHECKOUT_SOURCE_ROOT": str(CHECKOUT_SOURCE_ROOT),
            "FAULT_UUID": FAULT_TEXT,
            "REPORT_UUID": REPORT_TEXT,
            "SCENARIO_UUID": str(SCENARIO),
            "OCCURRENCE_UUID": str(OCCURRENCE),
            "CANDIDATE_UUID": str(CANDIDATE),
            "MATERIAL_UUID": str(MATERIAL),
            "RUN_UUID": str(RUN),
            "EXPLANATION_UUID": str(EXPLANATION),
            "REPOSITORY_ID": REPOSITORY_ID,
            "PROBLEM": PROBLEM,
            "DEVIATION": DEVIATION,
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
    assert tuple(reported["fields"]) == EXPECTED_FIELDS
    assert json.loads(reported["minimal"]) == _payload(_instance())
    assert reported["vertical_keys"] == sorted(
        (
            "fault",
            "reports",
            "scenarios",
            "occurrences",
            "repair_candidates",
            "test_materials",
            "test_runs",
            "test_outcomes",
            "explanations",
        )
    )
