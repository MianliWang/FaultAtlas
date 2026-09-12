"""`S1.P06` Fault Instance Model Phase closure, owned by `S1.P06.S12`.

This module owns one artifact: the sealed Phase closure under
`reference_corpus/contracts/fault-instance/closures/s1-p06-phase-closure`.
`closure.json` is the sole durable semantic authority and `closure.md` is a
deterministic projection over it, regenerated here and compared byte for byte
rather than probed for substrings.

Everything here is offline. The closure records provider-derived publication
facts -- pull-request numbers, workflow runs, ruleset evaluations, review-thread
state -- which were observed during `S1.P06.S12` orientation and publication.
They are historical observations, structurally checked here against the closure
and against retained Git and repository evidence; no test in this module
contacts GitHub. The closure says so itself, separating the provider facts
observed at closure time from the offline-replayable evidence this repository
actually retains.

What this module deliberately does not do:

* it does not repair, regenerate or edit a sealed predecessor artifact -- the
  `S1.P06.S10` decision and the `S1.P06.S11` corpus are inputs, locked by
  SHA-256 and byte length and verified against live bytes;
* it does not expand the `S1.P06.S10` prose screens. The Phase's actual
  non-generalizations are proved structurally, from the live production
  surface, the sealed decision, the sealed manifest and explicit closure
  assertions, rather than by reading more English;
* it does not run a generic mutation engine. Eight named mutations stand for
  the eight closure claims whose falsification would matter most, and each is
  required to fail.

One predecessor weakness is compensated rather than left standing. Some
`S1.P06.S11` roadmap checks test whole-file substring presence, so an appendix
anywhere in `docs/roadmap.md` could satisfy them. The `S1.P06.S11` executor is
not rewritten for that; instead the bounded `S1.P06.S11` roadmap section is
extracted here and its substantive claims are verified inside that section.
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import tarfile
import zipfile
from pathlib import Path
from typing import Any, cast

import pytest

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
CLOSURE_RELATIVE = (
    "reference_corpus/contracts/fault-instance/closures/s1-p06-phase-closure"
)
CLOSURE_ROOT = REPOSITORY_ROOT / CLOSURE_RELATIVE
CORPUS_RELATIVE = "reference_corpus/contracts/fault-instance/v1"
CORPUS = REPOSITORY_ROOT / CORPUS_RELATIVE
DECISION_RELATIVE = (
    "reference_corpus/contracts/fault-instance/decisions/"
    "s10-deferred-subject-disposition-readiness"
)
DECISION = REPOSITORY_ROOT / DECISION_RELATIVE
P05_CLOSURE_RELATIVE = (
    "reference_corpus/contracts/development-history/closures/"
    "s1-p05-phase-closure/closure.json"
)
ROADMAP = REPOSITORY_ROOT / "docs/roadmap.md"

EXPECTED_CLOSURE_FILES = frozenset({"closure.json", "closure.md"})

# The sealed predecessor authorities, by the digest each must still carry.
S10_DECISION_DIGEST = "57e9fdf8befdb4844459857f26dc5e69e91388f2d8a7a27994825882815d4fac"
S10_DECISION_BYTES = 24909
S11_CANONICAL_JSON = {
    "manifest.json": (
        "12844f3c6c26870cd3c1bb8d92e76612648bdfcf240a96be719eed4bdff70646",
        19115,
    ),
    "valid-vectors.json": (
        "2407d48598ce4cb7bc53da1383686c02754a349844bf0958a352e8dcc4525915",
        287863,
    ),
    "invalid-vectors.json": (
        "9bfabd902052102b742a62878a597543a2e38da6015c5330bab16c07af40e7c0",
        172147,
    ),
    "replay-vectors.json": (
        "14eb01c8f6d7fd51ef4bbef01a09ed0e5f5658c4144c730e74a5511a0b4ca5a2",
        129528,
    ),
}
S11_CORPUS_FILES = frozenset(
    {
        "contract.md",
        "invalid-vectors.json",
        "invalid-vectors.sha256",
        "manifest.json",
        "manifest.sha256",
        "replay-vectors.json",
        "replay-vectors.sha256",
        "valid-vectors.json",
        "valid-vectors.sha256",
    }
)

OWNED_MODULE_PATHS = (
    "src/faultatlas/domain/fault.py",
    "src/faultatlas/domain/fault_source_relationship.py",
    "src/faultatlas/domain/fault_repair.py",
    "src/faultatlas/domain/fault_test.py",
    "src/faultatlas/domain/fault_interpretation.py",
    "src/faultatlas/domain/fault_instance.py",
    "src/faultatlas/domain/fault_evidence_link.py",
)
OWNED_MODULE_COUNT = 7
OWNED_SYMBOL_COUNT = 30
# Two counts, not one. The sealed count is what `S1.P06` closed with and stays
# 20 forever: it is read out of the closure, out of the sealed source-lock rows
# and out of the baseline reconstructed from the `S1.P05` closure and the
# `S1.P06.S10` decision. The live count is what the working tree and a freshly
# built distribution carry now, and it moves when a later Phase publishes a
# module.
SEALED_PRODUCTION_MODULE_COUNT = 20
LIVE_PRODUCTION_MODULE_COUNT = 21

# Added by `S1.P07.S01`, the first `S1.P07` production module. It is named in
# both spellings this module already uses: the closure's own inventory is
# `src`-relative, while its source locks and the reconstructed baseline are
# repository-relative. A wheel or sdist member ends with the `src`-relative
# form, so that spelling serves the distribution check too.
PATTERN_MODULE = "src/faultatlas/domain/pattern.py"
PATTERN_MODULE_UNDER_SRC = "faultatlas/domain/pattern.py"
VECTOR_TOTAL = 254
FIXTURE_COUNT = 29
SYMBOL_COVERAGE = "30/30"

EXPECTED_SLICE_IDS = tuple(f"S1.P06.S{index:02d}" for index in range(1, 13))
EXPECTED_PUBLISHED_SLICES = tuple(
    (
        "S1.P06.S01",
        "S1.P06.S02",
        "S1.P06.S03",
        "S1.P06.S04",
        "S1.P06.S05",
        "S1.P06.S06",
        "S1.P06.S07",
        "S1.P06.S07.C01",
        "S1.P06.S08",
        "S1.P06.S09",
        "S1.P06.S10",
        "S1.P06.S11",
    )
)
EXPECTED_PUBLICATION_COUNT = 12
# The reviewed head and the squash commit of every canonical publication, so a
# ledger whose rows were swapped between Slices fails rather than merely
# staying internally consistent.
EXPECTED_PUBLICATION_IDENTITY: dict[str, tuple[int, str, str, str]] = {
    "S1.P06.S01": (
        73,
        "dadf64ef1617369563086e4862101b420188e811",
        "cf9b522f47bf18dc024ad29c5ad5a6f67533df8c",
        "bbd63377c474796bc0d56d5ecfa74f58024ae120",
    ),
    "S1.P06.S02": (
        74,
        "4e5fc4a5d52395593efe60c99a3f61cae664057a",
        "3788654147884bad79c99444d2accacd9ef16bd0",
        "025de19d780e9e3c8088bde735deb9bc401907ea",
    ),
    "S1.P06.S03": (
        75,
        "b2b6f8e227e725ecf514522d89445347e334cf3d",
        "1566902b56238712a3253d34a473a2754e1423cf",
        "cd43571085900475d72eb7eeb73237d856ba9666",
    ),
    "S1.P06.S04": (
        76,
        "cba21ee6ea1e3ca2f459e74acb261bfe6b1df805",
        "3c79395ca53f7b3a4326ebcb86d34117cbd7a591",
        "ebfa89e7adb6b5ae89010d5f3b0b1c6bedd4761e",
    ),
    "S1.P06.S05": (
        77,
        "4a2bb008c62643ec80d46377ac01baaf30aa79a3",
        "50688ad8474aa28e1d483c480941e1f573981375",
        "2d6ec0c08ff6614f5aad12b67c4209c24e4e62dc",
    ),
    "S1.P06.S06": (
        78,
        "d6404ed98b680ae9f5dd6d1f2c6cf70214c7baaf",
        "b3ffb0c76d676ff61857764a549c21b1e94d07f4",
        "dfd070746722e05657f24c6beb570bbaa72689dd",
    ),
    "S1.P06.S07": (
        79,
        "f99e55ef8a8f9830b24a271a8a367c931042d6d7",
        "c54300ca49ab26116a490c31afc21b8bded6f674",
        "337690a72c8d41c20956516963833bb51cc74e94",
    ),
    "S1.P06.S07.C01": (
        80,
        "646c49a96943e9784457c49372fa294ea26dd04c",
        "3f2ac32c3d00ee4fe1a673b913d8c867ebd353e4",
        "60e526fd32369ac0f6cb3fb4cd4d2a9fc51915cc",
    ),
    "S1.P06.S08": (
        81,
        "b26a9cdacbc9743a46b55758beeaeb5ee4c87c6a",
        "60e842e5d3ca2d14c5c9f672557a4d2c07c1cb1c",
        "80d44caf7596a150a63bd5200390bb9309586678",
    ),
    "S1.P06.S09": (
        83,
        "1083dd26a8a0a4e71651ac0e4a6844cb4f751150",
        "8fcc1fbda571d7bc0447e1a298f51d810915d287",
        "2bc107981e3573fefb132af366a09d05045d0506",
    ),
    "S1.P06.S10": (
        84,
        "9da8b24a5b90d9856faf3471e9dfce52aec8b782",
        "09f1c8a319f61a8c24466e4e62f321aaa1c0cb45",
        "394a0f024554025e1f9affff900c9c8a21472aaa",
    ),
    "S1.P06.S11": (
        85,
        "b8fee4e7d72b74ad36c445e7e005b151663d000a",
        "aacde1dc89a135d3efd1963d74e2ca6e77494441",
        "8b9a9baf03b88916f9357f782cf86519465ee0bc",
    ),
}
# The suite total each publication actually carried, corrections applied.
EXPECTED_PUBLICATION_TEST_COUNTS: dict[str, int] = {
    "S1.P06.S01": 7356,
    "S1.P06.S02": 7687,
    "S1.P06.S03": 8106,
    "S1.P06.S04": 8388,
    "S1.P06.S05": 8728,
    "S1.P06.S06": 9203,
    "S1.P06.S07": 9691,
    "S1.P06.S07.C01": 9776,
    "S1.P06.S08": 9968,
    "S1.P06.S09": 10096,
    "S1.P06.S10": 10148,
    "S1.P06.S11": 10455,
}

NONCANONICAL_PULL_REQUEST = 82
EXPECTED_DEBT_IDS = (
    "debt:01-s08-membership-performance",
    "debt:02-historical-source-lock-retrieval-identity",
    "debt:03-s10-prose-screen",
    "debt:04-s11-replay-category-coarseness",
    "debt:05-s11-roadmap-assertion-locality",
)
EXPECTED_CORRECTION_IDS = (
    "correction:s05-publication-prose",
    "correction:s07-c01-stale-counts",
    "correction:s09-pr-body-test-count",
    "correction:s09-governance-misdescription",
    "correction:s10-test-count",
)
EXPECTED_EXIT_CRITERION_COUNT = 32
EXPECTED_P07_PREREQUISITE_COUNT = 12
EXPECTED_VERTICAL_BOUNDARY_COUNT = 10
EXPECTED_NON_GENERALIZATION_COUNT = 20

S09_PULL_REQUEST = 83
S09_HEAD = "1083dd26a8a0a4e71651ac0e4a6844cb4f751150"
S09_SQUASH = "8fcc1fbda571d7bc0447e1a298f51d810915d287"
S09_PASSING_RULE_SUITE = 4016672138
S09_REFUSED_RULE_SUITE = 4016654651
MAIN_RULESET_ID = 19085054

EXPECTED_SECTIONS = (
    "Exact primary JSON digest",
    "Derived and non-authoritative warning",
    "Executive Phase-closure verdict",
    "Phase identity and scope",
    "Product surface",
    "Canonical publication ledger",
    "Publication metadata corrections",
    "S1.P06.S09 publication governance re-verification",
    "S1.P06.S10 deferred disposition",
    "S1.P06.S11 contract corpus assurance",
    "Canonical vertical assurance",
    "Known debt and limitations",
    "Non-generalizations",
    "Exit criteria",
    "S1.P07 entry readiness",
    "Publication candidate boundary",
    "Source locks",
)

# The P07 product surface, as it stands. At this closure none of it existed;
# `S1.P07.S01` has since published exactly one module and exactly two symbols,
# so the guard is now an equality on that surface rather than a blanket
# refusal. Everything `S1.P07` has not published yet is still refused by name.
P07_PUBLISHED_MODULES = (PATTERN_MODULE,)
P07_PUBLISHED_SYMBOLS = (
    "FaultPatternIdentity",
    "SuppliedFaultPattern",
)
ABSENT_P07_MODULES = (
    "src/faultatlas/domain/invariant.py",
    "src/faultatlas/domain/fault_pattern.py",
    "src/faultatlas/domain/fault_invariant.py",
    "src/faultatlas/domain/pattern_invariant.py",
)
ABSENT_P07_SYMBOLS = (
    "FaultPattern",
    "FaultInvariant",
    "PatternIdentity",
    "InvariantIdentity",
    "ReusableInvariant",
)

# Vocabulary that would announce a semantic S1.P06 never published. None of it
# may appear as a key or a string leaf anywhere in the closure.
FORBIDDEN_CLAIM_TOKENS = (
    "confidence_score",
    "evidence_derived_verified_fault",
    "proves",
    "repair_verified",
    "root_cause_identified",
    "support_strength",
    "verified_fault",
)


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _keys_named(node: Any, name: str) -> bool:
    """Whether any object anywhere in the document carries this key."""
    if isinstance(node, dict):
        mapping = cast(dict[str, Any], node)
        return name in mapping or any(
            _keys_named(value, name) for value in mapping.values()
        )
    if isinstance(node, list):
        return any(_keys_named(value, name) for value in cast(list[Any], node))
    return False


def _closure() -> dict[str, Any]:
    return cast(
        dict[str, Any], json.loads((CLOSURE_ROOT / "closure.json").read_bytes())
    )


def _manifest() -> dict[str, Any]:
    return cast(dict[str, Any], json.loads((CORPUS / "manifest.json").read_bytes()))


def _decision() -> dict[str, Any]:
    return cast(dict[str, Any], json.loads((DECISION / "decision.json").read_bytes()))


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
    """Rebuild `closure.md` from `closure.json` exactly as the publisher does.

    The projection is regenerated and compared byte for byte, so a doctored
    document fails rather than merely failing to contain a probed substring.
    """
    pi = cast(dict[str, Any], document["phase_identity"])
    ii = cast(dict[str, Any], document["implementation_inventory"])
    pl = cast(dict[str, Any], document["publication_ledger"])
    pmc = cast(dict[str, Any], document["publication_metadata_corrections"])
    gov = cast(dict[str, Any], document["publication_governance_reverification"])
    dr = cast(dict[str, Any], document["deferred_register"])
    cca = cast(dict[str, Any], document["contract_corpus_assurance"])
    cva = cast(dict[str, Any], document["canonical_vertical_assurance"])
    debt = cast(dict[str, Any], document["known_debt_register"])
    ng = cast(dict[str, Any], document["non_generalizations"])
    ec = cast(dict[str, Any], document["exit_criteria"])
    er = cast(dict[str, Any], document["entry_readiness"])
    pc = cast(dict[str, Any], document["publication_contract"])
    lk = cast(dict[str, Any], document["source_locks"])

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
        f"{pi['slice_count']} Slices, `{pi['phase']}.S01` through "
        f"`{pi['slice']}`. The Phase closes with the product that stands on "
        f"canonical `main`: **{ii['owned_module_count']}** owned production "
        f"modules exporting **{ii['owned_symbol_count']}** owned symbols, "
        f"**{ii['production_module_count']}** production Python modules in "
        f"total, one sealed v{cca['version']} contract corpus, and "
        f"**{dr['self_owned_open']}** open deferred subjects owned by the "
        f"Phase itself. Production change in this Slice: "
        f"`{pi['production_change']}`.\n"
    )

    add("## Phase identity and scope\n")
    add(
        f"Predecessor Phase `{pi['predecessor_phase']}`; next Phase "
        f"`{pi['next_phase']} — {pi['next_phase_title']}`, "
        f"`{er['readiness']}` with implementation state "
        f"`{er['implementation_state']}`. Owned symbols break down as "
        f"{ii['record_model_count']} record models, "
        f"{ii['identity_model_count']} identity models and "
        f"{ii['vocabulary_enum_count']} vocabulary enum, all derived from "
        f"`{ii['derived_from']}`. Duplicate or alias symbols: "
        f"{ii['duplicate_symbols']}.\n"
    )
    supporting = ", ".join(
        f"`{name}`" for name in cast(list[str], ii["supporting_authorities_not_owned"])
    )
    add(
        f"Supporting authorities `{pi['phase']}` consumes but does not own: {supporting}.\n"
    )

    add("## Product surface\n")
    add("| Slice | Module | Symbol | Class |")
    add("| --- | --- | --- | --- |")
    for entry in cast(list[dict[str, Any]], ii["owned_symbols"]):
        add(
            f"| {_cell(entry['publishing_slice'])} | {_cell(entry['module'])} "
            f"| {_cell(entry['symbol'])} | {_cell(entry['target_class'])} |"
        )
    add("")

    add("## Canonical publication ledger\n")
    add(
        f"{pl['publication_count']} canonical publications across "
        f"{pl['entry_count']} Slice entries. Reviewed tree equals squash tree "
        f"everywhere: `{pl['every_reviewed_tree_equals_squash_tree']}`. "
        f"Exact-head checks all succeeded: "
        f"`{pl['every_exact_head_check_succeeded']}`. Natural-main checks all "
        f"succeeded: `{pl['every_natural_main_check_succeeded']}`. Every "
        f"publication used squash merge: "
        f"`{pl['every_publication_used_squash_merge']}`.\n"
    )
    add(
        "| Slice | PR | Reviewed head | Reviewed tree | Squash | Squash tree "
        "| Equal | Exact-head run | Natural-main run | Tests |"
    )
    add("| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |")
    for entry in cast(list[dict[str, Any]], pl["publications"]):
        head_check = cast(dict[str, Any], entry["exact_head_check"])
        main_check = cast(dict[str, Any], entry["natural_main_check"])
        add(
            f"| {_cell(entry['slice_id'])} | {_cell(entry['pull_request'])} "
            f"| {_cell(str(entry['reviewed_head_sha'])[:12])} "
            f"| {_cell(str(entry['reviewed_tree'])[:12])} "
            f"| {_cell(str(entry['squash_sha'])[:12])} "
            f"| {_cell(str(entry['squash_tree'])[:12])} "
            f"| {_cell(entry['reviewed_tree_equals_squash_tree'])} "
            f"| {_cell(f'{head_check["run_id"]}/{head_check["conclusion"]}')} "
            f"| {_cell(f'{main_check["run_id"]}/{main_check["conclusion"]}')} "
            f"| {_cell(entry['publication_test_count'])} |"
        )
    add("")
    add(
        f"`{pi['slice']}` itself is recorded only as "
        f"`{pl['s12_publication_state']}`; "
        f"`actual_S12_publication_facts_in_candidate` is "
        f"`{pl['actual_S12_publication_facts_in_candidate']}`.\n"
    )

    add("## Publication metadata corrections\n")
    add(f"{_plain(pmc['note'])}\n")
    add("| Correction | Slice | PR | Class | Recorded in | Product failure |")
    add("| --- | --- | --- | --- | --- | --- |")
    for entry in cast(list[dict[str, Any]], pmc["items"]):
        add(
            f"| {_cell(entry['correction_id'])} | {_cell(entry['slice'])} "
            f"| {_cell(entry['pull_request'])} | {_cell(entry['class'])} "
            f"| {_cell(entry['recorded_where'])} "
            f"| {_cell(entry['product_failure'])} |"
        )
    add("")
    for entry in cast(list[dict[str, Any]], pmc["items"]):
        add(f"- `{entry['correction_id']}` — {_plain(entry['statement'])}")
    add("")

    add("## S1.P06.S09 publication governance re-verification\n")
    ruleset = cast(dict[str, Any], gov["ruleset"])
    good = cast(dict[str, Any], gov["successful_attempt"])
    bad = cast(dict[str, Any], gov["refused_attempt"])
    bypass = cast(dict[str, Any], gov["bypass"])
    threads = cast(dict[str, Any], gov["review_threads"])
    attribution = cast(dict[str, Any], gov["commit_attribution"])
    add(
        f"Re-verified at closure time by `{gov['method']}`, observed "
        f"`{gov['observed_at']}`. Pull request `{gov['pull_request']}`, "
        f"attributed head `{attribution['head_commit']}`, squash "
        f"`{gov['squash_commit']}`. Conclusion: **{gov['conclusion']}**; "
        f"publication-governance exception "
        f"`{gov['publication_governance_exception']}`. The `S1.P06.S10` "
        f"verdict was independently reproduced rather than consumed: "
        f"`s10_conclusion_independently_reproduced` is "
        f"`{gov['s10_conclusion_independently_reproduced']}`.\n"
    )
    add(
        f"The active `{ruleset['name']}` ruleset `{ruleset['id']}` is "
        f"`{ruleset['enforcement']}` over `{'`, `'.join(cast(list[str], ruleset['included_refs']))}` "
        f"and has been unchanged since `{ruleset['unchanged_since']}`, which "
        f"precedes every `{pi['phase']}` merge: "
        f"`{ruleset['unchanged_since_before_every_p06_merge']}`. Its allowed "
        f"merge methods are `{'`, `'.join(cast(list[str], ruleset['allowed_merge_methods']))}`, "
        f"it configures `{ruleset['bypass_actors']}` bypass actors, and it "
        f"requires review-thread resolution "
        f"(`{ruleset['required_review_thread_resolution']}`) and extra approval "
        f"for unattributed changes "
        f"(`{ruleset['require_extra_approval_for_unattributed_changes']}`).\n"
    )
    add("| Rule suite | Result | After | Rule | Enforcement or detail |")
    add("| --- | --- | --- | --- | --- |")
    add(
        f"| {_cell(bad['rule_suite_id'])} | {_cell(bad['result'])} "
        f"| {_cell(str(bad['after_sha'])[:12])} "
        f"| {_cell(bad['failing_rule_type'])} "
        f"| {_plain(bad['failing_rule_detail'])} |"
    )
    for evaluation in cast(list[dict[str, Any]], good["rule_evaluations"]):
        add(
            f"| {_cell(good['rule_suite_id'])} | {_cell(evaluation['result'])} "
            f"| {_cell(str(good['after_sha'])[:12])} "
            f"| {_cell(evaluation['rule_type'])} "
            f"| {_cell(evaluation['enforcement'])} |"
        )
    add("")
    add(
        f"At the successful merge `{threads['unresolved_at_successful_merge']}` "
        f"review threads were unresolved, out of `{threads['thread_count']}`. "
        f"The pull request's `{attribution['commit_count']}` commit is "
        f"attributed to `{attribution['attributed_login']}`, so the "
        f"extra-approval condition was never triggered "
        f"(`{attribution['extra_approval_condition_triggered']}`). The merge "
        f"command carried an administrator flag "
        f"(`{bypass['administrator_flag_passed']}`), but "
        f"`{bypass['bypass_actors_configured']}` bypass actors are configured, "
        f"the owner can bypass `{bypass['current_user_can_bypass']}`, and no "
        f"bypass evidence was found "
        f"(`{bypass['bypass_evidence_found']}`). A CLI flag is not evidence of "
        f"a bypass: `{bypass['cli_flag_is_not_evidence_of_bypass']}`.\n"
    )
    status = cast(dict[str, Any], gov["evidential_status"])
    retention = cast(dict[str, Any], gov["rule_suite_retention_limitation"])
    add(
        "Provider responses are not retained in this repository "
        f"(`{status['provider_responses_retained_in_repository']}`), so this "
        f"verdict is not offline replayable "
        f"(`{status['replayable_offline']}`). The closure distinguishes the two "
        "classes of evidence:\n"
    )
    add("Provider fact observed at closure time:\n")
    for item in cast(list[str], status["provider_fact_observed_at_closure_time"]):
        add(f"- {_plain(item)}")
    add("")
    add("Offline replayable retained repository evidence:\n")
    for item in cast(
        list[str], status["offline_replayable_retained_repository_evidence"]
    ):
        add(f"- {_plain(item)}")
    add("")
    add(f"{_plain(retention['note'])}\n")

    add("## S1.P06.S10 deferred disposition\n")
    ra = cast(dict[str, Any], dr["requirement_accounting"])
    pa = cast(dict[str, Any], dr["prohibition_accounting"])
    add(
        f"The sealed `S1.P06.S10` decision at `{dr['source_decision']['path']}` "
        f"carries SHA-256 `{dr['source_decision']['sha256']}` over "
        f"{dr['source_decision']['byte_length']} bytes. "
        f"`{dr['inherited_subject_count']}` inherited subject is dispositioned "
        f"exactly `{dr['dispositioned_exactly_once']}` time as "
        f"`{dr['disposition']}`; `self_owned_open` is `{dr['self_owned_open']}` "
        f"and ownership is complete (`{dr['owner_completeness']}`). "
        f"{ra['satisfied_count']} of {ra['count']} effective requirements are "
        f"satisfied and {pa['preserved_count']} of {pa['count']} effective "
        f"prohibitions are preserved, with {pa['violated_count']} violated.\n"
    )
    add("| ID | Subject | Disposition | Addressed by |")
    add("| --- | --- | --- | --- |")
    for entry in cast(list[dict[str, Any]], dr["items"]):
        add(
            f"| {_cell(entry['subject_id'])} | {_plain(entry['subject'])} "
            f"| {_cell(entry['disposition'])} "
            f"| {_cell(', '.join(cast(list[str], entry['addressed_by'])))} |"
        )
    add("")
    for entry in cast(list[dict[str, Any]], ra["items"]):
        add(
            f"- `{entry['requirement_id']}` — {entry['statement']} (`{entry['status']}`)"
        )
    for entry in cast(list[dict[str, Any]], pa["items"]):
        add(
            f"- `{entry['prohibition_id']}` — {entry['statement']} (`{entry['state']}`)"
        )
    add("")
    universal = cast(dict[str, Any], dr["universal_wording"])
    add(f"{_plain(universal['note'])}\n")

    add("## S1.P06.S11 contract corpus assurance\n")
    counts = cast(dict[str, Any], cca["vector_counts"])
    add(
        f"`{cca['corpus_id']}` v{cca['version']} at `{cca['directory']}`: "
        f"{cca['file_count']} files, {cca['canonical_json_file_count']} "
        f"canonical JSON, {cca['sidecar_count']} sidecars, all agreeing "
        f"(`{cca['sidecars_agree']}`). Vectors: **{counts['valid']} valid, "
        f"{counts['invalid']} invalid, {counts['replay']} replay, "
        f"{counts['total']} total** over {counts['fixtures']} fixtures, "
        f"reconciling (`{cca['vector_total_reconciles']}`). Owned-symbol "
        f"coverage `{cca['symbol_coverage']}`. Executor "
        f"`{cca['test_only_executor']}`; package excluded "
        f"(`{cca['package_excluded']}`); no production capability "
        f"(`{cca['no_production_capability']}`). Re-executed at closure "
        f"(`{cca['re_executed_at_closure']}`) and neither edited nor "
        f"regenerated (`{cca['edited_or_regenerated_by_S12']}`).\n"
    )
    add("| File | Role | Bytes | SHA-256 |")
    add("| --- | --- | --- | --- |")
    for entry in cast(list[dict[str, Any]], cca["files"]):
        add(
            f"| {_cell(entry['filename'])} | {_cell(entry['role'])} "
            f"| {_cell(entry['byte_length'])} | {_cell(entry['sha256'])} |"
        )
    add("")

    add("## Canonical vertical assurance\n")
    add("| Layer | Provenance |")
    add("| --- | --- |")
    for entry in cast(list[dict[str, Any]], cva["layers"]):
        add(f"| {_cell(entry['layer'])} | {_cell(entry['provenance'])} |")
    add("")
    add(
        f"{cva['boundary_count']} epistemic boundaries are preserved. "
        f"`flattened_evidence_derived_fault_instance_claimed`: "
        f"`{cva['flattened_evidence_derived_fault_instance_claimed']}`; "
        f"`root_cause_claimed`: `{cva['root_cause_claimed']}`; "
        f"`repair_correctness_claimed`: `{cva['repair_correctness_claimed']}`; "
        f"`verified_repair_claimed`: `{cva['verified_repair_claimed']}`; "
        f"`historical_s1_p06_uuid_identities`: "
        f"`{cva['historical_s1_p06_uuid_identities']}`.\n"
    )
    for entry in cast(list[dict[str, Any]], cva["boundaries"]):
        add(
            f"- `{entry['boundary_id']}` — {_plain(entry['statement'])} "
            f"(`{entry['preserved']}`)"
        )
    add("")

    add("## Known debt and limitations\n")
    add(
        f"{debt['count']} known items, every one dispositioned "
        f"(`{debt['every_item_dispositioned']}`), "
        f"{debt['phase_closure_blockers']} of them a Phase-closure blocker.\n"
    )
    add("| ID | Class | Disposition | Blocker |")
    add("| --- | --- | --- | --- |")
    for entry in cast(list[dict[str, Any]], debt["items"]):
        add(
            f"| {_cell(entry['debt_id'])} | {_cell(entry['class'])} "
            f"| {_cell(entry['disposition'])} "
            f"| {_cell(entry['phase_closure_blocker'])} |"
        )
    add("")
    for entry in cast(list[dict[str, Any]], debt["items"]):
        add(f"- `{entry['debt_id']}` — {_plain(entry['statement'])}")
    add("")

    add("## Non-generalizations\n")
    add(
        f"{ng['count']} limits carried forward. Intentional deferral is not "
        f"implementation failure: "
        f"`{ng['intentional_deferral_is_not_implementation_failure']}`.\n"
    )
    for index, item in enumerate(cast(list[str], ng["items"]), start=1):
        add(f"- `non-generalization:{index:02d}` — {_plain(item)}")
    add("")

    add("## Exit criteria\n")
    add(
        f"{ec['satisfied_count']} of {ec['count']} satisfied, "
        f"{ec['unsatisfied_count']} unsatisfied.\n"
    )
    for entry in cast(list[dict[str, Any]], ec["items"]):
        add(
            f"- `{entry['criterion_id']}` — {entry['subject']} "
            f"(`{entry['status']}`, evidence `{entry['evidence']}`)"
        )
    add("")

    add("## S1.P07 entry readiness\n")
    add(
        f"`{er['next_phase']} — {er['title']}` is `{er['readiness']}` with "
        f"implementation state `{er['implementation_state']}`. "
        f"{er['prerequisite_count']} prerequisites, "
        f"{er['unsatisfied_prerequisite_count']} unsatisfied. No exact "
        f"`{er['next_phase']}` schema is authorized here: "
        f"`{er['exact_schema_authorized']}`.\n"
    )
    for entry in cast(list[dict[str, Any]], er["prerequisites"]):
        add(
            f"- `{entry['prerequisite_id']}` — {entry['subject']} (owner "
            f"`{entry['owner']}`, `{entry['status']}`)"
        )
    add("")
    for entry in cast(list[dict[str, Any]], er["boundary"]):
        add(f"- `{entry['boundary_id']}` — {_plain(entry['statement'])}")
    add("")
    dependency = cast(dict[str, Any], er["publication_dependency"])
    add(
        f"{_plain(dependency['note'])} Required before `{er['next_phase']}` "
        f"begins: `{dependency['required_before_p07_begins']}`; recorded in "
        f"this candidate: `{dependency['recorded_in_candidate']}`; evidence at "
        f"`{dependency['evidence_location']}`.\n"
    )

    add("## Publication candidate boundary\n")
    add(
        f"This record is a `{document['format']['publication_state']}`. "
        f"`actual_S12_publication_facts_in_candidate`: "
        f"`{pc['actual_S12_publication_facts_in_candidate']}` — this closure "
        f"records no pull request, reviewed head, squash SHA or natural-main "
        f"run of its own, because none exists when these bytes are sealed. Its "
        f"publication evidence lives at "
        f"`{pc['future_publication_evidence_location']}`. Topic branch "
        f"`{pc['topic_branch']}`; required workflow `{pc['required_workflow']}` "
        f"check `{pc['required_check']}`; administrator or ruleset bypass "
        f"`{pc['admin_or_ruleset_bypass']}`; amend, rebase or force push "
        f"`{pc['amend_rebase_or_force_push']}`.\n"
    )

    add("## Source locks\n")
    add(
        f"{lk['production_observation_count']} closure-baseline production "
        f"observations and {lk['immutable_input_count']} immutable inputs, "
        f"{lk['total_lock_count']} locks total, each on "
        f"`{'` and `'.join(cast(list[str], lk['lock_basis']))}`. Production "
        f"observations are baseline records, not ownership claims. No "
        f"retrieval-identity field is recorded "
        f"(`{lk['retrieval_identity_fields_recorded']}`), and no lock points at "
        f"a mutable latest or current pointer "
        f"(`{lk['mutable_latest_or_current_pointer']}`).\n"
    )

    return "\n".join(lines).rstrip("\n") + "\n"


# --- 1: the closure artifact itself -----------------------------------------


def test_the_closure_directory_holds_exactly_the_two_declared_files() -> None:
    present = {path.name for path in CLOSURE_ROOT.iterdir() if path.is_file()}

    assert present == EXPECTED_CLOSURE_FILES, sorted(present)
    assert not any(path.is_dir() for path in CLOSURE_ROOT.iterdir())


def test_the_closure_json_is_canonical_under_the_declared_convention() -> None:
    raw = (CLOSURE_ROOT / "closure.json").read_bytes()
    document = _closure()

    canonicalization = cast(
        dict[str, Any], cast(dict[str, Any], document["format"])["canonicalization"]
    )
    assert canonicalization["name"] == "json-sort-keys-compact-utf8-lf-v1"

    rendered = (
        json.dumps(document, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")
    assert raw == rendered, "closure.json is not canonical under its own convention"

    assert not raw.startswith(b"\xef\xbb\xbf")
    assert b"\r" not in raw
    assert raw.endswith(b"}\n")
    assert raw.count(b"\n") == 1
    assert not _floats(document), "a float leaf is not canonical here"

    # `NaN` and `Infinity` are refused as JSON values rather than as substrings:
    # the document legitimately names the convention that forbids them.
    def _refuse(name: str) -> float:
        raise AssertionError(f"non-finite JSON constant: {name}")

    json.loads(raw, parse_constant=_refuse)


def _floats(node: Any) -> list[Any]:
    if isinstance(node, bool):
        return []
    if isinstance(node, float):
        return [node]
    if isinstance(node, dict):
        return [
            found
            for value in cast(dict[str, Any], node).values()
            for found in _floats(value)
        ]
    if isinstance(node, list):
        return [found for value in cast(list[Any], node) for found in _floats(value)]
    return []


def test_the_markdown_is_the_deterministic_projection_of_the_json() -> None:
    raw = (CLOSURE_ROOT / "closure.json").read_bytes()
    text = (CLOSURE_ROOT / "closure.md").read_text("utf-8")
    markdown = (CLOSURE_ROOT / "closure.md").read_bytes()

    assert text == _render_markdown(_closure(), _sha256(raw))
    assert not markdown.startswith(b"\xef\xbb\xbf")
    assert b"\r" not in markdown
    assert markdown.endswith(b"\n")
    assert not markdown.endswith(b"\n\n")


def test_the_markdown_carries_every_declared_section_once() -> None:
    text = (CLOSURE_ROOT / "closure.md").read_text("utf-8")
    headings = re.findall(r"^## (.+)$", text, re.M)

    assert tuple(headings) == EXPECTED_SECTIONS, headings
    assert len(headings) == len(set(headings))
    assert text.startswith("# S1.P06 Fault Instance Model Phase Closure\n")


def test_the_markdown_states_that_the_json_governs() -> None:
    """The projection must never read as a second authority."""
    text = (CLOSURE_ROOT / "closure.md").read_text("utf-8")

    assert "sole durable semantic authority" in text
    assert "derived, non-authoritative view" in text
    assert "Where the two differ, the JSON governs." in text


def test_the_closure_declares_itself_internal_and_not_a_production_contract() -> None:
    fmt = cast(dict[str, Any], _closure()["format"])

    assert fmt["public_contract"] is False
    assert fmt["internal"] is True
    assert fmt["production_persistence"] is False
    assert fmt["classification"] == "internal_phase_closure_governance_layer"
    assert "not_a_production_schema" in cast(str, fmt["non_production_schema_warning"])


# --- 2: the product surface --------------------------------------------------


def test_the_owned_surface_is_exactly_seven_modules_and_thirty_symbols() -> None:
    ii = cast(dict[str, Any], _closure()["implementation_inventory"])
    modules = cast(list[dict[str, Any]], ii["owned_modules"])
    symbols = cast(list[dict[str, Any]], ii["owned_symbols"])

    assert ii["owned_module_count"] == len(modules) == OWNED_MODULE_COUNT
    assert ii["owned_symbol_count"] == len(symbols) == OWNED_SYMBOL_COUNT
    assert tuple(cast(str, entry["path"]) for entry in modules) == OWNED_MODULE_PATHS
    assert (
        sum(cast(int, entry["exported_symbol_count"]) for entry in modules)
        == OWNED_SYMBOL_COUNT
    )
    assert ii["derived_from"] == "live_module_dunder_all"


def test_the_recorded_symbols_are_the_live_dunder_all_values() -> None:
    """The inventory is re-derived, not trusted."""
    import importlib

    ii = cast(dict[str, Any], _closure()["implementation_inventory"])
    recorded: dict[str, list[str]] = {}
    for entry in cast(list[dict[str, Any]], ii["owned_symbols"]):
        recorded.setdefault(cast(str, entry["module"]), []).append(
            cast(str, entry["symbol"])
        )

    live: dict[str, list[str]] = {}
    for entry in cast(list[dict[str, Any]], ii["owned_modules"]):
        dotted = cast(str, entry["module"])
        module = importlib.import_module(dotted)
        exported = list(cast(tuple[str, ...], module.__all__))
        live[dotted] = exported
        assert len(exported) == entry["exported_symbol_count"], dotted

    assert recorded == live
    flat = [symbol for exported in live.values() for symbol in exported]
    assert len(flat) == len(set(flat)) == OWNED_SYMBOL_COUNT
    assert ii["duplicate_symbols"] == 0
    assert ii["alias_symbols_published"] is False
    assert ii["aggregator_export_published"] is False


def test_no_supporting_authority_symbol_was_counted_as_owned() -> None:
    """`S1.P06` consumes five predecessor modules; none of them is owned here."""
    import importlib

    ii = cast(dict[str, Any], _closure()["implementation_inventory"])
    owned = {
        cast(str, entry["symbol"])
        for entry in cast(list[dict[str, Any]], ii["owned_symbols"])
    }
    owned_modules = {
        cast(str, entry["module"])
        for entry in cast(list[dict[str, Any]], ii["owned_modules"])
    }

    supporting = cast(list[str], ii["supporting_authorities_not_owned"])
    assert supporting
    for dotted in supporting:
        assert dotted not in owned_modules, dotted
        module = importlib.import_module(dotted)
        for symbol in cast(tuple[str, ...], module.__all__):
            assert symbol not in owned, (dotted, symbol)


def test_the_sealed_twenty_modules_stand_and_the_tree_added_only_pattern() -> None:
    """Two claims, only one of which a later Phase may change.

    The sealed claim is permanent: `S1.P06` closed with exactly these twenty
    production modules, and that stays true however the tree grows. The second
    claim was that the tree had not diverged from that snapshot yet, which is
    what catches a production module smuggled in under a governance Slice.
    `S1.P07.S01` has now published its first module, so that claim is migrated
    here exactly as `S1.P06` migrated the `S1.P05` closure inventory: the
    sealed set must still be present in full, and the difference must be
    exactly the one module a published Slice explains. A second module no
    Slice explains fails here instead of inflating a count.
    """
    ii = cast(dict[str, Any], _closure()["implementation_inventory"])
    recorded = cast(list[str], ii["production_modules"])
    live = sorted(
        path.relative_to(REPOSITORY_ROOT / "src").as_posix()
        for path in (REPOSITORY_ROOT / "src").rglob("*.py")
    )

    # Sealed, and permanent.
    assert ii["production_module_count"] == SEALED_PRODUCTION_MODULE_COUNT
    assert len(recorded) == len(set(recorded)) == SEALED_PRODUCTION_MODULE_COUNT
    for relative in recorded:
        assert (REPOSITORY_ROOT / "src" / relative).is_file(), relative

    # The closed-Phase snapshot against the tree as it now stands: intact, and
    # grown by exactly the named `S1.P07.S01` module.
    assert set(recorded) - set(live) == set(), sorted(set(recorded) - set(live))
    assert set(live) - set(recorded) == {PATTERN_MODULE_UNDER_SRC}, sorted(
        set(live) - set(recorded)
    )
    assert len(live) == LIVE_PRODUCTION_MODULE_COUNT, live


def test_the_owned_modules_still_carry_the_sealed_s10_source_locks() -> None:
    """The seven modules must be byte-identical to what `S1.P06.S10` recorded."""
    ii = cast(dict[str, Any], _closure()["implementation_inventory"])
    sealed = {
        cast(str, entry["path"]): cast(str, entry["sha256"])
        for entry in cast(
            list[dict[str, Any]],
            cast(dict[str, Any], _decision()["product_inventory"])["modules"],
        )
    }

    assert ii["source_locked_against_s10_decision"] is True
    assert len(sealed) == OWNED_MODULE_COUNT
    for entry in cast(list[dict[str, Any]], ii["owned_modules"]):
        path = cast(str, entry["path"])
        raw = (REPOSITORY_ROOT / path).read_bytes()
        assert _sha256(raw) == entry["sha256"], path
        assert len(raw) == entry["byte_length"], path
        assert sealed[path] == entry["sha256"], path


def test_the_closure_declares_the_absent_capabilities() -> None:
    ii = cast(dict[str, Any], _closure()["implementation_inventory"])
    absent = cast(list[str], ii["absent_capabilities"])

    assert absent == sorted(absent)
    for expected in (
        "network_or_provider_IO",
        "persistence_or_durable_serializer",
        "production_corpus_reader_or_executor",
        "retrieval_or_RAG",
        "source_ingestion",
    ):
        assert expected in absent, expected


# --- 3: the sealed S1.P06.S10 decision ---------------------------------------


def test_the_s10_decision_bytes_are_the_sealed_ones() -> None:
    raw = (DECISION / "decision.json").read_bytes()

    assert _sha256(raw) == S10_DECISION_DIGEST
    assert len(raw) == S10_DECISION_BYTES

    source = cast(
        dict[str, Any],
        cast(dict[str, Any], _closure()["deferred_register"])["source_decision"],
    )
    assert source["sha256"] == S10_DECISION_DIGEST
    assert source["byte_length"] == S10_DECISION_BYTES
    assert source["path"] == f"{DECISION_RELATIVE}/decision.json"


def test_the_deferred_register_reproduces_the_sealed_disposition() -> None:
    dr = cast(dict[str, Any], _closure()["deferred_register"])
    register = cast(dict[str, Any], _decision()["inherited_subject_register"])

    assert dr["inherited_subject_count"] == register["count"] == 1
    assert dr["dispositioned_exactly_once"] == 1
    assert dr["disposition"] == "addressed"
    assert dr["self_owned_open"] == register["self_owned_open"] == 0
    assert dr["owner_completeness"] is True
    assert dr["carried_forward_count"] == 0
    assert dr["split_count"] == 0
    assert dr["self_introduced_count"] == 0

    items = cast(list[dict[str, Any]], dr["items"])
    assert len(items) == 1
    sealed_item = cast(list[dict[str, Any]], register["items"])[0]
    assert items[0]["subject_id"] == sealed_item["source"]["subject_id"]
    assert items[0]["disposition"] == sealed_item["disposition"]
    assert items[0]["addressed_by"] == sealed_item["addressed_by"]


def test_both_effective_requirements_and_all_three_prohibitions_hold() -> None:
    dr = cast(dict[str, Any], _closure()["deferred_register"])
    decision = _decision()
    requirements = cast(dict[str, Any], dr["requirement_accounting"])
    prohibitions = cast(dict[str, Any], dr["prohibition_accounting"])

    assert requirements["count"] == 2
    assert requirements["satisfied_count"] == 2
    assert requirements["unsatisfied_count"] == 0
    assert prohibitions["count"] == 3
    assert prohibitions["preserved_count"] == 3
    assert prohibitions["violated_count"] == 0

    sealed_requirements = cast(dict[str, Any], decision["requirement_accounting"])
    sealed_prohibitions = cast(dict[str, Any], decision["prohibition_accounting"])
    assert [
        entry["requirement_id"]
        for entry in cast(list[dict[str, Any]], requirements["items"])
    ] == [
        entry["requirement_id"]
        for entry in cast(list[dict[str, Any]], sealed_requirements["items"])
    ]
    assert [
        entry["prohibition_id"]
        for entry in cast(list[dict[str, Any]], prohibitions["items"])
    ] == [
        entry["prohibition_id"]
        for entry in cast(list[dict[str, Any]], sealed_prohibitions["items"])
    ]
    for entry in cast(list[dict[str, Any]], requirements["items"]):
        assert entry["status"] == "satisfied", entry["requirement_id"]
    for entry in cast(list[dict[str, Any]], prohibitions["items"]):
        assert entry["state"] == "preserved", entry["prohibition_id"]


def test_the_historical_universal_wording_is_not_a_relationship_ontology() -> None:
    """The predecessor's word is quoted, never promoted into a capability."""
    universal = cast(
        dict[str, Any],
        cast(dict[str, Any], _closure()["deferred_register"])["universal_wording"],
    )

    assert universal["historical_wording"] == "universal relationship vocabulary"
    assert universal["reinterpreted_as_generic_ontology"] is False
    assert universal["generic_relationship_ontology_published"] is False

    items = cast(
        list[str], cast(dict[str, Any], _closure()["non_generalizations"])["items"]
    )
    assert "no universal relationship ontology" in items


