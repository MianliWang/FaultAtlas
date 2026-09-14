"""Bounded selected-file assessment workflow on observed local Linux ext4.

The input is data. It grants no locator, network, executable or lookup authority.
Name visibility, OS synchronization acknowledgments and cancellation are separate
facts. Stable caller-controlled paths/mounts are required; this is not a hostile
same-UID sandbox or a power-loss qualification. Importing performs no I/O.
"""

from __future__ import annotations

import errno
import json
import os
import stat
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, cast

from pydantic import ValidationError

from faultatlas.assessment import inspect_assessment
from faultatlas.domain.assessment import SuppliedAssessment

__all__ = ["AssessmentFileError", "inspect_assessment_file", "save_assessment_as_new"]

_MAX_BYTES = 1_048_576
_MAX_VIEW_BYTES = 8 * 1024 * 1024
_FORMAT = "faultatlas-supplied-assessment"
_BLOCK = 65536
_open, _read, _write = os.open, os.read, os.write
_close, _fsync, _link = os.close, os.fsync, os.link


def _quote(value: str) -> str:
    return json.dumps(value, ensure_ascii=True).replace("\x7f", "\\u007f")


def _excerpt(value: str, limit: int = 256) -> str:
    return _quote(value[:limit]) + (" (abbreviated)" if len(value) > limit else "")


class AssessmentFileError(Exception):
    """Anticipated workflow failure with effects that do not depend on prose."""

    def __init__(
        self,
        code: str,
        stage: str,
        *,
        input_path: str | None = None,
        output_path: str | None = None,
        location: tuple[str | int, ...] = (),
        output_visibility: str = "not_published",
        sync_completed: bool = False,
        cancel_requested: bool = False,
        detail: str = "",
    ) -> None:
        super().__init__(code)
        self.code = code
        self.stage = stage
        self.input_path = input_path
        self.output_path = output_path
        self.location = tuple(
            part[:128] if isinstance(part, str) else part for part in location[:33]
        )
        self.output_visibility = output_visibility
        self.sync_completed = sync_completed
        self.cancel_requested = cancel_requested
        self._detail = detail

    def __str__(self) -> str:
        # Each of the bounded fields is escaped separately; never slice an escape.
        places = ", ".join(
            _excerpt(part, 8) if isinstance(part, str) else str(part)
            for part in self.location
        )
        return (
            f"{_excerpt(self.code, 64)} at {_excerpt(self.stage, 64)}: "
            f"{_excerpt(self._detail)}; location=({places}); "
            f"input={_excerpt(self.input_path) if self.input_path is not None else 'null'}; "
            f"output={_excerpt(self.output_path) if self.output_path is not None else 'null'}; "
            f"visibility={_excerpt(self.output_visibility, 32)}; "
            f"sync_completed={self.sync_completed}; cancel_requested={self.cancel_requested}"
        )


@dataclass
class _Operation:
    input_path: str | None = None
    output_path: str | None = None
    cancelled: Callable[[], bool] | None = None
    stage: str = "path"
    visibility: str = "not_published"
    sync_completed: bool = False
    cancel_requested: bool = False
    attempted: bool = False
    completion_sampled: bool = False
    deferred: AssessmentFileError | None = None
    descriptors: list[int] = field(default_factory=list[int])

    def error(
        self,
        code: str,
        detail: str = "",
        location: tuple[str | int, ...] = (),
        *,
        stage: str | None = None,
    ) -> AssessmentFileError:
        return AssessmentFileError(
            code,
            self.stage if stage is None else stage,
            input_path=self.input_path,
            output_path=self.output_path,
            location=location,
            output_visibility=self.visibility,
            sync_completed=self.sync_completed,
            cancel_requested=self.cancel_requested,
            detail=detail,
        )

    def own(self, descriptor: int) -> int:
        self.descriptors.append(descriptor)
        return descriptor

    def close(self, descriptor: int) -> None:
        # Relinquish before close; Linux may already have reused a failed-close fd.
        self.descriptors.remove(descriptor)
        try:
            _close(descriptor)
        except OSError as error:
            raise self.error(
                "CLOSE_FAILED", f"close errno={error.errno}", stage="close"
            ) from None

    def close_all(self) -> AssessmentFileError | None:
        first = None
        while self.descriptors:
            try:
                self.close(self.descriptors[-1])
            except AssessmentFileError as error:
                if first is None:
                    first = error
        return first


