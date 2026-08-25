from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Any, cast

import pytest
from pydantic import BaseModel, ConfigDict, ValidationError

import faultatlas.domain.history as history_module
from faultatlas.domain.history import (
    PullRequestMergeRevisionOutcome,
    PullRequestRevisionRoleBinding,
)
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
    GitCommitParentTopology,
    GitHashAlgorithm,
    GitObjectKind,
    GitTreeIdentity,
    RevisionRole,
    RevisionRoleAssignment,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
HISTORY_SOURCE = REPOSITORY_ROOT / "src/faultatlas/domain/history.py"

CANONICAL_PROVIDER = "github"
CANONICAL_REPOSITORY_ID = "37489525"
CANONICAL_PULL_REQUEST_NUMBER = "4414"
CANONICAL_ISSUE_NUMBER = "4412"

# Authoritative digests from the S1.P00.S07 case_git_objects register.
CANONICAL_BASE_REVISION = "4c9cde74ab40027b5761ab9e002af116a4a20df3"
CANONICAL_HEAD_REVISION = "690a63b9218f72662cd3a67c6c200b758c88ce12"
CANONICAL_MERGE_FIRST_PARENT = "5fab0ca3127bc895b611cc03bb3af1ebf9a0dbed"
CANONICAL_MERGE_REVISION = "10cdae8e38ec448b7133cf163dca587ad806d262"
CANONICAL_MERGE_TREE = "098a83387668d175ae2c10f2b79a5dc30b55fc83"

SYNTHETIC_REVISION = "1a2b3c4d5e6f11111111111111111111111111ff"

FORBIDDEN_OUTCOME_IDENTIFIERS = (
    "ahead_by",
    "ancestor",
    "ancestry",
    "behind_by",
    "closed",
    "confidence",
    "descendant",
    "evidence",
    "merge_base",
    "merged_at",
    "merged_by",
    "occurred_at",
    "ordered_parents",
    "reachab",
    "review",
    "squash",
    "strategy",
    "timestamp",
    "topology",
    "unmerged",
)


def _repository() -> RepositoryIdentity:
    return RepositoryIdentity(
        provider=ProviderKey(CANONICAL_PROVIDER),
        provider_repository_id=ProviderRepositoryId(CANONICAL_REPOSITORY_ID),
    )


def _pull_request(
    number: str = CANONICAL_PULL_REQUEST_NUMBER,
) -> NumberedSourceObjectIdentity:
    return NumberedSourceObjectIdentity(
        repository_identity=_repository(),
        kind=SourceObjectKind.PULL_REQUEST,
        repository_scoped_number=RepositoryScopedNumber(number),
    )


def _issue() -> NumberedSourceObjectIdentity:
    return NumberedSourceObjectIdentity(
        repository_identity=_repository(),
        kind=SourceObjectKind.ISSUE,
        repository_scoped_number=RepositoryScopedNumber(CANONICAL_ISSUE_NUMBER),
    )


def _commit(
    full_digest: str = CANONICAL_MERGE_REVISION,
    algorithm: GitHashAlgorithm = GitHashAlgorithm.SHA1,
) -> GitCommitIdentity:
    return GitCommitIdentity(
        kind=GitObjectKind.COMMIT,
        algorithm=algorithm,
        full_digest=full_digest,
    )


def _outcome(
    *,
    pull_request: NumberedSourceObjectIdentity | None = None,
    merge_revision: GitCommitIdentity | None = None,
) -> PullRequestMergeRevisionOutcome:
    return PullRequestMergeRevisionOutcome(
        pull_request=_pull_request() if pull_request is None else pull_request,
        merge_revision=_commit() if merge_revision is None else merge_revision,
    )


def _payload() -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(_outcome().model_dump_json()))


# --- canonical witness -----------------------------------------------------


def test_the_canonical_pull_request_merged_as_the_canonical_revision() -> None:
    outcome = _outcome()

    assert outcome.pull_request == _pull_request()
    assert outcome.pull_request.kind is SourceObjectKind.PULL_REQUEST
    assert outcome.merge_revision.full_digest == CANONICAL_MERGE_REVISION
    assert outcome.merge_revision.kind is GitObjectKind.COMMIT
    assert outcome.merge_revision.algorithm is GitHashAlgorithm.SHA1


