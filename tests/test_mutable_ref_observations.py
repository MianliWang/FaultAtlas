from __future__ import annotations

import ast
import json
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pytest
from pydantic import BaseModel, ValidationError

import faultatlas
import faultatlas.domain as domain_package
import faultatlas.domain.revision as revision_module
from faultatlas.domain.identity import (
    AuthorityRole,
    ProviderAuthority,
    ProviderKey,
    ProviderRepositoryId,
    RepositoryIdentity,
    SourceIdentityLifecycleState,
)
from faultatlas.domain.revision import (
    GitBlobIdentity,
    GitCommitIdentity,
    GitCommitParentTopology,
    GitHashAlgorithm,
    GitObjectKind,
    GitRefName,
    GitRefNamespace,
    GitRefObservation,
    GitTreeIdentity,
    RevisionRole,
    RevisionRoleAssignment,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
REVISION_SOURCE = REPOSITORY_ROOT / "src/faultatlas/domain/revision.py"

# Directly observed: the retained PR-head representation co-locates this SHA
# and ref lexeme, and later evidence reports head_ref_deleted. The namespace,
# original repository identity, and FaultAtlas observation time are not locked.
CANONICAL_FORMER_TARGET = "690a63b9218f72662cd3a67c6c200b758c88ce12"
CANONICAL_REF_LEXEME = "starred_with_side_effect"
CANONICAL_PROVIDER_EVENT_AT = "2018-11-18T00:17:28Z"

# Reviewed synthetic vectors: these values fill fields the canonical case does
# not establish. They make no claim about the deleted pytest PR-head subject.
SYNTHETIC_NAMESPACE = "heads"
SYNTHETIC_NAME = "feature/fix-evaluation-order"
SYNTHETIC_OBSERVED_AT = datetime(2026, 8, 1, 12, 0, tzinfo=UTC)
SYNTHETIC_SHA1 = "1" * 40
SYNTHETIC_SHA256 = "2" * 64

EXPECTED_EXPORTS = [
    "GitHashAlgorithm",
    "GitObjectKind",
    "GitCommitIdentity",
    "GitTreeIdentity",
    "GitBlobIdentity",
    "GitObjectIdentity",
    "GitRevisionIdentity",
    "RevisionRole",
    "RevisionRoleAssignment",
    "GitCommitParentTopology",
    "GitRefNamespace",
    "GitRefName",
    "GitRefObservation",
    "GitRepositoryPath",
    "RevisionQualifiedPath",
]

EXPECTED_PRODUCTION_FILES = {
    "src/faultatlas/__init__.py",
    "src/faultatlas/__main__.py",
    "src/faultatlas/cli.py",
    "src/faultatlas/domain/__init__.py",
    "src/faultatlas/domain/compatibility.py",
    "src/faultatlas/domain/identity.py",
    "src/faultatlas/domain/revision.py",
    "src/faultatlas/domain/source.py",
}


def _provider(value: str = "github") -> ProviderKey:
    return ProviderKey.model_validate(value)


def _repository(
    provider_repository_id: str = "37489525",
    *,
    provider: ProviderKey | None = None,
) -> RepositoryIdentity:
    return RepositoryIdentity(
        provider=provider or _provider(),
        provider_repository_id=ProviderRepositoryId.model_validate(
            provider_repository_id
        ),
    )


def _authority(
    *,
    provider: ProviderKey | None = None,
    role: AuthorityRole = AuthorityRole.RETRIEVAL,
    host: str = "api.github.com",
) -> ProviderAuthority:
    return ProviderAuthority(
        provider=provider or _provider(),
        role=role,
        host=host,
    )


def _commit(
    digest: str = SYNTHETIC_SHA1,
    algorithm: GitHashAlgorithm = GitHashAlgorithm.SHA1,
) -> GitCommitIdentity:
    return GitCommitIdentity(
        kind=GitObjectKind.COMMIT,
        algorithm=algorithm,
        full_digest=digest,
    )


def _tree(digest: str = "a" * 40) -> GitTreeIdentity:
    return GitTreeIdentity(
        kind=GitObjectKind.TREE,
        algorithm=GitHashAlgorithm.SHA1,
        full_digest=digest,
    )


def _blob(digest: str = "b" * 40) -> GitBlobIdentity:
    return GitBlobIdentity(
        kind=GitObjectKind.BLOB,
        algorithm=GitHashAlgorithm.SHA1,
        full_digest=digest,
    )


def _observation(**overrides: object) -> GitRefObservation:
    payload: dict[str, object] = {
        "repository_identity": _repository(),
        "namespace": GitRefNamespace.model_validate(SYNTHETIC_NAMESPACE),
        "name": GitRefName.model_validate(SYNTHETIC_NAME),
        "state": SourceIdentityLifecycleState.OBSERVED_PRESENT,
        "authority": _authority(),
        "observed_at": SYNTHETIC_OBSERVED_AT,
        "observed_target": _commit(),
    }
    payload.update(overrides)
    return GitRefObservation.model_validate(payload)


def _validate_revision_public_surface(source: str) -> None:
    tree = ast.parse(source)
    export_values: object | None = None
    public_symbols: set[str] = set()
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == "__all__"
            for target in node.targets
        ):
            export_values = ast.literal_eval(node.value)
        elif isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            if not node.name.startswith("_"):
                public_symbols.add(node.name)
        elif isinstance(node, ast.TypeAlias) and not node.name.id.startswith("_"):
            public_symbols.add(node.name.id)
    assert export_values == EXPECTED_EXPORTS
    assert public_symbols == set(EXPECTED_EXPORTS)


