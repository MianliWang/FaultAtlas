from __future__ import annotations

import ast
import json
from enum import StrEnum
from pathlib import Path
from typing import Any, cast

import pytest
from pydantic import BaseModel, ConfigDict, ValidationError

import faultatlas.domain.history as history_module
from faultatlas.domain.history import (
    ChangedPathStatus,
    PullRequestChangedPath,
    PullRequestChangeSet,
    PullRequestRevisionRoleBinding,
)
from faultatlas.domain.identity import (
    NumberedSourceObjectIdentity,
    ProviderKey,
    ProviderRepositoryId,
    RepositoryIdentity,
    RepositoryScopedNumber,
    SourceObjectKind,
)
from faultatlas.domain.revision import (
    GitBlobIdentity,
    GitCommitIdentity,
    GitHashAlgorithm,
    GitObjectKind,
    GitRepositoryPath,
    GitTreeIdentity,
    RevisionRole,
    RevisionRoleAssignment,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
HISTORY_SOURCE = REPOSITORY_ROOT / "src/faultatlas/domain/history.py"

CANONICAL_PROVIDER = "github"
CANONICAL_REPOSITORY_ID = "37489525"
CANONICAL_PULL_REQUEST_NUMBER = "4414"
CANONICAL_BASE_REVISION = "4c9cde74ab40027b5761ab9e002af116a4a20df3"
CANONICAL_HEAD_REVISION = "690a63b9218f72662cd3a67c6c200b758c88ce12"
CANONICAL_HEAD_TREE = "9e5593159e909083009ac9ad72d5d59feb863c44"

# Exactly the three changed paths the retained comparison supplies, in the
# retained source order, with the head-side blob identity and status of each.
CANONICAL_CHANGED_PATHS = (
    ("changelog/4412.bugfix.rst", "7a28b610837873eeff2a16582de6d5a035820552", "added"),
    (
        "src/_pytest/assertion/rewrite.py",
        "7b9aa5006544c160f584f1e8fc3f7771ef6e5e99",
        "modified",
    ),
    (
        "testing/test_assertrewrite.py",
        "a02433cd62ab19ebb54b42b50c299e59e48de00e",
        "modified",
    ),
)
# Resolved at the head revision but not reported as changed by the comparison.
CANONICAL_UNCHANGED_PATH = ("LICENSE", "629df45ac405532c107eb233217bc2ac1ad70c88")

SYNTHETIC_BLOB = "1a2b3c4d5e6f11111111111111111111111111ff"

FORBIDDEN_CHANGE_SET_IDENTIFIERS = (
    "ahead_by",
    "ancestor",
    "ancestry",
    "base_object",
    "behind_by",
    "comparison",
    "complete",
    "contents",
    "copied",
    "deleted",
    "descendant",
    "diff",
    "evidence",
    "hunk",
    "merge_base",
    "patch",
    "reachab",
    "removed",
    "renamed",
    "snapshot",
    "total_commits",
)


def _pull_request(
    number: str = CANONICAL_PULL_REQUEST_NUMBER,
) -> NumberedSourceObjectIdentity:
    return NumberedSourceObjectIdentity(
        repository_identity=RepositoryIdentity(
            provider=ProviderKey(CANONICAL_PROVIDER),
            provider_repository_id=ProviderRepositoryId(CANONICAL_REPOSITORY_ID),
        ),
        kind=SourceObjectKind.PULL_REQUEST,
        repository_scoped_number=RepositoryScopedNumber(number),
    )


def _commit(full_digest: str) -> GitCommitIdentity:
    return GitCommitIdentity(
        kind=GitObjectKind.COMMIT,
        algorithm=GitHashAlgorithm.SHA1,
        full_digest=full_digest,
    )


def _blob(full_digest: str) -> GitBlobIdentity:
    return GitBlobIdentity(
        kind=GitObjectKind.BLOB,
        algorithm=GitHashAlgorithm.SHA1,
        full_digest=full_digest,
    )


def _binding(
    role: RevisionRole,
    full_digest: str,
    *,
    number: str = CANONICAL_PULL_REQUEST_NUMBER,
) -> PullRequestRevisionRoleBinding:
    return PullRequestRevisionRoleBinding(
        pull_request=_pull_request(number),
        role_assignment=RevisionRoleAssignment(
            role=role, revision=_commit(full_digest)
        ),
    )


def _base(
    number: str = CANONICAL_PULL_REQUEST_NUMBER,
) -> PullRequestRevisionRoleBinding:
    return _binding(RevisionRole.BASE, CANONICAL_BASE_REVISION, number=number)


def _head(
    number: str = CANONICAL_PULL_REQUEST_NUMBER,
) -> PullRequestRevisionRoleBinding:
    return _binding(RevisionRole.HEAD, CANONICAL_HEAD_REVISION, number=number)


def _changed_path(
    path: str,
    blob: str,
    status: str = "modified",
) -> PullRequestChangedPath:
    return PullRequestChangedPath(
        path=GitRepositoryPath(path),
        head_object=_blob(blob),
        status=ChangedPathStatus(status),
    )


def _canonical_changed_paths() -> tuple[PullRequestChangedPath, ...]:
    return tuple(_changed_path(*entry) for entry in CANONICAL_CHANGED_PATHS)


def _one_changed_path() -> tuple[PullRequestChangedPath, ...]:
    """Smallest valid collection, for cases that do not depend on contents."""
    return (_changed_path(*CANONICAL_CHANGED_PATHS[0]),)


def _change_set(
    *,
    base: PullRequestRevisionRoleBinding | None = None,
    head: PullRequestRevisionRoleBinding | None = None,
    changed_paths: tuple[PullRequestChangedPath, ...] | None = None,
) -> PullRequestChangeSet:
    return PullRequestChangeSet(
        base=_base() if base is None else base,
        head=_head() if head is None else head,
        changed_paths=(
            _canonical_changed_paths() if changed_paths is None else changed_paths
        ),
    )


def _payload() -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(_change_set().model_dump_json()))


