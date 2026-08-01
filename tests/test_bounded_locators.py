from __future__ import annotations

import ast
import hashlib
import json
import re
from pathlib import Path
from typing import Any, cast

import pytest
from pydantic import BaseModel, TypeAdapter, ValidationError

import faultatlas
import faultatlas.domain as domain_package
import faultatlas.domain.revision as revision_module
from faultatlas.domain.identity import (
    AuthorityRole,
    ProviderAuthority,
    ProviderKey,
    ProviderRepositoryId,
    RepositoryIdentity,
    SourceIdentityLifecycleState,
)
from faultatlas.domain.revision import (
    ArtifactByteLocator,
    BoundedLocator,
    DiffHunkLocator,
    GitCommitIdentity,
    GitHashAlgorithm,
    GitObjectKind,
    GitRefName,
    GitRefNamespace,
    GitRefObservation,
    GitRepositoryPath,
    LineEnding,
    OneBasedInclusiveLineSpan,
    RevisionLineLocator,
    RevisionQualifiedPath,
    RevisionRole,
    RevisionRoleAssignment,
    TextEncoding,
    ZeroBasedHalfOpenByteSpan,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
REVISION_SOURCE = REPOSITORY_ROOT / "src/faultatlas/domain/revision.py"
DIFF_ARTIFACT = REPOSITORY_ROOT / (
    "reference_corpus/pytest-4412/acquisitions/"
    "run-0001-s04-v1-base-4c9cde74-head-690a63b9/artifacts/base-to-head.diff"
)
ACQUISITION = REPOSITORY_ROOT / (
    "reference_corpus/pytest-4412/acquisitions/"
    "run-0001-s04-v1-base-4c9cde74-head-690a63b9/acquisition.json"
)
S06_CORPUS_RELATIVE = "reference_corpus/contracts/revision-locator/v1"
S06_CORPUS_ROOT = REPOSITORY_ROOT / S06_CORPUS_RELATIVE
EXPECTED_S06_CORPUS_FILES = {
    "contract.md",
    "invalid-vectors.json",
    "invalid-vectors.sha256",
    "manifest.json",
    "manifest.sha256",
    "replay-vectors.json",
    "replay-vectors.sha256",
    "valid-vectors.json",
    "valid-vectors.sha256",
}
EXPECTED_S06_CORPUS_PATHS = {
    f"{S06_CORPUS_RELATIVE}/{filename}" for filename in EXPECTED_S06_CORPUS_FILES
}

CANONICAL_PROVIDER = "github"
CANONICAL_REPOSITORY_ID = "37489525"
CANONICAL_BASE = "4c9cde74ab40027b5761ab9e002af116a4a20df3"
CANONICAL_HEAD = "690a63b9218f72662cd3a67c6c200b758c88ce12"
CANONICAL_ARTIFACT_SHA256 = (
    "dca87a4df1edb2d1acb3fc821724483ee874c2feba6525b2c21e79cb3e8f7312"
)
CANONICAL_ARTIFACT_BYTE_LENGTH = 1640
MAX_LINE = 2_147_483_647
MAX_INT64 = 9_223_372_036_854_775_807

EXPECTED_EXPORTS = [
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
EXPECTED_PRODUCTION_FILES = {
    "src/faultatlas/__init__.py",
    "src/faultatlas/__main__.py",
    "src/faultatlas/cli.py",
    "src/faultatlas/domain/__init__.py",
    "src/faultatlas/domain/compatibility.py",
    "src/faultatlas/domain/identity.py",
    "src/faultatlas/domain/revision.py",
    "src/faultatlas/domain/source.py",
}
S05_EXPORTS = {
    "TextEncoding",
    "LineEnding",
    "OneBasedInclusiveLineSpan",
    "ZeroBasedHalfOpenByteSpan",
    "RevisionLineLocator",
    "ArtifactByteLocator",
    "DiffHunkLocator",
    "BoundedLocator",
}

type _BoundedLocatorRuntime = (
    RevisionLineLocator | ArtifactByteLocator | DiffHunkLocator
)
LOCATOR_ADAPTER = cast(
    TypeAdapter[_BoundedLocatorRuntime],
    TypeAdapter(BoundedLocator),
)

type _CanonicalByteVector = tuple[int, int, int, int, str]
CANONICAL_BYTE_VECTORS: tuple[_CanonicalByteVector, ...] = (
    (
        165,
        77,
        6,
        7,
        "3a9ef726e8631334ac0ee92db96577569a58f2c972fb2b248b2f33a8833952a6",
    ),
    (
        439,
        394,
        12,
        21,
        "7395019171a710ce827d5ed71020afbdd790f8e1c158756388c08977d17bdecd",
    ),
    (
        1018,
        622,
        26,
        45,
        "47640375cbfeb436cfc73aeeb1926d77b05d969fc684289c17b271ca85facfc3",
    ),
)

type _CanonicalHunkVector = tuple[
    int,
    int,
    int,
    int,
    str | None,
    tuple[int, int] | None,
    str | None,
    tuple[int, int] | None,
]
CANONICAL_HUNK_VECTORS: tuple[_CanonicalHunkVector, ...] = (
    (
        165,
        77,
        6,
        7,
        None,
        None,
        "changelog/4412.bugfix.rst",
        (1, 1),
    ),
    (
        439,
        394,
        12,
        21,
        "src/_pytest/assertion/rewrite.py",
        (946, 952),
        "src/_pytest/assertion/rewrite.py",
        (946, 953),
    ),
    (
        1018,
        622,
        26,
        45,
        "testing/test_assertrewrite.py",
        (413, 418),
        "testing/test_assertrewrite.py",
        (413, 431),
    ),
)

type _ReviewedLineVector = tuple[str, int, int, str]
REVIEWED_LINE_VECTORS: tuple[_ReviewedLineVector, ...] = (
    (
        "changelog/4412.bugfix.rst",
        1,
        1,
        "reviewed_derived_interpretation",
    ),
    (
        "src/_pytest/assertion/rewrite.py",
        946,
        950,
        "reviewed_derived_interpretation",
    ),
    (
        "testing/test_assertrewrite.py",
        416,
        427,
        "reviewed_derived_interpretation",
    ),
)

EVIDENCE_CLASSIFICATIONS = {
    "byte_locator": "exact_byte_locator_fact",
    "hunk_and_additions": "deterministic_derivation",
    "role_and_applicability": "reviewed_derived_interpretation",
}


def _provider(value: str = CANONICAL_PROVIDER) -> ProviderKey:
    return ProviderKey.model_validate(value)


def _repository(
    repository_id: str = CANONICAL_REPOSITORY_ID,
    *,
    provider: str = CANONICAL_PROVIDER,
) -> RepositoryIdentity:
    return RepositoryIdentity(
        provider=_provider(provider),
        provider_repository_id=ProviderRepositoryId.model_validate(repository_id),
    )


def _commit(
    digest: str = CANONICAL_HEAD,
    algorithm: GitHashAlgorithm = GitHashAlgorithm.SHA1,
) -> GitCommitIdentity:
    return GitCommitIdentity(
        kind=GitObjectKind.COMMIT,
        algorithm=algorithm,
        full_digest=digest,
    )


def _qualified(
    path: str = "src/_pytest/assertion/rewrite.py",
    *,
    revision: GitCommitIdentity | None = None,
    repository: RepositoryIdentity | None = None,
) -> RevisionQualifiedPath:
    return RevisionQualifiedPath(
        repository_identity=repository or _repository(),
        revision=revision or _commit(),
        path=GitRepositoryPath.model_validate(path),
    )


def _line_span(start: int = 1, end: int = 1) -> OneBasedInclusiveLineSpan:
    return OneBasedInclusiveLineSpan(start_line=start, end_line=end)


def _byte_span(offset: int = 0, length: int = 1) -> ZeroBasedHalfOpenByteSpan:
    return ZeroBasedHalfOpenByteSpan(offset=offset, length=length)


def _line_locator(
    *,
    parent: RevisionQualifiedPath | None = None,
    span: OneBasedInclusiveLineSpan | None = None,
    line_ending: LineEnding = LineEnding.LF,
) -> RevisionLineLocator:
    return RevisionLineLocator(
        locator_kind="revision_line",
        parent=parent or _qualified(),
        span=span or _line_span(),
        text_encoding=TextEncoding.UTF8,
        line_ending=line_ending,
    )


def _artifact_locator(
    offset: int = 165,
    length: int = 77,
    *,
    parent_byte_length: int = CANONICAL_ARTIFACT_BYTE_LENGTH,
) -> ArtifactByteLocator:
    return ArtifactByteLocator(
        locator_kind="artifact_byte",
        parent_artifact_sha256=CANONICAL_ARTIFACT_SHA256,
        parent_byte_length=parent_byte_length,
        span=_byte_span(offset, length),
    )


def _hunk(
    *,
    artifact_bytes: ArtifactByteLocator | None = None,
    artifact_lines: OneBasedInclusiveLineSpan | None = None,
    old_file: RevisionQualifiedPath | None = None,
    old_lines: OneBasedInclusiveLineSpan | None = None,
    new_file: RevisionQualifiedPath | None = None,
    new_lines: OneBasedInclusiveLineSpan | None = None,
    line_ending: LineEnding = LineEnding.LF,
) -> DiffHunkLocator:
    return DiffHunkLocator(
        locator_kind="diff_hunk",
        artifact_bytes=artifact_bytes or _artifact_locator(),
        artifact_lines=artifact_lines or _line_span(6, 7),
        text_encoding=TextEncoding.UTF8,
        line_ending=line_ending,
        old_file=old_file,
        old_lines=old_lines,
        new_file=new_file or _qualified("changelog/4412.bugfix.rst"),
        new_lines=new_lines or _line_span(),
    )


def _ref_observation() -> GitRefObservation:
    from datetime import UTC, datetime

    return GitRefObservation(
        repository_identity=_repository(),
        namespace=GitRefNamespace.model_validate("heads"),
        name=GitRefName.model_validate("feature/example"),
        state=SourceIdentityLifecycleState.OBSERVED_PRESENT,
        authority=ProviderAuthority(
            provider=_provider(),
            role=AuthorityRole.RETRIEVAL,
            host="api.github.com",
        ),
        observed_at=datetime(2026, 8, 1, 12, 0, tzinfo=UTC),
        observed_target=_commit(),
    )


def _role_assignment() -> RevisionRoleAssignment:
    return RevisionRoleAssignment(role=RevisionRole.HEAD, revision=_commit())


def _revision_surface(source: str) -> tuple[list[str], set[str]]:
    tree = ast.parse(source)
    exports = next(
        ast.literal_eval(node.value)
        for node in tree.body
        if isinstance(node, ast.Assign)
        and any(
            isinstance(target, ast.Name) and target.id == "__all__"
            for target in node.targets
        )
    )
    public = {
        node.name
        for node in tree.body
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
        and not node.name.startswith("_")
    }
    public.update(
        node.name.id
        for node in tree.body
        if isinstance(node, ast.TypeAlias) and not node.name.id.startswith("_")
    )
    return exports, public


def _validate_revision_surface(source: str) -> None:
    exports, public = _revision_surface(source)
    assert exports == EXPECTED_EXPORTS
    assert public == set(EXPECTED_EXPORTS)


def _validate_production_inventory(paths: set[str]) -> None:
    assert paths == EXPECTED_PRODUCTION_FILES


def _validate_package_exports(exports: list[str]) -> None:
    assert exports == ["__version__"]


def _validate_no_deferred_surface(source: str) -> None:
    tree = ast.parse(source)
    forbidden_public = {
        "ColumnLocator",
        "LocatorReader",
        "LocatorResolver",
        "ReviewApplicability",
        "PathHistory",
        "EvidenceEnvelope",
    }
    definitions = {
        node.name
        for node in tree.body
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
        and not node.name.startswith("_")
    }
    assert not definitions & forbidden_public


def _derive_unified_hunks(
    artifact: bytes,
) -> tuple[tuple[int, tuple[int, int] | None, tuple[int, int] | None], ...]:
    lines = artifact.decode("utf-8").splitlines()
    pattern = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")
    derived: list[tuple[int, tuple[int, int] | None, tuple[int, int] | None]] = []
    for line_number, line in enumerate(lines, start=1):
        match = pattern.match(line)
        if match is None:
            continue
        old_start, old_count_text, new_start, new_count_text = match.groups()
        old_count = 1 if old_count_text is None else int(old_count_text)
        new_count = 1 if new_count_text is None else int(new_count_text)
        old_start_value = int(old_start)
        new_start_value = int(new_start)
        old_span = (
            None
            if old_count == 0
            else (old_start_value, old_start_value + old_count - 1)
        )
        new_span = (
            None
            if new_count == 0
            else (new_start_value, new_start_value + new_count - 1)
        )
        derived.append((line_number, old_span, new_span))
    return tuple(derived)


def _python_line_payload(**overrides: object) -> dict[str, object]:
    return {
        "locator_kind": "revision_line",
        "parent": _qualified(),
        "span": _line_span(),
        "text_encoding": TextEncoding.UTF8,
        "line_ending": LineEnding.LF,
        **overrides,
    }


def _python_artifact_payload(**overrides: object) -> dict[str, object]:
    return {
        "locator_kind": "artifact_byte",
        "parent_artifact_sha256": CANONICAL_ARTIFACT_SHA256,
        "parent_byte_length": CANONICAL_ARTIFACT_BYTE_LENGTH,
        "span": _byte_span(165, 77),
        **overrides,
    }


def _python_hunk_payload(**overrides: object) -> dict[str, object]:
    return {
        "locator_kind": "diff_hunk",
        "artifact_bytes": _artifact_locator(),
        "artifact_lines": _line_span(6, 7),
        "text_encoding": TextEncoding.UTF8,
        "line_ending": LineEnding.LF,
        "old_file": None,
        "old_lines": None,
        "new_file": _qualified("changelog/4412.bugfix.rst"),
        "new_lines": _line_span(),
        **overrides,
    }


def test_encoding_and_line_ending_vocabularies_are_exact() -> None:
    assert [(member.name, member.value) for member in TextEncoding] == [
        ("UTF8", "utf-8")
    ]
    assert [(member.name, member.value) for member in LineEnding] == [
        ("LF", "lf"),
        ("CRLF", "crlf"),
    ]
    assert len(TextEncoding.__members__) == 1
    assert len(LineEnding.__members__) == 2


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("text_encoding", "utf-8"),
        ("text_encoding", "UTF-8"),
        ("text_encoding", "utf8"),
        ("line_ending", "lf"),
        ("line_ending", "LF"),
        ("line_ending", "cr"),
        ("line_ending", "mixed"),
    ),
)
def test_python_locator_input_rejects_coercive_or_unknown_enum_strings(
    field: str,
    value: object,
) -> None:
    with pytest.raises(ValidationError):
        RevisionLineLocator.model_validate(_python_line_payload(**{field: value}))


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("text_encoding", "UTF-8"),
        ("text_encoding", "utf8"),
        ("line_ending", "LF"),
        ("line_ending", "cr"),
        ("line_ending", "mixed"),
    ),
)
def test_json_rejects_unknown_encoding_or_line_ending(
    field: str,
    value: str,
) -> None:
    payload = json.loads(_line_locator().model_dump_json())
    payload[field] = value
    with pytest.raises(ValidationError):
        RevisionLineLocator.model_validate_json(json.dumps(payload))


