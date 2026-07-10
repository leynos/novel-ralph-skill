# Post-merge audit — roadmap task 7.1.1

Audit of the codebase after roadmap task 7.1.1 ("Extract compile-currency
predicate and compiled.md path seam") merged to `main` at commit `e606735`. The
task centralized two things that were hand-repeated across the compile surface:
the compile-agreement invariant (now the named `compile_is_current(verdict)`
predicate) and the `working/manuscript/compiled.md` location (now the
`compiled_manuscript_path` / `COMPILED_REL` path seam). Both seam members live
in `novel_ralph_skill/state/compile_model.py`, the existing owner of the join
rule, and are re-exported through `novel_ralph_skill/state/__init__.py`. The
four consumers — `_compile.check_compiled`, `done_predicate.compile_consistent`,
the `_novel_done` compile clause, and the `state` package re-exports — were
routed through the seam, and `tests/test_compile_model_seam.py` pins the
projection and the single path.

Trail followed: `docs/novel-ralph-harness-design.md` §4.3/§5.4 (the compile and
disk-evidence model), `docs/developers-guide.md` §"`compile_consistent` is the
full content comparison" and §"One owner for 'compiled.md equals the ordered
draft concatenation'", the ADRs (ADR-001 deterministic/judgemental boundary,
ADR-003 shared interface contract, ADR-005 command surface), `AGENTS.md`
(quality gates, 400-line cap, CQS, en-GB Oxford spelling), the `python-router`
skill (Python work, routing to `python-types-and-apis` and `python-testing`),
and `leta`/`sem` for navigation and history. Files inspected:
`novel_ralph_skill/state/compile_model.py`,
`novel_ralph_skill/state/done_predicate.py`,
`novel_ralph_skill/state/disk_evidence.py`,
`novel_ralph_skill/state/__init__.py`,
`novel_ralph_skill/commands/_compile.py`,
`novel_ralph_skill/commands/_novel_done.py`,
`tests/test_compile_model_seam.py`, and the design and developer documents above.

The merged change is high quality. The extraction is well motivated (it closes
`docs/issues/audit-4.1.2.md` Findings 1 and 2), the four consumers genuinely
route through the new seam with no stragglers (verified by grepping every
`compiled.md` construction in `novel_ralph_skill/`), the opposite-polarity §5.4
detector is correctly left untouched and the reason is documented, and the seam
test exhausts the `CompiledComparison` truth table with a guard that forces a
decision if a fourth member is ever added. The findings below are at the
documentation-narrative and minor-ergonomics layer; none is a correctness
defect. Note also that the prior `docs/issues/audit-7.1.1.md` on `main`
described a *different* change (the `ai-isms.toml` pack, commit `42a6fc6`); this
file replaces it with an audit of the change that actually merged as 7.1.1.

## Finding 1 — developers' guide narrative predates the named currency predicate (severity: low)

**Category:** docs-gap

**Location:** `docs/developers-guide.md` §"`compile_consistent` is the full
content comparison (roadmap 3.1.2)" (lines ~1017-1048) and §"The exit-`4`
carve-out" (lines ~1050-1059).

