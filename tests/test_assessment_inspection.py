"""Authored views and exact requested-basis rejection through the real consumer."""

from __future__ import annotations

import ast
import builtins
import copy
import json
import os
import socket
import subprocess
import sys
import time
import uuid
from pathlib import Path
from typing import Any, cast

import pytest
from test_supplied_assessment import fields, rich_wire, sample_wire, typed_sample

import faultatlas
import faultatlas.assessment as inspection
import faultatlas.domain as domain_package
from faultatlas.assessment import inspect_assessment
from faultatlas.domain.assessment import (
    AssessmentAttribution,
    AssessmentBasis,
    AssessmentCondition,
    SuppliedAssessment,
)

ROOT = Path(__file__).resolve().parents[1]
# Literal expected output, authored from the accepted fields and labels.
EXPECTED_VIEW = """Supplied assessment - structural inspection only
Source pattern: "00000000-0000-4000-8000-000000000001"
Source statement: "Repeated evaluation may repeat a side effect."
Target snapshot: {"repository":{"schema_version":1,"provider":"github","provider_repository_id":"1001"},"revision":{"schema_version":1,"kind":"commit","algorithm":"sha1","full_digest":"1111111111111111111111111111111111111111"}}
Host/visibility: caller-declared "github.com" / "public"; not externally verified
Path scope: not supplied; no whole-repository coverage inferred
Context: not supplied
Assessment supplier: "Example author"
Rationale: "Synthetic input for a structural review."
Root attribution covers assembly, context and condition inventory; source authorship and authentication are not established.
Condition "once": "A side-effecting expression is evaluated no more than once."
Materials: not supplied
Opinion "op-a": caller position="unknown", supplier="Reviewer A"
Statement: "No target run or inspected target material was supplied."
Rationale: "The evaluation count cannot be established from this file."
Condition reference: {"key":"once","statement":"A side-effecting expression is evaluated no more than once."}
Material keys: []
Conflicts: none supplied; no absence-of-conflict claim
Overall opinion: not supplied; none inferred
Structural checks: passed; no applicability or repair certification
End of complete view
"""


def test_complete_view_is_independently_authored_and_pure() -> None:
    value = typed_sample()
    assert inspection.__all__ == ["inspect_assessment"]
    assert not hasattr(faultatlas, "SuppliedAssessment") and not hasattr(
        domain_package, "SuppliedAssessment"
    )
    before = value.model_dump_json()
    assert inspect_assessment(value.basis, value) == EXPECTED_VIEW
    assert value.model_dump_json() == before
    reconstructed = SuppliedAssessment.model_validate_json(json.dumps(sample_wire()))
    assert inspect_assessment(value.basis, reconstructed) == EXPECTED_VIEW


@pytest.mark.parametrize(
    "change",
    [
        "source",
        "revision",
        "scope",
        "host",
        "context",
        "condition_text",
        "condition_set",
        "condition_order",
        "material_text",
        "material_attribution",
        "omission",
    ],
)
def test_full_requested_basis_rejects_independently_valid_changes(change: str) -> None:
    wire = rich_wire()
    wire["basis"]["conditions"].append(
        {"key": "second", "statement": "Second condition."}
    )
    # Every altered basis is independently valid before the consumer compares it.
    original = SuppliedAssessment.model_validate_json(json.dumps(wire))
    changed = copy.deepcopy(wire["basis"])
    if change == "source":
        changed["source"]["pattern_statement"] = "Different text under the same UUID."
    elif change == "revision":
        changed["target"]["snapshot"]["revision"]["full_digest"] = "2" * 40
    elif change == "scope":
        changed["target"]["scope"] = {
            "snapshot": copy.deepcopy(changed["target"]["snapshot"]),
            "declared_paths": [],
        }
    elif change == "host":
        # Host/public have only one admitted literal each: a different declaration
        # fails its owner, so this axis is not an independently valid basis.
        changed["target"]["declared_host"] = "ghe.example"
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            AssessmentBasis.model_validate_json(json.dumps(changed))
        return
    elif change == "context":
        changed["context_statement"] = "Supplied different runtime context."
    elif change == "condition_text":
        changed["conditions"][0]["statement"] = "Different under the same key."
    elif change == "condition_set":
        changed["conditions"].append({"key": "third", "statement": "New condition."})
    elif change == "condition_order":
        changed["conditions"].reverse()
    elif change == "material_text":
        changed["materials"][0]["description"] = (
            "Different material under the same key."
        )
    elif change == "material_attribution":
        changed["materials"][0]["attribution"]["supplier"] = "Different supplier"
    else:
        changed["materials"] = None
        changed["material_omission"] = "Explicitly omitted now."
    basis = AssessmentBasis.model_validate_json(json.dumps(changed))
    assert basis != original.basis
    with pytest.raises(
        ValueError, match="^assessment basis does not match requested basis$"
    ):
        inspect_assessment(basis, original)
    # A newly supplied complete assessment for that basis is legal. It need not
    # reuse the old opinions or pretend a reassessment actually occurred.
    new = SuppliedAssessment(attribution=original.attribution, basis=basis)
    assert inspect_assessment(basis, new).endswith("End of complete view\n")


