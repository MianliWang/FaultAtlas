from __future__ import annotations

import ast
import json
import stat
from datetime import UTC, datetime, timedelta, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any, cast

import pytest
from pydantic import TypeAdapter, ValidationError

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
    ExactArtifactIdentity,
    ExactRetainedArtifact,
    HttpStatusCode,
    MediaType,
    RequestQueryParameter,
    ResponseRepresentationObservation,
    ResponseRepresentationState,
    RetrievalMethod,
    RetrievalRequestControls,
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
ACQUISITION_SIDECAR = ACQUISITION_ROOT / "acquisition.sha256"

CANONICAL_RUN_ID = "run-0001-s04-v1-base-4c9cde74-head-690a63b9"
CANONICAL_STARTED_AT = datetime(2026, 7, 24, 11, 3, 15, 269222, tzinfo=UTC)
CANONICAL_SEALED_AT = datetime(2026, 7, 30, 8, 28, 22, 796982, tzinfo=UTC)
CANONICAL_ACQUISITION_SHA256 = (
    "1c29093bf1537e9b824a18df1848b71a8da014f544bc9f385707eb0e000a1318"
)
DIFF_DIGEST = "dca87a4df1edb2d1acb3fc821724483ee874c2feba6525b2c21e79cb3e8f7312"
LICENSE_DIGEST = "a1ebce15afc7b5cf98c7c6de512d1959d4bf61db8c6bf2f111286d483b40a997"

SYNTHETIC_RUN_ID = "run-synthetic-complete-001"
SYNTHETIC_PARTIAL_RUN_ID = "run-synthetic-partial-001"
SYNTHETIC_STARTED_AT = datetime(2026, 8, 9, 12, 0, 0, tzinfo=UTC)
SYNTHETIC_SEALED_AT = datetime(2026, 8, 9, 12, 1, 0, tzinfo=UTC)

MAX_RETAINED_ARTIFACTS = 64
MAX_ACQUISITION_REQUESTS = 4096

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
    "src/faultatlas/domain/history.py",
    "src/faultatlas/domain/identity.py",
    "src/faultatlas/domain/revision.py",
    "src/faultatlas/domain/snapshot.py",
    "src/faultatlas/domain/snapshot_evidence_link.py",
    "src/faultatlas/domain/source.py",
}
PREDECESSOR_LOCKS = {
    "src/faultatlas/domain/source.py": (
        4336,
        "034e53fd58212f0e34376bbc790fc3e74057031aaed4d7d89fb67904bdd380bf",
    ),
    "src/faultatlas/domain/identity.py": (
        22684,
        "e2d604f4e86a3b94c2b1b1875fa6e8f408778cbadd829b3fe9e934dd53f2d169",
    ),
    "src/faultatlas/domain/compatibility.py": (
        18898,
        "f4ef93d432da4fd0ebf05237c164e10d8f18eceaf538ff4ddc3372565b5c46db",
    ),
    "src/faultatlas/domain/revision.py": (
        27342,
        "7bea28086b345f6c1b4eeebe9c483924e60521e2f3e78954b272ab3c42acacaa",
    ),
}
FORBIDDEN_S05_RELATIONSHIP_FIELDS = {
    "adapter",
    "baseline_revision",
    "completeness",
    "corpus_path",
    "correction",
    "envelope",
    "failure_reason",
    "http_client",
    "latest",
    "missing_evidence",
    "next_run",
    "omission",
    "policy",
    "prior_run",
    "procedure",
    "publication",
    "rate_limit",
    "request_budget",
    "required_requests",
    "retry_of",
    "seal_digest",
    "storage",
    "supersession",
    "tool_identity",
    "transformation",
}
FORBIDDEN_POST_S07_DEFINITIONS = {
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
    "SupersessionRecord",
    "TransformationRecord",
}


def _run_id(value: str = SYNTHETIC_RUN_ID) -> AcquisitionRunId:
    return AcquisitionRunId.model_validate(value)


def _request_id(
    ordinal: int = 1,
    *,
    run_id: str = SYNTHETIC_RUN_ID,
) -> RetrievalRequestId:
    return RetrievalRequestId(
        acquisition_run_id=_run_id(run_id),
        request_ordinal=RetrievalRequestOrdinal.model_validate(ordinal),
    )


def _authority() -> ProviderAuthority:
    return ProviderAuthority(
        provider=ProviderKey.model_validate("github"),
        role=AuthorityRole.RETRIEVAL,
        host="api.github.com",
    )


def _reference(
    request_id: RetrievalRequestId | None = None,
    *,
    started_at: datetime = SYNTHETIC_STARTED_AT,
) -> RetrievalRequestReference:
    return RetrievalRequestReference(
        request_id=request_id or _request_id(),
        authority=_authority(),
        method=RetrievalMethod.GET,
        route_path=RetrievalRoutePath.model_validate("/repos/example/project"),
        started_at=started_at,
    )


def _controls() -> RetrievalRequestControls:
    return RetrievalRequestControls(
        query_delimiter_present=True,
        query_parameters=(
            RequestQueryParameter(
                name="page",
                value="1",
                value_delimiter_present=True,
            ),
        ),
        requested_media_type=MediaType.model_validate("application/json"),
        api_version=ApiVersion.model_validate("2026-03-10"),
    )


def _observation(
    request_id: RetrievalRequestId | None = None,
    *,
    completed_at: datetime | None = None,
) -> ResponseRepresentationObservation:
    return ResponseRepresentationObservation(
        request_id=request_id or _request_id(),
        state=ResponseRepresentationState.OBSERVED,
        completed_at=completed_at or SYNTHETIC_STARTED_AT + timedelta(seconds=1),
        status_code=HttpStatusCode.model_validate(200),
        observed_media_type=MediaType.model_validate("application/json"),
        media_type_parameters=(),
        content_encodings=(),
    )


def _artifact_identity(
    index: int = 1,
    *,
    scope: str = "synthetic-http-entity-body",
    digest: str | None = None,
    byte_length: int | None = None,
) -> ExactArtifactIdentity:
    digest_value = digest or f"{index:064x}"
    return ExactArtifactIdentity(
        digest=ArtifactDigest(
            algorithm=ArtifactDigestAlgorithm.SHA256,
            scope=ArtifactDigestScope.model_validate(scope),
            value=ArtifactSha256Digest.model_validate(digest_value),
        ),
        byte_length=ArtifactByteLength.model_validate(
            index if byte_length is None else byte_length
        ),
    )


def _artifact(
    request_id: RetrievalRequestId | None = None,
    *,
    identity: ExactArtifactIdentity | None = None,
    index: int = 1,
) -> ExactRetainedArtifact:
    return ExactRetainedArtifact(
        request_id=request_id or _request_id(),
        artifact_identity=identity or _artifact_identity(index),
        retention_mode=ArtifactRetentionMode.EXACT_UNMODIFIED_BYTES,
    )


