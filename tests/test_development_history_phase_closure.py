"""Hold the S1.P05 phase closure to its own account.

`closure.json` is the sole durable authority; `closure.md` is a projection of it
and never an independent source. The closure is a *sealed publication candidate*,
so it records no evidence of its own merge -- that evidence cannot exist while
these bytes are being sealed.

The document is validated by independent validators rather than one comparison
against a stored copy, and every validator is proved load-bearing: the mutation
table below corrupts the closure one way at a time and each corruption must be
refused. A validator no mutation can defeat is a validator that is not there.
"""

from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import tomllib
from pathlib import Path
from typing import Any, cast

import pytest

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
CLOSURE_RELATIVE = (
    "reference_corpus/contracts/development-history/closures/s1-p05-phase-closure"
)
CLOSURE_ROOT = REPOSITORY_ROOT / CLOSURE_RELATIVE
CORPUS_RELATIVE = "reference_corpus/contracts/development-history/v1"
DECISION_RELATIVE = (
    "reference_corpus/contracts/development-history/decisions"
    "/s08-deferred-subject-disposition/decision.json"
)
CORRECTION_RELATIVE = (
    "reference_corpus/contracts/development-history/corrections"
    "/s08-c01-deferred-subject-owner-topology/correction.json"
)
ROADMAP_RELATIVE = "docs/roadmap.md"

EXPECTED_CLOSURE_FILES = frozenset({"closure.json", "closure.md", "closure.sha256"})

PREDECESSOR_DIGESTS = {
    "reference_corpus/contracts/development-history/v1/manifest.json": "818299d3a79d1dcd65c6db8e108beb23642f465a02e7109219ed250fceda4cc6",
    "reference_corpus/contracts/development-history/v1/valid-vectors.json": "d3e005a552cb8b8385358bd98f2e50621116a4c1e9938a5278ce51647fd910ab",
    "reference_corpus/contracts/development-history/v1/invalid-vectors.json": "208ec0331e793cf4445869a02c9522b204ad702bc719db7f958f196f6374e99f",
    "reference_corpus/contracts/development-history/v1/replay-vectors.json": "a2676829e963c73cf4252a65266f0b37e51e94c5199a8a6117e48e606fb7e1ca",
    "reference_corpus/contracts/development-history/v1/contract.md": "a3a6bbcae54badde20e658162da5a8cd46ba54420686f01a3db838189eb80607",
    "reference_corpus/contracts/development-history/decisions/s08-deferred-subject-disposition/decision.json": "8df7a989ef33fb5d6e70c8815d1b74748c8c2f98cfb7e581414548a403d65cfe",
    "reference_corpus/contracts/development-history/corrections/s08-c01-deferred-subject-owner-topology/correction.json": "1ca0459edcc44951639c7b465f47eca43221d892a1621030267cb72fbcdd3bc3",
    "reference_corpus/contracts/repository-snapshot/closures/s1-p04-phase-closure/closure.json": "8605fdd7972f18c0e9c85f26cb0c366e71362630f25ea87a4cd6c22cc85aee74",
    "reference_corpus/contracts/evidence-envelope/closures/s1-p03-phase-closure/closure.json": "21a24e7ab572456f22d3aca572e10e76be69529770b96a131f3d4f624d0b481b",
    "reference_corpus/contracts/revision-locator/closures/s1-p02-phase-closure/closure.json": "daf3a89ef22bf20652d91cc96f476f1f31584ec90d860e57d1641c3ec6ab5a67",
    "reference_corpus/contracts/identity/closures/s1-p01-phase-closure/closure.json": "2c1bfb9d3d596711066796ef83999d49b6846e65315a301eead7fa8fb5ac4642",
    "reference_corpus/pytest-4412/closures/s1-p00-phase-closure/closure.json": "8c02d79c4a5a1d52b9fc2a3718e1b47888da6195588e62ab927388dbe972189e",
}

CURRENT_PRODUCTION_FILES = frozenset(
    {
        "src/faultatlas/__init__.py",
        "src/faultatlas/__main__.py",
        "src/faultatlas/cli.py",
        "src/faultatlas/domain/__init__.py",
        "src/faultatlas/domain/compatibility.py",
        "src/faultatlas/domain/evidence.py",
        "src/faultatlas/domain/history.py",
        "src/faultatlas/domain/history_evidence_link.py",
        "src/faultatlas/domain/identity.py",
        "src/faultatlas/domain/revision.py",
        "src/faultatlas/domain/snapshot.py",
        "src/faultatlas/domain/snapshot_evidence_link.py",
        "src/faultatlas/domain/source.py",
    }
)

EXPECTED_OWNED_SYMBOLS = (
    ("S1.P05.S01", "faultatlas.domain.history", "PullRequestRevisionRoleBinding"),
    ("S1.P05.S02", "faultatlas.domain.history", "ChangedPathStatus"),
    ("S1.P05.S02", "faultatlas.domain.history", "PullRequestChangedPath"),
    ("S1.P05.S02", "faultatlas.domain.history", "PullRequestChangeSet"),
    ("S1.P05.S03", "faultatlas.domain.history", "PullRequestReviewRevisionApproval"),
    ("S1.P05.S04", "faultatlas.domain.history", "PullRequestMergeRevisionOutcome"),
    ("S1.P05.S05", "faultatlas.domain.history", "PullRequestHeadRefDeletion"),
    ("S1.P05.S06", "faultatlas.domain.history", "PullRequestHistoricalOccurrenceTime"),
    (
        "S1.P05.S07",
        "faultatlas.domain.history_evidence_link",
        "PullRequestHistoryFactEvidenceLink",
    ),
)
OWNED_MODULES = (
    "faultatlas.domain.history",
    "faultatlas.domain.history_evidence_link",
)

EXPECTED_SLICE_IDS = tuple(f"S1.P05.S{index:02d}" for index in range(1, 11))
PUBLISHED_STATE_VOCABULARY = frozenset(
    {"complete_published", "sealed_publication_candidate"}
)

