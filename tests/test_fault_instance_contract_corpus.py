"""Executes the sealed S1.P06.S11 FaultInstance contract corpus.

This file exists for one corpus. It is deliberately not a framework for later
phases: every registry in it is authored for the accumulated S1.P06 surface and
fails closed on anything it does not already name.
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
import sys
import uuid
from collections import Counter
from collections.abc import Iterator
from enum import Enum
from pathlib import Path
from typing import Any, cast

import pytest
from pydantic import BaseModel, ValidationError
from test_package import assert_current_inventory

import faultatlas.domain.fault as fault_module
import faultatlas.domain.fault_evidence_link as evidence_link_module
import faultatlas.domain.fault_instance as instance_module
import faultatlas.domain.fault_interpretation as interpretation_module
import faultatlas.domain.fault_repair as repair_module
import faultatlas.domain.fault_source_relationship as source_relationship_module
import faultatlas.domain.fault_test as test_module
from faultatlas.domain import (
    evidence,
    history,
    history_evidence_link,
    identity,
    revision,
    snapshot_evidence_link,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
CORPUS = REPOSITORY_ROOT / "reference_corpus/contracts/fault-instance/v1"

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

# The seven owned modules, in the order the corpus declares them.
OWNED_MODULES: dict[str, Any] = {
    "faultatlas.domain.fault": fault_module,
    "faultatlas.domain.fault_source_relationship": source_relationship_module,
    "faultatlas.domain.fault_repair": repair_module,
    "faultatlas.domain.fault_test": test_module,
    "faultatlas.domain.fault_interpretation": interpretation_module,
    "faultatlas.domain.fault_instance": instance_module,
    "faultatlas.domain.fault_evidence_link": evidence_link_module,
}

# Support values a vector may name. Deliberately closed, and deliberately not
# owned: none of these counts toward the thirty.
SUPPORT_TARGETS: dict[str, Any] = {
    "ChangedPathStatus": history.ChangedPathStatus,
    "DurableEvidenceRecordReference": evidence.DurableEvidenceRecordReference,
    "GitBlobIdentity": revision.GitBlobIdentity,
    "GitCommitIdentity": revision.GitCommitIdentity,
    "NumberedSourceObjectIdentity": identity.NumberedSourceObjectIdentity,
    "ProviderScopedSourceObjectIdentity": identity.ProviderScopedSourceObjectIdentity,
    "PullRequestChangeSet": history.PullRequestChangeSet,
    "PullRequestChangedPath": history.PullRequestChangedPath,
    "PullRequestHeadRefDeletion": history.PullRequestHeadRefDeletion,
    "PullRequestHistoricalOccurrenceTime": history.PullRequestHistoricalOccurrenceTime,
    "PullRequestHistoryFactEvidenceLink": (
        history_evidence_link.PullRequestHistoryFactEvidenceLink
    ),
    "PullRequestMergeRevisionOutcome": history.PullRequestMergeRevisionOutcome,
    "PullRequestReviewRevisionApproval": history.PullRequestReviewRevisionApproval,
    "PullRequestRevisionRoleBinding": history.PullRequestRevisionRoleBinding,
    "RepositoryIdentity": identity.RepositoryIdentity,
    "RepositorySnapshotFactEvidenceLink": (
        snapshot_evidence_link.RepositorySnapshotFactEvidenceLink
    ),
}
SUPPORT_MODULES = (
    "faultatlas.domain.evidence",
    "faultatlas.domain.history",
    "faultatlas.domain.history_evidence_link",
    "faultatlas.domain.identity",
    "faultatlas.domain.revision",
    "faultatlas.domain.snapshot_evidence_link",
)

# The production module count is two facts now, not one. The sealed
# `S1.P06.S11` manifest and the sealed `S1.P06.S10` decision both recorded
# twenty, and those bytes go on saying twenty; the live tree carries one more.
SEALED_PRODUCTION_MODULE_COUNT = 20
# Added by `S1.P07.S01`, the first `S1.P07` production module.
PATTERN_MODULE = "src/faultatlas/domain/pattern.py"
# Added by `S1.P07.S02`, after the sealed predecessor inventories.
PATTERN_EXEMPLAR_MODULE = "src/faultatlas/domain/pattern_exemplar.py"
# Added by `S1.P07.S03`; sealed predecessor inventories remain unchanged.
INVARIANT_MODULE = "src/faultatlas/domain/invariant.py"
# Added by `S1.P07.S04`; immutable baseline inventories are unchanged.
INVARIANT_RELATIONSHIP_MODULE = "src/faultatlas/domain/invariant_relationship.py"
PATTERN_COMPOSITION_MODULE = "src/faultatlas/domain/pattern_composition.py"
ALLOWED_MARKERS = ("enum_value", "indexed_value", "tuple_value", "typed_value")
MAX_INDEXED_COUNT = 4097
ALLOWED_OPERATIONS = ("construct", "reject")
LOCATION_MODES = ("exact", "prefix")
ALLOWED_INPUT_MODES = ("json", "python", "replay")
FAILURE_CATEGORIES = ("validation_error", "vocabulary_error")
ACCEPTED, REJECTED = "accepted", "rejected"

# The only positions whose refusal may be recorded by location prefix. Each is a
# union without a discriminator, so Pydantic reports a location per branch and
# those branch labels are not a published contract.
DISCRIMINATORLESS_UNIONS = {
    "FaultReportHistoryFactAssociation.history_fact": (
        "FaultReportHistoryFactAssociation",
        "history_fact",
    ),
    "FaultReportSourceObjectAssociation.source_object": (
        "FaultReportSourceObjectAssociation",
        "source_object",
    ),
    "FaultInstanceEvidenceLink.subject": ("FaultInstanceEvidenceLink", "subject"),
}

# Each published rule that refuses at the document root, and the fragment of
# that module's OWN authored ValueError text which names it. Several of these
# rules report `value_error` with an empty location, so type and location alone
# cannot tell them apart: a vector meant to prove one could trip another and
# still satisfy the oracle. The fragments below are written by the sealed
# modules themselves, not by the validator library, so naming a rule locks no
# envelope prose and no branch label.
ROOT_RULE_SIGNATURES = {
    "distinct_run_subjects": "before and after must report distinct run subjects",
    "layer_references_are_members": (
        "references a value this composition does not carry"
    ),
    "one_supplied_test_material": (
        "before and after must report the same supplied test material"
    ),
    "report_references_are_members": (
        "references a report this composition does not carry"
    ),
    "reports_name_the_composed_fault": "describes a different fault subject",
    "subject_is_composed_member": "is not a member of fault_instance.",
    "unique_primary_subjects": "names one subject identity more than once",
}

REPLAY_CLASSIFICATIONS = (
    "caller_supplied_association",
    "caller_supplied_composition",
    "caller_supplied_identity",
    "caller_supplied_record",
    "retained_normalized_observation",
)
FIXTURE_PROVENANCES = ("retained_case_value", "synthetic_caller_supplied")


def _owned_targets() -> dict[str, Any]:
    """The thirty S1.P06 targets, derived from live `__all__` values."""
    targets: dict[str, Any] = {}
    for module in OWNED_MODULES.values():
        for name in cast(list[str], module.__all__):
            targets[name] = getattr(module, name)
    return targets


OWNED = _owned_targets()
RESOLVABLE: dict[str, Any] = {**OWNED, **SUPPORT_TARGETS}
ENUM_TARGETS: dict[str, Any] = {
    name: value
    for name, value in RESOLVABLE.items()
    if isinstance(value, type) and issubclass(value, Enum)
}


def _reject_number(literal: str) -> Any:
    """Refuse a non-integer JSON number before it can become a Python value.

    `json.loads` accepts `NaN`, `Infinity` and `-Infinity` by default and round
    trips them faithfully, so a permissive parser plus a round-trip check would
    call a document canonical that is not standards-compliant JSON at all. The
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
    """The single strict loader every corpus document is read through."""
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

CARDINALITY = cast(dict[str, Any], MANIFEST["execution_contract"]["cardinality_probes"])
CARDINALITY_DUMP_EXEMPT = frozenset(
    cast(list[str], CARDINALITY["may_omit_semantic_dump"])
)
BOUND_PROBES = frozenset(cast(list[str], CARDINALITY["bound_probe_vectors"]))

FAMILIES = (
    ("valid", VALID, frozenset({"json", "python"}), frozenset({"construct"})),
    ("invalid", INVALID, frozenset({"json", "python"}), frozenset({"reject"})),
    ("replay", REPLAY, frozenset({"replay"}), frozenset({"construct"})),
)
ALL_VECTORS: list[dict[str, Any]] = [
    cast(dict[str, Any], vector)
    for _, section, _, _ in FAMILIES
    for vector in cast(list[Any], section["vectors"])
]

# --- the one declared cardinality template -----------------------------------
#
# The marker exists so the executor can synthesize a declared sequence for the
# bound probes without a four-thousand-member JSON file. Its meaning is spelled
# out here, it is deterministic, and it is expanded into published values before
# anything reaches production validation.

GENERATED_REPORT_TEMPLATE = "generated-fault-report"
GENERATED_CONTEXT: dict[str, Any] = {
    "fault": "12345678-1234-4234-8234-123456789abc",
    "repository": {
        "provider": "github",
        "provider_repository_id": "37489525",
        "schema_version": 1,
    },
}


