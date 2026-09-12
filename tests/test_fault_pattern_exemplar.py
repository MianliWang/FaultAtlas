"""Synthetic S02 designation, owning-schema delegation, and package witnesses."""

from __future__ import annotations

import ast
import hashlib
import json
import os
import subprocess
import sys
import tarfile
import uuid
import zipfile
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from pydantic import BaseModel, ValidationError

import faultatlas.domain.pattern_exemplar as exemplar_module
from faultatlas.domain.fault import (
    FaultInstanceIdentity,
    FaultOccurrenceIdentity,
    FaultReportIdentity,
    FaultRepositoryContext,
    FaultScenarioIdentity,
    SuppliedFaultOccurrenceContext,
    SuppliedFaultReport,
    SuppliedFaultScenario,
)
from faultatlas.domain.fault_instance import FaultInstance
from faultatlas.domain.fault_interpretation import (
    FaultExpectedPropertyIdentity,
    FaultHypothesisIdentity,
    SuppliedFaultExpectedProperty,
    SuppliedFaultHypothesis,
)
from faultatlas.domain.fault_test import (
    FaultTestMaterialIdentity,
    FaultTestRunIdentity,
    ReportedFaultTestOutcome,
    ReportedFaultTestOutcomeKind,
    ReportedFaultTestRun,
    SuppliedFaultTestMaterial,
)
from faultatlas.domain.identity import (
    ProviderKey,
    ProviderRepositoryId,
    RepositoryIdentity,
)
from faultatlas.domain.pattern import FaultPatternIdentity, SuppliedFaultPattern
from faultatlas.domain.pattern_exemplar import FaultPatternExemplarAssociation

ROOT = Path(__file__).resolve().parents[1]
MODULE = "src/faultatlas/domain/pattern_exemplar.py"
# Added by S03; BASELINE_PRODUCTION remains the immutable S01 observation.
INVARIANT_MODULE = "src/faultatlas/domain/invariant.py"
# Added by `S1.P07.S04`; immutable baseline inventories are unchanged.
INVARIANT_RELATIONSHIP_MODULE = "src/faultatlas/domain/invariant_relationship.py"
PATTERN_COMPOSITION_MODULE = "src/faultatlas/domain/pattern_composition.py"
FIELDS = ("pattern", "fault_instance")
# Every UUID, repository identifier and statement in this file is synthetic.
STATEMENT = "A supplied  重复 callback\nmay be observed."


def _pattern(text: str = STATEMENT, identifier: int = 1) -> SuppliedFaultPattern:
    return SuppliedFaultPattern(
        pattern=FaultPatternIdentity(uuid.UUID(int=identifier)), pattern_statement=text
    )


def _case(repository: str = "synthetic-a", fault: int = 10) -> FaultInstance:
    identity = FaultInstanceIdentity(uuid.UUID(int=fault))
    report = SuppliedFaultReport(
        report=FaultReportIdentity(uuid.UUID(int=11)),
        context=FaultRepositoryContext(
            fault=identity,
            repository=RepositoryIdentity(
                provider=ProviderKey("github"),
                provider_repository_id=ProviderRepositoryId(repository),
            ),
        ),
        problem_statement="The caller describes a callback problem.",
        behavioral_deviation="The caller reports two invocations.",
    )
    return FaultInstance(fault=identity, reports=(report,))


def _fields(value: BaseModel) -> dict[str, Any]:
    return {name: getattr(value, name) for name in type(value).model_fields}