# The eighteen publications, keyed by the slice each one published. A correction
# or assurance follow-up publishes under its own id, so this is not one per slice.
EXPECTED_PUBLICATIONS = (
    ("S1.P05.S01", 54),
    ("S1.P05.S02", 55),
    ("S1.P05.S02.C01", 56),
    ("S1.P05.S02.C01.A01", 57),
    ("S1.P05.S03", 58),
    ("S1.P05.S03.A01", 59),
    ("S1.P05.S04", 60),
    ("S1.P05.S04.A01", 61),
    ("S1.P05.S05", 62),
    ("S1.P05.S06", 63),
    ("S1.P05.S06.A01", 64),
    ("S1.P05.S06.A01.C01", 65),
    ("S1.P05.S06.A01.C02", 66),
    ("S1.P05.S07", 67),
    ("S1.P05.S07.A01", 68),
    ("S1.P05.S08", 69),
    ("S1.P05.S08.C01", 70),
    ("S1.P05.S09", 71),
)

EXPECTED_PUBLICATION_CONTRACT = {
    "actual_S10_publication_facts_in_candidate": False,
    "admin_or_ruleset_bypass": "forbidden",
    "direct_main_push": "forbidden",
    "exact_reviewed_head_required": True,
    "future_publication_evidence_location": (
        "Git_history_GitHub_and_final_execution_report"
    ),
    "linear_history_required": True,
    "natural_main_CI_required": True,
    "protected_ready_pull_request_required": True,
    "protected_squash_merge_required": True,
    "required_check": "validate",
    "required_workflow": "CI",
    "review_settlement_required": True,
    "reviewed_tree_squash_tree_equality_required": True,
    "topic_branch": "docs/s1-p05-s10-phase-closure",
}

EXPECTED_HEADINGS = (
    "# S1.P05 Development History Model Phase Closure",
    "## Exact primary JSON digest",
    "## Derived and non-authoritative warning",
    "## Executive Phase-closure verdict",
    "## Phase identity and scope",
    "## Product surface",
    "## Ordered Slice and publication ledger",
    "## S1.P05.S08 disposition summary",
    "## Deferred ownership",
    "## S1.P05.S09 contract corpus summary",
    "## Canonical vertical assurance",
    "## Non-generalizations",
    "## Exit criteria",
    "## S1.P06 entry readiness",
    "## S1.P06 handoff",
    "## Publication candidate boundary",
    "## Source locks",
)

BASE_DEFERRED_FIELDS = frozenset(
    {"subject_id", "subject", "disposition", "effective_authority"}
)
OWNER_FIELDS = frozenset({"immediate_owner", "preserved_long_term_owner"})
DISPOSITION_VOCABULARY = frozenset({"addressed", "split", "carried_forward"})
STATE_VOCABULARY = frozenset(
    {
        "evidence_insufficient",
        "unknown_pending_additional_evidence",
        "unsupported_current_scope",
    }
)

EXPECTED_MUTATIONS = (
    "closure-source-digest-drift",
    "missing-source-lock",
    "extra-source-lock",
    "altered-production-source-count",
    "altered-product-symbol-inventory",
    "reordered-product-symbols",
    "s08-decision-digest-drift",
    "s08-c01-correction-digest-drift",
    "s09-manifest-digest-drift",
    "altered-vector-count",
    "vector-total-does-not-reconcile",
    "omitted-corpus-symbol-coverage",
    "nonzero-self-owned-open",
    "omitted-deferred-entry",
    "deferred-owner-omitted",
    "p05-retained-as-deferred-owner",
    "invented-disposition",
    "invented-disposition-state",
    "ownership-marked-incomplete",
    "omitted-non-generalization",
    "level-1-upgraded-to-verification",
    "flattened-evidence-derived-history-claimed",
    "complete-history-graph-claimed",
    "historical-default-branch-claimed",
    "p06-marked-started",
    "p06-marked-ineligible",
    "p06-entry-prerequisite-unsatisfied",
    "p06-handoff-subject-dropped",
    "fabricated-s10-publication-facts",
    "s10-candidate-publication-ids-nonempty",
    "s10-marked-published",
    "exit-criterion-unsatisfied",
    "exit-criterion-evidence-dangles",
    "reordered-slice-ledger",
    "duplicated-slice-id",
    "publication-id-not-declared-by-any-slice",
    "reviewed-squash-tree-mismatch",
    "publication-check-failed",
    "unsettled-review-thread",
    "non-squash-merge-method",
    "predecessor-digest-drift",
    "production-persistence-capability-claim",
    "network-capability-claim",
    "phase-marked-incomplete",
    "closure-owner-disagrees-with-corpus",
)


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _digest(path: Path) -> str:
    return _sha256(path.read_bytes())


def _closure() -> dict[str, Any]:
    return cast(
        dict[str, Any], json.loads((CLOSURE_ROOT / "closure.json").read_bytes())
    )


def _resolve(document: Any, dotted: str) -> Any:
    """Resolve a dotted evidence pointer, refusing an address that does not exist."""
    node: Any = document
    for segment in dotted.split("."):
        assert isinstance(node, dict), dotted
        mapping = cast(dict[str, Any], node)
        assert segment in mapping, dotted
        node = mapping[segment]
    return node


# --- independent validators --------------------------------------------------


def _assert_format(document: dict[str, Any]) -> None:
    fmt = cast(dict[str, Any], document["format"])
    assert fmt["name"] == "faultatlas-s1-p05-development-history-phase-closure"
    assert fmt["version"] == "1"
    assert fmt["classification"] == "phase_closure"
    assert fmt["internal"] is True
    assert fmt["public_contract"] is False
    assert fmt["publication_state"] == "sealed_publication_candidate"
    assert fmt["authority_statement"] == (
        "closure.json_is_the_sole_durable_semantic_authority"
        "_and_closure.md_is_derived_non_authoritative"
    )
    canon = cast(dict[str, Any], fmt["canonicalization"])
    assert canon["name"] == "json-sort-keys-compact-utf8-lf-v1"
    assert canon["keys"] == "sorted"
    assert canon["whitespace"] == "compact"
    assert canon["encoding"] == "UTF-8_without_BOM"
    assert canon["line_endings"] == "LF_only"
    assert canon["exactly_one_trailing_lf"] is True
    assert canon["floats_NaN_and_Infinity_permitted"] is False


