# Logisphere design review — roadmap 2.1.3 ExecPlan, round 3

Verdict: ACCEPT. The round-3 rewrite resolves both remaining round-2 blocking
defects against the real source, and no new blocking defect is introduced. I
would stake my name on the plan being implementable and design-conformant as
written. Three advisory items follow; none blocks.

## Round-2 blocking defects — both resolved

### B1-r2 (reconcile both named proxies) — RESOLVED

The developers' guide (verified, lines 323-334) names **two** pure-state
proxies and closes "reconciling the proxy against a live draft count is task
2.1.3's on-disk cross-check" — `gate-ratio-consistent` AND
`consecutive-clean-within-drafted`. Round 2 reconciled only the gate ratio and
left the drafted-chapters proxy on a spec basis (`corpus_check` reads
`spec.chapters`, not disk — verified `_oracle.py` lines 142-149), which the
Work item 3 guide edit would have overclaimed.

Round 3 extends the live oracle to recompute the **drafted-chapters count**
from the present positive-token `draft.md` bodies and reconcile
`consecutive-clean-within-drafted` (`[drafting.critic].consecutive_clean`,
written by `_builder.py::_drafting_table` line 68 — verified) against it. Both
proxies the guide names are now reconciled against the live drafts. The
honest-draft bases are correct: the validator's drafted-chapters proxy counts
`by_chapter` entries `> 0`
(`validate.py::_check_consecutive_clean_within_drafted` line 187 — verified),
the oracle's honest basis counts
`sum(1 for chapter in spec.chapters if chapter.draft_words > 0)` (`_oracle.py`
line 148 — verified), and `draft_body(n)` writes exactly `n` whitespace tokens
(empty for `n <= 0`, `_specs.py` lines 205-214 — verified), so the live token
count recovers the basis byte-for-byte. The Work item 1 self-test
(`test_live_draft_counts_equal_honest_draft_bases`) pins both live numbers to
both honest bases on every coherent tree. The fix is sound.

### B2-r2 (signature cannot satisfy step 5) — RESOLVED

Round 3 fixes the signature to `live_draft_owned(spec, working_dir)` throughout
— the Interfaces block, Work item 1, the Work item 2 fixture wiring, and the
`check_live_draft` fixture type are all consistent now. The corpus fixtures do
hand back `(spec, working_dir)` at every call site (`coherent_oracle_cases`
returns `(spec, Path)`, `incoherent_tree` returns `(spec, Path, str)` — verified
`tests/corpus_fixtures.py` lines 176-203, 221-253), so threading the spec
costs nothing and the step-5 `corpus_check(spec, working_dir)` reuse is now
satisfiable. The plan states plainly that the oracle is spec-independent only
for the two live-draft proxies, table-internal for `by-chapter-sum`, and
spec-derived for the other five — exactly the honesty B2-r2 demanded.

## Verification of load-bearing claims against real source

- `build_working_tree` returns `dest/"working"`; manuscript is
  `working/"manuscript"`; `_write_chapter` writes
  `manuscript/chapter-NN/draft.md` (`_builder.py` lines 167-211). The plan's
  glob `working_dir/"manuscript"/"chapter-*"/"draft.md"` is correct.
- The eight owned names equal `PURE_STATE_INVARIANT_NAMES` (verified
  `validate.py` lines 60-69). The "five non-disk + three disk-reconcilable = 8"
  partition is correct.
- `corpus_check` returns the full 13-name vocabulary; restricting to the owned
  set and overriding the three disk-reconcilable names is well-defined.
- No variant sets `by_chapter_override`; only `by-chapter-sum-mismatch` sets
  `current_words_override=1` (`_variants.py` lines 110-116, `_specs.py` lines
  256-273 — verified). The override-landmine reasoning holds.
- The `consecutive-clean-over-chapters-drafted` variant (`_variants.py` lines
  125-133): one positive-draft chapter, `consecutive_clean=2`. Table count = 1
  and live count = 1, so validator and live oracle both fire
  `consecutive-clean-within-drafted` and agree. The agreement test passes for
  this variant.
- The reused helpers (`_validator_verdict`, `_load_succeeds`, `_PARSE_ERRORS`,
  `_PARSE_ENFORCED_INVARIANTS`) all exist in
  `tests/test_validate_state_corpus.py` (verified). `tomllib` tolerates the
  out-of-enum `phase-not-in-enum` tree, so `corpus_check`/the live oracle do
  not raise on the parse-rejected tree; the parse-rejection branch is sound.
