from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, cast

import pytest

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
DECISION_ROOT = (
    REPOSITORY_ROOT
    / "reference_corpus/contracts/development-history/decisions"
    / "s08-deferred-subject-disposition"
)
DECISION_JSON = DECISION_ROOT / "decision.json"
DECISION_MD = DECISION_ROOT / "decision.md"
DECISION_SHA256 = DECISION_ROOT / "decision.sha256"

# The five sealed predecessor closures this disposition redisposes from, and the
# retained acquisition it cites as evidence.
CITED_ARTIFACTS = {
    "closure:s1-p00": "reference_corpus/pytest-4412/closures/s1-p00-phase-closure/closure.json",
    "closure:s1-p01": (
        "reference_corpus/contracts/identity/closures/s1-p01-phase-closure/closure.json"
    ),
    "closure:s1-p02": (
        "reference_corpus/contracts/revision-locator/closures"
        "/s1-p02-phase-closure/closure.json"
    ),
    "closure:s1-p03": (
        "reference_corpus/contracts/evidence-envelope/closures"
        "/s1-p03-phase-closure/closure.json"
    ),
    "closure:s1-p04": (
        "reference_corpus/contracts/repository-snapshot/closures"
        "/s1-p04-phase-closure/closure.json"
    ),
    "acquisition:pytest-4412-run-0001": (
        "reference_corpus/pytest-4412/acquisitions"
        "/run-0001-s04-v1-base-4c9cde74-head-690a63b9/acquisition.json"
    ),
}

# Exactly the vocabulary S1.P04.S08 published. S1.P05.S08 introduces none.
PRECEDENT_DISPOSITIONS = ("addressed", "carried_forward", "split")
PRECEDENT_STATES = (
    "evidence_insufficient",
    "unknown_pending_additional_evidence",
    "unsupported_current_scope",
)
P04_DECISION = (
    REPOSITORY_ROOT
    / "reference_corpus/contracts/repository-snapshot/decisions"
    / "s08-deferred-subject-disposition/decision.json"
)

EXPECTED_SUBJECT_IDS = (
    "gap:s05-known:discussion-edit-and-deletion-history-unknown",
    "gap:s05-known:case-relationship-vocabulary-provisional",
    "deferred:p01:p05-development-history-event-model",
    "deferred:p01:p05-development-history-relationship-model",
    "deferred:p01:evidence-original-head-repository",
    "deferred:p01:evidence-historical-source-completeness",
    "deferred:21",
    "deferred:22",
    "deferred:23",
    "deferred:24",
    "deferred:02",
    "deferred:p04:04",
)

FORBIDDEN_OWNERS = ("S1.P05",)

PRODUCTION_SOURCE_COUNT = 13


def _decision() -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(DECISION_JSON.read_text(encoding="utf-8")))


def _register() -> dict[str, Any]:
    return cast(dict[str, Any], _decision()["inherited_subject_register"])


def _items() -> list[dict[str, Any]]:
    return cast(list[dict[str, Any]], _register()["items"])


def _remainder(item: dict[str, Any]) -> dict[str, Any]:
    """The carried-forward part of an item, whether whole or split."""
    if item["disposition"] == "split":
        return cast(dict[str, Any], item["split"]["carried_forward_remainder"])
    return cast(dict[str, Any], item["carried_forward"])


def _resolve(document: object, pointer: str) -> object:
    """Minimal RFC 6901 resolution, sufficient for the pointers cited here."""
    current: object = document
    for raw in pointer.lstrip("/").split("/"):
        token = raw.replace("~1", "/").replace("~0", "~")
        if isinstance(current, list):
            current = cast(list[object], current)[int(token)]
        else:
            current = cast(dict[str, object], current)[token]
    return current


# --- artifact identity and canonicalization ----------------------------------


def test_the_three_governance_artifacts_exist() -> None:
    assert DECISION_JSON.is_file()
    assert DECISION_MD.is_file()
    assert DECISION_SHA256.is_file()
    assert {path.name for path in DECISION_ROOT.iterdir()} == {
        "decision.json",
        "decision.md",
        "decision.sha256",
    }


def test_the_sidecar_digest_matches_the_decision_bytes() -> None:
    raw = DECISION_JSON.read_bytes()
    recorded = DECISION_SHA256.read_text(encoding="utf-8")

    assert recorded == f"{hashlib.sha256(raw).hexdigest()}  decision.json\n"


