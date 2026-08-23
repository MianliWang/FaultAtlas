from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest
from pydantic import BaseModel, ConfigDict, ValidationError

import faultatlas.domain.history as history_module
from faultatlas.domain.history import PullRequestRevisionRoleBinding
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
    GitTreeIdentity,
    RevisionRole,
    RevisionRoleAssignment,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
HISTORY_SOURCE = REPOSITORY_ROOT / "src/faultatlas/domain/history.py"
IDENTITY_SOURCE = REPOSITORY_ROOT / "src/faultatlas/domain/identity.py"
REVISION_SOURCE = REPOSITORY_ROOT / "src/faultatlas/domain/revision.py"

CANONICAL_PROVIDER = "github"
CANONICAL_REPOSITORY_ID = "37489525"
CANONICAL_PULL_REQUEST_NUMBER = "4414"
CANONICAL_ISSUE_NUMBER = "4412"
CANONICAL_BASE_REVISION = "4c9cde74ab40027b5761ab9e002af116a4a20df3"
CANONICAL_HEAD_REVISION = "690a63b9218f72662cd3a67c6c200b758c88ce12"
CANONICAL_MERGE_FIRST_PARENT = "5fab0ca3127bc895b611cc03bb3af1ebf9a0dbed"
CANONICAL_MERGE_REVISION = "10cdae8e38e1e1a1f8b1a1c1d1e1f1a1b1c1d1e1"
CANONICAL_HEAD_TREE = "9e5593159e909083009ac9ad72d5d59feb863c44"

SYNTHETIC_REPOSITORY_ID = "12345678"
SYNTHETIC_REVISION = "1111111111111111111111111111111111111111"

FORBIDDEN_BINDING_IDENTIFIERS = (
    "ancestor",
    "ancestry",
    "approval",
    "approved",
    "base_branch",
    "base_ref",
    "branch",
    "change_set",
    "chronology",
    "ci_run",
    "comparison",
    "completeness",
    "confidence",
    "contains",
    "default_branch",
    "descendant",
    "diff",
    "DurableEvidenceRecordReference",
    "evidence",
    "merged_at",
    "occurred_at",
    "parent",
    "reachab",
    "ref_name",
    "review",
    "snapshot",
    "test_run",
    "timestamp",
    "topology",
)


def _repository(repository_id: str = CANONICAL_REPOSITORY_ID) -> RepositoryIdentity:
    return RepositoryIdentity(
        provider=ProviderKey(CANONICAL_PROVIDER),
        provider_repository_id=ProviderRepositoryId(repository_id),
    )


def _pull_request(
    *,
    repository_id: str = CANONICAL_REPOSITORY_ID,
    number: str = CANONICAL_PULL_REQUEST_NUMBER,
) -> NumberedSourceObjectIdentity:
    return NumberedSourceObjectIdentity(
        repository_identity=_repository(repository_id),
        kind=SourceObjectKind.PULL_REQUEST,
        repository_scoped_number=RepositoryScopedNumber(number),
    )


def _issue(
    number: str = CANONICAL_ISSUE_NUMBER,
) -> NumberedSourceObjectIdentity:
    return NumberedSourceObjectIdentity(
        repository_identity=_repository(),
        kind=SourceObjectKind.ISSUE,
        repository_scoped_number=RepositoryScopedNumber(number),
    )


def _commit(
    full_digest: str = CANONICAL_HEAD_REVISION,
    algorithm: GitHashAlgorithm = GitHashAlgorithm.SHA1,
) -> GitCommitIdentity:
    return GitCommitIdentity(
        kind=GitObjectKind.COMMIT,
        algorithm=algorithm,
        full_digest=full_digest,
    )


def _assignment(
    role: RevisionRole = RevisionRole.HEAD,
    full_digest: str = CANONICAL_HEAD_REVISION,
) -> RevisionRoleAssignment:
    return RevisionRoleAssignment(role=role, revision=_commit(full_digest))


def _binding(
    *,
    pull_request: NumberedSourceObjectIdentity | None = None,
    role_assignment: RevisionRoleAssignment | None = None,
) -> PullRequestRevisionRoleBinding:
    return PullRequestRevisionRoleBinding(
        pull_request=_pull_request() if pull_request is None else pull_request,
        role_assignment=_assignment() if role_assignment is None else role_assignment,
    )


def _canonical_base_binding() -> PullRequestRevisionRoleBinding:
    return _binding(
        role_assignment=_assignment(RevisionRole.BASE, CANONICAL_BASE_REVISION)
    )


def _canonical_head_binding() -> PullRequestRevisionRoleBinding:
    return _binding(
        role_assignment=_assignment(RevisionRole.HEAD, CANONICAL_HEAD_REVISION)
    )


