from __future__ import annotations

import ast
import gc
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
import types
import typing
import uuid
import weakref
import zipfile
from collections.abc import Callable, Hashable, Sized
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any, cast

import pytest
from pydantic import (
    AwareDatetime,
    BaseModel,
    BeforeValidator,
    ConfigDict,
    TypeAdapter,
    ValidationError,
)

import faultatlas
import faultatlas.domain
import faultatlas.domain.fault_source_relationship as relationship_module
import faultatlas.domain.history as history_module
from faultatlas.domain.evidence import (
    ArtifactByteLength,
    ArtifactSha256Digest,
    DurableEvidenceRecordReference,
    EvidenceCanonicalization,
    EvidenceRecordFormat,
    EvidenceVersion,
)
from faultatlas.domain.fault import (
    FaultInstanceIdentity,
    FaultOccurrenceIdentity,
    FaultReportIdentity,
    FaultRepositoryContext,
    FaultScenarioIdentity,
    SuppliedFaultOccurrenceContext,
    SuppliedFaultReport,
    SuppliedFaultScenario,
)
from faultatlas.domain.fault_source_relationship import (
    FaultReportHistoryFactAssociation,
    FaultReportSourceObjectAssociation,
)
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
from faultatlas.domain.history_evidence_link import PullRequestHistoryFactEvidenceLink
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
    GitBlobIdentity,
    GitCommitIdentity,
    GitHashAlgorithm,
    GitObjectKind,
    GitRefName,
    GitRepositoryPath,
    RevisionRole,
    RevisionRoleAssignment,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
RELATIONSHIP_SOURCE = (
    REPOSITORY_ROOT / "src/faultatlas/domain/fault_source_relationship.py"
)
FAULT_SOURCE = REPOSITORY_ROOT / "src/faultatlas/domain/fault.py"
CHECKOUT_SOURCE_ROOT = REPOSITORY_ROOT / "src"
ROADMAP = REPOSITORY_ROOT / "docs/roadmap.md"

# `faultatlas.domain.fault` as `S1.P06.S03` published it. This Slice adds a
# module beside it and changes none of its bytes.
FAULT_SOURCE_BYTES = 22323
FAULT_SOURCE_SHA256 = "f8b8bed37aff51b8848c303f2fbffde4e5e365216b5f46755b043fad2d254e26"

# Every FaultAtlas identifier and every piece of prose below is fixed synthetic
# supplied data. The retained pytest #4412 case supplies no fault or report
# identifier, and none of the text here is a historical quotation, an evidence
# record, or a claim that FaultAtlas executed pytest or verified any historical
# fact.
SUPPLIED_FAULT_TEXT = "12345678-1234-4234-8234-123456789abc"
SUPPLIED_FAULT = uuid.UUID(SUPPLIED_FAULT_TEXT)
SECOND_FAULT_TEXT = "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee"
SECOND_FAULT = uuid.UUID(SECOND_FAULT_TEXT)
SUPPLIED_REPORT_TEXT = "87654321-4321-4abc-8def-0123456789ab"
SUPPLIED_REPORT = uuid.UUID(SUPPLIED_REPORT_TEXT)
SECOND_REPORT_TEXT = "11111111-2222-4333-8444-555555555555"
SECOND_REPORT = uuid.UUID(SECOND_REPORT_TEXT)
SUPPLIED_SCENARIO_TEXT = "66666666-7777-4888-8999-aaaaaaaaaaaa"
SUPPLIED_OCCURRENCE_TEXT = "12121212-3434-4565-8787-9a9a9a9a9a9a"

PROBLEM_STATEMENT = "Instrumentation can change callback behavior."
BEHAVIORAL_DEVIATION = "The supplied transformed path invokes one callback twice."
SECOND_PROBLEM_STATEMENT = "A cached rewrite may be reused after the source changes."
SECOND_BEHAVIORAL_DEVIATION = "The supplied stale rewrite reports the wrong line."
SCENARIO_STATEMENT = "A rewritten assertion evaluates a side-effecting callback."
OCCURRENCE_CONTEXT = "The caller encountered the duplicate callback in this scenario."

# Retained pytest case identities. They are typed fixtures only: every S04
# association below remains explicitly caller-supplied.
RETAINED_PROVIDER = "github"
RETAINED_REPOSITORY_ID = "37489525"
OTHER_REPOSITORY_ID = "37489526"
RETAINED_ISSUE_NUMBER = "4412"
RETAINED_PULL_REQUEST_NUMBER = "4414"
RETAINED_REVIEW_GLOBAL_ID = "176071572"
RETAINED_BASE_REVISION = "4c9cde74ab40027b5761ab9e002af116a4a20df3"
RETAINED_HEAD_REVISION = "690a63b9218f72662cd3a67c6c200b758c88ce12"
RETAINED_MERGE_REVISION = "10cdae8e38ec448b7133cf163dca587ad806d262"
RETAINED_HEAD_REF_NAME = "starred_with_side_effect"
RETAINED_CHANGED_PATHS = (
    ("changelog/4412.bugfix.rst", "7a28b610837873eeff2a16582de6d5a035820552", "added"),
    (
        "src/_pytest/assertion/rewrite.py",
        "7b9aa5006544c160f584f1e8fc3f7771ef6e5e99",
        "modified",
    ),
)
RETAINED_MERGE_INSTANT = "2018-11-18T00:17:25Z"
RETAINED_APPROVAL_INSTANT = "2018-11-17T23:54:20Z"
RETAINED_DELETION_INSTANT = "2018-11-18T00:17:28Z"

# Provider global identifiers for the comment, review-comment and timeline
# kinds. Only the review identifier above is retained material; these three are
# synthetic values in the retained lexical shape, used to witness that the
# published kinds are admitted rather than to assert a historical object.
SYNTHETIC_ISSUE_COMMENT_GLOBAL_ID = "900000001"
SYNTHETIC_PULL_REQUEST_COMMENT_GLOBAL_ID = "900000002"
SYNTHETIC_REVIEW_COMMENT_GLOBAL_ID = "900000003"
SYNTHETIC_TIMELINE_EVENT_GLOBAL_ID = "900000004"

# The module's whole declared surface. Pinning only `__all__`, only class names
# or only module-level functions leaves room for a registry, an adjacency
# accessor or a pairing method to be added without a single test failing, so
# every top-level binding and every class member is named here.
DECLARED_MODULE_BINDINGS = (
    "__all__",
    "_UNTYPED_REPORT_MESSAGE",
    "_UNTYPED_SOURCE_OBJECT_MESSAGE",
    "_UNTYPED_FACT_MESSAGE",
    "_ADMITTED_SOURCE_OBJECTS",
    "_OCCURRED_AT",
    "_require_published_fact",
    "_require_published_occurrence_time",
    "_PublishedRevisionRoleBinding",
    "_PublishedChangedPath",
    "_PublishedReviewRevisionApproval",
    "_PublishedMergeRevisionOutcome",
    "_PublishedHeadRefDeletion",
    "_PublishedHistoricalOccurrenceTime",
    "FaultReportSourceObjectAssociation",
    "FaultReportHistoryFactAssociation",
)
# Two guards share one name across the two classes, and `_require` is the
# closure `_require_published_fact` returns.
DECLARED_FUNCTIONS = (
    "_require",
    "_require_published_fact",
    "_require_published_occurrence_time",
    "_require_typed_python_report",
    "_require_typed_python_report",
    "_require_typed_python_source_object",
)
# Names the module imports. Together with the bindings above these are the
# module's whole runtime namespace, which is asserted directly: an AST scan can
# be dodged by a binding shape it does not model -- a tuple target, a starred
# target, a PEP 695 `type` statement -- while `vars()` sees every one.
DECLARED_MODULE_IMPORTS = (
    "Annotated",
    "Any",
    "AwareDatetime",
    "BaseModel",
    "BeforeValidator",
    "Callable",
    "ConfigDict",
    "Mapping",
    "NumberedSourceObjectIdentity",
    "ProviderScopedSourceObjectIdentity",
    "PullRequestChangedPath",
    "PullRequestHeadRefDeletion",
    "PullRequestHistoricalOccurrenceTime",
    "PullRequestMergeRevisionOutcome",
    "PullRequestReviewRevisionApproval",
    "PullRequestRevisionRoleBinding",
    "SuppliedFaultReport",
    "TypeAdapter",
    "ValidationInfo",
    "cast",
    "datetime",
    "field_validator",
)
# Only the statement forms the module actually uses. A `type` statement, a
# loop, a conditional or a context manager at module level is a shape this
# contract does not have and would carry behaviour no scan below models.
ADMITTED_TOP_LEVEL_STATEMENTS = (
    ast.AnnAssign,
    ast.Assign,
    ast.ClassDef,
    ast.Expr,
    ast.FunctionDef,
    ast.ImportFrom,
)

DECLARED_CLASS_MEMBERS: dict[str, tuple[str, ...]] = {
    "FaultReportSourceObjectAssociation": (
        "model_config",
        "report",
        "source_object",
        "_require_typed_python_report",
        "_require_typed_python_source_object",
    ),
    "FaultReportHistoryFactAssociation": (
        "model_config",
        "report",
        "history_fact",
        "_require_typed_python_report",
    ),
}

SOURCE_FIELDS = ("report", "source_object")
HISTORY_FIELDS = ("report", "history_fact")
EXPECTED_EXPORTS = [
    "FaultReportSourceObjectAssociation",
    "FaultReportHistoryFactAssociation",
]

# The six published `S1.P05` facts this relation admits, which are exactly the
# six the `S1.P05.S07` evidence link admits. The excluded set is derived from
# `history.__all__` against these rather than hand-listed, so a later published
# history symbol cannot become silently admissible or silently unpinned.
ADMITTED_FACT_TYPES: tuple[type[BaseModel], ...] = (
    PullRequestRevisionRoleBinding,
    PullRequestChangedPath,
    PullRequestReviewRevisionApproval,
    PullRequestMergeRevisionOutcome,
    PullRequestHeadRefDeletion,
    PullRequestHistoricalOccurrenceTime,
)
ADMITTED_SOURCE_TYPES: tuple[type[BaseModel], ...] = (
    NumberedSourceObjectIdentity,
    ProviderScopedSourceObjectIdentity,
)
_ADMITTED_TYPE_NAMES = frozenset(
    model.__name__ for model in (*ADMITTED_FACT_TYPES, *ADMITTED_SOURCE_TYPES)
)

# Neither association may grow an evidence, support, strength, confidence,
# role, causation or repair vocabulary. `schema_version` is listed separately
# below because the embedded children legitimately carry it: its absence is
# meaningful at association level only.
FORBIDDEN_ASSOCIATION_IDENTIFIERS = (
    "affected_path",
    "authoritative",
    "cause",
    "causal",
    "certainty",
    "confidence",
    "corroborated",
    "derived",
    "edge",
    "evidence",
    "evidence_record",
    "fix",
    "fixed_by",
    "graph",
    "hypothesis",
    "inverse",
    "kind",
    "observed",
    "origin",
    "originated",
    "pair",
    "predicate",
    "primary",
    "proves",
    "reachable",
    "relation_id",
    "relationship",
    "relationship_id",
    "relationship_kind",
    "relationship_type",
    "repair",
    "review_state",
    "role",
    "status",
    "strength",
    "subject",
    "supported",
    "support_role",
    "transitive",
    "verified",
)
REFUSED_EXTRA_KEYS = (*FORBIDDEN_ASSOCIATION_IDENTIFIERS, "schema_version")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _repository(identifier: str = RETAINED_REPOSITORY_ID) -> RepositoryIdentity:
    return RepositoryIdentity(
        provider=ProviderKey(RETAINED_PROVIDER),
        provider_repository_id=ProviderRepositoryId(identifier),
    )


def _context(
    fault: uuid.UUID = SUPPLIED_FAULT,
    repository: str = RETAINED_REPOSITORY_ID,
) -> FaultRepositoryContext:
    return FaultRepositoryContext(
        fault=FaultInstanceIdentity(fault),
        repository=_repository(repository),
    )


def _report(
    report: uuid.UUID = SUPPLIED_REPORT,
    fault: uuid.UUID = SUPPLIED_FAULT,
    repository: str = RETAINED_REPOSITORY_ID,
    problem_statement: str = PROBLEM_STATEMENT,
    behavioral_deviation: str = BEHAVIORAL_DEVIATION,
) -> SuppliedFaultReport:
    return SuppliedFaultReport(
        report=FaultReportIdentity(report),
        context=_context(fault, repository),
        problem_statement=problem_statement,
        behavioral_deviation=behavioral_deviation,
    )


def _second_report() -> SuppliedFaultReport:
    return _report(
        report=SECOND_REPORT,
        fault=SECOND_FAULT,
        problem_statement=SECOND_PROBLEM_STATEMENT,
        behavioral_deviation=SECOND_BEHAVIORAL_DEVIATION,
    )


def _numbered(
    kind: SourceObjectKind = SourceObjectKind.ISSUE,
    number: str = RETAINED_ISSUE_NUMBER,
    repository: str = RETAINED_REPOSITORY_ID,
) -> NumberedSourceObjectIdentity:
    return NumberedSourceObjectIdentity(
        repository_identity=_repository(repository),
        kind=kind,
        repository_scoped_number=RepositoryScopedNumber(number),
    )


def _issue(repository: str = RETAINED_REPOSITORY_ID) -> NumberedSourceObjectIdentity:
    return _numbered(SourceObjectKind.ISSUE, RETAINED_ISSUE_NUMBER, repository)


def _pull_request(
    repository: str = RETAINED_REPOSITORY_ID,
) -> NumberedSourceObjectIdentity:
    return _numbered(
        SourceObjectKind.PULL_REQUEST, RETAINED_PULL_REQUEST_NUMBER, repository
    )


