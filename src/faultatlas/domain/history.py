"""Supplied pull request revision bindings, change sets, approvals, and merges.

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

A change set carries the two bindings of one pull request together with the
paths its caller supplies as changed between them. The base and head positions
are the published bindings themselves rather than a separate boundary value:
the ordered pair is already exactly what those two bindings express, so no
additional subject is introduced to hold them. Both bindings must name the
same pull request, and each must carry its own role.

One Git object format governs a whole change set: the base revision, the head
revision, and every supplied head object share one hash algorithm, as the
published snapshot path binding and commit parent topology already require of
their own related identities. A change set mixing formats would be internally
contradictory rather than merely unusual.

A changed path names one repository path, one supplied blob identity for that
path on the head side, and one supplied status. The status vocabulary is closed
to `added` and `modified`, the two statuses the retained material supplies. A
removed, renamed, or copied status is absent rather than reserved: no supplied
value describes one, and inventing one would manufacture an object state that
nothing establishes.

Only a head-side object is carried. No blob identity is supplied for the base
side of a changed path, so a change set names what a path is said to hold
afterwards and says nothing about what it held before. File content is not
present in any form: a path entry carries an identity, never bytes, a diff, a
patch, a hunk, or a line.

A change set is bounded and preserves its caller's supplied order exactly. That
order is the supplied order alone and carries no provider, chronological,
lexical, or structural meaning. A repeated path is rejected without sorting,
merging, or deduplication.

At least one changed path is required. An empty collection cannot state that
nothing changed, because this value never expresses completeness, so an empty
change set would say nothing at all while still appearing to be a change
record. Supplying no changed path is therefore not a change set rather than an
empty one.

The base and head revisions must differ. A change set names what its caller
supplies as changed between two revisions, and one revision compared with
itself has no between: such a value could only carry changed paths that
contradict its own endpoints.

Nothing here is completeness. A change set is exactly the paths its caller
supplied, never the paths of a comparison, a commit, or a repository, and a
path that is absent from one is simply not supplied. The module expresses no
merge base, no ahead or behind count, no ancestry, descendance, reachability,
or parent topology, and no repository-snapshot membership or path existence.

A review approval supplies the edge the published review identity leaves open.
The `S1.P00.S07` decision links a pull-request review to its stable repository,
its parent pull request, and the revision it reviewed, and the published
`S1.P01` identity carries the first two inside its parent while carrying no
revision at all. An approval names that missing revision, so the review keeps
its published identity and gains no second one here.

The review position accepts a pull-request review only. The published identity
also spans comments, review comments, and timeline events, so the kind is
restricted here; the parent pull request is not restated, because the published
identity already carries it and already requires it to be a pull request.

The revision is bound directly rather than through a published revision-role
binding. The canonical review approved the revision that is also the recorded
pull-request head, but that coincidence is a derived observation about one
case, not a property of reviews, and a review of an intermediate revision would
be unrepresentable if the head role were required.

An approval is a historical occurrence, not a current state. Its caller states
that this review approved this revision; nothing here states that the approval
still stands, that it was never dismissed or edited, or that the review carries
any present state at all. Complete historical review state is not established
by any retained material, so neither an approval nor its absence describes one.

Approval is the whole of the positive claim, carried by the relation itself
rather than by a state field. The retained material supplies exactly one
approval disposition, so a vocabulary of one member would add nothing, and
naming dispositions that nothing supplies would invent them.

An approval records no submission time, no review body or rationale, and no
reviewer. A body observed to be exactly empty is not an absence of reason, and
occurrence time belongs to bounded chronology rather than to this relation.
Approval here is a provider-observed disposition and never FaultAtlas
confidence, claim acceptance, reviewed interpretation, technical correctness,
test or CI outcome, merge readiness, causation, or proof of repair.

A merge revision outcome names the immutable revision one pull request merged
as. Its caller states that the pull request merged and that this revision is
the result; the revision is bound directly, so no revision role, role
assignment, or parent sequence is restated here.

The outcome is a historical occurrence rather than a present state. Nothing
here reports whether the pull request is currently merged, open, or closed, and
the relation carries no merged flag, disposition, or state vocabulary of any
kind. Only a positive outcome is expressible: an absent outcome is not a
statement that a pull request did not merge, was abandoned, or was closed
without merging, and no vocabulary for those exists.

The merge revision's own parents are not carried. A commit and its exact
ordered parents are already a published revision fact, and restating them here
would duplicate that contract; a caller needing them uses the published
topology value directly. Nothing in an outcome asserts how many parents the
merge revision has, which parent holds which position, or that any particular
revision appears among them.

In particular an outcome asserts no relationship between the merge revision and
the revisions the pull request records in its base or head roles. The recorded
base need not be a parent of the merge revision, nor its ancestor, nor equal to
any parent: an integration branch may advance between the two, and the retained
canonical material is exactly such a case. No merge base, ahead or behind
count, ancestry, descendance, or reachability is expressed or implied, and no
merge strategy is assumed.

An outcome records no merge time, no merge actor, and no relationship to a
review: occurrence time belongs to bounded chronology, and an approval neither
causes nor precedes a merge by anything this relation states. Merging is not
correctness, test or CI outcome, causation, or proof of repair.

The module is evidence-neutral. No evidence record is referenced, and no claim
is made that any retained acquisition supports, corroborates, or verifies a
binding, a change set, an approval, or a merge outcome; record-level evidence association
remains exactly where `S1.P04` placed it, and exact retained comparison bytes
belong to a later association rather than to these values. The module performs no I/O: it
resolves nothing, reads nothing, contacts no provider, and defines no durable
bytes, reader, writer, or persistence.
"""

