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
from datetime import datetime, timedelta, timezone
from enum import StrEnum
from pathlib import Path, PurePosixPath
from typing import Any, NoReturn, cast

import pytest
from pydantic import BaseModel, TypeAdapter, ValidationError

import faultatlas
import faultatlas.domain as domain_package
import faultatlas.domain.evidence as evidence_module
from faultatlas.domain.compatibility import CompatibilityStatus
from faultatlas.domain.evidence import (
    AcquisitionRequestMembership,
    AcquisitionRun,
    AcquisitionRunId,
    AcquisitionRunStatus,
    ApiVersion,
    ArtifactByteLength,
    ArtifactDigest,
    ArtifactDigestAlgorithm,
    ArtifactDigestScope,
    ArtifactRetentionMode,
    ArtifactSha256Digest,
    ContentEncoding,
    DurableEvidenceRecordReference,
    EvidenceCanonicalization,
    EvidenceCompletenessAssessment,
    EvidenceCompletenessStatus,
    EvidenceCorrection,
    EvidenceDispositionReason,
    EvidenceEnvelope,
    EvidenceOmission,
    EvidencePublication,
    EvidencePublicationMethod,
    EvidenceRecordFormat,
    EvidenceRecordRelationship,
    EvidenceRelationId,
    EvidenceRequirementId,
    EvidenceRequirementOutcome,
    EvidenceRequirementResult,
    EvidenceScopeId,
    EvidenceSupersession,
    EvidenceTransformation,
    EvidenceVersion,
    ExactArtifactIdentity,
    ExactRetainedArtifact,
    HttpStatusCode,
    LegacyArtifactSnapshotEnvelopeMappingResult,
    LegacyArtifactSnapshotProjectionResult,
    LegacyEvidenceCompatibilityReason,
    MediaType,
    MediaTypeParameter,
    PublicationCheckEvent,
    PublicationCheckName,
    RequestQueryParameter,
    ResponseRepresentationObservation,
    ResponseRepresentationState,
    RetrievalMethod,
    RetrievalRequestControls,
    RetrievalRequestId,
    RetrievalRequestOrdinal,
    RetrievalRequestReference,
    RetrievalRoutePath,
    SuccessfulPublicationCheck,
    TransformationLossiness,
    TransformationOperation,
    TransformationReversibility,
    TransformationSubject,
    project_evidence_envelope_to_legacy_artifact_snapshot,
    wrap_legacy_artifact_snapshot,
)
from faultatlas.domain.identity import (
    AuthorityRole,
    NumberedSourceObjectIdentity,
    ProviderAuthority,
    ProviderGlobalId,
    ProviderKey,
    ProviderRepositoryId,
    RepositoryIdentity,
    RepositoryScopedNumber,
    SourceObjectKind,
)
from faultatlas.domain.revision import (
    GitCommitIdentity,
    GitHashAlgorithm,
    GitObjectKind,
    GitTreeIdentity,
)
from faultatlas.domain.source import ArtifactSnapshot, SourceLocator

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
CORPUS_RELATIVE = "reference_corpus/contracts/evidence-envelope/v1"
CORPUS_ROOT = REPOSITORY_ROOT / CORPUS_RELATIVE
ACQUISITION_RELATIVE = (
    "reference_corpus/pytest-4412/acquisitions/"
    "run-0001-s04-v1-base-4c9cde74-head-690a63b9/acquisition.json"
)
CORRECTION_RELATIVE = (
    "reference_corpus/pytest-4412/corrections/"
    "s04-c01-acquisition-closure/correction.json"
)
DIFF_RELATIVE = (
    "reference_corpus/pytest-4412/acquisitions/"
    "run-0001-s04-v1-base-4c9cde74-head-690a63b9/artifacts/base-to-head.diff"
)
LICENSE_RELATIVE = (
    "reference_corpus/pytest-4412/acquisitions/"
    "run-0001-s04-v1-base-4c9cde74-head-690a63b9/artifacts/LICENSE"
)
IDENTITY_CORPUS_RELATIVE = "reference_corpus/contracts/identity"
REVISION_CORPUS_RELATIVE = "reference_corpus/contracts/revision-locator"

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
        7374, "a391958867d047e783c652ae9bbae282fcf3c9148e621ecb21633f5d96c6f221"
    ),
    "invalid-vectors.json": LockedFile(
        141878, "a379f425e31e1a8627818fb2f4a8afb420975680048f0ecb14da6305022b3592"
    ),
    "invalid-vectors.sha256": LockedFile(
        87, "cfa302e3629fd78a3c839bd71f04872e6cc0516ffe7e5e8be4cc13ebee377c85"
    ),
    "manifest.json": LockedFile(
        20019, "1db40c259e40dc6eb5f6019f2355fba9ac6a272f16b45856c9fd75bd14baf97b"
    ),
    "manifest.sha256": LockedFile(
        80, "7b50090e3b4d09410deae96ed0cca92d2a5d0482117b6321b6e23291f9e85da4"
    ),
    "replay-vectors.json": LockedFile(
        75388, "dcf3a6133ff495bf9aec207fc3cf6bbdf9b26ec5ef1a13de83ecb8c8b85c0112"
    ),
    "replay-vectors.sha256": LockedFile(
        86, "04a37a1f7de55b49217f1cc366595873aedad9897f9007724cd3d016ff88d3e5"
    ),
    "valid-vectors.json": LockedFile(
        182770, "49a005d2ab8e321e0867c5346db187e4a7736a392fd8b7eb4d343ed100385b86"
    ),
    "valid-vectors.sha256": LockedFile(
        85, "1c21386cb1c1b861719a8d71e408963fcab413681f8ff3aa999bd638ea773379"
    ),
}

EXPECTED_FORMATS = {
    "manifest.json": "faultatlas-evidence-envelope-contract-corpus-manifest",
    "valid-vectors.json": "faultatlas-evidence-envelope-valid-contract-vectors",
    "invalid-vectors.json": "faultatlas-evidence-envelope-invalid-contract-vectors",
    "replay-vectors.json": "faultatlas-evidence-envelope-replay-contract-vectors",
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
        "semantic_boundaries",
        "source_decisions",
        "target_symbols",
        "vector_summary",
    },
    "valid-vectors.json": {"assurance", "fixtures", "format", "vectors"},
    "invalid-vectors.json": {"assurance", "fixtures", "format", "vectors"},
    "replay-vectors.json": {"assurance", "fixtures", "format", "vectors"},
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
    "EvidenceRecordFormat",
    "EvidenceVersion",
    "EvidenceCanonicalization",
    "DurableEvidenceRecordReference",
    "EvidenceRelationId",
    "TransformationOperation",
    "TransformationLossiness",
    "TransformationReversibility",
    "TransformationSubject",
    "EvidenceTransformation",
    "EvidenceCorrection",
    "EvidenceSupersession",
    "EvidenceRecordRelationship",
    "EvidenceScopeId",
    "EvidenceRequirementId",
    "EvidenceDispositionReason",
    "EvidenceRequirementOutcome",
    "EvidenceOmission",
    "EvidenceRequirementResult",
    "EvidenceCompletenessStatus",
    "EvidenceCompletenessAssessment",
    "EvidencePublicationMethod",
    "PublicationCheckEvent",
    "PublicationCheckName",
    "SuccessfulPublicationCheck",
    "EvidencePublication",
    "EvidenceEnvelope",
    "LegacyEvidenceCompatibilityReason",
    "LegacyArtifactSnapshotEnvelopeMappingResult",
    "LegacyArtifactSnapshotProjectionResult",
    "wrap_legacy_artifact_snapshot",
    "project_evidence_envelope_to_legacy_artifact_snapshot",
)
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
EXPECTED_PRODUCTION_LOCKS = {
    "src/faultatlas/domain/compatibility.py": LockedFile(
        18898, "f4ef93d432da4fd0ebf05237c164e10d8f18eceaf538ff4ddc3372565b5c46db"
    ),
    "src/faultatlas/domain/evidence.py": LockedFile(
        123689, "824ed6ad86d243ccf920f07fe66af5d6bf060d6d80fafb7d60588dec8244e7ba"
    ),
    "src/faultatlas/domain/identity.py": LockedFile(
        22684, "e2d604f4e86a3b94c2b1b1875fa6e8f408778cbadd829b3fe9e934dd53f2d169"
    ),
    "src/faultatlas/domain/revision.py": LockedFile(
        27342, "7bea28086b345f6c1b4eeebe9c483924e60521e2f3e78954b272ab3c42acacaa"
    ),
    "src/faultatlas/domain/source.py": LockedFile(
        4336, "034e53fd58212f0e34376bbc790fc3e74057031aaed4d7d89fb67904bdd380bf"
    ),
}
PREDECESSOR_LOCKS = {
    "reference_corpus/pytest-4412/closures/s1-p00-phase-closure/closure.json": (
        "8c02d79c4a5a1d52b9fc2a3718e1b47888da6195588e62ab927388dbe972189e"
    ),
    "reference_corpus/pytest-4412/closures/s1-p00-phase-closure/closure.sha256": (
        "5b5a189c173c7366d8fe39526d3eda20d6f61cdfd9095e7c22758ec3e710866a"
    ),
    "reference_corpus/pytest-4412/closures/s1-p00-phase-closure/closure.md": (
        "fdb39ed8a7194f0becb5b4e2536cd883e47e6f291791c26269c45e188e66f2b1"
    ),
    ACQUISITION_RELATIVE: (
        "1c29093bf1537e9b824a18df1848b71a8da014f544bc9f385707eb0e000a1318"
    ),
    CORRECTION_RELATIVE: (
        "44491ee512d2c2022110b83967fb6fa86d13045bc8404ea490d7a08b7aef24a2"
    ),
    "reference_corpus/contracts/identity/closures/s1-p01-phase-closure/closure.json": (
        "2c1bfb9d3d596711066796ef83999d49b6846e65315a301eead7fa8fb5ac4642"
    ),
    "reference_corpus/contracts/revision-locator/closures/"
    "s1-p02-phase-closure/closure.json": (
        "daf3a89ef22bf20652d91cc96f476f1f31584ec90d860e57d1641c3ec6ab5a67"
    ),
}
PREDECESSOR_BYTE_LENGTHS = {
    ACQUISITION_RELATIVE: 61283,
    CORRECTION_RELATIVE: 60832,
    DIFF_RELATIVE: 1640,
    LICENSE_RELATIVE: 1096,
}