def _head_payload() -> dict[str, object]:
    return {
        "pull_request": {
            "schema_version": 1,
            "repository_identity": {
                "schema_version": 1,
                "provider": CANONICAL_PROVIDER,
                "provider_repository_id": CANONICAL_REPOSITORY_ID,
            },
            "kind": "pull_request",
            "repository_scoped_number": CANONICAL_PULL_REQUEST_NUMBER,
        },
        "role_assignment": {
            "schema_version": 1,
            "role": "head",
            "revision": {
                "schema_version": 1,
                "kind": "commit",
                "algorithm": "sha1",
                "full_digest": CANONICAL_HEAD_REVISION,
            },
        },
    }


# --- canonical witnesses ---------------------------------------------------


def test_canonical_pull_request_base_revision_binds() -> None:
    binding = _canonical_base_binding()

    assert binding.pull_request == _pull_request()
    assert binding.pull_request.kind is SourceObjectKind.PULL_REQUEST
    assert binding.role_assignment.role is RevisionRole.BASE
    assert binding.role_assignment.revision.full_digest == CANONICAL_BASE_REVISION


def test_canonical_pull_request_head_revision_binds() -> None:
    binding = _canonical_head_binding()

    assert binding.pull_request == _pull_request()
    assert binding.role_assignment.role is RevisionRole.HEAD
    assert binding.role_assignment.revision.full_digest == CANONICAL_HEAD_REVISION


def test_the_two_canonical_bindings_share_one_pull_request() -> None:
    assert _canonical_base_binding().pull_request == (
        _canonical_head_binding().pull_request
    )


def test_the_two_canonical_bindings_are_distinct_values() -> None:
    assert _canonical_base_binding() != _canonical_head_binding()


def test_repeating_one_binding_yields_equal_independent_values() -> None:
    first = _canonical_head_binding()
    second = _canonical_head_binding()

    assert first == second
    assert first is not second


def test_the_two_supplied_values_are_preserved_unchanged() -> None:
    pull_request = _pull_request()
    role_assignment = _assignment(RevisionRole.BASE, CANONICAL_BASE_REVISION)

    binding = PullRequestRevisionRoleBinding(
        pull_request=pull_request,
        role_assignment=role_assignment,
    )

    assert binding.pull_request == pull_request
    assert binding.role_assignment == role_assignment


# --- binding distinctions --------------------------------------------------


def test_role_alone_distinguishes_two_bindings() -> None:
    as_base = _binding(
        role_assignment=_assignment(RevisionRole.BASE, CANONICAL_HEAD_REVISION)
    )
    as_head = _binding(
        role_assignment=_assignment(RevisionRole.HEAD, CANONICAL_HEAD_REVISION)
    )

    assert as_base.role_assignment.revision == as_head.role_assignment.revision
    assert as_base != as_head


def test_revision_alone_distinguishes_two_bindings() -> None:
    assert _canonical_head_binding() != _binding(
        role_assignment=_assignment(RevisionRole.HEAD, SYNTHETIC_REVISION)
    )


def test_the_same_role_and_revision_in_another_repository_is_another_binding() -> None:
    canonical = _canonical_head_binding()
    elsewhere = _binding(
        pull_request=_pull_request(repository_id=SYNTHETIC_REPOSITORY_ID)
    )

    assert canonical.role_assignment == elsewhere.role_assignment
    assert canonical != elsewhere


def test_another_pull_request_number_is_another_binding() -> None:
    assert _canonical_head_binding() != _binding(pull_request=_pull_request(number="1"))


def test_a_pull_request_may_bind_both_recorded_roles() -> None:
    bindings = (_canonical_base_binding(), _canonical_head_binding())

    assert bindings[0] != bindings[1]
    assert [binding.pull_request for binding in bindings] == [
        _pull_request(),
        _pull_request(),
    ]
    assert [binding.role_assignment.role for binding in bindings] == [
        RevisionRole.BASE,
        RevisionRole.HEAD,
    ]


# --- pull-request-only subject ---------------------------------------------


def test_an_issue_subject_is_rejected_in_python_input() -> None:
    with pytest.raises(ValidationError, match="must identify a pull_request"):
        _binding(pull_request=_issue())


def test_an_issue_subject_is_rejected_in_json_input() -> None:
    payload = _head_payload()
    subject = payload["pull_request"]
    assert isinstance(subject, dict)
    subject["kind"] = "issue"

    with pytest.raises(ValidationError, match="must identify a pull_request"):
        PullRequestRevisionRoleBinding.model_validate_json(json.dumps(payload))


def test_the_canonical_issue_number_is_still_rejected_as_a_subject() -> None:
    with pytest.raises(ValidationError, match="must identify a pull_request"):
        _binding(pull_request=_issue(CANONICAL_ISSUE_NUMBER))


@pytest.mark.parametrize(
    "kind",
    tuple(kind for kind in SourceObjectKind if kind is not SourceObjectKind.ISSUE),
)
def test_only_the_pull_request_kind_is_accepted(kind: SourceObjectKind) -> None:
    if kind is SourceObjectKind.PULL_REQUEST:
        assert _binding().pull_request.kind is kind
        return
    payload = _head_payload()
    subject = payload["pull_request"]
    assert isinstance(subject, dict)
    subject["kind"] = kind.value

    with pytest.raises(ValidationError):
        PullRequestRevisionRoleBinding.model_validate_json(json.dumps(payload))


