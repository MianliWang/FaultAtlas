from __future__ import annotations

import ast
import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import tarfile
import zipfile
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Any, cast

import pytest
from pydantic import BaseModel, ValidationError

import faultatlas
import faultatlas.domain.compatibility as compatibility_module
import faultatlas.domain.identity as identity_module
import faultatlas.domain.revision as revision_module
from faultatlas.domain.compatibility import (
    LegacyObjectIdInterpretation,
    map_legacy_source_locator,
)
from faultatlas.domain.identity import (
    AuthorityRole,
    IdentityFieldState,
    IdentityValueState,
    NumberedSourceObjectIdentity,
    ProviderAuthority,
    ProviderGlobalId,
    ProviderKey,
    ProviderRepositoryId,
    RepositoryAliasObservation,
    RepositoryIdentity,
    RepositoryScopedNumber,
    SourceIdentity,
    SourceObjectKind,
)
from faultatlas.domain.source import SourceLocator

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
CLOSURE_RELATIVE = Path(
    "reference_corpus/contracts/identity/closures/s1-p01-phase-closure"
)
CLOSURE_ROOT = REPOSITORY_ROOT / CLOSURE_RELATIVE
P00_ROOT = (
    REPOSITORY_ROOT / "reference_corpus/pytest-4412/closures/s1-p00-phase-closure"
)
V1_ROOT = REPOSITORY_ROOT / "reference_corpus/contracts/identity/v1"
C01_ROOT = (
    REPOSITORY_ROOT / "reference_corpus/contracts/identity/corrections/"
    "s05-c01-ambiguous-union-round-trip"
)
REVISION_LOCATOR_ROOT = (
    REPOSITORY_ROOT / "reference_corpus/contracts/revision-locator/v1"
)

EXPECTED_CLOSURE_FILES = {"closure.json", "closure.md", "closure.sha256"}
EXPECTED_V1_FILES = {
    "compatibility-vectors.json",
    "compatibility-vectors.sha256",
    "contract.md",
    "invalid-vectors.json",
    "invalid-vectors.sha256",
    "manifest.json",
    "manifest.sha256",
    "valid-vectors.json",
    "valid-vectors.sha256",
}
EXPECTED_C01_FILES = {
    "correction.json",
    "correction.md",
    "correction.sha256",
    "regression-vectors.json",
    "regression-vectors.sha256",
}
EXPECTED_REVISION_LOCATOR_FILES = {
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
EXPECTED_JSON_BYTES = 112606
EXPECTED_JSON_SHA256 = (
    "2c1bfb9d3d596711066796ef83999d49b6846e65315a301eead7fa8fb5ac4642"
)
EXPECTED_SIDECAR_BYTES = 79
EXPECTED_SIDECAR_SHA256 = (
    "8c1bc1ff60ef2ae25f0bca5abd696708b9a59b2fadd15bd7586a9fb868c262ae"
)
EXPECTED_MARKDOWN_BYTES = 3847
EXPECTED_MARKDOWN_SHA256 = (
    "cfde27cbd9d8d1fc979ffb3d878999663cc52a25e5f07d60b70b2791e69292ca"
)
EXPECTED_FORMAT = "faultatlas-s1-p01-identity-primitives-phase-closure"
EXPECTED_FORMAT_VERSION = "1"
EXPECTED_BASELINE = "f087492875635f5c99387a6354fb5acc1376dde2"
EXPECTED_BASELINE_TREE = "97e2c10e6cbf3247c7ec5905149518ca0ab5845f"
EXPECTED_TOP_LEVEL = {
    "assurance",
    "deferred_register",
    "effective_contract_assurance",
    "entry_readiness",
    "established_findings",
    "exit_criteria",
    "format",
    "implementation_inventory",
    "non_generalizations",
    "phase_identity",
    "publication_contract",
    "review_settlement",
    "roundtrip_correction_assurance",
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
    "reference_corpus/contracts/identity/v1/manifest.json": LockedFile(
        7586, "aafa6dee23971218f30f9c72f63e23741841f0852299bebf9f40471054cb760a"
    ),
    "reference_corpus/contracts/identity/v1/manifest.sha256": LockedFile(
        80, "b5769ead5196aa7ea780be5920efc295d16673e93ecc010b45394aaa4bd58173"
    ),
    "reference_corpus/contracts/identity/v1/valid-vectors.json": LockedFile(
        46891, "f58df3e6f123c468b8bc1f3185769e6d0773b4942a90207d7ec4fb37b26f8ef7"
    ),
    "reference_corpus/contracts/identity/v1/valid-vectors.sha256": LockedFile(
        85, "912070e5f3772a59985a57d623e2ab16caadd70ca902bab2e0bd13183c15c33e"
    ),
    "reference_corpus/contracts/identity/v1/invalid-vectors.json": LockedFile(
        56435, "d2d700c1e553df907dc43be73e40881e0f937472dbe40c65c9b7d5556cab4bc6"
    ),
    "reference_corpus/contracts/identity/v1/invalid-vectors.sha256": LockedFile(
        87, "32b5a8845243e5202464dbd09f6b06ee5dd750c69a8768fb5cea415f9e3a2fb7"
    ),
    "reference_corpus/contracts/identity/v1/compatibility-vectors.json": LockedFile(
        53810, "f3f9248c2562bb4a545b2e14d25d0346689bbf5b346ca343a8974b317d4b79ac"
    ),
    "reference_corpus/contracts/identity/v1/compatibility-vectors.sha256": LockedFile(
        93, "9c19cc782e935fa2a5954cebbcc7055a9c6cc895b657b36d5e5781f7169931ec"
    ),
    "reference_corpus/contracts/identity/v1/contract.md": LockedFile(
        3329, "4c3d44194d1708d1493808022212476ca4bfb3324ed3b620cbd7d9f830fcd806"
    ),
    "reference_corpus/contracts/identity/corrections/s05-c01-ambiguous-union-round-trip/correction.json": LockedFile(
        12436, "c17edfa5dc227850d6b982d1ec8c83b4236cd403bb7ca1b1c66b662f8657347a"
    ),
    "reference_corpus/contracts/identity/corrections/s05-c01-ambiguous-union-round-trip/correction.sha256": LockedFile(
        82, "d63684a33ca94471ff62485064850f1db7b5a8ec7eab25f3902b0afa529aec7e"
    ),
    "reference_corpus/contracts/identity/corrections/s05-c01-ambiguous-union-round-trip/correction.md": LockedFile(
        2808, "32eae618dc35a124f93f9dcac3682fb27fb7621c5a1065331be5584ec972bcc0"
    ),
    "reference_corpus/contracts/identity/corrections/s05-c01-ambiguous-union-round-trip/regression-vectors.json": LockedFile(
        26111, "721b6a97a7b80dcc1d33643f6920b21d2e2a8b010d8528f8d194a6691a3feff2"
    ),
    "reference_corpus/contracts/identity/corrections/s05-c01-ambiguous-union-round-trip/regression-vectors.sha256": LockedFile(
        90, "d8a881d7ec3bc9908fedd5b7eeb2ab03d9e241e12dbf90a45d477eae4acf1ed1"
    ),
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
}
CURRENT_PRODUCTION_FILES = {
    *EXPECTED_PRODUCTION,
    "src/faultatlas/domain/revision.py",
    "src/faultatlas/domain/evidence.py",
}
EVIDENCE_MODULE = "src/faultatlas/domain/evidence.py"
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
)
FORBIDDEN_POST_S03_EVIDENCE_SURFACE_FRAGMENTS = (
    "adapter",
    "completeness",
    "corpus",
    "correction",
    "envelope",
    "omission",
    "publication",
    "supersession",
    "transformation",
)

