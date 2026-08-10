"""Strict request, response, artifact, acquisition, and evidence models.

The models in this module identify one request attempt by acquisition-run ID
and run-local ordinal. Retrieval authority, method, origin-relative route, and
request-start time remain explicit provenance metadata rather than identity.
Ordered request controls, response representation metadata, and exact retained
artifact identity are separate immutable values linked through request
identity. Exact artifacts contain digest metadata and byte length but no
payload or storage locator. Terminal acquisition runs preserve ordered request
membership without inferring optional evidence or historical completeness.
Content-addressed durable-record references support explicit transformations,
additive corrections, and separate supersession edges without embedding record
bytes or storage locations. Declared evidence scopes preserve explicit
requirement outcomes and structured omissions, while publication records bind
exact reviewed and published revisions to successful observed checks. This
module also composes typed records in an outer evidence envelope and provides
an explicit, loss-aware in-memory mapping for legacy ArtifactSnapshot values.
It performs no I/O and does not execute transformations or publication checks,
define canonical writers, migration, persistence, or durable envelope bytes.
"""

import json
import re
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Annotated, Literal, Self, cast

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    RootModel,
    StringConstraints,
    ValidationInfo,
    field_validator,
    model_validator,
)

from faultatlas.domain.compatibility import CompatibilityStatus
from faultatlas.domain.identity import (
    AuthorityRole,
    NumberedSourceObjectIdentity,
    ProviderAuthority,
    ProviderGlobalId,
    RepositoryIdentity,
    SourceObjectKind,
)
from faultatlas.domain.revision import GitCommitIdentity, GitTreeIdentity
from faultatlas.domain.source import ArtifactSnapshot

__all__ = [
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
]

_MAX_RUN_ID_LENGTH = 160
_MAX_REQUEST_ORDINAL = 2_147_483_647
_MAX_ROUTE_PATH_LENGTH = 4096
_MAX_MEDIA_TYPE_LENGTH = 255
_MAX_API_VERSION_LENGTH = 128
_MAX_QUERY_NAME_LENGTH = 256
_MAX_QUERY_VALUE_LENGTH = 4096
_MAX_QUERY_PARAMETERS = 128
_MAX_MEDIA_TYPE_PARAMETERS = 64
_MAX_CONTENT_ENCODINGS = 32
_MAX_CONTENT_ENCODING_LENGTH = 64
_MAX_MEDIA_PARAMETER_NAME_LENGTH: int = 256
_MAX_MEDIA_PARAMETER_VALUE_LENGTH = 1024
_MAX_ARTIFACT_DIGEST_SCOPE_LENGTH = 128
_MAX_ARTIFACT_BYTE_LENGTH = 9_223_372_036_854_775_807
_MAX_RETAINED_ARTIFACTS_PER_REQUEST = 64
_MAX_REQUESTS_PER_ACQUISITION_RUN = 4096
_MAX_TRANSFORMATION_INPUTS = 64
_MAX_TRANSFORMATION_OUTPUTS = 64
_MAX_EVIDENCE_SCOPE_ID_LENGTH = 160
_MAX_EVIDENCE_REQUIREMENT_ID_LENGTH = 160
_MAX_EVIDENCE_DISPOSITION_REASON_LENGTH = 160
_MAX_OMISSION_SOURCE_RECORDS = 16
_MAX_EVIDENCE_RECORDS_PER_REQUIREMENT = 16
_MAX_REQUIREMENTS_PER_ASSESSMENT = 512
_MAX_PUBLICATION_CHECK_NAME_LENGTH = 128
_MAX_PUBLICATION_CHECK_ATTEMPT = 2_147_483_647
_MAX_ENVELOPE_LEGACY_SNAPSHOTS = 64
_MAX_ENVELOPE_REQUEST_MEMBERSHIPS = 4096
_MAX_ENVELOPE_ACQUISITION_RUNS = 64
_MAX_ENVELOPE_TRANSFORMATIONS = 256
_MAX_ENVELOPE_RECORD_RELATIONSHIPS = 256
_MAX_ENVELOPE_COMPLETENESS_ASSESSMENTS = 256
_MAX_ENVELOPE_PUBLICATIONS = 256
_LEGACY_ARTIFACT_SNAPSHOT_ADAPTER_ID = "legacy-artifact-snapshot-v1-envelope-adapter"
_LEGACY_ARTIFACT_SNAPSHOT_ADAPTER_VERSION = "1"
_ASSERTED_UTC_STARTED_AT_PATTERN = re.compile(
    r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}"
    r"(?:\.[0-9]{1,6})?(?:Z|\+00:00)"
)
_RUN_ID_PATTERN = re.compile(r"[a-z0-9](?:[a-z0-9._-]{0,158}[a-z0-9])?")
_INVALID_PERCENT_ENCODING = re.compile(r"%(?![0-9A-Fa-f]{2})")
_HTTP_TOKEN_PATTERN = re.compile(r"[!#$%&'*+\-.^_`|~0-9A-Za-z]+")
_MEDIA_TYPE_PATTERN = re.compile(
    r"[!#$%&'*+\-.^_`|~0-9A-Za-z]+/[!#$%&'*+\-.^_`|~0-9A-Za-z]+"
)
_ARTIFACT_DIGEST_SCOPE_PATTERN = re.compile(r"[a-z0-9](?:[a-z0-9-]{0,126}[a-z0-9])?")
_ARTIFACT_SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")

_AcquisitionRunIdValue = Annotated[
    str,
    StringConstraints(min_length=1, max_length=_MAX_RUN_ID_LENGTH),
]
_RetrievalRoutePathValue = Annotated[
    str,
    StringConstraints(min_length=1, max_length=_MAX_ROUTE_PATH_LENGTH),
]
_MediaTypeValue = Annotated[
    str,
    StringConstraints(min_length=3, max_length=_MAX_MEDIA_TYPE_LENGTH),
]
_ApiVersionValue = Annotated[
    str,
    StringConstraints(min_length=1, max_length=_MAX_API_VERSION_LENGTH),
]
_RequestQueryNameValue = Annotated[
    str,
    StringConstraints(min_length=1, max_length=_MAX_QUERY_NAME_LENGTH),
]
_RequestQueryValue = Annotated[
    str,
    StringConstraints(max_length=_MAX_QUERY_VALUE_LENGTH),
]
_ContentEncodingValue = Annotated[
    str,
    StringConstraints(min_length=1, max_length=_MAX_CONTENT_ENCODING_LENGTH),
]
_MediaTypeParameterValue = Annotated[
    str,
    StringConstraints(max_length=_MAX_MEDIA_PARAMETER_VALUE_LENGTH),
]
_ArtifactDigestScopeValue = Annotated[
    str,
    StringConstraints(min_length=1, max_length=_MAX_ARTIFACT_DIGEST_SCOPE_LENGTH),
]
_ArtifactSha256DigestValue = Annotated[
    str,
    StringConstraints(min_length=64, max_length=64),
]
_EvidenceRecordFormatValue = Annotated[
    str,
    StringConstraints(min_length=1, max_length=160),
]
_EvidenceVersionValue = Annotated[
    str,
    StringConstraints(min_length=1, max_length=64),
]
_EvidenceCanonicalizationValue = Annotated[
    str,
    StringConstraints(min_length=1, max_length=160),
]
_EvidenceRelationIdValue = Annotated[
    str,
    StringConstraints(min_length=1, max_length=160),
]
_TransformationOperationValue = Annotated[
    str,
    StringConstraints(min_length=1, max_length=128),
]
_EVIDENCE_RECORD_FORMAT_PATTERN = re.compile(r"[a-z0-9](?:[a-z0-9-]*[a-z0-9])?")
_EVIDENCE_VERSION_PATTERN = re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9._-]*[A-Za-z0-9])?")
_EVIDENCE_RELATION_ID_PATTERN = re.compile(r"[a-z0-9](?:[a-z0-9._-]*[a-z0-9])?")
_TRANSFORMATION_OPERATION_PATTERN = re.compile(r"[a-z0-9](?:[a-z0-9-]*[a-z0-9])?")
_EVIDENCE_SCOPE_ID_PATTERN = re.compile(r"[a-z0-9](?:[a-z0-9._-]{0,158}[a-z0-9])?")
_EVIDENCE_REQUIREMENT_ID_PATTERN = re.compile(
    r"[a-z0-9](?:[a-z0-9._-]{0,158}[a-z0-9])?"
)
_EVIDENCE_DISPOSITION_REASON_PATTERN = re.compile(
    r"[a-z0-9](?:[a-z0-9-]{0,158}[a-z0-9])?"
)

_EvidenceScopeIdValue = Annotated[
    str,
    StringConstraints(min_length=1, max_length=_MAX_EVIDENCE_SCOPE_ID_LENGTH),
]
_EvidenceRequirementIdValue = Annotated[
    str,
    StringConstraints(min_length=1, max_length=_MAX_EVIDENCE_REQUIREMENT_ID_LENGTH),
]
_EvidenceDispositionReasonValue = Annotated[
    str,
    StringConstraints(
        min_length=1,
        max_length=_MAX_EVIDENCE_DISPOSITION_REASON_LENGTH,
    ),
]
_PublicationCheckNameValue = Annotated[
    str,
    StringConstraints(min_length=1, max_length=_MAX_PUBLICATION_CHECK_NAME_LENGTH),
]


def _has_ascii_control(value: str) -> bool:
    return any(ord(character) < 32 or ord(character) == 127 for character in value)


def _require_asserted_utc_json(
    value: object,
    info: ValidationInfo,
    *,
    field_name: str,
) -> object:
    if info.mode != "json":
        return value
    if (
        not isinstance(value, str)
        or _ASSERTED_UTC_STARTED_AT_PATTERN.fullmatch(value) is None
    ):
        raise ValueError(
            f"{field_name} JSON value must use asserted-UTC RFC 3339 form "
            "ending in Z or +00:00"
        )
    parse_value = f"{value[:-1]}+00:00" if value.endswith("Z") else value
    try:
        return datetime.fromisoformat(parse_value)
    except ValueError:
        return value


def _normalize_asserted_utc(value: datetime, *, field_name: str) -> datetime:
    if value.utcoffset() != timedelta(0):
        raise ValueError(f"{field_name} must use a zero UTC offset")
    return value.astimezone(UTC)


class AcquisitionRunId(RootModel[_AcquisitionRunIdValue]):
    """Opaque acquisition-run identity with a conservative ASCII grammar."""

    model_config = ConfigDict(
        frozen=True,
        strict=True,
        revalidate_instances="always",
        validate_default=True,
    )

    root: _AcquisitionRunIdValue

    @field_validator("root")
    @classmethod
    def _validate_run_id(cls, value: str) -> str:
        if not value.isascii() or _RUN_ID_PATTERN.fullmatch(value) is None:
            raise ValueError(
                "acquisition run ID must begin and end with a lowercase ASCII "
                "letter or digit and contain only lowercase ASCII letters, "
                "digits, hyphens, underscores, or dots"
            )
        return value


class RetrievalRequestOrdinal(RootModel[int]):
    """Positive request ordinal scoped only to one acquisition run."""

    model_config = ConfigDict(
        frozen=True,
        strict=True,
        revalidate_instances="always",
        validate_default=True,
    )

    root: int

    @field_validator("root", mode="before")
    @classmethod
    def _validate_ordinal(cls, value: object) -> object:
        if type(value) is not int:
            raise ValueError("retrieval request ordinal must be an exact integer")
        if not 1 <= value <= _MAX_REQUEST_ORDINAL:
            raise ValueError(
                "retrieval request ordinal must be between 1 and "
                f"{_MAX_REQUEST_ORDINAL} inclusive"
            )
        return value


class _RetrievalRecordBase(BaseModel):
    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        strict=True,
        revalidate_instances="always",
        validate_default=True,
    )

    schema_version: Literal[1] = 1

    @field_validator("schema_version", mode="before")
    @classmethod
    def _require_exact_schema_version(cls, value: object) -> object:
        if type(value) is not int or value != 1:
            raise ValueError("schema_version must be the integer 1")
        return value


class RetrievalRequestId(_RetrievalRecordBase):
    """Identity of one request attempt: acquisition run plus local ordinal."""

    acquisition_run_id: AcquisitionRunId
    request_ordinal: RetrievalRequestOrdinal

    @field_validator("acquisition_run_id", mode="before")
    @classmethod
    def _require_typed_python_run_id(
        cls,
        value: object,
        info: ValidationInfo,
    ) -> object:
        if info.mode == "python" and not isinstance(value, AcquisitionRunId):
            raise ValueError(
                "acquisition_run_id must be an AcquisitionRunId in Python input"
            )
        return value

    @field_validator("request_ordinal", mode="before")
    @classmethod
    def _require_typed_python_ordinal(
        cls,
        value: object,
        info: ValidationInfo,
    ) -> object:
        if info.mode == "python" and not isinstance(value, RetrievalRequestOrdinal):
            raise ValueError(
                "request_ordinal must be a RetrievalRequestOrdinal in Python input"
            )
        return value


class RetrievalMethod(StrEnum):
    """Bounded HTTP method vocabulary observed or required for retrieval."""

    GET = "get"
    POST = "post"


