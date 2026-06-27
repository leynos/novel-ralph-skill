# Post-merge audit — roadmap task 7.1.6

Audit of the codebase after task 7.1.6 ("Settle the §7.1 authoritative-docstring
and self-projection convention") merged to `main` at commit `abc652f`. The task
pinned the §7.1 convention once: the authoritative module owns the canonical
projection docstring, registered consumers self-project the defining-module path,
and a reusable in-process drift-guard
(`tests/test_projection_docstring_drift_guard.py`) reds when a consumer drops the
canonical path or carries a bare re-export tail. It also normalised the
compile-projection and reconciliation-payload cross-references in `_compile.py`,
`novel_state.py`, and `compile_model.py`, and documented the convention in the
developers' guide.

The merged change is clean and well-pinned: the drift-guard keys
authoritative-versus-consumer by registry position (not by parsing prose for an
"authority" token), and its discriminating power is itself unit-tested with
planted drift shapes and legitimate-consumer fixtures
(`TestHelperRejectsDrift`, `TestHelperAcceptsLegitimateConsumers`). The findings
below are maintainability, ergonomics, and coverage opportunities surfaced while
auditing the 7.1.6 blast radius; none is a correctness defect.

The exploration used `leta`/`grep` for code navigation and `sem`/`git show` for
history tracing. The sources of truth consulted were
`docs/novel-ralph-harness-design.md` (§3.3 checker/mutator table, §4.3, §5.4),
`docs/adr-001-deterministic-judgemental-boundary.md`,
`docs/adr-003-shared-interface-contract.md`, `docs/developers-guide.md` (the §7.1
convention block), `AGENTS.md` (the 400-line cap and quality gates), and the
existing audit issues under `docs/issues/`. Prose follows the en-GB Oxford
spelling convention (`AGENTS.md`).

## Finding 1 — The draft-read fault-routing block is hand-repeated at five call sites

- **Category:** duplication
- **Severity:** low
- **Location:** `novel_ralph_skill/commands/_recount.py:94-97`,
  `novel_ralph_skill/commands/_wordcount.py:99-102`,
  `novel_ralph_skill/commands/_novel_done.py:90-96`,
  `novel_ralph_skill/commands/novel_state.py:162-165`
  (`_disk_evidence_or_state_error`), and
  `novel_ralph_skill/commands/_compile.py:138-144` and `217-223`
  (`_draft_read_error` is the shared *message* formatter, but the surrounding
  control flow is duplicated).

The 6.3.5 task correctly single-sourced the draft-read *message* into
`_draft_read_error`, but the *control-flow envelope* around it remains copied at
every draft-read boundary:

```python
try:
    return <reader>(...)
except STATE_INPUT_ERRORS as exc:
    raise _draft_read_error(<working_dir>) from exc
```

Five sites repeat this `try` / `except STATE_INPUT_ERRORS as exc` /
`raise _draft_read_error(dir) from exc` shape verbatim; only the wrapped reader
call and the directory expression vary. The duplication is benign today, but it
means the routing contract (which exception group routes to which formatter, and
that the original is chained via `from exc`) lives in five places rather than
one. A future change — adding a new exception class to the routed set, or
attaching structured context to the re-raise — must be made five times, and a
missed site silently lets a draft-read fault escape to the benign exit `1` it was
designed to keep it out of.

**Proposed fix:** Extract a single context manager beside `_draft_read_error` in
`_state_load.py`, for example
`@contextlib.contextmanager def draft_read_boundary(reported_dir: Path)`, that
wraps the body in the `try` / `except STATE_INPUT_ERRORS` / `raise
_draft_read_error(reported_dir) from exc` envelope. Each call site collapses to
`with draft_read_boundary(root): return <reader>(...)`, so the routing contract
lives in one place. This mirrors the established `_file_fault_error` single-arm
constructor pattern (`_state_load.py:146`) — the message stem was deduplicated;
this deduplicates the matching control flow. Add one focused unit test that the
context manager re-raises a planted `OSError` as a `StateInputError` carrying the
named directory and chains the original via `__cause__`.

## Finding 2 — `_render_reconciliation` is a one-line delegating wrapper

- **Category:** ergonomics
- **Severity:** low
- **Location:** `novel_ralph_skill/commands/novel_state.py:130-141`

`_render_reconciliation(reconciliation)` is an eleven-line function (mostly
docstring) whose entire body is `return reconciliation_payload(reconciliation)`.
After 7.1.6 routed it through the shared
`novel_ralph_skill.state.reconcile.reconciliation_payload` projection, the wrapper
adds no transformation — it neither reshapes the payload nor selects fields; it
re-spells the public projection behind a private name. Its sole caller is `_check`
(`novel_state.py:208`), which could call `reconciliation_payload` directly. This
is the same redundant-indirection shape recorded against the
`_envelope_field_order()` wrappers in `docs/issues/audit-7.1.5.md` Finding 2: a
reader must follow the helper to discover it does nothing but delegate.

There is one wrinkle: 7.1.6 registered `_render_reconciliation` as a *consumer*
row in the drift-guard (`test_projection_docstring_drift_guard.py:163`), so its
docstring is now load-bearing for the convention. Deleting the wrapper means
moving that consumer registration to the call-site context (or dropping the
reconciliation row to its sole remaining consumer if `_check` cites the canonical
path inline).

**Proposed fix:** Either (a) inline `_render_reconciliation` into `_check`,
calling `reconciliation_payload(derive_reconciliation(state, root))` directly and
relocating the defining-module cross-reference into `_check`'s docstring (then
drop the now-empty consumer row, or repoint it at `_check`); or (b) if the named
seam is kept deliberately for the drift-guard registration, document in the
wrapper docstring that it exists *solely* as the registered consumer anchor, so
a future reader does not mistake it for dead indirection. Option (a) is preferred
it removes a layer without weakening the convention, because `_check`'s docstring
already names the reconciliation payload.

