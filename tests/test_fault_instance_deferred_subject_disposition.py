from __future__ import annotations

import hashlib
import importlib
import json
import pathlib
import re
import tarfile
import zipfile
from typing import Any, cast

import pytest

REPOSITORY_ROOT = pathlib.Path(__file__).resolve().parents[1]
CHECKOUT_SOURCE_ROOT = REPOSITORY_ROOT / "src"
ROADMAP = REPOSITORY_ROOT / "docs/roadmap.md"
DECISION_ROOT = REPOSITORY_ROOT / (
    "reference_corpus/contracts/fault-instance/decisions/"
    "s10-deferred-subject-disposition-readiness"
)
DECISION_JSON = DECISION_ROOT / "decision.json"
DECISION_MD = DECISION_ROOT / "decision.md"

# The accumulated S1.P06 product surface S1.P06.S11 must cover. Declared here so
# the oracle compares the artifact against an independent statement rather than
# against the artifact's own copy of itself.
P06_MODULES = (
    "faultatlas.domain.fault",
    "faultatlas.domain.fault_source_relationship",
    "faultatlas.domain.fault_repair",
    "faultatlas.domain.fault_test",
    "faultatlas.domain.fault_interpretation",
    "faultatlas.domain.fault_instance",
    "faultatlas.domain.fault_evidence_link",
)
P06_SYMBOL_COUNT = 30
PRODUCTION_MODULE_COUNT = 20

SUBJECT_ID = "gap:s05-known:case-relationship-vocabulary-provisional"
HISTORICAL_WORDING = "case relationship vocabulary provisional"
CARRIED_FORWARD_WORDING = "universal relationship vocabulary"

EFFECTIVE_REQUIREMENTS = (
    "own_the_bounded_domain_relationship_vocabulary_needed_by_FaultInstance",
    "consume_the_bounded_S1_P05_history_facts_without_redefining_them",
)
EFFECTIVE_PROHIBITIONS = (
    "own_a_generic_git_ancestry_or_reachability_graph",
    "read_the_bounded_S1_P05_surface_as_a_complete_development_history",
    "upgrade_the_LEVEL_1_evidence_association_implicitly",
)
SUPERSEDED_HANDOFF = "handoff:s1-p05-s08:s1-p06"
EFFECTIVE_HANDOFF = "handoff:s1-p05-s08-c01:s1-p06"
# The requirement wording the superseded raw S1.P05.S08 handoff carried. It must
# never be treated as the effective obligation.
SUPERSEDED_REQUIREMENT = "own_fault_instance_consuming_relationship_and_event_semantics"

# Words that would turn this disposition into a claim of a universal relation
# model. Naming one is allowed only while denying it, which is what the absence
# check below requires clause by clause.
FORBIDDEN_GENERALIZATIONS = (
    "RelationKind",
    "ancestry",
    "reachability",
    "relationship graph",
    "relationship ontology",
    "relationship registry",
    "universal relationship",
)
# Words that assert a governance override. A clause naming one must deny it,
# in the same shape the generalization screen uses.
OVERRIDE_WORDS = (
    "bypass",
    "override",
    "overridden",
    "skipped",
    "not satisfied",
    "was not enforced",
)
# One clause grammar, read by both screens below. A second copy would drift,
# which is the failure this repository already records for its negation terms.
# Sentence boundaries only, because a bare "." also ends `S1.P06` and cutting
# there would sever the "no" that denies the clause; and coordination, because
# "No warning was emitted, and an ontology exists" is two claims, not one.
CLAUSE_BOUNDARY = r"[;\n]|\.\s|\.$|,\s+and\s+|,\s+but\s+|\s+but\s+"

# A clause naming a forbidden term must carry one of these to be a denial.
DENIAL_TOKENS = (
    "no ",
    "not ",
    "never",
    "none",
    "nor ",
    "neither",
    "cannot",
    "without",
    "refuses",
    "excluded",
)


def _raw() -> bytes:
    return DECISION_JSON.read_bytes()


def _document() -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(_raw().decode("utf-8")))


def _digest() -> str:
    return hashlib.sha256(_raw()).hexdigest()


def _live_exports() -> dict[str, list[str]]:
    return {name: list(importlib.import_module(name).__all__) for name in P06_MODULES}


def _live_production_modules() -> list[str]:
    return sorted(
        path.relative_to(CHECKOUT_SOURCE_ROOT).as_posix()
        for path in CHECKOUT_SOURCE_ROOT.rglob("*.py")
    )


# --- the oracles the direct mutations below must trip ------------------------


def _assert_single_subject_addressed(document: dict[str, Any]) -> None:
    register = cast(dict[str, Any], document["inherited_subject_register"])
    items = cast(list[dict[str, Any]], register["items"])

    assert register["count"] == 1
    assert len(items) == 1
    assert register["dispositioned_exactly_once"] == 1
    assert register["addressed_count"] == 1
    assert register["carried_forward_count"] == 0
    assert register["split_count"] == 0

    (item,) = items
    assert item["disposition"] == "addressed"
    assert item["subject"] == HISTORICAL_WORDING
    assert item["source"]["subject_id"] == SUBJECT_ID
    # An addressed subject has no remainder, so it carries no state and no owner.
    assert "carried_forward" not in item
    assert "current_state" not in item
    assert "immediate_owner" not in item
    assert "preserved_long_term_owner" not in item
    assert "remainder_subject" not in item
    assert register["state_totals"] == {}
    assert register["immediate_owner_totals"] == {}
    assert register["long_term_owner_totals"] == {}


def _every_string(node: object, path: str = "") -> list[tuple[str, str]]:
    """Every string in the document, with the pointer it sits at.

    Enumerating regions is the losing shape: whichever field is left off the
    list is where a false claim can be written. So the screen below reads the
    whole document instead.
    """
    found: list[tuple[str, str]] = []
    if isinstance(node, str):
        found.append((path, node))
    elif isinstance(node, dict):
        for key, value in cast(dict[str, Any], node).items():
            found.extend(_every_string(value, f"{path}/{key}"))
    elif isinstance(node, list):
        for index, value in enumerate(cast(list[Any], node)):
            found.extend(_every_string(value, f"{path}/{index}"))
    return found


# A prohibition's own statement, and the identifiers built from it, are the
# NAME of the forbidden thing. They are denied by the record's `state` rather
# than by their wording, so they are the one exemption from the screen below.
_PROHIBITION_NAME_KEYS = ("statement", "prohibition_id")

# The one field whose whole content is the predecessor's carried-forward
# wording. It is exempt only while it holds exactly that wording, so it cannot
# be widened into a claim.
_QUOTED_WORDING_KEYS = ("carried_forward_wording",)


def _mask_the_quoted_wording(text: str) -> str:
    """Mask the predecessor's carried-forward wording only where it is quoted.

    The Slice's subject is literally named "universal relationship vocabulary",
    so that phrase has to be sayable. Masking every occurrence would also erase
    an affirmative claim written in the same words, so only occurrences inside
    quotation marks -- the form in which the predecessor is quoted -- are
    masked, and a bare use is left for the screen to judge.
    """
    for quoted in (
        f'"{CARRIED_FORWARD_WORDING}"',
        f"`{CARRIED_FORWARD_WORDING}`",
    ):
        text = text.replace(quoted, "<quoted predecessor wording>")
    return text


