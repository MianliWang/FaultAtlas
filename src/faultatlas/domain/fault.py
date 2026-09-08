"""Caller-designated fault identity, report, scenario, and occurrence claim.

This module opens the FaultInstance model with the two values every later
fault-instance concept needs before any of them can be expressed: a name for
the fault subject a caller is talking about, and the repository context in
which that caller places it. It then adds the first small fault-knowledge
record built from them: a caller-designated report identity carrying one such
context together with the caller's own problem statement and behavioral
deviation text. It then adds the first case-local context layer over that
report, which answers two separate questions: under what supplied conditions
the report is relevant, and what distinct supplied occurrence, if any, the
caller claims under those conditions. Nothing else is decided here.

A fault instance identity names a FaultAtlas knowledge subject and nothing
more. Its caller assigns the identifier; the value is a name, not a finding.
Naming a subject does not establish that a real-world fault exists, that one
was observed, reproduced, verified, diagnosed, or repaired, or that the subject
is anything more than suspected. Two identities being different does not mean
two different defects, and two callers agreeing on one identity does not make
their subjects the same defect: same-defect and different-defect equivalence is
a judgement this layer never makes.

Assignment and collision are the caller's responsibility. The value model sees
one identifier at a time and cannot detect two independent callers that reused
one UUID, so equal assigned identifiers are equal within this contract and no
repository, tenant, or installation namespace is silently added to separate
them. No allocator is published: nothing here generates, derives, or reserves
an identifier, and no identifier is derived from content, so an identity is
never a digest of the fault it names. An identity is not an authorization
token, a capability, or a security boundary, and carries no secrecy claim.

No Issue, pull request, acquisition run, or evidence-record identity is
converted into a fault identity, and no fault identity is looked up, matched,
deduplicated, aliased, merged, or resolved to a source object. The retained
case material supplies no historical fault-instance identifier, so every
identifier in this contract is supplied by a caller.

The identifier is a UUID as the locked ordinary UUID validator admits it,
including the Nil and Max UUIDs. Neither is a missing, unknown, absent, or
tombstone sentinel here: a caller that assigns one has named a subject with it
like any other. No generation version is required and none is inferred, so no
time, ordering, node, or randomness property may be read out of an identity.

Repository context is separate from logical fault identity, which is why it is
a second value rather than a field. A caller may place one fault subject in
several repository contexts, and may place several fault subjects in one
repository. Doing so asserts only the placement: a context does not claim that
the repository is affected, causal, owning, responsible, the site of a repair,
or one the fault applies to; it claims no commit, revision, path, or snapshot
membership, no verified fault, no root cause, no successful reproduction, no
repair, no repair correctness, and no evidence support. Absence of a context
asserts nothing either, and no ordering, primacy, role, completeness, or
cross-repository deduplication over several contexts exists here.

A report identity names one caller-designated supplied-report record and
nothing more. It is a second, independent UUID-rooted value rather than a
subclass or alias of the fault identity, because a report is not the fault it
is about: the two remain nominally distinct even when their scalars happen to
coincide, and nothing requires the scalars to differ. Everything said above
about assignment, collision, allocation, admission breadth, the absence of a
generation-version promise, and the absence of any security meaning applies to
the report identity unchanged. It is not an external Issue, comment, or
provider identity, not an evidence-record or run identity, and not a digest.
Equality of two report identities is equality of the assigned value within
this contract; it does not establish that two independently supplied
real-world reports are one source report, and no collision or global
uniqueness policy is implemented here.

A supplied fault report binds one report identity to one repository context
and to two pieces of caller text: a concise problem statement saying what is
wrong or suspected, and a behavioral-deviation statement saying what
behavioral difference or risk is relevant. The context is consumed whole, so
the fault subject of a report is `report.context.fault`; no fault, repository,
provider, repository identifier, or schema version is restated at report
level, and no second fault field exists to fall out of step with the context.
Creating a report means only that the caller supplied this identity, placed
its fault subject in this context, and supplied these two texts. A report may
describe a suspected, latent, unreproduced, unfixed, or cause-unknown problem.
It does not imply that the repository is affected, that the fault exists, that
the deviation was executed or observed, that an external reporter said these
words, that the report came from a particular Issue or pull request, that
FaultAtlas verified anything, that a cause is known, that a repair exists or is
correct, that a before-run failed or an after-run passed, that an expected
property has been reviewed, or that the report is evidence-backed.

Every supplied text in this module is a claim and is handled as opaque prose,
under one shared rule stated separately on each field rather than through a
shared alias or base. Each must be present, non-blank, and at most 4096
characters; leading or trailing whitespace is refused rather than trimmed, so
whitespace-only text fails, and a value that cannot encode as UTF-8 is refused.
Admitted Unicode and interior whitespace, including newlines, are preserved
exactly: nothing here lowercases, normalizes, parses, tokenizes, classifies, or
rewrites the text, and nothing decides whether it is true, substantive, causal,
or technically correct. No two of these texts are required to differ, and none
of them is compared with another, so a caller may legitimately repeat one
statement across fields. The deviation text may describe differences in returned
values, exceptions, side-effect count or ordering, callback or event ordering,
resource or timing behavior, or any combination, and no closed deviation-kind
vocabulary is published to classify it. The 4096 limit is a character bound of
this internal supplied-text contract, not a durable byte-format promise.

A scenario identity names one caller-designated case-local scenario subject,
and an occurrence identity names one caller-designated fault-occurrence
subject. Each is a further independent UUID-rooted value, neither a subclass
nor an alias of the others, and everything said above about assignment,
collision, allocation, admission breadth, the absence of a generation-version
promise, and the absence of any security meaning applies to both unchanged.
Nothing requires the scalars of two nominally different identities to differ,
and two identities of different types are never equal because their scalars
coincide. An occurrence identity is not a test-run identity, a CI run, a
provider event, an evidence record, a timestamp, or a digest.

A supplied scenario ties one scenario identity to one complete supplied report
value and to one case-local scenario statement. It says only that the caller
supplies those three things. A scenario describes conditions, setting,
trigger, input shape, operation, configuration, state, or environment under
which the caller considers the report relevant; it does not state that those
conditions hold, that the fault occurred under them, that the fault applies
whenever they hold, or that another scenario whose prose reads the same is the
same scenario. The statement is opaque supplied prose, not a structured
applicability rule: nothing here parses it into platform, language, operating
system, version, architecture, trigger, input, or environment fields, and
reusable cross-instance applicability is later work.

A supplied occurrence context adds one occurrence identity, the scenario it
belongs under, and the caller's description of one particular claimed
manifestation. It is a positive caller claim that this manifestation was
encountered under that scenario, and nothing more. It does not establish that
FaultAtlas observed or reproduced anything, that a test was run, that code was
executed, that an output was collected, that an exception happened in a
FaultAtlas-controlled process, that the report was proven, that the scenario
was exhaustively specified, that a cause is known, that a repair works, or
that evidence supports the claim. Test material, run identity, reported
execution outcome, before-and-after comparison, timeout, environment-start,
flakiness, independence of runs, and fail-to-pass or regression-safety
semantics are all later work, so no run, attempt, execution, exit-code,
output, pass, fail, timeout, flaky, before, after, reproduction-status, or
independently-verified field exists here. Two occurrence identities differing
is not evidence that two independent runs happened; they are caller-assigned
occurrence subjects.

Occurrence is deliberately an optional separate record rather than a flag on a
scenario. A report may stand alone, may carry one scenario or several, and a
scenario may carry no occurrence, one, or several; a suspected, latent, or
unreproduced fault therefore never has to invent an occurrence to be
expressed. No boolean says whether the fault occurred. The absence of an
occurrence record means only that no occurrence record is present in this
composition: it does not mean the fault is known not to have occurred, that
occurrence is impossible, inapplicable, unavailable, or disproved, and no
sentinel, status, or `None` stands for any of those.

No time is recorded for a claimed occurrence. A fault occurrence may have no
known precise instant, and forcing a fabricated one to construct a record
would be worse than omitting it, so no occurred-at, observed-at, reported-at,
reproduced-at, started-at, or ended-at field exists. The published `S1.P05`
`PullRequestHistoricalOccurrenceTime` is a source instant for an already
published pull-request history fact and is neither reused, imported, aliased,
nor reinterpreted here; it is not a generic fault-occurrence time. A positive
chronology relation is later work that needs a concrete consumer and explicit
missing-state semantics first.

Two records carrying one scenario or occurrence identity with different
contents cannot be reconciled here. These are value models with no aggregate,
registry, or persistence authority: none of them looks another record up,
deduplicates, merges, or chooses a winner, so two scenarios whose statements
read identically stay two scenarios, two occurrences whose contexts read
identically stay two occurrences, and any conflict is left visible for a later
composition or review layer to surface.

An identity paired with a repository, a report over that pairing, or a
scenario and occurrence claim over that report, is not yet a complete fault
instance. A source relationship, repair candidate, test material, reported
outcome, explanation, hypothesis, expected property, evidence bridge,
confidence or review state, reusable pattern or invariant, and the composition
that binds them are later work and are deliberately absent rather than
reserved. No source association and no evidence association is created by a
report, a scenario, or an occurrence context.

The repository position reuses the published `S1.P01` `RepositoryIdentity`
whole, with its own child validation and its own schema version. The context
restates no provider, repository identifier, alias, or schema version of its
own, because the embedded value already publishes them.

Every model-valued immediate child position is closed to untyped Python input.
A caller must supply an already typed value; a raw UUID, a string, a mapping,
an attribute-backed lookalike, or a foreign model is refused even when its
scalar content matches, because constructing a published identity or relation
is that value's own responsibility and not its consumer's. JSON input is a
different language: there the declared child schemas reconstruct the typed
values normally, so a context's, a report's, a scenario's, or an occurrence
context's JSON round trip succeeds while a Python round trip through
`model_dump` deliberately does not. That holds for a whole embedded record as
much as for a scalar identity: a scenario admits an already typed supplied
report and an occurrence context an already typed supplied scenario, and each
embedded value is revalidated under its own published schema, so a tampered
child is refused at its own position. The raw text fields carry no such
nominal guard; their rules are content rules.

That closure is stated over the declared default validation policy, and the
guards test Python mode explicitly, as every published module here does.
Deliberately relaxing the policy is a different question this module does not
answer: `strict=False`, an altered `extra` setting, a schema or serializer
override, and the string-parsing entry point are not entry points designed
here, and no guarantee above is offered for them. The string-parsing mode in
particular is neither Python nor JSON input, so a caller that reaches for it
leaves the language this contract describes. Narrowing that third mode is a
repository-wide question about the shared validator idiom rather than a
property of this module, and it is deliberately not decided by one module
diverging from the published surface.

Raw identity JSON, for the fault, report, scenario, and occurrence identities
alike, is a bare UUID string and is not self-describing. Interchange that must
distinguish one UUID-rooted identity from another needs an explicit owning
field or a discriminator supplied by the carrier; no tagged envelope, wrapper
object, or union is published here. There is likewise no `{"root": ...}`,
`{"fault_id": ...}`, `{"report_id": ...}`, `{"scenario_id": ...}`, or
`{"occurrence_id": ...}` JSON form and no adapter for one.

The module performs no I/O. It reads no clock, allocates no identifier,
consults no registry or environment, and resolves nothing.
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

from faultatlas.domain.identity import RepositoryIdentity

__all__ = [
    "FaultInstanceIdentity",
    "FaultRepositoryContext",
    "FaultReportIdentity",
    "SuppliedFaultReport",
    "FaultScenarioIdentity",
    "FaultOccurrenceIdentity",
    "SuppliedFaultScenario",
    "SuppliedFaultOccurrenceContext",
]


class FaultInstanceIdentity(RootModel[uuid.UUID]):
    """Caller-assigned name for one possibly suspected fault subject."""

    model_config = ConfigDict(
        frozen=True,
        strict=True,
        revalidate_instances="always",
        validate_default=True,
    )

    root: uuid.UUID


class FaultRepositoryContext(BaseModel):
    """Supplied placement of one fault subject in one repository."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        strict=True,
        revalidate_instances="always",
        validate_default=True,
    )

    fault: FaultInstanceIdentity
    repository: RepositoryIdentity

    @field_validator("fault", mode="before")
    @classmethod
    def _require_typed_python_fault(
        cls,
        value: object,
        info: ValidationInfo,
    ) -> object:
        if info.mode == "python" and not isinstance(value, FaultInstanceIdentity):
            raise ValueError("fault must be a FaultInstanceIdentity in Python input")
        return value

    @field_validator("repository", mode="before")
    @classmethod
    def _require_typed_python_repository(
        cls,
        value: object,
        info: ValidationInfo,
    ) -> object:
        if info.mode == "python" and not isinstance(value, RepositoryIdentity):
            raise ValueError("repository must be a RepositoryIdentity in Python input")
        return value