def _provider_scoped(
    kind: SourceObjectKind,
    global_id: str,
    parent: NumberedSourceObjectIdentity | None = None,
) -> ProviderScopedSourceObjectIdentity:
    return ProviderScopedSourceObjectIdentity(
        kind=kind,
        provider_global_id=ProviderGlobalId(global_id),
        parent=_pull_request() if parent is None else parent,
    )


def _review() -> ProviderScopedSourceObjectIdentity:
    return _provider_scoped(
        SourceObjectKind.PULL_REQUEST_REVIEW, RETAINED_REVIEW_GLOBAL_ID
    )


def _commit(full_digest: str = RETAINED_HEAD_REVISION) -> GitCommitIdentity:
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
    role: RevisionRole = RevisionRole.HEAD,
    full_digest: str = RETAINED_HEAD_REVISION,
) -> PullRequestRevisionRoleBinding:
    return PullRequestRevisionRoleBinding(
        pull_request=_pull_request(),
        role_assignment=RevisionRoleAssignment(
            role=role, revision=_commit(full_digest)
        ),
    )


def _changed_path(index: int = 0) -> PullRequestChangedPath:
    path, blob, status = RETAINED_CHANGED_PATHS[index]
    return PullRequestChangedPath(
        path=GitRepositoryPath(path),
        head_object=_blob(blob),
        status=ChangedPathStatus(status),
    )


def _approval() -> PullRequestReviewRevisionApproval:
    return PullRequestReviewRevisionApproval(
        review=_review(),
        approved_revision=_commit(),
    )


def _outcome() -> PullRequestMergeRevisionOutcome:
    return PullRequestMergeRevisionOutcome(
        pull_request=_pull_request(),
        merge_revision=_commit(RETAINED_MERGE_REVISION),
    )


def _deletion() -> PullRequestHeadRefDeletion:
    return PullRequestHeadRefDeletion(
        head=_binding(),
        head_ref_name=GitRefName(RETAINED_HEAD_REF_NAME),
    )


def _instant(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _occurrence_time(
    occurrence: (
        PullRequestReviewRevisionApproval
        | PullRequestMergeRevisionOutcome
        | PullRequestHeadRefDeletion
        | None
    ) = None,
    instant: str = RETAINED_MERGE_INSTANT,
) -> PullRequestHistoricalOccurrenceTime:
    return PullRequestHistoricalOccurrenceTime(
        occurrence=_outcome() if occurrence is None else occurrence,
        occurred_at=_instant(instant),
    )


def _change_set() -> PullRequestChangeSet:
    return PullRequestChangeSet(
        base=_binding(RevisionRole.BASE, RETAINED_BASE_REVISION),
        head=_binding(),
        changed_paths=tuple(
            _changed_path(index) for index in range(len(RETAINED_CHANGED_PATHS))
        ),
    )


def _evidence_link() -> PullRequestHistoryFactEvidenceLink:
    return PullRequestHistoryFactEvidenceLink(
        fact=_outcome(),
        evidence_record=DurableEvidenceRecordReference(
            format_name=EvidenceRecordFormat("faultatlas-acquisition"),
            format_version=EvidenceVersion("1"),
            canonicalization=EvidenceCanonicalization(
                "json-sort-keys-compact-utf8-lf-v1"
            ),
            sha256=ArtifactSha256Digest(
                "1c29093bf1537e9b824a18df1848b71a8da014f544bc9f385707eb0e000a1318"
            ),
            byte_length=ArtifactByteLength(61_283),
        ),
    )


def _source_association(
    report: SuppliedFaultReport | None = None,
    source_object: (
        NumberedSourceObjectIdentity | ProviderScopedSourceObjectIdentity | None
    ) = None,
) -> FaultReportSourceObjectAssociation:
    return FaultReportSourceObjectAssociation(
        report=_report() if report is None else report,
        source_object=_issue() if source_object is None else source_object,
    )


def _history_association(
    report: SuppliedFaultReport | None = None,
    history_fact: Any = None,
) -> FaultReportHistoryFactAssociation:
    return FaultReportHistoryFactAssociation(
        report=_report() if report is None else report,
        history_fact=_outcome() if history_fact is None else history_fact,
    )


def _typed_source_mapping(**overrides: object) -> dict[str, Any]:
    mapping: dict[str, Any] = {"report": _report(), "source_object": _issue()}
    mapping.update(overrides)
    return mapping


def _typed_history_mapping(**overrides: object) -> dict[str, Any]:
    mapping: dict[str, Any] = {"report": _report(), "history_fact": _outcome()}
    mapping.update(overrides)
    return mapping


def _payload(value: BaseModel) -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(value.model_dump_json()))


def _is_union_branch_label(part: object) -> bool:
    """Pydantic's own union-branch label, which this contract does not lock."""
    return isinstance(part, str) and ("[" in part or part in _ADMITTED_TYPE_NAMES)


def _paths(error: ValidationError) -> tuple[tuple[str | int, ...], ...]:
    return tuple(
        tuple(part for part in detail["loc"] if not _is_union_branch_label(part))
        for detail in error.errors()
    )


def _failures(error: ValidationError) -> tuple[tuple[tuple[str | int, ...], str], ...]:
    return tuple(
        (
            tuple(part for part in detail["loc"] if not _is_union_branch_label(part)),
            detail["type"],
        )
        for detail in error.errors()
    )


def _target_names(target: ast.expr) -> list[str]:
    """Every name one assignment target binds, tuple and starred forms included."""
    if isinstance(target, ast.Name):
        return [target.id]
    if isinstance(target, ast.Starred):
        return _target_names(target.value)
    if isinstance(target, ast.Tuple | ast.List):
        return [name for item in target.elts for name in _target_names(item)]
    return []


def _own_attribute_names(value: object) -> frozenset[str]:
    """The names in one object's own `__dict__`, or none when it has none."""
    carried = cast("dict[str, object] | None", getattr(value, "__dict__", None))
    return frozenset(carried) if carried is not None else frozenset()


def _identity(value: object) -> object:
    """A do-nothing validator, used only to build a reference `Annotated`."""
    return value


def _reference_adapter() -> TypeAdapter[datetime]:
    """A freshly built adapter of the shape the module declares."""
    return TypeAdapter(AwareDatetime)


class _ReferenceValueModel(BaseModel):
    """A model under the published profile, carrying no validator of its own.

    Its class attributes are whatever Pydantic and `abc` install, so comparing
    against it keeps the surface check from hand-listing an internal.
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        strict=True,
        revalidate_instances="always",
        validate_default=True,
    )

    supplied: int


PYDANTIC_CLASS_ATTRIBUTES = frozenset(
    name
    for name in _own_attribute_names(_ReferenceValueModel)
    if not name.startswith("__")
)


def _bound_names(body: list[ast.stmt]) -> list[str]:
    """Every name one block binds, through every shape the grammar allows.

    Handling only simple `Name` targets would miss a tuple assignment, which is
    how a module-level container can be introduced without adding a visible
    name to any list this file pins.
    """
    names: list[str] = []
    for node in body:
        if isinstance(node, ast.Assign):
            names += [name for target in node.targets for name in _target_names(target)]
        elif isinstance(node, ast.AnnAssign):
            names += _target_names(node.target)
        elif isinstance(node, ast.TypeAlias):
            names += _target_names(node.name)
        elif isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
            names.append(node.name)
    return names


def _public_surface(model: type[BaseModel]) -> set[str]:
    """Public names the model adds beyond plain `BaseModel`.

    Pydantic fields are not class attributes, so a clean value model adds none.
    A property, method or classmethod added to either association appears here
    even though `model_fields` and the JSON payload stay unchanged.
    """
    return {name for name in dir(model) if not name.startswith("_")} - set(
        dir(BaseModel)
    )


def _module_body() -> str:
    """The module source below its docstring.

    Splitting on a bare delimiter stops at the LAST triple quote in the file,
    which is the end of the second class docstring, so it would scan only the
    final class body. The maxsplit keeps the whole body in view. Whitespace is
    normalized as it is for the roadmap and comment markers are dropped, so a
    phrase wrapped across two comment lines at the line-length bound is still
    one phrase to a reader of this.
    """
    body = RELATIONSHIP_SOURCE.read_text(encoding="utf-8").split('"""', 2)[-1]
    unmarked = [line.lstrip().removeprefix("#") for line in body.splitlines()]
    return " ".join(" ".join(unmarked).split())


def _relationship_tree() -> ast.Module:
    return ast.parse(
        RELATIONSHIP_SOURCE.read_bytes(), filename=RELATIONSHIP_SOURCE.name
    )


def _roadmap() -> str:
    return " ".join(ROADMAP.read_text(encoding="utf-8").split())


def _published_models() -> tuple[type[BaseModel], ...]:
    return (FaultReportSourceObjectAssociation, FaultReportHistoryFactAssociation)


def _annotation_members(annotation: object) -> tuple[object, ...]:
    """The declared members of a field annotation, unwrapping unions and Annotated.

    The history-fact position declares its members through `Annotated` aliases
    carrying each member's own guard, so a reader that only looked at
    `typing.get_args` of the union would see the aliases rather than the
    published types this relation admits. A PEP 695 `type` alias is resolved
    for the same reason: it is neither a class nor a union at runtime, so an
    unresolved one would be dropped by any caller filtering for classes, and a
    union widened through an alias would pass an exactness witness unnoticed.
    """
    if isinstance(annotation, typing.TypeAliasType):
        return _annotation_members(annotation.__value__)
    origin = typing.get_origin(annotation)
    if origin is typing.Annotated:
        return _annotation_members(typing.get_args(annotation)[0])
    if origin in (typing.Union, types.UnionType):
        members: list[object] = []
        for argument in typing.get_args(annotation):
            members.extend(_annotation_members(argument))
        return tuple(members)
    return (annotation,)


def _declared_member_names(model: type[BaseModel], field_name: str) -> tuple[str, ...]:
    """Every declared member of one field position, as published class names.

    Members are asserted to be classes rather than filtered for classes: a
    member this walker cannot resolve is a hole in the exactness witness, not a
    member to skip.
    """
    members = _annotation_members(model.model_fields[field_name].annotation)
    for member in members:
        assert isinstance(member, type), (model.__name__, field_name, member)
    return tuple(cast(type, member).__name__ for member in members)


def _distinct_value_count(*values: object) -> int:
    return len(set(cast(tuple[Hashable, ...], values)))


def _accepts(validate: Callable[[], object]) -> bool:
    try:
        validate()
    except ValidationError:
        return False
    return True


# --- foreign, lookalike and subclass carriers --------------------------------


class ForeignSourceObjectAssociation(BaseModel):
    """A structurally identical relation that is not the published type."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        strict=True,
        revalidate_instances="always",
        validate_default=True,
    )

    report: SuppliedFaultReport
    source_object: NumberedSourceObjectIdentity


class ForeignNumberedSourceObjectIdentity(BaseModel):
    """A structurally identical identity that is not the published type."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        strict=True,
        revalidate_instances="always",
        validate_default=True,
    )

    schema_version: int = 1
    repository_identity: RepositoryIdentity
    kind: SourceObjectKind
    repository_scoped_number: RepositoryScopedNumber


class SourceObjectLookalike:
    """An attribute-backed object carrying the published field names."""

    def __init__(self) -> None:
        self.schema_version = 1
        self.repository_identity = _repository()
        self.kind = SourceObjectKind.ISSUE
        self.repository_scoped_number = RepositoryScopedNumber(RETAINED_ISSUE_NUMBER)


class ReportLookalike:
    """An attribute-backed object carrying the published report field names."""

    def __init__(self) -> None:
        self.report = FaultReportIdentity(SUPPLIED_REPORT)
        self.context = _context()
        self.problem_statement = PROBLEM_STATEMENT
        self.behavioral_deviation = BEHAVIORAL_DEVIATION


class HistoryFactLookalike:
    """An attribute-backed object carrying a published fact's field names."""

    def __init__(self) -> None:
        self.pull_request = _pull_request()
        self.merge_revision = _commit(RETAINED_MERGE_REVISION)


class UnextendedSuppliedFaultReport(SuppliedFaultReport):
    """An ordinary report subclass that adds no field."""


class UnextendedNumberedSourceObjectIdentity(NumberedSourceObjectIdentity):
    """An ordinary source-object subclass that adds no field."""


class UnextendedMergeRevisionOutcome(PullRequestMergeRevisionOutcome):
    """An ordinary history-fact subclass that adds no field."""


class ExtendedSuppliedFaultReport(SuppliedFaultReport):
    """A report subclass that adds a field the base schema forbids."""

    note: str = "supplied"


# --- exact shape and the strict profile ---------------------------------------


def test_the_module_publishes_exactly_two_symbols_in_order() -> None:
    assert relationship_module.__all__ == EXPECTED_EXPORTS
    assert len(relationship_module.__all__) == 2
    assert [
        node.name
        for node in ast.walk(_relationship_tree())
        if isinstance(node, ast.ClassDef)
    ] == EXPECTED_EXPORTS