def _populated() -> FaultInstance:
    case = _case()
    report = case.reports[0]
    second = _case("synthetic-b").reports[0]
    second = SuppliedFaultReport.model_validate(
        _fields(second) | {"report": FaultReportIdentity(uuid.UUID(int=12))}
    )
    scenario = SuppliedFaultScenario(
        scenario=FaultScenarioIdentity(uuid.UUID(int=20)),
        report=report,
        scenario_statement="The caller supplies a warmed cache context.",
    )
    material = SuppliedFaultTestMaterial(
        material=FaultTestMaterialIdentity(uuid.UUID(int=30)),
        report=report,
        test_statement="A caller-supplied callback count assertion.",
    )
    run = ReportedFaultTestRun(
        run=FaultTestRunIdentity(uuid.UUID(int=31)),
        test_material=material,
        run_statement="Caller-reported execution; no test is executed here.",
    )
    return FaultInstance(
        fault=case.fault,
        reports=(second, report),
        scenarios=(scenario,),
        occurrences=(
            SuppliedFaultOccurrenceContext(
                occurrence=FaultOccurrenceIdentity(uuid.UUID(int=21)),
                scenario=scenario,
                occurrence_context="A caller-reported occurrence.",
            ),
        ),
        test_materials=(material,),
        test_runs=(run,),
        test_outcomes=tuple(
            ReportedFaultTestOutcome(
                run=run,
                outcome=kind,
                outcome_statement="A conflicting supplied outcome.",
            )
            for kind in (
                ReportedFaultTestOutcomeKind.PASSED,
                ReportedFaultTestOutcomeKind.FAILED,
            )
        ),
        hypotheses=tuple(
            SuppliedFaultHypothesis(
                hypothesis=FaultHypothesisIdentity(uuid.UUID(int=identifier)),
                report=report,
                hypothesis_statement=statement,
            )
            for identifier, statement in (
                (42, "The cache causes the duplication."),
                (41, "The cache does not cause the duplication."),
            )
        ),
        expected_properties=(
            SuppliedFaultExpectedProperty(
                expected_property=FaultExpectedPropertyIdentity(uuid.UUID(int=50)),
                report=report,
                expected_property_statement="One callback invocation for this report.",
            ),
        ),
    )


def _link() -> FaultPatternExemplarAssociation:
    return FaultPatternExemplarAssociation(pattern=_pattern(), fault_instance=_case())


def _errors(error: ValidationError) -> list[tuple[tuple[str | int, ...], str]]:
    return [(item["loc"], item["type"]) for item in error.errors()]


def test_exact_surface_and_configuration() -> None:
    assert exemplar_module.__all__ == ["FaultPatternExemplarAssociation"]
    assert tuple(FaultPatternExemplarAssociation.model_fields) == FIELDS
    assert [
        f.annotation for f in FaultPatternExemplarAssociation.model_fields.values()
    ] == [
        SuppliedFaultPattern,
        FaultInstance,
    ]
    assert all(
        f.is_required() for f in FaultPatternExemplarAssociation.model_fields.values()
    )
    assert dict(FaultPatternExemplarAssociation.model_config) == {
        "frozen": True,
        "extra": "forbid",
        "strict": True,
        "revalidate_instances": "always",
        "validate_default": True,
    }
    assert FaultPatternExemplarAssociation.model_computed_fields == {}
    assert not FaultPatternExemplarAssociation.__private_attributes__
    assert {
        n for n in dir(FaultPatternExemplarAssociation) if not n.startswith("_")
    } <= set(dir(BaseModel))
    assert not {"__eq__", "__hash__"}.intersection(
        node.name
        for node in ast.walk(ast.parse((ROOT / MODULE).read_bytes()))
        if isinstance(node, ast.FunctionDef)
    )


def test_minimal_designation_preserves_input_without_fabricating_claims() -> None:
    pattern, case = _pattern(), _case()
    before = (pattern.model_dump_json(), case.model_dump_json())
    link = FaultPatternExemplarAssociation(pattern=pattern, fault_instance=case)
    assert link.pattern == pattern and link.fault_instance == case
    assert (pattern.model_dump_json(), case.model_dump_json()) == before
    assert list(json.loads(link.model_dump_json())) == list(FIELDS)
    assert all(
        getattr(link.fault_instance, name) == ()
        for name in FaultInstance.model_fields
        if name not in ("fault", "reports")
    )
    assert tuple(SuppliedFaultPattern.model_fields) == ("pattern", "pattern_statement")
    assert (
        SuppliedFaultPattern.model_validate_json(pattern.model_dump_json()) == pattern
    )
    assert (
        FaultPatternExemplarAssociation.model_validate_json(link.model_dump_json())
        == link
    )
    assert FaultPatternExemplarAssociation.model_validate(link) == link
    assert FaultPatternExemplarAssociation.model_validate(_fields(link)) == link


