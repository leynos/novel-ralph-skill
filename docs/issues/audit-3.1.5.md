# Post-merge audit — roadmap task 3.1.5

Audit of the codebase after roadmap task 3.1.5 ("Align `no_unresolved_blockers`
to the real `critic-personas.md` format and define the resolution producer
contract") merged to `main` at commit `be64cef`. The slice realigns the
`no_unresolved_blockers` clause from a `startswith("BLOCKER")` line test — which
matched zero lines against genuine critic output and so read clean against every
live blocker — to the spiteful critic's real strict output format: a `## BLOCKER`
section heading carrying `### Bn — <label>` finding headings, a finding resolved
by a trailing space-then-`[resolved]` token. It extracts the heading grammar into
the pure
[`_blocker_notes.py`](../../novel_ralph_skill/state/_blocker_notes.py), documents
the producer/consumer convention on both sides
([`critic-personas.md`](../../skill/novel-ralph/references/critic-personas.md)
"Resolving a BLOCKER" and
[`done-conditions.md`](../../skill/novel-ralph/references/done-conditions.md)),
the developers' guide, and design §4.2, and expands the unit, property, corpus
oracle, and BDD coverage in both directions.

The slice is correct and of a high standard. It closes the exact exit-`0` lie
that audit-3.1.4 Finding 1 flagged as the headline contract gap: the recognizer
now matches genuine critic output, the producer convention is written once and
shared by both the side that writes notes and the side that reads them, the
section-scoping walk is sound, and the new module keeps `done_predicate.py` under
the AGENTS.md 400-line cap (337 lines). The corpus oracle in
[`_done_predicate_oracle.py`](../../tests/working_corpus/_done_predicate_oracle.py)
is a genuine independent re-spelling rather than a re-export, the Hypothesis
property pins the positional invariant on the extracted pure helper without a
filesystem round-trip, and the en-GB Oxford-spelling convention holds throughout
the new prose.

The findings below are minor. None is a defect in the 3.1.5 diff; they are
small residual documentation and test-coverage gaps in and around the clause that
are cheap to close now that the grammar is settled.

## Finding 1 — the `done-conditions.md` predicate pseudocode uses an unpadded `chapter-{id}` path that the shipped code never produces

- Category: inconsistency (docs vs code)
- Severity: low
- Location:
  [`done-conditions.md:184`](../../skill/novel-ralph/references/done-conditions.md)
  (`notes = working_dir / f"manuscript/chapter-{chapter_id}/critic-notes.md"`);
  [`_disk_paths.py:19-21`](../../novel_ralph_skill/state/_disk_paths.py)
  (`_chapter_dir_name` returns `chapter-{number:02d}`)

The reference predicate pseudocode joins the notes path as
`chapter-{chapter_id}`, but every shipped clause —
[`no_unresolved_blockers`](../../novel_ralph_skill/state/done_predicate.py),
`all_chapters_flagged`, and the §5.4 detector — derives the directory through
`_chapter_dir_name`, which zero-pads to `chapter-NN` (`chapter-01`, not
`chapter-1`). A reader following the pseudocode literally would look in the wrong
directory for any single-digit chapter. The same paragraph already carries a
"deliberate divergence" note for the manifest-versus-outline chapter set, so the
reference is the right place to record this padding too.

- Proposed fix: in the pseudocode, write the path as
  `f"manuscript/chapter-{chapter_id:02d}/critic-notes.md"` (and the sibling
  `done.flag` join, if present), or add a one-line note under the predicate that
  the materialized layout is the zero-padded `chapter-NN` form per
  `state-layout.md`, so the pseudocode and the shipped `_chapter_dir_name` agree.

## Finding 2 — no end-to-end scenario covers the cap-reached `[resolved]` path letting `novel-done` exit 0

- Category: test-gap
- Severity: low
- Location:
  [`novel_done.feature`](../../tests/features/novel_done.feature) (the BLOCKER
  scenarios cover the live `### B1` and incidental `[resolved]` paths, both
  exit-1, but not the resolved-and-otherwise-complete exit-0 path);
  [`test_done_predicate_blockers.py:92-100`](../../tests/test_done_predicate_blockers.py)
  (`test_resolved_blocker_is_clean` covers it at the function level only)

The whole reason the `[resolved]` token exists is the cap-reached resolution
path the producer contract documents: when the spiteful critic hits its pass cap
of 4, an unresolved finding is logged rather than deleted, and a since-fixed one
is marked closed in place with the token rather than vanishing. The unit test
`test_resolved_blocker_is_clean` pins that a `[resolved]`-marked finding holds the
clause, but there is no behavioural scenario asserting that a tree which is
otherwise complete and whose only blocker is `[resolved]`-marked actually drives
`novel-done` to exit `0`. The exit-`0` direction is the one the harness loop
terminates on, so it is the more consequential one to pin end-to-end, and the
feature file already has the harness wiring to express it.

- Proposed fix: add a `novel_done.feature` scenario — "a `[resolved]`-marked
  BLOCKER in an otherwise-complete tree is declared done" — that starts from the
  all-clauses-hold tree, writes a `### B1 — … [resolved]` finding into the first
  chapter's `critic-notes.md`, and asserts `novel-done` exits `0` with every
  clause true. A matching `Given` step can reuse the existing all-hold tree
  builder.

## Finding 3 — `state-layout.md` describes `critic-notes.md` without cross-linking the BLOCKER grammar it must now satisfy

- Category: docs-gap
- Severity: low
- Location:
  [`state-layout.md:41`](../../skill/novel-ralph/references/state-layout.md)
  (`critic-notes.md  # overwritten each spiteful pass`)

`state-layout.md` is the layout reference a producer-side reader consults to
learn what files live where. Its `critic-notes.md` entry now carries a load-bearing
on-disk grammar — the `## BLOCKER` / `### Bn` / `[resolved]` convention that
`novel-done` adjudicates against — but the entry only annotates the overwrite
cadence and points nowhere. A reader who finds `critic-notes.md` here would not
learn that its body shape is contractual without separately discovering
`critic-personas.md` "Resolving a BLOCKER". This is a cross-reference gap, not a
content gap: the format itself is documented thoroughly elsewhere.

- Proposed fix: extend the `critic-notes.md` annotation in `state-layout.md` with
  a brief pointer, for example
  `# overwritten each spiteful pass; BLOCKER grammar in critic-personas.md`, so
  the layout reference links to the format reference the file body must satisfy.

## Finding 4 — the resolved-suffix token is split across the production and oracle modules with no shared definition, inviting silent drift

- Category: duplication
- Severity: low
- Location:
  [`_blocker_notes.py:39-43`](../../novel_ralph_skill/state/_blocker_notes.py)
  (`_RESOLVED_TOKEN = "[resolved]"`, `_RESOLVED_SUFFIX = f" {_RESOLVED_TOKEN}"`);
  [`_done_predicate_oracle.py:39`](../../tests/working_corpus/_done_predicate_oracle.py)
  (`_RESOLVED_MARK = " [resolved]"`)

The oracle deliberately re-spells the grammar so the corpus cross-check is
genuine rather than a re-export — this is sound and should stay independent. The
observation is narrower: the literal token string `[resolved]` and the section
heading `## BLOCKER` now appear as independent literals in the production module,
the oracle module, and several prose references, so a future change to the token
spelling (the case-sensitivity limitation in audit-3.1.4 Finding 3 is the most
likely trigger) must be threaded through every site by hand. The case-variant
test (`test_case_variant_token_stays_unresolved`) guards the production side
against an accidental flip, but nothing guards the production token literal and
the documented token in the references against drifting apart.

- Proposed fix: leave the oracle's independent re-spelling as-is (its
  independence is the point), but add a single assertion — or a doctest — that
  pins the production `_RESOLVED_TOKEN` literal equal to the spelling quoted in
  `critic-personas.md` / `done-conditions.md`, so a future token change cannot
  silently desynchronize the predicate from its own producer contract. If a
  lighter touch is preferred, a code comment in `_blocker_notes.py` naming the
  two reference sites as the source of truth would at least make the coupling
  discoverable.
