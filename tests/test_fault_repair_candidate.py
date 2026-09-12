from __future__ import annotations

import ast
import json
import os
import re
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
from pydantic import BaseModel, ConfigDict, RootModel, ValidationError

import faultatlas
import faultatlas.domain
import faultatlas.domain.fault_repair as repair_module
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
    SuppliedFaultReport,
)
from faultatlas.domain.fault_repair import (
    FaultRepairCandidateChangeSetAssociation,
    FaultRepairCandidateIdentity,
    FaultRepairCandidateRevisionAssociation,
    SuppliedFaultRepairCandidate,
)
from faultatlas.domain.fault_source_relationship import (
    FaultReportHistoryFactAssociation,
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

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
REPAIR_SOURCE = REPOSITORY_ROOT / "src/faultatlas/domain/fault_repair.py"
CHECKOUT_SOURCE_ROOT = REPOSITORY_ROOT / "src"
ROADMAP = REPOSITORY_ROOT / "docs/roadmap.md"

# Every FaultAtlas identifier and every piece of prose below is fixed synthetic
# supplied data. The retained pytest #4412 case supplies no repair-candidate
# identifier, so every candidate UUID here is invented for this file, and no
# text is a historical quotation or a claim that FaultAtlas verified a repair.
SUPPLIED_FAULT_TEXT = "12345678-1234-4234-8234-123456789abc"
SUPPLIED_FAULT = uuid.UUID(SUPPLIED_FAULT_TEXT)
SECOND_FAULT_TEXT = "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee"
SECOND_FAULT = uuid.UUID(SECOND_FAULT_TEXT)
SUPPLIED_REPORT_TEXT = "87654321-4321-4abc-8def-0123456789ab"
SUPPLIED_REPORT = uuid.UUID(SUPPLIED_REPORT_TEXT)
SECOND_REPORT_TEXT = "11111111-2222-4333-8444-555555555555"
SECOND_REPORT = uuid.UUID(SECOND_REPORT_TEXT)
SUPPLIED_CANDIDATE_TEXT = "5c5c5c5c-6d6d-4e7e-8f8f-909090909090"
SUPPLIED_CANDIDATE = uuid.UUID(SUPPLIED_CANDIDATE_TEXT)
SECOND_CANDIDATE_TEXT = "13131313-2424-4535-8646-757575757575"
SECOND_CANDIDATE = uuid.UUID(SECOND_CANDIDATE_TEXT)
NIL_UUID = uuid.UUID("00000000-0000-0000-0000-000000000000")
MAX_UUID = uuid.UUID("ffffffff-ffff-ffff-ffff-ffffffffffff")

# Fixed lexemes covering several UUID generation versions plus the two special
# values. None is generated during the run and none carries an ordering, time,
# or generation-version promise in this contract.
ADMITTED_UUID_TEXT: tuple[tuple[str, int | None], ...] = (
    ("c232ab00-9414-11ec-b3c8-9e6bdeced846", 1),
    ("6fa459ea-ee8a-3ca4-894e-db77e160355e", 3),
    (SUPPLIED_CANDIDATE_TEXT, 4),
    ("886313e1-3b8a-5372-9b90-0c9aee199e5d", 5),
    ("018f2c9e-1a2b-7c3d-8e4f-5a6b7c8d9e0f", 7),
    ("00000000-0000-8000-8000-00000000002a", 8),
    ("00000000-0000-0000-0000-000000000000", None),
    ("ffffffff-ffff-ffff-ffff-ffffffffffff", None),
)

PROBLEM_STATEMENT = "Instrumentation can change callback behavior."
BEHAVIORAL_DEVIATION = "The supplied transformed path invokes one callback twice."
SECOND_PROBLEM_STATEMENT = "A cached rewrite may be reused after the source changes."
SECOND_BEHAVIORAL_DEVIATION = "The supplied stale rewrite reports the wrong line."

REPAIR_STATEMENT = (
    "Evaluate the side-effecting expression once and reuse that value during rewriting."
)
SECOND_REPAIR_STATEMENT = (
    "Bind the compared expression to a temporary before the assertion is rewritten."
)

# Retained pytest case material, used as caller-supplied demonstration only.
# Associating it with a candidate is a caller's proposal, not a FaultAtlas
# finding that these commits or paths are a correct repair.
RETAINED_PROVIDER = "github"
RETAINED_REPOSITORY_ID = "37489525"
OTHER_REPOSITORY_ID = "37489526"
RETAINED_PULL_REQUEST_NUMBER = "4414"
RETAINED_BASE_REVISION = "4c9cde74ab40027b5761ab9e002af116a4a20df3"
RETAINED_HEAD_REVISION = "690a63b9218f72662cd3a67c6c200b758c88ce12"
RETAINED_MERGE_REVISION = "10cdae8e38ec448b7133cf163dca587ad806d262"
INTERMEDIATE_REVISION = "1111111111111111111111111111111111111111"
RETAINED_CHANGED_PATHS = (
    ("changelog/4412.bugfix.rst", "7a28b610837873eeff2a16582de6d5a035820552", "added"),
    (
        "src/_pytest/assertion/rewrite.py",
        "7b9aa5006544c160f584f1e8fc3f7771ef6e5e99",
        "modified",
    ),
    (
        "testing/test_assertrewrite.py",
        "a02433cd62ab19ebb54b42b50c299e59e48de00e",
        "modified",
    ),
)

CANDIDATE_FIELDS = ("candidate", "report", "repair_statement")
REVISION_FIELDS = ("candidate", "revision")
CHANGE_SET_FIELDS = ("candidate", "change_set")
EXPECTED_EXPORTS = [
    "FaultRepairCandidateIdentity",
    "SuppliedFaultRepairCandidate",
    "FaultRepairCandidateRevisionAssociation",
    "FaultRepairCandidateChangeSetAssociation",
]
TEXT_LIMIT = 4096

# A repair candidate is a proposal. None of these may become a field of any
# published model here: each names an authority this Slice does not have.
FORBIDDEN_REPAIR_IDENTIFIERS = (
    "applied",
    "approved",
    "cause",
    "certainty",
    "commit_count",
    "complete",
    "completeness",
    "confidence",
    "correct",
    "correctness",
    "deployed",
    "evidence",
    "evidence_record",
    "explanation",
    "fixed",
    "fixes",
    "hypothesis",
    "implemented",
    "merged",
    "occurrence",
    "origin",
    "outcome",
    "passed",
    "proof",
    "proves",
    "rationale_source",
    "regression_safe",
    "rejected",
    "repository",
    "review",
    "reviewed",
    "root_cause",
    "scenario",
    "source",
    "status",
    "strength",
    "support",
    "test_result",
    "verified",
    "verification",
)
REFUSED_EXTRA_KEYS = (*FORBIDDEN_REPAIR_IDENTIFIERS, "schema_version")

# The four other UUID-rooted `S1.P06` identities. A candidate identity is a
# fifth, and all five must stay distinct on one shared scalar.
PREDECESSOR_UUID_IDENTITIES: tuple[type[RootModel[uuid.UUID]], ...] = (
    FaultInstanceIdentity,
    FaultReportIdentity,
    FaultScenarioIdentity,
    FaultOccurrenceIdentity,
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


def _candidate_identity(
    value: uuid.UUID = SUPPLIED_CANDIDATE,
) -> FaultRepairCandidateIdentity:
    return FaultRepairCandidateIdentity(value)


def _candidate(
    candidate: uuid.UUID = SUPPLIED_CANDIDATE,
    report: SuppliedFaultReport | None = None,
    repair_statement: str = REPAIR_STATEMENT,
) -> SuppliedFaultRepairCandidate:
    return SuppliedFaultRepairCandidate(
        candidate=_candidate_identity(candidate),
        report=_report() if report is None else report,
        repair_statement=repair_statement,
    )


def _commit(full_digest: str = RETAINED_HEAD_REVISION) -> GitCommitIdentity:
    return GitCommitIdentity(
        kind=GitObjectKind.COMMIT,
        algorithm=GitHashAlgorithm.SHA1,
        full_digest=full_digest,
    )


def _blob(full_digest: str) -> GitBlobIdentity:
    return GitBlobIdentity(
        kind=GitObjectKind.BLOB,
        algorithm=GitHashAlgorithm.SHA1,
        full_digest=full_digest,
    )


def _pull_request(
    repository: str = RETAINED_REPOSITORY_ID,
) -> NumberedSourceObjectIdentity:
    return NumberedSourceObjectIdentity(
        repository_identity=_repository(repository),
        kind=SourceObjectKind.PULL_REQUEST,
        repository_scoped_number=RepositoryScopedNumber(RETAINED_PULL_REQUEST_NUMBER),
    )


def _binding(
    role: RevisionRole,
    full_digest: str,
    repository: str = RETAINED_REPOSITORY_ID,
) -> PullRequestRevisionRoleBinding:
    return PullRequestRevisionRoleBinding(
        pull_request=_pull_request(repository),
        role_assignment=RevisionRoleAssignment(
            role=role, revision=_commit(full_digest)
        ),
    )


def _changed_path(index: int = 0) -> PullRequestChangedPath:
    path, blob, status = RETAINED_CHANGED_PATHS[index]
    return PullRequestChangedPath(
        path=GitRepositoryPath(path),
        head_object=_blob(blob),
        status=ChangedPathStatus(status),
    )


def _change_set(
    paths: int = len(RETAINED_CHANGED_PATHS),
    repository: str = RETAINED_REPOSITORY_ID,
    head: str = RETAINED_HEAD_REVISION,
) -> PullRequestChangeSet:
    return PullRequestChangeSet(
        base=_binding(RevisionRole.BASE, RETAINED_BASE_REVISION, repository),
        head=_binding(RevisionRole.HEAD, head, repository),
        changed_paths=tuple(_changed_path(index) for index in range(paths)),
    )


def _evidence_record() -> DurableEvidenceRecordReference:
    """The retained acquisition record, supplied only so a link is buildable."""
    return DurableEvidenceRecordReference(
        format_name=EvidenceRecordFormat("faultatlas-acquisition"),
        format_version=EvidenceVersion("1"),
        canonicalization=EvidenceCanonicalization("json-sort-keys-compact-utf8-lf-v1"),
        sha256=ArtifactSha256Digest(
            "1c29093bf1537e9b824a18df1848b71a8da014f544bc9f385707eb0e000a1318"
        ),
        byte_length=ArtifactByteLength(61_283),
    )


def _revision_association(
    candidate: SuppliedFaultRepairCandidate | None = None,
    revision: GitCommitIdentity | None = None,
) -> FaultRepairCandidateRevisionAssociation:
    return FaultRepairCandidateRevisionAssociation(
        candidate=_candidate() if candidate is None else candidate,
        revision=_commit() if revision is None else revision,
    )


def _change_set_association(
    candidate: SuppliedFaultRepairCandidate | None = None,
    change_set: PullRequestChangeSet | None = None,
) -> FaultRepairCandidateChangeSetAssociation:
    return FaultRepairCandidateChangeSetAssociation(
        candidate=_candidate() if candidate is None else candidate,
        change_set=_change_set() if change_set is None else change_set,
    )


def _typed_candidate_mapping(**overrides: object) -> dict[str, Any]:
    mapping: dict[str, Any] = {
        "candidate": _candidate_identity(),
        "report": _report(),
        "repair_statement": REPAIR_STATEMENT,
    }
    mapping.update(overrides)
    return mapping


def _typed_revision_mapping(**overrides: object) -> dict[str, Any]:
    mapping: dict[str, Any] = {"candidate": _candidate(), "revision": _commit()}
    mapping.update(overrides)
    return mapping


def _typed_change_set_mapping(**overrides: object) -> dict[str, Any]:
    mapping: dict[str, Any] = {"candidate": _candidate(), "change_set": _change_set()}
    mapping.update(overrides)
    return mapping


def _payload(value: BaseModel) -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(value.model_dump_json()))


def _failures(error: ValidationError) -> tuple[tuple[tuple[str | int, ...], str], ...]:
    return tuple((detail["loc"], detail["type"]) for detail in error.errors())


def _paths(error: ValidationError) -> tuple[tuple[str | int, ...], ...]:
    return tuple(detail["loc"] for detail in error.errors())


def _distinct_value_count(*values: object) -> int:
    return len({cast(Any, value) for value in values})


def _repair_tree() -> ast.Module:
    return ast.parse(REPAIR_SOURCE.read_bytes(), filename=REPAIR_SOURCE.name)


def _roadmap() -> str:
    return " ".join(ROADMAP.read_text(encoding="utf-8").split())


def _published_models() -> tuple[type[BaseModel], ...]:
    return (
        SuppliedFaultRepairCandidate,
        FaultRepairCandidateRevisionAssociation,
        FaultRepairCandidateChangeSetAssociation,
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


class ForeignSuppliedFaultRepairCandidate(BaseModel):
    """A structurally identical record that is not the published type."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        strict=True,
        revalidate_instances="always",
        validate_default=True,
    )

    candidate: FaultRepairCandidateIdentity
    report: SuppliedFaultReport
    repair_statement: str


class CandidateLookalike:
    """An attribute-backed object carrying the published field names."""

    def __init__(self) -> None:
        self.candidate = _candidate_identity()
        self.report = _report()
        self.repair_statement = REPAIR_STATEMENT


class UntypedChildCandidateLookalike:
    """An attribute-backed top-level object whose report child is untyped."""

    def __init__(self) -> None:
        self.candidate = _candidate_identity()
        self.report = _report().model_dump()
        self.repair_statement = REPAIR_STATEMENT


class RevisionLookalike:
    """An attribute-backed object carrying a commit identity's field names."""

    def __init__(self) -> None:
        self.schema_version = 1
        self.kind = GitObjectKind.COMMIT
        self.algorithm = GitHashAlgorithm.SHA1
        self.full_digest = RETAINED_HEAD_REVISION


class UnextendedFaultRepairCandidateIdentity(FaultRepairCandidateIdentity):
    """An ordinary identity subclass that adds no field."""


class UnextendedSuppliedFaultRepairCandidate(SuppliedFaultRepairCandidate):
    """An ordinary candidate subclass that adds no field."""


class ExtendedSuppliedFaultRepairCandidate(SuppliedFaultRepairCandidate):
    """A candidate subclass that adds a field the base schema forbids."""

    note: str = "supplied"


class SuppliedText(str):
    """A str subclass carrying an ordinary value."""


# --- the candidate identity ---------------------------------------------------


def test_a_candidate_identity_accepts_a_supplied_uuid_through_every_entry_path() -> (
    None
):
    positional = FaultRepairCandidateIdentity(SUPPLIED_CANDIDATE)
    keyword = FaultRepairCandidateIdentity(root=SUPPLIED_CANDIDATE)
    validated = FaultRepairCandidateIdentity.model_validate(SUPPLIED_CANDIDATE)

    assert positional.root == SUPPLIED_CANDIDATE
    assert positional == keyword == validated


@pytest.mark.parametrize(
    ("text", "version"),
    tuple(pytest.param(text, version, id=text) for text, version in ADMITTED_UUID_TEXT),
)
def test_the_identity_admits_every_uuid_the_locked_validator_admits(
    text: str,
    version: int | None,
) -> None:
    """Nil and Max are ordinary values here, not missing-state sentinels."""
    value = uuid.UUID(text)
    identity = FaultRepairCandidateIdentity(value)

    assert identity.root == value
    assert identity.root.version == version
    assert (
        FaultRepairCandidateIdentity.model_validate_json(identity.model_dump_json())
        == identity
    )


@pytest.mark.parametrize("supplied", (SUPPLIED_CANDIDATE_TEXT, 1, None, b"", 1.0))
def test_the_identity_refuses_untyped_python_input(supplied: object) -> None:
    """Strict Python input requires a real `uuid.UUID`, text included."""
    with pytest.raises(ValidationError) as failure:
        FaultRepairCandidateIdentity(cast(Any, supplied))

    assert _paths(failure.value) == ((),)


def test_the_identity_accepts_uuid_text_in_json_and_round_trips_as_a_scalar() -> None:
    identity = _candidate_identity()
    dumped = identity.model_dump_json()

    assert dumped == f'"{SUPPLIED_CANDIDATE_TEXT}"'
    assert json.loads(dumped) == SUPPLIED_CANDIDATE_TEXT
    assert FaultRepairCandidateIdentity.model_validate_json(dumped) == identity


@pytest.mark.parametrize(
    "wrapper",
    (
        {"root": SUPPLIED_CANDIDATE_TEXT},
        {"candidate": SUPPLIED_CANDIDATE_TEXT},
        {"candidate_id": SUPPLIED_CANDIDATE_TEXT},
        {"repair_candidate_id": SUPPLIED_CANDIDATE_TEXT},
    ),
)
def test_no_wrapper_object_json_form_is_published(wrapper: dict[str, str]) -> None:
    with pytest.raises(ValidationError):
        FaultRepairCandidateIdentity.model_validate_json(json.dumps(wrapper))


def test_the_identity_declares_the_published_value_profile() -> None:
    assert FaultRepairCandidateIdentity.model_config == {
        "frozen": True,
        "strict": True,
        "revalidate_instances": "always",
        "validate_default": True,
    }
    assert tuple(FaultRepairCandidateIdentity.model_fields) == ("root",)
    assert FaultRepairCandidateIdentity.model_fields["root"].is_required()
    assert FaultRepairCandidateIdentity.model_fields["root"].default_factory is None


def test_the_identity_is_frozen_and_allocates_nothing() -> None:
    identity = _candidate_identity()

    with pytest.raises(ValidationError):
        identity.root = MAX_UUID  # type: ignore[misc]

    with pytest.raises(ValidationError):
        FaultRepairCandidateIdentity()  # type: ignore[call-arg]


def test_the_identity_is_not_a_subclass_or_alias_of_its_four_predecessors() -> None:
    for predecessor in PREDECESSOR_UUID_IDENTITIES:
        assert not issubclass(FaultRepairCandidateIdentity, predecessor)
        assert not issubclass(predecessor, FaultRepairCandidateIdentity)
        assert FaultRepairCandidateIdentity is not predecessor


@pytest.mark.parametrize("scalar", (SUPPLIED_CANDIDATE, NIL_UUID, MAX_UUID))
def test_all_five_p06_identities_stay_distinct_on_one_shared_scalar(
    scalar: uuid.UUID,
) -> None:
    """One UUID may name a fault, report, scenario, occurrence and candidate."""
    carried: list[RootModel[uuid.UUID]] = [
        model(scalar) for model in PREDECESSOR_UUID_IDENTITIES
    ]
    carried.append(FaultRepairCandidateIdentity(scalar))

    for index, first in enumerate(carried):
        for second in carried[index + 1 :]:
            assert first != second
            assert second != first
    assert _distinct_value_count(*carried) == 5
    assert all(value.root == scalar for value in carried)


def test_a_foreign_uuid_root_model_is_not_a_candidate_identity() -> None:
    foreign = ForeignUuidRoot(SUPPLIED_CANDIDATE)

    assert foreign != _candidate_identity()
    with pytest.raises(ValidationError):
        SuppliedFaultRepairCandidate(
            candidate=cast(Any, foreign),
            report=_report(),
            repair_statement=REPAIR_STATEMENT,
        )


def test_equal_identities_hash_equally_and_carry_no_ordering() -> None:
    first = _candidate_identity()
    second = _candidate_identity()
    other = _candidate_identity(SECOND_CANDIDATE)

    assert first == second
    assert hash(first) == hash(second)
    assert first != other
    assert _distinct_value_count(first, second, other) == 2
    comparisons: tuple[Any, ...] = (
        lambda: cast(Any, first) < cast(Any, other),
        lambda: cast(Any, first) > cast(Any, other),
        lambda: cast(Any, first) <= cast(Any, other),
        lambda: cast(Any, first) >= cast(Any, other),
    )
    for compare in comparisons:
        with pytest.raises(TypeError):
            compare()


# --- the supplied candidate ---------------------------------------------------


def test_the_candidate_declares_exactly_three_fields_in_order() -> None:
    assert tuple(SuppliedFaultRepairCandidate.model_fields) == CANDIDATE_FIELDS


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


def test_a_candidate_is_built_from_already_typed_values() -> None:
    candidate = _candidate()

    assert candidate.candidate == _candidate_identity()
    assert candidate.report == _report()
    assert candidate.repair_statement == REPAIR_STATEMENT
    assert candidate.report.context.fault == FaultInstanceIdentity(SUPPLIED_FAULT)


def test_a_candidate_json_payload_has_exactly_three_keys() -> None:
    payload = _payload(_candidate())

    assert list(payload) == list(CANDIDATE_FIELDS)
    assert payload["candidate"] == SUPPLIED_CANDIDATE_TEXT
    assert payload["repair_statement"] == REPAIR_STATEMENT
    assert payload["report"]["report"] == SUPPLIED_REPORT_TEXT
    assert payload["report"]["context"]["fault"] == SUPPLIED_FAULT_TEXT


def test_a_candidate_round_trips_through_json() -> None:
    candidate = _candidate()

    restored = SuppliedFaultRepairCandidate.model_validate_json(
        candidate.model_dump_json()
    )

    assert restored == candidate
    assert type(restored.candidate) is FaultRepairCandidateIdentity
    assert type(restored.report) is SuppliedFaultReport


def test_a_candidate_refuses_its_own_python_dump() -> None:
    """A Python dump has projected its typed children to plain containers."""
    candidate = _candidate()

    with pytest.raises(ValidationError) as failure:
        SuppliedFaultRepairCandidate.model_validate(candidate.model_dump())

    assert _failures(failure.value) == (
        (("candidate",), "value_error"),
        (("report",), "value_error"),
    )


def test_a_candidate_accepts_its_own_typed_instance() -> None:
    candidate = _candidate()

    assert SuppliedFaultRepairCandidate.model_validate(candidate) == candidate


def test_a_candidate_needs_no_scenario_occurrence_or_root_cause() -> None:
    """A proposal may precede diagnosis, reproduction and implementation."""
    assert set(SuppliedFaultRepairCandidate.model_fields) == set(CANDIDATE_FIELDS)

    # Independent of the equality above: none of these reaches any record here,
    # as a field of any of the three models or as a key of any payload.
    payloads = [
        _payload(_candidate()),
        _payload(_revision_association()),
        _payload(_change_set_association()),
    ]
    for absent in (
        "scenario",
        "occurrence",
        "cause",
        "root_cause",
        "explanation",
        "hypothesis",
    ):
        for model in _published_models():
            assert absent not in model.model_fields, (model.__name__, absent)
        for payload in payloads:
            assert absent not in payload, absent
    assert _candidate().repair_statement == REPAIR_STATEMENT


def test_a_conceptual_candidate_is_complete_with_no_implementation() -> None:
    """No revision or change set is needed for a candidate to be a value."""
    candidate = _candidate()

    assert (
        SuppliedFaultRepairCandidate.model_validate_json(candidate.model_dump_json())
        == candidate
    )
    assert "revision" not in _payload(candidate)
    assert "change_set" not in _payload(candidate)
    # Nothing in the record can be read as "not yet implemented" either.
    for absent in ("implemented", "applied", "merged", "status", "outcome"):
        assert absent not in SuppliedFaultRepairCandidate.model_fields


@pytest.mark.parametrize("model", _published_models(), ids=lambda m: m.__name__)
def test_no_record_declares_a_status_evidence_or_confidence_field(
    model: type[BaseModel],
) -> None:
    declared = set(model.model_fields)

    for name in FORBIDDEN_REPAIR_IDENTIFIERS:
        assert name not in declared, (model.__name__, name)


def test_no_record_json_payload_carries_a_forbidden_key() -> None:
    for value in (_candidate(), _revision_association(), _change_set_association()):
        payload = _payload(value)
        for name in FORBIDDEN_REPAIR_IDENTIFIERS:
            assert name not in payload, (type(value).__name__, name)
        assert "schema_version" not in payload


# --- candidate child guards, omission, frozen, extras -------------------------


@pytest.mark.parametrize(
    ("label", "supplied"),
    (
        pytest.param("bare uuid", SUPPLIED_CANDIDATE, id="bare-uuid"),
        pytest.param("uuid text", SUPPLIED_CANDIDATE_TEXT, id="uuid-text"),
        pytest.param("mapping", {"root": SUPPLIED_CANDIDATE}, id="mapping"),
        pytest.param("foreign root", ForeignUuidRoot(SUPPLIED_CANDIDATE), id="foreign"),
        pytest.param(
            "report identity", FaultReportIdentity(SUPPLIED_CANDIDATE), id="sibling"
        ),
    ),
)
def test_the_candidate_position_is_closed_to_untyped_python_input(
    label: str,
    supplied: object,
) -> None:
    with pytest.raises(ValidationError) as failure:
        SuppliedFaultRepairCandidate(
            candidate=cast(Any, supplied),
            report=_report(),
            repair_statement=REPAIR_STATEMENT,
        )

    assert _failures(failure.value) == ((("candidate",), "value_error"),), label


@pytest.mark.parametrize(
    ("label", "supplied"),
    (
        pytest.param("raw mapping", _report().model_dump(), id="raw-mapping"),
        pytest.param("lookalike", CandidateLookalike(), id="attribute-lookalike"),
        pytest.param("context", _context(), id="context"),
        pytest.param("bare uuid", SUPPLIED_REPORT, id="bare-uuid"),
        pytest.param(
            "json text",
            json.dumps(_report().model_dump(mode="json")),
            id="json-text",
        ),
    ),
)
def test_the_report_position_is_closed_to_untyped_python_input(
    label: str,
    supplied: object,
) -> None:
    with pytest.raises(ValidationError) as failure:
        SuppliedFaultRepairCandidate(
            candidate=_candidate_identity(),
            report=cast(Any, supplied),
            repair_statement=REPAIR_STATEMENT,
        )

    assert _failures(failure.value) == ((("report",), "value_error"),), label


@pytest.mark.parametrize("from_attributes", (True, False), ids=("attrs", "no-attrs"))
def test_a_top_level_candidate_mapping_still_guards_each_child(
    from_attributes: bool,
) -> None:
    admitted = SuppliedFaultRepairCandidate.model_validate(
        _typed_candidate_mapping(), from_attributes=from_attributes
    )
    assert admitted == _candidate()

    with pytest.raises(ValidationError) as failure:
        SuppliedFaultRepairCandidate.model_validate(
            _typed_candidate_mapping(report=_report().model_dump()),
            from_attributes=from_attributes,
        )

    assert _failures(failure.value) == ((("report",), "value_error"),)


def test_from_attributes_reads_a_top_level_object_but_still_guards_its_children() -> (
    None
):
    """The guard is on the children, so a typed-child carrier is admitted.

    `from_attributes=True` is a statement about how the top-level value is
    read, not a relaxation of what each child position accepts: a lookalike
    carrying already-typed children is admitted exactly as a mapping of typed
    children is, and one carrying a raw child is refused at that child.
    """
    admitted = SuppliedFaultRepairCandidate.model_validate(
        CandidateLookalike(), from_attributes=True
    )
    assert admitted == _candidate()

    with pytest.raises(ValidationError) as failure:
        SuppliedFaultRepairCandidate.model_validate(
            UntypedChildCandidateLookalike(), from_attributes=True
        )

    assert _failures(failure.value) == ((("report",), "value_error"),)


@pytest.mark.parametrize("omitted", CANDIDATE_FIELDS)
def test_a_true_candidate_omission_fails_at_its_own_position(omitted: str) -> None:
    supplied = _typed_candidate_mapping()
    del supplied[omitted]

    with pytest.raises(ValidationError) as failure:
        SuppliedFaultRepairCandidate(**supplied)

    assert _failures(failure.value) == (((omitted,), "missing"),)


@pytest.mark.parametrize("field", CANDIDATE_FIELDS)
def test_a_candidate_is_frozen_against_assignment_and_deletion(field: str) -> None:
    candidate = _candidate()

    with pytest.raises(ValidationError) as failure:
        setattr(candidate, field, getattr(candidate, field))
    assert _failures(failure.value) == (((field,), "frozen_instance"),)

    with pytest.raises((AttributeError, ValidationError)):
        delattr(candidate, field)


@pytest.mark.parametrize("extra", REFUSED_EXTRA_KEYS)
def test_an_extra_candidate_key_is_refused_in_python_input(extra: str) -> None:
    with pytest.raises(ValidationError) as failure:
        SuppliedFaultRepairCandidate(**_typed_candidate_mapping(**{extra: "supplied"}))

    assert _failures(failure.value) == (((extra,), "extra_forbidden"),)


@pytest.mark.parametrize("extra", REFUSED_EXTRA_KEYS)
def test_an_extra_candidate_key_is_refused_in_json_input(extra: str) -> None:
    payload = _payload(_candidate())
    payload[extra] = "supplied"

    with pytest.raises(ValidationError) as failure:
        SuppliedFaultRepairCandidate.model_validate_json(json.dumps(payload))

    assert _failures(failure.value) == (((extra,), "extra_forbidden"),)


def test_an_extra_key_inside_the_embedded_report_is_refused() -> None:
    payload = _payload(_candidate())
    payload["report"]["confidence"] = "high"

    with pytest.raises(ValidationError) as failure:
        SuppliedFaultRepairCandidate.model_validate_json(json.dumps(payload))

    assert _failures(failure.value) == ((("report", "confidence"), "extra_forbidden"),)


def _corrupt_candidate_identity(payload: dict[str, Any]) -> None:
    payload["candidate"] = "not-a-uuid"


def _corrupt_embedded_fault(payload: dict[str, Any]) -> None:
    payload["report"]["context"]["fault"] = "not-a-uuid"


def _corrupt_repair_statement(payload: dict[str, Any]) -> None:
    payload["repair_statement"] = " padded "


def _corrupt_report_problem(payload: dict[str, Any]) -> None:
    payload["report"]["problem_statement"] = ""


@pytest.mark.parametrize(
    ("mutate", "expected"),
    (
        pytest.param(_corrupt_candidate_identity, ("candidate",), id="candidate"),
        pytest.param(
            _corrupt_embedded_fault, ("report", "context", "fault"), id="nested-fault"
        ),
        pytest.param(
            _corrupt_repair_statement, ("repair_statement",), id="padded-statement"
        ),
        pytest.param(
            _corrupt_report_problem, ("report", "problem_statement"), id="empty-problem"
        ),
    ),
)
def test_a_malformed_candidate_reentry_fails_at_the_relevant_path(
    mutate: Any,
    expected: tuple[str, ...],
) -> None:
    payload = _payload(_candidate())
    mutate(payload)

    with pytest.raises(ValidationError) as failure:
        SuppliedFaultRepairCandidate.model_validate_json(json.dumps(payload))

    assert expected in _paths(failure.value)


def test_a_no_added_field_subclass_is_admitted_and_base_normalized() -> None:
    """The promise is the normalized value, not preservation of the subclass."""
    candidate = SuppliedFaultRepairCandidate.model_validate(
        _typed_candidate_mapping(
            candidate=UnextendedFaultRepairCandidateIdentity(SUPPLIED_CANDIDATE)
        )
    )
    subclass = UnextendedSuppliedFaultRepairCandidate(**_typed_candidate_mapping())
    association = FaultRepairCandidateRevisionAssociation(
        candidate=subclass, revision=_commit()
    )

    assert candidate == _candidate()
    assert type(candidate.candidate) is FaultRepairCandidateIdentity
    assert association == _revision_association()
    assert type(association.candidate) is SuppliedFaultRepairCandidate


def test_a_subclass_extra_field_remains_refused() -> None:
    supplied = ExtendedSuppliedFaultRepairCandidate(
        **_typed_candidate_mapping(), note="supplied"
    )

    with pytest.raises(ValidationError) as failure:
        FaultRepairCandidateRevisionAssociation(candidate=supplied, revision=_commit())

    assert _failures(failure.value) == ((("candidate", "note"), "extra_forbidden"),)


# --- the repair statement text matrix -----------------------------------------


@pytest.mark.parametrize(
    "supplied",
    (
        "x",
        REPAIR_STATEMENT,
        "Multi\nline\nproposal.",
        "Tab\tseparated proposal.",
        "Unicode: café — naïve — 変更 — 🛠",
        "a" * TEXT_LIMIT,
        "Inner  double  spaces stay.",
    ),
)
def test_an_admitted_repair_statement_is_preserved_exactly(supplied: str) -> None:
    candidate = _candidate(repair_statement=supplied)

    assert candidate.repair_statement == supplied
    assert _payload(candidate)["repair_statement"] == supplied
    assert (
        SuppliedFaultRepairCandidate.model_validate_json(
            candidate.model_dump_json()
        ).repair_statement
        == supplied
    )


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
def test_a_refused_repair_statement_is_refused(supplied: str) -> None:
    with pytest.raises(ValidationError) as failure:
        _candidate(repair_statement=supplied)

    assert _paths(failure.value) == (("repair_statement",),)


@pytest.mark.parametrize("supplied", (None, 1, 1.0, b"bytes", ["text"], SUPPLIED_FAULT))
def test_a_non_string_repair_statement_is_refused(supplied: object) -> None:
    with pytest.raises(ValidationError) as failure:
        SuppliedFaultRepairCandidate(
            candidate=_candidate_identity(),
            report=_report(),
            repair_statement=cast(Any, supplied),
        )

    assert _paths(failure.value) == (("repair_statement",),)


def test_a_str_subclass_repair_statement_normalizes_to_str() -> None:
    candidate = _candidate(repair_statement=SuppliedText(REPAIR_STATEMENT))

    assert candidate.repair_statement == REPAIR_STATEMENT
    assert type(candidate.repair_statement) is str


def test_an_unencodable_repair_statement_is_refused_at_the_field() -> None:
    """Text that cannot encode as UTF-8 is refused where it is supplied."""
    with pytest.raises(ValidationError) as failure:
        _candidate(repair_statement="lone surrogate \ud800")

    assert _failures(failure.value) == ((("repair_statement",), "string_unicode"),)


def test_the_repair_statement_bound_is_declared_inline_on_the_field() -> None:
    """The bound is stated on the field, not through a shared alias.

    That no shared public alias is exported is held by the `__all__` lock; this
    asserts only that the literal bound is declared where the field is.
    """
    (candidate_class,) = [
        node
        for node in _repair_tree().body
        if isinstance(node, ast.ClassDef)
        and node.name == "SuppliedFaultRepairCandidate"
    ]
    annotations = [
        ast.unparse(node.annotation)
        for node in candidate_class.body
        if isinstance(node, ast.AnnAssign)
    ]

    assert any(
        "StringConstraints(min_length=1, max_length=4096)" in text
        for text in annotations
    )


# --- multiplicity and absence -------------------------------------------------


def test_one_report_may_carry_several_candidates() -> None:
    report = _report()
    first = _candidate(candidate=SUPPLIED_CANDIDATE, report=report)
    second = _candidate(
        candidate=SECOND_CANDIDATE,
        report=report,
        repair_statement=SECOND_REPAIR_STATEMENT,
    )

    assert first != second
    assert first.report == second.report == report
    assert _distinct_value_count(first.candidate, second.candidate) == 2


def test_identical_repair_prose_does_not_merge_two_candidates() -> None:
    """Nothing deduplicates: identical text stays two proposals."""
    report = _report()
    first = _candidate(candidate=SUPPLIED_CANDIDATE, report=report)
    second = _candidate(candidate=SECOND_CANDIDATE, report=report)

    assert first.repair_statement == second.repair_statement
    assert first != second
    assert first.candidate != second.candidate
    assert _distinct_value_count(first, second) == 2


def test_one_candidate_may_carry_several_revision_associations() -> None:
    candidate = _candidate()
    associations = tuple(
        _revision_association(candidate=candidate, revision=_commit(digest))
        for digest in (
            RETAINED_HEAD_REVISION,
            RETAINED_MERGE_REVISION,
            INTERMEDIATE_REVISION,
        )
    )

    assert _distinct_value_count(*associations) == 3
    assert all(item.candidate == candidate for item in associations)


def test_one_candidate_may_carry_several_change_set_associations() -> None:
    candidate = _candidate()
    first = _change_set_association(
        candidate=candidate, change_set=_change_set(paths=1)
    )
    second = _change_set_association(
        candidate=candidate, change_set=_change_set(paths=3)
    )

    assert first != second
    assert first.candidate == second.candidate == candidate


def test_one_revision_may_serve_candidates_of_two_different_fault_reports() -> None:
    """Sharing a commit merges neither the candidates nor the fault subjects."""
    revision = _commit()
    first = _revision_association(
        candidate=_candidate(candidate=SUPPLIED_CANDIDATE), revision=revision
    )
    second = _revision_association(
        candidate=_candidate(candidate=SECOND_CANDIDATE, report=_second_report()),
        revision=revision,
    )

    assert first != second
    assert first.revision == second.revision
    assert first.candidate.candidate != second.candidate.candidate
    assert first.candidate.report.context.fault != second.candidate.report.context.fault
    assert (
        _distinct_value_count(
            first.candidate.report.context.fault,
            second.candidate.report.context.fault,
        )
        == 2
    )


def test_one_change_set_may_serve_candidates_of_two_different_fault_reports() -> None:
    change_set = _change_set()
    first = _change_set_association(
        candidate=_candidate(candidate=SUPPLIED_CANDIDATE), change_set=change_set
    )
    second = _change_set_association(
        candidate=_candidate(candidate=SECOND_CANDIDATE, report=_second_report()),
        change_set=change_set,
    )

    assert first != second
    assert first.change_set == second.change_set
    assert first.candidate.report.context.fault != second.candidate.report.context.fault


def test_no_collection_field_and_no_module_registry_is_published() -> None:
    """Multiplicity is held by the caller, not by any container published here."""
    published = {
        node.name for node in ast.walk(_repair_tree()) if isinstance(node, ast.ClassDef)
    }

    assert published == set(EXPECTED_EXPORTS)
    for model in _published_models():
        for name, field in model.model_fields.items():
            assert field.is_required(), (model.__name__, name)
            annotation = field.annotation
            # The declared type itself, not its spelling: `set` is a substring
            # of `PullRequestChangeSet`, so a name scan would be nonsense here.
            # A container field would be a parametrized generic -- `tuple[...]`,
            # `list[...]`, `set[...]`, `dict[...]` -- and every field here is a
            # plain class instead.
            assert typing.get_origin(annotation) is None, (model.__name__, name)
            assert isinstance(annotation, type), (model.__name__, name)
            # A bare `list` is a plain class with no origin, so the two checks
            # above admit it; the declared type must not be a container at all.
            assert annotation not in (list, tuple, set, frozenset, dict), (
                model.__name__,
                name,
            )

    # A module-level container is the shape a candidate registry would take.
    for name, value in vars(repair_module).items():
        if name.startswith("__"):
            continue
        assert not isinstance(value, dict | list | set), name


# --- the revision association --------------------------------------------------


def test_the_revision_association_declares_exactly_two_fields_in_order() -> None:
    assert (
        tuple(FaultRepairCandidateRevisionAssociation.model_fields) == REVISION_FIELDS
    )


def test_a_revision_association_is_built_from_already_typed_values() -> None:
    association = _revision_association()

    assert association.candidate == _candidate()
    assert association.revision == _commit()
    assert association.candidate.report.context.fault == FaultInstanceIdentity(
        SUPPLIED_FAULT
    )


def test_a_revision_association_round_trips_through_json() -> None:
    association = _revision_association()

    restored = FaultRepairCandidateRevisionAssociation.model_validate_json(
        association.model_dump_json()
    )

    assert restored == association
    assert type(restored.revision) is GitCommitIdentity
    assert list(_payload(association)) == list(REVISION_FIELDS)
    assert _payload(association)["revision"]["full_digest"] == RETAINED_HEAD_REVISION


def test_a_revision_association_refuses_its_own_python_dump() -> None:
    association = _revision_association()

    with pytest.raises(ValidationError) as failure:
        FaultRepairCandidateRevisionAssociation.model_validate(association.model_dump())

    assert _failures(failure.value) == (
        (("candidate",), "value_error"),
        (("revision",), "value_error"),
    )


@pytest.mark.parametrize(
    ("label", "supplied"),
    (
        pytest.param("raw mapping", _commit().model_dump(), id="raw-mapping"),
        pytest.param("lookalike", RevisionLookalike(), id="attribute-lookalike"),
        pytest.param("bare digest", RETAINED_HEAD_REVISION, id="bare-digest"),
        pytest.param(
            "tree identity",
            GitTreeIdentity(
                kind=GitObjectKind.TREE,
                algorithm=GitHashAlgorithm.SHA1,
                full_digest=RETAINED_HEAD_REVISION,
            ),
            id="tree-identity",
        ),
        pytest.param(
            "json text",
            json.dumps(_commit().model_dump(mode="json")),
            id="json-text",
        ),
    ),
)
def test_the_revision_position_is_closed_to_untyped_python_input(
    label: str,
    supplied: object,
) -> None:
    with pytest.raises(ValidationError) as failure:
        FaultRepairCandidateRevisionAssociation(
            candidate=_candidate(), revision=cast(Any, supplied)
        )

    assert _failures(failure.value) == ((("revision",), "value_error"),), label


@pytest.mark.parametrize(
    ("label", "supplied"),
    (
        pytest.param("raw mapping", _candidate().model_dump(), id="raw-mapping"),
        pytest.param("lookalike", CandidateLookalike(), id="attribute-lookalike"),
        pytest.param("identity only", _candidate_identity(), id="identity"),
        pytest.param("report", _report(), id="report"),
        pytest.param(
            "foreign record",
            ForeignSuppliedFaultRepairCandidate(**_typed_candidate_mapping()),
            id="foreign-record",
        ),
    ),
)
def test_the_revision_associations_candidate_position_is_closed(
    label: str,
    supplied: object,
) -> None:
    with pytest.raises(ValidationError) as failure:
        FaultRepairCandidateRevisionAssociation(
            candidate=cast(Any, supplied), revision=_commit()
        )

    assert _failures(failure.value) == ((("candidate",), "value_error"),), label


@pytest.mark.parametrize("omitted", REVISION_FIELDS)
def test_a_true_revision_omission_fails_at_its_own_position(omitted: str) -> None:
    supplied = _typed_revision_mapping()
    del supplied[omitted]

    with pytest.raises(ValidationError) as failure:
        FaultRepairCandidateRevisionAssociation(**supplied)

    assert _failures(failure.value) == (((omitted,), "missing"),)


@pytest.mark.parametrize("extra", REFUSED_EXTRA_KEYS)
def test_an_extra_revision_key_is_refused_in_python_input(extra: str) -> None:
    with pytest.raises(ValidationError) as failure:
        FaultRepairCandidateRevisionAssociation(
            **_typed_revision_mapping(**{extra: "supplied"})
        )

    assert _failures(failure.value) == (((extra,), "extra_forbidden"),)


def test_a_revision_association_is_frozen() -> None:
    association = _revision_association()

    with pytest.raises(ValidationError) as failure:
        association.revision = _commit(RETAINED_MERGE_REVISION)  # type: ignore[misc]

    assert _failures(failure.value) == ((("revision",), "frozen_instance"),)


def test_a_malformed_revision_reentry_is_refused_under_the_published_schema() -> None:
    payload = _payload(_revision_association())
    payload["revision"]["full_digest"] = "not-a-digest"

    with pytest.raises(ValidationError) as failure:
        FaultRepairCandidateRevisionAssociation.model_validate_json(json.dumps(payload))

    assert ("revision",) in _paths(failure.value)


@pytest.mark.parametrize("from_attributes", (True, False), ids=("attrs", "no-attrs"))
def test_a_top_level_revision_mapping_still_guards_each_child(
    from_attributes: bool,
) -> None:
    admitted = FaultRepairCandidateRevisionAssociation.model_validate(
        _typed_revision_mapping(), from_attributes=from_attributes
    )
    assert admitted == _revision_association()

    with pytest.raises(ValidationError) as failure:
        FaultRepairCandidateRevisionAssociation.model_validate(
            _typed_revision_mapping(revision=_commit().model_dump()),
            from_attributes=from_attributes,
        )

    assert _failures(failure.value) == ((("revision",), "value_error"),)


def test_a_revision_association_claims_no_repository_membership_or_role() -> None:
    """The commit is reused intrinsically; where it lives is not asserted."""
    association = _revision_association()
    payload = _payload(association)

    assert set(payload["revision"]) == {
        "schema_version",
        "kind",
        "algorithm",
        "full_digest",
    }
    for absent in (
        "repository",
        "repository_identity",
        "role",
        "head",
        "merge",
        "applied",
        "fixed",
        "reachable",
        "branch",
    ):
        assert absent not in payload
        assert absent not in payload["revision"]


def test_a_revision_unrelated_to_the_reports_repository_is_admitted() -> None:
    """Nothing requires the commit to belong to the report's repository.

    A commit identity carries no repository at all, so an association cannot be
    repository-incoherent; the claim is that no such requirement was added. The
    digest here belongs to no pull request this file names.
    """
    unrelated = _commit("deadbeefdeadbeefdeadbeefdeadbeefdeadbeef")
    association = _revision_association(revision=unrelated)

    assert association.revision == unrelated
    assert set(_payload(association)["revision"]) == {
        "schema_version",
        "kind",
        "algorithm",
        "full_digest",
    }
    assert association.candidate.report.context.repository == _repository()
    assert (
        FaultRepairCandidateRevisionAssociation.model_validate_json(
            association.model_dump_json()
        )
        == association
    )


# --- the change-set association -------------------------------------------------


def test_the_change_set_association_declares_exactly_two_fields_in_order() -> None:
    assert (
        tuple(FaultRepairCandidateChangeSetAssociation.model_fields)
        == CHANGE_SET_FIELDS
    )


def test_a_change_set_association_consumes_the_published_p05_value() -> None:
    change_set = _change_set()
    association = _change_set_association(change_set=change_set)

    assert association.change_set == change_set
    assert type(association.change_set) is PullRequestChangeSet
    assert len(association.change_set.changed_paths) == len(RETAINED_CHANGED_PATHS)
    assert association.change_set.base.role_assignment.role is RevisionRole.BASE
    assert association.change_set.head.role_assignment.role is RevisionRole.HEAD


def test_a_change_set_association_round_trips_through_json() -> None:
    association = _change_set_association()

    restored = FaultRepairCandidateChangeSetAssociation.model_validate_json(
        association.model_dump_json()
    )

    assert restored == association
    assert type(restored.change_set) is PullRequestChangeSet
    assert restored.change_set == _change_set()
    assert list(_payload(association)) == list(CHANGE_SET_FIELDS)


def test_a_change_set_association_refuses_its_own_python_dump() -> None:
    association = _change_set_association()

    with pytest.raises(ValidationError) as failure:
        FaultRepairCandidateChangeSetAssociation.model_validate(
            association.model_dump()
        )

    assert _failures(failure.value) == (
        (("candidate",), "value_error"),
        (("change_set",), "value_error"),
    )


@pytest.mark.parametrize(
    ("label", "supplied"),
    (
        pytest.param("raw mapping", _change_set().model_dump(), id="raw-mapping"),
        pytest.param(
            "binding", _binding(RevisionRole.HEAD, RETAINED_HEAD_REVISION), id="binding"
        ),
        pytest.param("changed path", _changed_path(), id="changed-path"),
        pytest.param("commit", _commit(), id="commit"),
        pytest.param(
            "json text",
            json.dumps(_change_set().model_dump(mode="json")),
            id="json-text",
        ),
    ),
)
def test_the_change_set_position_is_closed_to_untyped_python_input(
    label: str,
    supplied: object,
) -> None:
    with pytest.raises(ValidationError) as failure:
        FaultRepairCandidateChangeSetAssociation(
            candidate=_candidate(), change_set=cast(Any, supplied)
        )

    assert _failures(failure.value) == ((("change_set",), "value_error"),), label


@pytest.mark.parametrize("omitted", CHANGE_SET_FIELDS)
def test_a_true_change_set_omission_fails_at_its_own_position(omitted: str) -> None:
    supplied = _typed_change_set_mapping()
    del supplied[omitted]

    with pytest.raises(ValidationError) as failure:
        FaultRepairCandidateChangeSetAssociation(**supplied)

    assert _failures(failure.value) == (((omitted,), "missing"),)


@pytest.mark.parametrize("extra", REFUSED_EXTRA_KEYS)
def test_an_extra_change_set_key_is_refused_in_python_input(extra: str) -> None:
    with pytest.raises(ValidationError) as failure:
        FaultRepairCandidateChangeSetAssociation(
            **_typed_change_set_mapping(**{extra: "supplied"})
        )

    assert _failures(failure.value) == (((extra,), "extra_forbidden"),)


def test_a_change_set_association_is_frozen() -> None:
    association = _change_set_association()

    with pytest.raises(ValidationError) as failure:
        association.change_set = _change_set(paths=1)  # type: ignore[misc]

    assert _failures(failure.value) == ((("change_set",), "frozen_instance"),)


@pytest.mark.parametrize("from_attributes", (True, False), ids=("attrs", "no-attrs"))
def test_a_top_level_change_set_mapping_still_guards_each_child(
    from_attributes: bool,
) -> None:
    admitted = FaultRepairCandidateChangeSetAssociation.model_validate(
        _typed_change_set_mapping(), from_attributes=from_attributes
    )
    assert admitted == _change_set_association()

    with pytest.raises(ValidationError) as failure:
        FaultRepairCandidateChangeSetAssociation.model_validate(
            _typed_change_set_mapping(change_set=_change_set().model_dump()),
            from_attributes=from_attributes,
        )

    assert _failures(failure.value) == ((("change_set",), "value_error"),)


def _break_same_pull_request(payload: dict[str, Any]) -> None:
    payload["change_set"]["head"]["pull_request"]["repository_scoped_number"] = "9999"


def _break_role_assignment(payload: dict[str, Any]) -> None:
    payload["change_set"]["head"]["role_assignment"]["role"] = "base"


def _break_distinct_revisions(payload: dict[str, Any]) -> None:
    payload["change_set"]["head"]["role_assignment"]["revision"] = payload[
        "change_set"
    ]["base"]["role_assignment"]["revision"]


def _break_unique_paths(payload: dict[str, Any]) -> None:
    paths = payload["change_set"]["changed_paths"]
    paths[1]["path"] = paths[0]["path"]


def _break_empty_paths(payload: dict[str, Any]) -> None:
    payload["change_set"]["changed_paths"] = []


@pytest.mark.parametrize(
    ("label", "mutate"),
    (
        pytest.param("two pull requests", _break_same_pull_request, id="two-prs"),
        pytest.param("wrong head role", _break_role_assignment, id="head-role"),
        pytest.param("same revision", _break_distinct_revisions, id="same-revision"),
        pytest.param("repeated path", _break_unique_paths, id="repeated-path"),
        pytest.param("no changed paths", _break_empty_paths, id="empty-paths"),
    ),
)
def test_an_invalid_p05_change_set_still_fails_its_own_published_rules(
    label: str,
    mutate: Any,
) -> None:
    """S05 redefines no base, head, or path semantics; P05 still decides."""
    payload = _payload(_change_set_association())
    mutate(payload)
    change_set_json = json.dumps(payload["change_set"])

    with pytest.raises(ValidationError):
        PullRequestChangeSet.model_validate_json(change_set_json)
    with pytest.raises(ValidationError) as failure:
        FaultRepairCandidateChangeSetAssociation.model_validate_json(
            json.dumps(payload)
        )

    assert {path[0] for path, _ in _failures(failure.value)} == {"change_set"}, label


def test_a_change_set_association_creates_no_evidence_or_completeness_field() -> None:
    association = _change_set_association()
    payload = _payload(association)

    assert set(payload["change_set"]) == {"base", "head", "changed_paths"}
    for absent in (
        "evidence",
        "evidence_record",
        "support",
        "affected_paths",
        "affected",
        "complete",
        "completeness",
        "provider_complete",
        "base_objects",
        "verified",
    ):
        assert absent not in payload
        assert absent not in payload["change_set"]


def test_the_change_set_stays_excluded_from_the_s04_and_p05_relations() -> None:
    """S05 consumes it under its own relation and moves no other boundary."""
    change_set = _change_set()

    with pytest.raises(ValidationError):
        FaultReportHistoryFactAssociation(
            report=_report(), history_fact=cast(Any, change_set)
        )
    with pytest.raises(ValidationError) as failure:
        PullRequestHistoryFactEvidenceLink(
            fact=cast(Any, change_set),
            evidence_record=_evidence_record(),
        )

    # A valid record is supplied so that `fact` is the only ground on which
    # this can fail; `evidence_record=None` would raise whatever the union
    # admitted, and would pass even if the change set were admissible.
    assert {path[0] for path, _ in _failures(failure.value)} == {"fact"}
    assert _change_set_association(change_set=change_set).change_set == change_set


def test_a_change_set_from_another_repository_is_admitted() -> None:
    """The change set's pull request need not sit in the report's repository."""
    association = _change_set_association(
        change_set=_change_set(repository=OTHER_REPOSITORY_ID)
    )

    assert association.change_set.head.pull_request.repository_identity == _repository(
        OTHER_REPOSITORY_ID
    )
    assert association.candidate.report.context.repository == _repository()
    assert (
        FaultRepairCandidateChangeSetAssociation.model_validate_json(
            association.model_dump_json()
        )
        == association
    )


# --- cross-association counterexamples -----------------------------------------


def test_a_candidate_existing_does_not_imply_a_revision_or_change_set() -> None:
    candidate = _candidate()

    assert set(_payload(candidate)) == set(CANDIDATE_FIELDS)
    assert "revision" not in SuppliedFaultRepairCandidate.model_fields
    assert "change_set" not in SuppliedFaultRepairCandidate.model_fields
    # The proposal is a complete value; the two associations are separate ones.
    assert FaultRepairCandidateRevisionAssociation.model_fields[
        "revision"
    ].is_required()
    assert FaultRepairCandidateChangeSetAssociation.model_fields[
        "change_set"
    ].is_required()


def test_a_revision_association_is_not_a_verified_fix() -> None:
    association = _revision_association(revision=_commit(RETAINED_MERGE_REVISION))

    assert set(association.model_fields_set) == set(REVISION_FIELDS)
    assert not hasattr(association, "verified")
    assert not hasattr(association, "fixed")
    # Two candidates may name the same merge revision; neither becomes correct.
    other = _revision_association(
        candidate=_candidate(candidate=SECOND_CANDIDATE),
        revision=_commit(RETAINED_MERGE_REVISION),
    )
    assert other != association
    assert other.revision == association.revision


def test_a_change_set_association_is_not_a_complete_diff() -> None:
    partial = _change_set_association(change_set=_change_set(paths=1))
    full = _change_set_association(change_set=_change_set(paths=3))

    assert len(partial.change_set.changed_paths) == 1
    assert len(full.change_set.changed_paths) == 3
    # Both are equally valid: nothing says how many paths a repair needs.
    assert partial != full
    assert partial.candidate == full.candidate
    assert "complete" not in _payload(partial)


def test_a_change_set_head_does_not_assert_repair_correctness() -> None:
    association = _change_set_association()
    head = association.change_set.head.role_assignment.revision

    assert head == _commit(RETAINED_HEAD_REVISION)
    assert not hasattr(association, "correct")
    for absent in ("correct", "correctness", "repaired", "merged"):
        assert absent not in _payload(association)


def test_the_same_repair_statement_does_not_make_one_candidate() -> None:
    first = _candidate(candidate=SUPPLIED_CANDIDATE)
    second = _candidate(candidate=SECOND_CANDIDATE)

    assert first.repair_statement == second.repair_statement
    assert first != second


def test_the_same_revision_does_not_make_one_candidate() -> None:
    revision = _commit()
    first = _revision_association(
        candidate=_candidate(candidate=SUPPLIED_CANDIDATE), revision=revision
    )
    second = _revision_association(
        candidate=_candidate(candidate=SECOND_CANDIDATE), revision=revision
    )

    assert first.revision == second.revision
    assert first.candidate != second.candidate
    assert first != second


def test_no_coherence_is_required_between_a_revision_and_a_change_set() -> None:
    """An associated revision need not equal the change set's head revision."""
    candidate = _candidate()
    change_set = _change_set()
    head = change_set.head.role_assignment.revision

    for digest in (
        INTERMEDIATE_REVISION,
        RETAINED_MERGE_REVISION,
        RETAINED_HEAD_REVISION,
    ):
        revision = _commit(digest)
        by_revision = _revision_association(candidate=candidate, revision=revision)
        by_change_set = _change_set_association(
            candidate=candidate, change_set=change_set
        )

        assert by_revision.candidate == by_change_set.candidate
        assert by_revision.revision == revision
        assert by_change_set.change_set.head.role_assignment.revision == head

    # The mismatching case is admitted exactly as the matching one is.
    assert _commit(INTERMEDIATE_REVISION) != head


def test_a_pull_request_association_and_a_change_set_compose_into_no_third_claim() -> (
    None
):
    """`S1.P06.S04` report-to-source and S05 candidate-to-change-set stay apart."""
    candidate = _candidate()
    association = _change_set_association(candidate=candidate)

    assert "source_object" not in FaultRepairCandidateChangeSetAssociation.model_fields
    assert "report" not in FaultRepairCandidateChangeSetAssociation.model_fields
    assert association.candidate.report == _report()
    # Reaching the pull request goes through the embedded P05 value only, which
    # is predecessor containment this module neither creates nor extends.
    assert (
        association.change_set.head.pull_request.repository_scoped_number
        == RepositoryScopedNumber(RETAINED_PULL_REQUEST_NUMBER)
    )


def test_no_published_model_relates_a_candidate_to_a_source_object() -> None:
    for model in _published_models():
        for name, field in model.model_fields.items():
            annotation = str(field.annotation)
            assert "SourceObjectIdentity" not in annotation, (model.__name__, name)


# --- the module's own surface and boundaries ------------------------------------


def test_the_module_publishes_exactly_four_symbols_in_order() -> None:
    assert repair_module.__all__ == EXPECTED_EXPORTS
    assert [
        node.name for node in ast.walk(_repair_tree()) if isinstance(node, ast.ClassDef)
    ] == EXPECTED_EXPORTS


DECLARED_VALIDATORS = (
    "_require_typed_python_candidate",
    "_require_typed_python_report",
    "_require_unpadded_text",
    "_require_typed_python_candidate",
    "_require_typed_python_revision",
    "_require_typed_python_candidate",
    "_require_typed_python_change_set",
)


def test_the_module_defines_only_the_declared_validators() -> None:
    """A derivation or a helper added anywhere in the module must fail here.

    `__all__` and the class-name list pin what is exported, not what exists: a
    classmethod deriving a candidate identity from a report, or any other
    function, changes neither and would otherwise be invisible.
    """
    functions = [
        node.name
        for node in ast.walk(_repair_tree())
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)
    ]

    assert tuple(functions) == DECLARED_VALIDATORS
    for name in functions:
        assert name.startswith("_")
        assert name not in repair_module.__all__


@pytest.mark.parametrize("model", _published_models(), ids=lambda m: m.__name__)
def test_no_record_publishes_an_attribute_beyond_its_fields(
    model: type[BaseModel],
) -> None:
    """An outcome claim may not arrive as a property or method either.

    Pydantic fields are not class attributes, so a clean value model adds no
    public name of its own. A `merged` or `regression_free` property would
    leave `model_fields` and the JSON payload untouched while still being
    reachable on the record.
    """
    beyond = {name for name in dir(model) if not name.startswith("_")} - set(
        dir(BaseModel)
    )

    assert beyond == set(), model.__name__
    assert model.model_computed_fields == {}


def test_the_candidate_identity_publishes_no_attribute_beyond_its_root() -> None:
    beyond = {
        name for name in dir(FaultRepairCandidateIdentity) if not name.startswith("_")
    } - set(dir(RootModel))

    assert beyond == set()
    assert FaultRepairCandidateIdentity.model_computed_fields == {}


def test_the_module_is_not_re_exported_from_the_package_or_domain_root() -> None:
    assert faultatlas.__all__ == ["__version__"]
    assert not hasattr(faultatlas.domain, "__all__")
    for symbol in EXPECTED_EXPORTS:
        assert not hasattr(faultatlas, symbol)
        assert not hasattr(faultatlas.domain, symbol)


def test_the_module_imports_only_its_declared_predecessors() -> None:
    imported = {
        alias.name if isinstance(node, ast.Import) else cast(str, node.module)
        for node in ast.walk(_repair_tree())
        if isinstance(node, ast.Import | ast.ImportFrom)
        for alias in node.names
    }

    # An exact set: the evidence layer, the S1.P06.S04 bridge and every other
    # module are excluded by this equality rather than by a name list.
    assert imported == {
        "uuid",
        "typing",
        "pydantic",
        "faultatlas.domain.fault",
        "faultatlas.domain.history",
        "faultatlas.domain.revision",
    }


def test_the_module_performs_no_io() -> None:
    called = {
        node.func.id
        for node in ast.walk(_repair_tree())
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }

    assert not called & {"open", "eval", "exec", "compile", "__import__", "print"}
    body = " ".join(
        REPAIR_SOURCE.read_text(encoding="utf-8").split('"""', 2)[-1].split()
    )
    for forbidden in ("import os", "import io", "Path(", "requests", "urllib", "now("):
        assert forbidden not in body, forbidden


@pytest.mark.parametrize(
    "relative",
    (
        "src/faultatlas/domain/fault.py",
        "src/faultatlas/domain/fault_interpretation.py",
        "src/faultatlas/domain/fault_source_relationship.py",
        "src/faultatlas/domain/fault_test.py",
        "src/faultatlas/domain/history.py",
        "src/faultatlas/domain/revision.py",
    ),
)
def test_no_predecessor_production_module_imports_this_one(relative: str) -> None:
    source = (REPOSITORY_ROOT / relative).read_text(encoding="utf-8")

    assert "fault_repair" not in source
    for symbol in EXPECTED_EXPORTS:
        assert symbol not in source


def test_the_tracked_production_inventory_is_twenty_three_modules() -> None:
    tracked = subprocess.run(  # noqa: S603 - literal argv, no shell
        ["git", "ls-files", "src/"],
        cwd=REPOSITORY_ROOT,
        capture_output=True,
        check=False,
    )
    assert tracked.returncode == 0, tracked.stderr
    observed = sorted(tracked.stdout.decode("utf-8").split())

    assert observed == [f"src/{name}" for name in EXPECTED_PRODUCTION_MODULES]
    assert len(observed) == 23
    assert "src/faultatlas/domain/fault_repair.py" in observed


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

    assert "`S1.P06` is complete" in section
    for index in range(1, 13):
        assert f"`S1.P06.S{index:02d}` is complete" in section, index
    assert "`S1.P06.S11` is complete" in section
    assert "`S1.P06.S12` is complete" in section
    assert "`S1.P07` is active and incomplete" in section
    assert "`S1.P07.S01` is complete" in section
    assert "`S1.P07.S04` is next and not started" in section
    assert "`S1.P08` through `S1.P10` remain not started" in section

    # Nothing beyond the Phase's twelve Slices may be claimed, and no Slice is
    # still a gate now that the Phase is closed.
    assert "`S1.P06.S13`" not in section
    for index in range(1, 13):
        assert f"`S1.P06.S{index:02d}` is next and not started" not in section, index
    assert "`S1.P07` is complete" not in section
    # `S1.P07.S01` began the Phase, so the phase-level gate is superseded by
    # the Slice gate above.
    assert "`S1.P07` is next and not started" not in section
    assert "`S1.P06` is `eligible_to_begin`" not in section


def test_the_roadmap_carries_exactly_one_live_gate() -> None:
    roadmap = _roadmap()

    live_next = re.findall(
        r"`(S1\.P\d\d(?:\.S\d\d)?)` is next and not started", roadmap
    )
    assert live_next, "the roadmap names no next gate"
    # `S1.P07.S01` moved the gate from the Phase to its first Slice: `S1.P07`
    # has begun, so the single live gate is now `S1.P07.S04`.
    assert set(live_next) == {"S1.P07.S04"}, sorted(set(live_next))
    live_phases = re.findall(r"`(S1\.P\d\d)` is active and incomplete", roadmap)
    # Exactly one Phase is now active, and it is the one that just began.
    assert set(live_phases) == {"S1.P07"}, sorted(set(live_phases))
    for line in ROADMAP.read_text(encoding="utf-8").splitlines():
        if "next and not started" in line:
            assert "`S1.P07.S04`" in line, line


def test_the_roadmap_records_the_p06_s05_transition() -> None:
    raw = ROADMAP.read_text(encoding="utf-8")
    roadmap = _roadmap()
    mapping = roadmap.split("## Current-code mapping", 1)
    assert len(mapping) == 2, "roadmap must retain a current-code mapping section"
    current = mapping[1]

    assert "`S1.P06.S05` is complete" in roadmap
    assert "`S1.P06.S06` is complete" in roadmap
    assert "`S1.P06.S07` is complete" in roadmap
    assert "`S1.P06.S08` is complete" in roadmap
    assert "`S1.P06.S09` is complete" in roadmap
    assert "`S1.P06.S10` is complete" in roadmap
    assert "`S1.P06.S11` is complete" in roadmap
    assert "`S1.P06.S12` is complete" in roadmap
    current_status = roadmap.split("## Current status", 1)[1].split("## ", 1)[0]
    assert "`S1.P07.S04` is next and not started" in current_status
    assert (
        "`S1.P06.S05` — Repair Candidates and Concrete Repair Associations "
        "(complete)" in roadmap
    )
    assert (
        "`S1.P06.S06` — Test Material, Reported Runs, Outcomes, and "
        "Comparability (complete)" in roadmap
    )
    assert "The `S1.P06` route is closed at `S1.P06.S12`." in roadmap

    assert "faultatlas.domain.fault_repair" in current
    for symbol in EXPECTED_EXPORTS:
        assert f"`{symbol}`" in current
    assert "Production Python sources are 23." in current
    assert "`candidate.report.context.fault`" in roadmap

    # The superseded live gate and provisional S05 title must be retired.
    assert "`S1.P06.S05` is next and not started" not in roadmap
    assert "`S1.P06.S05` — Repair candidates (next, not started)" not in roadmap
    assert "The `S1.P06` route is closed at `S1.P06.S07`." not in roadmap
    assert "The `S1.P06` route is closed at `S1.P06.S09`." not in roadmap
    assert "`S1.P06.S10` is next and not started" not in roadmap
    assert "`S1.P07` is complete" not in roadmap
    # `S1.P07.S01` began the Phase and added one production module, so the
    # phase-level gate and the count this file used to read are both
    # superseded and must be gone.
    assert "`S1.P07` is next and not started" not in roadmap
    assert "Production Python sources are 16." not in roadmap
    assert "Production Python sources are 20." not in roadmap
    assert "- **S1.P06 — Fault Instance Model**" not in raw


def test_the_roadmap_states_the_s05_decisions_and_non_claims() -> None:
    roadmap = _roadmap()

    assert "production Python sources move from 15 to 16" in roadmap
    assert "A repair candidate is a proposal, not an outcome." in roadmap
    assert "It requires no scenario and no occurrence" in roadmap
    assert "it requires no root cause either" in roadmap
    assert "A candidate is complete without any implementation." in roadmap
    assert "claims no repository membership" in roadmap
    assert "deliberately consumes the `S1.P05` `PullRequestChangeSet`" in roadmap
    assert "The `S1.P05.S07` evidence boundary is untouched." in roadmap
    assert "No coherence calculus over several associations exists." in roadmap
    assert "adds no candidate-to-source-object relation" in roadmap
    assert "identical repair prose does not merge them" in roadmap
    assert "none is an identity of another" in roadmap


def test_the_roadmap_preserves_the_predecessor_history_as_written() -> None:
    roadmap = _roadmap()

    assert (
        "`S1.P06.S01` publishes one new production module, `faultatlas.domain.fault`, "
        "whose initial `__all__` is exactly `FaultInstanceIdentity` and "
        "`FaultRepositoryContext`." in roadmap
    )
    assert "so production Python sources remain 14" in roadmap
    assert "production Python sources move from 14 to 15" in roadmap
    assert "`S1.P06` was `eligible_to_begin`" in roadmap
    assert "`S1.P05` is complete" in roadmap


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

import faultatlas.domain.fault_repair as repair_module
from faultatlas.domain.fault import (
    FaultInstanceIdentity,
    FaultReportIdentity,
    FaultRepositoryContext,
    SuppliedFaultReport,
)
from faultatlas.domain.fault_repair import (
    FaultRepairCandidateChangeSetAssociation,
    FaultRepairCandidateIdentity,
    FaultRepairCandidateRevisionAssociation,
    SuppliedFaultRepairCandidate,
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

module = Path(repair_module.__file__).resolve()
assert module.is_relative_to(installed), module
assert not module.is_relative_to(checkout), module
assert repair_module.__all__ == [
    "FaultRepairCandidateIdentity",
    "SuppliedFaultRepairCandidate",
    "FaultRepairCandidateRevisionAssociation",
    "FaultRepairCandidateChangeSetAssociation",
]

repository = RepositoryIdentity(
    provider=ProviderKey("github"),
    provider_repository_id=ProviderRepositoryId(os.environ["REPOSITORY_ID"]),
)
report = SuppliedFaultReport(
    report=FaultReportIdentity(uuid.UUID(os.environ["REPORT_UUID"])),
    context=FaultRepositoryContext(
        fault=FaultInstanceIdentity(uuid.UUID(os.environ["FAULT_UUID"])),
        repository=repository,
    ),
    problem_statement=os.environ["PROBLEM_STATEMENT"],
    behavioral_deviation=os.environ["BEHAVIORAL_DEVIATION"],
)
candidate = SuppliedFaultRepairCandidate(
    candidate=FaultRepairCandidateIdentity(uuid.UUID(os.environ["CANDIDATE_UUID"])),
    report=report,
    repair_statement=os.environ["REPAIR_STATEMENT"],
)


def commit(digest):
    return GitCommitIdentity(
        kind=GitObjectKind.COMMIT,
        algorithm=GitHashAlgorithm.SHA1,
        full_digest=digest,
    )


pull_request = NumberedSourceObjectIdentity(
    repository_identity=repository,
    kind=SourceObjectKind.PULL_REQUEST,
    repository_scoped_number=RepositoryScopedNumber(os.environ["PULL_REQUEST_NUMBER"]),
)


def binding(role, digest):
    return PullRequestRevisionRoleBinding(
        pull_request=pull_request,
        role_assignment=RevisionRoleAssignment(role=role, revision=commit(digest)),
    )


change_set = PullRequestChangeSet(
    base=binding(RevisionRole.BASE, os.environ["BASE_REVISION"]),
    head=binding(RevisionRole.HEAD, os.environ["HEAD_REVISION"]),
    changed_paths=(
        PullRequestChangedPath(
            path=GitRepositoryPath(os.environ["CHANGED_PATH"]),
            head_object=GitBlobIdentity(
                kind=GitObjectKind.BLOB,
                algorithm=GitHashAlgorithm.SHA1,
                full_digest=os.environ["CHANGED_BLOB"],
            ),
            status=ChangedPathStatus.ADDED,
        ),
    ),
)
revision_association = FaultRepairCandidateRevisionAssociation(
    candidate=candidate, revision=commit(os.environ["HEAD_REVISION"])
)
change_set_association = FaultRepairCandidateChangeSetAssociation(
    candidate=candidate, change_set=change_set
)

for value, model in (
    (candidate, SuppliedFaultRepairCandidate),
    (revision_association, FaultRepairCandidateRevisionAssociation),
    (change_set_association, FaultRepairCandidateChangeSetAssociation),
):
    assert model.model_validate_json(value.model_dump_json()) == value

print(
    json.dumps(
        {
            "module": str(module),
            "identity": FaultRepairCandidateIdentity(
                uuid.UUID(os.environ["CANDIDATE_UUID"])
            ).model_dump_json(),
            "candidate": candidate.model_dump_json(),
            "revision": revision_association.model_dump_json(),
            "change_set": change_set_association.model_dump_json(),
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

    root = tmp_path_factory.mktemp("repair-candidate-package")
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


# Added by `S1.P07.S01`, the first `S1.P07` production module.
PATTERN_MODULE = "faultatlas/domain/pattern.py"
# Added by `S1.P07.S02`, after the sealed predecessor inventories.
PATTERN_EXEMPLAR_MODULE = "faultatlas/domain/pattern_exemplar.py"
# Added by `S1.P07.S03`; sealed predecessor inventories remain unchanged.
INVARIANT_MODULE = "faultatlas/domain/invariant.py"

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
    INVARIANT_MODULE,
    PATTERN_MODULE,
    PATTERN_EXEMPLAR_MODULE,
    "faultatlas/domain/revision.py",
    "faultatlas/domain/snapshot.py",
    "faultatlas/domain/snapshot_evidence_link.py",
    "faultatlas/domain/source.py",
]


def test_the_wheel_ships_the_repair_module_and_no_corpus_or_test_material(
    offline_distributions: tuple[Path, Path],
) -> None:
    wheel, _ = offline_distributions
    with zipfile.ZipFile(wheel) as archive:
        names = tuple(info.filename for info in archive.infolist() if not info.is_dir())

    modules = sorted(name for name in names if name.endswith(".py"))
    assert modules == EXPECTED_PRODUCTION_MODULES
    assert len(modules) == 23
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


def test_the_sdist_ships_the_repair_module_and_no_corpus_or_test_material(
    offline_distributions: tuple[Path, Path],
) -> None:
    _, sdist = offline_distributions
    with tarfile.open(sdist, "r:gz") as archive:
        names = tuple(member.name for member in archive.getmembers() if member.isfile())

    modules = sorted(
        name.split("/src/", 1)[1] for name in names if name.endswith(".py")
    )
    assert modules == EXPECTED_PRODUCTION_MODULES
    assert len(modules) == 23
    assert "faultatlas/domain/fault_repair.py" in modules
    for name in names:
        parts = Path(name).parts
        assert "reference_corpus" not in parts
        assert "tests" not in parts
        assert "docs" not in parts


def test_the_installed_wheel_exercises_all_four_new_symbols(
    offline_distributions: tuple[Path, Path],
    tmp_path: Path,
) -> None:
    """All four S05 symbols must run from the wheel copy, not the checkout."""
    wheel, _ = offline_distributions
    installed = tmp_path / "installed"
    installed.mkdir()
    with zipfile.ZipFile(wheel) as archive:
        archive.extractall(installed)

    assert (installed / "faultatlas/domain/fault_repair.py").is_file()

    path, blob, _ = RETAINED_CHANGED_PATHS[0]
    environment = os.environ.copy()
    environment.update(
        {
            "INSTALLED_ROOT": str(installed),
            "CHECKOUT_SOURCE_ROOT": str(CHECKOUT_SOURCE_ROOT),
            "FAULT_UUID": SUPPLIED_FAULT_TEXT,
            "REPORT_UUID": SUPPLIED_REPORT_TEXT,
            "CANDIDATE_UUID": SUPPLIED_CANDIDATE_TEXT,
            "REPOSITORY_ID": RETAINED_REPOSITORY_ID,
            "PULL_REQUEST_NUMBER": RETAINED_PULL_REQUEST_NUMBER,
            "BASE_REVISION": RETAINED_BASE_REVISION,
            "HEAD_REVISION": RETAINED_HEAD_REVISION,
            "CHANGED_PATH": path,
            "CHANGED_BLOB": blob,
            "PROBLEM_STATEMENT": PROBLEM_STATEMENT,
            "BEHAVIORAL_DEVIATION": BEHAVIORAL_DEVIATION,
            "REPAIR_STATEMENT": REPAIR_STATEMENT,
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
    reported: dict[str, str] = json.loads(result.stdout.strip().splitlines()[-1])
    assert Path(reported["module"]).is_relative_to(installed)
    assert not Path(reported["module"]).is_relative_to(CHECKOUT_SOURCE_ROOT)
    assert json.loads(reported["identity"]) == SUPPLIED_CANDIDATE_TEXT
    assert json.loads(reported["candidate"]) == _payload(_candidate())
    assert json.loads(reported["revision"]) == _payload(_revision_association())
    assert json.loads(reported["change_set"]) == _payload(
        _change_set_association(change_set=_change_set(paths=1))
    )
