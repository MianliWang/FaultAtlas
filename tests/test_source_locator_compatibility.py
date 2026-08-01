from __future__ import annotations

import ast
import hashlib
import inspect
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

import pytest
from pydantic import ValidationError

import faultatlas
import faultatlas.domain as domain_package
import faultatlas.domain.compatibility as compatibility_module
from faultatlas.domain.compatibility import (
    CompatibilityStatus,
    LegacyCompatibilityReason,
    LegacyObjectIdInterpretation,
    LegacySourceLocatorMappingResult,
    LegacySourceLocatorProjectionResult,
    map_legacy_source_locator,
    project_source_identity_to_legacy,
)
from faultatlas.domain.identity import (
    AuthorityRole,
    IdentityFieldState,
    NumberedSourceObjectIdentity,
    ProviderAuthority,
    ProviderGlobalId,
    ProviderKey,
    ProviderRepositoryId,
    ProviderScopedSourceObjectIdentity,
    RepositoryAliasObservation,
    RepositoryIdentity,
    RepositoryScopedNumber,
    SourceIdentity,
    SourceObjectKind,
)
from faultatlas.domain.source import SourceLocator

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SOURCE_PATH = REPOSITORY_ROOT / "src/faultatlas/domain/source.py"
EXPECTED_SOURCE_SHA256 = (
    "034e53fd58212f0e34376bbc790fc3e74057031aaed4d7d89fb67904bdd380bf"
)
EXPECTED_EXPORTS = (
    "CompatibilityStatus",
    "LegacyCompatibilityReason",
    "LegacyObjectIdInterpretation",
    "LegacySourceLocatorMappingResult",
    "LegacySourceLocatorProjectionResult",
    "map_legacy_source_locator",
    "project_source_identity_to_legacy",
)
EXPECTED_ISSUE_PROJECTION_REASONS = (
    LegacyCompatibilityReason.STABLE_REPOSITORY_IDENTITY_NOT_REPRESENTED,
    LegacyCompatibilityReason.ALIAS_AUTHORITY_NOT_REPRESENTED,
    LegacyCompatibilityReason.ALIAS_OBSERVATION_TIME_NOT_REPRESENTED,
    LegacyCompatibilityReason.SCHEMA_VERSION_NOT_REPRESENTED,
)


def _provider(value: str = "github") -> ProviderKey:
    return ProviderKey.model_validate(value)


def _repository(
    *,
    provider: ProviderKey | None = None,
    repository_id: str = "37489525",
) -> RepositoryIdentity:
    return RepositoryIdentity(
        provider=provider or _provider(),
        provider_repository_id=ProviderRepositoryId.model_validate(repository_id),
    )


def _authority(provider: ProviderKey | None = None) -> ProviderAuthority:
    resolved_provider = provider or _provider()
    host = "github.com" if resolved_provider.root == "github" else "gitlab.com"
    return ProviderAuthority(
        provider=resolved_provider,
        role=AuthorityRole.NAVIGATION,
        host=host,
    )


def _alias_observation(
    *,
    repository: RepositoryIdentity | None = None,
    alias: str = "pytest-dev/pytest",
) -> RepositoryAliasObservation:
    resolved_repository = repository or _repository()
    return RepositoryAliasObservation(
        repository_identity=resolved_repository,
        observed_alias=alias,
        authority=_authority(resolved_repository.provider),
        observed_at=datetime(2026, 7, 24, 11, 3, 15, tzinfo=UTC),
    )


def _legacy_locator(object_id: str = "4412") -> SourceLocator:
    return SourceLocator(
        provider="github",
        repository="pytest-dev/pytest",
        object_kind="issue",
        object_id=object_id,
    )


def _numbered(
    *,
    repository: RepositoryIdentity | None = None,
    kind: SourceObjectKind = SourceObjectKind.ISSUE,
    number: str = "4412",
) -> NumberedSourceObjectIdentity:
    return NumberedSourceObjectIdentity(
        repository_identity=repository or _repository(),
        kind=kind,
        repository_scoped_number=RepositoryScopedNumber.model_validate(number),
    )


def _child(
    *,
    parent: NumberedSourceObjectIdentity | None = None,
    kind: SourceObjectKind = SourceObjectKind.ISSUE_COMMENT,
    global_id: str = "439722704",
) -> ProviderScopedSourceObjectIdentity:
    return ProviderScopedSourceObjectIdentity(
        kind=kind,
        provider_global_id=ProviderGlobalId.model_validate(global_id),
        parent=parent or _numbered(),
    )