def _validate_production_inventory(paths: set[str]) -> None:
    assert paths == EXPECTED_PRODUCTION_FILES


@pytest.mark.parametrize(
    "value",
    (
        "heads",
        "tags",
        "remotes",
        "a",
        "a0",
        "a-b",
        "a_b",
        "a" * 64,
    ),
)
def test_namespace_accepts_exact_conservative_ascii_grammar(value: str) -> None:
    namespace = GitRefNamespace.model_validate(value)

    assert namespace.root == value


@pytest.mark.parametrize(
    "value",
    (
        "",
        "a" * 65,
        "HEAD",
        "Heads",
        "refs",
        "1heads",
        "-heads",
        "_heads",
        "refs/heads",
        "heads.main",
        "heads main",
        "heads\tmain",
        "heads\nmain",
        "https://github.com",
        "héads",
    ),
)
def test_namespace_rejects_out_of_contract_lexemes(value: str) -> None:
    with pytest.raises(ValidationError):
        GitRefNamespace.model_validate(value)


@pytest.mark.parametrize(
    "value",
    (None, True, 1, b"heads", ["heads"], {"root": "heads"}),
)
def test_namespace_rejects_non_string_coercion(value: object) -> None:
    with pytest.raises(ValidationError):
        GitRefNamespace.model_validate(value)


def test_namespace_is_frozen_and_never_normalized() -> None:
    namespace = GitRefNamespace.model_validate("heads")

    with pytest.raises(ValidationError):
        namespace.root = "tags"
    with pytest.raises(ValidationError):
        GitRefNamespace.model_validate(" heads ")
    with pytest.raises(ValidationError):
        GitRefNamespace.model_validate("HEADS")


@pytest.mark.parametrize(
    "value",
    (
        "main",
        "feature/fix-evaluation-order",
        "Feature/Fix-Evaluation_Order",
        "release/2026/08/01",
        "a" * 255,
    ),
)
def test_ref_name_accepts_exact_conservative_ascii_subset(value: str) -> None:
    name = GitRefName.model_validate(value)

    assert name.root == value


@pytest.mark.parametrize(
    "value",
    (
        "",
        "a" * 256,
        "/main",
        "main/",
        "feature//main",
        "feature///main",
        ".hidden",
        "feature/.hidden",
        ".",
        "..",
        "feature/.",
        "feature/..",
        "main.lock",
        "feature/main.lock",
        "main.",
        "feature..main",
        "feature@{main",
        "feature\\main",
        "feature main",
        "feature\tmain",
        "feature\nmain",
        "feature~main",
        "feature^main",
        "feature:main",
        "feature?main",
        "feature*main",
        "feature[main",
        "@",
        "refs/heads/main",
        "https://github.com/owner/repo",
        "C:\\refs\\heads\\main",
        "fèature/main",
    ),
)
def test_ref_name_rejects_out_of_contract_lexemes(value: str) -> None:
    with pytest.raises(ValidationError):
        GitRefName.model_validate(value)