def _entries(payload: dict[str, Any]) -> list[dict[str, Any]]:
    entries = payload["changed_paths"]
    assert isinstance(entries, list)
    return cast(list[dict[str, Any]], entries)


# --- canonical witnesses ---------------------------------------------------


def test_the_canonical_three_path_change_set_is_supplied() -> None:
    change_set = _change_set()

    assert change_set.base == _base()
    assert change_set.head == _head()
    assert len(change_set.changed_paths) == 3
    assert [entry.path.root for entry in change_set.changed_paths] == [
        path for path, _, _ in CANONICAL_CHANGED_PATHS
    ]
    assert [entry.head_object.full_digest for entry in change_set.changed_paths] == [
        blob for _, blob, _ in CANONICAL_CHANGED_PATHS
    ]
    assert [entry.status.value for entry in change_set.changed_paths] == [
        status for _, _, status in CANONICAL_CHANGED_PATHS
    ]


def test_the_change_set_carries_the_canonical_base_and_head_revisions() -> None:
    change_set = _change_set()

    assert change_set.base.role_assignment.revision.full_digest == (
        CANONICAL_BASE_REVISION
    )
    assert change_set.head.role_assignment.revision.full_digest == (
        CANONICAL_HEAD_REVISION
    )
    assert change_set.base.pull_request == change_set.head.pull_request


def test_the_canonical_added_path_is_the_only_added_entry() -> None:
    statuses = [entry.status for entry in _change_set().changed_paths]

    assert statuses.count(ChangedPathStatus.ADDED) == 1
    assert statuses.count(ChangedPathStatus.MODIFIED) == 2
    assert _change_set().changed_paths[0].status is ChangedPathStatus.ADDED


def test_repeating_one_change_set_yields_equal_independent_values() -> None:
    first = _change_set()
    second = _change_set()

    assert first == second
    assert first is not second


def test_the_supplied_order_is_preserved_exactly_and_is_not_sorted() -> None:
    reversed_paths = tuple(reversed(_canonical_changed_paths()))

    change_set = _change_set(changed_paths=reversed_paths)

    assert change_set.changed_paths == reversed_paths
    assert change_set != _change_set()
    assert [entry.path.root for entry in change_set.changed_paths] != sorted(
        entry.path.root for entry in change_set.changed_paths
    )


def test_an_empty_change_set_is_rejected() -> None:
    with pytest.raises(ValidationError) as error:
        _change_set(changed_paths=())

    assert error.value.errors()[0]["type"] == "too_short"


def test_an_empty_changed_path_array_is_rejected_in_json() -> None:
    payload = _payload()
    payload["changed_paths"] = []

    with pytest.raises(ValidationError):
        PullRequestChangeSet.model_validate_json(json.dumps(payload))


def test_one_changed_path_is_enough() -> None:
    change_set = _change_set(changed_paths=_one_changed_path())

    assert len(change_set.changed_paths) == 1
    assert change_set != _change_set()


def test_a_path_resolved_at_head_need_not_be_a_changed_path() -> None:
    path, blob = CANONICAL_UNCHANGED_PATH
    supplied = {entry.path.root for entry in _change_set().changed_paths}

    assert path not in supplied
    # Supplying it is a different supplied value, not a correction of the first.
    widened = _change_set(
        changed_paths=(*_canonical_changed_paths(), _changed_path(path, blob))
    )
    assert len(widened.changed_paths) == 4
    assert widened != _change_set()


# --- one pull request, two roles -------------------------------------------


def test_base_and_head_must_bind_the_same_pull_request() -> None:
    with pytest.raises(ValidationError, match="same pull request"):
        _change_set(head=_head(number="1"))


def test_the_base_position_must_carry_the_base_role() -> None:
    with pytest.raises(ValidationError, match="base must carry the base revision role"):
        _change_set(base=_head())


def test_the_head_position_must_carry_the_head_role() -> None:
    with pytest.raises(ValidationError, match="head must carry the head revision role"):
        _change_set(head=_base())


def test_swapping_the_two_bindings_is_rejected() -> None:
    with pytest.raises(ValidationError, match="base must carry the base revision role"):
        _change_set(base=_head(), head=_base())


