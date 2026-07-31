from __future__ import annotations

import copy
import hashlib
import json
import re
import shutil
import stat
import subprocess
from collections import Counter
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import NoReturn, cast

import pytest

type JSONValue = None | bool | int | str | list[JSONValue] | dict[str, JSONValue]
type JSONObject = dict[str, JSONValue]


ROOT = Path(__file__).resolve().parents[1]
CORPUS_ROOT = ROOT / "reference_corpus" / "pytest-4412"

ACQUISITION = (
    "reference_corpus/pytest-4412/acquisitions/"
    "run-0001-s04-v1-base-4c9cde74-head-690a63b9/acquisition.json"
)
ACQUISITION_SIDECAR = ACQUISITION.removesuffix(".json") + ".sha256"
DIFF = (
    "reference_corpus/pytest-4412/acquisitions/"
    "run-0001-s04-v1-base-4c9cde74-head-690a63b9/artifacts/"
    "base-to-head.diff"
)
HISTORICAL_LICENSE = str(Path(DIFF).with_name("LICENSE"))
CORRECTION = (
    "reference_corpus/pytest-4412/corrections/"
    "s04-c01-acquisition-closure/correction.json"
)
CORRECTION_SIDECAR = CORRECTION.removesuffix(".json") + ".sha256"
CASE = "reference_corpus/pytest-4412/case/case.json"
CASE_SIDECAR = CASE.removesuffix(".json") + ".sha256"
GAP_MATRIX = (
    "reference_corpus/pytest-4412/analysis/"
    "s06-current-contract-gap-matrix/gap-matrix.json"
)
GAP_MATRIX_SIDECAR = GAP_MATRIX.removesuffix(".json") + ".sha256"
GAP_MATRIX_MARKDOWN = GAP_MATRIX.removesuffix(".json") + ".md"
S07_DECISION = (
    "reference_corpus/pytest-4412/decisions/"
    "s07-identity-revision-provenance/decision.json"
)
S07_SIDECAR = S07_DECISION.removesuffix(".json") + ".sha256"
S07_MARKDOWN = S07_DECISION.removesuffix(".json") + ".md"
S08_DECISION = (
    "reference_corpus/pytest-4412/decisions/"
    "s08-snapshot-boundary-compatibility/decision.json"
)
S08_SIDECAR = S08_DECISION.removesuffix(".json") + ".sha256"
S08_MARKDOWN = S08_DECISION.removesuffix(".json") + ".md"


@dataclass(frozen=True)
class LockedFile:
    path: str
    sha256: str
    byte_length: int


LOCKED_FILES = (
    LockedFile(
        ACQUISITION,
        "1c29093bf1537e9b824a18df1848b71a8da014f544bc9f385707eb0e000a1318",
        61_283,
    ),
    LockedFile(
        ACQUISITION_SIDECAR,
        "dbb4cf7cb2c0b95377a0a11892b854a46c43dd6c443e7e808e3a57fe31981824",
        83,
    ),
    LockedFile(
        DIFF,
        "dca87a4df1edb2d1acb3fc821724483ee874c2feba6525b2c21e79cb3e8f7312",
        1_640,
    ),
    LockedFile(
        HISTORICAL_LICENSE,
        "a1ebce15afc7b5cf98c7c6de512d1959d4bf61db8c6bf2f111286d483b40a997",
        1_096,
    ),
    LockedFile(
        CORRECTION,
        "44491ee512d2c2022110b83967fb6fa86d13045bc8404ea490d7a08b7aef24a2",
        60_832,
    ),
    LockedFile(
        CORRECTION_SIDECAR,
        "c585d66ea3d7edf6465ba292c7f08af9a15972ba082f4b0e07a8ffc3f6d61977",
        82,
    ),
    LockedFile(
        CASE,
        "fc1439a8f9766bdf55b95e9d63f3bf19db44da1724dfb7cd2e889771384b9efa",
        85_370,
    ),
    LockedFile(
        CASE_SIDECAR,
        "477a4dab64ee7f1353272229bf68c4ac076a4d6b8dbbbbd2fe4fab56c7506dd2",
        76,
    ),
    LockedFile(
        GAP_MATRIX,
        "55dacf5193aedc5493ac369dd0e3fb74a0f59f0c1f88bab1b625a2e4f4ff5f13",
        233_061,
    ),
    LockedFile(
        GAP_MATRIX_SIDECAR,
        "4811ef0c2aaf706361aa79d9300a4343f314ee7437cd6bd28b0f8a49712eff50",
        82,
    ),
    LockedFile(
        GAP_MATRIX_MARKDOWN,
        "6a569af7f9b1c691fc397e356d365664dcc14cbebe6ae589bd4501e23ac1893a",
        8_752,
    ),
    LockedFile(
        S07_DECISION,
        "60ecb66565525cb21a924508794635072ae50e935d4791d9d91da5b6399ce866",
        85_012,
    ),
    LockedFile(
        S07_SIDECAR,
        "a95d8f29afda95d1361d33a680694eb6618e9c5acaaf52afee5fe6678f34a891",
        80,
    ),
    LockedFile(
        S07_MARKDOWN,
        "75c9c84f2069a5782241b9c28cb4e5c39f1368ccdabbc11e4bed9a204869e857",
        9_553,
    ),
    LockedFile(
        S08_DECISION,
        "f788116f3b9ea470c370a56e55eb6f37e05be200f285ac9f2572c641215f5f40",
        46_533,
    ),
    LockedFile(
        S08_SIDECAR,
        "7a87fd638e0ea08dc4e592373c754cdd9c385e54d1197978fcf90eb843057982",
        80,
    ),
    LockedFile(
        S08_MARKDOWN,
        "6a1a28b7a250f80206da9ff43900a912e3fd201dc7ffa09255660897e193e9e0",
        5_679,
    ),
)

LOCK_BY_PATH = {locked.path: locked for locked in LOCKED_FILES}
PRIMARY_JSON = (
    ("s04-acquisition", ACQUISITION),
    ("s04-c01-correction", CORRECTION),
    ("s05-case", CASE),
    ("s06-gap-matrix", GAP_MATRIX),
    ("s07-decision", S07_DECISION),
    ("s08-decision", S08_DECISION),
)
SIDECAR_PAIRS = (
    (ACQUISITION, ACQUISITION_SIDECAR),
    (CORRECTION, CORRECTION_SIDECAR),
    (CASE, CASE_SIDECAR),
    (GAP_MATRIX, GAP_MATRIX_SIDECAR),
    (S07_DECISION, S07_SIDECAR),
    (S08_DECISION, S08_SIDECAR),
)
PRIMARY_PATH_BY_LAYER = dict(PRIMARY_JSON)
EXPECTED_LAYER_FILES = {
    "s04-acquisition": {
        ACQUISITION,
        ACQUISITION_SIDECAR,
        DIFF,
        HISTORICAL_LICENSE,
    },
    "s04-c01-correction": {CORRECTION, CORRECTION_SIDECAR},
    "s05-case": {CASE, CASE_SIDECAR},
    "s06-gap-matrix": {
        GAP_MATRIX,
        GAP_MATRIX_SIDECAR,
        GAP_MATRIX_MARKDOWN,
    },
    "s07-decision": {S07_DECISION, S07_SIDECAR, S07_MARKDOWN},
    "s08-decision": {S08_DECISION, S08_SIDECAR, S08_MARKDOWN},
}

EXPECTED_CLASSIFICATIONS = {
    "observed": 20,
    "deterministically_derived": 19,
    "reviewed_derived_interpretation": 9,
    "hypothesis": 1,
    "unknown": 2,
    "unsupported": 2,
}
EXPECTED_FIELD_STATES = {
    "present",
    "observed_null",
    "missing",
    "unavailable",
    "inaccessible",
    "deleted",
    "unknown",
    "unsupported",
    "conflict",
}
EXPECTED_COMPATIBILITY_STATUSES = {
    "native",
    "losslessly_mappable",
    "partially_mappable",
    "not_mappable",
    "unsupported_version",
    "conflict",
}


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _json_object(value: JSONValue, label: str) -> JSONObject:
    assert isinstance(value, dict), f"{label} must be a JSON object"
    return value


def _json_array(value: JSONValue, label: str) -> list[JSONValue]:
    assert isinstance(value, list), f"{label} must be a JSON array"
    return value


def _string(value: JSONValue, label: str) -> str:
    assert isinstance(value, str), f"{label} must be a string"
    return value


