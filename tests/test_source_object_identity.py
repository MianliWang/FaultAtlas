import json

import pytest
from pydantic import ValidationError

import faultatlas
import faultatlas.domain as domain_package
import faultatlas.domain.identity as identity_module
from faultatlas.domain.identity import (
    NumberedSourceObjectIdentity,
    ProviderGlobalId,
    ProviderKey,
    ProviderNodeId,
    ProviderRepositoryId,
    ProviderScopedSourceObjectIdentity,
    RepositoryIdentity,
    RepositoryScopedNumber,
    SourceObjectKind,
)
from faultatlas.domain.source import SourceLocator

ISSUE_NODE_ID = "MDU6SXNzdWUzODE4NjY3ODc="
PULL_REQUEST_NODE_ID = "MDExOlB1bGxSZXF1ZXN0MjMxNzQ0MDY4"
ISSUE_COMMENT_NODE_ID = "MDEyOklzc3VlQ29tbWVudDQzOTcyMjcwNA=="
PULL_REQUEST_COMMENT_NODE_ID = "MDEyOklzc3VlQ29tbWVudDQzOTY0NDU3Mw=="
PULL_REQUEST_REVIEW_NODE_ID = "MDE3OlB1bGxSZXF1ZXN0UmV2aWV3MTc2MDcxNTcy"
ISSUE_TIMELINE_NODE_ID = "MDExOkNsb3NlZEV2ZW50MTk3MzAxMjMwMQ=="
PULL_REQUEST_TIMELINE_NODE_ID = "MDE5OkhlYWRSZWZEZWxldGVkRXZlbnQxOTczMDEyMzE2"


def _provider(value: str = "github") -> ProviderKey:
    return ProviderKey.model_validate(value)