EXPECTED_IDENTITY_EXPORTS = {
    "AuthorityRole",
    "IdentityFieldState",
    "IdentityValueState",
    "NumberedSourceObjectIdentity",
    "ProviderAuthority",
    "ProviderGlobalId",
    "ProviderKey",
    "ProviderNodeId",
    "ProviderRepositoryId",
    "ProviderScopedSourceObjectIdentity",
    "RepositoryAliasObservation",
    "RepositoryIdentity",
    "RepositoryScopedNumber",
    "SourceIdentity",
    "SourceIdentityLifecycleObservation",
    "SourceIdentityLifecycleState",
    "SourceObjectKind",
}
EXPECTED_COMPATIBILITY_EXPORTS = {
    "CompatibilityStatus",
    "LegacyCompatibilityReason",
    "LegacyObjectIdInterpretation",
    "LegacySourceLocatorMappingResult",
    "LegacySourceLocatorProjectionResult",
    "map_legacy_source_locator",
    "project_source_identity_to_legacy",
}
EXPECTED_S05_REVISION_EXPORTS = {
    "ArtifactByteLocator",
    "BoundedLocator",
    "DiffHunkLocator",
    "LineEnding",
    "OneBasedInclusiveLineSpan",
    "RevisionLineLocator",
    "TextEncoding",
    "ZeroBasedHalfOpenByteSpan",
}
EXPECTED_REVISION_EXPORTS = {
    *EXPECTED_S05_REVISION_EXPORTS,
    "GitBlobIdentity",
    "GitCommitIdentity",
    "GitCommitParentTopology",
    "GitHashAlgorithm",
    "GitObjectIdentity",
    "GitObjectKind",
    "GitRefName",
    "GitRefNamespace",
    "GitRefObservation",
    "GitRepositoryPath",
    "GitRevisionIdentity",
    "GitTreeIdentity",
    "RevisionQualifiedPath",
    "RevisionRole",
    "RevisionRoleAssignment",
}
EXPECTED_LEDGER = (
    "S1.P01.S01",
    "S1.P01.S02",
    "S1.P01.S03",
    "S1.P01.S04",
    "S1.P01.S05",
    "S1.P01.S05.C01",
    "S1.P01.S06",
)
EXPECTED_PUBLICATION_EVIDENCE = (
    (
        17,
        "6851e0aee7cceef858e5fe1a4dd6676b6486504b",
        "7298d007e72988459a2081aa652efa1350a4fdde",
        "59e312d3412d92cb3cf0fc3721c04189413998be",
        30614222807,
        91103594814,
        30614315170,
        91103883266,
        371,
    ),
    (
        18,
        "0b49a221a4aa907718c64e2f3c366a1b1778253c",
        "4108e9e6dd43ae56c9bc481237cbc024af822ab8",
        "87060eaf9b16878581e4c6094e2a8d75ad827ed2",
        30620012920,
        91122112938,
        30620220062,
        91122770100,
        524,
    ),
    (
        19,
        "ba657f2a4bc76b075fe8ddcd59d14f423cb7ab19",
        "3a54fd51a97a3e8bfe92661c69e62cbbb53227ee",
        "26f7bf75b5a25c0f9f9a6f19796719b554b4d4d7",
        30623118940,
        91132037556,
        30623261249,
        91132493666,
        631,
    ),
    (
        20,
        "822d96e1f6a3438260781d7000280eb0576a5a0a",
        "b7cd6ecd84c9377c5ec3da2e79433989d9ce3e50",
        "05736e1bdde72eeb4431b11448db4ed7f8e3b36c",
        30657507686,
        91245462997,
        30657652283,
        91245944510,
        715,
    ),
    (
        21,
        "5ca1eaf6253dd7d1cea9a61fed259a2d13707401",
        "2d73d4b9697a3a34216165791e066a35a2fe2bfa",
        "3edd4024848d7e60cb506358913102f1d0958e7c",
        30662697018,
        91262389411,
        30662858781,
        91262909157,
        937,
    ),
    (
        22,
        "261cf7589d7eb4f858abb4ae789175bb081cc4d5",
        "97e2c10e6cbf3247c7ec5905149518ca0ab5845f",
        EXPECTED_BASELINE,
        30683618873,
        91325223719,
        30683722772,
        91325525281,
        1037,
    ),
)
EXPECTED_THREADS = (
    (19, 3689734505, 3694599405, "PRRT_kwDOTa_Fi86VYvjC"),
    (21, 3693174956, 3694599708, "PRRT_kwDOTa_Fi86Vhxf1"),
    (21, 3693174960, 3694599739, "PRRT_kwDOTa_Fi86Vhxf4"),
)

EXPECTED_CRITERIA = (
    "exit:p00-prerequisite-closure-valid",
    "exit:s01-s05-publication-reconciled",
    "exit:s05-c01-publication-reconciled",
    "exit:historical-review-findings-resolved",
    "exit:protected-publication-workflow-operational",
    "exit:provider-identity-implemented",
    "exit:navigation-retrieval-authorities-distinct",
    "exit:repository-identity-alias-independent",
    "exit:repository-alias-observations-qualified",
    "exit:repository-scoped-number-typed",
    "exit:provider-global-id-typed",
    "exit:provider-node-id-typed",
    "exit:issue-pr-identities-distinct",
    "exit:child-identities-parent-scoped",
    "exit:source-index-excluded-from-identity",
    "exit:nine-field-states-distinct",
    "exit:present-absent-conflict-valid",
    "exit:conflict-retains-candidates-no-winner",
    "exit:lifecycle-preserves-known-identity",
    "exit:observation-provider-event-time-distinct",
    "exit:monomorphic-roundtrip-type-equality",
    "exit:structured-union-roundtrip-type-equality",
    "exit:ambiguous-scalar-unions-reject",
    "exit:compatibility-domain-discrimination",
    "exit:same-lexeme-candidates-distinct-ordered",
    "exit:no-alternate-id-equivalence",
    "exit:legacy-source-locator-unchanged",
    "exit:legacy-object-id-ambiguity-explicit",
    "exit:legacy-to-typed-explicit-loss-aware",
    "exit:typed-to-legacy-conditional-lossy",
    "exit:compatibility-distinct-from-migration",
    "exit:s05-v1-immutable",
    "exit:s05-c01-append-only-immutable",
    "exit:supersession-replacement-complete",
    "exit:effective-contract-199",
    "exit:valid-vectors-cover-exports",
    "exit:invalid-vectors-enforce-rejection",
    "exit:compatibility-correction-enforce-boundaries",
    "exit:safe-test-registry",
    "exit:no-production-corpus-reader",
    "exit:production-source-inventory-exact",
    "exit:permissions-exact",
    "exit:package-root-exports-unchanged",
    "exit:source-only-material-package-excluded",
    "exit:legacy-p00-corpus-artifacts-unchanged",
    "exit:remaining-p01-semantics-owned",
    "exit:no-unresolved-p01-blocker",
    "exit:roadmap-current",
    "exit:full-validation-green",
    "exit:p02-entry-prerequisites-satisfied",
)
EXPECTED_PREREQUISITES = (
    "p02-entry:p00-closure-valid",
    "p02-entry:p01-candidate-internally-valid",
    "p02-entry:s05-v1-valid",
    "p02-entry:s05-c01-valid",
    "p02-entry:effective-contract-199",
    "p02-entry:ambiguous-union-corrected",
    "p02-entry:historical-reviews-resolved",
    "p02-entry:identity-module-present",
    "p02-entry:compatibility-module-present",
    "p02-entry:legacy-source-unchanged",
    "p02-entry:source-inventory-exact",
    "p02-entry:permissions-exact",
    "p02-entry:no-public-identity-api",
    "p02-entry:no-git-object-identity",
    "p02-entry:no-ref-observation",
    "p02-entry:no-revision-qualified-locator",
    "p02-entry:p00-p01-tests-green",
    "p02-entry:packages-exclude-corpora",
    "p02-entry:protected-pr-workflow-operational",
    "p02-entry:no-p01-blocker",
)

EXPECTED_DEFERRED = {
    "deferred:p01:p02-git-object-identity": ("implementation_deferred", "S1.P02"),
    "deferred:p01:p02-hash-algorithm-qualification": (
        "implementation_deferred",
        "S1.P02",
    ),
    "deferred:p01:p02-commit-tree-blob-distinction": (
        "implementation_deferred",
        "S1.P02",
    ),
    "deferred:p01:p02-revision-role-assignment": ("implementation_deferred", "S1.P02"),
    "deferred:p01:p02-ordered-merge-parents": ("implementation_deferred", "S1.P02"),
    "deferred:p01:p02-mutable-ref-observations": ("implementation_deferred", "S1.P02"),
    "deferred:p01:p02-deleted-ref-behavior": ("implementation_deferred", "S1.P02"),
    "deferred:p01:p02-revision-qualified-paths": ("implementation_deferred", "S1.P02"),
    "deferred:p01:p02-line-coordinate-contract": ("provisional_design", "S1.P02"),
    "deferred:p01:p02-byte-coordinate-contract": ("provisional_design", "S1.P02"),
    "deferred:p01:p02-diff-hunk-locator-contract": ("provisional_design", "S1.P02"),
    "deferred:p01:p03-evidence-envelope": ("provisional_design", "S1.P03"),
    "deferred:p01:p03-request-response-provenance": (
        "implementation_deferred",
        "S1.P03",
    ),
    "deferred:p01:p03-representation-exact-artifact-separation": (
        "implementation_deferred",
        "S1.P03",
    ),
    "deferred:p01:p03-transformation-lineage": ("implementation_deferred", "S1.P03"),
    "deferred:p01:p03-omission-completeness": ("provisional_design", "S1.P03"),
    "deferred:p01:p03-correction-references": ("implementation_deferred", "S1.P03"),
    "deferred:p01:p04-repository-snapshot-aggregation": (
        "provisional_design",
        "S1.P04",
    ),
    "deferred:p01:p05-development-history-event-model": (
        "provisional_design",
        "S1.P05",
    ),
    "deferred:p01:p05-development-history-relationship-model": (
        "provisional_design",
        "S1.P05",
    ),
    "deferred:p01:p09-actor-reviewer-attribution-identity": (
        "provisional_design",
        "S1.P09",
    ),
    "deferred:p01:p09-alternate-id-binding-review": ("provisional_design", "S1.P09"),
    "deferred:p01:p09-conflict-review-resolution": ("provisional_design", "S1.P09"),
    "deferred:p01:p09-claim-confidence-review": ("provisional_design", "S1.P09"),
    "deferred:p01:p10-production-readers-writers": ("provisional_design", "S1.P10"),
    "deferred:p01:p10-canonical-serialization": ("implementation_deferred", "S1.P10"),
    "deferred:p01:p10-migration-registry": ("provisional_design", "S1.P10"),
    "deferred:p01:p10-persistence-neutral-compatibility": (
        "provisional_design",
        "S1.P10",
    ),
    "deferred:p01:p10-contract-corpus-evolution": ("implementation_deferred", "S1.P10"),
    "deferred:p01:evidence-private-github": ("evidence_insufficient", "S1.P08"),
    "deferred:p01:evidence-github-enterprise": ("evidence_insufficient", "S1.P08"),
    "deferred:p01:evidence-other-source-providers": ("evidence_insufficient", "S1.P08"),
    "deferred:p01:evidence-non-git-vcs": ("evidence_insufficient", "S1.P08"),
    "deferred:p01:evidence-original-head-repository": (
        "evidence_insufficient",
        "S1.P05",
    ),
    "deferred:p01:evidence-historical-source-completeness": (
        "evidence_insufficient",
        "S1.P05",
    ),
    "deferred:p01:evidence-historical-actor-review-completeness": (
        "evidence_insufficient",
        "S1.P09",
    ),
    "deferred:p01:p06-stale-cache-causation": ("evidence_insufficient", "S1.P06"),
    "deferred:p01:p07-pattern-generality": ("evidence_insufficient", "S1.P07"),
    "deferred:p01:p08-transfer-applicability": ("evidence_insufficient", "S1.P08"),
    "deferred:p01:p10-legacy-removal-timeline": ("provisional_design", "S1.P10"),
}

