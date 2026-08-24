from __future__ import annotations

import ast
import copy
import hashlib
import json
from enum import StrEnum
from pathlib import Path
from typing import Any, NamedTuple, cast

import pytest
from pydantic import BaseModel, ValidationError

from faultatlas.domain.evidence import (
    ArtifactByteLength,
    ArtifactSha256Digest,
    DurableEvidenceRecordReference,
)
from faultatlas.domain.identity import RepositoryIdentity
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
CORPUS_ROOT = REPOSITORY_ROOT / "reference_corpus/contracts/repository-snapshot/v1"
CORPUS_RELATIVE = "reference_corpus/contracts/repository-snapshot/v1"

EXPECTED_CORPUS_FILES = {
    "contract.md",
    "invalid-vectors.json",
    "invalid-vectors.sha256",
    "manifest.json",
    "manifest.sha256",
    "replay-vectors.json",
    "replay-vectors.sha256",
    "valid-vectors.json",
    "valid-vectors.sha256",
}
SEALED_JSON = ("manifest", "valid-vectors", "invalid-vectors", "replay-vectors")


class LockedFile(NamedTuple):
    byte_length: int
    sha256: str


# Fixed, independently recorded oracles for every published corpus byte. These
# are literals rather than values recomputed from the files under test, so a
# coordinated edit of a JSON file, its sidecar, and its manifest entry fails
# here instead of silently re-deriving its own expectation. This is what makes
# the manifest's append-only correction policy and immutable_after_publication
# claim enforceable.
LOCKED_CORPUS_FILES = {
    "contract.md": LockedFile(
        6643, "9002d89007da5627662787ed05045ad100dae0bdcf49a70d6832cf4a9e0e32f7"
    ),
    "invalid-vectors.json": LockedFile(
        116565, "9377845c4e6735dadc8e079f637fe78a8a09fb05967824322cbec034c8f26cc4"
    ),
    "invalid-vectors.sha256": LockedFile(
        87, "3fcbbce5514f222bd87927a1c4ad65abaaa90517bad0a483a3a62eea6ffa605a"
    ),
    "manifest.json": LockedFile(
        9133, "ca53f751b2e276e100b6da0fb1795eeed5414e94f17f6ec88e68980bbfeb8b13"
    ),
    "manifest.sha256": LockedFile(
        80, "2ad75cbd954bfd03d0e842efc188b8d9d774516db7bbaf340bad6ed188f69a57"
    ),
    "replay-vectors.json": LockedFile(
        70034, "a4945c9e0bcc3e85f8f1f26a66992ec8618df4e4ad719a40fad61fca7dac0226"
    ),
    "replay-vectors.sha256": LockedFile(
        86, "8e459bc8a5c46dbe5dbb3c2f6ce8a07015667beac571985987918fbea6cbb576"
    ),
    "valid-vectors.json": LockedFile(
        136727, "f26cc45cf2b5a13ee099dbda8f890743fe233ca7db3c855a4547784a405ea56f"
    ),
    "valid-vectors.sha256": LockedFile(
        85, "bd20b3ec0c4fce34d795fd6de0e758dba8580b4b810379d7251a929dcc9fa021"
    ),
}

S08_DECISION = (
    "reference_corpus/contracts/repository-snapshot/decisions/"
    "s08-deferred-subject-disposition/decision.json"
)
P03_CLOSURE = (
    "reference_corpus/contracts/evidence-envelope/closures/"
    "s1-p03-phase-closure/closure.json"
)
ACQUISITION = (
    "reference_corpus/pytest-4412/acquisitions/"
    "run-0001-s04-v1-base-4c9cde74-head-690a63b9/acquisition.json"
)

PREDECESSOR_DIGESTS = {
    S08_DECISION: "7361582b749eeb986319b0cce87155671b3b25904346be06e6004fb0e53ac1da",
    P03_CLOSURE: "21a24e7ab572456f22d3aca572e10e76be69529770b96a131f3d4f624d0b481b",
    ACQUISITION: "1c29093bf1537e9b824a18df1848b71a8da014f544bc9f385707eb0e000a1318",
    "reference_corpus/pytest-4412/closures/s1-p00-phase-closure/closure.json": (
        "8c02d79c4a5a1d52b9fc2a3718e1b47888da6195588e62ab927388dbe972189e"
    ),
    "reference_corpus/contracts/identity/closures/s1-p01-phase-closure/closure.json": (
        "2c1bfb9d3d596711066796ef83999d49b6846e65315a301eead7fa8fb5ac4642"
    ),
    "reference_corpus/contracts/revision-locator/closures/"
    "s1-p02-phase-closure/closure.json": (
        "daf3a89ef22bf20652d91cc96f476f1f31584ec90d860e57d1641c3ec6ab5a67"
    ),
    "reference_corpus/contracts/identity/v1/manifest.json": (
        "aafa6dee23971218f30f9c72f63e23741841f0852299bebf9f40471054cb760a"
    ),
    "reference_corpus/contracts/revision-locator/v1/manifest.json": (
        "56ba607a098744800ae94448982a0a3bab91fb4e7fba445a31406e2478dc1b80"
    ),
    "reference_corpus/contracts/evidence-envelope/v1/manifest.json": (
        "139364b04676d59e4717a38e73b371b138146a2a933688ab3793aac6fd2e03f0"
    ),
}

EXPECTED_PRODUCTION_FILES = {
    "src/faultatlas/__init__.py",
    "src/faultatlas/__main__.py",
    "src/faultatlas/cli.py",
    "src/faultatlas/domain/__init__.py",
    "src/faultatlas/domain/compatibility.py",
    "src/faultatlas/domain/evidence.py",
    "src/faultatlas/domain/history.py",
    "src/faultatlas/domain/identity.py",
    "src/faultatlas/domain/revision.py",
    "src/faultatlas/domain/snapshot.py",
    "src/faultatlas/domain/snapshot_evidence_link.py",
    "src/faultatlas/domain/source.py",
}

