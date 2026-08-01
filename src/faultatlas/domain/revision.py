"""Internal Git identity, revision, path, and bounded-coordinate primitives.

These models validate explicit object identities and separately supplied role
or ordered-parent records, immutable observations of mutable refs, and exact
revision-qualified repository paths. They also describe bounded logical-line,
artifact-byte, and diff-hunk coordinates without reading or resolving their
parents. Repository paths intentionally cover only the bounded UTF-8 textual subset of
Git path bytes. The models do not inspect a repository, establish
path existence, entry kind, membership, or reachability, reconcile roles with
topology or refs, resolve symbolic refs or locators, verify coordinate content,
model path or ref history, or define durable canonical serialization. Pydantic
JSON support is semantic rather than a canonical wire format.
"""

import re
from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Annotated, Literal, Self, cast
from unicodedata import category

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    RootModel,
    StringConstraints,
    ValidationInfo,
    field_validator,
    model_validator,
)

from faultatlas.domain.identity import (
    ProviderAuthority,
    RepositoryIdentity,
    SourceIdentityLifecycleState,
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
    "GitRefNamespace",
    "GitRefName",
    "GitRefObservation",
    "GitRepositoryPath",
    "RevisionQualifiedPath",
    "TextEncoding",
    "LineEnding",
    "OneBasedInclusiveLineSpan",
    "ZeroBasedHalfOpenByteSpan",
    "RevisionLineLocator",
    "ArtifactByteLocator",
    "DiffHunkLocator",
    "BoundedLocator",
]

_LOWERCASE_ASCII_HEX = re.compile(r"[0-9a-f]+")
_GIT_REF_NAMESPACE_PATTERN = re.compile(r"[a-z][a-z0-9_-]{0,63}")
_WINDOWS_DRIVE_ABSOLUTE_PATTERN = re.compile(r"[A-Za-z]:/")
_MAX_LINE_NUMBER = 2_147_483_647
_MAX_SIGNED_64_BIT_INTEGER = 9_223_372_036_854_775_807

_GitRefNamespaceValue = Annotated[
    str,
    StringConstraints(min_length=1, max_length=64),
]
_GitRefNameValue = Annotated[
    str,
    StringConstraints(min_length=1, max_length=255),
]
_GitRepositoryPathValue = Annotated[str, StringConstraints(min_length=1)]


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


class GitRefNamespace(RootModel[_GitRefNamespaceValue]):
    """One conservative namespace segment beneath ``refs/``."""

    model_config = ConfigDict(
        frozen=True,
        strict=True,
        revalidate_instances="always",
        validate_default=True,
    )

    root: _GitRefNamespaceValue

    @field_validator("root")
    @classmethod
    def _validate_namespace(cls, value: str) -> str:
        if not value.isascii() or _GIT_REF_NAMESPACE_PATTERN.fullmatch(value) is None:
            raise ValueError(
                "Git ref namespace must begin with a lowercase ASCII letter and "
                "contain only lowercase ASCII letters, digits, hyphens, or "
                "underscores"
            )
        if value == "refs":
            raise ValueError("Git ref namespace must be a segment beneath refs")
        return value


class GitRefName(RootModel[_GitRefNameValue]):
    """Conservative ASCII ref-relative path beneath one namespace."""

    model_config = ConfigDict(
        frozen=True,
        strict=True,
        revalidate_instances="always",
        validate_default=True,
    )

    root: _GitRefNameValue

    @field_validator("root")
    @classmethod
    def _validate_ref_name(cls, value: str) -> str:
        if not value.isascii():
            raise ValueError("Git ref name must contain only ASCII characters")
        if value.startswith("refs/"):
            raise ValueError("Git ref name must not include the refs prefix")
        if value == "@":
            raise ValueError("Git ref name must not be exactly @")
        if value.startswith("/") or value.endswith("/") or "//" in value:
            raise ValueError(
                "Git ref name must not contain leading, trailing, or repeated slash"
            )
        if ".." in value:
            raise ValueError("Git ref name must not contain two consecutive dots")
        if "@{" in value:
            raise ValueError("Git ref name must not contain @{ sequence")
        if value.endswith("."):
            raise ValueError("Git ref name must not have a trailing dot")
        if any(
            character == " " or ord(character) < 32 or ord(character) == 127
            for character in value
        ):
            raise ValueError("Git ref name must not contain space or ASCII control")
        if any(character in value for character in "\\~^:?*["):
            raise ValueError("Git ref name contains forbidden punctuation")
        segments = value.split("/")
        if any(segment.startswith(".") for segment in segments):
            raise ValueError("Git ref name segments must not start with a dot")
        if any(segment.endswith(".lock") for segment in segments):
            raise ValueError("Git ref name segments must not end in .lock")
        return value