@pytest.mark.parametrize(
    ("start", "end"),
    ((1, 1), (1, 3), (946, 950), (MAX_LINE, MAX_LINE)),
)
def test_line_span_accepts_inclusive_minimum_multi_and_maximum_vectors(
    start: int,
    end: int,
) -> None:
    span = _line_span(start, end)
    assert tuple(OneBasedInclusiveLineSpan.model_fields) == (
        "start_line",
        "end_line",
    )
    assert (span.start_line, span.end_line) == (start, end)
    assert end - start + 1 >= 1


def test_line_span_equality_and_semantic_json_round_trip() -> None:
    span = _line_span(416, 427)
    restored = OneBasedInclusiveLineSpan.model_validate_json(span.model_dump_json())
    assert restored == span == _line_span(416, 427)
    assert restored != _line_span(416, 428)
    assert type(restored) is OneBasedInclusiveLineSpan


@pytest.mark.parametrize(
    ("start", "end"),
    (
        (0, 1),
        (-1, 1),
        (1, 0),
        (2, 1),
        (MAX_LINE + 1, MAX_LINE + 1),
        (MAX_LINE, MAX_LINE + 1),
        (True, 1),
        (1, False),
        (1.0, 1),
        (1, 1.0),
        ("1", 1),
        (1, "1"),
    ),
)
def test_line_span_rejects_invalid_order_bounds_and_coercion(
    start: object,
    end: object,
) -> None:
    with pytest.raises(ValidationError):
        OneBasedInclusiveLineSpan.model_validate({"start_line": start, "end_line": end})


