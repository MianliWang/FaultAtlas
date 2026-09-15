"""Source-qualified bounded P08 closure and finite installed integration."""

from __future__ import annotations

import ast
import copy
import hashlib
import json
import stat
import subprocess
import sys
from pathlib import Path
from typing import Any, cast

import pytest
from test_assessment_cli import installed_cli as installed_cli
from test_assessment_file import selected as selected
from test_supplied_assessment import rich_wire, sample_wire

from faultatlas.assessment import inspect_assessment
from faultatlas.domain.assessment import AssessmentBasis, SuppliedAssessment

ROOT = Path(__file__).resolve().parents[1]
CLOSURE_REL = (
    "reference_corpus/contracts/transfer-applicability/closures/s1-p08-phase-closure"
)
CLOSURE = ROOT / CLOSURE_REL
CLOSURE_SHA = "8d67767915bf8649560afd52e2c191f249071cdeee8aff5a2c173c7aeeadbf1b"
CLOSURE_BYTES = 57889
MARKDOWN_SHA = "5a0a0d6af4e93684d2ad3e10606e6bac83609177f5245bcff0dd6c5c5e50625f"
MARKDOWN_BYTES = 68746
DISPOSITION = (
    "reviewed_unknown_retained_nonblocking_for_bounded_supplied_workflow_closure"
)
TRIGGERS = [
    "before_any_widened_support_generality_or_verified_transfer_claim",
    "upon_new_relevant_reviewed_evidence",
]

# Historical source and publication observations captured from actual bytes and
# immutable Git/CI logs. Offline tests do not fetch old Git objects or providers.

SOURCE_PINS: Any = {
    "p00": {
        "path": "reference_corpus/pytest-4412/closures/s1-p00-phase-closure/closure.json",
        "byte_length": 102190,
        "sha256": "8c02d79c4a5a1d52b9fc2a3718e1b47888da6195588e62ab927388dbe972189e",
        "role": "primary inherited JSON",
    },
    "p01": {
        "path": "reference_corpus/contracts/identity/closures/s1-p01-phase-closure/closure.json",
        "byte_length": 112606,
        "sha256": "2c1bfb9d3d596711066796ef83999d49b6846e65315a301eead7fa8fb5ac4642",
        "role": "primary inherited JSON",
    },
    "p02": {
        "path": "reference_corpus/contracts/revision-locator/closures/s1-p02-phase-closure/closure.json",
        "byte_length": 100669,
        "sha256": "daf3a89ef22bf20652d91cc96f476f1f31584ec90d860e57d1641c3ec6ab5a67",
        "role": "primary inherited JSON",
    },
    "p03": {
        "path": "reference_corpus/contracts/evidence-envelope/closures/s1-p03-phase-closure/closure.json",
        "byte_length": 127921,
        "sha256": "21a24e7ab572456f22d3aca572e10e76be69529770b96a131f3d4f624d0b481b",
        "role": "primary inherited JSON",
    },
    "p07s07": {
        "path": "reference_corpus/contracts/pattern-invariant/decisions/s07-deferred-subject-disposition-readiness/decision.json",
        "byte_length": 22947,
        "sha256": "8937e1a896d8d4a78f01ce82878d478318b853532f90d9b93192f22d976ae237",
        "role": "primary inherited JSON",
    },
    "p07s09": {
        "path": "reference_corpus/contracts/pattern-invariant/closures/s1-p07-phase-closure/closure.json",
        "byte_length": 41207,
        "sha256": "5197b34ec97289d963d69d38bfc52ae640f2ad473df80d672eed3463c121366b",
        "role": "primary inherited JSON",
    },
    "identity_decision": {
        "path": "reference_corpus/pytest-4412/decisions/s07-identity-revision-provenance/decision.json",
        "byte_length": 85012,
        "sha256": "60ecb66565525cb21a924508794635072ae50e935d4791d9d91da5b6399ce866",
        "role": "primary inherited JSON",
    },
    "snapshot_decision": {
        "path": "reference_corpus/pytest-4412/decisions/s08-snapshot-boundary-compatibility/decision.json",
        "byte_length": 46533,
        "sha256": "f788116f3b9ea470c370a56e55eb6f37e05be200f285ac9f2572c641215f5f40",
        "role": "primary inherited JSON",
    },
    "s01": {
        "path": "docs/contracts/s1-p08-s01-supplied-assessment.md",
        "byte_length": 33760,
        "sha256": "bbb4be1bbae4b0520dbd72b179b36e84605b247c2204e57c1ea97b47074e8a34",
        "role": "published product contract",
    },
    "s02": {
        "path": "docs/contracts/s1-p08-s02-assessment-file.md",
        "byte_length": 18410,
        "sha256": "867f53e1cbdd17fa14bb261d57ef947f059beed2aa4da73ec1a2fef3d669cc14",
        "role": "published product contract",
    },
    "s03": {
        "path": "docs/contracts/s1-p08-s03-assessment-cli.md",
        "byte_length": 12301,
        "sha256": "3b70d254463a816f580fe30323fe6fec7f0024d0b67f56471fedac8a4fdfa7ae",
        "role": "published product contract",
    },
}

