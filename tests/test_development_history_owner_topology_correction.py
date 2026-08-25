from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, cast

import pytest

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
NAMESPACE = REPOSITORY_ROOT / "reference_corpus/contracts/development-history"
DECISION_JSON = NAMESPACE / "decisions/s08-deferred-subject-disposition/decision.json"
CORRECTION_ROOT = NAMESPACE / "corrections/s08-c01-deferred-subject-owner-topology"
CORRECTION_JSON = CORRECTION_ROOT / "correction.json"
CORRECTION_MD = CORRECTION_ROOT / "correction.md"
CORRECTION_SHA256 = CORRECTION_ROOT / "correction.sha256"

# Exactly the six records C01 is authorised to supersede, and the one earlier
# proposal it deliberately declines.
SUPERSEDED_SUBJECT_IDS = (
    "gap:s05-known:discussion-edit-and-deletion-history-unknown",
    "deferred:p01:p05-development-history-event-model",
    "deferred:p01:p05-development-history-relationship-model",
    "deferred:22",
    "deferred:24",
    "deferred:02",
)
RETAINED_SUBJECT_ID = "deferred:p04:04"

PRECEDENT_DISPOSITIONS = ("addressed", "carried_forward", "split")
PRECEDENT_STATES = (
    "evidence_insufficient",
    "unknown_pending_additional_evidence",
    "unsupported_current_scope",
)
VALID_OWNERS = ("S1.P06", "S2", "S5")
PRODUCTION_SOURCE_COUNT = 13


def _correction() -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(CORRECTION_JSON.read_text(encoding="utf-8")))


def _decision() -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(DECISION_JSON.read_text(encoding="utf-8")))


def _superseded() -> list[dict[str, Any]]:
    return cast(list[dict[str, Any]], _correction()["superseded_dispositions"]["items"])


def _projection() -> dict[str, Any]:
    return cast(dict[str, Any], _correction()["effective_projection"])


def _resolve(document: object, pointer: str) -> object:
    current: object = document
    for raw in pointer.lstrip("/").split("/"):
        token = raw.replace("~1", "/").replace("~0", "~")
        if isinstance(current, list):
            current = cast(list[object], current)[int(token)]
        else:
            current = cast(dict[str, object], current)[token]
    return current


def _published_view(item: dict[str, Any]) -> dict[str, Any]:
    """The disposition an S1.P05.S08 record actually expresses."""
    part = item.get("carried_forward") or item["split"]["carried_forward_remainder"]
    return {
        "current_state": part["current_state"],
        "disposition": item["disposition"],
        "immediate_owner": part["immediate_owner"],
        "preserved_long_term_owner": part["preserved_long_term_owner"],
    }


# --- artifact identity --------------------------------------------------------


def test_the_correction_artifact_triple_exists() -> None:
    assert {path.name for path in CORRECTION_ROOT.iterdir()} == {
        "correction.json",
        "correction.md",
        "correction.sha256",
    }


def test_the_sidecar_digest_matches_the_correction_bytes() -> None:
    raw = CORRECTION_JSON.read_bytes()

    assert CORRECTION_SHA256.read_text(encoding="utf-8") == (
        f"{hashlib.sha256(raw).hexdigest()}  correction.json\n"
    )


def test_the_correction_is_canonical_sorted_compact_utf8_lf() -> None:
    raw = CORRECTION_JSON.read_bytes()
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


def test_the_correction_identity_names_c01_and_its_predecessor() -> None:
    identity = _correction()["correction_identity"]

    assert identity["slice"] == "S1.P05.S08.C01"
    assert identity["corrects_slice"] == "S1.P05.S08"
    assert identity["title"] == "Deferred-Subject Owner-Topology Correction"
    assert identity["append_only"] is True
    assert identity["publication_state"] == "sealed_complete"
    assert _correction()["scope"]["production_modules"] == []


# --- append-only: the predecessor is untouched --------------------------------