class RetrievalRoutePath(RootModel[_RetrievalRoutePathValue]):
    """Exact ASCII origin-relative route path without query or fragment."""

    model_config = ConfigDict(
        frozen=True,
        strict=True,
        revalidate_instances="always",
        validate_default=True,
    )

    root: _RetrievalRoutePathValue

    @field_validator("root")
    @classmethod
    def _validate_route_path(cls, value: str) -> str:
        if not value.isascii():
            raise ValueError("retrieval route path must contain only ASCII characters")
        if not value.startswith("/") or value.startswith("//"):
            raise ValueError(
                "retrieval route path must begin with exactly one forward slash"
            )
        if "\\" in value:
            raise ValueError("retrieval route path must use forward slashes only")
        if "?" in value:
            raise ValueError("retrieval route path must not contain a query")
        if "#" in value:
            raise ValueError("retrieval route path must not contain a fragment")
        if any(
            character.isspace() or ord(character) < 32 or ord(character) == 127
            for character in value
        ):
            raise ValueError(
                "retrieval route path must not contain whitespace or controls"
            )
        if _INVALID_PERCENT_ENCODING.search(value) is not None:
            raise ValueError(
                "retrieval route path percent escapes must use exactly two "
                "hexadecimal digits"
            )
        return value


class RetrievalRequestReference(_RetrievalRecordBase):
    """Core provenance for one identified bounded retrieval request attempt."""

    request_id: RetrievalRequestId
    authority: ProviderAuthority
    method: RetrievalMethod
    route_path: RetrievalRoutePath
    started_at: AwareDatetime

    @field_validator("request_id", mode="before")
    @classmethod
    def _require_typed_python_request_id(
        cls,
        value: object,
        info: ValidationInfo,
    ) -> object:
        if info.mode == "python" and not isinstance(value, RetrievalRequestId):
            raise ValueError("request_id must be a RetrievalRequestId in Python input")
        return value

    @field_validator("authority", mode="before")
    @classmethod
    def _require_typed_python_authority(
        cls,
        value: object,
        info: ValidationInfo,
    ) -> object:
        if info.mode == "python" and not isinstance(value, ProviderAuthority):
            raise ValueError("authority must be a ProviderAuthority in Python input")
        return value

    @field_validator("authority")
    @classmethod
    def _require_retrieval_authority(
        cls,
        value: ProviderAuthority,
    ) -> ProviderAuthority:
        if value.role is not AuthorityRole.RETRIEVAL:
            raise ValueError("authority role must be retrieval")
        return value

    @field_validator("method", mode="before")
    @classmethod
    def _require_typed_python_method(
        cls,
        value: object,
        info: ValidationInfo,
    ) -> object:
        if info.mode == "python" and not isinstance(value, RetrievalMethod):
            raise ValueError("method must be a RetrievalMethod in Python input")
        return value

    @field_validator("route_path", mode="before")
    @classmethod
    def _require_typed_python_route_path(
        cls,
        value: object,
        info: ValidationInfo,
    ) -> object:
        if info.mode == "python" and not isinstance(value, RetrievalRoutePath):
            raise ValueError("route_path must be a RetrievalRoutePath in Python input")
        return value

    @field_validator("started_at", mode="before")
    @classmethod
    def _require_asserted_utc_started_at_json(
        cls,
        value: object,
        info: ValidationInfo,
    ) -> object:
        return _require_asserted_utc_json(value, info, field_name="started_at")

    @field_validator("started_at")
    @classmethod
    def _normalize_started_at(cls, value: datetime) -> datetime:
        return _normalize_asserted_utc(value, field_name="started_at")


class MediaType(RootModel[_MediaTypeValue]):
    """Exact ASCII media type without parameters or wildcards."""

    model_config = ConfigDict(
        frozen=True,
        strict=True,
        revalidate_instances="always",
        validate_default=True,
    )

    root: _MediaTypeValue

    @field_validator("root")
    @classmethod
    def _validate_media_type(cls, value: str) -> str:
        if not value.isascii() or _MEDIA_TYPE_PATTERN.fullmatch(value) is None:
            raise ValueError(
                "media type must use ASCII token/token grammar "
                "without parameters or wildcard components"
            )
        media_type, media_subtype = value.split("/", maxsplit=1)
        if media_type == "*" or media_subtype == "*":
            raise ValueError(
                "media type must use ASCII token/token grammar "
                "without parameters or wildcard components"
            )
        return value


class ApiVersion(RootModel[_ApiVersionValue]):
    """Exact bounded API-version lexeme without parsing or normalization."""

    model_config = ConfigDict(
        frozen=True,
        strict=True,
        revalidate_instances="always",
        validate_default=True,
    )

    root: _ApiVersionValue

    @field_validator("root")
    @classmethod
    def _validate_api_version(cls, value: str) -> str:
        if (
            not value.isascii()
            or _has_ascii_control(value)
            or any(character.isspace() for character in value)
        ):
            raise ValueError(
                "API version must contain only non-whitespace, non-control ASCII"
            )
        return value


class RequestQueryParameter(BaseModel):
    """One exact ordered encoded query entry with explicit delimiter presence."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        strict=True,
        revalidate_instances="always",
        validate_default=True,
    )

    name: _RequestQueryNameValue
    value: _RequestQueryValue
    value_delimiter_present: bool

    @field_validator("name", "value")
    @classmethod
    def _validate_query_text(cls, value: str) -> str:
        if re.fullmatch(r"(?:[A-Za-z0-9._~-]|%[0-9A-Fa-f]{2})*", value) is None:
            raise ValueError(
                "query parameter components must contain only RFC 3986 "
                "unreserved ASCII characters or percent escapes"
            )
        return value

    @model_validator(mode="after")
    def _validate_value_delimiter(self) -> Self:
        if self.value and not self.value_delimiter_present:
            raise ValueError(
                "nonempty query parameter value requires value_delimiter_present"
            )
        return self


class RetrievalRequestControls(_RetrievalRecordBase):
    """Explicit ordered controls for a request, separate from its identity."""

    query_delimiter_present: bool
    query_parameters: tuple[RequestQueryParameter, ...]
    requested_media_type: MediaType
    api_version: ApiVersion | None

    @field_validator("query_parameters", mode="before")
    @classmethod
    def _require_typed_python_query_parameters(
        cls,
        value: object,
        info: ValidationInfo,
    ) -> object:
        if info.mode == "json":
            if isinstance(value, list):
                raw_value = cast(list[object], value)
                if len(raw_value) > _MAX_QUERY_PARAMETERS:
                    raise ValueError(
                        "query_parameters must contain at most "
                        f"{_MAX_QUERY_PARAMETERS} entries"
                    )
                return tuple(raw_value)
            return value
        if info.mode != "python":
            return value
        if type(value) is not tuple:
            raise ValueError("query_parameters must be a tuple in Python input")
        typed_value = cast(tuple[object, ...], value)
        if len(typed_value) > _MAX_QUERY_PARAMETERS:
            raise ValueError(
                f"query_parameters must contain at most {_MAX_QUERY_PARAMETERS} entries"
            )
        if not all(isinstance(item, RequestQueryParameter) for item in typed_value):
            raise ValueError(
                "query_parameters entries must be RequestQueryParameter values "
                "in Python input"
            )
        return typed_value

    @field_validator("requested_media_type", mode="before")
    @classmethod
    def _require_typed_python_requested_media_type(
        cls,
        value: object,
        info: ValidationInfo,
    ) -> object:
        if info.mode == "python" and not isinstance(value, MediaType):
            raise ValueError("requested_media_type must be a MediaType in Python input")
        return value

    @field_validator("api_version", mode="before")
    @classmethod
    def _require_typed_python_api_version(
        cls,
        value: object,
        info: ValidationInfo,
    ) -> object:
        if (
            info.mode == "python"
            and value is not None
            and not isinstance(value, ApiVersion)
        ):
            raise ValueError(
                "api_version must be an ApiVersion or None in Python input"
            )
        return value

    @model_validator(mode="after")
    def _validate_query_delimiter_presence(self) -> Self:
        if not self.query_delimiter_present and self.query_parameters:
            raise ValueError(
                "query_parameters require query_delimiter_present to be true"
            )
        return self


class ResponseRepresentationState(StrEnum):
    """Availability of one response representation observation."""

    OBSERVED = "observed"
    UNAVAILABLE = "unavailable"
    INACCESSIBLE = "inaccessible"
    UNKNOWN = "unknown"


class HttpStatusCode(RootModel[int]):
    """Exact HTTP status code in the protocol-defined three-digit range."""

    model_config = ConfigDict(
        frozen=True,
        strict=True,
        revalidate_instances="always",
        validate_default=True,
    )

    root: int

    @field_validator("root", mode="before")
    @classmethod
    def _validate_status_code(cls, value: object) -> object:
        if type(value) is not int:
            raise ValueError("HTTP status code must be an exact integer")
        if not 100 <= value <= 599:
            raise ValueError("HTTP status code must be between 100 and 599 inclusive")
        return value


class ContentEncoding(RootModel[_ContentEncodingValue]):
    """Exact ASCII content-encoding token."""

    model_config = ConfigDict(
        frozen=True,
        strict=True,
        revalidate_instances="always",
        validate_default=True,
    )

    root: _ContentEncodingValue

    @field_validator("root")
    @classmethod
    def _validate_content_encoding(cls, value: str) -> str:
        if not value.isascii() or _HTTP_TOKEN_PATTERN.fullmatch(value) is None:
            raise ValueError("content encoding must use ASCII HTTP token grammar")
        return value


class MediaTypeParameter(BaseModel):
    """One exact ordered observed media-type parameter."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        strict=True,
        revalidate_instances="always",
        validate_default=True,
    )

    name: Annotated[
        str,
        StringConstraints(
            min_length=1,
            max_length=_MAX_MEDIA_PARAMETER_NAME_LENGTH,
        ),
    ]
    value: _MediaTypeParameterValue

    @field_validator("name")
    @classmethod
    def _validate_name(cls, value: str) -> str:
        if not value.isascii() or _HTTP_TOKEN_PATTERN.fullmatch(value) is None:
            raise ValueError(
                "media type parameter name must use ASCII HTTP token grammar"
            )
        return value

    @field_validator("value")
    @classmethod
    def _validate_value(cls, value: str) -> str:
        if _has_ascii_control(value):
            raise ValueError(
                "media type parameter value must not contain ASCII controls"
            )
        return value


class ResponseRepresentationObservation(_RetrievalRecordBase):
    """Immutable metadata observation for one request's response representation."""

    request_id: RetrievalRequestId
    state: ResponseRepresentationState
    completed_at: AwareDatetime
    status_code: HttpStatusCode | None
    observed_media_type: MediaType | None
    media_type_parameters: tuple[MediaTypeParameter, ...] | None
    content_encodings: tuple[ContentEncoding, ...] | None

    @field_validator("request_id", mode="before")
    @classmethod
    def _require_typed_python_request_id(
        cls,
        value: object,
        info: ValidationInfo,
    ) -> object:
        if info.mode == "python" and not isinstance(value, RetrievalRequestId):
            raise ValueError("request_id must be a RetrievalRequestId in Python input")
        return value

    @field_validator("state", mode="before")
    @classmethod
    def _require_typed_python_state(
        cls,
        value: object,
        info: ValidationInfo,
    ) -> object:
        if info.mode == "python" and not isinstance(value, ResponseRepresentationState):
            raise ValueError(
                "state must be a ResponseRepresentationState in Python input"
            )
        return value

    @field_validator("completed_at", mode="before")
    @classmethod
    def _require_asserted_utc_completed_at_json(
        cls,
        value: object,
        info: ValidationInfo,
    ) -> object:
        return _require_asserted_utc_json(value, info, field_name="completed_at")

    @field_validator("completed_at")
    @classmethod
    def _normalize_completed_at(cls, value: datetime) -> datetime:
        return _normalize_asserted_utc(value, field_name="completed_at")

    @field_validator("status_code", mode="before")
    @classmethod
    def _require_typed_python_status_code(
        cls,
        value: object,
        info: ValidationInfo,
    ) -> object:
        if (
            info.mode == "python"
            and value is not None
            and not isinstance(value, HttpStatusCode)
        ):
            raise ValueError(
                "status_code must be an HttpStatusCode or None in Python input"
            )
        return value

    @field_validator("observed_media_type", mode="before")
    @classmethod
    def _require_typed_python_observed_media_type(
        cls,
        value: object,
        info: ValidationInfo,
    ) -> object:
        if (
            info.mode == "python"
            and value is not None
            and not isinstance(value, MediaType)
        ):
            raise ValueError(
                "observed_media_type must be a MediaType or None in Python input"
            )
        return value

    @field_validator("media_type_parameters", mode="before")
    @classmethod
    def _require_typed_python_media_type_parameters(
        cls,
        value: object,
        info: ValidationInfo,
    ) -> object:
        if value is None:
            return value
        if info.mode == "json":
            if isinstance(value, list):
                raw_value = cast(list[object], value)
                if len(raw_value) > _MAX_MEDIA_TYPE_PARAMETERS:
                    raise ValueError(
                        "media_type_parameters must contain at most "
                        f"{_MAX_MEDIA_TYPE_PARAMETERS} entries"
                    )
                return tuple(raw_value)
            return value
        if info.mode != "python":
            return value
        if type(value) is not tuple:
            raise ValueError(
                "media_type_parameters must be a tuple or None in Python input"
            )
        typed_value = cast(tuple[object, ...], value)
        if len(typed_value) > _MAX_MEDIA_TYPE_PARAMETERS:
            raise ValueError(
                "media_type_parameters must contain at most "
                f"{_MAX_MEDIA_TYPE_PARAMETERS} entries"
            )
        if not all(isinstance(item, MediaTypeParameter) for item in typed_value):
            raise ValueError(
                "media_type_parameters entries must be MediaTypeParameter values "
                "in Python input"
            )
        return typed_value

    @field_validator("content_encodings", mode="before")
    @classmethod
    def _require_typed_python_content_encodings(
        cls,
        value: object,
        info: ValidationInfo,
    ) -> object:
        if value is None:
            return value
        if info.mode == "json":
            if isinstance(value, list):
                raw_value = cast(list[object], value)
                if len(raw_value) > _MAX_CONTENT_ENCODINGS:
                    raise ValueError(
                        "content_encodings must contain at most "
                        f"{_MAX_CONTENT_ENCODINGS} entries"
                    )
                return tuple(raw_value)
            return value
        if info.mode != "python":
            return value
        if type(value) is not tuple:
            raise ValueError(
                "content_encodings must be a tuple or None in Python input"
            )
        typed_value = cast(tuple[object, ...], value)
        if len(typed_value) > _MAX_CONTENT_ENCODINGS:
            raise ValueError(
                "content_encodings must contain at most "
                f"{_MAX_CONTENT_ENCODINGS} entries"
            )
        if not all(isinstance(item, ContentEncoding) for item in typed_value):
            raise ValueError(
                "content_encodings entries must be ContentEncoding values "
                "in Python input"
            )
        return typed_value

    @model_validator(mode="after")
    def _validate_media_type_parameters(self) -> Self:
        if self.observed_media_type is None and self.media_type_parameters is not None:
            raise ValueError(
                "media_type_parameters require observed_media_type to be present"
            )
        return self


