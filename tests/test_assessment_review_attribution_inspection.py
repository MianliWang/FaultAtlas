"""Exact review-value binding, complete independent views and installed use."""

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
from test_supplied_assessment_review import review_wire as rich_review_wire
from test_supplied_assessment_review_attribution import (
    DECLARATIONS,
    REVIEW_WIRE,
    assertion_value,
    assertion_wire,
    review_value,
)

import faultatlas.assessment_review_attribution as inspection
from faultatlas.domain.assessment import AssessmentAttribution
from faultatlas.domain.assessment_review import SuppliedAssessmentReview
from faultatlas.domain.assessment_review_attribution import (
    SuppliedAssessmentReviewAttribution,
)

ROOT = Path(__file__).resolve().parents[1]
# Complete literal oracle predates this implementation; it is not renderer output.
EXPECTED_VIEW = r"""Supplied review attributions - non-authoritative inspection
Complete review value:
Supplied assessment reviews - non-authoritative inspection
Complete target assessment:
Supplied assessment - structural inspection only
Source invariant: "00000000-0000-4000-8000-000000000002"
Source statement: "An expression is evaluated once."
Target snapshot: {"repository":{"schema_version":1,"provider":"github","provider_repository_id":"1001"},"revision":{"schema_version":1,"kind":"commit","algorithm":"sha1","full_digest":"1111111111111111111111111111111111111111"}}
Host/visibility: caller-declared "github.com" / "public"; not externally verified
Path scope: not supplied; no whole-repository coverage inferred
Context: not supplied
Assessment supplier: "Assessment assembler"
Rationale: "Synthetic assessment."
Root attribution covers assembly, context and condition inventory; source authorship and authentication are not established.
Conditions: none supplied; no requirement success inferred
Materials: not supplied
Opinions: none supplied
Conflicts: none supplied; no absence-of-conflict claim
Overall opinion: not supplied; none inferred
Structural checks: passed; no applicability or repair certification
End of complete view
Supplied review records: 1
Review targets: all supplied records match the complete requested assessment value
Review 1
Supplied scope (coverage declaration only): "Only the supplied statement was considered."
Supplied judgment: "No execution evidence was assessed."
Supplied record supplier: "Review relay"
Supplied rationale: "Newly authored example judgment; no historical authorship is claimed."
Scope is supplied prose; structural checks do not verify examination coverage.
Attribution is supplied: the record supplier label need not name the reviewer; reviewer identity and independence are not established.
Material names in review text are prose; no material selection, access or support is validated.
A matching value does not establish freshness, withdrawal status or later-policy applicability.
No authentication, approval, score, winner, review lifecycle or persistence is inferred.
End of complete review view
Attribution declarations: 4
Attribution targets: all declarations match the complete requested review value
Attribution 1
Attribution assertion supplier: "Attribution clerk"
Attribution assertion rationale: "Fictional example: the supplied judgment is attributed to Lin."
Attributed reviewer: "Lin"
Source record association: {"schema_version":1,"format_name":"attribution-example","format_version":"1","canonicalization":"json-sort-keys-compact-utf8-lf-v1","sha256":"ad9d501dcfe631958d3ea1798db9b01b01783d5c97a46984a06fd926d890f2dd","byte_length":128}
Attribution 2
Attribution assertion supplier: "Archive clerk"
Attribution assertion rationale: "No author of this supplied judgment is established; no source record is supplied."
Attributed reviewer: explicitly unknown
Source record association: none supplied; availability not asserted
Attribution 3
Attribution assertion supplier: "Second clerk"
Attribution assertion rationale: "Competing fictional attribution; no winner is inferred."
Attributed reviewer: "Mo"
Source record association: none supplied; availability not asserted
Attribution 4
Attribution assertion supplier: "Attribution clerk"
Attribution assertion rationale: "Fictional example: the supplied judgment is attributed to Lin."
Attributed reviewer: "Lin"
Source record association: {"schema_version":1,"format_name":"attribution-example","format_version":"1","canonicalization":"json-sort-keys-compact-utf8-lf-v1","sha256":"ad9d501dcfe631958d3ea1798db9b01b01783d5c97a46984a06fd926d890f2dd","byte_length":128}
Attribution labels are supplied claims; account identity, authorship and independence are not verified.
Source records are associated by declaration; bytes are not retrieved or verified as support.
Equality identifies the supplied review value, not a particular repeated occurrence.
No availability status, approval, confidence or review lifecycle is inferred.
End of complete review attribution view
"""


