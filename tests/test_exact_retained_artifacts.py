from __future__ import annotations

import ast
import json
import stat
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from hashlib import sha1, sha256
from pathlib import Path
from typing import Any, cast

import pytest
from pydantic import TypeAdapter, ValidationError

import faultatlas
import faultatlas.domain as domain_package
import faultatlas.domain.evidence as evidence_module
from faultatlas.domain.evidence import (
    AcquisitionRunId,
    ArtifactByteLength,
    ArtifactDigest,
    ArtifactDigestAlgorithm,
    ArtifactDigestScope,
    ArtifactRetentionMode,
    ArtifactSha256Digest,
    ExactArtifactIdentity,
    ExactRetainedArtifact,
    HttpStatusCode,
    MediaType,
    ResponseRepresentationObservation,
    ResponseRepresentationState,
    RetrievalMethod,
    RetrievalRequestId,
    RetrievalRequestOrdinal,
    RetrievalRequestReference,
    RetrievalRoutePath,
)
from faultatlas.domain.identity import AuthorityRole, ProviderAuthority, ProviderKey
from faultatlas.domain.source import ArtifactSnapshot

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_SOURCE = REPOSITORY_ROOT / "src/faultatlas/domain/evidence.py"
SOURCE_SOURCE = REPOSITORY_ROOT / "src/faultatlas/domain/source.py"
ACQUISITION_ROOT = (
    REPOSITORY_ROOT
    / "reference_corpus"
    / "pytest-4412"
    / "acquisitions"
    / "run-0001-s04-v1-base-4c9cde74-head-690a63b9"
)
ACQUISITION_PATH = ACQUISITION_ROOT / "acquisition.json"
CANONICAL_RUN_ID = "run-0001-s04-v1-base-4c9cde74-head-690a63b9"
DIFF_DIGEST = "dca87a4df1edb2d1acb3fc821724483ee874c2feba6525b2c21e79cb3e8f7312"
LICENSE_DIGEST = "a1ebce15afc7b5cf98c7c6de512d1959d4bf61db8c6bf2f111286d483b40a997"
EMPTY_DIGEST = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
MAX_BYTE_LENGTH = 9_223_372_036_854_775_807
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
    "src/faultatlas/domain/snapshot.py",
    "src/faultatlas/domain/source.py",
}
FORBIDDEN_ARTIFACT_FIELDS = (
    "acquisition_run",
    "base64",
    "bucket",
    "completeness",
    "content_encoding",
    "correction",
    "database_id",
    "git_blob_identity",
    "media_type",
    "omission",
    "path",
    "payload_bytes",
    "payload_text",
    "publication",
    "publication_provenance",
    "reader",
    "repository_path",
    "response_observation",
    "retained_at",
    "revision",
    "source",
    "storage_backend",
    "storage_locator",
    "supersession",
    "text_encoding",
    "transformation",
    "uri",
    "writer",
)


@dataclass(frozen=True)
class ArtifactCase:
    filename: str
    acquisition_path: str
    request_ordinal: int
    byte_length: int
    digest_scope: str
    digest_value: str


DIFF_CASE = ArtifactCase(
    filename="base-to-head.diff",
    acquisition_path="artifacts/base-to-head.diff",
    request_ordinal=30,
    byte_length=1640,
    digest_scope="github-compare-diff-http-entity-body",
    digest_value=DIFF_DIGEST,
)
LICENSE_CASE = ArtifactCase(
    filename="LICENSE",
    acquisition_path="artifacts/LICENSE",
    request_ordinal=32,
    byte_length=1096,
    digest_scope="git-blob-content",
    digest_value=LICENSE_DIGEST,
)
CANONICAL_CASES = (DIFF_CASE, LICENSE_CASE)


def _request_id(ordinal: int) -> RetrievalRequestId:
    return RetrievalRequestId(
        acquisition_run_id=AcquisitionRunId.model_validate(CANONICAL_RUN_ID),
        request_ordinal=RetrievalRequestOrdinal.model_validate(ordinal),
    )


def _artifact_digest(
    *,
    scope: str = DIFF_CASE.digest_scope,
    value: str = DIFF_CASE.digest_value,
) -> ArtifactDigest:
    return ArtifactDigest(
        algorithm=ArtifactDigestAlgorithm.SHA256,
        scope=ArtifactDigestScope.model_validate(scope),
        value=ArtifactSha256Digest.model_validate(value),
    )


