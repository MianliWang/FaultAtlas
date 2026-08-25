from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, cast

import pytest

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
DECISION_ROOT = (
    REPOSITORY_ROOT
    / "reference_corpus/contracts/repository-snapshot/decisions"
    / "s08-deferred-subject-disposition"
)
DECISION_JSON = DECISION_ROOT / "decision.json"
DECISION_MARKDOWN = DECISION_ROOT / "decision.md"
DECISION_SIDECAR = DECISION_ROOT / "decision.sha256"

DECISION_RELATIVE = (
    "reference_corpus/contracts/repository-snapshot/decisions/"
    "s08-deferred-subject-disposition"
)

P00_CLOSURE = "reference_corpus/pytest-4412/closures/s1-p00-phase-closure/closure.json"
P01_CLOSURE = (
    "reference_corpus/contracts/identity/closures/s1-p01-phase-closure/closure.json"
)
P02_CLOSURE = (
    "reference_corpus/contracts/revision-locator/closures/"
    "s1-p02-phase-closure/closure.json"
)
P03_CLOSURE = (
    "reference_corpus/contracts/evidence-envelope/closures/"
    "s1-p03-phase-closure/closure.json"
)
CASE_JSON = "reference_corpus/pytest-4412/case/case.json"
GAP_MATRIX = (
    "reference_corpus/pytest-4412/analysis/"
    "s06-current-contract-gap-matrix/gap-matrix.json"
)
S07_DECISION = (
    "reference_corpus/pytest-4412/decisions/"
    "s07-identity-revision-provenance/decision.json"
)
ACQUISITION = (
    "reference_corpus/pytest-4412/acquisitions/"
    "run-0001-s04-v1-base-4c9cde74-head-690a63b9/acquisition.json"
)

PREDECESSOR_DIGESTS = {
    P00_CLOSURE: "8c02d79c4a5a1d52b9fc2a3718e1b47888da6195588e62ab927388dbe972189e",
    P01_CLOSURE: "2c1bfb9d3d596711066796ef83999d49b6846e65315a301eead7fa8fb5ac4642",
    P02_CLOSURE: "daf3a89ef22bf20652d91cc96f476f1f31584ec90d860e57d1641c3ec6ab5a67",
    P03_CLOSURE: "21a24e7ab572456f22d3aca572e10e76be69529770b96a131f3d4f624d0b481b",
    CASE_JSON: "fc1439a8f9766bdf55b95e9d63f3bf19db44da1724dfb7cd2e889771384b9efa",
    GAP_MATRIX: "55dacf5193aedc5493ac369dd0e3fb74a0f59f0c1f88bab1b625a2e4f4ff5f13",
    S07_DECISION: "60ecb66565525cb21a924508794635072ae50e935d4791d9d91da5b6399ce866",
    ACQUISITION: "1c29093bf1537e9b824a18df1848b71a8da014f544bc9f385707eb0e000a1318",
}

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

HISTORY_MODULE = "src/faultatlas/domain/history.py"
HISTORY_EVIDENCE_LINK_MODULE = "src/faultatlas/domain/history_evidence_link.py"
CURRENT_PRODUCTION_FILES = {
    *EXPECTED_PRODUCTION_FILES,
    HISTORY_MODULE,
    HISTORY_EVIDENCE_LINK_MODULE,
}

# Every deferred-subject state published by S1.P00 through S1.P03. S08 may not
# introduce a state outside this closed vocabulary.
PUBLISHED_STATE_VOCABULARY = frozenset(
    {
        "decision_resolved_implementation_deferred",
        "evidence_insufficient",
        "implementation_deferred",
        "not_implemented",
        "provisional_design",
        "provisional_pending_later_phase_design",
        "unknown_pending_additional_evidence",
        "unsupported_current_scope",
    }
)