def _repository(
    *,
    provider: ProviderKey | None = None,
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


def _numbered_data(**overrides: object) -> dict[str, object]:
    data: dict[str, object] = {
        "repository_identity": _repository(),
        "kind": SourceObjectKind.ISSUE,
        "repository_scoped_number": RepositoryScopedNumber.model_validate("4412"),
    }
    data.update(overrides)
    return data


def _numbered(**overrides: object) -> NumberedSourceObjectIdentity:
    return NumberedSourceObjectIdentity.model_validate(_numbered_data(**overrides))


def _pull_request() -> NumberedSourceObjectIdentity:
    return _numbered(
        kind=SourceObjectKind.PULL_REQUEST,
        repository_scoped_number=RepositoryScopedNumber.model_validate("4414"),
    )


def _child_data(**overrides: object) -> dict[str, object]:
    data: dict[str, object] = {
        "kind": SourceObjectKind.ISSUE_COMMENT,
        "provider_global_id": ProviderGlobalId.model_validate("439722704"),
        "parent": _numbered(),
    }
    data.update(overrides)
    return data


def _child(**overrides: object) -> ProviderScopedSourceObjectIdentity:
    return ProviderScopedSourceObjectIdentity.model_validate(_child_data(**overrides))


def test_source_object_kind_vocabulary_is_exact() -> None:
    assert list(SourceObjectKind) == [
        SourceObjectKind.ISSUE,
        SourceObjectKind.PULL_REQUEST,
        SourceObjectKind.ISSUE_COMMENT,
        SourceObjectKind.PULL_REQUEST_COMMENT,
        SourceObjectKind.PULL_REQUEST_REVIEW,
        SourceObjectKind.PULL_REQUEST_REVIEW_COMMENT,
        SourceObjectKind.TIMELINE_EVENT,
    ]
    assert [kind.value for kind in SourceObjectKind] == [
        "issue",
        "pull_request",
        "issue_comment",
        "pull_request_comment",
        "pull_request_review",
        "pull_request_review_comment",
        "timeline_event",
    ]


@pytest.mark.parametrize("value", ["1", "4412", "4414", "9" * 20])
def test_repository_scoped_number_accepts_canonical_decimal_lexemes(
    value: str,
) -> None:
    assert RepositoryScopedNumber.model_validate(value).root == value


@pytest.mark.parametrize(
    "value",
    [
        "",
        "0",
        "01",
        "-1",
        "+1",
        "1.0",
        "1e3",
        " 1",
        "1 ",
        "1 2",
        "１２",
        "١٢",
        "9" * 21,
        4412,
        b"4412",
        True,
    ],
)
def test_repository_scoped_number_rejects_noncanonical_or_coerced_values(
    value: object,
) -> None:
    with pytest.raises(ValidationError):
        RepositoryScopedNumber.model_validate(value)


def test_repository_scoped_number_rejects_mapping_input() -> None:
    with pytest.raises(ValidationError):
        RepositoryScopedNumber.model_validate({"root": "4412"})


def test_repository_scoped_number_is_frozen_and_round_trips_semantic_json() -> None:
    number = RepositoryScopedNumber.model_validate("4412")

    with pytest.raises(ValidationError) as error:
        setattr(number, "root", "4414")

    reconstructed = RepositoryScopedNumber.model_validate_json(number.model_dump_json())
    assert error.value.errors()[0]["type"] == "frozen_instance"
    assert reconstructed == number
    assert number.model_dump(mode="json") == "4412"


@pytest.mark.parametrize(
    "value",
    [
        "381866787",
        "231744068",
        "439722704",
        "176071572",
        "1973012316",
        "opaque:α/ID==",
        "x" * 255,
    ],
)
def test_provider_global_id_accepts_and_preserves_opaque_lexemes(
    value: str,
) -> None:
    assert ProviderGlobalId.model_validate(value).root == value


@pytest.mark.parametrize(
    "value",
    [
        "",
        " global-id",
        "global-id ",
        "global id",
        "global\tid",
        "global\nid",
        "global\x00id",
        "global\x7fid",
        "global\u00a0id",
        "x" * 256,
        381866787,
        b"381866787",
        True,
    ],
)
def test_provider_global_id_rejects_whitespace_controls_or_coercion(
    value: object,
) -> None:
    with pytest.raises(ValidationError):
        ProviderGlobalId.model_validate(value)


def test_provider_global_id_is_frozen_and_round_trips_semantic_json() -> None:
    global_id = ProviderGlobalId.model_validate("opaque:α/ID==")

    with pytest.raises(ValidationError) as error:
        setattr(global_id, "root", "other")

    reconstructed = ProviderGlobalId.model_validate_json(global_id.model_dump_json())
    assert error.value.errors()[0]["type"] == "frozen_instance"
    assert reconstructed == global_id
    assert reconstructed.root == "opaque:α/ID=="


@pytest.mark.parametrize(
    "value",
    [
        ISSUE_NODE_ID,
        PULL_REQUEST_NODE_ID,
        ISSUE_COMMENT_NODE_ID,
        PULL_REQUEST_COMMENT_NODE_ID,
        PULL_REQUEST_REVIEW_NODE_ID,
        ISSUE_TIMELINE_NODE_ID,
        PULL_REQUEST_TIMELINE_NODE_ID,
        "opaque-node:α==",
        "x" * 512,
    ],
)
def test_provider_node_id_accepts_exact_observed_and_opaque_lexemes(
    value: str,
) -> None:
    assert ProviderNodeId.model_validate(value).root == value


@pytest.mark.parametrize(
    "value",
    [
        "",
        " node-id",
        "node-id ",
        "node id",
        "node\tid",
        "node\nid",
        "node\x00id",
        "node\x7fid",
        "node\u00a0id",
        "x" * 513,
        1,
        b"node-id",
        False,
    ],
)
def test_provider_node_id_rejects_whitespace_controls_or_coercion(
    value: object,
) -> None:
    with pytest.raises(ValidationError):
        ProviderNodeId.model_validate(value)


def test_provider_node_id_is_frozen_and_round_trips_without_decoding() -> None:
    node_id = ProviderNodeId.model_validate(ISSUE_COMMENT_NODE_ID)

    with pytest.raises(ValidationError) as error:
        setattr(node_id, "root", "other")

    reconstructed = ProviderNodeId.model_validate_json(node_id.model_dump_json())
    assert error.value.errors()[0]["type"] == "frozen_instance"
    assert reconstructed == node_id
    assert reconstructed.root == ISSUE_COMMENT_NODE_ID


def test_identifier_primitives_are_distinct_runtime_concepts() -> None:
    repository_id = ProviderRepositoryId.model_validate("4412")
    scoped_number = RepositoryScopedNumber.model_validate("4412")
    global_id = ProviderGlobalId.model_validate("4412")
    node_id = ProviderNodeId.model_validate("4412")

    assert type(repository_id) is ProviderRepositoryId
    assert type(scoped_number) is RepositoryScopedNumber
    assert type(global_id) is ProviderGlobalId
    assert type(node_id) is ProviderNodeId
    assert repository_id != scoped_number
    assert scoped_number != global_id
    assert global_id != node_id
    assert ProviderRepositoryId.model_validate("0001").root == "0001"
    with pytest.raises(ValidationError):
        RepositoryScopedNumber.model_validate("0001")


def test_typed_identifier_wrappers_cannot_replace_each_other() -> None:
    with pytest.raises(ValidationError):
        ProviderGlobalId.model_validate(ProviderNodeId.model_validate(ISSUE_NODE_ID))
    with pytest.raises(ValidationError):
        ProviderNodeId.model_validate(ProviderGlobalId.model_validate("381866787"))
    with pytest.raises(ValidationError):
        RepositoryScopedNumber.model_validate(ProviderGlobalId.model_validate("4412"))


def test_numbered_issue_identity_accepts_canonical_case() -> None:
    issue = _numbered()

    assert issue.schema_version == 1
    assert issue.repository_identity == _repository()
    assert issue.kind is SourceObjectKind.ISSUE
    assert issue.repository_scoped_number.root == "4412"


def test_numbered_pull_request_identity_accepts_canonical_case() -> None:
    pull_request = _pull_request()

    assert pull_request.kind is SourceObjectKind.PULL_REQUEST
    assert pull_request.repository_scoped_number.root == "4414"


@pytest.mark.parametrize(
    "kind",
    [
        SourceObjectKind.ISSUE_COMMENT,
        SourceObjectKind.PULL_REQUEST_COMMENT,
        SourceObjectKind.PULL_REQUEST_REVIEW,
        SourceObjectKind.PULL_REQUEST_REVIEW_COMMENT,
        SourceObjectKind.TIMELINE_EVENT,
    ],
)
def test_numbered_identity_rejects_non_numbered_kinds(
    kind: SourceObjectKind,
) -> None:
    with pytest.raises(ValidationError) as error:
        _numbered(kind=kind)

    assert error.value.errors()[0]["loc"] == ()


@pytest.mark.parametrize("kind", ["issue", "pull_request"])
def test_numbered_identity_strictly_rejects_raw_python_kind_strings(
    kind: str,
) -> None:
    with pytest.raises(ValidationError) as error:
        _numbered(kind=kind)

    assert error.value.errors()[0]["loc"] == ("kind",)


def test_same_repository_number_with_different_kind_is_distinct() -> None:
    issue = _numbered()
    pull_request = _numbered(kind=SourceObjectKind.PULL_REQUEST)

    assert issue.repository_scoped_number == pull_request.repository_scoped_number
    assert issue != pull_request


def test_same_kind_and_number_in_different_repositories_is_distinct() -> None:
    first = _numbered()
    other_id = _numbered(repository_identity=_repository(repository_id="999"))
    other_provider = _numbered(
        repository_identity=_repository(provider=_provider("gitlab"))
    )

    assert first != other_id
    assert first != other_provider


def test_numbered_identity_is_alias_independent() -> None:
    first = _numbered(repository_identity=_repository())
    same_stable_repository = _numbered(repository_identity=_repository())

    assert first == same_stable_repository
    assert "alias" not in NumberedSourceObjectIdentity.model_fields
    assert "observed_alias" not in NumberedSourceObjectIdentity.model_fields


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("provider_global_id", ProviderGlobalId.model_validate("381866787")),
        ("provider_node_id", ProviderNodeId.model_validate(ISSUE_NODE_ID)),
        ("alias", "pytest-dev/pytest"),
        ("url", "https://github.com/pytest-dev/pytest/issues/4412"),
        ("source_index", 17),
        ("actor", "pytest-dev"),
        ("lifecycle_state", "present"),
        ("observed_at", "2026-07-24T11:03:15.996744Z"),
    ],
)
def test_numbered_identity_rejects_nonidentity_fields(
    field: str,
    value: object,
) -> None:
    with pytest.raises(ValidationError) as error:
        NumberedSourceObjectIdentity.model_validate(_numbered_data(**{field: value}))

    assert any(item["type"] == "extra_forbidden" for item in error.value.errors())