def _map(
    interpretation: LegacyObjectIdInterpretation,
    *,
    locator: SourceLocator | None = None,
    observation: RepositoryAliasObservation | None = None,
) -> LegacySourceLocatorMappingResult:
    return map_legacy_source_locator(
        locator or _legacy_locator(),
        repository_alias_observation=observation or _alias_observation(),
        object_id_interpretation=interpretation,
    )


def _mapping_data(
    result: LegacySourceLocatorMappingResult,
    **overrides: object,
) -> dict[str, object]:
    data: dict[str, object] = {
        "schema_version": result.schema_version,
        "status": result.status,
        "legacy_locator": result.legacy_locator,
        "repository_alias_observation": result.repository_alias_observation,
        "object_id_interpretation": result.object_id_interpretation,
        "object_id_state": result.object_id_state,
        "mapped_identity": result.mapped_identity,
        "reasons": result.reasons,
        "mapping_basis": result.mapping_basis,
    }
    data.update(overrides)
    return data


def _projection_data(
    result: LegacySourceLocatorProjectionResult,
    **overrides: object,
) -> dict[str, object]:
    data: dict[str, object] = {
        "schema_version": result.schema_version,
        "status": result.status,
        "source_identity": result.source_identity,
        "repository_alias_observation": result.repository_alias_observation,
        "projected_locator": result.projected_locator,
        "reasons": result.reasons,
        "projection_basis": result.projection_basis,
    }
    data.update(overrides)
    return data


def test_compatibility_status_vocabulary_is_exact() -> None:
    expected = (
        "native",
        "losslessly_mappable",
        "partially_mappable",
        "not_mappable",
        "unsupported_version",
        "conflict",
    )

    assert tuple(status.value for status in CompatibilityStatus) == expected
    assert tuple(CompatibilityStatus.__members__) == tuple(
        status.name for status in CompatibilityStatus
    )
    assert [json.loads(json.dumps(status)) for status in CompatibilityStatus] == list(
        expected
    )


def test_legacy_object_id_interpretation_vocabulary_is_exact() -> None:
    expected = (
        "repository_scoped_number",
        "provider_global_id",
        "unresolved",
    )

    assert tuple(item.value for item in LegacyObjectIdInterpretation) == expected
    assert len(LegacyObjectIdInterpretation.__members__) == len(expected)


def test_legacy_compatibility_reason_vocabulary_is_exact_unique_and_stable() -> None:
    expected = (
        "legacy_alias_observation_mismatch",
        "repository_or_provider_context_mismatch",
        "legacy_object_id_role_ambiguous",
        "repository_scoped_issue_number_unavailable",
        "stable_repository_identity_not_represented",
        "alias_authority_not_represented",
        "alias_observation_time_not_represented",
        "schema_version_not_represented",
        "source_object_kind_unsupported",
        "provider_unsupported",
        "alias_lexeme_not_exactly_representable",
        "child_parent_scope_not_represented",
        "legacy_issue_object_identity_unavailable",
    )

    assert tuple(reason.value for reason in LegacyCompatibilityReason) == expected
    assert len(LegacyCompatibilityReason.__members__) == len(expected)
    assert len(set(LegacyCompatibilityReason)) == len(expected)
    assert [json.loads(json.dumps(reason)) for reason in LegacyCompatibilityReason] == (
        list(expected)
    )


def test_compatibility_module_exports_exactly_seven_internal_symbols() -> None:
    assert tuple(compatibility_module.__all__) == EXPECTED_EXPORTS
    assert len(set(compatibility_module.__all__)) == 7


def test_compatibility_module_import_boundary_is_exact_and_side_effect_free() -> None:
    source = (REPOSITORY_ROOT / "src/faultatlas/domain/compatibility.py").read_bytes()
    tree = ast.parse(source)
    imported_modules = {
        node.module
        for node in tree.body
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }

    assert not any(isinstance(node, ast.Import) for node in tree.body)
    assert imported_modules == {
        "enum",
        "typing",
        "pydantic",
        "faultatlas.domain.identity",
        "faultatlas.domain.source",
    }


def test_result_models_have_exact_fields_and_strict_frozen_configuration() -> None:
    assert tuple(LegacySourceLocatorMappingResult.model_fields) == (
        "schema_version",
        "status",
        "legacy_locator",
        "repository_alias_observation",
        "object_id_interpretation",
        "object_id_state",
        "mapped_identity",
        "reasons",
        "mapping_basis",
    )
    assert tuple(LegacySourceLocatorProjectionResult.model_fields) == (
        "schema_version",
        "status",
        "source_identity",
        "repository_alias_observation",
        "projected_locator",
        "reasons",
        "projection_basis",
    )
    for model in (
        LegacySourceLocatorMappingResult,
        LegacySourceLocatorProjectionResult,
    ):
        assert model.model_config.get("frozen") is True
        assert model.model_config.get("strict") is True
        assert model.model_config.get("extra") == "forbid"
        assert model.model_config.get("revalidate_instances") == "always"
        assert model.model_config.get("validate_default") is True