def _generated_fault_reports(count: int) -> tuple[Any, ...]:
    context = fault_module.FaultRepositoryContext.model_validate_json(
        json.dumps(GENERATED_CONTEXT)
    )
    return tuple(
        fault_module.SuppliedFaultReport(
            report=fault_module.FaultReportIdentity(uuid.UUID(int=index)),
            context=context,
            problem_statement=(f"Generated bounded-composition probe member {index}."),
            behavioral_deviation="Generated bounded-composition probe deviation.",
        )
        for index in range(1, count + 1)
    )


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
            key
            for key in mapping
            if key.endswith("_value") and key not in ALLOWED_MARKERS
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
    if marker == "indexed_value":
        spec_indexed = cast(dict[str, Any], payload)
        count = cast(int, spec_indexed["count"])
        assert spec_indexed["target"] == "SuppliedFaultReport", spec_indexed
        assert spec_indexed["template"] == GENERATED_REPORT_TEMPLATE, spec_indexed
        assert 0 < count <= MAX_INDEXED_COUNT, f"indexed count out of bounds: {count}"
        return _generated_fault_reports(count)
    spec = cast(dict[str, Any], payload)
    target = cast(str, spec["target"])
    if marker == "enum_value":
        assert target in ENUM_TARGETS, f"unknown enum target: {target}"
        return ENUM_TARGETS[target](spec["input"])
    assert target in RESOLVABLE, f"unknown target: {target}"
    resolved = RESOLVABLE[target]
    assert isinstance(resolved, type) and issubclass(resolved, BaseModel)
    # Declared fixture data is JSON, so a published value is reconstructed
    # through the published JSON grammar rather than through Python-mode input.
    return resolved.model_validate_json(json.dumps(spec["input"]))


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
    """Replay reconstructs a value through the published JSON grammar.

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


def _execute(vector: dict[str, Any]) -> dict[str, Any]:
    """Run a vector by its DECLARED operation, never by the file it came from."""
    operation = cast(str, vector["operation"])
    assert operation in ALLOWED_OPERATIONS, f"unknown operation: {operation}"
    resolved = RESOLVABLE[vector["target"]]
    observed: dict[str, Any] = {
        "errors": None,
        "runtime_target": resolved.__name__,
        "value": None,
        "vocabulary_error": False,
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
    return [cast(str, vector["id"]) for vector in section["vectors"]]


# --- 1-4: inventory, canonical form, sidecars and declared digests ------------


def test_the_corpus_directory_holds_exactly_the_declared_files() -> None:
    assert {path.name for path in CORPUS.iterdir()} == set(CORPUS_FILES)
    assert {
        cast(str, entry["filename"])
        for entry in cast(list[dict[str, Any]], MANIFEST["corpus_files"])
    } == set(CORPUS_FILES)
    assert len(CORPUS_FILES) == 9
    assert all(
        entry["required"]
        for entry in cast(list[dict[str, Any]], MANIFEST["corpus_files"])
    )
    # contract.md is derived prose and deliberately has no sidecar of its own.
    assert not (CORPUS / "contract.sha256").exists()
    assert sum(name.endswith(".sha256") for name in CORPUS_FILES) == 4
    assert sum(name.endswith(".json") for name in CORPUS_FILES) == 4


@pytest.mark.parametrize("name", SEALED_JSON)
def test_each_sealed_file_is_canonical_and_digest_locked(name: str) -> None:
    raw = (CORPUS / f"{name}.json").read_bytes()

    # The loader already enforced the canonical form; this repeats it against
    # the bytes on disk so a regenerated file cannot drift silently.
    assert _parse_canonical_json(raw)
    sidecar = (CORPUS / f"{name}.sha256").read_bytes()
    assert sidecar == (f"{hashlib.sha256(raw).hexdigest()}  {name}.json\n".encode())
    assert sidecar.count(b"\n") == 1
    assert b"\r" not in sidecar


def test_the_manifest_records_the_vector_file_digests_and_lengths() -> None:
    entries = {
        cast(str, entry["filename"]): entry
        for entry in cast(list[dict[str, Any]], MANIFEST["corpus_files"])
    }
    digested = [name for name, entry in entries.items() if "sha256" in entry]

    # The manifest cannot carry a digest of itself, so it names the three
    # vector files and its own sidecar carries the rest.
    assert sorted(digested) == [
        "invalid-vectors.json",
        "replay-vectors.json",
        "valid-vectors.json",
    ]
    for name in digested:
        raw = (CORPUS / name).read_bytes()
        assert entries[name]["sha256"] == hashlib.sha256(raw).hexdigest(), name
        assert entries[name]["byte_length"] == len(raw), name
    for name, entry in entries.items():
        if name in digested:
            assert entry["role"] == "canonical_vector_file", name
        else:
            assert "sha256" not in entry and "byte_length" not in entry, name


def test_a_regenerated_document_reproduces_the_sealed_bytes() -> None:
    """Byte stability, proven by re-serialising what was parsed."""
    for name in SEALED_JSON:
        raw = (CORPUS / f"{name}.json").read_bytes()
        assert _canonical_bytes(_parse_canonical_json(raw)) == raw, name
        assert _canonical_bytes(_parse_canonical_json(raw)) == raw, name


def test_the_declared_canonicalization_is_the_one_enforced() -> None:
    declared = cast(dict[str, Any], MANIFEST["format"]["canonicalization"])

    assert declared == {
        "encoding": "UTF-8_without_BOM",
        "exactly_one_trailing_lf": True,
        "floats_and_NaN_permitted": False,
        "keys": "sorted",
        "line_endings": "LF_only",
        "name": "json-sort-keys-compact-utf8-lf-v1",
        "whitespace": "compact",
    }
    assert MANIFEST["format"]["name"] == "faultatlas-fault-instance-contract-corpus"
    assert MANIFEST["format"]["version"] == "1"
    for _, section, _, _ in FAMILIES:
        assert section["format"] == MANIFEST["format"]

    # A float, a NaN and a BOM each fail at the parse rather than afterwards.
    with pytest.raises(AssertionError):
        _parse_canonical_json(b'{"a":1.5}\n')
    with pytest.raises(AssertionError):
        _parse_canonical_json(b'{"a":NaN}\n')
    with pytest.raises(AssertionError):
        _parse_canonical_json(b'\xef\xbb\xbf{"a":1}\n')
    with pytest.raises(AssertionError):
        _parse_canonical_json(b'{"b":1,"a":2}\n')
    with pytest.raises(AssertionError):
        _parse_canonical_json(b'{"a": 1}\n')
    with pytest.raises(AssertionError):
        _parse_canonical_json(b'{"a":1}\r\n')
    with pytest.raises(AssertionError):
        _parse_canonical_json(b'{"a":1}')


def test_the_corpus_identity_is_the_authored_constant() -> None:
    assert MANIFEST["corpus_identity"] == {
        "classification": "internal_source_repository_only_contract_corpus",
        "id": "faultatlas-fault-instance-contract-corpus",
        "originating_slice": "S1.P06.S11",
        "phase_closure_owner": "S1.P06.S12",
        "public_persistence_format": False,
        "serialization_and_migration_owner": "S1.P10",
        "version": "1",
    }


# --- 5-7: the live surface, the sealed inventory and owned coverage ----------


def test_the_thirty_product_targets_come_from_live_dunder_all() -> None:
    """Derived again from live `__all__`, never restated by hand."""
    declared = cast(list[dict[str, Any]], MANIFEST["target_symbols"])
    by_module: dict[str, list[str]] = {}
    for entry in declared:
        by_module.setdefault(cast(str, entry["module"]), []).append(
            cast(str, entry["symbol"])
        )

    assert list(by_module) == list(OWNED_MODULES)
    for name, module in OWNED_MODULES.items():
        assert by_module[name] == list(cast(list[str], module.__all__)), name
    assert len(declared) == 30
    assert len({entry["symbol"] for entry in declared}) == 30
    assert len(OWNED) == 30
    assert MANIFEST["scope"]["owned_symbol_count"] == 30
    assert MANIFEST["scope"]["owned_module_count"] == 7
    assert MANIFEST["scope"]["owned_modules"] == list(OWNED_MODULES)
    assert Counter(cast(str, entry["target_class"]) for entry in declared) == {
        "record_target": 19,
        "identity_target": 10,
        "vocabulary_target": 1,
    }


def test_the_owned_inventory_equals_what_the_sealed_s10_decision_recorded() -> None:
    authority = cast(dict[str, Any], MANIFEST["entry_authority"])
    path = REPOSITORY_ROOT / cast(str, authority["path"])
    raw = path.read_bytes()

    assert authority["slice"] == "S1.P06.S10"
    assert authority["sha256"] == hashlib.sha256(raw).hexdigest()
    assert authority["byte_length"] == len(raw)
    assert authority["vectorized_as_product_behavior"] is False

    decision = _parse_canonical_json(raw)
    inventory = cast(dict[str, Any], decision["product_inventory"])
    sealed = [
        (cast(str, entry["module"]), cast(str, entry["symbol"]))
        for entry in cast(list[dict[str, Any]], inventory["symbols"])
    ]
    live = [
        (name, symbol)
        for name, module in OWNED_MODULES.items()
        for symbol in cast(list[str], module.__all__)
    ]

    assert sealed == live
    assert inventory["owned_module_count"] == 7
    assert inventory["owned_symbol_count"] == 30
    assert inventory["production_module_count"] == SEALED_PRODUCTION_MODULE_COUNT
    # S1.P06.S10 is authority for readiness and scope, never a product symbol.
    assert "S1.P06.S10" not in {
        cast(str, entry["publishing_slice"])
        for entry in cast(list[dict[str, Any]], MANIFEST["target_symbols"])
    }
    assert decision["readiness"]["s11_contract_corpus"] == "eligible_to_begin"


def test_every_owned_symbol_is_executably_covered() -> None:
    targeted = {cast(str, vector["target"]) for vector in ALL_VECTORS}
    owned_targeted = targeted & set(OWNED)

    assert owned_targeted == set(OWNED), sorted(set(OWNED) - owned_targeted)
    assert len(owned_targeted) == 30
    assert MANIFEST["assurance"]["owned_symbol_coverage"] == "30/30"
    # Each owned symbol is exercised by an accepting vector, not merely refused.
    accepted_targets = {
        cast(str, vector["target"])
        for vector in ALL_VECTORS
        if vector["operation"] == "construct"
    }
    assert set(OWNED) <= accepted_targets

    # Refusals are published where a rule lives. An identity's own refusals are
    # stated at the consumer positions that require it, so the invalid family is
    # required to reach every owned module and every covered Slice rather than
    # every symbol name.
    refused = [
        cast(dict[str, Any], vector) for vector in cast(list[Any], INVALID["vectors"])
    ]
    refused_modules = {
        cast(str, entry["module"])
        for entry in cast(list[dict[str, Any]], MANIFEST["target_symbols"])
        if entry["symbol"] in {cast(str, vector["target"]) for vector in refused}
    }
    assert refused_modules == set(OWNED_MODULES), sorted(refused_modules)
    assert {cast(str, vector["covered_slice"]) for vector in refused} == set(
        cast(list[str], MANIFEST["scope"]["covered_slices"])
    )


def test_no_supporting_authority_symbol_is_counted_as_owned() -> None:
    support = cast(list[dict[str, Any]], MANIFEST["support_targets"])
    declared = {cast(str, entry["symbol"]) for entry in support}

    assert declared == set(SUPPORT_TARGETS)
    assert not declared & set(OWNED)
    assert sorted({cast(str, entry["module"]) for entry in support}) == sorted(
        SUPPORT_MODULES
    )
    assert MANIFEST["scope"]["supporting_authorities_not_owned"] == sorted(
        SUPPORT_MODULES
    )
    for entry in support:
        module_name = cast(str, entry["module"])
        symbol = cast(str, entry["symbol"])
        module = __import__(module_name, fromlist=["*"])
        assert getattr(module, symbol) is SUPPORT_TARGETS[symbol], symbol
        expected = "enum" if symbol in ENUM_TARGETS else "model"
        assert entry["target_class"] == expected, symbol
    assert MANIFEST["execution_contract"]["registry"]["support_targets"] == len(
        SUPPORT_TARGETS
    )
    assert MANIFEST["execution_contract"]["registry"]["owned_targets"] == 30


# --- 8-10: executing the vectors ---------------------------------------------


@pytest.mark.parametrize("vector", VALID["vectors"], ids=_ids(VALID))
def test_every_valid_vector_constructs_its_declared_value(
    vector: dict[str, Any],
) -> None:
    observed = _execute(vector)
    value = observed["value"]
    expected = cast(dict[str, Any], vector["expected"])

    assert observed["outcome"] == expected["outcome"], vector["id"]
    assert observed["runtime_target"] == expected["runtime_target"], vector["id"]
    assert type(value).__name__ == expected["concrete_type"], vector["id"]
    if expected.get("cardinality_probe"):
        # A cardinality probe declares its size rather than a four-thousand
        # member dump. The shape is a kill switch for the dump comparison, so
        # only a vector the manifest names may reach it, and it must actually
        # be a synthesized sequence rather than an ordinary input opting out.
        assert cast(str, vector["id"]) in CARDINALITY_DUMP_EXEMPT, vector["id"]
        assert "indexed_value" in json.dumps(vector["input"], sort_keys=True)
        assert "semantic_dump" not in expected, vector["id"]
        members = getattr(value, cast(str, expected["member_collection"]))
        assert isinstance(members, tuple)
        assert len(cast(tuple[Any, ...], members)) == expected["member_count"]
    else:
        assert _dump(value) == expected["semantic_dump"], vector["id"]
    assert (
        _observed_round_trip(value, RESOLVABLE[vector["target"]])
        == expected["round_trip_equal"]
    ), vector["id"]


@pytest.mark.parametrize("vector", INVALID["vectors"], ids=_ids(INVALID))
def test_every_invalid_vector_is_rejected_as_declared(vector: dict[str, Any]) -> None:
    expected = cast(dict[str, Any], vector["expected"])
    observed = _execute(vector)

    # The mode is a closed vocabulary and it selects how the location is
    # compared. Treating anything that is not "exact" as prefix would let a
    # vector publish a mode that means nothing, and the vocabulary-error branch
    # below returns before the field is ever read.
    assert expected["error_location_mode"] in LOCATION_MODES, vector["id"]
    assert expected["failure_category"] in FAILURE_CATEGORIES, vector["id"]
    assert observed["outcome"] == expected["outcome"] == REJECTED, vector["id"]
    assert "semantic_dump" not in expected, vector["id"]

    if expected["failure_category"] == "vocabulary_error":
        assert observed["vocabulary_error"], vector["id"]
        assert expected["error_type"] == "enum"
        assert expected["error_location"] == []
        assert expected["error_location_mode"] == "exact"
        return

    assert not observed["vocabulary_error"], vector["id"]
    errors = cast(list[dict[str, Any]], observed["errors"])
    location = tuple(cast(list[Any], expected["error_location"]))
    if expected["error_location_mode"] == "exact":
        first = errors[0]
        assert tuple(cast(list[Any], first["loc"])) == location, (vector["id"], errors)
        assert first["type"] == expected["error_type"], (vector["id"], errors)
        if location:
            assert "failing_rule" not in expected, vector["id"]
            return
        # A root-located refusal comes from a model validator, and several of
        # them are indistinguishable by type and location. The vector names
        # which rule it proves, and the rule is confirmed against that module's
        # own authored message. The refusal must also be the only one reported,
        # so a second rule cannot have fired unnoticed.
        assert len(errors) == 1, (vector["id"], errors)
        rule = cast(str, expected["failing_rule"])
        assert rule in ROOT_RULE_SIGNATURES, (vector["id"], rule)
        raised = str(cast(dict[str, Any], first["ctx"])["error"])
        assert ROOT_RULE_SIGNATURES[rule] in raised, (vector["id"], raised)
        return

    # Prefix mode. Some reported error of the declared type lies under the
    # prefix, and every reported error does, so the refusal is proven localized
    # to that union position without locking a single branch label.
    assert any(
        error["type"] == expected["error_type"]
        and tuple(cast(list[Any], error["loc"]))[: len(location)] == location
        for error in errors
    ), (vector["id"], errors)
    assert all(
        tuple(cast(list[Any], error["loc"]))[: len(location)] == location
        for error in errors
    ), (vector["id"], errors)


@pytest.mark.parametrize("vector", REPLAY["vectors"], ids=_ids(REPLAY))
def test_every_replay_vector_reconstructs_its_declared_value(
    vector: dict[str, Any],
) -> None:
    target = RESOLVABLE[vector["target"]]
    observed = _execute(vector)
    value = observed["value"]
    expected = cast(dict[str, Any], vector["expected"])

    assert observed["outcome"] == expected["outcome"], vector["id"]
    assert observed["runtime_target"] == expected["runtime_target"], vector["id"]
    assert type(value).__name__ == expected["concrete_type"], vector["id"]
    assert _dump(value) == expected["semantic_dump"], vector["id"]
    assert _observed_round_trip(value, target) == expected["round_trip_equal"], vector[
        "id"
    ]


# --- 13: repeated execution is deterministic ---------------------------------


def test_repeated_execution_reproduces_every_result_exactly() -> None:
    """Replay is a design property, so it is executed rather than declared."""
    # The two cardinality probes are excluded by their declared marker rather
    # than by name: they synthesise thousands of members and prove a bound, not
    # a reproduction, and both are executed once by the family tests above.
    sampled = [
        vector
        for vector in ALL_VECTORS
        if "indexed_value" not in json.dumps(vector["input"], sort_keys=True)
    ]
    assert len(sampled) == len(ALL_VECTORS) - 2

    def _signature(vector: dict[str, Any]) -> tuple[Any, ...]:
        observed = _execute(vector)
        value = observed["value"]
        errors = cast(list[dict[str, Any]] | None, observed["errors"])
        # The declared rejection contract, not the raw error records: a
        # Pydantic error carries the raised exception object in its context and
        # that compares by identity, which would make every rerun differ for a
        # reason the corpus never claims to be stable.
        signature = (
            None
            if errors is None
            else tuple(
                (error["type"], tuple(cast(list[Any], error["loc"])))
                for error in errors
            )
        )
        return (
            observed["outcome"],
            observed["runtime_target"],
            None if value is None else _dump(value),
            signature,
            observed["vocabulary_error"],
        )

    first = {cast(str, vector["id"]): _signature(vector) for vector in sampled}
    for vector in sampled:
        assert _signature(vector) == first[cast(str, vector["id"])], vector["id"]

    # The canonical bytes are stable across repeated reads as well.
    for name in SEALED_JSON:
        raw = (CORPUS / f"{name}.json").read_bytes()
        assert (CORPUS / f"{name}.json").read_bytes() == raw, name
        assert (
            hashlib.sha256(raw).hexdigest()
            == hashlib.sha256((CORPUS / f"{name}.json").read_bytes()).hexdigest()
        ), name


# --- 12: unknown target, operation, mode and marker all fail closed ----------


@pytest.mark.parametrize(
    ("family", "section", "modes", "operations"),
    [
        (name, section, modes, operations)
        for name, section, modes, operations in FAMILIES
    ],
    ids=[name for name, _, _, _ in FAMILIES],
)
def test_every_vector_declares_a_known_target_operation_and_mode(
    family: str,
    section: dict[str, Any],
    modes: frozenset[str],
    operations: frozenset[str],
) -> None:
    for vector in cast(list[dict[str, Any]], section["vectors"]):
        assert vector["target"] in RESOLVABLE, (family, vector["id"])
        assert vector["input_mode"] in modes, (family, vector["id"])
        assert vector["input_mode"] in ALLOWED_INPUT_MODES, (family, vector["id"])
        assert vector["operation"] in operations, (family, vector["id"])
        assert vector["operation"] in ALLOWED_OPERATIONS, (family, vector["id"])
        assert vector["covered_slice"] in cast(
            list[str], MANIFEST["scope"]["covered_slices"]
        ), (family, vector["id"])
        assert cast(str, vector["id"]).startswith(f"fault-instance.{family}."), vector[
            "id"
        ]
        partition = cast(str, vector["semantic_partition"]).split("/")
        assert partition[0] == vector["category"], vector["id"]
        assert len(partition) == 3, vector["id"]
        assert cast(str, vector["purpose"]).strip() == vector["purpose"]
        assert vector["purpose"], vector["id"]


def test_unknown_target_operation_mode_and_marker_all_fail_closed() -> None:
    base = cast(dict[str, Any], VALID["vectors"][0])

    with pytest.raises(KeyError):
        _execute({**base, "target": "NotAPublishedTarget"})
    with pytest.raises(AssertionError):
        _execute({**base, "operation": "coerce"})
    with pytest.raises(AssertionError):
        _execute({**base, "input_mode": "string", "operation": "construct"})
    with pytest.raises(AssertionError):
        _materialise({"smuggled_value": {"target": "FaultInstanceIdentity"}})
    with pytest.raises(AssertionError):
        _materialise({"typed_value": {"target": "NotAPublishedTarget", "input": {}}})
    with pytest.raises(AssertionError):
        _materialise({"enum_value": {"target": "FaultInstance", "input": "x"}})
    with pytest.raises(AssertionError):
        # Markers are exact singleton objects; a marker beside a sibling key is
        # ambiguous about which one the executor is meant to honour.
        _materialise({"typed_value": {"target": "FaultInstanceIdentity"}, "extra": 1})
    with pytest.raises(AssertionError):
        _materialise(
            {
                "indexed_value": {
                    "count": MAX_INDEXED_COUNT + 1,
                    "target": "SuppliedFaultReport",
                    "template": GENERATED_REPORT_TEMPLATE,
                }
            }
        )
    with pytest.raises(AssertionError):
        _materialise(
            {
                "indexed_value": {
                    "count": 1,
                    "target": "SuppliedFaultReport",
                    "template": "another-template",
                }
            }
        )
    assert MANIFEST["execution_contract"]["registry"]["unknown_marker"] == "reject"
    assert MANIFEST["execution_contract"]["registry"]["unknown_operation"] == "reject"
    assert MANIFEST["execution_contract"]["registry"]["unknown_target"] == "reject"


def test_the_execution_contract_matches_the_executor() -> None:
    contract = cast(dict[str, Any], MANIFEST["execution_contract"])
    markers = cast(dict[str, Any], contract["test_input_markers"])

    assert contract["input_modes"] == list(ALLOWED_INPUT_MODES)
    assert contract["operations"] == list(ALLOWED_OPERATIONS)
    assert markers["allowed"] == sorted(ALLOWED_MARKERS)
    assert set(markers["allowed"]) == set(ALLOWED_MARKERS)
    assert markers["max_indexed_count"] == MAX_INDEXED_COUNT
    assert markers["malformed_or_unknown"] == "reject"
    assert markers["shapes"] == "exact_singleton_objects"
    assert markers["never_reaches_production_validation"] is True
    assert contract["test_only_executor"] == (
        "tests/test_fault_instance_contract_corpus.py"
    )
    assert (REPOSITORY_ROOT / cast(str, contract["test_only_executor"])).samefile(
        Path(__file__).resolve()
    )
    expectation = cast(dict[str, Any], contract["expectation_contract"])
    assert expectation["production_dump_used_as_oracle"] is False
    assert expectation["explicit_semantic_dump"] == (
        "authored_from_declared_fixture_values"
    )

    # Every allowed marker is used, and every marker used is allowed.
    serialised = "".join(
        json.dumps(vector["input"], sort_keys=True) for vector in ALL_VECTORS
    )
    for marker in ALLOWED_MARKERS:
        assert f'"{marker}"' in serialised, marker


# --- identifiers, partitions, fixtures and declared counts -------------------


def test_vector_and_fixture_identifiers_are_unique_across_the_corpus() -> None:
    ids = [cast(str, vector["id"]) for vector in ALL_VECTORS]
    partitions = [cast(str, vector["semantic_partition"]) for vector in ALL_VECTORS]
    fixture_ids = [
        cast(str, fixture["id"])
        for fixture in cast(list[dict[str, Any]], VALID["fixtures"])
    ]

    assert len(ids) == len(set(ids))
    assert len(partitions) == len(set(partitions))
    assert len(fixture_ids) == len(set(fixture_ids))


def test_the_declared_counts_match_the_vector_files() -> None:
    summary = cast(dict[str, Any], MANIFEST["vector_summary"])

    assert summary["valid"]["count"] == len(cast(list[Any], VALID["vectors"])) == 103
    assert (
        summary["invalid"]["count"] == len(cast(list[Any], INVALID["vectors"])) == 110
    )
    assert summary["replay"]["count"] == len(cast(list[Any], REPLAY["vectors"])) == 41
    assert summary["total_vectors"] == len(ALL_VECTORS) == 254
    assert summary["fixtures"] == len(cast(list[Any], VALID["fixtures"])) == 29
    for family, section, _, _ in FAMILIES:
        counts = Counter(
            cast(str, vector["category"])
            for vector in cast(list[dict[str, Any]], section["vectors"])
        )
        assert cast(dict[str, Any], summary[family])["categories"] == dict(counts), (
            family
        )


REQUIRED_FIXTURE_KEYS = frozenset({"id", "provenance", "status", "value"})
REQUIRED_LOCK_KEYS = frozenset({"byte_length", "lock_id", "path", "sha256"})
REQUIRED_VECTOR_KEYS = frozenset(
    {
        "category",
        "covered_slice",
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
REQUIRED_REPLAY_KEYS = REQUIRED_VECTOR_KEYS | frozenset(
    {"evidence_classification", "retained_support"}
)


def test_every_declared_record_publishes_exactly_its_envelope() -> None:
    """A record collection beside the vectors cannot authorize its own growth.

    The authored key sets below are written out rather than built from the
    records they validate, because a set built from the records would admit
    whatever they happen to carry, which is the defect rather than the fix.
    """
    for family, section, _, _ in FAMILIES:
        shapes = {
            frozenset(cast(dict[str, Any], fixture))
            for fixture in cast(list[Any], section["fixtures"])
        }
        assert shapes == {REQUIRED_FIXTURE_KEYS}, family
        expected_keys = (
            REQUIRED_REPLAY_KEYS if family == "replay" else REQUIRED_VECTOR_KEYS
        )
        vector_shapes = {
            frozenset(cast(dict[str, Any], vector))
            for vector in cast(list[Any], section["vectors"])
        }
        assert vector_shapes == {expected_keys}, family

    assert {
        frozenset(cast(dict[str, Any], lock))
        for lock in cast(list[Any], REPLAY["artifact_locks"])
    } == {REQUIRED_LOCK_KEYS}
    assert len(REQUIRED_FIXTURE_KEYS) == 4
    assert len(REQUIRED_LOCK_KEYS) == 4
    assert len(REQUIRED_VECTOR_KEYS) == 10
    assert len(REQUIRED_REPLAY_KEYS) == 12


def test_declared_fixtures_are_shared_locked_and_actually_used() -> None:
    fixtures = cast(list[dict[str, Any]], VALID["fixtures"])

    assert VALID["fixtures"] == INVALID["fixtures"] == REPLAY["fixtures"]
    assert all(fixture["status"] == "locked" for fixture in fixtures)
    assert all(fixture["provenance"] in FIXTURE_PROVENANCES for fixture in fixtures)
    assert all(
        cast(str, fixture["id"]).startswith("fault-instance.fixture.")
        for fixture in fixtures
    )

    # A declared fixture that no vector carries is a claim with nothing behind
    # it, so sharing is proven by finding each value inside the corpus.
    serialised = "".join(
        json.dumps(vector, sort_keys=True, ensure_ascii=False) for vector in ALL_VECTORS
    )
    for fixture in fixtures:
        value = fixture["value"]
        needle = (
            value
            if isinstance(value, str)
            else json.dumps(value, sort_keys=True, ensure_ascii=False)
        )
        assert needle in serialised, fixture["id"]

    counts = Counter(cast(str, fixture["provenance"]) for fixture in fixtures)
    declared = cast(dict[str, Any], MANIFEST["fixture_provenance"])
    assert declared["counts"] == dict(counts)
    assert declared["total"] == len(fixtures)
    assert sorted(cast(dict[str, Any], declared["values"])) == sorted(
        FIXTURE_PROVENANCES
    )
    assert declared["corpus_vocabulary_not_a_production_enum"] is True
    for name in FIXTURE_PROVENANCES:
        assert name not in dir(fault_module)
        assert name not in dir(instance_module)


def test_the_retained_artifact_locks_match_live_bytes() -> None:
    for lock in cast(list[dict[str, Any]], REPLAY["artifact_locks"]):
        path = REPOSITORY_ROOT / cast(str, lock["path"])
        raw = path.read_bytes()
        assert lock["sha256"] == hashlib.sha256(raw).hexdigest(), lock["lock_id"]
        assert lock["byte_length"] == len(raw), lock["lock_id"]

    # Each lock is the durable record some replay vector names whole.
    referenced: set[tuple[str, int]] = set()
    for fixture in cast(list[dict[str, Any]], VALID["fixtures"]):
        value = cast(dict[str, Any], fixture["value"])
        if not isinstance(fixture["value"], dict) or "sha256" not in value:
            continue
        referenced.add((cast(str, value["sha256"]), cast(int, value["byte_length"])))
    locked = {
        (cast(str, lock["sha256"]), cast(int, lock["byte_length"]))
        for lock in cast(list[dict[str, Any]], REPLAY["artifact_locks"])
    }
    assert referenced == locked


# --- 11: replay classifications and provenance -------------------------------


def test_replay_classifications_are_exactly_the_five_published_kinds() -> None:
    declared = cast(dict[str, Any], MANIFEST["replay_contract"]["classifications"])
    used = Counter(
        cast(str, vector["evidence_classification"])
        for vector in cast(list[dict[str, Any]], REPLAY["vectors"])
    )

    assert sorted(declared) == sorted(REPLAY_CLASSIFICATIONS)
    assert sorted(used) == sorted(REPLAY_CLASSIFICATIONS)
    assert sum(used.values()) == len(cast(list[Any], REPLAY["vectors"]))
    # These are corpus metadata. None of them is a production name.
    for name in REPLAY_CLASSIFICATIONS:
        for module in OWNED_MODULES.values():
            assert name not in dir(module), name
            assert name.upper() not in dir(module), name
    assert MANIFEST["replay_contract"]["historical_s1_p06_uuid_identities"] == 0
    assert (
        MANIFEST["replay_contract"]["flattened_evidence_derived_fault_instance_claimed"]
        is False
    )
    assert MANIFEST["replay_contract"]["repair_correctness_claimed"] is False
    assert MANIFEST["replay_contract"]["root_cause_claimed"] is False
    assert MANIFEST["replay_contract"]["verified_repair_claimed"] is False
    assert MANIFEST["replay_contract"]["production_replay_io"] is False
    assert MANIFEST["replay_contract"]["deterministic_repeat_execution"] is True


def _fixtures_by_provenance(provenance: str) -> list[dict[str, Any]]:
    return [
        cast(dict[str, Any], fixture)
        for fixture in cast(list[Any], VALID["fixtures"])
        if fixture["provenance"] == provenance
    ]


def test_replay_retained_support_is_declared_exactly_and_not_inferred() -> None:
    retained = _fixtures_by_provenance("retained_case_value")
    by_id = {cast(str, fixture["id"]): fixture for fixture in retained}

    for vector in cast(list[dict[str, Any]], REPLAY["vectors"]):
        serialised = json.dumps(vector["input"], sort_keys=True, ensure_ascii=False)
        declared = cast(list[str], vector["retained_support"])
        assert declared == sorted(declared), vector["id"]
        assert len(declared) == len(set(declared)), vector["id"]
        present = {
            fixture_id
            for fixture_id, fixture in by_id.items()
            if json.dumps(fixture["value"], sort_keys=True, ensure_ascii=False)
            in serialised
        }
        assert set(declared) == present, (vector["id"], sorted(present))


def test_no_synthetic_s1_p06_value_is_replayed_as_a_retained_observation() -> None:
    """Replayability never promotes a supplied claim into a retained fact."""
    # Every synthetic fixture, not only the scalar ones: screening on
    # `isinstance(str)` silently exempted the invented repository identity,
    # which is exactly the kind of value that must never be replayed as
    # retained.
    fixtures = _fixtures_by_provenance("synthetic_caller_supplied")
    synthetic = [
        fixture["value"]
        if isinstance(fixture["value"], str)
        else json.dumps(fixture["value"], sort_keys=True, ensure_ascii=False)
        for fixture in fixtures
    ]
    assert len(synthetic) == len(fixtures) == 12
    assert sum(1 for value in fixtures if isinstance(value["value"], str)) == 11

    for vector in cast(list[dict[str, Any]], REPLAY["vectors"]):
        serialised = json.dumps(vector["input"], sort_keys=True, ensure_ascii=False)
        if vector["evidence_classification"] == "retained_normalized_observation":
            for scalar in synthetic:
                assert scalar not in serialised, (vector["id"], scalar)
            assert cast(str, vector["target"]) in SUPPORT_TARGETS, vector["id"]
        if vector["evidence_classification"] == "caller_supplied_identity":
            assert isinstance(vector["input"], str), vector["id"]
            assert vector["input"] in synthetic, vector["id"]
            assert vector["retained_support"] == [], vector["id"]
            assert cast(str, vector["target"]) in OWNED, vector["id"]


def test_the_replay_vertical_reaches_every_semantic_layer() -> None:
    targeted = {
        cast(str, vector["target"])
        for vector in cast(list[dict[str, Any]], REPLAY["vectors"])
    }
    owned_targeted = sorted(targeted & set(OWNED))
    contract = cast(dict[str, Any], MANIFEST["replay_contract"])

    assert contract["owned_symbols_targeted"] == len(owned_targeted) == 29
    assert (
        contract["owned_symbols_not_targeted"]
        == sorted(set(OWNED) - set(owned_targeted))
        == ["ReportedFaultTestOutcomeKind"]
    )

    # The one owned symbol replay does not target participates in the vertical
    # as the declared disposition inside the two reported outcomes.
    dispositions = {
        cast(dict[str, Any], vector["expected"])["semantic_dump"]["outcome"]
        for vector in cast(list[dict[str, Any]], REPLAY["vectors"])
        if vector["target"] == "ReportedFaultTestOutcome"
    }
    assert dispositions == {"failed", "passed"}
    assert dispositions <= {
        member.value
        for member in test_module.ReportedFaultTestOutcomeKind.__members__.values()
    }

    # Every covered Slice is reached by the replay family as well.
    assert {
        cast(str, vector["covered_slice"])
        for vector in cast(list[dict[str, Any]], REPLAY["vectors"])
    } == set(cast(list[str], MANIFEST["scope"]["covered_slices"]))


# --- the published boundaries the corpus claims to freeze --------------------


def test_the_outcome_vocabulary_is_exactly_seven_members_with_no_alias() -> None:
    """Read through `__members__`, which is the only view an alias appears in.

    Iteration, `len()` and `dir()` all skip an alias member, so a vocabulary
    widened by one alias would satisfy every one of them and the corpus would
    still claim a closed seven.
    """
    members = test_module.ReportedFaultTestOutcomeKind.__members__

    assert list(members) == [
        "PASSED",
        "FAILED",
        "ERRORED",
        "TIMED_OUT",
        "SKIPPED",
        "DID_NOT_START",
        "CANCELLED",
    ]
    assert len(members) == 7
    assert len(members) == len(list(test_module.ReportedFaultTestOutcomeKind))
    assert {member.value for member in members.values()} == {
        "passed",
        "failed",
        "errored",
        "timed_out",
        "skipped",
        "did_not_start",
        "cancelled",
    }
    for lexeme in ("unknown", "flaky", "PASSED", "", "passed "):
        with pytest.raises(ValueError):
            test_module.ReportedFaultTestOutcomeKind(lexeme)

    # Every member is covered by an accepting vector, and no more than seven.
    covered = {
        cast(dict[str, Any], vector["expected"])["semantic_dump"]
        for vector in cast(list[dict[str, Any]], VALID["vectors"])
        if vector["target"] == "ReportedFaultTestOutcomeKind"
        and vector["input_mode"] == "json"
    }
    assert covered == {member.value for member in members.values()}


def test_the_order_pair_is_two_different_composed_values() -> None:
    """Order is preserved and meaningless, and the pair proves both halves."""
    forward, reversed_ = (
        next(
            cast(dict[str, Any], vector)
            for vector in cast(list[Any], VALID["vectors"])
            if vector["id"] == f"fault-instance.valid.composition.{slug}"
        )
        for slug in ("tuple-order-as-supplied", "tuple-order-reversed")
    )

    # Two vectors that differ only in label would read as covered while
    # exercising one behaviour, so the pair is required to be two inputs.
    assert forward["input"] != reversed_["input"]
    built_forward = _execute(forward)["value"]
    built_reversed = _execute(reversed_)["value"]
    assert built_forward != built_reversed
    assert set(built_forward.explanations) == set(built_reversed.explanations)
    assert built_forward.explanations == tuple(reversed(built_reversed.explanations))

    # No two vectors anywhere share one executable payload.
    payloads = Counter(
        json.dumps(
            {
                key: vector[key]
                for key in ("target", "input_mode", "operation", "input")
            },
            sort_keys=True,
            ensure_ascii=False,
        )
        for vector in ALL_VECTORS
    )
    duplicated = [count for count in payloads.values() if count > 1]
    assert not duplicated, duplicated


def test_a_did_not_start_report_is_not_a_failure_and_absence_is_not_either() -> None:
    """Two refusals the corpus must never quietly convert into a failure."""
    kind = test_module.ReportedFaultTestOutcomeKind
    assert kind.DID_NOT_START is not kind.FAILED
    assert kind.DID_NOT_START.value != kind.FAILED.value

    # A composed run with no reported outcome is absent, never failed.
    run_only = next(
        vector
        for vector in cast(list[dict[str, Any]], VALID["vectors"])
        if vector["id"] == "fault-instance.valid.composition.connected-vertical"
    )
    minimal = next(
        vector
        for vector in cast(list[dict[str, Any]], VALID["vectors"])
        if vector["id"] == "fault-instance.valid.composition.minimal"
    )
    assert (
        cast(dict[str, Any], minimal["expected"])["semantic_dump"]["test_outcomes"]
        == []
    )
    assert "failed" not in json.dumps(
        cast(dict[str, Any], minimal["expected"])["semantic_dump"]
    )
    assert (
        len(cast(dict[str, Any], run_only["expected"])["semantic_dump"]["test_runs"])
        == 2
    )

    # A did_not_start before-report is accepted in a comparison, so the corpus
    # never needs to spell it as a failure to express the pair.
    accepted_pair = next(
        vector
        for vector in cast(list[dict[str, Any]], VALID["vectors"])
        if vector["id"].endswith("test-comparison.did-not-start-to-passed")
    )
    dump = cast(dict[str, Any], accepted_pair["expected"])["semantic_dump"]
    assert dump["before"]["outcome"] == "did_not_start"
    assert dump["after"]["outcome"] == "passed"


def test_prefix_location_is_used_only_at_the_declared_union_positions() -> None:
    declared = cast(
        list[str], MANIFEST["rejection_contract"]["discriminatorless_union_positions"]
    )
    assert sorted(declared) == sorted(DISCRIMINATORLESS_UNIONS)

    # Each declared position is a real union field on a real published model,
    # and it genuinely has no discriminator.
    for position in declared:
        symbol, field = DISCRIMINATORLESS_UNIONS[position]
        model = RESOLVABLE[symbol]
        info = cast(dict[str, Any], model.model_fields)[field]
        assert info.discriminator is None, position

    prefix_fields: set[str] = set()
    for vector in cast(list[dict[str, Any]], INVALID["vectors"]):
        expected = cast(dict[str, Any], vector["expected"])
        if expected["error_location_mode"] != "prefix":
            continue
        location = cast(list[str], expected["error_location"])
        assert len(location) == 1, vector["id"]
        prefix_fields.add(f"{vector['target']}.{location[0]}")
    assert prefix_fields <= set(DISCRIMINATORLESS_UNIONS), sorted(prefix_fields)
    assert prefix_fields == set(DISCRIMINATORLESS_UNIONS), sorted(prefix_fields)

    # Everything else is pinned exactly.
    exact = [
        vector
        for vector in cast(list[dict[str, Any]], INVALID["vectors"])
        if cast(dict[str, Any], vector["expected"])["error_location_mode"] == "exact"
    ]
    assert len(exact) > len(cast(list[Any], INVALID["vectors"])) // 2


def test_every_root_located_rule_is_named_proven_and_exercised() -> None:
    """The rules that share one type and one location are told apart.

    Thirteen vectors refuse at the document root. Nine of them report the same
    `value_error` with the same empty location, so the type-and-location oracle
    alone would accept a vector that proved a different rule than it claims.
    Each names its rule, each rule is confirmed against the sealed module's own
    message, and every declared rule is required to be exercised.
    """
    declared = cast(list[str], MANIFEST["rejection_contract"]["root_located_rules"])
    assert sorted(declared) == sorted(ROOT_RULE_SIGNATURES)
    assert "failing_rule" in cast(
        list[str], MANIFEST["rejection_contract"]["error_oracle"]
    )

    root_located = [
        cast(dict[str, Any], vector)
        for vector in cast(list[Any], INVALID["vectors"])
        if cast(dict[str, Any], vector["expected"])["failure_category"]
        == "validation_error"
        and not cast(dict[str, Any], vector["expected"])["error_location"]
    ]
    assert len(root_located) == 13, [v["id"] for v in root_located]

    used = Counter(
        cast(str, cast(dict[str, Any], vector["expected"])["failing_rule"])
        for vector in root_located
    )
    assert sorted(used) == sorted(ROOT_RULE_SIGNATURES), sorted(used)

    # No vector outside that set may name a rule, and every named rule really
    # is the one the live module raises.
    for vector in cast(list[dict[str, Any]], INVALID["vectors"]):
        expected = cast(dict[str, Any], vector["expected"])
        names_rule = "failing_rule" in expected
        assert names_rule == (vector in root_located), vector["id"]
        if not names_rule:
            continue
        errors = cast(list[dict[str, Any]], _execute(vector)["errors"])
        assert len(errors) == 1, vector["id"]
        raised = str(cast(dict[str, Any], errors[0]["ctx"])["error"])
        rule = cast(str, expected["failing_rule"])
        assert ROOT_RULE_SIGNATURES[rule] in raised, (vector["id"], raised)
        # And no other rule's signature also matches, so the naming is exact.
        others = [
            name
            for name, fragment in ROOT_RULE_SIGNATURES.items()
            if name != rule and fragment in raised
        ]
        assert not others, (vector["id"], others)


def test_only_the_declared_cardinality_probes_may_omit_a_semantic_dump() -> None:
    """The dump comparison may be skipped only where the corpus says so.

    Declaring the exemption in the document rather than in the expectation
    block is what keeps it from being a switch any vector can throw: a vector
    that dropped its dump and claimed to be a probe would not be in this set.
    """
    declared = cast(
        dict[str, Any], MANIFEST["execution_contract"]["cardinality_probes"]
    )
    assert set(cast(list[str], declared["bound_probe_vectors"])) == {
        "fault-instance.invalid.composition.above-maximum-reports",
        "fault-instance.valid.composition.maximum-reports",
    }
    assert set(cast(list[str], declared["may_omit_semantic_dump"])) == {
        "fault-instance.valid.composition.maximum-reports"
    }
    assert BOUND_PROBES == set(cast(list[str], declared["bound_probe_vectors"]))
    assert CARDINALITY_DUMP_EXEMPT == set(
        cast(list[str], declared["may_omit_semantic_dump"])
    )
    assert CARDINALITY_DUMP_EXEMPT < BOUND_PROBES

    exempt = {
        cast(str, vector["id"])
        for vector in ALL_VECTORS
        if cast(dict[str, Any], vector["expected"]).get("cardinality_probe")
    }
    assert exempt == CARDINALITY_DUMP_EXEMPT

    # Every other accepted vector really does carry an authored dump.
    for vector in ALL_VECTORS:
        expected = cast(dict[str, Any], vector["expected"])
        if expected["outcome"] != ACCEPTED:
            continue
        if cast(str, vector["id"]) in CARDINALITY_DUMP_EXEMPT:
            continue
        assert "semantic_dump" in expected, vector["id"]
        assert "cardinality_probe" not in expected, vector["id"]

    # And the marker is used by exactly the declared bound probes.
    using = {
        cast(str, vector["id"])
        for vector in ALL_VECTORS
        if "indexed_value" in json.dumps(vector["input"], sort_keys=True)
    }
    assert using == BOUND_PROBES

    # A vector that drops its dump without being declared is refused.
    victim = next(
        vector
        for vector in cast(list[dict[str, Any]], VALID["vectors"])
        if vector["id"] == "fault-instance.valid.composition.minimal"
    )
    smuggled = copy.deepcopy(victim)
    expected = cast(dict[str, Any], smuggled["expected"])
    del expected["semantic_dump"]
    expected["cardinality_probe"] = True
    expected["member_collection"] = "reports"
    expected["member_count"] = 1
    with pytest.raises(AssertionError):
        test_every_valid_vector_constructs_its_declared_value(smuggled)


def test_every_symbol_publishing_slice_matches_the_sealed_decision() -> None:
    """The per-symbol slice is a historical fact with an authority to check."""
    sealed = {
        (cast(str, entry["module"]), cast(str, entry["symbol"])): cast(
            str, entry["publishing_slice"]
        )
        for entry in cast(
            list[dict[str, Any]],
            _parse_canonical_json(
                (
                    REPOSITORY_ROOT / cast(str, MANIFEST["entry_authority"]["path"])
                ).read_bytes()
            )["product_inventory"]["symbols"],
        )
    }
    declared = cast(list[dict[str, Any]], MANIFEST["target_symbols"])

    assert len(sealed) == len(declared) == 30
    for entry in declared:
        key = (cast(str, entry["module"]), cast(str, entry["symbol"]))
        assert key in sealed, key
        assert entry["publishing_slice"] == sealed[key], key
        assert entry["publishing_slice"] in cast(
            list[str], MANIFEST["scope"]["covered_slices"]
        ), key

    # Every covered Slice published at least one symbol, so the mapping is not
    # a constant wearing nine different labels.
    assert {cast(str, entry["publishing_slice"]) for entry in declared} == set(
        cast(list[str], MANIFEST["scope"]["covered_slices"])
    )


# Each corpus file's role follows from what the file is, so the role is derived
# here and compared rather than read back out of the document it describes.
def _expected_role(filename: str) -> str:
    if filename.endswith(".sha256"):
        return "digest_sidecar"
    if filename == "contract.md":
        return "derived_prose"
    if filename == "manifest.json":
        return "canonical_manifest"
    return "canonical_vector_file"


def test_every_corpus_file_declares_the_role_its_own_name_implies() -> None:
    entries = cast(list[dict[str, Any]], MANIFEST["corpus_files"])

    for entry in entries:
        filename = cast(str, entry["filename"])
        assert entry["role"] == _expected_role(filename), filename
    assert Counter(_expected_role(name) for name in CORPUS_FILES) == {
        "digest_sidecar": 4,
        "canonical_vector_file": 3,
        "canonical_manifest": 1,
        "derived_prose": 1,
    }
    assert MANIFEST["entry_authority"]["role"] == (
        "sealed_predecessor_readiness_and_scope_decision"
    )


def test_every_retained_fixture_value_comes_from_the_retained_material() -> None:
    """A retained label must be answerable, or it is just a word.

    Nothing stopped a fabricated digest from carrying the retained provenance
    label, so every scalar inside a retained fixture is looked up in the bytes
    of the retained case material this corpus is calibrated to.
    """
    provenance = cast(dict[str, Any], MANIFEST["fixture_provenance"])
    sources = cast(list[str], provenance["retained_material"])
    assert sources, "a retained label needs a source"
    assert provenance["retained_values_verified_against_retained_material"] is True

    corpus_root = REPOSITORY_ROOT / "reference_corpus"
    material = ""
    for relative in sources:
        path = (REPOSITORY_ROOT / relative).resolve()
        # The path is canonical data. It is confined before it is opened.
        assert corpus_root.resolve() in path.parents, relative
        assert path.is_file(), relative
        material += path.read_text("utf-8")

    def _scalars(value: Any) -> Iterator[str]:
        if isinstance(value, dict):
            for item in cast(dict[str, Any], value).values():
                yield from _scalars(item)
        elif isinstance(value, list):
            for item in cast(list[Any], value):
                yield from _scalars(item)
        elif isinstance(value, str):
            yield value

    # Structural leaves the retained record has no reason to spell, and the two
    # durable references, which are checked against live bytes elsewhere.
    STRUCTURAL = {"commit", "blob", "sha1", "added", "modified", "base", "head"}
    checked = 0
    for fixture in _fixtures_by_provenance("retained_case_value"):
        value = fixture["value"]
        if isinstance(value, dict) and "sha256" in cast(dict[str, Any], value):
            continue
        for scalar in _scalars(value):
            if scalar in STRUCTURAL:
                continue
            # Anchored to a whole JSON string token. Raw containment would let
            # any substring of the retained bytes, down to one character,
            # satisfy a retained provenance label.
            assert json.dumps(scalar, ensure_ascii=False) in material, (
                fixture["id"],
                scalar,
            )
            checked += 1
    assert checked >= 40, checked

    # A fabricated digest carrying the retained label is refused.
    assert "0" * 40 not in material


def test_the_rejection_contract_locks_no_unstable_surface() -> None:
    contract = cast(dict[str, Any], MANIFEST["rejection_contract"])

    assert contract["coercion"] == "forbidden"
    assert contract["normalization"] == "forbidden"
    assert contract["internal_union_branch_labels_locked"] is False
    assert contract["unstable_prose_locked"] is False
    assert sorted(cast(list[str], contract["failure_categories"])) == sorted(
        FAILURE_CATEGORIES
    )
    assert sorted(cast(dict[str, Any], contract["error_location_modes"])) == sorted(
        LOCATION_MODES
    )
    assert sorted(cast(list[str], contract["error_oracle"])) == [
        "error_location",
        "error_location_mode",
        "error_type",
        "failing_rule",
        "failure_category",
    ]
    assert cast(str, contract["root_located_rule_source"]).strip()

    # No vector may pin a Pydantic message, a branch label, or a URL.
    serialised = json.dumps(INVALID, sort_keys=True, ensure_ascii=False)
    for forbidden in (
        "function-before[",
        "function-after[",
        "errors.pydantic.dev",
        "msg",
    ):
        assert forbidden not in serialised, forbidden
    declared_types = {
        cast(dict[str, Any], vector["expected"])["error_type"]
        for vector in cast(list[dict[str, Any]], INVALID["vectors"])
    }
    assert declared_types == {
        "enum",
        "extra_forbidden",
        "literal_error",
        "missing",
        "model_type",
        "string_too_long",
        "string_too_short",
        "string_type",
        "too_long",
        "too_short",
        "tuple_type",
        "uuid_type",
        "value_error",
    }


def test_a_consumer_position_refuses_the_bare_scalar_an_identity_accepts() -> None:
    """Why every consumer position carries its own guard.

    A `RootModel` reconstructs from its own root type even under `strict=True`,
    so the identity target itself accepts a bare `uuid.UUID`. That is exactly
    why the composition and every record close their identity positions, and
    the corpus records the refusal at the consumer rather than at the identity.
    """
    scalar = uuid.UUID("12345678-1234-4234-8234-123456789abc")
    assert fault_module.FaultInstanceIdentity.model_validate(scalar).root == scalar

    with pytest.raises(ValidationError) as caught:
        fault_module.FaultRepositoryContext.model_validate(
            {
                "fault": scalar,
                "repository": identity.RepositoryIdentity.model_validate_json(
                    json.dumps(GENERATED_CONTEXT["repository"])
                ),
            }
        )
    errors = caught.value.errors()
    assert errors[0]["type"] == "value_error"
    assert tuple(errors[0]["loc"]) == ("fault",)


# --- 14, 16: the package boundary and zero production capability -------------


def _production_sources() -> set[str]:
    return {
        path.relative_to(REPOSITORY_ROOT).as_posix()
        for path in (REPOSITORY_ROOT / "src").rglob("*.py")
    }


def test_the_corpus_is_source_only_and_adds_no_production_file() -> None:
    observed = _production_sources()

    assert MANIFEST["scope"]["source_only"] is True
    assert MANIFEST["scope"]["package_exclusion_required"] is True
    # The sealed figure and the live one parted company when `S1.P07.S01`
    # added one module. The corpus still adds none of its own.
    assert MANIFEST["scope"]["production_module_count"] == (
        SEALED_PRODUCTION_MODULE_COUNT
    )
    for module in OWNED_MODULES:
        assert "src/" + module.replace(".", "/") + ".py" in observed, module
    assert_current_inventory(observed)


def test_no_production_module_can_locate_or_read_the_corpus() -> None:
    for path in (REPOSITORY_ROOT / "src").rglob("*.py"):
        source = path.read_text("utf-8")
        assert "reference_corpus" not in source, path
        assert "contracts/fault-instance" not in source, path
        assert "contract_corpus" not in source, path
        assert CORPUS.name not in source.split('"""')[-1], path
    # Nothing the package exposes names the corpus either.
    for module in OWNED_MODULES.values():
        assert not any(
            "corpus" in name.lower() for name in cast(list[str], module.__all__)
        )


