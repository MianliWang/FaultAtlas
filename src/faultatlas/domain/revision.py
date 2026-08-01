"""Internal Git object identity, revision-role, and topology primitives.

These models validate explicit object identities and separately supplied role
or ordered-parent records. They do not inspect a repository, establish
repository membership or reachability, reconcile roles with topology, resolve
refs, qualify paths, or define durable canonical serialization. Pydantic JSON
support is semantic rather than a canonical wire format.
"""

import re
from collections.abc import Mapping
from enum import StrEnum
from typing import Annotated, Literal, Self, cast

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationInfo,
    field_validator,
    model_validator,
)

__all__ = [
    "GitHashAlgorithm",
    "GitObjectKind",
    "GitCommitIdentity",
    "GitTreeIdentity",
    "GitBlobIdentity",
    "GitObjectIdentity",
    "GitRevisionIdentity",
    "RevisionRole",
    "RevisionRoleAssignment",
    "GitCommitParentTopology",
]

_LOWERCASE_ASCII_HEX = re.compile(r"[0-9a-f]+")


class GitHashAlgorithm(StrEnum):
    """Supported Git object hash algorithms."""

    SHA1 = "sha1"
    SHA256 = "sha256"


class GitObjectKind(StrEnum):
    """Supported intrinsic Git object kinds."""

    COMMIT = "commit"
    TREE = "tree"
    BLOB = "blob"


_DIGEST_LENGTHS = {
    GitHashAlgorithm.SHA1: 40,
    GitHashAlgorithm.SHA256: 64,
}


class _GitObjectIdentityBase[GitObjectKindT: GitObjectKind](BaseModel):
    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        strict=True,
        revalidate_instances="always",
        validate_default=True,
    )

    schema_version: Literal[1] = 1
    kind: GitObjectKindT
    algorithm: GitHashAlgorithm
    full_digest: str

    @model_validator(mode="before")
    @classmethod
    def _require_strict_input_types(
        cls,
        value: object,
        info: ValidationInfo,
    ) -> object:
        if isinstance(value, _GitObjectIdentityBase):
            identity = cast(_GitObjectIdentityBase[GitObjectKind], value)
            kind: object = identity.kind
            schema_version: object = identity.schema_version
        elif isinstance(value, Mapping):
            mapping = cast(Mapping[object, object], value)
            if "kind" not in mapping:
                return cast(object, value)
            kind = mapping["kind"]
            schema_version = mapping.get("schema_version", 1)
        else:
            return value
        if type(schema_version) is not int or schema_version != 1:
            raise ValueError("schema_version must be the integer 1")
        if info.mode == "python" and not isinstance(kind, GitObjectKind):
            raise ValueError("kind must be a GitObjectKind in Python input")
        return cast(object, value)

    @model_validator(mode="after")
    def _validate_full_digest(self) -> Self:
        expected_length = _DIGEST_LENGTHS[self.algorithm]
        if len(self.full_digest) != expected_length:
            raise ValueError(
                f"{self.algorithm.value} full digest must contain exactly "
                f"{expected_length} hexadecimal characters"
            )
        if (
            not self.full_digest.isascii()
            or _LOWERCASE_ASCII_HEX.fullmatch(self.full_digest) is None
        ):
            raise ValueError(
                "full digest must contain only lowercase ASCII hexadecimal characters"
            )
        if not self.full_digest.strip("0"):
            raise ValueError("full digest must not be all zero")
        return self


class GitCommitIdentity(_GitObjectIdentityBase[Literal[GitObjectKind.COMMIT]]):
    """Intrinsic identity of one Git commit object."""


class GitTreeIdentity(_GitObjectIdentityBase[Literal[GitObjectKind.TREE]]):
    """Intrinsic identity of one Git tree object."""


class GitBlobIdentity(_GitObjectIdentityBase[Literal[GitObjectKind.BLOB]]):
    """Intrinsic identity of one Git blob object."""


type GitObjectIdentity = Annotated[
    GitCommitIdentity | GitTreeIdentity | GitBlobIdentity,
    Field(discriminator="kind"),
]
type GitRevisionIdentity = GitCommitIdentity


class RevisionRole(StrEnum):
    """Context-relative semantic roles assigned to immutable revisions."""

    BASE = "base"
    HEAD = "head"
    MERGE_FIRST_PARENT = "merge_first_parent"
    MERGE = "merge"


class _RevisionRecordBase(BaseModel):
    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        strict=True,
        revalidate_instances="always",
        validate_default=True,
    )

    schema_version: Literal[1] = 1

    @field_validator("schema_version", mode="before")
    @classmethod
    def _require_exact_schema_version(cls, value: object) -> object:
        if type(value) is not int or value != 1:
            raise ValueError("schema_version must be the integer 1")
        return value


class RevisionRoleAssignment(_RevisionRecordBase):
    """One context-relative role assigned to an immutable commit identity."""

    role: RevisionRole
    revision: GitRevisionIdentity

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


class GitCommitParentTopology(_RevisionRecordBase):
    """One commit and its exact ordered sequence of commit parents."""

    commit: GitCommitIdentity
    ordered_parents: tuple[GitCommitIdentity, ...]

    @field_validator("commit", mode="before")
    @classmethod
    def _require_typed_python_commit(
        cls,
        value: object,
        info: ValidationInfo,
    ) -> object:
        if info.mode == "python" and not isinstance(value, GitCommitIdentity):
            raise ValueError("commit must be a GitCommitIdentity in Python input")
        return value

    @field_validator("ordered_parents", mode="before")
    @classmethod
    def _require_strict_ordered_parents(
        cls,
        value: object,
        info: ValidationInfo,
    ) -> object:
        if info.mode == "json" and isinstance(value, list):
            return tuple(cast(list[object], value))
        if info.mode == "python":
            if not isinstance(value, tuple):
                raise ValueError("ordered_parents must be a tuple in Python input")
            parents = cast(tuple[object, ...], value)
            if any(not isinstance(parent, GitCommitIdentity) for parent in parents):
                raise ValueError(
                    "ordered_parents must contain GitCommitIdentity values"
                )
        return cast(object, value)

    @model_validator(mode="after")
    def _require_matching_hash_algorithms(self) -> Self:
        if any(
            parent.algorithm is not self.commit.algorithm
            for parent in self.ordered_parents
        ):
            raise ValueError("parent algorithms must match the commit algorithm")
        return self