ROW_BINDINGS: Any = [
    [
        "O01",
        "p00",
        "/deferred_register/items/23",
        "gap:s05-known:cross-repository-pattern-and-transfer-not-established",
    ],
    [
        "O02",
        "p00",
        "/deferred_register/items/10",
        "gap:s05-known:no-universal-private-or-ghe-claims",
    ],
    [
        "O03",
        "p01",
        "/deferred_register/items/29",
        "deferred:p01:evidence-private-github",
    ],
    [
        "O04",
        "p01",
        "/deferred_register/items/30",
        "deferred:p01:evidence-github-enterprise",
    ],
    [
        "O05",
        "p01",
        "/deferred_register/items/31",
        "deferred:p01:evidence-other-source-providers",
    ],
    ["O06", "p01", "/deferred_register/items/32", "deferred:p01:evidence-non-git-vcs"],
    [
        "O07",
        "p01",
        "/deferred_register/items/38",
        "deferred:p01:p08-transfer-applicability",
    ],
    ["O08", "p02", "/deferred_register/items/35", "deferred:36"],
    ["O09", "p02", "/deferred_register/items/36", "deferred:37"],
    ["O10", "p02", "/deferred_register/items/37", "deferred:38"],
    ["O11", "p02", "/deferred_register/items/38", "deferred:39"],
    ["O12", "p03", "/deferred_register/entries/4", "deferred:05"],
    ["O13", "p02", "/deferred_register/items/24", "deferred:25"],
    [
        "O14",
        "p01",
        "/deferred_register/items/37",
        "deferred:p01:p07-pattern-generality",
    ],
    ["O15", "p03", "/deferred_register/entries/3", "deferred:04"],
]

CONTEXT_BINDINGS: Any = {
    "p07_model": ["p07s07", "/subjects/0"],
    "p08_handoff": ["p07s07", "/subjects/1"],
    "p07_original_owner": ["p07s07", "/subjects/2"],
    "p07_empirical_disposition": ["p07s09", "/empirical_review"],
    "wrong_root_discrepancy": ["p07s07", "/census/non_subjects/2"],
    "wrong_root_target": ["identity_decision", "/decision_register/register_items/12"],
    "D11_generality": [
        "identity_decision",
        "/decision_register/scope_of_generality_decision",
    ],
    "alternate_ID": ["identity_decision", "/decision_register/register_items/21"],
    "arbitrary_history": ["identity_decision", "/decision_register/register_items/22"],
    "writer_D11": ["snapshot_decision", "/reader_and_writer_decisions/writer"],
    "history_unknown": ["snapshot_decision", "/decision_register/unknown/1"],
    "P00_non_generalizations": ["p00", "/non_generalizations"],
}

PUBLICATIONS: Any = [
    {
        "unit": "S1.P08.S01",
        "pr": 97,
        "url": "https://github.com/MianliWang/FaultAtlas/pull/97",
        "pr_ci": {
            "run": 34793923604,
            "event": "pull_request",
            "attempt": 1,
            "associated_head": "27ac983bdfb8c64109d13c8ba55ca4068f91bfb4",
            "actual_checkout": "6bc81ca3e004048a9b6c6e4098f8ca4661554353",
            "parents": [
                "5e1f3e20dabdb895b0c62e65a4a8b4790e60c1d4",
                "27ac983bdfb8c64109d13c8ba55ca4068f91bfb4",
            ],
            "tree": "86d1c39dc581345c8c63c3bbcc096c578053872a",
            "conclusion": "success",
            "passed": 11472,
            "url": "https://github.com/MianliWang/FaultAtlas/actions/runs/34793923604",
        },
        "main_ci": {
            "run": 34794386661,
            "event": "push",
            "attempt": 1,
            "associated_head": "fecde1eddb3c89aeefde6dab30caa4bd9eb0adc6",
            "actual_checkout": "fecde1eddb3c89aeefde6dab30caa4bd9eb0adc6",
            "parents": ["5e1f3e20dabdb895b0c62e65a4a8b4790e60c1d4"],
            "tree": "86d1c39dc581345c8c63c3bbcc096c578053872a",
            "conclusion": "success",
            "passed": 11472,
            "url": "https://github.com/MianliWang/FaultAtlas/actions/runs/34794386661",
        },
        "evidence_role": "Retained executor/provider checkout logs rebound to immutable Git objects; not "
        "fresh S04 execution",
    },
    {
        "unit": "S1.P08.S02",
        "pr": 98,
        "url": "https://github.com/MianliWang/FaultAtlas/pull/98",
        "pr_ci": {
            "run": 34805702556,
            "event": "pull_request",
            "attempt": 1,
            "associated_head": "833cc62d17879828f64a0c1e3fb7daa6eb3914c3",
            "actual_checkout": "c61ab267274edfe7313e94a8f0851f928358322e",
            "parents": [
                "fecde1eddb3c89aeefde6dab30caa4bd9eb0adc6",
                "833cc62d17879828f64a0c1e3fb7daa6eb3914c3",
            ],
            "tree": "9a550700dc1c5fcb236fd9cb51979aeff5a47a29",
            "conclusion": "success",
            "passed": 11604,
            "url": "https://github.com/MianliWang/FaultAtlas/actions/runs/34805702556",
        },
        "main_ci": {
            "run": 34806231479,
            "event": "push",
            "attempt": 1,
            "associated_head": "ffc0edb0d6b5e7118c3d4110cd1bdf14c8ecf6db",
            "actual_checkout": "ffc0edb0d6b5e7118c3d4110cd1bdf14c8ecf6db",
            "parents": ["fecde1eddb3c89aeefde6dab30caa4bd9eb0adc6"],
            "tree": "9a550700dc1c5fcb236fd9cb51979aeff5a47a29",
            "conclusion": "success",
            "passed": 11604,
            "url": "https://github.com/MianliWang/FaultAtlas/actions/runs/34806231479",
        },
        "evidence_role": "Retained executor/provider checkout logs rebound to immutable Git objects; not "
        "fresh S04 execution",
    },
    {
        "unit": "S1.P08.S03",
        "pr": 99,
        "url": "https://github.com/MianliWang/FaultAtlas/pull/99",
        "pr_ci": {
            "run": 34889874813,
            "event": "pull_request",
            "attempt": 1,
            "associated_head": "791d20bd70edd2d130ba199e8ed4b47a387d1eef",
            "actual_checkout": "59e284771945f0769ae359d7a1cec3f9a69131d2",
            "parents": [
                "ffc0edb0d6b5e7118c3d4110cd1bdf14c8ecf6db",
                "791d20bd70edd2d130ba199e8ed4b47a387d1eef",
            ],
            "tree": "c14d847142e04a34b2f0ed1325470917c9697018",
            "conclusion": "success",
            "passed": 11778,
            "url": "https://github.com/MianliWang/FaultAtlas/actions/runs/34889874813",
        },
        "main_ci": {
            "run": 34904487284,
            "event": "push",
            "attempt": 1,
            "associated_head": "37307d208587b741fe44cbfa36b81c0adc363306",
            "actual_checkout": "37307d208587b741fe44cbfa36b81c0adc363306",
            "parents": ["ffc0edb0d6b5e7118c3d4110cd1bdf14c8ecf6db"],
            "tree": "c14d847142e04a34b2f0ed1325470917c9697018",
            "conclusion": "success",
            "passed": 11778,
            "url": "https://github.com/MianliWang/FaultAtlas/actions/runs/34904487284",
        },
        "evidence_role": "Retained executor/provider checkout logs rebound to immutable Git objects; not "
        "fresh S04 execution",
        "review": {
            "rounds": 4,
            "review_driven_repairs": 3,
            "R4_attempts": 2,
            "automatic_attempt": "Failed; no verdict",
            "explicit_request": 5671609458,
            "verdict_comment": 5671635890,
            "reviewed_head": "791d20bd70edd2d130ba199e8ed4b47a387d1eef",
            "verdict": "No major issues found",
            "formal_APPROVED_claimed": False,
        },
    },
]

