"""Synthetic bounded-composition and explicit-reference contract witnesses."""

from __future__ import annotations

import ast
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

import faultatlas.domain.pattern_composition as module
from faultatlas.domain.fault import (
    FaultInstanceIdentity,
    FaultReportIdentity,
    FaultRepositoryContext,
    SuppliedFaultReport,
)
from faultatlas.domain.fault_instance import FaultInstance
from faultatlas.domain.fault_interpretation import (
    FaultExpectedPropertyIdentity,
    SuppliedFaultExpectedProperty,
)
from faultatlas.domain.identity import (
    ProviderKey,
    ProviderRepositoryId,
    RepositoryIdentity,
)
from faultatlas.domain.invariant import FaultInvariantIdentity, SuppliedFaultInvariant
from faultatlas.domain.invariant_relationship import (
    FaultInvariantExpectedPropertyAssociation,
    FaultPatternInvariantAssociation,
)
from faultatlas.domain.pattern import FaultPatternIdentity, SuppliedFaultPattern
from faultatlas.domain.pattern_composition import FaultPatternComposition
from faultatlas.domain.pattern_exemplar import FaultPatternExemplarAssociation

ROOT = Path(__file__).resolve().parents[1]
MODULE = "src/faultatlas/domain/pattern_composition.py"
FIELDS = (
    "pattern",
    "exemplar_associations",
    "invariants",
    "pattern_invariant_associations",
    "invariant_expected_property_associations",
)
COLLECTIONS = FIELDS[1:]
PATTERN_TEXT = "A supplied  模式\nwith repeated evaluation."
INVARIANT_TEXT = "Under this condition, preserve order."


def _pattern(identifier: int = 1, text: str = PATTERN_TEXT) -> SuppliedFaultPattern:
    return SuppliedFaultPattern(
        pattern=FaultPatternIdentity(uuid.UUID(int=identifier)), pattern_statement=text
    )


def _invariant(
    identifier: int = 1, text: str = INVARIANT_TEXT
) -> SuppliedFaultInvariant:
    return SuppliedFaultInvariant(
        invariant=FaultInvariantIdentity(uuid.UUID(int=identifier)),
        invariant_statement=text,
    )


def _case(repository: str = "synthetic-a") -> FaultInstance:
    report = SuppliedFaultReport(
        report=FaultReportIdentity(uuid.UUID(int=1)),
        context=FaultRepositoryContext(
            fault=FaultInstanceIdentity(uuid.UUID(int=1)),
            repository=RepositoryIdentity(
                provider=ProviderKey("github"),
                provider_repository_id=ProviderRepositoryId(repository),
            ),
        ),
        problem_statement="A caller describes repeated evaluation.",
        behavioral_deviation="The callback runs twice.",
    )
    expected = SuppliedFaultExpectedProperty(
        expected_property=FaultExpectedPropertyIdentity(uuid.UUID(int=1)),
        report=report,
        expected_property_statement="The callback runs once.",
    )
    return FaultInstance(
        fault=report.context.fault, reports=(report,), expected_properties=(expected,)
    )


def _values() -> dict[str, Any]:
    pattern, invariant, case = _pattern(), _invariant(), _case()
    return {
        "pattern": pattern,
        "exemplar_associations": (
            FaultPatternExemplarAssociation(pattern=pattern, fault_instance=case),
        ),
        "invariants": (invariant,),
        "pattern_invariant_associations": (
            FaultPatternInvariantAssociation(pattern=pattern, invariant=invariant),
        ),
        "invariant_expected_property_associations": (
            FaultInvariantExpectedPropertyAssociation(
                invariant=invariant,
                fault_instance=case,
                expected_property=case.expected_properties[0],
            ),
        ),
    }


def _fields(value: BaseModel) -> dict[str, Any]:
    return {name: getattr(value, name) for name in type(value).model_fields}


