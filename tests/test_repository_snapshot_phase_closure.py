from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any, NamedTuple, cast

import pytest

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
CLOSURE_ROOT = (
    REPOSITORY_ROOT
    / "reference_corpus/contracts/repository-snapshot/closures/s1-p04-phase-closure"
)
CLOSURE_RELATIVE = (
    "reference_corpus/contracts/repository-snapshot/closures/s1-p04-phase-closure"
)
CORPUS_RELATIVE = "reference_corpus/contracts/repository-snapshot/v1"
S08_DECISION = (
    "reference_corpus/contracts/repository-snapshot/decisions/"
    "s08-deferred-subject-disposition/decision.json"
)

EXPECTED_CLOSURE_FILES = {"closure.json", "closure.md", "closure.sha256"}


class LockedFile(NamedTuple):
    byte_length: int
    sha256: str


# Independently recorded oracles for the sealed closure bytes. These are
# literals, not values recomputed from the files under test, so a coordinated
# edit of closure.json together with its sidecar fails here instead of
# re-deriving its own expectation.
LOCKED_CLOSURE_FILES = {
    "closure.json": LockedFile(
        51268, "8605fdd7972f18c0e9c85f26cb0c366e71362630f25ea87a4cd6c22cc85aee74"
    ),
    "closure.sha256": LockedFile(
        79, "bf5ec1845a831c00ed55bf82f303de26d908a1d6b3b76577f0631381344d3c75"
    ),
}

