from __future__ import annotations

import base64
import copy
import hashlib
import json
import math
import os
import re
import stat
import subprocess
import tarfile
import zipfile
from collections import Counter
from pathlib import Path
from typing import Any, NoReturn, cast

import pytest
from pydantic import BaseModel

import faultatlas
from faultatlas.domain.evidence import (
    AcquisitionRun,
    EvidenceCompletenessAssessment,
    EvidenceCorrection,
    EvidenceEnvelope,
    EvidencePublication,
    EvidenceSupersession,
    EvidenceTransformation,
    ExactArtifactIdentity,
    ResponseRepresentationObservation,
    RetrievalRequestControls,
    RetrievalRequestReference,
    project_evidence_envelope_to_legacy_artifact_snapshot,
    wrap_legacy_artifact_snapshot,
)
from faultatlas.domain.source import ArtifactSnapshot, SourceLocator

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
CLOSURE_RELATIVE = (
    "reference_corpus/contracts/evidence-envelope/closures/s1-p03-phase-closure"
)
CLOSURE_ROOT = REPOSITORY_ROOT / CLOSURE_RELATIVE
CORPUS_ROOT = REPOSITORY_ROOT / "reference_corpus/contracts/evidence-envelope/v1"
REPLAY_PATH = CORPUS_ROOT / "replay-vectors.json"

EXPECTED_CLOSURE_FILES = {
    "closure.json": (
        127_921,
        "21a24e7ab572456f22d3aca572e10e76be69529770b96a131f3d4f624d0b481b",
    ),
    "closure.md": (
        10_462,
        "fe99a83ef91b16a590ccfb0178c5fc477d780b2a8bb4efe083cdd7eab47e7947",
    ),
    "closure.sha256": (
        79,
        "16068f08bf9ab929f601dbc010c0bc613a86f49f4e427070ebbf214a7ecf257a",
    ),
}

EXPECTED_TOP_LEVEL = {
    "assurance",
    "contract_corpus_assurance",
    "deferred_register",
    "entry_readiness",
    "established_findings",
    "exit_criteria",
    "format",
    "implementation_inventory",
    "integration_assurance",
    "legacy_compatibility_assurance",
    "non_generalizations",
    "phase_identity",
    "publication_contract",
    "replay_assurance",
    "semantic_boundaries",
    "slice_ledger",
    "source_locks",
    "test_assurance",
}

EXPECTED_SLICE_TITLES = [
    ("S1.P03.S01", "Retrieval Request Identity and Authority Foundation"),
    ("S1.P03.S02", "Request Controls and Response Representation Observations"),
    ("S1.P03.S03", "Exact Retained Artifacts and Digest Scope"),
    ("S1.P03.S04", "Acquisition Runs and Evidence Membership"),
    ("S1.P03.S05", "Transformations, Corrections, and Supersession"),
    ("S1.P03.S06", "Completeness, Omissions, and Publication Provenance"),
    ("S1.P03.S07", "Evidence Envelope Composition and Legacy Adapter"),
    ("S1.P03.S08", "Evidence Contract Corpus"),
    ("S1.P03.S09", "Integration and Phase Closure"),
]

EXPECTED_PUBLICATION_SLICES = {
    31: ("S1.P03.S01", "product_slice_publication"),
    32: ("S1.P03.S02", "product_slice_publication"),
    33: ("S1.P03.S03", "product_slice_publication"),
    34: ("S1.P03.S04", "product_slice_publication"),
    35: ("S1.P03.S05", "product_slice_publication"),
    36: ("S1.P03.S06", "product_slice_publication"),
    37: ("S1.P03.S07", "product_slice_publication"),
    38: ("S1.P03.S07", "test_assurance_corrective_publication"),
    41: ("S1.P03.S08", "product_slice_publication"),
}

EXPECTED_EVIDENCE_EXPORTS = (
    "AcquisitionRunId",
    "RetrievalRequestOrdinal",
    "RetrievalRequestId",
    "RetrievalMethod",
    "RetrievalRoutePath",
    "RetrievalRequestReference",
    "MediaType",
    "ApiVersion",
    "RequestQueryParameter",
    "RetrievalRequestControls",
    "ResponseRepresentationState",
    "HttpStatusCode",
    "ContentEncoding",
    "MediaTypeParameter",
    "ResponseRepresentationObservation",
    "ArtifactDigestAlgorithm",
    "ArtifactDigestScope",
    "ArtifactSha256Digest",
    "ArtifactByteLength",
    "ArtifactDigest",
    "ExactArtifactIdentity",
    "ArtifactRetentionMode",
    "ExactRetainedArtifact",
    "AcquisitionRunStatus",
    "AcquisitionRequestMembership",
    "AcquisitionRun",
    "EvidenceRecordFormat",
    "EvidenceVersion",
    "EvidenceCanonicalization",
    "DurableEvidenceRecordReference",
    "EvidenceRelationId",
    "TransformationOperation",
    "TransformationLossiness",
    "TransformationReversibility",
    "TransformationSubject",
    "EvidenceTransformation",
    "EvidenceCorrection",
    "EvidenceSupersession",
    "EvidenceRecordRelationship",
    "EvidenceScopeId",
    "EvidenceRequirementId",
    "EvidenceDispositionReason",
    "EvidenceRequirementOutcome",
    "EvidenceOmission",
    "EvidenceRequirementResult",
    "EvidenceCompletenessStatus",
    "EvidenceCompletenessAssessment",
    "EvidencePublicationMethod",
    "PublicationCheckEvent",
    "PublicationCheckName",
    "SuccessfulPublicationCheck",
    "EvidencePublication",
    "EvidenceEnvelope",
    "LegacyEvidenceCompatibilityReason",
    "LegacyArtifactSnapshotEnvelopeMappingResult",
    "LegacyArtifactSnapshotProjectionResult",
    "wrap_legacy_artifact_snapshot",
    "project_evidence_envelope_to_legacy_artifact_snapshot",
)

EXPECTED_PRODUCTION_SOURCES = (
    "src/faultatlas/__init__.py",
    "src/faultatlas/__main__.py",
    "src/faultatlas/cli.py",
    "src/faultatlas/domain/__init__.py",
    "src/faultatlas/domain/compatibility.py",
    "src/faultatlas/domain/evidence.py",
    "src/faultatlas/domain/identity.py",
    "src/faultatlas/domain/revision.py",
    "src/faultatlas/domain/source.py",
)
CURRENT_PRODUCTION_SOURCES = (
    *EXPECTED_PRODUCTION_SOURCES,
    "src/faultatlas/domain/snapshot.py",
    "src/faultatlas/domain/snapshot_evidence_link.py",
)

