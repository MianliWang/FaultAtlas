from __future__ import annotations

import ast
import json
from datetime import UTC, datetime
from functools import cache
from hashlib import sha256
from pathlib import Path
from typing import Any, cast

import pytest
from pydantic import BaseModel, ValidationError

import faultatlas
import faultatlas.domain as domain_package
import faultatlas.domain.compatibility as compatibility_module
import faultatlas.domain.evidence as evidence_module
from faultatlas.domain.compatibility import CompatibilityStatus
from faultatlas.domain.evidence import (
    AcquisitionRequestMembership,
    AcquisitionRun,
    AcquisitionRunId,
    AcquisitionRunStatus,
    ArtifactByteLength,
    ArtifactDigest,
    ArtifactDigestAlgorithm,
    ArtifactDigestScope,
    ArtifactRetentionMode,
    ArtifactSha256Digest,
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
    LegacyArtifactSnapshotEnvelopeMappingResult,
    LegacyArtifactSnapshotProjectionResult,
    LegacyEvidenceCompatibilityReason,
    PublicationCheckEvent,
    PublicationCheckName,
    RetrievalRequestId,
    RetrievalRequestOrdinal,
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
EVIDENCE_SOURCE = REPOSITORY_ROOT / "src/faultatlas/domain/evidence.py"
SOURCE_SOURCE = REPOSITORY_ROOT / "src/faultatlas/domain/source.py"
COMPATIBILITY_SOURCE = REPOSITORY_ROOT / "src/faultatlas/domain/compatibility.py"
CORPUS_ROOT = REPOSITORY_ROOT / "reference_corpus/pytest-4412"
EVIDENCE_CONTRACT_CORPUS_RELATIVE = "reference_corpus/contracts/evidence-envelope/v1"

CANONICAL_RUN_ID = "run-0001-s04-v1-base-4c9cde74-head-690a63b9"
CANONICAL_STARTED_AT = datetime(2026, 7, 24, 11, 3, 15, 269222, tzinfo=UTC)
CANONICAL_SEALED_AT = datetime(2026, 7, 30, 8, 28, 22, 796982, tzinfo=UTC)
CANONICAL_RECORDED_AT = datetime(2026, 7, 30, 19, 17, 9, 655780, tzinfo=UTC)
CANONICAL_ASSESSED_AT = CANONICAL_RECORDED_AT
SYNTHETIC_TIME = datetime(2026, 8, 10, 12, 0, 0, tzinfo=UTC)

CANONICAL_VERSION = "1"
CANONICAL_CANONICALIZATION = "json-sort-keys-compact-utf8-lf-v1"
ACQUISITION_FORMAT = "faultatlas-acquisition"
ACQUISITION_LENGTH = 61_283
ACQUISITION_SHA256 = "1c29093bf1537e9b824a18df1848b71a8da014f544bc9f385707eb0e000a1318"
CORRECTION_FORMAT = "faultatlas-pytest-4412-acquisition-closure-addendum"
CORRECTION_LENGTH = 60_832
CORRECTION_SHA256 = "44491ee512d2c2022110b83967fb6fa86d13045bc8404ea490d7a08b7aef24a2"
DIFF_DIGEST = "dca87a4df1edb2d1acb3fc821724483ee874c2feba6525b2c21e79cb3e8f7312"
LICENSE_DIGEST = "a1ebce15afc7b5cf98c7c6de512d1959d4bf61db8c6bf2f111286d483b40a997"

CANONICAL_RELATIONSHIP_ID = "s04-c01-acquisition-closure"
CANONICAL_ASSESSMENT_ID = "s04-c01-declared-evidence-scope"
CANONICAL_SCOPE_ID = "pytest-4412-s04-declared-retention-scope"
CANONICAL_REASON = "declared-retention-policy"
SATISFIED_REQUIREMENTS = (
    "retained_compare_diff",
    "retained_historical_license",
)
OMISSION_REQUIREMENTS = (
    "issue_body",
    "issue_comment_bodies",
    "issue_timeline_nested_prose",
    "pr_body",
    "pr_comment_bodies",
    "pr_timeline_nested_prose",
    "review_prose_except_exact_empty_state",
    "inline_review_comment_bodies",
    "commit_messages_names_and_emails",
    "changed_file_patch_fields",
    "complete_changed_file_bytes",
    "raw_provider_json",
    "transient_pr_diff_bytes",
    "incidental_personal_profile_fields",
    "credentials_tokens_and_local_paths",
)

PR9_REVIEWED = "32f51f569ec554573f29bfa4d49b4f9d40d555c7"
PR9_TREE = "fffb04451520453cd00b4c2fc4acf1edd2147d5e"
PR9_PUBLISHED = "fb9b7061c2cf70bb6d4bdceb8fd023c2bfbce32b"
PR10_REVIEWED = "60400fcb301e108dbd14477ec6bb30b42157f12d"
PR10_TREE = "c50f510c38bb2f56c0b38f14b9f8cb7a09075703"
PR10_PUBLISHED = "8ece1cfa49c718345028bc6d03aca5e4fcdf434c"

ADAPTER_ID = "legacy-artifact-snapshot-v1-envelope-adapter"
ADAPTER_VERSION = "1"
SOURCE_LENGTH = 4_336
SOURCE_SHA256 = "034e53fd58212f0e34376bbc790fc3e74057031aaed4d7d89fb67904bdd380bf"
COMPATIBILITY_LENGTH = 18_898
COMPATIBILITY_SHA256 = (
    "f4ef93d432da4fd0ebf05237c164e10d8f18eceaf538ff4ddc3372565b5c46db"
)

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
    "src/faultatlas/domain/snapshot_evidence_link.py",
    "src/faultatlas/domain/source.py",
}
EXPECTED_COMPATIBILITY_EXPORTS = (
    "CompatibilityStatus",
    "LegacyCompatibilityReason",
    "LegacyObjectIdInterpretation",
    "LegacySourceLocatorMappingResult",
    "LegacySourceLocatorProjectionResult",
    "map_legacy_source_locator",
    "project_source_identity_to_legacy",
)
ENVELOPE_FIELDS = (
    "schema_version",
    "legacy_snapshots",
    "request_memberships",
    "acquisition_runs",
    "transformations",
    "record_relationships",
    "completeness_assessments",
    "publications",
)
MAPPING_FIELDS = (
    "schema_version",
    "adapter_id",
    "adapter_version",
    "status",
    "source_snapshot",
    "envelope",
    "reasons",
)
PROJECTION_FIELDS = (
    "schema_version",
    "adapter_id",
    "adapter_version",
    "status",
    "source_envelope",
    "projected_snapshot",
    "reasons",
)
COMPONENT_CAPS = {
    "legacy_snapshots": 64,
    "request_memberships": 4096,
    "acquisition_runs": 64,
    "transformations": 256,
    "record_relationships": 256,
    "completeness_assessments": 256,
    "publications": 256,
}
MODERN_COMPONENT_FIELDS = tuple(
    field for field in COMPONENT_CAPS if field != "legacy_snapshots"
)
STRICT_RECORD_CONFIG = {
    "extra": "forbid",
    "frozen": True,
    "revalidate_instances": "always",
    "strict": True,
    "validate_default": True,
}


def _model_payload(model: BaseModel) -> dict[str, object]:
    return {
        field_name: cast(object, getattr(model, field_name))
        for field_name in model.__class__.model_fields
    }


def _envelope_data(**overrides: object) -> dict[str, object]:
    data: dict[str, object] = {
        "legacy_snapshots": None,
        "request_memberships": None,
        "acquisition_runs": None,
        "transformations": None,
        "record_relationships": None,
        "completeness_assessments": None,
        "publications": None,
    }
    data.update(overrides)
    return data


def _envelope(**overrides: object) -> EvidenceEnvelope:
    return EvidenceEnvelope.model_validate(_envelope_data(**overrides))


def _provider(value: str = "github") -> ProviderKey:
    return ProviderKey.model_validate(value)


def _repository() -> RepositoryIdentity:
    return RepositoryIdentity(
        provider=_provider(),
        provider_repository_id=ProviderRepositoryId.model_validate("1303365003"),
    )


def _authority() -> ProviderAuthority:
    return ProviderAuthority(
        provider=_provider(),
        role=AuthorityRole.RETRIEVAL,
        host="api.github.com",
    )