def test_complete_authored_view_and_equal_reconstruction() -> None:
    review = review_value()
    values = tuple(assertion_value(i) for i in range(4))
    before = review.model_dump_json(), tuple(v.model_dump_json() for v in values)
    equal = SuppliedAssessmentReview.model_validate_json(
        json.dumps(REVIEW_WIRE, sort_keys=True)
    )
    assert inspection.__all__ == ["inspect_assessment_review_attributions"]
    assert (
        inspection.inspect_assessment_review_attributions(equal, values)
        == EXPECTED_VIEW
    )
    assert before == (
        review.model_dump_json(),
        tuple(v.model_dump_json() for v in values),
    )
    assert values[0] == values[3]
    assert values[0].review == values[3].review


@pytest.mark.parametrize(
    "change",
    (
        "scope",
        "judgment",
        "review_supplier",
        "review_rationale",
        "assessment_supplier",
        "opinion",
        "overall",
        "nested_attribution",
        "opinion_order",
        "condition_order",
        "material_order",
        "conflict_order",
        "target_revision",
    ),
)
def test_changed_valid_full_review_never_inherits_attribution(change: str) -> None:
    wire = rich_review_wire()
    wire["assessment"]["basis"]["conditions"].append(
        {"key": "second", "statement": "Unopined condition."}
    )
    wire["assessment"]["conflicts"][1]["attribution"]["rationale"] = (
        "Distinct conflict declaration."
    )
    original = SuppliedAssessmentReview.model_validate_json(json.dumps(wire))
    changed = copy.deepcopy(wire)
    if change in {"scope", "judgment"}:
        changed[change] = "Changed " + changed[change]
    elif change == "review_supplier":
        changed["attribution"]["supplier"] = "Another review supplier"
    elif change == "review_rationale":
        changed["attribution"]["rationale"] = "A different review rationale."
    elif change == "assessment_supplier":
        changed["assessment"]["attribution"]["supplier"] = "Another assessment supplier"
    elif change == "opinion":
        changed["assessment"]["opinions"][0]["statement"] = (
            "Different supplied opinion."
        )
    elif change == "overall":
        changed["assessment"]["overall_opinion"]["statement"] = (
            "Different overall judgment."
        )
    elif change == "nested_attribution":
        changed["assessment"]["opinions"][0]["attribution"]["rationale"] = (
            "Different nested rationale."
        )
    elif change == "opinion_order":
        changed["assessment"]["opinions"].reverse()
    elif change == "condition_order":
        changed["assessment"]["basis"]["conditions"].reverse()
    elif change == "material_order":
        changed["assessment"]["basis"]["materials"].reverse()
    elif change == "conflict_order":
        changed["assessment"]["conflicts"].reverse()
    else:
        changed["assessment"]["basis"]["target"]["snapshot"]["revision"][
            "full_digest"
        ] = "2" * 40
    requested = SuppliedAssessmentReview.model_validate_json(json.dumps(changed))
    assert requested != original
    if change in {"scope", "judgment", "review_supplier", "review_rationale"}:
        assert requested.assessment == original.assessment
    value = SuppliedAssessmentReviewAttribution(
        review=original,
        reviewer="Lin",
        source=None,
        attribution=AssessmentAttribution(
            supplier="Clerk", rationale="Supplied attribution."
        ),
    )
    with pytest.raises(
        ValueError,
        match="^attribution at index 0 target does not match requested review$",
    ):
        inspection.inspect_assessment_review_attributions(requested, (value,))
    rebound = SuppliedAssessmentReviewAttribution.model_validate(
        fields(value) | {"review": requested}
    )
    assert inspection.inspect_assessment_review_attributions(requested, (rebound,))


