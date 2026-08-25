from __future__ import annotations

import ast
import json
from datetime import datetime
from pathlib import Path
from typing import Any, cast, get_args

import pytest
from pydantic import BaseModel, BeforeValidator, ConfigDict, ValidationError

import faultatlas.domain.history_evidence_link as link_module
from faultatlas.domain.evidence import (
    ArtifactByteLength,
    ArtifactSha256Digest,
    DurableEvidenceRecordReference,
    EvidenceCanonicalization,
    EvidenceRecordFormat,
    EvidenceVersion,
)
from faultatlas.domain.history import (
    ChangedPathStatus,
    PullRequestChangedPath,
    PullRequestChangeSet,
    PullRequestHeadRefDeletion,
    PullRequestHistoricalOccurrenceTime,
    PullRequestMergeRevisionOutcome,
    PullRequestReviewRevisionApproval,
    PullRequestRevisionRoleBinding,
)
from faultatlas.domain.history_evidence_link import PullRequestHistoryFactEvidenceLink
from faultatlas.domain.identity import (
    NumberedSourceObjectIdentity,
    ProviderGlobalId,
    ProviderKey,
    ProviderRepositoryId,
    ProviderScopedSourceObjectIdentity,
    RepositoryIdentity,
    RepositoryScopedNumber,
    SourceObjectKind,
)
from faultatlas.domain.revision import (
    GitBlobIdentity,
    GitCommitIdentity,
    GitHashAlgorithm,
    GitObjectKind,
    GitRefName,
    GitRepositoryPath,
    RevisionRole,
    RevisionRoleAssignment,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
LINK_SOURCE = REPOSITORY_ROOT / "src/faultatlas/domain/history_evidence_link.py"
HISTORY_SOURCE = REPOSITORY_ROOT / "src/faultatlas/domain/history.py"
EVIDENCE_SOURCE = REPOSITORY_ROOT / "src/faultatlas/domain/evidence.py"

CANONICAL_PROVIDER = "github"
CANONICAL_REPOSITORY_ID = "37489525"
CANONICAL_PULL_REQUEST_NUMBER = "4414"
CANONICAL_REVIEW_GLOBAL_ID = "176071572"
CANONICAL_BASE_REVISION = "4c9cde74ab40027b5761ab9e002af116a4a20df3"
CANONICAL_HEAD_REVISION = "690a63b9218f72662cd3a67c6c200b758c88ce12"
CANONICAL_MERGE_REVISION = "10cdae8e38ec448b7133cf163dca587ad806d262"
CANONICAL_HEAD_REF_NAME = "starred_with_side_effect"

# The three retained changed paths, in retained source order.
CANONICAL_CHANGED_PATHS = (
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

CANONICAL_APPROVAL_INSTANT = "2018-11-17T23:54:20Z"
CANONICAL_MERGE_INSTANT = "2018-11-18T00:17:25Z"
CANONICAL_DELETION_INSTANT = "2018-11-18T00:17:28Z"

# The retained acquisition record. Every canonical association below names this
# one record: the retained material carries all eleven facts inside it.
CANONICAL_RECORD_FORMAT = "faultatlas-acquisition"
CANONICAL_RECORD_VERSION = "1"
CANONICAL_RECORD_CANONICALIZATION = "json-sort-keys-compact-utf8-lf-v1"
CANONICAL_RECORD_SHA256 = (
    "1c29093bf1537e9b824a18df1848b71a8da014f544bc9f385707eb0e000a1318"
)
CANONICAL_RECORD_LENGTH = 61_283
# The retained additive correction. It is a second record a caller may name,
# never a record this relation follows on its own.
CANONICAL_CORRECTION_FORMAT = "faultatlas-pytest-4412-acquisition-closure-addendum"
CANONICAL_CORRECTION_SHA256 = (
    "44491ee512d2c2022110b83967fb6fa86d13045bc8404ea490d7a08b7aef24a2"
)
CANONICAL_CORRECTION_LENGTH = 60_832

FORBIDDEN_LINK_IDENTIFIERS = (
    "artifact",
    "authoritative",
    "byte_span",
    "confidence",
    "corroborated",
    "correct",
    "derived",
    "envelope",
    "evidence_records",
    "field_path",
    "json_pointer",
    "locator",
    "pointer",
    "primary",
    "proven",
    "request_id",
    "review_state",
    "semantic_field",
    "semantic_path",
    "strength",
    "status",
    "superseded",
    "support_role",
    "verified",
)

EXCLUDED_PUBLISHED_SYMBOLS = ("PullRequestChangeSet", "ChangedPathStatus")


def _repository() -> RepositoryIdentity:
    return RepositoryIdentity(
        provider=ProviderKey(CANONICAL_PROVIDER),
        provider_repository_id=ProviderRepositoryId(CANONICAL_REPOSITORY_ID),
    )


def _pull_request() -> NumberedSourceObjectIdentity:
    return NumberedSourceObjectIdentity(
        repository_identity=_repository(),
        kind=SourceObjectKind.PULL_REQUEST,
        repository_scoped_number=RepositoryScopedNumber(CANONICAL_PULL_REQUEST_NUMBER),
    )


def _commit(full_digest: str = CANONICAL_HEAD_REVISION) -> GitCommitIdentity:
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


def _binding(
    role: RevisionRole = RevisionRole.HEAD,
    full_digest: str = CANONICAL_HEAD_REVISION,
) -> PullRequestRevisionRoleBinding:
    return PullRequestRevisionRoleBinding(
        pull_request=_pull_request(),
        role_assignment=RevisionRoleAssignment(
            role=role, revision=_commit(full_digest)
        ),
    )


def _changed_path(index: int = 0) -> PullRequestChangedPath:
    path, blob, status = CANONICAL_CHANGED_PATHS[index]
    return PullRequestChangedPath(
        path=GitRepositoryPath(path),
        head_object=_blob(blob),
        status=ChangedPathStatus(status),
    )


def _approval() -> PullRequestReviewRevisionApproval:
    return PullRequestReviewRevisionApproval(
        review=ProviderScopedSourceObjectIdentity(
            kind=SourceObjectKind.PULL_REQUEST_REVIEW,
            provider_global_id=ProviderGlobalId(CANONICAL_REVIEW_GLOBAL_ID),
            parent=_pull_request(),
        ),
        approved_revision=_commit(),
    )


def _outcome() -> PullRequestMergeRevisionOutcome:
    return PullRequestMergeRevisionOutcome(
        pull_request=_pull_request(),
        merge_revision=_commit(CANONICAL_MERGE_REVISION),
    )


def _deletion() -> PullRequestHeadRefDeletion:
    return PullRequestHeadRefDeletion(
        head=_binding(),
        head_ref_name=GitRefName(CANONICAL_HEAD_REF_NAME),
    )


def _instant(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _occurrence_time(
    occurrence: (
        PullRequestReviewRevisionApproval
        | PullRequestMergeRevisionOutcome
        | PullRequestHeadRefDeletion
    ),
    instant: str,
) -> PullRequestHistoricalOccurrenceTime:
    return PullRequestHistoricalOccurrenceTime(
        occurrence=occurrence,
        occurred_at=_instant(instant),
    )


def _change_set() -> PullRequestChangeSet:
    return PullRequestChangeSet(
        base=_binding(RevisionRole.BASE, CANONICAL_BASE_REVISION),
        head=_binding(),
        changed_paths=tuple(
            _changed_path(index) for index in range(len(CANONICAL_CHANGED_PATHS))
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


def _synthetic_record() -> DurableEvidenceRecordReference:
    return DurableEvidenceRecordReference(
        format_name=EvidenceRecordFormat("synthetic-history-record"),
        format_version=EvidenceVersion("1"),
        canonicalization=EvidenceCanonicalization("synthetic-json-v1"),
        sha256=ArtifactSha256Digest(f"{1001:064x}"),
        byte_length=ArtifactByteLength(1),
    )


def _link(
    fact: Any,
    record: DurableEvidenceRecordReference | None = None,
) -> PullRequestHistoryFactEvidenceLink:
    return PullRequestHistoryFactEvidenceLink(
        fact=fact,
        evidence_record=_record() if record is None else record,
    )


def _canonical_facts() -> tuple[Any, ...]:
    """The eleven canonical P05 facts the retained acquisition record carries."""
    return (
        _binding(RevisionRole.BASE, CANONICAL_BASE_REVISION),
        _binding(),
        *(_changed_path(index) for index in range(len(CANONICAL_CHANGED_PATHS))),
        _approval(),
        _outcome(),
        _deletion(),
        _occurrence_time(_approval(), CANONICAL_APPROVAL_INSTANT),
        _occurrence_time(_outcome(), CANONICAL_MERGE_INSTANT),
        _occurrence_time(_deletion(), CANONICAL_DELETION_INSTANT),
    )


def _payload(link: PullRequestHistoryFactEvidenceLink) -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(link.model_dump_json()))


# --- canonical associations ---------------------------------------------------


def test_the_canonical_base_and_head_bindings_associate_with_the_record() -> None:
    for role, revision in (
        (RevisionRole.BASE, CANONICAL_BASE_REVISION),
        (RevisionRole.HEAD, CANONICAL_HEAD_REVISION),
    ):
        link = _link(_binding(role, revision))

        assert isinstance(link.fact, PullRequestRevisionRoleBinding)
        assert link.fact.role_assignment.role is role
        assert link.fact.role_assignment.revision.full_digest == revision
        assert link.evidence_record.sha256.root == CANONICAL_RECORD_SHA256
        assert link.evidence_record.byte_length.root == CANONICAL_RECORD_LENGTH


@pytest.mark.parametrize("index", range(len(CANONICAL_CHANGED_PATHS)))
def test_each_canonical_changed_path_associates_with_the_record(index: int) -> None:
    path, blob, status = CANONICAL_CHANGED_PATHS[index]
    link = _link(_changed_path(index))

    assert isinstance(link.fact, PullRequestChangedPath)
    assert link.fact.path.root == path
    assert link.fact.head_object.full_digest == blob
    assert link.fact.status == status
    assert link.evidence_record == _record()


def test_the_canonical_review_approval_associates_with_the_record() -> None:
    link = _link(_approval())

    assert isinstance(link.fact, PullRequestReviewRevisionApproval)
    assert link.fact.review.provider_global_id.root == CANONICAL_REVIEW_GLOBAL_ID
    assert link.fact.approved_revision.full_digest == CANONICAL_HEAD_REVISION


def test_the_canonical_merge_outcome_associates_with_the_record() -> None:
    link = _link(_outcome())

    assert isinstance(link.fact, PullRequestMergeRevisionOutcome)
    assert link.fact.merge_revision.full_digest == CANONICAL_MERGE_REVISION


def test_the_canonical_head_ref_deletion_associates_with_the_record() -> None:
    link = _link(_deletion())

    assert isinstance(link.fact, PullRequestHeadRefDeletion)
    assert link.fact.head_ref_name.root == CANONICAL_HEAD_REF_NAME


@pytest.mark.parametrize(
    ("occurrence", "instant"),
    (
        (_approval(), CANONICAL_APPROVAL_INSTANT),
        (_outcome(), CANONICAL_MERGE_INSTANT),
        (_deletion(), CANONICAL_DELETION_INSTANT),
    ),
)
def test_each_canonical_occurrence_time_associates_with_the_record(
    occurrence: Any,
    instant: str,
) -> None:
    link = _link(_occurrence_time(occurrence, instant))

    assert isinstance(link.fact, PullRequestHistoricalOccurrenceTime)
    assert link.fact.occurred_at == _instant(instant)
    assert link.fact.occurrence == occurrence
    assert link.evidence_record == _record()


def test_all_eleven_canonical_facts_associate_with_the_same_record() -> None:
    record = _record()
    links = tuple(_link(fact, record) for fact in _canonical_facts())

    assert len(links) == 11
    assert all(link.evidence_record == record for link in links)
    assert len(set(links)) == 11


def test_one_record_carrying_eleven_facts_is_eleven_links_not_an_aggregate() -> None:
    links = tuple(_link(fact) for fact in _canonical_facts())

    records = {link.evidence_record.model_dump_json() for link in links}
    facts = {json.dumps(_payload(link)["fact"], sort_keys=True) for link in links}

    assert len(records) == 1
    assert len(facts) == 11
    assert not hasattr(links[0], "evidence_records")


# --- synthetic associations ---------------------------------------------------


@pytest.mark.parametrize(
    "fact",
    (
        _binding(),
        _changed_path(),
        _approval(),
        _outcome(),
        _deletion(),
        _occurrence_time(_approval(), CANONICAL_APPROVAL_INSTANT),
    ),
)
def test_every_admitted_family_associates_with_a_synthetic_record(fact: Any) -> None:
    link = _link(fact, _synthetic_record())

    assert link.fact == fact
    assert link.evidence_record.format_name.root == "synthetic-history-record"


# --- one record per link ------------------------------------------------------


def test_one_fact_with_two_records_yields_two_distinct_links() -> None:
    fact = _approval()
    acquisition = _link(fact, _record())
    correction = _link(fact, _correction_record())

    assert acquisition != correction
    assert acquisition.fact == correction.fact
    assert acquisition.evidence_record != correction.evidence_record


def test_one_record_with_two_facts_yields_two_distinct_links() -> None:
    record = _record()
    first = _link(_approval(), record)
    second = _link(_outcome(), record)

    assert first != second
    assert first.evidence_record == second.evidence_record


def test_repeating_one_fact_and_record_yields_equal_independent_values() -> None:
    assert _link(_deletion()) == _link(_deletion())
    assert _link(_deletion()) is not _link(_deletion())


def test_the_correction_record_is_named_only_when_supplied() -> None:
    link = _link(_outcome(), _correction_record())

    assert link.evidence_record.sha256.root == CANONICAL_CORRECTION_SHA256
    assert link.evidence_record.format_name.root == CANONICAL_CORRECTION_FORMAT
    # No supersession is followed: the acquisition record is not reachable here.
    assert CANONICAL_RECORD_SHA256 not in link.model_dump_json()


# --- semantic JSON ------------------------------------------------------------


@pytest.mark.parametrize(
    "fact",
    (
        _binding(RevisionRole.BASE, CANONICAL_BASE_REVISION),
        _binding(),
        _changed_path(),
        _approval(),
        _outcome(),
        _deletion(),
        _occurrence_time(_approval(), CANONICAL_APPROVAL_INSTANT),
        _occurrence_time(_outcome(), CANONICAL_MERGE_INSTANT),
        _occurrence_time(_deletion(), CANONICAL_DELETION_INSTANT),
    ),
)
def test_semantic_json_round_trip_preserves_the_exact_value(fact: Any) -> None:
    original = _link(fact)
    restored = PullRequestHistoryFactEvidenceLink.model_validate_json(
        original.model_dump_json()
    )

    assert restored == original
    assert type(restored.fact) is type(fact)


def test_link_json_payload_carries_exactly_the_two_semantic_keys() -> None:
    payload = _payload(_link(_approval()))

    assert sorted(payload) == ["evidence_record", "fact"]
    assert "schema_version" not in payload


def test_the_occurrence_instant_survives_json_inside_the_fact_union() -> None:
    link = _link(_occurrence_time(_deletion(), CANONICAL_DELETION_INSTANT))
    payload = _payload(link)
    fact = cast(dict[str, Any], payload["fact"])

    assert fact["occurred_at"] == CANONICAL_DELETION_INSTANT
    restored = PullRequestHistoryFactEvidenceLink.model_validate_json(
        link.model_dump_json()
    )
    assert isinstance(restored.fact, PullRequestHistoricalOccurrenceTime)
    assert restored.fact.occurred_at.tzinfo is not None
    assert restored.fact.occurred_at == _instant(CANONICAL_DELETION_INSTANT)


# --- immutability and revalidation --------------------------------------------


def test_link_is_frozen() -> None:
    link = _link(_approval())

    with pytest.raises(ValidationError):
        link.fact = _outcome()  # type: ignore[misc]


def test_link_revalidates_a_nested_fact() -> None:
    link = _link(_approval())
    tampered = link.model_copy()
    object.__setattr__(tampered.fact, "approved_revision", "not-a-commit")

    with pytest.raises(ValidationError):
        PullRequestHistoryFactEvidenceLink.model_validate(tampered)


def test_link_revalidates_a_nested_evidence_record() -> None:
    link = _link(_approval())
    tampered = link.model_copy()
    object.__setattr__(tampered.evidence_record, "byte_length", -1)

    with pytest.raises(ValidationError):
        PullRequestHistoryFactEvidenceLink.model_validate(tampered)


def test_constructed_link_is_revalidated() -> None:
    link = _link(_deletion())

    assert PullRequestHistoryFactEvidenceLink.model_validate(link) == link


# --- required, extra, and untyped inputs --------------------------------------


@pytest.mark.parametrize("missing", ("fact", "evidence_record"))
def test_link_required_fields_cannot_be_omitted(missing: str) -> None:
    supplied: dict[str, Any] = {"fact": _approval(), "evidence_record": _record()}
    del supplied[missing]

    with pytest.raises(ValidationError, match=missing):
        PullRequestHistoryFactEvidenceLink.model_validate(supplied)


@pytest.mark.parametrize("extra", FORBIDDEN_LINK_IDENTIFIERS)
def test_link_extra_fields_fail_closed(extra: str) -> None:
    supplied: dict[str, Any] = {
        "fact": _approval(),
        "evidence_record": _record(),
        extra: "supplied",
    }

    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        PullRequestHistoryFactEvidenceLink.model_validate(supplied)


@pytest.mark.parametrize(
    "value",
    (None, "fact", 1, 1.0, True, (), [], {}, {"pull_request": None}, object()),
)
def test_link_rejects_untyped_python_facts(value: object) -> None:
    with pytest.raises(ValidationError):
        PullRequestHistoryFactEvidenceLink.model_validate(
            {"fact": value, "evidence_record": _record()}
        )


@pytest.mark.parametrize("value", (None, "record", 1, {}, {"sha256": "0" * 64}))
def test_link_rejects_untyped_python_evidence_records(value: object) -> None:
    with pytest.raises(ValidationError, match="in Python input"):
        PullRequestHistoryFactEvidenceLink.model_validate(
            {"fact": _approval(), "evidence_record": value}
        )


def test_link_python_construction_rejects_a_dumped_fact_mapping() -> None:
    dumped = _payload(_link(_approval()))["fact"]

    with pytest.raises(ValidationError):
        PullRequestHistoryFactEvidenceLink.model_validate(
            {"fact": dumped, "evidence_record": _record()}
        )


def test_link_rejects_a_typed_children_python_mapping() -> None:
    """A mapping whose children are already published values is still refused.

    Constructing a published fact is the history layer's responsibility. A
    strict union alone admits this input, so each admitted family carries its
    own Python-mode guard.
    """
    approval = _approval()
    occurrence = _occurrence_time(approval, CANONICAL_APPROVAL_INSTANT)

    for supplied in (
        {"review": approval.review, "approved_revision": approval.approved_revision},
        {"occurrence": approval, "occurred_at": occurrence.occurred_at},
        {
            "pull_request": _outcome().pull_request,
            "merge_revision": _outcome().merge_revision,
        },
        {"head": _deletion().head, "head_ref_name": _deletion().head_ref_name},
        {
            "path": _changed_path().path,
            "head_object": _changed_path().head_object,
            "status": _changed_path().status,
        },
        {
            "pull_request": _binding().pull_request,
            "role_assignment": _binding().role_assignment,
        },
    ):
        with pytest.raises(ValidationError, match="in Python input"):
            PullRequestHistoryFactEvidenceLink.model_validate(
                {"fact": supplied, "evidence_record": _record()}
            )


def test_link_rejects_fully_populated_attribute_backed_facts() -> None:
    approval = _approval()

    class AttributeApproval:
        review = approval.review
        approved_revision = approval.approved_revision

    class AttributeOccurrence:
        occurrence = approval
        occurred_at = _occurrence_time(approval, CANONICAL_APPROVAL_INSTANT).occurred_at

    for supplied in (AttributeApproval(), AttributeOccurrence()):
        with pytest.raises(ValidationError, match="in Python input"):
            PullRequestHistoryFactEvidenceLink.model_validate(
                {"fact": supplied, "evidence_record": _record()},
                from_attributes=True,
            )


def _occurrence_json(instant: str) -> str:
    link = _link(_occurrence_time(_approval(), CANONICAL_APPROVAL_INSTANT))
    payload = _payload(link)
    fact = cast(dict[str, Any], payload["fact"])
    payload["fact"] = {**fact, "occurred_at": instant}
    return json.dumps(payload)


@pytest.mark.parametrize(
    "instant", ("2018-11-17T23:54:20Z", "2018-11-17T23:54:20+00:00")
)
def test_both_asserted_utc_json_forms_reconstruct_the_occurrence(instant: str) -> None:
    restored = PullRequestHistoryFactEvidenceLink.model_validate_json(
        _occurrence_json(instant)
    )

    assert isinstance(restored.fact, PullRequestHistoricalOccurrenceTime)
    assert restored.fact.occurred_at == _instant(CANONICAL_APPROVAL_INSTANT)


@pytest.mark.parametrize(
    "instant",
    (
        "2018-11-17T23:54:20+01:00",
        "2018-11-17T22:54:20-01:00",
        "2018-11-17T23:54:20",
        "not-an-instant",
        "",
    ),
)
def test_the_instant_decode_is_transport_only_and_adds_no_tolerance(
    instant: str,
) -> None:
    """Decoding the JSON leaf must not relax any published S06 guard."""
    with pytest.raises(ValidationError):
        PullRequestHistoryFactEvidenceLink.model_validate_json(
            _occurrence_json(instant)
        )


def test_link_rejects_swapped_members() -> None:
    with pytest.raises(ValidationError):
        PullRequestHistoryFactEvidenceLink.model_validate(
            {"fact": _record(), "evidence_record": _approval()}
        )


# --- excluded published values ------------------------------------------------


def test_link_rejects_the_change_set_aggregate_as_fact() -> None:
    """The retained record declares a complete collection; the product does not.

    `PullRequestChangeSet` composes two bindings with a caller-supplied,
    caller-ordered path tuple and asserts no completeness. Associating one
    retained record with it would attribute the record's declared completeness
    to a value that disclaims it.
    """
    with pytest.raises(ValidationError):
        PullRequestHistoryFactEvidenceLink.model_validate(
            {"fact": _change_set(), "evidence_record": _record()}
        )


def test_link_rejects_the_changed_path_status_vocabulary_as_fact() -> None:
    with pytest.raises(ValidationError):
        PullRequestHistoryFactEvidenceLink.model_validate(
            {"fact": ChangedPathStatus.ADDED, "evidence_record": _record()}
        )


def test_link_rejects_a_change_set_json_mapping_as_fact() -> None:
    payload = json.loads(_change_set().model_dump_json())

    with pytest.raises(ValidationError):
        PullRequestHistoryFactEvidenceLink.model_validate_json(
            json.dumps(
                {
                    "fact": payload,
                    "evidence_record": json.loads(_record().model_dump_json()),
                }
            )
        )


def test_change_set_children_remain_individually_linkable() -> None:
    """Excluding the aggregate does not strand its atomic components."""
    change_set = _change_set()
    child_links = tuple(_link(path) for path in change_set.changed_paths)

    assert len(child_links) == len(change_set.changed_paths) == 3
    assert len(set(child_links)) == 3
    assert _link(change_set.base) != _link(change_set.head)
    with pytest.raises(ValidationError):
        _link(change_set)


@pytest.mark.parametrize("name", EXCLUDED_PUBLISHED_SYMBOLS)
def test_every_excluded_published_symbol_is_absent_from_the_fact_annotation(
    name: str,
) -> None:
    tree = ast.parse(LINK_SOURCE.read_text(encoding="utf-8"))
    annotations = [
        ast.unparse(node.annotation)
        for node in ast.walk(tree)
        if isinstance(node, ast.AnnAssign) and ast.unparse(node.target) == "fact"
    ]

    assert len(annotations) == 1
    assert name not in annotations[0]


def test_the_fact_annotation_is_exactly_the_six_eligible_families() -> None:
    members = get_args(
        PullRequestHistoryFactEvidenceLink.model_fields["fact"].annotation
    )
    resolved = [get_args(member)[0] for member in members]

    assert resolved == [
        PullRequestRevisionRoleBinding,
        PullRequestChangedPath,
        PullRequestReviewRevisionApproval,
        PullRequestMergeRevisionOutcome,
        PullRequestHeadRefDeletion,
        PullRequestHistoricalOccurrenceTime,
    ]


def test_every_admitted_family_carries_a_python_typed_guard() -> None:
    """No admitted family may be reachable from an untyped Python mapping."""
    members = get_args(
        PullRequestHistoryFactEvidenceLink.model_fields["fact"].annotation
    )

    assert len(members) == 6
    for member in members:
        metadata = get_args(member)[1:]
        assert any(isinstance(entry, BeforeValidator) for entry in metadata)


# --- malformed and foreign children -------------------------------------------


@pytest.mark.parametrize(
    "fact",
    (
        {},
        {"pull_request": {}},
        {"path": "a", "head_object": {}, "status": "added"},
        {"review": None, "approved_revision": None},
        {"occurrence": {}, "occurred_at": "2018-11-17T23:54:20Z"},
        {"occurrence": None, "occurred_at": None},
        {"head": {}, "head_ref_name": ""},
    ),
)
def test_link_rejects_malformed_json_facts(fact: object) -> None:
    payload = json.dumps(
        {"fact": fact, "evidence_record": json.loads(_record().model_dump_json())}
    )

    with pytest.raises(ValidationError):
        PullRequestHistoryFactEvidenceLink.model_validate_json(payload)


def test_link_rejects_a_hybrid_json_fact_that_matches_no_branch() -> None:
    payload = json.dumps(
        {
            "fact": {"path": "a", "merge_revision": {}, "occurred_at": "x"},
            "evidence_record": json.loads(_record().model_dump_json()),
        }
    )

    with pytest.raises(ValidationError):
        PullRequestHistoryFactEvidenceLink.model_validate_json(payload)


def test_link_rejects_malformed_evidence_record_json() -> None:
    payload = json.dumps(
        {
            "fact": json.loads(_approval().model_dump_json()),
            "evidence_record": {"sha256": "0" * 64},
        }
    )

    with pytest.raises(ValidationError):
        PullRequestHistoryFactEvidenceLink.model_validate_json(payload)


def test_link_rejects_foreign_models_as_children() -> None:
    class ForeignFact(BaseModel):
        model_config = ConfigDict(frozen=True)

        path: str

    with pytest.raises(ValidationError):
        PullRequestHistoryFactEvidenceLink.model_validate(
            {"fact": ForeignFact(path="a"), "evidence_record": _record()}
        )


def test_link_rejects_attribute_backed_children() -> None:
    class AttributeFact:
        path = "a"

    with pytest.raises(ValidationError):
        PullRequestHistoryFactEvidenceLink.model_validate(
            {"fact": AttributeFact(), "evidence_record": _record()},
            from_attributes=True,
        )


# --- strength and locator boundary --------------------------------------------


@pytest.mark.parametrize("field", FORBIDDEN_LINK_IDENTIFIERS)
def test_link_has_no_strength_locator_or_review_field(field: str) -> None:
    assert field not in PullRequestHistoryFactEvidenceLink.model_fields


def test_the_link_publishes_exactly_two_fields() -> None:
    assert list(PullRequestHistoryFactEvidenceLink.model_fields) == [
        "fact",
        "evidence_record",
    ]


def test_no_forbidden_identifier_appears_in_the_bridge_module_code_surface() -> None:
    """The boundary is asserted against code, not prose.

    The module docstring names several excluded concepts deliberately, so the
    scan strips docstrings and reads only the executable surface.
    """
    tree = ast.parse(LINK_SOURCE.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Module | ast.ClassDef | ast.FunctionDef):
            body = node.body
            if body and isinstance(body[0], ast.Expr):
                value = body[0].value
                if isinstance(value, ast.Constant) and isinstance(value.value, str):
                    node.body = body[1:]
    surface = ast.unparse(ast.fix_missing_locations(tree))

    for identifier in FORBIDDEN_LINK_IDENTIFIERS:
        assert identifier not in surface, identifier


def test_link_makes_no_support_verification_or_completeness_claim() -> None:
    payload = _payload(_link(_occurrence_time(_outcome(), CANONICAL_MERGE_INSTANT)))
    rendered = json.dumps(payload)

    for identifier in FORBIDDEN_LINK_IDENTIFIERS:
        assert f'"{identifier}"' not in rendered


# --- module surface -----------------------------------------------------------


def test_module_surface_is_exact_and_local() -> None:
    assert link_module.__all__ == ["PullRequestHistoryFactEvidenceLink"]

    tree = ast.parse(LINK_SOURCE.read_text(encoding="utf-8"))
    classes = [node.name for node in tree.body if isinstance(node, ast.ClassDef)]
    functions = [node.name for node in tree.body if isinstance(node, ast.FunctionDef)]

    assert classes == ["PullRequestHistoryFactEvidenceLink"]
    # The module-level helpers exist only to build the guarded fact union.
    assert functions == [
        "_require_published_fact",
        "_require_published_occurrence_time",
    ]
    assert all(name.startswith("_") for name in functions)


def test_bridge_module_has_no_io_or_capability_surface() -> None:
    source = LINK_SOURCE.read_text(encoding="utf-8")
    tree = ast.parse(source)
    referenced = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)} | {
        node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute)
    }

    for capability in (
        "Path",
        "__import__",
        "eval",
        "exec",
        "getattr",
        "hashlib",
        "httpx",
        "importlib",
        "json",
        "open",
        "os",
        "pickle",
        "read_bytes",
        "read_text",
        "requests",
        "setattr",
        "subprocess",
        "urlopen",
    ):
        assert capability not in referenced, capability


def test_the_bridge_owns_the_only_cross_domain_edge() -> None:
    history = HISTORY_SOURCE.read_text(encoding="utf-8")
    evidence = EVIDENCE_SOURCE.read_text(encoding="utf-8")
    link = LINK_SOURCE.read_text(encoding="utf-8")

    assert "faultatlas.domain.evidence" not in history
    assert "faultatlas.domain.history" not in evidence
    assert "history_evidence_link" not in history
    assert "history_evidence_link" not in evidence
    assert "faultatlas.domain.history import" in link
    assert "faultatlas.domain.evidence import" in link


def test_history_module_remains_evidence_neutral() -> None:
    history = HISTORY_SOURCE.read_text(encoding="utf-8")

    for identifier in ("DurableEvidenceRecordReference", "evidence_record"):
        assert identifier not in history


def test_link_model_config_matches_the_published_posture() -> None:
    assert PullRequestHistoryFactEvidenceLink.model_config == {
        "frozen": True,
        "extra": "forbid",
        "strict": True,
        "revalidate_instances": "always",
        "validate_default": True,
    }
    assert (
        PullRequestHistoryFactEvidenceLink.__module__
        == "faultatlas.domain.history_evidence_link"
    )


def test_link_declares_no_schema_version_of_its_own() -> None:
    assert "schema_version" not in PullRequestHistoryFactEvidenceLink.model_fields
    assert _record().schema_version == 1


def test_no_pydantic_internal_union_branch_label_is_asserted() -> None:
    """Union-branch labels are pydantic implementation detail.

    The scan reads this oracle's own docstring-stripped surface with this
    function removed, so its own needles cannot satisfy it.
    """
    tree = ast.parse(Path(__file__).read_text(encoding="utf-8"))
    tree.body = [
        node
        for node in tree.body
        if not (
            isinstance(node, ast.FunctionDef)
            and node.name == "test_no_pydantic_internal_union_branch_label_is_asserted"
        )
    ]
    for node in ast.walk(tree):
        if isinstance(node, ast.Module | ast.ClassDef | ast.FunctionDef):
            body = node.body
            if body and isinstance(body[0], ast.Expr):
                value = body[0].value
                if isinstance(value, ast.Constant) and isinstance(value.value, str):
                    node.body = body[1:]
    surface = ast.unparse(ast.fix_missing_locations(tree))

    for needle in ("function-after[", "function-before[", "tagged-union", "union["):
        assert needle not in surface, needle
