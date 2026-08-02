"""Strict retrieval-request identity and core provenance primitives.

The models in this module identify one request attempt by acquisition-run ID
and run-local ordinal. Retrieval authority, method, origin-relative route, and
request-start time remain explicit provenance metadata rather than identity.
This module performs no I/O and does not define request controls, response or
artifact observations, acquisition-run records, durable canonical bytes, or
an Evidence Envelope.
"""

import re
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    RootModel,
    StringConstraints,
    ValidationInfo,
    field_validator,
)

from faultatlas.domain.identity import AuthorityRole, ProviderAuthority

__all__ = [
    "AcquisitionRunId",
    "RetrievalRequestOrdinal",
    "RetrievalRequestId",
    "RetrievalMethod",
    "RetrievalRoutePath",
    "RetrievalRequestReference",
]

_MAX_RUN_ID_LENGTH = 160
_MAX_REQUEST_ORDINAL = 2_147_483_647
_MAX_ROUTE_PATH_LENGTH = 4096
_RUN_ID_PATTERN = re.compile(r"[a-z0-9](?:[a-z0-9._-]{0,158}[a-z0-9])?")
_INVALID_PERCENT_ENCODING = re.compile(r"%(?![0-9A-Fa-f]{2})")

_AcquisitionRunIdValue = Annotated[
    str,
    StringConstraints(min_length=1, max_length=_MAX_RUN_ID_LENGTH),
]
_RetrievalRoutePathValue = Annotated[
    str,
    StringConstraints(min_length=1, max_length=_MAX_ROUTE_PATH_LENGTH),
]


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
    def _reject_unknown_started_at_offset(
        cls,
        value: object,
        info: ValidationInfo,
    ) -> object:
        if info.mode == "json" and isinstance(value, str):
            if value.endswith("-00:00"):
                raise ValueError(
                    "started_at must assert UTC rather than an unknown offset"
                )
            parse_value = f"{value[:-1]}+00:00" if value.endswith("Z") else value
            try:
                return datetime.fromisoformat(parse_value)
            except ValueError:
                return value
        return value

    @field_validator("started_at")
    @classmethod
    def _normalize_started_at(cls, value: datetime) -> datetime:
        if value.utcoffset() != timedelta(0):
            raise ValueError("started_at must use a zero UTC offset")
        return value.astimezone(UTC)