def test_the_predecessor_decision_is_neither_edited_nor_regenerated() -> None:
    """C01 supersedes by citation. The S08 bytes must still be the cited bytes."""
    integrity = _correction()["predecessor_integrity"]
    cited = next(
        artifact
        for artifact in _correction()["source_locks"]["cited_artifacts"]
        if artifact["lock_id"] == "decision:s1-p05-s08"
    )
    raw = DECISION_JSON.read_bytes()

    assert integrity["append_only"] is True
    assert integrity["predecessor_artifact_regenerated"] is False
    assert integrity["predecessor_statements_remain_historically_correct"] is True
    assert cited["sha256"] == hashlib.sha256(raw).hexdigest()
    assert cited["byte_length"] == len(raw)


def test_every_cited_source_artifact_digest_matches_live_bytes() -> None:
    locks = _correction()["source_locks"]

    assert locks["count"] == len(locks["cited_artifacts"]) == 3
    for artifact in locks["cited_artifacts"]:
        raw = (REPOSITORY_ROOT / artifact["path"]).read_bytes()
        assert artifact["sha256"] == hashlib.sha256(raw).hexdigest()
        assert artifact["byte_length"] == len(raw)


# --- exactly six superseded, one deliberately retained ------------------------


def test_exactly_six_disposition_records_are_superseded() -> None:
    correction = _correction()

    assert correction["superseded_dispositions"]["count"] == 6
    assert len(_superseded()) == 6
    assert correction["assurance"]["coverage"]["superseded_dispositions"] == 6


def test_the_superseded_set_is_exactly_the_authorised_six() -> None:
    observed = tuple(item["source"]["subject_id"] for item in _superseded())

    assert observed == SUPERSEDED_SUBJECT_IDS
    assert len(set(observed)) == 6
    assert RETAINED_SUBJECT_ID not in observed


def test_correction_identifiers_are_unique_and_sequential() -> None:
    ids = [item["correction_id"] for item in _superseded()]

    assert ids == [f"correction:s1-p05-s08-c01:{index:02d}" for index in range(1, 7)]


@pytest.mark.parametrize("index", range(6))
def test_each_superseded_record_quotes_the_published_record_faithfully(
    index: int,
) -> None:
    """The `published` block must match what S1.P05.S08 actually says.

    A correction that misquotes what it supersedes is worthless, so the cited
    pointer is resolved against the sealed decision bytes and compared field by
    field.
    """
    item = _superseded()[index]
    source = item["source"]
    raw = (REPOSITORY_ROOT / source["path"]).read_bytes()

    assert hashlib.sha256(raw).hexdigest() == source["sha256"]

    entry = cast(dict[str, Any], _resolve(json.loads(raw), source["json_pointer"]))
    assert entry["source"]["subject_id"] == source["subject_id"]
    assert entry["disposition_id"] == item["published"]["disposition_id"]

    published = _published_view(entry)
    for field in (
        "disposition",
        "current_state",
        "immediate_owner",
        "preserved_long_term_owner",
    ):
        assert item["published"][field] == published[field]


@pytest.mark.parametrize("index", range(6))
def test_each_superseded_record_actually_changes_something(index: int) -> None:
    """A supersession that changes nothing would be noise, not a correction."""
    item = _superseded()[index]
    published = item["published"]
    corrected = item["corrected"]
    changed = [
        field
        for field in (
            "disposition",
            "current_state",
            "immediate_owner",
            "preserved_long_term_owner",
        )
        if published[field] != corrected[field]
    ]

    assert changed
    assert item["effective_status"] == "superseded_by_append_only_correction"
    assert item["historical_record_bytes_remain_valid"] is True
    assert item["rationale"]