def _assert_phase_identity(document: dict[str, Any]) -> None:
    identity = cast(dict[str, Any], document["phase_identity"])
    assert identity["phase"] == "S1.P05"
    assert identity["title"] == "Development History Model"
    assert identity["slice"] == "S1.P05.S10"
    assert identity["slice_count"] == len(EXPECTED_SLICE_IDS)
    assert identity["predecessor_phase"] == "S1.P04"
    assert identity["next_phase"] == "S1.P06"
    assert identity["phase_state"] == "complete"
    assert identity["closes_phase"] is True
    assert identity["corrective"] is False


def _assert_inventory(document: dict[str, Any]) -> None:
    inventory = cast(dict[str, Any], document["implementation_inventory"])
    modules = cast(list[str], inventory["owned_modules"])
    assert tuple(modules) == OWNED_MODULES
    assert inventory["owned_module_count"] == len(modules)

    symbols = cast(list[dict[str, Any]], inventory["owned_symbols"])
    assert inventory["owned_symbol_count"] == len(symbols)
    observed = tuple(
        (entry["slice_layer"], entry["module"], entry["symbol"]) for entry in symbols
    )
    # Order is part of the record: the surface is published slice by slice.
    assert observed == EXPECTED_OWNED_SYMBOLS
    assert {entry["module"] for entry in symbols} == set(OWNED_MODULES)

    absent = cast(list[str], inventory["absent_capabilities"])
    for capability in (
        "persistence",
        "storage",
        "migration",
        "network_io",
        "github_api_client",
        "git_or_filesystem_io",
        "production_development_history_reader",
        "production_development_history_writer",
    ):
        assert capability in absent, capability


def _assert_source_locks(document: dict[str, Any], *, verify_files: bool) -> None:
    locks = cast(dict[str, Any], document["source_locks"])
    immutable = cast(list[dict[str, Any]], locks["immutable_inputs"])
    observations = cast(list[dict[str, Any]], locks["production_observations"])
    assert locks["immutable_input_count"] == len(immutable)
    assert locks["production_observation_count"] == len(observations)
    assert locks["total_lock_count"] == len(immutable) + len(observations)
    assert locks["mutable_latest_or_current_pointer"] is False

    paths = [entry["path"] for entry in immutable]
    assert paths == sorted(paths), "immutable inputs are not path-ordered"
    assert len(set(paths)) == len(paths), "an input is locked twice"
    assert all(path.startswith("reference_corpus/") for path in paths)
    # The closure cannot lock itself: its own bytes are not sealed yet.
    assert not any(path.startswith(CLOSURE_RELATIVE) for path in paths)

    observed_sources = {entry["path"] for entry in observations}
    assert observed_sources == set(CURRENT_PRODUCTION_FILES)

    if verify_files:
        for entry in immutable + observations:
            path = REPOSITORY_ROOT / cast(str, entry["path"])
            assert path.is_file(), entry["path"]
            assert _digest(path) == entry["sha256"], entry["path"]
            assert path.stat().st_size == entry["byte_length"], entry["path"]


def _assert_deferred(document: dict[str, Any]) -> None:
    register = cast(dict[str, Any], document["deferred_register"])
    items = cast(list[dict[str, Any]], register["items"])
    assert register["count"] == len(items)
    assert register["dispositioned_exactly_once"] == len(items)
    assert register["ownership_complete"] is True
    assert register["self_owned_open"] == 0

    ids = [entry["subject_id"] for entry in items]
    assert len(set(ids)) == len(ids), "a subject is dispositioned twice"

    dispositions: dict[str, int] = {}
    states: dict[str, int] = {}
    immediate: dict[str, int] = {}
    long_term: dict[str, int] = {}
    for entry in items:
        assert BASE_DEFERRED_FIELDS <= set(entry), entry["subject_id"]
        disposition = cast(str, entry["disposition"])
        assert disposition in DISPOSITION_VOCABULARY, disposition
        dispositions[disposition] = dispositions.get(disposition, 0) + 1

        # A carried or split subject stays owned by somebody, and never by S1.P05.
        assert OWNER_FIELDS <= set(entry), entry["subject_id"]
        state = cast(str, entry["current_state"])
        assert state in STATE_VOCABULARY, state
        states[state] = states.get(state, 0) + 1
        for field, tally in (
            ("immediate_owner", immediate),
            ("preserved_long_term_owner", long_term),
        ):
            owner = cast(str, entry[field])
            assert owner, entry["subject_id"]
            assert owner != "S1.P05", (
                f"{entry['subject_id']} is still owned by the closing phase"
            )
            tally[owner] = tally.get(owner, 0) + 1

    assert register["disposition_totals"] == dispositions
    assert register["state_totals"] == states
    assert register["immediate_owner_totals"] == immediate
    assert register["long_term_owner_totals"] == long_term
    assert "S1.P05" not in immediate
    assert "S1.P05" not in long_term

    # The register is a projection of sealed governance, not a restatement.
    for key, relative in (
        ("source_decision", DECISION_RELATIVE),
        ("source_correction", CORRECTION_RELATIVE),
    ):
        source = cast(dict[str, Any], register[key])
        assert source["path"] == relative
        assert source["sha256"] == _digest(REPOSITORY_ROOT / relative)

    correction = json.loads((REPOSITORY_ROOT / CORRECTION_RELATIVE).read_bytes())
    projection = cast(dict[str, Any], correction["effective_projection"])
    assert items == projection["items"], "the register diverges from its correction"
    assert register["count"] == projection["count"]
    assert register["self_owned_open"] == projection["self_owned_open"]
    assert register["immediate_owner_totals"] == projection["immediate_owner_totals"]
    assert register["long_term_owner_totals"] == projection["long_term_owner_totals"]


