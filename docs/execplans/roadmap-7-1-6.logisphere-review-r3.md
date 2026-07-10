# Logisphere design review — roadmap 7.1.6 ExecPlan, round 3

Reviewer: adversarial Logisphere crew (df12-build design-review stage).
Date: 2026-06-27. Verdict: **Proceed with conditions** — one blocking defect, all
else verified against the real source.

## Scope and method

Plan reviewed from disk at `docs/execplans/roadmap-7-1-6.md` (not the planner's
summary). Every load-bearing factual claim was re-verified against the worktree
tree and the live `__doc__` of the named symbols. Round 3 resolves the round-2
blockers R2-B1 (`compile_is_current` carries only a bare relative ref) and R2-B2
(the re-export tail is not a substring of the canonical path); both are
independently confirmed below.

Sources consulted: `docs/roadmap.md` §7.1 (task 7.1.6, lines 2654-2683),
`docs/issues/audit-7.1.2.md` (Findings 2, 3, 5),
`docs/novel-ralph-harness-design.md` §4.3/§5.4, AGENTS.md (quality gates, en-GB
Oxford spelling, 400-line cap), the established prose-guard pattern
(`tests/test_developers_guide_contract_drift_guard.py`,
`tests/test_skill_contract_drift_guard.py`, `tests/_skill_contract_scanner.py`,
`tests/test_compile_model_seam.py`), `Makefile` (`all`/`lint`/`typecheck`/
`test`/`markdownlint`/`nixie` targets; `PYTHON_TARGETS` includes `tests`),
`pyproject.toml` (`[tool.interrogate] fail-under = 100`). Cross-checked the
read-only cuprum sibling expectation: cuprum appears only in `*_e2e` and
console-script fixtures, never in the in-process prose guards.

## Verified facts (planner's claims hold)

- R2-B1: `compile_is_current.__doc__` — canonical present **False**, re-export
  tail present **False**, bare relative `:func:\`compiled_matches_drafts\``
  present **True**. WI1 must normalize it; the plan does. Confirmed.
- R2-B2: tail `state.compiled_matches_drafts` is NOT a substring of the
  canonical `...state.compile_model.compiled_matches_drafts`; reconcile tail
  likewise absent from its canonical. The "tail count == 0" framing is correct.
