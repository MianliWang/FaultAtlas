from __future__ import annotations

import hashlib
import io
import os
import re
import shutil
import stat
import subprocess
import tarfile
import zipfile
from dataclasses import dataclass
from importlib.metadata import metadata, version
from pathlib import Path
from typing import Literal

import pytest

import faultatlas

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
PROJECT_LICENSE = REPOSITORY_ROOT / "LICENSE"
HISTORICAL_PYTEST_LICENSE = (
    REPOSITORY_ROOT
    / "reference_corpus"
    / "pytest-4412"
    / "acquisitions"
    / "run-0001-s04-v1-base-4c9cde74-head-690a63b9"
    / "artifacts"
    / "LICENSE"
)
PROJECT_LICENSE_SHA256 = (
    "c71d239df91726fc519c6eb72d318ec65820627232b2f796219e87dcf35d0ab4"
)
HISTORICAL_PYTEST_LICENSE_SHA256 = (
    "a1ebce15afc7b5cf98c7c6de512d1959d4bf61db8c6bf2f111286d483b40a997"
)
FORBIDDEN_CORPUS_PATH_COMPONENTS = frozenset(
    {
        "reference_corpus",
        "pytest-4412",
        "run-0001-s04-v1-base-4c9cde74-head-690a63b9",
        "s04-c01-acquisition-closure",
        "s06-current-contract-gap-matrix",
        "s07-identity-revision-provenance",
        "s08-snapshot-boundary-compatibility",
        "s08-deferred-subject-disposition",
        "repository-snapshot",
    }
)
CORPUS_DIRECTORY_NAMES = frozenset(
    {"acquisitions", "analysis", "artifacts", "case", "corrections", "decisions"}
)
CORPUS_ARTIFACT_NAMES = frozenset(
    {
        "acquisition.json",
        "acquisition.sha256",
        "base-to-head.diff",
        "case.json",
        "case.sha256",
        "correction.json",
        "correction.sha256",
        "decision.json",
        "decision.md",
        "decision.sha256",
        "gap-matrix.json",
        "gap-matrix.md",
        "gap-matrix.sha256",
        "regression-vectors.json",
        "regression-vectors.sha256",
    }
)
WINDOWS_DRIVE_PREFIX = re.compile(r"^[A-Za-z]:")
EXPECTED_PRODUCTION_FILES = {
    "src/faultatlas/__init__.py",
    "src/faultatlas/__main__.py",
    "src/faultatlas/cli.py",
    "src/faultatlas/domain/__init__.py",
    "src/faultatlas/domain/compatibility.py",
    "src/faultatlas/domain/evidence.py",
    "src/faultatlas/domain/identity.py",
    "src/faultatlas/domain/revision.py",
    "src/faultatlas/domain/snapshot.py",
    "src/faultatlas/domain/snapshot_evidence_link.py",
    "src/faultatlas/domain/source.py",
}
EVIDENCE_MODULE_PATH = "src/faultatlas/domain/evidence.py"
SNAPSHOT_MODULE_PATH = "src/faultatlas/domain/snapshot.py"

type ArchiveKind = Literal["wheel", "sdist"]
type MemberKind = Literal["file", "directory", "link", "special"]


@dataclass(frozen=True)
class ArchiveMember:
    name: str
    kind: MemberKind
    data: bytes | None = None


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _locked_license_bytes() -> tuple[bytes, bytes]:
    project_license = PROJECT_LICENSE.read_bytes()
    historical_license = HISTORICAL_PYTEST_LICENSE.read_bytes()
    assert _sha256(project_license) == PROJECT_LICENSE_SHA256
    assert _sha256(historical_license) == HISTORICAL_PYTEST_LICENSE_SHA256
    assert project_license != historical_license
    return project_license, historical_license


def _read_wheel(path: Path) -> tuple[ArchiveMember, ...]:
    members: list[ArchiveMember] = []
    with zipfile.ZipFile(path) as archive:
        for info in archive.infolist():
            mode = info.external_attr >> 16
            if stat.S_ISLNK(mode):
                members.append(ArchiveMember(info.filename, "link"))
            elif info.is_dir():
                members.append(ArchiveMember(info.filename, "directory"))
            else:
                members.append(ArchiveMember(info.filename, "file", archive.read(info)))
    return tuple(members)


