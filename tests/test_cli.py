import re
import subprocess
import sys
from importlib.metadata import version

from typer.testing import CliRunner

from faultatlas.cli import app

runner = CliRunner()


def _run_module(*arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "faultatlas", *arguments],
        check=False,
        capture_output=True,
        text=True,
    )


def test_cli_help() -> None:
    result = runner.invoke(app, ["--help"])
    plain_output = re.sub(
        r"\x1b\[[0-?]*[ -/]*[@-~]",
        "",
        result.output,
    )

    assert result.exit_code == 0
    assert "Usage:" in plain_output
    assert "--version" in plain_output


def test_cli_version() -> None:
    result = runner.invoke(app, ["--version"])

    assert result.exit_code == 0
    assert result.output == f"{version('faultatlas')}\n"


def test_module_without_arguments_shows_help() -> None:
    result = _run_module()

    assert result.returncode == 0, result.stderr
    assert "Usage:" in result.stdout


def test_module_help() -> None:
    result = _run_module("--help")

    assert result.returncode == 0, result.stderr
    assert "Usage:" in result.stdout
