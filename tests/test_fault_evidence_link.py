from __future__ import annotations

import ast
import json
import os
import shutil
import subprocess
import sys
import tarfile
import typing
import uuid
import zipfile
from pathlib import Path
from typing import Any, cast

import pytest
from pydantic import BaseModel, ConfigDict, ValidationError, field_validator

import faultatlas.domain.fault_evidence_link as link_module
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
    FaultOccurrenceIdentity,
    FaultReportIdentity,
    FaultRepositoryContext,
    FaultScenarioIdentity,
    SuppliedFaultOccurrenceContext,
    SuppliedFaultReport,
    SuppliedFaultScenario,
)
from faultatlas.domain.fault_evidence_link import FaultInstanceEvidenceLink
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
from faultatlas.domain.history_evidence_link import PullRequestHistoryFactEvidenceLink
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
    GitTreeIdentity,
    RevisionRole,
    RevisionRoleAssignment,
)
from faultatlas.domain.snapshot import (
    RepositorySnapshotIdentity,
    RepositorySnapshotRootTreeBinding,
)
from faultatlas.domain.snapshot_evidence_link import RepositorySnapshotFactEvidenceLink

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
LINK_SOURCE = REPOSITORY_ROOT / "src/faultatlas/domain/fault_evidence_link.py"
CHECKOUT_SOURCE_ROOT = REPOSITORY_ROOT / "src"
ROADMAP = REPOSITORY_ROOT / "docs/roadmap.md"

# Retained provenance from the pytest #4412 / #4414 case. These name a real
# retained normalized observation and the real retained acquisition record.
CANONICAL_PROVIDER = "github"
CANONICAL_REPOSITORY_ID = "37489525"
CANONICAL_PULL_REQUEST_NUMBER = "4414"
CANONICAL_BASE_REVISION = "4c9cde74ab40027b5761ab9e002af116a4a20df3"
CANONICAL_HEAD_REVISION = "690a63b9218f72662cd3a67c6c200b758c88ce12"
CANONICAL_CHANGED_PATH = "src/_pytest/assertion/rewrite.py"
CANONICAL_CHANGED_BLOB = "7b9aa5006544c160f584f1e8fc3f7771ef6e5e99"
CANONICAL_ROOT_TREE = "1" * 40

# The retained acquisition record, referenced whole.
CANONICAL_RECORD_FORMAT = "faultatlas-acquisition"
CANONICAL_RECORD_VERSION = "1"
CANONICAL_RECORD_CANONICALIZATION = "json-sort-keys-compact-utf8-lf-v1"
CANONICAL_RECORD_SHA256 = (
    "1c29093bf1537e9b824a18df1848b71a8da014f544bc9f385707eb0e000a1318"
)
CANONICAL_RECORD_LENGTH = 61_283
# A second retained record. A caller may name it; nothing here follows it.
CANONICAL_CORRECTION_FORMAT = "faultatlas-pytest-4412-acquisition-closure-addendum"
CANONICAL_CORRECTION_SHA256 = (
    "44491ee512d2c2022110b83967fb6fa86d13045bc8404ea490d7a08b7aef24a2"
)
CANONICAL_CORRECTION_LENGTH = 60_832

# Fixed synthetic P06 identities. The retained case supplies no fault instance
# and no fault UUID, so every identifier below is invented for this file.
FAULT_TEXT = "12345678-1234-4234-8234-123456789abc"
FAULT = uuid.UUID(FAULT_TEXT)
REPORT_TEXT = "87654321-4321-4abc-8def-0123456789ab"
REPORT = uuid.UUID(REPORT_TEXT)
SCENARIO = uuid.UUID("2b2b2b2b-3c3c-4d4d-8e8e-9f9f9f9f9f9f")
OCCURRENCE = uuid.UUID("74747474-8585-4696-8a7a-b8b8b8b8b8b8")
CANDIDATE = uuid.UUID("5c5c5c5c-6d6d-4e7e-8f8f-909090909090")
MATERIAL = uuid.UUID("3e3e3e3e-4f4f-4a5a-8b6b-7c7c7c7c7c7c")
RUN = uuid.UUID("0a0a0a0a-1b1b-4c2c-8d3d-4e4e4e4e4e4e")
SECOND_RUN = uuid.UUID("5f5f5f5f-6060-4171-8282-939393939393")
EXPLANATION = uuid.UUID("6a6a6a6a-7b7b-4c8c-89d9-0e0e0e0e0e0e")
HYPOTHESIS = uuid.UUID("42424242-5353-4646-8757-686868686868")
PROPERTY = uuid.UUID("cdcdcdcd-bebe-4faf-80b0-c1c1c1c1c1c1")

PROBLEM = "Instrumentation can change callback behavior."
DEVIATION = "The supplied transformed path invokes one callback twice."
DIVERGENT_PROBLEM = "A cached rewrite may be reused after the source changes."

EXPECTED_FIELDS = ("fault_instance", "subject", "evidence_record")

# The module's declared boundary, read once and typed here. Every assertion
# below reads these rather than reaching into the module repeatedly.
SUBJECT_COLLECTIONS: dict[type[BaseModel], str] = link_module._SUBJECT_COLLECTIONS  # pyright: ignore[reportPrivateUsage]
ADMITTED_SUBJECT_TYPES: tuple[type[BaseModel], ...] = (
    link_module._ADMITTED_SUBJECT_TYPES  # pyright: ignore[reportPrivateUsage]
)

# The vocabulary an audit hook structurally cannot witness. CPython raises no
# event for `os.times`, `os.stat`, `os.environ` or anything in `time`, so these
# pins fail an unlisted identifier for being absent from the published
# contract rather than for having been predicted.
EXPECTED_ATTRIBUTE_VOCABULARY = {
    "dumps",
    "fault_instance",
    "mode",
    "model_validate_json",
    "subject",
}
EXPECTED_NAME_VOCABULARY = {
    "BaseModel",
    "ConfigDict",
    "DurableEvidenceRecordReference",
    "FaultInstance",
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
    "TypeError",
    "ValidationInfo",
    "ValueError",
    "_ADMITTED_SUBJECT_TYPES",
    "_AdmittedSubject",
    "_SUBJECT_COLLECTIONS",
    "__all__",
    "classmethod",
    "collection",
    "dict",
    "encoded",
    "error",
    "evidence_record",
    "fault_instance",
    "field_validator",
    "getattr",
    "info",
    "isinstance",
    "json",
    "model_config",
    "model_validator",
    "object",
    "self",
    "str",
    "subject",
    "tuple",
    "type",
    "value",
}

# Words that would turn this weak association into support, proof, review, or
# derivation. None may appear as an identifier anywhere in the module.
FORBIDDEN_IDENTIFIERS = (
    "confidence",
    "confirmed",
    "corroborates",
    "corroboration",
    "derived",
    "hypothesis_confirmed",
    "independent",
    "observed",
    "proves",
    "reproduced",
    "repair_correct",
    "review",
    "status",
    "strength",
    "supported",
    "supports",
    "support_role",
    "verified",
    "verifies",
)


# --- builders ---------------------------------------------------------------


def _repository(identifier: str = CANONICAL_REPOSITORY_ID) -> RepositoryIdentity:
    return RepositoryIdentity(
        provider=ProviderKey(CANONICAL_PROVIDER),
        provider_repository_id=ProviderRepositoryId(identifier),
    )


def _commit(digest: str = CANONICAL_HEAD_REVISION) -> GitCommitIdentity:
    return GitCommitIdentity(
        kind=GitObjectKind.COMMIT,
        algorithm=GitHashAlgorithm.SHA1,
        full_digest=digest,
    )


def _pull_request() -> NumberedSourceObjectIdentity:
    return NumberedSourceObjectIdentity(
        repository_identity=_repository(),
        kind=SourceObjectKind.PULL_REQUEST,
        repository_scoped_number=RepositoryScopedNumber(CANONICAL_PULL_REQUEST_NUMBER),
    )


def _binding(
    role: RevisionRole = RevisionRole.HEAD,
    digest: str = CANONICAL_HEAD_REVISION,
) -> PullRequestRevisionRoleBinding:
    return PullRequestRevisionRoleBinding(
        pull_request=_pull_request(),
        role_assignment=RevisionRoleAssignment(role=role, revision=_commit(digest)),
    )


def _change_set() -> PullRequestChangeSet:
    return PullRequestChangeSet(
        base=_binding(RevisionRole.BASE, CANONICAL_BASE_REVISION),
        head=_binding(RevisionRole.HEAD, CANONICAL_HEAD_REVISION),
        changed_paths=(
            PullRequestChangedPath(
                path=GitRepositoryPath(CANONICAL_CHANGED_PATH),
                head_object=GitBlobIdentity(
                    kind=GitObjectKind.BLOB,
                    algorithm=GitHashAlgorithm.SHA1,
                    full_digest=CANONICAL_CHANGED_BLOB,
                ),
                status=ChangedPathStatus("modified"),
            ),
        ),
    )


