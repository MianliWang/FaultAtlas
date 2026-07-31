from datetime import UTC, datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

import faultatlas
import faultatlas.domain as domain_package
import faultatlas.domain.identity as identity_module
from faultatlas.domain.identity import (
    AuthorityRole,
    ProviderAuthority,
    ProviderKey,
    ProviderRepositoryId,
    RepositoryAliasObservation,
    RepositoryIdentity,
)
from faultatlas.domain.source import ArtifactSnapshot, SourceLocator

OBSERVED_AT = datetime(2026, 7, 24, 11, 3, 15, 996744, tzinfo=UTC)


def _provider(value: str = "github") -> ProviderKey:
    return ProviderKey.model_validate(value)


def _authority_data(**overrides: object) -> dict[str, object]:
    data: dict[str, object] = {
        "provider": _provider(),
        "role": AuthorityRole.RETRIEVAL,
        "host": "api.github.com",
    }
    data.update(overrides)
    return data


def _authority(**overrides: object) -> ProviderAuthority:
    return ProviderAuthority.model_validate(_authority_data(**overrides))


def _repository_data(**overrides: object) -> dict[str, object]:
    data: dict[str, object] = {
        "provider": _provider(),
        "provider_repository_id": ProviderRepositoryId.model_validate("37489525"),
    }
    data.update(overrides)
    return data


def _repository(**overrides: object) -> RepositoryIdentity:
    return RepositoryIdentity.model_validate(_repository_data(**overrides))


def _observation_data(**overrides: object) -> dict[str, object]:
    data: dict[str, object] = {
        "repository_identity": _repository(),
        "observed_alias": "pytest-dev/pytest",
        "authority": _authority(),
        "observed_at": OBSERVED_AT,
    }
    data.update(overrides)
    return data


def _observation(**overrides: object) -> RepositoryAliasObservation:
    return RepositoryAliasObservation.model_validate(_observation_data(**overrides))


@pytest.mark.parametrize(
    "value",
    ["github", "a", "g2", "git-hub", "provider-", "a" * 64],
)
def test_provider_key_accepts_canonical_values(value: str) -> None:
    assert ProviderKey.model_validate(value).root == value


@pytest.mark.parametrize(
    "value",
    [
        "",
        "GitHub",
        " github",
        "github ",
        "1github",
        "-github",
        "git_hub",
        "git/hub",
        "github.com",
        "https://github",
        "githüb",
        "github\n",
        "a" * 65,
        1,
        b"github",
    ],
)
def test_provider_key_rejects_invalid_or_coerced_values(value: object) -> None:
    with pytest.raises(ValidationError):
        ProviderKey.model_validate(value)


def test_provider_key_rejects_mapping_inputs() -> None:
    with pytest.raises(ValidationError):
        ProviderKey.model_validate({"root": "github"})
    with pytest.raises(ValidationError):
        ProviderKey.model_validate({"root": "github", "extra": "value"})


def test_provider_key_is_frozen() -> None:
    provider = _provider()

    with pytest.raises(ValidationError) as error:
        setattr(provider, "root", "gitlab")

    assert error.value.errors()[0]["type"] == "frozen_instance"


def test_provider_key_semantic_json_round_trip() -> None:
    provider = _provider()

    reconstructed = ProviderKey.model_validate_json(provider.model_dump_json())

    assert reconstructed == provider
    assert provider.model_dump(mode="json") == "github"


def test_authority_roles_are_exact_and_distinct() -> None:
    assert list(AuthorityRole) == [
        AuthorityRole.NAVIGATION,
        AuthorityRole.RETRIEVAL,
    ]
    assert AuthorityRole.NAVIGATION.value == "navigation"
    assert AuthorityRole.RETRIEVAL.value == "retrieval"
    assert AuthorityRole.NAVIGATION != AuthorityRole.RETRIEVAL


def test_provider_authority_accepts_navigation_and_retrieval_hosts() -> None:
    navigation = _authority(
        role=AuthorityRole.NAVIGATION,
        host="github.com",
    )
    retrieval = _authority(
        role=AuthorityRole.RETRIEVAL,
        host="api.github.com",
    )

    assert navigation.role is AuthorityRole.NAVIGATION
    assert navigation.host == "github.com"
    assert retrieval.role is AuthorityRole.RETRIEVAL
    assert retrieval.host == "api.github.com"