# --- recorded roles only ---------------------------------------------------


@pytest.mark.parametrize(
    ("role", "full_digest"),
    (
        (RevisionRole.MERGE_FIRST_PARENT, CANONICAL_MERGE_FIRST_PARENT),
        (RevisionRole.MERGE, CANONICAL_MERGE_REVISION),
    ),
)
def test_merge_roles_are_rejected_in_python_input(
    role: RevisionRole,
    full_digest: str,
) -> None:
    with pytest.raises(ValidationError, match="must be base or head"):
        _binding(role_assignment=_assignment(role, full_digest))


@pytest.mark.parametrize("role", ("merge", "merge_first_parent"))
def test_merge_roles_are_rejected_in_json_input(role: str) -> None:
    payload = _head_payload()
    assignment = payload["role_assignment"]
    assert isinstance(assignment, dict)
    assignment["role"] = role

    with pytest.raises(ValidationError, match="must be base or head"):
        PullRequestRevisionRoleBinding.model_validate_json(json.dumps(payload))


@pytest.mark.parametrize("unknown", ("reviewed", "published", "Base", "BASE", "", "1"))
def test_unknown_roles_fail_closed(unknown: str) -> None:
    payload = _head_payload()
    assignment = payload["role_assignment"]
    assert isinstance(assignment, dict)
    assignment["role"] = unknown

    with pytest.raises(ValidationError):
        PullRequestRevisionRoleBinding.model_validate_json(json.dumps(payload))


def test_the_published_revision_role_vocabulary_is_not_redefined() -> None:
    assert [member.value for member in RevisionRole] == [
        "base",
        "head",
        "merge_first_parent",
        "merge",
    ]
    assert not [
        name
        for name in vars(history_module)
        if name.endswith("Role") and name[0] != "R"
    ]


# --- semantic JSON ---------------------------------------------------------


def test_base_binding_semantic_json_round_trip_preserves_exact_value() -> None:
    binding = _canonical_base_binding()

    restored = PullRequestRevisionRoleBinding.model_validate_json(
        binding.model_dump_json()
    )

    assert restored == binding
    assert restored.model_dump_json() == binding.model_dump_json()


def test_head_binding_semantic_json_round_trip_preserves_exact_value() -> None:
    binding = _canonical_head_binding()

    restored = PullRequestRevisionRoleBinding.model_validate_json(
        binding.model_dump_json()
    )

    assert restored == binding
    assert restored.model_dump_json() == binding.model_dump_json()


def test_binding_json_payload_carries_exactly_the_two_semantic_keys() -> None:
    payload = json.loads(_canonical_head_binding().model_dump_json())

    assert set(payload) == {"pull_request", "role_assignment"}
    assert payload == _head_payload()


def test_binding_carries_no_schema_version_of_its_own() -> None:
    payload = json.loads(_canonical_head_binding().model_dump_json())

    assert "schema_version" not in payload
    assert payload["pull_request"]["schema_version"] == 1
    assert payload["role_assignment"]["schema_version"] == 1
    assert payload["role_assignment"]["revision"]["schema_version"] == 1


def test_embedded_children_keep_their_published_json_shape() -> None:
    binding = _canonical_head_binding()
    payload = json.loads(binding.model_dump_json())

    assert payload["pull_request"] == json.loads(binding.pull_request.model_dump_json())
    assert payload["role_assignment"] == json.loads(
        binding.role_assignment.model_dump_json()
    )


# --- model posture ---------------------------------------------------------


def test_binding_is_frozen() -> None:
    binding = _canonical_head_binding()

    for field, value in (
        ("pull_request", _pull_request(repository_id=SYNTHETIC_REPOSITORY_ID)),
        ("role_assignment", _assignment(RevisionRole.BASE, CANONICAL_BASE_REVISION)),
    ):
        with pytest.raises(ValidationError):
            setattr(binding, field, value)

    assert binding == _canonical_head_binding()


def test_binding_rejects_attribute_deletion() -> None:
    binding = _canonical_head_binding()

    with pytest.raises(ValidationError):
        del binding.role_assignment

    assert binding == _canonical_head_binding()


def test_constructed_binding_is_revalidated() -> None:
    assert (
        PullRequestRevisionRoleBinding.model_validate(_canonical_head_binding())
        == _canonical_head_binding()
    )


def test_binding_revalidates_a_nested_pull_request_identity() -> None:
    tampered = NumberedSourceObjectIdentity.model_construct(
        schema_version=1,
        repository_identity=_repository(),
        kind=SourceObjectKind.PULL_REQUEST,
        repository_scoped_number="04414",
    )

    with pytest.raises(ValidationError) as error:
        _binding(pull_request=tampered)

    assert error.value.errors()[0]["loc"] == (
        "pull_request",
        "repository_scoped_number",
    )


