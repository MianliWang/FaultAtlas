"""Internal, case-calibrated identity primitives and explicit identity states.

The models in this module support semantic Pydantic JSON round trips. Identity
field states preserve absence and unresolved conflict without selecting a
winner. Lifecycle observations record only the availability of an already
known source identity; they do not define transitions or source-object business
state. This module does not define FaultAtlas's durable canonical byte format,
retrieval provenance, revision identity, relationships, or evidence envelopes.
"""

import re
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from ipaddress import ip_address
from typing import Annotated, Literal, Self, cast

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    RootModel,
    StringConstraints,
    ValidationInfo,
    field_validator,
    model_validator,
)

__all__ = [
    "AuthorityRole",
    "IdentityFieldState",
    "IdentityValueState",
    "NumberedSourceObjectIdentity",
    "ProviderAuthority",
    "ProviderGlobalId",
    "ProviderKey",
    "ProviderNodeId",
    "ProviderRepositoryId",
    "ProviderScopedSourceObjectIdentity",
    "RepositoryAliasObservation",
    "RepositoryIdentity",
    "RepositoryScopedNumber",
    "SourceIdentity",
    "SourceIdentityLifecycleObservation",
    "SourceIdentityLifecycleState",
    "SourceObjectKind",
]

_PROVIDER_KEY_PATTERN = re.compile(r"[a-z][a-z0-9-]*")
_DNS_LABEL_PATTERN = re.compile(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?")
_REPOSITORY_SCOPED_NUMBER_PATTERN = re.compile(r"[1-9][0-9]{0,19}")
_MAX_PROVIDER_KEY_LENGTH = 64
_MAX_AUTHORITY_HOST_LENGTH = 253
_MAX_PROVIDER_REPOSITORY_ID_LENGTH = 255
_MAX_OBSERVED_ALIAS_LENGTH = 255
_MAX_PROVIDER_GLOBAL_ID_LENGTH = 255
_MAX_PROVIDER_NODE_ID_LENGTH = 512

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
_RepositoryScopedNumberValue = Annotated[
    str,
    StringConstraints(min_length=1, max_length=20),
]
_ProviderGlobalIdValue = Annotated[
    str,
    StringConstraints(min_length=1, max_length=_MAX_PROVIDER_GLOBAL_ID_LENGTH),
]
_ProviderNodeIdValue = Annotated[
    str,
    StringConstraints(min_length=1, max_length=_MAX_PROVIDER_NODE_ID_LENGTH),
]


def _require_unpadded_printable(value: str, *, field_name: str) -> str:
    if value != value.strip():
        raise ValueError(f"{field_name} must not have surrounding whitespace")
    if not value.isprintable():
        raise ValueError(f"{field_name} must contain only printable characters")
    return value


def _require_unspaced_printable(value: str, *, field_name: str) -> str:
    if any(character.isspace() for character in value):
        raise ValueError(f"{field_name} must not contain whitespace")
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


class SourceObjectKind(StrEnum):
    """Closed source-object vocabulary for the first object identity slice."""

    ISSUE = "issue"
    PULL_REQUEST = "pull_request"
    ISSUE_COMMENT = "issue_comment"
    PULL_REQUEST_COMMENT = "pull_request_comment"
    PULL_REQUEST_REVIEW = "pull_request_review"
    PULL_REQUEST_REVIEW_COMMENT = "pull_request_review_comment"
    TIMELINE_EVENT = "timeline_event"


class RepositoryScopedNumber(RootModel[_RepositoryScopedNumberValue]):
    """Canonical positive decimal number scoped to one repository."""

    model_config = ConfigDict(
        frozen=True,
        strict=True,
        revalidate_instances="always",
        validate_default=True,
    )

    root: _RepositoryScopedNumberValue

    @field_validator("root")
    @classmethod
    def _validate_repository_scoped_number(cls, value: str) -> str:
        if (
            not value.isascii()
            or _REPOSITORY_SCOPED_NUMBER_PATTERN.fullmatch(value) is None
        ):
            raise ValueError(
                "repository-scoped number must be a canonical positive "
                "ASCII decimal lexeme of at most 20 digits"
            )
        return value


class ProviderGlobalId(RootModel[_ProviderGlobalIdValue]):
    """Opaque provider-assigned global identifier for a source object."""

    model_config = ConfigDict(
        frozen=True,
        strict=True,
        revalidate_instances="always",
        validate_default=True,
    )

    root: _ProviderGlobalIdValue

    @field_validator("root")
    @classmethod
    def _validate_provider_global_id(cls, value: str) -> str:
        return _require_unspaced_printable(
            value,
            field_name="provider global ID",
        )


class ProviderNodeId(RootModel[_ProviderNodeIdValue]):
    """Opaque optional provider node identifier, without decode semantics."""

    model_config = ConfigDict(
        frozen=True,
        strict=True,
        revalidate_instances="always",
        validate_default=True,
    )

    root: _ProviderNodeIdValue

    @field_validator("root")
    @classmethod
    def _validate_provider_node_id(cls, value: str) -> str:
        return _require_unspaced_printable(
            value,
            field_name="provider node ID",
        )


_NUMBERED_SOURCE_OBJECT_KINDS: frozenset[SourceObjectKind] = frozenset(
    {
        SourceObjectKind.ISSUE,
        SourceObjectKind.PULL_REQUEST,
    }
)
_PROVIDER_SCOPED_PARENT_KINDS: dict[
    SourceObjectKind,
    frozenset[SourceObjectKind],
] = {
    SourceObjectKind.ISSUE_COMMENT: frozenset({SourceObjectKind.ISSUE}),
    SourceObjectKind.PULL_REQUEST_COMMENT: frozenset({SourceObjectKind.PULL_REQUEST}),
    SourceObjectKind.PULL_REQUEST_REVIEW: frozenset({SourceObjectKind.PULL_REQUEST}),
    SourceObjectKind.PULL_REQUEST_REVIEW_COMMENT: frozenset(
        {SourceObjectKind.PULL_REQUEST}
    ),
    SourceObjectKind.TIMELINE_EVENT: frozenset(
        {
            SourceObjectKind.ISSUE,
            SourceObjectKind.PULL_REQUEST,
        }
    ),
}


class NumberedSourceObjectIdentity(BaseModel):
    """Stable identity for an issue or pull request in one repository."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        strict=True,
        revalidate_instances="always",
        validate_default=True,
    )

    schema_version: Literal[1] = 1
    repository_identity: RepositoryIdentity
    kind: SourceObjectKind
    repository_scoped_number: RepositoryScopedNumber

    @model_validator(mode="after")
    def _validate_numbered_kind(self) -> Self:
        if self.kind not in _NUMBERED_SOURCE_OBJECT_KINDS:
            raise ValueError(
                "numbered source object kind must be issue or pull_request"
            )
        return self


class ProviderScopedSourceObjectIdentity(BaseModel):
    """Stable child-object identity under an issue or pull request parent."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        strict=True,
        revalidate_instances="always",
        validate_default=True,
    )

    schema_version: Literal[1] = 1
    kind: SourceObjectKind
    provider_global_id: ProviderGlobalId
    parent: NumberedSourceObjectIdentity

    @model_validator(mode="after")
    def _validate_parent_kind(self) -> Self:
        allowed_parent_kinds = _PROVIDER_SCOPED_PARENT_KINDS.get(self.kind)
        if allowed_parent_kinds is None:
            raise ValueError(
                "provider-scoped source object kind must be a comment, review, "
                "review comment, or timeline event"
            )
        if self.parent.kind not in allowed_parent_kinds:
            raise ValueError(
                f"{self.kind.value} cannot use {self.parent.kind.value} as its parent"
            )
        return self


