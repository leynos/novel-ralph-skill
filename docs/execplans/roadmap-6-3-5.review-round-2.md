# Logisphere design review — roadmap 6.3.5 ExecPlan (Round 2)

Verdict: PROCEED (✅). The three round-1 blocking defects (B1, B2, B3) are
closed and the four advisories (A1–A4) are folded into the plan body. Every
load-bearing source claim re-verified against real source. No new blocking
defect found.

Reviewer trail: `docs/novel-ralph-harness-design.md` §3.2/§3.4;
`docs/adr-003-shared-interface-contract.md`; `docs/scripting-standards.md`
600-688; `docs/developers-guide.md` line 589/1140-1148/1328-1359/1497;
`AGENTS.md` 18/24-27/141-165; `docs/execplans/roadmap-6-3-1.md` Decisions
D6/D8; first-hand read of `_state_load.py`, `_state_mutators.py`, `_compile.py`,
`novel_state.py`, `_recount.py`, `_wordcount.py`, `_novel_done.py`,
`_desloppify.py`, `tests/test_complete_final_pass_unit.py`,
`tests/test_state_input_message_parity.py`, plus a `grep` over `tests/`. Skills:
`logisphere-design-review`.

## Round-1 blocking defects — all closed

- **B1 (Work item 4 red→green guard did not exist) — CLOSED.** Verified
  `tests/test_complete_final_pass_unit.py:116` is a docstring;
  `test_incomplete_state_exits_three` (lines 111-124) asserts only
  `ExitCode.STATE_ERROR` and `envelope["ok"] is False`. A `grep` over `tests/`
  confirms `state is structurally incomplete` is asserted in no test. Work item
  4 now correctly **adds** a new message-text unit assertion as the red→green
  guard and no longer describes line 116 as an assertion to "update" (plan
  lines 178-189, 663-675; Decision D7).
- **B2 (dangling Decision D6 / unresolved `_compile.py:150` write tail) —
  CLOSED.**
  Decision D6 now exists (plan lines 300-316) and scopes the atomic-**write**
  tail out with a stated, defensible rationale: it is a *write* fault wanting a
  write-shaped remedy ("create `working/manuscript/`"), not the draft-read
  formatter's "inspect the draft you read". Verified `_compile.py:150` does
  interpolate raw `{exc}` (`cannot write {_COMPILED_REL}: {exc}`); leaving it
  for a sibling write-fault task is coherent. The plan now adds an in-code
  comment at that tail (Work item 2 step 5) so a future reader does not mistake
  it for a missed read tail. Forward references resolved.
- **B3 (state-document fault routed through a draft-read formatter) — CLOSED.**
  Decision D7 (plan lines 317-335) now routes `_state_view_or_state_error`
  through 6.3.1's existing `_state_input_error(state_path(), exc)`
  present-but-corrupt arm, **not** `_draft_read_error`. This reuses 6.3.1's
  machinery and honours 6.3.1 Decision D8's distinction. **Verified sound:**
  the mutators call `_load_document_or_state_error(path)` (reads `state.toml`
  from disk) *before* `_state_view_or_state_error(document)` runs on the loaded
  document (`_state_mutators.py:241-242, 247, 330-332, 342`), so by the time
  the view-derivation fault fires the file provably exists. Therefore
  `_state_input_error`'s `if not path.parent.exists() or not path.exists()`
  test is false and the present-but-corrupt arm (`<path> is unreadable or
  corrupt; inspect and repair it, or restore it from a known-good copy`)
  fires — the exact inspect/repair remedy the roadmap mandates, naming the
  state-document path with no raw `{exc}`/`Errno`. The corrupt-arm wording is
  verified verbatim in `_state_load.py`.

## Advisories A1–A4 — folded in

- **A1 (aliased accessor).** Verified `_state_mutators.py:39-43` imports
  `state_path as _state_path` and `working_dir as _working_dir`. Work item 4
  step 1 now calls `_state_input_error(_state_path(), exc)` and the plan notes
  the alias explicitly (lines 648-651). No `NameError`.
- **A2 (`check_compiled` has no `root` local).** Verified `_compile.py:211`
  calls `compiled_matches_drafts(state, working_dir())` with no `root` local.
  Work item 2 step 5 now prescribes `_draft_read_error(working_dir(), exc)`
  there and `_draft_read_error(root, exc)` for `compile_manuscript` (which has
  `root = working_dir()` at line 137). Correct.
