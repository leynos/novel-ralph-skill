# Logisphere design review — roadmap 3.1.4, round 1

Adversarial pre-implementation review of `docs/execplans/roadmap-3-1-4.md`
(anchor unresolved-BLOCKER resolution positionally; cover the false-clean
direction).

Verdict: **Proceed with conditions.** The plan targets a real soundness bug,
its load-bearing facts verify against source, and the grammar choice is sound.
One blocking implementability gap (the `blocker_edge_trees` fixture arity) and
several advisory tightenings.

## Verified against source

- The bug is real. `done_predicate.py:288` uses
  `_RESOLVED_TOKEN not in stripped`; the false-clean counter-example
  (`BLOCKER … the [resolved] issue in chapter 2`) is wrongly cleared.
- Both existing notes are compatible with `endswith`:
  `RESOLVED_BLOCKER_NOTE` ends with `[resolved]` (stays clean); `UNRESOLVED`/
  `NEAR_MISS` carry no token (stay unresolved).
  (`_done_predicate_specs.py:62,66,70`).
- The oracle twin re-spells the same substring rule
  (`_done_predicate_oracle.py:64`) and is pinned equal to production by
  `test_blocker_oracle_twin_agrees`
  (`tests/test_working_corpus_done_predicate.py:123`).
- `tests/test_done_predicate.py` already imports `given/settings/st`
  (lines 27–28) and carries the BLOCKER unit tests at 240–267.
- W4 doc targets verify: developers-guide BLOCKER paragraph at 566–571;
  done-conditions.md reference at ~181–185 pins no grammar; design §4.2
  impl-status note at 309–317.
- `xfail(strict=True)` has repo precedent
  (`test_novel_state_mutators.py:17`, `test_working_corpus.py:523`).
- AGENTS.md line 67 ("failing test before the fix") and line 153
  (snapshot-only guidance) exist as cited.

## Blocking

### B1 (Doggylump / Telefono) — W3 step 4 breaks the `blocker_edge_trees` contract

The plan says "Extend `blocker_edge_trees` … to also build the
incidental-resolved tree." But that fixture is typed
`cabc.Callable[[], tuple[Path, Path]]` and has **two** consumers that
destructure exactly two elements:

- `test_blocker_edges` (`…done_predicate.py:90-97`):
  `resolved, near_miss = blocker_edge_trees()` and asserts a per-tree verdict.
- `test_blocker_oracle_twin_agrees` (`…done_predicate.py:123-136`):
  `cases.extend(blocker_edge_trees())`.

Changing the fixture to a 3-tuple silently breaks `test_blocker_edges` (unpack
arity) and the fixture/consumer type annotations. The plan asserts the
cross-check "now covering the incidental tree" without specifying these
mechanical edits, so as written W3 does not pass `make all`. The plan must name
the edits: update the fixture return type to `tuple[Path, Path, Path]` (or
return a name-keyed mapping), update `test_blocker_edges` to unpack and assert
the third tree
(`incidental.failed_clause_names == ("no_unresolved_blockers",)`), and keep
`test_blocker_oracle_twin_agrees`'s `extend` working. Without this the
"cross-check covers the new tree" claim is unbacked and the W3 commit fails its
own gate.

## Advisory

### A1 (Telefono) — W2 Hypothesis strategy under-specifies the filtering trap