# The seven inherited subjects, their exact predecessor coordinates, and the
# exact approved disposition of each.
EXPECTED_SUBJECTS: tuple[dict[str, Any], ...] = (
    {
        "disposition": "addressed",
        "disposition_id": "disposition:s1-p04-s08:01",
        "outcome": "satisfied_by_S1.P04.S04",
        "addressed_by": ["S1.P04.S04"],
        "path": P01_CLOSURE,
        "pointer": "/deferred_register/items/17",
        "subject_id": "deferred:p01:p04-repository-snapshot-aggregation",
        "owner_fields": ("immediate_next_owner", "preserved_long_term_phase_owner"),
        "source_state": "provisional_design",
        "id_field": "deferred_item_id",
    },
    {
        "disposition": "addressed",
        "disposition_id": "disposition:s1-p04-s08:02",
        "outcome": "satisfied_by_S1.P04.S04",
        "addressed_by": ["S1.P04.S04"],
        "path": P02_CLOSURE,
        "pointer": "/deferred_register/items/16",
        "subject_id": "deferred:17",
        "owner_fields": ("immediate_owner", "preserved_long_term_owner"),
        "source_state": "provisional_design",
        "id_field": "deferred_item_id",
    },
    {
        "disposition": "split",
        "disposition_id": "disposition:s1-p04-s08:03",
        "addressed_by": ["S1.P04.S05", "S1.P04.S06"],
        "remainder_state": "evidence_insufficient",
        "remainder_immediate_owner": "S2",
        "remainder_long_term_owner": "S5",
        "path": P02_CLOSURE,
        "pointer": "/deferred_register/items/17",
        "subject_id": "deferred:18",
        "owner_fields": ("immediate_owner", "preserved_long_term_owner"),
        "source_state": "provisional_design",
        "id_field": "deferred_item_id",
    },
    {
        "disposition": "carried_forward",
        "disposition_id": "disposition:s1-p04-s08:04",
        "current_state": "unsupported_current_scope",
        "immediate_owner": "S1.P05",
        "long_term_owner": "S1.P05",
        "path": P02_CLOSURE,
        "pointer": "/deferred_register/items/18",
        "subject_id": "deferred:19",
        "owner_fields": ("immediate_owner", "preserved_long_term_owner"),
        "source_state": "provisional_design",
        "id_field": "deferred_item_id",
    },
    {
        "disposition": "carried_forward",
        "disposition_id": "disposition:s1-p04-s08:05",
        "current_state": "evidence_insufficient",
        "immediate_owner": "S2",
        "long_term_owner": "S5",
        "path": P02_CLOSURE,
        "pointer": "/deferred_register/items/19",
        "subject_id": "deferred:20",
        "owner_fields": ("immediate_owner", "preserved_long_term_owner"),
        "source_state": "provisional_design",
        "id_field": "deferred_item_id",
    },
    {
        "disposition": "addressed",
        "disposition_id": "disposition:s1-p04-s08:06",
        "outcome": "satisfied_by_S1.P04.S01_through_S1.P04.S07",
        "addressed_by": [
            "S1.P04.S01",
            "S1.P04.S02",
            "S1.P04.S03",
            "S1.P04.S04",
            "S1.P04.S05",
            "S1.P04.S06",
            "S1.P04.S07",
        ],
        "path": P03_CLOSURE,
        "pointer": "/deferred_register/entries/0",
        "subject_id": "deferred:01",
        "owner_fields": ("owner", None),
        "source_state": "not_implemented",
        "id_field": "deferred_id",
    },
    {
        "disposition": "carried_forward",
        "disposition_id": "disposition:s1-p04-s08:07",
        "current_state": "unknown_pending_additional_evidence",
        "immediate_owner": "S2",
        "long_term_owner": "S2",
        "path": P00_CLOSURE,
        "pointer": "/deferred_register/items/5",
        "subject_id": "gap:s05-known:historical-default-branch-unknown",
        "owner_fields": ("immediate_next_owner", "preserved_long_term_phase_owner"),
        "source_state": "unknown_pending_additional_evidence",
        "id_field": "deferred_item_id",
    },
)

EXPECTED_NON_GENERALIZATIONS = [
    "no whole-repository snapshot completeness",
    "no verified repository membership",
    "no historical default-branch substitution",
    "no default-branch designation model in S1.P04",
    "no known absence",
    "no prefix, ancestry, or tree-topology semantics",
    "no Git mode, symbolic-link, or gitlink semantics",
    "S1.P04.S07 evidence association remains LEVEL 1 record-level only",
    "no fact-level evidence locator",
    "no persistence or durable serialization",
    "intentional evidence-gated deferral is not implementation failure",
]


def _decision() -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(DECISION_JSON.read_text(encoding="utf-8")))


def _register() -> dict[str, Any]:
    return cast(dict[str, Any], _decision()["inherited_subject_register"])


def _items() -> list[dict[str, Any]]:
    return cast(list[dict[str, Any]], _register()["items"])


