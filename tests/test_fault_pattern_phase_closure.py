"""Finite bounded P07 closure assurance; live lifecycle and execution stay with owners."""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any, TypedDict, cast

import pytest
from _repository_contract import P07_SURFACE

ROOT = Path(__file__).resolve().parents[1]
CLOSURE = (
    ROOT / "reference_corpus/contracts/pattern-invariant/closures/s1-p07-phase-closure"
)
BASELINE = "21ada4fcc8fc4c23b0049e3df642573de7067407"
BASE_TREE = "1077df46bb135479bcf5a2f25541f6686d2fd886"
CLOSURE_SHA = "5197b34ec97289d963d69d38bfc52ae640f2ad473df80d672eed3463c121366b"
CLOSURE_LENGTH = 41207
P01_ID = "deferred:p01:p07-pattern-generality"
P00_ID = "gap:s05-known:cross-repository-pattern-and-transfer-not-established"
P01_CONSEQUENCE = "S1.P07 cannot publish a complete contract for p07 pattern generality until this item is resolved."
PRODUCT_PRS = (87, 88, 89, 90, 91, 93, 94, 95)
ANCESTRY_PRS = (87, 88, 89, 90, 91, 92, 93, 94, 95)


class _SourcePin(TypedDict):
    byte_length: int
    path: str
    sha256: str


# Historical pins independently captured from actual source bytes, Git objects,
# provider run metadata and checkout log lines. No Git history is required in CI.
SOURCE_PINS: dict[str, _SourcePin] = {
    "p00": {
        "byte_length": 102190,
        "path": "reference_corpus/pytest-4412/closures/s1-p00-phase-closure/closure.json",
        "sha256": "8c02d79c4a5a1d52b9fc2a3718e1b47888da6195588e62ab927388dbe972189e",
    },
    "p01": {
        "byte_length": 112606,
        "path": "reference_corpus/contracts/identity/closures/s1-p01-phase-closure/closure.json",
        "sha256": "2c1bfb9d3d596711066796ef83999d49b6846e65315a301eead7fa8fb5ac4642",
    },
    "p03": {
        "byte_length": 127921,
        "path": "reference_corpus/contracts/evidence-envelope/closures/s1-p03-phase-closure/closure.json",
        "sha256": "21a24e7ab572456f22d3aca572e10e76be69529770b96a131f3d4f624d0b481b",
    },
    "p06": {
        "byte_length": 62413,
        "path": "reference_corpus/contracts/fault-instance/closures/s1-p06-phase-closure/closure.json",
        "sha256": "0341e6320ffc7279d1083bc9bb1aca4896a7022b886456192db037628e7a10c0",
    },
    "s07": {
        "byte_length": 22947,
        "path": "reference_corpus/contracts/pattern-invariant/decisions/s07-deferred-subject-disposition-readiness/decision.json",
        "sha256": "8937e1a896d8d4a78f01ce82878d478318b853532f90d9b93192f22d976ae237",
    },
    "s08:composition-vectors.json": {
        "byte_length": 100145,
        "path": "reference_corpus/contracts/pattern-invariant/v1/composition-vectors.json",
        "sha256": "ed737148c3b182a1e27b4a35186ca525be557a05c132c29a13be3ed0c73e6b4d",
    },
    "s08:composition-vectors.sha256": {
        "byte_length": 91,
        "path": "reference_corpus/contracts/pattern-invariant/v1/composition-vectors.sha256",
        "sha256": "6146a391d26b3abfd7da13d6d9a19e90f76a3a48b7521d88469e43e802c7c74c",
    },
    "s08:contract.md": {
        "byte_length": 11814,
        "path": "reference_corpus/contracts/pattern-invariant/v1/contract.md",
        "sha256": "19f89799062c4be6d3bad205f4423e06da21fda4f2ed9220fc9a9465b746a5e5",
    },
    "s08:invalid-vectors.json": {
        "byte_length": 9943,
        "path": "reference_corpus/contracts/pattern-invariant/v1/invalid-vectors.json",
        "sha256": "d102e7ee656f2c2934eea630982d745d96c764c9594268ee40d1c71c99c8b2fa",
    },
    "s08:invalid-vectors.sha256": {
        "byte_length": 87,
        "path": "reference_corpus/contracts/pattern-invariant/v1/invalid-vectors.sha256",
        "sha256": "fdc6d480d8f212bf0edf5b0898f720d5b477784d5dd101443a0aaa54103a2070",
    },
    "s08:manifest.json": {
        "byte_length": 10529,
        "path": "reference_corpus/contracts/pattern-invariant/v1/manifest.json",
        "sha256": "9f1539ea47158b72466b17c1e774e9173f2a8def3f1e3237659504b8c6e7dc8b",
    },
    "s08:manifest.sha256": {
        "byte_length": 80,
        "path": "reference_corpus/contracts/pattern-invariant/v1/manifest.sha256",
        "sha256": "6afce77d707d0233467ee9ba845b402a2b614bf08e3f01837ff2d2de7b8ccc6b",
    },
    "s08:valid-vectors.json": {
        "byte_length": 24689,
        "path": "reference_corpus/contracts/pattern-invariant/v1/valid-vectors.json",
        "sha256": "1063f1af440bcd1f569025153a3205d260e2ef98473a22e3cc9d0ec2ee13492c",
    },
    "s08:valid-vectors.sha256": {
        "byte_length": 85,
        "path": "reference_corpus/contracts/pattern-invariant/v1/valid-vectors.sha256",
        "sha256": "01a5999178cfce27baefd736db8ae634aa0ce83fb0c1e4c6dbd9fa7f15bab35d",
    },
}

