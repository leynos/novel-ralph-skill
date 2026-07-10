# Logisphere design review — roadmap 7.1.6 — Round 1

Verdict: 🔄 **Revise.** The plan's intent is correct and design-conformant, but
two load-bearing claims are factually wrong against the real source, and the
guard's central discriminator (the "re-enumerated table" heuristic) collides
with a registered consumer (`check_compiled`). As written, Work Item 1 leaves
re-export-path references behind and Work Item 3's positive cases cannot both
pass `check_compiled` and reject a re-expanded table under the heuristic the
plan states. These go back to the planner.

## Core bets

1. *Bet:* the only re-export-path cross-references in `_compile.py` are the six
   at
   lines 12/14/34/175/181/186. **Wrong.** There are eight; lines 104 and 106
   (inside `compile_manuscript`'s docstring) also use the re-export path. (🔴
   B1)
2. *Bet:* a consumer can be told apart from the authoritative docstring by
   "names all three `CompiledComparison` members with both polarities." **Wrong
   for the worked example.** `check_compiled` legitimately names all three
   members and both absent-file polarities. (🔴 B2)
3. *Bet:* re-export spellings "live only in the named consumer docstrings."
   **Wrong.** `tests/test_reconciliation_payload.py:3` also names the re-export
   path. Benign for the guard, but the Artifacts/safety-grep narrative is
   false. (🟡 B3)
4. *Bet:* doc-and-test only, zero behaviour change, stdlib+pytest, no cuprum.
   Sound. The no-subprocess / no-cuprum scoping in the Decision Log is correct
   and well-justified; there is genuinely no external-library behaviour to pin
   here. ✅

## Blocking findings

### 🔴 B1 (Pandalump / Telefono) — Work Item 1 misses two re-export references

```console
$ syms='compiled_matches_drafts|concatenate_drafts'
$ syms="$syms|present_draft_bodies|CompiledComparison"
$ grep -nE "novel_ralph_skill\.state\.($syms)\b" \
    novel_ralph_skill/commands/_compile.py
```

returns **eight** lines: 12, 14, 34, 104, 106, 175, 181, 186. Work Item 1
enumerates only six (12, 14, 34, 175, 181, 186) and omits **104 and 106**,
which sit in `compile_manuscript`'s docstring:

- line 104: `:func:`~novel_ralph_skill.state.present_draft_bodies`rule`
- line 106: `:func:`~novel_ralph_skill.state.concatenate_drafts`, and writes`

Consequences:

- The plan's own success criterion ("no re-export-path or mixed spelling
  survives") is violated by its own work items — two re-export spellings would
  ship.
- `compile_manuscript` is itself a consumer of these two projections. If the
  guard registry (WI3) lists `compile_manuscript` or the `_compile` module as a
  consumer of `concatenate_drafts`/`present_draft_bodies`, the "no bare
  re-export spelling" assertion reddens against lines 104/106 the plan never
  normalizes — a green-after failure baked into the plan.

Fix required: WI1 must enumerate and normalize all eight references (or state
an explicit, justified carve-out, which there is no reason for here). The
registry in WI3 must then be reconciled with the full consumer set.

### 🔴 B2 (Telefono / Doggylump) — the "re-enumerated table" heuristic reddens a registered consumer

WI3 states the forbidden "re-expanded table" shape as: *"a consumer must not
name all three members with both polarities."* It also states the
authoritative-marker set as: *"the word `authoritative` and all three
`CompiledComparison` member names with both absent-file polarities."*

