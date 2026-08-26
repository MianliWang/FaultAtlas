from __future__ import annotations

import copy
import hashlib
import json
import re
from collections import Counter
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
ALLOWED_MARKERS = (
    "enum_value",
    "indexed_value",
    "instant_value",
    "tuple_value",
    "typed_value",
)
MAX_INDEXED_COUNT = 4097
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
    if marker == "indexed_value":
        spec_indexed = cast(dict[str, Any], payload)
        count = cast(int, spec_indexed["count"])
        assert spec_indexed["target"] == "PullRequestChangedPath"
        assert spec_indexed["template"] == "generated-changed-path"
        assert 0 < count <= MAX_INDEXED_COUNT, f"indexed count out of bounds: {count}"
        return tuple(
            history.PullRequestChangedPath(
                path=revision.GitRepositoryPath(f"generated/path-{index:04d}.py"),
                head_object=revision.GitBlobIdentity(
                    kind=revision.GitObjectKind.BLOB,
                    algorithm=revision.GitHashAlgorithm.SHA1,
                    full_digest=f"{index:040x}",
                ),
                status=history.ChangedPathStatus.MODIFIED,
            )
            for index in range(1, count + 1)
        )
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


def test_the_published_change_set_ceiling_is_covered_on_both_sides() -> None:
    """A corpus that freezes a bounded surface must pin the bound itself."""
    accepted = next(
        v
        for v in VALID["vectors"]
        if v["id"].endswith("change-set.maximum-changed-paths")
    )
    rejected = next(
        v
        for v in INVALID["vectors"]
        if v["id"].endswith("change-set.above-maximum-changed-paths")
    )

    assert accepted["input"]["changed_paths"]["indexed_value"]["count"] == 4096
    assert accepted["expected"]["changed_path_count"] == 4096
    assert rejected["input"]["changed_paths"]["indexed_value"]["count"] == 4097
    assert rejected["expected"]["error_type"] == "too_long"
    assert rejected["expected"]["error_location"] == ["changed_paths"]


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
    if "changed_path_count" in expected:
        # A cardinality probe declares its size rather than a whole dump.
        assert "semantic_dump" not in expected, vector["id"]
        assert len(value.changed_paths) == expected["changed_path_count"]
    else:
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


NON_GENERALIZATIONS = (
    "no complete development-history graph",
    "no generic DevelopmentEvent",
    "no generic relationship graph",
    "no ancestry or reachability semantics",
    "no merge-base semantics",
    "no ahead or behind semantics",
    "no branch containment",
    "no historical default-branch substitution",
    "current default branch is not historical truth",
    "no rename or copy semantics",
    "no complete mutable-ref history",
    "no complete discussion history",
    "no edit or deletion absence claim",
    "no complete historical review state",
    "no timestamp-implied causality",
    "approval does not cause merge",
    "merge does not cause ref deletion",
    "no CI or test correctness",
    "no repair correctness",
    "no FaultInstance semantics",
    "no root cause",
    "no violated invariant",
    "no S1.P09 confidence or review interpretation",
    "no field-level evidence locator",
    "no verification or support strength",
    "no persistence",
    "no production serializer or registry",
    "no production corpus reader",
    "no source ingestion",
    "no Git or GitHub I/O",
    "no retrieval or RAG",
    "generic repository or evolution graph is S5-owned, not S1.P06-owned",
)


def test_the_non_generalizations_are_declared_and_specific() -> None:
    """Merging boundaries hides them: each must stand as its own published claim."""
    goals = cast(list[str], MANIFEST["non_goals"])

    assert len(goals) == len(set(goals)) == 32
    assert list(goals) == list(NON_GENERALIZATIONS)


def test_no_non_generalization_is_a_lexical_variant_of_another() -> None:
    """Splitting one boundary into synonyms would inflate the count."""
    seen: dict[frozenset[str], str] = {}
    for goal in cast(list[str], MANIFEST["non_goals"]):
        key = frozenset(goal.replace("-", " ").split()) - {"no", "or", "is", "not", "a"}
        assert key not in seen, (goal, seen.get(key))
        seen[key] = goal


# --- the derived Markdown tracks the canonical JSON ---------------------------


