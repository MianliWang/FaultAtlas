from __future__ import annotations

import ast
import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
from annotated_types import MaxLen
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
    RepositorySnapshotDeclaredPathScope,
    RepositorySnapshotDeclaredPathScopeCoverage,
    RepositorySnapshotIdentity,
    RepositorySnapshotPathBinding,
    RepositorySnapshotPathBindingCollection,
    RepositorySnapshotRootTreeBinding,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT_SOURCE = REPOSITORY_ROOT / "src/faultatlas/domain/snapshot.py"

CANONICAL_REVISION = "690a63b9218f72662cd3a67c6c200b758c88ce12"
CANONICAL_ROOT_TREE = "9e5593159e909083009ac9ad72d5d59feb863c44"
CANONICAL_BLOB_PATH_BINDINGS = (
    ("LICENSE", "629df45ac405532c107eb233217bc2ac1ad70c88"),
    (
        "src/_pytest/assertion/rewrite.py",
        "7b9aa5006544c160f584f1e8fc3f7771ef6e5e99",
    ),
    ("testing/test_assertrewrite.py", "a02433cd62ab19ebb54b42b50c299e59e48de00e"),
    ("changelog/4412.bugfix.rst", "7a28b610837873eeff2a16582de6d5a035820552"),
)
CANONICAL_TREE_PATH_BINDINGS = (
    ("src", "a09c07b934d1f5fb98e598a0ab53c1ef520e4679"),
    ("src/_pytest", "4d3b4e04cb82671a039aa972bcf34b87d5b956d4"),
    ("src/_pytest/assertion", "5b8e5295983b6f7c8b38f26e197341308550702d"),
    ("testing", "087f1168831906c523a252e46b4e318847a5ac74"),
    ("changelog", "c283046f429bfc377758ad8e14eeab6be43b55e1"),
)
SYNTHETIC_NFC_PATH = "tests/fixtures/éxample.txt"
SYNTHETIC_NFD_PATH = "tests/fixtures/e\u0301xample.txt"


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


