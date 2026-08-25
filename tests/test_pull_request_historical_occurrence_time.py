from __future__ import annotations

import ast
import json
from datetime import UTC, date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, cast

import pytest
from pydantic import BaseModel, ConfigDict, ValidationError
from pydantic_core import PydanticUndefined

import faultatlas.domain.history as history_module
from faultatlas.domain.history import (
    ChangedPathStatus,
    PullRequestChangedPath,
    PullRequestChangeSet,
    PullRequestHeadRefDeletion,
    PullRequestHistoricalOccurrenceTime,
    PullRequestMergeRevisionOutcome,
    PullRequestReviewRevisionApproval,
    PullRequestRevisionRoleBinding,
)
from faultatlas.domain.identity import (
    NumberedSourceObjectIdentity,
    ProviderGlobalId,
    ProviderKey,
    ProviderRepositoryId,
    ProviderScopedSourceObjectIdentity,
    RepositoryIdentity,
    RepositoryScopedNumber,
    SourceObjectKind,
)
from faultatlas.domain.revision import (
    GitCommitIdentity,
    GitHashAlgorithm,
    GitObjectKind,
    GitRefName,
    RevisionRole,
    RevisionRoleAssignment,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
HISTORY_SOURCE = REPOSITORY_ROOT / "src/faultatlas/domain/history.py"

CANONICAL_PROVIDER = "github"
CANONICAL_REPOSITORY_ID = "37489525"
CANONICAL_PULL_REQUEST_NUMBER = "4414"
CANONICAL_ISSUE_NUMBER = "4412"
CANONICAL_REVIEW_GLOBAL_ID = "176071572"
CANONICAL_HEAD_REVISION = "690a63b9218f72662cd3a67c6c200b758c88ce12"
CANONICAL_MERGE_REVISION = "10cdae8e38ec448b7133cf163dca587ad806d262"
CANONICAL_HEAD_REF_NAME = "starred_with_side_effect"

# The retained chronology supplies every occurrence instant as second-precision
# RFC 3339 with a literal Z. These three are the only retained occurrences that
# a published S03, S04, or S05 fact can carry.
CANONICAL_APPROVAL_INSTANT = "2018-11-17T23:54:20Z"
CANONICAL_MERGE_INSTANT = "2018-11-18T00:17:25Z"
CANONICAL_DELETION_INSTANT = "2018-11-18T00:17:28Z"
# The retained issue closure shares the merge instant exactly. It is a separate
# source surface with no published relation here, and the retained material
# asserts no cross-surface order between the two.
CANONICAL_TIED_ISSUE_CLOSE_INSTANT = "2018-11-18T00:17:25Z"
# The merge commit is retained one second earlier than the merge outcome.
CANONICAL_MERGE_COMMIT_INSTANT = "2018-11-18T00:17:24Z"

# The seven published S01-S05 classes, in published order. S06 is append-only,
# so this oracle locks that the module still declares exactly these, in this
# order, ahead of the single S06 addition.
#
# It deliberately carries no digest of the predecessor bodies. A digest over
# `ast.dump` output is interpreter-sensitive: Python 3.13 omits fields equal to
# their default while 3.12 emits them, so every such digest changes across a
# minor version even when no predecessor changed. `requires-python` is `>=3.13`
# while CI pins 3.13 exactly, so a freeze of that shape would be green today and
# would fail wholesale on the first interpreter bump -- a false positive whose
# obvious repair is to re-baseline the constants, which is exactly what would
# hide a genuine predecessor change. Predecessor body equality is verified at
# the publication gate against the live baseline instead.
PUBLISHED_PREDECESSOR_CLASSES = (
    "PullRequestRevisionRoleBinding",
    "ChangedPathStatus",
    "PullRequestChangedPath",
    "PullRequestChangeSet",
    "PullRequestReviewRevisionApproval",
    "PullRequestMergeRevisionOutcome",
    "PullRequestHeadRefDeletion",
)

FORBIDDEN_OCCURRENCE_IDENTIFIERS = (
    "GitRefObservation",
    "ahead",
    "authority",
    "availability",
    "behind",
    "chronology",
    "classification",
    "confidence",
    "duration",
    "elapsed",
    "evidence",
    "index",
    "interval",
    "kind",
    "monotonic",
    "observed",
    "observed_at",
    "occurrence_kind",
    "ordinal",
    "precedes",
    "recorded_at",
    "sequence",
    "skew",
    "sort",
    "state",
    "timeline",
    "timestamp",
    "unknown",
)


_UNSET: Any = object()


def _instant(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _repository() -> RepositoryIdentity:
    return RepositoryIdentity(
        provider=ProviderKey(CANONICAL_PROVIDER),
        provider_repository_id=ProviderRepositoryId(CANONICAL_REPOSITORY_ID),
    )


def _pull_request() -> NumberedSourceObjectIdentity:
    return NumberedSourceObjectIdentity(
        repository_identity=_repository(),
        kind=SourceObjectKind.PULL_REQUEST,
        repository_scoped_number=RepositoryScopedNumber(CANONICAL_PULL_REQUEST_NUMBER),
    )


def _issue() -> NumberedSourceObjectIdentity:
    return NumberedSourceObjectIdentity(
        repository_identity=_repository(),
        kind=SourceObjectKind.ISSUE,
        repository_scoped_number=RepositoryScopedNumber(CANONICAL_ISSUE_NUMBER),
    )


def _commit(full_digest: str = CANONICAL_HEAD_REVISION) -> GitCommitIdentity:
    return GitCommitIdentity(
        kind=GitObjectKind.COMMIT,
        algorithm=GitHashAlgorithm.SHA1,
        full_digest=full_digest,
    )


def _review() -> ProviderScopedSourceObjectIdentity:
    return ProviderScopedSourceObjectIdentity(
        kind=SourceObjectKind.PULL_REQUEST_REVIEW,
        provider_global_id=ProviderGlobalId(CANONICAL_REVIEW_GLOBAL_ID),
        parent=_pull_request(),
    )


def _approval() -> PullRequestReviewRevisionApproval:
    return PullRequestReviewRevisionApproval(
        review=_review(),
        approved_revision=_commit(),
    )


def _outcome() -> PullRequestMergeRevisionOutcome:
    return PullRequestMergeRevisionOutcome(
        pull_request=_pull_request(),
        merge_revision=_commit(CANONICAL_MERGE_REVISION),
    )


def _head_binding() -> PullRequestRevisionRoleBinding:
    return PullRequestRevisionRoleBinding(
        pull_request=_pull_request(),
        role_assignment=RevisionRoleAssignment(
            role=RevisionRole.HEAD,
            revision=_commit(),
        ),
    )


def _deletion() -> PullRequestHeadRefDeletion:
    return PullRequestHeadRefDeletion(
        head=_head_binding(),
        head_ref_name=GitRefName(CANONICAL_HEAD_REF_NAME),
    )


def _occurrence_time(
    *,
    occurrence: Any = _UNSET,
    occurred_at: Any = _UNSET,
) -> PullRequestHistoricalOccurrenceTime:
    return PullRequestHistoricalOccurrenceTime(
        occurrence=_approval() if occurrence is _UNSET else occurrence,
        occurred_at=(
            _instant(CANONICAL_APPROVAL_INSTANT)
            if occurred_at is _UNSET
            else occurred_at
        ),
    )


def _payload() -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(_occurrence_time().model_dump_json()))


def _occurrence_payload(payload: dict[str, Any]) -> dict[str, Any]:
    occurrence = payload["occurrence"]
    assert isinstance(occurrence, dict)
    return cast(dict[str, Any], occurrence)


def _assert_tampered_child_refused(
    occurrence: Any,
    *,
    field: str,
    message: str,
) -> None:
    """Refusal must reach the tampered field of the embedded child.

    Every union member is attempted, so two of the three errors are ordinary
    member mismatches. Exactly one must be the tampered child's own guard,
    located at that child's field. Pydantic's internal union-branch labels sit
    between those two positions and are deliberately not asserted.
    """
    with pytest.raises(ValidationError) as caught:
        _occurrence_time(occurrence=occurrence)

    errors = caught.value.errors()
    assert all(error["loc"][0] == "occurrence" for error in errors)
    reached = [
        error
        for error in errors
        if error["type"] == "value_error" and error["loc"][-1] == field
    ]
    assert len(reached) == 1, errors
    assert message in reached[0]["msg"]


def _occurrence_class() -> ast.ClassDef:
    tree = ast.parse(HISTORY_SOURCE.read_text(encoding="utf-8"))
    return next(
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef)
        and node.name == "PullRequestHistoricalOccurrenceTime"
    )