def _integer(value: JSONValue, label: str) -> int:
    assert isinstance(value, int) and not isinstance(value, bool), (
        f"{label} must be an integer"
    )
    return value


def _boolean(value: JSONValue, label: str) -> bool:
    assert isinstance(value, bool), f"{label} must be a boolean"
    return value


def _reject_non_integer_number(value: str) -> NoReturn:
    raise ValueError(f"non-integer JSON number is forbidden: {value}")


def _load_canonical_json(source: bytes | Path) -> JSONValue:
    data = source.read_bytes() if isinstance(source, Path) else source
    if data.startswith(b"\xef\xbb\xbf"):
        raise ValueError("UTF-8 BOM is forbidden")
    if b"\r" in data:
        raise ValueError("carriage returns are forbidden")
    if not data.endswith(b"\n") or data.endswith(b"\n\n"):
        raise ValueError("exactly one terminal LF is required")

    text = data[:-1].decode("utf-8")
    value = cast(
        JSONValue,
        json.loads(
            text,
            parse_float=_reject_non_integer_number,
            parse_constant=_reject_non_integer_number,
        ),
    )
    canonical = (
        json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        + b"\n"
    )
    if data != canonical:
        raise ValueError("JSON bytes do not match the declared canonical form")
    repeated = (
        json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        + b"\n"
    )
    assert repeated == canonical, "canonical serialization is not deterministic"
    return value


def _validate_expected_bytes(data: bytes, expected: LockedFile) -> None:
    assert len(data) == expected.byte_length, f"byte length drift: {expected.path}"
    assert _sha256(data) == expected.sha256, f"SHA-256 drift: {expected.path}"


def _git_blob_sha1(data: bytes) -> str:
    return hashlib.sha1(
        b"blob " + str(len(data)).encode("ascii") + b"\0" + data,
        usedforsecurity=False,
    ).hexdigest()


def _validate_lock_record(record: JSONObject, label: str) -> str:
    path = _string(record["path"], f"{label} path")
    digest = _string(record["sha256"], f"{label} digest")
    assert path in LOCK_BY_PATH, f"{label} uses an unlocked path: {path}"
    locked = LOCK_BY_PATH[path]
    assert digest == locked.sha256, f"{label} records the wrong digest for {path}"
    data = (ROOT / path).read_bytes()
    _validate_expected_bytes(data, locked)
    if "byte_length" in record:
        assert _integer(record["byte_length"], f"{label} byte length") == len(data)
    if "mode" in record:
        assert record["mode"] == "100644", f"{label} records a non-regular mode"
    if "git_blob_sha1" in record:
        assert record["git_blob_sha1"] == _git_blob_sha1(data), (
            f"{label} records the wrong Git blob identity"
        )
    return path


def _validate_path_digest(path: str, digest: str, label: str) -> None:
    assert path in LOCK_BY_PATH, f"{label} uses an unlocked path: {path}"
    locked = LOCK_BY_PATH[path]
    assert digest == locked.sha256, f"{label} records the wrong digest for {path}"
    _validate_expected_bytes((ROOT / path).read_bytes(), locked)


def _validate_sidecar(
    json_bytes: bytes,
    sidecar_bytes: bytes,
    json_name: str,
    expected_json_sha256: str,
    expected_sidecar_sha256: str,
) -> None:
    assert _sha256(json_bytes) == expected_json_sha256, (
        f"independent JSON lock drift: {json_name}"
    )
    assert _sha256(sidecar_bytes) == expected_sidecar_sha256, (
        f"independent sidecar lock drift: {json_name}"
    )
    match = re.fullmatch(rb"([0-9a-f]{64})  ([^/\r\n]+)\n", sidecar_bytes)
    assert match is not None, f"invalid sidecar syntax: {json_name}"
    assert match.group(2).decode("ascii") == json_name, (
        f"wrong sidecar basename: {json_name}"
    )
    assert match.group(1).decode("ascii") == _sha256(json_bytes), (
        f"sidecar digest mismatch: {json_name}"
    )


def _walk_objects(value: JSONValue) -> Iterator[JSONObject]:
    if isinstance(value, dict):
        yield value
        for nested in value.values():
            yield from _walk_objects(nested)
    elif isinstance(value, list):
        for nested in value:
            yield from _walk_objects(nested)


def _decode_pointer_token(token: str) -> str:
    decoded: list[str] = []
    index = 0
    while index < len(token):
        character = token[index]
        if character != "~":
            decoded.append(character)
            index += 1
            continue
        if index + 1 >= len(token) or token[index + 1] not in {"0", "1"}:
            raise ValueError(f"invalid RFC 6901 escape in token: {token!r}")
        decoded.append("~" if token[index + 1] == "0" else "/")
        index += 2
    return "".join(decoded)


def _resolve_json_pointer(document: JSONValue, pointer: str) -> JSONValue:
    if pointer == "":
        return document
    if not pointer.startswith("/"):
        raise ValueError(f"JSON Pointer must start with '/': {pointer!r}")

    current = document
    for raw_token in pointer[1:].split("/"):
        token = _decode_pointer_token(raw_token)
        if isinstance(current, dict):
            if token not in current:
                raise KeyError(
                    f"object key not found for pointer {pointer!r}: {token!r}"
                )
            current = current[token]
        elif isinstance(current, list):
            if not re.fullmatch(r"0|[1-9][0-9]*", token):
                raise ValueError(
                    f"invalid array index in pointer {pointer!r}: {token!r}"
                )
            index = int(token)
            if index >= len(current):
                raise IndexError(f"array index out of range in pointer {pointer!r}")
            current = current[index]
        else:
            raise TypeError(f"pointer descends through a scalar: {pointer!r}")
    return current


def _load_documents() -> dict[str, JSONValue]:
    return {
        layer_id: _load_canonical_json(ROOT / path) for layer_id, path in PRIMARY_JSON
    }


def _evidence_references(value: JSONValue) -> list[tuple[str, str]]:
    references: list[tuple[str, str]] = []
    for item in _walk_objects(value):
        if "json_pointer" not in item:
            continue
        assert "layer_id" in item, "evidence pointers require a layer_id"
        references.append(
            (
                _string(item["layer_id"], "evidence layer_id"),
                _string(item["json_pointer"], "evidence json_pointer"),
            )
        )
    return references


def _validate_evidence_references(documents: dict[str, JSONValue]) -> int:
    count = 0
    for source_layer in ("s05-case", "s06-gap-matrix", "s07-decision", "s08-decision"):
        for target_layer, pointer in _evidence_references(documents[source_layer]):
            assert target_layer in documents, (
                f"{source_layer} references unknown evidence layer {target_layer!r}"
            )
            _resolve_json_pointer(documents[target_layer], pointer)
            count += 1

    equivalent_shapes = (
        ("s08-decision", "s06_pointer", "s06-gap-matrix"),
        ("s08-decision", "s07_pointer", "s07-decision"),
    )
    for source_layer, field_name, target_layer in equivalent_shapes:
        for item in _walk_objects(documents[source_layer]):
            if field_name not in item:
                continue
            pointer = _string(
                item[field_name], f"{source_layer} documented {field_name}"
            )
            _resolve_json_pointer(documents[target_layer], pointer)
            count += 1
    assert count > 0, "published evidence-pointer inventory is unexpectedly empty"
    return count