def test_repeating_one_outcome_yields_equal_independent_values() -> None:
    first = _outcome()
    second = _outcome()

    assert first == second
    assert first is not second


def test_the_two_supplied_values_are_preserved_unchanged() -> None:
    pull_request = _pull_request()
    revision = _commit()

    outcome = PullRequestMergeRevisionOutcome(
        pull_request=pull_request, merge_revision=revision
    )

    assert outcome.pull_request == pull_request
    assert outcome.merge_revision == revision


def test_the_merge_revision_is_not_the_head_revision() -> None:
    outcome = _outcome()

    assert outcome.merge_revision != _commit(CANONICAL_HEAD_REVISION)
    assert outcome.merge_revision.full_digest != CANONICAL_HEAD_REVISION


# --- outcome distinctions --------------------------------------------------


def test_a_different_pull_request_yields_a_distinct_outcome() -> None:
    assert _outcome() != _outcome(pull_request=_pull_request("1"))


def test_a_different_merge_revision_yields_a_distinct_outcome() -> None:
    assert _outcome() != _outcome(merge_revision=_commit(SYNTHETIC_REVISION))


def test_one_pull_request_may_name_two_revisions_as_two_values() -> None:
    first = _outcome()
    second = _outcome(merge_revision=_commit(SYNTHETIC_REVISION))

    assert first.pull_request == second.pull_request
    assert first != second


# --- pull-request-only subject ---------------------------------------------


def test_an_issue_cannot_have_a_merge_revision_outcome() -> None:
    with pytest.raises(ValidationError, match="must identify a pull_request"):
        _outcome(pull_request=_issue())


def test_an_issue_subject_is_rejected_in_json_input() -> None:
    payload = _payload()
    subject = payload["pull_request"]
    assert isinstance(subject, dict)
    subject["kind"] = "issue"
    subject["repository_scoped_number"] = CANONICAL_ISSUE_NUMBER

    with pytest.raises(ValidationError, match="must identify a pull_request"):
        PullRequestMergeRevisionOutcome.model_validate_json(json.dumps(payload))


@pytest.mark.parametrize(
    "kind",
    tuple(kind for kind in SourceObjectKind if kind is not SourceObjectKind.ISSUE),
)
def test_only_the_pull_request_kind_is_accepted(kind: SourceObjectKind) -> None:
    if kind is SourceObjectKind.PULL_REQUEST:
        assert _outcome().pull_request.kind is kind
        return
    payload = _payload()
    subject = payload["pull_request"]
    assert isinstance(subject, dict)
    subject["kind"] = kind.value

    with pytest.raises(ValidationError):
        PullRequestMergeRevisionOutcome.model_validate_json(json.dumps(payload))


# --- commit-only merge revision --------------------------------------------


def test_only_a_commit_identity_may_be_a_merge_revision() -> None:
    with pytest.raises(ValidationError, match="in Python input"):
        _outcome(
            merge_revision=GitTreeIdentity(  # type: ignore[arg-type]
                kind=GitObjectKind.TREE,
                algorithm=GitHashAlgorithm.SHA1,
                full_digest=CANONICAL_MERGE_TREE,
            )
        )
    with pytest.raises(ValidationError, match="in Python input"):
        _outcome(
            merge_revision=GitBlobIdentity(  # type: ignore[arg-type]
                kind=GitObjectKind.BLOB,
                algorithm=GitHashAlgorithm.SHA1,
                full_digest=CANONICAL_MERGE_TREE,
            )
        )


@pytest.mark.parametrize(
    "revision",
    (
        {},
        {"kind": "commit"},
        {"kind": "tree", "algorithm": "sha1", "full_digest": CANONICAL_MERGE_TREE},
        {"kind": "blob", "algorithm": "sha1", "full_digest": CANONICAL_MERGE_TREE},
        {"kind": "commit", "algorithm": "sha1", "full_digest": "0" * 40},
        {
            "kind": "commit",
            "algorithm": "sha1",
            "full_digest": CANONICAL_MERGE_REVISION.upper(),
        },
        {
            "kind": "commit",
            "algorithm": "sha256",
            "full_digest": CANONICAL_MERGE_REVISION,
        },
        {
            "schema_version": 2,
            "kind": "commit",
            "algorithm": "sha1",
            "full_digest": CANONICAL_MERGE_REVISION,
        },
        CANONICAL_MERGE_REVISION,
        None,
        [],
    ),
)
def test_outcome_rejects_malformed_merge_revision_json(revision: object) -> None:
    payload = _payload()
    payload["merge_revision"] = revision

    with pytest.raises(ValidationError):
        PullRequestMergeRevisionOutcome.model_validate_json(json.dumps(payload))


