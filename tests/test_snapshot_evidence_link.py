from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest
from pydantic import BaseModel, ConfigDict, ValidationError

import faultatlas.domain.snapshot_evidence_link as link_module
from faultatlas.domain.evidence import (
    ArtifactByteLength,
    ArtifactSha256Digest,
    DurableEvidenceRecordReference,
    EvidenceCanonicalization,
    EvidenceRecordFormat,
    EvidenceVersion,
)
from faultatlas.domain.identity import (
    ProviderKey,
    ProviderRepositoryId,
    RepositoryIdentity,
)
from faultatlas.domain.revision import (
    GitBlobIdentity,
    GitCommitIdentity,
    GitHashAlgorithm,
    GitObjectKind,
    GitRepositoryPath,
    GitTreeIdentity,
)
from faultatlas.domain.snapshot import (
    RepositorySnapshotDeclaredPathScope,
    RepositorySnapshotDeclaredPathScopeCoverage,
    RepositorySnapshotIdentity,
    RepositorySnapshotPathBinding,
    RepositorySnapshotPathBindingCollection,
    RepositorySnapshotRootTreeBinding,
)
from faultatlas.domain.snapshot_evidence_link import RepositorySnapshotFactEvidenceLink

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
LINK_SOURCE = REPOSITORY_ROOT / "src/faultatlas/domain/snapshot_evidence_link.py"
SNAPSHOT_SOURCE = REPOSITORY_ROOT / "src/faultatlas/domain/snapshot.py"
EVIDENCE_SOURCE = REPOSITORY_ROOT / "src/faultatlas/domain/evidence.py"

CANONICAL_REPOSITORY_ID = "37489525"
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

CANONICAL_RECORD_FORMAT = "faultatlas-acquisition"
CANONICAL_RECORD_VERSION = "1"
CANONICAL_RECORD_CANONICALIZATION = "json-sort-keys-compact-utf8-lf-v1"
CANONICAL_RECORD_SHA256 = (
    "1c29093bf1537e9b824a18df1848b71a8da014f544bc9f385707eb0e000a1318"
)
CANONICAL_RECORD_LENGTH = 61_283
CANONICAL_CORRECTION_FORMAT = "faultatlas-pytest-4412-acquisition-closure-addendum"
CANONICAL_CORRECTION_SHA256 = (
    "44491ee512d2c2022110b83967fb6fa86d13045bc8404ea490d7a08b7aef24a2"
)
CANONICAL_CORRECTION_LENGTH = 60_832

FORBIDDEN_LINK_IDENTIFIERS = (
    "artifact",
    "authoritative",
    "byte_span",
    "confidence",
    "corroborated",
    "correct",
    "derived",
    "envelope",
    "json_pointer",
    "locator",
    "pointer",
    "proven",
    "request_id",
    "review",
    "strength",
    "status",
    "support_role",
    "verified",
)


def _repository(repository_id: str = CANONICAL_REPOSITORY_ID) -> RepositoryIdentity:
    return RepositoryIdentity(
        provider=ProviderKey.model_validate("github"),
        provider_repository_id=ProviderRepositoryId.model_validate(repository_id),
    )


def _commit(
    digest: str = CANONICAL_REVISION,
    algorithm: GitHashAlgorithm = GitHashAlgorithm.SHA1,
) -> GitCommitIdentity:
    return GitCommitIdentity(
        kind=GitObjectKind.COMMIT,
        algorithm=algorithm,
        full_digest=digest,
    )