EXIT_OBLIGATIONS: Any = [
    {
        "id": "exit:01",
        "requirement": "Complete source/target/basis and nine supplied records; nominal ownership and "
        "full local references",
        "owners": [
            {
                "path": "tests/test_supplied_assessment.py",
                "node": "test_exact_surface_and_independently_authored_full_value",
                "class": "published semantic owner",
            },
            {
                "path": "tests/test_assessment_phase_closure.py",
                "node": "test_rich_value_full_binding_and_pure_view",
                "class": "new synthetic integration check",
            },
        ],
    },
    {
        "id": "exit:02",
        "requirement": "Complete pure view, ordered attributions/conflicts, unopined condition and no "
        "inferred overall verdict",
        "owners": [
            {
                "path": "tests/test_assessment_inspection.py",
                "node": "test_complete_view_is_independently_authored_and_pure",
                "class": "published semantic owner",
            },
            {
                "path": "tests/test_assessment_phase_closure.py",
                "node": "test_invariant_material_states_do_not_generate_an_overall_opinion",
                "class": "new synthetic integration check",
            },
        ],
    },
    {
        "id": "exit:03",
        "requirement": "Strict v1 gateway/default-inclusive canonical value and unchanged exact "
        "normalized budgets",
        "owners": [
            {
                "path": "tests/test_assessment_file.py",
                "node": "test_authored_sparse_inspect_save_reopen_and_resave",
                "class": "published file owner",
            },
            {
                "path": "tests/test_assessment_file.py",
                "node": "test_corrected_normalized_boundary_really_saves_and_reopens",
                "class": "published exact3116/4096 body131072/envelope131125 boundary owner",
            },
        ],
    },
    {
        "id": "exit:04",
        "requirement": "No-overwrite/sync/cancellation effects remain distinct from CLI delivery; no "
        "truth or power-loss certificate",
        "owners": [
            {
                "path": "tests/test_assessment_cli.py",
                "node": "test_installed_post_cutoff_sigint_keeps_saved_effects",
                "class": "inherited instrumented real signal/file check",
            },
            {
                "path": "tests/test_assessment_cli.py",
                "node": "test_real_closed_reader_after_successful_save",
                "class": "published real pipe check",
            },
        ],
    },
    {
        "id": "exit:05",
        "requirement": "Installed public library plus generated console inspect/save/reopen/resave; "
        "exact prefix/LF and canonical bytes; malformed full reference refused by its "
        "owner",
        "owners": [
            {
                "path": "tests/test_assessment_phase_closure.py",
                "node": "test_installed_rich_selected_workflow",
                "class": "new installed synthetic integration check",
            },
            {
                "path": "tests/test_assessment_cli.py",
                "node": "test_exact_single_public_delegation_and_plain_output",
                "class": "published CLI mapping check",
            },
        ],
    },
    {
        "id": "exit:06",
        "requirement": "Independent source/package boundaries, source-only closure, exact primary "
        "dispositions and no active Phase/P09 planning-only handoff",
        "owners": [
            {
                "path": "tests/test_package.py",
                "node": None,
                "class": "existing complete package/source owner",
            },
            {
                "path": "tests/test_assessment_phase_closure.py",
                "node": "test_complete_closure_and_projection",
                "class": "new source-only closure check",
            },
            {
                "path": "tests/test_roadmap_lifecycle_consistency.py",
                "node": "test_p08_closed_workflow_has_no_active_phase_and_p09_planning_gate",
                "class": "mutable lifecycle owner",
            },
        ],
    },
]


def _source(key: str) -> Any:
    pin = SOURCE_PINS[key]
    raw = (ROOT / pin["path"]).read_bytes()
    assert (
        len(raw) == pin["byte_length"]
        and hashlib.sha256(raw).hexdigest() == pin["sha256"]
    ), "primary source bytes"
    return json.loads(raw) if pin["path"].endswith(".json") else raw.decode()