def _record() -> DurableEvidenceRecordReference:
    return DurableEvidenceRecordReference(
        format_name=EvidenceRecordFormat(CANONICAL_RECORD_FORMAT),
        format_version=EvidenceVersion(CANONICAL_RECORD_VERSION),
        canonicalization=EvidenceCanonicalization(CANONICAL_RECORD_CANONICALIZATION),
        sha256=ArtifactSha256Digest(CANONICAL_RECORD_SHA256),
        byte_length=ArtifactByteLength(CANONICAL_RECORD_LENGTH),
    )


def _correction_record() -> DurableEvidenceRecordReference:
    return DurableEvidenceRecordReference(
        format_name=EvidenceRecordFormat(CANONICAL_CORRECTION_FORMAT),
        format_version=EvidenceVersion(CANONICAL_RECORD_VERSION),
        canonicalization=EvidenceCanonicalization(CANONICAL_RECORD_CANONICALIZATION),
        sha256=ArtifactSha256Digest(CANONICAL_CORRECTION_SHA256),
        byte_length=ArtifactByteLength(CANONICAL_CORRECTION_LENGTH),
    )


def _report(problem: str = PROBLEM) -> SuppliedFaultReport:
    return SuppliedFaultReport(
        report=FaultReportIdentity(REPORT),
        context=FaultRepositoryContext(
            fault=FaultInstanceIdentity(FAULT),
            repository=_repository(),
        ),
        problem_statement=problem,
        behavioral_deviation=DEVIATION,
    )


def _scenario(
    statement: str = "Only when the rewritten assertion is instrumented.",
) -> SuppliedFaultScenario:
    return SuppliedFaultScenario(
        scenario=FaultScenarioIdentity(SCENARIO),
        report=_report(),
        scenario_statement=statement,
    )


def _occurrence(
    statement: str = "Reported once by the caller on their own checkout.",
) -> SuppliedFaultOccurrenceContext:
    return SuppliedFaultOccurrenceContext(
        occurrence=FaultOccurrenceIdentity(OCCURRENCE),
        scenario=_scenario(),
        occurrence_context=statement,
    )


def _candidate(
    statement: str = "Evaluate the side-effecting expression once and reuse it.",
) -> SuppliedFaultRepairCandidate:
    return SuppliedFaultRepairCandidate(
        candidate=FaultRepairCandidateIdentity(CANDIDATE),
        report=_report(),
        repair_statement=statement,
    )


def _material(
    statement: str = "A regression test asserting the callback runs exactly once.",
) -> SuppliedFaultTestMaterial:
    return SuppliedFaultTestMaterial(
        material=FaultTestMaterialIdentity(MATERIAL),
        report=_report(),
        test_statement=statement,
    )


def _run(
    run: uuid.UUID = RUN,
    statement: str = "Reported as run from a local checkout by the caller.",
) -> ReportedFaultTestRun:
    return ReportedFaultTestRun(
        run=FaultTestRunIdentity(run),
        test_material=_material(),
        run_statement=statement,
    )


def _outcome(
    run: uuid.UUID = RUN,
    kind: ReportedFaultTestOutcomeKind = ReportedFaultTestOutcomeKind.FAILED,
    statement: str = "Reported as ending with the assertion the caller described.",
) -> ReportedFaultTestOutcome:
    return ReportedFaultTestOutcome(
        run=_run(run),
        outcome=kind,
        outcome_statement=statement,
    )


def _second_outcome() -> ReportedFaultTestOutcome:
    return _outcome(
        run=SECOND_RUN,
        kind=ReportedFaultTestOutcomeKind.PASSED,
        statement="Reported as ending without the assertion the caller described.",
    )


def _comparison(
    statement: str = "The caller reports the two supplied outcomes as comparable.",
) -> ReportedFaultTestComparison:
    return ReportedFaultTestComparison(
        before=_outcome(),
        after=_second_outcome(),
        comparison_statement=statement,
    )


def _explanation(
    statement: str = "The caller accounts for it by a second evaluation.",
) -> SuppliedFaultExplanation:
    return SuppliedFaultExplanation(
        explanation=FaultExplanationIdentity(EXPLANATION),
        report=_report(),
        explanation_statement=statement,
    )


def _hypothesis(
    statement: str = "The caller proposes, tentatively, a stale rewrite cache.",
) -> SuppliedFaultHypothesis:
    return SuppliedFaultHypothesis(
        hypothesis=FaultHypothesisIdentity(HYPOTHESIS),
        report=_report(),
        hypothesis_statement=statement,
    )


def _expected_property(
    statement: str = "For this report, evaluation count should be preserved.",
) -> SuppliedFaultExpectedProperty:
    return SuppliedFaultExpectedProperty(
        expected_property=FaultExpectedPropertyIdentity(PROPERTY),
        report=_report(),
        expected_property_statement=statement,
    )


def _history_association() -> FaultReportHistoryFactAssociation:
    return FaultReportHistoryFactAssociation(
        report=_report(),
        history_fact=_binding(),
    )


def _source_association() -> FaultReportSourceObjectAssociation:
    return FaultReportSourceObjectAssociation(
        report=_report(),
        source_object=_pull_request(),
    )


def _candidate_revision() -> FaultRepairCandidateRevisionAssociation:
    return FaultRepairCandidateRevisionAssociation(
        candidate=_candidate(),
        revision=_commit(),
    )


def _candidate_change_set() -> FaultRepairCandidateChangeSetAssociation:
    return FaultRepairCandidateChangeSetAssociation(
        candidate=_candidate(),
        change_set=_change_set(),
    )


def _run_revision() -> FaultTestRunRevisionAssociation:
    return FaultTestRunRevisionAssociation(run=_run(), revision=_commit())


def _minimal_instance() -> FaultInstance:
    """One identity and one report: the smallest published composition."""
    return FaultInstance(fault=FaultInstanceIdentity(FAULT), reports=(_report(),))


def _full_instance() -> FaultInstance:
    """One composition carrying every one of the eleven admitted categories."""
    return FaultInstance(
        fault=FaultInstanceIdentity(FAULT),
        reports=(_report(),),
        scenarios=(_scenario(),),
        occurrences=(_occurrence(),),
        repair_candidates=(_candidate(),),
        test_materials=(_material(),),
        test_runs=(_run(), _run(SECOND_RUN)),
        test_outcomes=(_outcome(), _second_outcome()),
        test_comparisons=(_comparison(),),
        explanations=(_explanation(),),
        hypotheses=(_hypothesis(),),
        expected_properties=(_expected_property(),),
    )


# A sentinel, so that `None` can itself be supplied to any position and be
# refused there rather than being read as "use the valid default".
_UNSET: Any = object()


def _link(
    subject: Any = _UNSET,
    instance: Any = _UNSET,
    record: Any = _UNSET,
) -> FaultInstanceEvidenceLink:
    return FaultInstanceEvidenceLink(
        fault_instance=_full_instance() if instance is _UNSET else instance,
        subject=_report() if subject is _UNSET else subject,
        evidence_record=_record() if record is _UNSET else record,
    )


def _payload(value: BaseModel) -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(value.model_dump_json()))


def _messages(error: ValidationError) -> str:
    return "\n".join(entry["msg"] for entry in error.errors())


def _link_tree() -> ast.Module:
    return ast.parse(LINK_SOURCE.read_text(encoding="utf-8"))


def _roadmap() -> str:
    return ROADMAP.read_text(encoding="utf-8")


class _Foreign(BaseModel):
    """A model that is not a published FaultAtlas value at all."""

    report: str = "not a published record"


class _AttributeLookalike:
    """An attribute-backed object shaped like a published value."""

    def __init__(self, source: BaseModel) -> None:
        for name, value in source.__dict__.items():
            setattr(self, name, value)


