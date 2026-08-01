from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

import faultatlas
import faultatlas.domain as domain_package
import faultatlas.domain.revision as revision_module
from faultatlas.domain.revision import (
    GitBlobIdentity,
    GitCommitIdentity,
    GitCommitParentTopology,
    GitHashAlgorithm,
    GitObjectKind,
    GitRefObservation,
    GitTreeIdentity,
    RevisionRole,
    RevisionRoleAssignment,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
REVISION_SOURCE = REPOSITORY_ROOT / "src/faultatlas/domain/revision.py"

BASE = "4c9cde74ab40027b5761ab9e002af116a4a20df3"
HEAD = "690a63b9218f72662cd3a67c6c200b758c88ce12"
MERGE_FIRST_PARENT = "5fab0ca3127bc895b611cc03bb3af1ebf9a0dbed"
MERGE = "10cdae8e38ec448b7133cf163dca587ad806d262"
SHA1_SYNTHETIC = (
    "1" * 40,
    "2" * 40,
    "3" * 40,
    "4" * 40,
)
SHA256_SYNTHETIC = (
    "1" * 64,
    "2" * 64,
    "3" * 64,
)

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


def _commit(
    digest: str,
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


def _topology_payload(
    commit: object,
    ordered_parents: object,
    **extra: object,
) -> dict[str, object]:
    return {
        "commit": commit,
        "ordered_parents": ordered_parents,
        **extra,
    }


def _validate_revision_public_surface(source: str) -> None:
    tree = ast.parse(source)
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
    assert public_definitions == set(EXPECTED_EXPORTS)


def test_revision_role_vocabulary_is_exact() -> None:
    assert [(item.name, item.value) for item in RevisionRole] == [
        ("BASE", "base"),
        ("HEAD", "head"),
        ("MERGE_FIRST_PARENT", "merge_first_parent"),
        ("MERGE", "merge"),
    ]
    assert RevisionRole.__members__ == {
        "BASE": RevisionRole.BASE,
        "HEAD": RevisionRole.HEAD,
        "MERGE_FIRST_PARENT": RevisionRole.MERGE_FIRST_PARENT,
        "MERGE": RevisionRole.MERGE,
    }
    assert [json.loads(json.dumps(item)) for item in RevisionRole] == [
        "base",
        "head",
        "merge_first_parent",
        "merge",
    ]


@pytest.mark.parametrize(
    "value",
    (
        "parent",
        "first_parent",
        "second_parent",
        "branch",
        "tag",
        "current",
        "previous",
        "target",
        "source",
        "comparison_endpoint",
        "commit",
        "tree",
        "blob",
        "ref",
        "",
    ),
)
def test_unknown_object_kind_and_alias_roles_are_rejected(value: str) -> None:
    with pytest.raises(ValueError):
        RevisionRole(value)


@pytest.mark.parametrize(
    ("role", "digest"),
    (
        (RevisionRole.BASE, BASE),
        (RevisionRole.HEAD, HEAD),
        (RevisionRole.MERGE_FIRST_PARENT, MERGE_FIRST_PARENT),
        (RevisionRole.MERGE, MERGE),
    ),
)
def test_canonical_revision_role_assignments(
    role: RevisionRole,
    digest: str,
) -> None:
    revision = _commit(digest)
    assignment = RevisionRoleAssignment(role=role, revision=revision)
    assert assignment.schema_version == 1
    assert assignment.role is role
    assert type(assignment.revision) is GitCommitIdentity
    assert assignment.revision == revision
    assert assignment.model_dump(mode="json") == {
        "schema_version": 1,
        "role": role.value,
        "revision": revision.model_dump(mode="json"),
    }


def test_role_assignments_are_independent_context_relative_records() -> None:
    base = RevisionRoleAssignment(role=RevisionRole.BASE, revision=_commit(BASE))
    first_parent = RevisionRoleAssignment(
        role=RevisionRole.MERGE_FIRST_PARENT,
        revision=_commit(MERGE_FIRST_PARENT),
    )
    assert base.revision != first_parent.revision

    shared = _commit(SHA1_SYNTHETIC[0])
    assert (
        RevisionRoleAssignment(
            role=RevisionRole.BASE,
            revision=shared,
        ).revision
        == RevisionRoleAssignment(
            role=RevisionRole.HEAD,
            revision=shared,
        ).revision
    )

    assert RevisionRoleAssignment(
        role=RevisionRole.HEAD,
        revision=_commit(SHA1_SYNTHETIC[1]),
    ) != RevisionRoleAssignment(
        role=RevisionRole.HEAD,
        revision=_commit(SHA1_SYNTHETIC[2]),
    )


@pytest.mark.parametrize("schema_version", (0, 2, "1", True, 1.0))
def test_role_assignment_schema_version_is_exact(schema_version: object) -> None:
    with pytest.raises(ValidationError):
        RevisionRoleAssignment.model_validate(
            {
                "schema_version": schema_version,
                "role": RevisionRole.BASE,
                "revision": _commit(BASE),
            }
        )


@pytest.mark.parametrize("role", ("base", b"base", 1))
def test_python_role_input_is_strict(role: object) -> None:
    with pytest.raises(ValidationError):
        RevisionRoleAssignment.model_validate({"role": role, "revision": _commit(BASE)})


@pytest.mark.parametrize("revision", (_tree(), _blob()))
def test_assignment_rejects_tree_and_blob_identities(revision: object) -> None:
    with pytest.raises(ValidationError):
        RevisionRoleAssignment.model_validate(
            {"role": RevisionRole.BASE, "revision": revision}
        )


def test_assignment_requires_a_typed_commit_for_python_input() -> None:
    with pytest.raises(ValidationError):
        RevisionRoleAssignment.model_validate(
            {
                "role": RevisionRole.BASE,
                "revision": _commit(BASE).model_dump(),
            }
        )


@pytest.mark.parametrize(
    "field",
    (
        "repository",
        "case",
        "comparison",
        "timestamp",
        "authority",
        "provenance",
        "ref",
        "path",
        "parents",
        "ordered_parents",
    ),
)
def test_assignment_rejects_extra_context_and_topology_fields(field: str) -> None:
    with pytest.raises(ValidationError):
        RevisionRoleAssignment.model_validate(
            {
                "role": RevisionRole.BASE,
                "revision": _commit(BASE),
                field: "unexpected",
            }
        )


def test_assignment_rejects_mutation_and_dynamic_attributes() -> None:
    assignment = RevisionRoleAssignment(
        role=RevisionRole.BASE,
        revision=_commit(BASE),
    )
    with pytest.raises(ValidationError):
        assignment.role = RevisionRole.HEAD
    with pytest.raises(ValidationError):
        setattr(assignment, "repository", "pytest-dev/pytest")


def test_assignment_revalidates_nested_and_outer_constructed_instances() -> None:
    invalid_revision = GitCommitIdentity.model_construct(
        kind=GitObjectKind.COMMIT,
        algorithm=GitHashAlgorithm.SHA1,
        full_digest="a" * 39,
    )
    with pytest.raises(ValidationError):
        RevisionRoleAssignment.model_validate(
            RevisionRoleAssignment.model_construct(
                role=RevisionRole.BASE,
                revision=invalid_revision,
            )
        )
    with pytest.raises(ValidationError):
        RevisionRoleAssignment.model_validate(
            RevisionRoleAssignment.model_construct(
                role="base",
                revision=_commit(BASE),
            )
        )


def test_assignment_semantic_json_round_trip_restores_exact_types() -> None:
    assignment = RevisionRoleAssignment(
        role=RevisionRole.MERGE,
        revision=_commit(MERGE),
    )
    restored = RevisionRoleAssignment.model_validate_json(assignment.model_dump_json())
    assert restored == assignment
    assert restored.role is RevisionRole.MERGE
    assert type(restored.revision) is GitCommitIdentity


@pytest.mark.parametrize("missing", ("role", "revision"))
def test_assignment_requires_both_semantic_fields(missing: str) -> None:
    payload: dict[str, object] = {
        "role": RevisionRole.BASE,
        "revision": _commit(BASE),
    }
    del payload[missing]
    with pytest.raises(ValidationError):
        RevisionRoleAssignment.model_validate(payload)


@pytest.mark.parametrize(
    ("algorithm", "child_digest", "parent_digests"),
    (
        (GitHashAlgorithm.SHA1, SHA1_SYNTHETIC[0], ()),
        (GitHashAlgorithm.SHA1, SHA1_SYNTHETIC[1], (SHA1_SYNTHETIC[0],)),
        (
            GitHashAlgorithm.SHA1,
            MERGE,
            (MERGE_FIRST_PARENT, HEAD),
        ),
        (
            GitHashAlgorithm.SHA256,
            SHA256_SYNTHETIC[2],
            SHA256_SYNTHETIC[:2],
        ),
        (
            GitHashAlgorithm.SHA1,
            SHA1_SYNTHETIC[3],
            SHA1_SYNTHETIC[:3],
        ),
    ),
)
def test_root_linear_merge_sha256_and_three_parent_topologies(
    algorithm: GitHashAlgorithm,
    child_digest: str,
    parent_digests: tuple[str, ...],
) -> None:
    parents = tuple(_commit(digest, algorithm) for digest in parent_digests)
    topology = GitCommitParentTopology(
        commit=_commit(child_digest, algorithm),
        ordered_parents=parents,
    )
    assert topology.ordered_parents == parents
    assert tuple(parent.full_digest for parent in topology.ordered_parents) == (
        parent_digests
    )


def test_canonical_merge_parent_order_and_distinct_base_are_explicit() -> None:
    first_parent = _commit(MERGE_FIRST_PARENT)
    head = _commit(HEAD)
    topology = GitCommitParentTopology(
        commit=_commit(MERGE),
        ordered_parents=(first_parent, head),
    )
    assert topology.ordered_parents[0] == first_parent
    assert topology.ordered_parents[1] == head
    assert _commit(BASE) != topology.ordered_parents[0]


def test_reversing_parent_order_produces_a_distinct_topology() -> None:
    first_parent = _commit(MERGE_FIRST_PARENT)
    head = _commit(HEAD)
    forward = GitCommitParentTopology(
        commit=_commit(MERGE),
        ordered_parents=(first_parent, head),
    )
    reverse = GitCommitParentTopology(
        commit=_commit(MERGE),
        ordered_parents=(head, first_parent),
    )
    assert forward != reverse
    assert forward.ordered_parents == tuple(reversed(reverse.ordered_parents))


def test_repeated_parent_multiplicity_is_preserved() -> None:
    repeated = _commit(SHA1_SYNTHETIC[0])
    topology = GitCommitParentTopology(
        commit=_commit(SHA1_SYNTHETIC[1]),
        ordered_parents=(repeated, repeated, _commit(SHA1_SYNTHETIC[2])),
    )
    assert len(topology.ordered_parents) == 3
    assert topology.ordered_parents[:2] == (repeated, repeated)
    assert json.loads(topology.model_dump_json())["ordered_parents"][0:2] == [
        repeated.model_dump(mode="json"),
        repeated.model_dump(mode="json"),
    ]


@pytest.mark.parametrize(
    "ordered_parents",
    (
        [_commit(SHA1_SYNTHETIC[0])],
        {SHA1_SYNTHETIC[0]},
        frozenset({SHA1_SYNTHETIC[0]}),
        iter((_commit(SHA1_SYNTHETIC[0]),)),
    ),
    ids=("list", "set", "frozenset", "iterator"),
)
def test_python_parent_container_must_be_a_tuple(ordered_parents: object) -> None:
    with pytest.raises(ValidationError):
        GitCommitParentTopology.model_validate(
            _topology_payload(_commit(SHA1_SYNTHETIC[1]), ordered_parents)
        )


def test_json_array_restores_a_tuple_of_concrete_commits() -> None:
    topology = GitCommitParentTopology(
        commit=_commit(MERGE),
        ordered_parents=(_commit(MERGE_FIRST_PARENT), _commit(HEAD)),
    )
    payload = json.loads(topology.model_dump_json())
    assert isinstance(payload["ordered_parents"], list)
    restored = GitCommitParentTopology.model_validate_json(json.dumps(payload))
    assert restored == topology
    assert isinstance(restored.ordered_parents, tuple)
    assert all(type(parent) is GitCommitIdentity for parent in restored.ordered_parents)


@pytest.mark.parametrize(
    ("child_algorithm", "parent_algorithm"),
    (
        (GitHashAlgorithm.SHA1, GitHashAlgorithm.SHA256),
        (GitHashAlgorithm.SHA256, GitHashAlgorithm.SHA1),
    ),
)
def test_child_parent_algorithm_mismatch_is_rejected(
    child_algorithm: GitHashAlgorithm,
    parent_algorithm: GitHashAlgorithm,
) -> None:
    child_digest = "a" * (40 if child_algorithm is GitHashAlgorithm.SHA1 else 64)
    parent_digest = "b" * (40 if parent_algorithm is GitHashAlgorithm.SHA1 else 64)
    with pytest.raises(ValidationError):
        GitCommitParentTopology(
            commit=_commit(child_digest, child_algorithm),
            ordered_parents=(_commit(parent_digest, parent_algorithm),),
        )


def test_mixed_parent_algorithms_are_rejected() -> None:
    with pytest.raises(ValidationError):
        GitCommitParentTopology(
            commit=_commit(SHA1_SYNTHETIC[2]),
            ordered_parents=(
                _commit(SHA1_SYNTHETIC[0]),
                _commit(SHA256_SYNTHETIC[0], GitHashAlgorithm.SHA256),
            ),
        )


@pytest.mark.parametrize(
    ("position", "identity"),
    (
        ("child", _tree()),
        ("child", _blob()),
        ("parent", _tree()),
        ("parent", _blob()),
    ),
)
def test_tree_and_blob_cannot_be_topology_child_or_parent(
    position: str,
    identity: object,
) -> None:
    child: object = _commit(SHA1_SYNTHETIC[1])
    parents: object = (_commit(SHA1_SYNTHETIC[0]),)
    if position == "child":
        child = identity
    else:
        parents = (identity,)
    with pytest.raises(ValidationError):
        GitCommitParentTopology.model_validate(_topology_payload(child, parents))


@pytest.mark.parametrize("position", ("child", "parent"))
def test_topology_requires_typed_commits_for_python_input(position: str) -> None:
    child: object = _commit(SHA1_SYNTHETIC[1])
    parents: object = (_commit(SHA1_SYNTHETIC[0]),)
    if position == "child":
        child = _commit(SHA1_SYNTHETIC[1]).model_dump()
    else:
        parents = (_commit(SHA1_SYNTHETIC[0]).model_dump(),)
    with pytest.raises(ValidationError):
        GitCommitParentTopology.model_validate(_topology_payload(child, parents))


@pytest.mark.parametrize(
    "field",
    (
        "role",
        "first_parent",
        "is_merge",
        "parent_count",
        "base",
        "head",
        "merge_first_parent",
        "repository",
        "ref",
        "timestamp",
        "path",
    ),
)
def test_topology_rejects_role_context_and_derived_fields(field: str) -> None:
    with pytest.raises(ValidationError):
        GitCommitParentTopology.model_validate(
            _topology_payload(
                _commit(MERGE),
                (_commit(MERGE_FIRST_PARENT), _commit(HEAD)),
                **{field: "unexpected"},
            )
        )


@pytest.mark.parametrize("schema_version", (0, 2, "1", True, 1.0))
def test_topology_schema_version_is_exact(schema_version: object) -> None:
    with pytest.raises(ValidationError):
        GitCommitParentTopology.model_validate(
            {
                "schema_version": schema_version,
                "commit": _commit(SHA1_SYNTHETIC[1]),
                "ordered_parents": (_commit(SHA1_SYNTHETIC[0]),),
            }
        )


def test_topology_rejects_mutation_and_dynamic_attributes() -> None:
    topology = GitCommitParentTopology(
        commit=_commit(SHA1_SYNTHETIC[1]),
        ordered_parents=(_commit(SHA1_SYNTHETIC[0]),),
    )
    first_parent = topology.ordered_parents[0]
    with pytest.raises(ValidationError):
        topology.ordered_parents = ()
    with pytest.raises(ValidationError):
        setattr(topology, "first_parent", first_parent)


@pytest.mark.parametrize("position", ("child", "first-parent", "second-parent"))
def test_topology_revalidates_constructed_invalid_nested_commits(
    position: str,
) -> None:
    valid_child = _commit(SHA1_SYNTHETIC[2])
    valid_parents = (_commit(SHA1_SYNTHETIC[0]), _commit(SHA1_SYNTHETIC[1]))
    invalid = GitCommitIdentity.model_construct(
        kind=GitObjectKind.COMMIT,
        algorithm=GitHashAlgorithm.SHA1,
        full_digest="a" * 39,
    )
    child = invalid if position == "child" else valid_child
    parents = list(valid_parents)
    if position == "first-parent":
        parents[0] = invalid
    elif position == "second-parent":
        parents[1] = invalid
    with pytest.raises(ValidationError):
        GitCommitParentTopology.model_validate(_topology_payload(child, tuple(parents)))


def test_topology_revalidates_constructed_invalid_outer_instance() -> None:
    invalid = GitCommitParentTopology.model_construct(
        commit=_commit(SHA1_SYNTHETIC[1]),
        ordered_parents=[_commit(SHA1_SYNTHETIC[0])],
    )
    with pytest.raises(ValidationError):
        GitCommitParentTopology.model_validate(invalid)


@pytest.mark.parametrize(
    "parent_digests",
    ((), (SHA1_SYNTHETIC[0],), (MERGE_FIRST_PARENT, HEAD)),
    ids=("root", "linear", "merge"),
)
def test_topology_semantic_json_round_trip_is_deterministic(
    parent_digests: tuple[str, ...],
) -> None:
    topology = GitCommitParentTopology(
        commit=_commit(MERGE),
        ordered_parents=tuple(_commit(digest) for digest in parent_digests),
    )
    payload = topology.model_dump_json()
    restored = GitCommitParentTopology.model_validate_json(payload)
    assert restored == topology
    assert restored.model_dump_json() == payload
    assert tuple(type(parent) for parent in restored.ordered_parents) == (
        (GitCommitIdentity,) * len(parent_digests)
    )


@pytest.mark.parametrize("missing", ("commit", "ordered_parents"))
def test_topology_requires_child_and_explicit_parent_sequence(missing: str) -> None:
    payload = _topology_payload(
        _commit(SHA1_SYNTHETIC[1]),
        (_commit(SHA1_SYNTHETIC[0]),),
    )
    del payload[missing]
    with pytest.raises(ValidationError):
        GitCommitParentTopology.model_validate(payload)


def test_new_models_have_exact_fields_and_configuration() -> None:
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
    for model in (RevisionRoleAssignment, GitCommitParentTopology):
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
    assert not {"role", "parents", "ordered_parents"} & set(
        GitCommitIdentity.model_fields
    )
    assert not {"parent", "parents", "ordered_parents"} & set(
        RevisionRoleAssignment.model_fields
    )
    assert not {"role", "first_parent", "is_merge", "parent_count"} & set(
        GitCommitParentTopology.model_fields
    )
    ref_observation_fields = set(GitRefObservation.model_fields)
    assert not {
        "repository_identity",
        "namespace",
        "name",
        "state",
        "authority",
        "observed_at",
        "observed_target",
    } & set(RevisionRoleAssignment.model_fields)
    assert not {
        "repository_identity",
        "namespace",
        "name",
        "state",
        "authority",
        "observed_at",
        "observed_target",
    } & set(GitCommitParentTopology.model_fields)
    assert (
        not {
            "role",
            "revision",
            "commit",
            "ordered_parents",
        }
        & ref_observation_fields
    )


def test_role_and_topology_models_have_no_cross_record_reconciliation() -> None:
    tree = ast.parse(REVISION_SOURCE.read_text(encoding="utf-8"))
    classes = {node.name: node for node in tree.body if isinstance(node, ast.ClassDef)}
    assignment_names = {
        node.id
        for node in ast.walk(classes["RevisionRoleAssignment"])
        if isinstance(node, ast.Name)
    }
    topology_names = {
        node.id
        for node in ast.walk(classes["GitCommitParentTopology"])
        if isinstance(node, ast.Name)
    }
    ref_observation_names = {
        node.id
        for node in ast.walk(classes["GitRefObservation"])
        if isinstance(node, ast.Name)
    }
    assert "GitCommitParentTopology" not in assignment_names
    assert "RevisionRoleAssignment" not in topology_names
    assert "RevisionRole" not in topology_names
    assert "GitRefObservation" not in assignment_names
    assert "GitRefObservation" not in topology_names
    assert "RevisionRoleAssignment" not in ref_observation_names
    assert "GitCommitParentTopology" not in ref_observation_names
    assert "RevisionRole" not in ref_observation_names


def test_exports_package_boundaries_and_production_inventory_are_exact() -> None:
    assert revision_module.__all__ == EXPECTED_EXPORTS
    assert faultatlas.__all__ == ["__version__"]
    assert not any(hasattr(faultatlas, name) for name in EXPECTED_EXPORTS)
    assert not any(hasattr(domain_package, name) for name in EXPECTED_EXPORTS)
    production_files = {
        path.relative_to(REPOSITORY_ROOT).as_posix()
        for path in (REPOSITORY_ROOT / "src").rglob("*.py")
    }
    assert production_files == EXPECTED_PRODUCTION_FILES


def test_revision_module_has_no_later_slice_or_io_surface() -> None:
    source = REVISION_SOURCE.read_text(encoding="utf-8")
    _validate_revision_public_surface(source)
    tree = ast.parse(source)

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


@pytest.mark.parametrize("position", ("child", "parent"))
def test_json_rejects_non_commit_topology_members(position: str) -> None:
    topology = GitCommitParentTopology(
        commit=_commit(MERGE),
        ordered_parents=(_commit(MERGE_FIRST_PARENT), _commit(HEAD)),
    )
    payload: dict[str, Any] = json.loads(topology.model_dump_json())
    if position == "child":
        payload["commit"] = _tree().model_dump(mode="json")
    else:
        payload["ordered_parents"][0] = _tree().model_dump(mode="json")
    with pytest.raises(ValidationError):
        GitCommitParentTopology.model_validate_json(json.dumps(payload))


@pytest.mark.parametrize(
    "symbol",
    ("RevisionQualifiedPath", "GitRefObservationHistory"),
)
def test_later_path_and_history_symbol_mutations_are_rejected(symbol: str) -> None:
    source = REVISION_SOURCE.read_text(encoding="utf-8")
    mutated = source + f"\n\nclass {symbol}:\n    pass\n"
    with pytest.raises(AssertionError):
        _validate_revision_public_surface(mutated)