@pytest.mark.parametrize("which", ["basis", "assessment"])
@pytest.mark.parametrize("wrong", [None, {}, "text", 1])
def test_consumer_does_not_coerce_wrong_parameter_types(which: str, wrong: Any) -> None:
    value = typed_sample()
    with pytest.raises(
        ValueError,
        match=f"^{which} must be an AssessmentBasis$"
        if which == "basis"
        else "^assessment must be a SuppliedAssessment$",
    ):
        inspect_assessment(
            cast(AssessmentBasis, wrong) if which == "basis" else value.basis,
            cast(SuppliedAssessment, wrong) if which == "assessment" else value,
        )


def test_consumer_revalidates_unchecked_nested_values() -> None:
    from pydantic import ValidationError

    value = typed_sample()
    bad = AssessmentAttribution.model_construct(supplier="", rationale="r")
    invalid_data = fields(value)
    invalid_data["attribution"] = bad
    invalid = SuppliedAssessment.model_construct(**invalid_data)
    with pytest.raises(ValidationError) as failure:
        inspect_assessment(value.basis, invalid)
    assert failure.value.errors()[0]["loc"] == ("attribution", "supplier")


def test_no_opinion_supplied_is_view_only_and_conditions_keep_order() -> None:
    value = typed_sample()
    extra = AssessmentCondition(key="second", statement="Still no opinion.")
    basis = AssessmentBasis.model_validate(
        fields(value.basis) | {"conditions": (extra, *value.basis.conditions)}
    )
    assessment = SuppliedAssessment.model_validate(fields(value) | {"basis": basis})
    view = inspect_assessment(basis, assessment)
    assert (
        'Condition "second": "Still no opinion."\nNo opinion supplied\nCondition "once"'
        in view
    )
    assert (
        len(assessment.opinions) == 1 and assessment.opinions[0].position == "unknown"
    )
    assert view.count("No opinion supplied") == 1


def test_every_material_reference_and_distinct_attribution_survives() -> None:
    wire = rich_wire()
    wire["basis"]["context_statement"] = " Context "
    wire["basis"]["target"]["scope"] = {
        "snapshot": copy.deepcopy(wire["basis"]["target"]["snapshot"]),
        "declared_paths": ["src/a.py", "src/b.py"],
    }
    value = SuppliedAssessment.model_validate_json(json.dumps(wire))
    view = inspect_assessment(value.basis, value)
    assert 'Context: " Context "' in view
    assert '"declared_paths":["src/a.py","src/b.py"]' in view
    assert 'Material "unused": "Supplied inline note."' in view
    record_line = next(
        line.removeprefix("Record reference: ")
        for line in view.splitlines()
        if line.startswith("Record reference: ")
    )
    assert json.loads(record_line) == wire["basis"]["materials"][0]["record"]
    for name in (
        "Example author",
        "Material supplier",
        "Reviewer A",
        "Reviewer B",
        "Conflict supplier",
        "Overall supplier",
    ):
        assert f'"{name}"' in view
    assert (
        "verified by our upstream script" in view
        and 'Overall caller opinion: "applicable"' in view
    )
    assert 'Conflict 1: left="op-a", right="op-b"; caller declaration' in view
    assert 'Conflict 2: left="op-a", right="op-b"; caller declaration' in view
    assert view.index('Opinion "op-a"') < view.index('Opinion "op-b"')
    assert "no applicability or repair certification" in view