@pytest.mark.parametrize("field", FIELDS)
def test_missing_endpoint_is_not_completed(field: str) -> None:
    values = _fields(_link())
    del values[field]
    with pytest.raises(ValidationError) as failure:
        FaultPatternExemplarAssociation.model_validate(values)
    assert _errors(failure.value) == [((field,), "missing")]


@pytest.mark.parametrize("field", FIELDS)
@pytest.mark.parametrize(
    "kind",
    [
        "none",
        "uuid",
        "identity",
        "string",
        "mapping",
        "typed_mapping",
        "lookalike",
        "foreign",
        "swapped",
        "subrecord",
    ],
)
def test_python_endpoint_requires_declared_record(field: str, kind: str) -> None:
    pattern, case = _pattern(), _case()
    endpoint = pattern if field == "pattern" else case

    class Foreign(BaseModel):
        pattern: SuppliedFaultPattern
        fault_instance: FaultInstance

    invalid: dict[str, object] = {
        "none": None,
        "uuid": uuid.UUID(int=1),
        "identity": pattern.pattern if field == "pattern" else case.fault,
        "string": "caller supplied",
        "mapping": endpoint.model_dump(),
        "typed_mapping": _fields(endpoint),
        "lookalike": SimpleNamespace(**_fields(endpoint)),
        "foreign": Foreign(pattern=pattern, fault_instance=case),
        "swapped": case if field == "pattern" else pattern,
        "subrecord": case.reports[0],
    }
    values: dict[str, Any] = {
        "pattern": pattern,
        "fault_instance": case,
        field: invalid[kind],
    }
    for attributes in (False, True):
        with pytest.raises(ValidationError) as failure:
            FaultPatternExemplarAssociation.model_validate(
                values, from_attributes=attributes
            )
        assert _errors(failure.value) == [((field,), "value_error")]
    with pytest.raises(ValidationError) as failure:
        FaultPatternExemplarAssociation(**values)
    assert _errors(failure.value) == [((field,), "value_error")]


def test_python_projection_is_not_the_json_language() -> None:
    link = _link()
    for projected in (link.model_dump(), json.loads(link.model_dump_json())):
        with pytest.raises(ValidationError) as failure:
            FaultPatternExemplarAssociation.model_validate(projected)
        assert _errors(failure.value) == [((name,), "value_error") for name in FIELDS]


@pytest.mark.parametrize("field", FIELDS)
def test_frozen_fields(field: str) -> None:
    link = _link()
    with pytest.raises(ValidationError) as failure:
        setattr(link, field, getattr(link, field))
    assert _errors(failure.value) == [((field,), "frozen_instance")]


@pytest.mark.parametrize(
    "extra",
    [
        "rationale",
        "source",
        "evidence",
        "match",
        "polarity",
        "status",
        "score",
        "counterexample",
        "review",
        "confidence",
        "applicability",
        "invariant",
        "recurrence",
        "support",
        "transfer",
        "selected_subrecord",
    ],
)
def test_no_extra_or_inferred_surface(extra: str) -> None:
    link = _link()
    for mode in ("python", "json"):
        values = (
            _fields(link) if mode == "python" else json.loads(link.model_dump_json())
        )
        values[extra] = "a caller-supplied claim"
        with pytest.raises(ValidationError) as failure:
            if mode == "python":
                FaultPatternExemplarAssociation.model_validate(values)
            else:
                FaultPatternExemplarAssociation.model_validate_json(json.dumps(values))
        assert _errors(failure.value) == [((extra,), "extra_forbidden")]


def test_ordinary_subclasses_normalize_to_base_values() -> None:
    class PatternChild(SuppliedFaultPattern):
        pass

    class CaseChild(FaultInstance):
        pass

    link = FaultPatternExemplarAssociation(
        pattern=PatternChild(**_fields(_pattern())),
        fault_instance=CaseChild(**_fields(_case())),
    )
    assert type(link.pattern) is SuppliedFaultPattern
    assert type(link.fault_instance) is FaultInstance
    assert link == _link()


