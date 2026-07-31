from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta, timezone
from typing import cast, get_args

import pytest
from pydantic import BaseModel, ValidationError

import faultatlas
import faultatlas.domain as domain_package
import faultatlas.domain.identity as identity_module
from faultatlas.domain.identity import (
    AuthorityRole,
    IdentityFieldState,
    IdentityValueState,
    NumberedSourceObjectIdentity,
    ProviderAuthority,
    ProviderGlobalId,
    ProviderKey,
    ProviderNodeId,
    ProviderRepositoryId,
    ProviderScopedSourceObjectIdentity,
    RepositoryAliasObservation,
    RepositoryIdentity,
    RepositoryScopedNumber,
    SourceIdentity,
    SourceIdentityLifecycleObservation,
    SourceIdentityLifecycleState,
    SourceObjectKind,
)

_ABSENT_FIELD_STATES = (
    IdentityFieldState.OBSERVED_NULL,
    IdentityFieldState.MISSING,
    IdentityFieldState.UNAVAILABLE,
    IdentityFieldState.INACCESSIBLE,
    IdentityFieldState.DELETED,
    IdentityFieldState.UNKNOWN,
    IdentityFieldState.UNSUPPORTED,
)


def _provider(value: str = "github") -> ProviderKey:
    return ProviderKey.model_validate(value)


def _authority(
    provider: ProviderKey | None = None,
    *,
    role: AuthorityRole = AuthorityRole.RETRIEVAL,
    host: str = "api.github.com",
) -> ProviderAuthority:
    return ProviderAuthority.model_validate(
        {
            "provider": provider or _provider(),
            "role": role,
            "host": host,
        }
    )


def _repository(
    provider: ProviderKey | None = None,
    *,
    repository_id: str = "37489525",
) -> RepositoryIdentity:
    return RepositoryIdentity.model_validate(
        {
            "provider": provider or _provider(),
            "provider_repository_id": ProviderRepositoryId.model_validate(
                repository_id
            ),
        }
    )


def _numbered(
    *,
    repository: RepositoryIdentity | None = None,
    kind: SourceObjectKind = SourceObjectKind.ISSUE,
    number: str = "4412",
) -> NumberedSourceObjectIdentity:
    return NumberedSourceObjectIdentity.model_validate(
        {
            "repository_identity": repository or _repository(),
            "kind": kind,
            "repository_scoped_number": RepositoryScopedNumber.model_validate(number),
        }
    )


def _child(
    *,
    parent: NumberedSourceObjectIdentity | None = None,
    kind: SourceObjectKind = SourceObjectKind.ISSUE_COMMENT,
    global_id: str = "439722704",
) -> ProviderScopedSourceObjectIdentity:
    return ProviderScopedSourceObjectIdentity.model_validate(
        {
            "kind": kind,
            "provider_global_id": ProviderGlobalId.model_validate(global_id),
            "parent": parent or _numbered(),
        }
    )


def _alias_observation() -> RepositoryAliasObservation:
    return RepositoryAliasObservation.model_validate(
        {
            "repository_identity": _repository(),
            "observed_alias": "pytest-dev/pytest",
            "authority": _authority(
                role=AuthorityRole.NAVIGATION,
                host="github.com",
            ),
            "observed_at": datetime(2026, 7, 24, 11, 3, tzinfo=UTC),
        }
    )


def _lifecycle(
    identity: SourceIdentity,
    *,
    state: SourceIdentityLifecycleState = (
        SourceIdentityLifecycleState.OBSERVED_PRESENT
    ),
    authority: ProviderAuthority | None = None,
    observed_at: datetime | str = datetime(2026, 7, 24, 11, 3, tzinfo=UTC),
) -> SourceIdentityLifecycleObservation:
    return SourceIdentityLifecycleObservation.model_validate(
        {
            "identity": identity,
            "state": state,
            "authority": authority or _authority(),
            "observed_at": observed_at,
        }
    )


