"""Immutable repository snapshot identity, root-tree, and path bindings.

This module identifies a stable repository at one immutable Git commit. It
also carries supplied root-tree and path-to-object associations without
verifying Git object bytes. A path binding associates one exact repository
path with one supplied intrinsic blob or tree identity; it does not establish
path existence, repository membership, root-tree reachability, Git tree-entry
mode, symbolic-link or gitlink semantics, or the absence of any other path.

A binding collection aggregates bounded supplied bindings sharing one snapshot
subject, preserving the supplied order exactly and rejecting a repeated path
without sorting, merging, or deduplication. That order is the supplied order
alone and carries no Git-tree, lexical, canonical, or repository structural
meaning. An empty collection aggregates zero supplied bindings rather than
asserting that any path is absent, and aggregation is not repository
membership.

A declared path scope records which exact repository paths a supplier declared
to be in scope for one snapshot subject. The scope is supplied by its caller
and is never derived from acquisition, binding, traversal, or root-tree
material. It covers exact paths only, never a prefix, subtree, or whole
repository. Declaring a path asserts nothing about that path: not existence,
membership, resolution, reachability, binding coverage, or availability. An
empty scope declares zero paths rather than asserting completeness or that any
path is absent, and undeclared paths are simply undeclared.

A scope-coverage witness relates one non-empty declared scope to one binding
collection over the same snapshot subject. It exists only when every exact
declared path also appears as the exact path of a supplied binding, matched by
path alone: no object kind, digest, or normalization participates, and bindings
outside the declared scope neither help nor hinder. Validity does not depend on
either supplied order, while the witness preserves both supplied values
unchanged, so ordinary value equality still distinguishes supplied orders.
Successful construction is the whole assertion; the witness stores no status,
count, or path subset. A declared path lacking a supplied binding is given no
name and no state here, and the absence of a witness asserts nothing at all.

The module does not resolve refs, inspect Git objects or files, establish path
prefix, ancestry, or tree topology, assert repository membership, path
existence, or root-tree reachability, assess snapshot or whole-repository
completeness, represent absence, attach evidence, or define durable bytes.
"""

from collections.abc import Mapping
from typing import Annotated, Self, cast

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationInfo,
    ValidatorFunctionWrapHandler,
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
    "RepositorySnapshotPathBindingCollection",
    "RepositorySnapshotDeclaredPathScope",
    "RepositorySnapshotDeclaredPathScopeCoverage",
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


class RepositorySnapshotPathBindingCollection(BaseModel):
    """Bounded ordered aggregate of supplied bindings for one snapshot."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        strict=True,
        revalidate_instances="always",
        validate_default=True,
    )

    snapshot: RepositorySnapshotIdentity
    bindings: Annotated[
        tuple[RepositorySnapshotPathBinding, ...],
        Field(max_length=4096),
    ]

    @field_validator("snapshot", mode="before")
    @classmethod
    def _require_typed_python_collection_snapshot(
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

    @model_validator(mode="after")
    def _require_shared_snapshot_and_unique_paths(self) -> Self:
        if any(binding.snapshot != self.snapshot for binding in self.bindings):
            raise ValueError("every binding must carry the collection snapshot subject")
        if len(frozenset(binding.path for binding in self.bindings)) != len(
            self.bindings
        ):
            raise ValueError("bindings must not repeat a repository path")
        return self


class RepositorySnapshotDeclaredPathScope(BaseModel):
    """Supplied declaration of exact repository paths scoped to one snapshot."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        strict=True,
        revalidate_instances="always",
        validate_default=True,
    )

    snapshot: RepositorySnapshotIdentity
    declared_paths: Annotated[
        tuple[GitRepositoryPath, ...],
        Field(max_length=4096),
    ]

    @field_validator("snapshot", mode="before")
    @classmethod
    def _require_typed_python_scope_snapshot(
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

    @field_validator("declared_paths", mode="before")
    @classmethod
    def _require_typed_python_declared_paths(
        cls,
        value: object,
        info: ValidationInfo,
    ) -> object:
        if info.mode == "json" and isinstance(value, list):
            return tuple(cast(list[object], value))
        if info.mode == "python" and isinstance(value, tuple):
            declared = cast(tuple[object, ...], value)
            if any(not isinstance(path, GitRepositoryPath) for path in declared):
                raise ValueError(
                    "declared_paths must contain GitRepositoryPath values in "
                    "Python input"
                )
        return cast(object, value)

    @model_validator(mode="after")
    def _require_unique_declared_paths(self) -> Self:
        if len(frozenset(self.declared_paths)) != len(self.declared_paths):
            raise ValueError("declared paths must not repeat a repository path")
        return self


class RepositorySnapshotDeclaredPathScopeCoverage(BaseModel):
    """Supplied witness that a declared path scope is covered by bindings."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        strict=True,
        revalidate_instances="always",
        validate_default=True,
    )

    scope: RepositorySnapshotDeclaredPathScope
    collection: RepositorySnapshotPathBindingCollection

    @field_validator("scope", "collection", mode="wrap")
    @classmethod
    def _require_typed_python_children(
        cls,
        value: object,
        handler: ValidatorFunctionWrapHandler,
        info: ValidationInfo,
    ) -> object:
        if info.mode == "python" and isinstance(value, Mapping):
            raise ValueError(
                "scope and collection must be typed values in Python input"
            )
        if info.mode == "json" and isinstance(value, Mapping):
            supplied = cast(Mapping[str, object], value)
            return handler(
                {
                    key: tuple(cast(list[object], supplied[key]))
                    if isinstance(supplied[key], list)
                    else supplied[key]
                    for key in supplied
                }
            )
        return handler(value)

    @model_validator(mode="after")
    def _require_covered_declared_paths(self) -> Self:
        if not self.scope.declared_paths:
            raise ValueError("a covered scope must declare at least one path")
        if self.scope.snapshot != self.collection.snapshot:
            raise ValueError("scope and collection must share the snapshot subject")
        bound = frozenset(binding.path for binding in self.collection.bindings)
        if any(path not in bound for path in self.scope.declared_paths):
            raise ValueError("every declared path must have a supplied binding")
        return self
