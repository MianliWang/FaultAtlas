from __future__ import annotations

import copy
import hashlib
import json
import re
import shutil
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, Any, NewType, TypeVar, cast

import pytest
from pydantic import BaseModel, ValidationError
from typing_extensions import TypeAliasType as ExtensionsTypeAliasType  # noqa: UP035

from faultatlas.domain.compatibility import (
    LegacyObjectIdInterpretation,
    LegacySourceLocatorMappingResult,
    map_legacy_source_locator,
)
from faultatlas.domain.identity import (
    IdentityFieldState,
    IdentityValueState,
    ProviderGlobalId,
    ProviderNodeId,
    RepositoryAliasObservation,
    RepositoryScopedNumber,
    SourceIdentity,
)
from faultatlas.domain.source import SourceLocator

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
V1_ROOT = REPOSITORY_ROOT / "reference_corpus/contracts/identity/v1"
CORRECTION_ROOT = (
    REPOSITORY_ROOT / "reference_corpus/contracts/identity/corrections/"
    "s05-c01-ambiguous-union-round-trip"
)
EXPECTED_CORRECTION_FILES = {
    "correction.json",
    "correction.md",
    "correction.sha256",
    "regression-vectors.json",
    "regression-vectors.sha256",
}
EXPECTED_CORRECTION_TOP_LEVEL = {
    "assurance",
    "assurance_corrections",
    "confirmed_defect",
    "correction_identity",
    "format",
    "publication_contract",
    "replacement_contract",
    "review_thread_settlement",
    "scope",
    "selected_resolution",
    "source_locks",
    "superseded_contract_vectors",
}
EXPECTED_REGRESSION_TOP_LEVEL = {
    "assurance",
    "correction_identity",
    "format",
    "vectors",
}
EXPECTED_VECTOR_KEYS = {
    "category",
    "expected",
    "id",
    "input",
    "input_mode",
    "operation",
    "purpose",
    "source_finding",
    "status",
    "supersedes_v1_vector_ids",
    "target",
}
EXPECTED_VECTOR_IDS = (
    "identity.correction.s05-c01.generic-rejection.global-node.present-python",
    "identity.correction.s05-c01.generic-rejection.global-node.present-json",
    "identity.correction.s05-c01.generic-rejection.global-node.conflict-python",
    "identity.correction.s05-c01.generic-rejection.global-node.conflict-json",
    "identity.correction.s05-c01.generic-rejection.number-global.present-python",
    "identity.correction.s05-c01.generic-rejection.number-global.present-json",
    "identity.correction.s05-c01.generic-rejection.number-global.conflict-distinct-json",
    "identity.correction.s05-c01.generic-rejection.number-global.conflict-same-lexeme-python",
    "identity.correction.s05-c01.generic-rejection.number-global.conflict-same-lexeme-json",
    "identity.correction.s05-c01.generic-rejection.alias-global-node.present-json",
    "identity.correction.s05-c01.generic-rejection.annotated-global-node.present-json",
    "identity.correction.s05-c01.generic-rejection.annotated-member-global-node.present-json",
    "identity.correction.s05-c01.generic-rejection.subclass-global-node.present-json",
    "identity.correction.s05-c01.generic-rejection.newtype-global-node.present-json",
    "identity.correction.s05-c01.generic-rejection.constrained-typevar-global-node.present-json",
    "identity.correction.s05-c01.generic-rejection.bound-typevar-global-node.present-json",
    "identity.correction.s05-c01.generic-rejection.alias-bound-typevar-global-node.present-json",
    "identity.correction.s05-c01.generic-rejection.generic-alias-global-node.present-json",
    "identity.correction.s05-c01.generic-rejection.nested-generic-alias-global-node.present-json",
    "identity.correction.s05-c01.generic-rejection.extensions-alias-global-node.present-json",
    "identity.correction.s05-c01.monomorphic.global-id.present-round-trip",
    "identity.correction.s05-c01.monomorphic.node-id.present-round-trip",
    "identity.correction.s05-c01.monomorphic.repository-number.present-round-trip",
    "identity.correction.s05-c01.monomorphic.node-id.conflict-round-trip",
    "identity.correction.s05-c01.structured-union.source-identity.conflict-round-trip",
    "identity.correction.s05-c01.compatibility.repository-scoped.present-round-trip",
    "identity.correction.s05-c01.compatibility.provider-global.present-round-trip",
    "identity.correction.s05-c01.compatibility.unresolved.same-lexeme-conflict-round-trip",
    "identity.correction.s05-c01.compatibility.unresolved.no-candidate-collapse",
    "identity.correction.s05-c01.compatibility.mapping-result.round-trip-equality",
    "identity.correction.s05-c01.compatibility.unresolved.no-selected-winner",
    "identity.correction.s05-c01.compatibility.no-alternate-id-equivalence",
)
SUPERSEDED_ID = "identity.valid.field-state.conflict-number-global"
REPLACEMENT_ID = (
    "identity.correction.s05-c01.generic-rejection.number-global.conflict-distinct-json"
)
AMBIGUOUS_MESSAGE_PARTS = (
    "ambiguous scalar JSON representations",
    "domain-discriminated carrier",
)