def test_currently_legal_constructed_children_are_revalidated_and_admitted() -> None:
    link = FaultPatternExemplarAssociation(
        pattern=SuppliedFaultPattern.model_construct(**_fields(_pattern())),
        fault_instance=FaultInstance.model_construct(**_fields(_case())),
    )
    assert link == _link()


@pytest.mark.parametrize(
    "field,child_field,invalid,category",
    [
        ("pattern", "pattern_statement", "", "string_too_short"),
        ("fault_instance", "reports", (), "too_short"),
    ],
)
@pytest.mark.parametrize("constructed", [False, True])
def test_invalid_children_fail_reentry(
    field: str, child_field: str, invalid: object, category: str, constructed: bool
) -> None:
    values = _fields(_link())
    child: BaseModel = values[field]
    if constructed:
        unchecked_fields = _fields(child)
        unchecked_fields[child_field] = invalid
        child = type(child).model_construct(**unchecked_fields)
    else:
        object.__setattr__(child, child_field, invalid)
    values[field] = child
    unchecked = FaultPatternExemplarAssociation.model_construct(**values)
    for candidate in (values, unchecked):
        with pytest.raises(ValidationError) as failure:
            FaultPatternExemplarAssociation.model_validate(candidate)
        assert _errors(failure.value) == [((field, child_field), category)]


def test_full_endpoint_values_determine_equality_and_many_to_many_designations() -> (
    None
):
    first = _link()
    equal = _link()
    assert first == equal and first is not equal
    assert hash(first) == hash(equal)
    altered_pattern = FaultPatternExemplarAssociation(
        pattern=_pattern("A different proposition."), fault_instance=_case()
    )
    altered_case = FaultPatternExemplarAssociation(
        pattern=_pattern(), fault_instance=_case("synthetic-b")
    )
    assert first.pattern.pattern == altered_pattern.pattern.pattern
    assert first.fault_instance.fault == altered_case.fault_instance.fault
    assert first != altered_pattern and first != altered_case
    # One proposition designates separate same-repository and other-repository cases.
    same_repo = FaultPatternExemplarAssociation(
        pattern=_pattern(), fault_instance=_case(fault=13)
    )
    assert same_repo.pattern == first.pattern == altered_case.pattern
    other_pattern = FaultPatternExemplarAssociation(
        pattern=_pattern(identifier=2), fault_instance=_case()
    )
    assert other_pattern.fault_instance == first.fault_instance
    assert other_pattern != first
    assert _link() == first  # No registration, uniqueness or deduplication side effect.


def test_populated_multirepository_json_preserves_conflicts_order_and_full_values() -> (
    None
):
    case = _populated()
    link = FaultPatternExemplarAssociation(pattern=_pattern(), fault_instance=case)
    restored = FaultPatternExemplarAssociation.model_validate_json(
        link.model_dump_json()
    )
    assert restored == link
    assert case.reports[0].context.repository != case.reports[1].context.repository
    collections = tuple(n for n in FaultInstance.model_fields if n != "fault")
    assert len(collections) == 16
    assert any(getattr(case, n) for n in collections)
    for name in collections:
        assert type(getattr(restored.fault_instance, name)) is tuple
        assert getattr(restored.fault_instance, name) == getattr(case, name)
    assert [h.hypothesis.root.int for h in restored.fault_instance.hypotheses] == [
        42,
        41,
    ]
    assert [o.outcome for o in restored.fault_instance.test_outcomes] == [
        ReportedFaultTestOutcomeKind.PASSED,
        ReportedFaultTestOutcomeKind.FAILED,
    ]
    reversed_case = FaultInstance.model_validate(
        _fields(case) | {"reports": tuple(reversed(case.reports))}
    )
    assert (
        FaultPatternExemplarAssociation(
            pattern=_pattern(), fault_instance=reversed_case
        )
        != link
    )
    # Two supplied designations retain conflicting interpretations, creating no claim.
    second = FaultPatternExemplarAssociation(
        pattern=link.pattern, fault_instance=_case(fault=14)
    )
    assert second.pattern == link.pattern
    assert set(second.model_dump()) == set(link.model_dump()) == set(FIELDS)