class IdentityFieldState(StrEnum):
    """Exact state of one identity-bearing field or typed identity value."""

    PRESENT = "present"
    OBSERVED_NULL = "observed_null"
    MISSING = "missing"
    UNAVAILABLE = "unavailable"
    INACCESSIBLE = "inaccessible"
    DELETED = "deleted"
    UNKNOWN = "unknown"
    UNSUPPORTED = "unsupported"
    CONFLICT = "conflict"


type SourceIdentity = (
    RepositoryIdentity
    | NumberedSourceObjectIdentity
    | ProviderScopedSourceObjectIdentity
)
type _IdentityValue = (
    ProviderGlobalId | ProviderNodeId | RepositoryScopedNumber | SourceIdentity
)

_SOURCE_IDENTITY_TYPES = (
    RepositoryIdentity,
    NumberedSourceObjectIdentity,
    ProviderScopedSourceObjectIdentity,
)
_IDENTITY_VALUE_TYPES = (
    ProviderGlobalId,
    ProviderNodeId,
    RepositoryScopedNumber,
    RepositoryIdentity,
    NumberedSourceObjectIdentity,
    ProviderScopedSourceObjectIdentity,
)


class IdentityValueState[IdentityValueT: _IdentityValue](BaseModel):
    """Typed value, explicit absence, or unresolved ordered conflict."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        strict=True,
        revalidate_instances="always",
        validate_default=True,
    )

    schema_version: Literal[1] = 1
    state: IdentityFieldState
    value: IdentityValueT | None = None
    conflict_candidates: tuple[IdentityValueT, ...] = ()

    @model_validator(mode="before")
    @classmethod
    def _require_explicit_specialization(cls, value: object) -> object:
        if cls is IdentityValueState:
            raise ValueError("IdentityValueState must be explicitly specialized")
        return value

    @field_validator("value", mode="before")
    @classmethod
    def _require_typed_python_value(
        cls,
        value: object,
        info: ValidationInfo,
    ) -> object:
        if (
            info.mode == "python"
            and value is not None
            and not isinstance(value, _IDENTITY_VALUE_TYPES)
        ):
            raise ValueError("Python value must use a supported identity type")
        return value

    @field_validator("conflict_candidates", mode="before")
    @classmethod
    def _require_typed_python_candidates(
        cls,
        value: object,
        info: ValidationInfo,
    ) -> object:
        if info.mode == "json" and isinstance(value, list):
            return tuple(cast(list[object], value))
        if info.mode == "python" and isinstance(value, tuple):
            if any(
                not isinstance(candidate, _IDENTITY_VALUE_TYPES)
                for candidate in cast(tuple[object, ...], value)
            ):
                raise ValueError(
                    "Python conflict candidates must use supported identity types"
                )
        return cast(object, value)

    @model_validator(mode="after")
    def _validate_state_shape(self) -> Self:
        if self.state is IdentityFieldState.PRESENT:
            if self.value is None:
                raise ValueError("present state requires exactly one typed value")
            if self.conflict_candidates:
                raise ValueError("present state cannot retain conflict candidates")
            return self

        if self.state is IdentityFieldState.CONFLICT:
            if self.value is not None:
                raise ValueError("conflict state cannot select a value")
            if len(self.conflict_candidates) < 2:
                raise ValueError("conflict state requires at least two candidates")
            for index, candidate in enumerate(self.conflict_candidates):
                if any(
                    candidate == prior for prior in self.conflict_candidates[:index]
                ):
                    raise ValueError("conflict candidates must be semantically unique")
            return self

        if self.value is not None:
            raise ValueError(f"{self.state.value} state cannot retain a value")
        if self.conflict_candidates:
            raise ValueError(
                f"{self.state.value} state cannot retain conflict candidates"
            )
        return self


class SourceIdentityLifecycleState(StrEnum):
    """Availability state for a known source identity, not business state."""

    OBSERVED_PRESENT = "observed_present"
    DELETED = "deleted"
    UNAVAILABLE = "unavailable"
    INACCESSIBLE = "inaccessible"
    UNKNOWN = "unknown"


def _source_identity_provider(identity: SourceIdentity) -> ProviderKey:
    if isinstance(identity, RepositoryIdentity):
        return identity.provider
    if isinstance(identity, NumberedSourceObjectIdentity):
        return identity.repository_identity.provider
    return identity.parent.repository_identity.provider


class SourceIdentityLifecycleObservation(BaseModel):
    """One availability observation about an already known source identity."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        strict=True,
        revalidate_instances="always",
        validate_default=True,
    )

    schema_version: Literal[1] = 1
    identity: SourceIdentity
    state: SourceIdentityLifecycleState
    authority: ProviderAuthority
    observed_at: AwareDatetime

    @field_validator("identity", mode="before")
    @classmethod
    def _require_known_python_identity(
        cls,
        value: object,
        info: ValidationInfo,
    ) -> object:
        if info.mode == "python" and not isinstance(value, _SOURCE_IDENTITY_TYPES):
            raise ValueError("identity must be a known source identity")
        return value

    @field_validator("observed_at")
    @classmethod
    def _normalize_observed_at(cls, value: datetime) -> datetime:
        if value.utcoffset() != timedelta(0):
            raise ValueError("observed_at must use a zero UTC offset")
        return value.astimezone(UTC)

    @model_validator(mode="after")
    def _validate_provider_match(self) -> Self:
        if self.authority.provider != _source_identity_provider(self.identity):
            raise ValueError("authority provider must match source identity provider")
        return self