EXPECTED_SOURCE_LOCKS = {
    "reference_corpus/contracts/evidence-envelope/v1/contract.md": (
        15384,
        "cb33ba75bc77ee9ac1701a09846168fdc44098a821dc246c3129a7d2c8fddfef",
    ),
    "reference_corpus/contracts/evidence-envelope/v1/invalid-vectors.json": (
        141878,
        "a379f425e31e1a8627818fb2f4a8afb420975680048f0ecb14da6305022b3592",
    ),
    "reference_corpus/contracts/evidence-envelope/v1/invalid-vectors.sha256": (
        87,
        "cfa302e3629fd78a3c839bd71f04872e6cc0516ffe7e5e8be4cc13ebee377c85",
    ),
    "reference_corpus/contracts/evidence-envelope/v1/manifest.json": (
        22846,
        "139364b04676d59e4717a38e73b371b138146a2a933688ab3793aac6fd2e03f0",
    ),
    "reference_corpus/contracts/evidence-envelope/v1/manifest.sha256": (
        80,
        "648f757f110fbe8ce5ac3376190375f48b42fbb4351f6860356086980d9972e4",
    ),
    "reference_corpus/contracts/evidence-envelope/v1/replay-vectors.json": (
        120288,
        "e677aa79cde9142975665f87a5c8be82ba8fa150c302ae11fbd1e863d4d2c32f",
    ),
    "reference_corpus/contracts/evidence-envelope/v1/replay-vectors.sha256": (
        86,
        "4b821d5c64c246ff90c8f43c816886312b6cc8008e6f3980bf81866f58bc2228",
    ),
    "reference_corpus/contracts/evidence-envelope/v1/valid-vectors.json": (
        182770,
        "49a005d2ab8e321e0867c5346db187e4a7736a392fd8b7eb4d343ed100385b86",
    ),
    "reference_corpus/contracts/evidence-envelope/v1/valid-vectors.sha256": (
        85,
        "1c21386cb1c1b861719a8d71e408963fcab413681f8ff3aa999bd638ea773379",
    ),
    "reference_corpus/contracts/identity/closures/s1-p01-phase-closure/closure.json": (
        112606,
        "2c1bfb9d3d596711066796ef83999d49b6846e65315a301eead7fa8fb5ac4642",
    ),
    "reference_corpus/contracts/identity/closures/s1-p01-phase-closure/closure.md": (
        3847,
        "cfde27cbd9d8d1fc979ffb3d878999663cc52a25e5f07d60b70b2791e69292ca",
    ),
    "reference_corpus/contracts/identity/closures/s1-p01-phase-closure/closure.sha256": (
        79,
        "8c1bc1ff60ef2ae25f0bca5abd696708b9a59b2fadd15bd7586a9fb868c262ae",
    ),
    "reference_corpus/contracts/identity/corrections/s05-c01-ambiguous-union-round-trip/correction.json": (
        12436,
        "c17edfa5dc227850d6b982d1ec8c83b4236cd403bb7ca1b1c66b662f8657347a",
    ),
    "reference_corpus/contracts/identity/corrections/s05-c01-ambiguous-union-round-trip/correction.md": (
        2808,
        "32eae618dc35a124f93f9dcac3682fb27fb7621c5a1065331be5584ec972bcc0",
    ),
    "reference_corpus/contracts/identity/corrections/s05-c01-ambiguous-union-round-trip/correction.sha256": (
        82,
        "d63684a33ca94471ff62485064850f1db7b5a8ec7eab25f3902b0afa529aec7e",
    ),
    "reference_corpus/contracts/identity/corrections/s05-c01-ambiguous-union-round-trip/regression-vectors.json": (
        26111,
        "721b6a97a7b80dcc1d33643f6920b21d2e2a8b010d8528f8d194a6691a3feff2",
    ),
    "reference_corpus/contracts/identity/corrections/s05-c01-ambiguous-union-round-trip/regression-vectors.sha256": (
        90,
        "d8a881d7ec3bc9908fedd5b7eeb2ab03d9e241e12dbf90a45d477eae4acf1ed1",
    ),
    "reference_corpus/contracts/identity/v1/compatibility-vectors.json": (
        53810,
        "f3f9248c2562bb4a545b2e14d25d0346689bbf5b346ca343a8974b317d4b79ac",
    ),
    "reference_corpus/contracts/identity/v1/compatibility-vectors.sha256": (
        93,
        "9c19cc782e935fa2a5954cebbcc7055a9c6cc895b657b36d5e5781f7169931ec",
    ),
    "reference_corpus/contracts/identity/v1/contract.md": (
        3329,
        "4c3d44194d1708d1493808022212476ca4bfb3324ed3b620cbd7d9f830fcd806",
    ),
    "reference_corpus/contracts/identity/v1/invalid-vectors.json": (
        56435,
        "d2d700c1e553df907dc43be73e40881e0f937472dbe40c65c9b7d5556cab4bc6",
    ),
    "reference_corpus/contracts/identity/v1/invalid-vectors.sha256": (
        87,
        "32b5a8845243e5202464dbd09f6b06ee5dd750c69a8768fb5cea415f9e3a2fb7",
    ),
    "reference_corpus/contracts/identity/v1/manifest.json": (
        7586,
        "aafa6dee23971218f30f9c72f63e23741841f0852299bebf9f40471054cb760a",
    ),
    "reference_corpus/contracts/identity/v1/manifest.sha256": (
        80,
        "b5769ead5196aa7ea780be5920efc295d16673e93ecc010b45394aaa4bd58173",
    ),
    "reference_corpus/contracts/identity/v1/valid-vectors.json": (
        46891,
        "f58df3e6f123c468b8bc1f3185769e6d0773b4942a90207d7ec4fb37b26f8ef7",
    ),
    "reference_corpus/contracts/identity/v1/valid-vectors.sha256": (
        85,
        "912070e5f3772a59985a57d623e2ab16caadd70ca902bab2e0bd13183c15c33e",
    ),
    "reference_corpus/contracts/revision-locator/closures/s1-p02-phase-closure/closure.json": (
        100669,
        "daf3a89ef22bf20652d91cc96f476f1f31584ec90d860e57d1641c3ec6ab5a67",
    ),
    "reference_corpus/contracts/revision-locator/closures/s1-p02-phase-closure/closure.md": (
        7011,
        "6222f91445a6664f754c99ccc5c2dda946356f0840360a832066350206b7e870",
    ),
    "reference_corpus/contracts/revision-locator/closures/s1-p02-phase-closure/closure.sha256": (
        79,
        "8686b06e8fcc9a61841b0c35f2f33f4856e353e063ba1004a26831a141dc3ceb",
    ),
    "reference_corpus/contracts/revision-locator/v1/contract.md": (
        3718,
        "6500936787c93f8f818d197876bf91ef9b0fb4d9fbddd33772442c39a57e9ea8",
    ),
    "reference_corpus/contracts/revision-locator/v1/invalid-vectors.json": (
        99806,
        "832486482537b88fabad8efe6f6fb0f9a908e6ea29005dd9bbc60a44101d5944",
    ),
    "reference_corpus/contracts/revision-locator/v1/invalid-vectors.sha256": (
        87,
        "660285fe678b6d8ffd569eac96ca2225be201eb85f52fcc06a481e531c3121d9",
    ),
    "reference_corpus/contracts/revision-locator/v1/manifest.json": (
        8083,
        "56ba607a098744800ae94448982a0a3bab91fb4e7fba445a31406e2478dc1b80",
    ),
    "reference_corpus/contracts/revision-locator/v1/manifest.sha256": (
        80,
        "53b5655d5d3ed8004331dbded43a8b5f846cffa3c17e2788e1f02ad17c9dd92b",
    ),
    "reference_corpus/contracts/revision-locator/v1/replay-vectors.json": (
        21868,
        "bbf8d770eabe289a7d703e8185e0c9187ab63d4d18a93c5c817477facff06a8f",
    ),
    "reference_corpus/contracts/revision-locator/v1/replay-vectors.sha256": (
        86,
        "14e9f813dafe9f036c85f95e19cc74fed5e767a10fb16e5413f527c80e6d4d45",
    ),
    "reference_corpus/contracts/revision-locator/v1/valid-vectors.json": (
        123920,
        "59720c65e195e09c00cf89f86b4ce232628dbb64861c0d6c8065257f062de989",
    ),
    "reference_corpus/contracts/revision-locator/v1/valid-vectors.sha256": (
        85,
        "d4fef0eccdca723a2b377baef5bdc1571c296745c33bf6b39a37ea23f9b1cc42",
    ),
    "reference_corpus/pytest-4412/acquisitions/run-0001-s04-v1-base-4c9cde74-head-690a63b9/acquisition.json": (
        61283,
        "1c29093bf1537e9b824a18df1848b71a8da014f544bc9f385707eb0e000a1318",
    ),
    "reference_corpus/pytest-4412/acquisitions/run-0001-s04-v1-base-4c9cde74-head-690a63b9/artifacts/LICENSE": (
        1096,
        "a1ebce15afc7b5cf98c7c6de512d1959d4bf61db8c6bf2f111286d483b40a997",
    ),
    "reference_corpus/pytest-4412/acquisitions/run-0001-s04-v1-base-4c9cde74-head-690a63b9/artifacts/base-to-head.diff": (
        1640,
        "dca87a4df1edb2d1acb3fc821724483ee874c2feba6525b2c21e79cb3e8f7312",
    ),
    "reference_corpus/pytest-4412/closures/s1-p00-phase-closure/closure.json": (
        102190,
        "8c02d79c4a5a1d52b9fc2a3718e1b47888da6195588e62ab927388dbe972189e",
    ),
    "reference_corpus/pytest-4412/closures/s1-p00-phase-closure/closure.md": (
        13707,
        "fdb39ed8a7194f0becb5b4e2536cd883e47e6f291791c26269c45e188e66f2b1",
    ),
    "reference_corpus/pytest-4412/closures/s1-p00-phase-closure/closure.sha256": (
        79,
        "5b5a189c173c7366d8fe39526d3eda20d6f61cdfd9095e7c22758ec3e710866a",
    ),
    "reference_corpus/pytest-4412/corrections/s04-c01-acquisition-closure/correction.json": (
        60832,
        "44491ee512d2c2022110b83967fb6fa86d13045bc8404ea490d7a08b7aef24a2",
    ),
    "reference_corpus/pytest-4412/decisions/s07-identity-revision-provenance/decision.json": (
        85012,
        "60ecb66565525cb21a924508794635072ae50e935d4791d9d91da5b6399ce866",
    ),
    "reference_corpus/pytest-4412/decisions/s07-identity-revision-provenance/decision.md": (
        9553,
        "75c9c84f2069a5782241b9c28cb4e5c39f1368ccdabbc11e4bed9a204869e857",
    ),
    "reference_corpus/pytest-4412/decisions/s07-identity-revision-provenance/decision.sha256": (
        80,
        "a95d8f29afda95d1361d33a680694eb6618e9c5acaaf52afee5fe6678f34a891",
    ),
    "reference_corpus/pytest-4412/decisions/s08-snapshot-boundary-compatibility/decision.json": (
        46533,
        "f788116f3b9ea470c370a56e55eb6f37e05be200f285ac9f2572c641215f5f40",
    ),
    "reference_corpus/pytest-4412/decisions/s08-snapshot-boundary-compatibility/decision.md": (
        5679,
        "6a1a28b7a250f80206da9ff43900a912e3fd201dc7ffa09255660897e193e9e0",
    ),
    "reference_corpus/pytest-4412/decisions/s08-snapshot-boundary-compatibility/decision.sha256": (
        80,
        "7a87fd638e0ea08dc4e592373c754cdd9c385e54d1197978fcf90eb843057982",
    ),
    "src/faultatlas/__init__.py": (
        103,
        "7f88816f33b0efc700b25bfb7ad171ef00a3e5875d358e258d8e3d755e4d8489",
    ),
    "src/faultatlas/__main__.py": (
        125,
        "97a5e95d8d541e00eb0ceb84e73a28f28c3007643d80d3814945e04bedc41800",
    ),
    "src/faultatlas/cli.py": (
        820,
        "31e7edfea6a699fd75a4503a91beaf564b7257a4b69422acd6d81bfad59fd824",
    ),
    "src/faultatlas/domain/__init__.py": (
        57,
        "5cae5f36fe402a284ee13c9757b8b8415d2951711107890ce8c6c038fa8b05b5",
    ),
    "src/faultatlas/domain/compatibility.py": (
        18898,
        "f4ef93d432da4fd0ebf05237c164e10d8f18eceaf538ff4ddc3372565b5c46db",
    ),
    "src/faultatlas/domain/evidence.py": (
        123689,
        "824ed6ad86d243ccf920f07fe66af5d6bf060d6d80fafb7d60588dec8244e7ba",
    ),
    "src/faultatlas/domain/identity.py": (
        22684,
        "e2d604f4e86a3b94c2b1b1875fa6e8f408778cbadd829b3fe9e934dd53f2d169",
    ),
    "src/faultatlas/domain/revision.py": (
        27342,
        "7bea28086b345f6c1b4eeebe9c483924e60521e2f3e78954b272ab3c42acacaa",
    ),
    "src/faultatlas/domain/source.py": (
        4336,
        "034e53fd58212f0e34376bbc790fc3e74057031aaed4d7d89fb67904bdd380bf",
    ),
}

