"""S03 representation and non-promotion witnesses using synthetic values."""

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
from pydantic import BaseModel, RootModel, ValidationError

import faultatlas.domain.invariant as invariant_module
from faultatlas.domain.fault import (
    FaultInstanceIdentity,
    FaultOccurrenceIdentity,
    FaultReportIdentity,
    FaultRepositoryContext,
    FaultScenarioIdentity,
    SuppliedFaultReport,
)
from faultatlas.domain.fault_instance import FaultInstance
from faultatlas.domain.fault_interpretation import (
    FaultExpectedPropertyIdentity,
    FaultExplanationIdentity,
    FaultHypothesisIdentity,
    SuppliedFaultExpectedProperty,
)
from faultatlas.domain.fault_repair import FaultRepairCandidateIdentity
from faultatlas.domain.fault_test import FaultTestMaterialIdentity, FaultTestRunIdentity
from faultatlas.domain.identity import (
    ProviderKey,
    ProviderRepositoryId,
    RepositoryIdentity,
)
from faultatlas.domain.invariant import FaultInvariantIdentity, SuppliedFaultInvariant
from faultatlas.domain.pattern import FaultPatternIdentity, SuppliedFaultPattern
from faultatlas.domain.pattern_exemplar import FaultPatternExemplarAssociation

ROOT = Path(__file__).resolve().parents[1]
MODULE = "src/faultatlas/domain/invariant.py"
# S04 adds a separate consumer; the S02 baseline byte map stays historical.
INVARIANT_RELATIONSHIP_MODULE = "src/faultatlas/domain/invariant_relationship.py"
FIELDS = ("invariant", "invariant_statement")
SCALAR = uuid.UUID("00000000-0000-4000-8000-000000000001")
# Authored illustrative prose, not evidence about the retained pytest case.
STATEMENT = (
    "For rewrites required to preserve an expression's side-effect behavior, "
    "preserve the original evaluation count and side-effect order."
)
COMPETING = "Such rewrites may duplicate evaluations."
# This bounded witness names all ten published P06 identities and the S01 one.
PREDECESSOR_IDENTITIES: tuple[type[RootModel[uuid.UUID]], ...] = (
    FaultInstanceIdentity,
    FaultReportIdentity,
    FaultScenarioIdentity,
    FaultOccurrenceIdentity,
    FaultRepairCandidateIdentity,
    FaultTestMaterialIdentity,
    FaultTestRunIdentity,
    FaultExplanationIdentity,
    FaultHypothesisIdentity,
    FaultExpectedPropertyIdentity,
    FaultPatternIdentity,
)


def _supplied(
    text: str = STATEMENT, identity: uuid.UUID = SCALAR
) -> SuppliedFaultInvariant:
    return SuppliedFaultInvariant(
        invariant=FaultInvariantIdentity(identity), invariant_statement=text
    )


def _fields(value: BaseModel) -> dict[str, Any]:
    return {name: getattr(value, name) for name in type(value).model_fields}


def _errors(error: ValidationError) -> list[tuple[tuple[str | int, ...], str]]:
    return [(item["loc"], item["type"]) for item in error.errors()]


def _minimal_case() -> FaultInstance:
    fault = FaultInstanceIdentity(SCALAR)
    report = SuppliedFaultReport(
        report=FaultReportIdentity(SCALAR),
        context=FaultRepositoryContext(
            fault=fault,
            repository=RepositoryIdentity(
                provider=ProviderKey("github"),
                provider_repository_id=ProviderRepositoryId("synthetic-invariant-case"),
            ),
        ),
        problem_statement="A caller describes a changed evaluation count.",
        behavioral_deviation="The caller reports repeated side effects.",
    )
    return FaultInstance(fault=fault, reports=(report,))


