from __future__ import annotations

import ast
import json
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
    AcquisitionRunId,
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
CANONICAL_RUN_ID = "run-0001-s04-v1-base-4c9cde74-head-690a63b9"
CANONICAL_ACQUISITION_SHA256 = (
    "1c29093bf1537e9b824a18df1848b71a8da014f544bc9f385707eb0e000a1318"
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
EXPECTED_EVIDENCE_CLASSES = set(EXPECTED_EVIDENCE_EXPORTS) - {
    "EvidenceRecordRelationship",
    "project_evidence_envelope_to_legacy_artifact_snapshot",
    "wrap_legacy_artifact_snapshot",
} | {"_ArtifactRecordBase", "_EvidenceRecordBase", "_RetrievalRecordBase"}
EXPECTED_EVIDENCE_TYPE_ALIASES = {"EvidenceRecordRelationship"}
EXPECTED_EVIDENCE_ASSIGNMENTS = {
    "__all__",
    "_AcquisitionRunIdValue",
    "_ASSERTED_UTC_STARTED_AT_PATTERN",
    "_INVALID_PERCENT_ENCODING",
    "_MAX_REQUEST_ORDINAL",
    "_MAX_ROUTE_PATH_LENGTH",
    "_MAX_RUN_ID_LENGTH",
    "_MAX_MEDIA_TYPE_LENGTH",
    "_MAX_API_VERSION_LENGTH",
    "_MAX_QUERY_NAME_LENGTH",
    "_MAX_QUERY_VALUE_LENGTH",
    "_MAX_QUERY_PARAMETERS",
    "_MAX_MEDIA_TYPE_PARAMETERS",
    "_MAX_CONTENT_ENCODINGS",
    "_MAX_CONTENT_ENCODING_LENGTH",
    "_MAX_MEDIA_PARAMETER_VALUE_LENGTH",
    "_MAX_ARTIFACT_DIGEST_SCOPE_LENGTH",
    "_MAX_ARTIFACT_BYTE_LENGTH",
    "_MAX_RETAINED_ARTIFACTS_PER_REQUEST",
    "_MAX_REQUESTS_PER_ACQUISITION_RUN",
    "_MAX_TRANSFORMATION_INPUTS",
    "_MAX_TRANSFORMATION_OUTPUTS",
    "_MAX_EVIDENCE_SCOPE_ID_LENGTH",
    "_MAX_EVIDENCE_REQUIREMENT_ID_LENGTH",
    "_MAX_EVIDENCE_DISPOSITION_REASON_LENGTH",
    "_MAX_OMISSION_SOURCE_RECORDS",
    "_MAX_EVIDENCE_RECORDS_PER_REQUIREMENT",
    "_MAX_REQUIREMENTS_PER_ASSESSMENT",
    "_MAX_PUBLICATION_CHECK_NAME_LENGTH",
    "_MAX_PUBLICATION_CHECK_ATTEMPT",
    "_MAX_ENVELOPE_LEGACY_SNAPSHOTS",
    "_MAX_ENVELOPE_REQUEST_MEMBERSHIPS",
    "_MAX_ENVELOPE_ACQUISITION_RUNS",
    "_MAX_ENVELOPE_TRANSFORMATIONS",
    "_MAX_ENVELOPE_RECORD_RELATIONSHIPS",
    "_MAX_ENVELOPE_COMPLETENESS_ASSESSMENTS",
    "_MAX_ENVELOPE_PUBLICATIONS",
    "_LEGACY_ARTIFACT_SNAPSHOT_ADAPTER_ID",
    "_LEGACY_ARTIFACT_SNAPSHOT_ADAPTER_VERSION",
    "_RUN_ID_PATTERN",
    "_HTTP_TOKEN_PATTERN",
    "_MEDIA_TYPE_PATTERN",
    "_ARTIFACT_DIGEST_SCOPE_PATTERN",
    "_ARTIFACT_SHA256_PATTERN",
    "_EVIDENCE_RECORD_FORMAT_PATTERN",
    "_EVIDENCE_VERSION_PATTERN",
    "_EVIDENCE_RELATION_ID_PATTERN",
    "_TRANSFORMATION_OPERATION_PATTERN",
    "_EVIDENCE_SCOPE_ID_PATTERN",
    "_EVIDENCE_REQUIREMENT_ID_PATTERN",
    "_EVIDENCE_DISPOSITION_REASON_PATTERN",
    "_RetrievalRoutePathValue",
    "_MediaTypeValue",
    "_ApiVersionValue",
    "_RequestQueryNameValue",
    "_RequestQueryValue",
    "_ContentEncodingValue",
    "_MediaTypeParameterValue",
    "_ArtifactDigestScopeValue",
    "_ArtifactSha256DigestValue",
    "_EvidenceRecordFormatValue",
    "_EvidenceVersionValue",
    "_EvidenceCanonicalizationValue",
    "_EvidenceRelationIdValue",
    "_TransformationOperationValue",
    "_EvidenceScopeIdValue",
    "_EvidenceRequirementIdValue",
    "_EvidenceDispositionReasonValue",
    "_PublicationCheckNameValue",
}
EXPECTED_EVIDENCE_IMPORTS = {
    "json": {None},
    "re": {None},
    "datetime": {"UTC", "datetime", "timedelta"},
    "enum": {"StrEnum"},
    "typing": {"Annotated", "Literal", "Self", "cast"},
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
SYNTHETIC_STARTED_AT = datetime(2026, 8, 1, 12, 0, 0, tzinfo=UTC)


def _provider(value: str = "github") -> ProviderKey:
    return ProviderKey.model_validate(value)


def _authority(
    *,
    role: AuthorityRole = AuthorityRole.RETRIEVAL,
    host: str = "api.github.com",
) -> ProviderAuthority:
    return ProviderAuthority(provider=_provider(), role=role, host=host)


def _request_id(
    *,
    run_id: str = "run-synthetic-get-001",
    ordinal: int = 1,
) -> RetrievalRequestId:
    return RetrievalRequestId(
        acquisition_run_id=AcquisitionRunId.model_validate(run_id),
        request_ordinal=RetrievalRequestOrdinal.model_validate(ordinal),
    )


def _reference_data(**overrides: object) -> dict[str, object]:
    data: dict[str, object] = {
        "request_id": _request_id(),
        "authority": _authority(),
        "method": RetrievalMethod.GET,
        "route_path": RetrievalRoutePath.model_validate(
            "/repos/example/project/issues/1"
        ),
        "started_at": SYNTHETIC_STARTED_AT,
    }
    data.update(overrides)
    return data


def _reference(**overrides: object) -> RetrievalRequestReference:
    return RetrievalRequestReference.model_validate(_reference_data(**overrides))


def _load_object(path: Path) -> dict[str, Any]:
    value = cast(object, json.loads(path.read_text(encoding="utf-8")))
    assert isinstance(value, dict)
    return cast(dict[str, Any], value)


def _acquisition_records() -> tuple[dict[str, Any], ...]:
    acquisition = _load_object(ACQUISITION_PATH)
    requests = cast(dict[str, Any], acquisition["requests"])
    records = cast(list[dict[str, Any]], requests["records"])
    return tuple(records)


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
    raw = cast(object, ast.literal_eval(assignments[0].value))
    assert isinstance(raw, list)
    values = cast(list[object], raw)
    assert all(isinstance(value, str) for value in values)
    return tuple(cast(str, value) for value in values)


def _validate_evidence_surface(source: str) -> None:
    tree = ast.parse(source)
    exports = _parse_exports(source)
    assert exports == EXPECTED_EVIDENCE_EXPORTS
    assert len(exports) == len(set(exports)) == 58
    classes = {node.name for node in tree.body if isinstance(node, ast.ClassDef)}
    type_aliases = {
        node.name.id for node in tree.body if isinstance(node, ast.TypeAlias)
    }
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
    functions = {
        node.name
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    assignments = {
        target.id
        for node in tree.body
        if isinstance(node, ast.Assign)
        for target in node.targets
        if isinstance(target, ast.Name)
    }
    assert classes == EXPECTED_EVIDENCE_CLASSES
    assert len(classes) == 58
    assert type_aliases == EXPECTED_EVIDENCE_TYPE_ALIASES
    assert public_symbols == EXPECTED_EVIDENCE_EXPORTS
    assert functions == {
        "_has_ascii_control",
        "_normalize_asserted_utc",
        "_require_asserted_utc_json",
        "project_evidence_envelope_to_legacy_artifact_snapshot",
        "wrap_legacy_artifact_snapshot",
    }
    assert assignments == EXPECTED_EVIDENCE_ASSIGNMENTS


def _validate_evidence_imports_and_calls(source: str) -> None:
    tree = ast.parse(source)
    observed_imports: dict[str, set[str | None]] = {}
    for node in tree.body:
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.asname is None
                observed_imports.setdefault(alias.name, set()).add(None)
        elif isinstance(node, ast.ImportFrom):
            assert node.level == 0
            assert node.module is not None
            imported_names = observed_imports.setdefault(node.module, set())
            for alias in node.names:
                assert alias.asname is None
                imported_names.add(alias.name)
    assert observed_imports == EXPECTED_EVIDENCE_IMPORTS

    forbidden_dynamic_calls = {
        "__import__",
        "compile",
        "eval",
        "exec",
        "getattr",
        "globals",
        "locals",
        "open",
        "setattr",
        "vars",
    }
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            assert node.func.id not in forbidden_dynamic_calls


def _validate_production_inventory(paths: set[str]) -> None:
    assert paths == EXPECTED_PRODUCTION_FILES


def _validate_package_root_exports(source: str) -> None:
    assert _parse_exports(source) == ("__version__",)


def _assert_no_post_s07_surface(source: str) -> None:
    tree = ast.parse(source)
    definitions = {
        node.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
    }
    definitions.update(
        node.name.id for node in ast.walk(tree) if isinstance(node, ast.TypeAlias)
    )
    forbidden = {
        "AcquisitionRunRecord",
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
        "RepositorySnapshot",
        "RepresentationObservation",
        "ResponseIdentity",
        "ResponseObservation",
        "RetainedArtifact",
        "RetainedArtifactRecord",
        "TransformationRecord",
    }
    assert not definitions & forbidden


def test_canonical_acquisition_lock_and_request_inventory_are_exact() -> None:
    raw = ACQUISITION_PATH.read_bytes()
    assert len(raw) == 61_283
    assert sha256(raw).hexdigest() == CANONICAL_ACQUISITION_SHA256
    acquisition = _load_object(ACQUISITION_PATH)
    run = cast(dict[str, Any], acquisition["run"])
    records = _acquisition_records()

    assert run["run_id"] == CANONICAL_RUN_ID
    assert len(records) == 32
    assert [record["ordinal"] for record in records] == list(range(1, 33))
    assert len({cast(int, record["ordinal"]) for record in records}) == 32
    assert {record["method"] for record in records} == {"GET"}
    assert all(
        {"ordinal", "method", "safe_target", "started_at"} <= set(record)
        for record in records
    )
    assert all(not ({"authority", "host", "url"} & set(record)) for record in records)


def test_canonical_inventory_supports_exactly_32_request_id_vectors() -> None:
    run_id = AcquisitionRunId.model_validate(CANONICAL_RUN_ID)
    request_ids = tuple(
        RetrievalRequestId(
            acquisition_run_id=run_id,
            request_ordinal=RetrievalRequestOrdinal.model_validate(
                cast(int, record["ordinal"])
            ),
        )
        for record in _acquisition_records()
    )

    assert len(request_ids) == len(set(request_ids)) == 32
    assert request_ids[0].request_ordinal.root == 1
    assert request_ids[-1].request_ordinal.root == 32
    assert all(item.acquisition_run_id == run_id for item in request_ids)


def test_canonical_request_field_classification_is_loss_aware() -> None:
    records = _acquisition_records()
    query_bearing = tuple(
        record for record in records if "?" in cast(str, record["safe_target"])
    )
    query_free = tuple(
        record for record in records if "?" not in cast(str, record["safe_target"])
    )
    projected_methods = tuple(
        RetrievalMethod(cast(str, record["method"]).lower()) for record in records
    )
    projected_routes = tuple(
        RetrievalRoutePath.model_validate(
            cast(str, record["safe_target"]).partition("?")[0]
        )
        for record in records
    )
    direct_started_at = tuple(
        datetime.fromisoformat(cast(str, record["started_at"]).replace("Z", "+00:00"))
        for record in records
    )

    assert len(query_bearing) == 9
    assert len(query_free) == 23
    assert set(projected_methods) == {RetrievalMethod.GET}
    assert len(projected_routes) == 32
    assert all(value.utcoffset() == timedelta(0) for value in direct_started_at)


@pytest.mark.parametrize(
    ("ordinal", "route", "started_at"),
    (
        (
            29,
            "/repos/pytest-dev/pytest/compare/"
            "4c9cde74ab40027b5761ab9e002af116a4a20df3..."
            "690a63b9218f72662cd3a67c6c200b758c88ce12",
            "2026-07-24T11:03:29.870414Z",
        ),
        (
            30,
            "/repos/pytest-dev/pytest/compare/"
            "4c9cde74ab40027b5761ab9e002af116a4a20df3..."
            "690a63b9218f72662cd3a67c6c200b758c88ce12",
            "2026-07-24T11:03:30.539163Z",
        ),
        (
            32,
            "/repos/pytest-dev/pytest/git/blobs/"
            "629df45ac405532c107eb233217bc2ac1ad70c88",
            "2026-07-24T11:03:31.479205Z",
        ),
    ),
)
def test_focal_canonical_request_fields_are_direct_or_deterministic_projections(
    ordinal: int,
    route: str,
    started_at: str,
) -> None:
    record = _acquisition_records()[ordinal - 1]

    assert record["ordinal"] == ordinal
    assert record["method"] == "GET"
    assert record["safe_target"] == route
    assert record["started_at"] == started_at
    assert RetrievalMethod(cast(str, record["method"]).lower()) is RetrievalMethod.GET
    assert RetrievalRoutePath.model_validate(record["safe_target"]).root == route


def test_no_canonical_full_request_reference_can_be_created_without_fabrication() -> (
    None
):
    original_records = _acquisition_records()
    acquisition = _load_object(ACQUISITION_PATH)
    run = cast(dict[str, Any], acquisition["run"])
    correction = _load_object(CORRECTION_PATH)
    observations = cast(dict[str, Any], correction["supplemental_observations"])
    request_graph = cast(dict[str, Any], observations["request_graph"])
    supplemental = cast(list[dict[str, Any]], request_graph["records"])

    candidate_fields = tuple(
        {
            "acquisition_run_id": run.get("run_id"),
            "request_ordinal": record.get("ordinal"),
            "authority": record.get("authority") or record.get("host"),
            "method": record.get("method"),
            "route_path": record.get("safe_target"),
            "started_at": record.get("started_at"),
        }
        for record in original_records
    )
    missing_fields = tuple(
        tuple(name for name, value in candidate.items() if value is None)
        for candidate in candidate_fields
    )
    canonical_full_reference_count = sum(not missing for missing in missing_fields)

    assert len(candidate_fields) == 32
    assert set(missing_fields) == {("authority",)}
    assert canonical_full_reference_count == 0
    assert len(supplemental) == 2
    assert all("api_host" in record for record in supplemental)
    assert all("run_id" not in record for record in supplemental)
    assert all(record["method"] == "GET" for record in supplemental)
    assert not any(
        cast(str, record["safe_target"]).casefold() == "/graphql"
        for record in (*original_records, *supplemental)
    )


@pytest.mark.parametrize(
    "value",
    (
        "a",
        "1",
        "run-0001-s04-v1-base-4c9cde74-head-690a63b9",
        "a.b_c-d9",
        "a" + ("-" * 158) + "z",
    ),
)
def test_acquisition_run_id_accepts_and_preserves_valid_opaque_lexemes(
    value: str,
) -> None:
    run_id = AcquisitionRunId.model_validate(value)
    assert run_id.root == value


@pytest.mark.parametrize(
    "value",
    (
        "",
        "-run",
        "run-",
        ".run",
        "run.",
        "Run-1",
        "run/1",
        "run\\1",
        "run:1",
        "run 1",
        "run\n1",
        "rún-1",
        "a" + ("-" * 159) + "z",
        1,
        None,
    ),
)
def test_acquisition_run_id_rejects_invalid_or_coercive_values(value: object) -> None:
    with pytest.raises(ValidationError):
        AcquisitionRunId.model_validate(value)


def test_acquisition_run_id_is_not_parsed_or_normalized() -> None:
    dotted = AcquisitionRunId.model_validate("run.a-1")
    underscored = AcquisitionRunId.model_validate("run_a-1")
    assert dotted.root == "run.a-1"
    assert underscored.root == "run_a-1"
    assert dotted != underscored


@pytest.mark.parametrize("value", (1, 2_147_483_647))
def test_request_ordinal_accepts_exact_bounds(value: int) -> None:
    assert RetrievalRequestOrdinal.model_validate(value).root == value


@pytest.mark.parametrize(
    "value",
    (0, -1, 2_147_483_648, True, False, 1.0, "1", None),
)
def test_request_ordinal_rejects_out_of_range_or_coercive_values(
    value: object,
) -> None:
    with pytest.raises(ValidationError):
        RetrievalRequestOrdinal.model_validate(value)


def test_request_id_has_exact_identity_fields_and_no_transport_metadata() -> None:
    assert set(RetrievalRequestId.model_fields) == {
        "schema_version",
        "acquisition_run_id",
        "request_ordinal",
    }
    assert len(RetrievalRequestId.model_fields) == 3
    request_id = _request_id()
    assert request_id.schema_version == 1
    assert request_id.acquisition_run_id.root == "run-synthetic-get-001"
    assert request_id.request_ordinal.root == 1


@pytest.mark.parametrize("missing", ("acquisition_run_id", "request_ordinal"))
def test_request_id_requires_run_and_ordinal(missing: str) -> None:
    data: dict[str, object] = {
        "acquisition_run_id": AcquisitionRunId.model_validate("run-a"),
        "request_ordinal": RetrievalRequestOrdinal.model_validate(1),
    }
    del data[missing]
    with pytest.raises(ValidationError) as error:
        RetrievalRequestId.model_validate(data)
    assert error.value.errors()[0]["type"] == "missing"


def test_request_id_rejects_ordinal_without_run() -> None:
    with pytest.raises(ValidationError):
        RetrievalRequestId.model_validate(
            {"request_ordinal": RetrievalRequestOrdinal.model_validate(1)}
        )


def test_same_ordinal_in_different_runs_is_not_equal() -> None:
    first = _request_id(run_id="run-a")
    second = _request_id(run_id="run-b")
    assert first.request_ordinal == second.request_ordinal
    assert first != second


def test_same_run_with_different_ordinals_is_not_equal() -> None:
    first = _request_id(ordinal=1)
    second = _request_id(ordinal=2)
    assert first.acquisition_run_id == second.acquisition_run_id
    assert first != second


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("acquisition_run_id", "run-a"),
        ("request_ordinal", 1),
    ),
)
def test_request_id_requires_typed_nested_python_values(
    field: str,
    value: object,
) -> None:
    data: dict[str, object] = {
        "acquisition_run_id": AcquisitionRunId.model_validate("run-a"),
        "request_ordinal": RetrievalRequestOrdinal.model_validate(1),
    }
    data[field] = value
    with pytest.raises(ValidationError):
        RetrievalRequestId.model_validate(data)


def test_request_id_rejects_extra_fields() -> None:
    with pytest.raises(ValidationError) as error:
        RetrievalRequestId.model_validate(
            {
                "acquisition_run_id": AcquisitionRunId.model_validate("run-a"),
                "request_ordinal": RetrievalRequestOrdinal.model_validate(1),
                "method": RetrievalMethod.GET,
            }
        )
    assert error.value.errors()[0]["type"] == "extra_forbidden"


@pytest.mark.parametrize("value", (2, 0, True, 1.0, "1"))
def test_request_records_require_exact_schema_version(value: object) -> None:
    with pytest.raises(ValidationError):
        RetrievalRequestId.model_validate(
            {
                "schema_version": value,
                "acquisition_run_id": AcquisitionRunId.model_validate("run-a"),
                "request_ordinal": RetrievalRequestOrdinal.model_validate(1),
            }
        )


def test_method_vocabulary_is_exact_and_has_no_implicit_methods() -> None:
    assert tuple(RetrievalMethod) == (RetrievalMethod.GET, RetrievalMethod.POST)
    assert [method.value for method in RetrievalMethod] == ["get", "post"]
    for forbidden in ("put", "patch", "delete", "connect", "trace", "GET"):
        with pytest.raises(ValueError):
            RetrievalMethod(forbidden)


def test_method_json_values_are_stable_and_reconstruct_the_enum() -> None:
    adapter = TypeAdapter(RetrievalMethod)
    assert adapter.dump_json(RetrievalMethod.GET) == b'"get"'
    assert adapter.dump_json(RetrievalMethod.POST) == b'"post"'
    assert adapter.validate_json(b'"get"') is RetrievalMethod.GET
    assert adapter.validate_json(b'"post"') is RetrievalMethod.POST


@pytest.mark.parametrize(
    "value",
    (
        "/",
        "/graphql",
        "/repos/example/project/issues/1",
        "/Repos/Example//Exact-Case",
        "/repos/example/project/contents/a%20b",
        "/encoded/%2F/%2f",
        "/a/./b/../c",
        "/" + ("a" * 4095),
    ),
)
def test_route_path_accepts_and_preserves_valid_exact_lexemes(value: str) -> None:
    route = RetrievalRoutePath.model_validate(value)
    assert route.root == value


@pytest.mark.parametrize(
    "value",
    (
        "",
        "repos/example",
        "//api.example.test/path",
        "https://api.example.test/repos/example",
        "http://api.example.test/repos/example",
        "/repos/example?per_page=100",
        "/repos/example#section",
        "/repos/example path",
        "/repos/example\npath",
        "/repos\\example",
        "/repos/éxample",
        "/repos/%",
        "/repos/%2",
        "/repos/%GG",
        "/repos/%0G",
        "/repos/example\x7f",
        "/" + ("a" * 4096),
        1,
        b"/repos/example",
        Path("/repos/example"),
    ),
)
def test_route_path_rejects_non_origin_relative_or_coercive_values(
    value: object,
) -> None:
    with pytest.raises(ValidationError):
        RetrievalRoutePath.model_validate(value)


def test_route_path_does_not_decode_normalize_or_dot_resolve() -> None:
    value = "/A//%2e%2e/b/./c"
    route = RetrievalRoutePath.model_validate(value)
    assert route.root == value
    assert route.root != "/a/../b/c"


def test_route_path_semantic_json_round_trip_preserves_the_exact_lexeme() -> None:
    route = RetrievalRoutePath.model_validate("/Repos/A%2fb//C")
    assert RetrievalRoutePath.model_validate_json(route.model_dump_json()) == route


def test_synthetic_get_and_post_request_references_are_explicit() -> None:
    get_reference = _reference()
    post_reference = _reference(
        request_id=_request_id(run_id="run-synthetic-post-001"),
        method=RetrievalMethod.POST,
        route_path=RetrievalRoutePath.model_validate("/graphql"),
    )

    assert get_reference.method is RetrievalMethod.GET
    assert get_reference.route_path.root == "/repos/example/project/issues/1"
    assert post_reference.method is RetrievalMethod.POST
    assert post_reference.route_path.root == "/graphql"
    assert get_reference.request_id != post_reference.request_id


def test_request_reference_has_exact_core_provenance_fields() -> None:
    assert set(RetrievalRequestReference.model_fields) == {
        "schema_version",
        "request_id",
        "authority",
        "method",
        "route_path",
        "started_at",
    }
    assert len(RetrievalRequestReference.model_fields) == 6


def test_request_reference_rejects_navigation_authority() -> None:
    with pytest.raises(ValidationError) as error:
        _reference(
            authority=_authority(role=AuthorityRole.NAVIGATION, host="github.com")
        )
    assert error.value.errors()[0]["loc"] == ("authority",)


def test_request_reference_rejects_plain_host_as_authority() -> None:
    with pytest.raises(ValidationError):
        _reference(authority="api.github.com")


def test_request_reference_requires_method() -> None:
    data = _reference_data()
    del data["method"]
    with pytest.raises(ValidationError) as error:
        RetrievalRequestReference.model_validate(data)
    assert error.value.errors()[0]["type"] == "missing"


def test_request_reference_rejects_invalid_schema_version() -> None:
    with pytest.raises(ValidationError):
        _reference(schema_version=2)


def test_request_reference_rejects_unknown_or_untyped_python_method() -> None:
    for method in ("get", "put"):
        with pytest.raises(ValidationError):
            _reference(method=method)


def test_request_reference_rejects_naive_started_at() -> None:
    with pytest.raises(ValidationError) as error:
        _reference(started_at=SYNTHETIC_STARTED_AT.replace(tzinfo=None))
    assert error.value.errors()[0]["type"] == "timezone_aware"
    assert error.value.errors()[0]["loc"] == ("started_at",)


def test_request_reference_rejects_nonzero_started_at_offset() -> None:
    nonzero = SYNTHETIC_STARTED_AT.astimezone(timezone(timedelta(hours=1)))
    with pytest.raises(ValidationError) as error:
        _reference(started_at=nonzero)
    assert error.value.errors()[0]["type"] == "value_error"
    assert error.value.errors()[0]["loc"] == ("started_at",)


@pytest.mark.parametrize(
    "started_at",
    (
        "2026-08-02T12:34:56-0000",
        "2026-08-02T12:34:56-00",
        "2026-08-02T12:34:56-00:00",
        "2026-08-02T12:34:56-00:00:00",
    ),
)
def test_request_reference_json_rejects_negative_zero_offsets(
    started_at: str,
) -> None:
    data = _reference().model_dump(mode="json")
    data["started_at"] = started_at
    with pytest.raises(ValidationError) as error:
        RetrievalRequestReference.model_validate_json(json.dumps(data))
    assert error.value.errors()[0]["type"] == "value_error"
    assert error.value.errors()[0]["loc"] == ("started_at",)
    assert error.value.errors()[0]["msg"] == (
        "Value error, started_at JSON value must use asserted-UTC RFC 3339 "
        "form ending in Z or +00:00"
    )


@pytest.mark.parametrize(
    "started_at",
    (
        "2026-08-02T12:34:56+0000",
        "2026-08-02T12:34:56+00",
        "2026-08-02T12:34:56+00:00:00",
        "2026-08-02T12:34:56+00:00:01",
        "2026-08-02T12:34:56+01:00",
        "2026-08-02T12:34:56-01:00",
    ),
)
def test_request_reference_json_rejects_unsupported_offset_forms(
    started_at: str,
) -> None:
    data = _reference().model_dump(mode="json")
    data["started_at"] = started_at
    with pytest.raises(ValidationError) as error:
        RetrievalRequestReference.model_validate_json(json.dumps(data))
    assert error.value.errors()[0]["loc"] == ("started_at",)


@pytest.mark.parametrize(
    "started_at",
    (
        "2026-08-02t12:34:56Z",
        "2026-08-02T12:34:56z",
        "2026-08-02 12:34:56Z",
        "2026-08-02T12:34Z",
        "2026-08-02",
        "2026-08-02T12:34:56",
        "2026-08-02T12:34:56.1234567Z",
        "2026-08-02T12:34:56.Z",
        " 2026-08-02T12:34:56Z",
        "2026-08-02T12:34:56Z ",
        "2026-8-02T12:34:56Z",
        "2026-08-2T12:34:56Z",
        "2026-08-02T2:34:56Z",
        "2026-08-02T12:3:56Z",
        "2026-08-02T12:34:5Z",
    ),
)
def test_request_reference_json_rejects_noncanonical_timestamp_grammar(
    started_at: str,
) -> None:
    data = _reference().model_dump(mode="json")
    data["started_at"] = started_at
    with pytest.raises(ValidationError) as error:
        RetrievalRequestReference.model_validate_json(json.dumps(data))
    assert error.value.errors()[0]["loc"] == ("started_at",)


@pytest.mark.parametrize(
    "started_at",
    (0, 1.25, True, None, {}, []),
)
def test_request_reference_json_rejects_non_string_timestamp_values(
    started_at: object,
) -> None:
    data = _reference().model_dump(mode="json")
    data["started_at"] = started_at
    with pytest.raises(ValidationError) as error:
        RetrievalRequestReference.model_validate_json(json.dumps(data))
    assert error.value.errors()[0]["loc"] == ("started_at",)


@pytest.mark.parametrize(
    "started_at",
    (
        "2025-02-29T12:34:56Z",
        "2026-13-02T12:34:56Z",
        "2026-08-02T24:00:00Z",
        "2026-08-02T12:34:60Z",
    ),
)
def test_request_reference_json_defers_calendar_and_clock_validity_to_parser(
    started_at: str,
) -> None:
    data = _reference().model_dump(mode="json")
    data["started_at"] = started_at
    with pytest.raises(ValidationError) as error:
        RetrievalRequestReference.model_validate_json(json.dumps(data))
    assert error.value.errors()[0]["loc"] == ("started_at",)


def test_request_reference_rejects_date_only_string() -> None:
    with pytest.raises(ValidationError):
        _reference(started_at="2026-08-01")


def test_request_reference_rejects_json_valid_timestamp_string_in_python_mode() -> None:
    with pytest.raises(ValidationError) as error:
        _reference(started_at="2026-08-02T12:34:56Z")
    assert error.value.errors()[0]["loc"] == ("started_at",)


def test_request_reference_normalizes_effective_zero_offset_to_utc() -> None:
    zero = timezone(timedelta(0), name="zero-offset")
    started_at = datetime(2026, 8, 1, 12, 0, 0, 123456, tzinfo=zero)
    reference = _reference(started_at=started_at)
    assert reference.started_at.tzinfo is UTC
    assert reference.model_dump(mode="json")["started_at"] == (
        "2026-08-01T12:00:00.123456Z"
    )


@pytest.mark.parametrize("suffix", ("Z", "+00:00"))
@pytest.mark.parametrize(
    ("fraction", "microsecond", "serialized_started_at"),
    (
        ("", 0, "2026-08-02T12:34:56Z"),
        (".1", 100_000, "2026-08-02T12:34:56.100000Z"),
        (".12", 120_000, "2026-08-02T12:34:56.120000Z"),
        (".123", 123_000, "2026-08-02T12:34:56.123000Z"),
        (".1234", 123_400, "2026-08-02T12:34:56.123400Z"),
        (".12345", 123_450, "2026-08-02T12:34:56.123450Z"),
        (".123456", 123_456, "2026-08-02T12:34:56.123456Z"),
    ),
)
def test_request_reference_json_accepts_asserted_utc_grammar(
    suffix: str,
    fraction: str,
    microsecond: int,
    serialized_started_at: str,
) -> None:
    data = _reference().model_dump(mode="json")
    data["started_at"] = f"2026-08-02T12:34:56{fraction}{suffix}"
    reference = RetrievalRequestReference.model_validate_json(json.dumps(data))
    expected_started_at = datetime(
        2026,
        8,
        2,
        12,
        34,
        56,
        microsecond,
        tzinfo=UTC,
    )

    assert reference.started_at == expected_started_at
    assert reference.started_at.tzinfo is UTC
    assert reference.model_dump(mode="json")["started_at"] == serialized_started_at
    assert (
        RetrievalRequestReference.model_validate_json(reference.model_dump_json())
        == reference
    )


@pytest.mark.parametrize(
    "extra_field",
    (
        "full_url",
        "query",
        "headers",
        "accept",
        "api_version",
        "cursor",
        "graphql_operation",
        "graphql_variables",
        "body",
        "content_type",
        "authorization",
        "token",
        "retry",
        "timeout",
        "redirects",
        "user_agent",
        "response",
        "response_id",
        "artifact",
        "source_subject",
        "acquisition_run",
        "previous_request_id",
        "latest_request_id",
    ),
)
def test_request_reference_rejects_controls_responses_and_later_scope(
    extra_field: str,
) -> None:
    data = _reference_data()
    data[extra_field] = "forbidden"
    with pytest.raises(ValidationError) as error:
        RetrievalRequestReference.model_validate(data)
    assert error.value.errors()[0]["type"] == "extra_forbidden"
    assert error.value.errors()[0]["loc"] == (extra_field,)


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("request_id", {"schema_version": 1}),
        (
            "authority",
            {
                "schema_version": 1,
                "provider": "github",
                "role": "retrieval",
                "host": "api.github.com",
            },
        ),
        ("method", "get"),
        ("route_path", "/graphql"),
    ),
)
def test_reference_requires_typed_nested_python_values(
    field: str,
    value: object,
) -> None:
    with pytest.raises(ValidationError):
        _reference(**{field: value})