EXPECTED_FINDINGS = {
    "finding:provider-identity-not-authority",
    "finding:navigation-not-retrieval-authority",
    "finding:repository-identity-not-alias",
    "finding:repository-number-not-global-id",
    "finding:node-id-distinct",
    "finding:object-kind-participates-in-identity",
    "finding:child-identity-parent-scoped",
    "finding:source-index-not-identity",
    "finding:nine-field-states-distinct",
    "finding:conflict-no-implicit-winner",
    "finding:known-identity-survives-lifecycle",
    "finding:observation-time-not-provider-event-time",
    "finding:union-order-not-json-discriminator",
    "finding:ambiguous-scalar-union-domain-discrimination",
    "finding:monomorphic-scalar-roundtrip",
    "finding:structured-union-shape-discrimination",
    "finding:legacy-object-id-ambiguous",
    "finding:legacy-mapping-requires-repository-context",
    "finding:typed-to-legacy-lossy",
    "finding:compatibility-not-migration",
    "finding:append-only-correction-preserves-history",
    "finding:whole-source-inventory-current-not-v1-frozen",
    "finding:non-executable-weaker-than-exact-modes",
    "finding:effective-contract-overlay-executable",
    "finding:offline-replay-package-exclusion-feasible",
}
EXPECTED_NON_GENERALIZATIONS = {
    f"non-generalization:{suffix}"
    for suffix in (
        "actor-user-identity",
        "reviewer-identity",
        "login-observation-contracts",
        "alternate-id-binding-equivalence",
        "conflict-review-resolution",
        "git-commit-tree-blob-identity",
        "hash-algorithm-identity",
        "mutable-ref-identity",
        "revision-roles",
        "merge-parent-production-semantics",
        "revision-qualified-paths",
        "line-byte-hunk-locators",
        "evidence-envelope",
        "repository-snapshot-aggregation",
        "development-history-graph",
        "fault-model",
        "pattern-generality",
        "transfer-scoring",
        "confidence-claim-review",
        "persistence",
        "migration-registry",
        "public-identity-api",
        "private-github",
        "github-enterprise",
        "non-git-vcs",
        "universal-multi-provider-compatibility",
    )
}

EXPECTED_MARKDOWN_HEADINGS = (
    "# S1.P01 Identity Primitives Phase Closure",
    "## Executive verdict",
    "## Phase identity and scope",
    "## Ordered Slice and correction ledger",
    "## Implementation inventory",
    "## Effective contract: v1 plus C01",
    "## Round-trip correction assurance",
    "## Historical review settlement",
    "## Test, source, permission, and package assurance",
    "## Exit criteria",
    "## Established findings",
    "## Non-generalizations",
    "## Deferred register summary",
    "## S1.P02 entry readiness",
    "## S1.P02 scope guard",
    "## Publication conditions",
    "## Authority warning",
)
STABLE_AMBIGUOUS_MESSAGE = (
    "IdentityValueState specialization has ambiguous scalar JSON representations "
    "and requires a domain-discriminated carrier"
)
SUPERSEDED_ID = "identity.valid.field-state.conflict-number-global"
REPLACEMENT_ID = (
    "identity.correction.s05-c01.generic-rejection.number-global.conflict-distinct-json"
)

REQUIRED_MUTATION_IDS = (
    "changed-json-byte",
    "coordinated-json-sidecar-reseal",
    "wrong-sidecar-basename",
    "missing-terminal-lf",
    "extra-terminal-lf",
    "pretty-json",
    "broken-p00-lock",
    "broken-v1-lock",
    "broken-c01-lock",
    "removed-ledger-item",
    "duplicate-ledger-id",
    "reordered-c01-s06",
    "fabricated-s06-pr",
    "unsatisfied-criterion",
    "missing-criterion",
    "missing-immediate-owner",
    "missing-long-term-owner",
    "ambiguous-union-deferred",
    "p02-started",
    "p02-ineligible",
    "candidate-published",
    "source-self-reference",
    "source-cycle",
    "mutable-latest",
    "unexpected-production-source",
    "missing-production-source",
    "missing-identity-export",
    "missing-compatibility-export",
    "package-root-identity-export",
    "production-corpus-reader",
    "changed-effective-vector-total",
    "superseded-without-replacement",
    "historical-thread-unresolved",
    "filesystem-mode-0755",
    "filesystem-mode-0600",
    "git-mode-100755",
    "closure-symlink",
    "synthetic-package-closure-member",
    "closure-fifo",
    "extra-closure-file",
)


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _no_float(value: Any) -> None:
    assert not isinstance(value, float)
    if isinstance(value, list):
        for item in cast(list[Any], value):
            _no_float(item)
    elif isinstance(value, dict):
        for item in cast(dict[str, Any], value).values():
            _no_float(item)


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
    value = json.loads(raw, object_pairs_hook=_unique_object)
    assert isinstance(value, dict)
    _no_float(value)
    assert _canonical_bytes(value) == raw
    return cast(dict[str, Any], value)


def _load_closure() -> dict[str, Any]:
    return _parse_canonical((CLOSURE_ROOT / "closure.json").read_bytes())


def _assert_primary_bytes(raw: bytes) -> dict[str, Any]:
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
        path = encoded_path.decode()
        assert stage == "0"
        modes[path] = mode
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


def _assert_git_modes_100644(modes: dict[str, str], expected: set[str]) -> None:
    assert set(modes) == expected
    assert all(mode == "100644" for mode in modes.values())


def _assert_graph(graph: dict[str, Any]) -> None:
    assert graph["node_count"] == 8
    assert graph["edge_count"] == 7
    assert graph["root_ids"] == ["source:p00-closure"]
    nodes = cast(list[dict[str, Any]], graph["nodes"])
    predecessors = {
        cast(str, node["id"]): cast(list[str], node["predecessors"]) for node in nodes
    }
    assert len(predecessors) == 8
    assert set(graph["root_ids"]) == {
        node_id for node_id, parents in predecessors.items() if not parents
    }
    visited: set[str] = set()
    active: set[str] = set()

    def visit(node_id: str) -> None:
        assert node_id in predecessors
        assert node_id not in active, "source-lock graph cycle"
        if node_id in visited:
            return
        active.add(node_id)
        for parent in predecessors[node_id]:
            visit(parent)
        active.remove(node_id)
        visited.add(node_id)

    for node_id in predecessors:
        visit(node_id)
    assert graph["acyclic"] is True


def _assert_source_locks(
    document: dict[str, Any], *, verify_files: bool = False
) -> None:
    source = cast(dict[str, Any], document["source_locks"])
    items = cast(list[dict[str, Any]], source["immutable_inputs"])
    observed = {
        cast(str, item["path"]): LockedFile(
            cast(int, item["byte_length"]), cast(str, item["sha256"])
        )
        for item in items
    }
    assert source["immutable_input_count"] == 17
    assert observed == EXPECTED_SOURCE_LOCKS
    assert source["self_reference"] is False
    assert source["mutable_pointer"] is False
    assert all("s1-p01-phase-closure" not in path for path in observed)
    for item in items:
        assert item["git_mode"] == "100644"
        assert item["filesystem_mode"] == "0644"
        _assert_safe_relative(cast(str, item["path"]))
    _assert_graph(cast(dict[str, Any], source["dependency_graph"]))
    if verify_files:
        for relative, expected in EXPECTED_SOURCE_LOCKS.items():
            raw = (REPOSITORY_ROOT / relative).read_bytes()
            assert len(raw) == expected.byte_length
            assert _sha256(raw) == expected.sha256


def _assert_ledger(document: dict[str, Any]) -> None:
    ledger = cast(dict[str, Any], document["slice_ledger"])
    entries = cast(list[dict[str, Any]], ledger["entries"])
    ids = tuple(cast(str, item["slice_id"]) for item in entries)
    assert ledger["count"] == 7
    assert tuple(ledger["order"]) == EXPECTED_LEDGER
    assert ids == EXPECTED_LEDGER
    assert len(ids) == len(set(ids))
    assert ledger["unique"] is True
    for item, expected in zip(entries[:-1], EXPECTED_PUBLICATION_EVIDENCE, strict=True):
        pr, head, tree, squash, pr_run, pr_job, main_run, main_job, tests = expected
        assert item["pull_request"] == pr
        assert item["primary_commit"] == head
        assert item["reviewed_head_sha"] == head
        assert item["reviewed_tree"] == tree
        assert item["squash_sha"] == squash
        assert item["required_pr_ci"] == {
            "conclusion": "success",
            "event": "pull_request",
            "head_sha": head,
            "job_id": pr_job,
            "job_name": "validate",
            "run_id": pr_run,
            "workflow": "CI",
        }
        assert item["natural_main_ci"]["run_id"] == main_run
        assert item["natural_main_ci"]["job_id"] == main_job
        assert item["natural_main_ci"]["head_sha"] == squash
        assert item["publication_test_count"] == tests
        assert item["reviewed_tree_equals_squash_tree"] is True
    s06 = entries[-1]
    assert set(s06) == {
        "candidate_changed_surfaces",
        "completion_state",
        "expected_publication_route",
        "external_operational_completion_conditions",
        "future_publication_identifiers",
        "purpose",
        "slice_id",
        "title",
    }
    assert s06["completion_state"] == "sealed_publication_candidate"
    assert s06["future_publication_identifiers"] == {
        "prohibited_in_candidate": [
            "pull_request",
            "reviewed_head",
            "merge",
            "PR_CI",
            "main_CI",
        ],
        "reason": "external_publication_evidence_is_unavailable_before_protected_publication",
        "state": "unavailable_in_self_contained_candidate",
    }


