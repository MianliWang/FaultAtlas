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
    ApiVersion,
    ContentEncoding,
    HttpStatusCode,
    MediaType,
    MediaTypeParameter,
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
from faultatlas.domain.identity import (
    AuthorityRole,
    ProviderAuthority,
    ProviderKey,
    ProviderRepositoryId,
    RepositoryIdentity,
    SourceIdentityLifecycleState,
)
from faultatlas.domain.revision import (
    GitBlobIdentity,
    GitHashAlgorithm,
    GitObjectKind,
    GitTreeIdentity,
)
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
CANONICAL_RUN_ID = "run-0001-s04-v1-base-4c9cde74-head-690a63b9"
CANONICAL_ACQUISITION_SHA256 = (
    "1c29093bf1537e9b824a18df1848b71a8da014f544bc9f385707eb0e000a1318"
)
SYNTHETIC_COMPLETED_AT = datetime(2026, 8, 2, 16, 0, 1, tzinfo=UTC)

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

CANONICAL_FACT_CASES = (
    {
        "case_id": "rest-json-ordinal-1",
        "json_pointer": "/requests/records/0",
        "ordinal": 1,
        "requested_media_type": "application/vnd.github+json",
        "api_version": "2026-03-10",
        "completed_at": "2026-07-24T11:03:15.996744Z",
        "status_code": 200,
        "observed_media_type": "application/json",
        "content_encoding": None,
    },
    {
        "case_id": "query-bearing-rest-ordinal-9",
        "json_pointer": "/requests/records/8",
        "ordinal": 9,
        "requested_media_type": "application/vnd.github+json",
        "api_version": "2026-03-10",
        "completed_at": "2026-07-24T11:03:20.302484Z",
        "status_code": 200,
        "observed_media_type": "application/json",
        "content_encoding": None,
    },
    {
        "case_id": "retained-diff-ordinal-30",
        "json_pointer": "/requests/records/29",
        "ordinal": 30,
        "requested_media_type": "application/vnd.github.diff",
        "api_version": "2026-03-10",
        "completed_at": "2026-07-24T11:03:30.930138Z",
        "status_code": 200,
        "observed_media_type": "application/vnd.github.diff",
        "content_encoding": None,
    },
    {
        "case_id": "historical-license-ordinal-32",
        "json_pointer": "/requests/records/31",
        "ordinal": 32,
        "requested_media_type": "application/vnd.github.raw+json",
        "api_version": "2026-03-10",
        "completed_at": "2026-07-24T11:03:31.777359Z",
        "status_code": 200,
        "observed_media_type": "text/plain",
        "content_encoding": None,
    },
)
SYNTHETIC_SCENARIOS = (
    "controls-no-query-delimiter",
    "controls-bare-query-delimiter",
    "controls-bare-query-name",
    "controls-explicit-empty-query-value",
    "controls-duplicate-query-names",
    "controls-requested-json",
    "controls-requested-diff",
    "controls-api-version-present",
    "controls-api-version-absent",
    "response-observed-json",
    "response-observed-text-charset",
    "response-observed-encoding-chain",
    "response-unavailable",
    "response-inaccessible",
    "response-unknown",
    "response-same-request-two-observations",
    "response-requested-observed-mismatch",
    "cross-layer-composition",
)


def _load_acquisition() -> dict[str, Any]:
    value = cast(object, json.loads(ACQUISITION_PATH.read_text(encoding="utf-8")))
    assert isinstance(value, dict)
    return cast(dict[str, Any], value)


def _request_id(
    *,
    run_id: str = "run-synthetic-response-001",
    ordinal: int = 1,
) -> RetrievalRequestId:
    return RetrievalRequestId(
        acquisition_run_id=AcquisitionRunId.model_validate(run_id),
        request_ordinal=RetrievalRequestOrdinal.model_validate(ordinal),
    )


def _query(
    name: str,
    value: str,
    *,
    value_delimiter_present: bool = True,
) -> RequestQueryParameter:
    return RequestQueryParameter(
        name=name,
        value=value,
        value_delimiter_present=value_delimiter_present,
    )


def _parameter(name: str, value: str) -> MediaTypeParameter:
    return MediaTypeParameter(name=name, value=value)


def _encoding(value: str) -> ContentEncoding:
    return ContentEncoding.model_validate(value)


def _controls_data(**overrides: object) -> dict[str, object]:
    data: dict[str, object] = {
        "query_delimiter_present": False,
        "query_parameters": (),
        "requested_media_type": MediaType.model_validate("application/json"),
        "api_version": None,
    }
    data.update(overrides)
    return data


def _controls(**overrides: object) -> RetrievalRequestControls:
    return RetrievalRequestControls.model_validate(_controls_data(**overrides))


def _observation_data(**overrides: object) -> dict[str, object]:
    data: dict[str, object] = {
        "request_id": _request_id(),
        "state": ResponseRepresentationState.OBSERVED,
        "completed_at": SYNTHETIC_COMPLETED_AT,
        "status_code": HttpStatusCode.model_validate(200),
        "observed_media_type": MediaType.model_validate("application/json"),
        "media_type_parameters": (),
        "content_encodings": None,
    }
    data.update(overrides)
    return data


def _observation(**overrides: object) -> ResponseRepresentationObservation:
    return ResponseRepresentationObservation.model_validate(
        _observation_data(**overrides)
    )


def _unobserved(
    state: ResponseRepresentationState,
    **overrides: object,
) -> ResponseRepresentationObservation:
    data = _observation_data(
        state=state,
        status_code=None,
        observed_media_type=None,
        media_type_parameters=None,
        content_encodings=None,
    )
    data.update(overrides)
    return ResponseRepresentationObservation.model_validate(data)


def _reference(request_id: RetrievalRequestId) -> RetrievalRequestReference:
    return RetrievalRequestReference(
        request_id=request_id,
        authority=ProviderAuthority(
            provider=ProviderKey.model_validate("github"),
            role=AuthorityRole.RETRIEVAL,
            host="api.github.com",
        ),
        method=RetrievalMethod.GET,
        route_path=RetrievalRoutePath.model_validate("/repos/example/project"),
        started_at=SYNTHETIC_COMPLETED_AT - timedelta(seconds=1),
    )


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
    items = cast(list[object], value)
    assert all(isinstance(item, str) for item in items)
    return tuple(cast(str, item) for item in items)


def _parse_media_parameter_name_limit(source: str) -> int:
    tree = ast.parse(source)
    assignments = [
        node
        for node in tree.body
        if isinstance(node, ast.AnnAssign)
        and isinstance(node.target, ast.Name)
        and node.target.id == "_MAX_MEDIA_PARAMETER_NAME_LENGTH"
    ]
    assert len(assignments) == 1
    assignment = assignments[0]
    assert isinstance(assignment.annotation, ast.Name)
    assert assignment.annotation.id == "int"
    assert assignment.value is not None
    value = cast(object, ast.literal_eval(assignment.value))
    assert type(value) is int
    return value


def _parse_collection_limits(source: str) -> dict[str, int]:
    expected_names = {
        "_MAX_QUERY_PARAMETERS",
        "_MAX_MEDIA_TYPE_PARAMETERS",
        "_MAX_CONTENT_ENCODINGS",
    }
    values: dict[str, int] = {}
    for node in ast.parse(source).body:
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        target = node.targets[0]
        if not isinstance(target, ast.Name) or target.id not in expected_names:
            continue
        value = cast(object, ast.literal_eval(node.value))
        assert type(value) is int
        values[target.id] = value
    assert set(values) == expected_names
    return values


def _validate_evidence_exports(source: str) -> None:
    exports = _parse_exports(source)
    assert exports == EXPECTED_EVIDENCE_EXPORTS
    assert len(exports) == len(set(exports)) == 58
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
    assert sum(isinstance(node, ast.ClassDef) for node in tree.body) == 58
    assert tuple(
        node.name.id for node in tree.body if isinstance(node, ast.TypeAlias)
    ) == ("EvidenceRecordRelationship",)


def _validate_no_post_s07_evidence_surface(source: str) -> None:
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
        "ResponseIdentity",
        "RetainedArtifact",
        "RetainedArtifactRecord",
        "TransformationRecord",
    }
    assert not definitions & forbidden


def _assert_query_order_and_multiplicity(
    controls: RetrievalRequestControls,
    expected: tuple[tuple[str, str, bool], ...],
) -> None:
    observed = tuple(
        (
            parameter.name,
            parameter.value,
            parameter.value_delimiter_present,
        )
        for parameter in controls.query_parameters
    )
    assert observed == expected


def _assert_collection_limit_error(
    error: pytest.ExceptionInfo[ValidationError],
    *,
    field: str,
    maximum: int,
) -> None:
    errors = error.value.errors()
    assert len(errors) == 1
    assert errors[0]["loc"] == (field,)
    assert f"at most {maximum} entries" in errors[0]["msg"]


def _assert_encoded_query_component(value: str, *, allow_empty: bool) -> None:
    if not allow_empty:
        assert value
    unreserved = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~"
    hexadecimal = "0123456789ABCDEFabcdef"
    index = 0
    while index < len(value):
        character = value[index]
        if character in unreserved:
            index += 1
            continue
        assert character == "%"
        assert index + 2 < len(value)
        assert value[index + 1] in hexadecimal
        assert value[index + 2] in hexadecimal
        index += 3


