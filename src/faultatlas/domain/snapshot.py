"""Immutable repository snapshot subject identity.

This module identifies a stable repository at one immutable Git commit. It
does not resolve refs, inspect Git objects or files, materialize repository
entries, assess completeness, attach evidence, or define durable bytes.
"""

from pydantic import BaseModel, ConfigDict, ValidationInfo, field_validator

from faultatlas.domain.identity import RepositoryIdentity
from faultatlas.domain.revision import GitCommitIdentity

__all__ = ["RepositorySnapshotIdentity"]


class RepositorySnapshotIdentity(BaseModel):
    """Stable repository identity qualified by one immutable Git commit."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        strict=True,
        revalidate_instances="always",
        validate_default=True,
    )

    repository: RepositoryIdentity
    revision: GitCommitIdentity

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
