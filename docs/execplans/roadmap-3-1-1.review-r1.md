# Logisphere design review — roadmap 3.1.1 ExecPlan — Round 1

Verdict: **Revise**. The plan is well-researched and largely design-conformant,
but it carries one structural soundness defect (the `compile_consistent`
placeholder makes the exit-0 "done" verdict unsound in 3.1.1), one completeness
gap with an internal contradiction (no all-six-clauses-hold corpus tree exists,
and the "no churn" promise collides with the need to build one), and several
citation inaccuracies that would mislead the implementer. Addressing the
blocking items below makes it implementable.

## Verification trail

- Reference predicate: `skill/novel-ralph/references/done-conditions.md`
  ("Novel-level predicate").
- Design §2.3 (predicate truthfulness), §4.2 (`novel-done`), §4.3
  (`novel-compile`, manifest-ordered) of `docs/novel-ralph-harness-design.md`.
- Roadmap tasks 3.1.1 / 3.1.2 / 4.1.x in `docs/roadmap.md`.
- Real source read: `novel_ralph_skill/state/disk_evidence.py`,
  `novel_ralph_skill/state/_disk_paths.py`, `novel_ralph_skill/state/schema.py`,
  `novel_ralph_skill/commands/novel_state.py`,
  `novel_ralph_skill/commands/_desloppify.py`,
  `novel_ralph_skill/commands/stub.py`, `pyproject.toml`, `uv.lock`,
  `tests/working_corpus/_specs.py`, `_builder.py`, `_library.py`.

## Blocking defects

### B1 — The `compile_consistent` placeholder makes 3.1.1's exit-0 verdict unsound (Pandalump / Telefono)

Design §2.3 names "predicate truthfulness" as a verifiable property:
`novel-done` returns "done" only when the §4.2 predicate holds **on disk**.
The §4.2 predicate (and the reference `novel_predicate`) require
`compiled.md` to exist and equal the ordered concatenation of drafts.

D-COMPILE-PLACEHOLDER hardcodes `compile_consistent = True`. The corpus already
models `compiled` as `None` / `COMPILED_AUTO` / stale-bytes
(`tests/working_corpus/_specs.py` `WorkingTreeSpec.compiled`). Therefore 3.1.1
will emit exit `0` with `ok: true` ("novel is done") on a tree whose
`compiled.md` is **absent or stale** — a state the real predicate rejects. The
plan acknowledges the deferral of *exit 4* but never acknowledges that the
placeholder also corrupts the *exit-0* path, which is the more dangerous lie
(declaring a novel done when it is not).

The plan's stated rationale — returning `True` "keeps it from masking the other
five clauses in the all-hold case" — is exactly the unsound choice. Required:
the plan must either (a) state explicitly that 3.1.1's exit-0 path is knowingly
unsound for `compiled.md` until 3.1.2 lands, scope every 3.1.1 all-hold
snapshot/e2e/feature fixture to a tree with a valid `COMPILED_AUTO`
`compiled.md`, and document this unsoundness window in the developers' guide and
the users' guide "v1 caveat"; or (b) have the placeholder read the real
existence/staleness of `compiled.md` as a stop-gap (returning `False` when
`compiled.md` is absent) so exit-0 is never wrongly emitted, deferring only the
hash comparison and exit-4 to 3.1.2. Pick one and pin it; do not leave the
exit-0 lie undiscussed.

### B2 — No all-six-clauses-hold corpus tree exists, and work item 2's "no churn" promise contradicts building one (Pandalump / Doggylump)

The roadmap 3.1.1 success criterion is "the exit code is 0 only when every
clause holds" — which requires a fixture where all six clauses hold. The
existing `PHASE_STATES["done"]` spec (`tests/working_corpus/_library.py`
`_drafting_spec`) sets `phase=done`, `final_pass_complete=True`, all flags, all
gates true, and `compiled=COMPILED_AUTO` — but under D-CLAUSES
`knitting_gates_passed` also needs `reviews/knitting-{30,50,80}.md` to **exist**,
and work item 2 defaults `knitting_reviews` to empty. So with work item 2 as
written, **no tree satisfies `knitting_gates_passed`, and the all-hold case is
unreachable** — the central success criterion cannot be demonstrated.

Resolving this means the `done` (and `final-pass`) library spec must gain the
three review files. But `PHASE_STATES` feeds `test_novel_state_check_disk.ambr`
and the corpus oracle agreement suites, and work item 2 promises "every existing
corpus spec stays byte-identical (no churn in the existing snapshot or oracle
suites)." These two requirements collide. The plan must:

1. Add an explicit work-item-2 step that constructs (or upgrades) an
   all-six-clauses-hold tree — `phase=done`, final gate, all flags, all three
   `knitting-NN.md`, clean/absent `critic-notes.md`, and a valid `compiled.md`.
2. Resolve the churn contradiction honestly: state which existing specs change,
   whether `test_novel_state_check_disk.ambr` (or any builder-output snapshot)
   re-baselines, and confirm the disk-evidence detector ignores `reviews/` and
   `critic-notes.md` so its verdicts (and their snapshots) do not change. The
   blanket "byte-identical, no churn" claim is false as written.

### B3 — Clause-source divergence from the reference predicate is unstated (Telefono)