def test_binding_revalidates_a_nested_role_assignment() -> None:
    tampered = RevisionRoleAssignment.model_construct(
        schema_version=1,
        role=RevisionRole.HEAD,
        revision=GitCommitIdentity.model_construct(
            schema_version=1,
            kind=GitObjectKind.COMMIT,
            algorithm=GitHashAlgorithm.SHA1,
            full_digest="not-a-digest",
        ),
    )

    with pytest.raises(ValidationError):
        _binding(role_assignment=tampered)


def test_binding_revalidates_a_tampered_subject_kind() -> None:
    tampered = NumberedSourceObjectIdentity.model_construct(
        schema_version=1,
        repository_identity=_repository(),
        kind=SourceObjectKind.ISSUE_COMMENT,
        repository_scoped_number=RepositoryScopedNumber(CANONICAL_PULL_REQUEST_NUMBER),
    )

    with pytest.raises(ValidationError):
        _binding(pull_request=tampered)


def test_binding_preserves_published_subclass_acceptance() -> None:
    class _SubclassedPullRequest(NumberedSourceObjectIdentity):
        pass

    class _SubclassedAssignment(RevisionRoleAssignment):
        pass

    binding = PullRequestRevisionRoleBinding(
        pull_request=_SubclassedPullRequest(
            repository_identity=_repository(),
            kind=SourceObjectKind.PULL_REQUEST,
            repository_scoped_number=RepositoryScopedNumber(
                CANONICAL_PULL_REQUEST_NUMBER
            ),
        ),
        role_assignment=_SubclassedAssignment(
            role=RevisionRole.HEAD,
            revision=_commit(),
        ),
    )

    assert binding == _canonical_head_binding()
    assert type(binding.pull_request) is NumberedSourceObjectIdentity
    assert type(binding.role_assignment) is RevisionRoleAssignment


def test_binding_preserves_published_predecessor_input_semantics() -> None:
    permissive = NumberedSourceObjectIdentity(
        repository_identity=_repository(),
        kind=SourceObjectKind.PULL_REQUEST,
        repository_scoped_number=CANONICAL_PULL_REQUEST_NUMBER,  # type: ignore[arg-type]
    )

    assert _binding(pull_request=permissive) == _canonical_head_binding()


# --- required fields and closed extras -------------------------------------


@pytest.mark.parametrize("missing", ("pull_request", "role_assignment"))
def test_binding_required_fields_cannot_be_omitted(missing: str) -> None:
    payload = _head_payload()
    del payload[missing]

    with pytest.raises(ValidationError) as error:
        PullRequestRevisionRoleBinding.model_validate_json(json.dumps(payload))

    assert error.value.errors()[0]["type"] == "missing"
    assert error.value.errors()[0]["loc"] == (missing,)


@pytest.mark.parametrize(
    "extra",
    (
        "ancestry",
        "base_ref",
        "branch",
        "change_set",
        "comparison",
        "default_branch",
        "evidence",
        "merged_at",
        "parent",
        "review",
        "schema_version",
        "snapshot",
        "repository",
        "role",
        "revision",
    ),
)
def test_binding_extra_fields_fail_closed(extra: str) -> None:
    payload = _head_payload()
    payload[extra] = "unexpected"

    with pytest.raises(ValidationError) as error:
        PullRequestRevisionRoleBinding.model_validate_json(json.dumps(payload))

    assert error.value.errors()[0]["type"] == "extra_forbidden"


def test_binding_has_no_field_beyond_the_two_semantic_positions() -> None:
    assert tuple(PullRequestRevisionRoleBinding.model_fields) == (
        "pull_request",
        "role_assignment",
    )


# --- strict Python input ---------------------------------------------------


@pytest.mark.parametrize(
    "value",
    (
        None,
        CANONICAL_PULL_REQUEST_NUMBER,
        4414,
        {"kind": "pull_request"},
        _assignment(),
        _repository(),
    ),
)
def test_binding_rejects_untyped_python_pull_requests(value: object) -> None:
    with pytest.raises(ValidationError, match="in Python input"):
        PullRequestRevisionRoleBinding(
            pull_request=value,  # type: ignore[arg-type]
            role_assignment=_assignment(),
        )


@pytest.mark.parametrize(
    "value",
    (
        None,
        "head",
        {"role": "head"},
        RevisionRole.HEAD,
        _commit(),
    ),
)
def test_binding_rejects_untyped_python_role_assignments(value: object) -> None:
    with pytest.raises(ValidationError, match="in Python input"):
        PullRequestRevisionRoleBinding(
            pull_request=_pull_request(),
            role_assignment=value,  # type: ignore[arg-type]
        )


def test_binding_python_construction_rejects_a_dumped_mapping() -> None:
    with pytest.raises(ValidationError, match="in Python input"):
        PullRequestRevisionRoleBinding.model_validate(_head_payload())


def test_binding_rejects_swapped_members() -> None:
    with pytest.raises(ValidationError, match="in Python input"):
        PullRequestRevisionRoleBinding(
            pull_request=_assignment(),  # type: ignore[arg-type]
            role_assignment=_pull_request(),  # type: ignore[arg-type]
        )


