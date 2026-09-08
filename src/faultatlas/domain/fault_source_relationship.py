"""Supplied associations from one fault report to sources and history facts.

This module owns the two cross-domain relations the current FaultInstance work
needs: one from a published supplied fault report to an already-typed external
source-object identity, and one from that same report to an already-published
bounded pull-request history fact. Neither side changes. The fault domain stays
free of provider identity, the `S1.P01` identity layer stays free of fault
knowledge, and the `S1.P05` history layer stays exactly the bounded fact set it
published, so both associations live here rather than in any of them.

The anchor is the published `SuppliedFaultReport`, not a bare
`FaultInstanceIdentity`. An identity alone is only a caller-designated subject
with no content; the report is the smallest published value that carries the
caller's problem statement and behavioral deviation, so it is the meaningful
thing an external source or a historical fact can be associated with. The
logical fault subject stays reachable at `association.report.context.fault`,
and nothing is restated at association level. A suspected, latent, or
unreproduced report needs no scenario and no occurrence record before it can
carry either association.

Both relations carry one deliberately weak, uniform meaning: the caller
associates these two supplied values. That is the entire claim. A source-object
association does not say why the source object is related, and in particular it
does not establish that the object originated the report, proves it, supports
it, verifies it, independently observed the fault, reproduces it, caused it,
contains a repair, is the primary source, or is authoritative. No `role` field
is published to guess among those meanings, because they have different owners
and different evidence, and a caller that supplies one association supplies no
evidence for any of them. Stronger concrete relations may be published later,
each with its own owner and its own evidence, rather than smuggled in now as a
vocabulary.

A history-fact association is equally weak. It does not mean that the fact
proves the fault, is causally responsible for it, is a repair for it, or that a
merge fixed it; that an approval is FaultAtlas confidence or a statement of
correctness; that a changed path is an affected path; that a deleted head ref
caused anything; or that a source occurrence instant is a fault-occurrence
instant. The embedded `S1.P05` fact keeps exactly its own published semantics
and gains none from being associated here. Nor is the `S1.P05.S07` LEVEL-1
evidence association upgraded, reached, or implied: association is not evidence
support, and the fact-to-record bridge remains the only thing that says a
retained record was named for a fact.

The source-object position admits exactly `NumberedSourceObjectIdentity` and
`ProviderScopedSourceObjectIdentity`, which together cover every currently
published `S1.P01` object kind: issue, pull request, issue comment, pull
request comment, pull request review, pull request review comment, and timeline
event. A bare `RepositoryIdentity` is not admitted, because repository
placement is already carried separately by the report's own
`FaultRepositoryContext` and a repository is not an object a report is about.
Commit, tree, blob, ref, and path identities are not admitted either: those are
revision and repair-shaped subjects whose relations need their own owner.

Repository coherence is deliberately not inferred. The source object's
repository is not required to equal `report.context.repository`. A report may
be analyzed in one repository context while the material a caller wants to
associate lives in another, and refusing that would force a false placement or
a lost association. Accepting it asserts nothing further: no affected
repository, no origin repository, no ownership, no causation, and no
applicability follows from a cross-repository association.

The history-fact position admits exactly the same six published facts the
`S1.P05.S07` evidence link admits, reused whole and unmodified: a supplied
revision role binding, changed path, review revision approval, merge revision
outcome, head-ref deletion, or historical occurrence time. No `S1.P05` field,
enum, role, revision, timestamp, path, or source identity is redefined,
narrowed, widened, or renamed here.

Three published history symbols are excluded, for three different reasons that
must not be collapsed into one. `ChangedPathStatus` is a closed vocabulary
rather than a fact, so there is nothing to associate. `PullRequestChangeSet` is
outside the `S1.P05.S07` fact boundary because its base and head composition,
its changed-path tuple, and its supplied order are caller-composed and no
retained record establishes their completeness; a later Slice may consume it
explicitly, but this one does not silently move that boundary.
`PullRequestHistoryFactEvidenceLink` is itself the `S1.P05` evidence
association, and nesting it in a source relation would blur source association
with evidence association and risk implicitly upgrading what the evidence link
means.

No relationship vocabulary is published. There is no relationship kind, type,
subject-predicate-object triple, graph node or edge, inverse, transitive
closure, relationship identifier, relation registry, or completeness claim, and
no source-object-to-source-object relation of any shape is created here. The
published `S1.P01` `ProviderScopedSourceObjectIdentity` already carries its own
`parent` numbered object, so a review admitted at `source_object` reaches the
pull request containing it; that containment is predecessor semantics this
module neither creates, extends, nor reads. In particular, a caller that
supplies one association from a report to an Issue and a second from the same
report to a pull request has supplied exactly two independent associations.
That constructs no Issue-to-pull-request pairing and implies none; the retained
pytest #4412 and #4414 pairing stays a reviewed derived interpretation rather
than a provider fact, and sharing one report is not a transitivity rule.
Ancestry, reachability, repository evolution, and any generic
development-history graph remain outside this module entirely.

Each association is one value, so multiplicity is expressed by holding several
of them. One report may be associated with an Issue, a pull request, and a
comment at once, and independently with any of the six history facts. One
source object may be associated with two reports whose embedded fault
identities differ, which merges nothing: the two remain two fault subjects. No
collection, ordering, uniqueness rule, precedence, or bound over several
associations exists here.

Absence asserts nothing. That no association value is supplied means only that
none is supplied here: not that no source relation exists in reality, not that
the source is unknown, unavailable, unsupported, or disproved, and the same for
history facts. No boolean and no missing-state enum stands for any of those,
because none of them is what an absent value means.

Equality is ordinary Pydantic model equality over the declared fields. Nothing
overrides `__eq__`, `__hash__`, or ordering, so equal values hash equally where
their contents are hashable and unequal values are free to collide.

Every model-valued position is closed to untyped Python input, following the
published convention. A caller must supply an already-typed value: a raw
mapping, a string, a UUID, an attribute-backed lookalike, or a foreign model is
refused even when its scalar content matches, because constructing a published
report, source-object identity, or history fact is that value's own
responsibility. Strictness alone cannot express that for the two union
positions, since a strict constraint is not applicable to a union schema and a
strict union still admits a mapping whose children are typed. JSON is a
different input language: there the declared child schemas reconstruct the
published values normally, so `model_validate_json(value.model_dump_json())`
succeeds while `model_validate(value.model_dump())` deliberately does not,
because a Python dump has projected its typed children to primitives and
mappings. That closure is stated over the declared default validation policy;
`strict=False`, an altered `extra` setting, a schema or serializer override,
and the string-parsing entry point are not entry points designed here.

The two union positions are guarded differently only because Pydantic requires
it. One before-validator over the whole source-object position is enough, and
its members reconstruct from JSON unchanged. The history-fact position cannot
use that shape: one admitted member carries an occurrence instant whose only
JSON form is a string, and any validator standing above the union hands its
result to the members as Python input, where a strict aware datetime refuses a
string. Each admitted fact therefore carries its own narrow guard, and the
occurrence-time guard decodes exactly that one leaf back to an aware instant
before the published model reads it. The decoding is transport only: it reads
the instant through the same aware-datetime grammar the published model applies
to JSON, so this relation accepts and refuses exactly the lexical forms the
embedded fact does. The published model still applies its own zero-offset rule,
its own normalization, and every other guard it declares, and no other field of
any admitted fact is read, rewritten, or interpreted here.

The module performs no I/O. It reads no clock, allocates no identifier,
consults no registry or environment, resolves nothing, and never inspects the
source object or the retained material a fact was drawn from.
"""