def _membership(
    ordinal: int = 1,
    *,
    run_id: str = SYNTHETIC_RUN_ID,
    request_reference: RetrievalRequestReference | None = None,
    request_controls: RetrievalRequestControls | None = None,
    response_observation: ResponseRepresentationObservation | None = None,
    retained_artifacts: tuple[ExactRetainedArtifact, ...] | None = None,
) -> AcquisitionRequestMembership:
    return AcquisitionRequestMembership(
        request_id=_request_id(ordinal, run_id=run_id),
        request_reference=request_reference,
        request_controls=request_controls,
        response_observation=response_observation,
        retained_artifacts=retained_artifacts,
    )


def _run(
    requests: tuple[AcquisitionRequestMembership, ...] = (),
    *,
    run_id: str = SYNTHETIC_RUN_ID,
    status: AcquisitionRunStatus = AcquisitionRunStatus.COMPLETE,
    started_at: datetime = SYNTHETIC_STARTED_AT,
    sealed_at: datetime = SYNTHETIC_SEALED_AT,
    request_count: int | None = None,
) -> AcquisitionRun:
    return AcquisitionRun(
        run_id=_run_id(run_id),
        status=status,
        started_at=started_at,
        sealed_at=sealed_at,
        request_count=len(requests) if request_count is None else request_count,
        requests=requests,
    )


def _model_payload(model: object) -> dict[str, object]:
    typed_model = cast(Any, model)
    return {
        field: cast(object, getattr(typed_model, field))
        for field in typed_model.__class__.model_fields
    }


def _load_acquisition() -> dict[str, Any]:
    loaded = json.loads(ACQUISITION_PATH.read_bytes())
    assert isinstance(loaded, dict)
    return cast(dict[str, Any], loaded)


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


def _parse_private_caps(source: str) -> dict[str, int]:
    expected = {
        "_MAX_RETAINED_ARTIFACTS_PER_REQUEST",
        "_MAX_REQUESTS_PER_ACQUISITION_RUN",
    }
    observed: dict[str, int] = {}
    for node in ast.parse(source).body:
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        target = node.targets[0]
        if not isinstance(target, ast.Name) or target.id not in expected:
            continue
        value = cast(object, ast.literal_eval(node.value))
        assert type(value) is int
        observed[target.id] = value
    assert set(observed) == expected
    return observed


