from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Any, cast

import pytest
from pydantic import TypeAdapter, ValidationError

import faultatlas
import faultatlas.domain as domain_package
import faultatlas.domain.revision as revision_module
from faultatlas.domain.identity import ProviderGlobalId
from faultatlas.domain.revision import (
    GitBlobIdentity,
    GitCommitIdentity,
    GitHashAlgorithm,
    GitObjectIdentity,
    GitObjectKind,
    GitRevisionIdentity,
    GitTreeIdentity,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
REVISION_SOURCE = REPOSITORY_ROOT / "src/faultatlas/domain/revision.py"

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
]
EXPECTED_FIELDS = ("schema_version", "kind", "algorithm", "full_digest")
type _ObjectIdentityRuntime = GitCommitIdentity | GitTreeIdentity | GitBlobIdentity
OBJECT_ADAPTER = cast(
    TypeAdapter[_ObjectIdentityRuntime],
    TypeAdapter(GitObjectIdentity),
)
REVISION_ADAPTER = cast(
    TypeAdapter[GitCommitIdentity],
    TypeAdapter(GitRevisionIdentity),
)

SHA1_COMMIT = "4c9cde74ab40027b5761ab9e002af116a4a20df3"
SHA1_TREE = "9e5593159e909083009ac9ad72d5d59feb863c44"
SHA1_BLOB = "629df45ac405532c107eb233217bc2ac1ad70c88"
SHA256_COMMIT = "1" * 64
SHA256_TREE = "2" * 64
SHA256_BLOB = "abcdef0123456789" * 4

MODEL_CASES = (
    (GitCommitIdentity, GitObjectKind.COMMIT, SHA1_COMMIT),
    (GitTreeIdentity, GitObjectKind.TREE, SHA1_TREE),
    (GitBlobIdentity, GitObjectKind.BLOB, SHA1_BLOB),
)

CANONICAL_SHA1_VECTORS = (
    (
        "base-commit",
        GitCommitIdentity,
        GitObjectKind.COMMIT,
        "4c9cde74ab40027b5761ab9e002af116a4a20df3",
    ),
    (
        "head-commit",
        GitCommitIdentity,
        GitObjectKind.COMMIT,
        "690a63b9218f72662cd3a67c6c200b758c88ce12",
    ),
    (
        "merge-first-parent-commit",
        GitCommitIdentity,
        GitObjectKind.COMMIT,
        "5fab0ca3127bc895b611cc03bb3af1ebf9a0dbed",
    ),
    (
        "merge-commit",
        GitCommitIdentity,
        GitObjectKind.COMMIT,
        "10cdae8e38ec448b7133cf163dca587ad806d262",
    ),
    (
        "head-tree",
        GitTreeIdentity,
        GitObjectKind.TREE,
        "9e5593159e909083009ac9ad72d5d59feb863c44",
    ),
    (
        "license-blob",
        GitBlobIdentity,
        GitObjectKind.BLOB,
        "629df45ac405532c107eb233217bc2ac1ad70c88",
    ),
    (
        "implementation-blob",
        GitBlobIdentity,
        GitObjectKind.BLOB,
        "7b9aa5006544c160f584f1e8fc3f7771ef6e5e99",
    ),
    (
        "regression-blob",
        GitBlobIdentity,
        GitObjectKind.BLOB,
        "a02433cd62ab19ebb54b42b50c299e59e48de00e",
    ),
    (
        "changelog-blob",
        GitBlobIdentity,
        GitObjectKind.BLOB,
        "7a28b610837873eeff2a16582de6d5a035820552",
    ),
)


def _identity(
    model: type[GitCommitIdentity] | type[GitTreeIdentity] | type[GitBlobIdentity],
    kind: GitObjectKind,
    algorithm: GitHashAlgorithm,
    full_digest: str,
) -> GitCommitIdentity | GitTreeIdentity | GitBlobIdentity:
    return model.model_validate(
        {
            "kind": kind,
            "algorithm": algorithm,
            "full_digest": full_digest,
        }
    )