def test_a_disposition_promoted_to_split_records_its_addressed_portion() -> None:
    promoted = [
        item
        for item in _superseded()
        if item["published"]["disposition"] != item["corrected"]["disposition"]
    ]

    assert len(promoted) == 1
    item = promoted[0]
    assert item["published"]["disposition"] == "carried_forward"
    assert item["corrected"]["disposition"] == "split"
    addressed = item["corrected"]["addressed_portion"]
    assert addressed["addressed_by"] == [
        "S1.P05.S01",
        "S1.P05.S03",
        "S1.P05.S04",
        "S1.P05.S05",
    ]
    assert addressed["subject"]
    assert addressed["rationale"]


def test_the_default_branch_record_is_a_deliberate_non_correction() -> None:
    """The earlier S2/S5 proposal is declined on the record, not silently."""
    non_corrections = _correction()["deliberate_non_corrections"]

    assert non_corrections["count"] == 1
    item = non_corrections["items"][0]
    assert item["source"]["subject_id"] == RETAINED_SUBJECT_ID
    assert item["status"] == "deliberate_non_correction"
    assert item["retained"]["immediate_owner"] == "S5"
    assert item["retained"]["preserved_long_term_owner"] == "S5"
    assert item["rationale"]
    assert item["supporting_evidence"]

    for evidence in item["supporting_evidence"]:
        raw = (REPOSITORY_ROOT / evidence["path"]).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == evidence["sha256"]
        _resolve(json.loads(raw), evidence["json_pointer"])


def test_the_retained_record_still_matches_the_published_decision() -> None:
    item = _correction()["deliberate_non_corrections"]["items"][0]
    entry = cast(
        dict[str, Any],
        _resolve(_decision(), item["source"]["json_pointer"]),
    )

    assert _published_view(entry) == {
        "current_state": item["retained"]["current_state"],
        "disposition": item["retained"]["disposition"],
        "immediate_owner": item["retained"]["immediate_owner"],
        "preserved_long_term_owner": item["retained"]["preserved_long_term_owner"],
    }


# --- the effective projection is recomputed, not merely asserted --------------


def test_the_effective_projection_is_reproducible_from_the_two_authorities() -> None:
    """Derive the projection independently and require an exact match.

    The stored projection is convenience. Recomputing it from the sealed
    decision plus the correction is what makes it trustworthy.
    """
    corrections = {
        item["source"]["subject_id"]: item["corrected"] for item in _superseded()
    }
    expected: list[dict[str, Any]] = []
    for entry in _decision()["inherited_subject_register"]["items"]:
        subject_id = entry["source"]["subject_id"]
        view = _published_view(entry)
        if subject_id in corrections:
            corrected = corrections[subject_id]
            view = {key: corrected[key] for key in view}
            authority = "S1.P05.S08.C01"
        else:
            authority = "S1.P05.S08"
        expected.append(
            {**view, "effective_authority": authority, "subject_id": subject_id}
        )

    observed = [
        {
            "current_state": entry["current_state"],
            "disposition": entry["disposition"],
            "effective_authority": entry["effective_authority"],
            "immediate_owner": entry["immediate_owner"],
            "preserved_long_term_owner": entry["preserved_long_term_owner"],
            "subject_id": entry["subject_id"],
        }
        for entry in _projection()["items"]
    ]

    assert observed == expected
    assert len(observed) == 12


def test_the_projection_keeps_twelve_subjects_exactly_once() -> None:
    projection = _projection()
    ids = [entry["subject_id"] for entry in projection["items"]]

    assert projection["count"] == 12
    assert projection["dispositioned_exactly_once"] == 12
    assert projection["self_introduced_count"] == 0
    assert len(set(ids)) == 12
    assert set(ids) == {
        entry["source"]["subject_id"]
        for entry in _decision()["inherited_subject_register"]["items"]
    }


