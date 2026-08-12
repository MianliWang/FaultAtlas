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
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum, StrEnum
from pathlib import Path, PurePosixPath
from types import UnionType
from typing import (
    Any,
    Literal,
    NamedTuple,
    NoReturn,
    Union,
    cast,
    get_args,
    get_origin,
)

import pytest
from pydantic import BaseModel, RootModel, TypeAdapter, ValidationError

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
CANONICAL_RUN_ID = "run-0001-s04-v1-base-4c9cde74-head-690a63b9"
P00_CLOSURE_RELATIVE = (
    "reference_corpus/pytest-4412/closures/s1-p00-phase-closure/closure.json"
)
P00_CLOSURE_AUTHORITY = "faultatlas-pytest-4412-s1-p00-phase-closure"
PROVIDER_REPOSITORY_ID = "1303365003"
ALTERNATE_REPOSITORY_ID = "1303365004"
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
        15384, "cb33ba75bc77ee9ac1701a09846168fdc44098a821dc246c3129a7d2c8fddfef"
    ),
    "invalid-vectors.json": LockedFile(
        141878, "a379f425e31e1a8627818fb2f4a8afb420975680048f0ecb14da6305022b3592"
    ),
    "invalid-vectors.sha256": LockedFile(
        87, "cfa302e3629fd78a3c839bd71f04872e6cc0516ffe7e5e8be4cc13ebee377c85"
    ),
    "manifest.json": LockedFile(
        22846, "139364b04676d59e4717a38e73b371b138146a2a933688ab3793aac6fd2e03f0"
    ),
    "manifest.sha256": LockedFile(
        80, "648f757f110fbe8ce5ac3376190375f48b42fbb4351f6860356086980d9972e4"
    ),
    "replay-vectors.json": LockedFile(
        120288, "e677aa79cde9142975665f87a5c8be82ba8fa150c302ae11fbd1e863d4d2c32f"
    ),
    "replay-vectors.sha256": LockedFile(
        86, "4b821d5c64c246ff90c8f43c816886312b6cc8008e6f3980bf81866f58bc2228"
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


PROJECTION_KINDS = {"collect", "length", "self_digest", "singleton", "text", "value"}
MAX_POINTER_DEPTH = 16


def _resolve_json_pointer(document: dict[str, Any], json_pointer: str) -> Any:
    assert json_pointer.startswith("/")
    tokens = json_pointer.split("/")[1:]
    assert 1 <= len(tokens) <= MAX_POINTER_DEPTH
    current: Any = document
    for token in tokens:
        assert token
        key = token.replace("~1", "/").replace("~0", "~")
        if isinstance(current, list):
            assert re.fullmatch(r"(?:0|[1-9][0-9]{0,5})", key)
            items = cast(list[Any], current)
            index = int(key)
            assert index < len(items)
            current = items[index]
            continue
        assert isinstance(current, dict)
        mapping = cast(dict[str, Any], current)
        assert key in mapping
        current = mapping[key]
    return current


def _assert_projection_shape(pointer: dict[str, Any]) -> list[dict[str, Any]]:
    assert isinstance(pointer, dict)
    assert set(pointer) == {"authority", "path", "projections", "sha256"}
    authority = pointer["authority"]
    assert isinstance(authority, str) and authority
    raw_projections = pointer["projections"]
    assert isinstance(raw_projections, list)
    projections = cast(list[dict[str, Any]], raw_projections)
    facts_named: list[str] = []
    for entry in projections:
        assert isinstance(entry, dict)
        allowed = {"fact", "json_pointer", "kind"}
        assert set(entry) in (allowed, allowed | {"key"})
        fact = entry["fact"]
        kind = entry["kind"]
        json_pointer = entry["json_pointer"]
        assert isinstance(fact, str) and fact
        assert kind in PROJECTION_KINDS
        assert isinstance(json_pointer, str)
        if kind == "self_digest":
            assert json_pointer == ""
        else:
            assert json_pointer.startswith("/")
        assert ("key" in entry) is (kind == "collect")
        facts_named.append(fact)
    assert facts_named == sorted(facts_named)
    assert len(set(facts_named)) == len(facts_named)
    return projections


def _assert_registered_authority(
    manifest: dict[str, Any], authority: str, path: str, digest: str
) -> None:
    matches: list[tuple[list[str], str]] = []
    for source in cast(list[dict[str, Any]], manifest["source_decisions"]):
        if source["path"] == path:
            matches.append(
                (cast(list[str], source["authority_ids"]), cast(str, source["sha256"]))
            )
    replay_contract = cast(dict[str, Any], manifest["replay_contract"])
    for artifact in cast(list[dict[str, Any]], replay_contract["artifacts"]):
        if artifact["path"] == path:
            matches.append(
                ([cast(str, artifact["authority"])], cast(str, artifact["sha256"]))
            )
    assert len(matches) == 1, f"{path} is not registered exactly once in the manifest"
    authority_ids, registered_digest = matches[0]
    assert authority in authority_ids, (
        f"authority {authority!r} is not registered for {path}"
    )
    assert registered_digest == digest


def _pointer_key(pointer: dict[str, Any]) -> str:
    path = pointer["path"]
    return "" if path is None else cast(str, path)


def _assert_source_pointers(
    vector: dict[str, Any], manifest: dict[str, Any]
) -> list[dict[str, Any]]:
    """Validate every bounded authority a replay vector stands on.

    A vector may name more than one immutable source document, so each pointer
    resolves independently through the manifest registry and no fact may be
    projected out of two different authorities.
    """

    raw = vector["source_pointers"]
    assert isinstance(raw, list)
    pointers = cast(list[dict[str, Any]], raw)
    assert pointers
    ordering = [_pointer_key(item) for item in pointers]
    assert ordering == sorted(ordering)
    assert len(set(ordering)) == len(ordering)
    operation = cast(str, vector["operation"])
    replay_contract = cast(dict[str, Any], manifest["replay_contract"])
    synthetic = cast(str, replay_contract["synthetic_authority"])
    projected: set[str] = set()
    paths: set[str] = set()
    for pointer in pointers:
        projections = _assert_projection_shape(pointer)
        names = {cast(str, entry["fact"]) for entry in projections}
        assert names.isdisjoint(projected)
        projected |= names
        authority = cast(str, pointer["authority"])
        path = pointer["path"]
        digest = pointer["sha256"]
        if path is None:
            assert digest is None
            assert not projections
            assert len(pointers) == 1
            assert authority == synthetic
            assert operation in {"adapter_project", "adapter_wrap"}
            assert vector["evidence_classification"] == "synthetic_contract_example"
            continue
        assert authority != synthetic
        assert vector["evidence_classification"] != "synthetic_contract_example"
        assert isinstance(path, str) and isinstance(digest, str)
        pure = PurePosixPath(path)
        assert not pure.is_absolute()
        assert ".." not in pure.parts
        paths.add(path)
        assert _sha256((REPOSITORY_ROOT / path).read_bytes()) == digest
        _assert_registered_authority(manifest, authority, path, digest)

    if operation in {"replay_record", "replay_envelope"}:
        assert projected
    elif operation == "replay_artifact":
        # One pointer names the retained bytes themselves; any other pointer
        # must carry bounded projections.
        assert len([item for item in pointers if not item["projections"]]) == 1
        assert projected
    else:
        # A non-synthetic adapter replay must carry bounded provenance; only a
        # declared synthetic fixture may stand on corpus-authored values alone.
        assert operation in {"adapter_project", "adapter_wrap"}
        assert bool(projected) is (pointers[0]["path"] is not None)
    return pointers


def _projected_value(
    document: dict[str, Any], entry: dict[str, Any], digest: str
) -> Any:
    kind = cast(str, entry["kind"])
    if kind == "self_digest":
        return digest
    resolved = _resolve_json_pointer(document, cast(str, entry["json_pointer"]))
    if kind == "value":
        return resolved
    if kind == "text":
        assert type(resolved) in (int, str)
        return str(resolved)
    if kind == "singleton":
        return [resolved]
    if kind == "length":
        assert isinstance(resolved, list)
        return len(cast(list[Any], resolved))
    assert kind == "collect"
    assert isinstance(resolved, list)
    key = cast(str, entry["key"])
    collected: list[Any] = []
    for item in cast(list[Any], resolved):
        assert isinstance(item, dict)
        element = cast(dict[str, Any], item)
        assert key in element
        collected.append(element[key])
    return collected


LEGACY_PROJECTION_FIELDS = {"reasons", "snapshot_present", "status"}
PRODUCT_SLICES = {f"S1.P03.S0{index}" for index in range(1, 8)}
# The corpus Slice itself authors the canonical envelope's representation
# choices, so it may own authored leaves without being a product Slice.
AUTHORING_SLICES = PRODUCT_SLICES | {"S1.P03.S08"}
EVIDENCE_CLASSIFICATIONS = {
    "bounded_source_plus_slice_authored_contract",
    "immutable_source_fact",
    "reviewed_derived_composition",
    "synthetic_contract_example",
}
SLICE_AUTHORED_CLASSIFICATION = "bounded_source_plus_slice_authored_contract"
SYNTHETIC_CLASSIFICATION = "synthetic_contract_example"
COMPOSITION_CLASSIFICATION = "reviewed_derived_composition"
IMMUTABLE_SOURCE_CLASSIFICATION = "immutable_source_fact"
DIGEST_ALGORITHM_CANDIDATES = (
    "sha1",
    "sha224",
    "sha256",
    "sha384",
    "sha512",
    "sha3_256",
)
PARTIAL_OUTCOME_VALUES = frozenset({"inaccessible", "unavailable", "unsupported"})

# Independent provenance roots a verified value may ultimately stand on. A fact
# whose complete ancestry stays inside the bounded-source and manifest-registry
# roots is eligible for immutable-source classification; a fact that reaches
# validated runtime composition state is not.
PROJECTION_ROOT_KIND = "bounded_source_projection"
COMPOSITION_ROOT_KIND = "composition_state"
ROOT_KINDS = frozenset(
    {
        "bounded_source_bytes",
        "bounded_source_document",
        COMPOSITION_ROOT_KIND,
        PROJECTION_ROOT_KIND,
    }
)


class ReplayContext(NamedTuple):
    """Independent inputs a derivation may compute from.

    Deliberately carries no corpus-authored expectation: expected values are
    comparison targets, never derivation inputs.
    """

    manifest: dict[str, Any]
    pointers: dict[str, dict[str, Any]]
    documents: dict[str, dict[str, Any]]
    inventory: dict[str, int | None]
    outcomes: tuple[str, ...]


def _completeness_status(outcomes: tuple[str, ...]) -> str:
    """Independently recompute the reviewed S1.P03.S06 derived-status rule."""

    unique = set(outcomes)
    assert unique
    if "unknown" in unique:
        return "scope_unknown"
    if unique & PARTIAL_OUTCOME_VALUES:
        return "scope_partial"
    if "intentionally_omitted" in unique:
        return "scope_satisfied_with_declared_omissions"
    return "scope_satisfied"


def _ordered_source_values(
    document: dict[str, Any], json_pointer: str, key: str
) -> list[str]:
    """Collect one nested key from an ordered source array, in its own order."""

    resolved = _resolve_json_pointer(document, json_pointer)
    assert isinstance(resolved, list)
    values: list[str] = []
    for item in cast(list[Any], resolved):
        node: Any = item
        for part in key.split("/"):
            if not isinstance(node, dict):
                node = None
                break
            mapping = cast(dict[str, Any], node)
            if part not in mapping:
                node = None
                break
            node = mapping[part]
        if isinstance(node, str):
            values.append(node)
    return values


def _compute_artifact_digest_algorithm(
    entry: dict[str, Any], verified: dict[str, Any], context: ReplayContext
) -> Any:
    pointer = context.pointers[cast(str, entry["path"])]
    raw = (REPOSITORY_ROOT / cast(str, pointer["path"])).read_bytes()
    matches = [
        name
        for name in DIGEST_ALGORITHM_CANDIDATES
        if hashlib.new(name, raw).hexdigest() == pointer["sha256"]
    ]
    assert len(matches) == 1
    return matches[0]


def _compute_completeness_status(
    entry: dict[str, Any], verified: dict[str, Any], context: ReplayContext
) -> Any:
    return _completeness_status(context.outcomes)


def _compute_component_count(
    entry: dict[str, Any], verified: dict[str, Any], context: ReplayContext
) -> Any:
    count = context.inventory[cast(str, entry["component"])]
    assert count is not None
    if "minus_fact" in entry:
        other = verified[cast(str, entry["minus_fact"])]
        assert type(other) is int
        return count - other
    return count


def _compute_component_inventory(
    entry: dict[str, Any], verified: dict[str, Any], context: ReplayContext
) -> Any:
    return context.inventory[cast(str, entry["component"])]


def _compute_difference(
    entry: dict[str, Any], verified: dict[str, Any], context: ReplayContext
) -> Any:
    minuend = verified[cast(str, entry["minuend_fact"])]
    subtrahend = verified[cast(str, entry["subtrahend_length_fact"])]
    assert type(minuend) is int and isinstance(subtrahend, list)
    return minuend - len(cast(list[Any], subtrahend))


def _compute_legacy_projection_outcome(
    entry: dict[str, Any], verified: dict[str, Any], context: ReplayContext
) -> Any:
    outcome = _legacy_projection_outcome(context.inventory)
    return outcome[cast(str, entry["outcome_field"])]


def _compute_product(
    entry: dict[str, Any], verified: dict[str, Any], context: ReplayContext
) -> Any:
    factor = verified[cast(str, entry["factor_fact"])]
    assert type(factor) is int
    return factor * cast(int, entry["multiplier"])


def _compute_represented_modern_components(
    entry: dict[str, Any], verified: dict[str, Any], context: ReplayContext
) -> Any:
    return _represented_modern_components(context.inventory)


def _compute_source_file_byte_length(
    entry: dict[str, Any], verified: dict[str, Any], context: ReplayContext
) -> Any:
    pointer = context.pointers[cast(str, entry["path"])]
    return len((REPOSITORY_ROOT / cast(str, pointer["path"])).read_bytes())


def _compute_source_ordered_subset(
    entry: dict[str, Any], verified: dict[str, Any], context: ReplayContext
) -> Any:
    document = context.documents[cast(str, entry["path"])]
    ordered = _ordered_source_values(
        document,
        cast(str, entry["order_json_pointer"]),
        cast(str, entry["order_key"]),
    )
    placed: list[tuple[int, str]] = []
    for json_pointer in cast(list[str], entry["member_json_pointers"]):
        member = _resolve_json_pointer(document, json_pointer)
        assert isinstance(member, str)
        assert ordered.count(member) == 1, (
            f"{member!r} is not a unique member of {json_pointer!r}"
        )
        placed.append((ordered.index(member), member))
    assert len({index for index, _ in placed}) == len(placed)
    return [member for _, member in sorted(placed)]


def _compute_sum(
    entry: dict[str, Any], verified: dict[str, Any], context: ReplayContext
) -> Any:
    total = 0
    for name in cast(list[str], entry["addend_facts"]):
        value = verified[name]
        assert type(value) is int
        total += value
    return total


def _validate_source_path(entry: dict[str, Any]) -> None:
    path = entry["path"]
    assert isinstance(path, str) and path


def _validate_component(entry: dict[str, Any]) -> None:
    assert entry["component"] in ENVELOPE_COMPONENT_FIELDS


def _validate_legacy_projection_outcome(entry: dict[str, Any]) -> None:
    assert entry["outcome_field"] in LEGACY_PROJECTION_FIELDS


def _validate_product(entry: dict[str, Any]) -> None:
    assert type(entry["multiplier"]) is int


def _validate_source_ordered_subset(entry: dict[str, Any]) -> None:
    _validate_source_path(entry)
    members = entry["member_json_pointers"]
    assert isinstance(members, list)
    typed = cast(list[Any], members)
    assert len(typed) > 1
    assert all(isinstance(item, str) and item.startswith("/") for item in typed)
    ordered = cast(list[str], typed)
    assert ordered == sorted(ordered)
    assert len(set(ordered)) == len(ordered)
    order_pointer = entry["order_json_pointer"]
    assert isinstance(order_pointer, str) and order_pointer.startswith("/")
    order_key = entry["order_key"]
    assert isinstance(order_key, str) and order_key
    assert not order_key.startswith("/") and not order_key.endswith("/")


class DerivationRule(NamedTuple):
    """One declared derivation rule and everything the graph needs from it.

    `fact_operands`, `optional_fact_operands`, and `list_operands` are the only
    corpus fields the executor treats as edges. A corpus-authored dependency
    list is never trusted: the edges come from this registry.
    """

    roots: frozenset[str]
    compute: Callable[[dict[str, Any], dict[str, Any], ReplayContext], Any]
    fact_operands: tuple[str, ...] = ()
    optional_fact_operands: tuple[str, ...] = ()
    list_operands: tuple[str, ...] = ()
    constants: tuple[str, ...] = ()
    validate: Callable[[dict[str, Any]], None] | None = None


DERIVATION_REGISTRY: dict[str, DerivationRule] = {
    "artifact_digest_algorithm": DerivationRule(
        roots=frozenset({"bounded_source_bytes"}),
        compute=_compute_artifact_digest_algorithm,
        constants=("path",),
        validate=_validate_source_path,
    ),
    "completeness_status": DerivationRule(
        roots=frozenset({COMPOSITION_ROOT_KIND}),
        compute=_compute_completeness_status,
    ),
    "component_count": DerivationRule(
        roots=frozenset({COMPOSITION_ROOT_KIND}),
        compute=_compute_component_count,
        optional_fact_operands=("minus_fact",),
        constants=("component",),
        validate=_validate_component,
    ),
    "component_inventory": DerivationRule(
        roots=frozenset({COMPOSITION_ROOT_KIND}),
        compute=_compute_component_inventory,
        constants=("component",),
        validate=_validate_component,
    ),
    "difference": DerivationRule(
        roots=frozenset(),
        compute=_compute_difference,
        fact_operands=("minuend_fact", "subtrahend_length_fact"),
    ),
    "legacy_projection_outcome": DerivationRule(
        roots=frozenset({COMPOSITION_ROOT_KIND}),
        compute=_compute_legacy_projection_outcome,
        constants=("outcome_field",),
        validate=_validate_legacy_projection_outcome,
    ),
    "product": DerivationRule(
        roots=frozenset(),
        compute=_compute_product,
        fact_operands=("factor_fact",),
        constants=("multiplier",),
        validate=_validate_product,
    ),
    "represented_modern_components": DerivationRule(
        roots=frozenset({COMPOSITION_ROOT_KIND}),
        compute=_compute_represented_modern_components,
    ),
    "source_file_byte_length": DerivationRule(
        roots=frozenset({"bounded_source_bytes"}),
        compute=_compute_source_file_byte_length,
        constants=("path",),
        validate=_validate_source_path,
    ),
    "source_ordered_subset": DerivationRule(
        roots=frozenset({"bounded_source_document"}),
        compute=_compute_source_ordered_subset,
        constants=(
            "member_json_pointers",
            "order_json_pointer",
            "order_key",
            "path",
        ),
        validate=_validate_source_ordered_subset,
    ),
    "sum": DerivationRule(
        roots=frozenset(),
        compute=_compute_sum,
        list_operands=("addend_facts",),
    ),
}
DERIVATION_RULES = frozenset(DERIVATION_REGISTRY)
PATH_BOUND_RULES = frozenset(
    name for name, rule in DERIVATION_REGISTRY.items() if "path" in rule.constants
)
DOCUMENT_BOUND_RULES = frozenset(
    name
    for name, rule in DERIVATION_REGISTRY.items()
    if "bounded_source_document" in rule.roots
)


def _operand_facts(entry: dict[str, Any]) -> list[str]:
    """Extract this derivation's fact operands from the rule registry."""

    rule = DERIVATION_REGISTRY[cast(str, entry["rule"])]
    names: list[str] = []
    for field in rule.fact_operands:
        names.append(cast(str, entry[field]))
    for field in rule.optional_fact_operands:
        if field in entry:
            names.append(cast(str, entry[field]))
    for field in rule.list_operands:
        names.extend(cast(list[str], entry[field]))
    return names


def _assert_derivation_shape(expected: dict[str, Any]) -> list[dict[str, Any]]:
    raw = expected["derivations"]
    assert isinstance(raw, list)
    derivations = cast(list[dict[str, Any]], raw)
    names: list[str] = []
    for entry in derivations:
        assert isinstance(entry, dict)
        fact = entry["fact"]
        rule_name = entry["rule"]
        assert isinstance(fact, str) and fact
        assert rule_name in DERIVATION_REGISTRY, (
            f"unknown derivation rule {rule_name!r}"
        )
        rule = DERIVATION_REGISTRY[cast(str, rule_name)]
        required = {
            "fact",
            "rule",
            *rule.fact_operands,
            *rule.list_operands,
            *rule.constants,
        }
        present = set(entry)
        assert required <= present, (
            f"{fact!r} is missing {sorted(required - present)!r}"
        )
        extra = present - required
        assert extra <= set(rule.optional_fact_operands), (
            f"{fact!r} declares unexpected fields {sorted(extra)!r}"
        )
        for field in (*rule.fact_operands, *rule.optional_fact_operands):
            if field in entry:
                operand = entry[field]
                assert isinstance(operand, str) and operand
        for field in rule.list_operands:
            operands = entry[field]
            assert isinstance(operands, list)
            typed = cast(list[Any], operands)
            assert typed
            assert all(isinstance(item, str) and item for item in typed)
            ordered = cast(list[str], typed)
            assert ordered == sorted(ordered)
            assert len(set(ordered)) == len(ordered)
        if rule.validate is not None:
            rule.validate(entry)
        names.append(fact)
    assert names == sorted(names)
    assert len(set(names)) == len(names)
    return derivations


class FactVerification(NamedTuple):
    """The verified fact layer a leaf proof may stand on."""

    graph: ProvenanceGraph
    verified: dict[str, Any]
    projected: frozenset[str]
    classification: str
    pointers: frozenset[str]
    used_pointers: frozenset[str]


class ProvenanceGraph(NamedTuple):
    """The acyclic dependency graph over one replay vector's facts."""

    derivations: dict[str, dict[str, Any]]
    order: tuple[str, ...]
    roots: dict[str, frozenset[str]]
    edges: int


def _build_provenance_graph(
    vector_id: str,
    projected: set[str],
    derivations: list[dict[str, Any]],
    labels: set[str],
) -> ProvenanceGraph:
    """Validate and topologically order the fact dependency graph.

    Every derived fact must resolve through operands that are themselves
    independently verified, the graph must be acyclic, and every chain must
    terminate at an independent provenance root.
    """

    targets = [cast(str, entry["fact"]) for entry in derivations]
    assert len(set(targets)) == len(targets), (
        f"{vector_id} declares duplicate derivation targets"
    )
    by_target = {cast(str, entry["fact"]): entry for entry in derivations}
    collisions = projected & set(by_target)
    assert not collisions, (
        f"{vector_id} both projects and derives {sorted(collisions)!r}"
    )
    assert labels.isdisjoint(projected | set(by_target)), (
        f"{vector_id} declares an authored label that is also a fact"
    )

    edges = 0
    for target, entry in by_target.items():
        for operand in _operand_facts(entry):
            edges += 1
            assert operand != target, (
                f"{vector_id} derivation {target!r} names itself as an operand"
            )
            assert operand not in labels, (
                f"{vector_id} derivation {target!r} consumes authored label {operand!r}"
            )
            assert operand in projected or operand in by_target, (
                f"{vector_id} derivation {target!r} names unknown operand {operand!r}"
            )

    order: list[str] = []
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(name: str, stack: tuple[str, ...]) -> None:
        if name in visited:
            return
        assert name not in visiting, (
            f"{vector_id} derivation graph has a cycle: {' -> '.join((*stack, name))}"
        )
        visiting.add(name)
        for operand in _operand_facts(by_target[name]):
            if operand in by_target:
                visit(operand, (*stack, name))
        visiting.discard(name)
        visited.add(name)
        order.append(name)

    for target in sorted(by_target):
        visit(target, ())
    assert len(order) == len(by_target)

    roots: dict[str, frozenset[str]] = {
        name: frozenset({PROJECTION_ROOT_KIND}) for name in projected
    }
    for name in order:
        rule = DERIVATION_REGISTRY[cast(str, by_target[name]["rule"])]
        assert rule.roots <= ROOT_KINDS
        inherited = set(rule.roots)
        for operand in _operand_facts(by_target[name]):
            inherited |= roots[operand]
        assert inherited, (
            f"{vector_id} derivation {name!r} terminates at no independent root"
        )
        roots[name] = frozenset(inherited)
    return ProvenanceGraph(by_target, tuple(order), roots, edges)


def _computed_classification(
    pointers: list[dict[str, Any]], labels: dict[str, Any], graph: ProvenanceGraph
) -> str:
    """Derive the evidence classification from provenance roots.

    The corpus-declared classification is never an input here; it is only ever
    compared against this result.
    """

    if pointers[0]["path"] is None:
        return SYNTHETIC_CLASSIFICATION
    if labels:
        return SLICE_AUTHORED_CLASSIFICATION
    if any(COMPOSITION_ROOT_KIND in kinds for kinds in graph.roots.values()):
        return COMPOSITION_CLASSIFICATION
    return IMMUTABLE_SOURCE_CLASSIFICATION


def _assert_authored_labels(expected: dict[str, Any]) -> dict[str, Any]:
    """Validate the exact contract labels a named Slice introduced.

    An authored label is declared contract data. It is never presented as an
    immutable source fact, a projected fact, or an independently derived fact,
    and it may never serve as a derivation operand.
    """

    raw = expected.get("authored_labels")
    if raw is None:
        return {}
    assert isinstance(raw, list)
    entries = cast(list[dict[str, Any]], raw)
    assert entries
    labels: dict[str, Any] = {}
    names: list[str] = []
    for entry in entries:
        assert isinstance(entry, dict)
        allowed = {"authored_by", "label", "value"}
        assert set(entry) in (allowed, allowed | {"decision_references"})
        label = entry["label"]
        assert isinstance(label, str) and label
        assert entry["authored_by"] in AUTHORING_SLICES
        if "decision_references" in entry:
            references = entry["decision_references"]
            assert isinstance(references, list)
            typed = cast(list[Any], references)
            assert typed
            assert all(
                isinstance(item, str) and item.startswith("decision:") for item in typed
            )
            ordered = cast(list[str], typed)
            assert ordered == sorted(ordered)
            assert len(set(ordered)) == len(ordered)
        names.append(label)
        labels[label] = entry["value"]
    assert names == sorted(names)
    assert len(set(names)) == len(names)
    return labels


def _assert_fact_provenance(
    vector: dict[str, Any],
    observed: dict[str, Any],
    expected: dict[str, Any],
    manifest: dict[str, Any],
    inventory: dict[str, int | None] | None = None,
    outcomes: tuple[str, ...] = (),
) -> FactVerification:
    """Recompute every replay fact from independently verified inputs.

    Projected facts are read out of bounded source bytes and seed the verified
    value set. Derivations are then evaluated in topological order, consuming
    only already verified values, bounded roots, and validated composition
    state. The corpus-authored expectation is compared afterwards; it is never
    an input.
    """

    vector_id = cast(str, vector["id"])
    pointers = cast(list[dict[str, Any]], vector["source_pointers"])
    derivations = _assert_derivation_shape(expected)
    labels = _assert_authored_labels(expected)

    by_path = {_pointer_key(item): item for item in pointers}
    needed = {_pointer_key(item) for item in pointers if item["projections"]}
    used = set(needed)
    for entry in derivations:
        rule_name = cast(str, entry["rule"])
        if rule_name not in PATH_BOUND_RULES:
            continue
        path = cast(str, entry["path"])
        assert path in by_path, (
            f"{vector_id} derives from unregistered source path {path!r}"
        )
        used.add(path)
        if rule_name in DOCUMENT_BOUND_RULES:
            needed.add(path)

    documents = {
        path: _parse_canonical_json((REPOSITORY_ROOT / path).read_bytes())
        for path in sorted(needed)
    }

    verified: dict[str, Any] = {}
    for pointer in pointers:
        projections = _assert_projection_shape(pointer)
        if not projections:
            continue
        document = documents[_pointer_key(pointer)]
        digest = cast(str, pointer["sha256"])
        for entry in projections:
            verified[cast(str, entry["fact"])] = _projected_value(
                document, entry, digest
            )
    projected = set(verified)

    graph = _build_provenance_graph(vector_id, projected, derivations, set(labels))

    declared = cast(dict[str, Any], expected.get("facts", {}))
    assert projected | set(graph.derivations) == set(declared), (
        f"{vector_id} declares facts without provenance: "
        f"{sorted(set(declared) - projected - set(graph.derivations))!r}"
    )
    assert set(declared) | set(labels) == set(observed), (
        f"{vector_id} leaves values unclassified: "
        f"{sorted(set(observed) - set(declared) - set(labels))!r}"
    )

    context = ReplayContext(
        manifest=manifest,
        pointers=by_path,
        documents=documents,
        inventory=inventory or {},
        outcomes=outcomes,
    )
    for name in graph.order:
        entry = graph.derivations[name]
        rule = DERIVATION_REGISTRY[cast(str, entry["rule"])]
        verified[name] = rule.compute(entry, verified, context)

    for name, value in verified.items():
        assert value == observed[name], (
            f"{vector_id} fact {name!r} is {observed[name]!r} but its "
            f"provenance graph computes {value!r}"
        )
    for name, value in declared.items():
        assert observed[name] == value, (
            f"{vector_id} declares fact {name!r} as {value!r} but the replayed "
            f"record carries {observed[name]!r}"
        )
    for name, value in labels.items():
        assert observed[name] == value, (
            f"{vector_id} authored label {name!r} declares {value!r} "
            f"but the replayed record carries {observed[name]!r}"
        )

    computed = _computed_classification(pointers, labels, graph)
    assert vector["evidence_classification"] == computed, (
        f"{vector_id} declares {vector['evidence_classification']!r} but its "
        f"provenance roots compute {computed!r}"
    )
    return FactVerification(
        graph,
        verified,
        frozenset(projected),
        computed,
        frozenset(by_path),
        frozenset(used),
    )


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
        "intentionally_omitted_count": len(
            [
                requirement
                for requirement in assessment.requirements
                if requirement.outcome
                is EvidenceRequirementOutcome.INTENTIONALLY_OMITTED
            ]
        ),
        "intentionally_omitted_requirements": [
            requirement.requirement_id.root
            for requirement in assessment.requirements
            if requirement.outcome is EvidenceRequirementOutcome.INTENTIONALLY_OMITTED
        ],
        "omission_reason": next(iter(reasons)),
        "requirement_count": len(assessment.requirements),
        "satisfied_requirement_count": len(
            [
                requirement
                for requirement in assessment.requirements
                if requirement.outcome is EvidenceRequirementOutcome.SATISFIED
            ]
        ),
        "satisfied_requirements": [
            requirement.requirement_id.root
            for requirement in assessment.requirements
            if requirement.outcome is EvidenceRequirementOutcome.SATISFIED
        ],
        "scope_id": assessment.scope_id.root,
        "status": assessment.status.value,
    }