def _checkpoint(operation: _Operation, point: str) -> None:
    if point == "completion":
        operation.completion_sampled = True
    if operation.cancelled is None:
        return
    failure = None
    try:
        requested = operation.cancelled()
        if type(requested) is not bool:
            failure = operation.error(
                "CANCEL_CHECK_FAILED",
                "callback must return an exact bool",
                stage="cancel",
            )
        elif requested:
            operation.cancel_requested = True
            failure = operation.error(
                "CANCELLED", "cancellation requested", stage="cancel"
            )
    except Exception as error:
        failure = operation.error(
            "CANCEL_CHECK_FAILED",
            f"callback raised {type(error).__name__}",
            stage="cancel",
        )
    if failure is not None:
        if not operation.attempted:
            raise failure
        if operation.deferred is None or operation.deferred.code == "CANCELLED":
            operation.deferred = failure


def _parts(operation: _Operation, value: object, argument: str) -> tuple[bytes, ...]:
    location = (argument,)
    if not isinstance(value, str):
        raise operation.error("INVALID_ARGUMENT", "path must be a string", location)
    try:
        encoded = value.encode("utf-8")
    except UnicodeEncodeError:
        raise operation.error(
            "INVALID_PATH", "path is not strict UTF-8", location
        ) from None
    if len(encoded) > 4096:
        raise operation.error("INVALID_PATH", "path exceeds 4096 bytes", location)
    setattr(operation, argument, value)
    parts = tuple(encoded.split(b"/")[1:])
    if (
        not encoded.startswith(b"/")
        or b"\x00" in encoded
        or not parts
        or len(parts) > 64
        or any(part in {b"", b".", b".."} or len(part) > 255 for part in parts)
    ):
        raise operation.error("INVALID_PATH", "invalid absolute Linux path", location)
    return parts


def _platform(operation: _Operation) -> None:
    operation.stage = "platform"
    if (
        sys.platform != "linux"
        or any(
            not hasattr(os, name)
            for name in (
                "O_PATH",
                "O_NOFOLLOW",
                "O_DIRECTORY",
                "O_CLOEXEC",
                "O_TMPFILE",
                "geteuid",
            )
        )
        or os.open not in os.supports_dir_fd
        or os.link not in os.supports_dir_fd
        or os.link not in os.supports_follow_symlinks
    ):
        raise operation.error(
            "UNSUPPORTED_PLATFORM", "required Linux descriptor capabilities unavailable"
        )


def _identity(info: os.stat_result) -> tuple[int, int]:
    return info.st_dev, info.st_ino


def _stamp(info: os.stat_result) -> tuple[int, int, int, int, int]:
    return info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns


def _walk_parent(operation: _Operation, parts: tuple[bytes, ...]) -> int:
    flags = os.O_PATH | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
    descriptor = operation.own(_open("/", flags))
    for component in parts[:-1]:
        try:
            child = operation.own(_open(component, flags, dir_fd=descriptor))
        except OSError as error:
            if error.errno in {errno.ELOOP, errno.ENOTDIR}:
                raise operation.error(
                    "UNSAFE_INPUT", "ancestor is not a no-follow directory"
                ) from None
            raise
        if not stat.S_ISDIR(os.fstat(child).st_mode):
            raise operation.error("UNSAFE_INPUT", "ancestor is not a directory")
        operation.close(descriptor)
        descriptor = child
    info = os.fstat(descriptor)
    if (
        not stat.S_ISDIR(info.st_mode)
        or info.st_uid != os.geteuid()
        or info.st_mode & 0o022
    ):
        raise operation.error(
            "UNSAFE_INPUT", "parent must be caller-owned and not group/other writable"
        )
    return descriptor