def test_same_request_id_with_different_metadata_is_not_same_reference() -> None:
    request_id = _request_id()
    first = _reference(request_id=request_id)
    second = _reference(
        request_id=request_id,
        route_path=RetrievalRoutePath.model_validate("/repos/example/project/issues/2"),
        started_at=SYNTHETIC_STARTED_AT + timedelta(seconds=1),
    )
    assert first.request_id == second.request_id
    assert first != second


@pytest.mark.parametrize(
    ("model", "field", "value"),
    (
        (AcquisitionRunId.model_validate("run-a"), "root", "changed"),
        (RetrievalRequestOrdinal.model_validate(1), "root", 2),
        (
            _request_id(),
            "request_ordinal",
            RetrievalRequestOrdinal.model_validate(2),
        ),
        (RetrievalRoutePath.model_validate("/graphql"), "root", "/changed"),
        (_reference(), "method", RetrievalMethod.POST),
    ),
)
def test_models_are_frozen(model: object, field: str, value: object) -> None:
    with pytest.raises(ValidationError):
        setattr(model, field, value)


@pytest.mark.parametrize(
    "model",
    (
        AcquisitionRunId.model_validate("run-a"),
        RetrievalRequestOrdinal.model_validate(1),
        _request_id(),
        RetrievalRoutePath.model_validate("/graphql"),
        _reference(),
    ),
)
def test_models_reject_dynamic_attributes(model: object) -> None:
    with pytest.raises(ValidationError):
        setattr(model, "unexpected", "value")


