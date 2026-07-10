# Logisphere design review — roadmap 7.1.2 (docstring consolidation) — Round 1

Verdict: REVISE. The plan is documentation-only and well-structured, but its
core factual premise is stale: it inherited the "four docstrings" enumeration
from audit-3.1.3/4.1.2, which both pre-date roadmap task 7.1.1. Task 7.1.1
(completed) added `compile_is_current`, whose docstring now carries a **full
restatement of both absent-file polarities**. The plan never surveys the current
tree, so its success criterion ("exactly one full copy of the projection table")
and the roadmap's ("described authoritatively once; no fourth full copy remains")
are both false after the plan's edits as written.

## Blocking defects

### B1 — `compile_is_current` is an unaccounted full copy of the projection table

`novel_ralph_skill/state/compile_model.py` lines 90-108 (`compile_is_current`)
states both polarities in full:

- content polarity: "only `MATCHES` means `compiled.md` is current; both `ABSENT`
  and `DIVERGES` are not" (lines 93-100);
- the detector's OPPOSITE polarity: "The §5.4 detector deliberately uses the
  **opposite** polarity inline (`is not CompiledComparison.DIVERGES`: an absent
  compile is vacuously satisfied), which is a genuinely different projection"
  (lines 102-107).

This is the same projection-table prose 7.1.2 exists to consolidate. It was
introduced by roadmap 7.1.1 (`docs/roadmap.md` line 2456, `[x]`), which both
audits predate, so neither audit's "four docstrings" list includes it. After the
plan's WI1-WI4 the table would still live in TWO docstrings (`compiled_matches_drafts`
and `compile_is_current`), not one. The plan must either (a) consolidate
`compile_is_current`'s polarity prose into the authoritative docstring and reduce
it to its own one-sentence note, adding it as a fifth work item; or (b) record an
explicit, defended Decision-Log entry for why `compile_is_current` is exempt
(e.g. it is the *named seam for the content polarity*, so stating that one
polarity is arguably its own contract) AND trim only its restatement of the
detector's opposite polarity, which is unambiguously shared prose. Either way the
plan's Purpose, Constraints (Tolerances "four source files"), Progress, and
success criterion must be reconciled with this file. As written the success
criterion is unachievable.

### B2 — WI3 describes prose that does not exist; the duplication claim is overstated for `_check_compiled_matches_drafts`

`novel_ralph_skill/state/disk_evidence.py` lines 194-208
(`_check_compiled_matches_drafts`) is already a self-projection: it states the
shared-seam reference + the D-READ read-and-join rule, its OWN polarity
(`DIVERGES` = violation, `ABSENT` trivially satisfies), and the oracle-twin note.
It does NOT restate the other caller's polarity and carries NO full three-valued
table. The plan's WI3 says to "Replace the longer projection-table restatement
with a single self-projection" (line 407) and its Context (line 263) claims the
shared prose to cross-reference is "the explanation of the three-valued verdict
and the contrast with the other caller's polarity" — neither is present. WI3 is
therefore either a near no-op or an invented edit. The plan must re-state WI3
against the actual docstring: at most it can add an explicit cross-reference
sentence ("see `compiled_matches_drafts` for the full table"), but there is no
duplicated table to remove. The Purpose's claim that the prose "was copied into
four docstrings" overstates this site.

### B3 — the `CompiledComparison` class-docstring exemption is asserted, not reconciled with the audit it cites

The plan (lines 240-247) decides to leave `CompiledComparison`'s class docstring
(lines 49-58) untouched, but audit-3.1.3 Finding 3 — which the plan cites as its
mandate — explicitly counts that class docstring among the duplication sites
(audit-3.1.3 lines 132-141: "in `CompiledComparison`'s class docstring ... lines
48-49"). The plan's exemption may be defensible (the class docstring describes
*why three states* and only references the per-caller polarity rather than
restating the table), but the plan presents it as settled fact while contradicting
its own cited source. This needs an explicit, evidenced Decision-Log reconciliation
that quotes the actual class-docstring text (lines 51-58) and shows it states the
type rationale, not the full polarity table — otherwise a downstream auditor will
re-open it. Severity is lower than B1/B2 but it is a correctness gap in the plan's
justification.