def test_a_sha256_merge_revision_is_accepted() -> None:
    outcome = _outcome(merge_revision=_commit("a" * 64, GitHashAlgorithm.SHA256))

    assert outcome.merge_revision.algorithm is GitHashAlgorithm.SHA256


# --- no parent, role, or strategy semantics --------------------------------


def test_the_outcome_carries_no_parent_sequence() -> None:
    fields = set(PullRequestMergeRevisionOutcome.model_fields)

    for absent in (
        "ordered_parents",
        "parents",
        "merge_topology",
        "topology",
        "first_parent",
        "merge_first_parent",
    ):
        assert absent not in fields
    assert fields == {"pull_request", "merge_revision"}


def test_the_outcome_carries_no_revision_role_or_assignment() -> None:
    for absent in ("role", "merge_assignment", "role_assignment"):
        assert absent not in PullRequestMergeRevisionOutcome.model_fields
    for annotation in (
        field.annotation
        for field in PullRequestMergeRevisionOutcome.model_fields.values()
    ):
        assert annotation is not RevisionRole
        assert annotation is not RevisionRoleAssignment
        assert annotation is not GitCommitParentTopology
        assert annotation is not PullRequestRevisionRoleBinding


def test_the_published_topology_value_remains_the_separate_parent_carrier() -> None:
    # The canonical merge parents stay a published revision fact; the outcome
    # neither embeds nor contradicts them.
    topology = GitCommitParentTopology(
        commit=_commit(),
        ordered_parents=(
            _commit(CANONICAL_MERGE_FIRST_PARENT),
            _commit(CANONICAL_HEAD_REVISION),
        ),
    )
    outcome = _outcome()

    assert topology.commit == outcome.merge_revision
    assert len(topology.ordered_parents) == 2
    assert not hasattr(outcome, "ordered_parents")


def _topology_of(count: int) -> GitCommitParentTopology:
    """A published P02 topology over the canonical merge commit, `count` parents.

    The parents differ only in digest, so only the parent count varies.
    """
    parents = (
        _commit(CANONICAL_MERGE_FIRST_PARENT),
        _commit(CANONICAL_HEAD_REVISION),
        _commit(SYNTHETIC_REVISION),
    )
    assert count <= len(parents)
    return GitCommitParentTopology(commit=_commit(), ordered_parents=parents[:count])


@pytest.mark.parametrize("count", (0, 1, 2, 3))
def test_any_parent_count_composes_with_one_unchanged_outcome(count: int) -> None:
    # The outcome is built identically regardless of the topology beside it. If
    # S04 ever gained a topology or parent input, this construction would fail.
    outcome = _outcome()
    topology = _topology_of(count)

    assert len(topology.ordered_parents) == count
    assert topology.commit == outcome.merge_revision
    assert outcome == _outcome()
    assert outcome.model_dump_json() == _outcome().model_dump_json()
    assert tuple(PullRequestMergeRevisionOutcome.model_fields) == (
        "pull_request",
        "merge_revision",
    )


def test_the_outcome_is_identical_across_every_parent_count() -> None:
    outcomes: list[str] = []
    for count in (0, 1, 2, 3):
        topology = _topology_of(count)
        outcome = _outcome()
        assert topology.commit == outcome.merge_revision
        outcomes.append(outcome.model_dump_json())

    assert len(set(outcomes)) == 1, "parent count must not reach the outcome"


def test_a_parentless_topology_is_a_valid_published_p02_fact() -> None:
    # P02 imposes no parent-count rule, so a root-like commit is representable
    # there; S04 neither requires nor forbids it.
    topology = _topology_of(0)

    assert topology.ordered_parents == ()
    assert topology.commit == _outcome().merge_revision


def test_an_outcome_asserts_nothing_about_parent_count_or_strategy() -> None:
    # A single-parent result, as a squash or rebase merge would produce, is a
    # perfectly ordinary outcome value.
    squash_like = _outcome(merge_revision=_commit(SYNTHETIC_REVISION))

    assert squash_like.merge_revision.full_digest == SYNTHETIC_REVISION
    for absent in ("parent_count", "strategy", "merge_method", "squash", "rebase"):
        assert not hasattr(squash_like, absent)