# Each admitted subject, the collection that must already carry it, and a
# same-identity record that differs somewhere else in its published content.
ADMITTED: tuple[tuple[str, BaseModel, str, BaseModel], ...] = (
    ("SuppliedFaultReport", _report(), "reports", _report(DIVERGENT_PROBLEM)),
    (
        "SuppliedFaultScenario",
        _scenario(),
        "scenarios",
        _scenario("A different supplied scenario statement."),
    ),
    (
        "SuppliedFaultOccurrenceContext",
        _occurrence(),
        "occurrences",
        _occurrence("A different supplied occurrence context."),
    ),
    (
        "SuppliedFaultRepairCandidate",
        _candidate(),
        "repair_candidates",
        _candidate("A different supplied repair statement."),
    ),
    (
        "SuppliedFaultTestMaterial",
        _material(),
        "test_materials",
        _material("A different supplied test statement."),
    ),
    (
        "ReportedFaultTestRun",
        _run(),
        "test_runs",
        _run(RUN, "A different reported run statement."),
    ),
    (
        "ReportedFaultTestOutcome",
        _outcome(),
        "test_outcomes",
        _outcome(RUN, ReportedFaultTestOutcomeKind.FAILED, "A different statement."),
    ),
    (
        "ReportedFaultTestComparison",
        _comparison(),
        "test_comparisons",
        _comparison("A different supplied comparison statement."),
    ),
    (
        "SuppliedFaultExplanation",
        _explanation(),
        "explanations",
        _explanation("A different supplied explanation statement."),
    ),
    (
        "SuppliedFaultHypothesis",
        _hypothesis(),
        "hypotheses",
        _hypothesis("A different supplied hypothesis statement."),
    ),
    (
        "SuppliedFaultExpectedProperty",
        _expected_property(),
        "expected_properties",
        _expected_property("A different supplied expected property."),
    ),
)

ADMITTED_IDS = tuple(name for name, _, _, _ in ADMITTED)


# --- the published surface ---------------------------------------------------


def test_the_module_publishes_exactly_one_symbol() -> None:
    assert link_module.__all__ == ["FaultInstanceEvidenceLink"]

    tree = _link_tree()
    assert [node.name for node in tree.body if isinstance(node, ast.ClassDef)] == [
        "FaultInstanceEvidenceLink"
    ]
    assert [
        node.name
        for node in tree.body
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)
    ] == []

    owned = {
        name
        for name, value in vars(link_module).items()
        if getattr(value, "__module__", None) == link_module.__name__
    }
    assert owned == {"FaultInstanceEvidenceLink"}


def test_the_module_assigns_no_public_name_beyond_its_published_symbol() -> None:
    """A helper, factory or registry would have to be assigned a public name."""
    assigned: set[str] = set()
    for node in _link_tree().body:
        if isinstance(node, ast.Assign):
            assigned.update(
                target.id for target in node.targets if isinstance(target, ast.Name)
            )
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            assigned.add(node.target.id)

    assert {name for name in assigned if not name.startswith("_")} == set()
    assert assigned == {
        "__all__",
        "_ADMITTED_SUBJECT_TYPES",
        "_AdmittedSubject",
        "_SUBJECT_COLLECTIONS",
    }


def test_the_link_publishes_no_attribute_of_its_own_beyond_the_model_base() -> None:
    """The class surface is pinned, not just the module's top level.

    "No link of this type is ever derived, inferred, computed or returned" is
    the load-bearing claim, and a method on the published class would derive
    one while every module-level oracle still passed. Nothing may stand on this
    class that `BaseModel` does not already provide.
    """
    published = {
        name for name in dir(FaultInstanceEvidenceLink) if not name.startswith("_")
    }

    assert published - set(dir(BaseModel)) == set()


def test_the_module_declares_exactly_its_four_published_validators() -> None:
    """A helper, factory or derivation would have to be a function somewhere."""
    declared = {
        node.name
        for node in ast.walk(_link_tree())
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)
    }

    assert declared == {
        "_require_typed_python_fault_instance",
        "_require_typed_python_subject",
        "_require_typed_python_evidence_record",
        "_require_subject_is_composed_member",
    }


def test_the_link_declares_exactly_three_fields_in_the_published_order() -> None:
    assert tuple(FaultInstanceEvidenceLink.model_fields) == EXPECTED_FIELDS


def test_the_link_declares_no_alias_and_no_computed_field() -> None:
    assert FaultInstanceEvidenceLink.model_computed_fields == {}
    for name, field in FaultInstanceEvidenceLink.model_fields.items():
        assert field.alias is None, name
        assert field.validation_alias is None, name
        assert field.serialization_alias is None, name


def test_the_link_declares_the_published_validation_policy() -> None:
    config = cast(dict[str, Any], FaultInstanceEvidenceLink.model_config)
    assert config["frozen"] is True
    assert config["extra"] == "forbid"
    assert config["strict"] is True
    assert config["revalidate_instances"] == "always"
    assert config["validate_default"] is True


def test_a_link_is_frozen_and_two_equal_links_are_equal_values() -> None:
    first = _link()
    second = _link()

    assert first == second
    assert hash(first) == hash(second)
    with pytest.raises(ValidationError):
        first.subject = _scenario()  # type: ignore[misc]


# --- the admitted boundary ---------------------------------------------------


def test_the_admitted_subject_union_is_exactly_the_eleven_published_records() -> None:
    admitted = typing.get_args(
        FaultInstanceEvidenceLink.model_fields["subject"].annotation
    )

    assert set(admitted) == {
        SuppliedFaultReport,
        SuppliedFaultScenario,
        SuppliedFaultOccurrenceContext,
        SuppliedFaultRepairCandidate,
        SuppliedFaultTestMaterial,
        ReportedFaultTestRun,
        ReportedFaultTestOutcome,
        ReportedFaultTestComparison,
        SuppliedFaultExplanation,
        SuppliedFaultHypothesis,
        SuppliedFaultExpectedProperty,
    }
    assert len(admitted) == 11


def test_every_admitted_type_is_mapped_to_one_composed_collection() -> None:
    """The dispatch is total, so no admitted subject can escape the check.

    The mapping is compared against the union itself rather than against a
    second hand-written list, so adding a member to one without the other
    fails here instead of silently skipping the membership rule.
    """
    admitted = set(
        typing.get_args(FaultInstanceEvidenceLink.model_fields["subject"].annotation)
    )

    assert set(SUBJECT_COLLECTIONS) == admitted
    assert set(ADMITTED_SUBJECT_TYPES) == admitted

    composed = set(FaultInstance.model_fields)
    for subject, collection in SUBJECT_COLLECTIONS.items():
        assert collection in composed, subject


def test_a_subclass_of_an_admitted_record_normalizes_to_the_published_type() -> None:
    """The membership dispatch reads an exact type, so this must hold.

    `revalidate_instances="always"` revalidates a subclass instance into the
    published type it declares, so the subject of a validated link is always
    exactly one of the eleven and the declared mapping can never miss.
    """

    class _SubclassedReport(SuppliedFaultReport):
        pass

    supplied = _SubclassedReport(
        **{name: getattr(_report(), name) for name in SuppliedFaultReport.model_fields}
    )
    assert isinstance(supplied, SuppliedFaultReport)
    assert type(supplied) is not SuppliedFaultReport

    link = _link(supplied)

    assert type(link.subject) is SuppliedFaultReport
    assert type(link.subject) in SUBJECT_COLLECTIONS
    assert link.subject == _report()


def test_the_five_association_collections_are_not_evidence_targets() -> None:
    """Association metadata is excluded, and this states it as a partition.

    `FaultInstance` publishes seventeen fields: one identity and sixteen
    collections. Eleven carry substantive records and are targets; the other
    five carry the caller-declared associations, which are relations about
    records rather than records, so no evidence attaches to them here.
    """
    collections = set(FaultInstance.model_fields) - {"fault"}
    targets = set(SUBJECT_COLLECTIONS.values())

    assert len(collections) == 16
    assert len(targets) == 11
    assert collections - targets == {
        "source_object_associations",
        "history_fact_associations",
        "repair_revision_associations",
        "repair_change_set_associations",
        "test_run_revision_associations",
    }


@pytest.mark.parametrize(
    ("subject", "collection"),
    [(subject, collection) for _, subject, collection, _ in ADMITTED],
    ids=ADMITTED_IDS,
)
def test_each_admitted_subject_links_when_it_is_composed(
    subject: Any, collection: str
) -> None:
    link = _link(subject)

    assert type(link.subject) is type(subject)
    assert link.subject == subject
    assert link.subject in getattr(link.fault_instance, collection)
    assert link.evidence_record == _record()


@pytest.mark.parametrize(
    "subject",
    [subject for _, subject, _, _ in ADMITTED],
    ids=ADMITTED_IDS,
)
def test_each_admitted_subject_round_trips_through_json_unchanged(
    subject: Any,
) -> None:
    """A union must not quietly reconstruct one admitted type as another."""
    link = _link(subject)
    restored = FaultInstanceEvidenceLink.model_validate_json(link.model_dump_json())

    assert type(restored.subject) is type(subject)
    assert restored.subject == subject
    assert restored == link
    assert _payload(restored) == _payload(link)