def test_the_contract_markdown_is_derived_from_the_json_authorities() -> None:
    """A stale projection would misreport a frozen surface."""
    text = (CORPUS / "contract.md").read_text("utf-8")
    summary = MANIFEST["vector_summary"]

    assert text.startswith("# Development History Contract Corpus")
    for entry in MANIFEST["target_symbols"]:
        assert f"`{entry['symbol']}`" in text, entry["symbol"]
        assert f"`{entry['slice_layer']}`" in text
    for module in MANIFEST["scope"]["production_modules"]:
        assert f"`{module}`" in text
    for authority in MANIFEST["scope"]["supporting_authorities_not_owned"]:
        assert f"`{authority}`" in text
    for classification in MANIFEST["replay_contract"]["classifications"]:
        assert f"`{classification}`" in text, classification
    for goal in MANIFEST["non_goals"]:
        assert goal in text, goal
    for entry in MANIFEST["source_decisions"]:
        assert entry["sha256"] in text
    assert f"**{summary['valid']['count']}**" in text
    assert f"**{summary['invalid']['count']}**" in text
    assert f"**{summary['replay']['count']}**" in text
    assert f"{summary['total_vectors']} vectors" in text
    assert f"{summary['fixtures']} declared fixtures" in text


def test_the_contract_markdown_reports_the_repaired_surfaces() -> None:
    """The derived prose must track the surfaces this repair added."""
    text = (CORPUS / "contract.md").read_text("utf-8")
    contract = MANIFEST["replay_contract"]

    for position, literal in cast(
        dict[str, str], contract["retained_role_source_positions"]
    ).items():
        assert f"`{position}` implies `{literal}`" in text, position
    for entry in cast(list[dict[str, str]], MANIFEST["s07_forbidden_extra_ledger"]):
        assert f"`{entry['extra_key']}`" in text, entry["extra_key"]
        assert entry["published_non_claim"] in text, entry["published_non_claim"]

    authority = MANIFEST["effective_governance"]["authority_totals"]
    assert f"S1.P05.S08 {authority['S1.P05.S08']}" in text
    assert f"S1.P05.S08.C01 {authority['S1.P05.S08.C01']}" in text


def test_the_contract_markdown_reports_the_effective_governance_totals() -> None:
    text = (CORPUS / "contract.md").read_text("utf-8")
    governance = MANIFEST["effective_governance"]

    assert f"inherited {governance['inherited_subject_count']}" in text
    assert "self_owned_open 0" in text
    assert f"split {governance['totals']['disposition']['split']}" in text
    assert (
        f"carried_forward {governance['totals']['disposition']['carried_forward']}"
        in text
    )
    for owner, count in governance["totals"]["immediate_owner"].items():
        assert f"{owner} {count}" in text, owner


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
        assert set(pointer) <= {
            "document_path",
            "json_pointer",
            "role_implications",
            "source_fields",
        }
        assert {"document_path", "json_pointer", "source_fields"} <= set(pointer)
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


def _leaves(node: Any, prefix: str = "") -> list[tuple[str, Any]]:
    if isinstance(node, dict):
        return [
            leaf
            for key, value in cast(dict[str, Any], node).items()
            for leaf in _leaves(value, f"{prefix}/{key}")
        ]
    if isinstance(node, list):
        return [
            leaf
            for index, value in enumerate(cast(list[Any], node))
            for leaf in _leaves(value, f"{prefix}/{index}")
        ]
    return [(prefix, node)]


ROLE_SUFFIX = "/role_assignment/role"
REVISION_SUFFIX = "/role_assignment/revision/full_digest"


def _is_declared_constant(path: str, value: Any) -> bool:
    """A constant is exempt where it is declared, not wherever its value appears.

    Matching by value alone lets any retained leaf escape provenance simply by
    being changed to the constant, so the exemption is scoped to the semantic
    path the constant actually occupies.
    """
    constants = cast(
        dict[str, str], MANIFEST["replay_contract"]["retained_case_constants"]
    )
    return (
        path.endswith(constants["provider_leaf_suffix"])
        and value == constants["provider"]
    )


def _unsourced_leaves(vector: dict[str, Any]) -> list[tuple[str, Any]]:
    contract = MANIFEST["replay_contract"]
    structural = set(cast(list[str], contract["structural_leaf_names"]))
    pointers = cast(list[dict[str, Any]], vector["source_pointers"])
    mapped = {
        replayed
        for pointer in pointers
        for replayed in cast(dict[str, str], pointer["source_fields"]).values()
    } | {
        replayed
        for pointer in pointers
        for replayed in cast(
            dict[str, str], pointer.get("role_implications", {})
        ).values()
    }
    return [
        (path, value)
        for path, value in _leaves(vector["expected"]["semantic_dump"])
        if path.rsplit("/", 1)[-1] not in structural
        and path not in mapped
        and not _is_declared_constant(path, value)
    ]


