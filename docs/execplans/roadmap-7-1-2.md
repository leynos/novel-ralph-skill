# Implement the per-novel `device-ledger.toml` enforcement (roadmap 7.1.2)

This ExecPlan (execution plan) is a living document. The sections `Constraints`,
`Tolerances`, `Risks`, `Progress`, `Surprises & Discoveries`, `Decision Log`,
and `Outcomes & Retrospective` must be kept up to date as work proceeds.

Status: COMPLETE

## Purpose / big picture

A novel rations its signature devices: a recurring image (a "sternum" motif), a
key phrase ("truth of the thing"), or a bookend line is meant to land a fixed
number of times, in a fixed set of chapters, and nowhere else. The field report
the design draws on names a forgotten ration as the highest-risk manual work —
"a forgotten ration silently breaks the book's discipline"
(`docs/novel-ralph-harness-design.md` §6.3, "Device ledger (resolves Q3)"). v1
ships no enforcement for this: `desloppify` flags prose tics from a rule pack
(`offenders.toml`, `ai-isms.toml`), but it cannot answer "have I spent the
sternum motif more than three times?" or "did the bookend line leak out of
chapter 12?".

After this change a novelist (or the harness) writes a per-novel
`working/device-ledger.toml` naming each rationed device, and runs
`desloppify --ledger working/device-ledger.toml`. The command recomputes every
device's current spend **from the chapter drafts on disk on every run** (so the
ledger cannot drift from the manuscript, design §6.3) and reports,
deterministically, each device that is over its ration: spent past `max_count`,
used outside its `allowed_chapters`, used after `retired_after_chapter`, or
used anywhere other than `reserved_for_chapter`. A device within its ration is
silent. The command **does not edit prose and does not decide whether a device
should be spent** — that judgement stays with the model (design §6.3, ADR-001
`docs/adr-001-deterministic-judgemental-boundary.md`). This resolves open
question Q3 (`docs/terms-of-reference.md`).

You can observe success four ways:

1. `uv run desloppify --ledger working/device-ledger.toml` over a manuscript
   that uses the `sternum` motif four times when `max_count = 3` exits `4` and
   names `sternum` in `result.violations`, reporting `count: 4` against
   `max_count: 3`; over a within-ration manuscript it exits `0`.
2. A device with `allowed_chapters = [1, 3, 8]` that appears in chapter `5`
   exits `4` and names that out-of-ration chapter in the finding; a device with
   `retired_after_chapter = 7` that appears in chapter `9` exits `4`; a device
   with `reserved_for_chapter = 12` that appears in chapter `4` exits `4`.
3. The current counts are recomputed from the chapter drafts every run: editing
   a draft to remove a spend and re-running drops the finding with no ledger
   edit (design §6.3 "recomputing current counts from disk every run").
4. A built-and-installed wheel runs `desloppify --ledger <path>` against a real
   `working/` tree and reports the same finding (the e2e proves the ledger
   enforcement travels in the wheel and works end to end), and `make all`,
   `make markdownlint`, and `make nixie` are all green.

## Scope and explicit non-goals

This task is an **engine addition**, unlike sibling task 7.1.1 (which shipped
data only). The device ledger carries per-device, chapter-aware rationing fields
(`max_count`, `allowed_chapters`, `retired_after_chapter`,
`reserved_for_chapter`) that the existing rule-pack schema
(`novel_ralph_skill/rulepack/schema.py`: `id`/`pattern`/`threshold`/`basis`/
`page_words`) **cannot express**. So this plan adds a new, parallel typed
model, a validating loader, a pure chapter-aware detector, an envelope
projection, and a `desloppify --ledger PATH` mode — mirroring the existing
rulepack package's structure (schema → parse → detect → report) so the two
detection families share shape and house style without sharing a schema.

- In scope: a new `novel_ralph_skill/ledger/` package (typed schema, validating
  parse boundary, pure chapter-aware detect, typed errors) modelled on the
  `rulepack` package; a `--ledger PATH` keyword on the existing `desloppify`
  command that runs ledger enforcement instead of (in v1) a rule-pack scan; an
  envelope projection for the ledger findings; a worked example
  `device-ledger.toml`; unit, example, property, snapshot, and POSIX wheel-e2e
  tests; developers'-guide, users'-guide, design §6.3, terms-of-reference Q3,
  and desloppify-checklist documentation.
- Out of scope (other roadmap items own these; do not touch them): combining a
  rule-pack scan and a ledger scan in one invocation (multi-pack surface, 7.1.7
  family); the per-hit payload-contract decisions 7.1.3/7.1.4/7.1.5 (clean-pass
  slimming, matched-span field, canonical finding projection) — the ledger
  emits its own payload and must NOT pre-empt those decisions for the rule-pack
  findings; the symbolic `--pack ai-isms` selector (7.1.6); any new
  console-script (ADR-005 fixes the surface at five scripts — the ledger is a
  flag on `desloppify`, never a sixth script).

If, while implementing, it emerges that ledger enforcement cannot be expressed
as a `--ledger` mode on `desloppify` without changing the rule-pack scan's
behaviour or envelope, **stop and escalate** (see `Tolerances`): that would be
a scope expansion into the multi-pack surface (7.1.7), not a silent workaround.

## Constraints

Hard invariants that must hold throughout implementation. Violation requires
escalation, not a workaround.

- The command surface stays **five console-scripts** (ADR-005,
  `docs/adr-005-command-surface-five-scripts.md`). Ledger enforcement is a
  `--ledger PATH` keyword on the existing `desloppify` command, never a new
  entry point. No change to `pyproject.toml` `[project.scripts]`.