@pytest.mark.parametrize(
    "field",
    (
        "column",
        "start_column",
        "end_column",
        "line_count",
        "index_base",
        "inclusive",
        "byte_offset",
        "path",
        "revision",
        "artifact_digest",
    ),
)
def test_line_span_rejects_every_non_coordinate_field(field: str) -> None:
    with pytest.raises(ValidationError):
        OneBasedInclusiveLineSpan.model_validate(
            {"start_line": 1, "end_line": 1, field: "forbidden"}
        )


def test_line_span_is_frozen_and_revalidates_constructed_instances() -> None:
    span = _line_span()
    with pytest.raises(ValidationError):
        span.start_line = 2
    with pytest.raises(ValidationError):
        span.extra = "forbidden"  # type: ignore[attr-defined]
    invalid = OneBasedInclusiveLineSpan.model_construct(start_line=0, end_line=1)
    with pytest.raises(ValidationError):
        RevisionLineLocator(
            locator_kind="revision_line",
            parent=_qualified(),
            span=invalid,
            text_encoding=TextEncoding.UTF8,
            line_ending=LineEnding.LF,
        )


@pytest.mark.parametrize(
    ("offset", "length"),
    (
        (0, 1),
        (1, 2),
        (165, 77),
        (MAX_INT64 - 1, 1),
        (0, MAX_INT64),
    ),
)
def test_byte_span_accepts_zero_based_half_open_vectors(
    offset: int,
    length: int,
) -> None:
    span = _byte_span(offset, length)
    assert tuple(ZeroBasedHalfOpenByteSpan.model_fields) == ("offset", "length")
    assert span.offset + span.length == offset + length
    assert [span.offset, span.offset + span.length] == [offset, offset + length]


def test_byte_span_semantic_json_round_trip_and_equality() -> None:
    span = _byte_span(1018, 622)
    restored = ZeroBasedHalfOpenByteSpan.model_validate_json(span.model_dump_json())
    assert restored == span == _byte_span(1018, 622)
    assert restored != _byte_span(1018, 621)
    assert type(restored) is ZeroBasedHalfOpenByteSpan


@pytest.mark.parametrize(
    ("offset", "length"),
    (
        (-1, 1),
        (0, 0),
        (0, -1),
        (MAX_INT64 + 1, 1),
        (0, MAX_INT64 + 1),
        (MAX_INT64, 1),
        (MAX_INT64 - 1, 2),
        (True, 1),
        (0, False),
        (0.0, 1),
        (0, 1.0),
        ("0", 1),
        (0, "1"),
    ),
)
def test_byte_span_rejects_invalid_bounds_overflow_and_coercion(
    offset: object,
    length: object,
) -> None:
    with pytest.raises(ValidationError):
        ZeroBasedHalfOpenByteSpan.model_validate({"offset": offset, "length": length})


@pytest.mark.parametrize(
    "field",
    ("end", "end_exclusive", "line", "path", "revision", "artifact_digest"),
)
def test_byte_span_rejects_redundant_or_parent_fields(field: str) -> None:
    with pytest.raises(ValidationError):
        ZeroBasedHalfOpenByteSpan.model_validate({"offset": 0, "length": 1, field: 1})


