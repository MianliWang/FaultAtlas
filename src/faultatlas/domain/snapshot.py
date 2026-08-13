"""Immutable repository snapshot subject identity and root-tree binding.

This module identifies a stable repository at one immutable Git commit. It
also carries a supplied root-tree association without verifying Git object
bytes. It does not resolve refs, inspect Git objects or files, materialize
repository entries, assess completeness, attach evidence, or define durable
bytes.
"""

from typing import Self

from pydantic import (
    BaseModel,
    ConfigDict,
    ValidationInfo,
    field_validator,
    model_validator,
)

from faultatlas.domain.identity import RepositoryIdentity
from faultatlas.domain.revision import GitCommitIdentity, GitTreeIdentity

__all__ = [
    "RepositorySnapshotIdentity",
    "RepositorySnapshotRootTreeBinding",
]


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


class RepositorySnapshotRootTreeBinding(BaseModel):
    """Supplied immutable root-tree binding for one repository snapshot."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        strict=True,
        revalidate_instances="always",
        validate_default=True,
    )

    snapshot: RepositorySnapshotIdentity
    root_tree: GitTreeIdentity

    @field_validator("snapshot", mode="before")
    @classmethod
    def _require_typed_python_snapshot(
        cls,
        value: object,
        info: ValidationInfo,
    ) -> object:
        if info.mode == "python" and not isinstance(
            value,
            RepositorySnapshotIdentity,
        ):
            raise ValueError(
                "snapshot must be a RepositorySnapshotIdentity in Python input"
            )
        return value

    @field_validator("root_tree", mode="before")
    @classmethod
    def _require_typed_python_root_tree(
        cls,
        value: object,
        info: ValidationInfo,
    ) -> object:
        if info.mode == "python" and not isinstance(value, GitTreeIdentity):
            raise ValueError("root_tree must be a GitTreeIdentity in Python input")
        return value

    @model_validator(mode="after")
    def _require_matching_hash_algorithms(self) -> Self:
        if self.root_tree.algorithm is not self.snapshot.revision.algorithm:
            raise ValueError(
                "root tree algorithm must match the snapshot revision algorithm"
            )
        return self