@pytest.mark.parametrize(
    ("materials", "omission", "expected"),
    [
        (None, None, "Materials: not supplied"),
        (
            None,
            " Missing deliberately ",
            "Materials: explicitly omitted by the assessment assembler",
        ),
        (
            [],
            None,
            "Materials: caller-declared empty inventory; no world-level absence inferred",
        ),
    ],
)
def test_optional_information_is_visible_without_changing_target(
    materials: Any, omission: Any, expected: str
) -> None:
    wire = sample_wire()
    wire["basis"]["materials"] = materials
    wire["basis"]["material_omission"] = omission
    value = SuppliedAssessment.model_validate_json(json.dumps(wire))
    view = inspect_assessment(value.basis, value)
    assert expected in view
    if omission is not None:
        assert 'Omission reason: " Missing deliberately "' in view
    assert value.basis.target.snapshot.repository.provider_repository_id.root == "1001"


@pytest.mark.parametrize(
    ("text", "escaped"),
    [
        ("\n", '"\\n"'),
        ("\t", '"\\t"'),
        ("\x1b]8;;https://x", '"\\u001b]8;;https://x"'),
        ("\x7f", '"\\u007f"'),
        ("\u202e", '"\\u202e"'),
        ("α", '"\\u03b1"'),
        ("\\", '"\\\\"'),
    ],
)
def test_untrusted_text_is_recoverably_escaped(text: str, escaped: str) -> None:
    # Raw whitespace-only inputs are invalid: surround them without changing
    # their content, and assert a literal expected escape in the resulting line.
    supplied = "A" + text + "B"
    quoted = '"A' + escaped[1:-1] + 'B"'
    wire = sample_wire()
    wire["attribution"]["rationale"] = supplied
    value = SuppliedAssessment.model_validate_json(json.dumps(wire))
    view = inspect_assessment(value.basis, value)
    assert "Rationale: " + quoted in view
    assert json.loads(quoted) == supplied
    assert (
        view.isascii()
        and all(ord(c) >= 32 or c == "\n" for c in view)
        and "\x7f" not in view
    )
    assert value.attribution.rationale == supplied


