"""Finite CLI boundary witnesses; installed real operations are separate from mocks."""

from __future__ import annotations

import io
import json
import os
import selectors
import signal
import stat
import subprocess
import sys
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

import pytest
from conftest import PreparedBuild, checked_distributions
from test_assessment_file import (
    CANONICAL,
    SPARSE,
    _assert_real_ext4,  # pyright: ignore[reportPrivateUsage] - reuse approved test seam
    _expected_view,  # pyright: ignore[reportPrivateUsage] - reuse authored S02 oracle
)
from typer.testing import CliRunner

import faultatlas.cli as cli
from faultatlas.assessment_file import AssessmentFileError

ROOT = Path(__file__).resolve().parents[1]
runner = CliRunner()


def _deny(*args: Any, **kwargs: Any) -> Any:
    pytest.fail("unexpected selected-file operation or handler installation")


@pytest.mark.parametrize(
    "args",
    [
        [],
        ["--help"],
        ["assessment"],
        ["assessment", "--help"],
        ["assessment", "inspect", "--help"],
        ["assessment", "save-as", "--help"],
        ["--version"],
        ["--version", "assessment", "save-as"],
    ],
)
def test_help_and_eager_version_do_no_work(
    monkeypatch: pytest.MonkeyPatch, args: list[str]
) -> None:
    monkeypatch.setattr(cli, "inspect_assessment_file", _deny)
    monkeypatch.setattr(cli, "save_assessment_as_new", _deny)
    monkeypatch.setattr(signal, "signal", _deny)
    result = runner.invoke(cli.app, args)
    assert result.exit_code == 0 and result.stderr == "", result.output
    if "--version" in args:
        assert result.stdout == "0.1.0\n"
    else:
        assert "Usage:" in result.stdout


@pytest.mark.parametrize(
    "args",
    [
        ["assessment", "inspect"],
        ["assessment", "save-as", "/x"],
        ["assessment", "inspect", "/x", "extra"],
        ["assessment", "save-as", "/x", "/y", "extra"],
        ["assessment", "inspect", "--force"],
        ["assessment", "\x1b]8;;url\x07[red]\u202e"],
        ["--bad\x7f\n"],
    ],
)
def test_usage_tokens_never_echo_or_enter_service(
    monkeypatch: pytest.MonkeyPatch, args: list[str]
) -> None:
    monkeypatch.setattr(cli, "inspect_assessment_file", _deny)
    monkeypatch.setattr(cli, "save_assessment_as_new", _deny)
    monkeypatch.setattr(signal, "signal", _deny)
    result = runner.invoke(cli.app, args)
    assert result.exit_code == 2 and result.stdout == ""
    assert (
        result.stderr
        == "CLI_USAGE: output_visibility=not_published; sync_completed=false; cancel_requested=false\n"
    )


@pytest.mark.parametrize(
    "path", ["-", "relative", "/selected/é [red]\x7f\u202e\n.json"]
)
@pytest.mark.parametrize("save", [False, True])
def test_exact_single_public_delegation_and_plain_output(
    monkeypatch: pytest.MonkeyPatch, path: str, save: bool
) -> None:
    calls: list[tuple[str, ...]] = []
    view = _expected_view(path)
    target = path + ".new" if path != "-" else "-"

    def inspect(selected: str, *, cancelled: Callable[[], bool]) -> str:
        assert cancelled() is False
        calls.append((selected,))
        return view

    def saving(selected: str, output: str, *, cancelled: Callable[[], bool]) -> str:
        assert cancelled() is False
        calls.append((selected, output))
        return output

    monkeypatch.setattr(cli, "inspect_assessment_file", inspect if not save else _deny)
    monkeypatch.setattr(cli, "save_assessment_as_new", saving if save else _deny)
    result = runner.invoke(
        cli.app,
        [
            "assessment",
            "save-as" if save else "inspect",
            path,
            *([target] if save else []),
        ],
        color=True,
    )
    assert result.exit_code == 0 and result.stderr == "", result.output
    assert calls == [(path, target) if save else (path,)]
    quoted = json.dumps(target, ensure_ascii=True).replace("\x7f", "\\u007f")
    assert result.stdout == (
        f"Saved new assessment file: {quoted}\noutput_visibility=published; sync_completed=true\n"
        if save
        else view
    )