class GitRefObservation(_RevisionRecordBase):
    """One immutable, repository-qualified observation of a mutable Git ref."""

    repository_identity: RepositoryIdentity
    namespace: GitRefNamespace
    name: GitRefName
    state: SourceIdentityLifecycleState
    authority: ProviderAuthority
    observed_at: AwareDatetime
    observed_target: GitRevisionIdentity | None

    @field_validator("repository_identity", mode="before")
    @classmethod
    def _require_typed_python_repository(
        cls,
        value: object,
        info: ValidationInfo,
    ) -> object:
        if info.mode == "python" and not isinstance(value, RepositoryIdentity):
            raise ValueError(
                "repository_identity must be a RepositoryIdentity in Python input"
            )
        return value

    @field_validator("namespace", mode="before")
    @classmethod
    def _require_typed_python_namespace(
        cls,
        value: object,
        info: ValidationInfo,
    ) -> object:
        if info.mode == "python" and not isinstance(value, GitRefNamespace):
            raise ValueError("namespace must be a GitRefNamespace in Python input")
        return value

    @field_validator("name", mode="before")
    @classmethod
    def _require_typed_python_name(
        cls,
        value: object,
        info: ValidationInfo,
    ) -> object:
        if info.mode == "python" and not isinstance(value, GitRefName):
            raise ValueError("name must be a GitRefName in Python input")
        return value

    @field_validator("state", mode="before")
    @classmethod
    def _require_typed_python_state(
        cls,
        value: object,
        info: ValidationInfo,
    ) -> object:
        if info.mode == "python" and not isinstance(
            value, SourceIdentityLifecycleState
        ):
            raise ValueError(
                "state must be a SourceIdentityLifecycleState in Python input"
            )
        return value

    @field_validator("authority", mode="before")
    @classmethod
    def _require_typed_python_authority(
        cls,
        value: object,
        info: ValidationInfo,
    ) -> object:
        if info.mode == "python" and not isinstance(value, ProviderAuthority):
            raise ValueError("authority must be a ProviderAuthority in Python input")
        return value

    @field_validator("observed_at")
    @classmethod
    def _normalize_observed_at(cls, value: datetime) -> datetime:
        if value.utcoffset() != timedelta(0):
            raise ValueError("observed_at must use a zero UTC offset")
        return value.astimezone(UTC)

    @field_validator("observed_target", mode="before")
    @classmethod
    def _require_typed_python_target(
        cls,
        value: object,
        info: ValidationInfo,
    ) -> object:
        if (
            info.mode == "python"
            and value is not None
            and not isinstance(value, GitCommitIdentity)
        ):
            raise ValueError(
                "observed_target must be a GitCommitIdentity or None in Python input"
            )
        return value

    @model_validator(mode="after")
    def _validate_observation_shape(self) -> Self:
        if self.authority.provider != self.repository_identity.provider:
            raise ValueError(
                "authority provider must match repository identity provider"
            )
        if self.state is SourceIdentityLifecycleState.OBSERVED_PRESENT:
            if self.observed_target is None:
                raise ValueError("observed_present state requires a commit target")
            return self
        if self.state is SourceIdentityLifecycleState.DELETED:
            return self
        if self.observed_target is not None:
            raise ValueError(f"{self.state.value} state cannot retain a target")
        return self


class GitRepositoryPath(RootModel[_GitRepositoryPathValue]):
    """Exact repository-relative path in the supported UTF-8 textual subset."""

    model_config = ConfigDict(
        frozen=True,
        strict=True,
        revalidate_instances="always",
        validate_default=True,
    )

    root: _GitRepositoryPathValue

    @field_validator("root")
    @classmethod
    def _validate_repository_path(cls, value: str) -> str:
        try:
            encoded = value.encode("utf-8")
        except UnicodeEncodeError as error:
            raise ValueError(
                "Git repository path must be encodable as strict UTF-8 text"
            ) from error
        if len(encoded) > 4096:
            raise ValueError(
                "Git repository path must contain at most 4096 encoded UTF-8 bytes"
            )
        if value.startswith("/") or value.endswith("/") or "//" in value:
            raise ValueError(
                "Git repository path must not contain leading, trailing, or "
                "repeated slash"
            )
        if "\\" in value:
            raise ValueError("Git repository path must use forward slashes only")
        if _WINDOWS_DRIVE_ABSOLUTE_PATTERN.match(value) is not None:
            raise ValueError("Git repository path must not be Windows drive-absolute")
        segments = value.split("/")
        if any(segment in {".", ".."} for segment in segments):
            raise ValueError("Git repository path must not contain . or .. segments")
        if any(category(character) in {"Cc", "Cf"} for character in value):
            raise ValueError(
                "Git repository path must not contain Unicode control or format "
                "characters"
            )
        return value