def test_exact_surface_configuration_and_independent_bases() -> None:
    assert invariant_module.__all__ == [
        "FaultInvariantIdentity",
        "SuppliedFaultInvariant",
    ]
    assert FaultInvariantIdentity.__bases__ == (RootModel[uuid.UUID],)
    assert SuppliedFaultInvariant.__bases__ == (BaseModel,)
    assert tuple(FaultInvariantIdentity.model_fields) == ("root",)
    assert FaultInvariantIdentity.model_fields["root"].annotation is uuid.UUID
    assert tuple(SuppliedFaultInvariant.model_fields) == FIELDS
    assert [f.annotation for f in SuppliedFaultInvariant.model_fields.values()] == [
        FaultInvariantIdentity,
        str,
    ]
    identity_config = {
        "frozen": True,
        "strict": True,
        "revalidate_instances": "always",
        "validate_default": True,
    }
    assert dict(FaultInvariantIdentity.model_config) == identity_config
    assert dict(SuppliedFaultInvariant.model_config) == identity_config | {
        "extra": "forbid"
    }
    for model in (FaultInvariantIdentity, SuppliedFaultInvariant):
        assert all(
            f.is_required() and f.default_factory is None
            for f in model.model_fields.values()
        )
        assert model.model_computed_fields == {}
        assert model.__private_attributes__ == {}
    assert not {
        "__eq__",
        "__hash__",
        "__lt__",
        "__le__",
        "__gt__",
        "__ge__",
    }.intersection(
        n.name
        for n in ast.walk(ast.parse((ROOT / MODULE).read_bytes()))
        if isinstance(n, ast.FunctionDef)
    )


@pytest.mark.parametrize(
    "scalar",
    [
        uuid.UUID(int=0),
        uuid.UUID(int=(1 << 128) - 1),
        SCALAR,
        uuid.UUID("00000000-0000-1000-8000-000000000001"),
        uuid.UUID("00000000-0000-7000-8000-000000000001"),
    ],
)
def test_uuid_policy_and_bare_json_round_trip(scalar: uuid.UUID) -> None:
    value = FaultInvariantIdentity(scalar)
    assert value.root == scalar
    assert FaultInvariantIdentity.model_validate(scalar) == value
    assert FaultInvariantIdentity.model_validate(value) == value
    assert json.loads(value.model_dump_json()) == str(scalar)
    assert FaultInvariantIdentity.model_validate_json(json.dumps(str(scalar))) == value
    record = _supplied(identity=scalar)
    assert (
        SuppliedFaultInvariant.model_validate_json(record.model_dump_json()) == record
    )


@pytest.mark.parametrize(
    "bad", [str(SCALAR), SCALAR.bytes, 1, True, None, {"root": SCALAR}]
)
def test_identity_default_python_input_is_strict(bad: object) -> None:
    with pytest.raises(ValidationError) as failure:
        FaultInvariantIdentity.model_validate(bad)
    assert _errors(failure.value) == [((), "is_instance_of")]


@pytest.mark.parametrize("other_type", PREDECESSOR_IDENTITIES)
def test_nominal_identity_does_not_conflate_shared_uuid(
    other_type: type[RootModel[uuid.UUID]],
) -> None:
    value, other = FaultInvariantIdentity(SCALAR), other_type(SCALAR)
    assert len(PREDECESSOR_IDENTITIES) == 11
    assert len(set(PREDECESSOR_IDENTITIES)) == 11
    assert not issubclass(FaultInvariantIdentity, other_type)
    assert not issubclass(other_type, FaultInvariantIdentity)
    assert value.root == other.root == SCALAR
    assert value != other and other != value
    assert hash(value) == hash(FaultInvariantIdentity(SCALAR))
    with pytest.raises(ValidationError) as failure:
        SuppliedFaultInvariant.model_validate(
            {"invariant": other, "invariant_statement": STATEMENT}
        )
    assert _errors(failure.value) == [(("invariant",), "value_error")]


def test_typed_python_and_independently_authored_json_values() -> None:
    supplied = _supplied()
    expected = {"invariant": str(SCALAR), "invariant_statement": STATEMENT}
    assert SuppliedFaultInvariant.model_validate_json(json.dumps(expected)) == supplied
    assert json.loads(supplied.model_dump_json()) == expected
    assert list(json.loads(supplied.model_dump_json())) == list(FIELDS)
    assert SuppliedFaultInvariant.model_validate(_fields(supplied)) == supplied
    assert (
        SuppliedFaultInvariant.model_validate(_fields(supplied), from_attributes=True)
        == supplied
    )
    assert SuppliedFaultInvariant.model_validate(supplied) == supplied
    for projection in (supplied.model_dump(), expected):
        with pytest.raises(ValidationError) as failure:
            SuppliedFaultInvariant.model_validate(projection)
        assert _errors(failure.value) == [(("invariant",), "value_error")]