def test_the_projection_reaches_self_owned_open_zero() -> None:
    projection = _projection()

    assert projection["self_owned_open"] == 0
    assert _correction()["assurance"]["self_owned_open"] == 0
    assert projection["owner_completeness"] is True
    for entry in projection["items"]:
        assert entry["immediate_owner"] != "S1.P05"
        assert entry["preserved_long_term_owner"] != "S1.P05"
        assert entry["immediate_owner"] in VALID_OWNERS
        assert entry["preserved_long_term_owner"] in VALID_OWNERS


def test_the_projection_totals_match_its_items() -> None:
    projection = _projection()
    dispositions: dict[str, int] = {}
    immediate: dict[str, int] = {}
    long_term: dict[str, int] = {}
    states: dict[str, int] = {}
    authority: dict[str, int] = {}

    for entry in projection["items"]:
        dispositions[entry["disposition"]] = (
            dispositions.get(entry["disposition"], 0) + 1
        )
        immediate[entry["immediate_owner"]] = (
            immediate.get(entry["immediate_owner"], 0) + 1
        )
        long_term[entry["preserved_long_term_owner"]] = (
            long_term.get(entry["preserved_long_term_owner"], 0) + 1
        )
        states[entry["current_state"]] = states.get(entry["current_state"], 0) + 1
        authority[entry["effective_authority"]] = (
            authority.get(entry["effective_authority"], 0) + 1
        )

    assert projection["disposition_totals"] == dispositions
    assert projection["immediate_owner_totals"] == immediate
    assert projection["long_term_owner_totals"] == long_term
    assert projection["state_totals"] == states
    assert projection["authority_totals"] == authority
    assert authority == {"S1.P05.S08": 6, "S1.P05.S08.C01": 6}
    assert sum(states.values()) == 12


def test_no_new_disposition_or_state_vocabulary_is_introduced() -> None:
    for entry in _projection()["items"]:
        assert entry["disposition"] in PRECEDENT_DISPOSITIONS
        assert entry["current_state"] in PRECEDENT_STATES
    for item in _superseded():
        assert item["corrected"]["disposition"] in PRECEDENT_DISPOSITIONS
        assert item["corrected"]["current_state"] in PRECEDENT_STATES


# --- owner-topology outcomes --------------------------------------------------


def test_generic_graph_semantics_belong_to_s5_and_not_to_p06() -> None:
    """The correction's whole point: P06 does not own a generic Git graph."""
    owners = {
        entry["subject_id"]: entry["immediate_owner"]
        for entry in _projection()["items"]
    }

    for subject_id in (
        "deferred:22",
        "deferred:02",
        "deferred:p01:p05-development-history-event-model",
        "deferred:p01:p05-development-history-relationship-model",
    ):
        assert owners[subject_id] == "S5"

    p06 = next(
        entry
        for entry in _correction()["downstream_handoff"]["handoffs"]
        if entry["target"] == "S1.P06"
    )
    assert "own_a_generic_git_ancestry_or_reachability_graph" in p06["prohibited"]


def test_p06_retains_only_the_bounded_relationship_vocabulary() -> None:
    p06_subjects = [
        entry["subject_id"]
        for entry in _projection()["items"]
        if entry["immediate_owner"] == "S1.P06"
    ]

    assert p06_subjects == ["gap:s05-known:case-relationship-vocabulary-provisional"]


def test_every_projection_owner_receives_a_handoff() -> None:
    handoffs = _correction()["downstream_handoff"]["handoffs"]
    targets = {entry["target"] for entry in handoffs}
    owners = {entry["immediate_owner"] for entry in _projection()["items"]}
    owners |= {entry["preserved_long_term_owner"] for entry in _projection()["items"]}

    assert owners <= targets
    for entry in handoffs:
        assert entry["status"] == "not_started"
        assert entry["received_subjects"]
        assert entry["requirements"]
        assert entry["prohibited"]


