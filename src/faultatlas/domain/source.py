"""Logical source identity and immutable retrieval snapshots."""

from datetime import UTC, datetime, timedelta
from hashlib import sha256
from typing import Annotated, Literal, Self

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

RepositoryIdentity = Annotated[
    str,
    StringConstraints(
        min_length=3,
        max_length=140,
        pattern=(
            r"^[a-z0-9](?:[a-z0-9-]{0,37}[a-z0-9])?/"
            r"[a-z0-9._-]{1,100}$"
        ),
    ),
]
ProviderObjectId = Annotated[
    str,
    StringConstraints(
        min_length=1,
        max_length=20,
        pattern=r"^[1-9][0-9]*$",
    ),
]
Sha256Digest = Annotated[
    str,
    StringConstraints(
        min_length=64,
        max_length=64,
        pattern=r"^[0-9a-f]+$",
    ),
]
MissingContextReason = Annotated[
    str,
    StringConstraints(min_length=1, max_length=200),
]
MissingContext = Annotated[
    tuple[MissingContextReason, ...],
    Field(max_length=16),
]

_MAX_PAYLOAD_BYTES = 1_048_576


class SourceLocator(BaseModel):
    """Canonical logical identity for one supported external source object."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        strict=True,
        revalidate_instances="always",
        validate_default=True,
    )

    provider: Literal["github"]
    repository: RepositoryIdentity
    object_kind: Literal["issue"]
    object_id: ProviderObjectId

    @field_validator("repository", mode="before")
    @classmethod
    def _normalize_repository(cls, value: object) -> object:
        if not isinstance(value, str):
            return value
        if value != value.strip():
            raise ValueError("repository must not have surrounding whitespace")
        if not value.isascii():
            raise ValueError("repository must contain only ASCII characters")
        return value.lower()


class ArtifactSnapshot(BaseModel):
    """One immutable retrieval of a logical source object."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        strict=True,
        revalidate_instances="always",
        validate_default=True,
    )

    schema_version: Literal[1] = 1
    source: SourceLocator
    retrieved_at: AwareDatetime
    media_type: Literal["application/json"] = "application/json"
    payload_text: str
    digest_algorithm: Literal["sha256"] = "sha256"
    digest: Sha256Digest
    truncated: bool | None
    redacted: bool | None
    missing_context: MissingContext | None

    @field_validator("retrieved_at")
    @classmethod
    def _normalize_retrieved_at(cls, value: datetime) -> datetime:
        if value.utcoffset() != timedelta(0):
            raise ValueError("retrieved_at must use a zero UTC offset")
        return value.astimezone(UTC)

    @field_validator("payload_text")
    @classmethod
    def _validate_payload_text(cls, value: str) -> str:
        try:
            payload_bytes = value.encode("utf-8")
        except UnicodeEncodeError as error:
            raise ValueError("payload_text must encode as UTF-8") from error
        if len(payload_bytes) > _MAX_PAYLOAD_BYTES:
            raise ValueError(
                f"payload_text must not exceed {_MAX_PAYLOAD_BYTES} UTF-8 bytes"
            )
        return value

    @field_validator("missing_context")
    @classmethod
    def _validate_missing_context(
        cls,
        value: tuple[str, ...] | None,
    ) -> tuple[str, ...] | None:
        if value is None:
            return None
        if len(value) != len(set(value)):
            raise ValueError("missing_context reasons must be unique")
        if any(reason != reason.strip() for reason in value):
            raise ValueError(
                "missing_context reasons must not have surrounding whitespace"
            )
        if any(not reason.isprintable() for reason in value):
            raise ValueError("missing_context reasons must be printable")
        return value

    @model_validator(mode="after")
    def _validate_digest(self) -> Self:
        payload_digest = sha256(self.payload_text.encode("utf-8")).hexdigest()
        if self.digest != payload_digest:
            raise ValueError("digest must match the exact UTF-8 payload bytes")
        return self
