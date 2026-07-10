# Logisphere Design Review — roadmap 2.3.7, Round 2

Reviewer: adversarial Logisphere crew (Pandalump, Wafflecat, Buzzy Bee,
Telefono, Doggylump, Dinolump) plus pre-mortem and alternatives checkpoint.
Date: 2026-06-26.

Verdict: **PROCEED**. The two Round-1 blocking defects (B1, B2) are genuinely
resolved, not papered over. Advisories A1-A5 are folded in. Every load-bearing
claim was re-verified against real source (`validate.py`, `_state_mutators.py`,
`_recount.py`, `contract/errors.py` + `runner.py`, `_gate_drafting_mutators.py`,
the e2e file, the cuprum read-only sibling, the Makefile/pyproject test config,
and
all four documentation surfaces). No blocking defects remain. The findings
below are advisory polish only.

## Verification trail (re-checked against real source this round)

- `_check_gate_ratio_consistent` (validate.py 250-278): numerator
  `sum(by_chapter.values())`, `target <= 0` short-circuit, name
  `GATE_RATIO_CONSISTENT`, current detail
  `f"knitting gates {flags} disagree with drafted ratio {ratio:.4f} against
  thresholds {GATE_THRESHOLDS}"`. `GATE_THRESHOLDS = (0.30, 0.50, 0.80)`
  (line 76). All as the plan states.
- `_refuse_if_incoherent(state, *, context)` (_state_mutators.py 142) raises
  `StateInputError(summary, *details)`; recount calls it at _recount.py 149.
  Confirmed. Adding a backward-compatible `remedy=None` keyword (shape 2)
  cannot disturb existing callers.
- `EnvelopeMessagesError.__init__(*messages)` (contract/errors.py 30) stores
  varargs prose; `StateInputError` subclasses it (runner.py). Appending remedy
  lines as extra `messages` entries is contract-legal. Confirmed.
- cuprum 0.1.0 (read-only /data/leynos/Projects/cuprum): `make` (sh.py 528),
  `run_sync` (sh.py 441/509), `ExecutionContext` (sh.py 169), `capture`
  (sh.py 281), `ProgramCatalogue` (catalogue.py 59). All present; the e2e
  reuses the surface the existing `test_recount_e2e.py` already drives.
- pytest-timeout under pytest-xdist: Makefile runs `pytest -v -n
  $(PYTEST_XDIST_WORKERS)` (default `auto`); `pytest-timeout` is a declared dev
  dep; project default `timeout = 30` (pyproject 327); the existing slow e2e
  carries `@pytest.mark.timeout(180)` and passes under this config. Proven
  in-repo pattern, not a memory claim. Acceptable — no firecrawl citation
  required because the behaviour is pinned by a passing test in this repo.
- Cyclopts flag mapping (_gate_drafting_mutators.py 70-74): `_KNITTING_KEYS`
  pairs Cyclopts param `knitting_30` with disk key `done_30` (and 50/80);
  Cyclopts renders the param as `--knitting-30`. Remedy text `gate done_NN …
  set-gate --knitting-NN` is consistent (`done_NN` is the disk key the operator
  sees; `--knitting-NN` is the repair flag).
- design §5.4 recovery rule 1 (harness-design.md 600-611): recount/reconcile
  rewrite `[word_counts]` only, never `[gates]`; "A done-claim large enough to
  move a gate is reported and escalated, not silently re-projected." The plan
  respects this boundary exactly — it makes the *report* actionable without
  performing the judgemental gate flip.
- ADR-001 (deterministic-judgemental boundary) and ADR-010 (gate-drafting
  mutators) exist as cited; both support "remedy points at a verb, never a
  hand-edit".
- Documentation line references (users-guide 241-249 / 285-298; developers-
  guide 605-625; skill state-layout 205-219) are accurate. The set-gate
  paragraph already calls itself "the **repair** for a gate that lags its
  ratio", confirming A1's scoping to a forward cross-link.

## B1 — RESOLVED

The message template is now fully pinned: two line forms (upward / downward),
worked examples for 30/50/80 upward and 80 downward, and an explicit list of
the load-bearing acceptance substrings. Shape 2 (the `remedy` callable keyword
defaulting to `None`) is committed, validating once on the refusal path. The
behavioural and e2e substring assertions are now derivable from the plan, not
reverse-engineered. This is a plan, not a wish.

## B2 — RESOLVED

The downward line is specified verbatim and deliberately omits `set-gate
--knitting-NN` ("the recorded gate no longer matches the drafts. Adjudicate
…"). Dual-direction coverage now exists at three levels: unit (with the
`"set-gate" not in <downward line>` absence assertion), behavioural (upward +
downward scenarios), and installed e2e (upward + downward, the downward e2e
asserting `"set-gate --knitting-80"` absent from *every* `messages` entry —
stronger than the per-line unit check). The pre-mortem's most-likely incident
(the upward-shaped message leaking into the downward path) is directly tested.
The validator's own detail never contains "set-gate", so the absence assertions
cannot be defeated by the shared detail line.

## ADVISORY (non-blocking — polish; do not gate implementation on these)

