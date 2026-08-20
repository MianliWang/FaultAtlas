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
    RepositorySnapshotPathBinding,
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
    assert snapshot_module.__all__ == [
        "RepositorySnapshotIdentity",
        "RepositorySnapshotRootTreeBinding",
        "RepositorySnapshotPathBinding",
    ]
    assert RepositorySnapshotIdentity.__module__ == "faultatlas.domain.snapshot"
    assert RepositorySnapshotRootTreeBinding.__module__ == "faultatlas.domain.snapshot"
    assert RepositorySnapshotPathBinding.__module__ == "faultatlas.domain.snapshot"


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
        ast.ClassDef,
    ]
    assert not [node for node in tree.body if isinstance(node, ast.Import)]
    imports = [
        (node.module, tuple(alias.name for alias in node.names))
        for node in tree.body
        if isinstance(node, ast.ImportFrom)
    ]
    assert imports == [
        ("typing", ("Annotated", "Self")),
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
    ] == [["model_config"], ["model_config"], ["model_config"]]
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
    calls = {
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    assert calls == {
        "ConfigDict",
        "Field",
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
        "Annotated",
        "BaseModel",
        "ConfigDict",
        "Field",
        "GitBlobIdentity",
        "GitCommitIdentity",
        "GitRepositoryPath",
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
        ("info", "mode"),
        ("info", "mode"),
        ("info", "mode"),
        ("self", "git_object"),
        ("self", "snapshot"),
        ("self", "snapshot"),
    ]