def _resolve(path: str, pointer: str) -> Any:
    node: object = json.loads((REPOSITORY_ROOT / path).read_text(encoding="utf-8"))
    for token in [part for part in pointer.split("/") if part]:
        if isinstance(node, list):
            node = cast(list[Any], node)[int(token)]
        else:
            node = cast(dict[str, Any], node)[token]
    return node


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _source_references(node: Any) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []

    def walk(value: Any) -> None:
        if isinstance(value, dict):
            mapping = cast(dict[str, Any], value)
            if {"path", "json_pointer", "sha256"} <= set(mapping):
                found.append(mapping)
            for nested in mapping.values():
                walk(nested)
        elif isinstance(value, list):
            for nested in cast(list[Any], value):
                walk(nested)

    walk(node)
    return found


# --- artifact shape --------------------------------------------------------


def test_decision_artifact_triple_is_exact() -> None:
    assert DECISION_ROOT.is_dir()
    assert {entry.name for entry in DECISION_ROOT.iterdir()} == {
        "decision.json",
        "decision.md",
        "decision.sha256",
    }
    assert all(entry.is_file() for entry in DECISION_ROOT.iterdir())
    assert not list(DECISION_ROOT.glob("*.py"))


def test_decision_json_is_exactly_canonical() -> None:
    raw = DECISION_JSON.read_bytes()
    document = json.loads(raw.decode("utf-8"))
    canonical = (
        json.dumps(
            document, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode("utf-8")
        + b"\n"
    )

    assert raw == canonical
    assert not raw.startswith(b"\xef\xbb\xbf")
    assert b"\r" not in raw
    assert raw.endswith(b"\n")
    assert not raw.endswith(b"\n\n")
    assert json.loads(canonical.decode("utf-8")) == document
    assert cast(dict[str, Any], _decision()["format"])["canonicalization"] == {
        "array_order": "declared_disposition_order",
        "encoding": "UTF-8_without_BOM",
        "exactly_one_trailing_lf": True,
        "floats_and_NaN_permitted": False,
        "keys": "sorted",
        "line_endings": "LF_only",
        "name": "json-sort-keys-compact-utf8-lf-v1",
        "whitespace": "compact",
    }


def test_decision_contains_no_float_or_non_finite_value() -> None:
    def walk(value: Any) -> None:
        assert not isinstance(value, float)
        if isinstance(value, dict):
            for nested in cast(dict[str, Any], value).values():
                walk(nested)
        elif isinstance(value, list):
            for nested in cast(list[Any], value):
                walk(nested)

    walk(_decision())


def test_sidecar_locks_the_exact_decision_bytes() -> None:
    assert DECISION_SIDECAR.read_bytes() == (
        f"{_digest(DECISION_JSON)}  decision.json\n".encode()
    )


def test_json_is_the_declared_semantic_authority() -> None:
    fmt = cast(dict[str, Any], _decision()["format"])
    assert fmt["primary_authority"] == (
        "decision.json_is_the_sole_durable_semantic_authority_and_"
        "decision.md_is_derived"
    )
    assert fmt["non_production_schema_warning"] == (
        "not_a_production_schema_class_wire_format_adapter_reader_writer"
        "_migration_persistence_contract_or_public_API"
    )
    assert fmt["classification"] == "internal_phase_governance_disposition_layer"
    assert fmt["production_persistence"] is False
    assert fmt["public_contract"] is False
    assert fmt["status"] == "sealed_complete"
    assert fmt["version"] == "1"


def test_markdown_is_derived_from_and_consistent_with_the_json() -> None:
    markdown = DECISION_MARKDOWN.read_text(encoding="utf-8")
    register = _register()

    assert markdown.startswith("# Repository Snapshot Deferred-Subject Disposition\n")
    assert "`decision.json` is the sole durable semantic authority" in markdown
    assert f"`{_digest(DECISION_JSON)}`" in markdown
    assert f"self_owned_open == {register['self_owned_open']}" in markdown
    assert f"inherited {register['count']} deferred subjects" in markdown

    for expected in EXPECTED_SUBJECTS:
        assert f"`{expected['subject_id']}`" in markdown
        assert expected["pointer"] in markdown
    for entry in EXPECTED_NON_GENERALIZATIONS:
        assert entry in markdown
    for lock in cast(
        list[dict[str, Any]],
        cast(dict[str, Any], _decision()["source_locks"])["cited_artifacts"],
    ):
        assert lock["sha256"] in markdown
    for forbidden in (
        "membership is established",
        "completeness is established",
        "default branch is main",
        "self_owned_open == 1",
    ):
        assert forbidden not in markdown


# --- subject register ------------------------------------------------------


def test_exactly_seven_inherited_subjects_each_dispositioned_once() -> None:
    register = _register()
    items = _items()

    assert len(items) == 7
    assert register["count"] == 7
    assert register["dispositioned_exactly_once"] == 7
    assert len({item["disposition_id"] for item in items}) == 7
    assert (
        len({cast(dict[str, Any], item["source"])["subject_id"] for item in items}) == 7
    )
    assert tuple(item["disposition_id"] for item in items) == tuple(
        expected["disposition_id"] for expected in EXPECTED_SUBJECTS
    )
    assert register["addressed_count"] == 3
    assert register["split_count"] == 1
    assert register["carried_forward_count"] == 4
    assert register["owner_completeness"] is True


def test_self_owned_open_is_zero() -> None:
    register = _register()
    assurance = cast(dict[str, Any], _decision()["assurance"])

    assert register["self_owned_open"] == 0
    assert assurance["self_owned_open"] == 0

    owners: list[str] = []
    for item in _items():
        if item["disposition"] == "carried_forward":
            owners.append(cast(str, item["immediate_owner"]))
            owners.append(cast(str, item["preserved_long_term_owner"]))
        elif item["disposition"] == "split":
            remainder = cast(
                dict[str, Any],
                cast(dict[str, Any], item["split"])["carried_forward_remainder"],
            )
            owners.append(cast(str, remainder["immediate_owner"]))
            owners.append(cast(str, remainder["preserved_long_term_owner"]))

    assert owners, "at least one subject must be carried forward"
    assert "S1.P04" not in owners
    assert set(owners) == {"S1.P05", "S2", "S5"}


def test_owner_and_state_totals_are_exact() -> None:
    register = _register()
    assert register["state_totals"] == {
        "evidence_insufficient": 2,
        "unknown_pending_additional_evidence": 1,
        "unsupported_current_scope": 1,
    }
    assert register["immediate_owner_totals"] == {"S1.P05": 1, "S2": 3}
    assert register["long_term_owner_totals"] == {"S1.P05": 1, "S2": 1, "S5": 2}


@pytest.mark.parametrize(
    "index",
    tuple(range(len(EXPECTED_SUBJECTS))),
    ids=[cast(str, expected["subject_id"]) for expected in EXPECTED_SUBJECTS],
)
def test_each_subject_carries_the_exact_approved_disposition(index: int) -> None:
    expected = EXPECTED_SUBJECTS[index]
    item = _items()[index]
    source = cast(dict[str, Any], item["source"])

    assert item["disposition_id"] == expected["disposition_id"]
    assert item["disposition"] == expected["disposition"]
    assert source["subject_id"] == expected["subject_id"]
    assert source["path"] == expected["path"]
    assert source["json_pointer"] == expected["pointer"]
    assert source["sha256"] == PREDECESSOR_DIGESTS[cast(str, expected["path"])]
    assert source["source_state"] == expected["source_state"]
    assert item["rationale"]

    if expected["disposition"] == "addressed":
        assert item["addressed_by"] == expected["addressed_by"]
        assert item["outcome"] == expected["outcome"]
        assert "current_state" not in item
        assert "immediate_owner" not in item
    elif expected["disposition"] == "carried_forward":
        assert item["current_state"] == expected["current_state"]
        assert item["immediate_owner"] == expected["immediate_owner"]
        assert item["preserved_long_term_owner"] == expected["long_term_owner"]
        assert item["evidence"]
        assert "addressed_by" not in item
    else:
        split = cast(dict[str, Any], item["split"])
        portion = cast(dict[str, Any], split["addressed_portion"])
        remainder = cast(dict[str, Any], split["carried_forward_remainder"])
        assert portion["addressed_by"] == expected["addressed_by"]
        assert portion["outcome"] == "satisfied_by_S1.P04.S05_and_S1.P04.S06"
        assert remainder["subject"] == "whole-repository snapshot completeness"
        assert remainder["current_state"] == expected["remainder_state"]
        assert remainder["immediate_owner"] == expected["remainder_immediate_owner"]
        assert (
            remainder["preserved_long_term_owner"]
            == expected["remainder_long_term_owner"]
        )
        assert remainder["evidence"]


def test_every_source_reference_resolves_with_a_matching_digest() -> None:
    references = _source_references(_decision())
    assert len(references) == 22

    for reference in references:
        path = REPOSITORY_ROOT / cast(str, reference["path"])
        assert path.is_file()
        assert _digest(path) == reference["sha256"]
        _resolve(cast(str, reference["path"]), cast(str, reference["json_pointer"]))


def test_each_subject_pointer_resolves_to_its_recorded_predecessor_record() -> None:
    for expected, item in zip(EXPECTED_SUBJECTS, _items(), strict=True):
        source = cast(dict[str, Any], item["source"])
        record = cast(
            dict[str, Any],
            _resolve(cast(str, expected["path"]), cast(str, expected["pointer"])),
        )
        id_field = cast(str, expected["id_field"])
        assert record[id_field] == expected["subject_id"]
        state_field = (
            "implementation_state" if id_field == "deferred_id" else "current_state"
        )
        assert record[state_field] == expected["source_state"]
        assert record[state_field] == source["source_state"]
        assert "S1.P04" in json.dumps(record)

        # Every owner field the decision attributes to this pointer must equal
        # the value actually stored at that pointer. A value taken from any
        # other artifact must never be recorded here.
        immediate_field, long_term_field = cast(
            tuple[str, str | None], expected["owner_fields"]
        )
        assert source["source_immediate_owner"] == record[immediate_field]
        if long_term_field is None:
            assert "source_preserved_long_term_owner" not in source
        else:
            assert source["source_preserved_long_term_owner"] == record[long_term_field]


def test_no_disposition_state_outside_the_published_vocabulary() -> None:
    used: set[str] = set()
    for item in _items():
        if "current_state" in item:
            used.add(cast(str, item["current_state"]))
        if item["disposition"] == "split":
            remainder = cast(
                dict[str, Any],
                cast(dict[str, Any], item["split"])["carried_forward_remainder"],
            )
            used.add(cast(str, remainder["current_state"]))
        used.add(cast(str, cast(dict[str, Any], item["source"])["source_state"]))

    assert used <= PUBLISHED_STATE_VOCABULARY
    assert used == {
        "evidence_insufficient",
        "not_implemented",
        "provisional_design",
        "unknown_pending_additional_evidence",
        "unsupported_current_scope",
    }
    for invented in (
        "closed_unsupported",
        "partially_complete",
        "permanently_unknown",
        "resolved_elsewhere",
        "transferred",
    ):
        assert invented not in DECISION_JSON.read_text(encoding="utf-8")


def test_historical_default_branch_state_is_preserved_and_never_substituted() -> None:
    item = _items()[6]
    source = cast(dict[str, Any], item["source"])

    assert item["current_state"] == source["source_state"]
    assert item["current_state"] == "unknown_pending_additional_evidence"
    assert item["immediate_owner"] == "S2"
    assert source["source_preserved_long_term_owner"] == "S1.P04"
    assert "prohibited_resolution" in item

    observation = cast(
        dict[str, Any],
        _resolve(ACQUISITION, "/observations/repository/default_branch_observation"),
    )
    assert observation["value"] == "main"
    assert cast(str, item["prohibited_resolution"]).startswith(
        "The historical unknown must never be replaced"
    )
    # The observed current value must never appear as a standalone token
    # anywhere in the decision, and the item must carry no resolved value.
    observed = re.escape(cast(str, observation["value"]))
    assert (
        re.search(rf"\b{observed}\b", DECISION_JSON.read_text(encoding="utf-8")) is None
    )
    assert not {
        "historical_default_branch",
        "resolved_value",
        "value",
    } & set(item)

    production = "\n".join(
        path.read_text(encoding="utf-8")
        for path in sorted((REPOSITORY_ROOT / "src").rglob("*.py"))
    )
    assert "default_branch" not in production
    assert "default branch" not in production


def test_gap_matrix_routing_is_attributed_to_its_own_artifact() -> None:
    item = _items()[6]
    note = cast(dict[str, Any], item["routing_note"])
    reference = cast(dict[str, Any], note["reference"])

    # The gap matrix and the S1.P00 closure state this item's immediate owner
    # differently. Each statement must be attributed to the artifact that
    # actually makes it, and neither may be recorded under the other's pointer.
    assert reference["path"] == GAP_MATRIX
    assert reference["json_pointer"] == "/gap_register/5"
    gap_record = cast(dict[str, Any], _resolve(GAP_MATRIX, "/gap_register/5"))
    assert gap_record["immediate_owner"] == "intentionally_unowned_until_more_evidence"
    assert gap_record["preserved_phase_owner"] == "S1.P04"
    assert gap_record["gap_id"] == cast(dict[str, Any], item["source"])["subject_id"]

    closure_record = cast(
        dict[str, Any], _resolve(P00_CLOSURE, "/deferred_register/items/5")
    )
    assert closure_record["immediate_next_owner"] == "S1.P04"
    assert gap_record["immediate_owner"] != closure_record["immediate_next_owner"]

    statement = cast(str, note["statement"])
    assert (
        "S1.P00 closure records this item's immediate next owner as S1.P04" in statement
    )
    assert "gap matrix" in statement
    assert "neither is attributed to the other" in statement


def test_downstream_handoffs_cover_every_carried_forward_subject() -> None:
    handoff = cast(dict[str, Any], _decision()["downstream_handoff"])
    handoffs = cast(list[dict[str, Any]], handoff["handoffs"])

    assert handoff["count"] == 3
    assert [entry["target"] for entry in handoffs] == ["S2", "S5", "S1.P05"]
    assert all(entry["status"] == "not_started" for entry in handoffs)
    assert all(entry["requirements"] and entry["prohibited"] for entry in handoffs)

    received: set[str] = set()
    for entry in handoffs:
        received.update(cast(list[str], entry["received_subjects"]))
    assert received == {
        "default-branch observation",
        "historical default branch unknown",
        "repository membership aggregation",
        "whole-repository snapshot completeness",
    }


def test_non_generalizations_are_exact_and_ordered() -> None:
    non_generalizations = cast(dict[str, Any], _decision()["non_generalizations"])
    assert non_generalizations["items"] == EXPECTED_NON_GENERALIZATIONS
    assert non_generalizations["count"] == len(EXPECTED_NON_GENERALIZATIONS)
    assert (
        non_generalizations["intentional_deferral_is_not_implementation_failure"]
        is True
    )


def test_phase_identity_does_not_claim_closure_or_correction() -> None:
    identity = cast(dict[str, Any], _decision()["phase_identity"])
    assert identity["phase"] == "S1.P04"
    assert identity["slice"] == "S1.P04.S08"
    assert identity["phase_state"] == "active_incomplete"
    assert identity["closes_phase"] is False
    assert identity["corrective"] is False
    assert identity["production_change"] is False
    assert identity["next_slice"] == "S1.P04.S09"
    assert identity["inherited_from"] == ["S1.P00", "S1.P01", "S1.P02", "S1.P03"]
    integrity = cast(dict[str, Any], _decision()["predecessor_integrity"])
    assert integrity["append_only"] is True
    assert integrity["predecessor_statements_remain_historically_correct"] is True


# --- historical integrity --------------------------------------------------


@pytest.mark.parametrize("relative", tuple(sorted(PREDECESSOR_DIGESTS)))
def test_predecessor_artifact_bytes_are_unchanged(relative: str) -> None:
    assert _digest(REPOSITORY_ROOT / relative) == PREDECESSOR_DIGESTS[relative]


def test_predecessor_deferred_registers_are_unchanged() -> None:
    p00 = cast(dict[str, Any], _resolve(P00_CLOSURE, "/deferred_register"))
    assert p00["count"] == 25
    assert p00["state_totals"] == {
        "decision_resolved_implementation_deferred": 12,
        "provisional_pending_later_phase_design": 4,
        "unknown_pending_additional_evidence": 9,
    }

    p01 = cast(dict[str, Any], _resolve(P01_CLOSURE, "/deferred_register"))
    assert p01["count"] == 40
    assert p01["immediate_owner_totals"]["S1.P04"] == 1
    assert p01["owners_complete"] is True

    p02 = cast(dict[str, Any], _resolve(P02_CLOSURE, "/deferred_register"))
    assert p02["count"] == 42
    assert p02["state_totals"] == {
        "evidence_insufficient": 4,
        "implementation_deferred": 12,
        "provisional_design": 23,
        "unsupported_current_scope": 3,
    }
    assert p02["immediate_owner_totals"]["S1.P04"] == 4
    assert p02["owner_completeness"] is True

    p03 = cast(dict[str, Any], _resolve(P03_CLOSURE, "/deferred_register"))
    assert p03["count"] == 14
    assert p03["ownership_complete"] is True


def test_p02_still_assigns_exactly_four_subjects_to_p04() -> None:
    items = cast(
        list[dict[str, Any]], _resolve(P02_CLOSURE, "/deferred_register/items")
    )
    owned = [item for item in items if item["immediate_owner"] == "S1.P04"]

    assert [item["deferred_item_id"] for item in owned] == [
        "deferred:17",
        "deferred:18",
        "deferred:19",
        "deferred:20",
    ]
    assert [item["subject"] for item in owned] == [
        "repository snapshot aggregation",
        "snapshot completeness",
        "default-branch observation",
        "repository membership aggregation",
    ]
    assert all(item["current_state"] == "provisional_design" for item in owned)


# --- governance-only boundary ----------------------------------------------


def test_production_surface_adds_only_history_after_this_decision() -> None:
    observed = {
        path.relative_to(REPOSITORY_ROOT).as_posix()
        for path in (REPOSITORY_ROOT / "src").rglob("*.py")
    }
    assert observed == CURRENT_PRODUCTION_FILES
    assert len(observed) == 13
    assert observed - EXPECTED_PRODUCTION_FILES == {
        HISTORY_MODULE,
        HISTORY_EVIDENCE_LINK_MODULE,
    }
    assert EXPECTED_PRODUCTION_FILES - observed == set()
    assert len(EXPECTED_PRODUCTION_FILES) == 11

    governance = cast(
        dict[str, Any],
        cast(dict[str, Any], _decision()["assurance"])["governance_only"],
    )
    assert governance == {
        "no_dependency_or_lockfile_change": True,
        "no_deferred_product_semantics_implemented": True,
        "no_production_module_added": True,
        "no_production_source_changed": True,
        "passed": True,
        "production_python_source_count": 11,
    }


def test_decision_artifact_is_outside_the_packaged_source_root() -> None:
    assert not DECISION_RELATIVE.startswith("src/")
    assert DECISION_ROOT.relative_to(REPOSITORY_ROOT).parts[0] == "reference_corpus"
    assert DECISION_ROOT.relative_to(REPOSITORY_ROOT).parts[-2] == "decisions"
    assert {entry.name for entry in DECISION_ROOT.iterdir()} <= {
        "decision.json",
        "decision.md",
        "decision.sha256",
    }
    package = cast(
        dict[str, Any],
        cast(dict[str, Any], _decision()["assurance"])["package_exclusion"],
    )
    assert package == {
        "excluded_from_sdist": True,
        "excluded_from_wheel": True,
        "passed": True,
    }


# --- roadmap ---------------------------------------------------------------


def test_roadmap_records_the_corrected_four_subject_accounting() -> None:
    roadmap = " ".join(
        (REPOSITORY_ROOT / "docs/roadmap.md").read_text(encoding="utf-8").split()
    )

    assert "exactly four deferred subjects, not three" in roadmap
    assert "Of the three S1.P02-deferred subjects" not in roadmap
    for subject_id in ("deferred:17", "deferred:18", "deferred:19", "deferred:20"):
        assert f"`{subject_id}`" in roadmap
    assert "The sealed `S1.P02` closure register was always correct" in roadmap


def test_roadmap_records_the_s08_disposition_and_transition() -> None:
    roadmap = " ".join(
        (REPOSITORY_ROOT / "docs/roadmap.md").read_text(encoding="utf-8").split()
    )

    assert "`S1.P04.S08` is complete" in roadmap
    assert "`S1.P04.S09` is complete" in roadmap
    assert "`S1.P04.S10` is complete" in roadmap
    assert "`S1.P04` is complete" in roadmap
    assert "`S1.P05` is active and incomplete" in roadmap
    assert "`S1.P05.S08` are complete" in roadmap
    assert "`S1.P05.S09` is next and not started" in roadmap
    assert "`S1.P06` through `S1.P10` remain not started" in roadmap
    assert "inherited exactly seven such subjects" in roadmap
    assert "`self_owned_open == 0`" in roadmap
    assert "S08 is governance-only" in roadmap
    assert "redisposition, not correction" in roadmap
    assert "`S1.P04` is complete" in roadmap