def test_the_module_declares_exactly_its_documented_top_level_surface() -> None:
    """A registry or adjacency table added beside the models must fail here.

    `__all__` and the class names alone do not pin the module: a module-level
    mutable container plus a `model_post_init` that fills it would publish the
    Issue-to-pull-request edge this contract says is never constructed, while
    leaving every field, payload and export untouched.
    """
    tree = _relationship_tree()

    assert tuple(_bound_names(tree.body)) == DECLARED_MODULE_BINDINGS

    for index, node in enumerate(tree.body):
        assert isinstance(node, ADMITTED_TOP_LEVEL_STATEMENTS), type(node).__name__
        # A bare expression binds no name and is not scanned for containers, so
        # it is admitted only as the docstring. `setattr(value, ..., {})` is
        # otherwise a module-level statement that no other check would see.
        assert not isinstance(node, ast.Expr) or index == 0, ast.dump(node)[:120]

    # `__all__` is a list by repository convention; nothing else may build a
    # mutable container anywhere in its value, because a module-level container
    # is the shape a relation registry takes.
    mutable = (ast.Dict, ast.List, ast.Set, ast.DictComp, ast.ListComp, ast.SetComp)
    for node in tree.body:
        if not isinstance(node, ast.Assign | ast.AnnAssign):
            continue
        if _bound_names([node]) == ["__all__"]:
            continue
        assert node.value is not None
        for inner in ast.walk(node.value):
            assert not isinstance(inner, mutable), ast.dump(inner)[:120]


def test_the_module_binds_exactly_its_documented_names_at_runtime() -> None:
    """The namespace itself is pinned, not one reading of the syntax tree.

    Every source scan in this file models some set of binding shapes, and a
    shape it does not model is a way to introduce a relation registry that no
    scan reports. `vars()` sees the result of every shape, so a hidden binding
    fails here whatever syntax produced it.
    """
    bound = {name for name in vars(relationship_module) if not name.startswith("__")}
    declared = {name for name in DECLARED_MODULE_BINDINGS if not name.startswith("__")}

    assert bound == declared | set(DECLARED_MODULE_IMPORTS)
    assert relationship_module.__all__ == EXPECTED_EXPORTS
    for name, value in vars(relationship_module).items():
        if name.startswith("__"):
            continue
        assert not isinstance(value, dict | list | set), name
        # A function attribute is another place a container can live, and it
        # is bound at import time without adding a module-level name.
        if isinstance(value, types.FunctionType):
            assert vars(value) == {}, name


def test_each_association_declares_exactly_its_documented_members() -> None:
    """A pairing method, a role property or a hash override must fail here."""
    classes = {
        node.name: node
        for node in _relationship_tree().body
        if isinstance(node, ast.ClassDef)
    }

    assert set(classes) == set(DECLARED_CLASS_MEMBERS)
    for name, declared in DECLARED_CLASS_MEMBERS.items():
        assert tuple(_bound_names(classes[name].body)) == declared, name
        assert "model_post_init" not in _bound_names(classes[name].body), name
        for member in _bound_names(classes[name].body):
            assert not member.startswith("__"), (name, member)


def test_no_module_level_value_carries_an_unexpected_attribute() -> None:
    """A container may live on a value's `__dict__` without binding a name.

    The runtime namespace check sees module-level names and the AST checks see
    module-level statements; neither sees an attribute set on an already
    declared value, which is one more place the prohibited relation registry
    fits. Each value the module creates is therefore compared with a freshly
    built equivalent, so a Pydantic or typing internal is not hand-listed here
    while an added attribute still fails.
    """
    reference_alias = Annotated[int, BeforeValidator(_identity)]
    expected: dict[str, frozenset[str]] = {
        "_OCCURRED_AT": _own_attribute_names(_reference_adapter()),
        "_require_published_fact": frozenset(),
        "_require_published_occurrence_time": frozenset(),
    }
    for alias in (
        "_PublishedRevisionRoleBinding",
        "_PublishedChangedPath",
        "_PublishedReviewRevisionApproval",
        "_PublishedMergeRevisionOutcome",
        "_PublishedHeadRefDeletion",
        "_PublishedHistoricalOccurrenceTime",
    ):
        expected[alias] = _own_attribute_names(reference_alias)

    for name in DECLARED_MODULE_BINDINGS:
        if name == "__all__" or name in DECLARED_CLASS_MEMBERS:
            continue
        value = cast(object, getattr(relationship_module, name))
        carried = _own_attribute_names(value)
        assert carried == expected.get(name, frozenset()), (name, sorted(carried))

    for name in DECLARED_CLASS_MEMBERS:
        model = cast(type[BaseModel], getattr(relationship_module, name))
        own = {
            member
            for member in _own_attribute_names(model)
            if not member.startswith("__")
        }
        declared = {
            member
            for member in DECLARED_CLASS_MEMBERS[name]
            if member.startswith("_require")
        }
        assert own == declared | PYDANTIC_CLASS_ATTRIBUTES, (name, sorted(own))


def _construct_and_weakly_reference() -> dict[str, weakref.ReferenceType[Any]]:
    """Build one of each association and return weak references to the parts."""
    report = _report()
    source_object = _issue()
    history_fact = _outcome()
    source = FaultReportSourceObjectAssociation(
        report=report, source_object=source_object
    )
    history = FaultReportHistoryFactAssociation(
        report=report, history_fact=history_fact
    )
    return {
        "report": weakref.ref(report),
        "source_object": weakref.ref(source_object),
        "history_fact": weakref.ref(history_fact),
        "source_association": weakref.ref(source),
        "history_association": weakref.ref(history),
    }


def test_constructing_an_association_retains_nothing_anywhere() -> None:
    """No relation registry can exist, wherever one might be hidden.

    Every check above names the places a container may live -- a module
    binding, a class member, a value's attributes -- and each such list has in
    turn been beaten by a place it did not name: a tuple target, a type alias,
    a function attribute, an adapter attribute, a dunder global, a dunder class
    attribute, an attribute on an imported object, an attribute on `BaseModel`
    itself. Enumerating hiding places does not converge, so this asserts the
    property instead of the locations.

    A relation registry has to retain what it registers. Nothing here does, so
    once the caller drops an association every part of it becomes unreachable,
    whatever code ran during validation and wherever it tried to store the
    result. A registry keyed on the report and holding source objects keeps the
    source object alive and fails here; so does one holding the report, the
    fact, or the association.
    """
    references = _construct_and_weakly_reference()
    gc.collect()

    retained = sorted(name for name, ref in references.items() if ref() is not None)

    assert retained == []


def test_repeated_construction_adds_no_reachable_module_state() -> None:
    """A registry that survived collection would still have to grow."""
    for _ in range(2):
        _source_association()

    def _container_sizes() -> dict[str, int]:
        return {
            name: len(cast("Sized", value))
            for name, value in vars(relationship_module).items()
            if isinstance(value, dict | list | set | bytearray)
        }

    before = _container_sizes()
    for _ in range(25):
        _source_association(source_object=_issue())
        _source_association(source_object=_pull_request())
        _history_association()

    assert _container_sizes() == before


def test_neither_association_publishes_an_attribute_beyond_its_fields() -> None:
    """A forbidden meaning may not arrive as a property or method either.

    `model_fields` and the JSON payload are both blind to a reachable
    attribute, so the same forbidden names are checked against the class and an
    instance as well.
    """
    for model in _published_models():
        assert _public_surface(model) == set(), model.__name__
        assert model.model_computed_fields == {}

    for value in (_source_association(), _history_association()):
        for name in FORBIDDEN_ASSOCIATION_IDENTIFIERS:
            assert not hasattr(value, name), (type(value).__name__, name)
            assert not hasattr(type(value), name), (type(value).__name__, name)
        for name in ("pair", "pairs_with", "siblings", "supports", "originated_here"):
            assert not hasattr(value, name), (type(value).__name__, name)


def test_each_association_declares_exactly_two_fields_in_order() -> None:
    assert tuple(FaultReportSourceObjectAssociation.model_fields) == SOURCE_FIELDS
    assert tuple(FaultReportHistoryFactAssociation.model_fields) == HISTORY_FIELDS


@pytest.mark.parametrize("model", _published_models(), ids=lambda m: m.__name__)
def test_each_association_declares_the_published_value_profile(
    model: type[BaseModel],
) -> None:
    assert model.model_config == {
        "frozen": True,
        "extra": "forbid",
        "strict": True,
        "revalidate_instances": "always",
        "validate_default": True,
    }


@pytest.mark.parametrize("model", _published_models(), ids=lambda m: m.__name__)
def test_an_association_is_frozen(model: type[BaseModel]) -> None:
    value: BaseModel = (
        _source_association()
        if model is FaultReportSourceObjectAssociation
        else _history_association()
    )

    with pytest.raises(ValidationError) as failure:
        setattr(value, "report", _second_report())

    assert _failures(failure.value) == ((("report",), "frozen_instance"),)


def test_no_association_declares_a_role_evidence_or_strength_field() -> None:
    for model in _published_models():
        declared = set(model.model_fields)
        for name in FORBIDDEN_ASSOCIATION_IDENTIFIERS:
            assert name not in declared, name


def test_neither_association_json_payload_carries_a_forbidden_key() -> None:
    for payload in (_payload(_source_association()), _payload(_history_association())):
        for name in FORBIDDEN_ASSOCIATION_IDENTIFIERS:
            assert name not in payload, name
        assert "schema_version" not in payload


# --- source-object association: construction, JSON and reentry ----------------


def test_a_source_association_is_built_from_already_typed_values() -> None:
    association = _source_association()

    assert association.report == _report()
    assert association.source_object == _issue()
    assert association.report.context.fault == FaultInstanceIdentity(SUPPLIED_FAULT)


def test_a_source_association_round_trips_through_json() -> None:
    association = _source_association()

    restored = FaultReportSourceObjectAssociation.model_validate_json(
        association.model_dump_json()
    )

    assert restored == association
    assert type(restored.source_object) is NumberedSourceObjectIdentity
    assert type(restored.report) is SuppliedFaultReport


def test_a_source_association_json_payload_has_exactly_two_keys() -> None:
    payload = _payload(_source_association())

    assert list(payload) == list(SOURCE_FIELDS)
    assert payload["source_object"]["kind"] == "issue"
    assert payload["source_object"]["repository_scoped_number"] == RETAINED_ISSUE_NUMBER
    assert payload["report"]["report"] == SUPPLIED_REPORT_TEXT
    assert payload["report"]["context"]["fault"] == SUPPLIED_FAULT_TEXT


def test_a_source_association_refuses_its_own_python_dump() -> None:
    """A Python dump has projected its typed children to plain containers."""
    association = _source_association()

    with pytest.raises(ValidationError) as failure:
        FaultReportSourceObjectAssociation.model_validate(association.model_dump())

    assert _failures(failure.value) == (
        (("report",), "value_error"),
        (("source_object",), "value_error"),
    )


def test_a_source_association_accepts_its_own_typed_instance() -> None:
    association = _source_association()

    assert FaultReportSourceObjectAssociation.model_validate(association) == association


# --- every published source-object kind is admitted ---------------------------

ADMITTED_SOURCE_OBJECTS: tuple[tuple[str, Any], ...] = (
    ("issue", _issue()),
    ("pull_request", _pull_request()),
    (
        "issue_comment",
        _provider_scoped(
            SourceObjectKind.ISSUE_COMMENT,
            SYNTHETIC_ISSUE_COMMENT_GLOBAL_ID,
            _issue(),
        ),
    ),
    (
        "pull_request_comment",
        _provider_scoped(
            SourceObjectKind.PULL_REQUEST_COMMENT,
            SYNTHETIC_PULL_REQUEST_COMMENT_GLOBAL_ID,
        ),
    ),
    ("pull_request_review", _review()),
    (
        "pull_request_review_comment",
        _provider_scoped(
            SourceObjectKind.PULL_REQUEST_REVIEW_COMMENT,
            SYNTHETIC_REVIEW_COMMENT_GLOBAL_ID,
        ),
    ),
    (
        "timeline_event",
        _provider_scoped(
            SourceObjectKind.TIMELINE_EVENT,
            SYNTHETIC_TIMELINE_EVENT_GLOBAL_ID,
            _issue(),
        ),
    ),
)


@pytest.mark.parametrize(
    ("kind", "source_object"),
    tuple(
        pytest.param(kind, value, id=kind) for kind, value in ADMITTED_SOURCE_OBJECTS
    ),
)
def test_every_published_source_object_kind_is_admitted(
    kind: str,
    source_object: NumberedSourceObjectIdentity | ProviderScopedSourceObjectIdentity,
) -> None:
    association = _source_association(source_object=source_object)
    restored = FaultReportSourceObjectAssociation.model_validate_json(
        association.model_dump_json()
    )

    assert association.source_object == source_object
    assert restored == association
    assert type(restored.source_object) is type(source_object)
    assert _payload(association)["source_object"]["kind"] == kind


def test_the_source_object_union_declares_exactly_the_two_admitted_types() -> None:
    """A third admitted identity would widen the relation without a decision."""
    members = _declared_member_names(
        FaultReportSourceObjectAssociation, "source_object"
    )

    assert members == (
        "NumberedSourceObjectIdentity",
        "ProviderScopedSourceObjectIdentity",
    )
    assert len(members) == len(ADMITTED_SOURCE_TYPES)
    assert "RepositoryIdentity" not in members
    for absent in (
        "GitCommitIdentity",
        "GitBlobIdentity",
        "GitRefName",
        "GitRepositoryPath",
        "SourceIdentity",
    ):
        assert absent not in members


def test_the_admitted_kinds_cover_the_whole_published_vocabulary() -> None:
    covered = {kind for kind, _ in ADMITTED_SOURCE_OBJECTS}

    assert covered == {member.value for member in SourceObjectKind}


# --- source-object refusals ---------------------------------------------------


def test_a_bare_repository_identity_is_not_a_source_object() -> None:
    """Repository placement already lives in `report.context.repository`."""
    with pytest.raises(ValidationError) as failure:
        FaultReportSourceObjectAssociation(
            report=_report(),
            source_object=cast(Any, _repository()),
        )

    assert _failures(failure.value) == ((("source_object",), "value_error"),)
    assert "source_object must be a published source object identity" in str(
        failure.value
    )


