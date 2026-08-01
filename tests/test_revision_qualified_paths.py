from __future__ import annotations

import ast
import json
from datetime import UTC, datetime
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
    RepositoryAliasObservation,
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
    GitRepositoryPath,
    GitTreeIdentity,
    RevisionQualifiedPath,
    RevisionRole,
    RevisionRoleAssignment,
)
from faultatlas.domain.source import SourceLocator

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
REVISION_SOURCE = REPOSITORY_ROOT / "src/faultatlas/domain/revision.py"

CANONICAL_REPOSITORY_ID = "37489525"
CANONICAL_HEAD = "690a63b9218f72662cd3a67c6c200b758c88ce12"
CANONICAL_PROVIDER = "github"
CANONICAL_ACQUISITION = (
    "reference_corpus/pytest-4412/acquisitions/"
    "run-0001-s04-v1-base-4c9cde74-head-690a63b9/acquisition.json"
)
type _CanonicalPathVector = tuple[
    str,
    str,
    str,
    str,
    str,
    GitHashAlgorithm,
    str,
]

# Only direct head-tree observations are canonical here. Diff-header and
# locator occurrences remain retained-artifact or deterministic-derivation
# evidence and are intentionally excluded from this table.
CANONICAL_PATH_VECTORS: tuple[_CanonicalPathVector, ...] = (
    (
        "LICENSE",
        f"{CANONICAL_ACQUISITION}#/observations/path_resolution/leaves/0",
        "directly_observed",
        CANONICAL_PROVIDER,
        CANONICAL_REPOSITORY_ID,
        GitHashAlgorithm.SHA1,
        CANONICAL_HEAD,
    ),
    (
        "src/_pytest/assertion/rewrite.py",
        f"{CANONICAL_ACQUISITION}#/observations/path_resolution/leaves/1",
        "directly_observed",
        CANONICAL_PROVIDER,
        CANONICAL_REPOSITORY_ID,
        GitHashAlgorithm.SHA1,
        CANONICAL_HEAD,
    ),
    (
        "testing/test_assertrewrite.py",
        f"{CANONICAL_ACQUISITION}#/observations/path_resolution/leaves/2",
        "directly_observed",
        CANONICAL_PROVIDER,
        CANONICAL_REPOSITORY_ID,
        GitHashAlgorithm.SHA1,
        CANONICAL_HEAD,
    ),
    (
        "changelog/4412.bugfix.rst",
        f"{CANONICAL_ACQUISITION}#/observations/path_resolution/leaves/3",
        "directly_observed",
        CANONICAL_PROVIDER,
        CANONICAL_REPOSITORY_ID,
        GitHashAlgorithm.SHA1,
        CANONICAL_HEAD,
    ),
)
EXPECTED_CANONICAL_PATH_POINTERS = {
    "LICENSE": f"{CANONICAL_ACQUISITION}#/observations/path_resolution/leaves/0",
    "src/_pytest/assertion/rewrite.py": (
        f"{CANONICAL_ACQUISITION}#/observations/path_resolution/leaves/1"
    ),
    "testing/test_assertrewrite.py": (
        f"{CANONICAL_ACQUISITION}#/observations/path_resolution/leaves/2"
    ),
    "changelog/4412.bugfix.rst": (
        f"{CANONICAL_ACQUISITION}#/observations/path_resolution/leaves/3"
    ),
}

SYNTHETIC_SHA1 = "1" * 40
SYNTHETIC_SHA1_OTHER = "2" * 40
SYNTHETIC_SHA256 = "3" * 64
SYNTHETIC_NFC_PATH = "tests/fixtures/éxample.txt"
SYNTHETIC_NFD_PATH = "tests/fixtures/e\u0301xample.txt"
SYNTHETIC_LEXICAL_PATH_VECTORS = (
    "src/faultatlas/domain/revision.py",
    "docs/reference cases/overview.md",
    SYNTHETIC_NFC_PATH,
    SYNTHETIC_NFD_PATH,
    "src/Module.py",
    "src/module.py",
    " leading/name",
    "trailing/name ",
    "docs/a  b.md",
)
ASCII_CONTROL_PATHS = tuple(
    f"control-{code}-{chr(code)}-byte" for code in range(32)
) + ("control-127-\x7f-byte",)

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
    repository_id: str = CANONICAL_REPOSITORY_ID,
    *,
    provider: ProviderKey | None = None,
) -> RepositoryIdentity:
    return RepositoryIdentity(
        provider=provider or _provider(),
        provider_repository_id=ProviderRepositoryId.model_validate(repository_id),
    )