def _select(value: Any, pointer: str) -> Any:
    for part in pointer.strip("/").split("/"):
        value = (
            cast(list[Any], value)[int(part)]
            if isinstance(value, list)
            else value[part]
        )
    return value


def _document() -> dict[str, Any]:
    return json.loads((CLOSURE / "closure.json").read_bytes())


def _validate_rows(d: dict[str, Any]) -> None:
    rows = d["inherited_rows"]
    assert len(rows) == 15 and [x["row"] for x in rows] == [
        x[0] for x in ROW_BINDINGS
    ], "source-qualified row coverage"
    for row, (oid, source, selector, identifier) in zip(
        rows, ROW_BINDINGS, strict=True
    ):
        assert set(row) == {
            "row",
            "source",
            "selector",
            "original_record",
            "effective",
            "disposition",
        }, "row fields"
        assert (row["source"], row["selector"]) == (source, selector), (
            "exact source selector"
        )
        original = _select(_source(source), selector)
        assert (
            original.get("deferred_item_id", original.get("deferred_id")) == identifier
        ), "source ID"
        assert json.dumps(
            row["original_record"], sort_keys=True, allow_nan=False
        ) == json.dumps(original, sort_keys=True, allow_nan=False), (
            "full original record including absent fields"
        )
        owner = (
            "S1.P09"
            if oid == "O13"
            else "S1.P07"
            if oid in {"O14", "O15"}
            else "S1.P08"
        )
        expected_state = original.get(
            "current_state", original.get("implementation_state")
        )
        if oid == "O12":
            expected_state = "bounded_workflow_implemented"
        elif oid == "O15":
            expected_state = "bounded_model_implemented"
        effective = row["effective"]
        assert effective["owner"] == owner and effective["state"] == expected_state, (
            "effective owner/state"
        )
        expected_basis = "original source owner retained"
        if oid == "O01":
            expected_basis = "p07s07#/subjects/1 additive P08 handoff"
        elif oid == "O02":
            expected_basis = "published s01 contract: prospective P08 responsibility; original P01 immediate owner is not rewritten"
        assert effective == {
            "owner": owner,
            "state": expected_state,
            "basis": expected_basis,
        }, "effective handoff basis"
        decision = row["disposition"]
        constraints = {
            key: original[key]
            for key in ("consequence_if_unresolved", "latest_decision_point")
            if key in original
        }
        assert decision["original_constraints"] == constraints, (
            "original consequence/deadline and genuine absence"
        )
        assert decision["source_restrictions_waived"] is False, (
            "source prohibition remains"
        )
        assert decision["selected_workflow_evidence"] == [
            "S1.P08.S01",
            "S1.P08.S02",
            "S1.P08.S03",
        ], "published workflow evidence"
        assert (
            decision["not_empirical_evidence"]
            == "Supplied values and structural/codec/CLI tests do not inspect or establish the source question, authenticate authorship, or add reviewed target cases."
        ), "not empirical evidence"
        assert (
            decision["bounded_scope"]
            == "complete supplied-assessment model, pure inspection, selected-file canonical save/reopen and CLI only"
        ), "bounded closure scope"
        assert (
            decision["own_S04_execution_results"]
            == "external receipt only; listed integration checks are responsibilities, not claimed results"
        ), "no own execution result"
        trigger = (
            _source("p07s09")["empirical_review"]["prospective_trigger"]
            if oid == "O14"
            else TRIGGERS
        )
        assert decision["prospective_trigger"] == trigger, (
            "prospective trigger does not replace deadline"
        )
        if int(oid[1:]) <= 11:
            assert decision["status"] == DISPOSITION, (
                "bounded pre-completion disposition"
            )
            assert (
                decision["performed"]
                == "S04_pre_completion_review_of_original_records_and_published_selected_workflow"
            ), "review now, not deferred past completion"
            assert (
                decision["conclusion"]
                == "Original unresolved state and empirical/support prohibition remain; no missing selected workflow obligation was identified in the published owners."
            ), "empirical uncertainty remains"
        else:
            expected = {
                "O12": (
                    "bounded_model_and_selected_workflow_implemented",
                    "S01-S03 implement the chosen subset; S04 integration/closure is subject to its external publication gate. No empirical transfer is established.",
                ),
                "O13": (
                    "supplied_attribution_subset_consumed_generic_review_retained",
                    "Only supplied attribution and rationale were pulled forward; provisional generic applicability/review remains P09 responsibility.",
                ),
                "O14": (
                    "retained_P07_S09_empirical_disposition",
                    "P07 S09 already reviewed this unknown for its own bounded closure; its exception is not reassigned to P08.",
                ),
                "O15": (
                    "retained_implemented_P07_bounded_model",
                    "P07 S07 already implemented the bounded Pattern/Invariant reservation; S04 adds no model.",
                ),
            }[oid]
            assert (decision["status"], decision["conclusion"]) == expected, (
                "specific model/generic/empirical disposition"
            )
        expected_fields = {
            "original_constraints",
            "source_restrictions_waived",
            "selected_workflow_evidence",
            "not_empirical_evidence",
            "bounded_scope",
            "own_S04_execution_results",
            "prospective_trigger",
            "status",
            "conclusion",
        }
        if int(oid[1:]) <= 11:
            expected_fields.add("performed")
        assert set(decision) == expected_fields, "bounded disposition fields"