def _replay_publication_facts(publication: EvidencePublication) -> dict[str, Any]:
    return {
        "main_check_event": publication.main_check.event.value,
        "main_check_job_id": publication.main_check.job_id.root,
        "main_check_run_id": publication.main_check.run_id.root,
        "publication_id": publication.publication_id.root,
        "published_at": publication.published_at.isoformat().replace("+00:00", "Z"),
        "published_revision": publication.published_revision.full_digest,
        "published_tree": publication.published_tree.full_digest,
        "pull_request_check_event": publication.pull_request_check.event.value,
        "pull_request_check_job_id": publication.pull_request_check.job_id.root,
        "pull_request_check_run_id": publication.pull_request_check.run_id.root,
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


def _represented_modern_components(
    inventory: dict[str, int | None],
) -> list[str]:
    return [field for field in MODERN_COMPONENT_FIELDS if inventory[field] is not None]


def _legacy_projection_outcome(inventory: dict[str, int | None]) -> dict[str, Any]:
    """Independently recompute the reviewed S1.P03.S07 fail-closed rule.

    The rule is restated here from the envelope's own component inventory so a
    replayed adapter claim is justified by actual envelope state rather than by
    a corpus-authored expectation.
    """

    legacy = inventory["legacy_snapshots"]
    if legacy is None or legacy == 0:
        return {
            "reasons": ["legacy_snapshot_absent"],
            "snapshot_present": False,
            "status": "not_mappable",
        }
    if legacy > 1:
        return {
            "reasons": ["multiple_legacy_snapshots_not_representable"],
            "snapshot_present": False,
            "status": "not_mappable",
        }
    if _represented_modern_components(inventory):
        return {
            "reasons": ["modern_components_not_representable"],
            "snapshot_present": False,
            "status": "partially_mappable",
        }
    return {"reasons": [], "snapshot_present": True, "status": "losslessly_mappable"}


def _adapter_projection_facts(
    envelope: EvidenceEnvelope, projection: LegacyArtifactSnapshotProjectionResult
) -> dict[str, Any]:
    inventory = _envelope_inventory(envelope)
    return {
        "acquisition_run_ids": [
            run.run_id.root for run in envelope.acquisition_runs or ()
        ],
        "legacy_snapshot_inventory": inventory["legacy_snapshots"],
        "modern_components_represented": _represented_modern_components(inventory),
        "projected_snapshot_present": projection.projected_snapshot is not None,
        "reasons": [reason.value for reason in projection.reasons],
        "status": projection.status.value,
    }


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
        "publication_subject_order": [
            publication.subject_record.sha256.root
            for publication in envelope.publications or ()
        ],
        "run_ids": [run.run_id.root for run in envelope.acquisition_runs or ()],
    }