# --- no base or head coupling ----------------------------------------------


def test_the_recorded_base_need_not_relate_to_the_merge_revision() -> None:
    # The canonical case is exactly this: the recorded base is not the merge
    # first parent, because the integration branch advanced before the merge.
    assert CANONICAL_BASE_REVISION != CANONICAL_MERGE_FIRST_PARENT

    base_binding = PullRequestRevisionRoleBinding(
        pull_request=_pull_request(),
        role_assignment=RevisionRoleAssignment(
            role=RevisionRole.BASE, revision=_commit(CANONICAL_BASE_REVISION)
        ),
    )
    outcome = _outcome()

    assert base_binding.role_assignment.revision != outcome.merge_revision
    assert base_binding.role_assignment.revision.full_digest != (
        CANONICAL_MERGE_FIRST_PARENT
    )


def test_the_head_revision_may_itself_be_supplied_as_a_merge_revision() -> None:
    # Nothing forbids it; the relation constrains no relationship to any role.
    outcome = _outcome(merge_revision=_commit(CANONICAL_HEAD_REVISION))

    assert outcome.merge_revision.full_digest == CANONICAL_HEAD_REVISION


def test_the_base_revision_may_itself_be_supplied_as_a_merge_revision() -> None:
    outcome = _outcome(merge_revision=_commit(CANONICAL_BASE_REVISION))

    assert outcome.merge_revision.full_digest == CANONICAL_BASE_REVISION


# --- no state vocabulary ---------------------------------------------------


def test_the_outcome_carries_no_merge_state_or_disposition() -> None:
    for absent in (
        "state",
        "merged",
        "disposition",
        "outcome",
        "merge_state",
        "closed",
    ):
        assert absent not in PullRequestMergeRevisionOutcome.model_fields


@pytest.mark.parametrize(
    "rejected",
    ("MergeState", "MergeOutcomeState", "MergeDisposition", "MergeMethod"),
)
def test_no_merge_state_vocabulary_is_published(rejected: str) -> None:
    source = HISTORY_SOURCE.read_text(encoding="utf-8")

    assert not hasattr(history_module, rejected)
    assert rejected not in history_module.__all__
    assert rejected not in source


def test_an_absent_outcome_is_not_a_negative_state() -> None:
    # Only positive outcomes exist; there is no value meaning "did not merge".
    outcome = _outcome()

    for absent in ("unmerged", "abandoned", "closed_without_merge", "pending"):
        assert not hasattr(outcome, absent)
        assert absent not in PullRequestMergeRevisionOutcome.model_fields


# --- semantic JSON ---------------------------------------------------------


def test_outcome_semantic_json_round_trip_preserves_the_exact_value() -> None:
    outcome = _outcome()

    restored = PullRequestMergeRevisionOutcome.model_validate_json(
        outcome.model_dump_json()
    )

    assert restored == outcome
    assert restored.model_dump_json() == outcome.model_dump_json()


def test_outcome_json_payload_carries_exactly_the_two_semantic_keys() -> None:
    payload = _payload()

    assert set(payload) == {"pull_request", "merge_revision"}
    assert "schema_version" not in payload


def test_embedded_children_keep_their_published_json_shape() -> None:
    outcome = _outcome()
    payload = _payload()

    assert payload["pull_request"] == json.loads(outcome.pull_request.model_dump_json())
    assert payload["merge_revision"] == json.loads(
        outcome.merge_revision.model_dump_json()
    )


def test_outcome_json_reconstruction_accepts_a_semantic_mapping() -> None:
    assert (
        PullRequestMergeRevisionOutcome.model_validate_json(json.dumps(_payload()))
        == _outcome()
    )


# --- model posture ---------------------------------------------------------


def test_outcome_is_frozen() -> None:
    outcome = _outcome()

    for field, value in (
        ("pull_request", _pull_request("1")),
        ("merge_revision", _commit(SYNTHETIC_REVISION)),
    ):
        with pytest.raises(ValidationError):
            setattr(outcome, field, value)

    assert outcome == _outcome()


