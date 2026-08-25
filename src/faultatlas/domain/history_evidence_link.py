"""Association between one pull-request history fact and one evidence record.

This module owns the single cross-domain relation between the published
development-history value layer and the published durable evidence-record
reference. Neither side changes: the history layer stays evidence-neutral and
the evidence layer stays unchanged, so the association lives here rather than
in either domain module.

The claim is exactly one level deep. A link records that its caller associated
one supplied published history fact with one supplied durable evidence-record
reference, and nothing else. It does not claim that the referenced record was
read, parsed, or inspected, that the record contains, corroborates, derives,
verifies, or proves the fact, or that the fact is correct or authoritative. No
support role, strength, status, confidence, review state, or verification
outcome is recorded, and every association carries the same weak, uniform
meaning.

The fact position accepts exactly one supplied revision role binding, changed
path, review revision approval, merge revision outcome, head-ref deletion, or
historical occurrence time, each of which corresponds to a retained normalized
observation. `PullRequestChangeSet` is excluded: its base and head composition,
its caller-supplied changed-path tuple, and its supplied order are declared by
callers rather than by any retained record, and it deliberately asserts no
completeness, so associating a record with it would manufacture provenance.
`ChangedPathStatus` is excluded because a closed vocabulary is not a fact.

Both positions are closed to untyped Python input. A caller must supply an
already published value; a mapping, an attribute-backed object, or a foreign
model is refused even when its own children are published values, because
constructing a published fact is the history layer's responsibility and not
this relation's. Strictness alone cannot express that: a strict constraint is
not applicable to a union schema, and a strict union still admits a mapping
whose children are typed.

One admitted member carries an occurrence instant, whose only JSON form is a
string. Any validator standing above a fact revalidates its result as Python
input, so that member's guard decodes exactly that one leaf back to an aware
instant before the published model reads it.

The decoding is transport only. It reads the instant through the same aware
datetime grammar the published model applies to JSON, so the link accepts and
refuses exactly the lexical forms the embedded fact does; a stdlib ISO parser
would not, admitting week dates and basic-format instants the published model
rejects while refusing a lowercase zone designator it accepts. Grammar is all
this decides: the published model still applies its own zero-offset rule, its
own normalization, and every other guard it declares, and no other field of any
admitted fact is read, rewritten, or interpreted here.

The referenced record is identified as a whole. There is no JSON pointer,
semantic path, field locator, byte span, request, artifact, or envelope that
would locate a fact inside the record, and byte offsets are not a substitute
for one. That a fact's fields are drawn from several places in one record, or
that an alternate surface inside it omits a duplicate field, changes nothing
here: the record is associated whole, and the retained record already carries
its own field-state. Each link carries exactly one record; associating one fact
with two records is two independent link values, and no ordering, duplicate,
precedence, or bound semantics over multiple associations exists here. A
correction or superseding record is associated only when a caller supplies it,
and no supersession is followed.

The target fact is embedded by value, so no durable history bytes, record
digest, registry, identifier, or persistence is required. The module performs
no I/O: it resolves nothing, reads nothing, and never inspects the record it
references. Occurrence ordering, chronology, completeness, absence, confidence,
review, and durable serialization all remain outside it.
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

from faultatlas.domain.evidence import DurableEvidenceRecordReference
from faultatlas.domain.history import (
    PullRequestChangedPath,
    PullRequestHeadRefDeletion,
    PullRequestHistoricalOccurrenceTime,
    PullRequestMergeRevisionOutcome,
    PullRequestReviewRevisionApproval,
    PullRequestRevisionRoleBinding,
)

__all__ = [
    "PullRequestHistoryFactEvidenceLink",
]

_UNTYPED_FACT_MESSAGE = (
    "fact must be a published pull request history fact in Python input"
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


class PullRequestHistoryFactEvidenceLink(BaseModel):
    """Supplied association from one history fact to one durable record."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        strict=True,
        revalidate_instances="always",
        validate_default=True,
    )

    fact: (
        _PublishedRevisionRoleBinding
        | _PublishedChangedPath
        | _PublishedReviewRevisionApproval
        | _PublishedMergeRevisionOutcome
        | _PublishedHeadRefDeletion
        | _PublishedHistoricalOccurrenceTime
    )
    evidence_record: DurableEvidenceRecordReference

    @field_validator("evidence_record", mode="before")
    @classmethod
    def _require_typed_python_evidence_record(
        cls,
        value: object,
        info: ValidationInfo,
    ) -> object:
        if info.mode == "python" and not isinstance(
            value,
            DurableEvidenceRecordReference,
        ):
            raise ValueError(
                "evidence_record must be a DurableEvidenceRecordReference in "
                "Python input"
            )
        return value