def test_the_seven_production_modules_match_their_sealed_source_locks() -> None:
    """Sealed inputs, verified before the corpus is trusted to describe them.

    These digests are a source lock for this publication. They are not a
    permanent behavioral identity of the modules, and the corpus says so.
    """
    locks = cast(list[dict[str, Any]], MANIFEST["source_locks"])

    assert [cast(str, lock["module"]) for lock in locks] == list(OWNED_MODULES)
    for lock in locks:
        path = REPOSITORY_ROOT / cast(str, lock["path"])
        raw = path.read_bytes()
        assert lock["sha256"] == hashlib.sha256(raw).hexdigest(), lock["module"]
        assert lock["byte_length"] == len(raw), lock["module"]
        assert cast(str, lock["path"]) == (
            "src/" + cast(str, lock["module"]).replace(".", "/") + ".py"
        )
        # No retrieval-identity claim is published that is not verified here.
        assert set(lock) == {"byte_length", "module", "path", "sha256"}

    sealed = {
        cast(str, entry["path"]): cast(str, entry["sha256"])
        for entry in cast(
            list[dict[str, Any]],
            _parse_canonical_json(
                (
                    REPOSITORY_ROOT / cast(str, MANIFEST["entry_authority"]["path"])
                ).read_bytes()
            )["product_inventory"]["modules"],
        )
    }
    assert sealed == {
        cast(str, lock["path"]): cast(str, lock["sha256"]) for lock in locks
    }
    assert MANIFEST["assurance"]["source_locks_verified_against_live_bytes"] is True