def _artifact_identity(
    *,
    scope: str = DIFF_CASE.digest_scope,
    value: str = DIFF_CASE.digest_value,
    byte_length: int = DIFF_CASE.byte_length,
) -> ExactArtifactIdentity:
    return ExactArtifactIdentity(
        digest=_artifact_digest(scope=scope, value=value),
        byte_length=ArtifactByteLength.model_validate(byte_length),
    )


def _retained_artifact(
    *,
    ordinal: int = DIFF_CASE.request_ordinal,
    identity: ExactArtifactIdentity | None = None,
) -> ExactRetainedArtifact:
    return ExactRetainedArtifact(
        request_id=_request_id(ordinal),
        artifact_identity=identity or _artifact_identity(),
        retention_mode=ArtifactRetentionMode.EXACT_UNMODIFIED_BYTES,
    )


def _load_acquisition() -> dict[str, Any]:
    loaded = json.loads(ACQUISITION_PATH.read_bytes())
    assert isinstance(loaded, dict)
    return cast(dict[str, Any], loaded)


def _assure_canonical_artifact(
    case: ArtifactCase,
    *,
    artifact_path: Path | None = None,
) -> ExactRetainedArtifact:
    acquisition = _load_acquisition()
    artifacts = cast(list[dict[str, object]], acquisition["artifacts"])
    matching = [item for item in artifacts if item["path"] == case.acquisition_path]
    assert len(matching) == 1
    retained = matching[0]
    assert retained["request_ordinal"] == case.request_ordinal
    assert retained["byte_length"] == case.byte_length
    assert retained["digest_scope"] == case.digest_scope
    assert retained["sha256"] == case.digest_value
    assert retained["retention"] == "exact_unmodified_bytes"

    path = artifact_path or ACQUISITION_ROOT / "artifacts" / case.filename
    assert path.exists()
    assert not path.is_symlink()
    path_stat = path.stat()
    assert stat.S_ISREG(path_stat.st_mode)
    assert len(path.read_bytes()) == case.byte_length
    assert sha256(path.read_bytes()).hexdigest() == case.digest_value

    artifact_identity = _artifact_identity(
        scope=case.digest_scope,
        value=case.digest_value,
        byte_length=case.byte_length,
    )
    record = _retained_artifact(
        ordinal=case.request_ordinal,
        identity=artifact_identity,
    )
    assert ExactRetainedArtifact.model_validate_json(record.model_dump_json()) == record
    return record


def _model_payload(model: object) -> dict[str, object]:
    dumped = cast(Any, model).model_dump(mode="python")
    assert isinstance(dumped, dict)
    return cast(dict[str, object], dumped)


def test_artifact_digest_algorithm_is_exact_typed_and_json_reconstructible() -> None:
    adapter = TypeAdapter(ArtifactDigestAlgorithm)
    algorithm = ArtifactDigestAlgorithm.SHA256
    assert tuple(ArtifactDigestAlgorithm) == (algorithm,)
    assert algorithm.value == "sha256"
    assert adapter.validate_python(algorithm, strict=True) is algorithm
    assert adapter.validate_json('"sha256"', strict=True) is algorithm
    assert adapter.dump_json(algorithm) == b'"sha256"'


@pytest.mark.parametrize(
    "value",
    ("SHA256", "sha-256", "sha1", "unknown", 256, None),
)
def test_artifact_digest_algorithm_rejects_unknown_or_coerced_values(
    value: object,
) -> None:
    adapter = TypeAdapter(ArtifactDigestAlgorithm)
    with pytest.raises(ValidationError):
        adapter.validate_python(value, strict=True)


@pytest.mark.parametrize(
    "value",
    (
        "a",
        "a1",
        "synthetic-http-entity-body",
        "github-compare-diff-http-entity-body",
        "git-blob-content",
        "a" * 128,
    ),
)
def test_artifact_digest_scope_preserves_valid_exact_lexemes(value: str) -> None:
    scope = ArtifactDigestScope.model_validate(value)
    assert scope.root == value
    assert scope.model_dump_json() == json.dumps(value, separators=(",", ":"))
    assert ArtifactDigestScope.model_validate_json(scope.model_dump_json()) == scope


