"""One source-only synthetic P07 corpus, with fixed dispatch and authored oracles."""

from __future__ import annotations

import copy
import hashlib
import json
import uuid
from collections import Counter
from pathlib import Path
from typing import Any, cast

import pytest
from _repository_contract import P07_SURFACE
from pydantic import BaseModel, ValidationError

from faultatlas.domain.evidence import DurableEvidenceRecordReference
from faultatlas.domain.fault import (
    FaultInstanceIdentity,
    FaultReportIdentity,
    FaultRepositoryContext,
    SuppliedFaultReport,
)
from faultatlas.domain.fault_evidence_link import FaultInstanceEvidenceLink
from faultatlas.domain.fault_instance import FaultInstance
from faultatlas.domain.fault_interpretation import (
    FaultExpectedPropertyIdentity,
    SuppliedFaultExpectedProperty,
)
from faultatlas.domain.fault_test import (
    FaultTestMaterialIdentity,
    FaultTestRunIdentity,
    ReportedFaultTestOutcome,
    ReportedFaultTestOutcomeKind,
    ReportedFaultTestRun,
    SuppliedFaultTestMaterial,
)
from faultatlas.domain.identity import (
    ProviderKey,
    ProviderRepositoryId,
    RepositoryIdentity,
)
from faultatlas.domain.invariant import FaultInvariantIdentity, SuppliedFaultInvariant
from faultatlas.domain.invariant_relationship import (
    FaultInvariantExpectedPropertyAssociation,
    FaultPatternInvariantAssociation,
)
from faultatlas.domain.pattern import FaultPatternIdentity, SuppliedFaultPattern
from faultatlas.domain.pattern_composition import FaultPatternComposition
from faultatlas.domain.pattern_exemplar import FaultPatternExemplarAssociation

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "reference_corpus/contracts/pattern-invariant/v1"
S07_PATH = "reference_corpus/contracts/pattern-invariant/decisions/s07-deferred-subject-disposition-readiness/decision.json"
S07_SHA = "8937e1a896d8d4a78f01ce82878d478318b853532f90d9b93192f22d976ae237"
S07_LENGTH = 22947
FORMAT = "faultatlas-pattern-invariant-contract-corpus"
STEMS = ("manifest", "valid-vectors", "invalid-vectors", "composition-vectors")
FILES = {"contract.md", *(s + suffix for s in STEMS for suffix in (".json", ".sha256"))}
PINS = {
    "manifest.json": (
        "9f1539ea47158b72466b17c1e774e9173f2a8def3f1e3237659504b8c6e7dc8b",
        10529,
    ),
    "valid-vectors.json": (
        "1063f1af440bcd1f569025153a3205d260e2ef98473a22e3cc9d0ec2ee13492c",
        24689,
    ),
    "invalid-vectors.json": (
        "d102e7ee656f2c2934eea630982d745d96c764c9594268ee40d1c71c99c8b2fa",
        9943,
    ),
    "composition-vectors.json": (
        "ed737148c3b182a1e27b4a35186ca525be557a05c132c29a13be3ed0c73e6b4d",
        100145,
    ),
}
TARGETS: dict[str, type[BaseModel]] = {
    "FaultPatternIdentity": FaultPatternIdentity,
    "SuppliedFaultPattern": SuppliedFaultPattern,
    "FaultPatternExemplarAssociation": FaultPatternExemplarAssociation,
    "FaultInvariantIdentity": FaultInvariantIdentity,
    "SuppliedFaultInvariant": SuppliedFaultInvariant,
    "FaultPatternInvariantAssociation": FaultPatternInvariantAssociation,
    "FaultInvariantExpectedPropertyAssociation": FaultInvariantExpectedPropertyAssociation,
    "FaultPatternComposition": FaultPatternComposition,
}
PC = "FaultPatternComposition"
IDENTITIES = {"FaultPatternIdentity", "FaultInvariantIdentity"}
PROPOSITIONS = {"SuppliedFaultPattern", "SuppliedFaultInvariant"}
OPERATIONS = ("validate", "reject", "compare")
MODES = ("python", "json", "json_wire")
RECIPES = ("typed", "literal", "wire", "nominal", "separate", "evidence")
# Obligation meaning is independent of row IDs and manifest-derived counters.
OBLIGATIONS = {
    "pattern_identity": "FaultPatternIdentity",
    "pattern": "SuppliedFaultPattern",
    "exemplar": "FaultPatternExemplarAssociation",
    "invariant_identity": "FaultInvariantIdentity",
    "invariant": "SuppliedFaultInvariant",
    "pattern_invariant": "FaultPatternInvariantAssociation",
    "invariant_expected": "FaultInvariantExpectedPropertyAssociation",
    "composition": PC,
    "two_cases": PC,
    "relation_independence": PC,
    "order_repetition": PC,
    "separate_roots": PC,
    "competing_claims": PC,
    "no_global_registry": PC,
    "evidence_separation": PC,
    "nominal_identity": "FaultPatternIdentity",
    "owner_revalidation": PC,
}
DEFECTS = {
    "raw_identity": (IDENTITIES, {"python"}),
    "bad_uuid": (IDENTITIES, {"json"}),
    "untyped_identity": (PROPOSITIONS, {"python"}),
    "padded_text": (PROPOSITIONS, {"json"}),
    "untyped_pattern": (
        {"FaultPatternExemplarAssociation", "FaultPatternInvariantAssociation"},
        {"python"},
    ),
    "extra_claim": (
        {"FaultPatternExemplarAssociation", "FaultPatternInvariantAssociation"},
        {"json"},
    ),
    "wrong_property": ({"FaultInvariantExpectedPropertyAssociation"}, {"python"}),
    "other_case_property": ({"FaultInvariantExpectedPropertyAssociation"}, {"json"}),
    "list_collection": ({PC}, {"python"}),
    "null_collection": ({PC}, {"json"}),
    "duplicate_invariant": ({PC}, {"python"}),
    "orphan_invariant": ({PC}, {"json"}),
    "wrong_pattern": ({PC}, {"json"}),
    "wrong_invariant": ({PC}, {"python"}),
    "nested_wrong_property": ({PC}, {"python"}),
    "invalid_nested_child": ({PC}, {"python"}),
    "lone_surrogate": ({"SuppliedFaultPattern"}, {"json_wire"}),
}
PRIMARY_SOURCES = {
    "p03": (
        "reference_corpus/contracts/evidence-envelope/closures/s1-p03-phase-closure/closure.json",
        "/deferred_register/entries/3",
        "deferred_id",
        "deferred:04",
    ),
    "p00": (
        "reference_corpus/pytest-4412/closures/s1-p00-phase-closure/closure.json",
        "/deferred_register/items/23",
        "deferred_item_id",
        "gap:s05-known:cross-repository-pattern-and-transfer-not-established",
    ),
    "p01": (
        "reference_corpus/contracts/identity/closures/s1-p01-phase-closure/closure.json",
        "/deferred_register/items/37",
        "deferred_item_id",
        "deferred:p01:p07-pattern-generality",
    ),
}


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _keys(
    data: dict[str, Any],
    required: set[str],
    optional: set[str] | frozenset[str] = frozenset(),
) -> None:
    _require(required <= data.keys() <= required | optional, "recipe input fields")


