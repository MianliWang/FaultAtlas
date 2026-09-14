"""Finite regression witnesses for E01's moved preparation and ownership."""

from __future__ import annotations

import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import Any, cast

import conftest as preparation
import pytest


def test_normal_build_is_reused(
    normal_distributions: preparation.PreparedBuild,
) -> None:
    first = preparation.checked_distributions(
        normal_distributions, preparation.REPOSITORY_ROOT
    )
    second = preparation.checked_distributions(
        normal_distributions, preparation.REPOSITORY_ROOT
    )
    assert first is second


@pytest.mark.parametrize("change", ("source", "configuration", "environment"))
def test_warmed_build_rejects_changed_inputs(
    normal_distributions: preparation.PreparedBuild,
    monkeypatch: pytest.MonkeyPatch,
    change: str,
) -> None:
    if change == "environment":
        monkeypatch.setenv("SOURCE_DATE_EPOCH", "1000000000")
    else:
        target = preparation.REPOSITORY_ROOT / (
            "src/faultatlas/__init__.py" if change == "source" else "pyproject.toml"
        )
        original = Path.read_bytes

        def changed(path: Path) -> bytes:
            value = original(path)
            return value + b"\n" if path == target else value

        monkeypatch.setattr(Path, "read_bytes", changed)
    with pytest.raises(AssertionError, match="shared build inputs changed"):
        preparation.checked_distributions(
            normal_distributions, preparation.REPOSITORY_ROOT
        )


def test_warmed_build_does_not_hide_a_failed_read(
    normal_distributions: preparation.PreparedBuild, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = preparation.REPOSITORY_ROOT / "README.md"
    original = Path.read_bytes

    def failed(path: Path) -> bytes:
        if path == target:
            raise OSError("injected build-input read failure")
        return original(path)

    monkeypatch.setattr(Path, "read_bytes", failed)
    with pytest.raises(OSError, match="injected build-input read failure"):
        preparation.checked_distributions(
            normal_distributions, preparation.REPOSITORY_ROOT
        )


def test_failed_preparation_propagates(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    original = subprocess.run
    attempts: list[object] = []

    def failed(args: Any, **kwargs: Any) -> Any:
        if args[1:2] == ["build"]:
            attempts.append(args)
            return subprocess.CompletedProcess(args, 42, "", "controlled build failure")
        return cast(subprocess.CompletedProcess[Any], original(args, **kwargs))

    monkeypatch.setattr(subprocess, "run", failed)
    with pytest.raises(AssertionError, match="offline uv build failed") as failure:
        preparation.build_distributions(preparation.REPOSITORY_ROOT, tmp_path)
    assert "controlled build failure" in str(failure.value)
    assert len(attempts) == 1
    assert not list(tmp_path.glob("*.whl"))


def test_mutated_shared_archive_is_rejected_and_restored(
    normal_distributions: preparation.PreparedBuild,
) -> None:
    archives = preparation.checked_distributions(
        normal_distributions, preparation.REPOSITORY_ROOT
    )
    wheel = archives[0]
    before = wheel.read_bytes()
    try:
        wheel.write_bytes(before + b"deliberate corruption")
        with pytest.raises(AssertionError, match="shared build artifact changed"):
            preparation.checked_distributions(
                normal_distributions, preparation.REPOSITORY_ROOT
            )
    finally:
        wheel.write_bytes(before)
    assert (
        preparation.checked_distributions(
            normal_distributions, preparation.REPOSITORY_ROOT
        )
        == archives
    )
    assert wheel.read_bytes() == before


def test_runtime_bytecode_does_not_change_source_build_profile(tmp_path: Path) -> None:
    build_profile: Callable[[Path, Path], preparation.BuildProfile] = getattr(
        preparation, "_build_profile"
    )
    source = tmp_path / "src" / "faultatlas"
    source.mkdir(parents=True)
    module = source / "example.py"
    module.write_text("value = 1\n")
    output_cache = tmp_path / "build-cache"
    before = build_profile(tmp_path, output_cache)
    bytecode = source / "__pycache__" / "example.cpython-313.pyc"
    bytecode.parent.mkdir()
    bytecode.write_bytes(b"synthetic bytecode, never executed")
    assert build_profile(tmp_path, output_cache) == before
    bytecode.write_bytes(b"changed synthetic bytecode")
    assert build_profile(tmp_path, output_cache) == before
    bytecode.unlink()
    assert build_profile(tmp_path, output_cache) == before
    module.write_text("value = 2\n")
    assert build_profile(tmp_path, output_cache) != before
    module.write_text("value = 1\n")
    (bytecode.parent / "unexpected.py").write_text("unexpected = True\n")
    assert build_profile(tmp_path, output_cache) != before