@pytest.mark.parametrize(
    ("label", "supplied"),
    (
        pytest.param("raw mapping", _issue().model_dump(), id="raw-mapping"),
        pytest.param(
            "typed-children mapping",
            {
                "schema_version": 1,
                "repository_identity": _repository(),
                "kind": SourceObjectKind.ISSUE,
                "repository_scoped_number": RepositoryScopedNumber(
                    RETAINED_ISSUE_NUMBER
                ),
            },
            id="typed-children-mapping",
        ),
        pytest.param(
            "foreign model",
            ForeignNumberedSourceObjectIdentity(
                repository_identity=_repository(),
                kind=SourceObjectKind.ISSUE,
                repository_scoped_number=RepositoryScopedNumber(RETAINED_ISSUE_NUMBER),
            ),
            id="foreign-model",
        ),
        pytest.param("lookalike", SourceObjectLookalike(), id="attribute-lookalike"),
        pytest.param(
            "json text", json.dumps(_issue().model_dump(mode="json")), id="json-text"
        ),
        pytest.param("bare number", RETAINED_ISSUE_NUMBER, id="bare-number"),
        pytest.param(
            "wrong published model",
            _outcome(),
            id="wrong-published-model",
        ),
        pytest.param(
            "this module's other association",
            _history_association(),
            id="sibling-association",
        ),
    ),
)
def test_the_source_object_position_is_closed_to_untyped_python_input(
    label: str,
    supplied: object,
) -> None:
    with pytest.raises(ValidationError) as failure:
        FaultReportSourceObjectAssociation(
            report=_report(), source_object=cast(Any, supplied)
        )

    assert _failures(failure.value) == ((("source_object",), "value_error"),), label


@pytest.mark.parametrize(
    ("label", "supplied"),
    (
        pytest.param("raw mapping", _report().model_dump(), id="raw-mapping"),
        pytest.param("lookalike", ReportLookalike(), id="attribute-lookalike"),
        pytest.param("bare uuid", SUPPLIED_REPORT, id="bare-uuid"),
        pytest.param(
            "report identity", FaultReportIdentity(SUPPLIED_REPORT), id="identity"
        ),
        pytest.param("context", _context(), id="context"),
        pytest.param(
            "foreign association",
            ForeignSourceObjectAssociation(report=_report(), source_object=_issue()),
            id="foreign-association",
        ),
        pytest.param(
            "scenario over the report",
            SuppliedFaultScenario(
                scenario=FaultScenarioIdentity(uuid.UUID(SUPPLIED_SCENARIO_TEXT)),
                report=_report(),
                scenario_statement=SCENARIO_STATEMENT,
            ),
            id="scenario",
        ),
    ),
)
@pytest.mark.parametrize("model", _published_models(), ids=lambda m: m.__name__)
def test_the_report_position_is_closed_to_untyped_python_input(
    model: type[BaseModel],
    label: str,
    supplied: object,
) -> None:
    other: dict[str, Any] = (
        {"source_object": _issue()}
        if model is FaultReportSourceObjectAssociation
        else {"history_fact": _outcome()}
    )

    with pytest.raises(ValidationError) as failure:
        model(report=cast(Any, supplied), **other)

    assert _failures(failure.value) == ((("report",), "value_error"),), label
    assert "report must be a SuppliedFaultReport in Python input" in str(failure.value)


@pytest.mark.parametrize(
    ("label", "supplied"),
    (
        pytest.param(
            "repository identity",
            _repository().model_dump(mode="json"),
            id="repository-identity",
        ),
        pytest.param(
            "commit identity",
            _commit().model_dump(mode="json"),
            id="commit-identity",
        ),
        pytest.param("report", _report().model_dump(mode="json"), id="report"),
        pytest.param("bare string", RETAINED_ISSUE_NUMBER, id="bare-string"),
    ),
)
def test_the_source_object_position_refuses_an_unadmitted_json_payload(
    label: str,
    supplied: object,
) -> None:
    """The Python guards do not run in JSON mode, so the union itself must hold.

    A member added to the declared union would be admitted here even while the
    Python-mode guard still refused it, which is exactly how a widened boundary
    would escape a Python-only refusal test.
    """
    payload = _payload(_source_association())
    payload["source_object"] = supplied

    with pytest.raises(ValidationError) as failure:
        FaultReportSourceObjectAssociation.model_validate_json(json.dumps(payload))

    assert {path[0] for path, _ in _failures(failure.value)} == {"source_object"}, label


@pytest.mark.parametrize(
    ("label", "supplied"),
    (
        pytest.param(
            "change set", _change_set().model_dump(mode="json"), id="change-set"
        ),
        pytest.param(
            "evidence link",
            _evidence_link().model_dump(mode="json"),
            id="evidence-link",
        ),
        pytest.param(
            "changed path status",
            ChangedPathStatus.ADDED.value,
            id="changed-path-status",
        ),
        pytest.param(
            "source object", _pull_request().model_dump(mode="json"), id="source-object"
        ),
    ),
)
def test_the_history_fact_position_refuses_an_unadmitted_json_payload(
    label: str,
    supplied: object,
) -> None:
    """The three exclusions must hold in JSON, not only in Python input."""
    payload = _payload(_history_association())
    payload["history_fact"] = supplied

    with pytest.raises(ValidationError) as failure:
        FaultReportHistoryFactAssociation.model_validate_json(json.dumps(payload))

    assert {path[0] for path, _ in _failures(failure.value)} == {"history_fact"}, label


@pytest.mark.parametrize("from_attributes", (True, False), ids=("attrs", "no-attrs"))
def test_a_top_level_mapping_still_guards_each_child(from_attributes: bool) -> None:
    with pytest.raises(ValidationError) as failure:
        FaultReportSourceObjectAssociation.model_validate(
            {"report": _report(), "source_object": _issue().model_dump()},
            from_attributes=from_attributes,
        )

    assert _failures(failure.value) == ((("source_object",), "value_error"),)


@pytest.mark.parametrize("from_attributes", (True, False), ids=("attrs", "no-attrs"))
def test_a_top_level_mapping_of_typed_children_is_admitted(
    from_attributes: bool,
) -> None:
    association = FaultReportSourceObjectAssociation.model_validate(
        _typed_source_mapping(), from_attributes=from_attributes
    )

    assert association == _source_association()


@pytest.mark.parametrize("from_attributes", (True, False), ids=("attrs", "no-attrs"))
def test_a_top_level_history_mapping_still_guards_each_child(
    from_attributes: bool,
) -> None:
    admitted = FaultReportHistoryFactAssociation.model_validate(
        _typed_history_mapping(), from_attributes=from_attributes
    )
    assert admitted == _history_association()

    with pytest.raises(ValidationError) as failure:
        FaultReportHistoryFactAssociation.model_validate(
            _typed_history_mapping(history_fact=_outcome().model_dump()),
            from_attributes=from_attributes,
        )

    assert {path for path, _ in _failures(failure.value)} == {("history_fact",)}


def test_a_lookalike_association_is_refused_even_with_from_attributes() -> None:
    class AssociationLookalike:
        def __init__(self) -> None:
            self.report = _report()
            self.source_object = SourceObjectLookalike()

    with pytest.raises(ValidationError) as failure:
        FaultReportSourceObjectAssociation.model_validate(
            AssociationLookalike(), from_attributes=True
        )

    assert _failures(failure.value) == ((("source_object",), "value_error"),)


# --- omission, extras and malformed reentry -----------------------------------


@pytest.mark.parametrize(
    ("model", "omitted", "supplied"),
    (
        pytest.param(
            FaultReportSourceObjectAssociation,
            "source_object",
            {"report": _report()},
            id="source-object-omitted",
        ),
        pytest.param(
            FaultReportSourceObjectAssociation,
            "report",
            {"source_object": _issue()},
            id="source-report-omitted",
        ),
        pytest.param(
            FaultReportHistoryFactAssociation,
            "history_fact",
            {"report": _report()},
            id="history-fact-omitted",
        ),
        pytest.param(
            FaultReportHistoryFactAssociation,
            "report",
            {"history_fact": _outcome()},
            id="history-report-omitted",
        ),
    ),
)
def test_a_true_omission_fails_at_its_own_position(
    model: type[BaseModel],
    omitted: str,
    supplied: dict[str, Any],
) -> None:
    with pytest.raises(ValidationError) as failure:
        model(**supplied)

    assert _failures(failure.value) == (((omitted,), "missing"),)


@pytest.mark.parametrize("extra", REFUSED_EXTRA_KEYS)
def test_an_extra_key_is_refused_in_python_input(extra: str) -> None:
    with pytest.raises(ValidationError) as failure:
        FaultReportSourceObjectAssociation(
            **_typed_source_mapping(**{extra: "supplied"})
        )

    assert _failures(failure.value) == (((extra,), "extra_forbidden"),)


@pytest.mark.parametrize("extra", REFUSED_EXTRA_KEYS)
def test_an_extra_key_is_refused_in_json_input(extra: str) -> None:
    payload = _payload(_source_association())
    payload[extra] = "supplied"

    with pytest.raises(ValidationError) as failure:
        FaultReportSourceObjectAssociation.model_validate_json(json.dumps(payload))

    assert _failures(failure.value) == (((extra,), "extra_forbidden"),)


def test_an_extra_key_inside_the_source_object_is_refused_in_json() -> None:
    payload = _payload(_source_association())
    payload["source_object"]["role"] = "primary"

    with pytest.raises(ValidationError) as failure:
        FaultReportSourceObjectAssociation.model_validate_json(json.dumps(payload))

    assert (("source_object", "role"), "extra_forbidden") in _failures(failure.value)


def test_an_extra_key_inside_the_report_is_refused_in_json() -> None:
    payload = _payload(_source_association())
    payload["report"]["confidence"] = "high"

    with pytest.raises(ValidationError) as failure:
        FaultReportSourceObjectAssociation.model_validate_json(json.dumps(payload))

    assert _failures(failure.value) == ((("report", "confidence"), "extra_forbidden"),)


def _corrupt_scoped_number(payload: dict[str, Any]) -> None:
    payload["source_object"]["repository_scoped_number"] = "0"


def _corrupt_source_kind(payload: dict[str, Any]) -> None:
    payload["source_object"]["kind"] = "commit"


def _corrupt_problem_statement(payload: dict[str, Any]) -> None:
    payload["report"]["problem_statement"] = " padded "


def _corrupt_fault_identity(payload: dict[str, Any]) -> None:
    payload["report"]["context"]["fault"] = "not-a-uuid"


@pytest.mark.parametrize(
    ("mutate", "expected"),
    (
        pytest.param(
            _corrupt_scoped_number,
            ("source_object", "repository_scoped_number"),
            id="non-canonical-number",
        ),
        pytest.param(
            _corrupt_source_kind,
            ("source_object", "kind"),
            id="unknown-kind",
        ),
        pytest.param(
            _corrupt_problem_statement,
            ("report", "problem_statement"),
            id="padded-problem-statement",
        ),
        pytest.param(
            _corrupt_fault_identity,
            ("report", "context", "fault"),
            id="malformed-fault-identity",
        ),
    ),
)
def test_a_malformed_json_reentry_fails_at_the_relevant_path(
    mutate: Callable[[dict[str, Any]], None],
    expected: tuple[str, ...],
) -> None:
    payload = _payload(_source_association())
    mutate(payload)

    with pytest.raises(ValidationError) as failure:
        FaultReportSourceObjectAssociation.model_validate_json(json.dumps(payload))

    assert expected in _paths(failure.value)


# --- subclass normalization ---------------------------------------------------


def test_a_no_added_field_child_subclass_is_admitted_and_base_normalized() -> None:
    """The promise is the normalized value, not preservation of the subclass."""
    association = FaultReportSourceObjectAssociation(
        report=UnextendedSuppliedFaultReport(
            report=FaultReportIdentity(SUPPLIED_REPORT),
            context=_context(),
            problem_statement=PROBLEM_STATEMENT,
            behavioral_deviation=BEHAVIORAL_DEVIATION,
        ),
        source_object=UnextendedNumberedSourceObjectIdentity(
            repository_identity=_repository(),
            kind=SourceObjectKind.ISSUE,
            repository_scoped_number=RepositoryScopedNumber(RETAINED_ISSUE_NUMBER),
        ),
    )
    history = FaultReportHistoryFactAssociation(
        report=_report(),
        history_fact=UnextendedMergeRevisionOutcome(
            pull_request=_pull_request(),
            merge_revision=_commit(RETAINED_MERGE_REVISION),
        ),
    )

    assert association == _source_association()
    assert type(association.report) is SuppliedFaultReport
    assert type(association.source_object) is NumberedSourceObjectIdentity
    assert history == _history_association()
    assert type(history.history_fact) is PullRequestMergeRevisionOutcome


def test_a_child_subclass_extra_field_remains_refused() -> None:
    supplied = ExtendedSuppliedFaultReport(
        report=FaultReportIdentity(SUPPLIED_REPORT),
        context=_context(),
        problem_statement=PROBLEM_STATEMENT,
        behavioral_deviation=BEHAVIORAL_DEVIATION,
        note="supplied",
    )

    with pytest.raises(ValidationError) as failure:
        FaultReportSourceObjectAssociation(report=supplied, source_object=_issue())

    assert _failures(failure.value) == ((("report", "note"), "extra_forbidden"),)


# --- repository coherence is not inferred -------------------------------------