@pytest.mark.parametrize(
    "value",
    (
        "",
        "A",
        "Git-blob-content",
        "-scope",
        "scope-",
        "two scopes",
        "two\tscopes",
        "two\nscopes",
        "two\x00scopes",
        "scope/name",
        "scope\\name",
        "scope:name",
        "scope.name",
        "scope_name",
        "https://example.test/path",
        "é",
        "a" * 129,
        1,
        b"git-blob-content",
        None,
    ),
)
def test_artifact_digest_scope_rejects_malformed_or_coerced_values(
    value: object,
) -> None:
    with pytest.raises(ValidationError):
        ArtifactDigestScope.model_validate(value)


def test_artifact_digest_scope_is_frozen() -> None:
    scope = ArtifactDigestScope.model_validate("git-blob-content")
    with pytest.raises(ValidationError):
        setattr(scope, "root", "other-scope")


@pytest.mark.parametrize("value", (DIFF_DIGEST, LICENSE_DIGEST, EMPTY_DIGEST))
def test_artifact_sha256_digest_preserves_valid_exact_lexemes(value: str) -> None:
    digest = ArtifactSha256Digest.model_validate(value)
    assert digest.root == value
    assert ArtifactSha256Digest.model_validate_json(digest.model_dump_json()) == digest


@pytest.mark.parametrize(
    "value",
    (
        DIFF_DIGEST.upper(),
        "a" * 63,
        "a" * 65,
        "g" * 64,
        f"sha256:{DIFF_DIGEST}",
        f" {DIFF_DIGEST}",
        f"{DIFF_DIGEST} ",
        f"{DIFF_DIGEST[:32]}-{DIFF_DIGEST[32:]}",
        "0" * 64,
        DIFF_DIGEST.encode(),
        123,
        None,
    ),
)
def test_artifact_sha256_digest_rejects_malformed_or_coerced_values(
    value: object,
) -> None:
    with pytest.raises(ValidationError):
        ArtifactSha256Digest.model_validate(value)


@pytest.mark.parametrize("value", (0, 1096, 1640, MAX_BYTE_LENGTH))
def test_artifact_byte_length_accepts_exact_bounded_integers(value: int) -> None:
    length = ArtifactByteLength.model_validate(value)
    assert length.root == value
    assert ArtifactByteLength.model_validate_json(length.model_dump_json()) == length


@pytest.mark.parametrize(
    "value",
    (-1, MAX_BYTE_LENGTH + 1, True, False, 1.0, "1640", None),
)
def test_artifact_byte_length_rejects_out_of_range_or_coerced_values(
    value: object,
) -> None:
    with pytest.raises(ValidationError):
        ArtifactByteLength.model_validate(value)


def test_artifact_digest_has_exact_fields_equality_and_semantic_json() -> None:
    diff = _artifact_digest()
    same = _artifact_digest()
    other_scope = _artifact_digest(scope="git-blob-content")
    assert tuple(ArtifactDigest.model_fields) == (
        "schema_version",
        "algorithm",
        "scope",
        "value",
    )
    assert diff == same
    assert diff != other_scope
    assert ArtifactDigest.model_validate_json(diff.model_dump_json()) == diff
    assert diff.model_dump(mode="json") == {
        "schema_version": 1,
        "algorithm": "sha256",
        "scope": DIFF_CASE.digest_scope,
        "value": DIFF_CASE.digest_value,
    }


@pytest.mark.parametrize("field", ("algorithm", "scope", "value"))
def test_artifact_digest_rejects_missing_required_fields(field: str) -> None:
    payload = _model_payload(_artifact_digest())
    payload.pop(field)
    with pytest.raises(ValidationError):
        ArtifactDigest.model_validate(payload)


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("algorithm", "sha256"),
        ("scope", DIFF_CASE.digest_scope),
        ("value", DIFF_CASE.digest_value),
    ),
)
def test_artifact_digest_requires_typed_nested_python_input(
    field: str,
    value: object,
) -> None:
    payload: dict[str, object] = {
        "algorithm": ArtifactDigestAlgorithm.SHA256,
        "scope": ArtifactDigestScope.model_validate(DIFF_CASE.digest_scope),
        "value": ArtifactSha256Digest.model_validate(DIFF_CASE.digest_value),
    }
    payload[field] = value
    with pytest.raises(ValidationError):
        ArtifactDigest.model_validate(payload)