def test_the_change_set_reuses_the_published_s01_binding_unchanged() -> None:
    change_set = _change_set()

    assert type(change_set.base) is PullRequestRevisionRoleBinding
    assert type(change_set.head) is PullRequestRevisionRoleBinding
    assert json.loads(change_set.model_dump_json())["base"] == json.loads(
        _base().model_dump_json()
    )


# --- changed-path status vocabulary ----------------------------------------


def test_changed_path_status_is_closed_to_added_and_modified() -> None:
    assert [member.name for member in ChangedPathStatus] == ["ADDED", "MODIFIED"]
    assert [member.value for member in ChangedPathStatus] == ["added", "modified"]
    assert len(ChangedPathStatus) == 2
    assert issubclass(ChangedPathStatus, StrEnum)


@pytest.mark.parametrize("member", tuple(ChangedPathStatus))
def test_both_statuses_are_accepted(member: ChangedPathStatus) -> None:
    entry = _changed_path("a", SYNTHETIC_BLOB, member.value)

    assert entry.status is member
    assert json.loads(entry.model_dump_json())["status"] == member.value


@pytest.mark.parametrize(
    "absent",
    ("removed", "deleted", "renamed", "copied", "changed", "unchanged", "unknown"),
)
def test_unwitnessed_statuses_are_absent_rather_than_reserved(absent: str) -> None:
    assert absent not in {member.value for member in ChangedPathStatus}

    payload = _payload()
    first = _entries(payload)[0]
    first["status"] = absent

    with pytest.raises(ValidationError):
        PullRequestChangeSet.model_validate_json(json.dumps(payload))


@pytest.mark.parametrize("raw", ("added", "modified", 1, None))
def test_raw_python_statuses_fail_closed(raw: object) -> None:
    with pytest.raises(ValidationError):
        PullRequestChangedPath(
            path=GitRepositoryPath("a"),
            head_object=_blob(SYNTHETIC_BLOB),
            status=raw,  # type: ignore[arg-type]
        )


# --- head-side object only -------------------------------------------------


def test_a_changed_path_carries_only_a_head_side_object() -> None:
    assert tuple(PullRequestChangedPath.model_fields) == (
        "path",
        "head_object",
        "status",
    )
    for absent in ("base_object", "before", "after", "previous_object", "old_object"):
        assert absent not in PullRequestChangedPath.model_fields


def test_only_a_blob_identity_may_be_supplied_as_the_head_object() -> None:
    with pytest.raises(ValidationError, match="in Python input"):
        PullRequestChangedPath(
            path=GitRepositoryPath("a"),
            head_object=_commit(CANONICAL_HEAD_REVISION),  # type: ignore[arg-type]
            status=ChangedPathStatus.MODIFIED,
        )
    with pytest.raises(ValidationError, match="in Python input"):
        PullRequestChangedPath(
            path=GitRepositoryPath("a"),
            head_object=GitTreeIdentity(  # type: ignore[arg-type]
                kind=GitObjectKind.TREE,
                algorithm=GitHashAlgorithm.SHA1,
                full_digest=CANONICAL_HEAD_TREE,
            ),
            status=ChangedPathStatus.MODIFIED,
        )


def test_a_changed_path_carries_no_content_diff_or_hunk() -> None:
    for absent in (
        "bytes",
        "content",
        "contents",
        "diff",
        "hunk",
        "line_span",
        "patch",
        "text",
    ):
        assert absent not in PullRequestChangedPath.model_fields


# --- one Git object format --------------------------------------------------


def _sha256_commit(full_digest: str = "a" * 64) -> GitCommitIdentity:
    return GitCommitIdentity(
        kind=GitObjectKind.COMMIT,
        algorithm=GitHashAlgorithm.SHA256,
        full_digest=full_digest,
    )


def _sha256_blob(full_digest: str = "b" * 64) -> GitBlobIdentity:
    return GitBlobIdentity(
        kind=GitObjectKind.BLOB,
        algorithm=GitHashAlgorithm.SHA256,
        full_digest=full_digest,
    )


def _sha256_binding(role: RevisionRole) -> PullRequestRevisionRoleBinding:
    return PullRequestRevisionRoleBinding(
        pull_request=_pull_request(),
        role_assignment=RevisionRoleAssignment(
            role=role,
            revision=_sha256_commit(
                "a" * 64 if role is RevisionRole.BASE else "c" * 64
            ),
        ),
    )


def test_a_head_object_must_share_the_head_revision_algorithm() -> None:
    with pytest.raises(ValidationError, match="head object algorithms must match"):
        _change_set(
            changed_paths=(
                PullRequestChangedPath(
                    path=GitRepositoryPath("a"),
                    head_object=_sha256_blob(),
                    status=ChangedPathStatus.ADDED,
                ),
            )
        )


def test_the_base_and_head_revisions_must_share_one_algorithm() -> None:
    with pytest.raises(
        ValidationError, match="base and head revision algorithms must match"
    ):
        _change_set(
            head=_sha256_binding(RevisionRole.HEAD),
            changed_paths=_one_changed_path(),
        )