def _blob(
    digest: str = "3" * 40,
    algorithm: GitHashAlgorithm = GitHashAlgorithm.SHA1,
) -> GitBlobIdentity:
    return GitBlobIdentity(
        kind=GitObjectKind.BLOB,
        algorithm=algorithm,
        full_digest=digest,
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


def _path(value: str = "LICENSE") -> GitRepositoryPath:
    return GitRepositoryPath.model_validate(value)


def _canonical_snapshot() -> RepositorySnapshotIdentity:
    return _snapshot(CANONICAL_REVISION)


def _binding(
    path: str = "LICENSE",
    git_object: GitBlobIdentity | GitTreeIdentity | None = None,
    snapshot: RepositorySnapshotIdentity | None = None,
) -> RepositorySnapshotPathBinding:
    return RepositorySnapshotPathBinding(
        snapshot=snapshot if snapshot is not None else _snapshot(),
        path=_path(path),
        git_object=git_object if git_object is not None else _blob(),
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


def test_canonical_license_blob_path_binding_is_representable() -> None:
    snapshot = _canonical_snapshot()
    blob = _blob("629df45ac405532c107eb233217bc2ac1ad70c88")

    binding = RepositorySnapshotPathBinding(
        snapshot=snapshot,
        path=_path("LICENSE"),
        git_object=blob,
    )

    assert binding.snapshot == snapshot
    assert binding.path.root == "LICENSE"
    assert binding.git_object == blob
    assert binding.git_object.kind is GitObjectKind.BLOB


@pytest.mark.parametrize(("path", "digest"), CANONICAL_BLOB_PATH_BINDINGS)
def test_canonical_blob_path_bindings_are_representable(
    path: str,
    digest: str,
) -> None:
    binding = RepositorySnapshotPathBinding(
        snapshot=_canonical_snapshot(),
        path=_path(path),
        git_object=_blob(digest),
    )

    assert binding.path.root == path
    assert binding.git_object.full_digest == digest
    assert type(binding.git_object) is GitBlobIdentity


@pytest.mark.parametrize(("path", "digest"), CANONICAL_TREE_PATH_BINDINGS)
def test_canonical_directory_tree_path_bindings_are_representable(
    path: str,
    digest: str,
) -> None:
    binding = RepositorySnapshotPathBinding(
        snapshot=_canonical_snapshot(),
        path=_path(path),
        git_object=_tree(digest),
    )

    assert binding.path.root == path
    assert binding.git_object.full_digest == digest
    assert type(binding.git_object) is GitTreeIdentity


def test_canonical_root_tree_is_not_expressed_as_a_path_binding() -> None:
    for root_lexeme in (".", "", "/"):
        with pytest.raises(ValidationError):
            RepositorySnapshotPathBinding.model_validate(
                {
                    "snapshot": _canonical_snapshot(),
                    "path": root_lexeme,
                    "git_object": _tree(CANONICAL_ROOT_TREE),
                }
            )

    root_binding = RepositorySnapshotRootTreeBinding(
        snapshot=_canonical_snapshot(),
        root_tree=_tree(CANONICAL_ROOT_TREE),
    )

    assert root_binding.root_tree.full_digest == CANONICAL_ROOT_TREE


@pytest.mark.parametrize(
    "git_object",
    (
        GitBlobIdentity(
            kind=GitObjectKind.BLOB,
            algorithm=GitHashAlgorithm.SHA256,
            full_digest="3" * 64,
        ),
        GitTreeIdentity(
            kind=GitObjectKind.TREE,
            algorithm=GitHashAlgorithm.SHA256,
            full_digest="4" * 64,
        ),
    ),
)
def test_path_binding_accepts_matching_sha256_objects(
    git_object: GitBlobIdentity | GitTreeIdentity,
) -> None:
    binding = RepositorySnapshotPathBinding(
        snapshot=_snapshot("1" * 64, GitHashAlgorithm.SHA256),
        path=_path("docs/example.md"),
        git_object=git_object,
    )

    assert binding.snapshot.revision.algorithm is GitHashAlgorithm.SHA256
    assert binding.git_object.algorithm is GitHashAlgorithm.SHA256


def test_same_inputs_reconstruct_equal_path_binding() -> None:
    first = _binding()
    second = _binding()

    assert first == second
    assert first.model_dump(mode="json") == second.model_dump(mode="json")


def test_path_binding_distinguishes_snapshot_path_and_object() -> None:
    baseline = _binding()

    assert baseline != _binding(snapshot=_snapshot(repository_id="99999999"))
    assert baseline != _binding(snapshot=_snapshot("2" * 40))
    assert baseline != _binding(path="LICENSE.md")
    assert baseline != _binding(git_object=_blob("4" * 40))


def test_same_object_binds_under_distinct_snapshots_and_remains_distinct() -> None:
    blob = _blob()

    first = _binding(snapshot=_snapshot(repository_id="37489525"), git_object=blob)
    second = _binding(snapshot=_snapshot(repository_id="99999999"), git_object=blob)

    assert first != second
    assert first.git_object == second.git_object
    assert first.path == second.path


def test_same_object_binds_to_distinct_paths_and_remains_distinct() -> None:
    blob = _blob()

    first = _binding(path="a/duplicate.txt", git_object=blob)
    second = _binding(path="b/duplicate.txt", git_object=blob)

    assert first != second
    assert first.git_object == second.git_object


def test_case_distinct_paths_remain_distinct_bindings() -> None:
    lower = _binding(path="license")
    upper = _binding(path="LICENSE")

    assert lower != upper
    assert lower.path.root == "license"
    assert upper.path.root == "LICENSE"


def test_nfc_and_nfd_path_spellings_remain_distinct_bindings() -> None:
    composed = _binding(path=SYNTHETIC_NFC_PATH)
    decomposed = _binding(path=SYNTHETIC_NFD_PATH)

    assert SYNTHETIC_NFC_PATH != SYNTHETIC_NFD_PATH
    assert composed != decomposed
    assert composed.path.root == SYNTHETIC_NFC_PATH
    assert decomposed.path.root == SYNTHETIC_NFD_PATH

    restored = RepositorySnapshotPathBinding.model_validate_json(
        decomposed.model_dump_json()
    )

    assert restored.path.root == SYNTHETIC_NFD_PATH


def test_path_binding_is_frozen() -> None:
    binding = _binding()

    with pytest.raises(ValidationError):
        binding.git_object = _blob("4" * 40)


def test_path_binding_semantic_json_round_trip_preserves_exact_value() -> None:
    original = RepositorySnapshotPathBinding(
        snapshot=_snapshot("1" * 64, GitHashAlgorithm.SHA256),
        path=_path("src/_pytest/assertion/rewrite.py"),
        git_object=_tree("2" * 64, GitHashAlgorithm.SHA256),
    )

    encoded = original.model_dump_json()
    restored = RepositorySnapshotPathBinding.model_validate_json(encoded)

    assert restored == original
    assert type(restored.snapshot) is RepositorySnapshotIdentity
    assert type(restored.path) is GitRepositoryPath
    assert type(restored.git_object) is GitTreeIdentity
    assert json.loads(encoded) == original.model_dump(mode="json")
    assert set(json.loads(encoded)) == {"snapshot", "path", "git_object"}


@pytest.mark.parametrize("missing", ("snapshot", "path", "git_object"))
def test_path_binding_required_fields_cannot_be_omitted(missing: str) -> None:
    payload: dict[str, object] = {
        "snapshot": _snapshot(),
        "path": _path(),
        "git_object": _blob(),
    }
    del payload[missing]

    with pytest.raises(ValidationError):
        RepositorySnapshotPathBinding.model_validate(payload)


@pytest.mark.parametrize(
    "field",
    (
        "mode",
        "file_mode",
        "entry_kind",
        "executable",
        "symlink_target",
        "gitlink",
        "exists",
        "member",
        "members",
        "entries",
        "children",
        "order",
        "ordinal",
        "complete",
        "completeness",
        "root_tree",
        "evidence",
        "verified",
    ),
)
def test_path_binding_rejects_mode_membership_and_evidence_fields(field: str) -> None:
    payload: dict[str, object] = {
        "snapshot": _snapshot(),
        "path": _path(),
        "git_object": _blob(),
        field: "100644",
    }

    with pytest.raises(ValidationError):
        RepositorySnapshotPathBinding.model_validate(payload)


@pytest.mark.parametrize(
    "snapshot",
    (
        _repository(),
        _commit(),
        _tree(),
        _blob(),
        _qualified_path(),
        "github/37489525@690a63b9",
    ),
)
def test_path_binding_rejects_non_snapshot_subjects(snapshot: object) -> None:
    with pytest.raises(ValidationError):
        RepositorySnapshotPathBinding.model_validate(
            {"snapshot": snapshot, "path": _path(), "git_object": _blob()}
        )


@pytest.mark.parametrize(
    "path",
    (
        "LICENSE",
        b"LICENSE",
        37489525,
        _qualified_path(),
    ),
)
def test_path_binding_rejects_untyped_python_path_values(path: object) -> None:
    with pytest.raises(ValidationError):
        RepositorySnapshotPathBinding(
            snapshot=_snapshot(),
            path=path,  # pyright: ignore[reportArgumentType]
            git_object=_blob(),
        )


@pytest.mark.parametrize(
    "path",
    ("", ".", "..", "/LICENSE", "LICENSE/", "a//b", "a\\b", "C:/a", "a/./b"),
)
def test_path_binding_inherits_exact_repository_path_rejections(path: str) -> None:
    with pytest.raises(ValidationError):
        RepositorySnapshotPathBinding.model_validate(
            {"snapshot": _snapshot(), "path": path, "git_object": _blob()}
        )


@pytest.mark.parametrize(
    "git_object",
    (
        _commit(),
        _ref_observation(),
        _qualified_path(),
        _locator(),
        "629df45ac405532c107eb233217bc2ac1ad70c88",
        37489525,
    ),
)
def test_path_binding_rejects_non_blob_or_tree_objects(git_object: object) -> None:
    with pytest.raises(ValidationError):
        RepositorySnapshotPathBinding.model_validate(
            {"snapshot": _snapshot(), "path": _path(), "git_object": git_object}
        )


def test_path_binding_rejects_commit_objects_in_both_input_modes() -> None:
    payload = {
        "snapshot": _snapshot().model_dump(mode="json"),
        "path": "LICENSE",
        "git_object": _commit().model_dump(mode="json"),
    }

    with pytest.raises(ValidationError) as json_error:
        RepositorySnapshotPathBinding.model_validate_json(json.dumps(payload))

    assert json_error.value.errors()[0]["type"] == "union_tag_invalid"
    assert json_error.value.errors()[0]["loc"] == ("git_object",)

    with pytest.raises(ValidationError) as python_error:
        RepositorySnapshotPathBinding(
            snapshot=_snapshot(),
            path=_path(),
            git_object=_commit(),  # pyright: ignore[reportArgumentType]
        )

    assert python_error.value.errors()[0]["type"] == "value_error"


def test_path_binding_extra_fields_fail_closed() -> None:
    with pytest.raises(ValidationError):
        RepositorySnapshotPathBinding.model_validate(
            {
                "snapshot": _snapshot(),
                "path": _path(),
                "git_object": _blob(),
                "root_tree": _tree(),
            }
        )


@pytest.mark.parametrize(
    ("field", "mapping"),
    (
        ("snapshot", _snapshot().model_dump(mode="python")),
        ("git_object", _blob().model_dump(mode="python")),
    ),
)
def test_path_binding_python_construction_rejects_nested_mappings(
    field: str,
    mapping: dict[str, object],
) -> None:
    payload: dict[str, object] = {
        "snapshot": _snapshot(),
        "path": _path(),
        "git_object": _blob(),
    }
    payload[field] = mapping

    with pytest.raises(ValidationError):
        RepositorySnapshotPathBinding.model_validate(payload)


def test_path_binding_revalidates_nested_snapshot() -> None:
    invalid_snapshot = RepositorySnapshotIdentity.model_construct(
        repository=_repository(),
        revision=GitCommitIdentity.model_construct(
            schema_version=1,
            kind=GitObjectKind.COMMIT,
            algorithm=GitHashAlgorithm.SHA1,
            full_digest="0" * 40,
        ),
    )

    with pytest.raises(ValidationError):
        RepositorySnapshotPathBinding(
            snapshot=invalid_snapshot,
            path=_path(),
            git_object=_blob(),
        )


@pytest.mark.parametrize(
    "git_object",
    (
        GitBlobIdentity.model_construct(
            schema_version=1,
            kind=GitObjectKind.BLOB,
            algorithm=GitHashAlgorithm.SHA1,
            full_digest="0" * 40,
        ),
        GitTreeIdentity.model_construct(
            schema_version=1,
            kind=GitObjectKind.TREE,
            algorithm=GitHashAlgorithm.SHA1,
            full_digest="0" * 40,
        ),
    ),
)
def test_path_binding_revalidates_nested_git_object(
    git_object: GitBlobIdentity | GitTreeIdentity,
) -> None:
    with pytest.raises(ValidationError):
        RepositorySnapshotPathBinding(
            snapshot=_snapshot(),
            path=_path(),
            git_object=git_object,
        )


def test_path_binding_revalidates_nested_path() -> None:
    invalid_path = GitRepositoryPath.model_construct(root="/LICENSE")

    with pytest.raises(ValidationError):
        RepositorySnapshotPathBinding(
            snapshot=_snapshot(),
            path=invalid_path,
            git_object=_blob(),
        )


@pytest.mark.parametrize(
    ("snapshot", "git_object"),
    (
        (
            _snapshot("1" * 40, GitHashAlgorithm.SHA1),
            GitBlobIdentity(
                kind=GitObjectKind.BLOB,
                algorithm=GitHashAlgorithm.SHA256,
                full_digest="3" * 64,
            ),
        ),
        (
            _snapshot("1" * 64, GitHashAlgorithm.SHA256),
            GitBlobIdentity(
                kind=GitObjectKind.BLOB,
                algorithm=GitHashAlgorithm.SHA1,
                full_digest="3" * 40,
            ),
        ),
        (
            _snapshot("1" * 40, GitHashAlgorithm.SHA1),
            GitTreeIdentity(
                kind=GitObjectKind.TREE,
                algorithm=GitHashAlgorithm.SHA256,
                full_digest="4" * 64,
            ),
        ),
        (
            _snapshot("1" * 64, GitHashAlgorithm.SHA256),
            GitTreeIdentity(
                kind=GitObjectKind.TREE,
                algorithm=GitHashAlgorithm.SHA1,
                full_digest="4" * 40,
            ),
        ),
    ),
)
def test_path_binding_rejects_hash_algorithm_mismatch(
    snapshot: RepositorySnapshotIdentity,
    git_object: GitBlobIdentity | GitTreeIdentity,
) -> None:
    with pytest.raises(ValidationError):
        RepositorySnapshotPathBinding(
            snapshot=snapshot,
            path=_path(),
            git_object=git_object,
        )


def test_constructed_path_binding_is_revalidated() -> None:
    invalid = RepositorySnapshotPathBinding.model_construct(
        snapshot=_snapshot("1" * 40, GitHashAlgorithm.SHA1),
        path=_path(),
        git_object=GitBlobIdentity(
            kind=GitObjectKind.BLOB,
            algorithm=GitHashAlgorithm.SHA256,
            full_digest="3" * 64,
        ),
    )

    with pytest.raises(ValidationError):
        RepositorySnapshotPathBinding.model_validate(invalid)


def _canonical_blob_bindings() -> tuple[RepositorySnapshotPathBinding, ...]:
    snapshot = _canonical_snapshot()
    return tuple(
        RepositorySnapshotPathBinding(
            snapshot=snapshot,
            path=_path(path),
            git_object=_blob(digest),
        )
        for path, digest in CANONICAL_BLOB_PATH_BINDINGS
    )


def _canonical_tree_bindings() -> tuple[RepositorySnapshotPathBinding, ...]:
    snapshot = _canonical_snapshot()
    return tuple(
        RepositorySnapshotPathBinding(
            snapshot=snapshot,
            path=_path(path),
            git_object=_tree(digest),
        )
        for path, digest in CANONICAL_TREE_PATH_BINDINGS
    )


def _collection(
    bindings: tuple[RepositorySnapshotPathBinding, ...] = (),
    snapshot: RepositorySnapshotIdentity | None = None,
) -> RepositorySnapshotPathBindingCollection:
    return RepositorySnapshotPathBindingCollection(
        snapshot=snapshot if snapshot is not None else _snapshot(),
        bindings=bindings,
    )


def test_empty_collection_aggregates_zero_supplied_bindings() -> None:
    snapshot = _snapshot()

    collection = _collection(snapshot=snapshot)

    assert collection.snapshot == snapshot
    assert collection.bindings == ()
    assert len(collection.bindings) == 0


def test_empty_and_nonempty_collections_over_one_snapshot_are_both_valid() -> None:
    snapshot = _snapshot()

    empty = _collection(snapshot=snapshot)
    populated = _collection((_binding(snapshot=snapshot),), snapshot=snapshot)

    assert empty.snapshot == populated.snapshot
    assert empty != populated
    assert empty.bindings == ()
    assert len(populated.bindings) == 1


def test_distinct_collections_over_one_snapshot_may_overlap_on_paths() -> None:
    snapshot = _snapshot()
    first = _collection((_binding("LICENSE", snapshot=snapshot),), snapshot=snapshot)
    second = _collection(
        (
            _binding("LICENSE", _blob("4" * 40), snapshot=snapshot),
            _binding("README.md", snapshot=snapshot),
        ),
        snapshot=snapshot,
    )

    assert first != second
    assert first.bindings[0].path == second.bindings[0].path
    assert first.bindings[0].git_object != second.bindings[0].git_object


def test_single_binding_collection_is_representable() -> None:
    binding = _binding()

    collection = _collection((binding,))

    assert collection.bindings == (binding,)


def test_canonical_four_blob_aggregate_is_representable() -> None:
    bindings = _canonical_blob_bindings()

    collection = _collection(bindings, snapshot=_canonical_snapshot())

    assert len(collection.bindings) == 4
    assert tuple(binding.path.root for binding in collection.bindings) == tuple(
        path for path, _ in CANONICAL_BLOB_PATH_BINDINGS
    )
    assert all(
        type(binding.git_object) is GitBlobIdentity for binding in collection.bindings
    )


def test_canonical_nine_binding_aggregate_tolerates_prefix_chains() -> None:
    bindings = _canonical_blob_bindings() + _canonical_tree_bindings()

    collection = _collection(bindings, snapshot=_canonical_snapshot())

    assert len(collection.bindings) == 9
    paths = tuple(binding.path.root for binding in collection.bindings)
    assert len(frozenset(paths)) == 9
    for ancestor in ("src", "src/_pytest", "src/_pytest/assertion"):
        assert ancestor in paths
    assert "src/_pytest/assertion/rewrite.py" in paths


def test_tree_binding_and_descendant_blob_binding_may_coexist() -> None:
    snapshot = _snapshot()

    collection = _collection(
        (
            _binding("a", _tree("5" * 40), snapshot=snapshot),
            _binding("a/b", snapshot=snapshot),
        ),
        snapshot=snapshot,
    )

    assert len(collection.bindings) == 2
    assert type(collection.bindings[0].git_object) is GitTreeIdentity
    assert type(collection.bindings[1].git_object) is GitBlobIdentity


def test_blob_binding_and_descendant_binding_are_not_rejected() -> None:
    snapshot = _snapshot()

    collection = _collection(
        (
            _binding("a", snapshot=snapshot),
            _binding("a/b", _blob("4" * 40), snapshot=snapshot),
        ),
        snapshot=snapshot,
    )

    assert tuple(binding.path.root for binding in collection.bindings) == ("a", "a/b")


def test_collection_accepts_the_maximum_supported_cardinality() -> None:
    snapshot = _snapshot()
    bindings = tuple(
        _binding(f"generated/{index}.txt", snapshot=snapshot) for index in range(4096)
    )

    collection = _collection(bindings, snapshot=snapshot)

    assert len(collection.bindings) == 4096


def test_collection_rejects_more_than_the_maximum_supported_cardinality() -> None:
    snapshot = _snapshot()
    bindings = tuple(
        _binding(f"generated/{index}.txt", snapshot=snapshot) for index in range(4097)
    )

    with pytest.raises(ValidationError) as error:
        _collection(bindings, snapshot=snapshot)

    assert error.value.errors()[0]["type"] == "too_long"


def test_supplied_order_is_preserved_without_sorting_or_truncation() -> None:
    snapshot = _canonical_snapshot()
    bindings = _canonical_blob_bindings()

    collection = _collection(bindings, snapshot=snapshot)

    assert collection.bindings == bindings
    assert tuple(binding.path.root for binding in collection.bindings) != tuple(
        sorted(binding.path.root for binding in bindings)
    )


def test_reversed_supply_is_a_distinct_value_without_structural_meaning() -> None:
    snapshot = _canonical_snapshot()
    bindings = _canonical_blob_bindings()
    reversed_bindings = tuple(reversed(bindings))

    forward = _collection(bindings, snapshot=snapshot)
    reverse = _collection(reversed_bindings, snapshot=snapshot)

    assert forward != reverse
    assert forward.bindings == tuple(reversed(reverse.bindings))
    assert forward.snapshot == reverse.snapshot
    assert frozenset(forward.bindings) == frozenset(reverse.bindings)


def test_same_object_may_bind_to_distinct_paths_within_one_collection() -> None:
    snapshot = _snapshot()
    shared = _blob()

    collection = _collection(
        (
            _binding("a/duplicate.txt", shared, snapshot=snapshot),
            _binding("b/duplicate.txt", shared, snapshot=snapshot),
        ),
        snapshot=snapshot,
    )

    assert collection.bindings[0].git_object == collection.bindings[1].git_object
    assert collection.bindings[0].path != collection.bindings[1].path


def test_collection_is_frozen() -> None:
    collection = _collection((_binding(),))

    with pytest.raises(ValidationError):
        collection.bindings = ()


def test_collection_semantic_json_round_trip_preserves_exact_value() -> None:
    snapshot = _canonical_snapshot()
    original = _collection(_canonical_blob_bindings(), snapshot=snapshot)

    encoded = original.model_dump_json()
    restored = RepositorySnapshotPathBindingCollection.model_validate_json(encoded)

    assert restored == original
    assert restored.bindings == original.bindings
    assert type(restored.snapshot) is RepositorySnapshotIdentity
    assert all(
        type(binding) is RepositorySnapshotPathBinding for binding in restored.bindings
    )
    assert json.loads(encoded) == original.model_dump(mode="json")
    assert set(json.loads(encoded)) == {"snapshot", "bindings"}


def test_collection_accepts_tuple_python_input_and_rejects_other_containers() -> None:
    snapshot = _snapshot()
    binding = _binding(snapshot=snapshot)

    assert _collection((binding,), snapshot=snapshot).bindings == (binding,)

    containers: tuple[object, ...] = (
        [binding],
        set((binding,)),
        frozenset((binding,)),
        (item for item in (binding,)),
    )
    for container in containers:
        with pytest.raises(ValidationError) as error:
            RepositorySnapshotPathBindingCollection.model_validate(
                {"snapshot": snapshot, "bindings": container}
            )
        assert error.value.errors()[0]["type"] == "tuple_type"


@pytest.mark.parametrize("missing", ("snapshot", "bindings"))
def test_collection_required_fields_cannot_be_omitted(missing: str) -> None:
    payload: dict[str, object] = {"snapshot": _snapshot(), "bindings": ()}
    del payload[missing]

    with pytest.raises(ValidationError):
        RepositorySnapshotPathBindingCollection.model_validate(payload)


@pytest.mark.parametrize(
    "field",
    (
        "binding_count",
        "root_tree",
        "members",
        "entries",
        "complete",
        "completeness",
        "absent",
        "evidence",
        "ordered",
        "prefix",
    ),
)
def test_collection_rejects_count_membership_and_completeness_fields(
    field: str,
) -> None:
    payload: dict[str, object] = {
        "snapshot": _snapshot(),
        "bindings": (),
        field: 0,
    }

    with pytest.raises(ValidationError):
        RepositorySnapshotPathBindingCollection.model_validate(payload)


@pytest.mark.parametrize(
    "snapshot",
    (_repository(), _commit(), _tree(), _blob(), _qualified_path(), "github/37489525"),
)
def test_collection_rejects_non_snapshot_subjects(snapshot: object) -> None:
    with pytest.raises(ValidationError):
        RepositorySnapshotPathBindingCollection.model_validate(
            {"snapshot": snapshot, "bindings": ()}
        )


@pytest.mark.parametrize(
    "child",
    ("LICENSE", 37489525, None, _qualified_path(), _blob()),
)
def test_collection_rejects_untyped_children(child: object) -> None:
    with pytest.raises(ValidationError):
        RepositorySnapshotPathBindingCollection.model_validate(
            {"snapshot": _snapshot(), "bindings": (child,)}
        )


def test_collection_rejects_python_mapping_children() -> None:
    binding = _binding()

    with pytest.raises(ValidationError):
        RepositorySnapshotPathBindingCollection.model_validate(
            {
                "snapshot": _snapshot(),
                "bindings": (binding.model_dump(mode="python"),),
            }
        )


def test_collection_rejects_a_single_foreign_snapshot_child() -> None:
    snapshot = _snapshot()
    foreign = _snapshot(repository_id="99999999")

    with pytest.raises(ValidationError, match="collection snapshot subject"):
        _collection((_binding(snapshot=foreign),), snapshot=snapshot)


def test_collection_rejects_mixed_local_and_foreign_snapshot_children() -> None:
    snapshot = _snapshot()
    foreign = _snapshot("2" * 40)

    with pytest.raises(ValidationError, match="collection snapshot subject"):
        _collection(
            (
                _binding("LICENSE", snapshot=snapshot),
                _binding("README.md", snapshot=foreign),
            ),
            snapshot=snapshot,
        )


def test_collection_rejects_an_identical_duplicate_path_without_deduplication() -> None:
    snapshot = _snapshot()
    binding = _binding("LICENSE", snapshot=snapshot)

    with pytest.raises(ValidationError, match="must not repeat a repository path"):
        _collection((binding, binding), snapshot=snapshot)


def test_collection_rejects_a_conflicting_duplicate_path() -> None:
    snapshot = _snapshot()

    with pytest.raises(ValidationError, match="must not repeat a repository path"):
        _collection(
            (
                _binding("LICENSE", _blob("3" * 40), snapshot=snapshot),
                _binding("LICENSE", _blob("4" * 40), snapshot=snapshot),
            ),
            snapshot=snapshot,
        )


def test_collection_rejects_a_duplicate_path_across_object_kinds() -> None:
    snapshot = _snapshot()

    with pytest.raises(ValidationError, match="must not repeat a repository path"):
        _collection(
            (
                _binding("src", _tree("5" * 40), snapshot=snapshot),
                _binding("src", _blob("6" * 40), snapshot=snapshot),
            ),
            snapshot=snapshot,
        )


def test_collection_extra_fields_fail_closed() -> None:
    with pytest.raises(ValidationError):
        RepositorySnapshotPathBindingCollection.model_validate(
            {"snapshot": _snapshot(), "bindings": (), "verified": True}
        )


def test_collection_revalidates_nested_children() -> None:
    snapshot = _snapshot()
    invalid_child = RepositorySnapshotPathBinding.model_construct(
        snapshot=snapshot,
        path=GitRepositoryPath.model_construct(root="/LICENSE"),
        git_object=_blob(),
    )

    with pytest.raises(ValidationError):
        _collection((invalid_child,), snapshot=snapshot)


def test_constructed_collection_is_revalidated() -> None:
    snapshot = _snapshot()
    binding = _binding("LICENSE", snapshot=snapshot)
    invalid = RepositorySnapshotPathBindingCollection.model_construct(
        snapshot=snapshot,
        bindings=(binding, binding),
    )

    with pytest.raises(ValidationError):
        RepositorySnapshotPathBindingCollection.model_validate(invalid)


def _scope(
    paths: tuple[GitRepositoryPath, ...] = (),
    snapshot: RepositorySnapshotIdentity | None = None,
) -> RepositorySnapshotDeclaredPathScope:
    return RepositorySnapshotDeclaredPathScope(
        snapshot=snapshot if snapshot is not None else _snapshot(),
        declared_paths=paths,
    )


def _canonical_blob_scope_paths() -> tuple[GitRepositoryPath, ...]:
    return tuple(_path(path) for path, _ in CANONICAL_BLOB_PATH_BINDINGS)


def _canonical_nine_scope_paths() -> tuple[GitRepositoryPath, ...]:
    return _canonical_blob_scope_paths() + tuple(
        _path(path) for path, _ in CANONICAL_TREE_PATH_BINDINGS
    )


def test_empty_declared_scope_declares_zero_paths() -> None:
    snapshot = _snapshot()

    scope = _scope(snapshot=snapshot)

    assert scope.snapshot == snapshot
    assert scope.declared_paths == ()
    assert len(scope.declared_paths) == 0


def test_empty_and_nonempty_scopes_over_one_snapshot_are_both_valid() -> None:
    snapshot = _snapshot()

    empty = _scope(snapshot=snapshot)
    populated = _scope((_path("LICENSE"),), snapshot=snapshot)

    assert empty.snapshot == populated.snapshot
    assert empty != populated
    assert empty.declared_paths == ()
    assert populated.declared_paths == (_path("LICENSE"),)


def test_single_path_scope_is_representable() -> None:
    scope = _scope((_path("LICENSE"),))

    assert scope.declared_paths == (_path("LICENSE"),)


def test_supplied_canonical_four_path_scope_is_representable() -> None:
    paths = _canonical_blob_scope_paths()

    scope = _scope(paths, snapshot=_canonical_snapshot())

    assert len(scope.declared_paths) == 4
    assert tuple(path.root for path in scope.declared_paths) == tuple(
        path for path, _ in CANONICAL_BLOB_PATH_BINDINGS
    )


def test_supplied_canonical_nine_path_scope_is_representable() -> None:
    paths = _canonical_nine_scope_paths()

    scope = _scope(paths, snapshot=_canonical_snapshot())

    assert len(scope.declared_paths) == 9
    assert len(frozenset(scope.declared_paths)) == 9
    declared = tuple(path.root for path in scope.declared_paths)
    for ancestor in ("src", "src/_pytest", "src/_pytest/assertion"):
        assert ancestor in declared
    assert "src/_pytest/assertion/rewrite.py" in declared


def test_scope_accepts_the_maximum_supported_cardinality() -> None:
    paths = tuple(_path(f"generated/{index}.txt") for index in range(4096))

    scope = _scope(paths)

    assert len(scope.declared_paths) == 4096


def test_scope_rejects_more_than_the_maximum_supported_cardinality() -> None:
    paths = tuple(_path(f"generated/{index}.txt") for index in range(4097))

    with pytest.raises(ValidationError) as error:
        _scope(paths)

    assert error.value.errors()[0]["type"] == "too_long"


def test_supplied_declaration_order_is_preserved_without_sorting() -> None:
    paths = _canonical_blob_scope_paths()

    scope = _scope(paths, snapshot=_canonical_snapshot())

    assert scope.declared_paths == paths
    assert tuple(path.root for path in scope.declared_paths) != tuple(
        sorted(path.root for path in paths)
    )


def test_reversed_declaration_is_a_distinct_value_without_structural_meaning() -> None:
    snapshot = _canonical_snapshot()
    paths = _canonical_blob_scope_paths()

    forward = _scope(paths, snapshot=snapshot)
    reverse = _scope(tuple(reversed(paths)), snapshot=snapshot)

    assert forward != reverse
    assert forward.declared_paths == tuple(reversed(reverse.declared_paths))
    assert forward.snapshot == reverse.snapshot
    assert frozenset(forward.declared_paths) == frozenset(reverse.declared_paths)


def test_one_path_may_be_declared_in_two_independent_scopes() -> None:
    snapshot = _snapshot()

    first = _scope((_path("LICENSE"),), snapshot=snapshot)
    second = _scope(
        (_path("LICENSE"), _path("README.md")),
        snapshot=snapshot,
    )

    assert first != second
    assert first.declared_paths[0] == second.declared_paths[0]


def test_scope_paths_may_prefix_one_another() -> None:
    scope = _scope(
        (
            _path("src"),
            _path("src/_pytest"),
            _path("src/_pytest/assertion/rewrite.py"),
        )
    )

    assert len(scope.declared_paths) == 3


def test_case_distinct_scope_paths_remain_distinct() -> None:
    lower = _scope((_path("license"),))
    upper = _scope((_path("LICENSE"),))

    assert lower != upper
    assert lower.declared_paths[0].root == "license"
    assert upper.declared_paths[0].root == "LICENSE"


def test_nfc_and_nfd_scope_paths_remain_distinct() -> None:
    composed = _scope((_path(SYNTHETIC_NFC_PATH),))
    decomposed = _scope((_path(SYNTHETIC_NFD_PATH),))

    assert SYNTHETIC_NFC_PATH != SYNTHETIC_NFD_PATH
    assert composed != decomposed

    both = _scope((_path(SYNTHETIC_NFC_PATH), _path(SYNTHETIC_NFD_PATH)))

    assert len(both.declared_paths) == 2


def test_scope_is_frozen() -> None:
    scope = _scope((_path("LICENSE"),))

    with pytest.raises(ValidationError):
        scope.declared_paths = ()


def test_scope_semantic_json_round_trip_preserves_exact_value() -> None:
    original = _scope(_canonical_nine_scope_paths(), snapshot=_canonical_snapshot())

    encoded = original.model_dump_json()
    restored = RepositorySnapshotDeclaredPathScope.model_validate_json(encoded)

    assert restored == original
    assert restored.declared_paths == original.declared_paths
    assert type(restored.snapshot) is RepositorySnapshotIdentity
    assert all(type(path) is GitRepositoryPath for path in restored.declared_paths)
    assert json.loads(encoded) == original.model_dump(mode="json")
    assert set(json.loads(encoded)) == {"snapshot", "declared_paths"}


def test_scope_accepts_tuple_python_input_and_rejects_other_containers() -> None:
    snapshot = _snapshot()
    path = _path("LICENSE")

    assert _scope((path,), snapshot=snapshot).declared_paths == (path,)

    containers: tuple[object, ...] = (
        [path],
        set((path,)),
        frozenset((path,)),
        (item for item in (path,)),
    )
    for container in containers:
        with pytest.raises(ValidationError) as error:
            RepositorySnapshotDeclaredPathScope.model_validate(
                {"snapshot": snapshot, "declared_paths": container}
            )
        assert error.value.errors()[0]["type"] == "tuple_type"


@pytest.mark.parametrize("missing", ("snapshot", "declared_paths"))
def test_scope_required_fields_cannot_be_omitted(missing: str) -> None:
    payload: dict[str, object] = {"snapshot": _snapshot(), "declared_paths": ()}
    del payload[missing]

    with pytest.raises(ValidationError):
        RepositorySnapshotDeclaredPathScope.model_validate(payload)


@pytest.mark.parametrize(
    "field",
    (
        "bindings",
        "collection",
        "status",
        "outcome",
        "assessment",
        "complete",
        "completeness",
        "coverage",
        "satisfied",
        "partial",
        "unknown",
        "unavailable",
        "absent",
        "missing_paths",
        "resolved_count",
        "declared_path_count",
        "members",
        "membership",
        "root_tree",
        "evidence",
        "prefix",
        "recursive",
    ),
)
def test_scope_rejects_accounting_membership_and_evidence_fields(field: str) -> None:
    payload: dict[str, object] = {
        "snapshot": _snapshot(),
        "declared_paths": (),
        field: 0,
    }

    with pytest.raises(ValidationError):
        RepositorySnapshotDeclaredPathScope.model_validate(payload)


@pytest.mark.parametrize(
    "snapshot",
    (_repository(), _commit(), _tree(), _blob(), _qualified_path(), "github/37489525"),
)
def test_scope_rejects_non_snapshot_subjects(snapshot: object) -> None:
    with pytest.raises(ValidationError):
        RepositorySnapshotDeclaredPathScope.model_validate(
            {"snapshot": snapshot, "declared_paths": ()}
        )


@pytest.mark.parametrize(
    "declared",
    ("LICENSE", b"LICENSE", 37489525, None, _qualified_path(), _blob()),
)
def test_scope_rejects_untyped_python_path_values(declared: object) -> None:
    with pytest.raises(ValidationError):
        RepositorySnapshotDeclaredPathScope.model_validate(
            {"snapshot": _snapshot(), "declared_paths": (declared,)}
        )


@pytest.mark.parametrize(
    "path",
    ("", ".", "..", "/LICENSE", "LICENSE/", "a//b", "a\\b", "C:/a", "a/./b"),
)
def test_scope_inherits_exact_repository_path_rejections(path: str) -> None:
    payload = {
        "snapshot": json.loads(_snapshot().model_dump_json()),
        "declared_paths": [path],
    }

    with pytest.raises(ValidationError):
        RepositorySnapshotDeclaredPathScope.model_validate_json(json.dumps(payload))


def test_scope_rejects_a_duplicate_declared_path_without_deduplication() -> None:
    path = _path("LICENSE")

    with pytest.raises(ValidationError, match="must not repeat a repository path"):
        _scope((path, path))


def test_scope_rejects_a_duplicate_declared_path_in_json_input() -> None:
    payload = {
        "snapshot": json.loads(_snapshot().model_dump_json()),
        "declared_paths": ["LICENSE", "README.md", "LICENSE"],
    }

    with pytest.raises(ValidationError, match="must not repeat a repository path"):
        RepositorySnapshotDeclaredPathScope.model_validate_json(json.dumps(payload))


def test_scope_extra_fields_fail_closed() -> None:
    with pytest.raises(ValidationError):
        RepositorySnapshotDeclaredPathScope.model_validate(
            {"snapshot": _snapshot(), "declared_paths": (), "verified": True}
        )


def test_scope_revalidates_nested_snapshot() -> None:
    invalid_snapshot = RepositorySnapshotIdentity.model_construct(
        repository=_repository(),
        revision=GitCommitIdentity.model_construct(
            schema_version=1,
            kind=GitObjectKind.COMMIT,
            algorithm=GitHashAlgorithm.SHA1,
            full_digest="0" * 40,
        ),
    )

    with pytest.raises(ValidationError):
        _scope((_path("LICENSE"),), snapshot=invalid_snapshot)


def test_scope_revalidates_nested_declared_paths() -> None:
    invalid_path = GitRepositoryPath.model_construct(root="/LICENSE")

    with pytest.raises(ValidationError):
        _scope((invalid_path,))


def test_constructed_scope_is_revalidated() -> None:
    path = _path("LICENSE")
    invalid = RepositorySnapshotDeclaredPathScope.model_construct(
        snapshot=_snapshot(),
        declared_paths=(path, path),
    )

    with pytest.raises(ValidationError):
        RepositorySnapshotDeclaredPathScope.model_validate(invalid)


def test_declared_scope_is_independent_of_any_binding_collection() -> None:
    snapshot = _canonical_snapshot()
    scope = _scope(_canonical_blob_scope_paths(), snapshot=snapshot)
    collection = _collection(_canonical_blob_bindings(), snapshot=snapshot)

    assert tuple(RepositorySnapshotDeclaredPathScope.model_fields) == (
        "snapshot",
        "declared_paths",
    )
    assert scope.snapshot == collection.snapshot
    assert set(json.loads(scope.model_dump_json())) == {"snapshot", "declared_paths"}

    unbound = _scope((_path("never/bound.txt"),), snapshot=snapshot)

    assert unbound.declared_paths == (_path("never/bound.txt"),)
    assert len(collection.bindings) == 4


def _coverage(
    paths: tuple[GitRepositoryPath, ...],
    bindings: tuple[RepositorySnapshotPathBinding, ...],
    scope_snapshot: RepositorySnapshotIdentity | None = None,
    collection_snapshot: RepositorySnapshotIdentity | None = None,
) -> RepositorySnapshotDeclaredPathScopeCoverage:
    return RepositorySnapshotDeclaredPathScopeCoverage(
        scope=_scope(paths, snapshot=scope_snapshot or _canonical_snapshot()),
        collection=_collection(
            bindings, snapshot=collection_snapshot or _canonical_snapshot()
        ),
    )


def test_canonical_four_path_scope_is_covered_by_the_four_blob_collection() -> None:
    coverage = _coverage(_canonical_blob_scope_paths(), _canonical_blob_bindings())

    assert coverage.scope.declared_paths == _canonical_blob_scope_paths()
    assert coverage.collection.bindings == _canonical_blob_bindings()


def test_canonical_four_path_scope_is_covered_by_the_nine_binding_collection() -> None:
    bindings = _canonical_blob_bindings() + _canonical_tree_bindings()

    coverage = _coverage(_canonical_blob_scope_paths(), bindings)

    assert len(coverage.scope.declared_paths) == 4
    assert len(coverage.collection.bindings) == 9


def test_canonical_nine_path_scope_is_covered_by_the_nine_binding_collection() -> None:
    bindings = _canonical_blob_bindings() + _canonical_tree_bindings()

    coverage = _coverage(_canonical_nine_scope_paths(), bindings)

    assert len(coverage.scope.declared_paths) == 9
    assert len(coverage.collection.bindings) == 9


def test_canonical_nine_path_scope_is_not_covered_by_the_four_blob_collection() -> None:
    with pytest.raises(ValidationError, match="must have a supplied binding"):
        _coverage(_canonical_nine_scope_paths(), _canonical_blob_bindings())


def test_bindings_outside_the_declared_scope_do_not_prevent_coverage() -> None:
    bindings = _canonical_blob_bindings() + _canonical_tree_bindings()

    coverage = _coverage((_path("LICENSE"),), bindings)

    declared = tuple(path.root for path in coverage.scope.declared_paths)
    supplied = tuple(binding.path.root for binding in coverage.collection.bindings)
    assert declared == ("LICENSE",)
    assert len(supplied) == 9
    assert any(path not in declared for path in supplied)


def test_one_declared_path_without_a_binding_prevents_coverage() -> None:
    bindings = _canonical_blob_bindings() + _canonical_tree_bindings()
    paths = _canonical_blob_scope_paths() + (_path("never/bound.txt"),)

    with pytest.raises(ValidationError, match="must have a supplied binding"):
        _coverage(paths, bindings)


@pytest.mark.parametrize(
    ("reverse_scope", "reverse_collection"),
    ((False, False), (True, False), (False, True), (True, True)),
)
def test_coverage_validity_does_not_depend_on_either_supplied_order(
    reverse_scope: bool,
    reverse_collection: bool,
) -> None:
    paths = _canonical_blob_scope_paths()
    bindings = _canonical_blob_bindings()

    coverage = _coverage(
        tuple(reversed(paths)) if reverse_scope else paths,
        tuple(reversed(bindings)) if reverse_collection else bindings,
    )

    assert len(coverage.scope.declared_paths) == 4
    assert len(coverage.collection.bindings) == 4


def test_reordered_coverage_witnesses_remain_distinct_values() -> None:
    paths = _canonical_blob_scope_paths()
    bindings = _canonical_blob_bindings()

    forward = _coverage(paths, bindings)
    reversed_scope = _coverage(tuple(reversed(paths)), bindings)
    reversed_collection = _coverage(paths, tuple(reversed(bindings)))
    both = _coverage(tuple(reversed(paths)), tuple(reversed(bindings)))

    assert forward != reversed_scope
    assert forward != reversed_collection
    assert forward != both
    assert reversed_scope != reversed_collection
    assert forward.scope.declared_paths == paths
    assert forward.collection.bindings == bindings


def test_coverage_preserves_both_supplied_children_unchanged() -> None:
    scope = _scope(_canonical_blob_scope_paths(), snapshot=_canonical_snapshot())
    collection = _collection(_canonical_blob_bindings(), snapshot=_canonical_snapshot())

    coverage = RepositorySnapshotDeclaredPathScopeCoverage(
        scope=scope, collection=collection
    )

    assert coverage.scope == scope
    assert coverage.collection == collection
    assert coverage.scope.declared_paths == scope.declared_paths
    assert coverage.collection.bindings == collection.bindings


def test_a_blob_backed_binding_covers_its_declared_path() -> None:
    bindings = _canonical_blob_bindings() + _canonical_tree_bindings()

    coverage = _coverage((_path("LICENSE"),), bindings)

    covering = coverage.collection.bindings[0]
    assert covering.path == _path("LICENSE")
    assert type(covering.git_object) is GitBlobIdentity


def test_a_tree_backed_binding_covers_its_declared_path() -> None:
    bindings = _canonical_blob_bindings() + _canonical_tree_bindings()

    coverage = _coverage((_path("src"),), bindings)

    covering = coverage.collection.bindings[4]
    assert covering.path == _path("src")
    assert type(covering.git_object) is GitTreeIdentity


def test_coverage_semantic_json_round_trip_preserves_exact_value() -> None:
    original = _coverage(
        _canonical_nine_scope_paths(),
        _canonical_blob_bindings() + _canonical_tree_bindings(),
    )

    encoded = original.model_dump_json()
    restored = RepositorySnapshotDeclaredPathScopeCoverage.model_validate_json(encoded)

    assert restored == original
    assert type(restored.scope) is RepositorySnapshotDeclaredPathScope
    assert type(restored.collection) is RepositorySnapshotPathBindingCollection
    assert restored.scope.declared_paths == original.scope.declared_paths
    assert restored.collection.bindings == original.collection.bindings
    assert json.loads(encoded) == original.model_dump(mode="json")
    assert set(json.loads(encoded)) == {"scope", "collection"}


def test_coverage_is_frozen() -> None:
    coverage = _coverage(_canonical_blob_scope_paths(), _canonical_blob_bindings())

    with pytest.raises(ValidationError):
        coverage.scope = _scope((_path("LICENSE"),), snapshot=_canonical_snapshot())


@pytest.mark.parametrize(
    ("declared", "bindings"),
    (((), ()), ((), "four"), ("four", ())),
    ids=("empty-scope-empty-collection", "empty-scope", "empty-collection"),
)
def test_coverage_requires_a_non_empty_scope_and_covering_bindings(
    declared: object,
    bindings: object,
) -> None:
    paths = _canonical_blob_scope_paths() if declared == "four" else ()
    supplied = _canonical_blob_bindings() if bindings == "four" else ()

    with pytest.raises(ValidationError):
        _coverage(paths, supplied)


def test_an_empty_declared_scope_remains_a_valid_scope_value() -> None:
    empty = _scope((), snapshot=_canonical_snapshot())

    assert empty.declared_paths == ()

    with pytest.raises(ValidationError, match="declare at least one path"):
        RepositorySnapshotDeclaredPathScopeCoverage(
            scope=empty,
            collection=_collection(
                _canonical_blob_bindings(), snapshot=_canonical_snapshot()
            ),
        )


@pytest.mark.parametrize(
    ("scope_snapshot", "collection_snapshot"),
    (
        ("99999999", None),
        (None, "99999999"),
    ),
    ids=("foreign-scope-repository", "foreign-collection-repository"),
)
def test_coverage_rejects_distinct_repository_subjects(
    scope_snapshot: str | None,
    collection_snapshot: str | None,
) -> None:
    foreign = _snapshot(CANONICAL_REVISION, repository_id="99999999")
    bindings = tuple(
        RepositorySnapshotPathBinding(
            snapshot=foreign, path=_path(path), git_object=_blob(digest)
        )
        for path, digest in CANONICAL_BLOB_PATH_BINDINGS
    )

    with pytest.raises(ValidationError, match="share the snapshot subject"):
        RepositorySnapshotDeclaredPathScopeCoverage(
            scope=_scope(
                _canonical_blob_scope_paths(),
                snapshot=foreign if scope_snapshot else _canonical_snapshot(),
            ),
            collection=_collection(
                bindings if collection_snapshot else _canonical_blob_bindings(),
                snapshot=foreign if collection_snapshot else _canonical_snapshot(),
            ),
        )


def test_coverage_rejects_the_same_repository_under_a_distinct_revision() -> None:
    other = _snapshot("4" * 40)
    bindings = tuple(
        RepositorySnapshotPathBinding(
            snapshot=other, path=_path(path), git_object=_blob(digest)
        )
        for path, digest in CANONICAL_BLOB_PATH_BINDINGS
    )

    with pytest.raises(ValidationError, match="share the snapshot subject"):
        RepositorySnapshotDeclaredPathScopeCoverage(
            scope=_scope(_canonical_blob_scope_paths(), snapshot=_canonical_snapshot()),
            collection=_collection(bindings, snapshot=other),
        )


@pytest.mark.parametrize("missing", ("scope", "collection"))
def test_coverage_required_fields_cannot_be_omitted(missing: str) -> None:
    payload: dict[str, object] = {
        "scope": _scope(_canonical_blob_scope_paths(), snapshot=_canonical_snapshot()),
        "collection": _collection(
            _canonical_blob_bindings(), snapshot=_canonical_snapshot()
        ),
    }
    del payload[missing]

    with pytest.raises(ValidationError):
        RepositorySnapshotDeclaredPathScopeCoverage.model_validate(payload)


@pytest.mark.parametrize(
    "field",
    (
        "snapshot",
        "declared_paths",
        "bindings",
        "status",
        "outcome",
        "assessment",
        "result",
        "complete",
        "completeness",
        "coverage_status",
        "covered",
        "fully_covered",
        "satisfied",
        "partial",
        "absent",
        "missing",
        "missing_paths",
        "covered_paths",
        "uncovered_paths",
        "unmatched_paths",
        "unknown",
        "unavailable",
        "inaccessible",
        "omitted",
        "unresolved",
        "membership",
        "member",
        "declared_count",
        "binding_count",
        "covered_count",
        "missing_count",
        "root_tree",
        "evidence",
    ),
)
def test_coverage_rejects_status_count_and_negative_state_fields(field: str) -> None:
    payload: dict[str, object] = {
        "scope": _scope(_canonical_blob_scope_paths(), snapshot=_canonical_snapshot()),
        "collection": _collection(
            _canonical_blob_bindings(), snapshot=_canonical_snapshot()
        ),
        field: 0,
    }

    with pytest.raises(ValidationError):
        RepositorySnapshotDeclaredPathScopeCoverage.model_validate(payload)


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("scope", "LICENSE"),
        ("scope", 37489525),
        ("scope", None),
        ("collection", "LICENSE"),
        ("collection", 37489525),
        ("collection", None),
    ),
)
def test_coverage_rejects_untyped_children(field: str, value: object) -> None:
    payload: dict[str, object] = {
        "scope": _scope(_canonical_blob_scope_paths(), snapshot=_canonical_snapshot()),
        "collection": _collection(
            _canonical_blob_bindings(), snapshot=_canonical_snapshot()
        ),
    }
    payload[field] = value

    with pytest.raises(ValidationError):
        RepositorySnapshotDeclaredPathScopeCoverage.model_validate(payload)