def test_no_admitted_payload_reconstructs_as_a_different_admitted_type() -> None:
    """Discrimination is asserted over every ordered pair, not spot-checked.

    Each admitted record declares its own field names and forbids extras, so a
    payload for one cannot satisfy another. This states that as a property of
    all eleven rather than trusting the union's member order.
    """
    reconstructed: dict[str, str] = {}
    for name, subject, _, _ in ADMITTED:
        payload = _payload(_link(subject))
        restored = FaultInstanceEvidenceLink.model_validate_json(json.dumps(payload))
        reconstructed[name] = type(restored.subject).__name__

    assert reconstructed == {name: name for name in ADMITTED_IDS}


@pytest.mark.parametrize(
    "subject",
    [subject for _, subject, _, _ in ADMITTED],
    ids=ADMITTED_IDS,
)
def test_a_raw_mapping_is_refused_in_every_admitted_subject_position(
    subject: Any,
) -> None:
    """A strict union still admits a mapping whose children are typed."""
    with pytest.raises(ValidationError) as error:
        _link(dict(subject.__dict__))

    assert "admitted published S1.P06 record in Python input" in _messages(error.value)


@pytest.mark.parametrize(
    "subject",
    [subject for _, subject, _, _ in ADMITTED],
    ids=ADMITTED_IDS,
)
def test_an_attribute_lookalike_is_refused_in_every_admitted_subject_position(
    subject: Any,
) -> None:
    with pytest.raises(ValidationError):
        FaultInstanceEvidenceLink.model_validate(
            {
                "fault_instance": _full_instance(),
                "subject": _AttributeLookalike(subject),
                "evidence_record": _record(),
            },
            from_attributes=True,
        )


# --- whole-record membership -------------------------------------------------


@pytest.mark.parametrize(
    ("subject", "collection"),
    [(subject, collection) for _, subject, collection, _ in ADMITTED],
    ids=ADMITTED_IDS,
)
def test_a_subject_the_composition_does_not_carry_is_refused(
    subject: Any, collection: str
) -> None:
    """Nothing is auto-inserted: the link is invalid, not the composition larger."""
    instance = _minimal_instance()
    if collection == "reports":
        instance = FaultInstance(
            fault=FaultInstanceIdentity(FAULT),
            reports=(_report(DIVERGENT_PROBLEM),),
        )

    with pytest.raises(ValidationError) as error:
        _link(subject, instance=instance)

    assert f"subject is not a member of fault_instance.{collection}" in _messages(
        error.value
    )
    assert getattr(instance, collection) == getattr(
        _minimal_instance() if collection != "reports" else instance, collection
    )


@pytest.mark.parametrize(
    ("subject", "collection", "divergent"),
    [
        (subject, collection, divergent)
        for _, subject, collection, divergent in ADMITTED
    ],
    ids=ADMITTED_IDS,
)
def test_a_same_identity_record_that_differs_anywhere_else_is_refused(
    subject: Any, collection: str, divergent: Any
) -> None:
    """Membership is by whole published record, never by a matching scalar.

    Each divergent record below carries the identity its composed counterpart
    carries -- the same report, scenario, occurrence, candidate, material or
    run subject, or for the two records that publish no identity of their own
    the same referenced run and outcomes -- and differs only in supplied
    content. Matching the embedded identifier would associate evidence with a
    record the caller never supplied.
    """
    composed = _full_instance()
    assert subject in getattr(composed, collection)
    assert divergent not in getattr(composed, collection)

    with pytest.raises(ValidationError) as error:
        _link(divergent, instance=composed)

    assert f"subject is not a member of fault_instance.{collection}" in _messages(
        error.value
    )


def test_the_supplied_composition_is_never_mutated_or_reconstructed() -> None:
    composed = _full_instance()
    before = _payload(composed)

    link = _link(_scenario(), instance=composed)

    assert _payload(composed) == before
    assert link.fault_instance == composed
    assert len(link.fault_instance.scenarios) == 1
    with pytest.raises(ValidationError):
        _link(_scenario("A statement this composition does not carry."))


def test_membership_is_decided_against_the_declared_collection_only() -> None:
    """A subject present in the composition but under no admitted collection.

    The five association collections are composed here and carry records, but
    none is an admitted subject, so composing them changes no answer.
    """
    composed = FaultInstance(
        fault=FaultInstanceIdentity(FAULT),
        reports=(_report(),),
        scenarios=(_scenario(),),
        source_object_associations=(_source_association(),),
        history_fact_associations=(_history_association(),),
        repair_candidates=(_candidate(),),
        repair_revision_associations=(_candidate_revision(),),
        repair_change_set_associations=(_candidate_change_set(),),
        test_materials=(_material(),),
        test_runs=(_run(),),
        test_run_revision_associations=(_run_revision(),),
    )

    assert _link(_scenario(), instance=composed).subject == _scenario()
    for excluded in (
        _source_association(),
        _history_association(),
        _candidate_revision(),
        _candidate_change_set(),
        _run_revision(),
    ):
        with pytest.raises(ValidationError) as error:
            _link(excluded, instance=composed)
        assert "admitted published S1.P06 record in Python input" in _messages(
            error.value
        )


# --- explicit exclusions -----------------------------------------------------


def test_the_composition_itself_and_its_identity_are_refused_as_subjects() -> None:
    """Evidence attaches to a record, never to the act of composing one."""
    for excluded in (_full_instance(), FaultInstanceIdentity(FAULT)):
        with pytest.raises(ValidationError) as error:
            _link(excluded)
        assert "admitted published S1.P06 record in Python input" in _messages(
            error.value
        )


def test_every_identity_and_scalar_is_refused_as_a_subject() -> None:
    for excluded in (
        FaultReportIdentity(REPORT),
        FaultScenarioIdentity(SCENARIO),
        FaultRepairCandidateIdentity(CANDIDATE),
        FaultTestRunIdentity(RUN),
        FaultInstanceIdentity(FAULT),
        REPORT,
        REPORT_TEXT,
        None,
        42,
    ):
        with pytest.raises(ValidationError):
            _link(excluded)


def test_the_five_association_record_types_are_refused_as_subjects() -> None:
    for excluded in (
        _source_association(),
        _history_association(),
        _candidate_revision(),
        _candidate_change_set(),
        _run_revision(),
    ):
        with pytest.raises(ValidationError) as error:
            _link(excluded)
        assert "admitted published S1.P06 record in Python input" in _messages(
            error.value
        )


def test_the_published_evidence_link_types_are_refused_as_subjects() -> None:
    """Each remains the authority for its own domain; none nests in another."""
    history_link = PullRequestHistoryFactEvidenceLink(
        fact=_binding(), evidence_record=_record()
    )
    snapshot_link = RepositorySnapshotFactEvidenceLink(
        fact=RepositorySnapshotRootTreeBinding(
            snapshot=RepositorySnapshotIdentity(
                repository=_repository(), revision=_commit()
            ),
            root_tree=GitTreeIdentity(
                kind=GitObjectKind.TREE,
                algorithm=GitHashAlgorithm.SHA1,
                full_digest=CANONICAL_ROOT_TREE,
            ),
        ),
        evidence_record=_record(),
    )

    for excluded in (history_link, snapshot_link, _link()):
        with pytest.raises(ValidationError) as error:
            _link(excluded)
        assert "admitted published S1.P06 record in Python input" in _messages(
            error.value
        )


def test_aggregate_and_foreign_values_are_refused_as_subjects() -> None:
    for excluded in (
        _change_set(),
        _pull_request(),
        _commit(),
        _repository(),
        _Foreign(),
        _record(),
    ):
        with pytest.raises(ValidationError) as error:
            _link(excluded)
        assert "admitted published S1.P06 record in Python input" in _messages(
            error.value
        )


# --- the composition position ------------------------------------------------


def test_the_composition_position_requires_a_published_aggregate() -> None:
    for excluded in (
        dict(_full_instance().__dict__),
        _payload(_full_instance()),
        _report(),
        FaultInstanceIdentity(FAULT),
        FAULT_TEXT,
        None,
    ):
        with pytest.raises(ValidationError) as error:
            _link(instance=excluded)
        assert "fault_instance must be a FaultInstance in Python input" in _messages(
            error.value
        )


def test_an_attribute_lookalike_composition_is_refused() -> None:
    with pytest.raises(ValidationError) as error:
        FaultInstanceEvidenceLink.model_validate(
            {
                "fault_instance": _AttributeLookalike(_full_instance()),
                "subject": _report(),
                "evidence_record": _record(),
            },
            from_attributes=True,
        )

    assert "fault_instance must be a FaultInstance in Python input" in _messages(
        error.value
    )