def test_byte_span_is_frozen_and_revalidates_constructed_instances() -> None:
    span = _byte_span()
    with pytest.raises(ValidationError):
        span.length = 2
    with pytest.raises(ValidationError):
        span.extra = "forbidden"  # type: ignore[attr-defined]
    invalid = ZeroBasedHalfOpenByteSpan.model_construct(offset=-1, length=1)
    with pytest.raises(ValidationError):
        ArtifactByteLocator(
            locator_kind="artifact_byte",
            parent_artifact_sha256=CANONICAL_ARTIFACT_SHA256,
            parent_byte_length=1,
            span=invalid,
        )


@pytest.mark.parametrize(
    ("path", "start", "end", "classification"),
    REVIEWED_LINE_VECTORS,
)
def test_canonical_reviewed_line_locators_are_honestly_classified(
    path: str,
    start: int,
    end: int,
    classification: str,
) -> None:
    locator = _line_locator(
        parent=_qualified(path, revision=_commit(CANONICAL_HEAD)),
        span=_line_span(start, end),
    )
    assert locator.locator_kind == "revision_line"
    assert locator.parent.path.root == path
    assert (locator.span.start_line, locator.span.end_line) == (start, end)
    assert locator.text_encoding is TextEncoding.UTF8
    assert locator.line_ending is LineEnding.LF
    assert classification == "reviewed_derived_interpretation"
    assert "classification" not in RevisionLineLocator.model_fields


def test_synthetic_crlf_revision_line_locator_is_explicit_not_canonical() -> None:
    locator = _line_locator(
        parent=_qualified("synthetic/crlf.txt"),
        span=_line_span(2, 4),
        line_ending=LineEnding.CRLF,
    )
    assert locator.line_ending is LineEnding.CRLF
    assert locator.parent.path.root == "synthetic/crlf.txt"


def test_revision_line_locator_fields_and_distinct_parent_span_identity() -> None:
    first = _line_locator(span=_line_span(1, 1))
    other_span = _line_locator(span=_line_span(1, 2))
    other_revision = _line_locator(
        parent=_qualified(revision=_commit("f" * 40)),
        span=_line_span(1, 1),
    )
    assert tuple(RevisionLineLocator.model_fields) == (
        "schema_version",
        "locator_kind",
        "parent",
        "span",
        "text_encoding",
        "line_ending",
    )
    assert first != other_span
    assert first != other_revision


def test_revision_line_semantic_json_restores_exact_nested_types_and_enums() -> None:
    locator = _line_locator(span=_line_span(946, 950))
    encoded = locator.model_dump_json()
    restored = RevisionLineLocator.model_validate_json(encoded)
    assert restored == locator
    assert restored.model_dump_json() == encoded
    assert type(restored) is RevisionLineLocator
    assert type(restored.parent) is RevisionQualifiedPath
    assert type(restored.span) is OneBasedInclusiveLineSpan
    assert type(restored.text_encoding) is TextEncoding
    assert type(restored.line_ending) is LineEnding


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("parent", "src/example.py"),
        ("parent", "a" * 64),
        ("parent", _ref_observation()),
        ("parent", _role_assignment()),
        ("parent", _qualified().model_dump()),
        ("span", _byte_span()),
        ("span", {"start_line": 1, "end_line": 1}),
    ),
)
def test_revision_line_python_input_requires_exact_typed_parent_and_span(
    field: str,
    value: object,
) -> None:
    with pytest.raises(ValidationError):
        RevisionLineLocator.model_validate(_python_line_payload(**{field: value}))


@pytest.mark.parametrize("schema_version", (0, 2, "1", True, 1.0, None))
def test_revision_line_schema_version_is_exact(schema_version: object) -> None:
    with pytest.raises(ValidationError):
        RevisionLineLocator.model_validate(
            _python_line_payload(schema_version=schema_version)
        )


@pytest.mark.parametrize(
    "field",
    (
        "byte_span",
        "artifact_digest",
        "role",
        "applicable",
        "reviewed",
        "causal",
        "history",
        "column",
        "exists",
    ),
)
def test_revision_line_rejects_cross_coordinate_or_interpretive_fields(
    field: str,
) -> None:
    with pytest.raises(ValidationError):
        RevisionLineLocator.model_validate(_python_line_payload(**{field: "x"}))


def test_revision_line_is_frozen_and_outer_instances_revalidate() -> None:
    locator = _line_locator()
    with pytest.raises(ValidationError):
        locator.span = _line_span(2, 2)
    with pytest.raises(ValidationError):
        locator.extra = "forbidden"  # type: ignore[attr-defined]
    invalid = RevisionLineLocator.model_construct(
        schema_version=2,
        locator_kind="revision_line",
        parent=_qualified(),
        span=_line_span(),
        text_encoding=TextEncoding.UTF8,
        line_ending=LineEnding.LF,
    )
    with pytest.raises(ValidationError):
        RevisionLineLocator.model_validate(invalid)


@pytest.mark.parametrize(
    ("offset", "length", "_start_line", "_end_line", "_slice_sha256"),
    CANONICAL_BYTE_VECTORS,
)
def test_canonical_artifact_byte_locators_bind_exact_parent_and_span(
    offset: int,
    length: int,
    _start_line: int,
    _end_line: int,
    _slice_sha256: str,
) -> None:
    locator = _artifact_locator(offset, length)
    assert tuple(ArtifactByteLocator.model_fields) == (
        "schema_version",
        "locator_kind",
        "parent_artifact_sha256",
        "parent_byte_length",
        "span",
    )
    assert locator.parent_artifact_sha256 == CANONICAL_ARTIFACT_SHA256
    assert locator.parent_byte_length == CANONICAL_ARTIFACT_BYTE_LENGTH
    assert (locator.span.offset, locator.span.length) == (offset, length)
    assert locator.span.offset + locator.span.length <= locator.parent_byte_length


def test_artifact_span_may_end_exactly_at_parent_length() -> None:
    locator = _artifact_locator(1018, 622)
    assert locator.span.offset + locator.span.length == locator.parent_byte_length


def test_artifact_byte_semantic_json_restores_exact_nested_type() -> None:
    locator = _artifact_locator(439, 394)
    encoded = locator.model_dump_json()
    restored = ArtifactByteLocator.model_validate_json(encoded)
    assert restored == locator
    assert restored.model_dump_json() == encoded
    assert type(restored) is ArtifactByteLocator
    assert type(restored.span) is ZeroBasedHalfOpenByteSpan