def test_the_decision_is_canonical_sorted_compact_utf8_lf() -> None:
    raw = DECISION_JSON.read_bytes()
    canonical = (
        json.dumps(
            json.loads(raw), sort_keys=True, separators=(",", ":"), ensure_ascii=False
        )
        + "\n"
    ).encode("utf-8")

    assert raw == canonical
    assert not raw.startswith(b"\xef\xbb\xbf")
    assert b"\r" not in raw
    assert raw.count(b"\n") == 1
    assert _decision()["format"]["canonicalization"]["name"] == (
        "json-sort-keys-compact-utf8-lf-v1"
    )


def test_the_decision_declares_itself_governance_only_and_not_a_schema() -> None:
    fmt = _decision()["format"]

    assert fmt["public_contract"] is False
    assert fmt["production_persistence"] is False
    assert fmt["status"] == "sealed_complete"
    assert "not_a_production_schema" in fmt["non_production_schema_warning"]
    assert fmt["primary_authority"].startswith("decision.json_is_the_sole")


def test_the_phase_identity_names_s08_and_does_not_close_the_phase() -> None:
    identity = _decision()["phase_identity"]

    assert identity["phase"] == "S1.P05"
    assert identity["slice"] == "S1.P05.S08"
    assert identity["title"] == "Deferred-Subject Disposition"
    assert identity["closes_phase"] is False
    assert identity["production_change"] is False
    assert identity["next_slice"] == "S1.P05.S09"
    assert identity["inherited_from"] == [
        "S1.P00",
        "S1.P01",
        "S1.P02",
        "S1.P03",
        "S1.P04",
    ]


# --- the register itself ------------------------------------------------------


def test_exactly_twelve_inherited_subjects_and_no_self_introduced_subject() -> None:
    register = _register()

    assert register["count"] == 12
    assert register["self_introduced_count"] == 0
    assert len(register["items"]) == 12


def test_every_subject_is_dispositioned_exactly_once() -> None:
    register = _register()
    subject_ids = [item["source"]["subject_id"] for item in _items()]

    assert tuple(subject_ids) == EXPECTED_SUBJECT_IDS
    assert len(set(subject_ids)) == 12
    assert register["dispositioned_exactly_once"] == 12


def test_disposition_identifiers_are_unique_and_sequential() -> None:
    ids = [item["disposition_id"] for item in _items()]

    assert ids == [f"disposition:s1-p05-s08:{index:02d}" for index in range(1, 13)]


def test_self_owned_open_is_zero_and_no_remainder_stays_with_p05() -> None:
    register = _register()

    assert register["self_owned_open"] == 0
    assert _decision()["assurance"]["self_owned_open"] == 0
    assert register["owner_completeness"] is True

    for item in _items():
        remainder = _remainder(item)
        for owner in FORBIDDEN_OWNERS:
            assert remainder["immediate_owner"] != owner
            assert remainder["preserved_long_term_owner"] != owner


def test_the_recorded_totals_match_the_items() -> None:
    register = _register()
    dispositions: dict[str, int] = {}
    immediate: dict[str, int] = {}
    long_term: dict[str, int] = {}
    states: dict[str, int] = {}

    for item in _items():
        dispositions[item["disposition"]] = dispositions.get(item["disposition"], 0) + 1
        remainder = _remainder(item)
        immediate[remainder["immediate_owner"]] = (
            immediate.get(remainder["immediate_owner"], 0) + 1
        )
        long_term[remainder["preserved_long_term_owner"]] = (
            long_term.get(remainder["preserved_long_term_owner"], 0) + 1
        )
        states[remainder["current_state"]] = (
            states.get(remainder["current_state"], 0) + 1
        )

    assert register["addressed_count"] == dispositions.get("addressed", 0)
    assert register["split_count"] == dispositions.get("split", 0)
    assert register["carried_forward_count"] == dispositions.get("carried_forward", 0)
    assert (
        register["addressed_count"]
        + register["split_count"]
        + register["carried_forward_count"]
        == 12
    )
    assert register["immediate_owner_totals"] == immediate
    assert register["long_term_owner_totals"] == long_term
    assert register["state_totals"] == states
    assert sum(states.values()) == 12


def test_no_new_disposition_or_state_vocabulary_is_introduced() -> None:
    """S1.P05.S08 reuses exactly the vocabulary S1.P04.S08 published."""
    p04 = json.loads(P04_DECISION.read_text(encoding="utf-8"))
    p04_items = p04["inherited_subject_register"]["items"]
    p04_dispositions = {item["disposition"] for item in p04_items}
    p04_states = set(p04["inherited_subject_register"]["state_totals"])

    assert p04_dispositions <= set(PRECEDENT_DISPOSITIONS)
    assert p04_states <= set(PRECEDENT_STATES)

    for item in _items():
        assert item["disposition"] in PRECEDENT_DISPOSITIONS
        assert _remainder(item)["current_state"] in PRECEDENT_STATES