@pytest.mark.parametrize(
    "field",
    ["repository_identity", "kind", "repository_scoped_number"],
)
def test_numbered_identity_requires_present_coordinates(field: str) -> None:
    missing = _numbered_data()
    del missing[field]
    null = _numbered_data(**{field: None})

    with pytest.raises(ValidationError) as missing_error:
        NumberedSourceObjectIdentity.model_validate(missing)
    with pytest.raises(ValidationError) as null_error:
        NumberedSourceObjectIdentity.model_validate(null)

    assert missing_error.value.errors()[0]["loc"] == (field,)
    assert null_error.value.errors()[0]["loc"] == (field,)


def test_numbered_identity_revalidates_constructed_nested_values() -> None:
    invalid_repository = RepositoryIdentity.model_construct(
        schema_version=1,
        provider=ProviderKey.model_construct(root="GitHub"),
        provider_repository_id=ProviderRepositoryId.model_validate("37489525"),
    )
    invalid_number = RepositoryScopedNumber.model_construct(root="01")

    with pytest.raises(ValidationError) as repository_error:
        _numbered(repository_identity=invalid_repository)
    with pytest.raises(ValidationError) as number_error:
        _numbered(repository_scoped_number=invalid_number)

    assert repository_error.value.errors()[0]["loc"] == (
        "repository_identity",
        "provider",
    )
    assert number_error.value.errors()[0]["loc"] == ("repository_scoped_number",)


