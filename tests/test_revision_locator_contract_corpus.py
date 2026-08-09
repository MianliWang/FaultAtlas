from __future__ import annotations

import ast
import copy
import hashlib
import json
import math
import os
import re
import shutil
import stat
import subprocess
import tarfile
import zipfile
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta, timezone
from enum import StrEnum
from pathlib import Path, PurePosixPath
from typing import Any, NoReturn, cast

import pytest
from pydantic import BaseModel, TypeAdapter, ValidationError

import faultatlas
import faultatlas.domain as domain_package
import faultatlas.domain.evidence as evidence_module
import faultatlas.domain.revision as revision_module
from faultatlas.domain.identity import (
    AuthorityRole,
    ProviderAuthority,
    ProviderKey,
    ProviderRepositoryId,
    RepositoryIdentity,
    SourceIdentityLifecycleState,
)
from faultatlas.domain.revision import (
    ArtifactByteLocator,
    BoundedLocator,
    DiffHunkLocator,
    GitBlobIdentity,
    GitCommitIdentity,
    GitCommitParentTopology,
    GitHashAlgorithm,
    GitObjectIdentity,
    GitObjectKind,
    GitRefName,
    GitRefNamespace,
    GitRefObservation,
    GitRepositoryPath,
    GitRevisionIdentity,
    LineEnding,
    OneBasedInclusiveLineSpan,
    RevisionLineLocator,
    RevisionQualifiedPath,
    RevisionRole,
    RevisionRoleAssignment,
    TextEncoding,
    ZeroBasedHalfOpenByteSpan,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
CORPUS_RELATIVE = "reference_corpus/contracts/revision-locator/v1"
CORPUS_ROOT = REPOSITORY_ROOT / CORPUS_RELATIVE
CLOSURE_RELATIVE = (
    "reference_corpus/contracts/revision-locator/closures/s1-p02-phase-closure"
)
CLOSURE_ROOT = REPOSITORY_ROOT / CLOSURE_RELATIVE
ARTIFACT_RELATIVE = (
    "reference_corpus/pytest-4412/acquisitions/"
    "run-0001-s04-v1-base-4c9cde74-head-690a63b9/artifacts/base-to-head.diff"
)
ARTIFACT_PATH = REPOSITORY_ROOT / ARTIFACT_RELATIVE
ACQUISITION_RELATIVE = (
    "reference_corpus/pytest-4412/acquisitions/"
    "run-0001-s04-v1-base-4c9cde74-head-690a63b9/acquisition.json"
)
ACQUISITION_SHA256 = "1c29093bf1537e9b824a18df1848b71a8da014f544bc9f385707eb0e000a1318"

EXPECTED_FILES = {
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
EXPECTED_CLOSURE_FILES = {
    "closure.json",
    "closure.md",
    "closure.sha256",
}
JSON_FILES = {
    "manifest.json",
    "valid-vectors.json",
    "invalid-vectors.json",
    "replay-vectors.json",
}
SIDECAR_FILES = {name.removesuffix(".json") + ".sha256" for name in JSON_FILES}


@dataclass(frozen=True)
class LockedFile:
    byte_length: int
    sha256: str


EXPECTED_LOCKS = {
    "contract.md": LockedFile(
        3718, "6500936787c93f8f818d197876bf91ef9b0fb4d9fbddd33772442c39a57e9ea8"
    ),
    "invalid-vectors.json": LockedFile(
        99806, "832486482537b88fabad8efe6f6fb0f9a908e6ea29005dd9bbc60a44101d5944"
    ),
    "invalid-vectors.sha256": LockedFile(
        87, "660285fe678b6d8ffd569eac96ca2225be201eb85f52fcc06a481e531c3121d9"
    ),
    "manifest.json": LockedFile(
        8083, "56ba607a098744800ae94448982a0a3bab91fb4e7fba445a31406e2478dc1b80"
    ),
    "manifest.sha256": LockedFile(
        80, "53b5655d5d3ed8004331dbded43a8b5f846cffa3c17e2788e1f02ad17c9dd92b"
    ),
    "replay-vectors.json": LockedFile(
        21868, "bbf8d770eabe289a7d703e8185e0c9187ab63d4d18a93c5c817477facff06a8f"
    ),
    "replay-vectors.sha256": LockedFile(
        86, "14e9f813dafe9f036c85f95e19cc74fed5e767a10fb16e5413f527c80e6d4d45"
    ),
    "valid-vectors.json": LockedFile(
        123920, "59720c65e195e09c00cf89f86b4ce232628dbb64861c0d6c8065257f062de989"
    ),
    "valid-vectors.sha256": LockedFile(
        85, "d4fef0eccdca723a2b377baef5bdc1571c296745c33bf6b39a37ea23f9b1cc42"
    ),
}

EXPECTED_FORMATS = {
    "manifest.json": "faultatlas-revision-locator-contract-corpus-manifest",
    "valid-vectors.json": "faultatlas-revision-locator-valid-contract-vectors",
    "invalid-vectors.json": "faultatlas-revision-locator-invalid-contract-vectors",
    "replay-vectors.json": "faultatlas-revision-locator-replay-contract-vectors",
}
EXPECTED_TOP_LEVEL = {
    "manifest.json": {
        "assurance",
        "corpus_files",
        "corpus_identity",
        "execution_contract",
        "format",
        "non_goals",
        "originating_publications",
        "rejection_contract",
        "replay_contract",
        "scope",
        "source_decisions",
        "target_symbols",
        "vector_summary",
    },
    "valid-vectors.json": {"assurance", "fixtures", "format", "vectors"},
    "invalid-vectors.json": {"assurance", "format", "vectors"},
    "replay-vectors.json": {
        "artifact_locks",
        "assurance",
        "fixtures",
        "format",
        "vectors",
    },
}
EXPECTED_EXPORTS = {
    "ArtifactByteLocator",
    "BoundedLocator",
    "DiffHunkLocator",
    "GitBlobIdentity",
    "GitCommitIdentity",
    "GitCommitParentTopology",
    "GitHashAlgorithm",
    "GitObjectIdentity",
    "GitObjectKind",
    "GitRefName",
    "GitRefNamespace",
    "GitRefObservation",
    "GitRepositoryPath",
    "GitRevisionIdentity",
    "GitTreeIdentity",
    "LineEnding",
    "OneBasedInclusiveLineSpan",
    "RevisionLineLocator",
    "RevisionQualifiedPath",
    "RevisionRole",
    "RevisionRoleAssignment",
    "TextEncoding",
    "ZeroBasedHalfOpenByteSpan",
}
EXPECTED_EVIDENCE_EXPORTS = (
    "AcquisitionRunId",
    "RetrievalRequestOrdinal",
    "RetrievalRequestId",
    "RetrievalMethod",
    "RetrievalRoutePath",
    "RetrievalRequestReference",
    "MediaType",
    "ApiVersion",
    "RequestQueryParameter",
    "RetrievalRequestControls",
    "ResponseRepresentationState",
    "HttpStatusCode",
    "ContentEncoding",
    "MediaTypeParameter",
    "ResponseRepresentationObservation",
    "ArtifactDigestAlgorithm",
    "ArtifactDigestScope",
    "ArtifactSha256Digest",
    "ArtifactByteLength",
    "ArtifactDigest",
    "ExactArtifactIdentity",
    "ArtifactRetentionMode",
    "ExactRetainedArtifact",
    "AcquisitionRunStatus",
    "AcquisitionRequestMembership",
    "AcquisitionRun",
)
EXPECTED_VALID_CATEGORIES = {
    "commit-topology": 7,
    "coordinate-span": 6,
    "enum": 5,
    "git-object-identity": 13,
    "git-object-union": 4,
    "locator": 16,
    "locator-union": 3,
    "mutable-ref": 17,
    "revision-qualified-path": 20,
    "revision-role": 6,
}
EXPECTED_INVALID_CATEGORIES = {
    "commit-topology": 10,
    "coordinate-span": 15,
    "enum": 5,
    "git-object-identity": 14,
    "git-object-union": 4,
    "locator": 20,
    "locator-union": 4,
    "mutable-ref": 22,
    "revision-qualified-path": 20,
    "revision-role": 7,
}
EXPECTED_REPLAY_CATEGORIES = {
    "artifact-parent": 1,
    "byte-fact": 3,
    "hunk-derivation": 3,
    "reviewed-line-interpretation": 3,
}
EXPECTED_PRODUCTION_FILES = {
    "src/faultatlas/__init__.py",
    "src/faultatlas/__main__.py",
    "src/faultatlas/cli.py",
    "src/faultatlas/domain/__init__.py",
    "src/faultatlas/domain/compatibility.py",
    "src/faultatlas/domain/evidence.py",
    "src/faultatlas/domain/identity.py",
    "src/faultatlas/domain/revision.py",
    "src/faultatlas/domain/source.py",
}
EVIDENCE_MODULE_PATH = "src/faultatlas/domain/evidence.py"

VECTOR_ID_PATTERN = re.compile(
    r"^revision\.(?:valid|invalid|replay)\.[a-z0-9-]+(?:\.[a-z0-9-]+)+$"
)
FIXTURE_ID_PATTERN = re.compile(
    r"^revision\.fixture\.(?:valid|replay)\.[a-z0-9-]+(?:\.[a-z0-9-]+)*$"
)
HUNK_HEADER_PATTERN = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")

MODEL_TARGETS: dict[str, type[BaseModel]] = {
    "ArtifactByteLocator": ArtifactByteLocator,
    "DiffHunkLocator": DiffHunkLocator,
    "GitBlobIdentity": GitBlobIdentity,
    "GitCommitIdentity": GitCommitIdentity,
    "GitCommitParentTopology": GitCommitParentTopology,
    "GitRefName": GitRefName,
    "GitRefNamespace": GitRefNamespace,
    "GitRefObservation": GitRefObservation,
    "GitRepositoryPath": GitRepositoryPath,
    "GitTreeIdentity": revision_module.GitTreeIdentity,
    "OneBasedInclusiveLineSpan": OneBasedInclusiveLineSpan,
    "RevisionLineLocator": RevisionLineLocator,
    "RevisionQualifiedPath": RevisionQualifiedPath,
    "RevisionRoleAssignment": RevisionRoleAssignment,
    "ZeroBasedHalfOpenByteSpan": ZeroBasedHalfOpenByteSpan,
}
ENUM_TARGETS: dict[str, type[StrEnum]] = {
    "GitHashAlgorithm": GitHashAlgorithm,
    "GitObjectKind": GitObjectKind,
    "LineEnding": LineEnding,
    "RevisionRole": RevisionRole,
    "TextEncoding": TextEncoding,
}
ALIAS_TARGETS: dict[str, TypeAdapter[Any]] = {
    "BoundedLocator": TypeAdapter(BoundedLocator),
    "GitObjectIdentity": TypeAdapter(GitObjectIdentity),
    "GitRevisionIdentity": TypeAdapter(GitRevisionIdentity),
}
SUPPORT_MODEL_TARGETS: dict[str, type[BaseModel]] = {
    "ProviderAuthority": ProviderAuthority,
    "ProviderKey": ProviderKey,
    "ProviderRepositoryId": ProviderRepositoryId,
    "RepositoryIdentity": RepositoryIdentity,
}
SUPPORT_ENUM_TARGETS: dict[str, type[StrEnum]] = {
    "AuthorityRole": AuthorityRole,
    "SourceIdentityLifecycleState": SourceIdentityLifecycleState,
    **ENUM_TARGETS,
}
KNOWN_OPERATIONS = {
    "compare",
    "construct",
    "construct_sequence",
    "derive_hunk_locator",
    "enum_reject",
    "enum_values",
    "reject",
    "replay_byte_locator",
    "replay_reviewed_line_locator",
    "validate_alias",
    "verify_artifact",
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
    assert not isinstance(value, float), "floating-point value is forbidden"
    if isinstance(value, list):
        for item in cast(list[Any], value):
            _assert_no_float(item)
    elif isinstance(value, dict):
        for item in cast(dict[str, Any], value).values():
            _assert_no_float(item)


def _parse_canonical_json(raw: bytes) -> dict[str, Any]:
    assert not raw.startswith(b"\xef\xbb\xbf")
    assert b"\r" not in raw
    assert raw.endswith(b"\n")
    assert not raw.endswith(b"\n\n")
    value = json.loads(
        raw.decode("utf-8"),
        parse_float=_reject_number,
        parse_constant=_reject_number,
    )
    assert isinstance(value, dict)
    document = cast(dict[str, Any], value)
    _assert_no_float(document)
    assert _canonical_bytes(document) == raw
    assert _canonical_bytes(json.loads(_canonical_bytes(document))) == raw
    return document


def _load_document(filename: str) -> dict[str, Any]:
    return _parse_canonical_json((CORPUS_ROOT / filename).read_bytes())


def _documents() -> dict[str, dict[str, Any]]:
    return {filename: _load_document(filename) for filename in sorted(JSON_FILES)}


def _vectors(document: dict[str, Any]) -> list[dict[str, Any]]:
    raw = document["vectors"]
    assert isinstance(raw, list)
    assert all(isinstance(item, dict) for item in cast(list[Any], raw))
    return cast(list[dict[str, Any]], raw)


def _vector_by_id(document: dict[str, Any], vector_id: str) -> dict[str, Any]:
    matches = [vector for vector in _vectors(document) if vector["id"] == vector_id]
    assert len(matches) == 1
    return matches[0]


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
        assert FIXTURE_ID_PATTERN.fullmatch(fixture_id)
        assert fixture_id not in fixtures
        assert fixture["status"] == "locked"
        fixtures[fixture_id] = fixture
    return fixtures


def _resolve_fixture_value(
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
            return _resolve_fixture_value(
                fixtures[fixture_id]["value"], fixtures, (*stack, fixture_id)
            )
        assert not any(key.startswith("fixture_") for key in mapping)
        return {
            key: _resolve_fixture_value(item, fixtures, stack)
            for key, item in mapping.items()
        }
    if isinstance(value, list):
        return [
            _resolve_fixture_value(item, fixtures, stack)
            for item in cast(list[Any], value)
        ]
    return value


def _validate_fixture_graph(document: dict[str, Any]) -> None:
    fixtures = _fixture_map(document)
    for fixture_id, fixture in fixtures.items():
        _resolve_fixture_value(fixture["value"], fixtures, (fixture_id,))
    for vector in _vectors(document):
        _resolve_fixture_value(vector["input"], fixtures)

    references: set[str] = set()

    def collect(value: Any) -> None:
        if isinstance(value, dict):
            mapping = cast(dict[str, Any], value)
            if set(mapping) == {"fixture_ref"}:
                fixture_id = mapping["fixture_ref"]
                assert isinstance(fixture_id, str)
                references.add(fixture_id)
                return
            for item in mapping.values():
                collect(item)
        elif isinstance(value, list):
            for item in cast(list[Any], value):
                collect(item)

    for fixture in fixtures.values():
        collect(fixture["value"])
    for vector in _vectors(document):
        collect(vector["input"])
    assert references == set(fixtures)


MARKER_KEYS = {
    "bytes_value",
    "datetime_value",
    "enum_value",
    "float_value",
    "path_value",
    "surrogate_value",
    "synthetic_windows_drive_path",
    "tuple_value",
    "typed_value",
}


def _materialize_synthetic_input(value: Any, depth: int = 0) -> Any:
    assert depth <= 32
    if isinstance(value, list):
        return [
            _materialize_synthetic_input(item, depth + 1)
            for item in cast(list[Any], value)
        ]
    if not isinstance(value, dict):
        return value
    mapping = cast(dict[str, Any], value)
    if set(mapping) == {"synthetic_windows_drive_path"}:
        descriptor = mapping["synthetic_windows_drive_path"]
        assert isinstance(descriptor, dict)
        descriptor = cast(dict[str, Any], descriptor)
        assert set(descriptor) == {"drive", "path"}
        drive = descriptor["drive"]
        path = descriptor["path"]
        assert isinstance(drive, str) and re.fullmatch(r"[A-Z]", drive)
        assert isinstance(path, str) and "/" not in path and "\\" not in path
        return f"{drive}:/{path}"
    return {
        key: _materialize_synthetic_input(item, depth + 1)
        for key, item in mapping.items()
    }


def _decode_python_value(value: Any, depth: int = 0) -> Any:
    assert depth <= 32
    if isinstance(value, list):
        return [
            _decode_python_value(item, depth + 1) for item in cast(list[Any], value)
        ]
    if not isinstance(value, dict):
        return value
    mapping = cast(dict[str, Any], value)
    marker_keys = {
        key
        for key in mapping
        if key.endswith("_value") or key == "synthetic_windows_drive_path"
    }
    if marker_keys:
        assert len(mapping) == 1
        assert marker_keys <= MARKER_KEYS
    if set(mapping) == {"enum_value"}:
        descriptor = mapping["enum_value"]
        assert isinstance(descriptor, dict)
        descriptor = cast(dict[str, Any], descriptor)
        assert set(descriptor) == {"target", "value"}
        target = descriptor["target"]
        assert target in SUPPORT_ENUM_TARGETS
        return SUPPORT_ENUM_TARGETS[cast(str, target)](descriptor["value"])
    if set(mapping) == {"typed_value"}:
        descriptor = mapping["typed_value"]
        assert isinstance(descriptor, dict)
        descriptor = cast(dict[str, Any], descriptor)
        assert set(descriptor) == {"input", "target"}
        target = descriptor["target"]
        assert target in {**MODEL_TARGETS, **SUPPORT_MODEL_TARGETS}
        model = {**MODEL_TARGETS, **SUPPORT_MODEL_TARGETS}[cast(str, target)]
        return model.model_validate(
            _decode_python_value(descriptor["input"], depth + 1)
        )
    if set(mapping) == {"tuple_value"}:
        raw_items = mapping["tuple_value"]
        assert isinstance(raw_items, list)
        return tuple(
            _decode_python_value(item, depth + 1) for item in cast(list[Any], raw_items)
        )
    if set(mapping) == {"datetime_value"}:
        descriptor = mapping["datetime_value"]
        assert isinstance(descriptor, dict)
        descriptor = cast(dict[str, Any], descriptor)
        assert set(descriptor) == {"iso8601", "timezone_name"}
        raw_datetime = descriptor["iso8601"]
        timezone_name = descriptor["timezone_name"]
        assert isinstance(raw_datetime, str) and isinstance(timezone_name, str)
        parsed = datetime.fromisoformat(raw_datetime)
        assert parsed.utcoffset() == timedelta(0)
        return parsed.replace(tzinfo=timezone(timedelta(0), timezone_name))
    if set(mapping) == {"bytes_value"}:
        raw_bytes = mapping["bytes_value"]
        assert isinstance(raw_bytes, str)
        return raw_bytes.encode("utf-8")
    if set(mapping) == {"path_value"}:
        raw_path = mapping["path_value"]
        assert isinstance(raw_path, str)
        return Path(raw_path)
    if set(mapping) == {"surrogate_value"}:
        assert mapping["surrogate_value"] == "high"
        return "\ud800"
    if set(mapping) == {"float_value"}:
        raw_float = mapping["float_value"]
        assert raw_float in {"0.0", "1.0"}
        result = float(cast(str, raw_float))
        assert math.isfinite(result)
        return result
    assert "synthetic_windows_drive_path" not in mapping
    return {key: _decode_python_value(item, depth + 1) for key, item in mapping.items()}


def _json_text(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    )


def _validate_model(model: type[BaseModel], value: Any, input_mode: str) -> BaseModel:
    if input_mode == "json":
        return model.model_validate_json(_json_text(value))
    assert input_mode == "python"
    return model.model_validate(_decode_python_value(value))


def _validate_alias(adapter: TypeAdapter[Any], value: Any, input_mode: str) -> Any:
    if input_mode == "json":
        return adapter.validate_json(_json_text(value))
    assert input_mode == "python"
    return adapter.validate_python(_decode_python_value(value))


def _semantic_dump(value: BaseModel) -> Any:
    return value.model_dump(mode="json")


def _assert_canonical_utc(value: BaseModel) -> None:
    if isinstance(value, GitRefObservation):
        assert value.observed_at.tzinfo is UTC


def _round_trip_model(model: type[BaseModel], value: BaseModel) -> BaseModel:
    _assert_canonical_utc(value)
    reconstructed = model.model_validate_json(value.model_dump_json())
    assert reconstructed == value
    assert _semantic_dump(reconstructed) == _semantic_dump(value)
    _assert_canonical_utc(reconstructed)
    return reconstructed


def _round_trip_alias(adapter: TypeAdapter[Any], value: Any) -> Any:
    reconstructed = adapter.validate_json(adapter.dump_json(value))
    assert reconstructed == value
    assert adapter.dump_python(reconstructed, mode="json") == adapter.dump_python(
        value, mode="json"
    )
    return reconstructed


def _resolved_input(vector: dict[str, Any], document: dict[str, Any]) -> Any:
    resolved = _resolve_fixture_value(vector["input"], _fixture_map(document))
    return _materialize_synthetic_input(resolved)


def _assert_operation_target(vector: dict[str, Any]) -> None:
    operation = vector["operation"]
    target = vector["target_symbol"]
    assert operation in KNOWN_OPERATIONS
    if operation in {"construct", "compare", "construct_sequence"}:
        assert target in MODEL_TARGETS
    elif operation == "reject":
        assert target in MODEL_TARGETS or target in ALIAS_TARGETS
    elif operation in {"validate_alias"}:
        assert target in ALIAS_TARGETS
    elif operation in {"enum_values", "enum_reject"}:
        assert target in ENUM_TARGETS
    elif operation in {"verify_artifact", "replay_byte_locator"}:
        assert target == "ArtifactByteLocator"
    elif operation == "derive_hunk_locator":
        assert target == "DiffHunkLocator"
    else:
        assert operation == "replay_reviewed_line_locator"
        assert target == "RevisionLineLocator"


def _execute_valid_vector(vector: dict[str, Any], document: dict[str, Any]) -> None:
    _assert_operation_target(vector)
    expected = cast(dict[str, Any], vector["expected"])
    assert expected["outcome"] == "accepted"
    value = _resolved_input(vector, document)
    operation = vector["operation"]
    target = cast(str, vector["target_symbol"])
    input_mode = cast(str, vector["input_mode"])

    if operation == "enum_values":
        assert expected["round_trip_equal"] is False
        assert expected["concrete_type"] == target
        assert expected["runtime_target"] == target
        actual = [item.value for item in ENUM_TARGETS[target]]
        assert actual == expected["semantic_dump"]
        return

    if operation == "construct":
        result = _validate_model(MODEL_TARGETS[target], value, input_mode)
        actual: Any = _semantic_dump(result)
        reconstructed = _round_trip_model(MODEL_TARGETS[target], result)
        concrete_type = type(reconstructed).__name__
    elif operation == "validate_alias":
        adapter = ALIAS_TARGETS[target]
        result = _validate_alias(adapter, value, input_mode)
        actual = adapter.dump_python(result, mode="json")
        reconstructed = _round_trip_alias(adapter, result)
        concrete_type = type(reconstructed).__name__
    elif operation == "compare":
        assert isinstance(value, dict)
        raw = cast(dict[str, Any], value)
        assert set(raw) == {"left", "right"}
        model = MODEL_TARGETS[target]
        left = _validate_model(model, raw["left"], input_mode)
        right = _validate_model(model, raw["right"], input_mode)
        assert (left == right) is expected["comparison_equal"]
        _round_trip_model(model, left)
        _round_trip_model(model, right)
        actual = [_semantic_dump(left), _semantic_dump(right)]
        concrete_type = type(left).__name__
    else:
        assert operation == "construct_sequence"
        assert isinstance(value, dict)
        raw = cast(dict[str, Any], value)
        assert set(raw) == {"items"}
        assert isinstance(raw["items"], list)
        model = MODEL_TARGETS[target]
        results = [
            _validate_model(model, item, input_mode)
            for item in cast(list[Any], raw["items"])
        ]
        assert len(results) == 2
        assert results[0] != results[1]
        assert _semantic_dump(results[0]) != _semantic_dump(results[1])
        for result in results:
            _round_trip_model(model, result)
        actual = [_semantic_dump(result) for result in results]
        concrete_type = type(results[0]).__name__

    assert expected["round_trip_equal"] is True
    assert expected["runtime_target"] == target
    assert concrete_type == expected["concrete_type"]
    assert actual == expected["semantic_dump"]


def _invoke_invalid_vector(vector: dict[str, Any], document: dict[str, Any]) -> None:
    _assert_operation_target(vector)
    target = cast(str, vector["target_symbol"])
    value = _resolved_input(vector, document)
    if vector["operation"] == "enum_reject":
        ENUM_TARGETS[target](value)
        return
    assert vector["operation"] == "reject"
    if target in ALIAS_TARGETS:
        _validate_alias(ALIAS_TARGETS[target], value, cast(str, vector["input_mode"]))
    else:
        _validate_model(MODEL_TARGETS[target], value, cast(str, vector["input_mode"]))


def _assert_invalid_vector(vector: dict[str, Any], document: dict[str, Any]) -> None:
    expected = cast(dict[str, Any], vector["expected"])
    assert expected["outcome"] == "rejected"
    if vector["operation"] == "enum_reject":
        assert expected == {
            "error_location": [],
            "error_type": "enum_value_error",
            "failure_category": "controlled_registry_rejection",
            "outcome": "rejected",
        }
        with pytest.raises(ValueError):
            _invoke_invalid_vector(vector, document)
        return

    assert expected["failure_category"] == "validation_error"
    try:
        _invoke_invalid_vector(vector, document)
    except ValidationError as error:
        location = tuple(cast(list[str | int], expected["error_location"]))
        matches = [
            item
            for item in error.errors()
            if item["loc"] == location and item["type"] == expected["error_type"]
        ]
        assert matches, (
            f"{vector['id']} expected {location!r}/{expected['error_type']!r}; "
            f"got {error.errors()!r}"
        )
        if "message_contains" in expected:
            assert any(expected["message_contains"] in item["msg"] for item in matches)
        return
    raise AssertionError(f"invalid vector unexpectedly succeeded: {vector['id']}")


def _artifact_bytes() -> bytes:
    raw = ARTIFACT_PATH.read_bytes()
    assert len(raw) == 1640
    assert _sha256(raw) == (
        "dca87a4df1edb2d1acb3fc821724483ee874c2feba6525b2c21e79cb3e8f7312"
    )
    assert b"\r" not in raw
    assert raw.endswith(b"\n")
    assert len(raw.splitlines()) == 45
    return raw


def _line_span_bytes(raw: bytes, span: dict[str, Any]) -> bytes:
    lines = raw.splitlines(keepends=True)
    start = cast(int, span["start_line"])
    end = cast(int, span["end_line"])
    assert 1 <= start <= end <= len(lines)
    return b"".join(lines[start - 1 : end])


def _derive_hunk_span(start_text: str, count_text: str | None) -> dict[str, int] | None:
    start = int(start_text)
    count = 1 if count_text is None else int(count_text)
    if count == 0:
        return None
    return {"start_line": start, "end_line": start + count - 1}


def _locked_acquisition_document() -> dict[str, Any]:
    raw = (REPOSITORY_ROOT / ACQUISITION_RELATIVE).read_bytes()
    assert _sha256(raw) == ACQUISITION_SHA256
    return _parse_canonical_json(raw)


def _resolve_replay_source_pointer(
    vector: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    source_pointer = vector["source_pointer"]
    assert isinstance(source_pointer, dict)
    pointer = cast(dict[str, Any], source_pointer)
    assert set(pointer) == {"artifact_path", "document_path", "json_pointer"}
    assert pointer["artifact_path"] == ARTIFACT_RELATIVE
    assert pointer["document_path"] == ACQUISITION_RELATIVE
    json_pointer = pointer["json_pointer"]
    assert isinstance(json_pointer, str)

    acquisition = _locked_acquisition_document()
    if json_pointer == "/artifacts/0":
        raw_artifacts = acquisition["artifacts"]
        assert isinstance(raw_artifacts, list)
        artifacts = cast(list[Any], raw_artifacts)
        assert len(artifacts) >= 1
        source = artifacts[0]
        assert isinstance(source, dict)
        return cast(dict[str, Any], source), None

    match = re.fullmatch(
        r"/locators/([0-2])(?:/(applicable_new_file_line_ranges)/0)?",
        json_pointer,
    )
    assert match is not None
    raw_locators = acquisition["locators"]
    assert isinstance(raw_locators, list)
    locators = cast(list[Any], raw_locators)
    assert len(locators) == 3
    locator = locators[int(match.group(1))]
    assert isinstance(locator, dict)
    source_locator = cast(dict[str, Any], locator)
    if match.group(2) is None:
        return source_locator, source_locator
    raw_ranges = source_locator["applicable_new_file_line_ranges"]
    assert isinstance(raw_ranges, list)
    ranges = cast(list[Any], raw_ranges)
    assert len(ranges) == 1
    source = ranges[0]
    assert isinstance(source, dict)
    return cast(dict[str, Any], source), source_locator


def _source_line_span(source: dict[str, Any]) -> dict[str, int]:
    assert set(source) == {"end", "start"}
    start = source["start"]
    end = source["end"]
    assert isinstance(start, int) and isinstance(end, int)
    return {"start_line": start, "end_line": end}


def _assert_replay_vector(vector: dict[str, Any], document: dict[str, Any]) -> None:
    _assert_operation_target(vector)
    assert vector["input_mode"] == "replay"
    raw = _artifact_bytes()
    value = _resolved_input(vector, document)
    assert isinstance(value, dict)
    replay_input = cast(dict[str, Any], value)
    expected = cast(dict[str, Any], vector["expected"])
    operation = vector["operation"]
    expected_classification = {
        "artifact-parent": "exact_byte_locator_fact",
        "byte-fact": "exact_byte_locator_fact",
        "hunk-derivation": "deterministic_derivation",
        "reviewed-line-interpretation": "reviewed_derived_interpretation",
    }
    assert (
        vector["evidence_classification"]
        == expected_classification[cast(str, vector["category"])]
    )
    source, source_locator = _resolve_replay_source_pointer(vector)

    if operation == "verify_artifact":
        assert source_locator is None
        source_path = (
            PurePosixPath(ACQUISITION_RELATIVE).parent / cast(str, source["path"])
        ).as_posix()
        assert source_path == ARTIFACT_RELATIVE
        assert source["sha256"] == _sha256(raw)
        assert source["byte_length"] == len(raw)
        assert replay_input == {"artifact_path": ARTIFACT_RELATIVE}
        assert expected == {
            "byte_length": 1640,
            "final_lf": True,
            "line_count": 45,
            "line_ending": "lf",
            "sha256": _sha256(raw),
        }
        return

    if operation == "replay_byte_locator":
        assert source_locator is source
        assert (
            source["classification"]["byte_locator"]
            == vector["evidence_classification"]
        )
        assert (
            replay_input["locator"]["parent_artifact_sha256"]
            == source["parent_artifact_sha256"]
        )
        assert replay_input["locator"]["span"] == {
            "length": source["length"],
            "offset": source["offset"],
        }
        assert replay_input["selected_sha256"] == source["sha256"]
        assert replay_input["artifact_lines"] == {
            "end_line": source["diff_line_end"],
            "start_line": source["diff_line_start"],
        }
        locator = ArtifactByteLocator.model_validate_json(
            _json_text(replay_input["locator"])
        )
        assert _semantic_dump(locator) == expected["semantic_dump"]
        assert type(locator).__name__ == expected["concrete_type"]
        offset = locator.span.offset
        selected = raw[offset : offset + locator.span.length]
        assert len(selected) == locator.span.length
        assert _sha256(selected) == replay_input["selected_sha256"]
        assert _sha256(selected) == expected["selected_sha256"]
        assert _line_span_bytes(raw, replay_input["artifact_lines"]) == selected
        assert replay_input["artifact_lines"] == expected["artifact_lines"]
        return

    if operation == "derive_hunk_locator":
        assert source_locator is source
        assert (
            source["classification"]["hunk_and_additions"]
            == vector["evidence_classification"]
        )
        assert replay_input["locator"]["artifact_bytes"]["span"] == {
            "length": source["length"],
            "offset": source["offset"],
        }
        assert replay_input["artifact_line"] == source["diff_line_start"]
        assert replay_input["locator"]["artifact_lines"] == {
            "end_line": source["diff_line_end"],
            "start_line": source["diff_line_start"],
        }
        assert replay_input["new_path"] == source["repository_path"]
        assert replay_input["new_span"] == _source_line_span(
            cast(dict[str, Any], source["hunk_new_file_span"])
        )
        line_number = cast(int, replay_input["artifact_line"])
        artifact_lines = [item.decode("utf-8") for item in raw.splitlines()]
        line = artifact_lines[line_number - 1]
        match = HUNK_HEADER_PATTERN.match(line)
        assert match is not None
        assert line == replay_input["expected_header"] == expected["header"]
        header_lines = cast(dict[str, int], replay_input["file_header_lines"])
        actual_file_headers = {
            side: artifact_lines[number - 1] for side, number in header_lines.items()
        }
        assert actual_file_headers == replay_input["expected_file_headers"]
        assert actual_file_headers == expected["file_headers"]
        old_span = _derive_hunk_span(match.group(1), match.group(2))
        new_span = _derive_hunk_span(match.group(3), match.group(4))
        assert old_span == replay_input["old_span"] == expected["old_span"]
        assert new_span == replay_input["new_span"] == expected["new_span"]
        locator = DiffHunkLocator.model_validate_json(
            _json_text(replay_input["locator"])
        )
        assert _semantic_dump(locator) == expected["semantic_dump"]
        assert type(locator).__name__ == expected["concrete_type"]
        assert (
            None if locator.old_file is None else locator.old_file.path.root
        ) == replay_input["old_path"]
        assert (
            None if locator.new_file is None else locator.new_file.path.root
        ) == replay_input["new_path"]
        if old_span is None:
            assert actual_file_headers["old"] == "--- /dev/null"
            assert locator.old_file is None
        else:
            assert actual_file_headers["old"] == f"--- a/{replay_input['old_path']}"
        assert actual_file_headers["new"] == f"+++ b/{replay_input['new_path']}"
        return

    assert operation == "replay_reviewed_line_locator"
    assert source_locator is not None
    assert (
        source_locator["classification"]["role_and_applicability"]
        == vector["evidence_classification"]
    )
    assert replay_input["reviewed_range"] == _source_line_span(source)
    assert (
        replay_input["locator"]["parent"]["path"] == source_locator["repository_path"]
    )
    locator = RevisionLineLocator.model_validate_json(
        _json_text(replay_input["locator"])
    )
    assert _semantic_dump(locator) == expected["semantic_dump"]
    assert type(locator).__name__ == expected["concrete_type"]
    assert replay_input["reviewed_range"] == expected["reviewed_range"]
    assert locator.span.model_dump(mode="json") == expected["reviewed_range"]
    assert "applicability" not in expected["semantic_dump"]
    assert "review" not in expected["semantic_dump"]


def _assert_fs_regular_0644(path: Path) -> None:
    mode = path.lstat().st_mode
    assert not stat.S_ISLNK(mode)
    assert stat.S_ISREG(mode)
    assert stat.S_IMODE(mode) == 0o644


def _parse_git_stage(raw: bytes) -> dict[str, str]:
    modes: dict[str, str] = {}
    for entry in raw.split(b"\0"):
        if not entry:
            continue
        header, path_bytes = entry.split(b"\t", 1)
        mode, object_id, stage = header.decode("ascii").split(" ")
        assert re.fullmatch(r"[0-9a-f]{40,64}", object_id)
        assert stage == "0"
        path = path_bytes.decode("utf-8")
        assert path not in modes
        modes[path] = mode
    return modes


def _git_stage_modes(
    paths: set[str], environment: dict[str, str] | None = None
) -> dict[str, str]:
    result = subprocess.run(
        ["git", "ls-files", "--stage", "-z", "--", *sorted(paths)],
        cwd=REPOSITORY_ROOT,
        env=environment,
        check=True,
        capture_output=True,
    )
    return _parse_git_stage(result.stdout)


def _assert_git_modes_100644(modes: dict[str, str], expected: set[str]) -> None:
    assert set(modes) == expected
    assert set(modes.values()) == ({"100644"} if expected else set())


def _prospective_modes(paths: set[str], tmp_path: Path) -> dict[str, str]:
    environment = os.environ.copy()
    environment["GIT_INDEX_FILE"] = str(tmp_path / "prospective-index")
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
    return _git_stage_modes(paths, environment)


def _assert_corpus_inventory(root: Path) -> None:
    assert root.is_dir()
    contract_root = root.parent
    assert {entry.name for entry in contract_root.iterdir()} == {"closures", "v1"}
    entries = tuple(root.iterdir())
    assert {entry.name for entry in entries} == EXPECTED_FILES
    for entry in entries:
        _assert_fs_regular_0644(entry)
        relative = entry.relative_to(REPOSITORY_ROOT) if root == CORPUS_ROOT else None
        if relative is not None:
            pure = PurePosixPath(relative.as_posix())
            assert not pure.is_absolute()
            assert ".." not in pure.parts
    _assert_phase_closure_inventory(contract_root / "closures" / CLOSURE_ROOT.name)


def _assert_phase_closure_inventory(root: Path) -> None:
    assert root.is_dir() and not root.is_symlink()
    assert {entry.name for entry in root.parent.iterdir()} == {root.name}
    entries = tuple(root.iterdir())
    assert {entry.name for entry in entries} == EXPECTED_CLOSURE_FILES
    for entry in entries:
        _assert_fs_regular_0644(entry)
        relative = entry.relative_to(REPOSITORY_ROOT) if root == CLOSURE_ROOT else None
        if relative is not None:
            pure = PurePosixPath(relative.as_posix())
            assert not pure.is_absolute()
            assert ".." not in pure.parts


def _assert_locked_file(filename: str, raw: bytes) -> None:
    lock = EXPECTED_LOCKS[filename]
    assert len(raw) == lock.byte_length
    assert _sha256(raw) == lock.sha256


def _assert_sidecar(filename: str, raw: bytes, target_raw: bytes) -> None:
    assert not raw.startswith(b"\xef\xbb\xbf")
    assert b"\r" not in raw
    assert raw.endswith(b"\n")
    assert not raw.endswith(b"\n\n")
    expected_target = filename.removesuffix(".sha256") + ".json"
    expected = f"{_sha256(target_raw)}  {expected_target}\n".encode("ascii")
    assert raw == expected
    digest_text = raw[:64]
    assert re.fullmatch(rb"[0-9a-f]{64}", digest_text)


def _category_counts(document: dict[str, Any]) -> dict[str, int]:
    return dict(
        sorted(Counter(vector["category"] for vector in _vectors(document)).items())
    )


def _assert_manifest_integrity(documents: dict[str, dict[str, Any]]) -> None:
    manifest = documents["manifest.json"]
    assert set(manifest) == EXPECTED_TOP_LEVEL["manifest.json"]
    assert manifest["format"] == {
        "name": EXPECTED_FORMATS["manifest.json"],
        "version": "1",
    }
    assert manifest["corpus_identity"] == {
        "classification": [
            "internal",
            "case-calibrated",
            "source-repository-only",
            "non-public",
            "non-production-persistence",
            "independently-versioned",
        ],
        "id": "faultatlas-revision-locator-contract-corpus",
        "version": "1",
    }
    assert manifest["target_symbols"] == list(revision_module.__all__)
    assert set(cast(list[str], manifest["target_symbols"])) == EXPECTED_EXPORTS
    summary = cast(dict[str, Any], manifest["vector_summary"])
    valid = documents["valid-vectors.json"]
    invalid = documents["invalid-vectors.json"]
    replay = documents["replay-vectors.json"]
    assert summary == {
        "fixtures": {"replay": 3, "total": 18, "valid": 15},
        "invalid": {"categories": EXPECTED_INVALID_CATEGORIES, "count": 121},
        "replay": {"categories": EXPECTED_REPLAY_CATEGORIES, "count": 10},
        "total_vectors": 228,
        "valid": {"categories": EXPECTED_VALID_CATEGORIES, "count": 97},
    }
    assert _category_counts(valid) == EXPECTED_VALID_CATEGORIES
    assert _category_counts(invalid) == EXPECTED_INVALID_CATEGORIES
    assert _category_counts(replay) == EXPECTED_REPLAY_CATEGORIES
    corpus_files = cast(list[dict[str, Any]], manifest["corpus_files"])
    assert [item["filename"] for item in corpus_files] == [
        "manifest.json",
        "manifest.sha256",
        "valid-vectors.json",
        "valid-vectors.sha256",
        "invalid-vectors.json",
        "invalid-vectors.sha256",
        "replay-vectors.json",
        "replay-vectors.sha256",
        "contract.md",
    ]
    assert {item["filename"] for item in corpus_files} == EXPECTED_FILES
    for item in corpus_files:
        assert item["required"] is True
        assert item["filesystem_mode"] == "0644"
        assert item["git_mode"] == "100644"
        filename = cast(str, item["filename"])
        if filename in {
            "valid-vectors.json",
            "valid-vectors.sha256",
            "invalid-vectors.json",
            "invalid-vectors.sha256",
            "replay-vectors.json",
            "replay-vectors.sha256",
        }:
            assert item["byte_length"] == EXPECTED_LOCKS[filename].byte_length
            assert item["sha256"] == EXPECTED_LOCKS[filename].sha256
        else:
            assert item["digest_lock"] == "independent_tracked_test_oracle"
            assert "sha256" not in item
    assert "manifest_sha256" not in manifest
    assert manifest["assurance"]["manifest_self_digest"] is False
    assert manifest["assurance"]["package_exclusion"] == (
        "required_wheel_sdist_and_installed_resources"
    )
    assert manifest["assurance"]["correction_policy"] == (
        "new_version_or_append_only_correction_after_publication"
    )
    assert manifest["execution_contract"]["registry"] == {
        "adapter_targets": 3,
        "enum_targets": 5,
        "model_targets": 15,
        "support_enum_targets": 2,
        "support_model_targets": 4,
        "unknown_operation": "reject",
        "unknown_target": "reject",
    }
    assert manifest["execution_contract"]["coordinate_conventions"] == {
        "artifact_bytes": "zero_based_half_open_offset_and_length",
        "logical_lines": "one_based_inclusive_nonempty",
    }
    assert manifest["execution_contract"]["fixture_references"] == (
        "file_local_acyclic_explicit_only"
    )
    assert manifest["execution_contract"]["test_input_markers"] == {
        "allowed": sorted(MARKER_KEYS),
        "datetime_value": "aware_ISO8601_zero_offset_with_explicit_timezone_name",
        "float_value": "finite_decimal_text_for_rejection_probe_only",
        "malformed_or_unknown": "reject",
        "max_recursive_depth": 32,
        "shapes": "exact_singleton_objects",
        "support_enum_allowlist": [
            "AuthorityRole",
            "SourceIdentityLifecycleState",
        ],
        "support_model_allowlist": [
            "ProviderAuthority",
            "ProviderKey",
            "ProviderRepositoryId",
            "RepositoryIdentity",
        ],
        "surrogate_value": "high_surrogate_rejection_probe_only",
    }
    assert manifest["scope"]["source_only"] is True
    assert manifest["scope"]["slice"] == "S1.P02.S06"
    assert manifest["originating_publications"] == [
        {
            "primary_commit": "d5e779c9aa34dc7a686bab8066c09e4d78d8267b",
            "pull_request": 24,
            "reviewed_tree": "c0b2e944ac8a92aa38cfca686c5552d6e5b3a605",
            "slice_id": "S1.P02.S01",
            "squash": "3759a87dd4376660d2b470ea92b373e9267eb5e7",
        },
        {
            "primary_commit": "07173a0e38a830f31dc3070ff79f010124be23fb",
            "pull_request": 25,
            "reviewed_tree": "724722f88a98c96360665d46e4bf0cd45e407c2b",
            "slice_id": "S1.P02.S02",
            "squash": "a2aa200357c99bab61e45b8307451533954650b3",
        },
        {
            "primary_commit": "7e3ede17e80f7a69968b1a61fbc0a2bcad365782",
            "pull_request": 26,
            "reviewed_tree": "d6adf0dede5a55ab9018684e9668bf11691e486c",
            "slice_id": "S1.P02.S03",
            "squash": "4c7123a46f5de43e782db7dbc6b5786888212ab2",
        },
        {
            "primary_commit": "47f65982a40b8764df34a048c83934e47a4be754",
            "pull_request": 27,
            "reviewed_tree": "7ee0f80ad4b04c1055e3b990ce83d92dc3aa8d57",
            "slice_id": "S1.P02.S04",
            "squash": "7aeab56d6b3077b8f1c57b80335a55980f80e16f",
        },
        {
            "primary_commit": "4dcd2148dd33e5f1685426f3e923ffc6d41cf71a",
            "pull_request": 28,
            "reviewed_tree": "327da2ca96f200faaf56c15a73accdec01d94e76",
            "slice_id": "S1.P02.S05",
            "squash": "577ee3726c60fb3b8d99772bd17b6fe067c064bd",
        },
    ]
    expected_sources = [
        (
            [
                "decision:s07:d4-git-object-revision-and-ref",
                "decision:s07:d5-revision-qualified-locator-boundary",
            ],
            "reference_corpus/pytest-4412/decisions/"
            "s07-identity-revision-provenance/decision.json",
            "60ecb66565525cb21a924508794635072ae50e935d4791d9d91da5b6399ce866",
        ),
        (
            ["faultatlas-s1-p01-identity-primitives-phase-closure"],
            "reference_corpus/contracts/identity/closures/"
            "s1-p01-phase-closure/closure.json",
            "2c1bfb9d3d596711066796ef83999d49b6846e65315a301eead7fa8fb5ac4642",
        ),
        (
            ["run-0001-s04-v1-base-4c9cde74-head-690a63b9"],
            ACQUISITION_RELATIVE,
            "1c29093bf1537e9b824a18df1848b71a8da014f544bc9f385707eb0e000a1318",
        ),
    ]
    assert manifest["source_decisions"] == [
        {"authority_ids": ids, "path": path, "sha256": digest}
        for ids, path, digest in expected_sources
    ]
    for authority_ids, relative, digest in expected_sources:
        raw = (REPOSITORY_ROOT / relative).read_bytes()
        assert _sha256(raw) == digest
        decoded = raw.decode("utf-8")
        assert all(authority_id in decoded for authority_id in authority_ids)
    assert manifest["replay_contract"]["artifact"] == {
        "byte_length": 1640,
        "path": ARTIFACT_RELATIVE,
        "sha256": "dca87a4df1edb2d1acb3fc821724483ee874c2feba6525b2c21e79cb3e8f7312",
    }
    assert manifest["replay_contract"]["production_lookup"] == "none"


def _assert_vector_structure(documents: dict[str, dict[str, Any]]) -> None:
    seen: set[str] = set()
    for filename in (
        "valid-vectors.json",
        "invalid-vectors.json",
        "replay-vectors.json",
    ):
        document = documents[filename]
        _validate_fixture_graph(document)
        for vector in _vectors(document):
            expected_keys = {
                "category",
                "expected",
                "id",
                "input",
                "input_mode",
                "operation",
                "purpose",
                "rationale",
                "status",
                "target_symbol",
            }
            if filename == "replay-vectors.json":
                expected_keys |= {"evidence_classification", "source_pointer"}
            else:
                expected_keys.add("decision_references")
            assert set(vector) == expected_keys
            vector_id = vector["id"]
            assert isinstance(vector_id, str)
            assert VECTOR_ID_PATTERN.fullmatch(vector_id)
            assert vector_id not in seen
            seen.add(vector_id)
            assert vector["status"] == "locked"
            assert vector["target_symbol"] in EXPECTED_EXPORTS
            _assert_operation_target(vector)
    assert len(seen) == 228


def _assert_export_coverage(documents: dict[str, dict[str, Any]]) -> None:
    assert (
        revision_module.__all__ == list(EXPECTED_EXPORTS)
        or set(revision_module.__all__) == EXPECTED_EXPORTS
    )
    assert len(revision_module.__all__) == 23
    assert not (
        EXPECTED_EXPORTS
        - set(cast(list[str], documents["manifest.json"]["target_symbols"]))
    )
    covered = {
        cast(str, vector["target_symbol"])
        for filename in (
            "valid-vectors.json",
            "invalid-vectors.json",
            "replay-vectors.json",
        )
        for vector in _vectors(documents[filename])
    }
    assert covered == EXPECTED_EXPORTS


def _assert_evidence_is_outside_revision_locator_contract(
    documents: dict[str, dict[str, Any]],
) -> None:
    manifest = documents["manifest.json"]
    evidence_exports = set(EXPECTED_EVIDENCE_EXPORTS)
    manifest_targets = set(cast(list[str], manifest["target_symbols"]))
    vector_targets = {
        cast(str, vector["target_symbol"])
        for filename in (
            "valid-vectors.json",
            "invalid-vectors.json",
            "replay-vectors.json",
        )
        for vector in _vectors(documents[filename])
    }

    assert evidence_module.__all__ == list(EXPECTED_EVIDENCE_EXPORTS)
    assert len(evidence_module.__all__) == 26
    assert evidence_exports.isdisjoint(manifest_targets)
    assert evidence_exports.isdisjoint(vector_targets)
    assert manifest["scope"]["production_module"] == "faultatlas.domain.revision"
    assert "faultatlas.domain.evidence" not in _json_text(manifest["scope"])
    assert manifest["vector_summary"]["total_vectors"] == 228
    assert (
        sum(
            len(_vectors(documents[filename]))
            for filename in (
                "valid-vectors.json",
                "invalid-vectors.json",
                "replay-vectors.json",
            )
        )
        == 228
    )
    _assert_package_root_exports(faultatlas.__all__)
    assert getattr(domain_package, "__all__", None) in (None, [])
    assert evidence_exports.isdisjoint(vars(faultatlas))
    assert evidence_exports.isdisjoint(vars(domain_package))
    for filename in EXPECTED_LOCKS:
        _assert_locked_file(filename, (CORPUS_ROOT / filename).read_bytes())


def _assert_semantic_boundaries(documents: dict[str, dict[str, Any]]) -> None:
    manifest = documents["manifest.json"]
    non_goals = set(cast(list[str], manifest["non_goals"]))
    assert non_goals == {
        "Evidence_Envelope",
        "Git_tag_object_identity",
        "S1.P02_phase_closure",
        "ancestry_or_reachability",
        "applicability_or_review_semantics",
        "canonical_production_serialization",
        "columns",
        "empty_line_spans",
        "entry_kinds",
        "locator_resolution",
        "migration",
        "mixed_or_bare_CR_line_endings",
        "non_UTF_8_path_bytes",
        "path_existence",
        "persistence",
        "production_corpus_reader_writer_or_validator",
        "production_locator_reader_or_resolver",
        "production_wire_format",
        "provider_SDK",
        "public_API",
        "public_JSON_Schema",
        "replacement_for_P01_identity_corpus",
        "repository_membership",
        "symbolic_refs",
        "universal_Git_compatibility",
        "zero_length_byte_selections",
    }
    valid_text = _json_text(documents["valid-vectors.json"])
    for forbidden in (
        '"applicability"',
        '"column"',
        '"entry_kind"',
        '"history"',
        '"resolver"',
        '"symbolic_ref"',
    ):
        assert forbidden not in valid_text
    for vector in _vectors(documents["invalid-vectors.json"]):
        purpose = cast(str, vector["purpose"]).casefold()
        if any(
            term in _json_text(vector["input"]).casefold()
            for term in ("applicability", "column", "history", "resolver", "symbolic")
        ):
            assert vector["expected"]["outcome"] == "rejected"
            assert "reject" in purpose
    replay_text = _json_text(documents["replay-vectors.json"])
    assert '"applicability"' not in replay_text
    assert '"reviewed_derived_interpretation"' in replay_text
    assert manifest["replay_contract"]["production_replay_io"] is False


def _assert_no_production_reader_or_resolver(
    sources: dict[str, bytes] | None = None,
) -> None:
    if sources is None:
        sources = {
            path.relative_to(REPOSITORY_ROOT).as_posix(): path.read_bytes()
            for path in (REPOSITORY_ROOT / "src").rglob("*.py")
        }
    assert set(sources) == EXPECTED_PRODUCTION_FILES
    for relative, raw in sources.items():
        tree = ast.parse(raw, filename=relative)
        definitions = {
            node.name
            for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
        }
        for name in definitions:
            lowered = name.casefold()
            assert not (
                "revision" in lowered
                and "locator" in lowered
                and any(
                    verb in lowered
                    for verb in ("load", "read", "resolve", "validate", "write")
                )
            )
            assert not ("locator" in lowered and "resolve" in lowered)
        assert CORPUS_RELATIVE.encode() not in raw
    _assert_package_root_exports(faultatlas.__all__)
    assert getattr(domain_package, "__all__", None) in (None, [])


def _assert_package_root_exports(exports: list[str]) -> None:
    assert exports == ["__version__"]


def _assert_privacy_bytes(raw: bytes) -> None:
    lowered = raw.lower()
    for forbidden in (
        b"/home/",
        b"/root/",
        b"/users/",
        b"authorization:",
        b'"authorization"',
        b"bearer ",
        b"authorization: bearer",
        b"begin openssh private key",
        b"begin private key",
        b"client-secret",
        b"client_secret",
        b"ghp_",
        b"github_pat_",
        b"secret-key",
        b"secret_key",
        b"x-access-token",
        b"x-api-key",
    ):
        assert forbidden not in lowered
    text = raw.decode("utf-8")
    separator_normalized = re.sub(r"[_-]+", " ", text.casefold())
    assert re.search(r"(?i)(?:^|[^a-z0-9])[a-z]:[\\/]", text) is None
    assert re.search(r"(?i)(?:^|[^a-z0-9])/tmp(?:[\\/])", text) is None
    assert (
        re.search(
            r"\b(?:credentials?|password|passwd|tokens?|secrets?|api keys?)\b",
            separator_normalized,
        )
        is None
    )
    assert re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text) is None


def _assert_no_raw_provider_response(value: Any) -> None:
    if isinstance(value, dict):
        for key, item in cast(dict[str, Any], value).items():
            normalized = re.sub(r"[^a-z0-9]", "", key.casefold())
            assert not (
                ("provider" in normalized and "response" in normalized)
                or ("raw" in normalized and "response" in normalized)
                or ("response" in normalized and "body" in normalized)
                or ("raw" in normalized and "payload" in normalized)
                or ("raw" in normalized and "body" in normalized)
            )
            _assert_no_raw_provider_response(item)
    elif isinstance(value, list):
        for item in cast(list[Any], value):
            _assert_no_raw_provider_response(item)


def _assert_privacy_and_retention() -> None:
    raw = b"\n".join(
        (CORPUS_ROOT / name).read_bytes() for name in sorted(EXPECTED_FILES)
    )
    _assert_privacy_bytes(raw)
    for document in _documents().values():
        _assert_no_raw_provider_response(document)


@dataclass(frozen=True)
class ArchiveMember:
    name: str
    kind: str
    data: bytes | None = None


def _archive_path_parts(member: ArchiveMember) -> tuple[str, ...]:
    name = member.name
    assert name and "\x00" not in name and "\\" not in name
    assert not name.startswith("/")
    assert re.match(r"^[A-Za-z]:", name) is None
    path_text = name[:-1] if member.kind == "directory" and name.endswith("/") else name
    parts = tuple(path_text.split("/"))
    assert all(part not in {"", ".", ".."} for part in parts)
    assert member.kind not in {"link", "special"}
    return parts


def _read_wheel(path: Path) -> tuple[ArchiveMember, ...]:
    members: list[ArchiveMember] = []
    with zipfile.ZipFile(path) as archive:
        for info in archive.infolist():
            mode = info.external_attr >> 16
            if stat.S_ISLNK(mode):
                members.append(ArchiveMember(info.filename, "link"))
            elif info.is_dir():
                members.append(ArchiveMember(info.filename, "directory"))
            else:
                members.append(ArchiveMember(info.filename, "file", archive.read(info)))
    return tuple(members)


def _read_sdist(path: Path) -> tuple[ArchiveMember, ...]:
    members: list[ArchiveMember] = []
    with tarfile.open(path, mode="r:gz") as archive:
        for info in archive.getmembers():
            if info.issym() or info.islnk():
                members.append(ArchiveMember(info.name, "link"))
            elif info.isdir():
                members.append(ArchiveMember(info.name, "directory"))
            elif info.isfile():
                stream = archive.extractfile(info)
                assert stream is not None
                members.append(ArchiveMember(info.name, "file", stream.read()))
            else:
                members.append(ArchiveMember(info.name, "special"))
    return tuple(members)


def _working_source_bytes() -> dict[str, bytes]:
    sources = {
        path.relative_to(REPOSITORY_ROOT).as_posix(): path.read_bytes()
        for path in (REPOSITORY_ROOT / "src").rglob("*.py")
    }
    assert set(sources) == EXPECTED_PRODUCTION_FILES
    assert len(sources) == 9
    return sources


def _archive_source_bytes(members: tuple[ArchiveMember, ...]) -> dict[str, bytes]:
    sources: dict[str, bytes] = {}
    for member in members:
        if member.kind != "file" or not member.name.endswith(".py"):
            continue
        parts = _archive_path_parts(member)
        assert "faultatlas" in parts
        index = parts.index("faultatlas")
        relative = "src/" + "/".join(parts[index:])
        assert relative not in sources
        assert member.data is not None
        sources[relative] = member.data
    return sources


def _assert_safe_archive(
    members: tuple[ArchiveMember, ...],
    *,
    project_license: bytes,
    historical_license: bytes,
    tests_forbidden: bool,
) -> None:
    assert members
    licenses: list[bytes] = []
    for member in members:
        parts = _archive_path_parts(member)
        lowered = {part.casefold() for part in parts}
        assert "reference_corpus" not in lowered
        assert CORPUS_RELATIVE not in member.name
        if tests_forbidden:
            assert "tests" not in lowered
        if member.kind != "file":
            continue
        assert member.data is not None
        assert member.data != historical_license
        if parts[-1] == "LICENSE":
            licenses.append(member.data)
    assert licenses == [project_license]
    packaged = _archive_source_bytes(members)
    working = _working_source_bytes()
    assert set(packaged) == EXPECTED_PRODUCTION_FILES
    assert packaged[EVIDENCE_MODULE_PATH] == working[EVIDENCE_MODULE_PATH]
    assert packaged == working


def _git_status() -> bytes:
    return subprocess.run(
        ["git", "status", "--porcelain=v1", "-z", "--untracked-files=all"],
        cwd=REPOSITORY_ROOT,
        check=True,
        capture_output=True,
    ).stdout


def _repository_snapshot() -> tuple[tuple[str, int, str], ...]:
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


@pytest.mark.parametrize("filename", sorted(EXPECTED_FILES))
def test_independent_digest_oracle(filename: str) -> None:
    _assert_locked_file(filename, (CORPUS_ROOT / filename).read_bytes())


@pytest.mark.parametrize("filename", sorted(JSON_FILES))
def test_canonical_json(filename: str) -> None:
    document = _load_document(filename)
    assert set(document) == EXPECTED_TOP_LEVEL[filename]
    assert document["format"] == {"name": EXPECTED_FORMATS[filename], "version": "1"}


@pytest.mark.parametrize("filename", sorted(SIDECAR_FILES))
def test_exact_sidecars(filename: str) -> None:
    target = filename.removesuffix(".sha256") + ".json"
    _assert_sidecar(
        filename,
        (CORPUS_ROOT / filename).read_bytes(),
        (CORPUS_ROOT / target).read_bytes(),
    )


def test_exact_inventory_and_permissions(tmp_path: Path) -> None:
    _assert_corpus_inventory(CORPUS_ROOT)
    expected_paths = {
        *(f"{CORPUS_RELATIVE}/{name}" for name in EXPECTED_FILES),
        *(f"{CLOSURE_RELATIVE}/{name}" for name in EXPECTED_CLOSURE_FILES),
    }
    actual_modes = _git_stage_modes(expected_paths)
    untracked = expected_paths - set(actual_modes)
    _assert_git_modes_100644(actual_modes, expected_paths - untracked)
    if untracked:
        for relative in untracked:
            status = subprocess.run(
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
            ).stdout
            assert status == f"?? {relative}\0".encode()
        prospective = _prospective_modes(untracked, tmp_path)
        _assert_git_modes_100644(prospective, untracked)


def test_manifest_vector_and_fixture_integrity() -> None:
    documents = _documents()
    _assert_manifest_integrity(documents)
    _assert_vector_structure(documents)


VALID_DOCUMENT = _load_document("valid-vectors.json")
INVALID_DOCUMENT = _load_document("invalid-vectors.json")
REPLAY_DOCUMENT = _load_document("replay-vectors.json")


@pytest.mark.parametrize(
    "vector",
    _vectors(VALID_DOCUMENT),
    ids=lambda vector: cast(dict[str, Any], vector)["id"],
)
def test_valid_vector_execution(vector: dict[str, Any]) -> None:
    _execute_valid_vector(vector, VALID_DOCUMENT)


def test_ref_observation_oracles_are_failure_sensitive() -> None:
    utc_vector = _vector_by_id(
        VALID_DOCUMENT, "revision.valid.ref-observation.python-strict"
    )
    utc_value = _resolved_input(utc_vector, VALID_DOCUMENT)
    observation = _validate_model(GitRefObservation, utc_value, "python")
    assert isinstance(observation, GitRefObservation)
    _assert_canonical_utc(observation)
    noncanonical = observation.model_copy(
        update={
            "observed_at": observation.observed_at.replace(
                tzinfo=timezone(timedelta(0), "equivalent-zero-offset")
            )
        }
    )
    assert noncanonical.observed_at.utcoffset() == timedelta(0)
    assert noncanonical.observed_at.tzinfo is not UTC
    with pytest.raises(AssertionError):
        _assert_canonical_utc(noncanonical)

    repository_vector = _vector_by_id(
        VALID_DOCUMENT,
        "revision.valid.ref-observation.cross-repository-distinct",
    )
    repository_value = _resolved_input(repository_vector, VALID_DOCUMENT)
    assert isinstance(repository_value, dict)
    sides = cast(dict[str, Any], repository_value)
    left = copy.deepcopy(cast(dict[str, Any], sides["left"]))
    right = copy.deepcopy(cast(dict[str, Any], sides["right"]))
    left_repository = cast(dict[str, Any], left["repository_identity"])
    right_repository = cast(dict[str, Any], right["repository_identity"])
    assert left_repository["provider"] == right_repository["provider"] == "github"
    assert (
        left_repository["provider_repository_id"]
        != right_repository["provider_repository_id"]
    )
    right_repository["provider_repository_id"] = left_repository[
        "provider_repository_id"
    ]
    assert right == left


@pytest.mark.parametrize(
    "vector",
    _vectors(INVALID_DOCUMENT),
    ids=lambda vector: cast(dict[str, Any], vector)["id"],
)
def test_invalid_vector_execution(vector: dict[str, Any]) -> None:
    _assert_invalid_vector(vector, INVALID_DOCUMENT)


@pytest.mark.parametrize(
    "vector",
    _vectors(REPLAY_DOCUMENT),
    ids=lambda vector: cast(dict[str, Any], vector)["id"],
)
def test_replay_vector_execution(vector: dict[str, Any]) -> None:
    _assert_replay_vector(vector, REPLAY_DOCUMENT)


def test_registry_fixture_and_source_safety() -> None:
    with pytest.raises(AssertionError):
        _assert_operation_target(
            {"operation": "construct", "target_symbol": "unknown.Target"}
        )
    with pytest.raises(AssertionError):
        _assert_operation_target(
            {"operation": "unknown_operation", "target_symbol": "GitCommitIdentity"}
        )
    with pytest.raises(ValueError):
        GitHashAlgorithm("sha512")
    for mutated in (
        {"fixture_ref": "revision.fixture.valid.missing"},
        {"fixture_pointer": "/fixtures/0"},
        {"fixture_link": "revision.fixture.valid.repository.github"},
        {"fixture_ref": "../valid-vectors.json"},
    ):
        with pytest.raises(AssertionError):
            _resolve_fixture_value(mutated, _fixture_map(VALID_DOCUMENT))
    duplicate = {
        "fixtures": [
            {"id": "revision.fixture.valid.duplicate", "status": "locked", "value": 1},
            {"id": "revision.fixture.valid.duplicate", "status": "locked", "value": 2},
        ],
        "vectors": [],
    }
    with pytest.raises(AssertionError):
        _fixture_map(duplicate)
    self_reference = {
        "fixtures": [
            {
                "id": "revision.fixture.valid.self",
                "status": "locked",
                "value": {"fixture_ref": "revision.fixture.valid.self"},
            }
        ],
        "vectors": [],
    }
    with pytest.raises(AssertionError):
        _validate_fixture_graph(self_reference)
    cycle = {
        "fixtures": [
            {
                "id": "revision.fixture.valid.cycle-a",
                "status": "locked",
                "value": {"fixture_ref": "revision.fixture.valid.cycle-b"},
            },
            {
                "id": "revision.fixture.valid.cycle-b",
                "status": "locked",
                "value": {"fixture_ref": "revision.fixture.valid.cycle-a"},
            },
        ],
        "vectors": [],
    }
    with pytest.raises(AssertionError):
        _validate_fixture_graph(cycle)
    for malformed_marker in (
        {"unknown_value": "unsafe"},
        {"unknown_value": "unsafe", "extra": True},
        {"bytes_value": "unsafe", "extra": True},
        {
            "synthetic_windows_drive_path": {"drive": "C", "path": "unsafe"},
            "extra": True,
        },
    ):
        with pytest.raises(AssertionError):
            _decode_python_value(malformed_marker)
    source = Path(__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    forbidden_calls = {
        "eval",
        "exec",
        "__import__",
        "import_module",
        "load_module",
    }
    calls = {
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    assert not (calls & forbidden_calls)


def test_export_coverage_and_semantic_boundaries() -> None:
    documents = _documents()
    _assert_export_coverage(documents)
    _assert_evidence_is_outside_revision_locator_contract(documents)
    _assert_semantic_boundaries(documents)
    _assert_no_production_reader_or_resolver()
    relative_paths = {
        path.relative_to(REPOSITORY_ROOT).as_posix()
        for path in REPOSITORY_ROOT.rglob("*")
    }
    expected_closure_paths = {
        CLOSURE_RELATIVE,
        *(f"{CLOSURE_RELATIVE}/{name}" for name in EXPECTED_CLOSURE_FILES),
    }
    assert {
        path for path in relative_paths if path.startswith(CLOSURE_RELATIVE)
    } == expected_closure_paths
    _assert_phase_closure_inventory(CLOSURE_ROOT)


def test_markdown_is_synchronized_and_non_authoritative() -> None:
    markdown = (CORPUS_ROOT / "contract.md").read_text(encoding="utf-8")
    assert "Internal, non-public" in markdown
    assert EXPECTED_LOCKS["manifest.json"].sha256 in markdown
    assert (
        "Derived, non-authoritative Markdown; the canonical JSON files remain "
        "the sole contract authority."
    ) in markdown
    for symbol in revision_module.__all__:
        assert f"`{symbol}`" in markdown
    for category, count in EXPECTED_VALID_CATEGORIES.items():
        assert f'"{category}": {count}' in markdown
    for category, count in EXPECTED_INVALID_CATEGORIES.items():
        assert f'"{category}": {count}' in markdown
    assert "one-based inclusive" in markdown
    assert "zero-based half-open" in markdown
    assert "adds no production reader" in markdown
    assert "wheel, sdist, and installed resources" in markdown


def test_privacy_and_retention_boundaries() -> None:
    _assert_privacy_and_retention()
    for leak in (
        b'"/root/private/file"',
        b'"C:/Users/private/file"',
        b'"D:\\\\Users\\\\private\\\\file"',
        b'"/tmp/private-task/output"',
        b'"credential=private"',
        b'"token=private"',
        b'{"access_token":"private"}',
        b'{"refresh_token":"private"}',
        b'{"api_key":"private"}',
        b'"Authorization: Bearer private"',
        b'"private@example.invalid"',
        b'"-----BEGIN OPENSSH PRIVATE KEY-----"',
    ):
        with pytest.raises(AssertionError):
            _assert_privacy_bytes(leak)
    for raw_response in (
        {"rawProviderResponseBody": {"private": True}},
        {"provider_response": {"private": True}},
        {"response_body": {"private": True}},
        {"raw_payload": {"private": True}},
    ):
        with pytest.raises(AssertionError):
            _assert_no_raw_provider_response(raw_response)


REQUIRED_MUTATIONS = (
    "changed-primary-json-byte",
    "coherent-json-sidecar-reseal",
    "uppercase-sidecar-digest",
    "wrong-sidecar-basename",
    "wrong-sidecar-spacing",
    "missing-terminal-lf",
    "extra-terminal-lf",
    "pretty-json",
    "unsorted-json",
    "inserted-float",
    "duplicate-vector-id",
    "unknown-target-symbol",
    "missing-export-coverage",
    "valid-wrong-expected-dump",
    "invalid-changed-to-valid",
    "invalid-wrong-error-location",
    "replay-artifact-digest-changed",
    "replay-artifact-byte-length-changed",
    "byte-offset-changed",
    "byte-length-changed",
    "selected-byte-digest-changed",
    "artifact-line-span-changed",
    "hunk-header-changed",
    "old-new-span-changed",
    "evidence-classification-changed",
    "source-pointer-swapped",
    "reviewed-line-range-changed",
    "line-semantics-zero-based",
    "byte-semantics-inclusive-end",
    "locator-discriminator-removed",
    "locator-discriminator-changed",
    "fixture-missing",
    "fixture-cycle",
    "manifest-count-changed",
    "manifest-file-digest-changed",
    "extra-corpus-file",
    "mutable-latest-pointer",
    "git-mode-100755",
    "filesystem-mode-0755",
    "filesystem-mode-0600",
    "corpus-symlink-or-special-file",
    "production-reader-inserted",
    "production-resolver-inserted",
    "package-root-export-inserted",
    "synthetic-package-corpus-member",
    "historical-pytest-license-inserted",
    "closure-artifact-inside-v1",
)
assert len(REQUIRED_MUTATIONS) == 47


def _copied_documents() -> dict[str, dict[str, Any]]:
    return {
        "manifest.json": copy.deepcopy(_load_document("manifest.json")),
        "valid-vectors.json": copy.deepcopy(VALID_DOCUMENT),
        "invalid-vectors.json": copy.deepcopy(INVALID_DOCUMENT),
        "replay-vectors.json": copy.deepcopy(REPLAY_DOCUMENT),
    }


def _synthetic_package_members(
    *, extra_name: str, extra_data: bytes
) -> tuple[ArchiveMember, ...]:
    project_license = (REPOSITORY_ROOT / "LICENSE").read_bytes()
    members = [
        ArchiveMember(relative.removeprefix("src/"), "file", data)
        for relative, data in sorted(_working_source_bytes().items())
    ]
    members.extend(
        [
            ArchiveMember(
                "faultatlas-0.1.0.dist-info/licenses/LICENSE",
                "file",
                project_license,
            ),
            ArchiveMember(extra_name, "file", extra_data),
        ]
    )
    return tuple(members)


def test_package_inspector_rejects_non_python_wheel_test_member() -> None:
    project_license = (REPOSITORY_ROOT / "LICENSE").read_bytes()
    historical_license = (
        REPOSITORY_ROOT / "reference_corpus/pytest-4412/acquisitions/"
        "run-0001-s04-v1-base-4c9cde74-head-690a63b9/artifacts/LICENSE"
    ).read_bytes()
    members = _synthetic_package_members(
        extra_name="tests/data.json", extra_data=b"{}\n"
    )
    with pytest.raises(AssertionError):
        _assert_safe_archive(
            members,
            project_license=project_license,
            historical_license=historical_license,
            tests_forbidden=True,
        )
    _assert_safe_archive(
        members,
        project_license=project_license,
        historical_license=historical_license,
        tests_forbidden=False,
    )


@pytest.mark.parametrize("mutation", REQUIRED_MUTATIONS)
def test_required_mutation_is_rejected(mutation: str, tmp_path: Path) -> None:
    if mutation == "changed-primary-json-byte":
        raw = bytearray((CORPUS_ROOT / "valid-vectors.json").read_bytes())
        raw[1] ^= 1
        with pytest.raises(AssertionError):
            _assert_locked_file("valid-vectors.json", bytes(raw))
        return

    if mutation == "coherent-json-sidecar-reseal":
        document = copy.deepcopy(VALID_DOCUMENT)
        document["assurance"]["status"] = "coherently_resealed"
        raw = _canonical_bytes(document)
        sidecar = f"{_sha256(raw)}  valid-vectors.json\n".encode("ascii")
        _assert_sidecar("valid-vectors.sha256", sidecar, raw)
        with pytest.raises(AssertionError):
            _assert_locked_file("valid-vectors.json", raw)
        return

    if mutation in {
        "uppercase-sidecar-digest",
        "wrong-sidecar-basename",
        "wrong-sidecar-spacing",
    }:
        target = (CORPUS_ROOT / "valid-vectors.json").read_bytes()
        sidecar = (CORPUS_ROOT / "valid-vectors.sha256").read_bytes()
        if mutation == "uppercase-sidecar-digest":
            sidecar = sidecar[:64].upper() + sidecar[64:]
        elif mutation == "wrong-sidecar-basename":
            sidecar = sidecar.replace(b"valid-vectors.json", b"manifest.json")
        else:
            sidecar = sidecar[:64] + b" " + sidecar[66:]
        with pytest.raises(AssertionError):
            _assert_sidecar("valid-vectors.sha256", sidecar, target)
        return

    if mutation in {
        "missing-terminal-lf",
        "extra-terminal-lf",
        "pretty-json",
        "unsorted-json",
        "inserted-float",
    }:
        raw = (CORPUS_ROOT / "valid-vectors.json").read_bytes()
        if mutation == "missing-terminal-lf":
            raw = raw[:-1]
        elif mutation == "extra-terminal-lf":
            raw += b"\n"
        elif mutation == "pretty-json":
            raw = (
                json.dumps(
                    VALID_DOCUMENT, ensure_ascii=False, indent=2, sort_keys=True
                ).encode("utf-8")
                + b"\n"
            )
        elif mutation == "unsorted-json":
            raw = b'{"z":0,"a":0}\n'
        else:
            document = copy.deepcopy(VALID_DOCUMENT)
            document["assurance"]["forbidden_float"] = 1.5
            raw = _canonical_bytes(document)
        with pytest.raises(AssertionError):
            _parse_canonical_json(raw)
        return

    if mutation in {"duplicate-vector-id", "unknown-target-symbol"}:
        documents = _copied_documents()
        vectors = _vectors(documents["valid-vectors.json"])
        if mutation == "duplicate-vector-id":
            vectors[1]["id"] = vectors[0]["id"]
        else:
            vectors[0]["target_symbol"] = "UnknownTarget"
        with pytest.raises(AssertionError):
            _assert_vector_structure(documents)
        return

    if mutation == "missing-export-coverage":
        documents = _copied_documents()
        cast(list[str], documents["manifest.json"]["target_symbols"]).remove(
            "BoundedLocator"
        )
        with pytest.raises(AssertionError):
            _assert_export_coverage(documents)
        return

    if mutation == "valid-wrong-expected-dump":
        vector = copy.deepcopy(
            _vector_by_id(VALID_DOCUMENT, "revision.valid.object.commit-base")
        )
        vector["expected"]["semantic_dump"]["full_digest"] = "f" * 40
        with pytest.raises(AssertionError):
            _execute_valid_vector(vector, VALID_DOCUMENT)
        return

    if mutation in {"invalid-changed-to-valid", "invalid-wrong-error-location"}:
        vector = copy.deepcopy(
            _vector_by_id(
                INVALID_DOCUMENT, "revision.invalid.object.commit-abbreviated"
            )
        )
        if mutation == "invalid-changed-to-valid":
            vector["input"]["full_digest"] = "4c9cde74ab40027b5761ab9e002af116a4a20df3"
        else:
            vector["expected"]["error_location"] = ["full_digest"]
        with pytest.raises(AssertionError):
            _assert_invalid_vector(vector, INVALID_DOCUMENT)
        return

    if mutation in {
        "replay-artifact-digest-changed",
        "replay-artifact-byte-length-changed",
    }:
        vector = copy.deepcopy(
            _vector_by_id(REPLAY_DOCUMENT, "revision.replay.artifact.parent-lock")
        )
        if mutation == "replay-artifact-digest-changed":
            vector["expected"]["sha256"] = "f" * 64
        else:
            vector["expected"]["byte_length"] = 1639
        with pytest.raises(AssertionError):
            _assert_replay_vector(vector, REPLAY_DOCUMENT)
        return

    if mutation in {
        "byte-offset-changed",
        "byte-length-changed",
        "selected-byte-digest-changed",
        "artifact-line-span-changed",
    }:
        vector = copy.deepcopy(
            _vector_by_id(REPLAY_DOCUMENT, "revision.replay.byte.changelog")
        )
        if mutation == "byte-offset-changed":
            vector["input"]["locator"]["span"]["offset"] += 1
        elif mutation == "byte-length-changed":
            vector["input"]["locator"]["span"]["length"] += 1
        elif mutation == "selected-byte-digest-changed":
            vector["input"]["selected_sha256"] = "f" * 64
        else:
            vector["input"]["artifact_lines"]["start_line"] += 1
        with pytest.raises(AssertionError):
            _assert_replay_vector(vector, REPLAY_DOCUMENT)
        return

    if mutation in {
        "hunk-header-changed",
        "old-new-span-changed",
        "evidence-classification-changed",
    }:
        vector = copy.deepcopy(
            _vector_by_id(REPLAY_DOCUMENT, "revision.replay.hunk.implementation")
        )
        if mutation == "hunk-header-changed":
            vector["input"]["expected_header"] += " mutated"
        elif mutation == "old-new-span-changed":
            vector["input"]["new_span"]["end_line"] += 1
        else:
            vector["evidence_classification"] = "exact_byte_locator_fact"
        with pytest.raises(AssertionError):
            _assert_replay_vector(vector, REPLAY_DOCUMENT)
        return

    if mutation == "source-pointer-swapped":
        vector = copy.deepcopy(
            _vector_by_id(REPLAY_DOCUMENT, "revision.replay.byte.changelog")
        )
        vector["source_pointer"]["json_pointer"] = "/locators/1"
        with pytest.raises(AssertionError):
            _assert_replay_vector(vector, REPLAY_DOCUMENT)
        return

    if mutation == "reviewed-line-range-changed":
        vector = copy.deepcopy(
            _vector_by_id(
                REPLAY_DOCUMENT, "revision.replay.reviewed-line.implementation"
            )
        )
        vector["input"]["reviewed_range"]["end_line"] += 1
        with pytest.raises(AssertionError):
            _assert_replay_vector(vector, REPLAY_DOCUMENT)
        return

    if mutation in {"line-semantics-zero-based", "byte-semantics-inclusive-end"}:
        documents = _copied_documents()
        conventions = documents["manifest.json"]["execution_contract"][
            "coordinate_conventions"
        ]
        if mutation == "line-semantics-zero-based":
            conventions["logical_lines"] = "zero_based_inclusive_nonempty"
        else:
            conventions["artifact_bytes"] = "zero_based_inclusive_end"
        with pytest.raises(AssertionError):
            _assert_manifest_integrity(documents)
        return

    if mutation in {
        "locator-discriminator-removed",
        "locator-discriminator-changed",
    }:
        vector = copy.deepcopy(
            _vector_by_id(VALID_DOCUMENT, "revision.valid.union.bounded-revision-line")
        )
        if mutation == "locator-discriminator-removed":
            del vector["input"]["locator_kind"]
        else:
            vector["input"]["locator_kind"] = "column"
        with pytest.raises(ValidationError):
            _execute_valid_vector(vector, VALID_DOCUMENT)
        return

    if mutation == "fixture-missing":
        with pytest.raises(AssertionError):
            _resolve_fixture_value(
                {"fixture_ref": "revision.fixture.valid.missing"},
                _fixture_map(VALID_DOCUMENT),
            )
        return

    if mutation == "fixture-cycle":
        document = {
            "fixtures": [
                {
                    "id": "revision.fixture.valid.cycle-a",
                    "status": "locked",
                    "value": {"fixture_ref": "revision.fixture.valid.cycle-b"},
                },
                {
                    "id": "revision.fixture.valid.cycle-b",
                    "status": "locked",
                    "value": {"fixture_ref": "revision.fixture.valid.cycle-a"},
                },
            ],
            "vectors": [],
        }
        with pytest.raises(AssertionError):
            _validate_fixture_graph(document)
        return

    if mutation in {"manifest-count-changed", "manifest-file-digest-changed"}:
        documents = _copied_documents()
        manifest = documents["manifest.json"]
        if mutation == "manifest-count-changed":
            manifest["vector_summary"]["valid"]["count"] += 1
        else:
            entry = next(
                item
                for item in manifest["corpus_files"]
                if item["filename"] == "valid-vectors.json"
            )
            entry["sha256"] = "f" * 64
        with pytest.raises(AssertionError):
            _assert_manifest_integrity(documents)
        return

    if mutation in {"extra-corpus-file", "mutable-latest-pointer"}:
        contract_root = tmp_path / "revision-locator"
        root = contract_root / "v1"
        shutil.copytree(CORPUS_ROOT, root)
        shutil.copytree(CLOSURE_ROOT.parent, contract_root / "closures")
        _assert_corpus_inventory(root)
        extra = (
            root / "unexpected.json"
            if mutation == "extra-corpus-file"
            else contract_root / "latest"
        )
        extra.write_bytes(b"{}\n")
        extra.chmod(0o644)
        with pytest.raises(AssertionError):
            _assert_corpus_inventory(root)
        return

    if mutation == "git-mode-100755":
        with pytest.raises(AssertionError):
            _assert_git_modes_100644({"synthetic": "100755"}, {"synthetic"})
        return

    if mutation in {"filesystem-mode-0755", "filesystem-mode-0600"}:
        path = tmp_path / "synthetic.json"
        path.write_bytes(b"{}\n")
        path.chmod(0o755 if mutation == "filesystem-mode-0755" else 0o600)
        with pytest.raises(AssertionError):
            _assert_fs_regular_0644(path)
        return

    if mutation == "corpus-symlink-or-special-file":
        target = tmp_path / "target"
        target.write_bytes(b"{}\n")
        link = tmp_path / "link"
        link.symlink_to(target)
        with pytest.raises(AssertionError):
            _assert_fs_regular_0644(link)
        fifo = tmp_path / "fifo"
        os.mkfifo(fifo, 0o644)
        with pytest.raises(AssertionError):
            _assert_fs_regular_0644(fifo)
        return

    if mutation in {"production-reader-inserted", "production-resolver-inserted"}:
        sources = _working_source_bytes()
        addition = (
            b"\ndef read_revision_locator_contract_corpus():\n    return None\n"
            if mutation == "production-reader-inserted"
            else b"\ndef resolve_bounded_locator():\n    return None\n"
        )
        sources["src/faultatlas/domain/revision.py"] += addition
        with pytest.raises(AssertionError):
            _assert_no_production_reader_or_resolver(sources)
        return

    if mutation == "package-root-export-inserted":
        with pytest.raises(AssertionError):
            _assert_package_root_exports(["__version__", "BoundedLocator"])
        return

    if mutation in {
        "synthetic-package-corpus-member",
        "historical-pytest-license-inserted",
    }:
        project_license = (REPOSITORY_ROOT / "LICENSE").read_bytes()
        historical_license = (
            REPOSITORY_ROOT / "reference_corpus/pytest-4412/acquisitions/"
            "run-0001-s04-v1-base-4c9cde74-head-690a63b9/artifacts/LICENSE"
        ).read_bytes()
        if mutation == "synthetic-package-corpus-member":
            name = f"{CORPUS_RELATIVE}/manifest.json"
            data = b"{}\n"
        else:
            name = "faultatlas-0.1.0/COPYING.pytest"
            data = historical_license
        members = _synthetic_package_members(extra_name=name, extra_data=data)
        with pytest.raises(AssertionError):
            _assert_safe_archive(
                members,
                project_license=project_license,
                historical_license=historical_license,
                tests_forbidden=True,
            )
        return

    assert mutation == "closure-artifact-inside-v1"
    contract_root = tmp_path / "revision-locator"
    root = contract_root / "v1"
    shutil.copytree(CORPUS_ROOT, root)
    shutil.copytree(CLOSURE_ROOT.parent, contract_root / "closures")
    _assert_corpus_inventory(root)
    misplaced = root / "closure.json"
    misplaced.write_bytes(b"{}\n")
    misplaced.chmod(0o644)
    with pytest.raises(AssertionError):
        _assert_corpus_inventory(root)


def test_actual_offline_build_excludes_corpus(tmp_path: Path) -> None:
    uv = shutil.which("uv")
    assert uv is not None
    project_license = (REPOSITORY_ROOT / "LICENSE").read_bytes()
    historical_license = (
        REPOSITORY_ROOT / "reference_corpus/pytest-4412/acquisitions/"
        "run-0001-s04-v1-base-4c9cde74-head-690a63b9/artifacts/LICENSE"
    ).read_bytes()
    assert _sha256(project_license) == (
        "c71d239df91726fc519c6eb72d318ec65820627232b2f796219e87dcf35d0ab4"
    )
    assert _sha256(historical_license) == (
        "a1ebce15afc7b5cf98c7c6de512d1959d4bf61db8c6bf2f111286d483b40a997"
    )
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
    files_before = _repository_snapshot()
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
    assert result.returncode == 0, (
        f"offline build failed\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )
    assert _git_status() == status_before
    assert _repository_snapshot() == files_before
    wheels = tuple(output.glob("*.whl"))
    sdists = tuple(output.glob("*.tar.gz"))
    assert len(wheels) == len(sdists) == 1
    _assert_safe_archive(
        _read_wheel(wheels[0]),
        project_license=project_license,
        historical_license=historical_license,
        tests_forbidden=True,
    )
    _assert_safe_archive(
        _read_sdist(sdists[0]),
        project_license=project_license,
        historical_license=historical_license,
        tests_forbidden=False,
    )
    assert faultatlas.__version__ == "0.1.0"