PUBLICATION_PINS = {
    87: {
        "base": "84f4311e92bcfea1e9314e01d4eae8de03694dfd",
        "head": "4dfefb30ea7a8033186e384981d3961f729f0de5",
        "main_job": 103477222467,
        "main_log_sha256": "275ffdc7f19c792bf5488431189d1fb24b4687be4290bc8e737bd1c0e486ab71",
        "main_run": 34665772074,
        "pr_checkout": "14ddda06e835b46b630dbf78b55b6f4929dc7c1c",
        "pr_job": 103476318068,
        "pr_log_sha256": "446bfef310d8d359ba481e2778496ca4a4d15cd7888df444ea3d960ff03de3ae",
        "pr_run": 34665460980,
        "squash": "f332d3b9d504265794d0cb0e64a6645a96032793",
        "tree": "a1df52daa2cdfdade04858dbdacd2a7149c9dff1",
    },
    88: {
        "base": "f332d3b9d504265794d0cb0e64a6645a96032793",
        "head": "f86111e5d6ea3e76f15520d4b29bc5081f2bcbc8",
        "main_job": 103496806076,
        "main_log_sha256": "f0b59737167b66badca5a0b27772f1292c526951f038f54b16eb181d33e39e1b",
        "main_run": 34672643046,
        "pr_checkout": "709d3d720d373e3683b63134095808da08ca4e95",
        "pr_job": 103495656958,
        "pr_log_sha256": "152730bc5c5d6ab3da63779e34fa5cf0f19f0bd15cad4c764e4de36b9ee856c2",
        "pr_run": 34672239622,
        "squash": "d8f3cc74d131c9e7e3479f46b43336ed2bda0f50",
        "tree": "af2a29b833b7f209c200fc35335da4394b42ac61",
    },
    89: {
        "base": "d8f3cc74d131c9e7e3479f46b43336ed2bda0f50",
        "head": "d7ee4c0b6947eb2794588d815cf81b3438e6bd2b",
        "main_job": 103511563177,
        "main_log_sha256": "024f645f0282a5aa62d3675e75c715ce96fa9f69941d5c00dafcb770162d9ddd",
        "main_run": 34678124824,
        "pr_checkout": "5d5bfa5ad82ee248f4b7e89ea0a1d2f773b55df6",
        "pr_job": 103509913751,
        "pr_log_sha256": "2f63062fd08845b5b7f78e76a9fbaa39bf3496c8c2226a1eaed44b69b775b8e1",
        "pr_run": 34677513924,
        "squash": "ce598cfc3a87a21239e470c9aabfc8db83a7727f",
        "tree": "1f78f1979e8970a269f2aa12c5b50dfc6665f852",
    },
    90: {
        "base": "ce598cfc3a87a21239e470c9aabfc8db83a7727f",
        "head": "b0096e8d7e35b721b7a48571d512a7ac0e0c86ea",
        "main_job": 103525947963,
        "main_log_sha256": "781dac5761bb2dd6e32681fbc5a43c0affdfa4f06051b762ead38b423eb3a85e",
        "main_run": 34683370198,
        "pr_checkout": "cdc1c4d811c5430970b9e2cc622c78014d877652",
        "pr_job": 103524347157,
        "pr_log_sha256": "e043c1dbdf8a3cbc4a018829b0752513eed9be1a7911a0b64f1ed3852fcfaca1",
        "pr_run": 34682770199,
        "squash": "c19822507e3e7c05575fc32cdc846e5c2518e749",
        "tree": "0a3b4c37fe149b137a7413c9839bb489811d0906",
    },
    91: {
        "base": "c19822507e3e7c05575fc32cdc846e5c2518e749",
        "head": "cb333327c2dfca1057614b65ae33da54217c1d17",
        "main_job": 103533919897,
        "main_log_sha256": "0760465e8cc822fe76e1368ebcf8e46039801847ce76db169ada00b75aa25d18",
        "main_run": 34686364883,
        "pr_checkout": "a8f551234c8380d9fcfd921ba87ececc82317818",
        "pr_job": 103532883714,
        "pr_log_sha256": "48b64d3008413b91388105f1c395476fcea299048d2b3edc41eb01c4e1af46be",
        "pr_run": 34685962344,
        "squash": "ff0908012bf34631342133e4e5a5713ba1fe234d",
        "tree": "f7bf0518f97403f39d90d9fc1bd2dbdc57b0564b",
    },
    92: {
        "base": "ff0908012bf34631342133e4e5a5713ba1fe234d",
        "head": "51f0f4c7b6b67f4d3d3dfc7038f603391e43a606",
        "main_job": 103662150457,
        "main_log_sha256": "ec296a57f44e1e1ce9507bf24716463bf0c9df76bd73ded4dc54146a55299733",
        "main_run": 34734064970,
        "pr_checkout": "1c9cfd6140be70e0ac976dbea020e6c6f84edc2c",
        "pr_job": 103660778722,
        "pr_log_sha256": "b2729968a16da4a85786f88c266f5268c14cbfb91adff2bbf3a76d2f17cd2412",
        "pr_run": 34733561112,
        "squash": "000da52cd4e503831a6705ae709ab3d34a479fbf",
        "tree": "3b5593770ad7434d297b80338a81383a00dda8e3",
    },
    93: {
        "base": "000da52cd4e503831a6705ae709ab3d34a479fbf",
        "head": "caf0d569ff273e0e737e788bd56b67a441196832",
        "main_job": 103677253133,
        "main_log_sha256": "c239b1778ec1888f16bcdae92e015f10e2eb0464b721a21dd751c9236c7578ca",
        "main_run": 34739720978,
        "pr_checkout": "e7abbc9b510da938015b4b108f8a1893f94db1fe",
        "pr_job": 103676277202,
        "pr_log_sha256": "4ed1bd011e2c3cd5f28578b02647efd2455578e2e4d7493e7584b4ee81c7899c",
        "pr_run": 34739350668,
        "squash": "fc8b00cd5b909fe52ba34b45be1ff245fdb21bb2",
        "tree": "6b3dfb2a7e045c244d17801b6bbdff43123fcecb",
    },
    94: {
        "base": "fc8b00cd5b909fe52ba34b45be1ff245fdb21bb2",
        "head": "fc748a4b3a4d966cc2226a5f8061bd82bda6af92",
        "main_job": 103687663129,
        "main_log_sha256": "1452169401ab4402eeed597b3456dfec19a7843e712b58cbbf2258144b7c46b6",
        "main_run": 34743721314,
        "pr_checkout": "8fed9aec9c5325e543221d3e2ca6d06be73fa4e0",
        "pr_job": 103686841066,
        "pr_log_sha256": "400554cf4589f24aeb61e7d924a3409648e2d3b1b32eb63d6766d30ceeaa66e0",
        "pr_run": 34743409829,
        "squash": "2f731bbfe4d34ad20100aff3c663b3e4eb3f8fd2",
        "tree": "6bf1e1819119ebbdc77349a3b480553273c0e577",
    },
    95: {
        "base": "2f731bbfe4d34ad20100aff3c663b3e4eb3f8fd2",
        "head": "8b147d394ae57f4d98c81224e48f97d7c1d0d611",
        "main_job": 103695897622,
        "main_log_sha256": "fcd8182b84626d9c9dbf52ca28c41eb2715a86a8911750b5057f577a51a9cbd9",
        "main_run": 34746727238,
        "pr_checkout": "de73bf4691b1b1e8d3d4822caf73e90f09ed3164",
        "pr_job": 103695032587,
        "pr_log_sha256": "665511769fe0910eda5e797c1edeaa5a38795c34d535f1b79e10c3d9990cf0d2",
        "pr_run": 34746407725,
        "squash": "21ada4fcc8fc4c23b0049e3df642573de7067407",
        "tree": "1077df46bb135479bcf5a2f25541f6686d2fd886",
    },
}

