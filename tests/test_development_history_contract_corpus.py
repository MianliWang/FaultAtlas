from __future__ import annotations

import hashlib
import json
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, cast

import pytest
from pydantic import BaseModel, ValidationError

import faultatlas.domain.history as history_module
import faultatlas.domain.history_evidence_link as link_module
from faultatlas.domain import evidence, history, identity, revision

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
CORPUS = REPOSITORY_ROOT / "reference_corpus/contracts/development-history/v1"

CORPUS_FILES = (
    "contract.md",
    "invalid-vectors.json",
    "invalid-vectors.sha256",
    "manifest.json",
    "manifest.sha256",
    "replay-vectors.json",
    "replay-vectors.sha256",
    "valid-vectors.json",
    "valid-vectors.sha256",
)
SEALED_JSON = ("manifest", "valid-vectors", "invalid-vectors", "replay-vectors")

PRODUCTION_MODULES = (
    "faultatlas.domain.history",
    "faultatlas.domain.history_evidence_link",
)
SUPPORTING_AUTHORITIES = (
    "faultatlas.domain.evidence",
    "faultatlas.domain.identity",
    "faultatlas.domain.revision",
)
PRODUCTION_SOURCE_COUNT = 13

# Support values a python-mode vector may materialise. Deliberately closed.
SUPPORT_MODELS = {
    "DurableEvidenceRecordReference": evidence.DurableEvidenceRecordReference,
    "GitBlobIdentity": revision.GitBlobIdentity,
    "GitCommitIdentity": revision.GitCommitIdentity,
    "GitRefName": revision.GitRefName,
    "GitRepositoryPath": revision.GitRepositoryPath,
    "NumberedSourceObjectIdentity": identity.NumberedSourceObjectIdentity,
    "ProviderScopedSourceObjectIdentity": identity.ProviderScopedSourceObjectIdentity,
    "RevisionRoleAssignment": revision.RevisionRoleAssignment,
}
SUPPORT_ENUMS = {
    "ChangedPathStatus": history.ChangedPathStatus,
    "RevisionRole": revision.RevisionRole,
    "SourceObjectKind": identity.SourceObjectKind,
}
ALLOWED_MARKERS = ("enum_value", "instant_value", "tuple_value", "typed_value")
ALLOWED_OPERATIONS = ("construct", "reject")
ALLOWED_INPUT_MODES = ("json", "python", "replay")


def _owned_targets() -> dict[str, Any]:
    """The nine P05 product targets, derived from live `__all__`."""
    targets = {name: getattr(history_module, name) for name in history_module.__all__}
    targets.update({name: getattr(link_module, name) for name in link_module.__all__})
    return targets


OWNED = _owned_targets()
RESOLVABLE = {**OWNED, **SUPPORT_MODELS, **SUPPORT_ENUMS}


def _load(name: str) -> dict[str, Any]:
    return cast(
        dict[str, Any], json.loads((CORPUS / f"{name}.json").read_text("utf-8"))
    )


MANIFEST = _load("manifest")
VALID = _load("valid-vectors")
INVALID = _load("invalid-vectors")
REPLAY = _load("replay-vectors")


def _materialise(value: Any) -> Any:
    """Turn a declared corpus input into a Python value, marker by marker."""
    if isinstance(value, list):
        return [_materialise(item) for item in cast(list[Any], value)]
    if not isinstance(value, dict):
        return value
    mapping = cast(dict[str, Any], value)
    markers = [key for key in mapping if key in ALLOWED_MARKERS]
    if not markers:
        unknown = [
            k for k in mapping if k.endswith("_value") and k not in ALLOWED_MARKERS
        ]
        assert not unknown, f"unknown marker rejected: {unknown}"
        return {key: _materialise(item) for key, item in mapping.items()}
    assert len(markers) == 1 and len(mapping) == 1, (
        "markers are exact singleton objects"
    )
    marker = markers[0]
    payload = mapping[marker]
    if marker == "tuple_value":
        return tuple(_materialise(item) for item in cast(list[Any], payload))
    if marker == "instant_value":
        return datetime.fromisoformat(cast(str, payload).replace("Z", "+00:00"))
    spec = cast(dict[str, Any], payload)
    target = cast(str, spec["target"])
    if marker == "enum_value":
        assert target in SUPPORT_ENUMS, f"unknown enum target: {target}"
        return SUPPORT_ENUMS[target](spec["input"])
    assert target in RESOLVABLE, f"unknown target: {target}"
    resolved = RESOLVABLE[target]
    assert isinstance(resolved, type) and issubclass(resolved, BaseModel)
    # Declared fixture data is JSON, so a published value is built through the
    # published JSON reconstruction rather than through Python-mode input.
    return resolved.model_validate_json(json.dumps(spec["input"]))


