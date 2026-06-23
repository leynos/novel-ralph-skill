# Logisphere design review — roadmap 2.1.4 ExecPlan (round 2)

Verdict: PROCEED WITH CONDITIONS. The round-2 plan resolves both round-1
blocking defects (B1 escalation, B2 atomicity). Every load-bearing claim was
re-verified against source. No blocking design-conformance or implementability
defect remains. Two precision conditions and three advisories would strengthen
it; none of the conditions is structural, so they are recorded as conditions on
the implementer rather than a return to the planner.

## Round-1 defects: confirmed resolved

- B1 (roadmap success vs locked boundary) — RESOLVED. The plan now escalates
  explicitly (Purpose "Escalation" sub-section, Decision Log D5) and discharges
  the escalation in Work item 1 by amending the roadmap 2.1.4 Success clause via
  a `review:2.1.4` `Reroute` note *before* any code lands. Verified against
  source:
  - The roadmap 2.1.4 Success text (`docs/roadmap.md` lines 407-410) does
    literally read "a negative fixture **the validator rejects**" for the "zero
    until plans exist" case — so the contradiction is real, not invented.
  - `docs/execplans/roadmap-2-1-2.md` lines 87-91 lock the disk-blind boundary:
    "The 'zero until plans exist' sub-clause … is the corpus task 2.1.4's and
    reconciliation task 2.3.2's concern, not validated here from disk." Lines
    302-311 and 736-745 corroborate. The validator physically cannot reject the
    disk-evidence fixture without breaching this boundary, so option (a)
    (amend and defer) is the only correct resolution. D5 selects it.
  - The `Reroute` mechanism is the established house instrument: eight existing
    `Reroute` notes in `docs/roadmap.md` (lines 254, 268, 377, 396, 480, 876,
    907, 921), including one already on the 2.1.4 block. The amendment fits the
    precedent.
  - D1's round-1 over-reach (citing "(or split it)" as licence to exempt the
    validator) is corrected in round 2: D1 now states the phrase splits the
    oracle branch only, and the validator exemption is carried by D5. This was
    the exact over-claim r1 flagged.

- B2 (atomicity / gate-red commit) — RESOLVED. Old Work items 3 and 4 are merged
  into a single atomic Work item 3 (oracle name + predicate + fixtures **and**
  the agreement-suite `_DEFERRED_INVARIANT_NAMES` deferral, one commit, one
  gate). Decision Log D4 records the model. Progress, Plan-of-work, Concrete
  steps, and Idempotence are now internally consistent on "no work item leaves
  `make all` red". The Work item 1 red-baseline is made gate-clean via
  `@pytest.mark.xfail(strict=True)`, removed in Work item 4. This is a sound
  mechanism: `xfail` is a builtin pytest marker (no `--strict-markers`
  conflict — none is configured), and strict-xfail evaluates per-test under
  `pytest-xdist`
  (`make test` runs `pytest -v -n $(PYTEST_XDIST_WORKERS)`), so the worker
  distribution does not affect it.

## What was re-verified against source (claims that hold)

- `_check_cursor_coherent` (oracle `_oracle.py:148`; validator `validate.py:196`)
  currently enforces only `0 <= current_chapter <= len(chapters)` and scene/beat
  non-negativity. `cursor-past-current-chapter` (`_variants.py:142`) is the sole
  cursor variant. WI1 framing accurate.
- `chapter_dir_name(number)` is at `_specs.py:172` (returns `chapter-NN`).
  `ChapterSpec` is a frozen, kw_only dataclass with `write_draft: bool = True`
  precedent for adding `has_scene_plan`/`has_beat_plan` defaulting off
  (`_specs.py:56-97`). The additive builder change in `_write_chapter`
  (`_builder.py:157`) mirrors the existing `write_draft` conditional exactly.
- `COHERENT_BASELINE = PHASE_STATES["drafting"]` (`_library.py:118`) carries
  `current_chapter=len(chapters)=3`, `current_scene=0`, `current_beat=0`, and no
  scene/beat-plan files. So: (i) the new `cursor-plan-present` predicate never
  fires on it (scene/beat are 0); (ii) the WI4 pure-state clause
  (`current_chapter==0 ⇒ scene==beat==0`) never fires on it (`current_chapter=3`).
  Both new sub-clauses leave every coherent tree clean — `test_coherent_trees_pass_the_oracle`
  stays green. Plan Risk rows (lines 175-193) are accurate.