# --- 15: the derived Markdown agrees with the canonical JSON -----------------


def test_the_contract_markdown_is_derived_from_the_json_authorities() -> None:
    text = (CORPUS / "contract.md").read_text("utf-8")
    raw = (CORPUS / "contract.md").read_bytes()
    summary = cast(dict[str, Any], MANIFEST["vector_summary"])

    assert not raw.startswith(b"\xef\xbb\xbf")
    assert b"\r" not in raw
    assert text.endswith("\n")
    assert "`S1.P06.S11`" in text
    assert MANIFEST["corpus_identity"]["id"] in text
    assert MANIFEST["corpus_identity"]["phase_closure_owner"] in text
    assert MANIFEST["corpus_identity"]["serialization_and_migration_owner"] in text

    for entry in cast(list[dict[str, Any]], MANIFEST["corpus_files"]):
        assert f"`{entry['filename']}`" in text, entry["filename"]
        if "sha256" in entry:
            assert cast(str, entry["sha256"]) in text, entry["filename"]
            assert str(entry["byte_length"]) in text, entry["filename"]
    for entry in cast(list[dict[str, Any]], MANIFEST["target_symbols"]):
        assert f"`{entry['symbol']}`" in text, entry["symbol"]
        assert f"`{entry['module']}`" in text, entry["module"]
    for module in cast(
        list[str], MANIFEST["scope"]["supporting_authorities_not_owned"]
    ):
        assert f"`{module}`" in text, module
    for goal in cast(list[str], MANIFEST["non_goals"]):
        assert f"- {goal}" in text, goal
    for limit in cast(list[str], MANIFEST["replay_contract"]["retained_case_limits"]):
        assert f"- {limit}" in text, limit
    for name in REPLAY_CLASSIFICATIONS:
        assert f"- `{name}` — " in text, name

    assert f"**{summary['valid']['count']}**" in text
    assert f"**{summary['invalid']['count']}**" in text
    assert f"**{summary['replay']['count']}**" in text
    assert f"{summary['total_vectors']} vectors" in text
    assert f"{summary['fixtures']} declared" in text
    assert f"{MANIFEST['scope']['owned_module_count']} owned" in text
    assert f"{MANIFEST['scope']['owned_symbol_count']} owned product" in text
    assert cast(str, MANIFEST["entry_authority"]["sha256"]) in text
    assert cast(str, MANIFEST["entry_authority"]["path"]) in text