from enum import StrEnum
from typing import Annotated, Self, cast

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationInfo,
    field_validator,
    model_validator,
)

from faultatlas.domain.identity import (
    NumberedSourceObjectIdentity,
    ProviderScopedSourceObjectIdentity,
    SourceObjectKind,
)
from faultatlas.domain.revision import (
    GitBlobIdentity,
    GitCommitIdentity,
    GitRepositoryPath,
    RevisionRole,
    RevisionRoleAssignment,
)

__all__ = [
    "PullRequestRevisionRoleBinding",
    "ChangedPathStatus",
    "PullRequestChangedPath",
    "PullRequestChangeSet",
    "PullRequestReviewRevisionApproval",
    "PullRequestMergeRevisionOutcome",
]

_MIN_CHANGED_PATHS = 1
_MAX_CHANGED_PATHS = 4096

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


class ChangedPathStatus(StrEnum):
    """Closed vocabulary of supplied changed-path statuses."""

    ADDED = "added"
    MODIFIED = "modified"


class PullRequestChangedPath(BaseModel):
    """One supplied changed path with its head-side object and status."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        strict=True,
        revalidate_instances="always",
        validate_default=True,
    )

    path: GitRepositoryPath
    head_object: GitBlobIdentity
    status: ChangedPathStatus

    @field_validator("path", mode="before")
    @classmethod
    def _require_typed_python_path(
        cls,
        value: object,
        info: ValidationInfo,
    ) -> object:
        if info.mode == "python" and not isinstance(value, GitRepositoryPath):
            raise ValueError("path must be a GitRepositoryPath in Python input")
        return value

    @field_validator("head_object", mode="before")
    @classmethod
    def _require_typed_python_head_object(
        cls,
        value: object,
        info: ValidationInfo,
    ) -> object:
        if info.mode == "python" and not isinstance(value, GitBlobIdentity):
            raise ValueError("head_object must be a GitBlobIdentity in Python input")
        return value


class PullRequestChangeSet(BaseModel):
    """Supplied changed paths between one pull request's base and head."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        strict=True,
        revalidate_instances="always",
        validate_default=True,
    )

    base: PullRequestRevisionRoleBinding
    head: PullRequestRevisionRoleBinding
    changed_paths: Annotated[
        tuple[PullRequestChangedPath, ...],
        Field(min_length=_MIN_CHANGED_PATHS, max_length=_MAX_CHANGED_PATHS),
    ]

    @field_validator("base", "head", mode="before")
    @classmethod
    def _require_typed_python_binding(
        cls,
        value: object,
        info: ValidationInfo,
    ) -> object:
        if info.mode == "python" and not isinstance(
            value,
            PullRequestRevisionRoleBinding,
        ):
            raise ValueError(
                f"{info.field_name} must be a PullRequestRevisionRoleBinding "
                "in Python input"
            )
        return value

    @field_validator("changed_paths", mode="before")
    @classmethod
    def _require_strict_changed_paths(
        cls,
        value: object,
        info: ValidationInfo,
    ) -> object:
        if info.mode == "json" and isinstance(value, list):
            return tuple(cast(list[object], value))
        if info.mode == "python":
            if not isinstance(value, tuple):
                raise ValueError("changed_paths must be a tuple in Python input")
            entries = cast(tuple[object, ...], value)
            if any(not isinstance(entry, PullRequestChangedPath) for entry in entries):
                raise ValueError(
                    "changed_paths must contain PullRequestChangedPath values"
                )
        return cast(object, value)

    @model_validator(mode="after")
    def _require_one_pull_request_and_its_two_roles(self) -> Self:
        if self.base.pull_request != self.head.pull_request:
            raise ValueError("base and head must bind the same pull request")
        if self.base.role_assignment.role is not RevisionRole.BASE:
            raise ValueError("base must carry the base revision role")
        if self.head.role_assignment.role is not RevisionRole.HEAD:
            raise ValueError("head must carry the head revision role")
        if self.base.role_assignment.revision == self.head.role_assignment.revision:
            raise ValueError("base and head must be distinct revisions")
        return self

    @model_validator(mode="after")
    def _require_one_hash_algorithm(self) -> Self:
        algorithm = self.head.role_assignment.revision.algorithm
        if self.base.role_assignment.revision.algorithm is not algorithm:
            raise ValueError("base and head revision algorithms must match")
        if any(
            entry.head_object.algorithm is not algorithm for entry in self.changed_paths
        ):
            raise ValueError(
                "head object algorithms must match the head revision algorithm"
            )
        return self

    @model_validator(mode="after")
    def _require_unique_changed_paths(self) -> Self:
        paths = frozenset(entry.path for entry in self.changed_paths)
        if len(paths) != len(self.changed_paths):
            raise ValueError("changed paths must not repeat a repository path")
        return self


