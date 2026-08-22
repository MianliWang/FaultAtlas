"""Identity of one repository-scoped Issue or Pull Request development subject.

This module publishes the smallest identity primitive the development-history
phase needs: a typed name for one Issue or one Pull Request in one stable
repository. It is the subject position that later history relations will point
at, and it is deliberately established before any relation exists.

A development subject identity is a supplied value. Its caller states which
repository the subject belongs to, whether the subject is an Issue or a Pull
Request, which repository-scoped number the provider assigned it, and which
provider-global identifier the provider assigned it. Construction records those
four supplied values and asserts nothing further.

The subject kind is closed to exactly `issue` and `pull_request`. Reviews,
comments, commits, branches, CI runs, test runs, discussions, releases, and
deployments are not development subjects here: an unknown kind fails closed
rather than widening the vocabulary.

The identity is complete only as a whole. Repository identity and subject kind
are both part of the subject, so the same number under a different repository
and the same number under a different kind are different values. The number and
the provider-global identifier are opaque supplied scalars that carry no
repository or provider information of their own, so no coherence between them
is checked, inferred, or implied; a supplied pair is never treated as an
authoritative provider match.

The module makes no history claim. It does not assert that the subject exists,
that a provider lookup would succeed, or anything about visibility, state,
title, body, author, labels, timestamps, comments, or discussion content. It
defines no chronology, no relation between an Issue and a Pull Request, no
relation to a commit, revision, or repository snapshot, no repair or fix
semantics, no review or merge status, no default-branch or mutable-ref
observation, and no change set. Completeness and historical truth are outside
it entirely.

The module is evidence-neutral. No evidence record is referenced, and no claim
is made that any retained acquisition supports, corroborates, or verifies a
supplied identity. Evidence association belongs to a later slice, after the
history fact types stabilize. The module performs no I/O: it resolves nothing,
reads nothing, contacts no provider, and defines no durable bytes, reader,
writer, or persistence.
"""

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, ValidationInfo, field_validator

from faultatlas.domain.identity import (
    ProviderGlobalId,
    RepositoryIdentity,
    RepositoryScopedNumber,
)

__all__ = [
    "DevelopmentSubjectKind",
    "DevelopmentSubjectIdentity",
]


class DevelopmentSubjectKind(StrEnum):
    """Closed vocabulary of repository-scoped development subjects."""

    ISSUE = "issue"
    PULL_REQUEST = "pull_request"


class DevelopmentSubjectIdentity(BaseModel):
    """Supplied identity of one Issue or Pull Request in one repository."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        strict=True,
        revalidate_instances="always",
        validate_default=True,
    )

    repository: RepositoryIdentity
    kind: DevelopmentSubjectKind
    number: RepositoryScopedNumber
    provider_global_id: ProviderGlobalId

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

    @field_validator("number", mode="before")
    @classmethod
    def _require_typed_python_number(
        cls,
        value: object,
        info: ValidationInfo,
    ) -> object:
        if info.mode == "python" and not isinstance(value, RepositoryScopedNumber):
            raise ValueError("number must be a RepositoryScopedNumber in Python input")
        return value

    @field_validator("provider_global_id", mode="before")
    @classmethod
    def _require_typed_python_provider_global_id(
        cls,
        value: object,
        info: ValidationInfo,
    ) -> object:
        if info.mode == "python" and not isinstance(value, ProviderGlobalId):
            raise ValueError(
                "provider_global_id must be a ProviderGlobalId in Python input"
            )
        return value