def _assert_corpus(document: dict[str, Any]) -> None:
    corpus = cast(dict[str, Any], document["contract_corpus_assurance"])
    assert corpus["directory"] == CORPUS_RELATIVE
    assert corpus["package_excluded"] is True
    assert corpus["no_production_capability"] is True
    closed = cast(dict[str, Any], corpus["closed_world"])
    assert closed["unknown_target_rejected"] is True
    assert closed["unknown_operation_rejected"] is True
    assert closed["unknown_marker_rejected"] is True

    files = cast(list[str], corpus["files"])
    observed = sorted(
        path.name for path in (REPOSITORY_ROOT / CORPUS_RELATIVE).iterdir()
    )
    assert files == observed
    assert corpus["file_count"] == len(files)
    assert corpus["canonical_json_files"] == sum(
        1 for f in files if f.endswith(".json")
    )
    assert corpus["sidecar_count"] == sum(1 for f in files if f.endswith(".sha256"))

    manifest = json.loads(
        (REPOSITORY_ROOT / CORPUS_RELATIVE / "manifest.json").read_bytes()
    )
    assert corpus["corpus_id"] == manifest["corpus_identity"]["id"]
    assert corpus["corpus_format"] == manifest["format"]["name"]
    assert corpus["version"] == manifest["format"]["version"]
    # The corpus names this closure as its owner; the two must agree.
    assert manifest["corpus_identity"]["phase_closure_owner"] == "S1.P05.S10"

    summary = cast(dict[str, Any], manifest["vector_summary"])
    counts = cast(dict[str, Any], corpus["vector_counts"])
    assert counts["valid"] == summary["valid"]["count"]
    assert counts["invalid"] == summary["invalid"]["count"]
    assert counts["replay"] == summary["replay"]["count"]
    assert counts["fixtures"] == summary["fixtures"]
    assert counts["total"] == summary["total_vectors"]
    assert counts["total"] == counts["valid"] + counts["invalid"] + counts["replay"]

    coverage = cast(dict[str, Any], corpus["symbol_coverage"])
    assert coverage["expected"] == len(manifest["target_symbols"])
    assert coverage["accounted_for"] == coverage["expected"]
    assert coverage["expected"] == len(EXPECTED_OWNED_SYMBOLS)
    assert corpus["test_only_executor"] == (
        "tests/test_development_history_contract_corpus.py"
    )


def _assert_vertical(document: dict[str, Any]) -> None:
    vertical = cast(dict[str, Any], document["canonical_vertical_assurance"])
    assert vertical["no_product_aggregate_composed"] is True
    assert vertical["production_replay_io"] is False
    assert vertical["flattened_evidence_derived_history_claimed"] is False

    limits = cast(dict[str, Any], vertical["evidence_limits"])
    assert limits["complete_history_graph_claimed"] is False
    assert limits["generic_development_event_claimed"] is False
    assert limits["historical_default_branch_claimed"] is False
    assert limits["verified_authorship_claimed"] is False
    assert limits["whole_repository_history_enumeration_claimed"] is False

    layers = cast(list[dict[str, Any]], vertical["layers"])
    assert layers, "no provenance layer is recorded"
    manifest = json.loads(
        (REPOSITORY_ROOT / CORPUS_RELATIVE / "manifest.json").read_bytes()
    )
    permitted = set(manifest["replay_contract"]["classifications"])
    for layer in layers:
        assert layer["classification"] in permitted, layer["classification"]
        assert layer["layer"].startswith("S1.P05."), layer["layer"]
    # The S07 association is record-level; nothing may quietly promote it.
    assert "caller_supplied_association" in {lay["classification"] for lay in layers}


def _assert_non_generalizations(document: dict[str, Any]) -> None:
    section = cast(dict[str, Any], document["non_generalizations"])
    items = cast(list[dict[str, Any]], section["items"])
    assert section["count"] == len(items)
    assert section["intentional_deferral_is_not_implementation_failure"] is True

    manifest = json.loads(
        (REPOSITORY_ROOT / CORPUS_RELATIVE / "manifest.json").read_bytes()
    )
    declared = cast(list[str], manifest["non_goals"])
    assert [entry["subject"] for entry in items] == declared, (
        "the closure's non-generalizations diverge from the sealed corpus non-goals"
    )
    identifiers = [entry["non_generalization_id"] for entry in items]
    assert identifiers == [
        f"non-generalization:{i:02d}" for i in range(1, len(items) + 1)
    ]


def _assert_ledger(document: dict[str, Any]) -> None:
    ledger = cast(dict[str, Any], document["slice_ledger"])
    entries = cast(list[dict[str, Any]], ledger["entries"])
    publications = cast(list[dict[str, Any]], ledger["publications"])
    assert ledger["entry_count"] == len(entries)
    assert ledger["publication_count"] == len(publications)

    assert tuple(entry["slice_id"] for entry in entries) == EXPECTED_SLICE_IDS
    assert [entry["ordinal"] for entry in entries] == list(range(1, len(entries) + 1))
    for entry in entries:
        assert entry["state"] in PUBLISHED_STATE_VOCABULARY, entry["slice_id"]
        assert entry["title"], entry["slice_id"]

    # S10 is the sealed candidate: it publishes nothing it could already cite.
    closing = entries[-1]
    assert closing["slice_id"] == "S1.P05.S10"
    assert closing["state"] == "sealed_publication_candidate"
    assert closing["publication_ids"] == []
    for entry in entries[:-1]:
        assert entry["state"] == "complete_published", entry["slice_id"]
        assert entry["publication_ids"], entry["slice_id"]

    declared = [pid for entry in entries for pid in entry["publication_ids"]]
    assert len(set(declared)) == len(declared), "a publication is claimed twice"
    assert set(declared) == {pub["id"] for pub in publications}

    assert tuple((p["slice_id"], p["pull_request"]) for p in publications) == (
        EXPECTED_PUBLICATIONS
    )
    numbers = [p["pull_request"] for p in publications]
    assert numbers == sorted(numbers), "publications are not in publication order"
    assert len(set(numbers)) == len(numbers)

    for publication in publications:
        where = publication["slice_id"]
        assert publication["publication_state"] == "merged", where
        assert publication["merge_method"] == "protected_pull_request_squash_merge", (
            where
        )
        assert publication["reviewed_tree_equals_squash_tree"] is True, where
        assert publication["reviewed_tree"] == publication["squash_tree"], where
        assert publication["reviewed_head_sha"] != publication["squash_sha"], where
        for field in (
            "reviewed_head_sha",
            "squash_sha",
            "reviewed_tree",
            "squash_tree",
        ):
            value = cast(str, publication[field])
            assert len(value) == 40 and set(value) <= set("0123456789abcdef"), where

        for key in ("pull_request_check", "main_check"):
            check = cast(dict[str, Any], publication[key])
            assert check["conclusion"] == "success", (where, key)
            assert check["context"] == "validate", (where, key)
            assert check["workflow"] == "CI", (where, key)

        settlement = cast(dict[str, Any], publication["review_settlement"])
        assert settlement["settlement"] == "clean", where
        assert settlement["actionable_unresolved_thread_count"] == 0, where
        assert settlement["changes_requested_count"] == 0, where