def test_identity_field_state_vocabulary_is_exact_unique_and_stable() -> None:
    expected = (
        "present",
        "observed_null",
        "missing",
        "unavailable",
        "inaccessible",
        "deleted",
        "unknown",
        "unsupported",
        "conflict",
    )

    assert tuple(item.value for item in IdentityFieldState) == expected
    assert len(IdentityFieldState.__members__) == len(expected)
    assert len(set(IdentityFieldState)) == len(expected)
    assert [json.loads(json.dumps(item)) for item in IdentityFieldState] == list(
        expected
    )


@pytest.mark.parametrize(
    "value",
    ["null", "absent", "not_found", "ambiguous", "resolved", "open", "closed"],
)
def test_identity_field_state_rejects_implicit_or_business_aliases(
    value: str,
) -> None:
    with pytest.raises(ValueError):
        IdentityFieldState(value)


def test_provider_global_id_present_state_is_typed() -> None:
    value = ProviderGlobalId.model_validate("381866787")
    record = IdentityValueState[ProviderGlobalId](
        state=IdentityFieldState.PRESENT,
        value=value,
    )

    assert record.schema_version == 1
    assert record.state is IdentityFieldState.PRESENT
    assert record.value == value
    assert isinstance(record.value, ProviderGlobalId)
    assert record.conflict_candidates == ()


def test_provider_node_id_present_state_is_typed() -> None:
    value = ProviderNodeId.model_validate("MDU6SXNzdWUzODE4NjY3ODc=")
    record = IdentityValueState[ProviderNodeId](
        state=IdentityFieldState.PRESENT,
        value=value,
    )

    assert record.value == value
    assert isinstance(record.value, ProviderNodeId)


def test_repository_scoped_number_present_state_is_typed() -> None:
    value = RepositoryScopedNumber.model_validate("4412")
    record = IdentityValueState[RepositoryScopedNumber](
        state=IdentityFieldState.PRESENT,
        value=value,
    )

    assert record.value == value
    assert isinstance(record.value, RepositoryScopedNumber)


@pytest.mark.parametrize("state", _ABSENT_FIELD_STATES)
def test_each_absent_field_state_has_no_value_or_candidates(
    state: IdentityFieldState,
) -> None:
    record = IdentityValueState[ProviderGlobalId](state=state)

    assert record.state is state
    assert record.value is None
    assert record.conflict_candidates == ()


def test_conflict_requires_explicit_ordered_typed_candidates() -> None:
    first = ProviderGlobalId.model_validate("381866787")
    second = ProviderGlobalId.model_validate("381866788")
    record = IdentityValueState[ProviderGlobalId](
        state=IdentityFieldState.CONFLICT,
        conflict_candidates=(second, first),
    )

    assert record.value is None
    assert record.conflict_candidates == (second, first)
    assert tuple(item.root for item in record.conflict_candidates) == (
        "381866788",
        "381866787",
    )


def test_present_state_requires_a_value() -> None:
    with pytest.raises(ValidationError) as error:
        IdentityValueState[ProviderGlobalId](state=IdentityFieldState.PRESENT)

    assert error.value.errors()[0]["loc"] == ()


def test_present_state_rejects_conflict_candidates() -> None:
    with pytest.raises(ValidationError) as error:
        IdentityValueState[ProviderGlobalId](
            state=IdentityFieldState.PRESENT,
            value=ProviderGlobalId.model_validate("381866787"),
            conflict_candidates=(
                ProviderGlobalId.model_validate("381866788"),
                ProviderGlobalId.model_validate("381866789"),
            ),
        )

    assert error.value.errors()[0]["loc"] == ()


def test_conflict_state_rejects_a_selected_value() -> None:
    with pytest.raises(ValidationError) as error:
        IdentityValueState[ProviderGlobalId](
            state=IdentityFieldState.CONFLICT,
            value=ProviderGlobalId.model_validate("381866787"),
            conflict_candidates=(
                ProviderGlobalId.model_validate("381866788"),
                ProviderGlobalId.model_validate("381866789"),
            ),
        )

    assert error.value.errors()[0]["loc"] == ()


