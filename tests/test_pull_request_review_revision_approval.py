from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Any, cast

import pytest
from pydantic import BaseModel, ConfigDict, ValidationError

import faultatlas.domain.history as history_module
from faultatlas.domain.history import (
    PullRequestReviewRevisionApproval,
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
    GitHashAlgorithm,
    GitObjectKind,
    GitTreeIdentity,
    RevisionRole,
    RevisionRoleAssignment,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
HISTORY_SOURCE = REPOSITORY_ROOT / "src/faultatlas/domain/history.py"
IDENTITY_SOURCE = REPOSITORY_ROOT / "src/faultatlas/domain/identity.py"

CANONICAL_PROVIDER = "github"
CANONICAL_REPOSITORY_ID = "37489525"
CANONICAL_PULL_REQUEST_NUMBER = "4414"
CANONICAL_ISSUE_NUMBER = "4412"
CANONICAL_REVIEW_GLOBAL_ID = "176071572"
CANONICAL_REVIEWED_REVISION = "690a63b9218f72662cd3a67c6c200b758c88ce12"
CANONICAL_BASE_REVISION = "4c9cde74ab40027b5761ab9e002af116a4a20df3"
CANONICAL_HEAD_TREE = "9e5593159e909083009ac9ad72d5d59feb863c44"

# A revision that is neither the canonical base nor the canonical head, used to
# show that an approval is not coupled to any revision role.
INTERMEDIATE_REVISION = "1a2b3c4d5e6f11111111111111111111111111ff"
SYNTHETIC_REVIEW_GLOBAL_ID = "999999999"

FORBIDDEN_APPROVAL_IDENTIFIERS = (
    "accepted",
    "ancestry",
    "approval_reason",
    "approved_at",
    "author",
    "ci_",
    "comment",
    "confidence",
    "contested",
    "dismiss",
    "evidence",
    "merge",
    "occurred_at",
    "rationale",
    "reviewer",
    "review_body",
    "review_state",
    "snapshot",
    "submitted_at",
    "test_run",
    "timestamp",
    "verified",
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


def _review(
    *,
    kind: SourceObjectKind = SourceObjectKind.PULL_REQUEST_REVIEW,
    global_id: str = CANONICAL_REVIEW_GLOBAL_ID,
    parent: NumberedSourceObjectIdentity | None = None,
) -> ProviderScopedSourceObjectIdentity:
    return ProviderScopedSourceObjectIdentity(
        kind=kind,
        provider_global_id=ProviderGlobalId(global_id),
        parent=_pull_request() if parent is None else parent,
    )


def _commit(full_digest: str = CANONICAL_REVIEWED_REVISION) -> GitCommitIdentity:
    return GitCommitIdentity(
        kind=GitObjectKind.COMMIT,
        algorithm=GitHashAlgorithm.SHA1,
        full_digest=full_digest,
    )


def _approval(
    *,
    review: ProviderScopedSourceObjectIdentity | None = None,
    approved_revision: GitCommitIdentity | None = None,
) -> PullRequestReviewRevisionApproval:
    return PullRequestReviewRevisionApproval(
        review=_review() if review is None else review,
        approved_revision=_commit() if approved_revision is None else approved_revision,
    )


def _payload() -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(_approval().model_dump_json()))


def _review_payload(payload: dict[str, Any]) -> dict[str, Any]:
    review = payload["review"]
    assert isinstance(review, dict)
    return cast(dict[str, Any], review)


# --- canonical witness -----------------------------------------------------


def test_the_canonical_review_approves_the_canonical_revision() -> None:
    approval = _approval()

    assert approval.review.kind is SourceObjectKind.PULL_REQUEST_REVIEW
    assert approval.review.provider_global_id == ProviderGlobalId(
        CANONICAL_REVIEW_GLOBAL_ID
    )
    assert approval.approved_revision.full_digest == CANONICAL_REVIEWED_REVISION
    assert approval.approved_revision.kind is GitObjectKind.COMMIT
    assert approval.approved_revision.algorithm is GitHashAlgorithm.SHA1


def test_the_parent_pull_request_is_reachable_through_the_published_identity() -> None:
    approval = _approval()

    assert approval.review.parent == _pull_request()
    assert approval.review.parent.kind is SourceObjectKind.PULL_REQUEST
    assert approval.review.parent.repository_scoped_number == RepositoryScopedNumber(
        CANONICAL_PULL_REQUEST_NUMBER
    )
    assert approval.review.parent.repository_identity == _repository()


def test_repeating_one_approval_yields_equal_independent_values() -> None:
    first = _approval()
    second = _approval()

    assert first == second
    assert first is not second


def test_the_two_supplied_values_are_preserved_unchanged() -> None:
    review = _review()
    revision = _commit()

    approval = PullRequestReviewRevisionApproval(
        review=review, approved_revision=revision
    )

    assert approval.review == review
    assert approval.approved_revision == revision


# --- approval distinctions -------------------------------------------------


def test_a_different_review_yields_a_distinct_approval() -> None:
    assert _approval() != _approval(
        review=_review(global_id=SYNTHETIC_REVIEW_GLOBAL_ID)
    )


def test_a_different_revision_yields_a_distinct_approval() -> None:
    assert _approval() != _approval(approved_revision=_commit(INTERMEDIATE_REVISION))


def test_a_review_under_another_pull_request_yields_a_distinct_approval() -> None:
    elsewhere = _approval(review=_review(parent=_pull_request("1")))

    assert elsewhere.review.provider_global_id == _approval().review.provider_global_id
    assert elsewhere != _approval()


def test_one_review_may_approve_two_revisions_as_two_values() -> None:
    first = _approval()
    second = _approval(approved_revision=_commit(INTERMEDIATE_REVISION))

    assert first.review == second.review
    assert first != second


# --- pull-request-review subject only --------------------------------------


@pytest.mark.parametrize(
    "kind",
    tuple(
        kind
        for kind in SourceObjectKind
        if kind is not SourceObjectKind.PULL_REQUEST_REVIEW
    ),
)
def test_only_a_pull_request_review_may_approve(kind: SourceObjectKind) -> None:
    payload = _payload()
    _review_payload(payload)["kind"] = kind.value

    with pytest.raises(ValidationError):
        PullRequestReviewRevisionApproval.model_validate_json(json.dumps(payload))


@pytest.mark.parametrize(
    "kind",
    (
        SourceObjectKind.PULL_REQUEST_COMMENT,
        SourceObjectKind.PULL_REQUEST_REVIEW_COMMENT,
        SourceObjectKind.TIMELINE_EVENT,
    ),
)
def test_other_provider_scoped_kinds_are_rejected_in_python_input(
    kind: SourceObjectKind,
) -> None:
    with pytest.raises(ValidationError, match="must identify a pull_request_review"):
        _approval(review=_review(kind=kind))


def test_an_issue_comment_identity_cannot_reach_the_review_position() -> None:
    # P01 already forbids an issue_comment under a pull_request parent, so the
    # value cannot even be built; the approval never sees a malformed review.
    with pytest.raises(ValidationError):
        _review(kind=SourceObjectKind.ISSUE_COMMENT)


def test_the_published_identity_already_requires_a_pull_request_parent() -> None:
    with pytest.raises(ValidationError):
        _review(parent=_issue())


def test_the_approval_does_not_restate_the_pull_request() -> None:
    fields = set(PullRequestReviewRevisionApproval.model_fields)

    assert "pull_request" not in fields
    assert "parent" not in fields
    assert "repository" not in fields
    assert fields == {"review", "approved_revision"}


# --- no revision-role coupling ---------------------------------------------


def test_an_intermediate_revision_may_be_approved() -> None:
    approval = _approval(approved_revision=_commit(INTERMEDIATE_REVISION))

    assert approval.approved_revision.full_digest == INTERMEDIATE_REVISION


def test_the_canonical_base_revision_may_be_approved() -> None:
    approval = _approval(approved_revision=_commit(CANONICAL_BASE_REVISION))

    assert approval.approved_revision.full_digest == CANONICAL_BASE_REVISION


def test_the_approval_carries_no_revision_role() -> None:
    fields = set(PullRequestReviewRevisionApproval.model_fields)

    assert "role" not in fields
    assert "role_assignment" not in fields
    assert "head" not in fields
    for annotation in (
        field.annotation
        for field in PullRequestReviewRevisionApproval.model_fields.values()
    ):
        assert annotation is not RevisionRole
        assert annotation is not RevisionRoleAssignment
        assert annotation is not PullRequestRevisionRoleBinding


def test_the_canonical_head_equality_is_not_enforced_by_the_contract() -> None:
    head_binding = PullRequestRevisionRoleBinding(
        pull_request=_pull_request(),
        role_assignment=RevisionRoleAssignment(
            role=RevisionRole.HEAD, revision=_commit()
        ),
    )
    approval = _approval()

    # The canonical values coincide, but nothing in the contract requires it.
    assert approval.approved_revision == head_binding.role_assignment.revision
    assert (
        _approval(approved_revision=_commit(INTERMEDIATE_REVISION)).approved_revision
        != head_binding.role_assignment.revision
    )


# --- commit-only revision --------------------------------------------------


def test_only_a_commit_identity_may_be_approved() -> None:
    with pytest.raises(ValidationError, match="in Python input"):
        _approval(
            approved_revision=GitTreeIdentity(  # type: ignore[arg-type]
                kind=GitObjectKind.TREE,
                algorithm=GitHashAlgorithm.SHA1,
                full_digest=CANONICAL_HEAD_TREE,
            )
        )
    with pytest.raises(ValidationError, match="in Python input"):
        _approval(
            approved_revision=GitBlobIdentity(  # type: ignore[arg-type]
                kind=GitObjectKind.BLOB,
                algorithm=GitHashAlgorithm.SHA1,
                full_digest=CANONICAL_HEAD_TREE,
            )
        )


@pytest.mark.parametrize(
    "revision",
    (
        {},
        {"kind": "commit"},
        {"kind": "tree", "algorithm": "sha1", "full_digest": CANONICAL_HEAD_TREE},
        {"kind": "blob", "algorithm": "sha1", "full_digest": CANONICAL_HEAD_TREE},
        {"kind": "commit", "algorithm": "sha1", "full_digest": "0" * 40},
        {
            "kind": "commit",
            "algorithm": "sha1",
            "full_digest": CANONICAL_REVIEWED_REVISION.upper(),
        },
        {
            "kind": "commit",
            "algorithm": "sha256",
            "full_digest": CANONICAL_REVIEWED_REVISION,
        },
        {
            "schema_version": 2,
            "kind": "commit",
            "algorithm": "sha1",
            "full_digest": CANONICAL_REVIEWED_REVISION,
        },
        CANONICAL_REVIEWED_REVISION,
        None,
        [],
    ),
)
def test_approval_rejects_malformed_revision_json(revision: object) -> None:
    payload = _payload()
    payload["approved_revision"] = revision

    with pytest.raises(ValidationError):
        PullRequestReviewRevisionApproval.model_validate_json(json.dumps(payload))


def test_a_sha256_review_approval_is_accepted() -> None:
    approval = _approval(
        approved_revision=GitCommitIdentity(
            kind=GitObjectKind.COMMIT,
            algorithm=GitHashAlgorithm.SHA256,
            full_digest="a" * 64,
        )
    )

    assert approval.approved_revision.algorithm is GitHashAlgorithm.SHA256


# --- semantic JSON ---------------------------------------------------------


def test_approval_semantic_json_round_trip_preserves_the_exact_value() -> None:
    approval = _approval()

    restored = PullRequestReviewRevisionApproval.model_validate_json(
        approval.model_dump_json()
    )

    assert restored == approval
    assert restored.model_dump_json() == approval.model_dump_json()


def test_approval_json_payload_carries_exactly_the_two_semantic_keys() -> None:
    payload = _payload()

    assert set(payload) == {"review", "approved_revision"}
    assert "schema_version" not in payload


def test_embedded_children_keep_their_published_json_shape() -> None:
    approval = _approval()
    payload = _payload()

    assert payload["review"] == json.loads(approval.review.model_dump_json())
    assert payload["approved_revision"] == json.loads(
        approval.approved_revision.model_dump_json()
    )
    assert _review_payload(payload)["schema_version"] == 1


def test_approval_json_reconstruction_accepts_a_semantic_mapping() -> None:
    assert (
        PullRequestReviewRevisionApproval.model_validate_json(json.dumps(_payload()))
        == _approval()
    )


# --- model posture ---------------------------------------------------------


def test_approval_is_frozen() -> None:
    approval = _approval()

    for field, value in (
        ("review", _review(global_id=SYNTHETIC_REVIEW_GLOBAL_ID)),
        ("approved_revision", _commit(INTERMEDIATE_REVISION)),
    ):
        with pytest.raises(ValidationError):
            setattr(approval, field, value)

    assert approval == _approval()


def test_approval_rejects_attribute_deletion() -> None:
    approval = _approval()

    with pytest.raises(ValidationError):
        del approval.review

    assert approval == _approval()


def test_constructed_approval_is_revalidated() -> None:
    assert PullRequestReviewRevisionApproval.model_validate(_approval()) == _approval()


def test_approval_revalidates_a_tampered_review_identity() -> None:
    tampered = ProviderScopedSourceObjectIdentity.model_construct(
        schema_version=1,
        kind=SourceObjectKind.PULL_REQUEST_COMMENT,
        provider_global_id=ProviderGlobalId(CANONICAL_REVIEW_GLOBAL_ID),
        parent=_pull_request(),
    )

    with pytest.raises(ValidationError, match="must identify a pull_request_review"):
        _approval(review=tampered)


def test_approval_revalidates_a_tampered_revision() -> None:
    tampered = GitCommitIdentity.model_construct(
        schema_version=1,
        kind=GitObjectKind.COMMIT,
        algorithm=GitHashAlgorithm.SHA1,
        full_digest="not-a-digest",
    )

    with pytest.raises(ValidationError):
        _approval(approved_revision=tampered)


def test_approval_preserves_published_subclass_acceptance() -> None:
    class _SubclassedReview(ProviderScopedSourceObjectIdentity):
        pass

    class _SubclassedCommit(GitCommitIdentity):
        pass

    approval = PullRequestReviewRevisionApproval(
        review=_SubclassedReview(
            kind=SourceObjectKind.PULL_REQUEST_REVIEW,
            provider_global_id=ProviderGlobalId(CANONICAL_REVIEW_GLOBAL_ID),
            parent=_pull_request(),
        ),
        approved_revision=_SubclassedCommit(
            kind=GitObjectKind.COMMIT,
            algorithm=GitHashAlgorithm.SHA1,
            full_digest=CANONICAL_REVIEWED_REVISION,
        ),
    )

    assert approval == _approval()
    assert type(approval.review) is ProviderScopedSourceObjectIdentity
    assert type(approval.approved_revision) is GitCommitIdentity


# --- required fields and closed extras -------------------------------------


@pytest.mark.parametrize("missing", ("review", "approved_revision"))
def test_approval_required_fields_cannot_be_omitted(missing: str) -> None:
    payload = _payload()
    del payload[missing]

    with pytest.raises(ValidationError) as error:
        PullRequestReviewRevisionApproval.model_validate_json(json.dumps(payload))

    assert error.value.errors()[0]["type"] == "missing"
    assert error.value.errors()[0]["loc"] == (missing,)


@pytest.mark.parametrize(
    "extra",
    (
        "approved_at",
        "body",
        "confidence",
        "dismissed",
        "merge_commit",
        "pull_request",
        "rationale",
        "reviewer",
        "schema_version",
        "state",
        "submitted_at",
    ),
)
def test_approval_extra_fields_fail_closed(extra: str) -> None:
    payload = _payload()
    payload[extra] = "unexpected"

    with pytest.raises(ValidationError) as error:
        PullRequestReviewRevisionApproval.model_validate_json(json.dumps(payload))

    assert error.value.errors()[0]["type"] == "extra_forbidden"


def test_approval_has_no_field_beyond_the_two_semantic_positions() -> None:
    assert tuple(PullRequestReviewRevisionApproval.model_fields) == (
        "review",
        "approved_revision",
    )


# --- strict Python input ---------------------------------------------------


@pytest.mark.parametrize(
    "value",
    (
        None,
        CANONICAL_REVIEW_GLOBAL_ID,
        176071572,
        {"kind": "pull_request_review"},
        _pull_request(),
        ProviderGlobalId(CANONICAL_REVIEW_GLOBAL_ID),
    ),
)
def test_approval_rejects_untyped_python_reviews(value: object) -> None:
    with pytest.raises(ValidationError, match="in Python input"):
        PullRequestReviewRevisionApproval(
            review=value,  # type: ignore[arg-type]
            approved_revision=_commit(),
        )


@pytest.mark.parametrize(
    "value",
    (
        None,
        CANONICAL_REVIEWED_REVISION,
        {"kind": "commit"},
        _review(),
    ),
)
def test_approval_rejects_untyped_python_revisions(value: object) -> None:
    with pytest.raises(ValidationError, match="in Python input"):
        PullRequestReviewRevisionApproval(
            review=_review(),
            approved_revision=value,  # type: ignore[arg-type]
        )


def test_approval_python_construction_rejects_a_dumped_mapping() -> None:
    with pytest.raises(ValidationError, match="in Python input"):
        PullRequestReviewRevisionApproval.model_validate(_payload())


def test_approval_rejects_swapped_members() -> None:
    with pytest.raises(ValidationError, match="in Python input"):
        PullRequestReviewRevisionApproval(
            review=_commit(),  # type: ignore[arg-type]
            approved_revision=_review(),  # type: ignore[arg-type]
        )


class _AttributeBackedReview:
    def __init__(self, review: ProviderScopedSourceObjectIdentity) -> None:
        self.schema_version = review.schema_version
        self.kind = review.kind
        self.provider_global_id = review.provider_global_id
        self.parent = review.parent


class _ForeignReview(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    schema_version: object
    kind: object
    provider_global_id: object
    parent: object


def test_approval_rejects_attribute_backed_children_under_from_attributes() -> None:
    with pytest.raises(ValidationError, match="in Python input"):
        PullRequestReviewRevisionApproval.model_validate(
            {
                "review": _AttributeBackedReview(_review()),
                "approved_revision": _commit(),
            },
            from_attributes=True,
        )


def test_approval_rejects_foreign_model_children_under_from_attributes() -> None:
    review = _review()

    with pytest.raises(ValidationError, match="in Python input"):
        PullRequestReviewRevisionApproval.model_validate(
            {
                "review": _ForeignReview(
                    schema_version=review.schema_version,
                    kind=review.kind,
                    provider_global_id=review.provider_global_id,
                    parent=review.parent,
                ),
                "approved_revision": _commit(),
            },
            from_attributes=True,
        )


# --- malformed review JSON -------------------------------------------------


@pytest.mark.parametrize(
    "review",
    (
        {},
        {"kind": "pull_request_review"},
        {
            "kind": "pull_request_review",
            "provider_global_id": "",
        },
        {
            "kind": "pull_request_review",
            "provider_global_id": " 176071572 ",
            "parent": {
                "repository_identity": {
                    "provider": CANONICAL_PROVIDER,
                    "provider_repository_id": CANONICAL_REPOSITORY_ID,
                },
                "kind": "pull_request",
                "repository_scoped_number": CANONICAL_PULL_REQUEST_NUMBER,
            },
        },
        {
            "schema_version": 2,
            "kind": "pull_request_review",
            "provider_global_id": CANONICAL_REVIEW_GLOBAL_ID,
            "parent": {
                "repository_identity": {
                    "provider": CANONICAL_PROVIDER,
                    "provider_repository_id": CANONICAL_REPOSITORY_ID,
                },
                "kind": "pull_request",
                "repository_scoped_number": CANONICAL_PULL_REQUEST_NUMBER,
            },
        },
        {
            "kind": "pull_request_review",
            "provider_global_id": CANONICAL_REVIEW_GLOBAL_ID,
            "parent": {
                "repository_identity": {
                    "provider": CANONICAL_PROVIDER,
                    "provider_repository_id": CANONICAL_REPOSITORY_ID,
                },
                "kind": "issue",
                "repository_scoped_number": CANONICAL_ISSUE_NUMBER,
            },
        },
        CANONICAL_REVIEW_GLOBAL_ID,
        None,
        [],
    ),
)
def test_approval_rejects_malformed_review_json(review: object) -> None:
    payload = _payload()
    payload["review"] = review

    with pytest.raises(ValidationError):
        PullRequestReviewRevisionApproval.model_validate_json(json.dumps(payload))


def test_approval_rejects_a_json_payload_that_is_not_an_object() -> None:
    for payload in ("[]", '"approved"', "1", "null"):
        with pytest.raises(ValidationError):
            PullRequestReviewRevisionApproval.model_validate_json(payload)


# --- non-claim boundary ----------------------------------------------------


@pytest.mark.parametrize(
    "absent",
    (
        "accepted",
        "approved_at",
        "body",
        "ci_status",
        "confidence",
        "contested",
        "dismissed",
        "evidence",
        "evidence_record",
        "merge_commit",
        "merged",
        "occurred_at",
        "rationale",
        "review_state",
        "reviewer",
        "state",
        "submitted_at",
        "test_status",
        "timestamp",
        "verified",
    ),
)
def test_approval_has_no_state_temporal_actor_or_confidence_field(
    absent: str,
) -> None:
    assert absent not in PullRequestReviewRevisionApproval.model_fields


def test_the_approval_is_a_historical_occurrence_not_a_current_state() -> None:
    approval = _approval()

    for absent in ("is_current", "still_approved", "active", "dismissed", "state"):
        assert not hasattr(approval, absent)
    # Two equal approvals carry no notion of which is later or still standing.
    assert approval == _approval()


def test_the_approval_claims_no_correctness_merge_or_repair() -> None:
    approval = _approval()

    for absent in (
        "correct",
        "fixes",
        "repairs",
        "proves",
        "caused_merge",
        "sufficient",
    ):
        assert not hasattr(approval, absent)


def test_no_forbidden_identifier_appears_in_the_approval_surface() -> None:
    tree = ast.parse(HISTORY_SOURCE.read_text(encoding="utf-8"))
    approval_class = next(
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef)
        and node.name == "PullRequestReviewRevisionApproval"
    )
    surface = ast.unparse(approval_class)

    for identifier in FORBIDDEN_APPROVAL_IDENTIFIERS:
        assert identifier not in surface


@pytest.mark.parametrize(
    "rejected",
    (
        "ReviewIdentity",
        "PullRequestReviewIdentity",
        "DevelopmentReviewIdentity",
        "ReviewSubject",
        "ReviewDecision",
        "ReviewState",
        "DevelopmentEvent",
    ),
)
def test_no_second_review_identity_or_state_vocabulary_is_published(
    rejected: str,
) -> None:
    source = HISTORY_SOURCE.read_text(encoding="utf-8")

    assert not hasattr(history_module, rejected)
    assert rejected not in history_module.__all__
    assert rejected not in source


def test_the_approval_module_adds_no_evidence_surface() -> None:
    source = HISTORY_SOURCE.read_text(encoding="utf-8")

    assert "faultatlas.domain.evidence" not in source
    assert "DurableEvidenceRecordReference" not in source
    assert "faultatlas.domain.snapshot" not in source


# --- module surface --------------------------------------------------------


def test_approval_model_surface_is_exact() -> None:
    assert history_module.__all__[-1] == "PullRequestReviewRevisionApproval"
    assert tuple(PullRequestReviewRevisionApproval.model_fields) == (
        "review",
        "approved_revision",
    )
    assert {
        name: field.annotation
        for name, field in PullRequestReviewRevisionApproval.model_fields.items()
    } == {
        "review": ProviderScopedSourceObjectIdentity,
        "approved_revision": GitCommitIdentity,
    }
    for field in PullRequestReviewRevisionApproval.model_fields.values():
        assert field.metadata == []
        assert field.discriminator is None
        assert field.is_required()
    assert PullRequestReviewRevisionApproval.model_config == {
        "frozen": True,
        "extra": "forbid",
        "strict": True,
        "revalidate_instances": "always",
        "validate_default": True,
    }
    assert PullRequestReviewRevisionApproval.__module__ == "faultatlas.domain.history"


def test_the_approval_declares_the_expected_validators() -> None:
    tree = ast.parse(HISTORY_SOURCE.read_text(encoding="utf-8"))
    approval_class = next(
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef)
        and node.name == "PullRequestReviewRevisionApproval"
    )

    assert [type(node) for node in approval_class.body] == [
        ast.Expr,
        ast.Assign,
        ast.AnnAssign,
        ast.AnnAssign,
        ast.FunctionDef,
        ast.FunctionDef,
        ast.FunctionDef,
    ]
    assert [
        node.name for node in approval_class.body if isinstance(node, ast.FunctionDef)
    ] == [
        "_require_typed_python_review",
        "_require_typed_python_approved_revision",
        "_require_pull_request_review_subject",
    ]
    assert [
        (node.target.id, ast.unparse(node.annotation))
        for node in approval_class.body
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name)
    ] == [
        ("review", "ProviderScopedSourceObjectIdentity"),
        ("approved_revision", "GitCommitIdentity"),
    ]


