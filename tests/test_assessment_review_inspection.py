"""Complete authored views, exact-target refusal, and an installed pure consumer."""

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
from pydantic import ValidationError
from test_supplied_assessment import fields

import faultatlas.assessment_review as inspection
from faultatlas.domain.assessment import AssessmentAttribution, SuppliedAssessment
from faultatlas.domain.assessment_review import SuppliedAssessmentReview

ROOT = Path(__file__).resolve().parents[1]
# Authored calibration design values and text; no runtime external evidence dependency.
PATTERN_WIRE: dict[str, Any] = json.loads(r"""
{
  "attribution": {
    "supplier": "Example assembler",
    "rationale": "Newly authored design input; no original source review is asserted."
  },
  "basis": {
    "source": {
      "pattern": "00000000-0000-4000-8000-000000000001",
      "pattern_statement": "Repeated evaluation may repeat a side effect."
    },
    "target": {
      "snapshot": {
        "repository": {
          "schema_version": 1,
          "provider": "github",
          "provider_repository_id": "1001"
        },
        "revision": {
          "schema_version": 1,
          "kind": "commit",
          "algorithm": "sha1",
          "full_digest": "1111111111111111111111111111111111111111"
        }
      },
      "declared_host": "github.com",
      "declared_visibility": "public",
      "scope": null
    },
    "context_statement": "Local prose-only design example.",
    "conditions": [
      {
        "key": "once",
        "statement": "A side-effecting expression is evaluated no more than once."
      }
    ],
    "materials": [
      {
        "key": "material-a",
        "description": "A declared note with an unavailable body.",
        "attribution": {
          "supplier": "Material supplier",
          "rationale": "This reference is a declaration."
        },
        "record": {
          "schema_version": 1,
          "format_name": "synthetic-note",
          "format_version": "1",
          "canonicalization": "json-sort-keys-compact-utf8-lf-v1",
          "sha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
          "byte_length": 1
        },
        "locator": "https://invalid.example/note"
      },
      {
        "key": "unused",
        "description": "A second, unselected note.",
        "attribution": {
          "supplier": "Other material supplier",
          "rationale": "No examination is claimed."
        },
        "record": null,
        "locator": null
      }
    ],
    "material_omission": null
  },
  "opinions": [
    {
      "key": "op-a",
      "condition": {
        "key": "once",
        "statement": "A side-effecting expression is evaluated no more than once."
      },
      "position": "unknown",
      "statement": "The evaluation count is unknown.",
      "attribution": {
        "supplier": "Opinion supplier A",
        "rationale": "No target execution is supplied."
      },
      "material_keys": []
    },
    {
      "key": "op-b",
      "condition": {
        "key": "once",
        "statement": "A side-effecting expression is evaluated no more than once."
      },
      "position": "stated",
      "statement": "The condition holds.",
      "attribution": {
        "supplier": "Opinion supplier B",
        "rationale": "This is a supplied claim only."
      },
      "material_keys": [
        "material-a"
      ]
    }
  ],
  "conflicts": [
    {
      "left_opinion_key": "op-a",
      "right_opinion_key": "op-b",
      "attribution": {
        "supplier": "Conflict supplier",
        "rationale": "The assembler declares a disagreement."
      }
    },
    {
      "left_opinion_key": "op-a",
      "right_opinion_key": "op-b",
      "attribution": {
        "supplier": "Conflict supplier",
        "rationale": "The assembler declares a disagreement."
      }
    }
  ],
  "overall_opinion": {
    "statement": "Applicability remains unknown.",
    "attribution": {
      "supplier": "Overall supplier",
      "rationale": "No technical certification is supplied."
    }
  }
}
""")