The dual property builds `f"BLOCKER {prefix} {_RESOLVED_TOKEN} {suffix}"`
(assert False) and `f"BLOCKER {prefix} {_RESOLVED_TOKEN}"` (assert True).
Because the production rule is `line.strip().endswith(_RESOLVED_TOKEN)`, the
False case is only valid when `suffix` survives `.strip()` — a whitespace-only
`suffix` strips away and flips the verdict to True, failing the assertion. The
plan gestures at this ("non-empty suffix of visible, non-whitespace-terminated
text … filtered to exclude a trailing-token collision") but does not pin the
exact constraints: (a) `suffix` must contain at least one non-whitespace char
*and* not be whitespace-terminated, (b) `prefix`/`suffix` must exclude newlines
(a newline splits the line), and (c) `prefix` must not itself produce a line
ending in the token. Per the `hypothesis` skill's filtering-trap guidance,
prefer *constructing* valid inputs (e.g. append a fixed non-space sentinel to
`suffix`) over `.filter()`. Spell these out so the property does not flake on
the first adverse example.

### A2 (Pandalump) — W1 xfail-then-remove adds two commits for a one-line fix

W1 lands a `xfail(strict=True)` red test as its own commit, W2 removes the
marker. This satisfies "failing test before the fix" but inflates a ~1-line
soundness fix to two commits and a marker churn. The plan already offers the
fold-into-W2 escape hatch; given repo precedent lands the failing test and fix
together where the gate allows, prefer folding W1 into W2 (failing test added
unmarked, immediately turned green by the same diff) unless the reviewer
specifically wants the recorded red commit. Either is acceptable; flagging so
the implementer picks deliberately rather than defaulting to the heavier path.

### A3 (Doggylump) — W3 step 5 BDD step wiring is conditional and unverified

The plan says wire the Given step "reusing the existing tree-builder step
machinery; add a step only if no parameterised tree-by-name step exists." The
existing `single_failer_tree` step is keyed off `DONE_PREDICATE_FAILERS[clause]`
(`novel_done_steps.py:89-98`), not an arbitrary tree-by-name, and the new
incidental tree is **not** a failer in that dict. So a new Given step (or a new
dict entry) is required, not optional. State this definitively so W3 does not
stall discovering the machinery does not generalise.

### A4 (Buzzy Bee / Wafflecat) — snapshot decision deferred to implementer

W3's snapshot extension is gated on "only if it captures a meaningful contract."
`tests/test_novel_done_snapshots.py` snapshots the machine-mode envelope with
semantic assertions (it already lists `no_unresolved_blockers` at line 43). The
incidental tree produces the same envelope shape as the existing
`no_unresolved_blockers` failer, so a snapshot adds little beyond the BDD
assertion — skipping it is defensible. No change required; recording that the
deferral is sound, not a gap.

### A5 (Wafflecat) — alternatives checkpoint

The strongest alternative is the structured-marker grammar (a `## RESOLVED`
section or per-finding `[resolved B1]` back-reference) that matches the real
`critic-personas.md` section format. The plan correctly defers this
(D-BLOCKER-SCOPE / D-BLOCKER-POSITIONAL) as a larger redesign beyond a
low-severity step-task, and records the grammar-vs-critic-format mismatch as a
known limitation. This is the right call for the task's scope; the
trailing-marker grammar is the minimal sound fix.

## Pre-mortem

- Most likely failure: W3 lands, `make all` fails on the broken
  `test_blocker_edges` unpack (B1). Blast radius: one commit, caught by the
  gate — but only after the implementer has already restructured the fixture.
  Prevention: B1 names the consumer edits up front.
- Second: the W2 property flakes on a whitespace-only `suffix` (A1). Caught
  by Hypothesis on first run; wastes an iteration. Prevention: construct valid
  suffixes rather than filter.

## Design-boundary conformance

- Read-only invariant preserved: change is in-memory line classification
  only; no write introduced (ADR-001; design §3.3). ✓
- Fault boundary untouched: `try/except FileNotFoundError` unchanged; the
  `endswith` swap cannot swallow or raise a new fault. ✓
- Clause set, order, and `DoneClauses` shape unchanged. ✓
- Deterministic/judgemental boundary respected: no narrative judgement
  added. ✓
- No new dependency; libraries used (`pytest`, `pytest-bdd`, `hypothesis`,
  `syrupy`) already in the suite — no memory-based locked-library claim to
  cite. The D-BLOCKER-NO-NETWORK rationale is sound: this change runs no
  subprocess, so cuprum/Cyclopts/uv/pytest-timeout behaviours are not
  load-bearing.