def _role_implication_failures(vector: dict[str, Any]) -> list[tuple[str, ...]]:
    """Every declared role must equal the role its source position implies."""
    table = cast(
        dict[str, str], MANIFEST["replay_contract"]["retained_role_source_positions"]
    )
    dump = cast(dict[str, Any], vector["expected"])["semantic_dump"]
    failures: list[tuple[str, ...]] = []
    for pointer in cast(list[dict[str, Any]], vector["source_pointers"]):
        implications = cast(dict[str, str], pointer.get("role_implications", {}))
        for source_field, role_path in implications.items():
            position = f"{pointer['json_pointer']}{source_field}"
            implied = table.get(position)
            observed = _resolve_pointer(dump, role_path)
            if implied is None or implied != observed:
                failures.append((position, role_path, str(implied), str(observed)))
                continue
            # The implication must ride the same mapping that supplies the
            # revision it names. Without this, a role could cite one source
            # position while its digest was read from another, and the retained
            # head revision would publish as a base binding.
            sources = cast(dict[str, str], pointer["source_fields"])
            if not role_path.endswith(ROLE_SUFFIX):
                failures.append((position, role_path, "malformed-role-path", ""))
            elif sources.get(source_field) != (
                role_path[: -len(ROLE_SUFFIX)] + REVISION_SUFFIX
            ):
                failures.append(
                    (
                        position,
                        role_path,
                        "uncoupled-from-revision-mapping",
                        str(sources.get(source_field)),
                    )
                )
    return failures


@pytest.mark.parametrize("vector", _SOURCED, ids=[cast(str, v["id"]) for v in _SOURCED])
def test_every_retained_data_leaf_is_sourced(vector: dict[str, Any]) -> None:
    """Sourcing part of a retained value leaves the rest free to drift.

    A single mapped field is not provenance for the whole value: an embedded
    pull request, repository, or revision that no pointer covers can be changed
    in both input and expectation and still read as retained. Every leaf must
    therefore be sourced, be a contract-level structural discriminator, or be a
    declared constant of the retained case.
    """
    unsourced = _unsourced_leaves(vector)
    assert not unsourced, f"{vector['id']}: unsourced retained leaves {unsourced}"


@pytest.mark.parametrize("vector", _SOURCED, ids=[cast(str, v["id"]) for v in _SOURCED])
def test_every_retained_role_is_implied_by_its_source_position(
    vector: dict[str, Any],
) -> None:
    """A role is what the retained comparison called it, not what the corpus says.

    `base` and `head` are the only leaves that distinguish one binding from the
    other, so a swapped role publishes a retained base revision as a head
    binding. The literal is therefore derived from the position the digest was
    read from rather than trusted from the vector.
    """
    failures = _role_implication_failures(vector)
    assert not failures, f"{vector['id']}: {failures}"


@pytest.mark.parametrize("vector", _SOURCED, ids=[cast(str, v["id"]) for v in _SOURCED])
def test_every_retained_role_leaf_declares_an_implication(
    vector: dict[str, Any],
) -> None:
    """A role leaf that declares nothing would silently escape the rule."""
    declared = {
        role_path
        for pointer in cast(list[dict[str, Any]], vector["source_pointers"])
        for role_path in cast(
            dict[str, str], pointer.get("role_implications", {})
        ).values()
    }
    present = {
        path
        for path, _ in _leaves(vector["expected"]["semantic_dump"])
        if path.rsplit("/", 1)[-1] == "role"
    }
    assert declared == present, vector["id"]


def _canonicalization_name(recorded: Any) -> str:
    """Retained artifacts record canonicalization as a scalar or as a block.

    The acquisition stores the name directly; the additive correction stores a
    structured block that carries the same name alongside its rules. Only the
    published `EvidenceCanonicalization` value is taken from either shape.
    """
    if isinstance(recorded, str):
        return recorded
    return cast(dict[str, str], recorded)["name"]