from collections.abc import Callable, Mapping
from datetime import datetime
from typing import Annotated, Any, cast

from pydantic import (
    AwareDatetime,
    BaseModel,
    BeforeValidator,
    ConfigDict,
    TypeAdapter,
    ValidationInfo,
    field_validator,
)

from faultatlas.domain.fault import SuppliedFaultReport
from faultatlas.domain.history import (
    PullRequestChangedPath,
    PullRequestHeadRefDeletion,
    PullRequestHistoricalOccurrenceTime,
    PullRequestMergeRevisionOutcome,
    PullRequestReviewRevisionApproval,
    PullRequestRevisionRoleBinding,
)
from faultatlas.domain.identity import (
    NumberedSourceObjectIdentity,
    ProviderScopedSourceObjectIdentity,
)

__all__ = [
    "FaultReportSourceObjectAssociation",
    "FaultReportHistoryFactAssociation",
]

_UNTYPED_REPORT_MESSAGE = "report must be a SuppliedFaultReport in Python input"
_UNTYPED_SOURCE_OBJECT_MESSAGE = (
    "source_object must be a published source object identity in Python input"
)
_UNTYPED_FACT_MESSAGE = (
    "history_fact must be a published pull request history fact in Python input"
)

_ADMITTED_SOURCE_OBJECTS: tuple[type[BaseModel], ...] = (
    NumberedSourceObjectIdentity,
    ProviderScopedSourceObjectIdentity,
)