def test_algorithm_and_kind_vocabularies_are_exact() -> None:
    assert [(item.name, item.value) for item in GitHashAlgorithm] == [
        ("SHA1", "sha1"),
        ("SHA256", "sha256"),
    ]
    assert [(item.name, item.value) for item in GitObjectKind] == [
        ("COMMIT", "commit"),
        ("TREE", "tree"),
        ("BLOB", "blob"),
    ]
    assert GitHashAlgorithm.__members__ == {
        "SHA1": GitHashAlgorithm.SHA1,
        "SHA256": GitHashAlgorithm.SHA256,
    }
    assert GitObjectKind.__members__ == {
        "COMMIT": GitObjectKind.COMMIT,
        "TREE": GitObjectKind.TREE,
        "BLOB": GitObjectKind.BLOB,
    }
    for value in ("SHA1", "SHA256", "sha-1", "sha512", ""):
        with pytest.raises(ValueError):
            GitHashAlgorithm(value)
    for value in ("COMMIT", "tag", "ref", "branch", "file", ""):
        with pytest.raises(ValueError):
            GitObjectKind(value)


@pytest.mark.parametrize(
    ("vector_id", "model", "kind", "full_digest"),
    CANONICAL_SHA1_VECTORS,
    ids=[item[0] for item in CANONICAL_SHA1_VECTORS],
)
def test_canonical_case_sha1_vectors(
    vector_id: str,
    model: type[GitCommitIdentity] | type[GitTreeIdentity] | type[GitBlobIdentity],
    kind: GitObjectKind,
    full_digest: str,
) -> None:
    identity = _identity(model, kind, GitHashAlgorithm.SHA1, full_digest)
    assert vector_id
    assert type(identity) is model
    assert identity.model_dump(mode="json") == {
        "schema_version": 1,
        "kind": kind.value,
        "algorithm": "sha1",
        "full_digest": full_digest,
    }


@pytest.mark.parametrize(
    ("model", "kind", "full_digest"),
    (
        (GitCommitIdentity, GitObjectKind.COMMIT, SHA256_COMMIT),
        (GitTreeIdentity, GitObjectKind.TREE, SHA256_TREE),
        (GitBlobIdentity, GitObjectKind.BLOB, SHA256_BLOB),
    ),
)
def test_synthetic_sha256_vectors(
    model: type[GitCommitIdentity] | type[GitTreeIdentity] | type[GitBlobIdentity],
    kind: GitObjectKind,
    full_digest: str,
) -> None:
    identity = _identity(model, kind, GitHashAlgorithm.SHA256, full_digest)
    assert identity.algorithm is GitHashAlgorithm.SHA256
    assert identity.full_digest == full_digest
    assert identity.model_dump(mode="json") == {
        "schema_version": 1,
        "kind": kind.value,
        "algorithm": "sha256",
        "full_digest": full_digest,
    }


@pytest.mark.parametrize(
    ("algorithm", "full_digest"),
    (
        (GitHashAlgorithm.SHA1, "a" * 39),
        (GitHashAlgorithm.SHA1, "a" * 41),
        (GitHashAlgorithm.SHA256, "a" * 63),
        (GitHashAlgorithm.SHA256, "a" * 65),
        (GitHashAlgorithm.SHA1, "A" * 40),
        (GitHashAlgorithm.SHA1, "g" * 40),
        (GitHashAlgorithm.SHA256, "A" * 64),
        (GitHashAlgorithm.SHA256, "g" * 64),
        (GitHashAlgorithm.SHA1, "é" * 40),
        (GitHashAlgorithm.SHA1, " " + "a" * 39),
        (GitHashAlgorithm.SHA1, "a" * 39 + "\n"),
        (GitHashAlgorithm.SHA1, "0x" + "a" * 38),
        (GitHashAlgorithm.SHA1, "a" * 20 + "-" + "b" * 19),
        (GitHashAlgorithm.SHA1, "0" * 40),
        (GitHashAlgorithm.SHA256, "0" * 64),
        (GitHashAlgorithm.SHA1, SHA256_COMMIT),
        (GitHashAlgorithm.SHA256, SHA1_COMMIT),
    ),
)
def test_invalid_digest_lexemes_are_rejected(
    algorithm: GitHashAlgorithm,
    full_digest: str,
) -> None:
    with pytest.raises(ValidationError):
        GitCommitIdentity(
            kind=GitObjectKind.COMMIT,
            algorithm=algorithm,
            full_digest=full_digest,
        )