def _assert_exit_criteria(document: dict[str, Any]) -> None:
    criteria = cast(dict[str, Any], document["exit_criteria"])
    items = cast(list[dict[str, Any]], criteria["items"])
    assert criteria["count"] == len(items)
    assert criteria["satisfied_count"] == sum(
        1 for entry in items if entry["status"] == "satisfied"
    )
    assert criteria["unsatisfied_count"] == len(items) - criteria["satisfied_count"]
    assert criteria["unsatisfied_count"] == 0
    assert criteria["satisfied_count"] == len(items)

    identifiers = [entry["criterion_id"] for entry in items]
    assert identifiers == [f"exit:{i:02d}" for i in range(1, len(items) + 1)]
    for entry in items:
        assert entry["subject"], entry["criterion_id"]
        # A criterion that cites an address this document does not carry is
        # not evidence of anything.
        _resolve(document, cast(str, entry["evidence"]))


def _assert_entry_readiness(document: dict[str, Any]) -> None:
    readiness = cast(dict[str, Any], document["entry_readiness"])
    assert readiness["next_phase"] == "S1.P06"
    assert readiness["readiness"] == "eligible_to_begin"
    assert readiness["implementation_state"] == "not_started"
    prerequisites = cast(list[dict[str, Any]], readiness["prerequisites"])
    assert readiness["prerequisite_count"] == len(prerequisites)
    identifiers = [entry["prerequisite_id"] for entry in prerequisites]
    assert identifiers == [
        f"p06-entry:{i:02d}" for i in range(1, len(prerequisites) + 1)
    ]
    for entry in prerequisites:
        assert entry["status"] == "satisfied", entry["prerequisite_id"]
        assert entry["evidence_owner"], entry["prerequisite_id"]
        assert entry["subject"], entry["prerequisite_id"]


def _assert_handoff(document: dict[str, Any]) -> None:
    handoff = cast(dict[str, Any], document["p06_handoff"])
    constraints = cast(list[dict[str, Any]], handoff["constraints"])
    assert handoff["constraint_count"] == len(constraints)
    identifiers = [entry["constraint_id"] for entry in constraints]
    assert identifiers == [
        f"p06-handoff:{i:02d}" for i in range(1, len(constraints) + 1)
    ]
    for entry in constraints:
        assert entry["statement"].endswith("."), entry["constraint_id"]

    assert handoff["status"] == "not_started"
    subjects = cast(list[str], handoff["received_subjects"])
    requirements = cast(list[dict[str, Any]], handoff["requirements"])
    assert handoff["received_subject_count"] == len(subjects)
    assert handoff["requirement_count"] == len(requirements)

    # The handoff is carried from sealed governance, not restated here.
    correction = json.loads((REPOSITORY_ROOT / CORRECTION_RELATIVE).read_bytes())
    source = next(
        record
        for record in correction["downstream_handoff"]["handoffs"]
        if record["target"] == "S1.P06"
    )
    assert handoff["source_handoff_id"] == source["handoff_id"]
    assert subjects == source["received_subjects"]
    assert requirements == source["requirements"]
    assert handoff["prohibited"] == source["prohibited"]
    assert handoff["status"] == source["status"]

    # Every subject S1.P06 receives must actually be owned by S1.P06.
    register = cast(dict[str, Any], document["deferred_register"])
    owned = {
        entry["remainder_subject"]
        for entry in cast(list[dict[str, Any]], register["items"])
        if entry["immediate_owner"] == "S1.P06"
    }
    assert set(subjects) <= owned, "S1.P06 is handed a subject it does not own"


def _assert_publication_contract(document: dict[str, Any]) -> None:
    contract = cast(dict[str, Any], document["publication_contract"])
    assert contract == EXPECTED_PUBLICATION_CONTRACT


def _assert_assurance(document: dict[str, Any]) -> None:
    assurance = cast(dict[str, Any], document["assurance"])
    locks = cast(dict[str, Any], document["source_locks"])
    criteria = cast(dict[str, Any], document["exit_criteria"])
    readiness = cast(dict[str, Any], document["entry_readiness"])
    register = cast(dict[str, Any], document["deferred_register"])

    assert assurance["candidate_state"] == "sealed_publication_candidate"
    assert assurance["no_production_change"] is True
    assert assurance["no_unresolved_P05_product_blockers"] is True
    assert assurance["package_exclusion"] is True
    assert assurance["predecessor_artifacts"] == "locked_unchanged"
    assert assurance["publication_state"] == "external_to_candidate_record"
    assert assurance["contract_corpus"] == "passed"
    assert assurance["self_owned_open"] == register["self_owned_open"]
    assert assurance["sealed_at"] == document["format"]["sealed_at"]
    assert assurance["P06_readiness"] == readiness["readiness"]
    assert assurance["P06_implementation_state"] == readiness["implementation_state"]

    total = cast(int, locks["total_lock_count"])
    assert assurance["source_locks"] == f"passed_{total}_of_{total}"
    satisfied, count = criteria["satisfied_count"], criteria["count"]
    assert assurance["exit_criteria"] == f"passed_{satisfied}_of_{count}"
    prerequisites = cast(int, readiness["prerequisite_count"])
    assert assurance["entry_readiness"] == f"passed_{prerequisites}_of_{prerequisites}"
    subjects = cast(int, register["count"])
    assert (
        assurance["deferred_owner_completeness"] == f"passed_{subjects}_of_{subjects}"
    )