def _validate_evidence_surface(source: str) -> None:
    assert _parse_exports(source) == EXPECTED_EVIDENCE_EXPORTS
    tree = ast.parse(source)
    public_definitions = tuple(
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
    assert public_definitions == EXPECTED_EVIDENCE_EXPORTS
    definitions = {
        node.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
    }
    definitions.update(
        node.name.id for node in ast.walk(tree) if isinstance(node, ast.TypeAlias)
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
    assert len(public_classes) == 55
    assert public_functions == {
        "project_evidence_envelope_to_legacy_artifact_snapshot",
        "wrap_legacy_artifact_snapshot",
    }
    assert {node.name.id for node in tree.body if isinstance(node, ast.TypeAlias)} == {
        "EvidenceRecordRelationship"
    }
    assert not definitions & FORBIDDEN_POST_S07_DEFINITIONS
    assert _parse_private_caps(source) == {
        "_MAX_RETAINED_ARTIFACTS_PER_REQUEST": MAX_RETAINED_ARTIFACTS,
        "_MAX_REQUESTS_PER_ACQUISITION_RUN": MAX_ACQUISITION_REQUESTS,
    }


def _assert_strict_record_config(
    model: type[AcquisitionRequestMembership] | type[AcquisitionRun],
) -> None:
    assert model.model_config == {
        "extra": "forbid",
        "frozen": True,
        "revalidate_instances": "always",
        "strict": True,
        "validate_default": True,
    }


def _canonical_artifact(
    *,
    ordinal: int,
    scope: str,
    digest: str,
    byte_length: int,
) -> ExactRetainedArtifact:
    return _artifact(
        _request_id(ordinal, run_id=CANONICAL_RUN_ID),
        identity=_artifact_identity(
            scope=scope,
            digest=digest,
            byte_length=byte_length,
        ),
    )


def _canonical_run() -> AcquisitionRun:
    artifacts = {
        30: _canonical_artifact(
            ordinal=30,
            scope="github-compare-diff-http-entity-body",
            digest=DIFF_DIGEST,
            byte_length=1640,
        ),
        32: _canonical_artifact(
            ordinal=32,
            scope="git-blob-content",
            digest=LICENSE_DIGEST,
            byte_length=1096,
        ),
    }
    memberships = tuple(
        _membership(
            ordinal,
            run_id=CANONICAL_RUN_ID,
            retained_artifacts=(artifacts[ordinal],) if ordinal in artifacts else (),
        )
        for ordinal in range(1, 33)
    )
    return _run(
        memberships,
        run_id=CANONICAL_RUN_ID,
        status=AcquisitionRunStatus.COMPLETE,
        started_at=CANONICAL_STARTED_AT,
        sealed_at=CANONICAL_SEALED_AT,
    )


def test_acquisition_run_status_vocabulary_and_semantic_json_are_exact() -> None:
    adapter = TypeAdapter(AcquisitionRunStatus)
    assert tuple(AcquisitionRunStatus) == (
        AcquisitionRunStatus.COMPLETE,
        AcquisitionRunStatus.PARTIAL,
    )
    assert [value.value for value in AcquisitionRunStatus] == ["complete", "partial"]
    assert adapter.validate_python(AcquisitionRunStatus.COMPLETE, strict=True) is (
        AcquisitionRunStatus.COMPLETE
    )
    assert (
        adapter.validate_json('"partial"', strict=True) is AcquisitionRunStatus.PARTIAL
    )


@pytest.mark.parametrize(
    "value",
    (
        "complete",
        "partial",
        "COMPLETE",
        "running",
        "pending",
        "failed",
        "cancelled",
        "published",
        "sealed",
        None,
    ),
)
def test_acquisition_run_status_rejects_untyped_or_unknown_python_values(
    value: object,
) -> None:
    with pytest.raises(ValidationError):
        TypeAdapter(AcquisitionRunStatus).validate_python(value, strict=True)


@pytest.mark.parametrize(
    "value",
    ("COMPLETE", "running", "pending", "failed", "cancelled", "published", "sealed"),
)
def test_acquisition_run_status_rejects_unknown_json_values(value: str) -> None:
    with pytest.raises(ValidationError):
        TypeAdapter(AcquisitionRunStatus).validate_json(json.dumps(value), strict=True)


def test_membership_has_exact_required_fields_and_strict_configuration() -> None:
    assert tuple(AcquisitionRequestMembership.model_fields) == (
        "schema_version",
        "request_id",
        "request_reference",
        "request_controls",
        "response_observation",
        "retained_artifacts",
    )
    assert not AcquisitionRequestMembership.model_fields["schema_version"].is_required()
    assert all(
        AcquisitionRequestMembership.model_fields[field].is_required()
        for field in (
            "request_id",
            "request_reference",
            "request_controls",
            "response_observation",
            "retained_artifacts",
        )
    )
    _assert_strict_record_config(AcquisitionRequestMembership)


def test_request_id_only_membership_preserves_explicit_unknown_components() -> None:
    membership = _membership()
    assert membership.request_id == _request_id()
    assert membership.request_reference is None
    assert membership.request_controls is None
    assert membership.response_observation is None
    assert membership.retained_artifacts is None
    assert membership.model_dump(mode="json") == {
        "schema_version": 1,
        "request_id": {
            "schema_version": 1,
            "acquisition_run_id": SYNTHETIC_RUN_ID,
            "request_ordinal": 1,
        },
        "request_reference": None,
        "request_controls": None,
        "response_observation": None,
        "retained_artifacts": None,
    }


def test_none_known_empty_and_nonempty_artifact_membership_remain_distinct() -> None:
    unknown = _membership(retained_artifacts=None)
    known_empty = _membership(retained_artifacts=())
    one = _membership(retained_artifacts=(_artifact(),))
    multiple = _membership(retained_artifacts=(_artifact(index=1), _artifact(index=2)))

    assert unknown.retained_artifacts is None
    assert known_empty.retained_artifacts == ()
    assert one.retained_artifacts == (_artifact(),)
    assert (
        len(cast(tuple[ExactRetainedArtifact, ...], multiple.retained_artifacts)) == 2
    )
    assert (
        len(
            {
                unknown.model_dump_json(),
                known_empty.model_dump_json(),
                one.model_dump_json(),
                multiple.model_dump_json(),
            }
        )
        == 4
    )


@pytest.mark.parametrize(
    "component",
    ("request_reference", "request_controls", "response_observation"),
)
def test_each_optional_linked_component_can_be_present_separately(
    component: str,
) -> None:
    request_id = _request_id()
    values: dict[str, object] = {
        "request_reference": None,
        "request_controls": None,
        "response_observation": None,
    }
    values[component] = {
        "request_reference": _reference(request_id),
        "request_controls": _controls(),
        "response_observation": _observation(request_id),
    }[component]
    membership = AcquisitionRequestMembership(
        request_id=request_id,
        request_reference=cast(
            RetrievalRequestReference | None, values["request_reference"]
        ),
        request_controls=cast(
            RetrievalRequestControls | None, values["request_controls"]
        ),
        response_observation=cast(
            ResponseRepresentationObservation | None,
            values["response_observation"],
        ),
        retained_artifacts=None,
    )
    assert getattr(membership, component) == values[component]
    assert getattr(membership, component) is not values[component]


def test_membership_accepts_all_components_without_merging_evidence_layers() -> None:
    request_id = _request_id()
    reference = _reference(request_id)
    controls = _controls()
    observation = _observation(request_id)
    artifact = _artifact(request_id)
    membership = AcquisitionRequestMembership(
        request_id=request_id,
        request_reference=reference,
        request_controls=controls,
        response_observation=observation,
        retained_artifacts=(artifact,),
    )

    assert membership.request_reference == reference
    assert membership.request_controls == controls
    assert membership.response_observation == observation
    assert membership.retained_artifacts == (artifact,)
    assert "request_id" not in RetrievalRequestControls.model_fields
    assert set(ResponseRepresentationObservation.model_fields).isdisjoint(
        {"status", "retained_artifacts", "request_count", "requests"}
    )
    assert artifact.artifact_identity == _artifact_identity()


def test_membership_semantic_json_round_trip_reconstructs_typed_tuple() -> None:
    request_id = _request_id()
    membership = AcquisitionRequestMembership(
        request_id=request_id,
        request_reference=_reference(request_id),
        request_controls=_controls(),
        response_observation=_observation(request_id),
        retained_artifacts=(
            _artifact(request_id, index=1),
            _artifact(request_id, index=2),
        ),
    )
    encoded = membership.model_dump_json()
    decoded = AcquisitionRequestMembership.model_validate_json(encoded)

    assert decoded == membership
    assert type(decoded.retained_artifacts) is tuple
    assert decoded.model_dump_json() == encoded


@pytest.mark.parametrize(
    "field",
    (
        "request_id",
        "request_reference",
        "request_controls",
        "response_observation",
        "retained_artifacts",
    ),
)
def test_membership_rejects_omitted_required_fields(field: str) -> None:
    payload = _model_payload(_membership())
    payload.pop(field)
    with pytest.raises(ValidationError):
        AcquisitionRequestMembership.model_validate(payload)


@pytest.mark.parametrize("schema_version", (True, 1.0, "1", 0, 2))
def test_membership_rejects_invalid_schema_versions(schema_version: object) -> None:
    payload = _model_payload(_membership())
    payload["schema_version"] = schema_version
    with pytest.raises(ValidationError):
        AcquisitionRequestMembership.model_validate(payload)


@pytest.mark.parametrize("field", sorted(FORBIDDEN_S05_RELATIONSHIP_FIELDS))
def test_membership_rejects_every_s05_relationship_field(field: str) -> None:
    payload = _model_payload(_membership())
    payload[field] = "forbidden"
    with pytest.raises(ValidationError):
        AcquisitionRequestMembership.model_validate(payload)


def test_membership_is_frozen() -> None:
    membership = _membership()
    with pytest.raises(ValidationError):
        membership.request_reference = _reference()  # pyright: ignore[reportAttributeAccessIssue]


@pytest.mark.parametrize(
    ("field", "replacement"),
    (
        (
            "request_id",
            {
                "schema_version": 1,
                "acquisition_run_id": SYNTHETIC_RUN_ID,
                "request_ordinal": 1,
            },
        ),
        ("request_reference", {}),
        ("request_controls", {}),
        ("response_observation", {}),
    ),
)
def test_membership_requires_typed_nested_python_values(
    field: str,
    replacement: object,
) -> None:
    payload = _model_payload(_membership())
    payload[field] = replacement
    with pytest.raises(ValidationError):
        AcquisitionRequestMembership.model_validate(payload)


def test_membership_rejects_python_list_but_json_array_reconstructs_tuple() -> None:
    artifact = _artifact()
    payload = _model_payload(_membership(retained_artifacts=(artifact,)))
    payload["retained_artifacts"] = [artifact]
    with pytest.raises(ValidationError, match="tuple"):
        AcquisitionRequestMembership.model_validate(payload)

    semantic = _membership(retained_artifacts=(artifact,)).model_dump(mode="json")
    decoded = AcquisitionRequestMembership.model_validate_json(json.dumps(semantic))
    assert type(decoded.retained_artifacts) is tuple
    assert decoded.retained_artifacts == (artifact,)


@pytest.mark.parametrize(
    "mismatch",
    ("request-reference", "response-observation", "retained-artifact"),
)
def test_membership_rejects_cross_request_component_mismatch(mismatch: str) -> None:
    request_id = _request_id(1)
    other_request_id = _request_id(2)
    values: dict[str, object] = {
        "request_id": request_id,
        "request_reference": None,
        "request_controls": None,
        "response_observation": None,
        "retained_artifacts": None,
    }
    if mismatch == "request-reference":
        values["request_reference"] = _reference(other_request_id)
    elif mismatch == "response-observation":
        values["response_observation"] = _observation(other_request_id)
    else:
        values["retained_artifacts"] = (_artifact(other_request_id),)

    with pytest.raises(ValidationError, match="request_id"):
        AcquisitionRequestMembership.model_validate(values)


def test_membership_rejects_mixed_artifact_request_ids_without_rewriting() -> None:
    request_id = _request_id(1)
    other_request_id = _request_id(2)
    artifacts = (_artifact(request_id, index=1), _artifact(other_request_id, index=2))
    with pytest.raises(ValidationError, match="request_id"):
        AcquisitionRequestMembership(
            request_id=request_id,
            request_reference=None,
            request_controls=None,
            response_observation=None,
            retained_artifacts=artifacts,
        )
    assert artifacts[0].request_id == request_id
    assert artifacts[1].request_id == other_request_id


def test_membership_rejects_duplicate_artifact_identity_without_deduplication() -> None:
    request_id = _request_id()
    identity = _artifact_identity()
    artifacts = (
        _artifact(request_id, identity=identity),
        _artifact(request_id, identity=identity),
    )
    with pytest.raises(ValidationError, match="unique within a membership"):
        _membership(retained_artifacts=artifacts)
    assert len(artifacts) == 2


def test_membership_preserves_distinct_artifact_order_and_multiplicity() -> None:
    request_id = _request_id()
    artifacts = tuple(_artifact(request_id, index=index) for index in (3, 1, 2))
    membership = _membership(retained_artifacts=artifacts)
    assert membership.retained_artifacts == artifacts
    assert tuple(
        item.artifact_identity.byte_length.root
        for item in cast(
            tuple[ExactRetainedArtifact, ...], membership.retained_artifacts
        )
    ) == (3, 1, 2)


def test_same_artifact_identity_is_allowed_under_different_request_memberships() -> (
    None
):
    identity = _artifact_identity()
    first_id = _request_id(1)
    second_id = _request_id(2)
    run = _run(
        (
            _membership(
                1,
                retained_artifacts=(_artifact(first_id, identity=identity),),
            ),
            _membership(
                2,
                retained_artifacts=(_artifact(second_id, identity=identity),),
            ),
        )
    )
    first_artifact = cast(
        tuple[ExactRetainedArtifact, ...], run.requests[0].retained_artifacts
    )[0]
    second_artifact = cast(
        tuple[ExactRetainedArtifact, ...], run.requests[1].retained_artifacts
    )[0]
    assert first_artifact.artifact_identity == second_artifact.artifact_identity
    assert first_artifact.request_id != second_artifact.request_id


def test_exact_maximum_artifact_membership_is_accepted() -> None:
    request_id = _request_id()
    artifacts = tuple(
        _artifact(request_id, index=index)
        for index in range(1, MAX_RETAINED_ARTIFACTS + 1)
    )
    membership = _membership(retained_artifacts=artifacts)
    assert membership.retained_artifacts == artifacts
    assert (
        len(cast(tuple[ExactRetainedArtifact, ...], membership.retained_artifacts))
        == 64
    )


def test_artifact_maximum_plus_one_rejects_before_python_nested_validation() -> None:
    payload = _model_payload(_membership())
    payload["retained_artifacts"] = tuple(
        object() for _ in range(MAX_RETAINED_ARTIFACTS + 1)
    )
    with pytest.raises(ValidationError, match="at most 64") as captured:
        AcquisitionRequestMembership.model_validate(payload)
    assert captured.value.error_count() == 1


def test_artifact_maximum_plus_one_rejects_before_json_nested_validation() -> None:
    semantic = _membership().model_dump(mode="json")
    semantic["retained_artifacts"] = [
        {"deliberately": "invalid"} for _ in range(MAX_RETAINED_ARTIFACTS + 1)
    ]
    with pytest.raises(ValidationError, match="at most 64") as captured:
        AcquisitionRequestMembership.model_validate_json(json.dumps(semantic))
    assert captured.value.error_count() == 1


def test_membership_revalidates_constructed_invalid_nested_instances() -> None:
    invalid_ordinal = RetrievalRequestOrdinal.model_construct(root=0)
    invalid_request_id = RetrievalRequestId.model_construct(
        schema_version=1,
        acquisition_run_id=_run_id(),
        request_ordinal=invalid_ordinal,
    )
    invalid = AcquisitionRequestMembership.model_construct(
        schema_version=1,
        request_id=invalid_request_id,
        request_reference=None,
        request_controls=None,
        response_observation=None,
        retained_artifacts=None,
    )
    with pytest.raises(ValidationError):
        AcquisitionRequestMembership.model_validate(invalid)


def test_membership_revalidates_constructed_cross_request_state() -> None:
    invalid = AcquisitionRequestMembership.model_construct(
        schema_version=1,
        request_id=_request_id(1),
        request_reference=_reference(_request_id(2)),
        request_controls=None,
        response_observation=None,
        retained_artifacts=None,
    )
    with pytest.raises(ValidationError, match="request_id"):
        AcquisitionRequestMembership.model_validate(invalid)


def test_run_has_exact_required_fields_and_strict_configuration() -> None:
    assert tuple(AcquisitionRun.model_fields) == (
        "schema_version",
        "run_id",
        "status",
        "started_at",
        "sealed_at",
        "request_count",
        "requests",
    )
    assert not AcquisitionRun.model_fields["schema_version"].is_required()
    assert all(
        AcquisitionRun.model_fields[field].is_required()
        for field in (
            "run_id",
            "status",
            "started_at",
            "sealed_at",
            "request_count",
            "requests",
        )
    )
    _assert_strict_record_config(AcquisitionRun)


def test_complete_synthetic_run_composes_three_distinct_evidence_memberships() -> None:
    first_id = _request_id(1)
    second_id = _request_id(2)
    third_id = _request_id(3)
    first = _membership(
        1,
        request_reference=_reference(first_id, started_at=SYNTHETIC_STARTED_AT),
        response_observation=_observation(
            first_id,
            completed_at=SYNTHETIC_STARTED_AT + timedelta(seconds=5),
        ),
        retained_artifacts=(),
    )
    second = _membership(2, request_controls=_controls(), retained_artifacts=None)
    third = _membership(
        3,
        retained_artifacts=(_artifact(third_id),),
    )
    run = _run((first, second, third))

    assert run.status is AcquisitionRunStatus.COMPLETE
    assert run.request_count == 3
    assert run.requests == (first, second, third)
    assert run.requests[0].request_reference is not None
    assert run.requests[1].request_controls is not None
    assert run.requests[2].retained_artifacts == (_artifact(third_id),)
    assert second_id == run.requests[1].request_id


def test_partial_synthetic_zero_request_run_is_terminal_without_failure_reason() -> (
    None
):
    run = _run(
        run_id=SYNTHETIC_PARTIAL_RUN_ID,
        status=AcquisitionRunStatus.PARTIAL,
    )
    assert run.status is AcquisitionRunStatus.PARTIAL
    assert run.request_count == 0
    assert run.requests == ()
    assert "failure_reason" not in AcquisitionRun.model_fields


def test_partial_run_can_contain_valid_request_and_retained_evidence() -> None:
    request_id = _request_id(1, run_id=SYNTHETIC_PARTIAL_RUN_ID)
    membership = _membership(
        1,
        run_id=SYNTHETIC_PARTIAL_RUN_ID,
        retained_artifacts=(_artifact(request_id),),
    )
    run = _run(
        (membership,),
        run_id=SYNTHETIC_PARTIAL_RUN_ID,
        status=AcquisitionRunStatus.PARTIAL,
    )
    assert run.requests[0].retained_artifacts == (_artifact(request_id),)


def test_status_is_explicit_and_independent_of_count_or_optional_population() -> None:
    complete_empty = _run(status=AcquisitionRunStatus.COMPLETE)
    partial_empty = _run(
        run_id=SYNTHETIC_PARTIAL_RUN_ID,
        status=AcquisitionRunStatus.PARTIAL,
    )
    complete_unknown = _run((_membership(),), status=AcquisitionRunStatus.COMPLETE)
    assert complete_empty.request_count == partial_empty.request_count == 0
    assert complete_empty.status is AcquisitionRunStatus.COMPLETE
    assert partial_empty.status is AcquisitionRunStatus.PARTIAL
    assert complete_unknown.requests[0].request_reference is None
    assert complete_unknown.requests[0].retained_artifacts is None


def test_run_semantic_json_round_trip_reconstructs_typed_request_tuple() -> None:
    run = _run((_membership(1, retained_artifacts=()),))
    encoded = run.model_dump_json()
    decoded = AcquisitionRun.model_validate_json(encoded)
    assert decoded == run
    assert type(decoded.requests) is tuple
    assert type(decoded.requests[0]) is AcquisitionRequestMembership
    assert decoded.started_at.tzinfo is UTC
    assert decoded.sealed_at.tzinfo is UTC
    assert decoded.model_dump_json() == encoded


@pytest.mark.parametrize(
    "field",
    ("run_id", "status", "started_at", "sealed_at", "request_count", "requests"),
)
def test_run_rejects_omitted_required_fields(field: str) -> None:
    payload = _model_payload(_run())
    payload.pop(field)
    with pytest.raises(ValidationError):
        AcquisitionRun.model_validate(payload)


@pytest.mark.parametrize("schema_version", (True, 1.0, "1", 0, 2))
def test_run_rejects_invalid_schema_versions(schema_version: object) -> None:
    payload = _model_payload(_run())
    payload["schema_version"] = schema_version
    with pytest.raises(ValidationError):
        AcquisitionRun.model_validate(payload)


@pytest.mark.parametrize("field", sorted(FORBIDDEN_S05_RELATIONSHIP_FIELDS))
def test_run_rejects_every_s05_relationship_field(field: str) -> None:
    payload = _model_payload(_run())
    payload[field] = "forbidden"
    with pytest.raises(ValidationError):
        AcquisitionRun.model_validate(payload)


def test_run_is_frozen() -> None:
    run = _run()
    with pytest.raises(ValidationError):
        run.status = AcquisitionRunStatus.PARTIAL  # pyright: ignore[reportAttributeAccessIssue]


@pytest.mark.parametrize(
    ("field", "replacement"),
    (
        ("run_id", SYNTHETIC_RUN_ID),
        ("status", "complete"),
        ("requests", [_membership()]),
        ("requests", ({"request_id": cast(dict[str, object], {})},)),
    ),
)
def test_run_requires_typed_nested_python_values(
    field: str,
    replacement: object,
) -> None:
    payload = _model_payload(_run((_membership(),)))
    payload[field] = replacement
    with pytest.raises(ValidationError):
        AcquisitionRun.model_validate(payload)


@pytest.mark.parametrize(
    "request_count",
    (True, False, "0", "1", 0.0, 1.0, -1, MAX_ACQUISITION_REQUESTS + 1),
)
def test_request_count_rejects_non_exact_or_out_of_range_values(
    request_count: object,
) -> None:
    payload = _model_payload(_run())
    payload["request_count"] = request_count
    with pytest.raises(ValidationError):
        AcquisitionRun.model_validate(payload)


def test_request_count_json_rejects_bool_string_float_and_above_cap() -> None:
    semantic = _run().model_dump(mode="json")
    for value in (True, "0", 0.0, MAX_ACQUISITION_REQUESTS + 1):
        mutated = dict(semantic)
        mutated["request_count"] = value
        with pytest.raises(ValidationError):
            AcquisitionRun.model_validate_json(json.dumps(mutated))


def test_run_rejects_python_request_list_but_json_array_reconstructs_tuple() -> None:
    membership = _membership()
    payload = _model_payload(_run((membership,)))
    payload["requests"] = [membership]
    with pytest.raises(ValidationError, match="tuple"):
        AcquisitionRun.model_validate(payload)

    decoded = AcquisitionRun.model_validate_json(_run((membership,)).model_dump_json())
    assert type(decoded.requests) is tuple
    assert decoded.requests == (membership,)


def test_zero_one_and_contiguous_multiple_request_sequences_are_accepted() -> None:
    assert _run().requests == ()
    assert _run((_membership(1),)).request_count == 1
    multiple = _run(tuple(_membership(ordinal) for ordinal in range(1, 5)))
    assert tuple(
        membership.request_id.request_ordinal.root for membership in multiple.requests
    ) == (1, 2, 3, 4)


@pytest.mark.parametrize(
    ("ordinals", "request_count"),
    (
        ((1,), 0),
        ((), 1),
        ((1, 2), 1),
        ((2,), 1),
        ((1, 3), 2),
        ((1, 2, 2), 3),
        ((2, 1), 2),
        ((1, 3, 2), 3),
    ),
)
def test_count_gaps_duplicates_and_nonascending_ordinals_reject(
    ordinals: tuple[int, ...],
    request_count: int,
) -> None:
    requests = tuple(_membership(ordinal) for ordinal in ordinals)
    with pytest.raises(ValidationError):
        _run(requests, request_count=request_count)
    assert (
        tuple(membership.request_id.request_ordinal.root for membership in requests)
        == ordinals
    )


def test_run_rejects_foreign_run_membership() -> None:
    foreign = _membership(1, run_id="run-synthetic-foreign-001")
    with pytest.raises(ValidationError, match="run_id"):
        _run((foreign,))
    assert foreign.request_id.acquisition_run_id == _run_id("run-synthetic-foreign-001")


def test_exact_maximum_request_count_is_accepted_with_lightweight_memberships() -> None:
    memberships = tuple(
        _membership(ordinal) for ordinal in range(1, MAX_ACQUISITION_REQUESTS + 1)
    )
    run = _run(memberships)
    assert run.request_count == MAX_ACQUISITION_REQUESTS
    assert len(run.requests) == MAX_ACQUISITION_REQUESTS
    assert run.requests[-1].request_id.request_ordinal.root == MAX_ACQUISITION_REQUESTS


def test_request_maximum_plus_one_rejects_before_python_nested_validation() -> None:
    payload = _model_payload(_run())
    payload["request_count"] = MAX_ACQUISITION_REQUESTS
    payload["requests"] = tuple(object() for _ in range(MAX_ACQUISITION_REQUESTS + 1))
    with pytest.raises(ValidationError, match="at most 4096") as captured:
        AcquisitionRun.model_validate(payload)
    assert captured.value.error_count() == 1


def test_request_maximum_plus_one_rejects_before_json_nested_validation() -> None:
    semantic = _run().model_dump(mode="json")
    semantic["request_count"] = MAX_ACQUISITION_REQUESTS
    semantic["requests"] = [
        {"deliberately": "invalid"} for _ in range(MAX_ACQUISITION_REQUESTS + 1)
    ]
    with pytest.raises(ValidationError, match="at most 4096") as captured:
        AcquisitionRun.model_validate_json(json.dumps(semantic))
    assert captured.value.error_count() == 1


def test_run_revalidates_constructed_invalid_membership() -> None:
    invalid_membership = AcquisitionRequestMembership.model_construct(
        schema_version=1,
        request_id=_request_id(2),
        request_reference=None,
        request_controls=None,
        response_observation=None,
        retained_artifacts=None,
    )
    invalid = AcquisitionRun.model_construct(
        schema_version=1,
        run_id=_run_id(),
        status=AcquisitionRunStatus.COMPLETE,
        started_at=SYNTHETIC_STARTED_AT,
        sealed_at=SYNTHETIC_SEALED_AT,
        request_count=1,
        requests=(invalid_membership,),
    )
    with pytest.raises(ValidationError):
        AcquisitionRun.model_validate(invalid)


def test_run_accepts_equal_start_and_seal_and_exact_nested_boundaries() -> None:
    boundary = SYNTHETIC_STARTED_AT
    request_id = _request_id()
    membership = _membership(
        request_reference=_reference(request_id, started_at=boundary),
        response_observation=_observation(request_id, completed_at=boundary),
        retained_artifacts=(),
    )
    run = _run((membership,), started_at=boundary, sealed_at=boundary)
    assert run.started_at == run.sealed_at == boundary
    assert cast(
        RetrievalRequestReference, run.requests[0].request_reference
    ).started_at == (boundary)
    assert (
        cast(
            ResponseRepresentationObservation,
            run.requests[0].response_observation,
        ).completed_at
        == boundary
    )


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("started_at", datetime(2026, 8, 9, 12, 0, 0)),
        ("sealed_at", datetime(2026, 8, 9, 12, 1, 0)),
        (
            "started_at",
            datetime(2026, 8, 9, 13, 0, 0, tzinfo=timezone(timedelta(hours=1))),
        ),
        (
            "sealed_at",
            datetime(2026, 8, 9, 13, 1, 0, tzinfo=timezone(timedelta(hours=1))),
        ),
    ),
)
def test_run_rejects_naive_or_nonzero_offset_python_timestamps(
    field: str,
    value: datetime,
) -> None:
    payload = _model_payload(_run())
    payload[field] = value
    with pytest.raises(ValidationError):
        AcquisitionRun.model_validate(payload)


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("started_at", "2026-08-09T12:00:00-00:00"),
        ("sealed_at", "2026-08-09T12:01:00-00:00"),
        ("started_at", "2026-08-09T13:00:00+01:00"),
        ("sealed_at", "2026-08-09T13:01:00+01:00"),
        ("started_at", "2026-08-09T12:00:00+0000"),
        ("sealed_at", "2026-08-09T12:01:00Z00:00"),
    ),
)
def test_run_rejects_negative_zero_nonzero_or_malformed_json_offsets(
    field: str,
    value: str,
) -> None:
    semantic = _run().model_dump(mode="json")
    semantic[field] = value
    with pytest.raises(ValidationError):
        AcquisitionRun.model_validate_json(json.dumps(semantic))


