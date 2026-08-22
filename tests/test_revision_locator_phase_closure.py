from __future__ import annotations

import ast
import copy
import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import tarfile
import zipfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, NoReturn, cast

import pytest

import faultatlas
import faultatlas.domain as domain_package
from faultatlas.domain import revision as revision_module

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
CLOSURE_RELATIVE = (
    "reference_corpus/contracts/revision-locator/closures/s1-p02-phase-closure"
)
CLOSURE_ROOT = REPOSITORY_ROOT / CLOSURE_RELATIVE
CORPUS_ROOT = REPOSITORY_ROOT / "reference_corpus/contracts/revision-locator/v1"
RETAINED_DIFF = (
    REPOSITORY_ROOT / "reference_corpus/pytest-4412/acquisitions/"
    "run-0001-s04-v1-base-4c9cde74-head-690a63b9/artifacts/base-to-head.diff"
)

EXPECTED_CLOSURE_FILES = {"closure.json", "closure.md", "closure.sha256"}
EXPECTED_JSON_BYTES = 100669
EXPECTED_JSON_SHA256 = (
    "daf3a89ef22bf20652d91cc96f476f1f31584ec90d860e57d1641c3ec6ab5a67"
)
EXPECTED_SIDECAR_BYTES = 79
EXPECTED_SIDECAR_SHA256 = (
    "8686b06e8fcc9a61841b0c35f2f33f4856e353e063ba1004a26831a141dc3ceb"
)
EXPECTED_MARKDOWN_BYTES = 7011
EXPECTED_MARKDOWN_SHA256 = (
    "6222f91445a6664f754c99ccc5c2dda946356f0840360a832066350206b7e870"
)
EXPECTED_FORMAT = "faultatlas-s1-p02-revision-qualified-locators-phase-closure"
EXPECTED_VERSION = "1"
EXPECTED_BASELINE = "b96575ebb2246321ec33804b301169fe11134da9"
EXPECTED_BASELINE_TREE = "3f07cac197460242c9c3b60b98acb5a86bafbcc8"
EXPECTED_TOP_LEVEL = {
    "assurance",
    "contract_corpus_assurance",
    "deferred_register",
    "entry_readiness",
    "established_findings",
    "exit_criteria",
    "format",
    "implementation_inventory",
    "non_generalizations",
    "phase_identity",
    "publication_contract",
    "replay_assurance",
    "semantic_boundaries",
    "slice_ledger",
    "source_locks",
    "test_assurance",
}


@dataclass(frozen=True)
class LockedFile:
    byte_length: int
    sha256: str


EXPECTED_SOURCE_LOCKS = {
    "reference_corpus/pytest-4412/closures/s1-p00-phase-closure/closure.json": LockedFile(
        102190, "8c02d79c4a5a1d52b9fc2a3718e1b47888da6195588e62ab927388dbe972189e"
    ),
    "reference_corpus/pytest-4412/closures/s1-p00-phase-closure/closure.sha256": LockedFile(
        79, "5b5a189c173c7366d8fe39526d3eda20d6f61cdfd9095e7c22758ec3e710866a"
    ),
    "reference_corpus/pytest-4412/closures/s1-p00-phase-closure/closure.md": LockedFile(
        13707, "fdb39ed8a7194f0becb5b4e2536cd883e47e6f291791c26269c45e188e66f2b1"
    ),
    "reference_corpus/contracts/identity/closures/s1-p01-phase-closure/closure.json": LockedFile(
        112606, "2c1bfb9d3d596711066796ef83999d49b6846e65315a301eead7fa8fb5ac4642"
    ),
    "reference_corpus/contracts/identity/closures/s1-p01-phase-closure/closure.sha256": LockedFile(
        79, "8c1bc1ff60ef2ae25f0bca5abd696708b9a59b2fadd15bd7586a9fb868c262ae"
    ),
    "reference_corpus/contracts/identity/closures/s1-p01-phase-closure/closure.md": LockedFile(
        3847, "cfde27cbd9d8d1fc979ffb3d878999663cc52a25e5f07d60b70b2791e69292ca"
    ),
    "reference_corpus/pytest-4412/decisions/s07-identity-revision-provenance/decision.json": LockedFile(
        85012, "60ecb66565525cb21a924508794635072ae50e935d4791d9d91da5b6399ce866"
    ),
    "reference_corpus/pytest-4412/decisions/s07-identity-revision-provenance/decision.sha256": LockedFile(
        80, "a95d8f29afda95d1361d33a680694eb6618e9c5acaaf52afee5fe6678f34a891"
    ),
    "reference_corpus/pytest-4412/decisions/s07-identity-revision-provenance/decision.md": LockedFile(
        9553, "75c9c84f2069a5782241b9c28cb4e5c39f1368ccdabbc11e4bed9a204869e857"
    ),
    "reference_corpus/pytest-4412/decisions/s08-snapshot-boundary-compatibility/decision.json": LockedFile(
        46533, "f788116f3b9ea470c370a56e55eb6f37e05be200f285ac9f2572c641215f5f40"
    ),
    "reference_corpus/pytest-4412/decisions/s08-snapshot-boundary-compatibility/decision.sha256": LockedFile(
        80, "7a87fd638e0ea08dc4e592373c754cdd9c385e54d1197978fcf90eb843057982"
    ),
    "reference_corpus/pytest-4412/decisions/s08-snapshot-boundary-compatibility/decision.md": LockedFile(
        5679, "6a1a28b7a250f80206da9ff43900a912e3fd201dc7ffa09255660897e193e9e0"
    ),
    "reference_corpus/contracts/revision-locator/v1/manifest.json": LockedFile(
        8083, "56ba607a098744800ae94448982a0a3bab91fb4e7fba445a31406e2478dc1b80"
    ),
    "reference_corpus/contracts/revision-locator/v1/manifest.sha256": LockedFile(
        80, "53b5655d5d3ed8004331dbded43a8b5f846cffa3c17e2788e1f02ad17c9dd92b"
    ),
    "reference_corpus/contracts/revision-locator/v1/valid-vectors.json": LockedFile(
        123920, "59720c65e195e09c00cf89f86b4ce232628dbb64861c0d6c8065257f062de989"
    ),
    "reference_corpus/contracts/revision-locator/v1/valid-vectors.sha256": LockedFile(
        85, "d4fef0eccdca723a2b377baef5bdc1571c296745c33bf6b39a37ea23f9b1cc42"
    ),
    "reference_corpus/contracts/revision-locator/v1/invalid-vectors.json": LockedFile(
        99806, "832486482537b88fabad8efe6f6fb0f9a908e6ea29005dd9bbc60a44101d5944"
    ),
    "reference_corpus/contracts/revision-locator/v1/invalid-vectors.sha256": LockedFile(
        87, "660285fe678b6d8ffd569eac96ca2225be201eb85f52fcc06a481e531c3121d9"
    ),
    "reference_corpus/contracts/revision-locator/v1/replay-vectors.json": LockedFile(
        21868, "bbf8d770eabe289a7d703e8185e0c9187ab63d4d18a93c5c817477facff06a8f"
    ),
    "reference_corpus/contracts/revision-locator/v1/replay-vectors.sha256": LockedFile(
        86, "14e9f813dafe9f036c85f95e19cc74fed5e767a10fb16e5413f527c80e6d4d45"
    ),
    "reference_corpus/contracts/revision-locator/v1/contract.md": LockedFile(
        3718, "6500936787c93f8f818d197876bf91ef9b0fb4d9fbddd33772442c39a57e9ea8"
    ),
    "reference_corpus/pytest-4412/acquisitions/run-0001-s04-v1-base-4c9cde74-head-690a63b9/artifacts/base-to-head.diff": LockedFile(
        1640, "dca87a4df1edb2d1acb3fc821724483ee874c2feba6525b2c21e79cb3e8f7312"
    ),
}

