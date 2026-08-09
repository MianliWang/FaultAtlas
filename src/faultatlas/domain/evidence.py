"""Strict request, response, artifact, acquisition, and evidence-relation models.

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
bytes or storage locations. This module performs no I/O and does not execute
transformations or define canonical writers, migration, completeness,
publication, persistence, or an Evidence Envelope.
"""

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

from faultatlas.domain.identity import AuthorityRole, ProviderAuthority

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
