# S1.P08.S02 — Selected assessment files, save-as-new and reopen

This Slice adds a bounded local-file workflow over the published
[S01 supplied assessment and pure inspection](s1-p08-s01-supplied-assessment.md).
It does not change that value contract. The caller explicitly selects an input
file and, for saving, one new output name. File round trips establish structural
and representation properties, not applicability, authenticated authorship,
provider support, target-repository existence or empirical transfer.

## Public API

`faultatlas.assessment_file.__all__` is exactly:

```python
["AssessmentFileError", "inspect_assessment_file", "save_assessment_as_new"]
```

```python
def inspect_assessment_file(
    input_path: str, *, cancelled: Callable[[], bool] | None = None
) -> str: ...

def save_assessment_as_new(
    input_path: str,
    output_path: str,
    *,
    cancelled: Callable[[], bool] | None = None,
) -> str: ...
```

Inspection returns a complete string. Save returns the exact selected output
string only after publication, required synchronization, binding checks and
successful descriptor cleanup. Neither function prints, exits, allocates a new
name, overwrites a destination, or reads a material locator. There is no target
override, discovery, catalog, stdin protocol, cross-file lookup or draft state.
The new module consumes the public S01 model and inspector; it exposes no codec
helper or package-initializer re-export. Production modules increase to 28;
the 12 UUID-root identities, P07 five modules/eight exports and S01 nine domain
records/one pure inspector remain unchanged.

For an existing valid input in a caller-owned private directory on supported
ext4, a library caller can use:

```python
from faultatlas.assessment_file import inspect_assessment_file, save_assessment_as_new

before = inspect_assessment_file("/absolute/private/input.json")
selected = save_assessment_as_new(
    "/absolute/private/input.json", "/absolute/private/new-assessment.json"
)
after = inspect_assessment_file(selected)
```

The caller chooses these literal paths. The example does not create the input
directory or claim those placeholder names exist. S03 owns CLI commands and
signal handling; the existing help/version CLI is unchanged.

## v1 file meaning and admission

Exactly one JSON object has exactly `format`, `version` and `assessment` keys.
The format is `faultatlas-supplied-assessment`; version is the exact integer 1.
The assessment is one valid full S01 value. For example, this sparse inner
representation has all required fields and no invented FaultInstance:

```json
{"format":"faultatlas-supplied-assessment","version":1,"assessment":{"attribution":{"supplier":"Example author","rationale":"An explicitly supplied structural example."},"basis":{"source":{"pattern":"00000000-0000-4000-8000-000000000001","pattern_statement":"Repeated evaluation may repeat a side effect."},"target":{"snapshot":{"repository":{"provider":"github","provider_repository_id":"1001"},"revision":{"kind":"commit","algorithm":"sha1","full_digest":"1111111111111111111111111111111111111111"}},"declared_host":"github.com","declared_visibility":"public"}}}}
```

Original bytes, decoded primitives, validated domain value and canonical output
are distinct layers. Whitespace, object-key order, escape spelling, omitted
defaults and owner-normalized identity spelling may change during save. Every
admitted prose/locator code point, attribution, optional-state distinction,
explicit conflict and array order survives. The original file is not rewritten;
save-as-new is not a raw-byte archive or signature check.

The single intake path reads in bounded blocks, at most 1,048,577 bytes, to
distinguish the 1,048,576-byte cap from one-over input. A size check can reject
early, but accepted inputs still undergo bounded reading. Strict UTF-8 is
required and a UTF-8 BOM is explicitly rejected. No UTF-16/32 autodetection,
replacement decoding or BOM stripping is used. A byte sequence that is valid
UTF-8 but not valid JSON is a JSON failure, without guessed alternate encoding.