PRODUCT_OBSERVATION_PINS = [
    {
        "byte_length": 4399,
        "path": "src/faultatlas/domain/invariant.py",
        "sha256": "58c9839419122c06d1e44aad7c1129fa05342d3d6ec2c388a830d2c62e6d1873",
    },
    {
        "byte_length": 7265,
        "path": "src/faultatlas/domain/invariant_relationship.py",
        "sha256": "8d075da4b91f9778e072938184306c6ffa3f06fbfac95425c5a609225ce9ce55",
    },
    {
        "byte_length": 9961,
        "path": "src/faultatlas/domain/pattern.py",
        "sha256": "590a4f2dcc2473415cc6c77dc4ce714b2995e1e3db35ea1fbe16ef5fcdfda4e3",
    },
    {
        "byte_length": 6856,
        "path": "src/faultatlas/domain/pattern_composition.py",
        "sha256": "c6edbdc2c092826a36e59d42277e335e1fbe892efb6a50b5ab167d5245d65cb7",
    },
    {
        "byte_length": 3820,
        "path": "src/faultatlas/domain/pattern_exemplar.py",
        "sha256": "b330f1187667843e7392e71d5efa8a6bd18fa0df43d7c5849266ca96b68fb770",
    },
]
EXECUTION_OBSERVATION_PIN = {
    "harness": {
        "byte_length": 41311,
        "path": "tests/test_fault_pattern_contract_corpus.py",
        "sha256": "4afe25e417c054d631f6e531f21c618c7eac1299e461b5f41e04c113983870dc",
    },
    "observation_receipt_sha256": "e7791cea2b891aeeed68fac5b17ba5315fabae51f18891a4556d5812e03a639e",
    "python": "3.13.13",
    "uv_lock_sha256": "eee6eb59f69839a202ec072a6b607b60eede58bf760b84f6821904fdd9a24a85",
}

OWNED = {
    "FaultPatternIdentity": ("faultatlas.domain.pattern", "S1.P07.S01"),
    "SuppliedFaultPattern": ("faultatlas.domain.pattern", "S1.P07.S01"),
    "FaultPatternExemplarAssociation": (
        "faultatlas.domain.pattern_exemplar",
        "S1.P07.S02",
    ),
    "FaultInvariantIdentity": ("faultatlas.domain.invariant", "S1.P07.S03"),
    "SuppliedFaultInvariant": ("faultatlas.domain.invariant", "S1.P07.S03"),
    "FaultPatternInvariantAssociation": (
        "faultatlas.domain.invariant_relationship",
        "S1.P07.S04",
    ),
    "FaultInvariantExpectedPropertyAssociation": (
        "faultatlas.domain.invariant_relationship",
        "S1.P07.S04",
    ),
    "FaultPatternComposition": ("faultatlas.domain.pattern_composition", "S1.P07.S05"),
}
BOUNDARIES = {
    "pattern_only_minimum": ["composition_defaults"],
    "typed_python_and_native_json": ["python_children", "json"],
    "local_bounds_order_and_repetition": ["order", "attachment"],
    "full_record_root_and_member_integrity": ["full_member", "V3"],
    "invariant_uniqueness_and_attachment": ["invariant_uniqueness", "attachment"],
    "explicit_relation_independence": ["V1", "V2", "V4"],
    "no_evidence_or_claim_promotion": ["V5", "V6", "V7"],
}
EXIT_EVIDENCE = {
    "published_product": [
        "/product_snapshot/owned",
        "/product_snapshot/source_observations",
    ],
    "composition_boundaries": ["/composition_boundaries"],
    "s07_integrity": ["/sources/s07", "/s07_dispositions"],
    "s08_assurance": ["/corpus_assurance"],
    "publication_lineage": ["/lineage"],
    "preservation": ["/sources", "/history", "/limits"],
    "empirical_review": ["/empirical_review"],
    "lifecycle_readiness": ["/readiness"],
}
PROSPECTIVE = [
    "new_relevant_reviewed_evidence",
    "before_any_future_widening_or_publication_claiming_empirical_pattern_generality",
]


def _check(value: bool, message: str) -> None:
    assert value, message


def _select(document: Any, pointer: str) -> Any:
    for token in pointer.split("/")[1:]:
        token = token.replace("~1", "/").replace("~0", "~")
        document = (
            cast(list[Any], document)[int(token)]
            if isinstance(document, list)
            else document[token]
        )
    return document