def test_a_wholly_sha256_change_set_is_accepted() -> None:
    change_set = PullRequestChangeSet(
        base=_sha256_binding(RevisionRole.BASE),
        head=_sha256_binding(RevisionRole.HEAD),
        changed_paths=(
            PullRequestChangedPath(
                path=GitRepositoryPath("a"),
                head_object=_sha256_blob(),
                status=ChangedPathStatus.MODIFIED,
            ),
        ),
    )

    assert change_set.head.role_assignment.revision.algorithm is (
        GitHashAlgorithm.SHA256
    )
    assert change_set.changed_paths[0].head_object.algorithm is (
        GitHashAlgorithm.SHA256
    )


def test_one_mismatched_entry_among_many_is_rejected() -> None:
    with pytest.raises(ValidationError, match="head object algorithms must match"):
        _change_set(
            changed_paths=(
                *_canonical_changed_paths(),
                PullRequestChangedPath(
                    path=GitRepositoryPath("later"),
                    head_object=_sha256_blob(),
                    status=ChangedPathStatus.ADDED,
                ),
            )
        )


def test_the_canonical_change_set_uses_one_algorithm_throughout() -> None:
    change_set = _change_set()
    algorithms = (
        {change_set.base.role_assignment.revision.algorithm}
        | {change_set.head.role_assignment.revision.algorithm}
        | {entry.head_object.algorithm for entry in change_set.changed_paths}
    )

    assert algorithms == {GitHashAlgorithm.SHA1}


# --- duplicate and bound rules ---------------------------------------------


def test_a_repeated_path_is_rejected_without_deduplication() -> None:
    entry = _changed_path(*CANONICAL_CHANGED_PATHS[0][:2], "added")

    with pytest.raises(ValidationError, match="must not repeat a repository path"):
        _change_set(changed_paths=(entry, entry))


def test_a_repeated_path_is_rejected_even_with_a_different_object() -> None:
    path = CANONICAL_CHANGED_PATHS[1][0]

    with pytest.raises(ValidationError, match="must not repeat a repository path"):
        _change_set(
            changed_paths=(
                _changed_path(path, CANONICAL_CHANGED_PATHS[1][1]),
                _changed_path(path, SYNTHETIC_BLOB),
            )
        )


def test_two_distinct_paths_sharing_one_object_are_allowed() -> None:
    change_set = _change_set(
        changed_paths=(
            _changed_path("a", SYNTHETIC_BLOB),
            _changed_path("b", SYNTHETIC_BLOB),
        )
    )

    assert len(change_set.changed_paths) == 2


def test_the_changed_path_collection_is_bounded() -> None:
    field = PullRequestChangeSet.model_fields["changed_paths"]

    assert [
        getattr(item, "min_length", None)
        for item in field.metadata
        if getattr(item, "min_length", None) is not None
    ] == [1]
    assert [
        getattr(item, "max_length", None)
        for item in field.metadata
        if getattr(item, "max_length", None) is not None
    ] == [4096]


def _distinct_changed_paths(count: int) -> tuple[PullRequestChangedPath, ...]:
    """`count` entries differing only by path, so only the bound is exercised."""
    return tuple(
        PullRequestChangedPath(
            path=GitRepositoryPath(f"generated/{index}"),
            head_object=_blob(SYNTHETIC_BLOB),
            status=ChangedPathStatus.MODIFIED,
        )
        for index in range(count)
    )


def test_the_maximum_changed_path_count_is_accepted() -> None:
    change_set = _change_set(changed_paths=_distinct_changed_paths(4096))

    assert len(change_set.changed_paths) == 4096


def test_exceeding_the_maximum_changed_path_count_is_rejected() -> None:
    with pytest.raises(ValidationError) as error:
        _change_set(changed_paths=_distinct_changed_paths(4097))

    assert error.value.errors()[0]["type"] == "too_long"


def test_the_changed_path_count_boundary_is_exact() -> None:
    for count, expected in ((0, False), (1, True), (4096, True), (4097, False)):
        try:
            _change_set(changed_paths=_distinct_changed_paths(count))
            accepted = True
        except ValidationError:
            accepted = False
        assert accepted is expected, f"{count} changed paths"


# --- semantic JSON ---------------------------------------------------------


def test_change_set_semantic_json_round_trip_preserves_the_exact_value() -> None:
    change_set = _change_set()

    restored = PullRequestChangeSet.model_validate_json(change_set.model_dump_json())

    assert restored == change_set
    assert restored.model_dump_json() == change_set.model_dump_json()


def test_change_set_json_payload_carries_exactly_the_three_semantic_keys() -> None:
    payload = _payload()

    assert set(payload) == {"base", "head", "changed_paths"}
    assert "schema_version" not in payload


def test_changed_path_json_payload_carries_exactly_three_keys() -> None:
    for entry in _entries(_payload()):
        assert set(entry) == {"path", "head_object", "status"}
        assert "schema_version" not in entry


def test_change_set_json_reconstruction_accepts_a_semantic_mapping() -> None:
    assert (
        PullRequestChangeSet.model_validate_json(json.dumps(_payload()))
        == _change_set()
    )