def _code_surface(node: ast.ClassDef) -> str:
    """Unparse a class with its docstring removed.

    The non-claim prose deliberately names what the contract refuses, so a
    scan over the rendered class would match its own disclaimers. Only the
    executable surface is scanned.
    """
    stripped = ast.ClassDef(
        name=node.name,
        bases=list(node.bases),
        keywords=list(node.keywords),
        body=[
            statement
            for statement in node.body
            if not (
                isinstance(statement, ast.Expr)
                and isinstance(statement.value, ast.Constant)
                and isinstance(statement.value.value, str)
            )
        ],
        decorator_list=list(node.decorator_list),
        type_params=[],
    )
    return ast.unparse(ast.fix_missing_locations(stripped))


# --- canonical witness -----------------------------------------------------


def test_the_canonical_review_approval_carries_its_retained_instant() -> None:
    occurrence_time = _occurrence_time()

    assert occurrence_time.occurrence == _approval()
    assert occurrence_time.occurred_at == _instant(CANONICAL_APPROVAL_INSTANT)
    assert occurrence_time.occurred_at.tzinfo is UTC


def test_the_canonical_merge_outcome_carries_its_retained_instant() -> None:
    occurrence_time = _occurrence_time(
        occurrence=_outcome(),
        occurred_at=_instant(CANONICAL_MERGE_INSTANT),
    )

    assert occurrence_time.occurrence == _outcome()
    assert occurrence_time.occurred_at == _instant(CANONICAL_MERGE_INSTANT)


def test_the_canonical_head_ref_deletion_carries_its_retained_instant() -> None:
    occurrence_time = _occurrence_time(
        occurrence=_deletion(),
        occurred_at=_instant(CANONICAL_DELETION_INSTANT),
    )

    assert occurrence_time.occurrence == _deletion()
    assert occurrence_time.occurred_at == _instant(CANONICAL_DELETION_INSTANT)


def test_repeating_one_occurrence_time_yields_equal_independent_values() -> None:
    first = _occurrence_time()
    second = _occurrence_time()

    assert first == second
    assert first is not second
    assert hash(first) == hash(second)


def test_the_two_supplied_values_are_preserved_unchanged() -> None:
    approval = _approval()
    instant = _instant(CANONICAL_APPROVAL_INSTANT)

    occurrence_time = _occurrence_time(occurrence=approval, occurred_at=instant)

    assert occurrence_time.occurrence == approval
    assert occurrence_time.occurred_at == instant


def test_the_retained_backbone_orders_only_by_its_own_supplied_values() -> None:
    approval = _occurrence_time(occurred_at=_instant(CANONICAL_APPROVAL_INSTANT))
    merge = _occurrence_time(
        occurrence=_outcome(), occurred_at=_instant(CANONICAL_MERGE_INSTANT)
    )
    deletion = _occurrence_time(
        occurrence=_deletion(), occurred_at=_instant(CANONICAL_DELETION_INSTANT)
    )

    # Reading the three supplied instants is the caller's arithmetic, not a
    # claim any one value makes about another.
    assert approval.occurred_at < merge.occurred_at < deletion.occurred_at


# --- the three admitted subjects -------------------------------------------


@pytest.mark.parametrize(
    "occurrence",
    (_approval(), _outcome(), _deletion()),
    ids=("approval", "merge_outcome", "head_ref_deletion"),
)
def test_every_published_occurrence_fact_is_admitted(occurrence: object) -> None:
    occurrence_time = _occurrence_time(occurrence=occurrence)

    assert occurrence_time.occurrence == occurrence
    assert type(occurrence_time.occurrence) is type(occurrence)


def test_the_admitted_subjects_are_exactly_the_three_published_facts() -> None:
    annotation = PullRequestHistoricalOccurrenceTime.model_fields[
        "occurrence"
    ].annotation

    assert annotation is not None
    assert set(getattr(annotation, "__args__", ())) == {
        PullRequestReviewRevisionApproval,
        PullRequestMergeRevisionOutcome,
        PullRequestHeadRefDeletion,
    }


@pytest.mark.parametrize(
    "occurrence",
    (
        _head_binding(),
        PullRequestChangedPath.model_construct(),
        PullRequestChangeSet.model_construct(),
    ),
    ids=("role_binding", "changed_path", "change_set"),
)
def test_a_non_occurrence_history_value_is_refused(occurrence: object) -> None:
    with pytest.raises(ValidationError, match="occurrence must be a"):
        _occurrence_time(occurrence=occurrence)