def test_coverage_rejects_swapped_children() -> None:
    scope = _scope(_canonical_blob_scope_paths(), snapshot=_canonical_snapshot())
    collection = _collection(_canonical_blob_bindings(), snapshot=_canonical_snapshot())

    with pytest.raises(ValidationError):
        RepositorySnapshotDeclaredPathScopeCoverage.model_validate(
            {"scope": collection, "collection": scope}
        )


@pytest.mark.parametrize("field", ("scope", "collection"))
def test_coverage_python_construction_rejects_nested_mappings(field: str) -> None:
    scope = _scope(_canonical_blob_scope_paths(), snapshot=_canonical_snapshot())
    collection = _collection(_canonical_blob_bindings(), snapshot=_canonical_snapshot())
    payload: dict[str, object] = {"scope": scope, "collection": collection}
    payload[field] = (
        scope.model_dump(mode="python")
        if field == "scope"
        else collection.model_dump(mode="python")
    )

    with pytest.raises(ValidationError):
        RepositorySnapshotDeclaredPathScopeCoverage.model_validate(payload)


@pytest.mark.parametrize("field", ("scope", "collection"))
def test_coverage_rejects_hybrid_mappings_with_typed_nested_values(
    field: str,
) -> None:
    scope = _scope(_canonical_blob_scope_paths(), snapshot=_canonical_snapshot())
    collection = _collection(_canonical_blob_bindings(), snapshot=_canonical_snapshot())
    hybrid: dict[str, object] = (
        {"snapshot": scope.snapshot, "declared_paths": scope.declared_paths}
        if field == "scope"
        else {
            "snapshot": collection.snapshot,
            "bindings": collection.bindings,
        }
    )
    payload: dict[str, object] = {"scope": scope, "collection": collection}
    payload[field] = hybrid

    with pytest.raises(ValidationError, match="typed values in Python input"):
        RepositorySnapshotDeclaredPathScopeCoverage.model_validate(payload)


