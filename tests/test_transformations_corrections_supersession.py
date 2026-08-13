from __future__ import annotations

import ast
import json
import stat
from datetime import UTC, datetime, timedelta, timezone
from enum import StrEnum
from hashlib import sha256
from pathlib import Path
from typing import Any, cast, get_args

import pytest
from pydantic import BaseModel, RootModel, TypeAdapter, ValidationError

import faultatlas
import faultatlas.domain as domain_package
import faultatlas.domain.evidence as evidence_module
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
ACQUISITION_SIDECAR = ACQUISITION_ROOT / "acquisition.sha256"
CORRECTION_ROOT = (
    REPOSITORY_ROOT
    / "reference_corpus"
    / "pytest-4412"
    / "corrections"
    / "s04-c01-acquisition-closure"
)
CORRECTION_PATH = CORRECTION_ROOT / "correction.json"
CORRECTION_SIDECAR = CORRECTION_ROOT / "correction.sha256"

CANONICAL_FORMAT = "faultatlas-acquisition"
CANONICAL_CORRECTION_FORMAT = "faultatlas-pytest-4412-acquisition-closure-addendum"
CANONICAL_VERSION = "1"
CANONICAL_CANONICALIZATION = "json-sort-keys-compact-utf8-lf-v1"
CANONICAL_RELATIONSHIP_ID = "s04-c01-acquisition-closure"
CANONICAL_RECORDED_AT = datetime(2026, 7, 30, 19, 17, 9, 655780, tzinfo=UTC)
CANONICAL_ACQUISITION_LENGTH = 61_283
CANONICAL_ACQUISITION_SHA256 = (
    "1c29093bf1537e9b824a18df1848b71a8da014f544bc9f385707eb0e000a1318"
)
CANONICAL_CORRECTION_LENGTH = 60_832
CANONICAL_CORRECTION_SHA256 = (
    "44491ee512d2c2022110b83967fb6fa86d13045bc8404ea490d7a08b7aef24a2"
)
CANONICAL_ACQUISITION_SIDECAR_SHA256 = (
    "dbb4cf7cb2c0b95377a0a11892b854a46c43dd6c443e7e808e3a57fe31981824"
)
CANONICAL_CORRECTION_SIDECAR_SHA256 = (
    "c585d66ea3d7edf6465ba292c7f08af9a15972ba082f4b0e07a8ffc3f6d61977"
)
SOURCE_SOURCE_LENGTH = 4_336
SOURCE_SOURCE_SHA256 = (
    "034e53fd58212f0e34376bbc790fc3e74057031aaed4d7d89fb67904bdd380bf"
)
SYNTHETIC_PERFORMED_AT = datetime(2026, 8, 9, 12, 0, 0, tzinfo=UTC)
MAX_TRANSFORMATION_INPUTS = 64
MAX_TRANSFORMATION_OUTPUTS = 64

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
EXPECTED_RUNTIME_EXPORTS = (
    AcquisitionRunId,
    RetrievalRequestOrdinal,
    RetrievalRequestId,
    RetrievalMethod,
    RetrievalRoutePath,
    RetrievalRequestReference,
    MediaType,
    ApiVersion,
    RequestQueryParameter,
    RetrievalRequestControls,
    ResponseRepresentationState,
    HttpStatusCode,
    ContentEncoding,
    MediaTypeParameter,
    ResponseRepresentationObservation,
    ArtifactDigestAlgorithm,
    ArtifactDigestScope,
    ArtifactSha256Digest,
    ArtifactByteLength,
    ArtifactDigest,
    ExactArtifactIdentity,
    ArtifactRetentionMode,
    ExactRetainedArtifact,
    AcquisitionRunStatus,
    AcquisitionRequestMembership,
    AcquisitionRun,
    EvidenceRecordFormat,
    EvidenceVersion,
    EvidenceCanonicalization,
    DurableEvidenceRecordReference,
    EvidenceRelationId,
    TransformationOperation,
    TransformationLossiness,
    TransformationReversibility,
    TransformationSubject,
    EvidenceTransformation,
    EvidenceCorrection,
    EvidenceSupersession,
    EvidenceRecordRelationship,
    EvidenceScopeId,
    EvidenceRequirementId,
    EvidenceDispositionReason,
    EvidenceRequirementOutcome,
    EvidenceOmission,
    EvidenceRequirementResult,
    EvidenceCompletenessStatus,
    EvidenceCompletenessAssessment,
    EvidencePublicationMethod,
    PublicationCheckEvent,
    PublicationCheckName,
    SuccessfulPublicationCheck,
    EvidencePublication,
    EvidenceEnvelope,
    LegacyEvidenceCompatibilityReason,
    LegacyArtifactSnapshotEnvelopeMappingResult,
    LegacyArtifactSnapshotProjectionResult,
    wrap_legacy_artifact_snapshot,
    project_evidence_envelope_to_legacy_artifact_snapshot,
)
EXPECTED_PUBLIC_CLASSES = tuple(
    name
    for name in EXPECTED_EVIDENCE_EXPORTS
    if name
    not in {
        "EvidenceRecordRelationship",
        "project_evidence_envelope_to_legacy_artifact_snapshot",
        "wrap_legacy_artifact_snapshot",
    }
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
EXPECTED_MODEL_FIELDS = {
    DurableEvidenceRecordReference: (
        "schema_version",
        "format_name",
        "format_version",
        "canonicalization",
        "sha256",
        "byte_length",
    ),
    TransformationSubject: (
        "schema_version",
        "subject_kind",
        "artifact_identity",
        "record_reference",
    ),
    EvidenceTransformation: (
        "schema_version",
        "transformation_id",
        "operation",
        "operation_version",
        "performed_at",
        "inputs",
        "outputs",
        "lossiness",
        "reversibility",
        "parameter_record",
    ),
    EvidenceCorrection: (
        "schema_version",
        "relationship_kind",
        "relationship_id",
        "target_record",
        "correction_record",
        "recorded_at",
    ),
    EvidenceSupersession: (
        "schema_version",
        "relationship_kind",
        "relationship_id",
        "superseded_record",
        "superseding_record",
        "recorded_at",
    ),
}
FORBIDDEN_POST_S07_DEFINITIONS = {
    "CompletenessRecord",
    "EvidenceAdapterRegistry",
    "EvidenceCompleteness",
    "EvidenceConfidence",
    "EvidenceContractCorpus",
    "EvidenceMigration",
    "EvidencePersistence",
    "EvidenceReader",
    "EvidenceReview",
    "EvidenceStorage",
    "EvidenceWriter",
    "MigrationRecord",
    "MissingEvidence",
    "OmissionRecord",
    "PublicationProvenance",
    "RepositorySnapshot",
}
FORBIDDEN_S05_FIELDS = {
    "adapter",
    "callback",
    "completeness",
    "corpus_path",
    "current",
    "delete_prior",
    "deletion",
    "envelope",
    "environment",
    "executor",
    "findings",
    "http_client",
    "json_patch",
    "latest",
    "loader",
    "migration",
    "missing_evidence",
    "omission",
    "operation_parameters",
    "parameter_map",
    "path",
    "payload",
    "publication",
    "publication_commit",
    "pull_request",
    "reader",
    "replacement",
    "repository",
    "request_id",
    "response_observation",
    "run_id",
    "runtime",
    "source",
    "storage",
    "storage_path",
    "tool_identity",
    "transitive",
    "uri",
    "writer",
}


def _artifact_identity(index: int = 1) -> ExactArtifactIdentity:
    return ExactArtifactIdentity(
        digest=ArtifactDigest(
            algorithm=ArtifactDigestAlgorithm.SHA256,
            scope=ArtifactDigestScope.model_validate("synthetic-entity-body"),
            value=ArtifactSha256Digest.model_validate(f"{index:064x}"),
        ),
        byte_length=ArtifactByteLength.model_validate(index),
    )


def _target_reference() -> DurableEvidenceRecordReference:
    return DurableEvidenceRecordReference(
        format_name=EvidenceRecordFormat.model_validate(CANONICAL_FORMAT),
        format_version=EvidenceVersion.model_validate(CANONICAL_VERSION),
        canonicalization=EvidenceCanonicalization.model_validate(
            CANONICAL_CANONICALIZATION
        ),
        sha256=ArtifactSha256Digest.model_validate(CANONICAL_ACQUISITION_SHA256),
        byte_length=ArtifactByteLength.model_validate(CANONICAL_ACQUISITION_LENGTH),
    )


def _correction_reference() -> DurableEvidenceRecordReference:
    return DurableEvidenceRecordReference(
        format_name=EvidenceRecordFormat.model_validate(CANONICAL_CORRECTION_FORMAT),
        format_version=EvidenceVersion.model_validate(CANONICAL_VERSION),
        canonicalization=EvidenceCanonicalization.model_validate(
            CANONICAL_CANONICALIZATION
        ),
        sha256=ArtifactSha256Digest.model_validate(CANONICAL_CORRECTION_SHA256),
        byte_length=ArtifactByteLength.model_validate(CANONICAL_CORRECTION_LENGTH),
    )


def _synthetic_reference(
    index: int = 1,
    *,
    format_name: str = "faultatlas-synthetic-record",
    format_version: str = "1",
    canonicalization: str = "synthetic-json-v1",
) -> DurableEvidenceRecordReference:
    return DurableEvidenceRecordReference(
        format_name=EvidenceRecordFormat.model_validate(format_name),
        format_version=EvidenceVersion.model_validate(format_version),
        canonicalization=EvidenceCanonicalization.model_validate(canonicalization),
        sha256=ArtifactSha256Digest.model_validate(f"{index + 1000:064x}"),
        byte_length=ArtifactByteLength.model_validate(index),
    )


def _artifact_subject(index: int = 1) -> TransformationSubject:
    return TransformationSubject(
        subject_kind="exact_artifact",
        artifact_identity=_artifact_identity(index),
        record_reference=None,
    )


def _record_subject(
    index: int = 1,
    *,
    record_reference: DurableEvidenceRecordReference | None = None,
) -> TransformationSubject:
    return TransformationSubject(
        subject_kind="durable_record",
        artifact_identity=None,
        record_reference=record_reference or _synthetic_reference(index),
    )


def _transformation(
    *,
    transformation_id: str = "synthetic-transformation-001",
    operation: str = "synthetic-byte-reversal",
    operation_version: str = "1",
    performed_at: datetime = SYNTHETIC_PERFORMED_AT,
    inputs: tuple[TransformationSubject, ...] | None = None,
    outputs: tuple[TransformationSubject, ...] | None = None,
    lossiness: TransformationLossiness = TransformationLossiness.LOSSLESS,
    reversibility: TransformationReversibility = (
        TransformationReversibility.REVERSIBLE
    ),
    parameter_record: DurableEvidenceRecordReference | None = None,
) -> EvidenceTransformation:
    return EvidenceTransformation(
        transformation_id=EvidenceRelationId.model_validate(transformation_id),
        operation=TransformationOperation.model_validate(operation),
        operation_version=EvidenceVersion.model_validate(operation_version),
        performed_at=performed_at,
        inputs=(_artifact_subject(1),) if inputs is None else inputs,
        outputs=(_artifact_subject(2),) if outputs is None else outputs,
        lossiness=lossiness,
        reversibility=reversibility,
        parameter_record=parameter_record,
    )


def _canonical_correction() -> EvidenceCorrection:
    return EvidenceCorrection(
        relationship_kind="correction",
        relationship_id=EvidenceRelationId.model_validate(CANONICAL_RELATIONSHIP_ID),
        target_record=_target_reference(),
        correction_record=_correction_reference(),
        recorded_at=CANONICAL_RECORDED_AT,
    )


def _synthetic_supersession() -> EvidenceSupersession:
    return EvidenceSupersession(
        relationship_kind="supersession",
        relationship_id=EvidenceRelationId.model_validate("synthetic-supersession-001"),
        superseded_record=_synthetic_reference(11),
        superseding_record=_synthetic_reference(12),
        recorded_at=SYNTHETIC_PERFORMED_AT,
    )


def _model_payload(model: object) -> dict[str, object]:
    typed_model = cast(Any, model)
    return {
        field: cast(object, getattr(typed_model, field))
        for field in typed_model.__class__.model_fields
    }


def _parse_exports(source: str) -> tuple[str, ...]:
    tree = ast.parse(source)
    assignments = [
        node
        for node in tree.body
        if isinstance(node, ast.Assign)
        and any(
            isinstance(target, ast.Name) and target.id == "__all__"
            for target in node.targets
        )
    ]
    assert len(assignments) == 1
    value = cast(object, ast.literal_eval(assignments[0].value))
    assert isinstance(value, list)
    raw = cast(list[object], value)
    assert all(isinstance(item, str) for item in raw)
    return tuple(cast(str, item) for item in raw)


def _assignment_name_and_value(
    node: ast.stmt,
) -> tuple[str, ast.expr] | None:
    if (
        isinstance(node, ast.Assign)
        and len(node.targets) == 1
        and isinstance(node.targets[0], ast.Name)
    ):
        return node.targets[0].id, node.value
    if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
        assert node.value is not None
        return node.target.id, node.value
    return None


def _parse_transformation_caps(source: str) -> dict[str, int]:
    expected = {
        "_MAX_TRANSFORMATION_INPUTS",
        "_MAX_TRANSFORMATION_OUTPUTS",
    }
    observed: dict[str, int] = {}
    for node in ast.parse(source).body:
        assignment = _assignment_name_and_value(node)
        if assignment is None or assignment[0] not in expected:
            continue
        value = cast(object, ast.literal_eval(assignment[1]))
        assert type(value) is int
        observed[assignment[0]] = value
    assert set(observed) == expected
    return observed


def _type_alias_name(node: ast.TypeAlias) -> str:
    assert isinstance(node.name, ast.Name)
    return node.name.id


def _validate_evidence_surface(source: str) -> None:
    tree = ast.parse(source)
    assert _parse_exports(source) == EXPECTED_EVIDENCE_EXPORTS
    public_classes = tuple(
        node.name
        for node in tree.body
        if isinstance(node, ast.ClassDef) and not node.name.startswith("_")
    )
    assert public_classes == EXPECTED_PUBLIC_CLASSES
    public_functions = tuple(
        node.name
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and not node.name.startswith("_")
    )
    assert public_functions == (
        "wrap_legacy_artifact_snapshot",
        "project_evidence_envelope_to_legacy_artifact_snapshot",
    )
    public_aliases = tuple(
        _type_alias_name(node)
        for node in tree.body
        if isinstance(node, ast.TypeAlias)
        and not _type_alias_name(node).startswith("_")
    )
    assert public_aliases == ("EvidenceRecordRelationship",)
    alias_nodes = [
        node
        for node in tree.body
        if isinstance(node, ast.TypeAlias)
        and _type_alias_name(node) == "EvidenceRecordRelationship"
    ]
    assert len(alias_nodes) == 1
    alias_value = ast.unparse(alias_nodes[0].value)
    assert alias_value.startswith("Annotated[")
    assert "EvidenceCorrection | EvidenceSupersession" in alias_value
    assert "Field(discriminator='relationship_kind')" in alias_value
    private_bases = [
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == "_EvidenceRecordBase"
    ]
    assert len(private_bases) == 1
    definitions = {
        node.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
    }
    assert not definitions & FORBIDDEN_POST_S07_DEFINITIONS
    assert _parse_transformation_caps(source) == {
        "_MAX_TRANSFORMATION_INPUTS": MAX_TRANSFORMATION_INPUTS,
        "_MAX_TRANSFORMATION_OUTPUTS": MAX_TRANSFORMATION_OUTPUTS,
    }


def _assert_root_config(model: type[Any]) -> None:
    assert model.model_config == {
        "frozen": True,
        "revalidate_instances": "always",
        "strict": True,
        "validate_default": True,
    }


def _assert_record_config(model: type[BaseModel]) -> None:
    assert model.model_config == {
        "extra": "forbid",
        "frozen": True,
        "revalidate_instances": "always",
        "strict": True,
        "validate_default": True,
    }


def _load_json(path: Path) -> dict[str, Any]:
    loaded = json.loads(path.read_bytes())
    assert isinstance(loaded, dict)
    return cast(dict[str, Any], loaded)


def _collect_named_values(value: object, name: str) -> list[object]:
    observed: list[object] = []
    if isinstance(value, dict):
        typed = cast(dict[object, object], value)
        if name in typed:
            observed.append(typed[name])
        for child in typed.values():
            observed.extend(_collect_named_values(child, name))
    elif isinstance(value, list):
        for child in cast(list[object], value):
            observed.extend(_collect_named_values(child, name))
    return observed


def _assert_exact_regular_file(
    path: Path,
    *,
    byte_length: int,
    digest: str,
) -> bytes:
    assert path.exists()
    assert not path.is_symlink()
    path_stat = path.stat()
    assert stat.S_ISREG(path_stat.st_mode)
    assert stat.S_IMODE(path_stat.st_mode) == 0o644
    raw = path.read_bytes()
    assert len(raw) == byte_length
    assert sha256(raw).hexdigest() == digest
    return raw


def test_preferred_runtime_imports_and_export_order_are_exact() -> None:
    assert tuple(
        getattr(symbol, "__name__") for symbol in EXPECTED_RUNTIME_EXPORTS
    ) == (EXPECTED_EVIDENCE_EXPORTS)
    assert tuple(evidence_module.__all__) == EXPECTED_EVIDENCE_EXPORTS
    assert len(evidence_module.__all__) == len(set(evidence_module.__all__)) == 58


def test_package_roots_current_sources_and_artifact_snapshot_boundary_are_exact() -> (
    None
):
    production_files = {
        path.relative_to(REPOSITORY_ROOT).as_posix()
        for path in (REPOSITORY_ROOT / "src").rglob("*.py")
    }
    assert production_files == EXPECTED_PRODUCTION_FILES
    assert len(production_files) == len(EXPECTED_PRODUCTION_FILES)
    assert faultatlas.__all__ == ["__version__"]
    assert getattr(domain_package, "__all__", None) in (None, [])
    assert not set(EXPECTED_EVIDENCE_EXPORTS) & set(vars(faultatlas))
    assert not set(EXPECTED_EVIDENCE_EXPORTS) & set(vars(domain_package))
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
    source_raw = SOURCE_SOURCE.read_bytes()
    assert len(source_raw) == SOURCE_SOURCE_LENGTH
    assert sha256(source_raw).hexdigest() == SOURCE_SOURCE_SHA256


@pytest.mark.parametrize(
    "value",
    (
        "a",
        "faultatlas-acquisition",
        "faultatlas-pytest-4412-acquisition-closure-addendum",
        "a" * 160,
    ),
)
def test_evidence_record_format_accepts_exact_bounded_lexemes(value: str) -> None:
    record_format = EvidenceRecordFormat.model_validate(value)
    assert record_format.root == value
    assert EvidenceRecordFormat.model_validate_json(
        record_format.model_dump_json()
    ) == (record_format)


@pytest.mark.parametrize(
    "value",
    (
        "",
        "Faultatlas-acquisition",
        "faultatlas-Acquisition",
        "-faultatlas",
        "faultatlas-",
        "faultatlas/acquisition",
        "faultatlas\\acquisition",
        "faultatlas:acquisition",
        "faultatlas.acquisition",
        "faultatlas_acquisition",
        "faultatlas acquisition",
        "faultatlas\tacquisition",
        "faultatlas\x00acquisition",
        "faultatlas-évidence",
        "a" * 161,
        1,
        True,
        None,
    ),
)
def test_evidence_record_format_rejects_invalid_or_coerced_values(
    value: object,
) -> None:
    with pytest.raises(ValidationError):
        EvidenceRecordFormat.model_validate(value)
    with pytest.raises(ValidationError):
        EvidenceRecordFormat.model_validate_json(json.dumps(value))


@pytest.mark.parametrize(
    "value",
    ("1", "v1", "V1.2_beta-3", "a" * 64),
)
def test_evidence_version_accepts_exact_bounded_lexemes(value: str) -> None:
    version = EvidenceVersion.model_validate(value)
    assert version.root == value
    assert EvidenceVersion.model_validate_json(version.model_dump_json()) == version


@pytest.mark.parametrize(
    "value",
    (
        "",
        ".1",
        "1.",
        "-1",
        "1-",
        "_1",
        "1_",
        "v 1",
        "v\t1",
        "v\x7f1",
        "v/1",
        "v\\1",
        "v:1",
        "https://version",
        "vé",
        "a" * 65,
        1,
        True,
        None,
    ),
)
def test_evidence_version_rejects_invalid_or_coerced_values(value: object) -> None:
    with pytest.raises(ValidationError):
        EvidenceVersion.model_validate(value)
    with pytest.raises(ValidationError):
        EvidenceVersion.model_validate_json(json.dumps(value))


@pytest.mark.parametrize(
    "value",
    ("a", CANONICAL_CANONICALIZATION, "a" * 160),
)
def test_evidence_canonicalization_accepts_exact_bounded_lexemes(
    value: str,
) -> None:
    canonicalization = EvidenceCanonicalization.model_validate(value)
    assert canonicalization.root == value
    assert (
        EvidenceCanonicalization.model_validate_json(canonicalization.model_dump_json())
        == canonicalization
    )


@pytest.mark.parametrize(
    "value",
    (
        "",
        "Json-v1",
        "json.V1",
        "-json-v1",
        "json-v1-",
        "json_v1",
        "json/v1",
        "json\\v1",
        "json:v1",
        "json v1",
        "json\nv1",
        "jsoñ-v1",
        "a" * 161,
        1,
        None,
    ),
)
def test_evidence_canonicalization_rejects_invalid_or_coerced_values(
    value: object,
) -> None:
    with pytest.raises(ValidationError):
        EvidenceCanonicalization.model_validate(value)
    with pytest.raises(ValidationError):
        EvidenceCanonicalization.model_validate_json(json.dumps(value))


@pytest.mark.parametrize(
    "value",
    (
        "a",
        CANONICAL_RELATIONSHIP_ID,
        "relation.with_underscores-and-dots",
        "a" * 160,
    ),
)
def test_evidence_relation_id_accepts_exact_bounded_lexemes(value: str) -> None:
    relation_id = EvidenceRelationId.model_validate(value)
    assert relation_id.root == value
    assert EvidenceRelationId.model_validate_json(relation_id.model_dump_json()) == (
        relation_id
    )


@pytest.mark.parametrize(
    "value",
    (
        "",
        "Relation",
        "-relation",
        "relation-",
        ".relation",
        "relation.",
        "_relation",
        "relation_",
        "relation/path",
        "relation\\path",
        "relation:value",
        "relation value",
        "relation\x1fvalue",
        "relatión",
        "a" * 161,
        1,
        None,
    ),
)
def test_evidence_relation_id_rejects_invalid_or_coerced_values(
    value: object,
) -> None:
    with pytest.raises(ValidationError):
        EvidenceRelationId.model_validate(value)
    with pytest.raises(ValidationError):
        EvidenceRelationId.model_validate_json(json.dumps(value))


@pytest.mark.parametrize(
    "value",
    (
        "a",
        "synthetic-byte-reversal",
        "synthetic-record-normalization",
        "a" * 128,
    ),
)
def test_transformation_operation_accepts_exact_bounded_lexemes(value: str) -> None:
    operation = TransformationOperation.model_validate(value)
    assert operation.root == value
    assert TransformationOperation.model_validate_json(operation.model_dump_json()) == (
        operation
    )


@pytest.mark.parametrize(
    "value",
    (
        "",
        "Synthetic-operation",
        "-operation",
        "operation-",
        "operation.name",
        "operation_name",
        "operation/path",
        "operation\\path",
        "operation:name",
        "operation name",
        "operation\x00name",
        "operatión",
        "a" * 129,
        1,
        None,
    ),
)
def test_transformation_operation_rejects_invalid_or_coerced_values(
    value: object,
) -> None:
    with pytest.raises(ValidationError):
        TransformationOperation.model_validate(value)
    with pytest.raises(ValidationError):
        TransformationOperation.model_validate_json(json.dumps(value))


def test_new_root_primitives_are_strict_frozen_root_models() -> None:
    for model in (
        EvidenceRecordFormat,
        EvidenceVersion,
        EvidenceCanonicalization,
        EvidenceRelationId,
        TransformationOperation,
    ):
        assert issubclass(model, RootModel)
        assert tuple(model.model_fields) == ("root",)
        _assert_root_config(model)

    record_format = EvidenceRecordFormat.model_validate(CANONICAL_FORMAT)
    with pytest.raises(ValidationError):
        cast(Any, record_format).root = "changed"


def test_transformation_enums_are_exact_str_enums() -> None:
    assert issubclass(TransformationLossiness, StrEnum)
    assert issubclass(TransformationReversibility, StrEnum)
    assert tuple(member.value for member in TransformationLossiness) == (
        "lossless",
        "lossy",
        "unknown",
    )
    assert tuple(member.value for member in TransformationReversibility) == (
        "reversible",
        "irreversible",
        "unknown",
    )
    for enum_type in (TransformationLossiness, TransformationReversibility):
        adapter = TypeAdapter(enum_type)
        for member in enum_type:
            assert adapter.validate_python(member, strict=True) is member
            assert (
                adapter.validate_json(json.dumps(member.value), strict=True) is member
            )
        for invalid in ("LOSSLESS", "reversable", "none", 1, True, None):
            with pytest.raises(ValidationError):
                adapter.validate_python(invalid, strict=True)


def test_durable_reference_fields_types_config_and_canonical_values_are_exact() -> None:
    assert (
        tuple(DurableEvidenceRecordReference.model_fields)
        == (EXPECTED_MODEL_FIELDS[DurableEvidenceRecordReference])
    )
    _assert_record_config(DurableEvidenceRecordReference)
    fields = DurableEvidenceRecordReference.model_fields
    assert fields["format_name"].annotation is EvidenceRecordFormat
    assert fields["format_version"].annotation is EvidenceVersion
    assert fields["canonicalization"].annotation is EvidenceCanonicalization
    assert fields["sha256"].annotation is ArtifactSha256Digest
    assert fields["byte_length"].annotation is ArtifactByteLength

    target = _target_reference()
    assert target.schema_version == 1
    assert target.format_name.root == CANONICAL_FORMAT
    assert target.format_version.root == CANONICAL_VERSION
    assert target.canonicalization.root == CANONICAL_CANONICALIZATION
    assert target.sha256.root == CANONICAL_ACQUISITION_SHA256
    assert target.byte_length.root == CANONICAL_ACQUISITION_LENGTH


def test_durable_reference_semantic_json_round_trip_preserves_nested_types() -> None:
    for reference in (_target_reference(), _correction_reference()):
        decoded = DurableEvidenceRecordReference.model_validate_json(
            reference.model_dump_json()
        )
        assert decoded == reference
        assert decoded is not reference
        assert isinstance(decoded.format_name, EvidenceRecordFormat)
        assert isinstance(decoded.format_version, EvidenceVersion)
        assert isinstance(decoded.canonicalization, EvidenceCanonicalization)
        assert isinstance(decoded.sha256, ArtifactSha256Digest)
        assert isinstance(decoded.byte_length, ArtifactByteLength)


def test_durable_reference_identity_uses_every_explicit_component() -> None:
    target = _target_reference()
    variants = (
        DurableEvidenceRecordReference.model_validate(
            {
                **_model_payload(target),
                "format_name": EvidenceRecordFormat.model_validate(
                    "synthetic-acquisition"
                ),
            }
        ),
        DurableEvidenceRecordReference.model_validate(
            {
                **_model_payload(target),
                "format_version": EvidenceVersion.model_validate("2"),
            }
        ),
        DurableEvidenceRecordReference.model_validate(
            {
                **_model_payload(target),
                "canonicalization": EvidenceCanonicalization.model_validate(
                    "synthetic-json-v1"
                ),
            }
        ),
        DurableEvidenceRecordReference.model_validate(
            {
                **_model_payload(target),
                "sha256": ArtifactSha256Digest.model_validate("f" * 64),
            }
        ),
        DurableEvidenceRecordReference.model_validate(
            {
                **_model_payload(target),
                "byte_length": ArtifactByteLength.model_validate(
                    CANONICAL_ACQUISITION_LENGTH + 1
                ),
            }
        ),
    )
    assert all(variant != target for variant in variants)
    all_references = (target, *variants)
    assert all(
        left != right
        for index, left in enumerate(all_references)
        for right in all_references[index + 1 :]
    )


@pytest.mark.parametrize(
    ("field", "raw_value"),
    (
        ("format_name", CANONICAL_FORMAT),
        ("format_version", CANONICAL_VERSION),
        ("canonicalization", CANONICAL_CANONICALIZATION),
        ("sha256", CANONICAL_ACQUISITION_SHA256),
        ("byte_length", CANONICAL_ACQUISITION_LENGTH),
    ),
)
def test_durable_reference_requires_typed_nested_python_values(
    field: str,
    raw_value: object,
) -> None:
    payload = _model_payload(_target_reference())
    payload[field] = raw_value
    with pytest.raises(ValidationError):
        DurableEvidenceRecordReference.model_validate(payload)

    semantic = _target_reference().model_dump(mode="json")
    assert isinstance(semantic, dict)
    assert (
        DurableEvidenceRecordReference.model_validate_json(json.dumps(semantic))
        == _target_reference()
    )


@pytest.mark.parametrize(
    "field",
    (
        "format_name",
        "format_version",
        "canonicalization",
        "sha256",
        "byte_length",
    ),
)
def test_durable_reference_rejects_missing_identity_components(field: str) -> None:
    semantic = cast(dict[str, object], _target_reference().model_dump(mode="json"))
    semantic.pop(field)
    with pytest.raises(ValidationError):
        DurableEvidenceRecordReference.model_validate_json(json.dumps(semantic))


@pytest.mark.parametrize(
    "field",
    (
        "path",
        "uri",
        "publication_commit",
        "loader",
        "payload",
        "record_body",
        "source",
        "request_id",
    ),
)
def test_durable_reference_rejects_storage_publication_and_body_fields(
    field: str,
) -> None:
    semantic = cast(dict[str, object], _target_reference().model_dump(mode="json"))
    semantic[field] = "forbidden"
    with pytest.raises(ValidationError):
        DurableEvidenceRecordReference.model_validate_json(json.dumps(semantic))


@pytest.mark.parametrize("schema_version", (0, 2, 1.0, "1", True, None))
def test_durable_reference_requires_exact_integer_schema_version(
    schema_version: object,
) -> None:
    payload = _model_payload(_target_reference())
    payload["schema_version"] = schema_version
    with pytest.raises(ValidationError):
        DurableEvidenceRecordReference.model_validate(payload)


def test_durable_reference_revalidates_constructed_invalid_nested_values() -> None:
    invalid_format = EvidenceRecordFormat.model_construct(root="INVALID")
    payload = _model_payload(_target_reference())
    payload["format_name"] = invalid_format
    with pytest.raises(ValidationError):
        DurableEvidenceRecordReference.model_validate(payload)


def test_durable_reference_is_frozen_and_extra_forbidden() -> None:
    target = _target_reference()
    with pytest.raises(ValidationError):
        cast(Any, target).byte_length = ArtifactByteLength.model_validate(1)
    with pytest.raises(ValidationError):
        DurableEvidenceRecordReference.model_validate(
            {
                **_model_payload(target),
                "path": "record.json",
            }
        )


def test_transformation_subject_fields_types_config_and_variants_are_exact() -> None:
    assert (
        tuple(TransformationSubject.model_fields)
        == (EXPECTED_MODEL_FIELDS[TransformationSubject])
    )
    _assert_record_config(TransformationSubject)
    fields = TransformationSubject.model_fields
    assert get_args(fields["subject_kind"].annotation) == (
        "exact_artifact",
        "durable_record",
    )
    assert fields["artifact_identity"].annotation == ExactArtifactIdentity | None
    assert fields["record_reference"].annotation == (
        DurableEvidenceRecordReference | None
    )

    artifact = _artifact_subject()
    record = _record_subject()
    assert artifact.subject_kind == "exact_artifact"
    assert isinstance(artifact.artifact_identity, ExactArtifactIdentity)
    assert artifact.record_reference is None
    assert record.subject_kind == "durable_record"
    assert record.artifact_identity is None
    assert isinstance(record.record_reference, DurableEvidenceRecordReference)


def test_transformation_subject_semantic_json_preserves_concrete_variant() -> None:
    for subject in (_artifact_subject(), _record_subject()):
        decoded = TransformationSubject.model_validate_json(subject.model_dump_json())
        assert decoded == subject
        assert decoded is not subject
        assert decoded.subject_kind == subject.subject_kind


@pytest.mark.parametrize(
    ("subject_kind", "artifact_identity", "record_reference"),
    (
        ("exact_artifact", None, None),
        ("durable_record", None, None),
        ("exact_artifact", _artifact_identity(), _synthetic_reference()),
        ("durable_record", _artifact_identity(), _synthetic_reference()),
        ("exact_artifact", None, _synthetic_reference()),
        ("durable_record", _artifact_identity(), None),
    ),
)
def test_transformation_subject_rejects_missing_both_present_both_or_mismatch(
    subject_kind: str,
    artifact_identity: ExactArtifactIdentity | None,
    record_reference: DurableEvidenceRecordReference | None,
) -> None:
    with pytest.raises(ValidationError):
        TransformationSubject.model_validate(
            {
                "subject_kind": subject_kind,
                "artifact_identity": artifact_identity,
                "record_reference": record_reference,
            }
        )


@pytest.mark.parametrize("subject_kind", ("artifact", "record", "unknown", 1, None))
def test_transformation_subject_rejects_unknown_or_coerced_kinds(
    subject_kind: object,
) -> None:
    with pytest.raises(ValidationError):
        TransformationSubject.model_validate(
            {
                "subject_kind": subject_kind,
                "artifact_identity": _artifact_identity(),
                "record_reference": None,
            }
        )


@pytest.mark.parametrize(
    ("subject", "field"),
    (
        (_artifact_subject(), "artifact_identity"),
        (_record_subject(), "record_reference"),
    ),
)
def test_transformation_subject_requires_typed_nested_python_values(
    subject: TransformationSubject,
    field: str,
) -> None:
    payload = _model_payload(subject)
    nested = cast(Any, payload[field])
    payload[field] = nested.model_dump(mode="json")
    with pytest.raises(ValidationError):
        TransformationSubject.model_validate(payload)

    semantic = cast(dict[str, object], subject.model_dump(mode="json"))
    assert TransformationSubject.model_validate_json(json.dumps(semantic)) == subject


@pytest.mark.parametrize(
    "field",
    (
        "request_id",
        "response_observation",
        "run_id",
        "path",
        "storage",
        "payload",
        "source",
    ),
)
def test_transformation_subject_rejects_request_run_storage_and_payload_fields(
    field: str,
) -> None:
    semantic = cast(dict[str, object], _artifact_subject().model_dump(mode="json"))
    semantic[field] = "forbidden"
    with pytest.raises(ValidationError):
        TransformationSubject.model_validate_json(json.dumps(semantic))


def test_transformation_subject_revalidates_constructed_invalid_nested_value() -> None:
    invalid_identity = ExactArtifactIdentity.model_construct(
        digest=None,
        byte_length=ArtifactByteLength.model_validate(1),
    )
    with pytest.raises(ValidationError):
        TransformationSubject(
            subject_kind="exact_artifact",
            artifact_identity=invalid_identity,
            record_reference=None,
        )


def test_transformation_fields_types_config_and_requiredness_are_exact() -> None:
    assert (
        tuple(EvidenceTransformation.model_fields)
        == (EXPECTED_MODEL_FIELDS[EvidenceTransformation])
    )
    _assert_record_config(EvidenceTransformation)
    fields = EvidenceTransformation.model_fields
    assert fields["transformation_id"].annotation is EvidenceRelationId
    assert fields["operation"].annotation is TransformationOperation
    assert fields["operation_version"].annotation is EvidenceVersion
    assert fields["inputs"].annotation == tuple[TransformationSubject, ...]
    assert fields["outputs"].annotation == tuple[TransformationSubject, ...]
    assert fields["lossiness"].annotation is TransformationLossiness
    assert fields["reversibility"].annotation is TransformationReversibility
    assert fields["parameter_record"].annotation == (
        DurableEvidenceRecordReference | None
    )
    for field in EXPECTED_MODEL_FIELDS[EvidenceTransformation][1:]:
        assert fields[field].is_required()


def test_lossless_reversible_artifact_transformation_is_explicit() -> None:
    transformation = _transformation()
    assert transformation.transformation_id.root == "synthetic-transformation-001"
    assert transformation.operation.root == "synthetic-byte-reversal"
    assert transformation.operation_version.root == "1"
    assert transformation.performed_at == SYNTHETIC_PERFORMED_AT
    assert transformation.inputs == (_artifact_subject(1),)
    assert transformation.outputs == (_artifact_subject(2),)
    assert transformation.lossiness is TransformationLossiness.LOSSLESS
    assert transformation.reversibility is TransformationReversibility.REVERSIBLE
    assert transformation.parameter_record is None


def test_lossy_irreversible_transformation_carries_exact_parameter_reference() -> None:
    parameter_record = _synthetic_reference(
        21,
        format_name="faultatlas-synthetic-parameters",
    )
    transformation = _transformation(
        transformation_id="synthetic-redaction-001",
        operation="synthetic-redaction",
        inputs=(_artifact_subject(3),),
        outputs=(_artifact_subject(4),),
        lossiness=TransformationLossiness.LOSSY,
        reversibility=TransformationReversibility.IRREVERSIBLE,
        parameter_record=parameter_record,
    )
    assert transformation.lossiness is TransformationLossiness.LOSSY
    assert transformation.reversibility is TransformationReversibility.IRREVERSIBLE
    assert transformation.parameter_record == parameter_record
    assert transformation.parameter_record is not parameter_record


def test_durable_record_transformation_remains_synthetic_and_explicit() -> None:
    transformation = _transformation(
        transformation_id="synthetic-record-transformation-001",
        operation="synthetic-record-normalization",
        operation_version="v1.0",
        inputs=(_record_subject(31),),
        outputs=(_record_subject(32),),
        lossiness=TransformationLossiness.UNKNOWN,
        reversibility=TransformationReversibility.UNKNOWN,
    )
    assert transformation.inputs[0].subject_kind == "durable_record"
    assert transformation.outputs[0].subject_kind == "durable_record"
    assert transformation.operation.root == "synthetic-record-normalization"
    assert transformation.operation_version.root == "v1.0"
    assert transformation.lossiness is TransformationLossiness.UNKNOWN
    assert transformation.reversibility is TransformationReversibility.UNKNOWN
    assert transformation.inputs[0].record_reference != _target_reference()


def test_transformation_semantic_json_round_trip_preserves_tuples_and_types() -> None:
    transformation = _transformation(
        inputs=(_artifact_subject(1), _record_subject(41)),
        outputs=(_record_subject(42), _artifact_subject(2)),
        parameter_record=_synthetic_reference(43),
    )
    decoded = EvidenceTransformation.model_validate_json(
        transformation.model_dump_json()
    )
    assert decoded == transformation
    assert decoded is not transformation
    assert type(decoded.inputs) is tuple
    assert type(decoded.outputs) is tuple
    assert all(isinstance(item, TransformationSubject) for item in decoded.inputs)
    assert all(isinstance(item, TransformationSubject) for item in decoded.outputs)
    assert isinstance(decoded.transformation_id, EvidenceRelationId)
    assert isinstance(decoded.operation, TransformationOperation)
    assert isinstance(decoded.operation_version, EvidenceVersion)
    assert isinstance(decoded.parameter_record, DurableEvidenceRecordReference)


def test_transformation_one_to_many_and_many_to_one_preserve_exact_order() -> None:
    one_to_many_outputs = (
        _artifact_subject(2),
        _record_subject(51),
        _artifact_subject(3),
    )
    one_to_many = _transformation(outputs=one_to_many_outputs)
    assert one_to_many.inputs == (_artifact_subject(1),)
    assert one_to_many.outputs == one_to_many_outputs

    many_to_one_inputs = (
        _record_subject(52),
        _artifact_subject(4),
        _record_subject(53),
    )
    many_to_one = _transformation(
        transformation_id="synthetic-many-to-one-001",
        inputs=many_to_one_inputs,
        outputs=(_artifact_subject(5),),
    )
    assert many_to_one.inputs == many_to_one_inputs
    assert many_to_one.outputs == (_artifact_subject(5),)


def test_transformation_input_and_output_reordering_changes_the_record() -> None:
    inputs = (_artifact_subject(1), _artifact_subject(2))
    outputs = (_artifact_subject(3), _artifact_subject(4))
    original = _transformation(inputs=inputs, outputs=outputs)
    reordered_inputs = _transformation(inputs=tuple(reversed(inputs)), outputs=outputs)
    reordered_outputs = _transformation(inputs=inputs, outputs=tuple(reversed(outputs)))
    assert original.inputs == inputs
    assert original.outputs == outputs
    assert reordered_inputs != original
    assert reordered_outputs != original


def test_transformation_partial_subject_overlap_is_allowed_without_inference() -> None:
    shared = _artifact_subject(2)
    transformation = _transformation(
        inputs=(_artifact_subject(1), shared),
        outputs=(shared, _artifact_subject(3)),
    )
    assert transformation.inputs[1] == transformation.outputs[0]
    assert set(transformation.inputs) != set(transformation.outputs)


@pytest.mark.parametrize(
    ("lossiness", "reversibility"),
    tuple(
        (lossiness, reversibility)
        for lossiness in TransformationLossiness
        for reversibility in TransformationReversibility
    ),
)
def test_lossiness_and_reversibility_are_independent_explicit_axes(
    lossiness: TransformationLossiness,
    reversibility: TransformationReversibility,
) -> None:
    transformation = _transformation(
        lossiness=lossiness,
        reversibility=reversibility,
    )
    assert transformation.lossiness is lossiness
    assert transformation.reversibility is reversibility


@pytest.mark.parametrize("field", ("inputs", "outputs"))
def test_transformation_requires_nonempty_inputs_and_outputs(field: str) -> None:
    payload = _model_payload(_transformation())
    payload[field] = ()
    with pytest.raises(ValidationError):
        EvidenceTransformation.model_validate(payload)

    semantic = cast(dict[str, object], _transformation().model_dump(mode="json"))
    semantic[field] = []
    with pytest.raises(ValidationError):
        EvidenceTransformation.model_validate_json(json.dumps(semantic))


@pytest.mark.parametrize("field", ("inputs", "outputs"))
def test_transformation_rejects_structurally_equal_duplicate_subjects(
    field: str,
) -> None:
    duplicate_one = _artifact_subject(7)
    duplicate_two = _artifact_subject(7)
    assert duplicate_one == duplicate_two
    assert duplicate_one is not duplicate_two
    payload = _model_payload(_transformation())
    payload[field] = (duplicate_one, duplicate_two)
    with pytest.raises(ValidationError):
        EvidenceTransformation.model_validate(payload)


def test_transformation_rejects_identical_subject_sets_even_when_reordered() -> None:
    first = _artifact_subject(8)
    second = _record_subject(61)
    with pytest.raises(ValidationError):
        _transformation(
            inputs=(first, second),
            outputs=(second, first),
        )


@pytest.mark.parametrize(
    ("field", "maximum"),
    (
        ("inputs", MAX_TRANSFORMATION_INPUTS),
        ("outputs", MAX_TRANSFORMATION_OUTPUTS),
    ),
)
def test_transformation_collection_maximum_is_accepted(
    field: str,
    maximum: int,
) -> None:
    subjects = tuple(_artifact_subject(index) for index in range(100, 100 + maximum))
    payload = _model_payload(_transformation())
    payload[field] = subjects
    transformation = EvidenceTransformation.model_validate(payload)
    assert getattr(transformation, field) == subjects
    assert len(getattr(transformation, field)) == maximum


@pytest.mark.parametrize(
    ("field", "maximum"),
    (
        ("inputs", MAX_TRANSFORMATION_INPUTS),
        ("outputs", MAX_TRANSFORMATION_OUTPUTS),
    ),
)
def test_python_max_plus_one_rejects_before_invalid_nested_revalidation(
    field: str,
    maximum: int,
) -> None:
    invalid = TransformationSubject.model_construct(
        subject_kind="exact_artifact",
        artifact_identity=None,
        record_reference=None,
    )
    payload = _model_payload(_transformation())
    payload[field] = tuple(invalid for _ in range(maximum + 1))
    with pytest.raises(ValidationError) as captured:
        EvidenceTransformation.model_validate(payload)
    errors = captured.value.errors()
    assert len(errors) == 1
    assert errors[0]["loc"] == (field,)
    assert errors[0]["type"] == "value_error"


@pytest.mark.parametrize(
    ("field", "maximum"),
    (
        ("inputs", MAX_TRANSFORMATION_INPUTS),
        ("outputs", MAX_TRANSFORMATION_OUTPUTS),
    ),
)
def test_json_max_plus_one_rejects_before_invalid_nested_validation(
    field: str,
    maximum: int,
) -> None:
    semantic = cast(dict[str, object], _transformation().model_dump(mode="json"))
    semantic[field] = [
        {"schema_version": 1, "raw-cap-marker": index} for index in range(maximum + 1)
    ]
    with pytest.raises(ValidationError) as captured:
        EvidenceTransformation.model_validate_json(json.dumps(semantic))
    errors = captured.value.errors()
    assert len(errors) == 1
    assert errors[0]["loc"] == (field,)
    assert errors[0]["type"] == "value_error"


@pytest.mark.parametrize("field", ("inputs", "outputs"))
def test_python_transformation_collections_require_exact_tuples(field: str) -> None:
    payload = _model_payload(_transformation())
    payload[field] = list(cast(tuple[TransformationSubject, ...], payload[field]))
    with pytest.raises(ValidationError):
        EvidenceTransformation.model_validate(payload)


@pytest.mark.parametrize(
    "field",
    (
        "transformation_id",
        "operation",
        "operation_version",
        "performed_at",
        "inputs",
        "outputs",
        "lossiness",
        "reversibility",
        "parameter_record",
    ),
)
def test_transformation_requires_every_explicit_field(field: str) -> None:
    semantic = cast(dict[str, object], _transformation().model_dump(mode="json"))
    semantic.pop(field)
    with pytest.raises(ValidationError):
        EvidenceTransformation.model_validate_json(json.dumps(semantic))


@pytest.mark.parametrize(
    ("field", "raw_value"),
    (
        ("transformation_id", "synthetic-transformation-001"),
        ("operation", "synthetic-byte-reversal"),
        ("operation_version", "1"),
        ("inputs", ({"subject_kind": "exact_artifact"},)),
        ("outputs", ({"subject_kind": "exact_artifact"},)),
        ("lossiness", "lossless"),
        ("reversibility", "reversible"),
        ("parameter_record", {"format_name": "synthetic-record"}),
    ),
)
def test_transformation_requires_typed_nested_python_values(
    field: str,
    raw_value: object,
) -> None:
    payload = _model_payload(_transformation(parameter_record=_synthetic_reference(70)))
    payload[field] = raw_value
    with pytest.raises(ValidationError):
        EvidenceTransformation.model_validate(payload)


@pytest.mark.parametrize(
    "json_value",
    (
        "2026-08-09T12:00:00Z",
        "2026-08-09T12:00:00+00:00",
        "2026-08-09T12:00:00.123456Z",
    ),
)
def test_transformation_accepts_asserted_utc_json_and_normalizes(
    json_value: str,
) -> None:
    semantic = cast(dict[str, object], _transformation().model_dump(mode="json"))
    semantic["performed_at"] = json_value
    decoded = EvidenceTransformation.model_validate_json(json.dumps(semantic))
    assert decoded.performed_at.utcoffset() == timedelta(0)
    assert decoded.performed_at.tzinfo is UTC


@pytest.mark.parametrize(
    "json_value",
    (
        "2026-08-09T12:00:00",
        "2026-08-09 12:00:00Z",
        "2026-08-09T12:00:00+01:00",
        "2026-08-09T12:00:00-00:00",
        "2026-08-09T12:00:00z",
        "not-a-time",
        1,
        None,
    ),
)
def test_transformation_rejects_non_asserted_utc_json(json_value: object) -> None:
    semantic = cast(dict[str, object], _transformation().model_dump(mode="json"))
    semantic["performed_at"] = json_value
    with pytest.raises(ValidationError):
        EvidenceTransformation.model_validate_json(json.dumps(semantic))


def test_transformation_python_time_requires_aware_zero_offset() -> None:
    zero_offset = datetime(
        2026,
        8,
        9,
        12,
        0,
        tzinfo=timezone(timedelta(0), name="synthetic-zero"),
    )
    accepted = _transformation(performed_at=zero_offset)
    assert accepted.performed_at.tzinfo is UTC
    for invalid in (
        datetime(2026, 8, 9, 12, 0),
        datetime(2026, 8, 9, 12, 0, tzinfo=timezone(timedelta(hours=1))),
        datetime(2026, 8, 9, 12, 0, tzinfo=timezone(timedelta(hours=-1))),
    ):
        with pytest.raises(ValidationError):
            _transformation(performed_at=invalid)


def test_transformation_none_and_present_parameter_record_are_distinct() -> None:
    absent = _transformation(parameter_record=None)
    present = _transformation(parameter_record=_synthetic_reference(71))
    assert absent.parameter_record is None
    assert isinstance(present.parameter_record, DurableEvidenceRecordReference)
    assert absent != present


def test_transformation_revalidates_constructed_invalid_subject() -> None:
    invalid = TransformationSubject.model_construct(
        subject_kind="exact_artifact",
        artifact_identity=None,
        record_reference=None,
    )
    payload = _model_payload(_transformation())
    payload["inputs"] = (invalid,)
    with pytest.raises(ValidationError):
        EvidenceTransformation.model_validate(payload)


@pytest.mark.parametrize(
    "field",
    (
        "callback",
        "completeness",
        "envelope",
        "executor",
        "migration",
        "operation_parameters",
        "parameter_map",
        "publication",
        "request_id",
        "run_id",
        "runtime",
        "tool_identity",
    ),
)
def test_transformation_rejects_execution_config_and_later_slice_fields(
    field: str,
) -> None:
    semantic = cast(dict[str, object], _transformation().model_dump(mode="json"))
    semantic[field] = {}
    with pytest.raises(ValidationError):
        EvidenceTransformation.model_validate_json(json.dumps(semantic))


def test_transformation_is_frozen_and_does_not_mutate_subjects() -> None:
    input_subject = _artifact_subject(80)
    output_subject = _artifact_subject(81)
    transformation = _transformation(
        inputs=(input_subject,),
        outputs=(output_subject,),
    )
    assert input_subject == _artifact_subject(80)
    assert output_subject == _artifact_subject(81)
    with pytest.raises(ValidationError):
        cast(Any, transformation).operation = TransformationOperation.model_validate(
            "changed-operation"
        )


def _relationship(
    relationship_kind: str,
) -> EvidenceCorrection | EvidenceSupersession:
    if relationship_kind == "correction":
        return _canonical_correction()
    assert relationship_kind == "supersession"
    return _synthetic_supersession()


def _relationship_adapter() -> TypeAdapter[EvidenceCorrection | EvidenceSupersession]:
    return cast(
        TypeAdapter[EvidenceCorrection | EvidenceSupersession],
        TypeAdapter(EvidenceRecordRelationship),
    )


def _validate_no_io_surface(source: str) -> None:
    tree = ast.parse(source)
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
            "http",
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
        "environ",
        "getenv",
        "hash",
        "open",
        "read_bytes",
        "read_text",
        "run",
        "sha256",
        "write_bytes",
        "write_text",
    }
    calls = {
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    calls.update(
        node.func.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    )
    assert not forbidden_calls & calls

    definitions = {
        node.name.casefold()
        for node in ast.walk(tree)
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
    }
    assert (
        not {
            "canonical_bytes",
            "canonical_json",
            "execute_transformation",
            "hash_record",
            "load",
            "migrate",
            "persist",
            "read",
            "save",
            "serialize_bytes",
            "to_bytes",
            "write",
        }
        & definitions
    )


def test_optional_subject_fields_are_required_with_explicit_none() -> None:
    for field in ("artifact_identity", "record_reference"):
        assert TransformationSubject.model_fields[field].is_required()
    semantic = cast(dict[str, object], _artifact_subject().model_dump(mode="json"))
    for field in ("artifact_identity", "record_reference"):
        mutated = dict(semantic)
        mutated.pop(field)
        with pytest.raises(ValidationError):
            TransformationSubject.model_validate_json(json.dumps(mutated))


def test_transformation_enums_have_no_aliases_and_reject_invalid_json() -> None:
    assert tuple(TransformationLossiness.__members__) == (
        "LOSSLESS",
        "LOSSY",
        "UNKNOWN",
    )
    assert tuple(TransformationReversibility.__members__) == (
        "REVERSIBLE",
        "IRREVERSIBLE",
        "UNKNOWN",
    )
    for enum_type in (TransformationLossiness, TransformationReversibility):
        adapter = TypeAdapter(enum_type)
        for invalid in ("LOSSLESS", "reversable", "none", 1, True, None):
            with pytest.raises(ValidationError):
                adapter.validate_json(json.dumps(invalid), strict=True)


def test_transformation_revalidates_constructed_invalid_parameter_reference() -> None:
    invalid_parameter = DurableEvidenceRecordReference.model_construct(
        format_name=EvidenceRecordFormat.model_construct(root="INVALID"),
        format_version=EvidenceVersion.model_validate("1"),
        canonicalization=EvidenceCanonicalization.model_validate(
            CANONICAL_CANONICALIZATION
        ),
        sha256=ArtifactSha256Digest.model_validate("f" * 64),
        byte_length=ArtifactByteLength.model_validate(1),
    )
    payload = _model_payload(_transformation())
    payload["parameter_record"] = invalid_parameter
    with pytest.raises(ValidationError):
        EvidenceTransformation.model_validate(payload)


def test_correction_fields_types_config_and_requiredness_are_exact() -> None:
    assert (
        tuple(EvidenceCorrection.model_fields)
        == (EXPECTED_MODEL_FIELDS[EvidenceCorrection])
    )
    _assert_record_config(EvidenceCorrection)
    fields = EvidenceCorrection.model_fields
    assert get_args(fields["relationship_kind"].annotation) == ("correction",)
    assert fields["relationship_id"].annotation is EvidenceRelationId
    assert fields["target_record"].annotation is DurableEvidenceRecordReference
    assert fields["correction_record"].annotation is DurableEvidenceRecordReference
    for field in EXPECTED_MODEL_FIELDS[EvidenceCorrection][1:]:
        assert fields[field].is_required()


def test_canonical_correction_is_one_additive_explicit_edge() -> None:
    correction = _canonical_correction()
    assert correction.schema_version == 1
    assert correction.relationship_kind == "correction"
    assert correction.relationship_id.root == CANONICAL_RELATIONSHIP_ID
    assert correction.target_record == _target_reference()
    assert correction.correction_record == _correction_reference()
    assert correction.target_record != correction.correction_record
    assert correction.recorded_at == CANONICAL_RECORDED_AT
    assert not isinstance(correction, EvidenceSupersession)
    assert not hasattr(correction, "superseded_record")
    assert not hasattr(correction, "superseding_record")
    assert not hasattr(correction, "replacement")


def test_correction_semantic_json_round_trip_preserves_nested_types() -> None:
    correction = _canonical_correction()
    decoded = EvidenceCorrection.model_validate_json(correction.model_dump_json())
    assert decoded == correction
    assert decoded is not correction
    assert isinstance(decoded.relationship_id, EvidenceRelationId)
    assert isinstance(decoded.target_record, DurableEvidenceRecordReference)
    assert isinstance(decoded.correction_record, DurableEvidenceRecordReference)
    assert decoded.target_record is not correction.target_record
    assert decoded.correction_record is not correction.correction_record


def test_correction_target_swap_changes_but_does_not_invalidate_the_edge() -> None:
    correction = _canonical_correction()
    swapped = EvidenceCorrection(
        relationship_kind="correction",
        relationship_id=correction.relationship_id,
        target_record=correction.correction_record,
        correction_record=correction.target_record,
        recorded_at=correction.recorded_at,
    )
    assert swapped != correction
    assert swapped.target_record == correction.correction_record
    assert swapped.correction_record == correction.target_record


def test_same_durable_records_may_participate_in_multiple_corrections() -> None:
    first = _canonical_correction()
    second = EvidenceCorrection(
        relationship_kind="correction",
        relationship_id=EvidenceRelationId.model_validate(
            "s04-c01-acquisition-closure-followup"
        ),
        target_record=first.target_record,
        correction_record=first.correction_record,
        recorded_at=first.recorded_at + timedelta(seconds=1),
    )
    assert first.target_record == second.target_record
    assert first.correction_record == second.correction_record
    assert first.relationship_id != second.relationship_id
    assert first != second


def test_correction_rejects_self_relationship() -> None:
    target = _target_reference()
    with pytest.raises(ValidationError):
        EvidenceCorrection(
            relationship_kind="correction",
            relationship_id=EvidenceRelationId.model_validate(
                CANONICAL_RELATIONSHIP_ID
            ),
            target_record=target,
            correction_record=target,
            recorded_at=CANONICAL_RECORDED_AT,
        )


@pytest.mark.parametrize(
    "field",
    (
        "relationship_kind",
        "relationship_id",
        "target_record",
        "correction_record",
        "recorded_at",
    ),
)
def test_correction_requires_every_explicit_field(field: str) -> None:
    semantic = cast(dict[str, object], _canonical_correction().model_dump(mode="json"))
    semantic.pop(field)
    with pytest.raises(ValidationError):
        EvidenceCorrection.model_validate_json(json.dumps(semantic))


@pytest.mark.parametrize(
    ("field", "raw_value"),
    (
        ("relationship_id", CANONICAL_RELATIONSHIP_ID),
        ("target_record", _target_reference().model_dump(mode="json")),
        ("correction_record", _correction_reference().model_dump(mode="json")),
        ("recorded_at", "2026-07-30T19:17:09.655780Z"),
    ),
)
def test_correction_requires_typed_nested_python_values(
    field: str,
    raw_value: object,
) -> None:
    payload = _model_payload(_canonical_correction())
    payload[field] = raw_value
    with pytest.raises(ValidationError):
        EvidenceCorrection.model_validate(payload)


@pytest.mark.parametrize(
    "relationship_kind",
    ("supersession", "Correction", "replacement", "", 1, None),
)
def test_correction_rejects_wrong_discriminator(relationship_kind: object) -> None:
    semantic = cast(dict[str, object], _canonical_correction().model_dump(mode="json"))
    semantic["relationship_kind"] = relationship_kind
    with pytest.raises(ValidationError):
        EvidenceCorrection.model_validate_json(json.dumps(semantic))


@pytest.mark.parametrize(
    "field",
    (
        "deletion",
        "findings",
        "json_patch",
        "latest",
        "migration",
        "omission",
        "path",
        "publication",
        "replacement",
        "request_id",
        "source",
        "superseded_record",
        "superseding_record",
        "uri",
    ),
)
def test_correction_rejects_copied_details_supersession_and_later_fields(
    field: str,
) -> None:
    semantic = cast(dict[str, object], _canonical_correction().model_dump(mode="json"))
    semantic[field] = []
    with pytest.raises(ValidationError):
        EvidenceCorrection.model_validate_json(json.dumps(semantic))


def test_correction_revalidates_constructed_invalid_target_reference() -> None:
    target = _target_reference()
    invalid_target = DurableEvidenceRecordReference.model_construct(
        schema_version=target.schema_version,
        format_name=EvidenceRecordFormat.model_construct(root="INVALID"),
        format_version=target.format_version,
        canonicalization=target.canonicalization,
        sha256=target.sha256,
        byte_length=target.byte_length,
    )
    payload = _model_payload(_canonical_correction())
    payload["target_record"] = invalid_target
    with pytest.raises(ValidationError):
        EvidenceCorrection.model_validate(payload)


def test_supersession_fields_types_config_and_requiredness_are_exact() -> None:
    assert (
        tuple(EvidenceSupersession.model_fields)
        == (EXPECTED_MODEL_FIELDS[EvidenceSupersession])
    )
    _assert_record_config(EvidenceSupersession)
    fields = EvidenceSupersession.model_fields
    assert get_args(fields["relationship_kind"].annotation) == ("supersession",)
    assert fields["relationship_id"].annotation is EvidenceRelationId
    assert fields["superseded_record"].annotation is DurableEvidenceRecordReference
    assert fields["superseding_record"].annotation is DurableEvidenceRecordReference
    for field in EXPECTED_MODEL_FIELDS[EvidenceSupersession][1:]:
        assert fields[field].is_required()


def test_synthetic_supersession_preserves_both_records_without_deletion() -> None:
    supersession = _synthetic_supersession()
    assert supersession.schema_version == 1
    assert supersession.relationship_kind == "supersession"
    assert supersession.relationship_id.root == "synthetic-supersession-001"
    assert supersession.superseded_record == _synthetic_reference(11)
    assert supersession.superseding_record == _synthetic_reference(12)
    assert supersession.superseded_record != supersession.superseding_record
    assert supersession.recorded_at == SYNTHETIC_PERFORMED_AT
    assert not isinstance(supersession, EvidenceCorrection)
    assert not hasattr(supersession, "delete_prior")
    assert not hasattr(supersession, "latest")
    assert not hasattr(supersession, "current")


def test_supersession_semantic_json_round_trip_preserves_nested_types() -> None:
    supersession = _synthetic_supersession()
    decoded = EvidenceSupersession.model_validate_json(supersession.model_dump_json())
    assert decoded == supersession
    assert decoded is not supersession
    assert isinstance(decoded.relationship_id, EvidenceRelationId)
    assert isinstance(decoded.superseded_record, DurableEvidenceRecordReference)
    assert isinstance(decoded.superseding_record, DurableEvidenceRecordReference)


def test_supersession_rejects_self_edge() -> None:
    prior = _synthetic_reference(11)
    with pytest.raises(ValidationError):
        EvidenceSupersession(
            relationship_kind="supersession",
            relationship_id=EvidenceRelationId.model_validate(
                "synthetic-self-supersession"
            ),
            superseded_record=prior,
            superseding_record=prior,
            recorded_at=SYNTHETIC_PERFORMED_AT,
        )


def test_two_supersession_edges_do_not_infer_transitive_closure() -> None:
    first = EvidenceSupersession(
        relationship_kind="supersession",
        relationship_id=EvidenceRelationId.model_validate("synthetic-a-to-b"),
        superseded_record=_synthetic_reference(101),
        superseding_record=_synthetic_reference(102),
        recorded_at=SYNTHETIC_PERFORMED_AT,
    )
    second = EvidenceSupersession(
        relationship_kind="supersession",
        relationship_id=EvidenceRelationId.model_validate("synthetic-b-to-c"),
        superseded_record=_synthetic_reference(102),
        superseding_record=_synthetic_reference(103),
        recorded_at=SYNTHETIC_PERFORMED_AT + timedelta(seconds=1),
    )
    assert first.superseding_record == second.superseded_record
    assert first.superseded_record != second.superseding_record
    assert not hasattr(first, "transitive_superseding_record")
    assert not hasattr(second, "cycle_state")


@pytest.mark.parametrize(
    "field",
    (
        "relationship_kind",
        "relationship_id",
        "superseded_record",
        "superseding_record",
        "recorded_at",
    ),
)
def test_supersession_requires_every_explicit_field(field: str) -> None:
    semantic = cast(
        dict[str, object],
        _synthetic_supersession().model_dump(mode="json"),
    )
    semantic.pop(field)
    with pytest.raises(ValidationError):
        EvidenceSupersession.model_validate_json(json.dumps(semantic))


@pytest.mark.parametrize(
    ("field", "raw_value"),
    (
        ("relationship_id", "synthetic-supersession-001"),
        ("superseded_record", _synthetic_reference(11).model_dump(mode="json")),
        ("superseding_record", _synthetic_reference(12).model_dump(mode="json")),
        ("recorded_at", "2026-08-09T12:00:00Z"),
    ),
)
def test_supersession_requires_typed_nested_python_values(
    field: str,
    raw_value: object,
) -> None:
    payload = _model_payload(_synthetic_supersession())
    payload[field] = raw_value
    with pytest.raises(ValidationError):
        EvidenceSupersession.model_validate(payload)


@pytest.mark.parametrize(
    "relationship_kind",
    ("correction", "Supersession", "replacement", "", 1, None),
)
def test_supersession_rejects_wrong_discriminator(
    relationship_kind: object,
) -> None:
    semantic = cast(
        dict[str, object],
        _synthetic_supersession().model_dump(mode="json"),
    )
    semantic["relationship_kind"] = relationship_kind
    with pytest.raises(ValidationError):
        EvidenceSupersession.model_validate_json(json.dumps(semantic))


@pytest.mark.parametrize(
    "field",
    (
        "correction_record",
        "cycle_graph",
        "delete_prior",
        "deletion",
        "latest",
        "migration",
        "path",
        "publication",
        "replacement",
        "target_record",
        "transitive",
        "uri",
    ),
)
def test_supersession_rejects_correction_deletion_graph_and_later_fields(
    field: str,
) -> None:
    semantic = cast(
        dict[str, object],
        _synthetic_supersession().model_dump(mode="json"),
    )
    semantic[field] = True
    with pytest.raises(ValidationError):
        EvidenceSupersession.model_validate_json(json.dumps(semantic))


@pytest.mark.parametrize("relationship_kind", ("correction", "supersession"))
@pytest.mark.parametrize(
    "json_value",
    (
        "2026-08-09T12:00:00Z",
        "2026-08-09T12:00:00+00:00",
        "2026-08-09T12:00:00.123456Z",
    ),
)
def test_relationships_accept_asserted_utc_json(
    relationship_kind: str,
    json_value: str,
) -> None:
    relation = _relationship(relationship_kind)
    semantic = cast(dict[str, object], relation.model_dump(mode="json"))
    semantic["recorded_at"] = json_value
    model = (
        EvidenceCorrection
        if relationship_kind == "correction"
        else EvidenceSupersession
    )
    decoded = model.model_validate_json(json.dumps(semantic))
    assert decoded.recorded_at.utcoffset() == timedelta(0)
    assert decoded.recorded_at.tzinfo is UTC


@pytest.mark.parametrize("relationship_kind", ("correction", "supersession"))
@pytest.mark.parametrize(
    "json_value",
    (
        "2026-08-09T12:00:00",
        "2026-08-09 12:00:00Z",
        "2026-08-09T12:00:00+01:00",
        "2026-08-09T12:00:00-00:00",
        "2026-08-09T12:00:00z",
        "not-a-time",
        1,
        None,
    ),
)
def test_relationships_reject_non_asserted_utc_json(
    relationship_kind: str,
    json_value: object,
) -> None:
    relation = _relationship(relationship_kind)
    semantic = cast(dict[str, object], relation.model_dump(mode="json"))
    semantic["recorded_at"] = json_value
    model = (
        EvidenceCorrection
        if relationship_kind == "correction"
        else EvidenceSupersession
    )
    with pytest.raises(ValidationError):
        model.model_validate_json(json.dumps(semantic))


@pytest.mark.parametrize("relationship_kind", ("correction", "supersession"))
def test_relationship_python_time_requires_aware_zero_offset(
    relationship_kind: str,
) -> None:
    relation = _relationship(relationship_kind)
    payload = _model_payload(relation)
    model = (
        EvidenceCorrection
        if relationship_kind == "correction"
        else EvidenceSupersession
    )
    zero_offset = datetime(
        2026,
        8,
        9,
        12,
        0,
        tzinfo=timezone(timedelta(0), name="synthetic-zero"),
    )
    payload["recorded_at"] = zero_offset
    accepted = model.model_validate(payload)
    assert accepted.recorded_at.tzinfo is UTC
    for invalid in (
        datetime(2026, 8, 9, 12, 0),
        datetime(2026, 8, 9, 12, 0, tzinfo=timezone(timedelta(hours=1))),
        datetime(2026, 8, 9, 12, 0, tzinfo=timezone(timedelta(hours=-1))),
    ):
        payload["recorded_at"] = invalid
        with pytest.raises(ValidationError):
            model.model_validate(payload)


def test_relationship_union_restores_exact_concrete_models_from_json() -> None:
    adapter = _relationship_adapter()
    for relation, expected_type in (
        (_canonical_correction(), EvidenceCorrection),
        (_synthetic_supersession(), EvidenceSupersession),
    ):
        decoded = adapter.validate_json(relation.model_dump_json(), strict=True)
        assert type(decoded) is expected_type
        assert decoded == relation
        assert json.loads(adapter.dump_json(decoded)) == json.loads(
            relation.model_dump_json()
        )


@pytest.mark.parametrize(
    ("relationship_kind", "mutation"),
    (
        ("correction", "missing"),
        ("correction", "unknown"),
        ("correction", "wrong-shape"),
        ("supersession", "missing"),
        ("supersession", "unknown"),
        ("supersession", "wrong-shape"),
    ),
)
def test_relationship_union_rejects_missing_unknown_or_wrong_discriminator_shape(
    relationship_kind: str,
    mutation: str,
) -> None:
    adapter = _relationship_adapter()
    relation = _relationship(relationship_kind)
    semantic = cast(dict[str, object], relation.model_dump(mode="json"))
    if mutation == "missing":
        semantic.pop("relationship_kind")
    elif mutation == "unknown":
        semantic["relationship_kind"] = "replacement"
    else:
        semantic["relationship_kind"] = (
            "supersession" if relationship_kind == "correction" else "correction"
        )
    with pytest.raises(ValidationError):
        adapter.validate_json(json.dumps(semantic), strict=True)


def test_relationship_union_never_first_match_collapses_concrete_types() -> None:
    adapter = _relationship_adapter()
    correction = adapter.validate_json(_canonical_correction().model_dump_json())
    supersession = adapter.validate_json(_synthetic_supersession().model_dump_json())
    assert isinstance(correction, EvidenceCorrection)
    assert not isinstance(correction, EvidenceSupersession)
    assert isinstance(supersession, EvidenceSupersession)
    assert not isinstance(supersession, EvidenceCorrection)
    assert correction.relationship_kind == "correction"
    assert supersession.relationship_kind == "supersession"
    assert correction.relationship_id != supersession.relationship_id


def test_relationship_models_are_frozen_and_do_not_modify_referenced_records() -> None:
    target = _target_reference()
    correction_record = _correction_reference()
    target_before = target.model_dump_json()
    correction_before = correction_record.model_dump_json()
    relation = EvidenceCorrection(
        relationship_kind="correction",
        relationship_id=EvidenceRelationId.model_validate(CANONICAL_RELATIONSHIP_ID),
        target_record=target,
        correction_record=correction_record,
        recorded_at=CANONICAL_RECORDED_AT,
    )
    assert target.model_dump_json() == target_before
    assert correction_record.model_dump_json() == correction_before
    with pytest.raises(ValidationError):
        cast(Any, relation).relationship_kind = "supersession"


def test_canonical_acquisition_and_correction_files_are_exact_regular_bytes() -> None:
    acquisition_raw = _assert_exact_regular_file(
        ACQUISITION_PATH,
        byte_length=CANONICAL_ACQUISITION_LENGTH,
        digest=CANONICAL_ACQUISITION_SHA256,
    )
    correction_raw = _assert_exact_regular_file(
        CORRECTION_PATH,
        byte_length=CANONICAL_CORRECTION_LENGTH,
        digest=CANONICAL_CORRECTION_SHA256,
    )
    assert acquisition_raw.endswith(b"\n")
    assert not acquisition_raw.endswith(b"\n\n")
    assert correction_raw.endswith(b"\n")
    assert not correction_raw.endswith(b"\n\n")


def test_canonical_record_sidecars_are_exact_regular_and_verified() -> None:
    acquisition_sidecar = _assert_exact_regular_file(
        ACQUISITION_SIDECAR,
        byte_length=83,
        digest=CANONICAL_ACQUISITION_SIDECAR_SHA256,
    )
    correction_sidecar = _assert_exact_regular_file(
        CORRECTION_SIDECAR,
        byte_length=82,
        digest=CANONICAL_CORRECTION_SIDECAR_SHA256,
    )
    assert acquisition_sidecar == (
        f"{CANONICAL_ACQUISITION_SHA256}  acquisition.json\n".encode("ascii")
    )
    assert correction_sidecar == (
        f"{CANONICAL_CORRECTION_SHA256}  correction.json\n".encode("ascii")
    )


def test_canonical_source_pointers_construct_exact_durable_references() -> None:
    acquisition = _load_json(ACQUISITION_PATH)
    correction = _load_json(CORRECTION_PATH)
    acquisition_format = cast(dict[str, object], acquisition["format"])
    correction_format = cast(dict[str, object], correction["format"])
    correction_canonicalization = cast(
        dict[str, object], correction_format["canonicalization"]
    )
    target = cast(dict[str, object], correction["target_acquisition"])
    target_format = cast(dict[str, object], target["format"])
    target_record = cast(dict[str, object], target["acquisition_record"])

    assert acquisition_format == {
        "canonicalization": CANONICAL_CANONICALIZATION,
        "name": CANONICAL_FORMAT,
        "version": CANONICAL_VERSION,
    }
    assert correction_format["name"] == CANONICAL_CORRECTION_FORMAT
    assert correction_format["version"] == CANONICAL_VERSION
    assert correction_canonicalization["name"] == CANONICAL_CANONICALIZATION
    assert target_format == acquisition_format
    assert target_record["sha256"] == CANONICAL_ACQUISITION_SHA256
    assert target_record["byte_length"] == CANONICAL_ACQUISITION_LENGTH
    assert _target_reference().model_dump(mode="json") == {
        "schema_version": 1,
        "format_name": target_format["name"],
        "format_version": target_format["version"],
        "canonicalization": target_format["canonicalization"],
        "sha256": target_record["sha256"],
        "byte_length": target_record["byte_length"],
    }
    assert _correction_reference().model_dump(mode="json") == {
        "schema_version": 1,
        "format_name": correction_format["name"],
        "format_version": correction_format["version"],
        "canonicalization": correction_canonicalization["name"],
        "sha256": CANONICAL_CORRECTION_SHA256,
        "byte_length": CANONICAL_CORRECTION_LENGTH,
    }


def test_canonical_c01_facts_replay_as_exactly_one_additive_correction() -> None:
    correction_source = _load_json(CORRECTION_PATH)
    correction_facts = cast(dict[str, object], correction_source["correction"])
    assert correction_facts["id"] == CANONICAL_RELATIONSHIP_ID
    assert correction_facts["created_at"] == "2026-07-30T19:17:09.655780Z"
    assert correction_facts["status"] == "complete"

    relationship = _canonical_correction()
    canonical_relationships = (relationship,)
    canonical_transformations: tuple[EvidenceTransformation, ...] = ()
    canonical_supersessions: tuple[EvidenceSupersession, ...] = ()
    assert len(canonical_relationships) == 1
    assert (
        sum(isinstance(item, EvidenceCorrection) for item in canonical_relationships)
        == 1
    )
    assert canonical_transformations == ()
    assert canonical_supersessions == ()
    assert relationship.relationship_id.root == correction_facts["id"]
    assert relationship.recorded_at == CANONICAL_RECORDED_AT
    assert relationship.target_record == _target_reference()
    assert relationship.correction_record == _correction_reference()

    adapter = _relationship_adapter()
    restored = adapter.validate_json(relationship.model_dump_json())
    assert type(restored) is EvidenceCorrection
    assert restored == relationship


def test_canonical_sources_prove_zero_transformations_without_fabrication() -> None:
    acquisition = _load_json(ACQUISITION_PATH)
    correction = _load_json(CORRECTION_PATH)
    transformation_values = _collect_named_values(acquisition, "transformations")
    assert transformation_values == [[], [], []]
    assert _collect_named_values(correction, "transformations") == []
    assert all(value == [] for value in transformation_values)
    assert _collect_named_values(correction, "superseded_record") == []
    assert _collect_named_values(correction, "superseding_record") == []

    canonical_transformations: tuple[EvidenceTransformation, ...] = ()
    canonical_supersessions: tuple[EvidenceSupersession, ...] = ()
    assert canonical_transformations == ()
    assert canonical_supersessions == ()
    assert (
        TransformationOperation.model_validate("synthetic-record-normalization").root
        != CANONICAL_CANONICALIZATION
    )


def test_prepublication_candidate_is_not_fabricated_as_a_durable_relationship() -> None:
    correction = _load_json(CORRECTION_PATH)
    disposition = cast(dict[str, object], correction["sealed_candidate_disposition"])
    candidate = cast(dict[str, object], disposition["prior_candidate"])
    candidate_digest = (
        "895576d3d9de395421d946a604547b3d5071c3c9d82f9a58230e62c6e733747a"
    )
    assert candidate["acquisition_sha256"] == candidate_digest
    assert candidate["published"] is False
    assert candidate["operationally_closed"] is False
    canonical = _canonical_correction()
    referenced_digests = {
        canonical.target_record.sha256.root,
        canonical.correction_record.sha256.root,
    }
    assert referenced_digests == {
        CANONICAL_ACQUISITION_SHA256,
        CANONICAL_CORRECTION_SHA256,
    }
    assert candidate_digest not in referenced_digests
    assert not isinstance(canonical, EvidenceSupersession)


def test_correction_details_remain_only_in_the_referenced_correction_record() -> None:
    correction_source = _load_json(CORRECTION_PATH)
    correction_facts = cast(dict[str, object], correction_source["correction"])
    findings = cast(list[object], correction_facts["findings"])
    relationship = _canonical_correction()
    assert len(findings) == 4
    assert "findings" not in EvidenceCorrection.model_fields
    assert "json_patch" not in EvidenceCorrection.model_fields
    assert "omission" not in EvidenceCorrection.model_fields
    assert relationship.correction_record == _correction_reference()


def test_canonical_relationship_construction_does_not_rewrite_source_bytes() -> None:
    acquisition_before = ACQUISITION_PATH.read_bytes()
    correction_before = CORRECTION_PATH.read_bytes()
    relationship = _canonical_correction()
    assert relationship.target_record != relationship.correction_record
    assert ACQUISITION_PATH.read_bytes() == acquisition_before
    assert CORRECTION_PATH.read_bytes() == correction_before
    assert sha256(acquisition_before).hexdigest() == CANONICAL_ACQUISITION_SHA256
    assert sha256(correction_before).hexdigest() == CANONICAL_CORRECTION_SHA256


def test_no_migration_manifest_reader_writer_or_new_durable_file_is_inferred() -> None:
    correction = _load_json(CORRECTION_PATH)
    correction_facts = cast(dict[str, object], correction["correction"])
    s05_requirement = cast(
        dict[str, object], correction_facts["s05_reference_requirement"]
    )
    assert s05_requirement["relationship_manifest_created"] is False
    fields = set(EvidenceCorrection.model_fields)
    assert (
        not {
            "adapter",
            "loader",
            "migration",
            "path",
            "reader",
            "storage",
            "uri",
            "writer",
        }
        & fields
    )
    assert not (CORRECTION_ROOT / "relationship.json").exists()


def test_exact_record_byte_assertions_are_mutation_sensitive() -> None:
    for path, byte_length, digest in (
        (
            ACQUISITION_PATH,
            CANONICAL_ACQUISITION_LENGTH,
            CANONICAL_ACQUISITION_SHA256,
        ),
        (CORRECTION_PATH, CANONICAL_CORRECTION_LENGTH, CANONICAL_CORRECTION_SHA256),
    ):
        raw = path.read_bytes()
        mutated = raw[:-1] + b" "
        assert mutated != raw
        with pytest.raises(AssertionError):
            assert len(mutated) == byte_length and sha256(mutated).hexdigest() == digest


def test_evidence_surface_exports_public_ast_alias_base_and_caps_are_exact() -> None:
    source = EVIDENCE_SOURCE.read_text(encoding="utf-8")
    _validate_evidence_surface(source)
    assert tuple(evidence_module.__all__) == EXPECTED_EVIDENCE_EXPORTS
    assert len(evidence_module.__all__) == len(set(evidence_module.__all__)) == 58
    assert _parse_transformation_caps(source) == {
        "_MAX_TRANSFORMATION_INPUTS": MAX_TRANSFORMATION_INPUTS,
        "_MAX_TRANSFORMATION_OUTPUTS": MAX_TRANSFORMATION_OUTPUTS,
    }


def test_new_record_fields_are_exact_and_exclude_s06_plus_surface() -> None:
    observed_fields: set[str] = set()
    for model, expected in EXPECTED_MODEL_FIELDS.items():
        assert tuple(model.model_fields) == expected
        observed_fields.update(model.model_fields)
    assert not FORBIDDEN_S05_FIELDS & observed_fields
    assert set(DurableEvidenceRecordReference.model_fields) == {
        "schema_version",
        "format_name",
        "format_version",
        "canonicalization",
        "sha256",
        "byte_length",
    }
    assert set(TransformationSubject.model_fields) == {
        "schema_version",
        "subject_kind",
        "artifact_identity",
        "record_reference",
    }


def test_production_evidence_module_has_no_io_hashing_execution_or_persistence() -> (
    None
):
    source = EVIDENCE_SOURCE.read_text(encoding="utf-8")
    _validate_no_io_surface(source)


@pytest.mark.parametrize("mutation", ("missing-export", "unexpected-export"))
def test_s05_export_inventory_is_mutation_sensitive(mutation: str) -> None:
    source = EVIDENCE_SOURCE.read_text(encoding="utf-8")
    if mutation == "missing-export":
        mutated = source.replace('    "EvidenceRecordRelationship",\n', "", 1)
    else:
        mutated = source.replace(
            '    "EvidenceRecordRelationship",\n',
            '    "EvidenceRecordRelationship",\n    "EvidenceCompleteness",\n',
            1,
        )
    assert mutated != source
    with pytest.raises(AssertionError):
        _validate_evidence_surface(mutated)


@pytest.mark.parametrize(
    ("name", "value"),
    (
        ("_MAX_TRANSFORMATION_INPUTS", MAX_TRANSFORMATION_INPUTS),
        ("_MAX_TRANSFORMATION_OUTPUTS", MAX_TRANSFORMATION_OUTPUTS),
    ),
)
def test_transformation_cap_constants_are_mutation_sensitive(
    name: str,
    value: int,
) -> None:
    source = EVIDENCE_SOURCE.read_text(encoding="utf-8")
    mutated = source.replace(f"{name} = {value}", f"{name} = {value + 1}", 1)
    assert mutated != source
    with pytest.raises(AssertionError):
        _validate_evidence_surface(mutated)


def test_relationship_alias_discriminator_is_mutation_sensitive() -> None:
    source = EVIDENCE_SOURCE.read_text(encoding="utf-8")
    mutated = source
    for quote in ('"', "'"):
        needle = f"discriminator={quote}relationship_kind{quote}"
        if needle in mutated:
            mutated = mutated.replace(
                needle,
                f"discriminator={quote}kind{quote}",
                1,
            )
            break
    assert mutated != source
    with pytest.raises(AssertionError):
        _validate_evidence_surface(mutated)


@pytest.mark.parametrize("definition", sorted(FORBIDDEN_POST_S07_DEFINITIONS))
def test_s08_plus_definition_mutations_are_rejected(definition: str) -> None:
    source = EVIDENCE_SOURCE.read_text(encoding="utf-8")
    mutated = f"{source}\n\nclass {definition}:\n    pass\n"
    with pytest.raises(AssertionError):
        _validate_evidence_surface(mutated)


@pytest.mark.parametrize(
    "mutation",
    (
        "import os\n",
        "from pathlib import Path\n",
        "open('record.json')\n",
        "sha256(b'record')\n",
        "def execute_transformation():\n    pass\n",
        "def persist():\n    pass\n",
    ),
)
def test_no_io_surface_is_mutation_sensitive(mutation: str) -> None:
    source = EVIDENCE_SOURCE.read_text(encoding="utf-8")
    with pytest.raises(AssertionError):
        _validate_no_io_surface(f"{source}\n{mutation}")


@pytest.mark.parametrize("mutation", ("missing-evidence", "unexpected-extra"))
def test_current_source_inventory_is_mutation_sensitive(mutation: str) -> None:
    paths = set(EXPECTED_PRODUCTION_FILES)
    if mutation == "missing-evidence":
        paths.remove("src/faultatlas/domain/evidence.py")
    else:
        paths.add("src/faultatlas/domain/transformation.py")
    with pytest.raises(AssertionError):
        assert paths == EXPECTED_PRODUCTION_FILES


def test_package_root_export_boundary_is_mutation_sensitive() -> None:
    leaked_root = set(vars(faultatlas)) | {"EvidenceCorrection"}
    leaked_domain = set(vars(domain_package)) | {"EvidenceTransformation"}
    with pytest.raises(AssertionError):
        assert not set(EXPECTED_EVIDENCE_EXPORTS) & leaked_root
    with pytest.raises(AssertionError):
        assert not set(EXPECTED_EVIDENCE_EXPORTS) & leaked_domain


def test_artifact_snapshot_remains_unchanged_and_unrelated_to_s05_models() -> None:
    expected_fields = (
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
    assert tuple(ArtifactSnapshot.model_fields) == expected_fields
    for model in (
        DurableEvidenceRecordReference,
        TransformationSubject,
        EvidenceTransformation,
        EvidenceCorrection,
        EvidenceSupersession,
    ):
        assert not issubclass(model, ArtifactSnapshot)
    assert not issubclass(EvidenceEnvelope, ArtifactSnapshot)
    assert not issubclass(ArtifactSnapshot, EvidenceEnvelope)
    assert (set(ArtifactSnapshot.model_fields) - {"schema_version"}).isdisjoint(
        EvidenceEnvelope.model_fields
    )
    with pytest.raises(AssertionError):
        assert (*expected_fields, "relationship") == expected_fields


def test_correction_supersession_and_transformation_remain_outside_run_membership() -> (
    None
):
    fields = set(AcquisitionRequestMembership.model_fields) | set(
        AcquisitionRun.model_fields
    )
    assert (
        not {
            "correction",
            "relationship",
            "supersession",
            "transformation",
            "transformations",
        }
        & fields
    )


def test_artifact_identity_remains_independent_of_relationships() -> None:
    artifact_fields = set(ExactArtifactIdentity.model_fields) | set(
        ExactRetainedArtifact.model_fields
    )
    assert (
        not {
            "correction",
            "record_reference",
            "supersession",
            "transformation",
        }
        & artifact_fields
    )
    identity = _artifact_identity(401)
    transformation = _transformation(
        inputs=(
            TransformationSubject(
                subject_kind="exact_artifact",
                artifact_identity=identity,
                record_reference=None,
            ),
        ),
        outputs=(_artifact_subject(402),),
    )
    assert transformation.inputs[0].artifact_identity == identity
    assert tuple(ExactArtifactIdentity.model_fields) == (
        "schema_version",
        "digest",
        "byte_length",
    )