def _validate_non_pointer_references(
    documents: dict[str, JSONValue],
) -> tuple[int, int]:
    document_count = 0
    for item in _walk_objects(documents["s05-case"]):
        if "document_path" not in item and "section" not in item:
            continue
        assert "document_path" in item and "section" in item
        path = ROOT / _string(item["document_path"], "document reference path")
        section = _string(item["section"], "document reference section")
        assert path.is_file(), f"missing referenced document: {path}"
        headings = {
            line.lstrip("#").strip()
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.startswith("#")
        }
        assert section in headings, f"missing referenced section {section!r} in {path}"
        document_count += 1

    s07 = _json_object(documents["s07-decision"], "S07 decision")
    s07_locks = _json_object(s07["source_locks"], "S07 source locks")
    s07_lock_records = [
        _json_object(value, "S07 source lock")
        for value in _json_array(
            s07_locks["legacy_model_source_and_test_blobs"],
            "S07 legacy source locks",
        )
    ]
    s07_by_id = {
        _string(record["lock_id"], "S07 source lock ID"): record
        for record in s07_lock_records
    }
    symbol_count = 0
    for item in _walk_objects(s07):
        if "source_lock_id" not in item and "symbol" not in item:
            continue
        assert "source_lock_id" in item and "symbol" in item
        lock_id = _string(item["source_lock_id"], "S07 source lock reference")
        symbol = _string(item["symbol"], "S07 source symbol")
        assert lock_id in s07_by_id, f"unknown S07 source lock: {lock_id}"
        path = ROOT / _string(s07_by_id[lock_id]["path"], "S07 source path")
        assert symbol in path.read_text(encoding="utf-8"), (
            f"S07 source symbol {symbol!r} not found in {path}"
        )
        symbol_count += 1

    s08 = _json_object(documents["s08-decision"], "S08 decision")
    s08_locks = _json_object(s08["source_locks"], "S08 source locks")
    s08_lock_records = [
        _json_object(value, "S08 source lock")
        for value in _json_array(
            s08_locks["legacy_model_source_and_test_blobs"],
            "S08 legacy source locks",
        )
    ]
    for item in _walk_objects(s08):
        if "source_lock_role" not in item and "symbol" not in item:
            continue
        assert "source_lock_role" in item and "symbol" in item
        role = _string(item["source_lock_role"], "S08 source-lock role")
        symbol = _string(item["symbol"], "S08 source symbol")
        candidates = [
            record for record in s08_lock_records if record.get("role") == role
        ]
        if "path" in item:
            reference_path = _string(item["path"], "S08 source reference path")
            candidates = [
                record for record in candidates if record.get("path") == reference_path
            ]
        assert len(candidates) == 1, f"unresolved S08 source-lock role {role!r}"
        path = ROOT / _string(candidates[0]["path"], "S08 source path")
        assert symbol in path.read_text(encoding="utf-8"), (
            f"S08 source symbol {symbol!r} not found in {path}"
        )
        symbol_count += 1
    return document_count, symbol_count


def _primary_file_from_layer(layer: JSONObject, label: str) -> JSONObject:
    if "path" in layer and "sha256" in layer:
        return layer
    files = _json_array(layer["files"], f"{label}.files")
    primary = [
        _json_object(item, f"{label}.files item")
        for item in files
        if _json_object(item, f"{label}.files item").get("role") == "primary_json"
    ]
    assert len(primary) == 1, f"{label} must lock exactly one primary JSON file"
    return primary[0]


def _source_lock_records(
    layer_id: str, documents: dict[str, JSONValue]
) -> list[tuple[str, str, str]]:
    document = _json_object(documents[layer_id], layer_id)
    if layer_id == "s04-acquisition":
        return []
    if layer_id == "s04-c01-correction":
        target = _json_object(document["target_acquisition"], "target_acquisition")
        record = _json_object(
            target["acquisition_record"], "target_acquisition.acquisition_record"
        )
        target_paths = {_validate_lock_record(record, "target acquisition")}
        sidecar = _json_object(target["sidecar"], "target acquisition sidecar")
        sidecar_path = _string(sidecar["path"], "target sidecar path")
        _validate_path_digest(
            sidecar_path,
            _string(sidecar["file_sha256"], "target sidecar digest"),
            "target acquisition sidecar",
        )
        target_paths.add(sidecar_path)
        for value in _json_array(
            target["retained_artifacts"], "target retained artifacts"
        ):
            target_paths.add(
                _validate_lock_record(
                    _json_object(value, "target retained artifact"),
                    "target retained artifact",
                )
            )
        assert target_paths == EXPECTED_LAYER_FILES["s04-acquisition"]
        return [
            (
                "s04-acquisition",
                _string(record["path"], "target acquisition path"),
                _string(record["sha256"], "target acquisition digest"),
            )
        ]
    if layer_id == "s05-case":
        evidence_layers = _json_object(document["evidence_layers"], "evidence_layers")
        evidence_records = _json_array(
            evidence_layers["records"], "evidence_layers.records"
        )
        results: list[tuple[str, str, str]] = []
        for value in evidence_records:
            record = _json_object(value, "evidence layer record")
            upstream_id = _string(record["id"], "evidence layer id")
            primary_path = _validate_lock_record(record, "evidence layer record")
            assert primary_path == PRIMARY_PATH_BY_LAYER[upstream_id]
            sidecar = _json_object(record["sidecar"], "evidence layer sidecar")
            sidecar_path = _string(sidecar["path"], "evidence sidecar path")
            _validate_path_digest(
                sidecar_path,
                _string(sidecar["file_sha256"], "evidence sidecar digest"),
                "evidence layer sidecar",
            )
            assert {primary_path, sidecar_path} == {
                PRIMARY_PATH_BY_LAYER[upstream_id],
                next(
                    path
                    for path in EXPECTED_LAYER_FILES[upstream_id]
                    if path.endswith(".sha256")
                ),
            }
            results.append(
                (
                    upstream_id,
                    primary_path,
                    _string(record["sha256"], "evidence layer digest"),
                )
            )
        return results

    source_locks = _json_object(document["source_locks"], f"{layer_id}.source_locks")
    layers = _json_array(
        source_locks["immutable_evidence_layers"],
        f"{layer_id}.source_locks.immutable_evidence_layers",
    )
    result_records: list[tuple[str, str, str]] = []
    for value in layers:
        layer = _json_object(value, f"{layer_id} source layer")
        upstream_id = _string(layer["layer_id"], f"{layer_id} upstream layer id")
        primary = _primary_file_from_layer(layer, layer_id)
        primary_path = _validate_lock_record(primary, f"{layer_id} upstream primary")
        assert primary_path == PRIMARY_PATH_BY_LAYER[upstream_id], (
            f"{layer_id} binds {upstream_id} to the wrong primary path"
        )
        if "files" in layer:
            locked_paths = {
                _validate_lock_record(
                    _json_object(file_value, f"{layer_id} upstream file"),
                    f"{layer_id} upstream file",
                )
                for file_value in _json_array(
                    layer["files"], f"{layer_id} upstream files"
                )
            }
            assert locked_paths == EXPECTED_LAYER_FILES[upstream_id]
        else:
            sidecar_path = _string(
                layer["sidecar_path"], f"{layer_id} upstream sidecar path"
            )
            _validate_path_digest(
                sidecar_path,
                _string(
                    layer["sidecar_file_sha256"],
                    f"{layer_id} upstream sidecar digest",
                ),
                f"{layer_id} upstream sidecar",
            )
            assert {primary_path, sidecar_path} == {
                PRIMARY_PATH_BY_LAYER[upstream_id],
                next(
                    path
                    for path in EXPECTED_LAYER_FILES[upstream_id]
                    if path.endswith(".sha256")
                ),
            }
        result_records.append(
            (
                upstream_id,
                primary_path,
                _string(primary["sha256"], f"{layer_id} upstream digest"),
            )
        )
    return result_records


def _validate_source_lock_graph(documents: dict[str, JSONValue]) -> None:
    expected_upstreams: dict[str, set[str]] = {
        "s04-acquisition": set(),
        "s04-c01-correction": {"s04-acquisition"},
        "s05-case": {"s04-acquisition", "s04-c01-correction"},
        "s06-gap-matrix": {
            "s04-acquisition",
            "s04-c01-correction",
            "s05-case",
        },
        "s07-decision": {
            "s04-acquisition",
            "s04-c01-correction",
            "s05-case",
            "s06-gap-matrix",
        },
        "s08-decision": {
            "s04-acquisition",
            "s04-c01-correction",
            "s05-case",
            "s06-gap-matrix",
            "s07-decision",
        },
    }
    graph: dict[str, set[str]] = {}
    for layer_id in documents:
        records = _source_lock_records(layer_id, documents)
        upstream_ids = {record[0] for record in records}
        assert upstream_ids == expected_upstreams[layer_id], (
            f"unexpected source-lock set for {layer_id}: {upstream_ids}"
        )
        assert layer_id not in upstream_ids, f"self-reference in {layer_id}"
        graph[layer_id] = upstream_ids
        for upstream_id, path, digest in records:
            assert upstream_id in documents, (
                f"{layer_id} references missing layer {upstream_id}"
            )
            assert path == PRIMARY_PATH_BY_LAYER[upstream_id], (
                f"{layer_id} binds {upstream_id} to the wrong primary path"
            )
            assert path in LOCK_BY_PATH, f"{layer_id} uses mutable/unlocked path {path}"
            locked = LOCK_BY_PATH[path]
            assert digest == locked.sha256, (
                f"{layer_id} records wrong digest for {upstream_id}"
            )
            _validate_expected_bytes((ROOT / path).read_bytes(), locked)

    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node: str) -> None:
        if node in visiting:
            raise AssertionError(f"source-lock cycle reaches {node}")
        if node in visited:
            return
        visiting.add(node)
        for upstream in graph[node]:
            visit(upstream)
        visiting.remove(node)
        visited.add(node)

    for layer_id in graph:
        visit(layer_id)

    correction = _json_object(documents["s04-c01-correction"], "correction")
    boundary = _json_object(
        correction["immutability_boundary"], "immutability_boundary"
    )
    assert boundary["relationship"] == "external_append_only_addendum"
    assert boundary["existing_files_modifiable"] is False
    assert boundary["in_place_correction_permitted"] is False
    forbidden = {
        _string(value, "forbidden operation")
        for value in _json_array(
            boundary["forbidden_operations"], "forbidden_operations"
        )
    }
    assert "replacement" in forbidden