def _reference_for_lock(lock: dict[str, Any]) -> dict[str, Any]:
    """Build the complete published reference from the locked bytes alone."""
    raw = (REPOSITORY_ROOT / cast(str, lock["path"])).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == lock["sha256"], lock["lock_id"]
    assert len(raw) == lock["byte_length"], lock["lock_id"]

    recorded = cast(dict[str, Any], json.loads(raw.decode("utf-8"))["format"])
    reference = evidence.DurableEvidenceRecordReference.model_validate_json(
        json.dumps(
            {
                "byte_length": len(raw),
                "canonicalization": _canonicalization_name(
                    recorded["canonicalization"]
                ),
                "format_name": recorded["name"],
                "format_version": recorded["version"],
                "sha256": hashlib.sha256(raw).hexdigest(),
            }
        )
    )
    return cast(dict[str, Any], _dump(reference))


def _locked_references() -> dict[str, dict[str, Any]]:
    return {
        cast(str, lock["lock_id"]): _reference_for_lock(lock)
        for lock in cast(list[dict[str, Any]], REPLAY["artifact_locks"])
    }


def _association_reference_failures(document: dict[str, Any]) -> list[tuple[str, str]]:
    """Every association must reproduce its locked artifact's whole reference."""
    references = _locked_references()
    failures: list[tuple[str, str]] = []
    for vector in cast(list[dict[str, Any]], document["vectors"]):
        lock_id = cast(str, vector["evidence_record_lock"])
        if vector["target"] != "PullRequestHistoryFactEvidenceLink":
            if lock_id:
                failures.append(
                    (cast(str, vector["id"]), "non-association-declares-lock")
                )
            continue
        if lock_id not in references:
            failures.append((cast(str, vector["id"]), "unknown-artifact-lock"))
            continue
        expected = references[lock_id]
        if vector["expected"]["semantic_dump"]["evidence_record"] != expected:
            failures.append((cast(str, vector["id"]), "expectation-differs-from-lock"))
        if vector["input"]["evidence_record"] != expected:
            failures.append((cast(str, vector["id"]), "input-differs-from-lock"))
    return failures


def test_the_derived_reference_accounts_for_every_published_field() -> None:
    """A subset comparison would leave the remaining fields free to lie."""
    published = set(evidence.DurableEvidenceRecordReference.model_fields)

    assert published == {
        "byte_length",
        "canonicalization",
        "format_name",
        "format_version",
        "schema_version",
        "sha256",
    }
    for reference in _locked_references().values():
        assert set(reference) == published


def test_every_replayed_association_equals_its_locked_artifact_reference() -> None:
    """A record reference is a retained claim and must be checkable as one.

    An association cites no source pointer, so nothing else ties its
    `evidence_record` to anything real. Binding only the content address left
    `format_name`, `format_version`, and `canonicalization` free to describe the
    locked artifact falsely, so the whole published reference is derived from
    the locked bytes and compared entire.
    """
    assert not _association_reference_failures(REPLAY)

    bound = Counter(
        cast(str, vector["evidence_record_lock"])
        for vector in REPLAY["vectors"]
        if vector["target"] == "PullRequestHistoryFactEvidenceLink"
    )
    assert dict(bound) == {
        "acquisition:run-0001": 11,
        "correction:s04-c01-acquisition-closure": 1,
    }


def test_no_retained_leaf_takes_the_constant_value_outside_its_declared_path() -> None:
    """Otherwise the exemption is a hole any leaf can climb through."""
    constants = cast(
        dict[str, str], MANIFEST["replay_contract"]["retained_case_constants"]
    )
    for vector in REPLAY["vectors"]:
        for path, value in _leaves(vector["expected"]["semantic_dump"]):
            if value == constants["provider"]:
                assert path.endswith(constants["provider_leaf_suffix"]), (
                    vector["id"],
                    path,
                )


def test_the_declared_structural_and_constant_leaves_are_exact() -> None:
    contract = MANIFEST["replay_contract"]

    assert contract["structural_leaf_names"] == [
        "algorithm",
        "kind",
        "schema_version",
    ]
    assert "role" not in contract["structural_leaf_names"], (
        "a retained role is semantic: it must be bound to a source position"
    )
    assert contract["retained_role_source_positions"] == {
        "/observations/comparison/base_sha": "base",
        "/observations/comparison/head_sha": "head",
        "/observations/pr/attempts/0/bracket_a/head/sha": "head",
    }
    assert contract["retained_case_constants"]["provider"] == "github"
    assert (
        contract["retained_case_constants"]["provider_leaf_suffix"]
        == "/repository_identity/provider"
    )
    assert contract["retained_case_constants"]["rationale"]