def test_every_predecessor_handoff_is_superseded_exactly_once() -> None:
    """Two sealed artifacts must not leave two live handoff sets.

    The correction moves subjects between owners, so the predecessor handoff
    membership no longer describes the effective projection. Without an explicit
    supersession a replay has no deterministic rule for which set is effective.
    """
    correction = _correction()
    decision_handoffs = _decision()["downstream_handoff"]["handoffs"]
    superseded = correction["superseded_handoffs"]["items"]

    assert correction["superseded_handoffs"]["count"] == len(decision_handoffs) == 3
    assert len(superseded) == 3

    published_ids = [entry["handoff_id"] for entry in decision_handoffs]
    assert [entry["published_handoff_id"] for entry in superseded] == published_ids
    assert len({entry["published_handoff_id"] for entry in superseded}) == 3

    effective_ids = {
        entry["handoff_id"] for entry in correction["downstream_handoff"]["handoffs"]
    }
    for entry in superseded:
        assert entry["effective_status"] == "superseded_by_append_only_correction"
        assert entry["historical_record_bytes_remain_valid"] is True
        assert entry["replaced_by_handoff_id"] in effective_ids
        source = entry["source"]
        raw = (REPOSITORY_ROOT / source["path"]).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == source["sha256"]
        resolved = cast(
            dict[str, Any], _resolve(json.loads(raw), source["json_pointer"])
        )
        assert resolved["handoff_id"] == entry["published_handoff_id"]
        assert resolved["target"] == entry["target"]


def test_every_effective_handoff_names_the_predecessor_it_replaces() -> None:
    superseded = {
        entry["replaced_by_handoff_id"]: entry["published_handoff_id"]
        for entry in _correction()["superseded_handoffs"]["items"]
    }

    for entry in _correction()["downstream_handoff"]["handoffs"]:
        assert entry["supersedes_handoff_id"] == superseded[entry["handoff_id"]]
    assert _correction()["downstream_handoff"]["authority"]


@pytest.mark.parametrize("target", ("S2", "S5", "S1.P06"))
def test_every_received_subject_is_covered_by_a_requirement(target: str) -> None:
    """A reassigned subject must not silently lose its obligation.

    The predecessor stated acquisition obligations per owner. When subjects move
    between owners, a single broad requirement can quietly drop one, so every
    requirement names the subjects it covers and the union must be total.
    """
    handoff = next(
        entry
        for entry in _correction()["downstream_handoff"]["handoffs"]
        if entry["target"] == target
    )
    received = set(handoff["received_subjects"])
    covered: set[str] = set()
    for requirement in handoff["requirements"]:
        assert requirement["requirement_id"].startswith("requirement:s1-p05-s08-c01:")
        assert requirement["statement"]
        assert requirement["covers_subjects"]
        covered |= set(requirement["covers_subjects"])

    assert covered == received
    assert (
        _correction()["assurance"]["coverage"][
            "every_received_subject_is_covered_by_a_requirement"
        ]
        is True
    )


def test_the_remainders_each_owner_receives_match_the_projection() -> None:
    projection = _projection()["items"]
    expected = {
        "S2": sorted(
            {e["remainder_subject"] for e in projection if e["immediate_owner"] == "S2"}
        ),
        "S5": sorted(
            {
                e["remainder_subject"]
                for e in projection
                if e["preserved_long_term_owner"] == "S5"
            }
        ),
        "S1.P06": sorted(
            {
                e["remainder_subject"]
                for e in projection
                if e["immediate_owner"] == "S1.P06"
            }
        ),
    }

    for entry in _correction()["downstream_handoff"]["handoffs"]:
        assert entry["received_subjects"] == expected[entry["target"]]


def test_every_projection_entry_names_its_unresolved_remainder() -> None:
    """The remainder is what remains open, and it comes from the authority.

    For a split record the inherited subject overstates what is unresolved, so
    the remainder is read from the sealed decision rather than reused from the
    subject name.
    """
    remainders: dict[str, str] = {}
    for entry in _decision()["inherited_subject_register"]["items"]:
        part = (
            entry.get("carried_forward") or entry["split"]["carried_forward_remainder"]
        )
        remainders[entry["source"]["subject_id"]] = part["subject"]

    for entry in _projection()["items"]:
        assert entry["remainder_subject"] == remainders[entry["subject_id"]]


