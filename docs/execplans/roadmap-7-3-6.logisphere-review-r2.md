# Logisphere design review — roadmap 7.3.6, round 2

Reviewer: adversarial Logisphere crew (Pandalump, Wafflecat, Buzzy Bee, Telefono,
Doggylump, Dinolump) plus pre-mortem and alternatives checkpoint.
Subject: `docs/execplans/roadmap-7-3-6.md` (DRAFT, round 2).
Verdict: **PROCEED** — both round-1 BLOCKING findings are genuinely resolved, the
named advisories are folded in, and no new blocking defect surfaces. The plan is
implementable and design-conformant as written.

## What was re-verified against real source (round 2)

- **Gate composition (round-1 BLOCKING 1).** `Makefile:37` is
  `all: build check-fmt lint typecheck test` — `audit` is **not** in `all`
  (`audit:` is a separate target at `Makefile:114`, running `pip-audit`).
  AGENTS.md lines 80 and 92 list auditing (`make audit`) as a distinct gate.
  The round-2 plan's Decision D3, the "Gate composition" block (Concrete steps),
  and every WI's Validation now run `make all` **then** an explicit `make audit`.
  Correctly resolved.
- **Red/green recipe (round-1 BLOCKING 2).** Traced the D4 / WI3 recipe against
  `git show HEAD:novel_ralph_skill/contract/envelope.py` line 19 —
  `from novel_ralph_skill.commands.names import ENVELOPE_COMMAND_NAMES`. The new
  recipe stages both the widened guard and the repoint, then
  `git restore --staged --worktree novel_ralph_skill/contract/envelope.py`
  reverts *only* `envelope.py` to HEAD (which imports `commands.names`), leaving
  the widened guard on disk. Because the existing guard reads module source
  statically off disk (`_read_seam_source` →
  `find_spec(...).origin` → `Path(...).read_text()`,
  `tests/test_contract_layering.py:193-203`), the widened guard reads the
  reverted on-disk `envelope.py` and genuinely **fails**; re-applying the repoint
  makes it **pass**. The blanket-`git stash` hazard from round 1 is gone.
  Correctly resolved.
- **Widening the guard is safe.** `grep -rn` for any `commands` import under
  `novel_ralph_skill/contract/` finds exactly one real import —
  `envelope.py:19`. The other hit, `finding_outcome.py:4`, is a docstring
  `:func:` cross-reference to `commands._desloppify_report.report_outcome`, not
  an import; the `_module_scope_imports` ast walk inspects `import`/`from`/
  dynamic-import nodes only and never parses docstrings, so it does not trip on
  it. Once `envelope.py:19` is repointed, a package-wide walk passes. The
  existing `runner.py` assertion is preservable as a special case.
- **Consumer enumeration matches `grep`.** `ENVELOPE_COMMAND_NAMES`: one
  production importer (`envelope.py:19`) plus `tests/test_contract_envelope.py`,
  `tests/cross_command_contract/_identity_assertions.py`,
  `tests/cross_command_contract/test_error_channels.py`. `WORKING_DIR_NAME`:
  def at `state_sourcing.py:56`, consumed by `_desloppify.py`, `_wordcount.py`,
  `tests/multiplexer_support.py`, `tests/test_state_sourcing_home.py`. The
  re-export (Decision D2) keeps every one resolving; none needs editing.
- **`commands/names.py` has no `__all__` today** (confirmed); WI1 step 2's "add
  an `__all__` if absent" is correct, not redundant.
- **`state_sourcing.py:14-15`** does carry the "imports only from … `state` and
  … `contract.runner` — never from `novel_state`" claim WI2 must correct; D5 and
  WI2 step 3 rewrite it (not merely annotate). Confirmed against source.
- **`developers-guide.md` ~603-614** calls `names.py` a "leaf source-of-truth
  module" and the edge "deliberate, not a layering leak"; WI4 step 1 rewrites it
  honestly (no longer a dependency-free leaf; transitive contract import, not a
  cycle). Confirmed against source.
- **No external-library claim is load-bearing** (Decision D0). Confirmed for the
  second time: this is a pure intra-package module-home relocation. No cuprum,
  Cyclopts, `uv`, or pytest-timeout behaviour is asserted, so no firecrawl
  citation or pinning test is owed. cuprum (`/data/leynos/Projects/cuprum`) is
  untouched.

## Findings

### BLOCKING

None. Both round-1 BLOCKING findings are resolved and re-verified against source.

### ADVISORY (address if cheap; not blocking)

