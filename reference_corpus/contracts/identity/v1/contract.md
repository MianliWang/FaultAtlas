# FaultAtlas Identity Contract Corpus v1

> Internal, case-calibrated, non-public contract material. This is not a production persistence format or public API.

## Manifest lock

The exact `manifest.json` SHA-256 is `aafa6dee23971218f30f9c72f63e23741841f0852299bebf9f40471054cb760a`.

## Version and scope

This source-repository-only corpus is version `v1`, originates in `S1.P01.S05`, and locks current `S1.P01.S01` through `S1.P01.S04` identity and compatibility behavior. It is informed by pytest Issue `#4412` without generalizing to a universal provider contract.

## Covered production symbols

The manifest inventories all 17 module-local exports from `faultatlas.domain.identity`, all 7 module-local exports from `faultatlas.domain.compatibility`, and the legacy `SourceLocator` compatibility target. No package-root export is added.

## Valid vectors

There are 58 locked valid vectors across: `enum` (4), `field-state` (16), `identifier` (10), `lifecycle` (6), `provider` (3), `repository` (8), `source-identity` (3), `source-object` (8). They preserve strict typed construction, all current source identities, all seven absence states, ordered unresolved conflicts, lifecycle observations, and semantic JSON round trips.

## Invalid vectors

There are 80 locked invalid vectors across: `authority-host` (12), `global-and-node-id` (10), `identity-state` (12), `lifecycle` (10), `provider-key` (9), `repository-and-alias` (11), `repository-scoped-number` (8), `source-object` (8). Python and JSON input modes remain distinct, and invalid values are rejected without coercion.

## Compatibility vectors

There are 30 locked compatibility vectors across: `enum` (3), `legacy-mapping` (9), `legacy-projection` (8), `result-model-rejection` (10). Legacy mapping and typed projection retain exact statuses, ordered reasons, explicit basis, unresolved candidate order, and absence of a fabricated winner.

## Strictness and loss

The corpus locks strict Pydantic semantic behavior, not Pydantic's bytes as a durable production format. Legacy projection is explicitly lossy: stable repository identity, alias authority, alias observation time, and schema version cannot be represented by `SourceLocator`. Conflict and absence are valid outcomes; no heuristic resolves them.

## Package and execution boundary

The complete directory is excluded from wheel and sdist. Corpus execution uses a safe explicit registry under tests only, requires no network, and permits no `eval`, `exec`, dynamic import, arbitrary attribute traversal, or plugin loading. No production corpus reader or validator exists.

## Deferred and unsupported concepts

Actor identity, alternate-ID binding, conflict resolution, Git identity, ref observations, revision-qualified paths, locators, Evidence Envelope, persistence, migrations, public APIs, and `S1.P01.S06` implementation remain unsupported and deferred.

## Publication and future versions

This version is a publication candidate until protected squash merge and natural main CI succeed. After publication it is immutable. Corrections require a new version or explicit append-only correction layer; future version/registry ownership remains `S1.P10`.

## Authority

This Markdown is derived and non-authoritative. `manifest.json` and the three vector JSON files are the semantic authorities.