def _wire() -> dict[str, Any]:
    # Authored wire oracle; no expected value is derived from a model dump.
    pattern = {"pattern": str(uuid.UUID(int=1)), "pattern_statement": PATTERN_TEXT}
    invariant = {
        "invariant": str(uuid.UUID(int=1)),
        "invariant_statement": INVARIANT_TEXT,
    }
    report = {
        "report": str(uuid.UUID(int=1)),
        "context": {
            "fault": str(uuid.UUID(int=1)),
            "repository": {
                "schema_version": 1,
                "provider": "github",
                "provider_repository_id": "synthetic-a",
            },
        },
        "problem_statement": "A caller describes repeated evaluation.",
        "behavioral_deviation": "The callback runs twice.",
    }
    expected = {
        "expected_property": str(uuid.UUID(int=1)),
        "report": report,
        "expected_property_statement": "The callback runs once.",
    }
    case = {
        "fault": str(uuid.UUID(int=1)),
        "reports": [report],
        "scenarios": [],
        "occurrences": [],
        "source_object_associations": [],
        "history_fact_associations": [],
        "repair_candidates": [],
        "repair_revision_associations": [],
        "repair_change_set_associations": [],
        "test_materials": [],
        "test_runs": [],
        "test_outcomes": [],
        "test_run_revision_associations": [],
        "test_comparisons": [],
        "explanations": [],
        "hypotheses": [],
        "expected_properties": [expected],
    }
    return {
        "pattern": pattern,
        "exemplar_associations": [{"pattern": pattern, "fault_instance": case}],
        "invariants": [invariant],
        "pattern_invariant_associations": [
            {"pattern": pattern, "invariant": invariant}
        ],
        "invariant_expected_property_associations": [
            {
                "invariant": invariant,
                "fault_instance": case,
                "expected_property": expected,
            }
        ],
    }


def _validate(values: dict[str, Any], mode: str) -> FaultPatternComposition:
    if mode == "python":
        return FaultPatternComposition.model_validate(values)
    return FaultPatternComposition.model_validate_json(
        json.dumps(values, default=lambda value: value.model_dump(mode="json"))
    )


def test_exact_surface_defaults_and_config() -> None:
    assert module.__all__ == ["FaultPatternComposition"]
    assert FaultPatternComposition.__bases__ == (BaseModel,)
    assert tuple(FaultPatternComposition.model_fields) == FIELDS
    assert dict(FaultPatternComposition.model_config) == {
        "frozen": True,
        "extra": "forbid",
        "strict": True,
        "revalidate_instances": "always",
        "validate_default": True,
    }
    minimal = FaultPatternComposition(pattern=_pattern())
    assert minimal.pattern == _pattern()
    assert FaultPatternComposition.model_fields["pattern"].is_required()
    for name in COLLECTIONS:
        field = FaultPatternComposition.model_fields[name]
        assert field.default == () and field.default_factory is None
        assert getattr(minimal, name) == ()
    assert minimal == FaultPatternComposition(
        pattern=_pattern(), **dict.fromkeys(COLLECTIONS, ())
    )
    with pytest.raises(ValidationError) as frozen:
        minimal.pattern = _pattern(2)
    assert frozen.value.errors()[0]["type"] == "frozen_instance"
    with pytest.raises(ValidationError) as missing:
        FaultPatternComposition.model_validate({})
    assert missing.value.errors()[0]["type"] == "missing"


@pytest.mark.parametrize("name", FIELDS)
@pytest.mark.parametrize("from_attributes", [False, True])
@pytest.mark.parametrize("kind", ["mapping", "lookalike", "foreign", "none"])
def test_python_children_are_typed(name: str, from_attributes: bool, kind: str) -> None:
    values = _values()
    child = values[name] if name == "pattern" else values[name][0]

    class Foreign(BaseModel):
        pass

    raw = {
        "mapping": child.model_dump(),
        "lookalike": SimpleNamespace(**_fields(child)),
        "foreign": Foreign(),
        "none": None,
    }[kind]
    values[name] = raw if name == "pattern" else (raw,)
    with pytest.raises(ValidationError) as failure:
        FaultPatternComposition.model_validate(values, from_attributes=from_attributes)
    assert failure.value.errors()[0]["loc"] == (
        (name,) if name == "pattern" else (name, 0)
    )
    assert failure.value.errors()[0]["type"] == "value_error"