def test_changed_paths_serialize_as_an_ordered_json_array() -> None:
    assert [entry["path"] for entry in _entries(_payload())] == [
        path for path, _, _ in CANONICAL_CHANGED_PATHS
    ]


# --- model posture ---------------------------------------------------------


def test_change_set_is_frozen() -> None:
    change_set = _change_set()

    for field, value in (
        ("base", _base()),
        ("head", _head()),
        ("changed_paths", ()),
    ):
        with pytest.raises(ValidationError):
            setattr(change_set, field, value)

    assert change_set == _change_set()


def test_changed_path_is_frozen() -> None:
    entry = _canonical_changed_paths()[0]

    with pytest.raises(ValidationError):
        entry.status = ChangedPathStatus.MODIFIED

    with pytest.raises(ValidationError):
        del entry.path


def test_constructed_change_set_is_revalidated() -> None:
    assert PullRequestChangeSet.model_validate(_change_set()) == _change_set()


def test_change_set_revalidates_a_tampered_binding() -> None:
    tampered = PullRequestRevisionRoleBinding.model_construct(
        pull_request=_pull_request(),
        role_assignment=RevisionRoleAssignment(
            role=RevisionRole.MERGE, revision=_commit(CANONICAL_BASE_REVISION)
        ),
    )

    with pytest.raises(ValidationError):
        _change_set(base=tampered)


def test_change_set_revalidates_a_tampered_changed_path() -> None:
    tampered = PullRequestChangedPath.model_construct(
        path=GitRepositoryPath("a"),
        head_object=GitBlobIdentity.model_construct(
            schema_version=1,
            kind=GitObjectKind.BLOB,
            algorithm=GitHashAlgorithm.SHA1,
            full_digest="not-a-digest",
        ),
        status=ChangedPathStatus.ADDED,
    )

    with pytest.raises(ValidationError):
        _change_set(changed_paths=(tampered,))


def test_change_set_preserves_published_subclass_acceptance() -> None:
    class _SubclassedBinding(PullRequestRevisionRoleBinding):
        pass

    subclassed = _SubclassedBinding(
        pull_request=_pull_request(),
        role_assignment=RevisionRoleAssignment(
            role=RevisionRole.BASE, revision=_commit(CANONICAL_BASE_REVISION)
        ),
    )

    change_set = _change_set(base=subclassed)

    assert change_set == _change_set()
    assert type(change_set.base) is PullRequestRevisionRoleBinding


# --- required fields and closed extras -------------------------------------


@pytest.mark.parametrize("missing", ("base", "head", "changed_paths"))
def test_change_set_required_fields_cannot_be_omitted(missing: str) -> None:
    payload = _payload()
    del payload[missing]

    with pytest.raises(ValidationError) as error:
        PullRequestChangeSet.model_validate_json(json.dumps(payload))

    assert error.value.errors()[0]["type"] == "missing"
    assert error.value.errors()[0]["loc"] == (missing,)


@pytest.mark.parametrize("missing", ("path", "head_object", "status"))
def test_changed_path_required_fields_cannot_be_omitted(missing: str) -> None:
    payload = _payload()
    first = _entries(payload)[0]
    del first[missing]

    with pytest.raises(ValidationError):
        PullRequestChangeSet.model_validate_json(json.dumps(payload))


@pytest.mark.parametrize(
    "extra",
    (
        "ahead_by",
        "behind_by",
        "comparison",
        "diff",
        "evidence",
        "merge_base",
        "schema_version",
        "status",
        "total_commits",
    ),
)
def test_change_set_extra_fields_fail_closed(extra: str) -> None:
    payload = _payload()
    payload[extra] = "unexpected"

    with pytest.raises(ValidationError) as error:
        PullRequestChangeSet.model_validate_json(json.dumps(payload))

    assert error.value.errors()[0]["type"] == "extra_forbidden"


@pytest.mark.parametrize(
    "extra",
    ("base_object", "additions", "deletions", "hunks", "patch", "schema_version"),
)
def test_changed_path_extra_fields_fail_closed(extra: str) -> None:
    payload = _payload()
    first = _entries(payload)[0]
    first[extra] = "unexpected"

    with pytest.raises(ValidationError):
        PullRequestChangeSet.model_validate_json(json.dumps(payload))


# --- strict Python input ---------------------------------------------------


@pytest.mark.parametrize("field", ("base", "head"))
def test_change_set_rejects_untyped_python_bindings(field: str) -> None:
    supplied: dict[str, object] = {"base": _base(), "head": _head()}
    supplied[field] = json.loads(supplied[field].model_dump_json())  # type: ignore[union-attr]

    with pytest.raises(ValidationError, match="in Python input"):
        PullRequestChangeSet(
            base=supplied["base"],  # type: ignore[arg-type]
            head=supplied["head"],  # type: ignore[arg-type]
            changed_paths=_one_changed_path(),
        )