def test_a_cross_repository_source_association_is_admitted() -> None:
    """Analysis context and associated material may live in two repositories."""
    association = _source_association(source_object=_issue(OTHER_REPOSITORY_ID))

    numbered = association.source_object
    assert isinstance(numbered, NumberedSourceObjectIdentity)
    assert association.report.context.repository == _repository()
    assert numbered.repository_identity == _repository(OTHER_REPOSITORY_ID)
    assert association.report.context.repository != _repository(OTHER_REPOSITORY_ID)
    assert (
        FaultReportSourceObjectAssociation.model_validate_json(
            association.model_dump_json()
        )
        == association
    )


def test_a_cross_repository_association_infers_no_second_placement() -> None:
    association = _source_association(source_object=_issue(OTHER_REPOSITORY_ID))
    payload = _payload(association)

    # The report keeps exactly the one repository context it was given, and the
    # association adds no affected, origin, owning or applicable repository.
    assert payload["report"]["context"]["repository"]["provider_repository_id"] == (
        RETAINED_REPOSITORY_ID
    )
    assert list(payload) == list(SOURCE_FIELDS)
    for name in ("affected_repository", "origin_repository", "owner", "applies_to"):
        assert name not in payload


# --- multiplicity, absence and equality ---------------------------------------


def test_one_report_may_carry_several_independent_source_associations() -> None:
    report = _report()
    associations = tuple(
        _source_association(report=report, source_object=source_object)
        for _, source_object in ADMITTED_SOURCE_OBJECTS
    )

    assert _distinct_value_count(
        *(association.source_object for association in associations)
    ) == len(ADMITTED_SOURCE_OBJECTS)
    assert all(association.report == report for association in associations)


def test_one_source_object_may_carry_reports_for_two_distinct_faults() -> None:
    """Sharing one Issue merges nothing: the two fault subjects stay two."""
    issue = _issue()
    first = _source_association(report=_report(), source_object=issue)
    second = _source_association(report=_second_report(), source_object=issue)

    assert first != second
    assert first.source_object == second.source_object
    assert first.report.context.fault != second.report.context.fault
    assert first.report.context.fault == FaultInstanceIdentity(SUPPLIED_FAULT)
    assert second.report.context.fault == FaultInstanceIdentity(SECOND_FAULT)
    assert (
        _distinct_value_count(first.report.context.fault, second.report.context.fault)
        == 2
    )


def test_one_report_may_carry_every_admitted_history_fact_independently() -> None:
    report = _report()
    facts: tuple[Any, ...] = (
        _binding(),
        _changed_path(),
        _approval(),
        _outcome(),
        _deletion(),
        _occurrence_time(),
    )
    associations = tuple(
        _history_association(report=report, history_fact=fact) for fact in facts
    )

    assert len(associations) == len(ADMITTED_FACT_TYPES)
    assert {type(a.history_fact) for a in associations} == set(ADMITTED_FACT_TYPES)
    assert all(a.report == report for a in associations)


def test_equal_associations_are_equal_and_hash_equally() -> None:
    first = _source_association()
    second = _source_association()
    history_first = _history_association()
    history_second = _history_association()

    assert first == second
    assert hash(first) == hash(second)
    assert history_first == history_second
    assert hash(history_first) == hash(history_second)
    assert _distinct_value_count(first, second, history_first, history_second) == 2


def test_neither_association_overrides_equality_hashing_or_ordering() -> None:
    """Equality is ordinary Pydantic model equality; nothing here redefines it.

    A frozen model's `__hash__` is generated by Pydantic itself, so the claim is
    about what this module declares, which is why the source is inspected rather
    than the runtime class dictionary.
    """
    declared = {
        item.name
        for node in ast.walk(_relationship_tree())
        if isinstance(node, ast.ClassDef)
        for item in node.body
        if isinstance(item, ast.FunctionDef)
    }

    assert not declared & {
        "__eq__",
        "__ne__",
        "__hash__",
        "__lt__",
        "__gt__",
        "__le__",
        "__ge__",
    }
    for model in _published_models():
        assert model.__eq__ is BaseModel.__eq__
        # A class-body assignment is not a `def`, so the runtime hash is
        # checked as well as the source: it must still be Pydantic's own.
        assert model.__hash__ is not None
        assert model.__hash__.__qualname__ == "make_hash_func.<locals>.hash_func"

    # No ordering exists to be relied on, so comparison stays a type error.
    first = cast(Any, _source_association())
    second = cast(Any, _source_association(source_object=_pull_request()))
    comparisons: tuple[Callable[[], object], ...] = (
        lambda: first < second,
        lambda: first > second,
        lambda: first <= second,
        lambda: first >= second,
    )
    for compare in comparisons:
        with pytest.raises(TypeError):
            compare()


def test_two_associations_of_different_declared_types_are_never_equal() -> None:
    assert _source_association() != _history_association()
    assert _history_association() != _source_association()


def test_a_report_alone_needs_no_association_and_declares_none() -> None:
    """Absence is expressed by holding no association, not by a field."""
    report = _report()

    assert "source_object" not in SuppliedFaultReport.model_fields
    assert "history_fact" not in SuppliedFaultReport.model_fields
    assert tuple(SuppliedFaultReport.model_fields) == (
        "report",
        "context",
        "problem_statement",
        "behavioral_deviation",
    )
    assert SuppliedFaultReport.model_validate_json(report.model_dump_json()) == report


def test_no_absence_sentinel_state_or_optional_position_is_published() -> None:
    """A missing association is not `unknown`, `unavailable` or `disproved`."""
    for model in _published_models():
        for name, field in model.model_fields.items():
            assert field.is_required(), (model.__name__, name)

    # No position may admit `None`, which a nullable annotation would allow
    # through JSON while `is_required()` still reported True.
    for model in _published_models():
        for name in model.model_fields:
            assert "NoneType" not in _declared_member_names(model, name), (
                model.__name__,
                name,
            )

    body = _module_body()
    for absent in (
        "unknown",
        "unavailable",
        "disproved",
        "absent",
        "None = ",
        "| None",
        "Optional",
    ):
        assert absent not in body, absent


# --- history-fact association: every admitted member --------------------------

ADMITTED_FACT_CASES: tuple[tuple[str, Any, type[BaseModel]], ...] = (
    ("revision_role_binding", _binding(), PullRequestRevisionRoleBinding),
    ("changed_path", _changed_path(), PullRequestChangedPath),
    ("review_revision_approval", _approval(), PullRequestReviewRevisionApproval),
    ("merge_revision_outcome", _outcome(), PullRequestMergeRevisionOutcome),
    ("head_ref_deletion", _deletion(), PullRequestHeadRefDeletion),
    (
        "historical_occurrence_time",
        _occurrence_time(),
        PullRequestHistoricalOccurrenceTime,
    ),
)


@pytest.mark.parametrize(
    ("label", "fact", "declared"),
    tuple(pytest.param(*case, id=case[0]) for case in ADMITTED_FACT_CASES),
)
def test_every_admitted_history_fact_is_accepted_and_preserved(
    label: str,
    fact: BaseModel,
    declared: type[BaseModel],
) -> None:
    association = _history_association(history_fact=fact)
    restored = FaultReportHistoryFactAssociation.model_validate_json(
        association.model_dump_json()
    )

    assert association.history_fact == fact
    assert type(association.history_fact) is declared
    assert restored == association
    assert type(restored.history_fact) is declared
    assert restored.history_fact == fact
    assert list(_payload(association)) == list(HISTORY_FIELDS)


def test_the_admitted_fact_set_is_exactly_the_published_evidence_link_set() -> None:
    """The `S1.P05.S07` fact boundary is reused, not restated or widened."""
    admitted = {declared for _, _, declared in ADMITTED_FACT_CASES}

    assert admitted == set(ADMITTED_FACT_TYPES)
    assert len(admitted) == 6

    link_members = _declared_member_names(PullRequestHistoryFactEvidenceLink, "fact")
    association_members = _declared_member_names(
        FaultReportHistoryFactAssociation, "history_fact"
    )

    assert association_members == link_members
    assert association_members == tuple(model.__name__ for model in ADMITTED_FACT_TYPES)
    assert len(association_members) == 6


def test_the_occurrence_time_member_keeps_the_published_instant_grammar() -> None:
    for instant in (
        RETAINED_MERGE_INSTANT,
        RETAINED_APPROVAL_INSTANT,
        RETAINED_DELETION_INSTANT,
    ):
        occurrence = _occurrence_time(instant=instant)
        association = _history_association(history_fact=occurrence)
        restored = FaultReportHistoryFactAssociation.model_validate_json(
            association.model_dump_json()
        )
        embedded = cast(PullRequestHistoricalOccurrenceTime, restored.history_fact)

        assert embedded.occurred_at == _instant(instant)
        assert embedded.occurred_at.tzinfo is UTC
        assert restored == association


@pytest.mark.parametrize(
    "lexeme",
    (
        "2018-11-18T00:17:25+01:00",
        "2018-11-18T00:17:25",
        "2018-W46-7T00:17:25Z",
        "20181118T001725Z",
        "not-an-instant",
    ),
)
def test_a_refused_instant_lexeme_stays_refused_through_the_association(
    lexeme: str,
) -> None:
    payload = _payload(_history_association(history_fact=_occurrence_time()))
    payload["history_fact"]["occurred_at"] = lexeme

    with pytest.raises(ValidationError):
        FaultReportHistoryFactAssociation.model_validate_json(json.dumps(payload))


# Lexical forms spanning the published aware-instant grammar, the forms a
# stdlib ISO parser would decide differently, and plain malformations. Three
# hardcoded verdicts cannot show that the transport decode neither widens nor
# narrows the embedded fact, so the corpus is decided differentially instead.
INSTANT_GRAMMAR_CASES = (
    "2018-11-18T00:17:25Z",
    "2018-11-18T00:17:25+00:00",
    "2018-11-18T00:17:25-00:00",
    "2018-11-18T00:17:25.5Z",
    "2018-11-18T00:17:25.123456Z",
    "2018-11-18T00:17:25.123456789Z",
    "2018-11-18 00:17:25Z",
    "2018-11-18t00:17:25Z",
    "2018-11-18T00:17:25z",
    "2018-W46-7T00:17:25Z",
    "20181118T001725Z",
    "20181118",
    "2018-11-18T00:17:25",
    "2018-11-18T00:17:25+01:00",
    "2018-11-17T23:17:25-01:00",
    "2018-11-18",
    "00:17:25Z",
    "",
    "not-an-instant",
    "2018-13-01T00:00:00Z",
    "2018-11-18T25:17:25Z",
    "2018-11-18T24:00:00Z",
    "  2018-11-18T00:17:25Z  ",
    "2018-11-18T00:17:25Z ",
    " 2018-11-18T00:17:25Z",
    "+2018-11-18T00:17:25Z",
    "1542500245",
    "1542500245.0",
    "2018-11-18T00:17:25,5Z",
    "2018-11-18T00:17:25 GMT",
)


def _occurrence_payloads(lexeme: str) -> tuple[str, str, str]:
    """The same supplied fact, as the fact, the S04 relation, and the P05 link."""
    association = _payload(_history_association(history_fact=_occurrence_time()))
    association["history_fact"]["occurred_at"] = lexeme
    link = _payload(_evidence_link())
    link["fact"] = association["history_fact"]
    return (
        json.dumps(association["history_fact"]),
        json.dumps(association),
        json.dumps(link),
    )


@pytest.mark.parametrize("lexeme", INSTANT_GRAMMAR_CASES)
def test_the_association_and_the_fact_decide_the_same_instant_grammar(
    lexeme: str,
) -> None:
    """The transport decode may neither widen nor narrow the embedded grammar.

    A stdlib ISO parser diverges in both directions here, and so would trimming
    whitespace, rejecting digit strings, or refusing a space separator before
    decoding, so the verdicts are compared rather than hardcoded. The published
    `S1.P05.S07` link is compared too: it restates the same grammar, and a
    silent drift in either direction would show as a three-way disagreement.
    """
    fact_json, association_json, link_json = _occurrence_payloads(lexeme)

    by_fact = _accepts(
        lambda: PullRequestHistoricalOccurrenceTime.model_validate_json(fact_json)
    )
    by_association = _accepts(
        lambda: FaultReportHistoryFactAssociation.model_validate_json(association_json)
    )
    by_link = _accepts(
        lambda: PullRequestHistoryFactEvidenceLink.model_validate_json(link_json)
    )

    assert by_association == by_fact, lexeme
    assert by_association == by_link, lexeme
    if by_fact:
        fact = PullRequestHistoricalOccurrenceTime.model_validate_json(fact_json)
        through = FaultReportHistoryFactAssociation.model_validate_json(
            association_json
        )
        assert through.history_fact == fact
        assert (
            cast(PullRequestHistoricalOccurrenceTime, through.history_fact).occurred_at
            == fact.occurred_at
        )


def test_the_lowercase_zone_designator_is_actually_admitted() -> None:
    """The differential above passes if both sides refuse; this pins the verdict."""
    fact_json, association_json, _ = _occurrence_payloads(
        RETAINED_MERGE_INSTANT.replace("Z", "z")
    )

    assert _accepts(
        lambda: PullRequestHistoricalOccurrenceTime.model_validate_json(fact_json)
    )
    assert _accepts(
        lambda: FaultReportHistoryFactAssociation.model_validate_json(association_json)
    )


def _add_fact_level_key(fact: dict[str, Any]) -> None:
    fact["confidence"] = "high"


def _add_occurrence_key(fact: dict[str, Any]) -> None:
    fact["occurrence"]["repair"] = True


def _uppercase_merge_digest(fact: dict[str, Any]) -> None:
    fact["occurrence"]["merge_revision"]["full_digest"] = (
        RETAINED_MERGE_REVISION.upper()
    )


def _drop_instant(fact: dict[str, Any]) -> None:
    del fact["occurred_at"]


