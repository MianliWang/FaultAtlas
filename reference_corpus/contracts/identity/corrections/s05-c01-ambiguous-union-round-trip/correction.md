# S1.P01.S05.C01 identity contract correction

> Internal, case-calibrated, non-public correction. The JSON records are authoritative; this Markdown is derived and non-authoritative.

Correction ID: `s1-p01-s05-c01-ambiguous-union-round-trip`
Correction JSON SHA-256: `c17edfa5dc227850d6b982d1ec8c83b4236cd403bb7ca1b1c66b662f8657347a`
Regression vectors SHA-256: `721b6a97a7b80dcc1d33643f6920b21d2e2a8b010d8528f8d194a6691a3feff2`

## Confirmed defect

Direct semantic JSON round trips through `IdentityValueState[ProviderGlobalId | ProviderNodeId]` and `IdentityValueState[RepositoryScopedNumber | ProviderGlobalId]` could restore the first scalar-root union member, changing wrapper type and equality. Same-lexeme conflicts could collapse before conflict validation.

## Selected hybrid resolution

Ambiguous scalar-root generic specializations now fail with the controlled domain-discriminator rule. Monomorphic scalar states and distinguishable structured `SourceIdentity` unions remain supported. Legacy compatibility uses `LegacyObjectIdInterpretation` plus a private carrier to preserve repository-number, provider-global, and unresolved ordered types without guessing, conversion, alternate-ID equivalence, or a winner.

## Contract replacement

The immutable v1 vector `identity.valid.field-state.conflict-number-global` is historically retained and explicitly superseded for current execution by `identity.correction.s05-c01.generic-rejection.number-global.conflict-distinct-json`. The other 167 v1 vectors remain active, and all 32 correction vectors execute, for 199 effective vectors.

## Assurance corrections

Current whole-source assurance covers the exact seven production Python files in the working tree, wheel, and sdist, including byte equality and unexpected/missing/mismatch mutations. It is separate from the historical v1 no-reader assertion.

Current permission assurance separately requires Git index mode `100644` and regular filesystem mode `0644` in the supported WSL/CI environment for the exact correction inventory, with executable, restrictive, symlink, special-file, and Git-mode mutations.

## Historical review settlement

After protected squash publication and exact natural-main CI, the one PR #19 ambiguity thread and the two PR #21 assurance threads will receive evidence-backed replies and be resolved.

## Publication conditions

The correction remains `sealed_publication_candidate` until ready-PR validation, review settlement, squash-tree equality, natural main CI, clean synchronization, and historical-thread settlement complete. `S1.P01.S06` remains next and not started.

## Immutability

All nine S05 v1 files remain byte-for-byte immutable. This correction directory is append-only and contains no mutable `latest`, `current`, symlink, or pointer artifact.