@pytest.mark.parametrize(
    "field",
    ("media_type", "path", "request_id", "sha256_algorithm_inferred"),
)
def test_artifact_digest_rejects_inference_and_extra_context(field: str) -> None:
    payload = _model_payload(_artifact_digest())
    payload[field] = "not-part-of-digest"
    with pytest.raises(ValidationError):
        ArtifactDigest.model_validate(payload)


def test_artifact_digest_never_infers_algorithm_or_scope() -> None:
    with pytest.raises(ValidationError):
        ArtifactDigest.model_validate(
            {
                "scope": ArtifactDigestScope.model_validate(DIFF_CASE.digest_scope),
                "value": ArtifactSha256Digest.model_validate(DIFF_CASE.digest_value),
            }
        )
    with pytest.raises(ValidationError):
        ArtifactDigest.model_validate(
            {
                "algorithm": ArtifactDigestAlgorithm.SHA256,
                "value": ArtifactSha256Digest.model_validate(DIFF_CASE.digest_value),
                "media_type": "application/vnd.github.diff",
                "request_id": _request_id(30),
            }
        )


@pytest.mark.parametrize("schema_version", (0, 2, True, "1", 1.0, None))
def test_artifact_models_reject_nonexact_schema_versions(
    schema_version: object,
) -> None:
    for model_type, model in (
        (ArtifactDigest, _artifact_digest()),
        (ExactArtifactIdentity, _artifact_identity()),
        (ExactRetainedArtifact, _retained_artifact()),
    ):
        payload = _model_payload(model)
        payload["schema_version"] = schema_version
        with pytest.raises(ValidationError):
            model_type.model_validate(payload)


def test_exact_artifact_identity_has_exact_fields_and_semantic_json() -> None:
    identity = _artifact_identity()
    assert tuple(ExactArtifactIdentity.model_fields) == (
        "schema_version",
        "digest",
        "byte_length",
    )
    assert (
        ExactArtifactIdentity.model_validate_json(identity.model_dump_json())
        == identity
    )
    assert identity.model_dump(mode="json") == {
        "schema_version": 1,
        "digest": {
            "schema_version": 1,
            "algorithm": "sha256",
            "scope": DIFF_CASE.digest_scope,
            "value": DIFF_CASE.digest_value,
        },
        "byte_length": DIFF_CASE.byte_length,
    }


@pytest.mark.parametrize("field", ("digest", "byte_length"))
def test_exact_artifact_identity_rejects_missing_fields(field: str) -> None:
    payload = _model_payload(_artifact_identity())
    payload.pop(field)
    with pytest.raises(ValidationError):
        ExactArtifactIdentity.model_validate(payload)


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("digest", {"algorithm": "sha256"}),
        ("byte_length", 1640),
    ),
)
def test_exact_artifact_identity_requires_typed_nested_python_input(
    field: str,
    value: object,
) -> None:
    payload: dict[str, object] = {
        "digest": _artifact_digest(),
        "byte_length": ArtifactByteLength.model_validate(1640),
    }
    payload[field] = value
    with pytest.raises(ValidationError):
        ExactArtifactIdentity.model_validate(payload)


@pytest.mark.parametrize(
    "field",
    (
        "request_id",
        "media_type",
        "path",
        "source",
        "revision",
        "payload_bytes",
        "retention_mode",
        "transformation",
    ),
)
def test_exact_artifact_identity_rejects_nonidentity_fields(field: str) -> None:
    payload = _model_payload(_artifact_identity())
    payload[field] = "forbidden"
    with pytest.raises(ValidationError):
        ExactArtifactIdentity.model_validate(payload)


def test_artifact_retention_mode_is_exact_typed_and_json_reconstructible() -> None:
    adapter = TypeAdapter(ArtifactRetentionMode)
    mode = ArtifactRetentionMode.EXACT_UNMODIFIED_BYTES
    assert tuple(ArtifactRetentionMode) == (mode,)
    assert mode.value == "exact_unmodified_bytes"
    assert adapter.validate_python(mode, strict=True) is mode
    assert adapter.validate_json('"exact_unmodified_bytes"', strict=True) is mode


