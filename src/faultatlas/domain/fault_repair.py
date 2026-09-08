"""Caller-proposed repair candidates and their concrete implementation links.

This module opens the repair layer of the FaultInstance model with the smallest
thing a caller can say about fixing a fault: that they propose something. A
repair candidate names a proposal subject, ties it to one already published
supplied fault report, and carries the caller's own statement of what the repair
would be. Two further relations attach concrete material to that proposal, one
Git commit revision at a time and one bounded `S1.P05` pull-request change set at
a time. Nothing here decides whether any of it works.

A candidate is a proposal, not an outcome. Designating one does not establish
that the root cause is known, that the repair was implemented, applied, merged,
or deployed, that any test passed, that a regression was avoided, that the fault
is fixed, or that evidence supports any of it. No status, confidence,
correctness, verification, review, or outcome field exists, and none is implied
by the presence of an association. Test material, reported outcomes and
comparability are `S1.P06.S06` work; case-local explanation, hypothesis and
expected property are `S1.P06.S07` work; the fault-evidence bridge is
`S1.P06.S09` work; and generic review, support and confidence calculus belongs to
`S1.P09`.

A candidate identity names one caller-designated proposal subject and nothing
more. It is a fifth independent UUID-rooted value beside the fault, report,
scenario, and occurrence identities, neither a subclass nor an alias of any of
them, and the five stay nominally distinct even when one scalar is assigned to
all five. The caller assigns the identifier: nothing here generates, derives,
reserves, looks up, deduplicates, merges, or registers one, no identifier is
derived from a pull-request number, a commit digest, change-set content, a report
identity, or a fault identity, and an identity is therefore never a digest of the
repair it names. Nil and Max are ordinary admitted values rather than sentinels,
no generation version is required or inferred, and an identity is not an
authorization token, a capability, or a security boundary. Its JSON form is the
ordinary bare UUID string, with no wrapper object and no compatibility adapter,
and equality, hashing and ordering are left exactly as Pydantic defines them.

A supplied repair candidate binds one candidate identity to one published
`SuppliedFaultReport` consumed whole and to one proposed repair statement. The
fault subject stays reachable at `candidate.report.context.fault`, and no fault,
repository, report identity, problem statement, or behavioral deviation is
restated at candidate level. It requires no scenario and no occurrence: a
proposal may be made about a suspected, latent, unreproduced, or cause-unknown
report, and demanding a claimed manifestation first would exclude exactly the
cases a repair proposal is most useful for.

It requires no root cause either. A caller may propose a repair that targets an
observed behavioral deviation while the true cause is still unknown, so no cause,
explanation, or hypothesis field exists and none is required to construct a
candidate. Proposing a repair is not claiming to have diagnosed the fault.

A candidate is complete without any implementation. `S1.P06.S05` deliberately
separates the proposal from the concrete material, so a candidate may be purely
conceptual and carry no revision and no change set at all, which is what a
not-yet-implemented repair looks like. Absence of an implementation association
means only that none is supplied here: not that the repair is impossible,
rejected, abandoned, known to be unimplemented, or incorrect. No boolean, status,
or sentinel stands for any of those.

The repair statement is a claim and is handled as opaque prose. It must be
present, non-blank, and at most 4096 characters; leading or trailing whitespace
is refused rather than trimmed, so whitespace-only text fails, and a value that
cannot encode as UTF-8 is refused. Admitted Unicode and interior whitespace,
including newlines, are preserved exactly: nothing here lowercases, normalizes,
parses, tokenizes, classifies, or rewrites it, and nothing decides whether the
proposal it describes is sound, minimal, or correct. The 4096 limit is a
character bound of this internal supplied-text contract, not a durable
byte-format promise, and the rule is stated on the field rather than through a
shared public prose alias.

A revision association records that the caller associates one immutable
`S1.P01`-rooted `GitCommitIdentity` with one repair candidate. The commit
identity is reused whole and intrinsically, so nothing about where that commit
lives is claimed: the association does not assert that the revision belongs to
the report's repository, is reachable there, is a pull-request head, is a merge
revision, was applied, was deployed, fixed the fault, passed any test, is
complete, or is the only revision for the candidate. No repository-membership,
role, head, merge, applied, or fixed field exists.

A change-set association records that the caller associates one already valid
bounded `S1.P05` `PullRequestChangeSet` with one repair candidate. This is the
Slice that deliberately consumes that value, and consuming it changes nothing
about it: the embedded change set keeps exactly its published meaning, which is
one pull request's base and head bindings, its one to 4096 supplied changed
paths in the caller's supplied order, its distinct base and head revisions, its
single hash algorithm, and its unique paths. It does not become a complete diff
or a verified repair by being associated here. The association asserts neither
that every path relevant to the repair is present, nor that every path in the set
is affected by the fault, nor that the head revision fixes anything, nor that the
pull request merged, nor that a merge was correct, nor that the changed paths are
evidence, nor that base-side blobs are known, nor that the set is
provider-complete.

The `S1.P05.S07` evidence boundary is untouched. `PullRequestChangeSet` remains
excluded from `PullRequestHistoryFactEvidenceLink` and from the
`S1.P06.S04` `FaultReportHistoryFactAssociation`, because no retained record
establishes its completeness; it is admitted here under a different relation
whose meaning is a repair proposal's supplied material rather than a history fact
or an evidence association. Nothing in this module reaches the evidence layer,
and no evidence record, support, source, origin, rationale source, confidence, or
review field exists on any of these models.

A candidate, a revision, a change set, and a pull request are four different
things and none of them is an identity of another. A pull request may contain one
candidate, several, unrelated changes, or no valid repair at all. A commit may
implement all, part, or none of a candidate. A change set describes supplied
changes between one pull request's base and head; it is not the candidate, and
the candidate is not the pull request.

Each association is an independent supplied value and no coherence calculus over
several of them exists. If a caller supplies both a revision association and a
change-set association for one candidate, this layer does not require the
associated revision to equal the change set's head revision: the revision may be
an intermediate one, the head, a later one, or any other commit the caller chose
to associate. Nor is a candidate change set's pull-request repository required to
equal the report's repository context. No value here has the aggregate authority
to say which associations together form one complete candidate record, and
inventing one would be `S1.P06.S08` work on bounded `FaultInstance` composition
and reference integrity.

Multiplicity is expressed by holding several values rather than by any collection
published here. One report may carry several candidates whose identities differ,
and their repair statements may read identically without merging them, because
identical prose is not identity. One candidate may carry several revision
associations and several change-set associations. One revision, and one change
set, may be associated with candidates belonging to different fault reports,
which merges neither the candidates nor the fault subjects. No collection,
ordering, uniqueness rule, registry, precedence, or completeness claim over
several associations exists.

`S1.P06.S05` adds no candidate-to-source-object relation. `S1.P06.S04` already
publishes weak report-to-source and report-to-history associations, and candidate
provenance belongs to later evidence and composition work. In particular, a
report associated with a pull request and a candidate associated with a change
set drawn from that same pull request compose into no third claim: there is no
transitivity rule here, and neither association supports the other.

Every model-valued immediate child position is closed to untyped Python input. A
caller must supply an already typed value; a raw UUID, a string, a mapping, an
attribute-backed lookalike, or a foreign model is refused even when its scalar
content matches, because constructing a published identity, report, commit
identity, or change set is that value's own responsibility and not its consumer's.
A top-level mapping validated with `from_attributes=True` does not bypass those
guards. JSON is a different input language: there the declared child schemas
reconstruct the typed values normally, so a semantic JSON round trip succeeds
while a Python round trip through `model_dump` deliberately does not, and each
embedded value is revalidated under its own published schema so a tampered child
is refused at its own position. The raw text field carries no such nominal guard;
its rules are content rules.

That closure is stated over the declared default validation policy, as every
published module here states it. Deliberately relaxing the policy is a different
question this module does not answer: `strict=False`, an altered `extra` setting,
a schema or serializer override, and the string-parsing entry point are not entry
points designed here, and no guarantee above is offered for them.

The module performs no I/O. It reads no clock, allocates no identifier, consults
no registry or environment, resolves nothing, and never inspects a repository, a
commit, or a pull request.
"""