INVARIANT_WIRE: dict[str, Any] = json.loads(r"""
{
  "attribution": {
    "supplier": "Invariant assembler",
    "rationale": "Independent authored contrast with no supplied reviews."
  },
  "basis": {
    "source": {
      "invariant": "00000000-0000-4000-8000-000000000002",
      "invariant_statement": "An expression is evaluated once."
    },
    "target": {
      "snapshot": {
        "repository": {
          "schema_version": 1,
          "provider": "github",
          "provider_repository_id": "1001"
        },
        "revision": {
          "schema_version": 1,
          "kind": "commit",
          "algorithm": "sha1",
          "full_digest": "1111111111111111111111111111111111111111"
        }
      },
      "declared_host": "github.com",
      "declared_visibility": "public",
      "scope": null
    },
    "context_statement": null,
    "conditions": [],
    "materials": null,
    "material_omission": null
  },
  "opinions": [],
  "conflicts": [],
  "overall_opinion": null
}
""")

PATTERN_VIEW = r"""Supplied assessment reviews - non-authoritative inspection
Complete target assessment:
Supplied assessment - structural inspection only
Source pattern: "00000000-0000-4000-8000-000000000001"
Source statement: "Repeated evaluation may repeat a side effect."
Target snapshot: {"repository":{"schema_version":1,"provider":"github","provider_repository_id":"1001"},"revision":{"schema_version":1,"kind":"commit","algorithm":"sha1","full_digest":"1111111111111111111111111111111111111111"}}
Host/visibility: caller-declared "github.com" / "public"; not externally verified
Path scope: not supplied; no whole-repository coverage inferred
Context: "Local prose-only design example."
Assessment supplier: "Example assembler"
Rationale: "Newly authored design input; no original source review is asserted."
Root attribution covers assembly, context and condition inventory; source authorship and authentication are not established.
Condition "once": "A side-effecting expression is evaluated no more than once."
Material "material-a": "A declared note with an unavailable body."
Supplier: "Material supplier"
Rationale: "This reference is a declaration."
Record reference: {"schema_version":1,"format_name":"synthetic-note","format_version":"1","canonicalization":"json-sort-keys-compact-utf8-lf-v1","sha256":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","byte_length":1}
Locator: "https://invalid.example/note"
References are supplied, not loaded or verified as support.
Material "unused": "A second, unselected note."
Supplier: "Other material supplier"
Rationale: "No examination is claimed."
Record reference: not supplied
Locator: not supplied
References are supplied, not loaded or verified as support.
Opinion "op-a": caller position="unknown", supplier="Opinion supplier A"
Statement: "The evaluation count is unknown."
Rationale: "No target execution is supplied."
Condition reference: {"key":"once","statement":"A side-effecting expression is evaluated no more than once."}
Material keys: []
Opinion "op-b": caller position="stated", supplier="Opinion supplier B"
Statement: "The condition holds."
Rationale: "This is a supplied claim only."
Condition reference: {"key":"once","statement":"A side-effecting expression is evaluated no more than once."}
Material keys: ["material-a"]
Conflict 1: left="op-a", right="op-b"; caller declaration
Supplier: "Conflict supplier"
Rationale: "The assembler declares a disagreement."
Conflict 2: left="op-a", right="op-b"; caller declaration
Supplier: "Conflict supplier"
Rationale: "The assembler declares a disagreement."
Overall caller opinion: "Applicability remains unknown."
Supplier: "Overall supplier"
Rationale: "No technical certification is supplied."
Structural checks: passed; no applicability or repair certification
End of complete view
Supplied review records: 3
Review targets: all supplied records match the complete requested assessment value
Review 1
Supplied scope (coverage declaration only): "I examined the condition inventory only."
Supplied judgment: "The assessment is adequate for that declared scope."
Supplied record supplier: "Example record supplier"
Supplied rationale: "Newly authored statement attributed to Reviewer One; identity is not established."
Review 2
Supplied scope (coverage declaration only): "I examined the condition inventory only."
Supplied judgment: "The assessment is not adequate; material-a was not examined."
Supplied record supplier: "Example record supplier"
Supplied rationale: "Newly authored statement attributed to Reviewer Two; identity is not established."
Review 3
Supplied scope (coverage declaration only): "I examined the condition inventory only."
Supplied judgment: "The assessment is adequate for that declared scope."
Supplied record supplier: "Example record supplier"
Supplied rationale: "Newly authored statement attributed to Reviewer One; identity is not established."
Scope is supplied prose; structural checks do not verify examination coverage.
Attribution is supplied: the record supplier label need not name the reviewer; reviewer identity and independence are not established.
Material names in review text are prose; no material selection, access or support is validated.
A matching value does not establish freshness, withdrawal status or later-policy applicability.
No authentication, approval, score, winner, review lifecycle or persistence is inferred.
End of complete review view
"""