def test_the_composition_reconstructs_from_json_through_its_own_grammar() -> None:
    """Delegating decides nothing: every published rule still applies.

    The aggregate refuses a reference to a record it does not carry, and that
    refusal must survive reconstruction here rather than being relaxed by
    passing through this module.
    """
    payload = _payload(_link(_scenario()))
    restored = FaultInstanceEvidenceLink.model_validate_json(json.dumps(payload))
    assert restored.fault_instance == _full_instance()

    dangling = _payload(_link(_scenario()))
    composition = cast(dict[str, Any], dangling["fault_instance"])
    composition["scenarios"] = []

    with pytest.raises(ValidationError):
        FaultInstanceEvidenceLink.model_validate_json(json.dumps(dangling))


def test_a_typed_composition_reaching_json_input_is_validated_not_encoded() -> None:
    """A mode reports the input language, not one value's provenance.

    A published link standing as a validated default on a consumer model is
    handed to the composition guard as a typed value while the ambient language
    is JSON. It must be validated as the published value it already is, not
    handed to an encoder that cannot represent it.
    """
    supplied = _link()

    class _Holder(BaseModel):
        model_config = ConfigDict(validate_default=True)

        link: FaultInstanceEvidenceLink = supplied

    assert _Holder.model_validate_json("{}").link == supplied
    assert _Holder.model_validate({}).link == supplied


def test_string_input_refuses_a_value_with_no_published_form() -> None:
    """String input is a third input language, not parsed JSON.

    Its values are ordinary Python objects, so the composition position may be
    handed something no encoder can represent. That must be refused as one more
    invalid input rather than escaping as an error a caller catching a
    validation failure would never see.
    """

    class _NotEncodable:
        pass

    for value in (_NotEncodable(), object(), {1, 2}, b"bytes", uuid.uuid4()):
        with pytest.raises(ValidationError):
            FaultInstanceEvidenceLink.model_validate_strings(
                {
                    "fault_instance": {"fault": value},
                    "subject": _payload(_report()),
                    "evidence_record": _payload(_record()),
                }
            )


def test_a_json_mapping_with_no_durable_form_is_refused_not_raised_through() -> None:
    """The decoded position is reachable with a mapping JSON cannot represent.

    A consumer's own guard may materialize a mapping while the ambient language
    is JSON, so the mapping the composition guard decodes is not always one a
    parser produced.
    """
    hostile: dict[str, Any] = {"fault": object()}

    class _Materializes(BaseModel):
        link: FaultInstanceEvidenceLink

        @field_validator("link", mode="before")
        @classmethod
        def _supply(cls, value: object) -> object:
            return {
                "fault_instance": hostile,
                "subject": _payload(_report()),
                "evidence_record": _payload(_record()),
            }

    with pytest.raises(ValidationError) as error:
        _Materializes.model_validate_json('{"link": {}}')

    assert "fault_instance must be a durable composition in JSON input" in _messages(
        error.value
    )


def test_a_python_dump_of_a_link_does_not_revalidate() -> None:
    """The projection has already turned typed children into mappings."""
    with pytest.raises(ValidationError):
        FaultInstanceEvidenceLink.model_validate(_link().model_dump())


# --- the evidence position ---------------------------------------------------


def test_the_evidence_position_accepts_one_published_durable_reference() -> None:
    link = _link(record=_record())

    assert link.evidence_record == _record()
    assert link.evidence_record.sha256 == ArtifactSha256Digest(CANONICAL_RECORD_SHA256)
    assert link.evidence_record.byte_length == ArtifactByteLength(
        CANONICAL_RECORD_LENGTH
    )


def test_a_raw_mapping_is_refused_in_the_evidence_position() -> None:
    with pytest.raises(ValidationError) as error:
        _link(record=dict(_record().__dict__))

    assert (
        "evidence_record must be a DurableEvidenceRecordReference in Python input"
        in _messages(error.value)
    )


def test_an_attribute_lookalike_is_refused_in_the_evidence_position() -> None:
    with pytest.raises(ValidationError) as error:
        FaultInstanceEvidenceLink.model_validate(
            {
                "fault_instance": _full_instance(),
                "subject": _report(),
                "evidence_record": _AttributeLookalike(_record()),
            },
            from_attributes=True,
        )

    assert (
        "evidence_record must be a DurableEvidenceRecordReference in Python input"
        in _messages(error.value)
    )


def test_a_foreign_value_is_refused_in_the_evidence_position() -> None:
    for excluded in (_Foreign(), CANONICAL_RECORD_SHA256, None, _report()):
        with pytest.raises(ValidationError):
            _link(record=excluded)


def test_a_malformed_evidence_payload_is_refused_in_json() -> None:
    payload = _payload(_link())
    record = cast(dict[str, Any], payload["evidence_record"])
    record["sha256"] = "not a digest"

    with pytest.raises(ValidationError):
        FaultInstanceEvidenceLink.model_validate_json(json.dumps(payload))


def test_the_evidence_reference_round_trips_through_json_exactly() -> None:
    link = _link()
    restored = FaultInstanceEvidenceLink.model_validate_json(link.model_dump_json())

    assert restored.evidence_record == _record()
    assert _payload(restored)["evidence_record"] == _payload(_record())


def test_the_link_states_nothing_about_where_inside_the_record_to_look() -> None:
    published = set(FaultInstanceEvidenceLink.model_fields) | set(
        DurableEvidenceRecordReference.model_fields
    )

    assert not published & {
        "artifact_path",
        "byte_span",
        "evidence_id",
        "evidence_kind",
        "field_pointer",
        "json_pointer",
        "locator",
        "offset",
        "request_id",
        "semantic_path",
    }


# --- multiplicity ------------------------------------------------------------


def test_one_subject_may_name_several_records_and_one_record_many_subjects() -> None:
    """Several links are several values. Nothing collects, orders or dedupes."""
    first = _link(_report(), record=_record())
    second = _link(_report(), record=_correction_record())

    assert first != second
    assert first.subject == second.subject

    across = tuple(_link(subject) for _, subject, _, _ in ADMITTED)
    assert all(link.evidence_record == _record() for link in across)
    assert len({type(link.subject) for link in across}) == 11
    assert len({link.model_dump_json() for link in across}) == 11

    assert _link() == _link()
    assert _link().model_dump_json() == _link().model_dump_json()


# --- no transitive inference -------------------------------------------------


def test_a_history_evidence_chain_manufactures_no_fault_evidence_link() -> None:
    """The load-bearing boundary, built as the chain that would tempt it.

    A report is associated with a retained history fact, and that same fact is
    associated with a retained durable record. Nothing here derives, computes,
    caches or returns a link from the report to that record: the composition
    exposes no such value, and the only way to obtain one is for a caller to
    construct it deliberately.
    """
    fact = _binding()
    record = _record()
    association = _history_association()
    fact_to_record = PullRequestHistoryFactEvidenceLink(
        fact=fact, evidence_record=record
    )

    composed = FaultInstance(
        fault=FaultInstanceIdentity(FAULT),
        reports=(_report(),),
        history_fact_associations=(association,),
    )

    assert association.history_fact == fact
    assert fact_to_record.fact == fact
    assert fact_to_record.evidence_record == record

    # The chain is complete, and the composition still exposes nothing of this
    # module's type anywhere inside it.
    assert not any(
        isinstance(value, FaultInstanceEvidenceLink) for value in _walk(composed)
    )
    assert not any(
        isinstance(value, FaultInstanceEvidenceLink) for value in _walk(fact_to_record)
    )
    assert "evidence" not in set(FaultInstance.model_fields)

    # Only an explicit construction produces one, and it is a separate value.
    explicit = FaultInstanceEvidenceLink(
        fault_instance=composed,
        subject=_report(),
        evidence_record=record,
    )
    assert explicit.subject == _report()
    assert explicit.evidence_record == record
    assert explicit.fault_instance == composed


def test_a_change_set_chain_manufactures_no_fault_evidence_link() -> None:
    """report -> pull request, candidate -> change set from it, still nothing."""
    composed = FaultInstance(
        fault=FaultInstanceIdentity(FAULT),
        reports=(_report(),),
        source_object_associations=(_source_association(),),
        repair_candidates=(_candidate(),),
        repair_change_set_associations=(_candidate_change_set(),),
    )

    assert _source_association().source_object == _pull_request()
    assert _candidate_change_set().change_set.head.pull_request == _pull_request()
    assert not any(
        isinstance(value, FaultInstanceEvidenceLink) for value in _walk(composed)
    )

    with pytest.raises(ValidationError):
        _link(_candidate_change_set(), instance=composed)