def _validate_s05(case_value: JSONValue) -> None:
    case = _json_object(case_value, "S05 case")
    entities = [
        _json_object(value, "S05 entity")
        for value in _json_array(case["entities"], "S05 entities")
    ]
    relationships = _json_object(case["relationships"], "S05 relationships")
    records = [
        _json_object(value, "S05 relationship")
        for value in _json_array(relationships["records"], "relationship records")
    ]
    entity_ids = [_string(entity["id"], "entity id") for entity in entities]
    relationship_ids = [
        _string(relationship["id"], "relationship id") for relationship in records
    ]
    assert len(entity_ids) == 33
    assert len(set(entity_ids)) == 33, "duplicate S05 entity ID"
    assert len(relationship_ids) == 53
    assert len(set(relationship_ids)) == 53, "duplicate S05 relationship ID"

    entity_id_set = set(entity_ids)
    for relationship in records:
        relationship_id = _string(relationship["id"], "relationship id")
        subject = _string(relationship["subject_entity_id"], "relationship subject")
        assert subject in entity_id_set, f"dangling subject in {relationship_id}"
        targets = {
            _string(value, f"target of {relationship_id}")
            for value in _json_array(
                relationship["object_entity_ids"], "relationship targets"
            )
        }
        assert targets <= entity_id_set, f"dangling target in {relationship_id}"
        classification = _string(
            relationship["classification"], f"classification of {relationship_id}"
        )
        if classification == "deterministically_derived":
            assert _json_array(
                relationship["inputs"], f"inputs of {relationship_id}"
            ), f"deterministic relationship lacks inputs: {relationship_id}"

    classifications = Counter(
        _string(record["classification"], "relationship classification")
        for record in records
    )
    assert dict(classifications) == EXPECTED_CLASSIFICATIONS
    assert len(_json_array(case["known_gaps"], "known gaps")) == 26


def _contains_json_string(value: JSONValue, expected: str) -> bool:
    if isinstance(value, str):
        return value == expected
    if isinstance(value, list):
        return any(_contains_json_string(item, expected) for item in value)
    if isinstance(value, dict):
        return any(_contains_json_string(item, expected) for item in value.values())
    return False


def _validate_chronology_and_negative_evidence(
    case_value: JSONValue,
    documents: dict[str, JSONValue] | None = None,
) -> None:
    case = _json_object(case_value, "S05 case")
    chronology = _json_object(case["chronology"], "chronology")
    items = [
        _json_object(value, "chronology item")
        for value in _json_array(chronology["items"], "chronology items")
    ]
    assert len(items) == 29
    chronology_ids = [_string(item["id"], "chronology ID") for item in items]
    assert len(set(chronology_ids)) == 29, "duplicate chronology ID"
    entity_ids = {
        _string(_json_object(value, "entity")["id"], "entity ID")
        for value in _json_array(case["entities"], "entities")
    }
    scope_pointers = {
        "issue_comments": "/observations/issue/comments/items/{index}",
        "issue_timeline": "/observations/issue/timeline/items/{index}",
        "pr_reviews": "/observations/pr/reviews/items/{index}",
        "pr_timeline": "/observations/pr/timeline/items/{index}",
        "pr_top_level_comments": "/observations/pr/top_level_comments/items/{index}",
        "topology_commits": "/observations/topology/commits/{index}",
    }

    observed_timestamps: list[str] = []
    source_indexes: dict[str, list[int]] = {}
    for item in items:
        source_entity_id = _string(item["source_entity_id"], "chronology entity ID")
        assert source_entity_id in entity_ids, (
            f"chronology item references unknown entity {source_entity_id}"
        )
        provider_timestamp = _json_object(
            item["provider_timestamp"], "chronology provider timestamp"
        )
        state = _string(provider_timestamp["field_state"], "timestamp field state")
        timestamp: str | None = None
        if state == "present":
            timestamp = _string(provider_timestamp["value"], "provider timestamp")
            observed_timestamps.append(timestamp)
        else:
            assert provider_timestamp.get("value") is None, (
                "missing timestamps must not be fabricated"
            )
        if "source_order_scope" in item:
            scope = _string(item["source_order_scope"], "source order scope")
            assert scope in scope_pointers, f"unknown chronology source scope {scope}"
            source_index = _integer(item["source_index"], "source index")
            source_indexes.setdefault(scope, []).append(source_index)
            if documents is not None:
                expected_pointer = scope_pointers[scope].format(index=source_index)
                matching_values = [
                    _resolve_json_pointer(documents[target_layer], pointer)
                    for target_layer, pointer in _evidence_references(item)
                    if target_layer == "s04-acquisition"
                    and (
                        pointer == expected_pointer
                        or pointer.startswith(expected_pointer + "/")
                    )
                ]
                assert matching_values, (
                    f"chronology source index does not match evidence: {item['id']}"
                )
                if state == "present":
                    assert timestamp is not None
                    assert any(
                        _contains_json_string(value, timestamp)
                        for value in matching_values
                    ), f"chronology timestamp does not match source: {item['id']}"
    assert observed_timestamps == sorted(observed_timestamps)
    for scope, indexes in source_indexes.items():
        assert indexes == sorted(indexes), f"source order drift in {scope}"

    negative = _json_object(case["negative_evidence"], "negative evidence")
    entries = [
        _json_object(value, "negative-evidence entry")
        for value in _json_array(negative["entries"], "negative-evidence entries")
    ]
    expected_order = [
        ("issue-comment:439722704", "apparent_failure_report"),
        ("issue-comment:439729234", "independent_success_report"),
        ("issue-comment:439731167", "stale_cache_hypothesis"),
        ("issue-comment:439732047", "resolution_report"),
    ]
    actual_order = [
        (
            _string(entry["comment_entity_id"], "negative-evidence comment"),
            _string(entry["role"], "negative-evidence role"),
        )
        for entry in entries
    ]
    assert actual_order == expected_order
    assert [
        _integer(entry["ordinal"], "negative-evidence ordinal") for entry in entries
    ] == [1, 2, 3, 4]
    assert {
        _string(entry["role_classification"], "negative-evidence classification")
        for entry in entries
    } == {"reviewed_derived_interpretation"}
    assert negative["stale_cache_explanation_state"] == (
        "hypothesis_unverified_causation"
    )
    assert _boolean(negative["causation_verified"], "causation_verified") is False

    relationships = _json_object(case["relationships"], "relationships")
    records = [
        _json_object(value, "relationship")
        for value in _json_array(relationships["records"], "relationship records")
    ]
    hypotheses = [
        relationship
        for relationship in records
        if relationship.get("id") == "hypothesis:stale-cache-explanation"
    ]
    assert len(hypotheses) == 1
    hypothesis = hypotheses[0]
    assert hypothesis["classification"] == "hypothesis"
    details = _json_object(hypothesis["details"], "stale-cache details")
    assert details["causation_verified"] is False

    invariant = _json_object(case["transferable_invariant"], "transferable invariant")
    assert invariant["exact_text"] == (
        "Transformation or instrumentation must preserve evaluation count and "
        "execution order for side-effecting expressions."
    )
    assert invariant["universal_cross_repository_pattern"] is False


