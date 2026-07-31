"""Internal, loss-aware compatibility for the legacy ``SourceLocator``.

This module maps only in-memory models. It performs no lookup, migration,
persistence, or canonical durable serialization, and it never infers the role
of the legacy numeric object identifier.
"""

from enum import StrEnum
from typing import Literal, Self, cast

from pydantic import (
    BaseModel,
    ConfigDict,
    ValidationError,
    ValidationInfo,
    field_validator,
    model_validator,
)

from faultatlas.domain.identity import (
    IdentityFieldState,
    IdentityValueState,
    NumberedSourceObjectIdentity,
    ProviderGlobalId,
    ProviderScopedSourceObjectIdentity,
    RepositoryAliasObservation,
    RepositoryIdentity,
    RepositoryScopedNumber,
    SourceIdentity,
    SourceObjectKind,
)
from faultatlas.domain.source import SourceLocator

__all__ = [
    "CompatibilityStatus",
    "LegacyCompatibilityReason",
    "LegacyObjectIdInterpretation",
    "LegacySourceLocatorMappingResult",
    "LegacySourceLocatorProjectionResult",
    "map_legacy_source_locator",
    "project_source_identity_to_legacy",
]


class CompatibilityStatus(StrEnum):
    """Controlled compatibility outcomes inherited from the S08 decision."""

    NATIVE = "native"
    LOSSLESSLY_MAPPABLE = "losslessly_mappable"
    PARTIALLY_MAPPABLE = "partially_mappable"
    NOT_MAPPABLE = "not_mappable"
    UNSUPPORTED_VERSION = "unsupported_version"
    CONFLICT = "conflict"


class LegacyObjectIdInterpretation(StrEnum):
    """Caller-selected semantic role for the legacy decimal object ID."""

    REPOSITORY_SCOPED_NUMBER = "repository_scoped_number"
    PROVIDER_GLOBAL_ID = "provider_global_id"
    UNRESOLVED = "unresolved"


class LegacyCompatibilityReason(StrEnum):
    """Deterministic reasons for compatibility loss or unresolved conflict."""

    LEGACY_ALIAS_OBSERVATION_MISMATCH = "legacy_alias_observation_mismatch"
    REPOSITORY_OR_PROVIDER_CONTEXT_MISMATCH = "repository_or_provider_context_mismatch"
    LEGACY_OBJECT_ID_ROLE_AMBIGUOUS = "legacy_object_id_role_ambiguous"
    REPOSITORY_SCOPED_ISSUE_NUMBER_UNAVAILABLE = (
        "repository_scoped_issue_number_unavailable"
    )
    STABLE_REPOSITORY_IDENTITY_NOT_REPRESENTED = (
        "stable_repository_identity_not_represented"
    )
    ALIAS_AUTHORITY_NOT_REPRESENTED = "alias_authority_not_represented"
    ALIAS_OBSERVATION_TIME_NOT_REPRESENTED = "alias_observation_time_not_represented"
    SCHEMA_VERSION_NOT_REPRESENTED = "schema_version_not_represented"
    SOURCE_OBJECT_KIND_UNSUPPORTED = "source_object_kind_unsupported"
    PROVIDER_UNSUPPORTED = "provider_unsupported"
    ALIAS_LEXEME_NOT_EXACTLY_REPRESENTABLE = "alias_lexeme_not_exactly_representable"
    CHILD_PARENT_SCOPE_NOT_REPRESENTED = "child_parent_scope_not_represented"
    LEGACY_ISSUE_OBJECT_IDENTITY_UNAVAILABLE = (
        "legacy_issue_object_identity_unavailable"
    )


_LegacyObjectIdStateModel = IdentityValueState[
    RepositoryScopedNumber | ProviderGlobalId
]
_SOURCE_IDENTITY_TYPES = (
    RepositoryIdentity,
    NumberedSourceObjectIdentity,
    ProviderScopedSourceObjectIdentity,
)
_MAPPING_BASIS = "legacy_locator_plus_explicit_repository_context"
_PROJECTION_BASIS = "source_identity_plus_explicit_repository_alias_observation"
_ISSUE_PROJECTION_LOSSES = (
    LegacyCompatibilityReason.STABLE_REPOSITORY_IDENTITY_NOT_REPRESENTED,
    LegacyCompatibilityReason.ALIAS_AUTHORITY_NOT_REPRESENTED,
    LegacyCompatibilityReason.ALIAS_OBSERVATION_TIME_NOT_REPRESENTED,
    LegacyCompatibilityReason.SCHEMA_VERSION_NOT_REPRESENTED,
)