EXPECTED_MUTATIONS = (
    "closure-source-digest-drift",
    "missing-source-lock",
    "extra-source-lock",
    "reordered-slice-ledger",
    "duplicated-slice-id",
    "superseded-candidate-marked-published",
    "pr41-marked-unmerged",
    "reviewed-squash-tree-mismatch",
    "pr-main-ci-event-swap",
    "s07-corrective-misclassified-as-product-slice",
    "altered-vector-count",
    "altered-fixture-count",
    "altered-evidence-export-order",
    "nonzero-uncovered-leaf-count",
    "replay-dependency-cycle-claim",
    "universal-completeness-claim",
    "omitted-deferred-owner",
    "p04-marked-started",
    "p04-marked-ineligible",
    "production-reader-writer-persistence-claim",
    "durable-envelope-byte-claim",
    "fabricated-s09-publication-facts",
    "unexpected-production-module",
    "package-root-export-change",
    "modified-artifact-snapshot",
)


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _reject_number(value: str) -> NoReturn:
    raise AssertionError(f"non-integer JSON number is forbidden: {value}")


def _assert_no_float(value: Any) -> None:
    if isinstance(value, float):
        assert math.isfinite(value) and False, "floats are forbidden"
    if isinstance(value, dict):
        for item in cast(dict[str, Any], value).values():
            _assert_no_float(item)
    elif isinstance(value, list):
        for item in cast(list[Any], value):
            _assert_no_float(item)


def _canonical_bytes(value: Any) -> bytes:
    _assert_no_float(value)
    return (
        json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )
        + "\n"
    ).encode()


def _parse_canonical(raw: bytes) -> dict[str, Any]:
    assert raw.startswith(b"{") and raw.endswith(b"}\n")
    assert not raw.startswith(b"\xef\xbb\xbf")
    assert b"\r" not in raw
    parsed = json.loads(
        raw,
        parse_constant=_reject_number,
        parse_float=_reject_number,
    )
    assert isinstance(parsed, dict)
    _assert_no_float(parsed)
    assert _canonical_bytes(parsed) == raw
    return cast(dict[str, Any], parsed)


def _load_closure() -> dict[str, Any]:
    return _parse_canonical((CLOSURE_ROOT / "closure.json").read_bytes())


def _assert_regular_0644(path: Path) -> None:
    mode = path.lstat().st_mode
    assert stat.S_ISREG(mode)
    assert not stat.S_ISLNK(mode)
    assert stat.S_IMODE(mode) == 0o644


def _assert_closure_inventory() -> None:
    assert CLOSURE_ROOT.is_dir() and not CLOSURE_ROOT.is_symlink()
    observed = {path.name for path in CLOSURE_ROOT.iterdir()}
    assert observed == set(EXPECTED_CLOSURE_FILES)
    for name, (length, expected_digest) in EXPECTED_CLOSURE_FILES.items():
        path = CLOSURE_ROOT / name
        _assert_regular_0644(path)
        raw = path.read_bytes()
        assert len(raw) == length
        assert _sha256(raw) == expected_digest


def _assert_sidecar() -> None:
    primary = (CLOSURE_ROOT / "closure.json").read_bytes()
    sidecar = (CLOSURE_ROOT / "closure.sha256").read_bytes()
    assert sidecar == f"{_sha256(primary)}  closure.json\n".encode()
    assert re.fullmatch(rb"[0-9a-f]{64}  closure[.]json\n", sidecar) is not None


def _assert_structure(document: dict[str, Any]) -> None:
    assert set(document) == EXPECTED_TOP_LEVEL
    fmt = document["format"]
    assert fmt == {
        "authority_statement": "closure.json_is_the_sole_durable_semantic_authority_and_closure.md_is_derived_non_authoritative",
        "canonicalization": {
            "array_order": "preserved",
            "encoding": "UTF-8_without_BOM",
            "exactly_one_trailing_lf": True,
            "floats_NaN_and_Infinity_permitted": False,
            "keys": "sorted",
            "line_endings": "LF_only",
            "name": "json-sort-keys-compact-utf8-lf-v1",
            "whitespace": "compact",
        },
        "classification": "phase_closure",
        "internal": True,
        "name": "faultatlas-s1-p03-evidence-envelope-phase-closure",
        "public_contract": False,
        "publication_state": "sealed_publication_candidate",
        "sealed_at": "2026-08-12T08:47:39Z",
        "version": "1",
    }
    phase = document["phase_identity"]
    assert phase["stage"] == "S1"
    assert phase["phase"] == "S1.P03"
    assert phase["phase_name"] == "Evidence Envelope"
    assert phase["closure_slice"] == "S1.P03.S09"
    assert phase["synchronized_baseline_sha"] == (
        "8f00f5d05271430dc811d13600005a4cff81230f"
    )
    assert phase["synchronized_baseline_tree"] == (
        "9c7b06012146ed371e190d54b36ccdc42a79637e"
    )
    assert phase["predecessor_slice_state"] == (
        "S1.P03.S01_through_S1.P03.S08_complete"
    )
    assert phase["implementation_state"] == "sealed_publication_candidate"
    assert phase["next_phase"] == "S1.P04"
    assert phase["next_phase_implementation_state"] == "not_started"


def _assert_source_locks(document: dict[str, Any], *, verify_files: bool) -> None:
    section = document["source_locks"]
    immutable = section["immutable_inputs"]
    production = section["production_observations"]
    assert section["immutable_input_count"] == len(immutable) == 51
    assert section["production_observation_count"] == len(production) == 9
    assert section["total_lock_count"] == 60
    assert section["mutable_latest_or_current_pointer"] is False
    entries = immutable + production
    assert all(
        set(entry)
        == {
            "byte_length",
            "filesystem_mode",
            "git_mode",
            "group",
            "layer",
            "path",
            "sha256",
        }
        for entry in entries
    )
    observed = {
        entry["path"]: (entry["byte_length"], entry["sha256"]) for entry in entries
    }
    assert len(observed) == len(entries) == 60
    assert observed == EXPECTED_SOURCE_LOCKS
    assert [entry["path"] for entry in immutable] == sorted(
        entry["path"] for entry in immutable
    )
    assert [entry["path"] for entry in production] == sorted(
        entry["path"] for entry in production
    )
    assert [entry["path"] for entry in production] == list(EXPECTED_PRODUCTION_SOURCES)
    assert all(entry["git_mode"] == "100644" for entry in entries)
    assert all(entry["filesystem_mode"] == "0644" for entry in entries)
    if verify_files:
        for relative, (length, expected_digest) in EXPECTED_SOURCE_LOCKS.items():
            path = REPOSITORY_ROOT / relative
            _assert_regular_0644(path)
            raw = path.read_bytes()
            assert len(raw) == length
            assert _sha256(raw) == expected_digest


def _replay_git_commit(snapshot: dict[str, Any]) -> tuple[str, str]:
    assert set(snapshot) == {
        "byte_length",
        "content_base64",
        "encoding",
        "object_type",
        "sha1",
    }
    assert snapshot["encoding"] == "base64"
    assert snapshot["object_type"] == "commit"
    raw = base64.b64decode(snapshot["content_base64"], validate=True)
    assert len(raw) == snapshot["byte_length"]
    object_bytes = b"commit " + str(len(raw)).encode() + b"\0" + raw
    assert hashlib.sha1(object_bytes).hexdigest() == snapshot["sha1"]  # noqa: S324
    tree_match = re.match(rb"tree ([0-9a-f]{40})\n", raw)
    assert tree_match is not None
    return snapshot["sha1"], tree_match.group(1).decode()