def test_outcome_rejects_attribute_deletion() -> None:
    outcome = _outcome()

    with pytest.raises(ValidationError):
        del outcome.merge_revision

    assert outcome == _outcome()


def test_constructed_outcome_is_revalidated() -> None:
    assert PullRequestMergeRevisionOutcome.model_validate(_outcome()) == _outcome()


def test_outcome_revalidates_a_tampered_pull_request() -> None:
    tampered = NumberedSourceObjectIdentity.model_construct(
        schema_version=1,
        repository_identity=_repository(),
        kind=SourceObjectKind.ISSUE,
        repository_scoped_number=RepositoryScopedNumber(CANONICAL_PULL_REQUEST_NUMBER),
    )

    with pytest.raises(ValidationError, match="must identify a pull_request"):
        _outcome(pull_request=tampered)


def test_outcome_revalidates_a_tampered_merge_revision() -> None:
    tampered = GitCommitIdentity.model_construct(
        schema_version=1,
        kind=GitObjectKind.COMMIT,
        algorithm=GitHashAlgorithm.SHA1,
        full_digest="not-a-digest",
    )

    with pytest.raises(ValidationError):
        _outcome(merge_revision=tampered)


def test_outcome_preserves_published_subclass_acceptance() -> None:
    class _SubclassedPullRequest(NumberedSourceObjectIdentity):
        pass

    class _SubclassedCommit(GitCommitIdentity):
        pass

    outcome = PullRequestMergeRevisionOutcome(
        pull_request=_SubclassedPullRequest(
            repository_identity=_repository(),
            kind=SourceObjectKind.PULL_REQUEST,
            repository_scoped_number=RepositoryScopedNumber(
                CANONICAL_PULL_REQUEST_NUMBER
            ),
        ),
        merge_revision=_SubclassedCommit(
            kind=GitObjectKind.COMMIT,
            algorithm=GitHashAlgorithm.SHA1,
            full_digest=CANONICAL_MERGE_REVISION,
        ),
    )

    assert outcome == _outcome()
    assert type(outcome.pull_request) is NumberedSourceObjectIdentity
    assert type(outcome.merge_revision) is GitCommitIdentity


# --- required fields and closed extras -------------------------------------


@pytest.mark.parametrize("missing", ("pull_request", "merge_revision"))
def test_outcome_required_fields_cannot_be_omitted(missing: str) -> None:
    payload = _payload()
    del payload[missing]

    with pytest.raises(ValidationError) as error:
        PullRequestMergeRevisionOutcome.model_validate_json(json.dumps(payload))

    assert error.value.errors()[0]["type"] == "missing"
    assert error.value.errors()[0]["loc"] == (missing,)


@pytest.mark.parametrize(
    "extra",
    (
        "ahead_by",
        "behind_by",
        "merge_base",
        "merged",
        "merged_at",
        "merged_by",
        "merge_assignment",
        "ordered_parents",
        "review",
        "schema_version",
        "state",
        "strategy",
    ),
)
def test_outcome_extra_fields_fail_closed(extra: str) -> None:
    payload = _payload()
    payload[extra] = "unexpected"

    with pytest.raises(ValidationError) as error:
        PullRequestMergeRevisionOutcome.model_validate_json(json.dumps(payload))

    assert error.value.errors()[0]["type"] == "extra_forbidden"


def test_outcome_has_no_field_beyond_the_two_semantic_positions() -> None:
    assert tuple(PullRequestMergeRevisionOutcome.model_fields) == (
        "pull_request",
        "merge_revision",
    )


# --- strict Python input ---------------------------------------------------


@pytest.mark.parametrize(
    "value",
    (
        None,
        CANONICAL_PULL_REQUEST_NUMBER,
        4414,
        {"kind": "pull_request"},
        _commit(),
    ),
)
def test_outcome_rejects_untyped_python_pull_requests(value: object) -> None:
    with pytest.raises(ValidationError, match="in Python input"):
        PullRequestMergeRevisionOutcome(
            pull_request=value,  # type: ignore[arg-type]
            merge_revision=_commit(),
        )


@pytest.mark.parametrize(
    "value",
    (
        None,
        CANONICAL_MERGE_REVISION,
        {"kind": "commit"},
        _pull_request(),
    ),
)
def test_outcome_rejects_untyped_python_merge_revisions(value: object) -> None:
    with pytest.raises(ValidationError, match="in Python input"):
        PullRequestMergeRevisionOutcome(
            pull_request=_pull_request(),
            merge_revision=value,  # type: ignore[arg-type]
        )


