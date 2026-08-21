from __future__ import annotations

import ast
import json
import stat
from datetime import UTC, datetime, timedelta, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any, cast

import pytest
from pydantic import BaseModel, RootModel, ValidationError

import faultatlas
import faultatlas.domain as domain_package
import faultatlas.domain.evidence as evidence_module
from faultatlas.domain.evidence import (
    AcquisitionRunStatus,
    ArtifactByteLength,
    ArtifactSha256Digest,
    DurableEvidenceRecordReference,
    EvidenceCanonicalization,
    EvidenceCompletenessAssessment,
    EvidenceCompletenessStatus,
    EvidenceDispositionReason,
    EvidenceOmission,
    EvidencePublication,
    EvidencePublicationMethod,
    EvidenceRecordFormat,
    EvidenceRelationId,
    EvidenceRequirementId,
    EvidenceRequirementOutcome,
    EvidenceRequirementResult,
    EvidenceScopeId,
    EvidenceVersion,
    PublicationCheckEvent,
    PublicationCheckName,
    SuccessfulPublicationCheck,
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
from faultatlas.domain.source import ArtifactSnapshot

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_SOURCE = REPOSITORY_ROOT / "src/faultatlas/domain/evidence.py"
SOURCE_SOURCE = REPOSITORY_ROOT / "src/faultatlas/domain/source.py"
ACQUISITION_PATH = (
    REPOSITORY_ROOT
    / "reference_corpus"
    / "pytest-4412"
    / "acquisitions"
    / "run-0001-s04-v1-base-4c9cde74-head-690a63b9"
    / "acquisition.json"
)
CORRECTION_PATH = (
    REPOSITORY_ROOT
    / "reference_corpus"
    / "pytest-4412"
    / "corrections"
    / "s04-c01-acquisition-closure"
    / "correction.json"
)

CANONICAL_VERSION = "1"
CANONICAL_CANONICALIZATION = "json-sort-keys-compact-utf8-lf-v1"
ACQUISITION_FORMAT = "faultatlas-acquisition"
ACQUISITION_LENGTH = 61_283
ACQUISITION_SHA256 = "1c29093bf1537e9b824a18df1848b71a8da014f544bc9f385707eb0e000a1318"
CORRECTION_FORMAT = "faultatlas-pytest-4412-acquisition-closure-addendum"
CORRECTION_LENGTH = 60_832
CORRECTION_SHA256 = "44491ee512d2c2022110b83967fb6fa86d13045bc8404ea490d7a08b7aef24a2"
ARTIFACT_SNAPSHOT_SOURCE_LENGTH = 4_336
ARTIFACT_SNAPSHOT_SOURCE_SHA256 = (
    "034e53fd58212f0e34376bbc790fc3e74057031aaed4d7d89fb67904bdd380bf"
)

CANONICAL_ASSESSMENT_ID = "s04-c01-declared-evidence-scope"
CANONICAL_SCOPE_ID = "pytest-4412-s04-declared-retention-scope"
CANONICAL_ASSESSED_AT = datetime(2026, 7, 30, 19, 17, 9, 655780, tzinfo=UTC)
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
CANONICAL_REQUIREMENTS = SATISFIED_REQUIREMENTS + OMISSION_REQUIREMENTS

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

PR9_REVIEWED = "32f51f569ec554573f29bfa4d49b4f9d40d555c7"
PR9_TREE = "fffb04451520453cd00b4c2fc4acf1edd2147d5e"
PR9_PUBLISHED = "fb9b7061c2cf70bb6d4bdceb8fd023c2bfbce32b"
PR10_REVIEWED = "60400fcb301e108dbd14477ec6bb30b42157f12d"
PR10_TREE = "c50f510c38bb2f56c0b38f14b9f8cb7a09075703"
PR10_PUBLISHED = "8ece1cfa49c718345028bc6d03aca5e4fcdf434c"

SYNTHETIC_TIME = datetime(2026, 8, 9, 12, 0, 0, tzinfo=UTC)


def _provider(value: str = "github") -> ProviderKey:
    return ProviderKey.model_validate(value)


def _repository(
    *,
    provider: str = "github",
    provider_repository_id: str = "1303365003",
) -> RepositoryIdentity:
    return RepositoryIdentity(
        provider=_provider(provider),
        provider_repository_id=ProviderRepositoryId.model_validate(
            provider_repository_id
        ),
    )


def _authority(
    *,
    provider: str = "github",
    role: AuthorityRole = AuthorityRole.RETRIEVAL,
    host: str = "api.github.com",
) -> ProviderAuthority:
    return ProviderAuthority(
        provider=_provider(provider),
        role=role,
        host=host,
    )


def _record_reference(
    *,
    format_name: str,
    digest: str,
    byte_length: int,
    version: str = CANONICAL_VERSION,
    canonicalization: str = CANONICAL_CANONICALIZATION,
) -> DurableEvidenceRecordReference:
    return DurableEvidenceRecordReference(
        format_name=EvidenceRecordFormat.model_validate(format_name),
        format_version=EvidenceVersion.model_validate(version),
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


def _synthetic_reference(index: int = 1) -> DurableEvidenceRecordReference:
    return _record_reference(
        format_name="faultatlas-synthetic-record",
        digest=f"{index + 1000:064x}",
        byte_length=index,
        canonicalization="synthetic-json-v1",
    )


def _requirement_id(value: str) -> EvidenceRequirementId:
    return EvidenceRequirementId.model_validate(value)


def _omission(
    requirement: str,
    *,
    outcome: EvidenceRequirementOutcome = (
        EvidenceRequirementOutcome.INTENTIONALLY_OMITTED
    ),
    sources: tuple[DurableEvidenceRecordReference, ...] | None = None,
) -> EvidenceOmission:
    source_records = (
        (_correction_reference(), _acquisition_reference())
        if sources is None
        else sources
    )
    return EvidenceOmission(
        omission_id=EvidenceRelationId.model_validate(
            f"s04-c01.omission.{requirement}"
        ),
        requirement_id=_requirement_id(requirement),
        outcome=outcome,
        reason=EvidenceDispositionReason.model_validate(CANONICAL_REASON),
        source_records=source_records,
    )


def _satisfied(
    requirement: str,
    *,
    records: tuple[DurableEvidenceRecordReference, ...] | None = None,
) -> EvidenceRequirementResult:
    return EvidenceRequirementResult(
        requirement_id=_requirement_id(requirement),
        outcome=EvidenceRequirementOutcome.SATISFIED,
        evidence_records=((_acquisition_reference(),) if records is None else records),
        omission=None,
    )


def _omitted_result(
    requirement: str,
    *,
    outcome: EvidenceRequirementOutcome = (
        EvidenceRequirementOutcome.INTENTIONALLY_OMITTED
    ),
) -> EvidenceRequirementResult:
    return EvidenceRequirementResult(
        requirement_id=_requirement_id(requirement),
        outcome=outcome,
        evidence_records=None,
        omission=_omission(requirement, outcome=outcome),
    )


def _not_applicable(requirement: str) -> EvidenceRequirementResult:
    return EvidenceRequirementResult(
        requirement_id=_requirement_id(requirement),
        outcome=EvidenceRequirementOutcome.NOT_APPLICABLE,
        evidence_records=None,
        omission=None,
    )


def _assessment(
    requirements: tuple[EvidenceRequirementResult, ...],
    *,
    status: EvidenceCompletenessStatus,
    assessment_id: str = "synthetic-assessment",
    scope_id: str = "synthetic-scope",
    subject: DurableEvidenceRecordReference | None = None,
    assessed_at: datetime = SYNTHETIC_TIME,
) -> EvidenceCompletenessAssessment:
    return EvidenceCompletenessAssessment(
        assessment_id=EvidenceRelationId.model_validate(assessment_id),
        subject_record=_synthetic_reference(900) if subject is None else subject,
        scope_id=EvidenceScopeId.model_validate(scope_id),
        assessed_at=assessed_at,
        status=status,
        requirements=requirements,
    )


def _canonical_assessment() -> EvidenceCompletenessAssessment:
    requirements = tuple(_satisfied(item) for item in SATISFIED_REQUIREMENTS) + tuple(
        _omitted_result(item) for item in OMISSION_REQUIREMENTS
    )
    return _assessment(
        requirements,
        status=(EvidenceCompletenessStatus.SCOPE_SATISFIED_WITH_DECLARED_OMISSIONS),
        assessment_id=CANONICAL_ASSESSMENT_ID,
        scope_id=CANONICAL_SCOPE_ID,
        subject=_acquisition_reference(),
        assessed_at=CANONICAL_ASSESSED_AT,
    )


def _commit(
    digest: str,
    *,
    algorithm: GitHashAlgorithm = GitHashAlgorithm.SHA1,
) -> GitCommitIdentity:
    return GitCommitIdentity(
        kind=GitObjectKind.COMMIT,
        algorithm=algorithm,
        full_digest=digest,
    )


def _tree(
    digest: str,
    *,
    algorithm: GitHashAlgorithm = GitHashAlgorithm.SHA1,
) -> GitTreeIdentity:
    return GitTreeIdentity(
        kind=GitObjectKind.TREE,
        algorithm=algorithm,
        full_digest=digest,
    )


def _pull_request_identity(
    number: str,
    *,
    repository: RepositoryIdentity | None = None,
    kind: SourceObjectKind = SourceObjectKind.PULL_REQUEST,
) -> NumberedSourceObjectIdentity:
    return NumberedSourceObjectIdentity(
        repository_identity=_repository() if repository is None else repository,
        kind=kind,
        repository_scoped_number=RepositoryScopedNumber.model_validate(number),
    )


def _check(
    *,
    event: PublicationCheckEvent,
    head: GitCommitIdentity,
    run_id: str,
    job_id: str,
    authority: ProviderAuthority | None = None,
    attempt: int = 1,
) -> SuccessfulPublicationCheck:
    return SuccessfulPublicationCheck(
        authority=_authority() if authority is None else authority,
        workflow_name=PublicationCheckName.model_validate("CI"),
        context=PublicationCheckName.model_validate("validate"),
        event=event,
        run_id=ProviderGlobalId.model_validate(run_id),
        job_id=ProviderGlobalId.model_validate(job_id),
        attempt=attempt,
        head_revision=head,
        conclusion="success",
    )


def _publication_data(
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
) -> dict[str, object]:
    reviewed = _commit(reviewed_digest)
    published = _commit(published_digest)
    tree = _tree(tree_digest)
    return {
        "publication_id": EvidenceRelationId.model_validate(publication_id),
        "subject_record": subject,
        "repository_identity": _repository(),
        "pull_request_identity": _pull_request_identity(pull_request_number),
        "reviewed_revision": reviewed,
        "reviewed_tree": tree,
        "published_revision": published,
        "published_tree": tree,
        "method": EvidencePublicationMethod.PROTECTED_PULL_REQUEST_SQUASH_MERGE,
        "published_at": published_at,
        "pull_request_check": _check(
            event=PublicationCheckEvent.PULL_REQUEST,
            head=reviewed,
            run_id=pull_request_run_id,
            job_id=pull_request_job_id,
        ),
        "main_check": _check(
            event=PublicationCheckEvent.PUSH,
            head=published,
            run_id=main_run_id,
            job_id=main_job_id,
        ),
    }


def _acquisition_publication() -> EvidencePublication:
    return EvidencePublication.model_validate(
        _publication_data(
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
    )


def _correction_publication() -> EvidencePublication:
    return EvidencePublication.model_validate(
        _publication_data(
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
    )


def _model_payload(model: BaseModel) -> dict[str, object]:
    return {
        field_name: cast(object, getattr(model, field_name))
        for field_name in model.__class__.model_fields
    }


def _load_json(path: Path) -> dict[str, Any]:
    value = cast(object, json.loads(path.read_bytes()))
    assert isinstance(value, dict)
    return cast(dict[str, Any], value)


def _assert_record_config(model: type[BaseModel]) -> None:
    assert model.model_config == {
        "extra": "forbid",
        "frozen": True,
        "revalidate_instances": "always",
        "strict": True,
        "validate_default": True,
    }


def _assert_root_config(model: type[RootModel[Any]]) -> None:
    assert model.model_config == {
        "frozen": True,
        "revalidate_instances": "always",
        "strict": True,
        "validate_default": True,
    }


def test_exact_s06_export_and_production_surfaces() -> None:
    assert tuple(evidence_module.__all__) == EXPECTED_EVIDENCE_EXPORTS
    assert len(evidence_module.__all__) == len(set(evidence_module.__all__)) == 58
    assert not set(EXPECTED_EVIDENCE_EXPORTS) & set(vars(faultatlas))
    assert not set(EXPECTED_EVIDENCE_EXPORTS) & set(vars(domain_package))
    production_files = {
        path.relative_to(REPOSITORY_ROOT).as_posix()
        for path in (REPOSITORY_ROOT / "src").rglob("*.py")
    }
    assert production_files == EXPECTED_PRODUCTION_FILES
    assert len(production_files) == len(EXPECTED_PRODUCTION_FILES)
    assert faultatlas.__all__ == ["__version__"]


def test_exact_s06_model_fields_and_configs() -> None:
    expected_fields = {
        EvidenceOmission: (
            "schema_version",
            "omission_id",
            "requirement_id",
            "outcome",
            "reason",
            "source_records",
        ),
        EvidenceRequirementResult: (
            "schema_version",
            "requirement_id",
            "outcome",
            "evidence_records",
            "omission",
        ),
        EvidenceCompletenessAssessment: (
            "schema_version",
            "assessment_id",
            "subject_record",
            "scope_id",
            "assessed_at",
            "status",
            "requirements",
        ),
        SuccessfulPublicationCheck: (
            "schema_version",
            "authority",
            "workflow_name",
            "context",
            "event",
            "run_id",
            "job_id",
            "attempt",
            "head_revision",
            "conclusion",
        ),
        EvidencePublication: (
            "schema_version",
            "publication_id",
            "subject_record",
            "repository_identity",
            "pull_request_identity",
            "reviewed_revision",
            "reviewed_tree",
            "published_revision",
            "published_tree",
            "method",
            "published_at",
            "pull_request_check",
            "main_check",
        ),
    }
    for model, fields in expected_fields.items():
        assert tuple(model.model_fields) == fields
        _assert_record_config(model)
    for root_model in (
        EvidenceScopeId,
        EvidenceRequirementId,
        EvidenceDispositionReason,
        PublicationCheckName,
    ):
        _assert_root_config(root_model)


def test_s08_plus_and_io_surfaces_remain_absent() -> None:
    source = EVIDENCE_SOURCE.read_text(encoding="utf-8")
    tree = ast.parse(source)
    definitions = {
        node.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
    }
    forbidden_definitions = {
        "EvidenceAdapterRegistry",
        "EvidenceConfidence",
        "EvidenceContractCorpus",
        "EvidenceMigration",
        "EvidencePersistence",
        "EvidenceReader",
        "EvidenceReview",
        "EvidenceWriter",
        "EvidenceStorage",
        "RepositorySnapshot",
    }
    assert not definitions & forbidden_definitions
    forbidden_import_roots = {
        "os",
        "pathlib",
        "socket",
        "subprocess",
        "urllib",
        "requests",
        "httpx",
    }
    imports = {
        alias.name.partition(".")[0]
        for node in tree.body
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    imports.update(
        node.module.partition(".")[0]
        for node in tree.body
        if isinstance(node, ast.ImportFrom) and node.module is not None
    )
    assert not imports & forbidden_import_roots
    assert not any(
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id in {"open", "exec", "eval", "compile", "__import__"}
        for node in ast.walk(tree)
    )


@pytest.mark.parametrize(
    "model,value",
    (
        (EvidenceScopeId, "pytest-4412-s04-declared-retention-scope"),
        (EvidenceScopeId, "a"),
        (EvidenceScopeId, "a" * 160),
        (EvidenceRequirementId, "retained_compare_diff"),
        (EvidenceRequirementId, "credentials_tokens_and_local_paths"),
        (EvidenceRequirementId, "a" * 160),
    ),
)
def test_scope_and_requirement_ids_accept_exact_bounded_lexemes(
    model: type[RootModel[Any]],
    value: str,
) -> None:
    identifier = model.model_validate(value)
    assert identifier.root == value
    assert model.model_validate_json(identifier.model_dump_json()) == identifier


@pytest.mark.parametrize("model", (EvidenceScopeId, EvidenceRequirementId))
@pytest.mark.parametrize(
    "value",
    (
        "",
        "Uppercase",
        "-leading",
        "trailing-",
        ".leading",
        "trailing.",
        "with/slash",
        "with\\backslash",
        "with:colon",
        "with space",
        "with\tcontrol",
        "café",
        "a" * 161,
        1,
        True,
    ),
)
def test_scope_and_requirement_ids_reject_malformed_or_coerced_values(
    model: type[RootModel[Any]],
    value: object,
) -> None:
    with pytest.raises(ValidationError):
        model.model_validate(value)


@pytest.mark.parametrize(
    "value",
    ("declared-retention-policy", "a", "a" * 160, "synthetic-reason-2"),
)
def test_disposition_reason_accepts_exact_reason_codes(value: str) -> None:
    reason = EvidenceDispositionReason.model_validate(value)
    assert reason.root == value
    assert (
        EvidenceDispositionReason.model_validate_json(reason.model_dump_json())
        == reason
    )


@pytest.mark.parametrize(
    "value",
    (
        "",
        "Declared-retention-policy",
        "-leading",
        "trailing-",
        "under_score",
        "with.dot",
        "with/slash",
        "with\\backslash",
        "with:colon",
        "with space",
        "control\ncode",
        "nonascii-é",
        "a" * 161,
        3,
        False,
    ),
)
def test_disposition_reason_rejects_malformed_or_coerced_values(
    value: object,
) -> None:
    with pytest.raises(ValidationError):
        EvidenceDispositionReason.model_validate(value)


def test_requirement_outcome_and_completeness_vocabularies_are_exact() -> None:
    assert tuple(item.value for item in EvidenceRequirementOutcome) == (
        "satisfied",
        "intentionally_omitted",
        "unavailable",
        "inaccessible",
        "unknown",
        "unsupported",
        "not_applicable",
    )
    assert tuple(item.value for item in EvidenceCompletenessStatus) == (
        "scope_satisfied",
        "scope_satisfied_with_declared_omissions",
        "scope_partial",
        "scope_unknown",
    )
    with pytest.raises(ValueError):
        EvidenceRequirementOutcome("omitted")
    with pytest.raises(ValueError):
        EvidenceCompletenessStatus("complete")


def test_all_canonical_omissions_are_exact_and_source_ordered() -> None:
    assessment = _canonical_assessment()
    assert tuple(item.requirement_id.root for item in assessment.requirements) == (
        CANONICAL_REQUIREMENTS
    )
    assert len(assessment.requirements) == 17
    assert len({item.requirement_id.root for item in assessment.requirements}) == 17
    omissions = tuple(
        cast(EvidenceOmission, item.omission) for item in assessment.requirements[2:]
    )
    assert tuple(item.requirement_id.root for item in omissions) == (
        OMISSION_REQUIREMENTS
    )
    assert tuple(item.omission_id.root for item in omissions) == tuple(
        f"s04-c01.omission.{requirement}" for requirement in OMISSION_REQUIREMENTS
    )
    assert all(
        item.outcome is EvidenceRequirementOutcome.INTENTIONALLY_OMITTED
        for item in omissions
    )
    assert all(item.reason.root == CANONICAL_REASON for item in omissions)
    assert all(
        item.source_records == (_correction_reference(), _acquisition_reference())
        for item in omissions
    )
    assert (
        EvidenceCompletenessAssessment.model_validate_json(assessment.model_dump_json())
        == assessment
    )


@pytest.mark.parametrize(
    "outcome",
    (
        EvidenceRequirementOutcome.INTENTIONALLY_OMITTED,
        EvidenceRequirementOutcome.UNAVAILABLE,
        EvidenceRequirementOutcome.INACCESSIBLE,
        EvidenceRequirementOutcome.UNKNOWN,
        EvidenceRequirementOutcome.UNSUPPORTED,
    ),
)
def test_omission_accepts_only_explicit_omission_outcomes(
    outcome: EvidenceRequirementOutcome,
) -> None:
    omission = _omission("synthetic-omission", outcome=outcome)
    assert omission.outcome is outcome
    assert EvidenceOmission.model_validate_json(omission.model_dump_json()) == omission


@pytest.mark.parametrize(
    "outcome",
    (
        EvidenceRequirementOutcome.SATISFIED,
        EvidenceRequirementOutcome.NOT_APPLICABLE,
    ),
)
def test_omission_rejects_non_omission_outcomes(
    outcome: EvidenceRequirementOutcome,
) -> None:
    data = _model_payload(_omission("synthetic-omission"))
    data["outcome"] = outcome
    with pytest.raises(ValidationError):
        EvidenceOmission.model_validate(data)


def test_omission_source_record_tuple_uniqueness_and_caps() -> None:
    sources = tuple(_synthetic_reference(index) for index in range(1, 17))
    omission = _omission("synthetic-omission", sources=sources)
    assert omission.source_records == sources

    for invalid in ((), (sources[0], sources[0])):
        data = _model_payload(omission)
        data["source_records"] = invalid
        with pytest.raises(ValidationError):
            EvidenceOmission.model_validate(data)

    over_cap = tuple(_synthetic_reference(index) for index in range(1, 18))
    data = _model_payload(omission)
    data["source_records"] = over_cap
    with pytest.raises(ValidationError, match="at most 16"):
        EvidenceOmission.model_validate(data)

    data["source_records"] = [object() for _ in range(17)]
    with pytest.raises(ValidationError, match="at most 16"):
        EvidenceOmission.model_validate(data)

    data["source_records"] = [sources[0]]
    with pytest.raises(ValidationError, match="tuple"):
        EvidenceOmission.model_validate(data)


@pytest.mark.parametrize("extra", ("payload", "prose", "omitted_content"))
def test_omission_rejects_payload_prose_and_extra_fields(extra: str) -> None:
    data = _model_payload(_omission("synthetic-omission"))
    data[extra] = "forbidden"
    with pytest.raises(ValidationError):
        EvidenceOmission.model_validate(data)


def test_requirement_result_accepts_every_valid_outcome_shape() -> None:
    results = (
        _satisfied("satisfied"),
        _omitted_result("intentionally-omitted"),
        _omitted_result("unavailable", outcome=EvidenceRequirementOutcome.UNAVAILABLE),
        _omitted_result(
            "inaccessible", outcome=EvidenceRequirementOutcome.INACCESSIBLE
        ),
        _omitted_result("unknown", outcome=EvidenceRequirementOutcome.UNKNOWN),
        _omitted_result("unsupported", outcome=EvidenceRequirementOutcome.UNSUPPORTED),
        _not_applicable("not-applicable"),
    )
    assert tuple(item.outcome for item in results) == tuple(EvidenceRequirementOutcome)
    assert all(
        EvidenceRequirementResult.model_validate_json(item.model_dump_json()) == item
        for item in results
    )


@pytest.mark.parametrize(
    "mutation",
    (
        "satisfied_without_evidence",
        "satisfied_with_omission",
        "omission_without_omission",
        "omission_with_evidence",
        "requirement_mismatch",
        "outcome_mismatch",
        "not_applicable_with_evidence",
        "not_applicable_with_omission",
    ),
)
def test_requirement_result_rejects_inconsistent_shapes(mutation: str) -> None:
    if mutation.startswith("satisfied"):
        data = _model_payload(_satisfied("synthetic-requirement"))
    elif mutation.startswith("not_applicable"):
        data = _model_payload(_not_applicable("synthetic-requirement"))
    else:
        data = _model_payload(_omitted_result("synthetic-requirement"))

    if mutation == "satisfied_without_evidence":
        data["evidence_records"] = None
    elif mutation == "satisfied_with_omission":
        data["omission"] = _omission("synthetic-requirement")
    elif mutation == "omission_without_omission":
        data["omission"] = None
    elif mutation == "omission_with_evidence":
        data["evidence_records"] = (_synthetic_reference(),)
    elif mutation == "requirement_mismatch":
        data["omission"] = _omission("different-requirement")
    elif mutation == "outcome_mismatch":
        data["omission"] = _omission(
            "synthetic-requirement",
            outcome=EvidenceRequirementOutcome.UNKNOWN,
        )
    elif mutation == "not_applicable_with_evidence":
        data["evidence_records"] = (_synthetic_reference(),)
    elif mutation == "not_applicable_with_omission":
        data["omission"] = _omission("synthetic-requirement")
    with pytest.raises(ValidationError):
        EvidenceRequirementResult.model_validate(data)


def test_requirement_evidence_records_preserve_order_uniqueness_and_cap() -> None:
    records = tuple(_synthetic_reference(index) for index in range(1, 17))
    result = _satisfied("synthetic-requirement", records=records)
    assert result.evidence_records == records

    data = _model_payload(result)
    data["evidence_records"] = (records[0], records[0])
    with pytest.raises(ValidationError):
        EvidenceRequirementResult.model_validate(data)

    data["evidence_records"] = tuple(
        _synthetic_reference(index) for index in range(1, 18)
    )
    with pytest.raises(ValidationError, match="at most 16"):
        EvidenceRequirementResult.model_validate(data)

    data["evidence_records"] = [object() for _ in range(17)]
    with pytest.raises(ValidationError, match="at most 16"):
        EvidenceRequirementResult.model_validate(data)

    data["evidence_records"] = [records[0]]
    with pytest.raises(ValidationError, match="tuple"):
        EvidenceRequirementResult.model_validate(data)


def test_canonical_completeness_assessment_is_exact_and_bounded() -> None:
    assessment = _canonical_assessment()
    assert assessment.assessment_id.root == CANONICAL_ASSESSMENT_ID
    assert assessment.subject_record == _acquisition_reference()
    assert assessment.scope_id.root == CANONICAL_SCOPE_ID
    assert assessment.assessed_at == CANONICAL_ASSESSED_AT
    assert assessment.status is (
        EvidenceCompletenessStatus.SCOPE_SATISFIED_WITH_DECLARED_OMISSIONS
    )
    assert tuple(item.outcome for item in assessment.requirements[:2]) == 2 * (
        EvidenceRequirementOutcome.SATISFIED,
    )
    assert all(
        item.evidence_records == (_acquisition_reference(),)
        for item in assessment.requirements[:2]
    )
    assert all(item.omission is None for item in assessment.requirements[:2])
    assert "AcquisitionRunStatus" not in EvidenceCompletenessAssessment.model_fields


@pytest.mark.parametrize(
    "requirements,status",
    (
        (
            (_satisfied("satisfied"), _not_applicable("not-applicable")),
            EvidenceCompletenessStatus.SCOPE_SATISFIED,
        ),
        (
            (_omitted_result("omitted"),),
            EvidenceCompletenessStatus.SCOPE_SATISFIED_WITH_DECLARED_OMISSIONS,
        ),
        (
            (
                _omitted_result(
                    "unavailable", outcome=EvidenceRequirementOutcome.UNAVAILABLE
                ),
            ),
            EvidenceCompletenessStatus.SCOPE_PARTIAL,
        ),
        (
            (
                _omitted_result(
                    "inaccessible", outcome=EvidenceRequirementOutcome.INACCESSIBLE
                ),
            ),
            EvidenceCompletenessStatus.SCOPE_PARTIAL,
        ),
        (
            (
                _omitted_result(
                    "unsupported", outcome=EvidenceRequirementOutcome.UNSUPPORTED
                ),
            ),
            EvidenceCompletenessStatus.SCOPE_PARTIAL,
        ),
        (
            (_omitted_result("unknown", outcome=EvidenceRequirementOutcome.UNKNOWN),),
            EvidenceCompletenessStatus.SCOPE_UNKNOWN,
        ),
    ),
)
def test_synthetic_completeness_status_vectors(
    requirements: tuple[EvidenceRequirementResult, ...],
    status: EvidenceCompletenessStatus,
) -> None:
    assessment = _assessment(requirements, status=status)
    assert assessment.status is status


def test_unknown_outcome_has_priority_over_partial_and_declared_omission() -> None:
    assessment = _assessment(
        (
            _omitted_result("declared-omission"),
            _omitted_result(
                "inaccessible", outcome=EvidenceRequirementOutcome.INACCESSIBLE
            ),
            _omitted_result("unknown", outcome=EvidenceRequirementOutcome.UNKNOWN),
        ),
        status=EvidenceCompletenessStatus.SCOPE_UNKNOWN,
    )
    assert assessment.status is EvidenceCompletenessStatus.SCOPE_UNKNOWN


@pytest.mark.parametrize(
    "requirements,wrong_status",
    (
        (
            (_satisfied("satisfied"),),
            EvidenceCompletenessStatus.SCOPE_PARTIAL,
        ),
        (
            (_omitted_result("omitted"),),
            EvidenceCompletenessStatus.SCOPE_SATISFIED,
        ),
        (
            (
                _omitted_result(
                    "unavailable", outcome=EvidenceRequirementOutcome.UNAVAILABLE
                ),
            ),
            EvidenceCompletenessStatus.SCOPE_UNKNOWN,
        ),
        (
            (_omitted_result("unknown", outcome=EvidenceRequirementOutcome.UNKNOWN),),
            EvidenceCompletenessStatus.SCOPE_PARTIAL,
        ),
    ),
)
def test_inconsistent_explicit_completeness_status_rejects(
    requirements: tuple[EvidenceRequirementResult, ...],
    wrong_status: EvidenceCompletenessStatus,
) -> None:
    with pytest.raises(ValidationError, match="inconsistent"):
        _assessment(requirements, status=wrong_status)


def test_assessment_preserves_declared_order_and_rejects_duplicates() -> None:
    requirements = (_satisfied("z-last"), _satisfied("a-first"))
    assessment = _assessment(
        requirements,
        status=EvidenceCompletenessStatus.SCOPE_SATISFIED,
    )
    assert assessment.requirements == requirements

    duplicate = (_satisfied("duplicate"), _satisfied("duplicate"))
    with pytest.raises(ValidationError, match="unique"):
        _assessment(
            duplicate,
            status=EvidenceCompletenessStatus.SCOPE_SATISFIED,
        )


def test_assessment_requirement_cap_and_prevalidation_are_exact() -> None:
    requirements = tuple(
        _satisfied(
            f"synthetic-requirement-{index:03d}",
            records=(_synthetic_reference(index + 1),),
        )
        for index in range(512)
    )
    assessment = _assessment(
        requirements,
        status=EvidenceCompletenessStatus.SCOPE_SATISFIED,
    )
    assert len(assessment.requirements) == 512

    data = _model_payload(assessment)
    data["requirements"] = requirements + (
        _satisfied(
            "synthetic-requirement-512",
            records=(_synthetic_reference(513),),
        ),
    )
    with pytest.raises(ValidationError, match="at most 512"):
        EvidenceCompletenessAssessment.model_validate(data)

    data["requirements"] = [object() for _ in range(513)]
    with pytest.raises(ValidationError, match="at most 512"):
        EvidenceCompletenessAssessment.model_validate(data)

    data["requirements"] = ()
    with pytest.raises(ValidationError, match="at least one"):
        EvidenceCompletenessAssessment.model_validate(data)


def test_acquisition_run_status_cannot_substitute_for_completeness_status() -> None:
    data = _model_payload(_canonical_assessment())
    data["status"] = AcquisitionRunStatus.COMPLETE
    with pytest.raises(ValidationError, match="EvidenceCompletenessStatus"):
        EvidenceCompletenessAssessment.model_validate(data)


@pytest.mark.parametrize(
    "field",
    (
        "acquisition_run_status",
        "provider_history",
        "hidden_private_history",
        "transformation",
        "correction",
        "supersession",
        "publication",
        "confidence",
        "review_state",
        "migration",
        "storage",
        "adapter",
        "evidence_envelope",
    ),
)
def test_completeness_assessment_rejects_later_or_cross_layer_fields(
    field: str,
) -> None:
    data = _model_payload(_canonical_assessment())
    data[field] = "forbidden"
    with pytest.raises(ValidationError):
        EvidenceCompletenessAssessment.model_validate(data)


@pytest.mark.parametrize(
    "value",
    (
        "CI",
        "validate",
        "CI / validate",
        "check.name-with_underscores/path",
        "x" * 128,
    ),
)
def test_publication_check_name_preserves_bounded_printable_ascii(value: str) -> None:
    name = PublicationCheckName.model_validate(value)
    assert name.root == value
    assert PublicationCheckName.model_validate_json(name.model_dump_json()) == name


@pytest.mark.parametrize(
    "value",
    (
        "",
        " leading",
        "trailing ",
        "line\nbreak",
        "tab\tcontrol",
        "nonascii-é",
        "x" * 129,
        1,
        True,
    ),
)
def test_publication_check_name_rejects_invalid_or_coerced_values(
    value: object,
) -> None:
    with pytest.raises(ValidationError):
        PublicationCheckName.model_validate(value)


def test_all_four_canonical_publication_checks_are_exact() -> None:
    acquisition = _acquisition_publication()
    correction = _correction_publication()
    checks = (
        acquisition.pull_request_check,
        acquisition.main_check,
        correction.pull_request_check,
        correction.main_check,
    )
    assert tuple(check.run_id.root for check in checks) == (
        "30527236496",
        "30527462427",
        "30575877780",
        "30576009699",
    )
    assert tuple(check.job_id.root for check in checks) == (
        "90820902687",
        "90821631028",
        "90983907152",
        "90984355320",
    )
    assert tuple(check.event for check in checks) == (
        PublicationCheckEvent.PULL_REQUEST,
        PublicationCheckEvent.PUSH,
        PublicationCheckEvent.PULL_REQUEST,
        PublicationCheckEvent.PUSH,
    )
    assert all(check.attempt == 1 for check in checks)
    assert all(check.conclusion == "success" for check in checks)
    assert all(check.workflow_name.root == "CI" for check in checks)
    assert all(check.context.root == "validate" for check in checks)
    assert all(
        SuccessfulPublicationCheck.model_validate_json(check.model_dump_json()) == check
        for check in checks
    )


@pytest.mark.parametrize("attempt", (0, -1, 2_147_483_648, True, 1.0, "1"))
def test_successful_check_rejects_invalid_attempts(attempt: object) -> None:
    check = _acquisition_publication().pull_request_check
    data = _model_payload(check)
    data["attempt"] = attempt
    with pytest.raises(ValidationError):
        SuccessfulPublicationCheck.model_validate(data)


def test_successful_check_rejects_navigation_failed_and_untyped_inputs() -> None:
    check = _acquisition_publication().pull_request_check
    data = _model_payload(check)
    data["authority"] = _authority(role=AuthorityRole.NAVIGATION)
    with pytest.raises(ValidationError):
        SuccessfulPublicationCheck.model_validate(data)

    data = _model_payload(check)
    data["conclusion"] = "failure"
    with pytest.raises(ValidationError):
        SuccessfulPublicationCheck.model_validate(data)

    for field in (
        "authority",
        "workflow_name",
        "context",
        "event",
        "run_id",
        "job_id",
        "head_revision",
    ):
        data = _model_payload(check)
        value = cast(Any, data[field])
        data[field] = (
            value.model_dump(mode="python")
            if isinstance(value, BaseModel)
            else cast(object, value.value)
        )
        with pytest.raises(ValidationError):
            SuccessfulPublicationCheck.model_validate(data)

    data = _model_payload(check)
    data["branch"] = "forbidden"
    with pytest.raises(ValidationError):
        SuccessfulPublicationCheck.model_validate(data)


def test_canonical_acquisition_and_correction_publications_are_exact() -> None:
    acquisition = _acquisition_publication()
    correction = _correction_publication()
    assert acquisition.publication_id.root == "s1-p00-s04-acquisition-publication"
    assert correction.publication_id.root == ("s1-p00-s04-c01-correction-publication")
    assert acquisition.subject_record == _acquisition_reference()
    assert correction.subject_record == _correction_reference()
    assert acquisition.subject_record != correction.subject_record
    assert (
        acquisition.repository_identity
        == correction.repository_identity
        == (_repository())
    )
    assert acquisition.repository_identity.provider_repository_id.root == ("1303365003")
    assert acquisition.pull_request_identity.repository_scoped_number.root == "9"
    assert correction.pull_request_identity.repository_scoped_number.root == "10"
    assert acquisition.reviewed_revision.full_digest == PR9_REVIEWED
    assert acquisition.published_revision.full_digest == PR9_PUBLISHED
    assert acquisition.reviewed_tree.full_digest == PR9_TREE
    assert acquisition.reviewed_tree == acquisition.published_tree
    assert correction.reviewed_revision.full_digest == PR10_REVIEWED
    assert correction.published_revision.full_digest == PR10_PUBLISHED
    assert correction.reviewed_tree.full_digest == PR10_TREE
    assert correction.reviewed_tree == correction.published_tree
    assert acquisition.reviewed_revision != acquisition.published_revision
    assert correction.reviewed_revision != correction.published_revision
    assert acquisition.published_at == datetime(2026, 7, 30, 8, 38, 4, tzinfo=UTC)
    assert correction.published_at == datetime(2026, 7, 30, 19, 42, 46, tzinfo=UTC)
    assert acquisition.method is (
        EvidencePublicationMethod.PROTECTED_PULL_REQUEST_SQUASH_MERGE
    )
    assert EvidencePublication.model_validate_json(acquisition.model_dump_json()) == (
        acquisition
    )
    assert EvidencePublication.model_validate_json(correction.model_dump_json()) == (
        correction
    )


def test_publication_identity_and_subject_boundaries_are_explicit() -> None:
    original_subject = _acquisition_reference()
    original_dump = original_subject.model_dump(mode="json")
    data = _publication_data(
        publication_id="synthetic-publication-two",
        subject=original_subject,
        pull_request_number="99",
        reviewed_digest="1" * 40,
        tree_digest="2" * 40,
        published_digest="3" * 40,
        published_at=SYNTHETIC_TIME,
        pull_request_run_id="1001",
        pull_request_job_id="1002",
        main_run_id="1003",
        main_job_id="1004",
    )
    publication = EvidencePublication.model_validate(data)
    assert original_subject.model_dump(mode="json") == original_dump
    assert publication.subject_record == original_subject
    assert publication.publication_id != publication.subject_record
    assert publication.pull_request_identity != publication.published_revision
    assert publication.pull_request_check != publication.main_check
    assert not (
        set(EvidencePublication.model_fields)
        & {
            "completeness",
            "correction",
            "supersession",
            "latest",
            "current",
        }
    )

    different_subject = dict(data)
    different_subject["publication_id"] = EvidenceRelationId.model_validate(
        "synthetic-publication-three"
    )
    different_subject["subject_record"] = _correction_reference()
    assert EvidencePublication.model_validate(different_subject).subject_record == (
        _correction_reference()
    )

    same_subject_new_id = dict(data)
    same_subject_new_id["publication_id"] = EvidenceRelationId.model_validate(
        "synthetic-publication-four"
    )
    assert EvidencePublication.model_validate(same_subject_new_id).subject_record == (
        original_subject
    )


@pytest.mark.parametrize(
    "mutation",
    (
        "wrong_pr_kind",
        "repository_mismatch",
        "provider_mismatch",
        "wrong_pr_event",
        "wrong_main_event",
        "wrong_pr_head",
        "wrong_main_head",
        "reused_run_id",
        "reused_job_id",
        "same_revision",
        "tree_mismatch",
        "algorithm_mismatch",
    ),
)
def test_publication_rejects_inconsistent_identity_tree_and_check_bindings(
    mutation: str,
) -> None:
    canonical = _acquisition_publication()
    data = _model_payload(canonical)
    if mutation == "wrong_pr_kind":
        data["pull_request_identity"] = _pull_request_identity(
            "9", kind=SourceObjectKind.ISSUE
        )
    elif mutation == "repository_mismatch":
        foreign = _repository(provider_repository_id="999")
        data["pull_request_identity"] = _pull_request_identity("9", repository=foreign)
    elif mutation == "provider_mismatch":
        foreign = _repository(provider="gitlab", provider_repository_id="1303365003")
        data["repository_identity"] = foreign
        data["pull_request_identity"] = _pull_request_identity("9", repository=foreign)
    elif mutation == "wrong_pr_event":
        data["pull_request_check"] = _check(
            event=PublicationCheckEvent.PUSH,
            head=canonical.reviewed_revision,
            run_id="30527236496",
            job_id="90820902687",
        )
    elif mutation == "wrong_main_event":
        data["main_check"] = _check(
            event=PublicationCheckEvent.PULL_REQUEST,
            head=canonical.published_revision,
            run_id="30527462427",
            job_id="90821631028",
        )
    elif mutation == "wrong_pr_head":
        data["pull_request_check"] = _check(
            event=PublicationCheckEvent.PULL_REQUEST,
            head=_commit("4" * 40),
            run_id="30527236496",
            job_id="90820902687",
        )
    elif mutation == "wrong_main_head":
        data["main_check"] = _check(
            event=PublicationCheckEvent.PUSH,
            head=_commit("5" * 40),
            run_id="30527462427",
            job_id="90821631028",
        )
    elif mutation == "reused_run_id":
        data["main_check"] = _check(
            event=PublicationCheckEvent.PUSH,
            head=canonical.published_revision,
            run_id=canonical.pull_request_check.run_id.root,
            job_id="90821631028",
        )
    elif mutation == "reused_job_id":
        data["main_check"] = _check(
            event=PublicationCheckEvent.PUSH,
            head=canonical.published_revision,
            run_id="30527462427",
            job_id=canonical.pull_request_check.job_id.root,
        )
    elif mutation == "same_revision":
        data["published_revision"] = canonical.reviewed_revision
        data["main_check"] = _check(
            event=PublicationCheckEvent.PUSH,
            head=canonical.reviewed_revision,
            run_id="30527462427",
            job_id="90821631028",
        )
    elif mutation == "tree_mismatch":
        data["published_tree"] = _tree("6" * 40)
    elif mutation == "algorithm_mismatch":
        published = _commit("7" * 64, algorithm=GitHashAlgorithm.SHA256)
        data["published_revision"] = published
        data["main_check"] = _check(
            event=PublicationCheckEvent.PUSH,
            head=published,
            run_id="30527462427",
            job_id="90821631028",
        )
    with pytest.raises(ValidationError):
        EvidencePublication.model_validate(data)


@pytest.mark.parametrize(
    "field",
    (
        "branch",
        "local_path",
        "raw_url",
        "actor_profile",
        "credential",
        "review_prose",
        "package_location",
        "source_payload",
        "storage_backend",
        "release",
        "migration",
        "latest",
        "current",
        "supersession",
        "evidence_envelope",
    ),
)
def test_publication_rejects_leakage_and_later_layer_fields(field: str) -> None:
    data = _model_payload(_acquisition_publication())
    data[field] = "forbidden"
    with pytest.raises(ValidationError):
        EvidencePublication.model_validate(data)


@pytest.mark.parametrize(
    "field",
    (
        "subject_record",
        "repository_identity",
        "pull_request_identity",
        "reviewed_revision",
        "reviewed_tree",
        "published_revision",
        "published_tree",
        "method",
        "pull_request_check",
        "main_check",
    ),
)
def test_publication_requires_typed_nested_python_inputs(field: str) -> None:
    data = _model_payload(_acquisition_publication())
    value = cast(Any, data[field])
    data[field] = (
        value.model_dump(mode="python")
        if isinstance(value, BaseModel)
        else cast(object, value.value)
    )
    with pytest.raises(ValidationError):
        EvidencePublication.model_validate(data)


@pytest.mark.parametrize(
    "model_factory,time_field",
    (
        (_canonical_assessment, "assessed_at"),
        (_acquisition_publication, "published_at"),
    ),
)
@pytest.mark.parametrize(
    "value",
    (
        "2026-07-30T19:17:09",
        "2026-07-30T19:17:09-00:00",
        "2026-07-30T15:17:09-04:00",
        "2026-07-30 19:17:09Z",
        "2026-07-30T19:17:09.1234567Z",
    ),
)
def test_asserted_utc_json_rejects_nonasserted_or_malformed_times(
    model_factory: Any,
    time_field: str,
    value: str,
) -> None:
    model = cast(BaseModel, model_factory())
    payload = model.model_dump(mode="json")
    payload[time_field] = value
    with pytest.raises(ValidationError):
        model.__class__.model_validate_json(json.dumps(payload))


def test_python_times_require_aware_zero_utc_offset() -> None:
    assessment_data = _model_payload(_canonical_assessment())
    publication_data = _model_payload(_acquisition_publication())
    for data, model, field in (
        (assessment_data, EvidenceCompletenessAssessment, "assessed_at"),
        (publication_data, EvidencePublication, "published_at"),
    ):
        for invalid in (
            datetime(2026, 7, 30, 19, 17, 9),
            datetime(
                2026,
                7,
                30,
                15,
                17,
                9,
                tzinfo=timezone(-timedelta(hours=4)),
            ),
        ):
            mutated = dict(data)
            mutated[field] = invalid
            with pytest.raises(ValidationError):
                model.model_validate(mutated)


def test_acquisition_correction_and_omission_source_assurance_is_exact() -> None:
    acquisition_raw = ACQUISITION_PATH.read_bytes()
    correction_raw = CORRECTION_PATH.read_bytes()
    assert len(acquisition_raw) == ACQUISITION_LENGTH
    assert sha256(acquisition_raw).hexdigest() == ACQUISITION_SHA256
    assert len(correction_raw) == CORRECTION_LENGTH
    assert sha256(correction_raw).hexdigest() == CORRECTION_SHA256
    for path in (ACQUISITION_PATH, CORRECTION_PATH):
        path_stat = path.stat()
        assert stat.S_ISREG(path_stat.st_mode)
        assert stat.S_IMODE(path_stat.st_mode) == 0o644
        assert not path.is_symlink()

    acquisition = _load_json(ACQUISITION_PATH)
    correction = _load_json(CORRECTION_PATH)
    acquisition_format = cast(dict[str, Any], acquisition["format"])
    correction_format = cast(dict[str, Any], correction["format"])
    correction_canonicalization = cast(
        dict[str, Any], correction_format["canonicalization"]
    )
    correction_record = cast(dict[str, Any], correction["correction"])
    structured = cast(list[dict[str, Any]], correction["structured_omissions"])
    dispositions = cast(dict[str, Any], acquisition["dispositions"])
    assert acquisition_format == {
        "canonicalization": CANONICAL_CANONICALIZATION,
        "name": ACQUISITION_FORMAT,
        "version": CANONICAL_VERSION,
    }
    assert correction_format["name"] == CORRECTION_FORMAT
    assert correction_format["version"] == CANONICAL_VERSION
    assert correction_canonicalization["name"] == CANONICAL_CANONICALIZATION
    assert correction_record["created_at"] == "2026-07-30T19:17:09.655780Z"
    categories = tuple(item["legacy_category"] for item in structured)
    assert categories == OMISSION_REQUIREMENTS
    assert tuple(cast(list[str], dispositions["omissions"])) == (OMISSION_REQUIREMENTS)
    assert len(categories) == len(set(categories)) == 15
    assert {item["disposition"] for item in structured} == {"intentional_omission"}
    assert all(
        cast(dict[str, Any], item["state_distinctions"])[
            "complete_historical_state_claimed"
        ]
        is False
        for item in structured
    )


def test_artifact_snapshot_and_cross_layer_boundaries_remain_unchanged() -> None:
    source_raw = SOURCE_SOURCE.read_bytes()
    assert len(source_raw) == ARTIFACT_SNAPSHOT_SOURCE_LENGTH
    assert sha256(source_raw).hexdigest() == ARTIFACT_SNAPSHOT_SOURCE_SHA256
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
    assert not (
        set(EvidenceOmission.model_fields)
        & {"publication", "transformation", "correction", "payload", "prose"}
    )
    assert not (
        set(EvidenceRequirementResult.model_fields)
        & {"acquisition_run_status", "publication", "transformation", "correction"}
    )
    assert not (
        set(EvidencePublication.model_fields)
        & {"completeness", "omission", "correction", "supersession"}
    )


@pytest.mark.parametrize(
    "model_factory,missing_field",
    (
        (_omission, "requirement_id"),
        (_omission, "outcome"),
        (_canonical_assessment, "scope_id"),
        (_acquisition_publication, "publication_id"),
        (_acquisition_publication, "subject_record"),
    ),
)
def test_material_required_fields_cannot_be_omitted(
    model_factory: Any,
    missing_field: str,
) -> None:
    model = cast(
        BaseModel,
        model_factory("synthetic-omission")
        if model_factory is _omission
        else model_factory(),
    )
    data = _model_payload(model)
    del data[missing_field]
    with pytest.raises(ValidationError):
        model.__class__.model_validate(data)


def test_models_are_frozen_and_extra_forbidden() -> None:
    models = (
        EvidenceScopeId.model_validate("synthetic-scope"),
        EvidenceRequirementId.model_validate("synthetic-requirement"),
        EvidenceDispositionReason.model_validate("synthetic-reason"),
        PublicationCheckName.model_validate("validate"),
        _omission("synthetic-omission"),
        _satisfied("synthetic-requirement"),
        _canonical_assessment(),
        _acquisition_publication().pull_request_check,
        _acquisition_publication(),
    )
    for model in models:
        field = (
            "root"
            if isinstance(model, RootModel)
            else next(iter(model.__class__.model_fields))
        )
        with pytest.raises(ValidationError):
            setattr(cast(Any, model), field, "changed")


def test_inventory_failure_sensitivity_detects_missing_and_unexpected_exports() -> None:
    exports = list(EXPECTED_EVIDENCE_EXPORTS)
    missing = tuple(exports[:-1])
    unexpected = tuple((*exports, "EvidenceContractCorpus"))
    with pytest.raises(AssertionError):
        assert missing == EXPECTED_EVIDENCE_EXPORTS
    with pytest.raises(AssertionError):
        assert unexpected == EXPECTED_EVIDENCE_EXPORTS
    with pytest.raises(AssertionError):
        assert (
            EXPECTED_PRODUCTION_FILES | {"src/faultatlas/domain/envelope.py"}
            == EXPECTED_PRODUCTION_FILES
        )
