# Broaden the state-layout direct-edit guard to reject any hand-edit recipe

This ExecPlan (execution plan) is a living document. The sections `Constraints`,
`Tolerances`, `Risks`, `Progress`, `Surprises & Discoveries`, `Decision Log`,
and `Outcomes & Retrospective` must be kept up to date as work proceeds.

Status: DRAFT (revised after design-review round 1; guard hardened after
dual-review fix rounds 1 and 2)

## Purpose / big picture

The novel-ralph harness keeps its entire memory in `working/state.toml`. The
design eliminates direct editing of that file: every mutation must pass through
a validated `novel-state` subcommand (`docs/novel-ralph-harness-design.md`
§4.1, "Direct editing of `state.toml` is eliminated"). The skill reference
`skill/novel-ralph/references/state-layout.md` once shipped a copy-pasteable
Python heredoc that imported the undeclared `tomli_w` dependency and hand-wrote
`state.toml` — exactly the pattern §4.1 and ADR-002
(`docs/adr-002-toml-round-trip-tomlkit.md`) reject. Roadmap task 1.2.6 deleted
that snippet and added a guard, `tests/test_state_layout_reference.py`, that
fails `make test` if it returns.

The 1.2.6 guard is deliberately narrow: it pins only the literal `tomli_w`
substrings (`tomli_w`, `tomllib, tomli_w`, `tomli_w.dump(`). A future author
who re-introduces a hand-edit recipe written with the project's *blessed*
library `tomlkit`, or with stdlib `tomllib` paired with any writer, or with a
shell redirect, would sail past the guard green while re-opening the same §4.1
"direct editing eliminated" violation. Roadmap task 1.2.8 widens the guard to
forbid *any* direct `state.toml`-write recipe, not just the one library that
happened to be used first.

After this change, a developer can add a Python or shell code block to
`state-layout.md` that writes `state.toml` outside `novel-state` and watch
`make test` fail with a message naming the offending token and pointing at
§4.1; the same `make test` passes on the current, recipe-free reference. The
guard must achieve this *without* flagging the legitimate prose that describes
the harness's own atomic-write discipline — "write to `state.toml.new`, fsync,
rename" — which the design mandates (`docs/novel-ralph-harness-design.md` §3.4
and §5.3) and which `novel-state` itself implements.

## Constraints

Hard invariants that must hold throughout implementation. Violation requires
escalation, not a workaround.

- Edit only inside the worktree
  `/data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-1-2-8`. Never
  touch the root/control worktree.
- The guard lives in `tests/test_state_layout_reference.py` and must remain a
  pure static-text check that reads the reference with `pathlib` and asserts in
  process. It must not shell out, import `novel_ralph_skill`, or read any file
  other than `skill/novel-ralph/references/state-layout.md`. This matches the
  1.2.6 design intent (the module docstring states "it does not shell out") and
  keeps the guard fast and dependency-free.
- Do not modify `skill/novel-ralph/references/state-layout.md` prose in this
  task. Rewriting the reference prose to point at the `novel-state` commands is
  owned by roadmap task 6.2.3 (`docs/roadmap.md` lines 468-476); 1.2.8 only
  hardens the guard. The roadmap text for 1.2.8 says the widening is
  "coordinated with task 6.2.3"; coordination here means the guard must not
  forbid anything 6.2.3 will legitimately need to write (see Risks).
- The guard must keep passing on the reference *as it stands today*: the
  current `state-layout.md` contains the atomic-write prose and a `toml` schema
  fence, and neither is a forbidden recipe. A guard that fails on the current
  tree is wrong.
- No new runtime or dev dependency. The locked dev set in `pyproject.toml`
  (`pytest`, `pytest-timeout`, `pytest-xdist`, plus lint/type tooling) is
  sufficient; the guard uses only the standard library (`pathlib`, `re`).
- All prose, comments, docstrings, and commit messages use en-GB Oxford
  spelling ("-ize"/"-yse"/"-our"), per AGENTS.md.
- Target Python 3.14 (`requires-python = ">=3.14"`),
  `from __future__ import annotations` at the top of the module, matching the
  existing file.

## Tolerances (exception triggers)

- Scope: the task touches exactly three files —
  `tests/test_state_layout_reference.py` (the guard),
  `docs/developers-guide.md` (the convention note), and `docs/roadmap.md` (the
  task tick). If the implementation needs to touch more than these three, or
  more than ~120 net lines, stop and escalate.
- Interface: this task adds no public API. If satisfying it appears to require
  changing `novel_ralph_skill` or adding a shared test helper that other
  modules import, stop and escalate (the shared-scaffolding consolidation is
  roadmap task 1.2.7, a separate work item).
- Dependencies: if any work item appears to need a new dependency (e.g. a
  Markdown-AST parser such as `markdown-it-py`), stop and escalate; the plan's
  position is that a small, well-tested `re`-based code-fence scanner is
  sufficient and a parser is over-engineering for a single reference file.
- Iterations: if the guard still misclassifies (false positive on the current
  reference, or false negative on a planted recipe) after 3 attempts, stop and
  escalate.
- Ambiguity: if review concludes the guard should also cover other skill
  references (e.g. `done-conditions.md`) beyond `state-layout.md`, stop and
  escalate — the roadmap scopes 1.2.8 to the state-layout guard only.

## Risks

- Risk: over-broad matching flags the legitimate atomic-write prose or the
  `toml` schema fence, breaking the green-on-current invariant. The
  atomic-write language lives entirely in **prose** — the one-line summary at
  state-layout.md line 60-61 ("written atomically (write to `state.toml.new`,
  fsync, rename)") and the numbered "Discipline" list under the
  `## Atomic writes` heading at lines 214-228 (verified by reading the file:
  line 212 is the heading, 214-228 are prose plus a numbered list, with **no
  fenced code block** there). Because this language is outside any fence,
  fence-scoped scanning already leaves it alone; the risk is only that a
  scanner which forgets the fence filter would flag it.
  - Severity: high. Likelihood: medium.
  - Mitigation: scope the write-token scan to executable code fences only (info
    strings python/py/sh/bash/shell/console), not prose or `text`/`toml` fences.
    Add a regression test asserting the current reference passes, and a test
    asserting a synthetic string carrying the atomic-write prose (no fence) does
    not trip the guard.