@pytest.mark.parametrize(
    "digest",
    (
        "f" * 63,
        "f" * 65,
        "F" * 64,
        "g" * 64,
        "é" * 64,
        "0" * 64,
        " f" + "0" * 62,
    ),
)
def test_artifact_parent_digest_is_exact_lowercase_nonzero_sha256(
    digest: str,
) -> None:
    with pytest.raises(ValidationError):
        ArtifactByteLocator.model_validate(
            _python_artifact_payload(parent_artifact_sha256=digest)
        )


@pytest.mark.parametrize(
    "parent_byte_length",
    (-1, MAX_INT64 + 1, True, 1.0, "1640", None),
)
def test_artifact_parent_length_is_exact_nonnegative_bounded_integer(
    parent_byte_length: object,
) -> None:
    with pytest.raises(ValidationError):
        ArtifactByteLocator.model_validate(
            _python_artifact_payload(parent_byte_length=parent_byte_length)
        )


@pytest.mark.parametrize(
    "span",
    (
        _byte_span(1639, 2),
        _byte_span(1640, 1),
        _line_span(1, 1),
        {"offset": 165, "length": 77},
    ),
)
def test_artifact_locator_rejects_out_of_parent_or_wrong_typed_span(
    span: object,
) -> None:
    with pytest.raises(ValidationError):
        ArtifactByteLocator.model_validate(_python_artifact_payload(span=span))


def test_zero_byte_parent_cannot_contain_nonempty_span() -> None:
    with pytest.raises(ValidationError):
        ArtifactByteLocator.model_validate(
            _python_artifact_payload(
                parent_byte_length=0,
                span=_byte_span(0, 1),
            )
        )


@pytest.mark.parametrize(
    "field",
    (
        "selected_slice_sha256",
        "selected_byte_digest",
        "artifact_path",
        "media_type",
        "request",
        "observation",
        "acquisition_provenance",
        "line_span",
    ),
)
def test_artifact_locator_rejects_slice_digest_path_media_or_provenance(
    field: str,
) -> None:
    with pytest.raises(ValidationError):
        ArtifactByteLocator.model_validate(
            _python_artifact_payload(**{field: "forbidden"})
        )


def test_artifact_locator_is_frozen() -> None:
    locator = _artifact_locator()
    with pytest.raises(ValidationError):
        locator.parent_byte_length = 2000
    with pytest.raises(ValidationError):
        locator.extra = "forbidden"  # type: ignore[attr-defined]


def test_retained_diff_parent_and_selected_bytes_replay_exactly() -> None:
    artifact = DIFF_ARTIFACT.read_bytes()
    assert len(artifact) == CANONICAL_ARTIFACT_BYTE_LENGTH
    assert hashlib.sha256(artifact).hexdigest() == CANONICAL_ARTIFACT_SHA256
    assert artifact.count(b"\r") == 0
    assert artifact.count(b"\n") == 45
    assert artifact.endswith(b"\n")
    for (
        offset,
        length,
        _start_line,
        _end_line,
        selected_sha256,
    ) in CANONICAL_BYTE_VECTORS:
        locator = _artifact_locator(offset, length)
        selected = artifact[
            locator.span.offset : locator.span.offset + locator.span.length
        ]
        assert len(selected) == locator.span.length
        assert hashlib.sha256(selected).hexdigest() == selected_sha256


def test_artifact_line_and_byte_coordinates_correspond_only_in_assurance() -> None:
    artifact = DIFF_ARTIFACT.read_bytes()
    line_starts = [0]
    line_ends: list[int] = []
    for index, value in enumerate(artifact):
        if value == 10:
            line_ends.append(index + 1)
            line_starts.append(index + 1)
    for offset, length, start_line, end_line, _slice_sha256 in CANONICAL_BYTE_VECTORS:
        assert line_starts[start_line - 1] == offset
        assert line_ends[end_line - 1] == offset + length


def test_exact_unified_diff_headers_derive_canonical_old_and_new_spans() -> None:
    artifact = DIFF_ARTIFACT.read_bytes()
    assert _derive_unified_hunks(artifact) == (
        (6, None, (1, 1)),
        (12, (946, 952), (946, 953)),
        (26, (413, 418), (413, 431)),
    )
    lines = artifact.decode("utf-8").splitlines()
    assert tuple(
        line.startswith(prefix)
        for line, prefix in zip(
            (lines[5], lines[11], lines[25]),
            (
                "@@ -0,0 +1 @@",
                "@@ -946,7 +946,8 @@",
                "@@ -413,6 +413,19 @@",
            ),
            strict=True,
        )
    ) == (True, True, True)


@pytest.mark.parametrize(
    ("old", "new"),
    (
        (b"@@ -946,7 +946,8 @@", b"@@ -946,6 +946,8 @@"),
        (b"@@ -946,7 +946,8 @@", b"@@ -946,7 +946,7 @@"),
        (b"@@ -413,6 +413,19 @@", b"@@ -413,6 +413,18 @@"),
    ),
)
def test_hunk_header_span_mutations_are_rejected(old: bytes, new: bytes) -> None:
    artifact = DIFF_ARTIFACT.read_bytes()
    assert old in artifact
    mutated = artifact.replace(old, new, 1)
    assert _derive_unified_hunks(mutated) != _derive_unified_hunks(artifact)


@pytest.mark.parametrize(
    (
        "offset",
        "length",
        "artifact_start",
        "artifact_end",
        "old_path",
        "old_range",
        "new_path",
        "new_range",
    ),
    CANONICAL_HUNK_VECTORS,
)
def test_canonical_added_and_modified_hunks_preserve_exact_sides(
    offset: int,
    length: int,
    artifact_start: int,
    artifact_end: int,
    old_path: str | None,
    old_range: tuple[int, int] | None,
    new_path: str | None,
    new_range: tuple[int, int] | None,
) -> None:
    old_file = (
        None
        if old_path is None
        else _qualified(old_path, revision=_commit(CANONICAL_BASE))
    )
    old_lines = None if old_range is None else _line_span(*old_range)
    new_file = (
        None
        if new_path is None
        else _qualified(new_path, revision=_commit(CANONICAL_HEAD))
    )
    new_lines = None if new_range is None else _line_span(*new_range)
    locator = DiffHunkLocator(
        locator_kind="diff_hunk",
        artifact_bytes=_artifact_locator(offset, length),
        artifact_lines=_line_span(artifact_start, artifact_end),
        text_encoding=TextEncoding.UTF8,
        line_ending=LineEnding.LF,
        old_file=old_file,
        old_lines=old_lines,
        new_file=new_file,
        new_lines=new_lines,
    )
    assert (locator.artifact_lines.start_line, locator.artifact_lines.end_line) == (
        artifact_start,
        artifact_end,
    )
    assert (locator.artifact_bytes.span.offset, locator.artifact_bytes.span.length) == (
        offset,
        length,
    )
    assert locator.old_file == old_file
    assert locator.old_lines == old_lines
    assert locator.new_file == new_file
    assert locator.new_lines == new_lines