@pytest.mark.parametrize(
    "kind", ["uuid", "string", "mapping", "foreign", "attributes", "none"]
)
def test_python_child_guard_cannot_be_bypassed_by_attributes(kind: str) -> None:
    class Foreign(RootModel[uuid.UUID]):
        pass

    bad: dict[str, object] = {
        "uuid": SCALAR,
        "string": str(SCALAR),
        "mapping": {"root": SCALAR},
        "foreign": Foreign(SCALAR),
        "attributes": SimpleNamespace(root=SCALAR),
        "none": None,
    }
    values: dict[str, Any] = {"invariant": bad[kind], "invariant_statement": STATEMENT}
    for attributes in (False, True):
        with pytest.raises(ValidationError) as failure:
            SuppliedFaultInvariant.model_validate(values, from_attributes=attributes)
        assert _errors(failure.value) == [(("invariant",), "value_error")]
    with pytest.raises(ValidationError) as failure:
        SuppliedFaultInvariant(**values)
    assert _errors(failure.value) == [(("invariant",), "value_error")]


@pytest.mark.parametrize("field", FIELDS)
def test_required_fields_and_frozen_behavior(field: str) -> None:
    value = _supplied()
    values = _fields(value)
    del values[field]
    with pytest.raises(ValidationError) as missing:
        SuppliedFaultInvariant.model_validate(values)
    assert _errors(missing.value) == [((field,), "missing")]
    with pytest.raises(ValidationError) as frozen:
        setattr(value, field, getattr(value, field))
    assert _errors(frozen.value) == [((field,), "frozen_instance")]
    with pytest.raises(ValidationError) as identity_frozen:
        setattr(value.invariant, "root", SCALAR)
    assert _errors(identity_frozen.value) == [(("root",), "frozen_instance")]


def test_ordinary_subclasses_and_legal_constructed_values_normalize() -> None:
    class IdentityChild(FaultInvariantIdentity):
        pass

    class RecordChild(SuppliedFaultInvariant):
        pass

    identity = IdentityChild(SCALAR)
    value = SuppliedFaultInvariant(invariant=identity, invariant_statement=STATEMENT)
    assert type(value.invariant) is FaultInvariantIdentity
    assert value == _supplied()
    normalized = SuppliedFaultInvariant.model_validate(RecordChild(**_fields(value)))
    assert type(normalized) is SuppliedFaultInvariant and normalized == value
    constructed = SuppliedFaultInvariant.model_construct(
        invariant=FaultInvariantIdentity.model_construct(root=SCALAR),
        invariant_statement=STATEMENT,
    )
    assert SuppliedFaultInvariant.model_validate(constructed) == value


@pytest.mark.parametrize("constructed", [False, True])
def test_invalid_identity_child_fails_normal_reentry(constructed: bool) -> None:
    value = _supplied()
    if constructed:
        invalid: Any = str(SCALAR)
        child = FaultInvariantIdentity.model_construct(root=invalid)
    else:
        child = FaultInvariantIdentity(SCALAR)
        object.__setattr__(child, "root", str(SCALAR))
    for payload in (
        {"invariant": child, "invariant_statement": STATEMENT},
        SuppliedFaultInvariant.model_construct(
            invariant=child, invariant_statement=STATEMENT
        ),
    ):
        with pytest.raises(ValidationError) as failure:
            SuppliedFaultInvariant.model_validate(payload)
        assert _errors(failure.value) == [(("invariant",), "is_instance_of")]
    assert value == _supplied()


def test_corrupted_record_text_is_revalidated() -> None:
    value = _supplied()
    object.__setattr__(value, "invariant_statement", " padded ")
    with pytest.raises(ValidationError) as failure:
        SuppliedFaultInvariant.model_validate(value)
    assert _errors(failure.value) == [(("invariant_statement",), "value_error")]


