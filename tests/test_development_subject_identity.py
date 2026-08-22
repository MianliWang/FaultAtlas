from __future__ import annotations

import ast
import json
from enum import StrEnum
from pathlib import Path

import pytest
from pydantic import BaseModel, ConfigDict, ValidationError

import faultatlas.domain.history as history_module
from faultatlas.domain.history import (
    DevelopmentSubjectIdentity,
    DevelopmentSubjectKind,
)
from faultatlas.domain.identity import (
    ProviderGlobalId,
    ProviderKey,
    ProviderRepositoryId,
    RepositoryIdentity,
    RepositoryScopedNumber,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
HISTORY_SOURCE = REPOSITORY_ROOT / "src/faultatlas/domain/history.py"
IDENTITY_SOURCE = REPOSITORY_ROOT / "src/faultatlas/domain/identity.py"

CANONICAL_PROVIDER = "github"
CANONICAL_REPOSITORY_ID = "37489525"
CANONICAL_ISSUE_NUMBER = "4412"
CANONICAL_ISSUE_GLOBAL_ID = "381866787"
CANONICAL_PULL_REQUEST_NUMBER = "4414"
CANONICAL_PULL_REQUEST_GLOBAL_ID = "231744068"

SYNTHETIC_REPOSITORY_ID = "12345678"

FORBIDDEN_HISTORY_IDENTIFIERS = (
    "ancestry",
    "author",
    "base_branch",
    "before_snapshot",
    "body",
    "branch",
    "CaseHistory",
    "change_set",
    "chronology",
    "ci_run",
    "closed_at",
    "comments",
    "commit",
    "confidence",
    "created_at",
    "default_branch",
    "descendant",
    "DevelopmentHistory",
    "DevelopmentHistoryIdentity",
    "discussion",
    "DurableEvidenceRecordReference",
    "evidence",
    "HistorySubject",
    "labels",
    "merged_at",
    "node_id",
    "occurred_at",
    "parent",
    "persistence",
    "release",
    "review",
    "revision",
    "SnapshotTransition",
    "snapshot",
    "state",
    "status",
    "test_run",
    "timestamp",
    "title",
    "updated_at",
    "url",
    "visibility",
)


def _repository(repository_id: str = CANONICAL_REPOSITORY_ID) -> RepositoryIdentity:
    return RepositoryIdentity(
        provider=ProviderKey(CANONICAL_PROVIDER),
        provider_repository_id=ProviderRepositoryId(repository_id),
    )


def _subject(
    *,
    repository: RepositoryIdentity | None = None,
    kind: DevelopmentSubjectKind = DevelopmentSubjectKind.ISSUE,
    number: str = CANONICAL_ISSUE_NUMBER,
    provider_global_id: str = CANONICAL_ISSUE_GLOBAL_ID,
) -> DevelopmentSubjectIdentity:
    return DevelopmentSubjectIdentity(
        repository=_repository() if repository is None else repository,
        kind=kind,
        number=RepositoryScopedNumber(number),
        provider_global_id=ProviderGlobalId(provider_global_id),
    )


def _canonical_issue() -> DevelopmentSubjectIdentity:
    return _subject()


def _canonical_pull_request() -> DevelopmentSubjectIdentity:
    return _subject(
        kind=DevelopmentSubjectKind.PULL_REQUEST,
        number=CANONICAL_PULL_REQUEST_NUMBER,
        provider_global_id=CANONICAL_PULL_REQUEST_GLOBAL_ID,
    )


def _issue_payload() -> dict[str, object]:
    return {
        "repository": {
            "schema_version": 1,
            "provider": CANONICAL_PROVIDER,
            "provider_repository_id": CANONICAL_REPOSITORY_ID,
        },
        "kind": "issue",
        "number": CANONICAL_ISSUE_NUMBER,
        "provider_global_id": CANONICAL_ISSUE_GLOBAL_ID,
    }


# --- canonical witnesses ---------------------------------------------------


def test_canonical_issue_4412_is_identified() -> None:
    issue = _canonical_issue()

    assert issue.repository == _repository()
    assert issue.kind is DevelopmentSubjectKind.ISSUE
    assert issue.number == RepositoryScopedNumber(CANONICAL_ISSUE_NUMBER)
    assert issue.provider_global_id == ProviderGlobalId(CANONICAL_ISSUE_GLOBAL_ID)
    assert issue.repository.provider_repository_id == ProviderRepositoryId(
        CANONICAL_REPOSITORY_ID
    )


def test_canonical_pull_request_4414_is_identified() -> None:
    pull_request = _canonical_pull_request()

    assert pull_request.repository == _repository()
    assert pull_request.kind is DevelopmentSubjectKind.PULL_REQUEST
    assert pull_request.number == RepositoryScopedNumber(CANONICAL_PULL_REQUEST_NUMBER)
    assert pull_request.provider_global_id == ProviderGlobalId(
        CANONICAL_PULL_REQUEST_GLOBAL_ID
    )


def test_the_canonical_witnesses_share_one_repository() -> None:
    assert _canonical_issue().repository == _canonical_pull_request().repository


def test_repeating_one_subject_yields_equal_independent_values() -> None:
    first = _canonical_issue()
    second = _canonical_issue()

    assert first == second
    assert first is not second


# --- identity distinctions -------------------------------------------------


def test_the_canonical_issue_and_pull_request_are_distinct_subjects() -> None:
    assert _canonical_issue() != _canonical_pull_request()


def test_kind_alone_distinguishes_two_subjects() -> None:
    as_issue = _subject(kind=DevelopmentSubjectKind.ISSUE)
    as_pull_request = _subject(kind=DevelopmentSubjectKind.PULL_REQUEST)

    assert as_issue.number == as_pull_request.number
    assert as_issue.repository == as_pull_request.repository
    assert as_issue.provider_global_id == as_pull_request.provider_global_id
    assert as_issue != as_pull_request


def test_the_same_number_in_another_repository_is_another_subject() -> None:
    canonical = _canonical_issue()
    elsewhere = _subject(repository=_repository(SYNTHETIC_REPOSITORY_ID))

    assert canonical.number == elsewhere.number
    assert canonical.kind is elsewhere.kind
    assert canonical.provider_global_id == elsewhere.provider_global_id
    assert canonical != elsewhere
    assert canonical.repository != elsewhere.repository


def test_a_different_provider_global_id_yields_a_distinct_subject() -> None:
    canonical = _canonical_issue()
    relabelled = _subject(provider_global_id="999999999")

    assert canonical.repository == relabelled.repository
    assert canonical.kind is relabelled.kind
    assert canonical.number == relabelled.number
    assert canonical != relabelled


def test_a_different_number_yields_a_distinct_subject() -> None:
    assert _canonical_issue() != _subject(number="4413")


def test_repository_and_kind_both_remain_part_of_the_subject() -> None:
    fields = set(DevelopmentSubjectIdentity.model_fields)

    assert "repository" in fields
    assert "kind" in fields


def test_the_four_supplied_values_are_preserved_unchanged() -> None:
    repository = _repository()
    number = RepositoryScopedNumber(CANONICAL_PULL_REQUEST_NUMBER)
    provider_global_id = ProviderGlobalId(CANONICAL_PULL_REQUEST_GLOBAL_ID)

    subject = DevelopmentSubjectIdentity(
        repository=repository,
        kind=DevelopmentSubjectKind.PULL_REQUEST,
        number=number,
        provider_global_id=provider_global_id,
    )

    assert subject.repository == repository
    assert subject.number == number
    assert subject.provider_global_id == provider_global_id


def test_a_number_and_global_id_pair_is_never_treated_as_a_provider_match() -> None:
    crossed = _subject(
        kind=DevelopmentSubjectKind.ISSUE,
        number=CANONICAL_PULL_REQUEST_NUMBER,
        provider_global_id=CANONICAL_ISSUE_GLOBAL_ID,
    )

    assert crossed.number == RepositoryScopedNumber(CANONICAL_PULL_REQUEST_NUMBER)
    assert crossed.provider_global_id == ProviderGlobalId(CANONICAL_ISSUE_GLOBAL_ID)
    assert crossed != _canonical_issue()
    assert crossed != _canonical_pull_request()


# --- subject kind ----------------------------------------------------------


def test_subject_kind_is_closed_to_exactly_issue_and_pull_request() -> None:
    assert [member.name for member in DevelopmentSubjectKind] == [
        "ISSUE",
        "PULL_REQUEST",
    ]
    assert [member.value for member in DevelopmentSubjectKind] == [
        "issue",
        "pull_request",
    ]
    assert len(DevelopmentSubjectKind) == 2
    assert issubclass(DevelopmentSubjectKind, StrEnum)


@pytest.mark.parametrize("member", tuple(DevelopmentSubjectKind))
def test_both_subject_kinds_are_accepted(member: DevelopmentSubjectKind) -> None:
    subject = _subject(kind=member)

    assert subject.kind is member
    assert json.loads(subject.model_dump_json())["kind"] == member.value


@pytest.mark.parametrize(
    "excluded",
    (
        "branch",
        "ci_run",
        "comment",
        "commit",
        "deployment",
        "discussion",
        "issue_comment",
        "pull_request_comment",
        "pull_request_review",
        "release",
        "review",
        "test_run",
        "timeline_event",
    ),
)
def test_non_subject_kinds_are_not_published(excluded: str) -> None:
    assert excluded not in {member.value for member in DevelopmentSubjectKind}


@pytest.mark.parametrize("unknown", ("review", "commit", "Issue", "ISSUE", "", "1"))
def test_unknown_subject_kinds_fail_closed_in_json(unknown: str) -> None:
    payload = _issue_payload()
    payload["kind"] = unknown

    with pytest.raises(ValidationError):
        DevelopmentSubjectIdentity.model_validate_json(json.dumps(payload))


@pytest.mark.parametrize("unknown", ("issue", "pull_request", "review", 1, None))
def test_unknown_and_raw_subject_kinds_fail_closed_in_python(
    unknown: object,
) -> None:
    with pytest.raises(ValidationError):
        DevelopmentSubjectIdentity(
            repository=_repository(),
            kind=unknown,  # type: ignore[arg-type]
            number=RepositoryScopedNumber(CANONICAL_ISSUE_NUMBER),
            provider_global_id=ProviderGlobalId(CANONICAL_ISSUE_GLOBAL_ID),
        )


# --- semantic JSON ---------------------------------------------------------


def test_issue_semantic_json_round_trip_preserves_the_exact_value() -> None:
    issue = _canonical_issue()

    restored = DevelopmentSubjectIdentity.model_validate_json(issue.model_dump_json())

    assert restored == issue
    assert restored.model_dump_json() == issue.model_dump_json()


def test_pull_request_semantic_json_round_trip_preserves_the_exact_value() -> None:
    pull_request = _canonical_pull_request()

    restored = DevelopmentSubjectIdentity.model_validate_json(
        pull_request.model_dump_json()
    )

    assert restored == pull_request
    assert restored.model_dump_json() == pull_request.model_dump_json()


def test_subject_json_payload_carries_exactly_the_four_semantic_keys() -> None:
    payload = json.loads(_canonical_issue().model_dump_json())

    assert set(payload) == {
        "repository",
        "kind",
        "number",
        "provider_global_id",
    }
    assert payload == _issue_payload()
    assert payload["kind"] == "issue"
    assert payload["number"] == CANONICAL_ISSUE_NUMBER
    assert payload["provider_global_id"] == CANONICAL_ISSUE_GLOBAL_ID


def test_subject_json_reconstruction_accepts_a_semantic_mapping() -> None:
    restored = DevelopmentSubjectIdentity.model_validate_json(
        json.dumps(_issue_payload())
    )

    assert restored == _canonical_issue()


# --- model posture ---------------------------------------------------------


def test_subject_is_frozen() -> None:
    subject = _canonical_issue()

    for field, value in (
        ("repository", _repository(SYNTHETIC_REPOSITORY_ID)),
        ("kind", DevelopmentSubjectKind.PULL_REQUEST),
        ("number", RepositoryScopedNumber(CANONICAL_PULL_REQUEST_NUMBER)),
        ("provider_global_id", ProviderGlobalId(CANONICAL_PULL_REQUEST_GLOBAL_ID)),
    ):
        with pytest.raises(ValidationError):
            setattr(subject, field, value)

    assert subject == _canonical_issue()


def test_subject_rejects_attribute_deletion() -> None:
    subject = _canonical_issue()

    with pytest.raises(ValidationError):
        del subject.kind

    assert subject == _canonical_issue()


def test_constructed_subject_is_revalidated() -> None:
    revalidated = DevelopmentSubjectIdentity.model_validate(_canonical_issue())

    assert revalidated == _canonical_issue()


def test_subject_revalidates_a_nested_repository_identity() -> None:
    tampered = RepositoryIdentity.model_construct(
        schema_version=1,
        provider=ProviderKey(CANONICAL_PROVIDER),
        provider_repository_id=" padded ",
    )

    with pytest.raises(ValidationError) as error:
        DevelopmentSubjectIdentity(
            repository=tampered,
            kind=DevelopmentSubjectKind.ISSUE,
            number=RepositoryScopedNumber(CANONICAL_ISSUE_NUMBER),
            provider_global_id=ProviderGlobalId(CANONICAL_ISSUE_GLOBAL_ID),
        )

    assert error.value.errors()[0]["loc"] == (
        "repository",
        "provider_repository_id",
    )


def test_subject_revalidates_a_nested_repository_scoped_number() -> None:
    with pytest.raises(ValidationError) as error:
        DevelopmentSubjectIdentity(
            repository=_repository(),
            kind=DevelopmentSubjectKind.ISSUE,
            number=RepositoryScopedNumber.model_construct(root="04412"),
            provider_global_id=ProviderGlobalId(CANONICAL_ISSUE_GLOBAL_ID),
        )

    assert error.value.errors()[0]["loc"] == ("number",)


def test_subject_revalidates_a_nested_provider_global_id() -> None:
    with pytest.raises(ValidationError) as error:
        DevelopmentSubjectIdentity(
            repository=_repository(),
            kind=DevelopmentSubjectKind.ISSUE,
            number=RepositoryScopedNumber(CANONICAL_ISSUE_NUMBER),
            provider_global_id=ProviderGlobalId.model_construct(root="has space"),
        )

    assert error.value.errors()[0]["loc"] == ("provider_global_id",)


def test_subject_preserves_published_subclass_acceptance() -> None:
    class _SubclassedRepository(RepositoryIdentity):
        pass

    class _SubclassedNumber(RepositoryScopedNumber):
        pass

    class _SubclassedGlobalId(ProviderGlobalId):
        pass

    subject = DevelopmentSubjectIdentity(
        repository=_SubclassedRepository(
            provider=ProviderKey(CANONICAL_PROVIDER),
            provider_repository_id=ProviderRepositoryId(CANONICAL_REPOSITORY_ID),
        ),
        kind=DevelopmentSubjectKind.ISSUE,
        number=_SubclassedNumber(CANONICAL_ISSUE_NUMBER),
        provider_global_id=_SubclassedGlobalId(CANONICAL_ISSUE_GLOBAL_ID),
    )

    assert subject == _canonical_issue()
    assert type(subject.repository) is RepositoryIdentity
    assert type(subject.number) is RepositoryScopedNumber
    assert type(subject.provider_global_id) is ProviderGlobalId


def test_subject_preserves_published_repository_identity_input_semantics() -> None:
    permissive = RepositoryIdentity(
        provider=ProviderKey(CANONICAL_PROVIDER),
        provider_repository_id=CANONICAL_REPOSITORY_ID,  # type: ignore[arg-type]
    )

    assert _subject(repository=permissive) == _canonical_issue()


# --- required fields and closed extras -------------------------------------


@pytest.mark.parametrize(
    "missing",
    ("repository", "kind", "number", "provider_global_id"),
)
def test_subject_required_fields_cannot_be_omitted(missing: str) -> None:
    payload = _issue_payload()
    del payload[missing]

    with pytest.raises(ValidationError) as error:
        DevelopmentSubjectIdentity.model_validate_json(json.dumps(payload))

    assert error.value.errors()[0]["type"] == "missing"
    assert error.value.errors()[0]["loc"] == (missing,)


@pytest.mark.parametrize(
    "extra",
    (
        "author",
        "body",
        "closed_at",
        "comments",
        "created_at",
        "evidence",
        "merged_at",
        "node_id",
        "schema_version",
        "snapshot",
        "state",
        "title",
        "updated_at",
        "url",
    ),
)
def test_subject_extra_fields_fail_closed(extra: str) -> None:
    payload = _issue_payload()
    payload[extra] = "unexpected"

    with pytest.raises(ValidationError) as error:
        DevelopmentSubjectIdentity.model_validate_json(json.dumps(payload))

    assert error.value.errors()[0]["type"] == "extra_forbidden"


def test_subject_has_no_field_beyond_the_four_semantic_positions() -> None:
    assert tuple(DevelopmentSubjectIdentity.model_fields) == (
        "repository",
        "kind",
        "number",
        "provider_global_id",
    )


# --- strict Python input ---------------------------------------------------


@pytest.mark.parametrize(
    "value",
    (
        {
            "schema_version": 1,
            "provider": CANONICAL_PROVIDER,
            "provider_repository_id": CANONICAL_REPOSITORY_ID,
        },
        CANONICAL_REPOSITORY_ID,
        37489525,
        None,
        ProviderGlobalId(CANONICAL_ISSUE_GLOBAL_ID),
    ),
)
def test_subject_rejects_untyped_python_repositories(value: object) -> None:
    with pytest.raises(ValidationError, match="in Python input"):
        DevelopmentSubjectIdentity(
            repository=value,  # type: ignore[arg-type]
            kind=DevelopmentSubjectKind.ISSUE,
            number=RepositoryScopedNumber(CANONICAL_ISSUE_NUMBER),
            provider_global_id=ProviderGlobalId(CANONICAL_ISSUE_GLOBAL_ID),
        )


@pytest.mark.parametrize(
    "value",
    (
        CANONICAL_ISSUE_NUMBER,
        4412,
        None,
        {"root": CANONICAL_ISSUE_NUMBER},
        ProviderGlobalId(CANONICAL_ISSUE_NUMBER),
    ),
)
def test_subject_rejects_untyped_python_numbers(value: object) -> None:
    with pytest.raises(ValidationError, match="in Python input"):
        DevelopmentSubjectIdentity(
            repository=_repository(),
            kind=DevelopmentSubjectKind.ISSUE,
            number=value,  # type: ignore[arg-type]
            provider_global_id=ProviderGlobalId(CANONICAL_ISSUE_GLOBAL_ID),
        )


@pytest.mark.parametrize(
    "value",
    (
        CANONICAL_ISSUE_GLOBAL_ID,
        381866787,
        None,
        {"root": CANONICAL_ISSUE_GLOBAL_ID},
        RepositoryScopedNumber(CANONICAL_ISSUE_GLOBAL_ID),
    ),
)
def test_subject_rejects_untyped_python_provider_global_ids(value: object) -> None:
    with pytest.raises(ValidationError, match="in Python input"):
        DevelopmentSubjectIdentity(
            repository=_repository(),
            kind=DevelopmentSubjectKind.ISSUE,
            number=RepositoryScopedNumber(CANONICAL_ISSUE_NUMBER),
            provider_global_id=value,  # type: ignore[arg-type]
        )


def test_subject_python_construction_rejects_a_dumped_mapping() -> None:
    with pytest.raises(ValidationError, match="in Python input"):
        DevelopmentSubjectIdentity.model_validate(_issue_payload())


def test_subject_rejects_swapped_scalar_members() -> None:
    with pytest.raises(ValidationError, match="in Python input"):
        DevelopmentSubjectIdentity(
            repository=_repository(),
            kind=DevelopmentSubjectKind.ISSUE,
            number=ProviderGlobalId(CANONICAL_ISSUE_NUMBER),  # type: ignore[arg-type]
            provider_global_id=RepositoryScopedNumber(  # type: ignore[arg-type]
                CANONICAL_ISSUE_GLOBAL_ID
            ),
        )


class _AttributeBackedRepository:
    def __init__(self, repository: RepositoryIdentity) -> None:
        self.schema_version = repository.schema_version
        self.provider = repository.provider
        self.provider_repository_id = repository.provider_repository_id


class _ForeignRepository(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    schema_version: object
    provider: object
    provider_repository_id: object


class _ForeignScalar(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    root: object


def test_subject_rejects_attribute_backed_children_under_from_attributes() -> None:
    with pytest.raises(ValidationError, match="in Python input"):
        DevelopmentSubjectIdentity.model_validate(
            {
                "repository": _AttributeBackedRepository(_repository()),
                "kind": DevelopmentSubjectKind.ISSUE,
                "number": RepositoryScopedNumber(CANONICAL_ISSUE_NUMBER),
                "provider_global_id": ProviderGlobalId(CANONICAL_ISSUE_GLOBAL_ID),
            },
            from_attributes=True,
        )


def test_subject_rejects_foreign_model_children_under_from_attributes() -> None:
    repository = _repository()

    with pytest.raises(ValidationError, match="in Python input"):
        DevelopmentSubjectIdentity.model_validate(
            {
                "repository": _ForeignRepository(
                    schema_version=repository.schema_version,
                    provider=repository.provider,
                    provider_repository_id=repository.provider_repository_id,
                ),
                "kind": DevelopmentSubjectKind.ISSUE,
                "number": RepositoryScopedNumber(CANONICAL_ISSUE_NUMBER),
                "provider_global_id": ProviderGlobalId(CANONICAL_ISSUE_GLOBAL_ID),
            },
            from_attributes=True,
        )
    with pytest.raises(ValidationError, match="in Python input"):
        DevelopmentSubjectIdentity.model_validate(
            {
                "repository": repository,
                "kind": DevelopmentSubjectKind.ISSUE,
                "number": _ForeignScalar(root=CANONICAL_ISSUE_NUMBER),
                "provider_global_id": ProviderGlobalId(CANONICAL_ISSUE_GLOBAL_ID),
            },
            from_attributes=True,
        )
    with pytest.raises(ValidationError, match="in Python input"):
        DevelopmentSubjectIdentity.model_validate(
            {
                "repository": repository,
                "kind": DevelopmentSubjectKind.ISSUE,
                "number": RepositoryScopedNumber(CANONICAL_ISSUE_NUMBER),
                "provider_global_id": _ForeignScalar(root=CANONICAL_ISSUE_GLOBAL_ID),
            },
            from_attributes=True,
        )


# --- malformed child JSON --------------------------------------------------


@pytest.mark.parametrize(
    "repository",
    (
        {},
        {"provider": CANONICAL_PROVIDER},
        {"provider_repository_id": CANONICAL_REPOSITORY_ID},
        {
            "schema_version": 2,
            "provider": CANONICAL_PROVIDER,
            "provider_repository_id": CANONICAL_REPOSITORY_ID,
        },
        {
            "provider": "GitHub",
            "provider_repository_id": CANONICAL_REPOSITORY_ID,
        },
        {"provider": CANONICAL_PROVIDER, "provider_repository_id": ""},
        {
            "provider": CANONICAL_PROVIDER,
            "provider_repository_id": " 37489525 ",
        },
        {
            "provider": CANONICAL_PROVIDER,
            "provider_repository_id": CANONICAL_REPOSITORY_ID,
            "unexpected": 1,
        },
        CANONICAL_REPOSITORY_ID,
        None,
        [],
    ),
)
def test_subject_rejects_malformed_repository_identity_json(
    repository: object,
) -> None:
    payload = _issue_payload()
    payload["repository"] = repository

    with pytest.raises(ValidationError):
        DevelopmentSubjectIdentity.model_validate_json(json.dumps(payload))


@pytest.mark.parametrize(
    "number",
    (
        "",
        "0",
        "04412",
        "-4412",
        "4412 ",
        " 4412",
        "4,412",
        "4412.0",
        "٤٤١٢",
        "1" * 21,
        4412,
        None,
        [],
    ),
)
def test_subject_rejects_malformed_repository_scoped_number_json(
    number: object,
) -> None:
    payload = _issue_payload()
    payload["number"] = number

    with pytest.raises(ValidationError):
        DevelopmentSubjectIdentity.model_validate_json(json.dumps(payload))


@pytest.mark.parametrize(
    "provider_global_id",
    (
        "",
        "381866787 ",
        " 381866787",
        "381 866 787",
        "381866787\n",
        "x" * 256,
        381866787,
        None,
        {},
    ),
)
def test_subject_rejects_malformed_provider_global_id_json(
    provider_global_id: object,
) -> None:
    payload = _issue_payload()
    payload["provider_global_id"] = provider_global_id

    with pytest.raises(ValidationError):
        DevelopmentSubjectIdentity.model_validate_json(json.dumps(payload))


def test_subject_rejects_a_json_payload_that_is_not_an_object() -> None:
    for payload in ("[]", '"issue"', "1", "null"):
        with pytest.raises(ValidationError):
            DevelopmentSubjectIdentity.model_validate_json(payload)


# --- non-claim boundary ----------------------------------------------------


@pytest.mark.parametrize(
    "absent",
    (
        "author",
        "base_branch",
        "body",
        "branch",
        "change_set",
        "chronology",
        "closed_at",
        "comments",
        "confidence",
        "created_at",
        "default_branch",
        "evidence",
        "evidence_record",
        "labels",
        "merged_at",
        "node_id",
        "occurred_at",
        "parent",
        "ref",
        "review",
        "revision",
        "snapshot",
        "state",
        "status",
        "title",
        "updated_at",
        "url",
        "visibility",
    ),
)
def test_subject_has_no_history_state_or_temporal_field(absent: str) -> None:
    assert absent not in DevelopmentSubjectIdentity.model_fields


def test_subject_makes_no_existence_or_history_claim() -> None:
    absent_from_provider = _subject(
        number="99999999",
        provider_global_id="999999999999",
    )

    assert absent_from_provider.number == RepositoryScopedNumber("99999999")
    assert absent_from_provider.provider_global_id == ProviderGlobalId("999999999999")
    assert set(json.loads(absent_from_provider.model_dump_json())) == {
        "repository",
        "kind",
        "number",
        "provider_global_id",
    }


def test_the_issue_and_pull_request_carry_no_relation_to_each_other() -> None:
    issue = _canonical_issue()
    pull_request = _canonical_pull_request()

    for subject in (issue, pull_request):
        assert not hasattr(subject, "fixes")
        assert not hasattr(subject, "resolves")
        assert not hasattr(subject, "related_subject")
        assert not hasattr(subject, "linked_subject")


@pytest.mark.parametrize(
    "aggregate",
    (
        "CaseHistory",
        "DevelopmentHistory",
        "DevelopmentHistoryIdentity",
        "HistorySubject",
        "RepositorySnapshotTransition",
        "SnapshotTransition",
    ),
)
def test_no_history_aggregate_or_transition_is_published(aggregate: str) -> None:
    assert not hasattr(history_module, aggregate)
    assert aggregate not in history_module.__all__


def test_no_forbidden_identifier_appears_in_the_history_module_surface() -> None:
    tree = ast.parse(HISTORY_SOURCE.read_text(encoding="utf-8"))
    body = [node for node in tree.body if not isinstance(node, ast.Expr)]
    surface = "\n".join(ast.unparse(node) for node in body)

    for identifier in FORBIDDEN_HISTORY_IDENTIFIERS:
        assert identifier not in surface


# --- module surface --------------------------------------------------------


def test_model_and_module_surfaces_are_exact_and_local() -> None:
    assert history_module.__all__ == [
        "DevelopmentSubjectKind",
        "DevelopmentSubjectIdentity",
    ]
    assert sorted(
        name for name in vars(history_module) if not name.startswith("_")
    ) == [
        "BaseModel",
        "ConfigDict",
        "DevelopmentSubjectIdentity",
        "DevelopmentSubjectKind",
        "ProviderGlobalId",
        "RepositoryIdentity",
        "RepositoryScopedNumber",
        "StrEnum",
        "ValidationInfo",
        "field_validator",
    ]
    assert DevelopmentSubjectIdentity.__module__ == "faultatlas.domain.history"
    assert DevelopmentSubjectKind.__module__ == "faultatlas.domain.history"

    assert tuple(DevelopmentSubjectIdentity.model_fields) == (
        "repository",
        "kind",
        "number",
        "provider_global_id",
    )
    annotations = {
        name: field.annotation
        for name, field in DevelopmentSubjectIdentity.model_fields.items()
    }
    assert annotations == {
        "repository": RepositoryIdentity,
        "kind": DevelopmentSubjectKind,
        "number": RepositoryScopedNumber,
        "provider_global_id": ProviderGlobalId,
    }
    for field in DevelopmentSubjectIdentity.model_fields.values():
        assert field.metadata == []
        assert field.discriminator is None
        assert field.is_required()

    assert DevelopmentSubjectIdentity.model_config == {
        "frozen": True,
        "extra": "forbid",
        "strict": True,
        "revalidate_instances": "always",
        "validate_default": True,
    }


def test_history_module_has_only_the_bounded_surface_and_no_io_calls() -> None:
    tree = ast.parse(HISTORY_SOURCE.read_text(encoding="utf-8"))

    assert [type(node) for node in tree.body] == [
        ast.Expr,
        ast.ImportFrom,
        ast.ImportFrom,
        ast.ImportFrom,
        ast.Assign,
        ast.ClassDef,
        ast.ClassDef,
    ]
    assert not [node for node in tree.body if isinstance(node, ast.Import)]
    assert [
        (node.module, tuple(alias.name for alias in node.names))
        for node in tree.body
        if isinstance(node, ast.ImportFrom)
    ] == [
        ("enum", ("StrEnum",)),
        (
            "pydantic",
            ("BaseModel", "ConfigDict", "ValidationInfo", "field_validator"),
        ),
        (
            "faultatlas.domain.identity",
            (
                "ProviderGlobalId",
                "RepositoryIdentity",
                "RepositoryScopedNumber",
            ),
        ),
    ]
    assert not [
        alias
        for node in tree.body
        if isinstance(node, ast.ImportFrom)
        for alias in node.names
        if alias.asname is not None
    ]
    assert not [
        node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.TypeAlias))
    ]
    assert [
        target.id
        for node in tree.body
        if isinstance(node, ast.Assign)
        for target in node.targets
        if isinstance(target, ast.Name)
    ] == ["__all__"]

    classes = [node for node in tree.body if isinstance(node, ast.ClassDef)]
    assert [node.name for node in classes] == [
        "DevelopmentSubjectKind",
        "DevelopmentSubjectIdentity",
    ]
    assert [[ast.unparse(base) for base in node.bases] for node in classes] == [
        ["StrEnum"],
        ["BaseModel"],
    ]
    assert not [node for node in classes if node.keywords or node.decorator_list]

    kind, identity = classes
    assert [type(node) for node in kind.body] == [ast.Expr, ast.Assign, ast.Assign]
    assert [
        (target.id, ast.literal_eval(node.value))
        for node in kind.body
        if isinstance(node, ast.Assign)
        for target in node.targets
        if isinstance(target, ast.Name)
    ] == [("ISSUE", "issue"), ("PULL_REQUEST", "pull_request")]

    assert [type(node) for node in identity.body] == [
        ast.Expr,
        ast.Assign,
        ast.AnnAssign,
        ast.AnnAssign,
        ast.AnnAssign,
        ast.AnnAssign,
        ast.FunctionDef,
        ast.FunctionDef,
        ast.FunctionDef,
    ]
    assert [
        target.id
        for node in identity.body
        if isinstance(node, ast.Assign)
        for target in node.targets
        if isinstance(target, ast.Name)
    ] == ["model_config"]
    assert [
        (node.target.id, ast.unparse(node.annotation))
        for node in identity.body
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name)
    ] == [
        ("repository", "RepositoryIdentity"),
        ("kind", "DevelopmentSubjectKind"),
        ("number", "RepositoryScopedNumber"),
        ("provider_global_id", "ProviderGlobalId"),
    ]
    assert not [
        node
        for node in identity.body
        if isinstance(node, ast.AnnAssign) and node.value is not None
    ]
    assert [
        node.name
        for node in identity.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    ] == [
        "_require_typed_python_repository",
        "_require_typed_python_number",
        "_require_typed_python_provider_global_id",
    ]

    comparisons = [node for node in ast.walk(tree) if isinstance(node, ast.Compare)]
    assert [
        (
            [type(operator) for operator in comparison.ops],
            [
                ast.unparse(comparison.left),
                *(ast.unparse(other) for other in comparison.comparators),
            ],
        )
        for comparison in comparisons
    ] == [
        ([ast.Eq], ["info.mode", "'python'"]),
        ([ast.Eq], ["info.mode", "'python'"]),
        ([ast.Eq], ["info.mode", "'python'"]),
    ]
    assert {
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    } == {"ConfigDict", "ValueError", "field_validator", "isinstance"}
    assert not [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    ]
    assert {
        node.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load)
    } == {
        "BaseModel",
        "ConfigDict",
        "DevelopmentSubjectKind",
        "ProviderGlobalId",
        "RepositoryIdentity",
        "RepositoryScopedNumber",
        "StrEnum",
        "ValidationInfo",
        "ValueError",
        "classmethod",
        "field_validator",
        "info",
        "isinstance",
        "object",
        "value",
    }
    assert [
        (node.value.id, node.attr)
        for node in ast.walk(tree)
        if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name)
    ] == [("info", "mode"), ("info", "mode"), ("info", "mode")]


