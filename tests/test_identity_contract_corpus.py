from __future__ import annotations

import ast
import copy
import hashlib
import io
import json
import os
import re
import shutil
import stat
import subprocess
import tarfile
import zipfile
from collections import Counter
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path, PurePosixPath
from typing import Any, NoReturn, cast

import pytest
from pydantic import BaseModel, TypeAdapter, ValidationError

import faultatlas
import faultatlas.domain as domain_package
import faultatlas.domain.compatibility as compatibility_module
import faultatlas.domain.identity as identity_module
from faultatlas.domain.compatibility import (
    CompatibilityStatus,
    LegacyCompatibilityReason,
    LegacyObjectIdInterpretation,
    LegacySourceLocatorMappingResult,
    LegacySourceLocatorProjectionResult,
    map_legacy_source_locator,
    project_source_identity_to_legacy,
)
from faultatlas.domain.identity import (
    AuthorityRole,
    IdentityFieldState,
    IdentityValueState,
    NumberedSourceObjectIdentity,
    ProviderAuthority,
    ProviderGlobalId,
    ProviderKey,
    ProviderNodeId,
    ProviderRepositoryId,
    ProviderScopedSourceObjectIdentity,
    RepositoryAliasObservation,
    RepositoryIdentity,
    RepositoryScopedNumber,
    SourceIdentity,
    SourceIdentityLifecycleObservation,
    SourceIdentityLifecycleState,
    SourceObjectKind,
)
from faultatlas.domain.source import SourceLocator

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
CORPUS_ROOT = REPOSITORY_ROOT / "reference_corpus/contracts/identity/v1"
CORPUS_RELATIVE = "reference_corpus/contracts/identity/v1"
CORRECTION_RELATIVE = (
    "reference_corpus/contracts/identity/corrections/s05-c01-ambiguous-union-round-trip"
)
CORRECTION_ROOT = REPOSITORY_ROOT / CORRECTION_RELATIVE
EXPECTED_FILES = {
    "compatibility-vectors.json",
    "compatibility-vectors.sha256",
    "contract.md",
    "invalid-vectors.json",
    "invalid-vectors.sha256",
    "manifest.json",
    "manifest.sha256",
    "valid-vectors.json",
    "valid-vectors.sha256",
}
EXPECTED_CORRECTION_FILES = {
    "correction.json",
    "correction.md",
    "correction.sha256",
    "regression-vectors.json",
    "regression-vectors.sha256",
}
SUPERSEDED_V1_VECTOR_ID = "identity.valid.field-state.conflict-number-global"
EXPECTED_CORRECTION_VECTOR_COUNT = 32
EXPECTED_EFFECTIVE_VECTOR_COUNT = 199
S06_CLOSURE_RELATIVE = (
    "reference_corpus/contracts/identity/closures/s1-p01-phase-closure"
)
EXPECTED_S06_CLOSURE_FILES = {"closure.json", "closure.md", "closure.sha256"}


@dataclass(frozen=True)
class LockedFile:
    byte_length: int
    sha256: str


@dataclass(frozen=True)
class ContractVectorPlanEntry:
    source: str
    filename: str
    vector_id: str