def _numeric_instant(fact: dict[str, Any]) -> None:
    fact["occurred_at"] = 1542500245


def _wrong_nested_kind(fact: dict[str, Any]) -> None:
    fact["occurrence"]["pull_request"]["kind"] = "issue"


@pytest.mark.parametrize(
    ("label", "mutate"),
    (
        pytest.param(
            "extra key at fact level", _add_fact_level_key, id="extra-fact-key"
        ),
        pytest.param(
            "extra key inside the occurrence",
            _add_occurrence_key,
            id="extra-occurrence-key",
        ),
        pytest.param(
            "uppercase merge digest", _uppercase_merge_digest, id="uppercase-digest"
        ),
        pytest.param("missing instant", _drop_instant, id="missing-instant"),
        pytest.param("numeric instant", _numeric_instant, id="numeric-instant"),
        pytest.param("wrong nested kind", _wrong_nested_kind, id="wrong-nested-kind"),
    ),
)
def test_the_transport_decode_reads_no_field_but_the_instant(
    label: str,
    mutate: Callable[[dict[str, Any]], None],
) -> None:
    """Every other field must be decided exactly as the published fact decides it.

    The decode touches one leaf. A helper that whitelisted keys, rewrote a
    digest, or dropped a child would make the association accept a fact the
    published model refuses while every instant lexeme still agreed.
    """
    association = _payload(_history_association(history_fact=_occurrence_time()))
    mutate(association["history_fact"])
    fact_json = json.dumps(association["history_fact"])

    by_fact = _accepts(
        lambda: PullRequestHistoricalOccurrenceTime.model_validate_json(fact_json)
    )
    by_association = _accepts(
        lambda: FaultReportHistoryFactAssociation.model_validate_json(
            json.dumps(association)
        )
    )

    assert by_fact is False, label
    assert by_association == by_fact, label


def _corrupt_merge_revision(payload: dict[str, Any]) -> None:
    payload["history_fact"]["merge_revision"]["full_digest"] = "not-a-digest"


def _corrupt_fact_pull_request_kind(payload: dict[str, Any]) -> None:
    payload["history_fact"]["pull_request"]["kind"] = "issue"


def _corrupt_fact_scoped_number(payload: dict[str, Any]) -> None:
    payload["history_fact"]["pull_request"]["repository_scoped_number"] = "04414"


@pytest.mark.parametrize(
    ("label", "mutate", "expected"),
    (
        pytest.param(
            "merge revision",
            _corrupt_merge_revision,
            ("history_fact", "merge_revision"),
            id="merge-revision",
        ),
        pytest.param(
            "pull request kind",
            _corrupt_fact_pull_request_kind,
            ("history_fact",),
            id="pull-request-kind",
        ),
        pytest.param(
            "scoped number",
            _corrupt_fact_scoped_number,
            ("history_fact", "pull_request", "repository_scoped_number"),
            id="scoped-number",
        ),
    ),
)
def test_a_malformed_nested_history_value_fails_at_the_relevant_path(
    label: str,
    mutate: Callable[[dict[str, Any]], None],
    expected: tuple[str, ...],
) -> None:
    payload = _payload(_history_association())
    mutate(payload)

    with pytest.raises(ValidationError) as failure:
        FaultReportHistoryFactAssociation.model_validate_json(json.dumps(payload))

    assert expected in _paths(failure.value), label


# --- the three explicit exclusions --------------------------------------------


def test_a_changed_path_status_is_not_a_fact_and_is_refused() -> None:
    """A closed vocabulary is not something a report can be associated with."""
    with pytest.raises(ValidationError) as failure:
        FaultReportHistoryFactAssociation(
            report=_report(), history_fact=cast(Any, ChangedPathStatus.ADDED)
        )

    assert {path for path, _ in _failures(failure.value)} == {("history_fact",)}
    assert "history_fact must be a published pull request history fact" in str(
        failure.value
    )


def test_a_change_set_stays_outside_the_published_fact_boundary() -> None:
    """Its composition and order are caller-composed, so S04 does not move it."""
    with pytest.raises(ValidationError) as failure:
        FaultReportHistoryFactAssociation(
            report=_report(), history_fact=cast(Any, _change_set())
        )

    assert {path for path, _ in _failures(failure.value)} == {("history_fact",)}
    assert PullRequestChangeSet.__name__ in (relationship_module.__doc__ or "")


def test_the_p05_evidence_link_is_not_admitted_as_a_history_fact() -> None:
    """Nesting the evidence association would blur what it means."""
    with pytest.raises(ValidationError) as failure:
        FaultReportHistoryFactAssociation(
            report=_report(), history_fact=cast(Any, _evidence_link())
        )

    assert {path for path, _ in _failures(failure.value)} == {("history_fact",)}


def test_the_excluded_set_is_derived_from_the_published_history_surface() -> None:
    admitted = {model.__name__ for model in ADMITTED_FACT_TYPES}
    excluded = tuple(name for name in history_module.__all__ if name not in admitted)

    assert excluded == ("ChangedPathStatus", "PullRequestChangeSet")
    assert set(admitted) < set(history_module.__all__)
    assert PullRequestHistoryFactEvidenceLink.__name__ not in history_module.__all__


@pytest.mark.parametrize(
    ("label", "supplied"),
    (
        pytest.param("raw mapping", _outcome().model_dump(), id="raw-mapping"),
        pytest.param("lookalike", HistoryFactLookalike(), id="attribute-lookalike"),
        pytest.param(
            "json text",
            json.dumps(_outcome().model_dump(mode="json")),
            id="json-text",
        ),
        pytest.param("source object", _pull_request(), id="source-object"),
        pytest.param("report", _report(), id="report"),
        pytest.param(
            "sibling association", _source_association(), id="sibling-association"
        ),
    ),
)
def test_the_history_fact_position_is_closed_to_untyped_python_input(
    label: str,
    supplied: object,
) -> None:
    with pytest.raises(ValidationError) as failure:
        FaultReportHistoryFactAssociation(
            report=_report(), history_fact=cast(Any, supplied)
        )

    assert {path for path, _ in _failures(failure.value)} == {("history_fact",)}, label


# --- the epistemic boundary ---------------------------------------------------


def test_an_approval_association_creates_no_confidence_or_review_state() -> None:
    association = _history_association(history_fact=_approval())
    payload = _payload(association)

    assert list(payload) == list(HISTORY_FIELDS)
    for name in ("confidence", "review_state", "approved", "certainty", "strength"):
        assert name not in payload
        assert name not in payload["history_fact"]
    assert set(payload["history_fact"]) == {"review", "approved_revision"}


def test_a_merge_association_creates_no_repair_or_fix_semantics() -> None:
    association = _history_association(history_fact=_outcome())
    payload = _payload(association)

    for name in ("repair", "fix", "fixed", "fixes", "verified", "resolved"):
        assert name not in payload
        assert name not in payload["history_fact"]
    assert set(payload["history_fact"]) == {"pull_request", "merge_revision"}


def test_a_changed_path_association_creates_no_affected_path_semantics() -> None:
    association = _history_association(history_fact=_changed_path())
    payload = _payload(association)

    assert set(payload["history_fact"]) == {"path", "head_object", "status"}
    assert payload["history_fact"]["status"] == "added"
    for name in ("affected_path", "affected", "fault_path", "culprit"):
        assert name not in payload
        assert name not in payload["history_fact"]


def test_a_source_occurrence_instant_is_not_a_fault_occurrence_time() -> None:
    """The P05 instant stays a source instant for a published history fact."""
    association = _history_association(history_fact=_occurrence_time())
    payload = _payload(association)

    assert payload["history_fact"]["occurred_at"] == RETAINED_MERGE_INSTANT
    for name in (
        "occurred_at",
        "observed_at",
        "reported_at",
        "reproduced_at",
        "started_at",
        "ended_at",
    ):
        assert name not in payload
        assert name not in payload["report"]

    # The published fault-occurrence record still carries no time of its own,
    # and this association copies none into it.
    occurrence = SuppliedFaultOccurrenceContext(
        occurrence=FaultOccurrenceIdentity(uuid.UUID(SUPPLIED_OCCURRENCE_TEXT)),
        scenario=SuppliedFaultScenario(
            scenario=FaultScenarioIdentity(uuid.UUID(SUPPLIED_SCENARIO_TEXT)),
            report=_report(),
            scenario_statement=SCENARIO_STATEMENT,
        ),
        occurrence_context=OCCURRENCE_CONTEXT,
    )
    assert tuple(SuppliedFaultOccurrenceContext.model_fields) == (
        "occurrence",
        "scenario",
        "occurrence_context",
    )
    assert "occurred_at" not in _payload(occurrence)


def test_no_association_carries_an_evidence_record_or_link() -> None:
    for model in _published_models():
        assert "evidence_record" not in model.model_fields
        assert "evidence" not in model.model_fields

    payload = _payload(_history_association())
    assert "evidence_record" not in payload
    assert "evidence_record" not in payload["history_fact"]
    assert "evidence_record" in PullRequestHistoryFactEvidenceLink.model_fields


def test_no_association_carries_a_support_strength_or_status_field() -> None:
    for model in _published_models():
        for name in ("support", "support_role", "strength", "status", "confidence"):
            assert name not in model.model_fields, (model.__name__, name)


# --- relationship counterexamples ---------------------------------------------


def test_two_source_associations_do_not_create_an_issue_to_pull_request_pair() -> None:
    """Sharing one report is not a transitivity rule over source objects."""
    report = _report()
    to_issue = _source_association(report=report, source_object=_issue())
    to_pull_request = _source_association(report=report, source_object=_pull_request())

    assert to_issue != to_pull_request
    assert to_issue.source_object != to_pull_request.source_object
    # Neither value can reach the other's source object by any published path.
    assert set(_payload(to_issue)["source_object"]) == {
        "schema_version",
        "repository_identity",
        "kind",
        "repository_scoped_number",
    }
    assert RETAINED_PULL_REQUEST_NUMBER not in json.dumps(_payload(to_issue))
    assert RETAINED_ISSUE_NUMBER not in json.dumps(_payload(to_pull_request))


def test_neither_association_declares_a_second_source_object_position() -> None:
    """Neither S04 model declares two source-object positions.

    This is a claim about what this Slice declares, not a global one: the
    published `S1.P01` `ProviderScopedSourceObjectIdentity` already carries its
    own `parent` numbered object, so a review admitted at `source_object`
    reaches the pull request containing it. That containment is predecessor
    semantics this module neither creates nor extends.
    """
    for model in _published_models():
        admitted = {declared.__name__ for declared in ADMITTED_SOURCE_TYPES}
        source_positions = [
            name
            for name in model.model_fields
            if set(_declared_member_names(model, name)) & admitted
        ]
        assert len(source_positions) <= 1, (model.__name__, source_positions)


def test_the_module_publishes_no_generic_relationship_vocabulary() -> None:
    published = {
        node.name
        for node in ast.walk(_relationship_tree())
        if isinstance(node, ast.ClassDef)
    }

    assert published == set(EXPECTED_EXPORTS)
    for absent in (
        "RelationshipKind",
        "RelationshipType",
        "Relationship",
        "RelationTriple",
        "GraphNode",
        "GraphEdge",
        "SourceObjectRelation",
        "IssuePullRequestPairing",
    ):
        assert absent not in published
        assert not hasattr(relationship_module, absent)


def test_a_merge_association_is_not_a_verified_repair() -> None:
    association = _history_association(history_fact=_outcome())

    # The value says the caller associated a report with a merge outcome. It
    # says nothing about the fault's state, and no field can be read to say so.
    assert set(association.model_fields_set) == {"report", "history_fact"}
    assert association.report.problem_statement == PROBLEM_STATEMENT
    assert "repair" not in _payload(association)
    assert _history_association(history_fact=_outcome()) == association
    # Two reports may be associated with the same merge outcome; that does not
    # make one of them repaired and the other not.
    other = _history_association(report=_second_report(), history_fact=_outcome())
    assert other != association
    assert other.history_fact == association.history_fact


def test_an_approval_association_is_not_faultatlas_confidence() -> None:
    association = _history_association(history_fact=_approval())
    approval = cast(PullRequestReviewRevisionApproval, association.history_fact)

    assert approval.review.kind is SourceObjectKind.PULL_REQUEST_REVIEW
    assert approval.approved_revision == _commit()
    assert not hasattr(association, "confidence")
    assert "confidence" not in _payload(association)


def test_a_history_association_creates_no_p05_evidence_link() -> None:
    association = _history_association()
    link = _evidence_link()

    assert not isinstance(association, PullRequestHistoryFactEvidenceLink)
    assert association.history_fact == link.fact
    assert tuple(FaultReportHistoryFactAssociation.model_fields) != tuple(
        PullRequestHistoryFactEvidenceLink.model_fields
    )
    assert "evidence_record" not in _payload(association)
    assert "evidence_record" in _payload(link)


def _walk_annotation(annotation: object) -> tuple[object, ...]:
    """Every leaf of an annotation, descending generic arguments as well.

    `_annotation_members` deliberately stops at a container so that an
    unresolved member fails an exactness witness. Reachability is the opposite
    question, so a `tuple[Model, ...]` position must be entered rather than
    dropped, or a whole branch of the graph would go unwalked.
    """
    members = _annotation_members(annotation)
    leaves: list[object] = []
    for member in members:
        arguments = typing.get_args(member)
        if arguments and not isinstance(member, type):
            for argument in arguments:
                leaves.extend(_walk_annotation(argument))
        else:
            leaves.append(member)
    return tuple(leaves)