- **A3 (parity).** Work item 5 step 2 now asserts the **formatter-owned remedy
  substring** appears in each draft-read boundary's `messages`, not
  byte-for-byte identity across boundaries — correct, because the formatter
  interpolates a per-boundary `reported_dir`. The view-derivation boundary is
  correctly excluded from the draft-read parity set (it shares
  `_state_input_error`'s corrupt arm, already guarded by
  `test_both_load_boundaries_emit_identical_corrupt_message`, verified present).
- **A4 (formatter name).** Moot under the chosen B3 resolution: because the
  view-derivation fault is routed away from `_draft_read_error`, the formatter
  now only ever serves the six read boundaries, so the "draft-read" name no
  longer overclaims to cover a state-document fault.

## Source re-verification (every load-bearing claim sampled)

All boundary line numbers, current strings, and the local variable in scope at
each call site match real source: `novel_state.py:155` (`working_dir` param),
`_recount.py:93` (`_working_dir()`), `_wordcount.py:99` (`working_dir`),
`_novel_done.py:92` (`root`), `_desloppify.py:210` (`working_dir`),
`_compile.py:141` (`root`) and `:211` (`working_dir()`), `_state_mutators.py`
view-derivation tail (`state is structurally incomplete: {exc}`). The two
direct test assertions to refresh (`test_compile_unit.py:295`,
`test_desloppify_sourcing.py:118`) are the only test sites asserting any old
string (verified by `grep`). The `_state_load.py` re-export uses `__all__`
(line 83), the same mechanism the plan reuses for `_draft_read_error`.

## Panel notes (no blockers)

- **Pandalump 🐼 (structure).** Dependency direction is sound: the formatter
  lives
  in the leaf `_state_load.py` (imports only `state`/`contract.runner`),
  re-exported via `novel_state`, mirroring `_state_input_error`; no import
  cycle. Minor residual: the internal name `_draft_read_error` covers
  `compiled.md` reads too (via `check_compiled`, `_novel_done`), which is a
  *compiled* artefact, not a draft — but the emitted message is
  artefact-agnostic (names the `working/` tree, not "draft.md"), so the name is
  a small internal imprecision, not a user-facing lie. Non-blocking; could be
  noted in the formatter docstring.
- **Wafflecat 🐈🧇 (alternatives).** The strongest alternative — one unified
  "present-but-faulted" formatter serving both the six reads and the
  view-derivation fault — was correctly rejected: it would force a single
  message to name either the `working/` tree or the `state.toml` path and blur
  6.3.1 D8's state-document/draft distinction. Splitting (new formatter for
  reads; reuse the corrupt arm for the state document) is the better
  decomposition. No unexplored viable alternative remains.
- **Buzzy Bee 🐝 (scaling).** N/A — pure exception-construction text change on a
  single-shot CLI error path; no load, fan-out, or cost dimension.
- **Telefono ☎️ (contracts).** The exit-code contract is untouched: exit 3 stays
  exit 3, the `StateInputError`→exit-3 mapping in `runner.py` is unchanged, the
  `STATE_INPUT_ERRORS` tuple is neither widened nor forked, and only the
  `messages` text changes. The new symbol is internal (underscore-prefixed); no
  public signature moves. Additive and contract-safe.
- **Doggylump 🐶 (failure modes).** Pre-mortem: the realistic failure is a
  one-sided re-wording reintroducing the drift the task exists to kill —
  mitigated by the formatter-owned-remedy-substring parity assertion (Work item
  5) and the `grep` anti-drift sweep (Concrete steps 3). A TOCTOU race (file
  deleted between `load_document` and view-derivation) would merely fall back
  to the benign missing arm; irrelevant to single-shot execution. No 03:00
  scenario.
- **Dinolump 🦕 (viability).** Low cognitive load: one new formatter beside its
  twin, six mechanical call-site swaps, one reroute. Testing strategy (unit +
  pytest-bdd behavioural + parity + grep sweep) matches the established
  `state_input_message` precedent the team already runs. Coordination with
  7.3.3 (share one home; do not pre-consolidate the wrapper) is explicit.

## Recommendation

Proceed to implementation as written. The two non-blocking notes (formatter
docstring could acknowledge it also covers `compiled.md` reads; keep the parity
assertion substring-based) are optional polish, not gates.