def _replay_query(parameters: tuple[RequestQueryParameter, ...]) -> str:
    return "&".join(
        parameter.name
        + (f"={parameter.value}" if parameter.value_delimiter_present else "")
        for parameter in parameters
    )


def _replay_request_target(
    route_path: str,
    controls: RetrievalRequestControls,
) -> str:
    query = _replay_query(controls.query_parameters)
    return route_path + (f"?{query}" if controls.query_delimiter_present else "")


def _parse_replayed_query(query: str) -> tuple[tuple[str, str, bool], ...]:
    if not query:
        return ()
    parsed: list[tuple[str, str, bool]] = []
    for entry in query.split("&"):
        name, separator, value = entry.partition("=")
        assert "=" not in value
        _assert_encoded_query_component(name, allow_empty=False)
        _assert_encoded_query_component(value, allow_empty=True)
        parsed.append((name, value, bool(separator)))
    return tuple(parsed)


def _assert_media_mismatch(
    controls: RetrievalRequestControls,
    observation: ResponseRepresentationObservation,
) -> None:
    assert controls.requested_media_type is not None
    assert observation.observed_media_type is not None
    assert controls.requested_media_type != observation.observed_media_type


def test_canonical_acquisition_lock_and_fact_registries_are_exact() -> None:
    raw = ACQUISITION_PATH.read_bytes()
    assert len(raw) == 61_283
    assert sha256(raw).hexdigest() == CANONICAL_ACQUISITION_SHA256
    assert len(CANONICAL_FACT_CASES) == 4
    assert len({case["case_id"] for case in CANONICAL_FACT_CASES}) == 4
    assert len(SYNTHETIC_SCENARIOS) == len(set(SYNTHETIC_SCENARIOS)) == 18


def test_canonical_facts_are_directly_bound_to_exact_request_records() -> None:
    acquisition = _load_acquisition()
    run = cast(dict[str, Any], acquisition["run"])
    requests = cast(dict[str, Any], acquisition["requests"])
    records = cast(list[dict[str, Any]], requests["records"])

    assert run["run_id"] == CANONICAL_RUN_ID
    for case in CANONICAL_FACT_CASES:
        ordinal = cast(int, case["ordinal"])
        record = records[ordinal - 1]
        assert record["ordinal"] == ordinal
        assert record["accept"] == case["requested_media_type"]
        assert record["api_version"] == case["api_version"]
        assert record["completed_at"] == case["completed_at"]
        assert record["status"] == case["status_code"]
        assert record["content_type"] == case["observed_media_type"]
        assert record["content_encoding"] == case["content_encoding"]
        assert case["json_pointer"] == f"/requests/records/{ordinal - 1}"


def test_canonical_facts_construct_only_supported_ids_and_primitives() -> None:
    acquisition = _load_acquisition()
    records = cast(
        list[dict[str, Any]],
        cast(dict[str, Any], acquisition["requests"])["records"],
    )
    run_id = AcquisitionRunId.model_validate(CANONICAL_RUN_ID)

    for case in CANONICAL_FACT_CASES:
        ordinal = cast(int, case["ordinal"])
        record = records[ordinal - 1]
        request_id = RetrievalRequestId(
            acquisition_run_id=run_id,
            request_ordinal=RetrievalRequestOrdinal.model_validate(ordinal),
        )
        assert request_id.request_ordinal.root == ordinal
        assert MediaType.model_validate(record["accept"]).root == record["accept"]
        assert (
            ApiVersion.model_validate(record["api_version"]).root
            == (record["api_version"])
        )
        assert HttpStatusCode.model_validate(record["status"]).root == 200
        assert (
            MediaType.model_validate(record["content_type"]).root
            == (record["content_type"])
        )


def test_canonical_license_media_mismatch_and_parameter_are_direct() -> None:
    acquisition = _load_acquisition()
    records = cast(
        list[dict[str, Any]],
        cast(dict[str, Any], acquisition["requests"])["records"],
    )
    record = records[31]

    assert record["requested_accept"] == "application/vnd.github.raw+json"
    assert record["observed_content_type_media_type"] == "text/plain"
    assert record["observed_content_type_parameters"] == [
        {"name": "charset", "value": "utf-8"}
    ]
    assert record["media_metadata_warning"] == (
        "content_type_differs_from_requested_accept"
    )


def test_no_canonical_full_s02_model_is_claimed_without_required_fields() -> None:
    acquisition = _load_acquisition()
    records = cast(
        list[dict[str, Any]],
        cast(dict[str, Any], acquisition["requests"])["records"],
    )

    assert all("query_parameters" not in record for record in records)
    assert all("state" not in record for record in records)
    assert all("request_id" not in record for record in records)
    assert {record["method"] for record in records} == {"GET"}
    assert not any(record["safe_target"].casefold() == "/graphql" for record in records)


@pytest.mark.parametrize(
    "value",
    (
        "a/b",
        "application/json",
        "Application/JSON",
        "TEXT/PLAIN",
        "application/Vnd.GitHub.Raw+Json",
        "text/plain",
        "application/vnd.github.diff",
        "application/vnd.github.raw+json",
        "application/x*json",
        "a/" + ("b" * 253),
    ),
)
def test_media_type_accepts_and_preserves_valid_bounded_tokens(value: str) -> None:
    media_type = MediaType.model_validate(value)
    assert media_type.root == value


@pytest.mark.parametrize(
    "value",
    (
        " application/json",
        "application/json ",
        "application /json",
        "application/ json",
        "applicationjson",
        "application/json/extra",
        "*/*",
        "application/*",
        "*/json",
        "application/json;charset=utf-8",
        "application/",
        "/json",
        "application/éjson",
        "application/json\n",
        "a/" + ("b" * 254),
        1,
        b"application/json",
        None,
    ),
)
def test_media_type_rejects_malformed_or_coercive_values(value: object) -> None:
    with pytest.raises(ValidationError):
        MediaType.model_validate(value)


def test_media_type_preserves_case_without_merging_parameters() -> None:
    lower = MediaType.model_validate("application/vnd.github.raw+json")
    mixed = MediaType.model_validate("Application/Vnd.GitHub.Raw+Json")
    assert lower.root == "application/vnd.github.raw+json"
    assert mixed.root == "Application/Vnd.GitHub.Raw+Json"
    assert mixed != lower
    assert MediaType.model_validate_json(mixed.model_dump_json()) == mixed
    with pytest.raises(ValidationError):
        MediaType.model_validate("text/plain; charset=utf-8")


def test_http_token_models_accept_every_ascii_letter_case_without_normalizing() -> None:
    letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
    media_type = MediaType.model_validate(f"{letters}/{letters}")
    encoding = ContentEncoding.model_validate(letters)
    parameter = MediaTypeParameter(name=letters, value="value")

    assert media_type.root == f"{letters}/{letters}"
    assert encoding.root == letters
    assert parameter.name == letters
    assert MediaType.model_validate_json(media_type.model_dump_json()) == media_type
    assert ContentEncoding.model_validate_json(encoding.model_dump_json()) == encoding
    assert (
        MediaTypeParameter.model_validate_json(parameter.model_dump_json()) == parameter
    )


@pytest.mark.parametrize(
    "value",
    ("2026-03-10", "v1", "V1", "not-a-date", "a" * 128),
)
def test_api_version_accepts_exact_nonsemantic_lexemes(value: str) -> None:
    version = ApiVersion.model_validate(value)
    assert version.root == value


@pytest.mark.parametrize(
    "value",
    (
        "",
        " 2026-03-10",
        "2026-03-10 ",
        "2026 03 10",
        "2026\t03",
        "2026\n03",
        "versión",
        "a" * 129,
        20260310,
        1.0,
        b"v1",
        None,
    ),
)
def test_api_version_rejects_whitespace_controls_non_ascii_and_coercion(
    value: object,
) -> None:
    with pytest.raises(ValidationError):
        ApiVersion.model_validate(value)


def test_api_version_is_not_date_parsed_or_normalized() -> None:
    first = ApiVersion.model_validate("2026-03-10")
    second = ApiVersion.model_validate("not-a-date")
    upper = ApiVersion.model_validate("V1")
    lower = ApiVersion.model_validate("v1")
    assert first.root == "2026-03-10"
    assert second.root == "not-a-date"
    assert upper.root == "V1"
    assert lower.root == "v1"
    assert upper != lower


def test_query_parameters_preserve_exact_order_duplicates_case_value_and_delimiter() -> (
    None
):
    controls = _controls(
        query_delimiter_present=True,
        query_parameters=(
            _query("cursor", "first"),
            _query("Cursor", "", value_delimiter_present=False),
            _query("Cursor", "", value_delimiter_present=True),
            _query("cursor", "second"),
        ),
    )
    expected = (
        ("cursor", "first", True),
        ("Cursor", "", False),
        ("Cursor", "", True),
        ("cursor", "second", True),
    )
    _assert_query_order_and_multiplicity(controls, expected)