def _record_reference(
    *,
    format_name: str,
    digest: str,
    byte_length: int,
    canonicalization: str = CANONICAL_CANONICALIZATION,
) -> DurableEvidenceRecordReference:
    return DurableEvidenceRecordReference(
        format_name=EvidenceRecordFormat.model_validate(format_name),
        format_version=EvidenceVersion.model_validate(CANONICAL_VERSION),
        canonicalization=EvidenceCanonicalization.model_validate(canonicalization),
        sha256=ArtifactSha256Digest.model_validate(digest),
        byte_length=ArtifactByteLength.model_validate(byte_length),
    )


def _acquisition_reference() -> DurableEvidenceRecordReference:
    return _record_reference(
        format_name=ACQUISITION_FORMAT,
        digest=ACQUISITION_SHA256,
        byte_length=ACQUISITION_LENGTH,
    )


def _correction_reference() -> DurableEvidenceRecordReference:
    return _record_reference(
        format_name=CORRECTION_FORMAT,
        digest=CORRECTION_SHA256,
        byte_length=CORRECTION_LENGTH,
    )


def _synthetic_reference(index: int) -> DurableEvidenceRecordReference:
    return _record_reference(
        format_name="faultatlas-synthetic-envelope-record",
        digest=f"{index + 10_000:064x}",
        byte_length=index + 1,
        canonicalization="synthetic-json-v1",
    )


def _request_id(
    ordinal: int,
    *,
    run_id: str,
) -> RetrievalRequestId:
    return RetrievalRequestId(
        acquisition_run_id=AcquisitionRunId.model_validate(run_id),
        request_ordinal=RetrievalRequestOrdinal.model_validate(ordinal),
    )


def _membership(
    ordinal: int,
    *,
    run_id: str,
    retained_artifacts: tuple[ExactRetainedArtifact, ...] | None = None,
) -> AcquisitionRequestMembership:
    return AcquisitionRequestMembership(
        request_id=_request_id(ordinal, run_id=run_id),
        request_reference=None,
        request_controls=None,
        response_observation=None,
        retained_artifacts=retained_artifacts,
    )


def _artifact_identity(
    index: int,
    *,
    scope: str | None = None,
    digest: str | None = None,
    byte_length: int | None = None,
) -> ExactArtifactIdentity:
    return ExactArtifactIdentity(
        digest=ArtifactDigest(
            algorithm=ArtifactDigestAlgorithm.SHA256,
            scope=ArtifactDigestScope.model_validate(
                scope or f"synthetic-envelope-artifact-{index}"
            ),
            value=ArtifactSha256Digest.model_validate(digest or f"{index:064x}"),
        ),
        byte_length=ArtifactByteLength.model_validate(
            index if byte_length is None else byte_length
        ),
    )


def _retained_artifact(
    ordinal: int,
    *,
    run_id: str,
    identity: ExactArtifactIdentity,
) -> ExactRetainedArtifact:
    return ExactRetainedArtifact(
        request_id=_request_id(ordinal, run_id=run_id),
        artifact_identity=identity,
        retention_mode=ArtifactRetentionMode.EXACT_UNMODIFIED_BYTES,
    )


