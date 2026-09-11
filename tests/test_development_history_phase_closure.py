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
import re
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

# The production surface this closure sealed as its observed inventory. It is a
# historical lock, compared below against the closure's own `observations`, so it
# stays at 13 even though the live tree has since gained S1.P06.S01's module.
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

# Published after this closure was sealed: S1.P06.S01 added the fault module,
# S1.P06.S04 the source-relationship bridge, and S1.P06.S09 the fault-evidence
# bridge.
FAULT_MODULE = "src/faultatlas/domain/fault.py"
FAULT_SOURCE_RELATIONSHIP_MODULE = "src/faultatlas/domain/fault_source_relationship.py"
FAULT_REPAIR_MODULE = "src/faultatlas/domain/fault_repair.py"
FAULT_TEST_MODULE = "src/faultatlas/domain/fault_test.py"
FAULT_INTERPRETATION_MODULE = "src/faultatlas/domain/fault_interpretation.py"
FAULT_INSTANCE_MODULE = "src/faultatlas/domain/fault_instance.py"
FAULT_EVIDENCE_LINK_MODULE = "src/faultatlas/domain/fault_evidence_link.py"

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

# Authored from the verified publication history, not from the document it
# checks. Both are projections of the same gathered evidence, held in separate
# files, so a later silent edit to either is caught by the other.
EXPECTED_PUBLICATIONS: tuple[
    tuple[str, int, str, str, str, int, int, int, int], ...
] = (
    (
        "S1.P05.S01",
        54,
        "feat/s1-p05-s01-pull-request-revision-role-binding",
        "6cb611fc5ea7b46ab355c61d437c87381bb4008d",
        "7e5732eacc38aaeb844d40bdb66ff72b5ee38057",
        1,
        1,
        2,
        1,
    ),
    (
        "S1.P05.S02",
        55,
        "feat/s1-p05-s02-pull-request-change-set",
        "c5e0e3043ebe6dfeaa8b91657811eec1c0128ecc",
        "21e6a48af3f568333bd41b216cdfabe749a00c6c",
        1,
        1,
        2,
        1,
    ),
    (
        "S1.P05.S02.C01",
        56,
        "fix/s1-p05-s02-c01-change-set-boundary",
        "d17b868c32c8887d30b527fdd2294046db389881",
        "6430049374bcf660f058cf11e77123e237914722",
        1,
        1,
        0,
        0,
    ),
    (
        "S1.P05.S02.C01.A01",
        57,
        "test/s1-p05-s02-c01-a01-boundary-assurance",
        "f7377b866c8515f180c9303c0bdfb1978c8a6907",
        "b2cb023621288e7d11ff1dcdb4b87f15b2b18714",
        1,
        1,
        0,
        0,
    ),
    (
        "S1.P05.S03",
        58,
        "feat/s1-p05-s03-review-revision-approval",
        "a34fee7a77a74bef9431c29570ad396b651d1e09",
        "107e677534e50719d3b5c5d568d0b4ed7b977c0e",
        1,
        1,
        0,
        0,
    ),
    (
        "S1.P05.S03.A01",
        59,
        "test/s1-p05-s03-a01-approved-revision-child-boundary",
        "f9fe795557e7ccbf6b64dd5b18312cc0ddc25af9",
        "f4f58e87461764ba09c43dd332fe3861e5c90a87",
        1,
        1,
        0,
        0,
    ),
    (
        "S1.P05.S04",
        60,
        "feat/s1-p05-s04-merge-revision-outcome",
        "e496cb6f9a6ed23a673dc7f5c9bf92003a68a95c",
        "261d4c4685e73fb82380a13f34627377abb4e746",
        1,
        1,
        0,
        0,
    ),
    (
        "S1.P05.S04.A01",
        61,
        "test/s1-p05-s04-a01-parent-count-independence",
        "9aa66ee2a1320ab294a35a6ddd49dc646db1dc45",
        "816f70341078883c8c92f7a64c11f0a5a0d1da76",
        1,
        1,
        0,
        0,
    ),
    (
        "S1.P05.S05",
        62,
        "feat/s1-p05-s05-head-ref-deletion",
        "6a9bfa170883a568860240296be2212293783710",
        "57761ebf2bebf31155f4819d1a015ed7cdc55d33",
        1,
        1,
        0,
        0,
    ),
    (
        "S1.P05.S06",
        63,
        "s1-p05-s06-pull-request-historical-occurrence-time",
        "12da03d7f5b938e5a26a534cfffc753884d01c28",
        "3253e804f86f7d991e75f33f1c2ba4e034020a88",
        1,
        1,
        0,
        0,
    ),
    (
        "S1.P05.S06.A01",
        64,
        "s1-p05-s06-a01-occurrence-time-boundary-assurance",
        "c262b13fd280bbd5ab1de236f0368ee10d1c125f",
        "6fc04733fe1ecde78bc8f6df739656a6c58ed4f1",
        1,
        1,
        0,
        0,
    ),
    (
        "S1.P05.S06.A01.C01",
        65,
        "s1-p05-s06-a01-c01-remove-interpreter-sensitive-freeze",
        "7a12d5519dc7883a6269be83ead28504c0f7a4ea",
        "2c6fa40d47250cb8e66e6d7fe9604a98a29de377",
        1,
        1,
        2,
        1,
    ),
    (
        "S1.P05.S06.A01.C02",
        66,
        "test/s1-p05-s06-a01-c02-remove-source-freeze",
        "48ec5d5fa7a50bf15935ec1d48f3bbd6f9612c2e",
        "def12890085c011d5b59b4843b7d67bf166af738",
        1,
        1,
        0,
        0,
    ),
    (
        "S1.P05.S07",
        67,
        "feat/s1-p05-s07-history-evidence-link",
        "d28a37ded9552c72881c0a8bc1c2f81992c357dc",
        "a090c3b342fe0432e7f19a2759afb52a42a51fdd",
        1,
        1,
        4,
        2,
    ),
    (
        "S1.P05.S07.A01",
        68,
        "test/s1-p05-s07-a01-link-boundary-assurance",
        "01a769c89bdbe2a4c739c972e4f292165e3e1e7f",
        "75000a92696146d6476e68f51bcae176c533cf64",
        2,
        1,
        0,
        0,
    ),
    (
        "S1.P05.S08",
        69,
        "docs/s1-p05-s08-deferred-subject-disposition",
        "c0f44e413309b2a8bd043148bb8b6bbf3417cbe4",
        "e1d673b2a26811b432bcf1a28e012100018edea5",
        1,
        1,
        4,
        2,
    ),
    (
        "S1.P05.S08.C01",
        70,
        "docs/s1-p05-s08-c01-owner-topology-correction",
        "f746210880f1f0bf1db7205a52a1c382a59ea02d",
        "676a666bf0924f210107dc735fe8bc8bf56bfc7b",
        1,
        1,
        12,
        7,
    ),
    (
        "S1.P05.S09",
        71,
        "feat/s1-p05-s09-development-history-contract-corpus",
        "72b52f25f9cdb12a042325aa68b8bd17ce3dc3e7",
        "61e1f67a1792b9eb20758d26988f8aa5988b163c",
        1,
        1,
        165,
        77,
    ),
)
EXPECTED_REVIEW_TOTAL = 191
EXPECTED_THREAD_TOTAL = 91