def _authority() -> ProviderAuthority:
    return ProviderAuthority(
        provider=_provider(),
        role=AuthorityRole.RETRIEVAL,
        host="api.github.com",
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


def _tree() -> GitTreeIdentity:
    return GitTreeIdentity(
        kind=GitObjectKind.TREE,
        algorithm=GitHashAlgorithm.SHA1,
        full_digest="a" * 40,
    )


def _blob() -> GitBlobIdentity:
    return GitBlobIdentity(
        kind=GitObjectKind.BLOB,
        algorithm=GitHashAlgorithm.SHA1,
        full_digest="b" * 40,
    )


def _path(value: str = "src/faultatlas/domain/revision.py") -> GitRepositoryPath:
    return GitRepositoryPath.model_validate(value)


def _qualified(
    *,
    repository: RepositoryIdentity | None = None,
    revision: GitCommitIdentity | None = None,
    path: GitRepositoryPath | None = None,
) -> RevisionQualifiedPath:
    return RevisionQualifiedPath(
        repository_identity=repository or _repository(),
        revision=revision or _commit(),
        path=path or _path(),
    )


def _python_payload(**overrides: object) -> dict[str, object]:
    return {
        "repository_identity": _repository(),
        "revision": _commit(),
        "path": _path(),
        **overrides,
    }


def _alias_observation() -> RepositoryAliasObservation:
    return RepositoryAliasObservation(
        repository_identity=_repository(),
        observed_alias="pytest-dev/pytest",
        authority=_authority(),
        observed_at=datetime(2026, 8, 1, 12, 0, tzinfo=UTC),
    )


def _ref_observation() -> GitRefObservation:
    return GitRefObservation(
        repository_identity=_repository(),
        namespace=GitRefNamespace.model_validate("heads"),
        name=GitRefName.model_validate("feature/example"),
        state=SourceIdentityLifecycleState.OBSERVED_PRESENT,
        authority=_authority(),
        observed_at=datetime(2026, 8, 1, 12, 0, tzinfo=UTC),
        observed_target=_commit(),
    )


def _role_assignment() -> RevisionRoleAssignment:
    return RevisionRoleAssignment(role=RevisionRole.HEAD, revision=_commit())


def _topology() -> GitCommitParentTopology:
    return GitCommitParentTopology(commit=_commit(), ordered_parents=())


def _legacy_locator() -> SourceLocator:
    return SourceLocator(
        provider="github",
        repository="pytest-dev/pytest",
        object_kind="issue",
        object_id="4412",
    )


def _validate_public_revision_surface(source: str) -> None:
    tree = ast.parse(source)
    exports = next(
        ast.literal_eval(node.value)
        for node in tree.body
        if isinstance(node, ast.Assign)
        and any(
            isinstance(target, ast.Name) and target.id == "__all__"
            for target in node.targets
        )
    )
    public_definitions = {
        node.name
        for node in tree.body
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
        and not node.name.startswith("_")
    }
    public_definitions.update(
        node.name.id
        for node in tree.body
        if isinstance(node, ast.TypeAlias) and not node.name.id.startswith("_")
    )
    assert exports == EXPECTED_EXPORTS
    assert public_definitions == set(EXPECTED_EXPORTS)


def _annotated_class_fields(source: str, class_name: str) -> tuple[str, ...]:
    tree = ast.parse(source)
    class_node = next(
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == class_name
    )
    return tuple(
        node.target.id
        for node in class_node.body
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name)
    )