def test_bare_and_explicitly_empty_query_values_are_distinct_and_json_stable() -> None:
    bare = _query("flag", "", value_delimiter_present=False)
    explicit_empty = _query("flag", "", value_delimiter_present=True)

    assert bare.name == explicit_empty.name == "flag"
    assert bare.value == explicit_empty.value == ""
    assert bare.value_delimiter_present is False
    assert explicit_empty.value_delimiter_present is True
    assert bare != explicit_empty
    assert bare.model_dump(mode="json") == {
        "name": "flag",
        "value": "",
        "value_delimiter_present": False,
    }
    assert explicit_empty.model_dump(mode="json") == {
        "name": "flag",
        "value": "",
        "value_delimiter_present": True,
    }
    assert RequestQueryParameter.model_validate_json(bare.model_dump_json()) == bare
    assert (
        RequestQueryParameter.model_validate_json(explicit_empty.model_dump_json())
        == explicit_empty
    )


@pytest.mark.parametrize("field", ("name", "value"))
@pytest.mark.parametrize(
    "lexeme",
    (
        "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~",
        "%2B",
        "%20",
        "%2F",
        "%26",
        "%3D",
        "%23",
        "%3F",
        "%3A",
        "%3B",
        "%25",
        "%00%7F%80%FF",
        "%C3%A9",
        "%2f%2F%aB%Ab",
        "%2526",
    ),
)
def test_query_component_encoded_lexemes_are_accepted_and_preserved_exactly(
    field: str,
    lexeme: str,
) -> None:
    data = {
        "name": "name",
        "value": "value",
        "value_delimiter_present": True,
    }
    data[field] = lexeme
    parameter = RequestQueryParameter.model_validate(data)
    assert getattr(parameter, field) == lexeme
    reconstructed = RequestQueryParameter.model_validate_json(
        parameter.model_dump_json()
    )
    assert getattr(reconstructed, field) == lexeme


def test_query_replay_preserves_flags_order_duplicates_and_encoded_delimiters() -> None:
    parameters = (
        _query("flag", "", value_delimiter_present=False),
        _query("flag", "", value_delimiter_present=True),
        _query("flag", "value"),
        _query("duplicate", "first"),
        _query("duplicate", "second"),
        _query("encoded%26name", "left%3Dright"),
        _query("encoded%3Dname", "left%26right"),
        _query("slash", "%2f"),
        _query("slash", "%2F"),
    )
    expected_entries = (
        ("flag", "", False),
        ("flag", "", True),
        ("flag", "value", True),
        ("duplicate", "first", True),
        ("duplicate", "second", True),
        ("encoded%26name", "left%3Dright", True),
        ("encoded%3Dname", "left%26right", True),
        ("slash", "%2f", True),
        ("slash", "%2F", True),
    )
    expected_query = (
        "flag&flag=&flag=value&duplicate=first&duplicate=second&"
        "encoded%26name=left%3Dright&encoded%3Dname=left%26right&"
        "slash=%2f&slash=%2F"
    )

    assert _replay_query(parameters) == expected_query
    assert _parse_replayed_query(expected_query) == expected_entries
    assert _replay_query(()) == ""
    assert _parse_replayed_query("") == ()

    controls = _controls(query_delimiter_present=True, query_parameters=parameters)
    reconstructed = RetrievalRequestControls.model_validate_json(
        controls.model_dump_json()
    )
    assert _replay_query(reconstructed.query_parameters) == expected_query
    assert _parse_replayed_query(_replay_query(reconstructed.query_parameters)) == (
        expected_entries
    )


def test_query_encoded_and_literal_lexemes_remain_distinct() -> None:
    assert _query("A", "~") != _query("%41", "%7E")
    assert _query("slash", "%2f") != _query("slash", "%2F")


@pytest.mark.parametrize("field", ("name", "value"))
@pytest.mark.parametrize(
    "character",
    tuple(
        chr(code)
        for code in range(128)
        if chr(code)
        not in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~%"
    ),
)
def test_query_components_reject_every_raw_ascii_non_unreserved_character(
    field: str,
    character: str,
) -> None:
    data = {
        "name": "name",
        "value": "value",
        "value_delimiter_present": True,
    }
    data[field] = f"before{character}after"
    with pytest.raises(ValidationError):
        RequestQueryParameter.model_validate(data)


@pytest.mark.parametrize("field", ("name", "value"))
@pytest.mark.parametrize(
    "lexeme",
    (
        "%_",
        "a%_b",
        "a%",
        "%0_",
        "a%0_b",
        "a%0",
        "%G_",
        "a%G_b",
        "a%G",
        "%0G_",
        "a%0G_b",
        "a%0G",
        "%G0_",
        "a%G0_b",
        "a%G0",
        "%GG_",
        "a%GG_b",
        "a%GG",
    ),
)
def test_query_components_reject_malformed_percent_escapes_at_every_position(
    field: str,
    lexeme: str,
) -> None:
    data = {
        "name": "name",
        "value": "value",
        "value_delimiter_present": True,
    }
    data[field] = lexeme
    with pytest.raises(ValidationError):
        RequestQueryParameter.model_validate(data)


@pytest.mark.parametrize("field", ("name", "value"))
@pytest.mark.parametrize(
    "lexeme",
    (
        "raw&delimiter",
        "raw=delimiter",
        "raw#fragment",
        "raw?query",
        "raw+plus",
        "raw/slash",
        "raw:colon",
        "raw:semicolon",
        "raw space",
        "naïve",
        "%",
        "%0",
        "%GG",
    ),
)
def test_query_component_json_rejects_raw_delimiters_and_malformed_escapes(
    field: str,
    lexeme: str,
) -> None:
    data = {
        "name": "name",
        "value": "value",
        "value_delimiter_present": True,
    }
    data[field] = lexeme
    with pytest.raises(ValidationError):
        RequestQueryParameter.model_validate_json(json.dumps(data))


def test_query_parameter_fields_are_exact_and_each_is_required() -> None:
    assert tuple(RequestQueryParameter.model_fields) == (
        "name",
        "value",
        "value_delimiter_present",
    )
    data: dict[str, object] = {
        "name": "flag",
        "value": "",
        "value_delimiter_present": False,
    }
    for field in tuple(data):
        incomplete = dict(data)
        del incomplete[field]
        with pytest.raises(ValidationError) as error:
            RequestQueryParameter.model_validate(incomplete)
        assert error.value.errors()[0]["type"] == "missing"


@pytest.mark.parametrize("value", (0, 1, "true", "false", None))
def test_query_parameter_value_delimiter_presence_requires_exact_bool(
    value: object,
) -> None:
    with pytest.raises(ValidationError):
        RequestQueryParameter.model_validate(
            {
                "name": "flag",
                "value": "",
                "value_delimiter_present": value,
            }
        )


def test_nonempty_query_value_requires_value_delimiter() -> None:
    with pytest.raises(ValidationError, match="requires value_delimiter_present"):
        _query("flag", "value", value_delimiter_present=False)


@pytest.mark.parametrize(
    "data",
    (
        {"name": "flag", "value": "", "value_delimiter_present": 0},
        {"name": "flag", "value": "", "value_delimiter_present": "false"},
        {"name": "flag", "value": "value", "value_delimiter_present": False},
    ),
)
def test_query_parameter_json_rejects_invalid_delimiter_states(
    data: dict[str, object],
) -> None:
    with pytest.raises(ValidationError):
        RequestQueryParameter.model_validate_json(json.dumps(data))


def test_query_order_and_duplicate_failure_sensitivity() -> None:
    controls = _controls(
        query_delimiter_present=True,
        query_parameters=(
            _query("page", "1"),
            _query("page", "2"),
            _query("sort", "created"),
        ),
    )
    expected = (
        ("page", "1", True),
        ("page", "2", True),
        ("sort", "created", True),
    )
    _assert_query_order_and_multiplicity(controls, expected)
    with pytest.raises(AssertionError):
        _assert_query_order_and_multiplicity(
            controls,
            (
                ("page", "2", True),
                ("page", "1", True),
                ("sort", "created", True),
            ),
        )
    with pytest.raises(AssertionError):
        _assert_query_order_and_multiplicity(
            controls,
            (("page", "1", True), ("sort", "created", True)),
        )


@pytest.mark.parametrize("field", ("name", "value"))
@pytest.mark.parametrize("control", (*map(chr, range(32)), chr(127)))
def test_query_parameters_reject_all_ascii_controls(
    field: str,
    control: str,
) -> None:
    data = {
        "name": "name",
        "value": "value",
        "value_delimiter_present": True,
    }
    data[field] = f"before{control}after"
    with pytest.raises(ValidationError):
        RequestQueryParameter.model_validate(data)


def test_query_parameter_length_bounds_are_exact() -> None:
    assert _query("n", "").value == ""
    assert len(_query("n" * 256, "v" * 4096).name) == 256
    percent_heavy_name = "%41" * 85 + "A"
    percent_heavy_value = "%41" * 1365 + "A"
    assert len(percent_heavy_name) == 256
    assert len(percent_heavy_value) == 4096
    assert _query(percent_heavy_name, percent_heavy_value).name == percent_heavy_name
    with pytest.raises(ValidationError):
        _query("", "value")
    with pytest.raises(ValidationError):
        _query("n" * 257, "value")
    with pytest.raises(ValidationError):
        _query("name", "v" * 4097)
    with pytest.raises(ValidationError):
        _query(percent_heavy_name + "A", "value")
    with pytest.raises(ValidationError):
        _query("name", percent_heavy_value + "A")