@dataclass(frozen=True)
class LockedFile:
    byte_length: int
    sha256: str


EXPECTED_LOCKS = {
    "correction.json": LockedFile(
        12436, "c17edfa5dc227850d6b982d1ec8c83b4236cd403bb7ca1b1c66b662f8657347a"
    ),
    "correction.md": LockedFile(
        2808, "32eae618dc35a124f93f9dcac3682fb27fb7621c5a1065331be5584ec972bcc0"
    ),
    "correction.sha256": LockedFile(
        82, "d63684a33ca94471ff62485064850f1db7b5a8ec7eab25f3902b0afa529aec7e"
    ),
    "regression-vectors.json": LockedFile(
        26111, "721b6a97a7b80dcc1d33643f6920b21d2e2a8b010d8528f8d194a6691a3feff2"
    ),
    "regression-vectors.sha256": LockedFile(
        90, "d8a881d7ec3bc9908fedd5b7eeb2ab03d9e241e12dbf90a45d477eae4acf1ed1"
    ),
}
V1_LOCKS = {
    "compatibility-vectors.json": LockedFile(
        53810, "f3f9248c2562bb4a545b2e14d25d0346689bbf5b346ca343a8974b317d4b79ac"
    ),
    "compatibility-vectors.sha256": LockedFile(
        93, "9c19cc782e935fa2a5954cebbcc7055a9c6cc895b657b36d5e5781f7169931ec"
    ),
    "contract.md": LockedFile(
        3329, "4c3d44194d1708d1493808022212476ca4bfb3324ed3b620cbd7d9f830fcd806"
    ),
    "invalid-vectors.json": LockedFile(
        56435, "d2d700c1e553df907dc43be73e40881e0f937472dbe40c65c9b7d5556cab4bc6"
    ),
    "invalid-vectors.sha256": LockedFile(
        87, "32b5a8845243e5202464dbd09f6b06ee5dd750c69a8768fb5cea415f9e3a2fb7"
    ),
    "manifest.json": LockedFile(
        7586, "aafa6dee23971218f30f9c72f63e23741841f0852299bebf9f40471054cb760a"
    ),
    "manifest.sha256": LockedFile(
        80, "b5769ead5196aa7ea780be5920efc295d16673e93ecc010b45394aaa4bd58173"
    ),
    "valid-vectors.json": LockedFile(
        46891, "f58df3e6f123c468b8bc1f3185769e6d0773b4942a90207d7ec4fb37b26f8ef7"
    ),
    "valid-vectors.sha256": LockedFile(
        85, "912070e5f3772a59985a57d623e2ab16caadd70ca902bab2e0bd13183c15c33e"
    ),
}


type _ScalarGlobalNodeAlias = ProviderGlobalId | ProviderNodeId
type _ScalarGenericAlias[T] = T | ProviderNodeId
type _NestedScalarGenericAlias[T] = _ScalarGenericAlias[T]
type _ProviderGlobalAliasOne = ProviderGlobalId
type _ProviderGlobalAliasTwo = ProviderGlobalId

_ConstrainedGlobalNodeT = TypeVar(
    "_ConstrainedGlobalNodeT",
    ProviderGlobalId,
    ProviderNodeId,
)
_BoundGlobalNodeT = TypeVar(
    "_BoundGlobalNodeT",
    bound=ProviderGlobalId | ProviderNodeId,
)
_AliasBoundGlobalNodeT = TypeVar(
    "_AliasBoundGlobalNodeT",
    bound=_ScalarGlobalNodeAlias,
)
_MonomorphicGlobalT = TypeVar(
    "_MonomorphicGlobalT",
    bound=ProviderGlobalId,
)
_ExtensionsScalarGlobalNodeAlias = ExtensionsTypeAliasType(  # noqa: UP040
    "_ExtensionsScalarGlobalNodeAlias",
    ProviderGlobalId | ProviderNodeId,
)


class _ProviderGlobalIdSubclass(ProviderGlobalId):
    pass


_NewTypeProviderGlobalId = NewType(
    "_NewTypeProviderGlobalId",
    ProviderGlobalId,
)


def _runtime_state_model(annotation: object) -> type[BaseModel]:
    return cast(type[BaseModel], cast(Any, IdentityValueState)[annotation])


