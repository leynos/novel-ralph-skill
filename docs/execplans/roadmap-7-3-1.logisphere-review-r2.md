# Logisphere design review — roadmap 7.3.1 (round 2)

Verdict: REVISE. Revision 2 cleanly resolves all three round-1 blocking points
on the **production** side (B1/B2/B3): the `_state_load` and bare
`_load_or_state_error` prose sweep is now exhaustive for `commands/`,
`state/compile_model.py`, and the developers' guide, gated by
`grep -rn '_state_load' …` returning nothing; the parity-test private-formatter
intent is pinned (D6); and the formatter-count guard is confirmed absent (D7).
Credit is due — the production migration (WI1, WI3) and the production prose
sweep (WI5 clean-ups 1–2) are complete and accurate, verified line-by-line.

But round-2 review surfaces a **symmetric, still-open** defect class on the
**test** side that the plan does not enumerate and that **no mechanical gate in
the plan catches**: six test files import seam/formatter symbols *from
`novel_state`*, and four test docstrings carry `:func:` roles to
`novel_state._<formatter>`. WI5 drops two of those symbols from `novel_state`
entirely (hard ImportError) and demotes the rest from the canonical home
(canonical-path-rule and WI4-validation violations). The plan's hard gate greps
`_state_load`, not `novel_state._<formatter>`, so this class falls through
every net. This is the same six-months-later trap round-1 B1 named, just on the
test side — so it is blocking.

Reviewer trail: read the execplan from disk; re-verified every load-bearing
claim against the real tree. `_state_load.py` is 364 lines (matches the
corrected figure). `stub.py` absent (confirmed). Roadmap 7.3.1 success criteria
and the 7.3.6 `WORKING_DIR_NAME`/`contract` coordination verified against
`docs/roadmap.md` lines 2760–2912. `leta mv --help` confirms it rewrites
*import statements only* ("update all imports") — it does **not** rewrite a
`from novel_state import X` line (that names `novel_state`, not `_state_load`),
and `leta rename` rewrites only the `_load_or_state_error`→
`load_or_state_error` symbol token. `make all` =
`build check-fmt lint typecheck test`; `nixie` validates **Mermaid only** —
there is **no Sphinx/cross-reference resolution gate**, so a dangling `:func:`
role rots silently. ADR-001 deterministic/ judgemental boundary untouched (pure
module-boundary refactor; no behaviour change). cuprum confirmed off-path
(`grep -rn cuprum novel_ralph_skill/commands/` empty; seam uses `tomllib`/
`pathlib`, no subprocess) — D4 holds.

## What now holds (round-1 remediation accepted)

- **B1 (production):** WI5 clean-up 1 enumerates exactly the 10 `_state_load`
  references the live grep returns (`state/compile_model.py:73`, `novel.py:153`,
  `state_sourcing.py:7,56`, `novel_state.py:57,61`, `test_state_load_*`
  :6/:13/:51, devguide:620) and gates them with the hard `grep`. Verified
  complete.
- **B1 (production prose roles):** WI5 clean-up 2 enumerates all six
  `novel_state._<formatter/seam>` `:func:` roles in *production* source
  (`_wordcount.py:112`, `_state_mutators.py:89,91,130`,
  `_desloppify.py:168,176`) plus the two bare-prose mentions
  (`_wordcount.py:117`, `_novel_done.py:28`). Cross-checked against
  `grep -rn 'novel_state\._' novel_ralph_skill/`: exact match, nothing missed
  on the production side.
- **B2:** D6 pins `test_state_load_actionable_parity.py` to the private
  formatter
  set, not the public seam. Correct.
- **B3:** D7 records the grep proving the developers-guide formatter-count prose
  is unguarded; "Five" stays, only the module token at 620 moves. Correct.
- Consumer import-block citations for WI3 spot-checked (`_desloppify.py:46-52`,
  `_recount.py:29-32`, `_novel_done.py:39-45`) — accurate.

## Blocking defects (back to the planner)

### B4 — Two test imports become hard ImportErrors when WI5 drops the re-exports, and the plan never names them

WI5 clean-up 3 drops the symbols `novel_state` does not use in its own body. I
verified novel_state's body usage (`awk 'NR>102' … | grep -c`): **used** =
`STATE_INPUT_ERRORS`, `_draft_read_error`, `_load_or_state_error`,
`resolved_working_dir`, `state_path`, `working_dir`; **re-export only
(dropped)** = `WORKING_DIR_NAME`, `_compile_write_error`,
`_device_ledger_read_error`, `_rule_pack_read_error`, `_state_input_error`. The
plan's clean-up-3 list matches this. But two test files import *dropped*
symbols from `novel_state`:

1. `tests/multiplexer_support.py:25` —
   `from … novel_state import WORKING_DIR_NAME`.
   `multiplexer_support` is a conftest-registered plugin
   (`tests/conftest.py:64`) imported by `test_multiplexer_dispatch.py`,
   `test_multiplexer_behaviour.py`, and `test_legacy_surface_retired.py`. After
   WI5 drops `WORKING_DIR_NAME` from `novel_state`, the multiplexer suite fails
   **at collection** with ImportError.
2. `tests/test_state_input_message_unit.py:22` — imports
   `_load_or_state_error, _state_input_error, state_path, working_dir` from
   `novel_state`. `_state_input_error` is dropped → ImportError.

The plan names `test_state_input_message_unit.py` in WI4 but only generically
("import the **public seam**") — and `_state_input_error` is a **private
formatter** that D3/D6 keep private, *not* the public seam, so the WI4 guidance
as written tells the implementer the wrong thing (it is the exact B2
conflation, re-introduced). `multiplexer_support.py` is **not named anywhere**
in the plan.

Following the plan literally — repoint only the named files, then drop the
re-exports in WI5 — leaves WI5's `make all` **red**. That violates the plan's
own "each work item is a single gate-passing commit" invariant.

Remedy: enumerate both files explicitly. `multiplexer_support.py:25` →
`from … state_sourcing import WORKING_DIR_NAME`.
`test_state_input_message_unit.py:22` → import the public seam
(`load_or_state_error`, `state_path`, `working_dir`) *and* the private
`_state_input_error` from `state_sourcing` (it is a formatter-parity import,
like the B2/D6 file — call it out the same way).

### B5 — Four test docstring `:func:` roles point at `novel_state._<formatter>` and silently rot; no gate catches them

These docstring roles name the re-export façade, not the defining module:

- `tests/test_draft_read_message_unit.py:4` — `novel_state._draft_read_error`
- `tests/test_draft_read_message_parity.py:7` — `novel_state._draft_read_error`
- `tests/test_state_input_message_unit.py:4` — `novel_state._state_input_error`
- `tests/test_state_input_message_parity.py:5` —
  `novel_state._state_input_error`

After WI5, `_state_input_error` no longer exists on `novel_state` at all, and
`_draft_read_error` is no longer the canonical home there. Per the
developers-guide "defining-module path is canonical, never the re-export
façade" rule (lines 1080–1104) — which the plan's own Constraints invoke —
these roles must name `state_sourcing`. They are **not** caught by the WI5 hard
gate (it greps `_state_load`, these say `novel_state`), **not** by `make lint`/
`nixie` (no Sphinx xref resolution; `nixie` is Mermaid-only), and **not** by
the projection drift-guard (it pins only `compile_model`/reconciliation). They
rot silently — the precise six-months-later failure round-1 B1 was about,
reproduced on the test side.

Remedy: add these four `:func:`-role sites to the WI5 clean-up-2 enumeration,
and **broaden the hard gate** so it actually catches this class, e.g.

```sh
grep -rnE \
'novel_state\._(draft_read_error|state_input_error|compile_write_error|rule_pack_read_error|device_ledger_read_error)' \
novel_ralph_skill/ tests/
```

must return nothing after WI5 (the seam `_load_or_state_error` role rewrites to
`load_or_state_error`, so add it to the gate too). The existing `_state_load`
grep is necessary but not sufficient; the rename's blast radius includes every
`novel_state._<formatter>` reference, and only a `novel_state._`-shaped gate
proves the façade roles are gone.

### B6 — Three further test files import seam symbols from `novel_state`; WI4 validation will fail unless they are repointed, yet the plan omits them

These import *kept* symbols (so no ImportError), but they import the **seam**
from the re-export façade, which WI4's own validation forbids
(`grep -rn 'novel_state import' tests/` must show "no seam symbols") and which
the canonical-path rule forbids:

- `tests/test_compile_unit.py:30` — `state_path, working_dir`
- `tests/test_validate_state_corpus.py:30` — `STATE_INPUT_ERRORS`
- `tests/test_draft_read_message_unit.py:25` — `_draft_read_error` (code import,
  in addition to its B5 docstring role)

