"""Caller-designated fault identity, repository context, and supplied report.

This module opens the FaultInstance model with the two values every later
fault-instance concept needs before any of them can be expressed: a name for
the fault subject a caller is talking about, and the repository context in
which that caller places it. It then adds the first small fault-knowledge
record built from them: a caller-designated report identity carrying one such
context together with the caller's own problem statement and behavioral
deviation text. Nothing else is decided here.

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

Both texts are supplied claims and are handled as opaque prose. Each must be
present, non-blank, and at most 4096 characters; leading or trailing whitespace
is refused rather than trimmed, so whitespace-only text fails, and a value that
cannot encode as UTF-8 is refused. Admitted Unicode and interior whitespace,
including newlines, are preserved exactly: nothing here lowercases, normalizes,
parses, tokenizes, classifies, or rewrites the text, and nothing decides
whether it is true, substantive, causal, or technically correct. The two texts
may be identical. The deviation text may describe differences in returned
values, exceptions, side-effect count or ordering, callback or event ordering,
resource or timing behavior, or any combination, and no closed deviation-kind
vocabulary is published to classify it. The 4096 limit is a character bound of
this internal supplied-text contract, not a durable byte-format promise.

An identity paired with a repository, or a report over that pairing, is not
yet a complete fault instance. An occurrence, scenario, source relationship,
repair candidate, test material, reported outcome, explanation, hypothesis,
expected property, evidence bridge, confidence or review state, and the
composition that binds them are later work and are deliberately absent rather
than reserved. No source association and no evidence association is created
by a report.

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
values normally, so a context's or a report's JSON round trip succeeds while a
Python round trip through `model_dump` deliberately does not. The raw text
fields carry no such nominal guard; their rules are content rules.

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

Raw identity JSON, for the fault identity and the report identity alike, is a
bare UUID string and is not self-describing. Interchange that must distinguish
one UUID-rooted identity from another needs an explicit owning field or a
discriminator supplied by the carrier; no tagged envelope, wrapper object, or
union is published here. There is likewise no `{"root": ...}`,
`{"fault_id": ...}`, or `{"report_id": ...}` JSON form and no adapter for one.

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