@pytest.mark.parametrize("target", ("S2", "S5", "S1.P06"))
def test_every_predecessor_requirement_is_accounted_for(target: str) -> None:
    """Full supersession must not silently drop an obligation.

    The predecessor handoffs are superseded in full, so any requirement they
    stated is either carried over verbatim, subsumed by a named successor, or
    retired with a reason. Nothing may simply vanish.
    """
    superseded = next(
        entry
        for entry in _correction()["superseded_handoffs"]["items"]
        if entry["target"] == target
    )
    replacement = next(
        entry
        for entry in _correction()["downstream_handoff"]["handoffs"]
        if entry["target"] == target
    )
    predecessor = next(
        entry
        for entry in _decision()["downstream_handoff"]["handoffs"]
        if entry["handoff_id"] == superseded["published_handoff_id"]
    )

    continuity = superseded["requirement_continuity"]
    statements = [row["predecessor_statement"] for row in continuity]
    assert sorted(statements) == sorted(predecessor["requirements"])
    assert len(statements) == len(set(statements))

    successor_ids = {r["requirement_id"] for r in replacement["requirements"]}
    successor_statements = {r["statement"] for r in replacement["requirements"]}
    for row in continuity:
        assert row["status"] in {"retained", "subsumed", "retired"}
        if row["status"] == "retained":
            assert row["predecessor_statement"] in successor_statements
            assert row["successor_requirement_ids"]
        if row["status"] == "subsumed":
            assert row["successor_requirement_ids"]
        if row["status"] == "retired":
            assert row["reason"]
        for identifier in row["successor_requirement_ids"]:
            assert identifier in successor_ids


def test_p06_still_may_not_redefine_the_published_history_facts() -> None:
    """The constraint the correction's own supersession rule nearly dropped."""
    p06 = next(
        entry
        for entry in _correction()["downstream_handoff"]["handoffs"]
        if entry["target"] == "S1.P06"
    )
    statements = {requirement["statement"] for requirement in p06["requirements"]}

    assert (
        "consume_the_bounded_S1_P05_history_facts_without_redefining_them" in statements
    )
    assert (
        _correction()["assurance"]["coverage"][
            "every_predecessor_requirement_is_retained_subsumed_or_retired"
        ]
        is True
    )


def test_no_addressed_portion_is_ever_handed_off() -> None:
    """Handing off an addressed portion would invite a replay to reopen it.

    Every portion `S1.P05` actually published is named in a split record. None
    of those names may appear in any handoff or requirement.
    """
    addressed: set[str] = set()
    for entry in _decision()["inherited_subject_register"]["items"]:
        if entry["disposition"] == "split":
            addressed.add(entry["split"]["addressed_portion"]["subject"])
    for item in _superseded():
        portion = item["corrected"].get("addressed_portion")
        if portion is not None:
            addressed.add(portion["subject"])

    assert addressed
    handed_off: set[str] = set()
    for entry in _correction()["downstream_handoff"]["handoffs"]:
        handed_off |= set(entry["received_subjects"])
        for requirement in entry["requirements"]:
            handed_off |= set(requirement["covers_subjects"])

    assert handed_off.isdisjoint(addressed)
    assert (
        _correction()["assurance"]["coverage"][
            "handoffs_transfer_unresolved_remainders_only"
        ]
        is True
    )


# --- anti-fabrication ---------------------------------------------------------


def test_the_correction_introduces_no_product_semantics() -> None:
    governance = _correction()["assurance"]["governance_only"]
    observed = {
        path.relative_to(REPOSITORY_ROOT).as_posix()
        for path in (REPOSITORY_ROOT / "src").rglob("*.py")
    }

    assert len(observed) == PRODUCTION_SOURCE_COUNT
    assert governance["production_python_source_count"] == PRODUCTION_SOURCE_COUNT
    assert governance["no_production_source_changed"] is True
    assert governance["no_production_module_added"] is True
    assert governance["no_dependency_or_lockfile_change"] is True