But `check_compiled` (a registered consumer) names **all three members**
(`MATCHES`, `ABSENT`, `DIVERGES` — verified by grep, one occurrence each) and
describes **both** absent-file polarities ("an absent compiled.md is equally
not current" plus "the §5.4 disk-evidence detector's opposite absent-file
polarity"). So the plan's stated discriminator:

- false-positives on `check_compiled` (the positive case the plan intends to
  pass would go red), and
- does not actually distinguish the authoritative docstring from this consumer
  (both satisfy the authoritative-marker set).

The consumers are heterogeneous: `check_compiled` names 3 members,
`_check_compiled_matches_drafts` names 2 (ABSENT+DIVERGES),
`compile_consistent` names 0. There is therefore no member-count threshold that
passes all three consumers while rejecting a re-expanded copy of the 3-member
authoritative table. This is exactly the brittleness audit-7.1.2 Finding 3 and
the plan's own Risk #1 warn about — but the plan only *names* the risk; it does
not supply a discriminator that survives the real tree.

The established pattern the plan claims to mirror
(`test_developers_guide_contract_drift_guard.py`) does **not** count
free-floating substrings across a whole docstring; it slices a structural
*region* and compares a code-derived field set by presence. The plan's
heuristic is weaker than the pattern it cites.

Fix required: the planner must specify a discriminator that actually works
against the real consumers — e.g. scope the load-bearing assertion to
**cross-reference presence in the defining-module spelling + absence of the
authoritative full-table *structure*** (the prose contiguity / table layout
that only the authoritative docstring carries), not "names all three members."
The Tolerance already says to "prefer scoping the guard to cross-reference
presence … over full-prose matching"; the plan should commit to that as the
primary assertion and **drop or redesign** the member-enumeration heuristic so
it does not red `check_compiled`. The negative-case fixtures must include a
string shaped like `check_compiled`'s real docstring to prove the chosen
discriminator does not false-positive on a legitimate three-member consumer.

## Advisory findings

### 🟡 B3 (Doggylump) — Artifacts/safety-grep narrative is inaccurate

The plan claims the pre-edit grep proves "the re-export spellings live only in
the named consumer docstrings." `tests/test_reconciliation_payload.py:3` carries
`:func:`novel_ralph_skill.state.reconciliation_payload``. Harmless to the
guard (test docstrings are out of the registry), but the Artefacts bullet and
the implicit invariant are false as stated. Reword to "live only in the named
*production* consumer docstrings; one test docstring also names it and is out
of scope," and have WI2's grep step expect that hit rather than treating it as
a surprise.

### 🟢 Improvement (Pandalump) — registry must be reconciled with the full consumer graph

Once B1 is fixed, decide explicitly whether `compile_manuscript` is a
registered consumer (it cross-references `concatenate_drafts`/
`present_draft_bodies`, whose authoritative home is `compile_model`, not
`compiled_matches_drafts`). The plan's registry currently binds consumers to
`compiled_matches_drafts` only; the `concatenate_drafts`/`present_draft_bodies`
projections have their own authoritative docstrings and are not represented as
registry rows at all, yet WI1 normalizes references to them. Either add rows
for them or state in the Decision Log why they are normalized-but-unguarded
(consistency-only), so the guard's coverage boundary is explicit and a future
reader is not surprised that normalized refs are unpinned.

### 💡 Open question (Wafflecat) — is the member-enumeration heuristic worth keeping at all?

The single load-bearing invariant §7.1 actually removed was *duplicated full
projection tables*. The defining-module-path spelling is the cheap, robust,
unambiguous half (substring assertion, already shown workable). The "no
re-enumerated table" half is the brittle half and, per B2, has no clean
threshold here. Wafflecat's alternative: **make the guard
cross-reference-only** (every consumer carries the defining-module
cross-reference; the authoritative docstring carries the table markers; no
per-consumer table-enumeration check at all). This solves ~80% of the
protection with ~20% of the brittleness, matches the Tolerance's stated
fallback, and avoids the `check_compiled` collision entirely. Trade-off: a
future edit could re-expand a consumer's prose *without* removing its
cross-reference and ship green. Mitigation: that re-expansion still cannot
silently *re-fork* the projection because the authoritative table remains the
only cited source; and the developers-guide convention (WI4) plus review catch
the prose bloat. The planner should consciously choose between (a) a working
structural table-detector and (b) cross-reference-only, and record the choice
in the Decision Log rather than leaving WI3 with a heuristic that does not hold.

## Pre-mortem (Doggylump)

1. **Most likely failure:** the implementer follows WI1 literally, normalizes
   six
   refs, runs `make all` green (no guard yet), commits — leaving lines 104/106
   on the re-export path. WI3's guard then either (a) does not cover
   `compile_manuscript` and the inconsistency the task exists to close
   survives, or (b) does cover it and the positive case is red, forcing an
   unplanned WI1 re-open mid-stream. *Prevention:* fix B1 — enumerate all eight
   refs up front.
2. **Second failure:** the implementer writes WI3's heuristic as stated, the
   `check_compiled` positive case reddens, and they spend the three Tolerance
   tuning attempts before escalating — burning a round on a defect the plan
   could have pre-empted. *Prevention:* fix B2 — specify the
   cross-reference-first discriminator and a `check_compiled`-shaped negative
   fixture before coding.
3. **Third failure:** WI4 documents a convention the guard does not actually
   enforce (because the table-detector was quietly dropped under brittleness),
   leaving the developers' guide overclaiming. *Prevention:* settle B2's
   discriminator first; document only what the guard enforces.

## Alternatives checkpoint

Strongest alternative (Wafflecat): the cross-reference-only guard above. It is
genuinely viable, structurally simpler, and the plan's own Tolerance already
sanctions it as the fallback. The only thing it trades away is the
table-re-expansion tripwire, which B2 shows the plan cannot currently implement
cleanly anyway. Recommend the planner adopt it explicitly unless they can
produce a structural table-detector (region/contiguity-based, like the existing
guards) that demonstrably passes a `check_compiled`-shaped fixture.

## Next steps (ordered)

1. (B1) Re-enumerate Work Item 1 to cover all eight re-export references in
   `_compile.py` (add lines 104 and 106), and re-run the grep to confirm zero
   `novel_ralph_skill.state.<symbol>` re-export spellings remain in production.
2. (B2) Redesign the WI3 discriminator so it does not red `check_compiled`:
   commit to cross-reference-presence as the primary assertion; either drop the
   member-enumeration check or replace it with a structural table-detector and a
   `check_compiled`-shaped negative fixture proving no false positive.
3. (Improvement) Reconcile the registry with the full consumer/projection graph
   (`concatenate_drafts`/`present_draft_bodies` rows, or a documented
   carve-out).
4. (B3) Correct the Artifacts/safety-grep narrative to expect the test-docstring
   re-export hit.
5. Re-record the WI3/discriminator decision in the Decision Log.

## Documentation & skills relied on

- ExecPlan under review: `docs/execplans/roadmap-7-1-6.md`.
- Source verified against:
  `novel_ralph_skill/commands/_compile.py`,
  `novel_ralph_skill/commands/novel_state.py`,
  `novel_ralph_skill/state/compile_model.py`,
  `novel_ralph_skill/state/reconcile.py`,
  `novel_ralph_skill/state/done_predicate.py`,
  `novel_ralph_skill/state/disk_evidence.py`,
  `tests/test_developers_guide_contract_drift_guard.py` (the mirrored pattern),
  `tests/test_reconciliation_payload.py`, `docs/developers-guide.md`
  (drift-guard subsections).
- Skill: `logisphere-design-review` (full crew + pre-mortem + alternatives).
- cuprum read-only sibling at `/data/leynos/Projects/cuprum`: not exercised —
  the
  Decision Log's no-subprocess/no-cuprum scoping is correct, so no cuprum claim
  required verification this round.