class _AttributeBackedPullRequest:
    def __init__(self, pull_request: NumberedSourceObjectIdentity) -> None:
        self.schema_version = pull_request.schema_version
        self.repository_identity = pull_request.repository_identity
        self.kind = pull_request.kind
        self.repository_scoped_number = pull_request.repository_scoped_number


class _AttributeBackedAssignment:
    def __init__(self, assignment: RevisionRoleAssignment) -> None:
        self.schema_version = assignment.schema_version
        self.role = assignment.role
        self.revision = assignment.revision


class _ForeignPullRequest(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    schema_version: object
    repository_identity: object
    kind: object
    repository_scoped_number: object


class _ForeignAssignment(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    schema_version: object
    role: object
    revision: object


def test_binding_rejects_attribute_backed_children_under_from_attributes() -> None:
    with pytest.raises(ValidationError, match="in Python input"):
        PullRequestRevisionRoleBinding.model_validate(
            {
                "pull_request": _AttributeBackedPullRequest(_pull_request()),
                "role_assignment": _assignment(),
            },
            from_attributes=True,
        )
    with pytest.raises(ValidationError, match="in Python input"):
        PullRequestRevisionRoleBinding.model_validate(
            {
                "pull_request": _pull_request(),
                "role_assignment": _AttributeBackedAssignment(_assignment()),
            },
            from_attributes=True,
        )


def test_binding_rejects_foreign_model_children_under_from_attributes() -> None:
    pull_request = _pull_request()
    assignment = _assignment()

    with pytest.raises(ValidationError, match="in Python input"):
        PullRequestRevisionRoleBinding.model_validate(
            {
                "pull_request": _ForeignPullRequest(
                    schema_version=pull_request.schema_version,
                    repository_identity=pull_request.repository_identity,
                    kind=pull_request.kind,
                    repository_scoped_number=(pull_request.repository_scoped_number),
                ),
                "role_assignment": assignment,
            },
            from_attributes=True,
        )
    with pytest.raises(ValidationError, match="in Python input"):
        PullRequestRevisionRoleBinding.model_validate(
            {
                "pull_request": pull_request,
                "role_assignment": _ForeignAssignment(
                    schema_version=assignment.schema_version,
                    role=assignment.role,
                    revision=assignment.revision,
                ),
            },
            from_attributes=True,
        )


# --- malformed child JSON --------------------------------------------------


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
        {
            "repository_identity": {
                "provider": CANONICAL_PROVIDER,
                "provider_repository_id": CANONICAL_REPOSITORY_ID,
            },
            "kind": "pull_request",
            "repository_scoped_number": CANONICAL_PULL_REQUEST_NUMBER,
            "unexpected": 1,
        },
        CANONICAL_PULL_REQUEST_NUMBER,
        None,
        [],
    ),
)
def test_binding_rejects_malformed_pull_request_json(pull_request: object) -> None:
    payload = _head_payload()
    payload["pull_request"] = pull_request

    with pytest.raises(ValidationError):
        PullRequestRevisionRoleBinding.model_validate_json(json.dumps(payload))


@pytest.mark.parametrize(
    "role_assignment",
    (
        {},
        {"role": "head"},
        {
            "role": "head",
            "revision": {
                "kind": "tree",
                "algorithm": "sha1",
                "full_digest": CANONICAL_HEAD_TREE,
            },
        },
        {
            "role": "head",
            "revision": {
                "kind": "commit",
                "algorithm": "sha1",
                "full_digest": CANONICAL_HEAD_REVISION.upper(),
            },
        },
        {
            "role": "head",
            "revision": {
                "kind": "commit",
                "algorithm": "sha1",
                "full_digest": "0" * 40,
            },
        },
        {
            "role": "head",
            "revision": {
                "kind": "commit",
                "algorithm": "sha256",
                "full_digest": CANONICAL_HEAD_REVISION,
            },
        },
        {
            "schema_version": 2,
            "role": "head",
            "revision": {
                "kind": "commit",
                "algorithm": "sha1",
                "full_digest": CANONICAL_HEAD_REVISION,
            },
        },
        "head",
        None,
        [],
    ),
)
def test_binding_rejects_malformed_role_assignment_json(
    role_assignment: object,
) -> None:
    payload = _head_payload()
    payload["role_assignment"] = role_assignment

    with pytest.raises(ValidationError):
        PullRequestRevisionRoleBinding.model_validate_json(json.dumps(payload))


def test_binding_rejects_a_json_payload_that_is_not_an_object() -> None:
    for payload in ("[]", '"head"', "1", "null"):
        with pytest.raises(ValidationError):
            PullRequestRevisionRoleBinding.model_validate_json(payload)