def _validate(d: dict[str, Any]) -> None:
    assert set(d) == {
        "format",
        "identity",
        "scope",
        "publications",
        "sources",
        "exit_obligations",
        "inherited_rows",
        "retained_context",
        "handoff",
        "evidence_roles",
    }, "document fields"
    assert type(d["format"]["version"]) is int, "integer format version"
    assert d["format"] == {
        "name": "faultatlas-transfer-applicability-bounded-phase-closure",
        "version": 1,
        "source_only": True,
        "product_interchange": False,
        "canonicalization": "json-sort-keys-compact-utf8-lf-v1",
    }, "source-only format"
    assert d["identity"] == {
        "id": "s1-p08-phase-closure",
        "phase": "S1.P08",
        "slice": "S1.P08.S04",
        "kind": "sealed_publication_candidate",
        "effective_only_after": "own protected publication and natural-main verification recorded externally",
        "authority_sha256": "7e5aefa1ab9f8e8fcccf9f4e91177954da0d68202bb37092e06208cfd3132411",
    }, "noncircular sealed candidate"
    assert d["scope"] == {
        "selected_workflow": "supplied-assessment/model/pure-inspection/selected-file/CLI",
        "production_changed": False,
        "production_modules": 28,
        "UUID_root_identities": 12,
        "P07_modules": 5,
        "P07_exports": 8,
        "selected_workflow_blockers": [],
        "empirical_transfer_established": False,
        "source_rows_are_independent_observations": False,
        "raw_or_normalized_limits_changed": False,
    }, "bounded scope and blockers"
    assert (
        d["format"]["source_only"] is True
        and d["format"]["product_interchange"] is False
    )
    for key in (
        "production_changed",
        "empirical_transfer_established",
        "source_rows_are_independent_observations",
        "raw_or_normalized_limits_changed",
    ):
        assert d["scope"][key] is False, "bounded scope boolean"
    assert d["handoff"]["implementation_authorized"] is False, (
        "P09 planning-only handoff"
    )
    assert json.dumps(d["sources"], sort_keys=True, allow_nan=False) == json.dumps(
        SOURCE_PINS, sort_keys=True, allow_nan=False
    ), "source pin set"
    for key in SOURCE_PINS:
        _source(key)
    assert json.dumps(d["publications"], sort_keys=True, allow_nan=False) == json.dumps(
        PUBLICATIONS, sort_keys=True, allow_nan=False
    ), "predecessor publication bindings"
    assert d["exit_obligations"] == EXIT_OBLIGATIONS, "complete exit responsibilities"
    assert set(d["retained_context"]) == set(CONTEXT_BINDINGS), (
        "retained boundary inventory"
    )
    for name, (source, pointer) in CONTEXT_BINDINGS.items():
        expected = {
            "source": source,
            "selector": pointer,
            "record": _select(_source(source), pointer),
        }
        assert json.dumps(
            d["retained_context"][name], sort_keys=True, allow_nan=False
        ) == json.dumps(expected, sort_keys=True, allow_nan=False), (
            "exact inherited handoff/boundary"
        )
    assert "becomes effective only on S01 publication" in _source("s01")
    assert "3116" in _source("s01") and "131125" in _source("s02")
    _validate_rows(d)
    assert d["handoff"] == {
        "completed_phase": "S1.P08",
        "completed_slices": ["S1.P08.S01", "S1.P08.S02", "S1.P08.S03", "S1.P08.S04"],
        "active_phases": [],
        "stage": "S1 active",
        "next": "S1.P09",
        "next_state": "not_started",
        "eligibility": "separate product/architecture Phase-start discussion and planning only",
        "implementation_authorized": False,
        "P10": "not_started",
        "generic_confidence_review": "P09 retains unimplemented generic responsibility; supplied attribution is not a confidence evaluator",
    }, "P09 planning-only handoff"
    assert d["evidence_roles"] == [
        "published S01-S03 semantic/file/CLI owners",
        "exact primary JSON source records and selectors",
        "retained Git/provider publication observations rebound outside tests",
        "executor-run/install/platform/cleanup results only in external S04 receipt",
        "independently authored synthetic values; no historical/empirical claim",
    ], "evidence roles"


def _render(d: dict[str, Any]) -> str:
    lines = [
        "# S1.P08 — Bounded supplied-workflow closure",
        "",
        "Sealed publication candidate: effective only after its own protected publication and natural-main verification, recorded externally. JSON is primary; this view adds no authority.",
        "",
    ]
    for name in (
        "format",
        "identity",
        "scope",
        "publications",
        "exit_obligations",
        "handoff",
        "evidence_roles",
        "sources",
        "retained_context",
    ):
        lines += [
            "## " + name.replace("_", " ").title(),
            "",
            "```json",
            json.dumps(d[name], ensure_ascii=False, sort_keys=True, indent=2),
            "```",
            "",
        ]
    lines += [
        "## Source-qualified original records and bounded dispositions",
        "",
        "Rows are source-qualified records, not fifteen independent empirical observations. Original fields, including absence, remain separate from new decisions.",
        "",
    ]
    for row in d["inherited_rows"]:
        lines += [
            "### " + row["row"],
            "",
            "```json",
            json.dumps(row, ensure_ascii=False, sort_keys=True, indent=2),
            "```",
            "",
        ]
    return "\n".join(lines)