class ArtifactDigestAlgorithm(StrEnum):
    """Supported algorithm for an exact retained-artifact digest claim."""

    SHA256 = "sha256"


class ArtifactDigestScope(RootModel[_ArtifactDigestScopeValue]):
    """Exact bounded identifier for the bytes covered by an artifact digest."""

    model_config = ConfigDict(
        frozen=True,
        strict=True,
        revalidate_instances="always",
        validate_default=True,
    )

    root: _ArtifactDigestScopeValue

    @field_validator("root")
    @classmethod
    def _validate_digest_scope(cls, value: str) -> str:
        if (
            not value.isascii()
            or _ARTIFACT_DIGEST_SCOPE_PATTERN.fullmatch(value) is None
        ):
            raise ValueError(
                "artifact digest scope must begin and end with a lowercase ASCII "
                "letter or digit and contain only lowercase ASCII letters, "
                "digits, or interior hyphens"
            )
        return value


class ArtifactSha256Digest(RootModel[_ArtifactSha256DigestValue]):
    """Exact lowercase nonzero SHA-256 digest lexeme for retained bytes."""

    model_config = ConfigDict(
        frozen=True,
        strict=True,
        revalidate_instances="always",
        validate_default=True,
    )

    root: _ArtifactSha256DigestValue

    @field_validator("root")
    @classmethod
    def _validate_sha256_digest(cls, value: str) -> str:
        if _ARTIFACT_SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError(
                "artifact SHA-256 digest must contain exactly 64 lowercase "
                "ASCII hexadecimal characters"
            )
        if value == "0" * 64:
            raise ValueError("artifact SHA-256 digest must not be all zero")
        return value


class ArtifactByteLength(RootModel[int]):
    """Exact retained-artifact octet count."""

    model_config = ConfigDict(
        frozen=True,
        strict=True,
        revalidate_instances="always",
        validate_default=True,
    )

    root: int

    @field_validator("root", mode="before")
    @classmethod
    def _validate_byte_length(cls, value: object) -> object:
        if type(value) is not int:
            raise ValueError("artifact byte length must be an exact integer")
        if not 0 <= value <= _MAX_ARTIFACT_BYTE_LENGTH:
            raise ValueError(
                "artifact byte length must be between 0 and "
                f"{_MAX_ARTIFACT_BYTE_LENGTH} inclusive"
            )
        return value


class _ArtifactRecordBase(BaseModel):
    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        strict=True,
        revalidate_instances="always",
        validate_default=True,
    )

    schema_version: Literal[1] = 1

    @field_validator("schema_version", mode="before")
    @classmethod
    def _require_exact_schema_version(cls, value: object) -> object:
        if type(value) is not int or value != 1:
            raise ValueError("schema_version must be the integer 1")
        return value


class ArtifactDigest(_ArtifactRecordBase):
    """Algorithm-, scope-, and value-qualified artifact digest claim."""

    algorithm: ArtifactDigestAlgorithm
    scope: ArtifactDigestScope
    value: ArtifactSha256Digest

    @field_validator("algorithm", mode="before")
    @classmethod
    def _require_typed_python_algorithm(
        cls,
        value: object,
        info: ValidationInfo,
    ) -> object:
        if info.mode == "python" and not isinstance(value, ArtifactDigestAlgorithm):
            raise ValueError(
                "algorithm must be an ArtifactDigestAlgorithm in Python input"
            )
        return value

    @field_validator("scope", mode="before")
    @classmethod
    def _require_typed_python_scope(
        cls,
        value: object,
        info: ValidationInfo,
    ) -> object:
        if info.mode == "python" and not isinstance(value, ArtifactDigestScope):
            raise ValueError("scope must be an ArtifactDigestScope in Python input")
        return value

    @field_validator("value", mode="before")
    @classmethod
    def _require_typed_python_value(
        cls,
        value: object,
        info: ValidationInfo,
    ) -> object:
        if info.mode == "python" and not isinstance(value, ArtifactSha256Digest):
            raise ValueError("value must be an ArtifactSha256Digest in Python input")
        return value


class ExactArtifactIdentity(_ArtifactRecordBase):
    """Content identity from explicit digest semantics and exact byte length."""

    digest: ArtifactDigest
    byte_length: ArtifactByteLength

    @field_validator("digest", mode="before")
    @classmethod
    def _require_typed_python_digest(
        cls,
        value: object,
        info: ValidationInfo,
    ) -> object:
        if info.mode == "python" and not isinstance(value, ArtifactDigest):
            raise ValueError("digest must be an ArtifactDigest in Python input")
        return value

    @field_validator("byte_length", mode="before")
    @classmethod
    def _require_typed_python_byte_length(
        cls,
        value: object,
        info: ValidationInfo,
    ) -> object:
        if info.mode == "python" and not isinstance(value, ArtifactByteLength):
            raise ValueError(
                "byte_length must be an ArtifactByteLength in Python input"
            )
        return value


class ArtifactRetentionMode(StrEnum):
    """Supported retention semantics for exact artifact bytes."""

    EXACT_UNMODIFIED_BYTES = "exact_unmodified_bytes"


class ExactRetainedArtifact(_ArtifactRecordBase):
    """Request linkage to one retained exact-artifact identity."""

    request_id: RetrievalRequestId
    artifact_identity: ExactArtifactIdentity
    retention_mode: ArtifactRetentionMode

    @field_validator("request_id", mode="before")
    @classmethod
    def _require_typed_python_request_id(
        cls,
        value: object,
        info: ValidationInfo,
    ) -> object:
        if info.mode == "python" and not isinstance(value, RetrievalRequestId):
            raise ValueError("request_id must be a RetrievalRequestId in Python input")
        return value

    @field_validator("artifact_identity", mode="before")
    @classmethod
    def _require_typed_python_artifact_identity(
        cls,
        value: object,
        info: ValidationInfo,
    ) -> object:
        if info.mode == "python" and not isinstance(value, ExactArtifactIdentity):
            raise ValueError(
                "artifact_identity must be an ExactArtifactIdentity in Python input"
            )
        return value

    @field_validator("retention_mode", mode="before")
    @classmethod
    def _require_typed_python_retention_mode(
        cls,
        value: object,
        info: ValidationInfo,
    ) -> object:
        if info.mode == "python" and not isinstance(value, ArtifactRetentionMode):
            raise ValueError(
                "retention_mode must be an ArtifactRetentionMode in Python input"
            )
        return value


class AcquisitionRunStatus(StrEnum):
    """Explicit terminal state declared for one acquisition run."""

    COMPLETE = "complete"
    PARTIAL = "partial"


class AcquisitionRequestMembership(_RetrievalRecordBase):
    """Optional evidence components linked to one request in an acquisition run."""

    request_id: RetrievalRequestId
    request_reference: RetrievalRequestReference | None
    request_controls: RetrievalRequestControls | None
    response_observation: ResponseRepresentationObservation | None
    retained_artifacts: tuple[ExactRetainedArtifact, ...] | None

    @field_validator("request_id", mode="before")
    @classmethod
    def _require_typed_python_request_id(
        cls,
        value: object,
        info: ValidationInfo,
    ) -> object:
        if info.mode == "python" and not isinstance(value, RetrievalRequestId):
            raise ValueError("request_id must be a RetrievalRequestId in Python input")
        return value

    @field_validator("request_reference", mode="before")
    @classmethod
    def _require_typed_python_request_reference(
        cls,
        value: object,
        info: ValidationInfo,
    ) -> object:
        if (
            info.mode == "python"
            and value is not None
            and not isinstance(value, RetrievalRequestReference)
        ):
            raise ValueError(
                "request_reference must be a RetrievalRequestReference or None "
                "in Python input"
            )
        return value

    @field_validator("request_controls", mode="before")
    @classmethod
    def _require_typed_python_request_controls(
        cls,
        value: object,
        info: ValidationInfo,
    ) -> object:
        if (
            info.mode == "python"
            and value is not None
            and not isinstance(value, RetrievalRequestControls)
        ):
            raise ValueError(
                "request_controls must be RetrievalRequestControls or None in "
                "Python input"
            )
        return value

    @field_validator("response_observation", mode="before")
    @classmethod
    def _require_typed_python_response_observation(
        cls,
        value: object,
        info: ValidationInfo,
    ) -> object:
        if (
            info.mode == "python"
            and value is not None
            and not isinstance(value, ResponseRepresentationObservation)
        ):
            raise ValueError(
                "response_observation must be a ResponseRepresentationObservation "
                "or None in Python input"
            )
        return value

    @field_validator("retained_artifacts", mode="before")
    @classmethod
    def _require_typed_python_retained_artifacts(
        cls,
        value: object,
        info: ValidationInfo,
    ) -> object:
        if value is None:
            return value
        if info.mode == "json":
            if isinstance(value, list):
                raw_value = cast(list[object], value)
                if len(raw_value) > _MAX_RETAINED_ARTIFACTS_PER_REQUEST:
                    raise ValueError(
                        "retained_artifacts must contain at most "
                        f"{_MAX_RETAINED_ARTIFACTS_PER_REQUEST} entries"
                    )
                return tuple(raw_value)
            return value
        if info.mode != "python":
            return value
        if type(value) is not tuple:
            raise ValueError(
                "retained_artifacts must be a tuple or None in Python input"
            )
        typed_value = cast(tuple[object, ...], value)
        if len(typed_value) > _MAX_RETAINED_ARTIFACTS_PER_REQUEST:
            raise ValueError(
                "retained_artifacts must contain at most "
                f"{_MAX_RETAINED_ARTIFACTS_PER_REQUEST} entries"
            )
        if not all(isinstance(item, ExactRetainedArtifact) for item in typed_value):
            raise ValueError(
                "retained_artifacts entries must be ExactRetainedArtifact values "
                "in Python input"
            )
        return typed_value

    @model_validator(mode="after")
    def _validate_request_linkage_and_artifact_uniqueness(self) -> Self:
        if (
            self.request_reference is not None
            and self.request_reference.request_id != self.request_id
        ):
            raise ValueError("request_reference must match membership request_id")
        if (
            self.response_observation is not None
            and self.response_observation.request_id != self.request_id
        ):
            raise ValueError("response_observation must match membership request_id")

        identities: set[ExactArtifactIdentity] = set()
        for artifact in self.retained_artifacts or ():
            if artifact.request_id != self.request_id:
                raise ValueError("retained artifact must match membership request_id")
            if artifact.artifact_identity in identities:
                raise ValueError(
                    "retained artifact identities must be unique within a membership"
                )
            identities.add(artifact.artifact_identity)
        return self


