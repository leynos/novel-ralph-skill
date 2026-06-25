# Architectural decision record (ADR) 008: the validated chapter-manifest mutator

## Status

Accepted, 2026-06-25. The `[chapters]` manifest is populated by a single
validated command, `novel-state set-chapters`, which writes the manifest, creates
the on-disk chapter directories, and is recovered after a crash by
`novel-state reconcile`. This realises roadmap task 2.2.3 under ADR 001 (scripts
detect and report; the model adjudicates) and design §4.1, §5.1, and §5.4.

## Date

2026-06-25.

## Context and problem statement

The chapter manifest (`[chapters]` in `working/state.toml`) was the one piece of
harness state with **no** sanctioned command to write it. A chapter planned in
`working/plan/chapter-outline.md` therefore had no validated path into
`[chapters]`, and the per-chapter drafting loop was blocked: with a draft on disk
but an empty manifest, `novel-state check` exits 4 on `manifest-disk-bijection`,
`novel-compile` exits 3, and `recount` returns an empty map. ADR 001 forbids
direct `state.toml` edits — all state mutation goes through validated commands —
so the manifest is no exception.

The command must (design §5.1, §5.2): populate `[chapters]` losslessly through the
`tomlkit` seam (ADR 002), create the on-disk `chapter-NN/` directories so the §5.2
manifest-to-disk bijection holds the instant the command returns, refuse an
incoherent plan before any write, and survive a crash mid-turn as a declared,
recoverable state.

## Decision drivers

- ADR 001: the manifest reaches `[chapters]` only through a validated command.
- The §5.1/§5.2 bijection is a hard, immediate invariant: `check` must exit 0
  directly after `set-chapters`.
- Validate before persist (§3.2, §3.4): a refusal leaves `state.toml`
  byte-for-byte intact.
- The manifest is the agent's *judgement* (slug, title, target words), not
  recomputable from disk — unlike `reconcile`'s recount payload.
- The no-deletion constraint and the `[pending_turn]` recovery model (§3.4, §5.4).

## Decision outcome

### Command name and input shape

The subcommand is `set-chapters` (the established `set-cursor` sibling verb reads
consistently). Its body is `set_chapters`. The plan is ingested as one keyword
parameter typed `list[ChapterPlanEntry]`, parsed by Cyclopts from a JSON array:

```bash
novel-state set-chapters --chapters '[
  {"number": 1, "slug": "the-summons", "title": "The Summons", "target_words": 3200},
  {"number": 2, "slug": "the-road", "title": "The Road", "target_words": 2800}
]'
```