@pytest.mark.parametrize(
    "full_digest", (b"a" * 40, 1111111111111111111111111111111111111111)
)
def test_non_string_digests_are_not_coerced(full_digest: object) -> None:
    with pytest.raises(ValidationError):
        GitCommitIdentity.model_validate(
            {
                "kind": GitObjectKind.COMMIT,
                "algorithm": GitHashAlgorithm.SHA1,
                "full_digest": full_digest,
            }
        )


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("algorithm", b"sha1"),
        ("algorithm", 1),
        ("kind", b"commit"),
        ("kind", 1),
    ),
)
def test_non_string_algorithm_and_kind_inputs_are_not_coerced(
    field: str,
    value: object,
) -> None:
    payload: dict[str, object] = {
        "kind": GitObjectKind.COMMIT,
        "algorithm": GitHashAlgorithm.SHA1,
        "full_digest": SHA1_COMMIT,
    }
    payload[field] = value
    with pytest.raises(ValidationError):
        GitCommitIdentity.model_validate(payload)


@pytest.mark.parametrize("model,kind,digest", MODEL_CASES)
def test_models_have_exact_fields_and_strict_frozen_configuration(
    model: type[GitCommitIdentity] | type[GitTreeIdentity] | type[GitBlobIdentity],
    kind: GitObjectKind,
    digest: str,
) -> None:
    assert tuple(model.model_fields) == EXPECTED_FIELDS
    assert model.model_config.get("frozen") is True
    assert model.model_config.get("extra") == "forbid"
    assert model.model_config.get("strict") is True
    assert model.model_config.get("revalidate_instances") == "always"
    assert model.model_config.get("validate_default") is True
    assert all(
        field.alias is None
        and field.validation_alias is None
        and field.serialization_alias is None
        for field in model.model_fields.values()
    )
    identity = _identity(model, kind, GitHashAlgorithm.SHA1, digest)
    with pytest.raises(ValidationError):
        identity.full_digest = "b" * 40
    with pytest.raises(ValidationError):
        setattr(identity, "role", "head")
    with pytest.raises(ValidationError):
        model.model_validate(
            {
                "kind": kind,
                "algorithm": GitHashAlgorithm.SHA1,
                "full_digest": digest,
                "role": "head",
            }
        )


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("role", "head"),
        ("ref", "refs/heads/main"),
        ("repository", "pytest-dev/pytest"),
        ("parents", (SHA1_COMMIT,)),
        ("timestamp", "2018-09-13T00:00:00Z"),
    ),
)
def test_future_slice_metadata_fields_are_rejected(
    field: str,
    value: object,
) -> None:
    payload: dict[str, object] = {
        "kind": GitObjectKind.COMMIT,
        "algorithm": GitHashAlgorithm.SHA1,
        "full_digest": SHA1_COMMIT,
        field: value,
    }
    with pytest.raises(ValidationError):
        GitCommitIdentity.model_validate(payload)


@pytest.mark.parametrize("schema_version", (0, 2, "1", True))
def test_schema_version_is_exact_and_strict(schema_version: object) -> None:
    with pytest.raises(ValidationError):
        GitCommitIdentity.model_validate(
            {
                "schema_version": schema_version,
                "kind": GitObjectKind.COMMIT,
                "algorithm": GitHashAlgorithm.SHA1,
                "full_digest": SHA1_COMMIT,
            }
        )