def _pattern(data: dict[str, Any]) -> SuppliedFaultPattern:
    _keys(data, {"id", "text"})
    return SuppliedFaultPattern(
        pattern=FaultPatternIdentity(uuid.UUID(data["id"])),
        pattern_statement=data["text"],
    )


def _invariant(data: dict[str, Any]) -> SuppliedFaultInvariant:
    _keys(data, {"id", "text"})
    return SuppliedFaultInvariant(
        invariant=FaultInvariantIdentity(uuid.UUID(data["id"])),
        invariant_statement=data["text"],
    )


def _report(data: dict[str, Any]) -> SuppliedFaultReport:
    return SuppliedFaultReport(
        report=FaultReportIdentity(uuid.UUID(data["report"])),
        context=FaultRepositoryContext(
            fault=FaultInstanceIdentity(uuid.UUID(data["fault"])),
            repository=RepositoryIdentity(
                provider=ProviderKey("github"),
                provider_repository_id=ProviderRepositoryId(data["repository"]),
            ),
        ),
        problem_statement=data["problem"],
        behavioral_deviation=data["deviation"],
    )


def _property(data: dict[str, Any]) -> SuppliedFaultExpectedProperty:
    return SuppliedFaultExpectedProperty(
        expected_property=FaultExpectedPropertyIdentity(uuid.UUID(data["property"])),
        report=_report(data),
        expected_property_statement=data["expectation"],
    )


def _case(data: dict[str, Any]) -> FaultInstance:
    _keys(
        data,
        {
            "fault",
            "report",
            "property",
            "repository",
            "problem",
            "deviation",
            "expectation",
        },
        {"test"},
    )
    values: dict[str, Any] = {
        "fault": FaultInstanceIdentity(uuid.UUID(data["fault"])),
        "reports": (_report(data),),
        "expected_properties": (_property(data),),
    }
    if "test" in data:
        test = data["test"]
        _keys(test, {"material", "run", "procedure", "attempt", "outcomes"})
        material = SuppliedFaultTestMaterial(
            material=FaultTestMaterialIdentity(uuid.UUID(test["material"])),
            report=_report(data),
            test_statement=test["procedure"],
        )
        run = ReportedFaultTestRun(
            run=FaultTestRunIdentity(uuid.UUID(test["run"])),
            test_material=material,
            run_statement=test["attempt"],
        )
        outcomes: list[ReportedFaultTestOutcome] = []
        for outcome in test["outcomes"]:
            _keys(outcome, {"kind", "text"})
            outcomes.append(
                ReportedFaultTestOutcome(
                    run=run,
                    outcome=ReportedFaultTestOutcomeKind(outcome["kind"]),
                    outcome_statement=outcome["text"],
                )
            )
        values.update(
            test_materials=(material,), test_runs=(run,), test_outcomes=tuple(outcomes)
        )
    return FaultInstance.model_validate(values)