## Verified-sound (so the next agent need not re-check)

- No doctest execution: `pyproject.toml`/`Makefile` carry no `--doctest-modules`;
  module docstrings are not run as doctests. WI0's posture is correct.
- No production-docstring-text assertion in `tests/`. The single grep hit
  (`tests/test_compile_e2e.py:13` "vacuously satisfied") is inside a *test module
  docstring* describing behaviour, not an assertion against production docstring
  text — benign. WI0's grep will surface it; the plan should note it is benign so
  the implementer does not stall.
- Named test pins exist: `test_disk_evidence.py::test_compiled_matches_drafts_projection`
  (line 181), `test_done_predicate.py::test_compile_consistent_present_coherent_and_absent`
  (line 143). The other four named suites exist as files.
- `interrogate` `fail-under = 100` confirmed (`pyproject.toml` line 309); trimming
  to one sentence keeps non-empty docstrings, so the coverage gate holds.
- `compile_model.py` is 245 lines; the 400-line AGENTS.md limit holds with room.
- Make targets `all`, `lint-python`, `markdownlint`, `nixie` exist.
- The deterministic/judgemental boundary (ADR-001) is not touched: this is
  doc-only, no control flow or exit codes change. No contract is altered.
- Roadmap line 2486 is `- [ ] 7.1.2.` as the plan states; WI5's edit target is
  correct. The roadmap success text matches the plan's success criterion (and is
  therefore equally blocked by B1).

## Pre-mortem

Six months on, an audit of 7.x re-flags the projection-table duplication because
`compile_is_current` still carries both polarities. Root cause: the plan trusted
the audits' stale "four docstrings" enumeration instead of re-surveying the tree
after 7.1.1 landed `compile_is_current`. The blast radius is small (doc-only) but
the slice would have shipped not meeting its own success criterion, and the
roadmap checkbox (WI5) would have been ticked falsely. Prevention is designed in
by B1: add a survey step to WI0 ("grep the whole `compile_model.py`/consumers for
every docstring that names *both* polarities or the absent-as-satisfied contrast,
and reconcile each against the keep/move split") and an explicit handling of
`compile_is_current`.

## Alternatives checkpoint (Wafflecat)

Strongest alternative: make `CompiledComparison`'s **class docstring** the
authoritative table instead of `compiled_matches_drafts`. The class is the type
every consumer imports and the most natural home for "what the three states mean
and how callers project them". Trade-off: the helper docstring is where audit-3.1.3
proposed putting it and where the existing prose already lives, so the chosen
location minimizes churn; the class-docstring alternative would require moving
prose into the type and trimming the helper too. Not better, but it would resolve
B3 by construction (the class becomes the seam rather than an awkward exemption).
The plan should at least acknowledge this option in its Decision Log given B3.

## Required next steps (ordered)

1. Re-survey the current tree (not the audits) for every docstring that restates
   the projection table or names the absent-as-satisfied contrast. Confirm the
   full inventory: class docstring, `compiled_matches_drafts`, `compile_is_current`,
   `compile_consistent`, `_check_compiled_matches_drafts`, `check_compiled`.
2. Resolve B1: add a work item for `compile_is_current` (consolidate or defend an
   exemption), and update Purpose/Tolerances/Progress/success accordingly.
3. Resolve B2: rewrite WI3 against the actual `_check_compiled_matches_drafts`
   docstring; drop the "remove the longer restatement" framing.
4. Resolve B3: add an evidenced Decision-Log entry quoting the class-docstring
   text and justifying its exemption (or fold it in).
5. Note the benign `test_compile_e2e.py:13` grep hit in WI0 so the implementer
   does not stall on it.
