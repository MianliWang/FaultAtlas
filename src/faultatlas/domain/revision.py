"""Internal, intrinsic Git object identity primitives.

These models validate explicit object identities only. They do not inspect a
repository, establish repository membership or reachability, attach revision
roles or topology, resolve refs, qualify paths, or define durable canonical
serialization. Pydantic JSON support is semantic rather than a canonical wire
format.
"""

import re
from collections.abc import Mapping
from enum import StrEnum
from typing import Annotated, Literal, Self, cast

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, model_validator

__all__ = [
    "GitHashAlgorithm",
    "GitObjectKind",
    "GitCommitIdentity",
    "GitTreeIdentity",
    "GitBlobIdentity",
    "GitObjectIdentity",
    "GitRevisionIdentity",
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
