"""Internal, case-calibrated provider and repository identity primitives.

The models in this module support semantic Pydantic JSON round trips. They do
not define FaultAtlas's durable canonical byte format, retrieval provenance,
source-object identity, revision identity, or evidence envelopes.
"""

import re
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from ipaddress import ip_address
from typing import Annotated, Literal, Self

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    RootModel,
    StringConstraints,
    field_validator,
    model_validator,
)

__all__ = [
    "AuthorityRole",
    "ProviderAuthority",
    "ProviderKey",
    "ProviderRepositoryId",
    "RepositoryAliasObservation",
    "RepositoryIdentity",
]

_PROVIDER_KEY_PATTERN = re.compile(r"[a-z][a-z0-9-]*")
_DNS_LABEL_PATTERN = re.compile(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?")
_MAX_PROVIDER_KEY_LENGTH = 64
_MAX_AUTHORITY_HOST_LENGTH = 253
_MAX_PROVIDER_REPOSITORY_ID_LENGTH = 255
_MAX_OBSERVED_ALIAS_LENGTH = 255

_ProviderKeyValue = Annotated[
    str,
    StringConstraints(min_length=1, max_length=_MAX_PROVIDER_KEY_LENGTH),
]
_ProviderRepositoryIdValue = Annotated[
    str,
    StringConstraints(
        min_length=1,
        max_length=_MAX_PROVIDER_REPOSITORY_ID_LENGTH,
    ),
]
_AuthorityHost = Annotated[
    str,
    StringConstraints(min_length=1, max_length=_MAX_AUTHORITY_HOST_LENGTH),
]
_ObservedAlias = Annotated[
    str,
    StringConstraints(min_length=1, max_length=_MAX_OBSERVED_ALIAS_LENGTH),
]


def _require_unpadded_printable(value: str, *, field_name: str) -> str:
    if value != value.strip():
        raise ValueError(f"{field_name} must not have surrounding whitespace")
    if not value.isprintable():
        raise ValueError(f"{field_name} must contain only printable characters")
    return value


class ProviderKey(RootModel[_ProviderKeyValue]):
    """Stable normalized key for a source ecosystem."""

    model_config = ConfigDict(
        frozen=True,
        strict=True,
        revalidate_instances="always",
        validate_default=True,
    )

    root: _ProviderKeyValue

    @field_validator("root")
    @classmethod
    def _validate_provider_key(cls, value: str) -> str:
        if not value.isascii() or _PROVIDER_KEY_PATTERN.fullmatch(value) is None:
            raise ValueError(
                "provider key must begin with a lowercase ASCII letter and "
                "contain only lowercase ASCII letters, digits, or hyphens"
            )
        return value


class AuthorityRole(StrEnum):
    """Role played by a provider authority."""

    NAVIGATION = "navigation"
    RETRIEVAL = "retrieval"


class ProviderAuthority(BaseModel):
    """One provider-qualified navigation or retrieval DNS authority."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        strict=True,
        revalidate_instances="always",
        validate_default=True,
    )

    schema_version: Literal[1] = 1
    provider: ProviderKey
    role: AuthorityRole
    host: _AuthorityHost

    @field_validator("host")
    @classmethod
    def _validate_host(cls, value: str) -> str:
        if value != value.strip():
            raise ValueError("host must not have surrounding whitespace")
        if not value.isascii():
            raise ValueError("host must contain only ASCII characters")
        if value != value.lower():
            raise ValueError("host must be lowercase")
        if value.endswith("."):
            raise ValueError("host must not have a trailing dot")
        try:
            ip_address(value)
        except ValueError:
            pass
        else:
            raise ValueError("host must be a DNS hostname, not an IP address")
        labels = value.split(".")
        if any(_DNS_LABEL_PATTERN.fullmatch(label) is None for label in labels):
            raise ValueError("host must be a valid conservative DNS hostname")
        return value


class ProviderRepositoryId(RootModel[_ProviderRepositoryIdValue]):
    """Opaque provider-assigned stable repository identifier."""

    model_config = ConfigDict(
        frozen=True,
        strict=True,
        revalidate_instances="always",
        validate_default=True,
    )

    root: _ProviderRepositoryIdValue

    @field_validator("root")
    @classmethod
    def _validate_provider_repository_id(cls, value: str) -> str:
        return _require_unpadded_printable(
            value,
            field_name="provider repository ID",
        )


class RepositoryIdentity(BaseModel):
    """Stable repository identity, independent of mutable aliases."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        strict=True,
        revalidate_instances="always",
        validate_default=True,
    )

    schema_version: Literal[1] = 1
    provider: ProviderKey
    provider_repository_id: ProviderRepositoryId


class RepositoryAliasObservation(BaseModel):
    """Positive alias observation without later-phase lifecycle semantics."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        strict=True,
        revalidate_instances="always",
        validate_default=True,
    )

    schema_version: Literal[1] = 1
    repository_identity: RepositoryIdentity
    observed_alias: _ObservedAlias
    authority: ProviderAuthority
    observed_at: AwareDatetime

    @field_validator("observed_alias")
    @classmethod
    def _validate_observed_alias(cls, value: str) -> str:
        return _require_unpadded_printable(value, field_name="observed alias")

    @field_validator("observed_at")
    @classmethod
    def _normalize_observed_at(cls, value: datetime) -> datetime:
        if value.utcoffset() != timedelta(0):
            raise ValueError("observed_at must use a zero UTC offset")
        return value.astimezone(UTC)

    @model_validator(mode="after")
    def _validate_provider_match(self) -> Self:
        if self.authority.provider != self.repository_identity.provider:
            raise ValueError(
                "authority provider must match repository identity provider"
            )
        return self