**Description:** The guide thoroughly documents the shared
`compile_model.compiled_matches_drafts` helper and its three-valued verdict, but
its prose still describes the content-polarity projection inline ("an absent
`compiled.md` is `False`, a present one is `True` iff …") and the path stat as a
bare "`compiled.md` `exists()` stat". After 7.1.1 there are now two *named*
single-owner seam members that own exactly these two operations:
`compile_is_current(verdict)` (the content-polarity projection both
`check_compiled` and `compile_consistent` route through) and
`compiled_manuscript_path` / `COMPILED_REL` (the single filesystem join and the
envelope token). A developer reading the guide is told the rule but not the name
of the function that now enforces it, so a future change that needs the
projection or the path may re-derive it inline rather than calling the seam —
the exact regression 7.1.1 was extracting to prevent.

**Proposed fix:** Add one short paragraph to the `compile_consistent` section
naming `compile_is_current` as the single content-polarity projection (and
noting the §5.4 detector deliberately uses the opposite `is not DIVERGES`
polarity inline, *not* through this predicate), and one sentence in the
carve-out section naming `compiled_manuscript_path` / `COMPILED_REL` as the
single owner of the `compiled.md` location and envelope token. Cite
`docs/issues/audit-4.1.2.md` Findings 1 and 2, which this seam closes, so the
guide and the code agree on where the rule lives.

## Finding 2 — `compile_model.py` module docstring not broadened to its new responsibilities (severity: low)

**Category:** docs-gap

**Location:** `novel_ralph_skill/state/compile_model.py` module docstring (lines
1-17).

**Description:** The module-level docstring still describes the module solely as
"the §4.3/§9 draft-concatenation model the disk-evidence detector shares" and
singles out `concatenate_drafts` as the production twin. After 7.1.1 the module
also owns the compile-currency projection (`compile_is_current`) and the
compiled-manuscript path seam (`compiled_manuscript_path`, `COMPILED_REL`) — two
responsibilities the header does not announce. A reader scanning the module top
to decide whether a new currency or path concern belongs here will not learn
from the docstring that this module is the designated single owner of both, even
though the per-symbol docstrings (correctly) say so.

**Proposed fix:** Extend the module docstring with one sentence stating that the
module is also the single owner of the compile-currency projection
(`compile_is_current`) and the `compiled.md` path/envelope token
(`compiled_manuscript_path` / `COMPILED_REL`), cross-referencing
`docs/issues/audit-4.1.2.md` Findings 1 and 2. This keeps the module header an
accurate map of its responsibilities, matching the project's heavy-docstring
convention.

## Finding 3 — `check_compiled` recomputes `working_dir()` on the fault path (severity: low)

**Category:** ergonomics

**Location:** `novel_ralph_skill/commands/_compile.py` `check_compiled` (lines
208-216).

**Description:** `check_compiled` calls `working_dir()` once to compute the
verdict (line 211) and again inside the `except` handler to pass to
`_draft_read_error` (line 216), with a comment explaining the second call
("`check_compiled` has no `root` local; pass `working_dir()` …"). The comment
itself signals the awkwardness: a `root = working_dir()` local computed once,
mirroring `compile_manuscript`'s own `root = working_dir()` (line 134), would
remove the duplicate call, the explanatory comment, and the asymmetry with the
write path. `working_dir()` is a pure path constructor so there is no
correctness or performance issue here; this is a readability and consistency
nit only.

**Proposed fix:** Hoist `root = working_dir()` to a local at the top of
`check_compiled`, pass `root` to both `compiled_matches_drafts(state, root)` and
`_draft_read_error(root, exc)`, and drop the now-redundant comment. This aligns
`check_compiled` with `compile_manuscript`, which already binds `root` once.

## Finding 4 — seam test asserts the happy join but not the doubled-prefix guard (severity: low)

**Category:** test-gap

**Location:** `tests/test_compile_model_seam.py`
`test_compiled_manuscript_path_joins_without_doubling_prefix` (lines 72-81);
`novel_ralph_skill/state/compile_model.py` `compiled_manuscript_path` docstring
(lines 71-76).

**Description:** The `compiled_manuscript_path` docstring makes a specific
contract claim: the input is "expected to be an already `working/`-anchored
directory … so the result is **not** doubly prefixed". The seam test proves the
positive direction — passing `Path("working")` reproduces `COMPILED_REL` — but
nothing pins the byte-exact `manuscript/compiled.md` tail independently of the
`working/` anchor, so a future edit that, say, changed the join to
`working_dir / "working" / "manuscript" / …` would only be caught by the single
combined `as_posix() == COMPILED_REL` assertion, which couples the anchor and
the tail. The claim that the function never doubles the prefix is asserted only
implicitly.

**Proposed fix:** Add one assertion that exercises a non-`working`-named anchor
(e.g. `compiled_manuscript_path(Path("/tmp/run/working")).parts[-2:] ==
("manuscript", "compiled.md")`) so the relative tail is pinned independently of
the `working/` segment, making the "no doubled prefix" contract explicit rather
than incidental to the one happy-path equality. Keep the existing
`COMPILED_REL` equality as the envelope-token guard.

## Finding 5 — the `working/`-anchored input contract is a convention, not a type (severity: low)

**Category:** ergonomics

**Location:** `novel_ralph_skill/state/compile_model.py` `compiled_manuscript_path`
(lines 66-87); `COMPILED_REL` (line 45).

**Description:** `compiled_manuscript_path(working_dir)` and the string constant
`COMPILED_REL = "working/manuscript/compiled.md"` are agreed *only* when the
caller passes a directory whose final segment is literally `working` (the
docstring spells this out, and the seam test passes exactly `Path("working")`).
The coupling between the path-builder's input contract and the hardcoded
envelope token is carried entirely in prose; a caller that passed a differently
named `working/` directory (e.g. a renamed scratch dir in a future test harness)
would silently produce a path whose POSIX form no longer matches `COMPILED_REL`,
with no type or assertion catching it. This is the residual seam after 7.1.1:
the path *join* is centralized, but the "input must be the `working/` segment"
precondition is not enforced anywhere it is called.

**Proposed fix:** This is a watch-item rather than an actionable defect for a
docs-only audit. If a future task introduces a second caller with a non-canonical
working directory, consider either (a) deriving `COMPILED_REL` from
`compiled_manuscript_path(Path("working")).as_posix()` so the constant cannot
drift from the join, or (b) accepting the `working/` root through a single shared
accessor so the precondition has one enforcement point. No change is warranted
now; recording so the next compile-surface task sees the latent coupling.