@pytest.mark.parametrize("schema_version", [0, 2, "1"])
def test_numbered_identity_rejects_wrong_schema_version(
    schema_version: object,
) -> None:
    with pytest.raises(ValidationError):
        _numbered(schema_version=schema_version)


def test_numbered_identity_is_frozen_extra_forbidden_and_dynamic_safe() -> None:
    issue = _numbered()

    with pytest.raises(ValidationError) as mutation_error:
        setattr(issue, "kind", SourceObjectKind.PULL_REQUEST)
    with pytest.raises(ValidationError) as dynamic_error:
        setattr(issue, "unexpected", "value")

    assert mutation_error.value.errors()[0]["type"] == "frozen_instance"
    assert dynamic_error.value.errors()[0]["type"] == "frozen_instance"


def test_numbered_identity_semantic_json_round_trip_is_deterministic() -> None:
    issue = _numbered()
    first_json = issue.model_dump_json()
    reconstructed = NumberedSourceObjectIdentity.model_validate_json(first_json)

    assert first_json == issue.model_dump_json()
    assert reconstructed == issue
    assert issue.model_dump(mode="json") == {
        "schema_version": 1,
        "repository_identity": {
            "schema_version": 1,
            "provider": "github",
            "provider_repository_id": "37489525",
        },
        "kind": "issue",
        "repository_scoped_number": "4412",
    }