@pytest.mark.parametrize("ending", ["", "\n"])
def test_view_only_adds_missing_lf(
    monkeypatch: pytest.MonkeyPatch, ending: str
) -> None:
    def view(*args: Any, **kwargs: Any) -> str:
        return "End of complete view" + ending

    monkeypatch.setattr(cli, "inspect_assessment_file", view)
    result = runner.invoke(cli.app, ["assessment", "inspect", "/x"])
    assert (
        result.exit_code == 0
        and result.stdout == "End of complete view\n"
        and result.stderr == ""
    )


# One row per published S02 code, plus the meaningful settled-effect variants.
ERROR_ROWS = [
    (code, "not_published", False)
    for code in (
        "INVALID_ARGUMENT",
        "INVALID_PATH",
        "UNSUPPORTED_PLATFORM",
        "UNSAFE_INPUT",
        "INPUT_CHANGED",
        "OUTPUT_PARENT_CHANGED",
        "INVALID_ENCODING",
        "INVALID_JSON",
        "UNSUPPORTED_FORMAT",
        "UNSUPPORTED_VERSION",
        "INVALID_ASSESSMENT",
        "RESOURCE_LIMIT",
        "DESTINATION_EXISTS",
        "IO_ERROR",
        "CLOSE_FAILED",
        "CANCELLED",
        "CANCEL_CHECK_FAILED",
    )
] + [
    ("PUBLICATION_UNCERTAIN", "uncertain", False),
    ("PUBLISHED_SYNC_UNCONFIRMED", "published", False),
    ("PUBLISHED_PATH_CHANGED", "published", True),
    ("CLOSE_FAILED", "published", True),
    ("IO_ERROR", "published", True),
    ("CANCELLED", "published", True),
    ("CANCEL_CHECK_FAILED", "published", True),
]


@pytest.mark.parametrize("code,visibility,synced", ERROR_ROWS)
@pytest.mark.parametrize("signum", [None, signal.SIGINT, signal.SIGTERM])
def test_service_mapping_retains_full_diagnostic_and_primary_precedence(
    monkeypatch: pytest.MonkeyPatch,
    code: str,
    visibility: str,
    synced: bool,
    signum: signal.Signals | None,
) -> None:
    error = AssessmentFileError(
        code,
        "test",
        input_path="/" + "\x1b\x7f\u202e[red]" * 4000,
        output_path="/out",
        location=("opinion", 1),
        detail="\n\x1b]8;;url\x07" * 4000,
        output_visibility=visibility,
        sync_completed=synced,
        cancel_requested=signum is not None,
    )

    def fail(*args: Any, **kwargs: Any) -> str:
        if signum is not None:
            handler: Any = signal.getsignal(signum)
            handler(signum, None)
            assert kwargs["cancelled"]() is True
        raise error

    monkeypatch.setattr(cli, "save_assessment_as_new", fail)
    result = runner.invoke(cli.app, ["assessment", "save-as", "/in", "/out"])
    assert result.exit_code == (
        128 + signum if code == "CANCELLED" and signum is not None else 1
    )
    assert result.stdout == "" and result.stderr == str(error) + "\n"
    assert len(result.stderr.encode()) <= 16385
    assert (
        result.stderr.isascii()
        and "\x1b" not in result.stderr
        and "\x7f" not in result.stderr
        and "abbreviated" in result.stderr
    )