def _replay_check_snapshot(
    snapshot: dict[str, Any], *, event: str, head_sha: str
) -> dict[str, Any]:
    assert snapshot["workflow"] == "CI"
    assert snapshot["event"] == event
    assert snapshot["head_sha"] == head_sha
    assert snapshot["attempt"] == 1
    assert snapshot["status"] == "completed"
    assert snapshot["conclusion"] == "success"
    assert snapshot["source_url"] == (
        f"https://github.com/MianliWang/FaultAtlas/actions/runs/{snapshot['run_id']}"
    )
    job = snapshot["job"]
    assert job["name"] == "validate"
    assert job["status"] == "completed"
    assert job["conclusion"] == "success"
    assert job["url"] == f"{snapshot['source_url']}/job/{job['job_id']}"
    assert all(
        step["status"] == "completed" and step["conclusion"] == "success"
        for step in job["steps"]
    )
    assert {
        "Check formatting",
        "Lint",
        "Type-check",
        "Test",
        "Build distributions",
        "Smoke-test package metadata and CLI",
    } <= {step["name"] for step in job["steps"]}
    replayed = {
        "attempt": snapshot["attempt"],
        "conclusion": snapshot["conclusion"],
        "context": job["name"],
        "event": snapshot["event"],
        "head_sha": snapshot["head_sha"],
        "job_id": job["job_id"],
        "run_id": snapshot["run_id"],
        "workflow": snapshot["workflow"],
    }
    if event == "push":
        assert snapshot["branch"] == "main"
        replayed["branch"] = snapshot["branch"]
    else:
        assert "branch" not in snapshot
    return replayed


def _replay_publication_evidence(section: dict[str, Any]) -> dict[int, Any]:
    snapshots = section["publication_evidence_snapshots"]
    assert snapshots["format"] == "faultatlas-bounded-publication-observation-snapshot"
    assert snapshots["version"] == "1"
    assert snapshots["repository"] == "MianliWang/FaultAtlas"
    assert snapshots["captured_at"] == "2026-08-12T08:47:39Z"
    assert snapshots["semantics"] == (
        "retained_bounded_observation_not_live_provider_or_complete_history"
    )
    assert snapshots["lock"] == (
        "canonical_snapshot_bytes_are_inside_closure.json_and_transitively_locked_by_closure.sha256"
    )
    assert snapshots["capture_sources"] == [
        "GitHub_GraphQL_pull_request_and_fully_paginated_review_connections",
        "GitHub_Actions_run_validate_job_and_step_observations",
        "raw_Git_commit_object_payloads",
    ]
    records = snapshots["records"]
    assert snapshots["record_count"] == len(records) == 9
    assert [record["pull_request_number"] for record in records] == list(
        EXPECTED_PUBLICATION_SLICES
    )
    replayed: dict[int, Any] = {}
    for record in records:
        number = record["pull_request_number"]
        pull_request = record["github_pull_request"]
        assert pull_request["number"] == number
        assert pull_request["source_url"] == (
            f"https://github.com/MianliWang/FaultAtlas/pull/{number}"
        )
        assert pull_request["state"] == "MERGED"
        assert pull_request["merged"] is True
        assert re.fullmatch(
            r"2026-08-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z",
            pull_request["merged_at"],
        )
        reviewed_sha, reviewed_tree = _replay_git_commit(
            record["git_commit_objects"]["reviewed_head"]
        )
        squash_sha, squash_tree = _replay_git_commit(
            record["git_commit_objects"]["squash_revision"]
        )
        assert pull_request["head_ref_oid"] == reviewed_sha
        assert pull_request["final_reviewed_commit"] == {
            "oid": reviewed_sha,
            "tree_oid": reviewed_tree,
        }
        assert pull_request["merge_commit"] == {
            "oid": squash_sha,
            "tree_oid": squash_tree,
        }
        assert reviewed_tree == squash_tree
        reviews = pull_request["reviews"]
        threads = pull_request["review_threads"]
        requests = pull_request["review_requests"]
        comments = pull_request["conversation_comments"]
        assert all(
            connection["page_complete"] is True
            for connection in (reviews, threads, requests, comments)
        )
        assert reviews["total_count"] == len(reviews["nodes"])
        assert threads["total_count"] == len(threads["nodes"])
        assert requests["total_count"] == 0
        assert len({review["id"] for review in reviews["nodes"]}) == len(
            reviews["nodes"]
        )
        assert len({thread["id"] for thread in threads["nodes"]}) == len(
            threads["nodes"]
        )
        assert all(
            thread["comments_page_complete"] is True for thread in threads["nodes"]
        )
        changes_requested = sum(
            review["state"] == "CHANGES_REQUESTED" for review in reviews["nodes"]
        )
        unresolved = sum(not thread["is_resolved"] for thread in threads["nodes"])
        assert changes_requested == 0
        assert unresolved == 0
        pr_check = _replay_check_snapshot(
            record["pull_request_check"], event="pull_request", head_sha=reviewed_sha
        )
        main_check = _replay_check_snapshot(
            record["main_check"], event="push", head_sha=squash_sha
        )
        replayed[number] = {
            "main_check": main_check,
            "pull_request_check": pr_check,
            "review_settlement": {
                "actionable_unresolved_thread_count": unresolved,
                "changes_requested_count": changes_requested,
                "review_count": reviews["total_count"],
                "review_request_count": requests["total_count"],
                "settlement": "clean",
                "thread_count": threads["total_count"],
            },
            "reviewed_head": reviewed_sha,
            "reviewed_tree": reviewed_tree,
            "squash_revision": squash_sha,
            "squash_tree": squash_tree,
        }
    return replayed


def _assert_ledger(document: dict[str, Any]) -> None:
    section = document["slice_ledger"]
    entries = section["entries"]
    publications = section["publications"]
    assert section["entry_count"] == len(entries) == 9
    assert section["publication_count"] == len(publications) == 9
    assert [
        (item["slice_id"], item["title"]) for item in entries
    ] == EXPECTED_SLICE_TITLES
    assert [item["ordinal"] for item in entries] == list(range(1, 10))
    assert [item["state"] for item in entries] == [
        *(["complete_published"] * 8),
        "sealed_publication_candidate",
    ]
    assert len({item["slice_id"] for item in entries}) == 9
    publication_ids = {item["id"] for item in publications}
    assert len(publication_ids) == len(publications)
    assert {
        identifier for entry in entries for identifier in entry["publication_ids"]
    } == publication_ids
    assert entries[-1]["publication_ids"] == []
    by_pr = {item["pull_request"]: item for item in publications}
    replayed = _replay_publication_evidence(section)
    assert set(by_pr) == set(replayed) == set(EXPECTED_PUBLICATION_SLICES)
    for pull_request, (slice_id, classification) in EXPECTED_PUBLICATION_SLICES.items():
        item = by_pr[pull_request]
        evidence = replayed[pull_request]
        assert item["slice_id"] == slice_id
        assert item["classification"] == classification
        assert item["reviewed_head"] == evidence["reviewed_head"]
        assert item["reviewed_tree"] == evidence["reviewed_tree"]
        assert item["squash_revision"] == evidence["squash_revision"]
        assert item["squash_tree"] == evidence["squash_tree"]
        assert item["reviewed_tree_equals_squash_tree"] is True
        assert item["publication_state"] == "merged"
        assert item["merge_method"] == "protected_pull_request_squash_merge"
        pr_check = evidence["pull_request_check"]
        main_check = evidence["main_check"]
        assert item["pull_request_check"] == pr_check
        assert item["main_check"] == main_check
        assert pr_check["run_id"] != main_check["run_id"]
        assert pr_check["job_id"] != main_check["job_id"]
        assert item["review_settlement"] == evidence["review_settlement"]
    assert by_pr[38]["classification"] == "test_assurance_corrective_publication"
    assert by_pr[38]["slice_id"] == "S1.P03.S07"
    candidates = section["superseded_candidates"]
    assert [item["pull_request"] for item in candidates] == [39, 40]
    assert [item["head_sha"] for item in candidates] == [
        "ea571865fe23c17a47fb5e34a5d212c3ea8ff215",
        "e9d7d0036aae58af4820617d35ba51888ed62187",
    ]
    assert [item["unresolved_historical_thread_count"] for item in candidates] == [
        3,
        1,
    ]
    assert [item["thread_count"] for item in candidates] == [12, 4]
    for item in candidates:
        assert item["state"] == "closed"
        assert item["merged"] is False
        assert item["status"] == (
            "superseded_publication_candidate_not_a_slice_publication"
        )
        assert item["historical_threads_intentionally_preserved"] is True


def _assert_inventory(document: dict[str, Any]) -> None:
    section = document["implementation_inventory"]
    assert section["production_source_count"] == 9
    assert section["production_sources"] == list(EXPECTED_PRODUCTION_SOURCES)
    assert section["no_tenth_production_module"] is True
    assert section["evidence_export_count"] == 58
    assert section["evidence_exports"] == list(EXPECTED_EVIDENCE_EXPORTS)
    assert tuple(
        __import__("faultatlas.domain.evidence", fromlist=["__all__"]).__all__
    ) == (EXPECTED_EVIDENCE_EXPORTS)
    assert section["package_root_exports"] == ["__version__"]
    assert faultatlas.__all__ == ["__version__"]
    assert section["package_version"] == faultatlas.__version__ == "0.1.0"
    legacy = section["legacy_models"]
    assert legacy["SourceLocator"]["fields"] == list(SourceLocator.model_fields)
    assert legacy["SourceLocator"]["unchanged"] is True
    assert legacy["ArtifactSnapshot"]["field_count"] == 10
    assert legacy["ArtifactSnapshot"]["fields"] == list(ArtifactSnapshot.model_fields)
    assert legacy["ArtifactSnapshot"]["unchanged"] is True
    assert set(section["absent_capabilities"]) == {
        "production_contract_corpus_reader",
        "production_contract_corpus_writer",
        "production_contract_corpus_validator",
        "production_EvidenceEnvelope_reader",
        "production_EvidenceEnvelope_writer",
        "persistence",
        "storage",
        "migration",
        "format_registry",
        "durable_EvidenceEnvelope_bytes",
    }