class AcquisitionRun(_RetrievalRecordBase):
    """Terminal acquisition state with exact ordered request membership."""

    run_id: AcquisitionRunId
    status: AcquisitionRunStatus
    started_at: AwareDatetime
    sealed_at: AwareDatetime
    request_count: int
    requests: tuple[AcquisitionRequestMembership, ...]

    @field_validator("run_id", mode="before")
    @classmethod
    def _require_typed_python_run_id(
        cls,
        value: object,
        info: ValidationInfo,
    ) -> object:
        if info.mode == "python" and not isinstance(value, AcquisitionRunId):
            raise ValueError("run_id must be an AcquisitionRunId in Python input")
        return value

    @field_validator("status", mode="before")
    @classmethod
    def _require_typed_python_status(
        cls,
        value: object,
        info: ValidationInfo,
    ) -> object:
        if info.mode == "python" and not isinstance(value, AcquisitionRunStatus):
            raise ValueError("status must be an AcquisitionRunStatus in Python input")
        return value

    @field_validator("started_at", mode="before")
    @classmethod
    def _require_asserted_utc_started_at_json(
        cls,
        value: object,
        info: ValidationInfo,
    ) -> object:
        return _require_asserted_utc_json(value, info, field_name="started_at")

    @field_validator("started_at")
    @classmethod
    def _normalize_started_at(cls, value: datetime) -> datetime:
        return _normalize_asserted_utc(value, field_name="started_at")

    @field_validator("sealed_at", mode="before")
    @classmethod
    def _require_asserted_utc_sealed_at_json(
        cls,
        value: object,
        info: ValidationInfo,
    ) -> object:
        return _require_asserted_utc_json(value, info, field_name="sealed_at")

    @field_validator("sealed_at")
    @classmethod
    def _normalize_sealed_at(cls, value: datetime) -> datetime:
        return _normalize_asserted_utc(value, field_name="sealed_at")

    @field_validator("request_count", mode="before")
    @classmethod
    def _validate_request_count(cls, value: object) -> object:
        if type(value) is not int:
            raise ValueError("request_count must be an exact integer")
        if not 0 <= value <= _MAX_REQUESTS_PER_ACQUISITION_RUN:
            raise ValueError(
                "request_count must be between 0 and "
                f"{_MAX_REQUESTS_PER_ACQUISITION_RUN} inclusive"
            )
        return value

    @field_validator("requests", mode="before")
    @classmethod
    def _require_typed_python_requests(
        cls,
        value: object,
        info: ValidationInfo,
    ) -> object:
        if info.mode == "json":
            if isinstance(value, list):
                raw_value = cast(list[object], value)
                if len(raw_value) > _MAX_REQUESTS_PER_ACQUISITION_RUN:
                    raise ValueError(
                        "requests must contain at most "
                        f"{_MAX_REQUESTS_PER_ACQUISITION_RUN} entries"
                    )
                return tuple(raw_value)
            return value
        if info.mode != "python":
            return value
        if type(value) is not tuple:
            raise ValueError("requests must be a tuple in Python input")
        typed_value = cast(tuple[object, ...], value)
        if len(typed_value) > _MAX_REQUESTS_PER_ACQUISITION_RUN:
            raise ValueError(
                "requests must contain at most "
                f"{_MAX_REQUESTS_PER_ACQUISITION_RUN} entries"
            )
        if not all(
            isinstance(item, AcquisitionRequestMembership) for item in typed_value
        ):
            raise ValueError(
                "requests entries must be AcquisitionRequestMembership values "
                "in Python input"
            )
        return typed_value

    @model_validator(mode="after")
    def _validate_run_membership_and_chronology(self) -> Self:
        if self.sealed_at < self.started_at:
            raise ValueError("sealed_at must not precede started_at")
        if self.request_count != len(self.requests):
            raise ValueError("request_count must equal the number of requests")

        previous_request_started_at: datetime | None = None
        for expected_ordinal, membership in enumerate(self.requests, start=1):
            request_id = membership.request_id
            if request_id.acquisition_run_id != self.run_id:
                raise ValueError("membership request_id must belong to run_id")
            if request_id.request_ordinal.root != expected_ordinal:
                raise ValueError(
                    "membership request ordinals must equal tuple positions "
                    "starting at 1"
                )

            request_reference = membership.request_reference
            if request_reference is not None:
                if (
                    not self.started_at
                    <= request_reference.started_at
                    <= self.sealed_at
                ):
                    raise ValueError(
                        "request_reference started_at must lie within the run window"
                    )
                if (
                    previous_request_started_at is not None
                    and request_reference.started_at < previous_request_started_at
                ):
                    raise ValueError(
                        "present request_reference start times must be nondecreasing"
                    )
                previous_request_started_at = request_reference.started_at

            response_observation = membership.response_observation
            if response_observation is not None:
                if not (
                    self.started_at
                    <= response_observation.completed_at
                    <= self.sealed_at
                ):
                    raise ValueError(
                        "response_observation completed_at must lie within the run "
                        "window"
                    )
                if (
                    request_reference is not None
                    and response_observation.completed_at < request_reference.started_at
                ):
                    raise ValueError(
                        "response_observation completed_at must not precede its "
                        "request_reference started_at"
                    )
        return self


class EvidenceRecordFormat(RootModel[_EvidenceRecordFormatValue]):
    """Exact internal format identifier for durable evidence-record bytes."""

    model_config = ConfigDict(
        frozen=True,
        strict=True,
        revalidate_instances="always",
        validate_default=True,
    )

    root: _EvidenceRecordFormatValue

    @field_validator("root")
    @classmethod
    def _validate_record_format(cls, value: str) -> str:
        if (
            not value.isascii()
            or _EVIDENCE_RECORD_FORMAT_PATTERN.fullmatch(value) is None
        ):
            raise ValueError(
                "evidence record format must begin and end with a lowercase "
                "ASCII letter or digit and contain only lowercase ASCII "
                "letters, digits, or interior hyphens"
            )
        return value


class EvidenceVersion(RootModel[_EvidenceVersionValue]):
    """Exact bounded version lexeme without numeric or date interpretation."""

    model_config = ConfigDict(
        frozen=True,
        strict=True,
        revalidate_instances="always",
        validate_default=True,
    )

    root: _EvidenceVersionValue

    @field_validator("root")
    @classmethod
    def _validate_evidence_version(cls, value: str) -> str:
        if not value.isascii() or _EVIDENCE_VERSION_PATTERN.fullmatch(value) is None:
            raise ValueError(
                "evidence version must begin and end with an ASCII letter or "
                "digit and contain only ASCII letters, digits, dots, hyphens, "
                "or underscores"
            )
        return value


class EvidenceCanonicalization(RootModel[_EvidenceCanonicalizationValue]):
    """Exact identifier for a durable record's declared byte convention."""

    model_config = ConfigDict(
        frozen=True,
        strict=True,
        revalidate_instances="always",
        validate_default=True,
    )

    root: _EvidenceCanonicalizationValue

    @field_validator("root")
    @classmethod
    def _validate_canonicalization(cls, value: str) -> str:
        if (
            not value.isascii()
            or _EVIDENCE_RECORD_FORMAT_PATTERN.fullmatch(value) is None
        ):
            raise ValueError(
                "evidence canonicalization must begin and end with a lowercase "
                "ASCII letter or digit and contain only lowercase ASCII "
                "letters, digits, or interior hyphens"
            )
        return value


class _EvidenceRecordBase(BaseModel):
    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        strict=True,
        revalidate_instances="always",
        validate_default=True,
    )

    schema_version: Literal[1] = 1

    @field_validator("schema_version", mode="before")
    @classmethod
    def _require_exact_schema_version(cls, value: object) -> object:
        if type(value) is not int or value != 1:
            raise ValueError("schema_version must be the integer 1")
        return value


class DurableEvidenceRecordReference(_EvidenceRecordBase):
    """Content-addressed reference to declared exact durable-record bytes."""

    format_name: EvidenceRecordFormat
    format_version: EvidenceVersion
    canonicalization: EvidenceCanonicalization
    sha256: ArtifactSha256Digest
    byte_length: ArtifactByteLength

    @field_validator("format_name", mode="before")
    @classmethod
    def _require_typed_python_format_name(
        cls,
        value: object,
        info: ValidationInfo,
    ) -> object:
        if info.mode == "python" and not isinstance(value, EvidenceRecordFormat):
            raise ValueError(
                "format_name must be an EvidenceRecordFormat in Python input"
            )
        return value

    @field_validator("format_version", mode="before")
    @classmethod
    def _require_typed_python_format_version(
        cls,
        value: object,
        info: ValidationInfo,
    ) -> object:
        if info.mode == "python" and not isinstance(value, EvidenceVersion):
            raise ValueError(
                "format_version must be an EvidenceVersion in Python input"
            )
        return value

    @field_validator("canonicalization", mode="before")
    @classmethod
    def _require_typed_python_canonicalization(
        cls,
        value: object,
        info: ValidationInfo,
    ) -> object:
        if info.mode == "python" and not isinstance(value, EvidenceCanonicalization):
            raise ValueError(
                "canonicalization must be an EvidenceCanonicalization in Python input"
            )
        return value

    @field_validator("sha256", mode="before")
    @classmethod
    def _require_typed_python_sha256(
        cls,
        value: object,
        info: ValidationInfo,
    ) -> object:
        if info.mode == "python" and not isinstance(value, ArtifactSha256Digest):
            raise ValueError("sha256 must be an ArtifactSha256Digest in Python input")
        return value

    @field_validator("byte_length", mode="before")
    @classmethod
    def _require_typed_python_byte_length(
        cls,
        value: object,
        info: ValidationInfo,
    ) -> object:
        if info.mode == "python" and not isinstance(value, ArtifactByteLength):
            raise ValueError(
                "byte_length must be an ArtifactByteLength in Python input"
            )
        return value


class EvidenceRelationId(RootModel[_EvidenceRelationIdValue]):
    """Exact internal identifier for one evidence relationship edge."""

    model_config = ConfigDict(
        frozen=True,
        strict=True,
        revalidate_instances="always",
        validate_default=True,
    )

    root: _EvidenceRelationIdValue

    @field_validator("root")
    @classmethod
    def _validate_relation_id(cls, value: str) -> str:
        if (
            not value.isascii()
            or _EVIDENCE_RELATION_ID_PATTERN.fullmatch(value) is None
        ):
            raise ValueError(
                "evidence relation ID must begin and end with a lowercase ASCII "
                "letter or digit and contain only lowercase ASCII letters, "
                "digits, hyphens, underscores, or dots"
            )
        return value


class TransformationOperation(RootModel[_TransformationOperationValue]):
    """Descriptive transformation-operation identity that is never executed."""

    model_config = ConfigDict(
        frozen=True,
        strict=True,
        revalidate_instances="always",
        validate_default=True,
    )

    root: _TransformationOperationValue

    @field_validator("root")
    @classmethod
    def _validate_operation(cls, value: str) -> str:
        if (
            not value.isascii()
            or _TRANSFORMATION_OPERATION_PATTERN.fullmatch(value) is None
        ):
            raise ValueError(
                "transformation operation must begin and end with a lowercase "
                "ASCII letter or digit and contain only lowercase ASCII "
                "letters, digits, or interior hyphens"
            )
        return value


class TransformationLossiness(StrEnum):
    """Explicit information-loss classification for a transformation."""

    LOSSLESS = "lossless"
    LOSSY = "lossy"
    UNKNOWN = "unknown"


class TransformationReversibility(StrEnum):
    """Explicit reversibility classification for a transformation."""

    REVERSIBLE = "reversible"
    IRREVERSIBLE = "irreversible"
    UNKNOWN = "unknown"


class TransformationSubject(_EvidenceRecordBase):
    """Exactly one artifact or durable-record subject of a transformation."""

    subject_kind: Literal["exact_artifact", "durable_record"]
    artifact_identity: ExactArtifactIdentity | None
    record_reference: DurableEvidenceRecordReference | None

    @field_validator("artifact_identity", mode="before")
    @classmethod
    def _require_typed_python_artifact_identity(
        cls,
        value: object,
        info: ValidationInfo,
    ) -> object:
        if (
            info.mode == "python"
            and value is not None
            and not isinstance(value, ExactArtifactIdentity)
        ):
            raise ValueError(
                "artifact_identity must be an ExactArtifactIdentity or None in "
                "Python input"
            )
        return value

    @field_validator("record_reference", mode="before")
    @classmethod
    def _require_typed_python_record_reference(
        cls,
        value: object,
        info: ValidationInfo,
    ) -> object:
        if (
            info.mode == "python"
            and value is not None
            and not isinstance(value, DurableEvidenceRecordReference)
        ):
            raise ValueError(
                "record_reference must be a DurableEvidenceRecordReference or "
                "None in Python input"
            )
        return value

    @model_validator(mode="after")
    def _validate_subject_representation(self) -> Self:
        if self.subject_kind == "exact_artifact":
            if self.artifact_identity is None or self.record_reference is not None:
                raise ValueError(
                    "exact_artifact subject requires artifact_identity and no "
                    "record_reference"
                )
        elif self.record_reference is None or self.artifact_identity is not None:
            raise ValueError(
                "durable_record subject requires record_reference and no "
                "artifact_identity"
            )
        return self