import uuid
from typing import Annotated

from pydantic import (
    BaseModel,
    ConfigDict,
    RootModel,
    StringConstraints,
    ValidationInfo,
    field_validator,
)

from faultatlas.domain.fault import SuppliedFaultReport
from faultatlas.domain.history import PullRequestChangeSet
from faultatlas.domain.revision import GitCommitIdentity

__all__ = [
    "FaultRepairCandidateIdentity",
    "SuppliedFaultRepairCandidate",
    "FaultRepairCandidateRevisionAssociation",
    "FaultRepairCandidateChangeSetAssociation",
]


class FaultRepairCandidateIdentity(RootModel[uuid.UUID]):
    """Caller-assigned name for one proposed repair-candidate subject."""

    model_config = ConfigDict(
        frozen=True,
        strict=True,
        revalidate_instances="always",
        validate_default=True,
    )

    root: uuid.UUID


class SuppliedFaultRepairCandidate(BaseModel):
    """Supplied repair proposal for one already published fault report."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        strict=True,
        revalidate_instances="always",
        validate_default=True,
    )

    candidate: FaultRepairCandidateIdentity
    report: SuppliedFaultReport
    repair_statement: Annotated[
        str,
        StringConstraints(min_length=1, max_length=4096),
    ]

    @field_validator("candidate", mode="before")
    @classmethod
    def _require_typed_python_candidate(
        cls,
        value: object,
        info: ValidationInfo,
    ) -> object:
        if info.mode == "python" and not isinstance(
            value,
            FaultRepairCandidateIdentity,
        ):
            raise ValueError(
                "candidate must be a FaultRepairCandidateIdentity in Python input"
            )
        return value

    @field_validator("report", mode="before")
    @classmethod
    def _require_typed_python_report(
        cls,
        value: object,
        info: ValidationInfo,
    ) -> object:
        if info.mode == "python" and not isinstance(value, SuppliedFaultReport):
            raise ValueError("report must be a SuppliedFaultReport in Python input")
        return value

    @field_validator("repair_statement", mode="after")
    @classmethod
    def _require_unpadded_text(cls, value: str, info: ValidationInfo) -> str:
        if value != value.strip():
            raise ValueError(
                f"{info.field_name} must not have leading or trailing whitespace"
            )
        return value


class FaultRepairCandidateRevisionAssociation(BaseModel):
    """Supplied association from one repair candidate to one commit revision."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        strict=True,
        revalidate_instances="always",
        validate_default=True,
    )

    candidate: SuppliedFaultRepairCandidate
    revision: GitCommitIdentity

    @field_validator("candidate", mode="before")
    @classmethod
    def _require_typed_python_candidate(
        cls,
        value: object,
        info: ValidationInfo,
    ) -> object:
        if info.mode == "python" and not isinstance(
            value,
            SuppliedFaultRepairCandidate,
        ):
            raise ValueError(
                "candidate must be a SuppliedFaultRepairCandidate in Python input"
            )
        return value

    @field_validator("revision", mode="before")
    @classmethod
    def _require_typed_python_revision(
        cls,
        value: object,
        info: ValidationInfo,
    ) -> object:
        if info.mode == "python" and not isinstance(value, GitCommitIdentity):
            raise ValueError("revision must be a GitCommitIdentity in Python input")
        return value


class FaultRepairCandidateChangeSetAssociation(BaseModel):
    """Supplied association from one repair candidate to one PR change set."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        strict=True,
        revalidate_instances="always",
        validate_default=True,
    )

    candidate: SuppliedFaultRepairCandidate
    change_set: PullRequestChangeSet

    @field_validator("candidate", mode="before")
    @classmethod
    def _require_typed_python_candidate(
        cls,
        value: object,
        info: ValidationInfo,
    ) -> object:
        if info.mode == "python" and not isinstance(
            value,
            SuppliedFaultRepairCandidate,
        ):
            raise ValueError(
                "candidate must be a SuppliedFaultRepairCandidate in Python input"
            )
        return value

    @field_validator("change_set", mode="before")
    @classmethod
    def _require_typed_python_change_set(
        cls,
        value: object,
        info: ValidationInfo,
    ) -> object:
        if info.mode == "python" and not isinstance(value, PullRequestChangeSet):
            raise ValueError(
                "change_set must be a PullRequestChangeSet in Python input"
            )
        return value
