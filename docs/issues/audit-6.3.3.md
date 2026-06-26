# Post-merge audit — roadmap task 6.3.3

Task 6.3.3 documented the unified command contract and the command-invocation
discipline inside `skill/novel-ralph/SKILL.md` (commit `2c33cb7`). It is a
docs-only change: it added a "Command contract" section to `SKILL.md` carrying
an exit-code table, an envelope-schema restatement, and an "Invocation
discipline" list, plus install-currency guidance, and cleared a markdownlint
baseline failure. It closes the 6.3 epic's "self-documenting" leg, after 6.3.1
made the exit-3 errors actionable and 6.3.2 pinned cross-command exit-code and
envelope-schema consistency.

This audit reviews the merged state at `origin/main` (commit `2c33cb7`) for
refactoring opportunities, duplication, complex conditionals, ergonomic
awkwardness, high-similarity functions, inconsistencies, separation-of-concerns
and command/query-segregation issues, and gaps in documentation comments,
developer/user documentation, and behavioural/unit test coverage. Each finding
records a location and a concrete proposed fix.

The 6.3.3 prose itself is in good shape: the `SKILL.md` exit-code table matches
`exit_codes.py`, the six-field envelope schema matches `envelope.py` field
order, the `ok` biconditional matches `is_ok`, and the cross-references into
ADR-003 Table 2 and the developers' guide sections "The shared JSON envelope"
and "Disambiguated exit codes" all resolve. The material findings are not in the
merged change but in the surrounding command layer the contract now documents:
a repeated state-error wrapping idiom across eight command bodies, a parallel
pack-detect pipeline shared between `desloppify` and its ledger variant, and the
absence of any drift-guard test pinning the new `SKILL.md` contract restatement
to the code it restates.

## 1. The draft-read state-error wrapping idiom is duplicated eight times

- **Category:** duplication
- **Severity:** medium
- **Location:** `novel_ralph_skill/commands/_wordcount.py:96-100`,
  `_recount.py:90-94`, `_compile.py:138-142`, `_compile.py:145-151`,
  `_compile.py:208-212`, `_desloppify.py:201-211`,
  `_state_mutators.py:145-147`, `_novel_done.py:89-93`, and the disk-evidence
  reader `novel_state.py:154-157`.

Eight command bodies wrap a `working/`-tree read in the byte-identical idiom:

```python
try:
    return <reader>(...)
except STATE_INPUT_ERRORS as exc:
    msg = f"<context phrase>: {exc}"
    raise StateInputError(msg) from exc
```