def test_change_set_accepts_a_json_array_of_changed_paths() -> None:
    assert (
        PullRequestChangeSet.model_validate_json(json.dumps(_payload())).changed_paths
        == _canonical_changed_paths()
    )


def test_change_set_python_construction_rejects_a_dumped_mapping() -> None:
    with pytest.raises(ValidationError, match="in Python input"):
        PullRequestChangeSet.model_validate(_payload())


@pytest.mark.parametrize(
    "value",
    (None, "changelog/4412.bugfix.rst", {"root": "a"}, _blob(SYNTHETIC_BLOB)),
)
def test_changed_path_rejects_untyped_python_paths(value: object) -> None:
    with pytest.raises(ValidationError, match="in Python input"):
        PullRequestChangedPath(
            path=value,  # type: ignore[arg-type]
            head_object=_blob(SYNTHETIC_BLOB),
            status=ChangedPathStatus.ADDED,
        )


@pytest.mark.parametrize(
    "value",
    (None, SYNTHETIC_BLOB, {"full_digest": SYNTHETIC_BLOB}, GitRepositoryPath("a")),
)
def test_changed_path_rejects_untyped_python_head_objects(value: object) -> None:
    with pytest.raises(ValidationError, match="in Python input"):
        PullRequestChangedPath(
            path=GitRepositoryPath("a"),
            head_object=value,  # type: ignore[arg-type]
            status=ChangedPathStatus.ADDED,
        )


class _AttributeBackedChangedPath:
    def __init__(self, entry: PullRequestChangedPath) -> None:
        self.path = entry.path
        self.head_object = entry.head_object
        self.status = entry.status


class _AttributeBackedBinding:
    def __init__(self, binding: PullRequestRevisionRoleBinding) -> None:
        self.pull_request = binding.pull_request
        self.role_assignment = binding.role_assignment