# --- semantic leaf provenance ------------------------------------------------
#
# A canonical replay record is trusted only when every semantic leaf of its
# validated representation has a proof that terminates in an independently
# verified root. Model validation, an `equals_resolved_input` dump, and
# equality with another corpus-authored record are not proofs.

LEAF_PROOF_KINDS = frozenset(
    {
        "bounded_source_projection",
        "deterministic_derivation",
        "reviewed_contract_literal",
        "slice_authored_contract",
        "verified_child_replay",
        "verified_retained_bytes",
    }
)


def _unwrap_annotation(annotation: Any) -> Any:  # noqa: ANN401
    """Reduce an annotation to the single type its leaf values inhabit."""

    seen: set[Any] = set()
    current: Any = annotation
    while True:
        origin = get_origin(current)
        arguments = get_args(current)
        if origin is Union or origin is UnionType:
            present = [item for item in arguments if item is not type(None)]
            if len(present) == 1:
                current = present[0]
                continue
            return current
        if origin is tuple:
            declared = [item for item in arguments if item is not Ellipsis]
            if len(set(declared)) == 1:
                current = declared[0]
                continue
            return current
        if getattr(current, "__metadata__", None) and arguments:
            current = arguments[0]
            continue
        if (
            isinstance(current, type)
            and issubclass(current, cast(type[BaseModel], RootModel))
            and current not in seen
        ):
            seen.add(current)
            current = cast(Any, current).model_fields["root"].annotation
            continue
        return cast(Any, current)


def _reviewed_contract_literal(annotation: Any) -> tuple[bool, Any]:
    """Report whether the reviewed contract admits exactly one value here.

    Only a single-argument `Literal` or a single-member enumeration qualifies.
    A multi-valued enumeration is a choice, not a contract literal.
    """

    resolved = _unwrap_annotation(annotation)
    if get_origin(resolved) is Literal:
        arguments = get_args(resolved)
        if len(arguments) == 1:
            return True, arguments[0]
    if isinstance(resolved, type) and issubclass(resolved, Enum):
        members = list(resolved)
        if len(members) == 1:
            return True, members[0].value
    return False, None


class SemanticLeaf(NamedTuple):
    """One leaf of a validated record and the contract that declares it."""

    value: Any
    annotation: Any
    declaring_model: str
    field_name: str


def _walk_semantic_leaves(
    value: Any,
    annotation: Any,
    prefix: str,
    declaring_model: str,
    field_name: str,
    out: dict[str, SemanticLeaf],
) -> None:
    if isinstance(value, BaseModel):
        if isinstance(value, cast(type[BaseModel], RootModel)):
            root = cast(Any, value).root
            _walk_semantic_leaves(
                root,
                cast(Any, type(value)).model_fields["root"].annotation,
                prefix,
                type(value).__name__,
                "root",
                out,
            )
            return
        for name, field in type(value).model_fields.items():
            _walk_semantic_leaves(
                getattr(value, name),
                field.annotation,
                f"{prefix}/{name}",
                type(value).__name__,
                name,
                out,
            )
        return
    if isinstance(value, tuple | list):
        items: list[Any] = list(cast(Any, value))
        if not items:
            out[prefix or "/"] = SemanticLeaf(
                [], annotation, declaring_model, field_name
            )
            return
        arguments = get_args(_unwrap_annotation(annotation))
        element = arguments[0] if arguments else None
        for index, item in enumerate(items):
            _walk_semantic_leaves(
                item,
                element if element is not None else type(item),
                f"{prefix}/{index}",
                declaring_model,
                field_name,
                out,
            )
        return
    out[prefix or "/"] = SemanticLeaf(value, annotation, declaring_model, field_name)