@pytest.mark.parametrize(
    "corruption", ["duplicate", "same_id_different_record", "bound"]
)
def test_json_delegation_preserves_owner_errors(corruption: str) -> None:
    payload = json.loads(_populated().model_dump_json())
    if corruption == "duplicate":
        payload["reports"].append(payload["reports"][0])
    elif corruption == "same_id_different_record":
        payload["scenarios"][0]["report"]["problem_statement"] = (
            "Different supplied content."
        )
    else:
        payload["reports"] = [payload["reports"][0]] * 4097
    with pytest.raises(ValidationError) as owner:
        FaultInstance.model_validate_json(json.dumps(payload))
    expected = (
        [((), "value_error")] if corruption != "bound" else [(("reports",), "too_long")]
    )
    assert _errors(owner.value) == expected
    wire = {
        "pattern": json.loads(_pattern().model_dump_json()),
        "fault_instance": payload,
    }
    with pytest.raises(ValidationError) as outer:
        FaultPatternExemplarAssociation.model_validate_json(json.dumps(wire))
    assert _errors(outer.value) == [
        (("fault_instance", *loc), kind) for loc, kind in expected
    ]
    assert [e["msg"] for e in outer.value.errors()] == [
        e["msg"] for e in owner.value.errors()
    ]


def test_direct_dependencies_and_no_predecessor_or_package_reexport() -> None:
    tree = ast.parse((ROOT / MODULE).read_bytes())
    imports = {
        n.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for n in node.names
    }
    from_imports = {
        node.module: {n.name for n in node.names}
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
    }
    assert imports == {"json"}
    assert from_imports == {
        "pydantic": {"BaseModel", "ConfigDict", "ValidationInfo", "field_validator"},
        "faultatlas.domain.pattern": {"SuppliedFaultPattern"},
        "faultatlas.domain.fault_instance": {"FaultInstance"},
    }
    assert all(
        node.level == 0 for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)
    )
    for relative, digest in BASELINE_PRODUCTION.items():
        source = (ROOT / relative).read_bytes()
        assert hashlib.sha256(source).hexdigest() == digest, relative
        assert b"pattern_exemplar" not in source, relative
        assert b"FaultPatternExemplarAssociation" not in source, relative


def test_value_entry_points_perform_no_io(monkeypatch: pytest.MonkeyPatch) -> None:
    import builtins
    import socket
    import time

    link = FaultPatternExemplarAssociation(
        pattern=_pattern(), fault_instance=_populated()
    )
    wire = link.model_dump_json()

    def denied(*args: object, **kwargs: object) -> Any:
        raise AssertionError("value validation attempted an external operation")

    with monkeypatch.context() as blocked:
        for owner, name in (
            (builtins, "open"),
            (Path, "open"),
            (socket, "socket"),
            (subprocess, "Popen"),
            (os, "getenv"),
            (os, "stat"),
            (time, "time"),
            (time, "monotonic"),
            (uuid, "uuid4"),
        ):
            blocked.setattr(owner, name, denied)
        assert FaultPatternExemplarAssociation.model_validate(link) == link
        assert FaultPatternExemplarAssociation.model_validate_json(wire) == link
        assert FaultPatternExemplarAssociation(**_fields(link)) == link
        with pytest.raises(ValidationError):
            FaultPatternExemplarAssociation.model_validate(link.model_dump())


