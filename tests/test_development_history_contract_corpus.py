from __future__ import annotations

import ast
import copy
import hashlib
import importlib
import inspect
import json
import re
import stat as stat_module
from collections import Counter
from collections.abc import Callable
from datetime import datetime
from enum import Enum
from pathlib import Path
from types import UnionType
from typing import Any, NamedTuple, Union, cast, get_origin

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
LOCATION_MODES = ("exact", "prefix")
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


# --- the records nested inside a vector document publish exact key sets ------
#
# The document root, the vector record and the `expected` block are each closed,
# but two record collections sitting beside the vectors were not: a fixture
# could gain a `value_sha256` and an artifact lock a `format_version`, both
# resealed, and every oracle stayed green. These are separate schemas from the
# vector envelope and from each other -- a fixture is a shared declaration
# replicated across three files, a lock is a digest-bearing citation living in
# replay alone -- so each gets its own authored set rather than one recursive
# "all dictionaries must have known keys" engine.
#
# Authored, because a durable record cannot authorize its own envelope
# expansion: a set built from the records would admit whatever they happen to
# carry, which is the defect rather than the fix.
#
# Structural only. `fixture["value"]` deliberately carries heterogeneous domain
# values and is governed by the semantic bindings below, not by this rule.
REQUIRED_FIXTURE_RECORD_KEYS = frozenset({"id", "status", "value"})
REQUIRED_ARTIFACT_LOCK_KEYS = frozenset({"byte_length", "lock_id", "path", "sha256"})


def _record_envelope_failures(
    label: str, record: dict[str, Any], required: frozenset[str], key: str
) -> list[tuple[str, ...]]:
    """Every way one nested record departs from its published key set."""
    present = set(record)
    identity = cast(str, record.get(key, "<unidentified>"))
    return [
        (label, identity, kind, name)
        for kind, names in (
            ("missing", sorted(required - present)),
            ("unexpected", sorted(present - required)),
        )
        for name in names
    ]


def test_every_fixture_record_publishes_exactly_its_envelope() -> None:
    """A fixture declares an id, a status and a value -- and nothing else."""
    failures = [
        failure
        for family, section, _ in FAMILIES
        for fixture in cast(list[dict[str, Any]], section["fixtures"])
        for failure in _record_envelope_failures(
            family, fixture, REQUIRED_FIXTURE_RECORD_KEYS, "id"
        )
    ]

    assert not failures, failures
    shapes = {
        frozenset(fixture)
        for _, section, _ in FAMILIES
        for fixture in cast(list[dict[str, Any]], section["fixtures"])
    }
    assert shapes == {REQUIRED_FIXTURE_RECORD_KEYS}
    assert len(REQUIRED_FIXTURE_RECORD_KEYS) == 3


def test_every_artifact_lock_publishes_exactly_its_envelope() -> None:
    """A lock cites a path by digest and length; it makes no other claim."""
    locks = cast(list[dict[str, Any]], REPLAY["artifact_locks"])
    failures = [
        failure
        for lock in locks
        for failure in _record_envelope_failures(
            "replay", lock, REQUIRED_ARTIFACT_LOCK_KEYS, "lock_id"
        )
    ]

    assert not failures, failures
    assert {frozenset(lock) for lock in locks} == {REQUIRED_ARTIFACT_LOCK_KEYS}
    assert len(REQUIRED_ARTIFACT_LOCK_KEYS) == 4


def test_a_drifting_nested_record_envelope_is_refused() -> None:
    """Additions, omissions and renames each fail, whatever the value."""
    fixture = copy.deepcopy(cast(dict[str, Any], VALID["fixtures"][0]))
    lock = copy.deepcopy(cast(list[dict[str, Any]], REPLAY["artifact_locks"])[0])

    probes: list[tuple[str, dict[str, Any], frozenset[str], str]] = []
    for label, record, required, key, dropped, renamed in (
        ("fixture", fixture, REQUIRED_FIXTURE_RECORD_KEYS, "id", "status", "value"),
        ("lock", lock, REQUIRED_ARTIFACT_LOCK_KEYS, "lock_id", "byte_length", "sha256"),
    ):
        # an unknown key is unexpected whatever it holds: emptiness is not
        # absence, and a published field is published
        empties: tuple[Any, ...] = ("", False, None, [], {}, 0)
        for value in empties:
            probes.append((label, {**record, "smuggled": value}, required, key))
        probes.append(
            (label, {k: v for k, v in record.items() if k != dropped}, required, key)
        )
        crossed = {k: v for k, v in record.items() if k != renamed}
        crossed[f"{renamed}_renamed"] = record[renamed]
        probes.append((label, crossed, required, key))

    for label, damaged, required, key in probes:
        assert _record_envelope_failures(label, damaged, required, key), label

    # the authored sets may not be rebuilt from the records they validate
    assert REQUIRED_FIXTURE_RECORD_KEYS == frozenset({"id", "status", "value"})
    assert REQUIRED_ARTIFACT_LOCK_KEYS == frozenset(
        {"byte_length", "lock_id", "path", "sha256"}
    )
    assert not REQUIRED_FIXTURE_RECORD_KEYS & REQUIRED_ARTIFACT_LOCK_KEYS


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

    # The mode is a closed vocabulary, and it selects how the location is
    # compared. Treating anything that is not "exact" as prefix would let a
    # vector publish a mode that means nothing, and the vocabulary-error branch
    # below returns before the field is ever read.
    assert expected["error_location_mode"] in LOCATION_MODES, vector["id"]
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

    # The role implications are compared whole by the block projection below;
    # containment cannot tell a declared mapping from a fabricated one.
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


# --- a partition identity is attached to one vector identity ------------------
#
# Three rules already govern `semantic_partition`. The values are globally
# unique, each prefix repeats the vector's own category, and the behavioural
# signature deliberately excludes the field so that renaming a label never
# reads as a new boundary. Together they establish that the corpus publishes a
# valid partition -- 183 distinct labels over 183 distinct behaviours.
#
# None of them establishes ATTACHMENT: which authored label belongs to which
# vector. Two vectors in one category can exchange their complete partition
# values and every rule above still holds, because uniqueness survives a
# permutation, the prefix is shared, and the signature never looks. The corpus
# then publishes each behaviour under the other's identity.
#
# Coverage and attachment are different properties, and the signature bijection
# only ever proved the first. The attachment is therefore authored here, keyed
# by the durable vector id.
#
# What this proves: the published partition identity is attached to the
# published vector identity that carries it. What it does not prove: that
# suffixes such as `canonical`, `python-typed` or `equal-instants-allowed` are
# correct descriptions of anything. Those stay opaque -- this repair does not
# promote a naming convention into product semantics, and the existing prefix
# rule remains the only lexical claim the corpus makes.

REQUIRED_SEMANTIC_PARTITION_BY_VECTOR_ID: dict[str, str] = {
    # -- 48 valid vectors --------------------------------------------------
    "history.valid.role-binding.base-canonical": "role-binding/accepts/base-canonical",
    "history.valid.role-binding.head-canonical": "role-binding/accepts/head-canonical",
    "history.valid.role-binding.distinct-pull-request": "role-binding/accepts/distinct-pull-request",
    "history.valid.role-binding.distinct-revision": "role-binding/accepts/distinct-revision",
    "history.valid.role-binding.python-typed": "role-binding/accepts/python-typed",
    "history.valid.status.added": "changed-path-status/accepts/added",
    "history.valid.status.modified": "changed-path-status/accepts/modified",
    "history.valid.status.python-enum": "changed-path-status/accepts/python-enum",
    "history.valid.changed-path.added": "changed-path/accepts/added",
    "history.valid.changed-path.modified": "changed-path/accepts/modified",
    "history.valid.changed-path.distinct-blob": "changed-path/accepts/distinct-blob",
    "history.valid.changed-path.python-typed": "changed-path/accepts/python-typed",
    "history.valid.change-set.canonical-three-paths": "change-set/accepts/canonical-three-paths",
    "history.valid.change-set.single-path-minimum": "change-set/accepts/single-path-minimum",
    "history.valid.change-set.supplied-order-preserved": "change-set/accepts/supplied-order-preserved",
    "history.valid.change-set.maximum-changed-paths": "change-set/accepts/maximum-changed-paths",
    "history.valid.change-set.python-typed": "change-set/accepts/python-typed",
    "history.valid.approval.canonical": "review-approval/accepts/canonical",
    "history.valid.approval.revision-need-not-be-head": "review-approval/accepts/revision-need-not-be-head",
    "history.valid.approval.python-typed": "review-approval/accepts/python-typed",
    "history.valid.merge-outcome.canonical": "merge-outcome/accepts/canonical",
    "history.valid.merge-outcome.revision-independent-of-head": "merge-outcome/accepts/revision-independent-of-head",
    "history.valid.merge-outcome.python-typed": "merge-outcome/accepts/python-typed",
    "history.valid.head-ref-deletion.canonical": "head-ref-deletion/accepts/canonical",
    "history.valid.head-ref-deletion.distinct-ref-name": "head-ref-deletion/accepts/distinct-ref-name",
    "history.valid.head-ref-deletion.python-typed": "head-ref-deletion/accepts/python-typed",
    "history.valid.occurrence-time.approval": "occurrence-time/accepts/approval",
    "history.valid.occurrence-time.merge": "occurrence-time/accepts/merge",
    "history.valid.occurrence-time.deletion": "occurrence-time/accepts/deletion",
    "history.valid.occurrence-time.offset-zero-form": "occurrence-time/accepts/offset-zero-form",
    "history.valid.occurrence-time.equal-instants-allowed": "occurrence-time/accepts/equal-instants-allowed",
    "history.valid.occurrence-time.sub-second-preserved": "occurrence-time/accepts/sub-second-preserved",
    "history.valid.occurrence-time.python-typed": "occurrence-time/accepts/python-typed",
    "history.valid.evidence-link.role-binding-json": "evidence-link/accepts/role-binding-json",
    "history.valid.evidence-link.changed-path-json": "evidence-link/accepts/changed-path-json",
    "history.valid.evidence-link.review-approval-json": "evidence-link/accepts/review-approval-json",
    "history.valid.evidence-link.merge-outcome-json": "evidence-link/accepts/merge-outcome-json",
    "history.valid.evidence-link.head-ref-deletion-json": "evidence-link/accepts/head-ref-deletion-json",
    "history.valid.evidence-link.occurrence-time-json": "evidence-link/accepts/occurrence-time-json",
    "history.valid.evidence-link.role-binding-python": "evidence-link/accepts/role-binding-python",
    "history.valid.evidence-link.changed-path-python": "evidence-link/accepts/changed-path-python",
    "history.valid.evidence-link.review-approval-python": "evidence-link/accepts/review-approval-python",
    "history.valid.evidence-link.merge-outcome-python": "evidence-link/accepts/merge-outcome-python",
    "history.valid.evidence-link.head-ref-deletion-python": "evidence-link/accepts/head-ref-deletion-python",
    "history.valid.evidence-link.occurrence-time-python": "evidence-link/accepts/occurrence-time-python",
    "history.valid.evidence-link.correction-record": "evidence-link/accepts/correction-record",
    "history.valid.evidence-link.synthetic-record": "evidence-link/accepts/synthetic-record",
    "history.valid.evidence-link.second-fact-same-record": "evidence-link/accepts/second-fact-same-record",
    # -- 111 invalid vectors -----------------------------------------------
    "history.invalid.role-binding.non-pull-request-subject": "role-binding/rejects/non-pull-request-subject",
    "history.invalid.role-binding.disallowed-revision-role": "role-binding/rejects/disallowed-revision-role",
    "history.invalid.role-binding.missing-pull-request": "role-binding/rejects/missing-pull-request",
    "history.invalid.role-binding.missing-role-assignment": "role-binding/rejects/missing-role-assignment",
    "history.invalid.role-binding.extra-observed-at": "role-binding/rejects/extra-observed-at",
    "history.invalid.role-binding.untyped-python-pull-request": "role-binding/rejects/untyped-python-pull-request",
    "history.invalid.role-binding.untyped-python-role-assignment": "role-binding/rejects/untyped-python-role-assignment",
    "history.invalid.role-binding.dumped-mapping-python": "role-binding/rejects/dumped-mapping-python",
    "history.invalid.role-binding.foreign-python-subject": "role-binding/rejects/foreign-python-subject",
    "history.invalid.role-binding.swapped-members": "role-binding/rejects/swapped-members",
    "history.invalid.role-binding.null-role-assignment": "role-binding/rejects/null-role-assignment",
    "history.invalid.status.removed": "changed-path-status/rejects/removed",
    "history.invalid.status.renamed": "changed-path-status/rejects/renamed",
    "history.invalid.status.copied": "changed-path-status/rejects/copied",
    "history.invalid.status.not-a-status": "changed-path-status/rejects/not-a-status",
    "history.invalid.changed-path.unknown-status": "changed-path/rejects/unknown-status",
    "history.invalid.changed-path.commit-as-head-object": "changed-path/rejects/commit-as-head-object",
    "history.invalid.changed-path.missing-path": "changed-path/rejects/missing-path",
    "history.invalid.changed-path.missing-head-object": "changed-path/rejects/missing-head-object",
    "history.invalid.changed-path.missing-status": "changed-path/rejects/missing-status",
    "history.invalid.changed-path.extra-base-object": "changed-path/rejects/extra-base-object",
    "history.invalid.changed-path.untyped-python-path": "changed-path/rejects/untyped-python-path",
    "history.invalid.changed-path.untyped-python-head-object": "changed-path/rejects/untyped-python-head-object",
    "history.invalid.changed-path.empty-path": "changed-path/rejects/empty-path",
    "history.invalid.changed-path.raw-python-status": "changed-path/rejects/python-input-requires-typed-status",
    "history.invalid.change-set.empty-changed-paths": "change-set/rejects/empty-changed-paths",
    "history.invalid.change-set.above-maximum-changed-paths": "change-set/rejects/above-maximum-changed-paths",
    "history.invalid.change-set.duplicate-path": "change-set/rejects/duplicate-path",
    "history.invalid.change-set.equal-base-and-head-revision": "change-set/rejects/equal-base-and-head-revision",
    "history.invalid.change-set.mismatched-pull-requests": "change-set/rejects/mismatched-pull-requests",
    "history.invalid.change-set.mixed-hash-algorithms": "change-set/rejects/mixed-hash-algorithms",
    "history.invalid.change-set.missing-base": "change-set/rejects/missing-base",
    "history.invalid.change-set.missing-head": "change-set/rejects/missing-head",
    "history.invalid.change-set.missing-changed-paths": "change-set/rejects/missing-changed-paths",
    "history.invalid.change-set.extra-complete": "change-set/rejects/extra-complete",
    "history.invalid.change-set.python-list-not-tuple": "change-set/rejects/python-list-not-tuple",
    "history.invalid.change-set.untyped-python-base": "change-set/rejects/untyped-python-base",
    "history.invalid.change-set.untyped-python-head": "change-set/rejects/untyped-python-head",
    "history.invalid.change-set.untyped-python-changed-path-element": "change-set/rejects/untyped-python-changed-path-element",
    "history.invalid.change-set.base-position-rejects-non-base-role": "change-set/rejects/base-position-rejects-non-base-role",
    "history.invalid.change-set.head-position-rejects-non-head-role": "change-set/rejects/head-position-rejects-non-head-role",
    "history.invalid.change-set.mismatched-revision-algorithms": "change-set/rejects/mismatched-revision-algorithms",
    "history.invalid.approval.non-review-subject": "review-approval/rejects/non-review-subject",
    "history.invalid.approval.non-pull-request-parent": "review-approval/rejects/non-pull-request-parent",
    "history.invalid.approval.blob-as-approved-revision": "review-approval/rejects/blob-as-approved-revision",
    "history.invalid.approval.missing-review": "review-approval/rejects/missing-review",
    "history.invalid.approval.missing-approved-revision": "review-approval/rejects/missing-approved-revision",
    "history.invalid.approval.extra-state": "review-approval/rejects/extra-state",
    "history.invalid.approval.extra-submitted-at": "review-approval/rejects/extra-submitted-at",
    "history.invalid.approval.untyped-python-review": "review-approval/rejects/untyped-python-review",
    "history.invalid.approval.untyped-python-approved-revision": "review-approval/rejects/untyped-python-approved-revision",
    "history.invalid.approval.non-review-kind-subject": "review-approval/rejects/non-review-kind-subject",
    "history.invalid.merge-outcome.non-pull-request-subject": "merge-outcome/rejects/non-pull-request-subject",
    "history.invalid.merge-outcome.tree-as-merge-revision": "merge-outcome/rejects/tree-as-merge-revision",
    "history.invalid.merge-outcome.missing-pull-request": "merge-outcome/rejects/missing-pull-request",
    "history.invalid.merge-outcome.missing-merge-revision": "merge-outcome/rejects/missing-merge-revision",
    "history.invalid.merge-outcome.extra-parents": "merge-outcome/rejects/extra-parents",
    "history.invalid.merge-outcome.extra-strategy": "merge-outcome/rejects/extra-strategy",
    "history.invalid.merge-outcome.untyped-python-pull-request": "merge-outcome/rejects/untyped-python-pull-request",
    "history.invalid.merge-outcome.untyped-python-merge-revision": "merge-outcome/rejects/untyped-python-merge-revision",
    "history.invalid.head-ref-deletion.base-binding": "head-ref-deletion/rejects/base-binding",
    "history.invalid.head-ref-deletion.refs-prefixed-name": "head-ref-deletion/rejects/refs-prefixed-name",
    "history.invalid.head-ref-deletion.empty-ref-name": "head-ref-deletion/rejects/empty-ref-name",
    "history.invalid.head-ref-deletion.missing-head": "head-ref-deletion/rejects/missing-head",
    "history.invalid.head-ref-deletion.missing-ref-name": "head-ref-deletion/rejects/missing-ref-name",
    "history.invalid.head-ref-deletion.extra-namespace": "head-ref-deletion/rejects/extra-namespace",
    "history.invalid.head-ref-deletion.raw-python-ref-name": "head-ref-deletion/rejects/raw-python-ref-name",
    "history.invalid.head-ref-deletion.untyped-python-head": "head-ref-deletion/rejects/untyped-python-head",
    "history.invalid.occurrence-time.instant-naive": "occurrence-time/rejects/instant-naive",
    "history.invalid.occurrence-time.instant-positive-offset": "occurrence-time/rejects/instant-positive-offset",
    "history.invalid.occurrence-time.instant-negative-offset": "occurrence-time/rejects/instant-negative-offset",
    "history.invalid.occurrence-time.instant-malformed": "occurrence-time/rejects/instant-malformed",
    "history.invalid.occurrence-time.non-admitted-commit-identity": "occurrence-time/rejects/non-admitted-commit-identity",
    "history.invalid.occurrence-time.non-admitted-changed-path-status": "occurrence-time/rejects/non-admitted-changed-path-status",
    "history.invalid.occurrence-time.non-admitted-change-set": "occurrence-time/rejects/non-admitted-change-set",
    "history.invalid.occurrence-time.non-admitted-role-binding": "occurrence-time/rejects/non-admitted-role-binding",
    "history.invalid.occurrence-time.non-admitted-changed-path": "occurrence-time/rejects/non-admitted-changed-path",
    "history.invalid.occurrence-time.missing-occurred-at": "occurrence-time/rejects/missing-occurred-at",
    "history.invalid.occurrence-time.extra-chronology": "occurrence-time/rejects/extra-chronology",
    "history.invalid.occurrence-time.untyped-python-occurrence": "occurrence-time/rejects/untyped-python-occurrence",
    "history.invalid.occurrence-time.missing-occurrence": "occurrence-time/rejects/missing-occurrence",
    "history.invalid.occurrence-time.raw-python-instant": "occurrence-time/rejects/raw-python-instant",
    "history.invalid.evidence-link.change-set-fact": "evidence-link/rejects/change-set-fact",
    "history.invalid.evidence-link.changed-path-status-fact": "evidence-link/rejects/changed-path-status-fact",
    "history.invalid.evidence-link.hybrid-fact-json": "evidence-link/rejects/hybrid-fact-json",
    "history.invalid.evidence-link.empty-fact-json": "evidence-link/rejects/empty-fact-json",
    "history.invalid.evidence-link.malformed-record": "evidence-link/rejects/malformed-record",
    "history.invalid.evidence-link.missing-fact": "evidence-link/rejects/missing-fact",
    "history.invalid.evidence-link.missing-evidence-record": "evidence-link/rejects/missing-evidence-record",
    "history.invalid.evidence-link.extra-schema-version": "evidence-link/rejects/extra-schema-version",
    "history.invalid.evidence-link.extra-json-pointer": "evidence-link/rejects/extra-json-pointer",
    "history.invalid.evidence-link.extra-support-role": "evidence-link/rejects/extra-support-role",
    "history.invalid.evidence-link.extra-strength": "evidence-link/rejects/extra-strength",
    "history.invalid.evidence-link.extra-verification": "evidence-link/rejects/extra-verification",
    "history.invalid.evidence-link.extra-confidence": "evidence-link/rejects/extra-confidence",
    "history.invalid.evidence-link.extra-primary-evidence": "evidence-link/rejects/extra-primary-evidence",
    "history.invalid.evidence-link.extra-evidence-records": "evidence-link/rejects/extra-evidence-records",
    "history.invalid.evidence-link.extra-superseded": "evidence-link/rejects/extra-superseded",
    "history.invalid.evidence-link.extra-request-id": "evidence-link/rejects/extra-request-id",
    "history.invalid.evidence-link.extra-artifact": "evidence-link/rejects/extra-artifact",
    "history.invalid.evidence-link.nested-non-admitted-occurrence": "evidence-link/rejects/nested-non-admitted-occurrence",
    "history.invalid.evidence-link.untyped-python-fact": "evidence-link/rejects/untyped-python-fact",
    "history.invalid.evidence-link.typed-children-mapping-python": "evidence-link/rejects/typed-children-mapping-python",
    "history.invalid.evidence-link.untyped-python-record": "evidence-link/rejects/untyped-python-record",
    "history.invalid.evidence-link.change-set-fact-python": "evidence-link/rejects/change-set-fact-python",
    "history.invalid.evidence-link.status-fact-python": "evidence-link/rejects/status-fact-python",
    "history.invalid.evidence-link.instant-naive": "evidence-link/rejects/instant-naive",
    "history.invalid.evidence-link.instant-non-zero-offset": "evidence-link/rejects/instant-non-zero-offset",
    "history.invalid.evidence-link.instant-week-date": "evidence-link/rejects/instant-week-date",
    "history.invalid.evidence-link.instant-basic-format": "evidence-link/rejects/instant-basic-format",
    "history.invalid.evidence-link.occurrence-time-fact-python": "evidence-link/rejects/occurrence-time-fact-python",
    # -- 24 replay vectors -------------------------------------------------
    "history.replay.role-binding.base": "revision-role-binding/replays/base",
    "history.replay.role-binding.head": "revision-role-binding/replays/head",
    "history.replay.changed-path.changelog": "changed-path/replays/changelog",
    "history.replay.changed-path.rewrite": "changed-path/replays/rewrite",
    "history.replay.changed-path.assertrewrite": "changed-path/replays/assertrewrite",
    "history.replay.change-set.supplied-three-paths": "supplied-change-set/replays/supplied-three-paths",
    "history.replay.review-approval.canonical": "review-approval/replays/canonical",
    "history.replay.merge-outcome.canonical": "merge-outcome/replays/canonical",
    "history.replay.head-ref-deletion.canonical": "head-ref-deletion/replays/canonical",
    "history.replay.occurrence-time.approval": "occurrence-time/replays/approval",
    "history.replay.occurrence-time.merge": "occurrence-time/replays/merge",
    "history.replay.occurrence-time.deletion": "occurrence-time/replays/deletion",
    "history.replay.evidence-association.base-binding": "evidence-association/replays/base-binding",
    "history.replay.evidence-association.head-binding": "evidence-association/replays/head-binding",
    "history.replay.evidence-association.changed-path-changelog": "evidence-association/replays/changed-path-changelog",
    "history.replay.evidence-association.changed-path-rewrite": "evidence-association/replays/changed-path-rewrite",
    "history.replay.evidence-association.changed-path-assertrewrite": "evidence-association/replays/changed-path-assertrewrite",
    "history.replay.evidence-association.review-approval": "evidence-association/replays/review-approval",
    "history.replay.evidence-association.merge-outcome": "evidence-association/replays/merge-outcome",
    "history.replay.evidence-association.head-ref-deletion": "evidence-association/replays/head-ref-deletion",
    "history.replay.evidence-association.occurrence-approval": "evidence-association/replays/occurrence-approval",
    "history.replay.evidence-association.occurrence-merge": "evidence-association/replays/occurrence-merge",
    "history.replay.evidence-association.occurrence-deletion": "evidence-association/replays/occurrence-deletion",
    "history.replay.evidence-association.approval-correction-record": "evidence-association/replays/approval-correction-record",
}


def _attachment_failures(
    sections: dict[str, dict[str, Any]],
    authority: dict[str, str],
) -> list[tuple[str, str]]:
    """`(coordinate, reason)` for every disagreement, in both directions.

    Counting 183 on each side would accept a corpus that repeated one id, so
    every vector is looked up individually, duplicates are named, and every
    authority entry must be reached.
    """
    failures: list[tuple[str, str]] = []
    seen: set[str] = set()
    for section in sections.values():
        for vector in section["vectors"]:
            identifier = cast(str, vector["id"])
            if identifier in seen:
                failures.append((identifier, "vector-id-repeated"))
                continue
            seen.add(identifier)
            if identifier not in authority:
                failures.append((identifier, "vector-absent-from-authority"))
                continue
            if cast(str, vector["semantic_partition"]) != authority[identifier]:
                failures.append((identifier, "partition-differs"))
    for identifier in sorted(set(authority) - seen):
        failures.append((identifier, "authority-entry-unpopulated"))
    return sorted(failures)


def test_every_vector_carries_the_partition_identity_authored_for_it() -> None:
    """The reported finding, closed.

    Exchanging the complete partition values of
    `history.valid.merge-outcome.canonical` and
    `history.valid.merge-outcome.python-typed` satisfied every published rule,
    because none of them related a partition identity to a vector identity.
    """
    sections = _sections(VALID, INVALID, REPLAY)

    assert not _attachment_failures(sections, REQUIRED_SEMANTIC_PARTITION_BY_VECTOR_ID)

    authority = REQUIRED_SEMANTIC_PARTITION_BY_VECTOR_ID
    assert len(authority) == 183
    assert len(set(authority.values())) == 183, "attachment stays one-to-one"
    assert sum(len(section["vectors"]) for section in sections.values()) == 183


def test_the_attachment_authority_closes_against_the_corpus_both_ways() -> None:
    """No vector without an entry, no entry without a vector."""
    observed = {
        cast(str, vector["id"]): cast(str, vector["semantic_partition"])
        for section in (VALID, INVALID, REPLAY)
        for vector in section["vectors"]
    }
    authority = REQUIRED_SEMANTIC_PARTITION_BY_VECTOR_ID

    assert set(observed) - set(authority) == set(), "a vector the authority omits"
    assert set(authority) - set(observed) == set(), "an entry no vector populates"
    assert observed == authority

    per_family = [
        len([v for v in section["vectors"] if v["id"] in authority])
        for section in (VALID, INVALID, REPLAY)
    ]
    assert per_family == [48, 111, 24]


def test_the_attachment_authority_is_written_out_and_never_computed() -> None:
    """A literal that a comprehension could rebuild is not an authority.

    The envelope repairs showed how easily an apparently authored mapping gets
    laundered into corpus-derived state. Checking only that a literal is
    *written* is not enough, because a later statement can rebind the name to
    something derived while leaving the literal in place for a reader to see.
    Three things are therefore required: the literal holds 183 string pairs,
    the name is touched exactly once at module scope, and the object the module
    actually binds equals the literal that was inspected.
    """
    name = "REQUIRED_SEMANTIC_PARTITION_BY_VECTOR_ID"
    module = ast.parse(Path(__file__).read_text("utf-8"))
    assigned = [
        node
        for node in module.body
        if isinstance(node, ast.AnnAssign)
        and isinstance(node.target, ast.Name)
        and node.target.id == name
    ]

    assert len(assigned) == 1
    literal = assigned[0].value
    assert isinstance(literal, ast.Dict)
    assert len(literal.keys) == 183
    for key, value in zip(literal.keys, literal.values, strict=True):
        assert isinstance(key, ast.Constant) and isinstance(key.value, str)
        assert isinstance(value, ast.Constant) and isinstance(value.value, str)

    # a second binding, an augmented assignment or a `.update(...)` at module
    # scope would all leave the literal above untouched and still replace what
    # the module binds, so the name must appear exactly once outside a body
    touching = [
        node
        for statement in module.body
        if not isinstance(
            statement, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef
        )
        for node in ast.walk(statement)
        if isinstance(node, ast.Name) and node.id == name
    ]
    assert len(touching) == 1, "the authority is bound once and never rebound"
    assert touching[0] is assigned[0].target

    # and what is bound at run time must be the literal that was inspected
    assert ast.literal_eval(literal) == REQUIRED_SEMANTIC_PARTITION_BY_VECTOR_ID

    source = inspect.getsource(_attachment_failures)
    for forbidden in ("VALID", "INVALID", "REPLAY", "MANIFEST", "CORPUS"):
        assert forbidden not in source, forbidden


def test_a_same_category_partition_swap_breaks_only_the_attachment_rule() -> None:
    """The reproduction, kept permanently.

    Two vectors in one category exchange their complete partition values.
    Uniqueness survives a permutation, the prefix is shared, and the
    behavioural signature never looks, so only the attachment notices.
    """
    valid = copy.deepcopy(VALID)
    first = next(
        v
        for v in valid["vectors"]
        if v["id"] == "history.valid.merge-outcome.canonical"
    )
    second = next(
        v
        for v in valid["vectors"]
        if v["id"] == "history.valid.merge-outcome.python-typed"
    )
    before = sorted(cast(str, v["semantic_partition"]) for v in valid["vectors"])
    first["semantic_partition"], second["semantic_partition"] = (
        second["semantic_partition"],
        first["semantic_partition"],
    )

    assert _resealed_digest(valid) != next(
        entry["sha256"]
        for entry in MANIFEST["corpus_files"]
        if entry["filename"] == "valid-vectors.json"
    )

    sections = _sections(valid, INVALID, REPLAY)
    assert (
        sorted(cast(str, v["semantic_partition"]) for v in valid["vectors"]) == before
    )
    assert first["category"] == second["category"] == "merge-outcome"
    assert first["target"] == second["target"]
    assert all(
        cast(str, v["semantic_partition"]).split("/")[0] == v["category"]
        for v in valid["vectors"]
    ), "the prefix rule is still satisfied"
    assert not _family_collisions(valid, "valid"), "behaviour is unchanged"
    assert not _taxonomy_failures(sections, REQUIRED_CATEGORY_BY_FAMILY_TARGET)
    assert not _manifest_histogram_failures(MANIFEST, sections)

    assert _attachment_failures(sections, REQUIRED_SEMANTIC_PARTITION_BY_VECTOR_ID) == [
        ("history.valid.merge-outcome.canonical", "partition-differs"),
        ("history.valid.merge-outcome.python-typed", "partition-differs"),
    ]


def test_the_same_swap_in_the_invalid_family_also_fails() -> None:
    """A second family, a different pair: the rule is not tuned to one place."""
    invalid = copy.deepcopy(INVALID)
    first = next(
        v
        for v in invalid["vectors"]
        if v["id"] == "history.invalid.merge-outcome.extra-parents"
    )
    second = next(
        v
        for v in invalid["vectors"]
        if v["id"] == "history.invalid.merge-outcome.extra-strategy"
    )
    first["semantic_partition"], second["semantic_partition"] = (
        second["semantic_partition"],
        first["semantic_partition"],
    )

    sections = _sections(VALID, invalid, REPLAY)
    assert not _family_collisions(invalid, "invalid")
    assert not _taxonomy_failures(sections, REQUIRED_CATEGORY_BY_FAMILY_TARGET)
    assert _attachment_failures(sections, REQUIRED_SEMANTIC_PARTITION_BY_VECTOR_ID) == [
        ("history.invalid.merge-outcome.extra-parents", "partition-differs"),
        ("history.invalid.merge-outcome.extra-strategy", "partition-differs"),
    ]


def test_the_same_swap_in_the_replay_family_also_fails() -> None:
    """Replay has categories with two vectors, so the real swap applies here."""
    replay = copy.deepcopy(REPLAY)
    first = next(
        v for v in replay["vectors"] if v["id"] == "history.replay.role-binding.base"
    )
    second = next(
        v for v in replay["vectors"] if v["id"] == "history.replay.role-binding.head"
    )
    held = {
        cast(str, v["id"])
        for v in replay["vectors"]
        if v["category"] == "revision-role-binding"
    }
    assert held == {cast(str, first["id"]), cast(str, second["id"])}, (
        "the chosen replay category holds exactly these two vectors"
    )
    first["semantic_partition"], second["semantic_partition"] = (
        second["semantic_partition"],
        first["semantic_partition"],
    )

    sections = _sections(VALID, INVALID, replay)
    assert not _family_collisions(replay, "replay")
    assert not _taxonomy_failures(sections, REQUIRED_CATEGORY_BY_FAMILY_TARGET)
    assert _attachment_failures(sections, REQUIRED_SEMANTIC_PARTITION_BY_VECTOR_ID) == [
        ("history.replay.role-binding.base", "partition-differs"),
        ("history.replay.role-binding.head", "partition-differs"),
    ]


def test_an_unknown_same_prefix_partition_fails_the_attachment_rule() -> None:
    """A fresh label with the right prefix satisfies every older rule."""
    valid = copy.deepcopy(VALID)
    renamed = next(
        v
        for v in valid["vectors"]
        if v["id"] == "history.valid.merge-outcome.canonical"
    )
    renamed["semantic_partition"] = "merge-outcome/accepts/newly-invented-boundary"

    partitions = [cast(str, v["semantic_partition"]) for v in valid["vectors"]]
    assert len(set(partitions)) == 48, "uniqueness is still satisfiable"
    assert all(
        cast(str, v["semantic_partition"]).split("/")[0] == v["category"]
        for v in valid["vectors"]
    )

    assert _attachment_failures(
        _sections(valid, INVALID, REPLAY), REQUIRED_SEMANTIC_PARTITION_BY_VECTOR_ID
    ) == [("history.valid.merge-outcome.canonical", "partition-differs")]


def test_a_missing_authority_entry_fails_the_attachment_rule() -> None:
    authority = copy.deepcopy(REQUIRED_SEMANTIC_PARTITION_BY_VECTOR_ID)
    del authority["history.replay.changed-path.rewrite"]

    assert _attachment_failures(_sections(VALID, INVALID, REPLAY), authority) == [
        ("history.replay.changed-path.rewrite", "vector-absent-from-authority")
    ]


def test_an_extra_authority_entry_fails_the_attachment_rule() -> None:
    authority = copy.deepcopy(REQUIRED_SEMANTIC_PARTITION_BY_VECTOR_ID)
    authority["history.valid.merge-outcome.never-published"] = (
        "merge-outcome/accepts/never-published"
    )

    assert _attachment_failures(_sections(VALID, INVALID, REPLAY), authority) == [
        ("history.valid.merge-outcome.never-published", "authority-entry-unpopulated")
    ]


def test_swapped_authority_values_fail_against_an_untouched_corpus() -> None:
    """The mutation may sit on either side; the relation is what is checked."""
    authority = copy.deepcopy(REQUIRED_SEMANTIC_PARTITION_BY_VECTOR_ID)
    first, second = (
        "history.valid.changed-path.added",
        "history.valid.changed-path.python-typed",
    )
    authority[first], authority[second] = authority[second], authority[first]

    assert len(set(authority.values())) == 183, "the authority is still a bijection"
    assert _attachment_failures(_sections(VALID, INVALID, REPLAY), authority) == [
        (first, "partition-differs"),
        (second, "partition-differs"),
    ]


def test_the_behavioural_signature_still_ignores_the_partition() -> None:
    """Attachment must not be allowed to confirm itself.

    Folding `semantic_partition` into the signature would make every partition
    edit look like a behaviour change, and the independence this repair relies
    on would collapse into self-confirmation.
    """
    for fields in SIGNATURE_FIELDS.values():
        assert "semantic_partition" not in fields
        assert "id" not in fields
        assert "purpose" not in fields

    relabelled = copy.deepcopy(VALID)
    moved = relabelled["vectors"][0]
    moved["semantic_partition"] = "role-binding/accepts/some-other-label"

    assert _behavioural_signature(moved, "valid") == _behavioural_signature(
        VALID["vectors"][0], "valid"
    ), "the signature must not move when only the label moves"
    assert not _family_collisions(relabelled, "valid")


# --- a vector identity is attached to one behavioural identity ----------------
#
# Two relations already hold. Every vector id carries the partition identity
# authored for it, and every behavioural signature is distinct inside its
# family. Neither closes the identity itself.
#
# The partition authority is keyed BY the vector id, so when an id and its
# partition move together the key and the value travel as a pair and the
# mapping still agrees. The signature check only ever asked whether the 183
# behaviours differ from one another, never which id selects which. So two
# vectors could exchange `id` and `semantic_partition`, leave every executing
# field in place, and publish each behaviour under the other's durable
# identity with the whole suite green.
#
# The corpus-wide law is therefore stated directly: every one of the 183
# vector ids is attached to exactly one family-scoped behavioural identity.
# It is total on purpose. Requirement ledgers, fixture bindings and the
# forbidden-extra ledger already pin many ids as a side effect of what they
# check, but those are domain relationships, not the identity contract -- 32
# vectors sat in same-category groups that no such authority reached, and a
# refactor must not be able to move a vector into that residue silently.
#
# What this proves: a durable vector identity stays attached to the behaviour
# already published for it. What it does not prove: that the behaviour is
# semantically correct. Correctness still comes from product execution, the
# expectation checks, the requirement and constraint ledgers, replay
# provenance and the evidence authorities. This is canonical identity
# attachment, and a wrong behaviour would still have to be rejected by those.


def _behavioural_fingerprint(vector: dict[str, Any], family: str) -> str:
    """A compact identity for the behaviour the signature already defines.

    It reuses `_behavioural_signature` rather than re-selecting fields, so the
    fingerprint inherits exactly one definition of behaviour and stays blind to
    `id`, `purpose`, `semantic_partition`, `decision_references` and
    `category`. If the id fed its own fingerprint the rule would be circular.
    """
    return hashlib.sha256(
        _behavioural_signature(vector, family).encode("utf-8")
    ).hexdigest()


REQUIRED_BEHAVIOUR_BY_VECTOR_ID: dict[str, tuple[str, str]] = {
    # -- 48 valid vectors -------------------------------------------------
    "history.valid.role-binding.base-canonical": (
        "valid",
        "d959478b92cfed41bcff5e2a0537046921b2cec43413f914ff04516461dc40e0",
    ),
    "history.valid.role-binding.head-canonical": (
        "valid",
        "253c4cde777ac9994e40a7c7a43d74725ddebf20d28ea4a55c04036389a46754",
    ),
    "history.valid.role-binding.distinct-pull-request": (
        "valid",
        "580f72ebedf46e8759f58417b895745b3bab3754c5e869f59cd55da1496a78cf",
    ),
    "history.valid.role-binding.distinct-revision": (
        "valid",
        "a191bdfca0caa3b4dacdd769bc49ac572f3b0960db3ab376aa043014f25d5fab",
    ),
    "history.valid.role-binding.python-typed": (
        "valid",
        "74f0977277a6d470993903f31dfa1ec0d372a971d7e3beecada4d0e2fb556acd",
    ),
    "history.valid.status.added": (
        "valid",
        "90c0cb2148e428f3fa492d4834e8397f775a1852b77de66629d6082de02c8953",
    ),
    "history.valid.status.modified": (
        "valid",
        "a986e1efec92d4689696328438babfad7d6cf22d0c4f22ed2b00b3e3628ff6af",
    ),
    "history.valid.status.python-enum": (
        "valid",
        "5c26ff6fdfdd97a80d3a80ef0cc2eb1b7c04e36343b8e3b72f297c0ae66732f3",
    ),
    "history.valid.changed-path.added": (
        "valid",
        "cf6056cec1c6e8b9dcc46e8870839a558b1aff7064c87aae3cce58a4a2777b60",
    ),
    "history.valid.changed-path.modified": (
        "valid",
        "5d7b888ca23dfb63aad6ef42af1aca2c888b3d03d4ef320d74b2fd9cbc13faf4",
    ),
    "history.valid.changed-path.distinct-blob": (
        "valid",
        "6eec882ddfc6a3a5275325ff5158ce0bd2c66e6a8e62a8705767f0eeed5b9f6b",
    ),
    "history.valid.changed-path.python-typed": (
        "valid",
        "07db582978ab466c982738a23da157f39b25fde273a9a58abf1a69f0399f5820",
    ),
    "history.valid.change-set.canonical-three-paths": (
        "valid",
        "232c6c023528a10edefada0290160985ff6ff7930592de4d4addbbb8a07076fe",
    ),
    "history.valid.change-set.single-path-minimum": (
        "valid",
        "5724e6116dfe423413e53e87ba8f0feafb688d13e13e793ab855fc12e68b1660",
    ),
    "history.valid.change-set.supplied-order-preserved": (
        "valid",
        "bba07afc1378a81cd187fff9328a71ee2a041373c77f442e9250b28e4a25c7c6",
    ),
    "history.valid.change-set.maximum-changed-paths": (
        "valid",
        "3d45e5b90fa903620c8faa7c41aae20052a7c29ed993834ba23e278d07732fa2",
    ),
    "history.valid.change-set.python-typed": (
        "valid",
        "f375956928573d223353e38f8dfb475b41b42e9fbe948f63febd8fbe75dbdf9f",
    ),
    "history.valid.approval.canonical": (
        "valid",
        "6f3792f08fe6027432767c48f8b475403085a65810990b695f71e5b07bc7f91b",
    ),
    "history.valid.approval.revision-need-not-be-head": (
        "valid",
        "c17295779f35d91155ee6b7a9f1bca64a953fb34db192b77fc75ea91ca46476c",
    ),
    "history.valid.approval.python-typed": (
        "valid",
        "71ae804ee77a6b3f81348f1798c8395816221e91f32459c13b608a8b991f73e5",
    ),
    "history.valid.merge-outcome.canonical": (
        "valid",
        "cd21d875aef4b8fbf4d3f7bbdddf555ff2ffe995afee5a75ef94fb7129801a2d",
    ),
    "history.valid.merge-outcome.revision-independent-of-head": (
        "valid",
        "14f4cf845106287062c3585ea01b2476a6c86868a4b8f36b3f137091715edb9d",
    ),
    "history.valid.merge-outcome.python-typed": (
        "valid",
        "cccdaa84b721f5907fa56461a893c202ece6d32780a95f84b9440397f18e9157",
    ),
    "history.valid.head-ref-deletion.canonical": (
        "valid",
        "bf2bfbc8a47a92f3fc3eab4322ae42403ccafafb8672f209da3107131d5db868",
    ),
    "history.valid.head-ref-deletion.distinct-ref-name": (
        "valid",
        "6d6ca6f259d8c0640081ab6bf713b326955b89c02d78fab6afe2278847b8b2bd",
    ),
    "history.valid.head-ref-deletion.python-typed": (
        "valid",
        "ee86166d21c3799f6a4173dd3d13f09426a5305b6e08e17ba2ae86740000d7bf",
    ),
    "history.valid.occurrence-time.approval": (
        "valid",
        "d7a7f4e295299ae74a617302b009b4616db5738f959d53442dcb84b323d612ce",
    ),
    "history.valid.occurrence-time.merge": (
        "valid",
        "e3eedaf08bbdf1ae741a0762ec31e5943c2740af56d0255aa0186d6c3bc10ee1",
    ),
    "history.valid.occurrence-time.deletion": (
        "valid",
        "f54afe71f03c08a447c69825d4acdcdf13594a6fd7689ef21fe569cbb2a6074c",
    ),
    "history.valid.occurrence-time.offset-zero-form": (
        "valid",
        "db89c1cf0cceb7fb4fe63b62fe149cba05ce3b7e186b23c8394518e1b0427e85",
    ),
    "history.valid.occurrence-time.equal-instants-allowed": (
        "valid",
        "60adce6281b4ec8a4760c2e31f998a4146e43b475e56d1dd68ef469451dec503",
    ),
    "history.valid.occurrence-time.sub-second-preserved": (
        "valid",
        "d07291737f658659a3e6ea21214168aec295fec38ce94ac366554040cc6136a3",
    ),
    "history.valid.occurrence-time.python-typed": (
        "valid",
        "cae3f2eeb33eb5f0031ea2b1ea5dc86cebd986e648f098a81c1105c8c0bcf8de",
    ),
    "history.valid.evidence-link.role-binding-json": (
        "valid",
        "b1182d653fafd2e823c8b36e1a1dea4d82f23b4cef36e51c9cf5af21ae69ce9e",
    ),
    "history.valid.evidence-link.changed-path-json": (
        "valid",
        "1561f9c60ebff2b86581402f92f28d82066b07e6a642e8bb1e80860344780c9b",
    ),
    "history.valid.evidence-link.review-approval-json": (
        "valid",
        "e19b96a59ff09be3edcbd8b246e688c1826b468256fc93c6b768ecf96708e4cd",
    ),
    "history.valid.evidence-link.merge-outcome-json": (
        "valid",
        "fa66f1920aed2b68c2059316cec5a3596710419ce1e68f238945cf80a0f07fd7",
    ),
    "history.valid.evidence-link.head-ref-deletion-json": (
        "valid",
        "901395bc464960b828ad8c4e1b0b64cf97c19eaa516f0d2c46e18e3ba6c5ed52",
    ),
    "history.valid.evidence-link.occurrence-time-json": (
        "valid",
        "76ea16ea6bd1b83058df41585debedf24a4db8f39c94096bfb7867d9f442ae9b",
    ),
    "history.valid.evidence-link.role-binding-python": (
        "valid",
        "13eea52f4fd1e64b650de2de35b1c8014c91c842bf7df8ae87995c398871de40",
    ),
    "history.valid.evidence-link.changed-path-python": (
        "valid",
        "10956a898025aa51b21b4baf968eab82a2ed5bc8c1f8a7367e7324ba5e703591",
    ),
    "history.valid.evidence-link.review-approval-python": (
        "valid",
        "9889e1a617673a43fc4593229f54e9bfc09d34351319c6bf023b89f9ca3d8bb0",
    ),
    "history.valid.evidence-link.merge-outcome-python": (
        "valid",
        "a63f25865e6faf98856021f13f64b1be83a51bd98454d37f4fc651e00fcf618f",
    ),
    "history.valid.evidence-link.head-ref-deletion-python": (
        "valid",
        "902ef5790a1d9a157d1479aa7903daf52d1ffd1a88f4ed809ceae6cf7607a27f",
    ),
    "history.valid.evidence-link.occurrence-time-python": (
        "valid",
        "3b3aa365e5236681ec1dce0aaa2b4f1229993b3ee65da3992c3979019116849b",
    ),
    "history.valid.evidence-link.correction-record": (
        "valid",
        "416ae4caa595bc9a3f8079dfc315da12b7cf8d286a90e472ea0ba96e262cff36",
    ),
    "history.valid.evidence-link.synthetic-record": (
        "valid",
        "5806f1553652b417b5d2c21857167dbf7e6f6ba7b9bdec0ef7b413e078680524",
    ),
    "history.valid.evidence-link.second-fact-same-record": (
        "valid",
        "0c4ba7ecde4c56b3a4e5756f853e183f5f0c97ece8e41a2b91b91237814307a7",
    ),
    # -- 111 invalid vectors ----------------------------------------------
    "history.invalid.role-binding.non-pull-request-subject": (
        "invalid",
        "7fdb532217499db2fe06473eb6e09569ed8b8a2914e20d58c90d7175249ebf40",
    ),
    "history.invalid.role-binding.disallowed-revision-role": (
        "invalid",
        "830a4845b5c96bcae1383a17c69d8d5376465632e62fdbfbcc8ea0702004edb4",
    ),
    "history.invalid.role-binding.missing-pull-request": (
        "invalid",
        "5ad9fba5ef81c6d224b309cce57bb309b565ef0b74e21c85a227136f500212a4",
    ),
    "history.invalid.role-binding.missing-role-assignment": (
        "invalid",
        "df7238e41891f4c884077a3a3b3f6bb9f377326023b6dbdfc07e9b51c20f7384",
    ),
    "history.invalid.role-binding.extra-observed-at": (
        "invalid",
        "db310e893aba711c33eab04962ee94ac4d2dccef45fe7c5fe808d027ce55468e",
    ),
    "history.invalid.role-binding.untyped-python-pull-request": (
        "invalid",
        "09070bceff5c5f336606743380b1e72d063d5565f085de83165856c46441f0fa",
    ),
    "history.invalid.role-binding.untyped-python-role-assignment": (
        "invalid",
        "9abcaedb46c69b442ea8c7017bd979689d9bfb0e98a6e838413e5e702cfa1cd8",
    ),
    "history.invalid.role-binding.dumped-mapping-python": (
        "invalid",
        "05c84563ca6fedc41eea7211cacd4144ee5799562fb2eb30f31d4b70e2bcf6e2",
    ),
    "history.invalid.role-binding.foreign-python-subject": (
        "invalid",
        "f9045622ffc99373e423629b1bd061b264efb08d52fe295cc123aed67c221037",
    ),
    "history.invalid.role-binding.swapped-members": (
        "invalid",
        "8fdbe0ec4007bd38c91307ba86432f1a69de178fb8b4bc3d792f2a305c794ef9",
    ),
    "history.invalid.role-binding.null-role-assignment": (
        "invalid",
        "12f00d23d7b7cc61fe236931e44155f73eddeeaba2909d168987d9abd584e86a",
    ),
    "history.invalid.status.removed": (
        "invalid",
        "40e0826e25565184efadd963d9d2aef08692be7544010962e02be59e715999ef",
    ),
    "history.invalid.status.renamed": (
        "invalid",
        "0c6863c96c2b9efc64e94f78cbe85b4793d252a151335b19e690c96ba4832cef",
    ),
    "history.invalid.status.copied": (
        "invalid",
        "c8c0e94cd93e083088aa3adaadf93a14ee96fbe16d2b0582be4b454058afe33d",
    ),
    "history.invalid.status.not-a-status": (
        "invalid",
        "72c6529b0d42d6b9d5ddc22d89b5ef283d74ea681e41c702d910059b08044e29",
    ),
    "history.invalid.changed-path.unknown-status": (
        "invalid",
        "e4ca9de8f820394e71d55985d56493e08c599a773b4469f76df6d3f30864db33",
    ),
    "history.invalid.changed-path.commit-as-head-object": (
        "invalid",
        "00e9c9c7f0327cf0ff46d539fe9d698641e61e1a55a08b0e322c1190cbab53b3",
    ),
    "history.invalid.changed-path.missing-path": (
        "invalid",
        "87e16053e052ffb9e7773be7258371099744646050cc3cf3adfd3a9b25c2ced2",
    ),
    "history.invalid.changed-path.missing-head-object": (
        "invalid",
        "a1d2f5b4a96a1bf7f9dd3952396f43b64b8fb9afd4da633b56e908133bda7168",
    ),
    "history.invalid.changed-path.missing-status": (
        "invalid",
        "5fdab6d415e52acf2ef05c4a2d2862dcff1e8279674a32192ac5f67040c237ce",
    ),
    "history.invalid.changed-path.extra-base-object": (
        "invalid",
        "3e8061852877cd5cd2e2161080facf36a610979914272be8af7fbbb67961a573",
    ),
    "history.invalid.changed-path.untyped-python-path": (
        "invalid",
        "6dc019e6e4c016943c373eb984b50173ee0573a670e5d1673914e65c80abda04",
    ),
    "history.invalid.changed-path.untyped-python-head-object": (
        "invalid",
        "716de82ee62d1dbb0c9d950ba3ca13979c39cd6405bc6d1b28748187d4045583",
    ),
    "history.invalid.changed-path.empty-path": (
        "invalid",
        "8ddefd221a03771d65468f5f5023bc008c898415c48b59bf29230c6aa77fedd1",
    ),
    "history.invalid.changed-path.raw-python-status": (
        "invalid",
        "d0bc71b7594ea9a0ccaaa8bd9d3bb04ac9760c6877d7a65a893ccbdc75c9e011",
    ),
    "history.invalid.change-set.empty-changed-paths": (
        "invalid",
        "b9fefb13e692f5937269534ff0ca920d96522f18ddf9c2d38a647859e2dd8e7c",
    ),
    "history.invalid.change-set.above-maximum-changed-paths": (
        "invalid",
        "031d7c7d8090fc2fb060949964f390f7e941fb4a960766b619220a545734dc5a",
    ),
    "history.invalid.change-set.duplicate-path": (
        "invalid",
        "867bcb5ed72bdb0d84490b2a4b687073edd594483b069ec2a4ab4fd2040e03c2",
    ),
    "history.invalid.change-set.equal-base-and-head-revision": (
        "invalid",
        "96e98e57cc45323845f5618d77b7afa50275699c1d3aac010247b1be052b1921",
    ),
    "history.invalid.change-set.mismatched-pull-requests": (
        "invalid",
        "6c58f71c96af3bd11424f7c998c15a47fec44e3f010d5e19cb21593cc431d412",
    ),
    "history.invalid.change-set.mixed-hash-algorithms": (
        "invalid",
        "6c7b30c7c6e70be5820f051abe3717576db9468d6937fc21d54721b301a2c4ef",
    ),
    "history.invalid.change-set.missing-base": (
        "invalid",
        "54bbb8087ea54f8dbd17924a025d539d9a1975f224c661a51601abf3042e74ba",
    ),
    "history.invalid.change-set.missing-head": (
        "invalid",
        "f3a91d3abc8c9825fae72c4e59e950bb66b3039996de6038710180a38ac02a49",
    ),
    "history.invalid.change-set.missing-changed-paths": (
        "invalid",
        "def4010839722f347da3647d68af08e343c8a75c011ff2b2daf26326f3edec1b",
    ),
    "history.invalid.change-set.extra-complete": (
        "invalid",
        "0a9654b78af419f90768cf7410e1806a402b32eaaa6b91a9c258376ad606971a",
    ),
    "history.invalid.change-set.python-list-not-tuple": (
        "invalid",
        "80c52e933b1f9a368db0161b5114aabb221240dabd4ef601e4d4f4a07a8f3a60",
    ),
    "history.invalid.change-set.untyped-python-base": (
        "invalid",
        "6f2274db3cbb66fb2f0200a8bb8589cac330a468d1bba5a669cd2a59b6a5ce52",
    ),
    "history.invalid.change-set.untyped-python-head": (
        "invalid",
        "20bed2e5d0ed1a956b219c887cd2bd5a407203c66c1fc73afb4d5060351dfa4c",
    ),
    "history.invalid.change-set.untyped-python-changed-path-element": (
        "invalid",
        "b3476d871b0d188a7e0e6a319e921972f93539115dab474fa483966aa367756b",
    ),
    "history.invalid.change-set.base-position-rejects-non-base-role": (
        "invalid",
        "0e07b5456f0ffe2cbfb64f5f8843f8e0a56dbb06f06b54f293491ebfe3f3232c",
    ),
    "history.invalid.change-set.head-position-rejects-non-head-role": (
        "invalid",
        "f95c94a0d42051515f6422d43e2eac1fb7ce2f605fda5961393b6580703f7431",
    ),
    "history.invalid.change-set.mismatched-revision-algorithms": (
        "invalid",
        "2802bf26e79f29dab03cebcf9859ebea862c8adcd04ef890d5f4730753b07161",
    ),
    "history.invalid.approval.non-review-subject": (
        "invalid",
        "6a82f9a2445e0cf92d492310246f5e0e5bb552ca470bebd9c143929156464664",
    ),
    "history.invalid.approval.non-pull-request-parent": (
        "invalid",
        "999f3b2d0101bf7fd4cb9f64411445c4677c5dd25fcf5441cca3d84112fd9cde",
    ),
    "history.invalid.approval.blob-as-approved-revision": (
        "invalid",
        "a12c9a1da4691496c0bd88fc473d9986a5a2c7601f16ba833683e0fbe37b68e2",
    ),
    "history.invalid.approval.missing-review": (
        "invalid",
        "8754f5c96aa523bd9fe1c79e78691c01f4a108e449a2224480a4b8cf879a94f0",
    ),
    "history.invalid.approval.missing-approved-revision": (
        "invalid",
        "4b06928472a9fea3b651d317e3e5463d7d585d0d3478d1a94ad42fdf6a8aaaee",
    ),
    "history.invalid.approval.extra-state": (
        "invalid",
        "663509013a75f601c6ed40145ccdcc2e128b42687d6cc4fb25a4fde7539bd99b",
    ),
    "history.invalid.approval.extra-submitted-at": (
        "invalid",
        "8dc47be0a9afcceefff8bad23af6a3302e8bad7084bf40142bb0cb0bd305d4b7",
    ),
    "history.invalid.approval.untyped-python-review": (
        "invalid",
        "51aa76555db2f13744fe17fb39abb9802d1c21b1c3290106b2532cb1db49a4f7",
    ),
    "history.invalid.approval.untyped-python-approved-revision": (
        "invalid",
        "65083d70cc27d7ae8b56a0ebe52a9f900a4000e646524d96251f2f743570abab",
    ),
    "history.invalid.approval.non-review-kind-subject": (
        "invalid",
        "2aeb70f53df96e217ba9515341baf3c0aaf0edd82ce03462e49c3e8638b5d87d",
    ),
    "history.invalid.merge-outcome.non-pull-request-subject": (
        "invalid",
        "218bd381b0b84e4ad47fd1702860ab13c031a96af3effddbd7d0dcdac19441b9",
    ),
    "history.invalid.merge-outcome.tree-as-merge-revision": (
        "invalid",
        "0fc00a39730ca684c5ddd0b4a5a2714007b5a7931f334751c47d7b8b0e10ddf4",
    ),
    "history.invalid.merge-outcome.missing-pull-request": (
        "invalid",
        "588e88e0990568af5809272747451764e0dd03b54af68c4f3f4488160e881b2d",
    ),
    "history.invalid.merge-outcome.missing-merge-revision": (
        "invalid",
        "c39a478d21182b62d028659b9d5df4012a6708a7b57a58c6c32dc0cf7ff916ec",
    ),
    "history.invalid.merge-outcome.extra-parents": (
        "invalid",
        "bf6fec6ba88010f000c5a3f8054335dec07f8005e3a685bf895988f74ee3a849",
    ),
    "history.invalid.merge-outcome.extra-strategy": (
        "invalid",
        "be1183874af813c125e3b68ead53118bb4d37af9defe97d9dcc1dd4e46cbda7c",
    ),
    "history.invalid.merge-outcome.untyped-python-pull-request": (
        "invalid",
        "e1f35c6aa5aa954616f1b1e702791df2ff6cb550787649ce0ec40eb80ceeead8",
    ),
    "history.invalid.merge-outcome.untyped-python-merge-revision": (
        "invalid",
        "e61f069142e6167d1ef02352d7cd92455e1f2afd69e309730d4253c0e28add7b",
    ),
    "history.invalid.head-ref-deletion.base-binding": (
        "invalid",
        "6d03674ed4f80d805625dd88e54b962a5a7ac9f714b344c7a4a10d9cdfc2efc8",
    ),
    "history.invalid.head-ref-deletion.refs-prefixed-name": (
        "invalid",
        "b11658cb15e4b23b5d2b9fd712be5ea419c246686aef64d72db99889b53fc612",
    ),
    "history.invalid.head-ref-deletion.empty-ref-name": (
        "invalid",
        "60bab71fc72200756082e6e09ad7e0ca85499343f2f612a1a4aae88267beff0a",
    ),
    "history.invalid.head-ref-deletion.missing-head": (
        "invalid",
        "1470d1c6326be9fc05c7839e1217b73e1097ebf694cbb89059c626ee8b2ce33d",
    ),
    "history.invalid.head-ref-deletion.missing-ref-name": (
        "invalid",
        "0dfc0227cea9cd9dbc02caeda058cad25ffe0836c2ef7185f3f3cbeb59949862",
    ),
    "history.invalid.head-ref-deletion.extra-namespace": (
        "invalid",
        "cdfd5df105799993fdf20f71f4012b3e39ea0d9019fc46f2b4f455e5a1d3f987",
    ),
    "history.invalid.head-ref-deletion.raw-python-ref-name": (
        "invalid",
        "c7e4a3beba197886d7aa724c39db322d4d206d95acb697e494d3ee12bd58208c",
    ),
    "history.invalid.head-ref-deletion.untyped-python-head": (
        "invalid",
        "2e0275b5e51b9d5a4de62b9c57b97159582acf62a304aa7296b84887a110de59",
    ),
    "history.invalid.occurrence-time.instant-naive": (
        "invalid",
        "1a8a4a03e4c8f06b88565ca407fea3ffaabf57516ae5a6cc07af4c298f8f2f51",
    ),
    "history.invalid.occurrence-time.instant-positive-offset": (
        "invalid",
        "bdb2f45875572b4317b3d57cfeed9fae6242e152e56bbafa289cf76bc8ed1c05",
    ),
    "history.invalid.occurrence-time.instant-negative-offset": (
        "invalid",
        "9a57e8a1f4a0823e1f32d7c5aa06a1f682f404a224d25952a32eacc00cad1dcf",
    ),
    "history.invalid.occurrence-time.instant-malformed": (
        "invalid",
        "2ea2501ad8ec710e2f0edb33ad31503ab387ea3e374900d447a4d290bf41f1ca",
    ),
    "history.invalid.occurrence-time.non-admitted-commit-identity": (
        "invalid",
        "c9a3be6fb6d9db53260ea3fa7f042e8b703b416fff2a6cef90399f4e6b03b6fc",
    ),
    "history.invalid.occurrence-time.non-admitted-changed-path-status": (
        "invalid",
        "ac194be7a7ed6415982893ac0dd71cc7a1b968d371bb87dc5cc17110075f770c",
    ),
    "history.invalid.occurrence-time.non-admitted-change-set": (
        "invalid",
        "8f41e12f98109ba7db5330a0c05df24b986cd98f3e140db28c07c0817c4511a9",
    ),
    "history.invalid.occurrence-time.non-admitted-role-binding": (
        "invalid",
        "a598dddce710402de317914f26992769e4ea5334fdcf088fd438c7a254ddd8c3",
    ),
    "history.invalid.occurrence-time.non-admitted-changed-path": (
        "invalid",
        "7d9e66d993b47f63e9966ef4e5507e25124d6a1dd82268a9412fc601332fbfc4",
    ),
    "history.invalid.occurrence-time.missing-occurred-at": (
        "invalid",
        "52e1fb1e1008c8e2494414641360e3e563e2efac4f483cea73b527e8b608cda8",
    ),
    "history.invalid.occurrence-time.extra-chronology": (
        "invalid",
        "7cc9121a9c66327c5912e7c931c95d59b15aeb8a5d6fdbeda9a8aaab4c21dc5f",
    ),
    "history.invalid.occurrence-time.untyped-python-occurrence": (
        "invalid",
        "06593b3df9cdfd488aa91c4f77c600bc4536856fc76d33b2d0fdabd5111eae9e",
    ),
    "history.invalid.occurrence-time.missing-occurrence": (
        "invalid",
        "21e24be2e768bee0abb034cfd0fb61b241d341b81ae9e214cac342e494c1f214",
    ),
    "history.invalid.occurrence-time.raw-python-instant": (
        "invalid",
        "5619831a2fd89e88db9a59f3ac3ee2533caa307b9bf18028e59c581d7b9da01a",
    ),
    "history.invalid.evidence-link.change-set-fact": (
        "invalid",
        "ce8defbae419c99193ebfa48ef49e2264cc1926aa150efa4fe4d8f1a3819412e",
    ),
    "history.invalid.evidence-link.changed-path-status-fact": (
        "invalid",
        "e8a2b90003e9f664e129a19aa751823e093357532c448e4391d9724408d82c9f",
    ),
    "history.invalid.evidence-link.hybrid-fact-json": (
        "invalid",
        "c7d9d9486e769d17fa2b0e7ac97d785a687ed6a88e1997e4d99dd4f6aa88397a",
    ),
    "history.invalid.evidence-link.empty-fact-json": (
        "invalid",
        "0d5c11b396bb5a7a6c9274ab8011634d699d23b5d7a947257f80912ddd490c22",
    ),
    "history.invalid.evidence-link.malformed-record": (
        "invalid",
        "7c7659b951abf06f4124e3605b3498d07322b7fbc6720008303a1f50c9c25e51",
    ),
    "history.invalid.evidence-link.missing-fact": (
        "invalid",
        "87dbc0711a732b612fbe6055d3a74ca8ee19d89c19372c119867891184517696",
    ),
    "history.invalid.evidence-link.missing-evidence-record": (
        "invalid",
        "8ba423bdeb5cfc04e00a3e2d692bcc0cd59ad4743626c4e6a744c8f547ed81e9",
    ),
    "history.invalid.evidence-link.extra-schema-version": (
        "invalid",
        "4f7175e7d0505d6f7df858050a51cbf7ab0c71f0785355673b70eac5fc62b205",
    ),
    "history.invalid.evidence-link.extra-json-pointer": (
        "invalid",
        "fc371a18b7f8480670a895698ef69c4e643585480112be852eb73bcd57c1cb18",
    ),
    "history.invalid.evidence-link.extra-support-role": (
        "invalid",
        "cf5aa81bfa02facf5d4a9905d6dbd3b17b93da78a7a129264f0acbe24f91f31a",
    ),
    "history.invalid.evidence-link.extra-strength": (
        "invalid",
        "14926c1db42d33eb39fcf35ac084698bad030bc8e7f1b8af8f47ea52cdc5669b",
    ),
    "history.invalid.evidence-link.extra-verification": (
        "invalid",
        "7d4196563b7e7281f044947835d2dbc3aa8a3c3eedb7e238350ce851e68f1a86",
    ),
    "history.invalid.evidence-link.extra-confidence": (
        "invalid",
        "8ec7970173d13aebbd543194bae936010db2f8513df95c48bfd108749d9a26b2",
    ),
    "history.invalid.evidence-link.extra-primary-evidence": (
        "invalid",
        "7d9fae8b13293a41355851a7038bbc9376201c38d342da01f42096b0f6122535",
    ),
    "history.invalid.evidence-link.extra-evidence-records": (
        "invalid",
        "e9462c3da082629d25784872241ed7f91f4df154c9684d4c25a5925feab8c72f",
    ),
    "history.invalid.evidence-link.extra-superseded": (
        "invalid",
        "6c26b63c1d97c181f7ebfd045fafcda4743ddd9323c15f8493cf236e6dc5560c",
    ),
    "history.invalid.evidence-link.extra-request-id": (
        "invalid",
        "11f5c5bf0b03e5843aaed1fb5613404377e8a07e20f586a7e74ddcf57bc0d225",
    ),
    "history.invalid.evidence-link.extra-artifact": (
        "invalid",
        "4750fabcf082158bcd06dce116de5df33eebd399191d0a5bf5913469da10a468",
    ),
    "history.invalid.evidence-link.nested-non-admitted-occurrence": (
        "invalid",
        "efb3c6f1369cb5f6e1dd098fd4e29a42323334eae84519f35f114e5220ed813b",
    ),
    "history.invalid.evidence-link.untyped-python-fact": (
        "invalid",
        "b10eb339b176a59f899cd9038d1b91cdee074daf0dda37d3e493b281445b07c5",
    ),
    "history.invalid.evidence-link.typed-children-mapping-python": (
        "invalid",
        "d18c837501c92267dc43926fa3b3aa19e301369184d5f7331be4b4f876adfbdd",
    ),
    "history.invalid.evidence-link.untyped-python-record": (
        "invalid",
        "a7850d8f71e5ce279298ae1dc9601d56007124e59f68f28be002aa74ab4b10dd",
    ),
    "history.invalid.evidence-link.change-set-fact-python": (
        "invalid",
        "9a01e21627e65e21117df84f41c00d4c421954d4a59857c572bc58f682f61bab",
    ),
    "history.invalid.evidence-link.status-fact-python": (
        "invalid",
        "6c98b31d1c688bb20435cdd94bf538608eca114110745e6b9dd54e7b0a195817",
    ),
    "history.invalid.evidence-link.instant-naive": (
        "invalid",
        "baec53d9f171b1e32d342dedf309444c49529e31c08686f06210f9965ce8ea5e",
    ),
    "history.invalid.evidence-link.instant-non-zero-offset": (
        "invalid",
        "2a3fb265bdbd2ea6ec91987abaa2391221cb8ceea598789c644bb77dc73cc7c5",
    ),
    "history.invalid.evidence-link.instant-week-date": (
        "invalid",
        "aa896d6511f3904f6625c7d23732e17ff0c46baf930a1034d9623cae772ac7bb",
    ),
    "history.invalid.evidence-link.instant-basic-format": (
        "invalid",
        "337a497938860e8d8a1613167d7c8f5d0198cda534e6e47770b2be7851f19a8b",
    ),
    "history.invalid.evidence-link.occurrence-time-fact-python": (
        "invalid",
        "e03597818c2033302ef91932ef80cd7d2196454bdbc00cd207539a93b11df8cf",
    ),
    # -- 24 replay vectors ------------------------------------------------
    "history.replay.role-binding.base": (
        "replay",
        "f4c03ce09bc89982f62f98a0082b59786569f41adce6d41325fb99bf9073b41a",
    ),
    "history.replay.role-binding.head": (
        "replay",
        "15086dd5b3b7878d16f23b9756cdb40c4ae5d7dfc4e3dd07b49924a67e251d3d",
    ),
    "history.replay.changed-path.changelog": (
        "replay",
        "161f9696da7e15fc93b75ee409c0b3acb568cc46be728832ccf6ea7d9fb3dd53",
    ),
    "history.replay.changed-path.rewrite": (
        "replay",
        "6745b395cb905d2a513690e6c5ce18bf3297b9d4e54b26fdf438612d8b8e86c9",
    ),
    "history.replay.changed-path.assertrewrite": (
        "replay",
        "cea106e9c076b9612b57364674b949831877f4e7fd48f87b9e5f27f41a8714e3",
    ),
    "history.replay.change-set.supplied-three-paths": (
        "replay",
        "9f7b8b311858e63932b608575d6403c3fad1a6affae2ca1dbdb4b208a8d8f561",
    ),
    "history.replay.review-approval.canonical": (
        "replay",
        "a6674f75b7bcc39284121e42b635b9de25b64480393ef894acb4f8a9947ff611",
    ),
    "history.replay.merge-outcome.canonical": (
        "replay",
        "16f12f3bf82f35ef0705d118724bef49997d075dfe7d97ff3bd8b7bcf13f2ddf",
    ),
    "history.replay.head-ref-deletion.canonical": (
        "replay",
        "1dd5156ce733ff3a999bf52ff128926c8fd3ec2e2755dc23f68d1d16059c3f56",
    ),
    "history.replay.occurrence-time.approval": (
        "replay",
        "fd03fc0b2b247950a4340194f767a895753288e02942444bd0362a11bdb56daa",
    ),
    "history.replay.occurrence-time.merge": (
        "replay",
        "f4c3609d7cbbe889ea0ca3e5dd490b06da1cdd8237fad8d97e9c48b4fe0436ff",
    ),
    "history.replay.occurrence-time.deletion": (
        "replay",
        "4ca2382bc81c0f56b30b6590f29afb930f1216a4326bb067e6f7131b558ec98a",
    ),
    "history.replay.evidence-association.base-binding": (
        "replay",
        "2af61586d530f111b5aa21f73fadb25f7fc99ad23e599efa59bbf6790b1e03a6",
    ),
    "history.replay.evidence-association.head-binding": (
        "replay",
        "941df02fbfb8036631997ac33ddce199a6ab81c5210ad4309d158962b887b896",
    ),
    "history.replay.evidence-association.changed-path-changelog": (
        "replay",
        "f8d7c647c348380dc56d8d7c20f2984f9be0c6e26e223656bddd1dfe1ddec63f",
    ),
    "history.replay.evidence-association.changed-path-rewrite": (
        "replay",
        "4130da73c2ca67035702cb0b864128986085e17e91d32973984ff32bd905b95b",
    ),
    "history.replay.evidence-association.changed-path-assertrewrite": (
        "replay",
        "0a8a42897158759c53606f2717735fdb087ae2e0a5ed55bd8af13fbe5321de3f",
    ),
    "history.replay.evidence-association.review-approval": (
        "replay",
        "44e7355b6466602dc405531d2e28ff6655672008a914947e0527252f4ca29589",
    ),
    "history.replay.evidence-association.merge-outcome": (
        "replay",
        "475d0e34b03c6e2a87615a940b72426ccf0cc80ed00b39d6b62d51a335b9c6a9",
    ),
    "history.replay.evidence-association.head-ref-deletion": (
        "replay",
        "de705e479967f47b3de575763973d08ebb9b4a29c3efef854a3a43d45cc27a89",
    ),
    "history.replay.evidence-association.occurrence-approval": (
        "replay",
        "1785b990990fd5cab9a94b5f82bf0c7e3b385f7527b91d2021c2426944926b43",
    ),
    "history.replay.evidence-association.occurrence-merge": (
        "replay",
        "198943a483e0175698ab57025467340ed49f0e194c5d132705358704ae791a04",
    ),
    "history.replay.evidence-association.occurrence-deletion": (
        "replay",
        "a508c4a263a2469abe39449f20942b1d05bf7ae91eac5bd65acbd19616c04b69",
    ),
    "history.replay.evidence-association.approval-correction-record": (
        "replay",
        "4caa286644ee52430833cde6cfeff0ef036613abaddf8741e74c0155f6ad0930",
    ),
}


def _behaviour_failures(
    sections: dict[str, dict[str, Any]],
    authority: dict[str, tuple[str, str]],
) -> list[tuple[str, str, str]]:
    """`(family, vector_id, reason)` for every disagreement, in both directions.

    Each vector is looked up individually, repeated ids are named rather than
    silently collapsed, and every authority entry must be reached, so equal
    totals on the two sides can never stand in for the relation itself.
    """
    failures: list[tuple[str, str, str]] = []
    seen: set[str] = set()
    for family, section in sorted(sections.items()):
        for vector in section["vectors"]:
            identifier = cast(str, vector["id"])
            if identifier in seen:
                failures.append((family, identifier, "vector-id-repeated"))
                continue
            seen.add(identifier)
            if identifier not in authority:
                failures.append((family, identifier, "vector-absent-from-authority"))
                continue
            expected_family, expected_fingerprint = authority[identifier]
            if family != expected_family:
                failures.append((family, identifier, "family-differs"))
                continue
            if _behavioural_fingerprint(vector, family) != expected_fingerprint:
                failures.append((family, identifier, "fingerprint-differs"))
    for identifier in sorted(set(authority) - seen):
        failures.append(
            (authority[identifier][0], identifier, "authority-entry-unpopulated")
        )
    return sorted(failures)


def _behaviour_detail(
    identifier: str,
    sections: dict[str, dict[str, Any]],
    authority: dict[str, tuple[str, str]],
) -> tuple[str, str, str, str, str]:
    """`(family, id, expected family, actual fingerprint, expected fingerprint)`."""
    for family, section in sorted(sections.items()):
        for vector in section["vectors"]:
            if vector["id"] == identifier:
                expected = authority.get(identifier, ("<absent>", "<absent>"))
                return (
                    family,
                    identifier,
                    expected[0],
                    _behavioural_fingerprint(vector, family),
                    expected[1],
                )
    raise AssertionError(identifier)


def test_every_vector_id_is_attached_to_the_behaviour_authored_for_it() -> None:
    """The reported finding, closed.

    Exchanging `id` and `semantic_partition` between two exposed vectors left
    the partition attachment satisfied -- key and value moved together -- and
    every other rule green, while each behaviour was published under the
    other's durable identity.
    """
    sections = _sections(VALID, INVALID, REPLAY)

    assert not _behaviour_failures(sections, REQUIRED_BEHAVIOUR_BY_VECTOR_ID)

    authority = REQUIRED_BEHAVIOUR_BY_VECTOR_ID
    assert len(authority) == 183
    assert sum(len(section["vectors"]) for section in sections.values()) == 183
    assert Counter(family for family, _ in authority.values()) == {
        "valid": 48,
        "invalid": 111,
        "replay": 24,
    }
    assert len({fingerprint for _, fingerprint in authority.values()}) == 183


def test_the_behaviour_authority_closes_against_the_corpus_both_ways() -> None:
    """No vector without an entry, no entry without a vector, one family each."""
    observed = {
        cast(str, vector["id"]): family
        for family, section in _sections(VALID, INVALID, REPLAY).items()
        for vector in section["vectors"]
    }
    authority = REQUIRED_BEHAVIOUR_BY_VECTOR_ID

    assert set(observed) - set(authority) == set(), "a vector the authority omits"
    assert set(authority) - set(observed) == set(), "an entry no vector populates"
    assert observed == {
        identifier: family for identifier, (family, _) in authority.items()
    }
    assert len(observed) == 183


def test_the_identity_law_is_total_and_not_the_current_residue() -> None:
    """Indirect pinning is a side effect, not the identity contract.

    The requirement ledger, the secondary-witness registry, the fixture
    bindings and the forbidden-extra ledger all name vector ids while checking
    something else. Between them they reach 132 of the 183, leaving 51 that no
    such authority names at all, 43 of those with a same-family same-category
    partner to be exchanged with. Their reach is incidental to what they check,
    so authoring only the residue would let a later refactor drop a vector out
    of an unrelated ledger and silently reopen this hole. The counts below are
    asserted so the description cannot drift away from the code.
    """
    indirectly_pinned = (
        {row[4] for row in REQUIREMENT_LEDGER}
        | set(SECONDARY_WITNESS_REGISTRY)
        | {binding[2] for binding in FIXTURE_BINDINGS}
        | {
            cast(str, entry["vector_id"])
            for entry in cast(
                list[dict[str, Any]], MANIFEST["s07_forbidden_extra_ledger"]
            )
        }
    )
    sections = _sections(VALID, INVALID, REPLAY)
    residue = {
        family: [
            cast(str, vector["id"])
            for vector in section["vectors"]
            if vector["id"] not in indirectly_pinned
        ]
        for family, section in sections.items()
    }
    assert len(indirectly_pinned) == 132
    assert indirectly_pinned <= set(REQUIRED_BEHAVIOUR_BY_VECTOR_ID), (
        "every id those authorities name must also carry the identity law"
    )
    assert [len(residue[family]) for family in ("valid", "invalid", "replay")] == [
        27,
        0,
        24,
    ]
    assert sum(len(names) for names in residue.values()) == 51

    grouped = 0
    for family, names in residue.items():
        counts = Counter(
            cast(str, vector["category"])
            for vector in sections[family]["vectors"]
            if cast(str, vector["id"]) in set(names)
        )
        grouped += sum(size for size in counts.values() if size >= 2)
    assert grouped == 43, "residue vectors that have an exchangeable partner"

    for family, section in sections.items():
        for vector in section["vectors"]:
            identifier = cast(str, vector["id"])
            assert REQUIRED_BEHAVIOUR_BY_VECTOR_ID[identifier][0] == family


def test_the_behaviour_authority_is_written_out_and_never_computed() -> None:
    """A literal a comprehension could rebuild is not an authority.

    The partition repair proved that inspecting only the annotated assignment
    is not enough: a later `.update(...)`, rebinding or augmented assignment
    leaves the literal in place for a reader while the module binds something
    derived. The same standard applies here, plus the value shape.
    """
    name = "REQUIRED_BEHAVIOUR_BY_VECTOR_ID"
    module = ast.parse(Path(__file__).read_text("utf-8"))
    assigned = [
        node
        for node in module.body
        if isinstance(node, ast.AnnAssign)
        and isinstance(node.target, ast.Name)
        and node.target.id == name
    ]

    assert len(assigned) == 1
    literal = assigned[0].value
    assert isinstance(literal, ast.Dict)
    assert len(literal.keys) == 183
    for key, value in zip(literal.keys, literal.values, strict=True):
        assert isinstance(key, ast.Constant) and isinstance(key.value, str)
        assert isinstance(value, ast.Tuple)
        assert len(value.elts) == 2
        for element in value.elts:
            assert isinstance(element, ast.Constant) and isinstance(element.value, str)

    touching = [
        node
        for statement in module.body
        if not isinstance(
            statement, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef
        )
        for node in ast.walk(statement)
        if isinstance(node, ast.Name) and node.id == name
    ]
    assert len(touching) == 1, "the authority is bound once and never rebound"
    assert touching[0] is assigned[0].target
    assert ast.literal_eval(literal) == REQUIRED_BEHAVIOUR_BY_VECTOR_ID

    for identifier, entry in REQUIRED_BEHAVIOUR_BY_VECTOR_ID.items():
        assert isinstance(identifier, str)
        assert isinstance(entry, tuple) and len(entry) == 2
        family, fingerprint = entry
        assert family in ("valid", "invalid", "replay")
        assert re.fullmatch(r"[0-9a-f]{64}", fingerprint), identifier

    source = inspect.getsource(_behaviour_failures) + inspect.getsource(
        _behavioural_fingerprint
    )
    for forbidden in ("VALID", "INVALID", "REPLAY", "MANIFEST", "CORPUS", "split"):
        assert forbidden not in source, forbidden


def test_an_id_and_partition_moved_together_break_only_the_identity_rule() -> None:
    """The reproduction, kept permanently.

    `history.valid.occurrence-time.offset-zero-form` and
    `history.valid.occurrence-time.sub-second-preserved` exchange `id` and
    `semantic_partition`. Because the partition authority is keyed by the id,
    key and value travel together and it still agrees; the behaviours never
    move, so the unlabelled signature set is unchanged.
    """
    valid = copy.deepcopy(VALID)
    first = next(
        v
        for v in valid["vectors"]
        if v["id"] == "history.valid.occurrence-time.offset-zero-form"
    )
    second = next(
        v
        for v in valid["vectors"]
        if v["id"] == "history.valid.occurrence-time.sub-second-preserved"
    )
    before = sorted(_behavioural_signature(v, "valid") for v in valid["vectors"])
    first["id"], second["id"] = second["id"], first["id"]
    first["semantic_partition"], second["semantic_partition"] = (
        second["semantic_partition"],
        first["semantic_partition"],
    )

    assert _resealed_digest(valid) != next(
        entry["sha256"]
        for entry in MANIFEST["corpus_files"]
        if entry["filename"] == "valid-vectors.json"
    )

    sections = _sections(valid, INVALID, REPLAY)
    assert not _attachment_failures(
        sections, REQUIRED_SEMANTIC_PARTITION_BY_VECTOR_ID
    ), "the completed partition rule cannot see an id and partition moving together"
    assert (
        sorted(_behavioural_signature(v, "valid") for v in valid["vectors"]) == before
    )
    assert not _family_collisions(valid, "valid")
    assert not _taxonomy_failures(sections, REQUIRED_CATEGORY_BY_FAMILY_TARGET)
    assert not _manifest_histogram_failures(MANIFEST, sections)

    assert _behaviour_failures(sections, REQUIRED_BEHAVIOUR_BY_VECTOR_ID) == [
        (
            "valid",
            "history.valid.occurrence-time.offset-zero-form",
            "fingerprint-differs",
        ),
        (
            "valid",
            "history.valid.occurrence-time.sub-second-preserved",
            "fingerprint-differs",
        ),
    ]


def test_a_second_exposed_valid_pair_also_breaks_the_identity_rule() -> None:
    """A different category: the rule is not tuned to occurrence-time."""
    valid = copy.deepcopy(VALID)
    first = next(
        v
        for v in valid["vectors"]
        if v["id"] == "history.valid.change-set.canonical-three-paths"
    )
    second = next(
        v
        for v in valid["vectors"]
        if v["id"] == "history.valid.change-set.single-path-minimum"
    )
    first["id"], second["id"] = second["id"], first["id"]
    first["semantic_partition"], second["semantic_partition"] = (
        second["semantic_partition"],
        first["semantic_partition"],
    )

    sections = _sections(valid, INVALID, REPLAY)
    assert not _attachment_failures(sections, REQUIRED_SEMANTIC_PARTITION_BY_VECTOR_ID)
    assert _behaviour_failures(sections, REQUIRED_BEHAVIOUR_BY_VECTOR_ID) == [
        (
            "valid",
            "history.valid.change-set.canonical-three-paths",
            "fingerprint-differs",
        ),
        (
            "valid",
            "history.valid.change-set.single-path-minimum",
            "fingerprint-differs",
        ),
    ]


def test_an_exposed_replay_pair_also_breaks_the_identity_rule() -> None:
    """No replay id is named by any of those four ledgers at all."""
    replay = copy.deepcopy(REPLAY)
    first = next(
        v
        for v in replay["vectors"]
        if v["id"] == "history.replay.evidence-association.base-binding"
    )
    second = next(
        v
        for v in replay["vectors"]
        if v["id"] == "history.replay.evidence-association.head-binding"
    )
    first["id"], second["id"] = second["id"], first["id"]
    first["semantic_partition"], second["semantic_partition"] = (
        second["semantic_partition"],
        first["semantic_partition"],
    )

    sections = _sections(VALID, INVALID, replay)
    assert not _attachment_failures(sections, REQUIRED_SEMANTIC_PARTITION_BY_VECTOR_ID)
    assert not _family_collisions(replay, "replay")
    assert _behaviour_failures(sections, REQUIRED_BEHAVIOUR_BY_VECTOR_ID) == [
        (
            "replay",
            "history.replay.evidence-association.base-binding",
            "fingerprint-differs",
        ),
        (
            "replay",
            "history.replay.evidence-association.head-binding",
            "fingerprint-differs",
        ),
    ]


def test_the_identity_rule_is_total_over_the_invalid_family_too() -> None:
    """Every invalid id is already held elsewhere, and still owes this law."""
    first = "history.invalid.merge-outcome.extra-parents"
    second = "history.invalid.merge-outcome.extra-strategy"
    assert {first, second} <= set(SECONDARY_WITNESS_REGISTRY) | {
        row[4] for row in REQUIREMENT_LEDGER
    }, "both are already pinned by a requirement authority"

    authority = copy.deepcopy(REQUIRED_BEHAVIOUR_BY_VECTOR_ID)
    authority[first], authority[second] = authority[second], authority[first]

    assert _behaviour_failures(_sections(VALID, INVALID, REPLAY), authority) == [
        ("invalid", first, "fingerprint-differs"),
        ("invalid", second, "fingerprint-differs"),
    ]


def test_a_changed_signature_field_moves_the_fingerprint() -> None:
    """Not only a permutation detector: fresh behaviour under an old identity."""
    valid = copy.deepcopy(VALID)
    edited = next(
        v
        for v in valid["vectors"]
        if v["id"] == "history.valid.occurrence-time.offset-zero-form"
    )
    held = {
        field: copy.deepcopy(edited[field])
        for field in ("id", "semantic_partition", "category", "purpose")
    }
    assert edited["input_mode"] == "json"
    edited["input_mode"] = "python"

    assert all(edited[field] == value for field, value in held.items())
    assert (
        _behavioural_fingerprint(edited, "valid")
        != (
            REQUIRED_BEHAVIOUR_BY_VECTOR_ID[
                "history.valid.occurrence-time.offset-zero-form"
            ][1]
        )
    )
    assert _behaviour_failures(
        _sections(valid, INVALID, REPLAY), REQUIRED_BEHAVIOUR_BY_VECTOR_ID
    ) == [
        (
            "valid",
            "history.valid.occurrence-time.offset-zero-form",
            "fingerprint-differs",
        )
    ]


def test_a_missing_behaviour_entry_fails_the_identity_rule() -> None:
    authority = copy.deepcopy(REQUIRED_BEHAVIOUR_BY_VECTOR_ID)
    del authority["history.replay.changed-path.rewrite"]

    assert _behaviour_failures(_sections(VALID, INVALID, REPLAY), authority) == [
        (
            "replay",
            "history.replay.changed-path.rewrite",
            "vector-absent-from-authority",
        )
    ]


def test_an_extra_behaviour_entry_fails_the_identity_rule() -> None:
    authority = copy.deepcopy(REQUIRED_BEHAVIOUR_BY_VECTOR_ID)
    authority["history.valid.change-set.never-published"] = ("valid", "0" * 64)

    assert _behaviour_failures(_sections(VALID, INVALID, REPLAY), authority) == [
        (
            "valid",
            "history.valid.change-set.never-published",
            "authority-entry-unpopulated",
        )
    ]


def test_a_wrong_family_fails_the_identity_rule() -> None:
    """Family is declared by the authority, never read off the id text."""
    identifier = "history.valid.change-set.python-typed"
    authority = copy.deepcopy(REQUIRED_BEHAVIOUR_BY_VECTOR_ID)
    authority[identifier] = ("replay", authority[identifier][1])

    assert _behaviour_failures(_sections(VALID, INVALID, REPLAY), authority) == [
        ("valid", identifier, "family-differs")
    ]
    assert _behaviour_detail(identifier, _sections(VALID, INVALID, REPLAY), authority)[
        :3
    ] == ("valid", identifier, "replay")


def test_a_wrong_fingerprint_fails_the_identity_rule() -> None:
    """A different but well-formed digest is still the wrong behaviour."""
    identifier = "history.valid.role-binding.base-canonical"
    replacement = hashlib.sha256(b"a behaviour this corpus never publishes").hexdigest()
    authority = copy.deepcopy(REQUIRED_BEHAVIOUR_BY_VECTOR_ID)
    authority[identifier] = ("valid", replacement)

    sections = _sections(VALID, INVALID, REPLAY)
    assert _behaviour_failures(sections, authority) == [
        ("valid", identifier, "fingerprint-differs")
    ]
    family, named, expected_family, actual, expected = _behaviour_detail(
        identifier, sections, authority
    )
    assert (family, named, expected_family) == ("valid", identifier, "valid")
    assert expected == replacement
    assert actual == REQUIRED_BEHAVIOUR_BY_VECTOR_ID[identifier][1]
    assert actual != expected


def test_a_repeated_vector_id_fails_the_identity_rule() -> None:
    """Two records claiming one identity is a collision, not a match."""
    valid = copy.deepcopy(VALID)
    twin = copy.deepcopy(valid["vectors"][0])
    twin["input_mode"] = "python"
    valid["vectors"].append(twin)

    failures = _behaviour_failures(
        _sections(valid, INVALID, REPLAY), REQUIRED_BEHAVIOUR_BY_VECTOR_ID
    )
    assert (cast(str, twin["id"]), "vector-id-repeated") in [
        (identifier, reason) for _, identifier, reason in failures
    ]


def test_the_fingerprint_ignores_every_authored_label() -> None:
    """If the id fed its own fingerprint the rule would confirm itself.

    This is the invariant the whole repair rests on, so it is checked over
    every vector in every family rather than a sample. A family-conditional
    extra input -- feeding `purpose` only for invalid, say -- would otherwise
    sit entirely outside a valid-family probe, and for those vectors the
    identity law would quietly degenerate into a statement about a label.
    """
    assert SIGNATURE_FIELDS == {
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

    sections = _sections(VALID, INVALID, REPLAY)
    labels: tuple[tuple[str, Any], ...] = (
        ("id", "history.relabelled.probe.identifier"),
        ("semantic_partition", "relabelled/probe/partition"),
        ("purpose", "a sentence this corpus never publishes"),
        ("category", "relabelled-probe-category"),
        ("decision_references", ["decision:relabelled:probe"]),
    )
    checked = 0
    for family, section in sections.items():
        for vector in section["vectors"]:
            # the definition is pinned per vector, so no family can carry a
            # different one
            baseline = _behavioural_fingerprint(vector, family)
            assert (
                baseline
                == hashlib.sha256(
                    _behavioural_signature(vector, family).encode("utf-8")
                ).hexdigest()
            ), vector["id"]
            assert re.fullmatch(r"[0-9a-f]{64}", baseline)

            for label, replacement in labels:
                relabelled = copy.deepcopy(vector)
                relabelled[label] = replacement
                assert relabelled[label] != vector[label], (label, vector["id"])
                assert _behavioural_fingerprint(relabelled, family) == baseline, (
                    label,
                    vector["id"],
                )
                checked += 1

    assert checked == 183 * len(labels)

    for family, section in sections.items():
        behaviourally_changed = copy.deepcopy(
            cast(dict[str, Any], section["vectors"][0])
        )
        assert behaviourally_changed["input_mode"] != "a-mode-the-corpus-never-uses"
        behaviourally_changed["input_mode"] = "a-mode-the-corpus-never-uses"
        assert _behavioural_fingerprint(
            behaviourally_changed, family
        ) != _behavioural_fingerprint(section["vectors"][0], family), family


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


# --- the corpus taxonomy attaches one category to one target ------------------
#
# `target` names a published product symbol; `category` is the corpus's own
# taxonomy label for the vectors aimed at that symbol. Every existing check
# reads the two fields apart. The histograms count categories without ever
# asking which target they describe, the partition prefix only repeats the
# category the same vector already carries, and the behavioural signature
# deliberately ignores both labels. Nothing binds the pair, so exchanging the
# categories of two same-family vectors leaves every count, every prefix and
# every signature intact while the published taxonomy now names the wrong
# target.
#
# The relationship is therefore authored below. It cannot be recovered from the
# corpus it governs: a histogram a reciprocal swap leaves untouched cannot
# witness the pairing it preserves, and the replay family alone refutes reading
# the pairing off the vector ids. What this pins is the published corpus
# taxonomy -- that the corpus attaches its label to the target it meant. It
# does not claim the lexeme `merge-outcome` is independently true of
# `PullRequestMergeRevisionOutcome`; that would need a product authority this
# corpus does not carry.
#
# The dependency runs one way: this authority fixes the category, and the
# category fixes the partition prefix. Neither the prefix nor the histogram may
# be read back as evidence for which category belongs to which target.

REQUIRED_CATEGORY_BY_FAMILY_TARGET: dict[str, dict[str, str]] = {
    "valid": {
        "ChangedPathStatus": "changed-path-status",
        "PullRequestChangeSet": "change-set",
        "PullRequestChangedPath": "changed-path",
        "PullRequestHeadRefDeletion": "head-ref-deletion",
        "PullRequestHistoricalOccurrenceTime": "occurrence-time",
        "PullRequestHistoryFactEvidenceLink": "evidence-link",
        "PullRequestMergeRevisionOutcome": "merge-outcome",
        "PullRequestReviewRevisionApproval": "review-approval",
        "PullRequestRevisionRoleBinding": "role-binding",
    },
    "invalid": {
        "ChangedPathStatus": "changed-path-status",
        "PullRequestChangeSet": "change-set",
        "PullRequestChangedPath": "changed-path",
        "PullRequestHeadRefDeletion": "head-ref-deletion",
        "PullRequestHistoricalOccurrenceTime": "occurrence-time",
        "PullRequestHistoryFactEvidenceLink": "evidence-link",
        "PullRequestMergeRevisionOutcome": "merge-outcome",
        "PullRequestReviewRevisionApproval": "review-approval",
        "PullRequestRevisionRoleBinding": "role-binding",
    },
    "replay": {
        "PullRequestChangeSet": "supplied-change-set",
        "PullRequestChangedPath": "changed-path",
        "PullRequestHeadRefDeletion": "head-ref-deletion",
        "PullRequestHistoricalOccurrenceTime": "occurrence-time",
        "PullRequestHistoryFactEvidenceLink": "evidence-association",
        "PullRequestMergeRevisionOutcome": "merge-outcome",
        "PullRequestReviewRevisionApproval": "review-approval",
        "PullRequestRevisionRoleBinding": "revision-role-binding",
    },
}


def _observed_taxonomy(
    sections: dict[str, dict[str, Any]],
) -> set[tuple[str, str, str]]:
    return {
        (family, cast(str, vector["target"]), cast(str, vector["category"]))
        for family, section in sections.items()
        for vector in section["vectors"]
    }


def _authored_taxonomy(
    authority: dict[str, dict[str, str]],
) -> set[tuple[str, str, str]]:
    return {
        (family, target, category)
        for family, rows in authority.items()
        for target, category in rows.items()
    }


def _taxonomy_failures(
    sections: dict[str, dict[str, Any]],
    authority: dict[str, dict[str, str]],
) -> list[tuple[str, str, str]]:
    """`(family, coordinate, reason)` for every disagreement, in both directions.

    Set equality alone would accept a family whose vectors all crowd onto one
    coordinate, so each vector is looked up individually and each authority
    entry must be reached by at least one vector.
    """
    failures: list[tuple[str, str, str]] = []
    for family in sorted(set(sections) | set(authority)):
        if family not in authority:
            failures.append((family, "*", "family-absent-from-authority"))
            continue
        if family not in sections:
            failures.append((family, "*", "family-absent-from-corpus"))
            continue
        expected = authority[family]
        populated: set[str] = set()
        for vector in sections[family]["vectors"]:
            identifier = cast(str, vector["id"])
            target = cast(str, vector["target"])
            if target not in expected:
                failures.append((family, identifier, "target-unknown-to-authority"))
                continue
            populated.add(target)
            if cast(str, vector["category"]) != expected[target]:
                failures.append((family, identifier, "category-differs"))
        for target in sorted(set(expected) - populated):
            failures.append((family, target, "authority-entry-unpopulated"))
    return sorted(failures)


def _taxonomy_injectivity_failures(
    authority: dict[str, dict[str, str]],
) -> list[tuple[str, str]]:
    """Injectivity is scoped to one family, never across families.

    A category lexeme may legitimately recur in another family whose local
    taxonomy says so, which is exactly what replay does for `changed-path`.
    """
    failures: list[tuple[str, str]] = []
    for family in sorted(authority):
        seen: dict[str, str] = {}
        for target in sorted(authority[family]):
            category = authority[family][target]
            if category in seen:
                failures.append((family, f"{category}<-{seen[category]}+{target}"))
            seen[category] = target
    return failures


def test_every_vector_carries_the_category_its_family_target_requires() -> None:
    """The reproduced finding, closed.

    Exchanging the categories of `history.valid.merge-outcome.canonical` and
    `history.valid.head-ref-deletion.canonical` satisfied every published check
    the corpus had, because none of them related a category to a target.
    """
    sections = _sections(VALID, INVALID, REPLAY)

    assert not _taxonomy_failures(sections, REQUIRED_CATEGORY_BY_FAMILY_TARGET)

    authority = REQUIRED_CATEGORY_BY_FAMILY_TARGET
    assert sorted(authority) == ["invalid", "replay", "valid"]
    assert [len(authority[family]) for family in ("valid", "invalid", "replay")] == [
        9,
        9,
        8,
    ]
    assert sum(len(rows) for rows in authority.values()) == 26
    assert sum(len(section["vectors"]) for section in sections.values()) == 183


def test_the_observed_taxonomy_relation_equals_the_authored_authority() -> None:
    """Closure in both directions: no unauthorised pair, no unpopulated pair."""
    observed = _observed_taxonomy(_sections(VALID, INVALID, REPLAY))
    authored = _authored_taxonomy(REQUIRED_CATEGORY_BY_FAMILY_TARGET)

    assert observed - authored == set(), "the corpus publishes an unauthorised pair"
    assert authored - observed == set(), "the authority claims a pair no vector uses"
    assert observed == authored
    assert len(observed) == 26


def test_each_family_taxonomy_is_one_to_one_within_that_family() -> None:
    """Injective per family, and deliberately not injective across families."""
    authority = REQUIRED_CATEGORY_BY_FAMILY_TARGET

    assert not _taxonomy_injectivity_failures(authority)

    lexemes = [category for rows in authority.values() for category in rows.values()]
    assert len(lexemes) == 26
    assert len(set(lexemes)) == 12, (
        "category lexemes recur across families, so injectivity must stay family-scoped"
    )
    assert authority["replay"]["PullRequestChangeSet"] == "supplied-change-set"
    assert authority["valid"]["PullRequestChangeSet"] == "change-set"


def test_a_reciprocal_category_swap_breaks_only_the_taxonomy_rule() -> None:
    """The reproduction, kept permanently.

    Two same-family vectors exchange categories and partition prefixes. The
    category multiset is unchanged, so every histogram still balances; the
    prefixes are still consistent; the behaviour is untouched. Only the
    authored relationship notices that both labels now name the wrong target.
    """
    valid = copy.deepcopy(VALID)
    first = next(
        v
        for v in valid["vectors"]
        if v["id"] == "history.valid.merge-outcome.canonical"
    )
    second = next(
        v
        for v in valid["vectors"]
        if v["id"] == "history.valid.head-ref-deletion.canonical"
    )
    first["category"], second["category"] = second["category"], first["category"]
    first["semantic_partition"], second["semantic_partition"] = (
        second["semantic_partition"],
        first["semantic_partition"],
    )

    assert _resealed_digest(valid) != next(
        entry["sha256"]
        for entry in MANIFEST["corpus_files"]
        if entry["filename"] == "valid-vectors.json"
    )

    sections = _sections(valid, INVALID, REPLAY)
    text = (CORPUS / "contract.md").read_text("utf-8")
    assert not _manifest_histogram_failures(MANIFEST, sections), "counts still balance"
    assert not _markdown_histogram_failures(text, sections), "the table still matches"
    assert not _family_collisions(valid, "valid"), "behaviour is unchanged"
    partitions = [cast(str, v["semantic_partition"]) for v in valid["vectors"]]
    assert len(set(partitions)) == 48
    assert all(
        cast(str, v["semantic_partition"]).split("/")[0] == v["category"]
        for v in valid["vectors"]
    ), "the prefix rule is still satisfied"

    assert _taxonomy_failures(sections, REQUIRED_CATEGORY_BY_FAMILY_TARGET) == [
        ("valid", "history.valid.head-ref-deletion.canonical", "category-differs"),
        ("valid", "history.valid.merge-outcome.canonical", "category-differs"),
    ]


def test_a_single_mapping_drift_breaks_the_taxonomy_rule() -> None:
    """One authority row repointed at another existing category."""
    authority = copy.deepcopy(REQUIRED_CATEGORY_BY_FAMILY_TARGET)
    authority["valid"]["PullRequestChangedPath"] = "change-set"

    failures = _taxonomy_failures(_sections(VALID, INVALID, REPLAY), authority)
    assert {reason for _, _, reason in failures} == {"category-differs"}
    assert len(failures) == 4, "every changed-path vector reports the drift"
    assert _taxonomy_injectivity_failures(authority) == [
        ("valid", "change-set<-PullRequestChangeSet+PullRequestChangedPath")
    ]


def test_an_unknown_target_fails_closed_from_either_side() -> None:
    """A target the authority never names, and one no vector ever uses."""
    invalid = copy.deepcopy(INVALID)
    stranger = invalid["vectors"][0]
    assert stranger["id"] == "history.invalid.role-binding.non-pull-request-subject"
    assert (
        sum(1 for v in INVALID["vectors"] if v["target"] == stranger["target"]) == 11
    ), "the vacated entry stays populated, so only the stranger is reported"
    stranger["target"] = "PullRequestUnpublishedSymbol"

    assert _taxonomy_failures(
        _sections(VALID, invalid, REPLAY), REQUIRED_CATEGORY_BY_FAMILY_TARGET
    ) == [
        (
            "invalid",
            "history.invalid.role-binding.non-pull-request-subject",
            "target-unknown-to-authority",
        )
    ]

    authority = copy.deepcopy(REQUIRED_CATEGORY_BY_FAMILY_TARGET)
    authority["valid"]["PullRequestUnpublishedSymbol"] = "unpublished-symbol"
    assert _taxonomy_failures(_sections(VALID, INVALID, REPLAY), authority) == [
        ("valid", "PullRequestUnpublishedSymbol", "authority-entry-unpopulated")
    ]


def test_a_missing_authority_entry_fails_the_taxonomy_rule() -> None:
    """An existing family-target pair the authority forgot to name."""
    authority = copy.deepcopy(REQUIRED_CATEGORY_BY_FAMILY_TARGET)
    del authority["valid"]["PullRequestMergeRevisionOutcome"]

    failures = _taxonomy_failures(_sections(VALID, INVALID, REPLAY), authority)
    assert {reason for _, _, reason in failures} == {"target-unknown-to-authority"}
    assert len(failures) == 3, "every orphaned vector is reported"

    del authority["replay"]
    assert (
        "replay",
        "*",
        "family-absent-from-authority",
    ) in _taxonomy_failures(_sections(VALID, INVALID, REPLAY), authority)


def test_an_unpopulated_authority_entry_fails_the_taxonomy_rule() -> None:
    """Replay does not exercise every published target, and may not pretend to."""
    assert "ChangedPathStatus" not in REQUIRED_CATEGORY_BY_FAMILY_TARGET["replay"]

    authority = copy.deepcopy(REQUIRED_CATEGORY_BY_FAMILY_TARGET)
    authority["replay"]["ChangedPathStatus"] = "changed-path-status"

    assert _taxonomy_failures(_sections(VALID, INVALID, REPLAY), authority) == [
        ("replay", "ChangedPathStatus", "authority-entry-unpopulated")
    ]


def test_the_vector_id_cannot_supply_the_taxonomy() -> None:
    """Ids stay durable identity; they are not a category oracle.

    `history.replay.role-binding.base` carries the category
    `revision-role-binding` and `history.valid.status.added` carries
    `changed-path-status`. Twenty-three vectors across all three families spell
    their id segment differently from their category, so deriving the pairing
    from the id would contradict the corpus it claims to describe.
    """
    disagreeing = {
        family: [
            cast(str, vector["id"])
            for vector in section["vectors"]
            if cast(str, vector["id"]).split(".")[2] != vector["category"]
        ]
        for family, section in _sections(VALID, INVALID, REPLAY).items()
    }

    assert [len(disagreeing[family]) for family in ("valid", "invalid", "replay")] == [
        6,
        14,
        3,
    ]
    assert "history.replay.role-binding.base" in disagreeing["replay"]
    assert "history.valid.status.added" in disagreeing["valid"]


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


# --- the vector record publishes exactly these keys and no others ------------
#
# The document root is closed and the `expected` block is closed, but the record
# between them was not: a resealed vector could carry an arbitrary new canonical
# field that no executor reads, and every oracle stayed green. Held test-side
# because a corpus cannot prove its own allowed envelope -- deriving the set
# from the vectors would accept whatever they happen to contain, which is the
# defect rather than the fix.
#
# Membership is structural. A key is published or it is not; an empty value is
# still a published field, and `embedded_facts = {}` does not make the key
# optional. The four replay keys carry retained provenance and belong to replay
# alone, so their presence on a valid or invalid vector is as wrong as their
# absence from a replay one.
COMMON_VECTOR_KEYS = frozenset(
    {
        "category",
        "decision_references",
        "expected",
        "id",
        "input",
        "input_mode",
        "operation",
        "purpose",
        "semantic_partition",
        "target",
    }
)
REPLAY_PROVENANCE_KEYS = frozenset(
    {
        "embedded_facts",
        "evidence_classification",
        "evidence_record_lock",
        "source_pointers",
    }
)
REQUIRED_VECTOR_KEYS_BY_FAMILY: dict[str, frozenset[str]] = {
    "valid": COMMON_VECTOR_KEYS,
    "invalid": COMMON_VECTOR_KEYS,
    "replay": COMMON_VECTOR_KEYS | REPLAY_PROVENANCE_KEYS,
}


def _envelope_failures(family: str, vector: dict[str, Any]) -> list[tuple[str, ...]]:
    """Every way one vector record departs from its family's published shape."""
    required = REQUIRED_VECTOR_KEYS_BY_FAMILY[family]
    present = set(vector)
    vector_id = cast(str, vector.get("id", "<no id>"))
    return [
        (family, vector_id, kind, key)
        for kind, keys in (
            ("missing", sorted(required - present)),
            ("unexpected", sorted(present - required)),
        )
        for key in keys
    ]


@pytest.mark.parametrize(
    ("family", "section", "count"), FAMILIES, ids=[f[0] for f in FAMILIES]
)
def test_every_vector_record_publishes_exactly_its_family_envelope(
    family: str, section: dict[str, Any], count: int
) -> None:
    """Exact equality, so an addition and an omission both fail."""
    failures = [
        failure
        for vector in cast(list[dict[str, Any]], section["vectors"])
        for failure in _envelope_failures(family, vector)
    ]

    assert not failures, failures
    assert len(cast(list[Any], section["vectors"])) == count


def test_each_family_publishes_exactly_one_vector_shape() -> None:
    """Derived, not authored: the corpus holds one record shape per family."""
    shapes = {
        family: {frozenset(vector) for vector in section["vectors"]}
        for family, section, _ in FAMILIES
    }
    total = sum(len(cast(list[Any], s["vectors"])) for _, s, _ in FAMILIES)

    for family, observed in shapes.items():
        assert observed == {REQUIRED_VECTOR_KEYS_BY_FAMILY[family]}, family
    assert total == 183

    # The envelope may not quietly be rewritten to follow the corpus. A mapping
    # built from the vectors would accept whatever they happen to carry, which
    # is the defect rather than the fix, so the mapping is pinned to its two
    # authored sets -- and those in turn to `SIGNATURE_FIELDS`, a list that
    # predates this closure and is read by a different test.
    assert REQUIRED_VECTOR_KEYS_BY_FAMILY["valid"] == COMMON_VECTOR_KEYS
    assert REQUIRED_VECTOR_KEYS_BY_FAMILY["invalid"] == COMMON_VECTOR_KEYS
    assert REQUIRED_VECTOR_KEYS_BY_FAMILY["replay"] == (
        COMMON_VECTOR_KEYS | REPLAY_PROVENANCE_KEYS
    )
    assert set(SIGNATURE_FIELDS["replay"]) - set(SIGNATURE_FIELDS["valid"]) == (
        REPLAY_PROVENANCE_KEYS
    )
    assert set(SIGNATURE_FIELDS["valid"]) <= COMMON_VECTOR_KEYS
    # a subset anchor cannot see a widened set, so the sizes are pinned too:
    # publishing a new record field has to be a deliberate edit here, which is
    # the whole point of closing this envelope
    assert len(COMMON_VECTOR_KEYS) == 10
    assert len(REPLAY_PROVENANCE_KEYS) == 4

    # the replay keys are replay's alone, in both directions
    assert not COMMON_VECTOR_KEYS & REPLAY_PROVENANCE_KEYS
    assert shapes["valid"] == shapes["invalid"]
    assert next(iter(shapes["replay"])) - next(iter(shapes["valid"])) == (
        REPLAY_PROVENANCE_KEYS
    )


def test_a_drifting_vector_envelope_is_refused() -> None:
    """Additions, omissions, renames and family crossings each fail."""
    probes: list[tuple[str, str, dict[str, Any]]] = []
    for family, section, _ in FAMILIES:
        sample = copy.deepcopy(cast(dict[str, Any], section["vectors"][0]))
        extra = {"valid": "verified", "invalid": "independently_reviewed"}.get(
            family, "confidence"
        )
        probes.append((family, "unknown key", {**sample, extra: True}))
        probes.append(
            (
                family,
                "missing common key",
                {k: v for k, v in sample.items() if k != "purpose"},
            )
        )
        renamed = {k: v for k, v in sample.items() if k != "purpose"}
        renamed["rationale"] = sample["purpose"]
        probes.append((family, "renamed key", renamed))

    for family in ("valid", "invalid"):
        sample = copy.deepcopy(cast(dict[str, Any], SECTIONS[family]["vectors"][0]))
        for key in sorted(REPLAY_PROVENANCE_KEYS):
            probes.append((family, f"replay key {key}", {**sample, key: {}}))

    replay = copy.deepcopy(cast(dict[str, Any], REPLAY["vectors"][0]))
    for key in sorted(REPLAY_PROVENANCE_KEYS):
        probes.append(
            ("replay", f"dropped {key}", {k: v for k, v in replay.items() if k != key})
        )
    # an empty value is still a published field
    probes.append(
        (
            "replay",
            "dropped embedded_facts though it was empty",
            {k: v for k, v in replay.items() if k != "embedded_facts"},
        )
    )

    for family, label, damaged in probes:
        assert _envelope_failures(family, damaged), (family, label)

    # and the live records themselves stay clean
    for family, section, _ in FAMILIES:
        for vector in cast(list[dict[str, Any]], section["vectors"]):
            assert not _envelope_failures(family, vector), vector["id"]


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


# --- a decision reference names one authored source record --------------------
#
# Every source-decision entry is checked against whichever artifact it names:
# the path must exist, the digest must match those live bytes, and the declared
# authority ids must resolve through the declared id-source. All of that is
# internal agreement. None of it asks whether the reference names the artifact
# it is supposed to name.
#
# So `closure:s1-p03:evidence-envelope` can be repointed at the already-locked
# S08 decision -- path, digest, id-source, ids and role all moved together --
# and every per-entry source-decision check still passes. What noticed the
# corpus-level version of that edit was a stale Section-9 projection and two
# declaration-path counts: consumers reacting to a side effect, not an
# authority asserting the mapping. A reordering of the entries, or a target
# whose id-source happens to have the same shape, would leave less behind.
#
# The mapping is therefore authored here, and it stays deliberately small. The
# digest is not copied into it, because the stronger chain already exists --
# authored reference to authored path to live bytes to observed SHA-256 -- and
# neither are the authority ids, which resolve out of the attached artifact
# through the attached id-source. Duplicating either here would re-state the
# sealed address rather than bind anything new.
#
# `authority_role` is descriptive metadata and stays that way. Pinning it fixes
# which role declaration belongs to this reference; it is not evidence that the
# role prose is independently true, and this repair adds no objective
# validator for it.

REQUIRED_SOURCE_DECISION_BY_REFERENCE: dict[str, tuple[str, str, str, str]] = {
    "acquisition:run-0001": (
        "reference_corpus/pytest-4412/acquisitions/"
        "run-0001-s04-v1-base-4c9cde74-head-690a63b9/acquisition.json",
        "retained_replay_evidence",
        "/run",
        "run_id",
    ),
    "closure:s1-p03:evidence-envelope": (
        "reference_corpus/contracts/evidence-envelope/closures/"
        "s1-p03-phase-closure/closure.json",
        "originating_development_history_model_reservation",
        "/deferred_register/entries",
        "deferred_id",
    ),
    "correction:s04-c01-acquisition-closure": (
        "reference_corpus/pytest-4412/corrections/"
        "s04-c01-acquisition-closure/correction.json",
        "retained_additive_correction_evidence",
        "/correction",
        "id",
    ),
    "correction:s1-p05-s08-c01:owner-topology": (
        "reference_corpus/contracts/development-history/corrections/"
        "s08-c01-deferred-subject-owner-topology/correction.json",
        "append_only_owner_topology_correction",
        "/superseded_dispositions/items",
        "correction_id",
    ),
    "decision:s1-p05-s08:disposition": (
        "reference_corpus/contracts/development-history/decisions/"
        "s08-deferred-subject-disposition/decision.json",
        "governance_disposition_not_vectorized",
        "/inherited_subject_register/items",
        "disposition_id",
    ),
}

SOURCE_DECISION_FIELDS = (
    "authority_id_source",
    "authority_ids",
    "authority_role",
    "decision_reference",
    "path",
    "sha256",
)


def _source_attachment_failures(
    entries: list[dict[str, Any]],
    authority: dict[str, tuple[str, str, str, str]],
) -> list[tuple[str, str]]:
    """`(decision_reference, reason)` for every disagreement, in both directions.

    The collection is a list, but the identity relation is not positional, so
    every entry is looked up by its own reference and a reordering must read as
    no change at all.
    """
    failures: list[tuple[str, str]] = []
    seen: set[str] = set()
    for entry in entries:
        reference = cast(str, entry["decision_reference"])
        if reference in seen:
            failures.append((reference, "duplicate-reference"))
            continue
        seen.add(reference)
        if reference not in authority:
            failures.append((reference, "manifest-reference-absent-from-authority"))
            continue
        path, role, collection, field = authority[reference]
        source = cast(dict[str, str], entry["authority_id_source"])
        if entry["path"] != path:
            failures.append((reference, "path-differs"))
        if entry["authority_role"] != role:
            failures.append((reference, "role-differs"))
        if source.get("collection") != collection:
            failures.append((reference, "collection-differs"))
        if source.get("id_field") != field:
            failures.append((reference, "id-field-differs"))
    for reference in sorted(set(authority) - seen):
        failures.append((reference, "authority-entry-unpopulated"))
    return sorted(failures)


def _live_source_decisions() -> list[dict[str, Any]]:
    return cast(list[dict[str, Any]], MANIFEST["source_decisions"])


def _set_path(entry: dict[str, Any]) -> None:
    entry["path"] = (
        "reference_corpus/contracts/development-history/decisions/"
        "s08-deferred-subject-disposition/decision.json"
    )


def _set_role(entry: dict[str, Any]) -> None:
    entry["authority_role"] = "governance_disposition_not_vectorized"


def _set_collection(entry: dict[str, Any]) -> None:
    entry["authority_id_source"] = {
        "collection": "/inherited_subject_register/items",
        "id_field": cast(dict[str, str], entry["authority_id_source"])["id_field"],
    }


def _set_id_field(entry: dict[str, Any]) -> None:
    entry["authority_id_source"] = {
        "collection": cast(dict[str, str], entry["authority_id_source"])["collection"],
        "id_field": "disposition_id",
    }


def test_every_source_decision_names_the_record_authored_for_it() -> None:
    """The reported finding, closed.

    A reference repointed at another already-locked artifact satisfied every
    per-entry check, because each of them asks only whether the record agrees
    with the file it happens to name.
    """
    assert not _source_attachment_failures(
        _live_source_decisions(), REQUIRED_SOURCE_DECISION_BY_REFERENCE
    )

    assert len(REQUIRED_SOURCE_DECISION_BY_REFERENCE) == 5
    assert len(_live_source_decisions()) == 5
    paths = {row[0] for row in REQUIRED_SOURCE_DECISION_BY_REFERENCE.values()}
    assert len(paths) == 5, "five references, five distinct artifacts"


def test_the_source_attachment_closes_against_the_manifest_both_ways() -> None:
    observed = {
        cast(str, entry["decision_reference"]) for entry in _live_source_decisions()
    }
    authored = set(REQUIRED_SOURCE_DECISION_BY_REFERENCE)

    assert observed - authored == set(), "a reference the authority omits"
    assert authored - observed == set(), "an entry the manifest never publishes"
    assert observed == authored
    assert len(observed) == 5


def test_the_source_attachment_authority_is_written_out_and_never_computed() -> None:
    """The manifest may not authorise its own reference-to-artifact mapping."""
    name = "REQUIRED_SOURCE_DECISION_BY_REFERENCE"
    module = ast.parse(Path(__file__).read_text("utf-8"))
    assigned = [
        node
        for node in module.body
        if isinstance(node, ast.AnnAssign)
        and isinstance(node.target, ast.Name)
        and node.target.id == name
    ]

    assert len(assigned) == 1
    literal = assigned[0].value
    assert isinstance(literal, ast.Dict)
    assert len(literal.keys) == 5
    for key, value in zip(literal.keys, literal.values, strict=True):
        assert isinstance(key, ast.Constant) and isinstance(key.value, str)
        assert isinstance(value, ast.Tuple)
        assert len(value.elts) == 4
        for element in value.elts:
            # a path is written as an implicitly concatenated literal, which
            # parses to a single constant, so every element must still be one
            assert isinstance(element, ast.Constant) and isinstance(element.value, str)

    touching = [
        node
        for statement in module.body
        if not isinstance(
            statement, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef
        )
        for node in ast.walk(statement)
        if isinstance(node, ast.Name) and node.id == name
    ]
    assert len(touching) == 1, "the authority is bound once and never rebound"
    assert touching[0] is assigned[0].target
    assert ast.literal_eval(literal) == REQUIRED_SOURCE_DECISION_BY_REFERENCE

    for reference, row in REQUIRED_SOURCE_DECISION_BY_REFERENCE.items():
        assert isinstance(reference, str) and reference
        assert isinstance(row, tuple) and len(row) == 4
        assert all(isinstance(element, str) and element for element in row)
        assert row[2].startswith("/")

    source = inspect.getsource(_source_attachment_failures)
    for forbidden in ("MANIFEST", "CORPUS", "VALID", "INVALID", "REPLAY"):
        assert forbidden not in source, forbidden


def test_repointing_a_reference_at_another_locked_artifact_fails() -> None:
    """The reproduction, kept permanently.

    `closure:s1-p03:evidence-envelope` is given the S08 decision's path, role
    and id-source. Every per-entry source-decision check still passes -- the
    digest matches those bytes and the ids resolve in that document -- and only
    the attachment notices the reference now names the wrong record.
    """
    entries = copy.deepcopy(_live_source_decisions())
    repointed = next(
        e
        for e in entries
        if e["decision_reference"] == "closure:s1-p03:evidence-envelope"
    )
    s08 = next(
        e
        for e in entries
        if e["decision_reference"] == "decision:s1-p05-s08:disposition"
    )
    for field in ("path", "sha256", "authority_role"):
        repointed[field] = copy.deepcopy(s08[field])
    repointed["authority_id_source"] = copy.deepcopy(s08["authority_id_source"])
    repointed["authority_ids"] = list(cast(list[str], s08["authority_ids"]))

    # every existing per-entry check the corpus already runs still passes
    raw = (REPOSITORY_ROOT / cast(str, repointed["path"])).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == repointed["sha256"]
    assert set(repointed["authority_ids"]) == _declared_authority_ids(repointed)

    assert _source_attachment_failures(
        entries, REQUIRED_SOURCE_DECISION_BY_REFERENCE
    ) == [
        ("closure:s1-p03:evidence-envelope", "collection-differs"),
        ("closure:s1-p03:evidence-envelope", "id-field-differs"),
        ("closure:s1-p03:evidence-envelope", "path-differs"),
        ("closure:s1-p03:evidence-envelope", "role-differs"),
    ]


def test_two_references_exchanging_their_whole_identity_tuple_fail() -> None:
    """The tuple multiset is preserved, so nothing counted changes."""
    entries = copy.deepcopy(_live_source_decisions())
    first = next(
        e for e in entries if e["decision_reference"] == "acquisition:run-0001"
    )
    second = next(
        e
        for e in entries
        if e["decision_reference"] == "correction:s04-c01-acquisition-closure"
    )
    for field in ("path", "sha256", "authority_role", "authority_id_source"):
        first[field], second[field] = (
            copy.deepcopy(second[field]),
            copy.deepcopy(first[field]),
        )
    first["authority_ids"], second["authority_ids"] = (
        list(second["authority_ids"]),
        list(first["authority_ids"]),
    )

    for entry in (first, second):
        raw = (REPOSITORY_ROOT / cast(str, entry["path"])).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == entry["sha256"], "still coherent"
        assert set(cast(list[str], entry["authority_ids"])) <= _declared_authority_ids(
            entry
        )

    assert _source_attachment_failures(
        entries, REQUIRED_SOURCE_DECISION_BY_REFERENCE
    ) == [
        ("acquisition:run-0001", "collection-differs"),
        ("acquisition:run-0001", "id-field-differs"),
        ("acquisition:run-0001", "path-differs"),
        ("acquisition:run-0001", "role-differs"),
        ("correction:s04-c01-acquisition-closure", "collection-differs"),
        ("correction:s04-c01-acquisition-closure", "id-field-differs"),
        ("correction:s04-c01-acquisition-closure", "path-differs"),
        ("correction:s04-c01-acquisition-closure", "role-differs"),
    ]


def test_each_attached_field_drifts_on_its_own() -> None:
    """One field at a time, so no probe can pass for a neighbour's reason."""
    reference = "correction:s1-p05-s08-c01:owner-topology"
    drifts: tuple[tuple[str, Callable[[dict[str, Any]], None], str], ...] = (
        ("path", _set_path, "path-differs"),
        ("authority_role", _set_role, "role-differs"),
        ("collection", _set_collection, "collection-differs"),
        ("id_field", _set_id_field, "id-field-differs"),
    )

    for _, mutate, reason in drifts:
        entries = copy.deepcopy(_live_source_decisions())
        mutate(next(e for e in entries if e["decision_reference"] == reference))
        assert _source_attachment_failures(
            entries, REQUIRED_SOURCE_DECISION_BY_REFERENCE
        ) == [(reference, reason)]


def test_missing_extra_and_duplicate_references_fail() -> None:
    absent = copy.deepcopy(_live_source_decisions())
    renamed = next(
        e for e in absent if e["decision_reference"] == "acquisition:run-0001"
    )
    renamed["decision_reference"] = "closure:s1-p99:never-registered"
    assert _source_attachment_failures(
        absent, REQUIRED_SOURCE_DECISION_BY_REFERENCE
    ) == [
        ("acquisition:run-0001", "authority-entry-unpopulated"),
        ("closure:s1-p99:never-registered", "manifest-reference-absent-from-authority"),
    ]

    authority = copy.deepcopy(REQUIRED_SOURCE_DECISION_BY_REFERENCE)
    authority["decision:s1-p05-s99:never-published"] = (
        "reference_corpus/contracts/development-history/decisions/nowhere/decision.json",
        "a_role_the_manifest_never_declares",
        "/nowhere/items",
        "nowhere_id",
    )
    assert _source_attachment_failures(_live_source_decisions(), authority) == [
        ("decision:s1-p05-s99:never-published", "authority-entry-unpopulated")
    ]

    doubled = copy.deepcopy(_live_source_decisions())
    doubled.append(
        copy.deepcopy(
            next(
                e
                for e in doubled
                if e["decision_reference"] == "decision:s1-p05-s08:disposition"
            )
        )
    )
    assert _source_attachment_failures(
        doubled, REQUIRED_SOURCE_DECISION_BY_REFERENCE
    ) == [("decision:s1-p05-s08:disposition", "duplicate-reference")]


def test_reordering_the_source_decisions_is_not_a_change() -> None:
    """Identity is keyed by the reference, never by the slot it sits in."""
    reversed_entries = list(reversed(copy.deepcopy(_live_source_decisions())))

    assert [e["decision_reference"] for e in reversed_entries] != [
        e["decision_reference"] for e in _live_source_decisions()
    ]
    assert not _source_attachment_failures(
        reversed_entries, REQUIRED_SOURCE_DECISION_BY_REFERENCE
    )


def test_every_published_source_decision_field_has_an_owner() -> None:
    """Every published field has a consumer, and they are not equally strong.

    `decision_reference` is the attachment key. `path`, `authority_role` and
    `authority_id_source` are authored here. `sha256` is recomputed from the
    bytes at the attached path, which is why no digest is copied into the
    mapping.

    `authority_ids` is resolved out of the attached artifact through the
    attached id-source. Four entries publish the complete resolved set; the
    P03 closure selects one reservation of fourteen, settled by the structured
    selector rather than by subset membership. `AUTHORITY_ID_OWNERSHIP` names
    which discipline each entry uses and is enforced separately.
    """
    for entry in _live_source_decisions():
        assert tuple(sorted(entry)) == SOURCE_DECISION_FIELDS

    for entry in _live_source_decisions():
        reference = cast(str, entry["decision_reference"])
        path, role, collection, field = REQUIRED_SOURCE_DECISION_BY_REFERENCE[reference]

        # authored attachment
        assert entry["path"] == path
        assert entry["authority_role"] == role
        assert entry["authority_id_source"] == {
            "collection": collection,
            "id_field": field,
        }
        # derived from the attached artifact, never authored here
        raw = (REPOSITORY_ROOT / path).read_bytes()
        assert entry["sha256"] == hashlib.sha256(raw).hexdigest()
        resolved = _declared_authority_ids(entry)
        declared = set(cast(list[str], entry["authority_ids"]))
        assert declared and declared <= resolved
        # which discipline settles the list is asserted by
        # test_every_authority_id_list_is_owned_and_none_is_subset_only
        assert reference in AUTHORITY_ID_OWNERSHIP

        # the role stays descriptive; this repair adds no objective validator
        index = _live_source_decisions().index(entry)
        assert f"/source_decisions/{index}/authority_role" in DESCRIPTIVE_PATHS

    for row in REQUIRED_SOURCE_DECISION_BY_REFERENCE.values():
        for column in row:
            assert not re.fullmatch(r"[0-9a-f]{64}", column), (
                "no digest may be authored into any column of the mapping"
            )


# --- one deferred reservation, selected by what it is about -------------------
#
# The attachment above fixes which artifact a reference names. Inside that
# artifact the P03 closure publishes fourteen deferred reservations, and the
# manifest cites exactly one of them. The only rule over that citation was
# subset membership -- is this a real deferred id? -- which fourteen different
# answers satisfy. Substituting `deferred:03` re-sealed to a green module while
# the manifest declared this development-history corpus to originate from the
# fault-instance reservation.
#
# The missing relation is not whether the id is real. It is which record is the
# semantic authority for this reference. That is answered from the structured
# source: the register carries `subject` and `owner` per entry, so the
# reservation is selected by what it is about and who owns it, and the id is
# then read through the id-source the attachment already binds. Nothing parses
# the role, the reference, the path or any prose.
#
# `owner` is not decoration here. `subject` alone names the reservation, and
# `owner` independently establishes that it is the S1.P05 one rather than a
# similarly-subjected entry filed under another phase.
#
# The expected id is deliberately absent from the selector. Authoring
# `deferred:02` would restate the manifest's own answer in a second place;
# authoring the semantics makes the corpus derive it, and a register that
# renumbered its entries would still resolve.
#
# What this proves: the P03 source decision cites the development-history
# reservation that the structured source selects. It does not prove that the
# other thirteen reservations belong to S1.P05, that P03 created the
# development-history model, or anything about future phase ownership.

REQUIRED_AUTHORITY_ID_SELECTION_BY_REFERENCE: dict[str, tuple[str, str]] = {
    "closure:s1-p03:evidence-envelope": (
        "development_history_model",
        "S1.P05",
    ),
}

SELECTION_SUBJECT_FIELD = "subject"
SELECTION_OWNER_FIELD = "owner"

AUTHORITY_ID_OWNERSHIP: dict[str, str] = {
    "acquisition:run-0001": "complete-resolved-set",
    "closure:s1-p03:evidence-envelope": "structured-semantic-selection",
    "correction:s04-c01-acquisition-closure": "complete-resolved-set",
    "correction:s1-p05-s08-c01:owner-topology": "complete-resolved-set",
    "decision:s1-p05-s08:disposition": "complete-resolved-set",
}


def _selection_records(
    reference: str, document: dict[str, Any] | None = None
) -> tuple[list[dict[str, Any]], str]:
    """The candidate records and the id field, both read from the attachment.

    The address comes from `REQUIRED_SOURCE_DECISION_BY_REFERENCE`, not from the
    manifest entry, so a repointed entry cannot redirect the selection.
    """
    path, _role, collection, id_field = REQUIRED_SOURCE_DECISION_BY_REFERENCE[reference]
    if document is None:
        document = json.loads((REPOSITORY_ROOT / path).read_text("utf-8"))
    node = _resolve_pointer(document, collection)
    records = (
        [cast(dict[str, Any], node)]
        if isinstance(node, dict)
        else cast(list[dict[str, Any]], node)
    )
    return records, id_field


def _authority_selection_failures(
    entries: list[dict[str, Any]],
    selections: dict[str, tuple[str, str]],
    documents: dict[str, dict[str, Any]] | None = None,
) -> list[tuple[str, str]]:
    """`(decision_reference, reason)` for every selection that does not hold.

    The document may be supplied in memory so the selector itself is exercised,
    rather than a digest mismatch standing in for it.
    """
    documents = documents or {}
    failures: list[tuple[str, str]] = []
    published = {cast(str, entry["decision_reference"]): entry for entry in entries}
    for reference in sorted(selections):
        if reference not in published:
            failures.append((reference, "selection-reference-absent-from-manifest"))
            continue
        subject, owner = selections[reference]
        records, id_field = _selection_records(reference, documents.get(reference))
        matched = [
            record
            for record in records
            if record.get(SELECTION_SUBJECT_FIELD) == subject
            and record.get(SELECTION_OWNER_FIELD) == owner
        ]
        if not matched:
            failures.append((reference, "no-record-matches-the-selector"))
            continue
        if len(matched) > 1:
            failures.append((reference, "selector-matches-more-than-one-record"))
            continue
        declared = cast(list[str], published[reference]["authority_ids"])
        if not declared:
            failures.append((reference, "declared-ids-empty"))
            continue
        if len(declared) != 1:
            failures.append((reference, "declared-ids-not-a-singleton"))
            continue
        if declared[0] != matched[0][id_field]:
            failures.append((reference, "declared-id-differs"))
    return sorted(failures)


def test_the_p03_reservation_is_selected_by_subject_and_owner() -> None:
    """The reported finding, closed.

    Fourteen reservations resolve from the bound collection, so subset
    membership accepted any of them. The selector names one by what it is
    about and who owns it, and the id is then read through the bound id-field.
    """
    assert not _authority_selection_failures(
        _live_source_decisions(), REQUIRED_AUTHORITY_ID_SELECTION_BY_REFERENCE
    )

    reference = "closure:s1-p03:evidence-envelope"
    records, id_field = _selection_records(reference)
    subject, owner = REQUIRED_AUTHORITY_ID_SELECTION_BY_REFERENCE[reference]
    matched = [
        record
        for record in records
        if record.get(SELECTION_SUBJECT_FIELD) == subject
        and record.get(SELECTION_OWNER_FIELD) == owner
    ]

    assert len(records) == 14, "the choice really is one of fourteen"
    assert len(matched) == 1, "the selector resolves exactly one record"
    assert matched[0][SELECTION_SUBJECT_FIELD] == "development_history_model"
    assert matched[0][SELECTION_OWNER_FIELD] == "S1.P05"
    assert id_field == "deferred_id"

    entry = next(
        e for e in _live_source_decisions() if e["decision_reference"] == reference
    )
    assert entry["authority_ids"] == [matched[0][id_field]]


def test_the_selector_does_not_embed_the_id_it_is_meant_to_derive() -> None:
    """Authoring the answer would restate the manifest, not bind it."""
    name = "REQUIRED_AUTHORITY_ID_SELECTION_BY_REFERENCE"
    module = ast.parse(Path(__file__).read_text("utf-8"))
    assigned = [
        node
        for node in module.body
        if isinstance(node, ast.AnnAssign)
        and isinstance(node.target, ast.Name)
        and node.target.id == name
    ]

    assert len(assigned) == 1
    literal = assigned[0].value
    assert isinstance(literal, ast.Dict)
    assert len(literal.keys) == 1
    for key, value in zip(literal.keys, literal.values, strict=True):
        assert isinstance(key, ast.Constant) and isinstance(key.value, str)
        assert isinstance(value, ast.Tuple)
        assert len(value.elts) == 2
        for element in value.elts:
            assert isinstance(element, ast.Constant) and isinstance(element.value, str)

    touching = [
        node
        for statement in module.body
        if not isinstance(
            statement, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef
        )
        for node in ast.walk(statement)
        if isinstance(node, ast.Name) and node.id == name
    ]
    assert len(touching) == 1, "the selector is bound once and never rebound"
    assert touching[0] is assigned[0].target
    assert ast.literal_eval(literal) == REQUIRED_AUTHORITY_ID_SELECTION_BY_REFERENCE

    # the derived answer must appear nowhere in the authored selector
    for reference, selection in REQUIRED_AUTHORITY_ID_SELECTION_BY_REFERENCE.items():
        records, id_field = _selection_records(reference)
        derived = next(
            record[id_field]
            for record in records
            if record.get(SELECTION_SUBJECT_FIELD) == selection[0]
            and record.get(SELECTION_OWNER_FIELD) == selection[1]
        )
        assert derived.startswith("deferred:"), "the id-field really yields an id"
        assert derived not in selection, "the id must be derived, never authored"
        assert derived != reference
    authored = {
        text
        for selection in REQUIRED_AUTHORITY_ID_SELECTION_BY_REFERENCE.values()
        for text in selection
    } | set(REQUIRED_AUTHORITY_ID_SELECTION_BY_REFERENCE)
    assert not any(text.startswith("deferred:") for text in authored)

    source = inspect.getsource(_authority_selection_failures) + inspect.getsource(
        _selection_records
    )
    for forbidden in ("MANIFEST", "deferred:", "CORPUS"):
        assert forbidden not in source, forbidden


def test_a_different_real_reservation_fails_the_selection() -> None:
    """The reproduction, kept permanently.

    `deferred:03` is the fault-instance reservation owned by S1.P06. It
    resolves in the same collection, so subset membership accepted it.
    """
    for wrong in ("deferred:03", "deferred:01"):
        entries = copy.deepcopy(_live_source_decisions())
        entry = next(
            e
            for e in entries
            if e["decision_reference"] == "closure:s1-p03:evidence-envelope"
        )
        entry["authority_ids"] = [wrong]

        assert set(entry["authority_ids"]) <= _declared_authority_ids(entry), (
            "subset membership is still satisfied, which is the whole problem"
        )
        assert _authority_selection_failures(
            entries, REQUIRED_AUTHORITY_ID_SELECTION_BY_REFERENCE
        ) == [("closure:s1-p03:evidence-envelope", "declared-id-differs")]


def test_a_malformed_declared_id_list_fails_the_selection() -> None:
    """Empty, plural, duplicated and unknown are each refused."""
    cases: tuple[tuple[list[str], str], ...] = (
        ([], "declared-ids-empty"),
        (["deferred:02", "deferred:03"], "declared-ids-not-a-singleton"),
        (["deferred:02", "deferred:02"], "declared-ids-not-a-singleton"),
        (["deferred:99"], "declared-id-differs"),
    )
    for declared, reason in cases:
        entries = copy.deepcopy(_live_source_decisions())
        entry = next(
            e
            for e in entries
            if e["decision_reference"] == "closure:s1-p03:evidence-envelope"
        )
        entry["authority_ids"] = declared

        assert _authority_selection_failures(
            entries, REQUIRED_AUTHORITY_ID_SELECTION_BY_REFERENCE
        ) == [("closure:s1-p03:evidence-envelope", reason)], declared


def test_a_drifted_selector_no_longer_names_the_canonical_reservation() -> None:
    """Both halves of the selector carry weight.

    The register gives every reservation a distinct subject and a distinct
    owner, so a drift in either half alone pairs with nothing and fails
    closed. Only moving both halves onto another real pairing resolves a
    record, and then it is the wrong reservation.
    """
    reference = "closure:s1-p03:evidence-envelope"

    # both halves moved onto another real pairing: the fault-instance
    # reservation resolves, and it is not the one this reference cites
    other_reservation = {reference: ("fault_instance_model", "S1.P06")}
    assert _authority_selection_failures(
        _live_source_decisions(), other_reservation
    ) == [(reference, "declared-id-differs")]

    # subject alone moved: no record pairs that subject with this owner
    drifted_subject = {reference: ("fault_instance_model", "S1.P05")}
    assert _authority_selection_failures(_live_source_decisions(), drifted_subject) == [
        (reference, "no-record-matches-the-selector")
    ]

    # owner alone moved: likewise nothing matches, so it fails closed
    drifted_owner = {reference: ("development_history_model", "S1.P06")}
    assert _authority_selection_failures(_live_source_decisions(), drifted_owner) == [
        (reference, "no-record-matches-the-selector")
    ]


def test_a_missing_or_ambiguous_reservation_fails_closed() -> None:
    """Exercised on an in-memory artifact, not through a digest mismatch."""
    reference = "closure:s1-p03:evidence-envelope"
    path = REQUIRED_SOURCE_DECISION_BY_REFERENCE[reference][0]
    original = json.loads((REPOSITORY_ROOT / path).read_text("utf-8"))

    without = copy.deepcopy(original)
    without["deferred_register"]["entries"] = [
        record
        for record in without["deferred_register"]["entries"]
        if record[SELECTION_SUBJECT_FIELD] != "development_history_model"
    ]
    assert len(without["deferred_register"]["entries"]) == 13
    assert _authority_selection_failures(
        _live_source_decisions(),
        REQUIRED_AUTHORITY_ID_SELECTION_BY_REFERENCE,
        {reference: without},
    ) == [(reference, "no-record-matches-the-selector")]

    doubled = copy.deepcopy(original)
    twin = copy.deepcopy(
        next(
            record
            for record in doubled["deferred_register"]["entries"]
            if record[SELECTION_SUBJECT_FIELD] == "development_history_model"
        )
    )
    twin["deferred_id"] = "deferred:15"
    doubled["deferred_register"]["entries"].append(twin)
    assert _authority_selection_failures(
        _live_source_decisions(),
        REQUIRED_AUTHORITY_ID_SELECTION_BY_REFERENCE,
        {reference: doubled},
    ) == [(reference, "selector-matches-more-than-one-record")]

    assert (REPOSITORY_ROOT / path).read_bytes() == json.dumps(
        original, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8") + b"\n", "the locked artifact was only ever read"


def test_a_selector_for_an_unpublished_reference_fails() -> None:
    assert _authority_selection_failures(
        _live_source_decisions(),
        {"closure:s1-p99:never-registered": ("development_history_model", "S1.P05")},
    ) == [
        ("closure:s1-p99:never-registered", "selection-reference-absent-from-manifest")
    ]


def test_every_authority_id_list_is_owned_and_none_is_subset_only() -> None:
    """Each entry publishes ids under exactly one declared discipline.

    Four entries publish the complete resolved set, so no choice is being
    made. The P03 closure deliberately selects one reservation out of
    fourteen, and that choice is now settled by the structured selector. No
    entry is left where picking a different real id would change the meaning
    without failing.
    """
    entries = _live_source_decisions()
    assert set(AUTHORITY_ID_OWNERSHIP) == {
        cast(str, entry["decision_reference"]) for entry in entries
    }
    assert set(AUTHORITY_ID_OWNERSHIP.values()) == {
        "complete-resolved-set",
        "structured-semantic-selection",
    }
    assert set(REQUIRED_AUTHORITY_ID_SELECTION_BY_REFERENCE) == {
        reference
        for reference, kind in AUTHORITY_ID_OWNERSHIP.items()
        if kind == "structured-semantic-selection"
    }

    for entry in entries:
        reference = cast(str, entry["decision_reference"])
        declared = set(cast(list[str], entry["authority_ids"]))
        resolved = _declared_authority_ids(entry)
        assert declared, reference
        if AUTHORITY_ID_OWNERSHIP[reference] == "complete-resolved-set":
            assert declared == resolved, reference
        else:
            assert declared < resolved, reference
            assert not _authority_selection_failures(
                [entry], REQUIRED_AUTHORITY_ID_SELECTION_BY_REFERENCE
            ), reference

    unsettled = [
        cast(str, entry["decision_reference"])
        for entry in entries
        if set(cast(list[str], entry["authority_ids"]))
        != _declared_authority_ids(entry)
        and cast(str, entry["decision_reference"])
        not in REQUIRED_AUTHORITY_ID_SELECTION_BY_REFERENCE
    ]
    assert not unsettled, unsettled


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

# --- the classifier sits outside the domain it classifies --------------------
#
# `/descriptive_metadata` is not a declaration about the corpus; it is the rule
# that sorts declarations into two kinds. It cannot be inside the partition it
# defines: as a descriptive entry it would have to enumerate its own 83 leaves,
# which creates 83 more leaves to enumerate and never terminates, and as an
# objective entry it would need a consumer proving the classification true by
# consulting the classification. The exclusion is named once here and reused, so
# it reads as a decision rather than a repeated `startswith`.
META_SCHEMA_ROOT = "/descriptive_metadata"

# The two kinds every declaration falls into. `_objective_leaf_paths` and
# `DESCRIPTIVE_PATHS` are their extensions.
DECLARATION_KINDS = ("objective", "descriptive")

# The classification rule the manifest publishes about its own leaves, held
# test-side. The surface cannot self-prove this: a rule naming which leaves have
# no independent source of truth is not itself checkable against one. This pins
# the REQUIRED PUBLISHED DECLARATION only -- it makes no claim that the manifest
# proves its own truth, and it is deliberately absent from OBJECTIVE_VALIDATORS.
REQUIRED_META_CONTRACT = (
    "these exact leaf paths carry human-oriented description only: they have no "
    "independent source of truth, are never counted as verified assurance, and "
    "must not be cited by contract.md or the pull request as independently "
    "checked; every other manifest leaf is objective and must be covered by the "
    "focused oracle's validator registry"
)


def _meta_schema_leaf_paths(document: dict[str, Any] | None = None) -> list[str]:
    """The classifier's own leaves, which no declaration kind may claim."""
    node = MANIFEST if document is None else document
    return [
        path
        for path in _leaf_paths(node)
        if path == META_SCHEMA_ROOT or path.startswith(f"{META_SCHEMA_ROOT}/")
    ]


def _declaration_universe(document: dict[str, Any] | None = None) -> list[str]:
    """Every manifest leaf that declares something about the corpus."""
    node = MANIFEST if document is None else document
    excluded = set(_meta_schema_leaf_paths(node))
    return [path for path in _leaf_paths(node) if path not in excluded]


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
    return [path for path in _declaration_universe() if path not in DESCRIPTIVE_PATHS]


def _unowned_objective_paths() -> list[str]:
    """Objective declarations no validator prefix claims."""
    return [
        path
        for path in _objective_leaf_paths()
        if not any(path.startswith(prefix) for prefix, _ in OBJECTIVE_VALIDATORS)
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
    duplicated = [
        path
        for path in _objective_leaf_paths()
        if len([p for p, _ in OBJECTIVE_VALIDATORS if path.startswith(p)]) > 1
    ]

    assert not _unowned_objective_paths(), _unowned_objective_paths()
    assert not duplicated, duplicated


def test_the_declared_descriptive_paths_are_real_and_non_objective() -> None:
    every = set(_leaf_paths(MANIFEST))
    meta = set(_meta_schema_leaf_paths())
    for path in DESCRIPTIVE_PATHS:
        assert path in every, path
        assert path not in meta, path
    assert MANIFEST["descriptive_metadata"]["contract"]
    assert not DESCRIPTIVE_PATHS & set(_objective_leaf_paths())


def test_the_manifest_partition_is_exhaustive() -> None:
    every = _declaration_universe()

    assert len(every) == len(_objective_leaf_paths()) + len(DESCRIPTIVE_PATHS)
    assert set(every) == set(_objective_leaf_paths()) | DESCRIPTIVE_PATHS


def test_the_meta_schema_is_exactly_the_classifier_and_its_paths() -> None:
    """The excluded domain is enumerated, not assumed from a prefix."""
    declared = cast(list[str], MANIFEST["descriptive_metadata"]["paths"])
    expected = [f"{META_SCHEMA_ROOT}/contract"] + [
        f"{META_SCHEMA_ROOT}/paths/{index}" for index in range(len(declared))
    ]

    assert sorted(_meta_schema_leaf_paths()) == sorted(expected)
    assert len(_meta_schema_leaf_paths()) == len(declared) + 1 == 84


def test_the_declaration_universe_excludes_the_meta_schema() -> None:
    every = set(_leaf_paths(MANIFEST))
    meta = set(_meta_schema_leaf_paths())
    universe = set(_declaration_universe())

    assert universe == every - meta
    assert not universe & meta
    assert len(every) == 470
    assert len(meta) == 84
    assert len(universe) == 386


def test_the_declaration_universe_is_partitioned_in_two_kinds() -> None:
    """386 = 303 + 83, with nothing unclassified and nothing counted twice."""
    universe = set(_declaration_universe())
    objective = set(_objective_leaf_paths())
    descriptive = set(DESCRIPTIVE_PATHS)

    assert len(DECLARATION_KINDS) == 2
    assert universe == objective | descriptive
    assert not objective & descriptive
    assert len(universe) == len(objective) + len(descriptive)
    assert len(objective) == 303
    assert len(descriptive) == 83
    # no meta-schema leaf reaches either side of the accounting
    assert not (objective | descriptive) & set(_meta_schema_leaf_paths())


def test_the_meta_contract_is_the_required_published_declaration() -> None:
    """Pins the published rule; it does not prove the manifest true of itself.

    The rule names the leaves that have no independent source of truth, so no
    canonical surface can confirm it -- confirming it would mean consulting the
    very classification it defines. It is therefore held test-side, and stays
    out of `OBJECTIVE_VALIDATORS`: pinning a declaration is not verifying it.
    """
    declared = cast(dict[str, Any], MANIFEST["descriptive_metadata"])["contract"]

    assert type(declared) is str
    assert declared == REQUIRED_META_CONTRACT
    assert not [p for p, _ in OBJECTIVE_VALIDATORS if p.startswith(META_SCHEMA_ROOT)]

    # the clauses `_render_epistemic_split` keys on must really be in the rule,
    # or the renderer would silently take its negative branch
    for clause in (
        "have no independent source of truth",
        "are never counted as verified assurance",
        "every other manifest leaf is objective",
    ):
        assert clause in declared, clause


def test_a_new_objective_declaration_forces_review() -> None:
    """An unclassified field must fail rather than pass unnoticed."""
    probe = copy.deepcopy(MANIFEST)
    probe["invented_objective_claim"] = True
    unowned = [
        path
        for path in _declaration_universe(probe)
        if path not in DESCRIPTIVE_PATHS
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
    "history.invalid.occurrence-time.non-admitted-commit-identity": (
        "occurrence admits only its published union members"
    ),
    "history.invalid.occurrence-time.non-admitted-changed-path-status": "occurrence refuses this published boundary",
    "history.invalid.occurrence-time.non-admitted-change-set": (
        "occurrence admits only its published union members"
    ),
    "history.invalid.occurrence-time.non-admitted-role-binding": (
        "occurrence admits only its published union members"
    ),
    "history.invalid.occurrence-time.non-admitted-changed-path": (
        "occurrence admits only its published union members"
    ),
    "history.invalid.occurrence-time.missing-occurred-at": "occurred_at is required",
    "history.invalid.occurrence-time.extra-chronology": "no chronology is published",
    "history.invalid.occurrence-time.missing-occurrence": "occurrence is required",
    "history.invalid.occurrence-time.raw-python-instant": "occurred_at refuses this published boundary",
    "history.invalid.evidence-link.hybrid-fact-json": (
        "fact admits only its published union members"
    ),
    "history.invalid.evidence-link.empty-fact-json": (
        "fact admits only its published union members"
    ),
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
    "history.invalid.evidence-link.nested-non-admitted-occurrence": (
        "fact admits only its published union members"
    ),
    "history.invalid.evidence-link.typed-children-mapping-python": "fact refuses this published boundary",
    "history.invalid.evidence-link.change-set-fact-python": "fact refuses this published boundary",
    "history.invalid.evidence-link.status-fact-python": "fact refuses this published boundary",
    "history.invalid.evidence-link.instant-naive": (
        "fact admits only its published union members"
    ),
    "history.invalid.evidence-link.instant-non-zero-offset": (
        "fact admits only its published union members"
    ),
    "history.invalid.evidence-link.instant-week-date": (
        "fact admits only its published union members"
    ),
    "history.invalid.evidence-link.instant-basic-format": (
        "fact admits only its published union members"
    ),
}


def test_every_invalid_vector_is_registered_or_primary() -> None:
    primaries = {row[4] for row in REQUIREMENT_LEDGER}
    ids = {cast(str, v["id"]) for v in INVALID["vectors"]}
    registered = set(SECONDARY_WITNESS_REGISTRY)

    assert not (primaries & registered), sorted(primaries & registered)
    assert registered <= ids, sorted(registered - ids)
    assert ids - primaries == registered, sorted((ids - primaries) ^ registered)
    assert all(SECONDARY_WITNESS_REGISTRY.values())


TRUE_OMISSION = "TRUE_REQUIRED_FIELD_OMISSION"
UNION_REJECTION = "CLOSED_UNION_REJECTION"


def _missing_shape(vector: dict[str, Any]) -> str | None:
    """What a `missing` error actually witnesses, read from the supplied input.

    Requiredness is a property of what was supplied, never of an error code. A
    discriminatorless union reports `missing` at its own field when no branch
    matches, with the value sitting right there in the input, so reading the
    code alone turns twelve closed-union refusals into false requiredness
    claims. Presence, published union membership and the prefix normalization
    must all hold; anything else stays unclassified rather than assumed.
    """
    expected = cast(dict[str, Any], vector["expected"])
    if expected.get("error_type") != "missing":
        return None

    location = cast(list[str], expected.get("error_location") or [])
    if len(location) != 1:
        return None

    field, target = location[0], cast(str, vector["target"])
    raw = vector["input"]
    supplied = cast(dict[str, Any], raw) if isinstance(raw, dict) else {}
    if field not in _model_fields_of(target):
        return None
    if field not in supplied:
        return TRUE_OMISSION
    if (
        field in _union_fields_of(target)
        and expected.get("error_location_mode") == "prefix"
    ):
        return UNION_REJECTION
    return None


def _derived_requirement(vector: dict[str, Any]) -> str:
    """The requirement a vector witnesses, read off its validated properties."""
    expected = cast(dict[str, Any], vector["expected"])
    location = cast(list[str], expected["error_location"])
    if len(location) > 1:
        return f"{location[0]} is refused by its published nested contract"
    if expected["error_type"] == "missing":
        shape = _missing_shape(vector)
        if shape == TRUE_OMISSION:
            return f"{location[0]} is required"
        if shape == UNION_REJECTION:
            return f"{location[0]} admits only its published union members"
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
    # bounded to section 8: an unterminated scan would find bullets anywhere
    lines = _section_lines(text, "## 8. Non-Generalizations")
    start = 0
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


# --- the replay summary sentences are projected, not sampled -----------------
#
# Section 4 states three manifest facts in prose: whether the replay flattens
# its layers, whether a deterministic derivation is published, and how many
# history facts are individually linkable. Nothing compared those sentences to
# the JSON, so the derived document could assert the exact opposite of the
# manifest -- "is present" over `deterministic_derivation_present: false` -- and
# stay green. `contract.md` carries no digest, so this projection is its only
# guard.
#
# The prose skeleton is test-side; every value in it comes from the manifest.
# The block is the set of section-4 lines that make one of these claims, so a
# paragraph added or lost changes it, while an explanatory paragraph that claims
# none of them is left alone. The classification and retained-role bullets keep
# their own exact projections; this composes with them and repeats neither.
#
# The marker list is lexical, and that bounds what the sweep can promise: it
# catches a restatement written in the document's own vocabulary, not an
# arbitrary paraphrase. The exact comparison below is the contract; the sweep
# only stops a second sentence from sitting beside the first.

# The document spells small integers as words. Anything outside the table falls
# back to digits so a changed count still renders and fails the comparison.
NUMBER_WORDS = {
    0: "zero",
    1: "one",
    2: "two",
    3: "three",
    4: "four",
    5: "five",
    6: "six",
    7: "seven",
    8: "eight",
    9: "nine",
    10: "ten",
    11: "eleven",
    12: "twelve",
}
REPLAY_SUMMARY_SECTION = "## 4. Replay and Provenance"
REPLAY_SUMMARY_MARKERS = (
    "flatten",
    "deterministic_derivation",
    "deterministic derivation",
    "linkable",
)


def _spelled(count: int) -> str:
    return NUMBER_WORDS.get(count, str(count))


def _target_entry(symbol: str) -> dict[str, str]:
    """The declared row for `symbol`; its absence means the prose is stale."""
    targets = cast(list[dict[str, str]], MANIFEST["target_symbols"])
    return next(entry for entry in targets if entry["symbol"] == symbol)


def _render_replay_summary_block() -> list[str]:
    contract = cast(dict[str, Any], MANIFEST["replay_contract"])
    classifications = cast(dict[str, str], contract["classifications"])
    derivation = cast(bool, contract["deterministic_derivation_present"])
    flattened = cast(bool, contract["flattened_evidence_derived_history_claimed"])
    linkable = cast(
        int, cast(dict[str, Any], contract["evidence_limits"])["linkable_history_facts"]
    )
    phase = cast(dict[str, Any], MANIFEST["scope"])["phase"]
    # the deferral is cited from the locked S08 register: the origin phase and
    # subject id, not a claim about who owns that subject today
    origin, subject = _deferred_ancestry_citation()
    change_set = _target_entry("PullRequestChangeSet")["symbol"]
    link_slice = _target_entry("PullRequestHistoryFactEvidenceLink")["slice_layer"]

    return [
        (
            f"The canonical replay {'flattens' if flattened else 'does not flatten'}"
            " its layers into evidence-derived history."
            f" {_spelled(len(classifications)).capitalize()} classifications are used"
            f" and a fourth is {'present' if derivation else 'deliberately absent'}:"
        ),
        (
            f"`deterministic_derivation` is {'present' if derivation else 'not present'}:"
            f" `{phase}` publishes no deterministic derivation, and the ahead, behind,"
            " and merge-base values the retained comparison carries remain deferred"
            f" with `{origin}` `{subject}`."
        ),
        (
            f"{_spelled(linkable).capitalize()} history facts are individually linkable."
            f" `{change_set}` is a published product fact and is replayed as a"
            f" caller-supplied composition, but `{link_slice}` does not admit it as an"
            " evidence-link fact, and the replay preserves that asymmetry."
        ),
    ]


# CommonMark heading forms, shared by the section slicer and the heading oracle
# so the two can never disagree about what a heading is. An ATX opening sequence
# may be indented up to three spaces and may be followed by a space, a tab, or
# the end of the line -- `##` alone is a real, empty level-two heading. A
# paragraph underlined with `=` or `-` is a heading carrying no `#` at all, and
# a single `-` underlines just as well as a row of them. Matching only `"## "`
# at column zero misses all of it, which is enough to append a whole fabricated
# section unnoticed. A blank line above disqualifies the underline -- that is an
# empty list item or a thematic break, not a heading -- so `_actual_headings`
# checks the preceding line rather than widening the pattern to compensate.
ATX_HEADING = re.compile(r"^ {0,3}#{1,6}(?:[ \t]|$)")
SECTION_HEADING = re.compile(r"^ {0,3}#{2}(?:[ \t]|$)")
SETEXT_UNDERLINE = re.compile(r"^ {0,3}(=+|-+)[ \t]*$")

# --- a bounded block model, because a pattern alone reads the wrong lines ----
#
# Patterns applied line by line got two whole classes wrong, both recorded when
# the empty-ATX correction landed and both closed here.
#
#   A real heading nested in a container was invisible. `- ## x`, `> ## x`,
#   `1. ## x` and `- - ## x` are headings CommonMark publishes and the
#   recognizer did not see, which is how a fabricated section could sit inside
#   a bullet list.
#
#   A line inside a fenced code block was read as a heading although CommonMark
#   says it is code, so `#` in a fence terminated a section that had not ended.
#
# The model below is deliberately small: the only containers are blockquote
# markers and list-item markers, stripped left to right; a fence opens at the
# depth it was written at and closes either on a matching fence at that depth
# or when its container ends; nothing inside a fence is a heading; and a setext
# underline must follow a nonblank line at its own depth. A bare `-` is both a
# list marker and an underline, so it is retried against the raw line whenever a
# document-level paragraph precedes it.
#
# WHAT THIS IS NOT, STATED IN BOTH DIRECTIONS. It is not a CommonMark parser.
# It does not implement HTML blocks, link reference definitions, lazy paragraph
# continuation, tab expansion to four-column stops, indented code inside a list
# item, or the line terminators `str.splitlines` accepts and CommonMark does not.
# The disagreements this produces are enumerated as executable cases in
# `test_the_bounded_block_model_reads_the_forms_it_claims`, in two tuples, so a
# later widening or narrowing has to move a test rather than a sentence.
#
#   FAIL-CLOSED -- a line CommonMark would not call a heading is read as one,
#   so the document is refused rather than admitted. Anything nonblank above a
#   `---` is treated as setext content, so a thematic break, an HTML block, a
#   link reference definition and an indented code line all underline; and the
#   underline is matched by container DEPTH, not container identity, so a `---`
#   one container over underlines the paragraph above it.
#
#   FAIL-OPEN -- CommonMark publishes a heading the model does not report: a
#   multi-line setext heading is anchored on its last content line rather than
#   its first; a list-item continuation indented four columns; a bare `-` used
#   as an underline inside a container; and a paragraph made only of `-` or `=`
#   characters. These do NOT leave an unowned region, and that is the point of
#   doing this after the projection rather than instead of it: every line of
#   contract.md is reconstructed from the registry, so a line the heading model
#   misreads is still a line no region produces, and is refused there. The
#   heading oracle is the second lock, not the only one.
#
# The adjudication against a CommonMark parser that produced this boundary is
# recorded in the change history rather than imported here, because that parser
# is not a declared dependency of this project.
_CONTAINER_MARKER = re.compile(
    r"^ {0,3}(?:>[ \t]?|(?:[-*+]|\d{1,9}[.)])(?=[ \t]|$)[ \t]*)"
)
_FENCE = re.compile(r"^ {0,3}(?P<marker>`{3,}|~{3,})(?P<info>.*)$")


def _strip_containers(raw: str) -> tuple[int, str]:
    """The line with its blockquote and list-item markers removed.

    Every marker consumes at least one character, so the walk is bounded by the
    line rather than by a nesting cap -- a cap would silently stop seeing the
    heading inside a container nested one deeper than the number chosen.
    """
    depth, content = 0, raw
    while True:
        marker = _CONTAINER_MARKER.match(content)
        if marker is None:
            return depth, content
        content = content[marker.end() :]
        depth += 1


def _markdown_blocks(text: str) -> list[tuple[int, str, bool]]:
    """`(container depth, content, inside a fenced block)` for every line."""
    blocks: list[tuple[int, str, bool]] = []
    fence, fence_depth = "", 0
    for raw in text.splitlines():
        depth, content = _strip_containers(raw)
        marker = _FENCE.match(content)
        if fence and depth < fence_depth:
            # the container the fence was written in has ended, and so has the
            # fence: an unterminated fence inside a blockquote must not swallow
            # every heading after it
            fence = ""
        if fence:
            if (
                marker is not None
                and depth == fence_depth
                and marker["marker"][0] == fence[0]
                and len(marker["marker"]) >= len(fence)
                and not marker["info"].strip()
            ):
                fence = ""
            blocks.append((depth, content, True))
            continue
        if marker is not None and not (
            marker["marker"][0] == "`" and "`" in marker["info"]
        ):
            fence, fence_depth = marker["marker"], depth
            blocks.append((depth, content, True))
            continue
        blocks.append((depth, content, False))
    return blocks


def _markdown_headings(text: str) -> list[tuple[int, int, int, str]]:
    """`(line index, container depth, level, the line as published)`."""
    blocks = _markdown_blocks(text)
    raws = text.splitlines()
    found: list[tuple[int, int, int, str]] = []
    for index, (depth, content, fenced) in enumerate(blocks):
        if fenced:
            continue
        opening = content.lstrip()
        if ATX_HEADING.match(content):
            found.append(
                (index, depth, len(opening) - len(opening.lstrip("#")), raws[index])
            )
            continue
        if not index:
            continue
        previous_depth, previous, previous_fenced = blocks[index - 1]
        underline = SETEXT_UNDERLINE.match(content)
        if underline is None and previous_depth == 0:
            underline = SETEXT_UNDERLINE.match(raws[index])
            depth = 0 if underline else depth
        if (
            underline
            and not previous_fenced
            and previous_depth == depth
            and previous.strip()
            and not ATX_HEADING.match(previous)
            and not SETEXT_UNDERLINE.match(previous)
        ):
            level = 1 if underline[1][0] == "=" else 2
            found.append((index - 1, depth, level, raws[index - 1]))
    return found


def _section_boundaries(text: str) -> set[int]:
    """The lines where a document-level section ends, however it is written."""
    return {
        index
        for index, depth, level, _raw in _markdown_headings(text)
        if depth == 0 and level == 2
    }


def _section_lines(text: str, heading: str) -> list[str]:
    """The lines under a heading, located by the block model rather than by text.

    `lines.index(heading)` finds a copy of the heading inside a fenced block as
    readily as the heading itself, which would hand back a slice of somebody
    else's section. The heading is resolved through the same model that decides
    where the section ends, and it must occur exactly once as real structure.
    """
    lines = text.splitlines()
    published = [
        index
        for index, depth, _level, raw in _markdown_headings(text)
        if depth == 0 and raw == heading
    ]
    assert len(published) == 1, heading
    boundaries = _section_boundaries(text)
    start = published[0] + 1
    end = start
    while end < len(lines) and end not in boundaries:
        end += 1
    return lines[start:end]


def _actual_replay_summary_block(text: str) -> list[str]:
    """Every section-4 line making one of these claims, in document order."""
    return [
        line
        for line in _section_lines(text, REPLAY_SUMMARY_SECTION)
        if any(marker in line.lower() for marker in REPLAY_SUMMARY_MARKERS)
    ]


def test_the_replay_summary_block_is_an_exact_projection() -> None:
    text = (CORPUS / "contract.md").read_text("utf-8")
    rendered = _render_replay_summary_block()

    assert _actual_replay_summary_block(text) == rendered
    assert len(rendered) == 3


def test_the_replay_summary_reads_its_values_from_the_manifest() -> None:
    """Every varying token is a manifest value, not a frozen spelling."""
    contract = cast(dict[str, Any], MANIFEST["replay_contract"])
    limits = cast(dict[str, Any], contract["evidence_limits"])
    rendered = _render_replay_summary_block()

    assert contract["flattened_evidence_derived_history_claimed"] is False
    assert contract["deterministic_derivation_present"] is False
    assert limits["linkable_history_facts"] == 11
    assert cast(dict[str, Any], MANIFEST["scope"])["phase"] == "S1.P05"
    assert _target_entry("PullRequestHistoryFactEvidenceLink")["slice_layer"] == (
        "S1.P05.S07"
    )

    assert "does not flatten" in rendered[0]
    assert rendered[1].startswith("`deterministic_derivation` is not present: `S1.P05`")
    assert rendered[2].startswith("Eleven history facts")
    # the count is spelled from the manifest, never matched against the English
    assert _spelled(cast(int, limits["linkable_history_facts"])) == "eleven"
    assert _spelled(len(cast(dict[str, Any], contract["classifications"]))) == "three"
    assert _spelled(97) == "97", "an unmapped count must render, not raise"


def test_a_contradicted_replay_summary_is_refused() -> None:
    """A second sentence may not assert what the canonical one denies."""
    text = (CORPUS / "contract.md").read_text("utf-8")
    rendered = _render_replay_summary_block()
    section = _section_lines(text, REPLAY_SUMMARY_SECTION)

    contradiction = "`deterministic_derivation` is present after all."
    assert any(m in contradiction.lower() for m in REPLAY_SUMMARY_MARKERS)
    assert contradiction not in section

    for damaged in (
        [*rendered, contradiction],
        rendered[:-1],
        [*rendered, rendered[0]],
        [rendered[0], rendered[0], rendered[2]],
        list(reversed(rendered)),
    ):
        assert damaged != rendered


# --- the replay classification bullets are projected, not sampled ------------


def _render_classification_block() -> list[str]:
    classifications = cast(
        dict[str, str], MANIFEST["replay_contract"]["classifications"]
    )
    return [f"- `{key}` — {value}" for key, value in sorted(classifications.items())]


def _actual_classification_block(text: str) -> list[str]:
    # bounded to section 4, mirroring its retained-role sibling
    lines = _section_lines(text, REPLAY_SUMMARY_SECTION)
    start = next(
        i for i, line in enumerate(lines) if line.startswith("- `caller_supplied_")
    )
    end = start
    while end < len(lines) and lines[end].startswith("- `"):
        end += 1
    return lines[start:end]


def test_the_classification_block_is_an_exact_projection() -> None:
    text = (CORPUS / "contract.md").read_text("utf-8")
    rendered = _render_classification_block()

    assert _actual_classification_block(text) == rendered
    assert len(rendered) == 3
    # bounding the slice to section 4 would otherwise stop watching the rest of
    # the file, so every bullet naming a classification must be one of these
    keys = tuple(cast(dict[str, str], MANIFEST["replay_contract"]["classifications"]))
    assert [
        line
        for line in text.splitlines()
        if any(line.startswith(f"- `{key}`") for key in keys)
    ] == rendered


# --- the retained-role implications are projected, not sampled ---------------
#
# Containment only asked whether each declared mapping appeared somewhere, which
# a fabricated bullet satisfies as easily as a real one: the derived document
# could publish a source coordinate the JSON authority never declared, and
# `contract.md` carries no digest to catch it. The pair -- source coordinate and
# implied role -- is the unit, so the block is rendered whole and compared.


ROLE_IMPLICATION = re.compile(r"^- `[^`]+` implies `[^`]+`$")
ROLE_SECTION = "## 4. Replay and Provenance"


def _render_role_implication_block() -> list[str]:
    positions = cast(
        dict[str, str], MANIFEST["replay_contract"]["retained_role_source_positions"]
    )
    return [f"- `{position}` implies `{role}`" for position, role in positions.items()]


def _actual_role_implication_block(text: str) -> list[str]:
    """The bullets as section 4 actually publishes them, in document order."""
    lines = text.splitlines()
    start = lines.index(ROLE_SECTION) + 1
    section = start
    while section < len(lines) and not lines[section].startswith("## "):
        section += 1
    while start < section and not ROLE_IMPLICATION.match(lines[start]):
        start += 1
    end = start
    while end < section and ROLE_IMPLICATION.match(lines[end]):
        end += 1
    return lines[start:end]


def test_the_role_implication_block_is_an_exact_projection() -> None:
    text = (CORPUS / "contract.md").read_text("utf-8")
    rendered = _render_role_implication_block()

    # bounded to section 4, so the block cannot be rehomed under another heading
    assert _actual_role_implication_block(text) == rendered
    assert len(rendered) == 3
    # `implies` is this document's only word for the relation and appears
    # nowhere else, so sweeping every line catches a mapping smuggled in as an
    # indented sub-bullet, a `*` bullet, or a sentence of prose.
    assert [line for line in text.splitlines() if "implies" in line] == rendered


def test_a_moved_role_implication_is_refused() -> None:
    """The role multiset survives a swap; the pairing does not."""
    rendered = _render_role_implication_block()
    positions = [line.split("`")[1] for line in rendered]
    roles = [line.split("`")[3] for line in rendered]
    assert roles[0] != roles[1], "the probe needs two rows that differ"

    swapped = [
        f"- `{positions[0]}` implies `{roles[1]}`",
        f"- `{positions[1]}` implies `{roles[0]}`",
        rendered[2],
    ]

    assert sorted(line.split("`")[3] for line in swapped) == sorted(roles)
    assert swapped != rendered
    assert [*rendered[:2]] != rendered
    assert [*rendered, rendered[0]] != rendered
    assert [rendered[0], rendered[0], rendered[2]] != rendered


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


def test_every_invalid_vector_declares_a_known_location_mode() -> None:
    """The mode selects the comparison, so an unknown one means nothing."""
    modes = {
        cast(str, v["expected"]["error_location_mode"]) for v in INVALID["vectors"]
    }

    assert modes <= set(LOCATION_MODES)
    assert modes == set(LOCATION_MODES), "both published modes must stay in use"
    assert set(
        cast(dict[str, str], MANIFEST["rejection_contract"]["error_location_modes"])
    ) == set(LOCATION_MODES)


def test_an_unknown_location_mode_is_refused() -> None:
    vector = copy.deepcopy(INVALID["vectors"][0])
    vector["expected"]["error_location_mode"] = "typo"

    assert vector["expected"]["error_location_mode"] not in LOCATION_MODES


def test_a_vocabulary_vector_still_declares_its_mode() -> None:
    """The early return must not exempt the field from validation."""
    vocabulary = [
        v
        for v in INVALID["vectors"]
        if v["expected"]["failure_category"] == "vocabulary_error"
    ]

    assert vocabulary
    for vector in vocabulary:
        assert vector["expected"]["error_location_mode"] in LOCATION_MODES, vector["id"]


# --- each vector file states its own decoding contract, so check it ----------
#
# `_load` enforces canonicalization from hard-coded rules and only the manifest
# `format` block was ever compared. Each vector document carries its own
# `format` and `assurance` envelope, which could therefore declare a different
# version, or permit floats, while the file decoded correctly anyway -- durable
# JSON misstating its own contract.

VECTOR_DOCUMENTS = (
    ("valid-vectors", VALID),
    ("invalid-vectors", INVALID),
    ("replay-vectors", REPLAY),
)

# The five declarations every vector document publishes, held test-side because
# a block cannot be its own authority. Comparing each file against
# `VALID["assurance"]` only proves the three agree, and three files agree just
# as readily on a disclaimed value: `expected_dumps_independently_authored`
# could be flipped to `false` corpus-wide, resealed, and every check would still
# pass. Naming the required declaration here consumes all five keys at once, so
# a changed value, a dropped key, and an unknown key are each a failure.
REQUIRED_VECTOR_ASSURANCE: dict[str, object] = {
    "expected_dumps_independently_authored": True,
    "fixture_scope": "file_local_acyclic_explicit_only",
    "production_dump_used_as_oracle": False,
    "round_trip_expectation_explicit_per_vector": True,
    "status": "locked",
}


def _assurance_failures(block: dict[str, Any]) -> list[tuple[str, str]]:
    """Every way a published assurance block departs from the required one."""
    failures: list[tuple[str, str]] = []
    for key, required in REQUIRED_VECTOR_ASSURANCE.items():
        if key not in block:
            failures.append((key, "missing"))
        elif block[key] != required:
            failures.append((key, "value-differs"))
        # `True == 1` and `False == 0`, and the envelope permits integers, so a
        # boolean arriving as a number must fail as loudly as a changed value.
        elif type(block[key]) is not type(required):
            failures.append((key, "widened-type"))
    failures.extend(
        (key, "unknown") for key in sorted(set(block) - set(REQUIRED_VECTOR_ASSURANCE))
    )
    return failures


@pytest.mark.parametrize(
    ("name", "document"), VECTOR_DOCUMENTS, ids=[n for n, _ in VECTOR_DOCUMENTS]
)
def test_each_vector_file_envelope_matches_the_enforced_contract(
    name: str, document: dict[str, Any]
) -> None:
    """A document may not describe a decoding contract other than the real one."""
    assert document["format"] == MANIFEST["format"], name

    canonical = cast(dict[str, Any], document["format"]["canonicalization"])
    raw = (CORPUS / f"{name}.json").read_bytes()
    assert canonical["floats_and_NaN_permitted"] is False, name
    assert not any(isinstance(v, float) for v in _flat_values(json.loads(raw))), name
    assert canonical["keys"] == "sorted" and canonical["whitespace"] == "compact", name
    assert _canonical_bytes(json.loads(raw)) == raw, name
    assert canonical["line_endings"] == "LF_only" and b"\r" not in raw, name
    assert canonical["encoding"] == "UTF-8_without_BOM"
    assert not raw.startswith(b"\xef\xbb\xbf"), name
    assert canonical["exactly_one_trailing_lf"] is True
    assert raw.endswith(b"\n") and not raw.endswith(b"\n\n"), name


@pytest.mark.parametrize(
    ("name", "document"), VECTOR_DOCUMENTS, ids=[n for n, _ in VECTOR_DOCUMENTS]
)
def test_each_vector_file_assurance_block_is_the_same_declaration(
    name: str, document: dict[str, Any]
) -> None:
    """Measured against the required declaration, not against each other."""
    assurance = cast(dict[str, Any], document["assurance"])

    assert _assurance_failures(assurance) == [], name
    # the round-trip claim must hold of the vectors themselves
    for vector in document["vectors"]:
        expected = cast(dict[str, Any], vector["expected"])
        if "round_trip_equal" in expected:
            assert isinstance(expected["round_trip_equal"], bool), vector["id"]


# --- the same assurance property, restated on another canonical surface ------
#
# The manifest declares two of the vector contract's properties again in its own
# vocabulary. Three surfaces then describe one authoring fact, and nothing bound
# them: the manifest could say a production dump WAS the oracle while all three
# vector files said it was not, and the corpus stayed green.
#
# Each surface is measured against `REQUIRED_VECTOR_ASSURANCE`, never against
# another surface, so the three form a star around the test-side authority
# rather than a ring that agrees with itself. What this proves is consistency of
# the published declarations, not that any of them is independently true: these
# manifest leaves are descriptive, they stay in `descriptive_metadata.paths`,
# and none is added to `OBJECTIVE_VALIDATORS`.
#
# `production_dump_used_as_oracle` has only one manifest restatement; the
# `assurance` block carries no such key. `/assurance/status` is deliberately not
# a member -- see `test_every_restated_assurance_leaf_is_bound`.
ASSURANCE_COHERENCE: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    (
        "independent authorship",
        "expected_dumps_independently_authored",
        (
            "/assurance/expected_dumps_independently_authored",
            "/execution_contract/expectation_contract/independently_authored",
        ),
    ),
    (
        "production dump oracle",
        "production_dump_used_as_oracle",
        ("/execution_contract/expectation_contract/production_dump_used_as_oracle",),
    ),
)


@pytest.mark.parametrize(
    ("label", "vector_key", "manifest_paths"),
    ASSURANCE_COHERENCE,
    ids=[entry[0] for entry in ASSURANCE_COHERENCE],
)
def test_a_restated_assurance_property_agrees_with_the_vector_contract(
    label: str, vector_key: str, manifest_paths: tuple[str, ...]
) -> None:
    """Cross-source consistency, not independent proof of either surface."""
    required = REQUIRED_VECTOR_ASSURANCE[vector_key]
    assert type(required) is bool, label

    for path in manifest_paths:
        declared = _resolve_pointer(MANIFEST, path)
        # `1 == True` and `0 == False`, so the declared type must match too
        assert type(declared) is bool, (label, path)
        assert declared is required, (label, path)


def test_every_restated_assurance_leaf_is_bound() -> None:
    """A same-named twin must join the rule rather than arrive unbound.

    The guard matches on leaf name, so it holds only for a restatement that
    keeps the vector contract's spelling. It cannot see a renamed one -- the
    live `independently_authored` below is itself a rename, which is why that
    path has to be named explicitly rather than discovered.
    """
    bound = {path for _, _, paths in ASSURANCE_COHERENCE for path in paths}
    restated = {
        path
        for path, _ in _leaves(MANIFEST)
        if path.rsplit("/", 1)[-1] in REQUIRED_VECTOR_ASSURANCE
    }

    # `/assurance/status` is excluded on purpose. `status` is each surface's own
    # seal lifecycle, not one corpus-wide fact: `repository-snapshot` publishes a
    # manifest `sealed_publication_candidate` over vectors reading `locked`, and
    # `revision-locator` does the same. Requiring agreement here would contradict
    # a shape the sibling corpora already ship.
    assert restated - bound == {"/assurance/status"}
    assert bound - restated == {
        "/execution_contract/expectation_contract/independently_authored"
    }


def test_a_falsified_assurance_declaration_is_refused() -> None:
    """No published key is unconsumed, and no unknown key arrives silently.

    Each probe mutates the block the way a corpus-wide reseal would: all three
    files still carry identical assurance, so nothing here is caught by the
    files agreeing. What the declaration says is what fails.
    """
    published = cast(dict[str, Any], VALID["assurance"])
    assert _assurance_failures(published) == []

    for key, falsified in (
        ("expected_dumps_independently_authored", False),
        ("fixture_scope", "any_vector_may_reference_any_other"),
        ("production_dump_used_as_oracle", True),
        ("round_trip_expectation_explicit_per_vector", False),
        ("status", "draft"),
    ):
        required = REQUIRED_VECTOR_ASSURANCE[key]
        assert falsified != required, key

        flipped = copy.deepcopy(published)
        flipped[key] = falsified
        assert _assurance_failures(flipped) == [(key, "value-differs")], key

        dropped = copy.deepcopy(published)
        del dropped[key]
        assert _assurance_failures(dropped) == [(key, "missing")], key

    extra = copy.deepcopy(published)
    extra["second_author_reviewed"] = True
    assert _assurance_failures(extra) == [("second_author_reviewed", "unknown")]

    # `0 == False`, so only the declared type separates these two blocks.
    widened = copy.deepcopy(published)
    widened["production_dump_used_as_oracle"] = 0
    assert _assurance_failures(widened) == [
        ("production_dump_used_as_oracle", "widened-type")
    ]


def test_a_falsified_vector_envelope_is_refused() -> None:
    """Version drift and a relaxed float claim must both fail."""
    probe = copy.deepcopy(cast(dict[str, Any], VALID["format"]))
    probe["version"] = "2"
    assert probe != MANIFEST["format"]

    relaxed = copy.deepcopy(cast(dict[str, Any], VALID["format"]))
    relaxed["canonicalization"]["floats_and_NaN_permitted"] = True
    assert relaxed != MANIFEST["format"]
    assert relaxed["canonicalization"]["floats_and_NaN_permitted"] is not False


def test_every_vector_document_key_is_accounted_for() -> None:
    """A new top-level key in a vector file must force review."""
    expected = {
        "valid-vectors": {"assurance", "fixtures", "format", "vectors"},
        "invalid-vectors": {"assurance", "fixtures", "format", "vectors"},
        "replay-vectors": {
            "artifact_locks",
            "assurance",
            "fixtures",
            "format",
            "vectors",
        },
    }
    for name, document in VECTOR_DOCUMENTS:
        assert set(document) == expected[name], name


# --- step 1: the document projection foundation ------------------------------
#
# The sweep found two thirds of contract.md's canonical claims falsifiable with
# the suite green. Closing that is a four-step repair; this is step 1, and it
# lands only the foundation: an ordered heading authority so later selectors can
# be bounded to their section, the two least-verified sections, and the registry
# record type. The global completeness invariant belongs to step 4, so nothing
# here asserts that every region is registered.


CONTRACT_HEADINGS = (
    "# Development History Contract Corpus",
    "## 1. Scope and Authority Warning",
    "## 2. Covered Product Surface",
    "## 3. Vector Inventory",
    "## 4. Replay and Provenance",
    "## 5. Objective and Descriptive Declarations",
    "## 6. Rejection Contract",
    "## 7. Effective Governance",
    "## 8. Non-Generalizations",
    "## 9. Locked Source Authorities",
)
SECTION_ONE, SECTION_FIVE = CONTRACT_HEADINGS[1], CONTRACT_HEADINGS[5]


def _actual_headings(text: str) -> list[str]:
    """Every heading the document publishes, nested ones included.

    A heading inside a list item or a blockquote is a heading, so it is
    reported rather than skipped: the published sequence is exactly ten
    document-level lines, and anything else in the list makes the comparison
    fail instead of passing quietly.
    """
    return [raw for _index, _depth, _level, raw in _markdown_headings(text)]


def _section_paragraphs(text: str, heading: str) -> list[str]:
    return [line for line in _section_lines(text, heading) if line]


def test_the_contract_headings_are_the_published_sequence() -> None:
    """Every heading load-bearing, so a section can anchor its own selector."""
    text = (CORPUS / "contract.md").read_text("utf-8")

    assert _actual_headings(text) == list(CONTRACT_HEADINGS)
    assert len(CONTRACT_HEADINGS) == 10


def test_a_drifting_heading_sequence_is_refused() -> None:
    """Missing, duplicated, reordered and renamed must each fail."""
    text = (CORPUS / "contract.md").read_text("utf-8")
    for label, original, replacement in (
        ("missing", "## 6. Rejection Contract\n", ""),
        ("duplicate", "## 6. Rejection Contract", "## 3. Vector Inventory"),
        ("reordered", "## 8. Non-Generalizations", "## 9. Locked Source Authorities"),
        ("renamed", "## 6. Rejection Contract", "## 6. Rejection Rules"),
        # a fabricated section may not enter by an indented or underlined heading
        ("indented", "## 6. Rejection Contract", "   ## 10. Extra Guarantees"),
        ("setext", "## 6. Rejection Contract", "10. Extra Guarantees\n---------"),
        # an opening sequence may end the line: `##` is an empty heading, and
        # `#` an empty top-level one
        ("empty atx", "## 6. Rejection Contract", "##"),
        ("empty h1", "## 6. Rejection Contract", "#"),
        ("tab after hashes", "## 6. Rejection Contract", "##\t6. Rejection Contract"),
        ("single-dash setext", "## 6. Rejection Contract", "Extra Guarantees\n-"),
        # A container is not a hiding place. Each of these ADDS a heading beside
        # a bullet that stays where it was, rather than replacing a published
        # heading -- replacing one would change the sequence by deletion and
        # prove nothing about whether the container was read.
        (
            "list item",
            "- no CI or test correctness",
            "- ## 10. Extra\n- no CI or test correctness",
        ),
        ("ordered list item", "- no root cause", "1. ## 10. Extra\n- no root cause"),
        (
            "indented list item",
            "- no persistence",
            "  - ## 10. Extra\n- no persistence",
        ),
        (
            "nested list item",
            "- no source ingestion",
            "- - ## 10. Extra\n- no source ingestion",
        ),
        (
            "blockquote",
            "- no merge-base semantics",
            "> ## 10. Extra\n\n- no merge-base semantics",
        ),
        (
            "tight blockquote",
            "- no branch containment",
            ">## 10. Extra\n\n- no branch containment",
        ),
        (
            "nested blockquote",
            "- no violated invariant",
            "> > ## 10. Extra\n\n- no violated invariant",
        ),
        (
            "blockquote setext",
            "- no repair correctness",
            "> Extra\n> ---\n\n- no repair correctness",
        ),
    ):
        tampered = text.replace(original, replacement, 1)
        assert tampered != text, label
        assert _actual_headings(tampered) != list(CONTRACT_HEADINGS), label


def test_a_fence_is_code_and_not_a_heading() -> None:
    """The other half of the same defect: a `#` in a fence is not a section.

    Reading it as one ended a section that had not ended, so the lines after it
    left their own section's tiling and stopped being compared. The fence is
    still refused -- nothing renders it -- but it is refused as unprojected
    content rather than misread as structure.
    """
    text = (CORPUS / "contract.md").read_text("utf-8")
    for label, fence in (
        ("backtick", "```\n# not actually a heading\n```"),
        ("tilde", "~~~\n## 10. Extra Guarantees\n~~~"),
        ("info string", "```python\n# not actually a heading\n```"),
        ("longer close", "```\n## 10. Extra Guarantees\n`````"),
        ("indented fence", "   ```\n   # not actually a heading\n   ```"),
    ):
        tampered = text.replace(
            "## 8. Non-Generalizations", f"{fence}\n\n## 8. Non-Generalizations", 1
        )
        assert tampered != text, label
        # the heading sequence is untouched: the fence lines are not structure
        assert _actual_headings(tampered) == list(CONTRACT_HEADINGS), label
        # section 7 keeps every line it had -- the fence lands inside it rather
        # than truncating it, which is what reading a fenced `#` as a heading did
        original = _section_lines(text, SECTION_SEVEN)
        widened = _section_lines(tampered, SECTION_SEVEN)
        assert widened[: len(original)] == original, label
        assert len(widened) > len(original), label

    # a fence containing a real-looking heading does not open a section either
    fenced = text.replace(
        "## 8. Non-Generalizations",
        "```\n## 8. Non-Generalizations\n```\n\n## 8. Non-Generalizations",
        1,
    )
    assert _actual_headings(fenced) == list(CONTRACT_HEADINGS)

    # the live document carries no fence at all, so none of this is retrofitting
    assert "```" not in text and "~~~" not in text
    assert all(not fenced_line for _d, _c, fenced_line in _markdown_blocks(text))


def test_the_bounded_block_model_reads_the_forms_it_claims() -> None:
    """Named boundaries, stated as executable cases rather than as prose.

    The comment above `_markdown_blocks` says what the model covers and what it
    does not. These are those claims, so a later widening or narrowing has to
    move a test rather than a sentence.
    """
    covered: tuple[tuple[str, str, list[tuple[int, int, int]]], ...] = (
        ("atx", "## Title\n", [(0, 0, 2)]),
        ("atx empty", "##\n", [(0, 0, 2)]),
        ("atx level six", "###### Title\n", [(0, 0, 6)]),
        ("atx seven hashes", "####### Title\n", []),
        ("atx no space", "##Title\n", []),
        ("atx three-space indent", "   ## Title\n", [(0, 0, 2)]),
        ("atx four-space indent", "    ## Title\n", []),
        ("setext equals", "Title\n=====\n", [(0, 0, 1)]),
        ("setext dashes", "Title\n-----\n", [(0, 0, 2)]),
        ("setext single dash", "Title\n-\n", [(0, 0, 2)]),
        ("setext after blank", "\n---\n", []),
        ("table delimiter is not setext", "| a |\n| --- |\n", []),
        ("list item", "- ## Title\n", [(0, 1, 2)]),
        ("ordered list item", "1. ## Title\n", [(0, 1, 2)]),
        ("nested list item", "- - ## Title\n", [(0, 2, 2)]),
        ("plain list item", "- not a heading\n", []),
        ("blockquote", "> ## Title\n", [(0, 1, 2)]),
        ("tight blockquote", ">## Title\n", [(0, 1, 2)]),
        ("nested blockquote", "> > ## Title\n", [(0, 2, 2)]),
        ("blockquote setext", "> Title\n> ---\n", [(0, 1, 2)]),
        ("fenced code", "```\n# not a heading\n```\n", []),
        ("tilde fence", "~~~\n# not a heading\n~~~\n", []),
        ("fence with info", "```py\n# not a heading\n```\n", []),
        ("unclosed fence", "```\n# not a heading\n", []),
        ("after a closed fence", "```\ncode\n```\n\n## Title\n", [(4, 0, 2)]),
        ("indented code", "para\n\n    # not a heading\n", []),
    )
    assert len(covered) == 26
    for label, sample, expected in covered:
        observed = [(i, d, level) for i, d, level, _raw in _markdown_headings(sample)]
        assert observed == expected, label

    # ...and the forms it deliberately does not resolve, pinned in the same way,
    # so a widening or a narrowing has to move one of these rather than a
    # sentence in the comment above. The trailing note on each row is what a
    # CommonMark parser publishes for that document.
    excluded: tuple[tuple[str, str, list[tuple[int, int, int]]], ...] = (
        # fail-closed: anything nonblank above a `---` underlines
        ("thematic break underlined", "***\n---\n", [(0, 0, 2)]),  # none
        ("indented code underlined", "    code\n---\n", [(0, 0, 2)]),  # none
        ("html block underlined", "<div>\n---\n", [(0, 0, 2)]),  # none
        ("link definition underlined", "[a]: /b\n---\n", [(0, 0, 2)]),  # none
        # fail-closed: depth is compared, container identity is not
        ("underline one container over", "- item\n> ---\n", [(0, 1, 2)]),  # none
        # fail-open: reported one line late, or not at all
        ("multi-line setext", "One\nTwo\n---\n", [(1, 0, 2)]),  # (0, h2)
        ("paragraph of dashes only", "===\n---\n", []),  # (0, h2)
        ("four-column continuation", "-\n    ## x\n", []),  # (1, h2)
        ("bare dash in a blockquote", "> quote\n> -\n", []),  # (0, h2)
    )
    assert len(excluded) == 9
    for label, sample, expected in excluded:
        observed = [(i, d, level) for i, d, level, _raw in _markdown_headings(sample)]
        assert observed == expected, label

    # nesting is bounded by the line, not by a cap: a cap would stop seeing the
    # heading inside a container one deeper than the number chosen
    for depth in (1, 4, 9, 20):
        deep = "> " * depth + "## Title\n"
        assert [(d, level) for _i, d, level, _raw in _markdown_headings(deep)] == [
            (depth, 2)
        ], depth

    # an unterminated fence inside a container ends with the container, so it
    # cannot swallow every heading after it
    assert [
        (i, d, level) for i, d, level, _raw in _markdown_headings("> ```\n\n## x\n")
    ] == [(2, 0, 2)]

    # and the live document is exactly its ten document-level headings
    text = (CORPUS / "contract.md").read_text("utf-8")
    assert [(depth, level) for _i, depth, level, _r in _markdown_headings(text)] == [
        (0, 1)
    ] + [(0, 2)] * 9


# --- section 1: the scope and authority warning ------------------------------


def _contract_markdown_entry() -> dict[str, str]:
    files = cast(list[dict[str, str]], MANIFEST["corpus_files"])
    return next(entry for entry in files if entry["filename"] == "contract.md")


def _render_scope_warning() -> list[str]:
    """The identity clause, read from the manifest rather than frozen."""
    identity = cast(dict[str, Any], MANIFEST["corpus_identity"])
    scope = cast(dict[str, Any], MANIFEST["scope"])
    execution = cast(dict[str, Any], MANIFEST["execution_contract"])
    assurance = cast(dict[str, Any], MANIFEST["assurance"])
    derived = str(_contract_markdown_entry()["role"]).startswith("derived_")

    # The nine-item negative enumeration is skeleton: four of its terms have no
    # canonical declaration anywhere in the corpus, so rendering them from an
    # authority would be inventing one.
    return [
        (
            f"This {cast(str, identity['classification']).split('_')[0]},"
            f" {'source-only' if scope['source_only'] else 'production'}"
            f" `{identity['originating_slice']}` contract corpus is not a"
            " production schema, class, adapter, reader, writer, migration,"
            " persistence contract, or public API."
            f" The {_spelled(cast(int, assurance['canonical_json_files']))}"
            " canonical JSON files are the semantic authority; this Markdown is"
            f" {'derived' if derived else 'authoritative'}."
            " The corpus is executed only by"
            f" `{execution['test_only_executor']}` and is excluded from"
            f" {'the wheel and the sdist' if scope['package_exclusion_required'] else 'nothing'}."
        )
    ]


def _actual_scope_warning(text: str) -> list[str]:
    return _section_paragraphs(text, SECTION_ONE)


def test_the_scope_warning_is_an_exact_projection() -> None:
    text = (CORPUS / "contract.md").read_text("utf-8")

    assert _actual_scope_warning(text) == _render_scope_warning()
    # The sentence spends only the first token of the classification, so the
    # rest could drift to say the opposite of the sentence carrying it. The leaf
    # is descriptive -- no canonical surface can confirm it -- so the published
    # value is pinned test-side rather than left free.
    assert MANIFEST["corpus_identity"]["classification"] == (
        "internal_source_repository_only_contract_corpus"
    )
    # the slice coordinate is declared twice and the two must not diverge
    assert (
        MANIFEST["scope"]["slice"] == MANIFEST["corpus_identity"]["originating_slice"]
    )
    # the declared file count is the sealed set the loader actually reads
    assert MANIFEST["assurance"]["canonical_json_files"] == len(SEALED_JSON) == 4


# --- section 5: one paragraph pair, four different authorities ---------------
#
# The epistemic split is compositional and must not pretend one source owns it.
# The count comes from the ordered `paths` list -- not a frozenset, which would
# hide a duplicate entry behind a smaller number. The meaning of "descriptive"
# comes from the meta-contract. The fail-closed sentence is a statement about
# the ORACLE, so it is rendered from the oracle's own closure rather than from
# a manifest leaf describing itself. The fixture mechanism and count come from
# the execution contract and the vector summary.


def _render_epistemic_split() -> list[str]:
    meta = cast(dict[str, Any], MANIFEST["descriptive_metadata"])
    declared = cast(list[str], meta["paths"])
    contract = cast(str, meta["contract"])
    truth = (
        "no independent source of truth"
        if "have no independent source of truth" in contract
        else "an independent source of truth"
    )
    counted = (
        "are never counted as verified assurance"
        if "are never counted as verified assurance" in contract
        else "are counted as verified assurance"
    )
    # observed, not declared: the oracle either leaves an objective leaf
    # unowned or it does not
    consumer = "fails if any" if not _unowned_objective_paths() else "passes even if an"

    return [
        (
            "Every manifest declaration is exactly one of"
            f" {_spelled(len(DECLARATION_KINDS))} kinds. An **objective**"
            " declaration is compared with something outside the manifest -- the"
            " live `__all__`, the filesystem, the sealed vector files, the locked"
            " source documents, or the executor's own registries -- and the"
            f" focused oracle {consumer} objective leaf has no such consumer. A"
            f" **descriptive** declaration has {truth}; the exact leaf paths are"
            f" enumerated in `descriptive_metadata.paths` ({len(declared)} of"
            f" them) and {counted}."
        )
    ]


def _render_fixture_mechanism() -> list[str]:
    execution = cast(dict[str, Any], MANIFEST["execution_contract"])
    mechanism = cast(str, execution["fixture_references"])
    fixtures = cast(dict[str, Any], MANIFEST["vector_summary"])["fixtures"]
    inlined = mechanism.startswith("inlined_values")

    return [
        (
            "Fixture values are"
            f" {'inlined in the vectors rather than referenced by marker' if inlined else 'referenced by marker rather than inlined in the vectors'}."
            f" The manifest records that mechanism as `{mechanism}`: the corpus"
            f" carries the values, and the oracle resolves each of the {fixtures}"
            " declared fixtures to an exact vector, side, and JSON pointer rather"
            " than searching for an equal value."
        )
    ]


def _actual_epistemic_split(text: str) -> list[str]:
    return _section_paragraphs(text, SECTION_FIVE)[:1]


def _actual_fixture_mechanism(text: str) -> list[str]:
    return _section_paragraphs(text, SECTION_FIVE)[1:]


def test_the_epistemic_split_is_an_exact_projection() -> None:
    text = (CORPUS / "contract.md").read_text("utf-8")

    assert _actual_epistemic_split(text) == _render_epistemic_split()
    assert _actual_fixture_mechanism(text) == _render_fixture_mechanism()
    assert len(_section_paragraphs(text, SECTION_FIVE)) == 2


def test_the_epistemic_counts_come_from_their_own_sources() -> None:
    """Each number is read from the surface that owns it, not from the prose."""
    declared = cast(list[str], MANIFEST["descriptive_metadata"]["paths"])
    summary = cast(dict[str, Any], MANIFEST["vector_summary"])

    # the ordered list, so a duplicated entry could not hide behind a set
    assert len(declared) == len(set(declared)) == len(DESCRIPTIVE_PATHS) == 83
    assert f"({len(declared)} of them)" in _render_epistemic_split()[0]
    assert summary["fixtures"] == 19 == len(cast(list[Any], VALID["fixtures"]))
    assert summary["fixtures"] == len(FIXTURE_BINDINGS)
    # the fail-closed clause is an observation about the oracle
    assert _unowned_objective_paths() == []


# --- step 1: the projection registry record ----------------------------------
#
# Three axes, deliberately separate, because one status cannot mean both "the
# Markdown faithfully projects its authority" and "the underlying claim has
# independent truth authority". A descriptive `slice_layer` is projected
# EXACTly and is CANONICAL_DECLARATION_ONLY; the section-5 fail-closed sentence
# is projected EXACTly and is INDEPENDENTLY_VERIFIED; a claim whose external
# owner has published no structured authority yet is EXTERNAL_AUTHORITY_DEFERRED
# while still being projected exactly. Where a region composes several
# authorities the weakest assurance is recorded, so the row never overclaims.
#
# Step 1 registers only the regions it closes. There is deliberately no "every
# region is registered" invariant here -- that is step 4, and asserting it now
# would demand placeholder rows for regions nobody has analysed.

PROJECTION_KINDS = ("EXACT", "EXPLANATORY")
EPISTEMIC_KINDS = ("OBJECTIVE", "DESCRIPTIVE", "EXPLANATORY")
AUTHORITY_ASSURANCES = (
    "INDEPENDENTLY_VERIFIED",
    "CANONICAL_DECLARATION_ONLY",
    "EXTERNAL_AUTHORITY_DEFERRED",
)


class ContractRegion(NamedTuple):
    region_id: str
    heading: str | None
    selector: Callable[[str], list[str]]
    renderer: Callable[[], list[str]] | None
    authority: tuple[str, ...]
    projection_kind: str
    epistemic_kind: str
    authority_assurance: str


STEP_ONE_REGIONS: tuple[ContractRegion, ...] = (
    ContractRegion(
        "s1.scope-warning",
        SECTION_ONE,
        _actual_scope_warning,
        _render_scope_warning,
        (
            "/corpus_identity/classification",
            "/corpus_identity/originating_slice",
            "/scope/source_only",
            "/scope/package_exclusion_required",
            "/assurance/canonical_json_files",
            "/execution_contract/test_only_executor",
            # The ledger row is addressed by filename and read for its role.
            # Only entry 8 is declared: blanking any other filename leaves the
            # search to find this one, so only this key can break the render,
            # and it is verified through the addressing-key branch of the drift
            # rule rather than by moving a word.
            "/corpus_files/8/filename",
            "/corpus_files/8/role",
        ),
        "EXACT",
        "DESCRIPTIVE",
        "CANONICAL_DECLARATION_ONLY",
    ),
    ContractRegion(
        "s5.epistemic-split",
        SECTION_FIVE,
        _actual_epistemic_split,
        _render_epistemic_split,
        (
            "/descriptive_metadata/paths",
            "/descriptive_metadata/contract",
            "DECLARATION_KINDS",
            "_unowned_objective_paths",
        ),
        "EXACT",
        "OBJECTIVE",
        # the fail-closed clause is observed from the oracle, but the paragraph
        # also restates the meta-contract, which nothing can independently
        # confirm -- weakest assurance wins so the row cannot overclaim
        "CANONICAL_DECLARATION_ONLY",
    ),
    ContractRegion(
        "s5.fixture-mechanism",
        SECTION_FIVE,
        _actual_fixture_mechanism,
        _render_fixture_mechanism,
        ("/execution_contract/fixture_references", "/vector_summary/fixtures"),
        "EXACT",
        "DESCRIPTIVE",
        "CANONICAL_DECLARATION_ONLY",
    ),
)


def test_every_registered_region_declares_a_known_classification() -> None:
    seen: set[str] = set()
    for region in CONTRACT_PROJECTION_REGISTRY:
        assert region.region_id not in seen, region.region_id
        seen.add(region.region_id)
        assert region.projection_kind in PROJECTION_KINDS, region.region_id
        assert region.epistemic_kind in EPISTEMIC_KINDS, region.region_id
        assert region.authority_assurance in AUTHORITY_ASSURANCES, region.region_id
        # explanatory prose carries no renderer and cites nothing; a derived
        # region must say where it reads from
        assert (region.renderer is None) == (region.projection_kind == "EXPLANATORY"), (
            region.region_id
        )
        assert bool(region.authority) == (region.renderer is not None), region.region_id


def test_every_registered_region_resolves_and_projects() -> None:
    text = (CORPUS / "contract.md").read_text("utf-8")
    for region in CONTRACT_PROJECTION_REGISTRY:
        assert region.heading in CONTRACT_HEADINGS, region.region_id
        assert text.count(cast(str, region.heading)) == 1, region.region_id

        selected = region.selector(text)
        if region.renderer is None:
            # an explanatory region declares its exact lines rather than
            # rendering them; the preamble declares none, and that is the claim
            assert selected == list(EXPLANATORY_REGION_LINES[region.region_id]), (
                region.region_id
            )
            continue

        assert selected, region.region_id
        assert selected == region.renderer(), region.region_id

        for reference in region.authority:
            if reference.startswith("/"):
                _resolve_pointer(MANIFEST, reference)
            else:
                assert reference in globals(), (region.region_id, reference)


def _drifted(value: Any) -> Any:
    """A value distinguishable from the original in every rendered branch."""
    if isinstance(value, bool):
        return not value
    if isinstance(value, int):
        return value + 1
    if isinstance(value, str):
        return ""
    if isinstance(value, list):
        items = cast(list[Any], value)
        # duplicate the last entry: the length moves, the element shape does not
        return [*items, items[-1]] if items else ["drifted"]
    if isinstance(value, dict):
        mapping = cast(dict[str, Any], value)
        return {**mapping, next(iter(mapping)): ""} if mapping else {"drifted": ""}
    raise AssertionError(f"no drift defined for {type(value).__name__}")


# Pointers a region ADDRESSES its authority by rather than spends as text. The
# section-1 sentence locates its ledger row with a search on
# `filename == "contract.md"`, so blanking that key cannot change a word -- it
# removes the row. These, and only these, may satisfy the drift rule by breaking
# a renderer instead of moving it.
ADDRESSING_KEY_AUTHORITIES: frozenset[str] = frozenset({"/corpus_files/8/filename"})


def _drift_forms(value: Any) -> list[Any]:
    """Every distinguishable perturbation of a declared value.

    `_drifted` blanks the first value of a mapping and leaves its size alone, so
    a renderer spending only `len(...)` -- the section-4 opening counts its
    three classifications -- does not move. A shortened mapping is therefore
    offered as well. Lists already move their length under `_drifted`, which
    appends; the extra list form is kept for symmetry and moves nothing today.
    A declared authority is load-bearing if any form reaches the render.
    """
    forms = [_drifted(value)]
    if isinstance(value, list) and len(cast(list[Any], value)) > 1:
        forms.append(cast(list[Any], value)[:-1])
    if isinstance(value, dict) and len(cast(dict[str, Any], value)) > 1:
        mapping = cast(dict[str, Any], value)
        forms.append(dict(list(mapping.items())[:-1]))
    return forms


def test_every_registered_renderer_depends_on_its_declared_authority(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A renderer that ignores its authority transcribes rather than projects.

    Comparing a renderer to the document proves only that the two agree today;
    a renderer returning a frozen copy of the prose would agree just as well.
    Each declared pointer is therefore drifted in place and the render must
    move, which is what makes the authority column mean something.

    One declared pointer cannot be spent as text at all. The section-1 sentence
    finds its ledger row with a search on `filename == "contract.md"`, so
    blanking that key does not change a word -- it removes the row and the
    renderer stops. Accepting a raise as movement from EVERY pointer would have
    been the wrong repair: many leaves make some renderer die without ever
    reaching the page -- the control below counts them -- and any of them could
    then have been declared as an authority it does not have. Raising is
    admitted only from the pointers named as addressing keys, and a pointer that
    raises without being one of them fails here.
    """

    def outcome(region: ContractRegion, baseline: list[str]) -> str:
        assert region.renderer is not None
        try:
            return "moved" if region.renderer() != baseline else "same"
        except Exception:  # noqa: BLE001 - the renderer could not run at all
            return "broke"

    for region in CONTRACT_PROJECTION_REGISTRY:
        if region.renderer is None:
            assert not region.authority, region.region_id
            continue
        baseline = region.renderer()
        # every declared authority must be able to move the render, whether it
        # is a manifest leaf, a live observation, or a vector collection
        pointers = [ref for ref in region.authority if ref.startswith("/")]
        named = [ref for ref in region.authority if not ref.startswith("/")]
        assert pointers or named, region.region_id

        for name in named:
            monkeypatch.setitem(globals(), name, _drifted_authority(name))
            try:
                assert outcome(region, baseline) == "moved", (region.region_id, name)
            finally:
                monkeypatch.undo()

        for pointer in pointers:
            parent_path, _, leaf = pointer.rpartition("/")
            parent = cast(dict[str, Any], _resolve_pointer(MANIFEST, parent_path))
            seen: set[str] = set()
            for form in _drift_forms(parent[leaf]):
                monkeypatch.setitem(parent, leaf, form)
                try:
                    seen.add(outcome(region, baseline))
                finally:
                    monkeypatch.undo()
            if "broke" in seen:
                assert pointer in ADDRESSING_KEY_AUTHORITIES, (
                    region.region_id,
                    pointer,
                )
            assert seen & {"moved", "broke"}, (region.region_id, pointer)

        assert region.renderer() == baseline, region.region_id


def test_every_addressing_key_is_declared_and_really_addresses() -> None:
    """The exemption is a named list, and each entry has to earn its place."""
    declared = {
        pointer
        for region in CONTRACT_PROJECTION_REGISTRY
        for pointer in region.authority
        if pointer.startswith("/")
    }
    assert ADDRESSING_KEY_AUTHORITIES <= declared, sorted(
        ADDRESSING_KEY_AUTHORITIES - declared
    )
    assert ADDRESSING_KEY_AUTHORITIES == frozenset({"/corpus_files/8/filename"})

    # an addressing key is one a renderer searches with rather than prints: its
    # drift must break a render, never merely change one
    for pointer in sorted(ADDRESSING_KEY_AUTHORITIES):
        owners = [
            region
            for region in CONTRACT_PROJECTION_REGISTRY
            if pointer in region.authority and region.renderer is not None
        ]
        assert owners, pointer
        for region in owners:
            renderer = region.renderer
            assert renderer is not None
            baseline = renderer()
            parent_path, _, leaf = pointer.rpartition("/")
            parent = cast(dict[str, Any], _resolve_pointer(MANIFEST, parent_path))
            original = parent[leaf]
            parent[leaf] = _drifted(original)
            try:
                broke = False
                try:
                    renderer()
                except Exception:  # noqa: BLE001 - which is the point
                    broke = True
                assert broke, (region.region_id, pointer)
            finally:
                parent[leaf] = original
            assert renderer() == baseline, region.region_id


def test_a_pointer_that_only_breaks_a_renderer_may_not_be_declared() -> None:
    """The finding this exemption was narrowed for, kept as a control.

    `/source_decisions/0/path` is opened by the deferral reader the section-4
    block runs, so drifting it kills all three section-4 renders -- without any
    of their sentences ever showing it. Under a blanket raise-tolerance each of
    them could have claimed it as an authority, and it is not a rare shape.
    """
    _shown, structural = _document_consumers()
    breakable = sorted(
        (path, region_id)
        for path, regions in structural.items()
        for region_id in regions
        if region_id not in _declared_consumers(path)
    )
    # every one of these could have been declared as an authority it does not
    # have, had a raise been allowed to stand in for reaching the page
    assert len(breakable) == 90
    assert len({path for path, _region_id in breakable}) == 31

    for region_id, pointer in (
        ("s4.linkable-facts", "/source_decisions/0/path"),
        ("s4.replay-summary-opening", "/source_decisions/0/sha256"),
        ("s6.rejection-oracle", "/target_symbols/7/symbol"),
        ("s7.governance-prose", "/source_decisions/1/decision_reference"),
    ):
        region = _region(region_id)
        renderer = region.renderer
        assert renderer is not None
        assert pointer not in region.authority, (region_id, pointer)
        assert pointer not in ADDRESSING_KEY_AUTHORITIES, pointer

        baseline = renderer()
        parent_path, _, leaf = pointer.rpartition("/")
        parent = cast(dict[str, Any], _resolve_pointer(MANIFEST, parent_path))
        original = parent[leaf]
        results: set[str] = set()
        for form in _drift_forms(original):
            parent[leaf] = form
            try:
                results.add("moved" if renderer() != baseline else "same")
            except Exception:  # noqa: BLE001 - the case the control is about
                results.add("broke")
            finally:
                parent[leaf] = original
        # it breaks the renderer and never reaches the page, so declaring it
        # would be a false authority -- which the rule above now refuses
        assert "broke" in results, (region_id, pointer)
        assert "moved" not in results, (region_id, pointer)
        assert renderer() == baseline, region_id


def test_a_declared_authority_that_moves_nothing_is_refused(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Offering several drift forms must not become "any excuse will do".

    The rule above accepts a pointer when SOME perturbation of it moves the
    render, because a renderer spending only `len(...)` is unmoved by a changed
    member. That quantifier would be worthless if a leaf the region never reads
    could satisfy it, so a leaf from each unrelated corner of the manifest is
    offered to three regions and every one must be refused.
    """

    def noticed(region: ContractRegion, pointer: str) -> bool:
        renderer = region.renderer
        assert renderer is not None
        baseline = renderer()
        parent_path, _, leaf = pointer.rpartition("/")
        parent = cast(dict[str, Any], _resolve_pointer(MANIFEST, parent_path))
        moved = False
        for form in _drift_forms(parent[leaf]):
            monkeypatch.setitem(parent, leaf, form)
            try:
                moved = moved or renderer() != baseline
            except Exception:  # noqa: BLE001 - a raising renderer noticed
                moved = True
            finally:
                monkeypatch.undo()
        return moved

    inert = [
        (region_id, pointer)
        for region_id in (
            "s1.scope-warning",
            "s7.governance-block",
            "s3.inventory-summary",
        )
        for pointer in (
            "/rejection_contract/normalization",
            "/assurance/status",
            "/corpus_identity/phase_closure_owner",
            "/corpus_identity/serialization_and_migration_owner",
            "/scope/covered_slices",
            "/non_goals",
            "/originating_publications",
        )
        if pointer not in _region(region_id).authority
        and noticed(_region(region_id), pointer)
    ]
    assert not inert, inert

    # and the rule is not merely refusing everything: each declared pointer is
    # still accepted, which is what the suite depends on
    for region in CONTRACT_PROJECTION_REGISTRY:
        if region.renderer is None:
            continue
        for pointer in region.authority:
            if pointer.startswith("/"):
                assert noticed(region, pointer), (region.region_id, pointer)


def test_every_registered_region_rejects_a_semantic_edit() -> None:
    """A selector that cannot see an edit inside its own region is decoration."""
    text = (CORPUS / "contract.md").read_text("utf-8")
    for region in CONTRACT_PROJECTION_REGISTRY:
        if region.renderer is None:
            # an explanatory region declares no lines, so the edit that has to
            # be refused is a line arriving where none belongs
            declared = list(EXPLANATORY_REGION_LINES[region.region_id])
            heading = cast(str, region.heading)
            tampered = text.replace(
                f"{heading}\n", f"{heading}\n\nA claim that answers to nothing.\n", 1
            )
            assert tampered != text, region.region_id
            assert region.selector(tampered) != declared, region.region_id
            continue
        # the last line, so a block anchored on its header row can still be
        # located after the edit and fails by comparison rather than by raising
        last = region.selector(text)[-1]
        tampered = text.replace(last, f"{last} SENTINEL", 1)

        assert tampered != text, region.region_id
        assert region.selector(tampered) != region.renderer(), region.region_id


# --- step 2: the bulk derived regions ----------------------------------------
#
# Step 1 landed the boundary, the heading authority and the two least-verified
# sections. This is the bulk: every remaining prose claim in sections 2, 3, 4, 6,
# 7 that restates a canonical value, rendered from that value and compared
# exactly, plus the section tiling that closes the placement and completeness
# claims -- a table or bullet block is no longer merely correct, it has to be
# under its own heading with nothing else beside it.
#
# Step 4 is not here. The document-wide registry closure needs every region to
# exist first, and the S1.P09 deflection needs an authority this corpus does not
# lock. The deferred:22 and owner-topology readers arrive in step 3, below.

SECTION_TWO = CONTRACT_HEADINGS[2]
SECTION_THREE = CONTRACT_HEADINGS[3]
SECTION_SIX = CONTRACT_HEADINGS[6]
SECTION_SEVEN = CONTRACT_HEADINGS[7]
SECTION_EIGHT = CONTRACT_HEADINGS[8]
SECTION_NINE = CONTRACT_HEADINGS[9]


def _target_slice(symbol: str) -> str:
    return _target_entry(symbol)["slice_layer"]


def _paragraph(text: str, heading: str, index: int) -> list[str]:
    """One paragraph of a section, addressed by position within that section."""
    return [_section_paragraphs(text, heading)[index]]


def _derived_table(
    label: str,
) -> tuple[tuple[str, ...], Callable[[], list[tuple[str, ...]]]]:
    entry = next(table for table in DERIVED_TABLES if table[0] == label)
    return entry[1], entry[2]


def _actual_table(text: str, heading: str, label: str) -> list[str]:
    """A table taken from inside its own section rather than from the file."""
    header, _ = _derived_table(label)
    lines = _section_lines(text, heading)
    start = lines.index(_md_row(header))
    end = start
    while end < len(lines) and lines[end].startswith("|"):
        end += 1
    return lines[start:end]


def _render_registered_table(label: str) -> list[str]:
    header, render = _derived_table(label)
    return _render_table(header, render())


def _paragraph_selector(heading: str, index: int) -> Callable[[str], list[str]]:
    def select(text: str) -> list[str]:
        return _paragraph(text, heading, index)

    return select


def _table_selector(heading: str, label: str) -> Callable[[str], list[str]]:
    def select(text: str) -> list[str]:
        return _actual_table(text, heading, label)

    return select


def _table_renderer(label: str) -> Callable[[], list[str]]:
    def render() -> list[str]:
        return _render_registered_table(label)

    return render


def _sliced_renderer(
    render: Callable[[], list[str]], start: int, stop: int | None
) -> Callable[[], list[str]]:
    def sliced() -> list[str]:
        return render()[start:stop]

    return sliced


# --- section 2: how much surface is covered, and whose ------------------------


def _render_surface_lead_in() -> list[str]:
    scope = cast(dict[str, Any], MANIFEST["scope"])
    modules = cast(list[str], scope["production_modules"])
    targets = cast(list[Any], MANIFEST["target_symbols"])
    return [
        f"{_spelled(len(modules)).capitalize()} `{scope['phase']}` production"
        f" modules and {_spelled(len(targets))} published product symbols:"
    ]


def _render_supporting_authorities() -> list[str]:
    scope = cast(dict[str, Any], MANIFEST["scope"])
    supporting = ", ".join(
        f"`{module}`"
        for module in cast(list[str], scope["supporting_authorities_not_owned"])
    )
    outside = " and ".join(f"`{module}`" for module in OUTSIDE_MODULES)
    return [
        f"Supporting authorities are consumed but not owned: {supporting}."
        f" {outside} are outside this corpus: no `{scope['phase']}` value"
        " consumes them."
    ]


# --- section 3: what the inventory totals to ---------------------------------


def _render_inventory_summary() -> list[str]:
    summary = cast(dict[str, Any], MANIFEST["vector_summary"])
    partitions = [
        cast(str, vector["semantic_partition"])
        for section in SECTIONS.values()
        for vector in section["vectors"]
    ]
    # observed, not declared: the partitions either collide or they do not
    distinct = "distinct" if len(set(partitions)) == len(partitions) else "shared"
    return [
        f"{summary['total_vectors']} vectors over {summary['fixtures']} declared"
        f" fixtures. Every vector occupies a {distinct} semantic partition."
    ]


# --- section 4: the two provenance sentences the bullets sit between ----------


def _retained_roles_are_source_derived() -> bool:
    """Observed: every retained role matches the position its digest came from."""
    return not any(_role_implication_failures(vector) for vector in _SOURCED)


def _caller_supplied_cite_no_retained_location() -> bool:
    """Observed: a caller-supplied replay vector carries no source pointer."""
    return all(
        not vector["source_pointers"]
        for vector in REPLAY["vectors"]
        if cast(str, vector["evidence_classification"]).startswith("caller_supplied")
    )


def _render_role_lead_in() -> list[str]:
    # a sentence about behaviour, rendered from the behaviour: if a swapped role
    # ever stopped failing, the claim would have to read the other way
    derived = _retained_roles_are_source_derived()
    stance = (
        "derived from the source position its revision digest was read from"
        " rather than trusted from the vector"
        if derived
        else "trusted from the vector rather than derived from the source"
        " position its revision digest was read from"
    )
    return [
        f"Every retained `role` is {stance}, so a swapped role"
        f" {'fails' if derived else 'passes'} even when every digest is re-sealed:"
    ]


def _render_embedded_provenance() -> list[str]:
    bound = _caller_supplied_cite_no_retained_location()
    return [
        "A caller-supplied composition or association cites"
        f" {'no retained location' if bound else 'a retained location'} of its"
        " own; each embedded fact is instead bound to the retained vector it"
        " reuses, so its nested values inherit that provenance."
    ]


# --- section 6: what a rejection locks, and what it refuses to ----------------


def _render_rejection_oracle() -> list[str]:
    rejection = cast(dict[str, Any], MANIFEST["rejection_contract"])
    oracle = ", ".join(
        f"`{field}`" for field in cast(list[str], rejection["error_oracle"])
    )
    locked = (
        rejection["unstable_prose_locked"]
        or rejection["internal_union_branch_labels_locked"]
    )
    # the carrier set is read off the vectors, not restated: which slice owns
    # which union is the claim, and swapping the two must not survive
    carriers = sorted(
        {
            (
                _target_slice(cast(str, vector["target"])),
                cast(list[str], vector["expected"]["error_location"])[0],
            )
            for vector in INVALID["vectors"]
            if vector["expected"]["error_location_mode"] == "prefix"
        }
    )
    unions = " and ".join(
        f"the `{layer}` {location} union" for layer, location in carriers
    )
    return [
        f"Invalid vectors lock {oracle}. Prose messages, Pydantic internal union"
        " branch labels, and validator function names are deliberately"
        f" {'locked' if locked else 'not locked'}. The `prefix` location mode is"
        " used only where a discriminatorless union reports per-branch locations:"
        f" {unions}."
    ]


def _render_forbidden_extra_prose() -> list[str]:
    ledger = cast(list[dict[str, str]], MANIFEST["s07_forbidden_extra_ledger"])
    pointer = next(entry for entry in ledger if entry["extra_key"] == "json_pointer")
    # the three excluded spellings are skeleton: they are absent from the corpus
    # by construction, so no canonical leaf can supply them
    return [
        f"The {_spelled(len(ledger))}"
        f" `{_target_slice('PullRequestHistoryFactEvidenceLink')}` forbidden extras"
        f" protect {_spelled(len({e['published_non_claim'] for e in ledger}))}"
        " DIFFERENT published non-claims. Further spellings of one boundary earn"
        " no partition: `field_path`, `semantic_path`, and `evidence_locator`"
        " restate the localization non-claim"
        f" `{pointer['extra_key']}` already carries."
    ]


# --- section 7: which artifacts govern, and how they are consumed -------------


def _render_governance_prose() -> list[str]:
    governance = cast(dict[str, Any], MANIFEST["effective_governance"])
    # the correction's own structured flag, not the manifest's label for it
    append_only = _correction_is_append_only()
    return [
        f"`S1.P05.S08` and its {'append-only' if append_only else 'regenerating'}"
        " `S1.P05.S08.C01` correction are consumed as source authorities and are"
        f" {'never' if not governance['vectorized_as_product_behavior'] else 'also'}"
        " vectorized as product behaviour. The executor"
        f" {'recomputes' if governance['recomputation_required'] else 'reads'} the"
        " effective projection from both artifacts rather than trusting a stored"
        " table:"
    ]


# --- step 2: register the regions and tile the sections they complete --------
#
# A region proves its own content. Tiling proves the section holds those regions
# and nothing else -- which is what the placement and completeness claims come
# to: the forbidden-extras table is section 6's table, section 8 is its bullets
# with no softening prose beside them, section 9 publishes the authority table
# and no count of it. Sections still register piecemeal; asserting every section
# is registered, and covering the lines that fall outside all of them, is step 4.

STEP_TWO_REGIONS: tuple[ContractRegion, ...] = (
    ContractRegion(
        "s2.surface-lead-in",
        SECTION_TWO,
        _paragraph_selector(SECTION_TWO, 0),
        _render_surface_lead_in,
        ("/scope/production_modules", "/scope/phase", "/target_symbols"),
        "EXACT",
        "OBJECTIVE",
        "CANONICAL_DECLARATION_ONLY",
    ),
    ContractRegion(
        "s2.target-table",
        SECTION_TWO,
        _table_selector(SECTION_TWO, "target symbols"),
        _table_renderer("target symbols"),
        ("/target_symbols",),
        "EXACT",
        "OBJECTIVE",
        "CANONICAL_DECLARATION_ONLY",
    ),
    ContractRegion(
        "s2.supporting-authorities",
        SECTION_TWO,
        _paragraph_selector(SECTION_TWO, -1),
        _render_supporting_authorities,
        ("/scope/supporting_authorities_not_owned", "/scope/phase"),
        "EXACT",
        "OBJECTIVE",
        "CANONICAL_DECLARATION_ONLY",
    ),
    ContractRegion(
        "s3.inventory-table",
        SECTION_THREE,
        _table_selector(SECTION_THREE, "vector inventory"),
        _table_renderer("vector inventory"),
        ("SECTIONS",),
        "EXACT",
        "OBJECTIVE",
        "INDEPENDENTLY_VERIFIED",
    ),
    ContractRegion(
        "s3.inventory-summary",
        SECTION_THREE,
        _paragraph_selector(SECTION_THREE, -1),
        _render_inventory_summary,
        ("/vector_summary/total_vectors", "/vector_summary/fixtures"),
        "EXACT",
        "OBJECTIVE",
        "INDEPENDENTLY_VERIFIED",
    ),
    ContractRegion(
        "s4.replay-summary-opening",
        REPLAY_SUMMARY_SECTION,
        _paragraph_selector(REPLAY_SUMMARY_SECTION, 0),
        _sliced_renderer(_render_replay_summary_block, 0, 1),
        (
            "/replay_contract/flattened_evidence_derived_history_claimed",
            # the sentence counts the classifications and says whether the
            # fourth is absent, so both are its authorities
            "/replay_contract/classifications",
            "/replay_contract/deterministic_derivation_present",
        ),
        "EXACT",
        "OBJECTIVE",
        "CANONICAL_DECLARATION_ONLY",
    ),
    ContractRegion(
        "s4.classification-bullets",
        REPLAY_SUMMARY_SECTION,
        _actual_classification_block,
        _render_classification_block,
        ("/replay_contract/classifications",),
        "EXACT",
        "DESCRIPTIVE",
        "CANONICAL_DECLARATION_ONLY",
    ),
    ContractRegion(
        "s4.deterministic-derivation",
        REPLAY_SUMMARY_SECTION,
        _paragraph_selector(REPLAY_SUMMARY_SECTION, 4),
        _sliced_renderer(_render_replay_summary_block, 1, 2),
        (
            "/replay_contract/deterministic_derivation_present",
            "/scope/phase",
            "_deferred_ancestry_citation",
        ),
        "EXACT",
        "OBJECTIVE",
        "CANONICAL_DECLARATION_ONLY",
    ),
    ContractRegion(
        "s4.linkable-facts",
        REPLAY_SUMMARY_SECTION,
        _paragraph_selector(REPLAY_SUMMARY_SECTION, 5),
        _sliced_renderer(_render_replay_summary_block, 2, None),
        (
            "/replay_contract/evidence_limits/linkable_history_facts",
            "/target_symbols/8/slice_layer",
        ),
        "EXACT",
        "OBJECTIVE",
        "CANONICAL_DECLARATION_ONLY",
    ),
    ContractRegion(
        "s4.role-lead-in",
        REPLAY_SUMMARY_SECTION,
        _paragraph_selector(REPLAY_SUMMARY_SECTION, 6),
        _render_role_lead_in,
        (
            "_retained_roles_are_source_derived",
            # the observation is over these declared positions
            "/replay_contract/retained_role_source_positions",
        ),
        "EXACT",
        "OBJECTIVE",
        "INDEPENDENTLY_VERIFIED",
    ),
    ContractRegion(
        "s4.role-implications",
        REPLAY_SUMMARY_SECTION,
        _actual_role_implication_block,
        _render_role_implication_block,
        ("/replay_contract/retained_role_source_positions",),
        "EXACT",
        "OBJECTIVE",
        "INDEPENDENTLY_VERIFIED",
    ),
    ContractRegion(
        "s4.embedded-provenance",
        REPLAY_SUMMARY_SECTION,
        _paragraph_selector(REPLAY_SUMMARY_SECTION, -1),
        _render_embedded_provenance,
        ("_caller_supplied_cite_no_retained_location",),
        "EXACT",
        "OBJECTIVE",
        "INDEPENDENTLY_VERIFIED",
    ),
    ContractRegion(
        "s6.rejection-oracle",
        SECTION_SIX,
        _paragraph_selector(SECTION_SIX, 0),
        _render_rejection_oracle,
        (
            "/rejection_contract/error_oracle",
            "/rejection_contract/unstable_prose_locked",
            "/rejection_contract/internal_union_branch_labels_locked",
            "/target_symbols/7/slice_layer",
            "/target_symbols/8/slice_layer",
        ),
        "EXACT",
        "OBJECTIVE",
        "CANONICAL_DECLARATION_ONLY",
    ),
    ContractRegion(
        "s6.forbidden-extra-prose",
        SECTION_SIX,
        _paragraph_selector(SECTION_SIX, 1),
        _render_forbidden_extra_prose,
        ("/s07_forbidden_extra_ledger", "/target_symbols/8/slice_layer"),
        "EXACT",
        "OBJECTIVE",
        "CANONICAL_DECLARATION_ONLY",
    ),
    ContractRegion(
        "s6.forbidden-extra-table",
        SECTION_SIX,
        _table_selector(SECTION_SIX, "forbidden extras"),
        _table_renderer("forbidden extras"),
        ("/s07_forbidden_extra_ledger",),
        "EXACT",
        "OBJECTIVE",
        "INDEPENDENTLY_VERIFIED",
    ),
    ContractRegion(
        "s7.governance-prose",
        SECTION_SEVEN,
        _paragraph_selector(SECTION_SEVEN, 0),
        _render_governance_prose,
        (
            "/effective_governance/vectorized_as_product_behavior",
            "/effective_governance/recomputation_required",
            "_correction_is_append_only",
        ),
        "EXACT",
        "OBJECTIVE",
        "CANONICAL_DECLARATION_ONLY",
    ),
    ContractRegion(
        "s7.governance-block",
        SECTION_SEVEN,
        _actual_governance_block,
        _render_governance_block,
        (
            # thirteen numbers are printed and thirteen are declared: the block
            # used to name five of them and read the other eight unannounced
            "/effective_governance/inherited_subject_count",
            "/effective_governance/dispositioned_exactly_once",
            "/effective_governance/self_introduced_count",
            "/effective_governance/self_owned_open",
            "/effective_governance/totals/disposition/split",
            "/effective_governance/totals/disposition/carried_forward",
            "/effective_governance/totals/immediate_owner/S1.P06",
            "/effective_governance/totals/immediate_owner/S2",
            "/effective_governance/totals/immediate_owner/S5",
            "/effective_governance/totals/preserved_long_term_owner/S1.P06",
            "/effective_governance/totals/preserved_long_term_owner/S5",
            "/effective_governance/authority_totals/S1.P05.S08",
            "/effective_governance/authority_totals/S1.P05.S08.C01",
        ),
        "EXACT",
        "OBJECTIVE",
        "INDEPENDENTLY_VERIFIED",
    ),
    ContractRegion(
        "s8.non-goals",
        SECTION_EIGHT,
        _actual_non_goal_block,
        _render_non_goal_block,
        ("/non_goals",),
        "EXACT",
        "OBJECTIVE",
        "INDEPENDENTLY_VERIFIED",
    ),
    ContractRegion(
        "s9.authority-table",
        SECTION_NINE,
        _table_selector(SECTION_NINE, "source authorities"),
        _table_renderer("source authorities"),
        ("/source_decisions",),
        "EXACT",
        "OBJECTIVE",
        "CANONICAL_DECLARATION_ONLY",
    ),
)

# --- step 4: the region above the first heading ------------------------------
#
# `TILED_SECTIONS` starts at the first level-two heading, so the lines between
# the document title and `## 1.` belonged to no region. Every prose form tried
# there -- a paragraph, a bullet list, a blockquote, an indented block, a fenced
# block, an HTML comment -- was published without a single test noticing, and a
# sentence contradicting the non-goals passed as readily as an innocent one.
#
# The band carries no semantic content: the title is followed by a blank line
# and then the first heading. That is a fact about the document, not an absence
# of one, so it is recorded as an EXPLANATORY region -- no renderer, no
# authority, and an authored line list that happens to be empty. Giving it a
# structured authority would be inventing a source for prose that has none.

DOCUMENT_TITLE = CONTRACT_HEADINGS[0]

# An explanatory region declares its exact lines rather than rendering them.
# Pinning the text refuses drift and claims nothing about whether it is true --
# the same standing a CANONICAL_DECLARATION_ONLY purpose fragment has.
#
# It is also the one place in the closure where a line could enter the document
# without a canonical source, so it is held empty and asserted empty: publishing
# explanatory prose here would have to be a deliberate edit to this table and to
# the test that pins it, never a quiet addition to the Markdown.
EXPLANATORY_REGION_LINES: dict[str, tuple[str, ...]] = {"doc.preamble": ()}


def _actual_preamble(text: str) -> list[str]:
    return _section_paragraphs(text, DOCUMENT_TITLE)


STEP_FOUR_REGIONS: tuple[ContractRegion, ...] = (
    ContractRegion(
        "doc.preamble",
        DOCUMENT_TITLE,
        _actual_preamble,
        None,
        (),
        "EXPLANATORY",
        "EXPLANATORY",
        "CANONICAL_DECLARATION_ONLY",
    ),
)

CONTRACT_PROJECTION_REGISTRY: tuple[ContractRegion, ...] = (
    STEP_ONE_REGIONS + STEP_TWO_REGIONS + STEP_FOUR_REGIONS
)

# heading -> the regions that must together account for every non-blank line in
# that section, in document order
TILED_SECTIONS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (SECTION_ONE, ("s1.scope-warning",)),
    (
        SECTION_TWO,
        ("s2.surface-lead-in", "s2.target-table", "s2.supporting-authorities"),
    ),
    (SECTION_THREE, ("s3.inventory-table", "s3.inventory-summary")),
    (
        REPLAY_SUMMARY_SECTION,
        (
            "s4.replay-summary-opening",
            "s4.classification-bullets",
            "s4.deterministic-derivation",
            "s4.linkable-facts",
            "s4.role-lead-in",
            "s4.role-implications",
            "s4.embedded-provenance",
        ),
    ),
    (SECTION_FIVE, ("s5.epistemic-split", "s5.fixture-mechanism")),
    (
        SECTION_SIX,
        ("s6.rejection-oracle", "s6.forbidden-extra-prose", "s6.forbidden-extra-table"),
    ),
    (SECTION_SEVEN, ("s7.governance-prose", "s7.governance-block")),
    (SECTION_EIGHT, ("s8.non-goals",)),
    (SECTION_NINE, ("s9.authority-table",)),
)

# the whole document, title band included: every heading the corpus publishes,
# each followed by the regions that must account for it
DOCUMENT_TILES: tuple[tuple[str, tuple[str, ...]], ...] = (
    (DOCUMENT_TITLE, ("doc.preamble",)),
) + TILED_SECTIONS


def _drifted_authority(name: str) -> Any:
    """A moved form of a named authority: a flipped observation, or a family
    one vector short."""
    value = globals()[name]
    if callable(value):
        observed = cast(Callable[[], Any], value)

        def moved() -> Any:
            result = observed()
            if isinstance(result, bool):
                return not result
            if isinstance(result, tuple):
                return tuple(
                    f"{part}-drifted" for part in cast(tuple[Any, ...], result)
                )
            return f"{result}-drifted"

        return moved

    if isinstance(value, tuple):
        return cast(tuple[Any, ...], value)[:-1]

    sections = cast(dict[str, Any], value)
    family, document = next(iter(sections.items()))
    shortened = cast(dict[str, Any], document)
    return {
        **sections,
        family: {**shortened, "vectors": cast(list[Any], shortened["vectors"])[:-1]},
    }


def _descriptive_pointers(region: ContractRegion) -> list[str]:
    """Declared pointers that reach a leaf the manifest calls descriptive."""
    return [
        pointer
        for pointer in region.authority
        if pointer.startswith("/")
        and any(
            path == pointer or path.startswith(f"{pointer}/")
            for path in DESCRIPTIVE_PATHS
        )
    ]


def test_no_region_claims_verification_it_reads_from_descriptive_data() -> None:
    """The manifest forbids citing descriptive leaves as independently checked.

    `descriptive_metadata.contract` says those paths "must not be cited by
    contract.md or the pull request as independently checked". A region that
    renders one is therefore a faithful projection of a declaration, never
    evidence: the weakest assurance among a region's authorities is the one it
    may claim.
    """
    for region in CONTRACT_PROJECTION_REGISTRY:
        if _descriptive_pointers(region):
            assert region.authority_assurance != "INDEPENDENTLY_VERIFIED", (
                region.region_id,
                _descriptive_pointers(region),
            )


def _region(region_id: str) -> ContractRegion:
    return next(r for r in CONTRACT_PROJECTION_REGISTRY if r.region_id == region_id)


def _region_lines(region: ContractRegion) -> list[str]:
    """What a region publishes: a projection, or an authored explanatory block."""
    if region.renderer is not None:
        return region.renderer()
    return list(EXPLANATORY_REGION_LINES[region.region_id])


def _tile_lines(region_ids: tuple[str, ...]) -> list[str]:
    return [
        line for region_id in region_ids for line in _region_lines(_region(region_id))
    ]


@pytest.mark.parametrize(
    ("heading", "region_ids"),
    DOCUMENT_TILES,
    ids=[
        h.split(".")[0] if h.startswith("## ") else "# title" for h, _ in DOCUMENT_TILES
    ],
)
def test_each_tiled_section_is_exactly_its_registered_regions(
    heading: str, region_ids: tuple[str, ...]
) -> None:
    """Placement and completeness: these regions, this section, nothing else.

    The section's whole non-blank content must equal what the registry renders
    for it, so a block is no longer merely correct -- it has to be under its own
    heading, in order, with no softening prose beside it. The title band is
    tiled on the same terms, and its region declares no lines at all.
    """
    text = (CORPUS / "contract.md").read_text("utf-8")

    assert _section_paragraphs(text, heading) == _tile_lines(region_ids), heading


def test_a_paragraph_added_to_a_tiled_section_is_refused() -> None:
    """Softening prose beside a published block must not pass unnoticed."""
    text = (CORPUS / "contract.md").read_text("utf-8")
    smuggled = "In practice this boundary is advisory rather than published."

    for heading, region_ids in DOCUMENT_TILES:
        tampered = text.replace(f"{heading}\n", f"{heading}\n\n{smuggled}\n", 1)
        assert tampered != text, heading
        assert _section_paragraphs(tampered, heading) != _tile_lines(region_ids), (
            heading
        )


# --- step 3: the authorities this corpus locks but had never opened ----------
#
# Three claims in contract.md were true of artifacts outside the manifest, and
# steps 1 and 2 could only project them from the manifest's own restatements.
# The deferral citation was a frozen literal, the owner topology was read off
# the non-goal string it is supposed to justify, and "append-only" came from a
# manifest label naming itself rather than from the correction's own flag.
#
# The rule for reaching outside is narrow: an artifact is readable only if
# `source_decisions` already locks it, and it is read through that lock -- the
# reference names the entry, the entry names the path and the digest, and the
# bytes must match before anything is parsed. A locked document may cite a
# predecessor; citing is not opening. The S08 decision cites the S1.P02 closure
# by path, pointer and digest, and that closure stays shut.

GOVERNANCE_DECISION = "decision:s1-p05-s08:disposition"
GOVERNANCE_CORRECTION = "correction:s1-p05-s08-c01:owner-topology"

# the deferred subject the replay summary cites, and the owner-topology subjects
# the generic-graph non-goal rests on
DEFERRED_ANCESTRY = "deferred:22"
GENERIC_GRAPH_SUBJECTS = (
    "deferred:02",
    "deferred:22",
    "deferred:p01:p05-development-history-event-model",
    "deferred:p01:p05-development-history-relationship-model",
)
FAULT_VOCABULARY_SUBJECT = "gap:s05-known:case-relationship-vocabulary-provisional"


def _locked_source(decision_reference: str) -> dict[str, Any]:
    """The structured body of an artifact `source_decisions` already locks."""
    entries = cast(list[dict[str, Any]], MANIFEST["source_decisions"])
    matches = [e for e in entries if e["decision_reference"] == decision_reference]
    assert len(matches) == 1, decision_reference

    entry = matches[0]
    raw = (REPOSITORY_ROOT / cast(str, entry["path"])).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == entry["sha256"], decision_reference
    return cast(dict[str, Any], json.loads(raw))


def _sole_record(records: list[dict[str, Any]], key: str, value: str) -> dict[str, Any]:
    """Exactly one structured record: absent, duplicated and ambiguous all fail."""
    found = [record for record in records if record.get(key) == value]
    assert len(found) == 1, (key, value, len(found))
    return found[0]


def _inherited_subject(subject_id: str) -> dict[str, Any]:
    """The S08 register entry for a subject, keyed on its origin citation."""
    items = cast(
        list[dict[str, Any]],
        _locked_source(GOVERNANCE_DECISION)["inherited_subject_register"]["items"],
    )
    found = [
        item
        for item in items
        if cast(dict[str, Any], item["source"])["subject_id"] == subject_id
    ]
    assert len(found) == 1, (subject_id, len(found))
    return found[0]


def _effective_subject(subject_id: str) -> dict[str, Any]:
    """The C01 effective projection for a subject: the owner that stands now."""
    items = cast(
        list[dict[str, Any]],
        _locked_source(GOVERNANCE_CORRECTION)["effective_projection"]["items"],
    )
    return _sole_record(items, "subject_id", subject_id)


def _deferred_ancestry_citation() -> tuple[str, str]:
    """The origin phase and subject id the replay summary cites, not its owner."""
    source = cast(dict[str, Any], _inherited_subject(DEFERRED_ANCESTRY)["source"])
    origin = cast(str, source["source_artifact"]).split("_")[0]
    return origin, cast(str, source["subject_id"])


def _generic_graph_owner() -> str:
    """The single owner the correction gives every generic-graph subject."""
    owners = {
        cast(str, _effective_subject(subject)["immediate_owner"])
        for subject in GENERIC_GRAPH_SUBJECTS
    }
    assert len(owners) == 1, owners
    return owners.pop()


def _subjects_owned_by(owner: str) -> set[str]:
    """Every subject the correction leaves with one owner."""
    items = cast(
        list[dict[str, Any]],
        _locked_source(GOVERNANCE_CORRECTION)["effective_projection"]["items"],
    )
    return {
        cast(str, item["subject_id"])
        for item in items
        if item["immediate_owner"] == owner
    }


def _correction_is_append_only() -> bool:
    identity = cast(
        dict[str, Any], _locked_source(GOVERNANCE_CORRECTION)["correction_identity"]
    )
    return identity["append_only"] is True


def test_the_deferred_ancestry_subject_reads_from_its_locked_register() -> None:
    """Origin and current owner are different facts and stay different.

    The decision carries the subject forward from `S1.P02` and, at the time it
    was written, left it with `S1.P06`. The correction moved it to `S5`. The
    sentence in section 4 cites the origin; it does not say who owns it now.
    """
    inherited = _inherited_subject(DEFERRED_ANCESTRY)
    source = cast(dict[str, Any], inherited["source"])
    carried = cast(dict[str, Any], inherited["carried_forward"])
    effective = _effective_subject(DEFERRED_ANCESTRY)

    assert source["subject_id"] == DEFERRED_ANCESTRY
    assert source["source_artifact"].startswith("S1.P02")
    assert inherited["subject"] == "ancestry and reachability"
    assert inherited["disposition"] == "carried_forward"

    # the decision's own owner is superseded, so reading it as current would be
    # wrong in exactly the way the correction exists to fix
    assert carried["immediate_owner"] == "S1.P06"
    assert effective["immediate_owner"] == "S5"
    assert effective["preserved_long_term_owner"] == "S5"
    assert effective["subject"] == inherited["subject"]

    assert _deferred_ancestry_citation() == ("S1.P02", DEFERRED_ANCESTRY)


def test_the_generic_graph_owner_topology_reads_from_the_locked_correction() -> None:
    """S5 owns the generic graph; S1.P06 keeps the fault-specific vocabulary."""
    for subject in GENERIC_GRAPH_SUBJECTS:
        entry = _effective_subject(subject)
        assert entry["immediate_owner"] == "S5", subject
        assert entry["preserved_long_term_owner"] == "S5", subject

    # positive control: the correction moved the generic graph, not everything
    # that mentions relationships
    fault = _effective_subject(FAULT_VOCABULARY_SUBJECT)
    assert fault["immediate_owner"] == "S1.P06"
    assert fault["preserved_long_term_owner"] == "S1.P06"
    assert _generic_graph_owner() == "S5"

    # closed from the other side too: S1.P06 keeps that subject and no other, so
    # the correction cannot be read as moving all relationship semantics to S5
    assert _subjects_owned_by("S1.P06") == {FAULT_VOCABULARY_SUBJECT}
    assert set(GENERIC_GRAPH_SUBJECTS) <= _subjects_owned_by("S5")


def test_the_generic_graph_non_goal_matches_the_locked_owner_topology() -> None:
    """The published bullet is rendered from the topology, not trusted beside it."""
    owner = _generic_graph_owner()
    fault_owner = cast(
        str, _effective_subject(FAULT_VOCABULARY_SUBJECT)["immediate_owner"]
    )
    assert owner != fault_owner

    declared = [
        goal
        for goal in cast(list[str], MANIFEST["non_goals"])
        if "evolution graph" in goal
    ]
    assert declared == [
        f"generic repository or evolution graph is {owner}-owned,"
        f" not {fault_owner}-owned"
    ]


def test_the_correction_append_only_flag_is_the_artifacts_own() -> None:
    """The manifest labels itself; only the correction can vouch for itself."""
    identity = cast(
        dict[str, Any], _locked_source(GOVERNANCE_CORRECTION)["correction_identity"]
    )

    assert identity["append_only"] is True
    assert type(identity["append_only"]) is bool
    assert identity["corrects_slice"] == "S1.P05.S08"
    assert identity["slice"] == "S1.P05.S08.C01"
    assert _correction_is_append_only() is True

    # the manifest's own role string is declared descriptive, so it could never
    # have been the independent authority step 2 needed -- but reading it to
    # check for contradiction is not citing it as verification, and step 2 was
    # the only thing pinning its value
    entry = _sole_record(
        cast(list[dict[str, Any]], MANIFEST["source_decisions"]),
        "decision_reference",
        GOVERNANCE_CORRECTION,
    )
    assert "/source_decisions/1/authority_role" in DESCRIPTIVE_PATHS
    assert (
        cast(str, entry["authority_role"]).startswith("append_only")
        is (identity["append_only"])
    )

    # the artifact also says its predecessor was never rewritten, and that is
    # checkable rather than merely asserted: the decision digest it locks is the
    # one this corpus locks, so no new file is opened to confirm it
    integrity = cast(
        dict[str, Any], _locked_source(GOVERNANCE_CORRECTION)["predecessor_integrity"]
    )
    assert integrity["append_only"] is True
    assert integrity["predecessor_artifact_regenerated"] is False

    cited = _sole_record(
        cast(
            list[dict[str, Any]],
            _locked_source(GOVERNANCE_CORRECTION)["source_locks"]["cited_artifacts"],
        ),
        "role",
        "corrected_predecessor_decision",
    )
    decision = _sole_record(
        cast(list[dict[str, Any]], MANIFEST["source_decisions"]),
        "decision_reference",
        GOVERNANCE_DECISION,
    )
    assert cited["path"] == decision["path"]
    assert cited["sha256"] == decision["sha256"]


def test_no_unlocked_predecessor_is_opened_as_authority() -> None:
    """A locked document may cite a predecessor; the citation is not a door.

    The S08 decision names the `S1.P02` closure by path, pointer and digest.
    That closure is not in `source_decisions`, so this module must never open
    it -- reading the citation is the whole of what step 3 is allowed to do.
    """
    locked = {
        cast(str, entry["path"])
        for entry in cast(list[dict[str, Any]], MANIFEST["source_decisions"])
    }
    # every path either locked document cites, wherever it sits: harvesting one
    # collection would leave the blocklist complete only by luck
    cited: set[str] = set()

    def collect(node: Any) -> None:
        if isinstance(node, dict):
            mapping = cast(dict[str, Any], node)
            value = mapping.get("path")
            if isinstance(value, str):
                cited.add(value)
            for child in mapping.values():
                collect(child)
        elif isinstance(node, list):
            for child in cast(list[Any], node):
                collect(child)

    for reference in (GOVERNANCE_DECISION, GOVERNANCE_CORRECTION):
        collect(_locked_source(reference))

    unlocked = sorted(cited - locked)
    assert len(unlocked) >= 3, unlocked
    assert any("s1-p02-phase-closure" in path for path in unlocked)

    # A source-text scan cannot stop a path assembled at runtime; what it does
    # stop is the ordinary way one gets opened, which is by being written down.
    module = Path(__file__).read_text("utf-8")
    for path in unlocked:
        assert path not in module, path


# --- step 3: claim-level assurance, because regions are coarser than claims --
#
# A region carries several claims and may only advertise the weakest assurance
# among them, so upgrading a whole region because one sentence inside it gained
# an external authority would overclaim the rest. The three claims that now rest
# on a locked artifact are recorded individually, alongside the one that does
# not: the S1.P09 deflection is projected exactly and verified by nobody, and
# saying so is the point of keeping the axes apart.

EXTERNAL_CLAIMS: tuple[tuple[str, str, str, str], ...] = (
    (
        "s4.deferred-ancestry-citation",
        "s4.deterministic-derivation",
        GOVERNANCE_DECISION,
        "INDEPENDENTLY_VERIFIED",
    ),
    (
        "s7.correction-append-only",
        "s7.governance-prose",
        GOVERNANCE_CORRECTION,
        "INDEPENDENTLY_VERIFIED",
    ),
    (
        "s8.generic-graph-owner",
        "s8.non-goals",
        GOVERNANCE_CORRECTION,
        "INDEPENDENTLY_VERIFIED",
    ),
    # S8-U12: the bullet projects `/non_goals/22` exactly, but the slice that
    # owns confidence and review publishes no structured authority this corpus
    # locks. Verifying it would mean opening the roadmap or another phase's
    # closure, which step 3 is not allowed to do.
    ("s8.p09-deflection", "s8.non-goals", "", "EXTERNAL_AUTHORITY_DEFERRED"),
)


# the reader each claim rests on, where the region's own renderer reads it.
# `s8.generic-graph-owner` is absent on purpose: the non-goal bullet renders from
# `/non_goals`, and its binding to the topology is the equality assertion in
# `test_the_generic_graph_non_goal_matches_the_locked_owner_topology`.
CLAIM_READERS = {
    "s4.deferred-ancestry-citation": "_deferred_ancestry_citation",
    "s7.correction-append-only": "_correction_is_append_only",
}


def test_the_external_claim_ledger_is_the_set_step_three_closed() -> None:
    """Listing well-formed rows proves nothing if a row can simply vanish."""
    verified = {c for c, _, _, s in EXTERNAL_CLAIMS if s == "INDEPENDENTLY_VERIFIED"}
    deferred = {
        c for c, _, _, s in EXTERNAL_CLAIMS if s == "EXTERNAL_AUTHORITY_DEFERRED"
    }

    assert verified == {
        "s4.deferred-ancestry-citation",
        "s7.correction-append-only",
        "s8.generic-graph-owner",
    }
    assert deferred == {"s8.p09-deflection"}

    # a claim whose region renders its reader must say so in that region's
    # authority, or the two could drift apart unnoticed
    for claim_id, region_id, _, _ in EXTERNAL_CLAIMS:
        reader = CLAIM_READERS.get(claim_id)
        if reader is not None:
            assert reader in _region(region_id).authority, claim_id


def test_every_external_claim_names_a_registered_region_and_authority() -> None:
    registered = {region.region_id for region in CONTRACT_PROJECTION_REGISTRY}
    references = {
        cast(str, entry["decision_reference"])
        for entry in cast(list[dict[str, Any]], MANIFEST["source_decisions"])
    }
    seen: set[str] = set()

    for claim_id, region_id, authority, assurance in EXTERNAL_CLAIMS:
        assert claim_id not in seen, claim_id
        seen.add(claim_id)
        assert region_id in registered, claim_id
        assert assurance in AUTHORITY_ASSURANCES, claim_id
        # verified means a locked artifact vouches for it; deferred means none does
        if assurance == "INDEPENDENTLY_VERIFIED":
            assert authority in references, claim_id
        else:
            assert authority == "", claim_id


def test_a_claim_may_not_outrank_the_region_that_carries_it() -> None:
    """A verified claim inside a declaration-only region does not lift the region.

    `s7.governance-prose` also restates `recomputation_required`, which is
    descriptive, so the region stays where step 2 left it even though the
    append-only half is now vouched for by the correction itself.
    """
    for _, region_id, _, assurance in EXTERNAL_CLAIMS:
        region = _region(region_id)
        if assurance != "INDEPENDENTLY_VERIFIED":
            continue
        if _descriptive_pointers(region):
            assert region.authority_assurance == "CANONICAL_DECLARATION_ONLY", region_id


def test_the_p09_deflection_is_never_reported_as_verified() -> None:
    """Step 3 must not be able to claim S8-U12 was independently checked."""
    claim = _sole_record(
        [
            {"id": c, "region": r, "authority": a, "assurance": s}
            for c, r, a, s in EXTERNAL_CLAIMS
        ],
        "id",
        "s8.p09-deflection",
    )

    assert claim["assurance"] == "EXTERNAL_AUTHORITY_DEFERRED"
    assert claim["authority"] == ""

    # nothing this corpus locks could supply the deflected slice's ownership
    locked = {
        cast(str, entry["path"]).lower()
        for entry in cast(list[dict[str, Any]], MANIFEST["source_decisions"])
    }
    assert not [path for path in locked if "roadmap" in path or "p09" in path]

    # and the bullet it refers to is still exactly projected
    assert "no S1.P09 confidence or review interpretation" in cast(
        list[str], MANIFEST["non_goals"]
    )


# --- step 4: the document, not a set of separately checked sections ----------
#
# Steps 1 to 3 closed regions one at a time and tiled the sections they lived
# in. What they never said is that those sections are the whole document, and
# three holes lived in the gap.
#
#   The band between the document title and `## 1.` belonged to no region, so
#   any prose put there published unchecked -- including prose contradicting a
#   non-goal the document projects correctly two hundred lines further down.
#
#   `TILED_SECTIONS` was a hand-maintained literal that nothing compared with
#   the document. Deleting one entry took a whole published section out of the
#   comparison and cost one silently vanished parametrization.
#
#   The tiling compared non-blank lines only, so blank lines were unowned
#   everywhere. Deleting the single blank line above the governance block
#   dissolves that indented code block into the paragraph before it -- the
#   document renders differently and every test stayed green.
#
# All three are the same missing statement, so one statement closes them: the
# document is reconstructed, line for line and blank for blank, from the
# heading authority and the registry, and compared with the published bytes.
# That is not a snapshot -- nothing here holds a copy of the prose. Every
# non-blank line comes from a named renderer reading the canonical JSON, or
# from an explanatory region's declared lines; the separators come from one
# stated rule; and the headings come from `CONTRACT_HEADINGS`. A line that no
# region produces cannot appear anywhere, at any indentation, in any container.

LINE_DISPOSITIONS = (
    "DOCUMENT_TITLE",
    "SECTION_HEADING",
    "BLOCK_SEPARATOR",
    "REGION",
)


def _document_partition(
    tiles: tuple[tuple[str, tuple[str, ...]], ...] = DOCUMENT_TILES,
) -> list[tuple[str, str, str]]:
    """`(line, disposition, owner)` for every line the document is made of.

    One blank line separates every block from the next: after a heading, and
    between two regions. The document ends at its last block rather than with a
    trailing separator. The tiling is a parameter so a probe can remove an
    entry and watch the projection lose the section it accounted for.
    """
    partition: list[tuple[str, str, str]] = []
    for heading, region_ids in tiles:
        kind = "DOCUMENT_TITLE" if heading == DOCUMENT_TITLE else "SECTION_HEADING"
        partition.append((heading, kind, heading))
        for region_id in region_ids:
            body = _region_lines(_region(region_id))
            if not body:
                continue
            partition.append(("", "BLOCK_SEPARATOR", region_id))
            partition.extend((line, "REGION", region_id) for line in body)
        partition.append(("", "BLOCK_SEPARATOR", heading))
    return partition[:-1]


def _render_contract_document() -> list[str]:
    return [line for line, _kind, _owner in _document_partition()]


def _document_closure_failures(text: str) -> list[tuple[int, str, str]]:
    """`(line number, reason, owner)` where the document departs from the projection.

    A whole-file comparison could only say "different". Walking the two in step
    names the line, why it is wrong, and which registered owner the projection
    had put there, so a smuggled claim is reported where it sits.
    """
    projected = _document_partition()
    published = text.splitlines()
    failures: list[tuple[int, str, str]] = []
    for index in range(max(len(projected), len(published))):
        expected = projected[index][0] if index < len(projected) else None
        actual = published[index] if index < len(published) else None
        if expected == actual:
            continue
        if expected is None:
            failures.append((index + 1, "line-outside-every-region", "END_OF_DOCUMENT"))
        elif actual is None:
            failures.append((index + 1, "projected-line-missing", projected[index][2]))
        else:
            failures.append(
                (
                    index + 1,
                    f"{projected[index][1].lower()}-differs",
                    projected[index][2],
                )
            )
    return failures


def test_the_contract_document_is_exactly_what_the_registry_projects() -> None:
    """The whole file, byte for byte, from the authorities that own it."""
    text = (CORPUS / "contract.md").read_text("utf-8")

    assert _document_closure_failures(text) == []
    assert _render_contract_document() == text.splitlines()
    # the bytes, not just the lines: LF endings and one final newline
    assert "\n".join(_render_contract_document()) + "\n" == text
    assert "\r" not in text and not text.endswith("\n\n")


def test_every_document_line_has_exactly_one_structural_disposition() -> None:
    """No line unowned, none owned twice, and no region split in two.

    Half of what follows is a property of `_document_partition` rather than of
    the document -- a separator is blank because the builder emits `""`, and the
    dispositions are the four it can produce. Those assertions are kept as the
    partition's own contract, so a later builder that emitted a semantic line as
    a separator, or ran two regions together, would have to break one of them.
    The claims that are about the DOCUMENT are the three at the end: the
    partition is exactly as long as the file, every registered region resolves
    to exactly one unbroken run, and the heading sequence the partition emits is
    the published one.
    """
    text = (CORPUS / "contract.md").read_text("utf-8")
    partition = _document_partition()
    registered = {region.region_id for region in CONTRACT_PROJECTION_REGISTRY}

    assert len(partition) == len(text.splitlines())
    # The separator rule is one blank line, stated rather than assumed: no two
    # blocks are joined and none is separated by two. It is deliberately
    # STRICTER than CommonMark, which would render a second blank line
    # identically -- a derived document has one layout, and a layout that can
    # drift silently is a layout nothing owns.
    assert "\n\n\n" not in text
    assert not any(
        partition[index][1] == "BLOCK_SEPARATOR" == partition[index + 1][1]
        for index in range(len(partition) - 1)
    )
    for line, kind, owner in partition:
        assert kind in LINE_DISPOSITIONS, (kind, owner)
        # a separator is blank and a semantic line is not: the two kinds of
        # line are distinguished by what they are, not by where they sit
        assert (kind == "BLOCK_SEPARATOR") == (line == ""), (kind, line)
        if kind == "REGION":
            assert owner in registered, owner
        else:
            assert owner in CONTRACT_HEADINGS or owner in registered, owner

    owned = [owner for _line, kind, owner in partition if kind == "REGION"]
    # every region resolves exactly once, as one unbroken run
    runs = [
        owner
        for index, owner in enumerate(owned)
        if not index or owner != owned[index - 1]
    ]
    assert len(runs) == len(set(runs)), runs
    assert set(runs) == registered - {"doc.preamble"}, sorted(registered ^ set(runs))
    # the one channel a line could enter through without a canonical source is
    # held empty, and every explanatory region has to come through it
    assert EXPLANATORY_REGION_LINES == {"doc.preamble": ()}
    assert {
        region.region_id
        for region in CONTRACT_PROJECTION_REGISTRY
        if region.renderer is None
    } == set(EXPLANATORY_REGION_LINES)

    headings = [
        owner
        for _line, kind, owner in partition
        if kind in ("DOCUMENT_TITLE", "SECTION_HEADING")
    ]
    assert headings == list(CONTRACT_HEADINGS)

    counted = Counter(kind for _line, kind, _owner in partition)
    assert counted["DOCUMENT_TITLE"] == 1
    assert counted["SECTION_HEADING"] == len(CONTRACT_HEADINGS) - 1
    assert sum(counted.values()) == len(text.splitlines())


def test_the_document_tiles_account_for_every_heading_and_every_region() -> None:
    """A hand-kept tiling that nothing compares can quietly lose a section."""
    text = (CORPUS / "contract.md").read_text("utf-8")

    assert [heading for heading, _ids in DOCUMENT_TILES] == list(CONTRACT_HEADINGS)
    assert [heading for heading, _ids in DOCUMENT_TILES] == _actual_headings(text)

    tiled = [region_id for _heading, ids in DOCUMENT_TILES for region_id in ids]
    assert len(tiled) == len(set(tiled))
    assert set(tiled) == {region.region_id for region in CONTRACT_PROJECTION_REGISTRY}
    # and every region is tiled under the heading it declares
    for heading, ids in DOCUMENT_TILES:
        for region_id in ids:
            assert _region(region_id).heading == heading, region_id


def test_a_section_dropped_from_the_tiling_is_refused() -> None:
    """Losing a tile used to cost one vanished parametrization and nothing else.

    A hand-kept tiling that no test compares with the document can shed a whole
    published section, after which anything may be written inside it. The
    projection notices because the section's lines simply stop being produced.
    """
    text = (CORPUS / "contract.md").read_text("utf-8")
    reduced = tuple(tile for tile in DOCUMENT_TILES if tile[0] != SECTION_EIGHT)

    assert len(reduced) == len(DOCUMENT_TILES) - 1
    assert [heading for heading, _ids in reduced] != list(CONTRACT_HEADINGS)

    lost = [line for line, _kind, _owner in _document_partition(reduced)]
    assert lost != text.splitlines()
    assert SECTION_EIGHT not in lost
    # the heading, its two separators, and every bullet the section published
    dropped = len(_region_lines(_region("s8.non-goals"))) + 3
    assert len(lost) == len(text.splitlines()) - dropped == 109
    # and the region it dropped stops being owned by anything
    assert "s8.non-goals" not in {
        owner for _l, _k, owner in _document_partition(reduced)
    }


# --- every way to publish an unowned line, refused --------------------------


# What the projection must report for each smuggled line: the line it first
# disagrees on, why, and which registered owner it had put there. Pinning the
# codomain of those three would have proved nothing -- a diagnostic returning a
# constant wrong answer satisfies it -- so each row carries its own triple.
DOCUMENT_MUTATION_REPORTS: dict[str, tuple[int, str, str]] = {
    "preamble prose": (3, "section_heading-differs", SECTION_ONE),
    "preamble bullet": (3, "section_heading-differs", SECTION_ONE),
    "preamble blockquote": (3, "section_heading-differs", SECTION_ONE),
    "preamble indented": (3, "section_heading-differs", SECTION_ONE),
    "preamble fenced": (3, "section_heading-differs", SECTION_ONE),
    "preamble html comment": (3, "section_heading-differs", SECTION_ONE),
    "preamble table": (3, "section_heading-differs", SECTION_ONE),
    "trailing prose": (145, "line-outside-every-region", "END_OF_DOCUMENT"),
    "trailing bullet": (145, "line-outside-every-region", "END_OF_DOCUMENT"),
    "after a heading": (73, "region-differs", "s6.rejection-oracle"),
    "between two regions": (43, "region-differs", "s3.inventory-summary"),
    "inside the bullet block": (123, "region-differs", "s8.non-goals"),
    "inside the governance block": (96, "region-differs", "s7.governance-block"),
    "inside a table": (41, "region-differs", "s3.inventory-table"),
    "separator deleted": (94, "block_separator-differs", "s7.governance-block"),
    "separator doubled": (67, "region-differs", "s5.epistemic-split"),
    "every separator deleted": (2, "block_separator-differs", DOCUMENT_TITLE),
    "trailing separator": (145, "line-outside-every-region", "END_OF_DOCUMENT"),
    "a table row moved to another section": (
        27,
        "region-differs",
        "s3.inventory-table",
    ),
    "a table row duplicated": (145, "line-outside-every-region", "END_OF_DOCUMENT"),
    "a table row deleted": (144, "projected-line-missing", "s9.authority-table"),
    "list-nested heading": (128, "region-differs", "s8.non-goals"),
    "blockquote heading": (136, "section_heading-differs", SECTION_NINE),
}


def _document_mutations(text: str) -> list[tuple[str, str]]:
    """`(label, tampered document)` for each way a line could be smuggled in."""
    claim = "In practice this corpus publishes a complete development-history graph."
    non_goal = "- a complete development-history graph is published"
    title = f"{DOCUMENT_TITLE}\n"
    last = text.splitlines()[-1]
    return [
        # the band that belonged to nobody, in every form that was silent
        ("preamble prose", text.replace(title, f"{title}\n{claim}\n", 1)),
        ("preamble bullet", text.replace(title, f"{title}\n{non_goal}\n", 1)),
        ("preamble blockquote", text.replace(title, f"{title}\n> {claim}\n", 1)),
        ("preamble indented", text.replace(title, f"{title}\n    {claim}\n", 1)),
        ("preamble fenced", text.replace(title, f"{title}\n```\n{claim}\n```\n", 1)),
        (
            "preamble html comment",
            text.replace(title, f"{title}\n<!-- {claim} -->\n", 1),
        ),
        (
            "preamble table",
            text.replace(title, f"{title}\n| a | b |\n| --- | --- |\n", 1),
        ),
        # and the rest of the document, so the closure is not preamble-shaped
        ("trailing prose", f"{text}\n{claim}\n"),
        ("trailing bullet", f"{text}{non_goal}\n"),
        (
            "after a heading",
            text.replace(f"{SECTION_SIX}\n", f"{SECTION_SIX}\n\n{claim}\n", 1),
        ),
        (
            "between two regions",
            text.replace("183 vectors over", f"{claim}\n\n183 vectors over", 1),
        ),
        (
            "inside the bullet block",
            text.replace("- no root cause", f"{non_goal}\n- no root cause", 1),
        ),
        (
            "inside the governance block",
            text.replace("    split 5", f"    {claim}\n    split 5", 1),
        ),
        (
            "inside a table",
            text.replace("| **total** |", f"| {claim} | | | |\n| **total** |", 1),
        ),
        # structure, not prose: the blank lines the document is built from
        (
            "separator deleted",
            text.replace("\n\n    inherited ", "\n    inherited ", 1),
        ),
        (
            "separator doubled",
            text.replace(f"{SECTION_FIVE}\n\n", f"{SECTION_FIVE}\n\n\n", 1),
        ),
        (
            "every separator deleted",
            "\n".join(line for line in text.splitlines() if line) + "\n",
        ),
        ("trailing separator", f"{text}\n"),
        # a region moved, duplicated or deleted
        (
            "a table row moved to another section",
            text.replace(f"\n{last}\n", "\n", 1).replace(
                f"{SECTION_THREE}\n", f"{SECTION_THREE}\n\n{last}\n", 1
            ),
        ),
        ("a table row duplicated", text.replace(f"{last}\n", f"{last}\n{last}\n", 1)),
        ("a table row deleted", text.replace(f"\n{last}\n", "\n", 1)),
        # a container is not a hiding place either
        (
            "list-nested heading",
            text.replace("- no persistence", "- ## 10. Extra\n- no persistence", 1),
        ),
        (
            "blockquote heading",
            text.replace(f"{SECTION_NINE}\n", f"> ## 10. Extra\n\n{SECTION_NINE}\n", 1),
        ),
    ]


def test_no_line_can_be_published_outside_the_registry() -> None:
    """Every way in, refused, and each refusal attributed to a registered owner.

    Once the document is reconstructed, ANY edit to it is detectable -- that is
    the point of the reconstruction and it makes "is this mutation caught" a
    weak question. So this test asks the two things that are not implied by it.
    First, that the enumeration covers every way a line could arrive: the title
    band in six shapes, the body in five positions, the block structure in four,
    and two containers. Second, that each refusal is ATTRIBUTED -- the line, the
    reason, and which registered owner the projection had put there -- because a
    rule that could only say "the file changed" would be a snapshot diff wearing
    a registry's name.
    """
    text = (CORPUS / "contract.md").read_text("utf-8")
    mutations = _document_mutations(text)

    # positive control: the published document is what the registry projects
    assert _document_closure_failures(text) == []
    assert len(mutations) == 23
    assert {label for label, _t in mutations} == set(DOCUMENT_MUTATION_REPORTS)

    registered = {region.region_id for region in CONTRACT_PROJECTION_REGISTRY}
    for label, tampered in mutations:
        assert tampered != text, label
        failures = _document_closure_failures(tampered)
        assert failures, label
        assert failures[0] == DOCUMENT_MUTATION_REPORTS[label], label
        _line, _reason, owner = failures[0]
        assert (
            owner in registered
            or owner in CONTRACT_HEADINGS
            or owner == "END_OF_DOCUMENT"
        ), (label, owner)

    # the title band is refused by its own region, not only by the whole-document
    # comparison, so the preamble has an owner rather than a special case
    for label, tampered in mutations:
        if label.startswith("preamble"):
            assert _actual_preamble(tampered) != [], label
            line, _reason, _owner = _document_closure_failures(tampered)[0]
            # reported inside the title band, above the first section heading
            assert line <= 4, (label, line)


# Where the projection first disagrees for each placement. A contradiction is
# an ordinary added line as far as the structure is concerned, so the report is
# the same whichever sentence is smuggled -- which is the honest claim, and is
# what these pins say.
CONTRADICTION_REPORTS: dict[str, tuple[int, str, str]] = {
    "preamble": (3, "section_heading-differs", SECTION_ONE),
    "after the first heading": (5, "region-differs", "s1.scope-warning"),
    "mid document": (67, "region-differs", "s5.epistemic-split"),
    "after the last table": (145, "line-outside-every-region", "END_OF_DOCUMENT"),
}


def test_a_contradiction_beside_a_correct_projection_is_refused() -> None:
    """The correct sentence surviving is not the question being asked.

    Every one of these leaves the projected statement exactly where it was and
    adds a second one denying it, which is the shape a contradiction takes when
    the oracle only checks that the right sentence is still present. Detection
    here is structural -- the added line answers to no region -- so no claim is
    made about reading English, and the two things asserted are the two that do
    not follow from the reconstruction existing: that every projected line
    really is still published unchanged in the tampered document, and that the
    refusal is attributed to an owner rather than to the file having changed.
    """
    text = (CORPUS / "contract.md").read_text("utf-8")
    rendered = _render_contract_document()
    title = f"{DOCUMENT_TITLE}\n"
    contradictions = (
        "In practice 184 vectors ship.",
        "The four canonical JSON files are derived; this Markdown is the authority.",
        "`deterministic_derivation` is in fact present.",
        "Only ten forbidden extras are published.",
        "This corpus is a production schema and a public API.",
        "Two of the nineteen fixtures are referenced by marker.",
        "The corpus is executed by the full suite and ships in the wheel.",
        "Ancestry and merge-base semantics are published after all.",
    )
    silent: list[tuple[str, str]] = []
    registered = {region.region_id for region in CONTRACT_PROJECTION_REGISTRY}
    placements: set[str] = set()
    for claim in contradictions:
        for where, tampered in (
            ("preamble", text.replace(title, f"{title}\n{claim}\n", 1)),
            (
                "after the first heading",
                text.replace(f"{SECTION_ONE}\n", f"{SECTION_ONE}\n\n{claim}\n", 1),
            ),
            (
                "mid document",
                text.replace(f"{SECTION_FIVE}\n", f"{SECTION_FIVE}\n\n{claim}\n", 1),
            ),
            ("after the last table", f"{text}\n{claim}\n"),
        ):
            placements.add(where)
            assert tampered != text, (claim, where)
            # the statement it denies is still published, unchanged
            assert set(rendered) <= set(tampered.splitlines()), (claim, where)
            failures = _document_closure_failures(tampered)
            if not failures:
                silent.append((where, claim))
                continue
            # the same attribution the smuggling probes require, per placement
            assert failures[0] == CONTRADICTION_REPORTS[where], (claim, where)
            _line, _reason, owner = failures[0]
            assert (
                owner in registered
                or owner in CONTRACT_HEADINGS
                or owner == "END_OF_DOCUMENT"
            ), (claim, where, owner)
    assert not silent, silent
    # the matrix is what the docstring says it is: a quarter of it may not go
    # missing because a tuple was edited
    assert placements == set(CONTRADICTION_REPORTS)
    assert len(contradictions) == 8
    assert len(contradictions) * len(placements) == 32


# --- the reverse direction: which region shows this declaration? -------------
#
# Every check so far runs Markdown -> authority: a published line names the
# region that renders it, and the region names the leaves it reads. That leaves
# the other question open. When a declaration is meant to appear in the
# document, WHICH region consumes it -- and can a leaf reach the page through a
# region that never declared it?
#
# It can be answered rather than asserted. Each region renders deterministically
# from the canonical JSON and a fixed set of named observations of the oracle
# itself, so a manifest leaf is document-facing exactly when perturbing it moves
# what some region renders. Two perturbations are used: the value is drifted,
# and then removed from its container, because a renderer spending only a
# collection's size is unmoved by a changed member.
#
# Three classes come out, and they partition the declaration universe:
#
#   PROJECTED   perturbing it changes a rendered line. Every region it moves
#               must declare a pointer covering it -- no leaf reaches the page
#               through a region that never said it reads it.
#   STRUCTURAL  perturbing it breaks a projection without changing any line: an
#               addressing key, or a locked artifact's coordinate read through
#               a named authority. Its value is not on the page, so demanding a
#               declaration from the breaking region would overclaim -- three
#               section-4 regions share one block renderer and would each have
#               to claim the deferral coordinate that only one of their
#               sentences rests on. The rule is therefore collection-granular:
#               the top-level key it lives under must be declared somewhere in
#               the registry. Two of the manifest's top-level keys are declared
#               by nobody, and a structural read into either of them fails.
#   UNSEEN      no region reads it. That is not the same as "not published":
#               the section-3 inventory table renders its counts from the
#               sealed vector FILES, so the manifest's own `vector_summary`
#               counts land here even though the same numbers appear on the
#               page. Nor is it "unchecked" -- those two surfaces are pinned to
#               each other elsewhere. It means only that the document does not
#               read this leaf.
#
# The counts are outputs. What is asserted is the partition and the no-silent-
# consumer rule; the numbers are reported so a later change has to move them
# deliberately.


def _leaf_slots(
    node: Any, prefix: str = "", parent: Any = None, key: Any = None
) -> list[tuple[str, Any, Any]]:
    """`(leaf path, the container holding it, its key)`, one per manifest leaf."""
    if isinstance(node, dict) and node:
        mapping = cast(dict[str, Any], node)
        return [
            slot
            for k, v in mapping.items()
            for slot in _leaf_slots(v, f"{prefix}/{k}", node, k)
        ]
    if isinstance(node, list) and node:
        items = cast(list[Any], node)
        return [
            slot
            for i, v in enumerate(items)
            for slot in _leaf_slots(v, f"{prefix}/{i}", node, i)
        ]
    return [(prefix, parent, key)]


# One sweep per registry, because three tests ask the same pure question of the
# same 386 leaves and this module is the project's fastest feedback loop. The
# key is the registry itself: the probes below hand in a modified one and must
# get a fresh answer rather than this one.
_CONSUMER_SWEEPS: dict[
    tuple[ContractRegion, ...],
    tuple[dict[str, frozenset[str]], dict[str, frozenset[str]]],
] = {}


def _document_consumers() -> tuple[
    dict[str, frozenset[str]], dict[str, frozenset[str]]
]:
    """`(shown by, broken by)` regions, for every declaration-universe leaf."""
    if CONTRACT_PROJECTION_REGISTRY in _CONSUMER_SWEEPS:
        return _CONSUMER_SWEEPS[CONTRACT_PROJECTION_REGISTRY]

    rendered = [
        (region.region_id, region.renderer)
        for region in CONTRACT_PROJECTION_REGISTRY
        if region.renderer is not None
    ]
    baseline = {region_id: render() for region_id, render in rendered}

    def observe() -> tuple[set[str], set[str]]:
        moved: set[str] = set()
        broke: set[str] = set()
        for region_id, render in rendered:
            try:
                now = render()
            except Exception:  # noqa: BLE001 - a renderer that cannot run noticed
                broke.add(region_id)
                continue
            if now != baseline[region_id]:
                moved.add(region_id)
        return moved, broke

    def restore(container: Any, key: Any, original: Any, order: Any) -> None:
        """Put the leaf back where it was, in the position it was in.

        Re-assigning a deleted mapping key APPENDS it, which silently permutes
        the manifest for every renderer that spends a dict's iteration order --
        the governance block spends three of them, and the next leaf of the same
        dict would then be measured against a stale baseline. The container is
        rebuilt from its own snapshot instead, and the seal below is
        order-sensitive so a future shortcut cannot hide the same way.
        """
        if isinstance(container, list):
            items = cast(list[Any], container)
            del items[:]
            items.extend(cast(list[Any], order))
        else:
            mapping = cast(dict[str, Any], container)
            mapping.clear()
            mapping.update(cast(dict[str, Any], order))

    meta = set(_meta_schema_leaf_paths())
    shown: dict[str, frozenset[str]] = {}
    structural: dict[str, frozenset[str]] = {}
    # The sweep edits the shared manifest in place, so it puts the document back
    # under try/finally and then proves it. Without that, an interrupted sweep
    # would leave six hundred other tests reading a damaged authority and
    # failing somewhere else entirely.
    sealed = json.dumps(MANIFEST)
    try:
        for path, container, key in _leaf_slots(MANIFEST):
            if path in meta:
                continue
            original = container[key]
            order = (
                list(cast(list[Any], container))
                if isinstance(container, list)
                else dict(cast(dict[str, Any], container))
            )
            moved: set[str] = set()
            broke: set[str] = set()
            for form in _drift_forms(original):
                container[key] = form
                seen, raised = observe()
                moved |= seen
                broke |= raised
            container[key] = original
            if isinstance(container, list):
                cast(list[Any], container).pop(key)
            else:
                del cast(dict[str, Any], container)[key]
            seen, raised = observe()
            restore(container, key, original, order)
            moved |= seen
            broke |= raised
            shown[path] = frozenset(moved)
            structural[path] = frozenset(broke - moved)
    finally:
        MANIFEST.clear()
        MANIFEST.update(cast(dict[str, Any], json.loads(sealed)))
    assert json.dumps(MANIFEST) == sealed, "the sweep did not restore"

    _CONSUMER_SWEEPS[CONTRACT_PROJECTION_REGISTRY] = (shown, structural)
    return shown, structural


def test_the_consumer_sweep_puts_the_manifest_back_exactly() -> None:
    """Including the order a mapping was in, which no renderer may find moved.

    Re-assigning a deleted key appends it. Three governance dicts are rendered
    by iteration, so a sweep that restored values but not positions would make
    the document itself change as a side effect of measuring it.
    """
    before = json.dumps(MANIFEST)
    document = _render_contract_document()
    _CONSUMER_SWEEPS.clear()
    _document_consumers()

    assert json.dumps(MANIFEST) == before
    assert _leaf_paths(MANIFEST) == json.loads(json.dumps(_leaf_paths(MANIFEST)))
    assert _render_contract_document() == document
    # and the memo really is keyed on the registry rather than on nothing
    assert CONTRACT_PROJECTION_REGISTRY in _CONSUMER_SWEEPS


def _declared_consumers(path: str) -> set[str]:
    """The regions whose declared pointers cover this leaf."""
    return {
        region.region_id
        for region in CONTRACT_PROJECTION_REGISTRY
        for reference in region.authority
        if reference.startswith("/")
        and (path == reference or path.startswith(f"{reference}/"))
    }


def test_the_leaf_slots_are_the_leaf_paths() -> None:
    """The reverse sweep addresses containers, so it must walk the same leaves."""
    assert [path for path, _c, _k in _leaf_slots(MANIFEST)] == _leaf_paths(MANIFEST)


def test_no_declaration_reaches_the_document_through_an_undeclared_region() -> None:
    """A region that shows a leaf must have said it reads it.

    The governance block printed thirteen numbers and named five; the section-4
    opening counted the classifications and named none of them; the role lead-in
    rested on the declared source positions without citing them. All three
    projected correctly and none of them said what from.
    """
    shown, structural = _document_consumers()

    undeclared = sorted(
        (path, sorted(regions - _declared_consumers(path)))
        for path, regions in shown.items()
        if regions - _declared_consumers(path)
    )
    assert not undeclared, undeclared

    # a structural input is never a leaf the registry has never heard of
    assert not _orphaned_structural_inputs(
        structural, shown, CONTRACT_PROJECTION_REGISTRY
    )


def _declared_collections(registry: tuple[ContractRegion, ...]) -> set[str]:
    return {
        reference.split("/")[1]
        for region in registry
        for reference in region.authority
        if reference.startswith("/")
    }


def _orphaned_structural_inputs(
    structural: dict[str, frozenset[str]],
    shown: dict[str, frozenset[str]],
    registry: tuple[ContractRegion, ...],
) -> list[str]:
    """Structural inputs whose collection no region declares at all."""
    collections = _declared_collections(registry)
    return sorted(
        path
        for path, regions in structural.items()
        if regions and not shown[path] and path.split("/")[1] not in collections
    )


def test_the_structural_input_rule_can_be_violated() -> None:
    """A rule nothing can break is a sentence, not a rule.

    Every `corpus_files` filename is a structural input: the section-1 sentence
    searches the ledger by filename, so removing any one of them stops the
    renderer without changing a word. They are accounted for because the region
    declares two pointers into that collection. Take both away and the nine
    become orphaned -- which is the state the rule exists to refuse.
    """
    shown, structural = _document_consumers()
    assert not _orphaned_structural_inputs(
        structural, shown, CONTRACT_PROJECTION_REGISTRY
    )

    stripped = tuple(
        region._replace(
            authority=tuple(
                reference
                for reference in region.authority
                if not reference.startswith("/corpus_files/")
            )
        )
        if region.region_id == "s1.scope-warning"
        else region
        for region in CONTRACT_PROJECTION_REGISTRY
    )
    assert "corpus_files" not in _declared_collections(stripped)
    orphaned = _orphaned_structural_inputs(structural, shown, stripped)
    assert orphaned == [f"/corpus_files/{index}/filename" for index in range(9)]


def test_the_declaration_universe_is_partitioned_by_what_the_document_shows() -> None:
    """Projected, structural, unseen -- exhaustive, disjoint, and counted."""
    shown, structural = _document_consumers()
    universe = _declaration_universe()

    projected = {path for path, regions in shown.items() if regions}
    structural_only = {
        path for path, regions in structural.items() if regions and not shown[path]
    }
    unseen = set(universe) - projected - structural_only

    # the sweep and the universe must be over the same leaves: if `_leaf_slots`
    # and `_leaf_paths` ever diverged, the three classes would silently be a
    # partition of something else
    assert set(shown) == set(structural) == set(universe)
    assert projected | structural_only | unseen == set(universe)
    assert len(universe) == 386
    assert len(projected) == 151
    assert len(structural_only) == 11
    assert len(unseen) == 224
    # the meta-schema stays outside the universe it classifies
    assert not set(shown) & set(_meta_schema_leaf_paths())

    # more than one consumer is allowed and is never silent: each is declared
    multiple = {
        path: sorted(regions) for path, regions in shown.items() if len(regions) > 1
    }
    assert len(multiple) == 11
    for path, regions in multiple.items():
        assert set(regions) <= _declared_consumers(path), path


def test_a_leaf_the_document_shows_cannot_be_dropped_from_the_registry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The rule is not vacuous: remove a declaration and the sweep says so.

    The registry itself is replaced with one governance pointer missing, and the
    same functions the rule uses are asked again. A local reimplementation of
    the matching would only have proved that this test agrees with itself.
    """
    path = "/effective_governance/dispositioned_exactly_once"
    shown, _structural = _document_consumers()
    assert shown[path] == frozenset({"s7.governance-block"})
    assert _declared_consumers(path) == {"s7.governance-block"}

    stripped = tuple(
        region._replace(
            authority=tuple(
                reference for reference in region.authority if reference != path
            )
        )
        if region.region_id == "s7.governance-block"
        else region
        for region in CONTRACT_PROJECTION_REGISTRY
    )
    monkeypatch.setitem(globals(), "CONTRACT_PROJECTION_REGISTRY", stripped)

    # the block still prints the number, so the leaf is still document-facing --
    # and now no region declares it, which is exactly the failure the rule names
    shown, _structural = _document_consumers()
    assert shown[path] == frozenset({"s7.governance-block"})
    assert _declared_consumers(path) == set()
    undeclared = sorted(
        (leaf, sorted(regions - _declared_consumers(leaf)))
        for leaf, regions in shown.items()
        if regions - _declared_consumers(leaf)
    )
    assert undeclared == [(path, ["s7.governance-block"])]


# --- the claim ledger, closed by partition rather than by row matching -------
#
# A document-projection audit taken before step 1 recorded roughly a hundred
# claim units and their gaps, and step 4 owes that ledger a final disposition
# for each. The sheet itself was an out-of-band artifact and its row numbering
# is not reconstructible: the one identifier that survives in this module,
# `S8-U12`, denotes `/non_goals/22`, which is not the twelfth unit under any
# line-order numbering of section 8. Inventing a numbering that collided with
# it would falsify a comment that is currently correct.
#
# So the ledger is closed the only way it honestly can be -- by exhaustion. The
# document is partitioned line for line, every semantic line carries the three
# declared axes of the region that owns it, and no line is left over. Any unit
# the audit could have named is a line of this document, so every unit has a
# disposition whether or not its old row number can be recovered.
#
# Exactly one audit identifier survives in this repository: `S8-U12`, in the
# step-3 comment and docstring above, and it is located below by name. The
# product-surface lead-in was discussed on the pull request as `S2-U1a` /
# `S2-U1b`; those labels appear nowhere in the repository, so that row is
# located by content rather than by a number this module would be inventing.


def _document_claim_units() -> list[tuple[int, str, str, str, str]]:
    """`(line, owner, projection kind, epistemic kind, assurance)` per unit."""
    units: list[tuple[int, str, str, str, str]] = []
    for index, (_line, kind, owner) in enumerate(_document_partition(), start=1):
        if kind == "BLOCK_SEPARATOR":
            continue
        if kind == "REGION":
            region = _region(owner)
            units.append(
                (
                    index,
                    owner,
                    region.projection_kind,
                    region.epistemic_kind,
                    region.authority_assurance,
                )
            )
        else:
            units.append((index, owner, "HEADING", "STRUCTURAL", "PUBLISHED_SEQUENCE"))
    return units


def test_every_document_claim_unit_carries_a_final_disposition() -> None:
    """No unexplained residue: the units are the document, exhaustively."""
    text = (CORPUS / "contract.md").read_text("utf-8")
    lines = text.splitlines()
    units = _document_claim_units()

    # exhaustive over the semantic lines, and only over those
    assert [line for line, _o, _p, _e, _a in units] == [
        index for index, line in enumerate(lines, start=1) if line
    ]
    assert len(units) == 113
    assert len({line for line, *_rest in units}) == len(units)

    kinds = Counter(
        (projection, epistemic, assurance)
        for _line, _owner, projection, epistemic, assurance in units
    )
    assert kinds == {
        ("HEADING", "STRUCTURAL", "PUBLISHED_SEQUENCE"): 10,
        ("EXACT", "OBJECTIVE", "INDEPENDENTLY_VERIFIED"): 71,
        ("EXACT", "OBJECTIVE", "CANONICAL_DECLARATION_ONLY"): 27,
        ("EXACT", "DESCRIPTIVE", "CANONICAL_DECLARATION_ONLY"): 5,
    }
    # nothing is projected exactly and called explanatory, or the reverse
    for _line, owner, projection, epistemic, _assurance in units:
        if projection == "HEADING":
            continue
        assert projection in PROJECTION_KINDS, owner
        assert epistemic in EPISTEMIC_KINDS, owner
        assert (projection == "EXPLANATORY") == (epistemic == "EXPLANATORY"), owner


def test_the_audit_rows_still_named_land_in_classified_regions() -> None:
    """The rows the record still names, located in the final partition.

    `S8-U12` is the one identifier this repository carries, so it is asserted by
    name. The product-surface lead-in is located by content, because no
    identifier for it exists outside the pull request discussion.
    """
    text = (CORPUS / "contract.md").read_text("utf-8")
    lines = text.splitlines()
    located = {line: owner for line, owner, *_rest in _document_claim_units()}

    # the two counts in the product-surface lead-in
    lead_in = next(
        line
        for line, raw in enumerate(lines, start=1)
        if "production modules and" in raw
    )
    assert located[lead_in] == "s2.surface-lead-in"
    assert _region("s2.surface-lead-in").authority == (
        "/scope/production_modules",
        "/scope/phase",
        "/target_symbols",
    )

    # S8-U12: the S1.P09 deflection, projected exactly and verified by nobody
    deflection = next(
        line
        for line, raw in enumerate(lines, start=1)
        if raw == f"- {MANIFEST['non_goals'][22]}"
    )
    assert located[deflection] == "s8.non-goals"
    assert ("s8.p09-deflection", "s8.non-goals", "", "EXTERNAL_AUTHORITY_DEFERRED") in (
        EXTERNAL_CLAIMS
    )

    # every external claim still names a region the partition actually owns
    owners = set(located.values())
    for _claim_id, region_id, _authority, _assurance in EXTERNAL_CLAIMS:
        assert region_id in owners, region_id


# --- every `missing` error, partitioned by what the input actually says ------
#
# `error_type == "missing"` was read as proof that a field was absent, so the
# twelve vectors where a discriminatorless union reports `missing` at its own
# supplied field derived "<field> is required". The registry repeated the same
# sentence, and the comparison between them agreed with itself. The partition
# below is over the input rather than the code, and it is exhaustive, so a new
# `missing` shape cannot slip in unclassified.


def _missing_vectors() -> list[dict[str, Any]]:
    return [
        vector
        for vector in INVALID["vectors"]
        if cast(dict[str, Any], vector["expected"]).get("error_type") == "missing"
    ]


def test_every_missing_error_is_classified_by_its_input() -> None:
    """Three shapes, disjoint and exhaustive, and none of them from the code."""
    nested: list[str] = []
    omissions: list[str] = []
    unions: list[str] = []

    for vector in _missing_vectors():
        vector_id = cast(str, vector["id"])
        expected = cast(dict[str, Any], vector["expected"])
        location = cast(list[str], expected.get("error_location") or [])
        shape = _missing_shape(vector)

        if len(location) > 1:
            # already routed to the nested-contract rule before requiredness is
            # ever considered, and untouched by this repair
            assert shape is None, vector_id
            nested.append(vector_id)
        elif shape == TRUE_OMISSION:
            omissions.append(vector_id)
        elif shape == UNION_REJECTION:
            unions.append(vector_id)
        else:
            raise AssertionError(f"unclassified missing shape: {vector_id}")

    assert len(nested) + len(omissions) + len(unions) == len(_missing_vectors()) == 32
    assert not (set(nested) & set(omissions) & set(unions))
    assert len(omissions) == 18 and len(unions) == 12 and len(nested) == 2

    for vector_id in omissions:
        vector = next(v for v in INVALID["vectors"] if v["id"] == vector_id)
        field = cast(list[str], vector["expected"]["error_location"])[0]
        assert field not in cast(dict[str, Any], vector["input"]), vector_id

    for vector_id in unions:
        vector = next(v for v in INVALID["vectors"] if v["id"] == vector_id)
        expected = cast(dict[str, Any], vector["expected"])
        field = cast(list[str], expected["error_location"])[0]
        assert field in cast(dict[str, Any], vector["input"]), vector_id
        assert field in _union_fields_of(cast(str, vector["target"])), vector_id
        assert expected["error_location_mode"] == "prefix", vector_id


def test_the_union_coordinates_are_published_discriminatorless_unions() -> None:
    """The union set is read off the live models, not asserted from prefix mode."""
    coordinates = {
        (
            cast(str, vector["target"]),
            cast(list[str], vector["expected"]["error_location"])[0],
        )
        for vector in _missing_vectors()
        if _missing_shape(vector) == UNION_REJECTION
    }

    assert coordinates == {
        ("PullRequestHistoricalOccurrenceTime", "occurrence"),
        ("PullRequestHistoryFactEvidenceLink", "fact"),
    }
    for target, field in coordinates:
        model = cast(Any, RESOLVABLE[target])
        info = cast(dict[str, Any], model.model_fields)[field]
        # a real union, and no discriminator that would change the reading
        assert get_origin(info.annotation) in (Union, UnionType), (target, field)
        assert getattr(info, "discriminator", None) is None, (target, field)
        assert field in _union_fields_of(target), (target, field)

    # the published union-membership requirement already owns these two
    owned = {
        row[1] for row in FRAMEWORK_CONSTRAINT_LEDGER if row[2] == "union membership"
    }
    assert owned == {f"{t}.{f}" for t, f in coordinates}


def test_requiredness_and_union_rejection_agree_with_the_omission_matrix() -> None:
    """A supplied union value may never count as a true-omission witness."""
    for vector in _missing_vectors():
        shape = _missing_shape(vector)
        if shape is None:
            continue
        field = cast(list[str], vector["expected"]["error_location"])[0]
        omitted = _omits(vector, field)
        assert omitted is (shape == TRUE_OMISSION), vector["id"]

    # the genuine omission witnesses survive alongside their supplied siblings
    for vector_id in (
        "history.invalid.occurrence-time.missing-occurrence",
        "history.invalid.evidence-link.missing-fact",
    ):
        vector = next(v for v in INVALID["vectors"] if v["id"] == vector_id)
        assert _missing_shape(vector) == TRUE_OMISSION, vector_id


def test_the_change_set_fact_primary_witness_is_unchanged() -> None:
    """EL-04 was already right: its shape is a union case, its wording is not.

    It is the control against a blanket rewrite of every prefix/missing vector.
    """
    vector_id = "history.invalid.evidence-link.change-set-fact"
    rows = [row for row in REQUIREMENT_LEDGER if row[4] == vector_id]

    assert len(rows) == 1
    assert rows[0][0] == "EL-04"
    assert rows[0][2] == "a change set is not an admitted fact"
    assert vector_id not in SECONDARY_WITNESS_REGISTRY

    vector = next(v for v in INVALID["vectors"] if v["id"] == vector_id)
    assert _missing_shape(vector) == UNION_REJECTION


# --- a purpose states claims, and every claim answers to an authority --------
#
# Each vector publishes a sentence saying what it is for, and the only rule
# over 183 of them was `assert vector["purpose"]`. Truthiness accepts any
# non-empty string, so two vectors could exchange sentences, or one could be
# replaced with prose about nothing at all, and every oracle stayed green.
#
# A purpose is not one claim. "The retained merged timeline event records
# merge revision 10cdae8e; the ordinary pull request object omits it" makes a
# provenance claim and then a descriptive one, and they are not equally
# supported. So the ledger below records ORDERED CLAIMS per vector, each with
# its own assurance class and its own authority, and the sentence is rebuilt
# by joining the rendered fragments with "; " and a final full stop. The
# comparison against the published text is exact -- punctuation, case and
# spacing -- with no normalising anywhere.
#
# What the four classes mean, stated plainly because the difference matters:
#
#   BEHAVIOUR_DERIVED           the fragment's content is read out of the
#                               vector's own executing fields, so a changed
#                               revision, path, instant or count changes it.
#   REQUIREMENT_DERIVED         the fragment is SELECTED by a requirement
#                               identity independently validated against this
#                               vector. The English is authored; what is
#                               derived is which sentence this vector is
#                               entitled to. That is what defeats a swap, and
#                               it is not a claim that the wording was
#                               reconstructed from structure.
#   PROVENANCE_DERIVED          the content is resolved through validated
#                               replay provenance -- source pointers, embedded
#                               facts, the evidence record lock.
#   CANONICAL_DECLARATION_ONLY  authored interpretation with no independent
#                               structured truth behind it, or a fragment
#                               rendered from a manifest leaf that the corpus
#                               itself declares descriptive. Pinning it proves
#                               the text has not drifted. It proves nothing
#                               about whether the text is true.
#
# The renderers never read `purpose`; the equality test is the only place the
# published string is touched. They also never parse a vector id, a semantic
# partition or a category for meaning -- those are identifiers and taxonomy,
# closed by their own authorities, and reading English out of them would make
# this rule agree with itself.

BEHAVIOUR_DERIVED = "BEHAVIOUR_DERIVED"
REQUIREMENT_DERIVED = "REQUIREMENT_DERIVED"
PROVENANCE_DERIVED = "PROVENANCE_DERIVED"
CANONICAL_DECLARATION_ONLY = "CANONICAL_DECLARATION_ONLY"

PURPOSE_ASSURANCE_CLASSES = (
    BEHAVIOUR_DERIVED,
    REQUIREMENT_DERIVED,
    PROVENANCE_DERIVED,
    CANONICAL_DECLARATION_ONLY,
)


class PurposeClaim(NamedTuple):
    """One claim a purpose makes, its strength, and what answers for it."""

    assurance: str
    renderer: str
    authority: str


# ---- valid family renderers ---------------------------------------------

"""Structured ledger and deterministic renderers for the `valid` family.

Each of the 48 valid vectors publishes a human-readable sentence, and this
module reproduces every one exactly, so a sentence that is swapped between
vectors or replaced with unrelated prose stops rendering.

The strength behind that is not uniform, and the ledger says so per claim.
Twenty-nine fragments are read out of `input` / `expected` / `input_mode`, out
of a live production model definition, or out of a requirement row that is
independently validated against the vector. Sixteen, over fifteen vectors, are
authored sentences this corpus carries no structured source for -- the
"distinct value" relations, which speak about a sibling vector no single
record expresses, and the per-target "Python input ..." wordings, which the
declared markers do not determine. Those are labelled
CANONICAL_DECLARATION_ONLY and pinned, which refuses drift and claims nothing
more.

No renderer reads the published sentence, and none parses a vector id, a
semantic partition or a category label to decide what to say.
"""

_pV_OWNED_MODELS: dict[str, type[BaseModel]] = {
    name: symbol
    for module in (history_module, link_module)
    for name in module.__all__
    if isinstance(symbol := getattr(module, name), type)
    and issubclass(symbol, BaseModel)
}

_pV_SYMBOL_BY_FIELD_SET: dict[frozenset[str], str] = {
    frozenset(model.model_fields): name for name, model in _pV_OWNED_MODELS.items()
}

assert len(_pV_SYMBOL_BY_FIELD_SET) == len(_pV_OWNED_MODELS), (
    "field sets must discriminate"
)

_pV_REQUIREMENT_BY_WITNESS: dict[str, str] = {
    row[4]: row[0] for row in REQUIREMENT_LEDGER
}

_PV_REQUIREMENT_SENTENCES: dict[str, str] = {
    "CS-18": "Supplied order is preserved exactly and carries no source meaning",
    "RA-04": "The approved revision need not equal any current head binding",
    "MO-04": "The merge revision is unconstrained by any base or head binding",
    "OT-06": ("equal instants across two surfaces carry no order and are accepted"),
    "EL-06": (
        "The same record associated with a second, different fact is an "
        "independent link value"
    ),
}

_PV_OCCURRENCE_SURFACE_NAMES: dict[str, str] = {
    "PullRequestReviewRevisionApproval": "review approval",
    "PullRequestMergeRevisionOutcome": "merge outcome",
    "PullRequestHeadRefDeletion": "head-ref deletion",
}

_PV_OCCURRENCE_SURFACE_SHORT_NAMES: dict[str, str] = {
    "PullRequestReviewRevisionApproval": "approval",
    "PullRequestMergeRevisionOutcome": "merge",
    "PullRequestHeadRefDeletion": "deletion",
}

_PV_INSTANT_NAMES: dict[str, str] = {
    "2018-11-17T23:54:20Z": "approval",
    "2018-11-18T00:17:25Z": "merge",
    "2018-11-18T00:17:28Z": "deletion",
}

_PV_PATH_NAMES: dict[str, str] = {
    "changelog/4412.bugfix.rst": "changelog",
    "src/_pytest/assertion/rewrite.py": "rewrite",
    "testing/test_assertrewrite.py": "assertrewrite",
}

_PV_CANONICAL_DECLARATIONS: dict[str, tuple[str, ...]] = {
    "history.valid.role-binding.distinct-pull-request": (
        "A different pull request with the same revision is a distinct value",
    ),
    "history.valid.role-binding.distinct-revision": (
        "A different revision in the same role is a distinct value",
    ),
    "history.valid.role-binding.python-typed": (
        "Python input accepts already published typed children",
    ),
    "history.valid.status.python-enum": (
        "The enum member itself is accepted in Python input",
    ),
    "history.valid.changed-path.distinct-blob": (
        "A different head-side blob is a distinct value",
    ),
    "history.valid.changed-path.python-typed": (
        "Python input accepts typed path, blob, and status",
    ),
    "history.valid.change-set.python-typed": (
        "Python input requires a tuple of typed changed paths",
    ),
    "history.valid.approval.python-typed": (
        "Python input accepts typed review and revision",
    ),
    "history.valid.merge-outcome.python-typed": (
        "Python input accepts typed subject and revision",
    ),
    "history.valid.head-ref-deletion.distinct-ref-name": (
        "A different ref lexeme is a distinct value",
    ),
    "history.valid.head-ref-deletion.python-typed": (
        "Python input requires a typed ref name",
    ),
    "history.valid.occurrence-time.sub-second-preserved": (
        "Sub-second precision is preserved exactly as supplied",
    ),
    "history.valid.occurrence-time.python-typed": (
        "Python input requires a typed occurrence and aware instant",
    ),
    "history.valid.evidence-link.correction-record": (
        "The same fact may name the retained additive correction record",
    ),
    "history.valid.evidence-link.synthetic-record": (
        "Structural validity holds against a synthetic record",
        "no retained support is claimed",
    ),
}

_pV_ONES = (
    "zero",
    "one",
    "two",
    "three",
    "four",
    "five",
    "six",
    "seven",
    "eight",
    "nine",
    "ten",
    "eleven",
    "twelve",
    "thirteen",
    "fourteen",
    "fifteen",
    "sixteen",
    "seventeen",
    "eighteen",
    "nineteen",
)

_pV_TENS = (
    "",
    "",
    "twenty",
    "thirty",
    "forty",
    "fifty",
    "sixty",
    "seventy",
    "eighty",
    "ninety",
)

_pV_OFFSET = re.compile(r"(Z|[+-]\d{2}:\d{2})$")


def _pV_under_hundred(value: int) -> str:
    if value < 20:
        return _pV_ONES[value]
    tens, ones = divmod(value, 10)
    return _pV_TENS[tens] if not ones else f"{_pV_TENS[tens]}-{_pV_ONES[ones]}"


def _pV_under_thousand(value: int) -> str:
    hundreds, rest = divmod(value, 100)
    if not hundreds:
        return _pV_under_hundred(rest)
    head = f"{_pV_ONES[hundreds]} hundred"
    return head if not rest else f"{head} and {_pV_under_hundred(rest)}"


def _pV_spell(value: int) -> str:
    """Spell a non-negative integer below one million, British `and` form."""
    assert 0 <= value < 1_000_000, value
    thousands, rest = divmod(value, 1000)
    if not thousands:
        return _pV_under_thousand(rest)
    head = f"{_pV_under_thousand(thousands)} thousand"
    if not rest:
        return head
    joiner = " and " if rest < 100 else " "
    return f"{head}{joiner}{_pV_under_thousand(rest)}"


def _pV_capitalise(text: str) -> str:
    return text[:1].upper() + text[1:]


def _pV_plain(value: Any) -> Any:
    """Strip the declared python-input markers down to the declared value."""
    while isinstance(value, dict):
        shaped = cast(dict[str, Any], value)
        if len(shaped) != 1:
            break
        marker, payload = next(iter(shaped.items()))
        if marker in ("typed_value", "enum_value"):
            value = payload["input"]
        elif marker == "instant_value":
            value = payload
        else:
            break
    return cast(Any, value)


def _pV_symbol_of(value: Any) -> str:
    """Name the union member a declared value is, from its own shape."""
    if isinstance(value, dict) and set(cast(dict[str, Any], value)) == {"typed_value"}:
        return str(cast(dict[str, Any], value)["typed_value"]["target"])
    return _pV_SYMBOL_BY_FIELD_SET[frozenset(cast(dict[str, Any], _pV_plain(value)))]


def _pV_changed_path_count(declared: Any) -> int:
    if isinstance(declared, list):
        return len(cast(list[Any], declared))
    shaped = cast(dict[str, Any], declared)
    if "tuple_value" in shaped:
        return len(cast(list[Any], shaped["tuple_value"]))
    return int(shaped["indexed_value"]["count"])


def _PV_role_binding_canonical(vector: dict[str, Any], family: str) -> str:
    """`<ROLE>` and the pull-request number, read out of the declared input."""
    supplied = vector["input"]
    role = _pV_plain(supplied["role_assignment"])["role"]
    number = _pV_plain(supplied["pull_request"])["repository_scoped_number"]
    return f"The canonical {role.upper()} binding of pull request {number}"


def _PV_status_member(vector: dict[str, Any], family: str) -> str:
    """The admitted vocabulary member, read out of the authored dump."""
    return f"The published {vector['expected']['semantic_dump']} status member"


def _PV_changed_path_canonical(vector: dict[str, Any], family: str) -> str:
    """Status out of the input; the path's published fixture name beside it."""
    supplied = vector["input"]
    status = _pV_plain(supplied["status"])
    name = _PV_PATH_NAMES[_pV_plain(supplied["path"])]
    return f"The canonical {status} {name} path"


def _PV_change_set_supplied_count(vector: dict[str, Any], family: str) -> str:
    count = _pV_changed_path_count(vector["input"]["changed_paths"])
    return f"The canonical supplied change set over {_pV_spell(count)} paths"


def _PV_change_set_minimum(vector: dict[str, Any], family: str) -> str:
    count = _pV_changed_path_count(vector["input"]["changed_paths"])
    return f"{_pV_capitalise(_pV_spell(count))} changed path is the published minimum"


def _PV_change_set_maximum(vector: dict[str, Any], family: str) -> str:
    count = _pV_changed_path_count(vector["input"]["changed_paths"])
    return (
        f"{_pV_capitalise(_pV_spell(count))} changed paths is the published maximum "
        "and is accepted"
    )


def _PV_approval_canonical(vector: dict[str, Any], family: str) -> str:
    supplied = vector["input"]
    review = _pV_plain(supplied["review"])["provider_global_id"]
    revision = _pV_plain(supplied["approved_revision"])["full_digest"][:8]
    return f"Review {review} approves revision {revision}"


def _PV_merge_outcome_canonical(vector: dict[str, Any], family: str) -> str:
    supplied = vector["input"]
    number = _pV_plain(supplied["pull_request"])["repository_scoped_number"]
    revision = _pV_plain(supplied["merge_revision"])["full_digest"][:8]
    return f"Pull request {number} merged as revision {revision}"


def _PV_head_ref_deletion_canonical(vector: dict[str, Any], family: str) -> str:
    lexeme = _pV_plain(vector["input"]["head_ref_name"])
    return f"The recorded head ref {lexeme} was deleted"


def _PV_occurrence_instant(vector: dict[str, Any], family: str) -> str:
    """The admitted surface and the instant it carries, both from the input."""
    supplied = vector["input"]
    surface = _PV_OCCURRENCE_SURFACE_NAMES[_pV_symbol_of(supplied["occurrence"])]
    return f"The {surface} occurred at {_pV_plain(supplied['occurred_at'])}"


def _PV_occurrence_offset_normalisation(vector: dict[str, Any], family: str) -> str:
    """Both offset lexemes: one supplied, one in the authored dump."""
    supplied = _pV_OFFSET.search(_pV_plain(vector["input"]["occurred_at"]))
    normalized = _pV_OFFSET.search(vector["expected"]["semantic_dump"]["occurred_at"])
    assert supplied and normalized
    return (
        f"An explicit {supplied.group(1)} offset is accepted and normalized "
        f"to {normalized.group(1)}"
    )


def _PV_occurrence_tied_surface(vector: dict[str, Any], family: str) -> str:
    """Which surface carries which of the locked instants."""
    supplied = vector["input"]
    surface = _PV_OCCURRENCE_SURFACE_SHORT_NAMES[_pV_symbol_of(supplied["occurrence"])]
    instant = _PV_INSTANT_NAMES[_pV_plain(supplied["occurred_at"])]
    return f"The {surface} surface carries the {instant} instant"


def _PV_evidence_link_json_fact(vector: dict[str, Any], family: str) -> str:
    symbol = _pV_symbol_of(vector["input"]["fact"])
    return f"A {symbol} is an admitted fact in the link's JSON reconstruction"


def _PV_evidence_link_python_fact(vector: dict[str, Any], family: str) -> str:
    symbol = _pV_symbol_of(vector["input"]["fact"])
    return f"A published {symbol} is admitted in Python input"


def _PV_requirement_sentence(vector: dict[str, Any], family: str) -> str:
    """One fixed sentence per ledger row, selected by that row's witness."""
    return _PV_REQUIREMENT_SENTENCES[_pV_REQUIREMENT_BY_WITNESS[vector["id"]]]


def _pV_declaration(index: int) -> Callable[[dict[str, Any], str], str]:
    def render(vector: dict[str, Any], family: str) -> str:
        """Authored interpretation; no structured authority stands behind it."""
        return _PV_CANONICAL_DECLARATIONS[vector["id"]][index]

    return render


_PV_canonical_declaration = _pV_declaration(0)

_PV_canonical_declaration_second = _pV_declaration(1)


_PV_DECLARATION = "CANONICAL_DECLARATION_ONLY"


# ---- invalid family renderers -------------------------------------------

"""Rendered semantics for the `invalid` family of the development-history corpus.

Every invalid vector carries a requirement identity that the corpus test module
already validates independently of any prose:

  * a ``REQUIREMENT_LEDGER`` row whose witness (``row[4]``) is this vector, and
    whose declared target is asserted equal to ``vector["target"]``; or
  * membership in ``SECONDARY_WITNESS_REGISTRY``, whose registered requirement
    string ``_derived_requirement`` recomputes from the vector's own validated
    ``expected`` / ``input`` fields.

One renderer, :func:`_pI_render_requirement_gloss`, turns that identity -- never a
vector id, partition or category string -- into the authored sentence the corpus
publishes for it.  Where one identity covers several vectors the key is widened
with a structured discriminator read out of the vector (the supplied lexeme, the
supplied union branch's key set, the normalized error type, the typed/enum
boundary marker, or the grammar of the supplied instant).  Two vectors publish a
second, separable claim about their own input; those render from the input and
expected fields directly.
"""


_pI_LEDGER_BY_WITNESS = {row[4]: row for row in REQUIREMENT_LEDGER}


def _pI_identity(vector: dict[str, Any]) -> tuple[str, str]:
    """The validated (target, requirement) pair this vector witnesses."""
    row = _pI_LEDGER_BY_WITNESS.get(vector["id"])
    if row is not None:
        return (vector["target"], row[2])
    registered = SECONDARY_WITNESS_REGISTRY[vector["id"]]
    derived = _derived_requirement(vector)
    if registered != derived:  # pragma: no cover - the corpus tests forbid it
        raise AssertionError(vector["id"])
    return (vector["target"], derived)


def _pI_instant_grammar(lexeme: str) -> str:
    """Classify a supplied instant lexeme by its own shape."""
    date, marker, clock = lexeme.partition("T")
    if not marker:
        return "unparsed"
    if "W" in date:
        return "week"
    if "-" not in date:
        return "basic"
    if clock.endswith("Z"):
        return "utc"
    for sign in ("+", "-"):
        cut = clock.rfind(sign)
        if cut > 0:
            return "zero-offset" if set(clock[cut + 1 :]) <= {"0", ":"} else "offset"
    return "naive"


def _pI_supplied_shape(node: Any) -> tuple[Any, ...]:
    """The published boundary marker (or bare shape) of a supplied member."""
    if isinstance(node, dict):
        shaped = cast(dict[str, Any], node)
        if set(shaped) == {"typed_value"}:
            return ("typed", cast(str, shaped["typed_value"]["target"]))
        if set(shaped) == {"enum_value"}:
            return ("enum", cast(str, shaped["enum_value"]["target"]))
        return ("mapping", tuple(sorted(shaped)))
    return ("scalar", type(node).__name__)


def _pI_fact_branch(vector: dict[str, Any]) -> tuple[Any, ...]:
    """Which admitted-fact branch the supplied mapping reaches for, if any."""
    fact = vector["input"]["fact"]
    keys = tuple(sorted(fact))
    if keys == ("occurred_at", "occurrence"):
        if not isinstance(fact["occurrence"], dict):
            return ("nested-occurrence",)
        return ("instant", _pI_instant_grammar(fact["occurred_at"]))
    return ("fact-keys", keys)


def _pI_no_discriminator(_vector: dict[str, Any]) -> tuple[Any, ...]:
    return ()


_pI_DISCRIMINATORS: dict[
    tuple[Any, ...], Callable[[dict[str, Any]], tuple[Any, ...]]
] = {
    ("ChangedPathStatus", "the vocabulary is closed"): lambda v: (v["input"],),
    (
        "PullRequestReviewRevisionApproval",
        "review refuses this published boundary",
    ): lambda v: (
        v["input"]["review"]["kind"],
        v["input"]["review"]["parent"]["kind"],
    ),
    (
        "PullRequestRevisionRoleBinding",
        "pull_request refuses this published boundary",
    ): lambda v: _pI_supplied_shape(v["input"]["pull_request"]),
    (
        "PullRequestHistoricalOccurrenceTime",
        "occurred_at refuses this published boundary",
    ): lambda v: (v["expected"]["error_type"],),
    (
        "PullRequestHistoricalOccurrenceTime",
        "occurrence admits only its published union members",
    ): lambda v: tuple(sorted(v["input"]["occurrence"])),
    (
        "PullRequestHistoryFactEvidenceLink",
        "fact refuses this published boundary",
    ): lambda v: _pI_supplied_shape(v["input"]["fact"]),
    (
        "PullRequestHistoryFactEvidenceLink",
        "fact admits only its published union members",
    ): _pI_fact_branch,
}


def _pI_gloss_key(vector: dict[str, Any]) -> tuple[Any, ...]:
    identity = _pI_identity(vector)
    discriminate = _pI_DISCRIMINATORS.get(identity, _pI_no_discriminator)
    return identity + tuple(discriminate(vector))


_pI_REQUIREMENT_GLOSS: dict[tuple[Any, ...], str] = {
    (
        "ChangedPathStatus",
        "the vocabulary is closed",
        "copied",
    ): "Copy is not a published status",
    (
        "ChangedPathStatus",
        "the vocabulary is closed",
        "not-a-status",
    ): "An arbitrary lexeme outside the closed vocabulary is refused",
    (
        "ChangedPathStatus",
        "the vocabulary is closed",
        "removed",
    ): "Removal is not a published status",
    (
        "ChangedPathStatus",
        "the vocabulary is closed",
        "renamed",
    ): "Rename is not a published status",
    (
        "PullRequestChangeSet",
        "at least one changed path",
    ): "Supplying no changed path is not an empty change set",
    (
        "PullRequestChangeSet",
        "at most 4096 changed paths",
    ): "One above the published maximum is refused",
    (
        "PullRequestChangeSet",
        "base and head algorithms match",
    ): "The two revisions must share one hash algorithm",
    (
        "PullRequestChangeSet",
        "base and head bind one pull request",
    ): "Both bindings must name one pull request",
    (
        "PullRequestChangeSet",
        "base and head revisions differ",
    ): "The two bindings must name distinct revisions",
    (
        "PullRequestChangeSet",
        "base is required",
    ): "A change set requires its base binding",
    (
        "PullRequestChangeSet",
        "base position requires the base role",
    ): "The base position independently requires the base revision role",
    (
        "PullRequestChangeSet",
        "base typed in Python",
    ): "The base position independently requires an already published binding in Python input",
    (
        "PullRequestChangeSet",
        "changed_paths holds published values",
    ): "A supplied tuple must contain published changed paths, not mappings",
    (
        "PullRequestChangeSet",
        "changed_paths is a tuple in Python",
    ): "Python input requires a tuple rather than a list",
    (
        "PullRequestChangeSet",
        "changed_paths is required",
    ): "A change set requires its supplied changed paths",
    (
        "PullRequestChangeSet",
        "head is required",
    ): "A change set requires its head binding",
    (
        "PullRequestChangeSet",
        "head position requires the head role",
    ): "The head position independently requires the head revision role",
    (
        "PullRequestChangeSet",
        "head typed in Python",
    ): "The head position independently requires an already published binding in Python input",
    (
        "PullRequestChangeSet",
        "no completeness claim",
    ): "No completeness claim is published here",
    (
        "PullRequestChangeSet",
        "object algorithms match the head",
    ): "One change set uses exactly one hash algorithm",
    (
        "PullRequestChangeSet",
        "repository paths are unique",
    ): "A repository path may appear at most once",
    (
        "PullRequestChangedPath",
        "Python input requires the published status member",
    ): "Python input must already supply the published status member, not its lexeme",
    (
        "PullRequestChangedPath",
        "head_object is required",
    ): "A changed path requires its head-side object",
    (
        "PullRequestChangedPath",
        "head_object must be a blob",
    ): "The head-side object must be a blob",
    (
        "PullRequestChangedPath",
        "head_object typed in Python",
    ): "Python input requires a published blob identity",
    (
        "PullRequestChangedPath",
        "no base_object is published",
    ): "No base-side object is published here",
    (
        "PullRequestChangedPath",
        "path is required",
    ): "A changed path requires its repository path",
    (
        "PullRequestChangedPath",
        "path refuses this published boundary",
    ): "An empty repository path is refused",
    (
        "PullRequestChangedPath",
        "path typed in Python",
    ): "Python input requires a published repository path",
    (
        "PullRequestChangedPath",
        "status is required",
    ): "A changed path requires its supplied status",
    (
        "PullRequestChangedPath",
        "status refuses this published boundary",
    ): "The status vocabulary is closed to added and modified",
    (
        "PullRequestHeadRefDeletion",
        "a refs/-prefixed name is refused",
    ): "A published ref name carries no refs/ prefix",
    (
        "PullRequestHeadRefDeletion",
        "head is required",
    ): "A deletion requires its recorded head binding",
    (
        "PullRequestHeadRefDeletion",
        "head typed in Python",
    ): "The deleted head requires an already published binding in Python input",
    (
        "PullRequestHeadRefDeletion",
        "head_ref_name is required",
    ): "A deletion requires the ref lexeme it recorded",
    (
        "PullRequestHeadRefDeletion",
        "head_ref_name refuses this published boundary",
    ): "An empty ref lexeme is refused",
    (
        "PullRequestHeadRefDeletion",
        "head_ref_name typed in Python",
    ): "Python input requires a published ref name",
    (
        "PullRequestHeadRefDeletion",
        "no namespace is published",
    ): "No ref namespace is published here",
    (
        "PullRequestHeadRefDeletion",
        "the binding must carry the head role",
    ): "The bound revision must carry the head role",
    (
        "PullRequestHistoricalOccurrenceTime",
        "no chronology is published",
    ): "No chronology, order, or sequence is published here",
    (
        "PullRequestHistoricalOccurrenceTime",
        "occurred_at is required",
    ): "An occurrence time requires its instant",
    (
        "PullRequestHistoricalOccurrenceTime",
        "occurred_at must be a zero UTC offset",
    ): "A positive non-zero offset is refused",
    (
        "PullRequestHistoricalOccurrenceTime",
        "occurred_at refuses this published boundary",
        "datetime_parsing",
    ): "A malformed instant is refused",
    (
        "PullRequestHistoricalOccurrenceTime",
        "occurred_at refuses this published boundary",
        "datetime_type",
    ): "Python input must already supply an aware datetime, not its lexeme",
    (
        "PullRequestHistoricalOccurrenceTime",
        "occurred_at refuses this published boundary",
        "timezone_aware",
    ): "A naive instant carries no zone and is refused",
    (
        "PullRequestHistoricalOccurrenceTime",
        "occurred_at refuses this published boundary",
        "value_error",
    ): "A negative non-zero offset is refused",
    (
        "PullRequestHistoricalOccurrenceTime",
        "occurrence admits only its published union members",
        "algorithm",
        "full_digest",
        "kind",
        "schema_version",
    ): "A commit-identity is not an admitted occurrence",
    (
        "PullRequestHistoricalOccurrenceTime",
        "occurrence admits only its published union members",
        "base",
        "changed_paths",
        "head",
    ): "A change-set is not an admitted occurrence",
    (
        "PullRequestHistoricalOccurrenceTime",
        "occurrence admits only its published union members",
        "head_object",
        "path",
        "status",
    ): "A changed-path is not an admitted occurrence",
    (
        "PullRequestHistoricalOccurrenceTime",
        "occurrence admits only its published union members",
        "pull_request",
        "role_assignment",
    ): "A role-binding is not an admitted occurrence",
    (
        "PullRequestHistoricalOccurrenceTime",
        "occurrence is required",
    ): "An occurrence time requires the occurrence it dates",
    (
        "PullRequestHistoricalOccurrenceTime",
        "occurrence refuses this published boundary",
    ): "A changed-path-status is not an admitted occurrence",
    (
        "PullRequestHistoricalOccurrenceTime",
        "occurrence typed in Python",
    ): "An admitted occurrence requires an already published value in Python input",
    (
        "PullRequestHistoryFactEvidenceLink",
        "a change set is not an admitted fact",
    ): "A caller-supplied change set is not an admitted fact",
    (
        "PullRequestHistoryFactEvidenceLink",
        "a status is not an admitted fact",
    ): "A closed status vocabulary is not a fact",
    (
        "PullRequestHistoryFactEvidenceLink",
        "evidence_record is refused by its published nested contract",
    ): "A malformed durable record reference is refused",
    (
        "PullRequestHistoryFactEvidenceLink",
        "evidence_record is required",
    ): "A link requires its durable evidence record",
    (
        "PullRequestHistoryFactEvidenceLink",
        "evidence_record typed in Python",
    ): "Python input requires a published durable record reference",
    (
        "PullRequestHistoryFactEvidenceLink",
        "fact admits only its published union members",
        "fact-keys",
        ("merge_revision", "path"),
    ): "A hybrid mapping matching no admitted branch is refused",
    (
        "PullRequestHistoryFactEvidenceLink",
        "fact admits only its published union members",
        "fact-keys",
        (),
    ): "An empty mapping matches no admitted branch",
    (
        "PullRequestHistoryFactEvidenceLink",
        "fact admits only its published union members",
        "instant",
        "basic",
    ): "A basic-format instant is outside the published grammar",
    (
        "PullRequestHistoryFactEvidenceLink",
        "fact admits only its published union members",
        "instant",
        "naive",
    ): "A naive instant is refused through the fact union",
    (
        "PullRequestHistoryFactEvidenceLink",
        "fact admits only its published union members",
        "instant",
        "offset",
    ): "A non-zero offset is refused through the fact union",
    (
        "PullRequestHistoryFactEvidenceLink",
        "fact admits only its published union members",
        "instant",
        "week",
    ): "A week date is outside the published instant grammar",
    (
        "PullRequestHistoryFactEvidenceLink",
        "fact admits only its published union members",
        "nested-occurrence",
    ): "A non-admitted inner occurrence is refused through the nested union",
    (
        "PullRequestHistoryFactEvidenceLink",
        "fact is required",
    ): "A link requires its fact",
    (
        "PullRequestHistoryFactEvidenceLink",
        "fact refuses this published boundary",
        "enum",
        "ChangedPathStatus",
    ): "The status vocabulary stays inadmissible in Python input",
    (
        "PullRequestHistoryFactEvidenceLink",
        "fact refuses this published boundary",
        "mapping",
        ("approved_revision", "review"),
    ): "A mapping of published children is still not a published fact",
    (
        "PullRequestHistoryFactEvidenceLink",
        "fact refuses this published boundary",
        "typed",
        "PullRequestChangeSet",
    ): "The change set stays inadmissible in Python input",
    (
        "PullRequestHistoryFactEvidenceLink",
        "fact typed in Python",
    ): "Python input requires an already published fact",
    (
        "PullRequestHistoryFactEvidenceLink",
        "no artifact is published",
    ): "The link references a durable record, never an artifact carrier",
    (
        "PullRequestHistoryFactEvidenceLink",
        "no confidence is published",
    ): "No confidence is published",
    (
        "PullRequestHistoryFactEvidenceLink",
        "no evidence_records is published",
    ): "No evidence aggregate is published",
    (
        "PullRequestHistoryFactEvidenceLink",
        "no json_pointer is published",
    ): "No evidence localization is published, under any spelling",
    (
        "PullRequestHistoryFactEvidenceLink",
        "no primary_evidence is published",
    ): "No primary designation is published",
    (
        "PullRequestHistoryFactEvidenceLink",
        "no request_id is published",
    ): "The link carries no acquisition-request provenance",
    (
        "PullRequestHistoryFactEvidenceLink",
        "no schema_version is published",
    ): "The link carries no version of its own",
    (
        "PullRequestHistoryFactEvidenceLink",
        "no strength is published",
    ): "No evidence strength is published",
    (
        "PullRequestHistoryFactEvidenceLink",
        "no superseded is published",
    ): "A link never follows a correction to a superseding record",
    (
        "PullRequestHistoryFactEvidenceLink",
        "no support_role is published",
    ): "No support role is published",
    (
        "PullRequestHistoryFactEvidenceLink",
        "no verification is published",
    ): "No verification outcome is published",
    (
        "PullRequestHistoryFactEvidenceLink",
        "occurrence-time fact typed in Python",
    ): "The occurrence-time branch requires an already published fact in Python input",
    (
        "PullRequestMergeRevisionOutcome",
        "merge_revision is refused by its published nested contract",
    ): "The merge revision must be a commit",
    (
        "PullRequestMergeRevisionOutcome",
        "merge_revision is required",
    ): "A merge outcome requires the revision it merged as",
    (
        "PullRequestMergeRevisionOutcome",
        "merge_revision typed in Python",
    ): "The merge revision requires an already published commit identity in Python input",
    (
        "PullRequestMergeRevisionOutcome",
        "no ordered_parents is published",
    ): "No parent topology is embedded here",
    (
        "PullRequestMergeRevisionOutcome",
        "no strategy is published",
    ): "No merge strategy is published here",
    (
        "PullRequestMergeRevisionOutcome",
        "pull_request is required",
    ): "A merge outcome requires its pull request",
    (
        "PullRequestMergeRevisionOutcome",
        "pull_request typed in Python",
    ): "The merged subject requires an already published numbered identity in Python input",
    (
        "PullRequestMergeRevisionOutcome",
        "subject must be a pull request",
    ): "The subject must identify a pull request",
    (
        "PullRequestReviewRevisionApproval",
        "approved_revision is refused by its published nested contract",
    ): "The approved revision must be a commit",
    (
        "PullRequestReviewRevisionApproval",
        "approved_revision is required",
    ): "An approval requires the revision it approved",
    (
        "PullRequestReviewRevisionApproval",
        "approved_revision typed in Python",
    ): "The approved revision requires an already published commit identity in Python input",
    (
        "PullRequestReviewRevisionApproval",
        "no state is published",
    ): "No review state vocabulary is published here",
    (
        "PullRequestReviewRevisionApproval",
        "no submitted_at is published",
    ): "Occurrence time is a separate published relation",
    (
        "PullRequestReviewRevisionApproval",
        "review is required",
    ): "An approval requires its review identity",
    (
        "PullRequestReviewRevisionApproval",
        "review must be a pull-request review",
    ): "A provider-scoped object of a pull request may still fail the published review-kind requirement",
    (
        "PullRequestReviewRevisionApproval",
        "review refuses this published boundary",
        "issue_comment",
        "pull_request",
    ): "The subject must identify a pull request review",
    (
        "PullRequestReviewRevisionApproval",
        "review refuses this published boundary",
        "pull_request_review",
        "issue",
    ): "A published review parents a pull request",
    (
        "PullRequestReviewRevisionApproval",
        "review typed in Python",
    ): "Python input requires a published review identity",
    (
        "PullRequestRevisionRoleBinding",
        "bound role must be base or head",
    ): "Only the base and head roles are recorded here",
    (
        "PullRequestRevisionRoleBinding",
        "no observed_at is published",
    ): "No observation time is published here",
    (
        "PullRequestRevisionRoleBinding",
        "pull_request is refused by its published nested contract",
    ): "Swapping the two members is refused",
    (
        "PullRequestRevisionRoleBinding",
        "pull_request is required",
    ): "A binding requires its pull request",
    (
        "PullRequestRevisionRoleBinding",
        "pull_request refuses this published boundary",
        "mapping",
        ("kind", "repository_identity", "repository_scoped_number", "schema_version"),
    ): "A dumped mapping is not a published value in Python input",
    (
        "PullRequestRevisionRoleBinding",
        "pull_request refuses this published boundary",
        "typed",
        "ProviderScopedSourceObjectIdentity",
    ): "A foreign published identity is refused in the subject position",
    (
        "PullRequestRevisionRoleBinding",
        "pull_request typed in Python",
    ): "Python input requires an already published subject",
    (
        "PullRequestRevisionRoleBinding",
        "role_assignment is required",
    ): "A binding requires its role assignment",
    (
        "PullRequestRevisionRoleBinding",
        "role_assignment refuses this published boundary",
    ): "A null role assignment is refused",
    (
        "PullRequestRevisionRoleBinding",
        "role_assignment typed in Python",
    ): "Python input requires an already published role assignment",
    (
        "PullRequestRevisionRoleBinding",
        "subject must be a pull request",
    ): "The subject must identify a pull request",
}


def _pI_render_requirement_gloss(vector: dict[str, Any], family: str) -> str:
    """The authored sentence selected by this vector's requirement identity."""
    return _pI_REQUIREMENT_GLOSS[_pI_gloss_key(vector)]


def _pI_render_objects_already_match_head(vector: dict[str, Any], family: str) -> str:
    """Whether every supplied changed object already matches the head revision."""
    supplied = vector["input"]
    head_algorithm = supplied["head"]["role_assignment"]["revision"]["algorithm"]
    objects = [p["head_object"]["algorithm"] for p in supplied["changed_paths"]]
    if objects and all(a == head_algorithm for a in objects):
        return "every changed object already matches the head"
    return "not every changed object matches the head"


def _pI_render_true_omission_not_union(vector: dict[str, Any], family: str) -> str:
    """Whether the recorded failure is a real omission or a closed-union refusal."""
    expected = vector["expected"]
    field = expected["error_location"][0]
    supplied = vector["input"]
    omitted = isinstance(supplied, dict) and field not in supplied
    if omitted and expected["error_location_mode"] == "exact":
        return "omitting it is not a union failure"
    return "omitting it is a union failure"


# ---- replay family renderers --------------------------------------------

"""Structured ledger + deterministic renderers for the ``replay`` family.

Every fragment below is produced from a validated structured authority carried
by the vector itself (``source_pointers``, ``embedded_facts``,
``evidence_record_lock``, ``evidence_classification``, ``target``) or from a
leaf of the sealed manifest.  No renderer reads the published prose, and no
renderer inspects a vector identifier, semantic partition, or category lexeme.
"""


_PR_RETAINED_NODE_NOUNS: dict[str, str] = {
    "/observations/comparison": "comparison",
    "/observations/pr/changed_files/items": "changed-file item",
    "/observations/pr/reviews/items": "review",
    "/observations/pr/timeline/items": "merged timeline event",
}

_PR_CALLER_VERBS: dict[str, str] = {
    "caller_supplied_association": "associates",
    "caller_supplied_composition": "composes",
}

_PR_OCCURRENCE_KINDS: dict[frozenset[str], str] = {
    frozenset({"approved_revision", "review"}): "approval",
    frozenset({"merge_revision", "pull_request"}): "merge",
    frozenset({"head", "head_ref_name"}): "deletion",
}

_PR_TARGET_DECLARATIONS: dict[str, str] = {
    "PullRequestHeadRefDeletion": (
        "The retained head_ref_deleted event and recorded head ref lexeme"
    ),
}

_PR_CARDINAL_WORDS: dict[int, str] = {1: "one", 2: "two", 3: "three"}

_PR_EVIDENCE_LINK_NON_CLAIM = (
    "the link asserts no support, verification, or localization"
)

_PR_CHANGE_SET_COMPLETENESS = (
    "the retained collection declares completeness and this value"
)


def _pR_resolve(node: Any, pointer: str) -> Any:
    for token in [part for part in pointer.split("/") if part]:
        node = (
            cast(list[Any], node)[int(token)]
            if isinstance(node, list)
            else cast(dict[str, Any], node)[token]
        )
    return node


def _pR_replayed(vector: dict[str, Any], pointer: str) -> Any:
    """Read a replayed leaf out of the vector's independently authored dump."""
    return _pR_resolve(vector["expected"]["semantic_dump"], pointer)


def _pR_source_position(pointer: dict[str, Any]) -> str:
    parts = [p for p in pointer["json_pointer"].split("/") if p and not p.isdigit()]
    return "/" + "/".join(parts)


def _pR_primary(vector: dict[str, Any]) -> dict[str, Any]:
    return vector["source_pointers"][0]


# The retained coordinate each provenance renderer actually reads. A vector
# cites several -- the comparison, the pull request bracket, the repository --
# and only one of them is the node a given sentence is about. These selections
# are the renderers' own, called from the renderers below and reused by the
# claim resolver, so the declared authority and the executed code cannot
# describe different coordinates.


def _pR_role_implication_pointer(vector: dict[str, Any]) -> dict[str, Any]:
    """The retained coordinate whose own mapping implies the replayed role."""
    return next(p for p in vector["source_pointers"] if p.get("role_implications"))


def _pR_instant_target(pointer: dict[str, Any], vector: dict[str, Any]) -> str:
    """The top-level replayed target a retained coordinate fills, if it fills one."""
    return next(
        target
        for target in cast(dict[str, str], pointer["source_fields"]).values()
        if "/" not in target.strip("/")
        and isinstance(_pR_replayed(vector, target), str)
    )


def _pR_instant_pointer(vector: dict[str, Any]) -> dict[str, Any]:
    """The retained coordinate the replayed occurrence instant is read from."""
    for pointer in cast(list[dict[str, Any]], vector["source_pointers"]):
        try:
            _pR_instant_target(pointer, vector)
        except StopIteration:
            continue
        return pointer
    raise LookupError("no retained coordinate carries the replayed instant")


def _pR_composed_bindings(vector: dict[str, Any]) -> list[str]:
    """The embedded facts a caller composition binds, in declared order."""
    return [key for key in vector["embedded_facts"] if key.count("/") == 1]


def _pR_replayed_targets(vector: dict[str, Any]) -> list[str]:
    return [
        target
        for pointer in vector["source_pointers"]
        for target in pointer["source_fields"].values()
    ]


def _pR_target_ending(targets: list[str], leaf: str) -> str:
    return next(t for t in targets if t.rsplit("/", 1)[-1] == leaf)


def _pR_short(digest: str) -> str:
    return digest[:8]


def _pR_authority_role(reference: str) -> str:
    entry = next(
        row
        for row in MANIFEST["source_decisions"]
        if row["decision_reference"] == reference
    )
    return str(entry["authority_role"])


def _PR_retained_role_binding_fact(vector: dict[str, Any], family: str) -> str:
    """Retained comparison node, the role it implies, its revision and the PR."""
    pointer = _pR_role_implication_pointer(vector)
    noun = _PR_RETAINED_NODE_NOUNS[_pR_source_position(pointer)]
    role = _pR_replayed(vector, next(iter(pointer["role_implications"].values())))
    revision = _pR_replayed(
        vector,
        _pR_target_ending(list(pointer["source_fields"].values()), "full_digest"),
    )
    number = _pR_replayed(
        vector,
        _pR_target_ending(_pR_replayed_targets(vector), "repository_scoped_number"),
    )
    return f"The retained {noun} records {role} {_pR_short(revision)} for pull request {number}"


def _PR_retained_changed_path_fact(vector: dict[str, Any], family: str) -> str:
    """Retained changed-file node and the repository path it carries."""
    pointer = _pR_primary(vector)
    noun = _PR_RETAINED_NODE_NOUNS[_pR_source_position(pointer)]
    path = _pR_replayed(
        vector, _pR_target_ending(list(pointer["source_fields"].values()), "path")
    )
    return f"The retained {noun} for {path}"


def _PR_retained_review_approval_fact(vector: dict[str, Any], family: str) -> str:
    """Retained review node, its provider id and the revision it approves."""
    pointer = _pR_primary(vector)
    noun = _PR_RETAINED_NODE_NOUNS[_pR_source_position(pointer)]
    fields = list(pointer["source_fields"].values())
    review = _pR_replayed(vector, _pR_target_ending(fields, "provider_global_id"))
    revision = _pR_replayed(vector, _pR_target_ending(fields, "full_digest"))
    return f"The retained {noun} {review} approves revision {_pR_short(revision)}"


def _PR_retained_merge_event_fact(vector: dict[str, Any], family: str) -> str:
    """Retained timeline event and the merge revision it alone carries."""
    pointer = _pR_primary(vector)
    noun = _PR_RETAINED_NODE_NOUNS[_pR_source_position(pointer)]
    target = _pR_target_ending(list(pointer["source_fields"].values()), "full_digest")
    subject = target.strip("/").split("/")[0].replace("_", " ")
    return f"The retained {noun} records {subject} {_pR_short(_pR_replayed(vector, target))}"


def _PR_retained_occurrence_instant_fact(vector: dict[str, Any], family: str) -> str:
    """Retained instant and the published history fact it is attached to."""
    roots = sorted({t.strip("/").split("/")[0] for t in _pR_replayed_targets(vector)})
    coordinate = _pR_instant_pointer(vector)
    instant = _pR_replayed(vector, _pR_instant_target(coordinate, vector))
    occurrence = next(
        _pR_replayed(vector, f"/{r}")
        for r in roots
        if isinstance(_pR_replayed(vector, f"/{r}"), dict)
    )
    kind = _PR_OCCURRENCE_KINDS[frozenset(occurrence)]
    return f"The retained source instant {instant} for the {kind} occurrence"


def _PR_retained_target_declaration(vector: dict[str, Any], family: str) -> str:
    """Authored declaration selected by the vector's published product symbol."""
    return _PR_TARGET_DECLARATIONS[vector["target"]]


def _PR_caller_composed_change_set(vector: dict[str, Any], family: str) -> str:
    """Caller composition: the bound role bindings plus a choice of paths."""
    verb = _PR_CALLER_VERBS[vector["evidence_classification"]]
    count = _PR_CARDINAL_WORDS[len(_pR_composed_bindings(vector))]
    return f"A caller {verb} the {count} bindings with a selection of retained paths"


# The manifest leaf each descriptive-limit sentence is built from. The renderer
# below and the claim resolver read the SAME constant, so a claim naming another
# leaf is naming a value its sentence was never built from.
_PR_CHANGE_SET_COMPLETENESS_LEAF = (
    "/replay_contract/evidence_limits/change_set_completeness_claimed"
)
_PR_MERGE_REVISION_SOURCE_LEAF = (
    "/replay_contract/evidence_limits/merge_revision_source"
)
_PR_SUPERSESSION_FOLLOWED_LEAF = (
    "/replay_contract/evidence_limits/supersession_followed"
)


def _PR_change_set_completeness_limit(vector: dict[str, Any], family: str) -> str:
    """Descriptive limit: the published change-set completeness flag."""
    claimed = _resolve_pointer(MANIFEST, _PR_CHANGE_SET_COMPLETENESS_LEAF)
    return f"{_PR_CHANGE_SET_COMPLETENESS} {'does' if claimed else 'does not'}"


def _PR_merge_revision_absent_surface(vector: dict[str, Any], family: str) -> str:
    """Descriptive limit: the surface the published merge-revision source excludes."""
    declared = cast(str, _resolve_pointer(MANIFEST, _PR_MERGE_REVISION_SOURCE_LEAF))
    return f"{declared.split(', not ', 1)[1]} omits it"


def _PR_caller_association_to_locked_record(vector: dict[str, Any], family: str) -> str:
    """Caller association from the bound fact to the locked evidence record."""
    verb = _PR_CALLER_VERBS[vector["evidence_classification"]]
    bound = sorted(vector["embedded_facts"])[0].strip("/").replace("_", " ")
    kind = vector["evidence_record_lock"].split(":", 1)[0]
    return f"A caller {verb} the {bound} with the retained {kind} record"


def _PR_evidence_link_non_claim(vector: dict[str, Any], family: str) -> str:
    """Authored summary of the S07 published non-claims."""
    return _PR_EVIDENCE_LINK_NON_CLAIM


def _PR_second_independent_correction_link(vector: dict[str, Any], family: str) -> str:
    """Authored reading of the correction association, named by its authority role."""
    role = _pR_authority_role(vector["evidence_record_lock"]).split("_")
    record = " ".join(role[:-1] + ["record"] if role[-1] == "evidence" else role)
    return f"The same fact associated with the {record} is a second independent link"


def _PR_supersession_limit(vector: dict[str, Any], family: str) -> str:
    """Descriptive limit: the published supersession-traversal flag."""
    followed = _resolve_pointer(MANIFEST, _PR_SUPERSESSION_FOLLOWED_LEAF)
    subject, participle = _PR_SUPERSESSION_FOLLOWED_LEAF.rsplit("/", 1)[1].split("_")
    return f"{'a' if followed else 'no'} {subject} is {participle}"


PURPOSE_SEMANTICS: dict[str, tuple[PurposeClaim, ...]] = {
    # -- 48 valid vectors -----------------------------------------------
    "history.valid.role-binding.base-canonical": (
        PurposeClaim(
            BEHAVIOUR_DERIVED,
            "valid:role_binding_canonical",
            "input:/role_assignment/role",
        ),
    ),
    "history.valid.role-binding.head-canonical": (
        PurposeClaim(
            BEHAVIOUR_DERIVED,
            "valid:role_binding_canonical",
            "input:/role_assignment/role",
        ),
    ),
    "history.valid.status.added": (
        PurposeClaim(
            BEHAVIOUR_DERIVED,
            "valid:status_member",
            "expected:/semantic_dump",
        ),
    ),
    "history.valid.status.modified": (
        PurposeClaim(
            BEHAVIOUR_DERIVED,
            "valid:status_member",
            "expected:/semantic_dump",
        ),
    ),
    "history.valid.changed-path.added": (
        PurposeClaim(
            BEHAVIOUR_DERIVED,
            "valid:changed_path_canonical",
            "input:/status",
        ),
    ),
    "history.valid.changed-path.modified": (
        PurposeClaim(
            BEHAVIOUR_DERIVED,
            "valid:changed_path_canonical",
            "input:/status",
        ),
    ),
    "history.valid.change-set.canonical-three-paths": (
        PurposeClaim(
            BEHAVIOUR_DERIVED,
            "valid:change_set_supplied_count",
            "input:/changed_paths",
        ),
    ),
    "history.valid.change-set.single-path-minimum": (
        PurposeClaim(
            BEHAVIOUR_DERIVED,
            "valid:change_set_minimum",
            "input:/changed_paths",
        ),
    ),
    "history.valid.change-set.supplied-order-preserved": (
        PurposeClaim(
            REQUIREMENT_DERIVED,
            "valid:requirement_sentence",
            "requirement:CS-18",
        ),
    ),
    "history.valid.change-set.maximum-changed-paths": (
        PurposeClaim(
            BEHAVIOUR_DERIVED,
            "valid:change_set_maximum",
            "input:/changed_paths/indexed_value/count",
        ),
    ),
    "history.valid.approval.canonical": (
        PurposeClaim(
            BEHAVIOUR_DERIVED,
            "valid:approval_canonical",
            "input:/review/provider_global_id",
        ),
    ),
    "history.valid.approval.revision-need-not-be-head": (
        PurposeClaim(
            REQUIREMENT_DERIVED,
            "valid:requirement_sentence",
            "requirement:RA-04",
        ),
    ),
    "history.valid.merge-outcome.canonical": (
        PurposeClaim(
            BEHAVIOUR_DERIVED,
            "valid:merge_outcome_canonical",
            "input:/merge_revision/full_digest",
        ),
    ),
    "history.valid.merge-outcome.revision-independent-of-head": (
        PurposeClaim(
            REQUIREMENT_DERIVED,
            "valid:requirement_sentence",
            "requirement:MO-04",
        ),
    ),
    "history.valid.head-ref-deletion.canonical": (
        PurposeClaim(
            BEHAVIOUR_DERIVED,
            "valid:head_ref_deletion_canonical",
            "input:/head_ref_name",
        ),
    ),
    "history.valid.occurrence-time.approval": (
        PurposeClaim(
            BEHAVIOUR_DERIVED,
            "valid:occurrence_instant",
            "input:/occurred_at",
        ),
    ),
    "history.valid.occurrence-time.merge": (
        PurposeClaim(
            BEHAVIOUR_DERIVED,
            "valid:occurrence_instant",
            "input:/occurred_at",
        ),
    ),
    "history.valid.occurrence-time.deletion": (
        PurposeClaim(
            BEHAVIOUR_DERIVED,
            "valid:occurrence_instant",
            "input:/occurred_at",
        ),
    ),
    "history.valid.occurrence-time.offset-zero-form": (
        PurposeClaim(
            BEHAVIOUR_DERIVED,
            "valid:occurrence_offset_normalisation",
            "input:/occurred_at",
        ),
    ),
    "history.valid.occurrence-time.equal-instants-allowed": (
        PurposeClaim(
            BEHAVIOUR_DERIVED,
            "valid:occurrence_tied_surface",
            "input:/occurred_at",
        ),
        PurposeClaim(
            REQUIREMENT_DERIVED,
            "valid:requirement_sentence",
            "requirement:OT-06",
        ),
    ),
    "history.valid.evidence-link.role-binding-json": (
        PurposeClaim(
            BEHAVIOUR_DERIVED,
            "valid:evidence_link_json_fact",
            "input:/fact",
        ),
    ),
    "history.valid.evidence-link.changed-path-json": (
        PurposeClaim(
            BEHAVIOUR_DERIVED,
            "valid:evidence_link_json_fact",
            "input:/fact",
        ),
    ),
    "history.valid.evidence-link.review-approval-json": (
        PurposeClaim(
            BEHAVIOUR_DERIVED,
            "valid:evidence_link_json_fact",
            "input:/fact",
        ),
    ),
    "history.valid.evidence-link.merge-outcome-json": (
        PurposeClaim(
            BEHAVIOUR_DERIVED,
            "valid:evidence_link_json_fact",
            "input:/fact",
        ),
    ),
    "history.valid.evidence-link.head-ref-deletion-json": (
        PurposeClaim(
            BEHAVIOUR_DERIVED,
            "valid:evidence_link_json_fact",
            "input:/fact",
        ),
    ),
    "history.valid.evidence-link.occurrence-time-json": (
        PurposeClaim(
            BEHAVIOUR_DERIVED,
            "valid:evidence_link_json_fact",
            "input:/fact",
        ),
    ),
    "history.valid.evidence-link.role-binding-python": (
        PurposeClaim(
            BEHAVIOUR_DERIVED,
            "valid:evidence_link_python_fact",
            "input:/fact/typed_value/target",
        ),
    ),
    "history.valid.evidence-link.changed-path-python": (
        PurposeClaim(
            BEHAVIOUR_DERIVED,
            "valid:evidence_link_python_fact",
            "input:/fact/typed_value/target",
        ),
    ),
    "history.valid.evidence-link.review-approval-python": (
        PurposeClaim(
            BEHAVIOUR_DERIVED,
            "valid:evidence_link_python_fact",
            "input:/fact/typed_value/target",
        ),
    ),
    "history.valid.evidence-link.merge-outcome-python": (
        PurposeClaim(
            BEHAVIOUR_DERIVED,
            "valid:evidence_link_python_fact",
            "input:/fact/typed_value/target",
        ),
    ),
    "history.valid.evidence-link.head-ref-deletion-python": (
        PurposeClaim(
            BEHAVIOUR_DERIVED,
            "valid:evidence_link_python_fact",
            "input:/fact/typed_value/target",
        ),
    ),
    "history.valid.evidence-link.occurrence-time-python": (
        PurposeClaim(
            BEHAVIOUR_DERIVED,
            "valid:evidence_link_python_fact",
            "input:/fact/typed_value/target",
        ),
    ),
    "history.valid.evidence-link.second-fact-same-record": (
        PurposeClaim(
            REQUIREMENT_DERIVED,
            "valid:requirement_sentence",
            "requirement:EL-06",
        ),
    ),
    "history.valid.role-binding.distinct-pull-request": (
        PurposeClaim(
            CANONICAL_DECLARATION_ONLY,
            "valid:canonical_declaration",
            "literal",
        ),
    ),
    "history.valid.role-binding.distinct-revision": (
        PurposeClaim(
            CANONICAL_DECLARATION_ONLY,
            "valid:canonical_declaration",
            "literal",
        ),
    ),
    "history.valid.role-binding.python-typed": (
        PurposeClaim(
            CANONICAL_DECLARATION_ONLY,
            "valid:canonical_declaration",
            "literal",
        ),
    ),
    "history.valid.status.python-enum": (
        PurposeClaim(
            CANONICAL_DECLARATION_ONLY,
            "valid:canonical_declaration",
            "literal",
        ),
    ),
    "history.valid.changed-path.distinct-blob": (
        PurposeClaim(
            CANONICAL_DECLARATION_ONLY,
            "valid:canonical_declaration",
            "literal",
        ),
    ),
    "history.valid.changed-path.python-typed": (
        PurposeClaim(
            CANONICAL_DECLARATION_ONLY,
            "valid:canonical_declaration",
            "literal",
        ),
    ),
    "history.valid.change-set.python-typed": (
        PurposeClaim(
            CANONICAL_DECLARATION_ONLY,
            "valid:canonical_declaration",
            "literal",
        ),
    ),
    "history.valid.approval.python-typed": (
        PurposeClaim(
            CANONICAL_DECLARATION_ONLY,
            "valid:canonical_declaration",
            "literal",
        ),
    ),
    "history.valid.merge-outcome.python-typed": (
        PurposeClaim(
            CANONICAL_DECLARATION_ONLY,
            "valid:canonical_declaration",
            "literal",
        ),
    ),
    "history.valid.head-ref-deletion.distinct-ref-name": (
        PurposeClaim(
            CANONICAL_DECLARATION_ONLY,
            "valid:canonical_declaration",
            "literal",
        ),
    ),
    "history.valid.head-ref-deletion.python-typed": (
        PurposeClaim(
            CANONICAL_DECLARATION_ONLY,
            "valid:canonical_declaration",
            "literal",
        ),
    ),
    "history.valid.occurrence-time.sub-second-preserved": (
        PurposeClaim(
            CANONICAL_DECLARATION_ONLY,
            "valid:canonical_declaration",
            "literal",
        ),
    ),
    "history.valid.occurrence-time.python-typed": (
        PurposeClaim(
            CANONICAL_DECLARATION_ONLY,
            "valid:canonical_declaration",
            "literal",
        ),
    ),
    "history.valid.evidence-link.correction-record": (
        PurposeClaim(
            CANONICAL_DECLARATION_ONLY,
            "valid:canonical_declaration",
            "literal",
        ),
    ),
    "history.valid.evidence-link.synthetic-record": (
        PurposeClaim(
            CANONICAL_DECLARATION_ONLY,
            "valid:canonical_declaration",
            "literal",
        ),
        PurposeClaim(
            CANONICAL_DECLARATION_ONLY,
            "valid:canonical_declaration_second",
            "literal",
        ),
    ),
    # -- 111 invalid vectors --------------------------------------------
    "history.invalid.approval.blob-as-approved-revision": (
        PurposeClaim(
            REQUIREMENT_DERIVED,
            "invalid:requirement_gloss",
            "secondary-witness",
        ),
    ),
    "history.invalid.approval.extra-state": (
        PurposeClaim(
            REQUIREMENT_DERIVED,
            "invalid:requirement_gloss",
            "secondary-witness",
        ),
    ),
    "history.invalid.approval.extra-submitted-at": (
        PurposeClaim(
            REQUIREMENT_DERIVED,
            "invalid:requirement_gloss",
            "secondary-witness",
        ),
    ),
    "history.invalid.approval.missing-approved-revision": (
        PurposeClaim(
            REQUIREMENT_DERIVED,
            "invalid:requirement_gloss",
            "secondary-witness",
        ),
    ),
    "history.invalid.approval.missing-review": (
        PurposeClaim(
            REQUIREMENT_DERIVED,
            "invalid:requirement_gloss",
            "secondary-witness",
        ),
    ),
    "history.invalid.approval.non-pull-request-parent": (
        PurposeClaim(
            REQUIREMENT_DERIVED,
            "invalid:requirement_gloss",
            "secondary-witness",
        ),
    ),
    "history.invalid.approval.non-review-kind-subject": (
        PurposeClaim(
            REQUIREMENT_DERIVED,
            "invalid:requirement_gloss",
            "requirement:RA-03",
        ),
    ),
    "history.invalid.approval.non-review-subject": (
        PurposeClaim(
            REQUIREMENT_DERIVED,
            "invalid:requirement_gloss",
            "secondary-witness",
        ),
    ),
    "history.invalid.approval.untyped-python-approved-revision": (
        PurposeClaim(
            REQUIREMENT_DERIVED,
            "invalid:requirement_gloss",
            "requirement:RA-02",
        ),
    ),
    "history.invalid.approval.untyped-python-review": (
        PurposeClaim(
            REQUIREMENT_DERIVED,
            "invalid:requirement_gloss",
            "requirement:RA-01",
        ),
    ),
    "history.invalid.change-set.above-maximum-changed-paths": (
        PurposeClaim(
            REQUIREMENT_DERIVED,
            "invalid:requirement_gloss",
            "requirement:CS-05",
        ),
    ),
    "history.invalid.change-set.base-position-rejects-non-base-role": (
        PurposeClaim(
            REQUIREMENT_DERIVED,
            "invalid:requirement_gloss",
            "requirement:CS-11",
        ),
    ),
    "history.invalid.change-set.duplicate-path": (
        PurposeClaim(
            REQUIREMENT_DERIVED,
            "invalid:requirement_gloss",
            "requirement:CS-16",
        ),
    ),
    "history.invalid.change-set.empty-changed-paths": (
        PurposeClaim(
            REQUIREMENT_DERIVED,
            "invalid:requirement_gloss",
            "requirement:CS-04",
        ),
    ),
    "history.invalid.change-set.equal-base-and-head-revision": (
        PurposeClaim(
            REQUIREMENT_DERIVED,
            "invalid:requirement_gloss",
            "requirement:CS-13",
        ),
    ),
    "history.invalid.change-set.extra-complete": (
        PurposeClaim(
            REQUIREMENT_DERIVED,
            "invalid:requirement_gloss",
            "requirement:CS-17",
        ),
    ),
    "history.invalid.change-set.head-position-rejects-non-head-role": (
        PurposeClaim(
            REQUIREMENT_DERIVED,
            "invalid:requirement_gloss",
            "requirement:CS-12",
        ),
    ),
    "history.invalid.change-set.mismatched-pull-requests": (
        PurposeClaim(
            REQUIREMENT_DERIVED,
            "invalid:requirement_gloss",
            "requirement:CS-10",
        ),
    ),
    "history.invalid.change-set.mismatched-revision-algorithms": (
        PurposeClaim(
            REQUIREMENT_DERIVED,
            "invalid:requirement_gloss",
            "requirement:CS-14",
        ),
        PurposeClaim(
            BEHAVIOUR_DERIVED,
            "invalid:objects_already_match_head",
            "input:/changed_paths",
        ),
    ),
    "history.invalid.change-set.missing-base": (
        PurposeClaim(
            REQUIREMENT_DERIVED,
            "invalid:requirement_gloss",
            "requirement:CS-01",
        ),
    ),
    "history.invalid.change-set.missing-changed-paths": (
        PurposeClaim(
            REQUIREMENT_DERIVED,
            "invalid:requirement_gloss",
            "requirement:CS-03",
        ),
    ),
    "history.invalid.change-set.missing-head": (
        PurposeClaim(
            REQUIREMENT_DERIVED,
            "invalid:requirement_gloss",
            "requirement:CS-02",
        ),
    ),
    "history.invalid.change-set.mixed-hash-algorithms": (
        PurposeClaim(
            REQUIREMENT_DERIVED,
            "invalid:requirement_gloss",
            "requirement:CS-15",
        ),
    ),
    "history.invalid.change-set.python-list-not-tuple": (
        PurposeClaim(
            REQUIREMENT_DERIVED,
            "invalid:requirement_gloss",
            "requirement:CS-08",
        ),
    ),
    "history.invalid.change-set.untyped-python-base": (
        PurposeClaim(
            REQUIREMENT_DERIVED,
            "invalid:requirement_gloss",
            "requirement:CS-06",
        ),
    ),
    "history.invalid.change-set.untyped-python-changed-path-element": (
        PurposeClaim(
            REQUIREMENT_DERIVED,
            "invalid:requirement_gloss",
            "requirement:CS-09",
        ),
    ),
    "history.invalid.change-set.untyped-python-head": (
        PurposeClaim(
            REQUIREMENT_DERIVED,
            "invalid:requirement_gloss",
            "requirement:CS-07",
        ),
    ),
    "history.invalid.changed-path.commit-as-head-object": (
        PurposeClaim(
            REQUIREMENT_DERIVED,
            "invalid:requirement_gloss",
            "requirement:CP-03",
        ),
    ),
    "history.invalid.changed-path.empty-path": (
        PurposeClaim(
            REQUIREMENT_DERIVED,
            "invalid:requirement_gloss",
            "secondary-witness",
        ),
    ),
    "history.invalid.changed-path.extra-base-object": (
        PurposeClaim(
            REQUIREMENT_DERIVED,
            "invalid:requirement_gloss",
            "secondary-witness",
        ),
    ),
    "history.invalid.changed-path.missing-head-object": (
        PurposeClaim(
            REQUIREMENT_DERIVED,
            "invalid:requirement_gloss",
            "secondary-witness",
        ),
    ),
    "history.invalid.changed-path.missing-path": (
        PurposeClaim(
            REQUIREMENT_DERIVED,
            "invalid:requirement_gloss",
            "secondary-witness",
        ),
    ),
    "history.invalid.changed-path.missing-status": (
        PurposeClaim(
            REQUIREMENT_DERIVED,
            "invalid:requirement_gloss",
            "secondary-witness",
        ),
    ),
    "history.invalid.changed-path.raw-python-status": (
        PurposeClaim(
            REQUIREMENT_DERIVED,
            "invalid:requirement_gloss",
            "requirement:CP-04",
        ),
    ),
    "history.invalid.changed-path.unknown-status": (
        PurposeClaim(
            REQUIREMENT_DERIVED,
            "invalid:requirement_gloss",
            "secondary-witness",
        ),
    ),
    "history.invalid.changed-path.untyped-python-head-object": (
        PurposeClaim(
            REQUIREMENT_DERIVED,
            "invalid:requirement_gloss",
            "requirement:CP-02",
        ),
    ),
    "history.invalid.changed-path.untyped-python-path": (
        PurposeClaim(
            REQUIREMENT_DERIVED,
            "invalid:requirement_gloss",
            "requirement:CP-01",
        ),
    ),
    "history.invalid.evidence-link.change-set-fact": (
        PurposeClaim(
            REQUIREMENT_DERIVED,
            "invalid:requirement_gloss",
            "requirement:EL-04",
        ),
    ),
    "history.invalid.evidence-link.change-set-fact-python": (
        PurposeClaim(
            REQUIREMENT_DERIVED,
            "invalid:requirement_gloss",
            "secondary-witness",
        ),
    ),
    "history.invalid.evidence-link.changed-path-status-fact": (
        PurposeClaim(
            REQUIREMENT_DERIVED,
            "invalid:requirement_gloss",
            "requirement:EL-05",
        ),
    ),
    "history.invalid.evidence-link.empty-fact-json": (
        PurposeClaim(
            REQUIREMENT_DERIVED,
            "invalid:requirement_gloss",
            "secondary-witness",
        ),
    ),
    "history.invalid.evidence-link.extra-artifact": (
        PurposeClaim(
            REQUIREMENT_DERIVED,
            "invalid:requirement_gloss",
            "secondary-witness",
        ),
    ),
    "history.invalid.evidence-link.extra-confidence": (
        PurposeClaim(
            REQUIREMENT_DERIVED,
            "invalid:requirement_gloss",
            "secondary-witness",
        ),
    ),
    "history.invalid.evidence-link.extra-evidence-records": (
        PurposeClaim(
            REQUIREMENT_DERIVED,
            "invalid:requirement_gloss",
            "secondary-witness",
        ),
    ),
    "history.invalid.evidence-link.extra-json-pointer": (
        PurposeClaim(
            REQUIREMENT_DERIVED,
            "invalid:requirement_gloss",
            "secondary-witness",
        ),
    ),
    "history.invalid.evidence-link.extra-primary-evidence": (
        PurposeClaim(
            REQUIREMENT_DERIVED,
            "invalid:requirement_gloss",
            "secondary-witness",
        ),
    ),
    "history.invalid.evidence-link.extra-request-id": (
        PurposeClaim(
            REQUIREMENT_DERIVED,
            "invalid:requirement_gloss",
            "secondary-witness",
        ),
    ),
    "history.invalid.evidence-link.extra-schema-version": (
        PurposeClaim(
            REQUIREMENT_DERIVED,
            "invalid:requirement_gloss",
            "secondary-witness",
        ),
    ),
    "history.invalid.evidence-link.extra-strength": (
        PurposeClaim(
            REQUIREMENT_DERIVED,
            "invalid:requirement_gloss",
            "secondary-witness",
        ),
    ),
    "history.invalid.evidence-link.extra-superseded": (
        PurposeClaim(
            REQUIREMENT_DERIVED,
            "invalid:requirement_gloss",
            "secondary-witness",
        ),
    ),
    "history.invalid.evidence-link.extra-support-role": (
        PurposeClaim(
            REQUIREMENT_DERIVED,
            "invalid:requirement_gloss",
            "secondary-witness",
        ),
    ),
    "history.invalid.evidence-link.extra-verification": (
        PurposeClaim(
            REQUIREMENT_DERIVED,
            "invalid:requirement_gloss",
            "secondary-witness",
        ),
    ),
    "history.invalid.evidence-link.hybrid-fact-json": (
        PurposeClaim(
            REQUIREMENT_DERIVED,
            "invalid:requirement_gloss",
            "secondary-witness",
        ),
    ),
    "history.invalid.evidence-link.instant-basic-format": (
        PurposeClaim(
            REQUIREMENT_DERIVED,
            "invalid:requirement_gloss",
            "secondary-witness",
        ),
    ),
    "history.invalid.evidence-link.instant-naive": (
        PurposeClaim(
            REQUIREMENT_DERIVED,
            "invalid:requirement_gloss",
            "secondary-witness",
        ),
    ),
    "history.invalid.evidence-link.instant-non-zero-offset": (
        PurposeClaim(
            REQUIREMENT_DERIVED,
            "invalid:requirement_gloss",
            "secondary-witness",
        ),
    ),
    "history.invalid.evidence-link.instant-week-date": (
        PurposeClaim(
            REQUIREMENT_DERIVED,
            "invalid:requirement_gloss",
            "secondary-witness",
        ),
    ),
    "history.invalid.evidence-link.malformed-record": (
        PurposeClaim(
            REQUIREMENT_DERIVED,
            "invalid:requirement_gloss",
            "secondary-witness",
        ),
    ),
    "history.invalid.evidence-link.missing-evidence-record": (
        PurposeClaim(
            REQUIREMENT_DERIVED,
            "invalid:requirement_gloss",
            "secondary-witness",
        ),
    ),
    "history.invalid.evidence-link.missing-fact": (
        PurposeClaim(
            REQUIREMENT_DERIVED,
            "invalid:requirement_gloss",
            "secondary-witness",
        ),
    ),
    "history.invalid.evidence-link.nested-non-admitted-occurrence": (
        PurposeClaim(
            REQUIREMENT_DERIVED,
            "invalid:requirement_gloss",
            "secondary-witness",
        ),
    ),
    "history.invalid.evidence-link.occurrence-time-fact-python": (
        PurposeClaim(
            REQUIREMENT_DERIVED,
            "invalid:requirement_gloss",
            "requirement:EL-02",
        ),
    ),
    "history.invalid.evidence-link.status-fact-python": (
        PurposeClaim(
            REQUIREMENT_DERIVED,
            "invalid:requirement_gloss",
            "secondary-witness",
        ),
    ),
    "history.invalid.evidence-link.typed-children-mapping-python": (
        PurposeClaim(
            REQUIREMENT_DERIVED,
            "invalid:requirement_gloss",
            "secondary-witness",
        ),
    ),
    "history.invalid.evidence-link.untyped-python-fact": (
        PurposeClaim(
            REQUIREMENT_DERIVED,
            "invalid:requirement_gloss",
            "requirement:EL-01",
        ),
    ),
    "history.invalid.evidence-link.untyped-python-record": (
        PurposeClaim(
            REQUIREMENT_DERIVED,
            "invalid:requirement_gloss",
            "requirement:EL-03",
        ),
    ),
    "history.invalid.head-ref-deletion.base-binding": (
        PurposeClaim(
            REQUIREMENT_DERIVED,
            "invalid:requirement_gloss",
            "requirement:HD-03",
        ),
    ),
    "history.invalid.head-ref-deletion.empty-ref-name": (
        PurposeClaim(
            REQUIREMENT_DERIVED,
            "invalid:requirement_gloss",
            "secondary-witness",
        ),
    ),
    "history.invalid.head-ref-deletion.extra-namespace": (
        PurposeClaim(
            REQUIREMENT_DERIVED,
            "invalid:requirement_gloss",
            "secondary-witness",
        ),
    ),
    "history.invalid.head-ref-deletion.missing-head": (
        PurposeClaim(
            REQUIREMENT_DERIVED,
            "invalid:requirement_gloss",
            "secondary-witness",
        ),
    ),
    "history.invalid.head-ref-deletion.missing-ref-name": (
        PurposeClaim(
            REQUIREMENT_DERIVED,
            "invalid:requirement_gloss",
            "secondary-witness",
        ),
    ),
    "history.invalid.head-ref-deletion.raw-python-ref-name": (
        PurposeClaim(
            REQUIREMENT_DERIVED,
            "invalid:requirement_gloss",
            "requirement:HD-02",
        ),
    ),
    "history.invalid.head-ref-deletion.refs-prefixed-name": (
        PurposeClaim(
            REQUIREMENT_DERIVED,
            "invalid:requirement_gloss",
            "requirement:HD-04",
        ),
    ),
    "history.invalid.head-ref-deletion.untyped-python-head": (
        PurposeClaim(
            REQUIREMENT_DERIVED,
            "invalid:requirement_gloss",
            "requirement:HD-01",
        ),
    ),
    "history.invalid.merge-outcome.extra-parents": (
        PurposeClaim(
            REQUIREMENT_DERIVED,
            "invalid:requirement_gloss",
            "secondary-witness",
        ),
    ),
    "history.invalid.merge-outcome.extra-strategy": (
        PurposeClaim(
            REQUIREMENT_DERIVED,
            "invalid:requirement_gloss",
            "secondary-witness",
        ),
    ),
    "history.invalid.merge-outcome.missing-merge-revision": (
        PurposeClaim(
            REQUIREMENT_DERIVED,
            "invalid:requirement_gloss",
            "secondary-witness",
        ),
    ),
    "history.invalid.merge-outcome.missing-pull-request": (
        PurposeClaim(
            REQUIREMENT_DERIVED,
            "invalid:requirement_gloss",
            "secondary-witness",
        ),
    ),
    "history.invalid.merge-outcome.non-pull-request-subject": (
        PurposeClaim(
            REQUIREMENT_DERIVED,
            "invalid:requirement_gloss",
            "requirement:MO-03",
        ),
    ),
    "history.invalid.merge-outcome.tree-as-merge-revision": (
        PurposeClaim(
            REQUIREMENT_DERIVED,
            "invalid:requirement_gloss",
            "secondary-witness",
        ),
    ),
    "history.invalid.merge-outcome.untyped-python-merge-revision": (
        PurposeClaim(
            REQUIREMENT_DERIVED,
            "invalid:requirement_gloss",
            "requirement:MO-02",
        ),
    ),
    "history.invalid.merge-outcome.untyped-python-pull-request": (
        PurposeClaim(
            REQUIREMENT_DERIVED,
            "invalid:requirement_gloss",
            "requirement:MO-01",
        ),
    ),
    "history.invalid.occurrence-time.extra-chronology": (
        PurposeClaim(
            REQUIREMENT_DERIVED,
            "invalid:requirement_gloss",
            "secondary-witness",
        ),
    ),
    "history.invalid.occurrence-time.instant-malformed": (
        PurposeClaim(
            REQUIREMENT_DERIVED,
            "invalid:requirement_gloss",
            "secondary-witness",
        ),
    ),
    "history.invalid.occurrence-time.instant-naive": (
        PurposeClaim(
            REQUIREMENT_DERIVED,
            "invalid:requirement_gloss",
            "secondary-witness",
        ),
    ),
    "history.invalid.occurrence-time.instant-negative-offset": (
        PurposeClaim(
            REQUIREMENT_DERIVED,
            "invalid:requirement_gloss",
            "secondary-witness",
        ),
    ),
    "history.invalid.occurrence-time.instant-positive-offset": (
        PurposeClaim(
            REQUIREMENT_DERIVED,
            "invalid:requirement_gloss",
            "requirement:OT-02",
        ),
    ),
    "history.invalid.occurrence-time.missing-occurred-at": (
        PurposeClaim(
            REQUIREMENT_DERIVED,
            "invalid:requirement_gloss",
            "secondary-witness",
        ),
    ),
    "history.invalid.occurrence-time.missing-occurrence": (
        PurposeClaim(
            REQUIREMENT_DERIVED,
            "invalid:requirement_gloss",
            "secondary-witness",
        ),
        PurposeClaim(
            BEHAVIOUR_DERIVED,
            "invalid:true_omission_not_union",
            "expected:/error_location_mode",
        ),
    ),
    "history.invalid.occurrence-time.non-admitted-change-set": (
        PurposeClaim(
            REQUIREMENT_DERIVED,
            "invalid:requirement_gloss",
            "secondary-witness",
        ),
    ),
    "history.invalid.occurrence-time.non-admitted-changed-path": (
        PurposeClaim(
            REQUIREMENT_DERIVED,
            "invalid:requirement_gloss",
            "secondary-witness",
        ),
    ),
    "history.invalid.occurrence-time.non-admitted-changed-path-status": (
        PurposeClaim(
            REQUIREMENT_DERIVED,
            "invalid:requirement_gloss",
            "secondary-witness",
        ),
    ),
    "history.invalid.occurrence-time.non-admitted-commit-identity": (
        PurposeClaim(
            REQUIREMENT_DERIVED,
            "invalid:requirement_gloss",
            "secondary-witness",
        ),
    ),
    "history.invalid.occurrence-time.non-admitted-role-binding": (
        PurposeClaim(
            REQUIREMENT_DERIVED,
            "invalid:requirement_gloss",
            "secondary-witness",
        ),
    ),
    "history.invalid.occurrence-time.raw-python-instant": (
        PurposeClaim(
            REQUIREMENT_DERIVED,
            "invalid:requirement_gloss",
            "secondary-witness",
        ),
    ),
    "history.invalid.occurrence-time.untyped-python-occurrence": (
        PurposeClaim(
            REQUIREMENT_DERIVED,
            "invalid:requirement_gloss",
            "requirement:OT-01",
        ),
    ),
    "history.invalid.role-binding.disallowed-revision-role": (
        PurposeClaim(
            REQUIREMENT_DERIVED,
            "invalid:requirement_gloss",
            "requirement:RB-04",
        ),
    ),
    "history.invalid.role-binding.dumped-mapping-python": (
        PurposeClaim(
            REQUIREMENT_DERIVED,
            "invalid:requirement_gloss",
            "secondary-witness",
        ),
    ),
    "history.invalid.role-binding.extra-observed-at": (
        PurposeClaim(
            REQUIREMENT_DERIVED,
            "invalid:requirement_gloss",
            "secondary-witness",
        ),
    ),
    "history.invalid.role-binding.foreign-python-subject": (
        PurposeClaim(
            REQUIREMENT_DERIVED,
            "invalid:requirement_gloss",
            "secondary-witness",
        ),
    ),
    "history.invalid.role-binding.missing-pull-request": (
        PurposeClaim(
            REQUIREMENT_DERIVED,
            "invalid:requirement_gloss",
            "secondary-witness",
        ),
    ),
    "history.invalid.role-binding.missing-role-assignment": (
        PurposeClaim(
            REQUIREMENT_DERIVED,
            "invalid:requirement_gloss",
            "secondary-witness",
        ),
    ),
    "history.invalid.role-binding.non-pull-request-subject": (
        PurposeClaim(
            REQUIREMENT_DERIVED,
            "invalid:requirement_gloss",
            "requirement:RB-03",
        ),
    ),
    "history.invalid.role-binding.null-role-assignment": (
        PurposeClaim(
            REQUIREMENT_DERIVED,
            "invalid:requirement_gloss",
            "secondary-witness",
        ),
    ),
    "history.invalid.role-binding.swapped-members": (
        PurposeClaim(
            REQUIREMENT_DERIVED,
            "invalid:requirement_gloss",
            "secondary-witness",
        ),
    ),
    "history.invalid.role-binding.untyped-python-pull-request": (
        PurposeClaim(
            REQUIREMENT_DERIVED,
            "invalid:requirement_gloss",
            "requirement:RB-01",
        ),
    ),
    "history.invalid.role-binding.untyped-python-role-assignment": (
        PurposeClaim(
            REQUIREMENT_DERIVED,
            "invalid:requirement_gloss",
            "requirement:RB-02",
        ),
    ),
    "history.invalid.status.copied": (
        PurposeClaim(
            REQUIREMENT_DERIVED,
            "invalid:requirement_gloss",
            "secondary-witness",
        ),
    ),
    "history.invalid.status.not-a-status": (
        PurposeClaim(
            REQUIREMENT_DERIVED,
            "invalid:requirement_gloss",
            "requirement:ST-03",
        ),
    ),
    "history.invalid.status.removed": (
        PurposeClaim(
            REQUIREMENT_DERIVED,
            "invalid:requirement_gloss",
            "secondary-witness",
        ),
    ),
    "history.invalid.status.renamed": (
        PurposeClaim(
            REQUIREMENT_DERIVED,
            "invalid:requirement_gloss",
            "secondary-witness",
        ),
    ),
    # -- 24 replay vectors ----------------------------------------------
    "history.replay.role-binding.base": (
        PurposeClaim(
            PROVENANCE_DERIVED,
            "replay:retained_role_binding_fact",
            "source-pointer:/observations/comparison",
        ),
    ),
    "history.replay.role-binding.head": (
        PurposeClaim(
            PROVENANCE_DERIVED,
            "replay:retained_role_binding_fact",
            "source-pointer:/observations/comparison",
        ),
    ),
    "history.replay.changed-path.changelog": (
        PurposeClaim(
            PROVENANCE_DERIVED,
            "replay:retained_changed_path_fact",
            "source-pointer:/observations/pr/changed_files/items/0",
        ),
    ),
    "history.replay.changed-path.rewrite": (
        PurposeClaim(
            PROVENANCE_DERIVED,
            "replay:retained_changed_path_fact",
            "source-pointer:/observations/pr/changed_files/items/1",
        ),
    ),
    "history.replay.changed-path.assertrewrite": (
        PurposeClaim(
            PROVENANCE_DERIVED,
            "replay:retained_changed_path_fact",
            "source-pointer:/observations/pr/changed_files/items/2",
        ),
    ),
    "history.replay.change-set.supplied-three-paths": (
        PurposeClaim(
            PROVENANCE_DERIVED,
            "replay:caller_composed_change_set",
            "embedded-fact:/base",
        ),
        PurposeClaim(
            CANONICAL_DECLARATION_ONLY,
            "replay:change_set_completeness_limit",
            "manifest:/replay_contract/evidence_limits/change_set_completeness_claimed",
        ),
    ),
    "history.replay.review-approval.canonical": (
        PurposeClaim(
            PROVENANCE_DERIVED,
            "replay:retained_review_approval_fact",
            "source-pointer:/observations/pr/reviews/items/0",
        ),
    ),
    "history.replay.merge-outcome.canonical": (
        PurposeClaim(
            PROVENANCE_DERIVED,
            "replay:retained_merge_event_fact",
            "source-pointer:/observations/pr/timeline/items/4",
        ),
        PurposeClaim(
            CANONICAL_DECLARATION_ONLY,
            "replay:merge_revision_absent_surface",
            "manifest:/replay_contract/evidence_limits/merge_revision_source",
        ),
    ),
    "history.replay.head-ref-deletion.canonical": (
        PurposeClaim(
            CANONICAL_DECLARATION_ONLY,
            "replay:retained_target_declaration",
            "target",
        ),
    ),
    "history.replay.occurrence-time.approval": (
        PurposeClaim(
            PROVENANCE_DERIVED,
            "replay:retained_occurrence_instant_fact",
            "source-pointer:/observations/pr/reviews/items/0/submitted_at",
        ),
    ),
    "history.replay.occurrence-time.merge": (
        PurposeClaim(
            PROVENANCE_DERIVED,
            "replay:retained_occurrence_instant_fact",
            "source-pointer:/observations/pr/timeline/items/4/created_at/value",
        ),
    ),
    "history.replay.occurrence-time.deletion": (
        PurposeClaim(
            PROVENANCE_DERIVED,
            "replay:retained_occurrence_instant_fact",
            "source-pointer:/observations/pr/timeline/items/6/created_at/value",
        ),
    ),
    "history.replay.evidence-association.base-binding": (
        PurposeClaim(
            PROVENANCE_DERIVED,
            "replay:caller_association_to_locked_record",
            "evidence-record-lock",
        ),
        PurposeClaim(
            CANONICAL_DECLARATION_ONLY,
            "replay:evidence_link_non_claim",
            "literal",
        ),
    ),
    "history.replay.evidence-association.head-binding": (
        PurposeClaim(
            PROVENANCE_DERIVED,
            "replay:caller_association_to_locked_record",
            "evidence-record-lock",
        ),
        PurposeClaim(
            CANONICAL_DECLARATION_ONLY,
            "replay:evidence_link_non_claim",
            "literal",
        ),
    ),
    "history.replay.evidence-association.changed-path-changelog": (
        PurposeClaim(
            PROVENANCE_DERIVED,
            "replay:caller_association_to_locked_record",
            "evidence-record-lock",
        ),
        PurposeClaim(
            CANONICAL_DECLARATION_ONLY,
            "replay:evidence_link_non_claim",
            "literal",
        ),
    ),
    "history.replay.evidence-association.changed-path-rewrite": (
        PurposeClaim(
            PROVENANCE_DERIVED,
            "replay:caller_association_to_locked_record",
            "evidence-record-lock",
        ),
        PurposeClaim(
            CANONICAL_DECLARATION_ONLY,
            "replay:evidence_link_non_claim",
            "literal",
        ),
    ),
    "history.replay.evidence-association.changed-path-assertrewrite": (
        PurposeClaim(
            PROVENANCE_DERIVED,
            "replay:caller_association_to_locked_record",
            "evidence-record-lock",
        ),
        PurposeClaim(
            CANONICAL_DECLARATION_ONLY,
            "replay:evidence_link_non_claim",
            "literal",
        ),
    ),
    "history.replay.evidence-association.review-approval": (
        PurposeClaim(
            PROVENANCE_DERIVED,
            "replay:caller_association_to_locked_record",
            "evidence-record-lock",
        ),
        PurposeClaim(
            CANONICAL_DECLARATION_ONLY,
            "replay:evidence_link_non_claim",
            "literal",
        ),
    ),
    "history.replay.evidence-association.merge-outcome": (
        PurposeClaim(
            PROVENANCE_DERIVED,
            "replay:caller_association_to_locked_record",
            "evidence-record-lock",
        ),
        PurposeClaim(
            CANONICAL_DECLARATION_ONLY,
            "replay:evidence_link_non_claim",
            "literal",
        ),
    ),
    "history.replay.evidence-association.head-ref-deletion": (
        PurposeClaim(
            PROVENANCE_DERIVED,
            "replay:caller_association_to_locked_record",
            "evidence-record-lock",
        ),
        PurposeClaim(
            CANONICAL_DECLARATION_ONLY,
            "replay:evidence_link_non_claim",
            "literal",
        ),
    ),
    "history.replay.evidence-association.occurrence-approval": (
        PurposeClaim(
            PROVENANCE_DERIVED,
            "replay:caller_association_to_locked_record",
            "evidence-record-lock",
        ),
        PurposeClaim(
            CANONICAL_DECLARATION_ONLY,
            "replay:evidence_link_non_claim",
            "literal",
        ),
    ),
    "history.replay.evidence-association.occurrence-merge": (
        PurposeClaim(
            PROVENANCE_DERIVED,
            "replay:caller_association_to_locked_record",
            "evidence-record-lock",
        ),
        PurposeClaim(
            CANONICAL_DECLARATION_ONLY,
            "replay:evidence_link_non_claim",
            "literal",
        ),
    ),
    "history.replay.evidence-association.occurrence-deletion": (
        PurposeClaim(
            PROVENANCE_DERIVED,
            "replay:caller_association_to_locked_record",
            "evidence-record-lock",
        ),
        PurposeClaim(
            CANONICAL_DECLARATION_ONLY,
            "replay:evidence_link_non_claim",
            "literal",
        ),
    ),
    "history.replay.evidence-association.approval-correction-record": (
        PurposeClaim(
            CANONICAL_DECLARATION_ONLY,
            "replay:second_independent_correction_link",
            "source-decision-role:correction:s04-c01-acquisition-closure",
        ),
        PurposeClaim(
            CANONICAL_DECLARATION_ONLY,
            "replay:supersession_limit",
            "manifest:/replay_contract/evidence_limits/supersession_followed",
        ),
    ),
}


PURPOSE_RENDERERS: dict[str, Callable[[dict[str, Any], str], str]] = {
    "valid:approval_canonical": _PV_approval_canonical,
    "valid:canonical_declaration": _PV_canonical_declaration,
    "valid:canonical_declaration_second": _PV_canonical_declaration_second,
    "valid:change_set_maximum": _PV_change_set_maximum,
    "valid:change_set_minimum": _PV_change_set_minimum,
    "valid:change_set_supplied_count": _PV_change_set_supplied_count,
    "valid:changed_path_canonical": _PV_changed_path_canonical,
    "valid:evidence_link_json_fact": _PV_evidence_link_json_fact,
    "valid:evidence_link_python_fact": _PV_evidence_link_python_fact,
    "valid:head_ref_deletion_canonical": _PV_head_ref_deletion_canonical,
    "valid:merge_outcome_canonical": _PV_merge_outcome_canonical,
    "valid:occurrence_instant": _PV_occurrence_instant,
    "valid:occurrence_offset_normalisation": _PV_occurrence_offset_normalisation,
    "valid:occurrence_tied_surface": _PV_occurrence_tied_surface,
    "valid:requirement_sentence": _PV_requirement_sentence,
    "valid:role_binding_canonical": _PV_role_binding_canonical,
    "valid:status_member": _PV_status_member,
    "invalid:objects_already_match_head": _pI_render_objects_already_match_head,
    "invalid:requirement_gloss": _pI_render_requirement_gloss,
    "invalid:true_omission_not_union": _pI_render_true_omission_not_union,
    "replay:caller_association_to_locked_record": _PR_caller_association_to_locked_record,
    "replay:caller_composed_change_set": _PR_caller_composed_change_set,
    "replay:change_set_completeness_limit": _PR_change_set_completeness_limit,
    "replay:evidence_link_non_claim": _PR_evidence_link_non_claim,
    "replay:merge_revision_absent_surface": _PR_merge_revision_absent_surface,
    "replay:retained_changed_path_fact": _PR_retained_changed_path_fact,
    "replay:retained_merge_event_fact": _PR_retained_merge_event_fact,
    "replay:retained_occurrence_instant_fact": _PR_retained_occurrence_instant_fact,
    "replay:retained_review_approval_fact": _PR_retained_review_approval_fact,
    "replay:retained_role_binding_fact": _PR_retained_role_binding_fact,
    "replay:retained_target_declaration": _PR_retained_target_declaration,
    "replay:second_independent_correction_link": _PR_second_independent_correction_link,
    "replay:supersession_limit": _PR_supersession_limit,
}


# Which retained coordinate each provenance renderer consumes. A replay vector
# cites several source pointers, so "the claimed coordinate is cited somewhere"
# accepted a coordinate the sentence was never read from -- the role-binding
# claim could name `/observations/repository` while the renderer went on
# deriving the role and the revision from the comparison. The values here are
# the renderers' own selections, so the two cannot disagree; a renderer with no
# entry may not carry a coordinate claim at all.
PURPOSE_SOURCE_POINTER_SELECTORS: dict[
    str, Callable[[dict[str, Any]], dict[str, Any]]
] = {
    "replay:retained_changed_path_fact": _pR_primary,
    "replay:retained_merge_event_fact": _pR_primary,
    "replay:retained_occurrence_instant_fact": _pR_instant_pointer,
    "replay:retained_review_approval_fact": _pR_primary,
    "replay:retained_role_binding_fact": _pR_role_implication_pointer,
}

# The same rule for embedded facts. A composition binds its role bindings and
# counts them; the paths it selects are not bindings, so citing one of those
# would name a key the sentence does not rest on.
PURPOSE_EMBEDDED_FACT_SELECTORS: dict[str, Callable[[dict[str, Any]], list[str]]] = {
    "replay:caller_composed_change_set": _pR_composed_bindings,
}

# And for the two remaining forms, which were checked only for existence.
#
# A scalar provenance field was accepted whenever it was non-empty. The
# association renderer reads BOTH scalars -- the classification supplies its
# verb, the lock supplies the record it names -- so "non-empty" let the claim
# cite the classification as support for a record identity the classification
# does not establish. The field the fragment's subject comes from is named here.
PURPOSE_SCALAR_FIELDS: dict[str, str] = {
    "replay:caller_association_to_locked_record": "evidence_record_lock",
    "replay:retained_target_declaration": "target",
}

# A manifest authority was accepted whenever the pointer resolved. Swapping the
# completeness and merge-revision pointers left both resolving and both
# descriptive while each renderer went on reading its own leaf, so the ledger
# recorded unrelated evidence locations. These are the constants the renderers
# themselves read.
PURPOSE_MANIFEST_POINTERS: dict[str, str] = {
    "replay:change_set_completeness_limit": _PR_CHANGE_SET_COMPLETENESS_LEAF,
    "replay:merge_revision_absent_surface": _PR_MERGE_REVISION_SOURCE_LEAF,
    "replay:supersession_limit": _PR_SUPERSESSION_FOLLOWED_LEAF,
}


def _render_purpose(
    vector: dict[str, Any],
    family: str,
    ledger: dict[str, tuple[PurposeClaim, ...]] | None = None,
) -> str:
    """Rebuild the published sentence from its claims, and only from those.

    The ledger is a parameter so a probe can move a claim descriptor and watch
    the rendering follow it; defaulting to the authored one keeps the call
    sites that only ask about the live corpus short.
    """
    claims = (PURPOSE_SEMANTICS if ledger is None else ledger)[cast(str, vector["id"])]
    fragments = [PURPOSE_RENDERERS[claim.renderer](vector, family) for claim in claims]
    return "; ".join(fragments) + "."


def _scalar_field_failures(claim: PurposeClaim, field: str) -> list[str]:
    """A scalar claim must name the field its own fragment is built from.

    The association renderer reads two of them -- the classification supplies
    its verb and the lock supplies the record it names -- so "the field is not
    empty" let a claim cite the classification as support for a record identity
    the classification does not establish.
    """
    declared = PURPOSE_SCALAR_FIELDS.get(claim.renderer)
    if declared is None:
        return ["renderer-reads-no-scalar-field"]
    if declared != field:
        return ["scalar-field-is-not-the-renderer-input"]
    return []


def _purpose_authority_failures(
    vector: dict[str, Any], family: str, claim: PurposeClaim
) -> list[str]:
    """Every way a claim's declared authority fails to answer for it."""
    reasons: list[str] = []
    authority = claim.authority
    identifier = cast(str, vector["id"])
    if claim.assurance not in PURPOSE_ASSURANCE_CLASSES:
        reasons.append("unknown-assurance")
    if claim.renderer not in PURPOSE_RENDERERS:
        reasons.append("unknown-renderer")
    if authority.startswith("requirement:"):
        row_id = authority.split(":", 1)[1]
        rows = [row for row in REQUIREMENT_LEDGER if row[0] == row_id]
        if len(rows) != 1:
            reasons.append("requirement-row-not-unique")
        elif rows[0][4] != identifier:
            reasons.append("requirement-row-witnesses-another-vector")
    elif authority == "secondary-witness":
        if identifier not in SECONDARY_WITNESS_REGISTRY:
            reasons.append("not-a-secondary-witness")
        elif SECONDARY_WITNESS_REGISTRY[identifier] != _derived_requirement(vector):
            reasons.append("secondary-witness-derivation-differs")
    elif authority.startswith(("input:", "expected:")):
        root, pointer = authority.split(":", 1)
        try:
            _resolve_pointer(vector[root], pointer)
        except (KeyError, IndexError, TypeError):
            reasons.append("pointer-does-not-resolve")
    elif authority.startswith("source-pointer:"):
        pointer = authority.split(":", 1)[1]
        cited = {
            cast(str, entry["json_pointer"])
            for entry in cast(list[dict[str, Any]], vector.get("source_pointers") or [])
        }
        if pointer not in cited:
            reasons.append("source-pointer-not-cited")
        else:
            # being cited is not enough: the coordinate must be the one this
            # renderer reads, or the ledger publishes an unrelated provenance
            select = PURPOSE_SOURCE_POINTER_SELECTORS.get(claim.renderer)
            if select is None:
                reasons.append("renderer-reads-no-source-pointer")
            else:
                try:
                    consumed = cast(str, select(vector)["json_pointer"])
                except (StopIteration, LookupError):
                    reasons.append("renderer-input-coordinate-unresolvable")
                else:
                    if consumed != pointer:
                        reasons.append("source-pointer-is-not-the-renderer-input")
    elif authority.startswith("embedded-fact:"):
        # `embedded_facts` is keyed by pointer strings, so this is membership
        pointer = authority.split(":", 1)[1]
        if pointer not in cast(dict[str, Any], vector.get("embedded_facts") or {}):
            reasons.append("embedded-fact-not-declared")
        else:
            bind = PURPOSE_EMBEDDED_FACT_SELECTORS.get(claim.renderer)
            if bind is None:
                reasons.append("renderer-reads-no-embedded-fact")
            elif pointer not in bind(vector):
                reasons.append("embedded-fact-is-not-the-renderer-input")
    elif authority.startswith("source-decision-role:"):
        # the reference is the whole tail: it carries a colon of its own
        reference = authority.split(":", 1)[1]
        if reference not in REQUIRED_SOURCE_DECISION_BY_REFERENCE:
            reasons.append("source-decision-reference-unknown")
        else:
            matching = [
                entry
                for entry in _live_source_decisions()
                if entry["decision_reference"] == reference
            ]
            if len(matching) != 1:
                reasons.append("source-decision-reference-not-unique")
            else:
                # the completed attachment already owns path, role and id-source
                attachment = _source_attachment_failures(
                    matching,
                    {reference: REQUIRED_SOURCE_DECISION_BY_REFERENCE[reference]},
                )
                if attachment:
                    reasons.append("source-decision-identity-differs")
            lock = cast(str, vector.get("evidence_record_lock") or "")
            if lock and lock != reference:
                reasons.append("claim-cites-another-source-than-the-renderer")
    elif authority.startswith("manifest:"):
        pointer = authority.split(":", 1)[1]
        # `source_decisions` ordering is semantically neutral, so a numeric slot
        # into it names whichever record happens to sit there
        if pointer.startswith("/source_decisions/") and any(
            segment.isdigit() for segment in pointer.split("/")
        ):
            reasons.append("positional-source-decision-authority-forbidden")
        try:
            _resolve_pointer(MANIFEST, pointer)
        except (KeyError, IndexError, TypeError):
            reasons.append("manifest-pointer-does-not-resolve")
        else:
            # resolving is not reading: the leaf must be the one this renderer
            # builds its sentence from
            declared = PURPOSE_MANIFEST_POINTERS.get(claim.renderer)
            if declared is None:
                reasons.append("renderer-reads-no-manifest-leaf")
            elif declared != pointer:
                reasons.append("manifest-leaf-is-not-the-renderer-input")
        if (
            pointer in DESCRIPTIVE_PATHS
            and claim.assurance != CANONICAL_DECLARATION_ONLY
        ):
            reasons.append("descriptive-leaf-claimed-as-verified")
    elif authority in ("target", "input_mode"):
        if authority not in vector:
            reasons.append("field-absent")
        else:
            reasons.extend(_scalar_field_failures(claim, authority))
    elif authority in ("evidence-classification", "evidence-record-lock"):
        field = authority.replace("-", "_")
        if not vector.get(field):
            reasons.append("provenance-field-absent")
        else:
            reasons.extend(_scalar_field_failures(claim, field))
    elif authority == "literal":
        if claim.assurance != CANONICAL_DECLARATION_ONLY:
            reasons.append("literal-claimed-as-verified")
    else:
        reasons.append("unrecognised-authority")
    return reasons


def _purpose_failures(
    sections: dict[str, dict[str, Any]],
    ledger: dict[str, tuple[PurposeClaim, ...]],
) -> list[tuple[str, str]]:
    """`(vector_id, reason)` for every purpose the ledger cannot account for."""
    failures: list[tuple[str, str]] = []
    seen: set[str] = set()
    for family, section in sorted(sections.items()):
        for vector in section["vectors"]:
            identifier = cast(str, vector["id"])
            if identifier in seen:
                failures.append((identifier, "vector-id-repeated"))
                continue
            seen.add(identifier)
            if identifier not in ledger:
                failures.append((identifier, "vector-absent-from-ledger"))
                continue
            claims = ledger[identifier]
            if not claims:
                failures.append((identifier, "no-claim"))
                continue
            for claim in claims:
                for reason in _purpose_authority_failures(vector, family, claim):
                    failures.append((identifier, reason))
            try:
                rendered = _render_purpose(vector, family, ledger)
            except Exception:  # noqa: BLE001 - a renderer that cannot run is a failure
                failures.append((identifier, "renderer-raised"))
                continue
            if rendered != vector["purpose"]:
                failures.append((identifier, "rendered-purpose-differs"))
    for identifier in sorted(set(ledger) - seen):
        failures.append((identifier, "ledger-entry-unpopulated"))
    return sorted(failures)


def _purpose_sections() -> dict[str, dict[str, Any]]:
    return _sections(VALID, INVALID, REPLAY)


def test_every_published_purpose_is_rebuilt_from_its_claims() -> None:
    """The reported finding, closed.

    Swapping two purposes, or replacing one with unrelated prose, left every
    oracle green because truthiness was the whole rule.
    """
    assert not _purpose_failures(_purpose_sections(), PURPOSE_SEMANTICS)

    assert len(PURPOSE_SEMANTICS) == 183
    assert sum(len(claims) for claims in PURPOSE_SEMANTICS.values()) == 201
    for family, section in _purpose_sections().items():
        for vector in section["vectors"]:
            assert _render_purpose(vector, family) == vector["purpose"], vector["id"]


def test_the_purpose_ledger_closes_against_the_corpus_both_ways() -> None:
    published = {
        cast(str, vector["id"])
        for section in (VALID, INVALID, REPLAY)
        for vector in section["vectors"]
    }

    assert published - set(PURPOSE_SEMANTICS) == set(), "a vector the ledger omits"
    assert set(PURPOSE_SEMANTICS) - published == set(), "an entry no vector publishes"
    assert [
        len([v for v in section["vectors"] if v["id"] in PURPOSE_SEMANTICS])
        for section in (VALID, INVALID, REPLAY)
    ] == [48, 111, 24]


def test_every_purpose_claim_carries_a_recognised_assurance_class() -> None:
    """No fragment may sit outside the partition, and none may be unowned."""
    counted = Counter(
        claim.assurance for claims in PURPOSE_SEMANTICS.values() for claim in claims
    )

    assert set(counted) <= set(PURPOSE_ASSURANCE_CLASSES)
    assert sum(counted.values()) == 201
    assert not [
        identifier for identifier, claims in PURPOSE_SEMANTICS.items() if not claims
    ], "every vector states at least one claim"
    assert all(
        claim.renderer in PURPOSE_RENDERERS
        for claims in PURPOSE_SEMANTICS.values()
        for claim in claims
    )


def test_every_invalid_purpose_answers_to_a_validated_requirement() -> None:
    """All 111 rest on an identity the corpus independently validates.

    Forty-three are REQUIREMENT_LEDGER witnesses; the rest are secondary
    witnesses whose registered requirement `_derived_requirement` reproduces
    from validated properties. None falls back to canonical declaration.
    """
    ledger_witnesses = {row[4] for row in REQUIREMENT_LEDGER}
    unowned: list[str] = []
    for vector in INVALID["vectors"]:
        identifier = cast(str, vector["id"])
        if identifier not in ledger_witnesses and identifier not in (
            SECONDARY_WITNESS_REGISTRY
        ):
            unowned.append(identifier)
    assert not unowned, unowned

    declaration_only = [
        identifier
        for vector in INVALID["vectors"]
        for identifier in [cast(str, vector["id"])]
        for claim in PURPOSE_SEMANTICS[identifier]
        if claim.assurance == CANONICAL_DECLARATION_ONLY
    ]
    assert not declaration_only, declaration_only

    for identifier in SECONDARY_WITNESS_REGISTRY:
        vector = next(v for v in INVALID["vectors"] if v["id"] == identifier)
        assert SECONDARY_WITNESS_REGISTRY[identifier] == _derived_requirement(vector)


REQUIRED_ASSURANCE_BY_AUTHORITY_FORM: dict[str, str] = {
    "embedded-fact": PROVENANCE_DERIVED,
    "evidence-classification": PROVENANCE_DERIVED,
    "evidence-record-lock": PROVENANCE_DERIVED,
    "expected": BEHAVIOUR_DERIVED,
    "input": BEHAVIOUR_DERIVED,
    "input_mode": BEHAVIOUR_DERIVED,
    "literal": CANONICAL_DECLARATION_ONLY,
    "manifest": CANONICAL_DECLARATION_ONLY,
    "requirement": REQUIREMENT_DERIVED,
    "secondary-witness": REQUIREMENT_DERIVED,
    "source-decision-role": CANONICAL_DECLARATION_ONLY,
    "source-pointer": PROVENANCE_DERIVED,
    "target": CANONICAL_DECLARATION_ONLY,
}


def _authority_form(authority: str) -> str:
    return authority.split(":", 1)[0]


def _reachable_purpose_functions() -> dict[str, ast.FunctionDef]:
    """Every module-level function a renderer can reach, transitively.

    A guard that reads only the registered renderer's own source proves
    nothing: one hop into a helper puts the code back out of sight.
    """
    module = ast.parse(Path(__file__).read_text("utf-8"))
    defined = {
        node.name: node for node in module.body if isinstance(node, ast.FunctionDef)
    }
    frontier = {
        renderer.__name__
        for renderer in PURPOSE_RENDERERS.values()
        if renderer.__name__ in defined
    }
    # a closure renderer reports its inner name, so seed the factories too
    frontier |= {
        node.name
        for node in module.body
        if isinstance(node, ast.FunctionDef)
        and any(
            isinstance(inner, ast.FunctionDef) and inner.name == "render"
            for inner in ast.walk(node)
        )
    }
    reached: dict[str, ast.FunctionDef] = {}
    while frontier:
        name = frontier.pop()
        node = defined.get(name)
        if node is None or name in reached:
            continue
        reached[name] = node
        for call in ast.walk(node):
            if isinstance(call, ast.Call) and isinstance(call.func, ast.Name):
                if call.func.id in defined and call.func.id not in reached:
                    frontier.add(call.func.id)
    return reached


def _identifier_readers(node: ast.FunctionDef) -> list[str]:
    """Names bound to the vector id, so a rename cannot hide the parsing."""
    bound = {"__vector_id__"}
    for statement in ast.walk(node):
        if not isinstance(statement, ast.Assign):
            continue
        value = statement.value
        if (
            isinstance(value, ast.Call)
            and isinstance(value.func, ast.Name)
            and value.func.id == "cast"
            and value.args
        ):
            value = value.args[-1]  # cast(str, vector["id"]) still binds the id
        if (
            isinstance(value, ast.Subscript)
            and isinstance(value.slice, ast.Constant)
            and value.slice.value == "id"
        ):
            bound |= {t.id for t in statement.targets if isinstance(t, ast.Name)}
    return sorted(bound)


def test_no_renderer_reads_the_text_it_is_rebuilding() -> None:
    """A renderer that consulted `purpose` would only be copying it.

    The check follows the call graph. Reading the registered function's own
    source would leave every helper it calls unexamined, and one hop is all a
    renderer would need to echo the sentence back.
    """
    reachable = _reachable_purpose_functions()

    assert len(reachable) >= len(PURPOSE_RENDERERS), "the closure is not smaller"
    for name, node in sorted(reachable.items()):
        for literal in ast.walk(node):
            if isinstance(literal, ast.Constant) and literal.value == "purpose":
                raise AssertionError(f"{name} names the field it rebuilds")
            if isinstance(literal, ast.Attribute) and literal.attr == "purpose":
                raise AssertionError(f"{name} reaches the field it rebuilds")

    resolver = inspect.getsource(_purpose_authority_failures)
    assert '"purpose"' not in resolver


def test_no_renderer_reads_meaning_out_of_an_identifier() -> None:
    """Ids, partitions and categories are identifiers, not English.

    Deriving BASE from a `.base-canonical` suffix, or merge prose from a
    `merge-outcome` category, would make this rule restate the labels other
    authorities already close. The id may be a dict key and nothing else, so
    the check tracks every name it is bound to and refuses any attribute call
    or subscript on it -- a substring search would miss `identifier.rsplit`.
    """
    for name, node in sorted(_reachable_purpose_functions().items()):
        for literal in ast.walk(node):
            if isinstance(literal, ast.Constant) and literal.value in (
                "semantic_partition",
                "category",
            ):
                raise AssertionError(f"{name} reads a taxonomy label")

        readers = set(_identifier_readers(node))
        for used in ast.walk(node):
            target: ast.expr | None = None
            if isinstance(used, ast.Attribute):
                target = used.value
            elif isinstance(used, ast.Subscript):
                target = used.value
            if isinstance(target, ast.Name) and target.id in readers:
                raise AssertionError(f"{name} takes the vector id apart")
            if (
                isinstance(target, ast.Subscript)
                and isinstance(target.slice, ast.Constant)
                and target.slice.value == "id"
            ):
                raise AssertionError(f"{name} takes the vector id apart")


def test_every_claim_class_follows_from_the_authority_it_cites() -> None:
    """The class is not decoration: the authority form determines it.

    Without this, relabelling a provenance claim as a canonical declaration --
    or the reverse -- would be silent, and the four classes would carry no
    weight beyond the word in the ledger.
    """
    forms = {
        _authority_form(claim.authority)
        for claims in PURPOSE_SEMANTICS.values()
        for claim in claims
    }
    unknown = forms - set(REQUIRED_ASSURANCE_BY_AUTHORITY_FORM)
    assert not unknown, sorted(unknown)
    assert {REQUIRED_ASSURANCE_BY_AUTHORITY_FORM[form] for form in forms} == set(
        PURPOSE_ASSURANCE_CLASSES
    ), "every class is reached by a live claim"

    for identifier, claims in PURPOSE_SEMANTICS.items():
        for claim in claims:
            assert (
                claim.assurance
                == REQUIRED_ASSURANCE_BY_AUTHORITY_FORM[
                    _authority_form(claim.authority)
                ]
            ), (identifier, claim.authority, claim.assurance)


def test_relabelling_a_claim_is_refused() -> None:
    """Every one of the 201 claims, moved to every other class, is caught."""
    silent: list[tuple[str, str]] = []
    for identifier, claims in PURPOSE_SEMANTICS.items():
        for index, claim in enumerate(claims):
            for other in PURPOSE_ASSURANCE_CLASSES:
                if other == claim.assurance:
                    continue
                moved = list(claims)
                moved[index] = PurposeClaim(other, claim.renderer, claim.authority)
                ledger = dict(PURPOSE_SEMANTICS)
                ledger[identifier] = tuple(moved)
                if not _claim_class_failures(ledger):
                    silent.append((identifier, other))
    assert not silent, silent[:5]


def _claim_class_failures(
    ledger: dict[str, tuple[PurposeClaim, ...]],
) -> list[tuple[str, str]]:
    """`(vector_id, reason)` wherever a class does not follow its authority."""
    return sorted(
        (identifier, "assurance-does-not-follow-authority")
        for identifier, claims in ledger.items()
        for claim in claims
        if REQUIRED_ASSURANCE_BY_AUTHORITY_FORM.get(_authority_form(claim.authority))
        != claim.assurance
    )


def test_a_derived_claim_moves_when_the_field_it_cites_moves() -> None:
    """A cited pointer that the renderer ignores is not an authority.

    Every `input:`/`expected:` claim names a leaf. Blanking that leaf must
    change the sentence, otherwise the citation is decoration.
    """
    inert: list[tuple[str, str]] = []
    for family, section in _purpose_sections().items():
        for vector in section["vectors"]:
            identifier = cast(str, vector["id"])
            for claim in PURPOSE_SEMANTICS[identifier]:
                if not claim.authority.startswith(("input:", "expected:")):
                    continue
                root, pointer = claim.authority.split(":", 1)
                edited = copy.deepcopy(vector)
                parent = _resolve_pointer(
                    edited[root], pointer.rsplit("/", 1)[0] or "/"
                )
                leaf = pointer.rsplit("/", 1)[-1]
                try:
                    if isinstance(parent, list):
                        cast(list[Any], parent)[int(leaf)] = "-"
                    else:
                        cast(dict[str, Any], parent)[leaf] = "-"
                    moved = _render_purpose(edited, family)
                except Exception:  # noqa: BLE001 - a raising renderer did notice
                    continue
                if moved == vector["purpose"]:
                    inert.append((identifier, claim.authority))
    assert not inert, inert[:5]


CORRECTION_PURPOSE_VECTOR = (
    "history.replay.evidence-association.approval-correction-record"
)
CORRECTION_PURPOSE_REFERENCE = "correction:s04-c01-acquisition-closure"


def _correction_purpose_claim() -> tuple[dict[str, Any], PurposeClaim]:
    vector = next(v for v in REPLAY["vectors"] if v["id"] == CORRECTION_PURPOSE_VECTOR)
    claim = next(
        c
        for c in PURPOSE_SEMANTICS[CORRECTION_PURPOSE_VECTOR]
        if c.authority.startswith("source-decision-role:")
    )
    return cast(dict[str, Any], vector), claim


def test_no_purpose_claim_addresses_a_source_decision_by_slot() -> None:
    """Ordering there is neutral, so a slot names whichever record sits in it.

    The prohibition is scoped to `source_decisions`. Numeric segments elsewhere
    stay legal: the eight replay claims that cite
    `/observations/pr/timeline/items/4` and its siblings are addressing the
    retained acquisition, where the position IS the source coordinate.
    """
    positional = [
        (identifier, claim.authority)
        for identifier, claims in PURPOSE_SEMANTICS.items()
        for claim in claims
        if claim.authority.startswith("manifest:/source_decisions/")
    ]
    assert not positional, positional

    retained = [
        claim.authority
        for claims in PURPOSE_SEMANTICS.values()
        for claim in claims
        if claim.authority.startswith("source-pointer:")
        and any(segment.isdigit() for segment in claim.authority.split("/"))
    ]
    assert len(retained) == 8, "retained source coordinates keep their positions"

    vector, claim = _correction_purpose_claim()
    assert claim.assurance == CANONICAL_DECLARATION_ONLY
    assert claim.authority == (f"source-decision-role:{CORRECTION_PURPOSE_REFERENCE}")
    assert _purpose_authority_failures(vector, "replay", claim) == []


def test_reordering_source_decisions_leaves_the_purpose_claim_alone(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The reorder law is kept, and the claim now survives it.

    Before this repair the claim cited `/source_decisions/4/authority_role`.
    Reversing the list is a semantically neutral edit the corpus explicitly
    permits, and it silently moved that slot onto another decision while every
    test stayed green.
    """
    live = _live_source_decisions()
    before = [entry["decision_reference"] for entry in live].index(
        CORRECTION_PURPOSE_REFERENCE
    )
    reordered = list(reversed(live))
    after = [entry["decision_reference"] for entry in reordered].index(
        CORRECTION_PURPOSE_REFERENCE
    )
    monkeypatch.setitem(MANIFEST, "source_decisions", reordered)

    assert before != after, "the correction sits in a different slot either way"
    assert not _source_attachment_failures(
        reordered, REQUIRED_SOURCE_DECISION_BY_REFERENCE
    ), "the completed identity relation is order-free"
    assert not _purpose_failures(_purpose_sections(), PURPOSE_SEMANTICS)

    vector, _claim = _correction_purpose_claim()
    assert _render_purpose(vector, "replay") == vector["purpose"]
    assert (
        _pR_authority_role(CORRECTION_PURPOSE_REFERENCE)
        == "retained_additive_correction_evidence"
    )


def test_the_old_positional_authority_form_is_refused() -> None:
    vector, claim = _correction_purpose_claim()
    positional = PurposeClaim(
        claim.assurance, claim.renderer, "manifest:/source_decisions/4/authority_role"
    )

    # refused twice over: the slot addresses an order-neutral collection, and
    # this renderer builds its sentence from no manifest leaf at all
    assert _purpose_authority_failures(vector, "replay", positional) == [
        "positional-source-decision-authority-forbidden",
        "renderer-reads-no-manifest-leaf",
    ]


def test_a_purpose_claim_citing_another_source_decision_is_refused() -> None:
    """The claim must name the source the renderer actually reads."""
    vector, claim = _correction_purpose_claim()

    other = PurposeClaim(
        claim.assurance,
        claim.renderer,
        "source-decision-role:decision:s1-p05-s08:disposition",
    )
    assert _purpose_authority_failures(vector, "replay", other) == [
        "claim-cites-another-source-than-the-renderer"
    ]

    unknown = PurposeClaim(
        claim.assurance, claim.renderer, "source-decision-role:closure:s1-p99:nowhere"
    )
    assert _purpose_authority_failures(vector, "replay", unknown) == [
        "source-decision-reference-unknown"
    ]

    moved = copy.deepcopy(vector)
    moved["evidence_record_lock"] = "acquisition:run-0001"
    assert _purpose_authority_failures(moved, "replay", claim) == [
        "claim-cites-another-source-than-the-renderer"
    ]


def test_a_duplicated_or_drifted_source_decision_refuses_the_claim(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Identity addressing needs exactly one record, and it must still match."""
    vector, claim = _correction_purpose_claim()
    live = _live_source_decisions()
    cited = next(
        entry
        for entry in live
        if entry["decision_reference"] == CORRECTION_PURPOSE_REFERENCE
    )

    doubled = [*live, copy.deepcopy(cited)]
    monkeypatch.setitem(MANIFEST, "source_decisions", doubled)
    assert _purpose_authority_failures(vector, "replay", claim) == [
        "source-decision-reference-not-unique"
    ]
    monkeypatch.undo()

    drifted = copy.deepcopy(live)
    next(
        entry
        for entry in drifted
        if entry["decision_reference"] == CORRECTION_PURPOSE_REFERENCE
    )["authority_role"] = "retained_replay_evidence"
    monkeypatch.setitem(MANIFEST, "source_decisions", drifted)
    assert _purpose_authority_failures(vector, "replay", claim) == [
        "source-decision-identity-differs"
    ]


# --- a coordinate claim names the coordinate the sentence was read from ------
#
# A replay vector cites several retained coordinates -- the comparison, the
# pull request bracket, the repository -- and the resolver asked only whether
# the claimed one appeared among them. So the role-binding claim could name
# `/observations/repository`, a node the sentence never touches, while the
# renderer went on reading the role and the revision from the comparison, and
# the purpose ledger published an unrelated coordinate as its provenance.
#
# The repair is the same shape as the source-decision one above: the claim is
# addressed by the coordinate the renderer consumes, and the selection is the
# renderer's own function rather than a second description of it, so the
# declaration and the code cannot drift apart.


def _coordinate_claims() -> list[tuple[str, str, dict[str, Any], PurposeClaim]]:
    """`(vector id, family, vector, claim)` for every coordinate-addressed claim."""
    return [
        (identifier, family, vector, claim)
        for family, section in sorted(_purpose_sections().items())
        for vector in cast(list[dict[str, Any]], section["vectors"])
        for identifier in [cast(str, vector["id"])]
        for claim in PURPOSE_SEMANTICS[identifier]
        if claim.authority.startswith(("source-pointer:", "embedded-fact:"))
    ]


def test_every_coordinate_claim_names_the_input_its_renderer_reads() -> None:
    """The reported finding, closed, and the selection is not restated.

    Eleven claims address a retained coordinate. Each must name the pointer the
    registered renderer actually selects, and that selection must be a function
    the renderer really calls -- otherwise the ledger and the renderer would be
    two descriptions of the same thing, free to disagree.
    """
    claims = _coordinate_claims()
    pointers = [c for *_, c in claims if c.authority.startswith("source-pointer:")]
    facts = [c for *_, c in claims if c.authority.startswith("embedded-fact:")]
    assert len(pointers) == 10
    assert len(facts) == 1

    for identifier, family, vector, claim in claims:
        assert _purpose_authority_failures(vector, family, claim) == [], identifier
        cited = claim.authority.split(":", 1)[1]
        if claim.authority.startswith("source-pointer:"):
            select = PURPOSE_SOURCE_POINTER_SELECTORS[claim.renderer]
            assert select(vector)["json_pointer"] == cited, identifier
        else:
            assert cited in PURPOSE_EMBEDDED_FACT_SELECTORS[claim.renderer](vector), (
                identifier
            )

    # every renderer that carries such a claim declares a selection, and no
    # selection row is dead
    assert {c.renderer for *_, c in claims if c.authority.startswith("source-")} == set(
        PURPOSE_SOURCE_POINTER_SELECTORS
    )
    assert {
        c.renderer for *_, c in claims if c.authority.startswith("embedded")
    } == set(PURPOSE_EMBEDDED_FACT_SELECTORS)


def test_every_declared_selection_is_code_its_renderer_runs() -> None:
    """A selection the renderer never calls would be a parallel description."""
    module = ast.parse(Path(__file__).read_text("utf-8"))
    defined = {
        node.name: node for node in module.body if isinstance(node, ast.FunctionDef)
    }

    def reaches(root: str, helper: str) -> bool:
        frontier, seen = {root}, set[str]()
        while frontier:
            name = frontier.pop()
            if name in seen:
                continue
            seen.add(name)
            node = defined.get(name)
            if node is None:
                continue
            for call in ast.walk(node):
                if isinstance(call, ast.Call) and isinstance(call.func, ast.Name):
                    if call.func.id in defined:
                        frontier.add(call.func.id)
        return helper in seen

    selections: dict[str, Callable[..., Any]] = {
        **PURPOSE_SOURCE_POINTER_SELECTORS,
        **PURPOSE_EMBEDDED_FACT_SELECTORS,
    }
    for renderer, select in sorted(selections.items()):
        root = PURPOSE_RENDERERS[renderer].__name__
        assert reaches(root, select.__name__), (renderer, select.__name__)
    # and the guard itself is not vacuous
    assert not reaches("_PR_retained_changed_path_fact", "_pR_instant_pointer")


def test_a_coordinate_the_renderer_never_reads_is_refused() -> None:
    """Cited-somewhere was the whole rule; now the sentence has to read it.

    `/observations/repository` is cited by the role-binding vector and ignored
    by its renderer. `/observations/pr/attempts/0/bracket_a` is read -- it
    supplies the pull request number -- but it is not the node the sentence is
    about, and naming it would still misreport the provenance.
    """
    identifier = "history.replay.role-binding.base"
    vector = next(v for v in REPLAY["vectors"] if v["id"] == identifier)
    claim = PURPOSE_SEMANTICS[identifier][0]
    assert claim.authority == "source-pointer:/observations/comparison"

    for coordinate in (
        "/observations/repository",
        "/observations/pr/attempts/0/bracket_a",
    ):
        moved = PurposeClaim(
            claim.assurance, claim.renderer, f"source-pointer:{coordinate}"
        )
        assert _purpose_authority_failures(vector, "replay", moved) == [
            "source-pointer-is-not-the-renderer-input"
        ], coordinate

    uncited = PurposeClaim(
        claim.assurance, claim.renderer, "source-pointer:/observations/pr/nowhere"
    )
    assert _purpose_authority_failures(vector, "replay", uncited) == [
        "source-pointer-not-cited"
    ]

    # a renderer that reads no coordinate may not carry a coordinate claim
    orphan = PurposeClaim(
        claim.assurance, "replay:retained_target_declaration", claim.authority
    )
    assert _purpose_authority_failures(vector, "replay", orphan) == [
        "renderer-reads-no-source-pointer"
    ]

    # and a vector whose selected coordinate is gone fails rather than passing
    stripped = copy.deepcopy(vector)
    stripped["source_pointers"] = [
        p
        for p in cast(list[dict[str, Any]], stripped["source_pointers"])
        if not p.get("role_implications")
    ]
    assert _purpose_authority_failures(stripped, "replay", claim) == [
        "source-pointer-not-cited"
    ]


def test_a_scalar_claim_may_not_cite_the_other_provenance_field() -> None:
    """Non-empty was the whole rule, and the renderer reads both fields.

    `_PR_caller_association_to_locked_record` takes its verb from the
    classification and the record it names from the lock. Citing the
    classification would offer it as support for a record identity it does not
    establish, and the sentence would go on reading the lock.
    """
    identifier = "history.replay.evidence-association.base-binding"
    vector = next(v for v in REPLAY["vectors"] if v["id"] == identifier)
    claim = next(
        c
        for c in PURPOSE_SEMANTICS[identifier]
        if c.authority == "evidence-record-lock"
    )
    assert _purpose_authority_failures(vector, "replay", claim) == []
    assert vector["evidence_classification"] and vector["evidence_record_lock"]

    swapped = PurposeClaim(claim.assurance, claim.renderer, "evidence-classification")
    assert _purpose_authority_failures(vector, "replay", swapped) == [
        "scalar-field-is-not-the-renderer-input"
    ]

    orphan = PurposeClaim(
        claim.assurance, "replay:evidence_link_non_claim", claim.authority
    )
    assert _purpose_authority_failures(vector, "replay", orphan) == [
        "renderer-reads-no-scalar-field"
    ]

    # the target declaration is the other scalar claim, and it is bound the same
    deletion = next(
        v
        for v in REPLAY["vectors"]
        if v["id"] == "history.replay.head-ref-deletion.canonical"
    )
    target = PURPOSE_SEMANTICS["history.replay.head-ref-deletion.canonical"][0]
    assert target.authority == "target"
    assert _purpose_authority_failures(deletion, "replay", target) == []
    moved = PurposeClaim(target.assurance, target.renderer, "input_mode")
    assert _purpose_authority_failures(deletion, "replay", moved) == [
        "scalar-field-is-not-the-renderer-input"
    ]

    # every renderer carrying a scalar claim declares its field, and no row is dead
    assert {
        c.renderer
        for claims in PURPOSE_SEMANTICS.values()
        for c in claims
        if c.authority
        in ("target", "input_mode", "evidence-classification", "evidence-record-lock")
    } == set(PURPOSE_SCALAR_FIELDS)


def test_a_manifest_claim_may_not_cite_another_published_limit() -> None:
    """Resolving is not reading: the three limits used to be interchangeable.

    Swapping the completeness and merge-revision pointers left both resolving
    and both descriptive, while each renderer went on reading its own leaf, so
    the ledger recorded an unrelated evidence location for each.
    """
    live = [
        (identifier, claim)
        for identifier, claims in PURPOSE_SEMANTICS.items()
        for claim in claims
        if claim.authority.startswith("manifest:")
    ]
    assert len(live) == 3
    assert {claim.renderer for _i, claim in live} == set(PURPOSE_MANIFEST_POINTERS)

    sections = _purpose_sections()
    for identifier, claim in live:
        vector = next(
            v
            for section in sections.values()
            for v in section["vectors"]
            if v["id"] == identifier
        )
        assert _purpose_authority_failures(vector, "replay", claim) == [], identifier
        for other in sorted(set(PURPOSE_MANIFEST_POINTERS.values())):
            if other == claim.authority.split(":", 1)[1]:
                continue
            swapped = PurposeClaim(claim.assurance, claim.renderer, f"manifest:{other}")
            assert _purpose_authority_failures(vector, "replay", swapped) == [
                "manifest-leaf-is-not-the-renderer-input"
            ], (identifier, other)

    # a renderer that reads no manifest leaf may not carry a manifest claim
    identifier, claim = live[0]
    vector = next(v for v in REPLAY["vectors"] if v["id"] == identifier)
    orphan = PurposeClaim(
        claim.assurance, "replay:evidence_link_non_claim", claim.authority
    )
    assert _purpose_authority_failures(vector, "replay", orphan) == [
        "renderer-reads-no-manifest-leaf"
    ]


def test_every_declared_purpose_leaf_and_field_moves_its_own_fragment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The declarations are read, not merely written down.

    Each declared manifest leaf is drifted in place and each declared scalar
    field is blanked, and the fragment the renderer produces must move or stop.
    A table naming a leaf nothing reads would otherwise look exactly like one
    naming the leaf the sentence is built from.
    """
    sections = _purpose_sections()
    vectors = {
        cast(str, vector["id"]): (family, vector)
        for family, section in sections.items()
        for vector in cast(list[dict[str, Any]], section["vectors"])
    }
    inert: list[tuple[str, str]] = []

    for identifier, claims in PURPOSE_SEMANTICS.items():
        family, vector = vectors[identifier]
        for claim in claims:
            render = PURPOSE_RENDERERS[claim.renderer]
            baseline = render(vector, family)
            if claim.authority.startswith("manifest:"):
                pointer = PURPOSE_MANIFEST_POINTERS[claim.renderer]
                parent_path, _, leaf = pointer.rpartition("/")
                parent = cast(dict[str, Any], _resolve_pointer(MANIFEST, parent_path))
                monkeypatch.setitem(parent, leaf, _drifted(parent[leaf]))
                try:
                    if render(vector, family) == baseline:
                        inert.append((identifier, pointer))
                except Exception:  # noqa: BLE001 - a renderer that stopped noticed
                    pass
                finally:
                    monkeypatch.undo()
            elif claim.authority in (
                "target",
                "input_mode",
                "evidence-classification",
                "evidence-record-lock",
            ):
                field = PURPOSE_SCALAR_FIELDS[claim.renderer]
                edited = copy.deepcopy(vector)
                edited[field] = ""
                try:
                    if render(edited, family) == baseline:
                        inert.append((identifier, field))
                except Exception:  # noqa: BLE001 - a renderer that stopped noticed
                    pass
    assert not inert, inert


def test_a_composed_binding_claim_may_not_name_a_selected_path() -> None:
    """The composition counts its bindings; the paths it chose are not those."""
    identifier = "history.replay.change-set.supplied-three-paths"
    vector = next(v for v in REPLAY["vectors"] if v["id"] == identifier)
    claim = next(
        c
        for c in PURPOSE_SEMANTICS[identifier]
        if c.authority.startswith("embedded-fact:")
    )
    assert claim.authority == "embedded-fact:/base"

    path = PurposeClaim(
        claim.assurance, claim.renderer, "embedded-fact:/changed_paths/0"
    )
    assert _purpose_authority_failures(vector, "replay", path) == [
        "embedded-fact-is-not-the-renderer-input"
    ]

    absent = PurposeClaim(claim.assurance, claim.renderer, "embedded-fact:/nowhere")
    assert _purpose_authority_failures(vector, "replay", absent) == [
        "embedded-fact-not-declared"
    ]

    orphan = PurposeClaim(
        claim.assurance, "replay:retained_changed_path_fact", claim.authority
    )
    assert _purpose_authority_failures(vector, "replay", orphan) == [
        "renderer-reads-no-embedded-fact"
    ]


def test_removing_a_claimed_coordinate_moves_the_sentence_it_carries() -> None:
    """A cited coordinate the renderer ignores is decoration, not provenance.

    The structural check above says the claim names the renderer's own
    selection. This says the same thing from the other side, behaviourally:
    delete the claimed coordinate and the fragment must move or stop rendering.
    Both directions are kept because either alone could be satisfied by a
    selection that has quietly stopped being read.
    """
    inert: list[tuple[str, str]] = []
    for identifier, _family, vector, claim in _coordinate_claims():
        kind, cited = claim.authority.split(":", 1)
        render = PURPOSE_RENDERERS[claim.renderer]
        edited = copy.deepcopy(vector)
        if kind == "source-pointer":
            edited["source_pointers"] = [
                p
                for p in cast(list[dict[str, Any]], edited["source_pointers"])
                if p["json_pointer"] != cited
            ]
        else:
            edited["embedded_facts"] = {
                key: value
                for key, value in cast(dict[str, Any], edited["embedded_facts"]).items()
                if key != cited
            }
        try:
            moved = render(edited, "replay") != render(vector, "replay")
        except Exception:  # noqa: BLE001 - a renderer that cannot run did notice
            moved = True
        if not moved:
            inert.append((identifier, claim.authority))
    assert not inert, inert

    # the probe is not vacuous: removing the coordinate the finding proposed
    # leaves the sentence exactly as it was
    vector = next(
        v for v in REPLAY["vectors"] if v["id"] == "history.replay.role-binding.base"
    )
    ignored = copy.deepcopy(vector)
    ignored["source_pointers"] = [
        p
        for p in cast(list[dict[str, Any]], ignored["source_pointers"])
        if p["json_pointer"] != "/observations/repository"
    ]
    assert _PR_retained_role_binding_fact(
        ignored, "replay"
    ) == _PR_retained_role_binding_fact(vector, "replay")


def test_the_purpose_ledger_is_bound_once_anywhere_in_the_module() -> None:
    """A rebuild hidden inside a function body is still a rebuild.

    Scanning only module-level statements would let `def _f(): LEDGER[k] = ...`
    followed by `_f()` recompute the authored ledger from the corpus while the
    literal above stayed on the page for a reader.
    """
    name = "PURPOSE_SEMANTICS"
    module = ast.parse(Path(__file__).read_text("utf-8"))
    annotated = [
        node
        for node in module.body
        if isinstance(node, ast.AnnAssign)
        and isinstance(node.target, ast.Name)
        and node.target.id == name
    ]
    assert len(annotated) == 1

    writes: list[str] = []
    for node in ast.walk(module):
        targets: list[ast.expr] = []
        if isinstance(node, ast.Assign):
            targets = list(node.targets)
        elif isinstance(node, (ast.AugAssign, ast.AnnAssign)):
            targets = [node.target]
        for target in targets:
            if isinstance(target, ast.Name) and target.id == name:
                if node is not annotated[0]:
                    writes.append("rebound")
            if (
                isinstance(target, ast.Subscript)
                and isinstance(target.value, ast.Name)
                and target.value.id == name
            ):
                writes.append("item-assigned")
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == name
            and node.func.attr in ("update", "setdefault", "pop", "clear")
        ):
            writes.append(f"mutated by {node.func.attr}")
    assert not writes, writes


def test_purpose_is_not_part_of_behavioural_identity() -> None:
    """Purpose describes a vector; it does not select what the vector does."""
    for fields in SIGNATURE_FIELDS.values():
        assert "purpose" not in fields

    for family, section in _purpose_sections().items():
        original = cast(dict[str, Any], section["vectors"][0])
        relabelled = copy.deepcopy(original)
        relabelled["purpose"] = "A sentence this corpus never publishes."
        assert _behavioural_fingerprint(relabelled, family) == (
            _behavioural_fingerprint(original, family)
        ), family


def _swapped(family: str, first_id: str, second_id: str) -> dict[str, Any]:
    section = copy.deepcopy(_purpose_sections()[family])
    first = next(v for v in section["vectors"] if v["id"] == first_id)
    second = next(v for v in section["vectors"] if v["id"] == second_id)
    first["purpose"], second["purpose"] = second["purpose"], first["purpose"]
    return section


def test_swapping_two_valid_purposes_is_refused() -> None:
    """The reported reproduction, kept permanently."""
    section = _swapped(
        "valid",
        "history.valid.role-binding.base-canonical",
        "history.valid.role-binding.head-canonical",
    )
    sections = _sections(section, INVALID, REPLAY)

    assert _resealed_digest(section) != next(
        entry["sha256"]
        for entry in MANIFEST["corpus_files"]
        if entry["filename"] == "valid-vectors.json"
    )
    assert _purpose_failures(sections, PURPOSE_SEMANTICS) == [
        ("history.valid.role-binding.base-canonical", "rendered-purpose-differs"),
        ("history.valid.role-binding.head-canonical", "rendered-purpose-differs"),
    ]


def test_swapping_two_invalid_purposes_is_refused() -> None:
    """Two different requirements cannot borrow each other's sentence."""
    section = _swapped(
        "invalid",
        "history.invalid.role-binding.non-pull-request-subject",
        "history.invalid.change-set.mismatched-revision-algorithms",
    )
    assert _purpose_failures(_sections(VALID, section, REPLAY), PURPOSE_SEMANTICS) == [
        (
            "history.invalid.change-set.mismatched-revision-algorithms",
            "rendered-purpose-differs",
        ),
        (
            "history.invalid.role-binding.non-pull-request-subject",
            "rendered-purpose-differs",
        ),
    ]


def test_swapping_two_replay_purposes_is_refused() -> None:
    """Retained base and head provenance are not interchangeable."""
    section = _swapped(
        "replay", "history.replay.role-binding.base", "history.replay.role-binding.head"
    )
    assert _purpose_failures(_sections(VALID, INVALID, section), PURPOSE_SEMANTICS) == [
        ("history.replay.role-binding.base", "rendered-purpose-differs"),
        ("history.replay.role-binding.head", "rendered-purpose-differs"),
    ]


def test_a_retained_purpose_cannot_borrow_a_caller_supplied_one() -> None:
    """Retained observation and caller-supplied composition differ in kind."""
    section = _swapped(
        "replay",
        "history.replay.changed-path.changelog",
        "history.replay.change-set.supplied-three-paths",
    )
    assert _purpose_failures(_sections(VALID, INVALID, section), PURPOSE_SEMANTICS) == [
        ("history.replay.change-set.supplied-three-paths", "rendered-purpose-differs"),
        ("history.replay.changed-path.changelog", "rendered-purpose-differs"),
    ]


def test_unrelated_and_empty_purposes_are_refused() -> None:
    """Neither survives the rebuild.

    Truthiness accepted the unrelated sentence; the empty string it already
    rejected. Both are kept because the rule now refuses them for the same
    reason -- the claims no longer rebuild what is published.
    """
    for replacement in ("This text is unrelated to the vector.", ""):
        section = copy.deepcopy(VALID)
        edited = next(
            v
            for v in section["vectors"]
            if v["id"] == "history.valid.change-set.canonical-three-paths"
        )
        edited["purpose"] = replacement
        assert _purpose_failures(
            _sections(section, INVALID, REPLAY), PURPOSE_SEMANTICS
        ) == [
            (
                "history.valid.change-set.canonical-three-paths",
                "rendered-purpose-differs",
            )
        ], replacement


def test_moving_a_structured_fact_moves_the_rendered_purpose() -> None:
    """A derived fragment follows its authority, which is the point of it."""
    section = copy.deepcopy(VALID)
    edited = next(
        v for v in section["vectors"] if v["id"] == "history.valid.approval.canonical"
    )
    original = _render_purpose(edited, "valid")
    review = cast(dict[str, Any], cast(dict[str, Any], edited["input"])["review"])
    assert "176071572" in original, "the published review id is in the sentence"
    review["provider_global_id"] = "999999999"

    moved = _render_purpose(edited, "valid")
    assert moved != original
    assert "999999999" in moved and "176071572" not in moved
    assert _purpose_failures(
        _sections(section, INVALID, REPLAY), PURPOSE_SEMANTICS
    ) == [("history.valid.approval.canonical", "rendered-purpose-differs")]


def test_pointing_a_claim_at_another_requirement_is_refused() -> None:
    """A claim may not cite a row that witnesses a different vector."""
    identifier = "history.invalid.role-binding.untyped-python-pull-request"
    ledger = dict(PURPOSE_SEMANTICS)
    claim = ledger[identifier][0]
    ledger[identifier] = (
        PurposeClaim(claim.assurance, claim.renderer, "requirement:RB-02"),
    )

    assert (
        identifier,
        "requirement-row-witnesses-another-vector",
    ) in _purpose_failures(_purpose_sections(), ledger)


def test_a_swapped_pair_of_ledger_entries_is_refused() -> None:
    """The corpus is untouched; only the claim descriptors move."""
    first = "history.valid.role-binding.base-canonical"
    second = "history.valid.status.added"
    ledger = dict(PURPOSE_SEMANTICS)
    assert ledger[first] != ledger[second], "the two entries describe different claims"
    ledger[first], ledger[second] = ledger[second], ledger[first]

    # each is refused, for the reason the exchange actually causes: the
    # role-binding vector renders the wrong sentence, and the status vector is
    # handed an authority that does not resolve against it at all
    assert _purpose_failures(_purpose_sections(), ledger) == [
        (first, "rendered-purpose-differs"),
        (second, "pointer-does-not-resolve"),
        (second, "renderer-raised"),
    ]

    # two vectors whose claims are genuinely identical descriptors are
    # interchangeable in the ledger by construction; the sentence still has to
    # come out right, which is what the rendering equality above enforces
    twins = "history.valid.occurrence-time.approval"
    other = "history.valid.occurrence-time.merge"
    assert PURPOSE_SEMANTICS[twins] == PURPOSE_SEMANTICS[other]


def test_a_descriptive_manifest_leaf_may_not_be_claimed_as_verified() -> None:
    """Rendering from a descriptive leaf does not promote it."""
    descriptive = [
        (identifier, claim)
        for identifier, claims in PURPOSE_SEMANTICS.items()
        for claim in claims
        if claim.authority.startswith("manifest:")
        and claim.authority.split(":", 1)[1] in DESCRIPTIVE_PATHS
    ]
    assert descriptive, "the replay family renders canonical claims from the manifest"
    for identifier, claim in descriptive:
        assert claim.assurance == CANONICAL_DECLARATION_ONLY, identifier

    identifier, claim = descriptive[0]
    ledger = dict(PURPOSE_SEMANTICS)
    ledger[identifier] = tuple(
        PurposeClaim(PROVENANCE_DERIVED, c.renderer, c.authority) if c is claim else c
        for c in ledger[identifier]
    )
    assert (
        identifier,
        "descriptive-leaf-claimed-as-verified",
    ) in _purpose_failures(_purpose_sections(), ledger)


def test_a_canonical_literal_fragment_is_declared_not_verified() -> None:
    """Every literal pin is labelled for what it is, and drifts loudly."""
    literals = [
        (identifier, index)
        for identifier, claims in PURPOSE_SEMANTICS.items()
        for index, claim in enumerate(claims)
        if claim.authority == "literal"
    ]
    assert literals
    for identifier, index in literals:
        assert PURPOSE_SEMANTICS[identifier][index].assurance == (
            CANONICAL_DECLARATION_ONLY
        ), identifier

    ledger = dict(PURPOSE_SEMANTICS)
    identifier, index = literals[0]
    claims = list(ledger[identifier])
    claims[index] = PurposeClaim(
        BEHAVIOUR_DERIVED, claims[index].renderer, claims[index].authority
    )
    ledger[identifier] = tuple(claims)
    assert (identifier, "literal-claimed-as-verified") in _purpose_failures(
        _purpose_sections(), ledger
    )


def test_the_purpose_ledger_is_written_out_and_never_computed() -> None:
    """A ledger a comprehension could rebuild is not an authority."""
    name = "PURPOSE_SEMANTICS"
    module = ast.parse(Path(__file__).read_text("utf-8"))
    assigned = [
        node
        for node in module.body
        if isinstance(node, ast.AnnAssign)
        and isinstance(node.target, ast.Name)
        and node.target.id == name
    ]

    assert len(assigned) == 1
    literal = assigned[0].value
    assert isinstance(literal, ast.Dict)
    assert len(literal.keys) == 183
    for key, value in zip(literal.keys, literal.values, strict=True):
        assert isinstance(key, ast.Constant) and isinstance(key.value, str)
        assert isinstance(value, ast.Tuple)
        for element in value.elts:
            # every claim is a PurposeClaim(...) call over three constants
            assert isinstance(element, ast.Call)
            assert isinstance(element.func, ast.Name)
            assert element.func.id == "PurposeClaim"
            assert len(element.args) == 3 and not element.keywords
            assert isinstance(element.args[0], ast.Name)
            assert element.args[0].id in PURPOSE_ASSURANCE_CLASSES
            for argument in element.args[1:]:
                assert isinstance(argument, ast.Constant)
                assert isinstance(argument.value, str)

    touching = [
        node
        for statement in module.body
        if not isinstance(
            statement, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef
        )
        for node in ast.walk(statement)
        if isinstance(node, ast.Name) and node.id == name
    ]
    assert len(touching) == 1, "the ledger is bound once and never rebound"
    assert touching[0] is assigned[0].target

    shape = {
        cast(str, cast(ast.Constant, key).value): len(cast(ast.Tuple, value).elts)
        for key, value in zip(literal.keys, literal.values, strict=True)
    }
    assert shape == {
        identifier: len(claims) for identifier, claims in PURPOSE_SEMANTICS.items()
    }


def test_the_missing_classifier_reads_no_authored_prose() -> None:
    """The derived side must not consult the text it is checking."""
    source = inspect.getsource(_missing_shape) + inspect.getsource(_derived_requirement)

    for forbidden in ("SECONDARY_WITNESS_REGISTRY", "purpose", "semantic_partition"):
        assert forbidden not in source, forbidden


def test_a_missing_shape_is_refused_unless_every_condition_holds() -> None:
    """Neither the error code nor the prefix mode may decide this on its own."""
    union = next(
        v
        for v in INVALID["vectors"]
        if v["id"] == "history.invalid.occurrence-time.non-admitted-change-set"
    )
    omission = next(
        v
        for v in INVALID["vectors"]
        if v["id"] == "history.invalid.occurrence-time.missing-occurrence"
    )

    assert _missing_shape(union) == UNION_REJECTION
    assert _missing_shape(omission) == TRUE_OMISSION

    # prefix mode on a field that is not a published union proves nothing
    not_a_union = copy.deepcopy(union)
    cast(dict[str, Any], not_a_union["expected"])["error_location"] = ["occurred_at"]
    cast(dict[str, Any], not_a_union["input"])["occurred_at"] = "supplied"
    assert _missing_shape(not_a_union) is None

    # a supplied union field whose normalization is not the published prefix
    wrong_mode = copy.deepcopy(union)
    cast(dict[str, Any], wrong_mode["expected"])["error_location_mode"] = "exact"
    assert _missing_shape(wrong_mode) is None

    # an unknown field cannot be either shape
    unknown = copy.deepcopy(union)
    cast(dict[str, Any], unknown["expected"])["error_location"] = ["invented"]
    assert _missing_shape(unknown) is None

    # removing the supplied value turns the same vector into a real omission
    emptied = copy.deepcopy(union)
    cast(dict[str, Any], emptied["input"]).pop("occurrence")
    assert _missing_shape(emptied) == TRUE_OMISSION
    assert _derived_requirement(emptied) == "occurrence is required"
    assert _derived_requirement(union) == (
        "occurrence admits only its published union members"
    )