@pytest.mark.parametrize(
    "text",
    [
        "x",
        "x" * 4096,
        "回" * 4096,
        "α  β\n\tγ",
        "e\u0301",
        "é",
        "条件：缓存有效时\n保持  顺序",
        "A variable may change while the required property remains satisfied.",
    ],
)
def test_admitted_text_preserves_exact_characters(text: str) -> None:
    value = _supplied(text)
    assert value.invariant_statement == text
    assert (
        SuppliedFaultInvariant.model_validate_json(
            value.model_dump_json()
        ).invariant_statement
        == text
    )
    assert json.loads(value.model_dump_json())["invariant_statement"] == text


@pytest.mark.parametrize(
    "text,category",
    [
        ("", "string_too_short"),
        ("x" * 4097, "string_too_long"),
        (" \t\n", "value_error"),
        ("　", "value_error"),
        (" leading", "value_error"),
        ("trailing\n", "value_error"),
        ("a\ud800b", "string_unicode"),
        ("a\udfff", "string_unicode"),
        (None, "string_type"),
        (1, "string_type"),
        (True, "string_type"),
        (["text"], "string_type"),
    ],
)
def test_invalid_text_is_refused_during_python_and_json_validation(
    text: object, category: str
) -> None:
    with pytest.raises(ValidationError) as python_error:
        SuppliedFaultInvariant.model_validate(
            {"invariant": FaultInvariantIdentity(SCALAR), "invariant_statement": text}
        )
    assert _errors(python_error.value) == [(("invariant_statement",), category)]
    with pytest.raises(ValidationError) as json_error:
        SuppliedFaultInvariant.model_validate_json(
            json.dumps({"invariant": str(SCALAR), "invariant_statement": text})
        )
    # Lone surrogate JSON is refused by the parser itself before field validation.
    if category == "string_unicode":
        assert _errors(json_error.value) == [((), "json_invalid")]
    else:
        assert _errors(json_error.value) == [(("invariant_statement",), category)]


def test_python_bytes_are_not_supplied_text() -> None:
    with pytest.raises(ValidationError) as failure:
        SuppliedFaultInvariant.model_validate(
            {
                "invariant": FaultInvariantIdentity(SCALAR),
                "invariant_statement": b"text",
            }
        )
    assert _errors(failure.value) == [(("invariant_statement",), "string_type")]


def test_identity_and_opaque_proposition_remain_independent() -> None:
    first, equal = _supplied(), _supplied()
    assert first == equal and hash(first) == hash(equal)
    assert _supplied(identity=uuid.UUID(int=2)) != first
    competing = _supplied(COMPETING)
    assert competing.invariant == first.invariant and competing != first
    assert competing.invariant_statement == COMPETING
    false = _supplied("Every integer equals its successor.")
    conditional = _supplied(
        "At observation B, preserve order unless exception C applies."
    )
    assert false.invariant_statement == "Every integer equals its successor."
    assert (
        conditional.invariant_statement
        == "At observation B, preserve order unless exception C applies."
    )
    assert _supplied("e\u0301") != _supplied("é")
    assert _supplied() == first


@pytest.mark.parametrize(
    "extra",
    [
        "pattern",
        "fault_instance",
        "exemplar",
        "expected_property",
        "source",
        "evidence",
        "support",
        "proof",
        "confidence",
        "review",
        "status",
        "applicability",
        "transfer",
        "exceptions",
        "counterexamples",
        "violations",
        "predicate",
        "origin",
    ],
)
def test_no_relationship_or_inferred_surface_is_preallocated(extra: str) -> None:
    value = _supplied()
    assert tuple(type(value).model_fields) == FIELDS
    assert set(value.model_dump()) == set(FIELDS)
    assert {n for n in dir(SuppliedFaultInvariant) if not n.startswith("_")} <= set(
        dir(BaseModel)
    )
    with pytest.raises(ValidationError) as failure:
        SuppliedFaultInvariant.model_validate(_fields(value) | {extra: "supplied"})
    assert _errors(failure.value) == [((extra,), "extra_forbidden")]