class EvidenceTransformation(_EvidenceRecordBase):
    """Explicit, non-executing derivation edge between ordered subjects."""

    transformation_id: EvidenceRelationId
    operation: TransformationOperation
    operation_version: EvidenceVersion
    performed_at: AwareDatetime
    inputs: tuple[TransformationSubject, ...]
    outputs: tuple[TransformationSubject, ...]
    lossiness: TransformationLossiness
    reversibility: TransformationReversibility
    parameter_record: DurableEvidenceRecordReference | None

    @field_validator("transformation_id", mode="before")
    @classmethod
    def _require_typed_python_transformation_id(
        cls,
        value: object,
        info: ValidationInfo,
    ) -> object:
        if info.mode == "python" and not isinstance(value, EvidenceRelationId):
            raise ValueError(
                "transformation_id must be an EvidenceRelationId in Python input"
            )
        return value

    @field_validator("operation", mode="before")
    @classmethod
    def _require_typed_python_operation(
        cls,
        value: object,
        info: ValidationInfo,
    ) -> object:
        if info.mode == "python" and not isinstance(value, TransformationOperation):
            raise ValueError(
                "operation must be a TransformationOperation in Python input"
            )
        return value

    @field_validator("operation_version", mode="before")
    @classmethod
    def _require_typed_python_operation_version(
        cls,
        value: object,
        info: ValidationInfo,
    ) -> object:
        if info.mode == "python" and not isinstance(value, EvidenceVersion):
            raise ValueError(
                "operation_version must be an EvidenceVersion in Python input"
            )
        return value

    @field_validator("performed_at", mode="before")
    @classmethod
    def _require_asserted_utc_performed_at_json(
        cls,
        value: object,
        info: ValidationInfo,
    ) -> object:
        return _require_asserted_utc_json(value, info, field_name="performed_at")

    @field_validator("performed_at")
    @classmethod
    def _normalize_performed_at(cls, value: datetime) -> datetime:
        return _normalize_asserted_utc(value, field_name="performed_at")

    @field_validator("inputs", "outputs", mode="before")
    @classmethod
    def _require_bounded_typed_subjects(
        cls,
        value: object,
        info: ValidationInfo,
    ) -> object:
        field_name = info.field_name or "subjects"
        maximum = (
            _MAX_TRANSFORMATION_INPUTS
            if field_name == "inputs"
            else _MAX_TRANSFORMATION_OUTPUTS
        )
        if info.mode == "json":
            if isinstance(value, list):
                raw_value = cast(list[object], value)
                if not 1 <= len(raw_value) <= maximum:
                    raise ValueError(
                        f"{field_name} must contain between 1 and {maximum} entries"
                    )
                return tuple(raw_value)
            return value
        if info.mode != "python":
            return value
        if type(value) is not tuple:
            raise ValueError(f"{field_name} must be a tuple in Python input")
        typed_value = cast(tuple[object, ...], value)
        if not 1 <= len(typed_value) <= maximum:
            raise ValueError(
                f"{field_name} must contain between 1 and {maximum} entries"
            )
        if not all(isinstance(item, TransformationSubject) for item in typed_value):
            raise ValueError(
                f"{field_name} entries must be TransformationSubject values in "
                "Python input"
            )
        return typed_value

    @field_validator("lossiness", mode="before")
    @classmethod
    def _require_typed_python_lossiness(
        cls,
        value: object,
        info: ValidationInfo,
    ) -> object:
        if info.mode == "python" and not isinstance(value, TransformationLossiness):
            raise ValueError(
                "lossiness must be a TransformationLossiness in Python input"
            )
        return value

    @field_validator("reversibility", mode="before")
    @classmethod
    def _require_typed_python_reversibility(
        cls,
        value: object,
        info: ValidationInfo,
    ) -> object:
        if info.mode == "python" and not isinstance(value, TransformationReversibility):
            raise ValueError(
                "reversibility must be a TransformationReversibility in Python input"
            )
        return value

    @field_validator("parameter_record", mode="before")
    @classmethod
    def _require_typed_python_parameter_record(
        cls,
        value: object,
        info: ValidationInfo,
    ) -> object:
        if (
            info.mode == "python"
            and value is not None
            and not isinstance(value, DurableEvidenceRecordReference)
        ):
            raise ValueError(
                "parameter_record must be a DurableEvidenceRecordReference or "
                "None in Python input"
            )
        return value

    @model_validator(mode="after")
    def _validate_subject_sets(self) -> Self:
        input_subjects = set(self.inputs)
        if len(input_subjects) != len(self.inputs):
            raise ValueError("inputs must not contain duplicate subjects")
        output_subjects = set(self.outputs)
        if len(output_subjects) != len(self.outputs):
            raise ValueError("outputs must not contain duplicate subjects")
        if input_subjects == output_subjects:
            raise ValueError("input and output subject sets must not be identical")
        return self


class EvidenceCorrection(_EvidenceRecordBase):
    """Additive correction edge preserving both exact durable records."""

    relationship_kind: Literal["correction"]
    relationship_id: EvidenceRelationId
    target_record: DurableEvidenceRecordReference
    correction_record: DurableEvidenceRecordReference
    recorded_at: AwareDatetime

    @field_validator("relationship_id", mode="before")
    @classmethod
    def _require_typed_python_relationship_id(
        cls,
        value: object,
        info: ValidationInfo,
    ) -> object:
        if info.mode == "python" and not isinstance(value, EvidenceRelationId):
            raise ValueError(
                "relationship_id must be an EvidenceRelationId in Python input"
            )
        return value

    @field_validator("target_record", mode="before")
    @classmethod
    def _require_typed_python_target_record(
        cls,
        value: object,
        info: ValidationInfo,
    ) -> object:
        if info.mode == "python" and not isinstance(
            value, DurableEvidenceRecordReference
        ):
            raise ValueError(
                "target_record must be a DurableEvidenceRecordReference in Python input"
            )
        return value

    @field_validator("correction_record", mode="before")
    @classmethod
    def _require_typed_python_correction_record(
        cls,
        value: object,
        info: ValidationInfo,
    ) -> object:
        if info.mode == "python" and not isinstance(
            value, DurableEvidenceRecordReference
        ):
            raise ValueError(
                "correction_record must be a DurableEvidenceRecordReference in "
                "Python input"
            )
        return value

    @field_validator("recorded_at", mode="before")
    @classmethod
    def _require_asserted_utc_recorded_at_json(
        cls,
        value: object,
        info: ValidationInfo,
    ) -> object:
        return _require_asserted_utc_json(value, info, field_name="recorded_at")

    @field_validator("recorded_at")
    @classmethod
    def _normalize_recorded_at(cls, value: datetime) -> datetime:
        return _normalize_asserted_utc(value, field_name="recorded_at")

    @model_validator(mode="after")
    def _validate_distinct_records(self) -> Self:
        if self.target_record == self.correction_record:
            raise ValueError("target_record and correction_record must be different")
        return self


class EvidenceSupersession(_EvidenceRecordBase):
    """One explicit precedence edge preserving prior and succeeding records."""

    relationship_kind: Literal["supersession"]
    relationship_id: EvidenceRelationId
    superseded_record: DurableEvidenceRecordReference
    superseding_record: DurableEvidenceRecordReference
    recorded_at: AwareDatetime

    @field_validator("relationship_id", mode="before")
    @classmethod
    def _require_typed_python_relationship_id(
        cls,
        value: object,
        info: ValidationInfo,
    ) -> object:
        if info.mode == "python" and not isinstance(value, EvidenceRelationId):
            raise ValueError(
                "relationship_id must be an EvidenceRelationId in Python input"
            )
        return value

    @field_validator("superseded_record", mode="before")
    @classmethod
    def _require_typed_python_superseded_record(
        cls,
        value: object,
        info: ValidationInfo,
    ) -> object:
        if info.mode == "python" and not isinstance(
            value, DurableEvidenceRecordReference
        ):
            raise ValueError(
                "superseded_record must be a DurableEvidenceRecordReference in "
                "Python input"
            )
        return value

    @field_validator("superseding_record", mode="before")
    @classmethod
    def _require_typed_python_superseding_record(
        cls,
        value: object,
        info: ValidationInfo,
    ) -> object:
        if info.mode == "python" and not isinstance(
            value, DurableEvidenceRecordReference
        ):
            raise ValueError(
                "superseding_record must be a DurableEvidenceRecordReference in "
                "Python input"
            )
        return value

    @field_validator("recorded_at", mode="before")
    @classmethod
    def _require_asserted_utc_recorded_at_json(
        cls,
        value: object,
        info: ValidationInfo,
    ) -> object:
        return _require_asserted_utc_json(value, info, field_name="recorded_at")

    @field_validator("recorded_at")
    @classmethod
    def _normalize_recorded_at(cls, value: datetime) -> datetime:
        return _normalize_asserted_utc(value, field_name="recorded_at")

    @model_validator(mode="after")
    def _validate_distinct_records(self) -> Self:
        if self.superseded_record == self.superseding_record:
            raise ValueError(
                "superseded_record and superseding_record must be different"
            )
        return self


type EvidenceRecordRelationship = Annotated[
    EvidenceCorrection | EvidenceSupersession,
    Field(discriminator="relationship_kind"),
]


class EvidenceScopeId(RootModel[_EvidenceScopeIdValue]):
    """Bounded identifier for one explicitly declared completeness scope."""

    model_config = ConfigDict(
        frozen=True,
        strict=True,
        revalidate_instances="always",
        validate_default=True,
    )

    root: _EvidenceScopeIdValue

    @field_validator("root")
    @classmethod
    def _validate_scope_id(cls, value: str) -> str:
        if not value.isascii() or _EVIDENCE_SCOPE_ID_PATTERN.fullmatch(value) is None:
            raise ValueError(
                "evidence scope ID must begin and end with a lowercase ASCII "
                "letter or digit and contain only lowercase ASCII letters, "
                "digits, hyphens, underscores, or dots"
            )
        return value


class EvidenceRequirementId(RootModel[_EvidenceRequirementIdValue]):
    """Bounded identifier for one requirement inside a declared scope."""

    model_config = ConfigDict(
        frozen=True,
        strict=True,
        revalidate_instances="always",
        validate_default=True,
    )

    root: _EvidenceRequirementIdValue

    @field_validator("root")
    @classmethod
    def _validate_requirement_id(cls, value: str) -> str:
        if (
            not value.isascii()
            or _EVIDENCE_REQUIREMENT_ID_PATTERN.fullmatch(value) is None
        ):
            raise ValueError(
                "evidence requirement ID must begin and end with a lowercase "
                "ASCII letter or digit and contain only lowercase ASCII letters, "
                "digits, hyphens, underscores, or dots"
            )
        return value


class EvidenceDispositionReason(RootModel[_EvidenceDispositionReasonValue]):
    """Bounded reason code for an explicit evidence disposition."""

    model_config = ConfigDict(
        frozen=True,
        strict=True,
        revalidate_instances="always",
        validate_default=True,
    )

    root: _EvidenceDispositionReasonValue

    @field_validator("root")
    @classmethod
    def _validate_disposition_reason(cls, value: str) -> str:
        if (
            not value.isascii()
            or _EVIDENCE_DISPOSITION_REASON_PATTERN.fullmatch(value) is None
        ):
            raise ValueError(
                "evidence disposition reason must begin and end with a lowercase "
                "ASCII letter or digit and contain only lowercase ASCII letters, "
                "digits, or interior hyphens"
            )
        return value


class EvidenceRequirementOutcome(StrEnum):
    """Explicit outcome for one declared evidence requirement."""

    SATISFIED = "satisfied"
    INTENTIONALLY_OMITTED = "intentionally_omitted"
    UNAVAILABLE = "unavailable"
    INACCESSIBLE = "inaccessible"
    UNKNOWN = "unknown"
    UNSUPPORTED = "unsupported"
    NOT_APPLICABLE = "not_applicable"


_OMISSION_OUTCOMES: frozenset[EvidenceRequirementOutcome] = frozenset(
    {
        EvidenceRequirementOutcome.INTENTIONALLY_OMITTED,
        EvidenceRequirementOutcome.UNAVAILABLE,
        EvidenceRequirementOutcome.INACCESSIBLE,
        EvidenceRequirementOutcome.UNKNOWN,
        EvidenceRequirementOutcome.UNSUPPORTED,
    }
)


class EvidenceOmission(_EvidenceRecordBase):
    """Structured disposition for one omitted or unobtainable requirement."""

    omission_id: EvidenceRelationId
    requirement_id: EvidenceRequirementId
    outcome: EvidenceRequirementOutcome
    reason: EvidenceDispositionReason
    source_records: tuple[DurableEvidenceRecordReference, ...]

    @field_validator("omission_id", mode="before")
    @classmethod
    def _require_typed_python_omission_id(
        cls,
        value: object,
        info: ValidationInfo,
    ) -> object:
        if info.mode == "python" and not isinstance(value, EvidenceRelationId):
            raise ValueError(
                "omission_id must be an EvidenceRelationId in Python input"
            )
        return value

    @field_validator("requirement_id", mode="before")
    @classmethod
    def _require_typed_python_requirement_id(
        cls,
        value: object,
        info: ValidationInfo,
    ) -> object:
        if info.mode == "python" and not isinstance(value, EvidenceRequirementId):
            raise ValueError(
                "requirement_id must be an EvidenceRequirementId in Python input"
            )
        return value

    @field_validator("outcome", mode="before")
    @classmethod
    def _require_typed_python_outcome(
        cls,
        value: object,
        info: ValidationInfo,
    ) -> object:
        if info.mode == "python" and not isinstance(value, EvidenceRequirementOutcome):
            raise ValueError(
                "outcome must be an EvidenceRequirementOutcome in Python input"
            )
        return value

    @field_validator("reason", mode="before")
    @classmethod
    def _require_typed_python_reason(
        cls,
        value: object,
        info: ValidationInfo,
    ) -> object:
        if info.mode == "python" and not isinstance(value, EvidenceDispositionReason):
            raise ValueError(
                "reason must be an EvidenceDispositionReason in Python input"
            )
        return value

    @field_validator("source_records", mode="before")
    @classmethod
    def _require_bounded_typed_source_records(
        cls,
        value: object,
        info: ValidationInfo,
    ) -> object:
        if info.mode == "json":
            if isinstance(value, list):
                raw_value = cast(list[object], value)
                if len(raw_value) > _MAX_OMISSION_SOURCE_RECORDS:
                    raise ValueError(
                        "source_records must contain at most "
                        f"{_MAX_OMISSION_SOURCE_RECORDS} entries"
                    )
                if not raw_value:
                    raise ValueError("source_records must contain at least one entry")
                return tuple(raw_value)
            return value
        if info.mode != "python":
            return value
        if isinstance(value, list):
            raw_list = cast(list[object], value)
            if len(raw_list) > _MAX_OMISSION_SOURCE_RECORDS:
                raise ValueError(
                    "source_records must contain at most "
                    f"{_MAX_OMISSION_SOURCE_RECORDS} entries"
                )
            raise ValueError("source_records must be a tuple in Python input")
        if type(value) is not tuple:
            raise ValueError("source_records must be a tuple in Python input")
        typed_value = cast(tuple[object, ...], value)
        if len(typed_value) > _MAX_OMISSION_SOURCE_RECORDS:
            raise ValueError(
                "source_records must contain at most "
                f"{_MAX_OMISSION_SOURCE_RECORDS} entries"
            )
        if not typed_value:
            raise ValueError("source_records must contain at least one entry")
        if not all(
            isinstance(item, DurableEvidenceRecordReference) for item in typed_value
        ):
            raise ValueError(
                "source_records entries must be DurableEvidenceRecordReference "
                "values in Python input"
            )
        return typed_value

    @model_validator(mode="after")
    def _validate_omission(self) -> Self:
        if self.outcome not in _OMISSION_OUTCOMES:
            raise ValueError(
                "omission outcome must be intentionally_omitted, unavailable, "
                "inaccessible, unknown, or unsupported"
            )
        if len(set(self.source_records)) != len(self.source_records):
            raise ValueError("source_records must not contain duplicate records")
        return self