@pytest.mark.parametrize(
    "candidates",
    [(), (ProviderGlobalId.model_validate("381866787"),)],
)
def test_conflict_state_requires_at_least_two_candidates(
    candidates: tuple[ProviderGlobalId, ...],
) -> None:
    with pytest.raises(ValidationError) as error:
        IdentityValueState[ProviderGlobalId](
            state=IdentityFieldState.CONFLICT,
            conflict_candidates=candidates,
        )

    assert error.value.errors()[0]["loc"] == ()


def test_conflict_state_rejects_semantically_duplicate_candidates() -> None:
    first = ProviderGlobalId.model_validate("381866787")
    same = ProviderGlobalId.model_validate("381866787")

    with pytest.raises(ValidationError) as error:
        IdentityValueState[ProviderGlobalId](
            state=IdentityFieldState.CONFLICT,
            conflict_candidates=(first, same),
        )

    assert error.value.errors()[0]["loc"] == ()


@pytest.mark.parametrize("state", _ABSENT_FIELD_STATES)
def test_absent_field_state_rejects_a_value(state: IdentityFieldState) -> None:
    with pytest.raises(ValidationError) as error:
        IdentityValueState[ProviderGlobalId](
            state=state,
            value=ProviderGlobalId.model_validate("381866787"),
        )

    assert error.value.errors()[0]["loc"] == ()


@pytest.mark.parametrize("state", _ABSENT_FIELD_STATES)
def test_absent_field_state_rejects_candidates(state: IdentityFieldState) -> None:
    with pytest.raises(ValidationError) as error:
        IdentityValueState[ProviderGlobalId](
            state=state,
            conflict_candidates=(
                ProviderGlobalId.model_validate("381866787"),
                ProviderGlobalId.model_validate("381866788"),
            ),
        )

    assert error.value.errors()[0]["loc"] == ()


def test_typed_state_rejects_cross_identifier_substitution() -> None:
    with pytest.raises(ValidationError) as error:
        IdentityValueState[ProviderGlobalId].model_validate(
            {
                "state": IdentityFieldState.PRESENT,
                "value": ProviderNodeId.model_validate("MDU6SXNzdWUzODE4NjY3ODc="),
            }
        )

    assert error.value.errors()[0]["loc"] == ("value",)


@pytest.mark.parametrize("value", ["381866787", 381866787, b"381866787"])
def test_typed_state_rejects_raw_python_value_coercion(value: object) -> None:
    with pytest.raises(ValidationError) as error:
        IdentityValueState[ProviderGlobalId].model_validate(
            {"state": IdentityFieldState.PRESENT, "value": value}
        )

    assert error.value.errors()[0]["loc"] == ("value",)


def test_typed_state_rejects_raw_python_candidate_coercion() -> None:
    with pytest.raises(ValidationError) as error:
        IdentityValueState[ProviderGlobalId].model_validate(
            {
                "state": IdentityFieldState.CONFLICT,
                "conflict_candidates": ("381866787", "381866788"),
            }
        )

    assert error.value.errors()[0]["loc"] == ("conflict_candidates",)


def test_typed_state_strictly_rejects_a_python_candidate_list() -> None:
    with pytest.raises(ValidationError) as error:
        IdentityValueState[ProviderGlobalId].model_validate(
            {
                "state": IdentityFieldState.CONFLICT,
                "conflict_candidates": [
                    ProviderGlobalId.model_validate("381866787"),
                    ProviderGlobalId.model_validate("381866788"),
                ],
            }
        )

    assert error.value.errors()[0]["loc"] == ("conflict_candidates",)