EXPECTED_LOCKS = {
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
EXPECTED_JSON_FORMATS = {
    "manifest.json": "faultatlas-identity-contract-corpus-manifest",
    "valid-vectors.json": "faultatlas-identity-valid-contract-vectors",
    "invalid-vectors.json": "faultatlas-identity-invalid-contract-vectors",
    "compatibility-vectors.json": (
        "faultatlas-identity-compatibility-contract-vectors"
    ),
}
EXPECTED_MANIFEST_TOP_LEVEL = {
    "assurance",
    "compatibility_contract",
    "corpus_files",
    "corpus_identity",
    "execution_contract",
    "format",
    "non_goals",
    "originating_publications",
    "rejection_contract",
    "scope",
    "source_decisions",
    "target_symbols",
    "vector_summary",
}
EXPECTED_VECTOR_TOP_LEVEL = {
    "valid-vectors.json": {"assurance", "fixtures", "format", "vectors"},
    "invalid-vectors.json": {"assurance", "format", "vectors"},
    "compatibility-vectors.json": {
        "assurance",
        "fixtures",
        "format",
        "vectors",
    },
}
EXPECTED_IDENTITY_EXPORTS = {
    "AuthorityRole",
    "IdentityFieldState",
    "IdentityValueState",
    "NumberedSourceObjectIdentity",
    "ProviderAuthority",
    "ProviderGlobalId",
    "ProviderKey",
    "ProviderNodeId",
    "ProviderRepositoryId",
    "ProviderScopedSourceObjectIdentity",
    "RepositoryAliasObservation",
    "RepositoryIdentity",
    "RepositoryScopedNumber",
    "SourceIdentity",
    "SourceIdentityLifecycleObservation",
    "SourceIdentityLifecycleState",
    "SourceObjectKind",
}
EXPECTED_COMPATIBILITY_EXPORTS = {
    "CompatibilityStatus",
    "LegacyCompatibilityReason",
    "LegacyObjectIdInterpretation",
    "LegacySourceLocatorMappingResult",
    "LegacySourceLocatorProjectionResult",
    "map_legacy_source_locator",
    "project_source_identity_to_legacy",
}
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
EXPECTED_REVISION_EXPORTS = {
    "GitBlobIdentity",
    "GitCommitIdentity",
    "GitCommitParentTopology",
    "GitHashAlgorithm",
    "GitObjectIdentity",
    "GitObjectKind",
    "GitRefName",
    "GitRefNamespace",
    "GitRefObservation",
    "GitRevisionIdentity",
    "GitTreeIdentity",
    "RevisionRole",
    "RevisionRoleAssignment",
}
EXPECTED_S02_REVISION_EXPORTS = {
    "GitCommitParentTopology",
    "RevisionRole",
    "RevisionRoleAssignment",
}
EXPECTED_S03_REVISION_EXPORTS = {
    "GitRefName",
    "GitRefNamespace",
    "GitRefObservation",
}
EXPECTED_CORRECTION_PERMISSION_PATHS = {
    *(f"{CORPUS_RELATIVE}/{filename}" for filename in EXPECTED_FILES),
    *(f"{CORRECTION_RELATIVE}/{filename}" for filename in EXPECTED_CORRECTION_FILES),
    "docs/roadmap.md",
    "tests/test_identity_contract_corpus.py",
    "tests/test_identity_roundtrip_correction.py",
    "tests/test_package.py",
    "tests/test_reference_corpus_phase_closure.py",
    "tests/test_source_locator_compatibility.py",
}
EXPECTED_NEW_PERMISSION_PATHS = {
    *(f"{CORRECTION_RELATIVE}/{filename}" for filename in EXPECTED_CORRECTION_FILES),
    "tests/test_identity_roundtrip_correction.py",
}
EXPECTED_VECTOR_COUNTS = {
    "valid-vectors.json": 58,
    "invalid-vectors.json": 80,
    "compatibility-vectors.json": 30,
}
EXPECTED_CATEGORY_COUNTS = {
    "valid-vectors.json": {
        "enum": 4,
        "field-state": 16,
        "identifier": 10,
        "lifecycle": 6,
        "provider": 3,
        "repository": 8,
        "source-identity": 3,
        "source-object": 8,
    },
    "invalid-vectors.json": {
        "authority-host": 12,
        "global-and-node-id": 10,
        "identity-state": 12,
        "lifecycle": 10,
        "provider-key": 9,
        "repository-and-alias": 11,
        "repository-scoped-number": 8,
        "source-object": 8,
    },
    "compatibility-vectors.json": {
        "enum": 3,
        "legacy-mapping": 9,
        "legacy-projection": 8,
        "result-model-rejection": 10,
    },
}
EXPECTED_SOURCE_DECISIONS = {
    "reference_corpus/pytest-4412/decisions/s07-identity-revision-provenance/decision.json": (
        "60ecb66565525cb21a924508794635072ae50e935d4791d9d91da5b6399ce866",
        {
            "decision:s07:d1-provider-authority-identity",
            "decision:s07:d2-stable-repository-and-alias",
            "decision:s07:d3-provider-object-identifiers",
            "decision:s07:d6-field-state-semantics",
            "decision:s07:d8-legacy-source-locator",
        },
    ),
    "reference_corpus/pytest-4412/decisions/s08-snapshot-boundary-compatibility/decision.json": (
        "f788116f3b9ea470c370a56e55eb6f37e05be200f285ac9f2572c641215f5f40",
        {
            "decision:s08:d5-legacy-to-future-mapping",
            "decision:s08:d6-future-to-legacy-projection",
            "decision:s08:d7-compatibility-status-vocabulary",
            "decision:s08:d8-independent-contract-versioning",
            "decision:s08:d9-semantic-versus-canonical-bytes",
        },
    ),
}
EXPECTED_NON_GOALS = {
    "Evidence_Envelope",
    "Git_object_identity",
    "S1.P01.S06_implementation",
    "actor_identity",
    "alternate_identifier_binding",
    "conflict_resolution",
    "locator_implementation",
    "migration",
    "persistence",
    "production_reader_or_validator",
    "public_API",
    "ref_observation",
    "revision_qualified_path",
    "universal_multi_provider_behavior",
}
EXPECTED_PUBLICATIONS = [
    ("S1.P01.S01", 17, "59e312d3412d92cb3cf0fc3721c04189413998be"),
    ("S1.P01.S02", 18, "87060eaf9b16878581e4c6094e2a8d75ad827ed2"),
    ("S1.P01.S03", 19, "26f7bf75b5a25c0f9f9a6f19796719b554b4d4d7"),
    ("S1.P01.S04", 20, "05736e1bdde72eeb4431b11448db4ed7f8e3b36c"),
    (
        "S1.P01.S05",
        "established_after_publication",
        "established_after_publication",
    ),
]
VECTOR_ID_PATTERN = re.compile(
    r"^identity\.(?:valid|invalid|compatibility)\.[a-z0-9-]+(?:\.[a-z0-9-]+)+$"
)
FIXTURE_ID_PATTERN = re.compile(
    r"^identity\.fixture\.(?:valid|compatibility)\.[a-z0-9-]+(?:\.[a-z0-9-]+)*$"
)

MODEL_TARGETS: dict[str, type[BaseModel]] = {
    "IdentityValueState": IdentityValueState,
    "LegacySourceLocatorMappingResult": LegacySourceLocatorMappingResult,
    "LegacySourceLocatorProjectionResult": LegacySourceLocatorProjectionResult,
    "NumberedSourceObjectIdentity": NumberedSourceObjectIdentity,
    "ProviderAuthority": ProviderAuthority,
    "ProviderGlobalId": ProviderGlobalId,
    "ProviderKey": ProviderKey,
    "ProviderNodeId": ProviderNodeId,
    "ProviderRepositoryId": ProviderRepositoryId,
    "ProviderScopedSourceObjectIdentity": ProviderScopedSourceObjectIdentity,
    "RepositoryAliasObservation": RepositoryAliasObservation,
    "RepositoryIdentity": RepositoryIdentity,
    "RepositoryScopedNumber": RepositoryScopedNumber,
    "SourceIdentityLifecycleObservation": SourceIdentityLifecycleObservation,
    "SourceLocator": SourceLocator,
}
ENUM_TARGETS: dict[str, type[StrEnum]] = {
    "AuthorityRole": AuthorityRole,
    "CompatibilityStatus": CompatibilityStatus,
    "IdentityFieldState": IdentityFieldState,
    "LegacyCompatibilityReason": LegacyCompatibilityReason,
    "LegacyObjectIdInterpretation": LegacyObjectIdInterpretation,
    "SourceIdentityLifecycleState": SourceIdentityLifecycleState,
    "SourceObjectKind": SourceObjectKind,
}
STATE_TARGETS: dict[str, type[IdentityValueState[Any]]] = {
    "NumberedSourceObjectIdentity": IdentityValueState[NumberedSourceObjectIdentity],
    "ProviderGlobalId": IdentityValueState[ProviderGlobalId],
    "ProviderNodeId": IdentityValueState[ProviderNodeId],
    "ProviderScopedSourceObjectIdentity": IdentityValueState[
        ProviderScopedSourceObjectIdentity
    ],
    "RepositoryIdentity": IdentityValueState[RepositoryIdentity],
    "RepositoryScopedNumber": IdentityValueState[RepositoryScopedNumber],
    "RepositoryScopedNumber|ProviderGlobalId": IdentityValueState[
        RepositoryScopedNumber | ProviderGlobalId
    ],
    "SourceIdentity": IdentityValueState[SourceIdentity],
}
SOURCE_IDENTITY_ADAPTER: TypeAdapter[SourceIdentity] = TypeAdapter(SourceIdentity)
KNOWN_OPERATIONS = {
    "compare_alias_independence",
    "construct",
    "construct_state_with_wrong_typed_value",
    "enum_values",
    "map_legacy_source_locator",
    "mutate_identity_state",
    "mutate_lifecycle_state",
    "mutate_numbered_identity_kind",
    "project_source_identity_to_legacy",
    "revalidate_constructed_numbered_identity",
    "validate_compatibility_result",
    "validate_type_alias",
}


def _validate_operation_target(vector: dict[str, Any]) -> None:
    operation = vector["operation"]
    target = vector["target_symbol"]
    if operation == "construct":
        assert target in MODEL_TARGETS
    elif operation == "enum_values":
        assert target in ENUM_TARGETS
    elif operation == "compare_alias_independence":
        assert target == "RepositoryIdentity"
    elif operation == "validate_type_alias":
        assert target == "SourceIdentity"
    elif operation in {
        "mutate_numbered_identity_kind",
        "revalidate_constructed_numbered_identity",
    }:
        assert target == "NumberedSourceObjectIdentity"
    elif operation in {
        "construct_state_with_wrong_typed_value",
        "mutate_identity_state",
    }:
        assert target == "IdentityValueState"
    elif operation == "mutate_lifecycle_state":
        assert target == "SourceIdentityLifecycleObservation"
    elif operation == "map_legacy_source_locator":
        assert target == "map_legacy_source_locator"
    elif operation == "project_source_identity_to_legacy":
        assert target == "project_source_identity_to_legacy"
    else:
        assert operation == "validate_compatibility_result"
        assert target in {
            "LegacySourceLocatorMappingResult",
            "LegacySourceLocatorProjectionResult",
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


def _reject_number(value: str) -> NoReturn:
    raise AssertionError(f"floating-point value is forbidden: {value}")


def _assert_no_float(value: Any) -> None:
    if isinstance(value, float):
        raise AssertionError("floating-point value is forbidden")
    if isinstance(value, list):
        for item in cast(list[Any], value):
            _assert_no_float(item)
    elif isinstance(value, dict):
        for item in cast(dict[str, Any], value).values():
            _assert_no_float(item)


def _all_strings(value: Any) -> set[str]:
    if isinstance(value, str):
        return {value}
    if isinstance(value, list):
        return {
            item for child in cast(list[Any], value) for item in _all_strings(child)
        }
    if isinstance(value, dict):
        return {
            item
            for child in cast(dict[str, Any], value).values()
            for item in _all_strings(child)
        }
    return set()


def _parse_canonical_json(raw: bytes) -> dict[str, Any]:
    assert raw.startswith(b"\xef\xbb\xbf") is False
    assert b"\r" not in raw
    assert raw.endswith(b"\n")
    assert not raw.endswith(b"\n\n")
    text = raw.decode("utf-8")
    value = json.loads(
        text,
        parse_float=_reject_number,
        parse_constant=_reject_number,
    )
    assert isinstance(value, dict)
    document = cast(dict[str, Any], value)
    _assert_no_float(document)
    assert _canonical_bytes(document) == raw
    return document


def _load_document(filename: str) -> dict[str, Any]:
    return _parse_canonical_json((CORPUS_ROOT / filename).read_bytes())


def _load_correction_document(filename: str) -> dict[str, Any]:
    return _parse_canonical_json((CORRECTION_ROOT / filename).read_bytes())


def _json_input(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    )


def _fixture_map(document: dict[str, Any]) -> dict[str, dict[str, Any]]:
    raw_fixtures = document.get("fixtures", [])
    assert isinstance(raw_fixtures, list)
    fixtures: dict[str, dict[str, Any]] = {}
    for raw_fixture in cast(list[Any], raw_fixtures):
        assert isinstance(raw_fixture, dict)
        fixture = cast(dict[str, Any], raw_fixture)
        assert set(fixture) == {"id", "status", "value"}
        fixture_id = fixture["id"]
        assert isinstance(fixture_id, str)
        assert FIXTURE_ID_PATTERN.fullmatch(fixture_id) is not None
        assert fixture["status"] == "locked"
        assert fixture_id not in fixtures
        fixtures[fixture_id] = fixture
    return fixtures


def _resolve_value(
    value: Any,
    fixtures: dict[str, dict[str, Any]],
    stack: tuple[str, ...] = (),
) -> Any:
    if isinstance(value, dict):
        mapping = cast(dict[str, Any], value)
        if "fixture_ref" in mapping:
            assert set(mapping) == {"fixture_ref"}
            fixture_id = mapping["fixture_ref"]
            assert isinstance(fixture_id, str)
            assert fixture_id in fixtures
            assert fixture_id not in stack
            return _resolve_value(
                fixtures[fixture_id]["value"], fixtures, (*stack, fixture_id)
            )
        return {
            key: _resolve_value(item, fixtures, stack) for key, item in mapping.items()
        }
    if isinstance(value, list):
        return [
            _resolve_value(item, fixtures, stack) for item in cast(list[Any], value)
        ]
    return value


def _validate_fixture_graph(document: dict[str, Any]) -> None:
    fixtures = _fixture_map(document)
    for fixture_id, fixture in fixtures.items():
        _resolve_value(fixture["value"], fixtures, (fixture_id,))
    for vector in _vectors(document):
        _resolve_value(vector["input"], fixtures)


def _vectors(document: dict[str, Any]) -> list[dict[str, Any]]:
    raw_vectors = document["vectors"]
    assert isinstance(raw_vectors, list)
    vectors: list[dict[str, Any]] = []
    for raw_vector in cast(list[Any], raw_vectors):
        assert isinstance(raw_vector, dict)
        vectors.append(cast(dict[str, Any], raw_vector))
    return vectors


def _vector_by_id(document: dict[str, Any], vector_id: str) -> dict[str, Any]:
    matches = [vector for vector in _vectors(document) if vector["id"] == vector_id]
    assert len(matches) == 1
    return matches[0]


def _build_effective_contract_plan(
    v1_documents: dict[str, dict[str, Any]],
    correction: dict[str, Any],
    regressions: dict[str, Any],
) -> tuple[ContractVectorPlanEntry, ...]:
    assert set(v1_documents) == {
        "valid-vectors.json",
        "invalid-vectors.json",
        "compatibility-vectors.json",
    }
    historical: dict[str, tuple[str, dict[str, Any]]] = {}
    for filename, document in v1_documents.items():
        for vector in _vectors(document):
            vector_id = cast(str, vector["id"])
            assert vector_id not in historical
            historical[vector_id] = (filename, vector)
    assert len(historical) == 168

    correction_vectors = _vectors(regressions)
    correction_by_id: dict[str, dict[str, Any]] = {}
    for vector in correction_vectors:
        vector_id = cast(str, vector["id"])
        assert vector_id not in historical
        assert vector_id not in correction_by_id
        correction_by_id[vector_id] = vector
    assert len(correction_by_id) == EXPECTED_CORRECTION_VECTOR_COUNT

    supersession = correction["superseded_contract_vectors"]
    items = cast(list[dict[str, Any]], supersession["items"])
    assert supersession["count"] == len(items)
    superseded_ids: set[str] = set()
    forward_replacements: dict[str, set[str]] = {}
    for item in items:
        original_id = cast(str, item["original_vector_id"])
        original_file = cast(str, item["original_corpus_file"])
        assert original_id not in superseded_ids
        assert original_id in historical
        assert historical[original_id][0] == original_file
        assert item["historical_artifact_bytes_remain_valid"] is True
        assert item["effective_status"] == "superseded_by_append_only_correction"
        replacements = cast(list[str], item["replacement_regression_vector_ids"])
        assert replacements
        assert len(replacements) == len(set(replacements))
        assert all(replacement in correction_by_id for replacement in replacements)
        superseded_ids.add(original_id)
        forward_replacements[original_id] = set(replacements)

    reverse_replacements: dict[str, set[str]] = {
        original_id: set() for original_id in superseded_ids
    }
    for replacement_id, vector in correction_by_id.items():
        reverse_ids = cast(list[str], vector["supersedes_v1_vector_ids"])
        assert len(reverse_ids) == len(set(reverse_ids))
        for original_id in reverse_ids:
            assert original_id in reverse_replacements
            reverse_replacements[original_id].add(replacement_id)
    assert reverse_replacements == forward_replacements

    active_ids = set(historical) - superseded_ids
    assert active_ids.isdisjoint(superseded_ids)
    assert active_ids | superseded_ids == set(historical)
    assert len(active_ids) == 167
    assert superseded_ids == {SUPERSEDED_V1_VECTOR_ID}

    plan: list[ContractVectorPlanEntry] = []
    for filename, document in v1_documents.items():
        plan.extend(
            ContractVectorPlanEntry("active_v1", filename, cast(str, vector["id"]))
            for vector in _vectors(document)
            if vector["id"] in active_ids
        )
    plan.extend(
        ContractVectorPlanEntry(
            "append_only_correction",
            "regression-vectors.json",
            cast(str, vector["id"]),
        )
        for vector in correction_vectors
    )
    assert len(plan) == EXPECTED_EFFECTIVE_VECTOR_COUNT
    assert correction["replacement_contract"]["effective_contract"] == {
        "active_v1_vectors": 167,
        "correction_vectors": 32,
        "historical_v1_vectors": 168,
        "superseded_v1_vectors": 1,
        "total_current_vectors": 199,
    }
    return tuple(plan)


def _model_for_vector(vector: dict[str, Any]) -> type[BaseModel]:
    symbol = vector["target_symbol"]
    assert isinstance(symbol, str)
    if symbol == "IdentityValueState" and vector["target_variant"] is not None:
        variant = vector["target_variant"]
        assert isinstance(variant, str)
        assert variant in STATE_TARGETS
        return STATE_TARGETS[variant]
    assert symbol in MODEL_TARGETS
    return MODEL_TARGETS[symbol]


def _validate_model(model: type[BaseModel], value: Any, input_mode: str) -> BaseModel:
    if input_mode == "json":
        return model.model_validate_json(_json_input(value))
    assert input_mode == "python"
    return model.model_validate(value)


def _semantic_dump(value: BaseModel) -> Any:
    return value.model_dump(mode="json")


def _round_trip(model: type[BaseModel], value: BaseModel) -> None:
    reconstructed = model.model_validate_json(value.model_dump_json())
    assert reconstructed == value
    assert reconstructed.model_dump(mode="json") == value.model_dump(mode="json")


def _execute_valid_vector(vector: dict[str, Any], document: dict[str, Any]) -> None:
    fixtures = _fixture_map(document)
    value = _resolve_value(vector["input"], fixtures)
    operation = vector["operation"]
    symbol = vector["target_symbol"]
    expected = cast(dict[str, Any], vector["expected"])
    assert set(expected) == {"outcome", "runtime_type", "semantic_dump"}
    assert expected["outcome"] == "accepted"

    if operation == "enum_values":
        assert symbol in ENUM_TARGETS
        actual = [item.value for item in ENUM_TARGETS[symbol]]
        runtime_value: Any = actual
    elif operation == "compare_alias_independence":
        assert symbol == "RepositoryIdentity"
        assert isinstance(value, dict)
        raw = cast(dict[str, Any], value)
        first = RepositoryAliasObservation.model_validate_json(
            _json_input(raw["first"])
        )
        second = RepositoryAliasObservation.model_validate_json(
            _json_input(raw["second"])
        )
        actual = {
            "aliases_excluded": "observed_alias"
            not in type(first.repository_identity).model_fields,
            "stable_identity_equal": (
                first.repository_identity == second.repository_identity
            ),
        }
        runtime_value = actual
    elif operation == "validate_type_alias":
        assert symbol == "SourceIdentity"
        source_identity = SOURCE_IDENTITY_ADAPTER.validate_json(_json_input(value))
        actual = SOURCE_IDENTITY_ADAPTER.dump_python(source_identity, mode="json")
        runtime_value = source_identity
        reconstructed = SOURCE_IDENTITY_ADAPTER.validate_json(
            SOURCE_IDENTITY_ADAPTER.dump_json(source_identity)
        )
        assert reconstructed == source_identity
    else:
        assert operation == "construct"
        model = _model_for_vector(vector)
        result = _validate_model(model, value, cast(str, vector["input_mode"]))
        actual = _semantic_dump(result)
        runtime_value = result
        _round_trip(model, result)

    assert type(runtime_value).__name__ == expected["runtime_type"]
    assert actual == expected["semantic_dump"]


def _invoke_invalid_vector(vector: dict[str, Any], document: dict[str, Any]) -> None:
    value = _resolve_value(vector["input"], _fixture_map(document))
    operation = vector["operation"]
    if operation == "construct":
        model = _model_for_vector(vector)
        _validate_model(model, value, cast(str, vector["input_mode"]))
        return
    if operation == "mutate_numbered_identity_kind":
        assert vector["target_symbol"] == "NumberedSourceObjectIdentity"
        assert vector["input_mode"] == "python"
        assert isinstance(value, dict)
        raw = cast(dict[str, Any], value)
        assert set(raw) == {"base", "mutation"}
        mutation = cast(dict[str, Any], raw["mutation"])
        assert mutation == {"field": "kind", "value": "pull_request"}
        identity = NumberedSourceObjectIdentity.model_validate_json(
            _json_input(raw["base"])
        )
        identity.kind = SourceObjectKind(cast(str, mutation["value"]))
        return
    if operation == "revalidate_constructed_numbered_identity":
        assert vector["target_symbol"] == "NumberedSourceObjectIdentity"
        assert vector["input_mode"] == "python"
        assert isinstance(value, dict)
        raw = cast(dict[str, Any], value)
        assert set(raw) == {"base", "constructed_repository_scoped_number_root"}
        base = NumberedSourceObjectIdentity.model_validate_json(
            _json_input(raw["base"])
        )
        constructed_root = raw["constructed_repository_scoped_number_root"]
        assert isinstance(constructed_root, str)
        invalid_number = RepositoryScopedNumber.model_construct(root=constructed_root)
        NumberedSourceObjectIdentity(
            repository_identity=base.repository_identity,
            kind=base.kind,
            repository_scoped_number=invalid_number,
            schema_version=base.schema_version,
        )
        return
    if operation == "construct_state_with_wrong_typed_value":
        assert vector["target_symbol"] == "IdentityValueState"
        assert vector["target_variant"] == "ProviderGlobalId"
        assert vector["input_mode"] == "python"
        assert isinstance(value, dict)
        raw = cast(dict[str, Any], value)
        assert set(raw) == {"base", "typed_value"}
        base = cast(dict[str, Any], raw["base"])
        typed_value = cast(dict[str, Any], raw["typed_value"])
        assert set(base) == {"conflict_candidates", "schema_version", "state", "value"}
        assert base["value"] is None
        assert typed_value["target_symbol"] == "ProviderNodeId"
        model = _model_for_vector(vector)
        model.model_validate(
            {
                "conflict_candidates": tuple(base["conflict_candidates"]),
                "schema_version": base["schema_version"],
                "state": IdentityFieldState(cast(str, base["state"])),
                "value": ProviderNodeId.model_validate(typed_value["value"]),
            }
        )
        return
    if operation == "mutate_identity_state":
        assert vector["target_symbol"] == "IdentityValueState"
        assert vector["input_mode"] == "python"
        assert isinstance(value, dict)
        raw = cast(dict[str, Any], value)
        assert set(raw) == {"base", "mutation"}
        mutation = cast(dict[str, Any], raw["mutation"])
        assert mutation == {"field": "state", "value": "unknown"}
        state = _model_for_vector(vector).model_validate_json(_json_input(raw["base"]))
        assert isinstance(state, IdentityValueState)
        state.state = IdentityFieldState(cast(str, mutation["value"]))
        return
    if operation == "mutate_lifecycle_state":
        assert vector["target_symbol"] == "SourceIdentityLifecycleObservation"
        assert vector["input_mode"] == "python"
        assert isinstance(value, dict)
        raw = cast(dict[str, Any], value)
        assert set(raw) == {"base", "mutation"}
        mutation = cast(dict[str, Any], raw["mutation"])
        assert mutation == {"field": "state", "value": "unknown"}
        observation = SourceIdentityLifecycleObservation.model_validate_json(
            _json_input(raw["base"])
        )
        observation.state = SourceIdentityLifecycleState(cast(str, mutation["value"]))
        return
    raise AssertionError(f"unknown invalid-vector operation: {operation!r}")


def _assert_invalid_vector(vector: dict[str, Any], document: dict[str, Any]) -> None:
    expected = cast(dict[str, Any], vector["expected"])
    assert set(expected) in (
        {"error_location", "error_type", "failure_category", "outcome"},
        {
            "error_location",
            "error_type",
            "failure_category",
            "message_contains",
            "outcome",
        },
    )
    assert expected["outcome"] == "rejected"
    assert expected["failure_category"] == "pydantic_validation_error"
    try:
        _invoke_invalid_vector(vector, document)
    except ValidationError as error:
        expected_location = tuple(cast(list[str | int], expected["error_location"]))
        expected_type = expected["error_type"]
        message = expected.get("message_contains")
        matches = [
            item
            for item in error.errors()
            if item["loc"] == expected_location
            and item["type"] == expected_type
            and (message is None or cast(str, message) in item["msg"])
        ]
        assert matches, (
            f"{vector['id']} expected {expected_location!r}/{expected_type!r}/"
            f"{message!r}, got {error.errors()!r}"
        )
        return
    raise AssertionError(f"invalid vector unexpectedly succeeded: {vector['id']}")


def _execute_compatibility_vector(
    vector: dict[str, Any], document: dict[str, Any]
) -> None:
    value = _resolve_value(vector["input"], _fixture_map(document))
    expected = cast(dict[str, Any], vector["expected"])
    operation = vector["operation"]
    if operation == "enum_values":
        symbol = cast(str, vector["target_symbol"])
        assert symbol in ENUM_TARGETS
        assert set(expected) == {"outcome", "runtime_type", "semantic_dump"}
        assert expected["outcome"] == "accepted"
        actual = [item.value for item in ENUM_TARGETS[symbol]]
        assert type(actual).__name__ == expected["runtime_type"]
        assert actual == expected["semantic_dump"]
        return
    if operation == "validate_compatibility_result":
        assert vector["target_symbol"] in {
            "LegacySourceLocatorMappingResult",
            "LegacySourceLocatorProjectionResult",
        }
        assert set(expected) in (
            {"error_location", "error_type", "failure_category", "outcome"},
            {
                "error_location",
                "error_type",
                "failure_category",
                "message_contains",
                "outcome",
            },
        )
        assert expected["outcome"] == "rejected"
        assert expected["failure_category"] == "compatibility_result_invariant"
        assert isinstance(value, dict)
        raw = cast(dict[str, Any], value)
        data = copy.deepcopy(cast(dict[str, Any], raw["base"]))
        data.update(cast(dict[str, Any], raw["overrides"]))
        model = _model_for_vector(vector)
        try:
            model.model_validate_json(_json_input(data))
        except ValidationError as error:
            expected_location = tuple(cast(list[str | int], expected["error_location"]))
            matches = [
                item
                for item in error.errors()
                if item["loc"] == expected_location
                and item["type"] == expected["error_type"]
                and (
                    "message_contains" not in expected
                    or cast(str, expected["message_contains"]) in item["msg"]
                )
            ]
            assert matches, f"{vector['id']}: {error.errors()!r}"
            return
        raise AssertionError(
            f"invalid compatibility result unexpectedly succeeded: {vector['id']}"
        )

    assert isinstance(value, dict)
    raw_input = cast(dict[str, Any], value)
    if operation == "map_legacy_source_locator":
        assert vector["target_symbol"] == "map_legacy_source_locator"
        assert set(expected) == {
            "candidate_runtime_types",
            "mapped_identity_present",
            "outcome",
            "reasons",
            "runtime_type",
            "semantic_dump",
            "status",
            "winner_selected",
        }
        assert expected["winner_selected"] is False
        locator = SourceLocator.model_validate_json(
            _json_input(raw_input["legacy_locator"])
        )
        alias = RepositoryAliasObservation.model_validate_json(
            _json_input(raw_input["repository_alias_observation"])
        )
        interpretation = LegacyObjectIdInterpretation(
            cast(str, raw_input["object_id_interpretation"])
        )
        result = map_legacy_source_locator(
            locator,
            repository_alias_observation=alias,
            object_id_interpretation=interpretation,
        )
        runtime_values = (
            result.object_id_state.conflict_candidates
            if result.object_id_state.state is IdentityFieldState.CONFLICT
            else (result.object_id_state.value,)
        )
        runtime_types = [type(item).__name__ for item in runtime_values]
        assert runtime_types == expected["candidate_runtime_types"]
        assert (result.mapped_identity is not None) is expected[
            "mapped_identity_present"
        ]
        if result.object_id_state.state is IdentityFieldState.CONFLICT:
            assert result.object_id_state.value is None
        assert result.status.value == expected["status"]
        assert [reason.value for reason in result.reasons] == expected["reasons"]
    else:
        assert operation == "project_source_identity_to_legacy"
        assert vector["target_symbol"] == "project_source_identity_to_legacy"
        assert set(expected) == {
            "outcome",
            "projected_locator_present",
            "reasons",
            "runtime_type",
            "semantic_dump",
            "status",
        }
        source_identity = SOURCE_IDENTITY_ADAPTER.validate_json(
            _json_input(raw_input["source_identity"])
        )
        alias = RepositoryAliasObservation.model_validate_json(
            _json_input(raw_input["repository_alias_observation"])
        )
        result = project_source_identity_to_legacy(
            source_identity,
            repository_alias_observation=alias,
        )
        assert (result.projected_locator is not None) is expected[
            "projected_locator_present"
        ]
        assert result.status.value == expected["status"]
        assert [reason.value for reason in result.reasons] == expected["reasons"]

    assert expected["outcome"] == "accepted"
    assert type(result).__name__ == expected["runtime_type"]
    assert result.model_dump(mode="json") == expected["semantic_dump"]
    reconstructed = type(result).model_validate_json(result.model_dump_json())
    assert reconstructed == result


def _validate_vector_shape_and_ids(documents: dict[str, dict[str, Any]]) -> None:
    vector_ids: list[str] = []
    fixture_ids: list[str] = []
    declared_decision_ids = {
        decision_id
        for _, decision_ids in EXPECTED_SOURCE_DECISIONS.values()
        for decision_id in decision_ids
    }
    for filename, document in documents.items():
        vectors = _vectors(document)
        assert len(vectors) == EXPECTED_VECTOR_COUNTS[filename]
        assert Counter(cast(str, vector["category"]) for vector in vectors) == Counter(
            EXPECTED_CATEGORY_COUNTS[filename]
        )
        for vector in vectors:
            assert set(vector) == {
                "category",
                "decision_references",
                "expected",
                "id",
                "input",
                "input_mode",
                "operation",
                "purpose",
                "rationale",
                "status",
                "target_symbol",
                "target_variant",
            }
            vector_id = vector["id"]
            assert isinstance(vector_id, str)
            assert VECTOR_ID_PATTERN.fullmatch(vector_id) is not None
            assert vector["status"] == "locked"
            assert vector["input_mode"] in {"python", "json"}
            assert isinstance(vector["purpose"], str) and vector["purpose"]
            assert isinstance(vector["rationale"], str) and vector["rationale"]
            assert vector["operation"] in KNOWN_OPERATIONS
            decision_references = vector["decision_references"]
            assert isinstance(decision_references, list) and decision_references
            assert all(
                isinstance(item, str) and item in declared_decision_ids
                for item in cast(list[Any], decision_references)
            )
            _validate_operation_target(vector)
            vector_ids.append(vector_id)
        fixture_ids.extend(_fixture_map(document))
    assert len(vector_ids) == len(set(vector_ids)) == 168
    assert len(fixture_ids) == len(set(fixture_ids)) == 26


def _validate_registry_and_coverage(
    documents: dict[str, dict[str, Any]],
) -> None:
    targets = {
        cast(str, vector["target_symbol"])
        for document in documents.values()
        for vector in _vectors(document)
    }
    allowed = (
        set(MODEL_TARGETS)
        | set(ENUM_TARGETS)
        | {
            "SourceIdentity",
            "map_legacy_source_locator",
            "project_source_identity_to_legacy",
        }
    )
    assert targets <= allowed
    assert EXPECTED_IDENTITY_EXPORTS <= targets
    assert EXPECTED_COMPATIBILITY_EXPORTS <= targets
    assert set(identity_module.__all__) == EXPECTED_IDENTITY_EXPORTS
    assert set(compatibility_module.__all__) == EXPECTED_COMPATIBILITY_EXPORTS
    assert faultatlas.__all__ == ["__version__"]
    assert EXPECTED_IDENTITY_EXPORTS.isdisjoint(vars(faultatlas))
    assert EXPECTED_COMPATIBILITY_EXPORTS.isdisjoint(vars(faultatlas))
    assert EXPECTED_IDENTITY_EXPORTS.isdisjoint(vars(domain_package))
    assert EXPECTED_COMPATIBILITY_EXPORTS.isdisjoint(vars(domain_package))


def _validate_sidecar(filename: str, raw: bytes) -> None:
    assert raw.startswith(b"\xef\xbb\xbf") is False
    assert b"\r" not in raw
    assert raw.endswith(b"\n")
    assert not raw.endswith(b"\n\n")
    text = raw.decode("ascii")
    match = re.fullmatch(r"([0-9a-f]{64})  ([a-z-]+\.json)\n", text)
    assert match is not None
    expected_json = filename.removesuffix(".sha256") + ".json"
    assert match.group(2) == expected_json
    assert match.group(1) == _sha256((CORPUS_ROOT / expected_json).read_bytes())


def _assert_locked_bytes(filename: str, raw: bytes) -> None:
    expected = EXPECTED_LOCKS[filename]
    assert len(raw) == expected.byte_length
    assert _sha256(raw) == expected.sha256


def _validate_corpus_inventory(corpus_root: Path) -> None:
    assert corpus_root.is_dir()
    paths = tuple(corpus_root.iterdir())
    assert {path.name for path in paths} == EXPECTED_FILES
    for path in paths:
        relative = path.relative_to(corpus_root.parent.parent.parent.parent)
        assert path.is_file()
        assert not path.is_symlink()
        assert stat.S_IMODE(path.stat().st_mode) & 0o111 == 0
        assert all(part not in {"", ".", ".."} for part in relative.parts)
    identity_contract_root = corpus_root.parent
    assert {path.name for path in identity_contract_root.iterdir()} == {
        "closures",
        "corrections",
        "v1",
    }
    corrections = identity_contract_root / "corrections"
    assert {path.name for path in corrections.iterdir()} == {
        "s05-c01-ambiguous-union-round-trip"
    }
    closure_root = identity_contract_root / "closures"
    assert {path.name for path in closure_root.iterdir()} == {"s1-p01-phase-closure"}
    closure = closure_root / "s1-p01-phase-closure"
    assert {path.name for path in closure.iterdir()} == EXPECTED_S06_CLOSURE_FILES
    assert all(path.is_file() and not path.is_symlink() for path in closure.iterdir())
    assert not any(
        path.name.casefold() in {"latest", "current"}
        for path in identity_contract_root.rglob("*")
    )


def _validate_manifest(
    manifest: dict[str, Any], documents: dict[str, dict[str, Any]]
) -> None:
    assert set(manifest) == EXPECTED_MANIFEST_TOP_LEVEL
    assert manifest["format"]["name"] == EXPECTED_JSON_FORMATS["manifest.json"]
    assert manifest["format"]["version"] == "1"
    assert manifest["corpus_identity"]["future_version_owner"] == "S1.P10"
    assert manifest["corpus_identity"]["originating_slice"] == "S1.P01.S05"
    assert manifest["scope"]["package_exclusion_required"] is True
    assert manifest["execution_contract"]["network_required"] is False
    assert manifest["execution_contract"]["production_reader"] is False
    assert manifest["execution_contract"]["dynamic_import_from_corpus"] is False
    assert manifest["execution_contract"]["eval"] is False
    assert manifest["execution_contract"]["exec"] is False
    assert (
        manifest["execution_contract"]["runtime_type_semantics"]
        == "exact_type_name_of_executor_result"
    )
    assert manifest["format"]["created_at"] == "2026-07-31T19:37:40Z"
    assert manifest["format"]["sealed_at"] == "2026-07-31T19:37:40Z"
    assert set(manifest["non_goals"]) == EXPECTED_NON_GOALS
    assert manifest["corpus_files"]["exact_inventory"] == [
        "manifest.json",
        "manifest.sha256",
        "valid-vectors.json",
        "valid-vectors.sha256",
        "invalid-vectors.json",
        "invalid-vectors.sha256",
        "compatibility-vectors.json",
        "compatibility-vectors.sha256",
        "contract.md",
    ]
    referenced_corpus_paths = [
        cast(str, item["path"])
        for group in ("manifest_files", "derived_files")
        for item in cast(list[dict[str, Any]], manifest["corpus_files"][group])
    ]
    for relative in referenced_corpus_paths:
        path = REPOSITORY_ROOT / relative
        assert path.is_file()
        assert path.parent == CORPUS_ROOT
    assert "sha256" not in manifest["corpus_files"]["manifest_files"][0]
    vector_locks = {
        Path(cast(str, item["path"])).name: item
        for item in cast(list[dict[str, Any]], manifest["corpus_files"]["vector_files"])
    }
    assert set(vector_locks) == {
        "valid-vectors.json",
        "invalid-vectors.json",
        "compatibility-vectors.json",
    }
    for filename, item in vector_locks.items():
        raw = (CORPUS_ROOT / filename).read_bytes()
        sidecar_name = filename.removesuffix(".json") + ".sha256"
        sidecar_raw = (CORPUS_ROOT / sidecar_name).read_bytes()
        assert item["sha256"] == _sha256(raw)
        assert item["byte_length"] == len(raw)
        assert item["sidecar"]["sha256"] == _sha256(sidecar_raw)
        assert item["sidecar"]["byte_length"] == len(sidecar_raw)
        assert item["path"] == f"{CORPUS_RELATIVE}/{filename}"
        assert item["sidecar"]["path"] == f"{CORPUS_RELATIVE}/{sidecar_name}"
    summary = manifest["vector_summary"]
    for label, filename in (
        ("valid", "valid-vectors.json"),
        ("invalid", "invalid-vectors.json"),
        ("compatibility", "compatibility-vectors.json"),
    ):
        vectors = _vectors(documents[filename])
        assert summary[label]["count"] == len(vectors)
        assert summary[label]["category_counts"] == EXPECTED_CATEGORY_COUNTS[filename]
    assert summary["total_vector_count"] == 168
    assert set(manifest["target_symbols"]["identity_module"]) == (
        EXPECTED_IDENTITY_EXPORTS
    )
    assert set(manifest["target_symbols"]["compatibility_module"]) == (
        EXPECTED_COMPATIBILITY_EXPORTS
    )
    assert manifest["target_symbols"]["legacy"] == ["SourceLocator"]
    source_decisions = cast(list[dict[str, Any]], manifest["source_decisions"])
    observed_source_decisions = {
        cast(str, item["path"]): (
            cast(str, item["sha256"]),
            set(cast(list[str], item["decision_ids"])),
        )
        for item in source_decisions
    }
    assert observed_source_decisions == EXPECTED_SOURCE_DECISIONS
    for relative, (expected_digest, expected_ids) in EXPECTED_SOURCE_DECISIONS.items():
        raw = (REPOSITORY_ROOT / relative).read_bytes()
        assert _sha256(raw) == expected_digest
        source_document = json.loads(raw)
        assert expected_ids <= _all_strings(source_document)
    declared_decision_ids = {
        decision_id
        for _, decision_ids in observed_source_decisions.values()
        for decision_id in decision_ids
    }
    vector_decision_ids = {
        cast(str, decision_id)
        for document in documents.values()
        for vector in _vectors(document)
        for decision_id in cast(list[Any], vector["decision_references"])
    }
    assert vector_decision_ids <= declared_decision_ids
    publications = manifest["originating_publications"]
    assert [
        (item["slice"], item["pull_request"], item["merge_sha"])
        for item in publications
    ] == EXPECTED_PUBLICATIONS


def _production_files() -> set[str]:
    return {
        path.relative_to(REPOSITORY_ROOT).as_posix()
        for path in (REPOSITORY_ROOT / "src").rglob("*.py")
    }


def _validate_current_production_file_inventory(production_files: set[str]) -> None:
    assert production_files == EXPECTED_PRODUCTION_FILES


def _working_source_bytes() -> dict[str, bytes]:
    production_files = _production_files()
    _validate_current_production_file_inventory(production_files)
    return {
        relative: (REPOSITORY_ROOT / relative).read_bytes()
        for relative in production_files
    }


def _validate_no_production_reader() -> None:
    production_files = _production_files()
    combined = b"\n".join(
        (REPOSITORY_ROOT / path).read_bytes() for path in sorted(production_files)
    )
    for forbidden in (
        b"IdentityContractCorpusReader",
        b"IdentityContractCorpusValidator",
        b"load_identity_contract_corpus",
        b"validate_identity_contract_corpus",
        b"reference_corpus/contracts/identity",
    ):
        assert forbidden not in combined
    assert not (REPOSITORY_ROOT / "reference_corpus/contracts/identity/latest").exists()
    assert not (
        REPOSITORY_ROOT / "reference_corpus/contracts/identity/current"
    ).exists()
    assert not (REPOSITORY_ROOT / "reference_corpus/contracts/identity/v2").exists()


def _assert_exact_s06_closure(paths: set[str]) -> None:
    actual = {
        path
        for path in paths
        if path == S06_CLOSURE_RELATIVE or path.startswith(f"{S06_CLOSURE_RELATIVE}/")
    }
    assert actual == {
        S06_CLOSURE_RELATIVE,
        *(f"{S06_CLOSURE_RELATIVE}/{name}" for name in EXPECTED_S06_CLOSURE_FILES),
    }


def _validate_registry_source() -> None:
    source = Path(__file__).read_bytes()
    tree = ast.parse(source)
    banned_calls = {"__import__", "eval", "exec", "getattr", "setattr"}
    direct_calls = {
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    assert banned_calls.isdisjoint(direct_calls)
    assert not any(
        isinstance(node, ast.Import)
        and any(alias.name.startswith("importlib") for alias in node.names)
        or isinstance(node, ast.ImportFrom)
        and node.module is not None
        and node.module.startswith("importlib")
        for node in tree.body
    )


def _privacy_findings(raw: bytes) -> list[str]:
    findings: list[str] = []
    lowered = raw.lower()
    if b"/home/" in lowered or b"/users/" in lowered:
        findings.append("absolute_home_path")
    if re.search(rb"(?:^|[\s\"'(])[a-zA-Z]:[\\/]", raw):
        findings.append("windows_drive_path")
    if b"/tmp/" in lowered:
        findings.append("tmp_path")
    if b"authorization:" in lowered or b"bearer " in lowered:
        findings.append("authorization")
    if re.search(rb"\b(?:gh[opurs]|github_pat)_[A-Za-z0-9_]{8,}\b", raw):
        findings.append("token")
    if re.search(rb"\b(?:sk|xox[baprs])-[A-Za-z0-9-]{16,}\b", raw):
        findings.append("service_credential")
    if b"private key-----" in lowered:
        findings.append("private_key")
    if re.search(rb"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b", raw):
        findings.append("email")
    if re.search(rb'"raw_provider_(?:response|body|payload|headers?)"\s*:', lowered):
        findings.append("raw_provider_body")
    return findings


type MemberKind = str


@dataclass(frozen=True)
class ArchiveMember:
    name: str
    kind: MemberKind
    data: bytes | None


def _archive_parts(member: ArchiveMember) -> tuple[str, ...]:
    assert member.name
    assert "\x00" not in member.name
    assert "\\" not in member.name
    assert not member.name.startswith("/")
    assert re.match(r"^[A-Za-z]:", member.name) is None
    text = (
        member.name[:-1]
        if member.kind == "directory" and member.name.endswith("/")
        else member.name
    )
    parts = tuple(text.split("/"))
    assert all(part not in {"", ".", ".."} for part in parts)
    assert member.kind not in {"link", "special"}
    return parts


def _wheel_members(path: Path) -> tuple[ArchiveMember, ...]:
    members: list[ArchiveMember] = []
    with zipfile.ZipFile(path) as archive:
        for info in archive.infolist():
            mode = info.external_attr >> 16
            if stat.S_ISLNK(mode):
                members.append(ArchiveMember(info.filename, "link", None))
            elif info.is_dir():
                members.append(ArchiveMember(info.filename, "directory", None))
            else:
                members.append(ArchiveMember(info.filename, "file", archive.read(info)))
    return tuple(members)


def _sdist_members(path: Path) -> tuple[ArchiveMember, ...]:
    members: list[ArchiveMember] = []
    with tarfile.open(path, mode="r:gz") as archive:
        for info in archive.getmembers():
            if info.issym() or info.islnk():
                members.append(ArchiveMember(info.name, "link", None))
            elif info.isdir():
                members.append(ArchiveMember(info.name, "directory", None))
            elif info.isfile():
                stream = archive.extractfile(info)
                assert stream is not None
                members.append(ArchiveMember(info.name, "file", stream.read()))
            else:
                members.append(ArchiveMember(info.name, "special", None))
    return tuple(members)


def _archive_source_bytes(
    members: tuple[ArchiveMember, ...],
) -> dict[str, bytes]:
    sources: dict[str, bytes] = {}
    for member in members:
        if member.kind != "file" or not member.name.endswith(".py"):
            continue
        parts = _archive_parts(member)
        try:
            package_index = parts.index("faultatlas")
        except ValueError:
            relative = f"__unexpected_archive_python__/{member.name}"
        else:
            relative = "src/" + "/".join(parts[package_index:])
        assert relative not in sources
        assert member.data is not None
        sources[relative] = member.data
    return sources


def _assert_complete_package_sources(
    packaged: dict[str, bytes],
    working: dict[str, bytes],
) -> None:
    assert set(working) == EXPECTED_PRODUCTION_FILES
    assert set(packaged) == EXPECTED_PRODUCTION_FILES
    assert packaged == working


def _assert_safe_archive(
    members: tuple[ArchiveMember, ...],
    *,
    expect_modules: bool,
) -> None:
    assert members
    corpus_payloads = {
        (CORPUS_ROOT / filename).read_bytes() for filename in EXPECTED_FILES
    } | {
        (CORRECTION_ROOT / filename).read_bytes()
        for filename in EXPECTED_CORRECTION_FILES
    }
    file_members: list[ArchiveMember] = []
    for member in members:
        parts = _archive_parts(member)
        assert "reference_corpus" not in {part.casefold() for part in parts}
        if member.kind == "file":
            assert member.data is not None
            assert member.data not in corpus_payloads
            assert b"faultatlas-identity-contract-corpus-manifest" not in member.data
            file_members.append(member)

    historical_license = (
        REPOSITORY_ROOT / "reference_corpus/pytest-4412/acquisitions/"
        "run-0001-s04-v1-base-4c9cde74-head-690a63b9/artifacts/LICENSE"
    ).read_bytes()
    project_license = (REPOSITORY_ROOT / "LICENSE").read_bytes()
    assert all(member.data != historical_license for member in file_members)
    packaged_licenses = [
        member.data
        for member in file_members
        if PurePosixPath(member.name).name == "LICENSE"
    ]
    assert packaged_licenses == [project_license]

    if expect_modules:
        working = {
            relative: (REPOSITORY_ROOT / relative).read_bytes()
            for relative in EXPECTED_PRODUCTION_FILES
        }
        _assert_complete_package_sources(_archive_source_bytes(members), working)


def _git_status() -> bytes:
    result = subprocess.run(
        ["git", "status", "--porcelain=v1", "-z", "--untracked-files=all"],
        cwd=REPOSITORY_ROOT,
        check=True,
        capture_output=True,
    )
    return result.stdout


def _repository_file_snapshot() -> tuple[tuple[str, int, str], ...]:
    snapshot: list[tuple[str, int, str]] = []
    for path in REPOSITORY_ROOT.rglob("*"):
        relative = path.relative_to(REPOSITORY_ROOT)
        if relative.parts[0] in {".git", ".venv"}:
            continue
        if path.is_symlink():
            payload = os.readlink(path).encode("utf-8")
        elif path.is_file():
            payload = path.read_bytes()
        else:
            continue
        snapshot.append(
            (relative.as_posix(), stat.S_IMODE(path.lstat().st_mode), _sha256(payload))
        )
    return tuple(sorted(snapshot))


def _parse_git_stage_z(raw: bytes) -> dict[str, str]:
    modes: dict[str, str] = {}
    for entry in raw.split(b"\0"):
        if not entry:
            continue
        header, path_bytes = entry.split(b"\t", 1)
        mode, object_id, stage = header.decode("ascii").split(" ")
        path = path_bytes.decode("utf-8")
        assert re.fullmatch(r"[0-9a-f]{40,64}", object_id) is not None
        assert stage == "0"
        assert path not in modes
        modes[path] = mode
    return modes


def _git_stage_modes(
    paths: set[str], *, environment: dict[str, str] | None = None
) -> dict[str, str]:
    result = subprocess.run(
        ["git", "ls-files", "--stage", "-z", "--", *sorted(paths)],
        cwd=REPOSITORY_ROOT,
        env=environment,
        check=True,
        capture_output=True,
    )
    return _parse_git_stage_z(result.stdout)


def _assert_fs_regular_0644(path: Path) -> None:
    mode = path.lstat().st_mode
    assert not stat.S_ISLNK(mode)
    assert stat.S_ISREG(mode)
    assert stat.S_IMODE(mode) == 0o644


def _assert_git_modes_100644(modes: dict[str, str], expected: set[str]) -> None:
    assert set(modes) == expected
    assert set(modes.values()) == {"100644"}


def _assert_untracked_path(relative: str) -> None:
    result = subprocess.run(
        [
            "git",
            "status",
            "--porcelain=v1",
            "-z",
            "--untracked-files=all",
            "--",
            relative,
        ],
        cwd=REPOSITORY_ROOT,
        check=True,
        capture_output=True,
    )
    assert result.stdout == f"?? {relative}\0".encode()


def _prospective_new_file_modes(paths: set[str], tmp_path: Path) -> dict[str, str]:
    index = tmp_path / "prospective-index"
    environment = os.environ.copy()
    environment["GIT_INDEX_FILE"] = str(index)
    subprocess.run(
        ["git", "read-tree", "HEAD"],
        cwd=REPOSITORY_ROOT,
        env=environment,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "update-index", "--info-only", "--add", "--", *sorted(paths)],
        cwd=REPOSITORY_ROOT,
        env=environment,
        check=True,
        capture_output=True,
    )
    return _git_stage_modes(paths, environment=environment)


def _validate_current_permission_contract(tmp_path: Path) -> None:
    for relative in EXPECTED_CORRECTION_PERMISSION_PATHS:
        _assert_fs_regular_0644(REPOSITORY_ROOT / relative)

    actual_modes = _git_stage_modes(EXPECTED_CORRECTION_PERMISSION_PATHS)
    untracked = EXPECTED_CORRECTION_PERMISSION_PATHS - set(actual_modes)
    assert untracked <= EXPECTED_NEW_PERMISSION_PATHS
    _assert_git_modes_100644(
        actual_modes,
        EXPECTED_CORRECTION_PERMISSION_PATHS - untracked,
    )

    if untracked:
        for relative in untracked:
            _assert_untracked_path(relative)
        prospective_modes = _prospective_new_file_modes(untracked, tmp_path)
        _assert_git_modes_100644(prospective_modes, untracked)


def _build_archives(tmp_path: Path) -> tuple[Path, Path]:
    uv = shutil.which("uv")
    assert uv is not None
    output = tmp_path / "dist"
    cache = tmp_path / "uv-cache"
    output.mkdir()
    cache.mkdir()
    environment = os.environ.copy()
    environment.update(
        {
            "PYTHONDONTWRITEBYTECODE": "1",
            "UV_CACHE_DIR": str(cache),
            "UV_NO_SYNC": "1",
            "UV_OFFLINE": "1",
        }
    )
    status_before = _git_status()
    files_before = _repository_file_snapshot()
    result = subprocess.run(
        [
            uv,
            "build",
            "--offline",
            "--no-create-gitignore",
            "--out-dir",
            str(output),
        ],
        cwd=REPOSITORY_ROOT,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
    )
    status_after = _git_status()
    files_after = _repository_file_snapshot()
    assert status_after == status_before
    assert files_after == files_before
    assert result.returncode == 0, (
        f"offline build failed\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )
    wheels = tuple(output.glob("*.whl"))
    sdists = tuple(output.glob("*.tar.gz"))
    assert len(wheels) == len(sdists) == 1
    return wheels[0], sdists[0]


def _write_synthetic_archive(
    tmp_path: Path, *, kind: str, name: str, data: bytes
) -> tuple[ArchiveMember, ...]:
    project_license = (REPOSITORY_ROOT / "LICENSE").read_bytes()
    if kind == "wheel":
        path = tmp_path / "synthetic.whl"
        with zipfile.ZipFile(path, "w") as archive:
            archive.writestr("synthetic.dist-info/licenses/LICENSE", project_license)
            archive.writestr(name, data)
        return _wheel_members(path)
    path = tmp_path / "synthetic.tar.gz"
    with tarfile.open(path, "w:gz") as archive:
        for member_name, member_data in (
            ("synthetic-0.0.0/LICENSE", project_license),
            (name, data),
        ):
            info = tarfile.TarInfo(member_name)
            info.size = len(member_data)
            info.mtime = 0
            archive.addfile(info, io.BytesIO(member_data))
    return _sdist_members(path)


VALID_DOCUMENT = _load_document("valid-vectors.json")
INVALID_DOCUMENT = _load_document("invalid-vectors.json")
COMPATIBILITY_DOCUMENT = _load_document("compatibility-vectors.json")
CORRECTION_DOCUMENT = _load_correction_document("correction.json")
REGRESSION_DOCUMENT = _load_correction_document("regression-vectors.json")
V1_DOCUMENTS = {
    "valid-vectors.json": VALID_DOCUMENT,
    "invalid-vectors.json": INVALID_DOCUMENT,
    "compatibility-vectors.json": COMPATIBILITY_DOCUMENT,
}
EFFECTIVE_CONTRACT_PLAN = _build_effective_contract_plan(
    V1_DOCUMENTS,
    CORRECTION_DOCUMENT,
    REGRESSION_DOCUMENT,
)
VALID_VECTOR_IDS = tuple(
    cast(str, item["id"])
    for item in _vectors(VALID_DOCUMENT)
    if item["id"] != SUPERSEDED_V1_VECTOR_ID
)
INVALID_VECTOR_IDS = tuple(cast(str, item["id"]) for item in _vectors(INVALID_DOCUMENT))
COMPATIBILITY_VECTOR_IDS = tuple(
    cast(str, item["id"]) for item in _vectors(COMPATIBILITY_DOCUMENT)
)
CORRECTION_VECTOR_IDS = tuple(
    cast(str, item["id"]) for item in _vectors(REGRESSION_DOCUMENT)
)


def test_exact_nine_file_inventory_is_regular_immutable_and_safe() -> None:
    _validate_corpus_inventory(CORPUS_ROOT)


@pytest.mark.parametrize("filename", sorted(EXPECTED_LOCKS))
def test_independent_file_digest_oracle(filename: str) -> None:
    _assert_locked_bytes(filename, (CORPUS_ROOT / filename).read_bytes())


@pytest.mark.parametrize("filename", sorted(EXPECTED_JSON_FORMATS))
def test_primary_json_is_canonical_and_has_exact_format(filename: str) -> None:
    document = _load_document(filename)
    assert document["format"]["name"] == EXPECTED_JSON_FORMATS[filename]
    assert document["format"]["version"] == "1"
    assert document["format"]["audience"] == "internal"
    assert document["format"]["calibration"] == "case-calibrated"
    assert document["format"]["public_contract"] is False
    assert document["format"]["production_persistence"] is False
    assert document["format"]["semantic_versioning"] == "independent"


@pytest.mark.parametrize(
    "filename",
    [
        "manifest.sha256",
        "valid-vectors.sha256",
        "invalid-vectors.sha256",
        "compatibility-vectors.sha256",
    ],
)
def test_sidecar_is_exact_and_independently_locked(filename: str) -> None:
    raw = (CORPUS_ROOT / filename).read_bytes()
    _assert_locked_bytes(filename, raw)
    _validate_sidecar(filename, raw)


def test_manifest_integrity_inventory_counts_and_source_decisions() -> None:
    documents = {
        "valid-vectors.json": VALID_DOCUMENT,
        "invalid-vectors.json": INVALID_DOCUMENT,
        "compatibility-vectors.json": COMPATIBILITY_DOCUMENT,
    }
    _validate_manifest(_load_document("manifest.json"), documents)


def test_vector_top_levels_counts_ids_and_fixture_graphs_are_exact() -> None:
    documents = {
        "valid-vectors.json": VALID_DOCUMENT,
        "invalid-vectors.json": INVALID_DOCUMENT,
        "compatibility-vectors.json": COMPATIBILITY_DOCUMENT,
    }
    for filename, document in documents.items():
        assert set(document) == EXPECTED_VECTOR_TOP_LEVEL[filename]
        _validate_fixture_graph(document)
    _validate_vector_shape_and_ids(documents)


def test_target_registry_is_explicit_complete_and_internal_only() -> None:
    documents = {
        "valid-vectors.json": VALID_DOCUMENT,
        "invalid-vectors.json": INVALID_DOCUMENT,
        "compatibility-vectors.json": COMPATIBILITY_DOCUMENT,
    }
    _validate_registry_and_coverage(documents)
    _validate_registry_source()
    with pytest.raises(AssertionError):
        _model_for_vector(
            {
                "target_symbol": "os.system",
                "target_variant": None,
            }
        )
    with pytest.raises(ValueError):
        CompatibilityStatus("invented")
    unknown_operation_documents = copy.deepcopy(documents)
    unknown_operation_documents["valid-vectors.json"]["vectors"][0]["operation"] = (
        "unknown_operation"
    )
    with pytest.raises(AssertionError):
        _validate_vector_shape_and_ids(unknown_operation_documents)

    duplicate_fixture_document = copy.deepcopy(VALID_DOCUMENT)
    duplicate_fixture_document["fixtures"][1]["id"] = duplicate_fixture_document[
        "fixtures"
    ][0]["id"]
    with pytest.raises(AssertionError):
        _fixture_map(duplicate_fixture_document)

    self_referencing_fixture_document = copy.deepcopy(VALID_DOCUMENT)
    fixture_id = self_referencing_fixture_document["fixtures"][0]["id"]
    self_referencing_fixture_document["fixtures"][0]["value"] = {
        "fixture_ref": fixture_id
    }
    with pytest.raises(AssertionError):
        _validate_fixture_graph(self_referencing_fixture_document)


def test_effective_contract_plan_is_complete_and_distinguishes_history() -> None:
    assert len(EFFECTIVE_CONTRACT_PLAN) == EXPECTED_EFFECTIVE_VECTOR_COUNT
    active_v1 = [
        entry for entry in EFFECTIVE_CONTRACT_PLAN if entry.source == "active_v1"
    ]
    correction = [
        entry
        for entry in EFFECTIVE_CONTRACT_PLAN
        if entry.source == "append_only_correction"
    ]
    assert len(active_v1) == 167
    assert len(correction) == EXPECTED_CORRECTION_VECTOR_COUNT
    assert {entry.vector_id for entry in correction} == set(CORRECTION_VECTOR_IDS)
    assert SUPERSEDED_V1_VECTOR_ID not in {
        entry.vector_id for entry in EFFECTIVE_CONTRACT_PLAN
    }
    assert _vector_by_id(VALID_DOCUMENT, SUPERSEDED_V1_VECTOR_ID)["status"] == (
        "locked"
    )


def test_superseded_historical_vector_is_retained_but_now_rejects() -> None:
    vector = _vector_by_id(VALID_DOCUMENT, SUPERSEDED_V1_VECTOR_ID)
    value = _resolve_value(vector["input"], _fixture_map(VALID_DOCUMENT))
    model = _model_for_vector(vector)
    with pytest.raises(ValidationError) as error:
        _validate_model(model, value, cast(str, vector["input_mode"]))
    assert len(error.value.errors()) == 1
    item = error.value.errors()[0]
    assert item["loc"] == ()
    assert item["type"] == "value_error"
    assert "ambiguous scalar JSON representations" in item["msg"]
    assert "domain-discriminated carrier" in item["msg"]


@pytest.mark.parametrize(
    "mutation",
    (
        "correction-layer-removed",
        "unknown-superseded-id",
        "duplicate-superseded-id",
        "superseded-without-replacement",
        "unknown-replacement-id",
        "replacement-without-reverse-reference",
    ),
)
def test_effective_contract_overlay_mutation_is_rejected(mutation: str) -> None:
    correction = copy.deepcopy(CORRECTION_DOCUMENT)
    regressions = copy.deepcopy(REGRESSION_DOCUMENT)
    item = correction["superseded_contract_vectors"]["items"][0]
    if mutation == "correction-layer-removed":
        correction = {}
    elif mutation == "unknown-superseded-id":
        item["original_vector_id"] = "identity.valid.field-state.unknown"
    elif mutation == "duplicate-superseded-id":
        correction["superseded_contract_vectors"]["items"].append(copy.deepcopy(item))
        correction["superseded_contract_vectors"]["count"] += 1
    elif mutation == "superseded-without-replacement":
        item["replacement_regression_vector_ids"] = []
    elif mutation == "unknown-replacement-id":
        item["replacement_regression_vector_ids"] = [
            "identity.correction.s05-c01.unknown"
        ]
    else:
        assert mutation == "replacement-without-reverse-reference"
        replacement = _vector_by_id(
            regressions,
            "identity.correction.s05-c01.generic-rejection."
            "number-global.conflict-distinct-json",
        )
        replacement["supersedes_v1_vector_ids"] = []
    with pytest.raises((AssertionError, KeyError)):
        _build_effective_contract_plan(V1_DOCUMENTS, correction, regressions)


@pytest.mark.parametrize("vector_id", VALID_VECTOR_IDS)
def test_valid_vector_executes_and_round_trips(vector_id: str) -> None:
    _execute_valid_vector(_vector_by_id(VALID_DOCUMENT, vector_id), VALID_DOCUMENT)


@pytest.mark.parametrize("vector_id", INVALID_VECTOR_IDS)
def test_invalid_vector_is_strictly_rejected(vector_id: str) -> None:
    _assert_invalid_vector(_vector_by_id(INVALID_DOCUMENT, vector_id), INVALID_DOCUMENT)


@pytest.mark.parametrize("vector_id", COMPATIBILITY_VECTOR_IDS)
def test_compatibility_vector_has_exact_loss_aware_outcome(vector_id: str) -> None:
    _execute_compatibility_vector(
        _vector_by_id(COMPATIBILITY_DOCUMENT, vector_id),
        COMPATIBILITY_DOCUMENT,
    )


def test_compatibility_status_reason_basis_and_no_winner_audit() -> None:
    vectors = _vectors(COMPATIBILITY_DOCUMENT)
    mapping_vectors = [item for item in vectors if item["category"] == "legacy-mapping"]
    projection_vectors = [
        item for item in vectors if item["category"] == "legacy-projection"
    ]
    assert {item["expected"]["status"] for item in mapping_vectors} == {
        "losslessly_mappable",
        "partially_mappable",
        "conflict",
    }
    assert {item["expected"]["status"] for item in projection_vectors} == {
        "partially_mappable",
        "not_mappable",
        "conflict",
    }
    assert all(item["expected"]["winner_selected"] is False for item in mapping_vectors)
    assert all(
        item["expected"]["semantic_dump"]["mapping_basis"]
        == "legacy_locator_plus_explicit_repository_context"
        for item in mapping_vectors
    )
    assert all(
        item["expected"]["semantic_dump"]["projection_basis"]
        == "source_identity_plus_explicit_repository_alias_observation"
        for item in projection_vectors
    )
    issue_projection = _vector_by_id(
        COMPATIBILITY_DOCUMENT,
        "identity.compatibility.legacy-projection.github-issue",
    )
    assert issue_projection["expected"]["reasons"] == [
        "stable_repository_identity_not_represented",
        "alias_authority_not_represented",
        "alias_observation_time_not_represented",
        "schema_version_not_represented",
    ]


def test_markdown_is_locked_synchronized_and_non_authoritative() -> None:
    raw = (CORPUS_ROOT / "contract.md").read_bytes()
    _assert_locked_bytes("contract.md", raw)
    text = raw.decode("utf-8")
    manifest_digest = _sha256((CORPUS_ROOT / "manifest.json").read_bytes())
    assert text.count(manifest_digest) == 1
    for required in (
        "Internal, case-calibrated, non-public",
        "58 locked valid vectors",
        "80 locked invalid vectors",
        "30 locked compatibility vectors",
        "excluded from wheel and sdist",
        "No production corpus reader or validator exists",
        "future version/registry ownership remains `S1.P10`",
        "derived and non-authoritative",
    ):
        assert required in text


def test_privacy_retention_and_no_raw_provider_payload() -> None:
    combined = b"\n".join(
        (CORPUS_ROOT / filename).read_bytes() for filename in sorted(EXPECTED_FILES)
    )
    assert _privacy_findings(combined) == []
    assert b"pytest-dev/pytest" in combined
    assert b"api.github.com" in combined
    assert b"381866787" in combined


def test_no_production_reader_and_exact_external_s06_closure() -> None:
    _validate_no_production_reader()
    paths = {
        path.relative_to(REPOSITORY_ROOT).as_posix()
        for path in REPOSITORY_ROOT.rglob("*")
    }
    _assert_exact_s06_closure(paths)


def test_missing_or_extra_s06_closure_artifact_is_rejected() -> None:
    exact = {
        S06_CLOSURE_RELATIVE,
        *(f"{S06_CLOSURE_RELATIVE}/{name}" for name in EXPECTED_S06_CLOSURE_FILES),
    }
    with pytest.raises(AssertionError):
        _assert_exact_s06_closure(exact - {f"{S06_CLOSURE_RELATIVE}/closure.md"})
    with pytest.raises(AssertionError):
        _assert_exact_s06_closure(exact | {f"{S06_CLOSURE_RELATIVE}/extra.json"})


def test_current_correction_whole_source_inventory_is_exact() -> None:
    working = _working_source_bytes()
    assert set(working) == EXPECTED_PRODUCTION_FILES
    assert len(working) == 8


def test_p02_revision_surface_is_outside_the_immutable_p01_contract() -> None:
    manifest = _load_document("manifest.json")
    target_symbols = manifest["target_symbols"]
    p01_targets = {
        symbol
        for key in ("identity_module", "compatibility_module", "legacy")
        for symbol in target_symbols[key]
    }
    assert not EXPECTED_REVISION_EXPORTS & p01_targets
    assert EXPECTED_S02_REVISION_EXPORTS <= EXPECTED_REVISION_EXPORTS
    assert EXPECTED_S03_REVISION_EXPORTS <= EXPECTED_REVISION_EXPORTS
    assert not EXPECTED_S02_REVISION_EXPORTS & p01_targets
    assert not EXPECTED_S03_REVISION_EXPORTS & p01_targets
    assert manifest["scope"]["production_modules"] == [
        "faultatlas.domain.identity",
        "faultatlas.domain.compatibility",
    ]
    assert "Git_object_identity" in manifest["non_goals"]
    assert EXPECTED_EFFECTIVE_VECTOR_COUNT == 199


@pytest.mark.parametrize(
    "mutation",
    ("unexpected-source", "missing-source", "packaged-byte-mismatch"),
)
def test_whole_source_inventory_mutation_is_rejected(mutation: str) -> None:
    working = _working_source_bytes()
    packaged = dict(working)
    if mutation == "unexpected-source":
        packaged["src/faultatlas/domain/unexpected.py"] = b"pass\n"
    elif mutation == "missing-source":
        del packaged["src/faultatlas/domain/revision.py"]
    else:
        assert mutation == "packaged-byte-mismatch"
        packaged["src/faultatlas/domain/compatibility.py"] += b"\n"
    with pytest.raises(AssertionError):
        _assert_complete_package_sources(packaged, working)


def test_current_git_and_filesystem_permission_contract_is_exact(
    tmp_path: Path,
) -> None:
    _validate_current_permission_contract(tmp_path)


@pytest.mark.parametrize(
    "mutation", ("filesystem-0755", "filesystem-0600", "symlink", "special-file")
)
def test_filesystem_permission_mutation_is_rejected(
    mutation: str, tmp_path: Path
) -> None:
    target = tmp_path / "artifact"
    if mutation == "symlink":
        source = tmp_path / "source"
        source.write_bytes(b"locked\n")
        target.symlink_to(source)
    elif mutation == "special-file":
        os.mkfifo(target)
    else:
        target.write_bytes(b"locked\n")
        target.chmod(0o755 if mutation == "filesystem-0755" else 0o600)
    with pytest.raises(AssertionError):
        _assert_fs_regular_0644(target)


def test_git_mode_100755_mutation_is_rejected() -> None:
    relative = f"{CORRECTION_RELATIVE}/correction.json"
    raw = f"100755 {'0' * 40} 0\t{relative}\0".encode()
    modes = _parse_git_stage_z(raw)
    with pytest.raises(AssertionError):
        _assert_git_modes_100644(modes, {relative})


def test_actual_offline_wheel_and_sdist_exclude_corpus(tmp_path: Path) -> None:
    wheel, sdist = _build_archives(tmp_path)
    wheel_members = _wheel_members(wheel)
    sdist_members = _sdist_members(sdist)
    _assert_safe_archive(wheel_members, expect_modules=True)
    _assert_safe_archive(sdist_members, expect_modules=True)
    assert not any(
        "tests" in {part.casefold() for part in _archive_parts(member)}
        for member in wheel_members
    )


MUTATION_CASES = (
    "changed-primary-byte",
    "coherent-json-sidecar-reseal",
    "sidecar-basename",
    "sidecar-uppercase-digest",
    "sidecar-spacing",
    "missing-terminal-lf",
    "duplicate-terminal-lf",
    "pretty-json",
    "unsorted-json",
    "inserted-float",
    "duplicate-vector-id",
    "unknown-target",
    "removed-target-coverage",
    "wrong-valid-expected-dump",
    "invalid-made-valid",
    "wrong-invalid-error-location",
    "compatibility-status-change",
    "compatibility-reason-removed",
    "unresolved-candidate-order-reversed",
    "conflict-winner-inserted",
    "fixture-reference-missing",
    "fixture-cycle",
    "manifest-vector-digest",
    "manifest-vector-count",
    "extra-corpus-file",
    "mutable-latest-pointer",
    "synthetic-package-corpus-member",
    "synthetic-package-historical-license",
)


@pytest.mark.parametrize("mutation", MUTATION_CASES)
def test_required_mutation_is_detected(mutation: str, tmp_path: Path) -> None:
    valid = copy.deepcopy(VALID_DOCUMENT)
    invalid = copy.deepcopy(INVALID_DOCUMENT)
    compatibility = copy.deepcopy(COMPATIBILITY_DOCUMENT)
    manifest = copy.deepcopy(_load_document("manifest.json"))
    documents = {
        "valid-vectors.json": valid,
        "invalid-vectors.json": invalid,
        "compatibility-vectors.json": compatibility,
    }

    if mutation == "changed-primary-byte":
        raw = bytearray((CORPUS_ROOT / "valid-vectors.json").read_bytes())
        raw[10] = ord("X")
        with pytest.raises(AssertionError):
            _assert_locked_bytes("valid-vectors.json", bytes(raw))
        return
    if mutation == "coherent-json-sidecar-reseal":
        changed = copy.deepcopy(valid)
        changed["assurance"]["status"] = "resealed"
        raw = _canonical_bytes(changed)
        sidecar = f"{_sha256(raw)}  valid-vectors.json\n".encode()
        _validate_sidecar_bytes = re.fullmatch(
            rb"[0-9a-f]{64}  valid-vectors\.json\n", sidecar
        )
        assert _validate_sidecar_bytes is not None
        with pytest.raises(AssertionError):
            _assert_locked_bytes("valid-vectors.json", raw)
        with pytest.raises(AssertionError):
            _assert_locked_bytes("valid-vectors.sha256", sidecar)
        return
    if mutation in {
        "sidecar-basename",
        "sidecar-uppercase-digest",
        "sidecar-spacing",
    }:
        raw = (CORPUS_ROOT / "valid-vectors.sha256").read_bytes()
        if mutation == "sidecar-basename":
            raw = raw.replace(b"valid-vectors.json", b"invalid-vectors.json")
        elif mutation == "sidecar-uppercase-digest":
            raw = raw[:64].upper() + raw[64:]
        else:
            raw = raw.replace(b"  valid", b" valid")
        with pytest.raises(AssertionError):
            _validate_sidecar("valid-vectors.sha256", raw)
        return
    if mutation in {
        "missing-terminal-lf",
        "duplicate-terminal-lf",
        "pretty-json",
        "unsorted-json",
        "inserted-float",
    }:
        raw = (CORPUS_ROOT / "valid-vectors.json").read_bytes()
        if mutation == "missing-terminal-lf":
            raw = raw[:-1]
        elif mutation == "duplicate-terminal-lf":
            raw += b"\n"
        elif mutation == "pretty-json":
            raw = (json.dumps(valid, indent=2, ensure_ascii=False) + "\n").encode()
        elif mutation == "unsorted-json":
            unsorted = {key: valid[key] for key in reversed(tuple(valid))}
            raw = (
                json.dumps(
                    unsorted,
                    ensure_ascii=False,
                    allow_nan=False,
                    separators=(",", ":"),
                )
                + "\n"
            ).encode()
        else:
            changed = copy.deepcopy(valid)
            changed["assurance"]["float"] = 1.5
            raw = (
                json.dumps(changed, separators=(",", ":"), sort_keys=True) + "\n"
            ).encode()
        with pytest.raises((AssertionError, json.JSONDecodeError)):
            _parse_canonical_json(raw)
        return
    if mutation == "duplicate-vector-id":
        valid["vectors"][1]["id"] = valid["vectors"][0]["id"]
        with pytest.raises(AssertionError):
            _validate_vector_shape_and_ids(documents)
        return
    if mutation == "unknown-target":
        valid["vectors"][0]["target_symbol"] = "pathlib.Path.read_text"
        with pytest.raises(AssertionError):
            _validate_registry_and_coverage(documents)
        return
    if mutation == "removed-target-coverage":
        valid["vectors"] = [
            vector
            for vector in valid["vectors"]
            if vector["target_symbol"] != "ProviderKey"
        ]
        invalid["vectors"] = [
            vector
            for vector in invalid["vectors"]
            if vector["target_symbol"] != "ProviderKey"
        ]
        with pytest.raises(AssertionError):
            _validate_registry_and_coverage(documents)
        return
    if mutation == "wrong-valid-expected-dump":
        vector = _vector_by_id(valid, "identity.valid.provider.key-github")
        vector["expected"]["semantic_dump"] = "gitlab"
        with pytest.raises(AssertionError):
            _execute_valid_vector(vector, valid)
        return
    if mutation == "invalid-made-valid":
        vector = _vector_by_id(invalid, "identity.invalid.provider-key.uppercase")
        vector["input"] = "github"
        with pytest.raises(AssertionError):
            _assert_invalid_vector(vector, invalid)
        return
    if mutation == "wrong-invalid-error-location":
        vector = _vector_by_id(invalid, "identity.invalid.authority-host.uppercase")
        vector["expected"]["error_location"] = ["provider"]
        with pytest.raises(AssertionError):
            _assert_invalid_vector(vector, invalid)
        return
    if mutation in {
        "compatibility-status-change",
        "compatibility-reason-removed",
        "unresolved-candidate-order-reversed",
        "conflict-winner-inserted",
    }:
        if mutation == "compatibility-status-change":
            vector = _vector_by_id(
                compatibility,
                "identity.compatibility.legacy-projection.github-issue",
            )
            vector["expected"]["status"] = "losslessly_mappable"
        elif mutation == "compatibility-reason-removed":
            vector = _vector_by_id(
                compatibility,
                "identity.compatibility.legacy-projection.github-issue",
            )
            vector["expected"]["reasons"] = vector["expected"]["reasons"][:-1]
        elif mutation == "unresolved-candidate-order-reversed":
            vector = _vector_by_id(
                compatibility,
                "identity.compatibility.legacy-mapping.unresolved",
            )
            vector["expected"]["candidate_runtime_types"] = [
                "ProviderGlobalId",
                "RepositoryScopedNumber",
            ]
        else:
            vector = _vector_by_id(
                compatibility,
                "identity.compatibility.legacy-mapping.unresolved",
            )
            vector["expected"]["semantic_dump"]["object_id_state"]["value"] = "4412"
        with pytest.raises(AssertionError):
            _execute_compatibility_vector(vector, compatibility)
        return
    if mutation == "fixture-reference-missing":
        valid["vectors"][0]["input"] = {"fixture_ref": "identity.fixture.valid.missing"}
        with pytest.raises(AssertionError):
            _validate_fixture_graph(valid)
        return
    if mutation == "fixture-cycle":
        valid["fixtures"][0]["value"] = {"fixture_ref": valid["fixtures"][1]["id"]}
        valid["fixtures"][1]["value"] = {"fixture_ref": valid["fixtures"][0]["id"]}
        with pytest.raises(AssertionError):
            _validate_fixture_graph(valid)
        return
    if mutation == "manifest-vector-digest":
        manifest["corpus_files"]["vector_files"][0]["sha256"] = "0" * 64
        with pytest.raises(AssertionError):
            _validate_manifest(manifest, documents)
        return
    if mutation == "manifest-vector-count":
        manifest["vector_summary"]["valid"]["count"] += 1
        with pytest.raises(AssertionError):
            _validate_manifest(manifest, documents)
        return
    if mutation in {"extra-corpus-file", "mutable-latest-pointer"}:
        synthetic_root = tmp_path / "contracts/identity/v1"
        shutil.copytree(CORPUS_ROOT, synthetic_root)
        shutil.copytree(
            CORRECTION_ROOT,
            synthetic_root.parent / "corrections/s05-c01-ambiguous-union-round-trip",
        )
        shutil.copytree(
            REPOSITORY_ROOT / S06_CLOSURE_RELATIVE,
            synthetic_root.parent / "closures/s1-p01-phase-closure",
        )
        if mutation == "extra-corpus-file":
            (synthetic_root / "extra.json").write_bytes(b"{}\n")
        else:
            (synthetic_root.parent / "latest").write_bytes(b"v1\n")
        with pytest.raises(AssertionError):
            _validate_corpus_inventory(synthetic_root)
        return
    if mutation == "synthetic-package-corpus-member":
        members = _write_synthetic_archive(
            tmp_path,
            kind="wheel",
            name="reference_corpus/contracts/identity/v1/manifest.json",
            data=b"{}\n",
        )
        with pytest.raises(AssertionError):
            _assert_safe_archive(members, expect_modules=False)
        return
    assert mutation == "synthetic-package-historical-license"
    historical = (
        REPOSITORY_ROOT / "reference_corpus/pytest-4412/acquisitions/"
        "run-0001-s04-v1-base-4c9cde74-head-690a63b9/artifacts/LICENSE"
    ).read_bytes()
    members = _write_synthetic_archive(
        tmp_path,
        kind="sdist",
        name="synthetic-0.0.0/COPYING.pytest",
        data=historical,
    )
    with pytest.raises(AssertionError):
        _assert_safe_archive(members, expect_modules=False)