# --- 4: the sealed S1.P06.S11 corpus -----------------------------------------


def test_the_corpus_is_exactly_nine_sealed_files() -> None:
    present = {path.name for path in CORPUS.iterdir() if path.is_file()}
    cca = cast(dict[str, Any], _closure()["contract_corpus_assurance"])

    assert present == S11_CORPUS_FILES, sorted(present)
    assert len(present) == 9
    assert cca["file_count"] == 9
    assert cca["directory"] == CORPUS_RELATIVE
    assert {
        cast(str, entry["filename"])
        for entry in cast(list[dict[str, Any]], cca["files"])
    } == S11_CORPUS_FILES


@pytest.mark.parametrize("name", sorted(S11_CANONICAL_JSON))
def test_each_canonical_corpus_json_matches_its_digest_length_and_sidecar(
    name: str,
) -> None:
    expected_digest, expected_length = S11_CANONICAL_JSON[name]
    raw = (CORPUS / name).read_bytes()
    sidecar = (CORPUS / f"{name[:-5]}.sha256").read_text("utf-8").split()

    assert _sha256(raw) == expected_digest, name
    assert len(raw) == expected_length, name
    assert sidecar[0] == expected_digest, name
    assert sidecar[1] == name, name

    recorded = {
        cast(str, entry["filename"]): entry
        for entry in cast(
            list[dict[str, Any]],
            cast(dict[str, Any], _closure()["contract_corpus_assurance"])["files"],
        )
    }[name]
    assert recorded["sha256"] == expected_digest
    assert recorded["byte_length"] == expected_length
    assert recorded["sidecar_agrees"] is True