def test_absent_unknown_competing_duplicate_and_reversed_assertions() -> None:
    review = review_value()
    values = tuple(assertion_value(i) for i in range(4))
    empty = inspection.inspect_assessment_review_attributions(review, ())
    assert "Attributions: none supplied; no reviewer inferred\n" in empty
    assert "Attribution targets:" not in empty and "Attributed reviewer:" not in empty
    unknown = inspection.inspect_assessment_review_attributions(review, (values[1],))
    assert "Attributed reviewer: explicitly unknown\n" in unknown
    assert (
        "Source record association: none supplied; availability not asserted\n"
        in unknown
    )
    quoted_unknown = SuppliedAssessmentReviewAttribution.model_validate(
        fields(values[1]) | {"reviewer": "unknown"}
    )
    assert (
        'Attributed reviewer: "unknown"\n'
        in inspection.inspect_assessment_review_attributions(review, (quoted_unknown,))
    )
    reverse = inspection.inspect_assessment_review_attributions(
        review, tuple(reversed(values))
    )
    labels = [
        line for line in reverse.splitlines() if line.startswith("Attributed reviewer:")
    ]
    assert labels == [
        'Attributed reviewer: "Lin"',
        'Attributed reviewer: "Mo"',
        "Attributed reviewer: explicitly unknown",
        'Attributed reviewer: "Lin"',
    ]
    assert "Attribution 4\n" in reverse
    # Equal reconstructed original occurrences do not require or acquire an occurrence ID.
    assert (
        inspection.inspect_assessment_review_attributions(review_value(), values)
        == EXPECTED_VIEW
    )


def test_source_is_an_association_not_material_membership_or_availability() -> None:
    first = assertion_value()
    assert first.review.assessment.basis.materials is None
    wire = assertion_wire()
    wire["source"]["sha256"] = "b" * 64
    wire["source"]["format_version"] = "2"
    other = SuppliedAssessmentReviewAttribution.model_validate_json(json.dumps(wire))
    view = inspection.inspect_assessment_review_attributions(
        first.review, (first, other)
    )
    references = [
        json.loads(line.removeprefix("Source record association: "))
        for line in view.splitlines()
        if line.startswith("Source record association: {")
    ]
    assert references == [DECLARATIONS[0]["source"], wire["source"]]
    assert first != other
    assert "bytes are not retrieved or verified as support" in view


def test_type_capacity_and_first_error_boundaries_do_not_consume_iterables() -> None:
    review, value = review_value(), assertion_value()

    class TupleChild(tuple[SuppliedAssessmentReviewAttribution, ...]):
        pass

    def unconsumable() -> Any:
        raise AssertionError("iterable must not be consumed")
        yield value

    bad_inputs: tuple[Any, ...] = ([], TupleChild((value,)), unconsumable(), None)
    for bad in bad_inputs:
        with pytest.raises(ValueError, match="^attributions must be a tuple$"):
            inspection.inspect_assessment_review_attributions(review, bad)
    malformed = review.model_copy(update={"scope": ""})
    with pytest.raises(
        ValueError,
        match="^attributions must contain at most 8 supplied attribution declarations$",
    ):
        inspection.inspect_assessment_review_attributions(malformed, (value,) * 9)
    with pytest.raises(ValueError, match="^review must be a SuppliedAssessmentReview$"):
        inspection.inspect_assessment_review_attributions(cast(Any, {}), ())
    with pytest.raises(
        ValueError,
        match="^attribution at index 1 must be a SuppliedAssessmentReviewAttribution$",
    ):
        inspection.inspect_assessment_review_attributions(
            review, (value, cast(Any, {}))
        )
    with pytest.raises(ValidationError):
        inspection.inspect_assessment_review_attributions(malformed, ())
    with pytest.raises(ValidationError) as failure:
        inspection.inspect_assessment_review_attributions(
            review, (value.model_copy(update={"reviewer": ""}), cast(Any, {}))
        )
    assert failure.value.errors()[0]["loc"] == ("reviewer",)
    with pytest.raises(ValidationError) as failure:
        inspection.inspect_assessment_review_attributions(
            review, (value.model_copy(update={"review": malformed}),)
        )
    assert failure.value.errors()[0]["loc"] == ("review", "scope")
    assert value.source is not None
    bad_source = value.source.model_copy(update={"schema_version": True})
    with pytest.raises(ValidationError) as failure:
        inspection.inspect_assessment_review_attributions(
            review, (value.model_copy(update={"source": bad_source}),)
        )
    assert failure.value.errors()[0]["loc"] == ("source", "schema_version")