def _semantic_leaves(model: BaseModel) -> dict[str, SemanticLeaf]:
    """Flatten a validated record into stable semantic leaf paths.

    The walk is driven by the production model itself, so a new field on a
    replayed model becomes a new uncovered leaf and fails closed.
    """

    leaves: dict[str, SemanticLeaf] = {}
    _walk_semantic_leaves(model, type(model), "", type(model).__name__, "", leaves)
    dumped: dict[str, Any] = {}
    _walk_dump_leaves(_semantic_dump(model), "", dumped)
    assert set(dumped) == set(leaves), (
        f"leaf walk disagrees with the semantic dump: "
        f"{sorted(set(dumped) ^ set(leaves))!r}"
    )
    return {
        path: SemanticLeaf(
            dumped[path], leaf.annotation, leaf.declaring_model, leaf.field_name
        )
        for path, leaf in leaves.items()
    }


def _walk_dump_leaves(value: Any, prefix: str, out: dict[str, Any]) -> None:
    if isinstance(value, dict):
        mapping = cast(dict[str, Any], value)
        if not mapping:
            out[prefix or "/"] = {}
            return
        for key in sorted(mapping):
            _walk_dump_leaves(mapping[key], f"{prefix}/{key}", out)
        return
    if isinstance(value, list):
        items = cast(list[Any], value)
        if not items:
            out[prefix or "/"] = []
            return
        for index, item in enumerate(items):
            _walk_dump_leaves(item, f"{prefix}/{index}", out)
        return
    out[prefix or "/"] = value


class LeafProof(NamedTuple):
    """Why one semantic leaf is trusted."""

    kind: str
    owner: str


LEAF_RULE_KINDS = frozenset(
    {"authored", "bytes", "child", "contract_literal", "fact", "source"}
)
BYTE_MEASURES = frozenset({"byte_length", "sha256"})


def _leaf_pattern_matches(pattern: str, path: str) -> tuple[int, ...] | None:
    """Match a leaf path against a pattern whose `#` segments are indices."""

    expected = pattern.split("/")
    actual = path.split("/")
    if len(expected) != len(actual):
        return None
    wildcards: list[int] = []
    for want, have in zip(expected, actual):
        if want.startswith("#"):
            if not re.fullmatch(r"(?:0|[1-9][0-9]{0,5})", have):
                return None
            index = int(have)
            bounds = want[1:]
            if bounds:
                low, _, high = bounds.partition("-")
                assert low.isdigit() and high.isdigit(), (
                    f"malformed bounded index pattern {want!r}"
                )
                if not int(low) <= index <= int(high):
                    return None
            wildcards.append(index)
            continue
        if want != have:
            return None
    return tuple(wildcards)


def _expand_leaf_pattern(
    pattern: str, paths: list[str]
) -> list[tuple[str, tuple[int, ...]]]:
    matched = [
        (path, wildcards)
        for path in paths
        if (wildcards := _leaf_pattern_matches(pattern, path)) is not None
    ]
    # Sequence semantics follow numeric index order, not lexicographic paths.
    matched.sort(key=lambda item: (item[1], item[0]))
    return matched


def _subtree_leaves(subtree: str, paths: list[str]) -> list[str]:
    prefix = f"{subtree}/"
    return [path for path in paths if path == subtree or path.startswith(prefix)]


def _resolve_pointer_template(
    template: str, wildcards: tuple[int, ...], rank: int
) -> str:
    resolved = template.replace("#seq", str(rank))
    for index, value in enumerate(wildcards, start=1):
        resolved = resolved.replace(f"#{index}", str(value))
    assert "#" not in resolved, f"unresolved pointer template {template!r}"
    return resolved


class ReplayVerification(NamedTuple):
    """A canonical replay vector proved leaf-complete."""

    vector_id: str
    dump: Any
    leaves: dict[str, SemanticLeaf]
    proofs: dict[str, LeafProof]
    corroborations: dict[str, tuple[str, ...]]
    children: tuple[str, ...]


class ReplaySession:
    """Verifies canonical replay vectors, memoized, with cycle detection."""

    def __init__(self, document: dict[str, Any]) -> None:
        self.document = document
        self.results: dict[str, ReplayVerification] = {}
        self.active: list[str] = []

    def verify(self, vector_id: str) -> ReplayVerification:
        cached = self.results.get(vector_id)
        if cached is not None:
            return cached
        assert vector_id not in self.active, (
            f"replay dependency cycle: {' -> '.join((*self.active, vector_id))}"
        )
        self.active.append(vector_id)
        try:
            verified = _verify_replay_vector(
                _vector_by_id(self.document, vector_id), self.document, self
            )
            assert verified is not None, f"{vector_id} yields no verified replay"
        finally:
            self.active.pop()
        self.results[vector_id] = verified
        return verified