STATE_TARGETS: dict[str, type[BaseModel]] = {
    "IdentityValueState[ProviderGlobalId|ProviderNodeId]": IdentityValueState[
        ProviderGlobalId | ProviderNodeId
    ],
    "IdentityValueState[RepositoryScopedNumber|ProviderGlobalId]": (
        IdentityValueState[RepositoryScopedNumber | ProviderGlobalId]
    ),
    "IdentityValueState[ProviderGlobalId]": IdentityValueState[ProviderGlobalId],
    "IdentityValueState[ProviderNodeId]": IdentityValueState[ProviderNodeId],
    "IdentityValueState[RepositoryScopedNumber]": IdentityValueState[
        RepositoryScopedNumber
    ],
    "IdentityValueState[SourceIdentity]": IdentityValueState[SourceIdentity],
    "IdentityValueState[ScalarGlobalNodeAlias]": IdentityValueState[
        _ScalarGlobalNodeAlias
    ],
    "IdentityValueState[Annotated[ProviderGlobalId|ProviderNodeId]]": (
        IdentityValueState[
            Annotated[ProviderGlobalId | ProviderNodeId, "correction-probe"]
        ]
    ),
    "IdentityValueState[Annotated[ProviderGlobalId]|ProviderNodeId]": (
        IdentityValueState[
            Annotated[ProviderGlobalId, "correction-probe"] | ProviderNodeId
        ]
    ),
    "IdentityValueState[ProviderGlobalIdSubclass|ProviderNodeId]": (
        IdentityValueState[_ProviderGlobalIdSubclass | ProviderNodeId]
    ),
    "IdentityValueState[NewTypeProviderGlobalId|ProviderNodeId]": (
        IdentityValueState[_NewTypeProviderGlobalId | ProviderNodeId]
    ),
    "IdentityValueState[ConstrainedGlobalNodeT]": _runtime_state_model(
        _ConstrainedGlobalNodeT
    ),
    "IdentityValueState[BoundGlobalNodeT]": _runtime_state_model(_BoundGlobalNodeT),
    "IdentityValueState[AliasBoundGlobalNodeT]": _runtime_state_model(
        _AliasBoundGlobalNodeT
    ),
    "IdentityValueState[ScalarGenericAlias[ProviderGlobalId]]": (
        IdentityValueState[_ScalarGenericAlias[ProviderGlobalId]]
    ),
    "IdentityValueState[NestedScalarGenericAlias[ProviderGlobalId]]": (
        IdentityValueState[_NestedScalarGenericAlias[ProviderGlobalId]]
    ),
    "IdentityValueState[ExtensionsScalarGlobalNodeAlias]": IdentityValueState[
        _ExtensionsScalarGlobalNodeAlias
    ],
}
IDENTITY_ROOT_TARGETS = {
    "ProviderGlobalId": ProviderGlobalId,
    "ProviderNodeId": ProviderNodeId,
    "RepositoryScopedNumber": RepositoryScopedNumber,
}


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical_bytes(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
        + b"\n"
    )


def _assert_no_float(value: Any) -> None:
    assert not isinstance(value, float)
    if isinstance(value, list):
        for item in cast(list[Any], value):
            _assert_no_float(item)
    elif isinstance(value, dict):
        for item in cast(dict[str, Any], value).values():
            _assert_no_float(item)


def _parse_canonical_json(raw: bytes) -> dict[str, Any]:
    assert not raw.startswith(b"\xef\xbb\xbf")
    assert b"\r" not in raw
    assert raw.endswith(b"\n") and not raw.endswith(b"\n\n")
    document = json.loads(raw)
    assert isinstance(document, dict)
    _assert_no_float(document)
    assert _canonical_bytes(document) == raw
    return cast(dict[str, Any], document)


def _load_document(filename: str) -> dict[str, Any]:
    return _parse_canonical_json((CORRECTION_ROOT / filename).read_bytes())


CORRECTION = _load_document("correction.json")
REGRESSIONS = _load_document("regression-vectors.json")
REGRESSION_VECTORS = {
    cast(str, vector["id"]): vector
    for vector in cast(list[dict[str, Any]], REGRESSIONS["vectors"])
}


def _materialize_python(value: Any) -> Any:
    if isinstance(value, dict):
        mapping = cast(dict[str, Any], value)
        if set(mapping) == {"identity_type", "root"}:
            identity_type = cast(str, mapping["identity_type"])
            assert identity_type in IDENTITY_ROOT_TARGETS
            return IDENTITY_ROOT_TARGETS[identity_type].model_validate(mapping["root"])
        return {key: _materialize_python(item) for key, item in mapping.items()}
    if isinstance(value, list):
        return tuple(_materialize_python(item) for item in cast(list[Any], value))
    return value