@pytest.mark.parametrize("name", COLLECTIONS)
@pytest.mark.parametrize("kind", ["list", "none", "mapping"])
def test_strict_collection_language(name: str, kind: str) -> None:
    values = _values()
    values[name] = {"list": list(values[name]), "none": None, "mapping": {}}[kind]
    with pytest.raises(ValidationError) as failure:
        FaultPatternComposition.model_validate(values)
    assert failure.value.errors()[0]["loc"] == (name,)
    assert failure.value.errors()[0]["type"] == "tuple_type"


@pytest.mark.parametrize("name", FIELDS)
def test_owning_revalidation_and_ordinary_subclasses(name: str) -> None:
    values = _values()
    value: BaseModel = values[name] if name == "pattern" else values[name][0]
    owner = type(value)
    subclass = type("OrdinarySubclass", (owner,), {})
    typed = subclass.model_validate(_fields(value))
    values[name] = typed if name == "pattern" else (typed,)
    result = FaultPatternComposition.model_validate(values)
    normalized = (
        getattr(result, name) if name == "pattern" else getattr(result, name)[0]
    )
    assert type(normalized) is owner and normalized == value
    legal = owner.model_construct(**_fields(value))
    values[name] = legal if name == "pattern" else (legal,)
    assert FaultPatternComposition.model_validate(values) == result
    key = next(iter(owner.model_fields))
    object.__setattr__(legal, key, None)
    with pytest.raises(ValidationError) as failure:
        FaultPatternComposition.model_validate(values)
    assert failure.value.errors()[0]["loc"][:1] == (name,)


@pytest.mark.parametrize("mode", ["python", "json"])
def test_full_authored_wire_and_reentry(mode: str) -> None:
    value = _validate(_values(), mode)
    assert value.model_dump(mode="json") == _wire()
    restored = FaultPatternComposition.model_validate_json(json.dumps(_wire()))
    assert restored == value
    assert FaultPatternComposition.model_validate(value) == value
    assert FaultPatternComposition.model_validate_json(value.model_dump_json()) == value
    assert isinstance(restored.exemplar_associations[0].fault_instance.reports, tuple)
    assert isinstance(
        restored.invariant_expected_property_associations[
            0
        ].fault_instance.expected_properties,
        tuple,
    )
    with pytest.raises(ValidationError):
        FaultPatternComposition.model_validate(value.model_dump(), from_attributes=True)
    invalid: dict[str, Any] = _fields(value)
    invalid["invariants"] = (None,)
    corrupted = FaultPatternComposition.model_construct(**invalid)
    with pytest.raises(ValidationError) as failure:
        FaultPatternComposition.model_validate(corrupted)
    assert failure.value.errors()[0]["loc"] == ("invariants", 0)


@pytest.mark.parametrize("name", COLLECTIONS)
@pytest.mark.parametrize("mode", ["python", "json"])
def test_collection_maximum(name: str, mode: str) -> None:
    schema = FaultPatternComposition.model_json_schema()["properties"][name]
    assert schema["maxItems"] == 4096
    values = _values()
    if name == "invariants":
        values[name] = tuple(_invariant(i) for i in range(4096))
        values["pattern_invariant_associations"] = tuple(
            FaultPatternInvariantAssociation(pattern=values["pattern"], invariant=i)
            for i in values[name]
        )
    else:
        values[name] = values[name] * 4096
    assert len(getattr(_validate(values, mode), name)) == 4096
    values[name] = (*values[name], values[name][0])
    with pytest.raises(ValidationError) as failure:
        _validate(values, mode)
    assert failure.value.errors()[0]["loc"] == (name,)
    assert failure.value.errors()[0]["type"] == "too_long"