def test_run_accepts_z_and_positive_zero_json_and_normalizes_to_datetime_utc() -> None:
    semantic = _run().model_dump(mode="json")
    semantic["started_at"] = "2026-08-09T12:00:00Z"
    semantic["sealed_at"] = "2026-08-09T12:01:00+00:00"
    run = AcquisitionRun.model_validate_json(json.dumps(semantic))
    assert run.started_at.tzinfo is UTC
    assert run.sealed_at.tzinfo is UTC


def test_run_rejects_seal_before_start() -> None:
    with pytest.raises(ValidationError, match="sealed_at"):
        _run(sealed_at=SYNTHETIC_STARTED_AT - timedelta(microseconds=1))


@pytest.mark.parametrize(
    "request_started_at",
    (
        SYNTHETIC_STARTED_AT - timedelta(microseconds=1),
        SYNTHETIC_SEALED_AT + timedelta(microseconds=1),
    ),
)
def test_run_rejects_request_start_outside_run_window(
    request_started_at: datetime,
) -> None:
    request_id = _request_id()
    membership = _membership(
        request_reference=_reference(request_id, started_at=request_started_at)
    )
    with pytest.raises(ValidationError, match="request_reference.started_at"):
        _run((membership,))


@pytest.mark.parametrize(
    "completed_at",
    (
        SYNTHETIC_STARTED_AT - timedelta(microseconds=1),
        SYNTHETIC_SEALED_AT + timedelta(microseconds=1),
    ),
)
def test_run_rejects_response_completion_outside_run_window(
    completed_at: datetime,
) -> None:
    request_id = _request_id()
    membership = _membership(
        response_observation=_observation(request_id, completed_at=completed_at)
    )
    with pytest.raises(ValidationError, match="response_observation.completed_at"):
        _run((membership,))