- A6 (Telefono) — **caller enumeration is factually incomplete.** The plan
  (Decision Log line 188; Work item 2 line 364; Interfaces line 749) states the
  *only* callers of `_refuse_if_incoherent` are `set_cursor`, `advance_phase`,
  `set_gate`, `reconcile`. The real caller set is larger: also `set-chapters`
  (_set_chapters.py 305), `complete-final-pass`, `set-fangirl`,
  `set-critic-pass` (_gate_drafting_mutators.py 247/294/336), and `reconcile`
  calls it twice (_reconcile.py 146/207). This does **not** weaken shape 2 — the
  `remedy=None` default still protects every caller untouched, so the plan's
  *conclusion* ("no other caller changes") holds. But the plan's *premise* (the
  exhaustive caller list) is wrong; correct it so the implementer does not trust
  a stale enumeration when reasoning about the keyword's blast radius. The R1
  review carried the same incomplete list, so this is inherited, not new.

- A7 (Pandalump) — **`:.0f` vs "two decimal places" wording slip.** Work item 2
  line 384 says the ratio is "rendered to two decimal places as a percentage
  (`ratio * 100:.0f`)". `:.0f` is *zero* decimal places; it yields the
  whole-number percentages the worked examples and acceptance substrings use
  (34%, 55%, 86%, 0%). The format spec, worked examples, and substrings all
  agree with each other; only the descriptive phrase "two decimal places" is
  wrong. Fix the phrase to "whole-number percentage" so the implementer is not
  misled into emitting `34.00%` and breaking its own substring assertions.

- A8 (Doggylump) — **rounding-display edge near a threshold boundary.** Because
  the percentage is rendered with `:.0f`, a ratio of, say, 0.298 displays as
  "30%" while the downward line says "left drafting below the 30% knitting
  threshold (drafts now at 30% of target)" — a sentence that reads as a
  self-contradiction at sub-percent proximity to a boundary. The pinned trigger
  trees (0.34, 0.55, 0.86, 0.00) all sit clear of boundaries, so no *test* hits
  this, but a real operator near a boundary could. This is cosmetic, not a
  correctness defect (the refusal verdict and exit code are unaffected).
  Optional mitigation: render the ratio with one decimal (`:.1f`) for the
  message only, or note the edge in the Decision Log so a future reader does not
  treat it as a bug. Not blocking.

- A9 (Wafflecat / Buzzy Bee) — **Risk 3 (snapshot churn) is over-hedged: no
  snapshot currently captures the gate-ratio detail.** A grep of
  `tests/__snapshots__` finds the detail string ("disagree with drafted ratio",
  "knitting gates (…") in *no* snapshot; `test_set_gate_snapshots.ambr` and
  `test_novel_state_mutator_snapshots.ambr` do not contain it; the only
  `test_command_surface_matrix.ambr` hits are an unrelated success-path summary
  ("all knitting gates reached"), not the violation detail. The plan's
  conservative "locate every snapshot before editing" instruction is harmless
  and good hygiene, but the implementer can expect zero snapshot churn from
  Work item 1's detail enrichment. State this so the snapshot-update step is not
  treated as load-bearing.

- A10 (Dinolump) — **skill state-layout uses `current`, validator uses the
  drafted sum.** skill/novel-ralph/references/state-layout.md line 207 says
  gates trigger on `word_counts.current / word_counts.target`, whereas the
  validator and developers-guide use `sum(by_chapter.values()) / target`. These
  coincide *after* a recount (which sets `current = sum(by_chapter)`), so the
  skill text is not wrong in practice, but it is a pre-existing terminological
  drift from the §5.2 numerator. Work item 5 edits this very section; the
  implementer should avoid worsening the drift and may align the wording to
  "drafted ratio" in passing. Pre-existing, not introduced by this plan.

## Pre-mortem (Doggylump)

The R1 pre-mortem incident — operator hits the downward refusal, reads "you
crossed the 80% threshold; run set-gate --knitting-80", does it, and corrupts
the gate-integration record — is now closed by B2's resolution: the downward
line is specified to omit the repair verb, and an absence assertion at the
unit, behavioural, and e2e levels prevents the upward-shaped message from
leaking into the downward path. No new six-month incident surfaces. Residual
risk A8 (boundary display rounding) is cosmetic and would not trigger an
operator into a destructive action — the downward line never prescribes a verb.

## Alternatives checkpoint (Wafflecat)

The R1 alternative (enrich only the shared `Violation.detail` to be fully
self-describing and have recount append a single fixed pointer sentence,
sidestepping command-layer branching) remains the safer fallback if the message
matrix proves fiddly. Now that B1/B2 are pinned with a finite, tested matrix
(three thresholds × two directions, single- and multi-gate fan-out), the
proposed design's extra actionability (the named percentage in the
recount-specific line) is earned. The Tolerances already authorize falling back
to shape 1 if shape 2 forces a caller change, and the command-layer branching is
bounded and fully tested, so the proposed design is the right call. No stronger
alternative exists; that is a positive signal.

## Recommended next steps (none blocking)

1. Correct the `_refuse_if_incoherent` caller enumeration (A6) in the Decision
   Log, Work item 2, and Interfaces — the conclusion is right, the list is
   stale.
2. Fix the "two decimal places" phrase to "whole-number percentage" (A7).
3. Optionally note the boundary-rounding display edge (A8) in the Decision Log.
4. Note that no snapshot currently captures the gate-ratio detail (A9) so the
   snapshot-update step is treated as a safety net, not an expected change.
5. While editing skill state-layout.md (Work item 5), avoid worsening the
   `current`-vs-drafted-sum drift (A10).