EXPECTED_CORPUS_FILES = {
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

EXPECTED_PRODUCTION = {
    "src/faultatlas/__init__.py": LockedFile(
        103, "7f88816f33b0efc700b25bfb7ad171ef00a3e5875d358e258d8e3d755e4d8489"
    ),
    "src/faultatlas/__main__.py": LockedFile(
        125, "97a5e95d8d541e00eb0ceb84e73a28f28c3007643d80d3814945e04bedc41800"
    ),
    "src/faultatlas/cli.py": LockedFile(
        820, "31e7edfea6a699fd75a4503a91beaf564b7257a4b69422acd6d81bfad59fd824"
    ),
    "src/faultatlas/domain/__init__.py": LockedFile(
        57, "5cae5f36fe402a284ee13c9757b8b8415d2951711107890ce8c6c038fa8b05b5"
    ),
    "src/faultatlas/domain/source.py": LockedFile(
        4336, "034e53fd58212f0e34376bbc790fc3e74057031aaed4d7d89fb67904bdd380bf"
    ),
    "src/faultatlas/domain/identity.py": LockedFile(
        22684, "e2d604f4e86a3b94c2b1b1875fa6e8f408778cbadd829b3fe9e934dd53f2d169"
    ),
    "src/faultatlas/domain/compatibility.py": LockedFile(
        18898, "f4ef93d432da4fd0ebf05237c164e10d8f18eceaf538ff4ddc3372565b5c46db"
    ),
    "src/faultatlas/domain/revision.py": LockedFile(
        27342, "7bea28086b345f6c1b4eeebe9c483924e60521e2f3e78954b272ab3c42acacaa"
    ),
}

EVIDENCE_MODULE = "src/faultatlas/domain/evidence.py"
SNAPSHOT_MODULE = "src/faultatlas/domain/snapshot.py"
SNAPSHOT_EVIDENCE_LINK_MODULE = "src/faultatlas/domain/snapshot_evidence_link.py"
CURRENT_PRODUCTION_FILES = {
    *EXPECTED_PRODUCTION,
    EVIDENCE_MODULE,
    SNAPSHOT_MODULE,
    SNAPSHOT_EVIDENCE_LINK_MODULE,
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
FORBIDDEN_POST_S07_EVIDENCE_SURFACE_FRAGMENTS = (
    "confidence",
    "corpus",
    "migration",
    "persistence",
    "reader",
    "registry",
    "repositorysnapshot",
    "review",
    "storage",
    "writer",
)

EXPECTED_EXPORTS = (
    "GitHashAlgorithm",
    "GitObjectKind",
    "GitCommitIdentity",
    "GitTreeIdentity",
    "GitBlobIdentity",
    "GitObjectIdentity",
    "GitRevisionIdentity",
    "RevisionRole",
    "RevisionRoleAssignment",
    "GitCommitParentTopology",
    "GitRefNamespace",
    "GitRefName",
    "GitRefObservation",
    "GitRepositoryPath",
    "RevisionQualifiedPath",
    "TextEncoding",
    "LineEnding",
    "OneBasedInclusiveLineSpan",
    "ZeroBasedHalfOpenByteSpan",
    "RevisionLineLocator",
    "ArtifactByteLocator",
    "DiffHunkLocator",
    "BoundedLocator",
)

EXPECTED_LEDGER = (
    (
        "S1.P02.S01",
        24,
        "d5e779c9aa34dc7a686bab8066c09e4d78d8267b",
        "c0b2e944ac8a92aa38cfca686c5552d6e5b3a605",
        "3759a87dd4376660d2b470ea92b373e9267eb5e7",
        30687963289,
        91337385699,
        30688084078,
        91337701950,
        1166,
    ),
    (
        "S1.P02.S02",
        25,
        "07173a0e38a830f31dc3070ff79f010124be23fb",
        "724722f88a98c96360665d46e4bf0cd45e407c2b",
        "a2aa200357c99bab61e45b8307451533954650b3",
        30690184255,
        91343389856,
        30690295809,
        91343686923,
        1270,
    ),
    (
        "S1.P02.S03",
        26,
        "7e3ede17e80f7a69968b1a61fbc0a2bcad365782",
        "d6adf0dede5a55ab9018684e9668bf11691e486c",
        "4c7123a46f5de43e782db7dbc6b5786888212ab2",
        30692113747,
        91348543281,
        30692350418,
        91349193668,
        1425,
    ),
    (
        "S1.P02.S04",
        27,
        "47f65982a40b8764df34a048c83934e47a4be754",
        "7ee0f80ad4b04c1055e3b990ce83d92dc3aa8d57",
        "7aeab56d6b3077b8f1c57b80335a55980f80e16f",
        30694477215,
        91354844012,
        30694582118,
        91355129387,
        1601,
    ),
    (
        "S1.P02.S05",
        28,
        "4dcd2148dd33e5f1685426f3e923ffc6d41cf71a",
        "327da2ca96f200faaf56c15a73accdec01d94e76",
        "577ee3726c60fb3b8d99772bd17b6fe067c064bd",
        30711272901,
        91399062607,
        30711673005,
        91400123838,
        1855,
    ),
    (
        "S1.P02.S06",
        29,
        "0e8b1aba586a8e946749157e6dd5dce44eb5c58f",
        "3f07cac197460242c9c3b60b98acb5a86bafbcc8",
        "b96575ebb2246321ec33804b301169fe11134da9",
        30716531073,
        91412909708,
        30716664962,
        91413261177,
        2159,
    ),
)

EXPECTED_BOUNDARIES = {
    "boundary:01-object-kind-vs-revision-role",
    "boundary:02-immutable-revision-vs-mutable-ref",
    "boundary:03-ref-vs-repository-alias",
    "boundary:04-topology-vs-role",
    "boundary:05-repository-path-vs-host-path",
    "boundary:06-qualified-path-vs-locator",
    "boundary:07-line-vs-byte",
    "boundary:08-diff-artifact-vs-file-sides",
    "boundary:09-coordinate-vs-interpretation",
    "boundary:10-artifact-digest-vs-Git-object",
    "boundary:11-locator-vs-resolver",
    "boundary:12-corpus-vs-production-wire",
}
EXPECTED_CRITERIA = {f"exit:{number:02d}" for number in range(1, 67)}
EXPECTED_FINDINGS = {f"finding:{number:02d}" for number in range(1, 31)}
EXPECTED_NON_GENERALIZATIONS = {
    f"non-generalization:{number:02d}" for number in range(1, 42)
}
EXPECTED_DEFERRED = {f"deferred:{number:02d}" for number in range(1, 43)}
EXPECTED_PREREQUISITES = {f"p03-entry:{number:02d}" for number in range(1, 25)}
EXPECTED_CHANGED_PATHS = (
    f"{CLOSURE_RELATIVE}/closure.json",
    f"{CLOSURE_RELATIVE}/closure.sha256",
    f"{CLOSURE_RELATIVE}/closure.md",
    "tests/test_revision_locator_phase_closure.py",
    "tests/test_identity_phase_closure.py",
    "tests/test_reference_corpus_phase_closure.py",
    "tests/test_revision_locator_contract_corpus.py",
    "tests/test_bounded_locators.py",
    "docs/roadmap.md",
    "docs/reference_cases/pytest-4412.md",
)
EXPECTED_EXTERNAL_COMPLETION_CONDITIONS = (
    "protected_S07_ready_pull_request",
    "exact_PR_head_validate_success",
    "all_actionable_review_threads_resolved",
    "squash_merge_tree_equals_reviewed_PR_head_tree",
    "natural_main_CI_success_for_exact_squash_SHA",
    "complete_test_suite_success_on_main",
    "package_exclusion_and_replay_assurance_success_on_main",
    "clean_synchronized_local_main",
)
EXPECTED_GRAPH_PREDECESSORS = {
    "source:s07-decision": [],
    "source:s08-decision": ["source:s07-decision"],
    "source:p00-closure": ["source:s07-decision", "source:s08-decision"],
    "source:p01-closure": ["source:p00-closure"],
    "publication:s01": ["source:p01-closure"],
    "publication:s02": ["publication:s01"],
    "publication:s03": ["publication:s02"],
    "publication:s04": ["publication:s03"],
    "publication:s05": ["publication:s04"],
    "source:retained-diff": [],
    "source:s06-corpus": ["publication:s05", "source:retained-diff"],
    "publication:s06": ["source:s06-corpus"],
    "observation:production": ["publication:s06"],
}
EXPECTED_P03_ALLOWED = (
    "source_and_authority_references",
    "retrieval_request_records",
    "response_representation_observations",
    "acquisition_run_records",
    "exact_retained_artifact_records",
    "representation_artifact_distinction",
    "media_and_encoding_observations",
    "digest_algorithm_and_scope",
    "transformation_records",
    "correction_and_supersession_records",
    "omission_and_completeness_records",
    "publication_provenance",
    "outer_Evidence_Envelope_composition",
    "identity_revision_locator_references_to_evidence_subjects",
)
EXPECTED_P03_FORBIDDEN = (
    "repository_snapshot_aggregation",
    "development_history_graph",
    "fault_instances",
    "patterns_and_invariants",
    "transfer_scoring",
    "claim_confidence_and_review",
    "persistence",
    "retrieval_or_RAG",
    "public_service_APIs",
)
EXPECTED_DEFERRED_STATE_TOTALS = {
    "evidence_insufficient": 4,
    "implementation_deferred": 12,
    "provisional_design": 23,
    "unsupported_current_scope": 3,
}
EXPECTED_OWNER_TOTALS = {
    "S1.P03": 16,
    "S1.P04": 4,
    "S1.P05": 4,
    "S1.P08": 4,
    "S1.P09": 5,
    "S1.P10": 9,
}
EXPECTED_MARKDOWN_HEADINGS = (
    "# S1.P02 Revision-qualified Locators Phase Closure",
    "## Exact primary JSON digest",
    "## Executive Phase-closure verdict",
    "## Phase identity and scope",
    "## S01–S07 ordered ledger",
    "## Production implementation inventory",
    "## Revision-locator corpus assurance",
    "## Exact retained-diff replay assurance",
    "## Semantic boundaries",
    "## Test, source, permission, and package assurance",
    "## Exit criteria summary",
    "## Established findings",
    "## Non-generalizations",
    "## Deferred-register summary",
    "## S1.P03 entry readiness",
    "## S1.P03 scope guard",
    "## Candidate publication conditions",
    "## S1.P03 remains not started",
    "## Derived and non-authoritative warning",
    "## Non-universal closure-schema warning",
)

REQUIRED_MUTATIONS = (
    "changed-closure-json-byte",
    "coordinated-json-sidecar-reseal",
    "uppercase-sidecar-digest",
    "wrong-sidecar-basename",
    "missing-terminal-lf",
    "extra-terminal-lf",
    "non-canonical-json",
    "broken-p00-lock",
    "broken-p01-lock",
    "broken-revision-locator-corpus-lock",
    "broken-retained-diff-lock",
    "missing-ledger-entry",
    "duplicate-ledger-id",
    "reordered-ledger",
    "fabricated-s07-pr-identifier",
    "criterion-unsatisfied",
    "required-criterion-removed",
    "deferred-missing-immediate-owner",
    "deferred-missing-long-term-owner",
    "completed-p02-behavior-marked-unresolved",
    "p03-marked-started",
    "p03-marked-ineligible",
    "candidate-marked-published",
    "source-lock-self-reference",
    "source-lock-cycle",
    "mutable-latest-pointer",
    "unexpected-production-source",
    "missing-production-source",
    "missing-revision-export",
    "unexpected-revision-export",
    "package-root-revision-export",
    "production-corpus-reader-inserted",
    "locator-resolver-inserted",
    "replay-vector-total-changed",
    "selected-byte-digest-changed",
    "evidence-classification-changed",
    "coordinate-convention-changed",
    "closure-filesystem-mode-0755",
    "closure-filesystem-mode-0600",
    "closure-git-mode-100755",
    "closure-symlink",
    "synthetic-package-closure-member",
    "historical-pytest-license-inserted",
    "evidence-envelope-production-surface-inserted",
)
assert len(REQUIRED_MUTATIONS) == 44


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _reject_float(_value: str) -> NoReturn:
    raise AssertionError("floating-point JSON is forbidden")


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        assert key not in result, f"duplicate JSON key: {key}"
        result[key] = value
    return result


def _canonical_bytes(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
        + b"\n"
    )


def _parse_canonical(raw: bytes) -> dict[str, Any]:
    assert not raw.startswith(b"\xef\xbb\xbf")
    assert b"\r" not in raw
    assert raw.endswith(b"\n") and not raw.endswith(b"\n\n")
    value = json.loads(
        raw,
        object_pairs_hook=_unique_object,
        parse_float=_reject_float,
        parse_constant=_reject_float,
    )
    assert isinstance(value, dict)
    assert _canonical_bytes(value) == raw
    return cast(dict[str, Any], value)


def _load_closure() -> dict[str, Any]:
    return _parse_canonical((CLOSURE_ROOT / "closure.json").read_bytes())


def _assert_primary(raw: bytes) -> dict[str, Any]:
    assert len(raw) == EXPECTED_JSON_BYTES
    assert _sha256(raw) == EXPECTED_JSON_SHA256
    return _parse_canonical(raw)


def _assert_sidecar(raw: bytes, primary: bytes) -> None:
    assert len(raw) == EXPECTED_SIDECAR_BYTES
    assert _sha256(raw) == EXPECTED_SIDECAR_SHA256
    assert raw == f"{_sha256(primary)}  closure.json\n".encode()
    assert re.fullmatch(rb"[0-9a-f]{64}  closure[.]json\n", raw) is not None


def _assert_safe_relative(relative: str) -> None:
    path = PurePosixPath(relative)
    assert not path.is_absolute()
    assert ".." not in path.parts
    assert "\\" not in relative


def _assert_regular_0644(path: Path) -> None:
    mode = path.lstat().st_mode
    assert not stat.S_ISLNK(mode)
    assert stat.S_ISREG(mode)
    assert stat.S_IMODE(mode) == 0o644


def _parse_git_stage(raw: bytes) -> dict[str, str]:
    modes: dict[str, str] = {}
    for entry in raw.rstrip(b"\0").split(b"\0") if raw else ():
        metadata, encoded_path = entry.split(b"\t", maxsplit=1)
        mode, _object_id, stage = metadata.decode().split()
        assert stage == "0"
        modes[encoded_path.decode()] = mode
    return modes


def _git_modes(
    paths: set[str], environment: dict[str, str] | None = None
) -> dict[str, str]:
    result = subprocess.run(
        ["git", "ls-files", "--stage", "-z", "--", *sorted(paths)],
        cwd=REPOSITORY_ROOT,
        env=environment,
        check=True,
        capture_output=True,
    )
    return _parse_git_stage(result.stdout)


def _prospective_modes(paths: set[str], tmp_path: Path) -> dict[str, str]:
    environment = os.environ.copy()
    environment["GIT_INDEX_FILE"] = str(tmp_path / "prospective-index")
    subprocess.run(
        ["git", "read-tree", "HEAD"],
        cwd=REPOSITORY_ROOT,
        env=environment,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "update-index", "--info-only", "--add", "--", *sorted(paths)],
        cwd=REPOSITORY_ROOT,
        env=environment,
        check=True,
        capture_output=True,
    )
    return _git_modes(paths, environment)


def _assert_git_modes(modes: dict[str, str], expected: set[str]) -> None:
    assert set(modes) == expected
    assert set(modes.values()) == {"100644"}


def _validate_graph(graph: dict[str, Any]) -> None:
    assert graph["node_count"] == 13
    assert graph["edge_count"] == 13
    assert graph["root_ids"] == ["source:s07-decision", "source:retained-diff"]
    nodes = cast(list[dict[str, Any]], graph["nodes"])
    node_ids = [cast(str, node["id"]) for node in nodes]
    assert len(nodes) == len(node_ids) == len(set(node_ids)) == graph["node_count"]
    for node in nodes:
        parents = cast(list[str], node["predecessors"])
        assert len(parents) == len(set(parents))
    assert (
        sum(len(cast(list[str], node["predecessors"])) for node in nodes)
        == (graph["edge_count"])
    )
    predecessors = {
        cast(str, node["id"]): cast(list[str], node["predecessors"]) for node in nodes
    }
    assert len(predecessors) == graph["node_count"]
    assert predecessors == EXPECTED_GRAPH_PREDECESSORS
    assert set(graph["root_ids"]) == {
        node_id for node_id, parents in predecessors.items() if not parents
    }
    visited: set[str] = set()
    active: set[str] = set()

    def visit(node_id: str) -> None:
        assert node_id in predecessors
        assert node_id not in active, "source-lock cycle"
        if node_id in visited:
            return
        active.add(node_id)
        for predecessor in predecessors[node_id]:
            visit(predecessor)
        active.remove(node_id)
        visited.add(node_id)

    for node_id in predecessors:
        visit(node_id)
    assert visited == set(predecessors)
    assert graph["acyclic"] is True


def _expected_source_node(relative: str) -> str:
    if relative.startswith("reference_corpus/pytest-4412/closures/s1-p00"):
        return "source:p00-closure"
    if relative.startswith("reference_corpus/contracts/identity/closures/s1-p01"):
        return "source:p01-closure"
    if relative.startswith(
        "reference_corpus/pytest-4412/decisions/s07-identity-revision-provenance/"
    ):
        return "source:s07-decision"
    if relative.startswith(
        "reference_corpus/pytest-4412/decisions/s08-snapshot-boundary-compatibility/"
    ):
        return "source:s08-decision"
    if relative.startswith("reference_corpus/contracts/revision-locator/v1/"):
        return "source:s06-corpus"
    if relative == RETAINED_DIFF.relative_to(REPOSITORY_ROOT).as_posix():
        return "source:retained-diff"
    raise AssertionError(f"unmapped immutable source: {relative}")


def _assert_source_locks(document: dict[str, Any], verify_files: bool = False) -> None:
    source = cast(dict[str, Any], document["source_locks"])
    items = cast(list[dict[str, Any]], source["immutable_inputs"])
    paths = [cast(str, item["path"]) for item in items]
    assert (
        len(items) == len(paths) == len(set(paths)) == source["immutable_input_count"]
    )
    assert source["immutable_input_count"] == len(EXPECTED_SOURCE_LOCKS) == 22
    observed = {
        cast(str, item["path"]): LockedFile(
            cast(int, item["byte_length"]), cast(str, item["sha256"])
        )
        for item in items
    }
    assert observed == EXPECTED_SOURCE_LOCKS
    assert source["self_reference"] is False
    assert source["mutable_pointer"] is False
    assert all(CLOSURE_RELATIVE not in relative for relative in observed)
    _validate_graph(cast(dict[str, Any], source["dependency_graph"]))
    graph_nodes = {
        cast(str, node["id"])
        for node in cast(list[dict[str, Any]], source["dependency_graph"]["nodes"])
    }
    for item in items:
        assert item["filesystem_mode"] == "0644"
        assert item["git_mode"] == "100644"
        relative = cast(str, item["path"])
        assert item["source_node"] in graph_nodes
        assert item["source_node"] == _expected_source_node(relative)
        _assert_safe_relative(relative)
    publication_commits = cast(list[dict[str, Any]], source["publication_commits"])
    assert len(publication_commits) == source["publication_commit_count"] == 6
    assert [
        (
            item["slice_id"],
            item["primary_commit"],
            item["reviewed_tree"],
            item["squash_sha"],
            item["source_node"],
        )
        for item in publication_commits
    ] == [
        (item[0], item[2], item[3], item[4], f"publication:s{index:02d}")
        for index, item in enumerate(EXPECTED_LEDGER, start=1)
    ]
    production_observations = cast(
        list[dict[str, Any]], source["production_observations"]
    )
    observation_paths = [cast(str, item["path"]) for item in production_observations]
    assert (
        len(production_observations)
        == len(observation_paths)
        == len(set(observation_paths))
        == source["production_observation_count"]
        == 8
    )
    assert {
        cast(str, item["path"]): LockedFile(
            cast(int, item["byte_length"]), cast(str, item["sha256"])
        )
        for item in production_observations
    } == EXPECTED_PRODUCTION
    for item in production_observations:
        assert item["filesystem_mode"] == "0644"
        assert item["git_mode"] == "100644"
        assert item["source_node"] == "observation:production"
    if verify_files:
        for relative, expected in EXPECTED_SOURCE_LOCKS.items():
            raw = (REPOSITORY_ROOT / relative).read_bytes()
            assert len(raw) == expected.byte_length
            assert _sha256(raw) == expected.sha256


def _assert_ledger(document: dict[str, Any]) -> None:
    ledger = cast(dict[str, Any], document["slice_ledger"])
    entries = cast(list[dict[str, Any]], ledger["entries"])
    expected_order = [f"S1.P02.S{number:02d}" for number in range(1, 8)]
    assert ledger == {
        **ledger,
        "count": 7,
        "order": expected_order,
        "unique": True,
    }
    ids = [entry["slice_id"] for entry in entries]
    assert ids == expected_order
    assert len(ids) == len(set(ids)) == 7
    for entry, expected in zip(entries[:6], EXPECTED_LEDGER, strict=True):
        (
            slice_id,
            pull_request,
            primary,
            tree,
            squash,
            pr_run,
            pr_job,
            main_run,
            main_job,
            tests,
        ) = expected
        assert entry["slice_id"] == slice_id
        assert entry["completion_state"] == "published_complete"
        assert entry["pull_request"] == pull_request
        assert entry["primary_commit"] == entry["reviewed_head_sha"] == primary
        assert entry["reviewed_tree"] == tree
        assert entry["squash_sha"] == squash
        assert entry["reviewed_tree_equals_squash_tree"] is True
        assert entry["publication_test_count"] == tests
        assert entry["package_build"] == "success"
        assert entry["required_pr_ci"] == {
            "conclusion": "success",
            "event": "pull_request",
            "head_sha": primary,
            "job_id": pr_job,
            "job_name": "validate",
            "run_attempt": 1,
            "run_id": pr_run,
            "workflow": "CI",
        }
        assert entry["natural_main_ci"] == {
            "conclusion": "success",
            "event": "push",
            "head_sha": squash,
            "job_id": main_job,
            "job_name": "validate",
            "run_attempt": 1,
            "run_id": main_run,
            "workflow": "CI",
        }
        assert entry["review_settlement"]["actionable_unresolved_count"] == 0
    s03 = entries[2]["review_settlement"]
    assert s03["thread_count"] == 1
    assert s03["threads"][0]["resolved"] is True
    s05 = entries[4]["review_settlement"]
    assert s05["thread_count"] == 1
    assert s05["threads"][0] == {
        "concern": "zero_count_existing_file_diff_anchor",
        "disposition": "resolved_without_semantic_expansion_valid_diff_shape_remains_outside_frozen_nonempty_span_and_paired_file_span_contract",
        "late_review": True,
        "outdated": False,
        "resolved": True,
    }
    candidate = entries[6]
    assert candidate["completion_state"] == "sealed_publication_candidate"
    assert tuple(candidate["candidate_changed_surfaces"]) == EXPECTED_CHANGED_PATHS
    assert (
        tuple(candidate["external_operational_completion_conditions"])
        == EXPECTED_EXTERNAL_COMPLETION_CONDITIONS
    )
    forbidden = {
        "primary_commit",
        "pull_request",
        "reviewed_head_sha",
        "reviewed_tree",
        "squash_sha",
        "required_pr_ci",
        "natural_main_ci",
    }
    assert not forbidden & set(candidate)
    assert (
        set(candidate["future_publication_identifiers"]["prohibited_in_candidate"])
        == forbidden
    )
    assert candidate["future_publication_identifiers"]["state"] == (
        "unavailable_in_self_contained_candidate"
    )


def _parse_module_exports(raw: bytes) -> tuple[str, ...]:
    tree = ast.parse(raw)
    assignments = [
        node
        for node in tree.body
        if isinstance(node, ast.Assign)
        and any(
            isinstance(target, ast.Name) and target.id == "__all__"
            for target in node.targets
        )
    ]
    assert len(assignments) == 1
    value = cast(object, ast.literal_eval(assignments[0].value))
    assert isinstance(value, list)
    items = cast(list[object], value)
    assert all(isinstance(item, str) for item in items)
    return tuple(cast(str, item) for item in items)


def _validate_production_inventory(paths: set[str]) -> None:
    assert paths == set(EXPECTED_PRODUCTION)


def _validate_current_production_inventory(paths: set[str]) -> None:
    assert paths == CURRENT_PRODUCTION_FILES


def _validate_exports(exports: tuple[str, ...]) -> None:
    assert exports == EXPECTED_EXPORTS
    assert len(exports) == len(set(exports)) == 23


def _validate_package_root_exports(exports: tuple[str, ...]) -> None:
    assert exports == ("__version__",)


def _validate_current_evidence_inventory(raw: bytes) -> None:
    exports = _parse_module_exports(raw)
    assert exports == EXPECTED_EVIDENCE_EXPORTS
    assert len(exports) == len(set(exports)) == 58

    tree = ast.parse(raw)
    top_level_definitions = [
        node.name
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
        else node.name.id
        for node in tree.body
        if isinstance(
            node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef, ast.TypeAlias)
        )
    ]
    public_definitions = tuple(
        name for name in top_level_definitions if not name.startswith("_")
    )
    assert public_definitions == EXPECTED_EVIDENCE_EXPORTS
    assert sum(isinstance(node, ast.ClassDef) for node in tree.body) == 58
    assert tuple(
        node.name
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and not node.name.startswith("_")
    ) == (
        "wrap_legacy_artifact_snapshot",
        "project_evidence_envelope_to_legacy_artifact_snapshot",
    )
    assert tuple(
        node.name.id for node in tree.body if isinstance(node, ast.TypeAlias)
    ) == ("EvidenceRecordRelationship",)
    for name in top_level_definitions:
        compact = name.replace("_", "").casefold()
        assert not any(
            fragment in compact
            for fragment in FORBIDDEN_POST_S07_EVIDENCE_SURFACE_FRAGMENTS
        )
        if "acquisitionrun" in compact:
            assert name in {
                "AcquisitionRunId",
                "AcquisitionRunStatus",
                "AcquisitionRun",
            }