def test_a_role_binding_is_not_an_occurrence() -> None:
    # S01 binds a revision to a role; nothing about it occurred at an instant.
    with pytest.raises(ValidationError, match="occurrence must be a"):
        _occurrence_time(occurrence=_head_binding())


def test_a_change_set_is_not_an_occurrence() -> None:
    with pytest.raises(ValidationError, match="occurrence must be a"):
        _occurrence_time(occurrence=PullRequestChangeSet.model_construct())


def test_the_subject_position_is_the_only_place_the_meaning_lives() -> None:
    approval = _occurrence_time(occurrence=_approval())
    merge = _occurrence_time(occurrence=_outcome())

    assert approval != merge
    assert approval.occurred_at == merge.occurred_at
    assert type(approval.occurrence) is not type(merge.occurrence)


# --- no occurrence kind or discriminator -----------------------------------


def test_the_occurrence_time_publishes_no_kind_field() -> None:
    assert tuple(PullRequestHistoricalOccurrenceTime.model_fields) == (
        "occurrence",
        "occurred_at",
    )
    assert "occurrence_kind" not in PullRequestHistoricalOccurrenceTime.model_fields
    assert "event_type" not in PullRequestHistoricalOccurrenceTime.model_fields


def test_the_subject_union_carries_no_discriminator() -> None:
    field = PullRequestHistoricalOccurrenceTime.model_fields["occurrence"]

    assert field.discriminator is None
    assert field.metadata == []


@pytest.mark.parametrize(
    "rejected",
    ("occurrence_kind", "event_kind", "event_type", "kind", "semantic_role"),
)
def test_no_occurrence_kind_vocabulary_is_published(rejected: str) -> None:
    assert rejected not in PullRequestHistoricalOccurrenceTime.model_fields
    assert rejected not in _payload()


def test_the_json_payload_carries_no_type_tag() -> None:
    payload = _payload()

    assert set(payload) == {"occurrence", "occurred_at"}
    assert "type" not in _occurrence_payload(payload)


# --- source occurrence time, never observation time ------------------------


def test_the_instant_is_not_a_faultatlas_observation_time() -> None:
    assert "observed_at" not in PullRequestHistoricalOccurrenceTime.model_fields
    assert "observed_at" not in _payload()
    assert "observed_at" not in _code_surface(_occurrence_class())


@pytest.mark.parametrize(
    "rejected",
    (
        "observed_at",
        "acquired_at",
        "retrieved_at",
        "published_at",
        "recorded_at",
        "sealed_at",
        "assessed_at",
    ),
)
def test_no_provenance_layer_timestamp_is_expressible(rejected: str) -> None:
    assert rejected not in PullRequestHistoricalOccurrenceTime.model_fields
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        PullRequestHistoricalOccurrenceTime(
            occurrence=_approval(),
            occurred_at=_instant(CANONICAL_APPROVAL_INSTANT),
            **{rejected: _instant(CANONICAL_APPROVAL_INSTANT)},
        )


def test_the_occurrence_time_carries_no_observing_authority() -> None:
    assert "authority" not in PullRequestHistoricalOccurrenceTime.model_fields
    assert "authority" not in _payload()


def test_the_generic_ref_observation_is_not_reused() -> None:
    assert "GitRefObservation" not in _code_surface(_occurrence_class())


# --- the instant is required and carries no condition ----------------------


def test_the_instant_is_required() -> None:
    field = PullRequestHistoricalOccurrenceTime.model_fields["occurred_at"]

    assert field.is_required()
    assert field.default is PydanticUndefined
    assert field.default_factory is None


def test_the_instant_cannot_be_omitted() -> None:
    with pytest.raises(ValidationError, match="Field required"):
        PullRequestHistoricalOccurrenceTime(occurrence=_approval())  # type: ignore[call-arg]


def test_the_instant_cannot_be_none() -> None:
    with pytest.raises(ValidationError):
        _occurrence_time(occurred_at=cast(Any, None))


@pytest.mark.parametrize(
    "rejected",
    (
        "occurred_at_state",
        "timestamp_state",
        "field_state",
        "availability",
        "is_known",
        "occurrence_classification",
        "semantic_role_classification",
    ),
)
def test_no_missing_time_vocabulary_is_published(rejected: str) -> None:
    assert rejected not in PullRequestHistoricalOccurrenceTime.model_fields
    assert rejected not in _payload()


def test_an_alternate_surface_omission_is_not_expressible_here() -> None:
    # The retained pull request timeline omits its copy of the review instant.
    # That is a statement about which record supplies a fact, and this contract
    # has no place to record it.
    surface = _code_surface(_occurrence_class())

    assert "missing" not in surface
    assert "unavailable" not in surface
    assert "field_state" not in surface


# --- one point, never a sequence -------------------------------------------


def test_the_occurrence_time_publishes_no_order_field() -> None:
    for rejected in ("order", "ordinal", "index", "position", "sequence", "rank"):
        assert rejected not in PullRequestHistoricalOccurrenceTime.model_fields
        assert rejected not in _payload()


def test_two_occurrence_times_at_one_instant_are_two_supplied_facts() -> None:
    merge = _occurrence_time(
        occurrence=_outcome(), occurred_at=_instant(CANONICAL_MERGE_INSTANT)
    )
    # The retained issue closure shares the merge instant exactly; it has no
    # published relation here, so the nearest expressible equal-instant pair is
    # two occurrence times over two distinct published facts.
    same_instant_deletion = _occurrence_time(
        occurrence=_deletion(),
        occurred_at=_instant(CANONICAL_TIED_ISSUE_CLOSE_INSTANT),
    )

    assert merge.occurred_at == same_instant_deletion.occurred_at
    assert merge != same_instant_deletion
    assert type(merge.occurrence) is not type(same_instant_deletion.occurrence)


def test_equal_instants_state_nothing_about_each_other() -> None:
    first = _occurrence_time(occurred_at=_instant(CANONICAL_MERGE_INSTANT))
    second = _occurrence_time(
        occurrence=_outcome(), occurred_at=_instant(CANONICAL_MERGE_INSTANT)
    )

    assert first.occurred_at == second.occurred_at
    # No relation, precedence, or causal field exists to distinguish them.
    assert (
        set(first.model_dump())
        == set(second.model_dump())
        == {
            "occurrence",
            "occurred_at",
        }
    )


