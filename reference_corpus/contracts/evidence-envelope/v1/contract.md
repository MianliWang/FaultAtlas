# FaultAtlas Evidence Envelope contract corpus v1

Internal, non-public, source-repository-only, case-calibrated contract corpus
for the `S1.P03.S01`-`S1.P03.S07` Evidence Envelope behavior implemented in
`faultatlas.domain.evidence`. Published by `S1.P03.S08`.

Derived, non-authoritative Markdown; the canonical JSON files remain the sole contract authority.

- Corpus identity: `faultatlas-evidence-envelope-contract-corpus`
- Corpus version: `1`
- Manifest SHA-256:
  `1db40c259e40dc6eb5f6019f2355fba9ac6a272f16b45856c9fd75bd14baf97b`

## Scope

The corpus freezes already-published behavior. It adds no product semantics and
adds no production reader, writer, or validator. Supporting authorities in
`faultatlas.domain.identity`, `faultatlas.domain.revision`,
`faultatlas.domain.source`, and `faultatlas.domain.compatibility` are used
through an explicit test-only allowlist and are not owned here.

## File inventory

Exactly nine tracked files, each a regular file with Git mode `100644` and
filesystem mode `0644`:

1. `manifest.json`
2. `manifest.sha256`
3. `valid-vectors.json`
4. `valid-vectors.sha256`
5. `invalid-vectors.json`
6. `invalid-vectors.sha256`
7. `replay-vectors.json`
8. `replay-vectors.sha256`
9. `contract.md`

## Covered symbols

All 58 current `faultatlas.domain.evidence` exports have a direct executable
vector target.

`S1.P03.S01`: `AcquisitionRunId`, `RetrievalRequestOrdinal`,
`RetrievalRequestId`, `RetrievalMethod`, `RetrievalRoutePath`,
`RetrievalRequestReference`.

`S1.P03.S02`: `MediaType`, `ApiVersion`, `RequestQueryParameter`,
`RetrievalRequestControls`, `ResponseRepresentationState`, `HttpStatusCode`,
`ContentEncoding`, `MediaTypeParameter`, `ResponseRepresentationObservation`.

`S1.P03.S03`: `ArtifactDigestAlgorithm`, `ArtifactDigestScope`,
`ArtifactSha256Digest`, `ArtifactByteLength`, `ArtifactDigest`,
`ExactArtifactIdentity`, `ArtifactRetentionMode`, `ExactRetainedArtifact`.

`S1.P03.S04`: `AcquisitionRunStatus`, `AcquisitionRequestMembership`,
`AcquisitionRun`.

`S1.P03.S05`: `EvidenceRecordFormat`, `EvidenceVersion`,
`EvidenceCanonicalization`, `DurableEvidenceRecordReference`,
`EvidenceRelationId`, `TransformationOperation`, `TransformationLossiness`,
`TransformationReversibility`, `TransformationSubject`,
`EvidenceTransformation`, `EvidenceCorrection`, `EvidenceSupersession`,
`EvidenceRecordRelationship`.

`S1.P03.S06`: `EvidenceScopeId`, `EvidenceRequirementId`,
`EvidenceDispositionReason`, `EvidenceRequirementOutcome`, `EvidenceOmission`,
`EvidenceRequirementResult`, `EvidenceCompletenessStatus`,
`EvidenceCompletenessAssessment`, `EvidencePublicationMethod`,
`PublicationCheckEvent`, `PublicationCheckName`, `SuccessfulPublicationCheck`,
`EvidencePublication`.

`S1.P03.S07`: `EvidenceEnvelope`, `LegacyEvidenceCompatibilityReason`,
`LegacyArtifactSnapshotEnvelopeMappingResult`,
`LegacyArtifactSnapshotProjectionResult`, `wrap_legacy_artifact_snapshot`,
`project_evidence_envelope_to_legacy_artifact_snapshot`.