def _validate_path_field_separation(source: str) -> None:
    for intrinsic_class in (
        "GitCommitIdentity",
        "GitTreeIdentity",
        "GitBlobIdentity",
    ):
        assert _annotated_class_fields(source, intrinsic_class) == ()
    assert _annotated_class_fields(source, "GitRefObservation") == (
        "repository_identity",
        "namespace",
        "name",
        "state",
        "authority",
        "observed_at",
        "observed_target",
    )
    assert _annotated_class_fields(source, "RevisionQualifiedPath") == (
        "repository_identity",
        "revision",
        "path",
    )


def _validate_canonical_path_vectors(
    vectors: tuple[_CanonicalPathVector, ...],
) -> None:
    assert len(vectors) == 4
    assert {vector[0]: vector[1] for vector in vectors} == (
        EXPECTED_CANONICAL_PATH_POINTERS
    )
    assert {vector[2] for vector in vectors} == {"directly_observed"}
    assert {vector[3] for vector in vectors} == {CANONICAL_PROVIDER}
    assert {vector[4] for vector in vectors} == {CANONICAL_REPOSITORY_ID}
    assert {vector[5] for vector in vectors} == {GitHashAlgorithm.SHA1}
    assert {vector[6] for vector in vectors} == {CANONICAL_HEAD}


@pytest.mark.parametrize(
    "value",
    SYNTHETIC_LEXICAL_PATH_VECTORS
    + (
        ".github/workflows/ci.yml",
        "src/a..b",
        "docs/a b.md",
        "punctuation/!#$%&'()+,-.;=@]_{}.txt",
    ),
)
def test_repository_path_accepts_exact_textual_subset(value: str) -> None:
    path = GitRepositoryPath.model_validate(value)
    assert path.root == value
    assert path.model_dump() == value


@pytest.mark.parametrize(
    "value",
    ASCII_CONTROL_PATHS
    + (
        "",
        "/absolute",
        "trailing/",
        "repeated//slash",
        ".",
        "..",
        "src/./module.py",
        "src/../module.py",
        "unicode\x85control",
        "format\u200bcharacter",
        "format\u2060character",
        "format\ufeffcharacter",
        "windows\\separator",
        "C:/absolute/windows",
        "z:/absolute/windows",
        "\\\\server\\share",
        "https://example.com/repository/path",
        "\ud800",
        "\udc00",
    ),
)
def test_repository_path_rejects_unsupported_lexemes(value: str) -> None:
    with pytest.raises(ValidationError):
        GitRepositoryPath.model_validate(value)


@pytest.mark.parametrize(
    "value",
    (
        b"src/module.py",
        Path("src/module.py"),
        1,
        True,
        ["src/module.py"],
        {"root": "src/module.py"},
        None,
    ),
)
def test_repository_path_rejects_non_string_python_input(value: object) -> None:
    with pytest.raises(ValidationError):
        GitRepositoryPath.model_validate(value)


@pytest.mark.parametrize(
    "value",
    (
        "a" * 4096,
        "é" * 2048,
        "目录/" + "界" * 1363,
    ),
)
def test_repository_path_accepts_exact_4096_byte_boundary(value: str) -> None:
    assert len(value.encode("utf-8")) == 4096
    assert GitRepositoryPath.model_validate(value).root == value


@pytest.mark.parametrize(
    "value",
    (
        "a" * 4097,
        "é" * 2048 + "a",
        "目录/" + "界" * 1363 + "a",
    ),
)
def test_repository_path_rejects_over_4096_encoded_bytes(value: str) -> None:
    assert len(value.encode("utf-8")) == 4097
    with pytest.raises(ValidationError):
        GitRepositoryPath.model_validate(value)


def test_case_spaces_punctuation_and_unicode_are_never_normalized() -> None:
    values = (
        "src/Module.py",
        "src/module.py",
        "docs/a b.md",
        " leading/name",
        "trailing/name ",
        "docs/a  b.md",
        SYNTHETIC_NFC_PATH,
        SYNTHETIC_NFD_PATH,
    )
    paths = tuple(GitRepositoryPath.model_validate(value) for value in values)

    assert tuple(path.root for path in paths) == values
    assert paths[0] != paths[1]
    assert paths[3].root.startswith(" ")
    assert paths[4].root.endswith(" ")
    assert "  " in paths[5].root
    assert paths[6] != paths[7]
    assert paths[6].root.encode("utf-8") != paths[7].root.encode("utf-8")