def test_the_contract_markdown_names_nothing_the_json_does_not_carry() -> None:
    """Markdown is a projection, never a second authority.

    Every quoted token and every digest in the prose is required to appear in
    the canonical JSON, so a claim can only be removed from the Markdown, never
    added to it. The handful of structural tokens that name the repository
    rather than the corpus are authored here and counted.
    """
    text = (CORPUS / "contract.md").read_text("utf-8")
    serialised = json.dumps(MANIFEST, sort_keys=True, ensure_ascii=False)

    structural = frozenset(
        {
            "docs/",
            "faultatlas",
            "__all__",
            "strict=True",
        }
    )
    assert len(structural) == 4

    quoted = set(re.findall(r"`([^`]+)`", text))
    assert quoted, "the projection quotes the values it reports"
    unexplained = sorted(
        token for token in quoted if token not in serialised and token not in structural
    )
    assert not unexplained, unexplained

    for digest in set(re.findall(r"\b[0-9a-f]{64}\b", text)):
        assert digest in serialised, digest

    # Numbers are claims too, and quoting rules do not reach them: an inventory
    # count sitting in ordinary prose was unconstrained until this read it.
    def _integers(document: Any) -> Iterator[int]:
        if isinstance(document, dict):
            for item in cast(dict[str, Any], document).values():
                yield from _integers(item)
        elif isinstance(document, list):
            for item in cast(list[Any], document):
                yield from _integers(item)
        elif isinstance(document, bool):
            return
        elif isinstance(document, int):
            yield document

    carried = set(_integers(MANIFEST))
    assert len(carried) >= 20, sorted(carried)
    # The nine section numbers this projection is organised into.
    section_numbers = set(range(0, 10))
    # The lookahead excludes a following digit, word character, backtick or
    # hyphen but NOT a full stop: excluding it skipped every sentence-final
    # number, which is exactly where an inventory count tends to land.
    printed = {
        int(token) for token in re.findall(r"(?<![\w`-])(\d+)(?![\d\w`-])", text)
    }
    assert 20 in printed, "the package-boundary count is read"
    assert printed, "the projection reports numbers"
    unexplained_numbers = sorted(printed - carried - section_numbers)
    assert not unexplained_numbers, unexplained_numbers

    # And the retained case numbers it prints are the ones the fixtures carry.
    retained = cast(dict[str, Any], MANIFEST["replay_contract"]["retained_case"])
    repository = next(
        cast(dict[str, Any], fixture)["value"]
        for fixture in cast(list[Any], VALID["fixtures"])
        if fixture["id"] == "fault-instance.fixture.repository.pytest"
    )
    assert str(retained["repository_id"]) == repository["provider_repository_id"]
    assert retained["provider"] == repository["provider"]
    for key, fixture_id in (
        ("issue_number", "fault-instance.fixture.issue.4412"),
        ("pull_request_number", "fault-instance.fixture.pull-request.4414"),
    ):
        value = next(
            cast(dict[str, Any], fixture)["value"]
            for fixture in cast(list[Any], VALID["fixtures"])
            if fixture["id"] == fixture_id
        )
        assert str(retained[key]) == value["repository_scoped_number"], key

    # The authority sentence the corpus does publish is present verbatim.
    assert "The four canonical JSON files are the semantic authority" in text
    assert "this Markdown is a derived projection" in text
    assert (
        "every name, digest and number it reports is one the canonical JSON "
        "carries" in text
    )
    # The refusals are asserted in the form the projection actually states them,
    # rather than by scanning for a phrase that also occurs inside its own
    # denial.
    assert "does not flatten its layers into an evidence-derived fault instance" in text
    assert "no repair correctness" in text
    assert "no root cause and no violated invariant" in text
    assert "adds no production file, symbol, or product semantic" in text
    for affirmative in (
        "the root cause is",
        "the repair is correct",
        "verified by faultatlas",
        "proven by",
    ):
        assert affirmative not in text.lower(), affirmative