def test_typed_state_strictly_rejects_a_raw_python_state_string() -> None:
    with pytest.raises(ValidationError) as error:
        IdentityValueState[ProviderGlobalId].model_validate(
            {
                "state": "present",
                "value": ProviderGlobalId.model_validate("381866787"),
            }
        )

    assert error.value.errors()[0]["loc"] == ("state",)


def test_typed_state_requires_callers_to_name_the_state() -> None:
    with pytest.raises(ValidationError) as missing_error:
        IdentityValueState[ProviderGlobalId].model_validate(
            {"value": ProviderGlobalId.model_validate("381866787")}
        )
    with pytest.raises(ValidationError) as null_error:
        IdentityValueState[ProviderGlobalId].model_validate({"value": None})

    assert missing_error.value.errors()[0]["loc"] == ("state",)
    assert null_error.value.errors()[0]["loc"] == ("state",)


def test_unparameterized_identity_value_state_is_rejected() -> None:
    bare_carrier = cast(type[BaseModel], IdentityValueState)

    with pytest.raises(ValidationError) as python_error:
        bare_carrier.model_validate(
            {
                "state": IdentityFieldState.PRESENT,
                "value": ProviderGlobalId.model_validate("381866787"),
            }
        )
    with pytest.raises(ValidationError) as json_error:
        bare_carrier.model_validate_json(
            '{"schema_version":1,"state":"missing",'
            '"value":null,"conflict_candidates":[]}'
        )

    assert python_error.value.errors()[0]["loc"] == ()
    assert json_error.value.errors()[0]["loc"] == ()


def test_typed_state_revalidates_constructed_nested_values() -> None:
    invalid = ProviderGlobalId.model_construct(root="not spaced")

    with pytest.raises(ValidationError) as value_error:
        IdentityValueState[ProviderGlobalId](
            state=IdentityFieldState.PRESENT,
            value=invalid,
        )
    with pytest.raises(ValidationError) as candidate_error:
        IdentityValueState[ProviderGlobalId](
            state=IdentityFieldState.CONFLICT,
            conflict_candidates=(
                ProviderGlobalId.model_validate("381866787"),
                invalid,
            ),
        )

    assert value_error.value.errors()[0]["loc"] == ("value",)
    assert candidate_error.value.errors()[0]["loc"] == (
        "conflict_candidates",
        1,
    )


def test_typed_state_is_frozen_and_extra_forbidden() -> None:
    record = IdentityValueState[ProviderGlobalId](
        state=IdentityFieldState.PRESENT,
        value=ProviderGlobalId.model_validate("381866787"),
    )

    with pytest.raises(ValidationError) as mutation_error:
        setattr(record, "value", ProviderGlobalId.model_validate("381866788"))
    with pytest.raises(ValidationError) as extra_error:
        IdentityValueState[ProviderGlobalId].model_validate(
            {
                "state": IdentityFieldState.MISSING,
                "reason": "not retained",
            }
        )

    assert mutation_error.value.errors()[0]["type"] == "frozen_instance"
    assert extra_error.value.errors()[0]["type"] == "extra_forbidden"


@pytest.mark.parametrize("schema_version", [0, 2, "1"])
def test_typed_state_rejects_wrong_schema_version(
    schema_version: object,
) -> None:
    with pytest.raises(ValidationError):
        IdentityValueState[ProviderGlobalId].model_validate(
            {
                "schema_version": schema_version,
                "state": IdentityFieldState.MISSING,
            }
        )


def test_typed_state_fields_exclude_resolution_and_provenance() -> None:
    assert set(IdentityValueState[ProviderGlobalId].model_fields) == {
        "schema_version",
        "state",
        "value",
        "conflict_candidates",
    }
    forbidden = {
        "winner",
        "preferred_candidate",
        "confidence",
        "resolution",
        "evidence",
        "observed_at",
        "reason",
        "provider_request",
    }
    assert forbidden.isdisjoint(IdentityValueState[ProviderGlobalId].model_fields)