def test_outcome_python_construction_rejects_a_dumped_mapping() -> None:
    with pytest.raises(ValidationError, match="in Python input"):
        PullRequestMergeRevisionOutcome.model_validate(_payload())


def test_outcome_rejects_swapped_members() -> None:
    with pytest.raises(ValidationError, match="in Python input"):
        PullRequestMergeRevisionOutcome(
            pull_request=_commit(),  # type: ignore[arg-type]
            merge_revision=_pull_request(),  # type: ignore[arg-type]
        )


class _AttributeBackedPullRequest:
    def __init__(self, pull_request: NumberedSourceObjectIdentity) -> None:
        self.schema_version = pull_request.schema_version
        self.repository_identity = pull_request.repository_identity
        self.kind = pull_request.kind
        self.repository_scoped_number = pull_request.repository_scoped_number


class _AttributeBackedRevision:
    def __init__(self, revision: GitCommitIdentity) -> None:
        self.schema_version = revision.schema_version
        self.kind = revision.kind
        self.algorithm = revision.algorithm
        self.full_digest = revision.full_digest


class _ForeignPullRequest(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    schema_version: object
    repository_identity: object
    kind: object
    repository_scoped_number: object


class _ForeignRevision(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    schema_version: object
    kind: object
    algorithm: object
    full_digest: object


def _foreign_pull_request() -> _ForeignPullRequest:
    pull_request = _pull_request()
    return _ForeignPullRequest(
        schema_version=pull_request.schema_version,
        repository_identity=pull_request.repository_identity,
        kind=pull_request.kind,
        repository_scoped_number=pull_request.repository_scoped_number,
    )


def _foreign_revision() -> _ForeignRevision:
    revision = _commit()
    return _ForeignRevision(
        schema_version=revision.schema_version,
        kind=revision.kind,
        algorithm=revision.algorithm,
        full_digest=revision.full_digest,
    )


def test_outcome_rejects_attribute_backed_children_under_from_attributes() -> None:
    with pytest.raises(ValidationError, match="in Python input"):
        PullRequestMergeRevisionOutcome.model_validate(
            {
                "pull_request": _AttributeBackedPullRequest(_pull_request()),
                "merge_revision": _commit(),
            },
            from_attributes=True,
        )
    with pytest.raises(ValidationError, match="in Python input"):
        PullRequestMergeRevisionOutcome.model_validate(
            {
                "pull_request": _pull_request(),
                "merge_revision": _AttributeBackedRevision(_commit()),
            },
            from_attributes=True,
        )


def test_outcome_rejects_foreign_models_in_plain_python_input() -> None:
    with pytest.raises(
        ValidationError, match="pull_request must be a NumberedSourceObjectIdentity"
    ):
        PullRequestMergeRevisionOutcome(
            pull_request=_foreign_pull_request(),  # type: ignore[arg-type]
            merge_revision=_commit(),
        )
    with pytest.raises(
        ValidationError, match="merge_revision must be a GitCommitIdentity"
    ):
        PullRequestMergeRevisionOutcome(
            pull_request=_pull_request(),
            merge_revision=_foreign_revision(),  # type: ignore[arg-type]
        )


def test_both_child_positions_reject_foreign_models_under_from_attributes() -> None:
    for supplied, expected in (
        (
            {"pull_request": _foreign_pull_request(), "merge_revision": _commit()},
            "pull_request must be",
        ),
        (
            {"pull_request": _pull_request(), "merge_revision": _foreign_revision()},
            "merge_revision must be",
        ),
    ):
        with pytest.raises(ValidationError, match=expected):
            PullRequestMergeRevisionOutcome.model_validate(
                supplied, from_attributes=True
            )


# --- malformed pull-request JSON -------------------------------------------


@pytest.mark.parametrize(
    "pull_request",
    (
        {},
        {"kind": "pull_request"},
        {
            "schema_version": 2,
            "repository_identity": {
                "provider": CANONICAL_PROVIDER,
                "provider_repository_id": CANONICAL_REPOSITORY_ID,
            },
            "kind": "pull_request",
            "repository_scoped_number": CANONICAL_PULL_REQUEST_NUMBER,
        },
        {
            "repository_identity": {
                "provider": CANONICAL_PROVIDER,
                "provider_repository_id": CANONICAL_REPOSITORY_ID,
            },
            "kind": "pull_request",
            "repository_scoped_number": "04414",
        },
        {
            "repository_identity": {
                "provider": CANONICAL_PROVIDER,
                "provider_repository_id": "",
            },
            "kind": "pull_request",
            "repository_scoped_number": CANONICAL_PULL_REQUEST_NUMBER,
        },
        CANONICAL_PULL_REQUEST_NUMBER,
        None,
        [],
    ),
)
def test_outcome_rejects_malformed_pull_request_json(pull_request: object) -> None:
    payload = _payload()
    payload["pull_request"] = pull_request

    with pytest.raises(ValidationError):
        PullRequestMergeRevisionOutcome.model_validate_json(json.dumps(payload))


def test_outcome_rejects_a_json_payload_that_is_not_an_object() -> None:
    for payload in ("[]", '"merged"', "1", "null"):
        with pytest.raises(ValidationError):
            PullRequestMergeRevisionOutcome.model_validate_json(payload)


# --- non-claim boundary ----------------------------------------------------


@pytest.mark.parametrize(
    "absent",
    (
        "ahead_by",
        "ancestry",
        "behind_by",
        "branch",
        "ci_status",
        "confidence",
        "evidence",
        "evidence_record",
        "merge_base",
        "merged_at",
        "merged_by",
        "occurred_at",
        "reachable",
        "review",
        "review_approval",
        "test_status",
        "timestamp",
    ),
)
def test_outcome_has_no_metric_temporal_actor_or_review_field(absent: str) -> None:
    assert absent not in PullRequestMergeRevisionOutcome.model_fields


def test_the_outcome_expresses_no_ancestry_or_reachability() -> None:
    outcome = _outcome()

    for absent in (
        "descends_from",
        "ancestry",
        "merge_base",
        "reachable",
        "distance",
        "commit_count",
    ):
        assert not hasattr(outcome, absent)


def test_the_outcome_claims_no_correctness_causation_or_repair() -> None:
    outcome = _outcome()

    for absent in ("correct", "fixes", "repairs", "proves", "caused_by", "verified"):
        assert not hasattr(outcome, absent)


def test_no_forbidden_identifier_appears_in_the_outcome_surface() -> None:
    tree = ast.parse(HISTORY_SOURCE.read_text(encoding="utf-8"))
    outcome_class = next(
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef)
        and node.name == "PullRequestMergeRevisionOutcome"
    )
    surface = ast.unparse(outcome_class)

    for identifier in FORBIDDEN_OUTCOME_IDENTIFIERS:
        assert identifier not in surface


def test_the_outcome_module_adds_no_evidence_or_confidence_surface() -> None:
    source = HISTORY_SOURCE.read_text(encoding="utf-8")

    assert "faultatlas.domain.evidence" not in source
    assert "DurableEvidenceRecordReference" not in source
    assert "faultatlas.domain.snapshot" not in source


# --- module surface --------------------------------------------------------


def test_outcome_model_surface_is_exact() -> None:
    assert history_module.__all__[5] == "PullRequestMergeRevisionOutcome"
    assert tuple(PullRequestMergeRevisionOutcome.model_fields) == (
        "pull_request",
        "merge_revision",
    )
    assert {
        name: field.annotation
        for name, field in PullRequestMergeRevisionOutcome.model_fields.items()
    } == {
        "pull_request": NumberedSourceObjectIdentity,
        "merge_revision": GitCommitIdentity,
    }
    for field in PullRequestMergeRevisionOutcome.model_fields.values():
        assert field.metadata == []
        assert field.discriminator is None
        assert field.is_required()
    assert PullRequestMergeRevisionOutcome.model_config == {
        "frozen": True,
        "extra": "forbid",
        "strict": True,
        "revalidate_instances": "always",
        "validate_default": True,
    }
    assert PullRequestMergeRevisionOutcome.__module__ == "faultatlas.domain.history"


def test_the_outcome_declares_the_expected_validators() -> None:
    tree = ast.parse(HISTORY_SOURCE.read_text(encoding="utf-8"))
    outcome_class = next(
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef)
        and node.name == "PullRequestMergeRevisionOutcome"
    )

    assert [type(node) for node in outcome_class.body] == [
        ast.Expr,
        ast.Assign,
        ast.AnnAssign,
        ast.AnnAssign,
        ast.FunctionDef,
        ast.FunctionDef,
        ast.FunctionDef,
    ]
    assert [
        node.name for node in outcome_class.body if isinstance(node, ast.FunctionDef)
    ] == [
        "_require_typed_python_merged_pull_request",
        "_require_typed_python_merge_revision",
        "_require_merged_pull_request_subject",
    ]
    assert [
        (node.target.id, ast.unparse(node.annotation))
        for node in outcome_class.body
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name)
    ] == [
        ("pull_request", "NumberedSourceObjectIdentity"),
        ("merge_revision", "GitCommitIdentity"),
    ]


