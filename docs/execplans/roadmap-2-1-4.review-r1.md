# Logisphere design review — roadmap 2.1.4 ExecPlan (round 1)

Verdict: REVISE. One blocking design-conformance defect, one blocking
plan-precision defect, plus advisories. The plan is well-researched and its
line citations check out against source; the structural approach (new
disk-evidence `cursor-plan-present` oracle name + pure-state
scene-vs-`current_chapter` clause in both oracle and validator) is sound. It
does not yet pass as stakeable because it silently resolves a contradiction with
the literal roadmap success criterion instead of escalating it.

## What was verified against source (claims that hold)

- Design §5.2 invariant 6 text (design lines 451-453) matches the plan's quote.
- `state-layout.md` lines 37-39 do name `scenes.md`/`beats.md` per chapter;
  lines 86-88 tie `current_scene = 0` / `current_beat = 0` to "plan not yet
  drafted". The on-disk representation the plan adds is authoritative, not
  invented.
- Oracle `_check_cursor_coherent` (`_oracle.py:148`) currently enforces only
  `0 <= current_chapter <= len(chapters)` and scene/beat non-negativity.
  Validator `_check_cursor_coherent` (`validate.py:196`) mirrors it. No existing
  variant targets the two missing sub-clauses (`_variants.py:142`,
  `cursor-past-current-chapter`, is the sole cursor variant). Plan Work item 1
  (WI1) framing is accurate.
- `_DEFERRED_INVARIANT_NAMES` has exactly four names today
  (`test_validate_state_corpus.py:62`); adding `cursor-plan-present` makes five.
  `test_owned_names_equal_corpus_vocabulary` (line 92) computes `owned ==
  set(corpus_names) - _DEFERRED_INVARIANT_NAMES` with `owned` hardcoded to the
  eight pure-state names, so subtracting the new deferred name keeps it green.
  Arithmetic checks out (12 -> 13 corpus names; 13 - 5 = 8 owned).
- `current_chapter` is referenced only inside `_check_cursor_coherent` in the
  validator. A perturbation forcing `current_chapter=0, current_scene>0` from an
  arbitrary coherent state breaks exactly `cursor-coherent`, so WI5's
  property-suite perturbation is decoupled and sound (unlike invariant 4, whose
  sub-rules cannot be driven from arbitrary states — `_property.py:224-228`).
