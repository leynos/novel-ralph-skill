# Architectural decision record (ADR) 009: the phase-gated drafting bijection relaxation

## Status

Accepted, 2026-06-25. While `[phase].current == drafting`, the user-facing
`novel-state check` relaxes the §5.2 invariant-5 manifest-to-disk bijection to
**disk-subset-of-manifest**: every on-disk `chapter-NN/` directory must still map
to a manifest entry, but a manifest entry need not yet have a directory. The
orphan direction and the manifest-contiguity check still fire in every phase, and
the exact bijection returns at `final-pass` and `done`. This realises roadmap task
2.1.7 under ADR 001 and design §5.2/§5.4.

## Date

2026-06-25.

## Context and problem statement

Design §5.2 invariant 5 requires an exact bijection between the `[chapters]`
manifest in `working/state.toml` and the on-disk
`working/manuscript/chapter-NN/` directories: every manifest entry must have a
directory and every directory must have a manifest entry. This is enforced by
`_check_manifest_disk_bijection` in
`novel_ralph_skill/state/disk_evidence.py`, the disk-evidence twin of the corpus
oracle's same-named predicate.

Beta testing found the exact bijection makes `check` unusable for the whole
drafting phase. Chapter planning (`novel-state set-chapters`) populates the
manifest with every planned chapter the instant planning finishes, but during
drafting only the chapters drafted so far need have a populated directory. A
workflow that does not pre-create every directory therefore holds manifest
`{1, 2, 3}` against on-disk `{1}` for the whole drafting run, so `check` exits 4
on `manifest-disk-bijection` throughout — so an author cannot use `check` to
confirm a mid-draft tree is honest.

The subset is honest only while chapters are still being drafted. At `final-pass`
every planned chapter must exist on disk: the manifest-to-disk bijection is the
ordering guarantee `novel-compile` relies on (design §4.3), so it must hold again
before any final compile.

## Decision drivers

- The roadmap's success criterion is one-directional: "disk subset of manifest"
  passes during drafting; an on-disk chapter absent from the manifest (an orphan
  directory) still flags, and the exact bijection tightens back at `final-pass`
  and `done`.
- `derive_reconciliation` (ADR 008) drives the torn `set-chapters` COMPLETE
  precedence off the **strict** bijection firing, and the decisive reconcile test
  builds that torn tree with `phase=drafting`. The relaxation must not suppress
  the bijection signal that path reads.
- The corpus structural oracle (an independent cross-check) is pinned to the
  production detector on every corpus tree under the strict call; the default
  behaviour of `check_disk_evidence` must stay strict so the agreement suite is
  unchanged.
- §4.3 compile ordering depends on the bijection holding before compile, which
  happens at `final-pass`, after drafting.

## Decision outcome

While `[phase].current == drafting`, `novel-state check` accepts a tree whose
on-disk chapter set is a **subset** of the manifest. The relaxation is scoped,
one-directional, and phase-gated:

- **Suppressed during drafting only:** the missing-directory direction (a manifest
  entry with no `chapter-NN/` directory).
- **Always fires, in every phase:** the orphan direction (an on-disk directory
  with no manifest entry) and the manifest-contiguity check (the manifest must be
  contiguous from 1 with no gaps).
- **Tightens back:** at `final-pass`, `done`, and every non-drafting phase the
  exact bijection is enforced, so the §4.3 ordering guarantee holds before any
  final compile.

### Why a flag, not an unconditional predicate change

The relaxation is exposed as a keyword-only, default-strict parameter on
`check_disk_evidence`:

```python
def check_disk_evidence(
    state: State,
    working_dir: Path,
    *,
    relax_drafting_bijection: bool = False,
) -> tuple[Violation, ...]: ...
```

The user-facing `check` (`novel_ralph_skill/commands/novel_state.py`) passes
`relax_drafting_bijection=True`. `derive_reconciliation`
(`novel_ralph_skill/state/reconcile.py`) keeps the default `False` (strict),
because it drives the torn `set-chapters` COMPLETE precedence off the strict
bijection firing at `phase=drafting`
(`tests/test_set_chapters_reconcile.py` builds that tree with
`phase_current="drafting"`). A default-strict flag leaves reconcile and the corpus
agreement suite untouched while letting only the user-facing checker relax.