EXPECTED_VALID_CATEGORIES = {
    "acquisition-run": 8,
    "completeness": 19,
    "durable-record": 13,
    "enum": 12,
    "envelope": 6,
    "exact-artifact": 14,
    "legacy-adapter": 3,
    "publication": 6,
    "relationship": 7,
    "request-controls": 12,
    "response-observation": 11,
    "retrieval-identity": 13,
    "transformation": 5,
}
EXPECTED_INVALID_CATEGORIES = {
    "bounds": 19,
    "completeness-publication": 19,
    "enum": 12,
    "envelope-adapter": 21,
    "identity-linkage": 9,
    "strictness": 43,
    "transformation-relationship": 12,
}
EXPECTED_REPLAY_CATEGORIES = {
    "canonical-artifact": 2,
    "canonical-completeness": 1,
    "canonical-correction": 1,
    "canonical-envelope": 2,
    "canonical-publication": 2,
    "canonical-run": 1,
    "legacy-adapter": 6,
}
EXPECTED_VALID_COUNT = 129
EXPECTED_INVALID_COUNT = 135
EXPECTED_REPLAY_COUNT = 15
EXPECTED_TOTAL_VECTORS = 279
EXPECTED_FIXTURE_COUNTS = {"invalid": 6, "replay": 2, "total": 20, "valid": 12}

VECTOR_ID_PATTERN = re.compile(
    r"^evidence\.(?:valid|invalid|replay)\.[a-z0-9-]+(?:\.[a-z0-9-]+)+$"
)
FIXTURE_ID_PATTERN = re.compile(
    r"^evidence\.fixture\.(?:valid|invalid|replay)\.[a-z0-9-]+(?:\.[a-z0-9-]+)*$"
)

MAX_MARKER_DEPTH = 48
MAX_REPEAT_COUNT = 8192

ENUM_TARGETS: dict[str, type[StrEnum]] = {
    "AcquisitionRunStatus": AcquisitionRunStatus,
    "ArtifactDigestAlgorithm": ArtifactDigestAlgorithm,
    "ArtifactRetentionMode": ArtifactRetentionMode,
    "EvidenceCompletenessStatus": EvidenceCompletenessStatus,
    "EvidencePublicationMethod": EvidencePublicationMethod,
    "EvidenceRequirementOutcome": EvidenceRequirementOutcome,
    "LegacyEvidenceCompatibilityReason": LegacyEvidenceCompatibilityReason,
    "PublicationCheckEvent": PublicationCheckEvent,
    "ResponseRepresentationState": ResponseRepresentationState,
    "RetrievalMethod": RetrievalMethod,
    "TransformationLossiness": TransformationLossiness,
    "TransformationReversibility": TransformationReversibility,
}
ROOT_MODEL_TARGETS: dict[str, type[BaseModel]] = {
    "AcquisitionRunId": AcquisitionRunId,
    "ApiVersion": ApiVersion,
    "ArtifactByteLength": ArtifactByteLength,
    "ArtifactDigestScope": ArtifactDigestScope,
    "ArtifactSha256Digest": ArtifactSha256Digest,
    "ContentEncoding": ContentEncoding,
    "EvidenceCanonicalization": EvidenceCanonicalization,
    "EvidenceDispositionReason": EvidenceDispositionReason,
    "EvidenceRecordFormat": EvidenceRecordFormat,
    "EvidenceRelationId": EvidenceRelationId,
    "EvidenceRequirementId": EvidenceRequirementId,
    "EvidenceScopeId": EvidenceScopeId,
    "EvidenceVersion": EvidenceVersion,
    "HttpStatusCode": HttpStatusCode,
    "MediaType": MediaType,
    "PublicationCheckName": PublicationCheckName,
    "RetrievalRequestOrdinal": RetrievalRequestOrdinal,
    "RetrievalRoutePath": RetrievalRoutePath,
    "TransformationOperation": TransformationOperation,
}
RECORD_MODEL_TARGETS: dict[str, type[BaseModel]] = {
    "AcquisitionRequestMembership": AcquisitionRequestMembership,
    "AcquisitionRun": AcquisitionRun,
    "ArtifactDigest": ArtifactDigest,
    "DurableEvidenceRecordReference": DurableEvidenceRecordReference,
    "EvidenceCompletenessAssessment": EvidenceCompletenessAssessment,
    "EvidenceCorrection": EvidenceCorrection,
    "EvidenceEnvelope": EvidenceEnvelope,
    "EvidenceOmission": EvidenceOmission,
    "EvidencePublication": EvidencePublication,
    "EvidenceRequirementResult": EvidenceRequirementResult,
    "EvidenceSupersession": EvidenceSupersession,
    "EvidenceTransformation": EvidenceTransformation,
    "ExactArtifactIdentity": ExactArtifactIdentity,
    "ExactRetainedArtifact": ExactRetainedArtifact,
    "LegacyArtifactSnapshotEnvelopeMappingResult": (
        LegacyArtifactSnapshotEnvelopeMappingResult
    ),
    "LegacyArtifactSnapshotProjectionResult": LegacyArtifactSnapshotProjectionResult,
    "MediaTypeParameter": MediaTypeParameter,
    "RequestQueryParameter": RequestQueryParameter,
    "ResponseRepresentationObservation": ResponseRepresentationObservation,
    "RetrievalRequestControls": RetrievalRequestControls,
    "RetrievalRequestId": RetrievalRequestId,
    "RetrievalRequestReference": RetrievalRequestReference,
    "SuccessfulPublicationCheck": SuccessfulPublicationCheck,
    "TransformationSubject": TransformationSubject,
}
MODEL_TARGETS: dict[str, type[BaseModel]] = {
    **ROOT_MODEL_TARGETS,
    **RECORD_MODEL_TARGETS,
}
UNION_TARGETS: dict[str, TypeAdapter[Any]] = {
    "EvidenceRecordRelationship": TypeAdapter(EvidenceRecordRelationship),
}
ADAPTER_TARGETS = (
    "wrap_legacy_artifact_snapshot",
    "project_evidence_envelope_to_legacy_artifact_snapshot",
)
SUPPORT_MODEL_TARGETS: dict[str, type[BaseModel]] = {
    "ArtifactSnapshot": ArtifactSnapshot,
    "GitCommitIdentity": GitCommitIdentity,
    "GitTreeIdentity": GitTreeIdentity,
    "NumberedSourceObjectIdentity": NumberedSourceObjectIdentity,
    "ProviderAuthority": ProviderAuthority,
    "ProviderGlobalId": ProviderGlobalId,
    "ProviderKey": ProviderKey,
    "ProviderRepositoryId": ProviderRepositoryId,
    "RepositoryIdentity": RepositoryIdentity,
    "RepositoryScopedNumber": RepositoryScopedNumber,
    "SourceLocator": SourceLocator,
}
SUPPORT_ENUM_TARGETS: dict[str, type[StrEnum]] = {
    "AuthorityRole": AuthorityRole,
    "CompatibilityStatus": CompatibilityStatus,
    "GitHashAlgorithm": GitHashAlgorithm,
    "GitObjectKind": GitObjectKind,
    "SourceObjectKind": SourceObjectKind,
}
KNOWN_OPERATIONS = {
    "adapter_project",
    "adapter_wrap",
    "compare",
    "construct",
    "enum_reject",
    "enum_values",
    "reject",
    "replay_artifact",
    "replay_envelope",
    "replay_record",
    "validate_union",
}
PYTHON_MARKER_KEYS = {
    "datetime_value",
    "enum_value",
    "tuple_value",
    "typed_value",
}
MATERIALIZED_MARKER_KEYS = {"float_value", "repeat_value"}
MARKER_KEYS = PYTHON_MARKER_KEYS | MATERIALIZED_MARKER_KEYS
ENVELOPE_COMPONENT_FIELDS = (
    "legacy_snapshots",
    "request_memberships",
    "acquisition_runs",
    "transformations",
    "record_relationships",
    "completeness_assessments",
    "publications",
)
MODERN_COMPONENT_FIELDS = tuple(
    field for field in ENVELOPE_COMPONENT_FIELDS if field != "legacy_snapshots"
)


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


