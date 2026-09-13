"""Sealed S07 decision assurance; no live lifecycle or corpus executor ownership."""

from __future__ import annotations

import copy
import hashlib
import importlib
import json
from pathlib import Path
from typing import Any, cast

import pytest
from _repository_contract import P07_SURFACE

# Required historical responsibility-to-owner mappings. The shared inventory
# supplies current module ownership; future additional exports are not forbidden.
SURFACE_WITNESSES = {
    "FaultPatternIdentity": "pattern_surface",
    "SuppliedFaultPattern": "pattern_surface",
    "FaultPatternExemplarAssociation": "exemplar_surface",
    "FaultInvariantIdentity": "invariant_surface",
    "SuppliedFaultInvariant": "invariant_surface",
    "FaultPatternInvariantAssociation": "pattern_invariant_surface",
    "FaultInvariantExpectedPropertyAssociation": "invariant_expected_surface",
    "FaultPatternComposition": "composition_defaults",
}

ROOT = Path(__file__).resolve().parents[1]
DECISION = (
    ROOT
    / "reference_corpus/contracts/pattern-invariant/decisions/s07-deferred-subject-disposition-readiness"
)
BASELINE = "fc8b00cd5b909fe52ba34b45be1ff245fdb21bb2"
DIGEST = "8937e1a896d8d4a78f01ce82878d478318b853532f90d9b93192f22d976ae237"
BYTE_LENGTH = 22947
EMPIRICAL = "gap:s05-known:cross-repository-pattern-and-transfer-not-established"
GENERALITY = "deferred:p01:p07-pattern-generality"
# Finite historical source boundary, not a mutable production inventory.
INPUT_PATHS = {
    "acquisition_correction": "reference_corpus/pytest-4412/corrections/s04-c01-acquisition-closure/correction.json",
    "case": "reference_corpus/pytest-4412/case/case.json",
    "gap_matrix": "reference_corpus/pytest-4412/analysis/s06-current-contract-gap-matrix/gap-matrix.json",
    "identity_correction": "reference_corpus/contracts/identity/corrections/s05-c01-ambiguous-union-round-trip/correction.json",
    "identity_decision": "reference_corpus/pytest-4412/decisions/s07-identity-revision-provenance/decision.json",
    "identity_vectors": "reference_corpus/contracts/identity/corrections/s05-c01-ambiguous-union-round-trip/regression-vectors.json",
    "p00": "reference_corpus/pytest-4412/closures/s1-p00-phase-closure/closure.json",
    "p01": "reference_corpus/contracts/identity/closures/s1-p01-phase-closure/closure.json",
    "p02": "reference_corpus/contracts/revision-locator/closures/s1-p02-phase-closure/closure.json",
    "p03": "reference_corpus/contracts/evidence-envelope/closures/s1-p03-phase-closure/closure.json",
    "p04": "reference_corpus/contracts/repository-snapshot/closures/s1-p04-phase-closure/closure.json",
    "p04_decision": "reference_corpus/contracts/repository-snapshot/decisions/s08-deferred-subject-disposition/decision.json",
    "p05": "reference_corpus/contracts/development-history/closures/s1-p05-phase-closure/closure.json",
    "p05_correction": "reference_corpus/contracts/development-history/corrections/s08-c01-deferred-subject-owner-topology/correction.json",
    "p05_decision": "reference_corpus/contracts/development-history/decisions/s08-deferred-subject-disposition/decision.json",
    "p06": "reference_corpus/contracts/fault-instance/closures/s1-p06-phase-closure/closure.json",
    "p06_decision": "reference_corpus/contracts/fault-instance/decisions/s10-deferred-subject-disposition-readiness/decision.json",
    "snapshot_decision": "reference_corpus/pytest-4412/decisions/s08-snapshot-boundary-compatibility/decision.json",
}