@pytest.mark.parametrize(
    "name", ["exemplar_associations", "pattern_invariant_associations"]
)
@pytest.mark.parametrize("mode", ["python", "json"])
def test_full_root_reference_refuses_same_identity_changed_prose(
    name: str, mode: str
) -> None:
    values = _values()
    relation: BaseModel = values[name][0]
    conflicting = type(relation).model_validate(
        _fields(relation) | {"pattern": _pattern(text="Different supplied prose.")}
    )
    values[name] = (conflicting,)
    before = conflicting.model_dump_json()
    with pytest.raises(ValidationError, match="different pattern"):
        _validate(values, mode)
    assert conflicting.model_dump_json() == before
    assert values["pattern"] == _pattern()


@pytest.mark.parametrize("mode", ["python", "json"])
@pytest.mark.parametrize("different_text", [False, True])
def test_duplicate_invariant_identity_refused(mode: str, different_text: bool) -> None:
    values = _values()
    values["invariants"] += (
        _invariant(
            text="Conflicting proposition." if different_text else INVARIANT_TEXT
        ),
    )
    with pytest.raises(ValidationError, match="one identity more than once"):
        _validate(values, mode)


def test_equal_python_hashes_do_not_merge_distinct_invariant_members() -> None:
    first = _invariant(1)
    second = _invariant(1 + sys.hash_info.modulus, "A different supplied proposition.")
    assert first.invariant != second.invariant
    assert hash(first.invariant) == hash(second.invariant)
    pattern = _pattern()
    value = FaultPatternComposition(
        pattern=pattern,
        invariants=(first, second),
        pattern_invariant_associations=tuple(
            FaultPatternInvariantAssociation(pattern=pattern, invariant=invariant)
            for invariant in (second, first)
        ),
    )
    assert value.invariants == (first, second)


@pytest.mark.parametrize("name", FIELDS)
def test_json_null_is_not_an_omitted_child(name: str) -> None:
    wire = _wire()
    wire[name] = None
    with pytest.raises(ValidationError) as failure:
        FaultPatternComposition.model_validate_json(json.dumps(wire))
    assert failure.value.errors()[0]["loc"] == (name,)


@pytest.mark.parametrize(
    "name",
    ["pattern_invariant_associations", "invariant_expected_property_associations"],
)
@pytest.mark.parametrize("mode", ["python", "json"])
@pytest.mark.parametrize("different_text", [False, True])
def test_full_invariant_membership_refuses_dangling_record(
    name: str, mode: str, different_text: bool
) -> None:
    values = _values()
    relation: BaseModel = values[name][0]
    nonmember = (
        _invariant(text="Different statement.") if different_text else _invariant(2)
    )
    values[name] = (
        type(relation).model_validate(_fields(relation) | {"invariant": nonmember}),
    )
    before = values["invariants"]
    with pytest.raises(ValidationError, match="nonmember invariant"):
        _validate(values, mode)
    assert values["invariants"] == before


@pytest.mark.parametrize("mode", ["python", "json"])
def test_root_attachment_and_repeated_explicit_relations(mode: str) -> None:
    values = _values()
    independently_equal = SuppliedFaultInvariant.model_validate_json(
        json.dumps(_wire()["invariants"][0])
    )
    assert independently_equal is not values["invariants"][0]
    values["invariants"] = (independently_equal,)
    for name in COLLECTIONS:
        if name != "invariants":
            values[name] *= 2
    value = _validate(values, mode)
    assert all(len(getattr(value, n)) == 2 for n in COLLECTIONS if n != "invariants")
    values["pattern_invariant_associations"] = ()
    with pytest.raises(ValidationError, match="not attached to the root"):
        _validate(values, mode)
    assert independently_equal == _invariant()  # Still valid on its own.