def test_bounded_roadmap_section_states_designation_and_live_gate() -> None:
    text = (ROOT / "docs/roadmap.md").read_text()
    section = (
        text.split("### S1.P07.S02 — Supplied pattern-exemplar designation\n", 1)[1]
        .split("\n### ", 1)[0]
        .split("\nThe `S1.P07` route", 1)[0]
    )
    assert "FaultPatternExemplarAssociation" in section
    assert "SuppliedFaultPattern" in section and "FaultInstance" in section
    for phrase in (
        "full endpoint values",
        "no automatic recurrence",
        "no nested claim is promoted",
        "own JSON validator",
        "same-repository",
        "cross-repository",
    ):
        assert phrase in section, phrase
    current = " ".join(
        text.split("## Current status\n", 1)[1].split("\n## ", 1)[0].split()
    )
    for phrase in (
        "`S1.P06` is complete",
        "`S1.P07` is active and incomplete",
        "`S1.P07.S01` is complete",
        "`S1.P07.S02` is complete",
        "`S1.P07.S06` is next and not started",
        "`S1.P08` through `S1.P10` remain not started",
    ):
        assert phrase in current, phrase


@pytest.fixture(scope="module")
def distributions(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, Path]:
    output = tmp_path_factory.mktemp("pattern-exemplar-dist")
    env = os.environ | {
        "UV_OFFLINE": "1",
        "UV_NO_SYNC": "1",
        "UV_CACHE_DIR": str(output / "cache"),
        "PYTHONDONTWRITEBYTECODE": "1",
    }
    result = subprocess.run(
        ["uv", "build", "--offline", "--no-create-gitignore", "--out-dir", str(output)],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return next(output.glob("*.whl")), next(output.glob("*.tar.gz"))


def test_tracked_checkout_wheel_and_sdist_are_exact(
    distributions: tuple[Path, Path],
) -> None:
    expected = sorted(
        [
            *BASELINE_PRODUCTION,
            MODULE,
            INVARIANT_MODULE,
            INVARIANT_RELATIONSHIP_MODULE,
            PATTERN_COMPOSITION_MODULE,
        ]
    )
    assert len(expected) == 25
    result = subprocess.run(
        ["git", "ls-files", "src/"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert sorted(result.stdout.splitlines()) == expected
    assert (
        sorted(p.relative_to(ROOT).as_posix() for p in (ROOT / "src").rglob("*.py"))
        == expected
    )
    wheel, sdist = distributions
    with zipfile.ZipFile(wheel) as archive:
        names = [i.filename for i in archive.infolist() if not i.is_dir()]
        assert sorted("src/" + n for n in names if n.endswith(".py")) == expected
        for relative in expected:
            assert (
                archive.read(relative.removeprefix("src/"))
                == (ROOT / relative).read_bytes()
            )
    with tarfile.open(sdist) as archive:
        members = [m for m in archive.getmembers() if m.isfile()]
        assert (
            sorted(m.name.split("/", 1)[1] for m in members if m.name.endswith(".py"))
            == expected
        )
        for member in members:
            if member.name.endswith(".py"):
                stream = archive.extractfile(member)
                assert stream is not None
                assert (
                    stream.read() == (ROOT / member.name.split("/", 1)[1]).read_bytes()
                )
        names.extend(m.name for m in members)
    assert names
    for name in names:
        assert not {"docs", "tests", "reference_corpus"}.intersection(
            Path(name).parts
        ), name


def test_installed_wheel_outside_checkout(
    distributions: tuple[Path, Path], tmp_path: Path
) -> None:
    wheel, _ = distributions
    installed = tmp_path / "installed"
    # Install the already-built local wheel only; owning dependencies stay locked.
    env = os.environ | {
        "UV_OFFLINE": "1",
        "UV_CACHE_DIR": str(tmp_path / "cache"),
        "PYTHONDONTWRITEBYTECODE": "1",
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
            str(wheel),
        ],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    script = """
import json, sys
from pathlib import Path
installed = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(installed))
import faultatlas.domain.pattern_exemplar as module
assert Path(module.__file__).resolve().is_relative_to(installed)
value = module.FaultPatternExemplarAssociation.model_validate_json(sys.argv[2])
assert value == module.FaultPatternExemplarAssociation.model_validate_json(value.model_dump_json())
print(json.dumps({"module": module.__file__, "value": value.model_dump(mode="json")}))
"""
    link = FaultPatternExemplarAssociation(
        pattern=_pattern(), fault_instance=_populated()
    )
    result = subprocess.run(
        [sys.executable, "-I", "-c", script, str(installed), link.model_dump_json()],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    receipt = json.loads(result.stdout)
    assert Path(receipt["module"]).is_relative_to(installed)
    assert not Path(receipt["module"]).is_relative_to(ROOT)
    assert receipt["value"] == json.loads(link.model_dump_json())


# Immutable production bytes observed at the accepted S01 squash f332d3b9.
BASELINE_PRODUCTION = {
    "src/faultatlas/__init__.py": "7f88816f33b0efc700b25bfb7ad171ef00a3e5875d358e258d8e3d755e4d8489",
    "src/faultatlas/__main__.py": "97a5e95d8d541e00eb0ceb84e73a28f28c3007643d80d3814945e04bedc41800",
    "src/faultatlas/cli.py": "31e7edfea6a699fd75a4503a91beaf564b7257a4b69422acd6d81bfad59fd824",
    "src/faultatlas/domain/__init__.py": "5cae5f36fe402a284ee13c9757b8b8415d2951711107890ce8c6c038fa8b05b5",
    "src/faultatlas/domain/compatibility.py": "f4ef93d432da4fd0ebf05237c164e10d8f18eceaf538ff4ddc3372565b5c46db",
    "src/faultatlas/domain/evidence.py": "824ed6ad86d243ccf920f07fe66af5d6bf060d6d80fafb7d60588dec8244e7ba",
    "src/faultatlas/domain/fault.py": "f8b8bed37aff51b8848c303f2fbffde4e5e365216b5f46755b043fad2d254e26",
    "src/faultatlas/domain/fault_evidence_link.py": "d8b0b0c59f48d0eb45285cde96f27d1640953b310c94b6e2a8ef20b5f142c1c1",
    "src/faultatlas/domain/fault_instance.py": "4d505c837ab261e65886464e950ae6417bf4bf09702ec0c45fac9f6924bc9b1d",
    "src/faultatlas/domain/fault_interpretation.py": "02ae3034a6ebfef54e1785b48a619dcdb56bd03354a01d1cde79d9f8e3e4ee54",
    "src/faultatlas/domain/fault_repair.py": "3256c64c2defc2635604fd5628cc9efbd94bb0c1b222a4994d29dd35ad6d0648",
    "src/faultatlas/domain/fault_source_relationship.py": "470bd4438e0b740e9955cd828f67a1d8ec5749a36be92301673375cae4285d31",
    "src/faultatlas/domain/fault_test.py": "9487cf11ecf7f11922f9ecd6a10945e7f929009e048131ec0609e3ee70aab3d0",
    "src/faultatlas/domain/history.py": "e72454294c448e4edeec0d7cc044c205d6e3852df9c2c244b5e21cb579e22990",
    "src/faultatlas/domain/history_evidence_link.py": "8b69bc47dc53ae754359877f3e50289530b745c69508b4144e8bcf39a6696c86",
    "src/faultatlas/domain/identity.py": "e2d604f4e86a3b94c2b1b1875fa6e8f408778cbadd829b3fe9e934dd53f2d169",
    "src/faultatlas/domain/pattern.py": "590a4f2dcc2473415cc6c77dc4ce714b2995e1e3db35ea1fbe16ef5fcdfda4e3",
    "src/faultatlas/domain/revision.py": "7bea28086b345f6c1b4eeebe9c483924e60521e2f3e78954b272ab3c42acacaa",
    "src/faultatlas/domain/snapshot.py": "3807eb6e1552bfd97c3bedd7ca6fe8bfe7351f0ff3bc8205afdbad69c7f3e5fd",
    "src/faultatlas/domain/snapshot_evidence_link.py": "a87b7ed338a74127bd490803a958316bbc2598989cbbf3b0534174bc2b9cd59d",
    "src/faultatlas/domain/source.py": "034e53fd58212f0e34376bbc790fc3e74057031aaed4d7d89fb67904bdd380bf",
}