- Locked-library use is confined to established roles: `pytest-xdist` (the
  existing suite already runs under it; new tests are xdist-safe via per-test
  `tmp_path`), `tomllib`, `pathlib.glob`, `str.split` (stdlib). No uncited
  memory-based claim about Cyclopts, pytest-timeout, or uv appears, so no
  firecrawl verification is owed. The cuprum exclusion is correct (no
  subprocess; verified against
  `/data/leynos/Projects/cuprum/cuprum/catalogue.py`, `program.py` —
  `ProgramCatalogue` is a process allowlist this task never touches).
- `make all`/`make markdownlint`/`make nixie`, the 400-line cap (AGENTS.md
  24-27), and single-green-commit discipline (AGENTS.md 100, 108) are the right
  gates and correctly invoked. `docs/documentation-style-guide.md` exists for
  Work item 3.

## Advisory (non-blocking)

- A1 (liveness not exercised by a divergence case). No incoherent corpus variant
  makes the table's drafted-chapters count diverge from the live count, so the
  agreement test never exercises a tree where the table-basis and live-basis
  `consecutive-clean-within-drafted` verdicts would differ. The same is true of
  `gate-ratio-consistent` (the `by-chapter-sum-mismatch` variant overrides
  `current`, not `by_chapter`, so the gate numerator `sum(by_chapter)` still
  equals the live total). Liveness for both proxies therefore rests on the
  `live_draft_counts` self-test plus the docstring, exactly as round 2 accepted
  for the gate proxy. The plan is honest about this (Work item 2 lines
  802-808). This is the accepted round-2 precedent applied symmetrically, not a
  regression; it is recorded so a future reviewer does not mistake it for a
  missed divergence test. If a stronger guarantee is wanted later, a corpus
  variant that sets `by_chapter_override` to drop a positively-drafted chapter
  would exercise the live drafted-chapters divergence directly — but adding it
  belongs to 1.3.2, not this task (and the plan's tolerances correctly route
  such a finding to escalation rather than absorption).

- A2 (step-1 tomllib enumeration omits `drafting.critic`). Work item 1 step 1
  (lines 661-665) lists the tomllib reads as `target`/`current`/`by_chapter`/
  `gates.knitting`, but step 5 also reads
  `state["drafting"]["critic"]["consecutive_clean"]`. The enumeration in step 1
  should include the `[drafting.critic]` read so the single-parse claim ("reads
  the materialised `state.toml` with `tomllib` once") names every key it
  consumes. Purely an internal-consistency tidy; the implementer reads what
  step 5 requires regardless.

- A3 (line-count drift). The plan states
  `tests/test_validate_state_corpus.py` is 237 lines; it is 236 (verified). The
  cap headroom argument is unaffected. Trivial.

## Pre-mortem (Doggylump)

Round 2's pre-mortem landmine — a future `by_chapter_override` variant dropping
a positively-drafted chapter, where the drafted-chapters mislabel slips through
because the proxy was on a table/spec basis — is now defused: the live oracle
reconciles `consecutive-clean-within-drafted` against the count of present
positive-token `draft.md` bodies, so the live disk source catches that mislabel
on the drafted-chapters quantity exactly as it does on the drafted-words
quantity. The plan's tolerances correctly classify any such future divergence
as a finding to investigate, not a test to align.

## Docs and skills relied on

- Source verified directly against the worktree:
  `novel_ralph_skill/state/validate.py` (owned-name tuple lines 60-69;
  `_check_consecutive_clean_within_drafted` table proxy line 187;
  `_check_gate_ratio_consistent` table numerator line 241),
  `tests/working_corpus/_oracle.py` (`corpus_check` full-vocabulary return;
  `_check_by_chapter_sum` table read lines 108-119; honest-draft bases lines
  148, 199), `_specs.py` (`draft_body` lines 205-214; `by_chapter_override`/
  `current_words_override` and their derive functions lines 249-273),
  `_variants.py` (only `current_words_override` is used; the
  `consecutive-clean-over-chapters-drafted` variant lines 125-133),
  `_builder.py` (`_write_chapter`/`build_working_tree` working-dir layout lines
  157-211; `consecutive_clean` write line 68), `_library.py`
  (`_DRAFTED_WORDS=(24000,24000,20800)`, target 80000, lines 41-42),
  `tests/corpus_fixtures.py` (fixture surface),
  `tests/test_validate_state_corpus.py` (236 lines; reused helpers).
- `docs/developers-guide.md` "Invariant validation" lines 320-360 (the two-proxy
  / live-draft-count definition at 323-334; the deliberate-twin policy at
  336-344).
- `docs/roadmap.md` 2.1.3 entry and reroute (lines 375-393).
- `AGENTS.md` (400-line cap 24-27; quality-gate / commit discipline 95-108).
- cuprum read-only sibling `/data/leynos/Projects/cuprum/cuprum/catalogue.py`,
  `program.py`.
- Skill: logisphere-design-review (this framework).