def test_history_module_still_performs_no_io() -> None:
    tree = ast.parse(HISTORY_SOURCE.read_text(encoding="utf-8"))
    referenced = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)} | {
        node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute)
    }

    for capability in (
        "Path",
        "__import__",
        "datetime",
        "getattr",
        "hashlib",
        "httpx",
        "importlib",
        "json",
        "open",
        "os",
        "read_bytes",
        "read_text",
        "requests",
        "setattr",
        "subprocess",
        "urlopen",
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
    assert "PullRequestReviewRevisionApproval" not in IDENTITY_SOURCE.read_text(
        encoding="utf-8"
    )


@pytest.mark.parametrize(
    "literal",
    (
        CANONICAL_REPOSITORY_ID,
        CANONICAL_PULL_REQUEST_NUMBER,
        CANONICAL_REVIEW_GLOBAL_ID,
        CANONICAL_REVIEWED_REVISION,
    ),
)
def test_no_canonical_case_literal_is_embedded_in_production(literal: str) -> None:
    assert literal not in HISTORY_SOURCE.read_text(encoding="utf-8")


def test_the_roadmap_records_the_s03_transition() -> None:
    roadmap = " ".join(
        (REPOSITORY_ROOT / "docs/roadmap.md").read_text(encoding="utf-8").split()
    )
    mapping = roadmap.split("## Current-code mapping", 1)
    assert len(mapping) == 2, "roadmap must retain a current-code mapping section"
    current = mapping[1]

    assert "PullRequestReviewRevisionApproval" in roadmap
    assert "PullRequestReviewRevisionApproval" in current
    assert "`S1.P05.S03` — Pull Request Review Revision Approval (complete)" in roadmap
    assert "`S1.P05.S04` is next and not started" in roadmap
    # The superseded provisional title and status must not survive.
    assert "Review Approval Relation" not in roadmap
    assert "`S1.P05.S03` is next and not started" not in roadmap


def test_canonical_review_literals_remain_locked() -> None:
    assert CANONICAL_REVIEW_GLOBAL_ID == "176071572"
    assert CANONICAL_REVIEWED_REVISION == "690a63b9218f72662cd3a67c6c200b758c88ce12"
    assert CANONICAL_PULL_REQUEST_NUMBER == "4414"
    assert CANONICAL_REPOSITORY_ID == "37489525"