def test_provider_authority_is_provider_neutral_at_conceptual_boundary() -> None:
    authority = _authority(
        provider=_provider("gitlab"),
        role=AuthorityRole.NAVIGATION,
        host="gitlab.com",
    )

    assert authority.provider == _provider("gitlab")


def test_provider_authority_accepts_dns_length_boundaries() -> None:
    longest_host = ".".join(("a" * 63, "b" * 63, "c" * 63, "d" * 61))

    authority = _authority(host=longest_host)

    assert len(authority.host) == 253


@pytest.mark.parametrize(
    "host",
    [
        "",
        "GitHub.com",
        "https://github.com",
        "github.com/path",
        "github.com?query=yes",
        "github.com#fragment",
        "github.com:443",
        "user@github.com",
        " github.com",
        "github.com ",
        "git hub.com",
        "github.com.",
        ".github.com",
        "github..com",
        "-github.com",
        "github-.com",
        "api_git.com",
        "*.github.com",
        "githüb.com",
        "127.0.0.1",
        "[::1]",
        "a" * 64 + ".com",
        ".".join(("a" * 63, "b" * 63, "c" * 63, "d" * 62)),
    ],
)
def test_provider_authority_rejects_noncanonical_hosts(host: str) -> None:
    with pytest.raises(ValidationError) as error:
        _authority(host=host)

    assert error.value.errors()[0]["loc"] == ("host",)


def test_provider_authority_strictly_rejects_bytes_host() -> None:
    with pytest.raises(ValidationError) as error:
        _authority(host=b"api.github.com")

    assert error.value.errors()[0]["type"] == "string_type"
    assert error.value.errors()[0]["loc"] == ("host",)


@pytest.mark.parametrize(
    "role",
    ["navigation", "retrieval", "human", "Navigation", 1, True],
)
def test_provider_authority_rejects_unknown_or_coerced_roles(
    role: object,
) -> None:
    with pytest.raises(ValidationError) as error:
        _authority(role=role)

    assert error.value.errors()[0]["loc"] == ("role",)


def test_provider_authority_revalidates_constructed_provider_key() -> None:
    invalid_provider = ProviderKey.model_construct(root="GitHub")

    with pytest.raises(ValidationError) as error:
        _authority(provider=invalid_provider)

    assert error.value.errors()[0]["loc"] == ("provider",)


@pytest.mark.parametrize("schema_version", [0, 2, "1"])
def test_provider_authority_rejects_wrong_schema_version(
    schema_version: object,
) -> None:
    with pytest.raises(ValidationError):
        ProviderAuthority.model_validate(_authority_data(schema_version=schema_version))


def test_provider_authority_is_frozen_and_extra_forbidden() -> None:
    authority = _authority()

    with pytest.raises(ValidationError) as mutation_error:
        setattr(authority, "host", "github.com")
    with pytest.raises(ValidationError) as extra_error:
        ProviderAuthority.model_validate(_authority_data(api_version="2026-03-10"))

    assert mutation_error.value.errors()[0]["type"] == "frozen_instance"
    assert extra_error.value.errors()[0]["type"] == "extra_forbidden"


def test_provider_authority_semantic_json_round_trip() -> None:
    authority = _authority()

    reconstructed = ProviderAuthority.model_validate_json(authority.model_dump_json())

    assert reconstructed == authority
    assert authority.model_dump(mode="json") == {
        "schema_version": 1,
        "provider": "github",
        "role": "retrieval",
        "host": "api.github.com",
    }


@pytest.mark.parametrize(
    "value",
    ["37489525", "0001", "repo-A_01", "opaque:id/α", "x" * 255],
)
def test_provider_repository_id_accepts_and_preserves_opaque_values(
    value: str,
) -> None:
    assert ProviderRepositoryId.model_validate(value).root == value


@pytest.mark.parametrize(
    "value",
    [
        "",
        " 37489525",
        "37489525 ",
        "repo\x00id",
        "repo\nid",
        "repo\x7fid",
        "x" * 256,
        37489525,
        b"37489525",
    ],
)
def test_provider_repository_id_rejects_invalid_or_coerced_values(
    value: object,
) -> None:
    with pytest.raises(ValidationError):
        ProviderRepositoryId.model_validate(value)


def test_provider_repository_id_rejects_mapping_inputs() -> None:
    with pytest.raises(ValidationError):
        ProviderRepositoryId.model_validate({"root": "37489525"})