@pytest.mark.parametrize(
    ("field", "value"),
    (("name", "naïve"), ("value", "välue"), ("name", 1), ("value", 1)),
)
def test_query_parameters_reject_non_ascii_and_non_string_values(
    field: str,
    value: object,
) -> None:
    data: dict[str, object] = {
        "name": "name",
        "value": "value",
        "value_delimiter_present": True,
    }
    data[field] = value
    with pytest.raises(ValidationError):
        RequestQueryParameter.model_validate(data)


def test_query_parameter_rejects_extras_and_is_frozen() -> None:
    with pytest.raises(ValidationError):
        RequestQueryParameter.model_validate(
            {
                "name": "page",
                "value": "1",
                "value_delimiter_present": True,
                "decoded": "1",
            }
        )
    parameter = _query("page", "1")
    with pytest.raises(ValidationError):
        parameter.name = "changed"
    with pytest.raises(ValidationError):
        parameter.value_delimiter_present = False


def test_request_controls_fields_are_exact_and_minimal_controls_are_explicit() -> None:
    assert tuple(RetrievalRequestControls.model_fields) == (
        "schema_version",
        "query_delimiter_present",
        "query_parameters",
        "requested_media_type",
        "api_version",
    )
    controls = _controls()
    assert controls.schema_version == 1
    assert controls.query_delimiter_present is False
    assert controls.query_parameters == ()
    assert controls.requested_media_type.root == "application/json"
    assert controls.api_version is None


@pytest.mark.parametrize(
    "field",
    (
        "query_delimiter_present",
        "query_parameters",
        "requested_media_type",
        "api_version",
    ),
)
def test_request_controls_require_each_explicit_component_field(field: str) -> None:
    data = _controls_data()
    del data[field]
    with pytest.raises(ValidationError) as error:
        RetrievalRequestControls.model_validate(data)
    assert error.value.errors()[0]["type"] == "missing"


@pytest.mark.parametrize("value", (0, 1, "true", "false", None))
def test_request_controls_query_delimiter_presence_requires_exact_bool(
    value: object,
) -> None:
    with pytest.raises(ValidationError):
        _controls(query_delimiter_present=value)

    semantic = _controls().model_dump(mode="json")
    semantic["query_delimiter_present"] = value
    with pytest.raises(ValidationError):
        RetrievalRequestControls.model_validate_json(json.dumps(semantic))


def test_request_controls_reject_parameters_without_query_delimiter() -> None:
    with pytest.raises(
        ValidationError,
        match="require query_delimiter_present to be true",
    ):
        _controls(
            query_delimiter_present=False,
            query_parameters=(_query("flag", "", value_delimiter_present=False),),
        )

    semantic = _controls(
        query_delimiter_present=True,
        query_parameters=(_query("flag", "", value_delimiter_present=False),),
    ).model_dump(mode="json")
    semantic["query_delimiter_present"] = False
    with pytest.raises(
        ValidationError,
        match="require query_delimiter_present to be true",
    ):
        RetrievalRequestControls.model_validate_json(json.dumps(semantic))


def test_query_target_states_are_distinct_replayable_and_json_stable() -> None:
    states = (
        _controls(query_delimiter_present=False, query_parameters=()),
        _controls(query_delimiter_present=True, query_parameters=()),
        _controls(
            query_delimiter_present=True,
            query_parameters=(_query("flag", "", value_delimiter_present=False),),
        ),
        _controls(
            query_delimiter_present=True,
            query_parameters=(_query("flag", "", value_delimiter_present=True),),
        ),
        _controls(
            query_delimiter_present=True,
            query_parameters=(_query("flag", "value"),),
        ),
    )
    expected_targets = (
        "/path",
        "/path?",
        "/path?flag",
        "/path?flag=",
        "/path?flag=value",
    )

    assert all(
        left != right
        for index, left in enumerate(states)
        for right in states[index + 1 :]
    )
    assert tuple(_replay_request_target("/path", state) for state in states) == (
        expected_targets
    )
    for state in states:
        reconstructed = RetrievalRequestControls.model_validate_json(
            state.model_dump_json()
        )
        assert reconstructed == state
        assert _replay_request_target("/path", reconstructed) == (
            _replay_request_target("/path", state)
        )


def test_request_controls_support_requested_json_diff_and_optional_api_version() -> (
    None
):
    json_controls = _controls(
        requested_media_type=MediaType.model_validate("application/json"),
        api_version=ApiVersion.model_validate("2026-03-10"),
    )
    diff_controls = _controls(
        requested_media_type=MediaType.model_validate("application/vnd.github.diff"),
        api_version=None,
    )
    assert json_controls.requested_media_type is not None
    assert json_controls.requested_media_type.root == "application/json"
    assert json_controls.api_version is not None
    assert json_controls.api_version.root == "2026-03-10"
    assert diff_controls.requested_media_type is not None
    assert diff_controls.requested_media_type.root == "application/vnd.github.diff"
    assert diff_controls.api_version is None


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("query_parameters", []),
        ("query_parameters", {"page": "1"}),
        (
            "query_parameters",
            (
                {
                    "name": "page",
                    "value": "1",
                    "value_delimiter_present": True,
                },
            ),
        ),
        ("requested_media_type", "application/json"),
        ("requested_media_type", None),
        ("api_version", "2026-03-10"),
    ),
)
def test_request_controls_require_typed_nested_python_values(
    field: str,
    value: object,
) -> None:
    with pytest.raises(ValidationError):
        _controls(**{field: value})


def test_request_controls_reject_mapping_query_coercion() -> None:
    with pytest.raises(ValidationError):
        _controls(query_parameters={"page": "1", "page_size": "100"})


def test_request_controls_semantic_json_reconstructs_typed_ordered_tuple() -> None:
    controls = _controls(
        query_delimiter_present=True,
        query_parameters=(
            _query("page", "1"),
            _query("flag", "", value_delimiter_present=False),
            _query("flag", "", value_delimiter_present=True),
            _query("page", "2"),
        ),
        requested_media_type=MediaType.model_validate("application/json"),
        api_version=ApiVersion.model_validate("v1"),
    )
    reconstructed = RetrievalRequestControls.model_validate_json(
        controls.model_dump_json()
    )
    assert reconstructed == controls
    assert type(reconstructed.query_parameters) is tuple
    assert all(
        isinstance(parameter, RequestQueryParameter)
        for parameter in reconstructed.query_parameters
    )
    _assert_query_order_and_multiplicity(
        reconstructed,
        (
            ("page", "1", True),
            ("flag", "", False),
            ("flag", "", True),
            ("page", "2", True),
        ),
    )


@pytest.mark.parametrize("count", (0, 1, 128))
def test_query_parameter_cardinality_accepts_exact_python_and_json_bounds(
    count: int,
) -> None:
    parameters = tuple(
        _query(f"q{index % 7}", f"v{index % 11}") for index in range(count)
    )
    controls = _controls(
        query_delimiter_present=True,
        query_parameters=parameters,
    )
    reconstructed = RetrievalRequestControls.model_validate_json(
        controls.model_dump_json()
    )
    expected = tuple(
        (parameter.name, parameter.value, parameter.value_delimiter_present)
        for parameter in parameters
    )

    assert controls.query_parameters == parameters
    assert reconstructed.query_parameters == parameters
    assert len(reconstructed.query_parameters) == count
    assert (
        tuple(
            (
                parameter.name,
                parameter.value,
                parameter.value_delimiter_present,
            )
            for parameter in reconstructed.query_parameters
        )
        == expected
    )
    if count == 128:
        assert len(set(expected)) < len(expected)
        assert _replay_query(reconstructed.query_parameters) == _replay_query(
            parameters
        )


def test_query_parameter_cardinality_rejects_max_plus_one_before_nested_items() -> None:
    valid_parameters = tuple(_query("duplicate", "value") for _ in range(129))
    with pytest.raises(ValidationError) as python_valid_error:
        _controls(
            query_delimiter_present=True,
            query_parameters=valid_parameters,
        )
    _assert_collection_limit_error(
        python_valid_error,
        field="query_parameters",
        maximum=128,
    )

    semantic: dict[str, object] = {
        "schema_version": 1,
        "query_delimiter_present": True,
        "query_parameters": [
            {"name": "duplicate", "value": "value", "value_delimiter_present": True}
        ]
        * 129,
        "requested_media_type": "application/json",
        "api_version": None,
    }
    with pytest.raises(ValidationError) as json_valid_error:
        RetrievalRequestControls.model_validate_json(json.dumps(semantic))
    _assert_collection_limit_error(
        json_valid_error,
        field="query_parameters",
        maximum=128,
    )

    with pytest.raises(ValidationError) as python_nested_error:
        _controls(
            query_delimiter_present=True,
            query_parameters=(object(),) * 129,
        )
    _assert_collection_limit_error(
        python_nested_error,
        field="query_parameters",
        maximum=128,
    )

    semantic["query_parameters"] = [{"name": "raw space"}] * 129
    with pytest.raises(ValidationError) as json_nested_error:
        RetrievalRequestControls.model_validate_json(json.dumps(semantic))
    _assert_collection_limit_error(
        json_nested_error,
        field="query_parameters",
        maximum=128,
    )