def _assert_inventory(document: dict[str, Any]) -> None:
    inventory = cast(dict[str, Any], document["implementation_inventory"])
    assert inventory["identity_export_count"] == 17
    assert {
        item["symbol"]
        for item in cast(list[dict[str, Any]], inventory["identity_exports"])
    } == EXPECTED_IDENTITY_EXPORTS
    assert inventory["compatibility_export_count"] == 7
    assert {
        item["symbol"]
        for item in cast(list[dict[str, Any]], inventory["compatibility_exports"])
    } == EXPECTED_COMPATIBILITY_EXPORTS
    package = cast(dict[str, Any], inventory["package_boundary"])
    assert set(package["production_files"]) == set(EXPECTED_PRODUCTION)
    assert package["package_root_exports"] == ["__version__"]
    assert package["package_version"] == "0.1.0"
    assert package["no_public_identity_API"] is True
    assert package["no_production_corpus_reader"] is True
    assert {item["model"] for item in inventory["legacy_models"]} == {
        "SourceLocator",
        "ArtifactSnapshot",
    }
    assert all(
        item["internal"]
        and item["legacy"]
        and item["provisional"]
        and item["unchanged_by_P01"]
        and item["not_reinterpreted"]
        for item in inventory["legacy_models"]
    )
    source = cast(dict[str, Any], document["source_locks"])
    observations = {
        item["path"]: LockedFile(item["byte_length"], item["sha256"])
        for item in source["production_observations"]
    }
    assert observations == EXPECTED_PRODUCTION


def _assert_effective_contract(document: dict[str, Any]) -> None:
    contract = cast(dict[str, Any], document["effective_contract_assurance"])
    assert (
        contract["historical_v1_vectors"],
        contract["superseded_current_vectors"],
        contract["active_historical_vectors"],
        contract["correction_vectors"],
        contract["effective_current_vectors"],
    ) == (168, 1, 167, 32, 199)
    assert contract["superseded_vector_id"] == SUPERSEDED_ID
    assert contract["replacement_vector_id"] == REPLACEMENT_ID
    assert contract["supersession_complete"] is True
    assert contract["historical_v1_byte_valid"] is True
    assert contract["no_v1_artifact_rewritten"] is True
    assert contract["append_only_correction"] is True
    assert contract["mutable_version_pointer"] is False
    assert contract["vector_inventory"] == {
        "compatibility": 30,
        "fixtures": 26,
        "invalid": 80,
        "unique_historical_ids": 168,
        "valid": 58,
    }


def _assert_review_settlement(document: dict[str, Any]) -> None:
    review = cast(dict[str, Any], document["review_settlement"])
    assert review["historical_thread_count"] == 3
    assert review["actionable_unresolved_count"] == 0
    assert review["corrective_pull_request"] == 22
    assert review["corrective_squash_sha"] == EXPECTED_BASELINE
    assert review["corrective_main_ci"]["run_id"] == 30683722772
    assert review["corrective_main_ci"]["job_id"] == 91325525281
    actual = tuple(
        (
            item["pull_request"],
            item["original_comment_id"],
            item["reply_comment_id"],
            item["thread_id"],
        )
        for item in review["threads"]
    )
    assert actual == EXPECTED_THREADS
    assert all(
        item["resolved"] and not item["outdated"] and item["reply_to_original_verified"]
        for item in review["threads"]
    )


def _assert_exit_criteria(document: dict[str, Any]) -> None:
    section = cast(dict[str, Any], document["exit_criteria"])
    items = cast(list[dict[str, Any]], section["items"])
    assert section["count"] == 50
    assert tuple(item["criterion_id"] for item in items) == EXPECTED_CRITERIA
    assert len(items) == len({item["criterion_id"] for item in items})
    controlled = {
        "satisfied",
        "satisfied_with_explicit_deferral",
        "not_applicable",
        "unsatisfied",
    }
    assert set(section["controlled_outcomes"]) == controlled
    actual_outcomes = [cast(str, item["outcome"]) for item in items]
    assert set(actual_outcomes) <= controlled
    actual_totals = Counter(actual_outcomes)
    for outcome in controlled:
        actual_totals.setdefault(outcome, 0)
    assert section["outcome_totals"] == {
        "not_applicable": 0,
        "satisfied": 49,
        "satisfied_with_explicit_deferral": 1,
        "unsatisfied": 0,
    }
    assert dict(actual_totals) == section["outcome_totals"]
    assert section["unsatisfied_count"] == actual_totals["unsatisfied"] == 0
    assert all(item["evidence"] and item["statement"] for item in items)
    assert all(item["outcome"] != "unsatisfied" for item in items)
    owned = next(
        item
        for item in items
        if item["criterion_id"] == "exit:remaining-p01-semantics-owned"
    )
    assert owned["outcome"] == "satisfied_with_explicit_deferral"
    assert set(owned["deferral"]["deferred_item_ids"]) == set(EXPECTED_DEFERRED)


def _assert_deferred(document: dict[str, Any]) -> None:
    section = cast(dict[str, Any], document["deferred_register"])
    items = cast(list[dict[str, Any]], section["items"])
    actual = {
        item["deferred_item_id"]: (
            item["current_state"],
            item["immediate_next_owner"],
        )
        for item in items
    }
    assert section["count"] == 40
    assert actual == EXPECTED_DEFERRED
    assert len(items) == len(actual)
    assert section["state_totals"] == {
        "evidence_insufficient": 10,
        "implementation_deferred": 14,
        "provisional_design": 16,
        "unsupported_current_scope": 0,
    }
    expected_owner_totals = {
        "S1.P02": 11,
        "S1.P03": 6,
        "S1.P04": 1,
        "S1.P05": 4,
        "S1.P06": 1,
        "S1.P07": 1,
        "S1.P08": 5,
        "S1.P09": 5,
        "S1.P10": 6,
    }
    assert section["immediate_owner_totals"] == expected_owner_totals
    assert section["long_term_owner_totals"] == expected_owner_totals
    assert section["owners_complete"] is True
    assert section["corrected_ambiguous_union_is_not_deferred"] is True
    for item in items:
        assert item["immediate_next_owner"]
        assert item["preserved_long_term_phase_owner"] == item["immediate_next_owner"]
        assert item["source_references"]
        assert item["reason_for_deferral"]
        assert item["latest_decision_point"]
        assert item["consequence_if_unresolved"]
        assert item["evidence"]
        assert "ambiguous-union" not in item["deferred_item_id"]


def _assert_readiness(document: dict[str, Any]) -> None:
    readiness = cast(dict[str, Any], document["entry_readiness"])
    prerequisites = cast(list[dict[str, Any]], readiness["prerequisites"])
    assert readiness["prerequisite_count"] == 20
    assert tuple(item["prerequisite_id"] for item in prerequisites) == (
        EXPECTED_PREREQUISITES
    )
    assert all(
        item["outcome"] == "satisfied" and item["evidence"] for item in prerequisites
    )
    assert readiness["status"] == "eligible_to_begin"
    assert readiness["implementation"] == "not_started"
    assert readiness["operational_activation"] == (
        "after_external_S06_publication_conditions"
    )
    assert set(readiness["scope_guard"]["forbidden"]) == {
        "Evidence_Envelope",
        "repository_snapshot_aggregation",
        "history_graph",
        "persistence",
        "retrieval",
        "pattern_or_transfer",
        "RAG",
        "public_APIs",
    }


def _assert_candidate(document: dict[str, Any]) -> None:
    assert set(document) == EXPECTED_TOP_LEVEL
    format_section = cast(dict[str, Any], document["format"])
    phase = cast(dict[str, Any], document["phase_identity"])
    publication = cast(dict[str, Any], document["publication_contract"])
    assert format_section["name"] == EXPECTED_FORMAT
    assert format_section["version"] == EXPECTED_FORMAT_VERSION
    assert format_section["publication_state"] == "sealed_publication_candidate"
    assert format_section["internal"] is True
    assert format_section["public_contract"] is False
    assert phase["phase"] == "S1.P01"
    assert phase["stage"] == "S1"
    assert phase["next_phase"] == "S1.P02"
    assert phase["candidate_state"] == "sealed_publication_candidate"
    assert phase["operational_completion"] == "pending_external_publication_conditions"
    assert phase["synchronized_baseline_sha"] == EXPECTED_BASELINE
    assert phase["synchronized_baseline_tree"] == EXPECTED_BASELINE_TREE
    assert len(phase["external_operational_completion_conditions"]) == 9
    assert publication["operational_completion"] == "external_to_candidate_record"
    assert publication["direct_main_push"] == "forbidden"
    assert publication["required_check"] == "validate"
    assert publication["squash_merge_required"] is True