@pytest.mark.parametrize("git_object", (GitTreeIdentity, GitBlobIdentity))
def test_only_commit_identities_can_be_bound(git_object: type[BaseModel]) -> None:
    with pytest.raises(ValidationError):
        RevisionRoleAssignment(
            role=RevisionRole.HEAD,
            revision=git_object(  # type: ignore[arg-type]
                kind=(
                    GitObjectKind.TREE
                    if git_object is GitTreeIdentity
                    else GitObjectKind.BLOB
                ),
                algorithm=GitHashAlgorithm.SHA1,
                full_digest=CANONICAL_HEAD_TREE,
            ),
        )


# --- non-claim boundary ----------------------------------------------------


@pytest.mark.parametrize(
    "absent",
    (
        "ancestry",
        "base_ref",
        "branch",
        "change_set",
        "comparison",
        "default_branch",
        "diff",
        "evidence",
        "evidence_record",
        "head_ref",
        "head_repository",
        "merge_commit",
        "merged_at",
        "occurred_at",
        "ordered_parents",
        "parent",
        "reachable",
        "ref",
        "review",
        "reviewed_revision",
        "snapshot",
        "timestamp",
    ),
)
def test_binding_has_no_topology_ref_or_temporal_field(absent: str) -> None:
    assert absent not in PullRequestRevisionRoleBinding.model_fields


def test_binding_does_not_claim_the_revision_lives_in_the_pull_requests_repository() -> (
    None
):
    binding = _canonical_head_binding()

    assert not hasattr(binding.role_assignment, "repository_identity")
    assert not hasattr(binding.role_assignment.revision, "repository_identity")
    assert not hasattr(binding, "head_repository")
    assert "repository" not in set(PullRequestRevisionRoleBinding.model_fields)


def test_a_fork_head_revision_binds_without_any_containment_claim() -> None:
    binding = _binding(
        role_assignment=_assignment(RevisionRole.HEAD, SYNTHETIC_REVISION)
    )

    assert binding.pull_request.repository_identity == _repository()
    assert set(json.loads(binding.model_dump_json())) == {
        "pull_request",
        "role_assignment",
    }


def test_base_and_head_bindings_assert_no_path_between_them() -> None:
    base = _canonical_base_binding()
    head = _canonical_head_binding()

    for binding in (base, head):
        assert not hasattr(binding, "ancestry")
        assert not hasattr(binding, "ordered_parents")
        assert not hasattr(binding, "descends_from")
    assert base.role_assignment.revision != head.role_assignment.revision


def test_binding_makes_no_existence_or_completeness_claim() -> None:
    absent_from_provider = _binding(
        pull_request=_pull_request(number="99999999"),
        role_assignment=_assignment(RevisionRole.HEAD, SYNTHETIC_REVISION),
    )

    assert absent_from_provider.pull_request.repository_scoped_number == (
        RepositoryScopedNumber("99999999")
    )
    assert not hasattr(absent_from_provider, "complete")
    assert not hasattr(absent_from_provider, "role_count")


def test_no_forbidden_identifier_appears_in_the_binding_module_surface() -> None:
    tree = ast.parse(HISTORY_SOURCE.read_text(encoding="utf-8"))
    # Scoped to the S01 binding and the module-level nodes it declares; later
    # relations in this module own their own forbidden-identifier assurance.
    body = [
        node
        for node in tree.body
        if not isinstance(node, ast.Expr)
        and not (
            isinstance(node, ast.ClassDef)
            and node.name != "PullRequestRevisionRoleBinding"
        )
        and not (
            isinstance(node, ast.Assign)
            and any(
                isinstance(target, ast.Name)
                and target.id in {"_MIN_CHANGED_PATHS", "_MAX_CHANGED_PATHS"}
                for target in node.targets
            )
        )
    ]
    surface = "\n".join(ast.unparse(node) for node in body)

    for identifier in FORBIDDEN_BINDING_IDENTIFIERS:
        assert identifier not in surface


@pytest.mark.parametrize(
    "rejected",
    (
        "DevelopmentSubjectIdentity",
        "DevelopmentSubjectKind",
        "DevelopmentHistory",
        "DevelopmentHistoryIdentity",
        "SnapshotTransition",
        "ProviderGlobalId",
        "provider_global_id",
    ),
)
def test_the_rejected_subject_identity_design_is_not_resurrected(
    rejected: str,
) -> None:
    source = HISTORY_SOURCE.read_text(encoding="utf-8")

    assert not hasattr(history_module, rejected)
    assert rejected not in history_module.__all__
    assert rejected not in source


# --- module surface --------------------------------------------------------