def _canonical_run() -> AcquisitionRun:
    artifacts = {
        30: _retained_artifact(
            30,
            run_id=CANONICAL_RUN_ID,
            identity=_artifact_identity(
                30,
                scope="github-compare-diff-http-entity-body",
                digest=DIFF_DIGEST,
                byte_length=1640,
            ),
        ),
        32: _retained_artifact(
            32,
            run_id=CANONICAL_RUN_ID,
            identity=_artifact_identity(
                32,
                scope="git-blob-content",
                digest=LICENSE_DIGEST,
                byte_length=1096,
            ),
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
    return AcquisitionRun(
        run_id=AcquisitionRunId.model_validate(CANONICAL_RUN_ID),
        status=AcquisitionRunStatus.COMPLETE,
        started_at=CANONICAL_STARTED_AT,
        sealed_at=CANONICAL_SEALED_AT,
        request_count=32,
        requests=memberships,
    )


def _synthetic_membership(index: int) -> AcquisitionRequestMembership:
    return _membership(
        index + 1,
        run_id="synthetic-envelope-membership-run",
        retained_artifacts=None,
    )


def _synthetic_run(
    index: int,
    *,
    requests: tuple[AcquisitionRequestMembership, ...] = (),
    run_id: str | None = None,
) -> AcquisitionRun:
    return AcquisitionRun(
        run_id=AcquisitionRunId.model_validate(
            run_id or f"synthetic-envelope-run-{index:04d}"
        ),
        status=AcquisitionRunStatus.COMPLETE,
        started_at=SYNTHETIC_TIME,
        sealed_at=SYNTHETIC_TIME,
        request_count=len(requests),
        requests=requests,
    )


def _artifact_subject(index: int) -> TransformationSubject:
    return TransformationSubject(
        subject_kind="exact_artifact",
        artifact_identity=_artifact_identity(index),
        record_reference=None,
    )


def _synthetic_transformation(index: int) -> EvidenceTransformation:
    return EvidenceTransformation(
        transformation_id=EvidenceRelationId.model_validate(
            f"synthetic-envelope-transformation-{index:04d}"
        ),
        operation=TransformationOperation.model_validate("synthetic-byte-copy"),
        operation_version=EvidenceVersion.model_validate("1"),
        performed_at=SYNTHETIC_TIME,
        inputs=(_artifact_subject(index * 2 + 1),),
        outputs=(_artifact_subject(index * 2 + 2),),
        lossiness=TransformationLossiness.LOSSLESS,
        reversibility=TransformationReversibility.REVERSIBLE,
        parameter_record=None,
    )


def _canonical_correction() -> EvidenceCorrection:
    return EvidenceCorrection(
        relationship_kind="correction",
        relationship_id=EvidenceRelationId.model_validate(CANONICAL_RELATIONSHIP_ID),
        target_record=_acquisition_reference(),
        correction_record=_correction_reference(),
        recorded_at=CANONICAL_RECORDED_AT,
    )


def _synthetic_correction(
    index: int,
    *,
    relationship_id: str | None = None,
) -> EvidenceCorrection:
    return EvidenceCorrection(
        relationship_kind="correction",
        relationship_id=EvidenceRelationId.model_validate(
            relationship_id or f"synthetic-envelope-correction-{index:04d}"
        ),
        target_record=_synthetic_reference(index * 2 + 1),
        correction_record=_synthetic_reference(index * 2 + 2),
        recorded_at=SYNTHETIC_TIME,
    )


def _synthetic_supersession(
    index: int,
    *,
    relationship_id: str | None = None,
) -> EvidenceSupersession:
    return EvidenceSupersession(
        relationship_kind="supersession",
        relationship_id=EvidenceRelationId.model_validate(
            relationship_id or f"synthetic-envelope-supersession-{index:04d}"
        ),
        superseded_record=_synthetic_reference(index * 2 + 101),
        superseding_record=_synthetic_reference(index * 2 + 102),
        recorded_at=SYNTHETIC_TIME,
    )


def _omission(requirement: str) -> EvidenceOmission:
    return EvidenceOmission(
        omission_id=EvidenceRelationId.model_validate(
            f"s04-c01.omission.{requirement}"
        ),
        requirement_id=EvidenceRequirementId.model_validate(requirement),
        outcome=EvidenceRequirementOutcome.INTENTIONALLY_OMITTED,
        reason=EvidenceDispositionReason.model_validate(CANONICAL_REASON),
        source_records=(_correction_reference(), _acquisition_reference()),
    )


def _satisfied(requirement: str) -> EvidenceRequirementResult:
    return EvidenceRequirementResult(
        requirement_id=EvidenceRequirementId.model_validate(requirement),
        outcome=EvidenceRequirementOutcome.SATISFIED,
        evidence_records=(_acquisition_reference(),),
        omission=None,
    )


def _omitted(requirement: str) -> EvidenceRequirementResult:
    return EvidenceRequirementResult(
        requirement_id=EvidenceRequirementId.model_validate(requirement),
        outcome=EvidenceRequirementOutcome.INTENTIONALLY_OMITTED,
        evidence_records=None,
        omission=_omission(requirement),
    )


def _canonical_assessment() -> EvidenceCompletenessAssessment:
    requirements = tuple(_satisfied(item) for item in SATISFIED_REQUIREMENTS) + tuple(
        _omitted(item) for item in OMISSION_REQUIREMENTS
    )
    return EvidenceCompletenessAssessment(
        assessment_id=EvidenceRelationId.model_validate(CANONICAL_ASSESSMENT_ID),
        subject_record=_acquisition_reference(),
        scope_id=EvidenceScopeId.model_validate(CANONICAL_SCOPE_ID),
        assessed_at=CANONICAL_ASSESSED_AT,
        status=(EvidenceCompletenessStatus.SCOPE_SATISFIED_WITH_DECLARED_OMISSIONS),
        requirements=requirements,
    )


def _synthetic_assessment(index: int) -> EvidenceCompletenessAssessment:
    result = EvidenceRequirementResult(
        requirement_id=EvidenceRequirementId.model_validate(
            f"synthetic-envelope-requirement-{index:04d}"
        ),
        outcome=EvidenceRequirementOutcome.NOT_APPLICABLE,
        evidence_records=None,
        omission=None,
    )
    return EvidenceCompletenessAssessment(
        assessment_id=EvidenceRelationId.model_validate(
            f"synthetic-envelope-assessment-{index:04d}"
        ),
        subject_record=_synthetic_reference(index + 5000),
        scope_id=EvidenceScopeId.model_validate(
            f"synthetic-envelope-scope-{index:04d}"
        ),
        assessed_at=SYNTHETIC_TIME,
        status=EvidenceCompletenessStatus.SCOPE_SATISFIED,
        requirements=(result,),
    )


def _commit(digest: str) -> GitCommitIdentity:
    return GitCommitIdentity(
        kind=GitObjectKind.COMMIT,
        algorithm=GitHashAlgorithm.SHA1,
        full_digest=digest,
    )


def _tree(digest: str) -> GitTreeIdentity:
    return GitTreeIdentity(
        kind=GitObjectKind.TREE,
        algorithm=GitHashAlgorithm.SHA1,
        full_digest=digest,
    )


def _pull_request_identity(number: str) -> NumberedSourceObjectIdentity:
    return NumberedSourceObjectIdentity(
        repository_identity=_repository(),
        kind=SourceObjectKind.PULL_REQUEST,
        repository_scoped_number=RepositoryScopedNumber.model_validate(number),
    )


def _check(
    *,
    event: PublicationCheckEvent,
    head: GitCommitIdentity,
    run_id: str,
    job_id: str,
) -> SuccessfulPublicationCheck:
    return SuccessfulPublicationCheck(
        authority=_authority(),
        workflow_name=PublicationCheckName.model_validate("CI"),
        context=PublicationCheckName.model_validate("validate"),
        event=event,
        run_id=ProviderGlobalId.model_validate(run_id),
        job_id=ProviderGlobalId.model_validate(job_id),
        attempt=1,
        head_revision=head,
        conclusion="success",
    )


def _publication(
    *,
    publication_id: str,
    subject: DurableEvidenceRecordReference,
    pull_request_number: str,
    reviewed_digest: str,
    tree_digest: str,
    published_digest: str,
    published_at: datetime,
    pull_request_run_id: str,
    pull_request_job_id: str,
    main_run_id: str,
    main_job_id: str,
) -> EvidencePublication:
    reviewed = _commit(reviewed_digest)
    published = _commit(published_digest)
    tree = _tree(tree_digest)
    return EvidencePublication(
        publication_id=EvidenceRelationId.model_validate(publication_id),
        subject_record=subject,
        repository_identity=_repository(),
        pull_request_identity=_pull_request_identity(pull_request_number),
        reviewed_revision=reviewed,
        reviewed_tree=tree,
        published_revision=published,
        published_tree=tree,
        method=EvidencePublicationMethod.PROTECTED_PULL_REQUEST_SQUASH_MERGE,
        published_at=published_at,
        pull_request_check=_check(
            event=PublicationCheckEvent.PULL_REQUEST,
            head=reviewed,
            run_id=pull_request_run_id,
            job_id=pull_request_job_id,
        ),
        main_check=_check(
            event=PublicationCheckEvent.PUSH,
            head=published,
            run_id=main_run_id,
            job_id=main_job_id,
        ),
    )


def _acquisition_publication() -> EvidencePublication:
    return _publication(
        publication_id="s1-p00-s04-acquisition-publication",
        subject=_acquisition_reference(),
        pull_request_number="9",
        reviewed_digest=PR9_REVIEWED,
        tree_digest=PR9_TREE,
        published_digest=PR9_PUBLISHED,
        published_at=datetime(2026, 7, 30, 8, 38, 4, tzinfo=UTC),
        pull_request_run_id="30527236496",
        pull_request_job_id="90820902687",
        main_run_id="30527462427",
        main_job_id="90821631028",
    )


def _correction_publication() -> EvidencePublication:
    return _publication(
        publication_id="s1-p00-s04-c01-correction-publication",
        subject=_correction_reference(),
        pull_request_number="10",
        reviewed_digest=PR10_REVIEWED,
        tree_digest=PR10_TREE,
        published_digest=PR10_PUBLISHED,
        published_at=datetime(2026, 7, 30, 19, 42, 46, tzinfo=UTC),
        pull_request_run_id="30575877780",
        pull_request_job_id="90983907152",
        main_run_id="30576009699",
        main_job_id="90984355320",
    )


def _synthetic_publication(index: int) -> EvidencePublication:
    data = _model_payload(_acquisition_publication())
    data["publication_id"] = EvidenceRelationId.model_validate(
        f"synthetic-envelope-publication-{index:04d}"
    )
    return EvidencePublication.model_validate(data)


def _synthetic_snapshot(index: int) -> ArtifactSnapshot:
    payload = json.dumps({"synthetic_issue": index}, separators=(",", ":"))
    locator = SourceLocator.model_validate(
        {
            "provider": "github",
            "repository": "example/faultatlas-fixtures",
            "object_kind": "issue",
            "object_id": str(index + 1),
        }
    )
    return ArtifactSnapshot.model_validate(
        {
            "source": locator,
            "retrieved_at": SYNTHETIC_TIME,
            "payload_text": payload,
            "digest": sha256(payload.encode("utf-8")).hexdigest(),
            "truncated": False,
            "redacted": False,
            "missing_context": (),
        }
    )


@cache
def _component_values(field: str, count: int) -> tuple[object, ...]:
    if field == "legacy_snapshots":
        return tuple(_synthetic_snapshot(index) for index in range(1, count + 1))
    if field == "request_memberships":
        return tuple(_synthetic_membership(index) for index in range(count))
    if field == "acquisition_runs":
        return tuple(_synthetic_run(index) for index in range(1, count + 1))
    if field == "transformations":
        return tuple(_synthetic_transformation(index) for index in range(1, count + 1))
    if field == "record_relationships":
        return tuple(_synthetic_correction(index) for index in range(1, count + 1))
    if field == "completeness_assessments":
        return tuple(_synthetic_assessment(index) for index in range(1, count + 1))
    if field == "publications":
        return tuple(_synthetic_publication(index) for index in range(1, count + 1))
    raise AssertionError(f"unexpected component field: {field}")


def _state_envelope(field: str, value: object) -> EvidenceEnvelope:
    data = _envelope_data(**{field: value})
    if value is None or value == ():
        anchor_field = (
            "acquisition_runs" if field == "legacy_snapshots" else "legacy_snapshots"
        )
        data[anchor_field] = _component_values(anchor_field, 1)
    return EvidenceEnvelope.model_validate(data)


def test_exact_s07_fields_configs_exports_and_package_surface() -> None:
    assert tuple(EvidenceEnvelope.model_fields) == ENVELOPE_FIELDS
    assert tuple(LegacyArtifactSnapshotEnvelopeMappingResult.model_fields) == (
        MAPPING_FIELDS
    )
    assert tuple(LegacyArtifactSnapshotProjectionResult.model_fields) == (
        PROJECTION_FIELDS
    )
    for model in (
        EvidenceEnvelope,
        LegacyArtifactSnapshotEnvelopeMappingResult,
        LegacyArtifactSnapshotProjectionResult,
    ):
        assert model.model_config == STRICT_RECORD_CONFIG

    assert tuple(evidence_module.__all__) == EXPECTED_EVIDENCE_EXPORTS
    assert len(evidence_module.__all__) == 58
    assert tuple(getattr(evidence_module, name) for name in evidence_module.__all__)[
        -6:
    ] == (
        EvidenceEnvelope,
        LegacyEvidenceCompatibilityReason,
        LegacyArtifactSnapshotEnvelopeMappingResult,
        LegacyArtifactSnapshotProjectionResult,
        wrap_legacy_artifact_snapshot,
        project_evidence_envelope_to_legacy_artifact_snapshot,
    )
    assert faultatlas.__all__ == ["__version__"]
    assert not hasattr(domain_package, "__all__")
    assert not set(EXPECTED_EVIDENCE_EXPORTS) & set(faultatlas.__all__)

    production_files = {
        path.relative_to(REPOSITORY_ROOT).as_posix()
        for path in (REPOSITORY_ROOT / "src").rglob("*.py")
    }
    assert production_files == EXPECTED_PRODUCTION_FILES


def test_envelope_and_adapter_results_require_exact_schema_and_are_frozen() -> None:
    envelope = _envelope(legacy_snapshots=(_synthetic_snapshot(1),))
    mapping = wrap_legacy_artifact_snapshot(_synthetic_snapshot(2))
    projection = project_evidence_envelope_to_legacy_artifact_snapshot(mapping.envelope)
    for model in (envelope, mapping, projection):
        assert model.schema_version == 1
        with pytest.raises(ValidationError):
            setattr(model, "schema_version", 2)

    for model, payload in (
        (EvidenceEnvelope, _envelope_data(legacy_snapshots=(_synthetic_snapshot(3),))),
        (
            LegacyArtifactSnapshotEnvelopeMappingResult,
            _model_payload(mapping),
        ),
        (
            LegacyArtifactSnapshotProjectionResult,
            _model_payload(projection),
        ),
    ):
        defaulted_payload = dict(payload)
        defaulted_payload.pop("schema_version", None)
        assert getattr(model.model_validate(defaulted_payload), "schema_version") == 1
        for invalid in (True, "1", 1.0, 0, 2):
            invalid_payload = dict(payload)
            invalid_payload["schema_version"] = invalid
            with pytest.raises(ValidationError):
                model.model_validate(invalid_payload)
        extra_payload = dict(payload)
        extra_payload["unexpected"] = "forbidden"
        with pytest.raises(ValidationError):
            model.model_validate(extra_payload)


@pytest.mark.parametrize("field", tuple(COMPONENT_CAPS))
def test_every_component_preserves_none_known_empty_and_nonempty_json_states(
    field: str,
) -> None:
    none_envelope = _state_envelope(field, None)
    empty_envelope = _state_envelope(field, ())
    values = _component_values(field, 2)
    present_envelope = _state_envelope(field, values)

    assert getattr(none_envelope, field) is None
    assert getattr(empty_envelope, field) == ()
    assert getattr(present_envelope, field) == values
    assert none_envelope != empty_envelope

    for envelope, expected_json in (
        (none_envelope, None),
        (empty_envelope, []),
        (present_envelope, [object(), object()]),
    ):
        dumped = envelope.model_dump(mode="json")
        if expected_json is None:
            assert dumped[field] is None
        elif expected_json == []:
            assert dumped[field] == []
        else:
            assert isinstance(dumped[field], list)
            assert len(cast(list[object], dumped[field])) == 2
        restored = EvidenceEnvelope.model_validate_json(envelope.model_dump_json())
        assert getattr(restored, field) == getattr(envelope, field)
        if getattr(restored, field) is not None:
            assert type(getattr(restored, field)) is tuple


@pytest.mark.parametrize(
    "components",
    [
        {field: None for field in COMPONENT_CAPS},
        {field: () for field in COMPONENT_CAPS},
        {
            field: None if index % 2 == 0 else ()
            for index, field in enumerate(COMPONENT_CAPS)
        },
    ],
    ids=("all-none", "all-known-empty", "mixed-empty"),
)
def test_envelope_rejects_every_composition_without_an_actual_record(
    components: dict[str, object],
) -> None:
    with pytest.raises(ValidationError, match="at least one record"):
        EvidenceEnvelope.model_validate(components)
    with pytest.raises(ValidationError, match="at least one record"):
        EvidenceEnvelope.model_validate_json(json.dumps(components))


@pytest.mark.parametrize(("field", "maximum"), tuple(COMPONENT_CAPS.items()))
def test_every_component_cap_python_and_json_prevalidation_is_exact(
    field: str,
    maximum: int,
) -> None:
    one = _component_values(field, 1)
    exact_max = _component_values(field, maximum)

    one_envelope = _envelope(**{field: one})
    max_envelope = _envelope(**{field: exact_max})
    assert getattr(one_envelope, field) == one
    assert len(cast(tuple[object, ...], getattr(max_envelope, field))) == maximum

    with pytest.raises(ValidationError, match="must be a tuple or None"):
        EvidenceEnvelope.model_validate(_envelope_data(**{field: list(one)}))

    invalid_tuple = tuple(object() for _ in range(maximum + 1))
    invalid_list = list(invalid_tuple)
    for invalid in (invalid_tuple, invalid_list):
        with pytest.raises(
            ValidationError,
            match=rf"{field} must contain at most {maximum} entries",
        ) as error:
            EvidenceEnvelope.model_validate(_envelope_data(**{field: invalid}))
        assert error.value.errors()[0]["loc"] == (field,)

    one_from_json = EvidenceEnvelope.model_validate_json(one_envelope.model_dump_json())
    max_from_json = EvidenceEnvelope.model_validate_json(max_envelope.model_dump_json())
    assert getattr(one_from_json, field) == one
    assert getattr(max_from_json, field) == exact_max
    assert type(getattr(max_from_json, field)) is tuple

    invalid_entries: list[dict[str, object]] = [{} for _ in range(maximum + 1)]
    invalid_json = _envelope_data(**{field: invalid_entries})
    with pytest.raises(
        ValidationError,
        match=rf"{field} must contain at most {maximum} entries",
    ) as error:
        EvidenceEnvelope.model_validate_json(json.dumps(invalid_json))
    assert error.value.errors()[0]["loc"] == (field,)


@pytest.mark.parametrize("field", tuple(COMPONENT_CAPS))
def test_every_component_preserves_declared_order_without_sorting_or_truncation(
    field: str,
) -> None:
    values = _component_values(field, 2)
    reversed_values = tuple(reversed(values))
    forward = _envelope(**{field: values})
    reverse = _envelope(**{field: reversed_values})
    restored = EvidenceEnvelope.model_validate_json(reverse.model_dump_json())

    assert getattr(forward, field) == values
    assert getattr(reverse, field) == reversed_values
    assert getattr(restored, field) == reversed_values
    assert forward != reverse


@pytest.mark.parametrize(
    ("field", "duplicate"),
    [
        ("legacy_snapshots", _synthetic_snapshot(101)),
        ("request_memberships", _synthetic_membership(101)),
        ("acquisition_runs", _synthetic_run(101)),
        ("transformations", _synthetic_transformation(101)),
        ("record_relationships", _synthetic_correction(101)),
        ("completeness_assessments", _synthetic_assessment(101)),
        ("publications", _synthetic_publication(101)),
    ],
)
def test_every_within_component_duplicate_identity_rejects_without_deduplication(
    field: str,
    duplicate: object,
) -> None:
    with pytest.raises(ValidationError, match="duplicate|unique"):
        _envelope(**{field: (duplicate, duplicate)})


def test_relationship_identity_is_typed_and_cross_kind_lexeme_reuse_is_valid() -> None:
    shared = "synthetic-shared-relationship-id"
    correction = _synthetic_correction(201, relationship_id=shared)
    supersession = _synthetic_supersession(201, relationship_id=shared)
    envelope = _envelope(record_relationships=(correction, supersession))

    assert envelope.record_relationships == (correction, supersession)
    assert correction.relationship_id == supersession.relationship_id
    assert correction.relationship_kind == "correction"
    assert supersession.relationship_kind == "supersession"

    with pytest.raises(ValidationError, match="unique typed relationship"):
        _envelope(record_relationships=(correction, correction))
    with pytest.raises(ValidationError, match="unique typed relationship"):
        _envelope(record_relationships=(supersession, supersession))


def test_standalone_and_run_membership_collision_rejects_but_partial_locations_work() -> (
    None
):
    run_id = "synthetic-envelope-collision-run"
    membership = _membership(1, run_id=run_id, retained_artifacts=None)
    run = _synthetic_run(301, requests=(membership,), run_id=run_id)

    assert _envelope(request_memberships=(membership,)).request_memberships == (
        membership,
    )
    assert _envelope(acquisition_runs=(run,)).acquisition_runs == (run,)
    with pytest.raises(ValidationError, match="both as a standalone membership"):
        _envelope(request_memberships=(membership,), acquisition_runs=(run,))

    different = _membership(2, run_id=run_id, retained_artifacts=None)
    valid = _envelope(request_memberships=(different,), acquisition_runs=(run,))
    assert valid.request_memberships == (different,)
    assert valid.acquisition_runs == (run,)


def _canonical_current_envelope() -> EvidenceEnvelope:
    return _envelope(
        acquisition_runs=(_canonical_run(),),
        transformations=(),
        record_relationships=(_canonical_correction(),),
        completeness_assessments=(_canonical_assessment(),),
        publications=(_acquisition_publication(), _correction_publication()),
    )


def test_canonical_current_p03_envelope_reconstructs_exact_ordered_s04_s06_facts() -> (
    None
):
    envelope = _canonical_current_envelope()
    run = _canonical_run()
    correction = _canonical_correction()
    assessment = _canonical_assessment()
    acquisition_publication = _acquisition_publication()
    correction_publication = _correction_publication()

    assert envelope.legacy_snapshots is None
    assert envelope.request_memberships is None
    assert envelope.acquisition_runs == (run,)
    assert envelope.transformations == ()
    assert envelope.record_relationships == (correction,)
    assert envelope.completeness_assessments == (assessment,)
    assert envelope.publications == (
        acquisition_publication,
        correction_publication,
    )

    assert run.run_id.root == CANONICAL_RUN_ID
    assert run.status is AcquisitionRunStatus.COMPLETE
    assert run.started_at == CANONICAL_STARTED_AT
    assert run.sealed_at == CANONICAL_SEALED_AT
    assert run.request_count == 32
    assert tuple(
        item.request_id.request_ordinal.root for item in run.requests
    ) == tuple(range(1, 33))
    assert tuple(
        item.request_id.request_ordinal.root
        for item in run.requests
        if item.retained_artifacts
    ) == (30, 32)
    retained = tuple(
        item.retained_artifacts[0] for item in run.requests if item.retained_artifacts
    )
    assert retained[0].artifact_identity.digest.value.root == DIFF_DIGEST
    assert retained[1].artifact_identity.digest.value.root == LICENSE_DIGEST

    assert correction.relationship_kind == "correction"
    assert correction.relationship_id.root == CANONICAL_RELATIONSHIP_ID
    assert correction.target_record == _acquisition_reference()
    assert correction.correction_record == _correction_reference()
    assert correction.recorded_at == CANONICAL_RECORDED_AT

    assert assessment.assessment_id.root == CANONICAL_ASSESSMENT_ID
    assert assessment.scope_id.root == CANONICAL_SCOPE_ID
    assert assessment.subject_record == _acquisition_reference()
    assert assessment.assessed_at == CANONICAL_ASSESSED_AT
    assert assessment.status is (
        EvidenceCompletenessStatus.SCOPE_SATISFIED_WITH_DECLARED_OMISSIONS
    )
    assert tuple(item.requirement_id.root for item in assessment.requirements) == (
        SATISFIED_REQUIREMENTS + OMISSION_REQUIREMENTS
    )
    assert tuple(item.outcome for item in assessment.requirements) == (
        (EvidenceRequirementOutcome.SATISFIED,) * len(SATISFIED_REQUIREMENTS)
        + (EvidenceRequirementOutcome.INTENTIONALLY_OMITTED,)
        * len(OMISSION_REQUIREMENTS)
    )

    assert envelope.publications is not None
    assert tuple(
        publication.pull_request_identity.repository_scoped_number.root
        for publication in envelope.publications
    ) == ("9", "10")
    assert acquisition_publication.reviewed_revision.full_digest == PR9_REVIEWED
    assert acquisition_publication.reviewed_tree.full_digest == PR9_TREE
    assert acquisition_publication.published_revision.full_digest == PR9_PUBLISHED
    assert correction_publication.reviewed_revision.full_digest == PR10_REVIEWED
    assert correction_publication.reviewed_tree.full_digest == PR10_TREE
    assert correction_publication.published_revision.full_digest == PR10_PUBLISHED

    restored = EvidenceEnvelope.model_validate_json(envelope.model_dump_json())
    assert restored == envelope
    assert restored.model_dump(mode="json") == envelope.model_dump(mode="json")


def test_canonical_current_envelope_is_not_legacy_projectable_or_fabricated() -> None:
    envelope = _canonical_current_envelope()
    result = project_evidence_envelope_to_legacy_artifact_snapshot(envelope)

    assert result.source_envelope == envelope
    assert result.status is CompatibilityStatus.NOT_MAPPABLE
    assert result.projected_snapshot is None
    assert result.reasons == (LegacyEvidenceCompatibilityReason.LEGACY_SNAPSHOT_ABSENT,)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("transformations", (_synthetic_transformation(401),)),
        ("record_relationships", (_synthetic_correction(401),)),
        ("completeness_assessments", (_synthetic_assessment(401),)),
        ("publications", (_synthetic_publication(401),)),
    ],
)
def test_envelope_has_no_reference_closure_requirement(
    field: str,
    value: tuple[object, ...],
) -> None:
    envelope = _envelope(**{field: value})

    assert getattr(envelope, field) == value
    assert envelope.legacy_snapshots is None
    assert envelope.acquisition_runs is None
    assert envelope.request_memberships is None