def test_repository_path_semantic_json_round_trip_preserves_exact_lexeme() -> None:
    path = _path(SYNTHETIC_NFD_PATH)
    restored = GitRepositoryPath.model_validate_json(path.model_dump_json())

    assert type(restored) is GitRepositoryPath
    assert restored == path
    assert restored.root == SYNTHETIC_NFD_PATH


def test_repository_path_is_frozen_and_rejects_dynamic_attributes() -> None:
    path = _path()
    with pytest.raises(ValidationError):
        path.root = "other.py"
    with pytest.raises(ValidationError):
        path.extra = "forbidden"  # type: ignore[attr-defined]


@pytest.mark.parametrize(
    (
        "path_lexeme",
        "source_pointer",
        "classification",
        "provider",
        "repository_id",
        "revision_algorithm",
        "revision_digest",
    ),
    CANONICAL_PATH_VECTORS,
)
def test_canonical_head_paths_use_exact_direct_observation_boundary(
    path_lexeme: str,
    source_pointer: str,
    classification: str,
    provider: str,
    repository_id: str,
    revision_algorithm: GitHashAlgorithm,
    revision_digest: str,
) -> None:
    qualified = _qualified(
        repository=_repository(repository_id, provider=_provider(provider)),
        revision=_commit(revision_digest, revision_algorithm),
        path=_path(path_lexeme),
    )

    assert qualified.repository_identity == _repository(
        CANONICAL_REPOSITORY_ID,
        provider=_provider(CANONICAL_PROVIDER),
    )
    assert qualified.revision.algorithm is GitHashAlgorithm.SHA1
    assert qualified.revision.full_digest == CANONICAL_HEAD
    assert qualified.path.root == path_lexeme
    assert source_pointer == EXPECTED_CANONICAL_PATH_POINTERS[path_lexeme]
    assert classification == "directly_observed"


def test_canonical_vectors_make_no_merge_base_sha256_or_blob_claim() -> None:
    _validate_canonical_path_vectors(CANONICAL_PATH_VECTORS)
    path_values = {item[0] for item in CANONICAL_PATH_VECTORS}
    pointers = {item[1] for item in CANONICAL_PATH_VECTORS}

    assert path_values == {
        "LICENSE",
        "src/_pytest/assertion/rewrite.py",
        "testing/test_assertrewrite.py",
        "changelog/4412.bugfix.rst",
    }
    assert len(pointers) == 4
    assert CANONICAL_HEAD != SYNTHETIC_SHA1
    assert len(SYNTHETIC_SHA256) == 64


def test_canonical_path_pointer_swap_is_rejected() -> None:
    first = CANONICAL_PATH_VECTORS[0]
    second = CANONICAL_PATH_VECTORS[1]
    mutated = (
        (first[0], second[1], *first[2:]),
        (second[0], first[1], *second[2:]),
        *CANONICAL_PATH_VECTORS[2:],
    )
    with pytest.raises(AssertionError):
        _validate_canonical_path_vectors(mutated)


def test_valid_qualified_path_composes_exact_typed_components() -> None:
    qualified = _qualified()

    assert tuple(RevisionQualifiedPath.model_fields) == (
        "schema_version",
        "repository_identity",
        "revision",
        "path",
    )
    assert qualified.schema_version == 1
    assert type(qualified.repository_identity) is RepositoryIdentity
    assert type(qualified.revision) is GitCommitIdentity
    assert type(qualified.path) is GitRepositoryPath


def test_synthetic_sha256_commit_is_supported_only_as_typed_coverage() -> None:
    qualified = _qualified(
        revision=_commit(SYNTHETIC_SHA256, GitHashAlgorithm.SHA256),
        path=_path("tests/fixtures/sha256.txt"),
    )

    assert qualified.revision.algorithm is GitHashAlgorithm.SHA256
    assert qualified.revision.full_digest == SYNTHETIC_SHA256
    assert qualified.path.root not in {item[0] for item in CANONICAL_PATH_VECTORS}