def test_repository_scoped_mapping_is_lossless_within_declared_basis() -> None:
    result = _map(LegacyObjectIdInterpretation.REPOSITORY_SCOPED_NUMBER)

    assert result.schema_version == 1
    assert result.status is CompatibilityStatus.LOSSLESSLY_MAPPABLE
    assert result.mapping_basis == "legacy_locator_plus_explicit_repository_context"
    assert result.reasons == ()
    assert result.object_id_state.state is IdentityFieldState.PRESENT
    assert isinstance(result.object_id_state.value, RepositoryScopedNumber)
    assert result.object_id_state.value.root == "4412"
    assert result.object_id_state.conflict_candidates == ()
    assert result.mapped_identity == _numbered()


def test_stable_repository_enters_mapped_issue_while_alias_does_not() -> None:
    observation = _alias_observation(repository=_repository(repository_id="987654321"))
    result = _map(
        LegacyObjectIdInterpretation.REPOSITORY_SCOPED_NUMBER,
        observation=observation,
    )

    assert result.mapped_identity is not None
    assert result.mapped_identity.repository_identity == observation.repository_identity
    assert "observed_alias" not in result.mapped_identity.model_dump(mode="json")
    assert "pytest-dev/pytest" not in result.mapped_identity.model_dump_json()


def test_provider_global_mapping_is_partial_and_fabricates_no_issue_number() -> None:
    result = _map(
        LegacyObjectIdInterpretation.PROVIDER_GLOBAL_ID,
        locator=_legacy_locator("381866787"),
    )

    assert result.status is CompatibilityStatus.PARTIALLY_MAPPABLE
    assert result.mapped_identity is None
    assert result.reasons == (
        LegacyCompatibilityReason.REPOSITORY_SCOPED_ISSUE_NUMBER_UNAVAILABLE,
    )
    assert result.object_id_state.state is IdentityFieldState.PRESENT
    assert isinstance(result.object_id_state.value, ProviderGlobalId)
    assert result.object_id_state.value.root == "381866787"


def test_unresolved_mapping_preserves_two_ordered_typed_candidates() -> None:
    result = _map(LegacyObjectIdInterpretation.UNRESOLVED)

    assert result.status is CompatibilityStatus.CONFLICT
    assert result.mapped_identity is None
    assert result.reasons == (
        LegacyCompatibilityReason.LEGACY_OBJECT_ID_ROLE_AMBIGUOUS,
    )
    assert result.object_id_state.state is IdentityFieldState.CONFLICT
    assert result.object_id_state.value is None
    assert tuple(type(item) for item in result.object_id_state.conflict_candidates) == (
        RepositoryScopedNumber,
        ProviderGlobalId,
    )
    assert tuple(item.root for item in result.object_id_state.conflict_candidates) == (
        "4412",
        "4412",
    )


def test_same_lexeme_changes_role_only_through_explicit_interpretation() -> None:
    locator = _legacy_locator("4412")
    scoped = _map(
        LegacyObjectIdInterpretation.REPOSITORY_SCOPED_NUMBER,
        locator=locator,
    )
    global_id = _map(
        LegacyObjectIdInterpretation.PROVIDER_GLOBAL_ID,
        locator=locator,
    )
    unresolved = _map(LegacyObjectIdInterpretation.UNRESOLVED, locator=locator)

    assert isinstance(scoped.object_id_state.value, RepositoryScopedNumber)
    assert isinstance(global_id.object_id_state.value, ProviderGlobalId)
    assert unresolved.object_id_state.state is IdentityFieldState.CONFLICT
    assert {result.legacy_locator.object_id for result in (scoped, global_id)} == {
        "4412"
    }


@pytest.mark.parametrize("lexeme", ["1", "9" * 20])
def test_digit_length_never_selects_an_object_id_role(lexeme: str) -> None:
    locator = _legacy_locator(lexeme)

    scoped = _map(
        LegacyObjectIdInterpretation.REPOSITORY_SCOPED_NUMBER,
        locator=locator,
    )
    global_id = _map(
        LegacyObjectIdInterpretation.PROVIDER_GLOBAL_ID,
        locator=locator,
    )

    assert isinstance(scoped.object_id_state.value, RepositoryScopedNumber)
    assert isinstance(global_id.object_id_state.value, ProviderGlobalId)