@pytest.mark.parametrize(
    ("kind", "global_id", "parent"),
    [
        (SourceObjectKind.ISSUE_COMMENT, "439722704", "issue"),
        (SourceObjectKind.PULL_REQUEST_COMMENT, "439644573", "pull_request"),
        (SourceObjectKind.PULL_REQUEST_REVIEW, "176071572", "pull_request"),
        (
            SourceObjectKind.PULL_REQUEST_REVIEW_COMMENT,
            "synthetic-inline-review-comment-id",
            "pull_request",
        ),
        (SourceObjectKind.TIMELINE_EVENT, "1973012301", "issue"),
        (SourceObjectKind.TIMELINE_EVENT, "1973012316", "pull_request"),
    ],
)
def test_provider_scoped_identity_accepts_each_parent_kind_rule(
    kind: SourceObjectKind,
    global_id: str,
    parent: str,
) -> None:
    parent_identity = _numbered() if parent == "issue" else _pull_request()

    identity = _child(
        kind=kind,
        provider_global_id=ProviderGlobalId.model_validate(global_id),
        parent=parent_identity,
    )

    assert identity.kind is kind
    assert identity.provider_global_id.root == global_id
    assert identity.parent is not None
    assert identity.parent.kind is parent_identity.kind


@pytest.mark.parametrize(
    ("kind", "wrong_parent"),
    [
        (SourceObjectKind.ISSUE_COMMENT, "pull_request"),
        (SourceObjectKind.PULL_REQUEST_COMMENT, "issue"),
        (SourceObjectKind.PULL_REQUEST_REVIEW, "issue"),
        (SourceObjectKind.PULL_REQUEST_REVIEW_COMMENT, "issue"),
    ],
)
def test_provider_scoped_identity_rejects_wrong_parent_kind(
    kind: SourceObjectKind,
    wrong_parent: str,
) -> None:
    parent = _numbered() if wrong_parent == "issue" else _pull_request()

    with pytest.raises(ValidationError) as error:
        _child(kind=kind, parent=parent)

    assert error.value.errors()[0]["loc"] == ()


@pytest.mark.parametrize(
    "kind",
    [SourceObjectKind.ISSUE, SourceObjectKind.PULL_REQUEST],
)
def test_provider_scoped_identity_rejects_numbered_kinds(
    kind: SourceObjectKind,
) -> None:
    with pytest.raises(ValidationError):
        _child(kind=kind)


@pytest.mark.parametrize(
    "kind",
    [
        "issue_comment",
        "pull_request_comment",
        "pull_request_review",
        "pull_request_review_comment",
        "timeline_event",
    ],
)
def test_provider_scoped_identity_rejects_raw_python_kind_strings(
    kind: str,
) -> None:
    with pytest.raises(ValidationError) as error:
        _child(kind=kind)

    assert error.value.errors()[0]["loc"] == ("kind",)


@pytest.mark.parametrize("field", ["kind", "provider_global_id", "parent"])
def test_provider_scoped_identity_requires_present_coordinates(field: str) -> None:
    missing = _child_data()
    del missing[field]
    null = _child_data(**{field: None})

    with pytest.raises(ValidationError) as missing_error:
        ProviderScopedSourceObjectIdentity.model_validate(missing)
    with pytest.raises(ValidationError) as null_error:
        ProviderScopedSourceObjectIdentity.model_validate(null)

    assert missing_error.value.errors()[0]["loc"] == (field,)
    assert null_error.value.errors()[0]["loc"] == (field,)


def test_timeline_event_requires_numbered_parent() -> None:
    data = _child_data(
        kind=SourceObjectKind.TIMELINE_EVENT,
        provider_global_id=ProviderGlobalId.model_validate("1973012316"),
    )
    del data["parent"]

    with pytest.raises(ValidationError) as error:
        ProviderScopedSourceObjectIdentity.model_validate(data)

    assert error.value.errors()[0]["loc"] == ("parent",)
    assert error.value.errors()[0]["type"] == "missing"


def test_provider_scoped_identity_rejects_integer_global_id() -> None:
    with pytest.raises(ValidationError) as error:
        _child(provider_global_id=1973012316)

    assert error.value.errors()[0]["loc"] == ("provider_global_id",)