def test_the_tied_issue_closure_has_no_expressible_occurrence() -> None:
    # The retained issue closure shares the merge instant exactly, but no
    # published relation names an issue closing, so the equal-second pair the
    # retained material records is not expressible here at all.
    with pytest.raises(ValidationError, match="occurrence must be a"):
        _occurrence_time(
            occurrence=_issue(),
            occurred_at=_instant(CANONICAL_TIED_ISSUE_CLOSE_INSTANT),
        )


def test_one_fact_may_carry_two_supplied_instants() -> None:
    # Nothing here declares an occurrence unique, so two callers supplying two
    # instants for one fact yield two values rather than a contradiction.
    first = _occurrence_time(occurred_at=_instant(CANONICAL_APPROVAL_INSTANT))
    second = _occurrence_time(occurred_at=_instant(CANONICAL_MERGE_INSTANT))

    assert first.occurrence == second.occurrence
    assert first != second


def test_the_merge_commit_instant_is_not_the_merge_outcome_instant() -> None:
    # The retained merge commit precedes the retained merge outcome by one
    # second. Commit authorship time has no published relation here.
    outcome = _occurrence_time(
        occurrence=_outcome(), occurred_at=_instant(CANONICAL_MERGE_INSTANT)
    )

    assert outcome.occurred_at != _instant(CANONICAL_MERGE_COMMIT_INSTANT)
    assert "committer_time" not in _payload()
    assert "authored_at" not in PullRequestHistoricalOccurrenceTime.model_fields


def test_the_occurrence_time_is_not_a_collection() -> None:
    field = PullRequestHistoricalOccurrenceTime.model_fields["occurrence"]
    annotation = field.annotation

    assert annotation is not None
    assert not isinstance(_occurrence_time().occurrence, (list, tuple, set, frozenset))
    with pytest.raises(ValidationError):
        _occurrence_time(occurrence=cast(Any, (_approval(), _outcome())))


def test_an_absent_occurrence_time_claims_nothing() -> None:
    # Absence is expressed by supplying no value; no field records it.
    assert "occurred" not in PullRequestHistoricalOccurrenceTime.model_fields
    assert "did_occur" not in PullRequestHistoricalOccurrenceTime.model_fields
    assert set(_payload()) == {"occurrence", "occurred_at"}


# --- no chronology, duration, or clock claim -------------------------------


@pytest.mark.parametrize(
    "rejected",
    (
        "duration",
        "elapsed",
        "ended_at",
        "interval",
        "monotonic",
        "precision",
        "skew",
        "still_stands",
        "until",
    ),
)
def test_no_duration_or_clock_vocabulary_is_published(rejected: str) -> None:
    assert rejected not in PullRequestHistoricalOccurrenceTime.model_fields
    assert rejected not in _payload()


def test_the_occurrence_time_declares_no_chronology_surface() -> None:
    surface = _code_surface(_occurrence_class())

    for rejected in ("chronology", "timeline", "sequence", "ordinal", "precedes"):
        assert rejected not in surface


def test_the_occurrence_time_adds_no_classification_axis() -> None:
    surface = _code_surface(_occurrence_class())

    assert "classification" not in surface
    assert "observed" not in surface
    assert "unknown" not in surface


# --- UTC discipline --------------------------------------------------------


def test_a_zero_offset_instant_is_accepted_and_normalized() -> None:
    supplied = datetime(2018, 11, 17, 23, 54, 20, tzinfo=timezone(timedelta(0)))

    occurrence_time = _occurrence_time(occurred_at=supplied)

    assert occurrence_time.occurred_at.tzinfo is UTC
    assert occurrence_time.occurred_at == supplied


@pytest.mark.parametrize(
    "offset_hours",
    (-8, -1, 1, 2, 14),
)
def test_a_non_zero_offset_instant_is_refused(offset_hours: int) -> None:
    supplied = datetime(
        2018,
        11,
        17,
        23,
        54,
        20,
        tzinfo=timezone(timedelta(hours=offset_hours)),
    )

    with pytest.raises(ValidationError, match="occurred_at must use a zero UTC offset"):
        _occurrence_time(occurred_at=supplied)


def test_a_sub_hour_non_zero_offset_is_refused() -> None:
    supplied = datetime(
        2018, 11, 17, 23, 54, 20, tzinfo=timezone(timedelta(minutes=-30))
    )

    with pytest.raises(ValidationError, match="occurred_at must use a zero UTC offset"):
        _occurrence_time(occurred_at=supplied)


def test_a_naive_instant_is_refused() -> None:
    with pytest.raises(ValidationError, match="Input should have timezone info"):
        _occurrence_time(occurred_at=datetime(2018, 11, 17, 23, 54, 20))


def test_sub_second_precision_is_preserved() -> None:
    supplied = datetime(2018, 11, 17, 23, 54, 20, 996744, tzinfo=UTC)

    occurrence_time = _occurrence_time(occurred_at=supplied)

    assert occurrence_time.occurred_at.microsecond == 996744


def test_the_retained_instants_are_second_precision() -> None:
    for value in (
        CANONICAL_APPROVAL_INSTANT,
        CANONICAL_MERGE_INSTANT,
        CANONICAL_DELETION_INSTANT,
    ):
        assert value.endswith("Z")
        assert _instant(value).microsecond == 0


@pytest.mark.parametrize(
    "supplied",
    ("2018-11-17T23:54:20Z", "2018-11-17T23:54:20+00:00"),
)
def test_json_input_accepts_both_asserted_utc_forms(supplied: str) -> None:
    payload = _payload()
    payload["occurred_at"] = supplied

    occurrence_time = PullRequestHistoricalOccurrenceTime.model_validate_json(
        json.dumps(payload)
    )

    assert occurrence_time.occurred_at == _instant(CANONICAL_APPROVAL_INSTANT)
    assert occurrence_time.occurred_at.tzinfo is UTC


def test_json_input_refuses_a_non_zero_offset() -> None:
    payload = _payload()
    payload["occurred_at"] = "2018-11-18T00:54:20+01:00"

    with pytest.raises(ValidationError, match="occurred_at must use a zero UTC offset"):
        PullRequestHistoricalOccurrenceTime.model_validate_json(json.dumps(payload))


def test_json_input_refuses_a_naive_instant() -> None:
    payload = _payload()
    payload["occurred_at"] = "2018-11-17T23:54:20"

    with pytest.raises(ValidationError, match="Input should have timezone info"):
        PullRequestHistoricalOccurrenceTime.model_validate_json(json.dumps(payload))


