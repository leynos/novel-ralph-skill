# Post-merge audit — roadmap task 6.3.1

Audit of the codebase after roadmap task 6.3.1 ("Make state-input (exit-3)
errors actionable across every command") merged to `main` at commit `53223a2`.

The merged change carves a new dependency-free leaf module
`novel_ralph_skill/commands/_state_load.py` out of `novel_state.py` and gives it
the single home for *where* a command looks (`working_dir`, `state_path`), *what
counts* as a state-input fault (`STATE_INPUT_ERRORS`), and *how* a failed
`state.toml` load is rendered as the exit-`3` `StateInputError`
(`_state_input_error`, `_load_or_state_error`). The mutator loader
`_state_mutators._load_document_or_state_error` now routes through the same
`_state_input_error` helper, so the reader/checker (`tomllib`) and mutator
(`tomlkit`) load boundaries emit byte-for-byte identical actionable prose. A
parity test (`tests/test_state_input_message_parity.py`) and a two-arm unit test
(`tests/test_state_input_message_unit.py`) pin that behaviour.

The work is high quality and meets its own success clause: both `state.toml`
load boundaries are genuinely consolidated (no third `load_state`/`load_document`
caller survives outside `_state_load`/`_state_mutators`), the missing-versus-corrupt
remedy split is sound, the no-`Errno`/no-traceback guarantee is tested on both
arms, and the new module respects the import-direction and 400-line-cap
constraints the docstrings cite. The findings below are about the *blast radius*
the change leaves uneven: it polishes the two `state.toml`-load boundaries but
leaves the sibling *draft-read* boundaries on the old raw-`{exc}` idiom, and the
user-facing docs do not yet show the new message.

## Finding 1 — Draft-read state-error boundaries still leak raw `{exc}`, now inconsistent with the polished state-load boundary

- **Category**: inconsistency
- **Severity**: medium
- **Location**:
  `novel_ralph_skill/commands/novel_state.py` (`_disk_evidence_or_state_error`,
  lines 153-157); `novel_ralph_skill/commands/_recount.py` (lines 92-94);
  `novel_ralph_skill/commands/_wordcount.py` (lines 98-100);
  `novel_ralph_skill/commands/_novel_done.py` (lines 91-93);
  `novel_ralph_skill/commands/_desloppify.py` (lines 209-211);
  `novel_ralph_skill/commands/_compile.py` (lines 140-141, 147-151).

Task 6.3.1 was raised to stop the exit-`3` channel from surfacing raw operating
-system text (an `Errno`, a path-as-noise) and to make it name where the command
looked and how to recover (`scripting-standards.md` lines 603-605: "Human-friendly
error messages should highlight remediation steps"). The new `_state_input_error`
helper delivers that for the `state.toml`-load fault. But the same exit-`3`
channel is reached by at least six sibling boundaries that catch the very same
`STATE_INPUT_ERRORS` tuple and re-raise as `StateInputError` with an open-coded
`f"… {exc}"` message — `f"cannot read chapter drafts: {exc}"`,
`f"cannot recount chapter drafts: {exc}"`,
`f"cannot read disk evidence under {working_dir}: {exc}"`,
`f"cannot evaluate the done predicate under {root}: {exc}"`, and the `_compile`
write/read pair. Each interpolates the raw exception, so after 6.3.1 a user who
runs `novel state check` from the wrong directory gets polished prose for a
missing `state.toml` but raw `Errno`-bearing text for an unreadable `draft.md` on
the same command. These boundaries do name their action (a partial win) but still
leak the OS noise 6.3.1 set out to remove, and they carry no remedy clause.

Roadmap task 7.16.3 already tracks the *DRY* consolidation of three of these
wrappers (`wordcount`, `recount`, `desloppify`) into one
`read_drafts_or_state_error` helper, but its text explicitly preserves the
`f"cannot read chapter drafts: {exc}"` string and does not address message
quality, nor does it enumerate the `_compile`, `_novel_done`, and
`_disk_evidence_or_state_error` copies. The message-quality gap is therefore the
genuinely new debt 6.3.1 surfaces.

- **Proposed fix**: When 7.16.3's `read_drafts_or_state_error` helper lands, have
  it (and the `_compile`/`_novel_done`/`_disk_evidence` boundaries) build their
  message through a shared actionable formatter analogous to
  `_state_input_error` — naming the `working/` tree and offering an inspect/repair
  remedy — rather than interpolating `{exc}`. Chain `exc` via `from` for the
  debugger while keeping `exc.messages` noise-free, exactly as `_state_input_error`
  does. Widen 7.16.3 (or add a sibling roadmap item) to enumerate all six call
  sites and to cover message quality, not only the catch-idiom DRY. Proposed as
  a roadmap item below; not applied here (roadmap edits are reserved to the root
  agent, and this is a read-only audit step).

## Finding 2 — `_state_input_error` reports "no novel working/ found" even when `working/` exists but `state.toml` is absent

- **Category**: ergonomics
- **Severity**: low
- **Location**: `novel_ralph_skill/commands/_state_load.py`
  (`_state_input_error`, lines 108-113).

The missing-arm guard is `if not path.parent.exists() or not path.exists():`,
and that arm emits `f"no novel working/ found in {cwd}; run from the novel root,
or run 'novel state init' to create one"`. When `working/` *does* exist but
`state.toml` is missing (a half-initialised tree, or a `state.toml` deleted by
hand), `path.parent.exists()` is `True` while `path.exists()` is `False`, so this
arm fires and tells the operator no `working/` was found — which is factually
wrong, since `working/` is right there. The remedy (`novel state init`) is still
correct (init recreates the missing `state.toml`), so the advice is sound even if
the diagnosis sentence is not. This is a message-accuracy nit, not a routing
defect: the exit code is correct on every branch.

- **Proposed fix**: Either soften the prose so it describes the actual fault
  ("no readable `working/state.toml` found in {cwd}") regardless of whether the
  directory exists, or split the missing arm into a "no `working/`" sub-case and
  a "`working/` present but `state.toml` missing" sub-case so each sentence matches
  the on-disk reality. A unit case asserting the message text when `working/`
  exists but `state.toml` does not would pin the chosen wording. Low priority; the
  current behaviour is correct and only the diagnosis sentence is imprecise.

## Finding 3 — User-facing docs describe the exit-3 conditions but never show the new actionable message or its two-arm remedy split

- **Category**: docs-gap
- **Severity**: low
- **Location**: `docs/users-guide.md` (lines 140-144 and the exit-`3`
  references at lines 104, 118, 143, 214, 252, 442, 490);
  `docs/developers-guide.md` (lines 122-123).

6.3.1 changed observable user behaviour: the exit-`3` envelope's `messages` now
carry actionable prose with a distinct remedy per arm (a missing `working/`
points at `novel state init`; a present-but-corrupt `state.toml` asks for
inspect/repair and deliberately *omits* `init`). The users' guide still describes
exit `3` only as "`./working/state.toml` is missing or unparseable (the
state-error channel)" and never surfaces the message a user will now read or the
missing-versus-corrupt distinction that tells them which remedy applies. The
developers' guide notes the message is "now an actionable string that names the
current directory and the `novel state init` remedy (roadmap §6.3.1)" but does
not record the *second* arm (corrupt files must not advise `init`), which is the
load-bearing Decision-Log-D2 invariant a future editor most needs to know before
touching `_state_input_error`.

- **Proposed fix**: Add a short paragraph (or a two-row table) to the users'
  guide exit-`3` section showing the two messages and when each appears, so an
  operator can self-diagnose "wrong directory" versus "damaged file". Extend the
  developers'-guide §6.3.1 note to record both arms and the rule that the corrupt
  arm must never advise `init`, cross-referencing `_state_input_error` and its
  unit test. Docs-only; safe to fold into the next docs-touching task.

## Finding 4 — Shared-symbol import source is split between `_state_load` and the `novel_state` re-export

- **Category**: inconsistency
- **Severity**: low
- **Location**: `novel_ralph_skill/commands/_state_mutators.py` (lines 36-37,
  importing `STATE_INPUT_ERRORS`/`_state_input_error` direct from `_state_load`)
  versus `_recount.py`, `_wordcount.py`, `_novel_done.py`, `_desloppify.py`,
  `_compile.py`, `novel.py` (importing the same re-exported symbols from
  `novel_state`).

`_state_load`'s module docstring states the intent plainly: the symbols are
re-exported by `novel_state` "so every command keeps importing these symbols from
`novel_state`". Most commands honour that, but `_state_mutators` imports
`STATE_INPUT_ERRORS` and `_state_input_error` directly from `_state_load`. That
direct import is *necessary* for `_state_mutators` (importing via `novel_state`
would reverse the `_state_mutators` → `novel_state` direction and re-create the
cycle the carve-out exists to avoid), so this is a justified exception rather than
a defect — but it is an undocumented one, and a future reader comparing import
lines may "fix" it in the wrong direction.

- **Proposed fix**: Add a one-line comment at the `_state_mutators` import site
  explaining why it must source from `_state_load` (cycle avoidance) while the
  other commands source from `novel_state` (the re-export convention), mirroring
  the explanatory comments already present at the `novel_state` import sites. No
  code movement needed.

## Finding 5 — `ledger`/`rulepack` `_coerce` and `errors` near-duplication is broad but already roadmapped

- **Category**: duplication
- **Severity**: low
- **Location**: `novel_ralph_skill/ledger/_coerce.py` versus
  `novel_ralph_skill/rulepack/_coerce.py`; `novel_ralph_skill/ledger/errors.py`
  versus `novel_ralph_skill/rulepack/errors.py`. Tracked deferral at
  `docs/roadmap.md` lines 4286-4303.

Outside the 6.3.1 change set, the two validating-loader subpackages remain
structural near-twins: `_coerce.py` is a line-for-line copy modulo the error type
(`LedgerError`/`RulePackError`), the entity noun (`device`/`rule`), and docstring
prose; `errors.py` is the same two-channel pair (a per-entity content error plus
a file error). `ledger/_coerce.py`'s own docstring documents this as a deliberate
near-copy justified by the frozen rule-pack path. The fold-out onto
error-factory-parameterised helpers is already enumerated in the roadmap (the
reroute at lines 4286-4303 names both `_coerce.py` files and the `parse`/`detect`
siblings), so no new tracking is required. Recorded here only to confirm the
duplication still stands after 6.3.1 and that the roadmap inventory is current.

- **Proposed fix**: None new — the existing roadmap reroute (audit:7.1.2) already
  owns this. Confirmed in-scope and current; no action for the root agent beyond
  leaving that item in place.