# --- the register is not fabricated -------------------------------------------


def test_every_cited_source_artifact_is_locked_by_exact_digest() -> None:
    locks = _decision()["source_locks"]
    assert locks["count"] == len(locks["cited_artifacts"]) == 6
    assert locks["immutable"] is True

    for artifact in locks["cited_artifacts"]:
        path = REPOSITORY_ROOT / artifact["path"]
        raw = path.read_bytes()

        assert CITED_ARTIFACTS[artifact["lock_id"]] == artifact["path"]
        assert artifact["byte_length"] == len(raw)
        assert artifact["sha256"] == hashlib.sha256(raw).hexdigest()


@pytest.mark.parametrize("index", range(12))
def test_each_subject_resolves_to_its_real_predecessor_entry(index: int) -> None:
    """The cited pointer must actually hold the subject the register claims.

    A disposition register is only worth its citations. Each item is resolved
    against the sealed predecessor bytes and must agree on the subject id, the
    predecessor state, and the predecessor owner.
    """
    item = _items()[index]
    source = item["source"]
    path = REPOSITORY_ROOT / source["path"]
    raw = path.read_bytes()

    assert hashlib.sha256(raw).hexdigest() == source["sha256"]

    entry = cast(dict[str, Any], _resolve(json.loads(raw), source["json_pointer"]))
    recorded_id = entry.get("deferred_item_id") or entry.get("deferred_id")
    recorded_owner = (
        entry.get("immediate_owner")
        or entry.get("immediate_next_owner")
        or entry.get("owner")
    )
    recorded_state = entry.get("current_state") or entry.get("implementation_state")

    assert recorded_id == source["subject_id"]
    assert recorded_owner == "S1.P05"
    assert recorded_state == source["source_state"]
    assert source["source_immediate_owner"] == "S1.P05"


def test_every_predecessor_p05_subject_appears_exactly_once() -> None:
    """Closed world: the register must cover every P05-routed predecessor entry.

    Derived from the sealed registers rather than from this file's own list, so
    a predecessor subject that is missed cannot pass unnoticed.
    """
    routed: set[str] = set()
    for lock_id, relative in CITED_ARTIFACTS.items():
        if not lock_id.startswith("closure:"):
            continue
        document = cast(
            dict[str, Any],
            json.loads((REPOSITORY_ROOT / relative).read_text(encoding="utf-8")),
        )
        register = cast(dict[str, Any], document["deferred_register"])
        entries = cast(
            list[dict[str, Any]],
            register.get("items") or register.get("entries") or [],
        )
        for entry in entries:
            owner = (
                entry.get("immediate_owner")
                or entry.get("immediate_next_owner")
                or entry.get("owner")
            )
            if owner == "S1.P05":
                identifier = entry.get("deferred_item_id") or entry.get("deferred_id")
                routed.add(cast(str, identifier))

    assert routed == set(EXPECTED_SUBJECT_IDS)
    assert len(routed) == 12


def test_every_carried_forward_remainder_names_evidence_and_a_later_owner() -> None:
    for item in _items():
        remainder = _remainder(item)

        assert remainder["subject"]
        assert remainder["rationale"]
        assert remainder["immediate_owner"] in {"S2", "S5", "S1.P06"}
        assert remainder["preserved_long_term_owner"] in {"S2", "S5", "S1.P06"}
        assert remainder["evidence"]
        for evidence in remainder["evidence"]:
            path = REPOSITORY_ROOT / evidence["path"]
            raw = path.read_bytes()
            assert hashlib.sha256(raw).hexdigest() == evidence["sha256"]
            _resolve(json.loads(raw), evidence["json_pointer"])


def test_every_split_names_published_slices_for_its_addressed_portion() -> None:
    splits = [item for item in _items() if item["disposition"] == "split"]

    assert len(splits) == _register()["split_count"]
    for item in splits:
        addressed = item["split"]["addressed_portion"]
        assert addressed["subject"]
        assert addressed["rationale"]
        assert addressed["addressed_by"]
        for slice_id in addressed["addressed_by"]:
            assert slice_id.startswith("S1.P05.S0")


# --- handoffs and non-claims --------------------------------------------------


def test_every_carried_forward_owner_receives_a_handoff() -> None:
    handoff = _decision()["downstream_handoff"]
    targets = {entry["target"] for entry in handoff["handoffs"]}
    owners = {_remainder(item)["immediate_owner"] for item in _items()}
    owners |= {_remainder(item)["preserved_long_term_owner"] for item in _items()}

    assert handoff["count"] == len(handoff["handoffs"]) == 3
    assert owners <= targets
    for entry in handoff["handoffs"]:
        assert entry["status"] == "not_started"
        assert entry["received_subjects"]
        assert entry["requirements"]
        assert entry["prohibited"]