def _json_text(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
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
    assert len(stack) <= MAX_MARKER_DEPTH
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


def _collect_fixture_references(value: Any, references: set[str]) -> None:
    if isinstance(value, dict):
        mapping = cast(dict[str, Any], value)
        if set(mapping) == {"fixture_ref"}:
            fixture_id = mapping["fixture_ref"]
            assert isinstance(fixture_id, str)
            references.add(fixture_id)
            return
        for item in mapping.values():
            _collect_fixture_references(item, references)
    elif isinstance(value, list):
        for item in cast(list[Any], value):
            _collect_fixture_references(item, references)


def _validate_fixture_graph(document: dict[str, Any]) -> None:
    fixtures = _fixture_map(document)
    for fixture_id, fixture in fixtures.items():
        _resolve_fixture_value(fixture["value"], fixtures, (fixture_id,))
    for vector in _vectors(document):
        _resolve_fixture_value(vector["input"], fixtures)
        _resolve_fixture_value(vector["expected"], fixtures)

    references: set[str] = set()
    for fixture in fixtures.values():
        _collect_fixture_references(fixture["value"], references)
    for vector in _vectors(document):
        _collect_fixture_references(vector["input"], references)
        _collect_fixture_references(vector["expected"], references)
    assert references == set(fixtures)


def _materialize(value: Any, depth: int = 0) -> Any:
    assert depth <= MAX_MARKER_DEPTH
    if isinstance(value, list):
        return [_materialize(item, depth + 1) for item in cast(list[Any], value)]
    if not isinstance(value, dict):
        return value
    mapping = cast(dict[str, Any], value)
    marker_keys = {key for key in mapping if key in MARKER_KEYS}
    if marker_keys:
        assert len(mapping) == 1
    if set(mapping) == {"repeat_value"}:
        descriptor = mapping["repeat_value"]
        assert isinstance(descriptor, dict)
        typed_descriptor = cast(dict[str, Any], descriptor)
        assert set(typed_descriptor) == {"count", "value"}
        count = typed_descriptor["count"]
        assert type(count) is int and 0 <= count <= MAX_REPEAT_COUNT
        item = _materialize(typed_descriptor["value"], depth + 1)
        return [copy.deepcopy(item) for _ in range(count)]
    if set(mapping) == {"float_value"}:
        raw_float = mapping["float_value"]
        assert isinstance(raw_float, str)
        result = float(raw_float)
        assert math.isfinite(result)
        return result
    return {key: _materialize(item, depth + 1) for key, item in mapping.items()}


def _assert_no_python_markers(value: Any) -> None:
    if isinstance(value, dict):
        mapping = cast(dict[str, Any], value)
        assert not (set(mapping) & PYTHON_MARKER_KEYS)
        for item in mapping.values():
            _assert_no_python_markers(item)
    elif isinstance(value, list):
        for item in cast(list[Any], value):
            _assert_no_python_markers(item)


def _decode_python_value(value: Any, depth: int = 0) -> Any:
    assert depth <= MAX_MARKER_DEPTH
    if isinstance(value, list):
        return [
            _decode_python_value(item, depth + 1) for item in cast(list[Any], value)
        ]
    if not isinstance(value, dict):
        return value
    mapping = cast(dict[str, Any], value)
    marker_keys = {key for key in mapping if key.endswith("_value")}
    if marker_keys:
        assert len(mapping) == 1
        assert marker_keys <= MARKER_KEYS
    if set(mapping) == {"typed_value"}:
        descriptor = mapping["typed_value"]
        assert isinstance(descriptor, dict)
        typed_descriptor = cast(dict[str, Any], descriptor)
        assert set(typed_descriptor) == {"input", "target"}
        target = typed_descriptor["target"]
        assert isinstance(target, str)
        registry = {**MODEL_TARGETS, **SUPPORT_MODEL_TARGETS}
        assert target in registry
        return registry[target].model_validate(
            _decode_python_value(typed_descriptor["input"], depth + 1)
        )
    if set(mapping) == {"enum_value"}:
        descriptor = mapping["enum_value"]
        assert isinstance(descriptor, dict)
        typed_descriptor = cast(dict[str, Any], descriptor)
        assert set(typed_descriptor) == {"target", "value"}
        target = typed_descriptor["target"]
        assert isinstance(target, str)
        registry_enum = {**ENUM_TARGETS, **SUPPORT_ENUM_TARGETS}
        assert target in registry_enum
        return registry_enum[target](typed_descriptor["value"])
    if set(mapping) == {"tuple_value"}:
        raw_items = mapping["tuple_value"]
        assert isinstance(raw_items, list)
        return tuple(
            _decode_python_value(item, depth + 1) for item in cast(list[Any], raw_items)
        )
    if set(mapping) == {"datetime_value"}:
        descriptor = mapping["datetime_value"]
        assert isinstance(descriptor, dict)
        typed_descriptor = cast(dict[str, Any], descriptor)
        assert set(typed_descriptor) == {"iso8601", "timezone_name"}
        raw_datetime = typed_descriptor["iso8601"]
        timezone_name = typed_descriptor["timezone_name"]
        assert isinstance(raw_datetime, str) and isinstance(timezone_name, str)
        parsed = datetime.fromisoformat(raw_datetime)
        assert parsed.utcoffset() == timedelta(0)
        return parsed.replace(tzinfo=timezone(timedelta(0), timezone_name))
    assert not marker_keys
    return {key: _decode_python_value(item, depth + 1) for key, item in mapping.items()}


def _resolved_input(vector: dict[str, Any], document: dict[str, Any]) -> Any:
    resolved = _resolve_fixture_value(vector["input"], _fixture_map(document))
    return _materialize(resolved)


def _resolved_expected(vector: dict[str, Any], document: dict[str, Any]) -> Any:
    resolved = _resolve_fixture_value(vector["expected"], _fixture_map(document))
    return cast(dict[str, Any], _materialize(resolved))


def _semantic_dump(value: BaseModel) -> Any:
    return value.model_dump(mode="json")


def _assert_operation_target(vector: dict[str, Any]) -> None:
    operation = vector["operation"]
    target = vector["target_symbol"]
    assert operation in KNOWN_OPERATIONS
    if operation in {"construct", "replay_record", "replay_envelope"}:
        assert target in MODEL_TARGETS
    elif operation == "reject":
        assert target in MODEL_TARGETS or target in UNION_TARGETS
    elif operation in {"validate_union", "compare"}:
        assert target in UNION_TARGETS
    elif operation in {"enum_values", "enum_reject"}:
        assert target in ENUM_TARGETS
    elif operation == "replay_artifact":
        assert target == "ExactArtifactIdentity"
    elif operation == "adapter_wrap":
        assert target == "wrap_legacy_artifact_snapshot"
    else:
        assert operation == "adapter_project"
        assert target == "project_evidence_envelope_to_legacy_artifact_snapshot"


def _validate_model(model: type[BaseModel], value: Any, input_mode: str) -> BaseModel:
    if input_mode == "json":
        _assert_no_python_markers(value)
        return model.model_validate_json(_json_text(value))
    assert input_mode == "python"
    return model.model_validate(_decode_python_value(value))


def _validate_union(adapter: TypeAdapter[Any], value: Any, input_mode: str) -> Any:
    if input_mode == "json":
        _assert_no_python_markers(value)
        return adapter.validate_json(_json_text(value))
    assert input_mode == "python"
    return adapter.validate_python(_decode_python_value(value))


def _round_trip_model(model: type[BaseModel], value: BaseModel) -> BaseModel:
    reconstructed = model.model_validate_json(value.model_dump_json())
    assert reconstructed == value
    assert _semantic_dump(reconstructed) == _semantic_dump(value)
    return reconstructed


def _round_trip_union(adapter: TypeAdapter[Any], value: Any) -> Any:
    reconstructed = adapter.validate_json(adapter.dump_json(value))
    assert reconstructed == value
    assert adapter.dump_python(reconstructed, mode="json") == adapter.dump_python(
        value, mode="json"
    )
    return reconstructed


def _assert_expected_dump(expected: dict[str, Any], actual: Any, resolved: Any) -> None:
    declared = expected["semantic_dump"]
    if isinstance(declared, dict) and set(cast(dict[str, Any], declared)) == {
        "equals_resolved_input"
    }:
        assert cast(dict[str, Any], declared)["equals_resolved_input"] is True
        assert actual == resolved
        return
    assert actual == declared


def _execute_valid_vector(vector: dict[str, Any], document: dict[str, Any]) -> None:
    _assert_operation_target(vector)
    expected = _resolved_expected(vector, document)
    assert expected["outcome"] == "accepted"
    value = _resolved_input(vector, document)
    operation = cast(str, vector["operation"])
    target = cast(str, vector["target_symbol"])
    input_mode = cast(str, vector["input_mode"])

    if operation == "enum_values":
        assert value == {"enum_target": target}
        assert expected["round_trip_equal"] is False
        assert expected["concrete_type"] == target
        assert expected["runtime_target"] == target
        assert [item.value for item in ENUM_TARGETS[target]] == expected[
            "semantic_dump"
        ]
        return

    if operation == "construct":
        result = _validate_model(MODEL_TARGETS[target], value, input_mode)
        actual: Any = _semantic_dump(result)
        reconstructed = _round_trip_model(MODEL_TARGETS[target], result)
        concrete_type = type(reconstructed).__name__
        _assert_expected_dump(expected, actual, value)
    elif operation == "validate_union":
        adapter = UNION_TARGETS[target]
        union_result = _validate_union(adapter, value, input_mode)
        actual = adapter.dump_python(union_result, mode="json")
        reconstructed_union = _round_trip_union(adapter, union_result)
        concrete_type = type(reconstructed_union).__name__
        _assert_expected_dump(expected, actual, value)
    else:
        assert operation == "compare"
        assert isinstance(value, dict)
        sides = cast(dict[str, Any], value)
        assert set(sides) == {"left", "right"}
        adapter = UNION_TARGETS[target]
        left = _validate_union(adapter, sides["left"], input_mode)
        right = _validate_union(adapter, sides["right"], input_mode)
        assert (left == right) is expected["comparison_equal"]
        _round_trip_union(adapter, left)
        _round_trip_union(adapter, right)
        actual = [
            adapter.dump_python(left, mode="json"),
            adapter.dump_python(right, mode="json"),
        ]
        concrete_type = type(left).__name__
        assert actual == expected["semantic_dump"]

    assert expected["round_trip_equal"] is True
    assert expected["runtime_target"] == target
    assert concrete_type == expected["concrete_type"]


def _invoke_invalid_vector(vector: dict[str, Any], document: dict[str, Any]) -> None:
    _assert_operation_target(vector)
    target = cast(str, vector["target_symbol"])
    value = _resolved_input(vector, document)
    if vector["operation"] == "enum_reject":
        ENUM_TARGETS[target](value)
        return
    assert vector["operation"] == "reject"
    input_mode = cast(str, vector["input_mode"])
    if target in UNION_TARGETS:
        _validate_union(UNION_TARGETS[target], value, input_mode)
    else:
        _validate_model(MODEL_TARGETS[target], value, input_mode)


def _assert_invalid_vector(vector: dict[str, Any], document: dict[str, Any]) -> None:
    expected = _resolved_expected(vector, document)
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
            f"got {[(item['loc'], item['type']) for item in error.errors()]!r}"
        )
        if "message_contains" in expected:
            assert any(expected["message_contains"] in item["msg"] for item in matches)
        return
    raise AssertionError(f"invalid vector unexpectedly succeeded: {vector['id']}")