def test_model_and_module_surfaces_are_exact_and_local() -> None:
    assert history_module.__all__ == [
        "PullRequestRevisionRoleBinding",
        "ChangedPathStatus",
        "PullRequestChangedPath",
        "PullRequestChangeSet",
        "PullRequestReviewRevisionApproval",
    ]
    assert history_module.__all__[0] == "PullRequestRevisionRoleBinding"
    assert sorted(
        name for name in vars(history_module) if not name.startswith("_")
    ) == [
        "Annotated",
        "BaseModel",
        "ChangedPathStatus",
        "ConfigDict",
        "Field",
        "GitBlobIdentity",
        "GitCommitIdentity",
        "GitRepositoryPath",
        "NumberedSourceObjectIdentity",
        "ProviderScopedSourceObjectIdentity",
        "PullRequestChangeSet",
        "PullRequestChangedPath",
        "PullRequestReviewRevisionApproval",
        "PullRequestRevisionRoleBinding",
        "RevisionRole",
        "RevisionRoleAssignment",
        "Self",
        "SourceObjectKind",
        "StrEnum",
        "ValidationInfo",
        "cast",
        "field_validator",
        "model_validator",
    ]
    assert PullRequestRevisionRoleBinding.__module__ == "faultatlas.domain.history"

    assert tuple(PullRequestRevisionRoleBinding.model_fields) == (
        "pull_request",
        "role_assignment",
    )
    annotations = {
        name: field.annotation
        for name, field in PullRequestRevisionRoleBinding.model_fields.items()
    }
    assert annotations == {
        "pull_request": NumberedSourceObjectIdentity,
        "role_assignment": RevisionRoleAssignment,
    }
    for field in PullRequestRevisionRoleBinding.model_fields.values():
        assert field.metadata == []
        assert field.discriminator is None
        assert field.is_required()

    assert PullRequestRevisionRoleBinding.model_config == {
        "frozen": True,
        "extra": "forbid",
        "strict": True,
        "revalidate_instances": "always",
        "validate_default": True,
    }


def test_history_module_has_only_the_bounded_relation_and_no_io_calls() -> None:
    tree = ast.parse(HISTORY_SOURCE.read_text(encoding="utf-8"))

    assert [type(node) for node in tree.body] == [
        ast.Expr,
        ast.ImportFrom,
        ast.ImportFrom,
        ast.ImportFrom,
        ast.ImportFrom,
        ast.ImportFrom,
        ast.Assign,
        ast.Assign,
        ast.Assign,
        ast.AnnAssign,
        ast.ClassDef,
        ast.ClassDef,
        ast.ClassDef,
        ast.ClassDef,
        ast.ClassDef,
    ]
    assert not [node for node in tree.body if isinstance(node, ast.Import)]
    assert [
        (node.module, tuple(alias.name for alias in node.names))
        for node in tree.body
        if isinstance(node, ast.ImportFrom)
    ] == [
        ("enum", ("StrEnum",)),
        ("typing", ("Annotated", "Self", "cast")),
        (
            "pydantic",
            (
                "BaseModel",
                "ConfigDict",
                "Field",
                "ValidationInfo",
                "field_validator",
                "model_validator",
            ),
        ),
        (
            "faultatlas.domain.identity",
            (
                "NumberedSourceObjectIdentity",
                "ProviderScopedSourceObjectIdentity",
                "SourceObjectKind",
            ),
        ),
        (
            "faultatlas.domain.revision",
            (
                "GitBlobIdentity",
                "GitCommitIdentity",
                "GitRepositoryPath",
                "RevisionRole",
                "RevisionRoleAssignment",
            ),
        ),
    ]
    assert not [
        alias
        for node in tree.body
        if isinstance(node, ast.ImportFrom)
        for alias in node.names
        if alias.asname is not None
    ]
    assert not [
        node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.TypeAlias))
    ]
    assert [
        target.id
        for node in tree.body
        if isinstance(node, ast.Assign)
        for target in node.targets
        if isinstance(target, ast.Name)
    ] == ["__all__", "_MIN_CHANGED_PATHS", "_MAX_CHANGED_PATHS"]
    assert [
        (node.target.id, ast.unparse(node.annotation))
        for node in tree.body
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name)
    ] == [("_PULL_REQUEST_RECORDED_ROLES", "frozenset[RevisionRole]")]

    classes = [node for node in tree.body if isinstance(node, ast.ClassDef)]
    assert [node.name for node in classes] == [
        "PullRequestRevisionRoleBinding",
        "ChangedPathStatus",
        "PullRequestChangedPath",
        "PullRequestChangeSet",
        "PullRequestReviewRevisionApproval",
    ]
    # This oracle owns only the S01 binding; the S02 values own their own.
    classes = classes[:1]
    assert [ast.unparse(base) for base in classes[0].bases] == ["BaseModel"]
    assert not classes[0].keywords
    assert not classes[0].decorator_list
    assert [type(node) for node in classes[0].body] == [
        ast.Expr,
        ast.Assign,
        ast.AnnAssign,
        ast.AnnAssign,
        ast.FunctionDef,
        ast.FunctionDef,
        ast.FunctionDef,
        ast.FunctionDef,
    ]
    assert [
        target.id
        for node in classes[0].body
        if isinstance(node, ast.Assign)
        for target in node.targets
        if isinstance(target, ast.Name)
    ] == ["model_config"]
    assert [
        (node.target.id, ast.unparse(node.annotation))
        for node in classes[0].body
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name)
    ] == [
        ("pull_request", "NumberedSourceObjectIdentity"),
        ("role_assignment", "RevisionRoleAssignment"),
    ]
    assert not [
        node
        for node in classes[0].body
        if isinstance(node, ast.AnnAssign) and node.value is not None
    ]
    assert [
        node.name
        for node in classes[0].body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    ] == [
        "_require_typed_python_pull_request",
        "_require_typed_python_role_assignment",
        "_require_pull_request_subject",
        "_require_pull_request_recorded_role",
    ]

    # This oracle owns the S01 binding and the module-level nodes it declares;
    # the S02 values are covered by their own focused oracle.
    owned = [
        node
        for node in tree.body
        if not (
            isinstance(node, ast.ClassDef)
            and node.name != "PullRequestRevisionRoleBinding"
        )
        and not (
            isinstance(node, ast.Assign)
            and any(
                isinstance(target, ast.Name)
                and target.id in {"_MIN_CHANGED_PATHS", "_MAX_CHANGED_PATHS"}
                for target in node.targets
            )
        )
    ]
    comparisons = [
        node
        for entry in owned
        for node in ast.walk(entry)
        if isinstance(node, ast.Compare)
    ]
    assert [
        (
            [type(operator) for operator in comparison.ops],
            [
                ast.unparse(comparison.left),
                *(ast.unparse(other) for other in comparison.comparators),
            ],
        )
        for comparison in comparisons
    ] == [
        (
            [ast.IsNot],
            ["self.pull_request.kind", "SourceObjectKind.PULL_REQUEST"],
        ),
        (
            [ast.NotIn],
            ["self.role_assignment.role", "_PULL_REQUEST_RECORDED_ROLES"],
        ),
        ([ast.Eq], ["info.mode", "'python'"]),
        ([ast.Eq], ["info.mode", "'python'"]),
    ]
    assert {
        node.func.id
        for entry in owned
        for node in ast.walk(entry)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    } == {
        "ConfigDict",
        "ValueError",
        "field_validator",
        "frozenset",
        "isinstance",
        "model_validator",
    }
    assert not [
        node
        for entry in owned
        for node in ast.walk(entry)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    ]
    assert {
        node.id
        for entry in owned
        for node in ast.walk(entry)
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load)
    } == {
        "BaseModel",
        "ConfigDict",
        "NumberedSourceObjectIdentity",
        "RevisionRole",
        "RevisionRoleAssignment",
        "Self",
        "SourceObjectKind",
        "ValidationInfo",
        "ValueError",
        "_PULL_REQUEST_RECORDED_ROLES",
        "classmethod",
        "field_validator",
        "frozenset",
        "info",
        "isinstance",
        "model_validator",
        "object",
        "self",
        "value",
    }