def _assert_names_no_generalization_it_does_not_deny(document: dict[str, Any]) -> None:
    """Naming a universal relation model is allowed only while denying it.

    Asserting that the denial sentences are present cannot catch an affirmative
    claim written beside them, so this states the absence as a property: split
    the artifact's generalization-bearing text into clauses, and require every
    clause that names a forbidden generalization to carry a denial. The one
    sanctioned use is the predecessor's own carried-forward wording, which is
    quoted rather than claimed, so it is masked before the check.
    """
    for pointer, text in _every_string(document):
        key = pointer.rsplit("/", 1)[-1]
        if (
            pointer.startswith("/prohibition_accounting/")
            and key in _PROHIBITION_NAME_KEYS
        ):
            continue
        if key in _QUOTED_WORDING_KEYS:
            assert text == CARRIED_FORWARD_WORDING, (pointer, text)
            continue
        masked = _mask_the_quoted_wording(text)
        for clause in re.split(CLAUSE_BOUNDARY, masked.replace("_", " ")):
            lowered = clause.strip().lower()
            named = [
                word for word in FORBIDDEN_GENERALIZATIONS if word.lower() in lowered
            ]
            if not named:
                continue
            assert any(token in lowered for token in DENIAL_TOKENS), (
                pointer,
                named,
                clause,
            )


def _assert_no_generic_relationship_claim(document: dict[str, Any]) -> None:
    """The bounded vocabulary is addressed; a universal one is never claimed."""
    non_generalizations = cast(dict[str, Any], document["non_generalizations"])
    published = cast(list[str], non_generalizations["items"])
    joined = " ".join(published).lower()

    assert non_generalizations["count"] == len(published)
    for phrase in (
        "no universal relationship ontology",
        "no generic relationship, edge, graph, or relationkind type exists",
        "no repository evolution graph semantics exist",
        "no ancestry, reachability, merge-base, or branch-containment semantics exist",
        "no cross-case relationship generalization exists",
    ):
        assert phrase in joined, phrase

    requirement = cast(
        list[dict[str, Any]], document["requirement_accounting"]["items"]
    )
    assert requirement[0]["generic_relation_schema_published"] is False

    item = cast(list[dict[str, Any]], document["inherited_subject_register"]["items"])[
        0
    ]
    assert item["effective_scope"] == EFFECTIVE_REQUIREMENTS[0]
    # The addressed portion is the bounded vocabulary, named endpoint by endpoint.
    assert len(item["addressed_by"]) >= 5
    rationale = cast(str, item["rationale"])
    assert "bounded domain relationship vocabulary" in rationale
    # The rationale must say which generic constructs were not needed, by name.
    for named in ("Relationship, Edge, Graph, RelationKind", "registry"):
        assert named in rationale, named

    _assert_names_no_generalization_it_does_not_deny(document)


def _assert_symbol_inventory_complete(
    document: dict[str, Any], live: dict[str, list[str]]
) -> None:
    inventory = cast(dict[str, Any], document["product_inventory"])
    recorded = cast(list[dict[str, Any]], inventory["symbols"])

    by_module: dict[str, list[str]] = {}
    for entry in recorded:
        by_module.setdefault(cast(str, entry["module"]), []).append(
            cast(str, entry["symbol"])
        )

    assert inventory["owned_symbol_count"] == P06_SYMBOL_COUNT
    assert len(recorded) == P06_SYMBOL_COUNT
    assert by_module == live

    names = [cast(str, entry["symbol"]) for entry in recorded]
    assert len(set(names)) == len(names)
    assert inventory["duplicate_symbols"] == 0


def _assert_self_owned_open_zero(document: dict[str, Any]) -> None:
    assert document["inherited_subject_register"]["self_owned_open"] == 0
    assert document["assurance"]["self_owned_open"] == 0


def _assert_publication_governance_matches_the_provider_record(
    document: dict[str, Any],
) -> None:
    """What the provider's ruleset evaluation recorded, in both directions.

    The failure mode this guards runs both ways. A real bypass must never be
    laundered into compliance, and a compliant publication must never be sealed
    as a violation that did not happen. So the recorded characterization is
    pinned to the rule-suite result it cites, and each is asserted to be
    consistent with the other rather than merely present.
    """
    governance = cast(dict[str, Any], document["publication_governance"])
    publications = cast(list[dict[str, Any]], governance["publications"])

    assert governance["count"] == len(publications) == 1
    assert governance["unresolved_exceptions"] == 0
    (record,) = publications
    assert record["slice"] == "S1.P06.S09"
    assert record["pull_request"] == 83
    assert record["reviewed_tree_equals_squash_tree"] is True
    assert record["must_be_preserved_for_s12_closure"] is True

    # The characterization and the cited evaluation must agree.
    assert record["ruleset_result"] == "pass"
    assert record["ruleset_condition_satisfied"] is True
    assert record["bypass_exercised"] is False
    assert record["bypass_records_in_period"] == 0
    assert record["bypass_actors_configured"] == 0
    assert record["characterization"] == "compliant publication"

    # The administrator flag is recorded rather than hidden, together with the
    # reason it changed nothing.
    assert record["administrator_flag_passed"] is True
    statement = cast(str, record["statement"])
    assert "administrator flag" in statement
    assert "no bypass actor" in statement
    assert "evaluated pass" in statement

    denied = cast(list[str], record["explicitly_not"])
    assert "an administrator bypass occurred" in denied
    assert "the ruleset was overridden" in denied
    assert "a required condition was skipped" in denied

    # The verdict must publish what it does and does not rest on. It is
    # analysis of an external record, not a retained observation, so it may not
    # present itself as offline-replayable or as settled for S1.P06.S12.
    status = cast(dict[str, Any], governance["evidential_status"])
    assert status["provider_records_retained"] is False
    assert status["replayable_offline"] is False
    assert status["s12_must_reverify_before_relying_on_it"] is True
    assert status["observed_at"]
    assert status["cited_by"] == "stable_provider_rule_suite_identifiers"
    note = cast(str, status["note"]).lower()
    assert "not offline-replayable" in note
    assert "model-generated analysis is not verified fact" in note

    # A record characterizing this publication as compliant may not assert a
    # bypass anywhere in the block, including in the note beside it. Screening
    # for three spellings is the wrong shape, so this reads every string in the
    # whole governance block and requires any clause naming an override to deny
    # it, exactly as the generalization screen does.
    for pointer, text in _every_string(governance, "/publication_governance"):
        if pointer.rsplit("/", 1)[-1] == "explicitly_not":
            continue
        if "/explicitly_not/" in pointer:
            continue
        for clause in re.split(CLAUSE_BOUNDARY, text.replace("_", " ")):
            lowered = clause.strip().lower()
            named = [word for word in OVERRIDE_WORDS if word in lowered]
            if not named:
                continue
            assert any(token in lowered for token in DENIAL_TOKENS), (
                pointer,
                named,
                clause,
            )


def _assert_s10_sealed_s11_as_eligible_to_begin(document: dict[str, Any]) -> None:
    """What the sealed decision recorded, read as history rather than as state.

    `S1.P06.S11` has since been published, so the live tree no longer answers
    "has S11 begun". The sealed record still says what S1.P06.S10 found when it
    was sealed, and that statement stays historically correct: the decision is
    not edited and this oracle no longer reads the working tree to confirm it.
    """
    readiness = cast(dict[str, Any], document["readiness"])

    assert readiness["s11_contract_corpus"] == "eligible_to_begin"
    assert readiness["s11_implementation_state"] == "not_started"
    assert readiness["next_slice"] == "S1.P06.S11"
    assert readiness["unsatisfied_prerequisite_count"] == 0

    prerequisites = cast(list[dict[str, Any]], readiness["prerequisites"])
    assert readiness["prerequisite_count"] == len(prerequisites)
    assert all(entry["status"] == "satisfied" for entry in prerequisites)


# --- JSON is the semantic authority ------------------------------------------


def test_the_decision_directory_carries_exactly_the_two_published_files() -> None:
    assert DECISION_JSON.is_file()
    assert DECISION_MD.is_file()
    assert sorted(path.name for path in DECISION_ROOT.iterdir()) == [
        "decision.json",
        "decision.md",
    ]