def _assert_source_pointer(vector: dict[str, Any]) -> None:
    raw_pointer = vector["source_pointer"]
    assert isinstance(raw_pointer, dict)
    pointer = cast(dict[str, Any], raw_pointer)
    assert set(pointer) == {"authority", "path", "sha256"}
    authority = pointer["authority"]
    assert isinstance(authority, str) and authority
    path = pointer["path"]
    digest = pointer["sha256"]
    if path is None:
        assert digest is None
        assert vector["evidence_classification"] == "synthetic_contract_example"
        return
    assert isinstance(path, str) and isinstance(digest, str)
    pure = PurePosixPath(path)
    assert not pure.is_absolute()
    assert ".." not in pure.parts
    assert _sha256((REPOSITORY_ROOT / path).read_bytes()) == digest


def _replay_run_facts(run: AcquisitionRun) -> dict[str, Any]:
    retained = [
        membership
        for membership in run.requests
        if membership.retained_artifacts is not None and membership.retained_artifacts
    ]
    return {
        "known_empty_membership_count": len(
            [
                membership
                for membership in run.requests
                if membership.retained_artifacts == ()
            ]
        ),
        "request_count": run.request_count,
        "retained_artifact_ordinals": [
            membership.request_id.request_ordinal.root for membership in retained
        ],
        "retained_artifact_scopes": [
            artifact.artifact_identity.digest.scope.root
            for membership in retained
            for artifact in membership.retained_artifacts or ()
        ],
        "run_id": run.run_id.root,
        "sealed_at": run.sealed_at.isoformat().replace("+00:00", "Z"),
        "started_at": run.started_at.isoformat().replace("+00:00", "Z"),
        "status": run.status.value,
        "unrepresented_component_count": len(
            [
                component
                for membership in run.requests
                for component in (
                    membership.request_reference,
                    membership.request_controls,
                    membership.response_observation,
                )
                if component is None
            ]
        ),
    }


def _replay_correction_facts(correction: EvidenceCorrection) -> dict[str, Any]:
    return {
        "correction_byte_length": correction.correction_record.byte_length.root,
        "correction_sha256": correction.correction_record.sha256.root,
        "recorded_at": correction.recorded_at.isoformat().replace("+00:00", "Z"),
        "relationship_id": correction.relationship_id.root,
        "relationship_kind": correction.relationship_kind,
        "target_byte_length": correction.target_record.byte_length.root,
        "target_sha256": correction.target_record.sha256.root,
    }


def _replay_assessment_facts(
    assessment: EvidenceCompletenessAssessment,
) -> dict[str, Any]:
    reasons = {
        requirement.omission.reason.root
        for requirement in assessment.requirements
        if requirement.omission is not None
    }
    assert len(reasons) == 1
    return {
        "assessed_at": assessment.assessed_at.isoformat().replace("+00:00", "Z"),
        "assessment_id": assessment.assessment_id.root,
        "intentionally_omitted_requirements": [
            requirement.requirement_id.root
            for requirement in assessment.requirements
            if requirement.outcome is EvidenceRequirementOutcome.INTENTIONALLY_OMITTED
        ],
        "omission_reason": next(iter(reasons)),
        "requirement_count": len(assessment.requirements),
        "satisfied_requirements": [
            requirement.requirement_id.root
            for requirement in assessment.requirements
            if requirement.outcome is EvidenceRequirementOutcome.SATISFIED
        ],
        "scope_id": assessment.scope_id.root,
        "status": assessment.status.value,
        "universal_completeness_claimed": assessment.status
        is EvidenceCompletenessStatus.SCOPE_SATISFIED,
    }


def _replay_publication_facts(publication: EvidencePublication) -> dict[str, Any]:
    return {
        "main_check_event": publication.main_check.event.value,
        "publication_id": publication.publication_id.root,
        "published_revision": publication.published_revision.full_digest,
        "published_tree": publication.published_tree.full_digest,
        "pull_request_check_event": publication.pull_request_check.event.value,
        "pull_request_number": (
            publication.pull_request_identity.repository_scoped_number.root
        ),
        "repository_provider_id": (
            publication.repository_identity.provider_repository_id.root
        ),
        "reviewed_revision": publication.reviewed_revision.full_digest,
        "reviewed_tree": publication.reviewed_tree.full_digest,
        "reviewed_tree_equals_published_tree": (
            publication.reviewed_tree == publication.published_tree
        ),
        "subject_sha256": publication.subject_record.sha256.root,
    }


def _replay_record_facts(target: str, model: BaseModel) -> dict[str, Any]:
    if target == "AcquisitionRun":
        assert isinstance(model, AcquisitionRun)
        return _replay_run_facts(model)
    if target == "EvidenceCorrection":
        assert isinstance(model, EvidenceCorrection)
        return _replay_correction_facts(model)
    if target == "EvidenceCompletenessAssessment":
        assert isinstance(model, EvidenceCompletenessAssessment)
        return _replay_assessment_facts(model)
    assert target == "EvidencePublication"
    assert isinstance(model, EvidencePublication)
    return _replay_publication_facts(model)


def _envelope_inventory(envelope: EvidenceEnvelope) -> dict[str, int | None]:
    inventory: dict[str, int | None] = {}
    for field in ENVELOPE_COMPONENT_FIELDS:
        component = cast(tuple[object, ...] | None, getattr(envelope, field))
        inventory[field] = None if component is None else len(component)
    return inventory


def _envelope_facts(envelope: EvidenceEnvelope) -> dict[str, Any]:
    relationships = envelope.record_relationships or ()
    return {
        "canonical_correction_count": len(
            [item for item in relationships if isinstance(item, EvidenceCorrection)]
        ),
        "canonical_supersession_count": len(
            [item for item in relationships if isinstance(item, EvidenceSupersession)]
        ),
        "canonical_transformation_count": len(envelope.transformations or ()),
        "publication_order": [
            publication.publication_id.root
            for publication in envelope.publications or ()
        ],
        "run_ids": [run.run_id.root for run in envelope.acquisition_runs or ()],
    }