@pytest.mark.parametrize(
    "value",
    (
        "normalized",
        "decoded",
        "decompressed",
        "transformed",
        "redacted",
        "truncated",
        "canonicalized",
        "EXACT_UNMODIFIED_BYTES",
        None,
    ),
)
def test_artifact_retention_mode_rejects_every_other_value(value: object) -> None:
    adapter = TypeAdapter(ArtifactRetentionMode)
    with pytest.raises(ValidationError):
        adapter.validate_python(value, strict=True)


def test_exact_retained_artifact_has_exact_fields_and_semantic_json() -> None:
    record = _retained_artifact()
    assert tuple(ExactRetainedArtifact.model_fields) == (
        "schema_version",
        "request_id",
        "artifact_identity",
        "retention_mode",
    )
    assert record.request_id == _request_id(30)
    assert record.artifact_identity == _artifact_identity()
    assert record.retention_mode is ArtifactRetentionMode.EXACT_UNMODIFIED_BYTES
    assert ExactRetainedArtifact.model_validate_json(record.model_dump_json()) == record


@pytest.mark.parametrize(
    "field",
    ("request_id", "artifact_identity", "retention_mode"),
)
def test_exact_retained_artifact_rejects_missing_fields(field: str) -> None:
    payload = _model_payload(_retained_artifact())
    payload.pop(field)
    with pytest.raises(ValidationError):
        ExactRetainedArtifact.model_validate(payload)


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("request_id", {"request_ordinal": 30}),
        ("artifact_identity", {"byte_length": 1640}),
        ("retention_mode", "exact_unmodified_bytes"),
    ),
)
def test_exact_retained_artifact_requires_typed_nested_python_input(
    field: str,
    value: object,
) -> None:
    payload: dict[str, object] = {
        "request_id": _request_id(30),
        "artifact_identity": _artifact_identity(),
        "retention_mode": ArtifactRetentionMode.EXACT_UNMODIFIED_BYTES,
    }
    payload[field] = value
    with pytest.raises(ValidationError):
        ExactRetainedArtifact.model_validate(payload)


@pytest.mark.parametrize("field", FORBIDDEN_ARTIFACT_FIELDS)
def test_exact_retained_artifact_rejects_every_later_or_merged_field(
    field: str,
) -> None:
    payload = _model_payload(_retained_artifact())
    payload[field] = "forbidden"
    with pytest.raises(ValidationError):
        ExactRetainedArtifact.model_validate(payload)


def test_artifact_and_retained_records_are_frozen() -> None:
    digest = _artifact_digest()
    identity = _artifact_identity()
    record = _retained_artifact()
    for model, field, replacement_value in (
        (digest, "scope", ArtifactDigestScope.model_validate("git-blob-content")),
        (identity, "byte_length", ArtifactByteLength.model_validate(1)),
        (record, "request_id", _request_id(31)),
    ):
        with pytest.raises(ValidationError):
            setattr(model, field, replacement_value)


def test_nested_constructed_invalid_instances_are_revalidated() -> None:
    invalid_scope = ArtifactDigestScope.model_construct(root="UPPERCASE")
    with pytest.raises(ValidationError):
        ArtifactDigest(
            algorithm=ArtifactDigestAlgorithm.SHA256,
            scope=invalid_scope,
            value=ArtifactSha256Digest.model_validate(DIFF_DIGEST),
        )

    invalid_value = ArtifactSha256Digest.model_construct(root="0" * 64)
    invalid_digest = ArtifactDigest.model_construct(
        schema_version=1,
        algorithm=ArtifactDigestAlgorithm.SHA256,
        scope=ArtifactDigestScope.model_validate(DIFF_CASE.digest_scope),
        value=invalid_value,
    )
    with pytest.raises(ValidationError):
        ExactArtifactIdentity(
            digest=invalid_digest,
            byte_length=ArtifactByteLength.model_validate(1640),
        )

    invalid_identity = ExactArtifactIdentity.model_construct(
        schema_version=1,
        digest=_artifact_digest(),
        byte_length=ArtifactByteLength.model_construct(root=-1),
    )
    with pytest.raises(ValidationError):
        ExactRetainedArtifact(
            request_id=_request_id(30),
            artifact_identity=invalid_identity,
            retention_mode=ArtifactRetentionMode.EXACT_UNMODIFIED_BYTES,
        )