def test_synthetic_deleted_hunk_allows_only_complete_old_side() -> None:
    locator = DiffHunkLocator(
        locator_kind="diff_hunk",
        artifact_bytes=_artifact_locator(),
        artifact_lines=_line_span(6, 7),
        text_encoding=TextEncoding.UTF8,
        line_ending=LineEnding.LF,
        old_file=_qualified("deleted/file.py", revision=_commit(CANONICAL_BASE)),
        old_lines=_line_span(8, 10),
        new_file=None,
        new_lines=None,
    )
    assert locator.old_file is not None
    assert locator.old_lines == _line_span(8, 10)
    assert locator.new_file is locator.new_lines is None


def test_synthetic_cross_repository_hunk_does_not_fabricate_equality() -> None:
    old_repository = _repository("111")
    new_repository = _repository("222", provider="gitlab")
    locator = DiffHunkLocator(
        locator_kind="diff_hunk",
        artifact_bytes=_artifact_locator(),
        artifact_lines=_line_span(6, 7),
        text_encoding=TextEncoding.UTF8,
        line_ending=LineEnding.LF,
        old_file=_qualified(
            "old/name.py",
            revision=_commit("1" * 40),
            repository=old_repository,
        ),
        old_lines=_line_span(10, 12),
        new_file=_qualified(
            "new/name.py",
            revision=_commit("2" * 40),
            repository=new_repository,
        ),
        new_lines=_line_span(20, 24),
    )
    assert locator.old_file is not None and locator.new_file is not None
    assert locator.old_file.repository_identity != locator.new_file.repository_identity
    assert locator.old_file.path != locator.new_file.path
    assert locator.old_lines != locator.new_lines


def test_synthetic_sha256_and_crlf_hunk_preserves_distinct_sides() -> None:
    locator = DiffHunkLocator(
        locator_kind="diff_hunk",
        artifact_bytes=_artifact_locator(),
        artifact_lines=_line_span(2, 5),
        text_encoding=TextEncoding.UTF8,
        line_ending=LineEnding.CRLF,
        old_file=_qualified(
            "old.txt",
            revision=_commit("1" * 64, GitHashAlgorithm.SHA256),
        ),
        old_lines=_line_span(100, 102),
        new_file=_qualified(
            "new.txt",
            revision=_commit("2" * 64, GitHashAlgorithm.SHA256),
        ),
        new_lines=_line_span(200, 204),
    )
    assert locator.line_ending is LineEnding.CRLF
    assert locator.old_file is not None and locator.new_file is not None
    assert locator.old_file.revision.algorithm is GitHashAlgorithm.SHA256
    assert locator.new_file.revision.algorithm is GitHashAlgorithm.SHA256
    assert locator.old_lines == _line_span(100, 102)
    assert locator.new_lines == _line_span(200, 204)


def test_hunk_allows_mixed_old_and_new_revision_hash_algorithms() -> None:
    locator = DiffHunkLocator(
        locator_kind="diff_hunk",
        artifact_bytes=_artifact_locator(),
        artifact_lines=_line_span(6, 7),
        text_encoding=TextEncoding.UTF8,
        line_ending=LineEnding.LF,
        old_file=_qualified(
            "old.txt",
            revision=_commit("1" * 40, GitHashAlgorithm.SHA1),
        ),
        old_lines=_line_span(1, 1),
        new_file=_qualified(
            "new.txt",
            revision=_commit("2" * 64, GitHashAlgorithm.SHA256),
        ),
        new_lines=_line_span(1, 2),
    )
    assert locator.old_file is not None and locator.new_file is not None
    assert locator.old_file.revision.algorithm is GitHashAlgorithm.SHA1
    assert locator.new_file.revision.algorithm is GitHashAlgorithm.SHA256


@pytest.mark.parametrize(
    ("old_file", "old_lines", "new_file", "new_lines"),
    (
        (_qualified("old.py"), None, _qualified("new.py"), _line_span()),
        (None, _line_span(), _qualified("new.py"), _line_span()),
        (_qualified("old.py"), _line_span(), _qualified("new.py"), None),
        (_qualified("old.py"), _line_span(), None, _line_span()),
        (None, None, None, None),
    ),
)
def test_hunk_rejects_unpaired_or_absent_sides(
    old_file: RevisionQualifiedPath | None,
    old_lines: OneBasedInclusiveLineSpan | None,
    new_file: RevisionQualifiedPath | None,
    new_lines: OneBasedInclusiveLineSpan | None,
) -> None:
    with pytest.raises(ValidationError):
        DiffHunkLocator.model_validate(
            _python_hunk_payload(
                old_file=old_file,
                old_lines=old_lines,
                new_file=new_file,
                new_lines=new_lines,
            )
        )


@pytest.mark.parametrize("missing", ("old_file", "old_lines", "new_file", "new_lines"))
def test_hunk_requires_explicit_nullable_side_fields(missing: str) -> None:
    payload = _python_hunk_payload()
    del payload[missing]
    with pytest.raises(ValidationError):
        DiffHunkLocator.model_validate(payload)


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("artifact_bytes", _byte_span()),
        ("artifact_bytes", _artifact_locator().model_dump()),
        ("artifact_lines", _byte_span()),
        ("artifact_lines", {"start_line": 6, "end_line": 7}),
        ("old_file", "old.py"),
        ("new_file", "new.py"),
        ("old_lines", _byte_span()),
        ("new_lines", _byte_span()),
    ),
)
def test_hunk_python_input_requires_exact_typed_nested_values(
    field: str,
    value: object,
) -> None:
    with pytest.raises(ValidationError):
        DiffHunkLocator.model_validate(_python_hunk_payload(**{field: value}))


@pytest.mark.parametrize(
    "field",
    (
        "role",
        "topology",
        "ref",
        "applicable",
        "reviewed",
        "relationship",
        "causal",
        "old_side",
        "new_side",
        "relation",
        "column",
        "history",
        "provider_provenance",
        "acquisition_provenance",
    ),
)
def test_hunk_rejects_interpretive_history_or_side_enum_fields(field: str) -> None:
    with pytest.raises(ValidationError):
        DiffHunkLocator.model_validate(_python_hunk_payload(**{field: "x"}))