def test_mapping_requires_explicit_interpretation() -> None:
    signature = inspect.signature(map_legacy_source_locator)

    assert (
        signature.parameters["object_id_interpretation"].default
        is inspect.Parameter.empty
    )
    with pytest.raises(TypeError):
        signature.bind(
            _legacy_locator(),
            repository_alias_observation=_alias_observation(),
        )


def test_mapping_rejects_raw_interpretation_strings() -> None:
    with pytest.raises(ValidationError):
        map_legacy_source_locator(
            _legacy_locator(),
            repository_alias_observation=_alias_observation(),
            object_id_interpretation=cast(
                LegacyObjectIdInterpretation,
                "repository_scoped_number",
            ),
        )


def test_alias_mismatch_is_an_unreconciled_conflict() -> None:
    result = _map(
        LegacyObjectIdInterpretation.REPOSITORY_SCOPED_NUMBER,
        observation=_alias_observation(alias="other/repository"),
    )

    assert result.status is CompatibilityStatus.CONFLICT
    assert result.mapped_identity is None
    assert result.reasons == (
        LegacyCompatibilityReason.LEGACY_ALIAS_OBSERVATION_MISMATCH,
    )


def test_provider_context_mismatch_is_an_unreconciled_conflict() -> None:
    gitlab_repository = _repository(provider=_provider("gitlab"))
    result = _map(
        LegacyObjectIdInterpretation.REPOSITORY_SCOPED_NUMBER,
        observation=_alias_observation(repository=gitlab_repository),
    )

    assert result.status is CompatibilityStatus.CONFLICT
    assert result.mapped_identity is None
    assert result.reasons == (
        LegacyCompatibilityReason.REPOSITORY_OR_PROVIDER_CONTEXT_MISMATCH,
    )


def test_context_and_interpretation_reasons_have_deterministic_order() -> None:
    gitlab_repository = _repository(provider=_provider("gitlab"))
    result = _map(
        LegacyObjectIdInterpretation.UNRESOLVED,
        observation=_alias_observation(
            repository=gitlab_repository,
            alias="other/repository",
        ),
    )

    assert result.reasons == (
        LegacyCompatibilityReason.REPOSITORY_OR_PROVIDER_CONTEXT_MISMATCH,
        LegacyCompatibilityReason.LEGACY_ALIAS_OBSERVATION_MISMATCH,
        LegacyCompatibilityReason.LEGACY_OBJECT_ID_ROLE_AMBIGUOUS,
    )


@pytest.mark.parametrize("interpretation", tuple(LegacyObjectIdInterpretation))
def test_mapping_result_round_trips_semantic_json_without_type_inference(
    interpretation: LegacyObjectIdInterpretation,
) -> None:
    locator = _legacy_locator(
        "381866787"
        if interpretation is LegacyObjectIdInterpretation.PROVIDER_GLOBAL_ID
        else "4412"
    )
    result = _map(interpretation, locator=locator)

    reconstructed = LegacySourceLocatorMappingResult.model_validate_json(
        result.model_dump_json()
    )

    assert reconstructed == result
    assert reconstructed.model_dump_json() == result.model_dump_json()
    if interpretation is LegacyObjectIdInterpretation.UNRESOLVED:
        assert tuple(
            type(item) for item in reconstructed.object_id_state.conflict_candidates
        ) == (RepositoryScopedNumber, ProviderGlobalId)


def test_mapping_json_rejects_a_changed_union_candidate() -> None:
    result = _map(LegacyObjectIdInterpretation.UNRESOLVED)
    payload = json.loads(result.model_dump_json())
    payload["object_id_state"]["conflict_candidates"][1] = "4413"

    with pytest.raises(ValidationError):
        LegacySourceLocatorMappingResult.model_validate_json(json.dumps(payload))


def test_mapping_context_conflict_round_trips_with_all_ordered_reasons() -> None:
    gitlab_repository = _repository(provider=_provider("gitlab"))
    result = _map(
        LegacyObjectIdInterpretation.UNRESOLVED,
        observation=_alias_observation(
            repository=gitlab_repository,
            alias="other/repository",
        ),
    )

    reconstructed = LegacySourceLocatorMappingResult.model_validate_json(
        result.model_dump_json()
    )

    assert reconstructed == result
    assert reconstructed.reasons == result.reasons


def test_mapping_does_not_mutate_its_inputs() -> None:
    locator = _legacy_locator()
    observation = _alias_observation()
    before = (locator.model_dump_json(), observation.model_dump_json())

    _map(
        LegacyObjectIdInterpretation.REPOSITORY_SCOPED_NUMBER,
        locator=locator,
        observation=observation,
    )

    assert (locator.model_dump_json(), observation.model_dump_json()) == before