@pytest.mark.parametrize(
    "extra_field",
    (
        "request_id",
        "authority",
        "method",
        "route_path",
        "started_at",
        "headers",
        "authorization",
        "cookies",
        "user_agent",
        "timeout",
        "redirect_policy",
        "retry_policy",
        "graphql_operation_name",
        "graphql_variables",
        "request_body",
        "content_type",
        "response",
    ),
)
def test_request_controls_reject_identity_transport_body_and_later_fields(
    extra_field: str,
) -> None:
    data = _controls_data()
    data[extra_field] = "forbidden"
    with pytest.raises(ValidationError) as error:
        RetrievalRequestControls.model_validate(data)
    assert error.value.errors()[0]["type"] == "extra_forbidden"


def test_request_controls_are_frozen_and_require_exact_schema_version() -> None:
    controls = _controls()
    with pytest.raises(ValidationError):
        controls.query_delimiter_present = True
    with pytest.raises(ValidationError):
        controls.query_parameters = (_query("changed", "1"),)
    for value in (0, 2, True, 1.0, "1"):
        with pytest.raises(ValidationError):
            _controls(schema_version=value)


@pytest.mark.parametrize(
    ("name", "value", "value_delimiter_present"),
    (
        ("raw&name", "value", True),
        ("name", "raw=value", True),
        ("name", "%GG", True),
        ("n" * 257, "value", True),
        ("name", "v" * 4097, True),
        ("flag", "value", False),
    ),
)
def test_request_controls_revalidate_constructed_invalid_query_parameters(
    name: str,
    value: str,
    value_delimiter_present: bool,
) -> None:
    invalid_parameter = RequestQueryParameter.model_construct(
        name=name,
        value=value,
        value_delimiter_present=value_delimiter_present,
    )
    with pytest.raises(ValidationError):
        RequestQueryParameter.model_validate(invalid_parameter)
    with pytest.raises(ValidationError):
        _controls(
            query_delimiter_present=True,
            query_parameters=(invalid_parameter,),
        )


def test_response_state_vocabulary_is_exact_and_distinct_from_source_lifecycle() -> (
    None
):
    assert tuple(ResponseRepresentationState) == (
        ResponseRepresentationState.OBSERVED,
        ResponseRepresentationState.UNAVAILABLE,
        ResponseRepresentationState.INACCESSIBLE,
        ResponseRepresentationState.UNKNOWN,
    )
    assert [state.value for state in ResponseRepresentationState] == [
        "observed",
        "unavailable",
        "inaccessible",
        "unknown",
    ]
    assert ResponseRepresentationState is not SourceIdentityLifecycleState
    assert "deleted" not in {state.value for state in ResponseRepresentationState}
    with pytest.raises(ValidationError):
        _unobserved(
            cast(ResponseRepresentationState, SourceIdentityLifecycleState.UNKNOWN)
        )


def test_response_state_json_is_semantic_and_python_input_is_typed() -> None:
    adapter = TypeAdapter(ResponseRepresentationState)
    assert adapter.dump_json(ResponseRepresentationState.OBSERVED) == b'"observed"'
    assert adapter.validate_json(b'"unknown"') is ResponseRepresentationState.UNKNOWN
    with pytest.raises(ValidationError):
        _observation(state="observed")


@pytest.mark.parametrize("value", (100, 200, 599))
def test_http_status_code_accepts_exact_bounds(value: int) -> None:
    assert HttpStatusCode.model_validate(value).root == value


@pytest.mark.parametrize(
    "value",
    (99, 600, 0, -1, True, False, 200.0, "200", b"200", None),
)
def test_http_status_code_rejects_out_of_range_or_coercive_values(
    value: object,
) -> None:
    with pytest.raises(ValidationError):
        HttpStatusCode.model_validate(value)


@pytest.mark.parametrize(
    "value",
    ("gzip", "GZip", "br", "BR", "identity", "Identity", "x-custom", "a" * 64),
)
def test_content_encoding_accepts_and_preserves_exact_http_tokens(value: str) -> None:
    assert ContentEncoding.model_validate(value).root == value


@pytest.mark.parametrize(
    "value",
    (
        "",
        "g zip",
        " gzip",
        "gzip ",
        "gzip, br",
        "gzip/br",
        "gzip\n",
        "bré",
        "a" * 65,
        1,
        b"gzip",
        None,
    ),
)
def test_content_encoding_rejects_malformed_or_coercive_values(
    value: object,
) -> None:
    with pytest.raises(ValidationError):
        ContentEncoding.model_validate(value)


def test_content_encoding_chain_preserves_none_empty_order_and_multiplicity() -> None:
    gzip = _encoding("gzip")
    br = _encoding("br")
    unavailable = _observation(content_encodings=None)
    empty = _observation(content_encodings=())
    one = _observation(content_encodings=(gzip,))
    forward = _observation(content_encodings=(gzip, br))
    reverse = _observation(content_encodings=(br, gzip))
    duplicate = _observation(content_encodings=(gzip, br, gzip))

    assert unavailable.content_encodings is None
    assert empty.content_encodings == ()
    assert unavailable != empty
    assert one.content_encodings == (gzip,)
    assert forward.content_encodings == (gzip, br)
    assert reverse.content_encodings == (br, gzip)
    assert forward != reverse
    assert duplicate.content_encodings == (gzip, br, gzip)


def test_content_encoding_chain_semantic_json_reconstructs_exact_typed_tuple() -> None:
    observation = _observation(
        content_encodings=(_encoding("gzip"), _encoding("br"), _encoding("gzip"))
    )
    semantic = observation.model_dump(mode="json")
    assert semantic["content_encodings"] == ["gzip", "br", "gzip"]

    reconstructed = ResponseRepresentationObservation.model_validate_json(
        observation.model_dump_json()
    )
    assert reconstructed == observation
    assert type(reconstructed.content_encodings) is tuple
    assert reconstructed.content_encodings is not None
    assert all(
        isinstance(encoding, ContentEncoding)
        for encoding in reconstructed.content_encodings
    )
    assert tuple(encoding.root for encoding in reconstructed.content_encodings) == (
        "gzip",
        "br",
        "gzip",
    )


@pytest.mark.parametrize("count", (0, 1, 32))
def test_content_encoding_cardinality_accepts_exact_python_and_json_bounds(
    count: int,
) -> None:
    lexemes = ("GZip", "BR", "Identity", "GZip")
    encodings = tuple(
        _encoding(lexemes[index % len(lexemes)]) for index in range(count)
    )
    observation = _observation(content_encodings=encodings)
    reconstructed = ResponseRepresentationObservation.model_validate_json(
        observation.model_dump_json()
    )
    expected = tuple(encoding.root for encoding in encodings)

    assert observation.content_encodings == encodings
    assert reconstructed.content_encodings == encodings
    assert reconstructed.content_encodings is not None
    assert len(reconstructed.content_encodings) == count
    assert tuple(encoding.root for encoding in reconstructed.content_encodings) == (
        expected
    )
    if count == 32:
        assert len(set(expected)) < len(expected)


def test_content_encoding_cardinality_rejects_max_plus_one_before_nested_items() -> (
    None
):
    encodings = tuple(_encoding("GZip") for _ in range(33))
    with pytest.raises(ValidationError) as python_valid_error:
        _observation(content_encodings=encodings)
    _assert_collection_limit_error(
        python_valid_error,
        field="content_encodings",
        maximum=32,
    )

    semantic = _observation(content_encodings=None).model_dump(mode="json")
    semantic["content_encodings"] = ["GZip"] * 33
    with pytest.raises(ValidationError) as json_valid_error:
        ResponseRepresentationObservation.model_validate_json(json.dumps(semantic))
    _assert_collection_limit_error(
        json_valid_error,
        field="content_encodings",
        maximum=32,
    )

    with pytest.raises(ValidationError) as python_nested_error:
        _observation(content_encodings=(object(),) * 33)
    _assert_collection_limit_error(
        python_nested_error,
        field="content_encodings",
        maximum=32,
    )

    semantic["content_encodings"] = ["gzip, br"] * 33
    with pytest.raises(ValidationError) as json_nested_error:
        ResponseRepresentationObservation.model_validate_json(json.dumps(semantic))
    _assert_collection_limit_error(
        json_nested_error,
        field="content_encodings",
        maximum=32,
    )


@pytest.mark.parametrize(
    "value",
    (
        [_encoding("gzip"), _encoding("br")],
        ("gzip", "br"),
        "gzip, br",
        _encoding("gzip"),
    ),
)
def test_content_encoding_chain_requires_exact_typed_python_tuple(
    value: object,
) -> None:
    with pytest.raises(ValidationError):
        _observation(content_encodings=value)


def test_content_encoding_chain_and_tokens_are_frozen_and_reject_stale_field() -> None:
    observation = _observation(content_encodings=(_encoding("gzip"),))
    assert observation.content_encodings is not None
    with pytest.raises(ValidationError):
        observation.content_encodings[0].root = "br"
    with pytest.raises(ValidationError):
        observation.content_encodings = ()
    with pytest.raises(ValidationError) as error:
        _observation(content_encoding=_encoding("gzip"))
    assert error.value.errors()[0]["type"] == "extra_forbidden"