# Native pytest nodes observed at BASELINE; these are references, not execution receipts.
WITNESSES = {
    "V1": "tests/test_fault_pattern_vertical.py::test_two_repository_composition_matches_authored_payload",
    "V2": "tests/test_fault_pattern_vertical.py::test_exemplars_and_expectation_chains_are_explicit",
    "V3": "tests/test_fault_pattern_vertical.py::test_wrong_case_property_fails_at_membership_owner[case_b_property]",
    "V4": "tests/test_fault_pattern_vertical.py::test_repetition_order_and_separate_roots_remain_local",
    "V5": "tests/test_fault_pattern_vertical.py::test_competing_claims_survive_composition",
    "V6": "tests/test_fault_pattern_vertical.py::test_case_evidence_link_does_not_propagate",
    "V7": "tests/test_fault_pattern_vertical.py::test_invalid_nested_child_revalidates_at_its_owner",
    "attachment": "tests/test_fault_pattern_composition.py::test_root_attachment_and_repeated_explicit_relations[json]",
    "composition_defaults": "tests/test_fault_pattern_composition.py::test_exact_surface_defaults_and_config",
    "exemplar_surface": "tests/test_fault_pattern_exemplar.py::test_exact_surface_and_configuration",
    "full_member": "tests/test_fault_invariant_relationship.py::test_full_record_equal_member_qualifies_without_object_identity",
    "invariant_expected_surface": "tests/test_fault_invariant_relationship.py::test_exact_surface_config_and_authored_full_wire[FaultInvariantExpectedPropertyAssociation-fields1]",
    "invariant_identity": "tests/test_fault_invariant.py::test_uuid_policy_and_bare_json_round_trip[scalar0]",
    "invariant_surface": "tests/test_fault_invariant.py::test_exact_surface_configuration_and_independent_bases",
    "invariant_text": "tests/test_fault_invariant.py::test_invalid_text_is_refused_during_python_and_json_validation[ "
    "\\t\\n-value_error]",
    "invariant_uniqueness": "tests/test_fault_pattern_composition.py::test_duplicate_invariant_identity_refused[False-json]",
    "json": "tests/test_fault_pattern_composition.py::test_full_authored_wire_and_reentry[json]",
    "order": "tests/test_fault_pattern_composition.py::test_order_is_preserved_and_changes_value_equality[exemplar_associations]",
    "package": "tests/test_package.py::test_offline_build_excludes_reference_corpus_and_historical_license",
    "pattern_invariant_surface": "tests/test_fault_invariant_relationship.py::test_exact_surface_config_and_authored_full_wire[FaultPatternInvariantAssociation-fields0]",
    "pattern_surface": "tests/test_fault_pattern.py::test_the_module_publishes_exactly_two_symbols_in_order",
    "pattern_text": "tests/test_fault_pattern.py::test_the_character_limit_is_inclusive_and_one_more_is_refused",
    "python_children": "tests/test_fault_pattern_composition.py::test_python_children_are_typed[foreign-False-exemplar_associations]",
    "wheel": "tests/test_fault_pattern_composition.py::test_installed_wheel_provenance_and_authored_json",
}
ROOTS = {
    "p03": ("model", "/deferred_register/entries/3", "deferred_id", "deferred:04"),
    "p00": ("empirical", "/deferred_register/items/23", "deferred_item_id", EMPIRICAL),
    "p01": (
        "generality",
        "/deferred_register/items/37",
        "deferred_item_id",
        GENERALITY,
    ),
}


def _select(document: Any, pointer: str) -> Any:
    assert pointer.startswith("/"), "source selector must be an absolute JSON pointer"
    for token in pointer.split("/")[1:]:
        token = token.replace("~1", "/").replace("~0", "~")
        document = (
            cast(list[Any], document)[int(token)]
            if isinstance(document, list)
            else document[token]
        )
    return document


def _no_number(value: str) -> Any:
    raise ValueError("non-integer JSON number is forbidden: " + value)


