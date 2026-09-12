# Validation ownership and build reuse

E01 is engineering maintenance. P06 remains complete; P07 remains active, with
S01–S05 complete and S06 next/not_started. It changes neither product semantics
nor the retained reference corpus. Publication remains subject to the protected
pull-request and natural-main checks below.

## Owners

| Obligation | Owner | Retained domain responsibility |
| --- | --- | --- |
| Expected current production paths and named current surfaces | `tests/_repository_contract.py` | Historical inventories, digests and publication facts stay with their historical contracts. |
| Independent tracked/source inventory, the roadmap's current source count, complete wheel/sdist inventory, source bytes, safe paths, duplicate/type checks, exclusions and licenses | `tests/test_package.py` | Existing corpus mutation cases delegate whole-source comparisons to this owner and retain their specific safety/metadata checks. Domain Current-code mapping symbol/field assertions remain local. |
| Mutable active/next/completed lifecycle and route state | `tests/test_roadmap_lifecycle_consistency.py` | Bounded product prose, historical transitions and correction obligations remain local. A correction summary delegates its bounded current gate check. |
| Normal offline distribution preparation | `tests/conftest.py` | Every existing installed-wheel semantic probe retains its own installation and out-of-checkout provenance check. |

The expected production names are manually authored, not discovered from the
checkout, archives or production exports. Dependency checks use the full intended
population but retain their explicit permitted consumers and forbidden directions.
Sharing inventory data grants no import permission. In particular, the S02
interpretation-import witness, S04's exact expected-property consumption, and
S01/S03 independence remain enforced.

## Build lifetime and isolation

One lazy session fixture builds the normal wheel/sdist pair in a serial pytest
process. Each consumer rechecks source/configuration bytes, relevant environment
and artifact digests. Changed inputs or artifacts fail explicitly; a new process
gets fresh preparation. No AST, mutable JSON value, assertion result or installed
environment is cached. Tests that mutate archives use private copies, or restore
the shared test artifact in `finally` while proving rejection and restoration.

Two pre-existing profiles remain isolated: the evidence-phase closure's managed
Python/inherited-cache build, and the revision-locator closure's sanitized
CONDA/PYTHON environment, managed Python, private cache and default gitignore
behavior. Their different inputs are not silently folded into the normal profile.
The normal profile's no-sync/no-bytecode flags control development preparation;
archive inventory and byte checks still inspect the actual built artifacts.

The shared preparation also checks that building changes neither repository
files nor Git status. A focused test that does not request distributions performs
no build. Support imports and fixtures use the standard direct-file pytest
invocation; no interpreter or package configuration changes are required.

## Procedure and evidence reuse

1. During edits, run direct-file focused tests for changed owners and their
   callers, including the intended negative witness. Check the actual assertion,
   not an incidental setup or model-validation error.
2. On a stable candidate, run `uv lock --check`,
   `uv run --frozen ruff format --check .`, `uv run --frozen ruff check .`,
   `uv run --frozen pyright`, `uv run --frozen pytest --durations=30`,
   `uv build --offline`, and `git diff --check`; retain direct exit codes.
3. Inspect the exact wheel/sdist inventories and source bytes, and perform a real
   local uv wheel installation outside the checkout. Preserve provenance and
   authored P07 semantic JSON reconstruction, not just import success.
4. Reuse completed evidence only when the relevant code, test harness,
   environment, inputs and Git/lifecycle context match. Unchanged production
   bytes alone do not validate a new harness. Revalidate affected evidence after
   a change; the candidate full run also supplies its measurement.
5. Independently review the candidate within the E01 limit of three substantive
   rounds and two review-driven repair cycles. Bind the final reviewed head to
   the PR. Required PR CI and natural-main CI are separate evidence: verify event,
   attempt, actual checkout SHA, merge parents when applicable, and reviewed /
   tested / squash tree equality. Then synchronize ff-only and clean only proven
   disposable task resources.

Development execution stays offline, with the unchanged locked toolchain and
credential-free subprocess environments. E01's temporary measurement copies use
a read-only host filesystem plus a writable task root and a separate network
namespace. A clone alone is workspace isolation, not OS containment. Historical
external repository material remains data and is never executed.

## Transfer ledger and measurement

The frozen E01 scope is 53 paths: 48 existing tests, `docs/roadmap.md`, and four
test-support/documentation additions. The task-local JSON ledger records old
obligations, replacement owners, reasons and witnesses per file; collection
reconciliation retains the exact removed/replaced node IDs. Pure duplicate
archive/lifecycle tests are consolidated; mixed tests retain their distinct
product, historical and retained-evidence cases. Test counts are neither a floor
nor an optimization target.

The isolated baseline at `ff0908012bf34631342133e4e5a5713ba1fe234d` collected and
passed 11,160 tests. Separate collection took 8.44 seconds; the complete pytest
command took 61.20 seconds (including collection and setup), and transparent uv
observation recorded 25 build invocations. Python was 3.13.13 and uv 0.11.19;
dependencies were installed from the existing offline cache. These are local
measurements, not CI timings or a promised speedup.
All 25 retained baseline wheels were byte-identical, as were all 25 sdists.

Candidate timings, reconciled counts, observed normal versus isolated builds,
and the two disposable maintenance rehearsals are recorded in the E01 task
receipt. The rehearsals introduce one harmless module and one synthetic
lifecycle advance, record the exact bookkeeping edits, and never alter the
publishable candidate or imply S06 implementation.
The module rehearsal passed 106 focused cases after editing the temporary
module, the single expected inventory and the roadmap's observed source-count
claim. The lifecycle rehearsal passed 184 cases after editing only its owner and
the necessary roadmap claims. Neither required edits to unrelated domain tests.

Remaining profiling opportunities include the development-history manifest
consumer sweep and large composition-boundary cases. E01 does not add global
source/AST/JSON caches, parallel test execution, an evidence scheduler, or timing
thresholds to tests.