@pytest.mark.parametrize(
    "value",
    (None, True, 1, b"main", ["main"], {"root": "main"}),
)
def test_ref_name_rejects_non_string_coercion(value: object) -> None:
    with pytest.raises(ValidationError):
        GitRefName.model_validate(value)


def test_ref_name_is_frozen_case_sensitive_and_never_normalized() -> None:
    supplied = "Feature/Fix-Evaluation_Order"
    name = GitRefName.model_validate(supplied)

    assert name.root == supplied
    with pytest.raises(ValidationError):
        name.root = "feature/fix-evaluation_order"
    with pytest.raises(ValidationError):
        GitRefName.model_validate(f" {supplied}")


def test_valid_present_observation_requires_explicit_commit_target() -> None:
    target = _commit()
    observation = _observation(observed_target=target)

    assert observation.schema_version == 1
    assert observation.repository_identity == _repository()
    assert observation.namespace.root == SYNTHETIC_NAMESPACE
    assert observation.name.root == SYNTHETIC_NAME
    assert observation.state is SourceIdentityLifecycleState.OBSERVED_PRESENT
    assert observation.authority == _authority()
    assert observation.observed_at == SYNTHETIC_OBSERVED_AT
    assert observation.observed_at.tzinfo is UTC
    assert type(observation.observed_target) is GitCommitIdentity
    assert observation.observed_target == target


def test_deleted_observation_may_retain_known_former_target() -> None:
    target = _commit(CANONICAL_FORMER_TARGET)
    before = target.model_dump_json()
    observation = _observation(
        state=SourceIdentityLifecycleState.DELETED,
        observed_target=target,
    )

    assert observation.state is SourceIdentityLifecycleState.DELETED
    assert observation.observed_target == target
    assert observation.observed_target is not None
    assert observation.observed_target.model_dump_json() == before
    assert target.model_dump_json() == before


def test_deleted_observation_may_omit_former_target_explicitly() -> None:
    observation = _observation(
        state=SourceIdentityLifecycleState.DELETED,
        observed_target=None,
    )

    assert observation.state is SourceIdentityLifecycleState.DELETED
    assert observation.observed_target is None


@pytest.mark.parametrize(
    "state",
    (
        SourceIdentityLifecycleState.UNAVAILABLE,
        SourceIdentityLifecycleState.INACCESSIBLE,
        SourceIdentityLifecycleState.UNKNOWN,
    ),
)
def test_targetless_lifecycle_states_are_valid_only_with_explicit_none(
    state: SourceIdentityLifecycleState,
) -> None:
    observation = _observation(state=state, observed_target=None)

    assert observation.state is state
    assert observation.observed_target is None


def test_synthetic_sha256_commit_target_is_supported_lexically() -> None:
    target = _commit(SYNTHETIC_SHA256, GitHashAlgorithm.SHA256)
    observation = _observation(observed_target=target)

    assert observation.observed_target == target
    assert observation.observed_target is not None
    assert observation.observed_target.algorithm is GitHashAlgorithm.SHA256


def test_authority_provider_must_match_stable_repository_provider() -> None:
    gitlab = _provider("gitlab")
    with pytest.raises(ValidationError) as error:
        _observation(
            authority=_authority(provider=gitlab, host="gitlab.com"),
        )

    assert error.value.errors()[0]["loc"] == ()


def test_authority_provider_is_not_inferred_from_other_fields() -> None:
    github_repository = _repository()
    gitlab = _provider("gitlab")
    with pytest.raises(ValidationError):
        _observation(
            repository_identity=github_repository,
            namespace=GitRefNamespace.model_validate("remotes"),
            name=GitRefName.model_validate("gitlab/main"),
            authority=_authority(provider=gitlab, host="gitlab.com"),
        )


def test_effective_zero_offset_is_normalized_to_datetime_utc() -> None:
    named_zero = timezone(timedelta(0), name="synthetic-zero")
    supplied = datetime(2026, 8, 1, 12, 0, tzinfo=named_zero)
    observation = _observation(observed_at=supplied)

    assert observation.observed_at == supplied
    assert observation.observed_at.tzinfo is UTC
    assert observation.model_dump(mode="json")["observed_at"].endswith("Z")


