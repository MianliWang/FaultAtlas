"""Lazy, process-local preparation for the unchanged normal build profile."""

from __future__ import annotations

import hashlib
import os
import shutil
import stat
import subprocess
from collections.abc import Iterator
from pathlib import Path

import pytest

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
type FileSnapshot = tuple[tuple[str, int, bytes], ...]
type BuildProfile = tuple[Path, FileSnapshot, tuple[tuple[str, str], ...]]
type Distributions = tuple[Path, Path]
type PreparedBuild = tuple[BuildProfile, Distributions, tuple[bytes, bytes]]


def _build_environment(cache: Path) -> dict[str, str]:
    environment = os.environ.copy()
    environment.update(
        UV_CACHE_DIR=str(cache),
        UV_OFFLINE="1",
        UV_NO_SYNC="1",
        UV_PYTHON_DOWNLOADS="never",
        PYTHONDONTWRITEBYTECODE="1",
    )
    return environment


def _file_snapshot(root: Path, paths: Iterator[Path]) -> FileSnapshot:
    return tuple(
        sorted(
            (
                path.relative_to(root).as_posix(),
                stat.S_IMODE(path.lstat().st_mode),
                os.readlink(path).encode() if path.is_symlink() else path.read_bytes(),
            )
            for path in paths
            if path.is_file() or path.is_symlink()
        )
    )


def _build_profile(root: Path, cache: Path) -> BuildProfile:
    inputs = [
        root / name
        for name in (
            "pyproject.toml",
            "uv.lock",
            "README.md",
            "LICENSE",
            ".python-version",
        )
    ]
    inputs.extend((root / "src").rglob("*"))
    assert not any(path.is_symlink() for path in inputs), (
        "symlink build input requires an isolated profile"
    )
    environment = _build_environment(cache)
    # pytest's current-test label is not a build input; toolchain/path settings are.
    relevant = tuple(
        sorted(
            (key, value)
            for key, value in environment.items()
            if key != "PYTEST_CURRENT_TEST"
        )
    )
    return root.resolve(), _file_snapshot(root, iter(inputs)), relevant


def _repository_snapshot(root: Path) -> FileSnapshot:
    return _file_snapshot(
        root,
        (
            path
            for path in root.rglob("*")
            if path.relative_to(root).parts[0] not in {".git", ".venv"}
        ),
    )


def build_distributions(root: Path, output: Path) -> PreparedBuild:
    uv = shutil.which("uv")
    assert uv is not None, "uv must be available for the supported offline build"
    cache = output / "cache"
    profile = _build_profile(root, cache)
    before = _repository_snapshot(root)
    status = subprocess.check_output(
        ["git", "status", "--porcelain=v1", "-z", "--untracked-files=all"], cwd=root
    )
    result = subprocess.run(
        [uv, "build", "--offline", "--no-create-gitignore", "--out-dir", str(output)],
        cwd=root,
        env=_build_environment(cache),
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, (
        f"offline uv build failed\n{result.stdout}\n{result.stderr}"
    )
    assert _repository_snapshot(root) == before, (
        "offline build changed repository files"
    )
    assert (
        subprocess.check_output(
            ["git", "status", "--porcelain=v1", "-z", "--untracked-files=all"], cwd=root
        )
        == status
    ), "offline build changed repository status"
    assert _build_profile(root, cache) == profile, (
        "build inputs changed during preparation"
    )
    wheels, sdists = tuple(output.glob("*.whl")), tuple(output.glob("*.tar.gz"))
    assert len(wheels) == len(sdists) == 1, "expected exactly one wheel and one sdist"
    archives = wheels[0], sdists[0]
    digests = (
        hashlib.sha256(archives[0].read_bytes()).digest(),
        hashlib.sha256(archives[1].read_bytes()).digest(),
    )
    return profile, archives, digests


def checked_distributions(prepared: PreparedBuild, root: Path) -> Distributions:
    profile, archives, digests = prepared
    assert _build_profile(root, archives[0].parent / "cache") == profile, (
        "shared build inputs changed"
    )
    assert (
        tuple(hashlib.sha256(path.read_bytes()).digest() for path in archives)
        == digests
    ), "shared build artifact changed; mutate a private copy"
    return archives


@pytest.fixture(scope="session")
def normal_distributions(tmp_path_factory: pytest.TempPathFactory) -> PreparedBuild:
    return build_distributions(
        REPOSITORY_ROOT, tmp_path_factory.mktemp("offline-distributions")
    )


@pytest.fixture
def offline_distributions(normal_distributions: PreparedBuild) -> Distributions:
    """Rebind bytes and environment for each consumer; failures are never cached as success."""
    return checked_distributions(normal_distributions, REPOSITORY_ROOT)