def _assert_corpus(document: dict[str, Any], *, verify_files: bool) -> None:
    section = document["contract_corpus_assurance"]
    expected_files = {
        "contract.md",
        "invalid-vectors.json",
        "invalid-vectors.sha256",
        "manifest.json",
        "manifest.sha256",
        "replay-vectors.json",
        "replay-vectors.sha256",
        "valid-vectors.json",
        "valid-vectors.sha256",
    }
    assert section["directory"] == "reference_corpus/contracts/evidence-envelope/v1"
    assert section["version"] == "1"
    assert section["corpus_id"] == "faultatlas-evidence-envelope-contract-corpus"
    assert section["manifest_format"] == (
        "faultatlas-evidence-envelope-contract-corpus-manifest"
    )
    assert section["file_count"] == len(section["files"]) == 9
    assert set(section["files"]) == expected_files
    assert section["file_modes"] == "100644"
    assert section["canonical_json_files"] == [
        "invalid-vectors.json",
        "manifest.json",
        "replay-vectors.json",
        "valid-vectors.json",
    ]
    assert section["sidecar_count"] == 4
    assert section["vector_counts"] == {
        "fixtures": 20,
        "invalid": 135,
        "replay": 15,
        "total": 279,
        "valid": 129,
    }
    assert section["fixtures"] == 20
    assert section["evidence_export_coverage"] == {
        "accounted_for": 58,
        "expected": 58,
    }
    assert all(
        section[key] is True
        for key in (
            "unknown_marker_rejected",
            "unknown_operation_rejected",
            "unknown_target_rejected",
            "package_excluded",
            "no_production_capability",
        )
    )
    assert section["test_only_executor"] == "tests/test_evidence_contract_corpus.py"
    if verify_files:
        assert {path.name for path in CORPUS_ROOT.iterdir()} == expected_files
        for filename in section["canonical_json_files"]:
            _parse_canonical((CORPUS_ROOT / filename).read_bytes())
        for filename in (
            "invalid-vectors",
            "manifest",
            "replay-vectors",
            "valid-vectors",
        ):
            primary = (CORPUS_ROOT / f"{filename}.json").read_bytes()
            sidecar = (CORPUS_ROOT / f"{filename}.sha256").read_bytes()
            assert sidecar == f"{_sha256(primary)}  {filename}.json\n".encode()


def _assert_integration(document: dict[str, Any]) -> None:
    section = document["integration_assurance"]
    assert section["invariant_count"] == section["passed_count"] == 23
    invariants = section["invariants"]
    assert len(invariants) == 23
    assert [item["invariant_id"] for item in invariants] == [
        f"integration:{index:02d}" for index in range(1, 24)
    ]
    assert all(item["status"] == "passed" for item in invariants)
    assert len({item["subject"] for item in invariants}) == 23
    boundary = document["semantic_boundaries"]
    assert boundary["canonical_transformation_count"] == 0
    assert boundary["canonical_supersession_count"] == 0
    assert boundary["canonical_correction_count"] == 1
    assert boundary["canonical_publication_order"] == [
        "s1-p00-s04-acquisition-publication",
        "s1-p00-s04-c01-correction-publication",
    ]
    assert boundary["completeness_scope"] == (
        "declared_17_requirement_scope_not_universal_history"
    )
    assert boundary["future_durable_production_record_bytes"] == "owned_by_S1.P10"


def _assert_replay(document: dict[str, Any]) -> None:
    section = document["replay_assurance"]
    assert section["non_synthetic_replay_instances"] == 9
    assert section["semantic_leaves"] == 2354
    assert section["primary_proof_ownership"] == {
        "ambiguous_primary_owners": 0,
        "bounded_source_projection": 255,
        "deterministic_derivation": 1,
        "reviewed_contract_literal": 195,
        "slice_authored_contract": 253,
        "verified_child_replay": 1572,
        "verified_retained_bytes": 78,
    }
    assert section["corroborated_leaves"] == 14
    assert section["uncovered_leaves"] == 0
    assert section["proof_rules"] == 244
    assert section["replay_dependency_graph"] == {
        "acyclic": True,
        "edge_count": 8,
        "maximum_depth": 3,
        "transitive_verification": True,
    }
    assert section["fact_graph"] == {
        "derived_nodes": 16,
        "maximum_depth": 2,
        "projected_roots": 48,
    }
    assert section["authored_fact_labels"] == 9
    assert section["mutation_probes"] == 103


def _assert_legacy(document: dict[str, Any]) -> None:
    section = document["legacy_compatibility_assurance"]
    assert section["selected_strategy"] == "preserve_v1_behind_outer_wrapper"
    assert section["adapter_id"] == "legacy-artifact-snapshot-v1-envelope-adapter"
    assert section["adapter_version"] == "1"
    assert section["legacy_model_field_count"] == 10
    assert section["legacy_source_and_byte_equality"] is True
    assert section["legacy_wrapping"] == ("losslessly_mappable_exact_source_preserved")
    assert section["exact_legacy_only_projection"] == "losslessly_mappable"
    assert section["modern_information_projection"] == "partially_mappable"
    assert section["known_empty_modern_inventory_projection"] == ("partially_mappable")
    assert section["no_snapshot_projection"] == "not_mappable"
    assert section["multiple_snapshot_projection"] == "not_mappable"
    assert section["canonical_current_projection"] == {
        "projected_snapshot": None,
        "reason": "legacy_snapshot_absent",
        "status": "not_mappable",
    }
    assert section["no_SourceLocator_resolution"] is True
    assert section["no_modern_identity_or_provenance_fabrication"] is True


def _assert_exit_deferred_readiness(document: dict[str, Any]) -> None:
    exits = document["exit_criteria"]
    assert exits["count"] == exits["satisfied_count"] == 24
    assert exits["unsatisfied_count"] == 0
    assert len(exits["items"]) == 24
    assert [item["criterion_id"] for item in exits["items"]] == [
        f"exit:{index:02d}" for index in range(1, 25)
    ]
    assert all(item["status"] == "satisfied" for item in exits["items"])
    assert len({item["subject"] for item in exits["items"]}) == 24
    for item in exits["items"]:
        assert item["evidence"].split(".", 1)[0] in document

    deferred = document["deferred_register"]
    assert deferred["count"] == len(deferred["entries"]) == 14
    assert deferred["ownership_complete"] is True
    assert [item["deferred_id"] for item in deferred["entries"]] == [
        f"deferred:{index:02d}" for index in range(1, 15)
    ]
    assert [item["owner"] for item in deferred["entries"]] == [
        "S1.P04",
        "S1.P05",
        "S1.P06",
        "S1.P07",
        "S1.P08",
        "S1.P09",
        "S1.P10",
        "S2",
        "S3/S4",
        "S5",
        "S6",
        "S7",
        "S8",
        "S9",
    ]
    assert all(
        item["implementation_state"] == "not_implemented"
        for item in deferred["entries"]
    )

    readiness = document["entry_readiness"]
    assert readiness["next_phase"] == "S1.P04"
    assert readiness["readiness"] == "eligible_to_begin"
    assert readiness["implementation_state"] == "not_started"
    assert readiness["unresolved_blocker_count"] == 0
    assert readiness["prerequisite_count"] == len(readiness["prerequisites"]) == 9
    assert [item["prerequisite_id"] for item in readiness["prerequisites"]] == [
        f"p04-entry:{index:02d}" for index in range(1, 10)
    ]
    assert all(item["status"] == "satisfied" for item in readiness["prerequisites"])


def _assert_publication_boundary(document: dict[str, Any]) -> None:
    contract = document["publication_contract"]
    assert contract == {
        "actual_S09_publication_facts_in_candidate": False,
        "admin_or_ruleset_bypass": "forbidden",
        "direct_main_push": "forbidden",
        "exact_reviewed_head_required": True,
        "future_publication_evidence_location": "Git_history_GitHub_and_final_execution_report",
        "linear_history_required": True,
        "natural_main_CI_required": True,
        "protected_ready_pull_request_required": True,
        "protected_squash_merge_required": True,
        "required_check": "validate",
        "required_workflow": "CI",
        "review_settlement_required": True,
        "reviewed_tree_squash_tree_equality_required": True,
        "topic_branch": "feat/s1-p03-s09-evidence-phase-closure",
    }
    s09 = document["slice_ledger"]["entries"][-1]
    assert set(s09) == {"ordinal", "publication_ids", "slice_id", "state", "title"}
    assert s09["slice_id"] == "S1.P03.S09"
    assert s09["publication_ids"] == []
    assert s09["state"] == "sealed_publication_candidate"


def _assert_scope(document: dict[str, Any]) -> None:
    non_generalizations = document["non_generalizations"]
    assert non_generalizations["count"] == len(non_generalizations["items"]) == 13
    subjects = [item["subject"] for item in non_generalizations["items"]]
    assert subjects == [
        "universal_cross_provider_schema",
        "complete_GitHub_history",
        "private_hidden_or_permission_filtered_record_completeness",
        "GitHub_Enterprise_support",
        "non_Git_provider_support",
        "arbitrary_non_UTF8_Git_path_support",
        "persistence_or_storage",
        "public_stable_API",
        "durable_EvidenceEnvelope_bytes",
        "production_contract_corpus_loading",
        "confidence_or_review_correctness",
        "repository_snapshot_correctness",
        "fault_pattern_transferability",
    ]
    assurance = document["assurance"]
    assert assurance["no_production_change"] is True
    assert assurance["no_unresolved_P03_product_blockers"] is True
    assert assurance["P04_readiness"] == "eligible_to_begin"
    assert assurance["P04_implementation_state"] == "not_started"