def test_node_id_cannot_replace_required_provider_global_id() -> None:
    with pytest.raises(ValidationError) as error:
        _child(
            kind=SourceObjectKind.TIMELINE_EVENT,
            provider_global_id=ProviderNodeId.model_validate(
                PULL_REQUEST_TIMELINE_NODE_ID
            ),
            parent=_pull_request(),
        )

    assert error.value.errors()[0]["loc"] == ("provider_global_id",)


def test_node_only_timeline_observation_cannot_fabricate_core_identity() -> None:
    data = _child_data(
        kind=SourceObjectKind.TIMELINE_EVENT,
        parent=_pull_request(),
        provider_node_id=ProviderNodeId.model_validate(
            "MDY6Q29tbWl0Mzc0ODk1MjU6NjkwYTYzYjkyMThmNzI2NjJjZDNhNjdjNmMyMDBiNzU4Yzg4Y2UxMg=="
        ),
    )
    del data["provider_global_id"]

    with pytest.raises(ValidationError) as error:
        ProviderScopedSourceObjectIdentity.model_validate(data)

    assert {item["type"] for item in error.value.errors()} == {
        "missing",
        "extra_forbidden",
    }


def test_same_global_id_under_different_parent_is_not_conflated() -> None:
    first = _child()
    other_parent = _numbered(repository_identity=_repository(repository_id="999"))
    second = _child(parent=other_parent)

    assert first.provider_global_id == second.provider_global_id
    assert first.parent != second.parent
    assert first != second


def test_same_global_id_and_parent_with_different_kind_is_not_conflated() -> None:
    parent = _pull_request()
    comment = _child(
        kind=SourceObjectKind.PULL_REQUEST_COMMENT,
        parent=parent,
    )
    review = _child(
        kind=SourceObjectKind.PULL_REQUEST_REVIEW,
        parent=parent,
    )

    assert comment.provider_global_id == review.provider_global_id
    assert comment.parent == review.parent
    assert comment != review


def test_provider_scoped_identity_preserves_opaque_global_id_lexeme() -> None:
    identity = _child(
        provider_global_id=ProviderGlobalId.model_validate("opaque:child/α==")
    )

    assert identity.provider_global_id.root == "opaque:child/α=="


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("repository_identity", _repository()),
        ("provider", _provider()),
        ("provider_node_id", ProviderNodeId.model_validate(ISSUE_COMMENT_NODE_ID)),
        ("repository_scoped_number", RepositoryScopedNumber.model_validate("4412")),
        ("source_index", 4),
        ("alias", "pytest-dev/pytest"),
        ("actor", "pytest-dev"),
        ("url", "https://github.com/pytest-dev/pytest/issues/4412"),
        ("lifecycle_state", "present"),
        ("revision", "690a63b9218f72662cd3a67c6c200b758c88ce12"),
    ],
)
def test_provider_scoped_identity_rejects_nonidentity_fields(
    field: str,
    value: object,
) -> None:
    with pytest.raises(ValidationError) as error:
        ProviderScopedSourceObjectIdentity.model_validate(_child_data(**{field: value}))

    assert any(item["type"] == "extra_forbidden" for item in error.value.errors())


def test_provider_scoped_identity_revalidates_constructed_nested_values() -> None:
    invalid_global_id = ProviderGlobalId.model_construct(root="bad id")
    invalid_parent = NumberedSourceObjectIdentity.model_construct(
        schema_version=1,
        repository_identity=_repository(),
        kind=SourceObjectKind.ISSUE,
        repository_scoped_number=RepositoryScopedNumber.model_construct(root="01"),
    )

    with pytest.raises(ValidationError) as global_error:
        _child(provider_global_id=invalid_global_id)
    with pytest.raises(ValidationError) as parent_error:
        _child(parent=invalid_parent)

    assert global_error.value.errors()[0]["loc"] == ("provider_global_id",)
    assert parent_error.value.errors()[0]["loc"] == (
        "parent",
        "repository_scoped_number",
    )


@pytest.mark.parametrize("schema_version", [0, 2, "1"])
def test_provider_scoped_identity_rejects_wrong_schema_version(
    schema_version: object,
) -> None:
    with pytest.raises(ValidationError):
        _child(schema_version=schema_version)