def test_naive_observation_time_is_rejected() -> None:
    with pytest.raises(ValidationError) as error:
        _observation(observed_at=datetime(2026, 8, 1, 12, 0))

    assert error.value.errors()[0]["loc"] == ("observed_at",)


@pytest.mark.parametrize(
    "offset",
    (timedelta(hours=1), timedelta(hours=-5), timedelta(minutes=30)),
)
def test_nonzero_offset_observation_time_is_rejected(offset: timedelta) -> None:
    with pytest.raises(ValidationError) as error:
        _observation(observed_at=datetime(2026, 8, 1, 12, 0, tzinfo=timezone(offset)))

    assert error.value.errors()[0]["loc"] == ("observed_at",)


@pytest.mark.parametrize("schema_version", (0, 2, "1", True, 1.0))
def test_observation_schema_version_is_exact(schema_version: object) -> None:
    with pytest.raises(ValidationError):
        _observation(schema_version=schema_version)


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("repository_identity", {"provider": "github"}),
        ("namespace", "heads"),
        ("name", "main"),
        ("state", "observed_present"),
        ("authority", {"provider": "github"}),
        ("observed_at", "2026-08-01T12:00:00Z"),
        ("observed_target", {"kind": "commit"}),
    ),
)
def test_python_observation_input_requires_typed_values(
    field: str,
    value: object,
) -> None:
    with pytest.raises(ValidationError):
        _observation(**{field: value})


def test_semantic_json_round_trip_restores_exact_types() -> None:
    original = _observation()
    payload = original.model_dump_json()
    restored = GitRefObservation.model_validate_json(payload)

    assert restored == original
    assert type(restored.repository_identity) is RepositoryIdentity
    assert type(restored.namespace) is GitRefNamespace
    assert type(restored.name) is GitRefName
    assert restored.state is SourceIdentityLifecycleState.OBSERVED_PRESENT
    assert type(restored.authority) is ProviderAuthority
    assert restored.observed_at.tzinfo is UTC
    assert type(restored.observed_target) is GitCommitIdentity
    assert json.loads(payload) == original.model_dump(mode="json")
    assert payload == original.model_dump_json()


@pytest.mark.parametrize(
    "field",
    (
        "role",
        "topology",
        "repository_alias",
        "alias",
        "transition",
        "previous_observation",
        "next_observation",
        "supersedes",
        "valid_from",
        "valid_until",
        "version_counter",
        "latest",
        "current",
        "path",
        "locator",
        "parents",
        "reachability",
    ),
)
def test_observation_rejects_every_deferred_or_cross_record_field(field: str) -> None:
    with pytest.raises(ValidationError) as error:
        _observation(**{field: "forbidden"})

    assert error.value.errors()[0]["type"] == "extra_forbidden"


def test_observation_is_frozen_and_rejects_dynamic_attributes() -> None:
    observation = _observation()

    with pytest.raises(ValidationError) as mutation_error:
        observation.state = SourceIdentityLifecycleState.DELETED
    with pytest.raises(ValidationError) as dynamic_error:
        setattr(observation, "latest", True)

    assert mutation_error.value.errors()[0]["type"] == "frozen_instance"
    assert dynamic_error.value.errors()[0]["type"] == "frozen_instance"


def test_observed_present_rejects_absent_target() -> None:
    with pytest.raises(ValidationError) as error:
        _observation(observed_target=None)

    assert error.value.errors()[0]["loc"] == ()


@pytest.mark.parametrize(
    "state",
    (
        SourceIdentityLifecycleState.UNAVAILABLE,
        SourceIdentityLifecycleState.INACCESSIBLE,
        SourceIdentityLifecycleState.UNKNOWN,
    ),
)
def test_targetless_states_reject_fabricated_target(
    state: SourceIdentityLifecycleState,
) -> None:
    with pytest.raises(ValidationError) as error:
        _observation(state=state, observed_target=_commit())

    assert error.value.errors()[0]["loc"] == ()