def test_run_rejects_response_before_its_present_request_start() -> None:
    request_id = _request_id()
    request_start = SYNTHETIC_STARTED_AT + timedelta(seconds=10)
    membership = _membership(
        request_reference=_reference(request_id, started_at=request_start),
        response_observation=_observation(
            request_id,
            completed_at=request_start - timedelta(microseconds=1),
        ),
    )
    with pytest.raises(ValidationError, match="must not precede"):
        _run((membership,))


def test_run_rejects_decreasing_present_request_start_chronology() -> None:
    later = SYNTHETIC_STARTED_AT + timedelta(seconds=20)
    earlier = SYNTHETIC_STARTED_AT + timedelta(seconds=10)
    requests = (
        _membership(
            1,
            request_reference=_reference(_request_id(1), started_at=later),
        ),
        _membership(2, request_reference=None),
        _membership(
            3,
            request_reference=_reference(_request_id(3), started_at=earlier),
        ),
    )
    with pytest.raises(ValidationError, match="nondecreasing"):
        _run(requests)


def test_equal_request_starts_and_nonserial_response_completion_are_accepted() -> None:
    shared_start = SYNTHETIC_STARTED_AT + timedelta(seconds=5)
    first_id = _request_id(1)
    second_id = _request_id(2)
    first = _membership(
        1,
        request_reference=_reference(first_id, started_at=shared_start),
        response_observation=_observation(
            first_id,
            completed_at=shared_start + timedelta(seconds=30),
        ),
    )
    second = _membership(
        2,
        request_reference=_reference(second_id, started_at=shared_start),
        response_observation=_observation(
            second_id,
            completed_at=shared_start + timedelta(seconds=10),
        ),
    )
    run = _run((first, second))
    first_response = cast(
        ResponseRepresentationObservation,
        run.requests[0].response_observation,
    )
    second_response = cast(
        ResponseRepresentationObservation,
        run.requests[1].response_observation,
    )
    assert first_response.completed_at > second_response.completed_at