def _assert_findings_non_generalizations(document: dict[str, Any]) -> None:
    findings = cast(dict[str, Any], document["established_findings"])
    assert findings["count"] == 25
    assert {item["finding_id"] for item in findings["items"]} == EXPECTED_FINDINGS
    assert findings["classification_totals"] == {
        "implementation_behavior": 7,
        "locked_case_calibrated_decision": 9,
        "reviewed_conclusion": 5,
        "verified_repository_fact": 4,
    }
    assert all(item["evidence"] and item["statement"] for item in findings["items"])
    non_generalizations = cast(dict[str, Any], document["non_generalizations"])
    assert non_generalizations["count"] == 26
    assert {
        item["non_generalization_id"] for item in non_generalizations["items"]
    } == EXPECTED_NON_GENERALIZATIONS
    assert non_generalizations["intentional_deferral_is_not_failure"] is True
    assert all(
        item["later_owner"] and item["statement"]
        for item in non_generalizations["items"]
    )


def _assert_document(document: dict[str, Any]) -> None:
    _assert_candidate(document)
    _assert_source_locks(document)
    _assert_ledger(document)
    _assert_inventory(document)
    _assert_effective_contract(document)
    _assert_review_settlement(document)
    _assert_exit_criteria(document)
    _assert_deferred(document)
    _assert_readiness(document)
    _assert_findings_non_generalizations(document)
    correction = cast(dict[str, Any], document["roundtrip_correction_assurance"])
    assert correction["correction_state"] == "corrected_and_regression_locked"
    assert correction["stable_rejection_message"] == STABLE_AMBIGUOUS_MESSAGE
    assert len(correction["facts"]) == 11
    assert all(item["status"] == "verified" for item in correction["facts"])
    tests = cast(dict[str, Any], document["test_assurance"])
    assert tests["baseline"]["full_pytest_count"] == 1037
    assert tests["fresh_s06"]["mutation_case_count"] == 40
    assert tests["fresh_s06"]["test_group_count"] == 15
    assurance = cast(dict[str, Any], document["assurance"])
    assert assurance["unsatisfied_exit_criteria"] == 0
    assert assurance["no_P02_implementation"] is True
    assert assurance["publication_state"] == "sealed_publication_candidate"


def _assert_no_production_reader(paths: list[Path]) -> None:
    forbidden_fragments = (
        "reference_corpus/contracts/identity",
        "s1-p01-phase-closure",
        "closure.json",
        "regression-vectors.json",
    )
    reader_calls = {"open", "read_bytes", "read_text"}
    for path in paths:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                assert not any(
                    fragment in node.value for fragment in forbidden_fragments
                )
            if isinstance(node, ast.Call):
                function = node.func
                if isinstance(function, ast.Name):
                    assert function.id not in reader_calls or not node.args
                elif isinstance(function, ast.Attribute):
                    assert function.attr not in reader_calls or not any(
                        isinstance(argument, ast.Constant)
                        and isinstance(argument.value, str)
                        and any(
                            fragment in argument.value
                            for fragment in forbidden_fragments
                        )
                        for argument in node.args
                    )


def _validate_current_production_inventory(paths: set[str]) -> None:
    assert paths == CURRENT_PRODUCTION_FILES


def _validate_current_evidence_inventory(source: bytes) -> None:
    tree = ast.parse(source)
    export_values: object | None = None
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == "__all__"
            for target in node.targets
        ):
            export_values = ast.literal_eval(node.value)
            break
    assert isinstance(export_values, list)
    raw_exports = cast(list[object], export_values)
    assert all(isinstance(item, str) for item in raw_exports)
    exports = tuple(cast(str, item) for item in raw_exports)
    assert exports == EXPECTED_EVIDENCE_EXPORTS
    assert len(exports) == len(set(exports)) == 23

    top_level_definitions = [
        node.name
        for node in tree.body
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
    ]
    public_definitions = tuple(
        name for name in top_level_definitions if not name.startswith("_")
    )
    assert public_definitions == EXPECTED_EVIDENCE_EXPORTS
    for name in top_level_definitions:
        compact = name.replace("_", "").casefold()
        assert not any(
            fragment in compact
            for fragment in FORBIDDEN_POST_S03_EVIDENCE_SURFACE_FRAGMENTS
        )
        if "acquisitionrun" in compact:
            assert name == "AcquisitionRunId"


def _validate_domain_root_unchanged(source: bytes) -> None:
    tree = ast.parse(source)
    assert not any(isinstance(node, (ast.Import, ast.ImportFrom)) for node in tree.body)
    assert not any(
        isinstance(node, ast.Assign)
        and any(
            isinstance(target, ast.Name) and target.id == "__all__"
            for target in node.targets
        )
        for node in tree.body
    )


def _validate_revision_inventory(source: bytes) -> None:
    tree = ast.parse(source)
    export_values: object | None = None
    public_symbols: set[str] = set()
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == "__all__"
            for target in node.targets
        ):
            export_values = ast.literal_eval(node.value)
        elif isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            if not node.name.startswith("_"):
                public_symbols.add(node.name)
        elif isinstance(node, ast.TypeAlias) and not node.name.id.startswith("_"):
            public_symbols.add(node.name.id)
    assert isinstance(export_values, list)
    raw_exports = cast(list[object], export_values)
    assert all(isinstance(item, str) for item in raw_exports)
    exports = {cast(str, item) for item in raw_exports}
    assert len(raw_exports) == len(exports) == 23
    assert exports == EXPECTED_REVISION_EXPORTS
    assert public_symbols == EXPECTED_REVISION_EXPORTS


def _assert_current_p03_s01_surface() -> None:
    production_files = {
        path.relative_to(REPOSITORY_ROOT).as_posix()
        for path in (REPOSITORY_ROOT / "src").rglob("*.py")
    }
    _validate_current_production_inventory(production_files)
    revision_source = (
        REPOSITORY_ROOT / "src/faultatlas/domain/revision.py"
    ).read_bytes()
    _validate_revision_inventory(revision_source)
    _validate_current_evidence_inventory(
        (REPOSITORY_ROOT / EVIDENCE_MODULE).read_bytes()
    )
    _validate_domain_root_unchanged(
        (REPOSITORY_ROOT / "src/faultatlas/domain/__init__.py").read_bytes()
    )
    forbidden_symbols = {
        "GitCommitRole",
        "GitParentIdentity",
        "GitRepositoryMembership",
        "MutableRefObservation",
        "LineLocator",
        "ByteLocator",
        "HunkLocator",
        "LocatorContractCorpus",
        "LocatorReader",
        "LocatorResolver",
        "EvidenceEnvelope",
    }
    tree = ast.parse(revision_source)
    definitions = {
        node.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
    }
    definitions.update(
        node.name.id for node in ast.walk(tree) if isinstance(node, ast.TypeAlias)
    )
    assert not definitions & forbidden_symbols
    for name in definitions:
        compact_name = name.replace("_", "").lower()
        assert not (
            "locator" in compact_name
            and any(
                forbidden_role in compact_name
                for forbidden_role in ("corpus", "reader", "resolver")
            )
        )
    assert tuple(revision_module.RevisionRoleAssignment.model_fields) == (
        "schema_version",
        "role",
        "revision",
    )
    assert tuple(revision_module.GitCommitParentTopology.model_fields) == (
        "schema_version",
        "commit",
        "ordered_parents",
    )
    assert tuple(revision_module.GitRefObservation.model_fields) == (
        "schema_version",
        "repository_identity",
        "namespace",
        "name",
        "state",
        "authority",
        "observed_at",
        "observed_target",
    )
    assert tuple(revision_module.GitRepositoryPath.model_fields) == ("root",)
    assert tuple(revision_module.RevisionQualifiedPath.model_fields) == (
        "schema_version",
        "repository_identity",
        "revision",
        "path",
    )
    assert tuple(member.value for member in revision_module.TextEncoding) == ("utf-8",)
    assert tuple(member.value for member in revision_module.LineEnding) == (
        "lf",
        "crlf",
    )
    assert tuple(revision_module.OneBasedInclusiveLineSpan.model_fields) == (
        "start_line",
        "end_line",
    )
    assert tuple(revision_module.ZeroBasedHalfOpenByteSpan.model_fields) == (
        "offset",
        "length",
    )
    assert tuple(revision_module.RevisionLineLocator.model_fields) == (
        "schema_version",
        "locator_kind",
        "parent",
        "span",
        "text_encoding",
        "line_ending",
    )
    assert tuple(revision_module.ArtifactByteLocator.model_fields) == (
        "schema_version",
        "locator_kind",
        "parent_artifact_sha256",
        "parent_byte_length",
        "span",
    )
    assert tuple(revision_module.DiffHunkLocator.model_fields) == (
        "schema_version",
        "locator_kind",
        "artifact_bytes",
        "artifact_lines",
        "text_encoding",
        "line_ending",
        "old_file",
        "old_lines",
        "new_file",
        "new_lines",
    )
    intrinsic_forbidden_fields = {
        "authority",
        "name",
        "namespace",
        "observed_at",
        "observed_target",
        "repository",
        "repository_identity",
        "role",
        "ref",
        "state",
        "path",
        "parent",
        "parents",
    }
    for model in (
        revision_module.GitCommitIdentity,
        revision_module.GitTreeIdentity,
        revision_module.GitBlobIdentity,
    ):
        assert not intrinsic_forbidden_fields & set(model.model_fields)
    deferred_fields = {
        "applicability",
        "applicable",
        "column",
        "confidence",
        "coordinate_index_base",
        "events",
        "former_target",
        "history",
        "next_state",
        "observation_time",
        "previous_state",
        "previous_target",
        "prior_state",
        "range",
        "ref",
        "relationship",
        "repository",
        "review",
        "review_state",
        "selected_byte_digest",
        "selected_slice_digest",
        "timestamp",
        "transition",
        "transitions",
    }
    fields = {
        node.target.id
        for node in ast.walk(tree)
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name)
    }
    assert not fields & deferred_fields