def test_envelope_does_not_infer_flatten_or_inherit_cross_layer_state() -> None:
    envelope = _envelope(publications=(_synthetic_publication(402),))

    assert not issubclass(EvidenceEnvelope, ArtifactSnapshot)
    assert not issubclass(ArtifactSnapshot, EvidenceEnvelope)
    assert set(EvidenceEnvelope.model_fields) & set(ArtifactSnapshot.model_fields) == {
        "schema_version"
    }
    assert set(envelope.model_dump()) == set(ENVELOPE_FIELDS)
    for forbidden in (
        "source",
        "retrieved_at",
        "payload_text",
        "digest",
        "acquisition_status",
        "transformation_order",
        "correction_precedence",
        "supersession_transitive_closure",
        "latest_publication",
        "repository_snapshot",
        "confidence",
        "claim_review",
        "migration",
    ):
        assert forbidden not in EvidenceEnvelope.model_fields
        assert not hasattr(envelope, forbidden)


def test_compatibility_status_and_s07_reason_vocabularies_are_exact_and_distinct() -> (
    None
):
    assert tuple(item.value for item in CompatibilityStatus) == (
        "native",
        "losslessly_mappable",
        "partially_mappable",
        "not_mappable",
        "unsupported_version",
        "conflict",
    )
    assert tuple(item.value for item in LegacyEvidenceCompatibilityReason) == (
        "legacy_snapshot_absent",
        "multiple_legacy_snapshots_not_representable",
        "modern_components_not_representable",
    )
    assert len(LegacyEvidenceCompatibilityReason.__members__) == 3
    assert not set(LegacyEvidenceCompatibilityReason.__members__) & set(
        compatibility_module.LegacyCompatibilityReason.__members__
    )