class RevisionQualifiedPath(_RevisionRecordBase):
    """Stable repository, immutable commit, and exact repository path."""

    repository_identity: RepositoryIdentity
    revision: GitRevisionIdentity
    path: GitRepositoryPath

    @field_validator("repository_identity", mode="before")
    @classmethod
    def _require_typed_python_repository(
        cls,
        value: object,
        info: ValidationInfo,
    ) -> object:
        if info.mode == "python" and not isinstance(value, RepositoryIdentity):
            raise ValueError(
                "repository_identity must be a RepositoryIdentity in Python input"
            )
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


class TextEncoding(StrEnum):
    """Supported text encoding for logical-line coordinates."""

    UTF8 = "utf-8"


class LineEnding(StrEnum):
    """Supported line-separator conventions for textual coordinates."""

    LF = "lf"
    CRLF = "crlf"


class _CoordinateSpanBase(BaseModel):
    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        strict=True,
        revalidate_instances="always",
        validate_default=True,
    )


class OneBasedInclusiveLineSpan(_CoordinateSpanBase):
    """Nonempty one-based line interval with both endpoints included."""

    start_line: int
    end_line: int

    @field_validator("start_line", "end_line", mode="before")
    @classmethod
    def _validate_line_number(cls, value: object) -> object:
        if type(value) is not int:
            raise ValueError("line numbers must be exact integers")
        if not 1 <= value <= _MAX_LINE_NUMBER:
            raise ValueError(
                f"line numbers must be between 1 and {_MAX_LINE_NUMBER} inclusive"
            )
        return value

    @model_validator(mode="after")
    def _validate_endpoint_order(self) -> Self:
        if self.end_line < self.start_line:
            raise ValueError("end_line must be greater than or equal to start_line")
        return self


class ZeroBasedHalfOpenByteSpan(_CoordinateSpanBase):
    """Nonempty zero-based byte interval represented by offset and length."""

    offset: int
    length: int

    @field_validator("offset", "length", mode="before")
    @classmethod
    def _require_exact_integer(cls, value: object) -> object:
        if type(value) is not int:
            raise ValueError("byte coordinates must be exact integers")
        return value

    @field_validator("offset")
    @classmethod
    def _validate_offset(cls, value: int) -> int:
        if not 0 <= value <= _MAX_SIGNED_64_BIT_INTEGER:
            raise ValueError(
                "offset must be between 0 and the signed 64-bit maximum inclusive"
            )
        return value

    @field_validator("length")
    @classmethod
    def _validate_length(cls, value: int) -> int:
        if not 1 <= value <= _MAX_SIGNED_64_BIT_INTEGER:
            raise ValueError(
                "length must be between 1 and the signed 64-bit maximum inclusive"
            )
        return value

    @model_validator(mode="after")
    def _validate_end_exclusive(self) -> Self:
        if self.offset + self.length > _MAX_SIGNED_64_BIT_INTEGER:
            raise ValueError("offset plus length exceeds the signed 64-bit maximum")
        return self


class RevisionLineLocator(_RevisionRecordBase):
    """Logical-line coordinates bound to one revision-qualified text path."""

    locator_kind: Literal["revision_line"]
    parent: RevisionQualifiedPath
    span: OneBasedInclusiveLineSpan
    text_encoding: TextEncoding
    line_ending: LineEnding

    @field_validator("parent", mode="before")
    @classmethod
    def _require_typed_python_parent(
        cls,
        value: object,
        info: ValidationInfo,
    ) -> object:
        if info.mode == "python" and not isinstance(value, RevisionQualifiedPath):
            raise ValueError("parent must be a RevisionQualifiedPath in Python input")
        return value

    @field_validator("span", mode="before")
    @classmethod
    def _require_typed_python_span(
        cls,
        value: object,
        info: ValidationInfo,
    ) -> object:
        if info.mode == "python" and not isinstance(value, OneBasedInclusiveLineSpan):
            raise ValueError("span must be a OneBasedInclusiveLineSpan in Python input")
        return value