def test_hunk_fields_and_semantic_json_preserve_order_and_exact_types() -> None:
    locator = _hunk(
        artifact_bytes=_artifact_locator(439, 394),
        artifact_lines=_line_span(12, 21),
        old_file=_qualified(
            "src/_pytest/assertion/rewrite.py",
            revision=_commit(CANONICAL_BASE),
        ),
        old_lines=_line_span(946, 952),
        new_file=_qualified(
            "src/_pytest/assertion/rewrite.py",
            revision=_commit(CANONICAL_HEAD),
        ),
        new_lines=_line_span(946, 953),
    )
    assert tuple(DiffHunkLocator.model_fields) == (
        "schema_version",
        "locator_kind",
        "artifact_bytes",
        "artifact_lines",
        "text_encoding",
        "line_ending",
        "old_file",
        "old_lines",
        "new_file",
        "new_lines",
    )
    encoded = locator.model_dump_json()
    restored = DiffHunkLocator.model_validate_json(encoded)
    assert restored == locator
    assert restored.model_dump_json() == encoded
    assert type(restored.artifact_bytes) is ArtifactByteLocator
    assert type(restored.artifact_lines) is OneBasedInclusiveLineSpan
    assert type(restored.old_file) is RevisionQualifiedPath
    assert type(restored.old_lines) is OneBasedInclusiveLineSpan
    assert type(restored.new_file) is RevisionQualifiedPath
    assert type(restored.new_lines) is OneBasedInclusiveLineSpan
    assert restored.old_lines == _line_span(946, 952)
    assert restored.new_lines == _line_span(946, 953)


def test_hunk_is_frozen_and_revalidates_invalid_constructed_outer_model() -> None:
    locator = _hunk()
    with pytest.raises(ValidationError):
        locator.artifact_lines = _line_span(1, 1)
    invalid = DiffHunkLocator.model_construct(
        schema_version=1,
        locator_kind="diff_hunk",
        artifact_bytes=_artifact_locator(),
        artifact_lines=_line_span(6, 7),
        text_encoding=TextEncoding.UTF8,
        line_ending=LineEnding.LF,
        old_file=None,
        old_lines=None,
        new_file=None,
        new_lines=None,
    )
    with pytest.raises(ValidationError):
        DiffHunkLocator.model_validate(invalid)


@pytest.mark.parametrize(
    "locator",
    (_line_locator(), _artifact_locator(), _hunk()),
)
def test_discriminated_union_json_restores_exact_concrete_type(
    locator: _BoundedLocatorRuntime,
) -> None:
    restored = LOCATOR_ADAPTER.validate_json(locator.model_dump_json())
    assert restored == locator
    assert type(restored) is type(locator)


def test_union_does_not_collapse_models_with_overlapping_nested_values() -> None:
    line_span = _line_span(1, 1)
    line = _line_locator(span=line_span)
    artifact = _artifact_locator(0, 1, parent_byte_length=1)
    hunk = _hunk(
        artifact_bytes=artifact,
        artifact_lines=line_span,
        new_lines=line_span,
    )
    restored = tuple(
        LOCATOR_ADAPTER.validate_json(locator.model_dump_json())
        for locator in (line, artifact, hunk)
    )
    assert tuple(type(item) for item in restored) == (
        RevisionLineLocator,
        ArtifactByteLocator,
        DiffHunkLocator,
    )


def test_bounded_locator_schema_has_exact_discriminator_mapping_and_one_of() -> None:
    schema = LOCATOR_ADAPTER.json_schema()
    assert schema["discriminator"] == {
        "propertyName": "locator_kind",
        "mapping": {
            "revision_line": "#/$defs/RevisionLineLocator",
            "artifact_byte": "#/$defs/ArtifactByteLocator",
            "diff_hunk": "#/$defs/DiffHunkLocator",
        },
    }
    assert schema["oneOf"] == [
        {"$ref": "#/$defs/RevisionLineLocator"},
        {"$ref": "#/$defs/ArtifactByteLocator"},
        {"$ref": "#/$defs/DiffHunkLocator"},
    ]


@pytest.mark.parametrize(
    "mutation",
    ("missing", "unknown", "wrong-shape"),
)
def test_union_rejects_missing_unknown_or_wrong_discriminator(
    mutation: str,
) -> None:
    payload: dict[str, Any] = json.loads(_line_locator().model_dump_json())
    if mutation == "missing":
        del payload["locator_kind"]
    elif mutation == "unknown":
        payload["locator_kind"] = "line"
    else:
        payload["locator_kind"] = "artifact_byte"
    with pytest.raises(ValidationError):
        LOCATOR_ADAPTER.validate_json(json.dumps(payload))


def test_models_have_exact_strict_frozen_configuration_and_no_aliases() -> None:
    for model in (
        OneBasedInclusiveLineSpan,
        ZeroBasedHalfOpenByteSpan,
        RevisionLineLocator,
        ArtifactByteLocator,
        DiffHunkLocator,
    ):
        assert issubclass(model, BaseModel)
        assert model.model_config.get("frozen") is True
        assert model.model_config.get("strict") is True
        assert model.model_config.get("extra") == "forbid"
        assert model.model_config.get("revalidate_instances") == "always"
        assert model.model_config.get("validate_default") is True
        assert all(
            field.alias is None
            and field.validation_alias is None
            and field.serialization_alias is None
            for field in model.model_fields.values()
        )


def test_locator_fields_exclude_columns_digest_applicability_and_provenance() -> None:
    fields = {
        *RevisionLineLocator.model_fields,
        *ArtifactByteLocator.model_fields,
        *DiffHunkLocator.model_fields,
    }
    assert not fields & {
        "column",
        "start_column",
        "end_column",
        "selected_slice_sha256",
        "selected_byte_digest",
        "exists",
        "entry_kind",
        "blob_identity",
        "tree_identity",
        "applicable",
        "reviewed",
        "role",
        "causal",
        "relationship",
        "history",
        "confidence",
        "provider_provenance",
        "acquisition_provenance",
        "artifact_path",
        "media_type",
    }


def test_existing_revision_path_fields_remain_coordinate_free() -> None:
    assert tuple(RevisionQualifiedPath.model_fields) == (
        "schema_version",
        "repository_identity",
        "revision",
        "path",
    )
    assert not set(RevisionQualifiedPath.model_fields) & {
        "span",
        "line",
        "byte",
        "column",
        "locator_kind",
    }


def test_production_locator_module_has_no_artifact_file_git_or_network_io() -> None:
    source = REVISION_SOURCE.read_text(encoding="utf-8")
    tree = ast.parse(source)
    forbidden_modules = {
        "hashlib",
        "git",
        "os",
        "pathlib",
        "socket",
        "subprocess",
        "urllib",
    }
    forbidden_calls = {
        "open",
        "read",
        "read_bytes",
        "read_text",
        "resolve",
        "exists",
        "run",
        "Popen",
        "getenv",
    }
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            assert (
                not {alias.name.split(".")[0] for alias in node.names}
                & forbidden_modules
            )
        elif isinstance(node, ast.ImportFrom):
            assert node.module is not None
            assert node.module.split(".")[0] not in forbidden_modules
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                assert node.func.id not in forbidden_calls
            elif isinstance(node.func, ast.Attribute):
                assert node.func.attr not in forbidden_calls