def test_artifact_identity_and_request_linkage_equality_boundaries() -> None:
    identity = _artifact_identity()
    other_scope = _artifact_identity(scope="git-blob-content")
    other_digest = _artifact_identity(value=LICENSE_DIGEST)
    other_length = _artifact_identity(byte_length=1641)
    assert identity != other_scope
    assert identity.digest != other_scope.digest
    assert identity != other_digest
    assert identity != other_length

    first_request = _retained_artifact(ordinal=30, identity=identity)
    second_request = _retained_artifact(ordinal=31, identity=identity)
    assert first_request.artifact_identity == second_request.artifact_identity
    assert first_request != second_request

    same_request_other_artifact = _retained_artifact(
        ordinal=30,
        identity=other_digest,
    )
    assert first_request.request_id == same_request_other_artifact.request_id
    assert first_request != same_request_other_artifact
    assert first_request == _retained_artifact(ordinal=30, identity=identity)


def test_synthetic_request_metadata_changes_do_not_change_artifact_identity() -> None:
    request_id = RetrievalRequestId(
        acquisition_run_id=AcquisitionRunId.model_validate(
            "run-synthetic-artifact-link"
        ),
        request_ordinal=RetrievalRequestOrdinal.model_validate(1),
    )
    authority = ProviderAuthority(
        provider=ProviderKey.model_validate("github"),
        role=AuthorityRole.RETRIEVAL,
        host="api.github.com",
    )
    first = RetrievalRequestReference(
        request_id=request_id,
        authority=authority,
        method=RetrievalMethod.GET,
        route_path=RetrievalRoutePath.model_validate("/synthetic/first"),
        started_at=datetime(2026, 8, 2, 15, 0, tzinfo=UTC),
    )
    second = RetrievalRequestReference(
        request_id=request_id,
        authority=authority,
        method=RetrievalMethod.POST,
        route_path=RetrievalRoutePath.model_validate("/synthetic/second"),
        started_at=datetime(2026, 8, 2, 15, 1, tzinfo=UTC),
    )
    identity = _artifact_identity()
    assert first != second
    assert _retained_artifact(identity=identity).artifact_identity == identity
    assert not {
        "authority",
        "method",
        "route_path",
        "started_at",
    } & set(ExactArtifactIdentity.model_fields)


def test_response_media_changes_do_not_change_artifact_identity() -> None:
    request_id = _request_id(30)
    first = ResponseRepresentationObservation(
        request_id=request_id,
        state=ResponseRepresentationState.OBSERVED,
        completed_at=datetime(2026, 8, 2, 16, 0, tzinfo=UTC),
        status_code=HttpStatusCode.model_validate(200),
        observed_media_type=MediaType.model_validate("application/vnd.github.diff"),
        media_type_parameters=(),
        content_encodings=(),
    )
    second = ResponseRepresentationObservation(
        request_id=request_id,
        state=ResponseRepresentationState.OBSERVED,
        completed_at=datetime(2026, 8, 2, 16, 0, tzinfo=UTC),
        status_code=HttpStatusCode.model_validate(200),
        observed_media_type=MediaType.model_validate("application/octet-stream"),
        media_type_parameters=(),
        content_encodings=(),
    )
    identity = _artifact_identity()
    assert first != second
    assert _retained_artifact(identity=identity).artifact_identity == identity
    response_specific_fields = set(ResponseRepresentationObservation.model_fields) - {
        "schema_version"
    }
    assert not response_specific_fields & set(ExactArtifactIdentity.model_fields)


def test_empty_arbitrary_byte_artifact_is_valid_metadata_only() -> None:
    identity = _artifact_identity(
        scope="synthetic-http-entity-body",
        value=EMPTY_DIGEST,
        byte_length=0,
    )
    record = _retained_artifact(ordinal=1, identity=identity)
    assert sha256(b"").hexdigest() == EMPTY_DIGEST
    assert identity.byte_length.root == 0
    assert record.artifact_identity == identity
    dumped = record.model_dump(mode="json")
    assert not any(field in dumped for field in FORBIDDEN_ARTIFACT_FIELDS)


