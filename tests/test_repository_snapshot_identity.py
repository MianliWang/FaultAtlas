from __future__ import annotations

import ast
import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

import faultatlas.domain.snapshot as snapshot_module
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
    GitHashAlgorithm,
    GitObjectKind,
    GitRefName,
    GitRefNamespace,
    GitRefObservation,
    GitRepositoryPath,
    GitTreeIdentity,
    LineEnding,
    OneBasedInclusiveLineSpan,
    RevisionLineLocator,
    RevisionQualifiedPath,
    TextEncoding,
)
from faultatlas.domain.snapshot import (
    RepositorySnapshotIdentity,
    RepositorySnapshotRootTreeBinding,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT_SOURCE = REPOSITORY_ROOT / "src/faultatlas/domain/snapshot.py"


def _provider(value: str = "github") -> ProviderKey:
    return ProviderKey.model_validate(value)


def _repository(
    repository_id: str = "37489525",
    *,
    provider: ProviderKey | None = None,
) -> RepositoryIdentity:
    return RepositoryIdentity(
        provider=provider or _provider(),
        provider_repository_id=ProviderRepositoryId.model_validate(repository_id),
    )


def _commit(
    digest: str = "1" * 40,
    algorithm: GitHashAlgorithm = GitHashAlgorithm.SHA1,
) -> GitCommitIdentity:
    return GitCommitIdentity(
        kind=GitObjectKind.COMMIT,
        algorithm=algorithm,
        full_digest=digest,
    )


def _tree(
    digest: str = "2" * 40,
    algorithm: GitHashAlgorithm = GitHashAlgorithm.SHA1,
) -> GitTreeIdentity:
    return GitTreeIdentity(
        kind=GitObjectKind.TREE,
        algorithm=algorithm,
        full_digest=digest,
    )


def _blob() -> GitBlobIdentity:
    return GitBlobIdentity(
        kind=GitObjectKind.BLOB,
        algorithm=GitHashAlgorithm.SHA1,
        full_digest="3" * 40,
    )


def _ref_observation() -> GitRefObservation:
    provider = _provider()
    return GitRefObservation(
        repository_identity=_repository(provider=provider),
        namespace=GitRefNamespace.model_validate("heads"),
        name=GitRefName.model_validate("main"),
        state=SourceIdentityLifecycleState.OBSERVED_PRESENT,
        authority=ProviderAuthority(
            provider=provider,
            role=AuthorityRole.RETRIEVAL,
            host="api.github.com",
        ),
        observed_at=datetime(2026, 8, 13, tzinfo=UTC),
        observed_target=_commit(),
    )


def _qualified_path() -> RevisionQualifiedPath:
    return RevisionQualifiedPath(
        repository_identity=_repository(),
        revision=_commit(),
        path=GitRepositoryPath.model_validate("src/faultatlas/domain/snapshot.py"),
    )


def _locator() -> RevisionLineLocator:
    return RevisionLineLocator(
        locator_kind="revision_line",
        parent=_qualified_path(),
        span=OneBasedInclusiveLineSpan(start_line=1, end_line=1),
        text_encoding=TextEncoding.UTF8,
        line_ending=LineEnding.LF,
    )


def _snapshot(
    commit_digest: str = "1" * 40,
    algorithm: GitHashAlgorithm = GitHashAlgorithm.SHA1,
    repository_id: str = "37489525",
) -> RepositorySnapshotIdentity:
    return RepositorySnapshotIdentity(
        repository=_repository(repository_id),
        revision=_commit(commit_digest, algorithm),
    )


@pytest.mark.parametrize(
    ("algorithm", "digest"),
    (
        (GitHashAlgorithm.SHA1, "1" * 40),
        (GitHashAlgorithm.SHA256, "2" * 64),
    ),
)
def test_snapshot_identity_accepts_supported_immutable_commit_algorithms(
    algorithm: GitHashAlgorithm,
    digest: str,
) -> None:
    repository = _repository()
    revision = _commit(digest, algorithm)

    identity = RepositorySnapshotIdentity(
        repository=repository,
        revision=revision,
    )

    assert identity.repository == repository
    assert identity.revision == revision


def test_same_repository_and_commit_reconstruct_equal_semantic_identity() -> None:
    first = RepositorySnapshotIdentity(
        repository=_repository(),
        revision=_commit(),
    )
    second = RepositorySnapshotIdentity(
        repository=_repository(),
        revision=_commit(),
    )

    assert first == second
    assert first.model_dump(mode="json") == second.model_dump(mode="json")


def test_same_commit_under_distinct_repositories_remains_distinct() -> None:
    revision = _commit()

    first = RepositorySnapshotIdentity(
        repository=_repository("37489525"),
        revision=revision,
    )
    second = RepositorySnapshotIdentity(
        repository=_repository("99999999"),
        revision=revision,
    )

    assert first != second


def test_same_repository_under_distinct_commits_remains_distinct() -> None:
    repository = _repository()

    first = RepositorySnapshotIdentity(
        repository=repository,
        revision=_commit("1" * 40),
    )
    second = RepositorySnapshotIdentity(
        repository=repository,
        revision=_commit("2" * 40),
    )

    assert first != second


def test_snapshot_identity_is_frozen() -> None:
    identity = RepositorySnapshotIdentity(
        repository=_repository(),
        revision=_commit(),
    )

    with pytest.raises(ValidationError):
        identity.revision = _commit("2" * 40)


def test_semantic_json_round_trip_preserves_exact_value() -> None:
    original = RepositorySnapshotIdentity(
        repository=_repository(),
        revision=_commit("2" * 64, GitHashAlgorithm.SHA256),
    )

    encoded = original.model_dump_json()
    restored = RepositorySnapshotIdentity.model_validate_json(encoded)

    assert restored == original
    assert json.loads(encoded) == original.model_dump(mode="json")
    assert set(json.loads(encoded)) == {"repository", "revision"}


@pytest.mark.parametrize("missing", ("repository", "revision"))
def test_required_fields_cannot_be_omitted(missing: str) -> None:
    payload: dict[str, object] = {
        "repository": _repository(),
        "revision": _commit(),
    }
    del payload[missing]

    with pytest.raises(ValidationError):
        RepositorySnapshotIdentity.model_validate(payload)


def test_extra_fields_fail_closed() -> None:
    with pytest.raises(ValidationError):
        RepositorySnapshotIdentity.model_validate(
            {
                "repository": _repository(),
                "revision": _commit(),
                "root_tree": _tree(),
            }
        )


@pytest.mark.parametrize(
    "repository",
    (
        "pytest-dev/pytest",
        "37489525",
        37489525,
        ProviderKey.model_validate("github"),
    ),
)
def test_repository_rejects_alias_scalars_and_provider_key(repository: object) -> None:
    with pytest.raises(ValidationError):
        RepositorySnapshotIdentity.model_validate(
            {"repository": repository, "revision": _commit()}
        )


@pytest.mark.parametrize(
    "revision",
    (
        _ref_observation(),
        _tree(),
        _blob(),
        _qualified_path(),
    ),
)
def test_revision_rejects_ref_tree_blob_and_qualified_path(revision: object) -> None:
    with pytest.raises(ValidationError):
        RepositorySnapshotIdentity.model_validate(
            {"repository": _repository(), "revision": revision}
        )


@pytest.mark.parametrize(
    ("field", "mapping"),
    (
        ("repository", _repository().model_dump(mode="python")),
        ("revision", _commit().model_dump(mode="python")),
    ),
)
def test_python_construction_rejects_coercive_nested_mappings(
    field: str,
    mapping: dict[str, object],
) -> None:
    payload: dict[str, object] = {
        "repository": _repository(),
        "revision": _commit(),
    }
    payload[field] = mapping

    with pytest.raises(ValidationError):
        RepositorySnapshotIdentity.model_validate(payload)


def test_nested_repository_identity_is_revalidated() -> None:
    invalid = RepositoryIdentity.model_construct(
        schema_version=1,
        provider=ProviderKey.model_construct(root="GitHub"),
        provider_repository_id=ProviderRepositoryId.model_validate("37489525"),
    )

    with pytest.raises(ValidationError):
        RepositorySnapshotIdentity(repository=invalid, revision=_commit())


def test_nested_commit_identity_is_revalidated() -> None:
    invalid = GitCommitIdentity.model_construct(
        schema_version=1,
        kind=GitObjectKind.COMMIT,
        algorithm=GitHashAlgorithm.SHA1,
        full_digest="0" * 40,
    )

    with pytest.raises(ValidationError):
        RepositorySnapshotIdentity(repository=_repository(), revision=invalid)


def test_canonical_pytest_4412_root_tree_binding_is_representable() -> None:
    snapshot = _snapshot(
        "690a63b9218f72662cd3a67c6c200b758c88ce12",
    )
    root_tree = _tree("9e5593159e909083009ac9ad72d5d59feb863c44")

    binding = RepositorySnapshotRootTreeBinding(
        snapshot=snapshot,
        root_tree=root_tree,
    )

    assert binding.snapshot == snapshot
    assert binding.root_tree == root_tree


def test_root_tree_binding_accepts_matching_sha256_identities() -> None:
    snapshot = _snapshot("1" * 64, GitHashAlgorithm.SHA256)
    root_tree = _tree("2" * 64, GitHashAlgorithm.SHA256)

    binding = RepositorySnapshotRootTreeBinding(
        snapshot=snapshot,
        root_tree=root_tree,
    )

    assert binding.snapshot.revision.algorithm is GitHashAlgorithm.SHA256
    assert binding.root_tree.algorithm is GitHashAlgorithm.SHA256


def test_same_snapshot_and_tree_reconstruct_equal_binding() -> None:
    first = RepositorySnapshotRootTreeBinding(
        snapshot=_snapshot(),
        root_tree=_tree(),
    )
    second = RepositorySnapshotRootTreeBinding(
        snapshot=_snapshot(),
        root_tree=_tree(),
    )

    assert first == second
    assert first.model_dump(mode="json") == second.model_dump(mode="json")


def test_same_tree_under_distinct_repositories_produces_distinct_bindings() -> None:
    root_tree = _tree()

    first = RepositorySnapshotRootTreeBinding(
        snapshot=_snapshot(repository_id="37489525"),
        root_tree=root_tree,
    )
    second = RepositorySnapshotRootTreeBinding(
        snapshot=_snapshot(repository_id="99999999"),
        root_tree=root_tree,
    )

    assert first != second
    assert first.root_tree == second.root_tree


def test_same_repository_and_tree_under_distinct_commits_remain_distinct() -> None:
    root_tree = _tree()

    first = RepositorySnapshotRootTreeBinding(
        snapshot=_snapshot("1" * 40),
        root_tree=root_tree,
    )
    second = RepositorySnapshotRootTreeBinding(
        snapshot=_snapshot("3" * 40),
        root_tree=root_tree,
    )

    assert first != second
    assert first.root_tree == second.root_tree


def test_root_tree_binding_is_frozen() -> None:
    binding = RepositorySnapshotRootTreeBinding(
        snapshot=_snapshot(),
        root_tree=_tree(),
    )

    with pytest.raises(ValidationError):
        binding.root_tree = _tree("3" * 40)


def test_root_tree_binding_semantic_json_round_trip_preserves_exact_value() -> None:
    original = RepositorySnapshotRootTreeBinding(
        snapshot=_snapshot("1" * 64, GitHashAlgorithm.SHA256),
        root_tree=_tree("2" * 64, GitHashAlgorithm.SHA256),
    )

    encoded = original.model_dump_json()
    restored = RepositorySnapshotRootTreeBinding.model_validate_json(encoded)

    assert restored == original
    assert type(restored.snapshot) is RepositorySnapshotIdentity
    assert type(restored.root_tree) is GitTreeIdentity
    assert json.loads(encoded) == original.model_dump(mode="json")
    assert set(json.loads(encoded)) == {"snapshot", "root_tree"}


@pytest.mark.parametrize("missing", ("snapshot", "root_tree"))
def test_root_tree_binding_required_fields_cannot_be_omitted(missing: str) -> None:
    payload: dict[str, object] = {
        "snapshot": _snapshot(),
        "root_tree": _tree(),
    }
    del payload[missing]

    with pytest.raises(ValidationError):
        RepositorySnapshotRootTreeBinding.model_validate(payload)


def test_root_tree_binding_extra_fields_fail_closed() -> None:
    with pytest.raises(ValidationError):
        RepositorySnapshotRootTreeBinding.model_validate(
            {
                "snapshot": _snapshot(),
                "root_tree": _tree(),
                "verified": True,
            }
        )


@pytest.mark.parametrize(
    "snapshot",
    (
        _repository(),
        _commit(),
        _tree(),
        "github/37489525@main",
    ),
)
def test_root_tree_binding_rejects_non_snapshot_subjects(snapshot: object) -> None:
    with pytest.raises(ValidationError):
        RepositorySnapshotRootTreeBinding.model_validate(
            {"snapshot": snapshot, "root_tree": _tree()}
        )


@pytest.mark.parametrize(
    "root_tree",
    (
        _commit(),
        _blob(),
        _ref_observation(),
        _qualified_path(),
        _locator(),
        "9e5593159e909083009ac9ad72d5d59feb863c44",
    ),
)
def test_root_tree_binding_rejects_non_tree_values(root_tree: object) -> None:
    with pytest.raises(ValidationError):
        RepositorySnapshotRootTreeBinding.model_validate(
            {"snapshot": _snapshot(), "root_tree": root_tree}
        )


@pytest.mark.parametrize(
    ("field", "mapping"),
    (
        ("snapshot", _snapshot().model_dump(mode="python")),
        ("root_tree", _tree().model_dump(mode="python")),
    ),
)
def test_root_tree_binding_python_construction_rejects_nested_mappings(
    field: str,
    mapping: dict[str, object],
) -> None:
    payload: dict[str, object] = {
        "snapshot": _snapshot(),
        "root_tree": _tree(),
    }
    payload[field] = mapping

    with pytest.raises(ValidationError):
        RepositorySnapshotRootTreeBinding.model_validate(payload)


def test_root_tree_binding_revalidates_nested_snapshot() -> None:
    invalid_revision = GitCommitIdentity.model_construct(
        schema_version=1,
        kind=GitObjectKind.COMMIT,
        algorithm=GitHashAlgorithm.SHA1,
        full_digest="0" * 40,
    )
    invalid_snapshot = RepositorySnapshotIdentity.model_construct(
        repository=_repository(),
        revision=invalid_revision,
    )

    with pytest.raises(ValidationError):
        RepositorySnapshotRootTreeBinding(
            snapshot=invalid_snapshot,
            root_tree=_tree(),
        )


def test_root_tree_binding_revalidates_nested_tree() -> None:
    invalid_tree = GitTreeIdentity.model_construct(
        schema_version=1,
        kind=GitObjectKind.TREE,
        algorithm=GitHashAlgorithm.SHA1,
        full_digest="0" * 40,
    )

    with pytest.raises(ValidationError):
        RepositorySnapshotRootTreeBinding(
            snapshot=_snapshot(),
            root_tree=invalid_tree,
        )


@pytest.mark.parametrize(
    ("snapshot", "root_tree"),
    (
        (
            _snapshot("1" * 40, GitHashAlgorithm.SHA1),
            _tree("2" * 64, GitHashAlgorithm.SHA256),
        ),
        (
            _snapshot("1" * 64, GitHashAlgorithm.SHA256),
            _tree("2" * 40, GitHashAlgorithm.SHA1),
        ),
    ),
)
def test_root_tree_binding_rejects_hash_algorithm_mismatch(
    snapshot: RepositorySnapshotIdentity,
    root_tree: GitTreeIdentity,
) -> None:
    with pytest.raises(ValidationError):
        RepositorySnapshotRootTreeBinding(
            snapshot=snapshot,
            root_tree=root_tree,
        )


def test_constructed_root_tree_binding_is_revalidated() -> None:
    invalid = RepositorySnapshotRootTreeBinding.model_construct(
        snapshot=_snapshot("1" * 40, GitHashAlgorithm.SHA1),
        root_tree=_tree("2" * 64, GitHashAlgorithm.SHA256),
    )

    with pytest.raises(ValidationError):
        RepositorySnapshotRootTreeBinding.model_validate(invalid)


def test_model_and_module_surfaces_are_exact_and_local() -> None:
    assert tuple(RepositorySnapshotIdentity.model_fields) == (
        "repository",
        "revision",
    )
    assert RepositorySnapshotIdentity.model_fields["repository"].annotation is (
        RepositoryIdentity
    )
    assert RepositorySnapshotIdentity.model_fields["revision"].annotation is (
        GitCommitIdentity
    )
    assert RepositorySnapshotIdentity.model_config == {
        "frozen": True,
        "extra": "forbid",
        "strict": True,
        "revalidate_instances": "always",
        "validate_default": True,
    }
    assert tuple(RepositorySnapshotRootTreeBinding.model_fields) == (
        "snapshot",
        "root_tree",
    )
    assert RepositorySnapshotRootTreeBinding.model_fields["snapshot"].annotation is (
        RepositorySnapshotIdentity
    )
    assert (
        RepositorySnapshotRootTreeBinding.model_fields["root_tree"].annotation
        is GitTreeIdentity
    )
    assert RepositorySnapshotRootTreeBinding.model_config == {
        "frozen": True,
        "extra": "forbid",
        "strict": True,
        "revalidate_instances": "always",
        "validate_default": True,
    }
    assert snapshot_module.__all__ == [
        "RepositorySnapshotIdentity",
        "RepositorySnapshotRootTreeBinding",
    ]
    assert RepositorySnapshotIdentity.__module__ == "faultatlas.domain.snapshot"
    assert RepositorySnapshotRootTreeBinding.__module__ == "faultatlas.domain.snapshot"


def test_snapshot_module_has_only_the_bounded_models_and_no_io_call_surface() -> None:
    tree = ast.parse(SNAPSHOT_SOURCE.read_text(encoding="utf-8"))
    assert [type(node) for node in tree.body] == [
        ast.Expr,
        ast.ImportFrom,
        ast.ImportFrom,
        ast.ImportFrom,
        ast.ImportFrom,
        ast.Assign,
        ast.ClassDef,
        ast.ClassDef,
    ]
    assert not [node for node in tree.body if isinstance(node, ast.Import)]
    imports = [
        (node.module, tuple(alias.name for alias in node.names))
        for node in tree.body
        if isinstance(node, ast.ImportFrom)
    ]
    assert imports == [
        ("typing", ("Self",)),
        (
            "pydantic",
            (
                "BaseModel",
                "ConfigDict",
                "ValidationInfo",
                "field_validator",
                "model_validator",
            ),
        ),
        ("faultatlas.domain.identity", ("RepositoryIdentity",)),
        (
            "faultatlas.domain.revision",
            ("GitCommitIdentity", "GitTreeIdentity"),
        ),
    ]
    classes = [node for node in tree.body if isinstance(node, ast.ClassDef)]
    assert [node.name for node in classes] == [
        "RepositorySnapshotIdentity",
        "RepositorySnapshotRootTreeBinding",
    ]
    assert [type(node) for node in classes[0].body] == [
        ast.Expr,
        ast.Assign,
        ast.AnnAssign,
        ast.AnnAssign,
        ast.FunctionDef,
        ast.FunctionDef,
    ]
    assert [type(node) for node in classes[1].body] == [
        ast.Expr,
        ast.Assign,
        ast.AnnAssign,
        ast.AnnAssign,
        ast.FunctionDef,
        ast.FunctionDef,
        ast.FunctionDef,
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
    ] == ["__all__"]
    assert [
        [
            target.id
            for node in class_node.body
            if isinstance(node, ast.Assign)
            for target in node.targets
            if isinstance(target, ast.Name)
        ]
        for class_node in classes
    ] == [["model_config"], ["model_config"]]
    assert [
        [
            node.target.id
            for node in class_node.body
            if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name)
        ]
        for class_node in classes
    ] == [["repository", "revision"], ["snapshot", "root_tree"]]
    assert [
        [
            node.name
            for node in class_node.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        ]
        for class_node in classes
    ] == [
        [
            "_require_typed_python_repository",
            "_require_typed_python_revision",
        ],
        [
            "_require_typed_python_snapshot",
            "_require_typed_python_root_tree",
            "_require_matching_hash_algorithms",
        ],
    ]
    algorithm_validator = classes[1].body[-1]
    assert isinstance(algorithm_validator, ast.FunctionDef)
    comparisons = [
        node for node in ast.walk(algorithm_validator) if isinstance(node, ast.Compare)
    ]
    assert len(comparisons) == 1
    comparison = comparisons[0]
    assert [type(operator) for operator in comparison.ops] == [ast.IsNot]
    assert [
        ast.unparse(comparison.left),
        *(ast.unparse(comparator) for comparator in comparison.comparators),
    ] == [
        "self.root_tree.algorithm",
        "self.snapshot.revision.algorithm",
    ]
    calls = {
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    assert calls == {
        "ConfigDict",
        "ValueError",
        "field_validator",
        "isinstance",
        "model_validator",
    }
    assert not [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    ]
    assert {
        node.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load)
    } == {
        "BaseModel",
        "ConfigDict",
        "GitCommitIdentity",
        "GitTreeIdentity",
        "RepositoryIdentity",
        "RepositorySnapshotIdentity",
        "Self",
        "ValidationInfo",
        "ValueError",
        "classmethod",
        "field_validator",
        "info",
        "isinstance",
        "model_validator",
        "object",
        "self",
        "value",
    }
    assert [
        (node.value.id, node.attr)
        for node in ast.walk(tree)
        if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name)
    ] == [
        ("info", "mode"),
        ("info", "mode"),
        ("info", "mode"),
        ("info", "mode"),
        ("self", "root_tree"),
        ("self", "snapshot"),
    ]