def _validate_domain_root_unchanged(raw: bytes) -> None:
    tree = ast.parse(raw)
    assert not any(isinstance(node, (ast.Import, ast.ImportFrom)) for node in tree.body)
    assert not any(
        isinstance(node, ast.Assign)
        and any(
            isinstance(target, ast.Name) and target.id == "__all__"
            for target in node.targets
        )
        for node in tree.body
    )


def _production_definitions(raw: bytes) -> set[str]:
    tree = ast.parse(raw)
    return {
        node.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
    }


def _assert_no_production_reader_or_p03(sources: dict[str, bytes]) -> None:
    assert set(sources) == set(EXPECTED_PRODUCTION)
    forbidden_names = {
        "EvidenceEnvelope",
        "AcquisitionRun",
        "RetainedArtifactRecord",
        "RevisionLocatorCorpusReader",
        "LocatorResolver",
    }
    for relative, raw in sources.items():
        lowered_path = relative.casefold()
        assert not any(
            marker in lowered_path
            for marker in (
                "evidence.py",
                "envelope.py",
                "locator_reader.py",
                "locator_resolver.py",
            )
        )
        definitions = _production_definitions(raw)
        assert not definitions & forbidden_names
        for name in definitions:
            lowered = name.casefold()
            assert not (
                "corpus" in lowered
                and any(word in lowered for word in ("read", "load", "write"))
            )
            assert not ("locator" in lowered and "resolve" in lowered)