def test_response_without_request_reference_is_bounded_only_by_run() -> None:
    completed = SYNTHETIC_STARTED_AT + timedelta(microseconds=1)
    membership = _membership(
        response_observation=_observation(_request_id(), completed_at=completed)
    )
    run = _run((membership,))
    assert run.requests[0].request_reference is None
    assert (
        cast(
            ResponseRepresentationObservation,
            run.requests[0].response_observation,
        ).completed_at
        == completed
    )


def test_canonical_acquisition_run_facts_and_request_sequence_are_direct() -> None:
    raw = ACQUISITION_PATH.read_bytes()
    acquisition = _load_acquisition()
    run = cast(dict[str, Any], acquisition["run"])
    seal = cast(dict[str, Any], cast(dict[str, Any], acquisition["assurance"])["seal"])
    request_section = cast(dict[str, Any], acquisition["requests"])
    records = cast(list[dict[str, Any]], request_section["records"])

    assert len(raw) == 61_283
    assert sha256(raw).hexdigest() == CANONICAL_ACQUISITION_SHA256
    assert run["run_id"] == CANONICAL_RUN_ID
    assert run["status"] == "complete"
    assert run["started_at"] == "2026-07-24T11:03:15.269222Z"
    assert seal == {
        "sealed": True,
        "sealed_at": "2026-07-30T08:28:22.796982Z",
        "status": "sealed",
    }
    assert request_section["started"] == len(records) == 32
    assert [record["ordinal"] for record in records] == list(range(1, 33))
    assert len({cast(int, record["ordinal"]) for record in records}) == 32


