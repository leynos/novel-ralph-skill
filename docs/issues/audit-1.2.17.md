# Post-merge audit — roadmap task 1.2.17

Task 1.2.17 extended the multiplexer-surface doc sweep into
`skill/novel-ralph/references/`, flipping the retired console-script
invocations in `state-layout.md`, `done-conditions.md`, and
`critic-personas.md` to the single `novel <sub>` surface ADR 007 fixes. It is
the third pass in the same lineage: 1.2.14 swept the design and `SKILL.md`,
1.2.16 swept the two guides, and 1.2.17 swept three of the eight reference
files. Each pass was itself spawned by the prior audit naming the next
untracked surface.

This audit reviews the merged state at `origin/main` (commit `5774178`) for
refactoring opportunities, duplication, complex conditionals, ergonomic
awkwardness, high-similarity functions, inconsistencies, separation-of-concerns
and command/query-separation (CQS) issues, and gaps in documentation comments,
developer/user documentation, and test coverage. Each finding records a
location and a concrete proposed fix.

The three reference files 1.2.17 owns are clean: no `novel-state`,
`novel-done`, or `novel-compile` invocation survives in them, and the noun-form
`desloppify` pass was correctly preserved. The material findings are wholly in
the surfaces the sweep lineage has not yet reached. The most concrete is that a
**fourth** reference file in the same just-swept directory —
`desloppify-checklist.md` — still presents the retired `desloppify` console
script as a runnable, flag-bearing invocation, exactly the defect class 1.2.17
was created to close. A secondary code finding records a verbatim orchestration
skeleton repeated across five state mutators.

## 1. `desloppify-checklist.md` still invokes the retired `desloppify` script

- **Category:** inconsistency
- **Severity:** medium
- **Location:** `skill/novel-ralph/references/desloppify-checklist.md` lines 294
  and 302

The 1.2.17 task description drew the load-bearing distinction explicitly: the
noun-form `desloppify` (which names the *desloppification operation*) stays,
but a retired console-script *invocation* (a flag-bearing command line) must
flip to `novel desloppify`. The sweep applied that rule to `state-layout.md`,
`done-conditions.md`, and `critic-personas.md` — but `desloppify-checklist.md`,
a sibling reference file in the very same directory, was outside the
three-file scope and was never swept. It still carries two flag-bearing
invocations of the retired script:

- Line 294: `desloppify --pack <ai-isms.toml>` "to scan a chapter against it"
  (the full path is `novel_ralph_skill/rulepack/packs/ai-isms.toml`).
- Line 302: `` `desloppify --ledger device-ledger.toml` ``.

These are command invocations, not the noun form: each carries a flag and is
presented as a command an operator runs. Under ADR 007 the only shipped surface
is `novel desloppify`, so a reader following this checklist runs a command that
no longer resolves on `PATH`. The `developers-guide.md` already uses the
correct `novel desloppify` spelling consistently (lines 102, 307, 336, 1170,
1227 and elsewhere), so the skill reference is now internally inconsistent with
the rest of the swept documentation.

**Proposed fix:** flip both invocations to the multiplexer surface —
`novel desloppify --pack …` (line 294) and `novel desloppify --ledger …`
(line 302) — leaving every noun-form mention of the desloppify *operation*
untouched, exactly as 1.2.17 handled the three swept files. This closes the
last flag-bearing retired invocation in the live skill surface.

## 2. Later ADRs (008, 009, 010) and `contents.md` retain the retired surface

- **Category:** docs-gap
- **Severity:** low
- **Location:** `docs/adr-008-chapter-manifest-mutator.md` (lines 6, 8, 21, 22,
  52, 168), `docs/adr-009-drafting-bijection-relaxation.md` (lines 6, 28, 38,
  60, 149), `docs/adr-010-gate-drafting-mutators.md` (line 10),
  `docs/contents.md` (lines 42, 46, 51)

ADRs 008, 009, and 010 were authored against the `novel-state` surface and
still name it inline. ADR 008 goes further: line 52 presents a fenced bash
example, `novel-state set-chapters --chapters '[…]'`, as a runnable
invocation — not as period history. `contents.md`, the documentation index,
then echoes those names when summarising what each ADR records (`novel-state
set-chapters`, `novel-state check`, `novel-state set-gate`).

This is the same surface defect the 1.2.14/1.2.16/1.2.17 lineage exists to
close, on a surface none of those tasks scoped. ADR 007's own migration plan
(lines 114-126) lists the sweep targets — design prose, diagrams, `SKILL.md` —
but names neither the later ADRs nor `contents.md`, and ADRs 008-010 carry no
cross-reference back to ADR 007's surface change. ADR 005 legitimately retains
the retired names because it is the *superseded* record (the five-script
surface ADR 007 replaced); that is correct history and must stay.

