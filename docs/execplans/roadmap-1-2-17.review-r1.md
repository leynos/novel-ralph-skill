# Logisphere design review — roadmap 1.2.17 ExecPlan (Round 1)

Verdict: REVISE. The design (documentation-only sweep, noun-form preservation,
scope boundaries, gate selection) is sound, but the enumeration the plan
designates as the execution contract is numerically wrong. Fix the counts and
the line-239 double-hit, then this proceeds.

## Blocking defects

- B1 (Pandalump / Telefono): The convert-bucket count is wrong. The plan asserts
  "17 `novel-state` invocations" (Purpose line 26; Work item 1 expected output
  line 416 "novel-state ×17"; Artifacts line 612 "novel-state ×17"). The live
  count is **15** `novel-state` occurrences across 14 lines, plus **1**
  `novel-compile`. Evidence: `grep -oE 'novel-state' state-layout.md | wc -l` →
  15. Work item 1 is explicitly "the contract the three sweep items execute
  against" and Work item 5's acceptance gate counts against it, so an off-by-two
  enumeration will trip the plan's own Tolerance (ambiguity / count mismatch)
  and stall the implementer hunting for two nonexistent occurrences.

- B2 (Pandalump): Line 239 is a double-hit, not a single `novel-compile`. The
  plan's Work item 1 expected output (line 416-418) and Artifacts block
  (line 612-615) mark only `230 (×2)` as a two-token line and present line 239
  as a lone `novel-compile`. In fact line 239 carries BOTH `novel-compile` and
  `novel-state set-chapters`, reading (pre-sweep):
  `` `novel-compile` follows. It is written only by ``
  `` `novel-state set-chapters` when ``.
  Work item 2's instruction list (lines 455-457) does separately catch
  `novel-state set-chapters` at line 239, so the per-edit instructions are
  complete — but the enumeration "contract" that Work items 1 and 5 audit
  against under-counts line 239 by one token. Reconcile the enumeration with the
  per-edit list or the count audit in Work item 5 cannot pass cleanly.

## Corrected enumeration (verified live, planning-run date)

state-layout.md convertible tokens = 16 total:
  novel-state ×15 — lines 118, 181, 190, 201, 211, 214, 217, 223, 230 (×2),
                    237, 239, 256, 257, 260
  novel-compile ×1 — line 239
  Two-token lines: 230 (complete-final-pass + set-gate --final);
                   239 (novel-compile + novel-state set-chapters).
done-conditions.md: novel-done ×5 — lines 17, 18, 141, 144, 145 (plan correct).
critic-personas.md: novel-done ×2 — lines 131, 133 (plan correct).
Preserve (desloppify noun): state-layout 167, 168; done-conditions 110, 191;
  critic-personas 162 (plan correct; genuine running-prose noun forms).

## What is sound (no change needed)

- Deterministic/judgemental boundary (ADR 001), state.toml-write discipline,
  exit-code and gate-ratio contracts: untouched. Correctly identified as a prose
  sweep only.
- Surface vocabulary verified against source: `names.py` `SUBCOMMAND_NAMES` =
  ("novel state", "novel done", "novel compile", "novel desloppify",
  "novel wordcount"). Every verb the references use (`set-chapters`, `set-gate`,
  `set-fangirl`, `set-critic-pass`, `complete-final-pass`, `recount`, `check`,
  `init`, `reconcile`) is a registered `novel state` subcommand, so the spaced
  conversions are truthful. ADR 007 line 92's six-verb list is illustrative, not
  exhaustive — not a defect.
- Test-body safety bet holds. `_state_layout_scanner.py` forbids only write
  recipes inside executable fences and does not require the `novel-state`
  literal. `test_state_layout_schema_guard.py` extracts the `toml` schema fence
  and matches only `name =` field lines and the `[[chapters]]` header — line
  118's `novel-state set-chapters` lives in a TOML *comment* inside that fence
  and is never inspected. `test_working_corpus.py` parses the phase-enum block
  (carries no command name). Converting the command literals cannot turn
  `make all` red.
- cuprum / Cyclopts / pytest-xdist / uv: correctly ruled non-load-bearing. No
  external-library behaviour is exercised; the only contract is the in-repo
  surface vocabulary, which is verified above. No firecrawl citation needed.
- Scope exclusion of `tests/` literals is correct: roadmap 1.2.8.5 explicitly
  owns them and places them "outside the skill/novel-ralph/references/ scope of
  1.2.17".
- Gates (`make markdownlint`, `make nixie`, `make all`) all exist in the
  Makefile; MD013 line_length is 80 (`.markdownlint-cli2.jsonc`), so the
  80-column claim is correct.

## Advisory (non-blocking)

- A1 (Doggylump): Work item 5's noun-form gate `grep -nE 'novel desloppify'`
  expects empty, but the registered subcommand spelling really is
  `novel desloppify` (a valid surface form). If a future edit legitimately
  introduced `novel desloppify` it would be flagged as a mis-sweep. For this
  task the references contain no such token, so the gate is fine, but the gate's
  rationale comment should note it is asserting "no noun form was converted",
  not "the string novel desloppify is forbidden".
- A2 (Dinolump): The plan twice re-derives the same enumeration (Work item 1
  expected output and the Artifacts block). Keep one canonical copy to avoid the
  two drifting — the present B1/B2 defect exists in both.