def _read_sdist(path: Path) -> tuple[ArchiveMember, ...]:
    members: list[ArchiveMember] = []
    with tarfile.open(path, mode="r:gz") as archive:
        for info in archive.getmembers():
            if info.issym() or info.islnk():
                members.append(ArchiveMember(info.name, "link"))
            elif info.isdir():
                members.append(ArchiveMember(info.name, "directory"))
            elif info.isfile():
                stream = archive.extractfile(info)
                assert stream is not None
                members.append(ArchiveMember(info.name, "file", stream.read()))
            else:
                members.append(ArchiveMember(info.name, "special"))
    return tuple(members)


def _read_archive(path: Path, kind: ArchiveKind) -> tuple[ArchiveMember, ...]:
    if kind == "wheel":
        return _read_wheel(path)
    return _read_sdist(path)


def _archive_path_parts(member: ArchiveMember) -> tuple[str, ...]:
    name = member.name
    assert name, "unsafe archive member: empty path"
    assert "\x00" not in name, f"unsafe archive member: {name!r}"
    assert "\\" not in name, f"unsafe archive member: {name!r}"
    assert not name.startswith("/"), f"unsafe archive member: {name!r}"
    assert WINDOWS_DRIVE_PREFIX.match(name) is None, f"unsafe archive member: {name!r}"

    path_text = name[:-1] if member.kind == "directory" and name.endswith("/") else name
    parts = tuple(path_text.split("/"))
    assert all(part not in {"", ".", ".."} for part in parts), (
        f"unsafe archive member: {name!r}"
    )
    assert member.kind not in {"link", "special"}, (
        f"unsafe archive member type: {name!r}"
    )
    return parts


def _working_source_bytes() -> dict[str, bytes]:
    observed = {
        path.relative_to(REPOSITORY_ROOT).as_posix(): path.read_bytes()
        for path in (REPOSITORY_ROOT / "src").rglob("*.py")
    }
    assert set(observed) == EXPECTED_PRODUCTION_FILES
    return observed


def _archive_source_bytes(
    members: tuple[ArchiveMember, ...],
) -> dict[str, bytes]:
    observed: dict[str, bytes] = {}
    for member in members:
        if member.kind != "file" or not member.name.endswith(".py"):
            continue
        parts = _archive_path_parts(member)
        try:
            package_index = parts.index("faultatlas")
        except ValueError:
            relative = f"__unexpected_archive_python__/{member.name}"
        else:
            relative = "src/" + "/".join(parts[package_index:])
        assert relative not in observed
        assert member.data is not None
        observed[relative] = member.data
    return observed


def _assert_complete_source_package(
    packaged: dict[str, bytes], working: dict[str, bytes]
) -> None:
    assert set(working) == EXPECTED_PRODUCTION_FILES
    assert set(packaged) == EXPECTED_PRODUCTION_FILES
    assert len(working) == len(packaged) == len(EXPECTED_PRODUCTION_FILES)
    assert packaged[EVIDENCE_MODULE_PATH] == working[EVIDENCE_MODULE_PATH]
    assert packaged == working


def _assert_safe_package_archive(
    members: tuple[ArchiveMember, ...],
    *,
    project_license: bytes,
    historical_license: bytes,
    expect_sources: bool = False,
) -> None:
    packaged_project_licenses: list[bytes] = []
    assert members, "package archive is empty"

    for member in members:
        parts = _archive_path_parts(member)
        lowered_parts = {part.casefold() for part in parts}
        forbidden = lowered_parts & FORBIDDEN_CORPUS_PATH_COMPONENTS
        corpus_signature = parts[-1].casefold() in CORPUS_ARTIFACT_NAMES and bool(
            lowered_parts & CORPUS_DIRECTORY_NAMES
        )
        assert not forbidden, (
            f"reference corpus path packaged in {member.name!r}: {sorted(forbidden)!r}"
        )
        assert not corpus_signature, (
            f"reference corpus path packaged in {member.name!r}"
        )

        if member.kind != "file":
            continue
        assert member.data is not None
        assert member.data != historical_license, (
            f"historical pytest LICENSE packaged as {member.name!r}"
        )
        if parts[-1] == "LICENSE":
            packaged_project_licenses.append(member.data)

    assert packaged_project_licenses == [project_license], (
        "archive must contain exactly one byte-identical FaultAtlas project LICENSE"
    )
    if expect_sources:
        _assert_complete_source_package(
            _archive_source_bytes(members),
            _working_source_bytes(),
        )