def _reachable_models(root: type[BaseModel]) -> set[type[BaseModel]]:
    """Every published model reachable from one root through declared fields."""
    seen: set[type[BaseModel]] = set()
    pending = [root]
    while pending:
        model = pending.pop()
        if model in seen:
            continue
        seen.add(model)
        for name in model.model_fields:
            for member in _walk_annotation(model.model_fields[name].annotation):
                if isinstance(member, type) and issubclass(member, BaseModel):
                    pending.append(member)
    return seen


def test_neither_association_reaches_the_evidence_layer_through_any_field() -> None:
    """The import scan alone would not establish reach, so the graph is walked."""
    reachable: set[type[BaseModel]] = set()
    for model in _published_models():
        reachable |= _reachable_models(model)

    modules = {model.__module__ for model in reachable}

    assert "faultatlas.domain.evidence" not in modules
    assert "faultatlas.domain.history_evidence_link" not in modules
    assert modules == {
        "faultatlas.domain.fault",
        "faultatlas.domain.fault_source_relationship",
        "faultatlas.domain.history",
        "faultatlas.domain.identity",
        "faultatlas.domain.revision",
    }
    assert DurableEvidenceRecordReference not in reachable
    assert PullRequestHistoryFactEvidenceLink not in reachable
    for model in reachable:
        for name in model.model_fields:
            assert "evidence" not in name, (model.__name__, name)
            assert "support" not in name, (model.__name__, name)


def test_neither_association_imports_the_evidence_layer() -> None:
    imported = {
        alias.name if isinstance(node, ast.Import) else cast(str, node.module)
        for node in ast.walk(_relationship_tree())
        if isinstance(node, ast.Import | ast.ImportFrom)
        for alias in node.names
    }

    assert "faultatlas.domain.evidence" not in imported
    assert "faultatlas.domain.history_evidence_link" not in imported
    assert imported == {
        "collections.abc",
        "datetime",
        "typing",
        "pydantic",
        "faultatlas.domain.fault",
        "faultatlas.domain.history",
        "faultatlas.domain.identity",
    }


# --- the module's own surface and boundaries ----------------------------------


def _docstrings() -> tuple[str, str, str]:
    module = relationship_module.__doc__ or ""
    return (
        " ".join(module.split()),
        " ".join((FaultReportSourceObjectAssociation.__doc__ or "").split()),
        " ".join((FaultReportHistoryFactAssociation.__doc__ or "").split()),
    )


# The module's executable code, with every docstring removed so that prose is
# governed by the digests below and behaviour by this one. Liveness proves that
# nothing is retained, but a registry that keeps only scalars -- a kind and a
# number are enough to reconstruct an Issue-to-pull-request edge -- retains no
# object to weakly reference, and no scan of module bindings, class members or
# top-level statements reads a validator body. This lock does: any code added
# anywhere in the module, at any nesting depth, changes it.
# Taken under CPython 3.13, the version this project requires and builds on:
# the digest covers `ast.unparse` output, so an interpreter change may move it
# without any source change, unlike the byte digests elsewhere in this file.
RELATIONSHIP_CODE_SHA256 = (
    "0ce2be814d2e54c35473edc18d9514575319d3b9922d1fb89b0020717ad7cc0a"
)


def _executable_code() -> str:
    """The module's code with all docstrings stripped, normalized by unparsing."""
    tree = _relationship_tree()
    for node in ast.walk(tree):
        if not isinstance(
            node, ast.Module | ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef
        ):
            continue
        first = node.body[0] if node.body else None
        if (
            isinstance(first, ast.Expr)
            and isinstance(first.value, ast.Constant)
            and isinstance(first.value.value, str)
        ):
            node.body.pop(0)
    return ast.unparse(tree)


def test_the_executable_code_of_this_module_is_locked() -> None:
    """No behaviour may be added anywhere, including inside a validator body.

    Every structural check in this file reads module bindings, class members or
    top-level statements, and none of them reads the inside of a function. A
    relation registry written into one of the guards is therefore invisible to
    all of them, and invisible to the liveness witness too when it stores
    scalars or copies rather than the supplied values. This digest is not a
    list of places: it covers the whole module, so an intended behaviour change
    updates it deliberately and an unintended one fails here.
    """
    assert _sha256(_executable_code().encode("utf-8")) == RELATIONSHIP_CODE_SHA256


# The published meaning of this Slice is its prose, and five rounds of review
# showed that pinning selected phrases leaves every unpinned sentence free to
# be inverted. These digests lock the three statements whole: any edit fails,
# and an intended edit updates the digest deliberately.
RELATIONSHIP_DOCSTRING_SHA256 = (
    "d7aa8ab472c516795788507720d060ed3217ddc6fa6f68d74d11906d95548469"
)
# The two sections are locked whole rather than only their `S1.P06.S04`
# paragraphs: the forbidden-claim scan reads the whole section, so locking less
# than it reads leaves the difference defended by a phrase list, and a full
# inversion of the published meaning fits in that gap.
ROADMAP_P06_SECTION_SHA256 = (
    "1f935b0fcdf557cd998b33a733d13b0ed56e56e66f5f66a3c9e8e9ef8efcba3b"
)
ROADMAP_MAPPING_SECTION_SHA256 = (
    "f73b4c76dd2903248ac2955ec55ab8308a0b8495eb5cb54ebf8e1e9b008e864d"
)


def _narrow_s04_roadmap_spans() -> tuple[str, str]:
    """The two `S1.P06.S04` narratives themselves, without their surroundings."""
    roadmap = _roadmap()
    return (
        _span(
            roadmap,
            "`S1.P06.S04` adds one new production module",
            "The `S1.P06` route is provisional beyond `S1.P06.S04`.",
        ),
        _span(
            roadmap,
            "`S1.P06.S04` adds the module `faultatlas.domain.fault_source_relationship`",
            "`S1.P05` is complete:",
        ),
    )


def test_the_published_prose_of_this_slice_is_locked() -> None:
    """Whole-text locks, because a phrase list cannot cover every sentence.

    The spans locked here are exactly the spans the forbidden-claim scan reads,
    so no text is scanned by an enumeration alone.
    """
    module, *_ = _docstrings()
    phase, mapping = _s04_roadmap_sections()

    assert _sha256(module.encode("utf-8")) == RELATIONSHIP_DOCSTRING_SHA256
    assert _sha256(phase.encode("utf-8")) == ROADMAP_P06_SECTION_SHA256
    assert _sha256(mapping.encode("utf-8")) == ROADMAP_MAPPING_SECTION_SHA256


def test_the_module_docstring_states_its_load_bearing_non_claims() -> None:
    """In this repository the published meaning is the prose, so it is pinned.

    The roadmap's parallel claims are asserted in detail; leaving the module's
    own statement unpinned would let a later Slice upgrade what these two
    models mean without a single test failing.
    """
    module, *_ = _docstrings()

    for claim in (
        "one deliberately weak, uniform meaning",
        "A source-object association does not say why the source object is related",
        # The two sentences that carry the non-claims are pinned whole: a
        # negation removed from either inverts the published meaning while
        # every shorter phrase around it still matches.
        "and in particular it does not establish that the object originated the "
        "report, proves it, supports it, verifies it, independently observed the "
        "fault, reproduces it, caused it, contains a repair, is the primary "
        "source, or is authoritative",
        "A history-fact association is equally weak. It does not mean that the "
        "fact proves the fault, is causally responsible for it, is a repair for "
        "it, or that a merge fixed it",
        "No `role` field is published",
        "association is not evidence support",
        "Repository coherence is deliberately not inferred.",
        "The source object's repository is not required to equal "
        "`report.context.repository`",
        "No relationship vocabulary is published.",
        "Absence asserts nothing.",
        "Equality is ordinary Pydantic model equality",
        "The module performs no I/O.",
    ):
        assert claim in module, claim


def test_the_module_docstring_keeps_the_three_exclusion_reasons_distinct() -> None:
    """Collapsing them into one would lose why each symbol is excluded."""
    module, *_ = _docstrings()

    assert "`ChangedPathStatus` is a closed vocabulary rather than a fact" in module
    assert "outside the `S1.P05.S07` fact boundary" in module
    assert "no retained record establishes their completeness" in module
    assert "itself the `S1.P05` evidence association" in module
    assert "blur source association with evidence association" in module


# Affirmative forms of the meanings this module exists to refuse. The
# disclaimers legitimately contain "originated", "is the primary source" and
# "causally responsible for", so the phrases pinned here are ones no disclaimer
# can produce: each would have to be written as a claim.
FORBIDDEN_DOCSTRING_CLAIMS = (
    "is the affected repository",
    "verified relation",
    "this association proves",
    "constructs the issue",
    "association is the level-1",
    "is the level-1 evidence",
    "level-1 evidence support for",
    "association establishes",
    "and proves the",
    "and is the primary",
    "does establish that",
    "it means that the fact proves",
)


def _span(roadmap: str, start_anchor: str, end_anchor: str) -> str:
    start = roadmap.index(start_anchor)
    end = roadmap.index(end_anchor)
    assert start < end, (start_anchor, end_anchor)
    return roadmap[start:end]


def _s04_roadmap_sections() -> tuple[str, str]:
    """Both places the roadmap states this Slice's meaning, in full.

    The phase section carries the narrative and the current-code mapping
    carries a second, independent statement of the same surface. Scanning only
    one leaves the other free to contradict it, which is how two of the
    contradictions this Slice has already repaired arrived. Each span is taken
    whole rather than from the `S1.P06.S04` paragraph onward, because a claim
    inserted immediately above that paragraph reads as though it governed it
    while sitting outside a narrower span.
    """
    roadmap = _roadmap()
    return (
        _span(
            roadmap,
            "## S1.P06 — Fault Instance Model",
            "## Preserved later Stage 1 phases",
        ),
        _span(
            roadmap,
            "## Current-code mapping",
            "The minimal CLI and governed Python foundation",
        ),
    )


@pytest.mark.parametrize("claim", FORBIDDEN_DOCSTRING_CLAIMS)
def test_no_prose_in_this_slice_states_a_listed_stronger_claim(claim: str) -> None:
    """No published prose may carry one of these phrases as a claim.

    This is a backstop, not the lock. A fixed list of phrases cannot decide
    whether an English sentence asserts a forbidden meaning, and a reworded
    inversion will pass it. The whole-text locks are what actually hold the
    prose this Slice owns, unconditionally and whatever the wording: the
    digests above for the module docstring and the two roadmap sections, and
    exact equality below for the two class docstrings. What the list adds is
    reach beyond those locks -- the rest of the roadmap and the module body,
    which no lock covers -- so it is read over the whole roadmap
    rather than over named sections, because a claim placed one line above a
    section start or in a status bullet reads as though it governed the
    contract while sitting outside every named span. Matching is
    case-insensitive so capitalising a sentence is not a way past.
    """
    for prose in (*_docstrings(), _roadmap(), _module_body()):
        assert claim not in prose.lower(), claim


def test_the_roadmap_section_states_the_same_non_claims_as_the_module() -> None:
    """The two published statements of the meaning must not drift apart.

    The narrow span is used here so a claim cannot be satisfied by text in the
    `S1.P06.S01` to `S1.P06.S03` narratives; the wide spans are for the
    forbidden scan, which must also see text placed just outside this one.
    """
    section = _narrow_s04_roadmap_spans()[0]

    for claim in (
        "Association is not proof, support, causation, or repair correctness.",
        "no `role` field guesses among them",
        "approval is not FaultAtlas confidence",
        "a changed path is not an affected path",
        "is not a fault-occurrence instant",
        "No relationship vocabulary is created.",
        "no source-object-to-source-object relation is created",
        "neither creates, extends, nor reads",
        "deliberately not required to equal `report.context.repository`",
        "a cross-repository association is accepted",
        "construct no Issue-to-pull-request pairing and imply none",
        "sharing one report is not a transitivity rule",
        "absence of an association asserts only that none is supplied here",
    ):
        assert claim in section, claim


def test_each_association_docstring_states_a_supplied_association() -> None:
    _, source_doc, history_doc = _docstrings()

    assert source_doc == (
        "Supplied association from one fault report to one source object."
    )
    assert history_doc == (
        "Supplied association from one fault report to one history fact."
    )


def test_the_predecessor_fault_module_is_byte_identical_to_its_publication() -> None:
    data = FAULT_SOURCE.read_bytes()

    assert len(data) == FAULT_SOURCE_BYTES
    assert _sha256(data) == FAULT_SOURCE_SHA256


@pytest.mark.parametrize(
    "relative",
    (
        "src/faultatlas/domain/fault.py",
        "src/faultatlas/domain/identity.py",
        "src/faultatlas/domain/history.py",
        "src/faultatlas/domain/history_evidence_link.py",
    ),
)
def test_no_predecessor_production_module_imports_this_bridge(relative: str) -> None:
    source = (REPOSITORY_ROOT / relative).read_text(encoding="utf-8")

    assert "fault_source_relationship" not in source
    assert "FaultReportSourceObjectAssociation" not in source
    assert "FaultReportHistoryFactAssociation" not in source


def test_the_module_is_not_re_exported_from_the_package_or_domain_root() -> None:
    assert faultatlas.__all__ == ["__version__"]
    assert not hasattr(faultatlas.domain, "__all__")
    for symbol in EXPECTED_EXPORTS:
        assert not hasattr(faultatlas, symbol)
        assert not hasattr(faultatlas.domain, symbol)


def test_the_module_performs_no_io() -> None:
    tree = _relationship_tree()
    called = {
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }

    assert not called & {"open", "eval", "exec", "compile", "__import__", "print"}
    body = _module_body()
    for forbidden in ("import os", "import io", "Path(", "requests", "urllib", "now("):
        assert forbidden not in body, forbidden