## Finding 3 — Production docstrings carry a very high prose-to-code ratio with embedded ExecPlan/Decision-Log citations

- **Category:** docs-gap
- **Severity:** low
- **Location:** `novel_ralph_skill/state/compile_model.py` (docstrings are ~72%
  of the file's lines), `novel_ralph_skill/commands/_state_load.py:173-340` (the
  four file-fault formatters carry 40+ docstring lines each over a one-line body),
  `novel_ralph_skill/commands/_compile.py:1-40` (a 40-line module docstring),
  `novel_ralph_skill/state/done_predicate.py:213-262` (`compile_consistent`).

Several modules in the 7.1.6 blast radius now devote the majority of their lines
to docstrings, and a large fraction of that prose is *process* citation — ExecPlan
decision-log tags (`D-READ`, `D-POLARITY`, `D-BYTE-COMPARE`, `D6`, `D7`, `WI3`),
round-numbered review points (`BR2-2`, `R2-A2`), and `audit:N.N.N` back-references
— rather than API contract a caller needs. `compile_model.py` is 72% docstring;
the four `_state_load.py` formatters repeat near-identical "renders from the path
alone; the caller keeps the caught exception solely for `raise … from exc`
chaining … no `Errno`, no `{exc}` repr, no traceback" paragraphs. This prose is
genuinely valuable as rationale, but co-locating ExecPlan tags inside the shipped
`__doc__` (a) couples the public docstring to transient plan artefacts a future
reader cannot resolve once the ExecPlan is archived, and (b) inflates the files
toward the 400-line cap (see Finding 4).

**Proposed fix:** Establish a convention (a short note in
`docs/documentation-style-guide.md`) that production docstrings state the *current*
contract — parameters, returns, raises, and the invariant — while ExecPlan tags,
round-review points, and `audit:` back-references belong in the commit message,
the ExecPlan, or a single `# rationale:` comment, not the shipped `__doc__`. Where
a rationale paragraph is shared verbatim across siblings (the "renders from the
path alone …" boilerplate across the four `_state_load.py` formatters), state it
once in the module docstring or the shared `_file_fault_error` constructor and let
the siblings reference it. This is a standing stylistic decision, not a 7.1.6
defect; track as a low-priority roadmap item.

## Finding 4 — Several command/state modules remain within a few lines of the 400-line cap

- **Category:** complexity
- **Severity:** low
- **Location:** `novel_ralph_skill/commands/_gate_drafting_mutators.py` (399
  lines), `novel_ralph_skill/rulepack/parse.py` (392),
  `novel_ralph_skill/commands/_desloppify.py` (389),
  `novel_ralph_skill/state/disk_evidence.py` (371),
  `novel_ralph_skill/state/reconcile.py` (366).

`AGENTS.md:24` imposes a 400-line per-file cap. This was already flagged in
`docs/issues/audit-7.1.5.md` Finding 4 for the top three files; 7.1.6 did not
touch them but the standing risk persists, and the verbose-docstring pattern
(Finding 3) actively pushes the next routine change over the cap. `_state_load.py`
now hosts four 40-line formatters and would itself approach the cap if a fifth
file-fault sibling is added. The next parameter, branch, or rationale paragraph
in any of these five files forces an unplanned mid-task split.

**Proposed fix:** As recommended in 7.1.5, pre-emptively identify a natural seam
in each near-cap module (for example, extracting the pure validation helpers from
`_gate_drafting_mutators.py` into a sibling, mirroring the established
`tests/_skill_contract_scanner.py` split pattern) so the split is a deliberate
design decision rather than a forced reaction. Applying Finding 3 (moving ExecPlan
prose out of `__doc__`) would also relieve the pressure. Track as a low-priority
roadmap item, not an immediate fix.

## Finding 5 — The drift-guard registry has no completeness check against the documented §7.1 family

- **Category:** test-gap
- **Severity:** low
- **Location:** `tests/test_projection_docstring_drift_guard.py:144-168`
  (`_REGISTRY`) versus `docs/developers-guide.md:1067-1104` (the convention block).

The drift-guard's `_REGISTRY` currently pins two projections
(`compiled_matches_drafts`, `reconciliation_payload`). The developers' guide states
the convention covers "the projections 7.1.1, 7.1.4, and the remaining §7.1 tasks
consolidate", and the guard's own module docstring says "A new §7.1 task that
consolidates a projection registers its row in that guard … rather than
re-deciding the convention". But nothing *enforces* that a newly consolidated
projection is actually added to `_REGISTRY`: a future §7.1 task could single-source
a third projection, cite it correctly, and forget to register the row, and the
green tree would never notice. The guard protects the rows it knows about, but not
the obligation to add rows.

**Proposed fix:** Add a coverage assertion that ties the registry to a declared
manifest of consolidated §7.1 projections — for example, a module-level
`CONSOLIDATED_PROJECTIONS` tuple of canonical paths (the same list the developers'
guide enumerates) and a test asserting every entry appears as a `_REGISTRY` row's
`canonical_path`. This makes "forgot to register the new row" a red test rather
than a silent gap, completing the single-source-of-truth invariant the convention
claims. If a lighter touch is preferred, at minimum add a comment in `_REGISTRY`
pointing at the developers'-guide list so the two stay manually synchronised.