def test_same_prose_does_not_promote_case_property_pattern_or_exemplar() -> None:
    case = _minimal_case()
    pattern = SuppliedFaultPattern(
        pattern=FaultPatternIdentity(SCALAR), pattern_statement=STATEMENT
    )
    expected = SuppliedFaultExpectedProperty(
        expected_property=FaultExpectedPropertyIdentity(SCALAR),
        report=case.reports[0],
        expected_property_statement=STATEMENT,
    )
    link = FaultPatternExemplarAssociation(pattern=pattern, fault_instance=case)
    invariant = _supplied()
    assert (
        expected.expected_property_statement
        == pattern.pattern_statement
        == invariant.invariant_statement
    )
    for foreign in (pattern, expected, link, case):
        with pytest.raises(ValidationError) as failure:
            SuppliedFaultInvariant.model_validate(foreign)
        assert _errors(failure.value) == [((), "model_type")]
        with pytest.raises(ValidationError) as child:
            SuppliedFaultInvariant.model_validate(
                {"invariant": foreign, "invariant_statement": STATEMENT}
            )
        assert _errors(child.value) == [(("invariant",), "value_error")]
    with pytest.raises(ValidationError) as s02:
        FaultPatternExemplarAssociation.model_validate(
            {"pattern": invariant, "fault_instance": case}
        )
    assert _errors(s02.value) == [(("pattern",), "value_error")]
    with pytest.raises(ValidationError) as local:
        SuppliedFaultExpectedProperty.model_validate(
            {
                "expected_property": invariant.invariant,
                "report": case.reports[0],
                "expected_property_statement": STATEMENT,
            }
        )
    assert _errors(local.value) == [(("expected_property",), "value_error")]