def test_media_type_parameters_preserve_order_multiplicity_and_exact_values() -> None:
    parameters = (
        _parameter("charset", "utf-8"),
        _parameter("charset", "UTF-8"),
        _parameter("title", "café"),
        _parameter("filename*", ""),
    )
    observation = _observation(
        observed_media_type=MediaType.model_validate("text/plain"),
        media_type_parameters=parameters,
    )
    assert observation.media_type_parameters == parameters
    assert tuple((item.name, item.value) for item in parameters) == (
        ("charset", "utf-8"),
        ("charset", "UTF-8"),
        ("title", "café"),
        ("filename*", ""),
    )


@pytest.mark.parametrize(
    "name",
    ("", "char set", "char/set", "charset\n", "chársét", 1, None),
)
def test_media_type_parameter_rejects_malformed_names(name: object) -> None:
    with pytest.raises(ValidationError):
        MediaTypeParameter.model_validate({"name": name, "value": "utf-8"})


@pytest.mark.parametrize("name", ("charset", "Charset", "CHARSET", "filename*"))
def test_media_type_parameter_name_preserves_valid_case_and_punctuation(
    name: str,
) -> None:
    parameter = _parameter(name, "UTF-8")
    assert parameter.name == name
    assert MediaTypeParameter.model_validate_json(parameter.model_dump_json()) == (
        parameter
    )


def test_media_type_parameter_name_bounds_and_json_lexeme_are_exact() -> None:
    minimum = _parameter("a", "value")
    maximum = _parameter("a" * 256, "value")
    assert minimum.name == "a"
    assert len(maximum.name) == 256
    assert MediaTypeParameter.model_validate_json(maximum.model_dump_json()) == maximum
    assert json.loads(maximum.model_dump_json())["name"] == "a" * 256
    with pytest.raises(ValidationError):
        _parameter("a" * 257, "value")


@pytest.mark.parametrize("control", (*map(chr, range(32)), chr(127)))
def test_media_type_parameter_values_reject_ascii_controls(control: str) -> None:
    with pytest.raises(ValidationError):
        _parameter("charset", f"utf{control}8")


def test_media_type_parameter_value_bound_and_extra_rejection_are_exact() -> None:
    assert len(_parameter("name", "v" * 1024).value) == 1024
    with pytest.raises(ValidationError):
        _parameter("name", "v" * 1025)
    with pytest.raises(ValidationError):
        MediaTypeParameter.model_validate(
            {"name": "charset", "value": "utf-8", "normalized": "utf-8"}
        )
    with pytest.raises(ValidationError):
        MediaTypeParameter.model_validate({"name": "charset", "value": 8})


def test_media_type_parameter_is_frozen() -> None:
    parameter = _parameter("charset", "utf-8")
    with pytest.raises(ValidationError):
        parameter.value = "changed"


@pytest.mark.parametrize("count", (0, 1, 64))
def test_media_parameter_cardinality_accepts_exact_python_and_json_bounds(
    count: int,
) -> None:
    names = ("Charset", "filename*", "X-Value", "Charset")
    parameters = tuple(
        _parameter(names[index % len(names)], f"value-{index % 9}")
        for index in range(count)
    )
    observation = _observation(media_type_parameters=parameters)
    reconstructed = ResponseRepresentationObservation.model_validate_json(
        observation.model_dump_json()
    )
    expected = tuple((parameter.name, parameter.value) for parameter in parameters)

    assert observation.media_type_parameters == parameters
    assert reconstructed.media_type_parameters == parameters
    assert reconstructed.media_type_parameters is not None
    assert len(reconstructed.media_type_parameters) == count
    assert (
        tuple(
            (parameter.name, parameter.value)
            for parameter in reconstructed.media_type_parameters
        )
        == expected
    )
    if count == 64:
        assert len(set(expected)) < len(expected)


def test_media_parameter_cardinality_rejects_max_plus_one_before_nested_items() -> None:
    parameters = tuple(_parameter("Charset", "UTF-8") for _ in range(65))
    with pytest.raises(ValidationError) as python_valid_error:
        _observation(media_type_parameters=parameters)
    _assert_collection_limit_error(
        python_valid_error,
        field="media_type_parameters",
        maximum=64,
    )

    semantic = _observation(media_type_parameters=None).model_dump(mode="json")
    semantic["media_type_parameters"] = [{"name": "Charset", "value": "UTF-8"}] * 65
    with pytest.raises(ValidationError) as json_valid_error:
        ResponseRepresentationObservation.model_validate_json(json.dumps(semantic))
    _assert_collection_limit_error(
        json_valid_error,
        field="media_type_parameters",
        maximum=64,
    )

    with pytest.raises(ValidationError) as python_nested_error:
        _observation(media_type_parameters=(object(),) * 65)
    _assert_collection_limit_error(
        python_nested_error,
        field="media_type_parameters",
        maximum=64,
    )

    semantic["media_type_parameters"] = [{"name": "raw space"}] * 65
    with pytest.raises(ValidationError) as json_nested_error:
        ResponseRepresentationObservation.model_validate_json(json.dumps(semantic))
    _assert_collection_limit_error(
        json_nested_error,
        field="media_type_parameters",
        maximum=64,
    )


def test_response_observation_fields_are_exact() -> None:
    assert set(ResponseRepresentationObservation.model_fields) == {
        "schema_version",
        "request_id",
        "state",
        "completed_at",
        "status_code",
        "observed_media_type",
        "media_type_parameters",
        "content_encodings",
    }


@pytest.mark.parametrize(
    "field",
    (
        "request_id",
        "state",
        "completed_at",
        "status_code",
        "observed_media_type",
        "media_type_parameters",
        "content_encodings",
    ),
)
def test_response_observation_requires_each_explicit_component_field(
    field: str,
) -> None:
    data = _observation_data()
    del data[field]
    with pytest.raises(ValidationError) as error:
        ResponseRepresentationObservation.model_validate(data)
    assert error.value.errors()[0]["type"] == "missing"


def test_observed_json_text_parameter_and_encoding_chain_responses_are_valid() -> None:
    json_response = _observation()
    text_response = _observation(
        observed_media_type=MediaType.model_validate("text/plain"),
        media_type_parameters=(_parameter("charset", "utf-8"),),
    )
    encoded_response = _observation(content_encodings=(_encoding("gzip"),))
    assert json_response.status_code is not None
    assert json_response.status_code.root == 200
    assert text_response.media_type_parameters is not None
    assert text_response.media_type_parameters[0].value == "utf-8"
    assert encoded_response.content_encodings is not None
    assert encoded_response.content_encodings[0].root == "gzip"


@pytest.mark.parametrize(
    ("state", "status_code"),
    (
        (ResponseRepresentationState.UNAVAILABLE, 204),
        (ResponseRepresentationState.INACCESSIBLE, 403),
    ),
)
def test_non_observed_representation_preserves_known_status(
    state: ResponseRepresentationState,
    status_code: int,
) -> None:
    observation = _observation(
        state=state,
        status_code=HttpStatusCode.model_validate(status_code),
        observed_media_type=None,
        media_type_parameters=None,
        content_encodings=None,
    )
    assert observation.state is state
    assert observation.status_code == HttpStatusCode.model_validate(status_code)
    assert observation.observed_media_type is None
    assert observation.media_type_parameters is None
    assert observation.content_encodings is None


@pytest.mark.parametrize(
    "state",
    tuple(ResponseRepresentationState),
)
def test_status_and_other_bounded_metadata_may_be_absent_under_every_state(
    state: ResponseRepresentationState,
) -> None:
    observation = _observation(
        state=state,
        status_code=None,
        observed_media_type=None,
        media_type_parameters=None,
        content_encodings=None,
    )
    assert observation.state is state
    assert observation.status_code is None
    assert observation.observed_media_type is None
    assert observation.media_type_parameters is None
    assert observation.content_encodings is None


@pytest.mark.parametrize("state", tuple(ResponseRepresentationState))
def test_metadata_presence_never_changes_or_infers_explicit_state(
    state: ResponseRepresentationState,
) -> None:
    encodings = (_encoding("gzip"), _encoding("br"))
    observation = _observation(
        state=state,
        status_code=HttpStatusCode.model_validate(206),
        observed_media_type=MediaType.model_validate("text/plain"),
        media_type_parameters=(_parameter("charset", "utf-8"),),
        content_encodings=encodings,
    )
    assert observation.state is state
    assert observation.status_code == HttpStatusCode.model_validate(206)
    assert observation.observed_media_type == MediaType.model_validate("text/plain")
    assert observation.media_type_parameters == (_parameter("charset", "utf-8"),)
    assert observation.content_encodings == encodings


@pytest.mark.parametrize(
    "parameters",
    ((), (_parameter("charset", "utf-8"),)),
)
@pytest.mark.parametrize("state", tuple(ResponseRepresentationState))
def test_media_parameters_without_media_type_fail_for_every_state(
    state: ResponseRepresentationState,
    parameters: tuple[MediaTypeParameter, ...],
) -> None:
    with pytest.raises(ValidationError, match="require observed_media_type"):
        _observation(
            state=state,
            observed_media_type=None,
            media_type_parameters=parameters,
        )


@pytest.mark.parametrize("state", tuple(ResponseRepresentationState))
def test_media_type_with_empty_parameters_succeeds_for_every_state(
    state: ResponseRepresentationState,
) -> None:
    media_type = MediaType.model_validate("application/json")
    observation = _observation(
        state=state,
        observed_media_type=media_type,
        media_type_parameters=(),
    )
    assert observation.state is state
    assert observation.observed_media_type == media_type
    assert observation.media_type_parameters == ()