def test_complete_closure_and_projection() -> None:
    raw = (CLOSURE / "closure.json").read_bytes()
    assert hashlib.sha256(raw).hexdigest() == CLOSURE_SHA and len(raw) == CLOSURE_BYTES
    d = _document()
    assert (
        raw
        == (
            json.dumps(
                d,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            )
            + "\n"
        ).encode()
    )
    assert (CLOSURE / "closure.sha256").read_text() == f"{CLOSURE_SHA}  closure.json\n"
    markdown = (CLOSURE / "closure.md").read_bytes()
    assert (
        hashlib.sha256(markdown).hexdigest() == MARKDOWN_SHA
        and len(markdown) == MARKDOWN_BYTES
    )
    assert markdown.decode() == _render(d)
    assert {x.name for x in CLOSURE.iterdir()} == {
        "closure.json",
        "closure.md",
        "closure.sha256",
    }
    family = CLOSURE.parent.parent
    assert {x.relative_to(family).as_posix() for x in family.rglob("*")} == {
        "closures",
        "closures/s1-p08-phase-closure",
        "closures/s1-p08-phase-closure/closure.json",
        "closures/s1-p08-phase-closure/closure.md",
        "closures/s1-p08-phase-closure/closure.sha256",
    }
    assert all(
        x.is_file() and not x.is_symlink() and stat.S_IMODE(x.stat().st_mode) == 0o644
        for x in CLOSURE.iterdir()
    )
    _validate(d)
    for obligation in d["exit_obligations"]:
        for owner in obligation["owners"]:
            tree = ast.parse((ROOT / owner["path"]).read_bytes())
            if owner["node"] is not None:
                assert owner["node"] in {
                    x.name for x in tree.body if isinstance(x, ast.FunctionDef)
                }


@pytest.mark.parametrize(
    "mutation,message",
    [
        ("boolean_version", "integer format version"),
        ("float_source_length", "source pin set"),
        ("exit", "exit responsibilities"),
        ("original_state", "full original record"),
        ("owner", "effective owner/state"),
        ("consequence", "original consequence"),
        ("selector", "exact source selector"),
        ("ID", "full original record"),
        ("empirical", "empirical uncertainty"),
        ("P09", "P09 planning-only"),
        ("own_result", "noncircular"),
        ("absent_deadline", "original consequence"),
    ],
)
def test_semantic_counterexamples_reach_their_own_guards(
    mutation: str, message: str
) -> None:
    d = _document()
    _validate(d)
    changed = copy.deepcopy(d)
    if mutation == "boolean_version":
        changed["format"]["version"] = True
    elif mutation == "float_source_length":
        changed["sources"]["p00"]["byte_length"] = float(
            changed["sources"]["p00"]["byte_length"]
        )
    elif mutation == "exit":
        changed["exit_obligations"].pop()
    elif mutation == "original_state":
        changed["inherited_rows"][2]["original_record"]["current_state"] = "resolved"
    elif mutation == "owner":
        changed["inherited_rows"][2]["effective"]["owner"] = "S1.P09"
    elif mutation == "consequence":
        changed["inherited_rows"][2]["disposition"]["original_constraints"][
            "consequence_if_unresolved"
        ] = "waived"
    elif mutation == "selector":
        changed["inherited_rows"][0]["selector"] = "/deferred_register/items/10"
    elif mutation == "ID":
        changed["inherited_rows"][0]["original_record"]["deferred_item_id"] = "alias"
    elif mutation == "empirical":
        changed["inherited_rows"][0]["disposition"]["conclusion"] = (
            "empirical transfer established"
        )
    elif mutation == "P09":
        changed["handoff"]["active_phases"] = ["S1.P09"]
    elif mutation == "own_result":
        changed["identity"]["own_CI_result"] = "passed"
    else:
        changed["inherited_rows"][11]["disposition"]["original_constraints"][
            "latest_decision_point"
        ] = "invented"
    with pytest.raises(AssertionError, match=message):
        _validate(changed)


def _rich_primitives() -> dict[str, Any]:
    value = rich_wire()
    value["basis"]["conditions"].append(
        {
            "key": "unopined",
            "statement": "A distinct condition has no supplied opinion.",
        }
    )
    value["conflicts"][1] = {
        "left_opinion_key": "op-b",
        "right_opinion_key": "op-a",
        "attribution": {
            "supplier": "Second conflict supplier",
            "rationale": "A separate reverse declaration.",
        },
    }
    return value


RICH_VIEW = """Supplied assessment - structural inspection only
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
Condition "unopined": "A distinct condition has no supplied opinion."
No opinion supplied
Material "note": "Supplied inline note."
Supplier: "Material supplier"
Rationale: "Record and locator are declarations only."
Record reference: {"schema_version":1,"format_name":"synthetic-note","format_version":"1","canonicalization":"json-sort-keys-compact-utf8-lf-v1","sha256":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","byte_length":1}
Locator: "https://invalid.example/note; do not execute or fetch"
References are supplied, not loaded or verified as support.
Material "unused": "Supplied inline note."
Supplier: "Material supplier"
Rationale: "Record and locator are declarations only."
Record reference: {"schema_version":1,"format_name":"synthetic-note","format_version":"1","canonicalization":"json-sort-keys-compact-utf8-lf-v1","sha256":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","byte_length":1}
Locator: "https://invalid.example/note; do not execute or fetch"
References are supplied, not loaded or verified as support.
Opinion "op-a": caller position="unknown", supplier="Reviewer A"
Statement: "No target run or inspected target material was supplied."
Rationale: "The evaluation count cannot be established from this file."
Condition reference: {"key":"once","statement":"A side-effecting expression is evaluated no more than once."}
Material keys: ["note"]
Opinion "op-b": caller position="stated", supplier="Reviewer B"
Statement: "verified by our upstream script"
Rationale: "This remains a claim."
Condition reference: {"key":"once","statement":"A side-effecting expression is evaluated no more than once."}
Material keys: ["note"]
Conflict 1: left="op-a", right="op-b"; caller declaration
Supplier: "Conflict supplier"
Rationale: "The caller declares this conflict."
Conflict 2: left="op-b", right="op-a"; caller declaration
Supplier: "Second conflict supplier"
Rationale: "A separate reverse declaration."
Overall caller opinion: "applicable"
Supplier: "Overall supplier"
Rationale: "A supplied opinion only."
Structural checks: passed; no applicability or repair certification
End of complete view
"""