def _assert_authored_leaves(expected: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Validate authored contract values declared apart from the record."""

    raw = expected.get("authored_leaves")
    if raw is None:
        return {}
    assert isinstance(raw, list)
    entries = cast(list[dict[str, Any]], raw)
    assert entries
    declared: dict[str, dict[str, Any]] = {}
    names: list[str] = []
    for entry in entries:
        assert isinstance(entry, dict)
        allowed = {"authored_by", "id", "values"}
        assert set(entry) in (allowed, allowed | {"decision_references"})
        identifier = entry["id"]
        assert isinstance(identifier, str) and identifier
        assert entry["authored_by"] in AUTHORING_SLICES
        values = entry["values"]
        assert isinstance(values, list) and cast(list[Any], values)
        if "decision_references" in entry:
            references = cast(list[Any], entry["decision_references"])
            assert references
            assert all(
                isinstance(item, str) and item.startswith("decision:")
                for item in references
            )
            ordered = cast(list[str], references)
            assert ordered == sorted(ordered)
        names.append(identifier)
        declared[identifier] = entry
    assert names == sorted(names)
    assert len(set(names)) == len(names)
    return declared


def _leaf_matches_source(value: Any, resolved: Any) -> bool:
    """Compare a semantic leaf with the source value that carries it."""

    if value == resolved and type(value) is type(resolved):
        return True
    # Source documents record some identifiers as integers that the reviewed
    # model carries as exact lexemes.
    if isinstance(value, str) and type(resolved) is int:
        return value == str(resolved)
    return False


def _assert_leaf_closure(
    vector: dict[str, Any],
    model: BaseModel,
    expected: dict[str, Any],
    facts: FactVerification,
    session: ReplaySession,
) -> ReplayVerification:
    """Prove every semantic leaf of a canonical record terminates honestly."""

    vector_id = cast(str, vector["id"])
    leaves = _semantic_leaves(model)
    paths = sorted(leaves)
    raw = expected["leaf_proofs"]
    assert isinstance(raw, list)
    rules = cast(list[dict[str, Any]], raw)
    assert rules
    labels = _assert_authored_labels(expected)
    contracts = _assert_authored_leaves(expected)
    pointers = {
        _pointer_key(item)
        for item in cast(list[dict[str, Any]], vector["source_pointers"])
    }
    documents: dict[str, dict[str, Any]] = {}

    primary: dict[str, LeafProof] = {}
    corroborations: dict[str, list[str]] = {}
    children: list[str] = []
    source_paths: set[str] = set()

    def claim(path: str, proof: LeafProof, corroborates: bool) -> None:
        assert proof.kind in LEAF_PROOF_KINDS
        if corroborates:
            corroborations.setdefault(path, []).append(f"{proof.kind}:{proof.owner}")
            return
        assert path not in primary, (
            f"{vector_id} leaf {path!r} has two primary proofs: "
            f"{primary[path]!r} and {proof!r}"
        )
        primary[path] = proof

    for rule in rules:
        assert isinstance(rule, dict)
        kind = rule["kind"]
        assert kind in LEAF_RULE_KINDS, f"unknown leaf proof kind {kind!r}"
        corroborates = rule.get("corroborates", False)
        assert type(corroborates) is bool

        if kind == "child":
            assert set(rule) == {"kind", "subtree", "vector"}
            subtree = cast(str, rule["subtree"])
            covered = _subtree_leaves(subtree, paths)
            assert covered, f"{vector_id} child subtree {subtree!r} matches no leaf"
            child_id = cast(str, rule["vector"])
            assert child_id != vector_id, f"{vector_id} binds a subtree to itself"
            child_vector = _vector_by_id(session.document, child_id)
            assert child_vector["operation"] in {
                "replay_artifact",
                "replay_envelope",
                "replay_record",
            }, f"{vector_id} binds a subtree to a non-record replay"
            assert (
                child_vector["evidence_classification"] != SYNTHETIC_CLASSIFICATION
            ), f"{vector_id} binds canonical evidence to synthetic {child_id}"
            child = session.verify(child_id)
            children.append(child_id)
            relatives = {path: path[len(subtree) :] or "/" for path in covered}
            assert set(relatives.values()) == set(child.leaves), (
                f"{vector_id} subtree {subtree!r} does not match the shape of "
                f"{child_id}"
            )
            for path, relative in relatives.items():
                assert leaves[path].value == child.leaves[relative].value, (
                    f"{vector_id} leaf {path!r} differs from the verified "
                    f"{child_id} replay"
                )
                claim(path, LeafProof("verified_child_replay", child_id), False)
            continue

        pattern = cast(str, rule["pattern"])
        matched = _expand_leaf_pattern(pattern, paths)
        assert matched, f"{vector_id} leaf rule {pattern!r} matches no leaf"
        for rank, (path, wildcards) in enumerate(matched):
            leaf = leaves[path]
            if kind == "contract_literal":
                assert set(rule) <= {"kind", "pattern", "corroborates"}
                unique, only = _reviewed_contract_literal(leaf.annotation)
                assert unique, (
                    f"{vector_id} leaf {path!r} is not uniquely constrained by "
                    f"the reviewed contract"
                )
                assert leaf.value == only
                proof = LeafProof(
                    "reviewed_contract_literal",
                    f"{leaf.declaring_model}.{leaf.field_name}",
                )
            elif kind == "source":
                source_path = cast(str, rule["path"])
                assert source_path in pointers, (
                    f"{vector_id} leaf rule names unregistered source {source_path!r}"
                )
                source_paths.add(source_path)
                document = documents.get(source_path)
                if document is None:
                    document = _parse_canonical_json(
                        (REPOSITORY_ROOT / source_path).read_bytes()
                    )
                    documents[source_path] = document
                pointer = _resolve_pointer_template(
                    cast(str, rule["json_pointer"]), wildcards, rank
                )
                resolved = _resolve_json_pointer(document, pointer)
                assert _leaf_matches_source(leaf.value, resolved), (
                    f"{vector_id} leaf {path!r} is {leaf.value!r} but "
                    f"{source_path}{pointer} carries {resolved!r}"
                )
                proof = LeafProof(
                    "bounded_source_projection", f"{source_path}{pointer}"
                )
            elif kind == "bytes":
                artifact = cast(str, rule["path"])
                assert artifact in pointers
                source_paths.add(artifact)
                measure = cast(str, rule["measure"])
                assert measure in BYTE_MEASURES
                data = (REPOSITORY_ROOT / artifact).read_bytes()
                actual: Any = len(data) if measure == "byte_length" else _sha256(data)
                assert leaf.value == actual, (
                    f"{vector_id} leaf {path!r} is {leaf.value!r} but the "
                    f"retained bytes of {artifact} give {actual!r}"
                )
                proof = LeafProof("verified_retained_bytes", f"{artifact}#{measure}")
            elif kind == "fact":
                name = cast(str, rule["fact"])
                assert name in facts.verified, (
                    f"{vector_id} leaf rule names unverified fact {name!r}"
                )
                verified = facts.verified[name]
                if rule.get("sequence", False):
                    sequence = cast(list[Any], verified)
                    assert isinstance(verified, list) and rank < len(sequence)
                    want = sequence[rank]
                else:
                    want = verified
                assert leaf.value == want, (
                    f"{vector_id} leaf {path!r} is {leaf.value!r} but verified "
                    f"fact {name!r} is {want!r}"
                )
                proof = LeafProof(
                    "bounded_source_projection"
                    if name in facts.projected
                    else "deterministic_derivation",
                    name,
                )
            else:
                assert kind == "authored"
                if "label" in rule:
                    owner = cast(str, rule["label"])
                    assert owner in labels
                    want = labels[owner]
                else:
                    owner = cast(str, rule["contract"])
                    assert owner in contracts, (
                        f"{vector_id} authored leaf rule names undeclared "
                        f"contract {owner!r}"
                    )
                    values = cast(list[Any], contracts[owner]["values"])
                    want = values[rank] if rule.get("sequence", False) else values[0]
                assert leaf.value == want, (
                    f"{vector_id} leaf {path!r} is {leaf.value!r} but its "
                    f"authored contract declares {want!r}"
                )
                proof = LeafProof("slice_authored_contract", owner)
            claim(path, proof, corroborates)

    assert facts.used_pointers | source_paths == facts.pointers, (
        f"{vector_id} carries unused source pointers: "
        f"{sorted(facts.pointers - facts.used_pointers - source_paths)!r}"
    )
    uncovered = set(leaves) - set(primary)
    assert not uncovered, (
        f"{vector_id} leaves {len(uncovered)} semantic leaves unproven; "
        f"shapes: {sorted({re.sub(r'/[0-9]+', '/#', path) for path in uncovered})!r}"
    )
    return ReplayVerification(
        vector_id,
        _semantic_dump(model),
        leaves,
        primary,
        {path: tuple(items) for path, items in corroborations.items()},
        tuple(children),
    )


def _assert_replay_vector(vector: dict[str, Any], document: dict[str, Any]) -> None:
    _verify_replay_vector(vector, document, ReplaySession(document))


def _verify_replay_vector(
    vector: dict[str, Any], document: dict[str, Any], session: ReplaySession
) -> ReplayVerification | None:
    """Verify one replay vector through every applicable assurance layer.

    A canonical record is returned as a `ReplayVerification` only after its
    model validates, its semantic dump matches, its facts are graph-verified,
    and every semantic leaf terminates in an honest proof.
    """

    _assert_operation_target(vector)
    assert vector["input_mode"] == "replay"
    assert vector["evidence_classification"] in EVIDENCE_CLASSIFICATIONS
    pointers = _assert_source_pointers(vector, MANIFEST_DOCUMENT)
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
        bytes_pointer = next(item for item in pointers if not item["projections"])
        assert artifact_path == bytes_pointer["path"]
        raw = (REPOSITORY_ROOT / artifact_path).read_bytes()
        assert len(raw) == expected["byte_length"]
        assert _sha256(raw) == expected["sha256"]
        identity = ExactArtifactIdentity.model_validate_json(
            _json_text(replay_input["artifact_identity"])
        )
        assert identity.byte_length.root == len(raw)
        assert identity.digest.value.root == _sha256(raw)
        facts = _assert_fact_provenance(
            vector,
            {
                "digest_algorithm": identity.digest.algorithm.value,
                "digest_scope": identity.digest.scope.root,
            },
            expected,
            MANIFEST_DOCUMENT,
        )
        return _assert_leaf_closure(vector, identity, expected, facts, session)

    if operation == "replay_record":
        assert set(replay_input) == {"record"}
        record = replay_input["record"]
        model = _validate_model(MODEL_TARGETS[target], record, "json")
        _round_trip_model(MODEL_TARGETS[target], model)
        _assert_expected_dump(expected, _semantic_dump(model), record)
        facts = _replay_record_facts(target, model)
        outcomes: tuple[str, ...] = ()
        if isinstance(model, EvidenceCompletenessAssessment):
            outcomes = tuple(
                requirement.outcome.value for requirement in model.requirements
            )
        verified = _assert_fact_provenance(
            vector, facts, expected, MANIFEST_DOCUMENT, outcomes=outcomes
        )
        assert expected["runtime_target"] == target
        return _assert_leaf_closure(vector, model, expected, verified, session)

    if operation == "replay_envelope":
        assert set(replay_input) == {"envelope"}
        payload = replay_input["envelope"]
        envelope = _validate_model(EvidenceEnvelope, payload, "json")
        assert isinstance(envelope, EvidenceEnvelope)
        _round_trip_model(EvidenceEnvelope, envelope)
        _assert_expected_dump(expected, _semantic_dump(envelope), payload)
        inventory = _envelope_inventory(envelope)
        assert inventory == expected["component_inventory"]
        envelope_facts = _envelope_facts(envelope)
        verified = _assert_fact_provenance(
            vector, envelope_facts, expected, MANIFEST_DOCUMENT, inventory
        )
        assert expected["runtime_target"] == target
        return _assert_leaf_closure(vector, envelope, expected, verified, session)

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
        return None

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

    if pointers[0]["path"] is None:
        assert "authored_labels" not in expected
        assert "authored_leaves" not in expected
        assert "component_inventory" not in expected
        assert "derivations" not in expected
        assert "facts" not in expected
        assert "leaf_proofs" not in expected
        return None
    inventory = _envelope_inventory(source_envelope)
    assert inventory == expected["component_inventory"]
    facts = _adapter_projection_facts(source_envelope, projection)
    verified = _assert_fact_provenance(
        vector, facts, expected, MANIFEST_DOCUMENT, inventory
    )
    return _assert_leaf_closure(vector, source_envelope, expected, verified, session)


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
    assert {entry.name for entry in root.parent.iterdir()} == {"closures", "v1"}
    closures = root.parent / "closures"
    assert closures.is_dir() and not closures.is_symlink()
    assert {entry.name for entry in closures.iterdir()} == {"s1-p03-phase-closure"}
    phase_closure = closures / "s1-p03-phase-closure"
    assert phase_closure.is_dir() and not phase_closure.is_symlink()
    assert {entry.name for entry in phase_closure.iterdir()} == {
        "closure.json",
        "closure.md",
        "closure.sha256",
    }
    for entry in phase_closure.iterdir():
        _assert_fs_regular_0644(entry)
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


SHA1_PATTERN = re.compile(r"[0-9a-f]{40}")


def _assert_originating_publications(manifest: dict[str, Any]) -> None:
    section = cast(dict[str, Any], manifest["originating_publications"])
    assert set(section) == {
        "records",
        "tracked_evidence_available",
        "verification_owner",
        "verification_state",
    }
    assert section["tracked_evidence_available"] is False
    assert section["verification_owner"] == "S1.P03.S09"
    assert section["verification_state"] == (
        "structurally_validated_pending_phase_closure_evidence"
    )

    records = cast(list[dict[str, Any]], section["records"])
    assert len(records) == 8
    numbers = [cast(int, record["pull_request"]) for record in records]
    assert numbers == sorted(numbers)
    assert numbers == list(range(31, 39))
    reviewed_heads: set[str] = set()
    squashes: set[str] = set()
    product_slices: list[str] = []
    corrective_slices: list[str] = []
    for record in records:
        assert set(record) == {
            "publication_kind",
            "pull_request",
            "reviewed_head",
            "reviewed_tree",
            "slice_id",
            "squash",
            "squash_tree",
        }
        for field in ("reviewed_head", "reviewed_tree", "squash", "squash_tree"):
            value = record[field]
            assert isinstance(value, str)
            assert SHA1_PATTERN.fullmatch(value)
        assert record["reviewed_tree"] == record["squash_tree"]
        assert record["reviewed_head"] != record["squash"]
        reviewed_heads.add(cast(str, record["reviewed_head"]))
        squashes.add(cast(str, record["squash"]))
        slice_id = cast(str, record["slice_id"])
        assert slice_id in PRODUCT_SLICES
        if record["publication_kind"] == "product":
            product_slices.append(slice_id)
        else:
            assert record["publication_kind"] == "test_only_corrective"
            corrective_slices.append(slice_id)
    assert len(reviewed_heads) == 8
    assert len(squashes) == 8
    assert product_slices == sorted(PRODUCT_SLICES)
    assert corrective_slices == ["S1.P03.S07"]


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
    assert replay_contract["source_projection_verification"] == (
        "required_for_record_and_envelope_replay"
    )
    assert replay_contract["fact_provenance"] == (
        "every_fact_is_projected_or_derived_by_declared_rule"
    )
    assert replay_contract["derivation_rules"] == sorted(DERIVATION_RULES)
    assert replay_contract["derivation_contract"] == (
        "expected_values_are_comparison_targets_not_derivation_inputs"
    )
    assert replay_contract["derivation_evaluation"] == (
        "acyclic_dependency_graph_evaluated_over_verified_values"
    )
    assert replay_contract["classification_source"] == (
        "computed_from_provenance_roots_then_compared_with_declaration"
    )
    assert replay_contract["provenance_root_kinds"] == sorted(ROOT_KINDS)
    assert replay_contract["nested_record_authentication"] == (
        "populated_components_bind_to_transitively_verified_child_replays"
    )
    assert replay_contract["leaf_closure"] == (
        "every_non_synthetic_canonical_semantic_leaf_has_one_primary_proof_owner"
    )
    assert replay_contract["leaf_proof_classes"] == sorted(LEAF_PROOF_KINDS)
    assert replay_contract["evidence_classifications"] == sorted(
        EVIDENCE_CLASSIFICATIONS
    )
    assert replay_contract["authored_label_contract"] == (
        "slice_authored_labels_are_declared_contract_data_not_source_evidence"
    )
    assert replay_contract["authored_label_fields"] == [
        "authored_by",
        "decision_references",
        "label",
        "value",
    ]
    assert replay_contract["publication_order_provenance"] == (
        "publication_subject_order_projected_from_s1_p00_slice_ledger_order"
    )
    assert replay_contract["source_pointer_cardinality"] == (
        "one_or_more_bounded_authorities_each_projected_or_derived_from"
    )
    assert replay_contract["adapter_provenance"] == (
        "non_synthetic_adapter_replay_requires_bounded_projection"
    )
    assert replay_contract["projection_kinds"] == sorted(PROJECTION_KINDS)
    assert replay_contract["authority_resolution"] == (
        "pointer_authority_path_and_digest_must_resolve_through_manifest"
    )
    assert replay_contract["synthetic_authority"] == "synthetic-legacy-adapter-fixture"
    assert replay_contract["source_pointer_fields"] == [
        "authority",
        "path",
        "projections",
        "sha256",
    ]
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
        assert set(artifact) == {
            "authority",
            "byte_length",
            "digest_scope",
            "path",
            "sha256",
        }
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

    _assert_originating_publications(manifest)

    boundaries = cast(dict[str, Any], manifest["semantic_boundaries"])
    assert set(boundaries) == {
        "corpus_canonical_json_bytes",
        "declared_scope_completeness",
        "future_durable_production_record_bytes",
        "python_model_equality",
        "retained_exact_artifact_bytes",
        "semantic_json_representation",
    }
    assert boundaries["declared_scope_completeness"] == (
        "bounded_to_one_declared_scope_never_a_universal_completeness_claim"
    )
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
                expected_keys |= {"evidence_classification", "source_pointers"}
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
            if filename == "replay-vectors.json":
                for pointer in cast(list[dict[str, Any]], vector["source_pointers"]):
                    _assert_projection_shape(pointer)
            else:
                references = vector["decision_references"]
                assert isinstance(references, list)
                typed_references = cast(list[Any], references)
                assert typed_references
                assert all(
                    isinstance(item, str) and item.startswith("decision:")
                    for item in typed_references
                )
                assert typed_references == sorted(cast(list[str], typed_references))
                assert len(set(cast(list[str], typed_references))) == len(
                    typed_references
                )
    assert len(seen) == EXPECTED_TOTAL_VECTORS
    _assert_decision_registry(documents)


def _assert_decision_registry(documents: dict[str, dict[str, Any]]) -> None:
    registered: set[str] = set()
    for source in cast(
        list[dict[str, Any]], documents["manifest.json"]["source_decisions"]
    ):
        registered.update(cast(list[str], source["authority_ids"]))
    referenced: set[str] = set()
    for filename in ("valid-vectors.json", "invalid-vectors.json"):
        for vector in _vectors(documents[filename]):
            referenced.update(cast(list[str], vector["decision_references"]))
    for vector in _vectors(documents["replay-vectors.json"]):
        expected = cast(dict[str, Any], vector["expected"])
        for entry in cast(list[dict[str, Any]], expected.get("authored_labels", [])):
            referenced.update(cast(list[str], entry.get("decision_references", [])))
    assert referenced
    assert referenced <= registered, sorted(referenced - registered)
    assert {item for item in registered if item.startswith("decision:")} == referenced


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


MANIFEST_DOCUMENT = _load_document("manifest.json")
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


def test_roadmap_records_s08_and_s09_complete_with_p04_next() -> None:
    roadmap = (REPOSITORY_ROOT / "docs/roadmap.md").read_text(encoding="utf-8")
    assert "`S1.P03.S08` — Evidence Contract Corpus (complete)" in roadmap
    assert (
        "`S1.P03.S09` — Integration and Phase Closure (complete; closes `S1.P03`)"
        in roadmap
    )
    assert "`S1.P03` is complete" in roadmap
    assert "`S1.P04` is next and not started" in roadmap
    assert "`S1.P05` through `S1.P10` remain not started" in roadmap
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
    "replay-source-pointer-retargeted",
    "replay-projection-pointer-changed",
    "replay-projection-kind-changed",
    "replay-unclassified-fact",
    "replay-numeric-fact-changed",
    "replay-derivation-list-unsorted",
    "replay-decision-reference-unregistered",
    "replay-authority-not-registered",
    "replay-authority-path-unregistered",
    "replay-derivation-recompute-mismatch",
    "replay-derivation-rule-missing",
    "manifest-publication-tree-inequality",
    "manifest-publication-verification-overclaimed",
    "replay-canonical-adapter-empty-provenance",
    "replay-canonical-adapter-coherent-legacy-change",
    "replay-source-backed-fact-coherent-change",
    "replay-authored-label-value-mismatch",
    "replay-authored-label-declaration-removed",
    "replay-authored-label-misclassified-as-source",
    "replay-authored-derivation-rule-reintroduced",
    "replay-canonical-publication-order-reversed",
    "replay-publication-subject-digest-changed",
    "replay-source-pointer-unused",
    "replay-duplicate-projected-fact",
    "replay-self-reference-via-product-factor",
    "replay-self-reference-via-difference-minuend",
    "replay-self-reference-via-difference-subtrahend",
    "replay-self-reference-via-sum-addend",
    "replay-self-reference-via-component-minus",
    "replay-derivation-two-node-cycle",
    "replay-derivation-three-node-cycle",
    "replay-derivation-unknown-operand",
    "replay-derivation-authored-label-operand",
    "replay-duplicate-derivation-target",
    "replay-projected-derived-name-collision",
    "replay-classification-composition-as-source",
    "replay-classification-source-as-composition",
    "replay-classification-synthetic-as-source",
    "replay-envelope-nested-record-drift",
    "replay-artifact-scope-coherent-drift",
    "leaf-compare-diff-digest-drift",
    "leaf-compare-diff-byte-length-drift",
    "leaf-license-digest-drift",
    "leaf-license-byte-length-drift",
    "leaf-run-timestamp-drift",
    "leaf-correction-drift",
    "leaf-completeness-drift",
    "leaf-publication-check-drift",
    "leaf-proof-rule-removed",
    "leaf-proof-rule-matches-nothing",
    "leaf-proof-primary-overlap",
    "leaf-child-binding-mismatched",
    "leaf-child-replay-failure",
    "leaf-child-self-dependency",
    "leaf-child-dependency-cycle",
    "leaf-synthetic-child-binding",
    "leaf-contract-literal-multivalued",
    "leaf-authored-value-drift",
    "leaf-source-pointer-retargeted",
    "leaf-sequence-reordered",
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
assert len(REQUIRED_MUTATIONS) == 103


LEAF_DRIFT_PROBES: dict[str, tuple[str, str, str]] = {
    "leaf-compare-diff-digest-drift": (
        "evidence.replay.run.canonical-32-request",
        "dca87a4df1edb2d1acb3fc821724483ee874c2feba6525b2c21e79cb3e8f7312",
        "f" * 64,
    ),
    "leaf-compare-diff-byte-length-drift": (
        "evidence.replay.run.canonical-32-request",
        "1640",
        "1639",
    ),
    "leaf-license-digest-drift": (
        "evidence.replay.run.canonical-32-request",
        "a1ebce15afc7b5cf98c7c6de512d1959d4bf61db8c6bf2f111286d483b40a997",
        "e" * 64,
    ),
    "leaf-license-byte-length-drift": (
        "evidence.replay.run.canonical-32-request",
        "1096",
        "1095",
    ),
    "leaf-run-timestamp-drift": (
        "evidence.replay.run.canonical-32-request",
        "2026-07-24T11:03:15.269222Z",
        "2026-07-24T11:03:15.269223Z",
    ),
    "leaf-correction-drift": (
        "evidence.replay.relationship.s04-c01-correction",
        "faultatlas-acquisition",
        "faultatlas-acquisition-renamed",
    ),
    "leaf-completeness-drift": (
        "evidence.replay.completeness.s04-c01-declared-scope",
        "issue_comment_bodies",
        "issue_comment_bodies_renamed",
    ),
    "leaf-publication-check-drift": (
        "evidence.replay.publication.acquisition",
        "90821631028",
        "90821631029",
    ),
}


def _leaf_probe_document(mutation: str) -> tuple[dict[str, Any], str]:
    """Build one mutated corpus for a leaf-provenance probe."""

    document = copy.deepcopy(REPLAY_DOCUMENT)
    run_id = "evidence.replay.run.canonical-32-request"
    diff_id = "evidence.replay.artifact.compare-diff"
    envelope_id = "evidence.replay.envelope.canonical-current"

    if mutation in LEAF_DRIFT_PROBES:
        vector_id, before, after = LEAF_DRIFT_PROBES[mutation]
        vector = _vector_by_id(document, vector_id)
        resolved = _json_text(_resolved_input(vector, document))
        assert before in resolved
        vector["input"] = json.loads(resolved.replace(before, after))
        return document, vector_id

    vector = _vector_by_id(document, run_id)
    expected = cast(dict[str, Any], vector["expected"])
    rules = cast(list[dict[str, Any]], expected["leaf_proofs"])
    if mutation == "leaf-proof-rule-removed":
        rules[:] = [item for item in rules if item.get("pattern") != "/run_id"]
    elif mutation == "leaf-proof-rule-matches-nothing":
        rules.append({"kind": "contract_literal", "pattern": "/absent_field"})
    elif mutation == "leaf-proof-primary-overlap":
        rules.append({"fact": "run_id", "kind": "fact", "pattern": "/run_id"})
    elif mutation == "leaf-child-binding-mismatched":
        entry = next(item for item in rules if item.get("vector") == diff_id)
        entry["vector"] = "evidence.replay.artifact.historical-license"
    elif mutation == "leaf-child-replay-failure":
        child = _vector_by_id(document, diff_id)
        cast(dict[str, Any], child["expected"])["sha256"] = "a" * 64
    elif mutation == "leaf-child-self-dependency":
        rules.append({"kind": "child", "subtree": "", "vector": run_id})
    elif mutation == "leaf-child-dependency-cycle":
        child = _vector_by_id(document, diff_id)
        cast(list[dict[str, Any]], child["expected"]["leaf_proofs"]).append(
            {"kind": "child", "subtree": "", "vector": run_id}
        )
    elif mutation == "leaf-synthetic-child-binding":
        entry = next(item for item in rules if item.get("vector") == diff_id)
        entry["vector"] = "evidence.replay.legacy-adapter.project-legacy-absent"
    elif mutation == "leaf-contract-literal-multivalued":
        rules[:] = [item for item in rules if item.get("pattern") != "/status"]
        rules.append({"kind": "contract_literal", "pattern": "/status"})
    elif mutation == "leaf-source-pointer-retargeted":
        entry = next(
            item
            for item in rules
            if item.get("pattern") == "/requests/#/request_id/request_ordinal"
        )
        entry["json_pointer"] = "/requests/records/#1/status"
    elif mutation == "leaf-authored-value-drift":
        assessment_id = "evidence.replay.completeness.s04-c01-declared-scope"
        vector = _vector_by_id(document, assessment_id)
        resolved = _json_text(_resolved_input(vector, document))
        vector["input"] = json.loads(
            resolved.replace("s04-c01-declared-evidence-scope", "s04-c01-renamed")
        )
        return document, assessment_id
    else:
        assert mutation == "leaf-sequence-reordered"
        assessment_id = "evidence.replay.completeness.s04-c01-declared-scope"
        vector = _vector_by_id(document, assessment_id)
        leaves = cast(
            list[dict[str, Any]],
            cast(dict[str, Any], vector["expected"])["authored_leaves"],
        )
        entry = next(item for item in leaves if item["id"] == "omission_ids")
        entry["values"] = list(reversed(cast(list[Any], entry["values"])))
        return document, assessment_id
    if mutation == "leaf-child-replay-failure":
        return document, envelope_id
    return document, run_id


def _assert_leaf_probe_rejected(mutation: str) -> None:
    document, vector_id = _leaf_probe_document(mutation)
    with pytest.raises(AssertionError):
        _assert_replay_vector(_vector_by_id(document, vector_id), document)


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


def _module_function(name: str) -> ast.FunctionDef:
    tree = ast.parse(Path(__file__).read_text(encoding="utf-8"))
    return next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == name
    )


def _derivation_compute_functions() -> list[ast.FunctionDef]:
    tree = ast.parse(Path(__file__).read_text(encoding="utf-8"))
    return [
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name.startswith("_compute_")
    ]


FORBIDDEN_COMPUTE_NAMES = frozenset({"declared", "expected", "facts", "observed"})


def _vector_provenance_graph(vector: dict[str, Any]) -> ProvenanceGraph:
    expected = cast(dict[str, Any], _resolved_expected(vector, REPLAY_DOCUMENT))
    projected = {
        cast(str, entry["fact"])
        for pointer in cast(list[dict[str, Any]], vector["source_pointers"])
        for entry in cast(list[dict[str, Any]], pointer["projections"])
    }
    derivations = (
        _assert_derivation_shape(expected) if "derivations" in expected else []
    )
    labels = _assert_authored_labels(expected)
    return _build_provenance_graph(
        cast(str, vector["id"]), projected, derivations, set(labels)
    )


def _graph_depth(graph: ProvenanceGraph) -> int:
    depth: dict[str, int] = {}
    for name in graph.order:
        operands = _operand_facts(graph.derivations[name])
        depth[name] = 1 + max(
            (depth.get(operand, 0) for operand in operands), default=0
        )
    return max(depth.values(), default=0)


SCOPE_BOUNDED_COMPLETENESS_STATUSES = {
    "scope_partial",
    "scope_satisfied",
    "scope_satisfied_with_declared_omissions",
    "scope_unknown",
}


def test_scope_completeness_is_never_a_universal_claim() -> None:
    """Scope satisfaction is bounded to one declared scope.

    `EvidenceCompletenessStatus` is derived only from the outcomes inside one
    explicit scope, so no status value may be promoted into a claim about
    evidence outside that scope. The corpus therefore states no universality
    fact at all rather than inferring one from `scope_satisfied`.
    """

    assert {
        status.value for status in EvidenceCompletenessStatus
    } == SCOPE_BOUNDED_COMPLETENESS_STATUSES
    source = (REPOSITORY_ROOT / "src/faultatlas/domain/evidence.py").read_text(
        encoding="utf-8"
    )
    assert "universal" not in source.lower()
    # Prose may name the boundary; no machine-readable claim may assert it.
    assert not any("universal" in rule for rule in DERIVATION_REGISTRY)
    for vector in _vectors(REPLAY_DOCUMENT):
        expected = cast(dict[str, Any], vector["expected"])
        for entry in cast(list[dict[str, Any]], expected.get("derivations", [])):
            assert "universal" not in cast(str, entry["rule"])
        for name in cast(dict[str, Any], expected.get("facts", {})):
            assert "universal" not in name
        for entry in cast(list[dict[str, Any]], expected.get("authored_labels", [])):
            assert "universal" not in cast(str, entry["label"])
        for pointer in cast(list[dict[str, Any]], vector["source_pointers"]):
            for entry in cast(list[dict[str, Any]], pointer["projections"]):
                assert "universal" not in cast(str, entry["fact"])


def test_derivation_registry_is_complete_and_exercised() -> None:
    used: set[str] = set()
    for vector in _vectors(REPLAY_DOCUMENT):
        expected = cast(dict[str, Any], vector["expected"])
        for entry in cast(list[dict[str, Any]], expected.get("derivations", [])):
            used.add(cast(str, entry["rule"]))
    assert used == DERIVATION_RULES, (
        f"unexercised {sorted(DERIVATION_RULES - used)!r}; "
        f"undeclared {sorted(used - DERIVATION_RULES)!r}"
    )
    assert "authored" not in DERIVATION_REGISTRY
    assert "ordered_component_ids" not in DERIVATION_REGISTRY
    for name, rule in DERIVATION_REGISTRY.items():
        assert rule.compute.__name__ == f"_compute_{name}"
        assert rule.roots <= ROOT_KINDS
        operand_fields = (
            *rule.fact_operands,
            *rule.optional_fact_operands,
            *rule.list_operands,
        )
        # A rule that introduces no independent root of its own may only be a
        # transformation of other verified values, so it must take operands.
        assert rule.roots or operand_fields, name
        assert len(set(operand_fields)) == len(operand_fields)
        assert set(operand_fields).isdisjoint(rule.constants)
        assert PROJECTION_ROOT_KIND not in rule.roots


def test_derivation_evaluator_never_reads_expected_values() -> None:
    functions = _derivation_compute_functions()
    assert {function.name for function in functions} == {
        f"_compute_{rule}" for rule in DERIVATION_RULES
    }
    for function in functions:
        names = {node.id for node in ast.walk(function) if isinstance(node, ast.Name)}
        assert names.isdisjoint(FORBIDDEN_COMPUTE_NAMES), (
            f"{function.name} reads {sorted(names & FORBIDDEN_COMPUTE_NAMES)!r}"
        )
        assert "entry['fact']" not in ast.unparse(function).replace('"', "'")
    provenance = _module_function("_assert_fact_provenance")
    calls = [
        node
        for node in ast.walk(provenance)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "compute"
    ]
    assert len(calls) == 1
    assert [ast.unparse(argument) for argument in calls[0].args] == [
        "entry",
        "verified",
        "context",
    ]


def test_replay_provenance_graphs_are_acyclic_and_rooted() -> None:
    for vector in _vectors(REPLAY_DOCUMENT):
        graph = _vector_provenance_graph(vector)
        assert len(graph.order) == len(graph.derivations)
        for name, kinds in graph.roots.items():
            assert kinds, name
            assert kinds <= ROOT_KINDS, name
        seen: set[str] = set()
        for name in graph.order:
            for operand in _operand_facts(graph.derivations[name]):
                # Topological order guarantees every operand is already
                # verified when its consumer runs.
                assert operand not in graph.derivations or operand in seen
            seen.add(name)
        # A cycle-free graph cannot have a chain longer than its node count.
        assert _graph_depth(graph) <= max(len(graph.derivations), 1)


def test_evidence_classification_is_graph_derived() -> None:
    observed: dict[str, int] = {}
    for vector in _vectors(REPLAY_DOCUMENT):
        graph = _vector_provenance_graph(vector)
        expected = cast(dict[str, Any], _resolved_expected(vector, REPLAY_DOCUMENT))
        labels = _assert_authored_labels(expected)
        pointers = cast(list[dict[str, Any]], vector["source_pointers"])
        computed = _computed_classification(pointers, labels, graph)
        assert vector["evidence_classification"] == computed, vector["id"]
        observed[computed] = observed.get(computed, 0) + 1
    assert set(observed) == EVIDENCE_CLASSIFICATIONS


def _canonical_envelope_order_derivation() -> tuple[
    dict[str, Any], ReplayContext, list[str]
]:
    vector = _vector_by_id(
        REPLAY_DOCUMENT, "evidence.replay.envelope.canonical-current"
    )
    expected = cast(dict[str, Any], _resolved_expected(vector, REPLAY_DOCUMENT))
    entry = next(
        item
        for item in cast(list[dict[str, Any]], expected["derivations"])
        if item["rule"] == "source_ordered_subset"
    )
    pointers = {
        _pointer_key(item): item
        for item in cast(list[dict[str, Any]], vector["source_pointers"])
    }
    path = cast(str, entry["path"])
    document = _parse_canonical_json((REPOSITORY_ROOT / path).read_bytes())
    context = ReplayContext(
        manifest=MANIFEST_DOCUMENT,
        pointers=pointers,
        documents={path: document},
        inventory={},
        outcomes=(),
    )
    facts = cast(dict[str, Any], expected["facts"])
    return entry, context, cast(list[str], facts["publication_subject_order"])


def test_publication_order_follows_bounded_ledger_not_corpus_order() -> None:
    entry, context, locked = _canonical_envelope_order_derivation()
    compute = DERIVATION_REGISTRY["source_ordered_subset"].compute
    derived = cast(list[str], compute(entry, {}, context))
    assert derived == locked
    assert derived != list(reversed(derived))
    swapped = dict(entry)
    swapped["member_json_pointers"] = list(
        reversed(cast(list[str], entry["member_json_pointers"]))
    )
    assert compute(swapped, {}, context) == derived


def test_authored_label_change_leaves_source_provenance_intact() -> None:
    vector = copy.deepcopy(
        _vector_by_id(REPLAY_DOCUMENT, "evidence.replay.publication.acquisition")
    )
    expected = cast(dict[str, Any], vector["expected"])
    before = copy.deepcopy(cast(dict[str, Any], expected["facts"]))
    resolved = _json_text(_resolved_input(vector, REPLAY_DOCUMENT))
    replaced = resolved.replace(PROVIDER_REPOSITORY_ID, ALTERNATE_REPOSITORY_ID)
    assert replaced != resolved
    vector["input"] = json.loads(replaced)
    entry = next(
        item
        for item in cast(list[dict[str, Any]], expected["authored_labels"])
        if item["label"] == "repository_provider_id"
    )
    entry["value"] = ALTERNATE_REPOSITORY_ID
    _assert_replay_vector(vector, REPLAY_DOCUMENT)
    assert cast(dict[str, Any], expected["facts"]) == before


def _mutation_routing_groups() -> list[frozenset[str]]:
    """Extract the mutation names each dispatch branch actually claims.

    Routing correctness must not depend on branch ordering, so the groups are
    read back from this module's own syntax tree and checked for exhaustive,
    pairwise-disjoint coverage of the required mutation set.
    """

    tree = ast.parse(Path(__file__).read_text(encoding="utf-8"))
    function = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef)
        and node.name == "test_required_mutation_is_rejected"
    )
    groups: list[frozenset[str]] = []
    for statement in function.body:
        if isinstance(statement, ast.If):
            # Only branches that terminate the dispatch route a mutation; an
            # inner selector that merely picks a payload does not.
            if not isinstance(statement.body[-1], ast.Return):
                continue
            test = statement.test
        elif isinstance(statement, ast.Assert):
            test = statement.test
        else:
            continue
        if not isinstance(test, ast.Compare) or len(test.ops) != 1:
            continue
        operator = test.ops[0]
        if isinstance(operator, ast.Eq):
            groups.append(frozenset({cast(str, ast.literal_eval(test.comparators[0]))}))
        elif isinstance(operator, ast.In):
            groups.append(
                frozenset(cast(set[str], ast.literal_eval(test.comparators[0])))
            )
    return groups


def test_mutation_routing_is_exhaustive_and_mutually_exclusive() -> None:
    groups = _mutation_routing_groups()
    assert groups
    seen: set[str] = set()
    for group in groups:
        assert group
        overlap = group & seen
        assert not overlap, f"mutation routing groups overlap on {sorted(overlap)!r}"
        seen |= group
    assert seen == set(REQUIRED_MUTATIONS), (
        f"unrouted {sorted(set(REQUIRED_MUTATIONS) - seen)!r}; "
        f"unknown {sorted(seen - set(REQUIRED_MUTATIONS))!r}"
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

    if mutation in {
        "replay-source-pointer-digest-changed",
        "replay-projection-pointer-changed",
        "replay-projection-kind-changed",
        "replay-numeric-fact-changed",
    }:
        vector = copy.deepcopy(
            _vector_by_id(REPLAY_DOCUMENT, "evidence.replay.run.canonical-32-request")
        )
        pointer = cast(list[dict[str, Any]], vector["source_pointers"])[0]
        projections = cast(list[dict[str, Any]], pointer["projections"])
        entry = next(item for item in projections if item["fact"] == "request_count")
        if mutation == "replay-source-pointer-digest-changed":
            pointer["sha256"] = "f" * 64
        elif mutation == "replay-projection-pointer-changed":
            entry["json_pointer"] = "/artifacts"
        elif mutation == "replay-projection-kind-changed":
            entry["kind"] = "value"
        else:
            vector["expected"]["facts"]["request_count"] = 31
        with pytest.raises(AssertionError):
            _assert_replay_vector(vector, REPLAY_DOCUMENT)
        return

    if mutation in {"replay-source-pointer-retargeted", "replay-unclassified-fact"}:
        vector = copy.deepcopy(
            _vector_by_id(REPLAY_DOCUMENT, "evidence.replay.publication.acquisition")
        )
        pointer = next(
            item
            for item in cast(list[dict[str, Any]], vector["source_pointers"])
            if item["path"] == P00_CLOSURE_RELATIVE
        )
        if mutation == "replay-source-pointer-retargeted":
            pointer["path"] = ACQUISITION_RELATIVE
            pointer["sha256"] = _sha256(
                (REPOSITORY_ROOT / ACQUISITION_RELATIVE).read_bytes()
            )
        else:
            projections = cast(list[dict[str, Any]], pointer["projections"])
            projections[:] = [
                entry for entry in projections if entry["fact"] != "published_tree"
            ]
        with pytest.raises(AssertionError):
            _assert_replay_vector(vector, REPLAY_DOCUMENT)
        return

    if mutation == "replay-derivation-list-unsorted":
        vector = copy.deepcopy(
            _vector_by_id(
                REPLAY_DOCUMENT,
                "evidence.replay.completeness.s04-c01-declared-scope",
            )
        )
        cast(list[dict[str, Any]], vector["expected"]["derivations"]).reverse()
        with pytest.raises(AssertionError):
            _assert_replay_vector(vector, REPLAY_DOCUMENT)
        return

    if mutation in {
        "replay-authority-not-registered",
        "replay-authority-path-unregistered",
    }:
        vector = copy.deepcopy(
            _vector_by_id(REPLAY_DOCUMENT, "evidence.replay.publication.acquisition")
        )
        pointer = next(
            item
            for item in cast(list[dict[str, Any]], vector["source_pointers"])
            if item["path"] == P00_CLOSURE_RELATIVE
        )
        if mutation == "replay-authority-not-registered":
            pointer["authority"] = "run-0001-s04-v1-base-4c9cde74-head-690a63b9"
        else:
            pointer["path"] = "reference_corpus/pytest-4412/case/case.json"
            pointer["sha256"] = _sha256(
                (
                    REPOSITORY_ROOT / "reference_corpus/pytest-4412/case/case.json"
                ).read_bytes()
            )
        with pytest.raises(AssertionError):
            _assert_replay_vector(vector, REPLAY_DOCUMENT)
        return

    if mutation in {
        "replay-derivation-recompute-mismatch",
        "replay-derivation-rule-missing",
    }:
        vector = copy.deepcopy(
            _vector_by_id(
                REPLAY_DOCUMENT, "evidence.replay.relationship.s04-c01-correction"
            )
        )
        if mutation == "replay-derivation-recompute-mismatch":
            # Change the replayed record and its expected fact together so the
            # direct fact comparison still agrees and only recomputation from
            # the bounded source rejects the claim.
            record = cast(dict[str, Any], vector["input"]["record"])
            cast(dict[str, Any], record["correction_record"])["byte_length"] = 60831
            vector["expected"]["facts"]["correction_byte_length"] = 60831
        else:
            derivations = cast(list[dict[str, Any]], vector["expected"]["derivations"])
            derivations[:] = [
                entry
                for entry in derivations
                if entry["fact"] != "correction_byte_length"
            ]
        with pytest.raises(AssertionError):
            _assert_replay_vector(vector, REPLAY_DOCUMENT)
        return

    if mutation in {
        "manifest-publication-tree-inequality",
        "manifest-publication-verification-overclaimed",
    }:
        documents = _copied_documents()
        section = cast(
            dict[str, Any], documents["manifest.json"]["originating_publications"]
        )
        if mutation == "manifest-publication-tree-inequality":
            cast(list[dict[str, Any]], section["records"])[0]["squash_tree"] = "a" * 40
        else:
            section["tracked_evidence_available"] = True
        with pytest.raises(AssertionError):
            _assert_manifest_integrity(documents)
        return

    if mutation in {
        "replay-canonical-adapter-empty-provenance",
        "replay-canonical-adapter-coherent-legacy-change",
    }:
        vector = copy.deepcopy(
            _vector_by_id(
                REPLAY_DOCUMENT,
                "evidence.replay.envelope.canonical-current-not-legacy-projectable",
            )
        )
        if mutation == "replay-canonical-adapter-empty-provenance":
            pointers = cast(list[dict[str, Any]], vector["source_pointers"])
            cast(list[Any], pointers[0]["projections"]).clear()
        else:
            # Rewrite the replayed canonical envelope and its expected facts
            # together; only the bounded projection into the acquisition record
            # still disagrees.
            resolved = _resolved_input(vector, REPLAY_DOCUMENT)
            replaced = _json_text(resolved).replace(
                CANONICAL_RUN_ID, "run-0002-synthetic-coherent-change"
            )
            vector["input"] = json.loads(replaced)
            facts = cast(dict[str, Any], vector["expected"]["facts"])
            facts["acquisition_run_ids"] = ["run-0002-synthetic-coherent-change"]
        with pytest.raises(AssertionError):
            _assert_replay_vector(vector, REPLAY_DOCUMENT)
        return

    if mutation == "replay-source-backed-fact-coherent-change":
        vector = copy.deepcopy(
            _vector_by_id(REPLAY_DOCUMENT, "evidence.replay.publication.acquisition")
        )
        facts = cast(dict[str, Any], vector["expected"]["facts"])
        original = cast(str, facts["published_tree"])
        replacement = "a" * 40
        resolved = _json_text(_resolved_input(vector, REPLAY_DOCUMENT))
        vector["input"] = json.loads(resolved.replace(original, replacement))
        facts["published_tree"] = replacement
        facts["reviewed_tree"] = replacement
        with pytest.raises(AssertionError):
            _assert_replay_vector(vector, REPLAY_DOCUMENT)
        return

    if mutation in {
        "replay-authored-label-value-mismatch",
        "replay-authored-label-declaration-removed",
        "replay-authored-label-misclassified-as-source",
        "replay-authored-derivation-rule-reintroduced",
    }:
        vector = copy.deepcopy(
            _vector_by_id(REPLAY_DOCUMENT, "evidence.replay.publication.acquisition")
        )
        expected = cast(dict[str, Any], vector["expected"])
        labels = cast(list[dict[str, Any]], expected["authored_labels"])
        if mutation == "replay-authored-label-value-mismatch":
            entry = next(
                item for item in labels if item["label"] == "repository_provider_id"
            )
            entry["value"] = ALTERNATE_REPOSITORY_ID
        elif mutation == "replay-authored-label-declaration-removed":
            labels[:] = [
                item for item in labels if item["label"] != "repository_provider_id"
            ]
        elif mutation == "replay-authored-label-misclassified-as-source":
            vector["evidence_classification"] = "immutable_source_fact"
        else:
            cast(list[dict[str, Any]], expected["derivations"]).append(
                {
                    "authored_by": "S1.P03.S06",
                    "fact": "publication_id",
                    "rule": "authored",
                }
            )
        with pytest.raises(AssertionError):
            _assert_replay_vector(vector, REPLAY_DOCUMENT)
        return

    if mutation in {
        "replay-canonical-publication-order-reversed",
        "replay-publication-subject-digest-changed",
    }:
        vector = copy.deepcopy(
            _vector_by_id(REPLAY_DOCUMENT, "evidence.replay.envelope.canonical-current")
        )
        resolved = cast(
            dict[str, Any],
            copy.deepcopy(_resolved_input(vector, REPLAY_DOCUMENT)),
        )
        envelope = cast(dict[str, Any], resolved["envelope"])
        publications = cast(list[dict[str, Any]], envelope["publications"])
        facts = cast(dict[str, Any], vector["expected"]["facts"])
        order = cast(list[str], facts["publication_subject_order"])
        if mutation == "replay-canonical-publication-order-reversed":
            # Reverse the components and the expected order together; only the
            # bounded S1.P00 ledger subject order still disagrees.
            publications.reverse()
            order.reverse()
        else:
            subject = cast(dict[str, Any], publications[0]["subject_record"])
            subject["sha256"] = "f" * 64
            order[0] = "f" * 64
        vector["input"] = resolved
        with pytest.raises(AssertionError):
            _assert_replay_vector(vector, REPLAY_DOCUMENT)
        return

    if mutation in {"replay-source-pointer-unused", "replay-duplicate-projected-fact"}:
        vector = copy.deepcopy(
            _vector_by_id(REPLAY_DOCUMENT, "evidence.replay.run.canonical-32-request")
        )
        projections: list[dict[str, Any]] = []
        if mutation == "replay-duplicate-projected-fact":
            projections.append(
                {
                    "fact": "run_id",
                    "json_pointer": "/slice_ledger/items/3/slice_id",
                    "kind": "value",
                }
            )
        pointers = cast(list[dict[str, Any]], vector["source_pointers"])
        pointers.append(
            {
                "authority": P00_CLOSURE_AUTHORITY,
                "path": P00_CLOSURE_RELATIVE,
                "projections": projections,
                "sha256": _sha256(
                    (REPOSITORY_ROOT / P00_CLOSURE_RELATIVE).read_bytes()
                ),
            }
        )
        pointers.sort(key=_pointer_key)
        with pytest.raises(AssertionError):
            _assert_replay_vector(vector, REPLAY_DOCUMENT)
        return

    if mutation in {
        "replay-self-reference-via-product-factor",
        "replay-self-reference-via-difference-minuend",
        "replay-self-reference-via-difference-subtrahend",
        "replay-derivation-two-node-cycle",
        "replay-derivation-unknown-operand",
        "replay-duplicate-derivation-target",
        "replay-projected-derived-name-collision",
        "replay-classification-source-as-composition",
    }:
        vector = copy.deepcopy(
            _vector_by_id(REPLAY_DOCUMENT, "evidence.replay.run.canonical-32-request")
        )
        derivations = cast(list[dict[str, Any]], vector["expected"]["derivations"])
        difference = next(
            entry for entry in derivations if entry["rule"] == "difference"
        )
        product = next(entry for entry in derivations if entry["rule"] == "product")
        if mutation == "replay-self-reference-via-product-factor":
            # The exact operand-aliasing shape reported against `ea57186`.
            product["factor_fact"] = "unrepresented_component_count"
            product["multiplier"] = 1
        elif mutation == "replay-self-reference-via-difference-minuend":
            difference["minuend_fact"] = "known_empty_membership_count"
        elif mutation == "replay-self-reference-via-difference-subtrahend":
            difference["subtrahend_length_fact"] = "known_empty_membership_count"
        elif mutation == "replay-derivation-two-node-cycle":
            difference["minuend_fact"] = "unrepresented_component_count"
            product["factor_fact"] = "known_empty_membership_count"
        elif mutation == "replay-derivation-unknown-operand":
            product["factor_fact"] = "no_such_fact"
        elif mutation == "replay-duplicate-derivation-target":
            derivations.append(copy.deepcopy(product))
        elif mutation == "replay-projected-derived-name-collision":
            derivations.insert(
                1,
                {
                    "fact": "request_count",
                    "factor_fact": "known_empty_membership_count",
                    "multiplier": 1,
                    "rule": "product",
                },
            )
        else:
            vector["evidence_classification"] = "reviewed_derived_composition"
        with pytest.raises(AssertionError):
            _assert_replay_vector(vector, REPLAY_DOCUMENT)
        return

    if mutation in {
        "replay-self-reference-via-sum-addend",
        "replay-derivation-authored-label-operand",
    }:
        vector = copy.deepcopy(
            _vector_by_id(
                REPLAY_DOCUMENT,
                "evidence.replay.completeness.s04-c01-declared-scope",
            )
        )
        derivations = cast(list[dict[str, Any]], vector["expected"]["derivations"])
        total = next(
            entry for entry in derivations if entry["fact"] == "requirement_count"
        )
        if mutation == "replay-self-reference-via-sum-addend":
            total["addend_facts"] = ["requirement_count"]
        else:
            total["addend_facts"] = [
                "intentionally_omitted_count",
                "satisfied_requirements",
            ]
        with pytest.raises(AssertionError):
            _assert_replay_vector(vector, REPLAY_DOCUMENT)
        return

    if mutation in {
        "replay-self-reference-via-component-minus",
        "replay-classification-composition-as-source",
        "replay-derivation-three-node-cycle",
        "replay-envelope-nested-record-drift",
    }:
        vector = copy.deepcopy(
            _vector_by_id(REPLAY_DOCUMENT, "evidence.replay.envelope.canonical-current")
        )
        expected = cast(dict[str, Any], vector["expected"])
        derivations = cast(list[dict[str, Any]], expected["derivations"])
        if mutation == "replay-self-reference-via-component-minus":
            entry = next(
                item
                for item in derivations
                if item["fact"] == "canonical_supersession_count"
            )
            entry["minus_fact"] = "canonical_supersession_count"
        elif mutation == "replay-classification-composition-as-source":
            vector["evidence_classification"] = "immutable_source_fact"
        elif mutation == "replay-derivation-three-node-cycle":
            chain = (
                ("canonical_correction_count", "canonical_supersession_count"),
                ("canonical_supersession_count", "canonical_transformation_count"),
                ("canonical_transformation_count", "canonical_correction_count"),
            )
            for target, operand in chain:
                entry = next(item for item in derivations if item["fact"] == target)
                entry.clear()
                entry.update(
                    {
                        "fact": target,
                        "factor_fact": operand,
                        "multiplier": 1,
                        "rule": "product",
                    }
                )
        elif mutation == "replay-envelope-nested-record-drift":
            # Every locked composition fact still agrees; only the nested
            # record's own source-backed replay disagrees.
            resolved = cast(
                dict[str, Any],
                copy.deepcopy(_resolved_input(vector, REPLAY_DOCUMENT)),
            )
            envelope = cast(dict[str, Any], resolved["envelope"])
            relationship = cast(list[dict[str, Any]], envelope["record_relationships"])[
                0
            ]
            relationship["recorded_at"] = "2026-07-30T19:17:09.655781Z"
            vector["input"] = resolved
        else:
            resolved = cast(
                dict[str, Any],
                copy.deepcopy(_resolved_input(vector, REPLAY_DOCUMENT)),
            )
            envelope = cast(dict[str, Any], resolved["envelope"])
            relationship = cast(list[dict[str, Any]], envelope["record_relationships"])[
                0
            ]
            relationship["recorded_at"] = "2026-07-30T19:17:09.655781Z"
            vector["input"] = resolved
        with pytest.raises(AssertionError):
            _assert_replay_vector(vector, REPLAY_DOCUMENT)
        return

    if mutation == "replay-artifact-scope-coherent-drift":
        vector = copy.deepcopy(
            _vector_by_id(REPLAY_DOCUMENT, "evidence.replay.artifact.compare-diff")
        )
        drifted = "s08-authored-scope-with-no-source-evidence"
        identity = cast(dict[str, Any], vector["input"]["artifact_identity"])
        cast(dict[str, Any], identity["digest"])["scope"] = drifted
        cast(dict[str, Any], vector["expected"]["facts"])["digest_scope"] = drifted
        with pytest.raises(AssertionError):
            _assert_replay_vector(vector, REPLAY_DOCUMENT)
        return

    if mutation == "replay-classification-synthetic-as-source":
        vector = copy.deepcopy(
            _vector_by_id(
                REPLAY_DOCUMENT,
                "evidence.replay.legacy-adapter.project-legacy-absent",
            )
        )
        vector["evidence_classification"] = "immutable_source_fact"
        with pytest.raises(AssertionError):
            _assert_replay_vector(vector, REPLAY_DOCUMENT)
        return

    if mutation in {
        "leaf-authored-value-drift",
        "leaf-child-binding-mismatched",
        "leaf-child-dependency-cycle",
        "leaf-child-replay-failure",
        "leaf-child-self-dependency",
        "leaf-compare-diff-byte-length-drift",
        "leaf-compare-diff-digest-drift",
        "leaf-completeness-drift",
        "leaf-contract-literal-multivalued",
        "leaf-correction-drift",
        "leaf-license-byte-length-drift",
        "leaf-license-digest-drift",
        "leaf-proof-primary-overlap",
        "leaf-proof-rule-matches-nothing",
        "leaf-proof-rule-removed",
        "leaf-publication-check-drift",
        "leaf-run-timestamp-drift",
        "leaf-sequence-reordered",
        "leaf-source-pointer-retargeted",
        "leaf-synthetic-child-binding",
    }:
        _assert_leaf_probe_rejected(mutation)
        return

    if mutation == "replay-decision-reference-unregistered":
        documents = _copied_documents()
        vectors = _vectors(documents["valid-vectors.json"])
        cast(list[str], vectors[0]["decision_references"]).append(
            "decision:s99:unregistered"
        )
        with pytest.raises(AssertionError):
            _assert_vector_structure(documents)
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
        shutil.copytree(CORPUS_ROOT.parent / "closures", contract_root / "closures")
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

    assert mutation in {
        "synthetic-package-corpus-member",
        "historical-pytest-license-inserted",
    }
    project_license = (REPOSITORY_ROOT / "LICENSE").read_bytes()
    historical_license = (REPOSITORY_ROOT / LICENSE_RELATIVE).read_bytes()
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