def _assert_inventory(document: dict[str, Any], verify_files: bool = False) -> None:
    inventory = cast(dict[str, Any], document["implementation_inventory"])
    exports = cast(list[dict[str, Any]], inventory["revision_exports"])
    assert inventory["revision_export_count"] == 23
    assert tuple(item["symbol"] for item in exports) == EXPECTED_EXPORTS
    assert len({item["symbol"] for item in exports}) == 23
    assert {item["originating_slice"] for item in exports} == {
        "S1.P02.S01",
        "S1.P02.S02",
        "S1.P02.S03",
        "S1.P02.S04",
        "S1.P02.S05",
    }
    assert all(item["internal_status"] == "internal_non_public" for item in exports)
    assert all(
        item["contract_corpus_coverage"] == "covered_by_revision_locator_v1"
        for item in exports
    )
    package = cast(dict[str, Any], inventory["package_boundary"])
    assert package["production_files"] == list(EXPECTED_PRODUCTION)
    _validate_package_root_exports(
        tuple(cast(list[str], package["package_root_exports"]))
    )
    assert package["domain_root_revision_exports"] == []
    assert package["package_version"] == "0.1.0"
    assert package["no_production_corpus_reader"] is True
    assert package["no_locator_resolver"] is True
    production_observations = cast(
        list[dict[str, Any]], inventory["production_observations"]
    )
    observation_paths = [cast(str, item["path"]) for item in production_observations]
    assert (
        len(production_observations)
        == len(observation_paths)
        == len(set(observation_paths))
        == len(EXPECTED_PRODUCTION)
    )
    observations = {
        item["path"]: LockedFile(item["byte_length"], item["sha256"])
        for item in production_observations
    }
    assert observations == EXPECTED_PRODUCTION
    if verify_files:
        current = {
            path.relative_to(REPOSITORY_ROOT).as_posix()
            for path in (REPOSITORY_ROOT / "src").rglob("*.py")
        }
        _validate_current_production_inventory(current)
        sources = {
            relative: (REPOSITORY_ROOT / relative).read_bytes()
            for relative in EXPECTED_PRODUCTION
        }
        _assert_no_production_reader_or_p03(sources)
        for relative, expected in EXPECTED_PRODUCTION.items():
            assert len(sources[relative]) == expected.byte_length
            assert _sha256(sources[relative]) == expected.sha256
        _validate_exports(
            _parse_module_exports(sources["src/faultatlas/domain/revision.py"])
        )


def _load_json(path: Path) -> dict[str, Any]:
    return _parse_canonical(path.read_bytes())


def _assert_corpus(document: dict[str, Any], verify_files: bool = False) -> None:
    corpus = cast(dict[str, Any], document["contract_corpus_assurance"])
    assert (
        corpus["corpus_format"]
        == "faultatlas-revision-locator-contract-corpus-manifest"
    )
    assert corpus["corpus_version"] == "1"
    file_locks = cast(list[dict[str, Any]], corpus["file_locks"])
    file_paths = [cast(str, item["path"]) for item in file_locks]
    assert (
        len(file_locks)
        == len(file_paths)
        == len(set(file_paths))
        == (corpus["file_count"])
        == 9
    )
    expected_file_locks = {
        relative: locked
        for relative, locked in EXPECTED_SOURCE_LOCKS.items()
        if relative.startswith("reference_corpus/contracts/revision-locator/v1/")
    }
    assert {
        cast(str, item["path"]): LockedFile(
            cast(int, item["byte_length"]), cast(str, item["sha256"])
        )
        for item in file_locks
    } == expected_file_locks
    assert all(
        item["filesystem_mode"] == "0644" and item["git_mode"] == "100644"
        for item in file_locks
    )
    assert corpus["valid_vector_count"] == 97
    assert corpus["invalid_vector_count"] == 121
    assert corpus["replay_vector_count"] == 10
    assert corpus["total_vector_count"] == 228
    assert corpus["fixture_count"] == 18
    assert corpus["target_export_coverage"] == "23_of_23"
    assert corpus["mutation_case_count"] == 47
    assert corpus["future_evolution_owner"] == "S1.P10"
    assert corpus["source_only"] is True
    assert corpus["mutable_pointer"] is False
    assert corpus["package_exclusion"] is True
    if verify_files:
        assert {path.name for path in CORPUS_ROOT.iterdir()} == EXPECTED_CORPUS_FILES
        valid = _load_json(CORPUS_ROOT / "valid-vectors.json")
        invalid = _load_json(CORPUS_ROOT / "invalid-vectors.json")
        replay = _load_json(CORPUS_ROOT / "replay-vectors.json")
        assert len(valid["vectors"]) == 97
        assert len(invalid["vectors"]) == 121
        assert len(replay["vectors"]) == 10
        assert len(valid["fixtures"]) + len(replay["fixtures"]) == 18
        manifest = _load_json(CORPUS_ROOT / "manifest.json")
        assert manifest["target_symbols"] == list(EXPECTED_EXPORTS)
        test_tree = ast.parse(
            (
                REPOSITORY_ROOT / "tests/test_revision_locator_contract_corpus.py"
            ).read_text(encoding="utf-8")
        )
        mutation_assignments = [
            node
            for node in test_tree.body
            if isinstance(node, ast.Assign)
            and any(
                isinstance(target, ast.Name) and target.id == "REQUIRED_MUTATIONS"
                for target in node.targets
            )
        ]
        assert len(mutation_assignments) == 1
        assert len(ast.literal_eval(mutation_assignments[0].value)) == 47