def test_the_vector_totals_reconcile_to_two_hundred_and_fifty_four() -> None:
    cca = cast(dict[str, Any], _closure()["contract_corpus_assurance"])
    counts = cast(dict[str, Any], cca["vector_counts"])
    manifest = _manifest()
    summary = cast(dict[str, Any], manifest["vector_summary"])

    assert counts["valid"] == summary["valid"]["count"] == 103
    assert counts["invalid"] == summary["invalid"]["count"] == 110
    assert counts["replay"] == summary["replay"]["count"] == 41
    assert counts["fixtures"] == summary["fixtures"] == FIXTURE_COUNT
    assert counts["total"] == summary["total_vectors"] == VECTOR_TOTAL
    assert counts["valid"] + counts["invalid"] + counts["replay"] == VECTOR_TOTAL
    assert cca["vector_total_reconciles"] is True

    for family, filename in (
        ("valid", "valid-vectors.json"),
        ("invalid", "invalid-vectors.json"),
        ("replay", "replay-vectors.json"),
    ):
        section = cast(dict[str, Any], json.loads((CORPUS / filename).read_bytes()))
        assert len(cast(list[Any], section["vectors"])) == counts[family], family


def test_the_corpus_covers_every_one_of_the_thirty_owned_symbols() -> None:
    cca = cast(dict[str, Any], _closure()["contract_corpus_assurance"])
    manifest = _manifest()
    ii = cast(dict[str, Any], _closure()["implementation_inventory"])

    assert cca["symbol_coverage"] == SYMBOL_COVERAGE
    assert cca["symbol_coverage_covered"] == OWNED_SYMBOL_COUNT
    assert cca["symbol_coverage_total"] == OWNED_SYMBOL_COUNT
    assert (
        cast(dict[str, Any], manifest["assurance"])["owned_symbol_coverage"]
        == SYMBOL_COVERAGE
    )
    assert (
        cast(dict[str, Any], manifest["assurance"])[
            "every_owned_symbol_is_executably_covered"
        ]
        is True
    )

    targeted = {
        cast(str, entry["symbol"])
        for entry in cast(list[dict[str, Any]], manifest["target_symbols"])
    }
    owned = {
        cast(str, entry["symbol"])
        for entry in cast(list[dict[str, Any]], ii["owned_symbols"])
    }
    assert targeted == owned
    assert len(targeted) == OWNED_SYMBOL_COUNT


