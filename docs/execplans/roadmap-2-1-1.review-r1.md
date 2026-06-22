# Logisphere design review — roadmap 2.1.1 (round 1)

Adversarial pre-implementation review of
`docs/execplans/roadmap-2-1-1.md` ("typed `state.toml` schema and phase enum").
Verdict: **Revise** — one blocking design defect plus two precision defects must
be resolved before implementation. The plan's library/dependency claims, the
deterministic/judgemental boundary, and the cuprum/cyclopts scope decision are
all verified and sound.

## Verification trail

Source of truth read in full: design §5.1/§5.2/§5.3/§5.4/§8/§9,
`skill/novel-ralph/references/state-layout.md`, the §1.3.2 corpus
(`tests/working_corpus/_specs.py`, `_builder.py`, `_library.py`, `_variants.py`,
`_oracle.py`, `__init__.py`), `tests/corpus_fixtures.py`, `tests/conftest.py`,
`tests/test_working_corpus.py`, the house-style `contract/exit_codes.py`,
`docs/developers-guide.md` "Shared test scaffolding"/"working/ fixture corpus",
`AGENTS.md`, `Makefile` (`PYTHON_TARGETS`, gate targets), `pyproject.toml`,
`uv.lock`, and the read-only cuprum sibling
(`/data/leynos/Projects/cuprum/docs/users-guide.md`).

Verified-true claims (no defect):

- `requires-python = ">=3.14"` — `enum.StrEnum` and `slots=True` available.
- `msgspec` is an import-convention alias only (`pyproject.toml` line ~108/122),
  absent from `uv.lock` deps; using it would be a new dependency. Stdlib
  `dataclasses`/`enum`/`tomllib` is the correct, dependency-free choice.
- `tomllib` is already used by the test suite (`conftest.py:117`,
  `_oracle.py:89`, `test_working_corpus.py:19`).
- `PYTHON_TARGETS = novel_ralph_skill tests`, so the new `state/` package and
  test module are auto-covered by `make lint`/`typecheck`/interrogate;
  `interrogate fail-under = 100`.