OWNED_TARGETS: dict[str, type[BaseModel]] = {
    "RepositorySnapshotIdentity": RepositorySnapshotIdentity,
    "RepositorySnapshotRootTreeBinding": RepositorySnapshotRootTreeBinding,
    "RepositorySnapshotPathBinding": RepositorySnapshotPathBinding,
    "RepositorySnapshotPathBindingCollection": RepositorySnapshotPathBindingCollection,
    "RepositorySnapshotDeclaredPathScope": RepositorySnapshotDeclaredPathScope,
    "RepositorySnapshotDeclaredPathScopeCoverage": (
        RepositorySnapshotDeclaredPathScopeCoverage
    ),
    "RepositorySnapshotFactEvidenceLink": RepositorySnapshotFactEvidenceLink,
}
SUPPORT_TARGETS: dict[str, type[BaseModel]] = {
    "ArtifactByteLength": ArtifactByteLength,
    "ArtifactSha256Digest": ArtifactSha256Digest,
    "DurableEvidenceRecordReference": DurableEvidenceRecordReference,
    "GitBlobIdentity": GitBlobIdentity,
    "GitCommitIdentity": GitCommitIdentity,
    "GitRepositoryPath": GitRepositoryPath,
    "GitTreeIdentity": GitTreeIdentity,
    "RepositoryIdentity": RepositoryIdentity,
}
SUPPORT_ENUMS: dict[str, type[StrEnum]] = {
    "GitHashAlgorithm": GitHashAlgorithm,
    "GitObjectKind": GitObjectKind,
}
ALL_TARGETS: dict[str, type[BaseModel]] = {**OWNED_TARGETS, **SUPPORT_TARGETS}

KNOWN_OPERATIONS = frozenset(
    {"construct", "mutate_reject", "reject", "replay_construct"}
)
KNOWN_MARKERS = frozenset(
    {"constructed_value", "enum_value", "indexed_value", "tuple_value", "typed_value"}
)
KNOWN_INPUT_MODES = frozenset({"json", "python", "replay"})
KNOWN_CLASSIFICATIONS = frozenset(
    {
        "caller_supplied_association",
        "caller_supplied_selection",
        "deterministic_derivation",
        "retained_normalized_observation",
    }
)
MAX_INDEXED_COUNT = 4097
MAX_DEPTH = 32

VECTOR_KEYS = frozenset(
    {
        "category",
        "decision_references",
        "expected",
        "id",
        "input",
        "input_mode",
        "operation",
        "purpose",
        "rationale",
        "semantic_partition",
        "status",
        "target_symbol",
    }
)
REPLAY_EXTRA_KEYS = frozenset({"evidence_classification", "source_pointers"})
MUTATION_EXTRA_KEYS = frozenset({"mutated_field"})


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load(name: str) -> dict[str, Any]:
    return cast(
        dict[str, Any], json.loads((CORPUS_ROOT / f"{name}.json").read_text("utf-8"))
    )


def _manifest() -> dict[str, Any]:
    return _load("manifest")


def _vectors(name: str) -> list[dict[str, Any]]:
    return cast(list[dict[str, Any]], _load(name)["vectors"])


def _fixtures(name: str) -> dict[str, Any]:
    document = _load(name)
    entries = cast(list[dict[str, Any]], document["fixtures"])
    return {cast(str, entry["id"]): entry["value"] for entry in entries}


def _substitute(node: Any, token: str, value: str) -> Any:
    if isinstance(node, dict):
        return {
            key: _substitute(item, token, value)
            for key, item in cast(dict[str, Any], node).items()
        }
    if isinstance(node, list):
        return [_substitute(item, token, value) for item in cast(list[Any], node)]
    if isinstance(node, str):
        return node.replace(token, value)
    return node


def _materialize(node: Any, fixtures: dict[str, Any], depth: int = 0) -> Any:
    assert depth <= MAX_DEPTH, "recursive marker depth exceeded"
    if isinstance(node, dict):
        mapping = cast(dict[str, Any], node)
        keys = set(mapping)
        marker = keys & KNOWN_MARKERS
        if keys and keys <= KNOWN_MARKERS:
            assert len(keys) == 1, "markers must be exact singleton objects"
        if marker:
            assert keys == marker, "a marker object carries no sibling keys"
        if keys == {"fixture_ref"}:
            reference = cast(str, mapping["fixture_ref"])
            assert reference in fixtures, f"unknown fixture reference: {reference}"
            return _materialize(copy.deepcopy(fixtures[reference]), fixtures, depth + 1)
        if keys == {"typed_value"}:
            descriptor = cast(dict[str, Any], mapping["typed_value"])
            assert set(descriptor) == {"input", "target"}
            target_name = cast(str, descriptor["target"])
            assert target_name in ALL_TARGETS, f"unknown target: {target_name}"
            resolved = _materialize(descriptor["input"], fixtures, depth + 1)
            return ALL_TARGETS[target_name].model_validate_json(json.dumps(resolved))
        if keys == {"constructed_value"}:
            descriptor = cast(dict[str, Any], mapping["constructed_value"])
            assert set(descriptor) == {"input", "target"}
            target_name = cast(str, descriptor["target"])
            assert target_name in ALL_TARGETS, f"unknown target: {target_name}"
            fields = cast(
                dict[str, Any], _materialize(descriptor["input"], fixtures, depth + 1)
            )
            # Deliberately bypasses validation so the parent's
            # revalidate_instances="always" contract has something to catch.
            return ALL_TARGETS[target_name].model_construct(**fields)
        if keys == {"enum_value"}:
            descriptor = cast(dict[str, Any], mapping["enum_value"])
            assert set(descriptor) == {"target", "value"}
            enum_name = cast(str, descriptor["target"])
            assert enum_name in SUPPORT_ENUMS, f"unknown enum target: {enum_name}"
            return SUPPORT_ENUMS[enum_name](descriptor["value"])
        if keys == {"tuple_value"}:
            items = cast(list[Any], mapping["tuple_value"])
            return tuple(_materialize(item, fixtures, depth + 1) for item in items)
        if keys == {"indexed_value"}:
            descriptor = cast(dict[str, Any], mapping["indexed_value"])
            assert set(descriptor) == {"count", "template", "token"}
            count = descriptor["count"]
            assert type(count) is int and 0 <= count <= MAX_INDEXED_COUNT
            token = cast(str, descriptor["token"])
            produced = [
                _materialize(
                    _substitute(descriptor["template"], token, str(index)),
                    fixtures,
                    depth + 1,
                )
                for index in range(count)
            ]
            return produced
        return {
            key: _materialize(item, fixtures, depth + 1)
            for key, item in mapping.items()
        }
    if isinstance(node, list):
        return [
            _materialize(item, fixtures, depth + 1) for item in cast(list[Any], node)
        ]
    return node