EXPECTED_REPLAY_SLICES = (
    (165, 77, 6, 7, "3a9ef726e8631334ac0ee92db96577569a58f2c972fb2b248b2f33a8833952a6"),
    (
        439,
        394,
        12,
        21,
        "7395019171a710ce827d5ed71020afbdd790f8e1c158756388c08977d17bdecd",
    ),
    (
        1018,
        622,
        26,
        45,
        "47640375cbfeb436cfc73aeeb1926d77b05d969fc684289c17b271ca85facfc3",
    ),
)
EXPECTED_HUNKS = (
    ("@@ -0,0 +1 @@", None, (1, 1), (1, 1)),
    (
        "@@ -946,7 +946,8 @@ def visit_Call_35(self, call):",
        (946, 952),
        (946, 953),
        (946, 950),
    ),
    (
        "@@ -413,6 +413,19 @@ def test_multmat_operator():",
        (413, 418),
        (413, 431),
        (416, 427),
    ),
)


def _span_tuple(value: dict[str, int] | None) -> tuple[int, int] | None:
    if value is None:
        return None
    return value["start_line"], value["end_line"]


def _assert_replay(document: dict[str, Any], verify_artifact: bool = False) -> None:
    replay = cast(dict[str, Any], document["replay_assurance"])
    assert replay["artifact"] == {
        "byte_length": 1640,
        "final_lf": True,
        "line_count": 45,
        "line_endings": "LF_only_no_CR",
        "path": RETAINED_DIFF.relative_to(REPOSITORY_ROOT).as_posix(),
        "sha256": "dca87a4df1edb2d1acb3fc821724483ee874c2feba6525b2c21e79cb3e8f7312",
    }
    observed_slices = tuple(
        (
            item["offset"],
            item["byte_length"],
            item["artifact_line_span"]["start_line"],
            item["artifact_line_span"]["end_line"],
            item["selected_sha256"],
        )
        for item in replay["byte_slices"]
    )
    assert observed_slices == EXPECTED_REPLAY_SLICES
    observed_hunks = tuple(
        (
            item["header"],
            _span_tuple(item["old_file_lines"]),
            _span_tuple(item["new_file_lines"]),
            _span_tuple(item["reviewed_applicable_new_file_lines"]),
        )
        for item in replay["hunks"]
    )
    assert observed_hunks == EXPECTED_HUNKS
    assert replay["evidence_classifications"] == [
        "exact_byte_locator_fact",
        "deterministic_derivation",
        "reviewed_derived_interpretation",
    ]
    assert replay["coordinate_conventions"] == {
        "artifact_and_repository_lines": "one_based_inclusive_nonempty",
        "artifact_bytes": "zero_based_half_open_offset_and_positive_length",
    }
    assert replay["replay_vector_count"] == 10
    assert replay["production_boundaries"] == {
        "models_do_not_parse_diffs": True,
        "models_do_not_read_artifacts": True,
        "models_do_not_resolve_locators": True,
        "models_do_not_store_applicability_or_review_meaning": True,
        "replay_tests_remain_test_only": True,
    }
    if verify_artifact:
        raw = RETAINED_DIFF.read_bytes()
        assert len(raw) == 1640
        assert _sha256(raw) == replay["artifact"]["sha256"]
        assert raw.endswith(b"\n") and b"\r" not in raw
        assert raw.count(b"\n") == 45
        for offset, length, _first, _last, digest in EXPECTED_REPLAY_SLICES:
            assert _sha256(raw[offset : offset + length]) == digest
        headers = [line.decode() for line in raw.splitlines() if line.startswith(b"@@")]
        assert headers == [item[0] for item in EXPECTED_HUNKS]


def _annotated_fields(raw: bytes) -> dict[str, set[str]]:
    tree = ast.parse(raw)
    result: dict[str, set[str]] = {}
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            result[node.name] = {
                child.target.id
                for child in node.body
                if isinstance(child, ast.AnnAssign)
                and isinstance(child.target, ast.Name)
            }
    return result


def _assert_boundaries(document: dict[str, Any], source: bytes | None = None) -> None:
    boundaries = cast(dict[str, Any], document["semantic_boundaries"])
    items = cast(list[dict[str, Any]], boundaries["items"])
    ids = [cast(str, item["boundary_id"]) for item in items]
    assert len(items) == len(ids) == len(set(ids)) == boundaries["count"] == 12
    assert set(ids) == EXPECTED_BOUNDARIES
    if source is None:
        return
    fields = _annotated_fields(source)
    assert fields["_GitObjectIdentityBase"] == {
        "schema_version",
        "kind",
        "algorithm",
        "full_digest",
    }
    assert fields["RevisionRoleAssignment"] == {"role", "revision"}
    assert fields["GitCommitParentTopology"] == {"commit", "ordered_parents"}
    assert not fields["GitRefObservation"] & {
        "role",
        "topology",
        "path",
        "history",
    }
    assert fields["RevisionQualifiedPath"] == {
        "repository_identity",
        "revision",
        "path",
    }
    locator_fields: set[str] = (
        fields["RevisionLineLocator"]
        | fields["ArtifactByteLocator"]
        | fields["DiffHunkLocator"]
    )
    assert not locator_fields & {
        "applicability",
        "review",
        "history",
        "provenance",
        "causal_interpretation",
    }
    assert b"reference_corpus/contracts/revision-locator" not in source


def _assert_exit_criteria(document: dict[str, Any]) -> None:
    criteria = cast(dict[str, Any], document["exit_criteria"])
    items = cast(list[dict[str, Any]], criteria["items"])
    assert criteria["controlled_outcomes"] == [
        "satisfied",
        "satisfied_with_explicit_deferral",
        "not_applicable",
        "unsatisfied",
    ]
    assert criteria["count"] == 66
    assert {item["criterion_id"] for item in items} == EXPECTED_CRITERIA
    assert len(items) == len({item["criterion_id"] for item in items}) == 66
    assert all(item["evidence"] for item in items)
    assert all(item["statement"] for item in items)
    assert criteria["outcome_totals"] == {
        "not_applicable": 0,
        "satisfied": 65,
        "satisfied_with_explicit_deferral": 1,
        "unsatisfied": 0,
    }
    assert criteria["unsatisfied_count"] == 0
    for item in items:
        if item["criterion_id"] == "exit:62":
            assert item["outcome"] == "satisfied_with_explicit_deferral"
            assert item["deferral"]["owner"] == "multiple_later_phase_owners"
        else:
            assert item["outcome"] == "satisfied"
            assert item["deferral"] == {"state": "not_applicable"}


EXPECTED_DEFERRED_SUBJECTS = (
    "Evidence Envelope",
    "source and provider authority references in the envelope",
    "retrieval request records",
    "response representation observations",
    "acquisition-run identity",
    "exact retained-artifact production record",
    "representation versus artifact distinction",
    "media and encoding observations",
    "artifact digest scope",
    "transformation record",
    "correction and supersession record",
    "completeness and omission record",
    "unavailable deleted inaccessible and unknown evidence states at envelope level",
    "publication provenance",
    "locator-to-evidence binding",
    "normalized versus exact representation distinction",
    "repository snapshot aggregation",
    "snapshot completeness",
    "default-branch observation",
    "repository membership aggregation",
    "revision ref and path event history",
    "ancestry and reachability",
    "path rename and copy history",
    "complete discussion and history relationships",
    "applicability and review state",
    "causal interpretation",
    "evidence confidence",
    "claim review",
    "attribution and reviewer identity",
    "production corpus readers and writers",
    "production canonical serialization",
    "locator wire-version dispatch",
    "migrations",
    "persistence",
    "contract-corpus evolution and correction policy",
    "private GitHub",
    "GitHub Enterprise",
    "other providers",
    "non-Git VCS",
    "non-UTF-8 Git path bytes",
    "universal symbolic-ref behavior",
    "tag-object identity requirements",
)


def _assert_deferred(document: dict[str, Any]) -> None:
    deferred = cast(dict[str, Any], document["deferred_register"])
    items = cast(list[dict[str, Any]], deferred["items"])
    ids = [cast(str, item["deferred_item_id"]) for item in items]
    assert len(items) == len(ids) == len(set(ids)) == deferred["count"] == 42
    assert set(ids) == EXPECTED_DEFERRED
    assert tuple(item["subject"] for item in items) == EXPECTED_DEFERRED_SUBJECTS
    assert deferred["state_totals"] == EXPECTED_DEFERRED_STATE_TOTALS
    assert deferred["immediate_owner_totals"] == EXPECTED_OWNER_TOTALS
    assert deferred["long_term_owner_totals"] == EXPECTED_OWNER_TOTALS
    assert deferred["owner_completeness"] is True
    assert all(item["immediate_owner"] for item in items)
    assert all(item["preserved_long_term_owner"] for item in items)
    assert all(item["reason"] and item["evidence"] for item in items)
    assert not any(
        item["subject"]
        in {
            "Git object identity",
            "revision roles",
            "mutable ref observations",
            "revision-qualified paths",
            "bounded locators",
        }
        for item in items
    )


def _assert_findings_non_generalizations(document: dict[str, Any]) -> None:
    findings = cast(dict[str, Any], document["established_findings"])
    finding_items = cast(list[dict[str, Any]], findings["items"])
    finding_ids = [cast(str, item["finding_id"]) for item in finding_items]
    assert (
        len(finding_items)
        == len(finding_ids)
        == len(set(finding_ids))
        == findings["count"]
        == 30
    )
    assert set(finding_ids) == EXPECTED_FINDINGS
    assert findings["classification_totals"] == {
        "implementation_behavior": 20,
        "locked_case_calibrated_decision": 4,
        "reviewed_conclusion": 3,
        "verified_repository_fact": 3,
    }
    non_general = cast(dict[str, Any], document["non_generalizations"])
    non_general_items = cast(list[dict[str, Any]], non_general["items"])
    non_general_ids = [
        cast(str, item["non_generalization_id"]) for item in non_general_items
    ]
    assert (
        len(non_general_items)
        == len(non_general_ids)
        == len(set(non_general_ids))
        == non_general["count"]
        == 41
    )
    assert set(non_general_ids) == EXPECTED_NON_GENERALIZATIONS
    assert non_general["intentional_deferral_is_not_implementation_failure"] is True


def _assert_readiness(document: dict[str, Any]) -> None:
    readiness = cast(dict[str, Any], document["entry_readiness"])
    prerequisites = cast(list[dict[str, Any]], readiness["prerequisites"])
    prerequisite_ids = [cast(str, item["prerequisite_id"]) for item in prerequisites]
    assert (
        len(prerequisites)
        == len(prerequisite_ids)
        == len(set(prerequisite_ids))
        == readiness["prerequisite_count"]
        == 24
    )
    assert set(prerequisite_ids) == EXPECTED_PREREQUISITES
    assert all(item["outcome"] == "satisfied" for item in prerequisites)
    assert readiness["status"] == "eligible_to_begin"
    assert readiness["implementation"] == "not_started"
    assert readiness["operational_activation"] == (
        "after_external_S07_publication_conditions"
    )
    assert tuple(readiness["scope_guard"]["allowed"]) == EXPECTED_P03_ALLOWED
    assert tuple(readiness["scope_guard"]["forbidden"]) == EXPECTED_P03_FORBIDDEN