def test_equality_includes_repository_revision_and_exact_path() -> None:
    base = _qualified(path=_path("src/Module.py"))
    same = _qualified(path=_path("src/Module.py"))
    other_repository = _qualified(
        repository=_repository("99999999"),
        path=_path("src/Module.py"),
    )
    other_revision = _qualified(
        revision=_commit(SYNTHETIC_SHA1_OTHER),
        path=_path("src/Module.py"),
    )
    other_case = _qualified(path=_path("src/module.py"))
    other_normalization = _qualified(path=_path(SYNTHETIC_NFD_PATH))
    nfc = _qualified(path=_path(SYNTHETIC_NFC_PATH))

    assert base == same
    assert base != other_repository
    assert base != other_revision
    assert base != other_case
    assert nfc != other_normalization


@pytest.mark.parametrize(
    ("field", "value"),
    (
        (
            "repository_identity",
            {
                "provider": "github",
                "provider_repository_id": CANONICAL_REPOSITORY_ID,
            },
        ),
        (
            "revision",
            {
                "kind": "commit",
                "algorithm": "sha1",
                "full_digest": SYNTHETIC_SHA1,
            },
        ),
        ("path", "src/module.py"),
    ),
)
def test_python_construction_requires_typed_nested_values(
    field: str,
    value: object,
) -> None:
    with pytest.raises(ValidationError):
        RevisionQualifiedPath.model_validate(_python_payload(**{field: value}))


def test_semantic_json_round_trip_restores_exact_nested_types() -> None:
    qualified = _qualified(path=_path(SYNTHETIC_NFD_PATH))
    encoded = qualified.model_dump_json()
    restored = RevisionQualifiedPath.model_validate_json(encoded)

    assert restored == qualified
    assert type(restored.repository_identity) is RepositoryIdentity
    assert type(restored.revision) is GitCommitIdentity
    assert type(restored.path) is GitRepositoryPath
    assert restored.path.root == SYNTHETIC_NFD_PATH
    assert restored.model_dump_json() == encoded


@pytest.mark.parametrize("missing", ("repository_identity", "revision", "path"))
def test_qualified_path_requires_every_semantic_component(missing: str) -> None:
    payload = _python_payload()
    del payload[missing]
    with pytest.raises(ValidationError):
        RevisionQualifiedPath.model_validate(payload)


@pytest.mark.parametrize("schema_version", (0, 2, "1", True, 1.0, None))
def test_qualified_path_schema_version_is_exact(schema_version: object) -> None:
    with pytest.raises(ValidationError):
        RevisionQualifiedPath.model_validate(
            _python_payload(schema_version=schema_version)
        )


@pytest.mark.parametrize(
    "field",
    (
        "repository_alias",
        "authority",
        "observed_at",
        "ref",
        "ref_namespace",
        "ref_name",
        "role",
        "parents",
        "ordered_parents",
        "entry_kind",
        "file_mode",
        "exists",
        "blob_identity",
        "tree_identity",
        "object_id",
        "content_digest",
        "media_type",
        "encoding",
        "line",
        "line_start",
        "line_end",
        "column",
        "byte_start",
        "byte_end",
        "old_side",
        "new_side",
        "diff_hunk",
        "span",
        "range",
        "coordinate_index_base",
        "rename_from",
        "copy_from",
        "path_history",
        "blame",
        "provider_provenance",
        "acquisition_provenance",
    ),
)
def test_qualified_path_rejects_deferred_or_cross_record_fields(field: str) -> None:
    with pytest.raises(ValidationError):
        RevisionQualifiedPath.model_validate(_python_payload(**{field: "x"}))


@pytest.mark.parametrize(
    "revision",
    (
        _tree(),
        _blob(),
        _ref_observation(),
        _role_assignment(),
        _topology(),
        SYNTHETIC_SHA1,
    ),
)
def test_revision_boundary_rejects_every_non_commit_value(revision: object) -> None:
    with pytest.raises(ValidationError):
        RevisionQualifiedPath.model_validate(_python_payload(revision=revision))