def test_a_link_to_one_record_says_nothing_about_a_second_record() -> None:
    """A correction is associated only when a caller supplies it."""
    to_record = _link(_report(), record=_record())
    to_correction = _link(_report(), record=_correction_record())

    assert to_record.evidence_record != to_correction.evidence_record
    assert to_record != to_correction
    assert not any(
        isinstance(value, DurableEvidenceRecordReference)
        and value == _correction_record()
        for value in _walk(to_record)
    )


def _walk(value: object) -> list[object]:
    """Every value reachable from a published model, by declared field."""
    seen: list[object] = []
    stack: list[object] = [value]
    while stack:
        current = stack.pop()
        seen.append(current)
        if isinstance(current, BaseModel):
            stack.extend(cast(dict[str, object], current.__dict__).values())
        elif isinstance(current, tuple):
            stack.extend(cast(tuple[object, ...], current))
    return seen


# --- non-claims --------------------------------------------------------------


def test_the_module_names_no_support_proof_or_review_identifier() -> None:
    tree = _link_tree()
    identifiers = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)} | {
        node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute)
    }
    identifiers |= {
        node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)
    }
    identifiers |= {
        node.name
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)
    }
    identifiers |= {
        node.target.id
        for node in ast.walk(tree)
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name)
    }

    for forbidden in FORBIDDEN_IDENTIFIERS:
        assert forbidden not in identifiers, forbidden


def test_the_published_link_exposes_no_support_or_confidence_surface() -> None:
    published = set(FaultInstanceEvidenceLink.model_fields) | set(
        FaultInstanceEvidenceLink.model_computed_fields
    )

    assert published == set(EXPECTED_FIELDS)
    for forbidden in FORBIDDEN_IDENTIFIERS:
        assert forbidden not in published
        assert not hasattr(FaultInstanceEvidenceLink, forbidden), forbidden

    schema = json.dumps(FaultInstanceEvidenceLink.model_json_schema())
    for forbidden in ("supports", "proves", "verifies", "confidence", "corroborates"):
        assert f'"{forbidden}"' not in schema


def test_the_link_adds_no_field_to_any_admitted_record() -> None:
    """Every admitted type is reused whole and unchanged."""
    for _, subject, _, _ in ADMITTED:
        restored = FaultInstanceEvidenceLink.model_validate_json(
            _link(subject).model_dump_json()
        ).subject
        assert set(restored.__dict__) == set(type(subject).model_fields)
        assert restored.model_dump_json() == subject.model_dump_json()


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
    `json.os.environ`, `getattr(json, "os")`, `__import__`, a `Path`, a
    `datetime` -- fails for being absent from it rather than for having been
    predicted.
    """
    tree = _link_tree()

    assert {
        node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute)
    } == EXPECTED_ATTRIBUTE_VOCABULARY
    assert {
        node.id for node in ast.walk(tree) if isinstance(node, ast.Name)
    } == EXPECTED_NAME_VOCABULARY


def test_the_one_dynamic_attribute_read_is_bounded_to_composed_collections() -> None:
    """`getattr` is reached with a variable, so the pin above cannot bound it.

    The only value it can receive is a member of the published mapping, and
    every one of those is a declared `FaultInstance` field name.
    """
    assert set(SUBJECT_COLLECTIONS.values()) <= set(FaultInstance.model_fields)
    assert all(isinstance(name, str) for name in SUBJECT_COLLECTIONS.values())
    assert len(set(SUBJECT_COLLECTIONS.values())) == 11


def test_the_module_reaches_no_module_through_a_dynamic_chain() -> None:
    """This closes what the attribute and name pins structurally cannot.

    Those two pins read `ast.Attribute.attr` and `ast.Name.id`. A chain built
    from `getattr` with string arguments and from subscripts introduces
    neither: `getattr(getattr(json, "codecs"), "sys").modules["os"].environ`
    spells every step as an `ast.Constant` or an `ast.Subscript`, so a clock,
    environment or filesystem read could reach through a module the contract
    does admit while both pins stayed satisfied.

    So the two dynamic constructs are bounded here by shape rather than by
    spelling. Exactly one `getattr` call exists, its object is the supplied
    composition and its name is the mapping-bound local rather than any
    literal; and every subscript is a declared annotation or the mapping
    lookup, so no module registry can be indexed at all.
    """
    tree = _link_tree()

    dynamic = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "getattr"
    ]
    assert len(dynamic) == 1
    (call,) = dynamic
    assert not call.keywords
    assert len(call.args) == 2
    assert isinstance(call.args[0], ast.Attribute)
    assert call.args[0].attr == "fault_instance"
    assert isinstance(call.args[1], ast.Name)
    assert call.args[1].id == "collection"

    subscripted = [
        node.value for node in ast.walk(tree) if isinstance(node, ast.Subscript)
    ]
    assert all(isinstance(node, ast.Name) for node in subscripted)
    assert {node.id for node in subscripted if isinstance(node, ast.Name)} == {
        "dict",
        "tuple",
        "type",
        "_SUBJECT_COLLECTIONS",
    }


def test_no_annotation_in_the_module_is_written_as_a_string() -> None:
    """A string annotation is source every pin above is structurally blind to.

    Those pins read node kinds: names, attributes, subscripts, calls and
    imports. An annotation written as a string is one `ast.Constant`, so it
    introduces none of them -- and the model machinery still compiles and
    evaluates it in this module's globals while the class is built, which
    happens at import. `"Annotated[_AdmittedSubject, __import__('os').environ]"`
    would read the environment with every other assertion here satisfied.

    Screening for the next construct that can carry hidden source is the losing
    shape, because whichever one is left off the list is the one that gets
    through. So this asserts the property instead: every annotation this module
    writes is a real expression, which hands all of them back to the vocabulary
    pins that already exist rather than adding a ninth place to look. The exact
    import set asserted below closes the other half, since deferring every
    annotation at once would have to import `__future__`.
    """
    annotations: list[ast.expr] = []
    for node in ast.walk(_link_tree()):
        if isinstance(node, ast.AnnAssign):
            annotations.append(node.annotation)
        elif isinstance(node, ast.arg) and node.annotation is not None:
            annotations.append(node.annotation)
        elif (
            isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)
            and node.returns is not None
        ):
            annotations.append(node.returns)

    assert annotations
    for annotation in annotations:
        for node in ast.walk(annotation):
            assert not (
                isinstance(node, ast.Constant) and isinstance(node.value, str)
            ), ast.unparse(annotation)


def test_the_module_calls_no_builtin_that_reaches_outside_itself() -> None:
    called = {
        node.func.id
        for node in ast.walk(_link_tree())
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }

    assert not called & {"open", "eval", "exec", "compile", "__import__", "print"}


def test_the_module_imports_exactly_its_published_dependencies() -> None:
    imported = {
        node.module
        for node in ast.walk(_link_tree())
        if isinstance(node, ast.ImportFrom) and node.module
    } | {
        alias.name
        for node in ast.walk(_link_tree())
        if isinstance(node, ast.Import)
        for alias in node.names
    }

    assert imported == {
        "json",
        "typing",
        "pydantic",
        "faultatlas.domain.evidence",
        "faultatlas.domain.fault",
        "faultatlas.domain.fault_instance",
        "faultatlas.domain.fault_interpretation",
        "faultatlas.domain.fault_repair",
        "faultatlas.domain.fault_test",
    }
    assert "os" not in imported
    assert "faultatlas.domain.fault_source_relationship" not in imported
    assert "faultatlas.domain.history_evidence_link" not in imported
    assert "faultatlas.domain.snapshot_evidence_link" not in imported


# --- the canonical vertical --------------------------------------------------


def test_the_canonical_vertical_keeps_five_layers_distinct() -> None:
    """One bounded vertical over the retained pytest #4412 / #4414 case.

    Five values are built, and each is a different kind of claim. Reading them
    as one "evidence-derived fault" is exactly the flattening this Slice
    refuses, so every layer is asserted to stay its own value.

    Layer 1 is a retained normalized observation: pull request #4414 of
    repository 37489525 binds a head revision. FaultAtlas retained it.

    Layer 2 is a caller-supplied fault claim about that repository. No retained
    record asserts it, and the fault UUID is invented here because the case
    supplies none.

    Layer 3 associates the caller's report with the retained observation. It
    is the caller's association, not a provider fact, and it does not say the
    pull request caused, fixed, or reported the fault.

    Layer 4 associates that retained observation with the retained acquisition
    record it came from. It says the caller associated them, nothing more.

    Layer 5 associates the caller's report with that same retained record. It
    is constructed explicitly below and is not implied by layers 3 and 4.
    """
    retained_observation = _binding()
    caller_report = _report()
    report_to_history = FaultReportHistoryFactAssociation(
        report=caller_report, history_fact=retained_observation
    )
    history_to_record = PullRequestHistoryFactEvidenceLink(
        fact=retained_observation, evidence_record=_record()
    )
    composed = FaultInstance(
        fault=FaultInstanceIdentity(FAULT),
        reports=(caller_report,),
        history_fact_associations=(report_to_history,),
    )
    fault_to_record = FaultInstanceEvidenceLink(
        fault_instance=composed,
        subject=caller_report,
        evidence_record=_record(),
    )

    layers = (
        retained_observation,
        caller_report,
        report_to_history,
        history_to_record,
        fault_to_record,
    )
    assert len({type(layer) for layer in layers}) == 5

    # The retained observation names real retained provenance.
    assert retained_observation.pull_request.repository_scoped_number == (
        RepositoryScopedNumber(CANONICAL_PULL_REQUEST_NUMBER)
    )
    assert retained_observation.role_assignment.revision == _commit()

    # The retained record is named whole, by its own retained digest and size.
    assert history_to_record.evidence_record == _record()
    assert fault_to_record.evidence_record == _record()
    assert history_to_record.evidence_record.sha256 == ArtifactSha256Digest(
        CANONICAL_RECORD_SHA256
    )

    # Layer 5 is not layer 4, and neither contains the other.
    assert not isinstance(fault_to_record, PullRequestHistoryFactEvidenceLink)
    assert history_to_record not in _walk(fault_to_record)
    assert fault_to_record not in _walk(history_to_record)
    assert fault_to_record.subject == caller_report
    assert history_to_record.fact == retained_observation


def test_the_canonical_vertical_promotes_no_supplied_claim_to_fact() -> None:
    """The hypothesis stays a hypothesis and the pairing stays a caller claim."""
    hypothesis = _hypothesis()
    composed = FaultInstance(
        fault=FaultInstanceIdentity(FAULT),
        reports=(_report(),),
        history_fact_associations=(_history_association(),),
        hypotheses=(hypothesis,),
    )
    link = FaultInstanceEvidenceLink(
        fault_instance=composed,
        subject=hypothesis,
        evidence_record=_record(),
    )

    # Associating a record with the hypothesis leaves it a supplied hypothesis.
    assert type(link.subject) is SuppliedFaultHypothesis
    assert link.subject == hypothesis
    assert "tentatively" in hypothesis.hypothesis_statement
    assert set(type(link.subject).model_fields) == {
        "hypothesis",
        "report",
        "hypothesis_statement",
    }

    # Nothing anywhere records that the record confirmed it.
    for forbidden in FORBIDDEN_IDENTIFIERS:
        assert forbidden not in set(FaultInstanceEvidenceLink.model_fields)
        assert forbidden not in set(SuppliedFaultHypothesis.model_fields)

    # The pairing of the retained issue's case with pull request #4414 is only
    # ever a supplied association, never a provider fact this module derives.
    assert _history_association().history_fact == _binding()
    assert not any(
        isinstance(value, PullRequestHistoryFactEvidenceLink)
        for value in _walk(composed)
    )


def test_the_canonical_vertical_claims_no_execution_of_the_analyzed_repository() -> (
    None
):
    """A reported run is a caller's report, not something FaultAtlas ran."""
    composed = _full_instance()
    link = _link(_outcome(), instance=composed)

    assert type(link.subject) is ReportedFaultTestOutcome
    assert link.subject.outcome_statement.startswith("Reported as")
    assert link.subject.run.run_statement.startswith("Reported as")
    assert set(ReportedFaultTestOutcome.model_fields) == {
        "run",
        "outcome",
        "outcome_statement",
    }
    assert "executed" not in set(ReportedFaultTestOutcome.model_fields)