def test_typed_identifier_state_semantic_json_round_trip_is_deterministic() -> None:
    original = IdentityValueState[ProviderGlobalId](
        state=IdentityFieldState.CONFLICT,
        conflict_candidates=(
            ProviderGlobalId.model_validate("381866788"),
            ProviderGlobalId.model_validate("381866787"),
        ),
    )
    first_json = original.model_dump_json()
    reconstructed = IdentityValueState[ProviderGlobalId].model_validate_json(first_json)

    assert first_json == original.model_dump_json()
    assert reconstructed == original
    assert all(
        isinstance(candidate, ProviderGlobalId)
        for candidate in reconstructed.conflict_candidates
    )
    assert reconstructed.conflict_candidates == original.conflict_candidates
    assert json.loads(first_json) == original.model_dump(mode="json")


def test_each_required_identifier_specialization_round_trips_json() -> None:
    node = IdentityValueState[ProviderNodeId](
        state=IdentityFieldState.PRESENT,
        value=ProviderNodeId.model_validate("MDU6SXNzdWUzODE4NjY3ODc="),
    )
    number = IdentityValueState[RepositoryScopedNumber](
        state=IdentityFieldState.PRESENT,
        value=RepositoryScopedNumber.model_validate("4412"),
    )

    rebuilt_node = IdentityValueState[ProviderNodeId].model_validate_json(
        node.model_dump_json()
    )
    rebuilt_number = IdentityValueState[RepositoryScopedNumber].model_validate_json(
        number.model_dump_json()
    )

    assert rebuilt_node == node
    assert isinstance(rebuilt_node.value, ProviderNodeId)
    assert rebuilt_number == number
    assert isinstance(rebuilt_number.value, RepositoryScopedNumber)


@pytest.mark.parametrize("identity", [_repository(), _numbered(), _child()])
def test_each_stable_source_identity_may_be_present(
    identity: SourceIdentity,
) -> None:
    record = IdentityValueState[SourceIdentity](
        state=IdentityFieldState.PRESENT,
        value=identity,
    )
    reconstructed = IdentityValueState[SourceIdentity].model_validate_json(
        record.model_dump_json()
    )

    assert record.value == identity
    assert reconstructed == record
    assert type(reconstructed.value) is type(identity)


def test_source_identity_conflict_retains_different_explicit_identities() -> None:
    issue = _numbered()
    synthetic_pull_request = _numbered(kind=SourceObjectKind.PULL_REQUEST)
    record = IdentityValueState[SourceIdentity](
        state=IdentityFieldState.CONFLICT,
        conflict_candidates=(issue, synthetic_pull_request),
    )

    assert record.value is None
    assert record.conflict_candidates == (issue, synthetic_pull_request)
    first, second = record.conflict_candidates
    assert isinstance(first, NumberedSourceObjectIdentity)
    assert isinstance(second, NumberedSourceObjectIdentity)
    assert first.kind is SourceObjectKind.ISSUE
    assert second.kind is SourceObjectKind.PULL_REQUEST


@pytest.mark.parametrize("value", [_authority(), _alias_observation()])
def test_source_identity_state_rejects_nonidentity_observations(
    value: BaseModel,
) -> None:
    with pytest.raises(ValidationError) as error:
        IdentityValueState[SourceIdentity].model_validate(
            {"state": IdentityFieldState.PRESENT, "value": value}
        )

    assert error.value.errors()[0]["loc"] == ("value",)


def test_source_identity_state_rejects_source_index_and_unnamed_none() -> None:
    with pytest.raises(ValidationError) as index_error:
        IdentityValueState[SourceIdentity].model_validate(
            {
                "state": IdentityFieldState.PRESENT,
                "value": _numbered(),
                "source_index": 17,
            }
        )
    with pytest.raises(ValidationError) as null_error:
        IdentityValueState[SourceIdentity].model_validate({"value": None})

    assert index_error.value.errors()[0]["type"] == "extra_forbidden"
    assert null_error.value.errors()[0]["loc"] == ("state",)