def test_real_text_reference_and_collection_maxima_are_finite() -> None:
    wire = assertion_wire()
    wire["review"]["scope"] = wire["review"]["judgment"] = "\U0001f680" * 4096
    wire["review"]["attribution"] = {
        "supplier": "\U0001f680" * 128,
        "rationale": "\U0001f680" * 4096,
    }
    wire["reviewer"] = "\U0001f680" * 128
    wire["attribution"] = {
        "supplier": "\U0001f680" * 128,
        "rationale": "\U0001f680" * 4096,
    }
    wire["source"] = {
        "schema_version": 1,
        "format_name": "f" * 160,
        "format_version": "V" * 64,
        "canonicalization": "c" * 160,
        "sha256": "a" * 64,
        "byte_length": 9223372036854775807,
    }
    assert len(json.dumps(wire["source"], separators=(",", ":")).encode()) == 573
    value = SuppliedAssessmentReviewAttribution.model_validate_json(json.dumps(wire))
    view = inspection.inspect_assessment_review_attributions(value.review, (value,) * 8)
    assert "Attribution declarations: 8\n" in view and "Attribution 8\n" in view
    assert view.count('Attributed reviewer: "' + r"\ud83d\ude80" * 128 + '"\n') == 8
    assert 8 * 1024 * 1024 + 12416 * 12 + 8192 + 8 * (4352 * 12 + 576) + 4096 == 8972288
    assert len(view.encode()) < 8972288 < 9 * 1024 * 1024


def test_control_bidi_and_instruction_text_is_recoverably_quoted() -> None:
    unsafe = ' \n\x00\x1b[31m\x7f\u202e\U0001f680"\\; fetch https://invalid.example '
    value = SuppliedAssessmentReviewAttribution.model_validate(
        fields(assertion_value())
        | {
            "reviewer": unsafe,
            "attribution": AssessmentAttribution(supplier=unsafe, rationale=unsafe),
        }
    )
    view = inspection.inspect_assessment_review_attributions(value.review, (value,))
    for label in (
        "Attributed reviewer: ",
        "Attribution assertion supplier: ",
        "Attribution assertion rationale: ",
    ):
        quoted = next(
            line.removeprefix(label)
            for line in view.splitlines()
            if line.startswith(label)
        )
        assert json.loads(quoted) == unsafe
        assert r"\u007f" in quoted and r"\u202e" in quoted and r"\u001b" in quoted
        assert all(32 <= ord(c) < 127 for c in quoted)