A string/escape-aware scan rejects nesting beyond 33 containers before recursive
JSON decoding. It does not replace the JSON parser. The standard decoder rejects
malformed/empty/multiple documents and trailing non-whitespace. S02 supplies
hooks for duplicate decoded keys at every object, all float/exponent tokens,
nonfinite constants, and integer tokens longer than 20 characters or outside
signed 64-bit range. Decoded keys and values must also be strict UTF-8 encodable,
so escaped lone surrogates fail. These are S02 restrictions: Python JSON defaults
are broader, including duplicate-name and nonfinite handling.
[Python JSON documentation](https://docs.python.org/3.13/library/json.html)
describes the decoder hooks and default behavior.

| Counting domain | Nodes | Objects | String code points, including keys | Container levels |
| --- | ---: | ---: | ---: | ---: |
| Each S01 normalized basis/assessment root | 8192 | 512 | 131072 | 32 |
| Raw and complete normalized S02 envelope | 8198 | 513 | 131125 | 33 |
| Exact envelope overhead above the assessment | 6 | 1 | 53 | 1 |

Each dict/list/scalar occurrence is a node; each dict key is another string
node, and each dict is an object. Root containers have depth 1; scalar leaves
add no container depth. References are counted on every occurrence. The raw
envelope is checked before exact shape/version and owning-schema validation.
Unknown keys are refused. Checked inner primitives are re-encoded for
`SuppliedAssessment.model_validate_json` using its published default policy;
strict Python tuple input is not substituted for native JSON.

After owning validation and the S01 pure inspection, the value is projected with
all defaults, unset values and nulls included. The complete envelope uses the
same private scalar/budget checks, including integer readability and float
refusal. Canonical bytes use sorted object keys, compact separators, literal
Unicode (`ensure_ascii=False`), `allow_nan=False`, strict UTF-8 and exactly one
final LF. Arrays are never sorted. The complete encoding must fit 1 MiB before
any output can be published. Shared grammar/limits and the owning projection
provide save/read closure; public operations do not recursively call each other
to verify it. Real tests reopen and resave the published files.

The S01 corrected witness is retained: 32 conditions `c0` through `c31`, first
statement 3116 ASCII characters, remaining 31 statements 4096 each, with the
authored complete sample and no opinions. Its complete body counts 131072 string
code points and envelope 131125. Length 3144 omitted two upstream
`schema_version` keys in the earlier draft arithmetic and is 28 characters over
the real body limit. S02 neither suppresses those defaults nor relaxes the cap.
The tests independently count the authored full shape and actually save/reopen
the exact boundary; a sparse otherwise-valid one-over case reaches the owner
budget failure.

Admission bounds do not prove peak memory, parser CPU or cancellation latency.
A valid upstream value may be refused by this narrower file gateway without
implying an upstream defect.

## Selected paths and supported descriptors

The initial backend requires Linux, observed local ext4 and actual O_PATH,
O_NOFOLLOW, O_DIRECTORY, O_CLOEXEC, O_TMPFILE, descriptor-relative open/link and
fixed proc-fd mechanisms. Imports perform no filesystem probe. A WSL label or
path prefix does not establish support. DrvFS, tmpfs, overlay, network mounts,
native Windows/macOS and other filesystem types are outside this backend.

Paths are explicit absolute Linux strings, strict UTF-8, at most 4096 encoded
bytes and 64 components, with each component 1–255 bytes. Relative paths, root
alone, NUL, repeated/trailing separators, `.` and `..` fail. There is no `~`,
variable, glob, URL or `resolve`/`realpath` expansion. Equal input/output strings
fail before publication.

Validated components and basenames reach open/link/recheck as explicit UTF-8
bytes, independently of Python's filesystem encoding. Selected strings are
retained for return values, error attributes and display. A real subprocess
regression covers Unicode parent/input/output names with filesystem encoding
ASCII and Python UTF-8 mode disabled.

The walk starts at `/`, opening each ancestor separately with held no-follow
directory descriptors. The immediate input/destination parent must belong to
the effective caller UID and must not be writable by group/other; the input file
must belong to that caller. Earlier ancestors such as `/tmp` need not be
caller-owned. Existing permissions are never changed to pass these checks.

The final input is opened first with O_PATH and O_NOFOLLOW, then fstat must show
a regular owned file. Symlinks, directories, FIFOs, sockets and devices are
refused before ordinary reading. Only the held descriptor is reopened through
the fixed `/proc/self/fd/<fd>` route; dev/inode equality is checked. This
controlled proc descriptor exception does not authorize following user symlinks.
[Linux open documentation](https://man7.org/linux/man-pages/man2/open.2.html)
describes O_PATH, O_NOFOLLOW and the proc descriptor mechanisms.

For the input and destination parent separately, bounded `/proc/self/fdinfo`
reads (64 KiB) supply `mnt_id`, matched to the corresponding bounded
`/proc/self/mountinfo` record (1 MiB). Only the required association fields are
parsed; missing, ambiguous, malformed, oversized or non-ext4 associations fail
closed. No answer is cached across descriptors. The association comes from the
kernel formats documented for [fdinfo](https://man7.org/linux/man-pages/man5/proc_pid_fdinfo.5.html)
and [mountinfo](https://man7.org/linux/man-pages/man5/proc_pid_mountinfo.5.html).

The input's dev/inode/size/mtime_ns/ctime_ns are checked after reading and again
before save publication, against both the pin and a fresh no-follow selected
path binding. Inspection makes its final check before returning. Destination
parent/name bindings are also rechecked. Directory identity is compared rather
than directory mtime, which the operation itself changes when publishing.
These checks assume stable caller-controlled files/parents/mount namespace and
no hostile same-UID/root actor. They do not create an atomic snapshot against
arbitrary concurrent rewriting; [stat documentation](https://man7.org/linux/man-pages/man2/stat.2.html)
also cautions about observations under concurrent changes. Ordinary access-time
effects are not claimed absent.

## Publication, synchronization and cancellation

After all intake/output/view checks, create one unnamed file in the held
destination directory with O_TMPFILE|O_RDWR|O_CLOEXEC and mode 0600, then fchmod
that owned descriptor to 0600. O_EXCL is deliberately absent because it would
prevent linking this inode. Bounded writes advance on short progress; zero or
error progress fails. Synchronize the complete file before linking.

After cancellation and input/parent rechecks, attempt exactly one link:

```python
os.link(
    f"/proc/self/fd/{temporary_fd}",
    output_basename,
    dst_dir_fd=parent_fd,
    follow_symlinks=True,
)
```

The documented proc-fd linkat route permits publishing a complete unnamed inode
without a visible partial temporary name. Python's
[descriptor-relative link API](https://docs.python.org/3.13/library/os.html#os.link)
is used with the required directory fd and follow behavior. Existing files,
directories, hardlinks and dangling symlinks are collisions; none is unlinked or
replaced. [Linux link semantics](https://man7.org/linux/man-pages/man2/link.2.html)
provide the no-replacement primitive. A friendly prior existence check is not
used as publication authority.

Successful link is the name-visibility point. Content is never written again.
The linked file and held destination directory are synchronized, then selected
parent/name bindings are checked and owned descriptors are closed. The file and
directory calls are distinct obligations; [fsync documentation](https://man7.org/linux/man-pages/man2/fsync.2.html)
explains why file synchronization alone does not acknowledge its directory entry.
Acknowledgment is not a host power-loss qualification or a guarantee for every
WSL/device stack.

Pre-link errors/cancellation leave this operation's name unpublished. After a
successful or ambiguous publication attempt, output is preserved with no
rollback unlink, move-back, replacement or repeated link. EEXIST is a known
collision. For ambiguous EIO/EINTR, at most one bounded no-follow inode comparison
can establish the created inode under the selected name. Otherwise visibility
remains uncertain. Known successful link history stays published even if the
selected parent/name later changes. Post-link synchronization is attempted where
possible, including directory synchronization after a file-sync error.

Each acquired descriptor is closed once. Ownership is relinquished before close;
no numeric-fd retry can affect a subsequently reused descriptor. Earlier
publication/sync failures take precedence over cleanup failures, while a cleanup
failure cannot become success or disappear behind a cancellation result.
[Linux close documentation](https://man7.org/linux/man-pages/man2/close.2.html)
describes the descriptor reuse hazard.

The optional caller hook is trusted in-memory code, validated for callability
before work. It must return an exact bool; ordinary exceptions/non-bool results
are callback failures. It is sampled at bounded read/write checkpoints, before
publication and at completion. No callback comes from JSON. Cancellation before
link prevents publication. After an attempt, known effects are settled and
required sync/cleanup continue before reporting cancellation. I/O/sync failures
retain their code alongside `cancel_requested=True`; late cancellation can
report a published, synchronized file without returning success. No signal
handler, hard cancellation deadline, SIGKILL recovery or arbitrary async-exception
atomicity is provided.

## Structured failures and display

`AssessmentFileError` derives from Exception and has these required attributes:

| Attribute | Meaning |
| --- | --- |
| `code: str` | One of the finite codes below. |
| `stage: str` | Actual local phase: path/platform/read/decode/validate/inspect/prepare/write/publish/sync/close/cancel. |
| `input_path`, `output_path` | Selected strings or None for absent/unbounded/non-string/non-UTF-8 arguments. Never a material locator. |
| `location` | Bounded structural field/index tuple where available, at most 33 parts with string parts at most 128 characters. Duplicate-key hooks identify the local key; syntax coordinates are diagnostic text, not invented field paths. |
| `output_visibility` | `not_published`, `published` or `uncertain`, describing this operation's creation history. |
| `sync_completed: bool` | Required post-link file and directory calls completed for a known publication. |
| `cancel_requested: bool` | Cancellation was actually observed, independent of the primary error code. |

Codes are `INVALID_ARGUMENT`, `INVALID_PATH`, `UNSUPPORTED_PLATFORM`,
`UNSAFE_INPUT`, `INPUT_CHANGED`, `OUTPUT_PARENT_CHANGED`, `INVALID_ENCODING`,
`INVALID_JSON`, `UNSUPPORTED_FORMAT`, `UNSUPPORTED_VERSION`,
`INVALID_ASSESSMENT`, `RESOURCE_LIMIT`, `DESTINATION_EXISTS`, `IO_ERROR`,
`PUBLICATION_UNCERTAIN`, `PUBLISHED_SYNC_UNCONFIRMED`,
`PUBLISHED_PATH_CHANGED`, `CLOSE_FAILED`, `CANCELLED`, `CANCEL_CHECK_FAILED`.

Malformed/mistyped envelope and unsupported numeric grammar use INVALID_JSON;
otherwise correctly shaped unknown format/version use their specific codes.
Owning field failures preserve the available location and error type as
INVALID_ASSESSMENT; identifiable S01 normalized budget excess is RESOURCE_LIMIT,
as are file/envelope/view bounds. Type/ownership refusals are UNSAFE_INPUT.
Backend capability/mount refusal is UNSUPPORTED_PLATFORM; ordinary permission or
storage errors remain I/O errors. Post-publication sync failure is
PUBLISHED_SYNC_UNCONFIRMED. `not_published` does not assert destination absence:
an untouched collision file may exist. Inspect/prepublication failures cannot
claim synchronization.

`str(error)` is at most 16 KiB UTF-8, with recoverable ASCII JSON escaping and
explicitly abbreviated bounded excerpts. It never dumps input bytes or raw
ValidationError/OSError payloads. Unexpected programming failures remain visible;
anticipated failures neither print nor exit. The complete file view prefixes the
S01 view with escaped selected-path and fixed v1 metadata, keeps S01's final
`End of complete view` marker last, and fits 8 MiB including the prefix. Both input
and proposed output-path views are checked before publication. Unicode, DEL,
controls and bidi characters remain escaped; terminal auto-linking is not under
API control.

## Evidence and boundaries

The task's Python 3.13.13 on Linux WSL2 6.18.33.2 observed actual ext4 descriptors
and completed O_PATH pin/reopen, O_TMPFILE/proc-fd link, mode 0600, both sync stages
and reopen. Current Python 3.13 reference pages identify patch 3.13.15; their
mechanism descriptions are not substituted for this actual runtime execution.
Tests exercise the real filesystem protocol, independent canonical bytes and
full values, corrected limits, safe display, collisions, controlled binding
changes, short/failed I/O, cancellation and one-close ownership. An actual
uv-installed wheel outside the checkout performs inspect/save/reopen/resave and
checks import provenance and unchanged input. No required platform witness is
skipped or replaced by a mocked success. Detailed command and publication
observations belong in the task receipt, not in a self-certifying corpus.

All S01 original-record bindings, empirical unknowns, provider/private/GHE/non-Git
restrictions, P07 generality ownership and future decision points remain intact.
This selected-file feature does not complete the whole P03 transfer workflow,
P09 review/support, P10 persistence, S2 ingestion, S9 service/scale or S3 lookup.
The four-unit P08 route remains: S01/S02 complete, S03 next/not_started, S04
not_started; P08 stays active/incomplete and P09/P10 not_started. Repository
publication via protected PR/squash/main CI is distinct from the API's local-file
publication semantics. S03 has not started.