def _tree(
    digest: str = CANONICAL_ROOT_TREE,
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


def _path(value: str) -> GitRepositoryPath:
    return GitRepositoryPath.model_validate(value)


def _snapshot(
    digest: str = CANONICAL_REVISION,
    algorithm: GitHashAlgorithm = GitHashAlgorithm.SHA1,
    *,
    repository_id: str = CANONICAL_REPOSITORY_ID,
) -> RepositorySnapshotIdentity:
    return RepositorySnapshotIdentity(
        repository=_repository(repository_id),
        revision=_commit(digest, algorithm),
    )


def _root_tree_fact(
    snapshot: RepositorySnapshotIdentity | None = None,
    root_tree: GitTreeIdentity | None = None,
) -> RepositorySnapshotRootTreeBinding:
    return RepositorySnapshotRootTreeBinding(
        snapshot=snapshot if snapshot is not None else _snapshot(),
        root_tree=root_tree if root_tree is not None else _tree(),
    )


def _path_fact(
    path: str,
    digest: str,
    kind: GitObjectKind = GitObjectKind.BLOB,
    *,
    snapshot: RepositorySnapshotIdentity | None = None,
) -> RepositorySnapshotPathBinding:
    return RepositorySnapshotPathBinding(
        snapshot=snapshot if snapshot is not None else _snapshot(),
        path=_path(path),
        git_object=_blob(digest) if kind is GitObjectKind.BLOB else _tree(digest),
    )


def _canonical_path_facts() -> tuple[RepositorySnapshotPathBinding, ...]:
    snapshot = _snapshot()
    return tuple(
        _path_fact(path, digest, GitObjectKind.BLOB, snapshot=snapshot)
        for path, digest in CANONICAL_BLOB_PATH_BINDINGS
    ) + tuple(
        _path_fact(path, digest, GitObjectKind.TREE, snapshot=snapshot)
        for path, digest in CANONICAL_TREE_PATH_BINDINGS
    )


def _record(
    *,
    format_name: str = CANONICAL_RECORD_FORMAT,
    format_version: str = CANONICAL_RECORD_VERSION,
    canonicalization: str = CANONICAL_RECORD_CANONICALIZATION,
    digest: str = CANONICAL_RECORD_SHA256,
    byte_length: int = CANONICAL_RECORD_LENGTH,
) -> DurableEvidenceRecordReference:
    return DurableEvidenceRecordReference(
        format_name=EvidenceRecordFormat.model_validate(format_name),
        format_version=EvidenceVersion.model_validate(format_version),
        canonicalization=EvidenceCanonicalization.model_validate(canonicalization),
        sha256=ArtifactSha256Digest.model_validate(digest),
        byte_length=ArtifactByteLength.model_validate(byte_length),
    )


def _correction_record() -> DurableEvidenceRecordReference:
    return _record(
        format_name=CANONICAL_CORRECTION_FORMAT,
        digest=CANONICAL_CORRECTION_SHA256,
        byte_length=CANONICAL_CORRECTION_LENGTH,
    )


def _synthetic_record(index: int = 1) -> DurableEvidenceRecordReference:
    return _record(
        format_name="faultatlas-synthetic-record",
        canonicalization="synthetic-json-v1",
        digest=f"{index + 1000:064x}",
        byte_length=index,
    )


def _link(
    fact: RepositorySnapshotRootTreeBinding | RepositorySnapshotPathBinding,
    evidence_record: DurableEvidenceRecordReference | None = None,
) -> RepositorySnapshotFactEvidenceLink:
    return RepositorySnapshotFactEvidenceLink(
        fact=fact,
        evidence_record=evidence_record if evidence_record is not None else _record(),
    )


# --- canonical associations ------------------------------------------------


def test_canonical_root_tree_fact_associates_with_the_acquisition_record() -> None:
    fact = _root_tree_fact()
    record = _record()

    associated = _link(fact, record)

    assert associated.fact == fact
    assert associated.evidence_record == record
    assert associated.fact.snapshot.revision.full_digest == CANONICAL_REVISION
    assert isinstance(associated.fact, RepositorySnapshotRootTreeBinding)
    assert associated.fact.root_tree.full_digest == CANONICAL_ROOT_TREE
    assert associated.evidence_record.sha256.root == CANONICAL_RECORD_SHA256
    assert associated.evidence_record.byte_length.root == CANONICAL_RECORD_LENGTH


def test_all_nine_canonical_path_facts_associate_with_the_same_record() -> None:
    record = _record()
    facts = _canonical_path_facts()

    associations = tuple(_link(fact, record) for fact in facts)

    assert len(associations) == 9
    assert tuple(
        association.fact.path.root
        for association in associations
        if isinstance(association.fact, RepositorySnapshotPathBinding)
    ) == (
        "LICENSE",
        "src/_pytest/assertion/rewrite.py",
        "testing/test_assertrewrite.py",
        "changelog/4412.bugfix.rst",
        "src",
        "src/_pytest",
        "src/_pytest/assertion",
        "testing",
        "changelog",
    )
    assert all(association.evidence_record == record for association in associations)
    assert len(set(associations)) == 9


def test_the_canonical_root_and_nine_path_links_are_ten_distinct_values() -> None:
    record = _record()
    associations = (
        _link(_root_tree_fact(), record),
        *(_link(fact, record) for fact in _canonical_path_facts()),
    )

    assert len(associations) == 10
    assert len(set(associations)) == 10


# --- synthetic associations ------------------------------------------------


def test_sha256_root_tree_fact_associates_with_a_synthetic_record() -> None:
    fact = _root_tree_fact(
        snapshot=_snapshot("1" * 64, GitHashAlgorithm.SHA256),
        root_tree=_tree("2" * 64, GitHashAlgorithm.SHA256),
    )
    record = _synthetic_record(7)

    associated = _link(fact, record)

    assert associated.fact == fact
    assert associated.evidence_record == record
    assert associated.fact.snapshot.revision.algorithm is GitHashAlgorithm.SHA256


def test_sha256_path_binding_fact_associates_with_a_synthetic_record() -> None:
    snapshot = _snapshot("1" * 64, GitHashAlgorithm.SHA256)
    fact = RepositorySnapshotPathBinding(
        snapshot=snapshot,
        path=_path("LICENSE"),
        git_object=_blob("3" * 64, GitHashAlgorithm.SHA256),
    )
    record = _synthetic_record(11)

    associated = _link(fact, record)

    assert associated.fact == fact
    assert associated.evidence_record == record
    assert isinstance(associated.fact, RepositorySnapshotPathBinding)
    assert associated.fact.git_object.algorithm is GitHashAlgorithm.SHA256


# --- one record per link ---------------------------------------------------


def test_one_fact_with_two_records_yields_two_distinct_links() -> None:
    fact = _root_tree_fact()

    acquisition = _link(fact, _record())
    correction = _link(fact, _correction_record())

    assert acquisition != correction
    assert acquisition.fact == correction.fact
    assert acquisition.evidence_record != correction.evidence_record


def test_one_record_with_two_facts_yields_two_distinct_links() -> None:
    record = _record()
    facts = _canonical_path_facts()

    first = _link(facts[0], record)
    second = _link(facts[1], record)

    assert first != second
    assert first.evidence_record == second.evidence_record


def test_repeating_one_fact_and_record_yields_equal_independent_values() -> None:
    fact = _root_tree_fact()

    assert _link(fact, _record()) == _link(fact, _record())


# --- semantic JSON ---------------------------------------------------------


def test_root_tree_link_semantic_json_round_trip_preserves_exact_value() -> None:
    original = _link(_root_tree_fact())

    restored = RepositorySnapshotFactEvidenceLink.model_validate_json(
        original.model_dump_json()
    )

    assert restored == original
    assert isinstance(restored.fact, RepositorySnapshotRootTreeBinding)
    assert restored.fact == original.fact
    assert restored.evidence_record == original.evidence_record


def test_path_binding_link_semantic_json_round_trip_preserves_exact_value() -> None:
    for fact in _canonical_path_facts():
        original = _link(fact)

        restored = RepositorySnapshotFactEvidenceLink.model_validate_json(
            original.model_dump_json()
        )

        assert restored == original
        assert isinstance(restored.fact, RepositorySnapshotPathBinding)
        assert restored.fact.path == fact.path
        assert restored.fact.git_object == fact.git_object


def test_link_json_payload_carries_exactly_the_two_semantic_keys() -> None:
    payload = json.loads(_link(_root_tree_fact()).model_dump_json())

    assert set(payload) == {"fact", "evidence_record"}
    assert set(payload["fact"]) == {"snapshot", "root_tree"}
    assert set(payload["evidence_record"]) == {
        "schema_version",
        "format_name",
        "format_version",
        "canonicalization",
        "sha256",
        "byte_length",
    }


# --- immutability and revalidation -----------------------------------------


def test_link_is_frozen() -> None:
    associated = _link(_root_tree_fact())

    with pytest.raises(ValidationError):
        associated.evidence_record = _correction_record()


def test_link_revalidates_a_nested_fact() -> None:
    invalid = RepositorySnapshotRootTreeBinding.model_construct(
        snapshot=_snapshot(),
        root_tree=GitTreeIdentity.model_construct(
            kind=GitObjectKind.TREE,
            algorithm=GitHashAlgorithm.SHA1,
            full_digest="not-a-digest",
        ),
    )

    with pytest.raises(ValidationError):
        RepositorySnapshotFactEvidenceLink(fact=invalid, evidence_record=_record())


def test_link_revalidates_a_nested_evidence_record() -> None:
    valid = _record()
    invalid = DurableEvidenceRecordReference.model_construct(
        schema_version=1,
        format_name=valid.format_name,
        format_version=valid.format_version,
        canonicalization=valid.canonicalization,
        sha256=ArtifactSha256Digest.model_construct(root="not-a-digest"),
        byte_length=valid.byte_length,
    )

    with pytest.raises(ValidationError):
        RepositorySnapshotFactEvidenceLink(
            fact=_root_tree_fact(), evidence_record=invalid
        )


def test_constructed_link_is_revalidated() -> None:
    invalid = RepositorySnapshotFactEvidenceLink.model_construct(
        fact=RepositorySnapshotRootTreeBinding.model_construct(
            snapshot=_snapshot(),
            root_tree=GitTreeIdentity.model_construct(
                kind=GitObjectKind.TREE,
                algorithm=GitHashAlgorithm.SHA1,
                full_digest="not-a-digest",
            ),
        ),
        evidence_record=_record(),
    )

    with pytest.raises(ValidationError):
        RepositorySnapshotFactEvidenceLink.model_validate(invalid)


# --- required, extra, and untyped inputs -----------------------------------


@pytest.mark.parametrize("missing", ("fact", "evidence_record"))
def test_link_required_fields_cannot_be_omitted(missing: str) -> None:
    payload: dict[str, object] = {
        "fact": _root_tree_fact(),
        "evidence_record": _record(),
    }
    del payload[missing]

    with pytest.raises(ValidationError):
        RepositorySnapshotFactEvidenceLink.model_validate(payload)


def test_link_extra_fields_fail_closed() -> None:
    with pytest.raises(ValidationError):
        RepositorySnapshotFactEvidenceLink.model_validate(
            {
                "fact": _root_tree_fact(),
                "evidence_record": _record(),
                "support_role": "observed_relation",
            }
        )


@pytest.mark.parametrize(
    "value",
    (
        None,
        "LICENSE",
        42,
        (),
        {"snapshot": None, "root_tree": None},
    ),
)
def test_link_rejects_untyped_python_facts(value: object) -> None:
    with pytest.raises(ValidationError, match="in Python input"):
        RepositorySnapshotFactEvidenceLink.model_validate(
            {"fact": value, "evidence_record": _record()}
        )


@pytest.mark.parametrize(
    "value",
    (
        None,
        CANONICAL_RECORD_SHA256,
        61_283,
        (),
        {"format_name": None},
    ),
)
def test_link_rejects_untyped_python_evidence_records(value: object) -> None:
    with pytest.raises(ValidationError, match="in Python input"):
        RepositorySnapshotFactEvidenceLink.model_validate(
            {"fact": _root_tree_fact(), "evidence_record": value}
        )


def test_link_python_construction_rejects_a_dumped_fact_mapping() -> None:
    with pytest.raises(ValidationError, match="in Python input"):
        RepositorySnapshotFactEvidenceLink.model_validate(
            {
                "fact": _root_tree_fact().model_dump(mode="python"),
                "evidence_record": _record(),
            }
        )


def test_link_rejects_swapped_members() -> None:
    with pytest.raises(ValidationError, match="in Python input"):
        RepositorySnapshotFactEvidenceLink.model_validate(
            {"fact": _record(), "evidence_record": _root_tree_fact()}
        )


def test_link_rejects_mutation_of_a_published_value() -> None:
    associated = _link(_root_tree_fact())

    with pytest.raises(ValidationError):
        associated.fact = _canonical_path_facts()[0]


# --- non-target snapshot values --------------------------------------------


def _collection() -> RepositorySnapshotPathBindingCollection:
    return RepositorySnapshotPathBindingCollection(
        snapshot=_snapshot(),
        bindings=_canonical_path_facts(),
    )


def _scope() -> RepositorySnapshotDeclaredPathScope:
    return RepositorySnapshotDeclaredPathScope(
        snapshot=_snapshot(),
        declared_paths=tuple(_path(path) for path, _ in CANONICAL_BLOB_PATH_BINDINGS),
    )


def _coverage() -> RepositorySnapshotDeclaredPathScopeCoverage:
    return RepositorySnapshotDeclaredPathScopeCoverage(
        scope=_scope(),
        collection=_collection(),
    )


def _non_target_facts() -> dict[str, BaseModel]:
    return {
        "s01-identity": _snapshot(),
        "s04-collection": _collection(),
        "s05-declared-scope": _scope(),
        "s06-coverage": _coverage(),
    }


@pytest.mark.parametrize(
    "name",
    ("s01-identity", "s04-collection", "s05-declared-scope", "s06-coverage"),
)
def test_link_rejects_non_binding_snapshot_values_as_fact(name: str) -> None:
    value = _non_target_facts()[name]

    with pytest.raises(ValidationError, match="in Python input"):
        RepositorySnapshotFactEvidenceLink.model_validate(
            {"fact": value, "evidence_record": _record()}
        )


@pytest.mark.parametrize(
    "name",
    ("s01-identity", "s04-collection", "s05-declared-scope", "s06-coverage"),
)
def test_link_rejects_non_binding_snapshot_json_mappings_as_fact(name: str) -> None:
    value = _non_target_facts()[name]
    payload = json.dumps(
        {
            "fact": json.loads(value.model_dump_json()),
            "evidence_record": json.loads(_record().model_dump_json()),
        }
    )

    with pytest.raises(ValidationError):
        RepositorySnapshotFactEvidenceLink.model_validate_json(payload)


def test_collection_children_do_not_become_a_collection_level_association() -> None:
    collection = _collection()
    record = _record()

    child_links = tuple(_link(binding, record) for binding in collection.bindings)

    assert len(child_links) == len(collection.bindings)
    with pytest.raises(ValidationError, match="in Python input"):
        RepositorySnapshotFactEvidenceLink.model_validate(
            {"fact": collection, "evidence_record": record}
        )


# --- malformed children ----------------------------------------------------


@pytest.mark.parametrize(
    "payload",
    (
        {"snapshot": None, "root_tree": None},
        {"snapshot": {}, "root_tree": {}},
        {"root_tree": {"kind": "tree", "algorithm": "sha1", "full_digest": "0"}},
    ),
)
def test_link_rejects_malformed_root_tree_binding_json(
    payload: dict[str, object],
) -> None:
    document = json.dumps(
        {
            "fact": payload,
            "evidence_record": json.loads(_record().model_dump_json()),
        }
    )

    with pytest.raises(ValidationError):
        RepositorySnapshotFactEvidenceLink.model_validate_json(document)


@pytest.mark.parametrize(
    "payload",
    (
        {"snapshot": None, "path": "LICENSE", "git_object": None},
        {"path": "LICENSE", "git_object": {"kind": "blob"}},
        {"snapshot": {}, "path": "", "git_object": {}},
    ),
)
def test_link_rejects_malformed_path_binding_json(
    payload: dict[str, object],
) -> None:
    document = json.dumps(
        {
            "fact": payload,
            "evidence_record": json.loads(_record().model_dump_json()),
        }
    )

    with pytest.raises(ValidationError):
        RepositorySnapshotFactEvidenceLink.model_validate_json(document)


@pytest.mark.parametrize(
    "payload",
    (
        {},
        {"format_name": CANONICAL_RECORD_FORMAT},
        {
            "schema_version": 1,
            "format_name": CANONICAL_RECORD_FORMAT,
            "format_version": CANONICAL_RECORD_VERSION,
            "canonicalization": CANONICAL_RECORD_CANONICALIZATION,
            "sha256": "0" * 64,
            "byte_length": CANONICAL_RECORD_LENGTH,
        },
    ),
)
def test_link_rejects_malformed_evidence_record_json(
    payload: dict[str, object],
) -> None:
    document = json.dumps(
        {
            "fact": json.loads(_root_tree_fact().model_dump_json()),
            "evidence_record": payload,
        }
    )

    with pytest.raises(ValidationError):
        RepositorySnapshotFactEvidenceLink.model_validate_json(document)


@pytest.mark.parametrize(
    "fact",
    (
        {},
        [],
        "LICENSE",
        0,
        None,
    ),
)
def test_link_rejects_ambiguous_and_malformed_json_facts(fact: object) -> None:
    document = json.dumps(
        {
            "fact": fact,
            "evidence_record": json.loads(_record().model_dump_json()),
        }
    )

    with pytest.raises(ValidationError):
        RepositorySnapshotFactEvidenceLink.model_validate_json(document)


def test_link_rejects_a_hybrid_json_fact_that_matches_neither_branch() -> None:
    hybrid = json.loads(_root_tree_fact().model_dump_json())
    hybrid["path"] = "LICENSE"
    document = json.dumps(
        {
            "fact": hybrid,
            "evidence_record": json.loads(_record().model_dump_json()),
        }
    )

    with pytest.raises(ValidationError):
        RepositorySnapshotFactEvidenceLink.model_validate_json(document)


# --- foreign and attribute-backed children ---------------------------------


class _AttributeBackedRootTreeBinding:
    def __init__(self, binding: RepositorySnapshotRootTreeBinding) -> None:
        self.snapshot = binding.snapshot
        self.root_tree = binding.root_tree


class _AttributeBackedRecord:
    def __init__(self, record: DurableEvidenceRecordReference) -> None:
        self.schema_version = record.schema_version
        self.format_name = record.format_name
        self.format_version = record.format_version
        self.canonicalization = record.canonicalization
        self.sha256 = record.sha256
        self.byte_length = record.byte_length


class _ForeignRootTreeBinding(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    snapshot: object
    root_tree: object


class _ForeignRecord(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    schema_version: object
    format_name: object
    format_version: object
    canonicalization: object
    sha256: object
    byte_length: object


def test_link_rejects_attribute_backed_children_under_from_attributes() -> None:
    fact = _root_tree_fact()
    record = _record()

    with pytest.raises(ValidationError, match="in Python input"):
        RepositorySnapshotFactEvidenceLink.model_validate(
            {
                "fact": _AttributeBackedRootTreeBinding(fact),
                "evidence_record": record,
            },
            from_attributes=True,
        )
    with pytest.raises(ValidationError, match="in Python input"):
        RepositorySnapshotFactEvidenceLink.model_validate(
            {"fact": fact, "evidence_record": _AttributeBackedRecord(record)},
            from_attributes=True,
        )


def test_link_rejects_foreign_model_children_under_from_attributes() -> None:
    fact = _root_tree_fact()
    record = _record()

    with pytest.raises(ValidationError, match="in Python input"):
        RepositorySnapshotFactEvidenceLink.model_validate(
            {
                "fact": _ForeignRootTreeBinding(
                    snapshot=fact.snapshot, root_tree=fact.root_tree
                ),
                "evidence_record": record,
            },
            from_attributes=True,
        )
    with pytest.raises(ValidationError, match="in Python input"):
        RepositorySnapshotFactEvidenceLink.model_validate(
            {
                "fact": fact,
                "evidence_record": _ForeignRecord(
                    schema_version=record.schema_version,
                    format_name=record.format_name,
                    format_version=record.format_version,
                    canonicalization=record.canonicalization,
                    sha256=record.sha256,
                    byte_length=record.byte_length,
                ),
            },
            from_attributes=True,
        )


def test_link_rejects_swapped_members_under_from_attributes() -> None:
    with pytest.raises(ValidationError, match="in Python input"):
        RepositorySnapshotFactEvidenceLink.model_validate(
            {"fact": _record(), "evidence_record": _root_tree_fact()},
            from_attributes=True,
        )


def test_link_preserves_published_subclass_acceptance() -> None:
    class _SubclassedRootTreeBinding(RepositorySnapshotRootTreeBinding):
        pass

    fact = _SubclassedRootTreeBinding(snapshot=_snapshot(), root_tree=_tree())

    associated = _link(fact)

    assert associated.fact == _root_tree_fact()
    assert type(associated.fact) is RepositorySnapshotRootTreeBinding


# --- strength and locator boundary -----------------------------------------


@pytest.mark.parametrize("field", FORBIDDEN_LINK_IDENTIFIERS)
def test_link_has_no_strength_locator_or_review_field(field: str) -> None:
    assert field not in RepositorySnapshotFactEvidenceLink.model_fields
    assert not hasattr(RepositorySnapshotFactEvidenceLink, field)
    assert not hasattr(link_module, field)
    with pytest.raises(ValidationError):
        RepositorySnapshotFactEvidenceLink.model_validate(
            {
                "fact": _root_tree_fact(),
                "evidence_record": _record(),
                field: "supplied",
            }
        )


def test_no_forbidden_identifier_appears_in_the_bridge_module_surface() -> None:
    tree = ast.parse(LINK_SOURCE.read_text(encoding="utf-8"))
    identifiers = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}
    identifiers.update(
        node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute)
    )
    identifiers.update(
        node.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
    )
    identifiers.update(node.arg for node in ast.walk(tree) if isinstance(node, ast.arg))
    identifiers.update(
        node.target.id
        for node in ast.walk(tree)
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name)
    )
    identifiers.update(
        alias.asname or alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
        for alias in node.names
    )

    assert not identifiers & set(FORBIDDEN_LINK_IDENTIFIERS)
    assert not [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant)
        and isinstance(node.value, str)
        and node.value in set(FORBIDDEN_LINK_IDENTIFIERS)
    ]