class FaultReportIdentity(RootModel[uuid.UUID]):
    """Caller-assigned name for one supplied fault-report record."""

    model_config = ConfigDict(
        frozen=True,
        strict=True,
        revalidate_instances="always",
        validate_default=True,
    )

    root: uuid.UUID


class SuppliedFaultReport(BaseModel):
    """Caller-supplied report of a fault subject placed in one repository."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        strict=True,
        revalidate_instances="always",
        validate_default=True,
    )

    report: FaultReportIdentity
    context: FaultRepositoryContext
    problem_statement: Annotated[
        str,
        StringConstraints(min_length=1, max_length=4096),
    ]
    behavioral_deviation: Annotated[
        str,
        StringConstraints(min_length=1, max_length=4096),
    ]

    @field_validator("report", mode="before")
    @classmethod
    def _require_typed_python_report(
        cls,
        value: object,
        info: ValidationInfo,
    ) -> object:
        if info.mode == "python" and not isinstance(value, FaultReportIdentity):
            raise ValueError("report must be a FaultReportIdentity in Python input")
        return value

    @field_validator("context", mode="before")
    @classmethod
    def _require_typed_python_context(
        cls,
        value: object,
        info: ValidationInfo,
    ) -> object:
        if info.mode == "python" and not isinstance(value, FaultRepositoryContext):
            raise ValueError("context must be a FaultRepositoryContext in Python input")
        return value

    @field_validator("problem_statement", "behavioral_deviation", mode="after")
    @classmethod
    def _require_unpadded_text(cls, value: str, info: ValidationInfo) -> str:
        if value != value.strip():
            raise ValueError(
                f"{info.field_name} must not have leading or trailing whitespace"
            )
        return value


class FaultScenarioIdentity(RootModel[uuid.UUID]):
    """Caller-assigned name for one case-local supplied scenario subject."""

    model_config = ConfigDict(
        frozen=True,
        strict=True,
        revalidate_instances="always",
        validate_default=True,
    )

    root: uuid.UUID


class FaultOccurrenceIdentity(RootModel[uuid.UUID]):
    """Caller-assigned name for one claimed fault-occurrence subject."""

    model_config = ConfigDict(
        frozen=True,
        strict=True,
        revalidate_instances="always",
        validate_default=True,
    )

    root: uuid.UUID


class SuppliedFaultScenario(BaseModel):
    """Supplied case-local conditions under which one report is relevant."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        strict=True,
        revalidate_instances="always",
        validate_default=True,
    )

    scenario: FaultScenarioIdentity
    report: SuppliedFaultReport
    scenario_statement: Annotated[
        str,
        StringConstraints(min_length=1, max_length=4096),
    ]

    @field_validator("scenario", mode="before")
    @classmethod
    def _require_typed_python_scenario(
        cls,
        value: object,
        info: ValidationInfo,
    ) -> object:
        if info.mode == "python" and not isinstance(value, FaultScenarioIdentity):
            raise ValueError("scenario must be a FaultScenarioIdentity in Python input")
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

    @field_validator("scenario_statement", mode="after")
    @classmethod
    def _require_unpadded_text(cls, value: str, info: ValidationInfo) -> str:
        if value != value.strip():
            raise ValueError(
                f"{info.field_name} must not have leading or trailing whitespace"
            )
        return value