def test_state_and_target_fields_are_both_explicitly_required() -> None:
    original = _observation()
    payload = {
        field: getattr(original, field) for field in GitRefObservation.model_fields
    }
    del payload["state"]
    with pytest.raises(ValidationError) as state_error:
        GitRefObservation.model_validate(payload)
    original = _observation(
        state=SourceIdentityLifecycleState.UNKNOWN,
        observed_target=None,
    )
    payload = {
        field: getattr(original, field) for field in GitRefObservation.model_fields
    }
    del payload["observed_target"]
    with pytest.raises(ValidationError) as target_error:
        GitRefObservation.model_validate(payload)

    assert state_error.value.errors()[0]["loc"] == ("state",)
    assert target_error.value.errors()[0]["loc"] == ("observed_target",)


def test_observation_namespace_is_explicitly_required() -> None:
    original = _observation()
    payload = {
        field: getattr(original, field) for field in GitRefObservation.model_fields
    }
    del payload["namespace"]

    with pytest.raises(ValidationError) as error:
        GitRefObservation.model_validate(payload)

    assert error.value.errors()[0]["loc"] == ("namespace",)


@pytest.mark.parametrize("target", (_tree(), _blob()))
def test_tree_and_blob_are_rejected_as_python_observed_targets(
    target: BaseModel,
) -> None:
    with pytest.raises(ValidationError) as error:
        _observation(observed_target=target)

    assert error.value.errors()[0]["loc"] == ("observed_target",)


@pytest.mark.parametrize("target", (_tree(), _blob()))
def test_tree_and_blob_are_rejected_as_json_observed_targets(
    target: BaseModel,
) -> None:
    payload: dict[str, Any] = json.loads(_observation().model_dump_json())
    payload["observed_target"] = target.model_dump(mode="json")

    with pytest.raises(ValidationError):
        GitRefObservation.model_validate_json(json.dumps(payload))


def test_constructed_invalid_nested_namespace_is_revalidated() -> None:
    invalid = GitRefNamespace.model_construct(root="HEAD")

    with pytest.raises(ValidationError) as error:
        _observation(namespace=invalid)

    assert error.value.errors()[0]["loc"] == ("namespace",)


def test_constructed_invalid_nested_name_is_revalidated() -> None:
    invalid = GitRefName.model_construct(root="refs/heads/main")

    with pytest.raises(ValidationError) as error:
        _observation(name=invalid)

    assert error.value.errors()[0]["loc"] == ("name",)


def test_constructed_invalid_repository_is_revalidated() -> None:
    invalid = RepositoryIdentity.model_construct(
        provider=ProviderKey.model_construct(root="GitHub"),
        provider_repository_id=ProviderRepositoryId.model_validate("37489525"),
    )

    with pytest.raises(ValidationError) as error:
        _observation(repository_identity=invalid)

    assert error.value.errors()[0]["loc"][0] == "repository_identity"


def test_constructed_invalid_authority_is_revalidated() -> None:
    invalid = ProviderAuthority.model_construct(
        provider=_provider(),
        role=AuthorityRole.RETRIEVAL,
        host="API.GITHUB.COM",
    )

    with pytest.raises(ValidationError) as error:
        _observation(authority=invalid)

    assert error.value.errors()[0]["loc"][0] == "authority"


def test_constructed_invalid_target_is_revalidated() -> None:
    invalid = GitCommitIdentity.model_construct(
        kind=GitObjectKind.COMMIT,
        algorithm=GitHashAlgorithm.SHA1,
        full_digest="a" * 39,
    )

    with pytest.raises(ValidationError) as error:
        _observation(observed_target=invalid)

    assert error.value.errors()[0]["loc"][0] == "observed_target"


def test_constructed_invalid_outer_observation_is_revalidated() -> None:
    original = _observation()
    values = {
        field: getattr(original, field) for field in GitRefObservation.model_fields
    }
    values["state"] = SourceIdentityLifecycleState.UNKNOWN
    invalid = GitRefObservation.model_construct(**values)

    with pytest.raises(ValidationError):
        GitRefObservation.model_validate(invalid)


def test_present_and_later_deleted_observations_coexist_without_mutation() -> None:
    target = _commit(CANONICAL_FORMER_TARGET)
    present = _observation(observed_target=target)
    present_before = present.model_dump_json()
    deleted = _observation(
        state=SourceIdentityLifecycleState.DELETED,
        observed_at=datetime(2026, 8, 2, 12, 0, tzinfo=UTC),
        observed_target=target,
    )

    assert present != deleted
    assert present.state is SourceIdentityLifecycleState.OBSERVED_PRESENT
    assert deleted.state is SourceIdentityLifecycleState.DELETED
    assert present.observed_target == deleted.observed_target == target
    assert present.model_dump_json() == present_before
    assert target == _commit(CANONICAL_FORMER_TARGET)