@pytest.mark.parametrize("state", tuple(ResponseRepresentationState))
def test_media_type_with_unknown_parameters_succeeds_for_every_state(
    state: ResponseRepresentationState,
) -> None:
    media_type = MediaType.model_validate("application/json")
    observation = _observation(
        state=state,
        status_code=None,
        observed_media_type=media_type,
        media_type_parameters=None,
        content_encodings=(_encoding("gzip"),),
    )
    assert observation.state is state
    assert observation.status_code is None
    assert observation.observed_media_type == media_type
    assert observation.media_type_parameters is None
    assert observation.content_encodings == (_encoding("gzip"),)


def test_unknown_and_known_empty_media_parameters_are_distinct() -> None:
    media_type = MediaType.model_validate("application/json")
    unknown = _observation(
        observed_media_type=media_type,
        media_type_parameters=None,
    )
    known_empty = _observation(
        observed_media_type=media_type,
        media_type_parameters=(),
    )
    assert unknown.media_type_parameters is None
    assert known_empty.media_type_parameters == ()
    assert unknown != known_empty
    assert unknown.model_dump(mode="json")["media_type_parameters"] is None
    assert known_empty.model_dump(mode="json")["media_type_parameters"] == []
    reconstructed_unknown = ResponseRepresentationObservation.model_validate_json(
        unknown.model_dump_json()
    )
    reconstructed_empty = ResponseRepresentationObservation.model_validate_json(
        known_empty.model_dump_json()
    )
    assert reconstructed_unknown.media_type_parameters is None
    assert reconstructed_empty.media_type_parameters == ()


def test_same_request_id_can_have_two_distinct_observation_values() -> None:
    request_id = _request_id()
    first = _observation(
        request_id=request_id,
        state=ResponseRepresentationState.UNAVAILABLE,
        status_code=HttpStatusCode.model_validate(204),
        observed_media_type=None,
        media_type_parameters=None,
        content_encodings=None,
    )
    second = _observation(
        request_id=request_id,
        state=ResponseRepresentationState.INACCESSIBLE,
        completed_at=SYNTHETIC_COMPLETED_AT + timedelta(seconds=1),
        status_code=HttpStatusCode.model_validate(403),
        observed_media_type=MediaType.model_validate("text/plain"),
        media_type_parameters=(_parameter("charset", "utf-8"),),
        content_encodings=(_encoding("br"),),
    )
    assert first.request_id == second.request_id
    assert first.state is ResponseRepresentationState.UNAVAILABLE
    assert second.state is ResponseRepresentationState.INACCESSIBLE
    assert first != second


def test_requested_and_observed_media_may_disagree_without_reconciliation() -> None:
    controls = _controls(
        requested_media_type=MediaType.model_validate("application/vnd.github.raw+json")
    )
    observation = _observation(
        observed_media_type=MediaType.model_validate("text/plain"),
        media_type_parameters=(_parameter("charset", "utf-8"),),
    )
    _assert_media_mismatch(controls, observation)
    with pytest.raises(AssertionError):
        _assert_media_mismatch(
            controls,
            _observation(
                observed_media_type=MediaType.model_validate(
                    "application/vnd.github.raw+json"
                )
            ),
        )


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("request_id", {"schema_version": 1}),
        ("state", "observed"),
        ("completed_at", "2026-08-02T16:00:01Z"),
        ("status_code", 200),
        ("observed_media_type", "application/json"),
        ("media_type_parameters", []),
        (
            "media_type_parameters",
            ({"name": "charset", "value": "utf-8"},),
        ),
        ("content_encodings", ("gzip",)),
    ),
)
def test_response_observation_requires_typed_nested_python_values(
    field: str,
    value: object,
) -> None:
    with pytest.raises(ValidationError):
        _observation(**{field: value})


def test_response_observation_semantic_json_reconstructs_nested_types() -> None:
    observation = _observation(
        observed_media_type=MediaType.model_validate("text/plain"),
        media_type_parameters=(
            _parameter("charset", "utf-8"),
            _parameter("charset", "UTF-8"),
        ),
        content_encodings=(_encoding("gzip"), _encoding("br")),
    )
    reconstructed = ResponseRepresentationObservation.model_validate_json(
        observation.model_dump_json()
    )
    assert reconstructed == observation
    assert isinstance(reconstructed.request_id, RetrievalRequestId)
    assert isinstance(reconstructed.status_code, HttpStatusCode)
    assert isinstance(reconstructed.observed_media_type, MediaType)
    assert type(reconstructed.media_type_parameters) is tuple
    assert tuple(
        (parameter.name, parameter.value)
        for parameter in reconstructed.media_type_parameters
    ) == (("charset", "utf-8"), ("charset", "UTF-8"))
    assert type(reconstructed.content_encodings) is tuple
    assert reconstructed.content_encodings is not None
    assert all(
        isinstance(encoding, ContentEncoding)
        for encoding in reconstructed.content_encodings
    )


def test_response_observation_json_accepts_semantic_unavailable_shape() -> None:
    value: dict[str, object] = {
        "schema_version": 1,
        "request_id": _request_id().model_dump(mode="json"),
        "state": "unavailable",
        "completed_at": "2026-08-02T16:00:01Z",
        "status_code": 204,
        "observed_media_type": None,
        "media_type_parameters": None,
        "content_encodings": None,
    }
    observation = ResponseRepresentationObservation.model_validate_json(
        json.dumps(value)
    )
    assert observation.state is ResponseRepresentationState.UNAVAILABLE
    assert observation.status_code == HttpStatusCode.model_validate(204)
    assert observation.media_type_parameters is None
    assert observation.completed_at.tzinfo is UTC


def test_response_completion_rejects_naive_and_nonzero_python_times() -> None:
    with pytest.raises(ValidationError):
        _observation(completed_at=SYNTHETIC_COMPLETED_AT.replace(tzinfo=None))
    with pytest.raises(ValidationError):
        _observation(
            completed_at=SYNTHETIC_COMPLETED_AT.astimezone(timezone(timedelta(hours=1)))
        )


def test_response_completion_normalizes_effective_zero_offset_to_utc() -> None:
    zero = timezone(timedelta(0), name="zero-offset")
    completed_at = datetime(2026, 8, 2, 16, 0, 1, 123456, tzinfo=zero)
    observation = _observation(completed_at=completed_at)
    assert observation.completed_at.tzinfo is UTC
    assert observation.model_dump(mode="json")["completed_at"] == (
        "2026-08-02T16:00:01.123456Z"
    )


@pytest.mark.parametrize(
    "completed_at",
    (
        "2026-08-02T16:00:01-0000",
        "2026-08-02T16:00:01-00",
        "2026-08-02T16:00:01-00:00",
        "2026-08-02T16:00:01-00:00:00",
        "2026-08-02T16:00:01+0000",
        "2026-08-02T16:00:01+00",
        "2026-08-02T16:00:01+01:00",
        "2026-08-02T16:00:01-01:00",
        "2026-08-02T16:00:01.1234567Z",
        "2026-08-02 16:00:01Z",
        "2026-08-02T16:00:01",
    ),
)
def test_response_completion_json_rejects_negative_zero_and_other_grammar(
    completed_at: str,
) -> None:
    data = _observation().model_dump(mode="json")
    data["completed_at"] = completed_at
    with pytest.raises(ValidationError):
        ResponseRepresentationObservation.model_validate_json(json.dumps(data))


@pytest.mark.parametrize("suffix", ("Z", "+00:00"))
@pytest.mark.parametrize(
    ("fraction", "microsecond"),
    (("", 0), (".1", 100_000), (".123456", 123_456)),
)
def test_response_completion_json_accepts_asserted_utc_grammar(
    suffix: str,
    fraction: str,
    microsecond: int,
) -> None:
    data = _observation().model_dump(mode="json")
    data["completed_at"] = f"2026-08-02T16:00:01{fraction}{suffix}"
    observation = ResponseRepresentationObservation.model_validate_json(
        json.dumps(data)
    )
    assert observation.completed_at == datetime(
        2026, 8, 2, 16, 0, 1, microsecond, tzinfo=UTC
    )


@pytest.mark.parametrize(
    "wrong_identity",
    (
        GitTreeIdentity(
            kind=GitObjectKind.TREE,
            algorithm=GitHashAlgorithm.SHA1,
            full_digest="a" * 40,
        ),
        GitBlobIdentity(
            kind=GitObjectKind.BLOB,
            algorithm=GitHashAlgorithm.SHA1,
            full_digest="b" * 40,
        ),
        RepositoryIdentity(
            provider=ProviderKey.model_validate("github"),
            provider_repository_id=ProviderRepositoryId.model_validate("37489525"),
        ),
    ),
)
def test_response_observation_rejects_tree_blob_and_source_identity_as_request_id(
    wrong_identity: object,
) -> None:
    with pytest.raises(ValidationError):
        _observation(request_id=wrong_identity)