def _validate_s06(matrix_value: JSONValue, case_value: JSONValue) -> None:
    matrix = _json_object(matrix_value, "S06 matrix")
    case = _json_object(case_value, "S05 case")
    case_entities = {
        _string(_json_object(value, "entity")["id"], "entity id")
        for value in _json_array(case["entities"], "entities")
    }
    relationships = _json_object(case["relationships"], "relationships")
    case_relationships = {
        _string(record["id"], "relationship id"): _string(
            record["classification"], "relationship classification"
        )
        for value in _json_array(relationships["records"], "relationship records")
        for record in [_json_object(value, "relationship")]
    }

    entity_coverage = [
        _json_object(value, "entity coverage row")
        for value in _json_array(matrix["entity_coverage"], "entity coverage")
    ]
    relationship_coverage = [
        _json_object(value, "relationship coverage row")
        for value in _json_array(
            matrix["relationship_coverage"], "relationship coverage"
        )
    ]
    covered_entities = [
        _string(row["case_entity_id"], "covered entity ID") for row in entity_coverage
    ]
    covered_relationships = [
        _string(row["relationship_id"], "covered relationship ID")
        for row in relationship_coverage
    ]
    assert len(covered_entities) == 33
    assert len(set(covered_entities)) == 33
    assert set(covered_entities) == case_entities
    assert len(covered_relationships) == 53
    assert len(set(covered_relationships)) == 53
    assert set(covered_relationships) == set(case_relationships)
    for row in relationship_coverage:
        relationship_id = _string(row["relationship_id"], "relationship ID")
        assert row["relationship_classification"] == case_relationships[relationship_id]

    concepts = [
        _json_object(value, "concept row")
        for value in _json_array(matrix["concept_matrix"], "concept matrix")
    ]
    gaps = [
        _json_object(value, "gap row")
        for value in _json_array(matrix["gap_register"], "gap register")
    ]
    decisions = [
        _json_object(value, "owner decision")
        for value in _json_array(
            matrix["owner_decision_register"], "owner decision register"
        )
    ]
    assert len(concepts) == 81
    assert len(gaps) == 31
    assert len(decisions) == 11
    assert len({_string(row["concept_id"], "concept ID") for row in concepts}) == 81
    assert len({_string(row["gap_id"], "gap ID") for row in gaps}) == 31
    assert (
        len({_string(row["decision_id"], "owner decision ID") for row in decisions})
        == 11
    )

    allowed_support = {
        "representable",
        "partially_representable",
        "not_representable",
        "intentionally_deferred",
        "unsupported_by_current_evidence",
    }
    for label, rows in (
        ("entity coverage", entity_coverage),
        ("relationship coverage", relationship_coverage),
        ("concept matrix", concepts),
    ):
        for row in rows:
            assert _string(row["support_status"], f"{label} support status") in (
                allowed_support
            )

    allowed_owners = {
        "S1.P00.S07",
        "S1.P00.S08",
        "S1.P00.S09",
        "S1.P00.S10",
        "intentionally_unowned_until_more_evidence",
        "later_s1_phase",
    }
    for gap in gaps:
        assert _string(gap["immediate_owner"], "gap immediate owner") in allowed_owners
    assert {
        _string(decision["decision_state"], "owner decision state")
        for decision in decisions
    } == {"owner_decision_required"}

    blockers = {
        (
            _string(gap["immediate_owner"], "blocking gap owner"),
            _string(gap["gap_id"], "blocking gap ID"),
        )
        for gap in gaps
        if gap.get("severity") == "blocking"
    }
    assert blockers == {
        (
            "S1.P00.S07",
            "gap:s05-known:source-locator-byte-range-ambiguity",
        ),
        (
            "S1.P00.S07",
            "gap:s05-known:source-locator-discussion-surface-gap",
        ),
        (
            "S1.P00.S08",
            "gap:s05-known:artifact-snapshot-media-and-envelope-gap",
        ),
        (
            "S1.P00.S08",
            "gap:s05-known:current-internal-models-cannot-represent-full-case",
        ),
    }


def _validate_s07(decision_value: JSONValue) -> None:
    decision = _json_object(decision_value, "S07 decision")
    reconciliation = _json_object(
        decision["s06_routed_decision_reconciliation"], "S07 S06 reconciliation"
    )
    routed_decisions = [
        _json_object(value, "S07 routed owner decision")
        for value in _json_array(
            reconciliation["owner_decisions"], "S07 routed owner decisions"
        )
    ]
    assert len(routed_decisions) == 5
    assert {
        _string(record["s06_decision_id"], "S07 routed S06 decision ID")
        for record in routed_decisions
    } == {
        "decision:s07:canonical-identity-tuple",
        "decision:s07:actor-reviewer-missing-states",
        "decision:s07:revision-identity",
        "decision:s07:topology-ref-and-locator",
        "decision:s07:provenance-authority-chain",
    }

    terminology = _json_object(decision["terminology"], "S07 terminology")
    terms = [
        _json_object(value, "S07 term")
        for value in _json_array(terminology["terms"], "S07 terms")
    ]
    assert len(terms) == 27
    assert len({_string(term["term_id"], "S07 term ID") for term in terms}) == 27

    field_states = _json_object(decision["field_state_decisions"], "S07 field states")
    field_state_records = _json_array(
        field_states["controlled_vocabulary"], "field-state vocabulary"
    )
    assert len(field_state_records) == 9
    controlled_states = {
        _string(_json_object(value, "field state")["controlled_name"], "field state")
        for value in field_state_records
    }
    assert controlled_states == EXPECTED_FIELD_STATES

    provenance = _json_object(
        decision["provenance_layer_decisions"], "S07 provenance layers"
    )
    provenance_layers = [
        _json_object(value, "provenance layer")
        for value in _json_array(provenance["layers"], "provenance layers")
    ]
    assert len(provenance_layers) == 14
    assert (
        len(
            {
                _string(layer["layer_id"], "provenance layer ID")
                for layer in provenance_layers
            }
        )
        == 14
    )

    repository = _json_object(
        decision["repository_identity_decisions"], "repository identity decisions"
    )
    projection = _json_object(repository["case_projection"], "repository projection")
    assert projection["provider"] == "github"
    assert projection["provider_stable_repository_id"] == "37489525"
    assert projection["observed_alias"] == "pytest-dev/pytest"

    authorities = _json_object(decision["authority_decisions"], "authority decisions")
    provider = _json_object(authorities["provider_key"], "provider key")
    navigation = _json_object(
        authorities["navigation_authority"], "navigation authority"
    )
    retrieval = _json_object(authorities["retrieval_authority"], "retrieval authority")
    assert {
        _string(provider["value"], "provider value"),
        _string(navigation["value"], "navigation authority value"),
        _string(retrieval["value"], "retrieval authority value"),
    } == {
        "github",
        "github.com",
        "api.github.com",
    }
    assert authorities["separation_rule"] == (
        "provider_key_navigation_authority_retrieval_authority_api_version_media_"
        "and_HTTP_controls_are_distinct"
    )

    source_objects = _json_object(
        decision["source_object_identity_decisions"], "source-object identity"
    )
    identifier_roles = _json_object(
        source_objects["repository_scoped_and_global_id_roles"], "identifier roles"
    )
    assert set(identifier_roles) == {
        "GraphQL_node_ID",
        "global_REST_ID",
        "repository_scoped_number",
    }

    revision = _json_object(
        decision["revision_and_git_object_decisions"], "revision decisions"
    )
    assert set(
        _string(value, "Git object kind")
        for value in _json_array(
            revision["git_object_kind_distinction"], "Git object kinds"
        )
    ) == {"commit", "tree", "blob"}
    assert set(
        _string(value, "Git identity requirement")
        for value in _json_array(
            revision["git_object_identity_requirements"],
            "Git identity requirements",
        )
    ) == {"object_kind", "hash_algorithm", "full_digest"}
    assert revision["deleted_ref_rule"] == (
        "deleted_ref_does_not_invalidate_the_immutable_commit_it_formerly_identified"
    )
    assert "observation_time" in {
        _string(value, "ref observation requirement")
        for value in _json_array(
            revision["ref_observation_requirements"], "ref observation requirements"
        )
    }

    legacy = _json_object(
        decision["legacy_compatibility_decisions"], "legacy compatibility"
    )
    locator = _json_object(legacy["source_locator_boundary"], "legacy locator")
    assert locator["object_id_semantics"] == (
        "unresolved_legacy_ambiguity_between_repository_scoped_number_and_global_"
        "provider_ID"
    )
    assert locator["new_consumer_may_depend_on_ambiguous_object_id"] is False
    format_record = _json_object(decision["format"], "S07 format")
    warning = _string(
        format_record["non_production_schema_warning"], "S07 production warning"
    )
    assert warning.startswith("not_a_production_schema")


