"""Caller-designated fault-instance identity and its repository context.

This module opens the FaultInstance model with the two values every later
fault-instance concept needs before any of them can be expressed: a name for
the fault subject a caller is talking about, and the repository context in
which that caller places it. Nothing else is decided here.

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

An identity paired with a repository is not yet a complete fault instance. A
report, deviation, occurrence, scenario, source relationship, repair candidate,
test material, explanation, evidence bridge, and the composition that binds
them are later work and are deliberately absent rather than reserved.

The repository position reuses the published `S1.P01` `RepositoryIdentity`
whole, with its own child validation and its own schema version. The context
restates no provider, repository identifier, alias, or schema version of its
own, because the embedded value already publishes them.

Both immediate child positions are closed to untyped Python input. A caller
must supply an already typed value; a raw UUID, a string, a mapping, an
attribute-backed lookalike, or a foreign model is refused even when its scalar
content matches, because constructing a published identity is that identity's
own responsibility and not this relation's. JSON input is a different language:
there the declared child schemas reconstruct the typed values normally, so a
context's JSON round trip succeeds while a Python round trip through
`model_dump` deliberately does not.

Raw fault-identity JSON is a bare UUID string and is not self-describing.
Interchange that must distinguish this identity from another UUID-rooted
identity needs an explicit owning field or a discriminator supplied by the
carrier; no tagged envelope, wrapper object, or union is published here. There
is likewise no `{"root": ...}` or `{"fault_id": ...}` JSON form and no adapter
for one.

The module performs no I/O. It reads no clock, allocates no identifier,
consults no registry or environment, and resolves nothing.
"""

import uuid

from pydantic import (
    BaseModel,
    ConfigDict,
    RootModel,
    ValidationInfo,
    field_validator,
)

from faultatlas.domain.identity import RepositoryIdentity

__all__ = [
    "FaultInstanceIdentity",
    "FaultRepositoryContext",
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