class _AttributeBackedScope:
    def __init__(self, scope: RepositorySnapshotDeclaredPathScope) -> None:
        self.snapshot = scope.snapshot
        self.declared_paths = scope.declared_paths


class _AttributeBackedCollection:
    def __init__(self, collection: RepositorySnapshotPathBindingCollection) -> None:
        self.snapshot = collection.snapshot
        self.bindings = collection.bindings


@pytest.mark.parametrize("field", ("scope", "collection"))
def test_coverage_rejects_attribute_backed_children_under_from_attributes(
    field: str,
) -> None:
    scope = _scope(_canonical_blob_scope_paths(), snapshot=_canonical_snapshot())
    collection = _collection(_canonical_blob_bindings(), snapshot=_canonical_snapshot())
    payload: dict[str, object] = {"scope": scope, "collection": collection}
    payload[field] = (
        _AttributeBackedScope(scope)
        if field == "scope"
        else _AttributeBackedCollection(collection)
    )

    with pytest.raises(ValidationError, match="typed values in Python input"):
        RepositorySnapshotDeclaredPathScopeCoverage.model_validate(
            payload, from_attributes=True
        )


def test_coverage_json_input_still_accepts_nested_arrays() -> None:
    original = _coverage(
        _canonical_nine_scope_paths(),
        _canonical_blob_bindings() + _canonical_tree_bindings(),
    )
    payload = json.loads(original.model_dump_json())

    assert isinstance(payload["collection"]["bindings"], list)
    assert isinstance(payload["scope"]["declared_paths"], list)

    restored = RepositorySnapshotDeclaredPathScopeCoverage.model_validate_json(
        json.dumps(payload)
    )

    assert restored == original
    assert restored.collection.bindings == original.collection.bindings