class EvidenceRequirementResult(_EvidenceRecordBase):
    """One explicit requirement outcome with its permitted supporting shape."""

    requirement_id: EvidenceRequirementId
    outcome: EvidenceRequirementOutcome
    evidence_records: tuple[DurableEvidenceRecordReference, ...] | None
    omission: EvidenceOmission | None

    @field_validator("requirement_id", mode="before")
    @classmethod
    def _require_typed_python_requirement_id(
        cls,
        value: object,
        info: ValidationInfo,
    ) -> object:
        if info.mode == "python" and not isinstance(value, EvidenceRequirementId):
            raise ValueError(
                "requirement_id must be an EvidenceRequirementId in Python input"
            )
        return value

    @field_validator("outcome", mode="before")
    @classmethod
    def _require_typed_python_outcome(
        cls,
        value: object,
        info: ValidationInfo,
    ) -> object:
        if info.mode == "python" and not isinstance(value, EvidenceRequirementOutcome):
            raise ValueError(
                "outcome must be an EvidenceRequirementOutcome in Python input"
            )
        return value

    @field_validator("evidence_records", mode="before")
    @classmethod
    def _require_bounded_typed_evidence_records(
        cls,
        value: object,
        info: ValidationInfo,
    ) -> object:
        if value is None:
            return value
        if info.mode == "json":
            if isinstance(value, list):
                raw_value = cast(list[object], value)
                if len(raw_value) > _MAX_EVIDENCE_RECORDS_PER_REQUIREMENT:
                    raise ValueError(
                        "evidence_records must contain at most "
                        f"{_MAX_EVIDENCE_RECORDS_PER_REQUIREMENT} entries"
                    )
                if not raw_value:
                    raise ValueError(
                        "evidence_records must contain at least one entry when present"
                    )
                return tuple(raw_value)
            return value
        if info.mode != "python":
            return value
        if isinstance(value, list):
            raw_list = cast(list[object], value)
            if len(raw_list) > _MAX_EVIDENCE_RECORDS_PER_REQUIREMENT:
                raise ValueError(
                    "evidence_records must contain at most "
                    f"{_MAX_EVIDENCE_RECORDS_PER_REQUIREMENT} entries"
                )
            raise ValueError("evidence_records must be a tuple or None in Python input")
        if type(value) is not tuple:
            raise ValueError("evidence_records must be a tuple or None in Python input")
        typed_value = cast(tuple[object, ...], value)
        if len(typed_value) > _MAX_EVIDENCE_RECORDS_PER_REQUIREMENT:
            raise ValueError(
                "evidence_records must contain at most "
                f"{_MAX_EVIDENCE_RECORDS_PER_REQUIREMENT} entries"
            )
        if not typed_value:
            raise ValueError(
                "evidence_records must contain at least one entry when present"
            )
        if not all(
            isinstance(item, DurableEvidenceRecordReference) for item in typed_value
        ):
            raise ValueError(
                "evidence_records entries must be DurableEvidenceRecordReference "
                "values in Python input"
            )
        return typed_value

    @field_validator("omission", mode="before")
    @classmethod
    def _require_typed_python_omission(
        cls,
        value: object,
        info: ValidationInfo,
    ) -> object:
        if (
            info.mode == "python"
            and value is not None
            and not isinstance(value, EvidenceOmission)
        ):
            raise ValueError(
                "omission must be an EvidenceOmission or None in Python input"
            )
        return value

    @model_validator(mode="after")
    def _validate_outcome_shape(self) -> Self:
        if self.evidence_records is not None and len(set(self.evidence_records)) != len(
            self.evidence_records
        ):
            raise ValueError("evidence_records must not contain duplicate records")
        if self.outcome is EvidenceRequirementOutcome.SATISFIED:
            if self.evidence_records is None or self.omission is not None:
                raise ValueError(
                    "satisfied outcome requires evidence_records and no omission"
                )
            return self
        if self.outcome in _OMISSION_OUTCOMES:
            if self.evidence_records is not None or self.omission is None:
                raise ValueError(
                    "omission outcome requires omission and no evidence_records"
                )
            if self.omission.requirement_id != self.requirement_id:
                raise ValueError(
                    "omission requirement_id must match result requirement_id"
                )
            if self.omission.outcome is not self.outcome:
                raise ValueError("omission outcome must match result outcome")
            return self
        if self.evidence_records is not None or self.omission is not None:
            raise ValueError(
                "not_applicable outcome requires no evidence_records and no omission"
            )
        return self


class EvidenceCompletenessStatus(StrEnum):
    """Status derived only from outcomes in one explicit evidence scope."""

    SCOPE_SATISFIED = "scope_satisfied"
    SCOPE_SATISFIED_WITH_DECLARED_OMISSIONS = "scope_satisfied_with_declared_omissions"
    SCOPE_PARTIAL = "scope_partial"
    SCOPE_UNKNOWN = "scope_unknown"


_PARTIAL_OUTCOMES: frozenset[EvidenceRequirementOutcome] = frozenset(
    {
        EvidenceRequirementOutcome.UNAVAILABLE,
        EvidenceRequirementOutcome.INACCESSIBLE,
        EvidenceRequirementOutcome.UNSUPPORTED,
    }
)


class EvidenceCompletenessAssessment(_EvidenceRecordBase):
    """Immutable completeness assessment over every requirement in one scope."""

    assessment_id: EvidenceRelationId
    subject_record: DurableEvidenceRecordReference
    scope_id: EvidenceScopeId
    assessed_at: AwareDatetime
    status: EvidenceCompletenessStatus
    requirements: tuple[EvidenceRequirementResult, ...]

    @field_validator("assessment_id", mode="before")
    @classmethod
    def _require_typed_python_assessment_id(
        cls,
        value: object,
        info: ValidationInfo,
    ) -> object:
        if info.mode == "python" and not isinstance(value, EvidenceRelationId):
            raise ValueError(
                "assessment_id must be an EvidenceRelationId in Python input"
            )
        return value

    @field_validator("subject_record", mode="before")
    @classmethod
    def _require_typed_python_subject_record(
        cls,
        value: object,
        info: ValidationInfo,
    ) -> object:
        if info.mode == "python" and not isinstance(
            value, DurableEvidenceRecordReference
        ):
            raise ValueError(
                "subject_record must be a DurableEvidenceRecordReference in "
                "Python input"
            )
        return value

    @field_validator("scope_id", mode="before")
    @classmethod
    def _require_typed_python_scope_id(
        cls,
        value: object,
        info: ValidationInfo,
    ) -> object:
        if info.mode == "python" and not isinstance(value, EvidenceScopeId):
            raise ValueError("scope_id must be an EvidenceScopeId in Python input")
        return value

    @field_validator("assessed_at", mode="before")
    @classmethod
    def _require_asserted_utc_assessed_at_json(
        cls,
        value: object,
        info: ValidationInfo,
    ) -> object:
        return _require_asserted_utc_json(value, info, field_name="assessed_at")

    @field_validator("assessed_at")
    @classmethod
    def _normalize_assessed_at(cls, value: datetime) -> datetime:
        return _normalize_asserted_utc(value, field_name="assessed_at")

    @field_validator("status", mode="before")
    @classmethod
    def _require_typed_python_status(
        cls,
        value: object,
        info: ValidationInfo,
    ) -> object:
        if info.mode == "python" and not isinstance(value, EvidenceCompletenessStatus):
            raise ValueError(
                "status must be an EvidenceCompletenessStatus in Python input"
            )
        return value

    @field_validator("requirements", mode="before")
    @classmethod
    def _require_bounded_typed_requirements(
        cls,
        value: object,
        info: ValidationInfo,
    ) -> object:
        if info.mode == "json":
            if isinstance(value, list):
                raw_value = cast(list[object], value)
                if len(raw_value) > _MAX_REQUIREMENTS_PER_ASSESSMENT:
                    raise ValueError(
                        "requirements must contain at most "
                        f"{_MAX_REQUIREMENTS_PER_ASSESSMENT} entries"
                    )
                if not raw_value:
                    raise ValueError("requirements must contain at least one entry")
                return tuple(raw_value)
            return value
        if info.mode != "python":
            return value
        if isinstance(value, list):
            raw_list = cast(list[object], value)
            if len(raw_list) > _MAX_REQUIREMENTS_PER_ASSESSMENT:
                raise ValueError(
                    "requirements must contain at most "
                    f"{_MAX_REQUIREMENTS_PER_ASSESSMENT} entries"
                )
            raise ValueError("requirements must be a tuple in Python input")
        if type(value) is not tuple:
            raise ValueError("requirements must be a tuple in Python input")
        typed_value = cast(tuple[object, ...], value)
        if len(typed_value) > _MAX_REQUIREMENTS_PER_ASSESSMENT:
            raise ValueError(
                "requirements must contain at most "
                f"{_MAX_REQUIREMENTS_PER_ASSESSMENT} entries"
            )
        if not typed_value:
            raise ValueError("requirements must contain at least one entry")
        if not all(isinstance(item, EvidenceRequirementResult) for item in typed_value):
            raise ValueError(
                "requirements entries must be EvidenceRequirementResult values "
                "in Python input"
            )
        return typed_value

    @model_validator(mode="after")
    def _validate_requirements_and_status(self) -> Self:
        requirement_ids = tuple(
            requirement.requirement_id for requirement in self.requirements
        )
        if len(set(requirement_ids)) != len(requirement_ids):
            raise ValueError("requirements must use unique requirement IDs")

        outcomes = frozenset(requirement.outcome for requirement in self.requirements)
        if EvidenceRequirementOutcome.UNKNOWN in outcomes:
            expected_status = EvidenceCompletenessStatus.SCOPE_UNKNOWN
        elif outcomes & _PARTIAL_OUTCOMES:
            expected_status = EvidenceCompletenessStatus.SCOPE_PARTIAL
        elif EvidenceRequirementOutcome.INTENTIONALLY_OMITTED in outcomes:
            expected_status = (
                EvidenceCompletenessStatus.SCOPE_SATISFIED_WITH_DECLARED_OMISSIONS
            )
        else:
            expected_status = EvidenceCompletenessStatus.SCOPE_SATISFIED
        if self.status is not expected_status:
            raise ValueError(
                "status is inconsistent with the explicit requirement outcomes"
            )
        return self


class EvidencePublicationMethod(StrEnum):
    """Observed method by which an evidence record was published."""

    PROTECTED_PULL_REQUEST_SQUASH_MERGE = "protected_pull_request_squash_merge"


class PublicationCheckEvent(StrEnum):
    """GitHub event that produced one successful publication check."""

    PULL_REQUEST = "pull_request"
    PUSH = "push"


class PublicationCheckName(RootModel[_PublicationCheckNameValue]):
    """Exact printable ASCII workflow or check-context name."""

    model_config = ConfigDict(
        frozen=True,
        strict=True,
        revalidate_instances="always",
        validate_default=True,
    )

    root: _PublicationCheckNameValue

    @field_validator("root")
    @classmethod
    def _validate_check_name(cls, value: str) -> str:
        if not value.isascii() or value != value.strip() or _has_ascii_control(value):
            raise ValueError("publication check name must be unpadded printable ASCII")
        return value


class SuccessfulPublicationCheck(_EvidenceRecordBase):
    """One successful, observed CI check without execution behavior."""

    authority: ProviderAuthority
    workflow_name: PublicationCheckName
    context: PublicationCheckName
    event: PublicationCheckEvent
    run_id: ProviderGlobalId
    job_id: ProviderGlobalId
    attempt: int
    head_revision: GitCommitIdentity
    conclusion: Literal["success"]

    @field_validator("authority", mode="before")
    @classmethod
    def _require_typed_python_authority(
        cls,
        value: object,
        info: ValidationInfo,
    ) -> object:
        if info.mode == "python" and not isinstance(value, ProviderAuthority):
            raise ValueError("authority must be a ProviderAuthority in Python input")
        return value

    @field_validator("authority")
    @classmethod
    def _require_retrieval_authority(
        cls,
        value: ProviderAuthority,
    ) -> ProviderAuthority:
        if value.role is not AuthorityRole.RETRIEVAL:
            raise ValueError("authority role must be retrieval")
        return value

    @field_validator("workflow_name", "context", mode="before")
    @classmethod
    def _require_typed_python_check_names(
        cls,
        value: object,
        info: ValidationInfo,
    ) -> object:
        if info.mode == "python" and not isinstance(value, PublicationCheckName):
            field_name = info.field_name or "check name"
            raise ValueError(
                f"{field_name} must be a PublicationCheckName in Python input"
            )
        return value

    @field_validator("event", mode="before")
    @classmethod
    def _require_typed_python_event(
        cls,
        value: object,
        info: ValidationInfo,
    ) -> object:
        if info.mode == "python" and not isinstance(value, PublicationCheckEvent):
            raise ValueError("event must be a PublicationCheckEvent in Python input")
        return value

    @field_validator("run_id", "job_id", mode="before")
    @classmethod
    def _require_typed_python_provider_ids(
        cls,
        value: object,
        info: ValidationInfo,
    ) -> object:
        if info.mode == "python" and not isinstance(value, ProviderGlobalId):
            field_name = info.field_name or "provider ID"
            raise ValueError(f"{field_name} must be a ProviderGlobalId in Python input")
        return value

    @field_validator("attempt", mode="before")
    @classmethod
    def _validate_attempt(cls, value: object) -> object:
        if type(value) is not int:
            raise ValueError("attempt must be an exact integer")
        if not 1 <= value <= _MAX_PUBLICATION_CHECK_ATTEMPT:
            raise ValueError(
                "attempt must be between 1 and "
                f"{_MAX_PUBLICATION_CHECK_ATTEMPT} inclusive"
            )
        return value

    @field_validator("head_revision", mode="before")
    @classmethod
    def _require_typed_python_head_revision(
        cls,
        value: object,
        info: ValidationInfo,
    ) -> object:
        if info.mode == "python" and not isinstance(value, GitCommitIdentity):
            raise ValueError(
                "head_revision must be a GitCommitIdentity in Python input"
            )
        return value