VALIDATORS = (
    _assert_format,
    _assert_phase_identity,
    _assert_inventory,
    _assert_deferred,
    _assert_corpus,
    _assert_vertical,
    _assert_non_generalizations,
    _assert_ledger,
    _assert_exit_criteria,
    _assert_entry_readiness,
    _assert_handoff,
    _assert_publication_contract,
    _assert_assurance,
)


def _validate(document: dict[str, Any], *, verify_files: bool = False) -> None:
    for validator in VALIDATORS:
        validator(document)
    _assert_source_locks(document, verify_files=verify_files)


# --- the sealed triple -------------------------------------------------------


def test_closure_triple_is_exact() -> None:
    observed = {path.name for path in CLOSURE_ROOT.iterdir()}
    assert observed == EXPECTED_CLOSURE_FILES
    for name in sorted(EXPECTED_CLOSURE_FILES):
        assert (CLOSURE_ROOT / name).is_file(), name


def test_closure_json_is_exactly_canonical() -> None:
    raw = (CLOSURE_ROOT / "closure.json").read_bytes()
    assert not raw.startswith(b"\xef\xbb\xbf"), "byte-order mark"
    assert b"\r" not in raw, "carriage return"
    assert raw.endswith(b"\n") and not raw.endswith(b"\n\n"), "trailing newline"
    document = json.loads(raw)
    canonical = (
        json.dumps(
            document,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")
    assert raw == canonical


def test_sidecar_locks_closure_json_only() -> None:
    sidecar = (CLOSURE_ROOT / "closure.sha256").read_text(encoding="utf-8")
    assert sidecar.endswith("\n") and sidecar.count("\n") == 1
    digest, _, name = sidecar.strip().partition("  ")
    assert name == "closure.json"
    assert digest == _digest(CLOSURE_ROOT / "closure.json")


def test_closure_json_carries_no_self_digest() -> None:
    """A document cannot contain its own digest; a claim to is a forgery."""
    raw = (CLOSURE_ROOT / "closure.json").read_text(encoding="utf-8")
    assert _digest(CLOSURE_ROOT / "closure.json") not in raw


def test_markdown_is_derived_digest_synchronized_and_non_authoritative() -> None:
    markdown = (CLOSURE_ROOT / "closure.md").read_text(encoding="utf-8")
    assert "\r" not in markdown
    assert markdown.endswith("\n")
    for heading in EXPECTED_HEADINGS:
        assert heading in markdown, heading
    assert markdown.splitlines()[0] == EXPECTED_HEADINGS[0]
    assert _digest(CLOSURE_ROOT / "closure.json") in markdown
    assert "sole durable semantic authority" in markdown
    assert "derived, non-authoritative view" in markdown
    assert "Where the two differ, the JSON governs." in markdown


def test_markdown_restates_only_figures_the_json_carries() -> None:
    """Every headline number in the projection is read back out of the JSON."""
    markdown = (CLOSURE_ROOT / "closure.md").read_text(encoding="utf-8")
    document = _closure()
    ledger = cast(dict[str, Any], document["slice_ledger"])
    locks = cast(dict[str, Any], document["source_locks"])
    register = cast(dict[str, Any], document["deferred_register"])
    corpus = cast(dict[str, Any], document["contract_corpus_assurance"])
    counts = cast(dict[str, Any], corpus["vector_counts"])

    assert (
        f"{ledger['entry_count']} Slice entries, "
        f"{ledger['publication_count']} published." in markdown
    )
    assert f"All **{register['count']}** inherited subjects" in markdown
    assert f"`self_owned_open == {register['self_owned_open']}`" in markdown
    assert (
        f"**{counts['valid']} valid, {counts['invalid']} invalid, "
        f"{counts['replay']} replay, {counts['total']} total**" in markdown
    )
    assert (
        f"{locks['production_observation_count']} closure-baseline production "
        f"observations and {locks['immutable_input_count']} immutable inputs, "
        f"{locks['total_lock_count']} locks total." in markdown
    )
    for symbol in EXPECTED_OWNED_SYMBOLS:
        assert f"| `{symbol[0]}` | `{symbol[1]}` | `{symbol[2]}` |" in markdown
    for publication in cast(list[dict[str, Any]], ledger["publications"]):
        assert f"`{publication['squash_sha'][:12]}`" in markdown


def test_markdown_publishes_no_bare_pipe_or_unclosed_span() -> None:
    """A projection that breaks its own tables is not a readable record."""
    markdown = (CLOSURE_ROOT / "closure.md").read_text(encoding="utf-8")
    assert markdown.count("`") % 2 == 0, "unbalanced code span"
    for line in markdown.splitlines():
        if line.startswith("|"):
            assert line.endswith("|"), line
            cells = line.split("|")[1:-1]
            assert cells, line
            for cell in cells:
                stripped = cell.strip()
                assert stripped, line
                if stripped not in {"---", "—"}:
                    assert stripped.count("`") % 2 == 0, line


# --- the validators, and the proof that each is load-bearing -----------------


def test_complete_closure_document_passes_every_independent_validator() -> None:
    _validate(_closure(), verify_files=True)


def test_every_named_mutation_is_reachable() -> None:
    """The table is the contract: a name nobody applies proves nothing."""
    assert len(set(EXPECTED_MUTATIONS)) == len(EXPECTED_MUTATIONS)


@pytest.mark.parametrize("mutation", EXPECTED_MUTATIONS)
def test_each_required_closure_mutation_is_rejected(mutation: str) -> None:
    document = _closure()
    register = cast(dict[str, Any], document["deferred_register"])
    items = cast(list[dict[str, Any]], register["items"])
    locks = cast(dict[str, Any], document["source_locks"])
    ledger = cast(dict[str, Any], document["slice_ledger"])
    entries = cast(list[dict[str, Any]], ledger["entries"])
    publications = cast(list[dict[str, Any]], ledger["publications"])
    inventory = cast(dict[str, Any], document["implementation_inventory"])
    corpus = cast(dict[str, Any], document["contract_corpus_assurance"])
    vertical = cast(dict[str, Any], document["canonical_vertical_assurance"])
    readiness = cast(dict[str, Any], document["entry_readiness"])

    if mutation == "closure-source-digest-drift":
        cast(list[dict[str, Any]], locks["production_observations"])[0]["sha256"] = (
            "0" * 64
        )
    elif mutation == "missing-source-lock":
        cast(list[dict[str, Any]], locks["production_observations"]).pop()
    elif mutation == "extra-source-lock":
        extra = copy.deepcopy(cast(list[dict[str, Any]], locks["immutable_inputs"])[0])
        extra["path"] = "reference_corpus/does-not-exist.json"
        cast(list[dict[str, Any]], locks["immutable_inputs"]).append(extra)
    elif mutation == "altered-production-source-count":
        locks["production_observation_count"] = 99
    elif mutation == "altered-product-symbol-inventory":
        cast(list[dict[str, Any]], inventory["owned_symbols"]).pop()
    elif mutation == "reordered-product-symbols":
        symbols = cast(list[dict[str, Any]], inventory["owned_symbols"])
        symbols[0], symbols[1] = symbols[1], symbols[0]
    elif mutation == "s08-decision-digest-drift":
        cast(dict[str, Any], register["source_decision"])["sha256"] = "1" * 64
    elif mutation == "s08-c01-correction-digest-drift":
        cast(dict[str, Any], register["source_correction"])["sha256"] = "1" * 64
    elif mutation == "s09-manifest-digest-drift":
        for entry in cast(list[dict[str, Any]], locks["immutable_inputs"]):
            if entry["path"].endswith(f"{CORPUS_RELATIVE}/manifest.json"):
                entry["sha256"] = "2" * 64
    elif mutation == "altered-vector-count":
        cast(dict[str, Any], corpus["vector_counts"])["invalid"] += 1
    elif mutation == "vector-total-does-not-reconcile":
        cast(dict[str, Any], corpus["vector_counts"])["total"] += 1
    elif mutation == "omitted-corpus-symbol-coverage":
        cast(dict[str, Any], corpus["symbol_coverage"])["accounted_for"] -= 1
    elif mutation == "nonzero-self-owned-open":
        register["self_owned_open"] = 1
    elif mutation == "omitted-deferred-entry":
        items.pop()
    elif mutation == "deferred-owner-omitted":
        del items[0]["immediate_owner"]
    elif mutation == "p05-retained-as-deferred-owner":
        items[0]["immediate_owner"] = "S1.P05"
    elif mutation == "invented-disposition":
        items[0]["disposition"] = "resolved"
    elif mutation == "invented-disposition-state":
        items[0]["current_state"] = "probably_fine"
    elif mutation == "ownership-marked-incomplete":
        register["ownership_complete"] = False
    elif mutation == "omitted-non-generalization":
        cast(list[dict[str, Any]], document["non_generalizations"]["items"]).pop()
    elif mutation == "level-1-upgraded-to-verification":
        for layer in cast(list[dict[str, Any]], vertical["layers"]):
            if layer["classification"] == "caller_supplied_association":
                layer["classification"] = "verified_association"
    elif mutation == "flattened-evidence-derived-history-claimed":
        vertical["flattened_evidence_derived_history_claimed"] = True
    elif mutation == "complete-history-graph-claimed":
        cast(dict[str, Any], vertical["evidence_limits"])[
            "complete_history_graph_claimed"
        ] = True
    elif mutation == "historical-default-branch-claimed":
        cast(dict[str, Any], vertical["evidence_limits"])[
            "historical_default_branch_claimed"
        ] = True
    elif mutation == "p06-marked-started":
        readiness["implementation_state"] = "in_progress"
    elif mutation == "p06-marked-ineligible":
        readiness["readiness"] = "blocked"
    elif mutation == "p06-entry-prerequisite-unsatisfied":
        cast(list[dict[str, Any]], readiness["prerequisites"])[0]["status"] = (
            "unsatisfied"
        )
    elif mutation == "p06-handoff-subject-dropped":
        cast(list[str], document["p06_handoff"]["received_subjects"]).pop()
    elif mutation == "fabricated-s10-publication-facts":
        cast(dict[str, Any], document["publication_contract"])[
            "actual_S10_publication_facts_in_candidate"
        ] = True
    elif mutation == "s10-candidate-publication-ids-nonempty":
        entries[-1]["publication_ids"] = ["publication:s10"]
    elif mutation == "s10-marked-published":
        entries[-1]["state"] = "complete_published"
    elif mutation == "exit-criterion-unsatisfied":
        cast(list[dict[str, Any]], document["exit_criteria"]["items"])[0]["status"] = (
            "unsatisfied"
        )
    elif mutation == "exit-criterion-evidence-dangles":
        cast(list[dict[str, Any]], document["exit_criteria"]["items"])[0][
            "evidence"
        ] = "slice_ledger.no_such_field"
    elif mutation == "reordered-slice-ledger":
        entries[0], entries[1] = entries[1], entries[0]
    elif mutation == "duplicated-slice-id":
        entries[1]["slice_id"] = entries[0]["slice_id"]
    elif mutation == "publication-id-not-declared-by-any-slice":
        publications[0]["id"] = "publication:unclaimed"
    elif mutation == "reviewed-squash-tree-mismatch":
        publications[0]["squash_tree"] = "3" * 40
    elif mutation == "publication-check-failed":
        cast(dict[str, Any], publications[0]["main_check"])["conclusion"] = "failure"
    elif mutation == "unsettled-review-thread":
        cast(dict[str, Any], publications[0]["review_settlement"])[
            "actionable_unresolved_thread_count"
        ] = 1
    elif mutation == "non-squash-merge-method":
        publications[0]["merge_method"] = "merge_commit"
    elif mutation == "predecessor-digest-drift":
        for entry in cast(list[dict[str, Any]], locks["immutable_inputs"]):
            if entry["path"].endswith("s1-p04-phase-closure/closure.json"):
                entry["sha256"] = "4" * 64
    elif mutation == "production-persistence-capability-claim":
        cast(list[str], inventory["absent_capabilities"]).remove("persistence")
    elif mutation == "network-capability-claim":
        cast(list[str], inventory["absent_capabilities"]).remove("network_io")
    elif mutation == "phase-marked-incomplete":
        cast(dict[str, Any], document["phase_identity"])["phase_state"] = "in_progress"
    elif mutation == "closure-owner-disagrees-with-corpus":
        cast(dict[str, Any], document["phase_identity"])["slice"] = "S1.P05.S11"
    else:  # pragma: no cover - guarded by the parametrization
        raise AssertionError(f"unhandled mutation: {mutation}")

    with pytest.raises(
        (AssertionError, KeyError, IndexError, ValueError, StopIteration)
    ):
        _validate(document, verify_files=True)


# --- integrity and environment ----------------------------------------------


@pytest.mark.parametrize("relative", tuple(sorted(PREDECESSOR_DIGESTS)))
def test_predecessor_and_governance_bytes_are_unchanged(relative: str) -> None:
    assert _digest(REPOSITORY_ROOT / relative) == PREDECESSOR_DIGESTS[relative]


def test_this_closure_adds_no_production_source() -> None:
    tracked = subprocess.run(  # noqa: S603 - literal argv, no shell
        ["git", "ls-files", "src/"],
        cwd=REPOSITORY_ROOT,
        capture_output=True,
        check=False,
    )
    assert tracked.returncode == 0, tracked.stderr
    observed = set(tracked.stdout.decode("utf-8").split())
    assert observed == set(CURRENT_PRODUCTION_FILES)
    assert len(observed) == 13


def test_owned_symbols_match_the_live_published_modules() -> None:
    """The record follows the code: a symbol resolves, or the closure is wrong."""
    import importlib

    for module_name in OWNED_MODULES:
        module = importlib.import_module(module_name)
        exported = tuple(cast(tuple[str, ...], module.__all__))
        expected = tuple(
            symbol
            for _slice, owner, symbol in EXPECTED_OWNED_SYMBOLS
            if owner == module_name
        )
        assert exported == expected, module_name
        for symbol in exported:
            resolved = getattr(module, symbol)
            assert resolved.__module__ == module_name, symbol


def test_deferred_source_references_resolve_into_their_sealed_documents() -> None:
    document = _closure()
    register = cast(dict[str, Any], document["deferred_register"])
    correction = json.loads((REPOSITORY_ROOT / CORRECTION_RELATIVE).read_bytes())
    projection = cast(dict[str, Any], correction["effective_projection"])

    assert register["items"] == projection["items"]
    assert register["count"] == len(projection["items"])
    assert projection["self_owned_open"] == 0
    # The correction supersedes the decision without rewriting its bytes.
    decision = json.loads((REPOSITORY_ROOT / DECISION_RELATIVE).read_bytes())
    assert decision, "the superseded decision must remain readable"
    assert cast(dict[str, Any], register["source_decision"])["sha256"] == _digest(
        REPOSITORY_ROOT / DECISION_RELATIVE
    )


def test_closure_lives_outside_the_packaged_source_root() -> None:
    """Exclusion is structural: the closure is not under the packaged root.

    The behavioural proof -- that a real offline build ships neither the corpus
    nor this closure -- is owned by ``tests/test_package.py``, which builds the
    wheel and sdist and enumerates their members. This test guards only the
    layout fact that makes that outcome possible.
    """
    pyproject = tomllib.loads(
        (REPOSITORY_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    )
    assert pyproject["build-system"]["build-backend"] == "uv_build"
    assert not CLOSURE_RELATIVE.startswith("src/")
    assert not CORPUS_RELATIVE.startswith("src/")
    assert (REPOSITORY_ROOT / "src" / "faultatlas").is_dir()
    assert not (REPOSITORY_ROOT / "src" / "faultatlas" / "reference_corpus").exists()


def test_roadmap_records_phase_completion_and_p06_readiness() -> None:
    roadmap = (REPOSITORY_ROOT / ROADMAP_RELATIVE).read_text(encoding="utf-8")
    assert "`S1.P05` is complete" in roadmap
    assert "`S1.P05.S10` are complete" in roadmap
    assert "`S1.P06` is next and not started" in roadmap
    assert "`S1.P04` is complete" in roadmap
    assert CLOSURE_RELATIVE in roadmap
    assert "`S1.P05.S10` — Integration and Phase Closure (complete)" in roadmap
    # The sequence is closed, so the provisional caveat must not still stand.
    assert "The remaining `S1.P05` sequence is PROVISIONAL" not in roadmap
    # The states the closure has left behind must not survive anywhere.
    assert "`S1.P05` is active and incomplete" not in roadmap
    assert "`S1.P05.S10` is next and not started" not in roadmap
    assert "S1.P06 implementation has begun" not in roadmap


def test_roadmap_narrative_restates_the_closure_figures() -> None:
    """The roadmap paragraph is another projection and must not drift from it."""
    document = _closure()
    locks = cast(dict[str, Any], document["source_locks"])
    register = cast(dict[str, Any], document["deferred_register"])
    criteria = cast(dict[str, Any], document["exit_criteria"])
    handoff = cast(dict[str, Any], document["p06_handoff"])
    generalizations = cast(dict[str, Any], document["non_generalizations"])
    roadmap = " ".join(
        (REPOSITORY_ROOT / ROADMAP_RELATIVE).read_text(encoding="utf-8").split()
    )
    assert (
        f"recording {locks['total_lock_count']} locks, {register['count']} finalized "
        f"deferred entries with `self_owned_open == {register['self_owned_open']}`, "
        f"{generalizations['count']} non-generalizations, "
        f"{criteria['satisfied_count']} satisfied exit criteria, and "
        f"{handoff['constraint_count']} `S1.P06` handoff constraints." in roadmap
    )


def test_closure_and_roadmap_agree_on_readiness() -> None:
    document = _closure()
    readiness = cast(dict[str, Any], document["entry_readiness"])
    roadmap = (REPOSITORY_ROOT / ROADMAP_RELATIVE).read_text(encoding="utf-8")
    assert readiness["implementation_state"] == "not_started"
    assert (
        f"`{readiness['next_phase']}` is `{readiness['readiness']}` with "
        f"implementation state `{readiness['implementation_state']}`" in roadmap
    )