def _bounded_read(operation: _Operation, descriptor: int, maximum: int) -> bytes:
    chunks: list[bytes] = []
    total = 0
    while total <= maximum:
        _checkpoint(operation, "read")
        chunk = _read(descriptor, min(_BLOCK, maximum + 1 - total))
        if not chunk:
            break
        chunks.append(chunk)
        total += len(chunk)
    if total > maximum:
        raise operation.error("RESOURCE_LIMIT", "bounded byte read exceeded")
    return b"".join(chunks)


def _metadata(operation: _Operation, path: str, maximum: int) -> bytes:
    try:
        descriptor = operation.own(
            _open(path, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW)
        )
    except OSError as error:
        if error.errno in {errno.ENOENT, errno.ENOTDIR, errno.ENOSYS}:
            raise operation.error(
                "UNSUPPORTED_PLATFORM", "fixed proc metadata unavailable"
            ) from None
        raise
    try:
        raw = _bounded_read(operation, descriptor, maximum)
    except AssessmentFileError as error:
        if error.code == "RESOURCE_LIMIT":
            raise operation.error(
                "UNSUPPORTED_PLATFORM", "fixed proc metadata exceeds bound"
            ) from None
        raise
    operation.close(descriptor)
    return raw


def _mount_type(fdinfo: bytes, mountinfo: bytes) -> str:
    if len(fdinfo) > 65536 or len(mountinfo) > 1048576:
        raise ValueError("proc metadata exceeds bound")
    identifiers = [
        line.split(b":", 1)[1].strip()
        for line in fdinfo.splitlines()
        if line.startswith(b"mnt_id:")
    ]
    if (
        len(identifiers) != 1
        or not identifiers[0].isdigit()
        or len(identifiers[0]) > 20
        or identifiers[0].startswith(b"0")
    ):
        raise ValueError("missing or ambiguous descriptor mount ID")
    rows = [
        line.split()
        for line in mountinfo.splitlines()
        if line.split() and line.split()[0] == identifiers[0]
    ]
    if len(rows) != 1:
        raise ValueError("missing or ambiguous mount association")
    row = rows[0]
    if row.count(b"-") != 1:
        raise ValueError("malformed mount association")
    separator = row.index(b"-")
    if separator < 6 or len(row) != separator + 4 or not row[1].isdigit():
        raise ValueError("malformed mount association")
    return row[separator + 1].decode("ascii")


def _ext4(operation: _Operation, descriptor: int) -> None:
    operation.stage = "platform"
    info = _metadata(operation, f"/proc/self/fdinfo/{descriptor}", 65536)
    mounts = _metadata(operation, "/proc/self/mountinfo", 1048576)
    try:
        filesystem = _mount_type(info, mounts)
    except (ValueError, UnicodeError):
        raise operation.error(
            "UNSUPPORTED_PLATFORM", "invalid descriptor mount metadata"
        ) from None
    if filesystem != "ext4":
        raise operation.error(
            "UNSUPPORTED_PLATFORM", "selected descriptor is not on observed ext4"
        )


def _depth(operation: _Operation, text: str) -> None:
    depth = 0
    quoted = escaped = False
    for character in text:
        if quoted:
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == '"':
                quoted = False
        elif character == '"':
            quoted = True
        elif character in "[{":
            depth += 1
            if depth > 33:
                raise operation.error(
                    "RESOURCE_LIMIT", "raw JSON container depth exceeds 33"
                )
        elif character in "]}":
            depth -= 1


