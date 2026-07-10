# Logisphere design review — roadmap 3.1.5 ExecPlan (round 1)

Reviewer: adversarial Logisphere crew (Pandalump, Wafflecat, Buzzy Bee,
Telefono, Doggylump, Dinolump) plus pre-mortem and alternatives checkpoint.
Verdict: **Proceed** (no blocking defects). Advisories only.

## Verification trail (every load-bearing claim checked against source)

- Diagnosis confirmed. `done_predicate.py:276-296` uses
  `stripped.startswith("BLOCKER") and not stripped.endswith("[resolved]")`;
  `critic-personas.md:81-104` emits `## BLOCKER` + `### B1 — <label>` and the
  `No BLOCKER. No MAJOR.` sentinel (116-118). No emitted line stripped-starts
  with bare `BLOCKER`, so the clause matches zero lines and reads clean — the
  exit-0 lie. Matches audit-3.1.4 Finding 1 (high) verbatim.
- All cited anchors are accurate: `done-conditions.md:191-195` (current
  grammar), `developers-guide.md:571-583` ("The BLOCKER format"), design §4.2
  status block 310-322, `test_done_predicate.py:241-330`,
  `_done_predicate_specs.py:60-177` (the four note constants),
  `_done_predicate_oracle.py:36-85`, `_builder.py:166-182` (writes
  `critic_notes` verbatim), SKILL.md:341-367 (loop overwrites notes; converges
  on sentinel), `novel_done.feature:30-34`, `_disk_paths.py` (relocation
  precedent for D-BLOCKER-MODULE).
- File size: `done_predicate.py` is **350** lines (plan says 351 — harmless
  off-by-one). R-FILESIZE and D-BLOCKER-MODULE escape hatch are well-judged.
- Locked-library brief requirement discharged correctly: the predicate is pure
  `str`/`pathlib`; no cuprum/Cyclopts/pytest-timeout/uv surface is load-bearing
  (grep of the module confirms no `cuprum`/`subprocess`; `cyclopts` import is in
  the command layer, untouched). The plan does not lean on any uncited
  memory-based external-library claim, so nothing needs firecrawl citation.

## Crew findings (all advisory)

- A1 (Telefono/Doggylump). The `[resolved]` in-place token is, by the plan's own
  W0 fact 2, exercised only on the cap-reached "log unresolved findings" path and
  by the corpus — in the normal loop a resolved blocker *vanishes* (notes
  overwritten; convergence is the sentinel). SKILL.md:360 logs unresolved
  *MAJOR* at the cap, not BLOCKER, and never instructs writing `[resolved]`.
  W1 *adds* the missing instruction, which is the correct closure, but the
  convention's only live producer is the cap path. W1 should state plainly, in
  `critic-personas.md`, *when* the loop writes the token (the cap-reached logged
  case) so the contract is not decorative. Not blocking — the plan already names
  this; make it explicit in the prose.
- A2 (Pandalump). "Under a `## BLOCKER` section" is left on "the next `##`-level
  heading". `### B1` is `###` (three hashes), `## MAJOR` is `##` (two). Ensure
  `_body_has_unresolved_blocker` leaves the section on a `##`-prefixed line that
  is **not** `###` — i.e. test `line.startswith("## ")` semantics so a `###`
  finding does not falsely close the section. W2's
  `test_finding_outside_blocker_section_is_clean` covers the positive direction;
  add an assertion that a `### B1` finding *after* a later `## MAJOR` is clean,
  and that a second `## BLOCKER`-then-`### B2` is still caught. Advisory.
- A3 (Wafflecat, alternatives checkpoint). Strongest alternative: an inline
  `BLOCKER:`/`BLOCKER … [resolved]` single-line form (audit Finding 1 lists it as
  an option) instead of the heading-aware parser. It is simpler (keeps the
  line-rule) but **rejected correctly** — it would require the critic to emit a
  shape it is not specified to produce, reintroducing the exact producer/consumer
  divergence this task closes. The heading-based grammar matches the real
  producer format; no credible alternative beats it. Recorded for calibration.
- A4 (Buzzy Bee). Scaling is a non-issue: O(lines) per chapter, pure in-memory,
  bounded by 25 findings/pass. No concern.
- A5 (Dinolump). The oracle-twin re-spelling (Constraint 5) must independently
  re-implement section tracking, not copy the production helpers. W3 says so.
  Confirm the twin parses `## BLOCKER`/`### Bn` with its own walk; a copy would
  void the cross-check. Advisory, already in-plan.
- A6 (Hypothesis). The rewritten positional property over
  `_line_is_unresolved_blocker_finding` must keep dodging the filtering trap
  (round-1 A1 carried over): construct a fixed `### B1 —` prefix, alphabet
  excluding `[`,`]`,newline, fixed non-space mid-line sentinel. Plan states this.

## Pre-mortem (Doggylump)

Six months on, the loop hangs on a chapter that hit the pass cap with a live
BLOCKER logged in `critic-notes.md`: `no_unresolved_blockers` is False forever
unless the agent marks it `[resolved]`. **This is by design** — the clause exists
to keep the loop running on unresolved blockers — and is pre-existing, not
introduced here. The risk this task *removes* is the opposite (false-clean) lie.
Mitigation already designed in: W1 documents the `[resolved]` escape so the cap
path has a defined way out; A1 asks only that W1 say so explicitly.

## Conclusion

The plan is implementable and design-conformant as written. Work items are
atomic, correctly ordered (contract → recognizer+unit → corpus/oracle/BDD →
docs), each independently committable and gated by `make all` (plus
`markdownlint`/`nixie` for prose). Validation is specified per item with
red-before-green evidence. Nothing contradicts ADR-001 (read-only), the D-FAULT
boundary, the six-clause set/order, or the deterministic/judgemental boundary.
Address advisories A1–A2 in prose/tests during implementation; none block.