def test_provider_repository_id_is_frozen() -> None:
    repository_id = ProviderRepositoryId.model_validate("37489525")

    with pytest.raises(ValidationError) as error:
        setattr(repository_id, "root", "1")

    assert error.value.errors()[0]["type"] == "frozen_instance"


def test_provider_repository_id_semantic_json_round_trip() -> None:
    repository_id = ProviderRepositoryId.model_validate("37489525")

    reconstructed = ProviderRepositoryId.model_validate_json(
        repository_id.model_dump_json()
    )

    assert reconstructed == repository_id
    assert repository_id.model_dump(mode="json") == "37489525"


def test_repository_identity_accepts_canonical_github_case() -> None:
    repository = _repository()

    assert repository.provider == _provider()
    assert repository.provider_repository_id.root == "37489525"


def test_repository_identity_equality_is_provider_plus_stable_id() -> None:
    first = _repository()
    same = _repository()
    different_provider = _repository(provider=_provider("gitlab"))
    different_id = _repository(
        provider_repository_id=ProviderRepositoryId.model_validate("999")
    )

    assert first == same
    assert first != different_provider
    assert first != different_id


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("owner", "pytest-dev"),
        ("name", "pytest"),
        ("alias", "pytest-dev/pytest"),
        ("host", "github.com"),
        ("url", "https://github.com/pytest-dev/pytest"),
        ("default_branch", "main"),
        ("object_id", "4412"),
    ],
)
def test_repository_identity_rejects_nonidentity_fields(
    field: str,
    value: str,
) -> None:
    with pytest.raises(ValidationError) as error:
        RepositoryIdentity.model_validate(_repository_data(**{field: value}))

    assert error.value.errors()[0]["type"] == "extra_forbidden"


def test_repository_identity_revalidates_constructed_nested_values() -> None:
    invalid_provider = ProviderKey.model_construct(root="GitHub")
    invalid_repository_id = ProviderRepositoryId.model_construct(root=" padded")

    with pytest.raises(ValidationError) as provider_error:
        _repository(provider=invalid_provider)
    with pytest.raises(ValidationError) as id_error:
        _repository(provider_repository_id=invalid_repository_id)

    assert provider_error.value.errors()[0]["loc"] == ("provider",)
    assert id_error.value.errors()[0]["loc"] == ("provider_repository_id",)


def test_repository_identity_is_frozen_and_extra_forbidden() -> None:
    repository = _repository()

    with pytest.raises(ValidationError) as mutation_error:
        setattr(
            repository,
            "provider_repository_id",
            ProviderRepositoryId.model_validate("1"),
        )
    with pytest.raises(ValidationError) as extra_error:
        RepositoryIdentity.model_validate(
            _repository_data(repository="pytest-dev/pytest")
        )

    assert mutation_error.value.errors()[0]["type"] == "frozen_instance"
    assert extra_error.value.errors()[0]["type"] == "extra_forbidden"


@pytest.mark.parametrize("schema_version", [0, 2, "1"])
def test_repository_identity_rejects_wrong_schema_version(
    schema_version: object,
) -> None:
    with pytest.raises(ValidationError):
        RepositoryIdentity.model_validate(
            _repository_data(schema_version=schema_version)
        )


def test_repository_identity_semantic_json_round_trip() -> None:
    repository = _repository()

    reconstructed = RepositoryIdentity.model_validate_json(repository.model_dump_json())

    assert reconstructed == repository
    assert repository.model_dump(mode="json") == {
        "schema_version": 1,
        "provider": "github",
        "provider_repository_id": "37489525",
    }


def test_alias_observation_accepts_canonical_case() -> None:
    observation = _observation()

    assert observation.repository_identity == _repository()
    assert observation.observed_alias == "pytest-dev/pytest"
    assert observation.authority == _authority()
    assert observation.observed_at == OBSERVED_AT


@pytest.mark.parametrize(
    "observed_alias",
    ["PyTest-Dev/PyTest", "repository-37489525", "group project", "x" * 255],
)
def test_alias_observation_preserves_provider_neutral_alias_lexemes(
    observed_alias: str,
) -> None:
    observation = _observation(observed_alias=observed_alias)

    assert observation.observed_alias == observed_alias


@pytest.mark.parametrize(
    "observed_alias",
    [
        "",
        " pytest-dev/pytest",
        "pytest-dev/pytest ",
        "pytest-dev\npytest",
        "pytest-dev\x00pytest",
        "pytest-dev\x7fpytest",
        "x" * 256,
        37489525,
    ],
)
def test_alias_observation_rejects_invalid_alias_lexemes(
    observed_alias: object,
) -> None:
    with pytest.raises(ValidationError) as error:
        _observation(observed_alias=observed_alias)

    assert error.value.errors()[0]["loc"] == ("observed_alias",)