def _validate_state_vector_input(
    model: type[BaseModel], vector: dict[str, Any]
) -> BaseModel:
    raw_input = vector["input"]
    if vector["input_mode"] == "json":
        return model.model_validate_json(json.dumps(raw_input))
    assert vector["input_mode"] == "python"
    materialized = _materialize_python(raw_input)
    assert isinstance(materialized, dict)
    materialized["state"] = IdentityFieldState(cast(str, materialized["state"]))
    return model.model_validate(materialized)


def _runtime_values(state_value: BaseModel) -> tuple[object, ...]:
    state_name = getattr(state_value, "state")
    if state_name is IdentityFieldState.CONFLICT:
        return cast(tuple[object, ...], getattr(state_value, "conflict_candidates"))
    value = getattr(state_value, "value")
    return () if value is None else (value,)


def _assert_rejected(call: Callable[[], object]) -> None:
    try:
        call()
    except ValidationError as error:
        matches = [
            item
            for item in error.errors()
            if item["loc"] == ()
            and item["type"] == "value_error"
            and all(part in item["msg"] for part in AMBIGUOUS_MESSAGE_PARTS)
        ]
        assert len(matches) == 1
        return
    raise AssertionError("ambiguous specialization unexpectedly succeeded")


def _execute_state_vector(vector: dict[str, Any]) -> None:
    target = cast(str, vector["target"])
    assert target in STATE_TARGETS
    model = STATE_TARGETS[target]
    expected = cast(dict[str, Any], vector["expected"])
    if expected["outcome"] == "rejected":
        _assert_rejected(lambda: _validate_state_vector_input(model, vector))
        return

    assert vector["operation"] == "semantic-json-round-trip"
    original = _validate_state_vector_input(model, vector)
    restored = model.model_validate_json(original.model_dump_json())
    assert (restored == original) is expected["equality"]
    assert restored.model_dump(mode="json") == expected["semantic_dump"]
    values = _runtime_values(restored)
    assert [type(item).__name__ for item in values] == expected["value_runtime_types"]
    if expected.get("candidate_roots"):
        assert [getattr(item, "root") for item in values] == expected["candidate_roots"]


def _mapping_result(vector: dict[str, Any]) -> LegacySourceLocatorMappingResult:
    raw = cast(dict[str, Any], vector["input"])
    locator = SourceLocator.model_validate_json(json.dumps(raw["legacy_locator"]))
    observation = RepositoryAliasObservation.model_validate_json(
        json.dumps(raw["repository_alias_observation"])
    )
    interpretation = LegacyObjectIdInterpretation(
        cast(str, raw["object_id_interpretation"])
    )
    return map_legacy_source_locator(
        locator,
        repository_alias_observation=observation,
        object_id_interpretation=interpretation,
    )


def _assert_mapping_expected(
    result: LegacySourceLocatorMappingResult,
    restored: LegacySourceLocatorMappingResult,
    expected: dict[str, Any],
) -> None:
    values = _runtime_values(restored.object_id_state)
    if "equality" in expected:
        assert (restored == result) is expected["equality"]
    if "semantic_dump_equal" in expected:
        assert (
            restored.model_dump(mode="json") == result.model_dump(mode="json")
        ) is expected["semantic_dump_equal"]
    if "state" in expected:
        assert restored.object_id_state.state.value == expected["state"]
    if "value_runtime_types" in expected:
        assert [type(item).__name__ for item in values] == expected[
            "value_runtime_types"
        ]
    if "candidate_roots" in expected:
        assert [getattr(item, "root") for item in values] == expected["candidate_roots"]
    if "candidate_count" in expected:
        assert len(values) == expected["candidate_count"]
    if "candidates_distinct" in expected:
        assert (values[0] != values[1]) is expected["candidates_distinct"]
    if "candidate_equality" in expected:
        assert (values[0] == values[1]) is expected["candidate_equality"]
    if "winner_selected" in expected:
        assert (restored.object_id_state.value is not None) is expected[
            "winner_selected"
        ]
    if "alternate_id_conversion" in expected:
        assert expected["alternate_id_conversion"] is False
        assert tuple(type(item) for item in values) == (
            RepositoryScopedNumber,
            ProviderGlobalId,
        )
        assert values[0] != values[1]


def _execute_mapping_vector(vector: dict[str, Any]) -> None:
    assert vector["operation"] == "legacy-mapping-round-trip"
    assert vector["target"] == "map_legacy_source_locator"
    result = _mapping_result(vector)
    restored = LegacySourceLocatorMappingResult.model_validate_json(
        result.model_dump_json()
    )
    _assert_mapping_expected(
        result,
        restored,
        cast(dict[str, Any], vector["expected"]),
    )


def _execute_regression_vector(vector: dict[str, Any]) -> None:
    if vector["target"] == "map_legacy_source_locator":
        _execute_mapping_vector(vector)
        return
    _execute_state_vector(vector)


