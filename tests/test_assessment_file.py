"""Authored file bytes, real ext4 workflow, and bounded failure/effect controls."""

from __future__ import annotations

import errno
import inspect
import json
import os
import socket
import stat
import subprocess
import sys
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier
from typing import Any, cast

import pytest
from test_assessment_inspection import EXPECTED_VIEW
from test_supplied_assessment import rich_wire, sample_wire

import faultatlas
import faultatlas.assessment_file as module
from faultatlas.assessment_file import (
    AssessmentFileError,
    inspect_assessment_file,
    save_assessment_as_new,
)

SPARSE = b"""{"format":"faultatlas-supplied-assessment","version":1,"assessment":{
"attribution":{"supplier":"Example author","rationale":"Synthetic input for a structural review."},
"basis":{"source":{"pattern":"00000000-0000-4000-8000-000000000001","pattern_statement":"Repeated evaluation may repeat a side effect."},
"target":{"snapshot":{"repository":{"provider":"github","provider_repository_id":"1001"},"revision":{"kind":"commit","algorithm":"sha1","full_digest":"1111111111111111111111111111111111111111"}},"declared_host":"github.com","declared_visibility":"public"},
"conditions":[{"key":"once","statement":"A side-effecting expression is evaluated no more than once."}]},
"opinions":[{"key":"op-a","condition":{"key":"once","statement":"A side-effecting expression is evaluated no more than once."},"position":"unknown","statement":"No target run or inspected target material was supplied.","attribution":{"supplier":"Reviewer A","rationale":"The evaluation count cannot be established from this file."}}]}}
"""

# Full bytes authored independently, including every owning default and key order.
CANONICAL = (
    b'{"assessment":{"attribution":{"rationale":"Synthetic input for a structural review.",'
    b'"supplier":"Example author"},"basis":{"conditions":[{"key":"once",'
    b'"statement":"A side-effecting expression is evaluated no more than once."}],'
    b'"context_statement":null,"material_omission":null,"materials":null,"source":{'
    b'"pattern":"00000000-0000-4000-8000-000000000001",'
    b'"pattern_statement":"Repeated evaluation may repeat a side effect."},'
    b'"target":{"declared_host":"github.com","declared_visibility":"public","scope":null,'
    b'"snapshot":{"repository":{"provider":"github","provider_repository_id":"1001",'
    b'"schema_version":1},"revision":{"algorithm":"sha1",'
    b'"full_digest":"1111111111111111111111111111111111111111","kind":"commit",'
    b'"schema_version":1}}}},"conflicts":[],"opinions":[{"attribution":{'
    b'"rationale":"The evaluation count cannot be established from this file.",'
    b'"supplier":"Reviewer A"},"condition":{"key":"once",'
    b'"statement":"A side-effecting expression is evaluated no more than once."},'
    b'"key":"op-a","material_keys":[],"position":"unknown",'
    b'"statement":"No target run or inspected target material was supplied."}],'
    b'"overall_opinion":null},"format":"faultatlas-supplied-assessment","version":1}\n'
)


def _expected_view(path: str, body: str = EXPECTED_VIEW) -> str:
    quoted = json.dumps(path, ensure_ascii=True).replace("\x7f", "\\u007f")
    return (
        f'Selected assessment file: {quoted}\nFormat: "faultatlas-supplied-assessment"\nVersion: 1\n'
        + body
    )