def _assert_replay_vector(vector: dict[str, Any], document: dict[str, Any]) -> None:
    _assert_operation_target(vector)
    assert vector["input_mode"] == "replay"
    assert vector["evidence_classification"] in {
        "immutable_source_fact",
        "reviewed_derived_composition",
        "synthetic_contract_example",
    }
    _assert_source_pointer(vector)
    value = _resolved_input(vector, document)
    assert isinstance(value, dict)
    replay_input = cast(dict[str, Any], value)
    expected = _resolved_expected(vector, document)
    assert expected["outcome"] == "accepted"
    operation = cast(str, vector["operation"])
    target = cast(str, vector["target_symbol"])

    if operation == "replay_artifact":
        assert set(replay_input) == {"artifact_identity", "artifact_path"}
        artifact_path = cast(str, replay_input["artifact_path"])
        assert artifact_path == vector["source_pointer"]["path"]
        raw = (REPOSITORY_ROOT / artifact_path).read_bytes()
        assert len(raw) == expected["byte_length"]
        assert _sha256(raw) == expected["sha256"]
        identity = ExactArtifactIdentity.model_validate_json(
            _json_text(replay_input["artifact_identity"])
        )
        assert identity.byte_length.root == len(raw)
        assert identity.digest.value.root == _sha256(raw)
        assert identity.digest.scope.root == expected["digest_scope"]
        assert identity.digest.algorithm.value == expected["digest_algorithm"]
        return

    if operation == "replay_record":
        assert set(replay_input) == {"record"}
        record = replay_input["record"]
        model = _validate_model(MODEL_TARGETS[target], record, "json")
        _round_trip_model(MODEL_TARGETS[target], model)
        _assert_expected_dump(expected, _semantic_dump(model), record)
        assert _replay_record_facts(target, model) == expected["facts"]
        assert expected["runtime_target"] == target
        return

    if operation == "replay_envelope":
        assert set(replay_input) == {"envelope"}
        payload = replay_input["envelope"]
        envelope = _validate_model(EvidenceEnvelope, payload, "json")
        assert isinstance(envelope, EvidenceEnvelope)
        _round_trip_model(EvidenceEnvelope, envelope)
        _assert_expected_dump(expected, _semantic_dump(envelope), payload)
        assert _envelope_inventory(envelope) == expected["component_inventory"]
        assert _envelope_facts(envelope) == expected["facts"]
        assert expected["runtime_target"] == target
        return

    if operation == "adapter_wrap":
        assert set(replay_input) == {"snapshot"}
        snapshot = ArtifactSnapshot.model_validate_json(
            _json_text(replay_input["snapshot"])
        )
        result = wrap_legacy_artifact_snapshot(snapshot)
        assert result.adapter_id.root == expected["adapter_id"]
        assert result.adapter_version.root == expected["adapter_version"]
        assert result.status.value == expected["status"]
        assert [reason.value for reason in result.reasons] == expected["reasons"]
        assert (result.source_snapshot == snapshot) is expected[
            "source_snapshot_preserved"
        ]
        assert result.envelope.legacy_snapshots == (snapshot,)
        assert (
            len(result.envelope.legacy_snapshots or ())
            == expected["envelope_legacy_snapshot_count"]
        )
        assert [
            field
            for field in MODERN_COMPONENT_FIELDS
            if getattr(result.envelope, field) is not None
        ] == expected["modern_components_represented"]
        return

    assert operation == "adapter_project"
    assert set(replay_input) == {"envelope"}
    source_envelope = _validate_model(
        EvidenceEnvelope, replay_input["envelope"], "json"
    )
    assert isinstance(source_envelope, EvidenceEnvelope)
    projection = project_evidence_envelope_to_legacy_artifact_snapshot(source_envelope)
    assert projection.adapter_id.root == expected["adapter_id"]
    assert projection.adapter_version.root == expected["adapter_version"]
    assert projection.status.value == expected["status"]
    assert [reason.value for reason in projection.reasons] == expected["reasons"]
    assert (projection.projected_snapshot is not None) is expected[
        "projected_snapshot_present"
    ]
    if expected["projected_snapshot_present"]:
        declared = ArtifactSnapshot.model_validate_json(
            _json_text(expected["projected_snapshot"])
        )
        assert projection.projected_snapshot == declared
        assert expected["projected_equals_expected_snapshot"] is True
    else:
        assert projection.projected_snapshot is None


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
    assert root.is_dir() and not root.is_symlink()
    assert {entry.name for entry in root.parent.iterdir()} == {"v1"}
    entries = tuple(root.iterdir())
    assert {entry.name for entry in entries} == EXPECTED_FILES
    for entry in entries:
        _assert_fs_regular_0644(entry)


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
    assert re.fullmatch(rb"[0-9a-f]{64}", raw[:64])


def _category_counts(document: dict[str, Any]) -> dict[str, int]:
    return dict(
        sorted(Counter(vector["category"] for vector in _vectors(document)).items())
    )