def _validate_correction_inventory(root: Path) -> None:
    assert root.is_dir()
    paths = tuple(root.iterdir())
    assert {path.name for path in paths} == EXPECTED_CORRECTION_FILES
    for path in paths:
        assert path.is_file()
        assert not path.is_symlink()


def _validate_sidecar(filename: str, raw: bytes, root: Path = CORRECTION_ROOT) -> None:
    assert not raw.startswith(b"\xef\xbb\xbf")
    assert b"\r" not in raw
    match = re.fullmatch(rb"([0-9a-f]{64})  ([a-z-]+\.json)\n", raw)
    assert match is not None
    json_name = filename.removesuffix(".sha256") + ".json"
    assert match.group(2).decode("ascii") == json_name
    assert match.group(1).decode("ascii") == _sha256((root / json_name).read_bytes())


def _assert_locked(filename: str, raw: bytes) -> None:
    expected = EXPECTED_LOCKS[filename]
    assert len(raw) == expected.byte_length
    assert _sha256(raw) == expected.sha256


def _assert_acyclic_dag(nodes: list[dict[str, Any]]) -> None:
    predecessors = {
        cast(str, item["id"]): tuple(cast(list[str], item["predecessors"]))
        for item in nodes
    }
    assert len(predecessors) == len(nodes)
    assert all(
        predecessor in predecessors
        for values in predecessors.values()
        for predecessor in values
    )

    visited: set[str] = set()
    active: set[str] = set()

    def visit(node: str) -> None:
        assert node not in active
        if node in visited:
            return
        active.add(node)
        for predecessor in predecessors[node]:
            visit(predecessor)
        active.remove(node)
        visited.add(node)

    for node in predecessors:
        visit(node)
    assert visited == set(predecessors)


def test_exact_append_only_correction_inventory_is_present() -> None:
    _validate_correction_inventory(CORRECTION_ROOT)
    identity_root = CORRECTION_ROOT.parent.parent
    assert not (identity_root / "latest").exists()
    assert not (identity_root / "current").exists()


@pytest.mark.parametrize("filename", sorted(EXPECTED_LOCKS))
def test_independent_correction_file_digest_oracle(filename: str) -> None:
    _assert_locked(filename, (CORRECTION_ROOT / filename).read_bytes())


@pytest.mark.parametrize("filename", ("correction.json", "regression-vectors.json"))
def test_correction_json_is_canonical_and_has_exact_format(filename: str) -> None:
    document = _load_document(filename)
    expected_name = (
        "faultatlas-identity-contract-correction"
        if filename == "correction.json"
        else "faultatlas-identity-correction-regression-vectors"
    )
    assert document["format"]["name"] == expected_name
    assert document["format"]["version"] == "1"
    assert document["format"]["public_contract"] is False
    assert document["format"]["production_persistence"] is False
    assert document["format"]["canonicalization"] == {
        "array_order": "declared_contract_order",
        "encoding": "UTF-8_without_BOM",
        "exactly_one_trailing_lf": True,
        "floats_and_NaN_permitted": False,
        "keys": "sorted",
        "line_endings": "LF_only",
        "name": "json-sort-keys-compact-utf8-lf-v1",
        "whitespace": "compact",
    }


@pytest.mark.parametrize("filename", ("correction.sha256", "regression-vectors.sha256"))
def test_correction_sidecar_is_exact_and_independently_locked(filename: str) -> None:
    raw = (CORRECTION_ROOT / filename).read_bytes()
    _assert_locked(filename, raw)
    _validate_sidecar(filename, raw)


def test_correction_schema_identity_scope_and_candidate_state_are_exact() -> None:
    assert set(CORRECTION) == EXPECTED_CORRECTION_TOP_LEVEL
    assert set(REGRESSIONS) == EXPECTED_REGRESSION_TOP_LEVEL
    identity = CORRECTION["correction_identity"]
    assert identity["correction_id"] == ("s1-p01-s05-c01-ambiguous-union-round-trip")
    assert identity["slice"] == "S1.P01.S05.C01"
    assert identity["corrects_slice"] == "S1.P01.S05"
    assert identity["publication_state"] == "sealed_publication_candidate"
    assert CORRECTION["scope"]["append_only"] is True
    assert CORRECTION["scope"]["identity_v1_bytes_modified"] is False
    assert "S1.P01.S06_implementation" in CORRECTION["scope"]["non_goals"]


def test_all_nine_v1_source_locks_remain_byte_exact() -> None:
    recorded = {
        Path(cast(str, item["path"])).name: LockedFile(
            cast(int, item["byte_length"]), cast(str, item["sha256"])
        )
        for item in CORRECTION["source_locks"]["immutable_s05_v1_files"]
    }
    assert recorded == V1_LOCKS
    for filename, expected in V1_LOCKS.items():
        raw = (V1_ROOT / filename).read_bytes()
        assert len(raw) == expected.byte_length
        assert _sha256(raw) == expected.sha256