def test_legacy_wrapper_is_exact_versioned_lossless_and_source_preserving() -> None:
    snapshot = _synthetic_snapshot(501)
    result = wrap_legacy_artifact_snapshot(snapshot)

    assert result.adapter_id.root == ADAPTER_ID
    assert result.adapter_version.root == ADAPTER_VERSION
    assert result.status is CompatibilityStatus.LOSSLESSLY_MAPPABLE
    assert result.source_snapshot == snapshot
    assert result.envelope.legacy_snapshots == (snapshot,)
    assert result.reasons == ()
    for field in MODERN_COMPONENT_FIELDS:
        assert getattr(result.envelope, field) is None
    assert (
        LegacyArtifactSnapshotEnvelopeMappingResult.model_validate_json(
            result.model_dump_json()
        )
        == result
    )
    assert result.model_dump(mode="json")["reasons"] == []


@pytest.mark.parametrize(
    ("field", "invalid"),
    [
        (
            "adapter_id",
            EvidenceRelationId.model_validate("noncanonical-legacy-adapter"),
        ),
        ("adapter_version", EvidenceVersion.model_validate("2")),
        ("status", CompatibilityStatus.PARTIALLY_MAPPABLE),
        (
            "reasons",
            (LegacyEvidenceCompatibilityReason.MODERN_COMPONENTS_NOT_REPRESENTABLE,),
        ),
    ],
)
def test_mapping_result_rejects_manual_canonical_invariant_mismatches(
    field: str,
    invalid: object,
) -> None:
    valid = wrap_legacy_artifact_snapshot(_synthetic_snapshot(502))
    payload = _model_payload(valid)
    payload[field] = invalid

    with pytest.raises(ValidationError):
        LegacyArtifactSnapshotEnvelopeMappingResult.model_validate(payload)