@pytest.mark.parametrize("mode", ["python", "json"])
def test_s04_owner_full_expected_property_rule_survives(mode: str) -> None:
    values = _values()
    relation = values["invariant_expected_property_associations"][0]
    changed = SuppliedFaultExpectedProperty.model_validate(
        _fields(relation.expected_property)
        | {"expected_property_statement": "Different expectation."}
    )
    invalid: dict[str, Any] = _fields(relation)
    invalid["expected_property"] = changed
    values["invariant_expected_property_associations"] = (
        FaultInvariantExpectedPropertyAssociation.model_construct(**invalid),
    )
    with pytest.raises(
        ValidationError, match="expected_property is not a full-record member"
    ):
        _validate(values, mode)


@pytest.mark.parametrize("mode", ["python", "json"])
def test_expectation_chain_and_exemplar_are_independent(mode: str) -> None:
    values = _values()
    values["exemplar_associations"] = ()
    chain = _validate(values, mode)
    assert chain.exemplar_associations == ()
    assert len(chain.invariant_expected_property_associations) == 1
    values = _values()
    exemplar = _validate(
        {
            "pattern": values["pattern"],
            "exemplar_associations": values["exemplar_associations"],
        },
        mode,
    )
    assert (
        exemplar.invariants
        == exemplar.pattern_invariant_associations
        == exemplar.invariant_expected_property_associations
        == ()
    )
    # Same UUID under every nominal subject type has no aggregate-wide rule.
    assert chain.pattern.pattern.root == chain.invariants[0].invariant.root
    assert chain.pattern.pattern != chain.invariants[0].invariant
    assert _validate(_fields(chain), mode) == chain  # No registry across values.


@pytest.mark.parametrize("name", COLLECTIONS)
def test_order_is_preserved_and_changes_value_equality(name: str) -> None:
    values = _values()
    second_invariant, second_case = _invariant(2), _case("synthetic-b")
    values["invariants"] += (second_invariant,)
    values["pattern_invariant_associations"] += (
        FaultPatternInvariantAssociation(
            pattern=values["pattern"], invariant=second_invariant
        ),
    )
    values["exemplar_associations"] += (
        FaultPatternExemplarAssociation(
            pattern=values["pattern"], fault_instance=second_case
        ),
    )
    values["invariant_expected_property_associations"] += (
        FaultInvariantExpectedPropertyAssociation(
            invariant=second_invariant,
            fault_instance=second_case,
            expected_property=second_case.expected_properties[0],
        ),
    )
    forward = FaultPatternComposition.model_validate(values)
    assert getattr(forward, name) == values[name]
    values[name] = tuple(reversed(values[name]))
    backward = FaultPatternComposition.model_validate(values)
    assert getattr(backward, name) == values[name]
    assert backward != forward
    assert (
        FaultPatternComposition.model_validate_json(backward.model_dump_json())
        == backward
    )


@pytest.mark.parametrize(
    "name",
    [
        "evidence",
        "support",
        "confidence",
        "review",
        "applicability",
        "transfer",
        "similarity",
        "satisfaction",
        "violation",
        "completeness",
        "canonical_ordering",
        "expected_properties",
        "composition_identity",
    ],
)
def test_no_extra_semantic_surface(name: str) -> None:
    with pytest.raises(ValidationError) as failure:
        FaultPatternComposition.model_validate({"pattern": _pattern(), name: ()})
    assert failure.value.errors()[0]["loc"] == (name,)
    assert failure.value.errors()[0]["type"] == "extra_forbidden"


