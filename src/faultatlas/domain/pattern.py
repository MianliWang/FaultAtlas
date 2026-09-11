"""Caller-supplied pattern identity and one proposed cross-instance pattern.

This module opens the Pattern & Invariant model with the smallest thing the
later layers need before any of them can be expressed: a name for the pattern
subject a caller is talking about, and the caller's own statement of what that
pattern is. Nothing else is decided here.

A pattern identity names a proposed FaultAtlas pattern subject and nothing
more. Its caller assigns the identifier; the value is a name, not a finding.
Naming a subject does not establish that a pattern is real, that it recurs,
that it generalizes, that it is reusable, or that it is correct. Two identities
being different does not mean two different patterns, and two callers agreeing
on one identity does not make their subjects the same pattern: same-pattern and
different-pattern equivalence is a judgement this layer never makes.

Assignment and collision are the caller's responsibility. The value model sees
one identifier at a time and cannot detect two independent callers that reused
one UUID, so equal assigned identifiers are equal within this contract and no
repository, tenant, or installation namespace is silently added to separate
them. No allocator is published: nothing here generates, derives, or reserves
an identifier. Nothing is derived from a `FaultInstance`, from prose
similarity, or from an expected property, and no identifier is derived from
content, so an identity is never a hash, digest, or canonical pattern key of
the pattern it names. An identity is not an authorization token, a capability,
or a security boundary, and carries no secrecy claim.

The identifier is a UUID as the locked ordinary UUID validator admits it,
including the Nil and Max UUIDs. Neither is a missing, unknown, absent, or
tombstone sentinel here: a caller that assigns one has named a subject with it
like any other. No generation version is required and none is inferred, so no
time, ordering, node, or randomness property may be read out of an identity.

The identity is nominally distinct from every published `S1.P06` identity. It
is a separate `RootModel[uuid.UUID]` rather than a subclass or alias of any of
them, so a fault, report, scenario, occurrence, repair-candidate, test-material,
run, explanation, hypothesis or expected-property identity is never equal to a
pattern identity, and nothing requires their scalars to differ. One UUID scalar
may therefore inhabit a pattern identity and a `S1.P06` identity at once,
exactly as the published identities already allow among themselves. Nominal
distinctness is an equality property, not a hashing one: unequal nominal
identities are not required to hash differently, and a caller that mixes
identity types in one set or mapping is relying on equality, which separates
them.

A supplied pattern binds one pattern identity to one piece of caller text: a
statement of the reusable or recurring abstraction the caller intends to
describe across fault instances. Creating one means only that the caller
supplied this identity and this text. The claim is deliberately weak. It does
not establish recurrence, that more than one example exists, that any two fault
instances are similar, that the abstraction is general or universal, that it is
an invariant, that it is true, where it applies, that it transfers anywhere,
that any evidence supports it, any confidence in it, any review of it, that it
is correct, that it names a root cause, or that a repair derived from it is
correct.

A pattern may therefore be represented before its caller supplies any
`FaultInstance` exemplar relationship at all, and that is the intended state
rather than an incomplete one. Constructing one means `proposed pattern with no
exemplars supplied yet`, never `verified cross-instance pattern`. No exemplar is
required, two fault instances are not required, and no instance relationship is
inferred from the statement text. Associating a pattern with a `FaultInstance`
is later `S1.P07` work and is deliberately absent rather than reserved, so no
fault, fault-instance, instance, example, exemplar, member, or source field
exists here.

Pattern identity and pattern statement stay two separate things. Two pattern
identities may carry identical prose and remain two distinct records, and two
separately constructed records may reuse one pattern identity while carrying
different supplied statements. Neither case is reconciled here: this is a value
model with no aggregate, registry, or persistence authority, so nothing looks
another record up, deduplicates, merges, replaces, supersedes, or chooses a
winner, and a conflicting pattern claim is left visible for a later layer.

The supplied text is a claim and is handled as opaque prose. It must be
present, non-blank, and at most 4096 characters; leading or trailing whitespace
is refused rather than trimmed, so whitespace-only text fails, and a value that
cannot encode as UTF-8 is refused. Admitted Unicode and interior whitespace,
including newlines, are preserved exactly: nothing here lowercases, normalizes,
parses, tokenizes, embeds, classifies, clusters, or rewrites the text, and
nothing decides whether it is true, substantive, general, or technically
correct. The 4096 limit is a character bound of this internal supplied-text
contract, not a durable byte-format promise.

The case-local `S1.P06.S07` `SuppliedFaultExpectedProperty` is neither imported,
aliased, reinterpreted, nor promoted by anything here. It remains what it was
published as, scoped to one report, and this module does not make it an
invariant. Invariants have no representation yet. Applicability and transfer
remain `S1.P08` work, generic confidence and review remain `S1.P09` work, and
durable serialization and persistence remain `S1.P10` work, so no scope,
applies-to, applicability, transfer, similarity, confidence, support, proof,
verification, review, status, probability, canonical, or universal field exists,
and no `PatternKind`, `RelationshipKind`, `PatternStatus`, `PatternScope`,
similarity score, or clustering metadata is published.

Dependency direction is downstream only. This module imports no published
`S1.P06` record, and no `S1.P06` record imports or references it, so nothing
already published changes meaning because this module now exists.

The pattern position is closed to untyped Python input. A caller must supply an
already typed `FaultPatternIdentity`; a bare UUID, a string, a mapping, an
attribute-backed lookalike, or a foreign model is refused even when its scalar
content matches, because constructing a published identity is that value's own
responsibility and not its consumer's. A `RootModel` field reconstructs from its
own root type even under `strict=True`, so without that guard the record would
be minting the identity rather than composing one a caller already published.
JSON input is a different language: there the declared child schema reconstructs
the typed value normally, so a JSON round trip succeeds while a Python round
trip through `model_dump` deliberately does not. The raw text field carries no
such nominal guard; its rules are content rules.

That closure is stated over the declared default validation policy, and the
guards test Python mode explicitly, as every published module here does.
Deliberately relaxing the policy is a different question this module does not
answer: `strict=False`, an altered `extra` setting, a schema or serializer
override, and the string-parsing entry point are not entry points designed
here, and no guarantee above is offered for them.

Raw identity JSON is a bare UUID string and is not self-describing. Interchange
that must distinguish one UUID-rooted identity from another needs an explicit
owning field or a discriminator supplied by the carrier; no tagged envelope,
wrapper object, or union is published here, and there is no `{"root": ...}` or
`{"pattern_id": ...}` JSON form and no adapter for one.

The module performs no I/O. It reads no clock, no environment and no
filesystem, opens no network connection, consults no registry, allocates no
identifier, resolves nothing, starts no process, calls no model, computes no
embedding, runs no similarity search or clustering, and extracts no pattern
from anything.
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

__all__ = [
    "FaultPatternIdentity",
    "SuppliedFaultPattern",
]


class FaultPatternIdentity(RootModel[uuid.UUID]):
    """Caller-assigned name for one proposed cross-instance pattern subject."""

    model_config = ConfigDict(
        frozen=True,
        strict=True,
        revalidate_instances="always",
        validate_default=True,
    )

    root: uuid.UUID


class SuppliedFaultPattern(BaseModel):
    """Caller-supplied proposition of one reusable or recurring abstraction."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        strict=True,
        revalidate_instances="always",
        validate_default=True,
    )

    pattern: FaultPatternIdentity
    pattern_statement: Annotated[
        str,
        StringConstraints(min_length=1, max_length=4096),
    ]

    @field_validator("pattern", mode="before")
    @classmethod
    def _require_typed_python_pattern(
        cls,
        value: object,
        info: ValidationInfo,
    ) -> object:
        if info.mode == "python" and not isinstance(value, FaultPatternIdentity):
            raise ValueError("pattern must be a FaultPatternIdentity in Python input")
        return value

    @field_validator("pattern_statement", mode="after")
    @classmethod
    def _require_unpadded_text(cls, value: str, info: ValidationInfo) -> str:
        if value != value.strip():
            raise ValueError(
                f"{info.field_name} must not have leading or trailing whitespace"
            )
        return value