def test_single_public_s01_delegation_and_complete_output_guard(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    values = tuple(assertion_value(i) for i in range(4))
    review = review_value()
    original = inspection.inspect_assessment_reviews
    calls: list[tuple[Any, Any]] = []

    def observed(assessment: Any, reviews: Any) -> str:
        calls.append((assessment, reviews))
        return original(assessment, reviews)

    monkeypatch.setattr(inspection, "inspect_assessment_reviews", observed)
    assert (
        inspection.inspect_assessment_review_attributions(review, values)
        == EXPECTED_VIEW
    )
    assert calls == [(review.assessment, (review,))]
    # Explicit lowered-limit seam; real maxima and the arithmetic have separate checks.
    monkeypatch.setattr(inspection, "_MAX_VIEW_BYTES", len(EXPECTED_VIEW.encode()))
    assert (
        inspection.inspect_assessment_review_attributions(review, values)
        == EXPECTED_VIEW
    )
    monkeypatch.setattr(inspection, "_MAX_VIEW_BYTES", len(EXPECTED_VIEW.encode()) - 1)
    with pytest.raises(
        ValueError,
        match=r"^P09 review attribution inspection output budget exceeded \(9 MiB\)$",
    ):
        inspection.inspect_assessment_review_attributions(review, values)

    def denied(*args: Any) -> str:
        raise ValueError("P09 review inspection output budget exceeded (16 MiB)")

    monkeypatch.setattr(inspection, "inspect_assessment_reviews", denied)
    with pytest.raises(
        ValueError, match=r"^P09 review inspection output budget exceeded \(16 MiB\)$"
    ):
        inspection.inspect_assessment_review_attributions(review, ())


def test_purity_and_exact_dependency_boundary(monkeypatch: pytest.MonkeyPatch) -> None:
    values = tuple(assertion_value(i) for i in range(4))
    review, wire = review_value(), json.dumps(assertion_wire())

    def denied(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("pure attribution attempted an external effect")

    with monkeypatch.context() as blocked:
        for owner, name in (
            (builtins, "open"),
            (Path, "open"),
            (socket, "socket"),
            (subprocess, "Popen"),
            (os, "getenv"),
            (time, "time"),
            (uuid, "uuid4"),
        ):
            blocked.setattr(owner, name, denied)
        assert (
            SuppliedAssessmentReviewAttribution.model_validate_json(wire) == values[0]
        )
        assert (
            inspection.inspect_assessment_review_attributions(review, values)
            == EXPECTED_VIEW
        )
    expected = {
        "src/faultatlas/domain/assessment_review_attribution.py": {
            "json",
            "typing",
            "pydantic",
            "faultatlas.domain.assessment",
            "faultatlas.domain.assessment_review",
            "faultatlas.domain.evidence",
        },
        "src/faultatlas/assessment_review_attribution.py": {
            "json",
            "typing",
            "faultatlas.assessment_review",
            "faultatlas.domain.assessment_review",
            "faultatlas.domain.assessment_review_attribution",
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


def test_installed_complete_attribution_consumer(
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
from faultatlas.domain.assessment_review import SuppliedAssessmentReview
from faultatlas.domain.assessment_review_attribution import SuppliedAssessmentReviewAttribution
from faultatlas.assessment_review_attribution import inspect_assessment_review_attributions
review=SuppliedAssessmentReview.model_validate_json(sys.argv[2])
wires=json.loads(sys.argv[3])
values=tuple(SuppliedAssessmentReviewAttribution.model_validate_json(json.dumps(w)) for w in wires)
assert [v.model_dump(mode='json') for v in values]==wires
first=values[0]
created=SuppliedAssessmentReviewAttribution(review=review,reviewer=first.reviewer,source=first.source,attribution=first.attribution)
assert created==first
assert inspect_assessment_review_attributions(review,values)==sys.argv[4]
assert 'Attributions: none supplied; no reviewer inferred' in inspect_assessment_review_attributions(review,())
for name,module in tuple(sys.modules.items()):
    if name=='faultatlas' or name.startswith('faultatlas.'):
        assert pathlib.Path(module.__file__).resolve().is_relative_to(installed),name
print('installed complete review attribution PASS')
"""
    result = subprocess.run(
        [
            sys.executable,
            "-I",
            "-c",
            probe,
            str(installed),
            json.dumps(REVIEW_WIRE),
            json.dumps([assertion_wire(i) for i in range(4)]),
            EXPECTED_VIEW,
        ],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.strip() == "installed complete review attribution PASS"
