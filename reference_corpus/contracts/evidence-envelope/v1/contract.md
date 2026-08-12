# FaultAtlas Evidence Envelope contract corpus v1

Internal, non-public, source-repository-only, case-calibrated contract corpus
for the `S1.P03.S01`-`S1.P03.S07` Evidence Envelope behavior implemented in
`faultatlas.domain.evidence`. Published by `S1.P03.S08`.

Derived, non-authoritative Markdown; the canonical JSON files remain the sole contract authority.

- Corpus identity: `faultatlas-evidence-envelope-contract-corpus`
- Corpus version: `1`
- Manifest SHA-256:
  `139364b04676d59e4717a38e73b371b138146a2a933688ab3793aac6fd2e03f0`

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
completeness assessment, and the acquisition and correction publications in the
order the `S1.P00` slice ledger records their published subjects. Canonical
transformation and supersession counts are both zero.

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

## Replay provenance taxonomy

Replayed values fall into five explicitly separated categories, and the corpus
never conflates them.

1. Immutable source projection. A fact projected out of a named bounded source
   document through an explicit JSON pointer. The six projection kinds are
   `collect`, `length`, `self_digest`, `singleton`, `text`, and `value`, which
   cover string, integer, boolean, and list facts alike.
2. Deterministic reviewed derivation. A fact the executor recomputes from
   bounded source bytes, a bounded source document, the manifest registry, or
   validated composition state. The declared rules are
   `artifact_digest_algorithm`, `completeness_status`, `component_count`,
   `component_inventory`, `difference`, `legacy_projection_outcome`,
   `product`, `represented_modern_components`, `source_file_byte_length`,
   `source_ordered_subset`, and `sum`. A value the corpus manifest itself
   declares is not immutable evidence, so no derivation is rooted in the
   manifest.
3. Slice-authored contract label. An exact identifier or label a named
   `S1.P03` Slice introduced, which no earlier record contains. Authored
   labels are declared in `authored_labels` with their value, their authoring
   Slice, and any applicable decision reference. They are contract data, not
   source evidence, and are never described as immutable source facts,
   projected facts, derived facts, or independently recomputed facts.
4. Reviewed derived composition. The canonical envelope composition itself.
5. Synthetic contract example. Explicitly synthetic legacy adapter fixtures.

`expected.facts` may hold only projected or recomputed values. A value that is
neither projected, nor derived by a declared rule, nor declared as an authored
label is rejected.

## Verified value graph

Replay provenance is a computed property, not a set of prohibitions. Each
replay vector induces a dependency graph over its own facts:

- projected facts are read out of bounded source bytes and seed the verified
  value set;
- each derivation is a node whose edges point at the fact operands the
  test-side rule registry declares for its rule, never at a corpus-authored
  dependency list;
- the graph is checked for duplicate targets, projected/derived collisions,
  unknown operands, authored-label operands, direct self-reference, and cycles
  of any length, then evaluated in topological order.

A derivation consumes only already verified values, bounded source data, the
manifest registry, and validated composition state. The corpus-authored
expected value is a comparison target and is never a computation input, so a
fact cannot authenticate itself directly or through any chain. Every fact
carries the set of independent provenance roots its ancestry reaches:
`bounded_source_projection`, `bounded_source_bytes`, `bounded_source_document`,
and `composition_state`. Every chain must terminate in at least one of them.

The evidence classification is computed from those roots and then compared with
the declaration rather than accepted from it:

- no bounded source path and the declared synthetic authority ->
  `synthetic_contract_example`;
- bounded source provenance with one or more authored labels ->
  `bounded_source_plus_slice_authored_contract`;
- no authored labels and some fact reaching `composition_state` ->
  `reviewed_derived_composition`;
- no authored labels and every fact rooted only in bounded source or the
  manifest registry -> `immutable_source_fact`.

Relabelling a vector into any other classification is therefore rejected, in
both directions, without any vector identity being hard-coded.

## Canonical semantic-leaf closure

Fact provenance proves the facts a replay declares. It does not by itself prove
everything the replayed record carries, so every non-synthetic canonical replay
is additionally leaf-closed.

The executor flattens the validated model into stable semantic leaf paths,
cross-checks that path set against the complete semantic dump, and requires

```
semantic_leaf_paths == primary_covered_leaf_paths
```

Every leaf has exactly one primary proof owner drawn from six classes:

1. `bounded_source_projection` - the leaf resolves at an exact JSON pointer in a
   registered immutable source document, with model sequence position mapped to
   source sequence position rather than to any equal value.
2. `verified_retained_bytes` - the leaf is hashed or measured from the actual
   retained file.
3. `deterministic_derivation` - the leaf equals a fact recomputed through the
   acyclic provenance graph.
4. `slice_authored_contract` - the value was genuinely introduced by an
   `S1.P03` Slice and is declared separately from the record it verifies, with
   its authoring Slice and any governing decision reference.
5. `reviewed_contract_literal` - model introspection proves the concrete field
   admits exactly one value. A multi-valued enumeration never qualifies, and the
   permitted value is computed from the model rather than declared in corpus
   data.
6. `verified_child_replay` - a whole subtree is delegated to another canonical
   replay that has itself already passed complete leaf verification.

Child bindings are transitive verified dependencies, not raw corpus-record
equality: a parent consumes the child's verified semantic result, the dependency
graph is acyclic and memoized, a failed child invalidates its parent, and
canonical pytest #4412 evidence may never terminate in synthetic replay data. A
new field on a replayed production model becomes a new uncovered leaf and fails
closed.

Retained artifact identity therefore terminates twice over: each retained
`ExactArtifactIdentity` inside the canonical run binds to the artifact replay
that hashes and measures the real file, while the acquisition record's own
`/artifacts` metadata corroborates the same digest, byte length, scope, and
request ordinal.

A vector may name more than one bounded authority. Every pointer must be used
by a projection or a derivation, no fact may be projected out of two different
authorities, and each pointer's logical authority, path, and digest must
resolve together through the manifest registry, so a mistyped or unrelated
authority is rejected even when its path, digest, and projections are otherwise
valid. Publication provenance is projected from the `S1.P00` phase-closure
slice ledger, the acquisition run from the acquisition record, and the
correction and completeness facts from the `S1.P00.S04.C01` addendum. Every
vector rationale reference must resolve through the same registry.

Canonical publication ordering is bound to bounded evidence rather than to
authored identifiers. The executor reads each publication's
`subject_record.sha256` from the validated envelope in component order and
compares it against the subject digests the `S1.P00` slice ledger records in
its own array order. Reversing the canonical publications, even together with
every authored publication identifier, is therefore rejected.

`manifest.originating_publications` records the `S1.P03.S01`-`S1.P03.S07`
publication chain. No tracked publication evidence for those Slices exists yet,
so the corpus does not claim source-backed provenance for them: the section
declares `tracked_evidence_available` false and names `S1.P03.S09` as the
verification owner, while its eight records are structurally validated for
exact pull-request ordering, 40-character lowercase Git identity lexemes,
reviewed-tree and squash-tree equality, distinct reviewed and squash revisions,
unique identities, complete `S01`-`S07` product coverage, and exactly one
test-only corrective publication.

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

Completeness is bounded to one declared scope. `EvidenceCompletenessStatus` is
derived only from the outcomes inside that scope, so `scope_satisfied` is never
promoted into a claim about evidence outside it. The corpus therefore states no
universality fact at all rather than inferring one from a scope status.

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