INVARIANT_VIEW = r"""Supplied assessment reviews - non-authoritative inspection
Complete target assessment:
Supplied assessment - structural inspection only
Source invariant: "00000000-0000-4000-8000-000000000002"
Source statement: "An expression is evaluated once."
Target snapshot: {"repository":{"schema_version":1,"provider":"github","provider_repository_id":"1001"},"revision":{"schema_version":1,"kind":"commit","algorithm":"sha1","full_digest":"1111111111111111111111111111111111111111"}}
Host/visibility: caller-declared "github.com" / "public"; not externally verified
Path scope: not supplied; no whole-repository coverage inferred
Context: not supplied
Assessment supplier: "Invariant assembler"
Rationale: "Independent authored contrast with no supplied reviews."
Root attribution covers assembly, context and condition inventory; source authorship and authentication are not established.
Conditions: none supplied; no requirement success inferred
Materials: not supplied
Opinions: none supplied
Conflicts: none supplied; no absence-of-conflict claim
Overall opinion: not supplied; none inferred
Structural checks: passed; no applicability or repair certification
End of complete view
Supplied review records: 0
Reviews: none supplied; no review judgment inferred
Scope is supplied prose; structural checks do not verify examination coverage.
Attribution is supplied: the record supplier label need not name the reviewer; reviewer identity and independence are not established.
Material names in review text are prose; no material selection, access or support is validated.
A matching value does not establish freshness, withdrawal status or later-policy applicability.
No authentication, approval, score, winner, review lifecycle or persistence is inferred.
End of complete review view
"""


def _assessment(wire: dict[str, Any] = PATTERN_WIRE) -> SuppliedAssessment:
    return SuppliedAssessment.model_validate_json(json.dumps(wire))


def _reviews(value: SuppliedAssessment) -> tuple[SuppliedAssessmentReview, ...]:
    first = SuppliedAssessmentReview(
        assessment=value,
        scope="I examined the condition inventory only.",
        judgment="The assessment is adequate for that declared scope.",
        attribution=AssessmentAttribution(
            supplier="Example record supplier",
            rationale="Newly authored statement attributed to Reviewer One; identity is not established.",
        ),
    )
    second = SuppliedAssessmentReview(
        assessment=value,
        scope=first.scope,
        judgment="The assessment is not adequate; material-a was not examined.",
        attribution=AssessmentAttribution(
            supplier="Example record supplier",
            rationale="Newly authored statement attributed to Reviewer Two; identity is not established.",
        ),
    )
    return first, second, first


def test_complete_independent_views_and_equal_reconstruction() -> None:
    value = _assessment()
    reviews = _reviews(value)
    before = value.model_dump_json(), tuple(r.model_dump_json() for r in reviews)
    assert inspection.__all__ == ["inspect_assessment_reviews"]
    assert inspection.inspect_assessment_reviews(_assessment(), reviews) == PATTERN_VIEW
    assert (
        inspection.inspect_assessment_reviews(_assessment(INVARIANT_WIRE), ())
        == INVARIANT_VIEW
    )
    assert before == (
        value.model_dump_json(),
        tuple(r.model_dump_json() for r in reviews),
    )
    # Full duplicate and contrary records survive; positional numbering is not identity.
    assert reviews[0] == reviews[2] and reviews[0] != reviews[1]