PREDECESSOR_DIGESTS = {
    "reference_corpus/pytest-4412/closures/s1-p00-phase-closure/closure.json": (
        "8c02d79c4a5a1d52b9fc2a3718e1b47888da6195588e62ab927388dbe972189e"
    ),
    "reference_corpus/contracts/identity/closures/s1-p01-phase-closure/closure.json": (
        "2c1bfb9d3d596711066796ef83999d49b6846e65315a301eead7fa8fb5ac4642"
    ),
    "reference_corpus/contracts/revision-locator/closures/"
    "s1-p02-phase-closure/closure.json": (
        "daf3a89ef22bf20652d91cc96f476f1f31584ec90d860e57d1641c3ec6ab5a67"
    ),
    "reference_corpus/contracts/evidence-envelope/closures/"
    "s1-p03-phase-closure/closure.json": (
        "21a24e7ab572456f22d3aca572e10e76be69529770b96a131f3d4f624d0b481b"
    ),
    "reference_corpus/contracts/identity/v1/manifest.json": (
        "aafa6dee23971218f30f9c72f63e23741841f0852299bebf9f40471054cb760a"
    ),
    "reference_corpus/contracts/revision-locator/v1/manifest.json": (
        "56ba607a098744800ae94448982a0a3bab91fb4e7fba445a31406e2478dc1b80"
    ),
    "reference_corpus/contracts/evidence-envelope/v1/manifest.json": (
        "139364b04676d59e4717a38e73b371b138146a2a933688ab3793aac6fd2e03f0"
    ),
    "reference_corpus/contracts/repository-snapshot/v1/manifest.json": (
        "ca53f751b2e276e100b6da0fb1795eeed5414e94f17f6ec88e68980bbfeb8b13"
    ),
    S08_DECISION: ("7361582b749eeb986319b0cce87155671b3b25904346be06e6004fb0e53ac1da"),
    "uv.lock": "eee6eb59f69839a202ec072a6b607b60eede58bf760b84f6821904fdd9a24a85",
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
CURRENT_PRODUCTION_FILES = {*EXPECTED_PRODUCTION_FILES, HISTORY_MODULE}

EXPECTED_OWNED_SYMBOLS = (
    ("faultatlas.domain.snapshot", "S1.P04.S01", "RepositorySnapshotIdentity"),
    ("faultatlas.domain.snapshot", "S1.P04.S02", "RepositorySnapshotRootTreeBinding"),
    ("faultatlas.domain.snapshot", "S1.P04.S03", "RepositorySnapshotPathBinding"),
    (
        "faultatlas.domain.snapshot",
        "S1.P04.S04",
        "RepositorySnapshotPathBindingCollection",
    ),
    ("faultatlas.domain.snapshot", "S1.P04.S05", "RepositorySnapshotDeclaredPathScope"),
    (
        "faultatlas.domain.snapshot",
        "S1.P04.S06",
        "RepositorySnapshotDeclaredPathScopeCoverage",
    ),
    (
        "faultatlas.domain.snapshot_evidence_link",
        "S1.P04.S07",
        "RepositorySnapshotFactEvidenceLink",
    ),
)

EXPECTED_SLICE_IDS = tuple(f"S1.P04.S{index:02d}" for index in range(1, 11))
PUBLISHED_STATE_VOCABULARY = frozenset(
    {
        "evidence_insufficient",
        "unknown_pending_additional_evidence",
        "unsupported_current_scope",
    }
)
BASE_DEFERRED_FIELDS = frozenset(
    {"deferred_id", "subject", "disposition", "source_reference"}
)
OWNER_FIELDS = frozenset(
    {"current_state", "immediate_owner", "preserved_long_term_owner"}
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
    "topic_branch": "docs/s1-p04-s10-phase-closure",
}

EXPECTED_HEADINGS = (
    "## Exact primary JSON digest",
    "## Derived and non-authoritative warning",
    "## Executive Phase-closure verdict",
    "## Product surface",
    "## Ordered Slice and publication ledger",
    "## S1.P04.S08 disposition summary",
    "## Deferred ownership",
    "## S1.P04.S09 contract corpus summary",
    "## Canonical vertical assurance",
    "## Non-generalizations",
    "## Exit criteria",
    "## S1.P05 entry readiness",
    "## S1.P05 handoff",
    "## Publication candidate boundary",
    "## Source locks",
)

# Independent failure axes. Each probe must be rejected by the full validator.
EXPECTED_MUTATIONS = (
    "closure-source-digest-drift",
    "missing-source-lock",
    "extra-source-lock",
    "altered-production-source-count",
    "altered-product-symbol-inventory",
    "reordered-product-symbols",
    "s08-decision-digest-drift",
    "s09-manifest-digest-drift",
    "altered-vector-count",
    "omitted-corpus-symbol-coverage",
    "nonzero-self-owned-open",
    "omitted-deferred-entry",
    "deferred-owner-omitted",
    "p04-retained-as-deferred-owner",
    "addressed-entry-with-owner-fields",
    "split-entry-missing-addressed-by",
    "carried-forward-entry-with-addressed-by",
    "invented-disposition-state",
    "historical-default-branch-value-substituted",
    "omitted-non-generalization",
    "level-1-upgraded-to-verification",
    "flattened-evidence-derived-snapshot-claimed",
    "membership-brought-back-into-p04",
    "p05-marked-started",
    "p05-marked-ineligible",
    "deferred-19-owner-changed",
    "fabricated-s10-publication-facts",
    "s10-candidate-publication-ids-nonempty",
    "s10-marked-published",
    "exit-criterion-unsatisfied",
    "reordered-slice-ledger",
    "duplicated-slice-id",
    "reviewed-squash-tree-mismatch",
    "pr-main-ci-event-swap",
    "predecessor-digest-drift",
    "production-persistence-capability-claim",
)


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _digest(path: Path) -> str:
    return _sha256(path.read_bytes())


def _closure() -> dict[str, Any]:
    return cast(
        dict[str, Any],
        json.loads((CLOSURE_ROOT / "closure.json").read_text(encoding="utf-8")),
    )


def _resolve(document: Any, pointer: str) -> Any:
    node = document
    for token in [part for part in pointer.split("/") if part]:
        if isinstance(node, list):
            node = cast(list[Any], node)[int(token)]
        else:
            node = cast(dict[str, Any], node)[token]
    return node


# --- independent validators -------------------------------------------------


def _assert_format(document: dict[str, Any]) -> None:
    fmt = cast(dict[str, Any], document["format"])
    assert fmt["name"] == "faultatlas-s1-p04-repository-snapshot-phase-closure"
    assert fmt["classification"] == "phase_closure"
    assert fmt["publication_state"] == "sealed_publication_candidate"
    assert fmt["public_contract"] is False
    assert fmt["internal"] is True
    assert fmt["authority_statement"] == (
        "closure.json_is_the_sole_durable_semantic_authority_and_closure.md_is_"
        "derived_non_authoritative"
    )
    assert cast(dict[str, Any], fmt["canonicalization"])["name"] == (
        "json-sort-keys-compact-utf8-lf-v1"
    )


def _assert_phase_identity(document: dict[str, Any]) -> None:
    identity = cast(dict[str, Any], document["phase_identity"])
    assert identity["phase"] == "S1.P04"
    assert identity["slice"] == "S1.P04.S10"
    assert identity["phase_state"] == "complete"
    assert identity["closes_phase"] is True
    assert identity["corrective"] is False
    assert identity["slice_count"] == 10
    assert identity["next_phase"] == "S1.P05"
    assert identity["predecessor_phase"] == "S1.P03"


def _assert_inventory(document: dict[str, Any]) -> None:
    inventory = cast(dict[str, Any], document["implementation_inventory"])
    assert inventory["production_change"] is False
    assert inventory["production_python_source_count"] == 11
    assert inventory["owned_symbol_count"] == 7
    assert inventory["owned_modules"] == [
        "faultatlas.domain.snapshot",
        "faultatlas.domain.snapshot_evidence_link",
    ]
    assert inventory["supporting_authorities_not_owned"] == [
        "faultatlas.domain.evidence",
        "faultatlas.domain.identity",
        "faultatlas.domain.revision",
    ]
    observed = tuple(
        (
            cast(str, entry["module"]),
            cast(str, entry["slice_layer"]),
            cast(str, entry["symbol"]),
        )
        for entry in cast(list[dict[str, Any]], inventory["owned_symbols"])
    )
    assert observed == EXPECTED_OWNED_SYMBOLS
    absent = cast(list[str], inventory["absent_capabilities"])
    for capability in (
        "persistence",
        "storage",
        "migration",
        "durable_repository_snapshot_bytes",
        "git_or_filesystem_io",
    ):
        assert capability in absent
    assert not set(inventory["owned_modules"]) & set(
        inventory["supporting_authorities_not_owned"]
    )


def _assert_source_locks(document: dict[str, Any], *, verify_files: bool) -> None:
    locks = cast(dict[str, Any], document["source_locks"])
    production = cast(list[dict[str, Any]], locks["production_observations"])
    immutable = cast(list[dict[str, Any]], locks["immutable_inputs"])

    assert locks["production_observation_count"] == len(production) == 11
    assert locks["immutable_input_count"] == len(immutable)
    assert locks["total_lock_count"] == len(production) + len(immutable)
    assert locks["mutable_latest_or_current_pointer"] is False

    assert {cast(str, e["path"]) for e in production} == EXPECTED_PRODUCTION_FILES
    assert all(e["group"] == "production_observation" for e in production)
    assert all(e["layer"] == "S1.P04.closure_baseline" for e in production)

    paths = [cast(str, e["path"]) for e in immutable]
    assert len(paths) == len(set(paths)), "duplicate immutable input"
    assert paths == sorted(paths), "immutable inputs must be path-sorted"
    for forbidden in ("uv.lock", "docs/roadmap.md"):
        assert forbidden not in paths
    assert not any(p.startswith(CLOSURE_RELATIVE) for p in paths), (
        "the closure must not lock its own bytes"
    )
    assert sum(1 for p in paths if p.startswith(CORPUS_RELATIVE)) == 9
    assert any(p == S08_DECISION for p in paths)

    for entry in production + immutable:
        assert set(entry) == {
            "byte_length",
            "filesystem_mode",
            "git_mode",
            "group",
            "layer",
            "path",
            "sha256",
        }
        assert entry["git_mode"] == "100644"
        assert entry["filesystem_mode"] == "0644"
        if verify_files:
            path = REPOSITORY_ROOT / cast(str, entry["path"])
            assert path.is_file(), entry["path"]
            raw = path.read_bytes()
            assert _sha256(raw) == entry["sha256"], entry["path"]
            assert len(raw) == entry["byte_length"], entry["path"]


def _assert_deferred(document: dict[str, Any]) -> None:
    register = cast(dict[str, Any], document["deferred_register"])
    items = cast(list[dict[str, Any]], register["items"])

    assert register["count"] == len(items) == 7
    assert register["self_owned_open"] == 0
    assert register["ownership_complete"] is True
    assert register["disposition_totals"] == {
        "addressed": 3,
        "carried_forward": 3,
        "split": 1,
    }
    assert register["state_totals"] == {
        "evidence_insufficient": 2,
        "unknown_pending_additional_evidence": 1,
        "unsupported_current_scope": 1,
    }
    assert register["immediate_owner_totals"] == {"S1.P05": 1, "S2": 3}
    assert register["long_term_owner_totals"] == {"S1.P05": 1, "S2": 1, "S5": 2}
    assert [cast(str, i["deferred_id"]) for i in items] == [
        f"deferred:p04:{index:02d}" for index in range(1, 8)
    ]

    observed_dispositions: dict[str, int] = {}
    observed_states: dict[str, int] = {}
    immediate: dict[str, int] = {}
    long_term: dict[str, int] = {}
    for item in items:
        disposition = cast(str, item["disposition"])
        keys = set(item)
        assert BASE_DEFERRED_FIELDS <= keys
        if disposition == "addressed":
            assert keys == BASE_DEFERRED_FIELDS | {"addressed_by"}
            assert not keys & OWNER_FIELDS
        elif disposition == "split":
            assert keys == BASE_DEFERRED_FIELDS | {"addressed_by"} | OWNER_FIELDS
        else:
            assert disposition == "carried_forward"
            assert keys == BASE_DEFERRED_FIELDS | OWNER_FIELDS
            assert "addressed_by" not in keys
        if "addressed_by" in item:
            assert cast(list[str], item["addressed_by"])
        if "current_state" in item:
            state = cast(str, item["current_state"])
            assert state in PUBLISHED_STATE_VOCABULARY
            observed_states[state] = observed_states.get(state, 0) + 1
            for field, tally in (
                ("immediate_owner", immediate),
                ("preserved_long_term_owner", long_term),
            ):
                owner = cast(str, item[field])
                assert owner != "S1.P04", item["deferred_id"]
                tally[owner] = tally.get(owner, 0) + 1
        observed_dispositions[disposition] = (
            observed_dispositions.get(disposition, 0) + 1
        )
        reference = cast(dict[str, str], item["source_reference"])
        assert set(reference) == {"json_pointer", "path", "sha256"}
        assert reference["path"] == S08_DECISION

    assert observed_dispositions == register["disposition_totals"]
    assert observed_states == register["state_totals"]
    assert immediate == register["immediate_owner_totals"]
    assert long_term == register["long_term_owner_totals"]

    historical = items[6]
    assert historical["current_state"] == "unknown_pending_additional_evidence"
    assert historical["immediate_owner"] == "S2"
    serialized = json.dumps(register)
    assert "main" not in json.dumps(historical), "no branch value may be substituted"
    assert "default_branch_value" not in serialized

    default_branch = items[3]
    assert default_branch["immediate_owner"] == "S1.P05"
    assert default_branch["preserved_long_term_owner"] == "S1.P05"
    assert default_branch["current_state"] == "unsupported_current_scope"


def _assert_corpus(document: dict[str, Any]) -> None:
    corpus = cast(dict[str, Any], document["contract_corpus_assurance"])
    counts = cast(dict[str, int], corpus["vector_counts"])
    assert corpus["directory"] == CORPUS_RELATIVE
    assert corpus["version"] == "1"
    assert corpus["file_count"] == 9
    assert corpus["canonical_json_files"] == 4
    assert corpus["sidecar_count"] == 4
    assert counts == {
        "fixtures": 16,
        "invalid": 82,
        "replay": 26,
        "total": 158,
        "valid": 50,
    }
    assert counts["valid"] + counts["invalid"] + counts["replay"] == counts["total"]
    assert corpus["symbol_coverage"] == {"accounted_for": 7, "expected": 7}
    assert corpus["package_excluded"] is True
    assert corpus["no_production_capability"] is True
    assert corpus["closed_world"] == {
        "unknown_marker_rejected": True,
        "unknown_operation_rejected": True,
        "unknown_target_rejected": True,
    }
    assert corpus["replay_classifications"] == [
        "caller_supplied_association",
        "caller_supplied_selection",
        "deterministic_derivation",
        "retained_normalized_observation",
    ]
    assert corpus["test_only_executor"] == (
        "tests/test_repository_snapshot_contract_corpus.py"
    )


def _assert_vertical(document: dict[str, Any]) -> None:
    vertical = cast(dict[str, Any], document["canonical_vertical_assurance"])
    assert vertical["flattened_evidence_derived_snapshot_claimed"] is False
    assert vertical["no_product_aggregate_composed"] is True
    assert vertical["production_replay_io"] is False
    limits = cast(dict[str, Any], vertical["evidence_limits"])
    assert limits["retained_normalized_leaves"] == 4
    assert limits["retained_non_recursive_traversals"] == 6
    assert limits["retained_tree_entry_manifest"] is False
    assert limits["whole_repository_enumeration_claimed"] is False
    assert limits["verified_membership_claimed"] is False
    assert limits["root_tree_reachability_claimed"] is False
    layers = cast(list[dict[str, str]], vertical["layers"])
    assert [entry["classification"] for entry in layers] == [
        "retained_normalized_observation",
        "caller_supplied_selection",
        "deterministic_derivation",
        "caller_supplied_association",
    ]
    assert "evidence-derived repository snapshot" not in json.dumps(vertical)


def _assert_non_generalizations(document: dict[str, Any]) -> None:
    register = cast(dict[str, Any], document["non_generalizations"])
    items = cast(list[dict[str, str]], register["items"])
    subjects = [entry["subject"] for entry in items]
    assert register["count"] == len(items) == 23
    assert len(set(subjects)) == len(subjects)
    assert register["intentional_deferral_is_not_implementation_failure"] is True
    assert [entry["non_generalization_id"] for entry in items] == [
        f"non-generalization:{index:02d}" for index in range(1, 24)
    ]
    for required in (
        "a_supplied_path_binding_is_not_verified_repository_membership",
        "a_coverage_witness_is_not_snapshot_completeness",
        "a_failed_coverage_creates_no_absent_missing_or_unknown_path_state",
        "no_whole_repository_completeness",
        "no_verified_repository_membership",
        "no_known_absence",
        "no_historical_default_branch_substitution",
        "no_P04_default_branch_designation_model",
        "no_prefix_ancestry_or_tree_topology_semantics",
        "no_git_mode_semantics",
        "no_executable_bit_semantics",
        "no_symbolic_link_semantics",
        "no_gitlink_or_submodule_semantics",
        "S07_evidence_association_is_LEVEL_1_record_level_only",
        "no_semantic_json_fact_locator",
        "no_verification_corroboration_or_support_strength_claim",
        "no_confidence_or_review_semantics",
        "no_persistence_or_durable_snapshot_serialization",
        "P04_publishes_no_production_aggregate_composing_the_offline_vertical",
    ):
        assert required in subjects
    for entry in cast(list[dict[str, str]], register["projected_from"]):
        assert set(entry) == {"authority", "path", "sha256"}


def _assert_exit_criteria(document: dict[str, Any]) -> None:
    criteria = cast(dict[str, Any], document["exit_criteria"])
    items = cast(list[dict[str, str]], criteria["items"])
    assert criteria["count"] == len(items)
    assert criteria["unsatisfied_count"] == 0
    assert criteria["satisfied_count"] == len(items)
    assert all(entry["status"] == "satisfied" for entry in items)
    identifiers = [entry["criterion_id"] for entry in items]
    assert identifiers == [f"exit:{index:02d}" for index in range(1, len(items) + 1)]
    for entry in items:
        assert set(entry) == {"criterion_id", "evidence", "status", "subject"}
        assert entry["evidence"] and entry["subject"]


def _assert_ledger(document: dict[str, Any]) -> None:
    ledger = cast(dict[str, Any], document["slice_ledger"])
    entries = cast(list[dict[str, Any]], ledger["entries"])
    publications = cast(list[dict[str, Any]], ledger["publications"])

    assert ledger["entry_count"] == len(entries) == 10
    assert ledger["publication_count"] == len(publications) == 9
    assert [cast(str, e["slice_id"]) for e in entries] == list(EXPECTED_SLICE_IDS)
    assert [cast(int, e["ordinal"]) for e in entries] == list(range(1, 11))

    for entry in entries[:9]:
        assert entry["state"] == "complete_published"
        assert len(cast(list[str], entry["publication_ids"])) == 1

    final = entries[-1]
    assert set(final) == {"ordinal", "publication_ids", "slice_id", "state", "title"}
    assert final["slice_id"] == "S1.P04.S10"
    assert final["publication_ids"] == []
    assert final["state"] == "sealed_publication_candidate"

    for publication in publications:
        assert publication["publication_state"] == "merged"
        assert publication["merge_method"] == "protected_pull_request_squash_merge"
        assert publication["reviewed_tree_equals_squash_tree"] is True
        assert publication["reviewed_tree"] == publication["squash_tree"]
        pr_check = cast(dict[str, Any], publication["pull_request_check"])
        main_check = cast(dict[str, Any], publication["main_check"])
        assert pr_check["event"] == "pull_request"
        assert main_check["event"] == "push"
        assert pr_check["conclusion"] == main_check["conclusion"] == "success"
        assert pr_check["context"] == main_check["context"] == "validate"
        assert pr_check["head_sha"] == publication["reviewed_head_sha"]
        assert main_check["head_sha"] == publication["squash_sha"]
        settlement = cast(dict[str, Any], publication["review_settlement"])
        assert settlement["settlement"] == "clean"
        assert settlement["actionable_unresolved_thread_count"] == 0
        assert settlement["changes_requested_count"] == 0

    slice_ids = [cast(str, p["slice_id"]) for p in publications]
    assert slice_ids == list(EXPECTED_SLICE_IDS[:9])
    assert "S1.P04.S10" not in slice_ids


def _assert_publication_boundary(document: dict[str, Any]) -> None:
    assert document["publication_contract"] == EXPECTED_PUBLICATION_CONTRACT
    assurance = cast(dict[str, Any], document["assurance"])
    assert assurance["publication_state"] == "external_to_candidate_record"
    assert assurance["candidate_state"] == "sealed_publication_candidate"
    serialized = json.dumps(document["slice_ledger"])
    assert "S1.P04.S10" in serialized
    for publication in cast(
        list[dict[str, Any]],
        cast(dict[str, Any], document["slice_ledger"])["publications"],
    ):
        assert publication["slice_id"] != "S1.P04.S10"


def _assert_readiness(document: dict[str, Any]) -> None:
    readiness = cast(dict[str, Any], document["entry_readiness"])
    assert readiness["next_phase"] == "S1.P05"
    assert readiness["readiness"] == "eligible_to_begin"
    assert readiness["implementation_state"] == "not_started"
    assert readiness["unresolved_blocker_count"] == 0
    prerequisites = cast(list[dict[str, str]], readiness["prerequisites"])
    assert readiness["prerequisite_count"] == len(prerequisites) == 9
    for entry in prerequisites:
        assert set(entry) == {
            "evidence_owner",
            "prerequisite_id",
            "status",
            "subject",
        }
        assert entry["status"] == "satisfied"

    assurance = cast(dict[str, Any], document["assurance"])
    assert assurance["P05_readiness"] == "eligible_to_begin"
    assert assurance["P05_implementation_state"] == "not_started"
    assert assurance["self_owned_open"] == 0
    assert assurance["no_production_change"] is True
    assert assurance["no_unresolved_P04_product_blockers"] is True
    assert assurance["package_exclusion"] is True
    assert assurance["predecessor_artifacts"] == "locked_unchanged"


def _assert_handoff(document: dict[str, Any]) -> None:
    handoff = cast(dict[str, Any], document["p05_handoff"])
    constraints = cast(list[dict[str, str]], handoff["constraints"])
    assert handoff["constraint_count"] == len(constraints) == 6
    assert [entry["constraint_id"] for entry in constraints] == [
        f"p05-handoff:{index:02d}" for index in range(1, 7)
    ]
    text = " ".join(entry["statement"] for entry in constraints)
    for required in (
        "Mutable refs remain observations",
        "must not redefine that identity",
        "deferred:19 default-branch observation is owned by S1.P05",
        "historical default branch remains unknown and owned by S2",
        "transferred to S2 and S5",
        "LEVEL 1 record-level only",
        "append-only correction",
    ):
        assert required in text


def _validate(document: dict[str, Any], *, verify_files: bool = True) -> None:
    _assert_format(document)
    _assert_phase_identity(document)
    _assert_inventory(document)
    _assert_source_locks(document, verify_files=verify_files)
    _assert_deferred(document)
    _assert_corpus(document)
    _assert_vertical(document)
    _assert_non_generalizations(document)
    _assert_exit_criteria(document)
    _assert_ledger(document)
    _assert_publication_boundary(document)
    _assert_readiness(document)
    _assert_handoff(document)


# --- artifact ---------------------------------------------------------------


def test_closure_triple_is_exact() -> None:
    assert CLOSURE_ROOT.is_dir()
    assert {entry.name for entry in CLOSURE_ROOT.iterdir()} == EXPECTED_CLOSURE_FILES
    assert all(
        entry.is_file() and not entry.is_symlink() for entry in CLOSURE_ROOT.iterdir()
    )
    assert not (CLOSURE_ROOT / "closure.md.sha256").exists()


def test_closure_json_is_exactly_canonical() -> None:
    raw = (CLOSURE_ROOT / "closure.json").read_bytes()
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
    assert raw.endswith(b"\n") and not raw.endswith(b"\n\n")

    def walk(value: Any) -> None:
        assert not isinstance(value, float)
        if isinstance(value, dict):
            for item in cast(dict[str, Any], value).values():
                walk(item)
        elif isinstance(value, list):
            for item in cast(list[Any], value):
                walk(item)

    walk(document)


def test_sidecar_locks_closure_json_only() -> None:
    raw = (CLOSURE_ROOT / "closure.sha256").read_bytes()
    assert raw == f"{_digest(CLOSURE_ROOT / 'closure.json')}  closure.json\n".encode()
    assert b"closure.md" not in raw


def test_closure_json_carries_no_self_digest() -> None:
    serialized = (CLOSURE_ROOT / "closure.json").read_text(encoding="utf-8")
    assert _digest(CLOSURE_ROOT / "closure.json") not in serialized


@pytest.mark.parametrize("filename", tuple(sorted(LOCKED_CLOSURE_FILES)))
def test_closure_bytes_match_their_independent_lock(filename: str) -> None:
    locked = LOCKED_CLOSURE_FILES[filename]
    raw = (CLOSURE_ROOT / filename).read_bytes()
    assert len(raw) == locked.byte_length, filename
    assert _sha256(raw) == locked.sha256, filename


def test_markdown_is_derived_digest_synchronized_and_non_authoritative() -> None:
    raw = (CLOSURE_ROOT / "closure.json").read_bytes()
    markdown = (CLOSURE_ROOT / "closure.md").read_text(encoding="utf-8")
    document = _closure()

    assert markdown.startswith("# S1.P04 Repository Snapshot Model Phase Closure\n")
    assert f"Primary JSON SHA-256: `{_sha256(raw)}`" in markdown
    assert "sole durable semantic authority" in markdown
    assert "derived, non-authoritative view" in markdown
    assert "**S1.P05 implementation has not started.**" in markdown
    for heading in EXPECTED_HEADINGS:
        assert heading in markdown, heading
    for symbol in (entry[2] for entry in EXPECTED_OWNED_SYMBOLS):
        assert f"`{symbol}`" in markdown
    for entry in cast(
        list[dict[str, Any]],
        cast(dict[str, Any], document["deferred_register"])["items"],
    ):
        assert f"`{entry['deferred_id']}`" in markdown
    assert "evidence-derived repository snapshot" not in markdown


# --- full closed-world validation -------------------------------------------


def test_complete_closure_document_passes_every_independent_validator() -> None:
    _validate(_closure())


@pytest.mark.parametrize("mutation", EXPECTED_MUTATIONS)
def test_each_required_closure_mutation_is_rejected(mutation: str) -> None:
    document = _closure()
    register = cast(dict[str, Any], document["deferred_register"])
    items = cast(list[dict[str, Any]], register["items"])
    locks = cast(dict[str, Any], document["source_locks"])
    ledger = cast(dict[str, Any], document["slice_ledger"])

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
        locks["immutable_input_count"] = len(locks["immutable_inputs"])
        locks["total_lock_count"] = locks["immutable_input_count"] + 11
    elif mutation == "altered-production-source-count":
        cast(dict[str, Any], document["implementation_inventory"])[
            "production_python_source_count"
        ] = 12
    elif mutation == "altered-product-symbol-inventory":
        cast(
            list[dict[str, Any]], document["implementation_inventory"]["owned_symbols"]
        ).pop()
    elif mutation == "reordered-product-symbols":
        symbols = cast(
            list[dict[str, Any]], document["implementation_inventory"]["owned_symbols"]
        )
        symbols[0], symbols[1] = symbols[1], symbols[0]
    elif mutation == "s08-decision-digest-drift":
        items[0]["source_reference"]["path"] = "reference_corpus/absent.json"
    elif mutation == "s09-manifest-digest-drift":
        for entry in cast(list[dict[str, Any]], locks["immutable_inputs"]):
            if entry["path"].endswith("repository-snapshot/v1/manifest.json"):
                entry["sha256"] = "1" * 64
    elif mutation == "altered-vector-count":
        cast(dict[str, Any], document["contract_corpus_assurance"])["vector_counts"][
            "valid"
        ] = 49
    elif mutation == "omitted-corpus-symbol-coverage":
        cast(dict[str, Any], document["contract_corpus_assurance"])[
            "symbol_coverage"
        ] = {
            "accounted_for": 6,
            "expected": 7,
        }
    elif mutation == "nonzero-self-owned-open":
        register["self_owned_open"] = 1
    elif mutation == "omitted-deferred-entry":
        items.pop()
    elif mutation == "deferred-owner-omitted":
        del items[3]["immediate_owner"]
    elif mutation == "p04-retained-as-deferred-owner":
        items[3]["immediate_owner"] = "S1.P04"
    elif mutation == "addressed-entry-with-owner-fields":
        items[0]["immediate_owner"] = "S2"
    elif mutation == "split-entry-missing-addressed-by":
        del items[2]["addressed_by"]
    elif mutation == "carried-forward-entry-with-addressed-by":
        items[4]["addressed_by"] = ["S1.P04.S05"]
    elif mutation == "invented-disposition-state":
        items[4]["current_state"] = "closed_unsupported"
    elif mutation == "historical-default-branch-value-substituted":
        items[6]["subject"] = "P00 historical default branch was main"
    elif mutation == "omitted-non-generalization":
        cast(list[dict[str, Any]], document["non_generalizations"]["items"]).pop()
    elif mutation == "level-1-upgraded-to-verification":
        for entry in cast(
            list[dict[str, str]], document["non_generalizations"]["items"]
        ):
            if entry["subject"].startswith("S07_evidence_association"):
                entry["subject"] = "S07_evidence_association_verifies_the_fact"
    elif mutation == "flattened-evidence-derived-snapshot-claimed":
        cast(dict[str, Any], document["canonical_vertical_assurance"])[
            "flattened_evidence_derived_snapshot_claimed"
        ] = True
    elif mutation == "membership-brought-back-into-p04":
        cast(dict[str, Any], document["canonical_vertical_assurance"])[
            "evidence_limits"
        ]["verified_membership_claimed"] = True
    elif mutation == "p05-marked-started":
        cast(dict[str, Any], document["entry_readiness"])["implementation_state"] = (
            "in_progress"
        )
    elif mutation == "p05-marked-ineligible":
        cast(dict[str, Any], document["entry_readiness"])["readiness"] = "blocked"
    elif mutation == "deferred-19-owner-changed":
        items[3]["immediate_owner"] = "S2"
    elif mutation == "fabricated-s10-publication-facts":
        cast(dict[str, Any], document["publication_contract"])[
            "actual_S10_publication_facts_in_candidate"
        ] = True
    elif mutation == "s10-candidate-publication-ids-nonempty":
        cast(list[dict[str, Any]], ledger["entries"])[-1]["publication_ids"] = [
            "publication:s10"
        ]
    elif mutation == "s10-marked-published":
        cast(list[dict[str, Any]], ledger["entries"])[-1]["state"] = (
            "complete_published"
        )
    elif mutation == "exit-criterion-unsatisfied":
        cast(list[dict[str, Any]], document["exit_criteria"]["items"])[0]["status"] = (
            "unsatisfied"
        )
    elif mutation == "reordered-slice-ledger":
        entries = cast(list[dict[str, Any]], ledger["entries"])
        entries[0], entries[1] = entries[1], entries[0]
    elif mutation == "duplicated-slice-id":
        cast(list[dict[str, Any]], ledger["entries"])[1]["slice_id"] = "S1.P04.S01"
    elif mutation == "reviewed-squash-tree-mismatch":
        cast(list[dict[str, Any]], ledger["publications"])[0]["squash_tree"] = "0" * 40
    elif mutation == "pr-main-ci-event-swap":
        publication = cast(list[dict[str, Any]], ledger["publications"])[0]
        publication["pull_request_check"]["event"] = "push"
    elif mutation == "predecessor-digest-drift":
        for entry in cast(list[dict[str, Any]], locks["immutable_inputs"]):
            if entry["path"].endswith("s1-p03-phase-closure/closure.json"):
                entry["sha256"] = "2" * 64
    elif mutation == "production-persistence-capability-claim":
        cast(
            list[str], document["implementation_inventory"]["absent_capabilities"]
        ).remove("persistence")
    else:  # pragma: no cover - guarded by the parametrization
        raise AssertionError(f"unhandled mutation: {mutation}")

    with pytest.raises((AssertionError, KeyError, IndexError, ValueError)):
        _validate(document, verify_files=True)


# --- integrity and environment ----------------------------------------------


@pytest.mark.parametrize("relative", tuple(sorted(PREDECESSOR_DIGESTS)))
def test_predecessor_and_governance_bytes_are_unchanged(relative: str) -> None:
    assert _digest(REPOSITORY_ROOT / relative) == PREDECESSOR_DIGESTS[relative]


def test_production_surface_adds_only_history_after_this_closure() -> None:
    observed = {
        path.relative_to(REPOSITORY_ROOT).as_posix()
        for path in (REPOSITORY_ROOT / "src").rglob("*.py")
    }
    assert observed == CURRENT_PRODUCTION_FILES
    assert len(observed) == 12
    assert observed - EXPECTED_PRODUCTION_FILES == {HISTORY_MODULE}
    assert EXPECTED_PRODUCTION_FILES - observed == set()
    assert len(EXPECTED_PRODUCTION_FILES) == 11


def test_owned_symbols_match_the_live_published_modules() -> None:
    import faultatlas.domain.snapshot as snapshot_module
    import faultatlas.domain.snapshot_evidence_link as link_module

    published = list(snapshot_module.__all__) + list(link_module.__all__)
    assert published == [entry[2] for entry in EXPECTED_OWNED_SYMBOLS]
    for module_name, _, symbol in EXPECTED_OWNED_SYMBOLS:
        module = (
            snapshot_module
            if module_name == "faultatlas.domain.snapshot"
            else link_module
        )
        assert hasattr(module, symbol)


def test_deferred_source_references_resolve_into_the_s08_decision() -> None:
    decision = json.loads((REPOSITORY_ROOT / S08_DECISION).read_text(encoding="utf-8"))
    register = cast(dict[str, Any], _closure()["deferred_register"])
    assert cast(dict[str, str], register["source_decision"])["sha256"] == _digest(
        REPOSITORY_ROOT / S08_DECISION
    )
    inherited = cast(dict[str, Any], decision["inherited_subject_register"])
    assert inherited["self_owned_open"] == 0
    assert inherited["count"] == 7

    for index, item in enumerate(cast(list[dict[str, Any]], register["items"])):
        reference = cast(dict[str, str], item["source_reference"])
        assert reference["sha256"] == _digest(REPOSITORY_ROOT / reference["path"])
        record = cast(dict[str, Any], _resolve(decision, reference["json_pointer"]))
        assert record["disposition_id"] == f"disposition:s1-p04-s08:{index + 1:02d}"
        assert record["disposition"] == item["disposition"]
        if "current_state" in item:
            source = (
                record
                if "current_state" in record
                else cast(dict[str, Any], record["split"])["carried_forward_remainder"]
            )
            assert source["current_state"] == item["current_state"]
            assert source["immediate_owner"] == item["immediate_owner"]
            assert (
                source["preserved_long_term_owner"] == item["preserved_long_term_owner"]
            )


def test_corpus_assurance_matches_the_sealed_manifest() -> None:
    manifest = json.loads(
        (REPOSITORY_ROOT / CORPUS_RELATIVE / "manifest.json").read_text("utf-8")
    )
    corpus = cast(dict[str, Any], _closure()["contract_corpus_assurance"])
    summary = cast(dict[str, Any], manifest["vector_summary"])
    counts = cast(dict[str, int], corpus["vector_counts"])

    assert corpus["corpus_id"] == manifest["corpus_identity"]["id"]
    assert corpus["version"] == manifest["corpus_identity"]["version"]
    assert corpus["corpus_format"] == manifest["format"]["name"]
    assert counts["valid"] == cast(dict[str, Any], summary["valid"])["count"]
    assert counts["invalid"] == cast(dict[str, Any], summary["invalid"])["count"]
    assert counts["replay"] == cast(dict[str, Any], summary["replay"])["count"]
    assert counts["total"] == summary["total_vectors"]
    assert counts["fixtures"] == summary["fixtures"]
    assert corpus["symbol_coverage"]["expected"] == len(manifest["target_symbols"])
    assert corpus["files"] == sorted(
        entry.name for entry in (REPOSITORY_ROOT / CORPUS_RELATIVE).iterdir()
    )
    assert corpus["replay_classifications"] == sorted(
        cast(dict[str, Any], manifest["replay_contract"])["classifications"]
    )


def test_closure_is_excluded_from_the_packaged_source_root() -> None:
    assert not CLOSURE_RELATIVE.startswith("src/")
    parts = CLOSURE_ROOT.relative_to(REPOSITORY_ROOT).parts
    assert parts[0] == "reference_corpus"
    assert parts[-2] == "closures"


# --- roadmap ----------------------------------------------------------------


def test_roadmap_records_phase_completion_and_p05_readiness() -> None:
    roadmap = " ".join(
        (REPOSITORY_ROOT / "docs/roadmap.md").read_text(encoding="utf-8").split()
    )
    assert "`S1.P04` is complete" in roadmap
    assert "`S1.P04.S10` is complete" in roadmap
    assert "`S1.P05` is active and incomplete" in roadmap
    assert "`S1.P05.S04` are complete" in roadmap
    assert "`S1.P05.S05` is next and not started" in roadmap
    assert "`S1.P06` through `S1.P10` remain not started" in roadmap
    assert CLOSURE_RELATIVE in roadmap
    assert "`S1.P04` is active and incomplete" not in roadmap
    assert "`S1.P04.S10` is next and not started" not in roadmap
    assert "`S1.P05` is complete" not in roadmap
    assert "S1.P05 implementation has begun" not in roadmap
    # A precondition that forbids the closure this file records would leave the
    # roadmap self-contradictory, so its retirement is asserted, not assumed.
    assert "closure cannot be presumed reachable" not in roadmap
    assert "remains unresolved or undispositioned" not in roadmap
    assert "dispositioned, not resolved" in roadmap
    assert "The gate is satisfied by explicit transferred ownership" in roadmap