def test_exports_package_roots_and_production_inventory_are_exact() -> None:
    source = REVISION_SOURCE.read_text(encoding="utf-8")
    _validate_revision_surface(source)
    assert revision_module.__all__ == EXPECTED_EXPORTS
    assert len(revision_module.__all__) == len(set(revision_module.__all__)) == 23
    assert faultatlas.__all__ == ["__version__"]
    assert not any(hasattr(faultatlas, name) for name in S05_EXPORTS)
    assert not any(hasattr(domain_package, name) for name in S05_EXPORTS)
    paths = {
        path.relative_to(REPOSITORY_ROOT).as_posix()
        for path in (REPOSITORY_ROOT / "src").rglob("*.py")
    }
    _validate_production_inventory(paths)


def test_s06_contract_corpus_is_exact_and_later_surfaces_remain_absent() -> None:
    forbidden_paths = {
        "reference_corpus/contracts/revision",
        "reference_corpus/contracts/locators",
        "src/faultatlas/domain/locator_reader.py",
        "src/faultatlas/domain/locator_resolver.py",
    }
    assert not {
        relative
        for relative in forbidden_paths
        if (REPOSITORY_ROOT / relative).exists()
    }
    actual_corpus_paths = {
        path.relative_to(REPOSITORY_ROOT).as_posix()
        for path in S06_CORPUS_ROOT.iterdir()
    }
    assert actual_corpus_paths == EXPECTED_S06_CORPUS_PATHS
    assert all(
        path.is_file() and not path.is_symlink() for path in S06_CORPUS_ROOT.iterdir()
    )
    assert not (
        REPOSITORY_ROOT / "reference_corpus/contracts/revision-locator/closures"
    ).exists()
    _validate_no_deferred_surface(REVISION_SOURCE.read_text(encoding="utf-8"))


@pytest.mark.parametrize("missing_export", tuple(S05_EXPORTS))
def test_omitted_locator_export_mutations_are_rejected(missing_export: str) -> None:
    source = REVISION_SOURCE.read_text(encoding="utf-8")
    mutated = source.replace(f'    "{missing_export}",\n', "", 1)
    with pytest.raises(AssertionError):
        _validate_revision_surface(mutated)


def test_unexpected_revision_export_mutation_is_rejected() -> None:
    source = REVISION_SOURCE.read_text(encoding="utf-8")
    mutated = source.replace(
        '    "BoundedLocator",\n',
        '    "BoundedLocator",\n    "UnexpectedLocator",\n',
        1,
    )
    with pytest.raises(AssertionError):
        _validate_revision_surface(mutated)


def test_missing_revision_and_unexpected_ninth_production_file_are_rejected() -> None:
    with pytest.raises(AssertionError):
        _validate_production_inventory(
            EXPECTED_PRODUCTION_FILES - {"src/faultatlas/domain/revision.py"}
        )
    with pytest.raises(AssertionError):
        _validate_production_inventory(
            EXPECTED_PRODUCTION_FILES | {"src/faultatlas/domain/locator.py"}
        )


def test_package_root_export_mutation_is_rejected() -> None:
    with pytest.raises(AssertionError):
        _validate_package_exports(["__version__", "RevisionLineLocator"])


def test_s06_corpus_path_mutation_is_rejected() -> None:
    def validate(paths: set[str]) -> None:
        assert paths == EXPECTED_S06_CORPUS_PATHS
        assert not paths & {
            "reference_corpus/contracts/revision/v1/manifest.json",
            "reference_corpus/contracts/locators/v1/manifest.json",
        }

    validate(EXPECTED_S06_CORPUS_PATHS)
    with pytest.raises(AssertionError):
        validate(EXPECTED_S06_CORPUS_PATHS - {f"{S06_CORPUS_RELATIVE}/contract.md"})
    with pytest.raises(AssertionError):
        validate(EXPECTED_S06_CORPUS_PATHS | {f"{S06_CORPUS_RELATIVE}/extra.json"})
    with pytest.raises(AssertionError):
        validate({"reference_corpus/contracts/locators/v1/manifest.json"})


def test_evidence_envelope_surface_mutation_is_rejected() -> None:
    source = REVISION_SOURCE.read_text(encoding="utf-8")
    mutated = source + "\n\nclass EvidenceEnvelope:\n    pass\n"
    with pytest.raises(AssertionError):
        _validate_no_deferred_surface(mutated)


def test_evidence_classifications_are_distinct_and_not_model_fields() -> None:
    assert EVIDENCE_CLASSIFICATIONS == {
        "byte_locator": "exact_byte_locator_fact",
        "hunk_and_additions": "deterministic_derivation",
        "role_and_applicability": "reviewed_derived_interpretation",
    }
    assert len(set(EVIDENCE_CLASSIFICATIONS.values())) == 3
    model_fields = {
        *ArtifactByteLocator.model_fields,
        *DiffHunkLocator.model_fields,
        *RevisionLineLocator.model_fields,
    }
    assert not model_fields & {
        "classification",
        "slice_sha256",
        "role",
        "applicability",
    }


def test_acquisition_locator_records_replay_without_promoting_review_semantics() -> (
    None
):
    document = json.loads(ACQUISITION.read_text(encoding="utf-8"))
    records = document["locators"]
    assert len(records) == 3
    assert (
        tuple(
            (
                record["offset"],
                record["length"],
                record["diff_line_start"],
                record["diff_line_end"],
                record["sha256"],
            )
            for record in records
        )
        == CANONICAL_BYTE_VECTORS
    )
    assert all(
        record["parent_artifact_sha256"] == CANONICAL_ARTIFACT_SHA256
        for record in records
    )
    assert all(
        record["classification"] == EVIDENCE_CLASSIFICATIONS for record in records
    )
    assert tuple(record["hunk_new_file_span"] for record in records) == (
        {"start": 1, "end": 1},
        {"start": 946, "end": 953},
        {"start": 413, "end": 431},
    )
    assert tuple(record["applicable_new_file_line_ranges"] for record in records) == (
        [{"start": 1, "end": 1}],
        [{"start": 946, "end": 950}],
        [{"start": 416, "end": 427}],
    )
    assert not {
        "classification",
        "role",
        "applicability",
        "sha256",
    } & {
        *ArtifactByteLocator.model_fields,
        *DiffHunkLocator.model_fields,
        *RevisionLineLocator.model_fields,
    }


def test_semantic_json_is_not_claimed_as_canonical_bytes() -> None:
    source = REVISION_SOURCE.read_text(encoding="utf-8")
    assert "semantic rather than a canonical wire format" in source
    assert "verify coordinate content" in source
    assert "resolve symbolic refs or locators" in source
