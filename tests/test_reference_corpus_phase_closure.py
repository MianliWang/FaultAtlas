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
from collections.abc import Callable, Iterator
from pathlib import Path, PurePosixPath
from typing import Any, cast

import pytest

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
CLOSURE_DIRECTORY = (
    REPOSITORY_ROOT
    / "reference_corpus"
    / "pytest-4412"
    / "closures"
    / "s1-p00-phase-closure"
)
CLOSURE_JSON = CLOSURE_DIRECTORY / "closure.json"
CLOSURE_SIDECAR = CLOSURE_DIRECTORY / "closure.sha256"
CLOSURE_MARKDOWN = CLOSURE_DIRECTORY / "closure.md"
IDENTITY_V1_DIRECTORY = REPOSITORY_ROOT / "reference_corpus/contracts/identity/v1"
IDENTITY_CORRECTION_DIRECTORY = (
    REPOSITORY_ROOT / "reference_corpus/contracts/identity/corrections/"
    "s05-c01-ambiguous-union-round-trip"
)
IDENTITY_S06_CLOSURE_DIRECTORY = (
    REPOSITORY_ROOT
    / "reference_corpus/contracts/identity/closures/s1-p01-phase-closure"
)
REVISION_LOCATOR_V1_DIRECTORY = (
    REPOSITORY_ROOT / "reference_corpus/contracts/revision-locator/v1"
)
EXPECTED_IDENTITY_V1_FILES = {
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
EXPECTED_IDENTITY_CORRECTION_FILES = {
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
EXPECTED_CLOSURE_SHA256 = (
    "8c02d79c4a5a1d52b9fc2a3718e1b47888da6195588e62ab927388dbe972189e"
)
EXPECTED_SIDECAR_SHA256 = (
    "5b5a189c173c7366d8fe39526d3eda20d6f61cdfd9095e7c22758ec3e710866a"
)
EXPECTED_MARKDOWN_SHA256 = (
    "fdb39ed8a7194f0becb5b4e2536cd883e47e6f291791c26269c45e188e66f2b1"
)
EXPECTED_MARKDOWN_LENGTH = 13707
EXPECTED_FORMAT = "faultatlas-pytest-4412-s1-p00-phase-closure"
EXPECTED_VERSION = "1"
EXPECTED_BASELINE = "090daa2adaa082af97535a5b734823125dbe5c7c"

EXPECTED_TOP_LEVEL = {
    "artifact_chain",
    "assurance",
    "deferred_register",
    "entry_readiness",
    "established_findings",
    "exit_criteria",
    "format",
    "non_generalizations",
    "phase_identity",
    "publication_contract",
    "slice_ledger",
    "source_locks",
    "test_assurance",
}

EXPECTED_LOCKS: dict[str, tuple[str, int, str]] = {
    "reference_corpus/pytest-4412/acquisitions/run-0001-s04-v1-base-4c9cde74-head-690a63b9/acquisition.json": (
        "1c29093bf1537e9b824a18df1848b71a8da014f544bc9f385707eb0e000a1318",
        61283,
        "100644",
    ),
    "reference_corpus/pytest-4412/acquisitions/run-0001-s04-v1-base-4c9cde74-head-690a63b9/acquisition.sha256": (
        "dbb4cf7cb2c0b95377a0a11892b854a46c43dd6c443e7e808e3a57fe31981824",
        83,
        "100644",
    ),
    "reference_corpus/pytest-4412/acquisitions/run-0001-s04-v1-base-4c9cde74-head-690a63b9/artifacts/LICENSE": (
        "a1ebce15afc7b5cf98c7c6de512d1959d4bf61db8c6bf2f111286d483b40a997",
        1096,
        "100644",
    ),
    "reference_corpus/pytest-4412/acquisitions/run-0001-s04-v1-base-4c9cde74-head-690a63b9/artifacts/base-to-head.diff": (
        "dca87a4df1edb2d1acb3fc821724483ee874c2feba6525b2c21e79cb3e8f7312",
        1640,
        "100644",
    ),
    "reference_corpus/pytest-4412/corrections/s04-c01-acquisition-closure/correction.json": (
        "44491ee512d2c2022110b83967fb6fa86d13045bc8404ea490d7a08b7aef24a2",
        60832,
        "100644",
    ),
    "reference_corpus/pytest-4412/corrections/s04-c01-acquisition-closure/correction.sha256": (
        "c585d66ea3d7edf6465ba292c7f08af9a15972ba082f4b0e07a8ffc3f6d61977",
        82,
        "100644",
    ),
    "reference_corpus/pytest-4412/case/case.json": (
        "fc1439a8f9766bdf55b95e9d63f3bf19db44da1724dfb7cd2e889771384b9efa",
        85370,
        "100644",
    ),
    "reference_corpus/pytest-4412/case/case.sha256": (
        "477a4dab64ee7f1353272229bf68c4ac076a4d6b8dbbbbd2fe4fab56c7506dd2",
        76,
        "100644",
    ),
    "reference_corpus/pytest-4412/analysis/s06-current-contract-gap-matrix/gap-matrix.json": (
        "55dacf5193aedc5493ac369dd0e3fb74a0f59f0c1f88bab1b625a2e4f4ff5f13",
        233061,
        "100644",
    ),
    "reference_corpus/pytest-4412/analysis/s06-current-contract-gap-matrix/gap-matrix.md": (
        "6a569af7f9b1c691fc397e356d365664dcc14cbebe6ae589bd4501e23ac1893a",
        8752,
        "100644",
    ),
    "reference_corpus/pytest-4412/analysis/s06-current-contract-gap-matrix/gap-matrix.sha256": (
        "4811ef0c2aaf706361aa79d9300a4343f314ee7437cd6bd28b0f8a49712eff50",
        82,
        "100644",
    ),
    "reference_corpus/pytest-4412/decisions/s07-identity-revision-provenance/decision.json": (
        "60ecb66565525cb21a924508794635072ae50e935d4791d9d91da5b6399ce866",
        85012,
        "100644",
    ),
    "reference_corpus/pytest-4412/decisions/s07-identity-revision-provenance/decision.md": (
        "75c9c84f2069a5782241b9c28cb4e5c39f1368ccdabbc11e4bed9a204869e857",
        9553,
        "100644",
    ),
    "reference_corpus/pytest-4412/decisions/s07-identity-revision-provenance/decision.sha256": (
        "a95d8f29afda95d1361d33a680694eb6618e9c5acaaf52afee5fe6678f34a891",
        80,
        "100644",
    ),
    "reference_corpus/pytest-4412/decisions/s08-snapshot-boundary-compatibility/decision.json": (
        "f788116f3b9ea470c370a56e55eb6f37e05be200f285ac9f2572c641215f5f40",
        46533,
        "100644",
    ),
    "reference_corpus/pytest-4412/decisions/s08-snapshot-boundary-compatibility/decision.md": (
        "6a1a28b7a250f80206da9ff43900a912e3fd201dc7ffa09255660897e193e9e0",
        5679,
        "100644",
    ),
    "reference_corpus/pytest-4412/decisions/s08-snapshot-boundary-compatibility/decision.sha256": (
        "7a87fd638e0ea08dc4e592373c754cdd9c385e54d1197978fcf90eb843057982",
        80,
        "100644",
    ),
}

EXPECTED_UPSTREAM_SIDECARS = {
    "reference_corpus/pytest-4412/acquisitions/run-0001-s04-v1-base-4c9cde74-head-690a63b9/acquisition.sha256": (
        "1c29093bf1537e9b824a18df1848b71a8da014f544bc9f385707eb0e000a1318  acquisition.json\n"
    ),
    "reference_corpus/pytest-4412/corrections/s04-c01-acquisition-closure/correction.sha256": (
        "44491ee512d2c2022110b83967fb6fa86d13045bc8404ea490d7a08b7aef24a2  correction.json\n"
    ),
    "reference_corpus/pytest-4412/case/case.sha256": (
        "fc1439a8f9766bdf55b95e9d63f3bf19db44da1724dfb7cd2e889771384b9efa  case.json\n"
    ),
    "reference_corpus/pytest-4412/analysis/s06-current-contract-gap-matrix/gap-matrix.sha256": (
        "55dacf5193aedc5493ac369dd0e3fb74a0f59f0c1f88bab1b625a2e4f4ff5f13  gap-matrix.json\n"
    ),
    "reference_corpus/pytest-4412/decisions/s07-identity-revision-provenance/decision.sha256": (
        "60ecb66565525cb21a924508794635072ae50e935d4791d9d91da5b6399ce866  decision.json\n"
    ),
    "reference_corpus/pytest-4412/decisions/s08-snapshot-boundary-compatibility/decision.sha256": (
        "f788116f3b9ea470c370a56e55eb6f37e05be200f285ac9f2572c641215f5f40  decision.json\n"
    ),
}

EXPECTED_LEDGER_ORDER = [
    "S1.P00.S01",
    "S1.P00.S02",
    "S1.P00.S03",
    "S1.P00.S04",
    "S1.P00.S04.C01",
    "S1.P00.S05",
    "S1.P00.S06",
    "S1.P00.S07",
    "S1.P00.S08",
    "S1.P00.S09",
    "S1.P00.S10",
]

EXPECTED_CHAIN_ORDER = [
    "layer:acquisition",
    "layer:correction",
    "layer:case",
    "layer:gap-analysis",
    "layer:identity-decision",
    "layer:snapshot-decision",
    "layer:deterministic-tests",
    "layer:phase-closure",
]

EXPECTED_EXIT_OUTCOMES = {
    "canonical-case-selected": "satisfied",
    "capture-policy-published": "satisfied",
    "acquisition-procedure-published": "satisfied",
    "immutable-evidence-acquired": "satisfied",
    "correction-boundary-established": "satisfied",
    "case-manifest-published": "satisfied",
    "relationship-classifications-separated": "satisfied",
    "negative-evidence-ordered": "satisfied",
    "gap-matrix-published": "satisfied",
    "identity-decisions-published": "satisfied",
    "snapshot-decisions-published": "satisfied",
    "deterministic-tests-published": "satisfied",
    "package-exclusion-protected": "satisfied",
    "internal-models-unchanged": "satisfied",
    "no-provider-reacquisition-after-c01": "satisfied",
    "no-p00-blocker": "satisfied",
    "unresolved-semantics-owned": "satisfied_with_explicit_deferral",
    "roadmap-reflects-reality": "satisfied",
    "repository-validation-green": "satisfied",
    "protected-publication-workflow-established": "satisfied",
}

EXPECTED_DEFERRED_IDS = [
    "gap:s05-known:artifact-snapshot-media-and-envelope-gap",
    "gap:s05-known:source-locator-byte-range-ambiguity",
    "gap:s05-known:source-locator-discussion-surface-gap",
    "gap:s05-known:current-visible-provider-surface-only",
    "gap:s05-known:discussion-edit-and-deletion-history-unknown",
    "gap:s05-known:historical-default-branch-unknown",
    "gap:s05-known:original-head-repository-identity-unknown",
    "gap:s05-known:private-and-permission-hidden-records-unknown",
    "gap:s05-known:mutable-alias-and-ref-observations",
    "gap:s05-known:recorded-base-differs-from-merge-first-parent",
    "gap:s05-known:no-universal-private-or-ghe-claims",
    "gap:s05-known:supplemental-observations-postdate-original-s04",
    "gap:s05-known:complete-historical-actor-and-review-state-not-proven",
    "gap:s05-known:issue-timeline-source-index-17-actor-observed-null",
    "gap:s05-known:canonical-urls-not-provider-observed",
    "gap:s05-known:original-s04-actor-reviewer-fields-remain-absent-by-immutability",
    "gap:s05-known:intentionally-omitted-original-field-values-not-replayable",
    "gap:s05-known:stale-cache-causation-unverified",
    "gap:s05-known:case-relationship-vocabulary-provisional",
    "gap:s05-known:current-internal-models-cannot-represent-full-case",
    "gap:s05-known:confidence-model-absent",
    "gap:s05-known:faultatlas-claim-review-state-model-absent",
    "gap:s05-known:production-loader-migration-and-persistence-contract-absent",
    "gap:s05-known:cross-repository-pattern-and-transfer-not-established",
    "gap:s05-known:single-case-insufficient-for-universal-schema-validation",
]

EXPECTED_S07_ALIASES = {
    "register:s07:locator-wire-syntax",
    "register:s07:cross-provider-mapping",
    "register:s07:original-head-repository",
    "register:s07:historical-default-branch",
    "register:s07:complete-discussion-history",
    "register:s07:private-permission-hidden",
    "register:s07:unsupported-private-github",
    "register:s07:unsupported-github-enterprise",
    "register:s07:unsupported-non-git-vcs",
    "register:s07:unsupported-other-issue-providers",
    "register:s07:unsupported-alternate-object-id-systems",
    "register:s07:unsupported-arbitrary-history",
    "register:s07:deferred-p01-provider-representation",
    "register:s07:deferred-p01-legacy-mapping",
    "register:s07:deferred-p01-field-state-carrier",
    "register:s07:deferred-p02-git-wire-syntax",
    "register:s07:deferred-p02-locator-coordinates",
    "register:s07:deferred-p02-ref-role-types",
    "register:s07:deferred-p03-evidence-envelope",
    "register:s07:deferred-p03-transformation-correction",
    "register:s07:deferred-p03-omission-completeness",
}

EXPECTED_S08_REFERENCES = {
    "provisional:s08:outer-contract-name-and-wire-schema",
    "provisional:s08:component-optionality-and-state-carriers",
    "provisional:s08:legacy-adapter-shape",
    "provisional:s08:repository-snapshot-details",
    "provisional:s08:claim-review-confidence-details",
    "provisional:s08:version-wire-syntax",
    "provisional:s08:reader-writer-APIs",
    "provisional:s08:migration-corpus-and-procedure",
    "unknown:s08:universal-provider-transfer",
    "unknown:s08:arbitrary-history-completeness",
    "unknown:s08:future-evidence-field-set",
    "unknown:s08:legacy-removal-timeline",
    "unsupported:s08:0",
    "unsupported:s08:1",
    "unsupported:s08:2",
    "unsupported:s08:3",
}

EXPECTED_OWNER_DECISIONS = {
    "decision:s07:canonical-identity-tuple",
    "decision:s07:actor-reviewer-missing-states",
    "decision:s07:revision-identity",
    "decision:s07:topology-ref-and-locator",
    "decision:s07:provenance-authority-chain",
    "decision:s08:artifact-snapshot-boundary",
    "decision:s08:representation-media-and-digest",
    "decision:s08:completeness-and-omission-carrier",
    "decision:s08:reader-writer-migration-compatibility",
    "decision:s09:test-verifier-scope",
    "decision:s10:p00-closure-criteria",
}

EXPECTED_PREREQUISITES = {
    "s07-layer-valid",
    "s08-boundary-valid",
    "s09-tests-green",
    "s04-s08-chain-valid",
    "source-locator-internal-unchanged",
    "no-public-identity-api",
    "no-production-schema-migration",
    "clean-synchronized-main",
    "protected-pr-workflow-available",
    "no-p00-blocker",
}

EXPECTED_FINDING_IDS = {
    "finding:stable-repository-identity-not-mutable-alias",
    "finding:repository-scoped-number-not-global-id",
    "finding:git-object-identity-not-revision-role",
    "finding:mutable-ref-not-immutable-revision",
    "finding:source-identity-not-provenance",
    "finding:exact-bytes-not-normalized-representation",
    "finding:correction-is-append-only",
    "finding:evidence-and-interpretation-states-distinct",
    "finding:negative-evidence-first-class",
    "finding:legacy-seeds-narrow-internal",
    "finding:future-outer-evidence-boundary-required",
    "finding:offline-deterministic-replay-feasible",
}

EXPECTED_NON_GENERALIZATION_IDS = {
    "non-generalization:universal-multi-provider-identity",
    "non-generalization:private-github-or-enterprise",
    "non-generalization:non-git-vcs-identity",
    "non-generalization:production-evidence-envelope-schema",
    "non-generalization:production-reader-writer-migration",
    "non-generalization:persistence-technology",
    "non-generalization:ingestion",
    "non-generalization:retrieval",
    "non-generalization:graph-storage",
    "non-generalization:cross-repository-generality",
    "non-generalization:transfer-scoring",
    "non-generalization:model-provider",
    "non-generalization:advanced-rag",
}

EXPECTED_S09 = {
    "canonical_JSON_count": 6,
    "focused_pytest_count": 115,
    "full_pytest_count": 181,
    "independent_probe_result": "6_of_6_passed",
    "lock_count": 17,
    "main_CI_result": "success",
    "mutation_and_sensitivity_count": 72,
    "package_build_result": "passed_offline_wheel_and_sdist_exclusion",
    "pointer_count": 696,
    "pr_CI_result": "success",
    "sidecar_count": 6,
    "S09_specific_added_test_count": 113,
}

EXPECTED_PRODUCTION_FILES = {
    "src/faultatlas/__init__.py",
    "src/faultatlas/__main__.py",
    "src/faultatlas/cli.py",
    "src/faultatlas/domain/__init__.py",
    "src/faultatlas/domain/compatibility.py",
    "src/faultatlas/domain/identity.py",
    "src/faultatlas/domain/revision.py",
    "src/faultatlas/domain/source.py",
}
EVIDENCE_MODULE = "src/faultatlas/domain/evidence.py"
CURRENT_PRODUCTION_FILES = {*EXPECTED_PRODUCTION_FILES, EVIDENCE_MODULE}
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
EXPECTED_P03_SLICE_SEQUENCE = (
    (
        "S1.P03.S01",
        "Retrieval Request Identity and Authority Foundation",
        "complete",
    ),
    (
        "S1.P03.S02",
        "Request Controls and Response Representation Observations",
        "complete",
    ),
    (
        "S1.P03.S03",
        "Exact Retained Artifacts and Digest Scope",
        "complete",
    ),
    (
        "S1.P03.S04",
        "Acquisition Runs and Evidence Membership",
        "complete",
    ),
    (
        "S1.P03.S05",
        "Transformations, Corrections, and Supersession",
        "complete",
    ),
    (
        "S1.P03.S06",
        "Completeness, Omissions, and Publication Provenance",
        "complete",
    ),
    (
        "S1.P03.S07",
        "Evidence Envelope Composition and Legacy Adapter",
        "complete",
    ),
    ("S1.P03.S08", "Evidence Contract Corpus", "complete"),
    ("S1.P03.S09", "Integration and Phase Closure", "next; not started"),
)

EXPECTED_REVISION_SYMBOLS = {
    "ArtifactByteLocator",
    "BoundedLocator",
    "DiffHunkLocator",
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
    "LineEnding",
    "OneBasedInclusiveLineSpan",
    "RevisionQualifiedPath",
    "RevisionLineLocator",
    "RevisionRole",
    "RevisionRoleAssignment",
    "TextEncoding",
    "ZeroBasedHalfOpenByteSpan",
}

EXPECTED_REVISION_CLASSES = {
    "ArtifactByteLocator",
    "DiffHunkLocator",
    "GitBlobIdentity",
    "GitCommitIdentity",
    "GitCommitParentTopology",
    "GitHashAlgorithm",
    "GitObjectKind",
    "GitRefName",
    "GitRefNamespace",
    "GitRefObservation",
    "GitRepositoryPath",
    "GitTreeIdentity",
    "LineEnding",
    "OneBasedInclusiveLineSpan",
    "RevisionQualifiedPath",
    "RevisionLineLocator",
    "RevisionRole",
    "RevisionRoleAssignment",
    "TextEncoding",
    "ZeroBasedHalfOpenByteSpan",
}

EXPECTED_S05_REVISION_SYMBOLS = {
    "ArtifactByteLocator",
    "BoundedLocator",
    "DiffHunkLocator",
    "LineEnding",
    "OneBasedInclusiveLineSpan",
    "RevisionLineLocator",
    "TextEncoding",
    "ZeroBasedHalfOpenByteSpan",
}

EXPECTED_COMPATIBILITY_SYMBOLS = {
    "CompatibilityStatus",
    "LegacyCompatibilityReason",
    "LegacyObjectIdInterpretation",
    "LegacySourceLocatorMappingResult",
    "LegacySourceLocatorProjectionResult",
    "map_legacy_source_locator",
    "project_source_identity_to_legacy",
}

EXPECTED_COMPATIBILITY_ENUMS = {
    "CompatibilityStatus",
    "LegacyCompatibilityReason",
    "LegacyObjectIdInterpretation",
}

EXPECTED_COMPATIBILITY_MODELS = {
    "LegacySourceLocatorMappingResult",
    "LegacySourceLocatorProjectionResult",
}

EXPECTED_COMPATIBILITY_FUNCTIONS = {
    "map_legacy_source_locator",
    "project_source_identity_to_legacy",
}

EXPECTED_IDENTITY_SYMBOLS = {
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

EXPECTED_IDENTITY_CLASSES = {
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
    "SourceIdentityLifecycleObservation",
    "SourceIdentityLifecycleState",
    "SourceObjectKind",
}

EXPECTED_S02_IDENTITY_SYMBOLS = {
    "NumberedSourceObjectIdentity",
    "ProviderGlobalId",
    "ProviderNodeId",
    "ProviderScopedSourceObjectIdentity",
    "RepositoryScopedNumber",
    "SourceObjectKind",
}

EXPECTED_S03_IDENTITY_SYMBOLS = {
    "IdentityFieldState",
    "IdentityValueState",
    "SourceIdentity",
    "SourceIdentityLifecycleObservation",
    "SourceIdentityLifecycleState",
}

EXPECTED_S10_CHANGED_PATHS = {
    "reference_corpus/pytest-4412/closures/s1-p00-phase-closure/closure.json",
    "reference_corpus/pytest-4412/closures/s1-p00-phase-closure/closure.sha256",
    "reference_corpus/pytest-4412/closures/s1-p00-phase-closure/closure.md",
    "tests/test_reference_corpus_phase_closure.py",
    "docs/reference_cases/pytest-4412.md",
    "docs/roadmap.md",
}


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _validate_production_file_inventory(production_files: set[str]) -> None:
    assert production_files == EXPECTED_PRODUCTION_FILES


def _validate_current_production_file_inventory(production_files: set[str]) -> None:
    assert production_files == CURRENT_PRODUCTION_FILES


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
    assert len(exports) == len(set(exports)) == 58

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


def _identity_symbol_inventory(
    source: bytes,
) -> tuple[set[str], set[str], set[str]]:
    tree = ast.parse(source)
    export_values: object | None = None
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        if any(
            isinstance(target, ast.Name) and target.id == "__all__"
            for target in node.targets
        ):
            export_values = ast.literal_eval(node.value)
            break
    assert isinstance(export_values, list)
    exports: set[str] = set()
    raw_exports = cast(list[object], export_values)
    for export_value in raw_exports:
        assert isinstance(export_value, str)
        exports.add(export_value)
    assert len(exports) == len(raw_exports)
    public_symbols: set[str] = set()
    public_classes: set[str] = set()
    public_symbol_count = 0
    public_class_count = 0
    for node in tree.body:
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            if not node.name.startswith("_"):
                public_symbols.add(node.name)
                public_symbol_count += 1
            if isinstance(node, ast.ClassDef) and not node.name.startswith("_"):
                public_classes.add(node.name)
                public_class_count += 1
        elif isinstance(node, ast.Assign):
            assigned_names = {
                target.id
                for target in node.targets
                if isinstance(target, ast.Name) and not target.id.startswith("_")
            }
            public_symbols.update(assigned_names)
            public_symbol_count += len(assigned_names)
        elif isinstance(node, ast.AnnAssign):
            if isinstance(node.target, ast.Name) and not node.target.id.startswith("_"):
                public_symbols.add(node.target.id)
                public_symbol_count += 1
        elif isinstance(node, ast.TypeAlias):
            if not node.name.id.startswith("_"):
                public_symbols.add(node.name.id)
                public_symbol_count += 1
    assert len(public_symbols) == public_symbol_count
    assert len(public_classes) == public_class_count
    return exports, public_symbols, public_classes


def _validate_identity_symbol_inventory(source: bytes) -> None:
    exports, public_symbols, public_classes = _identity_symbol_inventory(source)
    assert len(exports) == len(EXPECTED_IDENTITY_SYMBOLS) == 17
    assert exports == EXPECTED_IDENTITY_SYMBOLS
    assert len(public_symbols) == 17
    assert public_symbols == EXPECTED_IDENTITY_SYMBOLS
    assert len(public_classes) == len(EXPECTED_IDENTITY_CLASSES) == 16
    assert public_classes == EXPECTED_IDENTITY_CLASSES


def _validate_revision_symbol_inventory(source: bytes) -> None:
    exports, public_symbols, public_classes = _identity_symbol_inventory(source)
    assert len(exports) == len(EXPECTED_REVISION_SYMBOLS) == 23
    assert exports == EXPECTED_REVISION_SYMBOLS
    assert len(public_symbols) == 23
    assert public_symbols == EXPECTED_REVISION_SYMBOLS
    assert len(public_classes) == len(EXPECTED_REVISION_CLASSES) == 20
    assert public_classes == EXPECTED_REVISION_CLASSES


def _compatibility_symbol_inventory(
    source: bytes,
) -> tuple[set[str], set[str], set[str], set[str], set[str]]:
    tree = ast.parse(source)
    export_values: object | None = None
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        if any(
            isinstance(target, ast.Name) and target.id == "__all__"
            for target in node.targets
        ):
            export_values = ast.literal_eval(node.value)
            break
    assert isinstance(export_values, list)
    raw_exports = cast(list[object], export_values)
    assert all(isinstance(item, str) for item in raw_exports)
    exports = {cast(str, item) for item in raw_exports}
    assert len(exports) == len(raw_exports)

    public_symbols: set[str] = set()
    enums: set[str] = set()
    models: set[str] = set()
    functions: set[str] = set()
    public_symbol_count = 0
    enum_count = 0
    model_count = 0
    function_count = 0
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and not node.name.startswith("_"):
            public_symbols.add(node.name)
            public_symbol_count += 1
            base_names = {base.id for base in node.bases if isinstance(base, ast.Name)}
            if "StrEnum" in base_names:
                enums.add(node.name)
                enum_count += 1
            if "BaseModel" in base_names:
                models.add(node.name)
                model_count += 1
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and not (
            node.name.startswith("_")
        ):
            public_symbols.add(node.name)
            functions.add(node.name)
            public_symbol_count += 1
            function_count += 1
        elif isinstance(node, ast.Assign):
            assigned_names = {
                target.id
                for target in node.targets
                if isinstance(target, ast.Name) and not target.id.startswith("_")
            }
            public_symbols.update(assigned_names)
            public_symbol_count += len(assigned_names)
        elif isinstance(node, ast.AnnAssign):
            if isinstance(node.target, ast.Name) and not node.target.id.startswith("_"):
                public_symbols.add(node.target.id)
                public_symbol_count += 1
        elif isinstance(node, ast.TypeAlias) and not node.name.id.startswith("_"):
            public_symbols.add(node.name.id)
            public_symbol_count += 1
    assert len(public_symbols) == public_symbol_count
    assert len(enums) == enum_count
    assert len(models) == model_count
    assert len(functions) == function_count
    return exports, public_symbols, enums, models, functions


def _validate_compatibility_symbol_inventory(source: bytes) -> None:
    exports, public_symbols, enums, models, functions = _compatibility_symbol_inventory(
        source
    )
    assert len(exports) == len(EXPECTED_COMPATIBILITY_SYMBOLS) == 7
    assert exports == EXPECTED_COMPATIBILITY_SYMBOLS
    assert len(public_symbols) == 7
    assert public_symbols == EXPECTED_COMPATIBILITY_SYMBOLS
    assert len(enums) == 3
    assert enums == EXPECTED_COMPATIBILITY_ENUMS
    assert len(models) == 2
    assert models == EXPECTED_COMPATIBILITY_MODELS
    assert len(functions) == 2
    assert functions == EXPECTED_COMPATIBILITY_FUNCTIONS


def _validate_source_locator_method_inventory(source: bytes) -> None:
    tree = ast.parse(source)
    source_locator = next(
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == "SourceLocator"
    )
    methods = [
        node.name
        for node in source_locator.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    ]
    assert methods == ["_normalize_repository"]


def _validate_package_root_exports(source: bytes) -> None:
    tree = ast.parse(source)
    imports = [
        (node.module, tuple(alias.name for alias in node.names))
        for node in tree.body
        if isinstance(node, ast.ImportFrom)
    ]
    assert imports == [("importlib.metadata", ("version",))]
    export_values: object | None = None
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        if any(
            isinstance(target, ast.Name) and target.id == "__all__"
            for target in node.targets
        ):
            export_values = ast.literal_eval(node.value)
            break
    assert export_values == ["__version__"]


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


def _assert_no_float(value: Any) -> None:
    if isinstance(value, float):
        raise AssertionError("floats are forbidden in closure JSON")
    if isinstance(value, dict):
        for child in cast(dict[str, Any], value).values():
            _assert_no_float(child)
    elif isinstance(value, list):
        for child in cast(list[Any], value):
            _assert_no_float(child)


def _load_closure() -> tuple[bytes, dict[str, Any]]:
    raw = CLOSURE_JSON.read_bytes()
    parsed: Any = json.loads(raw)
    assert isinstance(parsed, dict)
    return raw, cast(dict[str, Any], parsed)


def _validate_primary_lock(raw: bytes, sidecar: bytes | None = None) -> None:
    assert _sha256(raw) == EXPECTED_CLOSURE_SHA256
    if sidecar is not None:
        assert _sha256(sidecar) == EXPECTED_SIDECAR_SHA256
        assert sidecar == f"{EXPECTED_CLOSURE_SHA256}  closure.json\n".encode()


def _validate_format_and_candidate_state(closure: dict[str, Any]) -> None:
    assert set(closure) == EXPECTED_TOP_LEVEL
    format_record = closure["format"]
    assert format_record["name"] == EXPECTED_FORMAT
    assert format_record["version"] == EXPECTED_VERSION
    assert format_record["classification"] == "phase_closure"
    assert format_record["publication_state"] == "sealed_publication_candidate"
    assert (
        "not_a_universal_phase_closure_schema" in format_record["non_universal_warning"]
    )
    assert format_record["created_at"].endswith("Z")
    assert format_record["created_at"] <= format_record["sealed_at"]
    canonical = format_record["canonicalization"]
    assert canonical["name"] == "json-sort-keys-compact-utf8-lf-v1"
    assert canonical["floats_and_NaN_permitted"] is False
    assert canonical["exactly_one_trailing_lf"] is True

    phase = closure["phase_identity"]
    assert phase["stage"] == "S1"
    assert phase["phase"] == "S1.P00"
    assert phase["phase_title"] == "Reference-Case Calibration & Stage 1 Entry"
    assert phase["canonical_case"] == "pytest-4412"
    assert phase["synchronized_baseline_sha"] == EXPECTED_BASELINE
    assert phase["closure_candidate_state"] == "sealed_publication_candidate"
    assert phase["operational_completion"] == "pending_external_publication_conditions"
    assert phase["external_publication_completion_conditions"] == [
        "exact_reviewed_candidate_merged_through_protected_PR",
        "merged_tree_contains_reviewed_closure_bytes",
        "required_PR_check_validate_passes",
        "natural_main_CI_passes_for_exact_squash_SHA",
        "local_main_is_clean_and_synchronized",
    ]


def _validate_source_lock_table(closure: dict[str, Any]) -> None:
    locks = closure["source_locks"]
    assert locks["immutable_input_count"] == 17
    actual = {
        item["path"]: (item["sha256"], item["byte_length"], item["git_mode"])
        for item in locks["immutable_inputs"]
    }
    assert actual == EXPECTED_LOCKS
    closure_prefix = "reference_corpus/pytest-4412/closures/"
    assert all(not path.startswith(closure_prefix) for path in actual)


def _validate_slice_ledger(closure: dict[str, Any]) -> None:
    ledger = closure["slice_ledger"]
    items = ledger["items"]
    ids = [item["slice_id"] for item in items]
    assert ledger["count"] == 11
    assert ledger["order"] == EXPECTED_LEDGER_ORDER
    assert ids == EXPECTED_LEDGER_ORDER
    assert len(ids) == len(set(ids))
    assert ledger["unique"] is True
    for item in items[:-1]:
        assert item["completion_state"] == "published_complete"
        assert item["reviewed_head_tree_equals_merge_tree"] is True
        assert item["required_pr_check"]["conclusion"] == "success"
        assert item["required_pr_check"]["event"] == "pull_request"
        assert item["required_pr_check"]["head_sha"] == item["reviewed_commit"]
        assert item["natural_main_ci"]["conclusion"] == "success"
        assert item["natural_main_ci"]["event"] == "push"
        assert item["natural_main_ci"]["head_sha"] == item["squash_merge_commit"]
        assert item["reviewed_head_tree"] == item["merge_tree"]
    candidate = items[-1]
    assert candidate["completion_state"] == "sealed_publication_candidate"
    assert set(candidate["authoritative_changed_paths"]) == EXPECTED_S10_CHANGED_PATHS
    for field in (
        "primary_commit",
        "pr",
        "required_pr_check",
        "reviewed_commit",
        "reviewed_head_tree",
        "squash_merge_commit",
        "merge_tree",
        "natural_main_ci",
    ):
        assert candidate[field]["state"] == "unavailable_until_protected_publication"


def _validate_artifact_chain(closure: dict[str, Any]) -> None:
    chain = closure["artifact_chain"]
    layers = chain["layers"]
    ids = [layer["layer_id"] for layer in layers]
    assert chain["count"] == 8
    assert ids == EXPECTED_CHAIN_ORDER
    assert len(ids) == len(set(ids))
    known = set(ids)
    graph: dict[str, list[str]] = {}
    for layer in layers:
        predecessors = layer["predecessor_ids"]
        assert layer["layer_id"] not in predecessors
        assert set(predecessors) <= known
        assert "replace" not in layer["relationship"]
        graph[layer["layer_id"]] = predecessors

    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node: str) -> None:
        assert node not in visiting, "artifact chain contains a cycle"
        if node in visited:
            return
        visiting.add(node)
        for predecessor in graph[node]:
            visit(predecessor)
        visiting.remove(node)
        visited.add(node)

    for node in graph:
        visit(node)
    assert visited == known
    assert chain["acyclic"] is True
    assert chain["append_only"] is True
    assert chain["no_layer_replaces_an_earlier_layer"] is True
    closure_layer = layers[-1]
    assert closure_layer["digest"]["algorithm"] == (
        "unavailable_inside_self_contained_candidate"
    )


def _validate_s09_assurance(closure: dict[str, Any]) -> None:
    assert closure["test_assurance"]["historical_S09_publication"] == EXPECTED_S09
    evidence = closure["source_locks"]["S09_publication_evidence"]
    assert evidence["reviewed_commit"] == ("8f393ac914cdf447687a0fdefef9c66e58a5f0dc")
    assert evidence["merge_commit"] == EXPECTED_BASELINE
    assert evidence["merge_tree"] == "78840b84c79c47781cfc44892a712099a08cf915"
    assert evidence["reviewed_head_tree"] == evidence["merge_tree"]
    assert evidence["pr"]["number"] == 15
    assert (evidence["pr_CI"]["run_id"], evidence["pr_CI"]["job_id"]) == (
        30603264480,
        91070231946,
    )
    assert (evidence["main_CI"]["run_id"], evidence["main_CI"]["job_id"]) == (
        30603392945,
        91070626145,
    )
    observations = closure["source_locks"]["S09_test_source_observations"]
    assert observations == [
        {
            "byte_length": 70329,
            "line_count": 1882,
            "observation_semantics": (
                "closure_time_observation_not_an_immutable_future_input"
            ),
            "path": "tests/test_reference_corpus_pytest_4412.py",
            "sha256": (
                "72324d8d8cfd31e3352464c66641b4b48ff0a71d6add242eba37a0cd0cf271a7"
            ),
        },
        {
            "byte_length": 12550,
            "line_count": 395,
            "observation_semantics": (
                "closure_time_observation_not_an_immutable_future_input"
            ),
            "path": "tests/test_package.py",
            "sha256": (
                "ee24408121a948bbc46609cdd37edeffd05028f719885340c087e8651c1ba5c5"
            ),
        },
    ]


def _validate_exit_criteria(closure: dict[str, Any]) -> None:
    record = closure["exit_criteria"]
    items = record["items"]
    actual = {item["criterion_id"]: item["outcome"] for item in items}
    assert record["count"] == 20
    assert actual == EXPECTED_EXIT_OUTCOMES
    assert len(items) == len(actual)
    assert record["unsatisfied_count"] == 0
    assert "unsatisfied" not in actual.values()
    allowed = {
        "satisfied",
        "satisfied_with_explicit_deferral",
        "not_applicable",
        "unsatisfied",
    }
    for item in items:
        assert item["outcome"] in allowed
        assert item["statement"]
        assert item["evidence"]
    deferral = next(
        item["deferral"]
        for item in items
        if item["criterion_id"] == "unresolved-semantics-owned"
    )
    assert deferral["deferred_item_ids"] == EXPECTED_DEFERRED_IDS
    assert all(
        re.fullmatch(r"S1\.P(?:0[1-9]|10)", owner) for owner in deferral["owners"]
    )


def _validate_findings(closure: dict[str, Any]) -> None:
    findings = closure["established_findings"]
    assert len(findings) == 12
    assert {item["finding_id"] for item in findings} == EXPECTED_FINDING_IDS
    allowed = {
        "verified_repository_fact",
        "locked_case_calibrated_decision",
        "reviewed_interpretation",
    }
    assert {item["classification"] for item in findings} <= allowed
    assert all(item["evidence"] for item in findings)
    non_generalizations = closure["non_generalizations"]
    assert non_generalizations["count"] == 13
    assert {
        item["non_generalization_id"] for item in non_generalizations["items"]
    } == EXPECTED_NON_GENERALIZATION_IDS
    assert all(
        item["disposition"]
        == "intentionally_out_of_P00_scope_or_explicitly_deferred_not_an_evidence_failure"
        for item in non_generalizations["items"]
    )


def _valid_owner(value: str) -> bool:
    return bool(
        re.fullmatch(
            r"S1\.P(?:00\.S(?:0[1-9]|10)|(?:0[1-9]|10)(?:\.S(?:0[1-9]|10))?)",
            value,
        )
    )


def _validate_deferred_register(closure: dict[str, Any]) -> None:
    record = closure["deferred_register"]
    items = record["items"]
    ids = [item["deferred_item_id"] for item in items]
    assert record["count"] == 25
    assert ids == EXPECTED_DEFERRED_IDS
    assert len(ids) == len(set(ids))
    assert record["state_totals"] == {
        "decision_resolved_implementation_deferred": 12,
        "provisional_pending_later_phase_design": 4,
        "unknown_pending_additional_evidence": 9,
    }
    assert record["owner_totals"]["immediate_next_owner"] == {
        "S1.P01": 6,
        "S1.P02": 2,
        "S1.P03": 7,
        "S1.P04": 1,
        "S1.P05": 2,
        "S1.P07": 1,
        "S1.P09": 4,
        "S1.P10": 2,
    }
    assert record["owner_totals"]["preserved_long_term_phase_owner"] == {
        "S1.P01": 3,
        "S1.P02": 3,
        "S1.P03": 6,
        "S1.P04": 1,
        "S1.P05": 2,
        "S1.P08": 2,
        "S1.P09": 6,
        "S1.P10": 2,
    }
    s07_refs: list[str] = []
    s08_refs: list[str] = []
    for item in items:
        assert item["reason_for_deferral"]
        assert item["latest_decision_point"]
        assert item["consequence_if_unresolved"]
        assert item["evidence_reference"]
        assert _valid_owner(item["immediate_next_owner"])
        assert _valid_owner(item["preserved_long_term_phase_owner"])
        for reference in item["source_references"]:
            source_id = reference["source_id"]
            if source_id.startswith("register:s07:"):
                s07_refs.append(source_id)
            elif reference["layer_id"] == "s08-snapshot-decision":
                s08_refs.append(source_id)
    assert set(s07_refs) == EXPECTED_S07_ALIASES
    assert len(s07_refs) == len(EXPECTED_S07_ALIASES)
    assert set(s08_refs) == EXPECTED_S08_REFERENCES
    assert len(s08_refs) == len(EXPECTED_S08_REFERENCES)


def _validate_s06_reconciliation(closure: dict[str, Any]) -> None:
    record = closure["deferred_register"]["s06_reconciliation"]
    decisions = record["owner_decisions"]
    assert record["owner_decision_count"] == 11
    assert {item["decision_id"] for item in decisions} == EXPECTED_OWNER_DECISIONS
    assert record["route_totals"] == {
        "S1.P00.S07": 5,
        "S1.P00.S08": 4,
        "S1.P00.S09": 1,
        "S1.P00.S10": 1,
    }
    assert record["direct_S10_owner_decision_count"] == 1
    assert record["all_11_owner_decisions_accounted_for"] is True
    assert record["no_owner_decision_disappeared"] is True
    assert record["gap_count"] == 31
    assert record["all_31_gaps_accounted_for"] is True
    accounted = record["carried_forward_gap_ids"] + [
        item["gap_id"] for item in record["dispositioned_gaps"]
    ]
    assert len(accounted) == 31
    assert len(accounted) == len(set(accounted))
    s10 = record["S10_decision_refinement"]
    assert s10["decision_id"] == "decision:s10:p00-closure-criteria"
    assert s10["disposition"] == "accepted_with_refinement"


def _resolve_pointer(document: Any, pointer: str) -> Any:
    assert pointer.startswith("/")
    current = document
    for raw_part in pointer[1:].split("/"):
        part = raw_part.replace("~1", "/").replace("~0", "~")
        if isinstance(current, list):
            current = cast(list[Any], current)[int(part)]
        else:
            current = cast(dict[str, Any], current)[part]
    return current


def _validate_deferred_source_pointers(closure: dict[str, Any]) -> None:
    cache: dict[str, Any] = {}
    for item in closure["deferred_register"]["items"]:
        for reference in item["source_references"]:
            path = reference["path"]
            document = cache.setdefault(
                path,
                json.loads((REPOSITORY_ROOT / path).read_bytes()),
            )
            target = _resolve_pointer(document, reference["json_pointer"])
            source_id = reference["source_id"]
            if reference["layer_id"] == "s06-gap-matrix":
                assert target["gap_id"] == source_id
            elif reference["layer_id"] == "s05-case":
                assert target["id"] == source_id
            elif reference["layer_id"] == "s07-identity-decision":
                assert target["register_id"] == source_id
            elif source_id.startswith("unsupported:s08:"):
                assert target == reference["source_value"]
            else:
                assert target["register_id"] == source_id


def _validate_entry_readiness(closure: dict[str, Any]) -> None:
    readiness = closure["entry_readiness"]
    assert readiness["next_phase"] == "S1.P01"
    assert readiness["status"] == "eligible_to_begin"
    assert readiness["implementation"] == "not_started"
    prerequisites = readiness["prerequisites"]
    assert len(prerequisites) == 10
    assert {item["prerequisite_id"] for item in prerequisites} == (
        EXPECTED_PREREQUISITES
    )
    assert all(item["outcome"] == "satisfied" for item in prerequisites)
    assert readiness["scope_guard"]["allowed_initial_scope"] == ["identity_primitives"]
    assert readiness["scope_guard"]["forbidden_surfaces"] == [
        "revision_qualified_locator_implementation",
        "Evidence_Envelope_implementation",
        "repository_snapshot_aggregation",
        "history_graph",
        "fault_model",
        "pattern_model",
        "transfer",
        "persistence_vendor_selection",
        "retrieval",
        "RAG",
    ]


def _validate_publication_contract(closure: dict[str, Any]) -> None:
    contract = closure["publication_contract"]
    assert contract == {
        "bypass_permitted": False,
        "direct_main_push_permitted": False,
        "final_local_synchronization": (
            "required_clean_HEAD_equals_origin_main_divergence_0_0"
        ),
        "final_operational_completion": ("external_to_self_contained_candidate_record"),
        "merge_method": "squash",
        "natural_main_CI": "required_for_exact_squash_SHA",
        "protected_topic_branch_PR": "required",
        "required_check_context": "validate",
        "required_workflow": "CI",
        "reviewed_head_merge_tree_equality": "required",
        "topic_branch": "feat/s1-p00-s10-phase-closure",
    }


def _reference_strings(value: Any, key: str = "") -> Iterator[str]:
    if isinstance(value, dict):
        for child_key, child in cast(dict[str, Any], value).items():
            yield from _reference_strings(child, child_key)
    elif isinstance(value, list):
        for child in cast(list[Any], value):
            yield from _reference_strings(child, key)
    elif isinstance(value, str) and (
        key.endswith("path")
        or key.endswith("paths")
        or key.endswith("reference")
        or key.endswith("references")
        or key.endswith("predecessor_ids")
    ):
        yield value


def _validate_no_mutable_or_self_reference(closure: dict[str, Any]) -> None:
    for value in _reference_strings(closure):
        lowered = value.lower()
        assert "/latest" not in lowered
        assert not lowered.endswith("latest")
    source_paths = {
        item["path"] for item in closure["source_locks"]["immutable_inputs"]
    }
    assert all("/closures/s1-p00-phase-closure/" not in path for path in source_paths)
    _validate_artifact_chain(closure)


def _validate_markdown(closure: dict[str, Any]) -> None:
    raw = CLOSURE_MARKDOWN.read_bytes()
    text = raw.decode("utf-8")
    assert len(raw) == EXPECTED_MARKDOWN_LENGTH
    assert _sha256(raw) == EXPECTED_MARKDOWN_SHA256
    assert not raw.startswith(b"\xef\xbb\xbf")
    assert b"\r" not in raw
    assert raw.endswith(b"\n") and not raw.endswith(b"\n\n")
    assert text.count(EXPECTED_CLOSURE_SHA256) == 1
    headings = [
        "## 1. Scope and Authority Warning",
        "## 2. Primary JSON Digest",
        "## 3. Executive Closure Verdict",
        "## 4. Phase and Canonical-Case Identity",
        "## 5. S01–S10 Slice Ledger",
        "## 6. Immutable Artifact Chain",
        "## 7. S09 Deterministic-Test Assurance",
        "## 8. S1.P00 Exit Criteria",
        "## 9. Established Findings",
        "## 10. Non-Generalizable Findings",
        "## 11. Deferred Register Summary",
        "## 12. S1.P01 Entry Readiness",
        "## 13. Publication Conditions",
        "## 14. S1.P01 Remains Not Started",
        "## 15. Non-Universal Schema Warning",
    ]
    positions = [text.index(heading) for heading in headings]
    assert positions == sorted(positions)
    for item in closure["slice_ledger"]["items"]:
        assert text.count(f"- `{item['slice_id']}` —") == 1
    for item in closure["artifact_chain"]["layers"]:
        assert text.count(f"- `{item['layer_id']}` —") == 1
    for item in closure["exit_criteria"]["items"]:
        expected = f"- `{item['criterion_id']}` — `{item['outcome']}`:"
        assert text.count(expected) == 1
    for item in closure["established_findings"]:
        assert text.count(f"- `{item['finding_id']}` —") == 1
    for item in closure["non_generalizations"]["items"]:
        assert text.count(f"- `{item['non_generalization_id']}` —") == 1
    for item in closure["deferred_register"]["items"]:
        assert text.count(f"- `{item['deferred_item_id']}` —") == 1
    assert "`S1.P01` is `eligible_to_begin`" in text
    assert "implementation `not_started`" in text
    assert "This is not a universal phase-closure schema" in text


def _validate_privacy() -> None:
    combined = b"\n".join(
        path.read_bytes() for path in (CLOSURE_JSON, CLOSURE_SIDECAR, CLOSURE_MARKDOWN)
    )
    lowered = combined.lower()
    forbidden = (
        b"/home/",
        b"/users/",
        b"/tmp/",
        b"authorization:",
        b"private key",
        b"begin rsa",
        b"discussion_body",
        b'"body":',
    )
    assert all(marker not in lowered for marker in forbidden)
    assert (
        re.search(rb"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", combined) is None
    )
    assert re.search(rb"[A-Za-z]:\\", combined) is None


def _archive_members(path: Path) -> Iterator[tuple[str, bytes]]:
    if path.suffix == ".whl":
        with zipfile.ZipFile(path) as archive:
            for info in archive.infolist():
                mode = info.external_attr >> 16
                assert not stat.S_ISLNK(mode)
                if not info.is_dir():
                    yield info.filename, archive.read(info)
        return
    with tarfile.open(path, mode="r:gz") as archive:
        for info in archive.getmembers():
            assert info.isdir() or info.isfile()
            if info.isfile():
                extracted = archive.extractfile(info)
                assert extracted is not None
                yield info.name, extracted.read()


def _validate_archive(path: Path) -> None:
    markers = (
        b"reference_corpus",
        b"pytest-4412",
        b"closures",
        b"s1-p00-phase-closure",
        b"closure.json",
        b"closure.sha256",
        b"closure.md",
        EXPECTED_FORMAT.encode(),
    )
    historical_license = (
        REPOSITORY_ROOT / "reference_corpus/pytest-4412/acquisitions/"
        "run-0001-s04-v1-base-4c9cde74-head-690a63b9/artifacts/LICENSE"
    ).read_bytes()
    for name, data in _archive_members(path):
        pure = PurePosixPath(name)
        assert not pure.is_absolute()
        assert ".." not in pure.parts
        lowered_name = name.lower().encode()
        lowered_data = data.lower()
        assert all(marker.lower() not in lowered_name for marker in markers)
        assert all(marker.lower() not in lowered_data for marker in markers)
        assert data != historical_license
        if path.suffix == ".whl":
            assert "tests" not in pure.parts


def test_primary_closure_is_locked_canonical_json() -> None:
    raw, closure = _load_closure()
    _validate_primary_lock(raw)
    assert not raw.startswith(b"\xef\xbb\xbf")
    assert b"\r" not in raw
    assert raw.endswith(b"\n") and not raw.endswith(b"\n\n")
    _assert_no_float(closure)
    assert raw == _canonical_bytes(closure)


def test_closure_sidecar_is_independently_locked() -> None:
    _validate_primary_lock(CLOSURE_JSON.read_bytes(), CLOSURE_SIDECAR.read_bytes())


def test_format_phase_and_candidate_state_are_exact() -> None:
    _, closure = _load_closure()
    _validate_format_and_candidate_state(closure)


@pytest.mark.parametrize("path", tuple(EXPECTED_LOCKS))
def test_each_upstream_source_lock_is_exact(path: str) -> None:
    expected_sha, expected_length, expected_mode = EXPECTED_LOCKS[path]
    target = REPOSITORY_ROOT / path
    data = target.read_bytes()
    assert not target.is_symlink()
    assert _sha256(data) == expected_sha
    assert len(data) == expected_length
    assert stat.S_IMODE(target.stat().st_mode) == int(expected_mode[-3:], 8)


@pytest.mark.parametrize("path", tuple(EXPECTED_UPSTREAM_SIDECARS))
def test_each_upstream_sidecar_is_exact(path: str) -> None:
    assert (REPOSITORY_ROOT / path).read_text(encoding="ascii") == (
        EXPECTED_UPSTREAM_SIDECARS[path]
    )


def test_closure_source_lock_table_is_independent_and_complete() -> None:
    _, closure = _load_closure()
    _validate_source_lock_table(closure)
    for item in closure["source_locks"]["immutable_inputs"]:
        data = (REPOSITORY_ROOT / item["path"]).read_bytes()
        framed = f"blob {len(data)}\0".encode() + data
        git_blob = hashlib.sha1(framed, usedforsecurity=False).hexdigest()
        assert item["git_blob_sha1"] == git_blob


def test_slice_ledger_is_complete_unique_ordered_and_evidenced() -> None:
    _, closure = _load_closure()
    _validate_slice_ledger(closure)


def test_artifact_chain_is_append_only_and_acyclic() -> None:
    _, closure = _load_closure()
    _validate_artifact_chain(closure)


def test_s09_historical_assurance_is_exact_and_not_a_future_source_lock() -> None:
    _, closure = _load_closure()
    _validate_s09_assurance(closure)


def test_exit_criteria_are_complete_with_zero_unsatisfied() -> None:
    _, closure = _load_closure()
    _validate_exit_criteria(closure)


def test_findings_and_non_generalizations_are_exact() -> None:
    _, closure = _load_closure()
    _validate_findings(closure)


def test_deferred_register_has_complete_valid_ownership() -> None:
    _, closure = _load_closure()
    _validate_deferred_register(closure)


def test_deferred_source_pointers_resolve_to_exact_source_records() -> None:
    _, closure = _load_closure()
    _validate_deferred_source_pointers(closure)


def test_s06_decisions_and_all_gaps_are_reconciled() -> None:
    _, closure = _load_closure()
    _validate_s06_reconciliation(closure)


def test_s07_and_s08_handoffs_are_preserved_or_satisfied() -> None:
    _, closure = _load_closure()
    handoffs = closure["deferred_register"]["handoff_reconciliation"]
    assert len(handoffs) == 12
    ids = [item["handoff_id"] for item in handoffs]
    assert len(ids) == len(set(ids))
    assert all(_valid_owner(item["owner"]) for item in handoffs)
    assert all(
        item["outcome"].startswith("satisfied_by_")
        or item["outcome"].startswith("accepted_by_")
        or item["outcome"] == "deferred_not_started"
        for item in handoffs
    )


def test_p01_is_eligible_but_not_started_and_scope_is_guarded() -> None:
    _, closure = _load_closure()
    _validate_entry_readiness(closure)


def test_production_surface_is_exact_and_legacy_models_are_unchanged() -> None:
    production_files = {
        path.relative_to(REPOSITORY_ROOT).as_posix()
        for path in (REPOSITORY_ROOT / "src").rglob("*.py")
    }
    _validate_current_production_file_inventory(production_files)
    identity_source = (
        REPOSITORY_ROOT / "src/faultatlas/domain/identity.py"
    ).read_bytes()
    _validate_identity_symbol_inventory(identity_source)
    compatibility_source = (
        REPOSITORY_ROOT / "src/faultatlas/domain/compatibility.py"
    ).read_bytes()
    _validate_compatibility_symbol_inventory(compatibility_source)
    revision_source = (
        REPOSITORY_ROOT / "src/faultatlas/domain/revision.py"
    ).read_bytes()
    _validate_revision_symbol_inventory(revision_source)
    _validate_current_evidence_inventory(
        (REPOSITORY_ROOT / EVIDENCE_MODULE).read_bytes()
    )
    source_path = REPOSITORY_ROOT / "src/faultatlas/domain/source.py"
    source = source_path.read_bytes()
    assert len(source) == 4336
    assert _sha256(source) == (
        "034e53fd58212f0e34376bbc790fc3e74057031aaed4d7d89fb67904bdd380bf"
    )
    tree = ast.parse(source)
    assert [node.name for node in tree.body if isinstance(node, ast.ClassDef)] == [
        "SourceLocator",
        "ArtifactSnapshot",
    ]
    _validate_source_locator_method_inventory(source)
    _validate_package_root_exports(
        (REPOSITORY_ROOT / "src/faultatlas/__init__.py").read_bytes()
    )
    domain_root = ast.parse(
        (REPOSITORY_ROOT / "src/faultatlas/domain/__init__.py").read_bytes()
    )
    assert not any(
        isinstance(node, (ast.Import, ast.ImportFrom)) for node in domain_root.body
    )
    complete_production_source = b"\n".join(
        (REPOSITORY_ROOT / path).read_bytes() for path in sorted(production_files)
    )
    assert b"AlternateIdBinding" not in complete_production_source
    assert b"EvidenceAdapterRegistry" not in complete_production_source
    assert b"EvidenceContractCorpus" not in complete_production_source
    assert b"MigrationRegistry" not in complete_production_source
    assert b"RepositorySnapshot" not in complete_production_source
    for forbidden in (
        b"GitCommitRole",
        b"GitParentIdentity",
        b"GitRepositoryMembership",
        b"MutableRefObservation",
        b"GitRefTransition",
        b"GitRefHistory",
        b"GitSymbolicRef",
        b"RepositorySnapshot",
    ):
        assert forbidden not in complete_production_source
    revision_tree = ast.parse(revision_source)
    revision_definitions = {
        node.name
        for node in ast.walk(revision_tree)
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
    }
    revision_definitions.update(
        node.name.id
        for node in ast.walk(revision_tree)
        if isinstance(node, ast.TypeAlias)
    )
    assert not revision_definitions & {
        "ByteLocator",
        "EvidenceEnvelope",
        "HunkLocator",
        "LineLocator",
        "LocatorContractCorpus",
        "LocatorReader",
        "LocatorResolver",
    }
    for name in revision_definitions:
        compact_name = name.replace("_", "").lower()
        assert not (
            "locator" in compact_name
            and any(
                forbidden_role in compact_name
                for forbidden_role in ("corpus", "reader", "resolver")
            )
        )
    assert not (REPOSITORY_ROOT / "reference_corpus/pytest-4412/phases/S1.P01").exists()


def test_identity_correction_is_append_only_with_external_s06_closure() -> None:
    assert {path.name for path in IDENTITY_V1_DIRECTORY.iterdir()} == (
        EXPECTED_IDENTITY_V1_FILES
    )
    assert {path.name for path in IDENTITY_CORRECTION_DIRECTORY.iterdir()} == (
        EXPECTED_IDENTITY_CORRECTION_FILES
    )
    assert all(
        path.is_file() and not path.is_symlink()
        for path in IDENTITY_CORRECTION_DIRECTORY.iterdir()
    )
    identity_root = IDENTITY_V1_DIRECTORY.parent
    contracts_root = identity_root.parent
    assert {path.name for path in contracts_root.iterdir()} == {
        "evidence-envelope",
        "identity",
        "revision-locator",
    }
    assert {path.name for path in identity_root.iterdir()} == {
        "closures",
        "corrections",
        "v1",
    }
    closures_root = identity_root / "closures"
    assert {path.name for path in closures_root.iterdir()} == {"s1-p01-phase-closure"}
    assert {path.name for path in IDENTITY_S06_CLOSURE_DIRECTORY.iterdir()} == {
        "closure.json",
        "closure.md",
        "closure.sha256",
    }
    assert all(
        path.is_file() and not path.is_symlink()
        for path in IDENTITY_S06_CLOSURE_DIRECTORY.iterdir()
    )
    closure_test = REPOSITORY_ROOT / "tests/test_identity_phase_closure.py"
    assert closure_test.is_file() and not closure_test.is_symlink()
    revision_locator_root = contracts_root / "revision-locator"
    assert {path.name for path in revision_locator_root.iterdir()} == {
        "closures",
        "v1",
    }
    assert {path.name for path in REVISION_LOCATOR_V1_DIRECTORY.iterdir()} == (
        EXPECTED_REVISION_LOCATOR_FILES
    )
    assert all(
        path.is_file()
        and not path.is_symlink()
        and stat.S_IMODE(path.stat().st_mode) == 0o644
        for path in REVISION_LOCATOR_V1_DIRECTORY.iterdir()
    )
    assert not (revision_locator_root / "latest").exists()
    assert not (revision_locator_root / "current").exists()
    revision_locator_closures = revision_locator_root / "closures"
    assert (
        revision_locator_closures.is_dir()
        and not revision_locator_closures.is_symlink()
    )
    assert {path.name for path in revision_locator_closures.iterdir()} == {
        "s1-p02-phase-closure"
    }
    phase_closure = revision_locator_closures / "s1-p02-phase-closure"
    assert phase_closure.is_dir() and not phase_closure.is_symlink()
    assert {path.name for path in phase_closure.iterdir()} == {
        "closure.json",
        "closure.md",
        "closure.sha256",
    }
    assert all(
        path.is_file()
        and not path.is_symlink()
        and stat.S_IMODE(path.stat().st_mode) == 0o644
        for path in phase_closure.iterdir()
    )


@pytest.mark.parametrize("symbol", sorted(EXPECTED_S02_IDENTITY_SYMBOLS))
def test_omitting_authorized_s02_identity_export_is_rejected(symbol: str) -> None:
    source = (REPOSITORY_ROOT / "src/faultatlas/domain/identity.py").read_text(
        encoding="utf-8"
    )
    mutated = source.replace(f'    "{symbol}",\n', "", 1).encode()

    with pytest.raises(AssertionError):
        _validate_identity_symbol_inventory(mutated)


@pytest.mark.parametrize("symbol", sorted(EXPECTED_S03_IDENTITY_SYMBOLS))
def test_omitting_authorized_s03_identity_export_is_rejected(symbol: str) -> None:
    source = (REPOSITORY_ROOT / "src/faultatlas/domain/identity.py").read_text(
        encoding="utf-8"
    )
    mutated = source.replace(f'    "{symbol}",\n', "", 1).encode()

    with pytest.raises(AssertionError):
        _validate_identity_symbol_inventory(mutated)


def test_unexpected_synthetic_identity_symbol_is_rejected() -> None:
    source = (REPOSITORY_ROOT / "src/faultatlas/domain/identity.py").read_bytes()
    mutated = source + b"\nclass SyntheticIdentity:\n    pass\n"

    with pytest.raises(AssertionError):
        _validate_identity_symbol_inventory(mutated)


@pytest.mark.parametrize("symbol", sorted(EXPECTED_COMPATIBILITY_SYMBOLS))
def test_omitting_expected_compatibility_export_is_rejected(symbol: str) -> None:
    source = (REPOSITORY_ROOT / "src/faultatlas/domain/compatibility.py").read_text(
        encoding="utf-8"
    )
    mutated = source.replace(f'    "{symbol}",\n', "", 1).encode()

    with pytest.raises(AssertionError):
        _validate_compatibility_symbol_inventory(mutated)


def test_unexpected_compatibility_export_is_rejected() -> None:
    source = (REPOSITORY_ROOT / "src/faultatlas/domain/compatibility.py").read_text(
        encoding="utf-8"
    )
    mutated = source.replace(
        '    "CompatibilityStatus",\n',
        '    "CompatibilityStatus",\n    "UnexpectedCompatibility",\n',
        1,
    )
    mutated += "\nclass UnexpectedCompatibility:\n    pass\n"

    with pytest.raises(AssertionError):
        _validate_compatibility_symbol_inventory(mutated.encode())


def test_omitting_compatibility_module_from_production_inventory_is_rejected() -> None:
    mutated = EXPECTED_PRODUCTION_FILES - {"src/faultatlas/domain/compatibility.py"}

    with pytest.raises(AssertionError):
        _validate_production_file_inventory(mutated)


def test_omitting_revision_module_from_production_inventory_is_rejected() -> None:
    mutated = EXPECTED_PRODUCTION_FILES - {"src/faultatlas/domain/revision.py"}

    with pytest.raises(AssertionError):
        _validate_production_file_inventory(mutated)


def test_unexpected_production_module_is_rejected() -> None:
    mutated = EXPECTED_PRODUCTION_FILES | {
        "src/faultatlas/domain/unexpected_identity.py"
    }

    with pytest.raises(AssertionError):
        _validate_production_file_inventory(mutated)


def test_current_p03_s01_production_inventory_mutations_are_rejected() -> None:
    with pytest.raises(AssertionError):
        _validate_current_production_file_inventory(
            CURRENT_PRODUCTION_FILES - {EVIDENCE_MODULE}
        )
    with pytest.raises(AssertionError):
        _validate_current_production_file_inventory(
            CURRENT_PRODUCTION_FILES | {"src/faultatlas/domain/unexpected.py"}
        )


def test_current_p03_s01_evidence_export_mutations_are_rejected() -> None:
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


@pytest.mark.parametrize(
    "missing_symbol",
    tuple(
        sorted(
            EXPECTED_S05_REVISION_SYMBOLS
            | {"GitRepositoryPath", "RevisionQualifiedPath", "GitRefObservation"}
        )
    ),
)
def test_revision_export_inventory_mutations_are_rejected(
    missing_symbol: str,
) -> None:
    source = (REPOSITORY_ROOT / "src/faultatlas/domain/revision.py").read_text(
        encoding="utf-8"
    )
    missing = source.replace(f'    "{missing_symbol}",\n', "", 1)
    with pytest.raises(AssertionError):
        _validate_revision_symbol_inventory(missing.encode())
    unexpected = source.replace(
        '    "GitRefObservation",\n',
        '    "GitRefObservation",\n    "UnexpectedRevision",\n',
        1,
    )
    with pytest.raises(AssertionError):
        _validate_revision_symbol_inventory(unexpected.encode())


@pytest.mark.parametrize(
    "function_name",
    ["map_legacy_source_locator", "project_source_identity_to_legacy"],
)
def test_compatibility_function_added_to_source_locator_is_rejected(
    function_name: str,
) -> None:
    source = (REPOSITORY_ROOT / "src/faultatlas/domain/source.py").read_text(
        encoding="utf-8"
    )
    addition = f"\n    def {function_name}(self) -> None:\n        pass\n"
    mutated = source.replace(
        "\n\nclass ArtifactSnapshot", addition + "\n\nclass ArtifactSnapshot", 1
    )

    with pytest.raises(AssertionError):
        _validate_source_locator_method_inventory(mutated.encode())


@pytest.mark.parametrize(
    ("module", "symbol"),
    (
        ("compatibility", "CompatibilityStatus"),
        ("evidence", "RetrievalRequestReference"),
        ("revision", "BoundedLocator"),
        ("revision", "GitRefObservation"),
        ("revision", "RevisionQualifiedPath"),
    ),
)
def test_package_root_domain_export_is_rejected(module: str, symbol: str) -> None:
    source = (REPOSITORY_ROOT / "src/faultatlas/__init__.py").read_text(
        encoding="utf-8"
    )
    mutated = source + (
        f"\nfrom faultatlas.domain.{module} import {symbol}\n"
        f'__all__.append("{symbol}")\n'
    )

    with pytest.raises(AssertionError):
        _validate_package_root_exports(mutated.encode())


def test_publication_contract_requires_protected_external_completion() -> None:
    _, closure = _load_closure()
    _validate_publication_contract(closure)


def test_no_mutable_pointer_self_reference_or_source_cycle_exists() -> None:
    _, closure = _load_closure()
    _validate_no_mutable_or_self_reference(closure)


def test_closure_markdown_is_locked_and_synchronized() -> None:
    _, closure = _load_closure()
    _validate_markdown(closure)


def test_closure_files_are_private_path_and_payload_safe() -> None:
    _validate_privacy()


def test_roadmap_and_case_documentation_match_current_semantics() -> None:
    roadmap = (REPOSITORY_ROOT / "docs/roadmap.md").read_text(encoding="utf-8")
    normalized_roadmap = " ".join(roadmap.split())
    case_doc = (REPOSITORY_ROOT / "docs/reference_cases/pytest-4412.md").read_text(
        encoding="utf-8"
    )
    assert "S1.P00.S10" in roadmap
    assert "S1.P01" in roadmap
    assert (
        "`S1.P01.S02` — Source Object Identity and Typed Identifiers (complete)"
        in normalized_roadmap
    )
    assert (
        "`S1.P01.S03` — Identity States, Lifecycle, and Conflict (complete)"
        in normalized_roadmap
    )
    assert (
        "`S1.P01.S04` — Legacy SourceLocator Compatibility Mapping (complete)"
        in normalized_roadmap
    )
    assert "`S1.P01.S05` — Identity Contract Corpus (complete)" in normalized_roadmap
    assert (
        "`S1.P01.S05.C01` — Ambiguous Identity Union Round-Trip and Contract "
        "Assurance Correction (complete)" in normalized_roadmap
    )
    assert (
        "`S1.P01.S06` — Integration and Phase Closure (complete; closes "
        "`S1.P01`)" in normalized_roadmap
    )
    assert "`S1.P01` is complete" in normalized_roadmap
    assert "`S1.P02` is complete" in normalized_roadmap
    assert "`S1.P02.S01` is complete" in normalized_roadmap
    assert "`S1.P02.S02` is complete" in normalized_roadmap
    assert "`S1.P02.S03` is complete" in normalized_roadmap
    assert "`S1.P02.S04` is complete" in normalized_roadmap
    assert "`S1.P02.S05` is complete" in normalized_roadmap
    assert "`S1.P02.S06` is complete" in normalized_roadmap
    assert "`S1.P02.S07` is complete" in normalized_roadmap
    assert "`S1.P03` is active" in normalized_roadmap
    assert "`S1.P03.S01` is complete" in normalized_roadmap
    assert "`S1.P03.S02` is complete" in normalized_roadmap
    assert "`S1.P03.S03` is complete" in normalized_roadmap
    assert "`S1.P03.S04` is complete" in normalized_roadmap
    assert (
        "`S1.P03.S05`, `S1.P03.S06`, `S1.P03.S07`, and `S1.P03.S08` are complete"
        in normalized_roadmap
    )
    assert "`S1.P03.S09` is next and not started" in normalized_roadmap
    assert "only its S01 retrieval-request identity" not in normalized_roadmap
    for slice_id, title, state in EXPECTED_P03_SLICE_SEQUENCE:
        assert f"`{slice_id}` — {title} ({state})" in normalized_roadmap
    for slice_id in range(6, 8):
        assert f"`S1.P02.S{slice_id:02d}`" in normalized_roadmap
    assert "s1-p00-phase-closure" in case_doc
    normalized_case_doc = " ".join(case_doc.split())
    assert (
        "nine canonical S1.P02.S01 Git object identity test vectors"
        in normalized_case_doc
    )
    assert (
        "retained-artifact SHA-256 remains a separate artifact digest"
        in normalized_case_doc
    )
    assert (
        "S1.P02.S02 adds the four context-relative revision roles and an "
        "ordered commit-parent topology record" in normalized_case_doc
    )
    assert (
        "S1.P02.S03 uses the locked case without fabricating a complete "
        "canonical ref observation" in normalized_case_doc
    )
    assert (
        "directly retains ref lexeme `starred_with_side_effect` with head SHA "
        "`690a63b9218f72662cd3a67c6c200b758c88ce12`" in normalized_case_doc
    )
    assert (
        "later head-ref deletion is separately observed. Treating that SHA as "
        "the former target is a reviewed derivation" in normalized_case_doc
    )
    assert (
        "original head repository identity remains unknown, and no ref "
        "namespace is retained" in normalized_case_doc
    )
    assert (
        "Provider event time `2018-11-18T00:17:28Z` is deletion-event evidence, "
        "not FaultAtlas observation time" in normalized_case_doc
    )
    assert (
        "Repository- and namespace-qualified ref subjects and observation "
        "times used by S03 tests are therefore explicitly synthetic"
        in normalized_case_doc
    )
    assert (
        "S1.P02.S04 projects four canonical revision-qualified path vectors "
        "from the locked acquisition’s directly observed head-path inventory"
        in normalized_case_doc
    )
    assert (
        "bounded UTF-8 path lexeme is preserved exactly without case, Unicode, "
        "or separator normalization" in normalized_case_doc
    )
    assert (
        "S1.P02.S05 classifies the three retained-diff coordinate layers "
        "without collapsing them" in normalized_case_doc
    )
    assert (
        "Offsets and lengths are direct exact-byte facts; old/new hunk spans "
        "are deterministic derivations from exact unified-diff headers"
        in normalized_case_doc
    )
    assert (
        "applicable new-file line ranges remain reviewed derived interpretation"
        in normalized_case_doc
    )
    assert (
        "S1.P02.S06 publishes a versioned, internal, source-only revision and "
        "locator contract corpus with valid, invalid, and exact-replay vectors "
        "kept separate" in normalized_case_doc
    )
    assert (
        "The corpus adds no production reader, locator resolver, persistence "
        "contract, or public API" in normalized_case_doc
    )
    assert (
        "`S1.P02.S07` publishes the internal, case-calibrated revision/locator "
        "Phase closure" in normalized_case_doc
    )
    assert (
        "without rewriting the canonical pytest #4412 artifacts or the "
        "immutable S06 contract corpus" in normalized_case_doc
    )
    assert (
        "`S1.P02` is complete and `S1.P02.S01` through `S1.P02.S07` are "
        "complete" in normalized_case_doc
    )
    assert "`S1.P03` is active" in normalized_case_doc
    assert "32 canonical request IDs" in normalized_case_doc
    assert "zero canonical full request references" in normalized_case_doc
    assert "two explicitly synthetic full request references" in normalized_case_doc
    assert "observed request-method vocabulary is GET-only" in normalized_case_doc
    assert (
        "run ID, ordinal, and request-start time are directly retained"
        in normalized_case_doc
    )
    assert (
        "lowercase `get` and the query-free route path are deterministic "
        "projections" in normalized_case_doc
    )
    assert "S1.P03.S03 Exact Retained Artifacts and Digest Scope" in case_doc
    assert (
        "Request ordinal 30 retained the 1,640-byte "
        "`artifacts/base-to-head.diff` HTTP entity body" in normalized_case_doc
    )
    assert (
        "Request ordinal 32 retained the 1,096-byte `artifacts/LICENSE` Git "
        "blob content" in normalized_case_doc
    )
    assert "Both acquisition entries classify retention as" in normalized_case_doc
    assert (
        "The production records are metadata-only and perform no artifact I/O"
        in normalized_case_doc
    )
    assert "S1.P03.S04 Acquisition Runs and Evidence Membership" in case_doc
    assert "32 contiguous request memberships" in normalized_case_doc
    assert "known-empty tuples" in normalized_case_doc


def test_offline_build_excludes_closure_from_wheel_and_sdist(tmp_path: Path) -> None:
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
            "UV_OFFLINE": "1",
            "UV_NO_SYNC": "1",
        }
    )
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
    assert result.returncode == 0, (
        f"offline uv build failed\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )
    wheel = tuple(output.glob("*.whl"))
    sdist = tuple(output.glob("*.tar.gz"))
    assert len(wheel) == len(sdist) == 1
    _validate_archive(wheel[0])
    _validate_archive(sdist[0])


def _remove_ledger_item(closure: dict[str, Any]) -> None:
    del closure["slice_ledger"]["items"][4]


def _duplicate_ledger_id(closure: dict[str, Any]) -> None:
    closure["slice_ledger"]["items"][1]["slice_id"] = "S1.P00.S01"


def _reorder_ledger(closure: dict[str, Any]) -> None:
    items = closure["slice_ledger"]["items"]
    items[1], items[2] = items[2], items[1]


def _break_upstream_digest(closure: dict[str, Any]) -> None:
    closure["source_locks"]["immutable_inputs"][0]["sha256"] = "0" * 64


def _make_exit_unsatisfied(closure: dict[str, Any]) -> None:
    closure["exit_criteria"]["items"][0]["outcome"] = "unsatisfied"


def _remove_deferred_owner(closure: dict[str, Any]) -> None:
    del closure["deferred_register"]["items"][0]["immediate_next_owner"]


def _start_p01(closure: dict[str, Any]) -> None:
    closure["entry_readiness"]["implementation"] = "started"


def _mark_published(closure: dict[str, Any]) -> None:
    closure["format"]["publication_state"] = "published"


def _add_self_reference(closure: dict[str, Any]) -> None:
    item = copy.deepcopy(closure["source_locks"]["immutable_inputs"][0])
    item["path"] = (
        "reference_corpus/pytest-4412/closures/s1-p00-phase-closure/closure.json"
    )
    closure["source_locks"]["immutable_inputs"].append(item)


def _add_mutable_latest(closure: dict[str, Any]) -> None:
    closure["source_locks"]["immutable_inputs"][0]["path"] = (
        "reference_corpus/pytest-4412/acquisitions/latest/acquisition.json"
    )


Mutation = tuple[
    str, Callable[[dict[str, Any]], None], Callable[[dict[str, Any]], None]
]

SEMANTIC_MUTATIONS: tuple[Mutation, ...] = (
    ("broken-upstream-digest", _break_upstream_digest, _validate_source_lock_table),
    ("removed-ledger-item", _remove_ledger_item, _validate_slice_ledger),
    ("duplicate-ledger-id", _duplicate_ledger_id, _validate_slice_ledger),
    ("reordered-ledger", _reorder_ledger, _validate_slice_ledger),
    ("unsatisfied-exit", _make_exit_unsatisfied, _validate_exit_criteria),
    ("missing-deferred-owner", _remove_deferred_owner, _validate_deferred_register),
    ("P01-started", _start_p01, _validate_entry_readiness),
    (
        "candidate-marked-published",
        _mark_published,
        _validate_format_and_candidate_state,
    ),
    (
        "source-lock-self-reference",
        _add_self_reference,
        _validate_no_mutable_or_self_reference,
    ),
    (
        "mutable-latest-reference",
        _add_mutable_latest,
        _validate_no_mutable_or_self_reference,
    ),
)


def test_changed_closure_json_byte_is_rejected() -> None:
    raw = bytearray(CLOSURE_JSON.read_bytes())
    raw[17] = raw[17] ^ 1
    with pytest.raises(AssertionError):
        _validate_primary_lock(bytes(raw))


def test_coordinated_json_and_sidecar_reseal_is_rejected() -> None:
    raw, closure = _load_closure()
    closure["format"]["sealed_at"] = "2099-01-01T00:00:00Z"
    mutated = _canonical_bytes(closure)
    resealed = f"{_sha256(mutated)}  closure.json\n".encode()
    assert resealed.endswith(b"  closure.json\n")
    assert raw != mutated
    with pytest.raises(AssertionError):
        _validate_primary_lock(mutated, resealed)


@pytest.mark.parametrize(
    ("name", "mutate", "validator"),
    SEMANTIC_MUTATIONS,
    ids=[item[0] for item in SEMANTIC_MUTATIONS],
)
def test_semantic_mutation_is_rejected(
    name: str,
    mutate: Callable[[dict[str, Any]], None],
    validator: Callable[[dict[str, Any]], None],
) -> None:
    del name
    _, closure = _load_closure()
    mutate(closure)
    with pytest.raises((AssertionError, KeyError)):
        validator(closure)
