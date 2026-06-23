# Logisphere design review — roadmap 2.2.2, round 2

Status: REVISE (two blocking defects).

Round-1 blocking points B1–B4 are genuinely resolved and were re-verified
against source (parse.py required-key set, tomlkit/`NonExistentKey` subclass
facts, the `completed-prefix-gap` variant and `incoherent_tree` fixture, and
the empty-manifest `PHASE_STATES["chapter-planning"]`). The cuprum e2e claims
match `cuprum/catalogue.py`/`sh.py` and the existing `check` e2e; no new cuprum
usage.

## Blocking

### BR2-1 (Telefono/Doggylump) — `document_to_state` escapes the exit-3 channel

`contract/runner.py:run` catches only `CycloptsError` and `StateInputError`;
every other exception propagates uncaught and the process exits 1 (Python's
uncaught-exception code), never the contract's exit 3.

In `set-cursor` (work item 3, step 4) and `advance-phase` (work item 4, step 1)
the call `document_to_state(document)` is made **after**
`_load_document_or_state_error` returns and is **not** wrapped. The helper as
coded (work item 3 code block) wraps only `load_document(path)`. A `state.toml`
that is syntactically valid TOML but structurally incomplete (a missing
required table or key) passes `load_document` cleanly, then `document_to_state`
→ `parse_state` raises `NonExistentKey`/`KeyError`/`TypeError`; a bad phase
string raises `ValueError` from `Phase(...)`. All are uncaught → exit 1,
breaching the load-bearing exit-3 refusal contract (design §3.2; the Tolerance
"Refusal-code regression").

Decision Log D4 asserts `STATE_INPUT_ERRORS` already subsumes these faults, but
that subsumption only matters at a catch site that wraps the raising call —
which the plan does not provide for `document_to_state`. The work-item-1
missing/unparseable test only exercises a missing file and a syntactically
invalid file, both of which raise inside `load_document`; the
structurally-incomplete-but-valid-TOML case is neither handled nor tested.

Fix direction (planner's call): route the `document_to_state` call through the
exit-3 translation too (e.g. `_load_document_or_state_error` returns the typed
view, or a second `_document_to_state_or_state_error` wraps it under the same
`STATE_INPUT_ERRORS` tuple), and add a contract test that drives `set-cursor`
and `advance-phase` against a `state.toml` that is valid TOML but missing a
required table (e.g. `working/state.toml` = `"schema_version = 1\n"`),
asserting exit 3, not 1.

### BR2-2 (Pandalump/Dinolump) — `init` drops the Initialisation directory skeleton

state-layout.md "Initialisation" step 1 is
`mkdir -p working/{characters,world,reader,plan,manuscript,reviews}`. The plan's
`init` body (work item 2) does only
`working.mkdir(parents=True, exist_ok=True)` plus the `state.toml` and `log.md`
writes, while the Context and "Docs to read" sections claim fidelity to
"state-layout.md Initialisation". The plan neither creates the subdirectory
skeleton nor records a decision to defer it.

No current invariant or test depends on those directories, so this does not
break `check`; but the plan contradicts its own cited source of truth silently.
Resolve by either (a) creating the skeleton in `init` to match step 1, or (b)
adding a Decision Log entry that defers directory creation to the commands that
first need each subdirectory, with the rationale, so a reviewer does not read
the omission as a gap.

## Advisory

- AR2-1 (Wafflecat): the B3 reconciliation makes "refuses skips" vacuous under
  the zero-argument `advance_phase()` — a skip cannot be *requested*, so the
  only refusal is an already-incoherent prior. This is internally consistent
  and recorded (D7), but the developers-guide subsection (work item 5) should
  state plainly that "out-of-order completion" is realised solely as the
  prior-state coherence guard, so a future reader does not look for
  skip-rejection logic that cannot exist.
- AR2-2 (Telefono): the `set-cursor` success test sets a cursor "within range"
  on `phase_state_tree("drafting")` (3 chapters, `current_chapter=3`). Pin the
  exact valid value used so the test does not accidentally assert `chapter=0`
  with a non-zero scene/beat (which the validator refuses).
