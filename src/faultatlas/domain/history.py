"""Binding from one pull request to one revision it records in a given role.

This module supplies the context that the published revision-role assignment
deliberately leaves open. `RevisionRoleAssignment` names a role that is
context-relative — a commit is a `base` or a `head` only with respect to
something — but it carries no context of its own. A binding here states the
missing side: the pull request with respect to which the assignment holds.

Both positions are published predecessor values, embedded whole. The subject
is the `S1.P01` `NumberedSourceObjectIdentity`, which already is the canonical
identity of one repository-scoped Issue or Pull Request; no development
subject identity is defined, aliased, wrapped, or subclassed here. The object
is the `S1.P02` `RevisionRoleAssignment`, which already pairs one role with
one immutable commit identity; neither the role nor the revision is restated.
The binding contributes exactly one edge and nothing else, so its own JSON
carries exactly two keys and no schema version, each embedded value keeping
the version it publishes.

The subject position is a pull request only. An Issue is a valid numbered
source object but has no base or head revision, so admitting one would make an
unwitnessable state constructible. The role is narrowed to `base` and `head`,
the two roles a pull request itself records. A merge commit and a merge first
parent are reached through merge and topology semantics rather than recorded
on the pull request, and they are not bound here.

A binding is supplied by its caller and asserts only that the caller states
this pull request records this role-assigned revision. It does not claim that
the pull request or the revision exists, is visible, or is reachable, and it
resolves nothing to find out.

In particular the revision is not claimed to reside in the pull request's own
repository. A head revision may be authored in a fork whose repository is
separately observed, absent, or no longer known, and treating the subject's
repository as the revision's would manufacture a containment fact that the
supplied values do not carry. The two positions therefore share no repository
coherence check, and none is implied.

No ref name, branch, or default-branch designation appears here: a recorded
base ref is a mutable-ref observation, and which branch was historically
default is not established by this or any value in this module. No ancestry,
descendance, parent topology, or reachability is expressed; a base and a head
bound to one pull request say nothing about the path between them. No
comparison, diff, or change set is present. No merge, review, approval, or
CI or test-run semantics, no timestamp or chronology, and no relation between
an Issue and a Pull Request are defined. Completeness is not claimed: bindings
carry no notion of how many roles a pull request has, and an absent binding
asserts nothing.

The module is evidence-neutral. No evidence record is referenced, and no claim
is made that any retained acquisition supports, corroborates, or verifies a
binding; record-level evidence association remains exactly where `S1.P04`
placed it. The module performs no I/O: it resolves nothing, reads nothing,
contacts no provider, and defines no durable bytes, reader, writer, or
persistence.
"""

from typing import Self

from pydantic import (
    BaseModel,
    ConfigDict,
    ValidationInfo,
    field_validator,
    model_validator,
)

from faultatlas.domain.identity import (
    NumberedSourceObjectIdentity,
    SourceObjectKind,
)
from faultatlas.domain.revision import RevisionRole, RevisionRoleAssignment

__all__ = [
    "PullRequestRevisionRoleBinding",
]

_PULL_REQUEST_RECORDED_ROLES: frozenset[RevisionRole] = frozenset(
    {
        RevisionRole.BASE,
        RevisionRole.HEAD,
    }
)


class PullRequestRevisionRoleBinding(BaseModel):
    """Supplied binding from one pull request to one role-assigned revision."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        strict=True,
        revalidate_instances="always",
        validate_default=True,
    )

    pull_request: NumberedSourceObjectIdentity
    role_assignment: RevisionRoleAssignment

    @field_validator("pull_request", mode="before")
    @classmethod
    def _require_typed_python_pull_request(
        cls,
        value: object,
        info: ValidationInfo,
    ) -> object:
        if info.mode == "python" and not isinstance(
            value,
            NumberedSourceObjectIdentity,
        ):
            raise ValueError(
                "pull_request must be a NumberedSourceObjectIdentity in Python input"
            )
        return value

    @field_validator("role_assignment", mode="before")
    @classmethod
    def _require_typed_python_role_assignment(
        cls,
        value: object,
        info: ValidationInfo,
    ) -> object:
        if info.mode == "python" and not isinstance(value, RevisionRoleAssignment):
            raise ValueError(
                "role_assignment must be a RevisionRoleAssignment in Python input"
            )
        return value

    @model_validator(mode="after")
    def _require_pull_request_subject(self) -> Self:
        if self.pull_request.kind is not SourceObjectKind.PULL_REQUEST:
            raise ValueError("pull_request must identify a pull_request source object")
        return self

    @model_validator(mode="after")
    def _require_pull_request_recorded_role(self) -> Self:
        if self.role_assignment.role not in _PULL_REQUEST_RECORDED_ROLES:
            raise ValueError("bound revision role must be base or head")
        return self