@pytest.mark.parametrize(
    "field",
    ["repository_identity", "observed_alias", "authority", "observed_at"],
)
def test_alias_observation_requires_every_observation_coordinate(
    field: str,
) -> None:
    data = _observation_data()
    del data[field]

    with pytest.raises(ValidationError) as error:
        RepositoryAliasObservation.model_validate(data)

    assert error.value.errors()[0]["type"] == "missing"
    assert error.value.errors()[0]["loc"] == (field,)


def test_alias_observation_rejects_naive_datetime() -> None:
    with pytest.raises(ValidationError) as error:
        _observation(observed_at=OBSERVED_AT.replace(tzinfo=None))

    assert error.value.errors()[0]["type"] == "timezone_aware"
    assert error.value.errors()[0]["loc"] == ("observed_at",)


def test_alias_observation_rejects_nonzero_utc_offset() -> None:
    nonzero = OBSERVED_AT.astimezone(timezone(timedelta(hours=-4)))

    with pytest.raises(ValidationError) as error:
        _observation(observed_at=nonzero)

    assert error.value.errors()[0]["type"] == "value_error"
    assert error.value.errors()[0]["loc"] == ("observed_at",)


def test_alias_observation_strictly_rejects_python_datetime_string() -> None:
    with pytest.raises(ValidationError) as error:
        _observation(observed_at="2026-07-24T11:03:15.996744Z")

    assert error.value.errors()[0]["type"] == "datetime_type"
    assert error.value.errors()[0]["loc"] == ("observed_at",)


def test_alias_observation_normalizes_zero_offset_and_serializes_rfc3339() -> None:
    zero_offset = timezone(timedelta(0), name="zero-offset")
    observed_at = datetime(
        2026,
        7,
        24,
        11,
        3,
        15,
        996744,
        tzinfo=zero_offset,
    )

    observation = _observation(observed_at=observed_at)

    assert observation.observed_at.tzinfo is UTC
    assert observation.observed_at.microsecond == 996744
    assert observation.model_dump(mode="json")["observed_at"] == (
        "2026-07-24T11:03:15.996744Z"
    )


def test_alias_observation_rejects_authority_provider_mismatch() -> None:
    other_authority = _authority(
        provider=_provider("gitlab"),
        host="gitlab.com",
    )

    with pytest.raises(ValidationError) as error:
        _observation(authority=other_authority)

    assert error.value.errors()[0]["type"] == "value_error"
    assert error.value.errors()[0]["loc"] == ()


@pytest.mark.parametrize(
    ("role", "host"),
    [
        (AuthorityRole.NAVIGATION, "github.com"),
        (AuthorityRole.RETRIEVAL, "api.github.com"),
    ],
)
def test_alias_observation_accepts_both_authority_roles(
    role: AuthorityRole,
    host: str,
) -> None:
    observation = _observation(authority=_authority(role=role, host=host))

    assert observation.authority.role is role


def test_multiple_aliases_can_observe_same_repository_identity() -> None:
    first = _observation(observed_alias="pytest-dev/pytest")
    renamed = _observation(observed_alias="pytest-dev/pytest-renamed")

    assert first.repository_identity == renamed.repository_identity
    assert first != renamed


def test_same_alias_does_not_equalize_different_repository_identities() -> None:
    first_repository = _repository()
    second_repository = _repository(
        provider_repository_id=ProviderRepositoryId.model_validate("999")
    )
    first = _observation(repository_identity=first_repository)
    second = _observation(repository_identity=second_repository)

    assert first.observed_alias == second.observed_alias
    assert first.repository_identity != second.repository_identity
    assert first != second


def test_alias_observation_revalidates_constructed_nested_models() -> None:
    invalid_repository = RepositoryIdentity.model_construct(
        schema_version=1,
        provider=_provider(),
        provider_repository_id=ProviderRepositoryId.model_construct(root=" padded"),
    )
    invalid_authority = ProviderAuthority.model_construct(
        schema_version=1,
        provider=_provider(),
        role=AuthorityRole.RETRIEVAL,
        host="API.GITHUB.COM",
    )

    with pytest.raises(ValidationError) as repository_error:
        _observation(repository_identity=invalid_repository)
    with pytest.raises(ValidationError) as authority_error:
        _observation(authority=invalid_authority)

    assert repository_error.value.errors()[0]["loc"] == (
        "repository_identity",
        "provider_repository_id",
    )
    assert authority_error.value.errors()[0]["loc"] == ("authority", "host")