def test_history_module_declares_no_reflection_or_capability_surface() -> None:
    tree = ast.parse(HISTORY_SOURCE.read_text(encoding="utf-8"))
    referenced = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)} | {
        node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute)
    }

    for capability in (
        "Path",
        "__import__",
        "datetime",
        "getattr",
        "hashlib",
        "httpx",
        "importlib",
        "json",
        "loads",
        "open",
        "os",
        "read_bytes",
        "read_text",
        "requests",
        "setattr",
        "subprocess",
        "urlopen",
        "write_bytes",
        "write_text",
    ):
        assert capability not in referenced


def test_history_module_depends_only_on_published_p01_identity() -> None:
    tree = ast.parse(HISTORY_SOURCE.read_text(encoding="utf-8"))
    faultatlas_modules = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
        and node.module is not None
        and node.module.startswith("faultatlas")
    }

    assert faultatlas_modules == {"faultatlas.domain.identity"}

    identity_text = IDENTITY_SOURCE.read_text(encoding="utf-8")
    assert "history" not in identity_text
    assert "DevelopmentSubject" not in identity_text


def test_history_module_reads_no_reference_corpus() -> None:
    source = HISTORY_SOURCE.read_text(encoding="utf-8")

    assert "reference_corpus" not in source
    assert "docs/reference_cases" not in source


@pytest.mark.parametrize(
    "literal",
    (
        CANONICAL_REPOSITORY_ID,
        CANONICAL_ISSUE_NUMBER,
        CANONICAL_ISSUE_GLOBAL_ID,
        CANONICAL_PULL_REQUEST_NUMBER,
        CANONICAL_PULL_REQUEST_GLOBAL_ID,
    ),
)
def test_no_canonical_case_literal_is_embedded_in_production(literal: str) -> None:
    assert literal not in HISTORY_SOURCE.read_text(encoding="utf-8")


def test_canonical_case_literals_remain_locked() -> None:
    assert CANONICAL_PROVIDER == "github"
    assert CANONICAL_REPOSITORY_ID == "37489525"
    assert CANONICAL_ISSUE_NUMBER == "4412"
    assert CANONICAL_ISSUE_GLOBAL_ID == "381866787"
    assert CANONICAL_PULL_REQUEST_NUMBER == "4414"
    assert CANONICAL_PULL_REQUEST_GLOBAL_ID == "231744068"