def test_every_cited_document_is_a_locked_artifact() -> None:
    locked = {lock["path"] for lock in REPLAY["artifact_locks"]}

    for vector in REPLAY["vectors"]:
        for pointer in cast(list[dict[str, Any]], vector["source_pointers"]):
            assert pointer["document_path"] in locked, vector["id"]


# --- the role rule survives a fully re-sealed corpus --------------------------


def _canonical(document: Any) -> bytes:
    return (
        json.dumps(document, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        + "\n"
    ).encode("utf-8")


@pytest.mark.parametrize(
    ("vector_id", "before", "after"),
    (
        ("history.replay.role-binding.base", "base", "head"),
        ("history.replay.role-binding.head", "head", "base"),
    ),
)
def test_a_digest_consistent_role_swap_is_still_refused(
    vector_id: str, before: str, after: str
) -> None:
    """Re-sealing every digest must not launder a swapped role.

    An author who swaps a role in both the input and the expectation and then
    regenerates the vector digest, its sidecar, and the manifest reference
    leaves nothing inconsistent to notice. The retained base revision would
    publish as a head binding. The swap must fail on provenance, so this probe
    performs the whole re-seal and asserts the semantic rule still rejects it.
    """
    document = json.loads((CORPUS / "replay-vectors.json").read_text("utf-8"))
    vector = next(v for v in document["vectors"] if v["id"] == vector_id)
    assert vector["input"]["role_assignment"]["role"] == before
    vector["input"]["role_assignment"]["role"] = after
    vector["expected"]["semantic_dump"]["role_assignment"]["role"] = after

    resealed = hashlib.sha256(_canonical(document)).hexdigest()
    sealed = next(
        entry
        for entry in MANIFEST["corpus_files"]
        if entry["filename"] == "replay-vectors.json"
    )
    assert resealed != sealed["sha256"], "the mutation must really change the bytes"

    # Every digest now agrees with the mutated bytes, so nothing below can pass
    # merely because a hash failed to match.
    assert _role_implication_failures(vector) == [
        (
            f"/observations/comparison/{before}_sha",
            "/role_assignment/role",
            before,
            after,
        )
    ]


def test_dropping_a_role_implication_leaves_the_role_unsourced() -> None:
    """The rule must not be escapable by declaring nothing at all."""
    vector = copy.deepcopy(
        next(
            v
            for v in REPLAY["vectors"]
            if v["id"] == "history.replay.role-binding.base"
        )
    )
    for pointer in cast(list[dict[str, Any]], vector["source_pointers"]):
        pointer.pop("role_implications", None)

    assert not _role_implication_failures(vector)
    assert [path for path, _ in _unsourced_leaves(vector)] == ["/role_assignment/role"]


def test_no_retained_role_leaf_relies_on_the_structural_exemption() -> None:
    """Restoring `role` to the exemption set would silently reopen the hole."""
    exempt = set(cast(list[str], MANIFEST["replay_contract"]["structural_leaf_names"]))
    roles = {
        path
        for vector in _SOURCED
        for path, _ in _leaves(vector["expected"]["semantic_dump"])
        if path.rsplit("/", 1)[-1] == "role"
    }

    assert roles, "the retained corpus must carry role leaves to bind"
    assert "role" not in exempt


# --- a caller-supplied value inherits the provenance it embeds ----------------


def test_every_embedded_fact_equals_its_bound_retained_vector() -> None:
    """Compositions and associations cite no source, so they must inherit one.

    A link and a change set carry retained bindings inside them while declaring
    no retained location of their own. Without this equality their nested roles,
    revisions, and paths could drift away from the sourced vectors they claim to
    reuse.
    """
    by_id = {cast(str, v["id"]): v for v in REPLAY["vectors"]}
    checked = 0
    for vector in REPLAY["vectors"]:
        embedded = cast(dict[str, str], vector["embedded_facts"])
        for pointer, source_id in embedded.items():
            assert source_id in by_id, (vector["id"], source_id)
            assert (
                _resolve_pointer(vector["expected"]["semantic_dump"], pointer)
                == by_id[source_id]["expected"]["semantic_dump"]
            ), (vector["id"], pointer)
            checked += 1

    assert checked == 17


def test_every_caller_supplied_replay_binds_its_embedded_facts() -> None:
    for vector in REPLAY["vectors"]:
        if vector["evidence_classification"] == "retained_normalized_observation":
            assert not vector["embedded_facts"], vector["id"]
        else:
            assert vector["embedded_facts"], vector["id"]


# --- every vector occupies exactly one declared semantic partition ------------


def test_every_vector_declares_a_globally_unique_semantic_partition() -> None:
    """Vector-id uniqueness is naming, not coverage.

    Two ids may still name one boundary, which is how four spellings of evidence
    localization once occupied four partitions. The partition key is therefore
    declared per vector and must be globally unique across all three files.
    """
    partitions = [
        cast(str, vector["semantic_partition"])
        for section in (VALID, INVALID, REPLAY)
        for vector in section["vectors"]
    ]

    assert len(partitions) == 167
    assert len(set(partitions)) == 167


def test_each_semantic_partition_is_distinct_from_its_vector_id() -> None:
    for section in (VALID, INVALID, REPLAY):
        for vector in section["vectors"]:
            partition = cast(str, vector["semantic_partition"])
            assert partition
            assert partition != vector["id"], vector["id"]
            assert partition.split("/")[0] == vector["category"], vector["id"]


# --- the eleven forbidden extras protect eleven different non-claims ----------


def test_the_forbidden_extra_ledger_covers_eleven_distinct_non_claims() -> None:
    """Eleven rejections of `extra` are not eleven published boundaries.

    Every entry hits `extra_forbidden`, so the count alone proves nothing. The
    ledger names the non-claim each key protects, and those must all differ.
    """
    ledger = cast(list[dict[str, str]], MANIFEST["s07_forbidden_extra_ledger"])
    invalid_by_id = {cast(str, v["id"]): v for v in INVALID["vectors"]}

    assert len(ledger) == 11
    assert len({entry["extra_key"] for entry in ledger}) == 11
    assert len({entry["published_non_claim"] for entry in ledger}) == 11
    assert len({entry["semantic_partition"] for entry in ledger}) == 11

    for entry in ledger:
        vector = invalid_by_id[entry["vector_id"]]
        assert vector["semantic_partition"] == entry["semantic_partition"]
        assert vector["expected"]["error_type"] == "extra_forbidden"
        assert vector["expected"]["error_location"] == [entry["extra_key"]]
        assert entry["extra_key"] in vector["input"]


def test_evidence_localization_keeps_exactly_one_representative() -> None:
    """`field_path`, `semantic_path`, and `evidence_locator` say the same thing."""
    ledger = cast(list[dict[str, str]], MANIFEST["s07_forbidden_extra_ledger"])
    keys = {entry["extra_key"] for entry in ledger}

    assert "json_pointer" in keys
    assert not keys & {"field_path", "semantic_path", "evidence_locator"}
    localization = [
        entry
        for entry in ledger
        if "localization" in entry["published_non_claim"]
        or "locator" in entry["published_non_claim"]
    ]
    assert len(localization) == 1


# --- the effective governance names which artifact carries each subject -------


def test_the_effective_governance_authority_split_is_recomputed() -> None:
    """Six subjects still stand on S08; six now stand on the C01 correction."""
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
        item["source"]["subject_id"]
        for item in correction["superseded_dispositions"]["items"]
    }

    split = {"S1.P05.S08": 0, "S1.P05.S08.C01": 0}
    for entry in base["inherited_subject_register"]["items"]:
        subject_id = entry["source"]["subject_id"]
        key = "S1.P05.S08.C01" if subject_id in corrected else "S1.P05.S08"
        split[key] += 1

    assert split == {"S1.P05.S08": 6, "S1.P05.S08.C01": 6}
    assert MANIFEST["effective_governance"]["authority_totals"] == split