def _git_status_snapshot() -> bytes | None:
    git = shutil.which("git")
    if git is None:
        return None
    result = subprocess.run(
        [git, "status", "--porcelain=v1", "-z", "--untracked-files=all"],
        cwd=REPOSITORY_ROOT,
        check=True,
        capture_output=True,
    )
    return result.stdout


def _repository_file_snapshot() -> tuple[tuple[str, int, str], ...]:
    snapshot: list[tuple[str, int, str]] = []
    for path in REPOSITORY_ROOT.rglob("*"):
        relative = path.relative_to(REPOSITORY_ROOT)
        if relative.parts[0] in {".git", ".venv"}:
            continue
        if path.is_symlink():
            payload = os.readlink(path).encode("utf-8")
        elif path.is_file():
            payload = path.read_bytes()
        else:
            continue
        snapshot.append(
            (relative.as_posix(), stat.S_IMODE(path.lstat().st_mode), _sha256(payload))
        )
    return tuple(sorted(snapshot))


def _write_synthetic_archive(
    tmp_path: Path,
    *,
    kind: ArchiveKind,
    extra_name: str,
    extra_data: bytes,
) -> Path:
    project_license, _ = _locked_license_bytes()
    if kind == "wheel":
        path = tmp_path / "synthetic.whl"
        with zipfile.ZipFile(path, mode="w") as archive:
            archive.writestr("synthetic.dist-info/licenses/LICENSE", project_license)
            archive.writestr(extra_name, extra_data)
        return path

    path = tmp_path / "synthetic.tar.gz"
    with tarfile.open(path, mode="w:gz") as archive:
        for name, data in (
            ("synthetic-0.0.0/LICENSE", project_license),
            (extra_name, extra_data),
        ):
            info = tarfile.TarInfo(name)
            info.size = len(data)
            info.mtime = 0
            archive.addfile(info, io.BytesIO(data))
    return path


def test_package_version_comes_from_distribution_metadata() -> None:
    assert faultatlas.__version__ == version("faultatlas")
    assert faultatlas.__version__ == "0.1.0"


def test_distribution_name_is_faultatlas() -> None:
    assert metadata("faultatlas")["Name"] == "faultatlas"


