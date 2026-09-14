# S1.P08.S03 — Selected-file CLI contract

This Slice adds `faultatlas assessment inspect INPUT` and
`faultatlas assessment save-as INPUT OUTPUT` over the unchanged public
[S02 file API](s1-p08-s02-assessment-file.md). The
[S01 supplied model and pure inspection](s1-p08-s01-supplied-assessment.md)
remain the semantic owners. `python -m faultatlas` has equivalent behavior.
There are still 28 production modules, twelve UUID-root identities and the
unchanged five-module/eight-export P07 surface. Only existing `cli.py` changes
in production. S04 integration and Phase closure are a separate gate.

## A complete synthetic example

All identities below, including repository `1001`, the pattern UUID, target
commit, host and visibility, are example declarations, not observed repository
facts. No target run, evidence fetch, applicability verdict or repair validation
is represented. The immutable target is a full SHA-1 commit declaration.
Root and opinion attributions record supplied claims, not authentication.

```json
{
  "format": "faultatlas-supplied-assessment",
  "version": 1,
  "assessment": {
    "attribution": {
      "supplier": "Example author",
      "rationale": "Synthetic input for a structural review."
    },
    "basis": {
      "source": {
        "pattern": "00000000-0000-4000-8000-000000000001",
        "pattern_statement": "Repeated evaluation may repeat a side effect."
      },
      "target": {
        "snapshot": {
          "repository": {
            "provider": "github",
            "provider_repository_id": "1001"
          },
          "revision": {
            "kind": "commit",
            "algorithm": "sha1",
            "full_digest": "1111111111111111111111111111111111111111"
          }
        },
        "declared_host": "github.com",
        "declared_visibility": "public"
      },
      "conditions": [
        {
          "key": "once",
          "statement": "A side-effecting expression is evaluated no more than once."
        }
      ]
    },
    "opinions": [
      {
        "key": "op-a",
        "condition": {
          "key": "once",
          "statement": "A side-effecting expression is evaluated no more than once."
        },
        "position": "unknown",
        "statement": "No target run or inspected target material was supplied.",
        "attribution": {
          "supplier": "Reviewer A",
          "rationale": "The evaluation count cannot be established from this file."
        }
      }
    ]
  }
}
```

Prepare that literal JSON yourself in a private existing directory, for example
`/home/alice/assessment-demo/input.json`, with input mode 0600. These are example
absolute paths: the directory does not exist merely because it is shown here.
The CLI creates neither parents nor input templates. Use a current-user-owned,
non-group/world-writable directory and input satisfying S02's descriptor and
ancestor checks, on actually observed supported Linux/ext4. A WSL label or path
spelling is not proof of ext4. Unsupported platforms fail through S02.
After installing the package, choose two unused names:

```bash
faultatlas assessment inspect "/home/alice/assessment-demo/input.json"
faultatlas assessment save-as "/home/alice/assessment-demo/input.json" "/home/alice/assessment-demo/saved.json"
faultatlas assessment inspect "/home/alice/assessment-demo/saved.json"
faultatlas assessment save-as "/home/alice/assessment-demo/saved.json" "/home/alice/assessment-demo/resaved.json"
python -m faultatlas assessment inspect "/home/alice/assessment-demo/resaved.json"
```

The first and reopened inspection preserve the complete supplied structure and
attribution. Stdout is inspection text, not a JSON assessment file. The selected
saved file is canonical v1 JSON with owning defaults and mode 0600; saving it
again yields the same bytes. The input content and stable metadata remain
unchanged (reads may update atime). Reusing `saved.json` returns
`DESTINATION_EXISTS` on stderr with exit 1 and leaves that existing file alone.
`not_published` describes this operation, not the absence of a collision file.

## Grammar and transport

Root/group no arguments and all ordinary help return 0. Root `--version` is
eager and emits exactly `0.1.0` and one LF. Help, version and parsing errors do
not invoke S02 or install handlers. Missing/extra arguments and unknown options
emit the fixed safe `CLI_USAGE` diagnostic on stderr with exit 2; supplied tokens
are not echoed. Positional selections are strings. No CLI pre-open, path
normalization, existence/type check, overwrite precheck or parent creation occurs.
Each inspect/save invokes exactly its one public S02 operation, with no implicit
inspect, reopen, retry, lookup or codec. Relative selections and literal `-`
reach S02 unchanged and return `INVALID_PATH`, exit 1. There is no stdin protocol,
force flag, prompt, automatic name, environment/tilde/glob expansion or URL fetch.