def test_rich_value_full_binding_and_pure_view() -> None:
    primitive = _rich_primitives()
    value = SuppliedAssessment.model_validate_json(json.dumps(primitive))
    basis = AssessmentBasis.model_validate_json(
        json.dumps(copy.deepcopy(primitive["basis"]))
    )
    assert value.model_dump(mode="json") == primitive
    assert inspect_assessment(basis, value) == RICH_VIEW
    assert SuppliedAssessment.model_validate(value) == value
    changed = copy.deepcopy(primitive["basis"])
    changed["materials"][0]["description"] = (
        "Changed content under the same material key."
    )
    valid_changed = AssessmentBasis.model_validate_json(json.dumps(changed))
    with pytest.raises(
        ValueError, match="^assessment basis does not match requested basis$"
    ):
        inspect_assessment(valid_changed, value)


@pytest.mark.parametrize("state", ["absent", "omitted", "empty"])
def test_invariant_material_states_do_not_generate_an_overall_opinion(
    state: str,
) -> None:
    primitive = sample_wire()
    primitive["basis"]["source"] = {
        "invariant": "00000000-0000-4000-8000-000000000002",
        "invariant_statement": "The supplied operation preserves the declared invariant.",
    }
    primitive["basis"]["materials"] = [] if state == "empty" else None
    primitive["basis"]["material_omission"] = (
        "No relevant material was supplied." if state == "omitted" else None
    )
    value = SuppliedAssessment.model_validate_json(json.dumps(primitive))
    equal = AssessmentBasis.model_validate_json(json.dumps(primitive["basis"]))
    assert value.model_dump(mode="json") == primitive
    view = inspect_assessment(equal, value)
    assert view.endswith(
        "Overall opinion: not supplied; none inferred\nStructural checks: passed; no applicability or repair certification\nEnd of complete view\n"
    )
    assert ("Materials: explicitly omitted" in view) is (state == "omitted")
    assert ("Materials: caller-declared empty inventory" in view) is (state == "empty")
    assert ("Materials: not supplied" in view) is (state == "absent")


def _prepare(path: Path, raw: bytes) -> None:
    with path.open("xb") as stream:
        stream.write(raw)
    path.chmod(0o600)


def _metadata(path: Path) -> tuple[int, ...]:
    s = path.stat()
    return (
        s.st_dev,
        s.st_ino,
        s.st_mode,
        s.st_uid,
        s.st_gid,
        s.st_nlink,
        s.st_size,
        s.st_mtime_ns,
        s.st_ctime_ns,
    )


def _file_view(path: Path) -> bytes:
    return (
        f'Selected assessment file: {json.dumps(str(path))}\nFormat: "faultatlas-supplied-assessment"\nVersion: 1\n'
        + RICH_VIEW
    ).encode()


def test_installed_rich_selected_workflow(
    installed_cli: tuple[Path, dict[str, str]], selected: tuple[Path, Path]
) -> None:
    executable, environment = installed_cli
    parent = selected[
        0
    ].parent  # Existing public fixture verified actual ext4/private ownership.
    source, saved, resaved = (
        parent / "rich-input.json",
        parent / "library-saved.json",
        parent / "cli-resaved.json",
    )
    _prepare(source, RICH_INPUT)
    expected: dict[str, Any] = {
        "format": "faultatlas-supplied-assessment",
        "version": 1,
        "assessment": _rich_primitives(),
    }
    assert json.loads(RICH_INPUT) == expected
    canonical = (
        json.dumps(expected, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        + "\n"
    ).encode()
    before = source.read_bytes(), _metadata(source)
    script = """
import json,pathlib,sys
from faultatlas.assessment import inspect_assessment
from faultatlas.domain.assessment import SuppliedAssessment,AssessmentBasis
from faultatlas.assessment_file import inspect_assessment_file,save_assessment_as_new
source,target=map(pathlib.Path,sys.argv[1:3]);installed=pathlib.Path(sys.argv[3])
value=SuppliedAssessment.model_validate_json(json.dumps(json.loads(source.read_bytes())["assessment"]))
basis=AssessmentBasis.model_validate_json(json.dumps(json.loads(source.read_bytes())["assessment"]["basis"]))
assert inspect_assessment(basis,value)==sys.argv[4]
assert inspect_assessment_file(str(source))==sys.argv[5]
assert save_assessment_as_new(str(source),str(target))==str(target)
for name,module in sys.modules.copy().items():
    if name=="faultatlas" or name.startswith("faultatlas."):
        assert pathlib.Path(module.__file__).is_relative_to(installed)
print("installed public library provenance PASS")
"""
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            script,
            str(source),
            str(saved),
            str(executable.parent.parent),
            RICH_VIEW,
            _file_view(source).decode(),
        ],
        cwd=parent,
        env=environment,
        capture_output=True,
        check=False,
        timeout=20,
    )
    assert (result.returncode, result.stdout, result.stderr) == (
        0,
        b"installed public library provenance PASS\n",
        b"",
    )
    assert (
        saved.read_bytes() == canonical and stat.S_IMODE(saved.stat().st_mode) == 0o600
    )
    for path, module in [(source, False), (saved, False), (resaved, True)]:
        if path == resaved:
            result = subprocess.run(
                [str(executable), "assessment", "save-as", str(saved), str(resaved)],
                cwd=parent,
                env=environment,
                capture_output=True,
                check=False,
                timeout=20,
            )
            assert (result.returncode, result.stdout, result.stderr) == (
                0,
                f'Saved new assessment file: "{resaved}"\noutput_visibility=published; sync_completed=true\n'.encode(),
                b"",
            )
        prefix = [sys.executable, "-m", "faultatlas"] if module else [str(executable)]
        result = subprocess.run(
            [*prefix, "assessment", "inspect", str(path)],
            cwd=parent,
            env=environment,
            capture_output=True,
            check=False,
            timeout=20,
        )
        assert (result.returncode, result.stdout, result.stderr) == (
            0,
            _file_view(path),
            b"",
        )
    assert (
        resaved.read_bytes() == canonical
        and stat.S_IMODE(resaved.stat().st_mode) == 0o600
    )
    assert (source.read_bytes(), _metadata(source)) == before
    invalid = copy.deepcopy(expected)
    invalid["assessment"]["basis"]["materials"][0]["record"]["sha256"] = "g" * 64
    bad, absent = parent / "bad-reference.json", parent / "not-published.json"
    _prepare(bad, json.dumps(invalid).encode())
    rejection = """
import sys
from faultatlas.assessment_file import AssessmentFileError,save_assessment_as_new
try:save_assessment_as_new(sys.argv[1],sys.argv[2])
except AssessmentFileError as error:
    assert error.code=="INVALID_ASSESSMENT"
    assert error.location==("assessment","basis","materials",0,"record","sha256"),error.location
    assert error.output_visibility=="not_published" and not error.sync_completed
else:raise AssertionError("invalid full reference accepted")
print("owning full-reference rejection PASS")
"""
    result = subprocess.run(
        [sys.executable, "-c", rejection, str(bad), str(absent)],
        cwd=parent,
        env=environment,
        capture_output=True,
        check=False,
        timeout=20,
    )
    assert (result.returncode, result.stdout, result.stderr) == (
        0,
        b"owning full-reference rejection PASS\n",
        b"",
    )
    assert not absent.exists()