# --- the record binding is proved by mutation, not by construction ------------


def _resealed_digest(document: Any) -> str:
    return hashlib.sha256(_canonical(document)).hexdigest()


def _sealed_replay_digest() -> str:
    return cast(
        str,
        next(
            entry
            for entry in MANIFEST["corpus_files"]
            if entry["filename"] == "replay-vectors.json"
        )["sha256"],
    )


def _association(document: dict[str, Any], vector_id: str) -> dict[str, Any]:
    return next(v for v in document["vectors"] if v["id"] == vector_id)


REVIEW_ASSOCIATION = "history.replay.evidence-association.review-approval"


def test_a_format_only_mutation_breaks_the_complete_reference() -> None:
    """The content address alone is not the reference.

    Keeping `sha256` and `byte_length` correct while rewriting the format
    metadata leaves a record that addresses the locked artifact but describes a
    different one. Nothing in the digests notices, so the whole-value comparison
    has to.
    """
    document = copy.deepcopy(REPLAY)
    vector = _association(document, REVIEW_ASSOCIATION)
    correct = copy.deepcopy(vector["expected"]["semantic_dump"]["evidence_record"])
    for side in (vector["input"], vector["expected"]["semantic_dump"]):
        record = side["evidence_record"]
        record["format_name"] = "faultatlas-pytest-4412-acquisition-closure-addendum"
        record["format_version"] = "2"
        record["canonicalization"] = "json-sort-keys-compact-utf8-lf-v2"

    # The bytes really change, so a re-seal would hide nothing, and the content
    # address is untouched, so no digest check can be what fails.
    assert _resealed_digest(document) != _sealed_replay_digest()
    for side in (vector["input"], vector["expected"]["semantic_dump"]):
        assert side["evidence_record"]["sha256"] == correct["sha256"]
        assert side["evidence_record"]["byte_length"] == correct["byte_length"]

    assert _association_reference_failures(document) == [
        (REVIEW_ASSOCIATION, "expectation-differs-from-lock"),
        (REVIEW_ASSOCIATION, "input-differs-from-lock"),
    ]