def test_observation_equality_includes_time_state_and_target() -> None:
    original = _observation()
    later = _observation(observed_at=datetime(2026, 8, 2, 12, 0, tzinfo=UTC))
    deleted = _observation(
        state=SourceIdentityLifecycleState.DELETED,
        observed_target=original.observed_target,
    )
    targetless = _observation(
        state=SourceIdentityLifecycleState.DELETED,
        observed_target=None,
    )

    serialized = {
        item.model_dump_json() for item in (original, later, deleted, targetless)
    }
    assert len(serialized) == 4


def test_same_ref_text_under_different_stable_repositories_is_distinct() -> None:
    first = _observation(repository_identity=_repository("37489525"))
    second = _observation(repository_identity=_repository("99999999"))

    assert first.namespace == second.namespace
    assert first.name == second.name
    assert first.repository_identity != second.repository_identity
    assert first != second


def test_authority_is_observation_context_not_stable_repository_identity() -> None:
    retrieval = _observation()
    navigation = _observation(
        authority=_authority(
            role=AuthorityRole.NAVIGATION,
            host="github.com",
        )
    )

    assert retrieval.repository_identity == navigation.repository_identity
    assert retrieval.authority != navigation.authority
    assert retrieval != navigation


def test_ref_subject_fields_are_exact_without_separate_identity_model() -> None:
    assert tuple(GitRefObservation.model_fields) == (
        "schema_version",
        "repository_identity",
        "namespace",
        "name",
        "state",
        "authority",
        "observed_at",
        "observed_target",
    )
    assert not hasattr(revision_module, "GitRefIdentity")
    assert not {
        "repository_alias",
        "alias",
        "role",
        "topology",
        "previous_observation",
        "next_observation",
        "transition",
        "supersedes",
        "valid_from",
        "valid_until",
        "version_counter",
        "current",
        "latest",
        "path",
        "locator",
        "parents",
        "ancestry",
        "reachability",
    } & set(GitRefObservation.model_fields)


def test_ref_observation_is_separate_from_role_and_topology_models() -> None:
    assert tuple(RevisionRoleAssignment.model_fields) == (
        "schema_version",
        "role",
        "revision",
    )
    assert tuple(GitCommitParentTopology.model_fields) == (
        "schema_version",
        "commit",
        "ordered_parents",
    )
    assert "ref" not in {item.value for item in RevisionRole}
    assert not set(GitRefObservation.model_fields) & {
        "role",
        "revision",
        "commit",
        "ordered_parents",
    }


def test_models_have_strict_frozen_revalidation_configuration() -> None:
    for model in (GitRefNamespace, GitRefName, GitRefObservation):
        assert model.model_config.get("frozen") is True
        assert model.model_config.get("strict") is True
        assert model.model_config.get("revalidate_instances") == "always"
        assert model.model_config.get("validate_default") is True
    assert GitRefObservation.model_config.get("extra") == "forbid"


def test_lifecycle_vocabulary_is_reused_without_revision_reexport() -> None:
    assert tuple(item.value for item in SourceIdentityLifecycleState) == (
        "observed_present",
        "deleted",
        "unavailable",
        "inaccessible",
        "unknown",
    )
    assert "SourceIdentityLifecycleState" not in revision_module.__all__
    assert "GitRefLifecycleState" not in vars(revision_module)


def test_canonical_evidence_use_is_bounded_and_synthetic_fields_are_explicit() -> None:
    observation = _observation(
        state=SourceIdentityLifecycleState.DELETED,
        observed_target=_commit(CANONICAL_FORMER_TARGET),
    )

    assert CANONICAL_REF_LEXEME == "starred_with_side_effect"
    assert CANONICAL_PROVIDER_EVENT_AT == "2018-11-18T00:17:28Z"
    assert observation.name.root == SYNTHETIC_NAME != CANONICAL_REF_LEXEME
    assert observation.namespace.root == SYNTHETIC_NAMESPACE
    assert observation.observed_at == SYNTHETIC_OBSERVED_AT
    assert observation.observed_target is not None
    assert observation.observed_target.full_digest == CANONICAL_FORMER_TARGET