@pytest.mark.parametrize(
    "change",
    (
        "source",
        "root_attribution",
        "opinion",
        "overall",
        "nested_attribution",
        "opinion_order",
        "material_order",
        "condition_order",
        "conflict_order",
        "absent_empty",
        "absent_omitted",
    ),
)
def test_independently_valid_full_target_changes_mismatch(change: str) -> None:
    wire = copy.deepcopy(PATTERN_WIRE)
    wire["basis"]["conditions"].append(
        {"key": "second", "statement": "Unopined condition."}
    )
    wire["conflicts"][1]["attribution"]["rationale"] = "A separately stated conflict."
    if change in {"absent_empty", "absent_omitted"}:
        wire["basis"]["materials"] = None
        wire["opinions"][1]["material_keys"] = []
    original = _assessment(wire)
    changed = copy.deepcopy(wire)
    if change == "source":
        changed["basis"]["source"]["pattern_statement"] = (
            "Different proposition under the same UUID."
        )
    elif change == "root_attribution":
        changed["attribution"]["rationale"] = "Different assembly rationale."
    elif change == "opinion":
        changed["opinions"][0]["statement"] = "Different opinion outside the basis."
    elif change == "overall":
        changed["overall_opinion"]["statement"] = "A different overall judgment."
    elif change == "nested_attribution":
        changed["opinions"][0]["attribution"]["supplier"] = "Different supplied label."
    elif change == "opinion_order":
        changed["opinions"].reverse()
    elif change == "material_order":
        changed["basis"]["materials"].reverse()
    elif change == "condition_order":
        changed["basis"]["conditions"].reverse()
    elif change == "conflict_order":
        changed["conflicts"].reverse()
    elif change == "absent_empty":
        changed["basis"]["materials"] = []
    else:
        changed["basis"]["material_omission"] = "Explicitly omitted by supplier."
    requested = _assessment(changed)
    assert original != requested
    if change in {
        "root_attribution",
        "opinion",
        "overall",
        "nested_attribution",
        "opinion_order",
        "conflict_order",
    }:
        assert requested.basis == original.basis
    with pytest.raises(
        ValueError,
        match="^review at index 0 target does not match requested assessment$",
    ):
        inspection.inspect_assessment_reviews(requested, _reviews(original))
    assert inspection.inspect_assessment_reviews(requested, _reviews(requested))


def test_no_category_material_access_or_freshness_is_inferred() -> None:
    value = _assessment()
    record = _reviews(value)[0]
    judgments = (
        "unknown",
        "unsupported: material-not-in-target",
        "negative",
        "approved 100",
    )
    reviews = tuple(
        SuppliedAssessmentReview.model_validate(fields(record) | {"judgment": text})
        for text in judgments
    )
    view = inspection.inspect_assessment_reviews(_assessment(), reviews)
    assert [
        json.loads(line.removeprefix("Supplied judgment: "))
        for line in view.splitlines()
        if line.startswith("Supplied judgment: ")
    ] == list(judgments)
    reverse = inspection.inspect_assessment_reviews(value, tuple(reversed(reviews)))
    assert [
        json.loads(line.removeprefix("Supplied judgment: "))
        for line in reverse.splitlines()
        if line.startswith("Supplied judgment: ")
    ] == list(reversed(judgments))
    empty = inspection.inspect_assessment_reviews(value, ())
    assert "Reviews: none supplied; no review judgment inferred" in empty
    assert "Review targets:" not in empty and "Supplied judgment:" not in empty


