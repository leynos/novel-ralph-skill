# Post-merge audit — roadmap task 6.3.7

Audit of the codebase after roadmap task 6.3.7 ("Pin the `SKILL.md` command
contract to code with a drift-guard test") merged to `main` at commit
`359c130`.

The merged change closes the last unguarded copy of the shared interface
contract. It adds a pure markdown scanner
([`tests/_skill_contract_scanner.py`](../../tests/_skill_contract_scanner.py))
and a docs-level drift-guard
([`tests/test_skill_contract_drift_guard.py`](../../tests/test_skill_contract_drift_guard.py))
that pin the agent-facing exit-code table and the six-field JSON envelope
skeleton in [`skill/novel-ralph/SKILL.md`](../../skill/novel-ralph/SKILL.md) to
the live `ExitCode` enum, the `Envelope` dataclass field order, and
`ENVELOPE_SCHEMA_VERSION`, cross-checked against ADR-003 Table 2 and design
§3.1/§3.2. The work is careful and well-documented: the scanner is pure over
document text, the guard module's two parsing carve-outs (Meaning-column-only
by keyword; the §3.1-region-narrowing before the first JSON fence) are recorded
in the docstrings and exercised by planted-fixture unit tests, and a dedicated
`TestSkillContractGuardNonVacuous` class proves the sliced regions are
non-empty so no guard passes vacuously. The split into a sub-400-line scanner
sibling follows the established `tests/_state_layout_scanner.py` precedent.

The standout strength of 6.3.7 is also the seam for this audit's findings. The
new guard derives the envelope field order from the *code* —
`_envelope_field_order()` reads `dataclasses.fields(Envelope)`
([`tests/test_skill_contract_drift_guard.py`](../../tests/test_skill_contract_drift_guard.py)
line 209) — making the dataclass the single source of truth for the field set
and order. But three pre-existing copies of that same field order remain
hand-written and unpinned to the dataclass, so the contract the new guard
just anchored is still re-spelled three times by literal tuples that can drift
from the dataclass the guard treats as canonical (Finding 1). The remaining two
findings record that 6.3.7's scanner is now the third independent markdown
fence/region parser in the test suite, reimplementing a CommonMark fence regex
(Finding 2) and a find-or-fail document slicer (Finding 3) that two sibling
prose-guards already carry.

All three findings are about *consistency and reuse*, not correctness: the
merged work is right, and `make all` is green. None is applied here — this is a
read-only audit step.

## Finding 1 — The envelope field order is hand-written in three places, none pinned to the dataclass the 6.3.7 guard treats as canonical

- **Category**: inconsistency
- **Severity**: medium
- **Location**:
  [`novel_ralph_skill/contract/envelope.py`](../../novel_ralph_skill/contract/envelope.py)
  (`render_machine`, the `ordered` dict literal at line 143) versus
  [`tests/test_contract_envelope.py`](../../tests/test_contract_envelope.py)
  (`_FIXED_FIELD_ORDER`, line 33) versus
  [`tests/cross_command_contract/__init__.py`](../../tests/cross_command_contract/__init__.py)
  (`ENVELOPE_KEY_ORDER`, line 81), all three against the canonical
  `dataclasses.fields(Envelope)` order that
  [`tests/test_skill_contract_drift_guard.py`](../../tests/test_skill_contract_drift_guard.py)
  `_envelope_field_order()` (line 209) now derives.

The `Envelope` dataclass declares the six contract fields in order — `command`,
`schema_version`, `ok`, `working_dir`, `result`, `messages` — and 6.3.7
elevates that declaration to the canonical source: its guard reads
`dataclasses.fields(Envelope)` and asserts the SKILL skeleton's key order
equals it, with the docstring framing the import as "the load-bearing coupling
that ties the SKILL restatement to the code". That is the right anchor.

Three other copies of the same six-name order remain literal and are *not*
derived from the dataclass:

- `render_machine` builds an `ordered` dict by spelling the six keys out
  in sequence (envelope.py line 143). Its own docstring says the order is
  "asserted by this function rather than implied" — i.e. the function is the
  contract's renderer of record, but it does not read the dataclass it renders.
- `_FIXED_FIELD_ORDER` (test_contract_envelope.py line 33) is a literal
  six-tuple used to assert `render_machine`'s output order.
- `ENVELOPE_KEY_ORDER` (`cross_command_contract/__init__.py` line 81) is a
  second literal six-tuple, reused by `assert_envelope_skeleton` across roughly
  seven cross-command sites.