def test_source_review_and_pre_correction_locks_are_exact() -> None:
    assert CORRECTION["source_locks"]["baseline_sha"] == (
        "3edd4024848d7e60cb506358913102f1d0958e7c"
    )
    production = CORRECTION["source_locks"]["pre_correction_production_sources"]
    assert {
        item["path"]: (item["byte_length"], item["sha256"], item["git_mode"])
        for item in production
    } == {
        "src/faultatlas/domain/identity.py": (
            18543,
            "8140fdaf5f568bc491d4853f0fe39e57b995cb1d170bceea92bd45444ce01547",
            "100644",
        ),
        "src/faultatlas/domain/compatibility.py": (
            17704,
            "090f9eab04ea54daf6c9bbc970285307ed1a42cd42b3a26df5e16d74a7e506aa",
            "100644",
        ),
    }
    discussions = CORRECTION["source_locks"]["relevant_review_discussions"]
    assert [(item["pull_request"], item["thread_id"]) for item in discussions] == [
        (19, "PRRT_kwDOTa_Fi86VYvjC"),
        (21, "PRRT_kwDOTa_Fi86Vhxf1"),
        (21, "PRRT_kwDOTa_Fi86Vhxf4"),
    ]


def test_selected_resolution_is_restrictive_and_has_no_public_expansion() -> None:
    resolution = CORRECTION["selected_resolution"]
    assert resolution == {
        "alternate_id_equivalence_added": False,
        "ambiguous_scalar_root_generic_unions": "rejected",
        "compatibility_discriminator": "LegacyObjectIdInterpretation",
        "compatibility_private_carrier": True,
        "implicit_winner_added": False,
        "monomorphic_specializations": "preserved",
        "public_API_expansion": False,
        "structured_source_identity_union": "preserved",
    }


def test_assurance_corrections_name_exact_tracked_test_changes() -> None:
    assurance = CORRECTION["assurance_corrections"]
    assert assurance["whole_source_inventory"]["tracked_test_changes"] == [
        "tests/test_identity_contract_corpus.py",
        "tests/test_package.py",
    ]
    assert assurance["exact_permission_bits"]["tracked_test_changes"] == [
        "tests/test_identity_contract_corpus.py",
        "tests/test_reference_corpus_phase_closure.py",
    ]


def test_supersession_and_replacement_inventory_is_exact() -> None:
    superseded = CORRECTION["superseded_contract_vectors"]
    assert superseded["count"] == 1
    assert len(superseded["items"]) == 1
    item = superseded["items"][0]
    assert item["original_vector_id"] == SUPERSEDED_ID
    assert item["original_corpus_file"] == "valid-vectors.json"
    assert item["historical_artifact_bytes_remain_valid"] is True
    assert item["effective_status"] == "superseded_by_append_only_correction"
    assert item["replacement_regression_vector_ids"] == [REPLACEMENT_ID]
    replacement = REGRESSION_VECTORS[REPLACEMENT_ID]
    assert replacement["supersedes_v1_vector_ids"] == [SUPERSEDED_ID]
    assert len(REGRESSION_VECTORS) == 32
    assert tuple(REGRESSION_VECTORS) == EXPECTED_VECTOR_IDS


def test_regression_vector_shape_ids_registry_and_counts_are_exact() -> None:
    vectors = cast(list[dict[str, Any]], REGRESSIONS["vectors"])
    assert len(vectors) == 32
    assert REGRESSIONS["assurance"]["expected_vector_count"] == 32
    assert REGRESSIONS["assurance"]["superseded_v1_vector_count"] == 1
    for vector in vectors:
        assert set(vector) == EXPECTED_VECTOR_KEYS
        assert vector["status"] == "locked"
        assert vector["input_mode"] in {"python", "json"}
        assert vector["operation"] in {
            "construct",
            "semantic-json-round-trip",
            "legacy-mapping-round-trip",
        }
        assert vector["target"] in set(STATE_TARGETS) | {"map_legacy_source_locator"}
        assert isinstance(vector["purpose"], str) and vector["purpose"]
        assert isinstance(vector["source_finding"], str) and vector["source_finding"]


@pytest.mark.parametrize("vector_id", EXPECTED_VECTOR_IDS)
def test_each_correction_regression_vector_executes(vector_id: str) -> None:
    _execute_regression_vector(REGRESSION_VECTORS[vector_id])


def test_artifact_dag_is_known_unique_acyclic_and_append_only() -> None:
    dag = CORRECTION["replacement_contract"]["artifact_dag"]
    nodes = cast(list[dict[str, Any]], dag["nodes"])
    assert dag["root"] == "immutable-s05-v1"
    _assert_acyclic_dag(nodes)
    assert {item["id"] for item in nodes} == {
        "immutable-s05-v1",
        "regression-vectors-json",
        "regression-vectors-sidecar",
        "correction-json",
        "correction-sidecar",
        "correction-markdown",
    }
    correction_node = next(item for item in nodes if item["id"] == "correction-json")
    assert correction_node["predecessors"] == [
        "immutable-s05-v1",
        "regression-vectors-json",
    ]
    assert "sha256" not in CORRECTION["correction_identity"]