def test_exact_dependencies_and_no_predecessor_imports() -> None:
    tree = ast.parse((ROOT / MODULE).read_text())
    assert not any(isinstance(n, ast.Import) for n in ast.walk(tree))
    imports = {
        n.module: {a.name for a in n.names}
        for n in ast.walk(tree)
        if isinstance(n, ast.ImportFrom)
    }
    assert imports == {
        "typing": {"Annotated", "Self"},
        "pydantic": {
            "BaseModel",
            "BeforeValidator",
            "ConfigDict",
            "Field",
            "ValidationInfo",
            "field_validator",
            "model_validator",
        },
        "faultatlas.domain.pattern": {"SuppliedFaultPattern"},
        "faultatlas.domain.pattern_exemplar": {"FaultPatternExemplarAssociation"},
        "faultatlas.domain.invariant": {"SuppliedFaultInvariant"},
        "faultatlas.domain.invariant_relationship": {
            "FaultPatternInvariantAssociation",
            "FaultInvariantExpectedPropertyAssociation",
        },
    }
    assert all(
        n.level == 0 and all(a.asname is None for a in n.names)
        for n in ast.walk(tree)
        if isinstance(n, ast.ImportFrom)
    )
    assert not {"__eq__", "__hash__"}.intersection(
        n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)
    )
    assert not {
        "sorted",
        "sort",
        "eval",
        "exec",
        "open",
        "__import__",
        "model_construct",
        "model_copy",
    }.intersection(n.id for n in ast.walk(tree) if isinstance(n, ast.Name))
    paths = sorted((ROOT / "src/faultatlas").rglob("*.py"))
    assert len(paths) == 25
    uuid_roots: list[str] = []
    for path in paths:
        source = path.read_text()
        if path != ROOT / MODULE:
            assert (
                "pattern_composition" not in source
                and "FaultPatternComposition" not in source
            )
        for n in ast.walk(ast.parse(source)):
            if isinstance(n, ast.ClassDef) and any(
                ast.unparse(b) == "RootModel[uuid.UUID]" for b in n.bases
            ):
                uuid_roots.append(n.name)
    assert len(uuid_roots) == len(set(uuid_roots)) == 12


def test_no_io_during_value_operations(monkeypatch: pytest.MonkeyPatch) -> None:
    import builtins
    import socket
    import time

    values, wire = _values(), json.dumps(_wire())

    def denied(*args: object, **kwargs: object) -> Any:
        raise AssertionError("composition attempted external operation")

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
        value = FaultPatternComposition.model_validate(values)
        assert FaultPatternComposition.model_validate_json(wire) == value
        assert FaultPatternComposition.model_validate(value) == value
        assert (
            FaultPatternComposition.model_validate_json(value.model_dump_json())
            == value
        )


def test_roadmap_states_bounded_s05_and_next_gate() -> None:
    text = (ROOT / "docs/roadmap.md").read_text()
    section = " ".join(
        text.split("### S1.P07.S05 — Bounded pattern composition", 1)[1]
        .split("The `S1.P07` route", 1)[0]
        .split()
    )
    for phrase in (
        "Pattern-only",
        "4096",
        "full-record-equal",
        "unique within this composition",
        "non-exemplar case",
        "Neither direction synthesizes",
        "Order is preserved",
        "Durable canonicalization",
        "five named modules and eight exports",
    ):
        assert phrase in section
    current = " ".join(text.split("## Current status", 1)[1].split("## ", 1)[0].split())
    assert "`S1.P07.S05` is complete" in current
    assert "`S1.P07.S06` is next and not started" in current
    assert "`S1.P07` is active and incomplete" in current


EXPECTED_MODULES = [
    "faultatlas/__init__.py",
    "faultatlas/__main__.py",
    "faultatlas/cli.py",
    "faultatlas/domain/__init__.py",
    "faultatlas/domain/compatibility.py",
    "faultatlas/domain/evidence.py",
    "faultatlas/domain/fault.py",
    "faultatlas/domain/fault_evidence_link.py",
    "faultatlas/domain/fault_instance.py",
    "faultatlas/domain/fault_interpretation.py",
    "faultatlas/domain/fault_repair.py",
    "faultatlas/domain/fault_source_relationship.py",
    "faultatlas/domain/fault_test.py",
    "faultatlas/domain/history.py",
    "faultatlas/domain/history_evidence_link.py",
    "faultatlas/domain/identity.py",
    "faultatlas/domain/invariant.py",
    "faultatlas/domain/invariant_relationship.py",
    "faultatlas/domain/pattern.py",
    "faultatlas/domain/pattern_composition.py",
    "faultatlas/domain/pattern_exemplar.py",
    "faultatlas/domain/revision.py",
    "faultatlas/domain/snapshot.py",
    "faultatlas/domain/snapshot_evidence_link.py",
    "faultatlas/domain/source.py",
]


