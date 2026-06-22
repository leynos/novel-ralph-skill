# Logisphere design review — roadmap 1.3.2 (round 3)

Adversarial pre-implementation review of `docs/execplans/roadmap-1-3-2.md`
(Status: DRAFT, revised round 3). Verdict: **Proceed.** The single round-2
blocking defect (D1, the spec-type import contract) is genuinely resolved, and
every prior fix and factual claim re-verifies against source. Two advisories
remain; neither is blocking.

Documents relied on: `docs/novel-ralph-harness-design.md` §3.4, §4.2, §4.3,
§5.1, §5.2, §5.4, §9, §10; `skill/novel-ralph/references/state-layout.md`;
`docs/developers-guide.md` "Shared test scaffolding" (the carve-out paragraph,
lines 39-52); `AGENTS.md` lines 24-27, 145-147; `tests/conftest.py` (the
existing `TYPE_CHECKING` re-export of `Program` and the
`from conftest import RepoTextReader` consumers); `pyproject.toml`
(`[tool.pytest.ini_options]`, default import mode, no `tests/__init__.py`);
`Makefile` (`ty` typechecker, `PYTHON_TARGETS = novel_ralph_skill tests`);
`/data/leynos/Projects/cuprum/`; `docs/execplans/roadmap-1-3-2.review-r1.md`,
`.review-r2.md`. Skill: `logisphere-design-review`.

## D1 resolved (verified)

Round 2 objected that a test importing
`from working_corpus import WorkingTreeSpec` (even under `TYPE_CHECKING`) was
an *extension* of the carve-out, not the carve-out, and that "no amendment"
contradicted Work item 5 writing a new clause. Round 3's resolution (a) fixes
both:

- The test-facing import is now the **verbatim** sanctioned form
  `from conftest import WorkingTreeSpec` under `if TYPE_CHECKING:`
  (developers-guide lines
  39-52). The spec types stay *defined* in `tests/working_corpus.py`;
  `tests/conftest.py` **re-exports** them inside its own `TYPE_CHECKING` block.
  The only runtime import edge is the `TYPE_CHECKING`-guarded
  `conftest → working_corpus`, which is `False` at runtime and mirrors
  conftest's existing `from cuprum.program import Program` (line 33). No
  runtime cross-module import is introduced anywhere; the no-value-import
  contract holds.
- Work item 5 is now explicitly *descriptive* — it "records how the corpus
  applies the already-stated rule" and carries an escalation guard if the
  carve-out "appears to genuinely require extension." The round-2
  self-contradiction (no-amendment vs writing a new clause) is gone.