def test_the_json_declares_itself_the_sole_semantic_authority() -> None:
    document = _document()
    fmt = cast(dict[str, Any], document["format"])

    assert fmt["primary_authority"] == (
        "decision.json_is_the_sole_durable_semantic_authority_and_decision.md_is_derived"
    )
    assert fmt["production_persistence"] is False
    assert fmt["public_contract"] is False
    assert fmt["status"] == "sealed_complete"
    assert fmt["version"] == "1"
    assert "not_a_production_schema" in fmt["non_production_schema_warning"]


def test_the_json_is_canonical_and_deterministic() -> None:
    raw = _raw()
    document = _document()

    assert raw.endswith(b"\n")
    assert not raw.endswith(b"\n\n")
    assert b"\r" not in raw
    assert not raw.startswith(b"\xef\xbb\xbf")
    assert raw.decode("utf-8")

    rendered = (
        json.dumps(
            document, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        + b"\n"
    )
    assert rendered == raw
    assert json.dumps(document, sort_keys=True) == json.dumps(
        json.loads(raw.decode("utf-8")), sort_keys=True
    )

    canonicalization = cast(dict[str, Any], document["format"]["canonicalization"])
    assert canonicalization["keys"] == "sorted"
    assert canonicalization["whitespace"] == "compact"
    assert canonicalization["line_endings"] == "LF_only"
    assert canonicalization["exactly_one_trailing_lf"] is True
    assert canonicalization["floats_and_NaN_permitted"] is False


def test_the_json_carries_no_float_and_no_nan() -> None:
    def walk(node: object) -> None:
        if isinstance(node, float):
            raise AssertionError(f"float in decision.json: {node!r}")
        if isinstance(node, dict):
            for value in cast(dict[str, object], node).values():
                walk(value)
        elif isinstance(node, list):
            for value in cast(list[object], node):
                walk(value)

    walk(_document())

    # A JSON parser is the authority on the literals, not a substring scan: the
    # artifact legitimately names "NaN" inside its own canonicalization keys.
    def refuse(token: str) -> object:
        raise AssertionError(f"non-finite literal in decision.json: {token}")

    json.loads(_raw().decode("utf-8"), parse_constant=refuse)
    assert json.loads(_raw().decode("utf-8"), parse_float=refuse) == _document()


def test_the_markdown_is_a_deterministic_projection_of_the_json() -> None:
    """The Markdown is derived, so it is reproduced here rather than trusted."""
    assert _render(_document(), _digest()) == DECISION_MD.read_text(encoding="utf-8")


def test_the_markdown_names_the_exact_json_digest() -> None:
    assert _digest() in DECISION_MD.read_text(encoding="utf-8")


# --- the effective inherited authority ---------------------------------------


def test_the_effective_authority_is_s08_plus_c01_plus_the_phase_closure() -> None:
    """Raw `S1.P05.S08` alone is not the authority and is not read as one."""
    authority = cast(dict[str, Any], _document()["effective_inherited_authority"])
    authorities = cast(list[dict[str, Any]], authority["authorities"])

    assert authority["count"] == 3
    assert [entry["slice"] for entry in authorities] == [
        "S1.P05.S08",
        "S1.P05.S08.C01",
        "S1.P05.S10",
    ]
    assert authority["effective_handoff_id"] == EFFECTIVE_HANDOFF
    assert authority["superseded_handoff_id"] == SUPERSEDED_HANDOFF
    assert authority["received_subject_count"] == 1
    assert authority["requirement_count"] == 2
    assert authority["prohibition_count"] == 3


def test_each_cited_authority_matches_its_published_bytes() -> None:
    document = _document()
    locks = cast(list[dict[str, Any]], document["source_locks"]["cited_artifacts"])

    assert document["source_locks"]["count"] == 3
    assert document["source_locks"]["immutable"] is True
    for entry in locks:
        path = REPOSITORY_ROOT / cast(str, entry["path"])
        assert path.is_file(), entry["path"]
        raw = path.read_bytes()
        assert hashlib.sha256(raw).hexdigest() == entry["sha256"], entry["path"]
        assert len(raw) == entry["byte_length"], entry["path"]
        assert entry["mode"] == "100644"

    cited = {cast(str, entry["path"]) for entry in locks}
    quoted = {
        cast(str, entry["path"])
        for entry in cast(
            list[dict[str, Any]],
            document["effective_inherited_authority"]["authorities"],
        )
    }
    assert cited == quoted


def test_the_superseded_owner_topology_is_not_treated_as_effective() -> None:
    """The corrected handoff supersedes the raw one; only the former is used."""
    document = _document()
    authority = cast(dict[str, Any], document["effective_inherited_authority"])
    note = cast(str, authority["note"])

    assert SUPERSEDED_REQUIREMENT in note
    assert "superseded" in note
    assert "must not be read alone" in note

    # The superseded requirement is quoted as history and never accounted as one
    # of the effective obligations.
    accounted = {
        cast(str, entry["statement"])
        for entry in cast(
            list[dict[str, Any]], document["requirement_accounting"]["items"]
        )
    }
    assert SUPERSEDED_REQUIREMENT not in accounted
    assert accounted == set(EFFECTIVE_REQUIREMENTS)

    # The raw handoff named six received subjects; the effective one names one.
    assert authority["received_subject_count"] == 1


def test_the_effective_authority_matches_the_published_phase_closure() -> None:
    """The artifact is checked against the predecessor, not against itself."""
    closure = json.loads(
        (
            REPOSITORY_ROOT / "reference_corpus/contracts/development-history/closures/"
            "s1-p05-phase-closure/closure.json"
        ).read_text(encoding="utf-8")
    )
    handoff = cast(dict[str, Any], closure["p06_handoff"])

    assert handoff["received_subject_count"] == 1
    assert handoff["received_subjects"] == [CARRIED_FORWARD_WORDING]
    assert handoff["source_handoff_id"] == EFFECTIVE_HANDOFF
    assert (
        tuple(
            cast(str, entry["statement"])
            for entry in cast(list[dict[str, Any]], handoff["requirements"])
        )
        == EFFECTIVE_REQUIREMENTS
    )
    assert tuple(cast(list[str], handoff["prohibited"])) == EFFECTIVE_PROHIBITIONS

    register = cast(dict[str, Any], closure["deferred_register"])
    owned = [
        entry
        for entry in cast(list[dict[str, Any]], register["items"])
        if entry["immediate_owner"] == "S1.P06"
    ]
    assert len(owned) == 1
    (inherited,) = owned
    assert inherited["subject_id"] == SUBJECT_ID
    assert inherited["subject"] == HISTORICAL_WORDING
    assert inherited["remainder_subject"] == CARRIED_FORWARD_WORDING


# --- the one inherited subject and its disposition ---------------------------


def test_exactly_one_inherited_subject_is_addressed() -> None:
    _assert_single_subject_addressed(_document())


def test_the_addressed_subject_quotes_both_predecessor_wordings() -> None:
    item = cast(
        list[dict[str, Any]], _document()["inherited_subject_register"]["items"]
    )[0]
    source = cast(dict[str, Any], item["source"])

    assert source["source_wording"] == HISTORICAL_WORDING
    assert source["carried_forward_wording"] == CARRIED_FORWARD_WORDING
    assert source["effective_authority"] == "S1.P05.S08.C01"
    assert source["source_artifact"] == "S1.P05_phase_closure"
    assert source["json_pointer"] == "/p06_handoff"


def test_no_generic_relationship_model_is_claimed() -> None:
    _assert_no_generic_relationship_claim(_document())


def test_the_addressed_subject_leaves_no_p06_owned_remainder() -> None:
    _assert_self_owned_open_zero(_document())
    register = cast(dict[str, Any], _document()["inherited_subject_register"])
    assert register["carried_forward_count"] == 0
    assert register["self_introduced_count"] == 0
    assert register["owner_completeness"] is True


# --- requirement and prohibition accounting ----------------------------------


def test_exactly_two_effective_requirements_are_satisfied() -> None:
    accounting = cast(dict[str, Any], _document()["requirement_accounting"])
    items = cast(list[dict[str, Any]], accounting["items"])

    assert accounting["count"] == 2
    assert len(items) == 2
    assert accounting["satisfied_count"] == 2
    assert accounting["unsatisfied_count"] == 0
    assert tuple(cast(str, entry["statement"]) for entry in items) == (
        EFFECTIVE_REQUIREMENTS
    )
    for entry in items:
        assert entry["status"] == "satisfied"
        assert entry["requirement_id"].startswith("requirement:s1-p05-s08-c01:s1-p06:")


def test_requirement_a_evidence_names_live_published_relation_symbols() -> None:
    """Every cited relation must actually be exported by the cited module."""
    items = cast(list[dict[str, Any]], _document()["requirement_accounting"]["items"])
    evidence = cast(list[dict[str, Any]], items[0]["evidence"])
    live = _live_exports()

    assert len(evidence) == 8
    cited_slices = {cast(str, entry["slice"]) for entry in evidence}
    assert cited_slices == {
        "S1.P06.S04",
        "S1.P06.S05",
        "S1.P06.S06",
        "S1.P06.S08",
        "S1.P06.S09",
    }
    for entry in evidence:
        module = cast(str, entry["module"])
        symbol = cast(str, entry["symbol"])
        assert module in live, module
        assert symbol in live[module], (module, symbol)
        assert entry["endpoints"]


def test_requirement_b_evidence_names_the_six_admitted_history_facts() -> None:
    import typing as _typing

    from faultatlas.domain.fault_source_relationship import (
        FaultReportHistoryFactAssociation,
    )

    admitted = sorted(
        _typing.get_args(member)[0].__name__
        for member in _typing.get_args(
            FaultReportHistoryFactAssociation.model_fields["history_fact"].annotation
        )
    )
    items = cast(list[dict[str, Any]], _document()["requirement_accounting"]["items"])
    recorded = cast(list[str], items[1]["admitted_S1_P05_history_facts"])

    assert len(admitted) == 6
    assert recorded == admitted
    assert items[1]["predecessor_production_bytes_redefined"] is False


def test_the_predecessor_p05_surface_is_unchanged_by_p06() -> None:
    """P06 consumed the P05 facts; it did not redefine them."""
    closure = json.loads(
        (
            REPOSITORY_ROOT / "reference_corpus/contracts/development-history/closures/"
            "s1-p05-phase-closure/closure.json"
        ).read_text(encoding="utf-8")
    )
    published: dict[str, list[str]] = {}
    for entry in cast(
        list[dict[str, Any]], closure["implementation_inventory"]["owned_symbols"]
    ):
        published.setdefault(cast(str, entry["module"]), []).append(
            cast(str, entry["symbol"])
        )
    published = {module: sorted(names) for module, names in published.items()}

    live = {
        module: sorted(importlib.import_module(module).__all__) for module in published
    }
    assert live == published

    items = cast(list[dict[str, Any]], _document()["requirement_accounting"]["items"])
    surface = cast(dict[str, Any], items[1]["predecessor_surface"])
    assert surface["unchanged_by_P06"] is True
    assert sorted(cast(list[str], surface["modules"])) == sorted(published)
    assert {
        module: sorted(names)
        for module, names in cast(
            dict[str, list[str]], surface["published_symbols"]
        ).items()
    } == published


def test_exactly_three_effective_prohibitions_are_preserved() -> None:
    accounting = cast(dict[str, Any], _document()["prohibition_accounting"])
    items = cast(list[dict[str, Any]], accounting["items"])

    assert accounting["count"] == 3
    assert len(items) == 3
    assert accounting["preserved_count"] == 3
    assert accounting["violated_count"] == 0
    assert tuple(cast(str, entry["statement"]) for entry in items) == (
        EFFECTIVE_PROHIBITIONS
    )
    for entry in items:
        assert entry["state"] == "preserved"
        assert entry["evidence"]
        assert entry["prohibition_id"].startswith("prohibition:s1-p05-s08-c01:s1-p06:")


def test_no_p06_module_publishes_a_graph_or_reachability_symbol() -> None:
    """The first prohibition is checked against the live surface, not the text."""
    for names in _live_exports().values():
        for symbol in names:
            lowered = symbol.lower()
            for forbidden in (
                "ancestry",
                "reachab",
                "mergebase",
                "merge_base",
                "graph",
                "relationkind",
                "edge",
            ):
                assert forbidden not in lowered, symbol


# --- the P06 product surface S1.P06.S11 must cover ---------------------------


def test_exactly_seven_p06_modules_are_inventoried() -> None:
    inventory = cast(dict[str, Any], _document()["product_inventory"])
    modules = cast(list[dict[str, Any]], inventory["modules"])

    assert inventory["owned_module_count"] == 7
    assert len(modules) == 7
    assert tuple(cast(str, entry["module"]) for entry in modules) == P06_MODULES
    for entry in modules:
        path = REPOSITORY_ROOT / cast(str, entry["path"])
        assert path.is_file(), entry["path"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == entry["sha256"]
        assert entry["publishing_slices"]


def test_exactly_thirty_live_symbols_are_inventoried() -> None:
    _assert_symbol_inventory_complete(_document(), _live_exports())


def test_the_inventory_is_derived_from_live_module_exports() -> None:
    """Each recorded symbol must be reachable on the module that claims it."""
    inventory = cast(dict[str, Any], _document()["product_inventory"])
    assert inventory["derived_from"] == "live_module_dunder_all"

    total = 0
    for entry in cast(list[dict[str, Any]], inventory["symbols"]):
        module = importlib.import_module(cast(str, entry["module"]))
        symbol = cast(str, entry["symbol"])
        assert symbol in module.__all__, entry
        assert hasattr(module, symbol), entry
        total += 1
    assert total == P06_SYMBOL_COUNT


def test_the_per_module_counts_sum_to_thirty() -> None:
    modules = cast(list[dict[str, Any]], _document()["product_inventory"]["modules"])
    counts = {
        cast(str, entry["module"]): cast(int, entry["exported_symbol_count"])
        for entry in modules
    }

    assert counts == {name: len(names) for name, names in _live_exports().items()}
    assert sum(counts.values()) == P06_SYMBOL_COUNT
    assert counts == {
        "faultatlas.domain.fault": 8,
        "faultatlas.domain.fault_source_relationship": 2,
        "faultatlas.domain.fault_repair": 4,
        "faultatlas.domain.fault_test": 8,
        "faultatlas.domain.fault_interpretation": 6,
        "faultatlas.domain.fault_instance": 1,
        "faultatlas.domain.fault_evidence_link": 1,
    }


def test_no_p06_symbol_is_exported_twice_or_re_exported_elsewhere() -> None:
    """No alias and no package-level export aggregator may stand."""
    live = _live_exports()
    names = [symbol for exported in live.values() for symbol in exported]
    assert len(set(names)) == len(names) == P06_SYMBOL_COUNT

    owned = set(names)
    for relative in _live_production_modules():
        module_name = relative.removesuffix(".py").replace("/", ".")
        module_name = module_name.removesuffix(".__init__")
        if module_name in P06_MODULES:
            continue
        module = importlib.import_module(module_name)
        exported = set(getattr(module, "__all__", ()))
        assert not exported & owned, (module_name, sorted(exported & owned))


def test_no_p06_product_module_is_left_unaccounted() -> None:
    """Every fault-domain production module is inventoried, not just seven."""
    recorded = {
        cast(str, entry["module"])
        for entry in cast(
            list[dict[str, Any]], _document()["product_inventory"]["modules"]
        )
    }
    live_fault_modules = {
        relative.removesuffix(".py").replace("/", ".")
        for relative in _live_production_modules()
        if pathlib.PurePosixPath(relative).name.startswith("fault")
    }

    assert live_fault_modules == recorded == set(P06_MODULES)


def test_the_package_still_carries_twenty_production_modules() -> None:
    inventory = cast(dict[str, Any], _document()["product_inventory"])
    live = _live_production_modules()

    assert len(live) == PRODUCTION_MODULE_COUNT
    assert inventory["production_module_count"] == PRODUCTION_MODULE_COUNT
    assert cast(list[str], inventory["production_modules"]) == live
    assert (
        _document()["assurance"]["governance_only"]["production_python_source_count"]
        == PRODUCTION_MODULE_COUNT
    )


def test_this_slice_changes_no_production_source() -> None:
    document = _document()
    governance = cast(dict[str, Any], document["assurance"]["governance_only"])

    assert governance["no_production_source_changed"] is True
    assert governance["no_production_module_added"] is True
    assert governance["no_product_semantics_added"] is True
    assert governance["no_dependency_or_lockfile_change"] is True
    assert document["phase_identity"]["production_change"] is False


# --- S1.P06.S11 readiness ----------------------------------------------------


def test_s10_sealed_s11_as_eligible_to_begin() -> None:
    _assert_s10_sealed_s11_as_eligible_to_begin(_document())


def test_the_s11_contract_corpus_now_stands_where_s10_authorized_it() -> None:
    """S1.P06.S11 exercised the readiness this decision sealed.

    The sealed bytes are untouched, so the two statements live side by side: the
    decision records that no corpus existed when it was written, and the tree
    now carries the corpus that record authorized. The oracle reads the live
    layout rather than asserting an absence the Phase has moved past.
    """
    root = REPOSITORY_ROOT / "reference_corpus/contracts/fault-instance"
    assert root.is_dir()
    assert sorted(path.name for path in root.iterdir()) == ["decisions", "v1"]

    corpus = root / "v1"
    assert sorted(path.name for path in corpus.iterdir()) == [
        "contract.md",
        "invalid-vectors.json",
        "invalid-vectors.sha256",
        "manifest.json",
        "manifest.sha256",
        "replay-vectors.json",
        "replay-vectors.sha256",
        "valid-vectors.json",
        "valid-vectors.sha256",
    ]
    # The corpus cites this decision as its entry authority by exact digest, so
    # the two artifacts cannot drift apart silently.
    manifest = json.loads((corpus / "manifest.json").read_text("utf-8"))
    authority = cast(dict[str, Any], manifest["entry_authority"])
    assert authority["slice"] == "S1.P06.S10"
    assert (
        REPOSITORY_ROOT / cast(str, authority["path"])
    ).resolve() == DECISION_JSON.resolve()
    assert authority["sha256"] == hashlib.sha256(DECISION_JSON.read_bytes()).hexdigest()


def test_the_readiness_prerequisites_are_the_declared_twelve() -> None:
    readiness = cast(dict[str, Any], _document()["readiness"])
    prerequisites = cast(list[dict[str, Any]], readiness["prerequisites"])

    assert readiness["prerequisite_count"] == 12
    assert len(prerequisites) == 12
    identifiers = [cast(str, entry["prerequisite_id"]) for entry in prerequisites]
    assert identifiers == [f"s11-entry:{index:02d}" for index in range(1, 13)]
    assert len(set(identifiers)) == 12


def test_governance_readiness_is_recorded_separately_from_semantic_readiness() -> None:
    """Publication governance must not be flattened into corpus readiness.

    Whatever the publication state turns out to be, it is recorded beside the
    semantic prerequisites rather than inside them, so a governance question
    can never silently decide whether the corpus may begin.
    """
    readiness = cast(dict[str, Any], _document()["readiness"])
    governance = cast(dict[str, Any], readiness["governance_readiness"])

    assert governance["s09_publication_governance_exception"] == "absent"
    assert governance["s09_publication_state"] == "compliant"
    assert governance["blocks_s11_semantic_corpus_construction"] is False
    assert governance["must_be_preserved_for_s12_closure"] is True
    assert governance["separate_from_semantic_readiness"] is True

    # No semantic prerequisite mentions publication governance at all, so the
    # twelve are decided on semantics alone.
    subjects = " ".join(
        cast(str, entry["subject"])
        for entry in cast(list[dict[str, Any]], readiness["prerequisites"])
    ).lower()
    for word in ("bypass", "override", "admin", "ruleset", "approval"):
        assert word not in subjects, word


def test_the_s09_publication_matches_the_provider_ruleset_record() -> None:
    _assert_publication_governance_matches_the_provider_record(_document())


def test_s10_does_not_decide_the_s12_closure_question() -> None:
    governance = cast(dict[str, Any], _document()["publication_governance"])

    assert governance["s12_closure_decision_owner"] == "S1.P06.S12"
    note = cast(str, governance["note"]).lower()
    assert "does not decide" in note
    assert "s1.p06.s12 owns that decision" in note


# --- the S08 performance candidate is not canonical product state ------------


def test_the_s08_performance_candidate_is_not_part_of_this_decision() -> None:
    """PR #82 is an independent optimization candidate, not S10 product state.

    The canonical `S1.P06` product surface is what stands on `main`. The
    recorded aggregate digest is the merged one, and it is compared here
    against the candidate branch's own version of the same file, so adopting
    that implementation would change the digest and fail this oracle rather
    than pass unnoticed.
    """
    import subprocess

    document = _document()
    recorded = {
        cast(str, entry["module"]): cast(str, entry["sha256"])
        for entry in cast(
            list[dict[str, Any]], document["product_inventory"]["modules"]
        )
    }
    aggregate = REPOSITORY_ROOT / "src/faultatlas/domain/fault_instance.py"
    merged = hashlib.sha256(aggregate.read_bytes()).hexdigest()
    assert recorded["faultatlas.domain.fault_instance"] == merged

    candidate = subprocess.run(
        ["git", "show", "dad36f8:src/faultatlas/domain/fault_instance.py"],
        cwd=REPOSITORY_ROOT,
        check=False,
        capture_output=True,
    )
    if candidate.returncode == 0:
        assert hashlib.sha256(candidate.stdout).hexdigest() != merged

    # No governance record names the optimization candidate.
    named = {
        str(entry.get("pull_request"))
        for entry in cast(
            list[dict[str, Any]], document["publication_governance"]["publications"]
        )
    }
    assert "82" not in named
    assert named == {"83"}


# --- direct semantic mutations -----------------------------------------------


def test_a_carried_forward_disposition_fails_the_subject_oracle() -> None:
    """Mutation 1: the addressed subject is rewritten as carried forward."""
    mutated = _document()
    register = cast(dict[str, Any], mutated["inherited_subject_register"])
    item = cast(list[dict[str, Any]], register["items"])[0]
    item["disposition"] = "carried_forward"
    item["current_state"] = "unsupported_current_scope"
    item["immediate_owner"] = "S5"
    register["addressed_count"] = 0
    register["carried_forward_count"] = 1

    with pytest.raises(AssertionError):
        _assert_single_subject_addressed(mutated)


def test_claiming_a_generic_relationship_graph_fails_its_oracle() -> None:
    """Mutation 2: a universal relation model is claimed as addressed."""
    mutated = _document()
    non_generalizations = cast(dict[str, Any], mutated["non_generalizations"])
    items = cast(list[str], non_generalizations["items"])
    items[:] = [
        entry
        for entry in items
        if "no repository evolution graph semantics exist" not in entry
    ]
    items.append("a universal relationship graph is published and addressed")
    non_generalizations["count"] = len(items)
    cast(list[dict[str, Any]], mutated["requirement_accounting"]["items"])[0][
        "generic_relation_schema_published"
    ] = True

    with pytest.raises(AssertionError):
        _assert_no_generic_relationship_claim(mutated)


def test_a_missing_symbol_fails_the_inventory_oracle() -> None:
    """Mutation 3: one of the thirty symbols drops out of the inventory."""
    mutated = _document()
    inventory = cast(dict[str, Any], mutated["product_inventory"])
    symbols = cast(list[dict[str, Any]], inventory["symbols"])
    dropped = next(
        entry for entry in symbols if entry["symbol"] == "FaultInstanceEvidenceLink"
    )
    symbols.remove(dropped)
    inventory["owned_symbol_count"] = len(symbols)

    with pytest.raises(AssertionError):
        _assert_symbol_inventory_complete(mutated, _live_exports())


def test_a_nonzero_self_owned_open_fails_its_oracle() -> None:
    """Mutation 4: an open P06-owned remainder is asserted."""
    mutated = _document()
    cast(dict[str, Any], mutated["inherited_subject_register"])["self_owned_open"] = 1

    with pytest.raises(AssertionError):
        _assert_self_owned_open_zero(mutated)


def test_recording_a_bypass_that_did_not_happen_fails_its_oracle() -> None:
    """Mutation 5: a compliant publication is restated as an override.

    Sealing a violation that the provider's record shows did not occur is the
    mirror of laundering a real one, and both are falsifications of the same
    field, so the oracle must reject this direction too.
    """
    mutated = _document()
    record = cast(
        list[dict[str, Any]], mutated["publication_governance"]["publications"]
    )[0]
    record["ruleset_condition_satisfied"] = False
    record["bypass_exercised"] = True
    record["characterization"] = "publication governance exception"
    record["merge_method"] = "squash_with_administrator_override"
    record["statement"] = (
        "The S1.P06.S09 pull request was merged with an administrator override "
        "of the main ruleset; the required approval was not satisfied, it was "
        "bypassed."
    )

    with pytest.raises(AssertionError):
        _assert_publication_governance_matches_the_provider_record(mutated)


def test_overclaiming_the_verdict_as_replayable_fails_its_oracle() -> None:
    """The evidential limits are part of the verdict, not a footnote."""
    mutated = _document()
    status = cast(
        dict[str, Any], mutated["publication_governance"]["evidential_status"]
    )
    status["replayable_offline"] = True
    status["provider_records_retained"] = True
    status["s12_must_reverify_before_relying_on_it"] = False

    with pytest.raises(AssertionError):
        _assert_publication_governance_matches_the_provider_record(mutated)


def test_laundering_a_real_bypass_into_compliance_fails_its_oracle() -> None:
    """The other direction: a recorded bypass restated as a passing ruleset."""
    mutated = _document()
    record = cast(
        list[dict[str, Any]], mutated["publication_governance"]["publications"]
    )[0]
    record["bypass_exercised"] = True
    record["bypass_records_in_period"] = 1
    record["ruleset_result"] = "bypass"

    with pytest.raises(AssertionError):
        _assert_publication_governance_matches_the_provider_record(mutated)


def test_marking_s11_implemented_fails_its_oracle() -> None:
    """Mutation 6: S11 is recorded as implemented rather than not started."""
    mutated = _document()
    readiness = cast(dict[str, Any], mutated["readiness"])
    readiness["s11_implementation_state"] = "implemented"
    readiness["s11_contract_corpus"] = "complete"

    with pytest.raises(AssertionError):
        _assert_s10_sealed_s11_as_eligible_to_begin(mutated)


# --- the roadmap transition --------------------------------------------------


def _roadmap() -> str:
    return ROADMAP.read_text(encoding="utf-8")


def _flat_roadmap() -> str:
    """Line wrapping is not part of the claim, so it is normalized away."""
    return " ".join(_roadmap().split())


def test_the_roadmap_records_the_p06_s10_transition() -> None:
    roadmap = _roadmap()
    mapping = roadmap.split("## Current-code mapping", 1)
    assert len(mapping) == 2, "roadmap must retain a current-code mapping section"
    current = mapping[1]

    assert "`S1.P06.S10` is complete" in roadmap
    assert "`S1.P06.S11` is complete" in roadmap
    assert "`S1.P06.S12` is next and not started" in roadmap
    assert "`S1.P06.S10` — Deferred disposition and readiness (complete)" in roadmap
    assert "The `S1.P06` route is provisional beyond `S1.P06.S11`." in roadmap
    assert "Production Python sources are 20." in current

    assert "`S1.P06.S10` is next and not started" not in roadmap
    assert "`S1.P06.S12` is complete" not in roadmap


def test_the_roadmap_states_the_s10_decisions() -> None:
    roadmap = _flat_roadmap()

    for statement in (
        "exactly one immediate inherited subject",
        "That subject is `addressed`",
        "no `S1.P06`-owned deferred subject remains open",
        "No universal relationship ontology",
        "seven production modules and thirty exported symbols",
        "evaluated pass on every rule",
        "no publication-governance exception stands against it",
        "wrong in the direction of non-compliance",
        "The verdict publishes its own limits",
        "must re-verify the verdict rather than consume it as settled",
        "recorded `S1.P06.S11` contract-corpus readiness as `eligible_to_begin`",
        "Both effective requirements are satisfied",
        "All three effective prohibitions are preserved",
        "not part of canonical `S1.P06` product state",
    ):
        assert statement in roadmap, statement


def test_the_roadmap_leaves_later_ownership_where_it_was() -> None:
    roadmap = _roadmap()

    assert "`S1.P06.S12` — Integration and Phase closure (next, not started)" in roadmap
    assert "`S1.P07` through `S1.P10` remain not started" in roadmap
    assert "`S1.P06` is active and incomplete" in roadmap


def test_the_roadmap_adds_no_production_module_claim() -> None:
    roadmap = _roadmap()

    assert "Production Python sources are 21." not in roadmap
    assert "production Python sources move from 20 to 21" not in roadmap


# --- packaging ---------------------------------------------------------------


EXPECTED_PRODUCTION_MODULES = [
    "faultatlas/__init__.py",
    "faultatlas/__main__.py",
    "faultatlas/cli.py",
    "faultatlas/domain/__init__.py",
    "faultatlas/domain/compatibility.py",
    "faultatlas/domain/evidence.py",
    "faultatlas/domain/fault.py",
    "faultatlas/domain/fault_evidence_link.py",
    "faultatlas/domain/fault_instance.py",
    "faultatlas/domain/fault_interpretation.py",
    "faultatlas/domain/fault_repair.py",
    "faultatlas/domain/fault_source_relationship.py",
    "faultatlas/domain/fault_test.py",
    "faultatlas/domain/history.py",
    "faultatlas/domain/history_evidence_link.py",
    "faultatlas/domain/identity.py",
    "faultatlas/domain/revision.py",
    "faultatlas/domain/snapshot.py",
    "faultatlas/domain/snapshot_evidence_link.py",
    "faultatlas/domain/source.py",
]


def test_the_checkout_carries_exactly_twenty_production_modules() -> None:
    assert _live_production_modules() == EXPECTED_PRODUCTION_MODULES
    assert len(EXPECTED_PRODUCTION_MODULES) == PRODUCTION_MODULE_COUNT


@pytest.fixture(scope="session")
def offline_distributions(
    tmp_path_factory: pytest.TempPathFactory,
) -> tuple[pathlib.Path, pathlib.Path]:
    import os
    import shutil
    import subprocess

    uv = shutil.which("uv")
    assert uv is not None, "uv must be available to build the supported distributions"

    root = tmp_path_factory.mktemp("fault-instance-decision-package")
    output = root / "distributions"
    output.mkdir()
    environment = os.environ.copy()
    environment.update(
        {
            "PYTHONDONTWRITEBYTECODE": "1",
            "UV_CACHE_DIR": str(root / "uv-cache"),
            "UV_NO_SYNC": "1",
            "UV_OFFLINE": "1",
        }
    )
    result = subprocess.run(
        [uv, "build", "--offline", "--no-create-gitignore", "--out-dir", str(output)],
        cwd=REPOSITORY_ROOT,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"offline build failed\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )
    wheels = tuple(output.glob("*.whl"))
    sdists = tuple(output.glob("*.tar.gz"))
    assert len(wheels) == 1, f"expected one wheel, found {wheels!r}"
    assert len(sdists) == 1, f"expected one sdist, found {sdists!r}"
    return wheels[0], sdists[0]


def test_the_wheel_excludes_the_new_decision_and_keeps_twenty_modules(
    offline_distributions: tuple[pathlib.Path, pathlib.Path],
) -> None:
    wheel, _ = offline_distributions
    with zipfile.ZipFile(wheel) as archive:
        names = tuple(info.filename for info in archive.infolist() if not info.is_dir())

    modules = sorted(name for name in names if name.endswith(".py"))
    assert modules == EXPECTED_PRODUCTION_MODULES
    assert len(modules) == PRODUCTION_MODULE_COUNT
    for name in names:
        assert "reference_corpus" not in name
        assert "fault-instance" not in name
        assert not name.startswith("tests/")
        assert not name.startswith("docs/")


def test_the_sdist_excludes_the_new_decision_and_keeps_twenty_modules(
    offline_distributions: tuple[pathlib.Path, pathlib.Path],
) -> None:
    _, sdist = offline_distributions
    with tarfile.open(sdist, "r:gz") as archive:
        names = tuple(member.name for member in archive.getmembers() if member.isfile())

    modules = sorted(
        name.split("/src/", 1)[1] for name in names if name.endswith(".py")
    )
    assert modules == EXPECTED_PRODUCTION_MODULES
    assert len(modules) == PRODUCTION_MODULE_COUNT
    for name in names:
        parts = pathlib.PurePosixPath(name).parts
        assert "reference_corpus" not in parts
        assert "fault-instance" not in parts
        assert "tests" not in parts
        assert "docs" not in parts


# --- the Markdown projection -------------------------------------------------
#
# `decision.md` is derived, so the projection lives here in the tests rather
# than in any production module. Nothing in `src/` reads or writes either file.


def _render(document: dict[str, Any], digest: str) -> str:
    fmt = cast(dict[str, Any], document["format"])
    identity = cast(dict[str, Any], document["phase_identity"])
    authority = cast(dict[str, Any], document["effective_inherited_authority"])
    register = cast(dict[str, Any], document["inherited_subject_register"])
    requirements = cast(dict[str, Any], document["requirement_accounting"])
    prohibitions = cast(dict[str, Any], document["prohibition_accounting"])
    inventory = cast(dict[str, Any], document["product_inventory"])
    readiness = cast(dict[str, Any], document["readiness"])
    governance = cast(dict[str, Any], document["publication_governance"])
    non_generalizations = cast(dict[str, Any], document["non_generalizations"])
    locks = cast(dict[str, Any], document["source_locks"])
    lines: list[str] = []

    def add(text: str = "") -> None:
        lines.append(text)

    add(
        f"# FaultInstance Deferred-Subject Disposition and {identity['next_slice']} Readiness"
    )
    add()
    add("## 1. Scope and Authority Warning")
    add()
    add(
        f"This internal, {fmt['calibration']} `{identity['slice']}` decision is not a "
        "production schema, class, adapter, reader, writer, migration, persistence "
        "contract, or public API. `decision.json` is the sole durable semantic "
        "authority; this Markdown is derived. The Slice is governance-only: no "
        "production Python source changed, no production module was added, and the "
        "production source count remains "
        f"{inventory['production_module_count']}."
    )
    add()
    add("## 2. Exact `decision.json` SHA-256")
    add()
    add(f"`{digest}`")
    add()
    add("## 3. Result")
    add()
    add(
        f"`{identity['phase']}` inherited exactly {register['count']} immediate deferred "
        f"subject under its effective authority. It is dispositioned exactly once, as "
        f"`{cast(list[dict[str, Any]], register['items'])[0]['disposition']}`. "
        f"{requirements['satisfied_count']} of {requirements['count']} effective "
        f"requirements are satisfied and {prohibitions['preserved_count']} of "
        f"{prohibitions['count']} effective prohibitions are preserved."
    )
    add()
    add("    self_owned_open == 0")
    add()
    add(
        "No universal relationship ontology is published, no predecessor artifact is "
        "edited, and no subject is claimed resolved that is not. "
        f"`{readiness['next_slice']}` contract-corpus readiness is "
        f"`{readiness['s11_contract_corpus']}`."
    )
    add()
    add("## 4. Effective Inherited Authority")
    add()
    add(
        f"The effective authority is the {authority['count']} artifacts below read "
        f"together. `{authority['superseded_handoff_id']}` is superseded by "
        f"`{authority['effective_handoff_id']}`."
    )
    add()
    add("| Slice | Role | Path |")
    add("| --- | --- | --- |")
    for entry in cast(list[dict[str, Any]], authority["authorities"]):
        add(f"| `{entry['slice']}` | `{entry['role']}` | `{entry['path']}` |")
    add()
    add(cast(str, authority["note"]))
    add()
    add(
        f"Received subjects: {authority['received_subject_count']}. Requirements: "
        f"{authority['requirement_count']}. Prohibitions: "
        f"{authority['prohibition_count']}."
    )
    add()
    add("## 5. The Inherited Subject and Its Disposition")
    add()
    item = cast(list[dict[str, Any]], register["items"])[0]
    source = cast(dict[str, Any], item["source"])
    add("| # | Subject | Subject ID | Disposition |")
    add("| --- | --- | --- | --- |")
    add(
        f"| 1 | {item['subject']} | `{source['subject_id']}` | "
        f"{item['disposition']} by {', '.join('`' + s + '`' for s in cast(list[str], item['addressed_by']))} |"
    )
    add()
    add(
        f"Source: `{source['path']}` at `{source['json_pointer']}`, SHA-256 "
        f'`{source["sha256"]}`. Predecessor wording: "{source["source_wording"]}". '
        f'Carried-forward wording: "{source["carried_forward_wording"]}". '
        f"Predecessor state: `{source['source_state']}`. Effective authority: "
        f"`{source['effective_authority']}`."
    )
    add()
    add(f"Effective scope: `{item['effective_scope']}`. Outcome: `{item['outcome']}`.")
    add()
    add(cast(str, item["rationale"]))
    add()
    add(
        f"An addressed subject carries no remainder, so no state and no owner is "
        f"attached: `addressed_count` is {register['addressed_count']}, "
        f"`carried_forward_count` is {register['carried_forward_count']}, "
        f"`split_count` is {register['split_count']}, and `self_owned_open` is "
        f"{register['self_owned_open']}."
    )
    add()
    add("## 6. Requirement Accounting")
    add()
    for index, entry in enumerate(
        cast(list[dict[str, Any]], requirements["items"]), start=1
    ):
        add(f"### 6.{index} `{entry['statement']}`")
        add()
        add(f"Status: `{entry['status']}`. Identifier: `{entry['requirement_id']}`.")
        add()
        if index == 1:
            add("| Slice | Module | Symbol | Endpoints |")
            add("| --- | --- | --- | --- |")
            for cited in cast(list[dict[str, Any]], entry["evidence"]):
                add(
                    f"| `{cited['slice']}` | `{cited['module']}` | "
                    f"`{cited['symbol']}` | {cited['endpoints']} |"
                )
            add()
            add(
                "A generic relation schema was published: "
                f"`{str(entry['generic_relation_schema_published']).lower()}`."
            )
        else:
            for cited in cast(list[str], entry["evidence"]):
                add(f"- {cited}")
            add()
            add(
                "Admitted `S1.P05` history facts: "
                + ", ".join(
                    f"`{name}`"
                    for name in cast(list[str], entry["admitted_S1_P05_history_facts"])
                )
                + "."
            )
            add()
            surface = cast(dict[str, Any], entry["predecessor_surface"])
            add(
                "Predecessor production bytes redefined: "
                f"`{str(entry['predecessor_production_bytes_redefined']).lower()}`. "
                "Predecessor modules unchanged by `S1.P06`: "
                + ", ".join(f"`{name}`" for name in cast(list[str], surface["modules"]))
                + "."
            )
        add()
    add("## 7. Prohibition Accounting")
    add()
    for index, entry in enumerate(
        cast(list[dict[str, Any]], prohibitions["items"]), start=1
    ):
        add(f"### 7.{index} `{entry['statement']}`")
        add()
        add(f"State: `{entry['state']}`. Identifier: `{entry['prohibition_id']}`.")
        add()
        for cited in cast(list[str], entry["evidence"]):
            add(f"- {cited}")
        add()
    add(
        f"## 8. `{identity['phase']}` Product Inventory for `{readiness['next_slice']}`"
    )
    add()
    add(cast(str, inventory["purpose"]).capitalize() + ".")
    add()
    add("| Module | Publishing Slices | Exported Symbols |")
    add("| --- | --- | --- |")
    for entry in cast(list[dict[str, Any]], inventory["modules"]):
        slices = ", ".join(
            f"`{name}`" for name in cast(list[str], entry["publishing_slices"])
        )
        add(f"| `{entry['module']}` | {slices} | {entry['exported_symbol_count']} |")
    add()
    add(
        f"Owned modules: {inventory['owned_module_count']}. Owned symbols: "
        f"{inventory['owned_symbol_count']}. Duplicate symbols: "
        f"{inventory['duplicate_symbols']}. Alias symbols published: "
        f"`{str(inventory['alias_symbols_published']).lower()}`. Package-level "
        "aggregator published: "
        f"`{str(inventory['aggregator_export_published']).lower()}`. Inventory derived "
        f"from `{inventory['derived_from']}`."
    )
    add()
    add("| Slice | Module | Symbol |")
    add("| --- | --- | --- |")
    for entry in cast(list[dict[str, Any]], inventory["symbols"]):
        add(
            f"| `{entry['publishing_slice']}` | `{entry['module']}` | "
            f"`{entry['symbol']}` |"
        )
    add()
    add(f"## 9. `{readiness['next_slice']}` Entry Readiness")
    add()
    add("| # | Prerequisite | Status |")
    add("| --- | --- | --- |")
    for entry in cast(list[dict[str, Any]], readiness["prerequisites"]):
        add(
            f"| {entry['prerequisite_id'].split(':')[1]} | `{entry['subject']}` | "
            f"`{entry['status']}` |"
        )
    add()
    add(
        f"Unsatisfied prerequisites: {readiness['unsatisfied_prerequisite_count']}. "
        f"`{readiness['next_slice']}` contract corpus: "
        f"`{readiness['s11_contract_corpus']}`. Implementation state: "
        f"`{readiness['s11_implementation_state']}`."
    )
    add()
    governance_readiness = cast(dict[str, Any], readiness["governance_readiness"])
    add(
        "Governance readiness is recorded separately from semantic readiness. "
        "`S1.P06.S09` publication state: "
        f"`{governance_readiness['s09_publication_state']}`. Publication-governance "
        "exception: "
        f"`{governance_readiness['s09_publication_governance_exception']}`. Blocks "
        f"`{readiness['next_slice']}` semantic corpus construction: "
        f"`{str(governance_readiness['blocks_s11_semantic_corpus_construction']).lower()}`. "
        "Must be preserved for `S1.P06.S12` closure: "
        f"`{str(governance_readiness['must_be_preserved_for_s12_closure']).lower()}`."
    )
    add()
    add("## 10. Publication Governance")
    add()
    for entry in cast(list[dict[str, Any]], governance["publications"]):
        add(f"### 10.1 `{entry['slice']}` — {entry['characterization']}")
        add()
        add(cast(str, entry["statement"]))
        add()
        add("| Fact | Value |")
        add("| --- | --- |")
        add(f"| pull request | #{entry['pull_request']} |")
        add(f"| merge method | `{entry['merge_method']}` |")
        add(f"| rule suite | `{entry['rule_suite']}` |")
        add(f"| ruleset result | `{entry['ruleset_result']}` |")
        add(
            "| ruleset condition satisfied | "
            f"`{str(entry['ruleset_condition_satisfied']).lower()}` |"
        )
        add(
            "| administrator flag passed | "
            f"`{str(entry['administrator_flag_passed']).lower()}` |"
        )
        add(f"| bypass exercised | `{str(entry['bypass_exercised']).lower()}` |")
        add(f"| bypass actors configured | {entry['bypass_actors_configured']} |")
        add(f"| bypass records in period | {entry['bypass_records_in_period']} |")
        add(f"| refused earlier attempt | `{entry['refused_rule_suite']}` |")
        add(f"| squash commit | `{entry['squash_commit']}` |")
        add(f"| reviewed tree == squash tree | `{entry['tree']}` |")
        add(
            "| must be preserved for `S1.P06.S12` | "
            f"`{str(entry['must_be_preserved_for_s12_closure']).lower()}` |"
        )
        add()
        add("Evidence:")
        add()
        for cited in cast(list[str], entry["evidence"]):
            add(f"- {cited}")
        add()
        add("This record explicitly does not say:")
        add()
        for denied in cast(list[str], entry["explicitly_not"]):
            add(f"- {denied}")
        add()
    add(f"Unresolved exceptions: {governance['unresolved_exceptions']}.")
    add()
    status = cast(dict[str, Any], governance["evidential_status"])
    add("### 10.2 Evidential status")
    add()
    add(cast(str, status["note"]))
    add()
    add("| Fact | Value |")
    add("| --- | --- |")
    add(f"| basis | `{status['basis']}` |")
    add(f"| observed at | `{status['observed_at']}` |")
    add(f"| cited by | `{status['cited_by']}` |")
    add(
        "| provider records retained | "
        f"`{str(status['provider_records_retained']).lower()}` |"
    )
    add(f"| replayable offline | `{str(status['replayable_offline']).lower()}` |")
    add(
        "| `S1.P06.S12` must re-verify | "
        f"`{str(status['s12_must_reverify_before_relying_on_it']).lower()}` |"
    )
    add()
    add(cast(str, governance["note"]))
    add()
    add("## 11. Non-Generalizations")
    add()
    for entry in cast(list[str], non_generalizations["items"]):
        add(f"- {entry}")
    add()
    add(
        "Intentional deferral is not implementation failure: "
        f"`{str(non_generalizations['intentional_deferral_is_not_implementation_failure']).lower()}`."
    )
    add()
    add("## 12. Source Locks")
    add()
    add("| Lock | Path | Bytes | SHA-256 |")
    add("| --- | --- | --- | --- |")
    for entry in cast(list[dict[str, Any]], locks["cited_artifacts"]):
        add(
            f"| `{entry['lock_id']}` | `{entry['path']}` | {entry['byte_length']} | "
            f"`{entry['sha256']}` |"
        )
    add()
    add(
        f"Cited artifacts: {locks['count']}. Immutable: "
        f"`{str(locks['immutable']).lower()}`. Sealed at `{fmt['sealed_at']}`."
    )
    return "\n".join(lines) + "\n"