@pytest.mark.parametrize(
    "extra_field",
    (
        "response_id",
        "acquisition_run_id",
        "request_ordinal",
        "method",
        "route_path",
        "authority",
        "started_at",
        "headers",
        "etag",
        "provider_request_id",
        "content_encoding",
        "body",
        "payload_text",
        "body_bytes",
        "body_length",
        "digest",
        "sha256",
        "retained_path",
        "retained_artifact",
        "truncated",
        "redacted",
    ),
)
def test_response_observation_rejects_duplicated_provenance_headers_and_bytes(
    extra_field: str,
) -> None:
    data = _observation_data()
    data[extra_field] = "forbidden"
    with pytest.raises(ValidationError) as error:
        ResponseRepresentationObservation.model_validate(data)
    assert error.value.errors()[0]["type"] == "extra_forbidden"


def test_response_observation_is_frozen_extra_forbidden_and_schema_strict() -> None:
    observation = _observation()
    with pytest.raises(ValidationError):
        observation.state = ResponseRepresentationState.UNKNOWN
    with pytest.raises(ValidationError):
        _observation(unexpected="value")
    for value in (0, 2, True, 1.0, "1"):
        with pytest.raises(ValidationError):
            _observation(schema_version=value)


def test_response_observation_revalidates_constructed_invalid_nested_values() -> None:
    invalid_status = HttpStatusCode.model_construct(root=99)
    invalid_media = MediaType.model_construct(root="application/json;bad")
    invalid_parameter = MediaTypeParameter.model_construct(
        name="bad name",
        value="utf-8",
    )
    invalid_overlong_parameter = MediaTypeParameter.model_construct(
        name="a" * 257,
        value="utf-8",
    )
    invalid_encoding = ContentEncoding.model_construct(root="gzip, br")
    for field, value in (
        ("status_code", invalid_status),
        ("observed_media_type", invalid_media),
        ("media_type_parameters", (invalid_parameter,)),
        ("media_type_parameters", (invalid_overlong_parameter,)),
        ("content_encodings", (invalid_encoding,)),
    ):
        with pytest.raises(ValidationError):
            _observation(**{field: value})


@pytest.mark.parametrize(
    "parameters",
    ((), (_parameter("charset", "utf-8"),)),
)
def test_response_observation_revalidates_constructed_invalid_media_knowledge(
    parameters: tuple[MediaTypeParameter, ...],
) -> None:
    invalid = ResponseRepresentationObservation.model_construct(
        schema_version=1,
        request_id=_request_id(),
        state=ResponseRepresentationState.OBSERVED,
        completed_at=SYNTHETIC_COMPLETED_AT,
        status_code=HttpStatusCode.model_validate(200),
        observed_media_type=None,
        media_type_parameters=parameters,
        content_encodings=None,
    )
    with pytest.raises(ValidationError, match="require observed_media_type"):
        ResponseRepresentationObservation.model_validate(invalid)


def test_cross_layer_composition_uses_one_request_id_without_duplication() -> None:
    request_id = _request_id()
    reference = _reference(request_id)
    controls = _controls(
        query_delimiter_present=True,
        query_parameters=(_query("page", "1"),),
        requested_media_type=MediaType.model_validate("application/json"),
        api_version=ApiVersion.model_validate("v1"),
    )
    observation = _observation(request_id=request_id)
    composed = (request_id, reference, controls, observation)

    assert composed[1].request_id == composed[0]
    assert composed[3].request_id == composed[0]
    assert "request_id" not in RetrievalRequestControls.model_fields
    assert "authority" not in ResponseRepresentationObservation.model_fields
    assert "method" not in ResponseRepresentationObservation.model_fields
    assert "route_path" not in ResponseRepresentationObservation.model_fields
    assert "acquisition_run_id" not in (ResponseRepresentationObservation.model_fields)


def test_controls_do_not_change_request_identity() -> None:
    request_id = _request_id()
    first = _controls()
    second = _controls(
        query_delimiter_present=True,
        query_parameters=(_query("page", "1"),),
        requested_media_type=MediaType.model_validate("application/json"),
    )
    assert first != second
    assert request_id == _request_id()
    assert "request_id" not in RetrievalRequestControls.model_fields


def test_representation_observation_is_not_a_retained_artifact() -> None:
    fields = set(ResponseRepresentationObservation.model_fields)
    assert (
        not {
            "body",
            "body_bytes",
            "body_length",
            "digest",
            "digest_scope",
            "completeness",
            "omission",
            "path",
            "publication",
            "publication_provenance",
            "retained_path",
            "retention",
            "sha256",
            "truncated",
            "redacted",
        }
        & fields
    )


def test_evidence_module_exports_are_exact_and_mutation_sensitive() -> None:
    source = EVIDENCE_SOURCE.read_text(encoding="utf-8")
    _validate_evidence_exports(source)
    assert tuple(evidence_module.__all__) == EXPECTED_EVIDENCE_EXPORTS

    missing = source.replace(
        '    "ResponseRepresentationObservation",\n',
        "",
        1,
    )
    unexpected = source.replace(
        '    "ResponseRepresentationObservation",\n',
        '    "ResponseRepresentationObservation",\n    "EvidenceContractCorpus",\n',
        1,
    )
    with pytest.raises(AssertionError):
        _validate_evidence_exports(missing)
    with pytest.raises(AssertionError):
        _validate_evidence_exports(unexpected)


def test_media_parameter_name_limit_is_one_private_annotated_constant() -> None:
    source = EVIDENCE_SOURCE.read_text(encoding="utf-8")
    assert _parse_media_parameter_name_limit(source) == 256
    mutated = source.replace(
        "_MAX_MEDIA_PARAMETER_NAME_LENGTH: int = 256",
        "_MAX_MEDIA_PARAMETER_NAME_LENGTH: int = 257",
        1,
    )
    with pytest.raises(AssertionError):
        assert _parse_media_parameter_name_limit(mutated) == 256


def test_collection_limits_are_exact_private_constants_and_mutation_sensitive() -> None:
    source = EVIDENCE_SOURCE.read_text(encoding="utf-8")
    expected = {
        "_MAX_QUERY_PARAMETERS": 128,
        "_MAX_MEDIA_TYPE_PARAMETERS": 64,
        "_MAX_CONTENT_ENCODINGS": 32,
    }
    assert _parse_collection_limits(source) == expected

    for name, value in expected.items():
        mutated = source.replace(f"{name} = {value}", f"{name} = {value + 1}", 1)
        assert mutated != source
        with pytest.raises(AssertionError):
            assert _parse_collection_limits(mutated) == expected


def test_s07_records_are_present_while_s08_and_later_surfaces_are_absent() -> None:
    source = EVIDENCE_SOURCE.read_text(encoding="utf-8")
    _validate_no_post_s07_evidence_surface(source)
    assert hasattr(evidence_module, "ExactRetainedArtifact")
    assert hasattr(evidence_module, "AcquisitionRun")
    assert hasattr(evidence_module, "EvidenceTransformation")
    assert hasattr(evidence_module, "EvidenceCorrection")
    assert hasattr(evidence_module, "EvidenceSupersession")
    assert hasattr(evidence_module, "EvidenceRecordRelationship")
    for class_name in EXPECTED_EVIDENCE_EXPORTS[39:]:
        assert hasattr(evidence_module, class_name)
    for class_name in (
        "RetainedArtifactRecord",
        "AcquisitionRunRecord",
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
    ):
        with pytest.raises(AssertionError):
            _validate_no_post_s07_evidence_surface(
                source + f"\n\nclass {class_name}:\n    pass\n"
            )
    assert not (REPOSITORY_ROOT / "src/faultatlas/domain/response.py").exists()
    assert not (REPOSITORY_ROOT / "src/faultatlas/domain/artifact.py").exists()
    assert not (REPOSITORY_ROOT / "reference_corpus/contracts/evidence").exists()


def test_evidence_module_imports_and_calls_remain_no_io() -> None:
    source = EVIDENCE_SOURCE.read_text(encoding="utf-8")
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
            names = observed_imports.setdefault(node.module, set())
            for alias in node.names:
                assert alias.asname is None
                names.add(alias.name)
    assert observed_imports == {
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
    forbidden_calls = {
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
            assert node.func.id not in forbidden_calls
    lowered = source.casefold()
    for forbidden in (
        "urllib",
        "pathlib",
        "subprocess",
        "os.environ",
        "decompress",
        "headerparser",
    ):
        assert forbidden not in lowered


def test_package_domain_roots_and_production_inventory_remain_exact() -> None:
    production_files = {
        path.relative_to(REPOSITORY_ROOT).as_posix()
        for path in (REPOSITORY_ROOT / "src").rglob("*.py")
    }
    assert production_files == EXPECTED_PRODUCTION_FILES
    assert len(production_files) == len(EXPECTED_PRODUCTION_FILES)
    assert faultatlas.__all__ == ["__version__"]
    assert getattr(domain_package, "__all__", None) in (None, [])
    assert not any(hasattr(faultatlas, name) for name in EXPECTED_EVIDENCE_EXPORTS)
    assert not any(hasattr(domain_package, name) for name in EXPECTED_EVIDENCE_EXPORTS)


def test_unexpected_extra_production_file_failure_sensitivity() -> None:
    mutated = EXPECTED_PRODUCTION_FILES | {"src/faultatlas/domain/response.py"}
    with pytest.raises(AssertionError):
        assert mutated == EXPECTED_PRODUCTION_FILES


def test_predecessor_models_and_legacy_artifact_snapshot_are_unchanged() -> None:
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