def _typed_object_id_state(
    legacy_locator: SourceLocator,
    interpretation: LegacyObjectIdInterpretation,
) -> IdentityValueState[RepositoryScopedNumber | ProviderGlobalId]:
    if interpretation is LegacyObjectIdInterpretation.REPOSITORY_SCOPED_NUMBER:
        return _LegacyObjectIdStateModel(
            state=IdentityFieldState.PRESENT,
            value=RepositoryScopedNumber.model_validate(legacy_locator.object_id),
        )
    if interpretation is LegacyObjectIdInterpretation.PROVIDER_GLOBAL_ID:
        return _LegacyObjectIdStateModel(
            state=IdentityFieldState.PRESENT,
            value=ProviderGlobalId.model_validate(legacy_locator.object_id),
        )
    return _LegacyObjectIdStateModel(
        state=IdentityFieldState.CONFLICT,
        conflict_candidates=(
            RepositoryScopedNumber.model_validate(legacy_locator.object_id),
            ProviderGlobalId.model_validate(legacy_locator.object_id),
        ),
    )


def _mapping_context_reasons(
    legacy_locator: SourceLocator,
    repository_alias_observation: RepositoryAliasObservation,
) -> tuple[LegacyCompatibilityReason, ...]:
    reasons: list[LegacyCompatibilityReason] = []
    if (
        repository_alias_observation.repository_identity.provider.root
        != legacy_locator.provider
    ):
        reasons.append(
            LegacyCompatibilityReason.REPOSITORY_OR_PROVIDER_CONTEXT_MISMATCH
        )
    if repository_alias_observation.observed_alias != legacy_locator.repository:
        reasons.append(LegacyCompatibilityReason.LEGACY_ALIAS_OBSERVATION_MISMATCH)
    return tuple(reasons)


def _mapping_outcome(
    legacy_locator: SourceLocator,
    repository_alias_observation: RepositoryAliasObservation,
    interpretation: LegacyObjectIdInterpretation,
) -> tuple[
    CompatibilityStatus,
    NumberedSourceObjectIdentity | None,
    tuple[LegacyCompatibilityReason, ...],
]:
    reasons = list(
        _mapping_context_reasons(legacy_locator, repository_alias_observation)
    )
    has_context_conflict = bool(reasons)

    if interpretation is LegacyObjectIdInterpretation.PROVIDER_GLOBAL_ID:
        reasons.append(
            LegacyCompatibilityReason.REPOSITORY_SCOPED_ISSUE_NUMBER_UNAVAILABLE
        )
    elif interpretation is LegacyObjectIdInterpretation.UNRESOLVED:
        reasons.append(LegacyCompatibilityReason.LEGACY_OBJECT_ID_ROLE_AMBIGUOUS)

    if has_context_conflict:
        return CompatibilityStatus.CONFLICT, None, tuple(reasons)
    if interpretation is LegacyObjectIdInterpretation.PROVIDER_GLOBAL_ID:
        return CompatibilityStatus.PARTIALLY_MAPPABLE, None, tuple(reasons)
    if interpretation is LegacyObjectIdInterpretation.UNRESOLVED:
        return CompatibilityStatus.CONFLICT, None, tuple(reasons)

    typed_number = RepositoryScopedNumber.model_validate(legacy_locator.object_id)
    mapped_identity = NumberedSourceObjectIdentity(
        repository_identity=repository_alias_observation.repository_identity,
        kind=SourceObjectKind.ISSUE,
        repository_scoped_number=typed_number,
    )
    return CompatibilityStatus.LOSSLESSLY_MAPPABLE, mapped_identity, ()


def _convert_json_object_id(
    value: object,
    interpretation: LegacyObjectIdInterpretation,
    *,
    candidate_index: int | None = None,
) -> object:
    if not isinstance(value, str):
        return value
    if interpretation is LegacyObjectIdInterpretation.REPOSITORY_SCOPED_NUMBER:
        return RepositoryScopedNumber.model_validate(value)
    if interpretation is LegacyObjectIdInterpretation.PROVIDER_GLOBAL_ID:
        return ProviderGlobalId.model_validate(value)
    if candidate_index == 0:
        return RepositoryScopedNumber.model_validate(value)
    return ProviderGlobalId.model_validate(value)