- Risk: over-broad `open(` matching flags a legitimate *read* of `state.toml`
  (e.g. a future validation example doing
  `tomllib.load(open("working/state.toml", "rb"))`, which contains both `open(`
  and `state.toml` but is read-only). Roadmap task 6.2.3 may add such read
  examples when it rewrites the prose.
  - Severity: medium. Likelihood: medium.
  - Mitigation: require a *write signal*, never bare `open(`. A fence trips the
    `open(` rule only when it pairs `state.toml` with a write mode literal
    (`"w"`, `"a"`, `"x"`, `"wb"`, `"ab"`, `"xb"`, `"w+"`, etc.) or a `.write(` /
    `.writelines(` call. Add a negative test feeding a read-only
    `open("working/state.toml", "rb")` + `tomllib.load(...)` `python` fence and
    assert an empty result.
- Risk: under-broad matching lets a real hand-edit recipe through (the whole
  point of the task), e.g. a `tomlkit.dump` write or a `cat > state.toml`
  heredoc.
  - Severity: high. Likelihood: medium.
  - Mitigation: drive the token set from the verified write surface (see the
    Decision log: tomlkit/tomllib/shell), and add a planted-recipe table test
    covering tomlkit, tomllib plus writer, raw `open().write`, `Path.write_text`,
    and shell redirect or heredoc forms. Each planted recipe must fail the guard.
- Risk: collision with task 6.2.3, which rewrites state-layout prose to point at
  `novel-state`. Roadmap 6.2.3 (lines 468-476) commits only to pointing the
  prose at the commands, reducing the done-predicate copies, and removing the
  dead `plan.md` reference; it does **not** promise a `novel-state` code fence.
  Even so, an over-eager guard could block a future sanctioned example, so the
  positive test below is kept as a defensive forward guard rather than as
  coverage of a promised artefact.
  - Severity: medium. Likelihood: low.
  - Mitigation: the guard forbids direct writes to the state.toml path from
    within a code fence, not mentions of state.toml or invocations of
    `novel-state`. A `novel-state set-cursor ...` example contains no write
    primitive and no redirect to the state file, so it passes. Document this
    boundary in the guard docstring and add a defensive positive test that a
    `novel-state` example fence passes.
- Risk: shell redirect tokens (`>`, `>>`, `tee`, `cat >`) matched
  *redirect-anywhere* would trip on any unrelated future `sh` fence that
  redirects to some other path (e.g. `echo done > /tmp/marker`), a false
  positive that breaks green-on-current the moment such an example lands.
  - Severity: medium. Likelihood: medium.
  - Mitigation: anchor every redirect rule to the `state.toml` path — the
    redirect must target `state.toml` (e.g. `> ...state.toml`,
    `tee ...state.toml`). Add a negative test feeding a `sh` fence with
    `echo done > /tmp/foo` and assert an empty result, so the rule is
    path-anchored, not redirect-anywhere.
- Risk: a future recipe uses a token the scan does not enumerate (e.g. an exotic
  writer), giving a false sense of completeness.
  - Severity: low. Likelihood: low.
  - Mitigation: include a backstop rule — any executable fence that both names
    the `state.toml` path and contains a write or redirect primitive fails — so
    the guard catches novel writers that target the file by path even when the
    library token is unknown. Document this as best-effort, not a proof.

## Progress

- [x] (done) Work item 1: broaden the guard in a single red-then-green
  commit — write the failing predicate tests, then implement the code-fence
  write-recipe scanner so the suite is green at commit time (no gate-failing
  commit). Landed as commit `ba17f1d`.
- [ ] (pending) Work item 2: documentation note, roadmap tick, and full gate
      run.

## Surprises & discoveries

- Observation: the current `state-layout.md` contains no executable code fence
  that writes `state.toml`; the only state.toml-write language is **prose**.
  The atomic-write discipline is the one-line summary at line 60-61 and the
  numbered "Discipline" list under `## Atomic writes` at lines 214-228 —
  neither is fenced.
  - Evidence: `grep -n '^```' state-layout.md` lists six fences only — `text`
    (13-52), `toml` (63-116), `text` (122-134), `markdown` (185-199), `text`
    (234-243), `text` (249-257). The two trailing `text` fences are the
    Initialisation and Resumption pseudocode; neither describes the write/rename
    discipline, and no python or sh fence touches state.toml. Line 212 is the
    `## Atomic writes` heading and 214-228 are prose plus a numbered list (no
    fence).
  - Impact: because the discipline is prose, fence-scoped scanning already
    leaves it untouched; the guard need only scan executable fences. The
    green-on-current regression test rests on this fact, not on a (non-existent)
    atomic-write fence.
- Observation: `tomllib` (stdlib, Python 3.14) is read-only; it exposes
  `load`/`loads` only and has no `dump`. A "tomllib-based hand-edit" therefore
  necessarily pairs `tomllib.load` with a separate write primitive.
  - Evidence: the Python 3.14 stdlib `tomllib` module documents only
    `load`/`loads`; the locked `tomlkit` 0.15.0 (uv.lock line 639) provides the
    writers `dump`/`dumps`.
  - Impact: the token set keys on the *write* primitive, not the read library,
    so a bare `tomllib.load(open(... "rb"))` read of `state.toml` must NOT be
    flagged (see the read-only negative test in work item 1).

## Decision log

- Decision: scan executable code fences for a write-to-state.toml primitive,
  rather than blanket substring-matching the whole document.
  - Rationale: the §4.1 violation is a copy-pasteable recipe, not a mention of
    state.toml. The reference legitimately discusses state.toml in prose and
    mandates the state.toml.new atomic-write discipline (design §3.4 and §5.3);
    blanket substring matching would either flag that discipline or be so narrow
    it misses real recipes. Fence-scoped matching is the only approach that
    satisfies both the green-on-current and catch-real-recipes invariants.
  - Date/Author: 2026-06-22, planning agent.