EXPECTED_SUPERSEDED_CANDIDATES = ((53, 54, "closed", False),)

PUBLICATION_FIELDS = frozenset(
    {
        "id",
        "slice_id",
        "pull_request",
        "topic_branch",
        "publication_state",
        "merge_method",
        "reviewed_head_sha",
        "reviewed_tree",
        "squash_sha",
        "squash_tree",
        "reviewed_tree_equals_squash_tree",
        "pull_request_check",
        "main_check",
        "review_settlement",
    }
)
EXPECTED_EXIT_CRITERION_COUNT = 25
EXPECTED_EXIT_SUBJECTS = (
    "S1.P05.S01_through_S1.P05.S09_are_published",
    "every_reviewed_tree_equals_its_squash_tree",
    "every_required_pull_request_and_natural_main_check_succeeded",
    "every_publication_settled_with_zero_unresolved_review_threads",
    "every_publication_used_protected_squash_merge",
    "no_admin_or_ruleset_bypass_was_used",
    "the_nine_owned_symbols_are_exported_by_the_two_owned_modules",
    "every_owned_symbol_is_covered_by_the_S09_corpus",
    "the_development_history_v1_corpus_is_sealed_and_its_four_digests_verify",
    "the_corpus_is_excluded_from_the_built_package",
    "the_corpus_introduces_no_production_capability",
    "inherited_deferred_subjects_are_dispositioned_exactly_once",
    "deferred_ownership_is_complete",
    "S1.P05_owns_no_open_deferred_subject",
    "the_S1.P05.S08_decision_bytes_are_unchanged_by_the_S08.C01_correction",
    "every_predecessor_artifact_is_locked_unchanged",
    "S1.P05.S10_adds_no_production_behaviour",
    "the_closure_records_no_evidence_of_its_own_publication",
    "every_S1.P06_entry_prerequisite_is_satisfied",
    "S1.P06_implementation_has_not_started",
    "every_source_lock_digest_matches_the_artifact_it_names",
    "the_phase_adds_no_network_persistence_or_filesystem_capability",
    "the_declared_non_goals_remain_non_goals",
    "the_vector_totals_reconcile_with_the_declared_summary",
    "PR53_is_recorded_as_a_closed_unmerged_superseded_candidate_not_a_publication",
)
EXPECTED_DISTINCT_EVIDENCE = 21
EXPECTED_PREREQUISITE_COUNT = 10
EXPECTED_PREREQUISITES = (
    ("S1.P01", "stable_repository_identity_available"),
    ("S1.P02", "immutable_revision_identity_available"),
    ("S1.P02", "mutable_ref_observations_available"),
    ("S1.P02", "revision_qualified_paths_and_bounded_locators_available"),
    ("S1.P03", "evidence_provenance_and_durable_record_references_available"),
    ("S1.P04", "repository_snapshot_contracts_published"),
    ("S1.P05.S01-S07", "bounded_development_history_contracts_published"),
    ("S1.P05.S08", "inherited_deferred_ownership_is_complete"),
    ("S1.P05.S09", "development_history_contract_corpus_published"),
    ("S1.P05.S10", "development_history_phase_closure_sealed"),
)
EXPECTED_HANDOFF_CONSTRAINT_COUNT = 6
EXPECTED_ABSENT_CAPABILITIES = (
    "production_contract_corpus_reader",
    "production_contract_corpus_writer",
    "production_contract_corpus_validator",
    "production_development_history_reader",
    "production_development_history_writer",
    "durable_development_history_bytes",
    "persistence",
    "storage",
    "migration",
    "format_registry",
    "git_or_filesystem_io",
    "github_api_client",
    "network_io",
)
EXPECTED_TARGET_CLASSES = (
    "record_model_target",
    "vocabulary_enum_target",
    "record_model_target",
    "record_model_target",
    "record_model_target",
    "record_model_target",
    "record_model_target",
    "record_model_target",
    "record_model_target",
)