class ArtifactByteLocator(_RevisionRecordBase):
    """Exact byte coordinates bound to an immutable SHA-256 artifact parent."""

    locator_kind: Literal["artifact_byte"]
    parent_artifact_sha256: str
    parent_byte_length: int
    span: ZeroBasedHalfOpenByteSpan

    @field_validator("parent_artifact_sha256")
    @classmethod
    def _validate_parent_artifact_sha256(cls, value: str) -> str:
        if len(value) != 64:
            raise ValueError(
                "parent_artifact_sha256 must contain exactly 64 hexadecimal characters"
            )
        if not value.isascii() or _LOWERCASE_ASCII_HEX.fullmatch(value) is None:
            raise ValueError(
                "parent_artifact_sha256 must contain only lowercase ASCII "
                "hexadecimal characters"
            )
        if not value.strip("0"):
            raise ValueError("parent_artifact_sha256 must not be all zero")
        return value

    @field_validator("parent_byte_length", mode="before")
    @classmethod
    def _validate_parent_byte_length(cls, value: object) -> object:
        if type(value) is not int:
            raise ValueError("parent_byte_length must be an exact integer")
        if not 0 <= value <= _MAX_SIGNED_64_BIT_INTEGER:
            raise ValueError(
                "parent_byte_length must be between 0 and the signed 64-bit "
                "maximum inclusive"
            )
        return value

    @field_validator("span", mode="before")
    @classmethod
    def _require_typed_python_span(
        cls,
        value: object,
        info: ValidationInfo,
    ) -> object:
        if info.mode == "python" and not isinstance(value, ZeroBasedHalfOpenByteSpan):
            raise ValueError("span must be a ZeroBasedHalfOpenByteSpan in Python input")
        return value

    @model_validator(mode="after")
    def _validate_span_within_parent(self) -> Self:
        if self.span.offset + self.span.length > self.parent_byte_length:
            raise ValueError("span must end within parent_byte_length")
        return self


class DiffHunkLocator(_RevisionRecordBase):
    """One diff hunk with distinct artifact, old-side, and new-side bounds."""

    locator_kind: Literal["diff_hunk"]
    artifact_bytes: ArtifactByteLocator
    artifact_lines: OneBasedInclusiveLineSpan
    text_encoding: TextEncoding
    line_ending: LineEnding
    old_file: RevisionQualifiedPath | None
    old_lines: OneBasedInclusiveLineSpan | None
    new_file: RevisionQualifiedPath | None
    new_lines: OneBasedInclusiveLineSpan | None

    @field_validator("artifact_bytes", mode="before")
    @classmethod
    def _require_typed_python_artifact_bytes(
        cls,
        value: object,
        info: ValidationInfo,
    ) -> object:
        if info.mode == "python" and not isinstance(value, ArtifactByteLocator):
            raise ValueError(
                "artifact_bytes must be an ArtifactByteLocator in Python input"
            )
        return value

    @field_validator("artifact_lines", mode="before")
    @classmethod
    def _require_typed_python_artifact_lines(
        cls,
        value: object,
        info: ValidationInfo,
    ) -> object:
        if info.mode == "python" and not isinstance(value, OneBasedInclusiveLineSpan):
            raise ValueError(
                "artifact_lines must be a OneBasedInclusiveLineSpan in Python input"
            )
        return value

    @field_validator("old_file", "new_file", mode="before")
    @classmethod
    def _require_typed_python_file(
        cls,
        value: object,
        info: ValidationInfo,
    ) -> object:
        if (
            info.mode == "python"
            and value is not None
            and not isinstance(value, RevisionQualifiedPath)
        ):
            raise ValueError(
                "diff files must be RevisionQualifiedPath values or None in "
                "Python input"
            )
        return value

    @field_validator("old_lines", "new_lines", mode="before")
    @classmethod
    def _require_typed_python_lines(
        cls,
        value: object,
        info: ValidationInfo,
    ) -> object:
        if (
            info.mode == "python"
            and value is not None
            and not isinstance(value, OneBasedInclusiveLineSpan)
        ):
            raise ValueError(
                "diff line spans must be OneBasedInclusiveLineSpan values or "
                "None in Python input"
            )
        return value

    @model_validator(mode="after")
    def _validate_sides(self) -> Self:
        old_file_present = self.old_file is not None
        old_lines_present = self.old_lines is not None
        new_file_present = self.new_file is not None
        new_lines_present = self.new_lines is not None
        if old_file_present != old_lines_present:
            raise ValueError("old_file and old_lines must be present together")
        if new_file_present != new_lines_present:
            raise ValueError("new_file and new_lines must be present together")
        if not old_file_present and not new_file_present:
            raise ValueError("at least one complete diff side must be present")
        return self


type BoundedLocator = Annotated[
    RevisionLineLocator | ArtifactByteLocator | DiffHunkLocator,
    Field(discriminator="locator_kind"),
]