def test_coverage_extra_fields_fail_closed() -> None:
    with pytest.raises(ValidationError):
        RepositorySnapshotDeclaredPathScopeCoverage.model_validate(
            {
                "scope": _scope(
                    _canonical_blob_scope_paths(), snapshot=_canonical_snapshot()
                ),
                "collection": _collection(
                    _canonical_blob_bindings(), snapshot=_canonical_snapshot()
                ),
                "verified": True,
            }
        )


def test_coverage_revalidates_nested_children() -> None:
    invalid_scope = RepositorySnapshotDeclaredPathScope.model_construct(
        snapshot=_canonical_snapshot(),
        declared_paths=(GitRepositoryPath.model_construct(root="/LICENSE"),),
    )

    with pytest.raises(ValidationError):
        RepositorySnapshotDeclaredPathScopeCoverage(
            scope=invalid_scope,
            collection=_collection(
                _canonical_blob_bindings(), snapshot=_canonical_snapshot()
            ),
        )


def test_constructed_coverage_is_revalidated() -> None:
    invalid = RepositorySnapshotDeclaredPathScopeCoverage.model_construct(
        scope=_scope((_path("never/bound.txt"),), snapshot=_canonical_snapshot()),
        collection=_collection(
            _canonical_blob_bindings(), snapshot=_canonical_snapshot()
        ),
    )

    with pytest.raises(ValidationError, match="must have a supplied binding"):
        RepositorySnapshotDeclaredPathScopeCoverage.model_validate(invalid)


