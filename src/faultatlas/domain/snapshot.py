"""Immutable repository snapshot identity, root-tree, and path bindings.

This module identifies a stable repository at one immutable Git commit. It
also carries supplied root-tree and path-to-object associations without
verifying Git object bytes. A path binding associates one exact repository
path with one supplied intrinsic blob or tree identity; it does not establish
path existence, repository membership, root-tree reachability, Git tree-entry
mode, symbolic-link or gitlink semantics, ordering, uniqueness against other
bindings, or the absence of any other path. It does not resolve refs, inspect
Git objects or files, aggregate snapshot collections, assess completeness,
attach evidence, or define durable bytes.
"""

from typing import Annotated, Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationInfo,
    field_validator,
    model_validator,
)

from faultatlas.domain.identity import RepositoryIdentity
from faultatlas.domain.revision import (
    GitBlobIdentity,
    GitCommitIdentity,
    GitRepositoryPath,
    GitTreeIdentity,
)

__all__ = [
    "RepositorySnapshotIdentity",
    "RepositorySnapshotRootTreeBinding",
    "RepositorySnapshotPathBinding",
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


class RepositorySnapshotPathBinding(BaseModel):
    """Supplied association from one snapshot path to one intrinsic Git object."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        strict=True,
        revalidate_instances="always",
        validate_default=True,
    )

    snapshot: RepositorySnapshotIdentity
    path: GitRepositoryPath
    git_object: Annotated[
        GitBlobIdentity | GitTreeIdentity,
        Field(discriminator="kind"),
    ]

    @field_validator("snapshot", mode="before")
    @classmethod
    def _require_typed_python_path_snapshot(
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

    @field_validator("git_object", mode="before")
    @classmethod
    def _require_typed_python_git_object(
        cls,
        value: object,
        info: ValidationInfo,
    ) -> object:
        if info.mode == "python" and not isinstance(
            value,
            (GitBlobIdentity, GitTreeIdentity),
        ):
            raise ValueError(
                "git_object must be a GitBlobIdentity or GitTreeIdentity in "
                "Python input"
            )
        return value

    @model_validator(mode="after")
    def _require_matching_object_hash_algorithm(self) -> Self:
        if self.git_object.algorithm is not self.snapshot.revision.algorithm:
            raise ValueError(
                "bound object algorithm must match the snapshot revision algorithm"
            )
        return self