def _envelope_budget(operation: _Operation, value: object) -> None:
    nodes = objects = characters = 0

    def visit(item: object, parent_depth: int, location: tuple[str | int, ...]) -> None:
        nonlocal nodes, objects, characters
        nodes += 1
        if nodes > 8198:
            raise operation.error(
                "RESOURCE_LIMIT", "envelope node budget exceeds 8198", location
            )
        if isinstance(item, str):
            try:
                item.encode("utf-8")
            except UnicodeEncodeError:
                raise operation.error(
                    "INVALID_JSON", "decoded string is not strict UTF-8", location
                ) from None
            characters += len(item)
            if characters > 131125:
                raise operation.error(
                    "RESOURCE_LIMIT", "envelope string budget exceeds 131125", location
                )
        elif type(item) is int:
            if not -(1 << 63) <= item < (1 << 63):
                raise operation.error(
                    "INVALID_JSON", "integer exceeds signed 64-bit range", location
                )
        elif item is None or type(item) is bool:
            return
        elif isinstance(item, (dict, list)):
            depth = parent_depth + 1
            if depth > 33:
                raise operation.error(
                    "RESOURCE_LIMIT", "envelope container depth exceeds 33", location
                )
            if isinstance(item, dict):
                objects += 1
                if objects > 513:
                    raise operation.error(
                        "RESOURCE_LIMIT", "envelope object budget exceeds 513", location
                    )
                for key, child in cast(dict[object, object], item).items():
                    if not isinstance(key, str):
                        raise operation.error(
                            "INVALID_JSON", "object keys must be strings", location
                        )
                    visit(key, depth, (*location, key))
                    visit(child, depth, (*location, key))
            else:
                for index, child in enumerate(cast(list[object], item)):
                    visit(child, depth, (*location, index))
        else:
            raise operation.error("INVALID_JSON", "unsupported JSON scalar", location)

    visit(value, 0, ())