def _canonical(document: dict[str, Any]) -> bytes:
    return (
        json.dumps(
            document,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def _decode(raw: bytes) -> dict[str, Any]:
    document: dict[str, Any] = json.loads(
        raw.decode("utf-8"), parse_float=_no_number, parse_constant=_no_number
    )
    assert _canonical(document) == raw, "noncanonical decision bytes"
    return document


def _document() -> dict[str, Any]:
    return _decode((DECISION / "decision.json").read_bytes())


def _render(document: dict[str, Any]) -> str:
    lines = [
        "# S1.P07.S07 — Deferred Disposition and Corpus Readiness",
        "",
        "This is a sealed publication candidate. JSON is the sole semantic authority.",
        "",
        "Baseline: `" + document["identity"]["baseline_commit"] + "`.",
        document["identity"]["observation_semantics"],
        "Whole-Phase planning audit: "
        + document["identity"]["whole_phase_planning_audit"]
        + ".",
        "",
        "## Effective source-qualified subjects",
        "",
    ]
    for subject in document["subjects"]:
        source = subject["source"]
        entry = document["inputs"][source["input"]]
        pointer = entry["selectors"][source["selection"]]["pointer"]
        lines += [
            "### `" + subject["id"] + "`",
            "",
            "Source: `" + entry["path"] + "#" + pointer + "`.",
            "Original: " + subject["original_meaning"],
            "Effective: " + subject["effective_meaning"],
            "Disposition: `" + subject["disposition"] + "`.",
            "Witnesses: "
            + ", ".join("`" + x + "`" for x in subject["witnesses"])
            + ".",
        ]
        remainder: dict[str, Any] | None = subject["remainder"]
        if remainder is None:
            lines += [
                "No remaining model-representation responsibility in this bounded disposition."
            ]
        else:
            lines += [
                remainder["question"],
                "State: `"
                + remainder["state"]
                + "`; owner: `"
                + remainder["owner"]
                + "`.",
                "Reason: " + remainder["reason"],
                "Revisit: `" + remainder["revisit"] + "`.",
                "Handoff: `" + remainder["handoff"] + "`.",
            ]
        lines += [""]
    lines += [
        "## Input census and exclusions",
        "",
        document["census"]["boundary"],
        document["census"]["count_scope"],
        "`" + json.dumps(document["census"]["summary"], sort_keys=True) + "`.",
        "",
    ]
    lines += ["- " + item["reason"] for item in document["census"]["non_subjects"]]
    lines += [
        "",
        "## Immutable source references",
        "",
        "| Input | Path | SHA-256 / bytes | Selectors |",
        "| --- | --- | --- | --- |",
    ]
    for key, value in sorted(document["inputs"].items()):
        selectors = "; ".join(
            label + ": " + selection["pointer"]
            for label, selection in sorted(value["selectors"].items())
        )
        lines.append(
            f"| {key} | `{value['path']}` | `{value['sha256']}` / {value['byte_length']} | {selectors or 'bounded search only'} |"
        )
    lines += [
        "",
        "Only SHA-256, byte length and the selected JSON content are verified; no Git blob/mode claim is made.",
        "",
        "## Published S01–S05 responsibility snapshot",
        "",
        "| Symbol | Module | Slice | Witness |",
        "| --- | --- | --- | --- |",
    ]
    for row in document["surface"]:
        lines.append(
            "| "
            + " | ".join(
                "`" + row[k] + "`" for k in ("symbol", "module", "slice", "witness")
            )
            + " |"
        )
    lines += ["", "## Existing collected witness references", ""]
    lines += [
        f"- `{key}`: `{value}`" for key, value in sorted(document["witnesses"].items())
    ]
    lines += [
        "",
        "Collection establishes node availability at the baseline. Successful execution requires matching external validation evidence.",
        "",
        "## Conditional S08 authoring readiness",
        "",
        "`" + document["readiness"]["verdict"] + "`.",
        document["readiness"]["purpose"],
    ]
    for key, requirement in sorted(document["readiness"]["requirements"].items()):
        lines += [
            "- "
            + key
            + ": "
            + requirement["requirement"]
            + " Witnesses: "
            + ", ".join(requirement["witnesses"])
            + "."
        ]
    lines += [
        document["readiness"]["empirical_gate"],
        "Scheduled: `"
        + json.dumps(document["readiness"]["scheduled"], sort_keys=True)
        + "`.",
        "P07 closed: `" + str(document["readiness"]["p07_closed"]).lower() + "`.",
        "Audited product/readiness blockers: `"
        + json.dumps(document["readiness"]["product_readiness_blockers"])
        + "`.",
        "",
        "## Publication boundary",
        "",
        "`" + document["publication"]["state"] + "`.",
        "External condition: `" + document["publication"]["condition"] + "`.",
        "Evidence location: `" + document["publication"]["evidence_location"] + "`.",
        "",
        "## Retained limitations",
        "",
    ]
    for limitation in document["limitations"]:
        lines += ["- " + json.dumps(limitation, ensure_ascii=False, sort_keys=True)]
    return "\n".join(lines) + "\n"


def _assert_bytes(raw: bytes) -> None:
    _decode(raw)
    assert len(raw) == BYTE_LENGTH, "decision byte length"
    assert hashlib.sha256(raw).hexdigest() == DIGEST, "decision digest"


def _assert_view(document: dict[str, Any], markdown: str) -> None:
    assert markdown == _render(document), "derived Markdown mismatch"


def _assert_sources(
    document: dict[str, Any], raw_sources: dict[str, bytes]
) -> dict[str, Any]:
    assert set(document["inputs"]) == set(INPUT_PATHS), "finite source coverage"
    sources: dict[str, Any] = {}
    for key, path in INPUT_PATHS.items():
        record = document["inputs"][key]
        assert record["path"] == path, f"source path: {key}"
        raw = raw_sources[key]
        assert len(raw) == record["byte_length"], f"source byte length: {key}"
        assert hashlib.sha256(raw).hexdigest() == record["sha256"], (
            f"source digest: {key}"
        )
        source = json.loads(raw)
        sources[key] = source
        for label, selection in record["selectors"].items():
            selected = _select(source, selection["pointer"])
            assert all(
                selected.get(k) == v for k, v in selection["expected"].items()
            ), f"source selection: {key}:{label}"
    for key, (label, pointer, field, identifier) in ROOTS.items():
        selection = document["inputs"][key]["selectors"][label]
        assert selection["pointer"] == pointer, f"root selector: {key}"
        assert _select(sources[key], pointer)[field] == identifier, (
            f"root identity: {key}"
        )
    return sources


def _summary(subjects: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "source_qualified_entries": len(subjects),
        "implemented_reservations": sum(
            s["kind"] == "model_reservation" for s in subjects
        ),
        "empirical_entries": sum(s["kind"] == "empirical_unknown" for s in subjects),
        "p07_owned_empirical_entries": sum(
            s["remainder"] is not None and s["remainder"]["owner"] == "S1.P07"
            for s in subjects
        ),
    }


def _assert_subjects(document: dict[str, Any], sources: dict[str, Any]) -> None:
    # Positive finite scan of the actual closure registers, not a prose classifier.
    found: set[tuple[str, str]] = set()
    for key in ("p00", "p01", "p02", "p03", "p04", "p05", "p06"):
        register = sources[key]["deferred_register"]
        for row in register.get("items", register.get("entries", [])):
            owners = [
                row.get(field)
                for field in (
                    "owner",
                    "immediate_owner",
                    "immediate_next_owner",
                    "preserved_long_term_owner",
                    "preserved_long_term_phase_owner",
                )
            ]
            if "S1.P07" in owners:
                identifier = row.get(
                    "deferred_item_id", row.get("deferred_id", row.get("subject_id"))
                )
                assert isinstance(identifier, str), (
                    "P07 source has no qualified subject identity"
                )
                found.add((key, identifier))
    expected = {(key, row[3]) for key, row in ROOTS.items()}
    assert found == expected and found, "effective source census"
    subjects = document["subjects"]
    actual = [(s["source"]["input"], s["id"]) for s in subjects]
    assert len(actual) == len(set(actual)) and set(actual) == found, (
        "subject coverage/identity"
    )
    assert document["census"]["subject_source_keys"] == [
        key + ":" + identifier for key, identifier in actual
    ], "census subject references"
    for subject in subjects:
        key = subject["source"]["input"]
        assert subject["source"]["selection"] == ROOTS[key][0], "subject root reference"
        original = _select(sources[key], ROOTS[key][1])
        if key == "p03":
            assert original == {
                "deferred_id": "deferred:04",
                "implementation_state": "not_implemented",
                "owner": "S1.P07",
                "subject": "pattern_and_invariant_model",
            }, "original model reservation"
            assert (
                subject["kind"] == "model_reservation"
                and subject["disposition"] == "bounded_model_implemented"
                and subject["remainder"] is None
            ), "bounded model disposition"
            assert set(subject["witnesses"]) == set(SURFACE_WITNESSES.values()) | {
                f"V{i}" for i in range(1, 8)
            }, "model obligation witnesses"
            continue
        assert subject["kind"] == "empirical_unknown", (
            "empirical kind cannot be promoted"
        )
        assert subject["disposition"] == (
            "unknown_carried_forward"
            if key == "p00"
            else "unknown_retained_with_original_owner"
        ), "empirical unknown cannot be resolved by synthetic tests"
        remainder: dict[str, Any] | None = subject["remainder"]
        assert isinstance(remainder, dict), "empirical remainder required"
        assert remainder["state"] == original["current_state"], (
            "empirical state must remain unknown"
        )
        assert remainder["owner"] == (
            "S1.P08" if key == "p00" else original["immediate_next_owner"]
        ), "empirical remainder owner"
        assert remainder["reason"] == original["reason_for_deferral"], (
            "empirical evidence reason"
        )
        assert remainder["revisit"] == original["latest_decision_point"], (
            "empirical revisit condition"
        )
        assert remainder["question"].strip(), "remaining empirical question"
        assert remainder["handoff"] == (
            "additive_to_existing_long_term_owner_not_acceptance_or_completion"
            if key == "p00"
            else "none_original_owner_retained"
        ), "handoff boundary"
    empirical = next(s for s in subjects if s["id"] == EMPIRICAL)
    assert empirical["aliases"] == [
        {"input": "gap_matrix", "selection": "empirical_alias"},
        {"input": "case", "selection": "empirical_alias"},
    ], "empirical exact aliases"
    for key, pointer in (
        ("gap_matrix", "/gap_register/24"),
        ("case", "/known_gaps/24"),
    ):
        selectors = document["inputs"][key]["selectors"]
        assert "empirical_alias" in selectors, "empirical alias selector required"
        assert selectors["empirical_alias"]["pointer"] == pointer, (
            "empirical alias root"
        )
    assert sources["gap_matrix"]["gap_register"][24]["gap_id"] == EMPIRICAL
    assert (
        sources["case"]["known_gaps"][24]["id"]
        == "cross_repository_pattern_and_transfer_not_established"
    )
    wrong = sources["identity_decision"]["decision_register"]["register_items"][12]
    assert (
        wrong["register_id"] == "register:s07:cross-provider-mapping"
        and wrong["source_pointer"]["json_pointer"] == "/known_gaps/25"
    ), "excluded wrong-root reference"
    assert all(type(v) is int for v in document["census"]["summary"].values())
    assert document["census"]["summary"] == _summary(subjects), "derived subject counts"


def _assert_surface(document: dict[str, Any]) -> None:
    rows = document["surface"]
    assert len(rows) == len(SURFACE_WITNESSES) and {r["symbol"] for r in rows} == set(
        SURFACE_WITNESSES
    ), "required model mapping coverage"
    current_owner = {
        symbol: "faultatlas.domain." + module
        for module, symbols in P07_SURFACE
        for symbol in symbols
    }
    for row in rows:
        symbol = row["symbol"]
        assert row["module"] == current_owner[symbol], "model module owner"
        assert row["witness"] == SURFACE_WITNESSES[symbol], "model test owner"
        slice_owner = {
            "pattern_surface": "S1.P07.S01",
            "exemplar_surface": "S1.P07.S02",
            "invariant_surface": "S1.P07.S03",
            "pattern_invariant_surface": "S1.P07.S04",
            "invariant_expected_surface": "S1.P07.S04",
            "composition_defaults": "S1.P07.S05",
        }
        assert row["slice"] == slice_owner[row["witness"]], "model Slice owner"
        model = getattr(importlib.import_module(current_owner[symbol]), symbol)
        assert model.__module__ == current_owner[symbol], (
            "published symbol defining owner"
        )
    assert document["witnesses"] == WITNESSES, "collected witness mapping"


def _assert_readiness(document: dict[str, Any], sources: dict[str, Any]) -> None:
    # Sources and actual model ownership are checked first by _assert_semantics.
    handoff = sources["p05_correction"]["downstream_handoff"]["handoffs"][2]
    assert handoff["target"] == "S1.P06"
    assert (
        handoff["requirements"][0]["statement"]
        == "own_the_bounded_domain_relationship_vocabulary_needed_by_FaultInstance"
    )
    addressed = sources["p06"]["deferred_register"]["items"][0]
    assert (
        addressed["disposition"] == "addressed"
        and addressed["effective_scope"] == handoff["requirements"][0]["statement"]
    ), "corrected P06 ownership"
    assert len(sources["p06"]["entry_readiness"]["boundary"]) == 5
    readiness = document["readiness"]
    assert readiness["verdict"] == "eligible_to_author_after_S07_publication", (
        "conditional authoring readiness"
    )
    assert readiness["p07_closed"] is False and readiness["scheduled"] == {
        "S1.P07.S08": "not_started",
        "S1.P07.S09": "not_started",
    }, "scheduled work is not completed"
    assert readiness["product_readiness_blockers"] == [], (
        "audited product readiness blockers"
    )
    assert readiness["preserved_empirical_subjects"] == [EMPIRICAL, GENERALITY], (
        "readiness preserves both empirical records"
    )
    assert set(readiness["required_witnesses"]) == set(WITNESSES) and len(
        readiness["required_witnesses"]
    ) == len(WITNESSES), "readiness witness basis"
    required = {
        "authored_examples": {"json", "V1", "V3", "V7"},
        "provenance": {"V1", "V5", "V6"},
        "unknown_targets": {"package"},
        "source_only": {"package", "wheel"},
        "owner_failures": {"full_member", "python_children", "json", "V3", "V7"},
        "canonical_boundary": {"json", "order"},
    }
    assert set(readiness["requirements"]) == set(required), "S08 requirement coverage"
    for key, witnesses in required.items():
        assert set(readiness["requirements"][key]["witnesses"]) == witnesses, (
            "S08 requirement witness basis"
        )
    assert document["publication"] == {
        "state": "sealed_publication_candidate",
        "condition": "successful_S07_protected_publication_and_natural_main_verification",
        "evidence_location": "external_Git_GitHub_and_execution_receipt",
    }, "publication remains an external condition"
    assert document["identity"]["baseline_commit"] == BASELINE
    assert (
        document["identity"]["whole_phase_planning_audit"]
        == "not_established_by_this_slice"
    ), "no retrospective whole-Phase audit"


def _source_bytes() -> dict[str, bytes]:
    return {key: (ROOT / path).read_bytes() for key, path in INPUT_PATHS.items()}


def _assert_semantics(document: dict[str, Any]) -> None:
    sources = _assert_sources(document, _source_bytes())
    _assert_subjects(document, sources)
    _assert_surface(document)
    _assert_readiness(document, sources)


def test_canonical_digest_and_derived_markdown() -> None:
    raw = (DECISION / "decision.json").read_bytes()
    _assert_bytes(raw)
    _assert_view(_decode(raw), (DECISION / "decision.md").read_text(encoding="utf-8"))


def test_positive_source_dispositions_and_conditional_readiness() -> None:
    _assert_semantics(_document())


@pytest.mark.parametrize(
    "kind",
    ("bom", "missing_lf", "pretty", "duplicate_key", "float", "nan", "changed_digest"),
)
def test_noncanonical_or_altered_bytes_fail(kind: str) -> None:
    raw = (DECISION / "decision.json").read_bytes()
    changed = {
        "bom": b"\xef\xbb\xbf" + raw,
        "missing_lf": raw[:-1],
        "pretty": (json.dumps(_document(), indent=2) + "\n").encode(),
        "duplicate_key": b'{"x":1,"x":1}\n',
        "float": b'{"x":1.5}\n',
        "nan": b'{"x":NaN}\n',
        "changed_digest": raw.replace(b"bounded_deferred", b"changed_deferred", 1),
    }[kind]
    with pytest.raises((AssertionError, ValueError)):
        _assert_bytes(changed)


def test_rendering_failure_is_independent_of_digest_and_semantics() -> None:
    document = _document()
    _assert_semantics(document)
    _assert_bytes(_canonical(document))
    with pytest.raises(AssertionError, match="derived Markdown mismatch"):
        _assert_view(document, _render(document) + "\nPublished successfully.\n")
    altered = copy.deepcopy(document)
    altered["subjects"][1]["remainder"]["question"] = "A different retained question."
    assert _render(altered) != _render(document)


@pytest.mark.parametrize(
    "kind", ("omit", "duplicate_and_omit", "wrong_subject_reference")
)
def test_subject_coverage_controls_do_not_depend_on_stale_counts(kind: str) -> None:
    document = _document()
    _assert_semantics(document)
    if kind == "omit":
        document["subjects"].pop(1)
    elif kind == "duplicate_and_omit":
        document["subjects"][1] = copy.deepcopy(document["subjects"][0])
    else:
        document["subjects"][1]["source"]["selection"] = "wrong_root_reference"
    document["census"]["summary"] = _summary(document["subjects"])
    document["census"]["subject_source_keys"] = [
        s["source"]["input"] + ":" + s["id"] for s in document["subjects"]
    ]
    with pytest.raises(
        AssertionError, match="subject coverage/identity|subject root reference"
    ):
        _assert_semantics(document)


@pytest.mark.parametrize(
    "kind",
    (
        "missing_symbol",
        "substituted_symbol",
        "wrong_module",
        "wrong_test",
        "missing_witness",
    ),
)
def test_required_model_and_test_owner_mapping(kind: str) -> None:
    document = _document()
    _assert_semantics(document)
    if kind == "missing_symbol":
        document["surface"].pop()
    elif kind == "substituted_symbol":
        document["surface"][0]["symbol"] = "FaultInstanceIdentity"
    elif kind == "wrong_module":
        document["surface"][0]["module"] = "faultatlas.domain.fault"
    elif kind == "wrong_test":
        document["surface"][0]["witness"] = "package"
    else:
        document["witnesses"].pop("V6")
    with pytest.raises(
        AssertionError,
        match="required model mapping coverage|model module owner|model test owner|collected witness mapping",
    ):
        _assert_semantics(document)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    (
        ("disposition", "resolved", "empirical unknown cannot be resolved"),
        ("state", "established", "empirical state must remain unknown"),
        ("owner", "S1.P07", "empirical remainder owner"),
        ("revisit", "after_synthetic_round_trip", "empirical revisit condition"),
        ("remainder", None, "empirical remainder required"),
    ),
)
def test_synthetic_witnesses_cannot_discharge_the_p00_unknown(
    field: str, value: Any, message: str
) -> None:
    document = _document()
    _assert_semantics(document)
    subject = document["subjects"][1]
    if field in ("disposition", "remainder"):
        subject[field] = value
    else:
        subject["remainder"][field] = value
    document["census"]["summary"] = _summary(document["subjects"])
    with pytest.raises(AssertionError, match=message):
        _assert_semantics(document)


def test_additional_p01_subject_cannot_be_silently_reassigned() -> None:
    document = _document()
    _assert_semantics(document)
    document["subjects"][2]["remainder"]["owner"] = "S1.P08"
    document["census"]["summary"] = _summary(document["subjects"])
    with pytest.raises(AssertionError, match="empirical remainder owner"):
        _assert_semantics(document)


@pytest.mark.parametrize(
    "kind",
    (
        "s08_complete",
        "p07_complete",
        "own_publication",
        "unconditional",
        "missing_basis",
        "missing_question",
    ),
)
def test_unsupported_readiness_or_publication_is_rejected(kind: str) -> None:
    document = _document()
    _assert_semantics(document)
    if kind == "s08_complete":
        document["readiness"]["scheduled"]["S1.P07.S08"] = "complete"
    elif kind == "p07_complete":
        document["readiness"]["p07_closed"] = True
    elif kind == "own_publication":
        document["publication"]["merged_sha"] = "a" * 40
    elif kind == "unconditional":
        document["readiness"]["verdict"] = "eligible_to_begin"
    elif kind == "missing_basis":
        document["readiness"]["required_witnesses"].remove("V3")
    else:
        document["readiness"]["preserved_empirical_subjects"].remove(GENERALITY)
    with pytest.raises(
        AssertionError,
        match="scheduled work|publication remains|conditional authoring|readiness witness basis|readiness preserves",
    ):
        _assert_semantics(document)


@pytest.mark.parametrize("kind", ("digest", "wrong_root_selector", "wrong_alias"))
def test_source_bytes_and_exact_selector_content_are_independent(kind: str) -> None:
    document = _document()
    raw = _source_bytes()
    _assert_sources(document, raw)
    if kind == "digest":
        raw["p00"] = raw["p00"].replace(
            b"unknown_pending_additional_evidence",
            b"changed_pending_additional_evidence",
            1,
        )
    elif kind == "wrong_root_selector":
        document["inputs"]["p00"]["selectors"]["empirical"]["pointer"] = (
            "/deferred_register/items/22"
        )
    else:
        document["inputs"]["case"]["selectors"]["empirical_alias"]["pointer"] = (
            "/known_gaps/25"
        )
    with pytest.raises(AssertionError, match="source digest|source selection"):
        _assert_sources(document, raw)