- The three unedited compile-family consumers
  (`done_predicate.compile_consistent`,
  `disk_evidence._check_compiled_matches_drafts`, plus reconcile's marker) carry
  the canonical path / `{action, discrepancies, detail}` marker, and carry **no**
  re-export tail. R2-A1 pre-flight gate is real.
- All eight `_compile.py` re-export lines (12, 14, 34, 104, 106, 175, 181, 186)
  and `novel_state.py` line 136 confirmed. No doctests (`>>>` count 0) in the
  edited modules. `_reconcile.py` carries no `:func:` cross-reference to
  `reconciliation_payload` (import + direct calls only), so WI2's "no edit
  there" is correct.
- All proposed canonical paths resolve to live symbols. The post-WI1 grep is
  intentionally scoped to the four touched symbols, not a global re-export ban —
  correct and self-consistent.
- Locked-library scoping is sound: the new guard is in-process `__doc__` reading,
  exercising no cuprum / Cyclopts / pytest-timeout / uv behaviour. The
  established guards explicitly say "no subprocess". There is no external-library
  behaviour to cite or pin; scoping it out is justified, not an uncited memory
  claim.
- WI4 has a genuine home in `docs/developers-guide.md` single-source material.
  `make` targets and interrogate's 100% rule (which covers `tests/`) are
  accounted for.

## Blocking defect

**B3-1 (Telefono / Doggylump — the tail-discriminator unit test does not
isolate the branch it claims to pin).** Decision Log "no-bare-re-export check
restated" and WI3 step 2 require a dedicated unit test proving the "no bare
re-export tail" check is *non-vacuous*. As worded, that test "asserts the helper
RED on a docstring containing `state.compiled_matches_drafts` ... and GREEN on a
docstring containing only `state.compile_model.compiled_matches_drafts`."

A docstring whose only reference is the bare re-export full path
`novel_ralph_skill.state.compiled_matches_drafts` does **not** contain the
canonical substring `...state.compile_model.compiled_matches_drafts`, so the
helper raises on the *cross-reference-present* assertion (assertion 2), never
reaching the tail assertion (assertion 3). The test goes red, the suite passes —
but it does NOT demonstrate the tail check fires, which is the exact proof the
round-3 decision claims to deliver. The tail branch remains unproven; a future
edit that deletes the tail assertion would keep this test green.

Fix (precise, addressable): the tail-isolating fixture must contain the
canonical path **and** the tail simultaneously (e.g. a docstring naming both
`novel_ralph_skill.state.compile_model.compiled_matches_drafts` and
`novel_ralph_skill.state.compiled_matches_drafts`), so assertion 2 passes and
assertion 3 is the one that raises. Verified constructible: such a string has
`canonical in doc == True` and `tail in doc == True`. State in the plan that the
non-vacuity fixture co-locates both spellings, distinct from the registry's
green tree (where the tail is genuinely absent). Without this the plan's stated
proof obligation is not met.

## Advisory (non-blocking)

- A3-1 (Wafflecat). WI1 normalizes the sibling `concatenate_drafts` /
  `present_draft_bodies` / `CompiledComparison` re-export refs but the guard does
  not pin a tail for those on `check_compiled`. The plan documents this as the
  deliberate "registry coverage" boundary (normalized-but-unguarded by design).
  Accepted; flagging only so the implementer does not mistake it for an omission.
- A3-2 (Dinolump). The roadmap's "apply the convention and guard to ... 7.1.5"
  is satisfied by documentation + an extensible registry, not by editing 7.1.5
  (correctly, since 7.1.6 does not require 7.1.5 and it may be unmerged). This is
  a reasonable reading; the residual is that 7.1.5's adoption is unenforced until
  that task lands. The plan's guard-failure-on-missing-row is the backstop.
- A3-3 (Pandalump). The accepted residual — a consumer could re-expand prose
  while keeping its cross-reference and ship green — is explicitly recorded as a
  trade-off. It does not violate the §7.1 "cannot silently re-fork" invariant
  (the authoritative table stays the only cited source). Acceptable.

## Pre-mortem (Doggylump)

1. Most likely failure: a later §7.1 consumer uses a bare relative
   `:func:\`name\`` and the guard admits it because the tail-discriminator was
   never proven non-vacuous (B3-1). Mitigation: fix B3-1; the bare-relative
   negative fixture (already specified) plus a properly isolated tail fixture
   close this.
2. Second: WI1 normalizes a docstring that a behavioural suite greps verbatim.
   Mitigated — verified no doctests, and the three test-module hits are
   out-of-scope test prose that assert nothing against production spelling.
3. Third: 7.1.5 lands and re-spells via the re-export path. Mitigated by the
   documented convention + the guard's missing-row failure; residual is
   adoption-timing only.

## Alternatives checkpoint (Wafflecat)

Strongest alternative: collapse the two independent consumer assertions
(cross-reference-present + no-tail) into a single regex that matches the
canonical dotted path and rejects anything else. It trades the plan's two clean,
separately-testable substring checks for one harder-to-prove regex and reopens
exactly the non-vacuity question B3-1 raises. The plan's two-independent-checks
design is the better choice; no change recommended beyond B3-1.

## Verdict

Revise to fix B3-1, then proceed. Every other claim is verified against the real
source; the plan is atomic, ordered, testable, design-conformant, respects the
doc-and-test-only / no-behaviour-change boundary, and correctly scopes out the
locked libraries. B3-1 is a single, precise, addressable test-design correction.