def test_mapping_result_rejects_lossless_without_mapped_identity() -> None:
    result = _map(LegacyObjectIdInterpretation.REPOSITORY_SCOPED_NUMBER)
    with pytest.raises(ValidationError):
        LegacySourceLocatorMappingResult.model_validate(
            _mapping_data(result, mapped_identity=None)
        )


def test_mapping_result_rejects_lossless_with_a_reason() -> None:
    result = _map(LegacyObjectIdInterpretation.REPOSITORY_SCOPED_NUMBER)
    with pytest.raises(ValidationError):
        LegacySourceLocatorMappingResult.model_validate(
            _mapping_data(
                result,
                reasons=(LegacyCompatibilityReason.SCHEMA_VERSION_NOT_REPRESENTED,),
            )
        )


def test_mapping_result_rejects_partial_relabelled_lossless() -> None:
    result = _map(LegacyObjectIdInterpretation.PROVIDER_GLOBAL_ID)
    with pytest.raises(ValidationError):
        LegacySourceLocatorMappingResult.model_validate(
            _mapping_data(result, status=CompatibilityStatus.LOSSLESSLY_MAPPABLE)
        )


def test_mapping_result_rejects_partial_with_a_mapped_issue() -> None:
    result = _map(LegacyObjectIdInterpretation.PROVIDER_GLOBAL_ID)
    with pytest.raises(ValidationError):
        LegacySourceLocatorMappingResult.model_validate(
            _mapping_data(result, mapped_identity=_numbered())
        )


def test_mapping_result_rejects_partial_without_reasons() -> None:
    result = _map(LegacyObjectIdInterpretation.PROVIDER_GLOBAL_ID)
    with pytest.raises(ValidationError):
        LegacySourceLocatorMappingResult.model_validate(
            _mapping_data(result, reasons=())
        )


def test_mapping_result_rejects_conflict_with_a_mapped_identity() -> None:
    result = _map(LegacyObjectIdInterpretation.UNRESOLVED)
    with pytest.raises(ValidationError):
        LegacySourceLocatorMappingResult.model_validate(
            _mapping_data(result, mapped_identity=_numbered())
        )


def test_mapping_result_rejects_unresolved_state_with_selected_winner() -> None:
    result = _map(LegacyObjectIdInterpretation.UNRESOLVED)
    selected = result.object_id_state.model_copy(
        update={
            "state": IdentityFieldState.PRESENT,
            "value": RepositoryScopedNumber.model_validate("4412"),
            "conflict_candidates": (),
        }
    )

    with pytest.raises(ValidationError):
        LegacySourceLocatorMappingResult.model_validate(
            _mapping_data(result, object_id_state=selected)
        )


def test_mapping_result_rejects_wrong_candidate_order_and_types() -> None:
    result = _map(LegacyObjectIdInterpretation.UNRESOLVED)
    reversed_candidates = result.object_id_state.model_copy(
        update={
            "conflict_candidates": (
                ProviderGlobalId.model_validate("4412"),
                RepositoryScopedNumber.model_validate("4412"),
            )
        }
    )

    with pytest.raises(ValidationError):
        LegacySourceLocatorMappingResult.model_validate(
            _mapping_data(result, object_id_state=reversed_candidates)
        )


def test_mapping_result_rejects_mapped_identity_from_another_repository() -> None:
    result = _map(LegacyObjectIdInterpretation.REPOSITORY_SCOPED_NUMBER)
    with pytest.raises(ValidationError):
        LegacySourceLocatorMappingResult.model_validate(
            _mapping_data(
                result,
                mapped_identity=_numbered(
                    repository=_repository(repository_id="99999999")
                ),
            )
        )


def test_mapping_result_rejects_duplicate_or_reordered_reasons() -> None:
    result = _map(LegacyObjectIdInterpretation.PROVIDER_GLOBAL_ID)
    reason = LegacyCompatibilityReason.REPOSITORY_SCOPED_ISSUE_NUMBER_UNAVAILABLE
    with pytest.raises(ValidationError):
        LegacySourceLocatorMappingResult.model_validate(
            _mapping_data(result, reasons=(reason, reason))
        )

    context = _map(
        LegacyObjectIdInterpretation.UNRESOLVED,
        observation=_alias_observation(alias="other/repository"),
    )
    with pytest.raises(ValidationError):
        LegacySourceLocatorMappingResult.model_validate(
            _mapping_data(context, reasons=tuple(reversed(context.reasons)))
        )