def _assert_test_assurance(document: dict[str, Any]) -> None:
    section = document["test_assurance"]
    assert section == {
        "baseline_full_pytest_count": 4554,
        "candidate_full_pytest_count": 4600,
        "closure_suite_test_count": 46,
        "documentation": "roadmap_and_pytest_4412_case_transition_required_and_tested",
        "mutation_probe_count": 25,
        "mutation_probes": list(EXPECTED_MUTATIONS),
        "package_exclusion": "wheel_and_sdist_independent_archive_inspection_required",
        "primary_suite": "tests/test_evidence_phase_closure.py",
        "validation_state": "local_validation_passed",
    }


def _validate_document(document: dict[str, Any]) -> None:
    _assert_structure(document)
    _assert_source_locks(document, verify_files=False)
    _assert_ledger(document)
    _assert_inventory(document)
    _assert_corpus(document, verify_files=False)
    _assert_integration(document)
    _assert_replay(document)
    _assert_legacy(document)
    _assert_exit_deferred_readiness(document)
    _assert_publication_boundary(document)
    _assert_scope(document)
    _assert_test_assurance(document)


def _fixture_values(document: dict[str, Any]) -> dict[str, Any]:
    return {item["id"]: item["value"] for item in document["fixtures"]}


def _resolve_fixtures(value: Any, fixtures: dict[str, Any]) -> Any:
    if isinstance(value, dict):
        mapping = cast(dict[str, Any], value)
        if set(mapping) == {"fixture_ref"}:
            reference = cast(str, mapping["fixture_ref"])
            assert reference in fixtures
            return _resolve_fixtures(copy.deepcopy(fixtures[reference]), fixtures)
        return {key: _resolve_fixtures(item, fixtures) for key, item in mapping.items()}
    if isinstance(value, list):
        return [_resolve_fixtures(item, fixtures) for item in cast(list[Any], value)]
    return value


def _canonical_envelope() -> EvidenceEnvelope:
    document = _parse_canonical(REPLAY_PATH.read_bytes())
    fixtures = _fixture_values(document)
    payload = fixtures["evidence.fixture.replay.envelope.canonical-current"]
    return EvidenceEnvelope.model_validate_json(
        json.dumps(payload, separators=(",", ":"), sort_keys=True)
    )


def _walk_leaves(value: Any, prefix: str = "") -> dict[str, Any]:
    if isinstance(value, dict):
        mapping = cast(dict[str, Any], value)
        if not mapping:
            return {prefix or "/": {}}
        result: dict[str, Any] = {}
        for key in sorted(mapping):
            result.update(_walk_leaves(mapping[key], f"{prefix}/{key}"))
        return result
    if isinstance(value, list):
        items = cast(list[Any], value)
        if not items:
            return {prefix or "/": []}
        result = {}
        for index, item in enumerate(items):
            result.update(_walk_leaves(item, f"{prefix}/{index}"))
        return result
    return {prefix or "/": value}


def _pattern_matches(pattern: str, path: str) -> bool:
    expected = pattern.split("/")
    actual = path.split("/")
    if len(expected) != len(actual):
        return False
    for want, have in zip(expected, actual):
        if want.startswith("#"):
            if not have.isdigit():
                return False
            bounds = want[1:]
            if bounds:
                low, high = bounds.split("-", 1)
                if not int(low) <= int(have) <= int(high):
                    return False
        elif want != have:
            return False
    return True


def _replay_models() -> tuple[dict[str, Any], list[tuple[dict[str, Any], BaseModel]]]:
    document = _parse_canonical(REPLAY_PATH.read_bytes())
    fixtures = _fixture_values(document)
    targets: dict[str, type[BaseModel]] = {
        "AcquisitionRun": AcquisitionRun,
        "EvidenceCorrection": EvidenceCorrection,
        "EvidenceCompletenessAssessment": EvidenceCompletenessAssessment,
        "EvidencePublication": EvidencePublication,
    }
    results: list[tuple[dict[str, Any], BaseModel]] = []
    for vector in document["vectors"]:
        if vector["evidence_classification"] == "synthetic_contract_example":
            continue
        resolved = _resolve_fixtures(vector["input"], fixtures)
        operation = vector["operation"]
        if operation == "replay_artifact":
            model = ExactArtifactIdentity.model_validate_json(
                json.dumps(resolved["artifact_identity"])
            )
        elif operation == "replay_record":
            model = targets[vector["target_symbol"]].model_validate_json(
                json.dumps(resolved["record"])
            )
        else:
            assert operation in {"replay_envelope", "adapter_project"}
            model = EvidenceEnvelope.model_validate_json(
                json.dumps(resolved["envelope"])
            )
        results.append((vector, model))
    return document, results


def _independent_leaf_metrics() -> dict[str, Any]:
    _, results = _replay_models()
    proof_counts: Counter[str] = Counter()
    corroborated = 0
    proof_rules = 0
    children: dict[str, list[str]] = {}
    projected_roots = 0
    derived_nodes = 0
    authored_labels = 0
    max_fact_depth = 0
    for vector, model in results:
        leaves = _walk_leaves(model.model_dump(mode="json", round_trip=True))
        paths = set(leaves)
        expected = vector["expected"]
        derivations = expected.get("derivations", [])
        derived_facts = {item["fact"] for item in derivations}
        primary: dict[str, str] = {}
        corroborations: set[str] = set()
        vector_children: list[str] = []
        for rule in expected["leaf_proofs"]:
            proof_rules += 1
            if rule["kind"] == "child":
                subtree = rule["subtree"]
                matched = {
                    path
                    for path in paths
                    if path == subtree or path.startswith(f"{subtree}/")
                }
                proof_kind = "verified_child_replay"
                vector_children.append(rule["vector"])
            else:
                matched = {
                    path for path in paths if _pattern_matches(rule["pattern"], path)
                }
                proof_kind = {
                    "authored": "slice_authored_contract",
                    "bytes": "verified_retained_bytes",
                    "contract_literal": "reviewed_contract_literal",
                    "source": "bounded_source_projection",
                }.get(rule["kind"])
                if rule["kind"] == "fact":
                    proof_kind = (
                        "deterministic_derivation"
                        if rule["fact"] in derived_facts
                        else "bounded_source_projection"
                    )
            assert matched
            if rule.get("corroborates", False):
                corroborations |= matched
                continue
            assert not (set(primary) & matched)
            for path in matched:
                assert proof_kind is not None
                primary[path] = proof_kind
                proof_counts[proof_kind] += 1
        assert set(primary) == paths
        corroborated += len(corroborations)
        children[vector["id"]] = vector_children
        projected_roots += len(
            {
                projection["fact"]
                for pointer in vector["source_pointers"]
                for projection in pointer["projections"]
            }
        )
        derived_nodes += len(derivations)
        authored_labels += len(expected.get("authored_labels", []))
        depths: dict[str, int] = {}
        for derivation in derivations:
            operands = [
                value
                for key, value in derivation.items()
                if key != "fact" and key.endswith("_fact") and isinstance(value, str)
            ]
            for key, value in derivation.items():
                if key.endswith("_facts") and isinstance(value, list):
                    raw_operands = cast(list[object], value)
                    assert all(isinstance(item, str) for item in raw_operands)
                    operands.extend(cast(list[str], raw_operands))
            depths[derivation["fact"]] = 1 + max(
                (depths.get(item, 0) for item in operands), default=0
            )
        max_fact_depth = max(max_fact_depth, max(depths.values(), default=0))

    def dependency_depth(vector_id: str, stack: tuple[str, ...] = ()) -> int:
        assert vector_id not in stack
        return (
            0
            if not children[vector_id]
            else 1
            + max(
                dependency_depth(child, (*stack, vector_id))
                for child in children[vector_id]
            )
        )

    return {
        "authored_labels": authored_labels,
        "corroborated": corroborated,
        "derived_nodes": derived_nodes,
        "fact_depth": max_fact_depth,
        "leaves": sum(
            len(_walk_leaves(model.model_dump(mode="json", round_trip=True)))
            for _, model in results
        ),
        "non_synthetic": len(results),
        "primary": dict(proof_counts),
        "projected_roots": projected_roots,
        "proof_rules": proof_rules,
        "replay_depth": max(dependency_depth(vector_id) for vector_id in children),
        "replay_edges": sum(len(value) for value in children.values()),
    }


def _assert_archive_sources(members: dict[str, bytes], *, wheel: bool) -> None:
    expected = {
        relative.removeprefix("src/"): (REPOSITORY_ROOT / relative).read_bytes()
        for relative in CURRENT_PRODUCTION_SOURCES
    }
    observed: dict[str, bytes] = {}
    for name, data in members.items():
        parts = Path(name).parts
        assert "reference_corpus" not in parts
        assert "s1-p03-phase-closure" not in name
        assert "evidence-envelope" not in name
        if wheel:
            if name.startswith("faultatlas/") and name.endswith(".py"):
                observed[name] = data
            assert not name.startswith("tests/")
        else:
            for index, part in enumerate(parts):
                if part == "src" and parts[index + 1 : index + 2] == ("faultatlas",):
                    relative = "/".join(parts[index + 1 :])
                    if relative.endswith(".py"):
                        observed[relative] = data
    assert observed == expected
    historical_license = (
        REPOSITORY_ROOT / "reference_corpus/pytest-4412/acquisitions/"
        "run-0001-s04-v1-base-4c9cde74-head-690a63b9/artifacts/LICENSE"
    ).read_bytes()
    assert historical_license not in members.values()
    project_license = (REPOSITORY_ROOT / "LICENSE").read_bytes()
    assert project_license in members.values()