def _pick(values: list[Any], index: Any) -> Any:
    _require(
        type(index) is int and 0 <= index < len(values),
        "unknown local recipe reference",
    )
    return values[index]


def _composition(data: dict[str, Any]) -> dict[str, Any]:
    _keys(
        data,
        {"pattern"},
        {"invariants", "cases", "exemplars", "attachments", "expectations"},
    )
    cases: list[dict[str, Any]] = data.get("cases", [])
    invariants: list[dict[str, Any]] = data.get("invariants", [])
    # Only these named collections become tuples; no recursive mapping coercion.
    result: dict[str, Any] = {"pattern": _pattern(data["pattern"])}
    if "invariants" in data:
        result["invariants"] = tuple(_invariant(v) for v in invariants)
    if "exemplars" in data:
        result["exemplar_associations"] = tuple(
            FaultPatternExemplarAssociation(
                pattern=_pattern(data["pattern"]), fault_instance=_case(_pick(cases, i))
            )
            for i in data["exemplars"]
        )
    if "attachments" in data:
        result["pattern_invariant_associations"] = tuple(
            FaultPatternInvariantAssociation(
                pattern=_pattern(data["pattern"]),
                invariant=_invariant(_pick(invariants, i)),
            )
            for i in data["attachments"]
        )
    if "expectations" in data:
        links: list[FaultInvariantExpectedPropertyAssociation] = []
        for pair in data["expectations"]:
            _require(
                isinstance(pair, list) and len(cast(list[Any], pair)) == 2,
                "expectation recipe pair",
            )
            inv, case = _pick(invariants, pair[0]), _pick(cases, pair[1])
            # Reconstructed equal endpoints, not retained object identity.
            links.append(
                FaultInvariantExpectedPropertyAssociation(
                    invariant=_invariant(inv),
                    fault_instance=_case(case),
                    expected_property=_property(case),
                )
            )
        result["invariant_expected_property_associations"] = tuple(links)
    return result


def _python_input(target: str, data: dict[str, Any]) -> Any:
    if target in IDENTITIES:
        _keys(data, {"root"})
        return uuid.UUID(data["root"])
    if target == "SuppliedFaultPattern":
        _keys(data, {"id", "text"})
        return {
            "pattern": FaultPatternIdentity(uuid.UUID(data["id"])),
            "pattern_statement": data["text"],
        }
    if target == "SuppliedFaultInvariant":
        _keys(data, {"id", "text"})
        return {
            "invariant": FaultInvariantIdentity(uuid.UUID(data["id"])),
            "invariant_statement": data["text"],
        }
    if target == "FaultPatternExemplarAssociation":
        _keys(data, {"pattern", "case"})
        return {
            "pattern": _pattern(data["pattern"]),
            "fault_instance": _case(data["case"]),
        }
    if target == "FaultPatternInvariantAssociation":
        _keys(data, {"pattern", "invariant"})
        return {
            "pattern": _pattern(data["pattern"]),
            "invariant": _invariant(data["invariant"]),
        }
    if target == "FaultInvariantExpectedPropertyAssociation":
        _keys(data, {"invariant", "case"})
        return {
            "invariant": _invariant(data["invariant"]),
            "fault_instance": _case(data["case"]),
            "expected_property": _property(data["case"]),
        }
    _require(target == PC, "unknown typed target")
    return _composition(data)


def _call(
    target: str,
    mode: str,
    payload: Any,
    calls: dict[str, list[str]],
    role: str = "primary",
) -> BaseModel:
    calls[role].append(target)
    if mode == "python":
        return TARGETS[target].model_validate(payload)
    wire = (
        payload
        if mode == "json_wire"
        else json.dumps(payload, ensure_ascii=True, allow_nan=False)
    )
    return TARGETS[target].model_validate_json(wire)


def _match_errors(
    error: ValidationError, expected: list[dict[str, Any]], label: str
) -> None:
    actual = error.errors()
    assert [(list(e["loc"]), e["type"]) for e in actual] == [
        (e["loc"], e["type"]) for e in expected
    ], f"{label}: wrong error location/type: {actual}"
    for found, wanted in zip(actual, expected, strict=True):
        if "message" in wanted:
            assert wanted["message"] in found["msg"], (
                f"{label}: wrong rule message: {found}"
            )


