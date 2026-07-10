# Logisphere design review — roadmap 2.1.7 (Round 2)

Verdict: PROCEED. The three round-1 blocking items are genuinely resolved against
source, the bijection-split / reconcile-flag spine (D1/D2/D3/D6/D7) is verified,
and the wiring is implementable as written. Two advisories below would tighten the
plan but do not block implementation.

## Round-1 blocking items — disposition

1. **cover-drafts coupling (R1 blocking 1) — RESOLVED.** `_check_word_counts_cover_drafts`
   (`novel_ralph_skill/state/_disk_word_counts.py` lines 128-130) defers
   (`return None`) whenever `manifest != _on_disk_chapter_numbers(working_dir)`,
   confirmed in source. A relaxed drafting subset always satisfies that inequality,
   so cover-drafts never fired on a subset under the strict detector. The plan now
   carries Decision D6, a Risk entry, a "Context and orientation" paragraph, the
   ADR-009 full-blast-radius enumeration mandate (WI1), and the WI2 boundary test
   (drifted-`by_chapter` relaxed subset → full relaxed verdict `()`, plus the
   strict-default paired assertion that the SAME tree fires only
   `manifest-disk-bijection` and not cover-drafts). The test as specified is
   satisfiable and pins exactly the documented boundary.

2. **Positive fixture must prove full cleanliness (R1 blocking 2) — RESOLVED.**
   WI3 step 3 now specifies the exact coherent drafting-subset fixture and asserts
   the FULL relaxed verdict is `()`, not merely the absence of the bijection name,
   paired with a strict-default assertion that the same tree fires exactly
   `manifest-disk-bijection`. Verified against the corpus builder: a `ChapterSpec`
   with `in_manifest=True` is ALWAYS given a directory by `build_working_tree`
   (`tests/working_corpus/_builder.py` line 228 → `_write_chapter` line 170-171),
   so the existing fields cannot express "real drafted chapter in manifest, absent
   on disk". The plan correctly instructs adding a minimal `WorkingTreeSpec` field
   that decouples in-manifest from on-disk for a real chapter and warns not to
   force it through `manifest_only_numbers` (which yields a placeholder, not a
   drafted chapter). This instruction is sound and conservative. (Note: a
   placeholder via `manifest_only_numbers=(3,)` over chapters `{1,2}` would in fact
   also produce a relaxed-clean verdict — `word-counts-match-drafts` compares only
   shared keys and cover-drafts defers — but the plan's chosen route is more
   faithful to the Purpose's "directory lags the manifest" scenario, so the extra
   field is a defensible, not gratuitous, addition.)

3. **Flag-threading mechanism vs `_PREDICATES` uniformity (R1 blocking 3) —
   RESOLVED.** WI2 step 3 commits to one concrete wiring: lift
   `_check_manifest_disk_bijection` out of the uniform `_PREDICATES` loop, call
   it first with the keyword-only flag, run the seven `_TAIL_PREDICATES` through
   loop, concatenate `(head, *tail)`. Verified: `_PREDICATES` in
   `disk_evidence.py` has no caller outside the module (definition line 264, loop
   line 298 only); the bijection is element 0 of `DISK_EVIDENCE_INVARIANT_NAMES`
   (line 101), so head-first + tail-in-order reproduces the single-loop order
   byte-for-byte. A union-order test is mandated. Widening
   `_check_manifest_disk_bijection` with a keyword-only
   `relax_drafting: bool = False` keeps it compatible with the
   `tuple[Callable[[State, Path], Violation | None], ...]` annotation, so
   re-deriving `_PREDICATES` for the comment's sake
   still typechecks under `ty`.

## Round-1 advisories — disposition

- **E2e subcommand argv — RESOLVED.** WI4 now uses
  `sh.make(prog, catalogue=catalogue)("check").run_sync(...)`, matching the proven
  harness (`tests/test_console_scripts_e2e.py` line 44 `_REAL_PATH_ARGV["novel-state"]
  == ("check",)`, lines 113-119). `single_program_catalogue` fixture confirmed at
  `tests/conftest.py` line 246.
- **pytest-timeout-under-xdist citation — RESOLVED.** WI4 cites the global
  `timeout = 30` (`pyproject.toml` line 326, verified) and reuses the existing
  `@pytest.mark.timeout(180)` + `@pytest.mark.slow` precedent
  (`tests/test_console_scripts_e2e.py` lines 127-128, verified) rather than
  asserting composition from memory. No new timeout value invented.