@pytest.mark.parametrize(
    "status",
    [
        CompatibilityStatus.NATIVE,
        CompatibilityStatus.NOT_MAPPABLE,
        CompatibilityStatus.UNSUPPORTED_VERSION,
    ],
)
def test_mapping_result_rejects_disallowed_output_statuses(
    status: CompatibilityStatus,
) -> None:
    result = _map(LegacyObjectIdInterpretation.REPOSITORY_SCOPED_NUMBER)
    with pytest.raises(ValidationError):
        LegacySourceLocatorMappingResult.model_validate(
            _mapping_data(result, status=status)
        )


def test_mapping_result_rejects_raw_state_and_extra_fields() -> None:
    result = _map(LegacyObjectIdInterpretation.REPOSITORY_SCOPED_NUMBER)
    raw_state = _mapping_data(
        result,
        object_id_state=result.object_id_state.model_dump(mode="python"),
    )
    extra = _mapping_data(result)
    extra["confidence"] = 1

    for data in (raw_state, extra):
        with pytest.raises(ValidationError):
            LegacySourceLocatorMappingResult.model_validate(data)


def test_mapping_result_is_frozen() -> None:
    result = _map(LegacyObjectIdInterpretation.REPOSITORY_SCOPED_NUMBER)

    with pytest.raises(ValidationError) as error:
        result.status = CompatibilityStatus.CONFLICT

    assert error.value.errors()[0]["type"] == "frozen_instance"


def test_typed_issue_projects_partially_with_exact_alias_and_losses() -> None:
    identity = _numbered()
    observation = _alias_observation()
    result = project_source_identity_to_legacy(
        identity,
        repository_alias_observation=observation,
    )

    assert result.schema_version == 1
    assert result.status is CompatibilityStatus.PARTIALLY_MAPPABLE
    assert result.projected_locator == _legacy_locator()
    assert result.projected_locator is not None
    assert result.projected_locator.repository == observation.observed_alias
    assert result.reasons == EXPECTED_ISSUE_PROJECTION_REASONS
    assert result.projection_basis == (
        "source_identity_plus_explicit_repository_alias_observation"
    )


def test_pull_request_is_not_projected_as_an_issue() -> None:
    identity = _numbered(kind=SourceObjectKind.PULL_REQUEST, number="4414")
    result = project_source_identity_to_legacy(
        identity,
        repository_alias_observation=_alias_observation(),
    )

    assert result.status is CompatibilityStatus.NOT_MAPPABLE
    assert result.projected_locator is None
    assert result.reasons == (LegacyCompatibilityReason.SOURCE_OBJECT_KIND_UNSUPPORTED,)


@pytest.mark.parametrize(
    ("kind", "parent_kind", "global_id"),
    [
        (SourceObjectKind.ISSUE_COMMENT, SourceObjectKind.ISSUE, "439722704"),
        (
            SourceObjectKind.PULL_REQUEST_REVIEW,
            SourceObjectKind.PULL_REQUEST,
            "176071572",
        ),
    ],
)
def test_child_identity_is_not_projected_without_parent_scope(
    kind: SourceObjectKind,
    parent_kind: SourceObjectKind,
    global_id: str,
) -> None:
    child = _child(
        parent=_numbered(kind=parent_kind, number="4414"),
        kind=kind,
        global_id=global_id,
    )
    result = project_source_identity_to_legacy(
        child,
        repository_alias_observation=_alias_observation(),
    )

    assert result.status is CompatibilityStatus.NOT_MAPPABLE
    assert result.projected_locator is None
    assert result.reasons == (
        LegacyCompatibilityReason.SOURCE_OBJECT_KIND_UNSUPPORTED,
        LegacyCompatibilityReason.CHILD_PARENT_SCOPE_NOT_REPRESENTED,
    )


def test_repository_identity_without_an_issue_is_not_mappable() -> None:
    result = project_source_identity_to_legacy(
        _repository(),
        repository_alias_observation=_alias_observation(),
    )

    assert result.status is CompatibilityStatus.NOT_MAPPABLE
    assert result.reasons == (
        LegacyCompatibilityReason.LEGACY_ISSUE_OBJECT_IDENTITY_UNAVAILABLE,
    )


def test_unsupported_provider_is_not_mappable() -> None:
    repository = _repository(provider=_provider("gitlab"))
    result = project_source_identity_to_legacy(
        _numbered(repository=repository),
        repository_alias_observation=_alias_observation(repository=repository),
    )

    assert result.status is CompatibilityStatus.NOT_MAPPABLE
    assert result.projected_locator is None
    assert result.reasons == (LegacyCompatibilityReason.PROVIDER_UNSUPPORTED,)