@pytest.mark.parametrize(
    ("run_id", "ordinal"),
    (
        (AcquisitionRunId.model_construct(root="Run-A"), RetrievalRequestOrdinal(1)),
        (AcquisitionRunId("run-a"), RetrievalRequestOrdinal.model_construct(root=0)),
    ),
)
def test_request_id_revalidates_constructed_invalid_nested_models(
    run_id: AcquisitionRunId,
    ordinal: RetrievalRequestOrdinal,
) -> None:
    with pytest.raises(ValidationError):
        RetrievalRequestId(
            acquisition_run_id=run_id,
            request_ordinal=ordinal,
        )


def test_reference_revalidates_constructed_invalid_nested_request_id() -> None:
    invalid_request_id = RetrievalRequestId.model_construct(
        schema_version=1,
        acquisition_run_id=AcquisitionRunId("run-a"),
        request_ordinal=RetrievalRequestOrdinal.model_construct(root=0),
    )
    with pytest.raises(ValidationError):
        _reference(request_id=invalid_request_id)


@pytest.mark.parametrize(
    ("field", "value"),
    (
        (
            "authority",
            ProviderAuthority.model_construct(
                schema_version=1,
                provider=_provider(),
                role=AuthorityRole.RETRIEVAL,
                host="Bad Host",
            ),
        ),
        (
            "route_path",
            RetrievalRoutePath.model_construct(root="https://api.example.test/path"),
        ),
    ),
)
def test_reference_revalidates_other_constructed_invalid_nested_models(
    field: str,
    value: object,
) -> None:
    with pytest.raises(ValidationError):
        _reference(**{field: value})