def test_the_canonical_vertical_round_trips_through_json() -> None:
    composed = FaultInstance(
        fault=FaultInstanceIdentity(FAULT),
        reports=(_report(),),
        history_fact_associations=(_history_association(),),
    )
    link = FaultInstanceEvidenceLink(
        fault_instance=composed,
        subject=_report(),
        evidence_record=_record(),
    )

    restored = FaultInstanceEvidenceLink.model_validate_json(link.model_dump_json())

    assert restored == link
    assert restored.fault_instance.history_fact_associations == (
        _history_association(),
    )
    assert type(restored.subject) is SuppliedFaultReport


# --- the module performs no I/O ----------------------------------------------


NO_IO_PROBE = """
import json
import os
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
CHECKOUT_SOURCE_ROOT = os.environ["CHECKOUT_SOURCE_ROOT"]
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

import faultatlas.domain.fault_evidence_link as module
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
from faultatlas.domain.fault_instance import FaultInstance
from faultatlas.domain.identity import (
    ProviderKey,
    ProviderRepositoryId,
    RepositoryIdentity,
)

import_violations = list(violations)
violations.clear()
allowed = USE_PHASE_ALLOWED

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
    problem_statement="probe problem",
    behavioral_deviation="probe deviation",
)
instance = FaultInstance(fault=fault, reports=(report,))
record = DurableEvidenceRecordReference(
    format_name=EvidenceRecordFormat(os.environ["RECORD_FORMAT"]),
    format_version=EvidenceVersion(os.environ["RECORD_VERSION"]),
    canonicalization=EvidenceCanonicalization(os.environ["RECORD_CANONICALIZATION"]),
    sha256=ArtifactSha256Digest(os.environ["RECORD_SHA256"]),
    byte_length=ArtifactByteLength(int(os.environ["RECORD_LENGTH"])),
)

link = module.FaultInstanceEvidenceLink(
    fault_instance=instance, subject=report, evidence_record=record
)
assert module.FaultInstanceEvidenceLink.model_validate_json(
    link.model_dump_json()
) == link
module.FaultInstanceEvidenceLink.model_validate(link)
module.FaultInstanceEvidenceLink.model_json_schema()
try:
    module.FaultInstanceEvidenceLink.model_validate(link.model_dump())
except Exception:
    pass
try:
    module.FaultInstanceEvidenceLink(
        fault_instance=instance, subject=report, evidence_record={}
    )
except Exception:
    pass

recording = False
print(
    json.dumps(
        {
            "import_violations": sorted(set(import_violations)),
            "use_violations": sorted(set(violations)),
            "opened": opened,
            "all": module.__all__,
        }
    )
)
"""


def test_the_module_starts_no_process_and_touches_no_file() -> None:
    """The closure is asserted as a property, not as a list of spellings.

    An audit hook is installed before the module is imported, in an isolated
    interpreter so it cannot contaminate any other test, and importing it,
    building a link, revalidating, serializing, reconstructing from JSON,
    refusing a Python dump, refusing an untyped record and building the JSON
    schema must raise nothing outside the interpreter's own machinery.
    """
    environment = os.environ.copy()
    environment.pop("PYTHONPATH", None)
    environment.update(
        {
            "CHECKOUT_SOURCE_ROOT": str(CHECKOUT_SOURCE_ROOT),
            "FAULT_UUID": FAULT_TEXT,
            "REPORT_UUID": REPORT_TEXT,
            "REPOSITORY_ID": CANONICAL_REPOSITORY_ID,
            "RECORD_FORMAT": CANONICAL_RECORD_FORMAT,
            "RECORD_VERSION": CANONICAL_RECORD_VERSION,
            "RECORD_CANONICALIZATION": CANONICAL_RECORD_CANONICALIZATION,
            "RECORD_SHA256": CANONICAL_RECORD_SHA256,
            "RECORD_LENGTH": str(CANONICAL_RECORD_LENGTH),
            "PYTHONDONTWRITEBYTECODE": "1",
        }
    )
    result = subprocess.run(
        [sys.executable, "-I", "-B", "-c", NO_IO_PROBE],
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
    assert reported["all"] == ["FaultInstanceEvidenceLink"]


# --- the roadmap transition --------------------------------------------------


def test_the_roadmap_records_the_p06_s09_transition() -> None:
    roadmap = _roadmap()
    mapping = roadmap.split("## Current-code mapping", 1)
    assert len(mapping) == 2, "roadmap must retain a current-code mapping section"
    current = mapping[1]

    assert "`S1.P06.S09` is complete" in roadmap
    assert "`S1.P06.S10` is complete" in roadmap
    assert "`S1.P06.S11` is complete" in roadmap
    assert "`S1.P06.S12` is complete" in roadmap
    current_status = roadmap.split("## Current status", 1)[1].split("## ", 1)[0]
    assert "`S1.P07.S04` is next and not started" in current_status
    assert (
        "`S1.P06.S09` — Fault-evidence bridge and canonical vertical (complete)"
        in roadmap
    )
    assert "The `S1.P06` route is closed at `S1.P06.S12`." in roadmap

    assert "faultatlas.domain.fault_evidence_link" in current
    assert "`FaultInstanceEvidenceLink`" in current
    # Twenty-three since `S1.P07.S03` added the independent invariant module.
    assert "Production Python sources are 23." in current

    assert "`S1.P06.S09` is next and not started" not in roadmap
    assert "`S1.P07` is complete" not in roadmap
    assert "Production Python sources are 19." not in roadmap


def test_the_roadmap_states_the_s09_decisions_and_non_claims() -> None:
    roadmap = _roadmap()

    for statement in (
        "production Python sources move from 19 to 20",
        "eleven substantive",
        "already be an exact member",
        "whole published record",
        "referenced as one whole durable record",
        "No association chaining exists",
        "`FaultInstance` is unchanged",
        "same weak association",
        "remains `S1.P09` work",
        "`S1.P06.S10`",
    ):
        assert statement in roadmap, statement


def test_the_roadmap_preserves_the_predecessor_history_as_written() -> None:
    roadmap = _roadmap()

    assert "production Python sources move from 18 to 19" in roadmap
    assert "`S1.P06.S07.C01` correction" in roadmap
    assert "`S1.P05` is complete" in roadmap
    assert "`S1.P06` is complete" in roadmap


def test_the_roadmap_leaves_later_ownership_where_it_was() -> None:
    roadmap = _roadmap()

    assert "`S1.P06.S11` — Accumulated contract corpus (complete)" in roadmap
    assert "`S1.P06.S12` — Integration and Phase closure (complete)" in roadmap
    assert "`S1.P08` through `S1.P10` remain not started" in roadmap


# --- packaging and an isolated installed-wheel smoke -------------------------


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
    # Added by `S1.P07.S03`, the independent invariant proposition.
    "faultatlas/domain/invariant.py",
    # Added by `S1.P07.S01`, the first `S1.P07` production module.
    "faultatlas/domain/pattern.py",
    # Added by `S1.P07.S02`, the explicit pattern-exemplar designation.
    "faultatlas/domain/pattern_exemplar.py",
    "faultatlas/domain/revision.py",
    "faultatlas/domain/snapshot.py",
    "faultatlas/domain/snapshot_evidence_link.py",
    "faultatlas/domain/source.py",
]


