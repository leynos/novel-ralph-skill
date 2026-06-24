# Post-merge audit — roadmap task 3.1.4

Audit of the codebase after roadmap task 3.1.4 ("Anchor unresolved-BLOCKER
resolution positionally and cover the false-clean direction") merged to `main`
at commit `94ac1d8`. The slice tightens the `no_unresolved_blockers` clause from
a substring test (`[resolved]` appears anywhere on a line) to a positional one
(the stripped line must *end with* the `[resolved]` token), closing the
false-clean direction in which a live BLOCKER that incidentally quoted the token
in its prose was wrongly cleared. It documents the new grammar in
[`done_predicate.py`](../../novel_ralph_skill/state/done_predicate.py),
[`done-conditions.md`](../../skill/novel-ralph/references/done-conditions.md),
the developers' guide, and design §4.2; pins a false-clean corpus tree with an
independent oracle twin; and adds a Hypothesis property pinning the positional
invariant.

The slice is correct and of a high standard for what it set out to do. The
soundness fix is the minimal correct change (`not in` → `not …endswith`), the
existing notes stay correctly classified, the oracle twin is a genuine
re-spelling rather than a re-export, and the new property
(`test_blocker_resolution_is_positional`) constructs valid inputs rather than
filtering, dodging the filtering trap the round-1 review flagged. Documentation
is thorough and the BLOCKER limitations are recorded in both directions.

The findings below are not defects in the 3.1.4 diff; they are pre-existing
contract gaps in the surrounding `no_unresolved_blockers` clause that the
tightening makes more acute and more worth closing now that the grammar is
positional. Finding 1 is the headline: the predicate adjudicates against a
producer convention that is nowhere defined and that the actual critic output
format contradicts.

## Finding 1 — the BLOCKER resolution grammar has no producer contract, and the predicate's `startswith("BLOCKER")` does not match the real critic output format

- Category: separation-of-concerns (producer/consumer contract)
- Severity: high
- Location:
  [`done_predicate.py:277-296`](../../novel_ralph_skill/state/done_predicate.py)
  (`_contains_unresolved_blocker`);
  [`critic-personas.md:81-104`](../../skill/novel-ralph/references/critic-personas.md)
  (the strict BLOCKER output format);
  [`done-conditions.md:111,191-194`](../../skill/novel-ralph/references/done-conditions.md)

The predicate decides a line is a BLOCKER when its stripped text *starts with*
the literal `BLOCKER` (case-sensitive) and clears it only when the same line
*ends with* `[resolved]`. But nothing in the skill instructs the side that
*writes* `critic-notes.md` to emit either shape. The critic-personas reference
(`critic-personas.md:81-104`) fixes a strict output format where blockers appear
under a `## BLOCKER` section heading with each finding as `### B1 — <label>`,
quoted passage, "What's wrong:", and "Suggested action:". Under that format:

- No emitted line's stripped text starts with `BLOCKER`. The section line is
  `## BLOCKER` (stripped: `## BLOCKER`, which starts with `##`); the finding
  lines are `### B1 — …`. So `_contains_unresolved_blocker` matches **zero**
  lines and `no_unresolved_blockers` returns `True` against genuine critic
  output — an exit-0 lie strictly larger than the mid-line false-clean one 3.1.4
  fixed, because it fires on *every* real unresolved blocker, not a near-miss
  edge.
- There is no defined way to *mark a blocker resolved*. The loop is told to
  "address every BLOCKER" (`SKILL.md:353`) and that done requires "no unresolved
  BLOCKER findings" (`done-conditions.md:111`), but no reference tells it to
  append `[resolved]` to anything. The `[resolved]` trailing-token grammar is
  invented by the predicate and the corpus, never by the producer's spec.

The round-1 design review's advisory A5 already noted "the grammar-vs-critic-
format mismatch as a known limitation" and the developers' guide records the
case/spelling-variant brittleness, but the deeper gap — that the predicate's
*both* anchors (`startswith` and `endswith`) are unbacked by any producer
contract — remains open and is the larger soundness risk.

Proposed fix: close the contract from the producing side, not by loosening the
predicate. (a) Add a "Resolving a BLOCKER" convention to `critic-personas.md`
and/or `done-conditions.md` that defines exactly how a resolved finding is
marked, and align the predicate's recogniser to the actual heading-based format
(match `### B<n>` finding lines under a `## BLOCKER` section, or a `BLOCKER:`
inline form, whichever the loop is told to emit). (b) Add a corpus tree built
from a *real* critic-personas-shaped `critic-notes.md` with an unresolved `### B1`
finding and assert `no_unresolved_blockers` is `False` against it — today no
test exercises the predicate against the format the producer is specified to
emit, so the mismatch is invisible to the suite. This is a redesign beyond a
single audit fix and is the strongest candidate for a roadmap item (see proposed
roadmap items).

## Finding 2 — the `endswith` tightening silently introduces a new false-dirty direction (a resolved BLOCKER with trailing text) that is undocumented and untested

- Category: test-gap / docs-gap
- Severity: low
- Location:
  [`done_predicate.py:294`](../../novel_ralph_skill/state/done_predicate.py)
  (`not stripped.endswith(_RESOLVED_TOKEN)`);
  [`developers-guide.md:578-583`](../../docs/developers-guide.md)

Moving from "contains `[resolved]`" to "ends with `[resolved]`" closes the
false-clean direction but opens a symmetric false-dirty one the old rule did not
have: a genuinely resolved blocker that carries any trailing text after the
marker — for example `BLOCKER B1 fixed [resolved] (see log entry 42)` or
`… [resolved].` with a trailing full stop — is now classified *unresolved* and
keeps the loop running. The developers' guide enumerates the documented
limitations "in *both* directions" but lists only the prose near-miss and the
case/spelling variants; it does not name this new "resolved-with-trailing-text"
direction, which is a direct consequence of *this* change, not a pre-existing
one. Whether it is a real risk depends entirely on the (undefined) producer
convention from Finding 1: if the loop ever writes anything after the marker,
the predicate hangs the loop on a resolved blocker.

Proposed fix: pin the decision explicitly. If trailing text after the marker is
forbidden, say so in the producer convention (Finding 1) and add a corpus/unit
case asserting `… [resolved] trailing` is treated as unresolved *by design*
(documenting the trade as deliberate). If trailing text should be tolerated,
relax the recogniser to "the stripped line *contains* `[resolved]` as a trailing
*token* (last whitespace-separated token, or last token before terminal
punctuation)" and add the corresponding case. Either way the developers' guide's
"limitations in both directions" sentence should name this third edge so the
asymmetry the tightening created is recorded.

## Finding 3 — the resolution marker is case- and spelling-brittle with no negative test pinning the documented mis-classification

- Category: test-gap
- Severity: low
- Location:
  [`done_predicate.py:74`](../../novel_ralph_skill/state/done_predicate.py)
  (`_RESOLVED_TOKEN`);
  [`developers-guide.md:580-581`](../../docs/developers-guide.md)
  (`RESOLVED`, `(resolved)` "still mis-classified")

The developers' guide states that case or alternative-spelling variants
(`RESOLVED`, `(resolved)`) are "still mis-classified (out of scope per
D-BLOCKER-SCOPE)". This is an honest limitation, but it is asserted only in
prose: no test pins the *current* behaviour, so a future well-meaning change
(e.g. someone adding `.casefold()` to "fix" it) could silently flip the
mis-classification without any test going red, and the guide's claim would
quietly become false. The corpus pins the false-dirty prose near-miss and the
false-clean mid-line edges but not the documented case/spelling edge.