- Detect-only boundary (ADR-001): the ledger model, loader, detector, and report
  detect and report; they never edit prose, never mutate `state.toml` or any
  draft, and never judge whether a device *should* have been spent. The command
  writes nothing to disk (mirrors `_desloppify.py`'s "writes nothing to disk").
- The current spend count is **recomputed from the chapter drafts on disk on
  every run** (design §6.3). The ledger TOML carries the rationing *rules*
  (`max_count`, the chapter constraints), never a cached count; the count comes
  only from `finditer` over the sourced chapter text, so the ledger cannot
  drift from the manuscript.
- The shared interface contract is unchanged for the existing rule-pack scan
  (design §3.1, §3.2; ADR-003 `docs/adr-003-shared-interface-contract.md`).
  `desloppify` with no `--ledger` behaves exactly as today (same default pack,
  exit codes, envelope). The `--ledger` mode reuses the same four-flag
  contract, the same `CommandOutcome`, and the same exit-code table (`0` clean /
  `4` finding / `2` usage / `3` state/input).
- Ledger device patterns compile under `re.compile` with **no flags** (`(?i)`
  inline only), and detection scans **line by line**, exactly as `detect.py`
  does (`detect.py` module docstring): `.` cannot cross `\n`, so a per-line
  scan keeps `{chapter, line}` exact. A multi-token device must use a bounded
  non-newline window `[^\n]{0,N}?`, never greedy `.*` or `re.DOTALL`.
- The ledger loader splits faults into the same two channels the rulepack loader
  uses: malformed *content* → a typed content error the command maps to exit 2
  (naming the offending device); an absent/unreadable/undecodable ledger *file*
  → a typed file error the command maps to exit 3 (design §3.2; mirrors
  `RulePackError`/`RulePackFileError` in
  `novel_ralph_skill/rulepack/errors.py`).
- No new third-party dependency. Every tool used (`tomllib` stdlib, `re` stdlib,
  `importlib.resources`, `pytest`, `syrupy`, `cuprum` 0.1.0, `hypothesis`, `uv`,
  `cyclopts` 4.18.0) is already locked.
- House style: frozen, slotted, keyword-only dataclasses (mirroring
  `rulepack/schema.py`); parse-to-a-schema-type at the boundary, no raw
  `dict[str, object]` leaking inward; 100% docstring coverage (`interrogate`,
  `pyproject.toml` `[tool.interrogate] fail-under = 100`); module line cap 400
  (`[tool.pylint.main] max-module-lines = 400`); Ruff line-length 88; Markdown
  paragraphs wrapped at 80 columns, code blocks at 120 (AGENTS.md).
- en-GB Oxford spelling ("-ize"/"-yse"/"-our") in all prose, comments,
  docstrings, TOML comments, and commit messages (workflow standing rule;
  `docs/documentation-style-guide.md`), excepting verbatim external-API names.

## Tolerances (exception triggers)

- Scope: if implementing `--ledger` requires editing the rule-pack scan path
  (`detect.py`, `parse.py`, `schema.py`, `_desloppify_report.py`'s
  `report_outcome`/`_finding_payload`) in any way that changes the rule-pack
  finding shape or behaviour, stop and escalate — that is
  7.1.3/7.1.4/7.1.5/7.1.7 territory, not this task.
- Surface: if ledger enforcement appears to need a sixth console-script, or to
  need running a rule pack and the ledger in one invocation, stop and escalate
  (ADR-005 / 7.1.7).
- Schema interpretation: if two device constraints can be set on the same device
  in a way the design §6.3 examples do not disambiguate (e.g. both
  `allowed_chapters` and `reserved_for_chapter` on one device), the
  interpretation materially affects which manuscripts are flagged — this is an
  **ambiguity Tolerance that is pre-tripped**; the Decision Log fixes the
  chosen semantics (see "Constraint combination semantics" below) and a test
  pins each; if a reviewer rejects the chosen semantics, stop and escalate
  rather than guessing a second interpretation.
- File-size: if either the command body (`_desloppify.py`, currently 318 lines)
  or any new module would exceed the 400-line cap, stop and split it (a sibling
  module), do not suppress the cap.
- Dependencies: if any new third-party dependency is required, stop and
  escalate.
- Iterations: if any new test suite still fails after 3 focused attempts, stop
  and escalate.

## Risks

    - Risk: a device pattern over-matches (flags legitimate prose) or
      under-matches, so the ration count is wrong. This is acute because device
      patterns are author-supplied per novel and the design's example uses bare
      single words (`\bsternum\b`, `\bbloom\b`), which fire on every literal use
      of the word, not only the motif use.
      Severity: medium
      Likelihood: medium
      Mitigation: this is inherent to a per-novel author-owned file (the author
      narrows the pattern to the motif), but the developers' guide and the
      worked-example file MUST state the line-by-line, no-semantic-gate counting
      model and that the count is literal `finditer` hits, so an author chooses a
      narrow pattern knowingly. Work Item 5 documents this; Work Item 6's worked
      example uses a collocational pattern where a bare word would be noisy.

    - Risk: the chapter number a device hit is attributed to is wrong, so the
      `allowed_chapters`/`retired_after_chapter`/`reserved_for_chapter` checks
      fire against the wrong chapter. The chapter-aware checks are the whole
      point of the ledger over a flat rule pack.
      Severity: high
      Likelihood: low
      Mitigation: reuse `desloppify`'s existing chapter sourcing
      (`source_chapters` in `_desloppify.py`), which already attributes each
      `ScannedChapter` its one-based `number` from the `[chapters]` manifest and
      reads `manuscript/chapter-NN/draft.md` (the same convention `recount`
      uses). The ledger detector reuses `ScannedChapter` rather than inventing a
      second sourcing path. Work Item 3's unit tests pin the per-chapter
      attribution explicitly (a hit in chapter 5 is attributed to chapter 5), and
      Work Item 4's property test asserts the attributed chapter is always one of
      the scanned chapters' numbers.

    - Risk: enforcing chapter-aware constraints under a `--chapter N` single-
      chapter scan gives a false negative — `retired_after_chapter = 7` cannot be
      evaluated if only chapter 9 is scanned without knowing chapters exist
      before it, and `max_count` across the manuscript cannot be totalled from
      one chapter.
      Severity: high
      Likelihood: high (if `--ledger` is allowed with `--chapter`)
      Mitigation: the ledger is a **whole-manuscript** concern by design (it
      rations across the book). Work Item 2 makes `--ledger` and `--chapter`
      mutually exclusive: combining them is a body-detected usage fault (exit 2),
      mirroring the existing `DesloppifyUsageError` for a bad `--chapter`. The
      Decision Log records this; a test pins the exit-2 rejection. This removes
      the partial-scan ambiguity rather than silently producing a wrong count.

    - Risk: the ledger file does not travel / resolve correctly. Unlike the
      shipped packs, the device ledger is **per-novel user data**, supplied by
      `--ledger PATH` (a filesystem path), not shipped in the wheel — so there is
      NO `importlib.resources` resolver and no packaged default. A reader might
      wrongly model it on `offenders_pack_path`.
      Severity: medium
      Likelihood: medium
      Mitigation: the Decision Log fixes that the ledger has no shipped default
      and no `importlib.resources` resolver: `--ledger` is required to invoke the
      mode and takes a filesystem `pathlib.Path` (exactly as `--pack PATH` takes
      a bespoke path today). An absent file is the exit-3 file channel. The
      worked-example file (Work Item 6) lives under `docs/` or `tests/data/` as a
      reference, NOT under `novel_ralph_skill/` (it is not shipped). The e2e
      writes the ledger into the throwaway `working/` tree.

    - Risk: `_desloppify.py` (318 lines) crosses the 400-line cap when the
      `--ledger` branch and its sourcing/validation land.
      Severity: medium
      Likelihood: medium
      Mitigation: keep the command body thin — the `--ledger` branch dispatches
      to a new `_ledger_scan` helper, and the ledger envelope projection lives in
      the new `novel_ralph_skill/ledger/` package (a `report.py` or in
      `_desloppify_report.py` only if it stays under cap), not inline. Work Item
      2 checks the line count after the branch lands; if over cap, split the
      sourcing/dispatch into a sibling `_desloppify_ledger.py` (mirrors the
      existing `_desloppify` / `_desloppify_report` split).

    - Risk: the ledger mode silently changes the exit-code or envelope contract
      for a normal `desloppify` run.
      Severity: medium
      Likelihood: low
      Mitigation: Work Item 2 adds a regression test that `desloppify` with no
      `--ledger` still scans the default pack and emits the unchanged envelope;
      the existing `tests/test_desloppify_snapshots.py` snapshot of the rule-pack
      envelope stays green untouched (if it churns, the change leaked into the
      rule-pack path — stop and escalate).

## Progress

    - [x] Work Item 1: add the `novel_ralph_skill/ledger/` package — typed
      schema, typed errors, validating parse boundary, and a worked-example
      reference file — modelling the `rulepack` package structure. DONE. Split
      the loader across `parse.py` (313 lines), `_coerce.py` (192 lines,
      ledger-local scalar helpers raising `LedgerError`), and `_fields.py`
      (203 lines, rationing-field validation) to stay under the 400-line cap;
      the worked example lives at
      `tests/data/ledgers/example-device-ledger.toml`.
    - [x] Work Item 2: wire `--ledger PATH` onto the `desloppify` command, mutually
      exclusive with `--chapter`, mapping the two ledger errors to exit 2 / 3,
      and keep the rule-pack path unchanged (regression-pinned). DONE. Added the
      `ledger` keyword to `build_app._scan`, a `_dispatch` helper that rejects
      `--ledger` + `--chapter` as exit 2, and the sibling
      `_desloppify_ledger.py` owning the ledger load + whole-manuscript sourcing
      + fault routing (`_desloppify.py` is 383 lines, under cap). The new
      behavioural tests (`test_ledger_with_chapter_exits_two`,
      `test_absent_ledger_file_exits_three`, `test_malformed_ledger_exits_two`)
      pass; the rule-pack snapshot is untouched.
    - [x] Work Item 3: implement the pure chapter-aware ledger detector and its
      envelope projection; pin every constraint (`max_count`, `allowed_chapters`,
      `retired_after_chapter`, `reserved_for_chapter`) and the recompute-from-disk
      behaviour with unit and example tests. DONE. The detector + projection
      landed in the WI2 commit (see deviation note); WI3 adds
      `tests/test_ledger_detect.py` (13 tests) pinning each constraint's breach
      and clean case, the per-chapter attribution, the `max_count`+window
      pairing, and the recompute-from-disk behaviour. The three window cases are
      parametrised (a typed `_Ration` config keeps the `_device` factory within
      the argument-count gate). A trivial CodeRabbit suggestion to convert the
      builder helpers to fixtures was declined: the sibling template
      `tests/test_rulepack_detect.py` uses module-level builder functions, and
      the parametrize data is built at module load (fixtures cannot supply it).
    - [x] Work Item 4: add Hypothesis property tests for the ledger loader and
      detector invariants (load-and-compile robustness; attributed chapter is
      always a scanned chapter; count equals literal hit total). DONE.
      `tests/test_ledger_properties.py` (5 properties) draws devices from a fixed
      well-formed ration set (no filtering trap) and chapters from a fixed
      chapter-number pool. `python-verification` confirms Hypothesis is the right
      adversary (ordering/range invariants, not contract counter-examples or
      mutation gaps); mutmut was NOT added — `detect_ledger`'s three window
      branches are each pinned by a WI3 breach+clean example, so the branch logic
      is already exercised. The example-ledger path is derived from `__file__`
      (cwd-independent collection).
    - [x] Work Item 5: add a snapshot test pinning the ledger envelope shape, and
      a `desloppify --ledger` behavioural test (exit 4 over-ration, exit 0
      within-ration, exit 2 with `--chapter`, exit 3 absent file). DONE.
      `tests/test_ledger_snapshots.py` pins the over-ration and clean envelope
      shapes with paired semantic assertions; `tests/test_ledger_command.py`
      drives the real app for over-ration (exit 4 naming the device),
      within-ration (exit 0), recompute-from-disk (4→0 on draft edit, no ledger
      edit), each malformed fixture (exit 2), and an undecodable file (exit 3).
      The exit-2 `--ledger`+`--chapter` and absent-file cases were pinned in the
      WI2 commit. Bad-ledger fixtures added under `tests/data/ledgers/`
      (`no-ration`, `two-windows`, `bad-pattern`, `duplicate-id`,
      `non-positive-max-count`, `undecodable`). Test signatures derive data paths
      from `__file__` and write the ledger into the tree's tmp parent to stay
      within the positional-argument gate (no suppression).
    - [x] Work Item 6: prove the ledger enforcement works on an installed wheel
      with a POSIX `slow` e2e mirroring `tests/test_desloppify_e2e.py`. DONE.
      Appended two tests to `tests/test_desloppify_e2e.py` (rather than a separate
      module) to reuse `_build_and_install_desloppify`/`_materialise_working`
      without the cross-module private import six post-merge audits flagged
      (conftest preamble). Over-ration tree exits 4 naming `sternum`;
      `sternum`-free tree exits 0. Exercises `max_count` only (round-1 condition
      2); both tests are `@skipif(os.name != "posix")` + `@timeout(180)`.
    - [x] Work Item 7: document the ledger (developers' guide, users' guide,
      design §6.3 pointer, terms-of-reference Q3 resolved, desloppify checklist).
      DONE. Added the developers' guide subsection "The device ledger and
      per-novel rationing" (closed vocabulary, constraint-combination semantics,
      counting model, two-exit-code split, whole-manuscript `--ledger`, the
      no-floor limitation); a users' guide `--ledger` note and extended exit-code
      table; a design §6.3 pointer recording Q3 resolved; the terms-of-reference
      Q3 marked resolved (roadmap 7.1.2); and a device-rationing pointer in the
      desloppify checklist. `make markdownlint` and `make nixie` pass; also fixed
      four pre-existing markdownlint failures in this ExecPlan and its review
      file (long inline-command lines, an inline-HTML `<id>`).