@pytest.fixture(scope="module")
def distributions(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, Path]:
    output = tmp_path_factory.mktemp("pattern-composition-distributions")
    result = subprocess.run(
        ["uv", "build", "--offline", "--no-create-gitignore", "--out-dir", str(output)],
        cwd=ROOT,
        env=os.environ | {"UV_CACHE_DIR": str(output / "cache"), "UV_OFFLINE": "1"},
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return next(output.glob("*.whl")), next(output.glob("*.tar.gz"))


def test_exact25_package_inventory_and_source_bytes(
    distributions: tuple[Path, Path],
) -> None:
    assert len(EXPECTED_MODULES) == len(set(EXPECTED_MODULES)) == 25
    assert (
        sorted(
            p.relative_to(ROOT / "src").as_posix() for p in (ROOT / "src").rglob("*.py")
        )
        == EXPECTED_MODULES
    )
    with zipfile.ZipFile(distributions[0]) as archive:
        names = archive.namelist()
        assert sorted(n for n in names if n.endswith(".py")) == EXPECTED_MODULES
        for path in EXPECTED_MODULES:
            assert archive.read(path) == (ROOT / "src" / path).read_bytes()
    with tarfile.open(distributions[1]) as archive:
        members = [m for m in archive.getmembers() if m.isfile()]
        assert (
            sorted(m.name.split("/", 2)[2] for m in members if m.name.endswith(".py"))
            == EXPECTED_MODULES
        )
        for member in members:
            if member.name.endswith(".py"):
                stream = archive.extractfile(member)
                assert stream is not None
                assert (
                    stream.read() == (ROOT / member.name.split("/", 1)[1]).read_bytes()
                )
        names += [m.name for m in members]
    for name in names:
        assert not {"docs", "tests", "reference_corpus"}.intersection(Path(name).parts)


def test_installed_wheel_provenance_and_authored_json(
    distributions: tuple[Path, Path], tmp_path: Path
) -> None:
    installed = tmp_path / "installed"
    env = os.environ | {"UV_CACHE_DIR": str(tmp_path / "cache"), "UV_OFFLINE": "1"}
    result = subprocess.run(
        [
            "uv",
            "pip",
            "install",
            "--offline",
            "--no-deps",
            "--target",
            str(installed),
            str(distributions[0]),
        ],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    probe = """
import json, pathlib, sys
installed = pathlib.Path(sys.argv[1]).resolve()
sys.path.insert(0, str(installed))
from faultatlas.domain.pattern_composition import FaultPatternComposition
wire = json.loads(sys.argv[2])
value = FaultPatternComposition.model_validate_json(sys.argv[2])
assert value.model_dump(mode="json") == wire
assert FaultPatternComposition.model_validate_json(value.model_dump_json()) == value
assert value.invariant_expected_property_associations[0].expected_property in value.invariant_expected_property_associations[0].fault_instance.expected_properties
for name, module in tuple(sys.modules.items()):
    if name == "faultatlas" or name.startswith("faultatlas."):
        assert pathlib.Path(module.__file__).resolve().is_relative_to(installed), name
assert tuple(type(value).model_fields) == ("pattern", "exemplar_associations", "invariants", "pattern_invariant_associations", "invariant_expected_property_associations")
print("installed S05 provenance and authored JSON PASS")
"""
    result = subprocess.run(
        [sys.executable, "-I", "-B", "-c", probe, str(installed), json.dumps(_wire())],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "installed S05 provenance and authored JSON PASS" in result.stdout