@pytest.mark.parametrize("schema_version", [0, 2, "1"])
def test_alias_observation_rejects_wrong_schema_version(
    schema_version: object,
) -> None:
    with pytest.raises(ValidationError):
        _observation(schema_version=schema_version)


def test_alias_observation_is_frozen_and_extra_forbidden() -> None:
    observation = _observation()

    with pytest.raises(ValidationError) as mutation_error:
        setattr(observation, "observed_alias", "other/repository")
    with pytest.raises(ValidationError) as extra_error:
        RepositoryAliasObservation.model_validate(
            _observation_data(lifecycle_state="present")
        )

    assert mutation_error.value.errors()[0]["type"] == "frozen_instance"
    assert extra_error.value.errors()[0]["type"] == "extra_forbidden"


def test_alias_observation_rejects_dynamic_attribute_attachment() -> None:
    observation = _observation()

    with pytest.raises(ValidationError) as error:
        setattr(observation, "unexpected", "value")

    assert error.value.errors()[0]["type"] == "frozen_instance"


def test_alias_observation_semantic_json_round_trip_is_deterministic() -> None:
    observation = _observation()

    first_json = observation.model_dump_json()
    reconstructed = RepositoryAliasObservation.model_validate_json(first_json)

    assert first_json == observation.model_dump_json()
    assert reconstructed == observation
    assert reconstructed.repository_identity.provider_repository_id.root == ("37489525")
    assert reconstructed.observed_alias == "pytest-dev/pytest"


def test_identity_model_field_sets_are_exact() -> None:
    assert set(ProviderAuthority.model_fields) == {
        "schema_version",
        "provider",
        "role",
        "host",
    }
    assert set(RepositoryIdentity.model_fields) == {
        "schema_version",
        "provider",
        "provider_repository_id",
    }
    assert set(RepositoryAliasObservation.model_fields) == {
        "schema_version",
        "repository_identity",
        "observed_alias",
        "authority",
        "observed_at",
    }


def test_identity_types_are_not_package_or_domain_root_exports() -> None:
    expected_names = {
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
    }

    assert faultatlas.__all__ == ["__version__"]
    assert set(identity_module.__all__) == expected_names
    assert expected_names.isdisjoint(vars(faultatlas))
    assert expected_names.isdisjoint(vars(domain_package))


def test_identity_models_do_not_implicitly_convert_legacy_locator() -> None:
    locator = SourceLocator.model_validate(
        {
            "provider": "github",
            "repository": "pytest-dev/pytest",
            "object_kind": "issue",
            "object_id": "4412",
        }
    )

    with pytest.raises(ValidationError):
        RepositoryIdentity.model_validate(locator)
    with pytest.raises(ValidationError):
        SourceLocator.model_validate(_repository())


def test_legacy_model_fields_and_behavior_remain_unchanged() -> None:
    locator = SourceLocator.model_validate(
        {
            "provider": "github",
            "repository": "PyTest-Dev/PyTest",
            "object_kind": "issue",
            "object_id": "4412",
        }
    )

    assert set(SourceLocator.model_fields) == {
        "provider",
        "repository",
        "object_kind",
        "object_id",
    }
    assert set(ArtifactSnapshot.model_fields) == {
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
    }
    assert locator.repository == "pytest-dev/pytest"


def test_identity_module_has_no_later_phase_surface() -> None:
    forbidden_names = {
        "ActorIdentity",
        "CommentIdentity",
        "EvidenceEnvelope",
        "GitRevisionIdentity",
        "IssueIdentity",
        "PullRequestIdentity",
        "RefObservation",
        "RepositorySnapshot",
        "ReviewIdentity",
        "RevisionQualifiedPath",
    }
    forbidden_methods = {
        "from_source_locator",
        "load",
        "migrate",
        "save",
        "to_canonical_bytes",
        "to_source_locator",
    }

    assert forbidden_names.isdisjoint(vars(identity_module))
    for model in (
        ProviderKey,
        ProviderAuthority,
        ProviderRepositoryId,
        RepositoryIdentity,
        RepositoryAliasObservation,
    ):
        assert forbidden_methods.isdisjoint(vars(model))