def test_offline_build_excludes_reference_corpus_and_historical_license(
    tmp_path: Path,
) -> None:
    uv = shutil.which("uv")
    assert uv is not None, "uv must be available to run the supported package build"

    project_license, historical_license = _locked_license_bytes()
    cache_dir = tmp_path / "uv-cache"
    output_dir = tmp_path / "distributions"
    cache_dir.mkdir()
    output_dir.mkdir()
    environment = os.environ.copy()
    environment.update(
        {
            "PYTHONDONTWRITEBYTECODE": "1",
            "UV_CACHE_DIR": str(cache_dir),
            "UV_OFFLINE": "1",
        }
    )
    status_before = _git_status_snapshot()
    files_before = _repository_file_snapshot()
    result = subprocess.run(
        [
            uv,
            "build",
            "--offline",
            "--no-create-gitignore",
            "--out-dir",
            str(output_dir),
        ],
        cwd=REPOSITORY_ROOT,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
    )
    status_after = _git_status_snapshot()
    files_after = _repository_file_snapshot()
    assert status_after == status_before, "offline build changed repository status"
    assert files_after == files_before, "offline build changed repository files"
    assert result.returncode == 0, (
        f"offline uv build failed\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )

    wheels = tuple(output_dir.glob("*.whl"))
    sdists = tuple(output_dir.glob("*.tar.gz"))
    assert len(wheels) == 1, f"expected one wheel, found {wheels!r}"
    assert len(sdists) == 1, f"expected one sdist, found {sdists!r}"
    archives: tuple[tuple[Path, ArchiveKind], ...] = (
        (wheels[0], "wheel"),
        (sdists[0], "sdist"),
    )
    for path, kind in archives:
        _assert_safe_package_archive(
            _read_archive(path, kind),
            project_license=project_license,
            historical_license=historical_license,
            expect_sources=True,
        )


@pytest.mark.parametrize(
    "mutation",
    (
        "unexpected-source",
        "missing-evidence-source",
        "missing-snapshot-source",
        "evidence-byte-mismatch",
    ),
)
def test_package_source_inventory_mutation_is_rejected(mutation: str) -> None:
    working = _working_source_bytes()
    packaged = dict(working)
    if mutation == "unexpected-source":
        packaged["src/faultatlas/domain/unexpected.py"] = b"pass\n"
    elif mutation == "missing-evidence-source":
        del packaged[EVIDENCE_MODULE_PATH]
    elif mutation == "missing-snapshot-source":
        del packaged[SNAPSHOT_MODULE_PATH]
    else:
        assert mutation == "evidence-byte-mismatch"
        packaged[EVIDENCE_MODULE_PATH] += b"\n"
    with pytest.raises(AssertionError):
        _assert_complete_source_package(packaged, working)


def test_archive_source_inventory_rejects_rogue_python_member() -> None:
    working = _working_source_bytes()
    members = tuple(
        ArchiveMember(relative.removeprefix("src/"), "file", data)
        for relative, data in working.items()
    ) + (ArchiveMember("unexpected.py", "file", b"pass\n"),)
    packaged = _archive_source_bytes(members)
    assert "__unexpected_archive_python__/unexpected.py" in packaged
    with pytest.raises(AssertionError):
        _assert_complete_source_package(packaged, working)


@pytest.mark.parametrize("kind", ("wheel", "sdist"))
@pytest.mark.parametrize(
    "extra_name",
    (
        "reference_corpus/pytest-4412/case/case.json",
        "reference_corpus/contracts/revision-locator/v1/manifest.json",
        "acquisitions/artifacts/acquisition.json",
        "corrections/correction.json",
        "case/case.json",
        "analysis/gap-matrix.json",
        "decisions/decision.json",
    ),
)
def test_package_archive_rejects_reference_corpus_member(
    tmp_path: Path,
    kind: ArchiveKind,
    extra_name: str,
) -> None:
    path = _write_synthetic_archive(
        tmp_path,
        kind=kind,
        extra_name=extra_name,
        extra_data=b"{}\n",
    )
    project_license, historical_license = _locked_license_bytes()
    with pytest.raises(AssertionError, match="reference corpus path packaged"):
        _assert_safe_package_archive(
            _read_archive(path, kind),
            project_license=project_license,
            historical_license=historical_license,
        )


@pytest.mark.parametrize("kind", ("wheel", "sdist"))
def test_package_archive_rejects_historical_pytest_license(
    tmp_path: Path,
    kind: ArchiveKind,
) -> None:
    project_license, historical_license = _locked_license_bytes()
    path = _write_synthetic_archive(
        tmp_path,
        kind=kind,
        extra_name="synthetic-0.0.0/COPYING.pytest",
        extra_data=historical_license,
    )
    with pytest.raises(AssertionError, match="historical pytest LICENSE packaged"):
        _assert_safe_package_archive(
            _read_archive(path, kind),
            project_license=project_license,
            historical_license=historical_license,
        )


@pytest.mark.parametrize("kind", ("wheel", "sdist"))
@pytest.mark.parametrize(
    "unsafe_name",
    (
        "../outside.txt",
        "/absolute.txt",
        "C:/drive.txt",
        "safe/../../outside.txt",
        "safe\\windows.txt",
    ),
)
def test_package_archive_rejects_unsafe_member_path(
    tmp_path: Path,
    kind: ArchiveKind,
    unsafe_name: str,
) -> None:
    path = _write_synthetic_archive(
        tmp_path,
        kind=kind,
        extra_name=unsafe_name,
        extra_data=b"unsafe",
    )
    project_license, historical_license = _locked_license_bytes()
    with pytest.raises(AssertionError, match="unsafe archive member"):
        _assert_safe_package_archive(
            _read_archive(path, kind),
            project_license=project_license,
            historical_license=historical_license,
        )