# --- the manifest's own claims -----------------------------------------------
#
# A manifest leaf that no oracle answers is a claim nobody checked. Every leaf
# is required to fall under exactly one authored validator prefix, or under a
# prefix the manifest itself declares as human-oriented prose. The two sets are
# disjoint, so prose can never quietly absorb an assurance claim.

VALIDATOR_PREFIXES: dict[str, tuple[str, ...]] = {
    "/assurance": ("test_the_assurance_block_is_recomputed",),
    "/corpus_files": (
        "test_every_corpus_file_declares_the_role_its_own_name_implies",
        "test_the_manifest_records_the_vector_file_digests_and_lengths",
        "test_the_corpus_directory_holds_exactly_the_declared_files",
    ),
    "/corpus_identity": ("test_the_corpus_identity_is_the_authored_constant",),
    "/descriptive_metadata/leaves": (
        "test_every_manifest_leaf_is_validated_or_declared_descriptive",
    ),
    "/entry_authority": (
        "test_the_owned_inventory_equals_what_the_sealed_s10_decision_recorded",
        "test_every_corpus_file_declares_the_role_its_own_name_implies",
    ),
    "/execution_contract": (
        "test_the_execution_contract_matches_the_executor",
        "test_unknown_target_operation_mode_and_marker_all_fail_closed",
        "test_no_supporting_authority_symbol_is_counted_as_owned",
    ),
    "/execution_contract/cardinality_probes": (
        "test_only_the_declared_cardinality_probes_may_omit_a_semantic_dump",
    ),
    "/fixture_provenance": (
        "test_every_retained_fixture_value_comes_from_the_retained_material",
        "test_declared_fixtures_are_shared_locked_and_actually_used",
    ),
    "/format": ("test_the_declared_canonicalization_is_the_one_enforced",),
    "/non_goals": ("test_the_non_generalizations_are_declared_and_specific",),
    "/rejection_contract": (
        "test_the_rejection_contract_locks_no_unstable_surface",
        "test_prefix_location_is_used_only_at_the_declared_union_positions",
        "test_every_root_located_rule_is_named_proven_and_exercised",
    ),
    "/replay_contract": (
        "test_replay_classifications_are_exactly_the_five_published_kinds",
        "test_the_replay_vertical_reaches_every_semantic_layer",
        "test_the_contract_markdown_is_derived_from_the_json_authorities",
        "test_the_contract_markdown_names_nothing_the_json_does_not_carry",
    ),
    "/scope": (
        "test_the_scope_matches_the_live_surface",
        "test_the_corpus_is_source_only_and_adds_no_production_file",
        "test_no_supporting_authority_symbol_is_counted_as_owned",
    ),
    "/source_locks": (
        "test_the_seven_production_modules_match_their_sealed_source_locks",
    ),
    "/support_targets": ("test_no_supporting_authority_symbol_is_counted_as_owned",),
    "/target_symbols": (
        "test_every_symbol_publishing_slice_matches_the_sealed_decision",
        "test_the_thirty_product_targets_come_from_live_dunder_all",
    ),
    "/vector_summary": ("test_the_declared_counts_match_the_vector_files",),
}