@pytest.mark.parametrize("case", CANONICAL_CASES, ids=("diff", "license"))
def test_canonical_exact_artifact_bytes_replay_and_build_records(
    case: ArtifactCase,
) -> None:
    acquisition_raw = ACQUISITION_PATH.read_bytes()
    assert len(acquisition_raw) == 61_283
    assert sha256(acquisition_raw).hexdigest() == (
        "1c29093bf1537e9b824a18df1848b71a8da014f544bc9f385707eb0e000a1318"
    )
    record = _assure_canonical_artifact(case)
    assert record.request_id == _request_id(case.request_ordinal)
    assert record.artifact_identity.digest.scope.root == case.digest_scope
    assert record.artifact_identity.byte_length.root == case.byte_length


def test_license_git_blob_identity_is_independent_from_artifact_model() -> None:
    raw = (ACQUISITION_ROOT / "artifacts/LICENSE").read_bytes()
    framed = f"blob {len(raw)}\0".encode() + raw
    assert sha256(raw).hexdigest() == LICENSE_DIGEST
    assert sha1(framed, usedforsecurity=False).hexdigest() == (
        "629df45ac405532c107eb233217bc2ac1ad70c88"
    )
    fields = set(ExactArtifactIdentity.model_fields) | set(
        ExactRetainedArtifact.model_fields
    )
    assert not {"git_blob_sha1", "git_blob_identity", "git_object_kind"} & fields


@pytest.mark.parametrize(
    "mutation",
    (
        "byte-length",
        "digest",
        "scope",
        "request-ordinal",
        "swapped-diff-file",
        "swapped-license-file",
    ),
)
def test_canonical_assurance_metadata_and_swap_mutations_fail(mutation: str) -> None:
    if mutation == "byte-length":
        case = replace(DIFF_CASE, byte_length=DIFF_CASE.byte_length + 1)
        path = None
    elif mutation == "digest":
        case = replace(DIFF_CASE, digest_value=LICENSE_DIGEST)
        path = None
    elif mutation == "scope":
        case = replace(DIFF_CASE, digest_scope=LICENSE_CASE.digest_scope)
        path = None
    elif mutation == "request-ordinal":
        case = replace(DIFF_CASE, request_ordinal=LICENSE_CASE.request_ordinal)
        path = None
    elif mutation == "swapped-diff-file":
        case = DIFF_CASE
        path = ACQUISITION_ROOT / "artifacts" / LICENSE_CASE.filename
    else:
        case = LICENSE_CASE
        path = ACQUISITION_ROOT / "artifacts" / DIFF_CASE.filename
    with pytest.raises(AssertionError):
        _assure_canonical_artifact(case, artifact_path=path)


@pytest.mark.parametrize("case", CANONICAL_CASES, ids=("diff", "license"))
def test_changed_temporary_artifact_bytes_fail_independent_assurance(
    case: ArtifactCase,
    tmp_path: Path,
) -> None:
    original = (ACQUISITION_ROOT / "artifacts" / case.filename).read_bytes()
    changed = bytearray(original)
    changed[0] ^= 1
    temporary = tmp_path / case.filename
    temporary.write_bytes(changed)
    with pytest.raises(AssertionError):
        _assure_canonical_artifact(case, artifact_path=temporary)


def test_artifact_models_exclude_response_source_storage_payload_and_later_fields() -> (
    None
):
    fields = {
        *ArtifactDigest.model_fields,
        *ExactArtifactIdentity.model_fields,
        *ExactRetainedArtifact.model_fields,
    }
    assert not set(FORBIDDEN_ARTIFACT_FIELDS) & fields
    assert fields == {
        "schema_version",
        "algorithm",
        "scope",
        "value",
        "digest",
        "byte_length",
        "request_id",
        "artifact_identity",
        "retention_mode",
    }