@pytest.mark.parametrize(
    "supplied",
    ("", "not-a-time", "2018-11-17", "23:54:20Z", "2018-13-17T23:54:20Z", 0, [], {}),
)
def test_json_input_refuses_a_malformed_instant(supplied: object) -> None:
    payload = _payload()
    payload["occurred_at"] = supplied

    with pytest.raises(ValidationError):
        PullRequestHistoricalOccurrenceTime.model_validate_json(json.dumps(payload))


# --- semantic JSON ---------------------------------------------------------


@pytest.mark.parametrize(
    "occurrence",
    (_approval(), _outcome(), _deletion()),
    ids=("approval", "merge_outcome", "head_ref_deletion"),
)
def test_json_round_trip_preserves_the_exact_value(occurrence: object) -> None:
    original = _occurrence_time(occurrence=occurrence)

    restored = PullRequestHistoricalOccurrenceTime.model_validate_json(
        original.model_dump_json()
    )

    assert restored == original
    assert type(restored.occurrence) is type(occurrence)


def test_json_payload_carries_exactly_the_two_semantic_keys() -> None:
    payload = _payload()

    assert set(payload) == {"occurrence", "occurred_at"}
    assert "schema_version" not in payload


def test_the_embedded_occurrence_keeps_its_published_json_shape() -> None:
    payload = _payload()

    assert set(_occurrence_payload(payload)) == {"review", "approved_revision"}
    assert _occurrence_payload(payload) == json.loads(_approval().model_dump_json())


def test_json_reconstruction_accepts_a_semantic_mapping() -> None:
    restored = PullRequestHistoricalOccurrenceTime.model_validate_json(
        json.dumps(_payload())
    )

    assert restored == _occurrence_time()


@pytest.mark.parametrize(
    "occurrence",
    (_approval(), _outcome(), _deletion()),
    ids=("approval", "merge_outcome", "head_ref_deletion"),
)
def test_json_reconstruction_selects_the_supplied_member(occurrence: object) -> None:
    payload = json.loads(_occurrence_time(occurrence=occurrence).model_dump_json())

    restored = PullRequestHistoricalOccurrenceTime.model_validate_json(
        json.dumps(payload)
    )

    assert type(restored.occurrence) is type(occurrence)
    assert restored.occurrence == occurrence


def test_the_three_members_have_disjoint_json_shapes() -> None:
    shapes = [
        frozenset(json.loads(value.model_dump_json()))
        for value in (_approval(), _outcome(), _deletion())
    ]

    assert len(set(shapes)) == 3
    for left_index, left in enumerate(shapes):
        for right in shapes[left_index + 1 :]:
            assert not left & right


# --- model posture ---------------------------------------------------------


def test_occurrence_time_is_frozen() -> None:
    occurrence_time = _occurrence_time()

    with pytest.raises(ValidationError, match="Instance is frozen"):
        occurrence_time.occurred_at = _instant(CANONICAL_MERGE_INSTANT)  # type: ignore[misc]
    with pytest.raises(ValidationError, match="Instance is frozen"):
        occurrence_time.occurrence = _outcome()  # type: ignore[misc]


def test_occurrence_time_rejects_attribute_deletion() -> None:
    occurrence_time = _occurrence_time()

    with pytest.raises((ValidationError, AttributeError, TypeError)):
        del occurrence_time.occurred_at


def test_constructed_occurrence_time_is_revalidated() -> None:
    assert (
        PullRequestHistoricalOccurrenceTime.model_validate(_occurrence_time())
        == _occurrence_time()
    )


def test_occurrence_time_revalidates_a_tampered_review_approval() -> None:
    tampered = PullRequestReviewRevisionApproval.model_construct(
        review=cast(Any, "not-a-review"),
        approved_revision=_commit(),
    )

    _assert_tampered_child_refused(
        tampered,
        field="review",
        message="review must be a ProviderScopedSourceObjectIdentity",
    )


def test_occurrence_time_revalidates_a_tampered_instant() -> None:
    tampered = PullRequestHistoricalOccurrenceTime.model_construct(
        occurrence=_approval(),
        occurred_at=cast(Any, "2018-11-17T23:54:20Z"),
    )

    with pytest.raises(ValidationError):
        PullRequestHistoricalOccurrenceTime.model_validate(tampered)


def test_occurrence_time_preserves_published_subclass_acceptance() -> None:
    class NarrowedApproval(PullRequestReviewRevisionApproval):
        pass

    narrowed = NarrowedApproval(review=_review(), approved_revision=_commit())

    occurrence_time = _occurrence_time(occurrence=narrowed)

    assert occurrence_time.occurrence == _approval()


# --- required fields and closed extras -------------------------------------


@pytest.mark.parametrize("missing", ("occurrence", "occurred_at"))
def test_required_fields_cannot_be_omitted(missing: str) -> None:
    supplied: dict[str, Any] = {
        "occurrence": _approval(),
        "occurred_at": _instant(CANONICAL_APPROVAL_INSTANT),
    }
    del supplied[missing]

    with pytest.raises(ValidationError, match="Field required"):
        PullRequestHistoricalOccurrenceTime(**supplied)


@pytest.mark.parametrize(
    "extra",
    (
        "availability",
        "classification",
        "evidence",
        "event_kind",
        "chronology",
        "observed_at",
        "occurrence_kind",
        "ordinal",
        "precedes",
        "schema_version",
        "sequence",
        "source_index",
        "source_order_scope",
        "timeline",
        "timestamp_state",
    ),
)
def test_extra_fields_fail_closed(extra: str) -> None:
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        PullRequestHistoricalOccurrenceTime(
            occurrence=_approval(),
            occurred_at=_instant(CANONICAL_APPROVAL_INSTANT),
            **{extra: "supplied"},
        )


def test_occurrence_time_has_no_field_beyond_the_two_semantic_positions() -> None:
    assert len(PullRequestHistoricalOccurrenceTime.model_fields) == 2
    assert set(PullRequestHistoricalOccurrenceTime.model_fields) == {
        "occurrence",
        "occurred_at",
    }


def test_occurrence_time_carries_no_schema_version() -> None:
    assert "schema_version" not in PullRequestHistoricalOccurrenceTime.model_fields
    assert "schema_version" not in _payload()
    # The embedded predecessors keep the versions they publish.
    assert "schema_version" in _occurrence_payload(_payload())["review"]


