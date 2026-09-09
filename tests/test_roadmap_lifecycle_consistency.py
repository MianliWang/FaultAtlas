"""Cross-Slice lifecycle-narrative consistency for `docs/roadmap.md`.

This module owns one rule, published by `S1.P06.S07.C01`: the roadmap must not
describe already-published work as current or future work, anywhere in the
document. Before this Slice that rule lived in product Slice oracles, where two
same-named copies had diverged and neither was sentence-local, and a sentence
that had been stale since `S1.P05.S08` survived both. Those two copies are
gone. The document-wide gate and status checks here deliberately overlap with
the product oracles rather than replacing them: those assert product-specific
roadmap facts, and this asserts the narrative rule.

Everything here reads prose. It asserts nothing about product semantics, owns
no production module, and pins no digest of a region the roadmap is designed to
evolve -- not the whole document, not the `S1.P06` section, not
`## Current status`, and not `## Current-code mapping`.

Locality is the design constraint. A guard that searches forward from one
lifecycle sentence until some later terminator can leave its own paragraph and
borrow a valid sentence from another section, which is how an earlier version
of a predecessor guard was weakened: a summary that had lost its own live-gate
claim silently satisfied itself from a claim tens of thousands of characters
away. Every check below is bounded to one paragraph or one sentence.

Sentence segmentation splits on ". ". In prose that boundary is exact: the
periods inside a Slice token such as `S1.P06.S01` are never followed by a
space, so no prose sentence is split in the middle and none is run together.
In an ordered list it splits at the list markers too, which is harmless here
because route state is parsed structurally by `_route_entries` rather than by
sentence, and every route item is self-contained.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
ROADMAP = REPOSITORY_ROOT / "docs/roadmap.md"

# The authoritative current state this module reconciles prose against.
COMPLETE_SLICES = tuple(f"S1.P06.S{index:02d}" for index in range(1, 8))
COMPLETE_PHASES = ("S1.P00", "S1.P01", "S1.P02", "S1.P03", "S1.P04", "S1.P05")
NEXT_SLICE = "S1.P06.S08"
NOT_STARTED_SLICES = tuple(f"S1.P06.S{index:02d}" for index in range(9, 13))
NOT_STARTED_PHASES = ("S1.P07", "S1.P08", "S1.P09", "S1.P10")
CORRECTION = "S1.P06.S07.C01"

# A Slice token, deliberately excluding a `.C01` correction suffix: a
# correction is a child of its Slice, never a gate of its own.
SLICE_TOKEN = re.compile(r"`(S1\.P\d\d(?:\.S\d\d)?)`")
GATE_CLAIM = re.compile(r"`(S1\.P\d\d(?:\.S\d\d)?)` is next and not started")
ACTIVE_PHASE = re.compile(r"`(S1\.P\d\d)` is active and incomplete")


def _text() -> str:
    return ROADMAP.read_text(encoding="utf-8")


def _flat(text: str) -> str:
    return " ".join(text.split())


def _paragraphs() -> list[tuple[int, str]]:
    """Blank-line separated paragraphs, each flattened, with its start line."""
    paragraphs: list[tuple[int, str]] = []
    current: list[str] = []
    start = 0
    for number, line in enumerate(_text().splitlines(), 1):
        if line.strip():
            if not current:
                start = number
            current.append(line)
        elif current:
            paragraphs.append((start, _flat(" ".join(current))))
            current = []
    if current:
        paragraphs.append((start, _flat(" ".join(current))))
    return paragraphs


def _sentences() -> list[tuple[int, str]]:
    """Every sentence in the document, each with the line its paragraph starts on.

    The span is the paragraph rather than the sentence because a sentence may
    wrap; it is used only to report where a failure lives.
    """
    return [
        (start, sentence.strip())
        for start, paragraph in _paragraphs()
        for sentence in paragraph.split(". ")
        if sentence.strip()
    ]


def _section(heading: str) -> str:
    """One `##` section, bounded by the next `##` heading."""
    text = _text()
    start = text.index(f"## {heading}")
    remainder = text.index("\n## ", start + 1)
    return _flat(text[start:remainder])


# --- 6.1 current-state structural witness ---------------------------------


def test_the_current_status_section_states_the_authoritative_lifecycle() -> None:
    section = _section("Current status")

    assert "`S1.P06` is active and incomplete" in section
    for slice_id in COMPLETE_SLICES:
        assert f"`{slice_id}` is complete" in section, slice_id
    assert f"`{NEXT_SLICE}` is next and not started" in section
    assert "`S1.P07` through `S1.P10` remain not started" in section
    for slice_id in (NEXT_SLICE, *NOT_STARTED_SLICES):
        assert f"`{slice_id}` is complete" not in section, slice_id
    for phase in NOT_STARTED_PHASES:
        assert f"`{phase}` is complete" not in section, phase


def test_the_current_status_section_records_the_correction_as_complete() -> None:
    """C01 is recorded as a child of `S1.P06.S07`, following `S1.P05.S08.C01`."""
    section = _section("Current status")

    assert f"`{CORRECTION}` correction" in section
    assert f"`S1.P06.S07` is complete including the `{CORRECTION}` correction" in (
        section
    )


def test_the_correction_is_not_a_gate_and_not_a_phase(  # noqa: D401
) -> None:
    """A correction may never appear as a gate or an active phase anywhere."""
    flat = _flat(_text())

    assert f"`{CORRECTION}` is active and incomplete" not in flat
    # Subsumes the "is next and not started" form.
    assert f"`{CORRECTION}` is next" not in flat
    assert f"`{CORRECTION}` is not started" not in flat


def test_the_document_names_exactly_one_live_p06_product_gate() -> None:
    flat = _flat(_text())
    gates = set(GATE_CLAIM.findall(flat))

    assert gates == {NEXT_SLICE}, sorted(gates)
    assert set(ACTIVE_PHASE.findall(flat)) == {"S1.P06"}


# Enumerating forbidden phrasings does not converge: each round of review
# supplies a spelling the previous list did not hold. The present-tense state
# vocabulary of this document is small and closed, so the set is inverted --
# every present-tense state claim is extracted by one grammar and checked
# against the state its unit actually has. A new spelling is caught because it
# is a claim, not because it was predicted.
PRESENT_CLAIM = re.compile(
    r"`(S1\.P\d\d(?:\.S\d\d)?)`\s+(is|are|remains|remain|will)\b([^,;:.]{0,60})"
)
ACTIVE_PHASE_ID = "S1.P06"


def _claimed_states(verb: str, tail: str) -> set[str]:
    """Every lifecycle state a predicate asserts, not the first one recognised.

    "is next but complete" asserts two states and is self-contradictory; a
    classifier that returned on the first match would read it as one.
    """
    states: set[str] = set()
    text = tail.lower()
    if verb == "will":
        states.add("future")
    if "not started" in text or "not yet started" in text:
        states.add("not_started")
    if "next" in text:
        states.add("next")
    if "active" in text or "incomplete" in text:
        states.add("active")
    # "incomplete" is not a completion claim.
    if re.search(r"(?<!in)complete", text):
        states.add("complete")
    return states


def _allowed_states(unit: str) -> set[str] | None:
    """The states one unit may be claimed to be in, or None if it is unknown.

    Returning None rather than an empty set matters: a claim about a unit this
    programme does not contain -- "`S1.P06.S13` is next" -- must be refused,
    not silently skipped.
    """
    phase = unit.partition(".S")[0]
    if phase in COMPLETE_PHASES:
        return {"complete"}
    if unit == ACTIVE_PHASE_ID:
        return {"active"}
    if phase == ACTIVE_PHASE_ID:
        if unit in COMPLETE_SLICES:
            return {"complete"}
        if unit == NEXT_SLICE:
            return {"next", "not_started"}
        if unit in NOT_STARTED_SLICES:
            return {"not_started"}
        return None
    if unit in NOT_STARTED_PHASES or phase in NOT_STARTED_PHASES:
        return {"not_started"}
    return None


def test_every_present_tense_state_claim_matches_the_authoritative_state() -> None:
    """One grammar over the closed predicate vocabulary, sentence-local.

    Past-tense narrative is untouched: only `is`, `are`, `remain(s)` and `will`
    are read, so "`S1.P05` was `eligible_to_begin`" and "`S1.P05` through
    `S1.P10` were not started" stay legitimate history.
    """
    seen = 0
    for start, sentence in _sentences():
        for unit, verb, tail in PRESENT_CLAIM.findall(sentence):
            states = _claimed_states(verb, tail)
            if not states:
                continue
            allowed = _allowed_states(unit)
            assert allowed is not None, (start, unit, sorted(states))
            seen += 1
            assert states <= allowed, (
                start,
                unit,
                sorted(states),
                sorted(allowed),
                tail[:60],
            )
    # A floor, so a grammar that silently stopped matching would fail here
    # rather than pass vacuously. The document currently carries 68 such claims.
    assert seen >= 60, seen


# Attribution reads the other way round: the unit is the object, not the
# subject. One vocabulary covers Slices and Phases alike.
ATTRIBUTED_TO = re.compile(
    r"(?<!was )(?<!were )\b(?:belongs to|owned by|is deferred to|"
    r"is scheduled for|awaits|is assigned to|"
    r"will be (?:added|published|implemented) by)\s+"
    r"`(S1\.P\d\d(?:\.S\d\d)?)`"
)


def _is_negated(clause: str) -> bool:
    """Whether a negation heads the noun phrase this predicate belongs to."""
    return bool(
        re.search(r"\bno\b\s+(?:\w+\s+){0,3}$", re.split(r"[;:,]", clause)[-1], re.I)
    )


def test_no_open_work_is_presently_attributed_to_a_completed_unit() -> None:
    """A completed Slice or Phase may be a past owner, never the present one.

    The reduced passive counts: "provenance owned by `S1.P09`" attributes just
    as directly as "is owned by". Past tense is excluded by the lookbehinds, and
    a negated claim -- "No subject remains owned by `S1.P04`" -- says the
    opposite and is admitted.
    """
    for start, sentence in _sentences():
        for match in ATTRIBUTED_TO.finditer(sentence):
            unit = match.group(1)
            if _is_negated(sentence[: match.start()]):
                continue
            assert unit not in COMPLETE_SLICES, (start, unit, sentence[:200])
            assert unit not in COMPLETE_PHASES, (start, unit, sentence[:200])


COMPLETION_CLAIM = re.compile(r"`(S1\.P06\.S\d\d)` is complete")
# A sentence enumerating this many completed Slices is a lifecycle summary,
# whatever phrase introduces it.
LIFECYCLE_ENUMERATION = 3
LIFECYCLE_SENTENCES = 5


def _lifecycle_sentences() -> list[tuple[int, str]]:
    """Sentences that enumerate the P06 lifecycle, selected by what they say.

    Keying on an introductory phrase such as "`S1.P06` is active and
    incomplete" would let a summary escape by omitting it, so the enumeration
    itself is the key.
    """
    return [
        (start, sentence)
        for start, sentence in _sentences()
        if len(COMPLETION_CLAIM.findall(sentence)) >= LIFECYCLE_ENUMERATION
    ]


def test_every_lifecycle_sentence_carries_its_own_live_gate() -> None:
    """Locality, at sentence granularity rather than paragraph granularity.

    A paragraph is the wrong bound: the largest in this document is around
    21,000 characters, so a paragraph-local check would still let one lifecycle
    claim borrow a valid gate sentence from far away inside it. The lifecycle
    claim is one sentence, so that is the unit checked.
    """
    lifecycle = _lifecycle_sentences()

    assert len(lifecycle) == LIFECYCLE_SENTENCES, len(lifecycle)
    for start, sentence in lifecycle:
        for slice_id in COMPLETE_SLICES:
            assert f"`{slice_id}` is complete" in sentence, (start, slice_id)
        assert f"`{NEXT_SLICE}` is next and not started" in sentence, start
        # The live gate is neither complete nor absent from this check: a
        # sentence asserting both states at once is self-contradictory.
        for slice_id in (NEXT_SLICE, *NOT_STARTED_SLICES):
            assert f"`{slice_id}` is complete" not in sentence, (start, slice_id)


def test_no_sentence_anywhere_calls_a_not_started_unit_complete() -> None:
    """The inverse error, document-wide and sentence-local.

    A completion claim for a unit that has not started contradicts the
    authoritative state wherever it stands, including outside any lifecycle
    summary.
    """
    for start, sentence in _sentences():
        for unit in (NEXT_SLICE, *NOT_STARTED_SLICES, *NOT_STARTED_PHASES):
            assert f"`{unit}` is complete" not in sentence, (start, unit)
            assert f"`{unit}` was completed" not in sentence, (start, unit)


# --- 6.2 route witness ------------------------------------------------------


def _route_entries() -> list[tuple[str, str, str, str]]:
    """The numbered `S1.P06` route.

    Each row is (list ordinal, slice id, the slice's numeric suffix,
    parenthesised state). The ordinal is carried because a Slice sitting at the
    wrong marker leaves the set of (slice, state) pairs unchanged.
    """
    text = _text()
    start = text.index("The `S1.P06` route is provisional")
    end = text.index("`S1.P06` consumes the bounded", start)
    block = text[start:end]
    rows: list[tuple[str, str, str, str]] = re.findall(
        r"^(\d+)\.\s+`(S1\.P06\.S(\d\d))`[^\n]*(?:\n\s+)?[^\n]*?\((complete|next, not "
        r"started|not started)\)",
        block,
        re.M,
    )
    return rows


def test_the_route_numbers_every_position_in_order() -> None:
    """The list marker is part of the route, not decoration.

    Swapping two markers leaves the same set of (Slice, state) pairs, so the
    ordinal is captured and required to match the Slice it labels.
    """
    rows = _route_entries()

    assert [ordinal for ordinal, _, _, _ in rows] == [str(n) for n in range(1, 13)]
    for ordinal, slice_id, suffix, _ in rows:
        assert int(ordinal) == int(suffix), (ordinal, slice_id)


def test_the_route_states_the_authoritative_state_for_every_position() -> None:
    rows = _route_entries()
    # Building the lookup first would let a duplicated row collapse silently.
    assert len(rows) == 12, rows
    assert len({slice_id for _, slice_id, _, _ in rows}) == 12, rows
    entries = {slice_id: state for _, slice_id, _, state in rows}

    assert len(entries) == 12, sorted(entries)
    for slice_id in COMPLETE_SLICES:
        assert entries[slice_id] == "complete", slice_id
    assert entries[NEXT_SLICE] == "next, not started"
    for slice_id in NOT_STARTED_SLICES:
        assert entries[slice_id] == "not started", slice_id


def test_the_route_carries_exactly_one_next_position() -> None:
    states = [state for _, _, _, state in _route_entries()]

    assert states.count("next, not started") == 1
    assert states.count("complete") == len(COMPLETE_SLICES)


def test_the_correction_is_not_a_numbered_route_position() -> None:
    """C01 is an unnumbered child bullet, as `S1.P05.S08.C01` is."""
    text = _text()
    start = text.index("The `S1.P06` route is provisional")
    end = text.index("`S1.P06` consumes the bounded", start)
    block = text[start:end]

    assert f"`{CORRECTION}`" in block
    assert not re.search(rf"^\d+\.\s+`{re.escape(CORRECTION)}`", block, re.M)
    assert re.search(rf"^- `{re.escape(CORRECTION)}` — ", block, re.M)
    assert CORRECTION not in {slice_id for _, slice_id, _, _ in _route_entries()}


# --- 6.3 sentence-local completed-Slice guard -------------------------------


# A bounded lexical backstop, not a semantic model. It is applied to one
# sentence at a time and only where that sentence names a completed Slice; it
# discovers formulations, and the positive assertions below carry the meaning.
def _completed_slices_in(sentence: str) -> list[str]:
    return [
        token for token in SLICE_TOKEN.findall(sentence) if token in COMPLETE_SLICES
    ]


@pytest.mark.parametrize("slice_id", COMPLETE_SLICES)
def test_no_sentence_calls_a_completed_slice_future_work(slice_id: str) -> None:
    """A lexical backstop applied sentence-locally, not a semantic verifier.

    This cannot decide whether prose is true. It refuses a bounded set of
    formulations that state a completed Slice is still ahead, in the sentence
    where they stand, and it is deliberately not the only assurance for this
    correction: the positive assertions below pin the corrected sentences
    themselves.
    """
    for start, sentence in _sentences():
        if slice_id not in _completed_slices_in(sentence):
            continue
        for shape in (
            f"`{slice_id}` is next",
            f"`{slice_id}` is not started",
            f"`{slice_id}` has not started",
            f"`{slice_id}` has not begun",
            f"`{slice_id}` remains not started",
            f"`{slice_id}` remains future",
            f"`{slice_id}` remains open",
            f"`{slice_id}` is planned",
            f"`{slice_id}` is not yet",
            f"`{slice_id}` will",
            f"remain `{slice_id}` work",
            f"remains `{slice_id}` work",
            f"remain owned by `{slice_id}`",
            f"remains owned by `{slice_id}`",
            f"deferred to `{slice_id}`",
            f"yet to be published by `{slice_id}`",
        ):
            assert shape not in sentence, (start, shape, sentence[:200])


# A future claim is attributed to whichever token it names, so the token is
# matched together with the wording rather than merely co-occurring with it.
ATTRIBUTED_FUTURE = (
    "will be added by",
    "will be published by",
    "will be implemented by",
    "is to be added by",
    "is to be published by",
    "is to be implemented by",
    "is deferred to",
    "is owned by",
    "belongs to",
    "is scheduled for",
    "awaits",
)


@pytest.mark.parametrize("slice_id", COMPLETE_SLICES)
def test_no_future_claim_is_attributed_to_a_completed_slice(slice_id: str) -> None:
    """The backstop from the other direction, tied to its own token.

    Co-occurrence is not attribution. A sentence may legitimately name a
    completed Slice and a not-started one together, so the wording is matched
    with the token it points at rather than anywhere in the sentence.
    """
    for start, sentence in _sentences():
        for wording in ATTRIBUTED_FUTURE:
            assert f"{wording} `{slice_id}`" not in sentence, (
                start,
                wording,
                sentence[:240],
            )


def test_no_completed_phase_is_named_as_a_present_owner_of_open_work() -> None:
    """The class this correction was written for.

    `S1.P05` had already carried the `deferred:19` default-branch subject
    forward to `S5`, yet the `S1.P05.S01` narrative still said the subject "is
    owned by `S1.P05`". A completed phase may be named as a past owner, never
    as the present one.
    """
    for start, sentence in _sentences():
        for phase in COMPLETE_PHASES:
            for shape in (
                f"is owned by `{phase}`",
                f"remains owned by `{phase}`",
                f"remain owned by `{phase}`",
            ):
                index = sentence.find(shape)
                if index == -1:
                    continue
                # A negated claim -- "No subject remains owned by `S1.P04`" --
                # says the opposite and is correct. The negation has to modify
                # this predicate's own subject, so it must head the noun phrase
                # immediately before it. An unrelated negation earlier in the
                # sentence does not negate the claim, whether or not
                # punctuation separates the two: "No evidence is available and
                # the subject remains owned by `S1.P05`" still asserts it.
                clause = re.split(r"[;:,]", sentence[:index])[-1]
                assert re.search(r"\bno\b\s+(?:\w+\s+){0,3}$", clause, re.I), (
                    start,
                    phase,
                    shape,
                    clause[-80:],
                )


# --- 6.4 positive assertions for the corrected sentences --------------------


def test_the_deferred_default_branch_subject_names_its_current_owner() -> None:
    """The sentence this correction repaired, asserted as intended prose."""
    flat = _flat(_text())

    assert (
        "`S1.P02` `deferred:19` default-branch observation was owned by `S1.P05` "
        "and was not implemented by `S1.P05.S01`; `S1.P05.S08` has since carried "
        "it forward to `S5`, and the historical default branch remains unknown "
        "and owned by `S2`." in flat
    )
    assert "default-branch observation is owned by `S1.P05`" not in flat


def test_the_authoritative_carry_forward_statement_is_unchanged() -> None:
    """The statement the corrected sentence had contradicted still stands."""
    flat = _flat(_text())

    assert (
        "`deferred:19` default-branch observation was assigned to `S1.P05`, which "
        "`S1.P05.S08` has since carried forward to `S5`" in flat
    )


def test_the_predecessor_corrections_from_s06_and_s07_still_stand() -> None:
    """The two sentences earlier Slices repaired, now owned here."""
    flat = _flat(_text())

    assert (
        "Test material, reported outcomes and comparability became `S1.P06.S06` "
        "work, case-local explanation and hypothesis became `S1.P06.S07` work" in flat
    )
    assert "the rest remain owned by `S1.P06.S08` through `S1.P06.S09`" in flat
    assert (
        "those were taken up by `S1.P06.S03` through `S1.P06.S07` and the rest "
        "remain owned by `S1.P06.S08`" in flat
    )


def test_correct_later_ownership_is_preserved() -> None:
    """Later owners must survive the audit untouched.

    The audit's failure mode in the other direction is rewriting a legitimate
    later-ownership sentence because a completed Slice is mentioned nearby.
    """
    flat = _flat(_text())

    for statement in (
        "confidence, review, and interpretation provenance remain owned by `S1.P09`",
        "the fault-evidence bridge remains `S1.P06.S09` work",
        "durable byte contracts remain `S1.P10` work",
        "which remains `S1.P06.S10` work",
        "the historical default branch remains unknown and owned by `S2`",
        "which remains `S5` ownership",
        "`S1.P07` through `S1.P10` remain not started",
    ):
        assert statement in flat, statement


def test_the_correction_narrative_records_what_it_changed() -> None:
    flat = _flat(_text())

    assert (
        "`S1.P06.S07.C01` corrects roadmap lifecycle narrative without changing "
        "any published contract." in flat
    )
    assert "It adds no production module" in flat
    assert "does not move the live gate, which stays `S1.P06.S08`" in flat