def test_link_makes_no_support_verification_or_completeness_claim() -> None:
    associated = _link(_root_tree_fact())

    assert tuple(RepositorySnapshotFactEvidenceLink.model_fields) == (
        "fact",
        "evidence_record",
    )
    assert set(json.loads(associated.model_dump_json())) == {
        "fact",
        "evidence_record",
    }
    for absent in (
        "absent",
        "complete",
        "completeness",
        "corroborates",
        "member",
        "membership",
        "missing",
        "not_found",
        "omitted",
        "supports",
        "unavailable",
        "unknown",
        "verifies",
    ):
        assert absent not in RepositorySnapshotFactEvidenceLink.model_fields
        assert not hasattr(RepositorySnapshotFactEvidenceLink, absent)


# --- module surface --------------------------------------------------------


def test_model_and_module_surfaces_are_exact_and_local() -> None:
    assert tuple(RepositorySnapshotFactEvidenceLink.model_fields) == (
        "fact",
        "evidence_record",
    )
    assert RepositorySnapshotFactEvidenceLink.model_fields["fact"].annotation == (
        RepositorySnapshotRootTreeBinding | RepositorySnapshotPathBinding
    )
    assert RepositorySnapshotFactEvidenceLink.model_fields["fact"].discriminator is None
    assert RepositorySnapshotFactEvidenceLink.model_fields["fact"].metadata == []
    assert RepositorySnapshotFactEvidenceLink.model_fields[
        "evidence_record"
    ].annotation is (DurableEvidenceRecordReference)
    assert (
        RepositorySnapshotFactEvidenceLink.model_fields["evidence_record"].metadata
        == []
    )
    assert RepositorySnapshotFactEvidenceLink.model_config == {
        "frozen": True,
        "extra": "forbid",
        "strict": True,
        "revalidate_instances": "always",
        "validate_default": True,
    }
    assert link_module.__all__ == ["RepositorySnapshotFactEvidenceLink"]
    assert (
        RepositorySnapshotFactEvidenceLink.__module__
        == "faultatlas.domain.snapshot_evidence_link"
    )


