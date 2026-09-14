"""Plain selected-file commands over the public S02 API."""

from __future__ import annotations

import json
import os
import signal
import sys
import threading
from collections.abc import Sequence
from dataclasses import dataclass
from types import FrameType
from typing import Annotated, Any, TextIO, cast

import typer
from typer._click import Context, Parameter
from typer._click.exceptions import UsageError
from typer.core import TyperCommand, TyperGroup, TyperOption

from faultatlas import __version__
from faultatlas.assessment_file import (
    AssessmentFileError,
    inspect_assessment_file,
    save_assessment_as_new,
)


@dataclass
class _Effects:
    visibility: str = "not_published"
    sync: str = "false"
    cancelled: bool = False


class _DeliveryFailed(Exception):
    def __init__(self, stream: TextIO | None) -> None:
        self.stream = stream


def _emit(stream: TextIO | None, text: str) -> None:
    """Acknowledge write and flush without a buffered EPIPE payload."""
    try:
        if stream is None:
            raise OSError("output stream unavailable")
        if stream is sys.__stdout__ or stream is sys.__stderr__:
            stream.flush()
            payload = text.encode("utf-8")
            offset = 0
            while offset < len(payload):
                count = os.write(stream.fileno(), payload[offset : offset + 65536])
                if count <= 0:
                    raise OSError("output write made no progress")
                offset += count
        elif stream.write(text) != len(text):
            raise OSError("short output write")
        stream.flush()
    except (OSError, ValueError):
        raise _DeliveryFailed(stream) from None


def _cli(code: str, effects: _Effects, *, signum: int | None = None) -> str:
    suffix = f"; signal={signum}" if signum is not None else ""
    return (
        f"CLI_{code}: output_visibility={effects.visibility}; "
        f"sync_completed={effects.sync}; "
        f"cancel_requested={str(effects.cancelled).lower()}{suffix}"
    )


def _deliver(text: str, status: int, effects: _Effects, *, error: bool) -> int:
    stream = sys.stderr if error else sys.stdout
    try:
        _emit(stream, text)
    except _DeliveryFailed:
        if stream is not sys.stderr:
            try:
                _emit(sys.stderr, _cli("OUTPUT", effects) + "\n")
            except _DeliveryFailed:
                return 1
        return 1
    return status


def _help(context: Context, parameter: Parameter, value: Any) -> None:
    if value and not context.resilient_parsing:
        text = context.get_help()
        _emit(sys.stdout, text if text.endswith("\n") else text + "\n")
        raise typer.Exit(0)


class _PlainCommand(TyperCommand):
    def get_help_option(self, ctx: Context) -> TyperOption | None:
        option = super().get_help_option(ctx)
        if option is not None:
            option.callback = _help
        return option


class _CLIGroup(TyperGroup):
    def get_help_option(self, ctx: Context) -> TyperOption | None:
        option = super().get_help_option(ctx)
        if option is not None:
            option.callback = _help
        return option

    def main(
        self,
        args: Sequence[str] | None = None,
        prog_name: str | None = None,
        complete_var: str | None = None,
        standalone_mode: bool = True,
        windows_expand_args: bool = True,
        **extra: Any,
    ) -> Any:
        # Use framework parsing/context/invocation; own safe error presentation.
        os_arguments = args is None
        selected_args = list(sys.argv[1:] if args is None else args)
        status = 0
        try:
            with self.make_context(
                prog_name or "faultatlas", selected_args, **extra
            ) as context:
                context.meta["faultatlas.os_arguments"] = os_arguments
                self.invoke(context)
        except typer.Exit as exit_error:
            status = exit_error.exit_code
        except UsageError:
            status = _deliver(
                _cli("USAGE", _Effects()) + "\n", 2, _Effects(), error=True
            )
        except _DeliveryFailed as failure:
            status = 1
            if failure.stream is not sys.stderr:
                status = _deliver(
                    _cli("OUTPUT", _Effects()) + "\n", 1, _Effects(), error=True
                )
        except (Exception, KeyboardInterrupt):
            # Default pre-dispatch interrupts have no cooperative signal sample.
            effects = _Effects("uncertain", "unestablished")
            status = _deliver(_cli("INTERNAL", effects) + "\n", 1, effects, error=True)
        if standalone_mode:
            raise SystemExit(status)
        return status


app = typer.Typer(
    cls=_CLIGroup,
    add_completion=False,
    help="Inspect the FaultAtlas foundation.",
    no_args_is_help=False,
    rich_markup_mode=None,
    pretty_exceptions_enable=False,
    pretty_exceptions_show_locals=False,
)
assessment = typer.Typer(
    cls=_CLIGroup, add_completion=False, no_args_is_help=False, rich_markup_mode=None
)
app.add_typer(
    assessment, name="assessment", help="Inspect and save selected assessment files."
)


def _version_callback(value: bool) -> None:
    if value:
        _emit(sys.stdout, __version__ + "\n")
        raise typer.Exit(0)