class SuppliedFaultOccurrenceContext(BaseModel):
    """Supplied claim of one manifestation encountered under one scenario."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        strict=True,
        revalidate_instances="always",
        validate_default=True,
    )

    occurrence: FaultOccurrenceIdentity
    scenario: SuppliedFaultScenario
    occurrence_context: Annotated[
        str,
        StringConstraints(min_length=1, max_length=4096),
    ]

    @field_validator("occurrence", mode="before")
    @classmethod
    def _require_typed_python_occurrence(
        cls,
        value: object,
        info: ValidationInfo,
    ) -> object:
        if info.mode == "python" and not isinstance(value, FaultOccurrenceIdentity):
            raise ValueError(
                "occurrence must be a FaultOccurrenceIdentity in Python input"
            )
        return value

    @field_validator("scenario", mode="before")
    @classmethod
    def _require_typed_python_scenario(
        cls,
        value: object,
        info: ValidationInfo,
    ) -> object:
        if info.mode == "python" and not isinstance(value, SuppliedFaultScenario):
            raise ValueError("scenario must be a SuppliedFaultScenario in Python input")
        return value

    @field_validator("occurrence_context", mode="after")
    @classmethod
    def _require_unpadded_text(cls, value: str, info: ValidationInfo) -> str:
        if value != value.strip():
            raise ValueError(
                f"{info.field_name} must not have leading or trailing whitespace"
            )
        return value