def _codec(operation: _Operation, raw: bytes) -> tuple[SuppliedAssessment, bytes, str]:
    operation.stage = "decode"
    if len(raw) > _MAX_BYTES:
        raise operation.error("RESOURCE_LIMIT", "file exceeds 1 MiB")
    if raw.startswith(b"\xef\xbb\xbf"):
        raise operation.error("INVALID_ENCODING", "UTF-8 BOM is not admitted")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        raise operation.error("INVALID_ENCODING", "file is not strict UTF-8") from None
    _depth(operation, text)

    def pairs(items: list[tuple[str, object]]) -> dict[str, object]:
        result: dict[str, object] = {}
        for key, value in items:
            if key in result:
                raise operation.error(
                    "INVALID_JSON", "duplicate decoded object key", (key,)
                )
            result[key] = value
        return result

    def integer(token: str) -> int:
        if len(token) > 20:
            raise operation.error("INVALID_JSON", "integer token exceeds 20 characters")
        number = int(token)
        if not -(1 << 63) <= number < (1 << 63):
            raise operation.error("INVALID_JSON", "integer exceeds signed 64-bit range")
        return number

    def non_integer(token: str) -> object:
        raise operation.error(
            "INVALID_JSON", "float/exponent/nonfinite tokens are not admitted"
        )

    try:
        envelope: Any = json.loads(
            text,
            object_pairs_hook=pairs,
            parse_int=integer,
            parse_float=non_integer,
            parse_constant=non_integer,
        )
    except json.JSONDecodeError as error:
        raise operation.error(
            "INVALID_JSON",
            f"malformed JSON document at line {error.lineno} column {error.colno}",
        ) from None
    _envelope_budget(operation, envelope)
    if not isinstance(envelope, dict):
        raise operation.error(
            "INVALID_JSON", "expected exact format/version/assessment envelope"
        )
    envelope = cast(dict[str, Any], envelope)
    for key in ("format", "version", "assessment"):
        if key not in envelope:
            raise operation.error("INVALID_JSON", "missing envelope field", (key,))
    for key in envelope:
        if key not in {"format", "version", "assessment"}:
            raise operation.error("INVALID_JSON", "extra envelope field", (key,))
    for key, expected in (("format", str), ("version", int), ("assessment", dict)):
        if type(envelope[key]) is not expected:
            raise operation.error("INVALID_JSON", "mistyped envelope field", (key,))
    if envelope["format"] != _FORMAT:
        raise operation.error(
            "UNSUPPORTED_FORMAT", "unsupported assessment file format", ("format",)
        )
    if envelope["version"] != 1:
        raise operation.error(
            "UNSUPPORTED_VERSION", "unsupported assessment file version", ("version",)
        )
    operation.stage = "validate"
    try:
        assessment = SuppliedAssessment.model_validate_json(
            json.dumps(envelope["assessment"], ensure_ascii=False, allow_nan=False)
        )
        operation.stage = "inspect"
        view = inspect_assessment(assessment.basis, assessment)
    except ValidationError as error:
        first = error.errors(include_input=False, include_context=False)[0]
        code = (
            "RESOURCE_LIMIT"
            if first["msg"].startswith("Value error, P08 normalized ")
            else "INVALID_ASSESSMENT"
        )
        raise operation.error(
            code,
            f"owning schema error type={first['type']}",
            ("assessment", *first["loc"]),
        ) from None
    except ValueError as error:
        if str(error) == "P08 inspection output budget exceeded (8 MiB)":
            raise operation.error(
                "RESOURCE_LIMIT", "pure inspection exceeds 8 MiB"
            ) from None
        raise
    operation.stage = "validate"
    complete = {
        "format": _FORMAT,
        "version": 1,
        "assessment": assessment.model_dump(
            mode="json", exclude_unset=False, exclude_defaults=False, exclude_none=False
        ),
    }
    _envelope_budget(operation, complete)
    canonical = (
        json.dumps(
            complete,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")
    if len(canonical) > _MAX_BYTES:
        raise operation.error("RESOURCE_LIMIT", "canonical file exceeds 1 MiB")
    return assessment, canonical, view


def _view(operation: _Operation, path: str, domain_view: str) -> str:
    operation.stage = "inspect"
    result = (
        f"Selected assessment file: {_quote(path)}\nFormat: {_quote(_FORMAT)}\nVersion: 1\n"
        + domain_view
    )
    if len(result.encode("utf-8")) > _MAX_VIEW_BYTES:
        raise operation.error("RESOURCE_LIMIT", "complete file view exceeds 8 MiB")
    return result


def _parent_binding(
    operation: _Operation,
    parts: tuple[bytes, ...],
    expected: tuple[int, int],
    code: str,
) -> int:
    try:
        current = _walk_parent(operation, parts)
        if _identity(os.fstat(current)) != expected:
            raise operation.error(code, "selected parent binding changed")
        return current
    except OSError:
        raise operation.error(code, "selected parent binding unavailable") from None
    except AssessmentFileError as error:
        if error.code == "UNSAFE_INPUT":
            raise operation.error(code, "selected parent became unsafe") from None
        raise


def _input_binding(
    operation: _Operation,
    parts: tuple[bytes, ...],
    parent: tuple[int, int],
    pinned: int,
    expected: tuple[int, int, int, int, int],
) -> None:
    operation.stage = "read"
    if _stamp(os.fstat(pinned)) != expected:
        raise operation.error("INPUT_CHANGED", "pinned input metadata changed")
    current = _parent_binding(operation, parts, parent, "INPUT_CHANGED")
    try:
        selected = operation.own(
            _open(parts[-1], os.O_PATH | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=current)
        )
    except OSError:
        raise operation.error(
            "INPUT_CHANGED", "selected input binding unavailable"
        ) from None
    if _stamp(os.fstat(selected)) != expected:
        raise operation.error("INPUT_CHANGED", "selected input binding changed")
    operation.close(selected)
    operation.close(current)


def _post_link(
    operation: _Operation,
    temporary: int,
    parent: int,
    parts: tuple[bytes, ...],
    identity: tuple[int, int],
) -> AssessmentFileError | None:
    _checkpoint(operation, "after_link")
    operation.stage = "sync"
    failure = None
    successes = 0
    for descriptor in (temporary, parent):
        try:
            _fsync(descriptor)
            successes += 1
        except OSError as error:
            if failure is None:
                failure = operation.error(
                    "PUBLISHED_SYNC_UNCONFIRMED", f"sync errno={error.errno}"
                )
    operation.sync_completed = successes == 2 and operation.visibility == "published"
    _checkpoint(operation, "completion")
    operation.stage = "publish"
    try:
        current = _parent_binding(operation, parts, identity, "PUBLISHED_PATH_CHANGED")
        selected = operation.own(
            _open(parts[-1], os.O_PATH | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=current)
        )
        if _identity(os.fstat(selected)) != _identity(os.fstat(temporary)):
            raise operation.error(
                "PUBLISHED_PATH_CHANGED", "published name identifies another inode"
            )
        operation.close(selected)
        operation.close(current)
    except OSError:
        if failure is None:
            failure = operation.error(
                "PUBLISHED_PATH_CHANGED", "published selected name unavailable"
            )
    except AssessmentFileError as error:
        if failure is None:
            failure = error
    return failure


def _perform(
    input_path: object, output_path: object, cancelled: object, *, saving: bool
) -> str:
    operation = _Operation()
    failure = None
    result = ""
    try:
        source_parts = _parts(operation, input_path, "input_path")
        output_parts = (
            _parts(operation, output_path, "output_path")
            if saving
            else cast(tuple[bytes, ...], ())
        )
        if saving and input_path == output_path:
            raise operation.error(
                "INVALID_PATH",
                "input and output selections must differ",
                ("output_path",),
            )
        if cancelled is not None and not callable(cancelled):
            raise operation.error(
                "INVALID_ARGUMENT", "cancelled must be callable", ("cancelled",)
            )
        operation.cancelled = cast(Callable[[], bool] | None, cancelled)
        _checkpoint(operation, "start")
        _platform(operation)
        operation.stage = "path"
        input_parent = _walk_parent(operation, source_parts)
        parent_identity = _identity(os.fstat(input_parent))
        pinned = operation.own(
            _open(
                source_parts[-1],
                os.O_PATH | os.O_NOFOLLOW | os.O_CLOEXEC,
                dir_fd=input_parent,
            )
        )
        info = os.fstat(pinned)
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.geteuid():
            raise operation.error(
                "UNSAFE_INPUT", "input must be a caller-owned regular file"
            )
        stamp = _stamp(info)
        _ext4(operation, pinned)
        operation.stage = "read"
        reader = operation.own(
            _open(f"/proc/self/fd/{pinned}", os.O_RDONLY | os.O_CLOEXEC)
        )
        if _identity(os.fstat(reader)) != _identity(info):
            raise operation.error("INPUT_CHANGED", "pinned input reopen mismatch")
        if info.st_size > _MAX_BYTES:
            raise operation.error("RESOURCE_LIMIT", "input size exceeds 1 MiB")
        raw = _bounded_read(operation, reader, _MAX_BYTES)
        operation.close(reader)
        _input_binding(operation, source_parts, parent_identity, pinned, stamp)
        _, canonical, domain_view = _codec(operation, raw)
        result = _view(operation, cast(str, input_path), domain_view)
        if saving:
            _view(operation, cast(str, output_path), domain_view)
            operation.stage = "path"
            parent_pin = _walk_parent(operation, output_parts)
            output_parent_identity = _identity(os.fstat(parent_pin))
            _ext4(operation, parent_pin)
            parent = operation.own(
                _open(
                    f"/proc/self/fd/{parent_pin}",
                    os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC,
                )
            )
            if _identity(os.fstat(parent)) != output_parent_identity:
                raise operation.error(
                    "OUTPUT_PARENT_CHANGED", "destination parent reopen mismatch"
                )
            _checkpoint(operation, "prepare")
            operation.stage = "prepare"
            try:
                temporary = operation.own(
                    _open(
                        ".",
                        os.O_TMPFILE | os.O_RDWR | os.O_CLOEXEC,
                        0o600,
                        dir_fd=parent,
                    )
                )
            except OSError as error:
                if error.errno in {
                    errno.EOPNOTSUPP,
                    errno.ENOSYS,
                    errno.EINVAL,
                    errno.EISDIR,
                    errno.ENOENT,
                }:
                    raise operation.error(
                        "UNSUPPORTED_PLATFORM", "O_TMPFILE creation unavailable"
                    ) from None
                raise
            os.fchmod(temporary, 0o600)
            operation.stage = "write"
            written = 0
            while written < len(canonical):
                _checkpoint(operation, "write")
                count = _write(temporary, canonical[written : written + _BLOCK])
                if count <= 0:
                    raise operation.error("IO_ERROR", "write made no progress")
                written += count
            operation.stage = "sync"
            _fsync(temporary)
            _checkpoint(operation, "before_link")
            _input_binding(operation, source_parts, parent_identity, pinned, stamp)
            operation.stage = "path"
            current = _parent_binding(
                operation, output_parts, output_parent_identity, "OUTPUT_PARENT_CHANGED"
            )
            operation.close(current)
            operation.stage = "publish"
            operation.attempted = True
            link_failure = None
            try:
                _link(
                    f"/proc/self/fd/{temporary}",
                    output_parts[-1],
                    dst_dir_fd=parent,
                    follow_symlinks=True,
                )
                operation.visibility = "published"
            except OSError as error:
                if error.errno == errno.EEXIST:
                    raise operation.error(
                        "DESTINATION_EXISTS", "selected destination already exists"
                    ) from None
                if error.errno not in {errno.EIO, errno.EINTR}:
                    code = (
                        "UNSUPPORTED_PLATFORM"
                        if error.errno in {errno.EOPNOTSUPP, errno.ENOSYS, errno.ENOENT}
                        else "IO_ERROR"
                    )
                    raise operation.error(code, f"link errno={error.errno}") from None
                operation.visibility = "uncertain"
                try:
                    observed = operation.own(
                        _open(
                            output_parts[-1],
                            os.O_PATH | os.O_NOFOLLOW | os.O_CLOEXEC,
                            dir_fd=parent,
                        )
                    )
                    if _identity(os.fstat(observed)) == _identity(os.fstat(temporary)):
                        operation.visibility = "published"
                    operation.close(observed)
                except (OSError, AssessmentFileError) as observation_error:
                    operation.deferred = (
                        observation_error
                        if isinstance(observation_error, AssessmentFileError)
                        else operation.error(
                            "PUBLICATION_UNCERTAIN", "bounded name observation failed"
                        )
                    )
                code = (
                    "IO_ERROR"
                    if operation.visibility == "published"
                    else "PUBLICATION_UNCERTAIN"
                )
                link_failure = operation.error(
                    code, f"link outcome errno={error.errno}"
                )
            settled_failure = _post_link(
                operation, temporary, parent, output_parts, output_parent_identity
            )
            if (
                settled_failure is not None
                and settled_failure.code == "PUBLISHED_SYNC_UNCONFIRMED"
            ):
                failure = settled_failure
                if link_failure is not None:
                    failure.add_note(str(link_failure))
            else:
                failure = link_failure or settled_failure
            result = cast(str, output_path)
        else:
            _checkpoint(operation, "completion")
            _input_binding(operation, source_parts, parent_identity, pinned, stamp)
    except AssessmentFileError as error:
        failure = error
    except OSError as error:
        failure = operation.error("IO_ERROR", f"OS errno={error.errno}")
    except BaseException:
        operation.close_all()
        raise
    if not operation.completion_sampled:
        try:
            _checkpoint(operation, "completion")
        except AssessmentFileError as error:
            if failure is None:
                failure = error
    close_failure = operation.close_all()
    if close_failure is not None and (
        failure is None or failure.code in {"CANCELLED", "CANCEL_CHECK_FAILED"}
    ):
        failure = close_failure
    failure = failure or operation.deferred
    if failure is not None:
        failure.output_visibility = operation.visibility
        failure.sync_completed = operation.sync_completed
        failure.cancel_requested = operation.cancel_requested
        raise failure from None
    return result


def inspect_assessment_file(
    input_path: str, *, cancelled: Callable[[], bool] | None = None
) -> str:
    """Inspect one selected v1 file after validating its complete reopenable value."""
    return _perform(input_path, None, cancelled, saving=False)


def save_assessment_as_new(
    input_path: str, output_path: str, *, cancelled: Callable[[], bool] | None = None
) -> str:
    """Publish complete canonical bytes once, without overwrite, then sync/close."""
    return _perform(input_path, output_path, cancelled, saving=True)