`ChapterPlanEntry` is a frozen, slotted, keyword-only input dataclass, distinct
from the on-disk `state.schema.ChapterEntry`; it is never union'd with `str`, the
constraint that lets Cyclopts parse the JSON-array form. It lives in a
dependency-free leaf module so both the command builder and the mutator body
import it as a runtime global (Cyclopts resolves the annotation against the
command function's `__globals__`) without a circular import.

### Exit-code split (exit 2 vs exit 3)

Two distinct refusal channels:

- **Shape faults — exit 2.** Malformed JSON, a missing required field, or a
  wrong-typed field raise a Cyclopts `CoercionError` at parse, which the runner
  maps to the usage-error exit 2.
- **Semantic refusals — exit 3.** A coherent-shaped but incoherent plan — numbers
  not contiguous from 1, a duplicate number or slug, a non-positive target, an
  empty plan, or a *non-empty prior manifest* — raises `StateInputError`, the
  exit-3 state-input channel.

Manifest coherence is a *new pure predicate* (`manifest_coherence_violations`)
the body calls before the §5.2 validate-before-persist pass, not an addition to
`validate_state`: contiguity and uniqueness are write-time preconditions the §5.2
self-consistency set does not own, and folding them in would change `check` for
every existing tree.

### Directory creation and the bijection

`set-chapters` creates the on-disk `working/manuscript/chapter-NN/` directories
so the §5.2 manifest-to-disk bijection holds immediately. It also seeds
`[word_counts].by_chapter` with a zero entry per planned chapter, so the §5.4
`word-counts-cover-drafts` coverage invariant (roadmap task 2.3.6) holds the
instant the command returns and `check` exits 0; zero is the honest count for a
planned, undrafted chapter, and `current` stays 0 = sum.

### One-shot populate, not an editor

When `[chapters]` is already non-empty, `set-chapters` refuses with exit 3:
overwriting a live manifest could orphan chapter directories and drafts.
Re-planning is a distinct, later concern. This refusal keys off "manifest
non-empty", not "non-empty and bijective", so it stays the simplest possible
guard — torn-turn completion is delegated to `reconcile` (below), not to a
`set-chapters` re-run, so the strict refusal strands no half-applied turn.

### Why not a manifest-only write

A manifest-only write (writing `[chapters]` alone, no directories, no bracket) was
rejected. The roadmap mandates the `[pending_turn]` bracket, and the §5.1/§5.2
bijection is a firm immediate invariant: a manifest-only write would leave
manifest `{1..n}` against on-disk `{}`, firing `manifest-disk-bijection` so
`check` exits 4 the instant the command returns. Deferring directory creation is
in no current task, and `reconcile`'s draft-without-manifest-entry path is a
REFUSE, not a repair, so it would not materialise the directories.

### Write ordering: the manifest persists at the intent write

Unlike `reconcile`, whose recount payload is recomputable from disk and so
persists *last*, `set-chapters`'s payload is the agent's judgement and is **not**
on disk anywhere else. It is therefore written into the document and persisted
**together with** the `[pending_turn]` record in the *first* atomic write, before
any directory is created. The fixed order is: load → refuse a non-empty or
incoherent prior (memory only) → edit `[chapters]` and seed `by_chapter` (memory
only) → open `[pending_turn]` naming `state.toml` and each chapter directory →
**one** atomic write (manifest and intent land together) → create the directories
→ append the `log.md` receipt → clear `[pending_turn]` → final atomic write. Every
torn state from the first write onward therefore has the full manifest on disk and
only deterministically-derivable empty directories outstanding. Were the manifest
persisted last (mirroring `reconcile`), a crash in the directory window would
leave the original empty manifest with the agent's plan gone, and a `reconcile`
against an empty manifest would only worsen the bijection.

### Torn-turn recovery and its precedence change

A crash after the intent write leaves a populated `operation="set-chapters"`
`[pending_turn]` over a persisted, populated manifest, with one or more
`chapter-NN/` directories missing — including the realistic **partial-directory**
case (manifest `{1, 2}`, on-disk `{1}`). That fires `manifest-disk-bijection`, a
refuse-class invariant that under the prior precedence short-circuits to REFUSE
(exit 4) before the pending-turn branch runs, and a `set-chapters` re-run is
refused (one-shot populate) — so the obvious recovery was blocked.

The resolution is a **scoped precedence change** in `derive_reconciliation`: a
guarded branch ahead of the refuse arm classifies a `set-chapters` `[pending_turn]`
as a COMPLETE when, and only when, all hold:

- the fired refuse-class set is exactly `{manifest-disk-bijection}` (no second
  contradiction, so the branch never masks one);
- the bijection break is **fully explained** by the pending turn's
  declared-but-missing chapter directories — the manifest is contiguous from 1,
  the on-disk chapter numbers are a subset of the manifest, and the set difference
  equals exactly the missing declared chapter numbers.

When the branch fires, `reconcile` COMPLETEs the turn by creating the missing
`chapter-NN/` directories (derived from the pending turn's `missing_paths`, never
a re-read manifest) and clearing the record. Any *unexplained* break — a stray
draft, an orphan directory, a manifest gap the pending turn does not account for,
or any second refuse-class violation — still REFUSEs.

This is a deliberate amendment to the §5.4 recomputable-artefact set and the
reconcile precedence, not a mechanical tweak. An empty `chapter-NN/` directory
counts as recomputable *given the persisted manifest* (the write ordering above
guarantees it is on disk): it carries no agent judgement and is wholly derivable
from the manifest, exactly like `log.md`. Recovery is therefore a single
sanctioned command — `novel-state reconcile` — with no manual `mkdir` and no
re-run of `set-chapters`.

## Goals and non-goals

- Goals:
  - A single validated command from a planned chapter to `[chapters]`.
  - The §5.2/§5.4 invariants hold the instant the command returns (`check`
    exits 0).
  - A torn turn is a declared, sanctioned-recovery state.
- Non-goals:
  - Re-planning or editing an existing manifest (a later task owns this).
  - Pruning a stray `chapter-NN/` directory the manifest does not name (the
    pre-existing draft-without-manifest-entry bijection variant; `set-chapters`
    adds no new stray-dir behaviour).

## Known risks and limitations

- The precedence change inverts refuse-class precedence for the single, narrowly
  scoped explained-`set-chapters`-bijection case; the guard ensures it never masks
  a second contradiction.
- Slug collisions cannot collide directories (the directory name derives from the
  chapter *number*, not the slug), so duplicate-slug rejection is a
  manifest-quality guard, not a correctness one.

## Outstanding decisions

None. The command name (`set-chapters`), the exit-2/exit-3 split, directory
creation, the one-shot refusal, the manifest-at-intent-write ordering, and the
torn-turn recovery precedence are all fixed here. Re-planning an existing manifest
is deferred to a later roadmap task.