def test_bridge_module_has_only_the_bounded_model_and_no_io_call_surface() -> None:
    tree = ast.parse(LINK_SOURCE.read_text(encoding="utf-8"))
    assert [type(node) for node in tree.body] == [
        ast.Expr,
        ast.ImportFrom,
        ast.ImportFrom,
        ast.ImportFrom,
        ast.Assign,
        ast.ClassDef,
    ]
    assert not [node for node in tree.body if isinstance(node, ast.Import)]
    assert [
        (node.module, tuple(alias.name for alias in node.names))
        for node in tree.body
        if isinstance(node, ast.ImportFrom)
    ] == [
        (
            "pydantic",
            ("BaseModel", "ConfigDict", "ValidationInfo", "field_validator"),
        ),
        ("faultatlas.domain.evidence", ("DurableEvidenceRecordReference",)),
        (
            "faultatlas.domain.snapshot",
            ("RepositorySnapshotPathBinding", "RepositorySnapshotRootTreeBinding"),
        ),
    ]
    assert not [
        alias
        for node in tree.body
        if isinstance(node, ast.ImportFrom)
        for alias in node.names
        if alias.asname is not None
    ]
    classes = [node for node in tree.body if isinstance(node, ast.ClassDef)]
    assert [node.name for node in classes] == ["RepositorySnapshotFactEvidenceLink"]
    assert [type(node) for node in classes[0].body] == [
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
        target.id
        for node in classes[0].body
        if isinstance(node, ast.Assign)
        for target in node.targets
        if isinstance(target, ast.Name)
    ] == ["model_config"]
    assert [
        node.target.id
        for node in classes[0].body
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name)
    ] == ["fact", "evidence_record"]
    assert [
        node.name
        for node in classes[0].body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    ] == [
        "_require_typed_python_fact",
        "_require_typed_python_evidence_record",
    ]
    comparisons = [node for node in ast.walk(tree) if isinstance(node, ast.Compare)]
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
        ([ast.Eq], ["info.mode", "'python'"]),
        ([ast.Eq], ["info.mode", "'python'"]),
    ]
    assert {
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    } == {"ConfigDict", "ValueError", "field_validator", "isinstance"}
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
        "DurableEvidenceRecordReference",
        "RepositorySnapshotPathBinding",
        "RepositorySnapshotRootTreeBinding",
        "ValidationInfo",
        "ValueError",
        "classmethod",
        "field_validator",
        "info",
        "isinstance",
        "object",
        "value",
    }
    assert [
        (node.value.id, node.attr)
        for node in ast.walk(tree)
        if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name)
    ] == [("info", "mode"), ("info", "mode")]