def test_effective_contract_counts_are_exact() -> None:
    assert CORRECTION["replacement_contract"]["effective_contract"] == {
        "active_v1_vectors": 167,
        "correction_vectors": 32,
        "historical_v1_vectors": 168,
        "superseded_v1_vectors": 1,
        "total_current_vectors": 199,
    }
    assert CORRECTION["assurance"]["effective_contract_vector_count"] == 199


def test_markdown_is_derived_synchronized_and_non_authoritative() -> None:
    raw = (CORRECTION_ROOT / "correction.md").read_bytes()
    _assert_locked("correction.md", raw)
    text = raw.decode("utf-8")
    assert text.count(EXPECTED_LOCKS["correction.json"].sha256) == 1
    assert text.count(EXPECTED_LOCKS["regression-vectors.json"].sha256) == 1
    for required in (
        "Internal, case-calibrated, non-public correction",
        "derived and non-authoritative",
        SUPERSEDED_ID,
        REPLACEMENT_ID,
        "whole-source assurance",
        "Git index mode `100644`",
        "filesystem mode `0644`",
        "S1.P01.S06` remains next and not started",
        "byte-for-byte immutable",
    ):
        assert required in text


def test_correction_payload_is_private_and_retains_no_credentials_or_paths() -> None:
    combined = b"\n".join(
        (CORRECTION_ROOT / filename).read_bytes()
        for filename in sorted(EXPECTED_CORRECTION_FILES)
    )
    lowered = combined.lower()
    assert b"/home/" not in lowered
    assert b"/tmp/" not in lowered
    assert b"authorization:" not in lowered
    assert b"bearer " not in lowered
    assert (
        re.search(rb"\b(?:gh[opurs]|github_pat)_[A-Za-z0-9_]{8,}\b", combined) is None
    )


@pytest.mark.parametrize(
    "model,state_name,input_mode",
    (
        (
            IdentityValueState[ProviderGlobalId | ProviderNodeId],
            "present",
            "python",
        ),
        (
            IdentityValueState[ProviderGlobalId | ProviderNodeId],
            "present",
            "json",
        ),
        (
            IdentityValueState[ProviderGlobalId | ProviderNodeId],
            "conflict",
            "python",
        ),
        (
            IdentityValueState[ProviderGlobalId | ProviderNodeId],
            "conflict",
            "json",
        ),
        (
            IdentityValueState[RepositoryScopedNumber | ProviderGlobalId],
            "present",
            "python",
        ),
        (
            IdentityValueState[RepositoryScopedNumber | ProviderGlobalId],
            "present",
            "json",
        ),
        (
            IdentityValueState[RepositoryScopedNumber | ProviderGlobalId],
            "conflict",
            "python",
        ),
        (
            IdentityValueState[RepositoryScopedNumber | ProviderGlobalId],
            "conflict",
            "json",
        ),
    ),
)
def test_direct_ambiguous_specializations_reject_before_union_selection(
    model: type[BaseModel], state_name: str, input_mode: str
) -> None:
    if state_name == "present":
        raw: dict[str, Any] = {
            "conflict_candidates": [],
            "schema_version": 1,
            "state": "present",
            "value": "4412",
        }
    else:
        raw = {
            "conflict_candidates": ["4412", "4412"],
            "schema_version": 1,
            "state": "conflict",
            "value": None,
        }
    if input_mode == "json":
        _assert_rejected(lambda: model.model_validate_json(json.dumps(raw)))
    else:
        python_raw = copy.deepcopy(raw)
        python_raw["state"] = IdentityFieldState(state_name)
        if state_name == "present":
            python_raw["value"] = ProviderGlobalId.model_validate("4412")
        else:
            python_raw["conflict_candidates"] = (
                RepositoryScopedNumber.model_validate("4412"),
                ProviderGlobalId.model_validate("4412"),
            )
        _assert_rejected(lambda: model.model_validate(python_raw))


@pytest.mark.parametrize(
    "model",
    (
        _runtime_state_model(_MonomorphicGlobalT),
        IdentityValueState[_ProviderGlobalAliasOne | _ProviderGlobalAliasTwo],
    ),
)
def test_annotation_closure_preserves_provably_monomorphic_wrappers(
    model: type[BaseModel],
) -> None:
    original = model.model_validate(
        {
            "conflict_candidates": (),
            "schema_version": 1,
            "state": IdentityFieldState.PRESENT,
            "value": ProviderGlobalId.model_validate("4412"),
        }
    )
    restored = model.model_validate_json(original.model_dump_json())
    assert restored == original
    assert type(cast(object, getattr(restored, "value"))) is ProviderGlobalId