def test_python_inputs_are_strict_while_json_restores_enums() -> None:
    valid = {
        "kind": GitObjectKind.COMMIT,
        "algorithm": GitHashAlgorithm.SHA1,
        "full_digest": SHA1_COMMIT,
    }
    assert GitCommitIdentity.model_validate(valid).kind is GitObjectKind.COMMIT
    for field, value in (("kind", "commit"), ("algorithm", "sha1")):
        invalid = dict(valid)
        invalid[field] = value
        with pytest.raises(ValidationError):
            GitCommitIdentity.model_validate(invalid)
    restored = GitCommitIdentity.model_validate_json(
        json.dumps(
            {
                "schema_version": 1,
                "kind": "commit",
                "algorithm": "sha1",
                "full_digest": SHA1_COMMIT,
            }
        )
    )
    assert restored.kind is GitObjectKind.COMMIT
    assert restored.algorithm is GitHashAlgorithm.SHA1
    for field, value in (
        ("kind", 1),
        ("algorithm", 1),
        ("algorithm", "SHA1"),
        ("algorithm", "sha512"),
    ):
        invalid_json = restored.model_dump(mode="json")
        invalid_json[field] = value
        with pytest.raises(ValidationError):
            GitCommitIdentity.model_validate_json(json.dumps(invalid_json))


@pytest.mark.parametrize("model,kind,digest", MODEL_CASES)
def test_discriminated_union_semantic_json_restores_exact_type(
    model: type[GitCommitIdentity] | type[GitTreeIdentity] | type[GitBlobIdentity],
    kind: GitObjectKind,
    digest: str,
) -> None:
    identity = _identity(model, kind, GitHashAlgorithm.SHA1, digest)
    payload = identity.model_dump_json()
    restored = OBJECT_ADAPTER.validate_json(payload)
    assert type(restored) is model
    assert restored == identity
    assert json.loads(payload) == identity.model_dump(mode="json")


def test_discriminator_is_explicit_and_rejects_missing_or_unknown_tags() -> None:
    schema = OBJECT_ADAPTER.json_schema()
    assert schema["discriminator"] == {
        "mapping": {
            "blob": "#/$defs/GitBlobIdentity",
            "commit": "#/$defs/GitCommitIdentity",
            "tree": "#/$defs/GitTreeIdentity",
        },
        "propertyName": "kind",
    }
    assert len(schema["oneOf"]) == 3
    base: dict[str, Any] = {
        "schema_version": 1,
        "algorithm": "sha1",
        "full_digest": SHA1_COMMIT,
    }
    with pytest.raises(ValidationError):
        OBJECT_ADAPTER.validate_json(json.dumps(base))
    for tag in ("tag", "COMMIT", ""):
        with pytest.raises(ValidationError):
            OBJECT_ADAPTER.validate_json(json.dumps({**base, "kind": tag}))


def test_same_digest_remains_distinct_across_object_kinds() -> None:
    identities = (
        GitCommitIdentity(
            kind=GitObjectKind.COMMIT,
            algorithm=GitHashAlgorithm.SHA1,
            full_digest=SHA1_COMMIT,
        ),
        GitTreeIdentity(
            kind=GitObjectKind.TREE,
            algorithm=GitHashAlgorithm.SHA1,
            full_digest=SHA1_COMMIT,
        ),
        GitBlobIdentity(
            kind=GitObjectKind.BLOB,
            algorithm=GitHashAlgorithm.SHA1,
            full_digest=SHA1_COMMIT,
        ),
    )
    assert len(set(identities)) == 3
    assert [
        type(OBJECT_ADAPTER.validate_json(item.model_dump_json()))
        for item in identities
    ] == [
        GitCommitIdentity,
        GitTreeIdentity,
        GitBlobIdentity,
    ]


def test_kind_is_required_and_literal_mismatches_are_rejected() -> None:
    with pytest.raises(ValidationError):
        GitCommitIdentity.model_validate(
            {
                "algorithm": GitHashAlgorithm.SHA1,
                "full_digest": SHA1_COMMIT,
            }
        )
    for model, wrong_kind in (
        (GitCommitIdentity, GitObjectKind.TREE),
        (GitTreeIdentity, GitObjectKind.BLOB),
        (GitBlobIdentity, GitObjectKind.COMMIT),
    ):
        with pytest.raises(ValidationError):
            model.model_validate(
                {
                    "kind": wrong_kind,
                    "algorithm": GitHashAlgorithm.SHA1,
                    "full_digest": SHA1_COMMIT,
                }
            )