def test_the_checkout_carries_exactly_twenty_three_production_modules() -> None:
    observed = sorted(
        str(path.relative_to(CHECKOUT_SOURCE_ROOT))
        for path in CHECKOUT_SOURCE_ROOT.rglob("*.py")
    )

    assert observed == EXPECTED_PRODUCTION_MODULES
    # Twenty-three since `S1.P07.S03` added the independent invariant module.
    assert len(observed) == 23
    assert "faultatlas/domain/fault_evidence_link.py" in observed
    assert "faultatlas/domain/pattern.py" in observed


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

import faultatlas.domain.fault_evidence_link as link_module
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
    SuppliedFaultScenario,
    FaultScenarioIdentity,
)
from faultatlas.domain.fault_evidence_link import FaultInstanceEvidenceLink
from faultatlas.domain.fault_instance import FaultInstance
from faultatlas.domain.identity import (
    ProviderKey,
    ProviderRepositoryId,
    RepositoryIdentity,
)

module = Path(link_module.__file__).resolve()
assert module.is_relative_to(installed), module
assert not module.is_relative_to(checkout), module
assert link_module.__all__ == ["FaultInstanceEvidenceLink"]

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
scenario = SuppliedFaultScenario(
    scenario=FaultScenarioIdentity(uuid.UUID(os.environ["SCENARIO_UUID"])),
    report=report,
    scenario_statement="probe scenario",
)
instance = FaultInstance(fault=fault, reports=(report,), scenarios=(scenario,))
record = DurableEvidenceRecordReference(
    format_name=EvidenceRecordFormat(os.environ["RECORD_FORMAT"]),
    format_version=EvidenceVersion(os.environ["RECORD_VERSION"]),
    canonicalization=EvidenceCanonicalization(os.environ["RECORD_CANONICALIZATION"]),
    sha256=ArtifactSha256Digest(os.environ["RECORD_SHA256"]),
    byte_length=ArtifactByteLength(int(os.environ["RECORD_LENGTH"])),
)

link = FaultInstanceEvidenceLink(
    fault_instance=instance, subject=report, evidence_record=record
)
assert FaultInstanceEvidenceLink.model_validate_json(link.model_dump_json()) == link

scenario_link = FaultInstanceEvidenceLink(
    fault_instance=instance, subject=scenario, evidence_record=record
)
assert type(scenario_link.subject).__name__ == "SuppliedFaultScenario"

refused = 0
for bad in ({}, fault, report.report, "text"):
    try:
        FaultInstanceEvidenceLink(
            fault_instance=instance, subject=bad, evidence_record=record
        )
    except Exception:
        refused += 1

print(
    json.dumps(
        {
            "module": str(module),
            "fields": list(FaultInstanceEvidenceLink.model_fields),
            "refused": refused,
            "link": link.model_dump_json(),
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

    root = tmp_path_factory.mktemp("fault-evidence-package")
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


def test_the_wheel_ships_twenty_three_modules_and_no_corpus_or_test_material(
    offline_distributions: tuple[Path, Path],
) -> None:
    wheel, _ = offline_distributions
    with zipfile.ZipFile(wheel) as archive:
        names = tuple(info.filename for info in archive.infolist() if not info.is_dir())

    modules = sorted(name for name in names if name.endswith(".py"))
    assert modules == EXPECTED_PRODUCTION_MODULES
    # Twenty-three since `S1.P07.S03` added the independent invariant module.
    assert len(modules) == 23
    assert "faultatlas/domain/fault_evidence_link.py" in modules
    assert "faultatlas/domain/pattern.py" in modules
    for name in names:
        assert "reference_corpus" not in name
        assert not name.startswith("tests/")
        assert not name.startswith("docs/")


def test_the_sdist_ships_twenty_three_modules_and_no_corpus_or_test_material(
    offline_distributions: tuple[Path, Path],
) -> None:
    _, sdist = offline_distributions
    with tarfile.open(sdist, "r:gz") as archive:
        names = tuple(member.name for member in archive.getmembers() if member.isfile())

    modules = sorted(
        name.split("/src/", 1)[1] for name in names if name.endswith(".py")
    )
    assert modules == EXPECTED_PRODUCTION_MODULES
    # Twenty-three since `S1.P07.S03` added the independent invariant module.
    assert len(modules) == 23
    assert "faultatlas/domain/fault_evidence_link.py" in modules
    assert "faultatlas/domain/pattern.py" in modules
    for name in names:
        parts = Path(name).parts
        assert "reference_corpus" not in parts
        assert "tests" not in parts
        assert "docs" not in parts


def test_the_installed_wheel_builds_an_instance_and_an_evidence_link(
    offline_distributions: tuple[Path, Path],
    tmp_path: Path,
) -> None:
    """Both values must be built from the wheel copy, not from the checkout."""
    wheel, _ = offline_distributions
    installed = tmp_path / "installed"
    installed.mkdir()
    with zipfile.ZipFile(wheel) as archive:
        archive.extractall(installed)

    assert (installed / "faultatlas/domain/fault_evidence_link.py").is_file()

    environment = os.environ.copy()
    environment.update(
        {
            "INSTALLED_ROOT": str(installed),
            "CHECKOUT_SOURCE_ROOT": str(CHECKOUT_SOURCE_ROOT),
            "FAULT_UUID": FAULT_TEXT,
            "REPORT_UUID": REPORT_TEXT,
            "SCENARIO_UUID": str(SCENARIO),
            "REPOSITORY_ID": CANONICAL_REPOSITORY_ID,
            "PROBLEM": PROBLEM,
            "DEVIATION": DEVIATION,
            "RECORD_FORMAT": CANONICAL_RECORD_FORMAT,
            "RECORD_VERSION": CANONICAL_RECORD_VERSION,
            "RECORD_CANONICALIZATION": CANONICAL_RECORD_CANONICALIZATION,
            "RECORD_SHA256": CANONICAL_RECORD_SHA256,
            "RECORD_LENGTH": str(CANONICAL_RECORD_LENGTH),
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
    assert reported["refused"] == 4

    expected = FaultInstanceEvidenceLink(
        fault_instance=FaultInstance(
            fault=FaultInstanceIdentity(FAULT),
            reports=(_report(),),
            scenarios=(_scenario("probe scenario"),),
        ),
        subject=_report(),
        evidence_record=_record(),
    )
    assert json.loads(reported["link"]) == _payload(expected)