def _leaf_pointers(document: Any, prefix: str = "") -> Iterator[str]:
    if isinstance(document, dict):
        mapping = cast(dict[str, Any], document)
        if not mapping:
            yield prefix
            return
        for key, value in mapping.items():
            escaped = key.replace("~", "~0").replace("/", "~1")
            yield from _leaf_pointers(value, f"{prefix}/{escaped}")
        return
    if isinstance(document, list):
        items = cast(list[Any], document)
        if not items:
            yield prefix
            return
        for index, value in enumerate(items):
            yield from _leaf_pointers(value, f"{prefix}/{index}")
        return
    yield prefix


def test_every_manifest_leaf_is_validated_or_declared_descriptive() -> None:
    """Prose is declared leaf by leaf, and every other leaf must be answerable.

    Declaring prose by PREFIX was the defect this replaces: one assertion
    anywhere under a prefix discharged every leaf beneath it, so fifty-two
    objective leaves could be falsified with the suite green. The declaration
    is now an exact leaf list, and the sweep below answers the rest by
    falsifying each remaining leaf and requiring the corpus to refuse it.
    """
    descriptive = tuple(cast(list[str], MANIFEST["descriptive_metadata"]["leaves"]))
    assert len(descriptive) == len(set(descriptive)) == 17
    assert tuple(sorted(descriptive)) == descriptive, "declared in sorted order"
    assert not set(descriptive) & set(VALIDATOR_PREFIXES)
    assert cast(str, MANIFEST["descriptive_metadata"]["contract"]).strip()

    leaves = sorted(set(_leaf_pointers(MANIFEST)))
    assert leaves, "the manifest has leaves"
    assert set(descriptive) <= set(leaves), sorted(set(descriptive) - set(leaves))

    unexplained = [
        leaf
        for leaf in leaves
        if leaf not in descriptive
        and not any(
            leaf == prefix or leaf.startswith(prefix + "/")
            for prefix in VALIDATOR_PREFIXES
        )
    ]
    assert not unexplained, unexplained

    # Every authored prefix answers something: an unused one is a validator
    # claiming to cover a part of the manifest that no longer exists.
    for prefix in VALIDATOR_PREFIXES:
        assert any(
            leaf == prefix or leaf.startswith(prefix + "/") for leaf in leaves
        ), prefix
    module_source = Path(__file__).read_text("utf-8")
    for prefix, names in VALIDATOR_PREFIXES.items():
        assert names, prefix
        for test_name in names:
            assert f"def {test_name}(" in module_source, (prefix, test_name)