def _execute(vector: dict[str, Any], fixtures: dict[str, Any]) -> tuple[str, Any]:
    target = ALL_TARGETS[cast(str, vector["target_symbol"])]
    payload = _materialize(vector["input"], fixtures)
    mode = cast(str, vector["input_mode"])
    if vector["operation"] == "mutate_reject":
        model = target.model_validate_json(json.dumps(payload))
        field = cast(str, vector["mutated_field"])
        try:
            setattr(model, field, getattr(model, field))
        except ValidationError as error:
            return "rejected", error.errors()
        return "accepted", model
    try:
        if mode in ("json", "replay"):
            return "accepted", target.model_validate_json(json.dumps(payload))
        return "accepted", target.model_validate(payload)
    except ValidationError as error:
        return "rejected", error.errors()


def _assert_rejection(vector: dict[str, Any], errors: list[dict[str, Any]]) -> None:
    expected = cast(dict[str, Any], vector["expected"])
    assert expected["failure_category"] == "validation_error"
    location = cast(list[Any], expected["error_location"])
    mode = cast(str, expected["error_location_mode"])
    if mode == "prefix":
        assert any(
            entry["type"] == expected["error_type"]
            and list(cast(tuple[Any, ...], entry["loc"]))[: len(location)] == location
            for entry in errors
        ), f"{vector['id']}: no {expected['error_type']} under {location}"
    else:
        assert mode == "exact"
        first = errors[0]
        assert first["type"] == expected["error_type"], vector["id"]
        assert list(cast(tuple[Any, ...], first["loc"])) == location, vector["id"]


# --- corpus files ----------------------------------------------------------


def test_corpus_file_inventory_is_exact() -> None:
    assert CORPUS_ROOT.is_dir()
    assert {entry.name for entry in CORPUS_ROOT.iterdir()} == EXPECTED_CORPUS_FILES
    assert all(
        entry.is_file() and not entry.is_symlink() for entry in CORPUS_ROOT.iterdir()
    )
    assert not list(CORPUS_ROOT.glob("*.py"))
    assert not (CORPUS_ROOT / "contract.sha256").exists()

    declared = cast(list[dict[str, Any]], _manifest()["corpus_files"])
    assert {cast(str, entry["filename"]) for entry in declared} == EXPECTED_CORPUS_FILES
    assert len(declared) == 9
    assert all(entry["required"] is True for entry in declared)
    assert all(entry["git_mode"] == "100644" for entry in declared)