def test_construction_needs_no_foreign_value_and_performs_no_io(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import builtins
    import socket
    import time

    def denied(*args: object, **kwargs: object) -> Any:
        raise AssertionError("unexpected foreign construction or external operation")

    with monkeypatch.context() as blocked:
        for model in (
            SuppliedFaultPattern,
            FaultInstance,
            FaultPatternExemplarAssociation,
            SuppliedFaultExpectedProperty,
        ):
            blocked.setattr(model, "__init__", denied)
        for owner, name in (
            (builtins, "open"),
            (Path, "open"),
            (socket, "socket"),
            (subprocess, "Popen"),
            (os, "getenv"),
            (os, "stat"),
            (time, "time"),
            (uuid, "uuid4"),
        ):
            blocked.setattr(owner, name, denied)
        value = _supplied()
        assert (
            SuppliedFaultInvariant.model_validate_json(value.model_dump_json()) == value
        )
        assert SuppliedFaultInvariant.model_validate(value) == value
    assert set(value.model_dump()) == set(FIELDS)


def test_module_is_independent_and_baseline_production_bytes_are_preserved() -> None:
    tree = ast.parse((ROOT / MODULE).read_bytes())
    imports = {
        a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names
    }
    from_imports = {
        n.module: {a.name for a in n.names}
        for n in ast.walk(tree)
        if isinstance(n, ast.ImportFrom)
    }
    assert imports == {"uuid"}
    assert from_imports == {
        "typing": {"Annotated"},
        "pydantic": {
            "BaseModel",
            "ConfigDict",
            "RootModel",
            "StringConstraints",
            "ValidationInfo",
            "field_validator",
        },
    }
    assert all(n.level == 0 for n in ast.walk(tree) if isinstance(n, ast.ImportFrom))
    for path, digest in BASELINE_PRODUCTION.items():
        data = (ROOT / path).read_bytes()
        assert hashlib.sha256(data).hexdigest() == digest, path
        assert (
            b"FaultInvariantIdentity" not in data
            and b"SuppliedFaultInvariant" not in data
        ), path


def test_roadmap_localizes_historical_absence_and_the_s03_proposition() -> None:
    text = (ROOT / "docs/roadmap.md").read_text()
    s01 = " ".join(
        text.split("## S1.P07 — Pattern & Invariant Model\n", 1)[1]
        .split("### S1.P07.S02", 1)[0]
        .split()
    )
    s02 = " ".join(
        text.split("### S1.P07.S02", 1)[1].split("### S1.P07.S03", 1)[0].split()
    )
    s03 = " ".join(
        text.split("### S1.P07.S03 — Supplied invariant proposition\n", 1)[1]
        .split("### S1.P07.S04", 1)[0]
        .split("The `S1.P07` route", 1)[0]
        .split()
    )
    assert "No invariant exists in the S01 module." in s01
    assert "The S02 module adds no invariant representation." in s02
    assert "No invariant exists yet." not in s01
    for phrase in (
        "FaultInvariantIdentity",
        "SuppliedFaultInvariant",
        "reusable property",
        "not its truth",
        "opaque text",
        "no promotion",
        "no relationships",
    ):
        assert phrase in s03, phrase
    current = " ".join(text.split("## Current status", 1)[1].split("## ", 1)[0].split())
    assert "`S1.P07.S03` is complete" in current
    assert "`S1.P07.S05` is next and not started" in current
    assert "`S1.P07` is active and incomplete" in current


@pytest.fixture(scope="module")
def distributions(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, Path]:
    output = tmp_path_factory.mktemp("invariant-distributions")
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


def test_exact24_tracked_checkout_and_distribution_source_bytes(
    distributions: tuple[Path, Path],
) -> None:
    expected = sorted([*BASELINE_PRODUCTION, MODULE, INVARIANT_RELATIONSHIP_MODULE])
    assert len(expected) == 24
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
    with zipfile.ZipFile(distributions[0]) as z:
        names = [n for n in z.namelist() if not n.endswith("/")]
        assert sorted("src/" + n for n in names if n.endswith(".py")) == expected
        for p in expected:
            assert z.read(p.removeprefix("src/")) == (ROOT / p).read_bytes()
    with tarfile.open(distributions[1]) as t:
        members = [m for m in t.getmembers() if m.isfile()]
        assert (
            sorted(m.name.split("/", 1)[1] for m in members if m.name.endswith(".py"))
            == expected
        )
        for m in members:
            if m.name.endswith(".py"):
                stream = t.extractfile(m)
                assert stream is not None
                assert stream.read() == (ROOT / m.name.split("/", 1)[1]).read_bytes()
        names.extend(m.name for m in members)
    for name in names:
        assert not {"docs", "tests", "reference_corpus"}.intersection(
            Path(name).parts
        ), name


def test_uv_installed_wheel_round_trip_and_import_provenance(
    distributions: tuple[Path, Path], tmp_path: Path
) -> None:
    installed = tmp_path / "installed"
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
            str(distributions[0]),
        ],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    script = """
import json, sys, uuid
from pathlib import Path
installed = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(installed))
import faultatlas.domain.invariant as module
assert Path(module.__file__).resolve().is_relative_to(installed)
identity = module.FaultInvariantIdentity(uuid.UUID(sys.argv[2]))
assert module.FaultInvariantIdentity.model_validate_json(identity.model_dump_json()) == identity
value = module.SuppliedFaultInvariant(invariant=identity, invariant_statement=sys.argv[3])
assert module.SuppliedFaultInvariant.model_validate_json(value.model_dump_json()) == value
print(json.dumps({"module": module.__file__, "value": value.model_dump(mode="json")}))
"""
    result = subprocess.run(
        [sys.executable, "-I", "-c", script, str(installed), str(SCALAR), STATEMENT],
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
    assert receipt["value"] == {
        "invariant": str(SCALAR),
        "invariant_statement": STATEMENT,
    }


# Immutable production bytes at the accepted S02 squash d8f3cc74.
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
    "src/faultatlas/domain/pattern_exemplar.py": "b330f1187667843e7392e71d5efa8a6bd18fa0df43d7c5849266ca96b68fb770",
    "src/faultatlas/domain/revision.py": "7bea28086b345f6c1b4eeebe9c483924e60521e2f3e78954b272ab3c42acacaa",
    "src/faultatlas/domain/snapshot.py": "3807eb6e1552bfd97c3bedd7ca6fe8bfe7351f0ff3bc8205afdbad69c7f3e5fd",
    "src/faultatlas/domain/snapshot_evidence_link.py": "a87b7ed338a74127bd490803a958316bbc2598989cbbf3b0534174bc2b9cd59d",
    "src/faultatlas/domain/source.py": "034e53fd58212f0e34376bbc790fc3e74057031aaed4d7d89fb67904bdd380bf",
}