def test_mapping_result_rejects_snapshot_or_envelope_loss_and_modern_known_empty() -> (
    None
):
    snapshot = _synthetic_snapshot(503)
    valid = wrap_legacy_artifact_snapshot(snapshot)

    different_source = _model_payload(valid)
    different_source["source_snapshot"] = _synthetic_snapshot(504)
    with pytest.raises(ValidationError, match="preserve exactly"):
        LegacyArtifactSnapshotEnvelopeMappingResult.model_validate(different_source)

    different_envelope = _model_payload(valid)
    different_envelope["envelope"] = _envelope(
        legacy_snapshots=(_synthetic_snapshot(505),)
    )
    with pytest.raises(ValidationError, match="preserve exactly"):
        LegacyArtifactSnapshotEnvelopeMappingResult.model_validate(different_envelope)

    modern_known_empty = _model_payload(valid)
    modern_known_empty["envelope"] = _envelope(
        legacy_snapshots=(snapshot,), transformations=()
    )
    with pytest.raises(ValidationError, match="modern component"):
        LegacyArtifactSnapshotEnvelopeMappingResult.model_validate(modern_known_empty)


def test_mapping_result_rejects_fabricated_nonempty_modern_component() -> None:
    snapshot = _synthetic_snapshot(507)
    payload = _model_payload(wrap_legacy_artifact_snapshot(snapshot))
    payload["envelope"] = _envelope(
        legacy_snapshots=(snapshot,),
        request_memberships=(_synthetic_membership(507),),
    )

    with pytest.raises(ValidationError, match="modern component"):
        LegacyArtifactSnapshotEnvelopeMappingResult.model_validate(payload)


@pytest.mark.parametrize(
    "invalid_reasons",
    [
        [],
        ("modern_components_not_representable",),
        None,
    ],
)
def test_mapping_result_rejects_untyped_python_reason_collections(
    invalid_reasons: object,
) -> None:
    valid = wrap_legacy_artifact_snapshot(_synthetic_snapshot(506))
    payload = _model_payload(valid)
    payload["reasons"] = invalid_reasons
    with pytest.raises(ValidationError):
        LegacyArtifactSnapshotEnvelopeMappingResult.model_validate(payload)


@pytest.mark.parametrize(
    ("name", "envelope", "status", "snapshot_index", "reason"),
    [
        (
            "legacy-only",
            _envelope(legacy_snapshots=(_synthetic_snapshot(601),)),
            CompatibilityStatus.LOSSLESSLY_MAPPABLE,
            601,
            None,
        ),
        (
            "legacy-modern-present",
            _envelope(
                legacy_snapshots=(_synthetic_snapshot(602),),
                transformations=(_synthetic_transformation(602),),
            ),
            CompatibilityStatus.PARTIALLY_MAPPABLE,
            None,
            LegacyEvidenceCompatibilityReason.MODERN_COMPONENTS_NOT_REPRESENTABLE,
        ),
        (
            "legacy-modern-known-empty",
            _envelope(legacy_snapshots=(_synthetic_snapshot(603),), transformations=()),
            CompatibilityStatus.PARTIALLY_MAPPABLE,
            None,
            LegacyEvidenceCompatibilityReason.MODERN_COMPONENTS_NOT_REPRESENTABLE,
        ),
        (
            "legacy-none",
            _envelope(transformations=(_synthetic_transformation(604),)),
            CompatibilityStatus.NOT_MAPPABLE,
            None,
            LegacyEvidenceCompatibilityReason.LEGACY_SNAPSHOT_ABSENT,
        ),
        (
            "legacy-known-empty",
            _envelope(
                legacy_snapshots=(),
                transformations=(_synthetic_transformation(605),),
            ),
            CompatibilityStatus.NOT_MAPPABLE,
            None,
            LegacyEvidenceCompatibilityReason.LEGACY_SNAPSHOT_ABSENT,
        ),
        (
            "multiple-legacy",
            _envelope(
                legacy_snapshots=(
                    _synthetic_snapshot(606),
                    _synthetic_snapshot(607),
                )
            ),
            CompatibilityStatus.NOT_MAPPABLE,
            None,
            LegacyEvidenceCompatibilityReason.MULTIPLE_LEGACY_SNAPSHOTS_NOT_REPRESENTABLE,
        ),
    ],
)
def test_projection_six_case_matrix_is_fail_closed_and_semantic_json_stable(
    name: str,
    envelope: EvidenceEnvelope,
    status: CompatibilityStatus,
    snapshot_index: int | None,
    reason: LegacyEvidenceCompatibilityReason | None,
) -> None:
    del name
    result = project_evidence_envelope_to_legacy_artifact_snapshot(envelope)

    assert result.adapter_id.root == ADAPTER_ID
    assert result.adapter_version.root == ADAPTER_VERSION
    assert result.source_envelope == envelope
    assert result.status is status
    expected_snapshot = (
        _synthetic_snapshot(snapshot_index) if snapshot_index is not None else None
    )
    assert result.projected_snapshot == expected_snapshot
    assert result.reasons == (() if reason is None else (reason,))
    assert (
        LegacyArtifactSnapshotProjectionResult.model_validate_json(
            result.model_dump_json()
        )
        == result
    )


@pytest.mark.parametrize("field", MODERN_COMPONENT_FIELDS)
@pytest.mark.parametrize("known_empty", [False, True], ids=("present", "known-empty"))
def test_every_modern_component_state_blocks_silent_lossless_projection(
    field: str,
    known_empty: bool,
) -> None:
    modern_value: tuple[object, ...]
    modern_value = () if known_empty else _component_values(field, 1)
    envelope = _envelope(
        legacy_snapshots=(_synthetic_snapshot(610),), **{field: modern_value}
    )
    result = project_evidence_envelope_to_legacy_artifact_snapshot(envelope)

    assert result.status is CompatibilityStatus.PARTIALLY_MAPPABLE
    assert result.projected_snapshot is None
    assert result.reasons == (
        LegacyEvidenceCompatibilityReason.MODERN_COMPONENTS_NOT_REPRESENTABLE,
    )


def test_multiple_legacy_snapshot_reason_precedes_modern_information() -> None:
    envelope = _envelope(
        legacy_snapshots=(_synthetic_snapshot(611), _synthetic_snapshot(612)),
        transformations=(_synthetic_transformation(611),),
    )
    result = project_evidence_envelope_to_legacy_artifact_snapshot(envelope)

    assert result.status is CompatibilityStatus.NOT_MAPPABLE
    assert result.projected_snapshot is None
    assert result.reasons == (
        LegacyEvidenceCompatibilityReason.MULTIPLE_LEGACY_SNAPSHOTS_NOT_REPRESENTABLE,
    )


@pytest.mark.parametrize(
    ("field", "invalid"),
    [
        (
            "adapter_id",
            EvidenceRelationId.model_validate("noncanonical-legacy-adapter"),
        ),
        ("adapter_version", EvidenceVersion.model_validate("2")),
        ("status", CompatibilityStatus.NOT_MAPPABLE),
        ("projected_snapshot", None),
        (
            "reasons",
            (LegacyEvidenceCompatibilityReason.LEGACY_SNAPSHOT_ABSENT,),
        ),
    ],
)
def test_projection_result_rejects_manual_invariant_mismatches(
    field: str,
    invalid: object,
) -> None:
    valid = project_evidence_envelope_to_legacy_artifact_snapshot(
        _envelope(legacy_snapshots=(_synthetic_snapshot(620),))
    )
    payload = _model_payload(valid)
    payload[field] = invalid
    with pytest.raises(ValidationError):
        LegacyArtifactSnapshotProjectionResult.model_validate(payload)