def test_the_corpus_stays_source_only_and_was_not_touched_by_s12() -> None:
    cca = cast(dict[str, Any], _closure()["contract_corpus_assurance"])

    assert cca["edited_or_regenerated_by_S12"] is False
    assert cca["no_production_capability"] is True
    assert cca["package_excluded"] is True
    assert cca["test_only_executor"] == "tests/test_fault_instance_contract_corpus.py"
    assert (REPOSITORY_ROOT / cast(str, cca["test_only_executor"])).is_file()
    assert cca["re_executed_at_closure"] is True

    # No production source may name the corpus directory or the closure. The
    # phrase "fault-instance" appears in production prose as a domain term, so
    # the check is on the paths, not on the words.
    for path in (REPOSITORY_ROOT / "src").rglob("*.py"):
        text = path.read_text("utf-8")
        assert "reference_corpus" not in text, path
        assert "contracts/fault-instance" not in text, path
        assert "s1-p06-phase-closure" not in text, path


def test_the_built_wheel_and_sdist_carry_twenty_one_sources_and_no_governance(
    tmp_path: Path,
) -> None:
    """Neither the corpus nor this closure may arrive by installing the package."""
    output = tmp_path / "dist"
    output.mkdir()
    result = subprocess.run(
        ["uv", "build", "--offline", "--no-create-gitignore", "--out-dir", str(output)],
        cwd=REPOSITORY_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr

    wheels = sorted(output.glob("*.whl"))
    sdists = sorted(output.glob("*.tar.gz"))
    assert len(wheels) == 1 and len(sdists) == 1

    with zipfile.ZipFile(wheels[0]) as archive:
        wheel_names = [info.filename for info in archive.infolist()]
    with tarfile.open(sdists[0], mode="r:gz") as tar:
        sdist_names = [member.name for member in tar.getmembers() if member.isfile()]

    for names, label in ((wheel_names, "wheel"), (sdist_names, "sdist")):
        sources = [name for name in names if name.endswith(".py")]
        # Twenty at the sealed closure; `S1.P07.S01` added the twenty-first,
        # which is named here rather than absorbed into a bumped integer.
        assert len(sources) == LIVE_PRODUCTION_MODULE_COUNT, (label, sorted(sources))
        assert any(name.endswith(PATTERN_MODULE_UNDER_SRC) for name in sources), label
        for excluded in ("reference_corpus", "tests/", "docs/"):
            assert not any(excluded in name for name in names), (label, excluded)
        assert not any("phase-closure" in name for name in names), label
        assert not any(name.endswith("closure.json") for name in names), label


# --- 5: the canonical publication ledger -------------------------------------


def test_the_ledger_records_every_canonical_publication_once() -> None:
    pl = cast(dict[str, Any], _closure()["publication_ledger"])
    publications = cast(list[dict[str, Any]], pl["publications"])

    assert pl["publication_count"] == len(publications) == EXPECTED_PUBLICATION_COUNT
    slices = [cast(str, entry["slice_id"]) for entry in publications]
    assert tuple(slices) == EXPECTED_PUBLISHED_SLICES
    assert len(slices) == len(set(slices))
    ids = [cast(str, entry["id"]) for entry in publications]
    assert len(ids) == len(set(ids))


def test_every_ledger_row_names_the_publication_it_actually_describes() -> None:
    """Swapping two rows leaves the totals intact, so identity is pinned."""
    publications = {
        cast(str, entry["slice_id"]): entry
        for entry in cast(
            list[dict[str, Any]],
            cast(dict[str, Any], _closure()["publication_ledger"])["publications"],
        )
    }

    assert set(publications) == set(EXPECTED_PUBLICATION_IDENTITY)
    for slice_id, pins in EXPECTED_PUBLICATION_IDENTITY.items():
        pull_request, head, squash, tree = pins
        entry = publications[slice_id]
        assert entry["pull_request"] == pull_request, slice_id
        assert entry["reviewed_head_sha"] == head, slice_id
        assert entry["squash_sha"] == squash, slice_id
        # The tree is pinned here as well as compared against Git, because the
        # Git cross-check verifies nothing in a shallow checkout and a ledger
        # value no oracle reads offline would survive the required CI run.
        assert entry["reviewed_tree"] == tree, slice_id
        assert entry["squash_tree"] == tree, slice_id
        assert (
            entry["publication_test_count"]
            == EXPECTED_PUBLICATION_TEST_COUNTS[slice_id]
        ), slice_id


def test_every_canonical_publication_satisfies_the_four_publication_rules() -> None:
    pl = cast(dict[str, Any], _closure()["publication_ledger"])

    assert pl["every_reviewed_tree_equals_squash_tree"] is True
    assert pl["every_exact_head_check_succeeded"] is True
    assert pl["every_natural_main_check_succeeded"] is True
    assert pl["every_publication_used_squash_merge"] is True

    for entry in cast(list[dict[str, Any]], pl["publications"]):
        slice_id = cast(str, entry["slice_id"])
        assert entry["reviewed_tree"] == entry["squash_tree"], slice_id
        assert entry["reviewed_tree_equals_squash_tree"] is True, slice_id
        assert entry["merge_method"] == "protected_pull_request_squash_merge", slice_id
        assert entry["publication_state"] == "merged", slice_id
        head = cast(dict[str, Any], entry["exact_head_check"])
        main = cast(dict[str, Any], entry["natural_main_check"])
        assert head["event"] == "pull_request" and head["conclusion"] == "success"
        assert main["event"] == "push" and main["conclusion"] == "success"
        assert head["context"] == main["context"] == "validate"
        assert head["head_sha"] == entry["reviewed_head_sha"], slice_id
        assert main["head_sha"] == entry["squash_sha"], slice_id
        settlement = cast(dict[str, Any], entry["review_settlement"])
        assert settlement["unresolved_thread_count_at_merge"] == 0, slice_id
        assert settlement["settlement"] == "clean", slice_id


def test_the_squash_commits_form_the_linear_chain_on_canonical_main() -> None:
    """Retained Git evidence, checked offline against the ledger's own claim.

    CI checks out a shallow merge ref, so the first-parent history genuinely is
    not there. That is allowed for, but it may not become an exemption: in a
    complete clone every publication must be present and must agree, and the
    shallow marker is what distinguishes the two cases. Without that the check
    would pass by finding nothing, which is how a guard stops guarding.

    This is the second witness, not the only one. Every squash tree is also
    pinned offline in `EXPECTED_PUBLICATION_IDENTITY`, so a corrupted ledger
    tree is refused in a shallow checkout too, where this check can verify
    nothing at all.
    """
    pl = cast(dict[str, Any], _closure()["publication_ledger"])
    publications = cast(list[dict[str, Any]], pl["publications"])
    expected = {
        cast(str, entry["squash_sha"]): cast(str, entry["squash_tree"])
        for entry in publications
    }
    assert len(expected) == len(publications)

    result = subprocess.run(
        ["git", "log", "--first-parent", "--format=%H %T", "-40"],
        cwd=REPOSITORY_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    trees = {
        line.split()[0]: line.split()[1]
        for line in result.stdout.splitlines()
        if line.strip()
    }

    present = {sha for sha in expected if sha in trees}
    if not (REPOSITORY_ROOT / ".git" / "shallow").exists():
        assert present == set(expected), sorted(set(expected) - present)
    for sha in sorted(present):
        assert trees[sha] == expected[sha], sha


def test_the_slice_ledger_covers_all_twelve_slices_in_order() -> None:
    pl = cast(dict[str, Any], _closure()["publication_ledger"])
    entries = cast(list[dict[str, Any]], pl["entries"])

    assert pl["entry_count"] == len(entries) == 12
    assert [cast(str, entry["slice_id"]) for entry in entries] == list(
        EXPECTED_SLICE_IDS
    )
    assert [cast(int, entry["ordinal"]) for entry in entries] == list(range(1, 13))

    declared = {
        publication_id
        for entry in entries
        for publication_id in cast(list[str], entry["publication_ids"])
    }
    actual = {
        cast(str, entry["id"])
        for entry in cast(list[dict[str, Any]], pl["publications"])
    }
    assert declared == actual

    closing = entries[-1]
    assert closing["slice_id"] == "S1.P06.S12"
    assert closing["state"] == "sealed_publication_candidate"
    assert closing["publication_ids"] == []
    for entry in entries[:-1]:
        assert entry["state"] == "complete_published", entry["slice_id"]
        assert entry["publication_ids"], entry["slice_id"]


def test_the_candidate_records_no_evidence_of_its_own_publication() -> None:
    document = _closure()
    pl = cast(dict[str, Any], document["publication_ledger"])
    pc = cast(dict[str, Any], document["publication_contract"])

    assert pl["actual_S12_publication_facts_in_candidate"] is False
    assert pc["actual_S12_publication_facts_in_candidate"] is False
    assert pl["s12_publication_state"] == "external_to_candidate_record"
    assert (
        cast(dict[str, Any], document["format"])["publication_state"]
        == "sealed_publication_candidate"
    )

    # No publication row may name S12, and no S12 pull request may appear.
    for entry in cast(list[dict[str, Any]], pl["publications"]):
        assert entry["slice_id"] != "S1.P06.S12"
    numbers = {
        cast(int, entry["pull_request"])
        for entry in cast(list[dict[str, Any]], pl["publications"])
    }
    assert max(numbers) == 85, sorted(numbers)


# --- 6: publication metadata corrections -------------------------------------


def test_every_known_publication_metadata_correction_is_recorded() -> None:
    pmc = cast(dict[str, Any], _closure()["publication_metadata_corrections"])
    items = cast(list[dict[str, Any]], pmc["items"])

    assert pmc["count"] == len(items) == len(EXPECTED_CORRECTION_IDS)
    assert (
        tuple(cast(str, entry["correction_id"]) for entry in items)
        == EXPECTED_CORRECTION_IDS
    )
    assert pmc["product_failures"] == 0
    assert pmc["corrected_descriptive_count_is_not_a_product_failure"] is True

    covered = {cast(str, entry["slice"]) for entry in items}
    for slice_id in ("S1.P06.S05", "S1.P06.S07.C01", "S1.P06.S09", "S1.P06.S10"):
        assert slice_id in covered, slice_id


def test_a_corrected_count_is_not_recorded_as_a_product_failure() -> None:
    pmc = cast(dict[str, Any], _closure()["publication_metadata_corrections"])

    for entry in cast(list[dict[str, Any]], pmc["items"]):
        correction_id = cast(str, entry["correction_id"])
        assert entry["product_failure"] is False, correction_id
        assert entry["reviewed_tree_equals_squash_tree"] is True, correction_id
        assert entry["required_ci_succeeded"] is True, correction_id
        assert entry["verified_at_closure"] is True, correction_id
        assert isinstance(entry["correction_comment_id"], int), correction_id
        assert cast(str, entry["correction_url"]).startswith(
            "https://github.com/MianliWang/FaultAtlas/pull/"
        ), correction_id
        assert entry["class"] in {
            "descriptive_count",
            "governance_misdescription_retracted",
        }, correction_id


def test_the_false_noncompliance_claim_is_preserved_as_retracted() -> None:
    """The incident is history, not something to tidy away."""
    pmc = cast(dict[str, Any], _closure()["publication_metadata_corrections"])
    entry = {
        cast(str, item["correction_id"]): item
        for item in cast(list[dict[str, Any]], pmc["items"])
    }["correction:s09-governance-misdescription"]

    assert entry["class"] == "governance_misdescription_retracted"
    assert entry["pull_request"] == S09_PULL_REQUEST
    statement = cast(str, entry["statement"])
    assert "retracted" in statement
    assert "false in the direction of non-compliance" in statement


# --- 7: the S1.P06.S09 governance re-verification -----------------------------


def test_the_s09_governance_verdict_was_reverified_not_copied() -> None:
    gov = cast(dict[str, Any], _closure()["publication_governance_reverification"])

    assert gov["reverified"] is True
    assert gov["consumed_s10_verdict_without_reverification"] is False
    assert gov["s10_conclusion_independently_reproduced"] is True
    assert gov["method"] == "read_only_provider_query_at_closure_time"
    assert gov["conclusion"] == "compliant_publication"
    assert gov["publication_governance_exception"] == "absent"
    assert gov["pull_request"] == S09_PULL_REQUEST
    assert gov["squash_commit"] == S09_SQUASH
    assert cast(dict[str, Any], gov["commit_attribution"])["head_commit"] == S09_HEAD


def test_the_provider_ruleset_evaluation_is_the_governance_authority() -> None:
    gov = cast(dict[str, Any], _closure()["publication_governance_reverification"])
    ruleset = cast(dict[str, Any], gov["ruleset"])
    good = cast(dict[str, Any], gov["successful_attempt"])
    bad = cast(dict[str, Any], gov["refused_attempt"])

    assert ruleset["id"] == MAIN_RULESET_ID
    assert ruleset["enforcement"] == "active"
    assert ruleset["allowed_merge_methods"] == ["squash"]
    assert ruleset["bypass_actors"] == 0
    assert ruleset["required_review_thread_resolution"] is True
    assert ruleset["require_extra_approval_for_unattributed_changes"] is True
    assert ruleset["unchanged_since_before_every_p06_merge"] is True

    assert good["rule_suite_id"] == S09_PASSING_RULE_SUITE
    assert good["result"] == "pass"
    assert good["after_sha"] == S09_SQUASH
    evaluations = cast(list[dict[str, Any]], good["rule_evaluations"])
    assert len(evaluations) == 5
    assert {cast(str, entry["rule_type"]) for entry in evaluations} == {
        "deletion",
        "non_fast_forward",
        "pull_request",
        "required_linear_history",
        "required_status_checks",
    }
    for entry in evaluations:
        assert entry["result"] == "pass", entry["rule_type"]
        assert entry["enforcement"] == "active", entry["rule_type"]

    assert bad["rule_suite_id"] == S09_REFUSED_RULE_SUITE
    assert bad["result"] == "fail"
    assert bad["failing_rule_type"] == "pull_request"
    assert "conversation must be resolved" in cast(str, bad["failing_rule_detail"])
    assert bad["after_sha"] != S09_SQUASH


def test_an_administrator_flag_is_not_recorded_as_a_bypass() -> None:
    bypass = cast(
        dict[str, Any],
        cast(dict[str, Any], _closure()["publication_governance_reverification"])[
            "bypass"
        ],
    )

    assert bypass["administrator_flag_passed"] is True
    assert bypass["bypass_exercised"] is False
    assert bypass["bypass_evidence_found"] is False
    assert bypass["bypass_actors_configured"] == 0
    assert bypass["current_user_can_bypass"] == "never"
    assert bypass["cli_flag_is_not_evidence_of_bypass"] is True


def test_the_merge_settled_with_no_unresolved_thread_and_an_attributed_commit() -> None:
    gov = cast(dict[str, Any], _closure()["publication_governance_reverification"])
    threads = cast(dict[str, Any], gov["review_threads"])
    attribution = cast(dict[str, Any], gov["commit_attribution"])

    assert threads["unresolved_at_successful_merge"] == 0
    assert threads["thread_count"] == 1
    assert attribution["commit_count"] == 1
    assert attribution["attributed"] is True
    assert attribution["extra_approval_condition_triggered"] is False


def test_the_closure_separates_provider_fact_from_retained_evidence() -> None:
    """A provider response is not retained evidence unless it was acquired."""
    status = cast(
        dict[str, Any],
        cast(dict[str, Any], _closure()["publication_governance_reverification"])[
            "evidential_status"
        ],
    )

    assert status["provider_responses_retained_in_repository"] is False
    assert status["replayable_offline"] is False
    assert (
        status["retaining_provider_snapshots_is_acquisition_work_outside_this_slice"]
        is True
    )

    observed = cast(list[str], status["provider_fact_observed_at_closure_time"])
    retained = cast(
        list[str], status["offline_replayable_retained_repository_evidence"]
    )
    assert observed and retained
    assert not set(observed) & set(retained)
    assert any("ruleset" in item for item in observed)
    assert any("rule-suite" in item for item in observed)
    assert any("commit chain" in item for item in retained)


def test_the_rule_suite_retention_limitation_is_stated_rather_than_glossed() -> None:
    retention = cast(
        dict[str, Any],
        cast(dict[str, Any], _closure()["publication_governance_reverification"])[
            "rule_suite_retention_limitation"
        ],
    )

    available = cast(list[str], retention["publications_with_retrievable_rule_suite"])
    assert available == ["S1.P06.S09", "S1.P06.S10", "S1.P06.S11"]
    assert retention["records_available_for_default_branch"] == 4
    note = cast(str, retention["note"])
    assert "S1.P06.S01 through" in note
    assert "not changed since before the first S1.P06 merge" in note


# --- 8: the canonical vertical -----------------------------------------------


def test_the_vertical_preserves_every_published_epistemic_boundary() -> None:
    cva = cast(dict[str, Any], _closure()["canonical_vertical_assurance"])
    boundaries = cast(list[dict[str, Any]], cva["boundaries"])

    assert cva["boundary_count"] == len(boundaries) == EXPECTED_VERTICAL_BOUNDARY_COUNT
    for entry in boundaries:
        assert entry["preserved"] is True, entry["boundary_id"]

    statements = " ".join(cast(str, entry["statement"]) for entry in boundaries)
    for required in (
        "synthetic and caller-supplied",
        "not a provider fact",
        "caller-supplied hypothesis",
        "did not execute pytest",
        "not an independent execution",
        "not repair correctness",
        "not an S1.P07 invariant",
        "explicitly supplied and never inferred",
        "LEVEL 1",
        "no support, confidence",
    ):
        assert required in statements, required


def test_no_flattened_evidence_derived_fault_appears_anywhere() -> None:
    document = _closure()
    cva = cast(dict[str, Any], document["canonical_vertical_assurance"])
    manifest = _manifest()
    replay = cast(dict[str, Any], manifest["replay_contract"])

    assert cva["flattened_evidence_derived_fault_instance_claimed"] is False
    assert cva["root_cause_claimed"] is False
    assert cva["repair_correctness_claimed"] is False
    assert cva["verified_repair_claimed"] is False
    assert cva["historical_s1_p06_uuid_identities"] == 0
    assert cva["production_replay_io"] is False

    assert replay["flattened_evidence_derived_fault_instance_claimed"] is False
    assert replay["root_cause_claimed"] is False
    assert replay["repair_correctness_claimed"] is False
    assert replay["verified_repair_claimed"] is False
    assert replay["historical_s1_p06_uuid_identities"] == 0

    flat = json.dumps(document, sort_keys=True).lower()
    for token in FORBIDDEN_CLAIM_TOKENS:
        assert token not in flat, token


def test_the_five_provenance_layers_are_declared_and_distinct() -> None:
    cva = cast(dict[str, Any], _closure()["canonical_vertical_assurance"])
    layers = cast(list[dict[str, Any]], cva["layers"])
    manifest = _manifest()
    published = cast(
        dict[str, Any],
        cast(dict[str, Any], manifest["replay_contract"])["classifications"],
    )

    assert len(layers) == 5
    provenances = [cast(str, entry["provenance"]) for entry in layers]
    assert len(set(provenances)) == 5
    assert set(provenances) == set(published)


# --- 9: known debt and limitations -------------------------------------------


def test_every_known_debt_item_is_present_and_dispositioned() -> None:
    debt = cast(dict[str, Any], _closure()["known_debt_register"])
    items = cast(list[dict[str, Any]], debt["items"])

    assert debt["count"] == len(items) == len(EXPECTED_DEBT_IDS)
    assert tuple(cast(str, entry["debt_id"]) for entry in items) == EXPECTED_DEBT_IDS
    assert debt["every_item_dispositioned"] is True
    assert debt["phase_closure_blockers"] == 0
    for entry in items:
        debt_id = cast(str, entry["debt_id"])
        assert entry["phase_closure_blocker"] is False, debt_id
        assert cast(str, entry["disposition"]).startswith("recorded_"), debt_id
        assert cast(str, entry["statement"]).strip() == entry["statement"], debt_id
        assert cast(str, entry["evidence"]).strip(), debt_id


def test_pull_request_82_is_recorded_as_noncanonical_and_not_a_prerequisite() -> None:
    document = _closure()
    entry = {
        cast(str, item["debt_id"]): item
        for item in cast(
            list[dict[str, Any]],
            cast(dict[str, Any], document["known_debt_register"])["items"],
        )
    }["debt:01-s08-membership-performance"]

    assert entry["pull_request"] == NONCANONICAL_PULL_REQUEST
    assert entry["class"] == "implementation_performance_debt"
    assert entry["canonical_product_semantics_affected"] is False
    assert entry["phase_closure_blocker"] is False
    assert entry["candidate_is_canonical"] is False
    assert entry["merged_into_p06"] is False

    # It may never appear as a publication or as a P07 prerequisite.
    publications = cast(
        list[dict[str, Any]],
        cast(dict[str, Any], document["publication_ledger"])["publications"],
    )
    assert all(
        item["pull_request"] != NONCANONICAL_PULL_REQUEST for item in publications
    )
    prerequisites = json.dumps(
        cast(dict[str, Any], document["entry_readiness"])["prerequisites"]
    )
    assert "82" not in prerequisites


def test_the_retrieval_identity_limitation_is_stated_and_not_relied_on() -> None:
    document = _closure()
    entry = {
        cast(str, item["debt_id"]): item
        for item in cast(
            list[dict[str, Any]],
            cast(dict[str, Any], document["known_debt_register"])["items"],
        )
    }["debt:02-historical-source-lock-retrieval-identity"]
    locks = cast(dict[str, Any], document["source_locks"])

    assert entry["class"] == "assurance_limitation"
    assert entry["known_product_semantic_effect"] is False
    assert entry["predecessor_artifacts_repaired"] is False
    assert entry["retrieval_identity_fields_used_as_s12_closure_evidence"] is False
    assert sorted(cast(list[str], entry["s12_lock_basis"])) == [
        "byte_length",
        "sha256",
    ]

    # The closure must not publish a retrieval-identity field it never verified.
    assert locks["retrieval_identity_fields_recorded"] is False
    assert sorted(cast(list[str], locks["lock_basis"])) == ["byte_length", "sha256"]
    # The limitation is named in prose; what must be absent is the field, so
    # the check is on keys rather than on a substring of the whole document.
    assert not _keys_named(document, "git_blob_sha1")
    for record in cast(
        list[dict[str, Any]],
        locks["immutable_inputs"] + locks["production_observations"],
    ):
        assert "mode" not in record, record
        assert "git_blob_sha1" not in record, record


def test_the_prose_screen_limitation_is_compensated_structurally() -> None:
    entry = {
        cast(str, item["debt_id"]): item
        for item in cast(
            list[dict[str, Any]],
            cast(dict[str, Any], _closure()["known_debt_register"])["items"],
        )
    }["debt:03-s10-prose-screen"]

    assert entry["class"] == "heuristic_assurance_limitation"
    assert entry["grammar_expanded_by_s12"] is False
    assert entry["compensated_by"] == "direct_structural_phase_closure_assertions"


def test_the_replay_category_coarseness_is_descriptive_only() -> None:
    """The coarse label is real; the authoritative provenance axis is correct."""
    entry = {
        cast(str, item["debt_id"]): item
        for item in cast(
            list[dict[str, Any]],
            cast(dict[str, Any], _closure()["known_debt_register"])["items"],
        )
    }["debt:04-s11-replay-category-coarseness"]

    assert entry["class"] == "descriptive_metadata_coarseness"
    assert entry["authoritative_provenance_axis"] == "evidence_classification"
    assert entry["authoritative_provenance_correct"] is True
    assert entry["executor_interprets_category_as_provenance"] is False
    assert entry["published_semantic_claim_depends_on_category"] is False
    assert entry["corpus_edited_by_s12"] is False

    replay = cast(
        dict[str, Any], json.loads((CORPUS / "replay-vectors.json").read_bytes())
    )
    vectors = cast(list[dict[str, Any]], replay["vectors"])
    coarse = [
        cast(str, vector["id"])
        for vector in vectors
        if vector["category"] == "retained-observation"
        and vector["evidence_classification"] != "retained_normalized_observation"
    ]
    assert coarse == cast(list[str], entry["miscategorised_vectors"])
    assert len(coarse) == entry["miscategorised_vector_count"] == 1
    # The one coarse row still carries the correct provenance.
    for vector in vectors:
        if cast(str, vector["id"]) in coarse:
            assert vector["evidence_classification"] == "caller_supplied_composition"

    # And the executor never reads `category` as provenance.
    executor = (
        REPOSITORY_ROOT / "tests/test_fault_instance_contract_corpus.py"
    ).read_text("utf-8")
    for shape in (
        'vector["category"] == "retained',
        'category"] == "caller_supplied',
        'if vector["category"]',
    ):
        assert shape not in executor, shape


# --- 10: the S1.P06.S11 roadmap claims, checked section-locally ---------------


def _roadmap_section(first: str, last: str) -> str:
    """One bounded roadmap region, so an appendix elsewhere cannot satisfy it."""
    text = ROADMAP.read_text("utf-8")
    start = text.index(first)
    end = text.index(last, start + len(first))
    assert start < end
    return " ".join(text[start:end].split())


def test_the_s11_roadmap_claims_hold_inside_the_s11_section_itself() -> None:
    """Compensates the predecessor's whole-file substring checks.

    `S1.P06.S11` asserts several of these with `in roadmap`, which an appendix
    anywhere in the document would satisfy. Here the `S1.P06.S11` narrative is
    bounded first and every claim is required to stand inside it.
    """
    section = _roadmap_section(
        "`S1.P06.S11` adds no production module, no symbol and no product",
        "`S1.P06.S12` adds no production module, no symbol and no product",
    )
    manifest = _manifest()
    summary = cast(dict[str, Any], manifest["vector_summary"])

    for claim in (
        "reference_corpus/contracts/fault-instance/v1",
        "in exactly nine files",
        "four canonical JSON files",
        "json-sort-keys-compact-utf8-lf-v1",
        "seven owned production modules",
        "thirty owned product symbols",
        "30/30",
        f"{summary['total_vectors']} vectors",
        f"{summary['fixtures']} declared fixtures",
        (
            f"{summary['valid']['count']} accepted, {summary['invalid']['count']} "
            f"refused and {summary['replay']['count']} replayed"
        ),
        "synthetic",
        "excludes the corpus",
        "production module count stays at 20",
        "tests/test_fault_instance_contract_corpus.py",
        "self_owned_open == 0",
    ):
        assert claim in section, claim

    # The section must not be so wide that it swallows the whole document.
    assert len(section) < 6000, len(section)


def test_the_s11_section_keeps_the_case_boundaries_locally() -> None:
    section = _roadmap_section(
        "Replay is one deterministic",
        "The corpus is source-only.",
    )

    for claim in (
        "is not a provider fact",
        "stale-cache causation stays a hypothesis",
        "FaultAtlas did not execute pytest",
        "a reported run is not an independent execution",
        "failed-then-passed pair is not repair correctness",
        "expected property is not an `S1.P07` invariant",
        "explicitly supplied rather than inferred",
    ):
        assert claim in section, claim


def test_the_roadmap_records_the_closed_phase_and_the_begun_next_one() -> None:
    roadmap = ROADMAP.read_text("utf-8")

    assert "`S1.P06` is complete" in roadmap
    assert "`S1.P06.S12` is complete" in roadmap
    # `S1.P07` was next and not started when this closure was sealed. That
    # eligibility has since been exercised, so the live roadmap names the Phase
    # as active and its own next Slice as the gate. Nothing sealed moved; only
    # the roadmap's projection of it did.
    assert "`S1.P07` is active and incomplete" in roadmap
    assert "`S1.P07.S01` is complete" in roadmap
    assert "`S1.P07.S02` is next and not started" in roadmap
    assert "`S1.P07` is next and not started" not in roadmap
    assert "`S1.P06` is active and incomplete" not in roadmap
    assert "`S1.P06.S12` is next and not started" not in roadmap
    assert "`S1.P07` is complete" not in roadmap

    # A `## S1.P07 — Pattern & Invariant Model` section now sits between the
    # `S1.P06` narrative and the preserved-phase list, so the bound ends at
    # that heading. Ending it at the preserved-phase list would swallow the
    # whole `S1.P07` section and stop being a check on the `S1.P06` narrative.
    section = _roadmap_section(
        "## S1.P06 — Fault Instance Model",
        "## S1.P07 — Pattern & Invariant Model",
    )
    for claim in (
        "7 `S1.P06`-owned production modules",
        "30 owned product symbols",
        "one bounded `FaultInstance` aggregate",
        "weak whole-record fault-evidence bridge",
        "254 vectors",
        "29 fixtures",
        "30-of-30",
        "pull request 82 is not canonical `S1.P06` state",
        # The sealed entry state, reported in the past tense, beside the fact
        # that the Phase has begun. The closure's own fields are unchanged.
        "`S1.P07` was `eligible_to_begin` with implementation state `not_started`",
        "`S1.P07` implementation has begun with `S1.P07.S01`",
    ):
        assert claim in section, claim
    assert "known nonblocking debt" in section
    assert "`S1.P07` is eligible to begin" not in section


# --- 11: exit criteria and P07 readiness --------------------------------------


def test_the_exit_criteria_register_is_complete_with_nothing_unsatisfied() -> None:
    document = _closure()
    ec = cast(dict[str, Any], document["exit_criteria"])
    items = cast(list[dict[str, Any]], ec["items"])

    assert ec["count"] == len(items) == EXPECTED_EXIT_CRITERION_COUNT
    assert ec["satisfied_count"] == len(items)
    assert ec["unsatisfied_count"] == 0
    assert cast(dict[str, Any], document["assurance"])["exit_criteria_unsatisfied"] == 0

    ids = [cast(str, entry["criterion_id"]) for entry in items]
    assert ids == [f"exit:{index:02d}" for index in range(1, len(items) + 1)]
    subjects = [cast(str, entry["subject"]) for entry in items]
    assert len(set(subjects)) == len(subjects)
    for entry in items:
        assert entry["status"] == "satisfied", entry["criterion_id"]


def test_every_exit_criterion_points_at_an_address_that_exists() -> None:
    """A dangling evidence pointer is a criterion that proves nothing."""
    document = _closure()
    items = cast(
        list[dict[str, Any]], cast(dict[str, Any], document["exit_criteria"])["items"]
    )

    addresses = [cast(str, entry["evidence"]) for entry in items]
    for address in addresses:
        resolved = _resolve(document, address)
        assert resolved is not None, address
    # Evidence must be spread rather than all pointing at one convenient leaf.
    assert len(set(addresses)) >= 20, sorted(set(addresses))


def test_the_mandated_exit_subjects_are_all_present() -> None:
    subjects = {
        cast(str, entry["subject"])
        for entry in cast(
            list[dict[str, Any]],
            cast(dict[str, Any], _closure()["exit_criteria"])["items"],
        )
    }

    for required in (
        "every_canonical_reviewed_tree_equals_its_squash_tree",
        "every_required_exact_head_check_succeeded",
        "every_required_natural_main_check_succeeded",
        "every_canonical_publication_used_squash_merge",
        "seven_owned_production_modules_are_present_and_source_locked",
        "thirty_owned_P06_symbols_are_present",
        "production_module_count_remains_twenty",
        "self_owned_open_is_zero",
        "the_S1.P06.S11_corpus_has_exactly_nine_files",
        "the_S1.P06.S11_vector_totals_reconcile_to_254",
        "S1.P06.S11_executable_owned_symbol_coverage_is_thirty_of_thirty",
        "the_corpus_remains_excluded_from_wheel_and_sdist",
        "no_S1.P07_Pattern_or_Invariant_product_already_exists",
        "S1.P07_implementation_is_still_not_started",
    ):
        assert required in subjects, required


def test_p07_is_eligible_to_begin_with_every_prerequisite_satisfied() -> None:
    er = cast(dict[str, Any], _closure()["entry_readiness"])
    prerequisites = cast(list[dict[str, Any]], er["prerequisites"])

    assert er["next_phase"] == "S1.P07"
    assert er["title"] == "Pattern & Invariant Model"
    assert er["readiness"] == "eligible_to_begin"
    assert er["implementation_state"] == "not_started"
    assert er["exact_schema_authorized"] is False
    assert er["prerequisite_count"] == len(prerequisites)
    assert len(prerequisites) == EXPECTED_P07_PREREQUISITE_COUNT
    assert er["unsatisfied_prerequisite_count"] == 0

    ids = [cast(str, entry["prerequisite_id"]) for entry in prerequisites]
    assert ids == [f"p07-entry:{index:02d}" for index in range(1, 13)]
    owners = [cast(str, entry["owner"]) for entry in prerequisites]
    assert owners == list(EXPECTED_SLICE_IDS)
    for entry in prerequisites:
        assert entry["status"] == "satisfied", entry["prerequisite_id"]


def test_no_prerequisite_claims_this_closure_was_already_published() -> None:
    """Readiness may rest on the closure being sealed, never on its publication.

    The twelfth prerequisite is the one that could quietly assert an outcome
    that has not happened: at seal time there is no pull request, no squash and
    no natural-main run for this Slice, so a prerequisite reading "published"
    and marked satisfied would record an unknown external event as fact.
    """
    er = cast(dict[str, Any], _closure()["entry_readiness"])
    final = cast(list[dict[str, Any]], er["prerequisites"])[-1]

    assert final["prerequisite_id"] == "p07-entry:12"
    assert final["subject"] == "P06_phase_closure_sealed_publication_candidate"
    assert final["publication_is_external_to_this_record"] is True

    dependency = cast(dict[str, Any], er["publication_dependency"])
    assert dependency["required_before_p07_begins"] is True
    assert dependency["recorded_in_candidate"] is False
    assert (
        dependency["evidence_location"]
        == "Git_history_GitHub_and_final_execution_report"
    )

    # No prerequisite anywhere may assert the publication as an accomplished
    # fact, and no publication row may name this Slice.
    for entry in cast(list[dict[str, Any]], er["prerequisites"]):
        assert "published" not in cast(str, entry["subject"]), entry["prerequisite_id"]


def test_the_p07_boundary_is_carried_forward_unweakened() -> None:
    er = cast(dict[str, Any], _closure()["entry_readiness"])
    boundary = cast(list[dict[str, Any]], er["boundary"])

    assert er["boundary_count"] == len(boundary) == 5
    statements = " ".join(cast(str, entry["statement"]) for entry in boundary)
    assert "not already a reusable invariant" in statements
    assert "S1.P08" in statements
    assert "S1.P09" in statements
    assert "S1.P10" in statements
    assert "not factual truth" in statements


def test_the_live_p07_surface_is_exactly_what_s01_published() -> None:
    """Readiness was a claim about absence; now it bounds what exists.

    At this closure `S1.P07` had published nothing and every one of these
    names was refused outright. `S1.P07.S01` has since published exactly one
    module exporting exactly two symbols, so the guard is migrated rather than
    dropped: that module and those two symbols are pinned as the whole
    published `S1.P07` surface, and every name the Phase has not published is
    still refused. A third, unexplained `Pattern` symbol fails here.
    """
    import importlib

    for relative in P07_PUBLISHED_MODULES:
        assert (REPOSITORY_ROOT / relative).is_file(), relative
    for relative in ABSENT_P07_MODULES:
        assert not (REPOSITORY_ROOT / relative).exists(), relative

    published = importlib.import_module("faultatlas.domain.pattern")
    assert tuple(cast(tuple[str, ...], published.__all__)) == P07_PUBLISHED_SYMBOLS, (
        published.__all__
    )

    exported: set[str] = set()
    for path in (REPOSITORY_ROOT / "src").rglob("*.py"):
        dotted = (
            path.relative_to(REPOSITORY_ROOT / "src")
            .with_suffix("")
            .as_posix()
            .replace("/", ".")
        )
        if dotted.endswith(".__init__") or dotted.endswith(".__main__"):
            continue
        module = importlib.import_module(dotted)
        exported |= set(cast(tuple[str, ...], getattr(module, "__all__", ())))

    for symbol in ABSENT_P07_SYMBOLS:
        assert symbol not in exported, symbol
    # The `Invariant` half of the screen still holds in full: `S1.P07` has
    # published no invariant surface at all. The `Pattern` half is now bounded
    # by the two symbols `S1.P07.S01` published rather than by their absence,
    # so an unexplained third still fails.
    assert not any("Invariant" in symbol for symbol in exported), sorted(exported)
    assert {symbol for symbol in exported if "Pattern" in symbol} == set(
        P07_PUBLISHED_SYMBOLS
    ), sorted(exported)


# --- 12: source locks and the no-production-change claim ----------------------


def test_every_source_lock_matches_the_bytes_it_names() -> None:
    locks = cast(dict[str, Any], _closure()["source_locks"])
    immutable = cast(list[dict[str, Any]], locks["immutable_inputs"])
    observations = cast(list[dict[str, Any]], locks["production_observations"])

    assert locks["immutable_input_count"] == len(immutable)
    assert locks["production_observation_count"] == len(observations)
    assert locks["total_lock_count"] == len(immutable) + len(observations)
    assert locks["mutable_latest_or_current_pointer"] is False

    for record in immutable + observations:
        path = REPOSITORY_ROOT / cast(str, record["path"])
        raw = path.read_bytes()
        assert _sha256(raw) == record["sha256"], record["path"]
        assert len(raw) == record["byte_length"], record["path"]

    ids = [cast(str, record["lock_id"]) for record in immutable]
    assert len(ids) == len(set(ids))
    paths = [cast(str, record["path"]) for record in observations]
    assert len(paths) == len(set(paths)) == SEALED_PRODUCTION_MODULE_COUNT


def test_the_locked_inputs_cover_the_decision_and_every_corpus_file() -> None:
    locks = cast(dict[str, Any], _closure()["source_locks"])
    locked = {
        cast(str, record["path"])
        for record in cast(list[dict[str, Any]], locks["immutable_inputs"])
    }

    assert f"{DECISION_RELATIVE}/decision.json" in locked
    assert f"{DECISION_RELATIVE}/decision.md" in locked
    for name in S11_CORPUS_FILES:
        assert f"{CORPUS_RELATIVE}/{name}" in locked, name
    assert (
        "reference_corpus/contracts/development-history/closures/"
        "s1-p05-phase-closure/closure.json" in locked
    )


def test_s12_adds_no_production_module_symbol_or_semantic() -> None:
    """Proved against sealed predecessors rather than against a Git range.

    `git diff origin/main` is not available in a shallow CI checkout, and a
    check that quietly skips there proves nothing. Every one of the twenty
    production modules this Phase closed with is instead compared to a digest
    some earlier Slice sealed: the thirteen pre-`S1.P06` modules to the
    `S1.P05` Phase closure, and the seven owned modules to the `S1.P06.S10`
    decision. Neither baseline was written by this Slice, so the argument is
    not circular. The live tree has since gained the `S1.P07.S01` module; it is
    named below rather than absorbed, so a further module no Slice explains
    still fails here.
    """
    document = _closure()
    assurance = cast(dict[str, Any], document["assurance"])
    identity = cast(dict[str, Any], document["phase_identity"])

    assert identity["production_change"] is False
    assert assurance["no_production_change"] is True
    assert assurance["production_python_source_count"] == SEALED_PRODUCTION_MODULE_COUNT
    assert assurance["predecessor_artifacts_unmodified"] is True

    sealed: dict[str, str] = {}
    p05 = cast(
        dict[str, Any],
        json.loads((REPOSITORY_ROOT / P05_CLOSURE_RELATIVE).read_bytes()),
    )
    for record in cast(
        list[dict[str, Any]],
        cast(dict[str, Any], p05["source_locks"])["production_observations"],
    ):
        sealed[cast(str, record["path"])] = cast(str, record["sha256"])
    assert len(sealed) == 13, sorted(sealed)

    for record in cast(
        list[dict[str, Any]],
        cast(dict[str, Any], _decision()["product_inventory"])["modules"],
    ):
        path = cast(str, record["path"])
        assert path not in sealed, path
        sealed[path] = cast(str, record["sha256"])
    assert len(sealed) == SEALED_PRODUCTION_MODULE_COUNT, sorted(sealed)

    live = sorted(
        path.relative_to(REPOSITORY_ROOT).as_posix()
        for path in (REPOSITORY_ROOT / "src").rglob("*.py")
    )
    # The sealed baseline is intact, and the live tree exceeds it by exactly
    # the one module `S1.P07.S01` published.
    assert set(sealed) - set(live) == set(), sorted(set(sealed) - set(live))
    assert set(live) - set(sealed) == {PATTERN_MODULE}, sorted(set(live) - set(sealed))
    assert len(live) == LIVE_PRODUCTION_MODULE_COUNT, live
    for path, digest in sorted(sealed.items()):
        assert _sha256((REPOSITORY_ROOT / path).read_bytes()) == digest, path

    # The other bytes this Slice may not touch, against their sealed digests.
    assert _sha256((DECISION / "decision.json").read_bytes()) == S10_DECISION_DIGEST
    for name, (digest, length) in S11_CANONICAL_JSON.items():
        raw = (CORPUS / name).read_bytes()
        assert _sha256(raw) == digest, name
        assert len(raw) == length, name


def test_the_assurance_block_agrees_with_the_sections_it_summarises() -> None:
    document = _closure()
    assurance = cast(dict[str, Any], document["assurance"])

    assert assurance["self_owned_open"] == _resolve(
        document, "deferred_register.self_owned_open"
    )
    assert assurance["exit_criteria_unsatisfied"] == _resolve(
        document, "exit_criteria.unsatisfied_count"
    )
    assert assurance["known_debt_blockers"] == _resolve(
        document, "known_debt_register.phase_closure_blockers"
    )
    assert assurance["production_python_source_count"] == _resolve(
        document, "implementation_inventory.production_module_count"
    )
    assert assurance["P07_readiness"] == _resolve(document, "entry_readiness.readiness")
    assert assurance["P07_implementation_state"] == _resolve(
        document, "entry_readiness.implementation_state"
    )
    assert assurance["phase_state"] == _resolve(document, "phase_identity.phase_state")
    assert assurance["source_lock_total"] == _resolve(
        document, "source_locks.total_lock_count"
    )
    assert assurance["sealed_at"] == _resolve(document, "format.sealed_at")
    assert assurance["publication_governance_reverified"] is True
    assert assurance["no_unresolved_P06_product_blockers"] is True


def test_the_phase_identity_closes_the_phase() -> None:
    identity = cast(dict[str, Any], _closure()["phase_identity"])

    assert identity["phase"] == "S1.P06"
    assert identity["title"] == "Fault Instance Model"
    assert identity["phase_state"] == "complete"
    assert identity["closes_phase"] is True
    assert identity["corrective"] is False
    assert identity["slice"] == "S1.P06.S12"
    assert identity["slice_count"] == 12
    assert identity["predecessor_phase"] == "S1.P05"
    assert identity["next_phase"] == "S1.P07"


def test_the_non_generalizations_are_declared_and_specific() -> None:
    ng = cast(dict[str, Any], _closure()["non_generalizations"])
    items = cast(list[str], ng["items"])

    assert ng["count"] == len(items) == EXPECTED_NON_GENERALIZATION_COUNT
    assert len(set(items)) == len(items)
    assert ng["intentional_deferral_is_not_implementation_failure"] is True
    for required in (
        "no universal relationship ontology",
        "no generic Git or repository evolution graph",
        "no complete provider development history",
        "no automatic evidence transitivity",
        "no field-level evidence locator",
        "no evidence support, proof or verification semantics",
        "no confidence or review calculus",
        "no repair correctness",
        "no independent test execution",
        "no reusable Pattern or Invariant yet",
        "no transfer or applicability semantics",
        "no persistence or production serializer",
        "no production corpus reader",
        "no source ingestion",
        "no retrieval or RAG",
        "no external repository execution",
    ):
        assert required in items, required


# --- 13: the eight mutations --------------------------------------------------

# Each mutation stands for one closure claim whose falsification would matter,
# and each is required to make this module fail. There is no generic engine
# here: a mutation is written because a specific untruth must be refused.


def _mutate(document: dict[str, Any], mutation: str) -> dict[str, Any]:
    if mutation == "pr-82-marked-canonical":
        entry = cast(list[dict[str, Any]], document["known_debt_register"]["items"])[0]
        entry["candidate_is_canonical"] = True
        entry["merged_into_p06"] = True
        return document
    if mutation == "self-owned-open-is-one":
        cast(dict[str, Any], document["deferred_register"])["self_owned_open"] = 1
        cast(dict[str, Any], document["assurance"])["self_owned_open"] = 1
        return document
    if mutation == "one-owned-symbol-removed":
        inventory = cast(dict[str, Any], document["implementation_inventory"])
        symbols = cast(list[dict[str, Any]], inventory["owned_symbols"])
        symbols.pop()
        inventory["owned_symbol_count"] = len(symbols)
        return document
    if mutation == "coverage-downgraded-to-29-of-30":
        corpus = cast(dict[str, Any], document["contract_corpus_assurance"])
        corpus["symbol_coverage"] = "29/30"
        corpus["symbol_coverage_covered"] = 29
        return document
    if mutation == "failed-then-passed-called-repair-correctness":
        vertical = cast(dict[str, Any], document["canonical_vertical_assurance"])
        vertical["repair_correctness_claimed"] = True
        boundaries = cast(list[dict[str, Any]], vertical["boundaries"])
        for entry in boundaries:
            if "repair correctness" in cast(str, entry["statement"]):
                entry["preserved"] = False
                entry["statement"] = (
                    "a reported failed-then-passed pair establishes repair correctness"
                )
        return document
    if mutation == "expected-property-promoted-to-reusable-invariant":
        readiness = cast(dict[str, Any], document["entry_readiness"])
        boundary = cast(list[dict[str, Any]], readiness["boundary"])
        boundary[0]["statement"] = (
            "case-local SuppliedFaultExpectedProperty is already a reusable invariant"
        )
        return document
    if mutation == "one-assurance-limitation-erased":
        debt = cast(dict[str, Any], document["known_debt_register"])
        items = cast(list[dict[str, Any]], debt["items"])
        debt["items"] = [
            entry for entry in items if entry["debt_id"] != "debt:03-s10-prose-screen"
        ]
        debt["count"] = len(cast(list[Any], debt["items"]))
        return document
    if mutation == "closure-claims-its-own-publication":
        readiness = cast(dict[str, Any], document["entry_readiness"])
        final = cast(list[dict[str, Any]], readiness["prerequisites"])[-1]
        final["subject"] = "P06_phase_closure_published"
        final["publication_is_external_to_this_record"] = False
        return document
    if mutation == "p07-marked-started":
        readiness = cast(dict[str, Any], document["entry_readiness"])
        readiness["implementation_state"] = "in_progress"
        cast(dict[str, Any], document["assurance"])["P07_implementation_state"] = (
            "in_progress"
        )
        return document
    raise AssertionError(f"unknown mutation: {mutation}")


MUTATION_CHECKS: tuple[tuple[str, str], ...] = (
    ("pr-82-marked-canonical", "test_pull_request_82_is_recorded_as_noncanonical"),
    ("self-owned-open-is-one", "test_the_deferred_register_reproduces"),
    ("one-owned-symbol-removed", "test_the_owned_surface_is_exactly_seven_modules"),
    ("coverage-downgraded-to-29-of-30", "test_the_corpus_covers_every_one"),
    (
        "failed-then-passed-called-repair-correctness",
        "test_the_vertical_preserves_every_published_epistemic_boundary",
    ),
    (
        "expected-property-promoted-to-reusable-invariant",
        "test_the_p07_boundary_is_carried_forward_unweakened",
    ),
    ("one-assurance-limitation-erased", "test_every_known_debt_item_is_present"),
    ("p07-marked-started", "test_p07_is_eligible_to_begin"),
    (
        "closure-claims-its-own-publication",
        "test_no_prerequisite_claims_this_closure_was_already_published",
    ),
)


def _assert_mutated_document_is_refused(mutated: dict[str, Any]) -> None:
    """Every closure assertion this module owns, re-run against a doctored copy."""
    failures: list[str] = []

    ii = cast(dict[str, Any], mutated["implementation_inventory"])
    dr = cast(dict[str, Any], mutated["deferred_register"])
    cca = cast(dict[str, Any], mutated["contract_corpus_assurance"])
    cva = cast(dict[str, Any], mutated["canonical_vertical_assurance"])
    debt = cast(dict[str, Any], mutated["known_debt_register"])
    er = cast(dict[str, Any], mutated["entry_readiness"])

    if ii["owned_symbol_count"] != OWNED_SYMBOL_COUNT:
        failures.append("owned symbol count")
    if len(cast(list[Any], ii["owned_symbols"])) != OWNED_SYMBOL_COUNT:
        failures.append("owned symbol rows")
    if dr["self_owned_open"] != 0:
        failures.append("self owned open")
    if cca["symbol_coverage"] != SYMBOL_COVERAGE:
        failures.append("symbol coverage")
    if cca["symbol_coverage_covered"] != OWNED_SYMBOL_COUNT:
        failures.append("symbol coverage count")
    if cva["repair_correctness_claimed"] is not False:
        failures.append("repair correctness")
    if any(
        entry["preserved"] is not True
        for entry in cast(list[dict[str, Any]], cva["boundaries"])
    ):
        failures.append("vertical boundary")
    if len(cast(list[Any], debt["items"])) != len(EXPECTED_DEBT_IDS):
        failures.append("debt register")
    if (
        tuple(
            cast(str, entry["debt_id"])
            for entry in cast(list[dict[str, Any]], debt["items"])
        )
        != EXPECTED_DEBT_IDS
    ):
        failures.append("debt identifiers")
    first_debt = cast(list[dict[str, Any]], debt["items"])[0]
    if first_debt.get("candidate_is_canonical") is not False:
        failures.append("pull request 82 canonicality")
    if first_debt.get("merged_into_p06") is not False:
        failures.append("pull request 82 merge state")
    if er["implementation_state"] != "not_started":
        failures.append("P07 implementation state")
    boundary = cast(list[dict[str, Any]], er["boundary"])
    if not any(
        "not already a reusable invariant" in cast(str, entry["statement"])
        for entry in boundary
    ):
        failures.append("P07 invariant boundary")
    final = cast(list[dict[str, Any]], er["prerequisites"])[-1]
    if final["subject"] != "P06_phase_closure_sealed_publication_candidate":
        failures.append("P07 publication prerequisite")
    if final.get("publication_is_external_to_this_record") is not True:
        failures.append("P07 publication externality")

    assert failures, "the mutated closure was accepted by every owned assertion"


@pytest.mark.parametrize(("mutation", "guard"), MUTATION_CHECKS)
def test_a_mutated_closure_is_refused(mutation: str, guard: str) -> None:
    """The guard name records which assertion each mutation is aimed at."""
    assert guard
    _assert_mutated_document_is_refused(_mutate(_closure(), mutation))


def test_the_unmutated_closure_is_accepted() -> None:
    """The refusal harness must not refuse the real document."""
    with pytest.raises(AssertionError):
        _assert_mutated_document_is_refused(_closure())
