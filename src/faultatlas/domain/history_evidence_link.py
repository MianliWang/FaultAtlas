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

The fact position is closed by strict typing rather than by a before-guard.
One admitted member carries an occurrence instant, whose only JSON form is a
string, and any before or wrap validator standing above the fact union
revalidates its result as Python input -- which would strip that instant of
its JSON reading and make the occurrence-time family impossible to reconstruct
from JSON. Strict mode already refuses an untyped mapping, a dumped fact, a
foreign model, and every excluded published value in that position, so the
guard would add a message and remove a capability. The evidence-record
position stands above no such value and keeps its explicit typed guard.

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

from pydantic import BaseModel, ConfigDict, ValidationInfo, field_validator

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
        PullRequestRevisionRoleBinding
        | PullRequestChangedPath
        | PullRequestReviewRevisionApproval
        | PullRequestMergeRevisionOutcome
        | PullRequestHeadRefDeletion
        | PullRequestHistoricalOccurrenceTime
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