def test_an_uncovered_pair_produces_no_domain_value_at_all() -> None:
    scope = _scope(
        _canonical_blob_scope_paths() + (_path("never/bound.txt"),),
        snapshot=_canonical_snapshot(),
    )
    collection = _collection(_canonical_blob_bindings(), snapshot=_canonical_snapshot())

    with pytest.raises(ValidationError) as error:
        RepositorySnapshotDeclaredPathScopeCoverage(scope=scope, collection=collection)

    assert tuple(RepositorySnapshotDeclaredPathScopeCoverage.model_fields) == (
        "scope",
        "collection",
    )
    message = str(error.value)
    for forbidden in (
        "absent",
        "missing from",
        "unknown",
        "unavailable",
        "inaccessible",
        "omitted",
        "deleted",
        "not found",
        "unresolved",
        "uncovered",
        "unmatched",
    ):
        assert forbidden not in message
    assert scope.declared_paths[4] == _path("never/bound.txt")
    assert len(collection.bindings) == 4


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
    assert tuple(RepositorySnapshotPathBinding.model_fields) == (
        "snapshot",
        "path",
        "git_object",
    )
    assert RepositorySnapshotPathBinding.model_fields["snapshot"].annotation is (
        RepositorySnapshotIdentity
    )
    assert RepositorySnapshotPathBinding.model_fields["path"].annotation is (
        GitRepositoryPath
    )
    assert RepositorySnapshotPathBinding.model_fields["git_object"].annotation == (
        GitBlobIdentity | GitTreeIdentity
    )
    assert (
        RepositorySnapshotPathBinding.model_fields["git_object"].discriminator == "kind"
    )
    assert RepositorySnapshotPathBinding.model_config == {
        "frozen": True,
        "extra": "forbid",
        "strict": True,
        "revalidate_instances": "always",
        "validate_default": True,
    }
    assert tuple(RepositorySnapshotPathBindingCollection.model_fields) == (
        "snapshot",
        "bindings",
    )
    assert RepositorySnapshotPathBindingCollection.model_fields[
        "snapshot"
    ].annotation is (RepositorySnapshotIdentity)
    assert (
        RepositorySnapshotPathBindingCollection.model_fields["bindings"].annotation
        == (tuple[RepositorySnapshotPathBinding, ...])
    )
    assert RepositorySnapshotPathBindingCollection.model_fields[
        "bindings"
    ].metadata == [MaxLen(max_length=4096)]
    assert RepositorySnapshotPathBindingCollection.model_config == {
        "frozen": True,
        "extra": "forbid",
        "strict": True,
        "revalidate_instances": "always",
        "validate_default": True,
    }
    assert tuple(RepositorySnapshotDeclaredPathScope.model_fields) == (
        "snapshot",
        "declared_paths",
    )
    assert RepositorySnapshotDeclaredPathScope.model_fields["snapshot"].annotation is (
        RepositorySnapshotIdentity
    )
    assert (
        RepositorySnapshotDeclaredPathScope.model_fields["declared_paths"].annotation
        == (tuple[GitRepositoryPath, ...])
    )
    assert RepositorySnapshotDeclaredPathScope.model_fields[
        "declared_paths"
    ].metadata == [MaxLen(max_length=4096)]
    assert RepositorySnapshotDeclaredPathScope.model_config == {
        "frozen": True,
        "extra": "forbid",
        "strict": True,
        "revalidate_instances": "always",
        "validate_default": True,
    }
    assert tuple(RepositorySnapshotDeclaredPathScopeCoverage.model_fields) == (
        "scope",
        "collection",
    )
    assert RepositorySnapshotDeclaredPathScopeCoverage.model_fields[
        "scope"
    ].annotation is (RepositorySnapshotDeclaredPathScope)
    assert RepositorySnapshotDeclaredPathScopeCoverage.model_fields[
        "collection"
    ].annotation is (RepositorySnapshotPathBindingCollection)
    assert (
        RepositorySnapshotDeclaredPathScopeCoverage.model_fields["scope"].metadata == []
    )
    assert (
        RepositorySnapshotDeclaredPathScopeCoverage.model_fields["collection"].metadata
        == []
    )
    assert RepositorySnapshotDeclaredPathScopeCoverage.model_config == {
        "frozen": True,
        "extra": "forbid",
        "strict": True,
        "revalidate_instances": "always",
        "validate_default": True,
    }
    assert snapshot_module.__all__ == [
        "RepositorySnapshotIdentity",
        "RepositorySnapshotRootTreeBinding",
        "RepositorySnapshotPathBinding",
        "RepositorySnapshotPathBindingCollection",
        "RepositorySnapshotDeclaredPathScope",
        "RepositorySnapshotDeclaredPathScopeCoverage",
    ]
    assert RepositorySnapshotIdentity.__module__ == "faultatlas.domain.snapshot"
    assert RepositorySnapshotRootTreeBinding.__module__ == "faultatlas.domain.snapshot"
    assert RepositorySnapshotPathBinding.__module__ == "faultatlas.domain.snapshot"
    assert (
        RepositorySnapshotPathBindingCollection.__module__
        == "faultatlas.domain.snapshot"
    )
    assert (
        RepositorySnapshotDeclaredPathScope.__module__ == "faultatlas.domain.snapshot"
    )
    assert (
        RepositorySnapshotDeclaredPathScopeCoverage.__module__
        == "faultatlas.domain.snapshot"
    )