# --- strict Python input ---------------------------------------------------


@pytest.mark.parametrize(
    "value",
    (
        None,
        0,
        "approval",
        b"approval",
        [],
        (),
        {},
        {"review": "x", "approved_revision": "y"},
        object(),
    ),
)
def test_untyped_python_occurrences_are_refused(value: object) -> None:
    with pytest.raises(ValidationError, match="occurrence must be a"):
        _occurrence_time(occurrence=value)


def test_python_construction_rejects_a_dumped_mapping() -> None:
    with pytest.raises(ValidationError, match="occurrence must be a"):
        PullRequestHistoricalOccurrenceTime(**cast(Any, _payload()))


@pytest.mark.parametrize(
    "value",
    (None, 0, 1_542_499_460, "2018-11-17T23:54:20Z", b"2018-11-17", [], {}, object()),
)
def test_untyped_python_instants_are_refused(value: object) -> None:
    with pytest.raises(ValidationError):
        _occurrence_time(occurred_at=cast(Any, value))


def test_a_date_is_not_an_instant() -> None:
    with pytest.raises(ValidationError):
        _occurrence_time(occurred_at=cast(Any, date(2018, 11, 17)))


def test_swapped_members_are_refused() -> None:
    with pytest.raises(ValidationError):
        PullRequestHistoricalOccurrenceTime(
            occurrence=cast(Any, _instant(CANONICAL_APPROVAL_INSTANT)),
            occurred_at=cast(Any, _approval()),
        )


def test_foreign_models_are_refused_in_plain_python_input() -> None:
    class ForeignOccurrence(BaseModel):
        model_config = ConfigDict(frozen=True)

        review: object
        approved_revision: object

    foreign = ForeignOccurrence(review=_review(), approved_revision=_commit())

    with pytest.raises(ValidationError, match="occurrence must be a"):
        _occurrence_time(occurrence=foreign)


def test_attribute_backed_occurrences_are_refused_under_from_attributes() -> None:
    class AttributeOccurrence:
        def __init__(self) -> None:
            self.review = _review()
            self.approved_revision = _commit()

    with pytest.raises(ValidationError, match="occurrence must be a"):
        PullRequestHistoricalOccurrenceTime.model_validate(
            {
                "occurrence": AttributeOccurrence(),
                "occurred_at": _instant(CANONICAL_APPROVAL_INSTANT),
            },
            from_attributes=True,
        )


# --- malformed child JSON --------------------------------------------------


@pytest.mark.parametrize(
    "occurrence",
    (
        None,
        0,
        "approval",
        [],
        {},
        {"review": None, "approved_revision": None},
        {"review": {}, "approved_revision": {}},
        {"unexpected": "key"},
    ),
)
def test_malformed_occurrence_json_is_refused(occurrence: object) -> None:
    payload = _payload()
    payload["occurrence"] = occurrence

    with pytest.raises(ValidationError):
        PullRequestHistoricalOccurrenceTime.model_validate_json(json.dumps(payload))


def test_an_occurrence_with_a_foreign_extra_key_is_refused() -> None:
    payload = _payload()
    occurrence = _occurrence_payload(payload)
    occurrence["occurrence_kind"] = "review_commit_approved"

    with pytest.raises(ValidationError):
        PullRequestHistoricalOccurrenceTime.model_validate_json(json.dumps(payload))


def test_a_json_payload_that_is_not_an_object_is_refused() -> None:
    for payload in ("[]", '"occurrence"', "0", "null"):
        with pytest.raises(ValidationError):
            PullRequestHistoricalOccurrenceTime.model_validate_json(payload)


def test_a_payload_mixing_two_member_shapes_is_refused() -> None:
    payload = _payload()
    merged = dict(_occurrence_payload(payload))
    merged.update(json.loads(_outcome().model_dump_json()))
    payload["occurrence"] = merged

    with pytest.raises(ValidationError):
        PullRequestHistoricalOccurrenceTime.model_validate_json(json.dumps(payload))


# --- module surface --------------------------------------------------------


def test_occurrence_time_model_surface_is_exact() -> None:
    assert history_module.__all__[7] == "PullRequestHistoricalOccurrenceTime"
    assert history_module.__all__[-1] == "PullRequestHistoricalOccurrenceTime"
    assert tuple(PullRequestHistoricalOccurrenceTime.model_fields) == (
        "occurrence",
        "occurred_at",
    )
    for field in PullRequestHistoricalOccurrenceTime.model_fields.values():
        assert field.metadata == []
        assert field.discriminator is None
        assert field.is_required()
    assert PullRequestHistoricalOccurrenceTime.model_config == {
        "frozen": True,
        "extra": "forbid",
        "strict": True,
        "revalidate_instances": "always",
        "validate_default": True,
    }
    assert PullRequestHistoricalOccurrenceTime.__module__ == "faultatlas.domain.history"


def test_the_occurrence_time_declares_the_expected_validators() -> None:
    occurrence_class = _occurrence_class()

    assert [type(node) for node in occurrence_class.body] == [
        ast.Expr,
        ast.Assign,
        ast.AnnAssign,
        ast.AnnAssign,
        ast.FunctionDef,
        ast.FunctionDef,
    ]
    assert [
        node.name for node in occurrence_class.body if isinstance(node, ast.FunctionDef)
    ] == [
        "_require_typed_python_occurrence",
        "_normalize_occurred_at",
    ]
    assert [
        (node.target.id, ast.unparse(node.annotation))
        for node in occurrence_class.body
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name)
    ] == [
        (
            "occurrence",
            "PullRequestReviewRevisionApproval | PullRequestMergeRevisionOutcome "
            "| PullRequestHeadRefDeletion",
        ),
        ("occurred_at", "AwareDatetime"),
    ]


def test_the_admitted_occurrence_tuple_is_declared_once_and_exactly() -> None:
    tree = ast.parse(HISTORY_SOURCE.read_text(encoding="utf-8"))
    declarations = [
        node
        for node in tree.body
        if isinstance(node, ast.AnnAssign)
        and isinstance(node.target, ast.Name)
        and node.target.id == "_PULL_REQUEST_HISTORICAL_OCCURRENCES"
    ]

    assert len(declarations) == 1
    declaration = declarations[0]
    assert ast.unparse(declaration.annotation) == "tuple[type[BaseModel], ...]"
    assert declaration.value is not None
    assert ast.unparse(declaration.value) == (
        "(PullRequestReviewRevisionApproval, PullRequestMergeRevisionOutcome, "
        "PullRequestHeadRefDeletion)"
    )
    assert vars(history_module)["_PULL_REQUEST_HISTORICAL_OCCURRENCES"] == (
        PullRequestReviewRevisionApproval,
        PullRequestMergeRevisionOutcome,
        PullRequestHeadRefDeletion,
    )