def _manifest_target_symbols(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    raw = manifest["target_symbols"]
    assert isinstance(raw, list)
    return cast(list[dict[str, Any]], raw)


def _assert_manifest_integrity(documents: dict[str, dict[str, Any]]) -> None:
    manifest = documents["manifest.json"]
    assert set(manifest) == EXPECTED_TOP_LEVEL["manifest.json"]
    assert manifest["format"]["name"] == EXPECTED_FORMATS["manifest.json"]
    assert manifest["format"]["version"] == "1"
    assert manifest["format"]["audience"] == "internal"
    assert manifest["format"]["public_contract"] is False
    assert manifest["format"]["no_production_persistence"] is True
    assert manifest["format"]["independent_versioning"] is True
    assert manifest["format"]["corpus_json_canonicalization"] == (
        "json-sort-keys-compact-utf8-lf-v1"
    )
    assert manifest["corpus_identity"] == {
        "classification": [
            "internal",
            "case-calibrated",
            "source-repository-only",
            "non-public",
            "non-production-persistence",
            "independently-versioned",
        ],
        "id": "faultatlas-evidence-envelope-contract-corpus",
        "originating_slice": "S1.P03.S08",
        "phase_closure_owner": "S1.P03.S09",
        "serialization_and_migration_owner": "S1.P10",
        "version": "1",
    }
    assert manifest["scope"]["phase"] == "S1.P03"
    assert manifest["scope"]["slice"] == "S1.P03.S08"
    assert manifest["scope"]["source_only"] is True
    assert manifest["scope"]["production_module"] == "faultatlas.domain.evidence"
    assert manifest["scope"]["covered_slices"] == [
        f"S1.P03.S0{index}" for index in range(1, 8)
    ]
    assert manifest["scope"]["supporting_authorities_not_owned"] == [
        "faultatlas.domain.compatibility",
        "faultatlas.domain.identity",
        "faultatlas.domain.revision",
        "faultatlas.domain.source",
    ]

    summary = cast(dict[str, Any], manifest["vector_summary"])
    assert summary == {
        "fixtures": EXPECTED_FIXTURE_COUNTS,
        "invalid": {
            "categories": EXPECTED_INVALID_CATEGORIES,
            "count": EXPECTED_INVALID_COUNT,
        },
        "replay": {
            "categories": EXPECTED_REPLAY_CATEGORIES,
            "count": EXPECTED_REPLAY_COUNT,
        },
        "total_vectors": EXPECTED_TOTAL_VECTORS,
        "valid": {
            "categories": EXPECTED_VALID_CATEGORIES,
            "count": EXPECTED_VALID_COUNT,
        },
    }
    assert _category_counts(documents["valid-vectors.json"]) == (
        EXPECTED_VALID_CATEGORIES
    )
    assert _category_counts(documents["invalid-vectors.json"]) == (
        EXPECTED_INVALID_CATEGORIES
    )
    assert _category_counts(documents["replay-vectors.json"]) == (
        EXPECTED_REPLAY_CATEGORIES
    )
    assert {
        name: len(_fixture_map(documents[f"{name}-vectors.json"]))
        for name in ("valid", "invalid", "replay")
    } == {
        name: EXPECTED_FIXTURE_COUNTS[name] for name in ("valid", "invalid", "replay")
    }

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
        if filename in {"manifest.json", "manifest.sha256", "contract.md"}:
            assert item["digest_lock"] == "independent_tracked_test_oracle"
            assert "sha256" not in item
        else:
            assert item["byte_length"] == EXPECTED_LOCKS[filename].byte_length
            assert item["sha256"] == EXPECTED_LOCKS[filename].sha256
    assert "manifest_sha256" not in manifest
    assert manifest["assurance"]["manifest_self_digest"] is False
    assert manifest["assurance"]["durable_envelope_bytes_claimed"] is False
    assert manifest["assurance"]["production_reader_writer_or_validator"] is False
    assert manifest["assurance"]["executor"] == "test_only_explicit_registry"
    assert manifest["assurance"]["package_exclusion"] == (
        "required_wheel_sdist_and_installed_resources"
    )
    assert manifest["assurance"]["corpus_canonicalization"] == (
        "json-sort-keys-compact-utf8-lf-v1"
    )

    execution = cast(dict[str, Any], manifest["execution_contract"])
    assert execution["registry"] == {
        "adapter_function_targets": len(ADAPTER_TARGETS),
        "enum_targets": len(ENUM_TARGETS),
        "record_model_targets": len(RECORD_MODEL_TARGETS),
        "root_model_targets": len(ROOT_MODEL_TARGETS),
        "support_enum_targets": len(SUPPORT_ENUM_TARGETS),
        "support_model_targets": len(SUPPORT_MODEL_TARGETS),
        "union_adapter_targets": len(UNION_TARGETS),
        "unknown_marker": "reject",
        "unknown_operation": "reject",
        "unknown_support_type": "reject",
        "unknown_target": "reject",
    }
    assert execution["fixture_references"] == "file_local_acyclic_explicit_only"
    assert execution["input_modes"] == ["json", "python", "replay"]
    markers = cast(dict[str, Any], execution["test_input_markers"])
    assert markers["allowed"] == sorted(MARKER_KEYS)
    assert markers["malformed_or_unknown"] == "reject"
    assert markers["max_recursive_depth"] == MAX_MARKER_DEPTH
    assert markers["max_repeat_count"] == MAX_REPEAT_COUNT
    assert markers["support_model_allowlist"] == sorted(SUPPORT_MODEL_TARGETS)
    assert markers["support_enum_allowlist"] == sorted(SUPPORT_ENUM_TARGETS)
    assert execution["unsafe_mechanisms_forbidden"] == [
        "arbitrary_attribute_traversal",
        "dynamic_import",
        "eval",
        "exec",
        "network_access",
        "plugin_loading",
        "production_file_readers",
    ]
    assert execution["expectation_contract"]["production_dump_used_as_oracle"] is False
    assert execution["expectation_contract"]["independently_authored"] is True

    replay_contract = cast(dict[str, Any], manifest["replay_contract"])
    assert replay_contract["production_replay_io"] is False
    assert replay_contract["production_lookup"] == "none"
    assert replay_contract["canonical_envelope"] == {
        "acquisition_runs": 1,
        "completeness_assessments": 1,
        "legacy_snapshots": None,
        "publications": 2,
        "record_relationships": 1,
        "request_memberships": None,
        "supersessions": 0,
        "transformations": 0,
    }
    assert replay_contract["canonical_legacy_projection"] == {
        "projected_snapshot": None,
        "reason": "legacy_snapshot_absent",
        "status": "not_mappable",
    }
    for artifact in cast(list[dict[str, Any]], replay_contract["artifacts"]):
        raw = (REPOSITORY_ROOT / cast(str, artifact["path"])).read_bytes()
        assert len(raw) == artifact["byte_length"]
        assert _sha256(raw) == artifact["sha256"]

    for source in cast(list[dict[str, Any]], manifest["source_decisions"]):
        assert set(source) == {"authority_ids", "path", "sha256"}
        raw = (REPOSITORY_ROOT / cast(str, source["path"])).read_bytes()
        assert _sha256(raw) == source["sha256"]
        decoded = raw.decode("utf-8")
        for authority_id in cast(list[str], source["authority_ids"]):
            assert authority_id in decoded

    boundaries = cast(dict[str, Any], manifest["semantic_boundaries"])
    assert set(boundaries) == {
        "corpus_canonical_json_bytes",
        "future_durable_production_record_bytes",
        "python_model_equality",
        "retained_exact_artifact_bytes",
        "semantic_json_representation",
    }
    assert boundaries["future_durable_production_record_bytes"] == "owned_by_S1.P10"


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
            assert vector["target_symbol"] in EXPECTED_EVIDENCE_EXPORTS
            assert vector["input_mode"] in {"json", "python", "replay"}
            _assert_operation_target(vector)
            if vector["input_mode"] == "json":
                _assert_no_python_markers(vector["input"])
    assert len(seen) == EXPECTED_TOTAL_VECTORS


def _assert_export_coverage(documents: dict[str, dict[str, Any]]) -> None:
    assert tuple(evidence_module.__all__) == EXPECTED_EVIDENCE_EXPORTS
    assert len(evidence_module.__all__) == 58
    registry_symbols = (
        set(ENUM_TARGETS)
        | set(MODEL_TARGETS)
        | set(UNION_TARGETS)
        | set(ADAPTER_TARGETS)
    )
    assert registry_symbols == set(EXPECTED_EVIDENCE_EXPORTS)
    assert registry_symbols.isdisjoint(SUPPORT_MODEL_TARGETS)
    assert registry_symbols.isdisjoint(SUPPORT_ENUM_TARGETS)

    manifest_targets = _manifest_target_symbols(documents["manifest.json"])
    assert [item["symbol"] for item in manifest_targets] == list(
        EXPECTED_EVIDENCE_EXPORTS
    )
    class_by_symbol = {
        **{name: "enum_target" for name in ENUM_TARGETS},
        **{name: "root_model_target" for name in ROOT_MODEL_TARGETS},
        **{name: "record_model_target" for name in RECORD_MODEL_TARGETS},
        **{name: "union_adapter_target" for name in UNION_TARGETS},
        **{name: "adapter_function_target" for name in ADAPTER_TARGETS},
    }
    for item in manifest_targets:
        assert set(item) == {"coverage", "slice_layer", "symbol", "target_class"}
        assert item["coverage"] == "direct_executable_vector_target"
        assert item["target_class"] == class_by_symbol[cast(str, item["symbol"])]
        assert re.fullmatch(r"S1\.P03\.S0[1-7]", cast(str, item["slice_layer"]))

    covered = {
        cast(str, vector["target_symbol"])
        for filename in (
            "valid-vectors.json",
            "invalid-vectors.json",
            "replay-vectors.json",
        )
        for vector in _vectors(documents[filename])
    }
    assert covered == set(EXPECTED_EVIDENCE_EXPORTS)


def _assert_package_root_exports(exports: list[str]) -> None:
    assert exports == ["__version__"]


def _assert_no_production_corpus_capability(
    sources: dict[str, bytes] | None = None,
) -> None:
    if sources is None:
        sources = {
            path.relative_to(REPOSITORY_ROOT).as_posix(): path.read_bytes()
            for path in (REPOSITORY_ROOT / "src").rglob("*.py")
        }
    assert set(sources) == EXPECTED_PRODUCTION_FILES
    for relative, raw in sources.items():
        assert CORPUS_RELATIVE.encode() not in raw
        assert b"reference_corpus" not in raw
        tree = ast.parse(raw, filename=relative)
        definitions = {
            node.name
            for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
        }
        for name in definitions:
            lowered = name.casefold()
            assert "corpus" not in lowered
            assert not (
                "evidence" in lowered
                and any(
                    verb in lowered
                    for verb in ("load", "read", "reader", "writer", "write", "persist")
                )
            )
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                assert node.func.id not in {"open", "eval", "exec", "__import__"}
            if isinstance(node, ast.Attribute):
                assert node.attr not in {
                    "read_bytes",
                    "read_text",
                    "write_bytes",
                    "write_text",
                }
    assert not hasattr(evidence_module, "EvidenceEnvelopeReader")
    assert not hasattr(evidence_module, "EvidenceEnvelopeWriter")
    assert not hasattr(evidence_module, "EvidenceContractCorpus")
    _assert_package_root_exports(faultatlas.__all__)
    assert getattr(domain_package, "__all__", None) in (None, [])


def _assert_semantic_boundaries(documents: dict[str, dict[str, Any]]) -> None:
    manifest = documents["manifest.json"]
    non_goals = set(cast(list[str], manifest["non_goals"]))
    assert {
        "S1.P03.S09_integration_and_phase_closure",
        "S1.P04_and_later_implementation",
        "canonical_EvidenceEnvelope_bytes",
        "confidence_or_review_semantics",
        "database",
        "development_history_aggregation",
        "evidence_persistence",
        "fault_instance_model",
        "migration",
        "network_access",
        "pattern_extraction",
        "production_corpus_reader",
        "production_corpus_validator",
        "production_corpus_writer",
        "provider_SDK",
        "public_API",
        "public_JSON_Schema",
        "repository_snapshot_model",
        "schema_registry",
        "serializer_registry",
        "storage_backend",
        "transfer_or_applicability_semantics",
    } == non_goals
    for field in (
        "envelope_canonicalization",
        "envelope_sha256",
        "durable_byte_length",
    ):
        assert field not in EvidenceEnvelope.model_fields
    for field in ("envelope_id", "canonicalization", "sha256", "byte_length"):
        assert field not in EvidenceEnvelope.model_fields
    combined = "".join(
        _json_text(documents[name]) for name in sorted(EXPECTED_TOP_LEVEL)
    )
    for forbidden in (
        '"durable_envelope_bytes"',
        '"envelope_canonicalization"',
        '"envelope_sha256"',
        '"production_serializer"',
        '"production_wire_format"',
    ):
        assert forbidden not in combined


def _assert_privacy_bytes(raw: bytes) -> None:
    lowered = raw.lower()
    for forbidden in (
        b"/home/",
        b"/root/",
        b"/users/",
        b"authorization:",
        b'"authorization"',
        b"bearer ",
        b"begin openssh private key",
        b"begin private key",
        b"client_secret",
        b"ghp_",
        b"github_pat_",
        b"secret_key",
        b"x-access-token",
        b"x-api-key",
    ):
        assert forbidden not in lowered
    text = raw.decode("utf-8")
    assert re.search(r"(?i)(?:^|[^a-z0-9])[a-z]:[\\/]", text) is None
    assert re.search(r"(?i)(?:^|[^a-z0-9])/tmp(?:[\\/])", text) is None
    assert re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text) is None


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
        assert "evidence-envelope" not in lowered
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


def _corpus_vector_count(relative: str) -> int:
    root = REPOSITORY_ROOT / relative
    total = 0
    for path in sorted(root.rglob("*.json")):
        if path.name in {"manifest.json", "closure.json", "correction.json"}:
            continue
        document = _parse_canonical_json(path.read_bytes())
        raw = document.get("vectors")
        if isinstance(raw, list):
            total += len(cast(list[Any], raw))
    return total


VALID_DOCUMENT = _load_document("valid-vectors.json")
INVALID_DOCUMENT = _load_document("invalid-vectors.json")
REPLAY_DOCUMENT = _load_document("replay-vectors.json")