def test_history_module_still_performs_no_io() -> None:
    tree = ast.parse(HISTORY_SOURCE.read_text(encoding="utf-8"))
    referenced = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)} | {
        node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute)
    }

    for capability in (
        "Path",
        "__import__",
        "fromtimestamp",
        "getattr",
        "hashlib",
        "httpx",
        "importlib",
        "json",
        "now",
        "open",
        "os",
        "read_bytes",
        "read_text",
        "requests",
        "setattr",
        "subprocess",
        "today",
        "urlopen",
        "utcnow",
        "write_text",
    ):
        assert capability not in referenced


def test_history_module_depends_only_on_published_p01_and_p02() -> None:
    tree = ast.parse(HISTORY_SOURCE.read_text(encoding="utf-8"))
    faultatlas_modules = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
        and node.module is not None
        and node.module.startswith("faultatlas")
    }

    assert faultatlas_modules == {
        "faultatlas.domain.identity",
        "faultatlas.domain.revision",
    }


@pytest.mark.parametrize(
    "literal",
    (
        CANONICAL_REPOSITORY_ID,
        CANONICAL_PULL_REQUEST_NUMBER,
        CANONICAL_MERGE_REVISION,
        CANONICAL_MERGE_FIRST_PARENT,
    ),
)
def test_no_canonical_case_literal_is_embedded_in_production(literal: str) -> None:
    assert literal not in HISTORY_SOURCE.read_text(encoding="utf-8")