def test_projection_repository_mismatch_is_a_conflict() -> None:
    result = project_source_identity_to_legacy(
        _numbered(),
        repository_alias_observation=_alias_observation(
            repository=_repository(repository_id="99999999")
        ),
    )

    assert result.status is CompatibilityStatus.CONFLICT
    assert result.projected_locator is None
    assert result.reasons == (
        LegacyCompatibilityReason.REPOSITORY_OR_PROVIDER_CONTEXT_MISMATCH,
    )


@pytest.mark.parametrize("alias", ["Pytest-Dev/Pytest", "not a repository"])
def test_projection_never_normalizes_or_rewrites_alias_lexemes(alias: str) -> None:
    result = project_source_identity_to_legacy(
        _numbered(),
        repository_alias_observation=_alias_observation(alias=alias),
    )

    assert result.status is CompatibilityStatus.NOT_MAPPABLE
    assert result.projected_locator is None
    assert result.reasons == (
        LegacyCompatibilityReason.ALIAS_LEXEME_NOT_EXACTLY_REPRESENTABLE,
    )


@pytest.mark.parametrize(
    "identity",
    [
        pytest.param(_repository(), id="repository"),
        pytest.param(_numbered(), id="issue"),
        pytest.param(
            _numbered(kind=SourceObjectKind.PULL_REQUEST, number="4414"),
            id="pull-request",
        ),
        pytest.param(_child(), id="child"),
    ],
)
def test_no_projection_is_reported_lossless(identity: SourceIdentity) -> None:
    result = project_source_identity_to_legacy(
        identity,
        repository_alias_observation=_alias_observation(),
    )

    assert result.status is not CompatibilityStatus.LOSSLESSLY_MAPPABLE
    assert result.status is not CompatibilityStatus.NATIVE


@pytest.mark.parametrize(
    "identity",
    [
        pytest.param(_repository(), id="repository"),
        pytest.param(_numbered(), id="issue"),
        pytest.param(
            _numbered(kind=SourceObjectKind.PULL_REQUEST, number="4414"),
            id="pull-request",
        ),
        pytest.param(_child(), id="child"),
    ],
)
def test_projection_result_round_trips_semantic_json(identity: SourceIdentity) -> None:
    result = project_source_identity_to_legacy(
        identity,
        repository_alias_observation=_alias_observation(),
    )

    reconstructed = LegacySourceLocatorProjectionResult.model_validate_json(
        result.model_dump_json()
    )

    assert reconstructed == result
    assert reconstructed.model_dump_json() == result.model_dump_json()


def test_projection_does_not_mutate_its_inputs() -> None:
    identity = _numbered()
    observation = _alias_observation()
    before = (identity.model_dump_json(), observation.model_dump_json())

    project_source_identity_to_legacy(
        identity,
        repository_alias_observation=observation,
    )

    assert (identity.model_dump_json(), observation.model_dump_json()) == before


def test_projection_result_rejects_locator_with_not_mappable_status() -> None:
    result = project_source_identity_to_legacy(
        _numbered(kind=SourceObjectKind.PULL_REQUEST, number="4414"),
        repository_alias_observation=_alias_observation(),
    )
    with pytest.raises(ValidationError):
        LegacySourceLocatorProjectionResult.model_validate(
            _projection_data(result, projected_locator=_legacy_locator("4414"))
        )


def test_projection_result_rejects_partial_without_locator_or_losses() -> None:
    result = project_source_identity_to_legacy(
        _numbered(),
        repository_alias_observation=_alias_observation(),
    )
    for overrides in (
        {"projected_locator": None},
        {"reasons": ()},
    ):
        with pytest.raises(ValidationError):
            LegacySourceLocatorProjectionResult.model_validate(
                _projection_data(result, **overrides)
            )


def test_projection_result_rejects_pr_projected_as_issue() -> None:
    result = project_source_identity_to_legacy(
        _numbered(),
        repository_alias_observation=_alias_observation(),
    )
    with pytest.raises(ValidationError):
        LegacySourceLocatorProjectionResult.model_validate(
            _projection_data(
                result,
                source_identity=_numbered(
                    kind=SourceObjectKind.PULL_REQUEST,
                    number="4414",
                ),
                projected_locator=_legacy_locator("4414"),
            )
        )


def test_projection_result_rejects_child_projected_without_parent_scope() -> None:
    result = project_source_identity_to_legacy(
        _child(),
        repository_alias_observation=_alias_observation(),
    )
    with pytest.raises(ValidationError):
        LegacySourceLocatorProjectionResult.model_validate(
            _projection_data(
                result,
                status=CompatibilityStatus.PARTIALLY_MAPPABLE,
                projected_locator=_legacy_locator(),
                reasons=EXPECTED_ISSUE_PROJECTION_REASONS,
            )
        )