@app.callback(invoke_without_command=True)
def main(
    context: typer.Context,
    version_option: Annotated[
        bool,
        typer.Option(
            "--version",
            callback=_version_callback,
            help="Show the installed version and exit.",
            is_eager=True,
        ),
    ] = False,
) -> None:
    """Run the FaultAtlas command-line interface."""
    if context.invoked_subcommand is None and not version_option:
        text = context.get_help()
        _emit(sys.stdout, text if text.endswith("\n") else text + "\n")


def _assessment_help(context: typer.Context) -> None:
    if context.invoked_subcommand is None:
        text = context.get_help()
        _emit(sys.stdout, text if text.endswith("\n") else text + "\n")


def _selected(value: str, context: typer.Context) -> str:
    if context.find_root().meta.get("faultatlas.os_arguments", False):
        return os.fsencode(value).decode("utf-8")
    return value


def _run_assessment(
    context: typer.Context, input_path: str, output_path: str | None = None
) -> None:
    effects = _Effects()
    try:
        input_path = _selected(input_path, context)
        if output_path is not None:
            output_path = _selected(output_path, context)
    except UnicodeError:
        raise typer.Exit(
            _deliver(_cli("ARGUMENT_ENCODING", effects) + "\n", 2, effects, error=True)
        ) from None
    observed: int | None = None
    installed: list[tuple[signal.Signals, Any]] = []
    service_error: AssessmentFileError | None = None
    message = ""
    status = 0
    restore_failed = False

    def latch(signum: int, frame: FrameType | None) -> None:
        nonlocal observed
        if observed is None:
            observed = signum

    def cancelled() -> bool:
        return observed is not None

    try:
        try:
            if threading.current_thread() is not threading.main_thread():
                raise ValueError("signal setup requires the main thread")
            previous = [
                (sig, signal.getsignal(sig)) for sig in (signal.SIGINT, signal.SIGTERM)
            ]
            for sig, handler in previous:
                signal.signal(sig, latch)
                installed.append((sig, handler))
        except Exception:
            message, status = _cli("SIGNAL_SETUP", effects), 1
        else:
            effects.visibility, effects.sync = "uncertain", "unestablished"
            try:
                if output_path is None:
                    result = inspect_assessment_file(input_path, cancelled=cancelled)
                    if not isinstance(cast(object, result), str):
                        raise TypeError("unexpected inspection return")
                    effects.visibility, effects.sync = "not_published", "false"
                    message = result if result.endswith("\n") else result + "\n"
                else:
                    result = save_assessment_as_new(
                        input_path, output_path, cancelled=cancelled
                    )
                    if (
                        not isinstance(cast(object, result), str)
                        or result != output_path
                    ):
                        raise TypeError("unexpected save return")
                    effects.visibility, effects.sync = "published", "true"
                    quoted = json.dumps(output_path, ensure_ascii=True).replace(
                        "\x7f", "\\u007f"
                    )
                    message = f"Saved new assessment file: {quoted}\noutput_visibility=published; sync_completed=true\n"
            except AssessmentFileError as error:
                service_error = error
                effects.visibility = error.output_visibility
                effects.sync = str(error.sync_completed).lower()
                effects.cancelled = error.cancel_requested
                message, status = str(error), 1
            except Exception:
                message, status = _cli("INTERNAL", effects), 1
    finally:
        # Final observation cutoff precedes response selection and restoration.
        cutoff = observed
        for sig, handler in reversed(installed):
            try:
                signal.signal(sig, handler)
            except Exception:
                restore_failed = True

    annotations: list[str] = []
    if cutoff is not None:
        effects.cancelled = True
        if status == 0:
            message = _cli("CANCELLED", effects, signum=cutoff)
            status = 128 + cutoff
        elif service_error is not None:
            if service_error.code == "CANCELLED":
                status = 128 + cutoff
            if not service_error.cancel_requested:
                annotations.append(_cli("CANCELLED", effects, signum=cutoff))
        else:
            annotations.append(_cli("CANCELLED", effects, signum=cutoff))
    if restore_failed:
        if status == 0:
            message = _cli("SIGNAL_RESTORE", effects)
        else:
            annotations.append(_cli("SIGNAL_RESTORE", effects))
        status = 1
    if annotations:
        message = message + "\n" + "\n".join(annotations)
    if not message.endswith("\n"):
        message += "\n"
    raise typer.Exit(_deliver(message, status, effects, error=status != 0))


def _inspect(
    context: typer.Context, input_path: Annotated[str, typer.Argument(metavar="INPUT")]
) -> None:
    """Inspect one explicitly selected assessment file."""
    _run_assessment(context, input_path)


def _save_as(
    context: typer.Context,
    input_path: Annotated[str, typer.Argument(metavar="INPUT")],
    output_path: Annotated[str, typer.Argument(metavar="OUTPUT")],
) -> None:
    """Save canonical assessment bytes under one selected new name."""
    _run_assessment(context, input_path, output_path)


assessment.callback(invoke_without_command=True)(_assessment_help)
assessment.command("inspect", cls=_PlainCommand)(_inspect)
assessment.command("save-as", cls=_PlainCommand)(_save_as)