def test_the_handoffs_forbid_the_named_fabrications() -> None:
    prohibited = {
        text
        for entry in _decision()["downstream_handoff"]["handoffs"]
        for text in entry["prohibited"]
    }

    assert "substitute_a_current_observation_for_a_historical_unknown" in prohibited
    assert "treat_absence_of_retained_edit_evidence_as_absence_of_edits" in prohibited
    assert "upgrade_the_LEVEL_1_evidence_association_implicitly" in prohibited
    assert (
        "read_the_bounded_S1_P05_surface_as_a_complete_development_history"
        in prohibited
    )


def test_the_preserved_non_generalizations_are_exact() -> None:
    non_generalizations = _decision()["non_generalizations"]

    assert non_generalizations["count"] == len(non_generalizations["items"]) == 13
    assert non_generalizations["intentional_deferral_is_not_implementation_failure"]
    joined = " | ".join(non_generalizations["items"])
    for needle in (
        "no historical default-branch substitution",
        "no ancestry",
        "no rename or copy inference",
        "no generic development event",
        "LEVEL 1 record-level only",
    ):
        assert needle in joined


# The historical default branch is a separate inherited subject, dispositioned to
# S2 by S1.P04.S08. It is deliberately absent from this register.
HISTORICAL_DEFAULT_BRANCH_SUBJECT = "gap:s05-known:historical-default-branch-unknown"
DEFAULT_BRANCH_SUBJECT_ID = "deferred:p04:04"


def _default_branch_item() -> dict[str, Any]:
    return next(
        item
        for item in _items()
        if item["source"]["subject_id"] == DEFAULT_BRANCH_SUBJECT_ID
    )


def test_the_default_branch_subject_does_not_absorb_the_historical_unknown() -> None:
    """Two inherited subjects, two owners, kept apart.

    `deferred:19` assigns the default-branch designation to S1.P05 while the
    historical default branch is a separate subject already owned by S2. Folding
    them together would let one disposition silently answer for both.
    """
    remainder = _remainder(_default_branch_item())
    separated = remainder["separated_subjects"]

    assert HISTORICAL_DEFAULT_BRANCH_SUBJECT not in EXPECTED_SUBJECT_IDS
    assert len(separated) == 2
    assert {entry["state"] for entry in separated} == {
        "observed_current_designation",
        "unknown_historical_designation",
    }
    assert {entry["owner"] for entry in separated} == {"S2", "S5"}
    current = next(e for e in separated if e["state"] == "observed_current_designation")
    historical = next(
        e for e in separated if e["state"] == "unknown_historical_designation"
    )
    assert current["owner"] == "S5"
    assert historical["owner"] == "S2"
    assert HISTORICAL_DEFAULT_BRANCH_SUBJECT in remainder["rationale"]


def test_the_default_branch_subject_is_not_routed_to_an_acquisition_owner() -> None:
    """Its blocker is a missing semantic owner, not missing evidence.

    The retained repository observation already supplies a current designation,
    so routing this subject to the acquisition owner would misstate why it is
    unresolved.
    """
    remainder = _remainder(_default_branch_item())

    assert remainder["immediate_owner"] == "S5"
    assert remainder["preserved_long_term_owner"] == "S5"
    assert remainder["current_state"] == "unsupported_current_scope"

    acquisition = next(
        entry
        for entry in _decision()["downstream_handoff"]["handoffs"]
        if entry["target"] == "S2"
    )
    semantic = next(
        entry
        for entry in _decision()["downstream_handoff"]["handoffs"]
        if entry["target"] == "S5"
    )
    assert (
        "default-branch designation semantics" not in acquisition["received_subjects"]
    )
    assert "default-branch designation semantics" in semantic["received_subjects"]
    assert (
        "merge_the_separately_owned_historical_default_branch_unknown"
        "_into_the_designation_subject" in semantic["prohibited"]
    )
    assert (
        "substitute_a_current_observation_for_a_historical_unknown"
        in (semantic["prohibited"])
    )


def test_the_current_default_branch_observation_is_cited_as_retained_evidence() -> None:
    """The disposition rests on the observation actually existing."""
    remainder = _remainder(_default_branch_item())
    pointers = {entry["json_pointer"] for entry in remainder["evidence"]}

    assert "/observations/repository/default_branch_observation" in pointers
    acquisition = REPOSITORY_ROOT / CITED_ARTIFACTS["acquisition:pytest-4412-run-0001"]
    observation = cast(
        dict[str, Any],
        _resolve(
            json.loads(acquisition.read_text(encoding="utf-8")),
            "/observations/repository/default_branch_observation",
        ),
    )
    assert observation["value"]
    assert observation["observed_at"]