def test_view_byte_cap_has_exact_boundary_and_no_partial_success(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    value = typed_sample()
    assert getattr(inspection, "_MAX_VIEW_BYTES") == 8 * 1024 * 1024
    size = len(EXPECTED_VIEW.encode("utf-8"))
    monkeypatch.setattr(inspection, "_MAX_VIEW_BYTES", size)
    assert inspect_assessment(value.basis, value) == EXPECTED_VIEW
    monkeypatch.setattr(inspection, "_MAX_VIEW_BYTES", size - 1)
    with pytest.raises(ValueError, match="inspection output budget"):
        inspect_assessment(value.basis, value)


def test_operations_do_not_read_execute_print_or_allocate_ids(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    wire = json.dumps(rich_wire())
    value = SuppliedAssessment.model_validate_json(wire)
    expected = inspect_assessment(value.basis, value)

    def denied(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("unexpected external operation")

    with monkeypatch.context() as blocked:
        for obj, name in [
            (builtins, "open"),
            (builtins, "print"),
            (Path, "open"),
            (os, "getenv"),
            (os, "stat"),
            (time, "time"),
            (time, "monotonic"),
            (socket, "socket"),
            (subprocess, "Popen"),
            (uuid, "uuid4"),
        ]:
            blocked.setattr(obj, name, denied)
        reentered = SuppliedAssessment.model_validate(value)
        from_json = SuppliedAssessment.model_validate_json(wire)
        actual = inspect_assessment(reentered.basis, from_json)
    assert actual == expected


def test_bounded_dependency_and_execution_surface() -> None:
    expected = {
        "src/faultatlas/domain/assessment.py": {
            "json",
            "re",
            "functools",
            "typing",
            "pydantic",
            "faultatlas.domain.evidence",
            "faultatlas.domain.invariant",
            "faultatlas.domain.pattern",
            "faultatlas.domain.snapshot",
        },
        "src/faultatlas/assessment.py": {
            "json",
            "typing",
            "faultatlas.domain.assessment",
        },
    }
    for path, imports in expected.items():
        tree = ast.parse((ROOT / path).read_text())
        observed = {
            n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)
        } | {
            a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names
        }
        assert observed == imports
        assert not {
            "__eq__",
            "__hash__",
            "model_validate",
            "model_validate_json",
        }.intersection(n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef))
        called = {
            n.func.id
            for n in ast.walk(tree)
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
        }
        assert not called & {"open", "print", "eval", "exec", "compile", "__import__"}


def test_installed_wheel_authored_vertical_and_provenance(
    offline_distributions: tuple[Path, Path], tmp_path: Path
) -> None:
    installed = tmp_path / "installed"
    env = os.environ | {"UV_OFFLINE": "1", "UV_CACHE_DIR": str(tmp_path / "cache")}
    result = subprocess.run(
        [
            "uv",
            "pip",
            "install",
            "--offline",
            "--no-deps",
            "--target",
            str(installed),
            str(offline_distributions[0]),
        ],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    probe = """
import json,pathlib,sys
installed=pathlib.Path(sys.argv[1]).resolve()
sys.path.insert(0,str(installed))
from faultatlas.domain.assessment import SuppliedAssessment
from faultatlas.assessment import inspect_assessment
wire=json.loads(sys.argv[2]);value=SuppliedAssessment.model_validate_json(sys.argv[2])
assert value.model_dump(mode="json")==wire
assert inspect_assessment(value.basis,value)==sys.argv[3]
assert SuppliedAssessment.model_validate_json(value.model_dump_json())==value
for name,module in tuple(sys.modules.items()):
    if name=="faultatlas" or name.startswith("faultatlas."):
        assert pathlib.Path(module.__file__).resolve().is_relative_to(installed),name
print("installed assessment authored vertical PASS")
"""
    result = subprocess.run(
        [
            sys.executable,
            "-I",
            "-B",
            "-c",
            probe,
            str(installed),
            json.dumps(sample_wire()),
            EXPECTED_VIEW,
        ],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.strip() == "installed assessment authored vertical PASS"


def test_contract_retains_exact_source_records_and_future_budget_boundary() -> None:
    import re

    doc = (ROOT / "docs/contracts/s1-p08-s01-supplied-assessment.md").read_text()
    selections = [
        (
            "reference_corpus/pytest-4412/closures/s1-p00-phase-closure/closure.json",
            "/deferred_register/items",
            [10, 23],
        ),
        (
            "reference_corpus/contracts/identity/closures/s1-p01-phase-closure/closure.json",
            "/deferred_register/items",
            [29, 30, 31, 32, 37, 38],
        ),
        (
            "reference_corpus/contracts/revision-locator/closures/s1-p02-phase-closure/closure.json",
            "/deferred_register/items",
            [24, 35, 36, 37, 38],
        ),
        (
            "reference_corpus/contracts/evidence-envelope/closures/s1-p03-phase-closure/closure.json",
            "/deferred_register/entries",
            [3, 4],
        ),
    ]
    expected: list[tuple[str, str, Any]] = []
    for path, pointer, indices in selections:
        data = json.loads((ROOT / path).read_text())
        for part in pointer.strip("/").split("/"):
            data = data[part]
        expected.extend(
            (path, pointer + "/" + str(index), data[index]) for index in indices
        )
    p07 = "reference_corpus/contracts/pattern-invariant/closures/s1-p07-phase-closure/closure.json"
    expected.append(
        (
            p07,
            "/empirical_review",
            json.loads((ROOT / p07).read_text())["empirical_review"],
        )
    )
    found = re.findall(
        r"`(reference_corpus/[^`#]+)#([^`]+)`\n\n```json\n(.*?)\n```", doc, re.S
    )
    assert [
        (path, pointer, json.loads(text)) for path, pointer, text in found
    ] == expected
    for text in (
        "8198/513/131125/33",
        "body remains8192/512/131072/32",
        "two upstream",
        "3116",
        "becomes effective only on S01 publication",
        "P03 deferred:05 is not completed by S01 alone.",
        "No opinion supplied",
    ):
        assert text in doc, text