- cuprum/cyclopts out of scope: design §9 line 710 ("v1 commands shell out to
  nothing"); cuprum users-guide confirms the catalogue is a shell-out allowlist.
  Decision is correctly cited against locked local sources — no memory claim.
- The phase enum eleven members/order match §5.1 and the corpus `PHASE_ORDER`
  exactly. The `uncleared-pending-turn` variant is indeed the only
  coherent-schema carrier of a populated `[pending_turn]`
  (`_variants.py:143`, built from the drafting baseline by `dc.replace`).
- `[chapters]` shape question is honestly flagged as a Work-item-1 pin; the
  builder writes an **array of inline tables** (`_builder.py:107`
  `tomlkit.array()`).

## BLOCKING

### B1 — The without-loss word-count assertion is not constructible under the corpus contract

WI3 (and Purpose, and Validation) require the parse test to iterate
`coherent_oracle_cases` and assert every field — explicitly including
`word_counts.current` and `word_counts.by_chapter` — equals "the value the
corpus's `WorkingTreeSpec` declared". It does **not**.

- `WorkingTreeSpec` does not carry `current` or `by_chapter`; both are *derived*
  by `derive_current` / `derive_by_chapter` (`_specs.py:228-253`).
- Those helpers are exported from the `working_corpus` package but are **not**
  among the fifteen fixtures the developers-guide pins as the entire sanctioned
  surface (`developers-guide.md:103-107`; `corpus_fixtures.py`). The guide is
  explicit: consume the corpus "by fixture name only … never by a runtime value
  import" (lines 31-32, 96-97).
- The existing corpus self-test proves the available pattern: it asserts exact
  `by_chapter`/`current` values only for specs it **authored itself**
  (`test_working_corpus.py:118-119`, `{"01": 4, "02": 6}` / `10`), and for
  `coherent_oracle_cases` it asserts only that the oracle returns empty
  (`:357-360`) — never the decoded word-count values, precisely because they are
  unavailable.

So as written, the plan's central test forces one of:
(a) a forbidden runtime import of `derive_*` (developers-guide violation);
(b) editing `corpus_fixtures.py` to expose them — explicitly barred by the
plan's own Tolerance ("if delivering the parse requires editing any
`tests/corpus_fixtures.py` … stop and escalate"); or
(c) silently dropping `current`/`by_chapter` from the without-loss assertion,
contradicting the stated §2.1.1 success criterion and the plan's own Purpose.

Required fix: restructure WI3's parse test so the without-loss check is
constructible. The viable shape is to **author the parse-test specs in the test
module** via the `make_working_tree_spec` / `make_chapter_spec` fixtures and
`build_tree` (the established pattern), so the test knows every expected value
by hand, and keep `coherent_oracle_cases` only for a coarser "parses to a
`State` without raising, phases resolve to `Phase`" pass over all eleven trees +
baseline. State this division explicitly and adjust the Purpose/Validation
success wording to match what is actually assertable. If the planner instead
wants exact-value coverage over the library trees, that requires a
corpus-fixture surface change, which is an escalation per the plan's own
Tolerances — call it out rather than burying it in WI3.

## ADVISORY (precision defects — fix before implementation, not blocking the verdict on their own)

### A1 — `paths` list-vs-tuple coercion is unstated

The `uncleared-pending-turn` variant writes `paths` as a list
(`_variants.py:148`); `tomllib` decodes a TOML array to `list`. The plan's
`PendingTurn.paths` is `tuple[str, ...]`. `parse_state` must coerce
list→tuple at the boundary, and the pending-turn test must assert against a
tuple. The plan says the boundary "constructs each field explicitly with the
expected type", which covers it, but the test assertion in WI3 ("`paths`") does
not name the coercion. State it so the implementer does not assert
`paths == ["…"]` and pass a list straight onto a `tuple` field.

### A2 — House-style member-doc form is mis-described

WI2 and Interfaces say each `Phase` member carries "a one-line docstring-style
comment" / "docstring or comment". The actual house style in
`contract/exit_codes.py` is a **string-literal docstring on the line after each
member** (e.g. `SUCCESS = 0` then `"""Success; …"""`), not a `#` comment, and
that is what satisfies interrogate's per-member coverage at `fail-under = 100`.
A `#` comment will not. Pin the member-doc form to the `ExitCode` literal-string
style to avoid an interrogate failure on first `make lint`.

### A3 — `last_finding_counts` is only ever exercised with zeros

The builder hard-codes `blocker/major/minor/taste = 0` for every tree
(`_builder.py:70-75`). The parse test therefore never proves the four counts are
parsed into the right fields (a transposition bug would pass). Consider one
self-authored assertion with distinct non-zero counts (mirrors A1's
"author-your-own-spec" remedy and the `state-layout.md` example `0/2/4/7`).

### A4 — Module-cap arithmetic for the schema is asserted, not shown

The plan says `schema.py` may split into `parse.py` "if the single file would
approach the cap" but gives no estimate. With ~8 sub-dataclasses, the boundary
parser, numpy docstrings on every attribute (envelope house style) and 100%
interrogate, 400 lines is plausibly tight. Not blocking — the split is
permitted — but WI3 should commit to the split up front rather than discover the
cap mid-implementation, given the Tolerance escalates at >6 files / ~450 net
lines.

## Pre-mortem (Doggylump)

It is the 2.1.2 build. The validator imports `parse_state`, and a chapter-manifest
field silently parsed into the wrong attribute (e.g. `target_words` ↔ `number`)
never surfaced, because 2.1.1's without-loss test was quietly narrowed to drop
the fields it could not source values for (B1) and the manifest entries it did
check happened to use values where the bug was invisible. Mitigation: B1's fix —
make the without-loss assertion exact and constructible — is exactly the signal
that would have caught it. A3 is the same class of latent transposition.

## Alternatives checkpoint (Wafflecat)

The strongest alternative to the test strategy is **golden-mapping assertion**:
decode each corpus `state.toml` with `tomllib` independently in the test, then
assert `parse_state(decoded) == State(**hand_built)` field-by-field — but the
"hand_built" expected still needs the derived word counts, so it collapses into
B1. The genuinely different alternative is **round-trip-by-decode**: assert that
`dataclasses.asdict(parse_state(decoded))` re-serialises to the same mapping
`tomllib` produced (modulo tuple/list and `Phase`/str), proving without-loss
without ever naming a corpus-internal expected value. That trades exact-value
readability for a self-contained oracle that needs no unexposed helper — and it
makes the §2.1.1 "without loss" criterion literally true by construction. Worth
the planner's consideration as the B1 remedy.

— Logisphere crew (Pandalump, Wafflecat, Buzzy Bee, Telefono, Doggylump,
Dinolump). Round 1.