@pytest.mark.parametrize("primary", [False, True])
def test_late_first_signal_and_sequential_handler_restoration(
    monkeypatch: pytest.MonkeyPatch, primary: bool
) -> None:
    previous = {sig: signal.getsignal(sig) for sig in (signal.SIGINT, signal.SIGTERM)}
    count = 0
    error = AssessmentFileError(
        "IO_ERROR", "close", output_visibility="published", sync_completed=True
    )

    def operation(*args: Any, **kwargs: Any) -> str:
        nonlocal count
        count += 1
        assert kwargs["cancelled"]() is False
        if count == 1:
            handler: Any = signal.getsignal(signal.SIGTERM)
            handler(signal.SIGTERM, None)
            handler(signal.SIGINT, None)
            if primary:
                raise error
        return "/out"

    monkeypatch.setattr(cli, "save_assessment_as_new", operation)
    first = runner.invoke(cli.app, ["assessment", "save-as", "/in", "/out"])
    assert first.exit_code == (1 if primary else 143)
    assert (
        first.stdout == ""
        and "CLI_CANCELLED: output_visibility=published; sync_completed=true; cancel_requested=true; signal=15\n"
        in first.stderr
    )
    if primary:
        assert first.stderr.startswith(str(error) + "\n")
    assert {sig: signal.getsignal(sig) for sig in previous} == previous
    second = runner.invoke(cli.app, ["assessment", "save-as", "/in", "/out"])
    assert second.exit_code == 0 and second.stderr == "" and count == 2
    assert {sig: signal.getsignal(sig) for sig in previous} == previous


@pytest.mark.parametrize("failure_at", [1, 2, 3, 4])
@pytest.mark.parametrize("primary", [False, True])
def test_partial_setup_and_restore_failures(
    monkeypatch: pytest.MonkeyPatch, failure_at: int, primary: bool
) -> None:
    previous = {sig: signal.getsignal(sig) for sig in (signal.SIGINT, signal.SIGTERM)}
    real_signal = signal.signal
    changes: list[int] = []
    calls: list[str] = []
    error = AssessmentFileError("IO_ERROR", "sync", output_visibility="published")

    def changing(sig: Any, handler: Any) -> Any:
        changes.append(int(sig))
        if len(changes) == failure_at:
            raise OSError("private failure payload")
        return real_signal(sig, handler)

    def operation(*args: Any, **kwargs: Any) -> str:
        calls.append("save")
        if primary:
            raise error
        return "/out"

    monkeypatch.setattr(signal, "signal", changing)
    monkeypatch.setattr(cli, "save_assessment_as_new", operation)
    try:
        result = runner.invoke(cli.app, ["assessment", "save-as", "/in", "/out"])
        assert result.exit_code == 1 and result.stdout == ""
        assert (
            "CLI_SIGNAL_SETUP" if failure_at < 3 else "CLI_SIGNAL_RESTORE"
        ) in result.stderr
        assert calls == ([] if failure_at < 3 else ["save"])
        assert "private failure payload" not in result.stderr
        if primary and failure_at >= 3:
            assert result.stderr.startswith(str(error) + "\n")
        if failure_at < 3:
            assert {sig: signal.getsignal(sig) for sig in previous} == previous
        if failure_at == 3:
            assert len(changes) == 4  # The other restoration is still attempted.
    finally:
        for sig, handler in previous.items():
            real_signal(sig, handler)