Proposed fix: add an `xfail(strict=True)`-marked (or plainly asserting-current-
behaviour) test that writes `BLOCKER … [RESOLVED]` and `BLOCKER … (resolved)`
and asserts they are treated as *unresolved* today, with a docstring citing
D-BLOCKER-SCOPE. This converts the prose limitation into an executable, change-
detecting fact and gives the eventual scope-expansion task a ready red test to
flip.

## Finding 4 — the BLOCKER classification predicate is inlined in a generator and not independently unit-testable

- Category: ergonomics / test-gap
- Severity: low
- Location:
  [`done_predicate.py:293-296`](../../novel_ralph_skill/state/done_predicate.py)

The line-level rule (`stripped.startswith(_BLOCKER_PREFIX) and not
stripped.endswith(_RESOLVED_TOKEN)`) is embedded inside the `any(...)` generator
in `_contains_unresolved_blocker`, which only runs against a file path. Every
test of the rule must therefore round-trip through `tmp_path`, a written
`critic-notes.md`, and a built working tree (see
`test_blocker_resolution_is_positional`, which spins a `TemporaryDirectory` and
an all-hold tree per Hypothesis example just to classify one string). The rule
is a pure `str -> bool` function; extracting it (e.g. `def _line_is_unresolved
_blocker(stripped: str) -> bool`) would let the property test and the unit cases
assert directly over strings — faster, clearer, and with no filesystem in the
loop — while `_contains_unresolved_blocker` keeps only the file-fault boundary.
The oracle twin could mirror the same split, keeping the cross-check honest.

Proposed fix: extract the line-classification rule into a private pure helper in
`done_predicate.py` and rewrite the positional property and the unit BLOCKER
cases to call it directly, leaving the file-reading helper as a thin wrapper
that owns only the `FileNotFoundError` boundary. Low priority; purely an
ergonomic and test-speed improvement with no behavioural change.

## Items verified sound (no action)

- The 3.1.4 soundness fix is correct and minimal; the oracle twin
  (`_done_predicate_oracle.py:64`) re-spells the rule independently and is pinned
  equal to production on every tree by `test_blocker_oracle_twin_agrees`
  ([`tests/test_working_corpus_done_predicate.py:131-144`](../../tests/test_working_corpus_done_predicate.py)).
- The read-only invariant (ADR-001) and the absent-vs-fault boundary (D-FAULT)
  are preserved: the `endswith` swap is in-memory line classification only and
  cannot swallow or raise a new fault.
- The Hypothesis property constructs valid inputs (fixed `X` sentinel,
  `[`/`]`/newline-excluded alphabet) rather than filtering, so it will not flake
  on whitespace-only suffixes — the round-1 A1 advisory was actioned.
- The `S105` suppressions on `_RESOLVED_TOKEN` carry an accurate why-comment in
  both production and the twin.