def _assert_candidate(document: dict[str, Any]) -> None:
    format_record = cast(dict[str, Any], document["format"])
    assert format_record["name"] == EXPECTED_FORMAT
    assert format_record["version"] == EXPECTED_VERSION
    assert format_record["classification"] == "phase_closure"
    assert format_record["publication_state"] == "sealed_publication_candidate"
    assert format_record["internal"] is True
    assert format_record["public_contract"] is False
    phase = cast(dict[str, Any], document["phase_identity"])
    assert phase["stage"] == "S1"
    assert phase["phase"] == "S1.P02"
    assert phase["phase_title"] == "Revision-qualified Locators"
    assert phase["predecessor_phase"] == "S1.P01"
    assert phase["next_phase"] == "S1.P03"
    assert phase["repository"] == "MianliWang/FaultAtlas"
    assert phase["synchronized_baseline_sha"] == EXPECTED_BASELINE
    assert phase["synchronized_baseline_tree"] == EXPECTED_BASELINE_TREE
    assert phase["candidate_state"] == "sealed_publication_candidate"
    assert phase["operational_completion"] == "pending_external_publication_conditions"
    assert (
        tuple(phase["external_operational_completion_conditions"])
        == EXPECTED_EXTERNAL_COMPLETION_CONDITIONS
    )
    publication = cast(dict[str, Any], document["publication_contract"])
    assert publication["topic_branch"] == (
        "feat/s1-p02-s07-revision-locator-phase-closure"
    )
    assert publication["required_check"] == "validate"
    assert publication["direct_main_push"] == "forbidden"
    assert publication["operational_completion"] == "external_to_candidate_record"
    assert publication["protected_ready_pull_request_required"] is True
    assert publication["review_thread_settlement_required"] is True
    assert publication["squash_merge_required"] is True
    assert publication["natural_main_CI_required"] is True


def _assert_test_assurance(document: dict[str, Any]) -> None:
    tests = cast(dict[str, Any], document["test_assurance"])
    assert tests["baseline"] == {
        "focused_governing_count": 2159,
        "focused_runtime_seconds": "7.82",
        "full_pytest_count": 2159,
        "full_result": "passed",
        "full_runtime_seconds": "7.40",
    }
    fresh = tests["fresh_s07"]
    assert fresh["closure_test_count"] == 61
    assert fresh["focused_test_count"] == 2220
    assert fresh["focused_runtime_seconds"] == "6.43"
    assert fresh["full_pytest_count"] == 2220
    assert fresh["full_runtime_seconds"] == "9.93"
    assert fresh["mutation_case_count"] == 44
    assert fresh["status"] == "passed_pre_publication_validation"
    for key in (
        "CLI_smoke",
        "P00_P01_assurance",
        "S01_through_S06_assurance",
        "contract_corpus_assurance",
        "offline_wheel_and_sdist",
        "package_exclusion",
        "permission_assurance",
        "pyright",
        "replay_assurance",
        "ruff_check",
        "ruff_format_check",
    ):
        assert fresh[key] == "passed"
    assert fresh["source_inventory"] == "passed_exact_eight"
    for key in (
        "no_P03_implementation",
        "no_production_change",
        "no_production_reader_or_resolver",
        "no_provider_or_network_acquisition",
    ):
        assert fresh[key] is True
    historical = cast(list[dict[str, Any]], tests["historical_publications"])
    assert len(historical) == 6
    assert [
        (
            item["slice_id"],
            item["test_count"],
            item["pr_CI"],
            item["main_CI"],
            item["reviewed_tree_equals_squash_tree"],
            item["package_build"],
        )
        for item in historical
    ] == [
        (expected[0], expected[9], "success", "success", True, "success")
        for expected in EXPECTED_LEDGER
    ]
    assert tests["test_count_is_not_product_completeness"] is True


def _assert_document(document: dict[str, Any]) -> None:
    assert set(document) == EXPECTED_TOP_LEVEL
    _assert_candidate(document)
    _assert_source_locks(document)
    _assert_ledger(document)
    _assert_inventory(document)
    _assert_corpus(document)
    _assert_replay(document)
    _assert_boundaries(document)
    _assert_exit_criteria(document)
    _assert_deferred(document)
    _assert_findings_non_generalizations(document)
    _assert_readiness(document)
    _assert_test_assurance(document)
    assurance = document["assurance"]
    assert assurance["unsatisfied_exit_criteria"] == 0
    assert assurance["unresolved_S1_P02_blockers"] == 0
    assert assurance["no_P03_implementation"] is True
    assert assurance["no_production_reader_or_resolver"] is True
    assert assurance["publication_state"] == "sealed_publication_candidate"


def _assert_private_payload(raw: bytes) -> None:
    lowered = raw.lower()
    for forbidden in (
        b"/home/",
        b"/root/",
        b"/users/",
        b"/tmp/",
        b"authorization:",
        b"bearer ",
        b"begin openssh private key",
        b"begin private key",
        b"ghp_",
        b"github_pat_",
        b"x-access-token",
    ):
        assert forbidden not in lowered
    normalized = re.sub(rb"[-_. ]", b"", lowered)
    for forbidden in (b"accesstoken", b"refreshtoken", b"apikey", b"clientsecret"):
        assert forbidden not in normalized
    assert re.search(rb"[A-Za-z]:[\\/]", raw) is None
    assert re.search(rb"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", raw) is None
    assert not any(
        marker in lowered
        for marker in (
            b'"raw_provider_response"',
            b'"provider_response"',
            b'"response_body"',
            b'"raw_payload"',
        )
    )


@dataclass(frozen=True)
class ArchiveMember:
    name: str
    kind: str
    data: bytes | None = None


def _read_wheel(path: Path) -> tuple[ArchiveMember, ...]:
    members: list[ArchiveMember] = []
    with zipfile.ZipFile(path) as archive:
        for info in archive.infolist():
            mode = info.external_attr >> 16
            if stat.S_ISLNK(mode):
                members.append(ArchiveMember(info.filename, "link"))
            elif info.is_dir():
                members.append(ArchiveMember(info.filename, "directory"))
            else:
                members.append(ArchiveMember(info.filename, "file", archive.read(info)))
    return tuple(members)


def _read_sdist(path: Path) -> tuple[ArchiveMember, ...]:
    members: list[ArchiveMember] = []
    with tarfile.open(path, mode="r:gz") as archive:
        for info in archive.getmembers():
            if info.issym() or info.islnk():
                members.append(ArchiveMember(info.name, "link"))
            elif info.isdir():
                members.append(ArchiveMember(info.name, "directory"))
            elif info.isfile():
                stream = archive.extractfile(info)
                assert stream is not None
                members.append(ArchiveMember(info.name, "file", stream.read()))
            else:
                members.append(ArchiveMember(info.name, "special"))
    return tuple(members)


def _assert_archive(
    members: tuple[ArchiveMember, ...],
    *,
    archive_name: str,
    project_license: bytes,
    historical_license: bytes,
) -> None:
    assert members
    assert archive_name in {
        "faultatlas-0.1.0-py3-none-any.whl",
        "faultatlas-0.1.0.tar.gz",
    }
    member_names = [member.name for member in members]
    assert len(member_names) == len(set(member_names))
    project_license_count = 0
    packaged_sources: dict[str, bytes] = {}
    metadata_payloads: list[bytes] = []
    for member in members:
        assert member.kind in {"file", "directory"}
        path = PurePosixPath(member.name)
        assert not path.is_absolute()
        assert ".." not in path.parts
        assert "\\" not in member.name
        assert re.match(r"^[A-Za-z]:", member.name) is None
        lowered_parts = tuple(part.casefold() for part in path.parts)
        assert "reference_corpus" not in lowered_parts
        assert "tests" not in lowered_parts
        if member.kind != "file":
            continue
        assert member.data is not None
        assert member.data != historical_license
        if path.name in {"METADATA", "PKG-INFO"}:
            metadata_payloads.append(member.data)
        if path.name == "LICENSE" and member.data == project_license:
            project_license_count += 1
        parts = list(path.parts)
        if "faultatlas" in parts and path.suffix == ".py":
            index = parts.index("faultatlas")
            relative = "src/" + "/".join(parts[index:])
            assert relative not in packaged_sources
            packaged_sources[relative] = member.data
    assert len(metadata_payloads) == 1
    metadata = metadata_payloads[0]
    assert re.search(rb"(?m)^Name: faultatlas$", metadata) is not None
    assert re.search(rb"(?m)^Version: 0[.]1[.]0$", metadata) is not None
    assert project_license_count == 1
    working = {
        relative: (REPOSITORY_ROOT / relative).read_bytes()
        for relative in CURRENT_PRODUCTION_FILES
    }
    assert packaged_sources == working


def _synthetic_archive_members(
    *, extra_name: str, extra_data: bytes
) -> tuple[ArchiveMember, ...]:
    members = [
        ArchiveMember(
            relative.removeprefix("src/"),
            "file",
            (REPOSITORY_ROOT / relative).read_bytes(),
        )
        for relative in CURRENT_PRODUCTION_FILES
    ]
    members.append(
        ArchiveMember("LICENSE", "file", (REPOSITORY_ROOT / "LICENSE").read_bytes())
    )
    members.append(
        ArchiveMember(
            "faultatlas-0.1.0.dist-info/METADATA",
            "file",
            b"Metadata-Version: 2.4\nName: faultatlas\nVersion: 0.1.0\n",
        )
    )
    members.append(ArchiveMember(extra_name, "file", extra_data))
    return tuple(members)