class EvidencePublication(_EvidenceRecordBase):
    """Protected-PR publication provenance for one exact durable record."""

    publication_id: EvidenceRelationId
    subject_record: DurableEvidenceRecordReference
    repository_identity: RepositoryIdentity
    pull_request_identity: NumberedSourceObjectIdentity
    reviewed_revision: GitCommitIdentity
    reviewed_tree: GitTreeIdentity
    published_revision: GitCommitIdentity
    published_tree: GitTreeIdentity
    method: EvidencePublicationMethod
    published_at: AwareDatetime
    pull_request_check: SuccessfulPublicationCheck
    main_check: SuccessfulPublicationCheck

    @field_validator("publication_id", mode="before")
    @classmethod
    def _require_typed_python_publication_id(
        cls,
        value: object,
        info: ValidationInfo,
    ) -> object:
        if info.mode == "python" and not isinstance(value, EvidenceRelationId):
            raise ValueError(
                "publication_id must be an EvidenceRelationId in Python input"
            )
        return value

    @field_validator("subject_record", mode="before")
    @classmethod
    def _require_typed_python_subject_record(
        cls,
        value: object,
        info: ValidationInfo,
    ) -> object:
        if info.mode == "python" and not isinstance(
            value, DurableEvidenceRecordReference
        ):
            raise ValueError(
                "subject_record must be a DurableEvidenceRecordReference in "
                "Python input"
            )
        return value

    @field_validator("repository_identity", mode="before")
    @classmethod
    def _require_typed_python_repository_identity(
        cls,
        value: object,
        info: ValidationInfo,
    ) -> object:
        if info.mode == "python" and not isinstance(value, RepositoryIdentity):
            raise ValueError(
                "repository_identity must be a RepositoryIdentity in Python input"
            )
        return value

    @field_validator("pull_request_identity", mode="before")
    @classmethod
    def _require_typed_python_pull_request_identity(
        cls,
        value: object,
        info: ValidationInfo,
    ) -> object:
        if info.mode == "python" and not isinstance(
            value, NumberedSourceObjectIdentity
        ):
            raise ValueError(
                "pull_request_identity must be a NumberedSourceObjectIdentity "
                "in Python input"
            )
        return value

    @field_validator("reviewed_revision", "published_revision", mode="before")
    @classmethod
    def _require_typed_python_revisions(
        cls,
        value: object,
        info: ValidationInfo,
    ) -> object:
        if info.mode == "python" and not isinstance(value, GitCommitIdentity):
            field_name = info.field_name or "revision"
            raise ValueError(
                f"{field_name} must be a GitCommitIdentity in Python input"
            )
        return value

    @field_validator("reviewed_tree", "published_tree", mode="before")
    @classmethod
    def _require_typed_python_trees(
        cls,
        value: object,
        info: ValidationInfo,
    ) -> object:
        if info.mode == "python" and not isinstance(value, GitTreeIdentity):
            field_name = info.field_name or "tree"
            raise ValueError(f"{field_name} must be a GitTreeIdentity in Python input")
        return value

    @field_validator("method", mode="before")
    @classmethod
    def _require_typed_python_method(
        cls,
        value: object,
        info: ValidationInfo,
    ) -> object:
        if info.mode == "python" and not isinstance(value, EvidencePublicationMethod):
            raise ValueError(
                "method must be an EvidencePublicationMethod in Python input"
            )
        return value

    @field_validator("published_at", mode="before")
    @classmethod
    def _require_asserted_utc_published_at_json(
        cls,
        value: object,
        info: ValidationInfo,
    ) -> object:
        return _require_asserted_utc_json(value, info, field_name="published_at")

    @field_validator("published_at")
    @classmethod
    def _normalize_published_at(cls, value: datetime) -> datetime:
        return _normalize_asserted_utc(value, field_name="published_at")

    @field_validator("pull_request_check", "main_check", mode="before")
    @classmethod
    def _require_typed_python_checks(
        cls,
        value: object,
        info: ValidationInfo,
    ) -> object:
        if info.mode == "python" and not isinstance(value, SuccessfulPublicationCheck):
            field_name = info.field_name or "check"
            raise ValueError(
                f"{field_name} must be a SuccessfulPublicationCheck in Python input"
            )
        return value

    @model_validator(mode="after")
    def _validate_publication_bindings(self) -> Self:
        if self.pull_request_identity.kind is not SourceObjectKind.PULL_REQUEST:
            raise ValueError("pull_request_identity kind must be pull_request")
        if self.pull_request_identity.repository_identity != self.repository_identity:
            raise ValueError(
                "pull_request_identity repository must match repository_identity"
            )
        if (
            self.pull_request_check.authority.provider
            != self.repository_identity.provider
            or self.main_check.authority.provider != self.repository_identity.provider
        ):
            raise ValueError(
                "publication check authority providers must match repository provider"
            )
        if self.pull_request_check.event is not PublicationCheckEvent.PULL_REQUEST:
            raise ValueError("pull_request_check event must be pull_request")
        if self.main_check.event is not PublicationCheckEvent.PUSH:
            raise ValueError("main_check event must be push")
        if self.pull_request_check.run_id == self.main_check.run_id:
            raise ValueError(
                "pull_request_check and main_check run_id values must differ"
            )
        if self.pull_request_check.job_id == self.main_check.job_id:
            raise ValueError(
                "pull_request_check and main_check job_id values must differ"
            )
        if self.pull_request_check.head_revision != self.reviewed_revision:
            raise ValueError(
                "pull_request_check head_revision must equal reviewed_revision"
            )
        if self.main_check.head_revision != self.published_revision:
            raise ValueError("main_check head_revision must equal published_revision")
        if self.reviewed_revision == self.published_revision:
            raise ValueError("reviewed_revision and published_revision must differ")
        algorithms = {
            self.reviewed_revision.algorithm,
            self.reviewed_tree.algorithm,
            self.published_revision.algorithm,
            self.published_tree.algorithm,
        }
        if len(algorithms) != 1:
            raise ValueError(
                "reviewed and published commit and tree hash algorithms must match"
            )
        if self.reviewed_tree != self.published_tree:
            raise ValueError("reviewed_tree must equal published_tree")
        return self


class EvidenceEnvelope(_EvidenceRecordBase):
    """Bounded composition of already-typed legacy and modern evidence records."""

    legacy_snapshots: tuple[ArtifactSnapshot, ...] | None
    request_memberships: tuple[AcquisitionRequestMembership, ...] | None
    acquisition_runs: tuple[AcquisitionRun, ...] | None
    transformations: tuple[EvidenceTransformation, ...] | None
    record_relationships: tuple[EvidenceRecordRelationship, ...] | None
    completeness_assessments: tuple[EvidenceCompletenessAssessment, ...] | None
    publications: tuple[EvidencePublication, ...] | None

    @field_validator(
        "legacy_snapshots",
        "request_memberships",
        "acquisition_runs",
        "transformations",
        "record_relationships",
        "completeness_assessments",
        "publications",
        mode="before",
    )
    @classmethod
    def _require_bounded_typed_component_tuple(
        cls,
        value: object,
        info: ValidationInfo,
    ) -> object:
        if value is None:
            return value

        field_name = info.field_name or "component collection"
        maximum: int
        expected_type: type[BaseModel] | tuple[type[BaseModel], ...]
        expected_name: str
        if field_name == "legacy_snapshots":
            maximum = _MAX_ENVELOPE_LEGACY_SNAPSHOTS
            expected_type = ArtifactSnapshot
            expected_name = "ArtifactSnapshot"
        elif field_name == "request_memberships":
            maximum = _MAX_ENVELOPE_REQUEST_MEMBERSHIPS
            expected_type = AcquisitionRequestMembership
            expected_name = "AcquisitionRequestMembership"
        elif field_name == "acquisition_runs":
            maximum = _MAX_ENVELOPE_ACQUISITION_RUNS
            expected_type = AcquisitionRun
            expected_name = "AcquisitionRun"
        elif field_name == "transformations":
            maximum = _MAX_ENVELOPE_TRANSFORMATIONS
            expected_type = EvidenceTransformation
            expected_name = "EvidenceTransformation"
        elif field_name == "record_relationships":
            maximum = _MAX_ENVELOPE_RECORD_RELATIONSHIPS
            expected_type = (EvidenceCorrection, EvidenceSupersession)
            expected_name = "EvidenceCorrection or EvidenceSupersession"
        elif field_name == "completeness_assessments":
            maximum = _MAX_ENVELOPE_COMPLETENESS_ASSESSMENTS
            expected_type = EvidenceCompletenessAssessment
            expected_name = "EvidenceCompletenessAssessment"
        elif field_name == "publications":
            maximum = _MAX_ENVELOPE_PUBLICATIONS
            expected_type = EvidencePublication
            expected_name = "EvidencePublication"
        else:
            raise AssertionError("unexpected EvidenceEnvelope component field")

        if info.mode == "json":
            if isinstance(value, list):
                raw_value = cast(list[object], value)
                if len(raw_value) > maximum:
                    raise ValueError(
                        f"{field_name} must contain at most {maximum} entries"
                    )
                if field_name == "legacy_snapshots":
                    return tuple(
                        ArtifactSnapshot.model_validate_json(json.dumps(item))
                        if isinstance(item, dict)
                        else item
                        for item in raw_value
                    )
                return tuple(raw_value)
            return value
        if info.mode != "python":
            return value
        if isinstance(value, list):
            raw_list = cast(list[object], value)
            if len(raw_list) > maximum:
                raise ValueError(f"{field_name} must contain at most {maximum} entries")
            raise ValueError(f"{field_name} must be a tuple or None in Python input")
        if type(value) is not tuple:
            raise ValueError(f"{field_name} must be a tuple or None in Python input")
        typed_value = cast(tuple[object, ...], value)
        if len(typed_value) > maximum:
            raise ValueError(f"{field_name} must contain at most {maximum} entries")
        if not all(isinstance(item, expected_type) for item in typed_value):
            raise ValueError(
                f"{field_name} entries must be {expected_name} values in Python input"
            )
        return typed_value

    @model_validator(mode="after")
    def _validate_composition(self) -> Self:
        components = (
            self.legacy_snapshots,
            self.request_memberships,
            self.acquisition_runs,
            self.transformations,
            self.record_relationships,
            self.completeness_assessments,
            self.publications,
        )
        if not any(component for component in components):
            raise ValueError("evidence envelope must contain at least one record")

        if self.legacy_snapshots is not None and len(set(self.legacy_snapshots)) != len(
            self.legacy_snapshots
        ):
            raise ValueError("legacy_snapshots must not contain duplicate values")

        if self.request_memberships is not None:
            request_ids = tuple(
                membership.request_id for membership in self.request_memberships
            )
            if len(set(request_ids)) != len(request_ids):
                raise ValueError(
                    "request_memberships must use unique request_id values"
                )

        if self.acquisition_runs is not None:
            run_ids = tuple(run.run_id for run in self.acquisition_runs)
            if len(set(run_ids)) != len(run_ids):
                raise ValueError("acquisition_runs must use unique run_id values")

        if self.transformations is not None:
            transformation_ids = tuple(
                transformation.transformation_id
                for transformation in self.transformations
            )
            if len(set(transformation_ids)) != len(transformation_ids):
                raise ValueError(
                    "transformations must use unique transformation_id values"
                )

        if self.record_relationships is not None:
            relationship_ids = tuple(
                (relationship.relationship_kind, relationship.relationship_id)
                for relationship in self.record_relationships
            )
            if len(set(relationship_ids)) != len(relationship_ids):
                raise ValueError(
                    "record_relationships must use unique typed relationship identities"
                )

        if self.completeness_assessments is not None:
            assessment_ids = tuple(
                assessment.assessment_id for assessment in self.completeness_assessments
            )
            if len(set(assessment_ids)) != len(assessment_ids):
                raise ValueError(
                    "completeness_assessments must use unique assessment_id values"
                )

        if self.publications is not None:
            publication_ids = tuple(
                publication.publication_id for publication in self.publications
            )
            if len(set(publication_ids)) != len(publication_ids):
                raise ValueError("publications must use unique publication_id values")

        standalone_request_ids = {
            (
                membership.request_id.acquisition_run_id.root,
                membership.request_id.request_ordinal.root,
            )
            for membership in self.request_memberships or ()
        }
        nested_request_ids = {
            (
                membership.request_id.acquisition_run_id.root,
                membership.request_id.request_ordinal.root,
            )
            for run in self.acquisition_runs or ()
            for membership in run.requests
        }
        if standalone_request_ids & nested_request_ids:
            raise ValueError(
                "a request_id must not appear both as a standalone membership "
                "and inside an acquisition run"
            )
        return self