@pytest.mark.parametrize("filename", sorted(EXPECTED_FILES))
def test_independent_digest_oracle(filename: str) -> None:
    _assert_locked_file(filename, (CORPUS_ROOT / filename).read_bytes())


@pytest.mark.parametrize("filename", sorted(JSON_FILES))
def test_canonical_json(filename: str) -> None:
    document = _load_document(filename)
    assert set(document) == EXPECTED_TOP_LEVEL[filename]
    assert document["format"]["name"] == EXPECTED_FORMATS[filename]
    assert document["format"]["version"] == "1"


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
    expected_paths = {f"{CORPUS_RELATIVE}/{name}" for name in EXPECTED_FILES}
    actual_modes = _git_stage_modes(expected_paths)
    untracked = expected_paths - set(actual_modes)
    _assert_git_modes_100644(actual_modes, expected_paths - untracked)
    if untracked:
        prospective = _prospective_modes(untracked, tmp_path)
        _assert_git_modes_100644(prospective, untracked)


def test_manifest_vector_and_fixture_integrity() -> None:
    documents = _documents()
    _assert_manifest_integrity(documents)
    _assert_vector_structure(documents)


@pytest.mark.parametrize(
    "vector",
    _vectors(VALID_DOCUMENT),
    ids=lambda vector: cast(dict[str, Any], vector)["id"],
)
def test_valid_vector_execution(vector: dict[str, Any]) -> None:
    _execute_valid_vector(vector, VALID_DOCUMENT)


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