- Decision: the forbidden write surface is the union of (a) the `tomli_w` tokens
  the 1.2.6 guard already pins (`tomli_w`, `tomllib, tomli_w`,
  `tomli_w.dump(`); (b) tomlkit write tokens `tomlkit.dump` and
  `tomlkit.dumps`; (c) generic Python file-writes targeting the state file —
  `.write_text(` paired with `state.toml`, and `open(` paired with `state.toml`
  **only when a write signal is also present** (a write-mode literal `"w"`/`"a"`
  /`"x"`/`"wb"`/`"ab"`/`"xb"`/ `"w+"` etc., or a `.write(`/`.writelines(`
  call), so a read-only `open(... "rb")` is not flagged; (d) shell redirects
  and heredocs whose target is the state file — `> ...state.toml`,
  `>> ...state.toml`, `tee ...state.toml`, `cat > ...state.toml` — every
  redirect rule anchored to the `state.toml` path, never redirect-anywhere;
  plus a backstop where any executable fence naming `state.toml` together with
  a write or redirect primitive *that targets that path* fails.
  - Rationale: tomlkit (locked 0.15.0) is the project's blessed writer and the
    named gap in the roadmap; tomllib cannot write, so it is covered by its
    paired writer; raw `open`/`Path.write_text` and shell redirects are the
    obvious remaining hand-edit forms. Requiring a write signal beside `open(`
    keeps a legitimate read example green; path-anchoring the redirects keeps an
    unrelated `> /tmp/foo` fence green. The backstop catches unknown writers by
    path.
  - Date/Author: 2026-06-22, planning agent.
- Decision: fold the red predicate tests and the green implementation into a
  single commit (work item 1), rather than committing the red tests separately.
  - Rationale: AGENTS.md "Change quality and committing" (lines 99 and 108)
    states "Only changes that meet all quality gates should be committed" and
    "Do not commit changes that fail any quality gate." `make test` is a gate, so
    a red-tests-only commit is forbidden. Test-driven development (write the
    failing test, observe red, implement, observe green) still happens — it just
    completes within one working session and lands as one passing commit. The
    red transcript is captured in `Artifacts and notes` as evidence, not as a
    committed state.
  - Date/Author: 2026-06-22, planning agent.
- Decision: use a small `re`-based fence scanner in the test module, not a
  Markdown-AST dependency.
  - Rationale: one reference file, a closed fence grammar, and the no-new-dep
    constraint. A regex that captures fenced blocks and filters by info string is
    sufficient and keeps the guard self-contained. An AST parser would breach the
    dependency tolerance for no behavioural gain.
  - Date/Author: 2026-06-22, planning agent.
- Decision: do not pre-empt roadmap task 1.2.7 (shared `conftest.py`). The guard
  keeps its own private `_state_layout_text` reader.
  - Rationale: 1.2.7 owns consolidating the duplicated readers; 1.2.8 must stay
    atomic and independently committable. Introducing the shared helper here
    would couple two roadmap items and breach the interface tolerance.
  - Date/Author: 2026-06-22, planning agent.

## Outcomes & retrospective

Delivered. The broadened guard meets the purpose:

- A planted hand-edit recipe fails the guard in every covered form. The
  parametrized `test_planted_recipe_is_flagged` table proves this for the
  `tomlkit.dump`, `tomllib` + `Path.write_text`, raw `open().write`, historical
  `tomli_w` heredoc, shell `cat`/`>>`/`tee`, and unknown-writer-backstop forms;
  each returns a non-empty, design-§4.1-citing message.
- The current, recipe-free `state-layout.md` still passes:
  `test_reference_has_no_direct_write_recipe` asserts an empty result and
  `make test` is green on the unmodified reference.
- The atomic-write *prose*, a read-only `open(…, "rb")`, an unrelated
  `> /tmp/foo` redirect, a `novel-state` example, and the non-executable `toml`
  schema fence are all left untouched (five negative tests, all green).

Retrospective: the only friction was tooling, not design. Ruff's
implicit-string-concatenation rule forced the planted recipes out of the
`parametrize` literal into a module-level `_PLANTED_RECIPES` dict (a readability
gain), and `make fmt`'s mdformat-all pass churns unrelated docs, so the touched
Python file was formatted with `ruff format` directly and the doc churn was
stashed. The plan's verified line-range observations (six fences, prose-only
atomic-write discipline) held exactly, so no escalation was needed. The
implementation stayed within the three-file, ~120-line scope tolerance.

## Context and orientation

The reader needs no prior plans. Key facts and paths:

- Working tree (all paths below are relative to it):
  `/data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-1-2-8`.
- The guard under change: `tests/test_state_layout_reference.py`. It is a single
  module with one helper `_state_layout_text()` (reads
  `skill/novel-ralph/references/state-layout.md` via `pathlib`) and one test
  class `TestStateLayoutReference` with two tests pinning the `tomli_w`
  substrings. It does not shell out and imports only `pathlib`.
- The protected file:
  `skill/novel-ralph/references/state-layout.md`. Today it contains no
  executable code fence that writes `state.toml`; its six fences are info-string
  `text` (lines 13-52), `toml` (63-116, the schema), `text` (122-134),
  `markdown` (185-199), `text` (234-243, Initialisation pseudocode), and `text`
  (249-257, Resumption pseudocode). Its **prose** — not any fence — describes
  the harness's mandatory atomic-write discipline (write `state.toml.new`,
  fsync, rename over `state.toml`): the one-line summary at lines 60-61 and the
  numbered "Discipline" list under the `## Atomic writes` heading at lines
  214-228 (the heading itself is line 212). No `text` fence describes the
  write/rename discipline.