EXPECTED_SECTIONS = frozenset(
    {
        "assurance",
        "canonical_vertical_assurance",
        "contract_corpus_assurance",
        "deferred_register",
        "entry_readiness",
        "exit_criteria",
        "format",
        "implementation_inventory",
        "non_generalizations",
        "p06_handoff",
        "phase_identity",
        "publication_contract",
        "slice_ledger",
        "source_locks",
    }
)
ENTRY_FIELDS = frozenset({"ordinal", "publication_ids", "slice_id", "state", "title"})
CANDIDATE_FIELDS = frozenset(
    {
        "head_sha",
        "historical_threads_intentionally_preserved",
        "merged",
        "pull_request",
        "state",
        "status",
        "superseded_by_pull_request",
        "thread_count",
        "unresolved_historical_thread_count",
    }
)
# `S1.P05.S10` as a JSON string value appears exactly three times: the phase
# identity, its slice-ledger entry, and the S1.P06 entry prerequisite whose
# evidence owner is this closure. Any further occurrence is a fact about this
# slice that a sealed publication candidate cannot yet hold.
EXPECTED_S10_MENTIONS = 3

# Contract roots published after this closure was sealed. A sealed closure locks
# the corpus as it stood when it was written, so a later Phase's own root lies
# outside its lock set by construction rather than by omission. Dropping a
# predecessor artifact is still a failure below.
SUCCESSOR_CONTRACT_ROOTS = ("reference_corpus/contracts/fault-instance/",)

UNLOCKED_WORKING_ARTIFACTS = frozenset(
    {
        # P00-era working material and the two acquisition-pair sidecars. The
        # S1.P04 closure left exactly these unlocked; the rule is inherited, not
        # invented here.
        "reference_corpus/pytest-4412/acquisitions"
        "/run-0001-s04-v1-base-4c9cde74-head-690a63b9/acquisition.sha256",
        "reference_corpus/pytest-4412/analysis/s06-current-contract-gap-matrix"
        "/gap-matrix.json",
        "reference_corpus/pytest-4412/analysis/s06-current-contract-gap-matrix"
        "/gap-matrix.md",
        "reference_corpus/pytest-4412/analysis/s06-current-contract-gap-matrix"
        "/gap-matrix.sha256",
        "reference_corpus/pytest-4412/case/case.json",
        "reference_corpus/pytest-4412/case/case.sha256",
        "reference_corpus/pytest-4412/corrections/s04-c01-acquisition-closure"
        "/correction.sha256",
    }
)