class PullRequestReviewRevisionApproval(BaseModel):
    """Supplied approval of one immutable revision by one pull request review."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        strict=True,
        revalidate_instances="always",
        validate_default=True,
    )

    review: ProviderScopedSourceObjectIdentity
    approved_revision: GitCommitIdentity

    @field_validator("review", mode="before")
    @classmethod
    def _require_typed_python_review(
        cls,
        value: object,
        info: ValidationInfo,
    ) -> object:
        if info.mode == "python" and not isinstance(
            value,
            ProviderScopedSourceObjectIdentity,
        ):
            raise ValueError(
                "review must be a ProviderScopedSourceObjectIdentity in Python input"
            )
        return value

    @field_validator("approved_revision", mode="before")
    @classmethod
    def _require_typed_python_approved_revision(
        cls,
        value: object,
        info: ValidationInfo,
    ) -> object:
        if info.mode == "python" and not isinstance(value, GitCommitIdentity):
            raise ValueError(
                "approved_revision must be a GitCommitIdentity in Python input"
            )
        return value

    @model_validator(mode="after")
    def _require_pull_request_review_subject(self) -> Self:
        if self.review.kind is not SourceObjectKind.PULL_REQUEST_REVIEW:
            raise ValueError("review must identify a pull_request_review object")
        return self


class PullRequestMergeRevisionOutcome(BaseModel):
    """Supplied immutable revision that one pull request merged as."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        strict=True,
        revalidate_instances="always",
        validate_default=True,
    )

    pull_request: NumberedSourceObjectIdentity
    merge_revision: GitCommitIdentity

    @field_validator("pull_request", mode="before")
    @classmethod
    def _require_typed_python_merged_pull_request(
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

    @field_validator("merge_revision", mode="before")
    @classmethod
    def _require_typed_python_merge_revision(
        cls,
        value: object,
        info: ValidationInfo,
    ) -> object:
        if info.mode == "python" and not isinstance(value, GitCommitIdentity):
            raise ValueError(
                "merge_revision must be a GitCommitIdentity in Python input"
            )
        return value

    @model_validator(mode="after")
    def _require_merged_pull_request_subject(self) -> Self:
        if self.pull_request.kind is not SourceObjectKind.PULL_REQUEST:
            raise ValueError("pull_request must identify a pull_request source object")
        return self