def test_group_a_exact_inventory_permissions_and_safe_paths(tmp_path: Path) -> None:
    assert CLOSURE_ROOT.is_dir() and not CLOSURE_ROOT.is_symlink()
    assert {path.name for path in CLOSURE_ROOT.iterdir()} == EXPECTED_CLOSURE_FILES
    for path in CLOSURE_ROOT.iterdir():
        _assert_regular_0644(path)
        _assert_safe_relative(path.relative_to(REPOSITORY_ROOT).as_posix())
    assert not (CLOSURE_ROOT.parent / "latest").exists()
    assert not (CLOSURE_ROOT.parent / "current").exists()
    relatives = {f"{CLOSURE_RELATIVE}/{name}" for name in EXPECTED_CLOSURE_FILES}
    _assert_git_modes(_prospective_modes(relatives, tmp_path), relatives)


def test_group_b_primary_json_is_locked_canonical_and_deterministic() -> None:
    raw = (CLOSURE_ROOT / "closure.json").read_bytes()
    document = _assert_primary(raw)
    assert _canonical_bytes(document) == raw
    assert _canonical_bytes(_parse_canonical(raw)) == raw
    _assert_document(document)


def test_group_c_sidecar_is_exact_and_independently_locked() -> None:
    primary = (CLOSURE_ROOT / "closure.json").read_bytes()
    _assert_sidecar((CLOSURE_ROOT / "closure.sha256").read_bytes(), primary)


def test_group_d_markdown_is_exactly_derived_and_synchronized() -> None:
    raw = (CLOSURE_ROOT / "closure.md").read_bytes()
    assert len(raw) == EXPECTED_MARKDOWN_BYTES
    assert _sha256(raw) == EXPECTED_MARKDOWN_SHA256
    assert b"\r" not in raw and raw.endswith(b"\n") and not raw.endswith(b"\n\n")
    text = raw.decode("utf-8")
    positions = [text.index(heading) for heading in EXPECTED_MARKDOWN_HEADINGS]
    assert positions == sorted(positions)
    assert EXPECTED_JSON_SHA256 in text
    assert "Internal, non-public" in text
    assert "derived and non-authoritative" in text
    assert "sole durable semantic authority" in text
    assert "S1.P03 remains not started" in text
    document = _load_closure()
    for value in (
        document["slice_ledger"]["count"],
        document["implementation_inventory"]["revision_export_count"],
        document["exit_criteria"]["count"],
        document["deferred_register"]["count"],
        document["entry_readiness"]["prerequisite_count"],
    ):
        assert str(value) in text


def test_group_e_source_locks_are_exact_acyclic_and_immutable() -> None:
    _assert_source_locks(_load_closure(), verify_files=True)


def test_group_f_ledger_is_exact_ordered_and_publication_evidenced() -> None:
    _assert_ledger(_load_closure())


def test_group_g_production_inventory_exports_and_absent_surfaces_are_exact() -> None:
    document = _load_closure()
    _assert_inventory(document, verify_files=True)
    assert tuple(revision_module.__all__) == EXPECTED_EXPORTS
    _validate_package_root_exports(
        _parse_module_exports(
            (REPOSITORY_ROOT / "src/faultatlas/__init__.py").read_bytes()
        )
    )
    assert faultatlas.__all__ == ["__version__"]
    assert faultatlas.__version__ == "0.1.0"
    assert getattr(domain_package, "__all__", None) in (None, [])
    assert not any(hasattr(faultatlas, name) for name in EXPECTED_EXPORTS)
    assert not any(hasattr(domain_package, name) for name in EXPECTED_EXPORTS)


def test_current_production_inventory_and_exports_are_exact() -> None:
    current = {
        path.relative_to(REPOSITORY_ROOT).as_posix()
        for path in (REPOSITORY_ROOT / "src").rglob("*.py")
    }
    _validate_current_production_inventory(current)
    _validate_current_evidence_inventory(
        (REPOSITORY_ROOT / EVIDENCE_MODULE).read_bytes()
    )
    _validate_package_root_exports(
        _parse_module_exports(
            (REPOSITORY_ROOT / "src/faultatlas/__init__.py").read_bytes()
        )
    )
    _validate_domain_root_unchanged(
        (REPOSITORY_ROOT / "src/faultatlas/domain/__init__.py").read_bytes()
    )


def test_group_h_contract_corpus_is_immutable_and_complete() -> None:
    _assert_corpus(_load_closure(), verify_files=True)


def test_group_i_retained_diff_replay_is_exact_and_test_only() -> None:
    _assert_replay(_load_closure(), verify_artifact=True)


def test_group_j_semantic_boundaries_are_exact_and_source_backed() -> None:
    source = (REPOSITORY_ROOT / "src/faultatlas/domain/revision.py").read_bytes()
    _assert_boundaries(_load_closure(), source)


def test_group_k_exit_criteria_are_exact_with_zero_unsatisfied() -> None:
    _assert_exit_criteria(_load_closure())


def test_group_l_deferred_register_has_complete_later_ownership() -> None:
    _assert_deferred(_load_closure())