def test_projection_result_rejects_source_envelope_mismatch_and_untyped_input() -> None:
    valid = project_evidence_envelope_to_legacy_artifact_snapshot(
        _envelope(legacy_snapshots=(_synthetic_snapshot(621),))
    )
    payload = _model_payload(valid)
    payload["source_envelope"] = _envelope(
        transformations=(_synthetic_transformation(621),)
    )
    with pytest.raises(ValidationError):
        LegacyArtifactSnapshotProjectionResult.model_validate(payload)

    invalid_reason_values: tuple[object, ...] = (
        list[object](),
        ("legacy_snapshot_absent",),
        None,
    )
    for invalid_reasons in invalid_reason_values:
        payload = _model_payload(valid)
        payload["reasons"] = invalid_reasons
        with pytest.raises(ValidationError):
            LegacyArtifactSnapshotProjectionResult.model_validate(payload)

    with pytest.raises(TypeError, match="ArtifactSnapshot"):
        wrap_legacy_artifact_snapshot(cast(ArtifactSnapshot, object()))
    with pytest.raises(TypeError, match="EvidenceEnvelope"):
        project_evidence_envelope_to_legacy_artifact_snapshot(
            cast(EvidenceEnvelope, object())
        )


@pytest.mark.parametrize(
    ("model", "factory"),
    [
        (
            LegacyArtifactSnapshotEnvelopeMappingResult,
            lambda: wrap_legacy_artifact_snapshot(_synthetic_snapshot(630)),
        ),
        (
            LegacyArtifactSnapshotProjectionResult,
            lambda: project_evidence_envelope_to_legacy_artifact_snapshot(
                _envelope(legacy_snapshots=(_synthetic_snapshot(631),))
            ),
        ),
    ],
)
def test_adapter_result_required_fields_extra_rejection_and_json_tuple_rebuild(
    model: type[BaseModel],
    factory: Any,
) -> None:
    result = cast(BaseModel, factory())
    for field in tuple(model.model_fields)[1:]:
        payload = result.model_dump(mode="json")
        del payload[field]
        with pytest.raises(ValidationError):
            model.model_validate_json(json.dumps(payload))

    extra = result.model_dump(mode="json")
    extra["unexpected"] = True
    with pytest.raises(ValidationError):
        model.model_validate_json(json.dumps(extra))

    restored = model.model_validate_json(result.model_dump_json())
    assert getattr(restored, "reasons") == ()
    assert type(getattr(restored, "reasons")) is tuple


def test_legacy_modules_bytes_exports_and_artifact_snapshot_contract_are_locked() -> (
    None
):
    source_bytes = SOURCE_SOURCE.read_bytes()
    compatibility_bytes = COMPATIBILITY_SOURCE.read_bytes()
    assert len(source_bytes) == SOURCE_LENGTH
    assert sha256(source_bytes).hexdigest() == SOURCE_SHA256
    assert len(compatibility_bytes) == COMPATIBILITY_LENGTH
    assert sha256(compatibility_bytes).hexdigest() == COMPATIBILITY_SHA256
    assert tuple(compatibility_module.__all__) == EXPECTED_COMPATIBILITY_EXPORTS

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
    assert tuple(SourceLocator.model_fields) == (
        "provider",
        "repository",
        "object_kind",
        "object_id",
    )
    assert ArtifactSnapshot.model_config == STRICT_RECORD_CONFIG
    assert SourceLocator.model_config == STRICT_RECORD_CONFIG


def test_wrapper_preserves_legacy_locator_without_remapping_or_modern_fabrication() -> (
    None
):
    snapshot = _synthetic_snapshot(701)
    wrapped = wrap_legacy_artifact_snapshot(snapshot)
    preserved = wrapped.envelope.legacy_snapshots

    assert preserved is not None
    assert preserved == (snapshot,)
    assert preserved[0].source == snapshot.source
    assert preserved[0].model_dump(mode="json") == snapshot.model_dump(mode="json")
    assert not any(
        getattr(wrapped.envelope, field) is not None
        for field in MODERN_COMPONENT_FIELDS
    )