def _restore_json_object_id_state(
    state_value: object,
    interpretation: LegacyObjectIdInterpretation,
) -> object:
    if not isinstance(state_value, dict):
        return state_value
    state_data = dict(cast(dict[str, object], state_value))
    raw_state = state_data.get("state")
    if isinstance(raw_state, str):
        try:
            state_data["state"] = IdentityFieldState(raw_state)
        except ValueError:
            pass
    if "value" in state_data:
        state_data["value"] = _convert_json_object_id(
            state_data["value"],
            interpretation,
        )
    raw_candidates = state_data.get("conflict_candidates")
    if isinstance(raw_candidates, list):
        state_data["conflict_candidates"] = tuple(
            _convert_json_object_id(
                candidate,
                interpretation,
                candidate_index=index,
            )
            for index, candidate in enumerate(cast(list[object], raw_candidates))
        )
    return _LegacyObjectIdStateModel.model_validate(state_data)


class LegacySourceLocatorMappingResult(BaseModel):
    """Validated result of mapping one already-constructed legacy locator."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        strict=True,
        revalidate_instances="always",
        validate_default=True,
    )

    schema_version: Literal[1] = 1
    status: CompatibilityStatus
    legacy_locator: SourceLocator
    repository_alias_observation: RepositoryAliasObservation
    object_id_interpretation: LegacyObjectIdInterpretation
    object_id_state: IdentityValueState[RepositoryScopedNumber | ProviderGlobalId]
    mapped_identity: NumberedSourceObjectIdentity | None = None
    reasons: tuple[LegacyCompatibilityReason, ...] = ()
    mapping_basis: Literal["legacy_locator_plus_explicit_repository_context"] = (
        _MAPPING_BASIS
    )

    @field_validator("object_id_state", mode="before")
    @classmethod
    def _restore_or_require_typed_object_id_state(
        cls,
        value: object,
        info: ValidationInfo,
    ) -> object:
        if info.mode == "json":
            interpretation = info.data.get("object_id_interpretation")
            if isinstance(interpretation, LegacyObjectIdInterpretation):
                return _restore_json_object_id_state(value, interpretation)
            return value
        if info.mode == "python" and not isinstance(value, IdentityValueState):
            raise ValueError("object_id_state must use the specialized typed state")
        return cast(object, value)

    @field_validator("reasons")
    @classmethod
    def _require_unique_reasons(
        cls,
        value: tuple[LegacyCompatibilityReason, ...],
    ) -> tuple[LegacyCompatibilityReason, ...]:
        if len(value) != len(set(value)):
            raise ValueError("compatibility reasons must be unique")
        return value

    @model_validator(mode="after")
    def _validate_mapping_shape(self) -> Self:
        expected_state = _typed_object_id_state(
            self.legacy_locator,
            self.object_id_interpretation,
        )
        expected_status, expected_identity, expected_reasons = _mapping_outcome(
            self.legacy_locator,
            self.repository_alias_observation,
            self.object_id_interpretation,
        )
        if self.object_id_state != expected_state:
            raise ValueError(
                "object_id_state must exactly preserve the explicit interpretation"
            )
        if self.status is not expected_status:
            raise ValueError("mapping status does not match the mapping inputs")
        if self.mapped_identity != expected_identity:
            raise ValueError("mapped identity does not match the mapping inputs")
        if self.reasons != expected_reasons:
            raise ValueError("mapping reasons do not match the mapping inputs")
        return self


def _source_repository_identity(identity: SourceIdentity) -> RepositoryIdentity:
    if isinstance(identity, RepositoryIdentity):
        return identity
    if isinstance(identity, NumberedSourceObjectIdentity):
        return identity.repository_identity
    return identity.parent.repository_identity


def _projection_outcome(
    source_identity: SourceIdentity,
    repository_alias_observation: RepositoryAliasObservation,
) -> tuple[
    CompatibilityStatus,
    SourceLocator | None,
    tuple[LegacyCompatibilityReason, ...],
]:
    repository_identity = _source_repository_identity(source_identity)
    if repository_alias_observation.repository_identity != repository_identity:
        return (
            CompatibilityStatus.CONFLICT,
            None,
            (LegacyCompatibilityReason.REPOSITORY_OR_PROVIDER_CONTEXT_MISMATCH,),
        )
    if repository_identity.provider.root != "github":
        return (
            CompatibilityStatus.NOT_MAPPABLE,
            None,
            (LegacyCompatibilityReason.PROVIDER_UNSUPPORTED,),
        )
    if isinstance(source_identity, RepositoryIdentity):
        return (
            CompatibilityStatus.NOT_MAPPABLE,
            None,
            (LegacyCompatibilityReason.LEGACY_ISSUE_OBJECT_IDENTITY_UNAVAILABLE,),
        )
    if isinstance(source_identity, ProviderScopedSourceObjectIdentity):
        return (
            CompatibilityStatus.NOT_MAPPABLE,
            None,
            (
                LegacyCompatibilityReason.SOURCE_OBJECT_KIND_UNSUPPORTED,
                LegacyCompatibilityReason.CHILD_PARENT_SCOPE_NOT_REPRESENTED,
            ),
        )
    if source_identity.kind is not SourceObjectKind.ISSUE:
        return (
            CompatibilityStatus.NOT_MAPPABLE,
            None,
            (LegacyCompatibilityReason.SOURCE_OBJECT_KIND_UNSUPPORTED,),
        )

    try:
        projected_locator = SourceLocator(
            provider="github",
            repository=repository_alias_observation.observed_alias,
            object_kind="issue",
            object_id=source_identity.repository_scoped_number.root,
        )
    except ValidationError:
        return (
            CompatibilityStatus.NOT_MAPPABLE,
            None,
            (LegacyCompatibilityReason.ALIAS_LEXEME_NOT_EXACTLY_REPRESENTABLE,),
        )
    if projected_locator.repository != repository_alias_observation.observed_alias:
        return (
            CompatibilityStatus.NOT_MAPPABLE,
            None,
            (LegacyCompatibilityReason.ALIAS_LEXEME_NOT_EXACTLY_REPRESENTABLE,),
        )
    return (
        CompatibilityStatus.PARTIALLY_MAPPABLE,
        projected_locator,
        (_ISSUE_PROJECTION_LOSSES),
    )


class LegacySourceLocatorProjectionResult(BaseModel):
    """Validated, explicitly lossy projection into the legacy Issue locator."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        strict=True,
        revalidate_instances="always",
        validate_default=True,
    )

    schema_version: Literal[1] = 1
    status: CompatibilityStatus
    source_identity: SourceIdentity
    repository_alias_observation: RepositoryAliasObservation
    projected_locator: SourceLocator | None = None
    reasons: tuple[LegacyCompatibilityReason, ...] = ()
    projection_basis: Literal[
        "source_identity_plus_explicit_repository_alias_observation"
    ] = _PROJECTION_BASIS

    @field_validator("source_identity", mode="before")
    @classmethod
    def _require_typed_python_source_identity(
        cls,
        value: object,
        info: ValidationInfo,
    ) -> object:
        if info.mode == "python" and not isinstance(value, _SOURCE_IDENTITY_TYPES):
            raise ValueError("source_identity must use a known typed identity")
        return value

    @field_validator("reasons")
    @classmethod
    def _require_unique_reasons(
        cls,
        value: tuple[LegacyCompatibilityReason, ...],
    ) -> tuple[LegacyCompatibilityReason, ...]:
        if len(value) != len(set(value)):
            raise ValueError("compatibility reasons must be unique")
        return value

    @model_validator(mode="after")
    def _validate_projection_shape(self) -> Self:
        expected_status, expected_locator, expected_reasons = _projection_outcome(
            self.source_identity,
            self.repository_alias_observation,
        )
        if self.status is not expected_status:
            raise ValueError("projection status does not match the projection inputs")
        if self.projected_locator != expected_locator:
            raise ValueError("projected locator does not match the projection inputs")
        if self.reasons != expected_reasons:
            raise ValueError("projection reasons do not match the projection inputs")
        return self