The reference `novel_predicate` derives planned chapters from
`parse_chapter_outline(working_dir / "plan/chapter-outline.md")` and reads
`reviews/knitting-NN.md` / `manuscript/chapter-NN/critic-notes.md` per **outline
chapter**. The plan instead reads per **manifest chapter** (`State.chapters`).
That substitution is in fact the design-conformant choice — design §4.3 pins
chapter ordering and set to the manifest, not outline prose, and the codebase
has no `parse_chapter_outline` — but the plan presents D-CLAUSES as a faithful
transcription of the reference without flagging that it deliberately departs
from the reference's `parse_chapter_outline` in favour of the manifest. Record
the divergence and its §4.3 justification in D-CLAUSES so a reader comparing the
plan against the reference does not read it as an unacknowledged error, and so a
future reconciliation of `done-conditions.md` is traceable.

## Advisory (non-blocking but fix before implementation)

- A1 (citation): The plan states `disk_evidence.py` "already exposes
  `_chapter_dir_name`" (Context line ~328; Artifacts cites
  `disk_evidence.py:133-161`). `_chapter_dir_name` is defined in
  `novel_ralph_skill/state/_disk_paths.py`; `disk_evidence.py` only imports it.
  The implementer should import from `_disk_paths` (or re-derive), not expect it
  in `disk_evidence`. Correct the citation.

- A2 (citation): The plan repeatedly cites `pyproject.toml:16` as the runtime
  dependency line. Line 16 is a `[project.scripts]` entry (`desloppify = ...`).
  Runtime deps (`cyclopts`, `tomlkit`) are on line 8. Fix the line reference.

- A3 (citation): D-EXTERNAL pins cyclopts behaviour against a **v5-develop**
  docs URL (`cyclopts.readthedocs.io/en/v5-develop/help.html`) while the locked
  version is **4.18.0** (`uv.lock`). The reused runner pattern is already gated
  by `tests/test_contract_runner.py` / `tests/test_cyclopts_contract.py`, so no
  new cyclopts surface is load-bearing and the conclusion stands — but cite the
  v4 docs (or state the pattern is pinned by existing tests, not docs) rather
  than a v5 page for a v4 pin.

- A4 (twin discipline): Work item 2 hedges the oracle-twin obligation with "if
  warranted ... escalate if this balloons." The developers' guide treats
  disk-evidence reads as deliberate twins with an independent oracle
  (`tests/working_corpus/_oracle.py`). The two new disk-reading clauses
  (`knitting_gates_passed` review-existence, `no_unresolved_blockers`
  BLOCKER-scan) are disk-evidence reads of the same shape. Decide up front
  whether they get oracle twins; deferring the decision into the work item risks
  the central twin discipline being silently skipped. Make it a stated decision,
  not a hedge.

- A5 (D-BLOCKER fragility): `[resolved]` as the sole resolution token, matched by
  substring, is brittle — a BLOCKER line quoting the word "[resolved]" in prose,
  or resolution written as "RESOLVED"/"(resolved)", would mis-classify. The plan
  pins one format and routes disputes to escalation, which is acceptable, but
  add at least one corpus spec exercising a near-miss (a BLOCKER whose body
  merely mentions resolution) so the substring rule's edge is pinned by a test,
  not left implicit.

## Pre-mortem (Doggylump)

Six months on, the harness loops forever or stops early on a real novel:

1. **Most likely failure:** 3.1.1 ships, 3.1.2 slips, and an operator runs the
   v1 `novel-done` against a tree with a stale `compiled.md`. The placeholder
   returns `True`, every other clause holds, the predicate exits `0`, and the
   Ralph Loop **stops with a stale manuscript** — the exact "compiled.md is
   stale" failure mode the reference's "Failure modes for the predicate" section
   warns about, now masked by the predicate that was supposed to catch it.
   Blast radius: a shipped novel with a stale compile. Missed signal: there is
   no exit-4 and no exit-0 guard. Wrong bet: "returning True is the safe
   placeholder." Prevention designed-in: B1 option (b) — placeholder returns
   `False` when `compiled.md` is absent/stale — closes this without waiting for
   3.1.2's hash work.

2. **Second failure:** the all-hold feature scenario is quietly never satisfiable
   (B2) because no tree carries the three review files, so the suite proves
   "exits 1 when a clause fails" but never proves "exits 0 when all hold." The
   roadmap success criterion passes on paper while its load-bearing half is
   untested. Prevention: B2.

## Strongest alternative (Wafflecat)

Do not split `compile_consistent` across 3.1.1 / 3.1.2 at all for the
*existence* half. Have 3.1.1 implement the cheap, sound part of the clause —
`compiled.md` exists — and defer only the **hash comparison** and the exit-4
carve-out to 3.1.2. This keeps the exit-0 path sound from day one (a missing
compile yields exit 1, never a false "done"), still leaves 3.1.2 owning the
hash routine and exit-4 branch as the roadmap requires, and turns the
placeholder from a lie into a partial-but-true clause. Trade-off: 3.1.2's swap
touches a two-line function instead of a one-line one, and 3.1.1 must model a
missing-`compiled.md` fixture. Given the soundness gain, the cost is trivial.
This is the recommended resolution of B1.