def _canonical(document: Any) -> bytes:
    return (
        json.dumps(
            document,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def _no_float(value: str) -> Any:
    raise ValueError("non-integer closure number: " + value)


def _document() -> dict[str, Any]:
    return json.loads(
        (CLOSURE / "closure.json").read_text(encoding="utf-8"),
        parse_float=_no_float,
        parse_constant=_no_float,
    )


def _source_bytes() -> dict[str, bytes]:
    return {key: (ROOT / pin["path"]).read_bytes() for key, pin in SOURCE_PINS.items()}


def _sources(document: dict[str, Any], raw_sources: dict[str, bytes]) -> dict[str, Any]:
    _check(document["sources"] == SOURCE_PINS, "exact immutable source lock map")
    parsed: dict[str, Any] = {}
    for key, pin in SOURCE_PINS.items():
        raw = raw_sources[key]
        _check(
            len(raw) == pin["byte_length"]
            and hashlib.sha256(raw).hexdigest() == pin["sha256"],
            "source bytes: " + key,
        )
        if pin["path"].endswith(".json"):
            parsed[key] = json.loads(raw)
    return parsed


def _product(document: dict[str, Any], sources: dict[str, Any]) -> None:
    product = document["product_snapshot"]
    rows = product["owned"]
    names = [row["symbol"] for row in rows]
    _check(
        len(names) == len(set(names)) and set(names) == set(OWNED),
        "owned symbol coverage",
    )
    current_owners = {
        symbol: "faultatlas.domain." + module
        for module, symbols in P07_SURFACE
        for symbol in symbols
    }
    for row in rows:
        _check(
            (row["module"], row["slice"]) == OWNED[row["symbol"]],
            "owned symbol relationship",
        )
        _check(
            current_owners[row["symbol"]] == row["module"], "shared owner relationship"
        )
    _check(rows == sources["s07"]["surface"], "published S07 responsibility mapping")
    modules = {row["module"] for row in rows}
    _check(product["p07_module_count"] == len(modules) == 5, "bounded module count")
    _check(
        (
            product["production_module_count"],
            product["uuid_identity_count"],
            product["p07_identity_count"],
            product["p07_record_model_count"],
        )
        == (25, 12, 2, 6),
        "historical product counts",
    )
    _check(product["at_commit"] == BASELINE, "product observation baseline")
    paths = ["src/" + m.replace(".", "/") + ".py" for m in sorted(modules)]
    _check(
        [x["path"] for x in product["source_observations"]] == paths,
        "source observation owners",
    )
    _check(
        product["source_observations"] == PRODUCT_OBSERVATION_PINS,
        "historical product observation binding",
    )
    for observation in product["source_observations"]:
        _check(
            len(observation["sha256"]) == 64 and observation["byte_length"] > 0,
            "source observation shape",
        )
    # These are historical source observations, not a future live-byte lock.
    _check(
        product["inventory_owner"] == "tests/_repository_contract.py"
        and product["package_owner"] == "tests/test_package.py",
        "inventory remains upstream owned",
    )
    boundaries = document["composition_boundaries"]
    _check(set(boundaries) == set(BOUNDARIES), "composition obligation coverage")
    for name, keys in BOUNDARIES.items():
        _check(
            boundaries[name]["witnesses"]
            == [sources["s07"]["witnesses"][k] for k in keys],
            "composition witness association",
        )


def _subjects_and_review(document: dict[str, Any], sources: dict[str, Any]) -> None:
    inherited = sources["s07"]["subjects"]
    rows = document["s07_dispositions"]
    _check(
        len(rows) == 3 and [x["id"] for x in rows] == ["deferred:04", P00_ID, P01_ID],
        "source-qualified disposition coverage",
    )
    for i, (key, pointer, id_field) in enumerate(
        [
            ("p03", "/deferred_register/entries/3", "deferred_id"),
            ("p00", "/deferred_register/items/23", "deferred_item_id"),
            ("p01", "/deferred_register/items/37", "deferred_item_id"),
        ]
    ):
        original = _select(sources[key], pointer)
        expected = {
            "s07_selector": f"/subjects/{i}",
            "id": original[id_field],
            "source": {"path": SOURCE_PINS[key]["path"], "selector": pointer},
            "inherited_disposition": inherited[i]["disposition"],
            "remainder": inherited[i]["remainder"],
        }
        _check(rows[i] == expected, "source-qualified disposition content/association")
    _check(
        rows[0]["inherited_disposition"] == "bounded_model_implemented",
        "P03 representation responsibility",
    )
    _check(
        rows[1]["remainder"]["state"] == "unknown_pending_additional_evidence"
        and rows[1]["remainder"]["owner"] == "S1.P08",
        "P00 empirical state/owner",
    )
    _check(
        rows[1]["remainder"]["revisit"]
        == "before_S1.P08_makes_transfer_or_applicability_claims_and_only_after_additional_cross_repository_cases",
        "P00 exact revisit condition",
    )
    _check("empirical_review" in document, "required P01 pre-completion review")
    review = document["empirical_review"]
    p01 = _select(sources["p01"], "/deferred_register/items/37")
    _check(review.get("original_record") == p01, "complete original P01 record")
    _check(
        review.get("original_consequence")
        == p01["consequence_if_unresolved"]
        == P01_CONSEQUENCE,
        "original P01 consequence",
    )
    _check(
        review["subject_source"]
        == {
            "path": SOURCE_PINS["p01"]["path"],
            "selector": "/deferred_register/items/37",
        },
        "P01 review source binding",
    )
    _check(
        review.get("performed") == "before_closure_candidate_sealing",
        "required P01 pre-completion review",
    )
    _check(
        review["decision_authority"] == "explicit_S1.P07.S09_task_contract_section_2",
        "S09 policy authority",
    )
    _check(
        review["conclusion"] == "empirical_pattern_generality_not_established"
        and review["retained_state"] == p01["current_state"] == "evidence_insufficient",
        "empirical uncertainty remains",
    )
    _check(
        review["retained_owner"]
        == p01["immediate_next_owner"]
        == p01["preserved_long_term_phase_owner"]
        == "S1.P07",
        "P01 semantic owner retained",
    )
    _check(
        review["original_deadline"]
        == p01["latest_decision_point"]
        == "before_S1_P07_operational_completion",
        "original P01 deadline retained",
    )
    _check(
        review["prospective_trigger"] == PROSPECTIVE, "prospective trigger is additive"
    )
    _check(
        review["disposition"]
        == "reviewed_unknown_retained_nonblocking_for_bounded_model_closure",
        "bounded review disposition",
    )
    _check(
        review["bounded_closure_policy"]
        == "nonblocking_only_for_supplied_representation_relationship_composition_and_contract_assurance",
        "bounded closure policy",
    )
    _check(
        review["still_blocks"]
        == "any_future_claim_requiring_established_empirical_pattern_generality",
        "generality claim prohibition remains",
    )
    _check(
        review["review_is_empirical_resolution"] is False
        and review["automatically_reopens_phase"] is False
        and review["authorizes_acquisition"] is False,
        "review is not resolution or new work",
    )
    _check(
        review["needed_evidence"]
        == [
            "specifically scoped proposition",
            "genuinely distinct relevant cases with exact source/revision and relationship attribution",
            "examined conditions and counterexamples",
            "reviewed conclusions no broader than the inspected cases",
        ],
        "qualitative evidence requirement",
    )
    expected_evidence = [
        {"source": "p01", "selector": "/deferred_register/items/37"},
        {"source": "s07", "selector": "/subjects/2"},
        {"source": "s08:manifest.json", "selector": "/provenance"},
        {"observation": "current_S09_existing_corpus_owner_execution"},
        {
            "owner": "tests/test_fault_pattern_vertical.py",
            "classification": "synthetic_constructor_scenarios",
        },
    ]
    _check(
        review["evidence"] == expected_evidence and bool(review["question"].strip()),
        "P01 inspected evidence/question",
    )


def _corpus(document: dict[str, Any], sources: dict[str, Any]) -> None:
    corpus = document["corpus_assurance"]
    manifest = sources["s08:manifest.json"]
    expected_files = sorted(k for k in SOURCE_PINS if k.startswith("s08:"))
    _check(
        corpus["file_sources"] == expected_files and len(set(expected_files)) == 9,
        "corpus file binding",
    )
    _check(
        corpus["directory"] == "reference_corpus/contracts/pattern-invariant/v1",
        "corpus directory",
    )
    for stem in ("manifest", "valid-vectors", "invalid-vectors", "composition-vectors"):
        source = SOURCE_PINS["s08:" + stem + ".json"]
        sidecar = (ROOT / SOURCE_PINS["s08:" + stem + ".sha256"]["path"]).read_text()
        _check(
            sidecar == source["sha256"] + "  " + stem + ".json\n",
            "S08 primary sidecar association",
        )
    rows = [
        r
        for stem in ("valid-vectors", "invalid-vectors", "composition-vectors")
        for r in sources["s08:" + stem + ".json"]["vectors"]
    ]
    ids = [r["id"] for r in rows]
    _check(len(ids) == len(set(ids)) == 48, "sealed vector identity coverage")
    actual_counts = {
        "files": {
            stem: len(sources["s08:" + stem + ".json"]["vectors"])
            for stem in ("valid-vectors", "invalid-vectors", "composition-vectors")
        },
        "vectors": len(rows),
        "accepted": sum(r["operation"] != "reject" for r in rows),
        "rejected": sum(r["operation"] == "reject" for r in rows),
    }
    _check(
        corpus["counts"]
        == manifest["counts"]
        == actual_counts
        == {
            "files": {
                "valid-vectors": 16,
                "invalid-vectors": 23,
                "composition-vectors": 9,
            },
            "vectors": 48,
            "accepted": 25,
            "rejected": 23,
        },
        "S08 row counts are not dispatch counts",
    )
    _check(
        corpus["targets"] == manifest["targets"] == {n: o[0] for n, o in OWNED.items()},
        "corpus primary target map",
    )
    _check(corpus["coverage"] == manifest["coverage"], "corpus coverage binding")
    for target, bucket in corpus["coverage"].items():
        for kind, accepted in [("accepted", True), ("rejected", False)]:
            actual = [
                r["id"]
                for r in rows
                if r["target"] == target and (r["operation"] != "reject") == accepted
            ]
            _check(
                bool(actual) and bucket[kind] == actual,
                "actual primary target acceptance/rejection coverage",
            )
    _check(
        all(r["provenance"] == "synthetic_caller_supplied" for r in rows),
        "all executable cases remain synthetic",
    )
    _check(
        corpus["provenance"] == "synthetic_caller_supplied"
        and type(corpus["independent_empirical_observations"]) is int
        and corpus["independent_empirical_observations"] == 0,
        "synthetic vectors are not empirical evidence",
    )
    execution = corpus["execution"]
    _check(
        execution["kind"] == "current_S09_presealing_existing_owner_execution"
        and execution["at_commit"] == BASELINE,
        "execution observation context",
    )
    _check(
        (
            execution["matched_rows"],
            execution["primary_dispatches"],
            execution["prerequisite_dispatches"],
            execution["companion_dispatches"],
        )
        == (48, 48, 23, 3),
        "separate execution counters",
    )
    _check(
        execution["targets"] == sorted(OWNED)
        and execution["input_sources"] == expected_files,
        "executed target/input scope",
    )
    expected_primary = {
        target: sum(r["target"] == target for r in rows) for target in OWNED
    }
    expected_prerequisites = {
        target: sum(r["target"] == target and r["operation"] == "reject" for r in rows)
        for target in OWNED
    }
    _check(
        execution["per_role_target_dispatches"]
        == {
            "primary": expected_primary,
            "prerequisite": expected_prerequisites,
            "companion": {"FaultPatternComposition": 2, "FaultInvariantIdentity": 1},
        },
        "current owner report target counts",
    )
    _check(
        {key: execution[key] for key in EXECUTION_OBSERVATION_PIN}
        == EXECUTION_OBSERVATION_PIN,
        "execution input/harness observation binding",
    )
    _check(
        execution["harness"]["path"]
        == corpus["existing_owner"]
        == "tests/test_fault_pattern_contract_corpus.py",
        "existing execution owner",
    )
    _check(
        corpus["canonicalization_scope"] == "test_artifacts_not_P10_product_bytes"
        and corpus["source_only"] == "package_excluded",
        "corpus packaging/interchange boundary",
    )
    # No predecessor verifier import, execution, or recursive pytest here.


def _lineage(document: dict[str, Any]) -> None:
    ledger = document["lineage"]
    products = ledger["product_publications"]
    _check(
        [(p["slice"], p["pr"]) for p in products]
        == [(f"S1.P07.S{i:02d}", pr) for i, pr in enumerate(PRODUCT_PRS, 1)],
        "required product publication coverage/order",
    )
    _check(
        (ledger["product_count"], ledger["maintenance_count"], ledger["ancestry_count"])
        == (len(products), 1, len(ledger["ancestry_order"])),
        "lineage derived counts",
    )
    maintenance = ledger["maintenance_publication"]
    _check(
        maintenance["pr"] == 92 and maintenance["kind"] == "maintenance",
        "E01 is separate maintenance",
    )
    _check(
        ledger["ancestry_order"] == list(ANCESTRY_PRS), "maintenance ancestry placement"
    )
    entries = {p["pr"]: p for p in [*products, maintenance]}
    for pr in ANCESTRY_PRS:
        p = entries[pr]
        pin = PUBLICATION_PINS[pr]
        _check(
            (p["base"], p["head"], p["head_tree"], p["squash"], p["squash_tree"])
            == (pin["base"], pin["head"], pin["tree"], pin["squash"], pin["tree"]),
            "publication base/head/tree/squash binding",
        )
        _check(
            p["kind"] == ("maintenance" if pr == 92 else "product_slice"),
            "publication kind",
        )
        for label, event in [("pr", "pull_request"), ("main", "push")]:
            c = p["checks"][label]
            expected_head = pin["head"] if label == "pr" else pin["squash"]
            expected_checkout = pin["pr_checkout"] if label == "pr" else pin["squash"]
            _check(
                (c["run_id"], c["job_id"], c["event"], c["attempt"], c["conclusion"])
                == (pin[label + "_run"], pin[label + "_job"], event, 1, "success"),
                "publication CI identity/event/attempt",
            )
            _check(
                c["associated_head"] == expected_head
                and c["actual_checkout"] == expected_checkout
                and c["checkout_tree"] == pin["tree"],
                "publication actual checkout/head/tree",
            )
            _check(
                c["checkout_parents"]
                == ([pin["base"], pin["head"]] if label == "pr" else [pin["base"]]),
                "publication checkout parents",
            )
            evidence = c["checkout_evidence"]
            _check(
                evidence["kind"] == "freshly_read_provider_log"
                and evidence["command"] == "git log -1 --format=%H"
                and evidence["log_sha256"] == pin[label + "_log_sha256"]
                and bool(evidence["line_numbers"]),
                "actual checkout log evidence",
            )
    ordered = [entries[pr] for pr in ANCESTRY_PRS]
    _check(
        all(b["base"] == a["squash"] for a, b in zip(ordered, ordered[1:]))
        and ordered[-1]["squash"] == BASELINE,
        "first-parent publication ancestry",
    )
    _check(
        ledger["own_publication"] == "external_future_event_not_in_this_ledger",
        "own publication absent from predecessor ledger",
    )


def _exit_and_readiness(document: dict[str, Any], sources: dict[str, Any]) -> None:
    obligations = document["exit_obligations"]
    names = [o["id"] for o in obligations]
    _check(
        len(names) == len(set(names)) and set(names) == set(EXIT_EVIDENCE),
        "bounded exit coverage",
    )
    for item in obligations:
        _check(
            item["evidence"] == EXIT_EVIDENCE[item["id"]]
            and item["disposition"] == "verified_for_bounded_scope",
            "bounded exit disposition/evidence",
        )
        for pointer in item["evidence"]:
            _check(bool(_select(document, pointer)), "nonvacuous bounded exit evidence")
    empirical = [
        s["remainder"]
        for s in document["s07_dispositions"]
        if s["remainder"] is not None
    ]
    expected = {
        "bounded_exit_obligations": len(obligations),
        "unresolved_product_blockers": sum(
            o["disposition"] != "verified_for_bounded_scope" for o in obligations
        ),
        "p07_owned_empirical_entries": sum(e["owner"] == "S1.P07" for e in empirical),
        "p08_owned_empirical_entries": sum(e["owner"] == "S1.P08" for e in empirical),
        "required_precompletion_reviews_performed": 1,
        "empirical_questions_resolved": 0,
        "independent_new_observed_cases": 0,
    }
    _check(
        all(type(v) is int for v in document["summary"].values())
        and document["summary"] == expected,
        "scoped blocker/unknown counters",
    )
    _check(
        not {"self_owned_open", "all_unknowns_resolved", "generality_established"}
        & document.keys(),
        "unqualified completion claim",
    )
    ready = document["readiness"]
    _check(
        ready["after_successful_external_publication"]
        == {
            "completed_phase": "S1.P07",
            "active_phases": [],
            "next": "S1.P08",
            "next_state": "not_started",
        },
        "bounded between-Phases readiness",
    )
    _check(
        ready["eligibility"] == "separate_Phase_start_discussion_and_planning_only"
        and ready["p08_schema_authorized"] is False
        and ready["p08_implementation_started"] is False
        and ready["empirical_transfer_validated"] is False
        and ready["p09_p10"] == "not_started",
        "P08 planning-only readiness",
    )
    _check(
        document["publication"]
        == {
            "state": "sealed_publication_candidate",
            "required_external_conditions": [
                "final_head_protected_PR_CI_and_review_settlement",
                "ordinary_protected_squash",
                "reviewed_tested_squash_tree_equality",
                "natural_main_actual_squash_checkout_attempt_and_success",
                "package_source_bytes_ff_only_sync_and_owned_cleanup",
            ],
            "actual_evidence_location": "Git_GitHub_and_final_task_execution_receipt",
            "own_publication_facts": None,
        },
        "own publication remains external",
    )
    history = document["history"]
    _check(
        [x["id"] for x in history] == ["s01_takeover", "s07_stop_scope01"],
        "retained continuation history",
    )
    _check(
        history[0]["observed_pr_commit_ids"]
        == [
            "fc969dc4cd31f09fa93d1cf87130fa140c425730",
            "4dfefb30ea7a8033186e384981d3961f729f0de5",
        ]
        and history[0]["source"] == "https://github.com/MianliWang/FaultAtlas/pull/87",
        "S01 attributed takeover history",
    )
    _check(
        history[1]["disposition"]
        == "resolved_by_explicit_four_reader_scope_expansion_and_successful_PR94_publication"
        and history[1]["current_product_blocker"] is False,
        "S07 resolved STOP history",
    )
    limits = {x["id"]: x for x in document["limits"]}
    _check(
        limits["missing_whole_phase_planning_exercise"]["disposition"]
        == "not_retrospectively_completed"
        and limits["missing_whole_phase_planning_exercise"]["missing"]
        == ["full_three_ledger_exercise", "whole_phase_route_comparison"],
        "no retrospective planning audit",
    )
    _check(
        limits["empirical_generality"]["disposition"] == "not_established"
        and limits["empirical_generality"]["independent_new_observed_cases"] == 0,
        "no empirical generality claim",
    )
    for i, debt in enumerate(sources["p06"]["known_debt_register"]["items"]):
        _check(
            limits[debt["debt_id"]]
            == {
                "id": debt["debt_id"],
                "source": "p06",
                "selector": f"/known_debt_register/items/{i}",
                "disposition": debt["disposition"],
            },
            "retained P06 limitation",
        )


def _validate(
    document: dict[str, Any], raw_sources: dict[str, bytes] | None = None
) -> None:
    _check(
        document["format"]
        == {
            "name": "faultatlas-pattern-invariant-bounded-phase-closure",
            "version": 1,
            "canonicalization": "json-sort-keys-compact-utf8-lf-v1",
        },
        "closure format",
    )
    _check(
        document["identity"]
        == {
            "phase": "S1.P07",
            "slice": "S1.P07.S09",
            "scope": "bounded_supplied_representation_relationship_composition_and_contract_assurance",
            "baseline_commit": BASELINE,
            "baseline_tree": BASE_TREE,
            "state": "sealed_publication_candidate",
            "proposed_completion": "bounded_P07_complete_with_explicit_empirical_limits",
        },
        "bounded candidate identity",
    )
    sources = _sources(
        document, _source_bytes() if raw_sources is None else raw_sources
    )
    _product(document, sources)
    _subjects_and_review(document, sources)
    _corpus(document, sources)
    _lineage(document)
    _exit_and_readiness(document, sources)


def _render(document: dict[str, Any]) -> str:
    d = document
    review = d["empirical_review"]
    corpus = d["corpus_assurance"]
    lines = [
        "# S1.P07 — Bounded Pattern/Invariant Phase Closure",
        "",
        "State: `"
        + d["identity"]["state"]
        + "`. Proposed completion: `"
        + d["identity"]["proposed_completion"]
        + "`.",
        "Scope: `" + d["identity"]["scope"] + "`.",
        "Baseline: `"
        + d["identity"]["baseline_commit"]
        + "` / tree `"
        + d["identity"]["baseline_tree"]
        + "`.",
        "",
        "## Required P01 pre-completion review",
        "",
        review["question"],
        "",
        "> " + review["original_consequence"],
        "",
        "The complete inherited record is retained in the primary JSON at `empirical_review.original_record`.",
        "Review: `"
        + review["performed"]
        + "`; authority: `"
        + review["decision_authority"]
        + "`.",
        "Conclusion: `"
        + review["conclusion"]
        + "`; disposition: `"
        + review["disposition"]
        + "`.",
        "State `"
        + review["retained_state"]
        + "`; semantic owner `"
        + review["retained_owner"]
        + "`.",
        "Original deadline: `" + review["original_deadline"] + "`.",
        "Additional prospective triggers: "
        + ", ".join("`" + x + "`" for x in review["prospective_trigger"])
        + ".",
        "Still blocks: `"
        + review["still_blocks"]
        + "`. Review completion is not empirical resolution, automatic reopening or acquisition authority.",
        "",
        "Needed evidence:",
        "",
    ] + ["- " + s for s in review["needed_evidence"]]
    lines += ["", "## Source-qualified inherited dispositions", ""]
    for s in d["s07_dispositions"]:
        lines += [
            "- `"
            + s["source"]["path"]
            + "#"
            + s["source"]["selector"]
            + "`: `"
            + s["id"]
            + "`, inherited `"
            + s["inherited_disposition"]
            + "`."
        ]
        if s["remainder"]:
            r = s["remainder"]
            lines += [
                "  `"
                + r["state"]
                + "`; owner `"
                + r["owner"]
                + "`; original revisit `"
                + r["revisit"]
                + "`. "
                + r["reason"]
            ]
    lines += [
        "",
        "These are source-qualified entries, not independent empirical observations.",
        "",
        "## Product snapshot",
        "",
        d["product_snapshot"]["observation_semantics"],
        "",
        "| Symbol | Module | Slice |",
        "| --- | --- | --- |",
    ]
    for row in d["product_snapshot"]["owned"]:
        lines.append(
            "| "
            + " | ".join("`" + row[k] + "`" for k in ("symbol", "module", "slice"))
            + " |"
        )
    lines += [
        "",
        "25 package modules; five P07 modules/eight symbols, including two UUID identities and six record models. Twelve UUID-root identities remain package-wide.",
        "",
        "## Composition boundaries",
        "",
    ]
    lines += [
        "- " + name + ": " + ", ".join("`" + w + "`" for w in entry["witnesses"])
        for name, entry in sorted(d["composition_boundaries"].items())
    ]
    lines += [
        "",
        "## Existing S08 corpus assurance",
        "",
        "`" + json.dumps(corpus["counts"], sort_keys=True) + "`.",
        "Current pre-sealing execution of the existing owner: 48 matched rows, 48 primary + 23 prerequisite + 3 companion target calls; all eight primary targets have accepted and rejected examples.",
        "Execution input commit: `"
        + corpus["execution"]["at_commit"]
        + "`; captured report SHA-256 `"
        + corpus["execution"]["observation_receipt_sha256"]
        + "`.",
        "Supporting/nested validation is not extra vector coverage. All executable examples remain synthetic; canonical test bytes are not P10 product interchange.",
        "",
        "## Canonical publication lineage",
        "",
        "| PR | Role | Final head | Actual PR checkout | Squash | Tree |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    entries = {
        x["pr"]: x
        for x in [
            *d["lineage"]["product_publications"],
            d["lineage"]["maintenance_publication"],
        ]
    }
    for pr in d["lineage"]["ancestry_order"]:
        x = entries[pr]
        lines.append(
            f"| [#{pr}](https://github.com/MianliWang/FaultAtlas/pull/{pr}) | {x.get('slice', 'E01 maintenance')} | `{x['head']}` | `{x['checks']['pr']['actual_checkout']}` | `{x['squash']}` | `{x['head_tree']}` |"
        )
    lines += [
        "",
        "Each entry records its base, successful PR/main events and attempts, run/job IDs, actual checkout parents/tree, and supporting log hash/line numbers in JSON. All historical actual-checkout claims were checked from provider logs in this task. E01 is a separate maintenance publication, not a ninth product Slice or correction. S09 publication remains external.",
        "",
        "## Retained history and limits",
        "",
    ]
    lines += [
        "- " + json.dumps(item, ensure_ascii=False, sort_keys=True)
        for item in d["history"]
    ]
    lines += [
        "- " + json.dumps(item, ensure_ascii=False, sort_keys=True)
        for item in d["limits"]
    ]
    lines += ["", "## Bounded exit obligations", ""]
    lines += [
        "- `"
        + item["id"]
        + "`: `"
        + item["disposition"]
        + "`; "
        + ", ".join(item["evidence"])
        for item in d["exit_obligations"]
    ]
    lines += [
        "",
        "`" + json.dumps(d["summary"], sort_keys=True) + "`.",
        "Zero unresolved product blockers applies only to the evidenced bounded scope. One P07-owned empirical entry and one P08-owned empirical entry remain.",
        "",
        "## Readiness and external publication",
        "",
        json.dumps(d["readiness"], ensure_ascii=False, sort_keys=True),
        json.dumps(d["publication"], ensure_ascii=False, sort_keys=True),
        "",
        "## Immutable retained source locks",
        "",
        "| Source | Path | SHA-256 | Bytes |",
        "| --- | --- | --- | --- |",
    ]
    for key, pin in sorted(d["sources"].items()):
        lines.append(
            f"| {key} | `{pin['path']}` | `{pin['sha256']}` | {pin['byte_length']} |"
        )
    lines += [
        "",
        "Primary JSON is authoritative; Markdown is deterministic derived documentation. No own final publication fact or future compatibility lock is introduced.",
    ]
    return "\n".join(lines) + "\n"


def _integrity(directory: Path = CLOSURE) -> None:
    _check(
        {p.name for p in directory.iterdir()}
        == {"closure.json", "closure.sha256", "closure.md"},
        "closure file inventory",
    )
    raw = (directory / "closure.json").read_bytes()
    document = json.loads(
        raw.decode("utf-8"), parse_float=_no_float, parse_constant=_no_float
    )
    _check(_canonical(document) == raw, "canonical closure bytes")
    _check(
        len(raw) == CLOSURE_LENGTH and hashlib.sha256(raw).hexdigest() == CLOSURE_SHA,
        "independent closure byte pin",
    )
    _check(
        (directory / "closure.sha256").read_bytes()
        == (CLOSURE_SHA + "  closure.json\n").encode(),
        "primary sidecar",
    )
    _check(
        (directory / "closure.md").read_text() == _render(document),
        "derived closure view",
    )


def test_complete_bounded_closure_and_independent_integrity() -> None:
    _integrity()
    _validate(_document())


@pytest.mark.parametrize("change", ("remove", "substitute", "duplicate"))
def test_publication_coverage_is_not_just_counts(change: str) -> None:
    d = _document()
    _validate(d)
    rows = d["lineage"]["product_publications"]
    if change == "remove":
        rows.pop()
    elif change == "substitute":
        rows[-1]["pr"] = 92
    else:
        rows[-1] = copy.deepcopy(rows[0])
    d["lineage"]["product_count"] = len(rows)
    d["lineage"]["ancestry_order"] = (
        [p["pr"] for p in rows[:5]] + [92] + [p["pr"] for p in rows[5:]]
    )
    d["lineage"]["ancestry_count"] = len(d["lineage"]["ancestry_order"])
    with pytest.raises(
        AssertionError, match="required product publication coverage/order"
    ):
        _validate(d)


@pytest.mark.parametrize("change", ("remove", "substitute", "duplicate"))
def test_owned_symbol_coverage_with_reconciled_counts(change: str) -> None:
    d = _document()
    _validate(d)
    rows = d["product_snapshot"]["owned"]
    if change == "remove":
        rows.pop()
    elif change == "substitute":
        rows[-1]["symbol"] = "FaultInstanceIdentity"
    else:
        rows[-1] = copy.deepcopy(rows[0])
    d["product_snapshot"]["p07_module_count"] = len({x["module"] for x in rows})
    d["product_snapshot"]["p07_identity_count"] = sum(
        x["symbol"] in {"FaultPatternIdentity", "FaultInvariantIdentity"} for x in rows
    )
    d["product_snapshot"]["p07_record_model_count"] = (
        len(rows) - d["product_snapshot"]["p07_identity_count"]
    )
    with pytest.raises(AssertionError, match="owned symbol coverage"):
        _validate(d)


@pytest.mark.parametrize(
    "change", ("checkout", "head", "tree", "corpus_file", "subject", "execution_input")
)
def test_full_publication_corpus_and_subject_bindings(change: str) -> None:
    d = _document()
    _validate(d)
    if change == "checkout":
        d["lineage"]["product_publications"][0]["checks"]["pr"]["actual_checkout"] = d[
            "lineage"
        ]["product_publications"][0]["head"]
    elif change == "head":
        d["lineage"]["product_publications"][0]["head"] = "0" * 40
    elif change == "tree":
        d["lineage"]["product_publications"][0]["checks"]["main"]["checkout_tree"] = (
            "0" * 40
        )
    elif change == "corpus_file":
        d["corpus_assurance"]["file_sources"][0] = "s08:valid-vectors.json"
    elif change == "subject":
        d["s07_dispositions"][2]["source"]["selector"] = "/deferred_register/items/23"
    else:
        d["corpus_assurance"]["execution"]["harness"]["sha256"] = "0" * 64
    with pytest.raises(
        AssertionError,
        match="publication actual checkout/head/tree|publication base/head/tree|corpus file binding|source-qualified disposition content|execution input/harness observation binding",
    ):
        _validate(d)


@pytest.mark.parametrize(
    "change",
    (
        "omit_consequence",
        "omit_review",
        "resolve",
        "move_owner",
        "merge_p00",
        "zero_p07_count",
        "drop_deadline",
        "replace_trigger",
    ),
)
def test_p01_review_does_not_resolve_or_erase_the_unknown(change: str) -> None:
    d = _document()
    _validate(d)
    if change == "omit_consequence":
        d["empirical_review"].pop("original_consequence")
    elif change == "omit_review":
        d.pop("empirical_review")
    elif change == "resolve":
        d["empirical_review"]["retained_state"] = "resolved"
    elif change == "move_owner":
        d["empirical_review"]["retained_owner"] = "S1.P08"
    elif change == "merge_p00":
        d["s07_dispositions"][2] = copy.deepcopy(d["s07_dispositions"][1])
    elif change == "zero_p07_count":
        d["summary"]["p07_owned_empirical_entries"] = 0
    elif change == "drop_deadline":
        d["empirical_review"]["original_deadline"] = ""
    else:
        d["empirical_review"]["prospective_trigger"] = [
            "before_S1_P07_operational_completion"
        ]
    with pytest.raises(
        AssertionError,
        match="original P01 consequence|required P01 pre-completion review|empirical uncertainty remains|P01 semantic owner|source-qualified disposition coverage|scoped blocker/unknown counters|original P01 deadline|prospective trigger",
    ):
        _validate(d)


@pytest.mark.parametrize(
    "change",
    (
        "generality",
        "transfer",
        "observations",
        "own_publication",
        "p08_implementation",
        "exit_omitted",
    ),
)
def test_false_completion_or_missing_bounded_exit_is_rejected(change: str) -> None:
    d = _document()
    _validate(d)
    if change == "generality":
        d["empirical_review"]["conclusion"] = "generality_established"
    elif change == "transfer":
        d["readiness"]["empirical_transfer_validated"] = True
    elif change == "observations":
        d["corpus_assurance"]["independent_empirical_observations"] = 48
    elif change == "own_publication":
        d["publication"]["own_publication_facts"] = {"merged": True, "sha": "a" * 40}
    elif change == "p08_implementation":
        d["readiness"]["p08_implementation_started"] = True
    else:
        d["exit_obligations"].pop()
        d["summary"]["bounded_exit_obligations"] -= 1
    with pytest.raises(
        AssertionError,
        match="empirical uncertainty remains|P08 planning-only|synthetic vectors are not empirical|own publication remains external|bounded exit coverage",
    ):
        _validate(d)


def test_locked_input_change_is_independent_of_closure_digest() -> None:
    d = _document()
    raw = _source_bytes()
    _validate(d, raw)
    raw["p01"] = raw["p01"].replace(
        b"evidence_insufficient", b"evidence_insufficienu", 1
    )
    with pytest.raises(AssertionError, match="source bytes: p01"):
        _validate(d, raw)


@pytest.mark.parametrize("change", ("primary", "sidecar", "view"))
def test_primary_sidecar_and_view_have_independent_integrity(
    tmp_path: Path, change: str
) -> None:
    for name in ("closure.json", "closure.sha256", "closure.md"):
        (tmp_path / name).write_bytes((CLOSURE / name).read_bytes())
    _integrity(tmp_path)
    if change == "primary":
        p = tmp_path / "closure.json"
        p.write_bytes(
            p.read_bytes().replace(
                b"evidence_insufficient", b"evidence_insufficienu", 1
            )
        )
    elif change == "sidecar":
        (tmp_path / "closure.sha256").write_text("0" * 64 + "  closure.json\n")
    else:
        p = tmp_path / "closure.md"
        p.write_text(p.read_text() + "\nGenerality established.\n")
    with pytest.raises(
        AssertionError,
        match="independent closure byte pin|primary sidecar|derived closure view",
    ):
        _integrity(tmp_path)