- **Reconciliation payload absence — RESOLVED.** `_check` attaches reconciliation
  only when `disk_evidence` fired (`novel_state.py` line 244, verified). WI4 now
  asserts the relaxed-clean drafting subset carries NO `reconciliation` key, and
  the acceptance criteria record it.

## Re-verified sound against source

- cuprum 0.1.0 absolute-path allowlisting: confirmed in round 1 against
  `/data/leynos/Projects/cuprum/cuprum/catalogue.py`; no cuprum surface change.
- D1 reconcile strictness: `derive_reconciliation` calls
  `check_disk_evidence(state, working_dir)` strict (`reconcile.py` line 345); torn
  `set-chapters` test uses `phase_current="drafting"`
  (`test_set_chapters_reconcile.py` line 125). Default-strict flag leaves it
  untouched.
- Strict split byte-equivalence: `orphans/missing/contiguous` reproduces
  `manifest == on_disk and contiguous` (`disk_evidence.py` lines 122-126).
- `manifest-extra-entry` variant is `dc.replace(_BASE, manifest_only_numbers=...)`
  on the drafting `_BASE` (`_variants.py` line 144-145; `COHERENT_BASELINE ==
  PHASE_STATES["drafting"]`, `_library.py` line 118).
- Oracle twin `_check_manifest_disk_bijection(working_dir)` reads `state.toml`
  from disk itself (`_oracle_disk.py` lines 73-85), so WI3's "read the materialized
  `[phase].current`" mirror is consistent with the twin's disk-reading style.
- Scope: matches roadmap 2.1.7 (`docs/roadmap.md` lines 672-685) exactly — ADR
  required, relax to disk-subset-of-manifest during drafting, re-tighten at
  final-pass/done, `set-chapters` and cover-drafts redesign out of scope.
- ADR 001 deterministic/judgemental boundary: untouched — this is pure
  deterministic validator set logic, no judgemental surface.

## Advisory (non-blocking)

- **Hypothesis property mechanism is under-described.** WI2's property test says
  "build the corresponding `(manifest, on_disk)` sets", but
  `_check_manifest_disk_bijection` does not accept raw sets — it derives `manifest`
  from `state.chapters` and `on_disk` by globbing `working_dir`
  (`disk_evidence.py` lines 122-123). The property test must therefore materialize
  a real tree on disk (via `build_working_tree`) and a `State` per generated
  shape, then call the predicate. This is achievable with the corpus builder and
  the repo's existing Hypothesis usage, but the implementer should read the
  predicate's actual inputs before writing the strategy, and keep the strategy
  constructive (no `assume`-heavy filtering) per the `hypothesis` skill.

- **Oracle-twin signature divergence.** Production
  `_check_manifest_disk_bijection(state, working_dir, *, relax_drafting=...)`
  takes `state`; the oracle twin takes only `working_dir` and re-parses
  `state.toml`. WI3
  step 1 must add the relax path by re-reading `[phase].current` from the
  materialized `state.toml` (the twin's existing idiom), not by widening the twin
  to take `state` — otherwise the twin stops being an independent re-implementation.
  The plan's wording ("reading the materialized `state.toml` `[phase].current`")
  already points this way; the implementer should hold that line.

## Pre-mortem (Doggylump) — re-run

The round-1 pre-mortem scenario (author trusts a mid-draft `check` over a drifted
`by_chapter`, drift surfaces late) is now designed against: D6 documents the
boundary, ADR 009 must enumerate cover-drafts as the second invariant whose
enforcement changes, and the WI2 boundary test pins it. No new 03:00 scenario
emerges from the R2 revisions: the wiring is local, reconcile is provably
untouched (strict default), and the terminal phases re-enforce the exact
bijection before any compile reads the manifest ordering.

## Signposting

Documents and skills relied on: `docs/novel-ralph-harness-design.md` §5.2/§5.4,
`docs/adr-001` (boundary), `docs/roadmap.md` 2.1.7, `docs/developers-guide.md`
"Invariant validation", `docs/users-guide.md` line 171; the `logisphere-design-review`
skill; `leta`-style navigation over `disk_evidence.py`, `_disk_word_counts.py`,
`reconcile.py`, `novel_state.py`, `wordcount.py`, and the corpus
(`_specs.py`, `_builder.py`, `_library.py`, `_variants.py`, `_oracle_disk.py`);
the read-only cuprum sibling at `/data/leynos/Projects/cuprum`.