def test_history_module_declares_no_reflection_or_capability_surface() -> None:
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
        "loads",
        "open",
        "os",
        "read_bytes",
        "read_text",
        "requests",
        "setattr",
        "subprocess",
        "urlopen",
        "write_bytes",
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

    for source in (IDENTITY_SOURCE, REVISION_SOURCE):
        text = source.read_text(encoding="utf-8")
        assert "domain.history" not in text
        assert "PullRequestRevisionRoleBinding" not in text


def test_history_module_neither_reads_the_corpus_nor_touches_evidence() -> None:
    source = HISTORY_SOURCE.read_text(encoding="utf-8")

    assert "reference_corpus" not in source
    assert "docs/reference_cases" not in source
    assert "faultatlas.domain.evidence" not in source
    assert "faultatlas.domain.snapshot" not in source


@pytest.mark.parametrize(
    "literal",
    (
        CANONICAL_REPOSITORY_ID,
        CANONICAL_PULL_REQUEST_NUMBER,
        CANONICAL_BASE_REVISION,
        CANONICAL_HEAD_REVISION,
    ),
)
def test_no_canonical_case_literal_is_embedded_in_production(literal: str) -> None:
    assert literal not in HISTORY_SOURCE.read_text(encoding="utf-8")


def test_the_roadmap_current_code_mapping_names_this_module() -> None:
    roadmap = " ".join(
        (REPOSITORY_ROOT / "docs/roadmap.md").read_text(encoding="utf-8").split()
    )
    mapping = roadmap.split("## Current-code mapping", 1)
    assert len(mapping) == 2, "roadmap must retain a current-code mapping section"
    current = mapping[1]

    assert "faultatlas.domain.history" in current
    assert "PullRequestRevisionRoleBinding" in current
    assert "`S1.P05` is active and incomplete" in current
    assert (
        "`S1.P05` is `eligible_to_begin` with implementation state `not_started`"
        not in current
    )


def test_canonical_case_literals_remain_locked() -> None:
    assert CANONICAL_PROVIDER == "github"
    assert CANONICAL_REPOSITORY_ID == "37489525"
    assert CANONICAL_PULL_REQUEST_NUMBER == "4414"
    assert CANONICAL_ISSUE_NUMBER == "4412"
    assert CANONICAL_BASE_REVISION == "4c9cde74ab40027b5761ab9e002af116a4a20df3"
    assert CANONICAL_HEAD_REVISION == "690a63b9218f72662cd3a67c6c200b758c88ce12"