def test_the_occurrence_time_declares_exactly_two_comparisons() -> None:
    occurrence_class = _occurrence_class()
    comparisons = [
        node
        for statement in occurrence_class.body
        for node in ast.walk(statement)
        if isinstance(node, ast.Compare)
    ]

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
        ([ast.NotEq], ["value.utcoffset()", "timedelta(0)"]),
    ]


def test_no_forbidden_identifier_appears_in_the_occurrence_time_surface() -> None:
    surface = _code_surface(_occurrence_class())

    for identifier in FORBIDDEN_OCCURRENCE_IDENTIFIERS:
        assert identifier not in surface, identifier


def test_history_module_reads_no_clock() -> None:
    tree = ast.parse(HISTORY_SOURCE.read_text(encoding="utf-8"))
    referenced = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)} | {
        node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute)
    }

    for capability in (
        "fromtimestamp",
        "monotonic",
        "now",
        "perf_counter",
        "time",
        "today",
        "utcnow",
    ):
        assert capability not in referenced


def test_history_module_still_performs_no_io() -> None:
    tree = ast.parse(HISTORY_SOURCE.read_text(encoding="utf-8"))
    referenced = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)} | {
        node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute)
    }

    for capability in (
        "Path",
        "__import__",
        "getattr",
        "hashlib",
        "httpx",
        "importlib",
        "json",
        "open",
        "os",
        "read_bytes",
        "read_text",
        "requests",
        "setattr",
        "subprocess",
        "urlopen",
        "write_text",
    ):
        assert capability not in referenced


def test_the_history_module_imports_only_the_datetime_names_it_needs() -> None:
    tree = ast.parse(HISTORY_SOURCE.read_text(encoding="utf-8"))
    datetime_imports = [
        tuple(alias.name for alias in node.names)
        for node in tree.body
        if isinstance(node, ast.ImportFrom) and node.module == "datetime"
    ]

    assert datetime_imports == [("UTC", "datetime", "timedelta")]
    assert not [node for node in tree.body if isinstance(node, ast.Import)]


def test_history_module_depends_only_on_published_p01_and_p02() -> None:
    tree = ast.parse(HISTORY_SOURCE.read_text(encoding="utf-8"))
    faultatlas_modules = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
        and node.module is not None
        and node.module.startswith("faultatlas")
    }

    assert faultatlas_modules == {
        "faultatlas.domain.identity",
        "faultatlas.domain.revision",
    }


def test_the_occurrence_time_adds_no_evidence_or_confidence_surface() -> None:
    source = HISTORY_SOURCE.read_text(encoding="utf-8")

    assert "faultatlas.domain.evidence" not in source
    assert "DurableEvidenceRecordReference" not in source
    assert "faultatlas.domain.snapshot" not in source


@pytest.mark.parametrize(
    "literal",
    (
        CANONICAL_APPROVAL_INSTANT,
        CANONICAL_MERGE_INSTANT,
        CANONICAL_DELETION_INSTANT,
        CANONICAL_REVIEW_GLOBAL_ID,
        CANONICAL_HEAD_REVISION,
    ),
)
def test_no_canonical_case_literal_is_embedded_in_production(literal: str) -> None:
    assert literal not in HISTORY_SOURCE.read_text(encoding="utf-8")


def test_the_roadmap_records_the_s06_transition() -> None:
    roadmap = " ".join(
        (REPOSITORY_ROOT / "docs/roadmap.md").read_text(encoding="utf-8").split()
    )
    mapping = roadmap.split("## Current-code mapping", 1)
    assert len(mapping) == 2, "roadmap must retain a current-code mapping section"
    current = mapping[1]

    assert "PullRequestHistoricalOccurrenceTime" in current
    assert "`S1.P05.S08` are complete" in current
    assert "`S1.P05.S09` is next and not started" in current
    assert (
        "`S1.P05.S06` — Pull Request Historical Occurrence Time (complete)" in roadmap
    )
    assert "`S1.P05.S08` are complete" in roadmap
    assert "`S1.P05.S09` is next and not started" in roadmap
    # The superseded provisional title and status must not survive.
    assert "Bounded Development Chronology" not in roadmap
    assert "`S1.P05.S06` is next and not started" not in roadmap
    assert "`S1.P05.S05` are complete" not in roadmap


def test_canonical_occurrence_literals_remain_locked() -> None:
    assert CANONICAL_APPROVAL_INSTANT == "2018-11-17T23:54:20Z"
    assert CANONICAL_MERGE_INSTANT == "2018-11-18T00:17:25Z"
    assert CANONICAL_DELETION_INSTANT == "2018-11-18T00:17:28Z"
    assert CANONICAL_TIED_ISSUE_CLOSE_INSTANT == CANONICAL_MERGE_INSTANT
    assert CANONICAL_MERGE_COMMIT_INSTANT == "2018-11-18T00:17:24Z"


# --- closed-world occurrence refusal -----------------------------------------


def test_a_bare_commit_identity_cannot_occupy_the_occurrence_position() -> None:
    # The retained merge commit is created one second before the retained merge
    # outcome, but a commit identity is not a historical occurrence fact and no
    # published relation names commit creation.
    with pytest.raises(ValidationError, match="occurrence must be a"):
        _occurrence_time(occurrence=_commit(CANONICAL_MERGE_REVISION))


def test_a_bare_review_identity_cannot_occupy_the_occurrence_position() -> None:
    with pytest.raises(ValidationError, match="occurrence must be a"):
        _occurrence_time(occurrence=_review())


def test_the_changed_path_status_vocabulary_is_not_an_occurrence() -> None:
    with pytest.raises(ValidationError, match="occurrence must be a"):
        _occurrence_time(occurrence=ChangedPathStatus.ADDED)