def test_predecessor_artifacts_are_unmodified_and_the_register_is_append_only() -> None:
    integrity = _decision()["predecessor_integrity"]

    assert integrity["append_only"] is True
    assert integrity["predecessor_statements_remain_historically_correct"] is True
    assert "no predecessor byte is edited" in integrity["mechanism"]


# --- governance-only ----------------------------------------------------------


def test_the_slice_changed_no_production_source() -> None:
    observed = {
        path.relative_to(REPOSITORY_ROOT).as_posix()
        for path in (REPOSITORY_ROOT / "src").rglob("*.py")
    }
    governance = _decision()["assurance"]["governance_only"]

    assert len(observed) == PRODUCTION_SOURCE_COUNT
    assert governance["production_python_source_count"] == PRODUCTION_SOURCE_COUNT
    assert governance["no_production_source_changed"] is True
    assert governance["no_production_module_added"] is True
    assert governance["no_deferred_product_semantics_implemented"] is True
    assert governance["no_dependency_or_lockfile_change"] is True


def test_the_decision_claims_no_subject_falsely_resolved() -> None:
    coverage = _decision()["assurance"]["coverage"]

    assert coverage["no_subject_falsely_claimed_resolved"] is True
    assert coverage["inherited_subjects_dispositioned_exactly_once"] == 12
    assert coverage["every_carried_forward_remainder_names_a_later_owner"] is True
    assert coverage["no_new_disposition_vocabulary_introduced"] is True
    assert coverage["predecessor_artifacts_unmodified"] is True


def test_the_decision_asserts_package_exclusion() -> None:
    exclusion = _decision()["assurance"]["package_exclusion"]

    assert exclusion["excluded_from_wheel"] is True
    assert exclusion["excluded_from_sdist"] is True


# --- the roadmap agrees with the authority ------------------------------------


ROADMAP = REPOSITORY_ROOT / "docs/roadmap.md"


def test_the_roadmap_owner_totals_agree_with_the_decision() -> None:
    """The roadmap is derived narrative; `decision.json` is the authority.

    The counts are stated in prose, so they can drift silently when a
    disposition is corrected. This binds them to the register.
    """
    register = _register()
    text = " ".join(ROADMAP.read_text(encoding="utf-8").split())
    immediate = register["immediate_owner_totals"]
    long_term = register["long_term_owner_totals"]
    words = {1: "one", 2: "two", 4: "four", 5: "five", 6: "six", 8: "eight"}

    assert (
        f"Immediate owners are therefore `S1.P06` {words[immediate['S1.P06']]}, "
        f"`S2` {words[immediate['S2']]}, and `S5` {words[immediate['S5']]}" in text
    )
    assert (
        f"long-term owners are `S1.P06` {words[long_term['S1.P06']]}, "
        f"`S5` {words[long_term['S5']]}, and `S2` {words[long_term['S2']]}" in text
    )
    lowered = text.lower()
    assert f"{words[register['split_count']]} are split" in lowered
    assert f"{words[register['carried_forward_count']]} are carried forward" in lowered


def test_the_roadmap_records_the_s08_disposition_and_transition() -> None:
    text = " ".join(ROADMAP.read_text(encoding="utf-8").split())

    assert "`S1.P05.S08` — Deferred-Subject Disposition (complete)" in text
    assert "`S1.P05.S10` is next and not started" in text
    assert "`self_owned_open == 0`" in text
    assert "reference_corpus/contracts/development-history/decisions" in text


# --- derived sidecar ----------------------------------------------------------


def test_the_markdown_is_derived_and_agrees_with_the_decision() -> None:
    text = DECISION_MD.read_text(encoding="utf-8")
    digest = hashlib.sha256(DECISION_JSON.read_bytes()).hexdigest()

    assert text.startswith("# Development History Deferred-Subject Disposition")
    assert "`decision.json` is the\nsole durable semantic authority" in text or (
        "sole durable semantic authority" in text
    )
    assert digest in text
    assert "self_owned_open == 0" in text
    for subject_id in EXPECTED_SUBJECT_IDS:
        assert f"`{subject_id}`" in text


def test_the_markdown_lists_every_locked_source_artifact() -> None:
    text = DECISION_MD.read_text(encoding="utf-8")

    for artifact in _decision()["source_locks"]["cited_artifacts"]:
        assert artifact["path"] in text
        assert artifact["sha256"] in text