def test_nonmain_thread_refuses_before_file_work(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(cli, "inspect_assessment_file", _deny)
    with ThreadPoolExecutor(max_workers=1) as executor:
        result = executor.submit(
            runner.invoke, cli.app, ["assessment", "inspect", "/x"]
        ).result()
    assert result.exit_code == 1 and "CLI_SIGNAL_SETUP" in result.stderr


def test_unexpected_exception_does_not_invent_file_effects_or_disclose(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail(*args: Any, **kwargs: Any) -> str:
        raise RuntimeError("SECRET untrusted payload")

    monkeypatch.setattr(cli, "save_assessment_as_new", fail)
    result = runner.invoke(cli.app, ["assessment", "save-as", "/in", "/out"])
    assert result.exit_code == 1 and result.stdout == ""
    assert (
        result.stderr
        == "CLI_INTERNAL: output_visibility=uncertain; sync_completed=unestablished; cancel_requested=false\n"
    )


class FailedStream(io.StringIO):
    def __init__(self, point: str) -> None:
        super().__init__()
        self.point = point
        self.writes = 0
        self.flushes = 0

    def write(self, value: str) -> int:
        self.writes += 1
        if self.point == "write":
            raise BrokenPipeError()
        if self.point == "short":
            return 0
        return super().write(value)

    def flush(self) -> None:
        self.flushes += 1
        if self.point == "flush":
            raise OSError("flush failed")


@pytest.mark.parametrize("point", ["write", "short", "flush"])
@pytest.mark.parametrize("both", [False, True])
def test_save_receipt_delivery_failure_keeps_effects_without_retry(
    monkeypatch: pytest.MonkeyPatch, point: str, both: bool
) -> None:
    output = FailedStream(point)
    error = FailedStream("write") if both else io.StringIO()
    calls: list[str] = []

    def saved(*args: Any, **kwargs: Any) -> str:
        calls.append("saved")
        return "/out"

    monkeypatch.setattr(cli, "save_assessment_as_new", saved)
    monkeypatch.setattr(sys, "stdout", output)
    monkeypatch.setattr(sys, "stderr", error)
    assert (
        cli.app(args=["assessment", "save-as", "/in", "/out"], standalone_mode=False)
        == 1
    )
    assert sys.stdout is output and sys.stderr is error
    assert calls == ["saved"] and output.writes == 1
    if both:
        assert isinstance(error, FailedStream) and error.writes == 1
    else:
        assert (
            error.getvalue()
            == "CLI_OUTPUT: output_visibility=published; sync_completed=true; cancel_requested=false\n"
        )


def test_failed_service_stderr_is_not_retried(monkeypatch: pytest.MonkeyPatch) -> None:
    error_stream = FailedStream("flush")

    def fail(*args: Any, **kwargs: Any) -> str:
        raise AssessmentFileError("IO_ERROR", "read")

    monkeypatch.setattr(cli, "inspect_assessment_file", fail)
    monkeypatch.setattr(sys, "stderr", error_stream)
    assert cli.app(args=["assessment", "inspect", "/in"], standalone_mode=False) == 1
    assert error_stream.writes == error_stream.flushes == 1


@pytest.mark.parametrize("missing", ["stdout", "stderr", "both"])
def test_absent_streams_preserve_effects_and_do_not_retry(
    monkeypatch: pytest.MonkeyPatch, missing: str
) -> None:
    output = None if missing in {"stdout", "both"} else io.StringIO()
    error = None if missing in {"stderr", "both"} else io.StringIO()
    calls: list[str] = []

    def operation(*args: Any, **kwargs: Any) -> str:
        calls.append("save")
        if missing == "stderr":
            raise AssessmentFileError("IO_ERROR", "read")
        return "/out"

    monkeypatch.setattr(cli, "save_assessment_as_new", operation)
    monkeypatch.setattr(sys, "stdout", output)
    monkeypatch.setattr(sys, "stderr", error)
    assert (
        cli.app(args=["assessment", "save-as", "/in", "/out"], standalone_mode=False)
        == 1
    )
    assert calls == ["save"] and sys.stdout is output and sys.stderr is error
    if error is not None:
        assert (
            error.getvalue()
            == "CLI_OUTPUT: output_visibility=published; sync_completed=true; cancel_requested=false\n"
        )
    if output is not None:
        assert output.getvalue() == ""


@pytest.mark.parametrize(
    "args",
    [["--version"], ["--help"], ["assessment"], ["assessment", "inspect", "--help"]],
)
def test_help_version_delivery_failures_are_nonzero(
    monkeypatch: pytest.MonkeyPatch, args: list[str]
) -> None:
    output, error = FailedStream("flush"), io.StringIO()
    monkeypatch.setattr(sys, "stdout", output)
    monkeypatch.setattr(sys, "stderr", error)
    monkeypatch.setattr(cli, "inspect_assessment_file", _deny)
    monkeypatch.setattr(signal, "signal", _deny)
    assert cli.app(args=args, standalone_mode=False) == 1
    assert error.getvalue().startswith("CLI_OUTPUT:")
    assert output.writes == 1 and sys.stdout is output


def _prepare(path: Path, contents: bytes) -> None:
    # Test fixture only: selected production commands never create inputs/parents.
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as stream:
        assert stream.write(contents) == len(contents)


@pytest.fixture
def documented(tmp_path: Path) -> Path:
    _assert_real_ext4(tmp_path)
    document = (ROOT / "docs/contracts/s1-p08-s03-assessment-cli.md").read_text()
    exact = document.split("```json\n", 1)[1].split("\n```", 1)[0].encode() + b"\n"
    assert json.loads(exact) == json.loads(SPARSE)
    path = tmp_path / "é [red]\x7f\u202e input.json"
    _prepare(path, exact)
    return path


type Installed = tuple[Path, dict[str, str]]


@pytest.fixture(scope="session")
def installed_cli(
    normal_distributions: PreparedBuild, tmp_path_factory: pytest.TempPathFactory
) -> Installed:
    wheel, _ = checked_distributions(normal_distributions, ROOT)
    parent = tmp_path_factory.mktemp("s03-installed")
    target = parent / "package"
    environment = {
        key: value
        for key, value in os.environ.items()
        if key in {"HOME", "PATH", "LANG", "LC_ALL", "TMPDIR", "UV_CACHE_DIR"}
    }
    environment.update(UV_OFFLINE="1", UV_NO_SYNC="1", UV_PYTHON_DOWNLOADS="never")
    result = subprocess.run(
        [
            "uv",
            "pip",
            "install",
            "--offline",
            "--no-deps",
            "--python",
            sys.executable,
            "--target",
            str(target),
            str(wheel),
        ],
        cwd=parent,
        env=environment,
        capture_output=True,
        check=False,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    executable = target / "bin/faultatlas"
    assert executable.is_file() and os.access(executable, os.X_OK)
    environment["PYTHONPATH"] = str(target)
    probe = "import pathlib,sys; import faultatlas.cli; root=pathlib.Path(sys.argv[1]); assert all(pathlib.Path(m.__file__).is_relative_to(root) for n,m in sys.modules.copy().items() if n=='faultatlas' or n.startswith('faultatlas.')); print('installed CLI provenance PASS')"
    result = subprocess.run(
        [sys.executable, "-c", probe, str(target)],
        cwd=parent,
        env=environment,
        capture_output=True,
        check=False,
        timeout=10,
    )
    assert (
        result.returncode == 0 and result.stdout == b"installed CLI provenance PASS\n"
    ), result.stderr
    return executable, environment


def _command(
    installed: Installed, cwd: Path, *args: str, module: bool = False
) -> subprocess.CompletedProcess[bytes]:
    executable, env = installed
    prefix = [sys.executable, "-m", "faultatlas"] if module else [str(executable)]
    return subprocess.run(
        [*prefix, *args], cwd=cwd, env=env, capture_output=True, check=False, timeout=20
    )


def _stable(path: Path) -> tuple[int, ...]:
    value = path.stat()
    return (
        value.st_dev,
        value.st_ino,
        value.st_mode,
        value.st_uid,
        value.st_gid,
        value.st_nlink,
        value.st_size,
        value.st_mtime_ns,
        value.st_ctime_ns,
    )


def test_actual_installed_document_inspect_save_reopen_resave(
    installed_cli: Installed, documented: Path
) -> None:
    source = documented
    parent = source.parent
    before = source.read_bytes(), _stable(source)
    saved, resaved = parent / "saved.json", parent / "resaved.json"
    for selected in (source, saved):
        result = _command(installed_cli, parent, "assessment", "inspect", str(selected))
        assert (result.returncode, result.stdout, result.stderr) == (
            0,
            _expected_view(str(selected)).encode(),
            b"",
        )
        target = saved if selected == source else resaved
        result = _command(
            installed_cli, parent, "assessment", "save-as", str(selected), str(target)
        )
        assert (result.returncode, result.stdout, result.stderr) == (
            0,
            f'Saved new assessment file: "{target}"\noutput_visibility=published; sync_completed=true\n'.encode(),
            b"",
        )
        assert (
            target.read_bytes() == CANONICAL
            and stat.S_IMODE(target.stat().st_mode) == 0o600
        )
    parity = _command(
        installed_cli, parent, "assessment", "inspect", str(resaved), module=True
    )
    assert (parity.returncode, parity.stdout, parity.stderr) == (
        0,
        _expected_view(str(resaved)).encode(),
        b"",
    )
    collision = _command(
        installed_cli, parent, "assessment", "save-as", str(source), str(saved)
    )
    assert (
        collision.returncode == 1
        and collision.stdout == b""
        and b'"DESTINATION_EXISTS"' in collision.stderr
    )
    assert saved.read_bytes() == CANONICAL
    assert (source.read_bytes(), _stable(source)) == before


@pytest.mark.parametrize(
    "value,code",
    [
        (b"{", b"INVALID_JSON"),
        (SPARSE.replace(b'"version":1', b'"version":2'), b"UNSUPPORTED_VERSION"),
    ],
)
def test_installed_rejection_does_not_publish(
    installed_cli: Installed, tmp_path: Path, value: bytes, code: bytes
) -> None:
    source, target = tmp_path / "bad.json", tmp_path / "absent.json"
    _prepare(source, value)
    result = _command(
        installed_cli, tmp_path, "assessment", "save-as", str(source), str(target)
    )
    assert (
        result.returncode == 1
        and result.stdout == b""
        and code in result.stderr
        and not target.exists()
    )


@pytest.mark.parametrize("path", ["-", "relative"])
def test_installed_relative_and_dash_remain_service_failures(
    installed_cli: Installed, tmp_path: Path, path: str
) -> None:
    result = _command(installed_cli, tmp_path, "assessment", "inspect", path)
    assert (
        result.returncode == 1
        and result.stdout == b""
        and b'"INVALID_PATH"' in result.stderr
    )


@pytest.mark.parametrize("module", [False, True])
def test_real_utf8_argv_under_ascii_filesystem_encoding(
    installed_cli: Installed, documented: Path, module: bool
) -> None:
    executable, env = installed_cli
    env = env | {
        "LC_ALL": "C",
        "LANG": "C",
        "PYTHONCOERCECLOCALE": "0",
        "PYTHONUTF8": "0",
    }
    encoding = subprocess.run(
        [sys.executable, "-c", "import sys; print(sys.getfilesystemencoding())"],
        env=env,
        cwd=documented.parent,
        capture_output=True,
        check=False,
        timeout=10,
    )
    assert encoding.returncode == 0 and encoding.stdout == b"ascii\n"
    prefix = (
        [os.fsencode(sys.executable), b"-m", b"faultatlas"]
        if module
        else [os.fsencode(executable)]
    )
    target = documented.parent / "α-output.json"
    for args, expected in [
        (
            [b"inspect", str(documented).encode()],
            _expected_view(str(documented)).encode(),
        ),
        (
            [b"save-as", str(documented).encode(), str(target).encode()],
            f"Saved new assessment file: {json.dumps(str(target), ensure_ascii=True)}\noutput_visibility=published; sync_completed=true\n".encode(),
        ),
    ]:
        result = subprocess.run(
            [*prefix, b"assessment", *args],
            env=env,
            cwd=documented.parent,
            capture_output=True,
            check=False,
            timeout=20,
        )
        assert (result.returncode, result.stdout, result.stderr) == (0, expected, b"")
    assert target.read_bytes() == CANONICAL
    invalid = subprocess.run(
        [
            *prefix,
            b"assessment",
            b"save-as",
            str(documented).encode(),
            os.fsencode(documented.parent) + b"/\xff\x1b.json",
        ],
        env=env,
        cwd=documented.parent,
        capture_output=True,
        check=False,
        timeout=20,
    )
    assert (
        invalid.returncode == 2
        and invalid.stdout == b""
        and invalid.stderr
        == b"CLI_ARGUMENT_ENCODING: output_visibility=not_published; sync_completed=false; cancel_requested=false\n"
    )
    assert not os.path.lexists(os.fsencode(documented.parent) + b"/\xff\x1b.json")


@pytest.mark.parametrize("signum", [signal.SIGINT, signal.SIGTERM])
@pytest.mark.parametrize("point", ["before_link", "returned"])
def test_instrumented_installed_real_signal_settles_s02(
    installed_cli: Installed, documented: Path, signum: signal.Signals, point: str
) -> None:
    _, env = installed_cli
    target = documented.parent / "signalled.json"
    ready_read, ready_write = os.pipe()
    go_read, go_write = os.pipe()
    # Test-only wrapper: real S02 operation, deterministic handshake, no product backdoor.
    probe = r"""
import os,signal,sys
import faultatlas.cli as cli
import faultatlas.assessment_file as service
ready,go,point=int(sys.argv[1]),int(sys.argv[2]),sys.argv[3]
sys.argv=["faultatlas",*sys.argv[4:]]
prior={s:signal.getsignal(s) for s in (signal.SIGINT,signal.SIGTERM)}
def pause():
    os.write(ready,b"ready")
    assert os.read(go,1)==b"g"
original=service._checkpoint
def checkpoint(operation,current):
    if current==point: pause()
    original(operation,current)
service._checkpoint=checkpoint
save=cli.save_assessment_as_new
def saving(*args,**kwargs):
    result=save(*args,**kwargs)
    if point=="returned": pause()
    return result
cli.save_assessment_as_new=saving
try: cli.app()
except SystemExit as error:
    assert {s:signal.getsignal(s) for s in prior}==prior
    raise
"""
    child: subprocess.Popen[bytes] | None = None
    try:
        child = subprocess.Popen(
            [
                sys.executable,
                "-c",
                probe,
                str(ready_write),
                str(go_read),
                point,
                "assessment",
                "save-as",
                str(documented),
                str(target),
            ],
            env=env,
            cwd=documented.parent,
            pass_fds=(ready_write, go_read),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        os.close(ready_write)
        ready_write = -1
        os.close(go_read)
        go_read = -1
        with selectors.DefaultSelector() as selector:
            selector.register(ready_read, selectors.EVENT_READ)
            assert selector.select(timeout=15), (
                "owned child did not reach instrumented handshake"
            )
        assert os.read(ready_read, 5) == b"ready"
        if point == "returned":
            assert target.read_bytes() == CANONICAL
        else:
            assert not target.exists()
        child.send_signal(signum)
        os.write(go_write, b"g")
        stdout, stderr = child.communicate(timeout=15)
        assert child.returncode == 128 + signum and stdout == b"", stderr
        assert b"cancel_requested=True" in stderr or b"cancel_requested=true" in stderr
        if point == "returned":
            assert stderr.startswith(
                b"CLI_CANCELLED: output_visibility=published; sync_completed=true;"
            )
            assert (
                target.read_bytes() == CANONICAL
                and stat.S_IMODE(target.stat().st_mode) == 0o600
            )
        else:
            assert (
                b'"CANCELLED"' in stderr
                and b'visibility="not_published"' in stderr
                and not target.exists()
            )
    finally:
        for fd in (ready_read, ready_write, go_read, go_write):
            if fd >= 0:
                os.close(fd)
        if child is not None and child.poll() is None:
            child.kill()
            child.communicate(timeout=10)


def test_real_closed_reader_after_successful_save(
    installed_cli: Installed, documented: Path
) -> None:
    executable, env = installed_cli
    target = documented.parent / "published-with-broken-receipt.json"
    read_fd, write_fd = os.pipe()
    os.close(read_fd)
    try:
        result = subprocess.run(
            [str(executable), "assessment", "save-as", str(documented), str(target)],
            env=env,
            cwd=documented.parent,
            stdout=write_fd,
            stderr=subprocess.PIPE,
            check=False,
            timeout=20,
        )
    finally:
        os.close(write_fd)
    assert result.returncode == 1
    assert (
        result.stderr
        == b"CLI_OUTPUT: output_visibility=published; sync_completed=true; cancel_requested=false\n"
    )
    assert (
        target.read_bytes() == CANONICAL
        and stat.S_IMODE(target.stat().st_mode) == 0o600
    )
    assert sorted(documented.parent.iterdir()) == sorted([documented, target])


@pytest.mark.parametrize("closed", ["1", "1,2"])
def test_installed_startup_without_stdout_keeps_published_effects(
    installed_cli: Installed, documented: Path, closed: str
) -> None:
    executable, env = installed_cli
    target = documented.parent / "published-without-stdout.json"
    # Owned launch instrumentation closes only this child's standard descriptors.
    # exec starts the unchanged generated console with genuinely absent streams.
    launch = "import os,sys; [os.close(int(fd)) for fd in sys.argv[1].split(',')]; os.execve(sys.argv[2],sys.argv[2:],dict(os.environ))"
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            launch,
            closed,
            str(executable),
            "assessment",
            "save-as",
            str(documented),
            str(target),
        ],
        env=env,
        cwd=documented.parent,
        capture_output=True,
        check=False,
        timeout=20,
    )
    assert result.returncode == 1 and result.stdout == b""
    assert result.stderr == (
        b"CLI_OUTPUT: output_visibility=published; sync_completed=true; cancel_requested=false\n"
        if closed == "1"
        else b""
    )
    assert target.read_bytes() == CANONICAL
    assert stat.S_IMODE(target.stat().st_mode) == 0o600


def test_installed_predispatch_sigint_has_controlled_diagnostic(
    installed_cli: Installed, tmp_path: Path
) -> None:
    _, env = installed_cli
    ready_read, ready_write = os.pipe()
    # Test-only launch seam interrupts the real installed command before parsing.
    probe = r"""
import os,signal,sys
import faultatlas.cli as cli
from typer.main import get_command
ready=int(sys.argv[1])
sys.argv=["faultatlas","--help"]
prior={s:signal.getsignal(s) for s in (signal.SIGINT,signal.SIGTERM)}
called=[]
def unexpected(*args,**kwargs):
    called.append(True)
    raise AssertionError("pre-dispatch must not call S02")
cli.inspect_assessment_file=unexpected
cli.save_assessment_as_new=unexpected
def pause(*args,**kwargs):
    os.write(ready,b"ready")
    signal.pause()
    raise AssertionError("SIGINT should interrupt the default handler")
get_command(cli.app).__class__.make_context=pause
try: cli.app()
except SystemExit:
    assert not called
    assert {s:signal.getsignal(s) for s in prior}==prior
    raise
"""
    child: subprocess.Popen[bytes] | None = None
    try:
        child = subprocess.Popen(
            [sys.executable, "-c", probe, str(ready_write)],
            cwd=tmp_path,
            env=env,
            pass_fds=(ready_write,),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        os.close(ready_write)
        ready_write = -1
        with selectors.DefaultSelector() as selector:
            selector.register(ready_read, selectors.EVENT_READ)
            assert selector.select(timeout=15), (
                "pre-dispatch child did not reach handshake"
            )
        assert os.read(ready_read, 5) == b"ready"
        child.send_signal(signal.SIGINT)
        stdout, stderr = child.communicate(timeout=15)
        assert child.returncode == 1 and stdout == b""
        assert (
            stderr
            == b"CLI_INTERNAL: output_visibility=uncertain; sync_completed=unestablished; cancel_requested=false\n"
        )
    finally:
        os.close(ready_read)
        if ready_write >= 0:
            os.close(ready_write)
        if child is not None and child.poll() is None:
            child.kill()
            child.communicate(timeout=10)