def map_legacy_source_locator(
    legacy_locator: SourceLocator,
    *,
    repository_alias_observation: RepositoryAliasObservation,
    object_id_interpretation: LegacyObjectIdInterpretation,
) -> LegacySourceLocatorMappingResult:
    """Map a legacy locator using only caller-supplied explicit context."""

    object_id_state = _typed_object_id_state(
        legacy_locator,
        object_id_interpretation,
    )
    status, mapped_identity, reasons = _mapping_outcome(
        legacy_locator,
        repository_alias_observation,
        object_id_interpretation,
    )
    return LegacySourceLocatorMappingResult(
        status=status,
        legacy_locator=legacy_locator,
        repository_alias_observation=repository_alias_observation,
        object_id_interpretation=object_id_interpretation,
        object_id_state=object_id_state,
        mapped_identity=mapped_identity,
        reasons=reasons,
    )


def project_source_identity_to_legacy(
    source_identity: SourceIdentity,
    *,
    repository_alias_observation: RepositoryAliasObservation,
) -> LegacySourceLocatorProjectionResult:
    """Project a typed identity without hiding incompatibility or semantic loss."""

    status, projected_locator, reasons = _projection_outcome(
        source_identity,
        repository_alias_observation,
    )
    return LegacySourceLocatorProjectionResult(
        status=status,
        source_identity=source_identity,
        repository_alias_observation=repository_alias_observation,
        projected_locator=projected_locator,
        reasons=reasons,
    )