# The published aware-instant grammar, read through the same adapter the
# embedded fact applies to its own JSON form.
_OCCURRED_AT: TypeAdapter[datetime] = TypeAdapter(AwareDatetime)


def _require_published_fact(expected: type[BaseModel]) -> Callable[..., Any]:
    def _require(value: object, info: ValidationInfo) -> object:
        if info.mode == "python" and not isinstance(value, expected):
            raise ValueError(_UNTYPED_FACT_MESSAGE)
        return value

    return _require


def _require_published_occurrence_time(value: object, info: ValidationInfo) -> object:
    if info.mode == "python":
        if not isinstance(value, PullRequestHistoricalOccurrenceTime):
            raise ValueError(_UNTYPED_FACT_MESSAGE)
        return value
    if not isinstance(value, Mapping):
        return value
    supplied = cast(Mapping[str, object], value)
    instant = supplied.get("occurred_at")
    if not isinstance(instant, str):
        return supplied
    decoded: dict[str, object] = dict(supplied)
    decoded["occurred_at"] = _OCCURRED_AT.validate_python(instant)
    return decoded


_PublishedRevisionRoleBinding = Annotated[
    PullRequestRevisionRoleBinding,
    BeforeValidator(_require_published_fact(PullRequestRevisionRoleBinding)),
]
_PublishedChangedPath = Annotated[
    PullRequestChangedPath,
    BeforeValidator(_require_published_fact(PullRequestChangedPath)),
]
_PublishedReviewRevisionApproval = Annotated[
    PullRequestReviewRevisionApproval,
    BeforeValidator(_require_published_fact(PullRequestReviewRevisionApproval)),
]
_PublishedMergeRevisionOutcome = Annotated[
    PullRequestMergeRevisionOutcome,
    BeforeValidator(_require_published_fact(PullRequestMergeRevisionOutcome)),
]
_PublishedHeadRefDeletion = Annotated[
    PullRequestHeadRefDeletion,
    BeforeValidator(_require_published_fact(PullRequestHeadRefDeletion)),
]
_PublishedHistoricalOccurrenceTime = Annotated[
    PullRequestHistoricalOccurrenceTime,
    BeforeValidator(_require_published_occurrence_time),
]


class FaultReportSourceObjectAssociation(BaseModel):
    """Supplied association from one fault report to one source object."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        strict=True,
        revalidate_instances="always",
        validate_default=True,
    )

    report: SuppliedFaultReport
    source_object: NumberedSourceObjectIdentity | ProviderScopedSourceObjectIdentity

    @field_validator("report", mode="before")
    @classmethod
    def _require_typed_python_report(
        cls,
        value: object,
        info: ValidationInfo,
    ) -> object:
        if info.mode == "python" and not isinstance(value, SuppliedFaultReport):
            raise ValueError(_UNTYPED_REPORT_MESSAGE)
        return value

    @field_validator("source_object", mode="before")
    @classmethod
    def _require_typed_python_source_object(
        cls,
        value: object,
        info: ValidationInfo,
    ) -> object:
        if info.mode == "python" and not isinstance(value, _ADMITTED_SOURCE_OBJECTS):
            raise ValueError(_UNTYPED_SOURCE_OBJECT_MESSAGE)
        return value


class FaultReportHistoryFactAssociation(BaseModel):
    """Supplied association from one fault report to one history fact."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        strict=True,
        revalidate_instances="always",
        validate_default=True,
    )

    report: SuppliedFaultReport
    history_fact: (
        _PublishedRevisionRoleBinding
        | _PublishedChangedPath
        | _PublishedReviewRevisionApproval
        | _PublishedMergeRevisionOutcome
        | _PublishedHeadRefDeletion
        | _PublishedHistoricalOccurrenceTime
    )

    @field_validator("report", mode="before")
    @classmethod
    def _require_typed_python_report(
        cls,
        value: object,
        info: ValidationInfo,
    ) -> object:
        if info.mode == "python" and not isinstance(value, SuppliedFaultReport):
            raise ValueError(_UNTYPED_REPORT_MESSAGE)
        return value