def test_canonical_acquisition_sidecar_is_exact_and_verified() -> None:
    raw = ACQUISITION_PATH.read_bytes()
    sidecar = ACQUISITION_SIDECAR.read_bytes()
    assert len(sidecar) == 83
    assert sidecar == (f"{sha256(raw).hexdigest()}  acquisition.json\n".encode("ascii"))
    assert sha256(sidecar).hexdigest() == (
        "dbb4cf7cb2c0b95377a0a11892b854a46c43dd6c443e7e808e3a57fe31981824"
    )


def test_canonical_retention_inventory_proves_known_empty_other_memberships() -> None:
    acquisition = _load_acquisition()
    artifacts = cast(list[dict[str, Any]], acquisition["artifacts"])
    request_section = cast(dict[str, Any], acquisition["requests"])
    records = cast(list[dict[str, Any]], request_section["records"])
    dispositions = cast(dict[str, Any], acquisition["dispositions"])
    retention = cast(dict[str, Any], dispositions["retention"])

    assert retention["exact_artifact_count"] == len(artifacts) == 2
    assert [artifact["request_ordinal"] for artifact in artifacts] == [30, 32]
    assert {
        cast(int, record["ordinal"])
        for record in records
        if record["response_retention"] == "exact"
    } == {30, 32}
    assert all(
        record["response_retention"] != "exact"
        for record in records
        if record["ordinal"] not in {30, 32}
    )

    canonical = _canonical_run()
    assert all(
        membership.retained_artifacts == ()
        for membership in canonical.requests
        if membership.request_id.request_ordinal.root not in {30, 32}
    )


@pytest.mark.parametrize(
    ("ordinal", "filename", "scope", "byte_length", "digest"),
    (
        (
            30,
            "base-to-head.diff",
            "github-compare-diff-http-entity-body",
            1640,
            DIFF_DIGEST,
        ),
        (32, "LICENSE", "git-blob-content", 1096, LICENSE_DIGEST),
    ),
)
def test_canonical_artifact_bytes_and_membership_replay_exactly(
    ordinal: int,
    filename: str,
    scope: str,
    byte_length: int,
    digest: str,
) -> None:
    acquisition = _load_acquisition()
    artifacts = cast(list[dict[str, Any]], acquisition["artifacts"])
    matches = [item for item in artifacts if item["request_ordinal"] == ordinal]
    assert len(matches) == 1
    descriptor = matches[0]
    assert descriptor["path"] == f"artifacts/{filename}"
    assert descriptor["digest_scope"] == scope
    assert descriptor["byte_length"] == byte_length
    assert descriptor["sha256"] == digest
    assert descriptor["retention"] == "exact_unmodified_bytes"

    path = ACQUISITION_ROOT / "artifacts" / filename
    assert path.exists()
    assert not path.is_symlink()
    path_stat = path.stat()
    assert stat.S_ISREG(path_stat.st_mode)
    assert stat.S_IMODE(path_stat.st_mode) == 0o644
    artifact_bytes = path.read_bytes()
    assert len(artifact_bytes) == byte_length
    assert sha256(artifact_bytes).hexdigest() == digest

    membership = _canonical_run().requests[ordinal - 1]
    retained = cast(tuple[ExactRetainedArtifact, ...], membership.retained_artifacts)
    assert len(retained) == 1
    assert retained[0].request_id == _request_id(ordinal, run_id=CANONICAL_RUN_ID)
    assert retained[0].artifact_identity.digest.scope.root == scope
    assert retained[0].artifact_identity.digest.value.root == digest
    assert retained[0].artifact_identity.byte_length.root == byte_length
    assert retained[0].retention_mode is ArtifactRetentionMode.EXACT_UNMODIFIED_BYTES


def test_canonical_full_run_constructs_without_optional_metadata_fabrication() -> None:
    acquisition = _load_acquisition()
    records = cast(
        list[dict[str, Any]],
        cast(dict[str, Any], acquisition["requests"])["records"],
    )
    canonical = _canonical_run()

    assert canonical.run_id == _run_id(CANONICAL_RUN_ID)
    assert canonical.status is AcquisitionRunStatus.COMPLETE
    assert canonical.started_at == CANONICAL_STARTED_AT
    assert canonical.sealed_at == CANONICAL_SEALED_AT
    assert canonical.request_count == len(canonical.requests) == 32
    assert tuple(
        membership.request_id.request_ordinal.root for membership in canonical.requests
    ) == tuple(range(1, 33))
    assert all(
        membership.request_id.acquisition_run_id == canonical.run_id
        for membership in canonical.requests
    )
    assert all(
        membership.request_reference is None for membership in canonical.requests
    )
    assert all(membership.request_controls is None for membership in canonical.requests)
    assert all(
        membership.response_observation is None for membership in canonical.requests
    )
    assert all("authority" not in record for record in records)
    assert all("query_parameters" not in record for record in records)
    assert all("state" not in record for record in records)
    assert AcquisitionRun.model_validate_json(canonical.model_dump_json()) == canonical