- `_check_cursor_coherent` is in `_SPEC_CHECKS` (`_oracle.py:227`); the
  disk-evidence predicate must be applied separately in `corpus_check` alongside
  `_check_by_chapter_sum`/`_check_compiled_matches_drafts` (`_oracle.py:254-256`).
  The plan routes `cursor-plan-present` there, not into `_SPEC_CHECKS`. Correct.
- Arithmetic: `CORPUS_INVARIANT_NAMES` has 12 names; `_DEFERRED_INVARIANT_NAMES`
  has 4; `PURE_STATE_INVARIANT_NAMES` has 8; 12−4=8. After: 13 corpus, 5
  deferred, 8 owned; 13−5=8. `test_owned_names_equal_corpus_vocabulary`
  (`test_validate_state_corpus.py:92`) computes
  `set(corpus_names) − _DEFERRED_INVARIANT_NAMES` and adjusts automatically.
  Holds.
- Fixtures auto-flow: `incoherent_variant_names`, `corpus_invariant_names`,
  `check_corpus`, `coherent_oracle_cases`, `incoherent_tree`
  (`corpus_fixtures.py`) all derive from the live mappings, so the new variants
  and the new name are exercised by the existing `TestCoherentIncoherentSplit`
  self-tests (`test_working_corpus.py:357-398`) with no new self-test body.
  Plan claim holds.
- Cursor decoupling: `current_chapter`/`current_scene`/`current_beat` appear in
  the validator only inside `_check_cursor_coherent` (grep-confirmed). A
  perturbation forcing `current_chapter=0, current_scene>0` from any coherent
  state breaks exactly `cursor-coherent`, so WI4's `_PERTURBATIONS` entry is
  sound over the full strategy (unlike invariant-4 sub-rules, which the property
  suite deliberately drives from controlled examples — `test_validate_state_property.py:224-228`).
- Property strategy hazard handled: `coherent_states()` draws
  `current_scene`/`current_beat` in `[0,20]` independently of `current_chapter`
  (`test_validate_state_property.py:174-178`). After WI4 a drawn
  `current_chapter=0, current_scene>0` would be rejected, breaking
  `test_coherent_states_accepted`; the plan's WI4 fixes the strategy in the same
  item (Risk lines 167-174). Correct.
- `test_materialises_design_paths` (`test_working_corpus.py:82`) asserts named
  paths present and only the *earlier-draft* wrong paths absent (lines 100-101);
  it does not assert `scenes.md`/`beats.md` absence, so the additive builder
  change does not break it. Plan Risk (lines 189-193) accurate.
- cuprum genuinely untouched: it appears only in `tests/conftest.py`,
  `test_novel_state_check.py`, `test_console_scripts_e2e.py`,
  `test_conftest_helpers.py`, `test_venv_scripts_dir.py` — none in the plan's
  edit set. No uncited Cyclopts / pytest-timeout / uv behavioural claim is made;
  the only locked-library reliance is on builtin pytest `xfail(strict=True)`,
  which is core pytest behaviour, not a memory-based assertion.

## Conditions on the implementer (precision; non-structural)

- C1 (Telefono) — pin the full disk path, not just `chapter_dir_name`. WI3
  step 2 says resolve the current chapter via
  `chapter_dir_name(spec.current_chapter)`
  but never states the `manuscript/` path segment. The builder writes chapter
  directories under `working_dir / "manuscript" / chapter-NN/`
  (`_builder.py:191-197`), so the predicate must test
  `working_dir / "manuscript" / chapter_dir_name(n) / "scenes.md"` (resp.
  `beats.md`). An implementer who joins `working_dir / chapter_dir_name(n)`
  directly will read a non-existent path and the predicate will fire on every
  tree, silently inverting the check. State the full join in the plan or the
  predicate docstring.

- C2 (Pandalump) — the agreement-suite docstring is already stale; do not
  copy the wrong number. WI3 step 5 says update the comment to "the five §5.4
  disk-evidence invariant names". Note that the module docstring of
  `tests/test_validate_state_corpus.py` (lines 7-8) currently says "the six
  pure-state invariants" and "the four disk-evidence names", but the owned set is
  in fact **eight** (`PURE_STATE_INVARIANT_NAMES`). The "six" is pre-existing
  drift. When WI3/WI5 touch that file, correct both numbers (eight owned, five
  deferred) rather than only the deferred count, or the docstring stays wrong.

## Advisories (non-blocking)

