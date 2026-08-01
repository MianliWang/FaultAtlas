# Revision and Locator Contract Corpus v1

> Internal, non-public, case-calibrated, source-repository-only contract corpus. It is not a public API, production wire format, or persistence schema.

`manifest.json` SHA-256: `56ba607a098744800ae94448982a0a3bab91fb4e7fba445a31406e2478dc1b80`

## Scope and authority

Version `1` locks the already-implemented S1.P02.S01-S05 revision and bounded-locator behavior for all 23 `faultatlas.domain.revision` exports. JSON is authoritative; this Markdown is derived and non-authoritative.

Covered production symbols: `GitHashAlgorithm`, `GitObjectKind`, `GitCommitIdentity`, `GitTreeIdentity`, `GitBlobIdentity`, `GitObjectIdentity`, `GitRevisionIdentity`, `RevisionRole`, `RevisionRoleAssignment`, `GitCommitParentTopology`, `GitRefNamespace`, `GitRefName`, `GitRefObservation`, `GitRepositoryPath`, `RevisionQualifiedPath`, `TextEncoding`, `LineEnding`, `OneBasedInclusiveLineSpan`, `ZeroBasedHalfOpenByteSpan`, `RevisionLineLocator`, `ArtifactByteLocator`, `DiffHunkLocator`, `BoundedLocator`.

## Vector summaries

Valid vectors: `97` across `{"commit-topology": 7, "coordinate-span": 6, "enum": 5, "git-object-identity": 13, "git-object-union": 4, "locator": 16, "locator-union": 3, "mutable-ref": 17, "revision-qualified-path": 20, "revision-role": 6}`. Invalid vectors: `121` across `{"commit-topology": 10, "coordinate-span": 15, "enum": 5, "git-object-identity": 14, "git-object-union": 4, "locator": 20, "locator-union": 4, "mutable-ref": 22, "revision-qualified-path": 20, "revision-role": 7}`. Replay vectors: `10` across `{"artifact-parent": 1, "byte-fact": 3, "hunk-derivation": 3, "reviewed-line-interpretation": 3}`.

Valid vectors preserve exact runtime types, semantic JSON-compatible dumps, and declared round-trip equality. Invalid vectors lock strict rejection without normalization or coercion. Replay vectors keep direct byte facts, deterministic hunk derivations, and reviewed applicable-line interpretations separate.

## Coordinate and path boundaries

Logical lines are one-based inclusive nonempty spans. Artifact bytes are zero-based half-open nonempty spans. UTF-8 and LF/CRLF are explicit. Repository paths preserve exact case and Unicode lexemes inside the bounded UTF-8 textual subset; non-UTF-8 Git path bytes are unsupported.

## Ref, topology, and replay boundaries

Git object kind, hash algorithm, and full digest remain intrinsic identity. Revision roles, ordered parent topology, and immutable time-qualified mutable-ref observations remain separate records. The retained 1640-byte diff is replayed by SHA-256 `dca87a4df1edb2d1acb3fc821724483ee874c2feba6525b2c21e79cb3e8f7312`; no provider, Git, filesystem, or network lookup is performed by production code.

## Strict execution and package boundary

The tracked executor uses an explicit safe registry and file-local acyclic fixtures. Corpus strings cannot trigger import, attribute traversal, `eval`, `exec`, or plugins. The corpus adds no production reader, writer, validator, locator resolver, applicability model, review model, persistence, migration, or public export. Every corpus file is excluded from wheel, sdist, and installed resources.

## Unsupported and correction rule

Tag objects, symbolic refs, non-UTF-8 paths, path existence, entry kinds, ancestry, columns, empty spans, zero-length byte selections, bare/mixed CR, locator resolution, Evidence Envelope, and S1.P02 Phase closure remain unsupported or deferred. After squash merge, reviewed-tree equality, and natural main CI, v1 is immutable; future correction requires a new version or append-only correction layer.

Derived, non-authoritative Markdown; the canonical JSON files remain the sole contract authority.