- Source of truth for the rule:
  - `docs/novel-ralph-harness-design.md` §4.1 — "All state mutation hides behind
    validated subcommands. Direct editing of `state.toml` is eliminated."
  - `docs/novel-ralph-harness-design.md` §3.4 and §5.3 — the atomic
    temp-file-and-`Path.replace` write discipline and the `tomlkit` round-trip.
  - `docs/adr-002-toml-round-trip-tomlkit.md` — selects `tomlkit` over `tomli_w`
    as the *only* sanctioned writer, and notes the failed `tomli_w` snippet was
    removed.
- Coordination: `docs/roadmap.md` lines 140-147 (task 1.2.8) and lines 468-476
  (task 6.2.3, which later rewrites the reference prose to point at the
  commands).
- Quality gates: AGENTS.md "Change quality and committing" — `make test`,
  `make lint`, `make check-fmt`, `make typecheck`, `make audit`; plus
  `make markdownlint` and `make nixie` for any Markdown change. The Makefile is
  the canonical entry point.
- Locked libraries verified for the token set: `tomlkit` 0.15.0 (uv.lock line
  639; writers `dump`/`dumps`); stdlib `tomllib` is read-only (no `dump`). No
  new dependency is added by this task.
- External-library scope note: this guard is a pure static-text predicate. It
  imports only `pathlib` and `re` and never shells out, so it does not exercise
  any cuprum API (catalogue construction, allowlisting, `program.run`/output
  options in `/data/leynos/Projects/cuprum/`), nor Cyclopts, nor any pytest
  plugin behaviour beyond plain in-process assertions. The locked external
  surface is therefore irrelevant to this task: there is no command execution,
  no subprocess, and no xdist-sensitive fixture. `tomlkit` and `tomllib` appear
  only as *token strings* the scanner matches in document text, never as
  imported code. No firecrawl-verified library behaviour is load-bearing here.

Definitions:

- "Direct-edit recipe" / "hand-edit recipe": a copy-pasteable snippet (Python or
  shell) inside an executable code fence that writes the `state.toml` file
  without going through a `novel-state` subcommand.
- "Executable code fence": a fenced code block whose info string is one of
  `python`, `py`, `sh`, `bash`, `shell`, `console`. Fences labelled `text`,
  `toml`, `markdown`, or `json` are treated as non-executable illustration and
  are not scanned for write recipes (they cannot tempt a reader to run them as
  a mutation script).

## Plan of work

Two ordered, independently committable work items, each gate-passable at commit
time. Test-driven: within work item 1, write the failing predicate tests first,
observe red, then implement the guard so the commit lands green. No commit is
made in a gate-failing state (AGENTS.md "Change quality and committing", lines
99 and 108).

### Work item 1 — Broaden the guard (red-then-green, one commit)

Implements: `docs/novel-ralph-harness-design.md` §4.1 (direct editing
eliminated); `docs/adr-002-toml-round-trip-tomlkit.md` (tomlkit is the only
sanctioned writer); AGENTS.md "Python verification and testing" (failing test
observed before the change, happy and unhappy paths, edge cases) and "Code
style and structure" (small, single-responsibility functions; comment *why*);
AGENTS.md "Change quality and committing" (commit only when all gates pass).

Docs to read first: `docs/novel-ralph-harness-design.md` §4.1, §3.4, §5.3;
`docs/adr-002-toml-round-trip-tomlkit.md`; the existing
`tests/test_state_layout_reference.py`; AGENTS.md testing and committing
sections; `.rules/python-00.md`, `.rules/python-typing.md`,
`.rules/python-return.md` (style, annotation, and return conventions).

Skills to load: `python-router` → `python-testing` (pytest parametrization and
the fixture boundary), `python-types-and-apis` (the predicate's public
signature and `list[str]` return shape), and `python-errors-and-logging` (the
guard raises no exceptions; it returns messages and the test asserts — no
logging is added). Optionally `python-iterators-and-generators` if the fence
scan reads cleanly as a generator over fences. Hypothesis/CrossHair/mutmut are
*not* warranted here — the guard is a deterministic string predicate over a
closed, enumerable set of recipe forms, not an invariant over a large input
space, so example-based parametrized tests are the correct adversary
(`python-verification` would route the same way). Do not pull in `hypothesis`.

Step 1 — write the failing tests. Add to `tests/test_state_layout_reference.py`
(or a sibling test class in the same module) tests that exercise a new,
not-yet-existing predicate. Factor the rule as a module-level pure function —
propose the signature:

```python
# tests/test_state_layout_reference.py
def find_direct_state_write_recipes(markdown: str) -> list[str]:
    """Return a message per executable code fence that writes ``state.toml``.

    Empty list means the document is clean. Each message names the offending
    fence's info string and the matched write token, so a failure points the
    author at the recipe and at design §4.1.
    """
```