def test_bridge_module_declares_no_reflection_or_capability_surface() -> None:
    source = LINK_SOURCE.read_text(encoding="utf-8")
    tree = ast.parse(source)
    referenced = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)} | {
        node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute)
    }

    for capability in (
        "Path",
        "__import__",
        "getattr",
        "hashlib",
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
        "write_text",
    ):
        assert capability not in referenced


def test_the_bridge_owns_the_only_cross_domain_edge() -> None:
    bridge = ast.parse(LINK_SOURCE.read_text(encoding="utf-8"))
    bridge_modules = {
        node.module
        for node in ast.walk(bridge)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }

    assert "faultatlas.domain.snapshot" in bridge_modules
    assert "faultatlas.domain.evidence" in bridge_modules

    for source in (SNAPSHOT_SOURCE, EVIDENCE_SOURCE):
        text = source.read_text(encoding="utf-8")
        assert "snapshot_evidence_link" not in text
        assert "RepositorySnapshotFactEvidenceLink" not in text

    snapshot_modules = {
        node.module
        for node in ast.walk(ast.parse(SNAPSHOT_SOURCE.read_text(encoding="utf-8")))
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }
    assert "faultatlas.domain.evidence" not in snapshot_modules

    evidence_modules = {
        node.module
        for node in ast.walk(ast.parse(EVIDENCE_SOURCE.read_text(encoding="utf-8")))
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }
    assert "faultatlas.domain.snapshot" not in evidence_modules