Every other factual claim re-verifies: the phase enum, invariants 1-7
(including invariant 4's three sub-clauses — `convergence_target ≥ 1` rejection
and the chapters-drafted bound, design §5.2 lines 439-444 — which the new
`consecutive-clean-over-chapters-drafted` and `convergence-target-below-one`
variants exercise), the §4.3/§9 content-hash compile model and the
`CORPUS_SEPARATOR` hedge, the string-keyed `by_chapter` form (state-layout line
114), the 0.30/0.50/0.80 gate thresholds, the empty-`touch` `done.flag`, the
two-key `[pending_turn]` shape (§3.4 lines 227-235), and the cuprum
non-dependency (§9 line 711; conftest's cuprum fixtures untouched). No
memory-based locked-library claim is made or relied upon: scope is `pathlib` +
`tomlkit` + `pytest`, all locked, with the one external behaviour (pytest
"Factories as fixtures") cited to the stable docs.

## Advisories (not blocking)

### A1 — make the `from conftest` re-export resolution an explicit acceptance check, not an only-on-failure Tolerance (Telefono / Doggylump)

The whole D1 resolution rests on `ty` resolving an **implicitly re-exported**
name: a test does `from conftest import WorkingTreeSpec`, but `conftest` itself
only obtains `WorkingTreeSpec` via `from working_corpus import …` under its
`TYPE_CHECKING` block, with no `as`-alias and no `__all__`. This pattern is
**unproven in this repo**: the existing `from conftest import RepoTextReader`
consumers work because `RepoTextReader` is *defined* in conftest; the only
existing third-module re-export (`Program`) is consumed *only inside conftest*,
never by a test. Strict checkers can treat a plain `from x import Y` as a
private import that is not re-exported, and flag the test's
`from conftest import WorkingTreeSpec` as accessing a name conftest does not
export.

The plan hedges this correctly with the Import-contract Tolerance (lines
350-354: "If the `from conftest` re-export appears not to work … stop and
escalate"), which is the sanctioned posture for a locked-tool behaviour the
plan cannot verify from docs — pin it with the gate and escalate on failure.
But the plan provides no *explicit* acceptance criterion or test that the
import resolves clean under `ty`. Strengthen it: add a deliberate red/green
acceptance check (write `from conftest import WorkingTreeSpec` in a test
annotation, run `make typecheck`, confirm `ty` resolves it) so the contract is
verified by the gate, not merely assumed to be caught by it. If `ty` rejects
the implicit re-export, the documented fallback is an explicit re-export in
conftest (`from working_corpus import WorkingTreeSpec as WorkingTreeSpec`, or a
`TYPE_CHECKING`-scoped `__all__`), which keeps the test-facing `from conftest`
form intact — record this fallback so the implementer does not reach for the
forbidden `from working_corpus` test import under gate pressure.

### A2 — `baseline_tree` and `corpus_invariant_names` fixtures are consumed but never declared in a work-item body (Pandalump)

Work item 3's tests consume a `baseline_tree` factory fixture (line 869) and a
`corpus_invariant_names` fixture (line 874), and both appear in the end-state
surface (lines 1106, 1112) and Work item 5's docs list. But neither is declared
in any work item's "Edits/new code": Work item 2 creates `phase_state_tree` /
`phase_names`; Work item 3 creates `incoherent_variant_names` /
`incoherent_tree` / `check_corpus`. `baseline_tree` (wrapping
`COHERENT_BASELINE`, defined in Work item 2) and `corpus_invariant_names`
(wrapping `CORPUS_INVARIANT_NAMES`, defined in Work item 3) are trivially
derivable, so the plan is implementable as written — the surface lists both
with signatures. But the work-item bodies should declare where each fixture is
created (both belong in Work item 3's conftest edits) so the implementer is not
left to infer them from the surface block.

## Pre-mortem (Doggylump)

Six months on, phase 2 lands. Most likely incident: `ty` (or a later checker
bump) rejects the implicit re-export, the implementer is under gate pressure,
and — finding `from conftest import WorkingTreeSpec` red — reaches for the
forbidden `from working_corpus import WorkingTreeSpec` in the test, re-opening
the very B2/D1 contract the three rounds closed. Blast radius: every phase-2-6
consumer that copies the pattern. Missed signal: the corpus self-test stays
green (it exercises trees, not the import contract). Prevention: A1 — make the
`from conftest` resolution an explicit typecheck acceptance check with a
recorded conftest-side fallback, so the gate proves the contract and the
implementer never has to improvise the forbidden import.

Secondary scenario unchanged from round 2: a phase-2 consumer needs a chapter
reference file (`critic-notes.md`) the builder never wrote — now mitigated by
the round-3 "What this task does NOT do" statement (deliberate narrow file set,
with an escalation path).

## Alternatives checkpoint (Wafflecat)

No materially stronger alternative than the calibration carried since round 1
(drop the bespoke oracle; prove the split structurally by mutation of
`COHERENT_BASELINE`). Round 3's stable `CORPUS_INVARIANT_NAMES` vocabulary
keeps the oracle's 2.1.2 cross-check real, so the oracle remains a defensible
choice. A simpler variant on D1 worth noting for the record: define the two
spec types *directly in `conftest`* and have `working_corpus` import them from
conftest at runtime — rejected by the plan (correctly) because that runtime edge
`working_corpus → conftest` is the forbidden cross-module value import; the
re-export keeps the edge pointing the sanctioned direction.

## Verdict

**Proceed.** D1 is genuinely resolved in the verbatim words the guide carries,
with no amendment and no runtime cross-module import; all factual claims hold
against the design, `state-layout.md`, `AGENTS.md`, the cuprum source, and the
locked tool set. The two advisories (make the re-export resolution an explicit
typecheck acceptance check with a recorded conftest-side fallback; declare the
two undeclared fixtures in a work-item body) tighten the plan but do not gate
it: it is implementable and design-conformant as written.