def _defect(row: dict[str, Any], payload: Any) -> Any:
    defect, argument, target = row["defect"], row["argument"], row["target"]
    if defect == "raw_identity":
        return str(payload)
    if defect in {"bad_uuid", "lone_surrogate"}:
        return argument
    if defect == "untyped_identity":
        key = "pattern" if target == "SuppliedFaultPattern" else "invariant"
        payload[key] = payload[key].root
    elif defect == "padded_text":
        payload[
            "pattern_statement"
            if target == "SuppliedFaultPattern"
            else "invariant_statement"
        ] = argument
    elif defect == "untyped_pattern":
        p = payload["pattern"]
        payload["pattern"] = {
            "pattern": p.pattern,
            "pattern_statement": p.pattern_statement,
        }
    elif defect == "extra_claim":
        payload["support"] = True
    elif defect == "wrong_property":
        p = payload["expected_property"]
        payload["expected_property"] = SuppliedFaultExpectedProperty(
            expected_property=p.expected_property,
            report=p.report,
            expected_property_statement=argument,
        )
    elif defect == "other_case_property":
        # Its own complete record is legal; only association membership is wrong.
        SuppliedFaultExpectedProperty.model_validate_json(json.dumps(argument))
        payload["expected_property"] = copy.deepcopy(argument)
    elif defect == "list_collection":
        payload["exemplar_associations"] = list(payload["exemplar_associations"])
    elif defect == "null_collection":
        payload["invariants"] = None
    elif defect == "duplicate_invariant":
        payload["invariants"] += (payload["invariants"][0],)
    elif defect == "orphan_invariant":
        payload["pattern_invariant_associations"] = []
    elif defect == "wrong_pattern":
        payload["exemplar_associations"][0]["pattern"]["pattern_statement"] = argument
    elif defect == "wrong_invariant":
        link = payload["pattern_invariant_associations"][0]
        changed = SuppliedFaultInvariant(
            invariant=link.invariant.invariant, invariant_statement=argument
        )
        payload["pattern_invariant_associations"] = (
            FaultPatternInvariantAssociation(pattern=link.pattern, invariant=changed),
            *payload["pattern_invariant_associations"][1:],
        )
    else:
        _require(
            defect in {"nested_wrong_property", "invalid_nested_child"},
            "unknown defect",
        )
        link = payload["invariant_expected_property_associations"][0]
        original = link.expected_property
        if defect == "nested_wrong_property":
            changed = SuppliedFaultExpectedProperty(
                expected_property=original.expected_property,
                report=original.report,
                expected_property_statement=argument,
            )
        else:
            changed = original.model_copy(
                update={"expected_property_statement": argument}
            )
            try:
                SuppliedFaultExpectedProperty.model_validate(changed)
            except ValidationError as error:
                _match_errors(
                    error, row["expect"]["owner_error"], row["id"] + " direct owner"
                )
            else:
                raise AssertionError(
                    "deliberately invalid child passed its direct owner"
                )
        # Explicitly named invalid re-entry witness; all other builders validate.
        invalid = link.model_copy(update={"expected_property": changed})
        payload["invariant_expected_property_associations"] = (
            invalid,
            *payload["invariant_expected_property_associations"][1:],
        )
    return payload


def _execute(
    row: dict[str, Any], rows: dict[str, dict[str, Any]], calls: dict[str, list[str]]
) -> None:
    target, mode, operation = row["target"], row["mode"], row["operation"]
    if operation == "compare":
        data = copy.deepcopy(row["input"])
        if row["recipe"] == "nominal":
            value = _call(target, "python", _python_input(target, data), calls)
            other = _call(
                "FaultInvariantIdentity",
                "python",
                _python_input("FaultInvariantIdentity", data),
                calls,
                "companion",
            )
            actual = {
                "value": value.model_dump(mode="json"),
                "companion": other.model_dump(mode="json"),
                "equal": value == other,
            }
        elif row["recipe"] == "separate":
            _keys(data, {"left", "right"})
            value = _call(target, "python", _composition(data["left"]), calls)
            other = _call(
                target, "python", _composition(data["right"]), calls, "companion"
            )
            actual = {
                "value": value.model_dump(mode="json"),
                "companion": other.model_dump(mode="json"),
                "equal": value == other,
            }
        else:
            _keys(data, {"composition", "evidence"})
            case = _case(data["composition"]["cases"][0])
            reference = DurableEvidenceRecordReference.model_validate_json(
                json.dumps(data["evidence"])
            )
            bridge = FaultInstanceEvidenceLink(
                fault_instance=case,
                subject=case.expected_properties[0],
                evidence_record=reference,
            )
            before = bridge.model_dump(mode="json")
            value = _call(target, "python", _composition(data["composition"]), calls)
            actual = {
                "value": value.model_dump(mode="json"),
                "evidence_before": before,
                "evidence_after": bridge.model_dump(mode="json"),
            }
        assert actual == row["expect"], f"{row['id']}: authored comparison mismatch"
        return
    if operation == "validate":
        payload = (
            _python_input(target, copy.deepcopy(row["input"]))
            if mode == "python"
            else copy.deepcopy(row["input"])
        )
        value = _call(target, mode, payload, calls)
        assert {"value": value.model_dump(mode="json")} == row["expect"], (
            f"{row['id']}: authored value mismatch"
        )
        return
    base = rows[row["base"]]
    payload = (
        _python_input(target, copy.deepcopy(base["input"]))
        if base["mode"] == "python"
        else copy.deepcopy(base["input"])
    )
    # Positive control and all mutation setup are outside the rejection catch.
    control = _call(target, base["mode"], payload, calls, "prerequisite")
    assert {"value": control.model_dump(mode="json")} == base["expect"], (
        f"{row['id']}: invalid prerequisite"
    )
    payload = _defect(row, payload)
    try:
        _call(target, mode, payload, calls)
    except ValidationError as error:
        _match_errors(error, row["expect"]["error"], row["id"])
    else:
        raise AssertionError(f"{row['id']}: expected model rejection")