- A1 (Doggylump) — WI3 fixture isolation note is hand-wavy. WI3 step 4's
  parenthetical ("set the other plan flag True … or keep the other cursor at 0")
  offers two routes without committing. The simpler, provably-isolated route is:
  keep the *other* cursor at 0 (then the other disk-evidence sub-check cannot
  fire) and keep the current chapter's other plan flag at its default `False`.
  Recommend stating the single chosen construction so the implementer does not
  improvise a variant that trips two names.

- A2 (Buzzy Bee) — positive-control fixture is net-new. WI3's positive-control
  unit test needs a coherent tree with `current_scene>0` AND `scenes.md` present;
  no existing fixture has `current_scene>0`. This is a fresh in-test spec built
  on the WI2 builder fields — fine, but it counts against the 8-file / 350-line
  Tolerance. The plan touches: `_specs.py`, `_builder.py`, `_oracle.py`,
  `_variants.py`, `test_validate_state_corpus.py`, `test_validate_state_property.py`,
  `test_working_corpus.py`, `docs/roadmap.md`, and this ExecPlan — that is nine
  files if the ExecPlan counts. Confirm the Tolerance counts production/test
  files only (the ExecPlan is a living doc, not a "net change") or escalate per
  the plan's own Tolerance rule.

- A3 (Dinolump) — D2 reviewer-confirmation gate is correctly surfaced. The plan
  flags D2 (read scene/beat-vs-`current_chapter` as "non-zero scene/beat while
  `current_chapter==0`") in Tolerances (Ambiguity) for reviewer confirmation.
  D2 is confirmed as follows: it is the reading `roadmap-2-1-2.md` lines 736-745
  explicitly deferred to 2.1.4, symmetric with the existing
  `current_chapter <= len(chapters)` clause, and the only pure-state,
  validator-expressible reading. No escalation needed; the plan may proceed on
  D2.

## Pre-mortem (Doggylump)

Six months on, the most likely incident under this plan: an implementer wires
the `cursor-plan-present` path lookup against `working_dir / chapter_dir_name(n)`
without the `manuscript/` segment (C1). The predicate then reads a never-present
path, returns "plan absent" for *every* tree, and fires on coherent trees —
`test_coherent_trees_pass_the_oracle` goes red. Blast radius: caught at the WI3
gate (the self-test iterates all coherent trees), so it never merges. Signal: the
failing assertion names the coherent phase whose tree was wrongly flagged.
Prevention: C1 (pin the full join in the plan). Severity is therefore low — the
corpus self-test is a tight net — but stating the path removes the trap entirely.

A second, subtler path: the WI4 strategy fix forces `scene=beat=0` only when
`current_chapter==0`, but the new `_perturb_cursor_past_current_chapter` must
then *re-introduce* `current_scene>0` with `current_chapter=0` to break the
clause. If the perturbation instead leaves `current_chapter` untouched it breaks
nothing and `test_single_perturbation_names_exactly_one` fails on an empty
verdict. Caught at the WI4 gate; prevention is the explicit perturbation
definition the plan already gives (WI4 step 4).

## Alternatives checkpoint (Wafflecat)

The plan's central structural bet — a *separate deferred* `cursor-plan-present`
name rather than folding the disk sub-clause into `cursor-coherent` — is the
correct one, and D1 now records the rejected fold-alternative (r1 advisory A5
discharged). The strongest genuine alternative is the inverse of D5: instead of
amending the roadmap Success clause, *narrow the corpus oracle* so the
disk-evidence sub-clause is modelled as a pure-state proxy (e.g. a spec flag
`scene_plan_drafted` the oracle reads from the spec, not from disk), letting a
single `cursor-coherent` name carry it and the validator agree. That trades away
fidelity to the design's actual on-disk semantics (`state-layout.md` ties the
clause to `scenes.md`/`beats.md` *existence*, which is genuinely disk-evidence)
in exchange for avoiding the roadmap amendment. It is rejected for the same
reason D1/D5 give: a spec-only proxy would not be the invariant the design
states, and task 2.3.2 would then inherit a corpus that never modelled the real
disk dependency. The proposed design is on solid ground; no credible alternative
beats it.

## Bottom line

Implementable and design-conformant as written, conditioned on C1 (state the
`manuscript/` path segment) and C2 (fix the stale owned-count, not just the
deferred count). Both are precision fixes the implementer applies in-flight, not
structural reworks. Verdict: PROCEED WITH CONDITIONS.