@pytest.mark.parametrize("name", SEALED_JSON)
def test_corpus_json_is_exactly_canonical(name: str) -> None:
    raw = (CORPUS_ROOT / f"{name}.json").read_bytes()
    document = json.loads(raw.decode("utf-8"))
    canonical = (
        json.dumps(
            document, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode("utf-8")
        + b"\n"
    )
    assert raw == canonical
    assert not raw.startswith(b"\xef\xbb\xbf")
    assert b"\r" not in raw
    assert raw.endswith(b"\n") and not raw.endswith(b"\n\n")

    def walk(value: Any) -> None:
        assert not isinstance(value, float)
        if isinstance(value, dict):
            for item in cast(dict[str, Any], value).values():
                walk(item)
        elif isinstance(value, list):
            for item in cast(list[Any], value):
                walk(item)

    walk(document)


@pytest.mark.parametrize("filename", tuple(sorted(LOCKED_CORPUS_FILES)))
def test_corpus_bytes_match_their_independent_locks(filename: str) -> None:
    locked = LOCKED_CORPUS_FILES[filename]
    path = CORPUS_ROOT / filename
    raw = path.read_bytes()
    assert len(raw) == locked.byte_length, filename
    assert hashlib.sha256(raw).hexdigest() == locked.sha256, filename


def test_locked_inventory_covers_every_published_corpus_file() -> None:
    assert set(LOCKED_CORPUS_FILES) == EXPECTED_CORPUS_FILES
    for name in SEALED_JSON:
        sidecar = LOCKED_CORPUS_FILES[f"{name}.sha256"]
        expected = f"{LOCKED_CORPUS_FILES[f'{name}.json'].sha256}  {name}.json\n"
        assert sidecar.byte_length == len(expected.encode())


@pytest.mark.parametrize("name", SEALED_JSON)
def test_sidecar_locks_the_exact_bytes(name: str) -> None:
    expected = f"{_digest(CORPUS_ROOT / f'{name}.json')}  {name}.json\n"
    assert (CORPUS_ROOT / f"{name}.sha256").read_bytes() == expected.encode()


def test_manifest_records_the_exact_vector_file_digests() -> None:
    declared = {
        cast(str, entry["filename"]): entry
        for entry in cast(list[dict[str, Any]], _manifest()["corpus_files"])
    }
    for name in ("valid-vectors", "invalid-vectors", "replay-vectors"):
        entry = declared[f"{name}.json"]
        path = CORPUS_ROOT / f"{name}.json"
        assert entry["sha256"] == _digest(path)
        assert entry["byte_length"] == len(path.read_bytes())
    assert "sha256" not in declared["manifest.json"]
    assert declared["manifest.json"]["digest_lock"] == "independent_tracked_test_oracle"


# --- manifest scope --------------------------------------------------------


def test_manifest_scope_is_exactly_the_two_owned_modules() -> None:
    scope = cast(dict[str, Any], _manifest()["scope"])
    assert scope["production_modules"] == [
        "faultatlas.domain.snapshot",
        "faultatlas.domain.snapshot_evidence_link",
    ]
    assert scope["supporting_authorities_not_owned"] == [
        "faultatlas.domain.evidence",
        "faultatlas.domain.identity",
        "faultatlas.domain.revision",
    ]
    assert scope["phase"] == "S1.P04"
    assert scope["slice"] == "S1.P04.S09"
    assert scope["covered_slices"] == [f"S1.P04.S0{index}" for index in range(1, 8)]
    assert scope["source_only"] is True
    assert scope["package_exclusion_required"] is True
    assert scope["source_hashes_are_behavioral_identity"] is False
    assert not set(scope["production_modules"]) & set(
        scope["supporting_authorities_not_owned"]
    )


def test_target_symbols_are_exactly_the_seven_owned_models() -> None:
    targets = cast(list[dict[str, Any]], _manifest()["target_symbols"])
    assert [cast(str, entry["symbol"]) for entry in targets] == list(OWNED_TARGETS)
    assert len(targets) == 7
    assert {cast(str, entry["module"]) for entry in targets} == {
        "faultatlas.domain.snapshot",
        "faultatlas.domain.snapshot_evidence_link",
    }
    assert [cast(str, entry["slice_layer"]) for entry in targets] == [
        f"S1.P04.S0{index}" for index in range(1, 8)
    ]

    import faultatlas.domain.snapshot as snapshot_module
    import faultatlas.domain.snapshot_evidence_link as link_module

    published = list(snapshot_module.__all__) + list(link_module.__all__)
    assert [cast(str, entry["symbol"]) for entry in targets] == published
    for entry in targets:
        module = (
            snapshot_module
            if entry["module"] == "faultatlas.domain.snapshot"
            else link_module
        )
        assert (
            getattr(module, cast(str, entry["symbol"]))
            is OWNED_TARGETS[cast(str, entry["symbol"])]
        )


def test_governance_records_are_not_product_symbols() -> None:
    symbols = {
        cast(str, entry["symbol"])
        for entry in cast(list[dict[str, Any]], _manifest()["target_symbols"])
    }
    assert not symbols & set(SUPPORT_TARGETS)
    for forbidden in (
        "DurableEvidenceRecordReference",
        "RepositoryIdentity",
        "GitCommitIdentity",
        "RepositorySnapshotFactEvidenceDisposition",
    ):
        assert forbidden not in symbols


# --- source decisions ------------------------------------------------------


def test_source_decisions_cite_and_lock_the_exact_authorities() -> None:
    decisions = cast(list[dict[str, Any]], _manifest()["source_decisions"])
    assert [cast(str, entry["path"]) for entry in decisions] == [
        S08_DECISION,
        P03_CLOSURE,
        ACQUISITION,
    ]
    for entry in decisions:
        path = REPOSITORY_ROOT / cast(str, entry["path"])
        assert path.is_file()
        assert entry["sha256"] == _digest(path)
        assert entry["sha256"] == PREDECESSOR_DIGESTS[cast(str, entry["path"])]
        assert entry["authority_ids"]

    assert decisions[0]["authority_role"] == "governance_disposition_not_vectorized"
    register = cast(
        dict[str, Any],
        json.loads((REPOSITORY_ROOT / S08_DECISION).read_text("utf-8"))[
            "inherited_subject_register"
        ],
    )
    assert register["self_owned_open"] == 0
    assert register["count"] == 7
    assert sorted(cast(list[str], decisions[0]["authority_ids"])) == sorted(
        cast(str, item["disposition_id"])
        for item in cast(list[dict[str, Any]], register["items"])
    )


def test_s08_decision_is_referenced_and_never_vectorized() -> None:
    corpus_text = "".join(
        (CORPUS_ROOT / f"{name}.json").read_text("utf-8") for name in SEALED_JSON
    )
    for governance_only in (
        "inherited_subject_register",
        "unknown_pending_additional_evidence",
        "evidence_insufficient",
        "unsupported_current_scope",
        "carried_forward",
    ):
        assert governance_only not in corpus_text
    for name in ("valid-vectors", "invalid-vectors", "replay-vectors"):
        for vector in _vectors(name):
            assert cast(str, vector["target_symbol"]) in OWNED_TARGETS


# --- vector schema ---------------------------------------------------------


@pytest.mark.parametrize("name", ("valid-vectors", "invalid-vectors", "replay-vectors"))
def test_vector_schema_is_exact(name: str) -> None:
    replay = name == "replay-vectors"
    for vector in _vectors(name):
        keys = set(vector)
        if replay:
            assert keys == VECTOR_KEYS | REPLAY_EXTRA_KEYS
        elif vector["operation"] == "mutate_reject":
            assert keys == VECTOR_KEYS | MUTATION_EXTRA_KEYS
            assert (
                cast(str, vector["mutated_field"])
                in ALL_TARGETS[cast(str, vector["target_symbol"])].model_fields
            )
        else:
            assert keys == VECTOR_KEYS
        assert vector["status"] == "locked"
        assert cast(str, vector["input_mode"]) in KNOWN_INPUT_MODES
        assert cast(str, vector["operation"]) in KNOWN_OPERATIONS
        assert cast(str, vector["target_symbol"]) in OWNED_TARGETS
        assert cast(str, vector["id"]).startswith("snapshot.")
        assert vector["purpose"] and vector["rationale"]
        assert vector["decision_references"]
        if replay:
            assert vector["evidence_classification"] in KNOWN_CLASSIFICATIONS
            assert vector["input_mode"] == "replay"
            assert vector["operation"] == "replay_construct"
        else:
            assert vector["operation"] == (
                "construct"
                if name == "valid-vectors"
                else ("reject", "mutate_reject")[vector["operation"] == "mutate_reject"]
            )


def test_vector_ids_and_semantic_partitions_are_globally_unique() -> None:
    vectors = [
        vector
        for name in ("valid-vectors", "invalid-vectors", "replay-vectors")
        for vector in _vectors(name)
    ]
    identifiers = [cast(str, vector["id"]) for vector in vectors]
    partitions = [cast(str, vector["semantic_partition"]) for vector in vectors]
    assert len(identifiers) == len(set(identifiers))
    assert len(partitions) == len(set(partitions)), "a vector duplicates a partition"
    assert len(vectors) == 158


def test_vector_counts_match_the_manifest_summary() -> None:
    summary = cast(dict[str, Any], _manifest()["vector_summary"])
    valid = _vectors("valid-vectors")
    invalid = _vectors("invalid-vectors")
    replay = _vectors("replay-vectors")

    assert cast(dict[str, Any], summary["valid"])["count"] == len(valid) == 50
    assert cast(dict[str, Any], summary["invalid"])["count"] == len(invalid) == 82
    assert cast(dict[str, Any], summary["replay"])["count"] == len(replay) == 26
    assert summary["total_vectors"] == len(valid) + len(invalid) + len(replay) == 158
    assert summary["fixtures"] == len(_fixtures("valid-vectors")) == 16

    for key, vectors in (("valid", valid), ("invalid", invalid), ("replay", replay)):
        categories = cast(
            dict[str, int], cast(dict[str, Any], summary[key])["categories"]
        )
        observed: dict[str, int] = {}
        for vector in vectors:
            name = cast(str, vector["category"])
            observed[name] = observed.get(name, 0) + 1
        assert categories == observed


def test_every_owned_symbol_is_covered_by_valid_and_invalid_vectors() -> None:
    valid_targets = {cast(str, v["target_symbol"]) for v in _vectors("valid-vectors")}
    invalid_targets = {
        cast(str, v["target_symbol"]) for v in _vectors("invalid-vectors")
    }
    replay_targets = {cast(str, v["target_symbol"]) for v in _vectors("replay-vectors")}
    assert valid_targets == set(OWNED_TARGETS)
    assert invalid_targets == set(OWNED_TARGETS)
    assert replay_targets <= set(OWNED_TARGETS)


# --- fixtures --------------------------------------------------------------


def test_fixtures_resolve_exactly_and_fail_closed() -> None:
    fixtures = _fixtures("valid-vectors")
    assert len(fixtures) == 16
    assert all(key.startswith("snapshot.fixture.") for key in fixtures)
    for entry in cast(list[dict[str, Any]], _load("valid-vectors")["fixtures"]):
        assert set(entry) == {"id", "status", "value"}
        assert entry["status"] == "locked"
    assert _load("invalid-vectors")["fixtures"] == []
    assert _load("replay-vectors")["fixtures"] == []

    with pytest.raises(AssertionError):
        _materialize({"fixture_ref": "snapshot.fixture.absent"}, fixtures)


def test_unknown_targets_operations_and_markers_reject() -> None:
    fixtures = _fixtures("valid-vectors")
    with pytest.raises(AssertionError):
        _materialize({"typed_value": {"input": "x", "target": "NoSuchModel"}}, fixtures)
    with pytest.raises(AssertionError):
        _materialize({"enum_value": {"target": "NoSuchEnum", "value": "x"}}, fixtures)
    with pytest.raises(AssertionError):
        _materialize(
            {
                "indexed_value": {
                    "count": MAX_INDEXED_COUNT + 1,
                    "template": {},
                    "token": "$I",
                }
            },
            fixtures,
        )
    with pytest.raises(AssertionError):
        _materialize(
            {"typed_value": {"input": 1, "target": "GitRepositoryPath"}, "x": 1},
            fixtures,
        )
    assert "NoSuchOperation" not in KNOWN_OPERATIONS
    registry = cast(dict[str, Any], _manifest()["execution_contract"])["registry"]
    assert cast(dict[str, Any], registry)["owned_model_targets"] == len(OWNED_TARGETS)
    assert cast(dict[str, Any], registry)["support_model_targets"] == len(
        SUPPORT_TARGETS
    )
    assert cast(dict[str, Any], registry)["support_enum_targets"] == len(SUPPORT_ENUMS)
    for policy in ("unknown_marker", "unknown_operation", "unknown_target"):
        assert cast(dict[str, Any], registry)[policy] == "reject"

    markers = cast(dict[str, Any], _manifest()["execution_contract"])[
        "test_input_markers"
    ]
    assert (
        set(cast(list[str], cast(dict[str, Any], markers)["allowed"])) == KNOWN_MARKERS
    )
    assert set(
        cast(list[str], cast(dict[str, Any], markers)["support_model_allowlist"])
    ) == set(SUPPORT_TARGETS)
    assert set(
        cast(list[str], cast(dict[str, Any], markers)["support_enum_allowlist"])
    ) == set(SUPPORT_ENUMS)


# --- execution -------------------------------------------------------------


@pytest.mark.parametrize(
    "vector",
    _vectors("valid-vectors"),
    ids=[cast(str, v["id"]) for v in _vectors("valid-vectors")],
)
def test_valid_vector_executes_to_its_recorded_expectation(
    vector: dict[str, Any],
) -> None:
    fixtures = _fixtures("valid-vectors")
    outcome, result = _execute(vector, fixtures)
    expected = cast(dict[str, Any], vector["expected"])
    assert outcome == "accepted", f"{vector['id']}: {result}"
    model = cast(BaseModel, result)
    assert type(model).__name__ == expected["concrete_type"]
    assert type(model) is ALL_TARGETS[cast(str, expected["runtime_target"])]
    dump = json.loads(model.model_dump_json())
    assert dump == _materialize(expected["semantic_dump"], fixtures), vector["id"]
    if expected["round_trip_equal"]:
        restored = type(model).model_validate_json(model.model_dump_json())
        assert restored == model


@pytest.mark.parametrize(
    "vector",
    _vectors("invalid-vectors"),
    ids=[cast(str, v["id"]) for v in _vectors("invalid-vectors")],
)
def test_invalid_vector_is_rejected_with_the_recorded_structure(
    vector: dict[str, Any],
) -> None:
    outcome, result = _execute(vector, _fixtures("invalid-vectors"))
    assert outcome == "rejected", f"{vector['id']} unexpectedly accepted"
    _assert_rejection(vector, cast(list[dict[str, Any]], result))


def test_error_oracle_locks_no_unstable_prose() -> None:
    contract = cast(dict[str, Any], _manifest()["rejection_contract"])
    assert contract["coercion"] == "forbidden"
    assert contract["normalization"] == "forbidden"
    assert contract["unstable_prose_locked"] is False
    assert contract["internal_union_branch_labels_locked"] is False
    assert contract["error_oracle"] == [
        "failure_category",
        "error_location",
        "error_location_mode",
        "error_type",
    ]
    for vector in _vectors("invalid-vectors"):
        expected = cast(dict[str, Any], vector["expected"])
        assert set(expected) == {
            "error_location",
            "error_location_mode",
            "error_type",
            "failure_category",
            "outcome",
        }
        assert expected["error_location_mode"] in {"exact", "prefix"}
        assert "msg" not in expected and "message" not in expected
        assert "function-after[" not in json.dumps(expected)


# --- replay ----------------------------------------------------------------


@pytest.mark.parametrize(
    "vector",
    _vectors("replay-vectors"),
    ids=[cast(str, v["id"]) for v in _vectors("replay-vectors")],
)
def test_replay_vector_reconstructs_its_published_value(
    vector: dict[str, Any],
) -> None:
    fixtures = _fixtures("replay-vectors")
    outcome, result = _execute(vector, fixtures)
    expected = cast(dict[str, Any], vector["expected"])
    assert outcome == "accepted", f"{vector['id']}: {result}"
    model = cast(BaseModel, result)
    assert json.loads(model.model_dump_json()) == _materialize(
        expected["semantic_dump"], fixtures
    )


def _resolve_pointer(document: Any, pointer: str) -> Any:
    node = document
    for token in [part for part in pointer.split("/") if part]:
        if isinstance(node, list):
            node = cast(list[Any], node)[int(token)]
        else:
            node = cast(dict[str, Any], node)[token]
    return node


@pytest.mark.parametrize(
    "vector",
    [v for v in _vectors("replay-vectors") if v["source_pointers"]],
    ids=[
        cast(str, v["id"]) for v in _vectors("replay-vectors") if v["source_pointers"]
    ],
)
def test_every_replay_source_pointer_resolves_into_its_replayed_value(
    vector: dict[str, Any],
) -> None:
    dump = cast(dict[str, Any], vector["expected"])["semantic_dump"]
    for pointer in cast(list[dict[str, Any]], vector["source_pointers"]):
        assert set(pointer) == {"document_path", "json_pointer", "source_fields"}
        path = REPOSITORY_ROOT / cast(str, pointer["document_path"])
        assert path.is_file(), f"{vector['id']}: {pointer['document_path']}"
        document = json.loads(path.read_text("utf-8"))
        # A cited pointer must resolve; a dangling pointer is a false
        # provenance claim even when the vector itself still constructs.
        resolved = _resolve_pointer(document, cast(str, pointer["json_pointer"]))

        # Resolvability alone proves nothing: an object-valued pointer could be
        # swapped for any other existing object. Each cited source field is
        # therefore mapped onto the exact replayed field and compared by value,
        # so a vector cannot claim retained provenance it does not have.
        fields = cast(dict[str, str], pointer["source_fields"])
        assert fields, f"{vector['id']}: a cited pointer must map at least one field"
        for source_field, replayed_field in fields.items():
            observed = _resolve_pointer(resolved, source_field)
            replayed = _resolve_pointer(dump, replayed_field)
            assert observed == replayed, (
                f"{vector['id']}: {pointer['json_pointer']}{source_field} is "
                f"{observed!r} but the replayed {replayed_field} is {replayed!r}"
            )


def test_only_retained_observations_cite_retained_evidence() -> None:
    for vector in _vectors("replay-vectors"):
        classification = cast(str, vector["evidence_classification"])
        pointers = cast(list[dict[str, Any]], vector["source_pointers"])
        if classification == "retained_normalized_observation":
            assert pointers, f"{vector['id']} claims retained provenance with no source"
        else:
            # Caller-supplied selections, deterministic derivations, and
            # associations are not declared by any retained record, so they
            # must cite no retained location at all.
            assert pointers == [], f"{vector['id']} must cite no retained source"


def test_replay_layers_are_actually_chained() -> None:
    dumps = {
        cast(str, vector["id"]): cast(dict[str, Any], vector["expected"])[
            "semantic_dump"
        ]
        for vector in _vectors("replay-vectors")
    }

    # The replayed subject must be the subject carried by every replayed fact,
    # so a corrected subject cannot leave stale copies behind.
    subject = dumps["snapshot.replay.subject.canonical"]
    fact_ids = ["snapshot.replay.root-tree.canonical"]
    fact_ids += [f"snapshot.replay.path-binding.blob-{index}" for index in range(4)]
    fact_ids += [f"snapshot.replay.path-binding.tree-{index}" for index in range(5)]
    for fact_id in fact_ids:
        assert dumps[fact_id]["snapshot"] == subject, fact_id

    # The replayed S04 aggregate must contain exactly the nine replayed S03
    # facts, in the replayed order.
    nine_facts = [dumps[fact_id] for fact_id in fact_ids[1:]]
    collection = dumps["snapshot.replay.collection.canonical-nine"]
    assert collection["bindings"] == nine_facts
    assert collection["snapshot"] == subject

    # The replayed S06 witnesses must embed the replayed S05 scope and the
    # replayed S04 collection, not independently authored copies of them.
    four_scope = dumps["snapshot.replay.scope.canonical-four"]
    nine_scope = dumps["snapshot.replay.scope.canonical-nine"]
    assert four_scope["snapshot"] == subject
    assert nine_scope["snapshot"] == subject
    assert dumps["snapshot.replay.coverage.four-over-nine"] == {
        "collection": collection,
        "scope": four_scope,
    }
    assert dumps["snapshot.replay.coverage.nine-over-nine"] == {
        "collection": collection,
        "scope": nine_scope,
    }

    # The declared scopes must be drawn from the replayed facts themselves.
    bound_paths = [cast(dict[str, Any], fact)["path"] for fact in nine_facts]
    assert cast(list[str], four_scope["declared_paths"]) == bound_paths[:4]
    assert cast(list[str], nine_scope["declared_paths"]) == bound_paths

    # Each replayed association must carry one of the replayed facts exactly.
    link_ids = ["snapshot.replay.link.root-tree"]
    link_ids += [f"snapshot.replay.link.blob-{index}" for index in range(4)]
    link_ids += [f"snapshot.replay.link.tree-{index}" for index in range(5)]
    assert [dumps[link_id]["fact"] for link_id in link_ids] == [
        dumps[fact_id] for fact_id in fact_ids
    ]


def test_replay_preserves_heterogeneous_provenance() -> None:
    observed: dict[str, set[str]] = {}
    for vector in _vectors("replay-vectors"):
        classification = cast(str, vector["evidence_classification"])
        observed.setdefault(classification, set()).add(
            cast(str, vector["target_symbol"])
        )

    assert set(observed) == KNOWN_CLASSIFICATIONS
    assert observed["retained_normalized_observation"] == {
        "RepositorySnapshotIdentity",
        "RepositorySnapshotRootTreeBinding",
        "RepositorySnapshotPathBinding",
    }
    assert observed["caller_supplied_selection"] == {
        "RepositorySnapshotPathBindingCollection",
        "RepositorySnapshotDeclaredPathScope",
    }
    assert observed["deterministic_derivation"] == {
        "RepositorySnapshotDeclaredPathScopeCoverage"
    }
    assert observed["caller_supplied_association"] == {
        "RepositorySnapshotFactEvidenceLink"
    }

    contract = cast(dict[str, Any], _manifest()["replay_contract"])
    assert (
        set(cast(dict[str, Any], contract["classifications"])) == KNOWN_CLASSIFICATIONS
    )
    assert contract["flattened_evidence_derived_snapshot_claimed"] is False
    assert contract["production_replay_io"] is False
    assert contract["production_lookup"] == "none"

    limits = cast(dict[str, Any], contract["evidence_limits"])
    assert limits["retained_leaves"] == 4
    assert limits["retained_traversals"] == 6
    assert limits["retained_tree_entry_manifest"] is False
    assert limits["whole_repository_enumeration_claimed"] is False
    assert limits["verified_membership_claimed"] is False
    assert limits["root_tree_reachability_claimed"] is False

    acquisition = cast(
        dict[str, Any],
        json.loads((REPOSITORY_ROOT / ACQUISITION).read_text("utf-8"))["observations"][
            "path_resolution"
        ],
    )
    assert len(cast(list[Any], acquisition["leaves"])) == limits["retained_leaves"]
    assert (
        len(cast(list[Any], acquisition["traversals"])) == limits["retained_traversals"]
    )
    for traversal in cast(list[dict[str, Any]], acquisition["traversals"]):
        assert traversal["non_recursive"] is True
        assert "entries" not in traversal


def test_replay_locks_the_retained_artifact_and_ten_evidence_links() -> None:
    document = _load("replay-vectors")
    locks = cast(list[dict[str, Any]], document["artifact_locks"])
    assert len(locks) == 1
    lock = locks[0]
    assert lock["path"] == ACQUISITION
    assert lock["sha256"] == _digest(REPOSITORY_ROOT / ACQUISITION)
    assert lock["byte_length"] == len((REPOSITORY_ROOT / ACQUISITION).read_bytes())

    links = [
        vector
        for vector in _vectors("replay-vectors")
        if vector["target_symbol"] == "RepositorySnapshotFactEvidenceLink"
    ]
    assert len(links) == 10
    # An association references the retained record as whole bytes rather than
    # a location inside it, so the artifact lock is its citation and the
    # referenced digest and length must match that artifact exactly.
    for vector in links:
        assert vector["source_pointers"] == []
        record = cast(
            dict[str, Any],
            cast(dict[str, Any], vector["expected"])["semantic_dump"][
                "evidence_record"
            ],
        )
        assert record["sha256"] == lock["sha256"]
        assert record["byte_length"] == lock["byte_length"]
    facts = [
        json.dumps(cast(dict[str, Any], vector["expected"])["semantic_dump"]["fact"])
        for vector in links
    ]
    assert len(set(facts)) == 10
    records = {
        json.dumps(
            cast(dict[str, Any], vector["expected"])["semantic_dump"][
                "evidence_record"
            ],
            sort_keys=True,
        )
        for vector in links
    }
    assert len(records) == 1


# --- semantic families -----------------------------------------------------


def test_empty_inventory_assertion_triple_is_locked() -> None:
    partitions = {
        cast(str, vector["semantic_partition"]): vector
        for name in ("valid-vectors", "invalid-vectors")
        for vector in _vectors(name)
    }
    assert (
        partitions["empty-triple:S04-empty-valid"]["expected"]["outcome"] == "accepted"
    )
    assert (
        partitions["empty-triple:S05-empty-valid"]["expected"]["outcome"] == "accepted"
    )
    assert (
        partitions["empty-triple:S06-empty-invalid"]["expected"]["outcome"]
        == "rejected"
    )


def test_ordering_and_superset_contracts_are_locked() -> None:
    partitions = {
        cast(str, vector["semantic_partition"]): vector
        for name in ("valid-vectors", "invalid-vectors")
        for vector in _vectors(name)
    }
    for partition in (
        "ordering:S04-order-preserved",
        "ordering:S05-order-preserved",
        "ordering:S06-scope-order-insensitive",
        "ordering:S06-collection-order-insensitive",
        "superset:exact-four",
        "superset:collection-superset",
        "superset:exact-nine",
    ):
        assert partitions[partition]["expected"]["outcome"] == "accepted"
    assert (
        partitions["superset:nine-scope-four-collection-rejected"]["expected"][
            "outcome"
        ]
        == "rejected"
    )

    fixtures = _fixtures("valid-vectors")
    forward = _execute(partitions["superset:exact-nine"], fixtures)[1]
    reordered = _execute(partitions["ordering:S06-scope-order-insensitive"], fixtures)[
        1
    ]
    assert cast(BaseModel, forward) != cast(BaseModel, reordered)


def test_rejected_coverage_encodes_no_absence_vocabulary() -> None:
    vector = next(
        v
        for v in _vectors("invalid-vectors")
        if v["semantic_partition"] == "superset:nine-scope-four-collection-rejected"
    )
    serialized = json.dumps(vector)
    for forbidden in (
        "absent",
        "missing_paths",
        "unavailable",
        "unknown_paths",
        "not_found",
        "omitted",
        "uncovered_paths",
    ):
        assert forbidden not in serialized


def test_non_goals_record_the_published_semantic_boundary() -> None:
    goals = cast(list[str], _manifest()["non_goals"])
    assert len(goals) == len(set(goals)) == 21
    for required in (
        "a_supplied_path_binding_is_not_repository_membership",
        "a_coverage_witness_is_not_snapshot_completeness",
        "an_uncovered_declared_path_is_not_absent_missing_unknown_or_unavailable",
        "no_whole_repository_enumeration_or_completeness",
        "no_verified_repository_membership",
        "no_known_absence",
        "no_prefix_ancestry_or_tree_topology_semantics",
        "no_git_mode_executable_symlink_or_gitlink_semantics",
        "no_default_branch_designation",
        "no_historical_default_branch_substitution",
        "S07_evidence_association_is_LEVEL_1_record_level_only",
        "no_fact_level_evidence_locator_or_json_pointer",
        "no_persistence_serialization_readers_writers_or_migration",
        "corpus_replay_classifications_are_test_metadata_not_production_vocabulary",
    ):
        assert required in goals


def test_level_one_association_is_established_by_shape_and_rejection() -> None:
    assert tuple(RepositorySnapshotFactEvidenceLink.model_fields) == (
        "fact",
        "evidence_record",
    )
    rejected = {
        cast(str, vector["semantic_partition"])
        for vector in _vectors("invalid-vectors")
        if vector["target_symbol"] == "RepositorySnapshotFactEvidenceLink"
    }
    for partition in (
        "non-generalization:no-support-role",
        "non-generalization:no-fact-locator",
        "non-generalization:level-1-only",
        "S07:cardinality:no-collection",
    ):
        assert partition in rejected
    # A rejected vector legitimately carries the forbidden field in its *input*;
    # what must never happen is a stronger field surviving into an accepted value.
    for name in ("valid-vectors", "replay-vectors"):
        for vector in _vectors(name):
            if vector["target_symbol"] != "RepositorySnapshotFactEvidenceLink":
                continue
            dump = cast(
                dict[str, Any],
                cast(dict[str, Any], vector["expected"])["semantic_dump"],
            )
            assert set(dump) == {"evidence_record", "fact"}, vector["id"]
            for stronger in (
                "confidence",
                "json_pointer",
                "locator",
                "review",
                "strength",
                "support_role",
                "verified",
            ):
                assert stronger not in dump, vector["id"]


# --- boundaries and integrity ----------------------------------------------


def test_python_json_input_boundary_is_covered_per_model() -> None:
    partitions = {
        cast(str, vector["semantic_partition"])
        for name in ("valid-vectors", "invalid-vectors")
        for vector in _vectors(name)
    }
    # Typed-positive and dumped-mapping rejection must both be frozen for every
    # one of the seven models, not only for the ones that happened to be easy.
    for index in range(1, 8):
        assert f"boundary:python-typed:S0{index}" in partitions
        assert f"boundary:python-mapping-rejected:S0{index}" in partitions
    for required in (
        "boundary:python-tuple-strict:S04",
        "boundary:python-tuple-strict:S05",
        "boundary:python-scalar-rejected",
        "boundary:python-swapped",
    ):
        assert required in partitions
    frozen_targets = {
        cast(str, v["target_symbol"])
        for v in _vectors("invalid-vectors")
        if cast(str, v["semantic_partition"]).startswith("frozen:")
    }
    revalidation_targets = {
        cast(str, v["target_symbol"])
        for v in _vectors("invalid-vectors")
        if cast(str, v["semantic_partition"]).startswith("revalidation:")
    }
    assert frozen_targets == set(OWNED_TARGETS)
    assert revalidation_targets == set(OWNED_TARGETS)
    typed_targets = {
        cast(str, v["target_symbol"])
        for v in _vectors("valid-vectors")
        if cast(str, v["semantic_partition"]).startswith("boundary:python-typed:")
    }
    rejected_targets = {
        cast(str, v["target_symbol"])
        for v in _vectors("invalid-vectors")
        if cast(str, v["semantic_partition"]).startswith(
            "boundary:python-mapping-rejected:"
        )
    }
    assert typed_targets == set(OWNED_TARGETS)
    assert rejected_targets == set(OWNED_TARGETS)
    json_targets = {
        cast(str, vector["target_symbol"])
        for vector in _vectors("valid-vectors")
        if vector["input_mode"] == "json"
    }
    assert json_targets == set(OWNED_TARGETS)


def test_corpus_declares_no_production_capability() -> None:
    assurance = cast(dict[str, Any], _manifest()["assurance"])
    assert assurance["no_production_capability"] is True
    assert assurance["production_reader_writer_or_validator"] is False
    assert assurance["package_exclusion"] is True
    assert assurance["immutable_after_publication"] is True
    forbidden = cast(
        list[str],
        cast(dict[str, Any], _manifest()["execution_contract"])[
            "unsafe_mechanisms_forbidden"
        ],
    )
    assert set(forbidden) == {
        "arbitrary_attribute_traversal",
        "dynamic_import",
        "eval",
        "exec",
        "network_access",
        "plugin_loading",
        "production_file_readers",
    }
    tree = ast.parse(Path(__file__).read_text("utf-8"))
    calls = {
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    assert not calls & {"eval", "exec", "__import__", "compile", "open"}


def test_corpus_is_excluded_from_the_packaged_source_root() -> None:
    assert not CORPUS_RELATIVE.startswith("src/")
    assert CORPUS_ROOT.relative_to(REPOSITORY_ROOT).parts[0] == "reference_corpus"
    observed = {
        path.relative_to(REPOSITORY_ROOT).as_posix()
        for path in (REPOSITORY_ROOT / "src").rglob("*.py")
    }
    assert observed == EXPECTED_PRODUCTION_FILES
    assert len(observed) == 12


@pytest.mark.parametrize("relative", tuple(sorted(PREDECESSOR_DIGESTS)))
def test_predecessor_and_governance_bytes_are_unchanged(relative: str) -> None:
    assert _digest(REPOSITORY_ROOT / relative) == PREDECESSOR_DIGESTS[relative]


def test_contract_markdown_is_derived_and_not_an_authority() -> None:
    markdown = (CORPUS_ROOT / "contract.md").read_text("utf-8")
    assert markdown.startswith("# Repository Snapshot Contract Corpus\n")
    assert "this Markdown is derived" in markdown
    assert "never an independent semantic authority" in markdown
    for name in SEALED_JSON:
        assert _digest(CORPUS_ROOT / f"{name}.json") in markdown
    summary = cast(dict[str, Any], _manifest()["vector_summary"])
    assert f"**{summary['total_vectors']}**" in markdown
    for symbol in OWNED_TARGETS:
        assert f"`{symbol}`" in markdown
    declared = {
        cast(str, entry["filename"]): entry
        for entry in cast(list[dict[str, Any]], _manifest()["corpus_files"])
    }
    assert declared["contract.md"]["role"] == "derived_non_authoritative_markdown"


# --- roadmap ---------------------------------------------------------------


def test_roadmap_records_the_s09_corpus_and_current_phase_state() -> None:
    roadmap = " ".join((REPOSITORY_ROOT / "docs/roadmap.md").read_text("utf-8").split())
    assert "`S1.P04.S09` is complete" in roadmap
    assert "`S1.P04.S10` is complete" in roadmap
    assert "`S1.P04` is complete" in roadmap
    assert "`S1.P05` is active and incomplete" in roadmap
    assert "`S1.P05.S06` are complete" in roadmap
    assert "`S1.P05.S07` is next and not started" in roadmap
    assert "`S1.P06` through `S1.P10` remain not started" in roadmap
    assert CORPUS_RELATIVE in roadmap
    assert "`S1.P04` is complete" in roadmap
    # S1.P04.S10 closure makes S1.P05 eligible; S09 itself did not.
    assert "`S1.P05` is active and incomplete" in roadmap
    assert "`S1.P05.S06` are complete" in roadmap
    assert "`S1.P05.S07` is next and not started" in roadmap
    assert "S1.P05 implementation has begun" not in roadmap