def test_a_fake_content_address_breaks_the_complete_reference() -> None:
    document = copy.deepcopy(REPLAY)
    vector = _association(document, REVIEW_ASSOCIATION)
    for side in (vector["input"], vector["expected"]["semantic_dump"]):
        side["evidence_record"]["sha256"] = "f" * 64
        side["evidence_record"]["byte_length"] = 999

    assert _resealed_digest(document) != _sealed_replay_digest()
    assert _association_reference_failures(document) == [
        (REVIEW_ASSOCIATION, "expectation-differs-from-lock"),
        (REVIEW_ASSOCIATION, "input-differs-from-lock"),
    ]


def test_an_unknown_artifact_lock_is_refused() -> None:
    document = copy.deepcopy(REPLAY)
    _association(document, REVIEW_ASSOCIATION)["evidence_record_lock"] = (
        "acquisition:absent"
    )

    assert _association_reference_failures(document) == [
        (REVIEW_ASSOCIATION, "unknown-artifact-lock")
    ]


def test_an_acquisition_association_bound_to_the_correction_lock_is_refused() -> None:
    """A registered but wrong lock must fail as loudly as an absent one."""
    document = copy.deepcopy(REPLAY)
    vector = _association(document, REVIEW_ASSOCIATION)
    vector["evidence_record_lock"] = "correction:s04-c01-acquisition-closure"

    assert _association_reference_failures(document) == [
        (REVIEW_ASSOCIATION, "expectation-differs-from-lock"),
        (REVIEW_ASSOCIATION, "input-differs-from-lock"),
    ]


def test_the_single_correction_association_binds_to_the_correction_artifact() -> None:
    vector = _association(
        REPLAY, "history.replay.evidence-association.approval-correction-record"
    )
    correction = _locked_references()["correction:s04-c01-acquisition-closure"]

    assert vector["evidence_record_lock"] == "correction:s04-c01-acquisition-closure"
    assert vector["expected"]["semantic_dump"]["evidence_record"] == correction
    assert (
        correction["sha256"] != _locked_references()["acquisition:run-0001"]["sha256"]
    )


# --- category inventories are counted, never declared -------------------------


def _category_histogram(section: dict[str, Any]) -> dict[str, int]:
    """Counted from each vector's own category field, not from any projection."""
    return dict(
        sorted(Counter(cast(str, v["category"]) for v in section["vectors"]).items())
    )


FAMILIES = (("valid", "VALID"), ("invalid", "INVALID"), ("replay", "REPLAY"))


def _sections(
    valid: dict[str, Any], invalid: dict[str, Any], replay: dict[str, Any]
) -> dict[str, dict[str, Any]]:
    return {"valid": valid, "invalid": invalid, "replay": replay}


def _markdown_category_table(text: str) -> dict[str, tuple[int, int, int]]:
    rows: dict[str, tuple[int, int, int]] = {}
    for line in text.splitlines():
        found = re.match(
            r"^\| `([a-z-]+)` \| (\d+) \| (\d+) \| (\d+) \|$", line.strip()
        )
        if found:
            rows[found.group(1)] = (
                int(found.group(2)),
                int(found.group(3)),
                int(found.group(4)),
            )
    return rows