class _ForeignBinding(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    pull_request: object
    role_assignment: object


def test_change_set_rejects_attribute_backed_children_under_from_attributes() -> None:
    with pytest.raises(
        ValidationError, match="must contain PullRequestChangedPath values"
    ):
        PullRequestChangeSet.model_validate(
            {
                "base": _base(),
                "head": _head(),
                "changed_paths": (
                    _AttributeBackedChangedPath(_canonical_changed_paths()[0]),
                ),
            },
            from_attributes=True,
        )
    with pytest.raises(ValidationError, match="in Python input"):
        PullRequestChangeSet.model_validate(
            {
                "base": _AttributeBackedBinding(_base()),
                "head": _head(),
                "changed_paths": (),
            },
            from_attributes=True,
        )


def test_change_set_requires_a_tuple_of_changed_paths_in_python_input() -> None:
    with pytest.raises(ValidationError, match="must be a tuple in Python input"):
        PullRequestChangeSet(
            base=_base(),
            head=_head(),
            changed_paths=list(_canonical_changed_paths()),  # type: ignore[arg-type]
        )
    with pytest.raises(
        ValidationError, match="must contain PullRequestChangedPath values"
    ):
        PullRequestChangeSet(
            base=_base(),
            head=_head(),
            changed_paths=(
                json.loads(  # type: ignore[arg-type]
                    _canonical_changed_paths()[0].model_dump_json()
                ),
            ),
        )


def test_change_set_rejects_foreign_model_bindings_under_from_attributes() -> None:
    base = _base()

    with pytest.raises(ValidationError, match="in Python input"):
        PullRequestChangeSet.model_validate(
            {
                "base": _ForeignBinding(
                    pull_request=base.pull_request,
                    role_assignment=base.role_assignment,
                ),
                "head": _head(),
                "changed_paths": (),
            },
            from_attributes=True,
        )


# --- malformed child JSON --------------------------------------------------


@pytest.mark.parametrize(
    "path",
    ("", "/absolute", "a//b", "a/../b", "./a", "a/", None, 1, []),
)
def test_change_set_rejects_malformed_changed_path_json(path: object) -> None:
    payload = _payload()
    first = _entries(payload)[0]
    first["path"] = path

    with pytest.raises(ValidationError):
        PullRequestChangeSet.model_validate_json(json.dumps(payload))


@pytest.mark.parametrize(
    "head_object",
    (
        {},
        {"kind": "blob"},
        {"kind": "tree", "algorithm": "sha1", "full_digest": CANONICAL_HEAD_TREE},
        {"kind": "commit", "algorithm": "sha1", "full_digest": CANONICAL_HEAD_REVISION},
        {"kind": "blob", "algorithm": "sha1", "full_digest": "0" * 40},
        {"kind": "blob", "algorithm": "sha1", "full_digest": SYNTHETIC_BLOB.upper()},
        {"kind": "blob", "algorithm": "sha256", "full_digest": SYNTHETIC_BLOB},
        SYNTHETIC_BLOB,
        None,
    ),
)
def test_change_set_rejects_malformed_head_object_json(head_object: object) -> None:
    payload = _payload()
    first = _entries(payload)[0]
    first["head_object"] = head_object

    with pytest.raises(ValidationError):
        PullRequestChangeSet.model_validate_json(json.dumps(payload))


@pytest.mark.parametrize("changed_paths", ("", {}, None, 3, [[]], [None]))
def test_change_set_rejects_a_malformed_changed_path_collection(
    changed_paths: object,
) -> None:
    payload = _payload()
    payload["changed_paths"] = changed_paths

    with pytest.raises(ValidationError):
        PullRequestChangeSet.model_validate_json(json.dumps(payload))


def test_change_set_rejects_a_json_payload_that_is_not_an_object() -> None:
    for payload in ("[]", '"added"', "1", "null"):
        with pytest.raises(ValidationError):
            PullRequestChangeSet.model_validate_json(payload)


# --- non-claim boundary ----------------------------------------------------


@pytest.mark.parametrize(
    "absent",
    (
        "ahead_by",
        "ancestry",
        "behind_by",
        "commit_shas",
        "comparison",
        "complete",
        "diff",
        "evidence",
        "files",
        "merge_base",
        "reachable",
        "snapshot",
        "status",
        "total_commits",
    ),
)
def test_change_set_has_no_comparison_metric_or_evidence_field(absent: str) -> None:
    assert absent not in PullRequestChangeSet.model_fields


def test_the_change_set_claims_no_completeness() -> None:
    change_set = _change_set()

    assert not hasattr(change_set, "complete")
    assert not hasattr(change_set, "changed_path_count")
    # A shorter supplied set is an equally valid value, not an incomplete one.
    partial = _change_set(changed_paths=_canonical_changed_paths()[:1])
    assert len(partial.changed_paths) == 1
    assert partial != change_set


def test_the_change_set_expresses_no_ancestry_between_base_and_head() -> None:
    change_set = _change_set()

    for absent in ("descends_from", "ancestry", "merge_base", "reachable", "distance"):
        assert not hasattr(change_set, absent)
    assert change_set.base.role_assignment.revision != (
        change_set.head.role_assignment.revision
    )


def test_an_unrelated_base_and_head_pair_still_constructs() -> None:
    unrelated = _change_set(
        base=_binding(RevisionRole.BASE, SYNTHETIC_BLOB),
        changed_paths=_one_changed_path(),
    )

    assert unrelated.base.role_assignment.revision.full_digest == SYNTHETIC_BLOB


def test_equal_base_and_head_revisions_are_rejected() -> None:
    with pytest.raises(ValidationError, match="must be distinct revisions"):
        _change_set(base=_binding(RevisionRole.BASE, CANONICAL_HEAD_REVISION))


def test_equal_base_and_head_revisions_are_rejected_with_one_changed_path() -> None:
    with pytest.raises(ValidationError, match="must be distinct revisions"):
        _change_set(
            base=_binding(RevisionRole.BASE, CANONICAL_HEAD_REVISION),
            changed_paths=_one_changed_path(),
        )


def test_equal_base_and_head_revisions_are_rejected_in_json() -> None:
    payload = _payload()
    base = payload["base"]
    head = payload["head"]
    assert isinstance(base, dict) and isinstance(head, dict)
    base["role_assignment"]["revision"] = head["role_assignment"]["revision"]

    with pytest.raises(ValidationError, match="must be distinct revisions"):
        PullRequestChangeSet.model_validate_json(json.dumps(payload))


def test_the_canonical_base_and_head_revisions_differ() -> None:
    change_set = _change_set()

    assert change_set.base.role_assignment.revision != (
        change_set.head.role_assignment.revision
    )


def test_no_forbidden_identifier_appears_in_the_change_set_surface() -> None:
    tree = ast.parse(HISTORY_SOURCE.read_text(encoding="utf-8"))
    # Scoped to the classes this Slice owns; later relations in this module
    # carry their own forbidden-identifier assurance.
    owned = {"ChangedPathStatus", "PullRequestChangedPath", "PullRequestChangeSet"}
    body = [
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name in owned
    ]
    surface = "\n".join(ast.unparse(node) for node in body)

    for identifier in FORBIDDEN_CHANGE_SET_IDENTIFIERS:
        assert identifier not in surface


def test_the_change_set_does_not_use_p04_snapshot_contracts() -> None:
    source = HISTORY_SOURCE.read_text(encoding="utf-8")

    assert "faultatlas.domain.snapshot" not in source
    assert "RepositorySnapshotPathBinding" not in source
    assert "RepositorySnapshotIdentity" not in source


# --- module surface --------------------------------------------------------


def test_change_set_model_surfaces_are_exact() -> None:
    assert tuple(PullRequestChangeSet.model_fields) == (
        "base",
        "head",
        "changed_paths",
    )
    annotations = {
        name: field.annotation
        for name, field in PullRequestChangeSet.model_fields.items()
    }
    assert annotations == {
        "base": PullRequestRevisionRoleBinding,
        "head": PullRequestRevisionRoleBinding,
        "changed_paths": tuple[PullRequestChangedPath, ...],
    }
    assert tuple(PullRequestChangedPath.model_fields) == (
        "path",
        "head_object",
        "status",
    )
    assert {
        name: field.annotation
        for name, field in PullRequestChangedPath.model_fields.items()
    } == {
        "path": GitRepositoryPath,
        "head_object": GitBlobIdentity,
        "status": ChangedPathStatus,
    }

    expected_config = {
        "frozen": True,
        "extra": "forbid",
        "strict": True,
        "revalidate_instances": "always",
        "validate_default": True,
    }
    assert PullRequestChangeSet.model_config == expected_config
    assert PullRequestChangedPath.model_config == expected_config

    for model in (PullRequestChangeSet, PullRequestChangedPath):
        assert model.__module__ == "faultatlas.domain.history"
        for field in model.model_fields.values():
            assert field.is_required()
            assert field.discriminator is None
    assert ChangedPathStatus.__module__ == "faultatlas.domain.history"


def test_the_change_set_models_declare_the_expected_validators() -> None:
    tree = ast.parse(HISTORY_SOURCE.read_text(encoding="utf-8"))
    classes = {node.name: node for node in tree.body if isinstance(node, ast.ClassDef)}

    assert [
        node.name
        for node in classes["PullRequestChangedPath"].body
        if isinstance(node, ast.FunctionDef)
    ] == ["_require_typed_python_path", "_require_typed_python_head_object"]
    assert [
        node.name
        for node in classes["PullRequestChangeSet"].body
        if isinstance(node, ast.FunctionDef)
    ] == [
        "_require_typed_python_binding",
        "_require_strict_changed_paths",
        "_require_one_pull_request_and_its_two_roles",
        "_require_one_hash_algorithm",
        "_require_unique_changed_paths",
    ]
    assert [
        (target.id, ast.literal_eval(node.value))
        for node in classes["ChangedPathStatus"].body
        if isinstance(node, ast.Assign)
        for target in node.targets
        if isinstance(target, ast.Name)
    ] == [("ADDED", "added"), ("MODIFIED", "modified")]


def test_history_module_still_performs_no_io() -> None:
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


def test_no_canonical_case_literal_is_embedded_in_production() -> None:
    source = HISTORY_SOURCE.read_text(encoding="utf-8")

    for literal in (
        CANONICAL_REPOSITORY_ID,
        CANONICAL_PULL_REQUEST_NUMBER,
        CANONICAL_BASE_REVISION,
        CANONICAL_HEAD_REVISION,
        *(path for path, _, _ in CANONICAL_CHANGED_PATHS),
        *(blob for _, blob, _ in CANONICAL_CHANGED_PATHS),
    ):
        assert literal not in source


def test_the_roadmap_current_code_mapping_names_the_change_set() -> None:
    roadmap = " ".join(
        (REPOSITORY_ROOT / "docs/roadmap.md").read_text(encoding="utf-8").split()
    )
    mapping = roadmap.split("## Current-code mapping", 1)
    assert len(mapping) == 2, "roadmap must retain a current-code mapping section"
    current = mapping[1]

    for symbol in history_module.__all__:
        assert symbol in current
    assert "`S1.P05.S05` are complete" in current
    assert "`S1.P05.S05` is next and not started" not in current


def test_the_roadmap_records_the_c01_boundary_correction() -> None:
    roadmap = " ".join(
        (REPOSITORY_ROOT / "docs/roadmap.md").read_text(encoding="utf-8").split()
    )

    assert "`S1.P05.S02.C01`" in roadmap
    assert "Positive Change-Set Boundary Correction (complete)" in roadmap
    assert "between one and 4096 changed paths" in roadmap
    # The corrected claim must not survive anywhere in the current roadmap.
    assert "may be empty without asserting that nothing changed" not in roadmap
    # The S02 publication history is acknowledged, not rewritten.
    assert "`S1.P05.S02` — Pull Request Supplied Change Set (complete)" in roadmap
    assert "publication history stands unrewritten" in roadmap


def test_the_module_documents_both_corrected_boundaries() -> None:
    source = HISTORY_SOURCE.read_text(encoding="utf-8")
    docstring = ast.get_docstring(ast.parse(source)) or ""

    assert "At least one changed path is required" in docstring
    assert "base and head revisions must differ" in docstring
    assert "An empty change set supplies zero changed paths" not in docstring


def test_canonical_change_set_literals_remain_locked() -> None:
    assert CANONICAL_BASE_REVISION == "4c9cde74ab40027b5761ab9e002af116a4a20df3"
    assert CANONICAL_HEAD_REVISION == "690a63b9218f72662cd3a67c6c200b758c88ce12"
    assert CANONICAL_CHANGED_PATHS == (
        (
            "changelog/4412.bugfix.rst",
            "7a28b610837873eeff2a16582de6d5a035820552",
            "added",
        ),
        (
            "src/_pytest/assertion/rewrite.py",
            "7b9aa5006544c160f584f1e8fc3f7771ef6e5e99",
            "modified",
        ),
        (
            "testing/test_assertrewrite.py",
            "a02433cd62ab19ebb54b42b50c299e59e48de00e",
            "modified",
        ),
    )
    assert CANONICAL_UNCHANGED_PATH == (
        "LICENSE",
        "629df45ac405532c107eb233217bc2ac1ad70c88",
    )