def _assert_real_ext4(path: Path) -> None:
    descriptor = os.open(path, os.O_PATH | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        with open(f"/proc/self/fdinfo/{descriptor}", "rb") as stream:
            info = stream.read(65537)
        with open("/proc/self/mountinfo", "rb") as stream:
            mounts = stream.read(1048577)
        assert len(info) <= 65536 and len(mounts) <= 1048576
        ids = [
            line.split()[1] for line in info.splitlines() if line.startswith(b"mnt_id:")
        ]
        assert len(ids) == 1
        rows = [line for line in mounts.splitlines() if line.split()[0] == ids[0]]
        assert len(rows) == 1 and rows[0].split(b" - ", 1)[1].split()[0] == b"ext4"
        assert os.fstat(descriptor).st_uid == os.geteuid()
        assert not os.fstat(descriptor).st_mode & 0o022
    finally:
        os.close(descriptor)


@pytest.fixture
def selected(tmp_path: Path) -> tuple[Path, Path]:
    _assert_real_ext4(tmp_path)
    source = tmp_path / "source.json"
    source.write_bytes(SPARSE)
    source.chmod(0o600)
    return source, tmp_path / "saved.json"


def _envelope(value: dict[str, Any]) -> bytes:
    return json.dumps(
        {"format": "faultatlas-supplied-assessment", "version": 1, "assessment": value},
        ensure_ascii=False,
    ).encode()


def _failure(
    call: Callable[[], object],
    code: str,
    *,
    visibility: str = "not_published",
    synced: bool = False,
    cancelled: bool = False,
) -> AssessmentFileError:
    with pytest.raises(AssessmentFileError) as caught:
        call()
    error = caught.value
    assert error.code == code
    assert error.output_visibility == visibility
    assert error.sync_completed is synced and error.cancel_requested is cancelled
    assert len(str(error).encode()) <= 16384
    assert (
        str(error).isascii() and "\x7f" not in str(error) and "\x1b" not in str(error)
    )
    return error


def test_authored_sparse_inspect_save_reopen_and_resave(
    selected: tuple[Path, Path],
) -> None:
    source, target = selected
    initial = source.read_bytes(), stat.S_IMODE(source.stat().st_mode)
    assert json.loads(CANONICAL)["assessment"] == sample_wire()
    assert inspect_assessment_file(str(source)) == _expected_view(str(source))
    assert save_assessment_as_new(str(source), str(target)) == str(target)
    assert target.read_bytes() == CANONICAL
    assert stat.S_IMODE(target.stat().st_mode) == 0o600
    assert inspect_assessment_file(str(target)) == _expected_view(str(target))
    third = target.with_name("resaved.json")
    assert save_assessment_as_new(str(target), str(third)) == str(third)
    assert third.read_bytes() == CANONICAL
    assert (source.read_bytes(), stat.S_IMODE(source.stat().st_mode)) == initial


def test_explicit_defaults_and_sparse_have_identical_canonical_bytes(
    selected: tuple[Path, Path],
) -> None:
    source, target = selected
    source.write_bytes(_envelope(sample_wire()))
    save_assessment_as_new(str(source), str(target))
    assert target.read_bytes() == CANONICAL


@pytest.mark.parametrize("state", ["not_supplied", "omitted", "empty", "rich"])
def test_invariant_information_order_and_attribution_survive(
    selected: tuple[Path, Path], state: str
) -> None:
    source, target = selected
    wire = rich_wire()
    wire["basis"]["source"] = {
        "invariant": "00000000-0000-4000-8000-000000000001",
        "invariant_statement": "A supplied invariant remains a proposition.",
    }
    wire["basis"]["context_statement"] = "  观察 verified \u202e\n\t\x1b\x7f  "
    if state != "rich":
        wire["basis"]["materials"] = [] if state == "empty" else None
        wire["basis"]["material_omission"] = (
            "  未提供  " if state == "omitted" else None
        )
        for opinion in wire["opinions"]:
            opinion["material_keys"] = []
    source.write_bytes(_envelope(wire))
    original_view = inspect_assessment_file(str(source)).split("\n", 3)[3]
    save_assessment_as_new(str(source), str(target))
    assert json.loads(target.read_bytes())["assessment"] == wire
    reopened = inspect_assessment_file(str(target)).split("\n", 3)[3]
    assert reopened == original_view
    assert reopened.isascii() and "\x1b" not in reopened and "\x7f" not in reopened
    assert (
        'caller position="stated"' in reopened and "Overall caller opinion" in reopened
    )
    assert reopened.count("caller declaration") == 2


def test_exact_api_signatures_and_no_package_reexports() -> None:
    assert module.__all__ == [
        "AssessmentFileError",
        "inspect_assessment_file",
        "save_assessment_as_new",
    ]
    assert issubclass(AssessmentFileError, Exception)
    for operation, names in [
        (inspect_assessment_file, ["input_path", "cancelled"]),
        (save_assessment_as_new, ["input_path", "output_path", "cancelled"]),
    ]:
        parameters = inspect.signature(operation).parameters
        assert list(parameters) == names
        assert parameters["cancelled"].kind == inspect.Parameter.KEYWORD_ONLY
        assert parameters["cancelled"].default is None
    assert not hasattr(faultatlas, "inspect_assessment_file")


@pytest.mark.parametrize(
    "payload,code,location",
    [
        (b"", "INVALID_JSON", ()),
        (b"{}", "INVALID_JSON", ("format",)),
        (SPARSE + b"{}", "INVALID_JSON", None),
        (SPARSE + b"x", "INVALID_JSON", None),
        (b"\xef\xbb\xbf" + SPARSE, "INVALID_ENCODING", ()),
        (SPARSE.decode().encode("utf-16"), "INVALID_ENCODING", ()),
        (SPARSE.decode().encode("utf-32"), "INVALID_ENCODING", ()),
        (b"\xff", "INVALID_ENCODING", ()),
        (
            SPARSE.replace(b'"version":1', b'"version":true'),
            "INVALID_JSON",
            ("version",),
        ),
        (
            SPARSE.replace(b'"version":1', b'"version":"1"'),
            "INVALID_JSON",
            ("version",),
        ),
        (SPARSE.replace(b'"version":1', b'"version":1.0'), "INVALID_JSON", ()),
        (
            SPARSE.replace(b'"version":1', b'"version":2'),
            "UNSUPPORTED_VERSION",
            ("version",),
        ),
        (
            SPARSE.replace(b'"faultatlas-supplied-assessment"', b'"other"'),
            "UNSUPPORTED_FORMAT",
            ("format",),
        ),
        (
            SPARSE.replace(b'"version":1', b'"version":1,"extra":0'),
            "INVALID_JSON",
            ("extra",),
        ),
        (
            SPARSE.replace(b'"version":1', b'"version":1,"version":1'),
            "INVALID_JSON",
            ("version",),
        ),
        (
            SPARSE.replace(b'"key":"op-a"', b'"key":"op-a","\\u006bey":"op-a"'),
            "INVALID_JSON",
            ("key",),
        ),
        (
            SPARSE.replace(b'"Example author"', b'"\\ud800"'),
            "INVALID_JSON",
            ("assessment", "attribution", "supplier"),
        ),
    ],
)
def test_decoder_refusals_are_structured_and_do_not_publish(
    selected: tuple[Path, Path],
    payload: bytes,
    code: str,
    location: tuple[str | int, ...] | None,
) -> None:
    source, target = selected
    source.write_bytes(payload)
    error = _failure(lambda: save_assessment_as_new(str(source), str(target)), code)
    if location is not None:
        assert error.location == location
    assert not target.exists() and source.read_bytes() == payload


@pytest.mark.parametrize(
    "token",
    [
        b"1e0",
        b"NaN",
        b"Infinity",
        b"-Infinity",
        b"9223372036854775808",
        b"-9223372036854775809",
        b"100000000000000000000",
    ],
)
def test_numeric_gateway_rejects_unsupported_tokens_before_shape(
    selected: tuple[Path, Path], token: bytes
) -> None:
    source, _ = selected
    source.write_bytes(SPARSE.replace(b'"version":1', b'"version":' + token))
    error = _failure(lambda: inspect_assessment_file(str(source)), "INVALID_JSON")
    assert error.stage == "decode"


def test_owning_schema_failure_keeps_type_and_location(
    selected: tuple[Path, Path],
) -> None:
    source, _ = selected
    wire = sample_wire()
    wire["attribution"]["extra"] = "untrusted"
    source.write_bytes(_envelope(wire))
    error = _failure(lambda: inspect_assessment_file(str(source)), "INVALID_ASSESSMENT")
    assert error.location == ("assessment", "attribution", "extra")
    assert "type=extra_forbidden" in str(error)


def _count(value: Any) -> tuple[int, int, int, int]:
    nodes = objects = strings = depth = 0
    pending: list[tuple[Any, int]] = [(value, 0)]
    while pending:
        item, parent = pending.pop()
        nodes += 1
        if isinstance(item, str):
            strings += len(item)
        elif isinstance(item, (dict, list)):
            depth = max(depth, parent + 1)
            if isinstance(item, dict):
                objects += 1
                mapping = cast(dict[str, Any], item)
                pending.extend((key, parent + 1) for key in mapping)
                pending.extend((child, parent + 1) for child in mapping.values())
            else:
                pending.extend((child, parent + 1) for child in cast(list[Any], item))
    return nodes, objects, strings, depth


def test_corrected_normalized_boundary_really_saves_and_reopens(
    selected: tuple[Path, Path],
) -> None:
    source, target = selected
    wire = sample_wire()
    wire["opinions"] = []
    wire["basis"]["conditions"] = [
        {"key": f"c{i}", "statement": "x" * (3116 if i == 0 else 4096)}
        for i in range(32)
    ]
    envelope = {
        "format": "faultatlas-supplied-assessment",
        "version": 1,
        "assessment": wire,
    }
    body_count, envelope_count = _count(wire), _count(envelope)
    assert body_count[2] == 131072 and envelope_count[2] == 131125
    assert tuple(b - a for a, b in zip(body_count, envelope_count)) == (6, 1, 53, 1)
    source.write_bytes(json.dumps(envelope).encode())
    save_assessment_as_new(str(source), str(target))
    assert json.loads(target.read_bytes()) == envelope
    assert (
        inspect_assessment_file(str(source)).split("\n", 3)[3]
        == inspect_assessment_file(str(target)).split("\n", 3)[3]
    )
    wire["basis"]["conditions"][0]["statement"] += "x"
    wire["basis"].pop("material_omission")
    assert _count(envelope)[2] < 131125
    source.write_bytes(json.dumps(envelope).encode())
    error = _failure(lambda: inspect_assessment_file(str(source)), "RESOURCE_LIMIT")
    assert error.location == ("assessment",) and "owning schema error" in str(error)


@pytest.mark.parametrize("dimension", ["nodes", "objects", "strings", "depth"])
def test_private_envelope_budget_exact_and_one_over(dimension: str) -> None:
    operation: Callable[[], Any] = getattr(module, "_Operation")
    check: Callable[[Any, object], None] = getattr(module, "_envelope_budget")
    if dimension == "nodes":
        boundary, over = [None] * 8197, [None] * 8198
    elif dimension == "objects":
        repeated: dict[str, object] = {}
        boundary, over = [repeated] * 513, [repeated] * 514
    elif dimension == "strings":
        boundary, over = "x" * 131125, "x" * 131126
    else:
        boundary = None
        for _ in range(33):
            boundary = [boundary]
        over = [boundary]
    check(operation(), boundary)
    error = _failure(lambda: check(operation(), over), "RESOURCE_LIMIT")
    assert {
        "nodes": "node",
        "objects": "object",
        "strings": "string",
        "depth": "depth",
    }[dimension] in str(error)


@pytest.mark.parametrize("number", [-(1 << 63), (1 << 63) - 1])
def test_integer_endpoints_are_admitted_by_gateway_but_not_as_versions(
    selected: tuple[Path, Path], number: int
) -> None:
    source, _ = selected
    source.write_bytes(
        SPARSE.replace(b'"version":1', b'"version":' + str(number).encode())
    )
    _failure(lambda: inspect_assessment_file(str(source)), "UNSUPPORTED_VERSION")


@pytest.mark.parametrize(
    "bad", [1.5, float("nan"), (1 << 63), -(1 << 63) - 1, {1: "value"}]
)
def test_normalized_projection_uses_same_scalar_language(bad: object) -> None:
    operation: Callable[[], Any] = getattr(module, "_Operation")
    check: Callable[[Any, object], None] = getattr(module, "_envelope_budget")
    _failure(lambda: check(operation(), bad), "INVALID_JSON")


def test_byte_limit_and_string_aware_depth_precheck(
    selected: tuple[Path, Path],
) -> None:
    source, _ = selected
    source.write_bytes(SPARSE + b" " * (1048576 - len(SPARSE)))
    assert inspect_assessment_file(str(source)) == _expected_view(str(source))
    source.write_bytes(source.read_bytes() + b" ")
    _failure(lambda: inspect_assessment_file(str(source)), "RESOURCE_LIMIT")
    source.write_bytes(b"[" * 34 + b"0" + b"]" * 34)
    error = _failure(lambda: inspect_assessment_file(str(source)), "RESOURCE_LIMIT")
    assert "raw JSON container depth" in str(error)
    wire = sample_wire()
    wire["basis"]["context_statement"] = '{["\\' * 300
    source.write_bytes(_envelope(wire))
    assert "End of complete view" in inspect_assessment_file(str(source))


def test_bounded_read_uses_limit_plus_one_and_never_unlimited(
    selected: tuple[Path, Path],
) -> None:
    source, _ = selected
    reader = os.open(source, os.O_RDONLY)
    operation: Callable[[], Any] = getattr(module, "_Operation")
    bounded: Callable[[Any, int, int], bytes] = getattr(module, "_bounded_read")
    try:
        _failure(lambda: bounded(operation(), reader, 10), "RESOURCE_LIMIT")
        assert os.lseek(reader, 0, os.SEEK_CUR) == 11
    finally:
        os.close(reader)


def test_canonical_size_and_entire_reopened_view_checked_before_publication(
    selected: tuple[Path, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    source, target = selected
    compact = json.dumps(json.loads(SPARSE), separators=(",", ":")).encode()
    source.write_bytes(compact)
    assert len(compact) < len(CANONICAL)
    monkeypatch.setattr(module, "_MAX_BYTES", len(CANONICAL) - 1)
    error = _failure(
        lambda: save_assessment_as_new(str(source), str(target)), "RESOURCE_LIMIT"
    )
    assert "canonical file" in str(error) and not target.exists()
    monkeypatch.setattr(module, "_MAX_BYTES", 1048576)
    long_target = target.with_name("longer-selected-output-name.json")
    limit = len(_expected_view(str(source)).encode())
    monkeypatch.setattr(module, "_MAX_VIEW_BYTES", limit)
    assert inspect_assessment_file(str(source)) == _expected_view(str(source))
    _failure(
        lambda: save_assessment_as_new(str(source), str(long_target)), "RESOURCE_LIMIT"
    )
    assert not long_target.exists()
    monkeypatch.setattr(module, "_MAX_VIEW_BYTES", limit - 1)
    _failure(lambda: inspect_assessment_file(str(source)), "RESOURCE_LIMIT")


@pytest.mark.parametrize(
    "value",
    [
        None,
        1,
        Path("/tmp/input"),
        b"/tmp/input",
        "relative",
        "/",
        "/a//b",
        "/a/../b",
        "/a/./b",
        "/a/b/",
        "/a/\x00b",
        "/" + "x" * 4096,
        "/" + "x" * 256,
        "/" + "/".join(["x"] * 65),
        "/\ud800",
    ],
)
def test_invalid_path_arguments_fail_before_open(
    value: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    def forbidden(*args: Any, **kwargs: Any) -> Any:
        pytest.fail("invalid path opened a descriptor")

    monkeypatch.setattr(module, "_open", forbidden)
    code = "INVALID_PATH" if isinstance(value, str) else "INVALID_ARGUMENT"
    error = _failure(lambda: inspect_assessment_file(value), code)
    assert error.location == ("input_path",)
    if not isinstance(value, str) or len(value) > 4096 or "\ud800" in value:
        assert error.input_path is None


def test_equal_selections_and_wrong_callback_are_arguments(
    selected: tuple[Path, Path],
) -> None:
    source, target = selected
    _failure(lambda: save_assessment_as_new(str(source), str(source)), "INVALID_PATH")
    _failure(
        lambda: save_assessment_as_new(
            str(source), str(target), cancelled=cast(Any, 1)
        ),
        "INVALID_ARGUMENT",
    )
    assert source.read_bytes() == SPARSE and not target.exists()


def test_paths_and_diagnostics_are_recoverable_and_bounded(
    selected: tuple[Path, Path],
) -> None:
    source, target = selected
    escaped = source.with_name('选定"\x1b]8;;x\x07\u202e\x7f.json')
    source.rename(escaped)
    view = inspect_assessment_file(str(escaped))
    assert json.loads(view.splitlines()[0].split(": ", 1)[1]) == str(escaped)
    assert view.isascii() and "\x1b" not in view and "\x7f" not in view
    error = AssessmentFileError(
        "INVALID_JSON",
        "decode",
        input_path="/" + "😀" * 1000,
        output_path="/" + "😀" * 1000,
        location=tuple("😀" * 128 for _ in range(33)),
        detail="😀" * 1000,
    )
    assert len(str(error).encode()) <= 16384 and "abbreviated" in str(error)
    assert not target.exists()


@pytest.mark.parametrize(
    "kind", ["file_link", "ancestor_link", "directory", "fifo", "socket"]
)
def test_unsafe_file_kinds_are_refused_before_ordinary_input_open(
    selected: tuple[Path, Path], kind: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    source, _ = selected
    chosen = source.with_name("unsafe")
    sock = None
    if kind == "file_link":
        chosen.symlink_to(source)
    elif kind == "ancestor_link":
        chosen.symlink_to(source.parent, target_is_directory=True)
        chosen = chosen / source.name
    elif kind == "directory":
        chosen.mkdir()
    elif kind == "fifo":
        os.mkfifo(chosen)
    else:
        sock = socket.socket(socket.AF_UNIX)
        sock.bind(str(chosen))
    original: Any = getattr(module, "_open")

    def monitored(path: Any, flags: int, *args: Any, **kwargs: Any) -> int:
        if str(path).startswith("/proc/self/fd/"):
            pytest.fail("unsafe input reached ordinary descriptor reopening")
        return original(path, flags, *args, **kwargs)

    monkeypatch.setattr(module, "_open", monitored)
    try:
        _failure(lambda: inspect_assessment_file(str(chosen)), "UNSAFE_INPUT")
    finally:
        if sock is not None:
            sock.close()


@pytest.mark.parametrize("kind", ["file", "directory", "hardlink", "dangling_symlink"])
def test_existing_destination_is_untouched(
    selected: tuple[Path, Path], kind: str
) -> None:
    source, target = selected
    os.utime(source, ns=(1, source.stat().st_mtime_ns))
    if kind == "file":
        target.write_bytes(b"keep")
    elif kind == "directory":
        target.mkdir()
    elif kind == "hardlink":
        os.link(source, target)
    else:
        target.symlink_to("absent")
    before = target.lstat()
    error = _failure(
        lambda: save_assessment_as_new(str(source), str(target)), "DESTINATION_EXISTS"
    )
    assert error.stage == "publish"
    after = target.lstat()
    # A collision may hardlink the input; reading it can legitimately update atime.
    stable_fields = (
        "st_dev",
        "st_ino",
        "st_mode",
        "st_nlink",
        "st_uid",
        "st_gid",
        "st_size",
        "st_mtime_ns",
        "st_ctime_ns",
    )
    assert tuple(getattr(after, name) for name in stable_fields) == tuple(
        getattr(before, name) for name in stable_fields
    )
    assert source.read_bytes() == SPARSE
    if kind in {"file", "hardlink"}:
        assert target.read_bytes() == (SPARSE if kind == "hardlink" else b"keep")


def _at(
    monkeypatch: pytest.MonkeyPatch, point: str, action: Callable[[Any], object]
) -> None:
    original: Callable[[Any, str], None] = getattr(module, "_checkpoint")
    acted = False

    def checkpoint(operation: Any, current: str) -> None:
        nonlocal acted
        if current == point and not acted:
            acted = True
            action(operation)
        original(operation, current)

    monkeypatch.setattr(module, "_checkpoint", checkpoint)


@pytest.mark.parametrize(
    "change",
    [
        "input_content",
        "input_inode",
        "input_parent",
        "output_parent",
        "post_parent",
        "post_name",
    ],
)
def test_actual_controlled_binding_changes(
    selected: tuple[Path, Path], change: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    original, _ = selected
    inputs = original.parent / "inputs"
    outputs = original.parent / "outputs"
    inputs.mkdir()
    outputs.mkdir()
    source, target = inputs / "source.json", outputs / "saved.json"
    source.write_bytes(SPARSE)
    moved = original.parent / "moved"

    def change_binding(operation: Any) -> None:
        if change == "input_content":
            source.write_bytes(SPARSE + b" ")
        elif change == "input_inode":
            source.rename(moved)
            source.write_bytes(SPARSE)
        elif change == "input_parent":
            inputs.rename(moved)
            inputs.mkdir()
            source.write_bytes(SPARSE)
        elif change in {"output_parent", "post_parent"}:
            outputs.rename(moved)
            outputs.mkdir()
        else:
            target.rename(moved)
            target.write_bytes(b"other inode")

    published = change.startswith("post_")
    _at(monkeypatch, "after_link" if published else "before_link", change_binding)
    code = (
        "PUBLISHED_PATH_CHANGED"
        if published
        else ("OUTPUT_PARENT_CHANGED" if change == "output_parent" else "INPUT_CHANGED")
    )
    error = _failure(
        lambda: save_assessment_as_new(str(source), str(target)),
        code,
        visibility="published" if published else "not_published",
        synced=published,
    )
    assert error.stage == (
        "publish" if published else ("path" if change == "output_parent" else "read")
    )
    if published:
        retained = moved / "saved.json" if change == "post_parent" else moved
        assert retained.read_bytes() == CANONICAL
    else:
        assert not target.exists()


def test_inspection_rechecks_input_at_completion(
    selected: tuple[Path, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    source, _ = selected
    _at(monkeypatch, "completion", lambda operation: source.write_bytes(SPARSE + b" "))
    _failure(lambda: inspect_assessment_file(str(source)), "INPUT_CHANGED")


@pytest.mark.parametrize(
    "point", ["start", "prepare", "before_link", "after_link", "completion"]
)
def test_cancellation_keeps_actual_visibility_and_sync(
    selected: tuple[Path, Path], point: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    source, target = selected
    flag = [False]
    _at(monkeypatch, point, lambda operation: flag.__setitem__(0, True))
    published = point in {"after_link", "completion"}
    _failure(
        lambda: save_assessment_as_new(
            str(source), str(target), cancelled=lambda: flag[0]
        ),
        "CANCELLED",
        visibility="published" if published else "not_published",
        synced=published,
        cancelled=True,
    )
    assert target.exists() is published
    if published:
        assert target.read_bytes() == CANONICAL


@pytest.mark.parametrize("bad", [None, 0, 1, "false"])
def test_non_bool_callback_results_fail(selected: tuple[Path, Path], bad: Any) -> None:
    source, target = selected
    _failure(
        lambda: save_assessment_as_new(str(source), str(target), cancelled=lambda: bad),
        "CANCEL_CHECK_FAILED",
    )
    assert not target.exists()


def test_postlink_callback_exception_still_syncs_and_preserves_file(
    selected: tuple[Path, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    source, target = selected
    flag = [False]
    _at(monkeypatch, "after_link", lambda operation: flag.__setitem__(0, True))

    def callback() -> bool:
        if flag[0]:
            raise ValueError("untrusted \x1b callback payload")
        return False

    error = _failure(
        lambda: save_assessment_as_new(str(source), str(target), cancelled=callback),
        "CANCEL_CHECK_FAILED",
        visibility="published",
        synced=True,
    )
    assert "untrusted" not in str(error) and target.read_bytes() == CANONICAL


@pytest.mark.parametrize("kind", ["partial", "zero", "error"])
def test_write_progress_and_no_partial_name(
    selected: tuple[Path, Path], kind: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    source, target = selected
    original: Any = getattr(module, "_write")

    def writing(descriptor: int, data: bytes) -> int:
        assert not target.exists()
        if kind == "zero":
            return 0
        if kind == "error":
            raise OSError(errno.ENOSPC, "injected")
        return original(descriptor, data[:7])

    monkeypatch.setattr(module, "_write", writing)
    if kind == "partial":
        save_assessment_as_new(str(source), str(target))
        assert target.read_bytes() == CANONICAL
    else:
        _failure(lambda: save_assessment_as_new(str(source), str(target)), "IO_ERROR")
        assert not target.exists()


@pytest.mark.parametrize("nth", [1, 2, 3])
def test_sync_failures_preserve_effects_and_cancellation(
    selected: tuple[Path, Path], nth: int, monkeypatch: pytest.MonkeyPatch
) -> None:
    source, target = selected
    original: Any = getattr(module, "_fsync")
    calls = 0
    flag = [False]

    def syncing(descriptor: int) -> None:
        nonlocal calls
        calls += 1
        if calls == nth:
            flag[0] = True
            raise OSError(errno.EIO, "injected sync failure")
        original(descriptor)

    monkeypatch.setattr(module, "_fsync", syncing)
    published = nth > 1
    _failure(
        lambda: save_assessment_as_new(
            str(source), str(target), cancelled=lambda: flag[0]
        ),
        "PUBLISHED_SYNC_UNCONFIRMED" if published else "IO_ERROR",
        visibility="published" if published else "not_published",
        cancelled=True,
    )
    assert target.exists() is published
    assert calls == (3 if published else 1)
    if published:
        assert target.read_bytes() == CANONICAL


@pytest.mark.parametrize("linked", [False, True])
def test_ambiguous_link_has_one_attempt_and_bounded_effect_observation(
    selected: tuple[Path, Path], linked: bool, monkeypatch: pytest.MonkeyPatch
) -> None:
    source, target = selected
    original: Any = getattr(module, "_link")
    calls = 0

    def linking(*args: Any, **kwargs: Any) -> None:
        nonlocal calls
        calls += 1
        if linked:
            original(*args, **kwargs)
        raise OSError(errno.EIO, "ambiguous link")

    monkeypatch.setattr(module, "_link", linking)
    _failure(
        lambda: save_assessment_as_new(str(source), str(target)),
        "IO_ERROR" if linked else "PUBLICATION_UNCERTAIN",
        visibility="published" if linked else "uncertain",
        synced=linked,
    )
    assert calls == 1 and target.exists() is linked
    if linked:
        assert target.read_bytes() == CANONICAL


def test_two_real_publishers_have_at_most_one_complete_winner(
    selected: tuple[Path, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    source, target = selected
    barrier = Barrier(2)
    original: Any = getattr(module, "_link")

    def linking(*args: Any, **kwargs: Any) -> None:
        assert kwargs["follow_symlinks"] is True and isinstance(
            kwargs["dst_dir_fd"], int
        )
        barrier.wait(timeout=5)
        original(*args, **kwargs)
        assert target.read_bytes() == CANONICAL

    monkeypatch.setattr(module, "_link", linking)

    def save() -> str:
        try:
            return save_assessment_as_new(str(source), str(target))
        except AssessmentFileError as error:
            assert (
                error.code == "DESTINATION_EXISTS"
                and error.output_visibility == "not_published"
            )
            return error.code

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(save) for _ in range(2)]
        results = [future.result(timeout=10) for future in futures]
    assert sorted(results) == sorted([str(target), "DESTINATION_EXISTS"])
    assert target.read_bytes() == CANONICAL


@pytest.mark.parametrize("which", ["input_parent", "output_parent", "output_ancestor"])
def test_unsafe_parents_are_not_chmodded_or_followed(
    selected: tuple[Path, Path], which: str
) -> None:
    source, target = selected
    directory = source.parent / "parent"
    directory.mkdir(mode=0o700)
    if which == "input_parent":
        child = directory / "source.json"
        child.write_bytes(SPARSE)
        source = child
        directory.chmod(0o777)
    elif which == "output_parent":
        target = directory / "saved.json"
        directory.chmod(0o777)
    else:
        alias = source.parent / "alias"
        alias.symlink_to(directory, target_is_directory=True)
        target = alias / "saved.json"
    before = stat.S_IMODE(directory.stat().st_mode)
    _failure(lambda: save_assessment_as_new(str(source), str(target)), "UNSAFE_INPUT")
    assert stat.S_IMODE(directory.stat().st_mode) == before and not target.exists()


@pytest.mark.parametrize("which", ["foreign_uid", "device"])
def test_foreign_input_and_device_never_reach_read_open(
    selected: tuple[Path, Path], which: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    source, _ = selected
    original_open: Any = getattr(module, "_open")
    original_stat = os.fstat
    pin: list[int] = []

    def opening(path: Any, flags: int, *args: Any, **kwargs: Any) -> int:
        if pin and str(path) == f"/proc/self/fd/{pin[0]}":
            pytest.fail("refused input reached ordinary reading")
        fd = original_open(path, flags, *args, **kwargs)
        if path == source.name.encode("utf-8") and flags & os.O_PATH:
            pin.append(fd)
        return fd

    def status(fd: int) -> os.stat_result:
        original = original_stat(fd)
        if fd in pin:
            parts = list(original)
            parts[4 if which == "foreign_uid" else 0] = (
                os.geteuid() + 1 if which == "foreign_uid" else stat.S_IFCHR | 0o600
            )
            return os.stat_result(parts)
        return original

    monkeypatch.setattr(module, "_open", opening)
    monkeypatch.setattr(os, "fstat", status)
    _failure(lambda: inspect_assessment_file(str(source)), "UNSAFE_INPUT")


@pytest.mark.parametrize(
    "failure_kind",
    [
        "success",
        "read",
        "unexpected",
        "early_close",
        "late_close",
        "cancel_close",
        "sync_close",
    ],
)
def test_descriptor_ownership_cleanup_and_primary_error(
    selected: tuple[Path, Path], failure_kind: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    source, target = selected
    original_open: Any = getattr(module, "_open")
    original_close: Any = getattr(module, "_close")
    original_read: Any = getattr(module, "_read")
    original_sync: Any = getattr(module, "_fsync")
    live: dict[int, str] = {}
    temporary: list[int] = []
    intruders: list[int] = []
    opened = closed = syncs = 0
    close_failed = False
    cancel_flag = [False]

    def opening(path: Any, flags: int, *args: Any, **kwargs: Any) -> int:
        nonlocal opened
        fd = original_open(path, flags, *args, **kwargs)
        assert fd not in live
        live[fd] = str(path)
        opened += 1
        if flags & os.O_TMPFILE == os.O_TMPFILE:
            temporary.append(fd)
        return fd

    def closing(fd: int) -> None:
        nonlocal closed, close_failed
        assert fd in live, "unknown or repeated descriptor close"
        del live[fd]
        closed += 1
        original_close(fd)
        failing = failure_kind == "early_close" or (
            failure_kind in {"late_close", "cancel_close", "sync_close"}
            and fd in temporary
        )
        if failing and not close_failed:
            close_failed = True
            # Deliberately reuse the number after Linux close has ended ownership.
            other = os.open(source, os.O_RDONLY)
            assert other == fd
            intruders.append(other)
            raise OSError(errno.EIO, "close reported an error after releasing fd")

    def reading(fd: int, amount: int) -> bytes:
        if live[fd].startswith("/proc/self/fd/"):
            if failure_kind == "read":
                raise OSError(errno.EIO, "read failure")
            if failure_kind == "unexpected":
                raise RuntimeError("unexpected programming failure")
        return original_read(fd, amount)

    def syncing(fd: int) -> None:
        nonlocal syncs
        syncs += 1
        if failure_kind == "sync_close" and syncs == 2:
            raise OSError(errno.EIO, "post-link file sync failure")
        original_sync(fd)

    monkeypatch.setattr(module, "_open", opening)
    monkeypatch.setattr(module, "_close", closing)
    monkeypatch.setattr(module, "_read", reading)
    monkeypatch.setattr(module, "_fsync", syncing)
    if failure_kind == "cancel_close":
        _at(
            monkeypatch,
            "before_link",
            lambda operation: cancel_flag.__setitem__(0, True),
        )
    try:

        def call() -> str:
            return save_assessment_as_new(
                str(source), str(target), cancelled=lambda: cancel_flag[0]
            )

        if failure_kind == "success":
            assert call() == str(target)
        elif failure_kind == "unexpected":
            with pytest.raises(RuntimeError, match="unexpected programming failure"):
                call()
        else:
            code = (
                "IO_ERROR"
                if failure_kind == "read"
                else (
                    "PUBLISHED_SYNC_UNCONFIRMED"
                    if failure_kind == "sync_close"
                    else "CLOSE_FAILED"
                )
            )
            published = failure_kind in {"late_close", "sync_close"}
            _failure(
                call,
                code,
                visibility="published" if published else "not_published",
                synced=failure_kind == "late_close",
                cancelled=failure_kind == "cancel_close",
            )
        assert not live and opened == closed
        for descriptor in intruders:
            assert os.fstat(descriptor).st_ino == source.stat().st_ino
    finally:
        for descriptor in intruders:
            os.close(descriptor)


@pytest.mark.parametrize(
    "info,mounts",
    [
        (b"", b""),
        (b"mnt_id: 7\nmnt_id: 7\n", b"7 1 0:1 / / rw - ext4 /dev/test rw\n"),
        (b"mnt_id: 0\n", b"0 1 0:1 / / rw - ext4 /dev/test rw\n"),
        (b"mnt_id: 7\n", b"8 1 0:1 / / rw - ext4 /dev/test rw\n"),
        (b"mnt_id: 7\n", b"7 1 0:1 / / rw - ext4 /dev/test rw\n" * 2),
        (b"mnt_id: 7\n", b"7 malformed - ext4\n"),
        (b"x" * 65537, b""),
        (b"mnt_id: 7\n", b"x" * 1048577),
    ],
)
def test_proc_metadata_failures_are_not_inferred_as_ext4(
    info: bytes, mounts: bytes
) -> None:
    mount_type: Callable[[bytes, bytes], str] = getattr(module, "_mount_type")
    with pytest.raises(ValueError, match="mount|bound"):
        mount_type(info, mounts)


def test_mount_id_association_and_non_ext4_refusal(
    selected: tuple[Path, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    source, target = selected
    mount_type: Callable[[bytes, bytes], str] = getattr(module, "_mount_type")
    raw = b"7 1 0:1 / / rw - tmpfs tmpfs rw\n8 1 0:2 / /other rw - ext4 /dev/test rw\n"
    assert mount_type(b"mnt_id:\t7\n", raw) == "tmpfs"
    assert mount_type(b"mnt_id:\t8\n", raw) == "ext4"

    def other_mount(info: bytes, mounts: bytes) -> str:
        return "tmpfs"

    monkeypatch.setattr(module, "_mount_type", other_mount)
    _failure(
        lambda: save_assessment_as_new(str(source), str(target)), "UNSUPPORTED_PLATFORM"
    )
    assert not target.exists()


@pytest.mark.parametrize("kind", ["platform", "dir_fd", "tmpfile"])
def test_unavailable_capabilities_fail_without_fallback(
    selected: tuple[Path, Path], kind: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    source, target = selected
    if kind == "platform":
        monkeypatch.setattr(sys, "platform", "unsupported")
    elif kind == "dir_fd":
        monkeypatch.setattr(os, "supports_dir_fd", set[Callable[..., Any]]())
    else:
        original: Any = getattr(module, "_open")

        def opening(path: Any, flags: int, *args: Any, **kwargs: Any) -> int:
            if flags & os.O_TMPFILE == os.O_TMPFILE:
                raise OSError(errno.EOPNOTSUPP, "unsupported unnamed creation")
            return original(path, flags, *args, **kwargs)

        monkeypatch.setattr(module, "_open", opening)
    _failure(
        lambda: save_assessment_as_new(str(source), str(target)), "UNSUPPORTED_PLATFORM"
    )
    assert not target.exists()


def test_locators_never_become_io_or_execution(
    selected: tuple[Path, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    source, target = selected
    wire = rich_wire()
    wire["basis"]["materials"][0]["locator"] = "/do-not-read/$(run-untrusted)"
    source.write_bytes(_envelope(wire))
    original: Any = getattr(module, "_open")

    def opening(path: Any, *args: Any, **kwargs: Any) -> int:
        assert "do-not-read" not in str(path)
        return original(path, *args, **kwargs)

    def forbidden(*args: Any, **kwargs: Any) -> Any:
        pytest.fail("file content attempted network/process execution")

    monkeypatch.setattr(module, "_open", opening)
    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(subprocess, "run", forbidden)
    save_assessment_as_new(str(source), str(target))
    assert json.loads(target.read_bytes())["assessment"] == wire


def test_import_performs_no_filesystem_or_environment_probe(
    selected: tuple[Path, Path],
) -> None:
    source, _ = selected
    probe = """
import os,builtins,dataclasses,json,stat,errno
import faultatlas.assessment
import faultatlas.domain.assessment
def forbidden(*args,**kwargs):raise AssertionError("import-time probe")
os.open=os.stat=os.fstat=os.geteuid=forbidden
builtins.open=forbidden
import faultatlas.assessment_file
assert faultatlas.assessment_file.__all__==["AssessmentFileError","inspect_assessment_file","save_assessment_as_new"]
print("import without operation probe PASS")
"""
    result = subprocess.run(
        [sys.executable, "-I", "-c", probe],
        cwd=source.parent,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "import without operation probe PASS"


def test_identity_spelling_is_normalized_by_the_existing_owner(
    selected: tuple[Path, Path],
) -> None:
    source, target = selected
    wire = sample_wire()
    wire["basis"]["source"]["pattern"] = "AAAAAAAA-0000-4000-8000-000000000001"
    source.write_bytes(_envelope(wire))
    save_assessment_as_new(str(source), str(target))
    wire["basis"]["source"]["pattern"] = "aaaaaaaa-0000-4000-8000-000000000001"
    assert json.loads(target.read_bytes())["assessment"] == wire
    assert "End of complete view" in inspect_assessment_file(str(target))


def test_input_change_during_bounded_read_is_detected_before_decode(
    selected: tuple[Path, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    source, target = selected
    original: Any = getattr(module, "_read")
    before = source.stat()
    changed = False

    def reading(fd: int, amount: int) -> bytes:
        nonlocal changed
        data = original(fd, amount)
        current = os.fstat(fd)
        if (
            data
            and not changed
            and (current.st_dev, current.st_ino) == (before.st_dev, before.st_ino)
        ):
            source.write_bytes(SPARSE + b" ")
            changed = True
        return data

    monkeypatch.setattr(module, "_read", reading)
    error = _failure(
        lambda: save_assessment_as_new(str(source), str(target)), "INPUT_CHANGED"
    )
    assert changed and error.stage == "read" and not target.exists()


def test_recovered_link_then_sync_failure_retains_both_facts(
    selected: tuple[Path, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    source, target = selected
    original_link: Any = getattr(module, "_link")
    original_sync: Any = getattr(module, "_fsync")
    syncs = 0

    def linking(*args: Any, **kwargs: Any) -> None:
        original_link(*args, **kwargs)
        raise OSError(errno.EIO, "link acknowledgment lost")

    def syncing(fd: int) -> None:
        nonlocal syncs
        syncs += 1
        if syncs == 2:
            raise OSError(errno.EIO, "post-link sync failed")
        original_sync(fd)

    monkeypatch.setattr(module, "_link", linking)
    monkeypatch.setattr(module, "_fsync", syncing)
    error = _failure(
        lambda: save_assessment_as_new(str(source), str(target)),
        "PUBLISHED_SYNC_UNCONFIRMED",
        visibility="published",
    )
    assert "link outcome errno=5" in error.__notes__[0]
    assert target.read_bytes() == CANONICAL and syncs == 3


def test_real_installed_wheel_file_vertical_and_provenance(
    offline_distributions: tuple[Path, Path], selected: tuple[Path, Path]
) -> None:
    source, target = selected
    installed = source.parent / "installed"
    environment = os.environ | {
        "UV_OFFLINE": "1",
        "UV_CACHE_DIR": str(source.parent / "cache"),
    }
    result = subprocess.run(
        [
            "uv",
            "pip",
            "install",
            "--offline",
            "--no-deps",
            "--target",
            str(installed),
            str(offline_distributions[0]),
        ],
        cwd=source.parent,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    probe = """
import pathlib,sys,stat
installed=pathlib.Path(sys.argv[1]).resolve()
source,target=pathlib.Path(sys.argv[2]),pathlib.Path(sys.argv[3])
sys.path.insert(0,str(installed))
from faultatlas.assessment_file import inspect_assessment_file,save_assessment_as_new
before=source.read_bytes(),stat.S_IMODE(source.stat().st_mode)
original=inspect_assessment_file(str(source))
assert original==sys.argv[5]
assert save_assessment_as_new(str(source),str(target))==str(target)
assert target.read_bytes()==sys.argv[4].encode()
assert stat.S_IMODE(target.stat().st_mode)==0o600
assert inspect_assessment_file(str(target)).split("\\n",3)[3]==original.split("\\n",3)[3]
third=target.with_name("installed-resaved.json")
assert save_assessment_as_new(str(target),str(third))==str(third)
assert third.read_bytes()==target.read_bytes()
assert (source.read_bytes(),stat.S_IMODE(source.stat().st_mode))==before
for name,value in tuple(sys.modules.items()):
    if name=="faultatlas" or name.startswith("faultatlas."):
        assert pathlib.Path(value.__file__).resolve().is_relative_to(installed),name
print("installed ext4 inspect/save/reopen/provenance PASS")
"""
    result = subprocess.run(
        [
            sys.executable,
            "-I",
            "-c",
            probe,
            str(installed),
            str(source),
            str(target),
            CANONICAL.decode(),
            _expected_view(str(source)),
        ],
        cwd=source.parent,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.strip() == "installed ext4 inspect/save/reopen/provenance PASS"


def test_unicode_selected_paths_do_not_depend_on_filesystem_encoding(
    selected: tuple[Path, Path],
) -> None:
    source, _ = selected
    probe = r"""
import json,os,sys
assert sys.getfilesystemencoding()=="ascii",sys.getfilesystemencoding()
from faultatlas.assessment_file import inspect_assessment_file,save_assessment_as_new
parent=sys.argv[1]+"/\u00e9-parent"
os.mkdir(parent.encode("utf-8"),0o700)
source=parent+"/\u00e9-input.json"
target=parent+"/\u03b1-output.json"
fd=os.open(source.encode("utf-8"),os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
try:assert os.write(fd,bytes.fromhex(sys.argv[2]))==len(bytes.fromhex(sys.argv[2]))
finally:os.close(fd)
before=inspect_assessment_file(source)
assert json.loads(before.splitlines()[0].split(": ",1)[1])==source
assert save_assessment_as_new(source,target)==target
after=inspect_assessment_file(target)
assert before.split("\n",3)[3]==after.split("\n",3)[3]
fd=os.open(target.encode("utf-8"),os.O_RDONLY)
try:assert os.read(fd,1048577)==bytes.fromhex(sys.argv[3])
finally:os.close(fd)
print("ASCII filesystem encoding with UTF-8 selected paths PASS")
"""
    environment = os.environ | {
        "LC_ALL": "C",
        "LANG": "C",
        "PYTHONCOERCECLOCALE": "0",
        "PYTHONUTF8": "0",
    }
    result = subprocess.run(
        [
            sys.executable,
            "-X",
            "utf8=0",
            "-c",
            probe,
            str(source.parent),
            SPARSE.hex(),
            CANONICAL.hex(),
        ],
        cwd=source.parent,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert (
        result.stdout.strip()
        == "ASCII filesystem encoding with UTF-8 selected paths PASS"
    )