1. **Name the `finding_outcome.py` docstring hit in WI3 so the implementer is not
   spooked.** When the implementer greps `commands` inside `contract/` to confirm
   the widened guard is green, they will see `finding_outcome.py:4`'s `:func:`
   docstring reference to `commands._desloppify_report`. It is harmless (the ast
   walk ignores docstrings), but the plan does not mention it. One sentence in
   WI3 ("the only real `contract → commands` import is `envelope.py:19`;
   `finding_outcome.py:4` is a docstring cross-reference the structural walk does
   not see") would pre-empt a false alarm. (Pandalump / Telefono.)

2. **`tests/test_contract_envelope.py` still imports `ENVELOPE_COMMAND_NAMES` and
   `SUBCOMMAND_NAMES` from `commands.names`** (lines 19-22). WI3 already says to
   repoint it at `contract.names` "since this is the contract suite". Good — but
   note `SUBCOMMAND_NAMES` too lives only in `contract.names` after WI1 (it is
   re-exported), so repoint both names together, not just `ENVELOPE_COMMAND_NAMES`.
   Either path stays green via the re-export; flagged only so the repoint is
   complete. (Telefono.)

3. **Keep the identity assertions.** Round-1 advisory 4 still stands: the
   `commands.names.SUBCOMMAND_NAMES is contract_names.SUBCOMMAND_NAMES` and the
   analogous `WORKING_DIR_NAME` identity checks are the actual neutrality proof
   against a silent second copy. The plan retains them (WI1, WI2 tests). Do not
   drop them under time pressure. (Telefono.)

## Pre-mortem (Doggylump)

- *Scenario A — the widened guard is a no-op.* The package-wide walk is written
  with `pkgutil.iter_modules` but the per-module source read silently skips a
  module (e.g. a `find_spec` returning `origin is None`, or a typo in the package
  name), so the guard iterates zero modules and passes vacuously. Prevention: the
  round-2 file-scoped red/green proof (D4) **is** the guard against this — it
  forces a real FAIL against the un-repointed `envelope.py`, which a vacuous walk
  could not produce. The proof is now correct, so the scenario is mitigated. Keep
  an explicit assertion in the test that the iterated module set is non-empty
  (cheap belt-and-braces; advisory, not blocking).
- *Scenario B — the audit gate slips.* Resolved by BLOCKING-1's fix: every WI now
  runs `make audit`.
- *Scenario C — import-time cost creeps.* `commands.names` now transitively pulls
  the whole `contract` package (and cyclopts) via the re-export. Not a cycle
  (nothing under `contract/` imports `commands`), and the `novel`-import laziness
  guard is unaffected (`novel` already pulls the contract package). WI4's honest
  doc rewrite is the hedge; the plan does this. Low severity.

## Alternatives checkpoint (Wafflecat)

Unchanged from round 1 and still correct. The strongest alternative — move the
*entire* `names.py` into `contract` and re-export from `commands` — is rejected
by Decision D1 because it would park a `commands`-layer entry-point path string
and the `[project.scripts]` derivation inside the contract package, recreating
the inversion in the opposite sense. The vocabulary/binding split is the right
cut.
The "document but don't repair" status quo is foreclosed by the roadmap success
criterion that the edge be *removed*. No superior alternative exists.

## Conformance check

- ADR-003 layering rule (contract below commands): the plan *enforces* it and
  hardens the static guard to the whole contract package. Aligns.
- Deterministic/judgemental boundary: untouched — no CLI, envelope wire-format,
  or exit-code change. The `command`/`working_dir` envelope fields are
  byte-for-byte preserved (identity + e2e/snapshot suites). Aligns.
- Behaviour-neutrality: backed by identity tests and the unchanged
  console-scripts e2e and envelope-snapshot suites. Sound.
- en-GB Oxford spelling: demanded in docstrings/commits; the plan text itself is
  compliant.
- Work items: atomic, ordered (WI1 → WI2 → WI3 → WI4, with WI3 correctly
  depending on the vocabulary already living in contract from WI1),
  independently committable, each with named tests and a red/green claim where
  applicable. Complete against every roadmap 7.3.6 success criterion
  (`WORKING_DIR_NAME` and vocabulary in contract; envelope validates against a
  contract-owned set with no `commands.names` import; no command depends on a
  sibling for the working-dir name; the 1.3.1.2 edge removed; suites green).

## Recommended next steps

1. Proceed to implementation as written.
2. (Advisory, optional) Add the one-sentence `finding_outcome.py` docstring note
   to WI3; repoint both `SUBCOMMAND_NAMES` and `ENVELOPE_COMMAND_NAMES` in
   `tests/test_contract_envelope.py`; add a non-empty assertion on the widened
   guard's iterated module set.

## Trail (documents and skills relied on)

- `logisphere-design-review` skill + `references/expert-profiles.md`.
- Source verified: `Makefile`, `AGENTS.md`, `novel_ralph_skill/commands/names.py`,
  `novel_ralph_skill/contract/envelope.py`, `.../contract/__init__.py`,
  `.../commands/state_sourcing.py`, `tests/test_contract_layering.py`,
  `tests/test_state_sourcing_home.py`, `tests/test_contract_envelope.py`,
  `docs/developers-guide.md`, `docs/roadmap.md` (task 7.3.6, 1.3.1.2, 7.3.5).
- Round-1 review: `docs/execplans/roadmap-7-3-6.logisphere-review-r1.md`.
- cuprum read-only sibling at `/data/leynos/Projects/cuprum` — not load-bearing
  (Decision D0 re-confirmed); not touched.