## Surprises & discoveries

    - WI1: `ruff format` re-expanded `parse.py` past the 400-line cap (487
      lines) once the rationing-field validators were inlined. Split the
      validators into a sibling `_fields.py` (203 lines) so `parse.py` returned
      to 313 lines, mirroring the `rulepack` `parse.py`/`_coerce.py` split. No
      behaviour change; the split is purely the file-size Tolerance honoured.
    - WI1: `make fmt` reflows ~165 unrelated Markdown files (the long-standing
      mdformat-all churn this repo records in dozens of stashes). Stashed that
      churn and kept only the intended Python reformat; `make all` runs
      `check-fmt`, not `fmt`, so the deterministic gate does not touch Markdown.

## Decision log

    - Decision: model the device ledger as a NEW `novel_ralph_skill/ledger/`
      package (schema/parse/detect/errors[/report]) parallel to
      `novel_ralph_skill/rulepack/`, NOT as a rule-pack schema extension.
      Rationale: the design §6.3 device fields (`max_count`, `allowed_chapters`,
      `retired_after_chapter`, `reserved_for_chapter`) are chapter-aware
      rationing constraints the closed v1 rule-pack key vocabulary
      (`id`/`pattern`/`threshold`/`basis`/`page_words`, enforced strictly by
      `parse.py` `_RULE_KEYS`/`_PACK_KEYS`) cannot carry without a schema bump
      and a basis the detector does not understand. A parallel package keeps the
      rule-pack contract frozen (Constraint) while sharing the proven
      schema→parse→detect→report shape and the `ScannedChapter` input type.
      Date/Author: 2026-06-25, planning agent.

    - Decision: ledger enforcement is a `--ledger PATH` keyword on the existing
      `desloppify` command, mutually exclusive with `--chapter`, never a sixth
      console-script.
      Rationale: ADR-005 fixes the surface at five scripts; design §6.3 says "a
      per-novel `device-ledger.toml` that `desloppify` enforces". Mutual
      exclusivity with `--chapter`: the ledger rations *across the manuscript*
      (max_count totals, chapter-window checks), so a single-chapter scan cannot
      compute the ration faithfully (Risk row "partial-scan false negative"). A
      `--ledger` + `--chapter` invocation is a body-detected usage fault (exit
      2), mirroring the existing bad-`--chapter` `DesloppifyUsageError`.
      Date/Author: 2026-06-25, planning agent.

    - Decision: the ledger has NO shipped default and NO `importlib.resources`
      resolver; `--ledger` takes a filesystem `pathlib.Path` and is required to
      enter the mode. The worked-example ledger lives as a reference under
      `docs/`/`tests/data/`, not inside `novel_ralph_skill/` (it is not packaged).
      Rationale: the ledger is per-novel user data (design §6.3 "per-novel"),
      unlike the shipped `offenders.toml`/`ai-isms.toml`. There is nothing to ship
      and nothing to resolve through the package tree. `--pack PATH` already
      proves Cyclopts binds an optional `pathlib.Path | None` keyword
      (`_desloppify.py` `build_app`), so `--ledger` reuses the identical pattern.
      Date/Author: 2026-06-25, planning agent.

    - Decision (constraint combination semantics — pre-tripped ambiguity
      Tolerance): each device may carry at most ONE chapter-window constraint
      among `allowed_chapters`, `retired_after_chapter`, `reserved_for_chapter`;
      `max_count` may co-exist with any one of them. A device combining two
      window constraints is a loader content fault (exit 2), naming the device.
      Within one window constraint the semantics are: `max_count` — total hits
      across the manuscript must be `<= max_count`; `allowed_chapters = [..]` —
      every hit's chapter must be in the set (a hit outside is a violation);
      `retired_after_chapter = N` — no hit in any chapter `> N`;
      `reserved_for_chapter = N` — every hit must be in chapter `N` (a hit
      elsewhere is a violation). A device with none of the four is rejected at
      load (a device with no ration is a no-op the author did not intend).
      Rationale: design §6.3's example sets exactly one window constraint per
      device (sternum: max_count+allowed_chapters; bloom: max_count;
      truth-of-the-thing: retired_after_chapter; stated-theme-bookend:
      reserved_for_chapter), so co-existing windows are undefined by the design;
      rejecting the combination loudly (rather than guessing precedence) honours
      the loud-failure discipline the rule-pack loader established (5.1.1). The
      `max_count`-plus-one-window pairing is the design's own sternum example, so
      it is explicitly allowed.
      Date/Author: 2026-06-25, planning agent.

    - Decision: the ledger reuses `desloppify`'s existing chapter sourcing
      (`source_chapters` → `ScannedChapter`) and the `detect.py` line-by-line,
      no-flags scanning discipline, rather than a second sourcing path.
      Rationale: the chapter-number attribution that the window checks depend on
      is already correct and tested in the rule-pack path (each `ScannedChapter`
      carries its manifest `number`); reusing it removes the Risk "wrong chapter
      attribution" and keeps the per-token/path conventions in one place.
      Date/Author: 2026-06-25, planning agent.

    - Decision (WI1, resolving the open `_coerce` question and round-1 review
      condition 1): add a ledger-local `novel_ralph_skill/ledger/_coerce.py`
      rather than importing the rulepack `_coerce` helpers.
      Rationale: every rulepack helper hard-raises `RulePackError` with
      `"rule '<id>'"` wording; the command routes on the exception *type*, so an
      imported helper would emit the wrong typed error and the wrong device
      naming. Refactoring the rulepack helpers to take an error factory would
      edit the frozen rule-pack loader (a Tolerance trip). The ledger-local copy
      raises `LedgerError` with `"device '<id>'"` wording. The AGENTS.md
      abstraction-reuse sweep was performed: the shared shape is the
      `EnvelopeMessagesError` base (reused) and the schema→parse→detect→report
      structure (mirrored), not the error-typed scalar coercers.
      Date/Author: 2026-06-25, implementing agent.

    - Deviation (WI2/WI3 ordering): the plan splits the detector + projection
      (`detect.py`, `report.py`) into WI3 and has WI2 "complete the dispatch" in
      WI3. To keep the WI2 commit atomic *and* green (no half-wired dispatch
      calling not-yet-existing symbols), `detect.py` and `report.py` landed in
      the WI2 commit so `_desloppify_ledger.ledger_scan` calls real code. WI3
      then adds the detector unit/example tests (`tests/test_ledger_detect.py`)
      that pin every constraint and the recompute-from-disk behaviour. No scope
      change; the modules are unchanged between WI2 and WI3, only the tests are
      added. Rationale: an importable-but-broken intermediate commit violates the
      "gate each commit" discipline more than a single-WI boundary shift.
      Date/Author: 2026-06-25, implementing agent.

