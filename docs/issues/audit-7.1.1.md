# Post-merge audit — roadmap task 7.1.1

Audit of the codebase after task 7.1.1 ("Ship the versioned `ai-isms.toml` pack
and update cadence") merged to `main` at commit `42a6fc6`. The task shipped a
second packaged rule pack (`ai-isms.toml`) beside `offenders.toml`, added the
`ai_isms_pack_path` resolver, a validation suite, robustness property tests, and
an end-to-end check proving the pack travels in the wheel, plus update-cadence
documentation and the Q5 resolution in the harness design.

Trail followed: `docs/novel-ralph-harness-design.md` §6.2 (resolves Q5),
`docs/developers-guide.md` §"Rule packs and the loader boundary" (new "ai-isms
pack: cadence, ownership, and membership" subsection), `docs/users-guide.md`
§`desloppify`, `skill/novel-ralph/references/desloppify-checklist.md`, the ADRs
(ADR-001 deterministic boundary, ADR-006 POSIX e2e policy), `AGENTS.md` (quality
gates, 400-line cap, CQS), the `python-router` skill (Python work), and
`leta`/`sem` for navigation and history. Files inspected:
`novel_ralph_skill/rulepack/packs/ai-isms.toml`,
`novel_ralph_skill/rulepack/packs/__init__.py`,
`novel_ralph_skill/commands/_desloppify_report.py`,
`novel_ralph_skill/commands/_desloppify.py`,
`novel_ralph_skill/rulepack/parse.py`, `tests/test_ai_isms_pack.py`,
`tests/test_ai_isms_e2e.py`, `tests/test_ai_isms_properties.py`,
`tests/test_desloppify_command.py`, and the three documents above.

The merged change is high quality: the pack-validation and property suites are
thorough, the membership policy is well reasoned and cited, and the casing
divergence and cross-pack ownership are pinned precisely. The findings below are
mostly at the CLI-ergonomics and documentation layer, where the in-wheel pack is
not actually reachable through the path users are told to type. Finding 1 is the
substantive one.

## Finding 1 — the documented `--pack` invocation does not work after install (severity: high)

**Category:** ergonomics

**Location:** `docs/users-guide.md` §`desloppify` (the `--pack
novel_ralph_skill/rulepack/packs/ai-isms.toml` instruction);
`docs/developers-guide.md` §"The ai-isms pack…" ("selects it only when given
`--pack ai-isms.toml`"); `skill/novel-ralph/references/desloppify-checklist.md`
(the same source-tree path); `novel_ralph_skill/commands/_desloppify.py`
(`pack: pathlib.Path | None`); `novel_ralph_skill/commands/_desloppify_report.py`
`ai_isms_pack_path`.

**Description:** The shipped `ai-isms.toml` lives inside the installed package
tree and is resolved through `importlib.resources` as a `Traversable` (the
resolver and `load_rulepack` are both correctly typed `Traversable`, precisely so
a zipped install works). But the only way the CLI lets a user reach it is the
`--pack PATH` keyword, which is bound to `pathlib.Path`, and the documentation
tells users to type the **source-tree relative path**
`novel_ralph_skill/rulepack/packs/ai-isms.toml`. That path exists only when
running from a checkout; after `pip install` the file is under `site-packages`
(and, in a zipped install, is not a filesystem path at all). An installed user
following the users-guide, developers-guide, or desloppify-checklist gets a
`cannot read rule pack` exit-3 error. `ai_isms_pack_path()` — the one resolver
that *does* find the installed pack — is never wired into the command surface;
the e2e only works because it shells out to `python -c "...; print(
ai_isms_pack_path())"` to discover the path first, which no end user would do.

**Proposed fix:** Wire the packaged pack into the command surface so it is
selectable without knowing an install path. Preferred: accept a symbolic pack
name on `--pack` (e.g. `--pack ai-isms` / `--pack offenders`) that the command
resolves through `ai_isms_pack_path()`/`offenders_pack_path()`, treating any
value that is not a known shipped name as a filesystem path (this keeps `--pack
PATH` for bespoke packs). Then correct all three documents to the symbolic form
and add a command-level test that selects the pack by the *documented* string
(not by `str(ai_isms_pack_path())`), so the docs claim is pinned. If a symbolic
selector is judged out of scope for a docs-only fix, the minimum remediation is
to correct the three documents to show the real discovery mechanism rather than
a path that fails after install.

## Finding 2 — the documented invocation string is never tested (severity: medium)

**Category:** test-gap

**Location:** `tests/test_desloppify_command.py`
(`test_ai_isms_pack_flags_load_bearing`,
`test_ai_isms_pack_clean_tree_exits_zero`); `tests/test_ai_isms_e2e.py`
(`test_installed_desloppify_ai_isms`).

**Description:** Every test that exercises pack selection passes the pack as
`str(ai_isms_pack_path())` — the resolver's output — never the string the docs
tell a user to type (`--pack novel_ralph_skill/rulepack/packs/ai-isms.toml`).
The tests therefore prove the *resolver* works but not that any *documented*
invocation works, which is exactly how the Finding 1 gap slipped through green.

**Proposed fix:** Once Finding 1 settles the supported selection string, add a
test that drives `desloppify` with that exact documented argument and asserts the
AI-ism is flagged. Until then, the e2e's reliance on a `python -c` discovery step
to find the pack is itself the signal that the user-facing path is missing — fold
that observation into the e2e docstring so the gap is visible to the next reader.

## Finding 3 — `offenders_pack_path` and `ai_isms_pack_path` are near-identical (severity: low)

**Category:** duplication

**Location:** `novel_ralph_skill/commands/_desloppify_report.py`
`offenders_pack_path` (lines 36-59) and `ai_isms_pack_path` (lines 62-86).

**Description:** The two resolvers differ only in the literal filename and the
docstring; both call
`importlib.resources.files("novel_ralph_skill.rulepack.packs").joinpath(<name>)`.
A third packaged pack (the `device-ledger.toml` of roadmap 7.1.2) will add a
third copy of the same body, and the shared package-anchor string is repeated in
each.

**Proposed fix:** Extract one private helper,
`_packaged_pack(name: str) -> Traversable`, that holds the `importlib.resources`
anchor once, and let `offenders_pack_path()`/`ai_isms_pack_path()` delegate to it
(each keeping its own docstring as the documented public entry point). This also
gives 7.1.2's device-ledger resolver a one-line definition. Coordinate with
roadmap 7.1.5, which already consolidates the finding-payload projection in the
same module.

## Finding 4 — `vital-role` misses the gerund "playing a vital role" (severity: low)

**Category:** test-gap

**Location:** `novel_ralph_skill/rulepack/packs/ai-isms.toml`
(`vital-role`, pattern
`(?i)\b(?:plays?|played) a (?:vital|pivotal|crucial|key) role\b`);
`tests/test_ai_isms_pack.py` `_PATTERN_CASES["vital-role"]`.

**Description:** The verb alternation is `plays?|played`, so the pattern matches
"plays/play/played a vital role" but not the gerund "playing a vital role", which
is at least as common an AI-ism collocation as the finite forms. The crafted
positive ("she plays a vital role…") only exercises the covered branch, so the
gap is invisible to the suite. This is a membership-completeness observation, not
a defect: the pack is deliberately conservative, and adding `playing` is the
exact "data edit" the cadence policy describes. (The negative-case discipline is
otherwise strong; nothing here fires on baseline fiction.)

**Proposed fix:** As a maintainer data edit, extend the verb alternation to
`(?:plays?|played|playing)` and add a positive test row for "playing a vital
role" in `_PATTERN_CASES`. Record a `# source:` note that the gerund branch is a
maintainer addition, consistent with the membership policy in the developers'
guide.

## Finding 5 — "the inline `(?i)` … with no flags" is asserted weakly (severity: low)

**Category:** test-gap

**Location:** `tests/test_ai_isms_pack.py`
`test_ai_isms_patterns_compile_without_flags` (lines 238-249).

**Description:** The test recompiles each pattern with `re.compile(rule.pattern)`
and asserts `compiled.flags & re.IGNORECASE`, which proves the pattern *is*
case-insensitive but not that the case-insensitivity comes from the **inline**
`(?i)` rather than a smuggled compile flag — the loader compiles with no flags,
so the distinction is the whole point of the casing-divergence note. A pattern
that lost its inline `(?i)` would still pass if `re.IGNORECASE` were applied some
other way, and the assertion message ("must carry inline (?i)") overstates what
is checked.

**Proposed fix:** Tighten the assertion to inspect the pattern source directly —
assert each `rule.pattern` begins with (or contains) the literal `(?i)` token —
so the inline-flag invariant the docstring claims is the one actually pinned.
Keep the `compiled.flags & re.IGNORECASE` check as a secondary guard.

## Finding 6 — pack selection is mutually exclusive but not documented as a limit (severity: low)

**Category:** docs-gap

**Location:** `docs/developers-guide.md` §"The ai-isms pack…" ("Combining both
packs in one invocation is a separate roadmap item and is not yet supported");
`docs/users-guide.md` §`desloppify`; `docs/roadmap.md` §7.1.

**Description:** The developers' guide states pack-combining is "a separate
roadmap item", but no roadmap item under §7.1 actually tracks it (7.1.2 is the
device ledger; 7.1.3–7.1.5 are payload-contract work). A reader who wants to scan
against both the offenders and ai-isms packs in one run has no item to follow,
and the users-guide does not mention the one-pack-per-run limit at all, so a user
may reasonably expect `--pack` to be additive.

**Proposed fix:** Either add an explicit roadmap item under §7.1 for multi-pack
selection (so the developers' guide cross-reference resolves), or soften the
guide to "not currently supported" without the phantom item reference. Add one
sentence to the users-guide noting that `--pack` selects exactly one pack per
run. (See proposed roadmap item below.)

## Finding 7 — `make markdownlint` fails on `developers-guide.md` after this merge (severity: medium)

**Category:** inconsistency

**Location:** `docs/developers-guide.md:700` (MD012/no-multiple-blanks, the two
consecutive blank lines introduced ahead of the new "#### The ai-isms pack…"
subsection by commit `42a6fc6`).

**Description:** The 7.1.1 merge left two consecutive blank lines before the new
ai-isms subsection, so `make markdownlint` — an AGENTS.md commit gate — now fails
on a clean `origin/main` checkout (verified by stashing this audit file and
re-running the lint). A failing gate on the integration branch means the next
task starts from a red baseline and either inherits or masks the breakage.

**Proposed fix:** Delete the duplicate blank line at `docs/developers-guide.md`
line 700 so a single blank separates the preceding paragraph from the new
heading. This is a one-line fix outwith this docs-only audit's scope, so it is
recorded here rather than applied; fold it into the next task that touches the
document, or take it as a trivial standalone fix.