def test_source_identity_union_has_only_the_three_stable_identity_members() -> None:
    accepted: tuple[SourceIdentity, ...] = (_repository(), _numbered(), _child())

    for identity in accepted:
        record = IdentityValueState[SourceIdentity](
            state=IdentityFieldState.PRESENT,
            value=identity,
        )
        assert record.value == identity

    assert get_args(SourceIdentity.__value__) == (
        RepositoryIdentity,
        NumberedSourceObjectIdentity,
        ProviderScopedSourceObjectIdentity,
    )


def test_lifecycle_state_vocabulary_is_exact_unique_and_stable() -> None:
    expected = (
        "observed_present",
        "deleted",
        "unavailable",
        "inaccessible",
        "unknown",
    )

    assert tuple(item.value for item in SourceIdentityLifecycleState) == expected
    assert len(SourceIdentityLifecycleState.__members__) == len(expected)
    assert len(set(SourceIdentityLifecycleState)) == len(expected)
    assert [
        json.loads(json.dumps(item)) for item in SourceIdentityLifecycleState
    ] == list(expected)


@pytest.mark.parametrize(
    "value",
    ["present", "open", "closed", "merged", "draft", "active", "superseded"],
)
def test_lifecycle_state_rejects_identity_field_and_business_states(
    value: str,
) -> None:
    with pytest.raises(ValueError):
        SourceIdentityLifecycleState(value)


@pytest.mark.parametrize("identity", [_repository(), _numbered(), _child()])
def test_lifecycle_observation_accepts_each_known_identity(
    identity: SourceIdentity,
) -> None:
    observation = _lifecycle(identity)

    assert observation.schema_version == 1
    assert observation.identity == identity
    assert observation.state is SourceIdentityLifecycleState.OBSERVED_PRESENT
    assert observation.authority == _authority()
    assert observation.observed_at.tzinfo is UTC


@pytest.mark.parametrize("state", tuple(SourceIdentityLifecycleState))
def test_lifecycle_observation_supports_each_exact_state(
    state: SourceIdentityLifecycleState,
) -> None:
    identity = _numbered(kind=SourceObjectKind.PULL_REQUEST, number="4414")
    observation = _lifecycle(identity, state=state)

    assert observation.identity == identity
    assert observation.state is state


def test_deleted_lifecycle_observation_preserves_known_identity() -> None:
    identity = _numbered(kind=SourceObjectKind.PULL_REQUEST, number="4414")
    before = identity.model_dump_json()
    observation = _lifecycle(
        identity,
        state=SourceIdentityLifecycleState.DELETED,
    )

    assert observation.identity == identity
    assert observation.identity.model_dump_json() == before
    assert identity.model_dump_json() == before


def test_lifecycle_observation_requires_matching_provider_authority() -> None:
    other_provider = _provider("gitlab")
    wrong_authority = _authority(
        other_provider,
        host="gitlab.com",
    )

    with pytest.raises(ValidationError) as error:
        _lifecycle(_numbered(), authority=wrong_authority)

    assert error.value.errors()[0]["loc"] == ()


def test_lifecycle_observation_normalizes_effective_zero_offset_to_utc() -> None:
    named_zero = timezone(timedelta(0), name="provider-zero")
    supplied = datetime(2026, 7, 24, 11, 3, tzinfo=named_zero)
    observation = _lifecycle(_repository(), observed_at=supplied)

    assert observation.observed_at == supplied
    assert observation.observed_at.tzinfo is UTC


def test_lifecycle_observation_rejects_naive_time() -> None:
    with pytest.raises(ValidationError) as error:
        _lifecycle(
            _repository(),
            observed_at=datetime(2026, 7, 24, 11, 3),
        )

    assert error.value.errors()[0]["loc"] == ("observed_at",)