def _assert_exact_types(
    values: tuple[object, ...], expected: tuple[type[object], ...]
) -> None:
    assert tuple(type(item) for item in values) == expected


def _assert_same_type_and_equality(original: object, restored: object) -> None:
    assert type(restored) is type(original)
    assert restored == original


def _assert_unresolved_shape(
    candidates: tuple[object, ...], selected: object | None
) -> None:
    assert selected is None
    assert len(candidates) == 2
    _assert_exact_types(
        candidates,
        (RepositoryScopedNumber, ProviderGlobalId),
    )
    assert candidates[0] != candidates[1]


@pytest.mark.parametrize(
    "mutation",
    (
        "ambiguous-first-type-restoration",
        "same-lexeme-candidate-collapse",
        "generic-rejection-removed",
        "monomorphic-type-change",
        "compatibility-interpretation-ignored",
        "unresolved-order-reversed",
        "candidate-wrappers-identical",
        "conflict-winner-inserted",
    ),
)
def test_behavior_mutation_oracle_rejects_required_failures(mutation: str) -> None:
    number = RepositoryScopedNumber.model_validate("4412")
    global_id = ProviderGlobalId.model_validate("4412")
    if mutation == "ambiguous-first-type-restoration":
        with pytest.raises(AssertionError):
            _assert_same_type_and_equality(global_id, number)
        return
    if mutation == "same-lexeme-candidate-collapse":
        with pytest.raises(AssertionError):
            _assert_unresolved_shape((global_id, global_id), None)
        return
    if mutation == "generic-rejection-removed":
        with pytest.raises(AssertionError):
            _assert_rejected(lambda: object())
        return
    if mutation == "monomorphic-type-change":
        node = ProviderNodeId.model_validate("4412")
        with pytest.raises(AssertionError):
            _assert_same_type_and_equality(node, global_id)
        return
    if mutation == "compatibility-interpretation-ignored":
        with pytest.raises(AssertionError):
            _assert_exact_types((number,), (ProviderGlobalId,))
        return
    if mutation == "unresolved-order-reversed":
        with pytest.raises(AssertionError):
            _assert_unresolved_shape((global_id, number), None)
        return
    if mutation == "candidate-wrappers-identical":
        with pytest.raises(AssertionError):
            _assert_unresolved_shape((number, number), None)
        return
    assert mutation == "conflict-winner-inserted"
    with pytest.raises(AssertionError):
        _assert_unresolved_shape((number, global_id), number)


@pytest.mark.parametrize(
    "mutation",
    (
        "coordinated-json-sidecar-reseal",
        "missing-correction-file",
        "extra-correction-file",
        "sidecar-basename",
        "dag-cycle",
        "inserted-float",
    ),
)
def test_correction_artifact_mutation_is_detected(
    mutation: str, tmp_path: Path
) -> None:
    if mutation == "coordinated-json-sidecar-reseal":
        changed = copy.deepcopy(CORRECTION)
        changed["assurance"]["status"] = "resealed"
        raw = _canonical_bytes(changed)
        sidecar = f"{_sha256(raw)}  correction.json\n".encode()
        with pytest.raises(AssertionError):
            _assert_locked("correction.json", raw)
        with pytest.raises(AssertionError):
            _assert_locked("correction.sha256", sidecar)
        return
    if mutation == "sidecar-basename":
        raw = (
            (CORRECTION_ROOT / "correction.sha256")
            .read_bytes()
            .replace(b"correction.json", b"regression-vectors.json")
        )
        with pytest.raises(AssertionError):
            _validate_sidecar("correction.sha256", raw)
        return
    if mutation == "dag-cycle":
        nodes = copy.deepcopy(
            CORRECTION["replacement_contract"]["artifact_dag"]["nodes"]
        )
        nodes[0]["predecessors"] = ["correction-json"]
        with pytest.raises(AssertionError):
            _assert_acyclic_dag(nodes)
        return
    if mutation == "inserted-float":
        changed = copy.deepcopy(CORRECTION)
        changed["assurance"]["ratio"] = 1.5
        raw = (
            json.dumps(changed, separators=(",", ":"), sort_keys=True).encode() + b"\n"
        )
        with pytest.raises(AssertionError):
            _parse_canonical_json(raw)
        return

    copied = tmp_path / "correction"
    shutil.copytree(CORRECTION_ROOT, copied)
    if mutation == "missing-correction-file":
        (copied / "correction.md").unlink()
    else:
        (copied / "unexpected.json").write_bytes(b"{}\n")
    with pytest.raises(AssertionError):
        _validate_correction_inventory(copied)