def test_constructed_invalid_instances_are_revalidated() -> None:
    invalid = GitCommitIdentity.model_construct(
        kind=GitObjectKind.COMMIT,
        algorithm=GitHashAlgorithm.SHA1,
        full_digest="a" * 39,
    )
    with pytest.raises(ValidationError):
        GitCommitIdentity.model_validate(invalid)
    with pytest.raises(ValidationError):
        OBJECT_ADAPTER.validate_python(invalid)


def test_revision_alias_is_commit_identity_without_a_duplicate_model() -> None:
    assert GitRevisionIdentity.__value__ is GitCommitIdentity
    commit = GitCommitIdentity(
        kind=GitObjectKind.COMMIT,
        algorithm=GitHashAlgorithm.SHA1,
        full_digest=SHA1_COMMIT,
    )
    assert type(REVISION_ADAPTER.validate_json(commit.model_dump_json())) is (
        GitCommitIdentity
    )
    for model, kind, digest in MODEL_CASES[1:]:
        identity = _identity(model, kind, GitHashAlgorithm.SHA1, digest)
        with pytest.raises(ValidationError):
            REVISION_ADAPTER.validate_json(identity.model_dump_json())


@pytest.mark.parametrize("legacy_name", ("object_kind", "hash_algorithm", "digest"))
def test_aliases_and_legacy_provider_identifiers_are_not_accepted(
    legacy_name: str,
) -> None:
    payload: dict[str, object] = {
        "kind": GitObjectKind.COMMIT,
        "algorithm": GitHashAlgorithm.SHA1,
        "full_digest": SHA1_COMMIT,
    }
    canonical_name = {
        "object_kind": "kind",
        "hash_algorithm": "algorithm",
        "digest": "full_digest",
    }[legacy_name]
    payload[legacy_name] = payload.pop(canonical_name)
    with pytest.raises(ValidationError):
        GitCommitIdentity.model_validate(payload)

    provider_id = ProviderGlobalId.model_validate(SHA1_COMMIT)
    with pytest.raises(ValidationError):
        GitCommitIdentity.model_validate(
            {
                "kind": GitObjectKind.COMMIT,
                "algorithm": GitHashAlgorithm.SHA1,
                "full_digest": provider_id,
            }
        )


def test_exports_fields_and_no_io_boundary_are_exact() -> None:
    assert revision_module.__all__ == EXPECTED_EXPORTS
    assert faultatlas.__all__ == ["__version__"]
    assert not any(hasattr(faultatlas, name) for name in EXPECTED_EXPORTS)
    assert not any(hasattr(domain_package, name) for name in EXPECTED_EXPORTS)

    forbidden_fields = {
        "repository",
        "repository_identity",
        "role",
        "ref",
        "namespace",
        "name",
        "state",
        "authority",
        "observed_at",
        "observed_target",
        "path",
        "parent",
        "parents",
        "author",
        "committer",
        "commit_time",
        "author_time",
        "tree",
        "message",
        "signature",
        "size",
        "media_type",
        "acquisition_time",
        "observation_authority",
        "source_index",
    }
    for model, _kind, _digest in MODEL_CASES:
        assert not forbidden_fields & set(model.model_fields)

    tree = ast.parse(REVISION_SOURCE.read_text(encoding="utf-8"))
    imported_modules: set[str] = set()
    forbidden_modules = {
        "git",
        "hashlib",
        "os",
        "pathlib",
        "socket",
        "subprocess",
    }
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
            imported_modules.update(alias.name for alias in node.names)
            assert not {alias.name.split(".")[0] for alias in node.names} & (
                forbidden_modules
            )
        elif isinstance(node, ast.ImportFrom):
            assert node.module is not None
            imported_modules.add(node.module)
            assert node.module is None or node.module.split(".")[0] not in (
                forbidden_modules
            )
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                assert node.func.id not in forbidden_calls
            elif isinstance(node.func, ast.Attribute):
                assert node.func.attr not in forbidden_calls
    assert imported_modules == {
        "collections.abc",
        "datetime",
        "enum",
        "faultatlas.domain.identity",
        "pydantic",
        "re",
        "typing",
    }