The severity is low because ADRs are decision records read for rationale, not
copy-paste setup; the harm is a reader copying ADR 008's `set-chapters` example
verbatim. But the asymmetry is real: a reader cannot tell from ADR 008 that its
example command no longer resolves.

**Proposed fix:** flip the inline command *invocations* in ADRs 008-010 and the
index entries in `contents.md` to the `novel <sub>` surface (e.g. ADR 008 line
52 → `novel state set-chapters …`), preserving each ADR's decision narrative.
Alternatively, if the project's convention is that ADRs are immutable, add a
short "surface note" to each of ADRs 008-010 pointing at ADR 007 and stating
that the inline `novel-state …` invocations now read `novel state …`. Either
way `contents.md`, being a live index rather than a historical record, should
name the current surface.

## 3. Five state mutators repeat a verbatim load/edit/validate/write skeleton

- **Category:** duplication
- **Severity:** low
- **Location:** `novel_ralph_skill/commands/_state_mutators.py` (`set_cursor`,
  lines 234-256), `novel_ralph_skill/commands/_gate_drafting_mutators.py`
  (`_set_gate` 168-183, `_complete_final_pass` 242-253, `_set_fangirl`
  278-300, `_set_critic_pass` 327-342)

Five mutator bodies share an identical orchestration skeleton, differing only
in the edit step and the result/message shape:

```text
path = _state_path()
document = _load_document_or_state_error(path)
_state_view_or_state_error(document)          # structural-completeness proof
… edit document in place …                    # the only varying logic
proposed = _state_view_or_state_error(document)
_refuse_if_incoherent(proposed, context=…)
write_document_atomically(document, path)
return CommandOutcome(code=SUCCESS, result=…, messages=[…])
```

The shared step helpers (`_load_document_or_state_error`,
`_state_view_or_state_error`, `_refuse_if_incoherent`) were already extracted
by earlier audits, which is good — but the *sequencing* of those steps, plus
the discarded structural-completeness view and the final write, is copied
verbatim five times. The repeated structural-completeness comment ("Derive the
typed view first to prove the document is structurally complete …") appears in
both `_set_gate` and `set_cursor`, signalling the same load-bearing invariant
re-explained per copy. `set-fangirl` and `set-critic-pass` add a precondition
check between view and edit, but otherwise follow the same arc.

**Proposed fix:** extract a single higher-order helper in `_state_mutators.py`,
e.g. `apply_state_mutation(*, context, edit, build_result, message)` (or a
small context-manager that yields the loaded document and runs the
load → structural-proof … re-view → refuse → write sentinel around the caller's
edit), so each mutator supplies only its edit closure and write-shaped result.
This removes the five-way structural duplication and gives the
structural-completeness proof and the validate-before-persist ordering a single
home, so a future change to the refusal contract touches one site, not five.
Keep the per-mutator precondition checks (fangirl range, critic `pass >= 1`) as
an optional pre-edit hook the helper invokes, preserving their distinct exit-3
messages.

## 4. No regression test pins the reference files clean of the retired surface

- **Category:** test-gap
- **Severity:** low
- **Location:** `tests/` (no surface-sweep guard for
  `skill/novel-ralph/references/`); the swept files are
  `skill/novel-ralph/references/state-layout.md`, `done-conditions.md`,
  `critic-personas.md`

The 1.2.14/1.2.16/1.2.17 sweep lineage has flipped four documentation
surfaces by hand, and each subsequent audit has had to re-discover by grep that
a sibling surface was missed (this audit's findings 1 and 2 are exactly that).
Nothing in the test suite asserts that the swept surfaces *stay* swept: a future
edit could reintroduce `novel-state init` into `state-layout.md` and no gate
would catch it.

**Proposed fix:** add a lightweight documentation guard test (a simple
content-scan over the skill reference files and the live guides) asserting that
no retired console-script *invocation* — a `novel-state`, `novel-done`, or
`novel-compile` verb, and a flag-bearing `desloppify`/`wordcount` — survives,
while explicitly allowing the noun-form `desloppify` and the superseded ADR 005.
This converts the manual grep each audit performs into a standing regression
gate and makes "the sweep is complete" a checkable property rather than an
audit-time observation.

## 5. `desloppify --ledger PATH` invocation in the terms of reference

- **Category:** inconsistency
- **Severity:** low
- **Location:** `docs/terms-of-reference.md` line 384

The terms-of-reference document names the retired script directly:
`` `desloppify --ledger PATH` enforces it ``. As a problem-space document the
ToR predates the surface decision, so this is lower-harm than the live skill
reference in finding 1, but it is still a flag-bearing invocation of a command
that no longer ships.

**Proposed fix:** flip to `novel desloppify --ledger PATH` if the ToR is
treated as a maintained reference, or leave it and rely on a dated note that the
command surface was later unified under ADR 007. Bundle this with finding 1 if a
broader retired-invocation sweep is scheduled.