def test_canonical_merge_literals_remain_locked() -> None:
    # These are the S1.P00.S07 case_git_objects digests, not test inventions.
    assert CANONICAL_BASE_REVISION == "4c9cde74ab40027b5761ab9e002af116a4a20df3"
    assert CANONICAL_HEAD_REVISION == "690a63b9218f72662cd3a67c6c200b758c88ce12"
    assert CANONICAL_MERGE_FIRST_PARENT == ("5fab0ca3127bc895b611cc03bb3af1ebf9a0dbed")
    assert CANONICAL_MERGE_REVISION == "10cdae8e38ec448b7133cf163dca587ad806d262"
    # The recorded base is not the merge first parent; the branch advanced.
    assert CANONICAL_BASE_REVISION != CANONICAL_MERGE_FIRST_PARENT


def test_the_roadmap_records_the_s04_transition() -> None:
    roadmap = " ".join(
        (REPOSITORY_ROOT / "docs/roadmap.md").read_text(encoding="utf-8").split()
    )
    mapping = roadmap.split("## Current-code mapping", 1)
    assert len(mapping) == 2, "roadmap must retain a current-code mapping section"
    current = mapping[1]

    assert "PullRequestMergeRevisionOutcome" in current
    assert "`S1.P05.S04` — Pull Request Merge Revision Outcome (complete)" in roadmap
    assert "`S1.P05.S08` is next and not started" in roadmap
    # The superseded provisional title and status must not survive.
    assert "Merge Outcome and Ordered Merge Parents" not in roadmap
    assert "`S1.P05.S04` is next and not started" not in roadmap


def test_the_unused_review_identity_type_stays_out_of_this_relation() -> None:
    review = ProviderScopedSourceObjectIdentity(
        kind=SourceObjectKind.PULL_REQUEST_REVIEW,
        provider_global_id=ProviderGlobalId("176071572"),
        parent=_pull_request(),
    )

    with pytest.raises(ValidationError, match="in Python input"):
        PullRequestMergeRevisionOutcome(
            pull_request=review,  # type: ignore[arg-type]
            merge_revision=_commit(),
        )
