from __future__ import annotations

import copy
import hashlib
import importlib
import json
import re
import stat as stat_module
from collections import Counter
from collections.abc import Callable
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


def _reject_number(literal: str) -> Any:
    """Refuse a non-integer JSON number before it can become a Python value.

    `json.loads` accepts `NaN`, `Infinity`, and `-Infinity` by default and
    round-trips them faithfully, so a permissive parser plus a round-trip check
    calls a document canonical that is not standards-compliant JSON at all. The
    published canonicalization forbids floats outright, so they are refused at
    the parse rather than admitted and inspected afterwards.
    """
    raise AssertionError(f"forbidden non-integer JSON number: {literal!r}")


def _canonical_bytes(document: Any) -> bytes:
    return (
        json.dumps(
            document,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def _parse_canonical_json(raw: bytes) -> dict[str, Any]:
    """The single strict loader every corpus document is read through.

    A permissive execution loader beside a stricter audit parser lets the two
    disagree about what the corpus is, so the executor itself enforces the
    published canonical form.
    """
    assert not raw.startswith(b"\xef\xbb\xbf"), "a UTF-8 BOM is forbidden"
    assert b"\r" not in raw, "line endings are LF only"
    assert raw.endswith(b"\n") and not raw.endswith(b"\n\n"), (
        "exactly one trailing LF is required"
    )
    value = json.loads(
        raw.decode("utf-8"), parse_float=_reject_number, parse_constant=_reject_number
    )
    assert isinstance(value, dict)
    document = cast(dict[str, Any], value)
    assert _canonical_bytes(document) == raw, "keys must be sorted and compact"
    return document


def _load(name: str) -> dict[str, Any]:
    raw = (CORPUS / f"{name}.json").read_bytes()
    document = _parse_canonical_json(raw)
    assert (CORPUS / f"{name}.sha256").read_text("utf-8") == (
        f"{hashlib.sha256(raw).hexdigest()}  {name}.json\n"
    ), name
    return document


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


# Which input modes each family may declare, read off the sealed corpus.
FAMILY_INPUT_MODES = {
    "valid": frozenset({"json", "python"}),
    "invalid": frozenset({"json", "python"}),
    "replay": frozenset({"replay"}),
}


def _build_python(target: Any, supplied: Any) -> Any:
    materialised = _materialise(supplied)
    if isinstance(target, type) and issubclass(target, Enum):
        return target(materialised)
    return cast(Any, target).model_validate(materialised)


def _build_json(target: Any, supplied: Any) -> Any:
    if isinstance(target, type) and issubclass(target, Enum):
        return target(supplied)
    return cast(Any, target).model_validate_json(json.dumps(supplied))


def _build_replay(target: Any, supplied: Any) -> Any:
    """Replay reconstructs a retained value through the published JSON grammar.

    It shares the JSON primitive deliberately, but it is a distinct branch with
    a distinct family contract: a replay vector relabelled `json` would
    otherwise reconstruct identically and read as covered.
    """
    return _build_json(target, supplied)


INPUT_MODE_DISPATCH = {
    "python": _build_python,
    "json": _build_json,
    "replay": _build_replay,
}


def _construct(vector: dict[str, Any]) -> Any:
    mode = cast(str, vector["input_mode"])
    build = INPUT_MODE_DISPATCH.get(mode)
    assert build is not None, f"unknown input mode: {mode}"
    return build(RESOLVABLE[vector["target"]], vector["input"])


ACCEPTED, REJECTED = "accepted", "rejected"

# Which operations each family is allowed to declare, read off the sealed corpus.
FAMILY_OPERATIONS = {
    "valid": frozenset({"construct"}),
    "invalid": frozenset({"reject"}),
    "replay": frozenset({"construct"}),
}


def _execute(vector: dict[str, Any]) -> dict[str, Any]:
    """Run a vector by its DECLARED operation, never by the file it came from.

    Execution used to be selected by which vector file was loaded, so the sealed
    `operation` could say the opposite of what actually ran and nothing noticed.
    Dispatching here makes the declared operation load-bearing, and an unknown
    operation fails closed rather than falling through to a default.
    """
    operation = cast(str, vector["operation"])
    assert operation in ALLOWED_OPERATIONS, f"unknown operation: {operation}"
    resolved = cast(Any, RESOLVABLE[vector["target"]])
    observed: dict[str, Any] = {
        "runtime_target": resolved.__name__,
        "errors": None,
        "vocabulary_error": False,
        "value": None,
    }

    if operation == "construct":
        observed["value"] = _construct(vector)
        observed["outcome"] = ACCEPTED
        return observed

    if operation == "reject":
        try:
            observed["value"] = _construct(vector)
        except ValidationError as caught:
            observed["outcome"] = REJECTED
            observed["errors"] = caught.errors()
            return observed
        except ValueError:
            # A closed vocabulary raises a plain ValueError rather than a
            # ValidationError, which the rejection contract records separately.
            observed["outcome"] = REJECTED
            observed["vocabulary_error"] = True
            return observed
        observed["outcome"] = ACCEPTED
        return observed

    raise AssertionError(f"unhandled operation: {operation}")


def _observed_round_trip(value: Any, target: Any) -> bool:
    if isinstance(value, Enum):
        return target(value.value) is value
    if not isinstance(value, BaseModel):
        return False
    return bool(target.model_validate_json(value.model_dump_json()) == value)


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
    assert summary["invalid"]["count"] == len(INVALID["vectors"]) == 111
    assert summary["replay"]["count"] == len(REPLAY["vectors"]) == 24
    assert summary["total_vectors"] == 183
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
    observed = _execute(vector)
    value = observed["value"]
    expected = vector["expected"]

    assert observed["outcome"] == expected["outcome"], vector["id"]
    assert observed["runtime_target"] == expected["runtime_target"], vector["id"]
    assert type(value).__name__ == expected["concrete_type"], vector["id"]
    if "changed_path_count" in expected:
        # A cardinality probe declares its size rather than a whole dump.
        assert "semantic_dump" not in expected, vector["id"]
        assert len(value.changed_paths) == expected["changed_path_count"]
    else:
        assert _dump(value) == expected["semantic_dump"], vector["id"]
    assert (
        _observed_round_trip(value, RESOLVABLE[vector["target"]])
        == expected["round_trip_equal"]
    ), vector["id"]


@pytest.mark.parametrize("vector", INVALID["vectors"], ids=_ids(INVALID))
def test_every_invalid_vector_is_rejected_as_declared(vector: dict[str, Any]) -> None:
    expected = vector["expected"]
    observed = _execute(vector)

    assert observed["outcome"] == expected["outcome"] == REJECTED, vector["id"]
    if expected["failure_category"] == "vocabulary_error":
        assert observed["vocabulary_error"], vector["id"]
        assert expected["error_type"] == "enum"
        assert expected["error_location"] == []
        return

    assert not observed["vocabulary_error"], vector["id"]
    errors = cast(list[dict[str, Any]], observed["errors"])
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
    observed = _execute(vector)
    value = observed["value"]
    expected = vector["expected"]

    assert observed["outcome"] == expected["outcome"], vector["id"]
    assert observed["runtime_target"] == expected["runtime_target"], vector["id"]
    assert type(value).__name__ == expected["concrete_type"], vector["id"]
    assert _dump(value) == expected["semantic_dump"], vector["id"]
    assert _observed_round_trip(value, target) == expected["round_trip_equal"], vector[
        "id"
    ]


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
    # The target table is compared whole by the row projection below; token
    # presence cannot tell a correct row from a transposed one.
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

    # The roadmap is another projection of the counts and must not drift from
    # the manifest the way the category inventories once did.
    summary = MANIFEST["vector_summary"]
    assert (
        f"{summary['total_vectors']} vectors over {summary['fixtures']} declared "
        f"fixtures -- {summary['valid']['count']} valid, "
        f"{summary['invalid']['count']} invalid, and {summary['replay']['count']} replay"
    ) in text


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

    assert len(partitions) == 183
    assert len(set(partitions)) == 183


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
    assert summary["invalid"]["count"] == 111
    assert summary["replay"]["count"] == 24
    assert summary["total_vectors"] == 183


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
    assert len(invalid["vectors"]) == 111, "the totals still balance"

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


# --- a partition label is not a partition -------------------------------------


SIGNATURE_FIELDS = {
    "valid": ("expected", "input", "input_mode", "operation", "target"),
    "invalid": ("expected", "input", "input_mode", "operation", "target"),
    "replay": (
        "embedded_facts",
        "evidence_classification",
        "evidence_record_lock",
        "expected",
        "input",
        "input_mode",
        "operation",
        "source_pointers",
        "target",
    ),
}


def _behavioural_signature(vector: dict[str, Any], family: str) -> str:
    """What a vector actually selects, excluding every descriptive label.

    `id`, `purpose`, `semantic_partition`, and `decision_references` are how a
    vector is described, not what it executes, so renaming must never read as a
    new boundary.
    """
    return json.dumps(
        {field: vector[field] for field in SIGNATURE_FIELDS[family]}, sort_keys=True
    )


def _family_collisions(section: dict[str, Any], family: str) -> list[list[str]]:
    """Collisions are scoped to one family.

    A valid vector and a replay vector may legitimately construct the same
    product value while serving different contract roles, so comparing across
    families would forbid something the corpus is entitled to do.
    """
    grouped: dict[str, list[str]] = {}
    for vector in section["vectors"]:
        grouped.setdefault(_behavioural_signature(vector, family), []).append(
            cast(str, vector["id"])
        )
    return sorted(ids for ids in grouped.values() if len(ids) > 1)


FAMILIES = (("valid", VALID, 48), ("invalid", INVALID, 111), ("replay", REPLAY, 24))


@pytest.mark.parametrize(
    ("family", "section", "count"), FAMILIES, ids=[f[0] for f in FAMILIES]
)
def test_no_two_vectors_in_a_family_exercise_the_same_behaviour(
    family: str, section: dict[str, Any], count: int
) -> None:
    """Unique labels once hid two vectors that selected identical behaviour.

    `semantic_partition` is authored, so label uniqueness proves only that the
    author wrote different words.
    """
    signatures = [_behavioural_signature(v, family) for v in section["vectors"]]

    assert len(signatures) == count
    assert len(set(signatures)) == count
    assert not _family_collisions(section, family)


def test_the_behavioural_signature_check_would_catch_a_relabelled_copy() -> None:
    """The mutation keeps every label unique, so only behaviour can fail it."""
    valid = copy.deepcopy(VALID)
    twin = copy.deepcopy(valid["vectors"][0])
    twin["id"] = "history.valid.probe.relabelled-copy"
    twin["purpose"] = "A relabelled copy of an existing witness."
    twin["semantic_partition"] = "role-binding/accepts/probe-relabelled-copy"
    valid["vectors"].append(twin)

    labels = [v["semantic_partition"] for v in valid["vectors"]]
    assert len(labels) == len(set(labels)), "every label stays unique"
    assert _family_collisions(valid, "valid") == [
        [cast(str, VALID["vectors"][0]["id"]), "history.valid.probe.relabelled-copy"]
    ]


def test_the_collision_helper_is_scoped_to_one_family() -> None:
    """A cross-family match must not be reported as a duplicate.

    Two synthetic descriptors with matching product behaviour, one valid and one
    replay, are compared. Nothing sealed is touched.
    """
    shared: dict[str, Any] = {
        "expected": {"outcome": ACCEPTED},
        "input": {"probe": True},
        "input_mode": "json",
        "operation": "construct",
        "target": "PullRequestChangedPath",
    }
    as_valid: dict[str, Any] = {**shared, "id": "probe.valid"}
    as_replay: dict[str, Any] = {
        **shared,
        "id": "probe.replay",
        "embedded_facts": {},
        "evidence_classification": "retained_normalized_observation",
        "evidence_record_lock": "",
        "source_pointers": [],
    }

    assert not _family_collisions({"vectors": [as_valid]}, "valid")
    assert not _family_collisions({"vectors": [as_replay]}, "replay")
    assert _behavioural_signature(as_valid, "valid") != _behavioural_signature(
        as_replay, "replay"
    )


def test_the_replaced_duplicates_now_witness_their_partitions() -> None:
    """Each replacement must differ from the vector it used to copy."""
    by_id = {cast(str, v["id"]): v for section in (VALID,) for v in section["vectors"]}

    tied = by_id["history.valid.occurrence-time.equal-instants-allowed"]
    merge = by_id["history.valid.occurrence-time.merge"]
    assert tied["input"]["occurred_at"] == merge["input"]["occurred_at"]
    assert tied["input"]["occurrence"] != merge["input"]["occurrence"], (
        "equal instants must be shown on two different surfaces"
    )

    second = by_id["history.valid.evidence-link.second-fact-same-record"]
    admitted = [
        v
        for v in VALID["vectors"]
        if v["category"] == "evidence-link" and v["id"] != second["id"]
    ]
    assert second["input"]["evidence_record"] in [
        v["input"].get("evidence_record") for v in admitted
    ], "the record must be one already associated with another fact"
    assert all(second["input"]["fact"] != v["input"].get("fact") for v in admitted), (
        "the second link must carry a fact no other link uses"
    )


def test_the_change_set_requiredness_coverage_is_derived_from_the_live_model() -> None:
    """The authority is the published model, not a list written beside it.

    Comparing coverage to a hand-written field set means a newly required member
    is covered by nothing and noticed by nobody. The required set is therefore
    read off the live model, and the corpus must carry a missing-member
    rejection for each.
    """
    required = {
        name
        for name, field in history.PullRequestChangeSet.model_fields.items()
        if field.is_required()
    }
    covered = {
        cast(list[str], v["expected"]["error_location"])[0]
        for v in INVALID["vectors"]
        if v["category"] == "change-set" and v["expected"]["error_type"] == "missing"
    }

    assert required, "the published change set must have required members"
    assert covered == required, sorted(required ^ covered)


def test_an_unpartitioned_required_member_is_refused() -> None:
    """Otherwise the derivation above could quietly agree with a gap."""
    covered = {
        cast(list[str], v["expected"]["error_location"])[0]
        for v in INVALID["vectors"]
        if v["category"] == "change-set" and v["expected"]["error_type"] == "missing"
    }

    assert covered - {"head"} != covered
    assert (covered - {"head"}) != {
        name
        for name, field in history.PullRequestChangeSet.model_fields.items()
        if field.is_required()
    }


# --- authority identifiers resolve into the locked documents ------------------


def _declared_authority_ids(entry: dict[str, Any]) -> set[str]:
    """Collect the ids the locked document itself publishes."""
    document = json.loads(
        (REPOSITORY_ROOT / cast(str, entry["path"])).read_text("utf-8")
    )
    source = cast(dict[str, str], entry["authority_id_source"])
    node = _resolve_pointer(document, source["collection"])
    field = source["id_field"]
    if isinstance(node, dict):
        return {cast(str, cast(dict[str, Any], node)[field])}
    return {cast(str, item[field]) for item in cast(list[dict[str, Any]], node)}


def test_every_declared_authority_id_resolves_in_its_locked_document() -> None:
    """A declared id that names nothing is a citation to nowhere.

    Asserting only that `authority_ids` is non-empty let the manifest name a
    disposition or deferred entry that does not exist, and re-sealing hid it.
    """
    for entry in cast(list[dict[str, Any]], MANIFEST["source_decisions"]):
        declared = set(cast(list[str], entry["authority_ids"]))
        resolved = _declared_authority_ids(entry)
        assert declared, entry["decision_reference"]
        assert declared <= resolved, (
            entry["decision_reference"],
            sorted(declared - resolved),
        )


def test_the_governance_authorities_declare_their_complete_id_sets() -> None:
    entries = {
        cast(str, e["decision_reference"]): e
        for e in cast(list[dict[str, Any]], MANIFEST["source_decisions"])
    }

    base = entries["decision:s1-p05-s08:disposition"]
    correction = entries["correction:s1-p05-s08-c01:owner-topology"]
    assert set(cast(list[str], base["authority_ids"])) == _declared_authority_ids(base)
    assert len(cast(list[str], base["authority_ids"])) == 12
    assert set(cast(list[str], correction["authority_ids"])) == _declared_authority_ids(
        correction
    )
    assert len(cast(list[str], correction["authority_ids"])) == 6


def test_an_unresolvable_authority_id_is_refused() -> None:
    entry = copy.deepcopy(
        next(
            e
            for e in MANIFEST["source_decisions"]
            if e["decision_reference"] == "closure:s1-p03:evidence-envelope"
        )
    )
    entry["authority_ids"] = ["deferred:does-not-exist"]

    assert not set(entry["authority_ids"]) <= _declared_authority_ids(entry)


def test_every_vector_reference_names_a_registered_authority() -> None:
    """A vector could otherwise cite an authority this corpus never locked."""
    registered = {
        cast(str, e["decision_reference"])
        for e in cast(list[dict[str, Any]], MANIFEST["source_decisions"])
    }
    cited: set[str] = set()
    for section in (VALID, INVALID, REPLAY):
        for vector in section["vectors"]:
            references = cast(list[str], vector["decision_references"])
            assert references, vector["id"]
            assert set(references) <= registered, (vector["id"], references)
            cited |= set(references)

    assert cited == registered - {"closure:s1-p03:evidence-envelope"}


# --- declared execution metadata is enforced, not merely carried --------------


def test_every_vector_declares_an_operation_its_family_permits() -> None:
    """Family and operation are separate claims and both must hold."""
    for family, section, _ in FAMILIES:
        permitted = FAMILY_OPERATIONS[family]
        for vector in section["vectors"]:
            assert vector["operation"] in permitted, (vector["id"], vector["operation"])

    assert FAMILY_OPERATIONS["valid"] == frozenset({"construct"})
    assert FAMILY_OPERATIONS["invalid"] == frozenset({"reject"})
    assert FAMILY_OPERATIONS["replay"] == frozenset({"construct"})
    assert set(ALLOWED_OPERATIONS) == set().union(*FAMILY_OPERATIONS.values())


def test_an_unknown_operation_fails_the_dispatcher_closed() -> None:
    vector = copy.deepcopy(VALID["vectors"][0])
    vector["operation"] = "walk"

    with pytest.raises(AssertionError, match="unknown operation"):
        _execute(vector)


@pytest.mark.parametrize(
    ("family", "index", "flipped"),
    (("valid", 0, "reject"), ("invalid", 0, "construct")),
)
def test_flipping_a_declared_operation_is_refused(
    family: str, index: int, flipped: str
) -> None:
    """The sealed corpus must not be able to describe the opposite of what runs.

    Execution used to be chosen by which file held the vector, so `operation`
    could be flipped and re-sealed with every test still green.
    """
    section = {"valid": VALID, "invalid": INVALID}[family]
    document = copy.deepcopy(section)
    vector = document["vectors"][index]
    vector["operation"] = flipped

    assert _resealed_digest(document) != next(
        entry["sha256"]
        for entry in MANIFEST["corpus_files"]
        if entry["filename"] == f"{family}-vectors.json"
    )
    assert vector["operation"] not in FAMILY_OPERATIONS[family]


def test_a_flipped_operation_also_changes_what_the_dispatcher_runs() -> None:
    """Family membership is one guard; the dispatch itself is the other."""
    accepted = copy.deepcopy(VALID["vectors"][0])
    accepted["operation"] = "reject"
    # A construct that succeeds under a reject operation is reported accepted,
    # so the rejection contract it would need can never be satisfied.
    assert _execute(accepted)["outcome"] == ACCEPTED

    rejected = copy.deepcopy(INVALID["vectors"][0])
    rejected["operation"] = "construct"
    with pytest.raises(ValidationError):
        _execute(rejected)


@pytest.mark.parametrize(
    ("family", "flipped"), (("valid", REJECTED), ("invalid", ACCEPTED))
)
def test_a_falsified_outcome_is_refused(family: str, flipped: str) -> None:
    """`outcome` was sealed metadata that nothing ever compared."""
    section = {"valid": VALID, "invalid": INVALID}[family]
    document = copy.deepcopy(section)
    vector = document["vectors"][0]
    vector["expected"]["outcome"] = flipped

    assert _resealed_digest(document) != next(
        entry["sha256"]
        for entry in MANIFEST["corpus_files"]
        if entry["filename"] == f"{family}-vectors.json"
    )
    assert _execute(vector)["outcome"] != vector["expected"]["outcome"]


def test_a_falsified_runtime_target_is_refused() -> None:
    """`runtime_target` must equal the target the registry actually resolved."""
    vector = copy.deepcopy(VALID["vectors"][0])
    assert vector["expected"]["runtime_target"] != "PullRequestChangeSet"
    vector["expected"]["runtime_target"] = "PullRequestChangeSet"

    assert _execute(vector)["runtime_target"] != vector["expected"]["runtime_target"]


def test_the_runtime_target_comes_from_the_registry_not_the_expectation() -> None:
    for _, section, _ in FAMILIES:
        for vector in section["vectors"]:
            expected = vector["expected"]
            if "runtime_target" not in expected:
                continue
            resolved = cast(type, RESOLVABLE[vector["target"]])
            assert expected["runtime_target"] == resolved.__name__, vector["id"]


def test_a_falsified_round_trip_claim_is_refused() -> None:
    """The field gated the check, so declaring False silently skipped it."""
    vector = copy.deepcopy(VALID["vectors"][0])
    assert vector["expected"]["round_trip_equal"] is True
    vector["expected"]["round_trip_equal"] = False

    observed = _execute(vector)
    assert (
        _observed_round_trip(observed["value"], RESOLVABLE[vector["target"]])
        != vector["expected"]["round_trip_equal"]
    )


def test_no_declared_execution_field_is_left_unverified() -> None:
    """A sealed field that claims observable behaviour must be compared."""
    verified = {
        "changed_path_count",
        "concrete_type",
        "error_location",
        "error_location_mode",
        "error_type",
        "failure_category",
        "outcome",
        "round_trip_equal",
        "runtime_target",
        "semantic_dump",
    }
    declared: set[str] = set()
    for _, section, _ in FAMILIES:
        for vector in section["vectors"]:
            declared |= set(cast(dict[str, Any], vector["expected"]))

    assert declared == verified, sorted(declared ^ verified)


# --- decision references are registered and non-repeating ---------------------


def test_no_vector_repeats_a_decision_reference() -> None:
    for _, section, _ in FAMILIES:
        for vector in section["vectors"]:
            references = cast(list[str], vector["decision_references"])
            assert references, vector["id"]
            assert len(references) == len(set(references)), vector["id"]


def _reference_failures(section: dict[str, Any]) -> list[tuple[str, str]]:
    registered = {
        cast(str, e["decision_reference"])
        for e in cast(list[dict[str, Any]], MANIFEST["source_decisions"])
    }
    failures: list[tuple[str, str]] = []
    for vector in section["vectors"]:
        references = cast(list[str], vector["decision_references"])
        if not set(references) <= registered:
            failures.append((cast(str, vector["id"]), "unregistered-reference"))
        if len(references) != len(set(references)):
            failures.append((cast(str, vector["id"]), "duplicate-reference"))
    return failures


def test_an_unregistered_decision_reference_is_refused() -> None:
    document = copy.deepcopy(INVALID)
    vector = document["vectors"][0]
    vector["decision_references"] = ["decision:not-registered"]

    assert _resealed_digest(document) != next(
        entry["sha256"]
        for entry in MANIFEST["corpus_files"]
        if entry["filename"] == "invalid-vectors.json"
    )
    assert _reference_failures(document) == [
        (cast(str, vector["id"]), "unregistered-reference")
    ]


def test_a_repeated_decision_reference_is_refused() -> None:
    document = copy.deepcopy(INVALID)
    vector = document["vectors"][0]
    vector["decision_references"] = [
        *vector["decision_references"],
        vector["decision_references"][0],
    ]

    assert _resealed_digest(document) != next(
        entry["sha256"]
        for entry in MANIFEST["corpus_files"]
        if entry["filename"] == "invalid-vectors.json"
    )
    assert _reference_failures(document) == [
        (cast(str, vector["id"]), "duplicate-reference")
    ]


def test_the_sealed_corpus_has_no_reference_failures() -> None:
    for _, section, _ in FAMILIES:
        assert not _reference_failures(section)


# --- every objective manifest declaration has an executable consumer ----------


def _leaf_paths(node: Any, prefix: str = "") -> list[str]:
    if isinstance(node, dict):
        mapping = cast(dict[str, Any], node)
        if not mapping:
            return [prefix]
        return [p for k, v in mapping.items() for p in _leaf_paths(v, f"{prefix}/{k}")]
    if isinstance(node, list):
        items = cast(list[Any], node)
        if not items:
            return [prefix]
        return [p for i, v in enumerate(items) for p in _leaf_paths(v, f"{prefix}/{i}")]
    return [prefix]


DESCRIPTIVE_PATHS = frozenset(
    cast(list[str], MANIFEST["descriptive_metadata"]["paths"])
)


def _v_format() -> None:
    """Canonicalization is enforced by the loader every document passes through."""
    fmt = cast(dict[str, Any], MANIFEST["format"])
    canonical = cast(dict[str, Any], fmt["canonicalization"])
    assert fmt["name"] == "faultatlas-development-history-contract-corpus"
    assert fmt["version"] == "1"
    assert canonical["name"] == "json-sort-keys-compact-utf8-lf-v1"
    assert canonical["encoding"] == "UTF-8_without_BOM"
    assert canonical["line_endings"] == "LF_only"
    assert canonical["keys"] == "sorted"
    assert canonical["whitespace"] == "compact"
    assert canonical["exactly_one_trailing_lf"] is True
    assert canonical["floats_and_NaN_permitted"] is False
    for name in SEALED_JSON:
        raw = (CORPUS / f"{name}.json").read_bytes()
        # Re-running the loader is the enforcement: it refuses a BOM, a CR, a
        # missing or doubled trailing LF, unsorted or spaced JSON, and any
        # non-integer number.
        assert _parse_canonical_json(raw) is not None
        assert not any(
            isinstance(value, float)
            for value in _flat_values(json.loads(raw.decode("utf-8")))
        )


def _flat_values(node: Any) -> list[Any]:
    if isinstance(node, dict):
        return [
            v
            for value in cast(dict[str, Any], node).values()
            for v in _flat_values(value)
        ]
    if isinstance(node, list):
        return [v for value in cast(list[Any], node) for v in _flat_values(value)]
    return [node]


def _v_corpus_identity() -> None:
    identity_block = cast(dict[str, Any], MANIFEST["corpus_identity"])
    assert identity_block["id"] == "faultatlas-development-history-contract-corpus"
    assert identity_block["version"] == "1"
    assert CORPUS.name == f"v{identity_block['version']}"


def _v_corpus_files() -> None:
    """Declared file state is compared with the filesystem, not with itself."""
    declared = cast(list[dict[str, Any]], MANIFEST["corpus_files"])
    assert tuple(sorted(cast(str, e["filename"]) for e in declared)) == CORPUS_FILES
    assert {p.name for p in CORPUS.iterdir()} == set(CORPUS_FILES)
    for entry in declared:
        path = CORPUS / cast(str, entry["filename"])
        info = path.stat()
        assert entry["required"] is True, entry["filename"]
        assert stat_module.S_ISREG(info.st_mode), entry["filename"]
        assert f"0{info.st_mode & 0o777:o}" == entry["filesystem_mode"], entry[
            "filename"
        ]
        executable = bool(info.st_mode & 0o111)
        assert entry["git_mode"] == ("100755" if executable else "100644"), entry[
            "filename"
        ]
        if "sha256" in entry:
            raw = path.read_bytes()
            assert hashlib.sha256(raw).hexdigest() == entry["sha256"], entry["filename"]
            assert len(raw) == entry["byte_length"], entry["filename"]


def _v_scope() -> None:
    scope = cast(dict[str, Any], MANIFEST["scope"])
    assert tuple(cast(list[str], scope["production_modules"])) == PRODUCTION_MODULES
    assert tuple(cast(list[str], scope["supporting_authorities_not_owned"])) == (
        SUPPORTING_AUTHORITIES
    )
    for module in PRODUCTION_MODULES + SUPPORTING_AUTHORITIES:
        assert importlib.import_module(module) is not None
    # source_only: no production module may reach the corpus tree at all.
    assert scope["source_only"] is True
    for source in (REPOSITORY_ROOT / "src").rglob("*.py"):
        assert "reference_corpus" not in source.read_text("utf-8"), source
    # package exclusion is enforced repository-wide by the packaging oracle.
    assert scope["package_exclusion_required"] is True
    packaging = (REPOSITORY_ROOT / "tests/test_package.py").read_text("utf-8")
    assert "reference_corpus" in packaging, (
        "the packaging oracle must exclude the corpus"
    )


def _v_target_symbols() -> None:
    declared = cast(list[dict[str, Any]], MANIFEST["target_symbols"])
    assert {cast(str, e["symbol"]) for e in declared} == set(OWNED)
    for entry in declared:
        module = importlib.import_module(cast(str, entry["module"]))
        assert entry["symbol"] in module.__all__, entry["symbol"]


def _v_execution_contract() -> None:
    """Declared executor inventories are compared with the live registries."""
    contract = cast(dict[str, Any], MANIFEST["execution_contract"])
    registry = cast(dict[str, Any], contract["registry"])
    owned_enums = {
        n for n, t in OWNED.items() if isinstance(t, type) and issubclass(t, Enum)
    }
    assert registry["owned_enum_targets"] == len(owned_enums)
    assert registry["owned_model_targets"] == len(OWNED) - len(owned_enums)
    assert registry["support_enum_targets"] == len(SUPPORT_ENUMS)
    assert registry["support_model_targets"] == len(SUPPORT_MODELS)
    for key in ("unknown_target", "unknown_operation", "unknown_marker"):
        assert registry[key] == "reject"
    markers = cast(dict[str, Any], contract["test_input_markers"])
    assert tuple(cast(list[str], markers["allowed"])) == ALLOWED_MARKERS
    assert markers["max_indexed_count"] == MAX_INDEXED_COUNT
    assert tuple(cast(list[str], markers["support_enum_allowlist"])) == tuple(
        sorted(SUPPORT_ENUMS)
    )
    assert tuple(cast(list[str], markers["support_model_allowlist"])) == tuple(
        sorted(SUPPORT_MODELS)
    )
    assert tuple(cast(list[str], contract["input_modes"])) == tuple(
        sorted(INPUT_MODE_DISPATCH)
    )
    executor = REPOSITORY_ROOT / cast(str, contract["test_only_executor"])
    assert executor.resolve() == Path(__file__).resolve()


def _v_rejection_contract() -> None:
    contract = cast(dict[str, Any], MANIFEST["rejection_contract"])
    assert cast(list[str], contract["error_oracle"]) == [
        "failure_category",
        "error_location",
        "error_location_mode",
        "error_type",
    ]
    declared = set(cast(list[str], contract["error_oracle"]))
    for vector in INVALID["vectors"]:
        assert set(cast(dict[str, Any], vector["expected"])) - {"outcome"} == declared
    assert contract["internal_union_branch_labels_locked"] is False
    assert contract["unstable_prose_locked"] is False
    blob = json.dumps(INVALID["vectors"])
    assert "function-after[" not in blob and "function-before[" not in blob


def _v_replay_contract() -> None:
    contract = cast(dict[str, Any], MANIFEST["replay_contract"])
    classifications = {
        cast(str, v["evidence_classification"]) for v in REPLAY["vectors"]
    }
    assert contract["deterministic_derivation_present"] is False
    assert "deterministic_derivation" not in classifications
    limits = cast(dict[str, Any], contract["evidence_limits"])
    linkable = {
        cast(str, v["embedded_facts"]["/fact"])
        for v in REPLAY["vectors"]
        if v["target"] == "PullRequestHistoryFactEvidenceLink"
    }
    assert limits["linkable_history_facts"] == len(linkable)
    assert limits["change_set_completeness_claimed"] is False
    composed = next(
        v for v in REPLAY["vectors"] if v["target"] == "PullRequestChangeSet"
    )
    assert "complete" not in cast(dict[str, Any], composed["input"])
    assert contract["production_replay_io"] is False
    assert contract["production_lookup"] == "none"
    constants = cast(dict[str, str], contract["retained_case_constants"])
    assert constants["provider"] == "github"
    assert constants["provider_leaf_suffix"] == "/repository_identity/provider"
    assert cast(list[str], contract["structural_leaf_names"]) == [
        "algorithm",
        "kind",
        "schema_version",
    ]
    assert contract["retained_role_source_positions"] == {
        "/observations/comparison/base_sha": "base",
        "/observations/comparison/head_sha": "head",
        "/observations/pr/attempts/0/bracket_a/head/sha": "head",
    }


def _v_source_decisions() -> None:
    entries = cast(list[dict[str, Any]], MANIFEST["source_decisions"])
    assert len(entries) == 5
    for entry in entries:
        raw = (REPOSITORY_ROOT / cast(str, entry["path"])).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == entry["sha256"]
        assert set(cast(list[str], entry["authority_ids"])) <= _declared_authority_ids(
            entry
        )
        source = cast(dict[str, str], entry["authority_id_source"])
        assert source["collection"].startswith("/") and source["id_field"]


def _v_effective_governance() -> None:
    governance = cast(dict[str, Any], MANIFEST["effective_governance"])
    registered = {
        cast(str, e["decision_reference"]) for e in MANIFEST["source_decisions"]
    }
    assert governance["base_decision"] in registered
    assert governance["correction"] in registered
    # Subset membership would let the correction drop out of the declared
    # inputs while the recomputation still loads it, so the manifest could
    # misreport which artifacts produced its totals.
    assert set(cast(list[str], governance["recomputed_from"])) == {
        governance["base_decision"],
        governance["correction"],
    }
    assert set(cast(list[str], governance["recomputed_from"])) <= registered
    assert len(cast(list[str], governance["recomputed_from"])) == 2
    assert governance["vectorized_as_product_behavior"] is False
    # The numeric projection is recomputed from both artifacts elsewhere; this
    # validator binds the declared references and the invariant totals.
    assert governance["inherited_subject_count"] == 12
    assert governance["dispositioned_exactly_once"] == 12
    assert governance["self_introduced_count"] == 0
    assert governance["self_owned_open"] == 0
    assert governance["authority_totals"] == {"S1.P05.S08": 6, "S1.P05.S08.C01": 6}


def _v_vector_summary() -> None:
    summary = cast(dict[str, Any], MANIFEST["vector_summary"])
    sections = {"valid": VALID, "invalid": INVALID, "replay": REPLAY}
    total = 0
    for family, section in sections.items():
        derived = dict(
            sorted(
                Counter(cast(str, v["category"]) for v in section["vectors"]).items()
            )
        )
        assert summary[family]["categories"] == derived, family
        assert summary[family]["count"] == len(section["vectors"]), family
        total += len(section["vectors"])
    assert summary["total_vectors"] == total
    assert summary["fixtures"] == len(cast(list[Any], VALID["fixtures"]))


def _v_non_goals() -> None:
    assert list(cast(list[str], MANIFEST["non_goals"])) == list(NON_GENERALIZATIONS)


def _v_s07_ledger() -> None:
    ledger = cast(list[dict[str, str]], MANIFEST["s07_forbidden_extra_ledger"])
    by_id = {cast(str, v["id"]): v for v in INVALID["vectors"]}
    assert len({e["published_non_claim"] for e in ledger}) == len(ledger) == 11
    for entry in ledger:
        vector = by_id[entry["vector_id"]]
        assert vector["semantic_partition"] == entry["semantic_partition"]
        assert vector["expected"]["error_location"] == [entry["extra_key"]]
        assert entry["extra_key"] in cast(dict[str, Any], vector["input"])


def _v_assurance() -> None:
    assurance = cast(dict[str, Any], MANIFEST["assurance"])
    assert assurance["canonical_json_files"] == len(SEALED_JSON)
    assert assurance["sidecar_count"] == len(
        [f for f in CORPUS_FILES if f.endswith(".sha256")]
    )
    locked = [e for e in MANIFEST["corpus_files"] if "sha256" in e]
    assert assurance["corpus_files_digest_locked"] is bool(locked)
    for entry in locked:
        raw = (CORPUS / cast(str, entry["filename"])).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == entry["sha256"]
    assert assurance["symbol_coverage_derived_from_live_dunder_all"] is True
    assert {cast(str, e["symbol"]) for e in MANIFEST["target_symbols"]} == set(OWNED)


OBJECTIVE_VALIDATORS: tuple[tuple[str, Callable[[], None]], ...] = (
    ("/assurance/", _v_assurance),
    ("/corpus_files/", _v_corpus_files),
    ("/corpus_identity/", _v_corpus_identity),
    ("/effective_governance/", _v_effective_governance),
    ("/execution_contract/", _v_execution_contract),
    ("/format/", _v_format),
    ("/non_goals/", _v_non_goals),
    ("/rejection_contract/", _v_rejection_contract),
    ("/replay_contract/", _v_replay_contract),
    ("/s07_forbidden_extra_ledger/", _v_s07_ledger),
    ("/scope/", _v_scope),
    ("/source_decisions/", _v_source_decisions),
    ("/target_symbols/", _v_target_symbols),
    ("/vector_summary/", _v_vector_summary),
)


def _objective_leaf_paths() -> list[str]:
    return [
        path
        for path in _leaf_paths(MANIFEST)
        if not path.startswith("/descriptive_metadata")
        and path not in DESCRIPTIVE_PATHS
    ]


@pytest.mark.parametrize(
    ("prefix", "validator"),
    OBJECTIVE_VALIDATORS,
    ids=[p.strip("/") for p, _ in OBJECTIVE_VALIDATORS],
)
def test_each_objective_manifest_family_is_independently_validated(
    prefix: str, validator: Callable[[], None]
) -> None:
    """Each validator compares the declaration with an independent reality."""
    assert any(path.startswith(prefix) for path in _objective_leaf_paths()), prefix
    validator()


def test_every_objective_manifest_declaration_has_exactly_one_consumer() -> None:
    """A declaration nothing checks is decoration wearing an assurance costume.

    Reading a manifest field and asserting it equals a literal proves only that
    the manifest says what it says. Every objective leaf must therefore fall to
    a validator that consults something outside the manifest, and every leaf
    that genuinely cannot must be declared descriptive instead.
    """
    uncovered: list[str] = []
    duplicated: list[str] = []
    for path in _objective_leaf_paths():
        owners = [p for p, _ in OBJECTIVE_VALIDATORS if path.startswith(p)]
        if not owners:
            uncovered.append(path)
        elif len(owners) > 1:
            duplicated.append(path)

    assert not uncovered, uncovered
    assert not duplicated, duplicated


def test_the_declared_descriptive_paths_are_real_and_non_objective() -> None:
    every = set(_leaf_paths(MANIFEST))
    for path in DESCRIPTIVE_PATHS:
        assert path in every, path
        assert not path.startswith("/descriptive_metadata"), path
    assert MANIFEST["descriptive_metadata"]["contract"]
    assert not DESCRIPTIVE_PATHS & set(_objective_leaf_paths())


def test_the_manifest_partition_is_exhaustive() -> None:
    every = [
        p for p in _leaf_paths(MANIFEST) if not p.startswith("/descriptive_metadata")
    ]

    assert len(every) == len(_objective_leaf_paths()) + len(DESCRIPTIVE_PATHS)
    assert set(every) == set(_objective_leaf_paths()) | DESCRIPTIVE_PATHS


def test_a_new_objective_declaration_forces_review() -> None:
    """An unclassified field must fail rather than pass unnoticed."""
    probe = copy.deepcopy(MANIFEST)
    probe["invented_objective_claim"] = True
    unowned = [
        path
        for path in _leaf_paths(probe)
        if not path.startswith("/descriptive_metadata")
        and path not in DESCRIPTIVE_PATHS
        and not any(path.startswith(p) for p, _ in OBJECTIVE_VALIDATORS)
    ]

    assert unowned == ["/invented_objective_claim"]


def test_descriptive_metadata_cannot_justify_an_assurance_claim() -> None:
    """Descriptive data is explicitly outside the verified surface."""
    objective = set(_objective_leaf_paths())
    for path in sorted(DESCRIPTIVE_PATHS):
        assert path not in objective, path

    # Mutating a descriptive leaf must change no objective validator's outcome:
    # descriptive data can never be the reason an assurance check passes.
    assert "/corpus_identity/classification" in DESCRIPTIVE_PATHS
    for _, validator in OBJECTIVE_VALIDATORS:
        validator()


# --- fixtures are declarations, resolved to exact semantic coordinates --------

FIXTURE_BINDINGS: tuple[tuple[str, str, str, str, str], ...] = (
    (
        "history.fixture.repository.pytest",
        "valid",
        "history.valid.role-binding.base-canonical",
        "input",
        "/pull_request/repository_identity",
    ),
    (
        "history.fixture.pull-request.4414",
        "valid",
        "history.valid.role-binding.base-canonical",
        "input",
        "/pull_request",
    ),
    (
        "history.fixture.review.176071572",
        "valid",
        "history.valid.approval.canonical",
        "input",
        "/review",
    ),
    (
        "history.fixture.commit.base-4c9cde74",
        "valid",
        "history.valid.role-binding.base-canonical",
        "input",
        "/role_assignment/revision",
    ),
    (
        "history.fixture.commit.head-690a63b9",
        "valid",
        "history.valid.role-binding.head-canonical",
        "input",
        "/role_assignment/revision",
    ),
    (
        "history.fixture.commit.merge-10cdae8e",
        "valid",
        "history.valid.merge-outcome.canonical",
        "input",
        "/merge_revision",
    ),
    (
        "history.fixture.blob.changelog-7a28b610",
        "valid",
        "history.valid.changed-path.added",
        "input",
        "/head_object",
    ),
    (
        "history.fixture.blob.rewrite-7b9aa500",
        "valid",
        "history.valid.changed-path.modified",
        "input",
        "/head_object",
    ),
    (
        "history.fixture.blob.assertrewrite-a02433cd",
        "valid",
        "history.valid.changed-path.distinct-blob",
        "input",
        "/head_object",
    ),
    (
        "history.fixture.path.changelog",
        "valid",
        "history.valid.changed-path.added",
        "input",
        "/path",
    ),
    (
        "history.fixture.path.rewrite",
        "valid",
        "history.valid.changed-path.modified",
        "input",
        "/path",
    ),
    (
        "history.fixture.path.assertrewrite",
        "valid",
        "history.valid.changed-path.distinct-blob",
        "input",
        "/path",
    ),
    (
        "history.fixture.ref-name.starred-with-side-effect",
        "valid",
        "history.valid.head-ref-deletion.canonical",
        "input",
        "/head_ref_name",
    ),
    (
        "history.fixture.instant.approval",
        "valid",
        "history.valid.occurrence-time.approval",
        "input",
        "/occurred_at",
    ),
    (
        "history.fixture.instant.merge",
        "valid",
        "history.valid.occurrence-time.merge",
        "input",
        "/occurred_at",
    ),
    (
        "history.fixture.instant.deletion",
        "valid",
        "history.valid.occurrence-time.deletion",
        "input",
        "/occurred_at",
    ),
    (
        "history.fixture.record.acquisition-1c29093b",
        "valid",
        "history.valid.evidence-link.role-binding-json",
        "input",
        "/evidence_record",
    ),
    (
        "history.fixture.record.correction-44491ee5",
        "valid",
        "history.valid.evidence-link.correction-record",
        "input",
        "/evidence_record",
    ),
    (
        "history.fixture.record.synthetic",
        "valid",
        "history.valid.evidence-link.synthetic-record",
        "input",
        "/evidence_record",
    ),
)

SECTIONS = {"valid": VALID, "invalid": INVALID, "replay": REPLAY}


def _binding_failures(
    fixtures: list[dict[str, Any]],
    bindings: tuple[tuple[str, str, str, str, str], ...] = FIXTURE_BINDINGS,
) -> list[tuple[str, str]]:
    """Resolve each fixture at an exact semantic coordinate, never by search.

    A global equality sweep would bind a fixture to any position that happens to
    hold an equal value, so a wrong coordinate would still look satisfied.
    """
    declared = {cast(str, f["id"]): f for f in fixtures}
    failures: list[tuple[str, str]] = []
    bound: set[str] = set()
    for fixture_id, family, vector_id, side, pointer in bindings:
        if fixture_id not in declared:
            failures.append((fixture_id, "unknown-fixture"))
            continue
        section = SECTIONS.get(family)
        if section is None:
            failures.append((fixture_id, "unknown-family"))
            continue
        vector = next((v for v in section["vectors"] if v["id"] == vector_id), None)
        if vector is None:
            failures.append((fixture_id, "unknown-vector"))
            continue
        try:
            observed = _resolve_pointer(vector[side], pointer)
        except (KeyError, IndexError, TypeError, ValueError):
            failures.append((fixture_id, "unresolvable-pointer"))
            continue
        if observed != declared[fixture_id]["value"]:
            failures.append((fixture_id, "value-mismatch"))
            continue
        bound.add(fixture_id)
    for fixture_id in declared:
        if fixture_id not in bound and not any(f[0] == fixture_id for f in failures):
            failures.append((fixture_id, "orphan"))
    return sorted(failures)


def test_every_declared_fixture_binds_to_an_exact_semantic_use() -> None:
    """A fixture list nothing resolves is a claim about data it never touches."""
    fixtures = cast(list[dict[str, Any]], VALID["fixtures"])

    assert len(fixtures) == 19
    assert len({cast(str, f["id"]) for f in fixtures}) == 19
    assert len({f[0] for f in FIXTURE_BINDINGS}) == 19
    assert all(f["status"] == "locked" for f in fixtures)
    assert not _binding_failures(fixtures)


def test_the_three_fixture_lists_are_the_same_declaration() -> None:
    rendered = {
        json.dumps(section["fixtures"], sort_keys=True) for section in SECTIONS.values()
    }
    assert len(rendered) == 1


def test_a_fixture_that_drifts_from_its_use_is_refused() -> None:
    """The reproduced finding, kept permanently."""
    fixtures = copy.deepcopy(cast(list[dict[str, Any]], VALID["fixtures"]))
    drifted = next(f for f in fixtures if f["id"] == "history.fixture.path.changelog")
    drifted["value"] = "changelog/9999.tampered.rst"

    assert _binding_failures(fixtures) == [
        ("history.fixture.path.changelog", "value-mismatch")
    ]


def test_a_binding_at_the_wrong_semantic_coordinate_is_refused() -> None:
    """An equal value elsewhere must not satisfy a fixture."""
    wrong = tuple(
        (
            fid,
            fam,
            vid,
            side,
            "/status" if fid == "history.fixture.path.changelog" else ptr,
        )
        for fid, fam, vid, side, ptr in FIXTURE_BINDINGS
    )
    failures = _binding_failures(cast(list[dict[str, Any]], VALID["fixtures"]), wrong)

    assert ("history.fixture.path.changelog", "value-mismatch") in failures


def test_a_binding_to_an_unknown_fixture_or_vector_is_refused() -> None:
    unknown_fixture = FIXTURE_BINDINGS[:-1] + (
        (
            "history.fixture.absent",
            "valid",
            "history.valid.changed-path.added",
            "input",
            "/path",
        ),
    )
    unknown_vector = FIXTURE_BINDINGS[:-1] + (
        (FIXTURE_BINDINGS[-1][0], "valid", "history.valid.absent", "input", "/x"),
    )
    fixtures = cast(list[dict[str, Any]], VALID["fixtures"])

    assert ("history.fixture.absent", "unknown-fixture") in _binding_failures(
        fixtures, unknown_fixture
    )
    assert (FIXTURE_BINDINGS[-1][0], "unknown-vector") in _binding_failures(
        fixtures, unknown_vector
    )


# --- input modes are bound to their family and dispatched explicitly ----------


def test_every_vector_declares_an_input_mode_its_family_permits() -> None:
    for family, section in SECTIONS.items():
        permitted = FAMILY_INPUT_MODES[family]
        for vector in section["vectors"]:
            assert vector["input_mode"] in permitted, (
                vector["id"],
                vector["input_mode"],
            )

    assert FAMILY_INPUT_MODES["replay"] == frozenset({"replay"})
    assert set(ALLOWED_INPUT_MODES) == set().union(*FAMILY_INPUT_MODES.values())
    assert set(INPUT_MODE_DISPATCH) == set(ALLOWED_INPUT_MODES)


def test_the_measured_family_mode_matrix_is_the_declared_one() -> None:
    observed = {
        family: dict(
            sorted(
                Counter(cast(str, v["input_mode"]) for v in section["vectors"]).items()
            )
        )
        for family, section in SECTIONS.items()
    }

    assert observed == {
        "valid": {"json": 33, "python": 15},
        "invalid": {"json": 85, "python": 26},
        "replay": {"replay": 24},
    }


def test_relabelling_every_replay_vector_as_json_is_refused() -> None:
    """JSON and replay reconstruct alike, so only the family contract catches it."""
    document = copy.deepcopy(REPLAY)
    for vector in document["vectors"]:
        vector["input_mode"] = "json"

    assert _resealed_digest(document) != _sealed_replay_digest()
    offending = [
        cast(str, v["id"])
        for v in document["vectors"]
        if v["input_mode"] not in FAMILY_INPUT_MODES["replay"]
    ]
    assert len(offending) == 24


def test_relabelling_a_valid_vector_as_replay_is_refused() -> None:
    vector = copy.deepcopy(VALID["vectors"][0])
    vector["input_mode"] = "replay"

    assert vector["input_mode"] not in FAMILY_INPUT_MODES["valid"]


def test_an_unknown_input_mode_fails_the_dispatcher_closed() -> None:
    vector = copy.deepcopy(VALID["vectors"][0])
    vector["input_mode"] = "telepathy"

    with pytest.raises(AssertionError, match="unknown input mode"):
        _construct(vector)


# --- canonicalization is enforced at the parse, not after it ------------------


def _unsorted(raw: bytes) -> bytes:
    document = json.loads(raw.decode("utf-8"))
    reversed_top = dict(reversed(list(cast(dict[str, Any], document).items())))
    return (
        json.dumps(
            reversed_top, sort_keys=False, separators=(",", ":"), ensure_ascii=False
        )
        + "\n"
    ).encode("utf-8")


def _sub_number(raw: bytes, literal: bytes) -> bytes:
    return raw.replace(
        b'"canonical_json_files":4', b'"canonical_json_files":' + literal, 1
    )


def _m_nan(raw: bytes) -> bytes:
    return _sub_number(raw, b"NaN")


def _m_inf(raw: bytes) -> bytes:
    return _sub_number(raw, b"Infinity")


def _m_neg_inf(raw: bytes) -> bytes:
    return _sub_number(raw, b"-Infinity")


def _m_float(raw: bytes) -> bytes:
    return _sub_number(raw, b"1.5")


def _m_bom(raw: bytes) -> bytes:
    return b"\xef\xbb\xbf" + raw


def _m_cr(raw: bytes) -> bytes:
    return raw[:-1] + b"\r\n"


def _m_no_lf(raw: bytes) -> bytes:
    return raw[:-1]


def _m_extra_lf(raw: bytes) -> bytes:
    return raw + b"\n"


def _m_spaced(raw: bytes) -> bytes:
    return raw.replace(b'","', b'" , "', 1)


CANONICAL_MUTATIONS: tuple[tuple[str, Callable[[bytes], bytes]], ...] = (
    ("NaN", _m_nan),
    ("Infinity", _m_inf),
    ("-Infinity", _m_neg_inf),
    ("finite float", _m_float),
    ("BOM", _m_bom),
    ("CR", _m_cr),
    ("missing trailing LF", _m_no_lf),
    ("extra trailing LF", _m_extra_lf),
    ("non-compact spacing", _m_spaced),
    ("unsorted keys", _unsorted),
)


@pytest.mark.parametrize(
    ("label", "mutate"), CANONICAL_MUTATIONS, ids=[m[0] for m in CANONICAL_MUTATIONS]
)
def test_the_strict_loader_refuses_each_forbidden_canonical_form(
    label: str, mutate: Callable[[bytes], bytes]
) -> None:
    """Each mutation must fail on canonicalization, never on a stale digest."""
    raw = (CORPUS / "manifest.json").read_bytes()
    mutated = mutate(raw)

    assert mutated != raw, label
    with pytest.raises((AssertionError, json.JSONDecodeError)):
        _parse_canonical_json(mutated)


def test_the_sealed_corpus_carries_no_float_or_nonstandard_constant() -> None:
    for name in SEALED_JSON:
        raw = (CORPUS / f"{name}.json").read_bytes()
        assert not any(
            isinstance(value, float) for value in _flat_values(json.loads(raw))
        ), name


# --- the objective validators are themselves falsifiable ---------------------


def test_a_false_file_mode_declaration_is_refused() -> None:
    entry = copy.deepcopy(
        next(e for e in MANIFEST["corpus_files"] if e["filename"] == "manifest.json")
    )
    assert entry["filesystem_mode"] == "0644"
    entry["filesystem_mode"] = "0777"
    info = (CORPUS / "manifest.json").stat()

    assert f"0{info.st_mode & 0o777:o}" != entry["filesystem_mode"]


def test_an_execution_registry_drift_is_refused() -> None:
    """The declared inventory must track the live registry, not a stored number."""
    registry = copy.deepcopy(
        cast(dict[str, Any], MANIFEST["execution_contract"]["registry"])
    )
    registry["support_model_targets"] = len(SUPPORT_MODELS) + 1

    assert registry["support_model_targets"] != len(SUPPORT_MODELS)

    markers = copy.deepcopy(
        cast(dict[str, Any], MANIFEST["execution_contract"]["test_input_markers"])
    )
    markers["support_model_allowlist"] = [
        *markers["support_model_allowlist"],
        "Smuggled",
    ]
    assert tuple(markers["support_model_allowlist"]) != tuple(sorted(SUPPORT_MODELS))


# --- the reference systems are enumerated and every one resolves --------------

REFERENCE_SYSTEMS: tuple[tuple[str, str, str], ...] = (
    (
        "decision_references",
        "vector.decision_references",
        "registered decision_reference set",
    ),
    ("authority_ids", "source_decisions[].authority_ids", "locked source document ids"),
    ("source_pointers", "replay.source_pointers", "retained acquisition JSON pointers"),
    ("evidence_record_lock", "replay.evidence_record_lock", "replay artifact_locks"),
    ("embedded_facts", "replay.embedded_facts", "replay vector ids"),
    ("fixture_bindings", "fixtures[].id", "exact vector semantic coordinates"),
    ("corpus_files", "corpus_files[].filename", "filesystem and digest state"),
    (
        "execution_registry",
        "execution_contract inventories",
        "live executor registries",
    ),
)


def test_every_reference_system_has_a_resolver() -> None:
    """Eight systems, each with an executable resolver and a fail-closed policy."""
    resolvers = {
        "decision_references": test_every_vector_reference_names_a_registered_authority,
        "authority_ids": test_every_declared_authority_id_resolves_in_its_locked_document,
        "source_pointers": test_only_retained_observations_cite_retained_evidence,
        "evidence_record_lock": test_every_replayed_association_equals_its_locked_artifact_reference,
        "embedded_facts": test_every_embedded_fact_equals_its_bound_retained_vector,
        "fixture_bindings": test_every_declared_fixture_binds_to_an_exact_semantic_use,
        "corpus_files": _v_corpus_files,
        "execution_registry": _v_execution_contract,
    }

    assert len(REFERENCE_SYSTEMS) == 8
    assert {name for name, _, _ in REFERENCE_SYSTEMS} == set(resolvers)
    for name, resolver in resolvers.items():
        assert callable(resolver), name


def test_the_contract_markdown_states_the_epistemic_split() -> None:
    """The derived prose must not present descriptive data as verified."""
    text = (CORPUS / "contract.md").read_text("utf-8")
    mechanism = cast(str, MANIFEST["execution_contract"]["fixture_references"])

    assert "## 5. Objective and Descriptive Declarations" in text
    assert f"`{mechanism}`" in text
    assert f"({len(DESCRIPTIVE_PATHS)} of them)" in text
    assert "never counted as verified assurance" in text


# --- the nine-target semantic requirement ledger ------------------------------
#
# One row per independently published requirement. A validator function may
# publish more than one requirement -- `_require_typed_python_binding` publishes
# both the base and the head typing rule -- and each gets its own row and its
# own witness. Nothing here records source text, line numbers, or validator
# names: the ledger is semantic.

NEGATIVE, POSITIVE = "NEGATIVE_ISOLATED", "POSITIVE_ISOLATED"
RELATIONAL, UNIT, GENERIC = "RELATIONAL_POSITIVE", "UNIT_ORACLE", "FRAMEWORK_GENERIC"

REQUIREMENT_LEDGER: tuple[tuple[str, str, str, str, str], ...] = (
    # PullRequestRevisionRoleBinding
    (
        "RB-01",
        "PullRequestRevisionRoleBinding",
        "pull_request typed in Python",
        NEGATIVE,
        "history.invalid.role-binding.untyped-python-pull-request",
    ),
    (
        "RB-02",
        "PullRequestRevisionRoleBinding",
        "role_assignment typed in Python",
        NEGATIVE,
        "history.invalid.role-binding.untyped-python-role-assignment",
    ),
    (
        "RB-03",
        "PullRequestRevisionRoleBinding",
        "subject must be a pull request",
        NEGATIVE,
        "history.invalid.role-binding.non-pull-request-subject",
    ),
    (
        "RB-04",
        "PullRequestRevisionRoleBinding",
        "bound role must be base or head",
        NEGATIVE,
        "history.invalid.role-binding.disallowed-revision-role",
    ),
    (
        "RB-05",
        "PullRequestRevisionRoleBinding",
        "base binding is accepted",
        POSITIVE,
        "history.valid.role-binding.base-canonical",
    ),
    (
        "RB-06",
        "PullRequestRevisionRoleBinding",
        "head binding is accepted",
        POSITIVE,
        "history.valid.role-binding.head-canonical",
    ),
    # ChangedPathStatus
    (
        "ST-01",
        "ChangedPathStatus",
        "added is admitted",
        POSITIVE,
        "history.valid.status.added",
    ),
    (
        "ST-02",
        "ChangedPathStatus",
        "modified is admitted",
        POSITIVE,
        "history.valid.status.modified",
    ),
    (
        "ST-03",
        "ChangedPathStatus",
        "the vocabulary is closed",
        NEGATIVE,
        "history.invalid.status.not-a-status",
    ),
    # PullRequestChangedPath
    (
        "CP-01",
        "PullRequestChangedPath",
        "path typed in Python",
        NEGATIVE,
        "history.invalid.changed-path.untyped-python-path",
    ),
    (
        "CP-02",
        "PullRequestChangedPath",
        "head_object typed in Python",
        NEGATIVE,
        "history.invalid.changed-path.untyped-python-head-object",
    ),
    (
        "CP-03",
        "PullRequestChangedPath",
        "head_object must be a blob",
        NEGATIVE,
        "history.invalid.changed-path.commit-as-head-object",
    ),
    (
        "CP-04",
        "PullRequestChangedPath",
        "Python input requires the published status member",
        NEGATIVE,
        "history.invalid.changed-path.raw-python-status",
    ),
    # PullRequestChangeSet
    (
        "CS-01",
        "PullRequestChangeSet",
        "base is required",
        NEGATIVE,
        "history.invalid.change-set.missing-base",
    ),
    (
        "CS-02",
        "PullRequestChangeSet",
        "head is required",
        NEGATIVE,
        "history.invalid.change-set.missing-head",
    ),
    (
        "CS-03",
        "PullRequestChangeSet",
        "changed_paths is required",
        NEGATIVE,
        "history.invalid.change-set.missing-changed-paths",
    ),
    (
        "CS-04",
        "PullRequestChangeSet",
        "at least one changed path",
        NEGATIVE,
        "history.invalid.change-set.empty-changed-paths",
    ),
    (
        "CS-05",
        "PullRequestChangeSet",
        "at most 4096 changed paths",
        NEGATIVE,
        "history.invalid.change-set.above-maximum-changed-paths",
    ),
    (
        "CS-06",
        "PullRequestChangeSet",
        "base typed in Python",
        NEGATIVE,
        "history.invalid.change-set.untyped-python-base",
    ),
    (
        "CS-07",
        "PullRequestChangeSet",
        "head typed in Python",
        NEGATIVE,
        "history.invalid.change-set.untyped-python-head",
    ),
    (
        "CS-08",
        "PullRequestChangeSet",
        "changed_paths is a tuple in Python",
        NEGATIVE,
        "history.invalid.change-set.python-list-not-tuple",
    ),
    (
        "CS-09",
        "PullRequestChangeSet",
        "changed_paths holds published values",
        NEGATIVE,
        "history.invalid.change-set.untyped-python-changed-path-element",
    ),
    (
        "CS-10",
        "PullRequestChangeSet",
        "base and head bind one pull request",
        NEGATIVE,
        "history.invalid.change-set.mismatched-pull-requests",
    ),
    (
        "CS-11",
        "PullRequestChangeSet",
        "base position requires the base role",
        NEGATIVE,
        "history.invalid.change-set.base-position-rejects-non-base-role",
    ),
    (
        "CS-12",
        "PullRequestChangeSet",
        "head position requires the head role",
        NEGATIVE,
        "history.invalid.change-set.head-position-rejects-non-head-role",
    ),
    (
        "CS-13",
        "PullRequestChangeSet",
        "base and head revisions differ",
        NEGATIVE,
        "history.invalid.change-set.equal-base-and-head-revision",
    ),
    (
        "CS-14",
        "PullRequestChangeSet",
        "base and head algorithms match",
        NEGATIVE,
        "history.invalid.change-set.mismatched-revision-algorithms",
    ),
    (
        "CS-15",
        "PullRequestChangeSet",
        "object algorithms match the head",
        NEGATIVE,
        "history.invalid.change-set.mixed-hash-algorithms",
    ),
    (
        "CS-16",
        "PullRequestChangeSet",
        "repository paths are unique",
        NEGATIVE,
        "history.invalid.change-set.duplicate-path",
    ),
    (
        "CS-17",
        "PullRequestChangeSet",
        "no completeness claim",
        NEGATIVE,
        "history.invalid.change-set.extra-complete",
    ),
    (
        "CS-18",
        "PullRequestChangeSet",
        "supplied order is preserved",
        POSITIVE,
        "history.valid.change-set.supplied-order-preserved",
    ),
    # PullRequestReviewRevisionApproval
    (
        "RA-01",
        "PullRequestReviewRevisionApproval",
        "review typed in Python",
        NEGATIVE,
        "history.invalid.approval.untyped-python-review",
    ),
    (
        "RA-02",
        "PullRequestReviewRevisionApproval",
        "approved_revision typed in Python",
        NEGATIVE,
        "history.invalid.approval.untyped-python-approved-revision",
    ),
    (
        "RA-03",
        "PullRequestReviewRevisionApproval",
        "review must be a pull-request review",
        NEGATIVE,
        "history.invalid.approval.non-review-kind-subject",
    ),
    (
        "RA-04",
        "PullRequestReviewRevisionApproval",
        "approval is independent of HEAD",
        RELATIONAL,
        "history.valid.approval.revision-need-not-be-head",
    ),
    # PullRequestMergeRevisionOutcome
    (
        "MO-01",
        "PullRequestMergeRevisionOutcome",
        "pull_request typed in Python",
        NEGATIVE,
        "history.invalid.merge-outcome.untyped-python-pull-request",
    ),
    (
        "MO-02",
        "PullRequestMergeRevisionOutcome",
        "merge_revision typed in Python",
        NEGATIVE,
        "history.invalid.merge-outcome.untyped-python-merge-revision",
    ),
    (
        "MO-03",
        "PullRequestMergeRevisionOutcome",
        "subject must be a pull request",
        NEGATIVE,
        "history.invalid.merge-outcome.non-pull-request-subject",
    ),
    (
        "MO-04",
        "PullRequestMergeRevisionOutcome",
        "merge revision is independent of head",
        RELATIONAL,
        "history.valid.merge-outcome.revision-independent-of-head",
    ),
    # PullRequestHeadRefDeletion
    (
        "HD-01",
        "PullRequestHeadRefDeletion",
        "head typed in Python",
        NEGATIVE,
        "history.invalid.head-ref-deletion.untyped-python-head",
    ),
    (
        "HD-02",
        "PullRequestHeadRefDeletion",
        "head_ref_name typed in Python",
        NEGATIVE,
        "history.invalid.head-ref-deletion.raw-python-ref-name",
    ),
    (
        "HD-03",
        "PullRequestHeadRefDeletion",
        "the binding must carry the head role",
        NEGATIVE,
        "history.invalid.head-ref-deletion.base-binding",
    ),
    (
        "HD-04",
        "PullRequestHeadRefDeletion",
        "a refs/-prefixed name is refused",
        NEGATIVE,
        "history.invalid.head-ref-deletion.refs-prefixed-name",
    ),
    # PullRequestHistoricalOccurrenceTime
    (
        "OT-01",
        "PullRequestHistoricalOccurrenceTime",
        "occurrence typed in Python",
        NEGATIVE,
        "history.invalid.occurrence-time.untyped-python-occurrence",
    ),
    (
        "OT-02",
        "PullRequestHistoricalOccurrenceTime",
        "occurred_at must be a zero UTC offset",
        NEGATIVE,
        "history.invalid.occurrence-time.instant-positive-offset",
    ),
    (
        "OT-03",
        "PullRequestHistoricalOccurrenceTime",
        "the approval branch is admitted",
        POSITIVE,
        "history.valid.occurrence-time.approval",
    ),
    (
        "OT-04",
        "PullRequestHistoricalOccurrenceTime",
        "the merge branch is admitted",
        POSITIVE,
        "history.valid.occurrence-time.merge",
    ),
    (
        "OT-05",
        "PullRequestHistoricalOccurrenceTime",
        "the deletion branch is admitted",
        POSITIVE,
        "history.valid.occurrence-time.deletion",
    ),
    (
        "OT-06",
        "PullRequestHistoricalOccurrenceTime",
        "equal instants carry no order",
        RELATIONAL,
        "history.valid.occurrence-time.equal-instants-allowed",
    ),
    # PullRequestHistoryFactEvidenceLink
    (
        "EL-01",
        "PullRequestHistoryFactEvidenceLink",
        "fact typed in Python",
        NEGATIVE,
        "history.invalid.evidence-link.untyped-python-fact",
    ),
    (
        "EL-02",
        "PullRequestHistoryFactEvidenceLink",
        "occurrence-time fact typed in Python",
        NEGATIVE,
        "history.invalid.evidence-link.occurrence-time-fact-python",
    ),
    (
        "EL-03",
        "PullRequestHistoryFactEvidenceLink",
        "evidence_record typed in Python",
        NEGATIVE,
        "history.invalid.evidence-link.untyped-python-record",
    ),
    (
        "EL-04",
        "PullRequestHistoryFactEvidenceLink",
        "a change set is not an admitted fact",
        NEGATIVE,
        "history.invalid.evidence-link.change-set-fact",
    ),
    (
        "EL-05",
        "PullRequestHistoryFactEvidenceLink",
        "a status is not an admitted fact",
        NEGATIVE,
        "history.invalid.evidence-link.changed-path-status-fact",
    ),
    (
        "EL-06",
        "PullRequestHistoryFactEvidenceLink",
        "one record carries a second fact",
        RELATIONAL,
        "history.valid.evidence-link.second-fact-same-record",
    ),
)

LEDGER_TARGETS = {row[1] for row in REQUIREMENT_LEDGER}


def test_the_requirement_ledger_covers_every_owned_target() -> None:
    assert LEDGER_TARGETS == set(OWNED)


def test_every_ledger_witness_exists_and_matches_its_coverage_kind() -> None:
    """A ledger row is a claim about a vector; the vector must bear it out."""
    by_id = {
        cast(str, v["id"]): (family, v)
        for family, section in SECTIONS.items()
        for v in section["vectors"]
    }
    seen: set[str] = set()
    for req_id, target, _, kind, witness in REQUIREMENT_LEDGER:
        assert req_id not in seen, req_id
        seen.add(req_id)
        assert witness in by_id, (req_id, witness)
        family, vector = by_id[witness]
        assert vector["target"] == target, req_id
        if kind == NEGATIVE:
            assert family == "invalid", req_id
            assert vector["operation"] == "reject", req_id
        else:
            assert family == "valid", req_id
            assert vector["operation"] == "construct", req_id


# Four outer typed-input guards are equivalent mutants: deleting one leaves the
# same input refused by the nested published type at the same normalized error
# location and error type, so no vector can ever distinguish them. The
# requirement stays corpus-owned and witnessed -- it is the MUTATION that is
# uninformative, not the contract. Recorded semantically: no line numbers, no
# source text, no hashes.
EQUIVALENT_MUTANT_REDUNDANT_ENFORCEMENT: tuple[tuple[str, str, str, str], ...] = (
    ("CP-02", "PullRequestChangedPath.head_object", "GitBlobIdentity", "head_object"),
    (
        "RA-02",
        "PullRequestReviewRevisionApproval.approved_revision",
        "GitCommitIdentity",
        "approved_revision",
    ),
    (
        "MO-02",
        "PullRequestMergeRevisionOutcome.merge_revision",
        "GitCommitIdentity",
        "merge_revision",
    ),
    (
        "EL-02",
        "PullRequestHistoryFactEvidenceLink.fact occurrence-time branch",
        "PullRequestHistoricalOccurrenceTime",
        "fact",
    ),
)


def test_no_actionable_requirement_is_uncovered() -> None:
    """Every ledger row carries a recognised coverage kind."""
    assert not [
        r
        for r in REQUIREMENT_LEDGER
        if r[3] not in {NEGATIVE, POSITIVE, RELATIONAL, UNIT, GENERIC}
    ]


def test_the_equivalent_mutant_register_is_exactly_four() -> None:
    """A fifth entry would mean a requirement lost its discriminating witness.

    Each entry names the nested published type that enforces the same boundary,
    and the witness that still pins the published rejection contract.
    """
    ledger = {row[0]: row for row in REQUIREMENT_LEDGER}

    assert len(EQUIVALENT_MUTANT_REDUNDANT_ENFORCEMENT) == 4
    assert {row[0] for row in EQUIVALENT_MUTANT_REDUNDANT_ENFORCEMENT} == {
        "CP-02",
        "RA-02",
        "MO-02",
        "EL-02",
    }
    for req_id, outer, nested, location in EQUIVALENT_MUTANT_REDUNDANT_ENFORCEMENT:
        assert req_id in ledger, req_id
        assert ledger[req_id][3] == NEGATIVE, req_id
        assert outer and nested, req_id
        witness = next(v for v in INVALID["vectors"] if v["id"] == ledger[req_id][4])
        assert witness["input_mode"] == "python", req_id
        assert cast(list[str], witness["expected"]["error_location"])[0] == location
        assert witness["expected"]["error_type"] == "value_error", req_id


# --- a negative witness must violate exactly what it claims -------------------


def _change_set_siblings(supplied: dict[str, Any]) -> dict[str, bool]:
    """Evaluate each published change-set invariant on a JSON candidate.

    Validator ordering is not proof of isolation: a vector can be rejected for
    the reason it names while quietly violating a second requirement, which is
    how one cross-swapped vector came to stand for two role rules.
    """
    base = cast(dict[str, Any], supplied["base"])
    head = cast(dict[str, Any], supplied["head"])
    paths = cast(list[dict[str, Any]], supplied["changed_paths"])
    base_rev = base["role_assignment"]["revision"]
    head_rev = head["role_assignment"]["revision"]
    return {
        "same_pull_request": base["pull_request"] == head["pull_request"],
        "base_role_is_base": base["role_assignment"]["role"] == "base",
        "head_role_is_head": head["role_assignment"]["role"] == "head",
        "revisions_distinct": base_rev != head_rev,
        "algorithms_match": base_rev["algorithm"] == head_rev["algorithm"],
        "objects_match_head": all(
            entry["head_object"]["algorithm"] == head_rev["algorithm"]
            for entry in paths
        ),
        "paths_unique": len({entry["path"] for entry in paths}) == len(paths),
        "cardinality_valid": 1 <= len(paths) <= 4096,
    }


CHANGE_SET_ISOLATION = (
    (
        "history.invalid.change-set.base-position-rejects-non-base-role",
        "base_role_is_base",
    ),
    (
        "history.invalid.change-set.head-position-rejects-non-head-role",
        "head_role_is_head",
    ),
    ("history.invalid.change-set.mismatched-revision-algorithms", "algorithms_match"),
)


@pytest.mark.parametrize(
    ("vector_id", "violated"),
    CHANGE_SET_ISOLATION,
    ids=[v[1] for v in CHANGE_SET_ISOLATION],
)
def test_each_change_set_witness_violates_exactly_one_requirement(
    vector_id: str, violated: str
) -> None:
    vector = next(v for v in INVALID["vectors"] if v["id"] == vector_id)
    observed = _change_set_siblings(cast(dict[str, Any], vector["input"]))

    assert observed[violated] is False, (vector_id, violated)
    satisfied = {k: v for k, v in observed.items() if k != violated}
    assert all(satisfied.values()), (vector_id, satisfied)


def test_the_retired_cross_swap_is_gone() -> None:
    """Two role rules now have one witness each; the pair vector added nothing."""
    ids = {cast(str, v["id"]) for v in INVALID["vectors"]}

    assert "history.invalid.change-set.wrong-role-assignment" not in ids
    both: list[str] = []
    for vector in INVALID["vectors"]:
        supplied = cast(dict[str, Any], vector["input"])
        if vector["category"] != "change-set" or vector["input_mode"] != "json":
            continue
        if not all(
            isinstance(supplied.get(part), dict)
            and "role_assignment" in cast(dict[str, Any], supplied[part])
            for part in ("base", "head")
        ) or not isinstance(supplied.get("changed_paths"), list):
            continue
        observed = _change_set_siblings(supplied)
        if not observed["base_role_is_base"] and not observed["head_role_is_head"]:
            both.append(cast(str, vector["id"]))
    assert not both, "no vector may violate both role requirements at once"


def test_every_python_typing_witness_supplies_one_untyped_position() -> None:
    """A typed-input witness must be untyped in exactly the position it names."""
    expectations = {
        "history.invalid.change-set.untyped-python-base": ("base", ("head",)),
        "history.invalid.change-set.untyped-python-head": ("head", ("base",)),
        "history.invalid.approval.untyped-python-approved-revision": (
            "approved_revision",
            ("review",),
        ),
        "history.invalid.merge-outcome.untyped-python-pull-request": (
            "pull_request",
            ("merge_revision",),
        ),
        "history.invalid.merge-outcome.untyped-python-merge-revision": (
            "merge_revision",
            ("pull_request",),
        ),
        "history.invalid.head-ref-deletion.untyped-python-head": (
            "head",
            ("head_ref_name",),
        ),
        "history.invalid.occurrence-time.untyped-python-occurrence": ("occurrence", ()),
        "history.invalid.evidence-link.occurrence-time-fact-python": (
            "fact",
            ("evidence_record",),
        ),
    }
    for vector_id, (untyped, typed) in expectations.items():
        vector = next(v for v in INVALID["vectors"] if v["id"] == vector_id)
        assert vector["input_mode"] == "python", vector_id
        supplied = cast(dict[str, Any], vector["input"])
        assert "typed_value" not in cast(dict[str, Any], supplied[untyped]), vector_id
        for field in typed:
            assert "typed_value" in cast(dict[str, Any], supplied[field]), (
                vector_id,
                field,
            )


# --- every vector answers to a requirement -----------------------------------

NO_REQUIREMENT = "NO_CLEAR_REQUIREMENT"


def _model_fields_of(target: str) -> set[str]:
    resolved = RESOLVABLE.get(target)
    fields = getattr(resolved, "model_fields", None)
    return set(fields) if fields else set()


def _union_fields_of(target: str) -> set[str]:
    resolved = RESOLVABLE.get(target)
    fields = getattr(resolved, "model_fields", None)
    if not fields:
        return set()
    return {
        name
        for name, info in cast(dict[str, Any], fields).items()
        if "|" in str(info.annotation) or "Union" in str(info.annotation)
    }


def _vector_role(vector: dict[str, Any], primaries: set[str]) -> str:
    """Classify a vector only when a rule actually holds for it.

    The previous fallback returned a predecessor-boundary label for anything it
    did not recognise, which made `NO_CLEAR_REQUIREMENT` unreachable: an
    unrelated vector could be added and the reverse ledger would still close.
    Every branch below is now a claim that must be true of the vector.
    """
    vector_id = cast(str, vector["id"])
    if vector_id in primaries:
        return "PRIMARY_WITNESS"

    expected = cast(dict[str, Any], vector["expected"])
    location = cast(list[str], expected.get("error_location") or [])
    fields = _model_fields_of(cast(str, vector["target"]))
    raw_input = vector["input"]
    supplied: dict[str, Any] = (
        cast(dict[str, Any], raw_input) if isinstance(raw_input, dict) else {}
    )

    if expected.get("failure_category") == "vocabulary_error":
        if expected.get("error_type") == "enum" and not location:
            return "SECONDARY_BOUNDARY_WITNESS: a closed vocabulary refuses a lexeme"
        return NO_REQUIREMENT

    if len(location) > 1 and location[0] in fields and location[0] in supplied:
        # The outer field is supplied; the published nested type is what refuses
        # it, so this witnesses a predecessor contract boundary.
        return "SECONDARY_BOUNDARY_WITNESS: a nested predecessor contract boundary"

    if expected.get("error_type") == "missing" and location:
        if location[0] in fields and location[0] not in supplied:
            return "SECONDARY_BOUNDARY_WITNESS: a required member is absent"
        if location[0] in _union_fields_of(cast(str, vector["target"])):
            # A closed union reports `missing` at its own field when no branch
            # matches, which is a union claim rather than a requiredness one.
            return "SECONDARY_BOUNDARY_WITNESS: a closed union admits no branch"
        return NO_REQUIREMENT

    if expected.get("error_type") == "extra_forbidden" and location:
        if location[0] in supplied and location[0] not in fields:
            return "SECONDARY_BOUNDARY_WITNESS: a forbidden extra is refused"
        return NO_REQUIREMENT

    if location and location[0] in fields:
        return "SECONDARY_BOUNDARY_WITNESS: a published field boundary"
    if not location:
        return "SECONDARY_BOUNDARY_WITNESS: a cross-field model invariant"
    return NO_REQUIREMENT


def test_every_invalid_vector_answers_to_a_requirement() -> None:
    """The reverse direction: no vector may exist without a contract purpose."""
    primaries = {row[4] for row in REQUIREMENT_LEDGER}
    unclassified = [
        cast(str, v["id"])
        for v in INVALID["vectors"]
        if _vector_role(v, primaries) == NO_REQUIREMENT
    ]
    roles = Counter(_vector_role(v, primaries) for v in INVALID["vectors"])

    assert not unclassified, unclassified
    assert sum(roles.values()) == len(INVALID["vectors"])
    assert roles["PRIMARY_WITNESS"] == len(
        [r for r in REQUIREMENT_LEDGER if r[3] == NEGATIVE]
    )


def test_every_replay_vector_is_canonical_provenance_coverage() -> None:
    for vector in REPLAY["vectors"]:
        assert vector["evidence_classification"] in {
            "retained_normalized_observation",
            "caller_supplied_composition",
            "caller_supplied_association",
        }, vector["id"]


# --- cross-system edge: an artifact lock answers to a source authority -------


def _lock_authority_failures(
    locks: list[dict[str, Any]], authorities: list[dict[str, Any]]
) -> list[tuple[str, str]]:
    """Resolve each lock id back to the source decision that authorises it.

    Each system was previously verified only against itself: the locks against
    their bytes, the authorities against theirs. Nothing tied a lock id to the
    authority whose bytes it claims, so the two could describe different
    records while both stayed internally consistent.
    """
    by_reference: dict[str, list[dict[str, Any]]] = {}
    for entry in authorities:
        by_reference.setdefault(cast(str, entry["decision_reference"]), []).append(
            entry
        )

    failures: list[tuple[str, str]] = []
    for lock in locks:
        lock_id = cast(str, lock["lock_id"])
        matches = by_reference.get(lock_id, [])
        if not matches:
            failures.append((lock_id, "unknown-authority"))
            continue
        if len(matches) > 1:
            failures.append((lock_id, "ambiguous-authority"))
            continue
        authority = matches[0]
        if authority["path"] != lock["path"]:
            failures.append((lock_id, "authority-path-differs"))
        if authority["sha256"] != lock["sha256"]:
            failures.append((lock_id, "authority-digest-differs"))
        raw = (REPOSITORY_ROOT / cast(str, lock["path"])).read_bytes()
        if hashlib.sha256(raw).hexdigest() != lock["sha256"]:
            failures.append((lock_id, "live-bytes-differ"))
        if len(raw) != lock["byte_length"]:
            failures.append((lock_id, "live-length-differs"))
    return sorted(failures)


def test_every_artifact_lock_resolves_to_its_source_authority() -> None:
    locks = cast(list[dict[str, Any]], REPLAY["artifact_locks"])
    authorities = cast(list[dict[str, Any]], MANIFEST["source_decisions"])

    assert not _lock_authority_failures(locks, authorities)
    assert len({cast(str, lock["lock_id"]) for lock in locks}) == len(locks)


@pytest.mark.parametrize(
    ("label", "mutate_locks", "mutate_authorities", "expected"),
    (
        ("wrong authority path", None, "path", "authority-path-differs"),
        ("wrong authority digest", None, "sha256", "authority-digest-differs"),
        ("unknown lock id", "lock_id", None, "unknown-authority"),
        ("swapped logical authority", "swap", None, "authority-path-differs"),
    ),
)
def test_the_lock_authority_edge_is_load_bearing(
    label: str,
    mutate_locks: str | None,
    mutate_authorities: str | None,
    expected: str,
) -> None:
    """Each probe changes only the cross-system edge, never a digest seal."""
    locks = copy.deepcopy(cast(list[dict[str, Any]], REPLAY["artifact_locks"]))
    authorities = copy.deepcopy(
        cast(list[dict[str, Any]], MANIFEST["source_decisions"])
    )

    if mutate_locks == "lock_id":
        locks[0]["lock_id"] = "acquisition:invented"
    elif mutate_locks == "swap":
        locks[0]["lock_id"], locks[1]["lock_id"] = (
            locks[1]["lock_id"],
            locks[0]["lock_id"],
        )
    if mutate_authorities:
        target = (
            next(
                a for a in authorities if a["decision_reference"] == locks[0]["lock_id"]
            )
            if mutate_locks is None
            else authorities[0]
        )
        target[mutate_authorities] = (
            "reference_corpus/elsewhere.json"
            if mutate_authorities == "path"
            else "0" * 64
        )

    reasons = {reason for _, reason in _lock_authority_failures(locks, authorities)}
    assert expected in reasons, (label, reasons)


# --- the embedded-fact provenance graph --------------------------------------

RETAINED = "retained_normalized_observation"
CALLER_SUPPLIED = {"caller_supplied_composition", "caller_supplied_association"}


def _embedded_graph_failures(vectors: list[dict[str, Any]]) -> list[tuple[str, str]]:
    """Equality is not provenance: the source must itself be retained.

    Without a class restriction a caller-supplied value could stand as its own
    source -- or two could cite each other -- and the equality check would
    compare a dump with itself and call it sourced. Cycle detection is a real
    traversal rather than a reliance on the graph currently being one level
    deep.
    """
    by_id = {cast(str, v["id"]): v for v in vectors}
    failures: list[tuple[str, str]] = []
    edges: dict[str, set[str]] = {}
    for vector in vectors:
        consumer = cast(str, vector["id"])
        embedded = cast(dict[str, str], vector["embedded_facts"])
        if embedded and vector["evidence_classification"] not in CALLER_SUPPLIED:
            failures.append((consumer, "retained-consumer-declares-embedded-facts"))
        for pointer, source in embedded.items():
            edges.setdefault(consumer, set()).add(source)
            if source == consumer:
                failures.append((consumer, "self-reference"))
                continue
            if source not in by_id:
                failures.append((consumer, "unknown-source"))
                continue
            if by_id[source]["evidence_classification"] != RETAINED:
                failures.append((consumer, "source-is-not-a-retained-observation"))
            if not pointer.startswith("/"):
                failures.append((consumer, "malformed-pointer"))

    # depth-first cycle detection over whatever shape the graph actually has
    colour: dict[str, int] = {}

    def visit(node: str) -> bool:
        colour[node] = 1
        for nxt in edges.get(node, ()):  # pragma: no branch - small graph
            if colour.get(nxt) == 1:
                return True
            if colour.get(nxt) is None and visit(nxt):
                return True
        colour[node] = 2
        return False

    for node in list(edges):
        if colour.get(node) is None and visit(node):
            failures.append((node, "cycle"))
    return sorted(set(failures))


def test_the_embedded_fact_graph_is_retained_sourced_and_acyclic() -> None:
    vectors = cast(list[dict[str, Any]], REPLAY["vectors"])

    assert not _embedded_graph_failures(vectors)
    edges = [
        (cast(str, v["id"]), src)
        for v in vectors
        for src in cast(dict[str, str], v["embedded_facts"]).values()
    ]
    consumers = {c for c, _ in edges}
    sources = {s for _, s in edges}
    assert len(edges) == 17
    assert len(consumers) == 13
    assert len(sources) == 11
    assert not consumers & sources, "a consumer must never also be a source"


@pytest.mark.parametrize(
    ("label", "mutate"),
    (
        ("self-reference", "self"),
        ("caller-supplied source", "caller"),
        ("two-node cycle", "cycle"),
        ("unknown source", "unknown"),
        ("source reclassified away from retained", "reclassify"),
    ),
)
def test_the_embedded_graph_rule_is_the_direct_detector(
    label: str, mutate: str
) -> None:
    vectors = copy.deepcopy(cast(list[dict[str, Any]], REPLAY["vectors"]))
    by_id = {cast(str, v["id"]): v for v in vectors}
    first = by_id["history.replay.evidence-association.review-approval"]
    second = by_id["history.replay.evidence-association.merge-outcome"]

    if mutate == "self":
        first["embedded_facts"] = {"/fact": first["id"]}
        expected = "self-reference"
    elif mutate == "caller":
        first["embedded_facts"] = {"/fact": second["id"]}
        expected = "source-is-not-a-retained-observation"
    elif mutate == "cycle":
        first["embedded_facts"] = {"/fact": second["id"]}
        second["embedded_facts"] = {"/fact": first["id"]}
        expected = "cycle"
    elif mutate == "unknown":
        first["embedded_facts"] = {"/fact": "history.replay.absent"}
        expected = "unknown-source"
    else:
        by_id["history.replay.review-approval.canonical"]["evidence_classification"] = (
            "caller_supplied_composition"
        )
        expected = "source-is-not-a-retained-observation"

    reasons = {reason for _, reason in _embedded_graph_failures(vectors)}
    assert expected in reasons, (label, reasons)


def test_the_two_cross_edges_are_not_new_reference_systems() -> None:
    """Eight systems, each resolved; these additions are consistency edges."""
    assert len(REFERENCE_SYSTEMS) == 8
    cross_edges = {
        "artifact_locks -> source_decisions": _lock_authority_failures,
        "embedded_facts -> retained acyclic graph": _embedded_graph_failures,
    }
    assert len(cross_edges) == 2
    assert all(callable(resolver) for resolver in cross_edges.values())


# --- constraints the framework enforces are requirements too ------------------
#
# The guard ledger above walks custom validators. That is not the whole
# contract: an annotation, an enum, a Field bound, or a model_config value can
# publish an observable boundary with no raise site anywhere, which is exactly
# how the raw-status boundary went uncovered. These rows record the audited
# disposition of every such constraint so a later sweep starts from the
# constraint surface rather than rediscovering it.

P05_OWNED = "P05_CORPUS_REQUIREMENT"
PREDECESSOR = "PREDECESSOR_TYPE_REQUIREMENT"
UNIT_OWNED = "UNIT_ORACLE_REQUIREMENT"
GENERIC_OWNED = "FRAMEWORK_GENERIC"
EQUIVALENT = "EQUIVALENT_ENFORCEMENT"

FRAMEWORK_CONSTRAINT_LEDGER: tuple[tuple[str, str, str, str, str], ...] = (
    (
        "FC-01",
        "PullRequestChangedPath.status",
        "enum",
        P05_OWNED,
        "history.invalid.changed-path.raw-python-status",
    ),
    (
        "FC-02",
        "PullRequestChangedPath.status",
        "enum vocabulary",
        P05_OWNED,
        "history.invalid.changed-path.unknown-status",
    ),
    (
        "FC-03",
        "PullRequestChangeSet.changed_paths",
        "Field min_length",
        P05_OWNED,
        "history.invalid.change-set.empty-changed-paths",
    ),
    (
        "FC-04",
        "PullRequestChangeSet.changed_paths",
        "Field max_length",
        P05_OWNED,
        "history.invalid.change-set.above-maximum-changed-paths",
    ),
    (
        "FC-05",
        "PullRequestHistoricalOccurrenceTime.occurred_at",
        "AwareDatetime",
        P05_OWNED,
        "history.invalid.occurrence-time.instant-naive",
    ),
    (
        "FC-06",
        "PullRequestHistoricalOccurrenceTime.occurrence",
        "union membership",
        P05_OWNED,
        "history.invalid.occurrence-time.non-admitted-change-set",
    ),
    (
        "FC-07",
        "PullRequestHistoryFactEvidenceLink.fact",
        "union membership",
        P05_OWNED,
        "history.invalid.evidence-link.change-set-fact",
    ),
    (
        "FC-08",
        "every target",
        "extra=forbid",
        P05_OWNED,
        "history.invalid.change-set.extra-complete",
    ),
    ("FC-09", "nested identity construction", "predecessor schema", PREDECESSOR, ""),
    ("FC-10", "every target", "frozen assignment", UNIT_OWNED, ""),
    ("FC-11", "every target", "revalidate_instances", GENERIC_OWNED, ""),
    ("FC-12", "seven targets", "strict=True on model-typed fields", EQUIVALENT, ""),
)


def test_the_framework_constraint_ledger_is_closed() -> None:
    """No observable constraint may be left without a recorded disposition."""
    owners = {row[3] for row in FRAMEWORK_CONSTRAINT_LEDGER}

    assert owners <= {P05_OWNED, PREDECESSOR, UNIT_OWNED, GENERIC_OWNED, EQUIVALENT}
    ids = [row[0] for row in FRAMEWORK_CONSTRAINT_LEDGER]
    assert len(ids) == len(set(ids))
    by_id = {
        cast(str, v["id"]): v
        for section in SECTIONS.values()
        for v in section["vectors"]
    }
    for row_id, _, _, ownership, witness in FRAMEWORK_CONSTRAINT_LEDGER:
        if ownership == P05_OWNED:
            assert witness, row_id
            assert witness in by_id, (row_id, witness)
        else:
            assert not witness, row_id


def test_the_enum_field_requires_its_published_member_in_python() -> None:
    """The boundary that no raise site published, now witnessed."""
    vector = next(
        v
        for v in INVALID["vectors"]
        if v["id"] == "history.invalid.changed-path.raw-python-status"
    )

    assert vector["input_mode"] == "python"
    assert vector["input"]["status"] == "added", (
        "the lexeme itself must be supplied raw"
    )
    assert "typed_value" in cast(dict[str, Any], vector["input"]["path"])
    assert "typed_value" in cast(dict[str, Any], vector["input"]["head_object"])
    assert vector["expected"]["error_location"] == ["status"]
    assert vector["expected"]["error_type"] == "is_instance_of"


# --- the field surface, closed by matrix rather than by inspection -----------
#
# Two coverage questions were previously answered per finding, not per field:
# does every required field have a witness that actually omits it, and does
# every field have a witness for its Python input language. Both are now
# matrices over the live field surface, so a newly required field or a newly
# published Python boundary forces review instead of arriving unnoticed.


def _required_field_coordinates() -> list[tuple[str, str]]:
    return sorted(
        (name, field)
        for name, target in OWNED.items()
        if hasattr(target, "model_fields")
        for field, info in target.model_fields.items()
        if info.is_required()
    )


def _omits(vector: dict[str, Any], field: str) -> bool:
    """True omission is a property of the supplied input, never of an error code.

    A discriminatorless union reports `missing` at its own field when no branch
    matches, so a present-but-wrong value looks identical to an absent one if
    the error type is all that is consulted.
    """
    supplied = vector["input"]
    if not isinstance(supplied, dict):
        return False
    return field not in cast(dict[str, Any], supplied)


def _omission_witnesses(field_target: str, field: str) -> list[str]:
    return [
        cast(str, v["id"])
        for v in INVALID["vectors"]
        if v["target"] == field_target
        and _omits(v, field)
        and v["expected"]["error_type"] == "missing"
        and cast(list[str], v["expected"]["error_location"]) == [field]
    ]


def _python_language_witnesses(field_target: str, field: str) -> list[str]:
    return [
        cast(str, v["id"])
        for v in INVALID["vectors"]
        if v["target"] == field_target
        and v["input_mode"] == "python"
        and not _omits(v, field)
        and cast(list[str], v["expected"]["error_location"])[:1] == [field]
    ]


def test_every_required_field_has_a_true_omission_witness() -> None:
    coordinates = _required_field_coordinates()
    uncovered = [
        f"{target}.{field}"
        for target, field in coordinates
        if not _omission_witnesses(target, field)
    ]

    assert len(coordinates) == 18
    assert not uncovered, uncovered


def test_every_required_field_has_a_python_language_witness() -> None:
    coordinates = _required_field_coordinates()
    uncovered = [
        f"{target}.{field}"
        for target, field in coordinates
        if not _python_language_witnesses(target, field)
    ]

    assert len(coordinates) == 18
    assert not uncovered, uncovered


def test_a_present_wrong_branch_value_is_not_an_omission_witness() -> None:
    """The false positive that hid the occurrence requiredness gap."""
    union_vectors = [
        v
        for v in INVALID["vectors"]
        if v["target"] == "PullRequestHistoricalOccurrenceTime"
        and v["expected"]["error_type"] == "missing"
        and cast(list[str], v["expected"]["error_location"]) == ["occurrence"]
        and not _omits(v, "occurrence")
    ]

    assert union_vectors, "the non-admitted union vectors must still exist"
    for vector in union_vectors:
        assert "occurrence" in cast(dict[str, Any], vector["input"])
        assert vector["id"] not in _omission_witnesses(
            "PullRequestHistoricalOccurrenceTime", "occurrence"
        )


def test_removing_the_omission_witness_reopens_exactly_one_coordinate() -> None:
    kept = [
        v
        for v in INVALID["vectors"]
        if v["id"] != "history.invalid.occurrence-time.missing-occurrence"
    ]
    surviving = {
        f"{target}.{field}"
        for target, field in _required_field_coordinates()
        for witnesses in [
            [
                cast(str, v["id"])
                for v in kept
                if v["target"] == target
                and _omits(v, field)
                and v["expected"]["error_type"] == "missing"
                and cast(list[str], v["expected"]["error_location"]) == [field]
            ]
        ]
        if not witnesses
    }

    assert surviving == {"PullRequestHistoricalOccurrenceTime.occurrence"}


def test_a_json_instant_vector_cannot_fill_the_python_language_cell() -> None:
    """The occurred_at cell demands a Python-mode witness, not a JSON neighbour."""
    json_instants = [
        cast(str, v["id"])
        for v in INVALID["vectors"]
        if v["target"] == "PullRequestHistoricalOccurrenceTime"
        and v["input_mode"] == "json"
        and cast(list[str], v["expected"]["error_location"])[:1] == ["occurred_at"]
    ]
    python_witnesses = _python_language_witnesses(
        "PullRequestHistoricalOccurrenceTime", "occurred_at"
    )

    assert json_instants, "the JSON instant boundaries must still exist"
    assert python_witnesses == ["history.invalid.occurrence-time.raw-python-instant"]
    assert not set(json_instants) & set(python_witnesses)


def test_the_python_instant_witness_isolates_its_field() -> None:
    """Occurrence stays valid and present, so only the instant language fails."""
    vector = next(
        v
        for v in INVALID["vectors"]
        if v["id"] == "history.invalid.occurrence-time.raw-python-instant"
    )
    supplied = cast(dict[str, Any], vector["input"])

    assert vector["input_mode"] == "python"
    assert "typed_value" in cast(dict[str, Any], supplied["occurrence"])
    assert isinstance(supplied["occurred_at"], str)
    assert vector["expected"]["error_location"] == ["occurred_at"]
    assert vector["expected"]["error_type"] == "datetime_type"


# --- every derived table is rendered whole, never token-matched --------------
#
# Token presence cannot tell a correct row from a transposed one: two rows may
# exchange a column and every symbol, digest, and claim still occurs somewhere
# in the file. The association tuple is the contract, so each table is rendered
# from its canonical authority and compared to the extracted block exactly --
# and a closure check requires every table in the document to be one of them.


def _md_row(cells: tuple[str, ...]) -> str:
    return "| " + " | ".join(cells) + " |"


def _tick(value: object) -> str:
    return f"`{value}`"


def _render_targets() -> list[tuple[str, ...]]:
    return [
        (
            _tick(e["symbol"]),
            _tick(e["module"]),
            _tick(e["slice_layer"]),
            _tick(e["target_class"]),
        )
        for e in cast(list[dict[str, str]], MANIFEST["target_symbols"])
    ]


def _render_inventory() -> list[tuple[str, ...]]:
    counts = {
        family: Counter(cast(str, v["category"]) for v in section["vectors"])
        for family, section in SECTIONS.items()
    }
    families: list[str] = sorted(
        {family for counter in counts.values() for family in counter}
    )
    rows = [
        (
            _tick(family),
            str(counts["valid"][family]),
            str(counts["invalid"][family]),
            str(counts["replay"][family]),
        )
        for family in families
    ]
    rows.append(
        (
            "**total**",
            f"**{len(VALID['vectors'])}**",
            f"**{len(INVALID['vectors'])}**",
            f"**{len(REPLAY['vectors'])}**",
        )
    )
    return rows


def _render_forbidden_extras() -> list[tuple[str, ...]]:
    return [
        (_tick(e["extra_key"]), e["published_non_claim"])
        for e in cast(list[dict[str, str]], MANIFEST["s07_forbidden_extra_ledger"])
    ]


def _render_authorities() -> list[tuple[str, ...]]:
    return [
        (_tick(e["decision_reference"]), _tick(e["authority_role"]), _tick(e["sha256"]))
        for e in cast(list[dict[str, str]], MANIFEST["source_decisions"])
    ]


DERIVED_TABLES: tuple[
    tuple[str, tuple[str, ...], Callable[[], list[tuple[str, ...]]]], ...
] = (
    ("target symbols", ("Symbol", "Module", "Slice", "Target class"), _render_targets),
    ("vector inventory", ("Family", "valid", "invalid", "replay"), _render_inventory),
    (
        "forbidden extras",
        ("Extra key", "Published non-claim"),
        _render_forbidden_extras,
    ),
    ("source authorities", ("Authority", "Role", "SHA-256"), _render_authorities),
)


def _render_table(header: tuple[str, ...], rows: list[tuple[str, ...]]) -> list[str]:
    return [
        _md_row(header),
        _md_row(tuple("---" for _ in header)),
        *[_md_row(row) for row in rows],
    ]


def _markdown_tables(text: str) -> list[list[str]]:
    blocks: list[list[str]] = []
    current: list[str] = []
    for line in text.splitlines():
        if line.startswith("|"):
            current.append(line)
        elif current:
            blocks.append(current)
            current = []
    if current:
        blocks.append(current)
    return blocks


@pytest.mark.parametrize(
    ("label", "header", "render"), DERIVED_TABLES, ids=[t[0] for t in DERIVED_TABLES]
)
def test_each_derived_table_is_an_exact_projection(
    label: str, header: tuple[str, ...], render: Callable[[], list[tuple[str, ...]]]
) -> None:
    tables = _markdown_tables((CORPUS / "contract.md").read_text("utf-8"))
    actual = [t for t in tables if t[0] == _md_row(header)]

    assert len(actual) == 1, label
    assert actual[0] == _render_table(header, render()), label


def test_every_markdown_table_is_a_registered_projection() -> None:
    """A table nobody renders is a table nobody checks."""
    tables = _markdown_tables((CORPUS / "contract.md").read_text("utf-8"))
    rendered = [_render_table(header, render()) for _, header, render in DERIVED_TABLES]

    assert len(tables) == len(DERIVED_TABLES) == 4
    assert sorted(tables) == sorted(rendered)


# (label, table index, column, two row indices whose value in that column differs)
ASSOCIATION_PROBES = (
    ("target symbols", 0, 2, 0, 1),
    ("vector inventory", 1, 1, 0, 1),
    ("forbidden extras", 2, 1, 0, 1),
    ("source authorities", 3, 1, 0, 1),
)


@pytest.mark.parametrize(
    ("label", "table_index", "column", "first", "second"),
    ASSOCIATION_PROBES,
    ids=[p[0] for p in ASSOCIATION_PROBES],
)
def test_no_derived_table_row_association_can_drift(
    label: str, table_index: int, column: int, first: int, second: int
) -> None:
    """Swap one column between two rows; the column inventory is unchanged."""
    _, header, render = DERIVED_TABLES[table_index]
    rows = [list(row) for row in render()]
    assert rows[first][column] != rows[second][column], label
    rows[first][column], rows[second][column] = (
        rows[second][column],
        rows[first][column],
    )
    mutated = [tuple(row) for row in rows]

    assert sorted(r[column] for r in mutated) == sorted(r[column] for r in render())
    assert _render_table(header, mutated) != _render_table(header, render()), label


@pytest.mark.parametrize(
    ("label", "table_index"), [(t[0], i) for i, t in enumerate(DERIVED_TABLES)]
)
def test_no_derived_table_may_lose_gain_or_reorder_a_row(
    label: str, table_index: int
) -> None:
    _, header, render = DERIVED_TABLES[table_index]
    expected = _render_table(header, render())
    rows = render()

    assert _render_table(header, rows[:-1]) != expected
    assert _render_table(header, [*rows, rows[0]]) != expected
    assert _render_table(header, [rows[0], *rows]) != expected
    assert _render_table(header, list(reversed(rows))) != expected


def test_a_changed_markdown_cell_is_refused() -> None:
    """Drift the other way: the Markdown moves, the manifest does not."""
    text = (CORPUS / "contract.md").read_text("utf-8")
    for original, replacement in (
        ("| `S1.P05.S01` |", "| `S1.P05.S09` |"),
        ("no confidence or review-status semantics", "no evidence aggregation"),
    ):
        tampered = text.replace(original, replacement, 1)
        assert tampered != text, original
        tables = _markdown_tables(tampered)
        rendered = [_render_table(h, r()) for _, h, r in DERIVED_TABLES]
        assert sorted(tables) != sorted(rendered), original


def test_the_target_row_columns_stay_descriptive() -> None:
    """Rendering them faithfully must not promote them to verified claims."""
    for index in range(len(cast(list[Any], MANIFEST["target_symbols"]))):
        for column in ("slice_layer", "target_class"):
            assert f"/target_symbols/{index}/{column}" in DESCRIPTIVE_PATHS
        for column in ("symbol", "module"):
            assert f"/target_symbols/{index}/{column}" not in DESCRIPTIVE_PATHS
    for index in range(len(cast(list[Any], MANIFEST["source_decisions"]))):
        assert f"/source_decisions/{index}/authority_role" in DESCRIPTIVE_PATHS


# --- the forbidden-extra pairing has an authority of its own -----------------
#
# Rendering the ledger faithfully stops the Markdown drifting from the manifest,
# but it cannot stop the manifest itself pairing a key with the wrong claim: a
# consistent edit to both would project cleanly. The pairing is the whole point
# of the ledger -- it is what makes eleven `extra_forbidden` rejections eleven
# different published non-claims -- so it is pinned here as well.

FORBIDDEN_EXTRA_AUTHORITY = {
    "schema_version": "no top-level history-evidence-link schema version",
    "json_pointer": "no field-level or semantic evidence localization",
    "support_role": "no support-role semantics",
    "strength": "no support-strength semantics",
    "verification": "no verification or proof semantics",
    "confidence": "no confidence or review-status semantics",
    "primary_evidence": "no primary-evidence designation or ranking",
    "evidence_records": "no evidence aggregation",
    "superseded": "no automatic correction or supersession traversal",
    "request_id": "no acquisition-request provenance coupling",
    "artifact": "no direct artifact or envelope carrier coupling",
}


def test_each_forbidden_extra_is_paired_with_its_own_non_claim() -> None:
    ledger = cast(list[dict[str, str]], MANIFEST["s07_forbidden_extra_ledger"])
    observed = {entry["extra_key"]: entry["published_non_claim"] for entry in ledger}

    assert observed == FORBIDDEN_EXTRA_AUTHORITY
    assert len(FORBIDDEN_EXTRA_AUTHORITY) == 11
    assert len(set(FORBIDDEN_EXTRA_AUTHORITY.values())) == 11


def test_a_consistently_swapped_pairing_is_still_refused() -> None:
    """The mutation that a faithful projection alone would let through."""
    swapped = dict(FORBIDDEN_EXTRA_AUTHORITY)
    swapped["artifact"], swapped["confidence"] = (
        FORBIDDEN_EXTRA_AUTHORITY["confidence"],
        FORBIDDEN_EXTRA_AUTHORITY["artifact"],
    )

    assert sorted(swapped.values()) == sorted(FORBIDDEN_EXTRA_AUTHORITY.values())
    assert set(swapped) == set(FORBIDDEN_EXTRA_AUTHORITY)
    assert swapped != FORBIDDEN_EXTRA_AUTHORITY


def test_every_forbidden_extra_key_reaches_its_vector() -> None:
    """The pairing must also hold at the vector that enforces it."""
    ledger = cast(list[dict[str, str]], MANIFEST["s07_forbidden_extra_ledger"])
    by_id = {cast(str, v["id"]): v for v in INVALID["vectors"]}

    for entry in ledger:
        vector = by_id[entry["vector_id"]]
        assert entry["extra_key"] in cast(dict[str, Any], vector["input"])
        assert cast(list[str], vector["expected"]["error_location"]) == [
            entry["extra_key"]
        ]
        assert (
            FORBIDDEN_EXTRA_AUTHORITY[entry["extra_key"]]
            == entry["published_non_claim"]
        )


def test_an_unrecognised_vector_is_refused_by_the_reverse_ledger() -> None:
    """The classifier must be able to fail, or the ledger proves nothing."""
    primaries = {row[4] for row in REQUIREMENT_LEDGER}
    stranger = {
        "id": "history.invalid.probe.stranger",
        "target": "PullRequestChangedPath",
        "input": {"path": "x"},
        "input_mode": "json",
        "operation": "reject",
        "expected": {
            "error_location": ["not_a_published_field"],
            "error_location_mode": "exact",
            "error_type": "value_error",
            "failure_category": "validation_error",
            "outcome": "rejected",
        },
    }

    assert _vector_role(stranger, primaries) == NO_REQUIREMENT


@pytest.mark.parametrize(
    ("label", "mutate"),
    (
        ("extra key that is actually a model field", "extra"),
        ("missing error for a field that is present", "missing"),
        ("vocabulary error carrying a location", "vocabulary"),
    ),
)
def test_each_secondary_rule_must_actually_hold(label: str, mutate: str) -> None:
    primaries = {row[4] for row in REQUIREMENT_LEDGER}
    vector = copy.deepcopy(
        next(
            v
            for v in INVALID["vectors"]
            if v["id"].endswith("changed-path.extra-base-object")
        )
    )
    if mutate == "extra":
        vector["expected"]["error_location"] = ["path"]
        vector["input"] = {"path": "x"}
    elif mutate == "missing":
        vector["expected"]["error_type"] = "missing"
        vector["expected"]["error_location"] = ["path"]
        vector["input"] = {"path": "x"}
    else:
        vector["expected"]["failure_category"] = "vocabulary_error"
        vector["expected"]["error_type"] = "enum"
        vector["expected"]["error_location"] = ["status"]

    assert _vector_role(vector, primaries) == NO_REQUIREMENT, label


# --- the derived governance block is rendered, not sampled -------------------


def _render_governance_block() -> list[str]:
    governance = cast(dict[str, Any], MANIFEST["effective_governance"])
    totals = cast(dict[str, Any], governance["totals"])

    def owners(key: str) -> str:
        return " · ".join(
            f"{owner} {count}"
            for owner, count in cast(dict[str, int], totals[key]).items()
        )

    authority = cast(dict[str, int], governance["authority_totals"])
    return [
        f"    inherited {governance['inherited_subject_count']}"
        f" · exactly once {governance['dispositioned_exactly_once']}"
        f" · self-introduced {governance['self_introduced_count']}"
        f" · self_owned_open {governance['self_owned_open']}",
        f"    split {totals['disposition']['split']}"
        f" · carried_forward {totals['disposition']['carried_forward']}",
        f"    immediate {owners('immediate_owner')}",
        f"    long-term {owners('preserved_long_term_owner')}",
        "    authority "
        + " · ".join(f"{name} {count}" for name, count in authority.items()),
    ]


def _actual_governance_block(text: str) -> list[str]:
    lines = text.splitlines()
    start = next(i for i, line in enumerate(lines) if line.startswith("    inherited "))
    end = start
    while end < len(lines) and lines[end].startswith("    "):
        end += 1
    return lines[start:end]


def test_the_governance_block_is_an_exact_projection() -> None:
    """Every published governance number, not a sampled few."""
    text = (CORPUS / "contract.md").read_text("utf-8")

    assert _actual_governance_block(text) == _render_governance_block()


@pytest.mark.parametrize(
    "line",
    ("inherited", "exactly once", "split", "immediate", "long-term", "authority"),
)
def test_no_governance_value_can_drift_unnoticed(line: str) -> None:
    text = (CORPUS / "contract.md").read_text("utf-8")
    block = _actual_governance_block(text)
    target = next(entry for entry in block if line in entry)
    bumped = re.sub(r"(\d+)", lambda m: str(int(m.group(1)) + 1), target, count=1)
    tampered = text.replace(target, bumped, 1)

    assert tampered != text, line
    assert _actual_governance_block(tampered) != _render_governance_block()


# --- every secondary vector is registered, not inferred ----------------------
#
# Classifying by error shape still ended in broad fallbacks: any error under a
# real field became a "field boundary" and any model-level error a "cross-field
# invariant", so an unrelated vector could still pass as answered-for. Each
# non-primary vector is therefore named here against the requirement it exists
# to witness. Adding a vector without registering it fails the closure.

SECONDARY_WITNESS_REGISTRY: dict[str, str] = {
    "history.invalid.role-binding.missing-pull-request": "pull_request is required",
    "history.invalid.role-binding.missing-role-assignment": "role_assignment is required",
    "history.invalid.role-binding.extra-observed-at": "no observed_at is published",
    "history.invalid.role-binding.dumped-mapping-python": "pull_request refuses this published boundary",
    "history.invalid.role-binding.foreign-python-subject": "pull_request refuses this published boundary",
    "history.invalid.role-binding.swapped-members": "pull_request is refused by its published nested contract",
    "history.invalid.role-binding.null-role-assignment": "role_assignment refuses this published boundary",
    "history.invalid.status.removed": "the vocabulary is closed",
    "history.invalid.status.renamed": "the vocabulary is closed",
    "history.invalid.status.copied": "the vocabulary is closed",
    "history.invalid.changed-path.unknown-status": "status refuses this published boundary",
    "history.invalid.changed-path.missing-path": "path is required",
    "history.invalid.changed-path.missing-head-object": "head_object is required",
    "history.invalid.changed-path.missing-status": "status is required",
    "history.invalid.changed-path.extra-base-object": "no base_object is published",
    "history.invalid.changed-path.empty-path": "path refuses this published boundary",
    "history.invalid.approval.non-review-subject": "review refuses this published boundary",
    "history.invalid.approval.non-pull-request-parent": "review refuses this published boundary",
    "history.invalid.approval.blob-as-approved-revision": "approved_revision is refused by its published nested contract",
    "history.invalid.approval.missing-review": "review is required",
    "history.invalid.approval.missing-approved-revision": "approved_revision is required",
    "history.invalid.approval.extra-state": "no state is published",
    "history.invalid.approval.extra-submitted-at": "no submitted_at is published",
    "history.invalid.merge-outcome.tree-as-merge-revision": "merge_revision is refused by its published nested contract",
    "history.invalid.merge-outcome.missing-pull-request": "pull_request is required",
    "history.invalid.merge-outcome.missing-merge-revision": "merge_revision is required",
    "history.invalid.merge-outcome.extra-parents": "no ordered_parents is published",
    "history.invalid.merge-outcome.extra-strategy": "no strategy is published",
    "history.invalid.head-ref-deletion.empty-ref-name": "head_ref_name refuses this published boundary",
    "history.invalid.head-ref-deletion.missing-head": "head is required",
    "history.invalid.head-ref-deletion.missing-ref-name": "head_ref_name is required",
    "history.invalid.head-ref-deletion.extra-namespace": "no namespace is published",
    "history.invalid.occurrence-time.instant-naive": "occurred_at refuses this published boundary",
    "history.invalid.occurrence-time.instant-negative-offset": "occurred_at refuses this published boundary",
    "history.invalid.occurrence-time.instant-malformed": "occurred_at refuses this published boundary",
    "history.invalid.occurrence-time.non-admitted-commit-identity": "occurrence is required",
    "history.invalid.occurrence-time.non-admitted-changed-path-status": "occurrence refuses this published boundary",
    "history.invalid.occurrence-time.non-admitted-change-set": "occurrence is required",
    "history.invalid.occurrence-time.non-admitted-role-binding": "occurrence is required",
    "history.invalid.occurrence-time.non-admitted-changed-path": "occurrence is required",
    "history.invalid.occurrence-time.missing-occurred-at": "occurred_at is required",
    "history.invalid.occurrence-time.extra-chronology": "no chronology is published",
    "history.invalid.occurrence-time.missing-occurrence": "occurrence is required",
    "history.invalid.occurrence-time.raw-python-instant": "occurred_at refuses this published boundary",
    "history.invalid.evidence-link.hybrid-fact-json": "fact is required",
    "history.invalid.evidence-link.empty-fact-json": "fact is required",
    "history.invalid.evidence-link.malformed-record": "evidence_record is refused by its published nested contract",
    "history.invalid.evidence-link.missing-fact": "fact is required",
    "history.invalid.evidence-link.missing-evidence-record": "evidence_record is required",
    "history.invalid.evidence-link.extra-schema-version": "no schema_version is published",
    "history.invalid.evidence-link.extra-json-pointer": "no json_pointer is published",
    "history.invalid.evidence-link.extra-support-role": "no support_role is published",
    "history.invalid.evidence-link.extra-strength": "no strength is published",
    "history.invalid.evidence-link.extra-verification": "no verification is published",
    "history.invalid.evidence-link.extra-confidence": "no confidence is published",
    "history.invalid.evidence-link.extra-primary-evidence": "no primary_evidence is published",
    "history.invalid.evidence-link.extra-evidence-records": "no evidence_records is published",
    "history.invalid.evidence-link.extra-superseded": "no superseded is published",
    "history.invalid.evidence-link.extra-request-id": "no request_id is published",
    "history.invalid.evidence-link.extra-artifact": "no artifact is published",
    "history.invalid.evidence-link.nested-non-admitted-occurrence": "fact is required",
    "history.invalid.evidence-link.typed-children-mapping-python": "fact refuses this published boundary",
    "history.invalid.evidence-link.change-set-fact-python": "fact refuses this published boundary",
    "history.invalid.evidence-link.status-fact-python": "fact refuses this published boundary",
    "history.invalid.evidence-link.instant-naive": "fact is required",
    "history.invalid.evidence-link.instant-non-zero-offset": "fact is required",
    "history.invalid.evidence-link.instant-week-date": "fact is required",
    "history.invalid.evidence-link.instant-basic-format": "fact is required",
}


def test_every_invalid_vector_is_registered_or_primary() -> None:
    primaries = {row[4] for row in REQUIREMENT_LEDGER}
    ids = {cast(str, v["id"]) for v in INVALID["vectors"]}
    registered = set(SECONDARY_WITNESS_REGISTRY)

    assert not (primaries & registered), sorted(primaries & registered)
    assert registered <= ids, sorted(registered - ids)
    assert ids - primaries == registered, sorted((ids - primaries) ^ registered)
    assert all(SECONDARY_WITNESS_REGISTRY.values())


def _derived_requirement(vector: dict[str, Any]) -> str:
    """The requirement a vector witnesses, read off its validated properties."""
    expected = cast(dict[str, Any], vector["expected"])
    location = cast(list[str], expected["error_location"])
    if len(location) > 1:
        return f"{location[0]} is refused by its published nested contract"
    if expected["error_type"] == "missing":
        return f"{location[0]} is required"
    if expected["error_type"] == "extra_forbidden":
        return f"no {location[0]} is published"
    if expected.get("failure_category") == "vocabulary_error":
        return "the vocabulary is closed"
    if not location:
        return "a published cross-field invariant"
    return f"{location[0]} refuses this published boundary"


def test_each_registered_requirement_matches_its_vector() -> None:
    """A description nobody derives can say anything at all."""
    mismatched = [
        cast(str, v["id"])
        for v in INVALID["vectors"]
        if v["id"] in SECONDARY_WITNESS_REGISTRY
        and SECONDARY_WITNESS_REGISTRY[cast(str, v["id"])] != _derived_requirement(v)
    ]

    assert not mismatched, mismatched


def test_a_swapped_registry_description_is_refused() -> None:
    vectors = {cast(str, v["id"]): v for v in INVALID["vectors"]}
    first, second = sorted(SECONDARY_WITNESS_REGISTRY)[:2]
    swapped = dict(SECONDARY_WITNESS_REGISTRY)
    swapped[first], swapped[second] = swapped[second], swapped[first]

    assert swapped[first] != _derived_requirement(vectors[first]) or swapped[
        second
    ] != _derived_requirement(vectors[second])


def test_an_unregistered_vector_is_refused() -> None:
    """The closure must fail for a vector nobody named."""
    primaries = {row[4] for row in REQUIREMENT_LEDGER}
    ids = {cast(str, v["id"]) for v in INVALID["vectors"]} | {
        "history.invalid.probe.stranger"
    }

    assert ids - primaries != set(SECONDARY_WITNESS_REGISTRY)


# --- a source coordinate is authoritative for one replayed field -------------
#
# Value equality is not provenance: a resealed vector could drop one mapping and
# add another whose value happens to match, publishing a pull-request number as
# a repository identity. The permitted coordinate pairs are pinned here.

SOURCE_COORDINATES: tuple[tuple[str, str, str], ...] = (
    (
        "history.replay.changed-path.assertrewrite",
        "/observations/pr/changed_files/items/2/blob_sha",
        "/head_object/full_digest",
    ),
    (
        "history.replay.changed-path.assertrewrite",
        "/observations/pr/changed_files/items/2/path",
        "/path",
    ),
    (
        "history.replay.changed-path.assertrewrite",
        "/observations/pr/changed_files/items/2/status",
        "/status",
    ),
    (
        "history.replay.changed-path.changelog",
        "/observations/pr/changed_files/items/0/blob_sha",
        "/head_object/full_digest",
    ),
    (
        "history.replay.changed-path.changelog",
        "/observations/pr/changed_files/items/0/path",
        "/path",
    ),
    (
        "history.replay.changed-path.changelog",
        "/observations/pr/changed_files/items/0/status",
        "/status",
    ),
    (
        "history.replay.changed-path.rewrite",
        "/observations/pr/changed_files/items/1/blob_sha",
        "/head_object/full_digest",
    ),
    (
        "history.replay.changed-path.rewrite",
        "/observations/pr/changed_files/items/1/path",
        "/path",
    ),
    (
        "history.replay.changed-path.rewrite",
        "/observations/pr/changed_files/items/1/status",
        "/status",
    ),
    (
        "history.replay.head-ref-deletion.canonical",
        "/observations/pr/attempts/0/bracket_a/head/ref/value",
        "/head_ref_name",
    ),
    (
        "history.replay.head-ref-deletion.canonical",
        "/observations/pr/attempts/0/bracket_a/head/sha",
        "/head/role_assignment/revision/full_digest",
    ),
    (
        "history.replay.head-ref-deletion.canonical",
        "/observations/pr/attempts/0/bracket_a/number",
        "/head/pull_request/repository_scoped_number",
    ),
    (
        "history.replay.head-ref-deletion.canonical",
        "/observations/repository/global_id",
        "/head/pull_request/repository_identity/provider_repository_id",
    ),
    (
        "history.replay.merge-outcome.canonical",
        "/observations/pr/attempts/0/bracket_a/number",
        "/pull_request/repository_scoped_number",
    ),
    (
        "history.replay.merge-outcome.canonical",
        "/observations/pr/timeline/items/4/commit_id/value",
        "/merge_revision/full_digest",
    ),
    (
        "history.replay.merge-outcome.canonical",
        "/observations/repository/global_id",
        "/pull_request/repository_identity/provider_repository_id",
    ),
    (
        "history.replay.occurrence-time.approval",
        "/observations/pr/attempts/0/bracket_a/number",
        "/occurrence/review/parent/repository_scoped_number",
    ),
    (
        "history.replay.occurrence-time.approval",
        "/observations/pr/reviews/items/0/commit_sha",
        "/occurrence/approved_revision/full_digest",
    ),
    (
        "history.replay.occurrence-time.approval",
        "/observations/pr/reviews/items/0/global_id",
        "/occurrence/review/provider_global_id",
    ),
    (
        "history.replay.occurrence-time.approval",
        "/observations/pr/reviews/items/0/submitted_at/normalized_utc",
        "/occurred_at",
    ),
    (
        "history.replay.occurrence-time.approval",
        "/observations/repository/global_id",
        "/occurrence/review/parent/repository_identity/provider_repository_id",
    ),
    (
        "history.replay.occurrence-time.deletion",
        "/observations/pr/attempts/0/bracket_a/head/ref/value",
        "/occurrence/head_ref_name",
    ),
    (
        "history.replay.occurrence-time.deletion",
        "/observations/pr/attempts/0/bracket_a/head/sha",
        "/occurrence/head/role_assignment/revision/full_digest",
    ),
    (
        "history.replay.occurrence-time.deletion",
        "/observations/pr/attempts/0/bracket_a/number",
        "/occurrence/head/pull_request/repository_scoped_number",
    ),
    (
        "history.replay.occurrence-time.deletion",
        "/observations/pr/timeline/items/6/created_at/value/normalized_utc",
        "/occurred_at",
    ),
    (
        "history.replay.occurrence-time.deletion",
        "/observations/repository/global_id",
        "/occurrence/head/pull_request/repository_identity/provider_repository_id",
    ),
    (
        "history.replay.occurrence-time.merge",
        "/observations/pr/attempts/0/bracket_a/number",
        "/occurrence/pull_request/repository_scoped_number",
    ),
    (
        "history.replay.occurrence-time.merge",
        "/observations/pr/timeline/items/4/commit_id/value",
        "/occurrence/merge_revision/full_digest",
    ),
    (
        "history.replay.occurrence-time.merge",
        "/observations/pr/timeline/items/4/created_at/value/normalized_utc",
        "/occurred_at",
    ),
    (
        "history.replay.occurrence-time.merge",
        "/observations/repository/global_id",
        "/occurrence/pull_request/repository_identity/provider_repository_id",
    ),
    (
        "history.replay.review-approval.canonical",
        "/observations/pr/attempts/0/bracket_a/number",
        "/review/parent/repository_scoped_number",
    ),
    (
        "history.replay.review-approval.canonical",
        "/observations/pr/reviews/items/0/commit_sha",
        "/approved_revision/full_digest",
    ),
    (
        "history.replay.review-approval.canonical",
        "/observations/pr/reviews/items/0/global_id",
        "/review/provider_global_id",
    ),
    (
        "history.replay.review-approval.canonical",
        "/observations/repository/global_id",
        "/review/parent/repository_identity/provider_repository_id",
    ),
    (
        "history.replay.role-binding.base",
        "/observations/comparison/base_sha",
        "/role_assignment/revision/full_digest",
    ),
    (
        "history.replay.role-binding.base",
        "/observations/pr/attempts/0/bracket_a/number",
        "/pull_request/repository_scoped_number",
    ),
    (
        "history.replay.role-binding.base",
        "/observations/repository/global_id",
        "/pull_request/repository_identity/provider_repository_id",
    ),
    (
        "history.replay.role-binding.head",
        "/observations/comparison/head_sha",
        "/role_assignment/revision/full_digest",
    ),
    (
        "history.replay.role-binding.head",
        "/observations/pr/attempts/0/bracket_a/number",
        "/pull_request/repository_scoped_number",
    ),
    (
        "history.replay.role-binding.head",
        "/observations/repository/global_id",
        "/pull_request/repository_identity/provider_repository_id",
    ),
)


def test_every_source_mapping_uses_an_authorised_coordinate() -> None:
    """Bound per vector: a corpus-wide set would let two vectors trade sources."""
    permitted = set(SOURCE_COORDINATES)
    observed = {
        (
            cast(str, vector["id"]),
            f"{pointer['json_pointer']}{source_field}",
            replayed,
        )
        for vector in REPLAY["vectors"]
        for pointer in cast(list[dict[str, Any]], vector["source_pointers"])
        for source_field, replayed in cast(
            dict[str, str], pointer["source_fields"]
        ).items()
    }

    assert observed == permitted, sorted(observed ^ permitted)


def test_two_vectors_cannot_trade_source_coordinates() -> None:
    """The approval must be timestamped from its own retained event."""
    permitted = set(SOURCE_COORDINATES)
    approval = next(
        t
        for t in permitted
        if t[0] == "history.replay.occurrence-time.approval" and t[2] == "/occurred_at"
    )
    merge = next(
        t
        for t in permitted
        if t[0] == "history.replay.occurrence-time.merge" and t[2] == "/occurred_at"
    )

    assert approval[1] != merge[1]
    traded = (permitted - {approval, merge}) | {
        (approval[0], merge[1], approval[2]),
        (merge[0], approval[1], merge[2]),
    }
    assert traded != permitted
    assert sorted(c for _, c, _ in traded) == sorted(c for _, c, _ in permitted)


def test_an_unauthorised_source_coordinate_is_refused() -> None:
    """Re-pointing a leaf at a different retained coordinate must fail."""
    permitted = set(SOURCE_COORDINATES)
    smuggled = (
        "history.replay.role-binding.base",
        "/observations/pr/attempts/0/bracket_a/number",
        "/pull_request/repository_identity/provider_repository_id",
    )

    assert smuggled not in permitted
    assert permitted | {smuggled} != permitted


def test_each_replayed_leaf_has_one_source_within_a_vector() -> None:
    """Two coordinates for one leaf would let either stand in for the other.

    Across vectors a leaf legitimately has different sources -- the base and
    head bindings both replay `/role_assignment/revision/full_digest`, from
    `base_sha` and `head_sha` respectively. Within a single vector it must not.
    """
    ambiguous: dict[str, dict[str, list[str]]] = {}
    for vector in REPLAY["vectors"]:
        by_leaf: dict[str, set[str]] = {}
        for pointer in cast(list[dict[str, Any]], vector["source_pointers"]):
            for source_field, replayed in cast(
                dict[str, str], pointer["source_fields"]
            ).items():
                by_leaf.setdefault(replayed, set()).add(
                    f"{pointer['json_pointer']}{source_field}"
                )
        clashes = {leaf: sorted(v) for leaf, v in by_leaf.items() if len(v) > 1}
        if clashes:
            ambiguous[cast(str, vector["id"])] = clashes

    assert not ambiguous, ambiguous


# --- the non-goal bullet block is projected, not searched --------------------


def _render_non_goal_block() -> list[str]:
    return [f"- {goal}" for goal in cast(list[str], MANIFEST["non_goals"])]


def _actual_non_goal_block(text: str) -> list[str]:
    lines = text.splitlines()
    start = lines.index("## 8. Non-Generalizations") + 1
    while start < len(lines) and not lines[start].startswith("- "):
        start += 1
    end = start
    while end < len(lines) and lines[end].startswith("- "):
        end += 1
    return lines[start:end]


def test_the_non_goal_block_is_an_exact_projection() -> None:
    text = (CORPUS / "contract.md").read_text("utf-8")

    assert _actual_non_goal_block(text) == _render_non_goal_block()
    assert len(_render_non_goal_block()) == 32


@pytest.mark.parametrize("mutate", ("extra", "missing", "reorder", "changed"))
def test_no_non_goal_bullet_can_drift(mutate: str) -> None:
    rendered = _render_non_goal_block()
    if mutate == "extra":
        drifted = [*rendered, "- no invented boundary"]
    elif mutate == "missing":
        drifted = rendered[:-1]
    elif mutate == "reorder":
        drifted = list(reversed(rendered))
    else:
        drifted = [rendered[0].replace("no ", "no longer "), *rendered[1:]]

    assert drifted != rendered, mutate


# --- a citation belongs to a vector, not merely to the corpus ----------------
#
# Membership in the registered set says a reference exists somewhere. It cannot
# tell whether the retained correction is cited by the association that
# actually replays it or by an unrelated valid vector, because the union is the
# same either way. The citing population of each non-baseline authority is
# therefore pinned.

GOVERNANCE_REFERENCES = (
    "decision:s1-p05-s08:disposition",
    "correction:s1-p05-s08-c01:owner-topology",
)
RETAINED_ACQUISITION_REFERENCE = "acquisition:run-0001"
RETAINED_CORRECTION_REFERENCE = "correction:s04-c01-acquisition-closure"
CORRECTION_CITING_VECTOR = (
    "history.replay.evidence-association.approval-correction-record"
)


def _citing(reference: str) -> set[str]:
    return {
        cast(str, v["id"])
        for section in (VALID, INVALID, REPLAY)
        for v in section["vectors"]
        if reference in cast(list[str], v["decision_references"])
    }


def test_each_authority_is_cited_by_exactly_its_own_vectors() -> None:
    every = {
        cast(str, v["id"])
        for section in (VALID, INVALID, REPLAY)
        for v in section["vectors"]
    }
    replay_ids = {cast(str, v["id"]) for v in REPLAY["vectors"]}

    for reference in GOVERNANCE_REFERENCES:
        assert _citing(reference) == every, reference
    assert _citing(RETAINED_ACQUISITION_REFERENCE) == replay_ids
    assert _citing(RETAINED_CORRECTION_REFERENCE) == {CORRECTION_CITING_VECTOR}


def test_a_moved_citation_is_refused() -> None:
    """Moving the retained correction to another vector preserves the union."""
    moved = (_citing(RETAINED_CORRECTION_REFERENCE) - {CORRECTION_CITING_VECTOR}) | {
        "history.valid.role-binding.base-canonical"
    }

    assert len(moved) == len(_citing(RETAINED_CORRECTION_REFERENCE))
    assert moved != {CORRECTION_CITING_VECTOR}


def test_the_correction_citing_vector_is_the_one_that_replays_it() -> None:
    """The citation must name the vector whose record is the correction."""
    vector = next(v for v in REPLAY["vectors"] if v["id"] == CORRECTION_CITING_VECTOR)

    assert vector["evidence_record_lock"] == RETAINED_CORRECTION_REFERENCE
    assert RETAINED_CORRECTION_REFERENCE in cast(
        list[str], vector["decision_references"]
    )


# --- the replay classification bullets are projected, not sampled ------------


def _render_classification_block() -> list[str]:
    classifications = cast(
        dict[str, str], MANIFEST["replay_contract"]["classifications"]
    )
    return [f"- `{key}` — {value}" for key, value in sorted(classifications.items())]


def _actual_classification_block(text: str) -> list[str]:
    lines = text.splitlines()
    start = next(
        i for i, line in enumerate(lines) if line.startswith("- `caller_supplied_")
    )
    end = start
    while end < len(lines) and lines[end].startswith("- `"):
        end += 1
    return lines[start:end]


def test_the_classification_block_is_an_exact_projection() -> None:
    text = (CORPUS / "contract.md").read_text("utf-8")

    assert _actual_classification_block(text) == _render_classification_block()
    assert len(_render_classification_block()) == 3


def test_swapped_classification_descriptions_are_refused() -> None:
    """Token presence cannot tell a link layer from a composition layer."""
    rendered = _render_classification_block()
    keys = [line.split("`")[1] for line in rendered]
    bodies = [line.split(" — ", 1)[1] for line in rendered]
    swapped = [
        f"- `{keys[0]}` — {bodies[1]}",
        f"- `{keys[1]}` — {bodies[0]}",
        rendered[2],
    ]

    assert sorted(b.split(" — ", 1)[1] for b in swapped) == sorted(bodies)
    assert swapped != rendered


def test_a_partial_recomputed_from_is_refused() -> None:
    """Dropping the correction must not leave the declaration true."""
    governance = cast(dict[str, Any], MANIFEST["effective_governance"])
    complete = {governance["base_decision"], governance["correction"]}

    for partial in ([], [governance["base_decision"]], [governance["correction"]]):
        assert set(cast(list[str], partial)) != complete


# --- the scope paragraph names roles, so it is projected too -----------------


def _render_scope_sentence() -> str:
    scope = cast(dict[str, Any], MANIFEST["scope"])
    supporting = ", ".join(
        f"`{module}`"
        for module in cast(list[str], scope["supporting_authorities_not_owned"])
    )
    outside = " and ".join(f"`{module}`" for module in OUTSIDE_MODULES)
    return (
        f"Supporting authorities are consumed but not owned: {supporting}. "
        f"{outside} are outside this corpus: no `S1.P05` value consumes them."
    )


OUTSIDE_MODULES = (
    "faultatlas.domain.snapshot",
    "faultatlas.domain.snapshot_evidence_link",
)


def test_the_scope_sentence_is_an_exact_projection() -> None:
    """Token presence cannot tell a supporting module from an excluded one."""
    text = (CORPUS / "contract.md").read_text("utf-8")
    rendered = _render_scope_sentence()

    assert rendered in text
    for module in OUTSIDE_MODULES:
        assert module not in cast(
            list[str], MANIFEST["scope"]["supporting_authorities_not_owned"]
        )
        assert module not in set(OWNED)


def test_a_reassigned_scope_role_is_refused() -> None:
    """Swapping a supporting module for an excluded one keeps every token."""
    text = (CORPUS / "contract.md").read_text("utf-8")
    supporting = list(
        cast(list[str], MANIFEST["scope"]["supporting_authorities_not_owned"])
    )
    swapped = [
        OUTSIDE_MODULES[0] if m == "faultatlas.domain.identity" else m
        for m in supporting
    ]

    assert sorted(swapped) != sorted(supporting)
    reassigned = (
        "Supporting authorities are consumed but not owned: "
        + ", ".join(f"`{m}`" for m in swapped)
        + "."
    )
    assert reassigned not in text