An unconditional phase-gating inside the predicate was rejected: it would break
the reconcile precedence. A separate `check_disk_evidence_relaxed` function was
rejected: it duplicates the eight-predicate assembly, where a flag is smaller. A
command-layer drop of the `manifest-disk-bijection` violation after the fact was
rejected: the `Violation` detail is a free-text string, so the command layer
cannot tell a missing-direction-only break from an orphan break without
re-deriving the direction or widening `Violation`; the flag keeps the
direction-classification in the one place that already holds the manifest and
on-disk sets.

## Consequences

### The full blast radius

The relaxation changes the enforcement of exactly **two** disk-evidence
invariants during drafting:

1. **`manifest-disk-bijection`** — relaxed to disk-subset-of-manifest. The orphan
   direction and the contiguity check still fire; only the missing-directory
   direction is suppressed during drafting.

2. **`word-counts-cover-drafts`** — **not enforced** during a relaxed subset. This
   is a consequence, not a regression. `_check_word_counts_cover_drafts`
   (`novel_ralph_skill/state/_disk_word_counts.py`) already defers (returns
   `None`) on any tree where `manifest != on_disk`, because it recomputes
   `by_chapter` by keying off the manifest and a non-bijective manifest makes that
   recount untrustworthy; the deferral keeps it from double-firing with the
   bijection signal. A relaxed drafting subset always satisfies
   `manifest != on_disk` (that is precisely what "subset" means), so for every
   tree the relaxation newly accepts, `word-counts-cover-drafts` was *already*
   deferring under the strict detector — it has never fired on a subset. The
   relaxation therefore does not silence a firing check; it removes the louder
   `manifest-disk-bijection` signal that previously sat in front of the
   already-silent cover-drafts deferral. `word-counts-cover-drafts` re-enforces
   once the tree returns to bijection (every drafted chapter gets its directory)
   and at `final-pass`/`done` where the strict bijection is mandatory.

The remaining **six** disk-evidence predicates — `cursor-plan-present`,
`done-flag-without-draft`, `compiled-matches-drafts`, `pending-turn-cleared`,
`word-counts-match-drafts`, and `log-present` — do not read the manifest-to-disk
equality and are unchanged. In particular `word-counts-match-drafts` compares only
the chapter keys shared between the table and disk, so it stays clean on a subset
whose present drafts match the table.

### Reconcile is unchanged

`derive_reconciliation` reads the strict bijection (the default flag), so the torn
`set-chapters` COMPLETE precedence (ADR 008) is unaffected even though that torn
tree carries `phase=drafting`. The strict/relaxed split is the controlling reason
the relaxation is a flag and not an unconditional predicate change.

### Compile ordering is unweakened

The manifest-to-disk ordering guarantee `novel-compile` depends on (design §4.3)
holds again at `final-pass` before any final compile, because the exact bijection
re-tightens at the terminal phases. Relaxing during drafting does not weaken
compile ordering: compile runs after the bijection re-tightens.

## Known risks and limitations

- A relaxed drafting subset leaves `word-counts-cover-drafts` un-enforced, so a
  `by_chapter` key-set drift on a subset tree is not caught until the tree returns
  to bijection or reaches `final-pass`/`done`. This is the documented boundary
  above, not a new gap: the recount is untrustworthy off a non-bijective manifest
  by design, so cover-drafts cannot meaningfully run on a subset anyway.
- The relaxation is gated on `Phase.DRAFTING` identity; a malformed
  `state.phase.current` cannot reach the relaxed path because `current` is parsed
  into the `Phase` `StrEnum` before `check` runs.

## Outstanding decisions

None. The disk-subset-of-manifest relaxation, its phase gate (drafting only), the
one-directional guarantee (orphan and contiguity still fire), the default-strict
flag, and the strict/relaxed split between `check` and `reconcile` are all fixed
here. Re-keying `word-counts-cover-drafts` off the on-disk drafted subset rather
than the manifest is a separate detector redesign, deferred to a later roadmap
task.

## References

- Design §5.2 (invariant 5), §5.4 (the disk-authoritative model), §4.3 (the
  compile ordering guarantee).
- ADR 001 (scripts detect and report; the model adjudicates).
- ADR 008 (the validated chapter-manifest mutator and the torn `set-chapters`
  reconcile precedence the strict bijection drives).
- Roadmap task 2.1.7.