def test_registry_fixture_and_marker_safety() -> None:
    with pytest.raises(AssertionError):
        _assert_operation_target(
            {"operation": "construct", "target_symbol": "UnknownTarget"}
        )
    with pytest.raises(AssertionError):
        _assert_operation_target(
            {"operation": "unknown_operation", "target_symbol": "AcquisitionRun"}
        )
    with pytest.raises(AssertionError):
        _assert_operation_target(
            {"operation": "adapter_wrap", "target_symbol": "EvidenceEnvelope"}
        )
    with pytest.raises(ValueError):
        AcquisitionRunStatus("running")

    for mutated in (
        {"fixture_ref": "evidence.fixture.valid.missing"},
        {"fixture_pointer": "/fixtures/0"},
        {"fixture_link": "evidence.fixture.valid.record.acquisition"},
        {"fixture_ref": "../valid-vectors.json"},
    ):
        with pytest.raises(AssertionError):
            _resolve_fixture_value(mutated, _fixture_map(VALID_DOCUMENT))

    duplicate = {
        "fixtures": [
            {"id": "evidence.fixture.valid.duplicate", "status": "locked", "value": 1},
            {"id": "evidence.fixture.valid.duplicate", "status": "locked", "value": 2},
        ],
        "vectors": [],
    }
    with pytest.raises(AssertionError):
        _fixture_map(duplicate)

    cycle = {
        "fixtures": [
            {
                "id": "evidence.fixture.valid.cycle-a",
                "status": "locked",
                "value": {"fixture_ref": "evidence.fixture.valid.cycle-b"},
            },
            {
                "id": "evidence.fixture.valid.cycle-b",
                "status": "locked",
                "value": {"fixture_ref": "evidence.fixture.valid.cycle-a"},
            },
        ],
        "vectors": [],
    }
    with pytest.raises(AssertionError):
        _validate_fixture_graph(cycle)

    malformed_markers: tuple[dict[str, Any], ...] = (
        {"unknown_value": "unsafe"},
        {"typed_value": {"input": {}, "target": "EvidenceEnvelopeReader"}},
        {"enum_value": {"target": "UnknownEnum", "value": "x"}},
        {"typed_value": {"input": {}, "target": "AcquisitionRun"}, "extra": True},
    )
    for malformed in malformed_markers:
        with pytest.raises(AssertionError):
            _decode_python_value(malformed)
    with pytest.raises(AssertionError):
        _materialize({"repeat_value": {"count": MAX_REPEAT_COUNT + 1, "value": {}}})
    with pytest.raises(AssertionError):
        _assert_no_python_markers({"typed_value": {"input": 1, "target": "MediaType"}})

    source = Path(__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    forbidden_calls = {"eval", "exec", "__import__", "import_module", "load_module"}
    calls = {
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    assert not (calls & forbidden_calls)
    assert not (
        calls
        & {"setattr", "delattr", "vars", "globals", "locals", "compile", "__import__"}
    )
    attribute_calls = {
        node.func.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    }
    assert not (attribute_calls & {"import_module", "load_module", "find_module"})
    imported = {
        alias.name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    } | {
        (node.module or "").split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
    }
    assert not (imported & {"importlib", "pkgutil", "runpy", "socket", "urllib"})
    getattr_calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "getattr"
    ]
    assert getattr_calls
    for node in getattr_calls:
        assert len(node.args) >= 2
        assert isinstance(node.args[1], (ast.Constant, ast.Name))


def test_export_coverage_and_semantic_boundaries() -> None:
    documents = _documents()
    _assert_export_coverage(documents)
    _assert_semantic_boundaries(documents)
    _assert_no_production_corpus_capability()
    raw = b"\n".join(
        (CORPUS_ROOT / name).read_bytes() for name in sorted(EXPECTED_FILES)
    )
    _assert_privacy_bytes(raw)


def test_predecessor_locks_remain_exact() -> None:
    for relative, digest in PREDECESSOR_LOCKS.items():
        assert _sha256((REPOSITORY_ROOT / relative).read_bytes()) == digest
    for relative, byte_length in PREDECESSOR_BYTE_LENGTHS.items():
        assert len((REPOSITORY_ROOT / relative).read_bytes()) == byte_length
    assert _corpus_vector_count(IDENTITY_CORPUS_RELATIVE) == 200
    assert _corpus_vector_count(REVISION_CORPUS_RELATIVE) == 228
    identity_test = (
        REPOSITORY_ROOT / "tests/test_identity_contract_corpus.py"
    ).read_text(encoding="utf-8")
    assert "EXPECTED_EFFECTIVE_VECTOR_COUNT = 199" in identity_test


def test_production_surface_is_unchanged() -> None:
    sources = _working_source_bytes()
    for relative, lock in EXPECTED_PRODUCTION_LOCKS.items():
        assert len(sources[relative]) == lock.byte_length
        assert _sha256(sources[relative]) == lock.sha256
    assert faultatlas.__version__ == "0.1.0"
    _assert_package_root_exports(faultatlas.__all__)
    assert tuple(ArtifactSnapshot.model_fields) == (
        "schema_version",
        "source",
        "retrieved_at",
        "media_type",
        "payload_text",
        "digest_algorithm",
        "digest",
        "truncated",
        "redacted",
        "missing_context",
    )
    assert tuple(EvidenceEnvelope.model_fields) == (
        "schema_version",
        *ENVELOPE_COMPONENT_FIELDS,
    )


def test_roadmap_records_s08_complete_and_s09_next() -> None:
    roadmap = (REPOSITORY_ROOT / "docs/roadmap.md").read_text(encoding="utf-8")
    assert "`S1.P03.S08` — Evidence Contract Corpus (complete)" in roadmap
    assert "`S1.P03.S09` is next and not started" in roadmap
    assert "`S1.P03` is active" in roadmap
    assert "`S1.P04` through `S1.P10` remain not started" in roadmap
    assert "**S2-S9** are not implemented." in roadmap
    reference_case = (
        REPOSITORY_ROOT / "docs/reference_cases/pytest-4412.md"
    ).read_text(encoding="utf-8")
    assert "reference_corpus/contracts/evidence-envelope/v1" in reference_case


def test_markdown_is_synchronized_and_non_authoritative() -> None:
    markdown = (CORPUS_ROOT / "contract.md").read_text(encoding="utf-8")
    assert "Internal, non-public" in markdown
    assert EXPECTED_LOCKS["manifest.json"].sha256 in markdown
    assert (
        "Derived, non-authoritative Markdown; the canonical JSON files remain "
        "the sole contract authority."
    ) in markdown
    for symbol in evidence_module.__all__:
        assert f"`{symbol}`" in markdown
    for category, count in EXPECTED_VALID_CATEGORIES.items():
        assert f'"{category}": {count}' in markdown
    for category, count in EXPECTED_INVALID_CATEGORIES.items():
        assert f'"{category}": {count}' in markdown
    for category, count in EXPECTED_REPLAY_CATEGORIES.items():
        assert f'"{category}": {count}' in markdown
    assert "adds no production reader, writer, or validator" in markdown
    assert "wheel, sdist, and installed resources" in markdown
    assert "not a durable `EvidenceEnvelope` byte contract" in markdown
    assert "`S1.P03.S09`" in markdown
    assert "`S1.P10`" in markdown


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
    "valid-equals-input-broken",
    "invalid-changed-to-valid",
    "invalid-wrong-error-location",
    "replay-artifact-digest-changed",
    "replay-artifact-byte-length-changed",
    "replay-run-request-count-changed",
    "replay-correction-digest-changed",
    "replay-assessment-requirement-count-changed",
    "replay-publication-tree-changed",
    "replay-envelope-inventory-changed",
    "replay-envelope-known-empty-to-unknown",
    "replay-adapter-status-changed",
    "replay-adapter-reason-changed",
    "replay-source-pointer-digest-changed",
    "fixture-missing",
    "fixture-cycle",
    "manifest-count-changed",
    "manifest-file-digest-changed",
    "manifest-target-class-changed",
    "extra-corpus-file",
    "mutable-latest-pointer",
    "git-mode-100755",
    "filesystem-mode-0755",
    "corpus-symlink-or-special-file",
    "production-corpus-reader-inserted",
    "production-io-inserted",
    "package-root-export-inserted",
    "synthetic-package-corpus-member",
    "historical-pytest-license-inserted",
)
assert len(REQUIRED_MUTATIONS) == 43


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
                "faultatlas-0.1.0.dist-info/licenses/LICENSE", "file", project_license
            ),
            ArchiveMember(extra_name, "file", extra_data),
        ]
    )
    return tuple(members)


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
        cast(dict[str, Any], document["assurance"])["status"] = "coherently_resealed"
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
            cast(dict[str, Any], document["assurance"])["forbidden_float"] = 1.5
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

    if mutation in {"missing-export-coverage", "manifest-target-class-changed"}:
        documents = _copied_documents()
        targets = _manifest_target_symbols(documents["manifest.json"])
        if mutation == "missing-export-coverage":
            del targets[-1]
        else:
            targets[0]["target_class"] = "adapter_function_target"
        with pytest.raises(AssertionError):
            _assert_export_coverage(documents)
        return

    if mutation in {"valid-wrong-expected-dump", "valid-equals-input-broken"}:
        vector = copy.deepcopy(
            _vector_by_id(
                VALID_DOCUMENT, "evidence.valid.exact-artifact.digest-compare-diff"
            )
        )
        if mutation == "valid-wrong-expected-dump":
            vector["expected"]["semantic_dump"] = {"equals_resolved_input": False}
        else:
            vector["input"]["scope"] = "github-compare-diff-http-entity-body-changed"
            vector["expected"]["semantic_dump"] = {
                "schema_version": 1,
                "algorithm": "sha256",
                "scope": "github-compare-diff-http-entity-body",
                "value": vector["input"]["value"],
            }
        with pytest.raises(AssertionError):
            _execute_valid_vector(vector, VALID_DOCUMENT)
        return

    if mutation in {"invalid-changed-to-valid", "invalid-wrong-error-location"}:
        vector = copy.deepcopy(
            _vector_by_id(INVALID_DOCUMENT, "evidence.invalid.strictness.ordinal-zero")
        )
        if mutation == "invalid-changed-to-valid":
            vector["input"] = 1
        else:
            vector["expected"]["error_location"] = ["root"]
        with pytest.raises(AssertionError):
            _assert_invalid_vector(vector, INVALID_DOCUMENT)
        return

    if mutation in {
        "replay-artifact-digest-changed",
        "replay-artifact-byte-length-changed",
    }:
        vector = copy.deepcopy(
            _vector_by_id(REPLAY_DOCUMENT, "evidence.replay.artifact.compare-diff")
        )
        if mutation == "replay-artifact-digest-changed":
            vector["expected"]["sha256"] = "f" * 64
        else:
            vector["expected"]["byte_length"] = 1639
        with pytest.raises(AssertionError):
            _assert_replay_vector(vector, REPLAY_DOCUMENT)
        return

    if mutation == "replay-run-request-count-changed":
        vector = copy.deepcopy(
            _vector_by_id(REPLAY_DOCUMENT, "evidence.replay.run.canonical-32-request")
        )
        vector["expected"]["facts"]["request_count"] = 31
        with pytest.raises(AssertionError):
            _assert_replay_vector(vector, REPLAY_DOCUMENT)
        return

    if mutation == "replay-correction-digest-changed":
        vector = copy.deepcopy(
            _vector_by_id(
                REPLAY_DOCUMENT, "evidence.replay.relationship.s04-c01-correction"
            )
        )
        vector["expected"]["facts"]["correction_sha256"] = "f" * 64
        with pytest.raises(AssertionError):
            _assert_replay_vector(vector, REPLAY_DOCUMENT)
        return

    if mutation == "replay-assessment-requirement-count-changed":
        vector = copy.deepcopy(
            _vector_by_id(
                REPLAY_DOCUMENT,
                "evidence.replay.completeness.s04-c01-declared-scope",
            )
        )
        vector["expected"]["facts"]["requirement_count"] = 16
        with pytest.raises(AssertionError):
            _assert_replay_vector(vector, REPLAY_DOCUMENT)
        return

    if mutation == "replay-publication-tree-changed":
        vector = copy.deepcopy(
            _vector_by_id(REPLAY_DOCUMENT, "evidence.replay.publication.acquisition")
        )
        vector["expected"]["facts"]["published_tree"] = "0" * 40
        with pytest.raises(AssertionError):
            _assert_replay_vector(vector, REPLAY_DOCUMENT)
        return

    if mutation in {
        "replay-envelope-inventory-changed",
        "replay-envelope-known-empty-to-unknown",
    }:
        vector = copy.deepcopy(
            _vector_by_id(REPLAY_DOCUMENT, "evidence.replay.envelope.canonical-current")
        )
        if mutation == "replay-envelope-inventory-changed":
            vector["expected"]["component_inventory"]["publications"] = 1
        else:
            vector["expected"]["component_inventory"]["transformations"] = None
        with pytest.raises(AssertionError):
            _assert_replay_vector(vector, REPLAY_DOCUMENT)
        return

    if mutation in {"replay-adapter-status-changed", "replay-adapter-reason-changed"}:
        vector = copy.deepcopy(
            _vector_by_id(
                REPLAY_DOCUMENT,
                "evidence.replay.legacy-adapter.project-legacy-absent",
            )
        )
        if mutation == "replay-adapter-status-changed":
            vector["expected"]["status"] = "losslessly_mappable"
        else:
            vector["expected"]["reasons"] = [
                "multiple_legacy_snapshots_not_representable"
            ]
        with pytest.raises(AssertionError):
            _assert_replay_vector(vector, REPLAY_DOCUMENT)
        return

    if mutation == "replay-source-pointer-digest-changed":
        vector = copy.deepcopy(
            _vector_by_id(REPLAY_DOCUMENT, "evidence.replay.run.canonical-32-request")
        )
        vector["source_pointer"]["sha256"] = "f" * 64
        with pytest.raises(AssertionError):
            _assert_replay_vector(vector, REPLAY_DOCUMENT)
        return

    if mutation == "fixture-missing":
        with pytest.raises(AssertionError):
            _resolve_fixture_value(
                {"fixture_ref": "evidence.fixture.valid.missing"},
                _fixture_map(VALID_DOCUMENT),
            )
        return

    if mutation == "fixture-cycle":
        document = {
            "fixtures": [
                {
                    "id": "evidence.fixture.valid.cycle-a",
                    "status": "locked",
                    "value": {"fixture_ref": "evidence.fixture.valid.cycle-b"},
                },
                {
                    "id": "evidence.fixture.valid.cycle-b",
                    "status": "locked",
                    "value": {"fixture_ref": "evidence.fixture.valid.cycle-a"},
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
            cast(dict[str, Any], manifest["vector_summary"])["valid"]["count"] += 1
        else:
            entry = next(
                item
                for item in cast(list[dict[str, Any]], manifest["corpus_files"])
                if item["filename"] == "valid-vectors.json"
            )
            entry["sha256"] = "f" * 64
        with pytest.raises(AssertionError):
            _assert_manifest_integrity(documents)
        return

    if mutation in {"extra-corpus-file", "mutable-latest-pointer"}:
        contract_root = tmp_path / "evidence-envelope"
        root = contract_root / "v1"
        shutil.copytree(CORPUS_ROOT, root)
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

    if mutation == "filesystem-mode-0755":
        path = tmp_path / "synthetic.json"
        path.write_bytes(b"{}\n")
        path.chmod(0o755)
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

    if mutation in {"production-corpus-reader-inserted", "production-io-inserted"}:
        sources = _working_source_bytes()
        addition = (
            b"\n\nclass EvidenceContractCorpusReader:\n    pass\n"
            if mutation == "production-corpus-reader-inserted"
            else b"\n\ndef _leak(path):\n    return path.read_bytes()\n"
        )
        sources["src/faultatlas/domain/evidence.py"] += addition
        with pytest.raises(AssertionError):
            _assert_no_production_corpus_capability(sources)
        return

    if mutation == "package-root-export-inserted":
        with pytest.raises(AssertionError):
            _assert_package_root_exports(["__version__", "EvidenceEnvelope"])
        return

    project_license = (REPOSITORY_ROOT / "LICENSE").read_bytes()
    historical_license = (REPOSITORY_ROOT / LICENSE_RELATIVE).read_bytes()
    if mutation == "synthetic-package-corpus-member":
        name = f"{CORPUS_RELATIVE}/manifest.json"
        data = b"{}\n"
    else:
        assert mutation == "historical-pytest-license-inserted"
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


def test_actual_offline_build_excludes_corpus(tmp_path: Path) -> None:
    uv = shutil.which("uv")
    assert uv is not None
    project_license = (REPOSITORY_ROOT / "LICENSE").read_bytes()
    historical_license = (REPOSITORY_ROOT / LICENSE_RELATIVE).read_bytes()
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
        [uv, "build", "--offline", "--no-create-gitignore", "--out-dir", str(output)],
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
