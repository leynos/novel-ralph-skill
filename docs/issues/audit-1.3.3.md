# Post-merge audit — roadmap task 1.3.3

Audit of the codebase after roadmap task 1.3.3 ("Hoist `parse_global_flags` and
`_HUMAN_FLAG` into a shared seam") merged to `main` at commit `61858d5`. The
slice moves the command-agnostic `--human` global-flag splitter
([`parse_global_flags`](../../novel_ralph_skill/contract/runner.py)) and its
`_HUMAN_FLAG` constant out of the `novel-state` command module
([`novel_ralph_skill/commands/novel_state.py`](../../novel_ralph_skill/commands/novel_state.py))
and into the shared contract package
([`novel_ralph_skill/contract/runner.py`](../../novel_ralph_skill/contract/runner.py)),
re-exports it from
[`novel_ralph_skill/contract/__init__.py`](../../novel_ralph_skill/contract/__init__.py),
reroutes the `stub.novel_state()` entry point and the `test_novel_state_check`
importer to the new home, and adds two seam-guard tests to
[`tests/test_contract_runner.py`](../../tests/test_contract_runner.py). The
developers' guide is updated to attribute the splitter to the contract package.

The slice is sound and discharges its success criterion: a command-agnostic
splitter no longer lives in a command module, every consumer imports it from
the contract front door, the package `__all__` advertises it, and a structural
tripwire pins both the re-export identity and the absence of the symbol from the
old command module. The move is clean and introduces no behavioural drift. The
findings below are test-organization, ergonomics, citation-consistency, and
documentation tidy-ups; none is a blocking defect and none weakens the contract.

This audit checks the new surface against the design's authoritative artefacts
and the recurring themes carried by the prior audits (`docs/issues/audit-1.2.1.md`
through `docs/issues/audit-7.3.3.md`). Each finding records a category, a
location, a description, a concrete proposed fix, and a severity.

Trail followed: created a `git-donkey` worktree off `origin/main` and explored
with `leta` (`show`/`refs`/`grep`/`files`) over
`novel_ralph_skill/contract/runner.py`,
`novel_ralph_skill/contract/__init__.py`,
`novel_ralph_skill/commands/novel_state.py`,
`novel_ralph_skill/commands/stub.py`, `tests/test_contract_runner.py`, and
`tests/test_novel_state_check.py`; traced history with `sem diff --commit
61858d5` and `git log origin/main`. Source of truth consulted:
`docs/novel-ralph-harness-design.md` §3.1-§3.2;
[`docs/adr-003-shared-interface-contract.md`](../adr-003-shared-interface-contract.md);
`docs/developers-guide.md` ("The shared JSON envelope"); `docs/roadmap.md`
(task 1.3.3); and `AGENTS.md`. Language router: `python-router` (data shapes,
public API typing, testing). Spelling per `en-gb-oxendict`.

## Finding 1 — The splitter's behavioural unit tests stayed behind in the command test module

- **Category:** separation-of-concerns
- **Severity:** medium
- **Location:**
  [`tests/test_novel_state_check.py:271-298`](../../tests/test_novel_state_check.py)
  (`test_parse_global_flags`) versus the function's new home
  [`novel_ralph_skill/contract/runner.py:52-79`](../../novel_ralph_skill/contract/runner.py)
  and its sibling tests in
  [`tests/test_contract_runner.py:277-301`](../../tests/test_contract_runner.py)

The slice moved `parse_global_flags` from the `novel-state` command module to
the shared contract package, and `test_contract_runner.py` gained two *structural*
guards (the re-export identity and the absence of the symbol from the old
command module). But the only *behavioural* coverage of the splitter — the
parametrized `test_parse_global_flags` exercising leading/trailing/between/
absent/multiple/other-flag-untouched argv shapes — was left in
`tests/test_novel_state_check.py`, whose docstring scopes it to "Behavioural and
end-to-end tests for `novel-state check`". The function is now command-agnostic
and contract-owned, yet the proof of its parsing behaviour lives in a file about
one command. A future reader auditing the contract seam's behaviour will not find
its tests beside the seam; a reader deleting or refactoring the `novel-state`
test module risks orphaning the only argv-shape coverage the splitter has. This
is the test-organization mirror of the very mis-attribution the slice corrected
in the production code.

- **Proposed fix:** Move the `test_parse_global_flags` parametrized case (and its
  `parse_global_flags` import) from `tests/test_novel_state_check.py` into
  `tests/test_contract_runner.py`, grouping it under the existing
  "`parse_global_flags` seam guards" section so the behavioural and structural
  tests for the splitter share one home beside the function. Keep the
  `novel-state` entry-point tests that exercise `--human` *through* the command
  (e.g. `test_human_flag_*` at lines 199 and 236) where they are — they pin the
  command's wiring, not the splitter's parsing.

## Finding 2 — `parse_global_flags` and `run` disagree on the argv parameter type

- **Category:** inconsistency
- **Severity:** low
- **Location:**
  [`novel_ralph_skill/contract/runner.py:52`](../../novel_ralph_skill/contract/runner.py)
  (`parse_global_flags(argv: list[str])`) versus
  [`novel_ralph_skill/contract/runner.py:167-171`](../../novel_ralph_skill/contract/runner.py)
  (`run(app, argv: cabc.Sequence[str], context)`)

The two argv-consuming functions now sitting side by side in `runner.py` accept
different parameter types: `parse_global_flags` demands a concrete `list[str]`,
while `run` accepts the wider `collections.abc.Sequence[str]`. A public
input-parameter is conventionally typed at its widest tolerated abstraction
(accept an interface, return a concrete type); `parse_global_flags` reads `argv`
only by iteration and `len`, so it has no reason to require a `list`. The
mismatch is a small ergonomic wart on a shared seam: a caller holding a
`Sequence[str]` (or a tuple) can pass it to `run` but must first materialize a
`list` for `parse_global_flags`, even though both functions are part of the same
pre-parse-then-run idiom the entry point follows.

- **Proposed fix:** Widen `parse_global_flags`'s parameter to
  `argv: cabc.Sequence[str]` to match `run`, update the docstring's
  Parameters/Returns prose accordingly, and keep the concrete `list[str]` in the
  *return* type (it constructs a fresh list, so returning the concrete type is
  correct). Confirm `pyright` and the existing call sites (`sys.argv[1:]` is a
  `list`, already compatible) stay green.

## Finding 3 — `parse_global_flags` cites a non-existent ADR-003 §3.1

- **Category:** docs-gap
- **Severity:** low
- **Location:**
  [`novel_ralph_skill/contract/runner.py:22`](../../novel_ralph_skill/contract/runner.py)
  (module docstring) and
  [`novel_ralph_skill/contract/runner.py:53`](../../novel_ralph_skill/contract/runner.py)
  (`parse_global_flags` docstring), both reading "ADR-003 §3.1"

The splitter's docstring and the `runner.py` module docstring both attribute the
splitter to "ADR-003 §3.1". ADR-003
([`docs/adr-003-shared-interface-contract.md`](../adr-003-shared-interface-contract.md))
uses named headings ("Context and problem statement", "Requirements",
"Decision outcome / proposed direction") and has no numbered "§3.1" subsection.
The actual referent for the `--human` output-mode contract is *design* §3.1
("Output modes", `docs/novel-ralph-harness-design.md:137`). This is a
repo-wide shorthand the slice inherited and faithfully copied into the moved
docstring rather than a regression — the same "ADR-003 §3.1" string appears in
the roadmap, the execplans, and a prior audit — but the move was an opportunity
to correct the dangling cross-reference, and the citation now sits in a freshly
relocated production docstring where it reads as authoritative.

- **Proposed fix:** Treat as a small, low-priority documentation-consistency
  sweep: decide on the single correct citation (most likely "design §3.1; ADR-003
  Requirements") and apply it to the two `runner.py` docstrings, the
  `novel_state.py` module docstring, and `tests/test_novel_state_check.py`'s
  header. Because the string also appears across `docs/roadmap.md`,
  `docs/execplans/`, and `docs/issues/audit-2.1.2.md`, fold the wider sweep into
  a dedicated citation-hygiene task rather than expanding this slice's footprint.

## Finding 4 — The contract-package public-surface docstring is a hand-maintained list that can drift from `__all__`

- **Category:** docs-gap
- **Severity:** low
- **Location:**
  [`novel_ralph_skill/contract/__init__.py:9-12`](../../novel_ralph_skill/contract/__init__.py)
  (the prose roll-call) versus
  [`novel_ralph_skill/contract/__init__.py:33-46`](../../novel_ralph_skill/contract/__init__.py)
  (`__all__`)

The package docstring spells out the public surface in prose — "…
:class:`StateInputError`, :func:`parse_global_flags`, and :func:`run`." — a
second hand-maintained copy of the `__all__` list immediately below it. This
slice correctly extended *both* (it added `parse_global_flags` to the prose and
to `__all__`), but the two are kept in lockstep only by author diligence. The
next symbol added to the contract front door has two places to update and no
tripwire to catch a one-sided edit, so the prose roll-call can silently fall out
of step with the exported surface. No test pins the correspondence.

- **Proposed fix:** Add a lightweight test in `tests/test_contract_*` asserting
  that every name in `contract.__all__` is referenced by the module docstring (a
  set-membership scan of `contract.__doc__`), so a future one-sided edit fails a
  guard rather than rotting silently. Alternatively, demote the docstring's
  exhaustive roll-call to "see `__all__` for the exported surface" to remove the
  duplicate source of truth. The test option preserves the discoverable prose
  while eliminating the drift risk; prefer it.