def test_tuple_and_capacity_guards_precede_iteration_and_revalidation() -> None:
    value = _assessment()
    record = _reviews(value)[0]

    class TupleChild(tuple[SuppliedAssessmentReview, ...]):
        pass

    def forbidden_iterator() -> Any:
        raise AssertionError("iterator must not be consumed")
        yield record

    wrong_inputs: tuple[Any, ...] = (
        [],
        TupleChild((record,)),
        forbidden_iterator(),
        None,
    )
    for wrong in wrong_inputs:
        with pytest.raises(ValueError, match="^reviews must be a tuple$"):
            inspection.inspect_assessment_reviews(value, wrong)
    invalid = value.model_copy(update={"attribution": None})
    with pytest.raises(
        ValueError, match="^reviews must contain at most 32 supplied reviews$"
    ):
        inspection.inspect_assessment_reviews(invalid, (record,) * 33)
    with pytest.raises(ValueError, match="^assessment must be a SuppliedAssessment$"):
        inspection.inspect_assessment_reviews(cast(Any, {}), ())
    with pytest.raises(
        ValueError, match="^review at index 1 must be a SuppliedAssessmentReview$"
    ):
        inspection.inspect_assessment_reviews(value, (record, cast(Any, {})))
    with pytest.raises(ValidationError):
        inspection.inspect_assessment_reviews(invalid, ())
    bad = record.model_copy(update={"scope": ""})
    with pytest.raises(ValidationError) as failure:
        inspection.inspect_assessment_reviews(value, (bad, cast(Any, {})))
    assert failure.value.errors()[0]["loc"] == ("scope",)


def test_revalidation_reaches_review_target_before_matching() -> None:
    value = _assessment()
    record = _reviews(value)[0]
    bad = value.model_copy(update={"overall_opinion": "not a typed opinion"})
    with pytest.raises(ValidationError) as failure:
        inspection.inspect_assessment_reviews(
            value, (record.model_copy(update={"assessment": bad}),)
        )
    assert failure.value.errors()[0]["loc"][:2] == ("assessment", "overall_opinion")


def test_quoted_unicode_and_maximum_records_and_text() -> None:
    value = _assessment(INVARIANT_WIRE)
    text = "\U0001f680" * 4096
    record = SuppliedAssessmentReview(
        assessment=value,
        scope=text,
        judgment=text,
        attribution=AssessmentAttribution(supplier="\U0001f680" * 128, rationale=text),
    )
    view = inspection.inspect_assessment_reviews(value, (record,) * 32)
    assert "Supplied review records: 32\n" in view and "\nReview 32\n" in view
    assert view.count('Supplied judgment: "' + r"\ud83d\ude80" * 4096 + '"\n') == 32
    assert len(view.encode()) < 13_164_544 < 16_777_216
    unsafe = ' \n\t\x1b[31m\x7f\u202e\U0001f680"\\; open https://invalid.example '
    small = SuppliedAssessmentReview.model_validate(fields(record) | {"scope": unsafe})
    rendered = inspection.inspect_assessment_reviews(value, (small,))
    line = next(
        line for line in rendered.splitlines() if line.startswith("Supplied scope (")
    )
    quoted = line.split(": ", 1)[1]
    assert json.loads(quoted) == unsafe
    assert r"\u007f" in quoted and r"\u202e" in quoted and r"\u001b" in quoted
    assert all(ord(c) < 128 and ord(c) >= 32 for c in quoted)


def test_complete_output_guard_and_public_target_delegation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    value = _assessment()
    original = inspection.inspect_assessment
    called: list[SuppliedAssessment] = []

    def public_view(basis: Any, target: SuppliedAssessment) -> str:
        called.append(target)
        return original(basis, target)

    monkeypatch.setattr(inspection, "inspect_assessment", public_view)
    assert inspection.inspect_assessment_reviews(value, _reviews(value)) == PATTERN_VIEW
    assert called == [value]
    monkeypatch.setattr(inspection, "_MAX_VIEW_BYTES", len(PATTERN_VIEW.encode()) - 1)
    with pytest.raises(
        ValueError, match=r"^P09 review inspection output budget exceeded \(16 MiB\)$"
    ):
        inspection.inspect_assessment_reviews(value, _reviews(value))

    def target_rejection(*args: Any) -> str:
        raise ValueError("P08 inspection output budget exceeded (8 MiB)")

    monkeypatch.setattr(inspection, "inspect_assessment", target_rejection)
    with pytest.raises(
        ValueError, match=r"^P08 inspection output budget exceeded \(8 MiB\)$"
    ):
        inspection.inspect_assessment_reviews(value, ())


