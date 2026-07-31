# pytest #4412 Snapshot Boundary and Compatibility Decision

## 1. Scope and Authority Warning

This internal, case-calibrated S1.P00.S08 decision is not a production schema, class, adapter, reader, writer, migration, persistence contract, or public API. `decision.json` is the sole durable semantic authority; this Markdown is derived.

## 2. Exact `decision.json` SHA-256

`f788116f3b9ea470c370a56e55eb6f37e05be200f285ac9f2572c641215f5f40`

## 3. Executive Decision

Select `preserve_v1_behind_outer_wrapper`. Legacy `ArtifactSnapshot` v1 remains unchanged; a future evidence boundary composes around it without inheritance or silent field expansion.

## 4. Current `ArtifactSnapshot` Boundary

The current internal, provisional v1 model is one Issue-bound observation: UTF-8 text, fixed `application/json`, at most 1,048,576 encoded bytes, an exact-UTF-8-payload SHA-256, an exact-zero-offset UTC timestamp, and required nullable limitation fields under strict/frozen validation. It does not carry arbitrary bytes, exact diff or LICENSE identity, transport/acquisition provenance, structured completeness, transformations, corrections, relationships, review, migration, or publication provenance.

## 5. Preserve-v1-Behind-Outer-Wrapper Strategy

In-place evolution and immediate replacement are rejected for now. Composition minimizes breakage while preventing the generic snapshot name from acquiring semantics absent from current code and tests.

## 6. Representation Versus Exact-Artifact Boundary

Source identity, retrieval request, representation observation, normalized metadata, retained exact artifact, transformation, correction/supersession, case interpretation, and publication provenance remain distinct. Exact artifacts support arbitrary bytes without a UTF-8 or JSON requirement; media type does not define byte identity; every digest declares scope.

## 7. Legacy-to-Future Mapping

Mapping is explicit, versioned, loss-aware, source-preserving, and adapter-versioned. It may preserve all legacy fields and the exact legacy representation used by the adapter, but must not fabricate identity, transport, pagination, completeness, omission, exact-provider-byte, transformation, review, confidence, or publication facts.

## 8. Future-to-Legacy Projection Limits

Projection is non-default and permitted only for one compatible Issue locator, one size-bounded UTF-8 JSON text representation, the required UTC timestamp and digest behavior, and valid limitation state. Otherwise it returns a typed unsupported or incompatible result; diff and LICENSE bytes are never coerced into v1.

## 9. Compatibility Statuses

The controlled statuses are: `native`, `losslessly_mappable`, `partially_mappable`, `not_mappable`, `unsupported_version`, and `conflict`. Partial mapping is never full compatibility.

## 10. Versioning

Each independently persisted contract has its own format name and explicit version, plus canonicalization when byte identity matters. There is no global Fault Atlas schema version. Exact version wire syntax and registry implementation remain provisional for S1.P10.

## 11. Canonicalization

In-memory equality, ordinary Pydantic JSON serialization, canonical durable record bytes, retained artifact bytes, and digest scope are distinct. Current semantic round trips are not declared durable byte-canonical. Exact artifacts are not recanonicalized.

## 12. Reader and Writer Behavior

Readers are format- and version-aware, strict, structured on failure, and never silently fall back or coerce. Writers emit exactly one declared format/version, never silently upgrade or overwrite immutable records, and claim canonical bytes only after applying the declared canonicalizer.

## 13. Migration Versus Correction Versus Supersession

Migration translates versions; correction addresses a defect; supersession states scoped precedence. All are explicit and provenance-bearing, and published immutable sources remain accessible. Migration and correction produce append-only records rather than rewriting history.

## 14. Backward-Compatibility Commitment

Through S1.P00, current v1 behavior and tests remain authoritative, no payload is silently reinterpreted, no broader public promise is created, and no new consumer should depend on broader semantics. Breaking change requires the S1.P10 reader, mapping, migration, corpus, fixture, and unsupported-behavior prerequisites.

## 15. S09 and S10 Handoff

S09 tests the decision and corpus deterministically without implementing a future model. S10 verifies the complete P00 chain, immutable inputs, explicit deferrals, and Stage 1 entry prerequisites. Both remain not started.

## 16. S1.P03/P04/P09/P10 Handoff

S1.P03 owns future outer evidence semantics; S1.P04 owns repository snapshot aggregation; S1.P09 owns claim, confidence, review, and extended supersession semantics; S1.P10 owns production serialization, readers, writers, migrations, registry, corpus, and persistence-neutral compatibility.

## 17. Locked, Provisional, and Unknown Summary

The register contains 16 locked decisions, 8 provisional details, and 4 unknown questions. No unresolved item is hidden in prose; owners and implementation deferrals are explicit in JSON.

## 18. No Production Model Changed

No production model, export, adapter, reader, writer, migration, dependency, CI surface, public API, or S09 artifact changed. S1.P03 implementation has not begun.

## 19. Not a Universal Production Schema

This decision is calibrated to the locked pytest #4412 evidence and current FaultAtlas code. It does not generalize to private, enterprise, non-Git, non-GitHub, arbitrary-history, or universal storage contracts.