def test_the_assurance_block_is_recomputed() -> None:
    assurance = cast(dict[str, Any], MANIFEST["assurance"])

    assert assurance["canonical_json_files"] == len(SEALED_JSON) == 4
    assert assurance["sidecar_count"] == 4
    assert assurance["status"] == "locked"
    assert assurance["expected_dumps_independently_authored"] is True
    assert assurance["production_dump_used_as_oracle"] is False
    assert assurance["symbol_inventory_derived_from_live_dunder_all"] is True
    assert assurance["every_owned_symbol_is_executably_covered"] is True
    assert assurance["owned_symbol_coverage"] == f"{len(OWNED)}/30"
    assert assurance["source_locks_verified_against_live_bytes"] is True

    # The oracle never reads an expected value out of the product, so no
    # expectation in the corpus can be a restatement of what it produced.
    executor = Path(__file__).read_text("utf-8")
    assert "model_dump_json()" in executor
    body = executor.split("def _dump(")[1]
    assert "expected" not in body.split("def _ids(")[0]


def test_the_scope_matches_the_live_surface() -> None:
    scope = cast(dict[str, Any], MANIFEST["scope"])

    assert scope["phase"] == "S1.P06"
    assert scope["slice"] == "S1.P06.S11"
    assert scope["covered_slices"] == [f"S1.P06.S0{index}" for index in range(1, 10)]
    assert len(cast(list[str], scope["covered_slices"])) == 9
    assert "S1.P06.S10" not in cast(list[str], scope["covered_slices"])
    assert "S1.P06.S11" not in cast(list[str], scope["covered_slices"])
    assert scope["owned_modules"] == list(OWNED_MODULES)
    assert scope["owned_module_count"] == len(OWNED_MODULES)
    assert scope["owned_symbol_count"] == len(OWNED)
    # This historical count belongs to the sealed manifest, independent of later modules.
    assert scope["production_module_count"] == SEALED_PRODUCTION_MODULE_COUNT
    assert scope["source_only"] is True
    assert scope["package_exclusion_required"] is True
    assert cast(str, scope["note"]).strip() == scope["note"]

    # Every covered Slice is reached by an accepting vector.
    reached = {
        cast(str, vector["covered_slice"])
        for vector in ALL_VECTORS
        if vector["operation"] == "construct"
    }
    assert reached == set(cast(list[str], scope["covered_slices"]))


NON_GENERALIZATIONS = (
    "no universal relationship ontology",
    "no generic relationship graph",
    "no generic Git ancestry or reachability graph",
    "no merge-base, ahead, behind, or branch-containment semantics",
    "no complete development-history claim",
    "no support, confidence, or review calculus",
    "no field-level evidence locator",
    "no automatic evidence transitivity",
    "no repair correctness",
    "no independent test execution",
    "no reusable Pattern or Invariant",
    "no transfer or applicability semantics",
    "no persistence or production serializer",
    "no production corpus reader",
    "no source ingestion",
    "no retrieval or RAG",
    "no repository execution",
    "no root cause and no violated invariant",
    "no timestamp-implied causality and no fault-occurrence time",
    "no allocator and no identity resolution, deduplication, or merging",
    "no same-defect or different-defect equivalence judgement",
    "no canonical ordering of a composed collection",
    "corpus validity does not prove factual truth of caller-supplied records",
    "replayability does not promote a supplied claim into retained observation",
)


def test_the_non_generalizations_are_declared_and_specific() -> None:
    declared = cast(list[str], MANIFEST["non_goals"])

    # Authored here, not read back from the manifest: a list rebuilt from the
    # document it validates would accept whatever the document happens to say.
    assert tuple(declared) == NON_GENERALIZATIONS
    assert len(declared) == len(set(declared)) == 24
    assert declared[-2:] == [
        "corpus validity does not prove factual truth of caller-supplied records",
        "replayability does not promote a supplied claim into retained observation",
    ]
    normalised = [
        "".join(character for character in goal.lower() if character.isalnum())
        for goal in declared
    ]
    assert len(normalised) == len(set(normalised)), "no lexical duplicates"

    # None of the refused vocabulary exists on the published surface.
    for module in OWNED_MODULES.values():
        for symbol in cast(list[str], module.__all__):
            value = getattr(module, symbol)
            if not (isinstance(value, type) and issubclass(value, BaseModel)):
                continue
            fields = set(cast(dict[str, Any], value.model_fields))
            for forbidden in (
                "confidence",
                "support",
                "verification",
                "verified",
                "root_cause",
                "json_pointer",
                "field_pointer",
                "byte_span",
                "status",
                "promoted",
                "strength",
                "pattern",
                "invariant",
            ):
                assert forbidden not in fields, (symbol, forbidden)


# --- the lifecycle this Slice hands on ---------------------------------------

ROADMAP = REPOSITORY_ROOT / "docs/roadmap.md"


def test_the_roadmap_records_the_corpus_and_holds_the_phase_state() -> None:
    roadmap = ROADMAP.read_text("utf-8")

    assert "`S1.P06.S11` is complete" in roadmap
    assert "`S1.P06.S12` is complete" in roadmap
    # `S1.P07.S01` exercised the eligibility this Phase handed on, so the
    # gate moved: `S1.P07` is no longer the thing that has not started.
    assert "`S1.P07` is active and incomplete" in roadmap
    assert "The `S1.P06` route is closed at `S1.P06.S12`." in roadmap
    assert "`S1.P06` is complete" in roadmap
    assert "`S1.P06.S07.C01` correction" in roadmap

    assert "`S1.P06.S11` is next and not started" not in roadmap
    assert "`S1.P07` is next and not started" not in roadmap
    assert "`S1.P07` is complete" not in roadmap
    assert "`S1.P07` is complete" not in roadmap

    for claim in (
        "reference_corpus/contracts/fault-instance/v1",
        "seven owned production modules",
        "thirty owned product symbols",
        "30/30",
        "four canonical JSON files",
        "synthetic",
    ):
        assert claim in roadmap, claim
    # The corpus stays out of the package and no production module reads it.
    assert "excludes the corpus" in roadmap
    assert "production module count stays at 20" in roadmap

    # The roadmap narrative is a second published account of this Slice, so the
    # claims it shares with contract.md are required to agree. The unqualified
    # semantic-dump sentence survived one repair round here after being fixed
    # one directory away, because nothing read it.
    flat = " ".join(roadmap.split())
    exempt = cast(
        list[str],
        MANIFEST["execution_contract"]["cardinality_probes"]["may_omit_semantic_dump"],
    )
    assert len(exempt) == 1
    assert "except the one declared cardinality probe" in flat
    assert "semantic dump, so no expectation is a restatement" not in flat, (
        "the unqualified claim is false for the declared probe"
    )
    summary = cast(dict[str, Any], MANIFEST["vector_summary"])
    assert f"{summary['total_vectors']} vectors" in flat
    assert f"{summary['fixtures']} declared fixtures" in flat
    assert (
        f"{summary['valid']['count']} accepted, {summary['invalid']['count']} "
        f"refused and {summary['replay']['count']} replayed" in flat
    )
    assert len(cast(list[Any], MANIFEST["target_symbols"])) == 30
    assert "thirty owned product symbols" in flat
    assert "seven owned production modules" in flat


# --- the leaf-coverage claim, answered by falsifying every leaf --------------


def _resolve_leaf(document: Any, pointer: str) -> Any:
    node: Any = document
    for raw in pointer.split("/")[1:]:
        part = raw.replace("~1", "/").replace("~0", "~")
        node = (
            cast(list[Any], node)[int(part)]
            if isinstance(node, list)
            else cast(dict[str, Any], node)[part]
        )
    return node


def _set_leaf(document: Any, pointer: str, value: Any) -> None:
    parts = [
        raw.replace("~1", "/").replace("~0", "~") for raw in pointer.split("/")[1:]
    ]
    node: Any = document
    for part in parts[:-1]:
        node = (
            cast(list[Any], node)[int(part)]
            if isinstance(node, list)
            else cast(dict[str, Any], node)[part]
        )
    last = parts[-1]
    if isinstance(node, list):
        cast(list[Any], node)[int(last)] = value
    else:
        cast(dict[str, Any], node)[last] = value


def _falsify(value: Any) -> Any:
    if isinstance(value, bool):
        return not value
    if isinstance(value, int):
        return value + 1
    if isinstance(value, str):
        return "FALSIFIED-" + value
    raise AssertionError(f"unfalsifiable leaf value: {value!r}")


def test_falsifying_any_objective_manifest_leaf_is_refused(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The leaf-coverage claim, executed rather than asserted.

    The manifest says every leaf outside the declared prose list is refused
    when falsified. Checking that a validator NAME exists proves nothing about
    whether it reads the leaf, so each leaf is actually falsified here and the
    validators registered for it are required to refuse the result. A leaf no
    registered validator answers shows up as a survivor.
    """
    module = sys.modules[__name__]
    # Captured by value before anything is patched. Restoring with the bare
    # name would re-read the module global that the mutation just replaced,
    # which leaves every later leaf judged against an accumulated corruption
    # and makes the sweep pass whatever it is given.
    original = MANIFEST
    descriptive = set(cast(list[str], original["descriptive_metadata"]["leaves"]))
    validators = {
        prefix: tuple(getattr(module, name) for name in names)
        for prefix, names in VALIDATOR_PREFIXES.items()
    }

    pointers = sorted(set(_leaf_pointers(original)))
    survivors: list[str] = []
    swept = 0
    for pointer in pointers:
        if pointer in descriptive:
            continue
        value = _resolve_leaf(original, pointer)
        if not isinstance(value, (bool, int, str)):
            # An empty container is a leaf with nothing to falsify.
            continue
        swept += 1
        mutated = copy.deepcopy(original)
        _set_leaf(mutated, pointer, _falsify(value))
        monkeypatch.setattr(module, "MANIFEST", mutated)
        try:
            # The question is only whether anything objects. A falsified path
            # that no longer resolves, a falsified digest that no longer
            # matches and a falsified count that no longer adds up are all
            # refusals.
            refused = False
            for prefix, registered in validators.items():
                if not (pointer == prefix or pointer.startswith(prefix + "/")):
                    continue
                for validator in registered:
                    try:
                        validator()
                    except Exception:  # noqa: BLE001
                        refused = True
                        break
                if refused:
                    break
            if not refused:
                survivors.append(pointer)
        finally:
            monkeypatch.setattr(module, "MANIFEST", original)

    # The restore is load-bearing, so it is checked rather than assumed.
    assert module.MANIFEST is original
    assert not survivors, survivors
    assert swept >= 400, swept
    assert len(descriptive) == 17