def _construct(vector: dict[str, Any]) -> Any:
    target = RESOLVABLE[vector["target"]]
    supplied = vector["input"]
    if vector["input_mode"] == "python":
        supplied = _materialise(supplied)
        if isinstance(target, type) and issubclass(target, Enum):
            return target(supplied)
        return cast(Any, target).model_validate(supplied)
    if isinstance(target, type) and issubclass(target, Enum):
        return target(supplied)
    return cast(Any, target).model_validate_json(json.dumps(supplied))


def _dump(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    return json.loads(cast(BaseModel, value).model_dump_json())


def _ids(section: dict[str, Any]) -> list[str]:
    return [cast(str, v["id"]) for v in section["vectors"]]


# --- corpus files -------------------------------------------------------------


def test_the_corpus_directory_holds_exactly_the_declared_files() -> None:
    assert {path.name for path in CORPUS.iterdir()} == set(CORPUS_FILES)
    assert {entry["filename"] for entry in MANIFEST["corpus_files"]} == set(
        CORPUS_FILES
    )
    assert len(MANIFEST["corpus_files"]) == len(CORPUS_FILES) == 9


@pytest.mark.parametrize("name", SEALED_JSON)
def test_each_sealed_file_is_canonical_and_digest_locked(name: str) -> None:
    raw = (CORPUS / f"{name}.json").read_bytes()
    canonical = (
        json.dumps(
            json.loads(raw), sort_keys=True, separators=(",", ":"), ensure_ascii=False
        )
        + "\n"
    ).encode("utf-8")

    assert raw == canonical
    assert not raw.startswith(b"\xef\xbb\xbf")
    assert b"\r" not in raw
    assert (CORPUS / f"{name}.sha256").read_text("utf-8") == (
        f"{hashlib.sha256(raw).hexdigest()}  {name}.json\n"
    )


def test_the_manifest_records_the_vector_file_digests() -> None:
    declared = {e["filename"]: e for e in MANIFEST["corpus_files"] if "sha256" in e}

    assert set(declared) == {
        "valid-vectors.json",
        "invalid-vectors.json",
        "replay-vectors.json",
    }
    for filename, entry in declared.items():
        raw = (CORPUS / filename).read_bytes()
        assert entry["sha256"] == hashlib.sha256(raw).hexdigest()
        assert entry["byte_length"] == len(raw)


# --- registry and closed world ------------------------------------------------


def test_the_nine_product_targets_come_from_live_dunder_all() -> None:
    """Target coverage is derived, so a later published symbol forces review."""
    declared = [entry["symbol"] for entry in MANIFEST["target_symbols"]]
    live = list(history_module.__all__) + list(link_module.__all__)

    assert declared == live
    assert len(declared) == 9
    assert set(declared) == set(OWNED)
    modules = {entry["module"] for entry in MANIFEST["target_symbols"]}
    assert modules == set(PRODUCTION_MODULES)
    assert tuple(MANIFEST["scope"]["production_modules"]) == PRODUCTION_MODULES
    assert (
        tuple(MANIFEST["scope"]["supporting_authorities_not_owned"])
        == SUPPORTING_AUTHORITIES
    )


def test_no_supporting_authority_symbol_is_counted_as_owned() -> None:
    owned = {entry["symbol"] for entry in MANIFEST["target_symbols"]}

    assert owned.isdisjoint(SUPPORT_MODELS)
    assert owned.isdisjoint(set(SUPPORT_ENUMS) - set(history_module.__all__))
    registry = MANIFEST["execution_contract"]["registry"]
    assert registry["owned_model_targets"] + registry["owned_enum_targets"] == 9


def test_the_snapshot_modules_are_outside_this_corpus() -> None:
    """No S1.P05 value consumes them, so the corpus must not re-own them."""
    blob = json.dumps([MANIFEST, VALID, INVALID, REPLAY])

    assert "faultatlas.domain.snapshot" not in blob
    assert "RepositorySnapshot" not in blob


@pytest.mark.parametrize("section", (VALID, INVALID, REPLAY))
def test_every_vector_declares_a_known_target_operation_and_mode(
    section: dict[str, Any],
) -> None:
    for vector in section["vectors"]:
        assert vector["target"] in RESOLVABLE, vector["id"]
        assert vector["operation"] in ALLOWED_OPERATIONS, vector["id"]
        assert vector["input_mode"] in ALLOWED_INPUT_MODES, vector["id"]
        assert vector["purpose"], vector["id"]
        assert vector["decision_references"], vector["id"]


def test_unknown_target_operation_and_marker_all_fail_closed() -> None:
    with pytest.raises(KeyError):
        RESOLVABLE["RepositorySnapshotIdentity"]
    assert "walk" not in ALLOWED_OPERATIONS
    with pytest.raises(AssertionError):
        _materialise({"smuggled_value": {"target": "GitRefName", "input": "x"}})
    with pytest.raises(AssertionError):
        _materialise(
            {"typed_value": {"target": "RepositorySnapshotIdentity", "input": {}}}
        )


def test_vector_identifiers_are_unique_across_the_corpus() -> None:
    ids = _ids(VALID) + _ids(INVALID) + _ids(REPLAY)

    assert len(ids) == len(set(ids))
    assert all(i.startswith("history.") for i in ids)


def test_the_declared_counts_match_the_vector_files() -> None:
    summary = MANIFEST["vector_summary"]

    assert summary["valid"]["count"] == len(VALID["vectors"]) == 48
    assert summary["invalid"]["count"] == len(INVALID["vectors"]) == 95
    assert summary["replay"]["count"] == len(REPLAY["vectors"]) == 24
    assert summary["total_vectors"] == 167
    assert summary["fixtures"] == len(VALID["fixtures"]) == 19


def test_declared_fixtures_are_shared_and_locked() -> None:
    ids = [f["id"] for f in VALID["fixtures"]]

    assert len(ids) == len(set(ids)) == 19
    assert all(f["status"] == "locked" for f in VALID["fixtures"])
    assert VALID["fixtures"] == INVALID["fixtures"] == REPLAY["fixtures"]


# --- executing the vectors ----------------------------------------------------


@pytest.mark.parametrize("vector", VALID["vectors"], ids=_ids(VALID))
def test_every_valid_vector_constructs_its_declared_value(
    vector: dict[str, Any],
) -> None:
    value = _construct(vector)
    expected = vector["expected"]

    assert type(value).__name__ == expected["concrete_type"], vector["id"]
    assert _dump(value) == expected["semantic_dump"], vector["id"]
    if expected["round_trip_equal"] and isinstance(value, BaseModel):
        target = cast(Any, RESOLVABLE[vector["target"]])
        assert target.model_validate_json(value.model_dump_json()) == value


@pytest.mark.parametrize("vector", INVALID["vectors"], ids=_ids(INVALID))
def test_every_invalid_vector_is_rejected_as_declared(vector: dict[str, Any]) -> None:
    expected = vector["expected"]
    if expected["failure_category"] == "vocabulary_error":
        with pytest.raises(ValueError):
            _construct(vector)
        assert expected["error_type"] == "enum"
        assert expected["error_location"] == []
        return

    with pytest.raises(ValidationError) as caught:
        _construct(vector)

    errors = caught.value.errors()
    assert expected["failure_category"] == "validation_error"
    location = tuple(expected["error_location"])
    if expected["error_location_mode"] == "exact":
        first = errors[0]
        assert first["loc"] == location, (vector["id"], errors)
        assert first["type"] == expected["error_type"], (vector["id"], errors)
    else:
        assert any(
            error["type"] == expected["error_type"]
            and tuple(error["loc"])[: len(location)] == location
            for error in errors
        ), (vector["id"], errors)


@pytest.mark.parametrize("vector", REPLAY["vectors"], ids=_ids(REPLAY))
def test_every_replay_vector_reconstructs_the_retained_value(
    vector: dict[str, Any],
) -> None:
    target = cast(Any, RESOLVABLE[vector["target"]])
    value = target.model_validate_json(json.dumps(vector["input"]))
    expected = vector["expected"]

    assert type(value).__name__ == expected["concrete_type"], vector["id"]
    assert _dump(value) == expected["semantic_dump"], vector["id"]
    assert target.model_validate_json(value.model_dump_json()) == value


def test_enum_vectors_reject_a_lexeme_outside_the_published_vocabulary() -> None:
    with pytest.raises(ValueError):
        history.ChangedPathStatus("renamed")
    assert [m.value for m in history.ChangedPathStatus] == ["added", "modified"]


# --- governance is an authority, never a vector -------------------------------


def _authority(reference: str) -> dict[str, Any]:
    return next(
        entry
        for entry in MANIFEST["source_decisions"]
        if entry["decision_reference"] == reference
    )


@pytest.mark.parametrize(
    "reference",
    (
        "decision:s1-p05-s08:disposition",
        "correction:s1-p05-s08-c01:owner-topology",
        "closure:s1-p03:evidence-envelope",
        "acquisition:run-0001",
        "correction:s04-c01-acquisition-closure",
    ),
)
def test_every_source_authority_digest_matches_live_bytes(reference: str) -> None:
    entry = _authority(reference)
    raw = (REPOSITORY_ROOT / entry["path"]).read_bytes()

    assert entry["sha256"] == hashlib.sha256(raw).hexdigest()
    assert entry["authority_ids"]
    assert entry["authority_role"]


def test_the_authority_set_is_exactly_five_and_minimal() -> None:
    assert len(MANIFEST["source_decisions"]) == 5


def test_the_effective_governance_is_recomputed_from_both_artifacts() -> None:
    """The corpus must not treat the base S08 owner topology as current truth."""
    base = json.loads(
        (
            REPOSITORY_ROOT / _authority("decision:s1-p05-s08:disposition")["path"]
        ).read_text("utf-8")
    )
    correction = json.loads(
        (
            REPOSITORY_ROOT
            / _authority("correction:s1-p05-s08-c01:owner-topology")["path"]
        ).read_text("utf-8")
    )
    corrected = {
        item["source"]["subject_id"]: item["corrected"]
        for item in correction["superseded_dispositions"]["items"]
    }

    dispositions: dict[str, int] = {}
    immediate: dict[str, int] = {}
    long_term: dict[str, int] = {}
    states: dict[str, int] = {}
    subjects: set[str] = set()
    for entry in base["inherited_subject_register"]["items"]:
        subject_id = entry["source"]["subject_id"]
        subjects.add(subject_id)
        part = (
            entry.get("carried_forward") or entry["split"]["carried_forward_remainder"]
        )
        view = {
            "disposition": entry["disposition"],
            "current_state": part["current_state"],
            "immediate_owner": part["immediate_owner"],
            "preserved_long_term_owner": part["preserved_long_term_owner"],
        }
        if subject_id in corrected:
            view = {key: corrected[subject_id][key] for key in view}
        dispositions[view["disposition"]] = dispositions.get(view["disposition"], 0) + 1
        immediate[view["immediate_owner"]] = (
            immediate.get(view["immediate_owner"], 0) + 1
        )
        long_term[view["preserved_long_term_owner"]] = (
            long_term.get(view["preserved_long_term_owner"], 0) + 1
        )
        states[view["current_state"]] = states.get(view["current_state"], 0) + 1
        assert view["immediate_owner"] != "S1.P05"
        assert view["preserved_long_term_owner"] != "S1.P05"

    declared = MANIFEST["effective_governance"]
    assert len(subjects) == declared["inherited_subject_count"] == 12
    assert declared["self_introduced_count"] == 0
    assert declared["self_owned_open"] == 0
    assert declared["totals"]["disposition"] == dispositions
    assert declared["totals"]["immediate_owner"] == immediate
    assert declared["totals"]["preserved_long_term_owner"] == long_term
    assert declared["totals"]["state"] == states
    assert declared["recomputation_required"] is True


def test_governance_vocabulary_never_leaks_into_product_vectors() -> None:
    """Authority references are allowed; governance vocabulary as data is not."""
    surfaces = [
        {key: vector[key] for key in ("input", "expected")}
        for section in (VALID, INVALID, REPLAY)
        for vector in section["vectors"]
    ]
    vectors = json.dumps(surfaces)

    for token in (
        "carried_forward",
        "self_owned_open",
        "unsupported_current_scope",
        "evidence_insufficient",
        "preserved_long_term_owner",
        "disposition",
    ):
        assert token not in vectors, token


def test_the_governance_artifacts_are_not_vectorized() -> None:
    assert MANIFEST["effective_governance"]["vectorized_as_product_behavior"] is False
    assert _authority("decision:s1-p05-s08:disposition")["authority_role"] == (
        "governance_disposition_not_vectorized"
    )


# --- replay provenance --------------------------------------------------------


def test_replay_classifications_are_exactly_the_three_published_kinds() -> None:
    declared = MANIFEST["replay_contract"]["classifications"]
    used = {v["evidence_classification"] for v in REPLAY["vectors"]}

    assert (
        set(declared)
        == used
        == {
            "caller_supplied_association",
            "caller_supplied_composition",
            "retained_normalized_observation",
        }
    )
    assert MANIFEST["replay_contract"]["deterministic_derivation_present"] is False
    assert (
        MANIFEST["replay_contract"]["flattened_evidence_derived_history_claimed"]
        is False
    )


def test_the_change_set_replays_as_composition_and_is_never_linked() -> None:
    """A published fact that S1.P05.S07 does not admit as evidence-linkable."""
    change_sets = [
        v for v in REPLAY["vectors"] if v["target"] == "PullRequestChangeSet"
    ]
    links = [
        v
        for v in REPLAY["vectors"]
        if v["target"] == "PullRequestHistoryFactEvidenceLink"
    ]

    assert len(change_sets) == 1
    assert change_sets[0]["evidence_classification"] == "caller_supplied_composition"
    assert len(links) == 12
    for vector in links:
        assert vector["evidence_classification"] == "caller_supplied_association"
        assert "changed_paths" not in json.dumps(vector["input"]["fact"])
    assert (
        MANIFEST["replay_contract"]["evidence_limits"]["linkable_history_facts"] == 11
    )
    assert (
        MANIFEST["replay_contract"]["evidence_limits"][
            "change_set_completeness_claimed"
        ]
        is False
    )


def test_the_retained_artifact_locks_match_live_bytes() -> None:
    for lock in REPLAY["artifact_locks"]:
        raw = (REPOSITORY_ROOT / lock["path"]).read_bytes()
        assert lock["sha256"] == hashlib.sha256(raw).hexdigest()
        assert lock["byte_length"] == len(raw)


# --- boundaries the corpus permanently holds ----------------------------------


def test_the_corpus_is_source_only_and_package_excluded() -> None:
    scope = MANIFEST["scope"]

    assert scope["source_only"] is True
    assert scope["package_exclusion_required"] is True
    assert scope["source_hashes_are_behavioral_identity"] is False
    assert MANIFEST["replay_contract"]["production_replay_io"] is False
    assert MANIFEST["replay_contract"]["production_lookup"] == "none"
    assert MANIFEST["execution_contract"]["test_only_executor"] == (
        "tests/test_development_history_contract_corpus.py"
    )


def test_the_production_surface_is_unchanged_by_this_corpus() -> None:
    observed = {
        path.relative_to(REPOSITORY_ROOT).as_posix()
        for path in (REPOSITORY_ROOT / "src").rglob("*.py")
    }

    assert len(observed) == PRODUCTION_SOURCE_COUNT
    assert "src/faultatlas/domain/history.py" in observed
    assert "src/faultatlas/domain/history_evidence_link.py" in observed


def test_no_production_module_reads_the_corpus() -> None:
    for path in (REPOSITORY_ROOT / "src").rglob("*.py"):
        assert "reference_corpus" not in path.read_text("utf-8"), path


def test_the_rejection_contract_locks_no_unstable_surface() -> None:
    contract = MANIFEST["rejection_contract"]

    assert contract["error_oracle"] == [
        "failure_category",
        "error_location",
        "error_location_mode",
        "error_type",
    ]
    assert contract["internal_union_branch_labels_locked"] is False
    assert contract["unstable_prose_locked"] is False
    assert contract["coercion"] == "forbidden"
    blob = json.dumps(INVALID["vectors"])
    assert "function-after[" not in blob
    assert "function-before[" not in blob


def test_prefix_mode_is_used_only_for_the_two_discriminatorless_unions() -> None:
    prefixed = [
        v
        for v in INVALID["vectors"]
        if v["expected"]["error_location_mode"] == "prefix"
    ]

    assert prefixed
    for vector in prefixed:
        assert vector["expected"]["error_location"] in (["occurrence"], ["fact"])


def test_the_non_generalizations_are_declared_and_specific() -> None:
    goals = MANIFEST["non_goals"]

    assert len(goals) == len(set(goals)) == 23
    joined = " | ".join(goals)
    for needle in (
        "no ancestry",
        "no historical default-branch substitution",
        "no rename or copy",
        "no generic development event model",
        "no field-level evidence locator",
        "no generic repository or evolution graph owned by S1.P06",
    ):
        assert needle in joined


def test_the_roadmap_names_exactly_one_next_gate() -> None:
    """Two live next-gate claims would let a consumer report the wrong gate.

    Each Slice narrative states the gate that was next when it published, so a
    superseded claim has to be retired rather than left standing beside the
    current one.
    """
    text = (REPOSITORY_ROOT / "docs/roadmap.md").read_text("utf-8")
    claims = [
        line.strip() for line in text.splitlines() if "next and not started" in line
    ]

    assert claims
    for claim in claims:
        assert "`S1.P05.S10`" in claim, claim
        assert "`S1.P05.S09`" not in claim, claim


def test_the_roadmap_records_the_corpus_and_holds_the_phase_state() -> None:
    text = " ".join((REPOSITORY_ROOT / "docs/roadmap.md").read_text("utf-8").split())

    assert "`S1.P05.S09` — Development History Contract Corpus (complete)" in text
    assert "`S1.P05.S10` is next and not started" in text
    assert "`S1.P06` is not eligible to begin" in text
    assert "reference_corpus/contracts/development-history/v1" in text


# --- retained provenance is verified, not asserted ----------------------------


def _resolve_pointer(document: Any, pointer: str) -> Any:
    node = document
    for token in [part for part in pointer.split("/") if part]:
        node = (
            cast(list[Any], node)[int(token)]
            if isinstance(node, list)
            else cast(dict[str, Any], node)[token]
        )
    return node


_SOURCED = [v for v in REPLAY["vectors"] if v["source_pointers"]]


@pytest.mark.parametrize("vector", _SOURCED, ids=[cast(str, v["id"]) for v in _SOURCED])
def test_every_replay_source_pointer_resolves_into_its_replayed_value(
    vector: dict[str, Any],
) -> None:
    """A retained claim must be checkable against the retained bytes.

    Comparing a vector's input to its own expectation proves only that the file
    agrees with itself: a wrong revision digest, pull-request number, path, or
    instant would publish as a retained observation. Each cited field is
    therefore resolved out of the locked acquisition and compared to the exact
    replayed field.
    """
    dump = cast(dict[str, Any], vector["expected"])["semantic_dump"]
    for pointer in cast(list[dict[str, Any]], vector["source_pointers"]):
        assert set(pointer) == {"document_path", "json_pointer", "source_fields"}
        path = REPOSITORY_ROOT / cast(str, pointer["document_path"])
        assert path.is_file(), f"{vector['id']}: {pointer['document_path']}"
        resolved = _resolve_pointer(
            json.loads(path.read_text("utf-8")), cast(str, pointer["json_pointer"])
        )
        fields = cast(dict[str, str], pointer["source_fields"])
        assert fields, f"{vector['id']}: a cited pointer must map at least one field"
        for source_field, replayed_field in fields.items():
            observed = _resolve_pointer(resolved, source_field)
            replayed = _resolve_pointer(dump, replayed_field)
            assert observed == replayed, (
                f"{vector['id']}: {pointer['json_pointer']}{source_field} is "
                f"{observed!r} but the replayed {replayed_field} is {replayed!r}"
            )


def test_only_retained_observations_cite_retained_evidence() -> None:
    """Caller-supplied values must not borrow retained provenance."""
    sourced = 0
    for vector in REPLAY["vectors"]:
        pointers = cast(list[dict[str, Any]], vector["source_pointers"])
        if vector["evidence_classification"] == "retained_normalized_observation":
            assert pointers, f"{vector['id']} claims retained provenance with no source"
            sourced += 1
        else:
            assert not pointers, (
                f"{vector['id']} is caller supplied and must cite no retained location"
            )

    assert sourced == 11


def test_every_cited_document_is_a_locked_artifact() -> None:
    locked = {lock["path"] for lock in REPLAY["artifact_locks"]}

    for vector in REPLAY["vectors"]:
        for pointer in cast(list[dict[str, Any]], vector["source_pointers"]):
            assert pointer["document_path"] in locked, vector["id"]