RICH_INPUT = b'{\n  "format": "faultatlas-supplied-assessment",\n  "version": 1,\n  "assessment": {\n    "attribution": {\n      "supplier": "Example author",\n      "rationale": "Synthetic input for a structural review."\n    },\n    "basis": {\n      "source": {\n        "pattern": "00000000-0000-4000-8000-000000000001",\n        "pattern_statement": "Repeated evaluation may repeat a side effect."\n      },\n      "target": {\n        "snapshot": {\n          "repository": {\n            "schema_version": 1,\n            "provider": "github",\n            "provider_repository_id": "1001"\n          },\n          "revision": {\n            "schema_version": 1,\n            "kind": "commit",\n            "algorithm": "sha1",\n            "full_digest": "1111111111111111111111111111111111111111"\n          }\n        },\n        "declared_host": "github.com",\n        "declared_visibility": "public",\n        "scope": null\n      },\n      "context_statement": null,\n      "conditions": [\n        {\n          "key": "once",\n          "statement": "A side-effecting expression is evaluated no more than once."\n        },\n        {\n          "key": "unopined",\n          "statement": "A distinct condition has no supplied opinion."\n        }\n      ],\n      "materials": [\n        {\n          "key": "note",\n          "description": "Supplied inline note.",\n          "attribution": {\n            "supplier": "Material supplier",\n            "rationale": "Record and locator are declarations only."\n          },\n          "record": {\n            "schema_version": 1,\n            "format_name": "synthetic-note",\n            "format_version": "1",\n            "canonicalization": "json-sort-keys-compact-utf8-lf-v1",\n            "sha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",\n            "byte_length": 1\n          },\n          "locator": "https://invalid.example/note; do not execute or fetch"\n        },\n        {\n          "key": "unused",\n          "description": "Supplied inline note.",\n          "attribution": {\n            "supplier": "Material supplier",\n            "rationale": "Record and locator are declarations only."\n          },\n          "record": {\n            "schema_version": 1,\n            "format_name": "synthetic-note",\n            "format_version": "1",\n            "canonicalization": "json-sort-keys-compact-utf8-lf-v1",\n            "sha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",\n            "byte_length": 1\n          },\n          "locator": "https://invalid.example/note; do not execute or fetch"\n        }\n      ],\n      "material_omission": null\n    },\n    "opinions": [\n      {\n        "key": "op-a",\n        "condition": {\n          "key": "once",\n          "statement": "A side-effecting expression is evaluated no more than once."\n        },\n        "position": "unknown",\n        "statement": "No target run or inspected target material was supplied.",\n        "attribution": {\n          "supplier": "Reviewer A",\n          "rationale": "The evaluation count cannot be established from this file."\n        },\n        "material_keys": [\n          "note"\n        ]\n      },\n      {\n        "key": "op-b",\n        "condition": {\n          "key": "once",\n          "statement": "A side-effecting expression is evaluated no more than once."\n        },\n        "position": "stated",\n        "statement": "verified by our upstream script",\n        "attribution": {\n          "supplier": "Reviewer B",\n          "rationale": "This remains a claim."\n        },\n        "material_keys": [\n          "note"\n        ]\n      }\n    ],\n    "conflicts": [\n      {\n        "left_opinion_key": "op-a",\n        "right_opinion_key": "op-b",\n        "attribution": {\n          "supplier": "Conflict supplier",\n          "rationale": "The caller declares this conflict."\n        }\n      },\n      {\n        "left_opinion_key": "op-b",\n        "right_opinion_key": "op-a",\n        "attribution": {\n          "supplier": "Second conflict supplier",\n          "rationale": "A separate reverse declaration."\n        }\n      }\n    ],\n    "overall_opinion": {\n      "statement": "applicable",\n      "attribution": {\n        "supplier": "Overall supplier",\n        "rationale": "A supplied opinion only."\n      }\n    }\n  }\n}\n'