def _assert_exact_s06_locator_contract_corpus() -> None:
    contracts_root = REPOSITORY_ROOT / "reference_corpus/contracts"
    assert {path.name for path in contracts_root.iterdir()} == {
        "identity",
        "revision-locator",
    }
    identity_root = contracts_root / "identity"
    assert {path.name for path in identity_root.iterdir()} == {
        "closures",
        "corrections",
        "v1",
    }
    revision_locator_root = contracts_root / "revision-locator"
    assert {path.name for path in revision_locator_root.iterdir()} == {
        "closures",
        "v1",
    }
    assert {path.name for path in REVISION_LOCATOR_ROOT.iterdir()} == (
        EXPECTED_REVISION_LOCATOR_FILES
    )
    for path in REVISION_LOCATOR_ROOT.iterdir():
        assert path.is_file() and not path.is_symlink()
        assert stat.S_IMODE(path.stat().st_mode) == 0o644
    assert not (revision_locator_root / "latest").exists()
    assert not (revision_locator_root / "current").exists()
    closures_root = revision_locator_root / "closures"
    assert closures_root.is_dir() and not closures_root.is_symlink()
    assert {path.name for path in closures_root.iterdir()} == {"s1-p02-phase-closure"}
    phase_closure = closures_root / "s1-p02-phase-closure"
    assert phase_closure.is_dir() and not phase_closure.is_symlink()
    assert {path.name for path in phase_closure.iterdir()} == EXPECTED_CLOSURE_FILES
    for path in phase_closure.iterdir():
        assert path.is_file() and not path.is_symlink()
        assert stat.S_IMODE(path.stat().st_mode) == 0o644


def _provider() -> ProviderKey:
    return ProviderKey.model_validate("github")


def _repository() -> RepositoryIdentity:
    return RepositoryIdentity(
        provider=_provider(),
        provider_repository_id=ProviderRepositoryId.model_validate("37489525"),
    )


def _alias() -> RepositoryAliasObservation:
    provider = _provider()
    return RepositoryAliasObservation(
        repository_identity=_repository(),
        observed_alias="pytest-dev/pytest",
        authority=ProviderAuthority(
            provider=provider,
            role=AuthorityRole.NAVIGATION,
            host="github.com",
        ),
        observed_at=datetime(2026, 7, 24, 11, 3, 15, tzinfo=UTC),
    )


def _legacy() -> SourceLocator:
    return SourceLocator(
        provider="github",
        repository="pytest-dev/pytest",
        object_kind="issue",
        object_id="4412",
    )


def _archive_names_are_safe(names: list[str]) -> None:
    for name in names:
        path = PurePosixPath(name)
        assert not path.is_absolute()
        assert ".." not in path.parts
        assert "\\" not in name
        lowered = {part.casefold() for part in path.parts}
        assert "reference_corpus" not in lowered
        assert "tests" not in lowered


def _packaged_sources(names_and_bytes: list[tuple[str, bytes]]) -> dict[str, bytes]:
    result: dict[str, bytes] = {}
    for name, data in names_and_bytes:
        parts = PurePosixPath(name).parts
        if "faultatlas" not in parts or not name.endswith(".py"):
            continue
        index = parts.index("faultatlas")
        relative = "src/" + "/".join(parts[index:])
        result[relative] = data
    return result


def test_group_a_exact_inventory_permissions_and_safe_paths(tmp_path: Path) -> None:
    assert {path.name for path in CLOSURE_ROOT.iterdir()} == EXPECTED_CLOSURE_FILES
    relative_paths = {
        (CLOSURE_RELATIVE / filename).as_posix() for filename in EXPECTED_CLOSURE_FILES
    }
    for relative in relative_paths:
        _assert_safe_relative(relative)
        _assert_regular_0644(REPOSITORY_ROOT / relative)
    modes = _git_modes(relative_paths)
    untracked = relative_paths - set(modes)
    _assert_git_modes_100644(modes, relative_paths - untracked)
    if untracked:
        _assert_git_modes_100644(_prospective_modes(untracked, tmp_path), untracked)
    assert not (CLOSURE_ROOT.parent / "latest").exists()
    assert not (CLOSURE_ROOT.parent / "current").exists()


def test_group_b_primary_json_is_locked_canonical_and_deterministic() -> None:
    raw = (CLOSURE_ROOT / "closure.json").read_bytes()
    document = _assert_primary_bytes(raw)
    assert _canonical_bytes(document) == raw
    assert _canonical_bytes(json.loads(raw)) == raw


def test_group_c_sidecar_is_exact_and_independently_locked() -> None:
    primary = (CLOSURE_ROOT / "closure.json").read_bytes()
    sidecar = (CLOSURE_ROOT / "closure.sha256").read_bytes()
    _assert_sidecar(sidecar, primary)


def test_group_d_markdown_is_exactly_derived_and_synchronized() -> None:
    raw = (CLOSURE_ROOT / "closure.md").read_bytes()
    assert len(raw) == EXPECTED_MARKDOWN_BYTES
    assert _sha256(raw) == EXPECTED_MARKDOWN_SHA256
    assert b"\r" not in raw
    assert raw.endswith(b"\n") and not raw.endswith(b"\n\n")
    text = raw.decode("utf-8")
    assert text.count(EXPECTED_JSON_SHA256) == 1
    positions = [text.index(heading) for heading in EXPECTED_MARKDOWN_HEADINGS]
    assert positions == sorted(positions)
    document = _load_closure()
    assert f"Exact count: {document['slice_ledger']['count']}." in text
    assert f"Criteria: {document['exit_criteria']['count']};" in text
    assert f"Findings: {document['established_findings']['count']};" in text
    assert f"Deferred items: {document['deferred_register']['count']};" in text
    assert "S1.P02 remains not started." in text
    assert "derived and non-authoritative" in text
    assert "not a universal Phase-closure schema" in text


def test_group_e_source_locks_are_exact_acyclic_and_immutable() -> None:
    _assert_source_locks(_load_closure(), verify_files=True)


def test_group_f_ledger_is_exact_ordered_and_publication_evidenced() -> None:
    document = _load_closure()
    _assert_ledger(document)
    tests = document["test_assurance"]["fresh_s06"]
    assert tests["status"] == "passed_pre_publication_validation"
    assert tests["closure_test_count"] == 64
    assert tests["focused_test_count"] > tests["closure_test_count"]
    assert tests["full_pytest_count"] > tests["focused_test_count"]


def test_group_g_production_inventory_exports_and_legacy_boundary_are_exact() -> None:
    document = _load_closure()
    _assert_inventory(document)
    assert set(identity_module.__all__) == EXPECTED_IDENTITY_EXPORTS
    assert set(compatibility_module.__all__) == EXPECTED_COMPATIBILITY_EXPORTS
    assert faultatlas.__all__ == ["__version__"]
    assert faultatlas.__version__ == "0.1.0"
    for relative, expected in EXPECTED_PRODUCTION.items():
        raw = (REPOSITORY_ROOT / relative).read_bytes()
        assert len(raw) == expected.byte_length
        assert _sha256(raw) == expected.sha256
    current = {
        path.relative_to(REPOSITORY_ROOT).as_posix()
        for path in (REPOSITORY_ROOT / "src").rglob("*.py")
    }
    _validate_current_production_inventory(current)
    assert set(revision_module.__all__) == EXPECTED_REVISION_EXPORTS


def test_group_g_s06_corpus_and_current_p03_s01_surface_are_bounded() -> None:
    paths = [REPOSITORY_ROOT / relative for relative in CURRENT_PRODUCTION_FILES]
    _assert_no_production_reader(paths)
    _assert_current_p03_s01_surface()
    _assert_exact_s06_locator_contract_corpus()


@pytest.mark.parametrize(
    "missing_symbol",
    tuple(
        sorted(
            EXPECTED_S05_REVISION_EXPORTS
            | {"GitRepositoryPath", "RevisionQualifiedPath", "GitRefObservation"}
        )
    ),
)
def test_current_revision_inventory_mutations_are_rejected(
    missing_symbol: str,
) -> None:
    with pytest.raises(AssertionError):
        _validate_current_production_inventory(
            CURRENT_PRODUCTION_FILES - {"src/faultatlas/domain/revision.py"}
        )
    with pytest.raises(AssertionError):
        _validate_current_production_inventory(
            CURRENT_PRODUCTION_FILES | {"src/faultatlas/domain/unexpected.py"}
        )

    source = (REPOSITORY_ROOT / "src/faultatlas/domain/revision.py").read_text(
        encoding="utf-8"
    )
    missing_export = source.replace(f'    "{missing_symbol}",\n', "", 1)
    with pytest.raises(AssertionError):
        _validate_revision_inventory(missing_export.encode())
    unexpected_export = source.replace(
        '    "GitRefObservation",\n',
        '    "GitRefObservation",\n    "UnexpectedRevision",\n',
        1,
    )
    with pytest.raises(AssertionError):
        _validate_revision_inventory(unexpected_export.encode())


def test_current_p03_s01_inventory_and_export_mutations_are_rejected() -> None:
    with pytest.raises(AssertionError):
        _validate_current_production_inventory(
            CURRENT_PRODUCTION_FILES - {EVIDENCE_MODULE}
        )
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
        "LegacyEvidenceAdapter",
        "EvidenceEnvelope",
        "EvidenceContractCorpus",
    ),
)
def test_current_p03_post_s01_surface_is_rejected(early_surface: str) -> None:
    source = (REPOSITORY_ROOT / EVIDENCE_MODULE).read_bytes()
    mutated = source + f"\nclass {early_surface}:\n    pass\n".encode()
    with pytest.raises(AssertionError):
        _validate_current_evidence_inventory(mutated)