@pytest.mark.parametrize(
    "repository",
    (
        _alias_observation(),
        _authority(),
        _legacy_locator(),
        _ref_observation(),
        "pytest-dev/pytest",
        "https://github.com/pytest-dev/pytest",
    ),
)
def test_repository_boundary_rejects_every_non_stable_identity(
    repository: object,
) -> None:
    with pytest.raises(ValidationError):
        RevisionQualifiedPath.model_validate(
            _python_payload(repository_identity=repository)
        )


def test_json_rejects_tree_and_blob_revisions() -> None:
    qualified = _qualified()
    payload: dict[str, Any] = json.loads(qualified.model_dump_json())
    for invalid in (_tree(), _blob()):
        payload["revision"] = invalid.model_dump(mode="json")
        with pytest.raises(ValidationError):
            RevisionQualifiedPath.model_validate_json(json.dumps(payload))


def test_constructed_invalid_nested_path_is_revalidated() -> None:
    invalid = GitRepositoryPath.model_construct(root="/absolute")
    with pytest.raises(ValidationError):
        _qualified(path=invalid)


def test_constructed_invalid_nested_repository_is_revalidated() -> None:
    invalid_id = ProviderRepositoryId.model_construct(root="")
    invalid = RepositoryIdentity.model_construct(
        provider=_provider(),
        provider_repository_id=invalid_id,
    )
    with pytest.raises(ValidationError):
        _qualified(repository=invalid)


def test_constructed_invalid_nested_commit_is_revalidated() -> None:
    invalid = GitCommitIdentity.model_construct(
        kind=GitObjectKind.COMMIT,
        algorithm=GitHashAlgorithm.SHA1,
        full_digest="short",
    )
    with pytest.raises(ValidationError):
        _qualified(revision=invalid)


def test_constructed_invalid_outer_model_is_revalidated() -> None:
    invalid = RevisionQualifiedPath.model_construct(
        schema_version=2,
        repository_identity=_repository(),
        revision=_commit(),
        path=_path(),
    )
    with pytest.raises(ValidationError):
        RevisionQualifiedPath.model_validate(invalid)


def test_qualified_path_is_frozen_and_rejects_dynamic_attributes() -> None:
    qualified = _qualified()
    with pytest.raises(ValidationError):
        qualified.path = _path("other.py")
    with pytest.raises(ValidationError):
        qualified.extra = "forbidden"  # type: ignore[attr-defined]


def test_alias_ref_role_topology_and_object_metadata_are_absent() -> None:
    assert tuple(RevisionQualifiedPath.model_fields) == (
        "schema_version",
        "repository_identity",
        "revision",
        "path",
    )
    assert not set(RevisionQualifiedPath.model_fields) & {
        "repository_alias",
        "authority",
        "observed_at",
        "ref",
        "namespace",
        "name",
        "role",
        "parents",
        "ordered_parents",
        "entry_kind",
        "file_mode",
        "exists",
        "blob_identity",
        "tree_identity",
        "content_digest",
        "line",
        "byte_start",
        "diff_hunk",
        "path_history",
    }


def test_existing_identity_role_topology_and_ref_fields_remain_unchanged() -> None:
    assert tuple(GitCommitIdentity.model_fields) == (
        "schema_version",
        "kind",
        "algorithm",
        "full_digest",
    )
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
    _validate_path_field_separation(REVISION_SOURCE.read_text(encoding="utf-8"))


def test_models_have_exact_strict_frozen_configuration() -> None:
    for model in (GitRepositoryPath, RevisionQualifiedPath):
        assert model.model_config.get("frozen") is True
        assert model.model_config.get("strict") is True
        assert model.model_config.get("revalidate_instances") == "always"
        assert model.model_config.get("validate_default") is True
    assert RevisionQualifiedPath.model_config.get("extra") == "forbid"
    assert all(
        field.alias is None
        and field.validation_alias is None
        and field.serialization_alias is None
        for field in RevisionQualifiedPath.model_fields.values()
    )