@pytest.mark.parametrize(
    "offset",
    [timedelta(hours=1), timedelta(hours=-5), timedelta(minutes=30)],
)
def test_lifecycle_observation_rejects_nonzero_utc_offset(
    offset: timedelta,
) -> None:
    with pytest.raises(ValidationError) as error:
        _lifecycle(
            _repository(),
            observed_at=datetime(2026, 7, 24, 11, 3, tzinfo=timezone(offset)),
        )

    assert error.value.errors()[0]["loc"] == ("observed_at",)


def test_lifecycle_observation_strictly_rejects_python_datetime_string() -> None:
    with pytest.raises(ValidationError) as error:
        _lifecycle(_repository(), observed_at="2026-07-24T11:03:00Z")

    assert error.value.errors()[0]["loc"] == ("observed_at",)


def test_lifecycle_observation_strictly_rejects_python_state_string() -> None:
    with pytest.raises(ValidationError) as error:
        SourceIdentityLifecycleObservation.model_validate(
            {
                "identity": _repository(),
                "state": "observed_present",
                "authority": _authority(),
                "observed_at": datetime(2026, 7, 24, 11, 3, tzinfo=UTC),
            }
        )

    assert error.value.errors()[0]["loc"] == ("state",)


@pytest.mark.parametrize("value", [_authority(), _alias_observation()])
def test_lifecycle_observation_rejects_non_source_identity(
    value: BaseModel,
) -> None:
    with pytest.raises(ValidationError) as error:
        SourceIdentityLifecycleObservation.model_validate(
            {
                "identity": value,
                "state": SourceIdentityLifecycleState.UNKNOWN,
                "authority": _authority(),
                "observed_at": datetime(2026, 7, 24, 11, 3, tzinfo=UTC),
            }
        )

    assert error.value.errors()[0]["loc"][0] == "identity"


def test_lifecycle_observation_requires_a_known_identity() -> None:
    base: dict[str, object] = {
        "state": SourceIdentityLifecycleState.UNKNOWN,
        "authority": _authority(),
        "observed_at": datetime(2026, 7, 24, 11, 3, tzinfo=UTC),
    }
    with pytest.raises(ValidationError) as missing_error:
        SourceIdentityLifecycleObservation.model_validate(base)
    with pytest.raises(ValidationError) as null_error:
        SourceIdentityLifecycleObservation.model_validate({**base, "identity": None})

    assert missing_error.value.errors()[0]["loc"] == ("identity",)
    assert null_error.value.errors()[0]["loc"][0] == "identity"


def test_lifecycle_observation_revalidates_constructed_nested_identity() -> None:
    invalid = RepositoryIdentity.model_construct(
        provider=ProviderKey.model_construct(root="GitHub"),
        provider_repository_id=ProviderRepositoryId.model_validate("37489525"),
    )

    with pytest.raises(ValidationError) as error:
        _lifecycle(invalid)

    assert error.value.errors()[0]["loc"][0] == "identity"


def test_lifecycle_observation_is_frozen_and_extra_forbidden() -> None:
    observation = _lifecycle(_repository())

    with pytest.raises(ValidationError) as mutation_error:
        setattr(observation, "state", SourceIdentityLifecycleState.DELETED)
    with pytest.raises(ValidationError) as extra_error:
        SourceIdentityLifecycleObservation.model_validate(
            {
                "identity": _repository(),
                "state": SourceIdentityLifecycleState.UNKNOWN,
                "authority": _authority(),
                "observed_at": datetime(2026, 7, 24, 11, 3, tzinfo=UTC),
                "provider_event_at": datetime(2026, 7, 24, 11, 2, tzinfo=UTC),
            }
        )

    assert mutation_error.value.errors()[0]["type"] == "frozen_instance"
    assert extra_error.value.errors()[0]["type"] == "extra_forbidden"