def test_group_h_effective_contract_overlay_is_exact() -> None:
    document = _load_closure()
    _assert_effective_contract(document)
    assert {path.name for path in V1_ROOT.iterdir()} == EXPECTED_V1_FILES
    assert {path.name for path in C01_ROOT.iterdir()} == EXPECTED_C01_FILES
    valid = cast(
        dict[str, Any], json.loads((V1_ROOT / "valid-vectors.json").read_bytes())
    )
    invalid = cast(
        dict[str, Any], json.loads((V1_ROOT / "invalid-vectors.json").read_bytes())
    )
    compatibility = cast(
        dict[str, Any],
        json.loads((V1_ROOT / "compatibility-vectors.json").read_bytes()),
    )
    correction = cast(
        dict[str, Any], json.loads((C01_ROOT / "correction.json").read_bytes())
    )
    regressions = cast(
        dict[str, Any],
        json.loads((C01_ROOT / "regression-vectors.json").read_bytes()),
    )
    v1_groups = (
        cast(list[dict[str, Any]], valid["vectors"]),
        cast(list[dict[str, Any]], invalid["vectors"]),
        cast(list[dict[str, Any]], compatibility["vectors"]),
    )
    assert tuple(len(group) for group in v1_groups) == (58, 80, 30)
    historical_ids = [cast(str, item["id"]) for group in v1_groups for item in group]
    assert len(historical_ids) == len(set(historical_ids)) == 168
    assert len(valid["fixtures"]) == 14
    assert len(compatibility["fixtures"]) == 12
    correction_vectors = cast(list[dict[str, Any]], regressions["vectors"])
    assert len(correction_vectors) == 32
    replacement = next(
        item for item in correction_vectors if item["id"] == REPLACEMENT_ID
    )
    assert replacement["supersedes_v1_vector_ids"] == [SUPERSEDED_ID]
    superseded = correction["superseded_contract_vectors"]
    assert superseded["count"] == 1
    assert superseded["items"][0]["original_vector_id"] == SUPERSEDED_ID
    assert superseded["items"][0]["replacement_regression_vector_ids"] == [
        REPLACEMENT_ID
    ]
    assert 168 - superseded["count"] + len(correction_vectors) == 199


@pytest.mark.parametrize("input_mode", ("python", "json"))
def test_group_i_ambiguous_specialization_rejects(input_mode: str) -> None:
    model: type[BaseModel] = IdentityValueState[
        RepositoryScopedNumber | ProviderGlobalId
    ]
    raw: dict[str, Any] = {
        "conflict_candidates": [],
        "schema_version": 1,
        "state": "present",
        "value": "4412",
    }
    with pytest.raises(ValidationError) as caught:
        if input_mode == "json":
            model.model_validate_json(json.dumps(raw))
        else:
            raw["state"] = IdentityFieldState.PRESENT
            raw["value"] = ProviderGlobalId.model_validate("4412")
            model.model_validate(raw)
    errors = caught.value.errors(include_url=False)
    assert len(errors) == 1
    assert errors[0]["loc"] == ()
    assert errors[0]["type"] == "value_error"
    assert STABLE_AMBIGUOUS_MESSAGE in errors[0]["msg"]


@pytest.mark.parametrize("shape", ("monomorphic", "structured"))
def test_group_i_typed_state_roundtrip_is_exact(shape: str) -> None:
    if shape == "monomorphic":
        model: type[BaseModel] = IdentityValueState[ProviderGlobalId]
        original = model.model_validate(
            {
                "state": IdentityFieldState.PRESENT,
                "value": ProviderGlobalId.model_validate("4412"),
                "conflict_candidates": (),
            }
        )
        restored = model.model_validate_json(original.model_dump_json())
        assert restored == original
        assert type(getattr(restored, "value")) is ProviderGlobalId
        return
    model = IdentityValueState[SourceIdentity]
    repository = _repository()
    numbered = NumberedSourceObjectIdentity(
        repository_identity=repository,
        kind=SourceObjectKind.ISSUE,
        repository_scoped_number=RepositoryScopedNumber.model_validate("4412"),
    )
    original = model.model_validate(
        {
            "state": IdentityFieldState.CONFLICT,
            "value": None,
            "conflict_candidates": (repository, numbered),
        }
    )
    restored = model.model_validate_json(original.model_dump_json())
    assert restored == original
    assert tuple(type(item) for item in restored.conflict_candidates) == (
        RepositoryIdentity,
        NumberedSourceObjectIdentity,
    )


@pytest.mark.parametrize(
    "interpretation,expected_types",
    (
        (
            LegacyObjectIdInterpretation.REPOSITORY_SCOPED_NUMBER,
            (RepositoryScopedNumber,),
        ),
        (LegacyObjectIdInterpretation.PROVIDER_GLOBAL_ID, (ProviderGlobalId,)),
        (
            LegacyObjectIdInterpretation.UNRESOLVED,
            (RepositoryScopedNumber, ProviderGlobalId),
        ),
    ),
)
def test_group_i_compatibility_roundtrip_is_exact(
    interpretation: LegacyObjectIdInterpretation,
    expected_types: tuple[type[object], ...],
) -> None:
    original = map_legacy_source_locator(
        _legacy(),
        repository_alias_observation=_alias(),
        object_id_interpretation=interpretation,
    )
    restored = type(original).model_validate_json(original.model_dump_json())
    assert restored == original
    state = restored.object_id_state
    values = (
        cast(tuple[object, ...], state.conflict_candidates)
        if state.state is IdentityFieldState.CONFLICT
        else (state.value,)
    )
    assert tuple(type(item) for item in values) == expected_types
    if interpretation is LegacyObjectIdInterpretation.UNRESOLVED:
        assert state.value is None
        assert len(values) == 2
        assert values[0] != values[1]
        assert getattr(values[0], "root") == getattr(values[1], "root") == "4412"


def test_group_j_historical_review_settlement_is_exact() -> None:
    _assert_review_settlement(_load_closure())


def test_group_k_exit_criteria_are_exact_and_have_zero_unsatisfied() -> None:
    _assert_exit_criteria(_load_closure())


def test_group_l_deferred_register_has_complete_later_ownership() -> None:
    _assert_deferred(_load_closure())


def test_group_m_p02_is_eligible_not_started_and_scope_guarded() -> None:
    _assert_readiness(_load_closure())
    roadmap = " ".join(
        (REPOSITORY_ROOT / "docs/roadmap.md").read_text(encoding="utf-8").split()
    )
    assert "`S1.P01` is complete" in roadmap
    assert "`S1.P02` is complete" in roadmap
    assert "`S1.P02.S01` is complete" in roadmap
    assert "`S1.P02.S02` is complete" in roadmap
    assert "`S1.P02.S03` is complete" in roadmap
    assert "`S1.P02.S04` is complete" in roadmap
    assert "`S1.P02.S05` is complete" in roadmap
    assert "`S1.P02.S06` is complete" in roadmap
    assert "`S1.P02.S07` is complete" in roadmap
    assert "`S1.P03` is active" in roadmap
    assert "`S1.P03.S01` is complete" in roadmap
    assert "`S1.P03.S02` is complete" in roadmap
    assert "`S1.P03.S03` is complete" in roadmap
    assert "`S1.P03.S04` is next and not started" in roadmap


def test_group_n_candidate_publication_semantics_are_exact() -> None:
    document = _load_closure()
    _assert_document(document)
    payload = (CLOSURE_ROOT / "closure.json").read_text(encoding="utf-8")
    assert '"publication_state":"published"' not in payload
    assert '"operational_completion":"complete"' not in payload


def test_group_o_payload_is_private() -> None:
    combined = b"\n".join(
        (CLOSURE_ROOT / filename).read_bytes()
        for filename in sorted(EXPECTED_CLOSURE_FILES)
    )
    lowered = combined.lower()
    for forbidden in (
        b"/home/",
        b"/tmp/",
        b"authorization:",
        b"bearer ",
        b"begin private key",
    ):
        assert forbidden not in lowered
    assert re.search(rb"\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b", combined) is None
    assert (
        re.search(rb"\b(?:gh[opurs]|github_pat)_[A-Za-z0-9_]{8,}\b", combined) is None
    )