def test_projection_result_rejects_conflict_without_mismatch_reason() -> None:
    result = project_source_identity_to_legacy(
        _numbered(),
        repository_alias_observation=_alias_observation(
            repository=_repository(repository_id="99999999")
        ),
    )
    with pytest.raises(ValidationError):
        LegacySourceLocatorProjectionResult.model_validate(
            _projection_data(result, reasons=())
        )


@pytest.mark.parametrize(
    "status",
    [
        CompatibilityStatus.NATIVE,
        CompatibilityStatus.LOSSLESSLY_MAPPABLE,
        CompatibilityStatus.UNSUPPORTED_VERSION,
    ],
)
def test_projection_result_rejects_disallowed_output_statuses(
    status: CompatibilityStatus,
) -> None:
    result = project_source_identity_to_legacy(
        _numbered(),
        repository_alias_observation=_alias_observation(),
    )
    with pytest.raises(ValidationError):
        LegacySourceLocatorProjectionResult.model_validate(
            _projection_data(result, status=status)
        )


def test_projection_result_rejects_duplicate_reasons_raw_identity_and_extra() -> None:
    result = project_source_identity_to_legacy(
        _numbered(),
        repository_alias_observation=_alias_observation(),
    )
    duplicate = _projection_data(
        result,
        reasons=(result.reasons[0], result.reasons[0]),
    )
    raw_identity = _projection_data(
        result,
        source_identity=result.source_identity.model_dump(mode="python"),
    )
    extra = _projection_data(result)
    extra["review_status"] = "accepted"

    for data in (duplicate, raw_identity, extra):
        with pytest.raises(ValidationError):
            LegacySourceLocatorProjectionResult.model_validate(data)


def test_projection_result_is_frozen() -> None:
    result = project_source_identity_to_legacy(
        _numbered(),
        repository_alias_observation=_alias_observation(),
    )

    with pytest.raises(ValidationError) as error:
        result.projected_locator = None

    assert error.value.errors()[0]["type"] == "frozen_instance"


def test_legacy_source_module_bytes_and_class_fields_are_unchanged() -> None:
    source = SOURCE_PATH.read_bytes()

    assert hashlib.sha256(source).hexdigest() == EXPECTED_SOURCE_SHA256
    assert tuple(SourceLocator.model_fields) == (
        "provider",
        "repository",
        "object_kind",
        "object_id",
    )


def test_legacy_normalization_issue_kind_and_object_id_grammar_are_unchanged() -> None:
    locator = SourceLocator(
        provider="github",
        repository="Pytest-Dev/Pytest",
        object_kind="issue",
        object_id="4412",
    )

    assert locator.repository == "pytest-dev/pytest"
    with pytest.raises(ValidationError):
        SourceLocator(
            provider="github",
            repository="pytest-dev/pytest",
            object_kind="pull_request",  # type: ignore[arg-type]
            object_id="4414",
        )
    for invalid in ("0", "01", "-1", "9" * 21):
        with pytest.raises(ValidationError):
            SourceLocator(
                provider="github",
                repository="pytest-dev/pytest",
                object_kind="issue",
                object_id=invalid,
            )


def test_no_compatibility_method_was_added_to_source_locator() -> None:
    direct_methods = {
        name
        for name, value in SourceLocator.__dict__.items()
        if not name.startswith("__")
        and (callable(value) or isinstance(value, classmethod))
    }

    assert direct_methods == {"_normalize_repository"}
    assert not hasattr(SourceLocator, "map_legacy_source_locator")
    assert not hasattr(SourceLocator, "project_source_identity_to_legacy")


def test_compatibility_symbols_are_not_package_root_or_domain_exports() -> None:
    assert faultatlas.__all__ == ["__version__"]
    for name in EXPECTED_EXPORTS:
        assert not hasattr(faultatlas, name)
        assert not hasattr(domain_package, name)


def test_compatibility_surface_excludes_later_phase_concepts() -> None:
    forbidden_public_names = {
        "AlternateIdBinding",
        "Confidence",
        "EvidenceEnvelope",
        "GitObjectIdentity",
        "IdentityReview",
        "LifecycleTransition",
        "Migration",
        "Persistence",
        "RepositorySnapshot",
        "resolve_conflict",
    }

    assert forbidden_public_names.isdisjoint(compatibility_module.__all__)
    assert all("migrate" not in name.lower() for name in compatibility_module.__all__)