The consequence is a four-way pin with only a partial spanning tree. A field
reordered or renamed in the dataclass is caught by the 6.3.7 SKILL guard, but
`render_machine`, `_FIXED_FIELD_ORDER`, and `ENVELOPE_KEY_ORDER` would each need
a matching hand-edit; conversely, `render_machine` could be reordered out of
step with the dataclass and *only* the two literal test tuples — themselves
hand-maintained twins of the old order — would catch it, never the dataclass.
The new guard makes the dataclass canonical for the SKILL copy alone; the
in-tree renderer and its two test oracles still treat their own literals as the
source. This is the precise "single un-pinned copy" pattern 6.3.7 set out to
eliminate, left standing one layer down in the code the guard imports.

- **Proposed fix**: Make `dataclasses.fields(Envelope)` the one source for every
  consumer of the field order. (1) Have `render_machine` build its ordered
  mapping by iterating `dataclasses.fields(Envelope)` and pulling each value via
  `getattr`, with `result`/`messages` coerced to `dict`/`list` as today, so the
  renderer cannot diverge from the declaration it renders. (2) Replace the two
  literal tuples with a single shared constant derived once from the dataclass
  — e.g. promote `ENVELOPE_FIELD_ORDER = tuple(f.name for f in
  dataclasses.fields(Envelope))` beside the `Envelope` definition in
  `envelope.py`, and have both `_FIXED_FIELD_ORDER` and `ENVELOPE_KEY_ORDER`
  import it rather than re-spell it. Keep one literal-tuple assertion (for
  instance in `test_contract_envelope.py`) as the human-readable tripwire that
  pins the *expected* names, so an accidental dataclass reorder still fails a
  test rather than silently propagating. Proposed as a roadmap item below; not
  applied here.

## Finding 2 — The 6.3.7 scanner is the second hand-rolled CommonMark fence regex; the two share a non-trivial core that could be a shared helper

- **Category**: similarity
- **Severity**: low
- **Location**:
  [`tests/_skill_contract_scanner.py`](../../tests/_skill_contract_scanner.py)
  (`_FENCE_TEMPLATE`, line 47, consumed by `extract_fenced_json`) versus
  [`tests/_state_layout_scanner.py`](../../tests/_state_layout_scanner.py)
  (`_FENCE_RE`, line 58).