def test_group_o_offline_archives_exclude_source_only_material(tmp_path: Path) -> None:
    uv = shutil.which("uv")
    assert uv is not None
    output = tmp_path / "dist"
    cache = tmp_path / "uv-cache"
    output.mkdir()
    cache.mkdir()
    environment = os.environ.copy()
    environment.update(
        {
            "PYTHONDONTWRITEBYTECODE": "1",
            "UV_CACHE_DIR": str(cache),
            "UV_NO_SYNC": "1",
            "UV_OFFLINE": "1",
        }
    )
    status_before = subprocess.run(
        ["git", "status", "--porcelain=v1", "-z", "--untracked-files=all"],
        cwd=REPOSITORY_ROOT,
        check=True,
        capture_output=True,
    ).stdout
    result = subprocess.run(
        [
            uv,
            "build",
            "--offline",
            "--no-create-gitignore",
            "--out-dir",
            str(output),
        ],
        cwd=REPOSITORY_ROOT,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    status_after = subprocess.run(
        ["git", "status", "--porcelain=v1", "-z", "--untracked-files=all"],
        cwd=REPOSITORY_ROOT,
        check=True,
        capture_output=True,
    ).stdout
    assert status_after == status_before
    wheel = tuple(output.glob("*.whl"))
    sdist = tuple(output.glob("*.tar.gz"))
    assert len(wheel) == len(sdist) == 1
    archives: list[list[tuple[str, bytes]]] = []
    with zipfile.ZipFile(wheel[0]) as opened:
        archives.append(
            [
                (info.filename, opened.read(info))
                for info in opened.infolist()
                if not info.is_dir()
            ]
        )
    with tarfile.open(sdist[0], mode="r:gz") as opened:
        files: list[tuple[str, bytes]] = []
        for member in opened.getmembers():
            assert not member.issym() and not member.islnk()
            if not member.isfile():
                continue
            stream = opened.extractfile(member)
            assert stream is not None
            files.append((member.name, stream.read()))
        archives.append(files)
    working = {
        relative: (REPOSITORY_ROOT / relative).read_bytes()
        for relative in CURRENT_PRODUCTION_FILES
    }
    project_license = (REPOSITORY_ROOT / "LICENSE").read_bytes()
    assert _sha256(project_license) == (
        "c71d239df91726fc519c6eb72d318ec65820627232b2f796219e87dcf35d0ab4"
    )
    for members in archives:
        _archive_names_are_safe([name for name, _data in members])
        assert _packaged_sources(members) == working
        licenses = [
            data for name, data in members if PurePosixPath(name).name == "LICENSE"
        ]
        assert licenses == [project_license]
        assert all(
            _sha256(data)
            != "a1ebce15afc7b5cf98c7c6de512d1959d4bf61db8c6bf2f111286d483b40a997"
            for _name, data in members
        )


def test_required_mutation_inventory_is_exact() -> None:
    assert len(REQUIRED_MUTATION_IDS) == 40
    assert len(set(REQUIRED_MUTATION_IDS)) == 40


@pytest.mark.parametrize("mutation_id", REQUIRED_MUTATION_IDS)
def test_required_mutation_is_rejected(mutation_id: str, tmp_path: Path) -> None:
    raw = (CLOSURE_ROOT / "closure.json").read_bytes()
    sidecar = (CLOSURE_ROOT / "closure.sha256").read_bytes()
    document = _load_closure()
    if mutation_id == "changed-json-byte":
        mutated = bytearray(raw)
        mutated[20] = ord("X")
        with pytest.raises(AssertionError):
            _assert_primary_bytes(bytes(mutated))
        return
    if mutation_id == "coordinated-json-sidecar-reseal":
        document["format"]["version"] = "2"
        mutated = _canonical_bytes(document)
        coordinated = f"{_sha256(mutated)}  closure.json\n".encode()
        assert coordinated == f"{_sha256(mutated)}  closure.json\n".encode()
        with pytest.raises(AssertionError):
            _assert_primary_bytes(mutated)
        return
    if mutation_id == "wrong-sidecar-basename":
        with pytest.raises(AssertionError):
            _assert_sidecar(sidecar.replace(b"closure.json", b"other.json"), raw)
        return
    if mutation_id == "missing-terminal-lf":
        with pytest.raises(AssertionError):
            _parse_canonical(raw[:-1])
        return
    if mutation_id == "extra-terminal-lf":
        with pytest.raises(AssertionError):
            _parse_canonical(raw + b"\n")
        return
    if mutation_id == "pretty-json":
        pretty = json.dumps(document, indent=2, sort_keys=True).encode() + b"\n"
        with pytest.raises(AssertionError):
            _parse_canonical(pretty)
        return
    if mutation_id == "broken-p00-lock":
        document["source_locks"]["immutable_inputs"][0]["sha256"] = "0" * 64
        check = _assert_source_locks
    elif mutation_id == "broken-v1-lock":
        document["source_locks"]["immutable_inputs"][3]["sha256"] = "0" * 64
        check = _assert_source_locks
    elif mutation_id == "broken-c01-lock":
        document["source_locks"]["immutable_inputs"][12]["sha256"] = "0" * 64
        check = _assert_source_locks
    elif mutation_id == "removed-ledger-item":
        document["slice_ledger"]["entries"].pop(0)
        check = _assert_ledger
    elif mutation_id == "duplicate-ledger-id":
        document["slice_ledger"]["entries"][1]["slice_id"] = "S1.P01.S01"
        check = _assert_ledger
    elif mutation_id == "reordered-c01-s06":
        document["slice_ledger"]["entries"][-2:] = reversed(
            document["slice_ledger"]["entries"][-2:]
        )
        check = _assert_ledger
    elif mutation_id == "fabricated-s06-pr":
        document["slice_ledger"]["entries"][-1]["pull_request"] = 23
        check = _assert_ledger
    elif mutation_id == "unsatisfied-criterion":
        document["exit_criteria"]["items"][0]["outcome"] = "unsatisfied"
        check = _assert_exit_criteria
    elif mutation_id == "missing-criterion":
        document["exit_criteria"]["items"].pop()
        check = _assert_exit_criteria
    elif mutation_id == "missing-immediate-owner":
        document["deferred_register"]["items"][0]["immediate_next_owner"] = ""
        check = _assert_deferred
    elif mutation_id == "missing-long-term-owner":
        document["deferred_register"]["items"][0]["preserved_long_term_phase_owner"] = (
            ""
        )
        check = _assert_deferred
    elif mutation_id == "ambiguous-union-deferred":
        document["deferred_register"]["corrected_ambiguous_union_is_not_deferred"] = (
            False
        )
        check = _assert_deferred
    elif mutation_id == "p02-started":
        document["entry_readiness"]["implementation"] = "started"
        check = _assert_readiness
    elif mutation_id == "p02-ineligible":
        document["entry_readiness"]["status"] = "ineligible"
        check = _assert_readiness
    elif mutation_id == "candidate-published":
        document["format"]["publication_state"] = "published"
        check = _assert_candidate
    elif mutation_id == "source-self-reference":
        document["source_locks"]["self_reference"] = True
        check = _assert_source_locks
    elif mutation_id == "source-cycle":
        document["source_locks"]["dependency_graph"]["nodes"][0]["predecessors"] = [
            "observation:corrected-production"
        ]
        check = _assert_source_locks
    elif mutation_id == "mutable-latest":
        document["source_locks"]["mutable_pointer"] = True
        check = _assert_source_locks
    elif mutation_id == "unexpected-production-source":
        document["implementation_inventory"]["package_boundary"][
            "production_files"
        ].append("src/faultatlas/domain/unexpected.py")
        check = _assert_inventory
    elif mutation_id == "missing-production-source":
        document["implementation_inventory"]["package_boundary"][
            "production_files"
        ].pop()
        check = _assert_inventory
    elif mutation_id == "missing-identity-export":
        document["implementation_inventory"]["identity_exports"].pop()
        check = _assert_inventory
    elif mutation_id == "missing-compatibility-export":
        document["implementation_inventory"]["compatibility_exports"].pop()
        check = _assert_inventory
    elif mutation_id == "package-root-identity-export":
        document["implementation_inventory"]["package_boundary"][
            "package_root_exports"
        ].append("RepositoryIdentity")
        check = _assert_inventory
    elif mutation_id == "production-corpus-reader":
        synthetic = tmp_path / "reader.py"
        synthetic.write_text(
            "from pathlib import Path\n"
            "def read_contract():\n"
            "    return Path('reference_corpus/contracts/identity/v1/manifest.json').read_text()\n",
            encoding="utf-8",
        )
        with pytest.raises(AssertionError):
            _assert_no_production_reader([synthetic])
        return
    elif mutation_id == "changed-effective-vector-total":
        document["effective_contract_assurance"]["effective_current_vectors"] = 198
        check = _assert_effective_contract
    elif mutation_id == "superseded-without-replacement":
        document["effective_contract_assurance"]["replacement_vector_id"] = ""
        check = _assert_effective_contract
    elif mutation_id == "historical-thread-unresolved":
        document["review_settlement"]["threads"][0]["resolved"] = False
        check = _assert_review_settlement
    elif mutation_id in {"filesystem-mode-0755", "filesystem-mode-0600"}:
        target = tmp_path / "closure.json"
        target.write_bytes(raw)
        target.chmod(0o755 if mutation_id.endswith("0755") else 0o600)
        with pytest.raises(AssertionError):
            _assert_regular_0644(target)
        return
    elif mutation_id == "git-mode-100755":
        with pytest.raises(AssertionError):
            _assert_git_modes_100644({"closure.json": "100755"}, {"closure.json"})
        return
    elif mutation_id == "closure-symlink":
        target = tmp_path / "target"
        target.write_bytes(raw)
        link = tmp_path / "closure.json"
        link.symlink_to(target)
        with pytest.raises(AssertionError):
            _assert_regular_0644(link)
        return
    elif mutation_id == "synthetic-package-closure-member":
        with pytest.raises(AssertionError):
            _archive_names_are_safe(
                [
                    "faultatlas-0.1.0/reference_corpus/contracts/identity/closures/"
                    "s1-p01-phase-closure/closure.json"
                ]
            )
        return
    elif mutation_id == "closure-fifo":
        target = tmp_path / "closure.json"
        os.mkfifo(target)
        with pytest.raises(AssertionError):
            _assert_regular_0644(target)
        return
    else:
        assert mutation_id == "extra-closure-file"
        copied = tmp_path / "closure"
        shutil.copytree(CLOSURE_ROOT, copied)
        (copied / "extra.txt").write_text("unexpected\n", encoding="utf-8")
        with pytest.raises(AssertionError):
            assert {path.name for path in copied.iterdir()} == EXPECTED_CLOSURE_FILES
        return
    with pytest.raises(AssertionError):
        check(document)