- D2 (read scene-vs-`current_chapter` as "scene/beat non-zero while
  `current_chapter == 0`") is the interpretation roadmap-2-1-2 explicitly
  deferred to 2.1.4 (`roadmap-2-1-2.md:736-745`), not a fresh guess.
- D3 (do not add disk access to the pure-state validator) conforms to the
  locked checker/mutator boundary (`roadmap-2-1-2.md:87-91`, `302-311`).
- cuprum is genuinely untouched: it appears only in `tests/conftest.py`,
  `test_novel_state_check.py`, `test_console_scripts_e2e.py`,
  `test_conftest_helpers.py`, `test_venv_scripts_dir.py` — none modified by this
  plan. No uncited Cyclopts / pytest-timeout / uv behavioural claims are made.

## Blocking defects

### B1 (Pandalump / Telefono) — roadmap success criterion vs locked boundary

Roadmap 2.1.4 Success (docs/roadmap.md ~line 411): "a non-zero
`current_scene`/`current_beat` before its plan exists ... [is] a negative
fixture **the validator rejects**, with the corpus oracle labelling each on
the cursor invariant." The plan (D1, D3) routes this sub-clause to a
disk-evidence
name `cursor-plan-present` that the validator is added to `_DEFERRED_INVARIANT_
NAMES` to **never emit**. Under the plan the validator does NOT reject the
"zero until plans exist" fixture — only the oracle does. That contradicts the
literal success text.

The plan cites roadmap line 402 "(or split it)" as sanction, but that phrase
applies to splitting the **oracle's** `cursor-coherent` branch so all three
sub-clauses are exercised; it is not a licence to exempt the validator from the
success criterion's "the validator rejects" requirement.

The deeper truth: "zero until plans exist" is disk-evidence; a pure-state,
disk-blind validator physically cannot reject it without breaching the boundary
that 2.1.2 locked. So the roadmap success criterion as written is in tension
with the locked architecture. That is precisely the case the plan's own
Constraints ("if satisfying the objective requires violating a constraint,
stop, record the conflict, and escalate") and Tolerances (Oracle/validator
split) name as an escalation trigger.

Required: the plan must not silently resolve this in its own favour. Either (a)
escalate the roadmap-success-vs-boundary contradiction explicitly and obtain an
amended success clause (e.g. "the corpus oracle rejects on the disk-evidence
name; validator rejection is deferred to 2.3.2"), recording the resolution in
the Decision Log; or (b) demonstrate a boundary-respecting way for the validator
itself to reject. Option (a) is almost certainly correct, but it must be raised,
not assumed.

### B2 (Pandalump) — atomicity: WI3 leaves `make all` red; commit boundary unclear

WI3 itself states the agreement suite goes red after WI3 and is only restored by
WI4, then offers two contradictory instructions: "Do not commit until Work item
4 is staged together, OR commit Work items 3 and 4 as a single atomic commit."
The Progress list and Plan-of-work, however, present WI3 and WI4 as separate
items with separate validation gates. A work item that cannot pass `make all`
on its own is not atomic. The plan must commit to one model: merge WI3 and WI4
into a single atomic work item (preferred — one gate-passable commit), or state
unambiguously that WI3 is non-committable and only the combined WI3+WI4 boundary
is gated. As written the ambiguity invites a gate-red commit.

## Advisory (non-blocking, would strengthen)

- A1 (Telefono) — WI3 predicate signature. The interface block shows
  `_check_cursor_plan_present(spec, working_dir)`. The oracle's two disk-evidence
  checks differ in arity (`_check_by_chapter_sum(working_dir)` vs
  `_check_compiled_matches_drafts(spec, working_dir)`). Pin the chosen signature
  and note that the predicate resolves the current chapter's directory via the
  existing `chapter_dir_name(spec.current_chapter)` helper
  (`_specs.py:172`), so it does not re-invent path construction.

- A2 (Doggylump) — WI3 out-of-range guard. The predicate must not raise when
  `current_chapter` is out of range (the degenerate case WI5 owns). The plan
  says "the plan-present check does not fire" — good — but make explicit that the
  guard is `0 < current_chapter <= len(chapters)` before any path lookup, so a
  malformed cursor cannot make the predicate throw and pollute the verdict.

- A3 (Buzzy Bee / Dinolump) — scene AND beat coverage. WI3 leaves the
  beat-without-plan case optional ("one named case ... is sufficient ... covering
  both ... is preferred"). The roadmap names both `current_scene` and
  `current_beat`. Completeness of invariant-6 coverage is the entire point of
  this task; make both `scene-cursor-without-plan` and
  `beat-cursor-without-plan` mandatory rather than preferred. Likewise the
  pure-state variant should cover
  both scene and beat.

- A4 (Telefono) — WI5 perturbation wiring. WI5 step 4 says "wire it into the
  rejection parametrization." State explicitly whether the new perturbation joins
  the `_PERTURBATIONS` dict (sound here, since the cursor clause is decoupled) or
  is a standalone example-based test. Prefer adding it to `_PERTURBATIONS` so
  `test_single_perturbation_names_exactly_one` covers it over the whole
  strategy.

- A5 (Wafflecat) — alternatives. The plan records no alternatives-considered for
  the central D1 split decision beyond "fold vs split". A one-line note on the
  rejected alternative (extend `cursor-coherent` to carry a disk read in the
  oracle while keeping the validator silent) and why the separate deferred name
  is cleaner would satisfy the alternatives checkpoint.

## Pre-mortem (Doggylump)

Six months on, the most likely incident: a future change adds disk-evidence
validation to the production validator for 2.3.2 and re-uses
`cursor-plan-present`; because this plan never resolved B1, the success
criterion's "validator rejects" wording is ambiguous and a reviewer cannot tell
whether 2.1.4 ever discharged its mandate. Prevention: resolve B1 now by
amending the success criterion text and recording the disk-evidence deferral
explicitly, so the 2.3.2 author inherits an unambiguous contract.