class LegacyEvidenceCompatibilityReason(StrEnum):
    """Exact reasons why an envelope cannot project losslessly to legacy v1."""

    LEGACY_SNAPSHOT_ABSENT = "legacy_snapshot_absent"
    MULTIPLE_LEGACY_SNAPSHOTS_NOT_REPRESENTABLE = (
        "multiple_legacy_snapshots_not_representable"
    )
    MODERN_COMPONENTS_NOT_REPRESENTABLE = "modern_components_not_representable"


class LegacyArtifactSnapshotEnvelopeMappingResult(_EvidenceRecordBase):
    """Validated lossless wrapping of one legacy ArtifactSnapshot."""

    adapter_id: EvidenceRelationId
    adapter_version: EvidenceVersion
    status: CompatibilityStatus
    source_snapshot: ArtifactSnapshot
    envelope: EvidenceEnvelope
    reasons: tuple[LegacyEvidenceCompatibilityReason, ...]

    @field_validator("adapter_id", mode="before")
    @classmethod
    def _require_typed_python_adapter_id(
        cls,
        value: object,
        info: ValidationInfo,
    ) -> object:
        if info.mode == "python" and not isinstance(value, EvidenceRelationId):
            raise ValueError("adapter_id must be an EvidenceRelationId in Python input")
        return value

    @field_validator("adapter_version", mode="before")
    @classmethod
    def _require_typed_python_adapter_version(
        cls,
        value: object,
        info: ValidationInfo,
    ) -> object:
        if info.mode == "python" and not isinstance(value, EvidenceVersion):
            raise ValueError(
                "adapter_version must be an EvidenceVersion in Python input"
            )
        return value

    @field_validator("status", mode="before")
    @classmethod
    def _require_typed_python_status(
        cls,
        value: object,
        info: ValidationInfo,
    ) -> object:
        if info.mode == "python" and not isinstance(value, CompatibilityStatus):
            raise ValueError("status must be a CompatibilityStatus in Python input")
        return value

    @field_validator("source_snapshot", mode="before")
    @classmethod
    def _require_typed_python_source_snapshot(
        cls,
        value: object,
        info: ValidationInfo,
    ) -> object:
        if info.mode == "json" and isinstance(value, dict):
            return ArtifactSnapshot.model_validate_json(json.dumps(value))
        if info.mode == "python" and not isinstance(value, ArtifactSnapshot):
            raise ValueError(
                "source_snapshot must be an ArtifactSnapshot in Python input"
            )
        return value

    @field_validator("envelope", mode="before")
    @classmethod
    def _require_typed_python_envelope(
        cls,
        value: object,
        info: ValidationInfo,
    ) -> object:
        if info.mode == "python" and not isinstance(value, EvidenceEnvelope):
            raise ValueError("envelope must be an EvidenceEnvelope in Python input")
        return value

    @field_validator("reasons", mode="before")
    @classmethod
    def _require_typed_python_reasons(
        cls,
        value: object,
        info: ValidationInfo,
    ) -> object:
        if info.mode == "json":
            if isinstance(value, list):
                return tuple(cast(list[object], value))
            return value
        if info.mode != "python":
            return value
        if type(value) is not tuple:
            raise ValueError("reasons must be a tuple in Python input")
        typed_value = cast(tuple[object, ...], value)
        if not all(
            isinstance(item, LegacyEvidenceCompatibilityReason) for item in typed_value
        ):
            raise ValueError(
                "reasons entries must be LegacyEvidenceCompatibilityReason "
                "values in Python input"
            )
        return typed_value

    @model_validator(mode="after")
    def _validate_mapping(self) -> Self:
        if self.adapter_id.root != _LEGACY_ARTIFACT_SNAPSHOT_ADAPTER_ID:
            raise ValueError("adapter_id must identify the canonical legacy adapter")
        if self.adapter_version.root != _LEGACY_ARTIFACT_SNAPSHOT_ADAPTER_VERSION:
            raise ValueError("adapter_version must be the canonical adapter version")
        if self.status is not CompatibilityStatus.LOSSLESSLY_MAPPABLE:
            raise ValueError("legacy snapshot wrapping must be losslessly_mappable")
        if self.reasons:
            raise ValueError("lossless legacy snapshot wrapping must have no reasons")
        if self.envelope.legacy_snapshots != (self.source_snapshot,):
            raise ValueError(
                "envelope must preserve exactly the source legacy snapshot"
            )
        modern_components = (
            self.envelope.request_memberships,
            self.envelope.acquisition_runs,
            self.envelope.transformations,
            self.envelope.record_relationships,
            self.envelope.completeness_assessments,
            self.envelope.publications,
        )
        if any(component is not None for component in modern_components):
            raise ValueError(
                "legacy snapshot wrapping must leave every modern component "
                "unrepresented"
            )
        return self


class LegacyArtifactSnapshotProjectionResult(_EvidenceRecordBase):
    """Validated fail-closed projection from an envelope to legacy v1."""

    adapter_id: EvidenceRelationId
    adapter_version: EvidenceVersion
    status: CompatibilityStatus
    source_envelope: EvidenceEnvelope
    projected_snapshot: ArtifactSnapshot | None
    reasons: tuple[LegacyEvidenceCompatibilityReason, ...]

    @field_validator("adapter_id", mode="before")
    @classmethod
    def _require_typed_python_adapter_id(
        cls,
        value: object,
        info: ValidationInfo,
    ) -> object:
        if info.mode == "python" and not isinstance(value, EvidenceRelationId):
            raise ValueError("adapter_id must be an EvidenceRelationId in Python input")
        return value

    @field_validator("adapter_version", mode="before")
    @classmethod
    def _require_typed_python_adapter_version(
        cls,
        value: object,
        info: ValidationInfo,
    ) -> object:
        if info.mode == "python" and not isinstance(value, EvidenceVersion):
            raise ValueError(
                "adapter_version must be an EvidenceVersion in Python input"
            )
        return value

    @field_validator("status", mode="before")
    @classmethod
    def _require_typed_python_status(
        cls,
        value: object,
        info: ValidationInfo,
    ) -> object:
        if info.mode == "python" and not isinstance(value, CompatibilityStatus):
            raise ValueError("status must be a CompatibilityStatus in Python input")
        return value

    @field_validator("source_envelope", mode="before")
    @classmethod
    def _require_typed_python_source_envelope(
        cls,
        value: object,
        info: ValidationInfo,
    ) -> object:
        if info.mode == "python" and not isinstance(value, EvidenceEnvelope):
            raise ValueError(
                "source_envelope must be an EvidenceEnvelope in Python input"
            )
        return value

    @field_validator("projected_snapshot", mode="before")
    @classmethod
    def _require_typed_python_projected_snapshot(
        cls,
        value: object,
        info: ValidationInfo,
    ) -> object:
        if info.mode == "json" and isinstance(value, dict):
            return ArtifactSnapshot.model_validate_json(json.dumps(value))
        if (
            info.mode == "python"
            and value is not None
            and not isinstance(value, ArtifactSnapshot)
        ):
            raise ValueError(
                "projected_snapshot must be an ArtifactSnapshot or None in Python input"
            )
        return value

    @field_validator("reasons", mode="before")
    @classmethod
    def _require_typed_python_reasons(
        cls,
        value: object,
        info: ValidationInfo,
    ) -> object:
        if info.mode == "json":
            if isinstance(value, list):
                return tuple(cast(list[object], value))
            return value
        if info.mode != "python":
            return value
        if type(value) is not tuple:
            raise ValueError("reasons must be a tuple in Python input")
        typed_value = cast(tuple[object, ...], value)
        if not all(
            isinstance(item, LegacyEvidenceCompatibilityReason) for item in typed_value
        ):
            raise ValueError(
                "reasons entries must be LegacyEvidenceCompatibilityReason "
                "values in Python input"
            )
        return typed_value

    @model_validator(mode="after")
    def _validate_projection(self) -> Self:
        if self.adapter_id.root != _LEGACY_ARTIFACT_SNAPSHOT_ADAPTER_ID:
            raise ValueError("adapter_id must identify the canonical legacy adapter")
        if self.adapter_version.root != _LEGACY_ARTIFACT_SNAPSHOT_ADAPTER_VERSION:
            raise ValueError("adapter_version must be the canonical adapter version")

        legacy_snapshots = self.source_envelope.legacy_snapshots
        modern_components = (
            self.source_envelope.request_memberships,
            self.source_envelope.acquisition_runs,
            self.source_envelope.transformations,
            self.source_envelope.record_relationships,
            self.source_envelope.completeness_assessments,
            self.source_envelope.publications,
        )
        expected_status: CompatibilityStatus
        expected_snapshot: ArtifactSnapshot | None
        expected_reasons: tuple[LegacyEvidenceCompatibilityReason, ...]
        if legacy_snapshots is None or len(legacy_snapshots) == 0:
            expected_status = CompatibilityStatus.NOT_MAPPABLE
            expected_snapshot = None
            expected_reasons = (
                LegacyEvidenceCompatibilityReason.LEGACY_SNAPSHOT_ABSENT,
            )
        elif len(legacy_snapshots) > 1:
            expected_status = CompatibilityStatus.NOT_MAPPABLE
            expected_snapshot = None
            expected_reasons = (
                LegacyEvidenceCompatibilityReason.MULTIPLE_LEGACY_SNAPSHOTS_NOT_REPRESENTABLE,
            )
        elif any(component is not None for component in modern_components):
            expected_status = CompatibilityStatus.PARTIALLY_MAPPABLE
            expected_snapshot = None
            expected_reasons = (
                LegacyEvidenceCompatibilityReason.MODERN_COMPONENTS_NOT_REPRESENTABLE,
            )
        else:
            expected_status = CompatibilityStatus.LOSSLESSLY_MAPPABLE
            expected_snapshot = legacy_snapshots[0]
            expected_reasons = ()

        if self.status is not expected_status:
            raise ValueError("projection status does not match the source envelope")
        if self.projected_snapshot != expected_snapshot:
            raise ValueError("projected_snapshot does not match the source envelope")
        if self.reasons != expected_reasons:
            raise ValueError("projection reasons do not match the source envelope")
        return self


def wrap_legacy_artifact_snapshot(
    source_snapshot: ArtifactSnapshot,
) -> LegacyArtifactSnapshotEnvelopeMappingResult:
    """Preserve one validated legacy snapshot inside an otherwise unknown envelope."""

    if not isinstance(cast(object, source_snapshot), ArtifactSnapshot):
        raise TypeError("source_snapshot must be an ArtifactSnapshot")
    envelope = EvidenceEnvelope(
        legacy_snapshots=(source_snapshot,),
        request_memberships=None,
        acquisition_runs=None,
        transformations=None,
        record_relationships=None,
        completeness_assessments=None,
        publications=None,
    )
    return LegacyArtifactSnapshotEnvelopeMappingResult(
        adapter_id=EvidenceRelationId.model_validate(
            _LEGACY_ARTIFACT_SNAPSHOT_ADAPTER_ID
        ),
        adapter_version=EvidenceVersion.model_validate(
            _LEGACY_ARTIFACT_SNAPSHOT_ADAPTER_VERSION
        ),
        status=CompatibilityStatus.LOSSLESSLY_MAPPABLE,
        source_snapshot=source_snapshot,
        envelope=envelope,
        reasons=(),
    )


def project_evidence_envelope_to_legacy_artifact_snapshot(
    source_envelope: EvidenceEnvelope,
) -> LegacyArtifactSnapshotProjectionResult:
    """Project only an exactly representable legacy-only envelope."""

    if not isinstance(cast(object, source_envelope), EvidenceEnvelope):
        raise TypeError("source_envelope must be an EvidenceEnvelope")
    legacy_snapshots = source_envelope.legacy_snapshots
    modern_components = (
        source_envelope.request_memberships,
        source_envelope.acquisition_runs,
        source_envelope.transformations,
        source_envelope.record_relationships,
        source_envelope.completeness_assessments,
        source_envelope.publications,
    )
    status: CompatibilityStatus
    projected_snapshot: ArtifactSnapshot | None
    reasons: tuple[LegacyEvidenceCompatibilityReason, ...]
    if legacy_snapshots is None or len(legacy_snapshots) == 0:
        status = CompatibilityStatus.NOT_MAPPABLE
        projected_snapshot = None
        reasons = (LegacyEvidenceCompatibilityReason.LEGACY_SNAPSHOT_ABSENT,)
    elif len(legacy_snapshots) > 1:
        status = CompatibilityStatus.NOT_MAPPABLE
        projected_snapshot = None
        reasons = (
            LegacyEvidenceCompatibilityReason.MULTIPLE_LEGACY_SNAPSHOTS_NOT_REPRESENTABLE,
        )
    elif any(component is not None for component in modern_components):
        status = CompatibilityStatus.PARTIALLY_MAPPABLE
        projected_snapshot = None
        reasons = (
            LegacyEvidenceCompatibilityReason.MODERN_COMPONENTS_NOT_REPRESENTABLE,
        )
    else:
        status = CompatibilityStatus.LOSSLESSLY_MAPPABLE
        projected_snapshot = legacy_snapshots[0]
        reasons = ()

    return LegacyArtifactSnapshotProjectionResult(
        adapter_id=EvidenceRelationId.model_validate(
            _LEGACY_ARTIFACT_SNAPSHOT_ADAPTER_ID
        ),
        adapter_version=EvidenceVersion.model_validate(
            _LEGACY_ARTIFACT_SNAPSHOT_ADAPTER_VERSION
        ),
        status=status,
        source_envelope=source_envelope,
        projected_snapshot=projected_snapshot,
        reasons=reasons,
    )
