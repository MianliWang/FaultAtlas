import ast
import re
import subprocess
import sys
from importlib.metadata import version
from pathlib import Path

import pytest
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


def assert_current_cli_source(raw: bytes) -> None:
    """Current CLI accountability; historical seed records remain with their owners."""
    tree = ast.parse(raw)
    owners = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
        and node.module == "faultatlas.assessment_file"
    ]
    assert len(owners) == 1 and {alias.name for alias in owners[0].names} == {
        "AssessmentFileError",
        "inspect_assessment_file",
        "save_assessment_as_new",
    }, "current CLI public S02 imports"
    assert not any(
        isinstance(node, ast.ImportFrom)
        and (node.module or "").startswith("faultatlas.domain")
        for node in ast.walk(tree)
    ), "current CLI domain independence"
    routes = [
        node.args[0].value
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "assessment"
        and node.func.attr == "command"
        and node.args
        and isinstance(node.args[0], ast.Constant)
    ]
    assert routes == ["inspect", "save-as"], "current CLI assessment routes"
    calls = [
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    ]
    assert (
        calls.count("inspect_assessment_file")
        == calls.count("save_assessment_as_new")
        == 1
    ), "current CLI single service calls"


def test_current_cli_source_contract() -> None:
    assert_current_cli_source(
        (Path(__file__).parents[1] / "src/faultatlas/cli.py").read_bytes()
    )


@pytest.mark.parametrize(
    "before,after,message",
    [
        (b'command("save-as"', b'command("overwrite"', "routes"),
        (b"    inspect_assessment_file,", b"    _codec,", "imports"),
    ],
)
def test_current_cli_source_rejects_wrong_routes_and_owner_imports(
    before: bytes, after: bytes, message: str
) -> None:
    raw = (Path(__file__).parents[1] / "src/faultatlas/cli.py").read_bytes()
    assert before in raw
    with pytest.raises(AssertionError, match=message):
        assert_current_cli_source(raw.replace(before, after))