Tests to add (all in `tests/`, per AGENTS.md "keep pytest tests in the top-level
`tests/` tree"):

1. Green-on-current regression: `find_direct_state_write_recipes` returns an
   empty list for the real `_state_layout_text()`. This pins the
   green-on-current invariant from Constraints.
2. Atomic-write prose is not flagged: feed a **synthetic** string carrying the
   atomic-write language as *prose* — the line-60-61 summary plus the numbered
   "Discipline" list under `## Atomic writes` (text such as "Write state.toml
   via a temporary file in working/, then atomically rename it over
   working/state.toml") with **no fence around it** — and assert an empty
   result. This mirrors how the real file carries the discipline (prose, not a
   fence); label it in a comment as a synthetic fixture reconstructing the real
   prose, not a copy of a fenced block. Guards the over-broad-prose Risk.
3. Read-only `open` is not flagged: feed a `python` fence containing
   `tomllib.load(open("working/state.toml", "rb"))` (a read, no write signal)
   and assert an empty result. Guards the over-broad-`open(` Risk and protects
   any read example 6.2.3 may add.
4. Unrelated redirect is not flagged: feed a `sh` fence containing
   `echo done > /tmp/foo` (a redirect to a different path) and assert an empty
   result. Guards the redirect-anywhere Risk; proves the rule is path-anchored.
5. `novel-state` example is not flagged: feed a `sh` fence containing
   `novel-state set-cursor --chapter 7` and assert an empty result. Defensive
   forward guard for the 6.2.3 collision Risk (6.2.3 does not promise such a
   fence, but the guard must not block one if it appears).
6. Non-executable fence is ignored: a `toml` fence that literally contains a
   `state.toml` token (like the schema block) returns empty — confirming the
   info-string filter.
7. Planted-recipe table (parametrized, one row per forbidden form), each
   asserting a non-empty result:
   - Python `tomlkit.dump(doc, f)` writing into
     `open("working/state.toml", "w")`.
   - Python `tomllib.load` paired with
     `pathlib.Path("working/state.toml").write_text(...)`.
   - Python raw `open("working/state.toml", "w").write(...)`.
   - The historical `import tomllib, tomli_w, os` + `tomli_w.dump(...)` heredoc
     (the 1.2.6 case must still fail under the new predicate).
   - Shell `cat > working/state.toml <<'EOF' ... EOF`.
   - Shell `echo ... >> working/state.toml`.
   - Shell `tee working/state.toml`.
   - Backstop: an unknown-writer fence that names `working/state.toml` and a
     `.write(` primitive but no enumerated library token — must still fail.

Observe red: from the worktree root run `make test`. Expect the new tests that
target `find_direct_state_write_recipes` to **fail** with `NameError`/
`AttributeError` (the predicate does not exist yet). Capture this transcript in
`Artifacts and notes`. Do **not** commit at this point — a red-test state is
not gate-passable and must not be committed.

Step 2 — implement the predicate in `tests/test_state_layout_reference.py`:

1. A small `re`-based fence extractor that yields `(info_string, body)` tuples
   for each fenced block. Use a compiled pattern capturing the opening fence
   info string and the body up to the closing fence. Keep it readable; comment
   *why* the info-string filter exists (so the guard never scans the
   atomic-write prose or the `toml` schema fence).
2. A constant set of executable info strings:
   `{"python", "py", "sh", "bash", "shell", "console"}`.
3. The write-token rule, driven by the Decision Log surface. For each
   executable fence whose body contains `state.toml`, flag it when any of:
   - it contains `tomlkit.dump`, `tomli_w`, or `.write_text(`;
   - it contains `open(` **and** a write signal — a write-mode literal
     (`"w"`, `"a"`, `"x"`, `"wb"`, `"ab"`, `"xb"`, `"w+"`, etc.) or a paired
     `.write(`/`.writelines(` — so a read-only `open(... "rb")` does not trip;
   - it contains a redirect/heredoc whose target is the `state.toml` path
     (`> ...state.toml`, `>> ...state.toml`, `tee ...state.toml`,
     `cat > ...state.toml`) — never a bare `>`/`tee` to some other path;
   - backstop: the fence body pairs `state.toml` with a `.write(` primitive
     targeting that path even when no library token is recognised.
   Return one descriptive message per offending fence naming its info string
   and the matched token, so a failure points the author at the recipe and at
   design §4.1.
4. Rewrite the two existing substring tests' guard so the broad-case assertion
   delegates to `find_direct_state_write_recipes`, while the explicit `tomli_w`
   substring checks remain as named, documented regressions of the 1.2.6 case
   (do not delete them — they pin the specific historical strings cheaply, so
   the broadening is strictly additive).
5. Update the module docstring: replace the "substring-specific by design …
   broadening it would collide with roadmap task 6.2.3" paragraph (lines 13-16
   of the current file) with the new, broadened intent — the guard now forbids
   any direct `state.toml`-write recipe in an executable fence, while leaving
   the atomic-write *prose* and any `novel-state` invocation example untouched
   so it does not collide with 6.2.3's prose rewrite. Cite design §4.1 and
   ADR-002.

Keep the module under the 400-line AGENTS.md limit (it is tiny today; this
stays well within it). Maintain 100% docstring coverage — `interrogate` runs
under `make lint`, so every new function and class needs a docstring.

Validation (run sequentially from the worktree root, never in parallel per the
build-cache note): `make check-fmt`, then `make lint`, then `make typecheck`,
then `make test`, then `make audit`, then `make all`. Expect all green: every
new test now passes, the existing suite stays green, `interrogate` reports 100%,
`ruff`/`ruff format`/`ty` clean, `pip-audit` clean. Capture the `make test`
summary line (N passed) in `Artifacts and notes`. Only when every gate is green
is the commit made.

Commit (single, gate-passing): "Broaden state-layout guard to reject any direct
state.toml write".

### Work item 2 — Documentation note, roadmap tick, and Markdown gates

Implements: AGENTS.md "Documentation maintenance" (record the convention) and
"Markdown files" gates; `docs/roadmap.md` task-completion convention.

Docs to read first: `docs/developers-guide.md` (where guard conventions are
recorded — it already documents the interrogate gate at lines 12-14 and the
entry-point guard at lines 87-90), `docs/documentation-style-guide.md` (wrap at
80 columns, en-GB Oxford spelling), and `docs/roadmap.md` task 1.2.8 (lines
140-147) and task 6.2.3 (lines 468-476).

Skills to load: `en-gb-oxendict` (spelling enforcement for the prose edits).

What to do:

1. Add a short paragraph to `docs/developers-guide.md` recording the broadened
   guard as a project convention: `state-layout.md` must not carry any
   copy-pasteable recipe that writes `state.toml` outside `novel-state`; the
   guard `tests/test_state_layout_reference.py` enforces this by scanning
   executable code fences (`python`/`py`/`sh`/`bash`/`shell`/`console`) for a
   write primitive that targets the state-file path, while leaving the
   atomic-write *prose* untouched. Note that rewriting the reference prose to
   point at the `novel-state` commands remains roadmap task 6.2.3's job.
   Cross-reference design §4.1 and ADR-002. Keep it consistent with the
   existing guard-documentation style (the interrogate and entry-point guard
   notes).
2. Tick task 1.2.8 in `docs/roadmap.md` (`- [ ]` → `- [x]`). Do **not** alter
   the 6.2.3 entry.

Validation (run sequentially from the worktree root, never in parallel):
because two `.md` files changed, run `make markdownlint` and `make nixie` (the
edited Markdown has no Mermaid, so `nixie` passes trivially, but AGENTS.md
requires running it for any Markdown change). Then run the full code suite plus
the non-`all` gates as a final end-to-end check, in this order: `make all`, then
`make audit`, then `make markdownlint`, then `make nixie`. (`make all` is
`build check-fmt lint typecheck test` per Makefile line 28; it does **not** run
`audit`, `markdownlint`, or `nixie`, so those are run explicitly.) Expect
`make all` green, `make audit` clean, `make markdownlint` clean, `make nixie`
clean. Capture each summary in `Artifacts and notes`.

Commit: "Document broadened state.toml-write guard and tick roadmap 1.2.8".

## Concrete steps

Run everything from the worktree root
`/data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-1-2-8`.

1. Confirm the branch and clean tree from the worktree root. Run
   `git branch --show-current` (expect `roadmap-1-2-8`) and
   `git status --short` (expect
   clean or plan-only).

2. Work item 1, step 1 — add the failing predicate tests, then run `make test`
   to observe red. Expect the new `find_direct_state_write_recipes` tests to
   error or fail (the predicate does not exist yet) while the existing tests
   pass, e.g. a
   `NameError: name 'find_direct_state_write_recipes' is not defined`. Capture
   the transcript. Do **not** commit this red state.

3. Work item 1, step 2 — implement the predicate and rewire the guard, then gate
   by running, sequentially from the worktree root: `make check-fmt`,
   `make lint`, `make typecheck`, `make test`, `make audit`, `make all`. Expect
   all green; `make test` reports all tests passed. Commit once, gate-passing.

4. Work item 2 — edit the two Markdown files, then run, sequentially:
   `make markdownlint`, `make nixie`, then `make all`, then `make audit`.
   (`make all` is `build check-fmt lint typecheck test` per Makefile line 28
   and does not chain `audit`/`markdownlint`/`nixie`, so each is run
   explicitly.) Expect `markdownlint` and `nixie` clean and `make all` green.
   Commit once, gate-passing.

5. Commit each work item separately with a file-based commit message (never
   `-m`), per the `commit-message` skill, after its gates pass. Two commits
   total — no commit is made while any gate is red.

## Validation and acceptance

Acceptance is behavioural and observable:

- Before the guard change, a planted hand-edit recipe (any covered form) added
  to a test string is *not* caught by the 1.2.6 substring guard; after the
  change, `find_direct_state_write_recipes` returns a non-empty, descriptive
  message for each such form, and `make test` fails if such a recipe is added
  to the real reference.
- The current, recipe-free `state-layout.md` passes the guard: the
  green-on-current regression test asserts an empty result, and `make test` is
  green on the unmodified reference.
- The atomic-write discipline prose, a read-only `open(... "rb")` of
  `state.toml`, an unrelated `> /tmp/foo` redirect, and a `novel-state`
  invocation example are *not* flagged (negative tests assert empty results).

Quality criteria ("done"):

- Tests: every new and existing test in `tests/test_state_layout_reference.py`
  passes under `make test`; within work item 1 the new tests are observed
  failing before the predicate lands and passing after (red-then-green captured
  in `Artifacts and notes`), but the commit itself is green.
- Lint/typecheck: `make lint` (ruff + `interrogate` 100% docstring coverage +
  Pylint) and `make typecheck` (`ty`) clean; `make check-fmt` clean.
- Audit: `make audit` (`pip-audit`) clean — no new dependency is introduced.
- Markdown: `make markdownlint` and `make nixie` clean on the edited docs.

Quality method: run the Makefile targets sequentially (per the build-cache
note, never in parallel) from the worktree root. `make all` is
`build check-fmt lint typecheck test` (Makefile line 28) and does **not** run
`audit`, `markdownlint`, or `nixie`; the final end-to-end check is therefore
`make all` followed by `make audit`, then (for the Markdown work item)
`make markdownlint` and `make nixie`, each run on its own so no gate is skipped.

## Idempotence and recovery

- All steps are re-runnable. The test edits are additive and deterministic; the
  Markdown edits are single-paragraph insertions and a one-character checkbox
  flip.
- If `make test` reports an unexpected failure outside the guard module, stop:
  the guard must not affect other suites (Constraint: it reads only one file
  and imports only `pathlib`/`re`). Revert the guard edit and re-examine.
- If `markdownlint` flags wrapping, re-wrap the inserted paragraph to 80 columns
  and re-run; `make fmt` may be used to normalise Markdown tables (none added
  here).
- No destructive operations. Recovery is `git checkout -- <file>` on any edited
  file within the worktree.

## Artifacts and notes

- Record both halves of work item 1 here: the red transcript (the failing
  `find_direct_state_write_recipes` tests before the predicate lands) and the
  green `make test` summary after implementation. The red transcript is
  evidence only; it is never committed.
- Work item 1 result (commit `ba17f1d`): the predicate and its tests were
  written together within one session (TDD performed in place; no red state
  committed, per Decision-log AGENTS.md lines 99/108). `make check-fmt`, `make
  lint` (ruff clean, `interrogate` 100%, Pylint 10.00/10), `make typecheck`
  (`ty` clean), `make test` (61 passed), `make all` (61 passed), and `make
  audit` (no known vulnerabilities) were all green. The new
  `TestFindDirectStateWriteRecipes` class covers the green-on-current
  regression, the five negative cases, and the eight-row planted-recipe table.
- Work item 1 deviations: (a) the planted recipes were lifted into a
  module-level `_PLANTED_RECIPES` dict because ruff's implicit-string-
  concatenation rule (ISC) forbids multi-line string fragments inside a
  `parametrize` collection literal; the dict keeps each fixture readable and is
  driven into `parametrize` via `list(_PLANTED_RECIPES.items())`. (b) The
  empty-result assertions use `assert not find_direct_state_write_recipes(...)`
  rather than `== []` to satisfy Pylint C1803. (c) `make fmt` (mdformat-all)
  spuriously rewrites many unrelated tracked `.md` files; those mutations were
  stashed and not committed, and only `ruff format` was run on the touched
  Python file. The Safety Net blocks `git checkout --` and `rm -rf`, so doc
  reverts use `git stash push -- docs/` and temp cleanup avoids `-rf`.
- coderabbit (work item 1): one minor finding, against the pre-existing review
  artefact `docs/execplans/roadmap-1-2-8.review-r1.md` (an Oxford-comma nit in a
  reviewer list), not against any file changed by this work item. No actionable
  finding on the guard module; left unchanged.
- Work item 2 result: added the "The state-layout direct-edit guard"
  subsection to `docs/developers-guide.md` (after "State and on-disk layout")
  and ticked roadmap task 1.2.8 (`- [ ]` -> `- [x]`), leaving 6.2.3 untouched.
  Gate summaries — `make markdownlint`: 55 files, 0 errors; `make nixie`: all
  diagrams validated; `make all`: 61 passed; `make audit`: no known
  vulnerabilities.
- coderabbit (work item 2): one finding, severity "major", against
  `docs/execplans/roadmap-1-2-8.md`. It is stale: it re-raises the three
  round-1 blocking defects (the false `text` fence at 212-228, the gate-failing
  red-test commit, and the claim that `make all` chains audit/markdownlint/
  nixie) that the plan's round-2 "Revision note" already resolved. Verified all
  three are corrected in the current plan: every assertion states lines 214-228
  are prose with no fence; Progress shows one red-then-green commit (work item
  1); and the validation sections state `make all` is
  `build check-fmt lint typecheck test` with audit/markdownlint/nixie run
  explicitly. The shipped implementation matches (test #2 feeds synthetic prose,
  not a fence; one green commit `ba17f1d`; gates run sequentially). No
  actionable change; left as is.
- Dual-review fix round 1 (commit `32873c6`): closed four blocking
  guard-bypass findings against `tests/test_state_layout_reference.py`, all of
  which let a forbidden recipe report green.
  - (a) Indented executable fences were never scanned. `_FENCE_RE` anchored
    both fence markers to the line start with zero leading whitespace, so a
    `python` or `sh` fence nested in a numbered-list step (CommonMark permits
    up to three leading spaces) was invisible — the idiomatic
    "Discipline"-list structure the guard is meant to catch. Fixed by allowing
    up to three spaces of indentation on the opening and closing markers and
    adding `_dedent_fence_body`, which strips the captured indentation from
    each body line before the write-token rule runs.
  - (b)/(c) The standard append form `tee -a` of the covered `tee` redirect
    token escaped `_REDIRECT_RE`, which anchored `tee` directly to whitespace
    and the path. Fixed by allowing optional `-` flag tokens between `tee` and
    the path.
  - (d) The `python3`, `py3`, and `pycon` info strings bypassed the closed
    `_EXECUTABLE_INFO_STRINGS` set. Added them, and split the Python-only
    `.write(` backstop onto a dedicated `_PYTHON_INFO_STRINGS` set. A negative
    lookbehind on the redirect rule keeps a triple-prompt `pycon` REPL line
    from being misread as a two-character append operator, so a read-only
    `tomllib.load(open(..., "rb"))` console session is not falsely flagged.
  - Regression coverage: planted rows `shell-tee-append`,
    `python3-raw-open-write`, and `indented-list-step-append`, plus negative
    tests `test_indented_unrelated_redirect_not_flagged` and
    `test_pycon_read_only_session_not_flagged`. Gates green sequentially:
    `make check-fmt` and `make lint` (ruff clean, interrogate 100%, Pylint
    10.00/10), `make typecheck` (ty clean), `make test` and `make all`
    (66 passed, up from 61), `make audit` (no known vulnerabilities). No
    runtime Markdown changed in this round; the execplan edit was validated
    with `make markdownlint` and `make nixie`. `coderabbit review --agent`
    returned 0 findings (one rate-limit retry with roughly 130 s backoff).
- Dual-review fix round 2 (commit `769c90e`): closed three further blocking
  guard-bypass findings against `tests/test_state_layout_reference.py`, the
  same "anchor too tight" bypass class round 1 addressed, each of which let a
  forbidden recipe report green.
  - (a) No-space shell redirects bypassed `_REDIRECT_RE`, which required `\s+`
    between the `>`/`>>` operator (and `cat >`) and the path. POSIX shells
    treat `>file` and `> file` (and `>>file`, `cat >file`) identically — the
    whitespace is optional — so `echo x >working/state.toml`,
    `>>working/state.toml`, `printf x >working/state.toml`, and
    `cat >working/state.toml <<'EOF'` were copy-pasteable hand-edit recipes the
    guard reported clean. Fixed by allowing `\s*` after the redirect operators
    while keeping the path anchor; `tee` keeps `\s+` because
    `teeworking/state.toml` is a different command, not a redirect.
  - (b) `Path(...).write_bytes(...)` to the state file was not flagged.
    `_LIBRARY_WRITE_TOKENS` enumerated `.write_text(` but not its binary
    sibling, and the bare `.write(` backstop does not contain the
    `.write_bytes(` substring. Binary mode is the natural TOML-write form (the
    historical heredoc and `tomli_w` both use `wb`), so a `write_bytes` recipe
    slipped both. Added `.write_bytes(` to the token set.
  - (c) The fence scanner only matched triple-backtick fences. CommonMark
    equally permits tilde fences and 4+ backtick fences, so a recipe in a
    `~~~python` or four-backtick block passed both `make test` and
    `make markdownlint` (MD048 unenforced). `_FENCE_RE` now matches 3+
    backticks or 3+ tildes and back-references the opening run via `(?P=fence)`
    so the closing marker matches in character and length.
  - Regression coverage: planted rows `shell-redirect-no-space`,
    `shell-append-no-space`, `shell-cat-heredoc-no-space`, `path-write-bytes`,
    `tilde-raw-open-write`, and `quad-backtick-raw-open-write`, plus a negative
    test `test_unrelated_no_space_redirect_not_flagged` proving the path anchor
    holds for `>/tmp/foo`. To stay under the 400-line module cap, several
    multi-line planted recipes were condensed to their minimal write surface
    (the token rule only needs the substrings, so dropped `import` lines and
    shortened payloads do not weaken coverage). Gates green sequentially:
    `make check-fmt`, `make lint` (ruff clean, interrogate 100%, Pylint
    10.00/10), `make typecheck` (ty clean), `make test` and `make all`
    (73 passed, up from 66), `make audit` (no known vulnerabilities). No
    runtime Markdown changed in this round; the execplan edit was validated
    with `make markdownlint` and `make nixie`. `coderabbit review --agent`
    returned 0 findings (one rate-limit retry with roughly 200 s backoff).

## Interfaces and dependencies

No production interface changes; `novel_ralph_skill` is untouched. The new
test-module-private surface in `tests/test_state_layout_reference.py` is:

```python
def find_direct_state_write_recipes(markdown: str) -> list[str]:
    """Return one message per executable fence that writes ``state.toml``."""
```

plus a private fence iterator and the executable-info-string constant set.
These stay inside the test module (no cross-module import) to keep the task
atomic and avoid pre-empting the shared-`conftest` consolidation owned by
roadmap task 1.2.7. The guard uses standard-library only — `pathlib` (already
imported) and `re`. No runtime or dev dependency is added; `make audit` must
stay clean.

## Revision note

- 2026-06-22 (round 2): revised to clear the three blocking points from
  design-review round 1.
  - Blocking 1 (gate-failing commit): merged the former "red tests" and
    "implement" work items into a single red-then-green work item 1 that commits
    only once all gates pass; the red transcript is captured as evidence, never
    committed. Deleted the separate "Add red tests…" commit and the "if your
    gating policy forbids committing red tests" caveat. Added a Decision Log
    entry citing AGENTS.md lines 99 and 108. The plan now has two commits.
  - Blocking 2 (false `text` fence at 212-228): corrected every assertion. Line
    212 is the `## Atomic writes` heading; 214-228 is prose plus a numbered
    list with no fence. Fixed the Risks, Surprises, and Context wording to state
    the atomic-write discipline lives in prose (lines 60-61 and 214-228) and is
    already safe under fence-scoped scanning; rewrote work item 1 test #2 to feed
    a synthetic *prose* fixture explicitly labelled as such, not a non-existent
    fence; enumerated the six real fences with verified line ranges.
  - Blocking 3 (`make all` does not chain audit/markdownlint/nixie): removed the
    "or simply `make all` if it chains them" claim and the "final `make all`"
    shorthand. The validation now states `make all` is
    `build check-fmt lint typecheck test` (Makefile line 28) and runs `make
    audit`, `make markdownlint`, and `make nixie` explicitly and sequentially.
  - Advisories also actioned: pinned the `open(` rule to require a write signal
    and added a read-only negative test (4); reframed the 6.2.3 mitigation as
    defensive, dropping the unverified "shows an example invocation" claim (5);
    path-anchored the redirect rules and added a `> /tmp/foo` negative test (6);
    deleted the contradictory "text pseudocode fence" sentence in Surprises (7).
  - Effect on remaining work: implementation is now two commits, not three; the
    test list gains three negative cases (read-only `open`, unrelated redirect,
    plus the existing `novel-state` and `toml`-fence cases) and the predicate
    spec is unambiguous on `open(` and redirects.

## Addenda (post-merge follow-ups)

Lightweight addendum work items folded back onto this completed task from later
reviews and audits of the state-layout guard. Execute each as a small addendum
pass — no plan or design-review cycle: make the change, run `make all` (plus
`make markdownlint`/`make nixie` for Markdown), `coderabbit review --agent`,
commit, and tick the matching roadmap sub-task on merge. The substantial guard
*extensions* were re-routed to roadmap step 7.3; these four are the small fixes
and hygiene only.

- [x] 1.2.8.1 — Enforce a single code-fence style (MD048) in the markdownlint
  config (from review:1.2.8, low). Add the MD048 rule (backtick-only) and
  normalise any tilde fences repo-wide. Gate with `make markdownlint`.
- [x] 1.2.8.2 — Split `tests/test_state_layout_reference.py` before it breaches
  the 400-line cap (from review:1.2.8, low). Extract the recipe corpus or
  scanner helpers into a small support module (coordinate with the 1.2.7 shared
  conftest). Behaviour-preserving; gate with `make all`.
- [x] 1.2.8.3 — Distinguish the live `state.toml` from its `.new` sibling in the
  guard (from review:1.2.8, medium — a real false-positive bug). `_STATE_FILE`
  matches as a bare substring, so a write-then-rename illustration (design §3.4,
  §5.3) is false-flagged; anchor the live-file match on a word, quote, or
  end-of-line boundary and add a negative test for a `.new`-only
  write-then-rename fence. Gate with `make all`.
- [x] 1.2.8.4 — Reconcile the developers' guide guard section with the merged
  code (from audit:1.2.8, medium). The guide's write-token list omits
  `.write_bytes`/`.writelines` and the executable info-string list omits
  `python3`/`py3`/`pycon`; a one-paragraph edit makes the prose truthful. Gate
  with `make markdownlint` and `make nixie`.
- [ ] 1.2.8.5 — Sweep the residual hyphenated `novel-state` literals in
  `tests/test_state_layout_reference.py` to the `novel state` surface (from
  review:1.2.14, low). The module's docstrings (the `novel-state` mentions at
  the file and method level) and the negative-test fixture fence
  `novel-state set-cursor --chapter 7` still name the retired console-script;
  these sit outside the `skill/novel-ralph/references/` scope of roadmap 1.2.17
  and the production-module-name scope of 1.2.14/1.2.16, so they survive
  untracked. Flip each `novel-state` reference to the spaced `novel state`
  surface, preserving the negative test's intent (an invocation example must
  still not be flagged by the guard). Behaviour-preserving; gate with `make all`
  plus `make markdownlint`/`make nixie`.