def test_canonical_artifacts_are_assigned_to_no_other_requests() -> None:
    canonical = _canonical_run()
    observed: dict[int, tuple[str, ...]] = {}
    for membership in canonical.requests:
        ordinal = membership.request_id.request_ordinal.root
        retained = cast(
            tuple[ExactRetainedArtifact, ...], membership.retained_artifacts
        )
        observed[ordinal] = tuple(
            artifact.artifact_identity.digest.value.root for artifact in retained
        )
    assert observed[30] == (DIFF_DIGEST,)
    assert observed[32] == (LICENSE_DIGEST,)
    assert all(
        not digests for ordinal, digests in observed.items() if ordinal not in {30, 32}
    )


def test_new_models_have_no_procedure_completeness_or_later_fields() -> None:
    fields = set(AcquisitionRequestMembership.model_fields) | set(
        AcquisitionRun.model_fields
    )
    assert fields == {
        "schema_version",
        "request_id",
        "request_reference",
        "request_controls",
        "response_observation",
        "retained_artifacts",
        "run_id",
        "status",
        "started_at",
        "sealed_at",
        "request_count",
        "requests",
    }
    assert not FORBIDDEN_S05_RELATIONSHIP_FIELDS & fields
    assert (
        not {
            "provider_run_id",
            "membership_id",
            "response_id",
            "artifact_id",
            "run_digest",
        }
        & fields
    )


def test_evidence_exports_public_definitions_and_private_caps_are_exact() -> None:
    source = EVIDENCE_SOURCE.read_text(encoding="utf-8")
    _validate_evidence_surface(source)
    assert tuple(evidence_module.__all__) == EXPECTED_EVIDENCE_EXPORTS
    assert len(evidence_module.__all__) == len(set(evidence_module.__all__)) == 58
    assert _parse_private_caps(source) == {
        "_MAX_RETAINED_ARTIFACTS_PER_REQUEST": 64,
        "_MAX_REQUESTS_PER_ACQUISITION_RUN": 4096,
    }


@pytest.mark.parametrize("mutation", ("missing-export", "unexpected-export"))
def test_evidence_export_inventory_is_mutation_sensitive(mutation: str) -> None:
    source = EVIDENCE_SOURCE.read_text(encoding="utf-8")
    if mutation == "missing-export":
        mutated = source.replace('    "AcquisitionRun",\n', "", 1)
    else:
        mutated = source.replace(
            '    "AcquisitionRun",\n',
            '    "AcquisitionRun",\n    "TransformationRecord",\n',
            1,
        )
    assert mutated != source
    with pytest.raises(AssertionError):
        _validate_evidence_surface(mutated)


@pytest.mark.parametrize(
    ("name", "value"),
    (
        ("_MAX_RETAINED_ARTIFACTS_PER_REQUEST", 64),
        ("_MAX_REQUESTS_PER_ACQUISITION_RUN", 4096),
    ),
)
def test_private_cap_constants_are_mutation_sensitive(name: str, value: int) -> None:
    source = EVIDENCE_SOURCE.read_text(encoding="utf-8")
    mutated = source.replace(f"{name} = {value}", f"{name} = {value + 1}", 1)
    assert mutated != source
    with pytest.raises(AssertionError):
        _validate_evidence_surface(mutated)


@pytest.mark.parametrize("definition", sorted(FORBIDDEN_POST_S07_DEFINITIONS))
def test_post_s07_definition_mutations_are_rejected(definition: str) -> None:
    source = EVIDENCE_SOURCE.read_text(encoding="utf-8")
    mutated = f"{source}\n\nclass {definition}:\n    pass\n"
    with pytest.raises(AssertionError):
        _validate_evidence_surface(mutated)


def test_production_evidence_module_performs_no_io_hashing_git_or_environment_access() -> (
    None
):
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


def test_no_durable_canonical_byte_or_persistence_api_is_introduced() -> None:
    tree = ast.parse(EVIDENCE_SOURCE.read_bytes())
    definitions = {
        node.name.casefold()
        for node in ast.walk(tree)
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
    }
    assert (
        not {
            "canonical_bytes",
            "canonical_json",
            "load",
            "persist",
            "read",
            "save",
            "serialize_bytes",
            "to_bytes",
            "write",
        }
        & definitions
    )


def test_package_roots_and_production_inventory_remain_exact() -> None:
    production_files = {
        path.relative_to(REPOSITORY_ROOT).as_posix()
        for path in (REPOSITORY_ROOT / "src").rglob("*.py")
    }
    assert production_files == EXPECTED_PRODUCTION_FILES
    assert len(production_files) == len(EXPECTED_PRODUCTION_FILES)
    assert faultatlas.__all__ == ["__version__"]
    assert faultatlas.__version__ == "0.1.0"
    assert getattr(domain_package, "__all__", None) in (None, [])
    assert not set(EXPECTED_EVIDENCE_EXPORTS) & set(vars(faultatlas))
    assert not set(EXPECTED_EVIDENCE_EXPORTS) & set(vars(domain_package))


@pytest.mark.parametrize("mutation", ("missing-evidence", "unexpected-extra"))
def test_production_inventory_is_mutation_sensitive(mutation: str) -> None:
    paths = set(EXPECTED_PRODUCTION_FILES)
    if mutation == "missing-evidence":
        paths.remove("src/faultatlas/domain/evidence.py")
    else:
        paths.add("src/faultatlas/domain/acquisition.py")
    with pytest.raises(AssertionError):
        assert paths == EXPECTED_PRODUCTION_FILES


def test_predecessor_sources_and_legacy_artifact_snapshot_remain_unchanged() -> None:
    for relative, (byte_length, digest) in PREDECESSOR_LOCKS.items():
        raw = (REPOSITORY_ROOT / relative).read_bytes()
        assert len(raw) == byte_length
        assert sha256(raw).hexdigest() == digest

    source_raw = SOURCE_SOURCE.read_bytes()
    assert len(source_raw) == 4336
    assert (
        sha256(source_raw).hexdigest()
        == PREDECESSOR_LOCKS["src/faultatlas/domain/source.py"][1]
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
    assert not issubclass(AcquisitionRequestMembership, ArtifactSnapshot)
    assert not issubclass(AcquisitionRun, ArtifactSnapshot)
    assert not issubclass(evidence_module.EvidenceEnvelope, ArtifactSnapshot)
    assert not issubclass(ArtifactSnapshot, evidence_module.EvidenceEnvelope)
    assert (set(ArtifactSnapshot.model_fields) - {"schema_version"}).isdisjoint(
        evidence_module.EvidenceEnvelope.model_fields
    )
