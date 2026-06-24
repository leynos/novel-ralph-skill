# Logisphere design review — roadmap 5.1.2 — round 3

Adversarial pre-implementation review of `docs/execplans/roadmap-5-1-2.md`
(`desloppify` detection over the §6 offender table). Verdict: **Proceed with
conditions** — the round-3 `found-herself` fix is correct and verified, all 24
rows map to the §6 table with verbatim thresholds, and every locked-library
claim (cuprum, the loader's flag-free `re.compile`, design §9 exit routing) is
verified against real source. One blocking defect remains: a pack `# why`
comment makes a false claim about its own regex (`couldnt-help-but`), exactly
the defect-2 class round 1 raised, in a work item whose entire remedy was to be
verbatim-transcribable without improvisation.

Trail followed: design §3.1-§3.2, §4.4, §9 (lines 689-726); developers-guide
"Rule packs and the loader boundary" (lines 635-641); AGENTS.md (snapshot/e2e,
400-line cap, en-GB); `skill/novel-ralph/references/desloppify-checklist.md` §1
and §6; real source — `rulepack/{parse,schema,errors}.py`,
`contract/runner.py`, cuprum sibling (`cuprum/{catalogue,sh}.py`).

## Blocking defect (back to the planner)

1. **`couldnt-help-but` pack comment contradicts its own pattern (Telefono /
   Doggylump — defect-2 class).** Line 602 comments
   `# couldn't / couldnt / could not all caught.` The pinned pattern is
   `(?i)\bcould\s?n'?t help but\b`. Verified against `re`:

   - `couldn't help but` → match ✓
   - `couldnt help but` → match ✓
   - **`could not help but` → NO match ✗** (the comment claims it matches)

   The construction `\s?n'?t` is "could", an optional space, `n`, an optional
   apostrophe, then `t` — i.e. it matches `nt` or `n't`, never `not` (the `o`
   breaks it). The comment asserts a behaviour the regex does not have. This is
   the identical failure mode round 1 flagged as blocking defect 2 ("a `# why`
   comment asserting behaviour the pattern does not have"), and it lands in the
   one work item (Work item 2) whose round-2 remedy was to make the pack a
   verbatim transcription so the implementer copies it without re-deriving.

   The fix is a binary choice, and the planner must pin one and make the matrix
   test it:
   - **(a) Narrow to the §6 literal.** The §6 row and the §1 canonical example
     are both the contraction ("couldn't help but"). Keep the pattern as-is and
     correct the comment to `# couldn't / couldnt caught; "could not" is the §1
     non-hedge form, out of scope (Decision Log).` Add a Decision Log entry and
     a negative test asserting `could not help but` yields 0 hits, mirroring the
     `verb-ed-adverb` "said sadly" out-of-scope pin.
   - **(b) Widen to the hedge.** If "could not help but" is intended in scope,
     change the pattern to `(?i)\bcould\s?n(?:'?t| not) help but\b` (verified:
     matches all three forms) and keep the comment. Add a positive test for
     `could not help but`.

   As written, the plan ships a false claim and the planned per-rule
   positive/negative matrix would not catch it (the positive uses the
   contraction). Either an implementer trusts the comment and writes a
   `could not` positive test that fails (a wasted iteration the spec-first
   remedy was meant to remove), or the false comment ships verbatim.

## Advisory (non-blocking)

- **`verb-ed-adverb` admits non-verb `-ed` tokens (Wafflecat).** `\w+ed` matches
  "red", "bed", "fed", so "the red door closed softly" and "he bed quietly"
  produce hits. This is an inherent stdlib-`re` limitation (no POS engine), the
  same constraint the plan already pins for `found-herself` and
  `capitalised-abstract-noun`, and the threshold-2 tolerance absorbs incidental
  hits. Not blocking, but the `found-herself` Decision Log explicitly
  enumerates its over-match tolerance; a one-line note that `verb-ed-adverb`
  shares the same `\w+ed`-admits-non-verbs tolerance would make the three
  placeholder rows consistently documented. (Optional; the row's existing
  comment already cites the literal §6 reading.)

## What the plan gets right (verified, credit where due)

- **Round-3 fix is correct.** The `found-herself` pattern
  `(?i)\bfound (?:her|him|them|my|our|your)sel(?:f|ves)[^\S\n]+\w` matches all
  five positives (incl. the §1 examples "found herself crying", "found himself
  agreeing") and rejects all five negatives ("found herself.", "found
  himself!", "found herself, alone", "found her keys", bare "found herself").
  The sole round-3 blocking point is resolved.
- **All 24 rows present, thresholds verbatim.** The pack's
  `(id, threshold, basis)` triples match the §6 table row-for-row; `em-dash` is
  the only
  `per_page` row (threshold 5, page_words 300). The round-1 completeness defect
  (defect 1) and the rule-id-set-equality test stand.
- **Every locked-library claim verified.** cuprum: `sh.py:make` (line 528) →
  `catalogue.lookup` (line 538); `catalogue.py:lookup` (line 79) raises
  `UnknownProgramError` (line 85); `allowlist` is a read-only `frozenset`
  property (line 70). The loader: `parse.py:_compile_pattern` uses
  `re.compile(pattern)` with no flags (line 135), so `.` cannot cross `\n` and
  the line-by-line rationale holds. Design §9 (lines 689-726) confirms snapshot
  - boundary coverage, malformed pack → exit 2, unreadable/absent file → exit 3,
  and "v1 commands shell out to nothing".
- **Runner-extension is mechanically safe.** `RulePackError` and
  `RulePackFileError` both extend `EnvelopeMessagesError` *directly* (siblings
  of `StateInputError`, not subclasses), so the proposed new `except` arms in
  `runner.py:run` are order-independent and cannot shadow the existing
  `StateInputError` arm. The body-fallback alternative is equally viable.
- **Detection model verified.** The line-by-line scan with `[^\n]{0,N}?` bounded
  windows yields the documented results: `it-s-not-just` single-line positive
  matches, the multiline split yields 0 (documented v1 limitation), the
  far-apart cross-sentence case yields 0 (window bound holds). The example
  envelope's density (7 / (312/300) = 6.73) is arithmetically correct.

## Pre-mortem (Doggylump)

- *Six months on, the implementer "fixed" a failing `could not help but` test by
  loosening the pattern unreviewed, or shipped the false comment and a later
  reader trusted it.* Trigger: the line-602 comment claims a behaviour the
  regex lacks. Prevention designable now: pin one reading (narrow or widen) and
  add the matching negative/positive test so the comment and the pattern agree
  and the matrix enforces it.

## Strongest alternative (Wafflecat)

None structurally different remains; the spec-first pack-as-deliverable shape
adopted in round 2 is the right one and round 3 only sharpens a single pattern.
The residual defect is a transcription-fidelity slip, not an architectural
fork. Closing the comment-vs-behaviour gap (and, ideally, a planning-time
assertion that every `# why` comment's claim is mechanically checked by the
matrix) is the last step to a clean proceed.