def _pointer(value: Any, pointer: str) -> Any:
    for token in pointer.split("/")[1:]:
        token = token.replace("~1", "/").replace("~0", "~")
        value = (
            cast(list[Any], value)[int(token)]
            if isinstance(value, list)
            else value[token]
        )
    return value


def _preserved_limits(manifest: dict[str, Any]) -> None:
    authority = manifest["authority"]
    _require(
        (authority["path"], authority["sha256"], authority["byte_length"])
        == (S07_PATH, S07_SHA, S07_LENGTH),
        "S07 authority lock",
    )
    raw = (ROOT / S07_PATH).read_bytes()
    _require(
        hashlib.sha256(raw).hexdigest() == S07_SHA and len(raw) == S07_LENGTH,
        "S07 source bytes",
    )
    decision = json.loads(raw)
    _require(
        len(authority["subjects"]) == len(PRIMARY_SOURCES),
        "source-qualified subject coverage",
    )
    for index, (key, (path, pointer, id_field, identifier)) in enumerate(
        PRIMARY_SOURCES.items()
    ):
        original = _pointer(decision, f"/subjects/{index}")
        _require(original["id"] == identifier, "S07 subject selector identity")
        expected = {
            "selector": f"/subjects/{index}",
            "id": identifier,
            "disposition": original["disposition"],
            "source": {"path": path, "selector": pointer},
            "remainder": original["remainder"],
        }
        _require(
            authority["subjects"][index] == expected,
            "preserved empirical disposition/owner/revisit",
        )
        source = decision["inputs"][key]
        source_raw = (ROOT / path).read_bytes()
        _require(
            source["path"] == path
            and hashlib.sha256(source_raw).hexdigest() == source["sha256"]
            and len(source_raw) == source["byte_length"],
            "retained source lock",
        )
        selected = _pointer(json.loads(source_raw), pointer)
        _require(selected[id_field] == identifier, "retained root identity")
        selector = source["selectors"][original["source"]["selection"]]
        _require(
            selector["pointer"] == pointer
            and all(selected[k] == v for k, v in selector["expected"].items()),
            "retained source selector content",
        )
    _require(
        manifest["publication"]
        == {
            "state": "sealed_publication_candidate",
            "completion_evidence": "external_Git_GitHub_and_task_receipt",
            "condition": "protected_squash_and_successful_natural_main_verification",
        },
        "external publication boundary",
    )