def test_snapshot_module_has_only_the_bounded_models_and_no_io_call_surface() -> None:
    tree = ast.parse(SNAPSHOT_SOURCE.read_text(encoding="utf-8"))
    assert [type(node) for node in tree.body] == [
        ast.Expr,
        ast.ImportFrom,
        ast.ImportFrom,
        ast.ImportFrom,
        ast.ImportFrom,
        ast.ImportFrom,
        ast.Assign,
        ast.ClassDef,
        ast.ClassDef,
        ast.ClassDef,
        ast.ClassDef,
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
        ("collections.abc", ("Mapping",)),
        ("typing", ("Annotated", "Self", "cast")),
        (
            "pydantic",
            (
                "BaseModel",
                "ConfigDict",
                "Field",
                "ValidationInfo",
                "ValidatorFunctionWrapHandler",
                "field_validator",
                "model_validator",
            ),
        ),
        ("faultatlas.domain.identity", ("RepositoryIdentity",)),
        (
            "faultatlas.domain.revision",
            (
                "GitBlobIdentity",
                "GitCommitIdentity",
                "GitRepositoryPath",
                "GitTreeIdentity",
            ),
        ),
    ]
    classes = [node for node in tree.body if isinstance(node, ast.ClassDef)]
    assert [node.name for node in classes] == [
        "RepositorySnapshotIdentity",
        "RepositorySnapshotRootTreeBinding",
        "RepositorySnapshotPathBinding",
        "RepositorySnapshotPathBindingCollection",
        "RepositorySnapshotDeclaredPathScope",
        "RepositorySnapshotDeclaredPathScopeCoverage",
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
    assert [type(node) for node in classes[2].body] == [
        ast.Expr,
        ast.Assign,
        ast.AnnAssign,
        ast.AnnAssign,
        ast.AnnAssign,
        ast.FunctionDef,
        ast.FunctionDef,
        ast.FunctionDef,
        ast.FunctionDef,
    ]
    assert [type(node) for node in classes[3].body] == [
        ast.Expr,
        ast.Assign,
        ast.AnnAssign,
        ast.AnnAssign,
        ast.FunctionDef,
        ast.FunctionDef,
    ]
    assert [type(node) for node in classes[4].body] == [
        ast.Expr,
        ast.Assign,
        ast.AnnAssign,
        ast.AnnAssign,
        ast.FunctionDef,
        ast.FunctionDef,
        ast.FunctionDef,
    ]
    assert [type(node) for node in classes[5].body] == [
        ast.Expr,
        ast.Assign,
        ast.AnnAssign,
        ast.AnnAssign,
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
    ] == [
        ["model_config"],
        ["model_config"],
        ["model_config"],
        ["model_config"],
        ["model_config"],
        ["model_config"],
    ]
    assert [
        [
            node.target.id
            for node in class_node.body
            if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name)
        ]
        for class_node in classes
    ] == [
        ["repository", "revision"],
        ["snapshot", "root_tree"],
        ["snapshot", "path", "git_object"],
        ["snapshot", "bindings"],
        ["snapshot", "declared_paths"],
        ["scope", "collection"],
    ]
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
        [
            "_require_typed_python_path_snapshot",
            "_require_typed_python_path",
            "_require_typed_python_git_object",
            "_require_matching_object_hash_algorithm",
        ],
        [
            "_require_typed_python_collection_snapshot",
            "_require_shared_snapshot_and_unique_paths",
        ],
        [
            "_require_typed_python_scope_snapshot",
            "_require_typed_python_declared_paths",
            "_require_unique_declared_paths",
        ],
        [
            "_require_typed_python_children",
            "_require_covered_declared_paths",
        ],
    ]
    for class_index, expected_left in (
        (1, "self.root_tree.algorithm"),
        (2, "self.git_object.algorithm"),
    ):
        algorithm_validator = classes[class_index].body[-1]
        assert isinstance(algorithm_validator, ast.FunctionDef)
        comparisons = [
            node
            for node in ast.walk(algorithm_validator)
            if isinstance(node, ast.Compare)
        ]
        assert len(comparisons) == 1
        comparison = comparisons[0]
        assert [type(operator) for operator in comparison.ops] == [ast.IsNot]
        assert [
            ast.unparse(comparison.left),
            *(ast.unparse(comparator) for comparator in comparison.comparators),
        ] == [
            expected_left,
            "self.snapshot.revision.algorithm",
        ]
    collection_validator = classes[3].body[-1]
    assert isinstance(collection_validator, ast.FunctionDef)
    collection_comparisons = [
        node for node in ast.walk(collection_validator) if isinstance(node, ast.Compare)
    ]
    assert len(collection_comparisons) == 2
    assert [
        (
            [type(operator) for operator in comparison.ops],
            [
                ast.unparse(comparison.left),
                *(ast.unparse(other) for other in comparison.comparators),
            ],
        )
        for comparison in collection_comparisons
    ] == [
        (
            [ast.NotEq],
            [
                "len(frozenset((binding.path for binding in self.bindings)))",
                "len(self.bindings)",
            ],
        ),
        ([ast.NotEq], ["binding.snapshot", "self.snapshot"]),
    ]
    scope_validator = classes[4].body[-1]
    assert isinstance(scope_validator, ast.FunctionDef)
    scope_comparisons = [
        node for node in ast.walk(scope_validator) if isinstance(node, ast.Compare)
    ]
    assert len(scope_comparisons) == 1
    scope_comparison = scope_comparisons[0]
    assert [type(operator) for operator in scope_comparison.ops] == [ast.NotEq]
    assert [
        ast.unparse(scope_comparison.left),
        *(ast.unparse(other) for other in scope_comparison.comparators),
    ] == [
        "len(frozenset(self.declared_paths))",
        "len(self.declared_paths)",
    ]
    coverage_validator = classes[5].body[-1]
    assert isinstance(coverage_validator, ast.FunctionDef)
    coverage_comparisons = [
        node for node in ast.walk(coverage_validator) if isinstance(node, ast.Compare)
    ]
    assert len(coverage_comparisons) == 2
    assert [
        (
            [type(operator) for operator in comparison.ops],
            [
                ast.unparse(comparison.left),
                *(ast.unparse(other) for other in comparison.comparators),
            ],
        )
        for comparison in coverage_comparisons
    ] == [
        ([ast.NotEq], ["self.scope.snapshot", "self.collection.snapshot"]),
        ([ast.NotIn], ["path", "bound"]),
    ]
    calls = {
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    assert calls == {
        "ConfigDict",
        "Field",
        "ValueError",
        "any",
        "cast",
        "field_validator",
        "frozenset",
        "handler",
        "isinstance",
        "len",
        "model_validator",
        "tuple",
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
        "Annotated",
        "BaseModel",
        "ConfigDict",
        "Field",
        "GitBlobIdentity",
        "GitCommitIdentity",
        "GitRepositoryPath",
        "GitTreeIdentity",
        "Mapping",
        "RepositoryIdentity",
        "RepositorySnapshotDeclaredPathScope",
        "RepositorySnapshotIdentity",
        "RepositorySnapshotPathBinding",
        "RepositorySnapshotPathBindingCollection",
        "Self",
        "ValidationInfo",
        "ValidatorFunctionWrapHandler",
        "ValueError",
        "any",
        "binding",
        "bound",
        "cast",
        "classmethod",
        "declared",
        "field_validator",
        "frozenset",
        "handler",
        "info",
        "isinstance",
        "key",
        "len",
        "list",
        "model_validator",
        "object",
        "path",
        "self",
        "str",
        "supplied",
        "tuple",
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
        ("info", "mode"),
        ("info", "mode"),
        ("info", "mode"),
        ("self", "git_object"),
        ("info", "mode"),
        ("self", "bindings"),
        ("info", "mode"),
        ("info", "mode"),
        ("info", "mode"),
        ("self", "declared_paths"),
        ("info", "mode"),
        ("info", "mode"),
        ("self", "scope"),
        ("self", "scope"),
        ("self", "collection"),
        ("binding", "path"),
        ("self", "snapshot"),
        ("self", "snapshot"),
        ("binding", "snapshot"),
        ("self", "snapshot"),
        ("self", "bindings"),
        ("self", "declared_paths"),
        ("binding", "path"),
        ("self", "collection"),
        ("self", "scope"),
        ("self", "bindings"),
    ]