Both scanners parse fenced code blocks with the same CommonMark-correctness
reasoning, and the two regexes share a non-trivial core: a `(?P<fence>`
``` `{3,}|~{3,} ``` `)` opening run that back-references via `(?P=fence)` so the
closing run matches character and length, up to three spaces of leading indent
(`{0,3}`), a non-greedy `(?P<body>.*?)`, and `re.DOTALL | re.MULTILINE`. Each
file carries a long comment block re-deriving why backtick *and* tilde fences,
four-or-more-backtick runs, and three-space indents must all be tolerated —
the same reasoning, written twice.

They differ at the edges, which is why this is a similarity finding rather than
a strict duplicate: `_state_layout_scanner._FENCE_RE` captures the `indent` and
the full `info` string (it iterates *every* fence to classify info strings as
executable or illustrative), whereas `_skill_contract_scanner._FENCE_TEMPLATE`
bakes a single `re.escape(fence_lang)` into the opening and takes the *first*
matching fence. The shared part is the CommonMark fence grammar; the divergent
part is what each caller does with the matches. With 6.3.7 the count of
hand-rolled fence parsers in `tests/` has gone from one to two, so the
correctness reasoning now has two homes that must stay in agreement (for
instance if a future CommonMark nuance — closing-fence trailing whitespace —
needs handling).

- **Proposed fix**: Extract the CommonMark fence grammar into one shared
  helper used by both scanners — for example an `iter_fences(text) ->
  Iterable[Fence]` generator (yielding `info`, `indent`, `body`) in a small
  `tests/_markdown_fence.py` sibling, with the single authoritative comment
  block on the grammar. `_state_layout_scanner` filters the yielded fences by
  info string; `extract_fenced_json` takes the first fence whose `info` starts
  with `fence_lang`. This removes the duplicated grammar and its twin comment
  while keeping each caller's distinct selection logic local. Low severity: two
  copies is the threshold where extraction starts paying off, not an urgent
  defect. Proposed as a roadmap item below; not applied here.

## Finding 3 — Three prose-guard modules each reimplement a find-or-fail document slicer

- **Category**: duplication
- **Severity**: low
- **Location**:
  [`tests/_skill_contract_scanner.py`](../../tests/_skill_contract_scanner.py)
  (`slice_doc_region`, line 53) versus
  [`tests/test_skill_deflation_guard.py`](../../tests/test_skill_deflation_guard.py)
  (`_slice_between`, line 63, and `_require_index`, line 51).

The repository's prose-guards all slice a document into a named region between
two heading anchors and fail loudly when an anchor is missing, so a renamed
heading raises rather than yielding an empty region that passes the downstream
assertions vacuously. That single idiom is now implemented three times:

- `slice_doc_region(text, start, end, *, source)` (6.3.7) — `str.find` for both
  anchors, `ValueError` naming `source` when either is absent.
- `_slice_between(text, start_marker, end_marker)`
  (test_skill_deflation_guard.py) — the same two-`find` slice, but it `assert`s
  with a message hard-coded to "in SKILL.md".
- `_require_index(haystack, needle, *, context)`
  (test_skill_deflation_guard.py) — the find-or-fail half alone, used for the
  ordinal comparisons.

The 6.3.7 docstring explicitly notes the divergence — `slice_doc_region` "names
`source` in its failure message, so a missing anchor in the design doc or
ADR-003 does not misreport 'not found in SKILL.md'" — which is a genuine
improvement over `_slice_between`'s hard-coded label. But the improvement was
made by writing a third copy rather than by generalising the existing one, so
the deflation guard still carries the inferior single-document variant, and a
fourth prose-guard will face the same choose-or-copy fork. The slicers are
small, so this is low severity; it is recorded because the count is now three
and 6.3.7 already demonstrated the strictly better signature.

- **Proposed fix**: Promote `slice_doc_region` (and a `require_index` companion
  for the ordinal case) into a shared `tests/_doc_slice.py` helper, then have
  `test_skill_deflation_guard.py` and `_skill_contract_scanner.py` import it,
  deleting `_slice_between` and `_require_index`. The deflation guard's callers
  pass `source="SKILL.md"`, preserving today's messages while gaining the
  source-naming for free. This collapses three near-identical find-or-fail
  slicers to one and gives the next prose-guard a single seam to reuse.
  Proposed as a roadmap item below; not applied here.

## Proposed roadmap items (for the root agent only)

- **Derive the envelope field order from the dataclass everywhere**
  (severity: medium). Make `dataclasses.fields(Envelope)` the single source for
  the field order across `render_machine`
  ([`novel_ralph_skill/contract/envelope.py`](../../novel_ralph_skill/contract/envelope.py)
  line 143), `_FIXED_FIELD_ORDER`
  ([`tests/test_contract_envelope.py`](../../tests/test_contract_envelope.py)
  line 33), and `ENVELOPE_KEY_ORDER`
  ([`tests/cross_command_contract/__init__.py`](../../tests/cross_command_contract/__init__.py)
  line 81): build the renderer's ordered mapping by iterating the dataclass
  fields, and promote one shared `ENVELOPE_FIELD_ORDER` constant that the two
  test tuples import. Rationale: 6.3.7 makes the dataclass canonical for the
  SKILL copy via `dataclasses.fields(Envelope)`, yet the renderer of record and
  its two test oracles still hand-spell the same order, leaving the
  "single un-pinned copy" problem 6.3.7 set out to remove standing in the code
  the guard imports.

- **Extract a shared CommonMark fence parser for the test prose-guards**
  (severity: low). Factor the fence grammar shared by
  `tests/_skill_contract_scanner.py` (`_FENCE_TEMPLATE`) and
  `tests/_state_layout_scanner.py` (`_FENCE_RE`) into one `iter_fences` helper
  with a single authoritative comment, leaving each caller's info-string
  selection local. Rationale: 6.3.7 makes this the second hand-rolled fence
  regex, so the CommonMark-correctness reasoning now lives in two places that
  must stay in agreement.

- **Consolidate the find-or-fail document slicers** (severity: low). Promote
  `slice_doc_region` (and a `require_index` companion) into a shared
  `tests/_doc_slice.py` and migrate `test_skill_deflation_guard.py`'s
  `_slice_between`/`_require_index` onto it. Rationale: 6.3.7 introduces a
  strictly better source-naming slicer as a third copy of the same idiom rather
  than generalising the existing one, so the deflation guard keeps the inferior
  single-document variant and the next prose-guard faces the same copy fork.