@pytest.mark.parametrize("schema_version", [0, 2, "1"])
def test_lifecycle_observation_rejects_wrong_schema_version(
    schema_version: object,
) -> None:
    with pytest.raises(ValidationError):
        SourceIdentityLifecycleObservation.model_validate(
            {
                "schema_version": schema_version,
                "identity": _repository(),
                "state": SourceIdentityLifecycleState.UNKNOWN,
                "authority": _authority(),
                "observed_at": datetime(2026, 7, 24, 11, 3, tzinfo=UTC),
            }
        )


def test_repeated_lifecycle_observations_do_not_create_a_transition() -> None:
    identity = _numbered(kind=SourceObjectKind.PULL_REQUEST, number="4414")
    first = _lifecycle(
        identity,
        state=SourceIdentityLifecycleState.OBSERVED_PRESENT,
        observed_at=datetime(2026, 7, 24, 11, 3, tzinfo=UTC),
    )
    second = _lifecycle(
        identity,
        state=SourceIdentityLifecycleState.UNKNOWN,
        observed_at=datetime(2026, 7, 25, 11, 3, tzinfo=UTC),
    )

    assert first.identity == second.identity == identity
    assert first.state is SourceIdentityLifecycleState.OBSERVED_PRESENT
    assert second.state is SourceIdentityLifecycleState.UNKNOWN
    assert "prior_state" not in SourceIdentityLifecycleObservation.model_fields
    assert "next_state" not in SourceIdentityLifecycleObservation.model_fields


def test_lifecycle_observation_fields_exclude_history_and_business_metadata() -> None:
    assert set(SourceIdentityLifecycleObservation.model_fields) == {
        "schema_version",
        "identity",
        "state",
        "authority",
        "observed_at",
    }
    forbidden = {
        "provider_event_at",
        "prior_state",
        "next_state",
        "source_index",
        "request_ordinal",
        "actor",
        "reason",
        "relationship",
        "confidence",
        "resolution",
        "open",
        "closed",
        "merged",
    }
    assert forbidden.isdisjoint(SourceIdentityLifecycleObservation.model_fields)


def test_lifecycle_observation_semantic_json_round_trip_is_deterministic() -> None:
    original = _lifecycle(
        _child(),
        state=SourceIdentityLifecycleState.INACCESSIBLE,
    )
    first_json = original.model_dump_json()
    reconstructed = SourceIdentityLifecycleObservation.model_validate_json(first_json)

    assert first_json == original.model_dump_json()
    assert reconstructed == original
    assert isinstance(reconstructed.identity, ProviderScopedSourceObjectIdentity)
    assert reconstructed.observed_at.tzinfo is UTC
    assert json.loads(first_json) == original.model_dump(mode="json")


def test_identity_state_symbols_are_internal_module_exports_only() -> None:
    new_names = {
        "IdentityFieldState",
        "IdentityValueState",
        "SourceIdentity",
        "SourceIdentityLifecycleObservation",
        "SourceIdentityLifecycleState",
    }

    assert faultatlas.__all__ == ["__version__"]
    assert new_names <= set(identity_module.__all__)
    assert new_names.isdisjoint(vars(faultatlas))
    assert new_names.isdisjoint(vars(domain_package))


def test_identity_state_module_has_no_deferred_runtime_surface() -> None:
    forbidden_names = {
        "ActorIdentity",
        "AlternateIdentifierBinding",
        "ConflictResolution",
        "EvidenceEnvelope",
        "GitObjectIdentity",
        "IdentityHistory",
        "RefObservation",
        "Relationship",
        "RevisionQualifiedLocator",
        "SourceLocator",
    }
    forbidden_methods = {
        "bind_alternate_identifiers",
        "from_source_locator",
        "load",
        "migrate",
        "resolve_conflict",
        "save",
        "to_canonical_bytes",
        "to_source_locator",
        "transition_to",
    }

    assert forbidden_names.isdisjoint(vars(identity_module))
    for model in (
        IdentityValueState[ProviderGlobalId],
        SourceIdentityLifecycleObservation,
    ):
        assert forbidden_methods.isdisjoint(vars(model))
