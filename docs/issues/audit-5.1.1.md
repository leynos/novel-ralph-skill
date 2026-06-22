# Post-merge audit — roadmap task 5.1.1

Audit of the codebase after roadmap task 5.1.1 ("Implement the versioned
rule-pack loader and schema") merged to `main` at commit `ad8e09a`. The slice
delivers the `novel_ralph_skill.rulepack` package: the frozen, slotted shapes
([`schema.py`](../../novel_ralph_skill/rulepack/schema.py): `RuleBasis`,
`Rule`, `RulePack`, `RULEPACK_SCHEMA_VERSION`), the two typed failure channels
([`errors.py`](../../novel_ralph_skill/rulepack/errors.py): `RulePackError`,
`RulePackFileError`), and the validating boundary
([`parse.py`](../../novel_ralph_skill/rulepack/parse.py): `parse_rulepack`,
`load_rulepack`). It is re-exported from
[`__init__.py`](../../novel_ralph_skill/rulepack/__init__.py), documented in the
developers' guide, and guarded by
[`tests/test_rulepack_schema.py`](../../tests/test_rulepack_schema.py),
[`tests/test_rulepack_loader.py`](../../tests/test_rulepack_loader.py), and the
Hypothesis properties in
[`tests/test_rulepack_properties.py`](../../tests/test_rulepack_properties.py),
with twenty-one TOML fixtures under
[`tests/data/rulepacks/`](../../tests/data/rulepacks/).

The slice is sound and discharges its success criterion: a pack whose rule
carries an uncompilable `pattern` fails loudly through `RulePackError`, naming
the offending rule, rather than silently skipping it. The validating-versus-
structural distinction from `state/parse.py` is implemented and documented
exactly as the ExecPlan and design §6.1 require, the deterministic/judgemental
boundary (ADR-001) holds (the loader compiles and validates but never judges
prose), and the two exit-code channels (exit 2 for content, exit 3 for file)
are kept cleanly separate. The findings below are tidy-up, consistency, and
coverage opportunities; none is a blocking defect.

This audit checks the new package against the design's authoritative artefacts
and the recurring themes carried by the prior audits
(`docs/issues/audit-1.2.1.md` through `docs/issues/audit-2.2.1.md`). Each
finding records a category, a location, a description, a concrete proposed fix,
and a severity.

Trail followed: explored with `leta`/`Read` over the `rulepack` package,
`state/parse.py`, `contract/runner.py`, `_freeze.py`, and the rulepack tests;
traced history with `sem diff --commit ad8e09a` and `git log origin/main`.
Source of truth consulted: `docs/novel-ralph-harness-design.md` §3.1, §4.4,
§6.1, and §10;
[`docs/adr-001-deterministic-judgemental-boundary.md`](../adr-001-deterministic-judgemental-boundary.md);
[`docs/adr-002-toml-round-trip-tomlkit.md`](../adr-002-toml-round-trip-tomlkit.md);
`docs/scripting-standards.md`; `docs/developers-guide.md`; `docs/users-guide.md`;
and `AGENTS.md`. Language router: `python-router` (Python boundary constructors,
data shapes, errors and logging). Spelling per `en-gb-oxendict`.

## Finding 1 — Three exception classes hand-repeat the same `messages`-carrying `__init__`

- **Category:** duplication
- **Severity:** medium
- **Location:**
  [`novel_ralph_skill/rulepack/errors.py:38-52`](../../novel_ralph_skill/rulepack/errors.py)
  (`RulePackError.__init__`) and
  [`novel_ralph_skill/rulepack/errors.py:65-74`](../../novel_ralph_skill/rulepack/errors.py)
  (`RulePackFileError.__init__`), against
  [`novel_ralph_skill/contract/runner.py:52-61`](../../novel_ralph_skill/contract/runner.py)
  (`StateInputError.__init__`)

The 5.1.1 slice introduces two more exceptions that store human-prose
`*messages` on the instance as a `tuple[str, ...]` for the envelope a command
will later build, repeating verbatim the pattern `StateInputError` established
(`super().__init__(*messages)` then `self.messages: tuple[str, ...] = messages`).
There are now three copies of the same six-line constructor and its
parameter-list docstring across two modules. The shared intent — "a domain
exception that carries envelope `messages`" — is implicit and re-keyed by hand,
so a future change to that contract (for example, freezing `messages` through
`_freeze.freeze_sequence`, as `CommandOutcome` already does for its own
`messages`, or recording a structured `detail` alongside the prose) must be
mirrored across all three sites or they drift apart. `RulePackError`
additionally carries `rule_id`, so it is not identical, but the
`messages`-carrying half is.

**Proposed fix:** extract a small shared base, for example an
`EnvelopeMessagesError(Exception)` in a neutral module (a new
`novel_ralph_skill/contract/errors.py`, or alongside `StateInputError`), whose
`__init__` records `self.messages: tuple[str, ...]`. `RulePackFileError` and
`StateInputError` then subclass it directly; `RulePackError` subclasses it and
adds `rule_id` via `super().__init__(*messages)`. This gives the
"carries envelope messages" contract one definition and one docstring, and lets
the eventual freeze-on-construct decision land in one place. Note the cross-layer
direction: `rulepack` may depend on a `contract` base, but not vice versa. Gated
by Ruff, `pyright`, `interrogate`, and `pytest`.

## Finding 2 — The on-disk rule-pack TOML format is undocumented for pack authors

- **Category:** docs-gap
- **Severity:** medium
- **Location:**
  [`docs/developers-guide.md:336-371`](../developers-guide.md) ("Rule packs and
  the loader boundary") and
  [`docs/users-guide.md:85`](../users-guide.md) (the lone `desloppify` line)

The developers' guide explains the *loader architecture* well — the
validating-boundary split, the two error channels, the ADR-001 stance — but it
never shows a pack author what a rule pack *looks like on disk*: the top-level
`schema_version`/`pack` keys, the `[[rule]]` array-of-tables, and a worked
`manuscript` and `per_page` example with `page_words`. That on-disk shape exists
only as the `valid.toml` test fixture
([`tests/data/rulepacks/valid.toml`](../../tests/data/rulepacks/valid.toml)),
which is not discoverable from the prose. The users' guide mentions `desloppify`
in one line and says nothing about packs at all. The roadmap's stated outcome is
that an author can write a pack and have a bad pattern flagged by rule id, but a
prospective author has no documented format to write against. No example pack
ships outside `tests/` either, so there is no canonical artefact to copy.

**Proposed fix:** add a short fenced TOML example to the developers' guide
"Rule packs" section showing both bases (a `manuscript` rule with
`threshold = 0`, a `per_page` rule with `page_words`), and enumerate the v1 key
vocabulary (`schema_version`, `pack`, and per-rule `id`/`pattern`/`threshold`/
`basis`/`page_words`) with the strict rules the loader enforces (`page_words`
required iff `per_page`; ids unique; unknown keys rejected). When task 5.1.2
lands `desloppify`, extend the users' guide accordingly. Consider whether a
canonical `ai-isms` pack should ship as a real package artefact rather than
living only as a test fixture — flag for the roadmap rather than deciding here.
Gated by `make markdownlint` and `make nixie`.

## Finding 3 — `parse_rulepack`'s `Raises` block does not document the `RulePackFileError` boundary contract

- **Category:** docs-gap
- **Severity:** low
- **Location:**
  [`novel_ralph_skill/rulepack/parse.py:436-477`](../../novel_ralph_skill/rulepack/parse.py)
  (`parse_rulepack`) and
  [`novel_ralph_skill/rulepack/parse.py:480-515`](../../novel_ralph_skill/rulepack/parse.py)
  (`load_rulepack`)

`load_rulepack`'s docstring states clearly that it raises `RulePackFileError`
for a file or decode fault and lets `RulePackError` propagate from
`parse_rulepack`. But `parse_rulepack`'s own `Raises` block lists only
`RulePackError`; nothing in the pure boundary's contract states that it *never*
raises `RulePackFileError` (file faults are `load_rulepack`'s sole concern) and
that any other surfacing exception would be a bug. For a function described as
the reusable boundary every pack consumer composes (the design wants 5.1.2 and
later detection logic to call it directly), the "this is the only exception type
you must catch" guarantee is the load-bearing part of the contract and is left
implicit. The parallel `parse_state` documents its `KeyError`/`ValueError`
surface explicitly, so this boundary is slightly less self-describing than its
sibling.

**Proposed fix:** add one sentence to `parse_rulepack`'s `Raises`/`Notes`
making the total exception surface explicit — `RulePackError` is the only
exception it raises; file and decode faults belong to `load_rulepack`
(`RulePackFileError`) and never reach the pure boundary. This pins the contract
5.1.2 will catch against. Gated by `interrogate` and Ruff.

## Finding 4 — Per-rule error-message construction repeats the `f"rule {rule_id!r} ..."` prefix inline

- **Category:** duplication
- **Severity:** low
- **Location:**
  [`novel_ralph_skill/rulepack/parse.py`](../../novel_ralph_skill/rulepack/parse.py):
  the `_where(rule_id)` helper (lines 64-81) is used by the generic helpers, but
  the rule-specific helpers re-inline the prefix at lines 281, 309, 346, 351,
  393, and 431

The module factors a `_where(rule_id)` helper that returns `"rule '<id>'"` or
`"rule pack"`, and the generic field helpers (`_require`, `_require_str`,
`_require_int`, `_reject_unknown_keys`) use it consistently. But the
rule-specific helpers — `_compile_pattern`, `_resolve_basis`,
`_resolve_page_words`, `_rule` (threshold check), and `_reject_duplicate_ids` —
hand-write `f"rule {rule_id!r} ..."` inline instead of calling `_where(rule_id)`.
Because these helpers always have a concrete `rule_id` (never the pack level),
the two spellings happen to agree today, but the rule-naming prefix format
now lives in two places. A change to how a rule is named in diagnostics (for
example, to add the array index alongside the id) would have to be made in both
the
`_where` helper and the six inline sites, and a missed site would emit an
inconsistent message — exactly the kind of message-format drift the envelope's
human channel is sensitive to.

**Proposed fix:** route every per-rule message through `_where(rule_id)`, for
example `f"{_where(rule_id)} has an invalid pattern {pattern!r}: {exc}"`, so the
"how a rule is named" decision has one home. This is purely internal; the public
behaviour (`error.rule_id` and the substring assertions in
`test_rulepack_loader.py`) is unchanged because `_where` already renders the id
the existing tests look for. Gated by Ruff and `pytest`.

## Finding 5 — `_entries` narrows on `list`/`dict` while the rest of the module reasons over `Mapping`/`Sequence`

- **Category:** inconsistency
- **Severity:** low
- **Location:**
  [`novel_ralph_skill/rulepack/parse.py:221-251`](../../novel_ralph_skill/rulepack/parse.py)
  (`_entries`), and the `_Mapping` alias at line 48

The module's type vocabulary is abstract — `_Mapping` is
`cabc.Mapping[str, object]`, and `_require`/`parse_rulepack` accept any
`cabc.Mapping`. But `_entries` guards the rule array with the *concrete*
`isinstance(value, list)` and each entry with `isinstance(entry, dict)`, then
casts back to the abstract `cabc.Sequence[_Mapping]`. For the `tomllib` read
path this is exact (arrays decode to `list`, tables to `dict`), but
`parse_rulepack` is documented as the pure boundary any consumer may reuse with
its own decoded mapping — and a consumer passing a `tuple` of rule tables, or
entries that are `Mapping` but not `dict` (a frozen mapping, a `MappingProxy`),
would be rejected by `_entries` even though every downstream helper accepts
`cabc.Mapping`. The narrowing is stricter than the boundary's advertised input
type, an inconsistency between the abstract signature and the concrete guard.

**Proposed fix:** either (a) tighten the documented contract — state that
`parse_rulepack` expects a `tomllib`-shaped mapping whose arrays are `list` and
tables are `dict` — so the concrete guard matches the advertised input; or
(b) loosen the guards to the abstract shapes (`isinstance(value,
cabc.Sequence)` and not `str`/`bytes`; `isinstance(entry, cabc.Mapping)`) so the
purity claim holds for any decoded mapping. Option (a) is the smaller change and
matches how `parse_state` is used in practice; pick one and make the signature
and guard agree. Gated by `pyright`, Ruff, and `pytest`.

## Finding 6 — No test pins `parse_rulepack`'s purity against a non-`dict` mapping input

- **Category:** test-gap
- **Severity:** low
- **Location:**
  [`tests/test_rulepack_loader.py:175-188`](../../tests/test_rulepack_loader.py)
  (`_valid_mapping`) and the `parse_rulepack` direct tests (lines 191-293)

Every direct `parse_rulepack` test builds its input with `_valid_mapping`, a
plain `dict[str, object]` whose `rule` value is a `list[dict]`. So the suite
proves the boundary works for exactly the shape `load_rulepack` feeds it, but it
does not pin the purity claim the docstring makes — that `parse_rulepack` is
reusable "without a filesystem" by any pack consumer. Combined with Finding 5,
this means the abstract-`Mapping` contract is asserted by neither the type guard
nor a test: whether a consumer may legitimately pass a non-`dict` mapping is
currently undefined behaviour, untested in either direction. The Hypothesis
properties also build only `dict`/`list` packs, so they do not close this gap.

**Proposed fix:** once Finding 5 fixes the contract one way or the other, add a
matching test. If the boundary is to accept any `cabc.Mapping` (option (b)),
add a parse test that passes a `types.MappingProxyType` pack and asserts it
loads. If the contract is tightened to `tomllib` shapes (option (a)), add a test
asserting a documented, recognisable error when a non-`list` `rule` value (for
example a `tuple`) is passed, so the precondition is enforced rather than
implied. Gated by `pytest`.

## Finding 7 — The `RuleBasis`-membership message recomputes `str(member)` although members are already strings

- **Category:** ergonomics
- **Severity:** low
- **Location:**
  [`novel_ralph_skill/rulepack/parse.py:305-310`](../../novel_ralph_skill/rulepack/parse.py)
  (`_resolve_basis`)

`_resolve_basis` builds its "allowed" list with
`", ".join(repr(str(member)) for member in RuleBasis)`. Because `RuleBasis` is a
`enum.StrEnum`, each `member` *is* its string value, so the `str(member)` call is
redundant defensive scaffolding — `repr(member)` would render identically, and
`RuleBasis.MANUSCRIPT` already equals `"manuscript"`. The same idiom recurs in
`_resolve_page_words` (line 352, `str(basis)!r`). The extra `str(...)` reads as
though the author was unsure the enum members were strings, which slightly
obscures the `StrEnum` design the schema docstring is at pains to explain. It is
harmless but adds noise to two diagnostic builders.

**Proposed fix:** drop the redundant `str(...)` wrappers — use
`repr(member)` and `basis!r` directly — or, if an explicit conversion is
preferred for clarity, add a one-line comment noting `StrEnum` members render as
their value so a future reader does not reintroduce the wrapper "to be safe".
Purely cosmetic; behaviour and the existing `unknown-basis` assertions are
unchanged. Gated by Ruff and `pytest`.