def test_s07_surface_has_no_io_dynamic_adapter_or_future_contract_capability() -> None:
    tree = ast.parse(EVIDENCE_SOURCE.read_text(encoding="utf-8"))
    reviewed_plain_imports = {"json", "re"}
    reviewed_from_imports = {
        "datetime": {"UTC", "datetime", "timedelta"},
        "enum": {"StrEnum"},
        "faultatlas.domain.compatibility": {"CompatibilityStatus"},
        "faultatlas.domain.identity": {
            "AuthorityRole",
            "NumberedSourceObjectIdentity",
            "ProviderAuthority",
            "ProviderGlobalId",
            "RepositoryIdentity",
            "SourceObjectKind",
        },
        "faultatlas.domain.revision": {"GitCommitIdentity", "GitTreeIdentity"},
        "faultatlas.domain.source": {"ArtifactSnapshot"},
        "pydantic": {
            "AwareDatetime",
            "BaseModel",
            "ConfigDict",
            "Field",
            "RootModel",
            "StringConstraints",
            "ValidationInfo",
            "field_validator",
            "model_validator",
        },
        "typing": {"Annotated", "Literal", "Self", "cast"},
    }
    unreviewed_imports: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.asname is not None or alias.name not in reviewed_plain_imports:
                    unreviewed_imports.append((node.lineno, ast.unparse(node)))
        elif isinstance(node, ast.ImportFrom):
            reviewed_names = (
                set[str]()
                if node.level
                else reviewed_from_imports.get(node.module or "", set[str]())
            )
            for alias in node.names:
                if alias.asname is not None or alias.name not in reviewed_names:
                    unreviewed_imports.append((node.lineno, ast.unparse(node)))
    assert not unreviewed_imports

    adapter_function_names = {
        "wrap_legacy_artifact_snapshot",
        "project_evidence_envelope_to_legacy_artifact_snapshot",
    }
    adapter_functions = [
        node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name in adapter_function_names
    ]
    assert {node.name for node in adapter_functions} == adapter_function_names
    approved_builtin_names = {
        "AssertionError",
        "TypeError",
        "ValueError",
        "all",
        "any",
        "bool",
        "classmethod",
        "dict",
        "enumerate",
        "frozenset",
        "int",
        "isinstance",
        "len",
        "list",
        "object",
        "ord",
        "set",
        "str",
        "tuple",
        "type",
    }
    approved_call_operations = {
        "add",
        "astimezone",
        "compile",
        "dumps",
        "endswith",
        "fromisoformat",
        "fullmatch",
        "isascii",
        "isspace",
        "model_validate",
        "model_validate_json",
        "search",
        "split",
        "startswith",
        "strip",
        "utcoffset",
    }
    reviewed_node_kinds = {
        "And",
        "AnnAssign",
        "Assign",
        "Attribute",
        "BinOp",
        "BitAnd",
        "BitOr",
        "BoolOp",
        "Call",
        "ClassDef",
        "Compare",
        "Constant",
        "Eq",
        "ExceptHandler",
        "Expr",
        "For",
        "FormattedValue",
        "FunctionDef",
        "GeneratorExp",
        "Gt",
        "If",
        "IfExp",
        "Import",
        "ImportFrom",
        "In",
        "Is",
        "IsNot",
        "JoinedStr",
        "List",
        "Load",
        "Lt",
        "LtE",
        "Module",
        "Mult",
        "Name",
        "Not",
        "NotEq",
        "NotIn",
        "Or",
        "Raise",
        "Return",
        "Set",
        "SetComp",
        "Slice",
        "Store",
        "Subscript",
        "Try",
        "Tuple",
        "TypeAlias",
        "USub",
        "UnaryOp",
        "alias",
        "arg",
        "arguments",
        "comprehension",
        "keyword",
    }
    reviewed_top_level_statements = {
        "AnnAssign",
        "Assign",
        "ClassDef",
        "Expr",
        "FunctionDef",
        "Import",
        "ImportFrom",
        "TypeAlias",
    }

    assert not {type(node).__name__ for node in ast.walk(tree)} - reviewed_node_kinds
    assert (
        not {type(node).__name__ for node in tree.body} - reviewed_top_level_statements
    )
    assert not [
        node.lineno
        for node in tree.body
        if isinstance(node, ast.Expr) and not isinstance(node.value, ast.Constant)
    ]

    parent_nodes: dict[int, ast.AST] = {}
    for parent in ast.walk(tree):
        for child in ast.iter_child_nodes(parent):
            parent_nodes[id(child)] = parent

    scope_kinds = (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)

    def enclosing_scope(node: ast.AST) -> ast.AST:
        current = parent_nodes.get(id(node))
        while current is not None and not isinstance(current, scope_kinds):
            current = parent_nodes.get(id(current))
        return current if current is not None else tree

    scope_bindings: dict[int, set[str]] = {}
    module_bindings: list[str] = []

    def record_binding(node: ast.AST, name: str) -> None:
        scope = enclosing_scope(node)
        scope_bindings.setdefault(id(scope), set()).add(name)
        if scope is tree:
            module_bindings.append(name)

    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and isinstance(node.ctx, (ast.Store, ast.Del)):
            record_binding(node, node.id)
        elif isinstance(node, ast.arg):
            record_binding(node, node.arg)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            record_binding(node, node.name)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            for alias in node.names:
                record_binding(node, (alias.asname or alias.name).split(".")[0])
        elif isinstance(node, ast.ExceptHandler) and node.name is not None:
            record_binding(node, node.name)

    module_declared_names = scope_bindings.get(id(tree), set())
    assert not [name for name in module_bindings if module_bindings.count(name) > 1]
    assert not module_declared_names & approved_builtin_names
    assert not [
        name
        for scope_id, names in scope_bindings.items()
        if scope_id != id(tree)
        for name in names & (module_declared_names | approved_builtin_names)
    ]

    def resolvable_names(node: ast.AST) -> set[str]:
        names = module_declared_names | approved_builtin_names
        scope = enclosing_scope(node)
        while True:
            names = names | scope_bindings.get(id(scope), set())
            if scope is tree:
                return names
            scope = enclosing_scope(scope)

    assert not [
        (node.lineno, node.id)
        for node in ast.walk(tree)
        if isinstance(node, ast.Name)
        and isinstance(node.ctx, ast.Load)
        and node.id not in resolvable_names(node)
    ]

    approved_call_names = module_declared_names | approved_builtin_names
    assert not [
        (node.lineno, ast.unparse(node.func))
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and not (
            isinstance(node.func, ast.Name) and node.func.id in approved_call_names
        )
        and not (
            isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name)
            and node.func.attr in approved_call_operations
        )
    ]

    assert not [
        (node.lineno, node.attr)
        for node in ast.walk(tree)
        if isinstance(node, ast.Attribute) and node.attr.startswith("_")
    ]

    source_locator_mapper_symbol = "map_legacy_source_locator"
    repository_identity_symbol = "RepositoryIdentity"

    def symbol_references(root: ast.AST, symbol: str) -> list[ast.expr]:
        return [
            reference
            for reference in ast.walk(root)
            if isinstance(reference, ast.expr)
            if (isinstance(reference, ast.Name) and reference.id == symbol)
            or (isinstance(reference, ast.Attribute) and reference.attr == symbol)
        ]

    assert not [
        (reference.lineno, ast.unparse(reference))
        for reference in symbol_references(tree, source_locator_mapper_symbol)
    ]

    annotation_roots: list[ast.AST] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.arg) and node.annotation is not None:
            annotation_roots.append(node.annotation)
        elif isinstance(node, ast.AnnAssign):
            annotation_roots.append(node.annotation)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.returns is not None:
                annotation_roots.append(node.returns)

    def direct_repository_identity_reference_ids(root: ast.AST) -> set[int]:
        if isinstance(root, ast.Name):
            return {id(root)} if root.id == repository_identity_symbol else set()
        if isinstance(root, ast.Attribute):
            base = root.value
            while isinstance(base, ast.Attribute):
                base = base.value
            if root.attr == repository_identity_symbol and isinstance(base, ast.Name):
                return {id(root)}
            return set()
        if isinstance(root, ast.Tuple):
            return {
                reference_id
                for element in root.elts
                for reference_id in direct_repository_identity_reference_ids(element)
            }
        return set()

    allowed_repository_identity_reference_ids = {
        reference_id
        for annotation in annotation_roots
        for reference_id in direct_repository_identity_reference_ids(annotation)
    }
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or len(node.args) < 2:
            continue
        if not isinstance(node.func, ast.Name) or node.func.id != "isinstance":
            continue
        allowed_repository_identity_reference_ids.update(
            direct_repository_identity_reference_ids(node.args[1])
        )

    assert not [
        (reference.lineno, ast.unparse(reference))
        for reference in symbol_references(tree, repository_identity_symbol)
        if id(reference) not in allowed_repository_identity_reference_ids
    ]

    adapter_call_targets = {
        ast.unparse(node.func)
        for function in adapter_functions
        for node in ast.walk(function)
        if isinstance(node, ast.Call)
    }
    assert adapter_call_targets == {
        "EvidenceEnvelope",
        "EvidenceRelationId.model_validate",
        "EvidenceVersion.model_validate",
        "LegacyArtifactSnapshotEnvelopeMappingResult",
        "LegacyArtifactSnapshotProjectionResult",
        "TypeError",
        "any",
        "cast",
        "isinstance",
        "len",
    }

    class_names = {node.name for node in tree.body if isinstance(node, ast.ClassDef)}
    assert not any(
        token in name.lower()
        for name in class_names
        for token in (
            "corpus",
            "migration",
            "repositorysnapshot",
            "reader",
            "registry",
            "storage",
            "writer",
        )
    )
    assert not hasattr(evidence_module, "EvidenceEnvelopeReader")
    assert not hasattr(evidence_module, "EvidenceEnvelopeWriter")
    assert not hasattr(evidence_module, "EvidenceEnvelopeCanonicalBytes")
    assert not hasattr(evidence_module, "EvidenceRepositorySnapshot")
    assert not hasattr(evidence_module, "EvidenceConfidenceReview")

    evidence_bytes = EVIDENCE_SOURCE.read_bytes()
    assert b"reference_corpus" not in evidence_bytes
    assert EVIDENCE_CONTRACT_CORPUS_RELATIVE.encode() not in evidence_bytes
    corpus_reader_tokens = ("corpus", "reader", "writer", "registry", "storage")
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            module = "" if isinstance(node, ast.Import) else (node.module or "")
            names = [module, *(alias.name for alias in node.names)]
            assert not any(
                token in name.casefold()
                for name in names
                for token in corpus_reader_tokens
            )
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            assert node.func.id not in {"open", "eval", "exec", "__import__"}
        if isinstance(node, ast.Attribute):
            assert node.attr not in {
                "read_bytes",
                "read_text",
                "write_bytes",
                "write_text",
                "open",
            }
    corpus_executor = REPOSITORY_ROOT / "tests/test_evidence_contract_corpus.py"
    assert corpus_executor.is_file()
    assert corpus_executor.relative_to(REPOSITORY_ROOT).parts[0] == "tests"
    assert not (REPOSITORY_ROOT / "src/faultatlas/domain/corpus.py").exists()
    production_files = {
        path.relative_to(REPOSITORY_ROOT).as_posix()
        for path in (REPOSITORY_ROOT / "src").rglob("*.py")
    }
    assert production_files == EXPECTED_PRODUCTION_FILES


@pytest.mark.parametrize("missing", ENVELOPE_FIELDS[1:])
def test_envelope_failure_sensitivity_for_every_missing_field(missing: str) -> None:
    payload = _envelope(legacy_snapshots=(_synthetic_snapshot(801),)).model_dump(
        mode="json"
    )
    del payload[missing]
    with pytest.raises(ValidationError):
        EvidenceEnvelope.model_validate_json(json.dumps(payload))


@pytest.mark.parametrize("field", tuple(COMPONENT_CAPS))
def test_envelope_rejects_wrong_nested_python_type_without_coercion(field: str) -> None:
    with pytest.raises(ValidationError, match="entries must be"):
        _envelope(**{field: (object(),)})


def test_envelope_has_no_identity_or_durable_canonical_byte_contract() -> None:
    assert "envelope_id" not in EvidenceEnvelope.model_fields
    assert "canonicalization" not in EvidenceEnvelope.model_fields
    assert "sha256" not in EvidenceEnvelope.model_fields
    assert "byte_length" not in EvidenceEnvelope.model_fields
    envelope = _canonical_current_envelope()
    semantic_json = envelope.model_dump(mode="json")
    assert isinstance(semantic_json, dict)
    assert EvidenceEnvelope.model_validate_json(json.dumps(semantic_json)) == envelope