CHECK_FIELDS = frozenset(
    {"attempt", "conclusion", "context", "event", "job_id", "run_id", "workflow"}
)
SETTLEMENT_FIELDS = frozenset(
    {
        "actionable_unresolved_thread_count",
        "changes_requested_count",
        "review_count",
        "settlement",
        "thread_count",
    }
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
    "## Superseded publication candidates",
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
    # the classes the reviews proved inert
    "forged-merge-record-section",
    "s10-publication-fact-smuggled-into-its-entry",
    "immutable-lock-set-truncated",
    "real-but-unlocked-corpus-file-added",
    "production-observation-duplicated",
    "production-observations-reordered",
    "publication-squash-shas-swapped-between-slices",
    "publication-reviewed-heads-swapped",
    "review-count-inflated",
    "thread-count-inflated",
    "ci-attempt-falsified",
    "run-identifier-falsified",
    "topic-branch-falsified",
    "check-event-swapped",
    "exit-criteria-truncated",
    "exit-evidence-all-point-at-one-address",
    "exit-subject-replaced",
    "entry-prerequisites-truncated",
    "handoff-constraints-truncated",
    "absent-capability-list-reordered",
    "format-canonicalization-relaxed",
    "format-marked-public-contract",
    "assurance-lock-total-disagrees",
    "assurance-exit-total-disagrees",
    "sealed-at-disagrees-between-sections",
    "superseded-candidate-marked-merged",
    "superseded-candidate-claimed-as-publication",
    "vocabulary-enum-relabelled-as-record-model",
    "slice-entry-gains-a-field",
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


def _cell(value: Any) -> str:
    """A table cell is a code span or an em dash; nothing else reaches a table."""
    if value is None or value == "":
        return "—"
    text = str(value)
    assert "`" not in text and "|" not in text and "\n" not in text, text
    return f"`{text}`"


def _plain(value: Any) -> str:
    text = str(value)
    assert "|" not in text and "\n" not in text, text
    return text


def _render_markdown(document: dict[str, Any], digest: str) -> str:
    """Rebuild closure.md from closure.json exactly as the publisher does.

    The projection is regenerated and compared byte for byte, so a doctored
    document fails rather than merely failing to contain a probed substring.
    """
    pi = cast(dict[str, Any], document["phase_identity"])
    sl = cast(dict[str, Any], document["slice_ledger"])
    ii = cast(dict[str, Any], document["implementation_inventory"])
    dr = cast(dict[str, Any], document["deferred_register"])
    cca = cast(dict[str, Any], document["contract_corpus_assurance"])
    cva = cast(dict[str, Any], document["canonical_vertical_assurance"])
    ec = cast(dict[str, Any], document["exit_criteria"])
    er = cast(dict[str, Any], document["entry_readiness"])
    hs = cast(dict[str, Any], document["p06_handoff"])
    lk = cast(dict[str, Any], document["source_locks"])
    pc = cast(dict[str, Any], document["publication_contract"])
    manifest = json.loads(
        (REPOSITORY_ROOT / CORPUS_RELATIVE / "manifest.json").read_bytes()
    )
    entries = cast(list[dict[str, Any]], sl["entries"])
    publications = cast(list[dict[str, Any]], sl["publications"])

    lines: list[str] = []
    add = lines.append
    add(f"# {pi['phase']} {pi['title']} Phase Closure\n")
    add("## Exact primary JSON digest\n")
    add(f"Primary JSON SHA-256: `{digest}`\n")
    add("## Derived and non-authoritative warning\n")
    add(
        "`closure.json` is the sole durable semantic authority for this Phase "
        "closure. This Markdown is a derived, non-authoritative view and never an "
        "independent authority. Where the two differ, the JSON governs.\n"
    )
    add("## Executive Phase-closure verdict\n")
    add(
        f"`{pi['phase']} — {pi['title']}` is **{pi['phase_state']}** across "
        f"{pi['slice_count']} Slices, `{entries[0]['slice_id']}` through "
        f"`{entries[-1]['slice_id']}`. The Phase adds no production capability "
        "beyond its published contracts, changed no production Python source in "
        "its governance and corpus Slices, and closes with no deferred subject "
        "still owned by itself.\n"
    )
    add("## Phase identity and scope\n")
    modules = ", ".join(f"`{m}`" for m in cast(list[str], ii["owned_modules"]))
    support = ", ".join(
        f"`{m}`" for m in manifest["scope"]["supporting_authorities_not_owned"]
    )
    add(
        f"Owned modules: {modules}. Owned product symbols: "
        f"**{ii['owned_symbol_count']}** — {ii['record_model_count']} record models "
        f"and {ii['vocabulary_enum_count']} vocabulary enum. Production Python "
        f"sources observed: **{lk['production_observation_count']}**. Production "
        "change in this Slice: `False`.\n"
    )
    add(f"Supporting authorities that `{pi['phase']}` does not own: {support}.\n")

    add("## Product surface\n")
    add("| Slice | Module | Symbol | Class |")
    add("| --- | --- | --- | --- |")
    for symbol in cast(list[dict[str, Any]], ii["owned_symbols"]):
        add(
            f"| {_cell(symbol['slice_layer'])} | {_cell(symbol['module'])} "
            f"| {_cell(symbol['symbol'])} | {_cell(symbol['target_class'])} |"
        )
    add("")

    add("## Ordered Slice and publication ledger\n")
    add(f"{sl['entry_count']} Slice entries, {sl['publication_count']} published.\n")
    add("| Slice | State | Title |")
    add("| --- | --- | --- |")
    for entry in entries:
        add(
            f"| {_cell(entry['slice_id'])} | {_cell(entry['state'])} "
            f"| {_plain(entry['title'])} |"
        )
    add("")
    add("| Publication | PR | Reviewed head | Squash | Trees equal |")
    add("| --- | --- | --- | --- | --- |")
    for publication in publications:
        add(
            f"| {_cell(publication['slice_id'])} | {_cell(publication['pull_request'])} "
            f"| {_cell(publication['reviewed_head_sha'][:12])} "
            f"| {_cell(publication['squash_sha'][:12])} "
            f"| {_cell(publication['reviewed_tree_equals_squash_tree'])} |"
        )
    add("")

    add("## Superseded publication candidates\n")
    candidates = cast(list[dict[str, Any]], sl["superseded_candidates"])
    add(
        f"{sl['superseded_candidate_count']} closed, unmerged candidate opened and "
        "abandoned inside the Phase. A superseded candidate is audit history, never "
        "a Slice publication, and its historical threads are preserved unresolved "
        "rather than tidied away.\n"
    )
    add("| PR | State | Merged | Superseded by | Threads | Unresolved |")
    add("| --- | --- | --- | --- | --- | --- |")
    for candidate in candidates:
        add(
            f"| {_cell(candidate['pull_request'])} | {_cell(candidate['state'])} "
            f"| {_cell(candidate['merged'])} "
            f"| {_cell(candidate['superseded_by_pull_request'])} "
            f"| {_cell(candidate['thread_count'])} "
            f"| {_cell(candidate['unresolved_historical_thread_count'])} |"
        )
    add("")

    add("## S1.P05.S08 disposition summary\n")
    totals = ", ".join(
        f"{v} {k.replace('_', ' ')}"
        for k, v in sorted(cast(dict[str, int], dr["disposition_totals"]).items())
    )
    add(
        f"All **{dr['count']}** inherited subjects are dispositioned exactly once: "
        f"{totals}. `self_owned_open == {dr['self_owned_open']}`.\n"
    )
    add("| ID | Subject | Disposition | State | Immediate | Long-term |")
    add("| --- | --- | --- | --- | --- | --- |")
    for item in cast(list[dict[str, Any]], dr["items"]):
        add(
            f"| {_cell(item['subject_id'])} | {_plain(item['subject'])} "
            f"| {_cell(item['disposition'])} | {_cell(item.get('current_state'))} "
            f"| {_cell(item.get('immediate_owner'))} "
            f"| {_cell(item.get('preserved_long_term_owner'))} |"
        )
    add("")
    add("## Deferred ownership\n")
    add(
        f"`ownership_complete: {dr['ownership_complete']}`. Immediate owners "
        f"{dr['immediate_owner_totals']}; long-term owners "
        f"{dr['long_term_owner_totals']}. No subject remains owned by "
        f"`{pi['phase']}`.\n"
    )
    add("## S1.P05.S09 contract corpus summary\n")
    vc = cast(dict[str, Any], cca["vector_counts"])
    coverage = cast(dict[str, Any], cca["symbol_coverage"])
    add(
        f"`{cca['corpus_id']}` v{cca['version']} at `{cca['directory']}`: "
        f"{cca['file_count']} files, {cca['canonical_json_files']} canonical JSON, "
        f"{cca['sidecar_count']} sidecars. Vectors: **{vc['valid']} valid, "
        f"{vc['invalid']} invalid, {vc['replay']} replay, {vc['total']} total** over "
        f"{vc['fixtures']} fixtures. Symbol coverage "
        f"{coverage['accounted_for']}/{coverage['expected']}. Executor "
        f"`{cca['test_only_executor']}`; package excluded; no production capability; "
        "unknown target, operation, and marker all rejected.\n"
    )
    add("## Canonical vertical assurance\n")
    add("| Layer | Provenance |")
    add("| --- | --- |")
    for layer in cast(list[dict[str, Any]], cva["layers"]):
        add(f"| {_cell(layer['layer'])} | {_cell(layer['classification'])} |")
    add("")
    limits = cast(dict[str, Any], cva["evidence_limits"])
    add(
        f"Retained role source positions: "
        f"`{limits['retained_role_source_positions']}`. "
        f"`flattened_evidence_derived_history_claimed: "
        f"{cva['flattened_evidence_derived_history_claimed']}`; no product aggregate "
        "is composed, no complete history graph is claimed, and no historical "
        "default branch is inferred.\n"
    )
    add("## Non-generalizations\n")
    for note in cast(list[dict[str, Any]], document["non_generalizations"]["items"]):
        add(f"- `{note['non_generalization_id']}` — {_plain(note['subject'])}")
    add("")
    add("## Exit criteria\n")
    add(
        f"{ec['satisfied_count']} of {ec['count']} satisfied, "
        f"{ec['unsatisfied_count']} unsatisfied.\n"
    )
    for item in cast(list[dict[str, Any]], ec["items"]):
        add(
            f"- `{item['criterion_id']}` — {_plain(item['subject'])} "
            f"(`{item['status']}`, evidence `{item['evidence']}`)"
        )
    add("")
    add(f"## {er['next_phase']} entry readiness\n")
    add(
        f"`{er['next_phase']}` is `{er['readiness']}` with implementation state "
        f"`{er['implementation_state']}`. {er['prerequisite_count']} prerequisites, "
        "all satisfied.\n"
    )
    for prerequisite in cast(list[dict[str, Any]], er["prerequisites"]):
        add(
            f"- `{prerequisite['prerequisite_id']}` — "
            f"{_plain(prerequisite['subject'])} "
            f"(owner `{prerequisite['evidence_owner']}`)"
        )
    add("")
    add(f"## {er['next_phase']} handoff\n")
    add(
        f"`{er['next_phase']}` receives {hs['received_subject_count']} subject and "
        f"{hs['requirement_count']} requirements from `{hs['source_handoff_id']}`, "
        f"status `{hs['status']}`.\n"
    )
    for constraint in cast(list[dict[str, Any]], hs["constraints"]):
        add(f"- `{constraint['constraint_id']}` — {_plain(constraint['statement'])}")
    add("")
    add("## Publication candidate boundary\n")
    add(
        f"This record is a `{document['format']['publication_state']}`. "
        f"`actual_S10_publication_facts_in_candidate: "
        f"{pc['actual_S10_publication_facts_in_candidate']}` — this closure records "
        "no pull request, reviewed head, squash SHA, or natural-main run of its own, "
        "because none exists when these bytes are sealed. Its publication evidence "
        f"lives at `{pc['future_publication_evidence_location']}`.\n"
    )
    add("## Source locks\n")
    add(
        f"{lk['production_observation_count']} closure-baseline production "
        f"observations and {lk['immutable_input_count']} immutable inputs, "
        f"{lk['total_lock_count']} locks total. Production observations are baseline "
        "records, not ownership claims; predecessor corpora, closures, and decisions "
        "remain byte-identical."
    )
    return "\n".join(lines) + "\n"


# --- independent validators --------------------------------------------------


def _assert_closed_world(document: dict[str, Any]) -> None:
    """The document publishes these sections and no others.

    Without this, a sealed candidate can be handed real evidence of its own
    merge in a section nobody enumerated, and every existing assertion still
    passes.
    """
    assert set(document) == EXPECTED_SECTIONS, {
        "unexpected": sorted(set(document) - EXPECTED_SECTIONS),
        "missing": sorted(EXPECTED_SECTIONS - set(document)),
    }
    ledger = cast(dict[str, Any], document["slice_ledger"])
    for entry in cast(list[dict[str, Any]], ledger["entries"]):
        assert set(entry) == ENTRY_FIELDS, entry["slice_id"]
    for candidate in cast(list[dict[str, Any]], ledger["superseded_candidates"]):
        assert set(candidate) == CANDIDATE_FIELDS, candidate["pull_request"]

    # No section may smuggle in publication facts about S1.P05.S10 itself.
    forbidden = ("squash_sha", "merge_commit", "merged_at", "merge_record")
    serialized = json.dumps(document, sort_keys=True)
    closing = cast(list[dict[str, Any]], ledger["entries"])[-1]
    assert closing["slice_id"] == "S1.P05.S10"
    assert not (set(closing) & set(forbidden)), closing
    # The closing slice's own identifiers must appear nowhere in the record.
    assert serialized.count('"S1.P05.S10"') == EXPECTED_S10_MENTIONS


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

    assert tuple(cast(list[str], inventory["absent_capabilities"])) == (
        EXPECTED_ABSENT_CAPABILITIES
    )
    assert (
        inventory["record_model_count"] + inventory["vocabulary_enum_count"]
        == (inventory["owned_symbol_count"])
    )
    assert tuple(entry["target_class"] for entry in symbols) == EXPECTED_TARGET_CLASSES


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

    # An ordered list, not a set: a set collapses a duplicate and lets the
    # counts inflate consistently around it.
    assert [entry["path"] for entry in observations] == sorted(CURRENT_PRODUCTION_FILES)

    # Membership, not merely arithmetic. The immutable set is derived from the
    # same inclusion rule the S1.P04 closure used -- every tracked
    # reference_corpus path except this closure, the P00-era working artifacts,
    # and the two acquisition-pair sidecars -- so dropping a predecessor
    # artifact is a failure rather than a smaller consistent number.
    if verify_files:
        tracked = subprocess.run(  # noqa: S603 - literal argv, no shell
            ["git", "ls-files", "reference_corpus/"],
            cwd=REPOSITORY_ROOT,
            capture_output=True,
            check=False,
        )
        assert tracked.returncode == 0, tracked.stderr
        expected = {
            path
            for path in tracked.stdout.decode("utf-8").split()
            if path not in UNLOCKED_WORKING_ARTIFACTS
            and not path.startswith(CLOSURE_RELATIVE)
            and not path.startswith(SUCCESSOR_CONTRACT_ROOTS)
        }
        assert set(paths) == expected, {
            "unlocked": sorted(expected - set(paths)),
            "unexpected": sorted(set(paths) - expected),
        }

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

    observed = tuple(
        (
            pub["slice_id"],
            pub["pull_request"],
            pub["topic_branch"],
            pub["reviewed_head_sha"],
            pub["squash_sha"],
            pub["pull_request_check"]["attempt"],
            pub["main_check"]["attempt"],
            pub["review_settlement"]["review_count"],
            pub["review_settlement"]["thread_count"],
        )
        for pub in publications
    )
    # Every identifier is pinned, so evidence cannot be reattributed between
    # slices while the internal cross-checks stay self-consistent.
    assert observed == EXPECTED_PUBLICATIONS
    numbers = [pub["pull_request"] for pub in publications]
    assert numbers == sorted(numbers), "publications are not in publication order"
    assert len(set(numbers)) == len(numbers)
    assert (
        sum(pub["review_settlement"]["review_count"] for pub in publications)
        == EXPECTED_REVIEW_TOTAL
    )
    assert (
        sum(pub["review_settlement"]["thread_count"] for pub in publications)
        == EXPECTED_THREAD_TOTAL
    )

    for publication in publications:
        where = publication["slice_id"]
        assert set(publication) == PUBLICATION_FIELDS, where
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

        for key, event in (
            ("pull_request_check", "pull_request"),
            ("main_check", "push"),
        ):
            check = cast(dict[str, Any], publication[key])
            assert set(check) == CHECK_FIELDS, (where, key)
            assert check["conclusion"] == "success", (where, key)
            assert check["context"] == "validate", (where, key)
            assert check["workflow"] == "CI", (where, key)
            assert check["event"] == event, (where, key)
            # A run and job identifier that is not a plausible identifier is not
            # evidence anyone could follow back to the run it names.
            for field in ("run_id", "job_id"):
                identifier = check[field]
                assert isinstance(identifier, int) and identifier > 10**9, (
                    where,
                    field,
                )
            assert isinstance(check["attempt"], int) and check["attempt"] >= 1, (
                where,
                key,
            )

        settlement = cast(dict[str, Any], publication["review_settlement"])
        assert set(settlement) == SETTLEMENT_FIELDS, where
        assert settlement["settlement"] == "clean", where
        assert settlement["actionable_unresolved_thread_count"] == 0, where
        assert settlement["changes_requested_count"] == 0, where
        # A thread cannot exist without a review that opened it.
        if settlement["thread_count"]:
            assert settlement["review_count"] >= settlement["thread_count"], where

    candidates = cast(list[dict[str, Any]], ledger["superseded_candidates"])
    assert ledger["superseded_candidate_count"] == len(candidates)
    assert (
        tuple(
            (
                candidate["pull_request"],
                candidate["superseded_by_pull_request"],
                candidate["state"],
                candidate["merged"],
            )
            for candidate in candidates
        )
        == EXPECTED_SUPERSEDED_CANDIDATES
    )
    published_numbers = set(numbers)
    for candidate in candidates:
        # A superseded candidate is audit history, never a publication.
        assert candidate["merged"] is False, candidate["pull_request"]
        assert candidate["state"] == "closed", candidate["pull_request"]
        assert candidate["pull_request"] not in published_numbers
        assert candidate["superseded_by_pull_request"] in published_numbers
        assert candidate["status"] == (
            "superseded_publication_candidate_not_a_slice_publication"
        )
        assert candidate["historical_threads_intentionally_preserved"] is True


def _assert_exit_criteria(document: dict[str, Any]) -> None:
    criteria = cast(dict[str, Any], document["exit_criteria"])
    items = cast(list[dict[str, Any]], criteria["items"])
    assert criteria["count"] == len(items)
    # Pinned, because a count derived from the list it describes survives
    # truncation with every internal cross-check intact.
    assert criteria["count"] == EXPECTED_EXIT_CRITERION_COUNT
    assert tuple(entry["subject"] for entry in items) == EXPECTED_EXIT_SUBJECTS
    # A criterion pointing at an address that proves nothing is not evidence.
    assert len({entry["evidence"] for entry in items}) >= EXPECTED_DISTINCT_EVIDENCE
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
    assert readiness["prerequisite_count"] == EXPECTED_PREREQUISITE_COUNT
    assert (
        tuple((entry["evidence_owner"], entry["subject"]) for entry in prerequisites)
        == EXPECTED_PREREQUISITES
    )
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
    assert handoff["constraint_count"] == EXPECTED_HANDOFF_CONSTRAINT_COUNT
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
    _assert_closed_world,
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


def test_markdown_is_exactly_the_projection_of_the_json() -> None:
    """Regenerate the document and compare bytes.

    A substring probe accepts anything it does not look for: a forged merge
    record, a swapped publication row, a flipped verdict. Regeneration accepts
    exactly one document for a given closure.json.
    """
    published = (CLOSURE_ROOT / "closure.md").read_text(encoding="utf-8")
    rebuilt = _render_markdown(_closure(), _digest(CLOSURE_ROOT / "closure.json"))
    assert published == rebuilt


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


def test_markdown_headings_are_exactly_the_published_set() -> None:
    """A forged section is a heading the projection does not produce."""
    markdown = (CLOSURE_ROOT / "closure.md").read_text(encoding="utf-8")
    observed = tuple(line for line in markdown.splitlines() if line.startswith("#"))
    assert observed == EXPECTED_HEADINGS


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
    elif mutation == "forged-merge-record-section":
        document["s10_publication"] = {"pull_request": 72, "merged": True}
    elif mutation == "s10-publication-fact-smuggled-into-its-entry":
        entries[-1]["squash_sha"] = "9" * 40
    elif mutation == "immutable-lock-set-truncated":
        immutable = cast(list[dict[str, Any]], locks["immutable_inputs"])
        del immutable[2:]
        locks["immutable_input_count"] = len(immutable)
        locks["total_lock_count"] = len(immutable) + len(
            cast(list[dict[str, Any]], locks["production_observations"])
        )
        total = locks["total_lock_count"]
        cast(dict[str, Any], document["assurance"])["source_locks"] = (
            f"passed_{total}_of_{total}"
        )
    elif mutation == "real-but-unlocked-corpus-file-added":
        immutable = cast(list[dict[str, Any]], locks["immutable_inputs"])
        smuggled = "reference_corpus/pytest-4412/case/case.json"
        extra = copy.deepcopy(immutable[0])
        extra["path"] = smuggled
        extra["sha256"] = _digest(REPOSITORY_ROOT / smuggled)
        extra["byte_length"] = (REPOSITORY_ROOT / smuggled).stat().st_size
        immutable.append(extra)
        immutable.sort(key=lambda entry: cast(str, entry["path"]))
        locks["immutable_input_count"] = len(immutable)
        locks["total_lock_count"] += 1
        total = locks["total_lock_count"]
        cast(dict[str, Any], document["assurance"])["source_locks"] = (
            f"passed_{total}_of_{total}"
        )
    elif mutation == "production-observation-duplicated":
        observations = cast(list[dict[str, Any]], locks["production_observations"])
        observations.append(copy.deepcopy(observations[0]))
        locks["production_observation_count"] = len(observations)
        locks["total_lock_count"] += 1
        total = locks["total_lock_count"]
        cast(dict[str, Any], document["assurance"])["source_locks"] = (
            f"passed_{total}_of_{total}"
        )
    elif mutation == "production-observations-reordered":
        cast(list[dict[str, Any]], locks["production_observations"]).reverse()
    elif mutation == "publication-squash-shas-swapped-between-slices":
        publications[0]["squash_sha"], publications[1]["squash_sha"] = (
            publications[1]["squash_sha"],
            publications[0]["squash_sha"],
        )
    elif mutation == "publication-reviewed-heads-swapped":
        publications[0]["reviewed_head_sha"], publications[1]["reviewed_head_sha"] = (
            publications[1]["reviewed_head_sha"],
            publications[0]["reviewed_head_sha"],
        )
    elif mutation == "review-count-inflated":
        cast(dict[str, Any], publications[0]["review_settlement"])["review_count"] = (
            9999
        )
    elif mutation == "thread-count-inflated":
        cast(dict[str, Any], publications[0]["review_settlement"])["thread_count"] = (
            4242
        )
    elif mutation == "ci-attempt-falsified":
        for publication in publications:
            cast(dict[str, Any], publication["pull_request_check"])["attempt"] = 1
    elif mutation == "run-identifier-falsified":
        cast(dict[str, Any], publications[0]["main_check"])["run_id"] = 2
    elif mutation == "topic-branch-falsified":
        publications[0]["topic_branch"] = "feat/not-the-branch-that-published-this"
    elif mutation == "check-event-swapped":
        cast(dict[str, Any], publications[0]["pull_request_check"])["event"] = "push"
    elif mutation == "exit-criteria-truncated":
        criteria = cast(dict[str, Any], document["exit_criteria"])
        items = cast(list[dict[str, Any]], criteria["items"])
        del items[3:]
        criteria["count"] = len(items)
        criteria["satisfied_count"] = len(items)
        criteria["unsatisfied_count"] = 0
        cast(dict[str, Any], document["assurance"])["exit_criteria"] = (
            f"passed_{len(items)}_of_{len(items)}"
        )
    elif mutation == "exit-evidence-all-point-at-one-address":
        for entry in cast(list[dict[str, Any]], document["exit_criteria"]["items"]):
            entry["evidence"] = "format.version"
    elif mutation == "exit-subject-replaced":
        cast(list[dict[str, Any]], document["exit_criteria"]["items"])[0]["subject"] = (
            "everything_is_fine"
        )
    elif mutation == "entry-prerequisites-truncated":
        prerequisites = cast(list[dict[str, Any]], readiness["prerequisites"])
        del prerequisites[1:]
        readiness["prerequisite_count"] = len(prerequisites)
        cast(dict[str, Any], document["assurance"])["entry_readiness"] = "passed_1_of_1"
    elif mutation == "handoff-constraints-truncated":
        handoff = cast(dict[str, Any], document["p06_handoff"])
        constraints = cast(list[dict[str, Any]], handoff["constraints"])
        del constraints[1:]
        handoff["constraint_count"] = len(constraints)
    elif mutation == "absent-capability-list-reordered":
        cast(list[str], inventory["absent_capabilities"]).reverse()
    elif mutation == "format-canonicalization-relaxed":
        cast(dict[str, Any], document["format"]["canonicalization"])[
            "floats_NaN_and_Infinity_permitted"
        ] = True
    elif mutation == "format-marked-public-contract":
        cast(dict[str, Any], document["format"])["public_contract"] = True
    elif mutation == "assurance-lock-total-disagrees":
        cast(dict[str, Any], document["assurance"])["source_locks"] = "passed_1_of_1"
    elif mutation == "assurance-exit-total-disagrees":
        cast(dict[str, Any], document["assurance"])["exit_criteria"] = "passed_1_of_1"
    elif mutation == "sealed-at-disagrees-between-sections":
        cast(dict[str, Any], document["assurance"])["sealed_at"] = (
            "1999-01-01T00:00:00Z"
        )
    elif mutation == "superseded-candidate-marked-merged":
        cast(list[dict[str, Any]], ledger["superseded_candidates"])[0]["merged"] = True
    elif mutation == "superseded-candidate-claimed-as-publication":
        cast(list[dict[str, Any]], ledger["superseded_candidates"])[0][
            "superseded_by_pull_request"
        ] = 999
    elif mutation == "vocabulary-enum-relabelled-as-record-model":
        for entry in cast(list[dict[str, Any]], inventory["owned_symbols"]):
            entry["target_class"] = "record_model_target"
    elif mutation == "slice-entry-gains-a-field":
        entries[0]["note"] = "added later"
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


def test_this_closure_adds_no_production_source_and_names_what_followed() -> None:
    tracked = subprocess.run(  # noqa: S603 - literal argv, no shell
        ["git", "ls-files", "src/"],
        cwd=REPOSITORY_ROOT,
        capture_output=True,
        check=False,
    )
    assert tracked.returncode == 0, tracked.stderr
    observed = set(tracked.stdout.decode("utf-8").split())
    # This closure added no production source, and the set it sealed is intact.
    # Every module the live tree gained since is named rather than absorbed, so
    # one more that no Slice explains fails here instead of inflating a count.
    assert CURRENT_PRODUCTION_FILES - observed == set()
    assert observed - CURRENT_PRODUCTION_FILES == {
        FAULT_MODULE,
        FAULT_SOURCE_RELATIONSHIP_MODULE,
        FAULT_REPAIR_MODULE,
        FAULT_TEST_MODULE,
        FAULT_INTERPRETATION_MODULE,
        FAULT_INSTANCE_MODULE,
        FAULT_EVIDENCE_LINK_MODULE,
    }
    assert len(CURRENT_PRODUCTION_FILES) == 13
    assert len(observed) == 20


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
    assert "`S1.P06.S02` is complete" in roadmap
    assert "`S1.P06.S03` is complete" in roadmap
    assert "`S1.P06.S04` is complete" in roadmap
    assert "`S1.P06.S05` is complete" in roadmap
    assert "`S1.P06.S06` is complete" in roadmap
    assert "`S1.P06.S07` is complete" in roadmap
    assert "`S1.P06.S08` is complete" in roadmap
    assert "`S1.P06.S09` is complete" in roadmap
    assert "`S1.P06.S10` is complete" in roadmap
    assert "`S1.P06.S11` is complete" in roadmap
    assert "`S1.P06.S12` is complete" in roadmap
    assert "`S1.P07` is next and not started" in roadmap
    assert "`S1.P04` is complete" in roadmap
    assert CLOSURE_RELATIVE in roadmap
    assert "`S1.P05.S10` — Integration and Phase Closure (complete)" in roadmap
    # The sequence is closed, so the provisional caveat must not still stand.
    assert "The remaining `S1.P05` sequence is PROVISIONAL" not in roadmap
    # Every state this closure retired must be gone, not merely outvoted by a
    # newer sentence sitting beside it.
    assert "`S1.P05` is active and incomplete" not in roadmap
    assert "`S1.P05.S10` is next and not started" not in roadmap
    assert "`S1.P06` is not eligible to begin" not in roadmap
    assert (
        "`S1.P05.S10` — Integration and Phase Closure (provisional; next, not started)"
        not in roadmap
    )
    # The closure sealed P06 as eligible but not commenced. That eligibility has
    # since been exercised by `S1.P06.S01`, so the roadmap records the entry
    # state in the past tense and names the phase as begun.
    assert "`S1.P06` implementation has begun with `S1.P06.S01`" in roadmap
    assert "`S1.P06` implementation has not started" not in roadmap


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


def test_the_roadmap_carries_exactly_one_live_gate() -> None:
    """A superseded gate left in the present tense reports the wrong gate.

    The earlier guard only scanned lines containing "next and not started", so
    a stale `eligible_to_begin` sentence in a predecessor section stood beside
    the live one unnoticed. Present-tense claims are collected by their own
    grammar here, and every one must name the phase that is actually next.
    """
    roadmap = " ".join(
        (REPOSITORY_ROOT / ROADMAP_RELATIVE).read_text(encoding="utf-8").split()
    )
    # No phase is awaiting entry any more: P06 has commenced, so its sealed
    # eligibility now reads in the past tense and the live gate is a Slice.
    live_gates = re.findall(r"`(S1\.P\d\d)` is `eligible_to_begin`", roadmap)
    assert live_gates == [], live_gates
    exercised = re.findall(r"`(S1\.P\d\d)` was `eligible_to_begin`", roadmap)
    assert sorted(exercised) == ["S1.P05", "S1.P06"], exercised

    live_next = re.findall(
        r"`(S1\.P\d\d(?:\.S\d\d)?)` is next and not started", roadmap
    )
    assert live_next, "the roadmap names no next gate"
    assert set(live_next) == {"S1.P07"}, sorted(set(live_next))

    live_phases = re.findall(r"`(S1\.P\d\d)` is active and incomplete", roadmap)
    assert set(live_phases) == set(), sorted(set(live_phases))

    # A phase this closure records as complete must not also be claimed open.
    for phase in ("S1.P01", "S1.P02", "S1.P03", "S1.P04", "S1.P05"):
        assert f"`{phase}` is active and incomplete" not in roadmap, phase
        assert f"`{phase}` is `eligible_to_begin`" not in roadmap, phase


def test_closure_and_roadmap_agree_on_readiness() -> None:
    document = _closure()
    readiness = cast(dict[str, Any], document["entry_readiness"])
    roadmap = " ".join(
        (REPOSITORY_ROOT / ROADMAP_RELATIVE).read_text(encoding="utf-8").split()
    )
    assert readiness["implementation_state"] == "not_started"
    # The sealed bytes still record the entry state at closure time. The roadmap
    # reports the same state historically, because P06 has since commenced. The
    # text is normalized first: this is a semantic agreement, not a line wrap.
    assert (
        f"`{readiness['next_phase']}` was `{readiness['readiness']}` with "
        f"implementation state `{readiness['implementation_state']}`" in roadmap
    )
    assert f"`{readiness['next_phase']}` is `{readiness['readiness']}`" not in roadmap