def test_the_preserved_non_generalizations_name_the_boundaries() -> None:
    non_generalizations = _correction()["non_generalizations"]

    assert non_generalizations["count"] == len(non_generalizations["items"]) == 8
    joined = " | ".join(non_generalizations["items"])
    for needle in (
        "does not own a generic Git ancestry",
        "no historical default-branch substitution",
        "remain separate subjects with separate owners",
        "not regenerated",
        "LEVEL 1 record-level only",
        "owner assignment and not an implementation",
    ):
        assert needle in joined


def test_the_correction_asserts_package_exclusion() -> None:
    exclusion = _correction()["assurance"]["package_exclusion"]

    assert exclusion["excluded_from_wheel"] is True
    assert exclusion["excluded_from_sdist"] is True


# --- derived sidecar and roadmap ---------------------------------------------


def test_the_markdown_is_derived_and_agrees_with_the_correction() -> None:
    text = CORRECTION_MD.read_text(encoding="utf-8")
    digest = hashlib.sha256(CORRECTION_JSON.read_bytes()).hexdigest()

    assert text.startswith(
        "# Development History Deferred-Subject Owner-Topology Correction"
    )
    assert digest in text
    assert "self_owned_open == 0" in text
    for subject_id in (*SUPERSEDED_SUBJECT_IDS, RETAINED_SUBJECT_ID):
        assert f"`{subject_id}`" in text
    for artifact in _correction()["source_locks"]["cited_artifacts"]:
        assert artifact["sha256"] in text
    for entry in _correction()["superseded_handoffs"]["items"]:
        assert f"`{entry['published_handoff_id']}`" in text


def test_every_phase_status_summary_records_the_correction() -> None:
    """The roadmap repeats its phase state in several places.

    Recording the correction only in the provisional sequence would leave the
    repeated summaries stale, so every summary that calls `S1.P05.S08` complete
    must also name the correction.
    """
    text = " ".join(
        (REPOSITORY_ROOT / "docs/roadmap.md").read_text(encoding="utf-8").split()
    )
    complete = text.count("`S1.P05.S08` are complete")
    recorded = text.count("including the `S1.P05.S08.C01` correction")

    assert complete >= 4
    assert recorded == complete
    assert text.count("`S1.P05.S09` is next and not started") == complete


def test_the_derived_summary_preserves_whole_rationale_sentences() -> None:
    """The summary column must not cut a sentence inside a Slice identifier.

    Splitting on a bare period truncates `S1.P06` to `S1`, which would make the
    Markdown an unfaithful rendering of the JSON authority.
    """
    text = CORRECTION_MD.read_text(encoding="utf-8")
    rows = [
        line
        for line in text.splitlines()
        if line.startswith("| ") and line.count("|") >= 6 and line[2].isdigit()
    ]

    assert len(rows) == 6
    for row, item in zip(rows, _superseded(), strict=True):
        summary = row.split("|")[-2].strip()
        assert summary
        assert not summary.endswith("S1.")
        assert item["rationale"].startswith(summary.rstrip("."))


def test_the_roadmap_records_the_correction_and_holds_the_phase_state() -> None:
    text = " ".join(
        (REPOSITORY_ROOT / "docs/roadmap.md").read_text(encoding="utf-8").split()
    )

    assert "`S1.P05.S08.C01`" in text
    assert "`S1.P05.S09` is next and not started" in text
    assert "`S1.P05.S09` — Contract Corpus (provisional; next, not started)" in text
    assert "`S1.P05.S10` — Integration and Phase Closure (provisional)" in text
    assert "`S1.P05` is active and incomplete" in text
    assert "`S1.P06` is not eligible to begin" in text