def test_closure_artifacts_are_exact_canonical_regular_and_non_executable() -> None:
    _assert_closure_inventory()
    _parse_canonical((CLOSURE_ROOT / "closure.json").read_bytes())
    _assert_sidecar()


def test_closure_git_modes_are_or_will_be_100644() -> None:
    for filename in EXPECTED_CLOSURE_FILES:
        relative = f"{CLOSURE_RELATIVE}/{filename}"
        output = subprocess.run(
            ["git", "ls-files", "-s", "--", relative],
            cwd=REPOSITORY_ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        if output:
            assert output.split(maxsplit=1)[0] == "100644"
        else:
            _assert_regular_0644(REPOSITORY_ROOT / relative)


def test_markdown_is_digest_synchronized_and_non_authoritative() -> None:
    document = _load_closure()
    raw = (CLOSURE_ROOT / "closure.json").read_bytes()
    markdown = (CLOSURE_ROOT / "closure.md").read_text(encoding="utf-8")
    assert f"Primary JSON SHA-256: `{_sha256(raw)}`" in markdown
    for heading in (
        "## Executive Phase-closure verdict",
        "## Ordered Slice and publication ledger",
        "## Contract corpus and replay assurance",
        "## Cross-layer integration assurance",
        "## Deferred ownership",
        "## S1.P04 entry readiness",
        "## Publication boundary",
    ):
        assert heading in markdown
    assert "sole durable semantic authority" in markdown
    assert "derived, non-authoritative view" in markdown
    assert "S1.P04 remains `not_started`" in markdown
    assert str(document["replay_assurance"]["semantic_leaves"])[0] in markdown


def test_closure_structure_phase_identity_and_repeat_serialization_are_exact() -> None:
    document = _load_closure()
    _assert_structure(document)
    assert _canonical_bytes(document) == _canonical_bytes(
        _parse_canonical(_canonical_bytes(document))
    )


def test_all_sixty_source_locks_are_independently_hard_locked() -> None:
    _assert_source_locks(_load_closure(), verify_files=True)


def test_slice_ledger_publications_superseded_history_and_review_are_exact() -> None:
    _assert_ledger(_load_closure())


def test_implementation_inventory_exports_and_legacy_models_are_exact() -> None:
    _assert_inventory(_load_closure())


def test_s08_contract_corpus_counts_integrity_and_package_boundary_are_locked() -> None:
    _assert_corpus(_load_closure(), verify_files=True)
    valid = _parse_canonical((CORPUS_ROOT / "valid-vectors.json").read_bytes())
    invalid = _parse_canonical((CORPUS_ROOT / "invalid-vectors.json").read_bytes())
    replay = _parse_canonical(REPLAY_PATH.read_bytes())
    assert (len(valid["vectors"]), len(invalid["vectors"]), len(replay["vectors"])) == (
        129,
        135,
        15,
    )
    assert sum(len(item["fixtures"]) for item in (valid, invalid, replay)) == 20


def test_replay_leaf_metrics_are_independently_recomputed() -> None:
    metrics = _independent_leaf_metrics()
    assert metrics == {
        "authored_labels": 9,
        "corroborated": 14,
        "derived_nodes": 16,
        "fact_depth": 2,
        "leaves": 2354,
        "non_synthetic": 9,
        "primary": {
            "bounded_source_projection": 255,
            "deterministic_derivation": 1,
            "reviewed_contract_literal": 195,
            "slice_authored_contract": 253,
            "verified_child_replay": 1572,
            "verified_retained_bytes": 78,
        },
        "projected_roots": 48,
        "proof_rules": 244,
        "replay_depth": 3,
        "replay_edges": 8,
    }
    _assert_replay(_load_closure())


def test_canonical_envelope_reconstructs_exact_cross_layer_composition() -> None:
    envelope = _canonical_envelope()
    assert envelope.legacy_snapshots is None
    assert envelope.request_memberships is None
    assert len(envelope.acquisition_runs or ()) == 1
    assert envelope.transformations == ()
    assert len(envelope.record_relationships or ()) == 1
    assert len(envelope.completeness_assessments or ()) == 1
    assert len(envelope.publications or ()) == 2
    run = cast(tuple[AcquisitionRun, ...], envelope.acquisition_runs)[0]
    assert run.status.value == "complete"
    assert run.request_count == 32
    assert [
        request.request_id.request_ordinal.root for request in run.requests
    ] == list(range(1, 33))
    assert all(request.request_reference is None for request in run.requests)
    assert all(request.request_controls is None for request in run.requests)
    assert all(request.response_observation is None for request in run.requests)
    assert [len(request.retained_artifacts or ()) for request in run.requests] == [
        *([0] * 29),
        1,
        0,
        1,
    ]
    correction = cast(tuple[EvidenceCorrection, ...], envelope.record_relationships)[0]
    assert isinstance(correction, EvidenceCorrection)
    assert correction.target_record != correction.correction_record
    assessment = cast(
        tuple[EvidenceCompletenessAssessment, ...],
        envelope.completeness_assessments,
    )[0]
    assert assessment.subject_record == correction.target_record
    assert assessment.status.value == "scope_satisfied_with_declared_omissions"
    assert len(assessment.requirements) == 17
    assert [item.outcome.value for item in assessment.requirements[:2]] == [
        "satisfied",
        "satisfied",
    ]
    assert all(
        item.outcome.value == "intentionally_omitted"
        for item in assessment.requirements[2:]
    )
    publications = cast(tuple[EvidencePublication, ...], envelope.publications)
    assert [item.publication_id.root for item in publications] == [
        "s1-p00-s04-acquisition-publication",
        "s1-p00-s04-c01-correction-publication",
    ]
    assert [item.subject_record for item in publications] == [
        correction.target_record,
        correction.correction_record,
    ]
    assert all(item.reviewed_tree == item.published_tree for item in publications)


def test_request_representation_artifact_status_and_relationship_layers_are_distinct() -> (
    None
):
    assert "request_id" in RetrievalRequestReference.model_fields
    assert "requested_media_type" in RetrievalRequestControls.model_fields
    assert "observed_media_type" in ResponseRepresentationObservation.model_fields
    assert "requested_media_type" not in ResponseRepresentationObservation.model_fields
    assert "observed_media_type" not in RetrievalRequestControls.model_fields
    assert set(ExactArtifactIdentity.model_fields) == {
        "schema_version",
        "digest",
        "byte_length",
    }
    forbidden_artifact_fields = {
        "response",
        "git_object",
        "path",
        "storage",
        "location",
    }
    assert forbidden_artifact_fields.isdisjoint(ExactArtifactIdentity.model_fields)
    assert "status" in AcquisitionRun.model_fields
    assert "status" in EvidenceCompletenessAssessment.model_fields
    assert AcquisitionRun.model_fields["status"].annotation != (
        EvidenceCompletenessAssessment.model_fields["status"].annotation
    )
    assert EvidenceTransformation is not EvidenceCorrection
    assert EvidenceCorrection is not EvidenceSupersession
    assert set(EvidenceCorrection.model_fields) != set(
        EvidenceSupersession.model_fields
    )


def test_none_known_empty_and_nonempty_envelope_states_remain_distinct() -> None:
    envelope = _canonical_envelope()
    payload = envelope.model_dump(mode="json", round_trip=True)
    assert payload["request_memberships"] is None
    assert payload["transformations"] == []
    assert payload["acquisition_runs"]
    none_transformations = EvidenceEnvelope.model_validate_json(
        json.dumps({**payload, "transformations": None})
    )
    assert none_transformations.transformations is None
    assert none_transformations != envelope


def test_retained_artifact_identities_terminate_in_exact_bytes() -> None:
    envelope = _canonical_envelope()
    run = cast(tuple[AcquisitionRun, ...], envelope.acquisition_runs)[0]
    observed = {
        retained.artifact_identity.digest.scope.root: retained.artifact_identity
        for request in run.requests
        for retained in request.retained_artifacts or ()
    }
    paths = {
        "github-compare-diff-http-entity-body": REPOSITORY_ROOT
        / "reference_corpus/pytest-4412/acquisitions/"
        "run-0001-s04-v1-base-4c9cde74-head-690a63b9/artifacts/base-to-head.diff",
        "git-blob-content": REPOSITORY_ROOT
        / "reference_corpus/pytest-4412/acquisitions/"
        "run-0001-s04-v1-base-4c9cde74-head-690a63b9/artifacts/LICENSE",
    }
    assert set(observed) == set(paths)
    for scope, path in paths.items():
        raw = path.read_bytes()
        identity = observed[scope]
        assert identity.byte_length.root == len(raw)
        assert identity.digest.value.root == _sha256(raw)


def test_legacy_adapter_is_exact_source_preserving_and_fail_closed() -> None:
    replay = _parse_canonical(REPLAY_PATH.read_bytes())
    fixture = next(
        item["value"]
        for item in replay["fixtures"]
        if item["id"] == "evidence.fixture.replay.snapshot.synthetic-one"
    )
    snapshot = ArtifactSnapshot.model_validate_json(json.dumps(fixture))
    wrapped = wrap_legacy_artifact_snapshot(snapshot)
    assert wrapped.source_snapshot == snapshot
    assert wrapped.envelope.legacy_snapshots == (snapshot,)
    assert wrapped.status.value == "losslessly_mappable"
    assert wrapped.reasons == ()
    exact = project_evidence_envelope_to_legacy_artifact_snapshot(wrapped.envelope)
    assert exact.status.value == "losslessly_mappable"
    assert exact.projected_snapshot == snapshot
    modern_known_empty = EvidenceEnvelope.model_validate_json(
        json.dumps(
            {
                **wrapped.envelope.model_dump(mode="json", round_trip=True),
                "transformations": [],
            }
        )
    )
    partial = project_evidence_envelope_to_legacy_artifact_snapshot(modern_known_empty)
    assert partial.status.value == "partially_mappable"
    assert partial.projected_snapshot is None
    canonical = project_evidence_envelope_to_legacy_artifact_snapshot(
        _canonical_envelope()
    )
    assert canonical.status.value == "not_mappable"
    assert canonical.projected_snapshot is None
    assert [reason.value for reason in canonical.reasons] == ["legacy_snapshot_absent"]
    _assert_legacy(_load_closure())


def test_all_cross_layer_invariants_and_semantic_boundaries_are_explicit() -> None:
    _assert_integration(_load_closure())


def test_exit_criteria_deferred_owners_and_p04_readiness_are_complete() -> None:
    _assert_exit_deferred_readiness(_load_closure())


def test_publication_contract_has_no_fabricated_s09_publication_facts() -> None:
    _assert_publication_boundary(_load_closure())


def test_privacy_non_generalizations_and_scope_are_fail_closed() -> None:
    document = _load_closure()
    _assert_scope(document)
    raw = (CLOSURE_ROOT / "closure.json").read_bytes()
    for forbidden in (
        b"/home/",
        b"/tmp/",
        b"Authorization:",
        b"BEGIN PRIVATE KEY",
        b"github_pat_",
        b"ghp_",
    ):
        assert forbidden not in raw
    assert b"private_hidden_or_permission_filtered_record_completeness" in raw
    assert b"complete_GitHub_history" in raw
    assert b"raw_provider_response" not in raw


def test_roadmap_advances_p04_while_case_preserves_p03_closure_state() -> None:
    roadmap = " ".join(
        (REPOSITORY_ROOT / "docs/roadmap.md").read_text(encoding="utf-8").split()
    )
    case = " ".join(
        (REPOSITORY_ROOT / "docs/reference_cases/pytest-4412.md")
        .read_text(encoding="utf-8")
        .split()
    )
    assert "`S1.P03` is complete" in roadmap
    assert (
        "`S1.P03.S09` — Integration and Phase Closure (complete; closes `S1.P03`)"
        in roadmap
    )
    assert "`S1.P04` is active and incomplete" in roadmap
    assert "`S1.P04.S01` is complete" in roadmap
    assert "`S1.P04.S02` is complete" in roadmap
    assert "`S1.P04.S03` is complete" in roadmap
    assert "`S1.P04.S04` is complete" in roadmap
    assert "`S1.P04.S05` is complete" in roadmap
    assert "`S1.P04.S06` is complete" in roadmap
    assert "`S1.P04.S07` is complete" in roadmap
    assert "`S1.P04.S08` is complete" in roadmap
    assert "`S1.P04.S09` is next and not started" in roadmap
    assert "`S1.P05` through `S1.P10` remain not started" in roadmap
    assert "**S2-S9** are not implemented" in roadmap
    assert CLOSURE_RELATIVE in case
    assert "S1.P04" in case and "eligible to begin" in case
    assert "S1.P04 remains not started" in case
    assert "sealed publication candidate" in case


def test_actual_offline_build_excludes_closure_corpus_and_tests(tmp_path: Path) -> None:
    output = tmp_path / "dist"
    environment = os.environ.copy()
    environment.update(
        {
            "PYTHONDONTWRITEBYTECODE": "1",
            "UV_MANAGED_PYTHON": "1",
            "UV_NO_SYNC": "1",
            "UV_OFFLINE": "1",
        }
    )
    subprocess.run(
        [
            "uv",
            "build",
            "--offline",
            "--no-create-gitignore",
            "--out-dir",
            str(output),
        ],
        cwd=REPOSITORY_ROOT,
        env=environment,
        check=True,
        capture_output=True,
        text=True,
    )
    wheel = next(output.glob("*.whl"))
    sdist = next(output.glob("*.tar.gz"))
    with zipfile.ZipFile(wheel) as archive:
        wheel_members = {
            info.filename: archive.read(info)
            for info in archive.infolist()
            if not info.is_dir()
        }
    with tarfile.open(sdist, "r:gz") as archive:
        sdist_members = {
            member.name: cast(Any, archive.extractfile(member)).read()
            for member in archive.getmembers()
            if member.isfile()
        }
    _assert_archive_sources(wheel_members, wheel=True)
    _assert_archive_sources(sdist_members, wheel=False)


@pytest.mark.parametrize("mutation", EXPECTED_MUTATIONS)
def test_each_required_closure_mutation_is_rejected(mutation: str) -> None:
    document = copy.deepcopy(_load_closure())
    if mutation == "closure-source-digest-drift":
        document["source_locks"]["immutable_inputs"][0]["sha256"] = "0" * 64
    elif mutation == "missing-source-lock":
        document["source_locks"]["immutable_inputs"].pop()
    elif mutation == "extra-source-lock":
        extra = copy.deepcopy(document["source_locks"]["immutable_inputs"][0])
        extra["path"] = "reference_corpus/extra.json"
        document["source_locks"]["immutable_inputs"].append(extra)
        document["source_locks"]["immutable_input_count"] += 1
        document["source_locks"]["total_lock_count"] += 1
    elif mutation == "reordered-slice-ledger":
        document["slice_ledger"]["entries"][0:2] = reversed(
            document["slice_ledger"]["entries"][0:2]
        )
    elif mutation == "duplicated-slice-id":
        document["slice_ledger"]["entries"][1]["slice_id"] = "S1.P03.S01"
    elif mutation == "superseded-candidate-marked-published":
        document["slice_ledger"]["superseded_candidates"][0]["status"] = (
            "complete_published"
        )
    elif mutation == "pr41-marked-unmerged":
        next(
            item
            for item in document["slice_ledger"]["publications"]
            if item["pull_request"] == 41
        )["publication_state"] = "closed_unmerged"
    elif mutation == "reviewed-squash-tree-mismatch":
        document["slice_ledger"]["publications"][0]["squash_tree"] = "0" * 40
    elif mutation == "pr-main-ci-event-swap":
        publication = document["slice_ledger"]["publications"][0]
        publication["pull_request_check"]["event"] = "push"
        publication["main_check"]["event"] = "pull_request"
    elif mutation == "s07-corrective-misclassified-as-product-slice":
        next(
            item
            for item in document["slice_ledger"]["publications"]
            if item["pull_request"] == 38
        )["classification"] = "product_slice_publication"
    elif mutation == "altered-vector-count":
        document["contract_corpus_assurance"]["vector_counts"]["valid"] += 1
    elif mutation == "altered-fixture-count":
        document["contract_corpus_assurance"]["fixtures"] += 1
    elif mutation == "altered-evidence-export-order":
        exports = document["implementation_inventory"]["evidence_exports"]
        exports[0], exports[1] = exports[1], exports[0]
    elif mutation == "nonzero-uncovered-leaf-count":
        document["replay_assurance"]["uncovered_leaves"] = 1
    elif mutation == "replay-dependency-cycle-claim":
        document["replay_assurance"]["replay_dependency_graph"]["acyclic"] = False
    elif mutation == "universal-completeness-claim":
        document["semantic_boundaries"]["completeness_scope"] = (
            "universal_provider_history"
        )
    elif mutation == "omitted-deferred-owner":
        document["deferred_register"]["entries"].pop()
    elif mutation == "p04-marked-started":
        document["entry_readiness"]["implementation_state"] = "started"
    elif mutation == "p04-marked-ineligible":
        document["entry_readiness"]["readiness"] = "ineligible"
    elif mutation == "production-reader-writer-persistence-claim":
        document["implementation_inventory"]["absent_capabilities"] = []
    elif mutation == "durable-envelope-byte-claim":
        document["semantic_boundaries"]["future_durable_production_record_bytes"] = (
            "implemented_by_S1.P03"
        )
    elif mutation == "fabricated-s09-publication-facts":
        document["slice_ledger"]["entries"][-1]["future_pull_request"] = 42
    elif mutation == "unexpected-production-module":
        document["implementation_inventory"]["production_sources"].append(
            "src/faultatlas/domain/repository_snapshot.py"
        )
    elif mutation == "package-root-export-change":
        document["implementation_inventory"]["package_root_exports"].append(
            "EvidenceEnvelope"
        )
    else:
        assert mutation == "modified-artifact-snapshot"
        document["implementation_inventory"]["legacy_models"]["ArtifactSnapshot"][
            "fields"
        ].append("storage_path")
    with pytest.raises(AssertionError):
        _validate_document(document)


def test_complete_closure_document_passes_every_independent_validator() -> None:
    _validate_document(_load_closure())