`TransformationSubject` is a single discriminated record rather than a type
alias union, so it carries a direct record-model target.
`EvidenceRecordRelationship` is the only type alias union and is executed
through an explicit `TypeAdapter` target. Both `S1.P03.S07` adapter functions
are explicit adapter targets.

## Vector inventory

279 locked vectors in a contractual order, with unique identifiers.

Valid vectors (129):

```
"acquisition-run": 8
"completeness": 19
"durable-record": 13
"enum": 12
"envelope": 6
"exact-artifact": 14
"legacy-adapter": 3
"publication": 6
"relationship": 7
"request-controls": 12
"response-observation": 11
"retrieval-identity": 13
"transformation": 5
```

Invalid vectors (135):

```
"bounds": 19
"completeness-publication": 19
"enum": 12
"envelope-adapter": 21
"identity-linkage": 9
"strictness": 43
"transformation-relationship": 12
```

Replay vectors (15):

```
"canonical-artifact": 2
"canonical-completeness": 1
"canonical-correction": 1
"canonical-envelope": 2
"canonical-publication": 2
"canonical-run": 1
"legacy-adapter": 6
```

Twenty fixtures use stable explicit identifiers, resolve exactly once through
`{"fixture_ref": "..."}` singletons, stay file-local, and form a bounded
acyclic graph.

## Canonical replay

The canonical pytest #4412 envelope contains no legacy snapshot and no
standalone request membership, one sealed 32-request acquisition run, a
known-empty transformation inventory, one `S1.P00.S04.C01` correction, one
completeness assessment, and the acquisition and correction publications in
that order. Canonical transformation and supersession counts are both zero.

The two retained exact artifacts are locked by digest scope, SHA-256, and byte
length and are replayed against the tracked immutable reference bytes. The
completeness assessment declares seventeen requirements: two satisfied, then
fifteen source-ordered intentional omissions under one declared retention
reason. Publication records preserve stable repository identity, pull-request
number, distinct reviewed and published revisions, equal reviewed and published
trees, and separate pull-request and natural-main checks.

The canonical envelope projects to legacy v1 as `not_mappable` with
`legacy_snapshot_absent` and no projected snapshot; no legacy snapshot is ever
fabricated from modern evidence.

## Legacy adapter replay

Legacy fixtures are explicitly synthetic. The adapter replay freezes lossless
wrapping, exact projection of a wrapped legacy-only envelope, partial mapping
when a modern component is present, partial mapping when a modern component is
known-empty, refusal when no legacy snapshot exists, and refusal when several
legacy snapshots exist.

## Rejection behavior

Invalid vectors use a structured oracle of failure category, error location,
error type, and an optional stable message substring; unstable validator prose
is not locked. They cover strict typing, forbidden coercion, tuple versus list
input mode, unexpected fields, wrong schema versions, unknown enum members,
malformed identifiers, forbidden surrounding whitespace, every declared
collection ceiling at maximum plus one, identity and linkage mismatches, the
`S1.P03.S05` relationship invariants, the `S1.P03.S06` completeness and
publication invariants, and the `S1.P03.S07` envelope and adapter invariants.

## Boundaries

Python model equality, semantic JSON representation, corpus canonical JSON
bytes, retained exact artifact bytes, and future durable production record
bytes are five different concepts. The corpus byte convention
`json-sort-keys-compact-utf8-lf-v1` applies only to these tracked corpus files.
It is not a durable `EvidenceEnvelope` byte contract, not a production
serializer, and not a public wire format.

The executor `tests/test_evidence_contract_corpus.py` is the only registry for
this corpus. It uses a fixed test-only target registry, rejects unknown
targets, operations, markers, and support types, and performs no dynamic
import, arbitrary attribute traversal, `eval`, `exec`, plugin loading, network
access, or production file reading.

Corpus bytes are excluded from packaged artifacts: wheel, sdist, and installed resources.

## Handoff

`S1.P03.S09` owns integration and Phase closure. `S1.P10` owns persistence,
serialization, migration, registries, and any future durable record byte
format. Neither is implemented here.