None of the three is named in the plan. WI4 relies on the implementer's
`grep -rn 'novel_state import' tests/` to surface "any others", but then states
a validation criterion that *fails* if they are not repointed — so the plan is
internally inconsistent: it omits the files from its enumeration while
requiring their absence from the final grep. Enumerate all three (repoint to
`state_sourcing`), so WI4's commit can actually pass its stated validation.

(Note: `test_draft_read_message_unit.py:25` imports `_draft_read_error`, a
private formatter, from `novel_state`. Like the B2/D6 case, WI4's "import the
public seam" guidance is wrong for it — it must import the private formatter
from `state_sourcing`.)

## Advisory (non-blocking)

- A1: The four message tests (`test_state_input_message_*`,
  `test_draft_read_message_*`) and the corpus/compile/multiplexer importers
  form a coherent "formatter-and-seam parity test" cohort that the plan
  currently treats piecemeal. Consider one WI4 sub-table: column 1 = file,
  column 2 = imported symbols, column 3 = public-seam vs private-formatter,
  column 4 = docstring `:func:` role to fix. That table, plus the broadened B5
  gate, closes the whole class in one pass and makes the next reviewer's job
  mechanical.
- A2: WI4's decision line ("import the *seam* from `state_sourcing` in tests,
  **except** the formatter-parity test above") names only **one** exception
  (`test_state_load_actionable_parity.py`). There are in fact **three**
  private-formatter importers
  (`+ test_state_input_message_unit.py:22 _state_input_error`,
  `+ test_draft_read_message_unit.py:25 _draft_read_error`). Generalise the
  exception from "the parity test" to "every test that imports a private
  `_…_error` formatter" so the rule scales.

## Pre-mortem (Doggylump)

Six months on, the incident is a doc/test audit (or task 7.3.3, which
`Requires 7.3.1` and lands the `read_drafts_or_state_error` helper *in the same
neutral home*) that trips over `:func:`-role references to
`novel_state._state_input_error` — a symbol that no longer exists on
`novel_state` — and a confused investigator spends an afternoon discovering the
role was never repointed because no gate ever checked the `novel_state._`
spelling. Blast radius: a stale-doc hunt, not a runtime outage (the
dropped-symbol ImportErrors in B4 are loud and caught by `make all`; the
rotting roles in B5 are quiet and caught by nobody). Bet that was wrong: "the
`_state_load` grep gate proves the rename left no dead reference" — it proves
only the *file-name* half; the *symbol-façade* half
(`novel_state._<formatter>`) is unguarded. Prevention designed in now: the
broadened B5 gate.

## Strongest alternative (Wafflecat)

Round 1's alternative (home the seam under `state/` rather than flat in
`commands/`) still stands rejected for the same reason — it trades away the
clean 7.3.6 `contract` coordination for no 7.3.1 gain, and risks a
`state`-internal edge. D1 holds.

The round-2 alternative worth weighing is **scope**: rather than have WI5 drop
*every* unused re-export now, keep `novel_state` re-exporting the formatters
(behind `__all__`) for one more task and let **7.3.3** — which lands in the
same home and must touch these very call sites — retire them. Trade-off: it
would shrink 7.3.1's test-side blast radius to just the two hard ImportErrors
and defer the four rotting roles. But it leaves `novel_state` a partial façade
(the exact "de-facto shared-utility home" smell 7.3.1 exists to kill) and
splits one rename across two tasks. Net: reject — fixing B4/B5/B6 in 7.3.1 is
the right call; the work is bounded (six files, four roles) and finishes the
single-home property cleanly. Recording for calibration.

## Recommended next steps (ordered)

1. **B4** — name `multiplexer_support.py:25` and
   `test_state_input_message_unit.py:22`
   in WI4; repoint before WI5 drops the re-exports, so each commit stays green.
2. **B5** — add the four test docstring `:func:` roles to WI5 clean-up 2 and
   **broaden the hard gate** to a `novel_state\._<formatter>` form.
3. **B6** — enumerate `test_compile_unit.py:30`,
   `test_validate_state_corpus.py:30`,
   `test_draft_read_message_unit.py:25` in WI4 so its stated validation can
   pass.
4. **A1/A2** — fold the cohort into one WI4 table and generalise the
   private-formatter exception to all three such files.

— end round 2
