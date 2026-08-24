from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Any, cast

import pytest
from pydantic import BaseModel, ConfigDict, ValidationError

import faultatlas.domain.history as history_module
from faultatlas.domain.history import (
    PullRequestHeadRefDeletion,
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
    GitCommitIdentity,
    GitHashAlgorithm,
    GitObjectKind,
    GitRefName,
    GitRefNamespace,
    GitRefObservation,
    RevisionRole,
    RevisionRoleAssignment,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
HISTORY_SOURCE = REPOSITORY_ROOT / "src/faultatlas/domain/history.py"

CANONICAL_PROVIDER = "github"
CANONICAL_REPOSITORY_ID = "37489525"
CANONICAL_PULL_REQUEST_NUMBER = "4414"
CANONICAL_HEAD_REVISION = "690a63b9218f72662cd3a67c6c200b758c88ce12"
CANONICAL_BASE_REVISION = "4c9cde74ab40027b5761ab9e002af116a4a20df3"
CANONICAL_MERGE_REVISION = "10cdae8e38ec448b7133cf163dca587ad806d262"
# The retained head-ref lexeme, recorded beside the head SHA in one provider
# head object whose repository field is an observed null.
CANONICAL_HEAD_REF_NAME = "starred_with_side_effect"

SYNTHETIC_REF_NAME = "another-supplied-name"

FORBIDDEN_DELETION_IDENTIFIERS = (
    "GitRefNamespace",
    "GitRefObservation",
    "authority",
    "availability",
    "branch",
    "confidence",
    "default_branch",
    "deleted_at",
    "evidence",
    "former_target",
    "namespace",
    "observed_at",
    "observed_null",
    "occurred_at",
    "rename",
    "repository",
    "timestamp",
    "unavailable",
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


def _commit(full_digest: str = CANONICAL_HEAD_REVISION) -> GitCommitIdentity:
    return GitCommitIdentity(
        kind=GitObjectKind.COMMIT,
        algorithm=GitHashAlgorithm.SHA1,
        full_digest=full_digest,
    )


def _binding(
    role: RevisionRole = RevisionRole.HEAD,
    full_digest: str = CANONICAL_HEAD_REVISION,
    *,
    number: str = CANONICAL_PULL_REQUEST_NUMBER,
) -> PullRequestRevisionRoleBinding:
    return PullRequestRevisionRoleBinding(
        pull_request=_pull_request(number),
        role_assignment=RevisionRoleAssignment(
            role=role, revision=_commit(full_digest)
        ),
    )


def _deletion(
    *,
    head: PullRequestRevisionRoleBinding | None = None,
    head_ref_name: GitRefName | None = None,
) -> PullRequestHeadRefDeletion:
    return PullRequestHeadRefDeletion(
        head=_binding() if head is None else head,
        head_ref_name=(
            GitRefName(CANONICAL_HEAD_REF_NAME)
            if head_ref_name is None
            else head_ref_name
        ),
    )


def _payload() -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(_deletion().model_dump_json()))


# --- canonical witness -----------------------------------------------------


def test_the_canonical_head_ref_deletion_is_supplied() -> None:
    deletion = _deletion()

    assert deletion.head == _binding()
    assert deletion.head.role_assignment.role is RevisionRole.HEAD
    assert deletion.head.role_assignment.revision.full_digest == (
        CANONICAL_HEAD_REVISION
    )
    assert deletion.head_ref_name == GitRefName(CANONICAL_HEAD_REF_NAME)


def test_the_deleted_ref_name_and_its_former_target_stay_together() -> None:
    deletion = _deletion()

    # The revision the ref named is reachable through the published binding, so
    # no separate former-target field is needed.
    assert deletion.head.role_assignment.revision == _commit()
    assert deletion.head.pull_request == _pull_request()
    assert "former_target" not in PullRequestHeadRefDeletion.model_fields


def test_repeating_one_deletion_yields_equal_independent_values() -> None:
    first = _deletion()
    second = _deletion()

    assert first == second
    assert first is not second


def test_the_two_supplied_values_are_preserved_unchanged() -> None:
    head = _binding()
    name = GitRefName(CANONICAL_HEAD_REF_NAME)

    deletion = PullRequestHeadRefDeletion(head=head, head_ref_name=name)

    assert deletion.head == head
    assert deletion.head_ref_name == name


# --- head role restriction -------------------------------------------------


def test_a_base_binding_cannot_carry_a_head_ref_deletion() -> None:
    with pytest.raises(ValidationError, match="head must carry the head revision role"):
        _deletion(head=_binding(RevisionRole.BASE, CANONICAL_BASE_REVISION))


@pytest.mark.parametrize(
    "role",
    tuple(role for role in RevisionRole if role is not RevisionRole.HEAD),
)
def test_only_a_head_binding_is_accepted(role: RevisionRole) -> None:
    # base is rejected by this relation; merge and merge_first_parent are
    # already refused by the published S01 binding itself.
    with pytest.raises(ValidationError):
        _deletion(head=_binding(role, CANONICAL_MERGE_REVISION))


def test_a_base_role_is_rejected_in_json_input() -> None:
    payload = _payload()
    head = cast(dict[str, Any], payload["head"])
    assignment = cast(dict[str, Any], head["role_assignment"])
    assignment["role"] = "base"

    with pytest.raises(ValidationError, match="head must carry the head revision role"):
        PullRequestHeadRefDeletion.model_validate_json(json.dumps(payload))


def test_the_deletion_does_not_restate_the_pull_request_or_revision() -> None:
    fields = set(PullRequestHeadRefDeletion.model_fields)

    for absent in ("pull_request", "revision", "head_revision", "former_target"):
        assert absent not in fields
    assert fields == {"head", "head_ref_name"}


# --- the ref is named, not identified --------------------------------------


def test_the_deletion_carries_no_repository_for_the_ref() -> None:
    fields = set(PullRequestHeadRefDeletion.model_fields)

    for absent in (
        "repository",
        "repository_identity",
        "head_repository",
        "fork",
        "fork_repository",
    ):
        assert absent not in fields


def test_the_deletion_carries_no_namespace() -> None:
    fields = set(PullRequestHeadRefDeletion.model_fields)

    for absent in ("namespace", "ref_namespace", "qualified_name", "full_ref"):
        assert absent not in fields
    for annotation in (
        field.annotation for field in PullRequestHeadRefDeletion.model_fields.values()
    ):
        assert annotation is not GitRefNamespace
        assert annotation is not GitRefObservation


def test_the_published_ref_name_contributes_only_lexeme_validation() -> None:
    # GitRefName is namespace-relative by contract and refuses a refs/ prefix,
    # so using it states no namespace rather than asserting one.
    assert tuple(GitRefName.model_fields) == ("root",)
    assert GitRefName(CANONICAL_HEAD_REF_NAME).root == CANONICAL_HEAD_REF_NAME

    with pytest.raises(ValidationError):
        GitRefName(f"refs/heads/{CANONICAL_HEAD_REF_NAME}")


def test_the_pull_request_repository_is_not_the_refs_repository() -> None:
    deletion = _deletion()

    # The binding's pull request has a repository; the deleted ref does not.
    assert deletion.head.pull_request.repository_identity == _repository()
    assert not hasattr(deletion, "repository_identity")
    assert not hasattr(deletion.head_ref_name, "repository_identity")


def test_the_generic_ref_observation_is_not_reused() -> None:
    source = HISTORY_SOURCE.read_text(encoding="utf-8")

    assert "GitRefObservation" not in source
    assert "GitRefNamespace" not in source
    assert "SourceIdentityLifecycleState" not in source


# --- named, distinct, and not a history ------------------------------------


def test_two_ref_names_under_one_head_are_two_supplied_facts() -> None:
    first = _deletion()
    second = _deletion(head_ref_name=GitRefName(SYNTHETIC_REF_NAME))

    assert first.head == second.head
    assert first != second
    # Neither is "the" ref history of that head; each is one supplied fact.
    assert not hasattr(first, "history")
    assert not hasattr(first, "sequence")


def test_one_ref_name_under_two_heads_are_two_supplied_facts() -> None:
    first = _deletion()
    second = _deletion(head=_binding(number="1"))

    assert first.head_ref_name == second.head_ref_name
    assert first != second


def test_a_namespace_relative_name_with_a_slash_is_accepted() -> None:
    deletion = _deletion(head_ref_name=GitRefName("user/topic"))

    assert deletion.head_ref_name.root == "user/topic"


def test_the_deletion_carries_no_ref_history_or_rename_surface() -> None:
    for absent in (
        "history",
        "events",
        "sequence",
        "renamed_from",
        "renamed_to",
        "previous_name",
        "recreated",
    ):
        assert absent not in PullRequestHeadRefDeletion.model_fields


# --- historical occurrence, not present state ------------------------------


def test_the_deletion_carries_no_lifecycle_state() -> None:
    for absent in (
        "state",
        "lifecycle_state",
        "ref_state",
        "deleted",
        "is_deleted",
        "present",
    ):
        assert absent not in PullRequestHeadRefDeletion.model_fields


@pytest.mark.parametrize(
    "rejected",
    ("RefLifecycleState", "HeadRefState", "RefState", "DeletionState"),
)
def test_no_ref_state_vocabulary_is_published(rejected: str) -> None:
    source = HISTORY_SOURCE.read_text(encoding="utf-8")

    assert not hasattr(history_module, rejected)
    assert rejected not in history_module.__all__
    assert rejected not in source


def test_an_absent_deletion_is_not_a_claim_that_a_ref_exists() -> None:
    deletion = _deletion()

    for absent in ("exists", "still_present", "restored", "tombstone"):
        assert not hasattr(deletion, absent)
    assert absent not in PullRequestHeadRefDeletion.model_fields


def test_the_deletion_carries_no_representation_availability() -> None:
    for absent in (
        "availability",
        "representation_availability",
        "unavailable",
        "retrievable",
        "observed_null",
    ):
        assert absent not in PullRequestHeadRefDeletion.model_fields


# --- no time, no cause -----------------------------------------------------


def test_the_deletion_carries_no_timestamp() -> None:
    for absent in (
        "deleted_at",
        "occurred_at",
        "observed_at",
        "timestamp",
        "event_time",
    ):
        assert absent not in PullRequestHeadRefDeletion.model_fields


def test_the_deletion_claims_no_cause_or_merge_relationship() -> None:
    deletion = _deletion()

    for absent in ("caused_by", "merge", "merged", "reason", "actor", "deleted_by"):
        assert not hasattr(deletion, absent)
        assert absent not in PullRequestHeadRefDeletion.model_fields


def test_the_deletion_claims_no_branch_or_default_branch_meaning() -> None:
    for absent in ("branch", "default_branch", "is_default", "base_ref"):
        assert absent not in PullRequestHeadRefDeletion.model_fields


# --- semantic JSON ---------------------------------------------------------


def test_deletion_semantic_json_round_trip_preserves_the_exact_value() -> None:
    deletion = _deletion()

    restored = PullRequestHeadRefDeletion.model_validate_json(
        deletion.model_dump_json()
    )

    assert restored == deletion
    assert restored.model_dump_json() == deletion.model_dump_json()


def test_deletion_json_payload_carries_exactly_the_two_semantic_keys() -> None:
    payload = _payload()

    assert set(payload) == {"head", "head_ref_name"}
    assert "schema_version" not in payload
    assert payload["head_ref_name"] == CANONICAL_HEAD_REF_NAME


def test_embedded_children_keep_their_published_json_shape() -> None:
    deletion = _deletion()
    payload = _payload()

    assert payload["head"] == json.loads(deletion.head.model_dump_json())
    assert payload["head_ref_name"] == json.loads(
        deletion.head_ref_name.model_dump_json()
    )


def test_deletion_json_reconstruction_accepts_a_semantic_mapping() -> None:
    assert (
        PullRequestHeadRefDeletion.model_validate_json(json.dumps(_payload()))
        == _deletion()
    )


# --- model posture ---------------------------------------------------------


def test_deletion_is_frozen() -> None:
    deletion = _deletion()

    for field, value in (
        ("head", _binding(number="1")),
        ("head_ref_name", GitRefName(SYNTHETIC_REF_NAME)),
    ):
        with pytest.raises(ValidationError):
            setattr(deletion, field, value)

    assert deletion == _deletion()


def test_deletion_rejects_attribute_deletion() -> None:
    deletion = _deletion()

    with pytest.raises(ValidationError):
        del deletion.head_ref_name

    assert deletion == _deletion()


def test_constructed_deletion_is_revalidated() -> None:
    assert PullRequestHeadRefDeletion.model_validate(_deletion()) == _deletion()


def test_deletion_revalidates_a_tampered_head_binding() -> None:
    tampered = PullRequestRevisionRoleBinding.model_construct(
        pull_request=_pull_request(),
        role_assignment=RevisionRoleAssignment(
            role=RevisionRole.BASE, revision=_commit(CANONICAL_BASE_REVISION)
        ),
    )

    with pytest.raises(ValidationError, match="head must carry the head revision role"):
        _deletion(head=tampered)


def test_deletion_revalidates_a_tampered_ref_name() -> None:
    tampered = GitRefName.model_construct(root="refs/heads/invalid")

    with pytest.raises(ValidationError):
        _deletion(head_ref_name=tampered)


def test_deletion_preserves_published_subclass_acceptance() -> None:
    class _SubclassedBinding(PullRequestRevisionRoleBinding):
        pass

    class _SubclassedRefName(GitRefName):
        pass

    deletion = PullRequestHeadRefDeletion(
        head=_SubclassedBinding(
            pull_request=_pull_request(),
            role_assignment=RevisionRoleAssignment(
                role=RevisionRole.HEAD, revision=_commit()
            ),
        ),
        head_ref_name=_SubclassedRefName(CANONICAL_HEAD_REF_NAME),
    )

    assert deletion == _deletion()
    assert type(deletion.head) is PullRequestRevisionRoleBinding
    assert type(deletion.head_ref_name) is GitRefName


# --- required fields and closed extras -------------------------------------


@pytest.mark.parametrize("missing", ("head", "head_ref_name"))
def test_deletion_required_fields_cannot_be_omitted(missing: str) -> None:
    payload = _payload()
    del payload[missing]

    with pytest.raises(ValidationError) as error:
        PullRequestHeadRefDeletion.model_validate_json(json.dumps(payload))

    assert error.value.errors()[0]["type"] == "missing"
    assert error.value.errors()[0]["loc"] == (missing,)


@pytest.mark.parametrize(
    "extra",
    (
        "availability",
        "deleted",
        "deleted_at",
        "former_target",
        "namespace",
        "observed_at",
        "observed_null",
        "repository",
        "repository_identity",
        "schema_version",
        "state",
        "unavailable",
    ),
)
def test_deletion_extra_fields_fail_closed(extra: str) -> None:
    payload = _payload()
    payload[extra] = "unexpected"

    with pytest.raises(ValidationError) as error:
        PullRequestHeadRefDeletion.model_validate_json(json.dumps(payload))

    assert error.value.errors()[0]["type"] == "extra_forbidden"


def test_deletion_has_no_field_beyond_the_two_semantic_positions() -> None:
    assert tuple(PullRequestHeadRefDeletion.model_fields) == (
        "head",
        "head_ref_name",
    )


# --- strict Python input ---------------------------------------------------


@pytest.mark.parametrize(
    "value",
    (None, CANONICAL_HEAD_REVISION, {"role": "head"}, _commit(), _pull_request()),
)
def test_deletion_rejects_untyped_python_heads(value: object) -> None:
    with pytest.raises(ValidationError, match="in Python input"):
        PullRequestHeadRefDeletion(
            head=value,  # type: ignore[arg-type]
            head_ref_name=GitRefName(CANONICAL_HEAD_REF_NAME),
        )


@pytest.mark.parametrize(
    "value",
    (None, CANONICAL_HEAD_REF_NAME, {"root": CANONICAL_HEAD_REF_NAME}, _commit()),
)
def test_deletion_rejects_untyped_python_ref_names(value: object) -> None:
    with pytest.raises(ValidationError, match="in Python input"):
        PullRequestHeadRefDeletion(
            head=_binding(),
            head_ref_name=value,  # type: ignore[arg-type]
        )


def test_deletion_python_construction_rejects_a_dumped_mapping() -> None:
    with pytest.raises(ValidationError, match="in Python input"):
        PullRequestHeadRefDeletion.model_validate(_payload())


def test_deletion_rejects_swapped_members() -> None:
    with pytest.raises(ValidationError, match="in Python input"):
        PullRequestHeadRefDeletion(
            head=GitRefName(CANONICAL_HEAD_REF_NAME),  # type: ignore[arg-type]
            head_ref_name=_binding(),  # type: ignore[arg-type]
        )


class _AttributeBackedBinding:
    def __init__(self, binding: PullRequestRevisionRoleBinding) -> None:
        self.pull_request = binding.pull_request
        self.role_assignment = binding.role_assignment


class _AttributeBackedRefName:
    def __init__(self, name: GitRefName) -> None:
        self.root = name.root


class _ForeignBinding(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    pull_request: object
    role_assignment: object


class _ForeignRefName(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    root: object


def _foreign_binding() -> _ForeignBinding:
    binding = _binding()
    return _ForeignBinding(
        pull_request=binding.pull_request,
        role_assignment=binding.role_assignment,
    )


def _foreign_ref_name() -> _ForeignRefName:
    return _ForeignRefName(root=CANONICAL_HEAD_REF_NAME)


def test_deletion_rejects_attribute_backed_children_under_from_attributes() -> None:
    with pytest.raises(ValidationError, match="in Python input"):
        PullRequestHeadRefDeletion.model_validate(
            {
                "head": _AttributeBackedBinding(_binding()),
                "head_ref_name": GitRefName(CANONICAL_HEAD_REF_NAME),
            },
            from_attributes=True,
        )
    with pytest.raises(ValidationError, match="in Python input"):
        PullRequestHeadRefDeletion.model_validate(
            {
                "head": _binding(),
                "head_ref_name": _AttributeBackedRefName(
                    GitRefName(CANONICAL_HEAD_REF_NAME)
                ),
            },
            from_attributes=True,
        )


def test_deletion_rejects_foreign_models_in_plain_python_input() -> None:
    with pytest.raises(
        ValidationError, match="head must be a PullRequestRevisionRoleBinding"
    ):
        PullRequestHeadRefDeletion(
            head=_foreign_binding(),  # type: ignore[arg-type]
            head_ref_name=GitRefName(CANONICAL_HEAD_REF_NAME),
        )
    with pytest.raises(ValidationError, match="head_ref_name must be a GitRefName"):
        PullRequestHeadRefDeletion(
            head=_binding(),
            head_ref_name=_foreign_ref_name(),  # type: ignore[arg-type]
        )


def test_both_child_positions_reject_foreign_models_under_from_attributes() -> None:
    for supplied, expected in (
        (
            {
                "head": _foreign_binding(),
                "head_ref_name": GitRefName(CANONICAL_HEAD_REF_NAME),
            },
            "head must be",
        ),
        (
            {"head": _binding(), "head_ref_name": _foreign_ref_name()},
            "head_ref_name must be",
        ),
    ):
        with pytest.raises(ValidationError, match=expected):
            PullRequestHeadRefDeletion.model_validate(supplied, from_attributes=True)


# --- malformed child JSON --------------------------------------------------


@pytest.mark.parametrize(
    "name",
    (
        "",
        "refs/heads/topic",
        "@",
        "/leading",
        "trailing/",
        "double//slash",
        "two..dots",
        "with space",
        "at@{brace",
        "x" * 256,
        None,
        1,
        [],
        {"root": "topic"},
    ),
)
def test_deletion_rejects_malformed_ref_name_json(name: object) -> None:
    payload = _payload()
    payload["head_ref_name"] = name

    with pytest.raises(ValidationError):
        PullRequestHeadRefDeletion.model_validate_json(json.dumps(payload))


@pytest.mark.parametrize(
    "head",
    (
        {},
        {"pull_request": {"kind": "pull_request"}},
        {
            "pull_request": {
                "repository_identity": {
                    "provider": CANONICAL_PROVIDER,
                    "provider_repository_id": CANONICAL_REPOSITORY_ID,
                },
                "kind": "issue",
                "repository_scoped_number": "4412",
            },
            "role_assignment": {
                "role": "head",
                "revision": {
                    "kind": "commit",
                    "algorithm": "sha1",
                    "full_digest": CANONICAL_HEAD_REVISION,
                },
            },
        },
        {
            "pull_request": {
                "repository_identity": {
                    "provider": CANONICAL_PROVIDER,
                    "provider_repository_id": CANONICAL_REPOSITORY_ID,
                },
                "kind": "pull_request",
                "repository_scoped_number": CANONICAL_PULL_REQUEST_NUMBER,
            },
            "role_assignment": {
                "role": "head",
                "revision": {
                    "kind": "tree",
                    "algorithm": "sha1",
                    "full_digest": CANONICAL_HEAD_REVISION,
                },
            },
        },
        CANONICAL_HEAD_REVISION,
        None,
        [],
    ),
)
def test_deletion_rejects_malformed_head_binding_json(head: object) -> None:
    payload = _payload()
    payload["head"] = head

    with pytest.raises(ValidationError):
        PullRequestHeadRefDeletion.model_validate_json(json.dumps(payload))


def test_deletion_rejects_a_json_payload_that_is_not_an_object() -> None:
    for payload in ("[]", '"deleted"', "1", "null"):
        with pytest.raises(ValidationError):
            PullRequestHeadRefDeletion.model_validate_json(payload)


# --- module surface --------------------------------------------------------


def test_deletion_model_surface_is_exact() -> None:
    assert history_module.__all__[-1] == "PullRequestHeadRefDeletion"
    assert tuple(PullRequestHeadRefDeletion.model_fields) == (
        "head",
        "head_ref_name",
    )
    assert {
        name: field.annotation
        for name, field in PullRequestHeadRefDeletion.model_fields.items()
    } == {
        "head": PullRequestRevisionRoleBinding,
        "head_ref_name": GitRefName,
    }
    for field in PullRequestHeadRefDeletion.model_fields.values():
        assert field.metadata == []
        assert field.discriminator is None
        assert field.is_required()
    assert PullRequestHeadRefDeletion.model_config == {
        "frozen": True,
        "extra": "forbid",
        "strict": True,
        "revalidate_instances": "always",
        "validate_default": True,
    }
    assert PullRequestHeadRefDeletion.__module__ == "faultatlas.domain.history"


def test_the_deletion_declares_the_expected_validators() -> None:
    tree = ast.parse(HISTORY_SOURCE.read_text(encoding="utf-8"))
    deletion_class = next(
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == "PullRequestHeadRefDeletion"
    )

    assert [type(node) for node in deletion_class.body] == [
        ast.Expr,
        ast.Assign,
        ast.AnnAssign,
        ast.AnnAssign,
        ast.FunctionDef,
        ast.FunctionDef,
        ast.FunctionDef,
    ]
    assert [
        node.name for node in deletion_class.body if isinstance(node, ast.FunctionDef)
    ] == [
        "_require_typed_python_deleted_head",
        "_require_typed_python_head_ref_name",
        "_require_head_revision_role",
    ]
    assert [
        (node.target.id, ast.unparse(node.annotation))
        for node in deletion_class.body
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name)
    ] == [
        ("head", "PullRequestRevisionRoleBinding"),
        ("head_ref_name", "GitRefName"),
    ]


def test_no_forbidden_identifier_appears_in_the_deletion_surface() -> None:
    tree = ast.parse(HISTORY_SOURCE.read_text(encoding="utf-8"))
    deletion_class = next(
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == "PullRequestHeadRefDeletion"
    )
    surface = ast.unparse(deletion_class)

    for identifier in FORBIDDEN_DELETION_IDENTIFIERS:
        assert identifier not in surface


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


def test_the_deletion_adds_no_evidence_or_confidence_surface() -> None:
    source = HISTORY_SOURCE.read_text(encoding="utf-8")

    assert "faultatlas.domain.evidence" not in source
    assert "DurableEvidenceRecordReference" not in source
    assert "faultatlas.domain.snapshot" not in source


@pytest.mark.parametrize(
    "literal",
    (
        CANONICAL_REPOSITORY_ID,
        CANONICAL_PULL_REQUEST_NUMBER,
        CANONICAL_HEAD_REVISION,
        CANONICAL_HEAD_REF_NAME,
    ),
)
def test_no_canonical_case_literal_is_embedded_in_production(literal: str) -> None:
    assert literal not in HISTORY_SOURCE.read_text(encoding="utf-8")


def test_the_roadmap_records_the_s05_transition() -> None:
    roadmap = " ".join(
        (REPOSITORY_ROOT / "docs/roadmap.md").read_text(encoding="utf-8").split()
    )
    mapping = roadmap.split("## Current-code mapping", 1)
    assert len(mapping) == 2, "roadmap must retain a current-code mapping section"
    current = mapping[1]

    assert "PullRequestHeadRefDeletion" in current
    assert "`S1.P05.S05` — Pull Request Head-Ref Deletion (complete)" in roadmap
    assert "`S1.P05.S06` is next and not started" in roadmap
    # The superseded provisional title and status must not survive.
    assert "Mutable Head-Ref Observation and Deletion" not in roadmap
    assert "`S1.P05.S05` is next and not started" not in roadmap


def test_canonical_head_ref_literals_remain_locked() -> None:
    assert CANONICAL_HEAD_REF_NAME == "starred_with_side_effect"
    assert CANONICAL_HEAD_REVISION == "690a63b9218f72662cd3a67c6c200b758c88ce12"
    assert CANONICAL_PULL_REQUEST_NUMBER == "4414"
    assert CANONICAL_REPOSITORY_ID == "37489525"