def test_exports_are_exact_and_internal_only() -> None:
    assert revision_module.__all__ == EXPECTED_EXPORTS
    assert len(revision_module.__all__) == len(set(revision_module.__all__)) == 15
    assert faultatlas.__all__ == ["__version__"]
    assert not any(hasattr(faultatlas, name) for name in EXPECTED_EXPORTS)
    assert not any(hasattr(domain_package, name) for name in EXPECTED_EXPORTS)
    _validate_revision_public_surface(REVISION_SOURCE.read_text(encoding="utf-8"))


@pytest.mark.parametrize("mutation", ("missing", "unexpected"))
def test_revision_export_surface_mutations_are_rejected(
    mutation: str,
) -> None:
    source = REVISION_SOURCE.read_text(encoding="utf-8")
    if mutation == "missing":
        mutated = source.replace('    "GitRefObservation",\n', "", 1)
    else:
        assert mutation == "unexpected"
        mutated = source.replace(
            '    "GitRefObservation",\n',
            '    "GitRefObservation",\n    "UnexpectedRevision",\n',
            1,
        )
    with pytest.raises(AssertionError):
        _validate_revision_public_surface(mutated)


@pytest.mark.parametrize(
    "symbol",
    (
        "GitSymbolicRef",
        "GitTagIdentity",
        "GitRefHistory",
        "GitRefTransition",
    ),
)
def test_deferred_ref_and_history_model_mutations_are_rejected(symbol: str) -> None:
    source = REVISION_SOURCE.read_text(encoding="utf-8")
    mutated = source + f"\n\nclass {symbol}:\n    pass\n"

    with pytest.raises(AssertionError):
        _validate_revision_public_surface(mutated)


def test_production_inventory_remains_exactly_eight_modules() -> None:
    production_files = {
        path.relative_to(REPOSITORY_ROOT).as_posix()
        for path in (REPOSITORY_ROOT / "src").rglob("*.py")
    }

    _validate_production_inventory(production_files)
    assert len(production_files) == 8
    with pytest.raises(AssertionError):
        _validate_production_inventory(
            production_files | {"src/faultatlas/domain/ref_history.py"}
        )


def test_package_root_export_mutation_is_rejected() -> None:
    source = (REPOSITORY_ROOT / "src/faultatlas/__init__.py").read_text(
        encoding="utf-8"
    )
    mutated = source + (
        "\nfrom faultatlas.domain.revision import GitRefObservation\n"
        '__all__.append("GitRefObservation")\n'
    )
    tree = ast.parse(mutated)
    exports = [
        ast.literal_eval(node.value)
        for node in tree.body
        if isinstance(node, ast.Assign)
        and any(
            isinstance(target, ast.Name) and target.id == "__all__"
            for target in node.targets
        )
    ]
    appended = any(
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "append"
        for node in ast.walk(tree)
    )

    with pytest.raises(AssertionError):
        assert exports == [["__version__"]] and not appended


def test_no_symbolic_ref_tag_object_history_graph_locator_or_io_surface() -> None:
    source = REVISION_SOURCE.read_text(encoding="utf-8")
    _validate_revision_public_surface(source)
    tree = ast.parse(source)
    public_definitions = {
        node.name
        for node in tree.body
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
        and not node.name.startswith("_")
    }
    assert not public_definitions & {
        "GitSymbolicRef",
        "GitTagIdentity",
        "GitRefTransition",
        "GitRefHistory",
        "RepositoryMembership",
        "RepositoryReachability",
        "RepositoryHistoryGraph",
        "LineLocator",
        "ByteLocator",
        "HunkLocator",
    }

    forbidden_modules = {"git", "os", "pathlib", "socket", "subprocess"}
    forbidden_calls = {
        "open",
        "read",
        "read_bytes",
        "read_text",
        "run",
        "Popen",
        "check_call",
        "check_output",
    }
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            assert (
                not {alias.name.split(".")[0] for alias in node.names}
                & forbidden_modules
            )
        elif isinstance(node, ast.ImportFrom):
            assert node.module is not None
            assert node.module.split(".")[0] not in forbidden_modules
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                assert node.func.id not in forbidden_calls
            elif isinstance(node.func, ast.Attribute):
                assert node.func.attr not in forbidden_calls