def test_exports_and_package_boundaries_are_exact() -> None:
    assert revision_module.__all__ == EXPECTED_EXPORTS
    assert len(revision_module.__all__) == len(set(revision_module.__all__)) == 15
    assert faultatlas.__all__ == ["__version__"]
    assert not any(hasattr(faultatlas, name) for name in EXPECTED_EXPORTS)
    assert not any(hasattr(domain_package, name) for name in EXPECTED_EXPORTS)
    _validate_public_revision_surface(REVISION_SOURCE.read_text(encoding="utf-8"))


@pytest.mark.parametrize(
    "mutation",
    ("missing-path", "missing-qualified", "unexpected"),
)
def test_revision_surface_mutations_are_rejected(mutation: str) -> None:
    source = REVISION_SOURCE.read_text(encoding="utf-8")
    if mutation == "missing-path":
        mutated = source.replace('    "GitRepositoryPath",\n', "", 1)
    elif mutation == "missing-qualified":
        mutated = source.replace('    "RevisionQualifiedPath",\n', "", 1)
    else:
        assert mutation == "unexpected"
        mutated = source.replace(
            '    "RevisionQualifiedPath",\n',
            '    "RevisionQualifiedPath",\n    "UnexpectedPathSurface",\n',
            1,
        )
    with pytest.raises(AssertionError):
        _validate_public_revision_surface(mutated)


@pytest.mark.parametrize(
    "symbol",
    ("LineLocator", "PathExistenceObservation", "PathHistory"),
)
def test_deferred_model_mutations_are_rejected(symbol: str) -> None:
    source = REVISION_SOURCE.read_text(encoding="utf-8")
    mutated = source + f"\n\nclass {symbol}:\n    pass\n"
    with pytest.raises(AssertionError):
        _validate_public_revision_surface(mutated)


@pytest.mark.parametrize(
    "class_declaration",
    (
        "class GitCommitIdentity(_GitObjectIdentityBase[Literal[GitObjectKind.COMMIT]]):",
        "class GitRefObservation(_RevisionRecordBase):",
    ),
)
def test_path_field_leakage_mutations_are_rejected(class_declaration: str) -> None:
    source = REVISION_SOURCE.read_text(encoding="utf-8")
    mutated = source.replace(
        class_declaration,
        class_declaration + "\n    path: GitRepositoryPath",
        1,
    )
    with pytest.raises(AssertionError):
        _validate_path_field_separation(mutated)


def test_production_inventory_remains_exactly_eight_sources() -> None:
    production_files = {
        path.relative_to(REPOSITORY_ROOT).as_posix()
        for path in (REPOSITORY_ROOT / "src").rglob("*.py")
    }
    assert production_files == EXPECTED_PRODUCTION_FILES
    assert len(production_files) == 8


def test_no_io_normalization_existence_or_s05_surface() -> None:
    source = REVISION_SOURCE.read_text(encoding="utf-8")
    tree = ast.parse(source)
    forbidden_modules = {
        "git",
        "os",
        "pathlib",
        "socket",
        "subprocess",
        "urllib",
    }
    forbidden_calls = {
        "open",
        "read",
        "read_bytes",
        "read_text",
        "resolve",
        "exists",
        "is_file",
        "is_dir",
        "normpath",
        "normalize",
        "lower",
        "casefold",
        "run",
        "Popen",
        "check_call",
        "check_output",
        "getenv",
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

    public_classes = {
        node.name
        for node in tree.body
        if isinstance(node, ast.ClassDef) and not node.name.startswith("_")
    }
    assert not public_classes & {
        "LineLocator",
        "ByteLocator",
        "DiffHunkLocator",
        "LocatorUnion",
        "PathExistenceObservation",
        "PathEntryKind",
        "PathHistory",
        "PathTransition",
        "EvidenceEnvelope",
    }


def test_path_contract_is_semantic_not_canonical_and_uses_no_io_base() -> None:
    assert issubclass(RevisionQualifiedPath, BaseModel)
    source = REVISION_SOURCE.read_text(encoding="utf-8")
    assert "bounded UTF-8 textual subset" in source
    assert "semantic rather than a canonical wire format" in source
    assert "path existence" in source