def _manifest_histogram_failures(
    manifest: dict[str, Any], sections: dict[str, dict[str, Any]]
) -> list[tuple[str, str]]:
    summary = cast(dict[str, Any], manifest["vector_summary"])
    failures: list[tuple[str, str]] = []
    for family, section in sections.items():
        derived = _category_histogram(section)
        if summary[family]["categories"] != derived:
            failures.append((family, "manifest-categories-differ"))
        if summary[family]["count"] != sum(derived.values()):
            failures.append((family, "manifest-count-differs"))
    return failures


def _markdown_histogram_failures(
    text: str, sections: dict[str, dict[str, Any]]
) -> list[tuple[str, str]]:
    table = _markdown_category_table(text)
    derived = {family: _category_histogram(s) for family, s in sections.items()}
    families = set(derived["valid"]) | set(derived["invalid"]) | set(derived["replay"])
    failures: list[tuple[str, str]] = []
    if set(table) != families:
        failures.append(("*", "markdown-family-set-differs"))
    for family in sorted(families & set(table)):
        expected = (
            derived["valid"].get(family, 0),
            derived["invalid"].get(family, 0),
            derived["replay"].get(family, 0),
        )
        if table[family] != expected:
            failures.append((family, "markdown-row-differs"))
    return failures


def test_the_manifest_category_inventory_is_derived_from_the_vectors() -> None:
    """Totals can balance while the families underneath them are wrong.

    A vector moved between categories keeps every count summing to 167, so the
    per-family histogram is recomputed from the vectors themselves and compared
    entry by entry rather than in aggregate.
    """
    assert not _manifest_histogram_failures(MANIFEST, _sections(VALID, INVALID, REPLAY))

    summary = MANIFEST["vector_summary"]
    assert summary["valid"]["count"] == 48
    assert summary["invalid"]["count"] == 95
    assert summary["replay"]["count"] == 24
    assert summary["total_vectors"] == 167


def test_the_contract_markdown_category_table_is_derived_from_the_vectors() -> None:
    """Two families with equal counts must not be swappable unnoticed."""
    text = (CORPUS / "contract.md").read_text("utf-8")

    assert _markdown_category_table(text), "the family table must be parseable"
    assert not _markdown_histogram_failures(text, _sections(VALID, INVALID, REPLAY))


def test_a_category_move_breaks_the_derived_inventory() -> None:
    """The reproduced finding, kept permanently.

    Moving a vector to another family while updating its partition prefix keeps
    every existing consistency check satisfied and every total unchanged.
    """
    invalid = copy.deepcopy(INVALID)
    moved = next(
        v
        for v in invalid["vectors"]
        if v["id"] == "history.invalid.change-set.duplicate-path"
    )
    moved["category"] = "changed-path"
    moved["semantic_partition"] = "changed-path/rejects/duplicate-path"

    assert _resealed_digest(invalid) != next(
        entry["sha256"]
        for entry in MANIFEST["corpus_files"]
        if entry["filename"] == "invalid-vectors.json"
    )
    assert len(invalid["vectors"]) == 95, "the totals still balance"

    sections = _sections(VALID, invalid, REPLAY)
    assert _manifest_histogram_failures(MANIFEST, sections) == [
        ("invalid", "manifest-categories-differ")
    ]
    text = (CORPUS / "contract.md").read_text("utf-8")
    assert sorted(_markdown_histogram_failures(text, sections)) == [
        ("change-set", "markdown-row-differs"),
        ("changed-path", "markdown-row-differs"),
    ]


def test_updating_only_the_manifest_leaves_the_markdown_stale() -> None:
    """Repairing one projection must not silence the other."""
    invalid = copy.deepcopy(INVALID)
    moved = next(
        v
        for v in invalid["vectors"]
        if v["id"] == "history.invalid.change-set.duplicate-path"
    )
    moved["category"] = "changed-path"
    moved["semantic_partition"] = "changed-path/rejects/duplicate-path"

    manifest = copy.deepcopy(MANIFEST)
    manifest["vector_summary"]["invalid"]["categories"] = _category_histogram(invalid)

    sections = _sections(VALID, invalid, REPLAY)
    assert not _manifest_histogram_failures(manifest, sections)
    text = (CORPUS / "contract.md").read_text("utf-8")
    assert _markdown_histogram_failures(text, sections), (
        "the derived Markdown must still report the stale inventory"
    )