def _catalog(documents: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    _require(set(documents) == set(STEMS), "document inventory")
    for stem, document in documents.items():
        f = document["format"]
        _require(
            type(f["version"]) is int
            and f["version"] == 1
            and f["name"] == FORMAT
            and f["kind"] == stem,
            "unknown format version/kind",
        )
    m = documents["manifest"]
    _require(
        set(m["files"]) == {s + ".json" for s in STEMS[1:]}, "vector file declarations"
    )
    _require(
        m["operations"] == list(OPERATIONS)
        and m["modes"] == list(MODES)
        and m["recipes"] == list(RECIPES),
        "dispatch contract",
    )
    expected_targets = {name: owner.__module__ for name, owner in TARGETS.items()}
    shared = {
        symbol: "faultatlas.domain." + module
        for module, symbols in P07_SURFACE
        for symbol in symbols
    }
    _require(
        m["targets"] == expected_targets
        and all(shared[n] == owner for n, owner in expected_targets.items()),
        "owned target map",
    )
    rows_list = [r for stem in STEMS[1:] for r in documents[stem]["vectors"]]
    ids = [r["id"] for r in rows_list]
    _require(
        all(isinstance(i, str) and i for i in ids) and len(ids) == len(set(ids)),
        "duplicate/invalid vector ID",
    )
    rows = {r["id"]: r for r in rows_list}
    for row in rows_list:
        target, operation, mode, recipe = (
            row["target"],
            row["operation"],
            row["mode"],
            row["recipe"],
        )
        _require(target in TARGETS, "unknown target")
        _require(operation in OPERATIONS, "unknown operation")
        fields = {
            "id",
            "target",
            "operation",
            "mode",
            "recipe",
            "obligation",
            "provenance",
            "expect",
        }
        fields |= {"base", "defect", "argument"} if operation == "reject" else {"input"}
        _require(set(row) == fields, "vector fields")
        _require(mode in MODES, "unknown input mode")
        _require(recipe in RECIPES, "unknown recipe")
        _require(
            row["obligation"] in OBLIGATIONS
            and OBLIGATIONS[row["obligation"]] == target,
            "wrong obligation target",
        )
        _require(
            row["provenance"] == "synthetic_caller_supplied",
            "synthetic provenance required",
        )
        if operation == "compare":
            _require(
                mode == "python" and recipe in {"nominal", "separate", "evidence"},
                "compare recipe/mode",
            )
            _require(
                target == ("FaultPatternIdentity" if recipe == "nominal" else PC),
                "compare target",
            )
        else:
            _require(
                recipe
                == {"python": "typed", "json": "literal", "json_wire": "wire"}[mode],
                "recipe/mode mismatch",
            )
        if operation == "reject":
            _require(row["defect"] in DEFECTS, "unknown defect")
            targets, modes = DEFECTS[row["defect"]]
            _require(target in targets and mode in modes, "defect target/mode")
            _require(row["base"] in rows, "unknown base reference")
            base = rows[row["base"]]
            _require(
                base["target"] == target
                and base["operation"] == "validate"
                and base["mode"] == ("json" if mode == "json_wire" else mode),
                "wrong base target/example",
            )
    _require(set(m["obligations"]) == set(OBLIGATIONS), "obligation coverage")
    accounted: list[str] = []
    for obligation, refs in m["obligations"].items():
        _require(bool(refs), "empty obligation")
        for ref in refs:
            _require(
                ref in rows and rows[ref]["obligation"] == obligation,
                "wrong obligation reference",
            )
        accounted.extend(refs)
    _require(
        len(accounted) == len(set(accounted)) and set(accounted) == set(rows),
        "unaccounted executable rows",
    )
    _require(set(m["coverage"]) == set(TARGETS), "primary target coverage")
    for target, bucket in m["coverage"].items():
        for outcome, accepted in [("accepted", True), ("rejected", False)]:
            actual = [
                r["id"]
                for r in rows_list
                if r["target"] == target and (r["operation"] != "reject") == accepted
            ]
            _require(
                bool(actual) and bucket[outcome] == actual,
                "wrong primary target coverage/reference",
            )
    counts = {
        "files": {s: len(documents[s]["vectors"]) for s in STEMS[1:]},
        "vectors": len(rows_list),
        "accepted": sum(r["operation"] != "reject" for r in rows_list),
        "rejected": sum(r["operation"] == "reject" for r in rows_list),
    }
    _require(m["counts"] == counts, "derived row counts")
    _require(
        m["provenance"]
        == {
            "executable_examples": "synthetic_caller_supplied",
            "retained_governance_sources": "metadata_only_not_observed_case_examples",
            "independent_observed_failures": 0,
        },
        "manifest synthetic provenance",
    )
    _preserved_limits(m)
    return rows


def _run(documents: dict[str, dict[str, Any]]) -> dict[str, Any]:
    rows = _catalog(documents)  # All metadata checked before any model dispatch.
    calls: dict[str, list[str]] = {"primary": [], "prerequisite": [], "companion": []}
    matched: list[tuple[str, str, str]] = []
    for row in rows.values():
        _execute(copy.deepcopy(row), rows, calls)
        matched.append(
            (
                row["id"],
                row["target"],
                "rejected" if row["operation"] == "reject" else "accepted",
            )
        )
    observed = {(target, outcome) for _, target, outcome in matched}
    assert observed == {
        (target, outcome) for target in TARGETS for outcome in ("accepted", "rejected")
    }
    return {
        "matched_rows": len(matched),
        "matched": matched,
        "dispatches": {role: dict(Counter(names)) for role, names in calls.items()},
        "primary_dispatches": len(calls["primary"]),
        "prerequisite_dispatches": len(calls["prerequisite"]),
        "companion_dispatches": len(calls["companion"]),
        "targets": sorted({target for _, target, _ in matched}),
    }


def _no_float(value: str) -> Any:
    raise ValueError("non-integer artifact number: " + value)


def _canonical(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def _documents(directory: Path = CORPUS) -> dict[str, dict[str, Any]]:
    return {
        s: json.loads(
            (directory / (s + ".json")).read_text(encoding="utf-8"),
            parse_float=_no_float,
            parse_constant=_no_float,
        )
        for s in STEMS
    }


def _render(documents: dict[str, dict[str, Any]]) -> str:
    m = documents["manifest"]
    lines = [
        "# P07 Pattern/Invariant Contract Corpus v1",
        "",
        "Source-only synthetic constructor examples; JSON is authoritative. No retained-real replay or empirical generality is established.",
        "",
        "## Fixed target snapshot",
        "",
        "| Target | Owner |",
        "| --- | --- |",
    ]
    lines += [
        f"| `{target}` | `{owner}` |" for target, owner in sorted(m["targets"].items())
    ]
    lines += [
        "",
        "## Executable vectors",
        "",
        "| ID | Target | Operation / mode / recipe | Obligation |",
        "| --- | --- | --- | --- |",
    ]
    for s in STEMS[1:]:
        for r in documents[s]["vectors"]:
            lines.append(
                f"| `{r['id']}` | `{r['target']}` | {r['operation']} / {r['mode']} / {r['recipe']} | {r['obligation']} |"
            )
    lines += [
        "",
        "Counts: `"
        + json.dumps(m["counts"], sort_keys=True)
        + "`. Counts describe declared rows; execution results live in external validation receipts.",
        "",
        "Input builders consume explicit declarations; expected primitives are separately authored, including defaults and tuple order. Actual model dumps are compared to those expectations, never used to generate them.",
        "Every rejection validates a legal base first. Native JSON enters model_validate_json; escaped product wire preserves the lone-surrogate case without corrupting artifact UTF-8. Unknown dispatch metadata fails before model calls.",
        "",
        "## Integrity",
        "",
        "Each sha256sum-style sidecar locks its own JSON. The manifest locks the three vector JSON files; the focused test independently pins all four. This view has no self-digest or hash cycle.",
        "",
    ]
    lines += [
        f"- `{name}`: `{lock['sha256']}`, {lock['byte_length']} bytes."
        for name, lock in sorted(m["files"].items())
    ]
    a = m["authority"]
    lines += [
        "",
        "## Preserved S07 authority",
        "",
        f"`{a['path']}`: `{a['sha256']}`, {a['byte_length']} bytes.",
    ]
    for subject in a["subjects"]:
        lines += [
            "- `"
            + subject["selector"]
            + "`: `"
            + subject["id"]
            + "`, `"
            + subject["disposition"]
            + "`; origin `"
            + subject["source"]["path"]
            + "#"
            + subject["source"]["selector"]
            + "`."
        ]
        if subject["remainder"]:
            r = subject["remainder"]
            lines += [
                "  `"
                + r["state"]
                + "`; owner `"
                + r["owner"]
                + "`; revisit `"
                + r["revisit"]
                + "`. "
                + r["reason"]
            ]
    lines += ["", "## Reused focused owners", "", m["reused_owners"]["semantics"]]
    lines += [
        "- `" + key + "`: `" + node + "`"
        for key, node in sorted(m["reused_owners"]["nodes"].items())
    ]
    lines += ["", "## Limits", ""] + ["- " + s for s in m["limits"]]
    lines += [
        "",
        "Publication: `" + json.dumps(m["publication"], sort_keys=True) + "`.",
    ]
    return "\n".join(lines) + "\n"


def _integrity(directory: Path = CORPUS) -> None:
    paths = list(directory.iterdir())
    _require({p.name for p in paths} == FILES, "corpus file inventory")
    _require(
        all(p.is_file() and not p.is_symlink() for p in paths),
        "regular corpus files required",
    )
    docs = _documents(directory)
    for filename, (sha, length) in PINS.items():
        raw = (directory / filename).read_bytes()
        stem = filename.removesuffix(".json")
        _require(_canonical(docs[stem]) == raw, "canonical artifact bytes")
        _require(
            len(raw) == length and hashlib.sha256(raw).hexdigest() == sha,
            "independent artifact pin",
        )
        _require(
            (directory / (stem + ".sha256")).read_bytes()
            == f"{sha}  {filename}\n".encode(),
            "sidecar mismatch",
        )
    for name, lock in docs["manifest"]["files"].items():
        _require(name in {s + ".json" for s in STEMS[1:]}, "vector file lock target")
        raw = (directory / name).read_bytes()
        _require(
            lock
            == {"sha256": hashlib.sha256(raw).hexdigest(), "byte_length": len(raw)},
            "manifest vector lock",
        )
    _require(
        (directory / "contract.md").read_text(encoding="utf-8") == _render(docs),
        "derived Markdown mismatch",
    )


def test_corpus_integrity_and_complete_execution() -> None:
    _integrity()
    report = _run(_documents())
    assert report["matched_rows"] == _documents()["manifest"]["counts"]["vectors"]
    assert report["targets"] == sorted(TARGETS)
    assert report["primary_dispatches"] == report["matched_rows"]


@pytest.mark.parametrize(
    "change", ("canonical", "sidecar", "omit", "extra", "markdown")
)
def test_artifact_integrity_controls(tmp_path: Path, change: str) -> None:
    for name in FILES:
        (tmp_path / name).write_bytes((CORPUS / name).read_bytes())
    _integrity(tmp_path)
    if change == "canonical":
        p = tmp_path / "valid-vectors.json"
        p.write_bytes(p.read_bytes().rstrip(b"\n"))
    elif change == "sidecar":
        (tmp_path / "manifest.sha256").write_text("0" * 64 + "  manifest.json\n")
    elif change == "omit":
        (tmp_path / "composition-vectors.json").unlink()
    elif change == "extra":
        (tmp_path / "replay-vectors.json").write_text("{}\n")
    else:
        p = tmp_path / "contract.md"
        p.write_text(p.read_text() + "Observed true pattern.\n")
    with pytest.raises(
        ValueError,
        match="canonical artifact|sidecar mismatch|corpus file inventory|derived Markdown",
    ):
        _integrity(tmp_path)


@pytest.mark.parametrize("field", ("target", "operation", "recipe", "version"))
def test_unknown_dispatch_cannot_masquerade_as_model_rejection(
    monkeypatch: pytest.MonkeyPatch, field: str
) -> None:
    docs = _documents()
    _catalog(docs)
    if field == "version":
        docs["invalid-vectors"]["format"]["version"] = 999
    else:
        docs["invalid-vectors"]["vectors"][0][field] = "unknown"
    calls: list[tuple[Any, ...]] = []

    def forbidden(*args: Any, **kwargs: Any) -> Any:
        calls.append(args)
        raise AssertionError("model dispatch preceded metadata validation")

    monkeypatch.setattr(__name__ + "._call", forbidden)
    with pytest.raises(
        ValueError,
        match="unknown target|unknown operation|unknown recipe|unknown format",
    ):
        _run(docs)
    assert calls == []


def _recount(docs: dict[str, dict[str, Any]]) -> None:
    rows = [r for s in STEMS[1:] for r in docs[s]["vectors"]]
    docs["manifest"]["counts"] = {
        "files": {s: len(docs[s]["vectors"]) for s in STEMS[1:]},
        "vectors": len(rows),
        "accepted": sum(r["operation"] != "reject" for r in rows),
        "rejected": sum(r["operation"] == "reject" for r in rows),
    }


@pytest.mark.parametrize(
    "change", ("omitted_target", "duplicate", "substituted", "wrong_coverage_reference")
)
def test_coverage_controls_with_reconciled_counts(change: str) -> None:
    docs = _documents()
    _catalog(docs)
    if change == "omitted_target":
        removed = {
            r["id"]
            for s in STEMS[1:]
            for r in docs[s]["vectors"]
            if r["target"] == "FaultInvariantIdentity"
        }
        for s in STEMS[1:]:
            docs[s]["vectors"] = [
                r for r in docs[s]["vectors"] if r["id"] not in removed
            ]
        docs["manifest"]["obligations"]["invariant_identity"] = []
        docs["manifest"]["coverage"]["FaultInvariantIdentity"] = {
            "accepted": [],
            "rejected": [],
        }
    elif change == "duplicate":
        docs["valid-vectors"]["vectors"][1] = copy.deepcopy(
            docs["valid-vectors"]["vectors"][0]
        )
    elif change == "substituted":
        docs["valid-vectors"]["vectors"][0]["target"] = "FaultInvariantIdentity"
    else:
        docs["manifest"]["coverage"]["FaultPatternIdentity"]["accepted"][0] = (
            "valid.invariant_identity.python"
        )
    _recount(docs)
    with pytest.raises(
        ValueError,
        match="empty obligation|duplicate/invalid vector|wrong obligation target|wrong primary target coverage",
    ):
        _run(docs)


@pytest.mark.parametrize("change", ("golden", "error_location"))
def test_expected_results_are_real_oracles(change: str) -> None:
    docs = _documents()
    _catalog(docs)
    if change == "golden":
        docs["valid-vectors"]["vectors"][0]["expect"]["value"] = str(uuid.UUID(int=171))
    else:
        docs["invalid-vectors"]["vectors"][0]["expect"]["error"][0]["loc"] = [
            "not_the_owner"
        ]
    with pytest.raises(
        AssertionError, match="authored value mismatch|wrong error location/type"
    ):
        _run(docs)


@pytest.mark.parametrize(
    "change", ("observed_vector", "observed_manifest", "resolved_p00", "reassigned_p01")
)
def test_provenance_and_empirical_remainders_are_not_promoted(change: str) -> None:
    docs = _documents()
    _catalog(docs)
    if change == "observed_vector":
        docs["composition-vectors"]["vectors"][0]["provenance"] = "observed_evidence"
    elif change == "observed_manifest":
        docs["manifest"]["provenance"]["independent_observed_failures"] = 2
    elif change == "resolved_p00":
        docs["manifest"]["authority"]["subjects"][1]["remainder"]["state"] = "resolved"
    else:
        docs["manifest"]["authority"]["subjects"][2]["remainder"]["owner"] = "S1.P08"
    with pytest.raises(
        ValueError, match="synthetic provenance|preserved empirical disposition"
    ):
        _run(docs)


def test_changed_payload_fails_without_poisoning_a_fresh_run() -> None:
    pristine = _documents()
    original = copy.deepcopy(pristine)
    first = _run(pristine)
    altered = copy.deepcopy(pristine)
    altered["valid-vectors"]["vectors"][2]["input"]["text"] = (
        "Synthetic changed supplied input."
    )
    with pytest.raises(AssertionError, match="authored value mismatch"):
        _run(altered)
    assert pristine == original
    assert _run(_documents()) == first