The sites differ only in the reader called and the context phrase ("cannot read
chapter drafts", "cannot recount chapter drafts", "cannot evaluate the done
predicate under {root}", and so on). The `state.toml` *load* boundary already
has a single home — `_state_load._state_input_error` plus `_load_or_state_error`
(roadmap 6.3.1) — but the *draft-read* boundary the same epic governs was never
given the equivalent shared seam, so the translate-to-exit-3 step is hand-rolled
once per command. Each repetition is a place a future contributor can forget the
`from exc` chain, the `STATE_INPUT_ERRORS` tuple, or the exit-3 routing, letting
an undecodable draft escape to the benign exit 1 — exactly the leak each
docstring warns against.

- **Proposed fix:** Add a small context-manager helper to the dependency-free
  `_state_load.py` leaf, beside `STATE_INPUT_ERRORS` and `_state_input_error`,
  for example:

  ```python
  @contextlib.contextmanager
  def state_error_context(context: str) -> cabc.Iterator[None]:
      try:
          yield
      except STATE_INPUT_ERRORS as exc:
          raise StateInputError(f"{context}: {exc}") from exc
  ```

  Replace each of the eight `try/except STATE_INPUT_ERRORS` blocks with
  `with state_error_context("cannot read chapter drafts"): ...`. This collapses
  the eight sites to one tested home, mirroring the load-boundary consolidation
  6.3.1 already established, and keeps the import direction acyclic (the helper
  imports only `StateInputError`, exactly as `_state_input_error` does today).

## 2. `desloppify` and its ledger variant share a parallel pack-detect pipeline

- **Category:** similarity
- **Severity:** medium
- **Location:** `novel_ralph_skill/commands/_desloppify.py:252-266` versus
  `novel_ralph_skill/commands/_desloppify_ledger.py:78-92`.

The rule-pack detect body and the device-ledger detect body are structurally
the same pipeline: load a pack/ledger file; map a *content* error to an exit-2
`CommandOutcome` locally; map a *file* error to an exit-3 `StateInputError`;
source the chapters via the shared `source_chapters`; then run the detector and
project the result through a report-outcome helper. They differ only in three
substitutions — the loader (`load_rulepack` versus `load_ledger`), the error
pair (`RulePackError`/`RulePackFileError` versus `LedgerError`/`LedgerFileError`),
and the report function (`report_outcome`/`detect` versus
`ledger_report_outcome`/`detect_ledger`) — plus the message noun ("rule pack"
versus "device ledger"). The two comment blocks explaining the content-versus-
file split are verbatim copies. A future change to the load-error contract (say,
a new file-error arm) must be applied in both, with no guard that they stay in
step.

- **Proposed fix:** Extract the shared shape into one parametrised helper, e.g.
  `run_pack_detect(*, load, content_error, file_error, file_noun, detect,
  report_outcome, chapter)` that owns the two-arm error handling, the
  `source_chapters` call, and the report projection; have both bodies call it
  with their three substitutions. If the ergonomics of passing six callables
  read worse than the duplication, at minimum hoist the two identical comment
  blocks and the file-error message template into a single shared site so the
  content-versus-file split is documented and worded once.

## 3. The new `SKILL.md` contract restatement has no drift-guard test

- **Category:** test-gap
- **Severity:** medium
- **Location:** `skill/novel-ralph/SKILL.md` "Command contract" section
  (lines 90-185) against `novel_ralph_skill/contract/exit_codes.py` and
  `novel_ralph_skill/contract/envelope.py`; no covering test under `tests/`.

The 6.3.3 section is explicitly a "convenience restatement" that "follows" the
canonical sources and must be edited when the contract changes. Nothing enforces
that following. The exit-code table hard-codes the five code/meaning rows, the
envelope-schema block hard-codes the six field names and their order, and the
`ok`-biconditional prose hard-codes "true if and only if the exit code is 0".
If `ExitCode` gains a code, `ENVELOPE_SCHEMA_VERSION` bumps, or the envelope
field set changes, the `SKILL.md` restatement silently goes stale — the precise
agent-facing failure (a wrong exit-code table) the section exists to prevent.
The repository already has the pattern to guard this: `test_skill_deflation_
guard.py` and `test_state_layout_reference.py` read `SKILL.md` in process and
assert stable mechanism substrings.

- **Proposed fix:** Add a `tests/test_skill_contract_reference.py` that reads
  `SKILL.md` via the shared `read_repo_text` fixture and asserts the contract
  restatement against the code: every `ExitCode` member's value and one-line
  meaning appears as a table row; every `Envelope` dataclass field name appears
  in the documented schema block in declaration order; and the `ok`/exit-0
  biconditional sentence is present. Drive the assertions from
  `ExitCode.__members__` and `dataclasses.fields(Envelope)` so the test fails
  loudly the moment the code and the restatement diverge.

## 4. The contract restatement lives only in `SKILL.md`, not the design source

- **Category:** docs-gap
- **Severity:** low
- **Location:** `skill/novel-ralph/SKILL.md` lines 95-100 and 152-153 point at
  `docs/adr-003-shared-interface-contract.md` and the developers' guide as the
  source of truth; `docs/novel-ralph-harness-design.md` is not named.

The `SKILL.md` section names ADR-003 Table 2 and the developers'-guide sections
as canonical, and §3.1/§3.2 of the design document as the basis for the envelope
and exit-code policy. The pointers resolve, but the agent-facing "where do I edit
when the contract changes" note lists ADR-003 and the developers' guide only; a
contributor who edits `docs/novel-ralph-harness-design.md` §3.1/§3.2 (the
envelope field set, the exit-code meanings) would not learn from this section
that the design document is also a canonical copy that must move in lockstep.
This is a minor completeness gap in an otherwise careful cross-reference block.

- **Proposed fix:** Extend the "the source of truth is …" sentence (line 95-98)
  to name `docs/novel-ralph-harness-design.md` §3.1 and §3.2 alongside ADR-003
  and the developers' guide, so the canonical-copy set the contributor must keep
  in step is listed exhaustively at the one point of use.

## 5. `make markdownlint`/`make nixie` are not gated in CI on docs-only changes

- **Category:** test-gap
- **Severity:** low
- **Location:** `.github/workflows/ci.yml`; `Makefile` targets `markdownlint`
  and `nixie`.

Task 6.3.3's own Work item 0 existed to clear a markdownlint baseline failure,
which means a Markdown lint violation had already reached `main` undetected. The
`Makefile` exposes `markdownlint` and `nixie` targets and `make all` runs
`check-fmt lint typecheck test`, but `markdownlint`/`nixie` are not part of that
chain, so a docs-only change (the whole of 6.3.3) can merge without either gate
running automatically. This audit step runs them by hand; the project should not
rely on the auditor to catch Markdown regressions.

- **Proposed fix:** Either fold `markdownlint` and `nixie` into the `make all`
  prerequisite chain, or add a lightweight docs-lint job to `ci.yml` that runs
  `make markdownlint nixie` on every push. Gate it on Markdown-file changes if
  the cost on code-only PRs is a concern.