def test_every_other_published_history_symbol_is_refused() -> None:
    admitted = {
        "PullRequestReviewRevisionApproval",
        "PullRequestMergeRevisionOutcome",
        "PullRequestHeadRefDeletion",
        "PullRequestHistoricalOccurrenceTime",
    }
    others = [name for name in history_module.__all__ if name not in admitted]

    assert others == [
        "PullRequestRevisionRoleBinding",
        "ChangedPathStatus",
        "PullRequestChangedPath",
        "PullRequestChangeSet",
    ]

    samples: dict[str, Any] = {
        "PullRequestRevisionRoleBinding": _head_binding(),
        "ChangedPathStatus": ChangedPathStatus.ADDED,
        "PullRequestChangedPath": PullRequestChangedPath.model_construct(),
        "PullRequestChangeSet": PullRequestChangeSet.model_construct(),
    }
    assert set(samples) == set(others)
    for name in others:
        with pytest.raises(ValidationError, match="occurrence must be a"):
            _occurrence_time(occurrence=samples[name])


# --- every admitted family revalidates its tampered child --------------------


def test_occurrence_time_revalidates_a_tampered_merge_outcome() -> None:
    tampered = PullRequestMergeRevisionOutcome.model_construct(
        pull_request=cast(Any, "not-a-pull-request"),
        merge_revision=_commit(CANONICAL_MERGE_REVISION),
    )

    _assert_tampered_child_refused(
        tampered,
        field="pull_request",
        message="pull_request must be a NumberedSourceObjectIdentity",
    )


def test_occurrence_time_revalidates_a_tampered_head_ref_deletion() -> None:
    tampered = PullRequestHeadRefDeletion.model_construct(
        head=cast(Any, "not-a-head-binding"),
        head_ref_name=GitRefName(CANONICAL_HEAD_REF_NAME),
    )

    _assert_tampered_child_refused(
        tampered,
        field="head",
        message="head must be a PullRequestRevisionRoleBinding",
    )


def test_occurrence_time_revalidates_a_tampered_grandchild() -> None:
    # Revalidation reaches through the admitted child into the published
    # predecessor it embeds.
    tampered = PullRequestHeadRefDeletion.model_construct(
        head=PullRequestRevisionRoleBinding.model_construct(
            pull_request=cast(Any, "not-an-identity"),
            role_assignment=RevisionRoleAssignment(
                role=RevisionRole.HEAD,
                revision=_commit(),
            ),
        ),
        head_ref_name=GitRefName(CANONICAL_HEAD_REF_NAME),
    )

    _assert_tampered_child_refused(
        tampered,
        field="pull_request",
        message="pull_request must be a NumberedSourceObjectIdentity",
    )


# --- both asserted-UTC JSON forms, for every admitted family -----------------


@pytest.mark.parametrize(
    ("occurrence", "instant"),
    (
        (_approval(), CANONICAL_APPROVAL_INSTANT),
        (_outcome(), CANONICAL_MERGE_INSTANT),
        (_deletion(), CANONICAL_DELETION_INSTANT),
    ),
    ids=("approval", "merge_outcome", "head_ref_deletion"),
)
@pytest.mark.parametrize("form", ("z", "offset"))
def test_every_family_accepts_both_asserted_utc_json_forms(
    occurrence: Any,
    instant: str,
    form: str,
) -> None:
    payload = json.loads(
        _occurrence_time(
            occurrence=occurrence, occurred_at=_instant(instant)
        ).model_dump_json()
    )
    payload["occurred_at"] = instant if form == "z" else f"{instant[:-1]}+00:00"

    restored = PullRequestHistoricalOccurrenceTime.model_validate_json(
        json.dumps(payload)
    )

    assert type(restored.occurrence) is type(occurrence)
    assert restored.occurrence == occurrence
    assert restored.occurred_at == _instant(instant)
    assert restored.occurred_at.tzinfo is UTC


@pytest.mark.parametrize(
    ("occurrence", "instant"),
    (
        (_approval(), CANONICAL_APPROVAL_INSTANT),
        (_outcome(), CANONICAL_MERGE_INSTANT),
        (_deletion(), CANONICAL_DELETION_INSTANT),
    ),
    ids=("approval", "merge_outcome", "head_ref_deletion"),
)
def test_every_family_refuses_a_non_zero_offset_json_instant(
    occurrence: Any,
    instant: str,
) -> None:
    payload = json.loads(
        _occurrence_time(
            occurrence=occurrence, occurred_at=_instant(instant)
        ).model_dump_json()
    )
    payload["occurred_at"] = f"{instant[:-1]}+01:00"

    with pytest.raises(ValidationError, match="occurred_at must use a zero UTC offset"):
        PullRequestHistoricalOccurrenceTime.model_validate_json(json.dumps(payload))


# --- the published class manifest is append-only -----------------------------


def test_the_history_module_declares_exactly_the_published_classes_in_order() -> None:
    tree = ast.parse(HISTORY_SOURCE.read_text(encoding="utf-8"))
    declared = [node.name for node in tree.body if isinstance(node, ast.ClassDef)]

    assert declared == [
        *PUBLISHED_PREDECESSOR_CLASSES,
        "PullRequestHistoricalOccurrenceTime",
    ]
    assert declared == history_module.__all__


def test_s06_is_the_only_class_added_after_the_published_predecessors() -> None:
    assert len(PUBLISHED_PREDECESSOR_CLASSES) == 7
    assert len(history_module.__all__) == 8
    assert history_module.__all__[-1] == "PullRequestHistoricalOccurrenceTime"
    assert list(PUBLISHED_PREDECESSOR_CLASSES) == history_module.__all__[:-1]


def test_no_pydantic_internal_union_branch_label_is_asserted() -> None:
    """Refusal shape is asserted through field names and error types only.

    The labels pydantic places in a union error path are implementation
    detail. This check scans the oracle's own docstring-stripped code surface
    with this function removed, so its own needles cannot satisfy it.
    """
    tree = ast.parse(Path(__file__).read_text(encoding="utf-8"))
    tree.body = [
        node
        for node in tree.body
        if not (
            isinstance(node, ast.FunctionDef)
            and node.name == "test_no_pydantic_internal_union_branch_label_is_asserted"
        )
    ]

    class _StripDocstrings(ast.NodeTransformer):
        def _strip(self, node: Any) -> Any:
            self.generic_visit(node)
            first = node.body[0] if node.body else None
            if (
                isinstance(first, ast.Expr)
                and isinstance(first.value, ast.Constant)
                and isinstance(first.value.value, str)
            ):
                node.body = node.body[1:] or [ast.Pass()]
            return node

        visit_Module = _strip
        visit_ClassDef = _strip
        visit_FunctionDef = _strip

    surface = ast.unparse(ast.fix_missing_locations(_StripDocstrings().visit(tree)))

    for label in ("function-after[", "function-before[", "tagged-union", "union_tag"):
        assert label not in surface, label