def test_semantic_json_round_trips_reconstruct_equal_typed_models() -> None:
    run_id = AcquisitionRunId.model_validate(CANONICAL_RUN_ID)
    ordinal = RetrievalRequestOrdinal.model_validate(29)
    request_id = RetrievalRequestId(
        acquisition_run_id=run_id,
        request_ordinal=ordinal,
    )
    reference = _reference(request_id=request_id)

    assert AcquisitionRunId.model_validate_json(run_id.model_dump_json()) == run_id
    assert (
        RetrievalRequestOrdinal.model_validate_json(ordinal.model_dump_json())
        == ordinal
    )
    assert (
        RetrievalRequestId.model_validate_json(request_id.model_dump_json())
        == request_id
    )
    assert (
        RetrievalRequestReference.model_validate_json(reference.model_dump_json())
        == reference
    )
    assert reference.model_dump_json() == reference.model_dump_json()


def test_serialization_is_semantic_and_declares_no_canonical_byte_contract() -> None:
    source = EVIDENCE_SOURCE.read_text(encoding="utf-8")
    tree = ast.parse(source)
    definition_names = {
        node.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    assert (
        not {
            "canonical_bytes",
            "canonical_json",
            "serialize_bytes",
            "to_bytes",
        }
        & definition_names
    )
    assert {name for name in definition_names if "canonical" in name.casefold()} == {
        "_require_typed_python_canonicalization",
        "_validate_canonicalization",
    }
    assert _reference().model_dump(mode="json")["schema_version"] == 1


def test_evidence_module_has_exact_ordered_exports_and_public_surface() -> None:
    source = EVIDENCE_SOURCE.read_text(encoding="utf-8")
    _validate_evidence_surface(source)
    assert tuple(evidence_module.__all__) == EXPECTED_EVIDENCE_EXPORTS


@pytest.mark.parametrize("mutation", ("missing-export", "unexpected-export"))
def test_evidence_export_mutations_are_rejected(mutation: str) -> None:
    source = EVIDENCE_SOURCE.read_text(encoding="utf-8")
    if mutation == "missing-export":
        mutated = source.replace('    "RetrievalRequestReference",\n', "", 1)
    else:
        mutated = source.replace(
            '    "RetrievalRequestReference",\n',
            '    "RetrievalRequestReference",\n    "ResponseObservation",\n',
            1,
        )
    with pytest.raises(AssertionError):
        _validate_evidence_surface(mutated)


def test_package_and_domain_roots_do_not_export_evidence_symbols() -> None:
    package_source = (REPOSITORY_ROOT / "src/faultatlas/__init__.py").read_text(
        encoding="utf-8"
    )
    _validate_package_root_exports(package_source)
    assert faultatlas.__all__ == ["__version__"]
    assert getattr(domain_package, "__all__", None) in (None, [])
    assert not any(hasattr(faultatlas, name) for name in EXPECTED_EVIDENCE_EXPORTS)
    assert not any(hasattr(domain_package, name) for name in EXPECTED_EVIDENCE_EXPORTS)


def test_package_root_evidence_export_mutation_is_rejected() -> None:
    source = (REPOSITORY_ROOT / "src/faultatlas/__init__.py").read_text(
        encoding="utf-8"
    )
    mutated = source.replace(
        '__all__ = ["__version__"]',
        '__all__ = ["__version__", "RetrievalRequestId"]',
        1,
    )
    with pytest.raises(AssertionError):
        _validate_package_root_exports(mutated)


def test_current_production_inventory_is_exactly_nine_files() -> None:
    paths = {
        path.relative_to(REPOSITORY_ROOT).as_posix()
        for path in (REPOSITORY_ROOT / "src").rglob("*.py")
    }
    _validate_production_inventory(paths)
    assert len(paths) == 9


@pytest.mark.parametrize("mutation", ("missing-evidence", "unexpected-tenth"))
def test_production_inventory_mutations_are_rejected(mutation: str) -> None:
    paths = set(EXPECTED_PRODUCTION_FILES)
    if mutation == "missing-evidence":
        paths.remove("src/faultatlas/domain/evidence.py")
    else:
        paths.add("src/faultatlas/domain/response.py")
    with pytest.raises(AssertionError):
        _validate_production_inventory(paths)


@pytest.mark.parametrize(
    "class_name",
    (
        "ResponseObservation",
        "_PrivateResponseObservation",
        "RetainedArtifactRecord",
        "AcquisitionRunRecord",
        "TransformationRecord",
        "OmissionRecord",
        "EvidenceContractCorpus",
        "EvidenceMigration",
        "EvidencePersistence",
        "EvidenceReader",
        "EvidenceStorage",
        "EvidenceWriter",
        "EvidenceAdapterRegistry",
        "EvidenceConfidence",
        "EvidenceReview",
        "RepositorySnapshot",
    ),
)
def test_post_s07_surface_mutations_are_rejected(class_name: str) -> None:
    source = EVIDENCE_SOURCE.read_text(encoding="utf-8")
    mutated = source + f"\n\nclass {class_name}:\n    pass\n"
    with pytest.raises(AssertionError):
        _validate_evidence_surface(mutated)


def test_evidence_module_has_no_io_or_secret_bearing_surface() -> None:
    source = EVIDENCE_SOURCE.read_text(encoding="utf-8")
    _validate_evidence_imports_and_calls(source)
    for forbidden in (
        "authorization",
        "bearer",
        "headers: dict",
        "token:",
        "api_key",
    ):
        assert forbidden not in source.casefold()


@pytest.mark.parametrize(
    "mutation",
    (
        "import io",
        "import requests",
        "from pathlib import Path",
        "from urllib.request import urlopen",
    ),
)
def test_io_import_mutations_are_rejected(mutation: str) -> None:
    source = EVIDENCE_SOURCE.read_text(encoding="utf-8")
    with pytest.raises(AssertionError):
        _validate_evidence_imports_and_calls(f"{mutation}\n{source}")


def test_request_models_have_no_controls_response_subject_run_or_retry_fields() -> None:
    assert set(RetrievalRequestId.model_fields) == {
        "schema_version",
        "acquisition_run_id",
        "request_ordinal",
    }
    assert set(RetrievalRequestReference.model_fields) == {
        "schema_version",
        "request_id",
        "authority",
        "method",
        "route_path",
        "started_at",
    }
    forbidden = {
        "accept",
        "acquisition_run",
        "artifact",
        "body",
        "content_type",
        "cursor",
        "full_url",
        "headers",
        "latest_request_id",
        "query",
        "response",
        "retry",
        "source_subject",
        "token",
    }
    assert not forbidden & set(RetrievalRequestReference.model_fields)


def test_predecessor_production_models_and_artifact_snapshot_are_unchanged() -> None:
    for relative, (byte_length, digest) in PREDECESSOR_LOCKS.items():
        raw = (REPOSITORY_ROOT / relative).read_bytes()
        assert len(raw) == byte_length
        assert sha256(raw).hexdigest() == digest
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


def test_no_p03_contract_corpus_reader_or_s08_plus_surface_exists() -> None:
    _assert_no_post_s07_surface(EVIDENCE_SOURCE.read_text(encoding="utf-8"))
    assert not (REPOSITORY_ROOT / "reference_corpus/contracts/evidence").exists()
    assert not (
        REPOSITORY_ROOT / "reference_corpus/contracts/retrieval-request"
    ).exists()