def _validate_s08(decision_value: JSONValue) -> None:
    decision = _json_object(decision_value, "S08 decision")
    reconciliation = _json_object(
        decision["s06_routed_decision_reconciliation"], "S08 S06 reconciliation"
    )
    routed_decisions = [
        _json_object(value, "S08 routed owner decision")
        for value in _json_array(
            reconciliation["routed_owner_decisions"], "S08 routed owner decisions"
        )
    ]
    assert len(routed_decisions) == 4
    assert {
        _string(record["s06_decision_id"], "S08 routed S06 decision ID")
        for record in routed_decisions
    } == {
        "decision:s08:artifact-snapshot-boundary",
        "decision:s08:representation-media-and-digest",
        "decision:s08:completeness-and-omission-carrier",
        "decision:s08:reader-writer-migration-compatibility",
    }

    strategy = _json_object(
        decision["selected_compatibility_strategy"], "selected strategy"
    )
    assert strategy["selected"] == "preserve_v1_behind_outer_wrapper"
    assert strategy["in_place_evolution_disposition"] == "rejected_for_now"
    assert strategy["immediate_replacement_disposition"] == "rejected_for_now"

    s07_handoff = _json_object(
        decision["s07_handoff_reconciliation"], "S08 S07 handoff"
    )
    option_records = _json_array(
        s07_handoff["option_dispositions"], "compatibility options"
    )
    assert len(option_records) == 3
    option_dispositions = {
        _string(option["option"], "compatibility option"): _string(
            option["disposition"], "compatibility-option disposition"
        )
        for value in option_records
        for option in [_json_object(value, "compatibility option")]
    }
    assert option_dispositions == {
        "preserve_v1_behind_outer_wrapper": "selected",
        "explicitly_version_and_evolve": "rejected_for_now",
        "replace_through_compatibility_adapter": "rejected_for_now",
    }

    statuses = _json_object(
        decision["compatibility_statuses"], "compatibility statuses"
    )
    status_records = _json_array(statuses["statuses"], "compatibility status records")
    assert len(status_records) == 6
    controlled = {
        _string(
            _json_object(value, "compatibility status")["controlled_name"], "status"
        )
        for value in status_records
    }
    assert controlled == EXPECTED_COMPATIBILITY_STATUSES

    boundary = _json_object(
        decision["representation_and_artifact_boundary"], "artifact boundary"
    )
    invariants = {
        _string(value, "artifact-boundary invariant")
        for value in _json_array(boundary["invariants"], "artifact-boundary invariants")
    }
    assert (
        "representation_observation_and_retained_exact_artifact_are_related_not_"
        "interchangeable" in invariants
    )

    mappings = _json_object(
        decision["compatibility_mappings"], "compatibility mappings"
    )
    case_examples = {
        _string(example["case_id"], "mapping case ID"): _string(
            example["outcome"], "mapping outcome"
        )
        for value in _json_array(mappings["case_examples"], "mapping examples")
        for example in [_json_object(value, "mapping example")]
    }
    assert case_examples["example:retained-base-to-head-diff"] == "not_mappable"
    assert case_examples["example:retained-historical-license"] == "not_mappable"

    versioning = _json_object(decision["versioning_decisions"], "versioning decisions")
    assert versioning["global_FaultAtlas_schema_version"] is False
    serialization = _json_object(
        decision["serialization_and_canonicalization_decisions"],
        "serialization decisions",
    )
    assert serialization["legacy_declared_durable_canonical"] is False

    migration = _json_object(
        decision["migration_correction_supersession_decisions"],
        "migration decisions",
    )
    operations = {
        _string(_json_object(value, "operation record")["operation"], "operation")
        for value in _json_array(migration["comparison"], "operation comparison")
    }
    assert operations == {"migration", "correction", "supersession"}
    assert migration["correction_is_migration"] is False

    legacy = _json_object(
        decision["legacy_compatibility_commitment"], "legacy commitment"
    )
    backward = _json_object(legacy["backward_compatibility"], "backward compatibility")
    supported = {
        _string(value, "supported legacy behavior")
        for value in _json_array(
            backward["supported_through_S1_P00"], "supported legacy behavior"
        )
    }
    assert {
        "current_ArtifactSnapshot_behavior",
        "existing_authoritative_tests",
        "schema_version_1_semantic_round_trip",
    } <= supported

    handoff = _json_object(decision["downstream_handoff"], "downstream handoff")
    p03 = [
        record
        for value in _json_array(handoff["handoffs"], "handoffs")
        for record in [_json_object(value, "handoff")]
        if record.get("target") == "S1.P03"
    ]
    assert len(p03) == 1
    assert p03[0]["status"] == "not_started"