def test_group_m_historical_p03_readiness_and_current_s05_are_scope_guarded() -> None:
    document = _load_closure()
    _assert_readiness(document)
    production_sources = b"\n".join(
        (REPOSITORY_ROOT / relative).read_bytes() for relative in EXPECTED_PRODUCTION
    )
    assert b"class EvidenceEnvelope" not in production_sources
    roadmap = " ".join(
        (REPOSITORY_ROOT / "docs/roadmap.md").read_text(encoding="utf-8").split()
    )
    assert "`S1.P02` is complete" in roadmap
    assert "`S1.P02.S07` is complete" in roadmap
    assert "`S1.P03` is complete" in roadmap
    assert "`S1.P03.S01` is complete" in roadmap
    assert "`S1.P03.S02` is complete" in roadmap
    assert "`S1.P03.S03` is complete" in roadmap
    assert "`S1.P03.S04` is complete" in roadmap
    assert (
        "`S1.P03.S05`, `S1.P03.S06`, `S1.P03.S07`, `S1.P03.S08`, and "
        "`S1.P03.S09` are complete" in roadmap
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
    assert "`S1.P04.S09` is complete" in roadmap
    assert "`S1.P04.S10` is next and not started" in roadmap
    assert "`S1.P05` through `S1.P10` remain not started" in roadmap


def test_group_n_candidate_publication_semantics_are_exact() -> None:
    document = _load_closure()
    _assert_candidate(document)
    _assert_ledger(document)
    payload = (CLOSURE_ROOT / "closure.json").read_text(encoding="utf-8")
    assert '"publication_state":"published"' not in payload
    assert '"operational_completion":"complete"' not in payload


def test_group_o_payload_is_private_and_retention_safe() -> None:
    combined = b"\n".join(
        (CLOSURE_ROOT / name).read_bytes() for name in sorted(EXPECTED_CLOSURE_FILES)
    )
    _assert_private_payload(combined)


def test_group_o_actual_offline_archives_exclude_closure_and_tests(
    tmp_path: Path,
) -> None:
    uv = shutil.which("uv")
    assert uv is not None
    output = tmp_path / "dist"
    cache = tmp_path / "uv-cache"
    output.mkdir()
    cache.mkdir()
    environment = os.environ.copy()
    for variable in (
        "CONDA_DEFAULT_ENV",
        "CONDA_PREFIX",
        "CONDA_PROMPT_MODIFIER",
        "PYTHONHOME",
        "PYTHONPATH",
    ):
        environment.pop(variable, None)
    environment.update(
        {
            "PYTHONDONTWRITEBYTECODE": "1",
            "UV_CACHE_DIR": str(cache),
            "UV_MANAGED_PYTHON": "1",
            "UV_NO_SYNC": "1",
            "UV_OFFLINE": "1",
        }
    )
    before = subprocess.run(
        ["git", "status", "--porcelain=v2", "--untracked-files=all"],
        cwd=REPOSITORY_ROOT,
        check=True,
        capture_output=True,
    ).stdout
    result = subprocess.run(
        [uv, "build", "--offline", "--out-dir", str(output)],
        cwd=REPOSITORY_ROOT,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
    )
    after = subprocess.run(
        ["git", "status", "--porcelain=v2", "--untracked-files=all"],
        cwd=REPOSITORY_ROOT,
        check=True,
        capture_output=True,
    ).stdout
    assert after == before
    assert result.returncode == 0, (
        f"offline build failed\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )
    wheels = tuple(output.glob("*.whl"))
    sdists = tuple(output.glob("*.tar.gz"))
    assert len(wheels) == len(sdists) == 1
    project_license = (REPOSITORY_ROOT / "LICENSE").read_bytes()
    historical_license = (
        REPOSITORY_ROOT / "reference_corpus/pytest-4412/acquisitions/"
        "run-0001-s04-v1-base-4c9cde74-head-690a63b9/artifacts/LICENSE"
    ).read_bytes()
    _assert_archive(
        _read_wheel(wheels[0]),
        archive_name=wheels[0].name,
        project_license=project_license,
        historical_license=historical_license,
    )
    _assert_archive(
        _read_sdist(sdists[0]),
        archive_name=sdists[0].name,
        project_license=project_license,
        historical_license=historical_license,
    )


def test_required_mutation_inventory_is_exact() -> None:
    assert len(REQUIRED_MUTATIONS) == len(set(REQUIRED_MUTATIONS)) == 44


@pytest.mark.parametrize("missing", (EVIDENCE_MODULE, SNAPSHOT_MODULE))
def test_current_inventory_and_export_mutations_are_rejected(missing: str) -> None:
    with pytest.raises(AssertionError):
        _validate_current_production_inventory(CURRENT_PRODUCTION_FILES - {missing})
    with pytest.raises(AssertionError):
        _validate_current_production_inventory(
            CURRENT_PRODUCTION_FILES | {"src/faultatlas/domain/unexpected.py"}
        )

    source = (REPOSITORY_ROOT / EVIDENCE_MODULE).read_text(encoding="utf-8")
    missing_export = source.replace('    "RetrievalRequestReference",\n', "", 1)
    assert missing_export != source
    with pytest.raises(AssertionError):
        _validate_current_evidence_inventory(missing_export.encode())
    unexpected_export = source.replace(
        '    "RetrievalRequestReference",\n',
        '    "RetrievalRequestReference",\n    "UnexpectedEvidence",\n',
        1,
    )
    assert unexpected_export != source
    with pytest.raises(AssertionError):
        _validate_current_evidence_inventory(unexpected_export.encode())


@pytest.mark.parametrize(
    "early_surface",
    (
        "RequestControls",
        "ResponseRepresentationObservation",
        "RetainedArtifactRecord",
        "AcquisitionRunRecord",
        "TransformationRecord",
        "CorrectionRecord",
        "SupersessionRecord",
        "OmissionRecord",
        "CompletenessRecord",
        "PublicationProvenance",
        "EvidenceAdapterRegistry",
        "EvidenceConfidence",
        "EvidenceContractCorpus",
        "EvidenceReview",
        "RepositorySnapshot",
    ),
)
def test_current_p03_post_s07_surface_is_rejected(early_surface: str) -> None:
    source = (REPOSITORY_ROOT / EVIDENCE_MODULE).read_bytes()
    mutated = source + f"\nclass {early_surface}:\n    pass\n".encode()
    with pytest.raises(AssertionError):
        _validate_current_evidence_inventory(mutated)


@pytest.mark.parametrize("mutation", REQUIRED_MUTATIONS)
def test_required_mutation_is_rejected(mutation: str, tmp_path: Path) -> None:
    primary = (CLOSURE_ROOT / "closure.json").read_bytes()
    sidecar = (CLOSURE_ROOT / "closure.sha256").read_bytes()
    document = copy.deepcopy(_load_closure())

    if mutation == "changed-closure-json-byte":
        mutated = primary.replace(b'"phase":"S1.P02"', b'"phase":"S1.P99"', 1)
        with pytest.raises(AssertionError):
            _assert_primary(mutated)
        return
    if mutation == "coordinated-json-sidecar-reseal":
        document["phase_identity"]["phase"] = "S1.P99"
        mutated = _canonical_bytes(document)
        resealed = f"{_sha256(mutated)}  closure.json\n".encode()
        assert resealed == f"{_sha256(mutated)}  closure.json\n".encode()
        with pytest.raises(AssertionError):
            _assert_primary(mutated)
        return
    if mutation in {
        "uppercase-sidecar-digest",
        "wrong-sidecar-basename",
        "missing-terminal-lf",
        "extra-terminal-lf",
    }:
        if mutation == "uppercase-sidecar-digest":
            mutated_sidecar = sidecar[:64].upper() + sidecar[64:]
        elif mutation == "wrong-sidecar-basename":
            mutated_sidecar = sidecar.replace(b"closure.json", b"candidate.json")
        elif mutation == "missing-terminal-lf":
            mutated_sidecar = sidecar.rstrip(b"\n")
        else:
            mutated_sidecar = sidecar + b"\n"
        with pytest.raises(AssertionError):
            _assert_sidecar(mutated_sidecar, primary)
        return
    if mutation == "non-canonical-json":
        pretty = (
            json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True).encode()
            + b"\n"
        )
        with pytest.raises(AssertionError):
            _parse_canonical(pretty)
        return
    if mutation in {
        "broken-p00-lock",
        "broken-p01-lock",
        "broken-revision-locator-corpus-lock",
        "broken-retained-diff-lock",
    }:
        prefixes = {
            "broken-p00-lock": "reference_corpus/pytest-4412/closures/s1-p00",
            "broken-p01-lock": "reference_corpus/contracts/identity/closures/s1-p01",
            "broken-revision-locator-corpus-lock": "reference_corpus/contracts/revision-locator/v1",
            "broken-retained-diff-lock": "reference_corpus/pytest-4412/acquisitions/",
        }
        item = next(
            value
            for value in document["source_locks"]["immutable_inputs"]
            if value["path"].startswith(prefixes[mutation])
        )
        item["sha256"] = "0" * 64
        with pytest.raises(AssertionError):
            _assert_document(document)
        return
    if mutation in {
        "missing-ledger-entry",
        "duplicate-ledger-id",
        "reordered-ledger",
        "fabricated-s07-pr-identifier",
    }:
        entries = document["slice_ledger"]["entries"]
        if mutation == "missing-ledger-entry":
            entries.pop(1)
        elif mutation == "duplicate-ledger-id":
            entries[1]["slice_id"] = entries[0]["slice_id"]
        elif mutation == "reordered-ledger":
            entries[0], entries[1] = entries[1], entries[0]
        else:
            entries[-1]["pull_request"] = 30
        with pytest.raises(AssertionError):
            _assert_document(document)
        return
    if mutation in {"criterion-unsatisfied", "required-criterion-removed"}:
        if mutation == "criterion-unsatisfied":
            document["exit_criteria"]["items"][0]["outcome"] = "unsatisfied"
        else:
            document["exit_criteria"]["items"].pop()
        with pytest.raises(AssertionError):
            _assert_document(document)
        return
    if mutation in {
        "deferred-missing-immediate-owner",
        "deferred-missing-long-term-owner",
        "completed-p02-behavior-marked-unresolved",
    }:
        item = document["deferred_register"]["items"][0]
        if mutation == "deferred-missing-immediate-owner":
            item["immediate_owner"] = ""
        elif mutation == "deferred-missing-long-term-owner":
            item["preserved_long_term_owner"] = ""
        else:
            item["subject"] = "Git object identity"
        with pytest.raises(AssertionError):
            _assert_document(document)
        return
    if mutation in {"p03-marked-started", "p03-marked-ineligible"}:
        if mutation == "p03-marked-started":
            document["entry_readiness"]["implementation"] = "started"
        else:
            document["entry_readiness"]["status"] = "ineligible"
        with pytest.raises(AssertionError):
            _assert_document(document)
        return
    if mutation == "candidate-marked-published":
        document["format"]["publication_state"] = "published"
        with pytest.raises(AssertionError):
            _assert_document(document)
        return
    if mutation == "source-lock-self-reference":
        document["source_locks"]["immutable_inputs"][0]["path"] = (
            f"{CLOSURE_RELATIVE}/closure.json"
        )
        with pytest.raises(AssertionError):
            _assert_document(document)
        return
    if mutation == "source-lock-cycle":
        document["source_locks"]["dependency_graph"]["nodes"][0]["predecessors"] = [
            "observation:production"
        ]
        with pytest.raises(AssertionError):
            _assert_document(document)
        return
    if mutation == "mutable-latest-pointer":
        document["source_locks"]["mutable_pointer"] = True
        with pytest.raises(AssertionError):
            _assert_document(document)
        return
    if mutation in {"unexpected-production-source", "missing-production-source"}:
        paths = set(EXPECTED_PRODUCTION)
        if mutation == "unexpected-production-source":
            paths.add("src/faultatlas/domain/unexpected.py")
        else:
            paths.remove("src/faultatlas/domain/revision.py")
        with pytest.raises(AssertionError):
            _validate_production_inventory(paths)
        return
    if mutation in {"missing-revision-export", "unexpected-revision-export"}:
        exports: list[str] = list(EXPECTED_EXPORTS)
        if mutation == "missing-revision-export":
            exports.pop()
        else:
            exports.append("UnexpectedRevision")
        with pytest.raises(AssertionError):
            _validate_exports(tuple(exports))
        return
    if mutation == "package-root-revision-export":
        package_source = (
            (REPOSITORY_ROOT / "src/faultatlas/__init__.py")
            .read_bytes()
            .replace(
                b'__all__ = ["__version__"]',
                b'__all__ = ["__version__", "RevisionLineLocator"]',
                1,
            )
        )
        with pytest.raises(AssertionError):
            _validate_package_root_exports(_parse_module_exports(package_source))
        return
    if mutation in {
        "production-corpus-reader-inserted",
        "locator-resolver-inserted",
        "evidence-envelope-production-surface-inserted",
    }:
        sources = {
            relative: (REPOSITORY_ROOT / relative).read_bytes()
            for relative in EXPECTED_PRODUCTION
        }
        injected = {
            "production-corpus-reader-inserted": b"\nclass RevisionLocatorCorpusReader:\n    pass\n",
            "locator-resolver-inserted": b"\nclass LocatorResolver:\n    pass\n",
            "evidence-envelope-production-surface-inserted": b"\nclass EvidenceEnvelope:\n    pass\n",
        }[mutation]
        sources["src/faultatlas/domain/revision.py"] += injected
        with pytest.raises(AssertionError):
            _assert_no_production_reader_or_p03(sources)
        return
    if mutation in {
        "replay-vector-total-changed",
        "selected-byte-digest-changed",
        "evidence-classification-changed",
        "coordinate-convention-changed",
    }:
        replay = document["replay_assurance"]
        if mutation == "replay-vector-total-changed":
            replay["replay_vector_count"] = 9
        elif mutation == "selected-byte-digest-changed":
            replay["byte_slices"][0]["selected_sha256"] = "0" * 64
        elif mutation == "evidence-classification-changed":
            replay["evidence_classifications"][0] = "reviewed_derived_interpretation"
        else:
            replay["coordinate_conventions"]["artifact_bytes"] = "one_based_inclusive"
        with pytest.raises(AssertionError):
            _assert_document(document)
        return
    if mutation in {"closure-filesystem-mode-0755", "closure-filesystem-mode-0600"}:
        path = tmp_path / "closure.json"
        path.write_bytes(primary)
        path.chmod(0o755 if mutation.endswith("0755") else 0o600)
        with pytest.raises(AssertionError):
            _assert_regular_0644(path)
        return
    if mutation == "closure-git-mode-100755":
        with pytest.raises(AssertionError):
            _assert_git_modes(
                {f"{CLOSURE_RELATIVE}/closure.json": "100755"},
                {f"{CLOSURE_RELATIVE}/closure.json"},
            )
        return
    if mutation == "closure-symlink":
        target = tmp_path / "target"
        target.write_bytes(primary)
        link = tmp_path / "closure.json"
        link.symlink_to(target)
        with pytest.raises(AssertionError):
            _assert_regular_0644(link)
        return
    if mutation in {
        "synthetic-package-closure-member",
        "historical-pytest-license-inserted",
    }:
        project_license = (REPOSITORY_ROOT / "LICENSE").read_bytes()
        historical_license = (
            REPOSITORY_ROOT / "reference_corpus/pytest-4412/acquisitions/"
            "run-0001-s04-v1-base-4c9cde74-head-690a63b9/artifacts/LICENSE"
        ).read_bytes()
        if mutation == "synthetic-package-closure-member":
            name = f"{CLOSURE_RELATIVE}/closure.json"
            data = primary
        else:
            name = "faultatlas-0.1.0/COPYING.pytest"
            data = historical_license
        with pytest.raises(AssertionError):
            _assert_archive(
                _synthetic_archive_members(extra_name=name, extra_data=data),
                archive_name="faultatlas-0.1.0-py3-none-any.whl",
                project_license=project_license,
                historical_license=historical_license,
            )
        return
    raise AssertionError(f"unhandled mutation: {mutation}")