## Outcomes & retrospective

    - Delivered all seven work items across seven atomic commits. `desloppify
      --ledger PATH` enforces a per-novel device ledger: over-ration exits 4
      naming the device, within-ration exits 0, malformed content exits 2, an
      undecodable file exits 3, and `--ledger` + `--chapter` exits 2. The count
      is recomputed from disk every run (proven in-process and on an installed
      wheel). The rule-pack scan path, its envelope, and its snapshot are
      unchanged. `make all`, `make markdownlint`, and `make nixie` are green at
      HEAD.
    - Deviation from the WI ordering: the detector (`detect.py`) and projection
      (`report.py`) landed in the WI2 commit rather than WI3, so the command
      wiring could call real code and each commit stayed green; WI3 added the
      detector unit/example tests. Recorded in the Decision Log.
    - The constraint-combination semantics (at most one window per device,
      `max_count` may pair with one, ration-less rejected) held without a
      reviewer challenge; the no-"must-appear"-floor limitation is documented in
      the developers' guide as the highest-value future enhancement.
    - CodeRabbit drove several test-quality improvements: assertion messages on
      every check, a typed `_Ration` config to drop a `too-many-arguments`
      suppression, parametrised window cases, and cwd-independent test-data paths
      derived from `__file__`. Two trivial "convert helpers to fixtures"
      suggestions were declined to stay consistent with the sibling
      `test_rulepack_detect.py` / `test_desloppify_command.py` templates (which
      use module-level builder functions and per-module helper copies).
    - One CodeRabbit run hit a rate limit; exponential backoff (two ~500s waits)
      cleared it within the budget, so no work item was blocked.

## Context and orientation

Read these before starting. They are the source of truth.

- `docs/novel-ralph-harness-design.md` §6.3 "Device ledger (resolves Q3)" (lines
  670-703): the authoritative spec — the four rationing fields, the TOML
  example, "recomputed from disk on every run", "Detection is deterministic;
  the decision to spend a device stays with the model". §6.1 (rule-pack schema,
  the structural template the ledger schema parallels), §4.4 (`desloppify`
  per-hit output), §3.1/§3.2 (envelope and exit codes).