def test_only_the_declared_private_helpers_exist() -> None:
    """Nested definitions count: a helper hidden in a closure is still a helper."""
    functions = [
        node.name
        for node in ast.walk(_relationship_tree())
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)
    ]

    assert sorted(functions) == sorted(DECLARED_FUNCTIONS)
    for name in functions:
        assert name.startswith("_")
        assert name not in relationship_module.__all__


def test_the_tracked_production_inventory_is_fifteen_modules() -> None:
    tracked = subprocess.run(  # noqa: S603 - literal argv, no shell
        ["git", "ls-files", "src/"],
        cwd=REPOSITORY_ROOT,
        capture_output=True,
        check=False,
    )
    assert tracked.returncode == 0, tracked.stderr
    observed = sorted(tracked.stdout.decode("utf-8").split())

    assert observed == [f"src/{name}" for name in EXPECTED_PRODUCTION_MODULES]
    assert len(observed) == 15
    assert "src/faultatlas/domain/fault_source_relationship.py" in observed


# --- the roadmap transition ---------------------------------------------------


def test_the_roadmap_records_the_p06_s04_transition() -> None:
    raw = ROADMAP.read_text(encoding="utf-8")
    roadmap = _roadmap()
    mapping = roadmap.split("## Current-code mapping", 1)
    assert len(mapping) == 2, "roadmap must retain a current-code mapping section"
    current = mapping[1]

    assert "`S1.P06` is active and incomplete" in roadmap
    assert "`S1.P06.S01` is complete" in roadmap
    assert "`S1.P06.S02` is complete" in roadmap
    assert "`S1.P06.S03` is complete" in roadmap
    assert "`S1.P06.S04` is complete" in roadmap
    assert "`S1.P06.S05` is next and not started" in roadmap
    assert "`S1.P07` through `S1.P10` remain not started" in roadmap
    assert (
        "`S1.P06.S04` — Bounded Source and History Relationships (complete)" in roadmap
    )
    assert "`S1.P06.S05` — Repair candidates (next, not started)" in roadmap

    assert "faultatlas.domain.fault_source_relationship" in current
    for symbol in EXPECTED_EXPORTS:
        assert f"`{symbol}`" in current
    assert "Production Python sources are 15." in current
    assert "`association.report.context.fault`" in roadmap

    # The superseded live gate and the provisional S04 title must be retired.
    assert "`S1.P06.S04` is next and not started" not in roadmap
    assert "`S1.P06.S04` — Bounded source relationships (next, not started)" not in (
        roadmap
    )
    assert "`S1.P06` is complete" not in roadmap
    assert "`S1.P06.S05` is complete" not in roadmap
    assert "- **S1.P06 — Fault Instance Model**" not in raw


def test_the_roadmap_states_the_s04_decisions_and_non_claims() -> None:
    roadmap = _roadmap()

    assert "production Python sources move from 14 to 15" in roadmap
    assert "cross-domain bridge" in roadmap
    assert "Association is not proof, support, causation, or repair correctness." in (
        roadmap
    )
    assert "no `role` field guesses among them" in roadmap
    assert "approval is not FaultAtlas confidence" in roadmap
    assert "a changed path is not an affected path" in roadmap
    assert "is not a fault-occurrence instant" in roadmap
    assert "No relationship vocabulary is created." in roadmap
    assert "construct no Issue-to-pull-request pairing and imply none" in roadmap
    assert "sharing one report is not a transitivity rule" in roadmap
    assert "without merging those two fault subjects" in roadmap
    assert "closed vocabulary rather than a fact" in roadmap
    assert "outside the `S1.P05.S07` fact boundary" in roadmap
    assert "which nesting here would blur with source association" in roadmap
    assert "no complete development history is owned here" in roadmap
    assert "remain `S1.P06.S10` work" in roadmap


def test_the_roadmap_preserves_the_predecessor_history_as_written() -> None:
    roadmap = _roadmap()

    assert (
        "`S1.P06.S01` publishes one new production module, `faultatlas.domain.fault`, "
        "whose initial `__all__` is exactly `FaultInstanceIdentity` and "
        "`FaultRepositoryContext`." in roadmap
    )
    assert "so production Python sources remain 14" in roadmap
    assert "The `S1.P06.S01` and `S1.P06.S02` models are unchanged." in roadmap
    assert "`S1.P05` is complete" in roadmap
    assert "`S1.P06` was `eligible_to_begin`" in roadmap


def test_the_roadmap_carries_exactly_one_live_gate() -> None:
    roadmap = _roadmap()

    live_next = re.findall(
        r"`(S1\.P\d\d(?:\.S\d\d)?)` is next and not started", roadmap
    )
    assert live_next, "the roadmap names no next gate"
    assert set(live_next) == {"S1.P06.S05"}, sorted(set(live_next))
    live_phases = re.findall(r"`(S1\.P\d\d)` is active and incomplete", roadmap)
    assert set(live_phases) == {"S1.P06"}, sorted(set(live_phases))
    for line in ROADMAP.read_text(encoding="utf-8").splitlines():
        if "next and not started" in line:
            assert "`S1.P06.S05`" in line, line


# --- packaging and an isolated installed-wheel smoke --------------------------


ISOLATED_SMOKE = """
import json
import os
import sys
import uuid
from pathlib import Path

installed = Path(os.environ["INSTALLED_ROOT"]).resolve()
checkout = Path(os.environ["CHECKOUT_SOURCE_ROOT"]).resolve()
sys.path = [entry for entry in sys.path if Path(entry).resolve() != checkout]
sys.path.insert(0, str(installed))

import faultatlas.domain.fault_source_relationship as relationship_module
from faultatlas.domain.fault import (
    FaultInstanceIdentity,
    FaultReportIdentity,
    FaultRepositoryContext,
    SuppliedFaultReport,
)
from faultatlas.domain.fault_source_relationship import (
    FaultReportHistoryFactAssociation,
    FaultReportSourceObjectAssociation,
)
from faultatlas.domain.history import (
    PullRequestMergeRevisionOutcome,
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
    GitCommitIdentity,
    GitHashAlgorithm,
    GitObjectKind,
)

module = Path(relationship_module.__file__).resolve()
assert module.is_relative_to(installed), module
assert not module.is_relative_to(checkout), module
assert relationship_module.__all__ == [
    "FaultReportSourceObjectAssociation",
    "FaultReportHistoryFactAssociation",
]

repository = RepositoryIdentity(
    provider=ProviderKey("github"),
    provider_repository_id=ProviderRepositoryId(os.environ["REPOSITORY_ID"]),
)
report = SuppliedFaultReport(
    report=FaultReportIdentity(uuid.UUID(os.environ["REPORT_UUID"])),
    context=FaultRepositoryContext(
        fault=FaultInstanceIdentity(uuid.UUID(os.environ["FAULT_UUID"])),
        repository=repository,
    ),
    problem_statement=os.environ["PROBLEM_STATEMENT"],
    behavioral_deviation=os.environ["BEHAVIORAL_DEVIATION"],
)
issue = NumberedSourceObjectIdentity(
    repository_identity=repository,
    kind=SourceObjectKind.ISSUE,
    repository_scoped_number=RepositoryScopedNumber(os.environ["ISSUE_NUMBER"]),
)
pull_request = NumberedSourceObjectIdentity(
    repository_identity=repository,
    kind=SourceObjectKind.PULL_REQUEST,
    repository_scoped_number=RepositoryScopedNumber(os.environ["PULL_REQUEST_NUMBER"]),
)
source_association = FaultReportSourceObjectAssociation(
    report=report, source_object=issue
)
history_association = FaultReportHistoryFactAssociation(
    report=report,
    history_fact=PullRequestMergeRevisionOutcome(
        pull_request=pull_request,
        merge_revision=GitCommitIdentity(
            kind=GitObjectKind.COMMIT,
            algorithm=GitHashAlgorithm.SHA1,
            full_digest=os.environ["MERGE_REVISION"],
        ),
    ),
)

assert (
    FaultReportSourceObjectAssociation.model_validate_json(
        source_association.model_dump_json()
    )
    == source_association
)
assert (
    FaultReportHistoryFactAssociation.model_validate_json(
        history_association.model_dump_json()
    )
    == history_association
)

print(
    json.dumps(
        {
            "module": str(module),
            "source": source_association.model_dump_json(),
            "history": history_association.model_dump_json(),
        }
    )
)
"""


@pytest.fixture(scope="session")
def offline_distributions(
    tmp_path_factory: pytest.TempPathFactory,
) -> tuple[Path, Path]:
    uv = shutil.which("uv")
    assert uv is not None, "uv must be available to build the supported distributions"

    root = tmp_path_factory.mktemp("source-relationship-package")
    output = root / "distributions"
    output.mkdir()
    environment = os.environ.copy()
    environment.update(
        {
            "PYTHONDONTWRITEBYTECODE": "1",
            "UV_CACHE_DIR": str(root / "uv-cache"),
            "UV_NO_SYNC": "1",
            "UV_OFFLINE": "1",
        }
    )
    result = subprocess.run(
        [uv, "build", "--offline", "--no-create-gitignore", "--out-dir", str(output)],
        cwd=REPOSITORY_ROOT,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"offline build failed\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )
    wheels = tuple(output.glob("*.whl"))
    sdists = tuple(output.glob("*.tar.gz"))
    assert len(wheels) == 1, f"expected one wheel, found {wheels!r}"
    assert len(sdists) == 1, f"expected one sdist, found {sdists!r}"
    return wheels[0], sdists[0]


EXPECTED_PRODUCTION_MODULES = [
    "faultatlas/__init__.py",
    "faultatlas/__main__.py",
    "faultatlas/cli.py",
    "faultatlas/domain/__init__.py",
    "faultatlas/domain/compatibility.py",
    "faultatlas/domain/evidence.py",
    "faultatlas/domain/fault.py",
    "faultatlas/domain/fault_source_relationship.py",
    "faultatlas/domain/history.py",
    "faultatlas/domain/history_evidence_link.py",
    "faultatlas/domain/identity.py",
    "faultatlas/domain/revision.py",
    "faultatlas/domain/snapshot.py",
    "faultatlas/domain/snapshot_evidence_link.py",
    "faultatlas/domain/source.py",
]


def test_the_wheel_ships_the_bridge_and_no_corpus_or_test_material(
    offline_distributions: tuple[Path, Path],
) -> None:
    wheel, _ = offline_distributions
    with zipfile.ZipFile(wheel) as archive:
        names = tuple(info.filename for info in archive.infolist() if not info.is_dir())

    modules = sorted(name for name in names if name.endswith(".py"))
    assert modules == EXPECTED_PRODUCTION_MODULES
    assert len(modules) == 15
    assert "faultatlas/domain/fault_source_relationship.py" in modules
    assert "faultatlas/domain/fault.py" in modules
    for name in names:
        assert "reference_corpus" not in name
        assert not name.startswith("tests/")
        assert not name.startswith("docs/")


def test_the_sdist_ships_the_bridge_and_no_corpus_or_test_material(
    offline_distributions: tuple[Path, Path],
) -> None:
    _, sdist = offline_distributions
    with tarfile.open(sdist, "r:gz") as archive:
        names = tuple(member.name for member in archive.getmembers() if member.isfile())

    modules = sorted(
        name.split("/src/", 1)[1] for name in names if name.endswith(".py")
    )
    assert modules == EXPECTED_PRODUCTION_MODULES
    assert len(modules) == 15
    assert "faultatlas/domain/fault_source_relationship.py" in modules
    for name in names:
        parts = Path(name).parts
        assert "reference_corpus" not in parts
        assert "tests" not in parts
        assert "docs" not in parts


def test_the_installed_wheel_exercises_both_new_association_types(
    offline_distributions: tuple[Path, Path],
    tmp_path: Path,
) -> None:
    """Both S04 models must run from the wheel copy, not from the checkout."""
    wheel, _ = offline_distributions
    installed = tmp_path / "installed"
    installed.mkdir()
    with zipfile.ZipFile(wheel) as archive:
        archive.extractall(installed)

    assert (installed / "faultatlas/domain/fault_source_relationship.py").is_file()

    environment = os.environ.copy()
    environment.update(
        {
            "INSTALLED_ROOT": str(installed),
            "CHECKOUT_SOURCE_ROOT": str(CHECKOUT_SOURCE_ROOT),
            "FAULT_UUID": SUPPLIED_FAULT_TEXT,
            "REPORT_UUID": SUPPLIED_REPORT_TEXT,
            "REPOSITORY_ID": RETAINED_REPOSITORY_ID,
            "ISSUE_NUMBER": RETAINED_ISSUE_NUMBER,
            "PULL_REQUEST_NUMBER": RETAINED_PULL_REQUEST_NUMBER,
            "MERGE_REVISION": RETAINED_MERGE_REVISION,
            "PROBLEM_STATEMENT": PROBLEM_STATEMENT,
            "BEHAVIORAL_DEVIATION": BEHAVIORAL_DEVIATION,
            "PYTHONDONTWRITEBYTECODE": "1",
        }
    )
    environment.pop("PYTHONPATH", None)
    result = subprocess.run(
        [sys.executable, "-I", "-c", ISOLATED_SMOKE],
        cwd=tmp_path,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, (
        f"isolated wheel smoke failed\nstdout:\n{result.stdout}\n"
        f"stderr:\n{result.stderr}"
    )
    reported: dict[str, str] = json.loads(result.stdout.strip().splitlines()[-1])
    assert Path(reported["module"]).is_relative_to(installed)
    assert not Path(reported["module"]).is_relative_to(CHECKOUT_SOURCE_ROOT)
    assert json.loads(reported["source"]) == _payload(_source_association())
    assert json.loads(reported["history"]) == _payload(_history_association())