_PRIVACY_PATTERNS = {
    "absolute Linux home path": re.compile(rb"/(?:home|Users)/[A-Za-z0-9._-]+/"),
    "Windows local path": re.compile(rb"(?i)(?:^|[\"'\s])[a-z]:[\\/]"),
    "email address": re.compile(rb"(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b"),
    "GitHub credential": re.compile(rb"\bgh[pousr]_[A-Za-z0-9_]{20,}\b"),
    "service credential": re.compile(rb"\b(?:sk|xox[baprs])-[A-Za-z0-9-]{16,}\b"),
    "authorization header": re.compile(
        rb"(?i)authorization\s*:\s*(?:bearer|token|basic)\s+\S+"
    ),
    "private key header": re.compile(rb"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    "temporary audit root": re.compile(rb"/tmp/faultatlas(?:-|/)", re.IGNORECASE),
}


def _privacy_findings(data: bytes) -> list[str]:
    return [name for name, pattern in _PRIVACY_PATTERNS.items() if pattern.search(data)]


@pytest.mark.parametrize("locked", LOCKED_FILES, ids=lambda item: item.path)
def test_static_corpus_file_lock(locked: LockedFile) -> None:
    path = ROOT / locked.path
    assert path.exists(), f"missing locked file: {locked.path}"
    assert path.is_file(), f"locked path is not a file: {locked.path}"
    assert not path.is_symlink(), f"locked path is a symlink: {locked.path}"
    _validate_expected_bytes(path.read_bytes(), locked)
    assert stat.S_IMODE(path.stat().st_mode) & 0o111 == 0, (
        f"locked file is executable: {locked.path}"
    )

    if shutil.which("git") is not None and (ROOT / ".git").exists():
        result = subprocess.run(
            ["git", "ls-files", "--stage", "--", locked.path],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        assert result.stdout.startswith("100644 "), (
            f"unexpected tracked mode for {locked.path}: {result.stdout!r}"
        )


def test_corpus_has_no_mutable_latest_pointer() -> None:
    assert CORPUS_ROOT.is_dir()
    assert not [path for path in CORPUS_ROOT.rglob("*") if path.name == "latest"]


@pytest.mark.parametrize(
    ("layer_id", "path"),
    PRIMARY_JSON,
    ids=[layer_id for layer_id, _ in PRIMARY_JSON],
)
def test_primary_json_is_canonical(layer_id: str, path: str) -> None:
    document = _json_object(_load_canonical_json(ROOT / path), layer_id)
    format_record = _json_object(document["format"], f"{layer_id}.format")
    declaration = format_record["canonicalization"]
    if isinstance(declaration, str):
        name = declaration
    else:
        name = _string(
            _json_object(declaration, f"{layer_id}.canonicalization")["name"],
            "canonicalization name",
        )
    assert name == "json-sort-keys-compact-utf8-lf-v1"


@pytest.mark.parametrize(
    ("json_path", "sidecar_path"),
    SIDECAR_PAIRS,
    ids=[Path(json_path).parent.name for json_path, _ in SIDECAR_PAIRS],
)
def test_digest_sidecar_is_exact(json_path: str, sidecar_path: str) -> None:
    _validate_sidecar(
        (ROOT / json_path).read_bytes(),
        (ROOT / sidecar_path).read_bytes(),
        Path(json_path).name,
        LOCK_BY_PATH[json_path].sha256,
        LOCK_BY_PATH[sidecar_path].sha256,
    )


def test_exact_artifacts_and_diff_locators() -> None:
    diff_bytes = (ROOT / DIFF).read_bytes()
    license_bytes = (ROOT / HISTORICAL_LICENSE).read_bytes()
    _validate_expected_bytes(diff_bytes, LOCK_BY_PATH[DIFF])
    _validate_expected_bytes(license_bytes, LOCK_BY_PATH[HISTORICAL_LICENSE])
    git_blob = _git_blob_sha1(license_bytes)
    assert git_blob == "629df45ac405532c107eb233217bc2ac1ad70c88"

    acquisition = _json_object(_load_canonical_json(ROOT / ACQUISITION), "acquisition")
    assert acquisition["run"] != "complete"
    run = _json_object(acquisition["run"], "acquisition run")
    assert run["status"] == "complete"
    assert "status" not in acquisition

    artifacts = [
        _json_object(value, "acquisition artifact")
        for value in _json_array(acquisition["artifacts"], "acquisition artifacts")
    ]
    actual_artifacts = {
        "artifacts/base-to-head.diff": diff_bytes,
        "artifacts/LICENSE": license_bytes,
    }
    expected_digest_scopes = {
        "artifacts/base-to-head.diff": "github-compare-diff-http-entity-body",
        "artifacts/LICENSE": "git-blob-content",
    }
    assert {_string(item["path"], "artifact path") for item in artifacts} == set(
        actual_artifacts
    )
    for artifact in artifacts:
        path = _string(artifact["path"], "artifact path")
        data = actual_artifacts[path]
        assert artifact["retention"] == "exact_unmodified_bytes"
        assert artifact["transformations"] == []
        assert artifact["digest_scope"] == expected_digest_scopes[path]
        assert _integer(artifact["byte_length"], "artifact length") == len(data)
        assert artifact["sha256"] == _sha256(data)
        if path == "artifacts/LICENSE":
            assert artifact["blob_sha1"] == git_blob

    expected_locators = [
        (165, 77, "3a9ef726e8631334ac0ee92db96577569a58f2c972fb2b248b2f33a8833952a6"),
        (439, 394, "7395019171a710ce827d5ed71020afbdd790f8e1c158756388c08977d17bdecd"),
        (1018, 622, "47640375cbfeb436cfc73aeeb1926d77b05d969fc684289c17b271ca85facfc3"),
    ]
    locators = [
        _json_object(value, "diff locator")
        for value in _json_array(acquisition["locators"], "diff locators")
    ]
    assert len(locators) == 3
    for locator, (offset, length, digest) in zip(
        locators, expected_locators, strict=True
    ):
        assert locator["offset"] == offset
        assert locator["length"] == length
        assert locator["parent_artifact_sha256"] == LOCK_BY_PATH[DIFF].sha256
        assert locator["digest_scope"] == "artifact-byte-slice"
        assert _sha256(diff_bytes[offset : offset + length]) == digest
        assert locator["sha256"] == digest


def test_cross_layer_source_lock_dag() -> None:
    _validate_source_lock_graph(_load_documents())


def test_all_published_evidence_pointers_resolve() -> None:
    documents = _load_documents()
    count = _validate_evidence_references(documents)
    assert count == 696
    assert _validate_non_pointer_references(documents) == (37, 12)


def test_s05_entity_relationship_and_classification_integrity() -> None:
    documents = _load_documents()
    _validate_s05(documents["s05-case"])
    _validate_evidence_references(documents)


def test_s05_chronology_and_negative_evidence() -> None:
    documents = _load_documents()
    _validate_chronology_and_negative_evidence(documents["s05-case"], documents)


def test_s06_coverage_routing_and_markdown_lock() -> None:
    documents = _load_documents()
    _validate_s06(documents["s06-gap-matrix"], documents["s05-case"])
    markdown = (ROOT / GAP_MATRIX_MARKDOWN).read_text(encoding="utf-8")
    assert LOCK_BY_PATH[GAP_MATRIX].sha256 in markdown
    assert "exactly 33 S05 entities, 53 S05 relationships, and 81" in markdown


def test_s07_identity_field_state_provenance_and_markdown_lock() -> None:
    _validate_s07(_load_documents()["s07-decision"])
    markdown = (ROOT / S07_MARKDOWN).read_text(encoding="utf-8")
    assert LOCK_BY_PATH[S07_DECISION].sha256 in markdown
    assert "covers five S06-routed owner decisions" in markdown


def test_s08_compatibility_boundary_and_markdown_lock() -> None:
    _validate_s08(_load_documents()["s08-decision"])
    markdown = (ROOT / S08_MARKDOWN).read_text(encoding="utf-8")
    assert LOCK_BY_PATH[S08_DECISION].sha256 in markdown
    assert "preserve_v1_behind_outer_wrapper" in markdown


def test_corpus_privacy_and_retention_boundary() -> None:
    for locked in LOCKED_FILES:
        findings = _privacy_findings((ROOT / locked.path).read_bytes())
        assert not findings, f"privacy findings in {locked.path}: {findings}"

    approved_public_data = (
        b"reference_corpus/pytest-4412/case/case.json\n"
        b"/repos/pytest-dev/pytest/issues/4412\n"
        b"public_login=asottile\n"
        b"https://github.com/pytest-dev/pytest/issues/4412\n"
        b"690a63b9218f72662cd3a67c6c200b758c88ce12\n"
    )
    assert not _privacy_findings(approved_public_data)


def test_changed_primary_json_byte_fails_independent_lock() -> None:
    original = (ROOT / ACQUISITION).read_bytes()
    changed = original.replace(b'"artifacts"', b'"artifactz"', 1)
    assert changed != original
    with pytest.raises(AssertionError, match="SHA-256 drift"):
        _validate_expected_bytes(changed, LOCK_BY_PATH[ACQUISITION])


def test_coordinated_json_and_sidecar_reseal_fails_independent_oracle() -> None:
    original = (ROOT / ACQUISITION).read_bytes()
    document = _json_object(_load_canonical_json(original), "acquisition")
    changed_document = copy.deepcopy(document)
    run = _json_object(changed_document["run"], "run")
    run["status"] = "corrupted"
    changed = (
        json.dumps(
            changed_document,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        + b"\n"
    )
    resealed = f"{_sha256(changed)}  acquisition.json\n".encode("ascii")
    with pytest.raises(AssertionError, match="independent JSON lock drift"):
        _validate_sidecar(
            changed,
            resealed,
            "acquisition.json",
            LOCK_BY_PATH[ACQUISITION].sha256,
            _sha256(resealed),
        )


@pytest.mark.parametrize(
    "mutation",
    ["uppercase", "one-space", "three-spaces", "wrong-basename"],
)
def test_invalid_sidecar_mutations_fail(mutation: str) -> None:
    json_bytes = (ROOT / CASE).read_bytes()
    digest = _sha256(json_bytes)
    if mutation == "uppercase":
        sidecar = f"{digest.upper()}  case.json\n".encode("ascii")
    elif mutation == "one-space":
        sidecar = f"{digest} case.json\n".encode("ascii")
    elif mutation == "three-spaces":
        sidecar = f"{digest}   case.json\n".encode("ascii")
    else:
        sidecar = f"{digest}  wrong.json\n".encode("ascii")
    with pytest.raises(AssertionError):
        _validate_sidecar(
            json_bytes,
            sidecar,
            "case.json",
            LOCK_BY_PATH[CASE].sha256,
            _sha256(sidecar),
        )


@pytest.mark.parametrize(
    "mutated",
    [
        b'{"a":1}',
        b'{"a":1}\n\n',
        b'{"a":1}\r\n',
        b'\xef\xbb\xbf{"a":1}\n',
        b'{ "a": 1 }\n',
        b'{"b":2,"a":1}\n',
        b'{"a":1.5}\n',
        b'{"a":NaN}\n',
    ],
    ids=[
        "missing-terminal-lf",
        "duplicate-terminal-lf",
        "crlf",
        "utf8-bom",
        "noncanonical-whitespace",
        "unsorted-object",
        "float",
        "nan",
    ],
)
def test_noncanonical_json_mutations_fail(mutated: bytes) -> None:
    with pytest.raises((ValueError, json.JSONDecodeError)):
        _load_canonical_json(mutated)


@pytest.mark.parametrize("pointer", ["/missing", "/a/~2invalid"])
def test_invalid_or_unresolved_json_pointer_fails(pointer: str) -> None:
    with pytest.raises((KeyError, ValueError)):
        _resolve_json_pointer({"a": {"~key/part": 1}}, pointer)


def test_json_pointer_rfc6901_escapes_resolve() -> None:
    assert _resolve_json_pointer({"a": {"~key/part": 1}}, "/a/~0key~1part") == 1


@pytest.mark.parametrize(
    "mutation", ["wrong-digest", "self-reference", "swapped-layer-bindings"]
)
def test_broken_source_lock_mutations_fail(mutation: str) -> None:
    documents = copy.deepcopy(_load_documents())
    s06 = _json_object(documents["s06-gap-matrix"], "S06")
    source_locks = _json_object(s06["source_locks"], "S06 source locks")
    layers = _json_array(
        source_locks["immutable_evidence_layers"], "S06 immutable layers"
    )
    first_layer = _json_object(layers[0], "S06 first source layer")
    primary = _primary_file_from_layer(first_layer, "S06 first source layer")
    if mutation == "wrong-digest":
        primary["sha256"] = "0" * 64
    elif mutation == "self-reference":
        first_layer["layer_id"] = "s06-gap-matrix"
        primary["path"] = GAP_MATRIX
        primary["sha256"] = LOCK_BY_PATH[GAP_MATRIX].sha256
    else:
        second_layer = _json_object(layers[1], "S06 second source layer")
        first_layer["layer_id"], second_layer["layer_id"] = (
            second_layer["layer_id"],
            first_layer["layer_id"],
        )
    with pytest.raises(AssertionError):
        _validate_source_lock_graph(documents)


def test_nonprimary_source_lock_digest_mutation_fails() -> None:
    documents = copy.deepcopy(_load_documents())
    s07 = _json_object(documents["s07-decision"], "S07")
    source_locks = _json_object(s07["source_locks"], "S07 source locks")
    layers = _json_array(
        source_locks["immutable_evidence_layers"], "S07 immutable layers"
    )
    first_layer = _json_object(layers[0], "S07 first source layer")
    files = _json_array(first_layer["files"], "S07 first source-layer files")
    sidecar = _json_object(files[1], "S07 source sidecar")
    sidecar["sha256"] = "0" * 64
    with pytest.raises(AssertionError):
        _validate_source_lock_graph(documents)


@pytest.mark.parametrize(
    "mutation",
    [
        "missing-entity",
        "duplicate-entity",
        "missing-relationship",
        "duplicate-relationship",
        "dangling-endpoint",
    ],
)
def test_s05_integrity_mutations_fail(mutation: str) -> None:
    case = copy.deepcopy(_load_documents()["s05-case"])
    case_object = _json_object(case, "case")
    entities = _json_array(case_object["entities"], "entities")
    relationships = _json_object(case_object["relationships"], "relationships")
    records = _json_array(relationships["records"], "relationship records")
    if mutation == "missing-entity":
        entities.pop()
    elif mutation == "duplicate-entity":
        entities[-1] = copy.deepcopy(entities[0])
    elif mutation == "missing-relationship":
        records.pop()
    elif mutation == "duplicate-relationship":
        records[-1] = copy.deepcopy(records[0])
    else:
        first = _json_object(records[0], "first relationship")
        first["subject_entity_id"] = "entity:does-not-exist"
    with pytest.raises(AssertionError):
        _validate_s05(case)


@pytest.mark.parametrize(
    "mutation",
    [
        "reordered-negative-evidence",
        "stale-cache-observed",
        "causation-verified",
        "duplicate-chronology-id",
        "dangling-chronology-entity",
        "shifted-chronology-source-index",
    ],
)
def test_s05_chronology_and_causation_mutations_fail(mutation: str) -> None:
    documents = _load_documents()
    case = copy.deepcopy(documents["s05-case"])
    case_object = _json_object(case, "case")
    negative = _json_object(case_object["negative_evidence"], "negative evidence")
    if mutation == "reordered-negative-evidence":
        entries = _json_array(negative["entries"], "negative entries")
        entries[0], entries[1] = entries[1], entries[0]
    elif mutation == "causation-verified":
        negative["causation_verified"] = True
    elif mutation == "stale-cache-observed":
        relationships = _json_object(case_object["relationships"], "relationships")
        records = _json_array(relationships["records"], "relationship records")
        stale_cache = next(
            _json_object(value, "stale-cache relationship")
            for value in records
            if _json_object(value, "relationship").get("id")
            == "hypothesis:stale-cache-explanation"
        )
        stale_cache["classification"] = "observed"
    else:
        chronology = _json_object(case_object["chronology"], "chronology")
        items = _json_array(chronology["items"], "chronology items")
        first = _json_object(items[0], "first chronology item")
        if mutation == "duplicate-chronology-id":
            _json_object(items[-1], "last chronology item")["id"] = first["id"]
        elif mutation == "dangling-chronology-entity":
            first["source_entity_id"] = "entity:does-not-exist"
        else:
            issue_comments = [
                _json_object(value, "issue-comment chronology item")
                for value in items
                if _json_object(value, "chronology item").get("source_order_scope")
                == "issue_comments"
            ]
            issue_comments[-1]["source_index"] = 8
    with pytest.raises(AssertionError):
        _validate_chronology_and_negative_evidence(case, documents)


@pytest.mark.parametrize(
    "mutation", ["missing-entity-coverage", "duplicate-relationship-coverage"]
)
def test_s06_coverage_mutations_fail(mutation: str) -> None:
    documents = _load_documents()
    matrix = copy.deepcopy(documents["s06-gap-matrix"])
    matrix_object = _json_object(matrix, "matrix")
    if mutation == "missing-entity-coverage":
        _json_array(matrix_object["entity_coverage"], "entity coverage").pop()
    else:
        rows = _json_array(
            matrix_object["relationship_coverage"], "relationship coverage"
        )
        rows[-1] = copy.deepcopy(rows[0])
    with pytest.raises(AssertionError):
        _validate_s06(matrix, documents["s05-case"])


@pytest.mark.parametrize("mutation", ["removed", "duplicated", "duplicate-routed"])
def test_s07_field_state_mutation_fails(mutation: str) -> None:
    decision = copy.deepcopy(_load_documents()["s07-decision"])
    decision_object = _json_object(decision, "S07")
    field_states = _json_object(
        decision_object["field_state_decisions"], "field states"
    )
    if mutation == "duplicate-routed":
        reconciliation = _json_object(
            decision_object["s06_routed_decision_reconciliation"],
            "S07 reconciliation",
        )
        routed = _json_array(reconciliation["owner_decisions"], "S07 routed")
        routed[-1] = copy.deepcopy(routed[0])
    else:
        records = _json_array(field_states["controlled_vocabulary"], "field vocabulary")
        if mutation == "removed":
            records.pop()
        else:
            records.append(copy.deepcopy(records[0]))
    with pytest.raises(AssertionError):
        _validate_s07(decision)


@pytest.mark.parametrize(
    "mutation",
    [
        "in-place-strategy",
        "missing-partially-mappable",
        "duplicate-compatibility-status",
        "renamed-rejected-option",
        "duplicate-routed-decision",
    ],
)
def test_s08_compatibility_mutations_fail(mutation: str) -> None:
    decision = copy.deepcopy(_load_documents()["s08-decision"])
    decision_object = _json_object(decision, "S08")
    if mutation == "in-place-strategy":
        strategy = _json_object(
            decision_object["selected_compatibility_strategy"], "strategy"
        )
        strategy["selected"] = "explicitly_version_and_evolve"
    elif mutation in {"missing-partially-mappable", "duplicate-compatibility-status"}:
        statuses = _json_object(decision_object["compatibility_statuses"], "statuses")
        records = _json_array(statuses["statuses"], "status records")
        if mutation == "missing-partially-mappable":
            records[:] = [
                value
                for value in records
                if _json_object(value, "status").get("controlled_name")
                != "partially_mappable"
            ]
        else:
            records.append(copy.deepcopy(records[0]))
    elif mutation == "renamed-rejected-option":
        reconciliation = _json_object(
            decision_object["s07_handoff_reconciliation"], "S07 handoff"
        )
        options = _json_array(
            reconciliation["option_dispositions"], "compatibility options"
        )
        _json_object(options[1], "rejected option")["option"] = "renamed"
    else:
        reconciliation = _json_object(
            decision_object["s06_routed_decision_reconciliation"],
            "S08 reconciliation",
        )
        routed = _json_array(
            reconciliation["routed_owner_decisions"], "S08 routed decisions"
        )
        routed[-1] = copy.deepcopy(routed[0])
    with pytest.raises(AssertionError):
        _validate_s08(decision)


@pytest.mark.parametrize(
    ("payload", "expected_finding"),
    [
        (b'"/home/alice/private.json"', "absolute Linux home path"),
        (b'"C:\\Users\\Alice\\secret.json"', "Windows local path"),
        (b'"alice@example.com"', "email address"),
        (b'"ghp_abcdefghijklmnopqrstuvwxyz1234"', "GitHub credential"),
        (b'"Authorization: Bearer not-a-real-token"', "authorization header"),
        (b'"-----BEGIN PRIVATE KEY-----"', "private key header"),
        (b'"/tmp/faultatlas-audit/source.json"', "temporary audit root"),
    ],
)
def test_privacy_mutations_are_detected(payload: bytes, expected_finding: str) -> None:
    assert expected_finding in _privacy_findings(payload)