def test_pure_operations_and_static_import_boundary(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    value = _assessment()
    reviews = _reviews(value)
    wire = reviews[0].model_dump_json()

    def denied(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("unexpected effect in pure review operations")

    with monkeypatch.context() as blocked:
        for obj, name in (
            (builtins, "open"),
            (Path, "open"),
            (socket, "socket"),
            (subprocess, "Popen"),
            (time, "time"),
            (uuid, "uuid4"),
            (os, "getenv"),
        ):
            blocked.setattr(obj, name, denied)
        assert SuppliedAssessmentReview.model_validate_json(wire) == reviews[0]
        assert inspection.inspect_assessment_reviews(value, reviews) == PATTERN_VIEW
    expected = {
        "src/faultatlas/domain/assessment_review.py": {
            "json",
            "typing",
            "pydantic",
            "faultatlas.domain.assessment",
        },
        "src/faultatlas/assessment_review.py": {
            "json",
            "typing",
            "faultatlas.assessment",
            "faultatlas.domain.assessment",
            "faultatlas.domain.assessment_review",
        },
    }
    for path, imports in expected.items():
        tree = ast.parse((ROOT / path).read_bytes())
        observed = {
            n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)
        } | {
            a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names
        }
        assert observed == imports
        assert not {"__eq__", "__hash__", "model_validate", "model_validate_json"} & {
            n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)
        }


def test_installed_complete_review_consumer(
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
    value = _assessment()
    # Wire starts from the explicitly authored assessment, not production output.
    wire = [
        dict(
            assessment=copy.deepcopy(PATTERN_WIRE),
            scope=r.scope,
            judgment=r.judgment,
            attribution={
                "supplier": r.attribution.supplier,
                "rationale": r.attribution.rationale,
            },
        )
        for r in _reviews(value)
    ]
    probe = """
import json,pathlib,sys
installed=pathlib.Path(sys.argv[1]).resolve()
sys.path.insert(0,str(installed))
from faultatlas.domain.assessment import SuppliedAssessment, AssessmentAttribution
from faultatlas.domain.assessment_review import SuppliedAssessmentReview
from faultatlas.assessment_review import inspect_assessment_reviews
assessment=SuppliedAssessment.model_validate_json(sys.argv[2])
reviews=tuple(SuppliedAssessmentReview.model_validate_json(json.dumps(r)) for r in json.loads(sys.argv[3]))
assert inspect_assessment_reviews(assessment,reviews)==sys.argv[4]
first=reviews[0]
created=SuppliedAssessmentReview(assessment=assessment,scope=first.scope,judgment=first.judgment,attribution=AssessmentAttribution(supplier=first.attribution.supplier,rationale=first.attribution.rationale))
assert created==first
invariant=SuppliedAssessment.model_validate_json(sys.argv[5])
assert inspect_assessment_reviews(invariant,())==sys.argv[6]
for name,module in tuple(sys.modules.items()):
    if name=='faultatlas' or name.startswith('faultatlas.'):
        assert pathlib.Path(module.__file__).resolve().is_relative_to(installed),name
print('installed supplied review complete views PASS')
"""
    result = subprocess.run(
        [
            sys.executable,
            "-I",
            "-c",
            probe,
            str(installed),
            json.dumps(PATTERN_WIRE),
            json.dumps(wire),
            PATTERN_VIEW,
            json.dumps(INVARIANT_WIRE),
            INVARIANT_VIEW,
        ],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.strip() == "installed supplied review complete views PASS"