- `docs/terms-of-reference.md` Q3 (the device-ledger open question this task
  resolves; mark it resolved in Work Item 7, citing the developers' guide).
- `docs/adr-001-deterministic-judgemental-boundary.md` (detect-only),
  `docs/adr-003-shared-interface-contract.md` (envelope contract),
  `docs/adr-005-command-surface-five-scripts.md` (no sixth script — the ledger
  is a `desloppify` flag).
- `docs/developers-guide.md` "Rule packs and the loader boundary" (lines
  950-1095): the description of the pack TOML shape, the closed key vocabulary,
  the validating loader, and the two-exit-code fault split. The ledger gets a
  parallel "The device ledger and per-novel rationing" subsection here.
- `docs/users-guide.md` `desloppify` section (lines ~282-316): the `--pack`/
  `--chapter` flags and the exit-code table; the `--ledger` flag and its mutual
  exclusion with `--chapter` are documented here.
- `docs/scripting-standards.md` for cuprum/Cyclopts/pathlib conventions in the
  e2e and any helper.
- AGENTS.md "Python verification and testing" (unit + behavioural + property +
  snapshot + e2e discipline) and "Markdown guidance".

Key code, by full path:

- `novel_ralph_skill/rulepack/schema.py` — the frozen/slotted/kw-only dataclass
  house style the ledger schema mirrors (`RuleBasis`, `Rule`, `RulePack`).
- `novel_ralph_skill/rulepack/parse.py` and `_coerce.py` — the validating
  boundary the ledger loader mirrors (`parse_rulepack`/`load_rulepack`; the
  `_where`/`_require*`/`_reject_unknown_keys` scalar helpers). The ledger
  loader may import the schema-agnostic `_coerce` helpers, or copy them into a
  ledger `_coerce` if the `rule_id` naming does not fit a `device_id` — decide
  in WI1.
- `novel_ralph_skill/rulepack/errors.py` — `RulePackError`/`RulePackFileError`,
  both subclassing `EnvelopeMessagesError`; the ledger errors mirror this
  exactly (`LedgerError`/`LedgerFileError`).
- `novel_ralph_skill/rulepack/detect.py` — the pure line-by-line detector and
  its
  `ScannedChapter`/`LineHit`/`RuleFinding`/`DetectionReport` shapes; the ledger
  detector reuses `ScannedChapter` and mirrors the per-line `finditer` scan.
- `novel_ralph_skill/commands/_desloppify.py` — the command body;
  `source_chapters`
  (chapter sourcing the ledger reuses), `_select_chapters`,
  `DesloppifyUsageError` (the exit-2 body fault the ledger reuses), and
  `build_app` (where `--ledger` is added to the `_scan` signature). Currently
  318 lines — watch the cap.
- `novel_ralph_skill/commands/_desloppify_report.py` — the rule-pack envelope
  projection and the shipped-pack resolvers; the ledger projection lives here
  only if the file stays under 400 lines, else in the ledger package.
- `novel_ralph_skill/state/schema.py` `ChapterEntry` (the `[chapters]` manifest
  entry carrying `number`) — the source of the chapter numbers the windows
  check.
- `tests/test_offenders_pack.py` (pack-validation template for WI3's example
  suite), `tests/test_rulepack_properties.py` (Hypothesis template for WI4),
  `tests/test_desloppify_command.py` (in-process command template for WI5),
  `tests/test_desloppify_e2e.py` (wheel-e2e template for WI6),
  `tests/test_desloppify_snapshots.py` (envelope snapshot template for WI5),
  `tests/conftest.py` (`single_program_catalogue`, `venv_scripts_dir`),
  `tests/corpus_fixtures.py` (`baseline_tree`).

Terms defined:

- *Device ledger*: a per-novel TOML file naming each rationed narrative device
  and its ration (design §6.3). Each `[[device]]` names an `id`, a regex
  `pattern`, and exactly one of `max_count` / `allowed_chapters` /
  `retired_after_chapter` / `reserved_for_chapter` (with `max_count` optionally
  pairing with one window constraint).
- *Ration*: the limit a device must stay within — a maximum count, an allowed
  chapter set, a retirement boundary, or a reservation to one chapter.
- *Spend*: one literal `finditer` hit of a device's pattern in a chapter draft.
  The current spend is recomputed from disk every run (design §6.3).
- *Window constraint*: one of `allowed_chapters` / `retired_after_chapter` /
  `reserved_for_chapter`, all chapter-aware (depend on which chapter a hit is
  in).

## Verified external facts (do not re-derive)

- cuprum is locked at `0.1.0` (`uv.lock` lines 113-114). It exposes
  `cuprum.sh.make(program, catalogue=...)`, `cuprum.program.Program(path)`,
  `cuprum.sh.ExecutionContext(cwd=...)`, and `.run_sync(context=, capture=)`;
  `cuprum.catalogue.ProgramCatalogue.lookup` raises `UnknownProgramError` for
  any unregistered program (verified against
  `/data/leynos/Projects/cuprum/cuprum/catalogue.py` `UnknownProgramError`
  (line 28) / `lookup` (line 79), and `cuprum/sh.py` `make` (line 528) /
  `run_sync` (lines 441, 509) / `ExecutionContext` (line 169)). The wheel e2e
  must register the absolute installed `desloppify` path through the
  `single_program_catalogue` fixture before running it — there is no
  allowlist-bypass API; this is exactly the working pattern in
  `tests/test_desloppify_e2e.py` lines 64-118.
- Cyclopts is locked at `4.18.0` (`uv.lock` lines 137-138). An optional keyword
  bound to `pathlib.Path | None = None` is already proven by the live `--pack`
  flag (`_desloppify.py` `build_app`'s `_scan` signature:
  `pack: pathlib.Path | None = None`), so
  `--ledger: pathlib.Path | None = None` reuses the identical, in-repo-tested
  binding — no Cyclopts change is needed. (Cyclopts binds keyword-only
  parameters as `--name` options; confirmed against the Cyclopts API reference,
  cyclopts.readthedocs.io, and more authoritatively by the existing `--pack`/
  `--chapter` keywords already exercised in `tests/test_desloppify_command.py`.)
- `pytest-timeout` is locked at `2.4.0` (`uv.lock` lines 603-605) and supports a
  per-test `@pytest.mark.timeout(N)` override that supersedes the project
  default under `pytest-xdist`; `tests/test_desloppify_e2e.py` lines 93/130
  already use `@pytest.mark.timeout(180)` for the wheel e2e, so WI6 reuses that
  proven override rather than asserting it afresh.
- Hatch wheel default file selection ships every file under
  `packages = ["novel_ralph_skill"]` recursively; the ledger adds files under
  `novel_ralph_skill/ledger/` (a package with an `__init__.py`), which travel
  by the same default mechanism the packs already use — but note the
  worked-example `device-ledger.toml` is **not** placed there (it is user data,
  not shipped), so no build-config change and no packaged-resource resolver is
  needed.

## Plan of work

Seven ordered, independently committable work items. Each ends with its own
validation; do not advance if validation fails. Tests are written **red first**
where they assert new behaviour, then made green. Run everything from the
worktree root `/data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-7-1-2`.

### Work Item 1 — the `novel_ralph_skill/ledger/` package (schema, errors, loader)

Create the package mirroring `novel_ralph_skill/rulepack/`:

- `novel_ralph_skill/ledger/__init__.py` — re-exports the public surface
  (`Device`, `DeviceLedger`, `load_ledger`, `parse_ledger`, `LedgerError`,
  `LedgerFileError`), mirroring `rulepack/__init__.py`.
- `novel_ralph_skill/ledger/schema.py` — frozen/slotted/kw-only dataclasses
  mirroring `rulepack/schema.py`:
  - `LEDGER_SCHEMA_VERSION: int = 1`.
  - `Device` with `id: str`, `pattern: str`, `compiled: re.Pattern[str]`, and
    the
    four optional rationing fields `max_count: int | None`,
    `allowed_chapters: tuple[int, ...] | None`,
    `retired_after_chapter: int | None`, `reserved_for_chapter: int | None`.
    (TOML arrays coerced to tuples at the boundary, as the rulepack does.)
  - `DeviceLedger` with `schema_version: int` and `devices: tuple[Device, ...]`.
    (Per design §6.3 the example carries only `schema_version` and `[[device]]`
    tables — no `pack` name; do not invent one.)
- `novel_ralph_skill/ledger/errors.py` — `LedgerError(EnvelopeMessagesError)`
  (content fault, carries the offending `device_id`, maps to exit 2) and
  `LedgerFileError(EnvelopeMessagesError)` (file fault, maps to exit 3),
  mirroring `rulepack/errors.py`.
- `novel_ralph_skill/ledger/parse.py` — the validating boundary mirroring
  `rulepack/parse.py`: `parse_ledger(mapping) -> DeviceLedger` (pure) and
  `load_ledger(path: Traversable) -> DeviceLedger` (the `tomllib` file
  convenience). It must:
  - Reject unknown top-level keys (only `schema_version`, `device`) and unknown
    `[[device]]` keys (only `id`, `pattern`, `max_count`, `allowed_chapters`,
    `retired_after_chapter`, `reserved_for_chapter`), naming the device.
  - Require `schema_version == 1`, a non-empty `device` array, a string `id`
    (unique across devices), and a compilable `pattern` (`re.compile`, no flags)
    — all loud failures naming the device, as the rulepack loader does.
  - Enforce the **constraint-combination semantics** (Decision Log): a device
    must carry at least one of the four rationing fields; at most one of the
    three window constraints; `max_count` (when present) is a positive integer;
    `allowed_chapters` is a non-empty array of positive ints; `retired_after_
    chapter`/`reserved_for_chapter` are positive ints. Any violation is a
    `LedgerError` naming the device.
  - Decide in this WI whether to import the rulepack `_coerce` helpers
    (`_require`, `_require_int`, `_require_str`, `_reject_unknown_keys`, `_where`)
    or to add a ledger-local `_coerce.py` (if `_where`'s "rule" wording does not
    fit "device"). Record the decision and the AGENTS.md abstraction-reuse sweep
    in the Decision Log.

Also add the worked-example reference `device-ledger.toml` under `tests/data/`
(e.g. `tests/data/ledgers/example-device-ledger.toml`) transcribing the design
§6.3 example (sternum, bloom, truth-of-the-thing, stated-theme-bookend), with a
header comment stating the no-flags/line-by-line counting model. (A second,
under `docs/` for the users' guide, is added in WI7.)

Validation:

- A `uv run python -c` import of `load_ledger` from
  `novel_ralph_skill.ledger` succeeds.
- A `uv run python -c` load of
  `tests/data/ledgers/example-device-ledger.toml` through `load_ledger`
  prints the device count (see "Concrete steps" for the exact invocation).
- `make all` green.

Docs to read: design §6.1 (schema template), §6.3 (the device fields);
developers' guide "Rule packs and the loader boundary"; `rulepack/schema.py`,
`rulepack/parse.py`, `rulepack/_coerce.py`, `rulepack/errors.py` as templates.
Skills to load: `python-router` → `python-data-shapes` (the frozen-dataclass
boundary shape), `python-types-and-apis` (the `Traversable` loader signature
and the `X | None` optional fields), `python-errors-and-logging` (the
typed-error hierarchy and `raise … from …`).

### Work Item 2 — wire `--ledger PATH` onto `desloppify` (mode dispatch + fault routing)

Add the `--ledger` keyword to `_desloppify.py` `build_app`'s `_scan` body
(`ledger: pathlib.Path | None = None`, mirroring `--pack`), and dispatch:

- When `--ledger` is given, run the ledger mode (the detector + projection land
  in WI3); when absent, run the existing rule-pack scan unchanged.
- `--ledger` with `--chapter` is a body-detected usage fault: raise
  `DesloppifyUsageError` (exit 2), reusing the existing `_scan_or_usage`
  adapter. Record the rationale (whole-manuscript rationing) in a comment
  citing the Decision Log.
- Map the two ledger loader errors locally, exactly as the rule-pack errors are
  mapped in `_desloppify`: `LedgerError` → exit-2 `CommandOutcome`;
  `LedgerFileError` → re-raise as `StateInputError` (exit 3). Keep the
  ledger→contract coupling out of the shared `run` wrapper (mirrors the
  existing rulepack handling).
- Source the chapters with the **existing** `source_chapters(None)` (whole
  manuscript), reusing the proven chapter-number attribution.

If adding the branch pushes `_desloppify.py` past 400 lines, split the ledger
sourcing/dispatch into a sibling
`novel_ralph_skill/commands/_desloppify_ledger.py` (mirrors the `_desloppify`/
`_desloppify_report` split) and keep the body thin.

Add a **regression** test asserting `desloppify` with no `--ledger` is
unchanged (default pack scanned, same envelope), and that the existing
`tests/test_desloppify_snapshots.py` rule-pack snapshot is untouched.

Validation:

- `uv run pytest` over `tests/test_desloppify_command.py` and
  `tests/test_desloppify_snapshots.py` passes (the rule-pack path is unchanged;
  the new exit-2 `--ledger` + `--chapter` rejection test passes — write it red
  first).
- `make all` green.

Docs to read: `_desloppify.py` (`build_app`, `_scan_or_usage`, `_desloppify`'s
error mapping, `DesloppifyUsageError`); design §3.2 (exit-code routing);
ADR-003. Skills to load: `python-router` → `python-errors-and-logging` (the
exit-channel mapping and exception translation), `domain-cli-and-daemons` (the
command lifecycle and operator-facing fault routing), `python-testing` (the
regression pin).

### Work Item 3 — the pure chapter-aware ledger detector and envelope projection

Add `novel_ralph_skill/ledger/detect.py` (pure, mirroring `rulepack/detect.py`):

- Reuse `ScannedChapter` from `rulepack.detect` (import it) as the input type,
  so
  chapter sourcing is shared and the chapter-number attribution is identical.
- A `DeviceFinding` (frozen/slotted/kw-only) carrying `device_id`, `pattern`,
  `count`, the per-hit `lines: tuple[LineHit, ...]` (reuse `LineHit`), the
  evaluated ration (which constraint, its bound), and `passed: bool` plus the
  specific offending chapters for a window violation (so the report can name
  *which* chapter leaked).
- A `LedgerReport` (frozen/slotted/kw-only) carrying `findings` and `passed`.
- `detect_ledger(ledger, chapters) -> LedgerReport`: for each device, scan every
  chapter line by line (`finditer`, no flags — `.` cannot cross `\n`), tally
  the total count and the per-(chapter, line) hits, then evaluate the device's
  constraint:
  - `max_count`: `passed = count <= max_count`.
  - `allowed_chapters`: `passed` iff every hit chapter is in the set; the
    offending
    chapters are the hit chapters outside the set.
  - `retired_after_chapter = N`: `passed` iff no hit chapter `> N`; offenders
    are
    the hit chapters `> N`.
  - `reserved_for_chapter = N`: `passed` iff every hit chapter `== N`; offenders
    are the hit chapters `!= N`.
  - `max_count` paired with one window constraint: `passed` iff both hold.

Add the envelope projection (in `novel_ralph_skill/ledger/report.py`, or in
`_desloppify_report.py` only if it stays under 400 lines):
`ledger_report_outcome(report) -> CommandOutcome` — exit `0` clean / exit `4`
on any over-ration device; `result` carries `violations` (the offending
`device_id` list) and per-device `findings` (id, pattern, count, the ration
kind and bound, the offending chapters, `passed`, and the `{chapter, line}`
hits); `messages` carries one human line per over-ration device naming the
breach (e.g. "sternum spent 4 times (max 3)", "truth-of-the-thing used in
chapter 9 after retirement chapter 7"). This projection is the ledger's own
payload and MUST NOT reuse or alter the rule-pack `_finding_payload`
(Constraint: do not pre-empt 7.1.3/7.1.4/7.1.5).

Then complete the WI2 dispatch to call `detect_ledger` and
`ledger_report_outcome`.

Unit/example tests (`tests/test_ledger_detect.py`, mirroring
`tests/test_rulepack_detect.py`): one test per constraint kind asserting the
breach and the clean case; explicit per-chapter attribution (a hit in chapter 5
is attributed to chapter 5); the `max_count`+window pairing; the
recompute-from-disk behaviour expressed as: given two chapter texts, the count
equals the literal total `finditer` hits across them (so removing a spend
lowers the count). Drive `detect_ledger` directly with hand-built
`ScannedChapter`s (pure, no filesystem).

Validation:

- `uv run pytest tests/test_ledger_detect.py -q` passes (each new constraint
  test
  fails before the detector branch exists, passes after).
- `make all` green.

Docs to read: design §6.3 (the four constraints' meaning); `rulepack/detect.py`
(the line-by-line scan and finding-shape template); `_desloppify_report.py`
(the projection template). Skills to load: `python-router` →
`python-iterators-and-generators` (the per-line `finditer` aggregation),
`python-data-shapes` (the finding/report dataclasses), `python-testing`
(per-constraint parametrization).

### Work Item 4 — Hypothesis property tests for the ledger

Add `tests/test_ledger_properties.py`, mirroring
`tests/test_rulepack_properties.py`:

- Loader robustness: for any permutation of the example ledger's devices fed
  through `parse_ledger`, the ledger loads and every pattern compiles (draw
  from the loaded device list — avoid the filtering trap).
- Loader invariants restated as properties: every device carries at least one
  rationing field and at most one window constraint; every present `max_count`/
  `retired_after_chapter`/`reserved_for_chapter` is positive; every
  `allowed_chapters` is a non-empty tuple of positive ints.
- Detector invariant: for `ScannedChapter`s synthesised from a strategy over the
  scanned chapters' numbers and device-bearing/clean lines, every `LineHit`'s
  `chapter` is one of the scanned chapters' numbers, and each `DeviceFinding`'s
  `count` equals the total number of its `lines` (count cannot drift from the
  per-hit list).

Use the `hypothesis` skill to keep strategies inside data the ledger/chapters
actually contain (no arbitrary-regex synthesis). Confirm with
`python-verification` that Hypothesis (not CrossHair/mutmut) is the right
adversary here: these are ordering/range invariants over loader and detector
inputs, not contract counter-examples or mutation gaps. Do NOT add mutmut unless
`python-verification` shows the detector's branch logic warrants it; if it
does, record that and scope a focused mutmut run on `detect_ledger`'s
constraint evaluation only.

Validation:

- `uv run pytest tests/test_ledger_properties.py -q` passes.
- `make all` green.

Docs to read: `tests/test_rulepack_properties.py`; AGENTS.md property-test
rule. Skills to load: `python-router` → `python-verification` (adversary
selection), then `hypothesis` (strategy design, the filtering trap, drawing
from loaded data); load `mutmut` only if verification selects it for
`detect_ledger`.

### Work Item 5 — envelope snapshot + `desloppify --ledger` behavioural tests

Two additions:

1. A snapshot test (`tests/test_ledger_snapshots.py`, mirroring
   `tests/test_desloppify_snapshots.py`) pinning the ledger envelope shape for
   a small over-ration case and a clean case. Redact/normalise nothing
   nondeterministic (the ledger envelope is deterministic), and pair the
   snapshot with semantic assertions (exit code, `violations` membership) so
   the snapshot pins the *shape* while the assertions pin the *behaviour*
   (AGENTS.md snapshot discipline).
2. Behavioural tests (fast, in-process, mirroring
   `tests/test_desloppify_command.py`):
   - `desloppify --ledger <path>` over a `working/` tree that over-spends a
     device exits `4` and names it in `result.violations`.
   - the within-ration tree exits `0` with empty `violations`.
   - `--ledger` with `--chapter N` exits `2` (the WI2 usage fault).
   - `--ledger <absent path>` exits `3` (the file channel).
   - a malformed ledger (`tests/data/ledgers/` bad-fixtures mirroring
     `tests/data/rulepacks/`) exits `2` naming the offending device.
   Drive them through the real `desloppify` app via the shared `run` wrapper
   (`monkeypatch.chdir` into a materialised tree, `capsys` for the envelope),
   exactly as `test_desloppify_command.py` does.

Add the bad-ledger fixtures under `tests/data/ledgers/` (e.g.
`two-windows.toml`, `no-ration.toml`, `bad-pattern.toml`, `duplicate-id.toml`,
`non-positive- max-count.toml`, `undecodable.toml`) mirroring the
`tests/data/rulepacks/` set, each pinning one loader fault.

Validation:

- `uv run pytest` over `tests/test_ledger_snapshots.py` and
  `tests/test_desloppify_command.py` passes; new snapshots reviewed and
  committed.
- `make all` green.

Docs to read: AGENTS.md "Python verification and testing" (snapshot discipline);
`tests/test_desloppify_snapshots.py`, `tests/test_desloppify_command.py`,
`tests/data/rulepacks/` as the bad-fixture template. Skills to load:
`python-router` → `python-testing` (syrupy snapshots, marks, in-process command
tests).

### Work Item 6 — prove ledger enforcement travels in the wheel (POSIX e2e)

Add a POSIX-only, `slow`-marked wheel e2e (in `tests/test_ledger_e2e.py` or
appended to `tests/test_desloppify_e2e.py`), mirroring
`test_installed_desloppify_flags_offender`:

- Build the wheel, install into a throwaway venv, materialise a `working/` tree
  via `baseline_tree`, write a device-bearing draft and a `device-ledger.toml`
  into the tree, and run the installed
  `desloppify --ledger <tree>/device-ledger.toml` through a
  `single_program_catalogue` that registers the absolute installed script path
  (the cuprum allowlist gate). Assert exit `4` and the device in
  `result.violations`; assert a within-ration tree exits `0`.
- `@pytest.mark.skipif(os.name != "posix", reason=… ADR-006)` and
  `@pytest.mark.timeout(180)` (the proven `pytest-timeout` override).

This is the defence of the "ledger does not work after install" risk: it proves
`desloppify --ledger` resolves a filesystem ledger and enforces it end to end
on a real install — note the ledger is read from `--ledger PATH`, NOT from the
package tree, so this proves the *mode* travels (the command code), not a
packaged resource.

Validation:

- `uv run pytest -m slow -q` runs the e2e on POSIX and passes; off POSIX it is
  skipped with the ADR-006 reason.
- `make all` green (the slow e2e runs under `make test`).

Docs to read: `tests/test_desloppify_e2e.py`; ADR-006
(`docs/adr-006-console-scripts-e2e-posix-policy.md`);
`docs/scripting-standards.md` (cuprum catalogue allowlisting);
`tests/conftest.py`, `tests/corpus_fixtures.py`. Skills to load:
`python-router` → `python-testing` (e2e/marks), `domain-cli-and-daemons`
(subprocess/console-script lifecycle).

### Work Item 7 — document the device ledger; resolve Q3

Prose-only, the Q3 resolution. Edits:

- `docs/developers-guide.md`: add a "The device ledger and per-novel rationing"
  subsection beside "Rule packs and the loader boundary". State: the device
  ledger is per-novel user data (not shipped), selected with
  `desloppify --ledger PATH`; the TOML shape (`schema_version`, `[[device]]`
  with `id`/`pattern` and the four rationing fields); the closed key vocabulary
  and the constraint- combination semantics (at most one window constraint;
  `max_count` may pair with one window; a device with no ration is rejected);
  the line-by-line, no-flags, no-semantic-gate counting model and that the
  count is recomputed from disk every run; the two-exit-code fault split; and
  that `--ledger` is whole-manuscript (mutually exclusive with `--chapter`).
  Cite design §6.3 and ADR-001/003/005.
- `docs/users-guide.md` `desloppify` section: a note that `--ledger PATH`
  enforces a per-novel device ledger, that it scans the whole manuscript and so
  cannot be combined with `--chapter`, and the exit-code meaning (`4` over a
  ration, `2` ledger content malformed or `--ledger`+`--chapter`, `3` ledger
  file absent/unreadable).
- `docs/novel-ralph-harness-design.md` §6.3: a sentence pointing at the
  developers' guide for the concrete enforcement and constraint semantics, and
  recording that Q3 is resolved.
- `docs/terms-of-reference.md` Q3: mark resolved, citing the developers' guide
  section.
- `skill/novel-ralph/references/desloppify-checklist.md`: a pointer that device
  rationing is now enforceable via `desloppify --ledger device-ledger.toml`,
  where the ledger lives (per-novel, in `working/`), and the constraint kinds.

Validation:

- `make markdownlint` passes on every edited Markdown file.
- `make nixie` passes (no Mermaid added; run per the workflow rule).
- `make fmt` reflows prose to 80 columns; re-run `make markdownlint` after.
- `make all` green.

Docs to read: AGENTS.md "Markdown guidance" and "Project documentation";
`docs/documentation-style-guide.md`; `docs/terms-of-reference.md` Q3; the
developers' guide ai-isms subsection (the structural template for the new
subsection). Skills to load: `en-gb-oxendict` (Oxford spelling on the new
prose).

## Concrete steps

Run everything from the worktree root
`/data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-7-1-2`.

1. Confirm the branch and clean tree:

        $ git branch --show
        roadmap-7-1-2
        $ git status --porcelain   # expect empty before starting

2. Work Item 1: add the `ledger/` package and the example fixture. Verify it
   loads:

        $ uv run python -c "$(printf '%s\n' \
            'import pathlib' \
            'from novel_ralph_skill.ledger import load_ledger' \
            'l = load_ledger(pathlib.Path(' \
            '  "tests/data/ledgers/example-device-ledger.toml"))' \
            'print(l.schema_version, len(l.devices))')"
        1 <N>

   Then `make all`; commit (gate first).

3. Work Item 2: wire `--ledger` and the fault routing; add the regression and
   `--ledger`+`--chapter` exit-2 tests (red first):

        $ uv run pytest tests/test_desloppify_command.py \
            tests/test_desloppify_snapshots.py -q
        … passed

   Then `make all`; commit.

4. Work Item 3: add the detector, projection, and unit tests:

        $ uv run pytest tests/test_ledger_detect.py -q
        … passed

   Then `make all`; commit.

5. Work Item 4: add the property tests:

        $ uv run pytest tests/test_ledger_properties.py -q
        … passed

   Then `make all`; commit.

6. Work Item 5: add the snapshot and behavioural tests and the bad-ledger
   fixtures:

        $ uv run pytest tests/test_ledger_snapshots.py \
            tests/test_desloppify_command.py -q
        … passed

   Review and accept the new snapshots; then `make all`; commit.

7. Work Item 6: add the POSIX wheel e2e:

        $ uv run pytest -m slow -q
        … passed   (or skipped off POSIX)

   Then `make all`; commit.

8. Work Item 7: edit the docs and skill reference:

        $ make markdownlint && make nixie && make all
        # all three gates exit 0

   Commit.

Each commit is gated by `make all` per the workflow standing rule; commit only
when the user has approved the plan and asked to proceed.

## Validation and acceptance

Quality criteria (what "done" means):

- Tests: the ledger loader, detector, property, snapshot, behavioural, and POSIX
  e2e suites pass; `desloppify --ledger` exits `4` over an over-ration device
  and `0` within ration; `--ledger`+`--chapter` exits `2`; an absent ledger
  file exits `3`; a malformed ledger exits `2` naming the device. Each new test
  is red before the implementing code lands and green after. The rule-pack
  path's existing tests and snapshot stay green untouched.
- Lint/typecheck: `make all` (build, check-fmt, lint, typecheck, test) green —
  Ruff, `interrogate` 100%, Pylint, `ty`. No module over 400 lines.
- Docs: `make markdownlint` and `make nixie` pass on every edited Markdown file.
- en-GB Oxford spelling throughout new prose, comments, and TOML comments.

Quality method (how we check):

- Local: `make all`; for the doc work item also `make markdownlint` and
  `make nixie`. The same gates run in CI (`.github/workflows/ci.yml`).
- Behavioural acceptance: in a `working/` tree whose drafts use a `sternum`
  device four times under `max_count = 3`,
  `uv run desloppify --ledger working/device-ledger.toml` exits `4` and lists
  `sternum` in `result.violations`; removing one use and re-running drops
  `sternum` and exits `0`, proving the count is recomputed from disk.

## Idempotence and recovery

- Adding the `ledger/` package, tests, and fixtures is additive; re-running any
  work item is safe. The example and bad-ledger fixtures are overwritten
  wholesale on re-edit; no migration.
- The `--ledger` mode is detect-only (ADR-001): no `working/` tree,
  `state.toml`,
  or draft is mutated by any step; the e2e materialises throwaway trees under
  `tmp_path`, which pytest discards.
- The wheel e2e builds into a `tmp_path` venv/wheel dir pytest discards;
  re-running rebuilds cleanly. If a build fails mid-run, delete the `tmp_path`
  and re-run.
- If a commit's gate fails, fix forward on the same work item; do not advance.

## Interfaces and dependencies

- New package `novel_ralph_skill/ledger/`:
  - `schema.py`: `LEDGER_SCHEMA_VERSION: int`; frozen/slotted/kw-only `Device`
    (`id`, `pattern`, `compiled`, `max_count`, `allowed_chapters`,
    `retired_after_chapter`, `reserved_for_chapter`) and `DeviceLedger`
    (`schema_version`, `devices: tuple[Device, ...]`).
  - `parse.py`:
    `parse_ledger(mapping: cabc.Mapping[str, object]) -> DeviceLedger`
    (pure validating boundary) and `load_ledger(path: Traversable) ->
    DeviceLedger` (`tomllib` file convenience).
  - `errors.py`: `LedgerError(EnvelopeMessagesError)` (exit 2, carries
    `device_id`) and `LedgerFileError(EnvelopeMessagesError)` (exit 3).
  - `detect.py`: `detect_ledger(ledger: DeviceLedger, chapters:
    cabc.Sequence[ScannedChapter]) -> LedgerReport`; `DeviceFinding`,
    `LedgerReport` (frozen/slotted/kw-only). Reuses `ScannedChapter`/`LineHit`
    from `novel_ralph_skill.rulepack.detect`.
  - `report.py` (or a helper in `_desloppify_report.py` under cap):
    `ledger_report_outcome(report: LedgerReport) -> CommandOutcome`.
- Modified `novel_ralph_skill/commands/_desloppify.py`: `build_app`'s `_scan`
  body gains `ledger: pathlib.Path | None = None`; a dispatch to the ledger
  mode when set; `--ledger`+`--chapter` raises `DesloppifyUsageError`;
  `LedgerError`/ `LedgerFileError` mapped to exit 2 / 3 locally (mirrors the
  rulepack handling). If over the 400-line cap, the ledger sourcing/dispatch
  moves to a new `novel_ralph_skill/commands/_desloppify_ledger.py`.
- Reused, unchanged: `novel_ralph_skill.commands._desloppify.source_chapters`;
  `novel_ralph_skill.rulepack.detect.{ScannedChapter, LineHit}`; the
  `desloppify` Cyclopts app and the shared `run`/`CommandOutcome` contract; the
  test fixtures `baseline_tree`, `single_program_catalogue`,
  `venv_scripts_dir`. The rule-pack scan path, its envelope, exit codes, and
  snapshots are unchanged.
- Dependencies: no new third-party dependency. `tomllib`/`re`/
  `importlib.resources`
  (stdlib), `pytest`, `syrupy`, `cuprum` 0.1.0, `hypothesis`, `cyclopts` 4.18.0,
  `pytest-timeout` 2.4.0, `uv` are already locked.

## Revision note

- 2026-06-25: initial DRAFT. Decomposed roadmap 7.1.2 into seven ordered work
  items (ledger package + loader, `--ledger` command wiring + fault routing,
  chapter-aware detector + projection, Hypothesis properties, snapshot +
  behavioural tests, POSIX wheel e2e, cadence/Q3 docs). Pinned every external
  behaviour: cuprum 0.1.0 catalogue/run APIs against the cuprum source
  (`catalogue.py` `UnknownProgramError`/`lookup`, `sh.py` `make`/`run_sync`/
  `ExecutionContext`); Cyclopts 4.18.0 optional `pathlib.Path | None` keyword
  against the live in-repo `--pack` flag and the Cyclopts API reference;
  `pytest-timeout` 2.4.0 per-test override against the in-repo e2e proof. Fixed
  the chosen mechanism rather than offering a menu: a NEW
  `novel_ralph_skill/ ledger/` package (the rule-pack schema cannot carry the
  chapter-aware rationing fields), `--ledger` as a flag on `desloppify`
  (ADR-005 forbids a sixth script), whole-manuscript-only (mutually exclusive
  with `--chapter`, removing the partial-scan ambiguity), no shipped default /
  no `importlib.resources` resolver (the ledger is per-novel user data), and
  the constraint-combination semantics fixed in the Decision Log (at most one
  window constraint per device, `max_count` may pair with one window, a
  ration-less device rejected) with the ambiguity Tolerance pre-tripped.