def test_provider_scoped_identity_is_frozen_extra_forbidden_and_dynamic_safe() -> None:
    identity = _child()

    with pytest.raises(ValidationError) as mutation_error:
        setattr(identity, "provider_global_id", ProviderGlobalId.model_validate("1"))
    with pytest.raises(ValidationError) as dynamic_error:
        setattr(identity, "unexpected", "value")

    assert mutation_error.value.errors()[0]["type"] == "frozen_instance"
    assert dynamic_error.value.errors()[0]["type"] == "frozen_instance"


def test_provider_scoped_identity_semantic_json_round_trip_is_deterministic() -> None:
    identity = _child(
        kind=SourceObjectKind.TIMELINE_EVENT,
        provider_global_id=ProviderGlobalId.model_validate("1973012316"),
        parent=_pull_request(),
    )
    first_json = identity.model_dump_json()
    reconstructed = ProviderScopedSourceObjectIdentity.model_validate_json(first_json)

    assert first_json == identity.model_dump_json()
    assert reconstructed == identity
    assert json.loads(first_json) == identity.model_dump(mode="json")
    assert identity.model_dump(mode="json") == {
        "schema_version": 1,
        "kind": "timeline_event",
        "provider_global_id": "1973012316",
        "parent": {
            "schema_version": 1,
            "repository_identity": {
                "schema_version": 1,
                "provider": "github",
                "provider_repository_id": "37489525",
            },
            "kind": "pull_request",
            "repository_scoped_number": "4414",
        },
    }


def test_core_identity_field_sets_exclude_indices_aliases_and_alternate_ids() -> None:
    assert set(NumberedSourceObjectIdentity.model_fields) == {
        "schema_version",
        "repository_identity",
        "kind",
        "repository_scoped_number",
    }
    assert set(ProviderScopedSourceObjectIdentity.model_fields) == {
        "schema_version",
        "kind",
        "provider_global_id",
        "parent",
    }
    forbidden = {
        "actor",
        "alias",
        "canonical_url",
        "chronology",
        "lifecycle_state",
        "observed_at",
        "provider_node_id",
        "relationship",
        "request_ordinal",
        "revision",
        "source_index",
    }
    assert forbidden.isdisjoint(NumberedSourceObjectIdentity.model_fields)
    assert forbidden.isdisjoint(ProviderScopedSourceObjectIdentity.model_fields)


def test_new_identity_types_are_not_package_or_domain_root_exports() -> None:
    new_names = {
        "NumberedSourceObjectIdentity",
        "ProviderGlobalId",
        "ProviderNodeId",
        "ProviderScopedSourceObjectIdentity",
        "RepositoryScopedNumber",
        "SourceObjectKind",
    }

    assert faultatlas.__all__ == ["__version__"]
    assert new_names <= set(identity_module.__all__)
    assert new_names.isdisjoint(vars(faultatlas))
    assert new_names.isdisjoint(vars(domain_package))


def test_new_identity_models_do_not_implicitly_convert_legacy_locator() -> None:
    locator = SourceLocator.model_validate(
        {
            "provider": "github",
            "repository": "pytest-dev/pytest",
            "object_kind": "issue",
            "object_id": "4412",
        }
    )

    with pytest.raises(ValidationError):
        NumberedSourceObjectIdentity.model_validate(locator)
    with pytest.raises(ValidationError):
        ProviderScopedSourceObjectIdentity.model_validate(locator)


def test_s02_module_has_no_later_phase_runtime_surface() -> None:
    forbidden_names = {
        "ActorIdentity",
        "AlternateIdentifierBinding",
        "EvidenceEnvelope",
        "FieldState",
        "GitObjectIdentity",
        "IdentityConflict",
        "IdentityLifecycle",
        "RefObservation",
        "Relationship",
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
        RepositoryScopedNumber,
        ProviderGlobalId,
        ProviderNodeId,
        NumberedSourceObjectIdentity,
        ProviderScopedSourceObjectIdentity,
    ):
        assert forbidden_methods.isdisjoint(vars(model))