def test_evidence_exports_roots_inventory_and_s08_boundary_are_exact() -> None:
    assert tuple(evidence_module.__all__) == EXPECTED_EVIDENCE_EXPORTS
    assert len(evidence_module.__all__) == len(set(evidence_module.__all__)) == 58
    assert faultatlas.__all__ == ["__version__"]
    assert getattr(domain_package, "__all__", None) in (None, [])
    assert not set(EXPECTED_EVIDENCE_EXPORTS) & set(vars(faultatlas))
    assert not set(EXPECTED_EVIDENCE_EXPORTS) & set(vars(domain_package))

    production_files = {
        path.relative_to(REPOSITORY_ROOT).as_posix()
        for path in (REPOSITORY_ROOT / "src").rglob("*.py")
    }
    assert production_files == EXPECTED_PRODUCTION_FILES
    assert len(production_files) == len(EXPECTED_PRODUCTION_FILES)
    tree = ast.parse(EVIDENCE_SOURCE.read_bytes())
    definitions = {
        node.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
    }
    definitions.update(
        node.name.id for node in ast.walk(tree) if isinstance(node, ast.TypeAlias)
    )
    public_symbols = tuple(
        node.name
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
        else node.name.id
        for node in tree.body
        if (
            isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
            and not node.name.startswith("_")
        )
        or (isinstance(node, ast.TypeAlias) and not node.name.id.startswith("_"))
    )
    public_classes = {
        node.name
        for node in tree.body
        if isinstance(node, ast.ClassDef) and not node.name.startswith("_")
    }
    public_functions = {
        node.name
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and not node.name.startswith("_")
    }
    assert public_symbols == EXPECTED_EVIDENCE_EXPORTS
    assert len(public_classes) == 55
    assert public_functions == {
        "project_evidence_envelope_to_legacy_artifact_snapshot",
        "wrap_legacy_artifact_snapshot",
    }
    assert {node.name.id for node in tree.body if isinstance(node, ast.TypeAlias)} == {
        "EvidenceRecordRelationship"
    }
    assert (
        not {
            "AcquisitionRunRecord",
            "CompletenessRecord",
            "CorrectionRecord",
            "EvidenceAdapterRegistry",
            "EvidenceConfidence",
            "EvidenceContractCorpus",
            "EvidenceMigration",
            "EvidencePersistence",
            "EvidenceReader",
            "EvidenceReview",
            "EvidenceStorage",
            "EvidenceWriter",
            "OmissionRecord",
            "PublicationProvenance",
            "RepositorySnapshot",
            "TransformationRecord",
        }
        & definitions
    )


def test_production_artifact_models_perform_no_io_hashing_or_payload_work() -> None:
    tree = ast.parse(EVIDENCE_SOURCE.read_bytes())
    imports = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }
    imports.update(
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    )
    assert (
        not {
            "hashlib",
            "io",
            "os",
            "pathlib",
            "requests",
            "subprocess",
            "urllib",
        }
        & imports
    )
    forbidden_calls = {
        "open",
        "read_bytes",
        "read_text",
        "sha256",
        "write_bytes",
        "write_text",
    }
    observed_calls = {
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    observed_calls.update(
        node.func.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    )
    assert not forbidden_calls & observed_calls


def test_legacy_artifact_snapshot_is_byte_locked_separate_and_unchanged() -> None:
    raw = SOURCE_SOURCE.read_bytes()
    assert len(raw) == 4336
    assert sha256(raw).hexdigest() == (
        "034e53fd58212f0e34376bbc790fc3e74057031aaed4d7d89fb67904bdd380bf"
    )
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
    assert not issubclass(ExactArtifactIdentity, ArtifactSnapshot)
    assert not issubclass(ExactRetainedArtifact, ArtifactSnapshot)
    assert not issubclass(evidence_module.EvidenceEnvelope, ArtifactSnapshot)
    assert not issubclass(ArtifactSnapshot, evidence_module.EvidenceEnvelope)
    assert (set(ArtifactSnapshot.model_fields) - {"schema_version"}).isdisjoint(
        evidence_module.EvidenceEnvelope.model_fields
    )


@pytest.mark.parametrize("mutation", ("missing", "unexpected"))
def test_evidence_export_inventory_is_mutation_sensitive(mutation: str) -> None:
    exports: list[str] = list(EXPECTED_EVIDENCE_EXPORTS)
    if mutation == "missing":
        exports.remove("ExactRetainedArtifact")
    else:
        exports.append("TransformationRecord")
    with pytest.raises(AssertionError):
        assert tuple(exports) == EXPECTED_EVIDENCE_EXPORTS


def test_package_root_export_and_extra_module_mutations_are_rejected() -> None:
    with pytest.raises(AssertionError):
        assert ["__version__", "ExactRetainedArtifact"] == ["__version__"]
    with pytest.raises(AssertionError):
        assert (
            EXPECTED_PRODUCTION_FILES | {"src/faultatlas/domain/artifact.py"}
            == EXPECTED_PRODUCTION_FILES
        )