For actual Unix argv, the CLI recovers original bytes with `os.fsencode` and
decodes strict UTF-8. This preserves UTF-8 filenames even with ASCII filesystem
encoding; invalid bytes return `CLI_ARGUMENT_ENCODING`, exit 2 before file work.
Explicit in-process argument strings have their own boundary and pass unchanged.
No locale change or replacement decoding is a transport fix. The mechanism is
explained by [Python sys.argv](https://docs.python.org/3.13/library/sys.html#sys.argv);
locked runtime and actual subprocess tests supply execution evidence.

## Plain output and truthful effects

Inspect emits the complete S02 view unchanged, adding one LF only if missing.
It ends at `End of complete view`; no markup/Rich interpretation, wrapping,
truncation or added verdict occurs. The 8 MiB admission remains S02-owned.
Successful stderr is empty. Save success emits exactly:

```text
Saved new assessment file: "/home/alice/assessment-demo/saved.json"
output_visibility=published; sync_completed=true
```

Each line has one LF. The actual selected path is recoverable ASCII JSON string
escaping, including DEL as `\u007f`. Controls, bidi and markup remain data. This
reports the settled file operation, not future filesystem state or empirical truth.

Expected `AssessmentFileError` text is emitted unchanged plus one LF on stderr.
Typed attributes govern behavior; diagnostics are never parsed for authority.
The finite CLI vocabulary is `CLI_USAGE`, `CLI_ARGUMENT_ENCODING`,
`CLI_SIGNAL_SETUP`, `CLI_SIGNAL_RESTORE`, `CLI_OUTPUT`, `CLI_CANCELLED` and
`CLI_INTERNAL`. These fixed safe lines report known visibility, synchronization
and cancellation; the bounded CLI diagnostic is at most 16 KiB plus LF, and a
service diagnostic plus short annotations is at most 16 KiB plus 512 bytes.
Unknown internal failure reports uncertain visibility and unestablished sync
unless a returned result or structured error already established the effects.
No traceback, exception payload or locals are printed.

A `KeyboardInterrupt` reaching the top-level runner before scoped signal handling
also uses `CLI_INTERNAL`, exit 1, with unestablished effects. It is not reported
as cooperative cancellation: no supported signal was latched by this command.
This bounded fallback does not promise arbitrary asynchronous-exception recovery.

| Exit | Result |
| ---: | --- |
| 0 | Successful command/help/version, including write and flush |
| 2 | Parser or raw UTF-8 argument transport rejection before S02 |
| 1 | Non-cancellation S02 failure, setup/restore/delivery/internal failure |
| 130 | Pure cooperative cancellation from observed SIGINT |
| 143 | Pure cooperative cancellation from observed SIGTERM |

For example, malformed JSON returns S02 `INVALID_JSON`, exit 1; unsupported
version returns `UNSUPPORTED_VERSION`, exit 1. Cancellation without an observed
signal is not invented as SIGINT. I/O, sync, close and callback errors retain
exit 1 even when cancellation is also observed. Pure cancellation can report
published and sync completed. No success receipt follows failure or cancellation
observed at the completion cutoff.

Delivery is separate from publication. Actual process standard streams use
explicit bounded descriptor writes and flush acknowledgment, avoiding a buffered
EPIPE payload at interpreter shutdown. In-process replacement streams use checked
write/flush without replacing global streams. Failure is exit 1; a failed stdout
gets one bounded stderr diagnostic where possible, a failed stderr is not retried.
There is no null sink, descriptor leak, retry save, rollback or destination probe.
A saved file remains complete even if its receipt pipe breaks. Partial delivery,
downstream acknowledgment, atomic stdout, stdout-file fsync and the caller's shell
redirections are outside the guarantee. [Python streams](https://docs.python.org/3.13/library/sys.html#sys.stdout)
and [Typer printing](https://typer.tiangolo.com/tutorial/printing/) explain the
mechanisms; real closed-reader and injected write/flush cases test this boundary.

## Cooperative signals

Actual assessment commands require main-thread SIGINT/SIGTERM setup before S02.
Prior handlers are preserved, partial setup is restored, and unsupported setup
returns `CLI_SIGNAL_SETUP`, exit 1 without file work. The handler only latches the
first supported signal; the trusted callback returns an exact bool. It does no
I/O, cleanup, raising or locking. Repeated signals are not forced interruption.
S02 settles publication, sync and cleanup before the CLI decides its response.

The cutoff is the final explicit signal-state sample after S02 settles and before
response selection. A late observed signal after S02's last callback is a CLI
observation: `CLI_CANCELLED` retains known returned save effects without a success
receipt. Service errors remain intact; a short CLI annotation records a new
cancellation fact when needed. All installed handlers are restored; restoration
failure adds `CLI_SIGNAL_RESTORE`, preserves a primary error and forces exit 1.
Sequential invocations keep no handler or cancellation state. Arrivals after the
cutoff do not retroactively change the result. This is cooperative cancellation,
not a hard deadline, interruptible-everywhere I/O, arbitrary asynchronous exception,
SIGKILL or power-loss guarantee. See [Python signals](https://docs.python.org/3.13/library/signal.html).
No product worker, watchdog or wakeup-fd infrastructure is added.

## Evidence ownership and preservation

`tests/test_assessment_cli.py` owns the literal-document installed-console
inspect/save/reopen/resave workflow, canonical bytes, provenance, stable input
metadata, real ext4, actual ASCII-locale UTF-8 argv, invalid bytes and broken pipe.
An explicitly instrumented installed test wrapper coordinates real SIGINT/SIGTERM
with pipes around actual S02 publication; it is separate from the uninstrumented
workflow. Mapping/fault injection tests establish CLI presentation and precedence,
not real file publication. S01/S02 tests retain their semantic/filesystem matrix.
Existing package tests still own full archive inventory and source byte equality.

The nine named historical readers (six initial readers plus the three SCOPE-01
closure readers) retain their seed CLI digest/length observations
and every other path's exact checks. Only their assumption that current CLI bytes
must remain the seed is retired, delegating current source accountability to
`tests/test_cli.py`, behavior to the CLI owners and package bytes to the existing
package owner. Per-reader controls admit a harmless current-CLI comment and reject
an altered `__main__.py`. The four additional closure entry points independently
accept valid/commented CLI bytes and reject a renamed CLI route; both fault-instance
validators are exercised separately so one rejection cannot mask the other.
No unavailable historical Git bytes are inferred from
retained digest text, and shallow offline CI needs no old Git objects.

O01–O15 source-qualified owners, original states/consequences/decision points,
private/GHE/provider/non-Git limits and P07 empirical-generality disposition are
unchanged. CLI success resolves none of those unknowns. P08 remains incomplete;
P09/P10 remain not started. The selected workflow adds no ingestion, general
persistence, automatic applicability, target override or analyzed-code execution.
