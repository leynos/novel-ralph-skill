# Implement `desloppify` detection over the §6 offender table

This ExecPlan (execution plan) is a living document. The sections `Constraints`,
`Tolerances`, `Risks`, `Progress`, `Surprises & Discoveries`, `Decision Log`,
and `Outcomes & Retrospective` must be kept up to date as work proceeds.

Status: DRAFT (round 4 — revised after design review; fix round 1 applied after
dual review)

## Purpose / big picture

After this change, a user (the Ralph harness or a person) can run the
`desloppify` console-script against a `working/` tree and get a structured,
per-rule report of prose tics — the §6 high-frequency-offender table — without
any editing and without any improvised `grep`. The command reads a versioned
rule pack (the first such pack, shipped with the package), scans either one
chapter or the whole manuscript, and emits the shared JSON envelope. Its exit
code alone distinguishes the three outcomes the harness branches on: `0` for a
clean pass, `4` when one or more rules exceed threshold (an actionable finding
the agent must adjudicate), and `2` for a usage error (a bad invocation or a
malformed rule pack).

You can observe success three ways:

- `desloppify` over clean prose prints `{"command":"desloppify",…,"ok":true,…}`
  and exits `0`.
- `desloppify` over a manuscript with a tic past threshold prints `ok:false`,
  names the offending rule and its count in `result`, and exits `4`.
- `desloppify --chapter 99` (no such chapter) or a malformed pack exits `2`,
  and a missing/unreadable pack file or absent `working/` exits `3` — each
  distinguishable without parsing the JSON.

This is roadmap task 5.1.2. It builds directly on the rule-pack loader and
schema delivered by task 5.1.1 (`novel_ralph_skill.rulepack`: `load_rulepack`,
`parse_rulepack`, `RulePack`, `Rule`, `RuleBasis`, `RulePackError`,
`RulePackFileError`). It implements design §4.4 (the `desloppify` contract) and
§6.1 (the rule-pack schema), and is verified per design §9 (snapshot of the
envelope plus boundary examples; no property-based or behavioural suite —
`desloppify` is a pure aggregation).

## Constraints

Hard invariants that must hold throughout implementation. Violation requires
escalation, not a workaround.

- **Detect-only, never edit, never judge (ADR-001; design §4.4).** `desloppify`
  reads files and reports. It writes nothing to disk: no `state.toml` mutation,
  no manuscript edit, no `[pending_turn]` bracket.
- **No shelling out (design §9, lines 724-726).** "v1 commands shell out to
  nothing, so the suite touches only the filesystem under `tmp_path`."
  `desloppify` must replace the improvised `grep` (slice-4 idea, roadmap lines
  808-811) with in-process Python `re` matching over text read with
  `pathlib.Path.read_text`. **It must not use `cuprum` in production code.**
  cuprum appears only in the *end-to-end test* to run the installed
  console-script by absolute path, exactly as
  `tests/test_console_scripts_e2e.py` already does for the other scripts.
- **Exit-code contract (design §3.2 and §9; `ExitCode`).** `0` clean, `4`
  actionable finding, `2` usage error (bad invocation **or** malformed pack
  content via `RulePackError`), `3` state/input error (absent `working/`,
  missing manifest, unreadable/undecodable pack file via `RulePackFileError`,
  unreadable draft). The exit-3 cases are not scope creep beyond the roadmap's
  0/4/2 success line: design §9 explicitly lists "unreadable or absent pack
  file → exit 3" and the absent-`working/` state-error channel, so exit 3 is
  the design-mandated fault route, cited here against §9 (round-1 advisory).
  Code `1` (benign negative) is **not** used by `desloppify`: a clean pass is a
  success (`0`), not a "not yet" — confirmed by design §4.4 line 371 ("A clean
  pass exits 0").
- **Shared envelope contract (design §3.1; ADR-003).** Output is the one JSON
  object built by `build_envelope`; `result` carries machine-actionable data,
  `messages` carries human prose. The command is wired through the shared
  `novel_ralph_skill.contract.runner.run` wrapper exactly as `novel-state` is,
  and the `--human` global flag is pre-parsed with `parse_global_flags`.
- **Rule-pack schema is fixed (design §6.1; task 5.1.1).** The pack carries
  `schema_version = 1`, a `pack` name, and `[[rule]]` tables of `id`, `pattern`,
  `threshold`, `basis` (`manuscript` | `per_page`), and `page_words`
  (`per_page` only). This plan adds **no** new pack keys and no new `RuleBasis`
  member. The loader (`load_rulepack`) is reused unchanged.
- **Working directory is the fixed `working/` constant (design line 151;
  `WORKING_DIR_NAME`).** There is no `--working-dir` flag. The manuscript lives
  at `working/manuscript/chapter-NN/draft.md` and the chapter manifest is
  `[chapters]` in `working/state.toml` (design §5.1).
- **Word/page counting rule is fixed (design §4.5; `state.wordcount`).** A page
  for `per_page` density is `page_words` whitespace-split tokens, using the same
  `len(text.split())` token rule the existing `recount_words` uses, so the two
  counts cannot drift.
- **en-GB Oxford spelling** ("-ize"/"-yse"/"-our") in all prose, comments, and
  commits. No file exceeds 400 lines (AGENTS.md).

## Tolerances (exception triggers)

- **Scope.** If the implementation requires changing more than 8 production
  files or more than ~500 net lines, stop and escalate.
- **Interface.** If the shared `run`/`CommandOutcome`/`Envelope`/`ExitCode`
  signatures must change, or `build_app` in `novel_state.py` must change, stop
  and escalate. `desloppify` is a standalone app; it must not perturb
  `novel-state`.
- **Dependencies.** If a new external dependency is required, stop and
  escalate. This plan adds none — it uses stdlib `re`, `pathlib`,
  `importlib.resources`, and the existing `cyclopts`, plus the existing
  `rulepack`/`contract`/`state` packages.
- **Loader change.** If a §6 offender pattern cannot be expressed under the
  frozen rule-pack schema (for example a rule needs a counting basis other than
  `manuscript`/`per_page`), stop and escalate rather than extending the schema
  inside this task.
- **Iterations.** If a stage's tests still fail after 3 focused attempts, stop
  and escalate.
- **Ambiguity.** If a §6 offender's regex is genuinely ambiguous (e.g. the
  bracketed `[her]`/`[verb]` placeholders), pin the chosen interpretation in
  the Decision Log; if two readings materially change which prose is flagged,
  stop and present them.

## Risks

    - Risk: A §6 offender row uses a placeholder ("[her]", "[verb]-ed
      sadly/quietly/softly", "capitalized abstract noun") that has no single
      obvious regex, or one obvious reading silently misses the offender.
      Severity: medium
      Likelihood: high
      Mitigation: Work item 2 pins the *complete* 24-row pack verbatim in this
      ExecPlan (the TOML block below), thresholds taken from the §6 table, with
      a `# why` comment on every placeholder row. A table-driven unit test
      asserts the loaded rule-id set **equals** the §6 row set (a missing or
      extra row fails), and a per-rule positive/negative matrix pins each
      pattern. The two genuinely ambiguous placeholders are pinned in the
      Decision Log: (1) "[verb]-ed sadly/quietly/softly" is read as the literal
      §6 row — a token ending `-ed` followed within a short non-newline window by
      one of the three named adverbs — and the broader §4 "X said with adverbs"
      dialogue tell (whose canonical example "she said sadly" does **not** end in
      "-ed") is **out of scope** for the §6 pack (it is a §4 tell, not a §6 row);
      (2) "capitalized abstract noun" is narrowed to the closed alternation of
      the §6 named offenders ("Tapestry"/"Symphony"/"Paradigm"), not a
      part-of-speech check. Both narrowings are recorded in the Decision Log.

    - Risk: The packaged pack TOML is not included in the built wheel, so the
      installed console-script cannot find it at runtime.
      Severity: high
      Likelihood: medium
      Mitigation: Place the pack inside the package tree at
      `novel_ralph_skill/rulepack/packs/offenders.toml` and resolve it with
      `importlib.resources.files`. hatchling's wheel target already ships every
      file under `novel_ralph_skill/` (pyproject `packages = ["novel_ralph_skill"]`).
      The Work item 5 e2e builds and installs a real wheel and runs the script,
      proving the pack travels.

    - Risk: `per_page` density is computed inconsistently with the existing word
      count, letting `desloppify` and `wordcount`/`recount` disagree on "a page".
      Severity: medium
      Likelihood: medium
      Mitigation: Reuse the `len(text.split())` token rule; a unit test pins the
      density formula against a hand-computed example at the page boundary.

    - Risk: Line numbers in the report drift when the manuscript is the ordered
      concatenation of several chapter drafts (whole-manuscript scope).
      Severity: low
      Likelihood: medium
      Mitigation: Report line numbers per source file (chapter), not against a
      synthesized global buffer; the detection core records `(chapter, line)`
      for each hit. Pin with a two-chapter snapshot.

    - Risk: A multi-token span offender ("it's not just… it's…",
      "—but that was just the beginning") matches greedily across sentence or
      paragraph boundaries, or its `.`-based span silently fails to cross a
      newline, so the v1 scan over-matches distant unrelated text or misses a
      newline-split instance entirely.
      Severity: medium
      Likelihood: high
      Mitigation: The loader compiles every pattern with `re.compile(pattern)`
      and **no** flags (`rulepack/parse.py:_compile_pattern`, verified), so `.`
      never crosses `\n` and any laziness/window must be written into the
      pattern itself. **Detection therefore scans line-by-line, not
      whole-chapter:** Work item 1 splits each chapter into physical lines
      (`text.splitlines()`) and runs `rule.compiled.finditer(line)` per line,
      recording the 1-based line index directly (no offset arithmetic). This
      makes the line number exact and bounds every match to a single line.
      Multi-token spans that legitimately occur within one line use a **bounded,
      lazy, non-newline window** `[^\n]{0,N}?` (N pinned per row in the pack
      below) rather than greedy `.*`, so a span cannot run to a distant
      unrelated token. **v1 scope is explicit: a multi-token offender split
      across a hard line break is not detected** (recorded as a Decision Log
      limitation; the writer's drafts wrap at sentence/paragraph granularity, so
      single-line coverage catches the common case). Work item 1's test matrix
      adds a multi-line negative (an "it's not just X,\nit's Y" split across two
      lines yields **zero** hits — the documented v1 limitation) and a
      cross-sentence negative (two unrelated "it's" tokens on one long line do
      **not** match because the window is bounded and lazy).

## Progress

    - [x] Work item 1 — Detection core: pure `desloppify` aggregation over a
      `RulePack` and manuscript text. Done: `novel_ralph_skill/rulepack/detect.py`
      with `ScannedChapter`, `LineHit`, `RuleFinding`, `DetectionReport`, and
      `detect`; line-by-line scan; `tests/test_rulepack_detect.py` (11 cases,
      all green). `make all` green; coderabbit run 1 (3 findings: test-assertion
      messages applied; the "single-line private docstring" finding skipped — the
      package convention and the 100% interrogate gate require full structured
      docstrings on private helpers, matching `parse.py`/`wordcount.py`).
    - [x] Work item 2 — Author and validate the §6 offender rule pack
      (`offenders.toml`) and ship it inside the package. Done:
      `novel_ralph_skill/rulepack/packs/offenders.toml` (24 rows, thresholds
      verbatim) and `…/packs/__init__.py`; `tests/test_offenders_pack.py` pins
      rule-id set equality, the (id, threshold, basis) table, the single
      per_page rule, the per-rule positive/negative matrix, and the
      Decision-Log out-of-scope cases (verb-ed/"said sadly", couldnt-help-but/
      "could not", found-herself bare reflexive + line-wrap). `make all` green
      (433 passed); coderabbit run 2 returned 0 findings.
    - [x] Work item 3 — Manuscript/chapter text sourcing from the `working/`
      tree (manifest-driven, exit-3 fault routing). Done:
      `novel_ralph_skill/commands/_desloppify.py` adds `source_chapters`,
      `_chapter_text`, `_select_chapters`, and the exit-2-bound
      `DesloppifyUsageError`; loads typed state via `novel_state.
      _load_or_state_error`; absent draft → empty text, other read faults →
      `StateInputError` (exit 3). `tests/test_desloppify_sourcing.py` pins the
      scope, the benign-absent case, and the exit-2 vs exit-3 split. `make all`
      green (439 passed); coderabbit run 3 (1 minor: added `match=` regex to the
      three `pytest.raises` — applied).
    - [x] Work item 4 — Wire the `desloppify` Cyclopts command, exit-code
      translation, and envelope; replace the stub. Done:
      `_desloppify.py` adds `build_app`, `_desloppify`, `_scan_or_usage`;
      `_desloppify_report.py` adds `offenders_pack_path`, `report_outcome`,
      `_finding_payload`/`_finding_message` (the 400-line-cap split, Decision
      Log). `stub.desloppify()` now drives the real app; `test_command_stubs.py`
      and `test_console_scripts_e2e.py` drop `desloppify` from the still-stubbed
      sets. `tests/test_desloppify_command.py` pins the 0/4/2/3 exit routes and
      the `--help` carve-out. `basis` emitted as `.value`. `make all` green
      (450 passed incl. snapshot + e2e); coderabbit run 4 (2 findings: critical
      `offenders_pack_path` returned a `Traversable` cast to `Path` — fixed by
      widening `load_rulepack` to accept `Traversable` (a `Path` *is* a
      `Traversable`; the loader only needs `.open("rb")`) and returning the honest
      type; major "explicit return in test `_run`" skipped — `run()` is `NoReturn`
      so a trailing `return` is unreachable, and the established `_run_check`
      helper in `test_novel_state_check.py` uses the same no-explicit-return
      shape).
    - [x] Work item 5 — Snapshot, boundary, error-path, and e2e tests
      (design §9), plus docs. Done: `tests/test_desloppify_snapshots.py` (the
      clean-pass / one-hit-past-threshold envelope pair, paired with semantic
      guards — `basis` is a `str`, `lines` ascending, no volatile fields);
      `tests/test_desloppify_e2e.py` (build-install-run wheel proof, exit 4 on an
      em-dash flood and 0 clean, proving the packaged pack travels). Docs:
      `users-guide.md` and `developers-guide.md` move `desloppify` out of the
      stub list and document it; `roadmap.md` ticks 5.1.2. `make all` green
      (450 passed); `make markdownlint`/`make nixie` green on the edited docs;
      coderabbit run 5 returned 0 findings.
    - [x] Fix round 1 — Emit the enumerated `phrase` per-hit field. Done:
      `_desloppify_report.py:_finding_payload` now emits
      `"phrase": finding.pattern` (the design §4.4 / roadmap 5.1.2 enumerated
      field that round 1 dropped, leaving `RuleFinding.pattern` dead in the
      envelope — dual-review blocking finding); module and function docstrings
      updated; `tests/test_desloppify_snapshots.py` asserts `phrase` is a
      non-empty `str` directly and the `.ambr` snapshot was regenerated;
      `users-guide.md` adds `phrase` to the `result.findings` field list. No
      design/roadmap wording change needed — `rule_id` is retained as the stable
      slug, `phrase` is the offender pattern, so contract and implementation
      agree (see Decision Log). `make all` green (450 passed); `make
      markdownlint`/`make nixie` green; coderabbit fix-round-1 run returned 0
      findings.

## Surprises & discoveries

    - Observation: (none yet)
      Evidence:
      Impact:

## Decision log

    - Decision: `desloppify` uses no `cuprum` in production; cuprum is test-only.
      Rationale: Design §9 states v1 commands shell out to nothing; the slice-4
      purpose is to *replace* the improvised `grep` with in-process matching.
      The task brief asked the plan to pin cuprum APIs, but the verified
      design forbids shelling out here. cuprum's role is confined to the e2e
      test, which runs the installed console-script by absolute path via
      `Program(str(path))` and `sh.make(prog, catalogue=…).run_sync(capture=True)`
      — the exact pattern already in `tests/test_console_scripts_e2e.py`.
      Verified against the locked cuprum 0.1.0 source: `cuprum/sh.py:make`
      (line 528) calls `catalogue.lookup(program)` (line 538), and
      `ProgramCatalogue.lookup` (`cuprum/catalogue.py` line 79) raises
      `UnknownProgramError` for any program not registered in the catalogue.
      cuprum does **not** admit arbitrary `Program` strings: `allowlist`
      (`cuprum/catalogue.py`) is a read-only `frozenset` property derived from
      the registered `ProjectSettings.programs`, not an admission method. The
      e2e therefore works because the absolute-path `Program` is **registered**:
      `tests/conftest.py:single_program_catalogue` builds a one-`ProjectSettings`
      catalogue whose `programs` tuple contains exactly that `Program`, making
      the allowlist the execution gate. Work item 5's e2e reuses that fixture
      and registers the installed `desloppify` script path the same way.
      Date/Author: 2026-06-24, planner.

    - Decision: Detection scans line-by-line; multi-token offenders use a
      bounded, lazy, non-newline window and v1 does not detect a span split
      across a hard line break.
      Rationale: The loader compiles with `re.compile(pattern)` and no flags
      (`rulepack/parse.py:_compile_pattern`, verified), so `.` cannot cross
      `\n` and greedy `.*` over whole-chapter text both over-matches to distant
      unrelated tokens and misses newline-split spans (the round-1 review's
      verified failure modes). Scanning each physical line independently
      (`text.splitlines()` + `finditer(line)`) makes line numbers exact, bounds
      each match to one line, and removes the offset arithmetic. Multi-token
      single-line spans use `[^\n]{0,N}?` (lazy, non-newline) instead of `.*`.
      The cost is that a span hard-wrapped across a line break is undetected in
      v1; this is acceptable because the writer drafts wrap at sentence or
      paragraph boundaries, so single-line coverage catches the common case, and
      it is pinned by a multi-line negative test so the limitation is explicit,
      not accidental. (Risk "multi-token span offender"; round-1 defect 3.)
      Date/Author: 2026-06-24, planner.

    - Decision: The "[verb]-ed sadly/quietly/softly" §6 row is read as the
      literal row (a `-ed` token then one of the three named adverbs within a
      short non-newline window); the broader §4 "X said with adverbs" tell is
      out of scope for the §6 pack.
      Rationale: The §6 table row is the literal string
      "[verb]-ed sadly/quietly/softly" with threshold 2. The §4 canonical
      example "she said sadly" is a *different* checklist tell (§4 "Dialogue
      tells → 'X said' with adverbs"); "said" does not end in "-ed", so the §6
      row was never meant to catch it. Conflating the two would either bake in a
      silent false negative (a `\w+ed` pattern that "passes" its positive test
      while missing "said sadly") or balloon the §6 row into a §4 rule. The §6
      pack pins the §6 reading; §4's dialogue adverbs belong to a later
      dialogue-tells pack (roadmap 7.1), recorded here as out of scope.
      (Round-1 defect 2.)
      Date/Author: 2026-06-24, planner.

    - Decision: The `couldnt-help-but` §6 row matches the contraction only
      ("couldn't help but" / "couldnt help but"); the expanded hedge "could not
      help but" is deliberately **out of scope** for this row.
      Rationale: The §6 table row is the literal string "couldn't help but"
      (threshold 1) and the §1 canonical example is "She couldn't help but
      smile" — both the contraction. The pinned pattern
      `(?i)\bcould\s?n'?t help but\b` matches "couldn't"/"couldnt" but NOT "could
      not" (verified against Python `re`: `couldn't help but`→match,
      `couldnt help but`→match, `could not help but`→NO match; the `\s?n'?t`
      fragment matches `nt`/`n't`, and the `o` of "not" breaks it). Widening to
      the hedge was considered and rejected: it would balloon the faithful §6
      transcription beyond the §6 literal, exactly the over-reach the
      `verb-ed-adverb`/"said sadly" row was pinned to avoid. The correct widening
      would be `(?i)\bcould(?:\s?n'?t| not) help but\b` (verified to match all
      three forms while rejecting "could help but" and "couldnot help but"); the
      review's candidate `\bcould\s?n(?:'?t| not) help but\b` is itself buggy (it
      still misses "could not help but", verified). This row keeps the §6 literal
      and pins the omission with a negative test: `could not help but`→0 hits,
      mirroring the `verb-ed-adverb`/"said sadly" out-of-scope pin. (Round-4
      blocking defect; same defect-class as round-1 defect 2 — a `# why` comment
      asserting behaviour the pattern lacks. The contradictory comment is
      corrected to state "could not" is out of scope.)
      Date/Author: 2026-06-24, planner.

    - Decision: "shivers down [her] spine" pins the `[her]` placeholder to a
      possessive/article set and allows the common "shiver"/"shivers" and
      "down"/"up" variants; "capitalized abstract noun" narrows to a closed
      alternation of the §6 named offenders.
      Rationale: The `[her]` bracket is the checklist's placeholder for "any
      possessive"; pinning it to `(?:her|his|their|my|your|the)` covers the POV
      pronouns plus the article without a part-of-speech engine. A true
      "capitalized abstract noun" classifier is out of reach for stdlib `re`;
      the §6 table already supplies the offenders to count ("Tapestry",
      "Symphony", "Paradigm"), so the rule is a closed alternation of those
      proper-noun-cased tells, anchored to word boundaries. Both are pinned
      verbatim in the Work item 2 TOML block. (Round-1 defect 2; Risk row 1.)
      Date/Author: 2026-06-24, planner.

    - Decision: The "found [herself] + verb" §6 row requires a following word
      token (`[^\S\n]+\w`), the regex-expressible proxy for "+ verb"; the bare
      reflexive ("found herself." with no continuation) is deliberately **not**
      flagged.
      Rationale: The §6 table row is the literal string '"found [herself]" +
      verb' (threshold 2) — the "+ verb" is constitutive of the row, not
      decoration. The round-2 pattern
      `\bfound (?:her|him|them|my|our|your)sel(?:f|ves)\b` dropped the "+ verb"
      part and matched the bare reflexive (verified: it matches "found herself."
      with no following verb), which is an unpinned reinterpretation that flags
      prose the §6 row does not name — the same defect-class as round-1 defect 2.
      A true part-of-speech verb classifier is out of reach for stdlib `re` (the
      same constraint already pinned for the capitalized-abstract-noun row), so
      the faithful, testable reading is to require at least one more word token
      immediately after the reflexive: `[^\S\n]+\w`. `[^\S\n]` is whitespace
      except a newline, so the continuation stays on the same physical line
      (consistent with the line-by-line scan, Work item 1) and a reflexive that
      ends a line with its verb on the next line is undetected in v1 (the same
      single-line limitation already documented for multi-token spans). This
      narrows "+ verb" to "+ following word token": it correctly admits "found
      herself wondering / walking / drawn" and correctly rejects the bare
      reflexive ("found herself." / "found himself!" / "found herself, alone"),
      at the cost of also admitting a following non-verb word ("found herself
      alone") — an over-match that is far less harmful than the round-2
      under-specification and is acceptable because the row's threshold is 2
      (it tolerates incidental hits) and a POS check is unavailable in `re`. The
      positive/negative matrix in `tests/test_offenders_pack.py` pins this exact
      reading. (Round-3 blocking defect; mirrors the shivers/verb-ed-adverb/
      capitalized-noun placeholder decisions.)
      Date/Author: 2026-06-24, planner.

    - Decision: The spaced en dash ( – ) of the df12 register (§1 of the
      checklist) is out of scope for the §6 `em-dash` row, which counts the
      unspaced em dash (—) only.
      Rationale: §6's "em dash" row counts the literal `—`; the df12
      spaced-en-dash variant is a register-specific tell belonging to a future
      register pack, not the universal §6 offender table. Recorded so a later
      reader does not treat the omission as a miss. (Round-1 advisory.)
      Date/Author: 2026-06-24, planner.

    - Decision: The §6 offender pack ships at
      `novel_ralph_skill/rulepack/packs/offenders.toml`, resolved with
      `importlib.resources.files("novel_ralph_skill.rulepack.packs")`.
      Rationale: It must be present in an installed wheel; placing it inside the
      already-shipped package tree (hatchling `packages = ["novel_ralph_skill"]`)
      and resolving via `importlib.resources` is the stdlib-only way that
      survives installation. No `tool.hatch.build` change is needed because
      hatchling includes non-`.py` files under the package directory by default.
      Date/Author: 2026-06-24, planner.

    - Decision: Default pack is `offenders.toml`; an optional `--pack PATH`
      overrides it.
      Rationale: Design §4.4 says `desloppify` runs "the checklist's §6
      high-frequency-offender table as a versioned rule pack", so the §6 pack is
      the default. `--pack` lets the later ai-isms/device-ledger packs (roadmap
      7.1) reuse the command without re-plumbing. A missing/unreadable
      `--pack` file is `RulePackFileError` → exit 3; malformed content is
      `RulePackError` → exit 2, both already raised by `load_rulepack`.
      Date/Author: 2026-06-24, planner.

    - Decision: Scope selection is `--chapter N` (one chapter) or, when absent,
      the whole manuscript (every manifest chapter in order).
      Rationale: Design §4.4 line 363 — "over a chapter or the whole
      manuscript". The chapter set is the `[chapters]` manifest in
      `working/state.toml` (design §5.1), the same authoritative source
      `recount` uses. `--chapter N` outside the manifest is a usage error
      (exit 2); an absent `working/` or unparseable `state.toml` is a state
      error (exit 3).
      Date/Author: 2026-06-24, planner.

    - Decision: Line numbers are reported per source chapter file, not against a
      synthesized global buffer.
      Rationale: Whole-manuscript scope concatenates several drafts; a global
      line number would be meaningless to the agent fixing chapter 7. Each hit
      carries `{chapter, line}`. (Risk "line numbers drift".)
      Date/Author: 2026-06-24, planner.

    - Decision: The two loader errors are mapped to exit codes in the command
      *body* (`_desloppify`), not by extending the shared `run` wrapper's
      `except` chain.
      Rationale: The ExecPlan's preferred approach was extending `runner.py`,
      with a body-local fallback if that would breach the interface tolerance.
      The body-local catch was chosen: it keeps `runner.py` untouched (so the
      four other commands cannot be perturbed) and confines the
      `rulepack`→`contract` coupling to the one command that needs it rather than
      importing `rulepack.errors` into the shared seam. `_desloppify` catches
      `RulePackError` and returns `CommandOutcome(USAGE_ERROR)` (exit 2); it
      catches `RulePackFileError` and re-raises `StateInputError` (exit 3, which
      the runner already maps). The body-detected bad-`--chapter`
      `DesloppifyUsageError` is mapped by the thin `_scan_or_usage` adapter to a
      `CommandOutcome(USAGE_ERROR)`. All four routes are pinned by
      `tests/test_desloppify_command.py`. (ExecPlan WI4 "Decide at implementation
      time and record in the Decision Log".)
      Date/Author: 2026-06-24, implementer.

    - Decision: The command module splits into `_desloppify.py` (sourcing +
      Cyclopts wiring) and `_desloppify_report.py` (the envelope projection and
      the `offenders_pack_path` resolver).
      Rationale: The combined module reached 431 lines, over the 400-line cap
      (AGENTS.md). The split mirrors `_recount.py` beside the mutator module:
      the pure report→`CommandOutcome` projection and the `importlib.resources`
      pack resolver have no dependency on the sourcing/Cyclopts code, so they
      move cleanly. `_desloppify.py` re-imports `offenders_pack_path` and
      `report_outcome`, so the ExecPlan's prescribed `_desloppify` public surface
      (which lists `offenders_pack_path`) still resolves.
      Date/Author: 2026-06-24, implementer.

    - Decision: The per-hit envelope payload emits the enumerated `phrase` field,
      carrying the rule's authored pattern source (`RuleFinding.pattern`).
      Rationale: Design §4.4 ("It emits structured output per hit: phrase, count,
      density per N words, threshold, pass or fail, and line numbers") and the
      roadmap 5.1.2 bullet both enumerate `phrase`, but the round-1 projection in
      `_desloppify_report.py:_finding_payload` emitted only `rule_id`, `count`,
      `threshold`, `basis`, `density`, `passed`, and `lines` — so an enumerated
      contract field was silently absent and `RuleFinding.pattern` (carried all
      the way through `detect.py`) was dead data in the envelope (dual-review
      blocking finding). The data is already present, so the fix emits it under
      the contract's own field name, `phrase = finding.pattern`, beside the
      retained `rule_id` slug that the `violations` list references. `rule_id` is
      kept (it is the stable machine handle the harness branches on) rather than
      treated as a substitute for `phrase`, so no design/roadmap wording change is
      needed: both the contract field and the implementation now agree. The
      snapshot test asserts `phrase` is a non-empty `str` directly (not
      snapshot-only), and the `desloppify` snapshots and the users-guide field
      list were updated to carry the new field.
      Date/Author: 2026-06-24, implementer.

## Outcomes & retrospective

All five work items are landed and `make all` is green at HEAD. The three
observable outcomes from Purpose hold, each verified by an automated test:

- `desloppify` over clean prose prints `ok:true` and exits `0`
  (`test_desloppify_command.py::test_clean_tree_exits_zero`; the e2e
  `test_installed_desloppify_clean_tree_exits_zero` proves it for the installed
  script).
- `desloppify` over an em-dash flood prints `ok:false`, names `em-dash` in
  `result.violations`, and exits `4`
  (`test_em_dash_flood_exits_four`; e2e `test_installed_desloppify_flags_offender`
  proves the packaged pack travels in the wheel).
- A malformed pack / bad `--chapter` exits `2` and an absent pack file / absent
  `working/` exits `3`, each distinguishable by exit code alone
  (`test_malformed_pack_exits_two`, `test_chapter_outside_manifest_exits_two`,
  `test_absent_pack_file_exits_three`, `test_absent_working_dir_exits_three`).

Lessons:

- The `importlib.resources` resolver must be typed as `Traversable`, not cast to
  `pathlib.Path`: a normal install yields a `PosixPath` (which *is* a
  `Traversable`), but the honest type and a `Traversable`-typed `load_rulepack`
  avoid an unsafe cast and keep a zipped install correct (CodeRabbit round-4
  critical finding).
- The combined command module overran the 400-line cap; splitting the pure
  envelope projection and the resolver into `_desloppify_report.py` (mirroring
  `_recount.py`) kept both files well under the cap with a clean dependency edge.
- Placeholder §6 rows ("[her]", "+ verb", capitalized abstract noun, the
  contraction-only "couldn't help but") each needed an explicit pinned reading
  and a both-directions positive/negative test, so the pack's comments never
  assert behaviour the regex lacks.

## Context and orientation

This repository builds a deterministic command spine for a novel-writing Ralph
harness. The five console-scripts are `novel-state`, `novel-done`,
`novel-compile`, `desloppify`, and `wordcount`. Four are still stubs; this task
turns `desloppify` real.

Key existing files (full repository-relative paths):

- `novel_ralph_skill/rulepack/__init__.py`, `…/schema.py`, `…/parse.py`,
  `…/errors.py` — the task-5.1.1 rule-pack model and loader.
  `load_rulepack(path)` returns a frozen `RulePack` of `Rule` objects, each
  with a precompiled `compiled: re.Pattern[str]`, an integer `threshold`, a
  `RuleBasis` `basis` (`MANUSCRIPT` | `PER_PAGE`), and
  `page_words: int | None`. A malformed pack raises `RulePackError` (exit 2,
  names the rule); a missing/undecodable file raises `RulePackFileError` (exit
  3). The loader never calls `sys.exit` and emits no envelope — translation is
  this command's job.
- `novel_ralph_skill/contract/runner.py` — the shared `run(app, argv, context)`
  wrapper, `CommandOutcome(code, result, messages)`,
  `RunContext(command, working_dir, human)`, `StateInputError` (exit-3
  channel), and `parse_global_flags(argv)` (the `--human` splitter).
- `novel_ralph_skill/contract/exit_codes.py` — `ExitCode` IntEnum:
  `SUCCESS=0`, `BENIGN_NEGATIVE=1`, `USAGE_ERROR=2`, `STATE_ERROR=3`,
  `ACTIONABLE_FINDING=4`.
- `novel_ralph_skill/contract/envelope.py` — `build_envelope(...)` and the two
  renderers; `command` must be a member of `COMMAND_NAMES`.
- `novel_ralph_skill/commands/novel_state.py` — the model for a real command:
  `build_app()` builds a Cyclopts app with
  `result_action="return_value", exit_on_error=False, print_error=False, help_on_error=False`;
  `WORKING_DIR_NAME = "working"`; `STATE_INPUT_ERRORS` (the tuple of load
  faults translated to exit 3); `_load_or_state_error`.
- `novel_ralph_skill/commands/_recount.py` and
  `novel_ralph_skill/state/wordcount.py` — the manifest-driven draft reader.
  `recount_words(working_dir, manifest)` reads
  `working/manuscript/chapter-NN/draft.md` per `[chapters]` entry; the token
  rule is `len(text.split())`; an absent draft is `0`, every other read fault
  propagates for the command to route to exit 3.
- `novel_ralph_skill/commands/stub.py` — the `desloppify()` entry point
  (currently a stub) and the shared `make_stub_app`. `novel_state()` shows the
  real wiring: `parse_global_flags(sys.argv[1:])` then
  `run(build_app(), residual, RunContext(...))`.
- `novel_ralph_skill/commands/names.py` — `COMMAND_NAMES`,
  `COMMAND_ENTRY_POINTS` (single source of truth for the script ↔ entry-point
  map).
- `tests/data/rulepacks/` — the corpus of valid/invalid packs the 5.1.1 loader
  tests use; `valid.toml` is a working reference. Reusable here for fault paths.
- `tests/test_console_scripts_e2e.py` — the build-install-run e2e pattern that
  uses cuprum to run an installed script by absolute path.
- `tests/test_novel_state_check.py` — the in-process command test pattern
  (`monkeypatch.chdir`, `capsys`, `run(...)` under a materialized `working/`).

Terms:

- **Rule pack** — a versioned TOML file of detection rules (design §6.1).
- **Basis** — how hits are counted: `manuscript` (one count across all scanned
  text against `threshold`) or `per_page` (hits per notional `page_words`-token
  page against `threshold`).
- **Hit** — one non-overlapping regex match of a rule's `compiled` pattern.
- **Actionable finding** — a checker result (`exit 4`) the agent must
  adjudicate; here, any rule exceeding its threshold.

Source docs to read before implementing: design §4.4, §6.1, §3.1-§3.2, §9;
`docs/developers-guide.md` "Rule packs and the loader boundary"; AGENTS.md
testing rules; `docs/adr-003-shared-interface-contract.md`;
`docs/scripting-standards.md` (Cyclopts; cuprum for the e2e only);
`skill/novel-ralph/references/desloppify-checklist.md` §6 (the offender table).

## Plan of work

Five atomic, independently committable work items. Each ends with `make all`
green and, where markdown changes, `make markdownlint` and `make nixie`.

### Work item 1 — Detection core (pure aggregation)

Create `novel_ralph_skill/rulepack/detect.py` (a leaf module beside the loader,
under the 400-line cap). It contains the pure detection over a `RulePack` and
in-memory text — no filesystem, no `sys.exit`, no envelope — so it is trivially
unit-testable and reusable by the later packs (roadmap 7.1).

Define the result shapes as frozen, slotted, keyword-only dataclasses, in the
package house style:

        # novel_ralph_skill/rulepack/detect.py
        @dataclasses.dataclass(frozen=True, kw_only=True, slots=True)
        class RuleFinding:
            rule_id: str
            pattern: str
            count: int
            threshold: int
            basis: RuleBasis
            page_words: int | None
            density: float | None   # hits per page (per_page); None for manuscript
            passed: bool            # count/density within threshold
            lines: tuple[LineHit, …]  # (chapter, line) per match, in order

        @dataclasses.dataclass(frozen=True, kw_only=True, slots=True)
        class LineHit:
            chapter: int
            line: int

        @dataclasses.dataclass(frozen=True, kw_only=True, slots=True)
        class DetectionReport:
            pack: str
            total_words: int
            findings: tuple[RuleFinding, …]
            passed: bool   # all(f.passed for f in findings)

Define a `ScannedChapter` input shape `(number: int, text: str)` and the entry
point:

        def detect(
            pack: RulePack,
            chapters: cabc.Sequence[ScannedChapter],
        ) -> DetectionReport: …

`detect` iterates each rule over each chapter's text **line by line**. For each
chapter it splits the text into physical lines with `text.splitlines()` and,
for each rule, runs `rule.compiled.finditer(line)` over each line, recording
the 1-based line index directly (the enumeration index, no offset arithmetic).
This is the round-1 defect-3 fix: the loader compiles patterns with
`re.compile` and **no** flags, so `.` cannot cross `\n`; scanning per line
makes line numbers exact, bounds every match to a single line, and prevents a
greedy span from running to a distant unrelated token. Multi-token single-line
offenders express their span as the bounded lazy non-newline window
`[^\n]{0,N}?` in the pack (Work item 2), never greedy `.*`. A multi-token
offender hard-wrapped across a line break is **not** detected in v1 (Decision
Log limitation). The total `count` for a rule is the sum of its per-line,
non-overlapping `finditer` matches across all chapters; pass/fail is then
computed:

- `MANUSCRIPT`: `passed = count <= threshold`; `density = None`.
- `PER_PAGE`: `total_words = sum(len(ch.text.split()) for ch in chapters)`;
  `pages = total_words / page_words` (a float; a partial page still counts);
  `density = count / pages` when `pages > 0` else `0.0`;
  `passed = density <= threshold`. Pin the `pages == 0` (empty manuscript) edge
  to `passed = count <= 0`.

`DetectionReport.passed = all(f.passed for f in findings)`.

Stage B tests (`tests/test_rulepack_detect.py`, unit):

- A `manuscript` rule at exactly `threshold` hits passes; one over fails.
- A `per_page` rule at exactly `threshold` density passes; one over fails
  (hand-computed against a fixed `page_words` and a fixed word count — the
  boundary example design §9 names).
- Two hits on one line produce `count == 2` and two `LineHit`s with the same
  line; hits on chapters 1 and 2 carry the right `chapter`.
- An empty manuscript: every rule passes; `total_words == 0`; no
  `ZeroDivisionError`.
- Overlap: a pattern that could overlap counts non-overlapping matches only
  (pin the chosen `finditer` semantics).
- **Multi-line negative (defect 3):** an "it's not just X,\nit's Y" instance
  split across two physical lines yields **zero** hits for the `it-s-not-just`
  rule — pinning the documented v1 single-line limitation so it is explicit,
  not accidental.
- **Cross-sentence negative (defect 3):** a single long line containing two
  unrelated "it's" tokens far apart (beyond the rule's `[^\n]{0,N}?` window)
  yields **zero** hits, proving the bounded lazy window does not over-match to
  a distant token.
- **Single-line positive (defect 3):** "It's not just cold, it's freezing." on
  one line yields exactly one hit at that line — the offender the rule must
  catch.

Validation: `make all`. New test `tests/test_rulepack_detect.py` fails before
the module exists and passes after.

Skills/docs for this item: load `python-router` → `python-data-shapes` (frozen
dataclass choice), `python-testing` (boundary unit tests), and review design
§4.4, §6.1, §9. No property/Hypothesis suite (design §9: pure aggregation).

### Work item 2 — Author and ship the §6 offender rule pack

Create `novel_ralph_skill/rulepack/packs/offenders.toml` and
`novel_ralph_skill/rulepack/packs/__init__.py` (empty package marker so
`importlib.resources.files("novel_ralph_skill.rulepack.packs")` resolves).

The pack carries `schema_version = 1`, `pack = "offenders"`, and exactly **24**
`[[rule]]` tables — **one per row** of the §6 high-frequency-offender table
(`skill/novel-ralph/references/desloppify-checklist.md` §6). This work item is
**transcription, not derivation**: the complete pack is pinned verbatim below.
Every threshold is the §6 table's "Threshold" column verbatim; the implementer
copies the block, runs the tests, and stops. Every pattern was validated
against positive and negative fixtures during planning (see the per-row `# why`
comments); the loader compiles each with `re.compile(pattern)` and no flags
(`parse.py:_compile_pattern`), so `(?i)` is written inline and `.` never crosses
`\n`. Multi-token spans use the bounded lazy non-newline window `[^\n]{0,N}?`
(Work item 1 / defect 3), never greedy `.*`.

The `id` for each row is the slug given. The pinned pack is:

    # novel_ralph_skill/rulepack/packs/offenders.toml
    # The §6 high-frequency-offender table, one [[rule]] per row, thresholds
    # verbatim. Patterns compile under re.compile() with no flags; (?i) is inline.
    # Multi-token spans use a bounded, lazy, non-newline window [^\n]{0,N}? so a
    # single line cannot over-match to a distant token (ExecPlan defect 3).
    schema_version = 1
    pack = "offenders"

    [[rule]]
    id = "it-s-not-just"
    # "It's not just… it's…" — bounded lazy window; v1 single-line only.
    pattern = '''(?i)\bit'?s not just\b[^\n]{0,80}?\bit'?s\b'''
    threshold = 0
    basis = "manuscript"

    [[rule]]
    id = "let-out-a-breath"
    pattern = '''(?i)\blet out a breath\b'''
    threshold = 0
    basis = "manuscript"

    [[rule]]
    id = "shivers-down-spine"
    # "shivers down [her] spine" — [her] pinned to possessive/article set;
    # allow shiver(s) and down/up (Decision Log).
    pattern = '''(?i)\bshivers? (?:down|up) (?:her|his|their|my|your|the) spine\b'''
    threshold = 0
    basis = "manuscript"

    [[rule]]
    id = "air-thick-with"
    pattern = '''(?i)\bthe air was thick with\b'''
    threshold = 0
    basis = "manuscript"

    [[rule]]
    id = "found-herself"
    # "found [herself]" + verb — reflexive-pronoun set, AND a required following
    # word token (the "+ verb" part of the §6 row). [^\S\n]+\w is a newline-safe
    # whitespace-then-word continuation: it is the regex-expressible proxy for
    # "+ verb" (stdlib re has no part-of-speech engine; same constraint as the
    # capitalized-abstract-noun row). It matches "found herself wondering" but NOT
    # the bare reflexive "found herself." / "found himself!" / "found herself,".
    # The [^\S\n] (whitespace except newline) keeps the continuation on the same
    # physical line, consistent with the line-by-line scan (Work item 1). The
    # deliberate narrowing of "+ verb" to "+ following word token" is pinned in the
    # Decision Log; the positive/negative matrix below asserts the chosen reading.
    pattern = '''(?i)\bfound (?:her|him|them|my|our|your)sel(?:f|ves)[^\S\n]+\w'''
    threshold = 2
    basis = "manuscript"

    [[rule]]
    id = "couldnt-help-but"
    # The §6 literal is the contraction "couldn't help but"; this pattern catches
    # the apostrophe form "couldn't" and the apostrophe-less "couldnt" (\s?n'?t
    # matches "n't"/"nt"). The expanded hedge "could not help but" is NOT matched
    # and is deliberately out of scope for this §6 row (Decision Log) — the §6
    # table row and the §1 canonical example are both the contraction. A negative
    # test in tests/test_offenders_pack.py pins "could not help but" → 0 hits.
    pattern = '''(?i)\bcould\s?n'?t help but\b'''
    threshold = 1
    basis = "manuscript"

    [[rule]]
    id = "em-dash"
    # The only per_page row; literal unspaced em dash. The df12 spaced en dash
    # ( – ) is deliberately out of scope (Decision Log).
    pattern = '''—'''
    threshold = 5
    basis = "per_page"
    page_words = 300

    [[rule]]
    id = "but-that-was-just-the-beginning"
    # "—but that was just the beginning"; leading em dash optional.
    pattern = '''(?i)—?but that was just the beginning\b'''
    threshold = 0
    basis = "manuscript"

    [[rule]]
    id = "and-in-that-moment"
    pattern = '''(?i)\band in that moment\b'''
    threshold = 0
    basis = "manuscript"

    [[rule]]
    id = "some-things"
    # "Some things…" (sententious) — sentence-initial; anchored to a line start
    # or after sentence punctuation to avoid mid-sentence "some things".
    pattern = '''(?i)(?:^|[.!?]\s+)some things\b'''
    threshold = 0
    basis = "manuscript"

    [[rule]]
    id = "a-part-of-her"
    pattern = '''(?i)\ba part of (?:her|him|them|me|us|you)\b'''
    threshold = 1
    basis = "manuscript"

    [[rule]]
    id = "capitalized-abstract-noun"
    # Narrowed to the closed set of §6 named offenders, proper-noun-cased; NOT a
    # part-of-speech check (Decision Log). Case-sensitive on purpose.
    pattern = '''\b(?:Tapestry|Symphony|Paradigm)\b'''
    threshold = 1
    basis = "manuscript"

    [[rule]]
    id = "smirked"
    pattern = '''(?i)\bsmirked\b'''
    threshold = 1
    basis = "manuscript"

    [[rule]]
    id = "verb-ed-adverb"
    # "[verb]-ed sadly/quietly/softly" — literal §6 reading: an -ed token then one
    # of the three named adverbs within a short non-newline window. The §4 "X said
    # with adverbs" tell ("she said sadly") is a different checklist item and is
    # out of scope here (Decision Log).
    pattern = '''(?i)\b\w+ed\b[^\n]{0,12}?\b(?:sadly|quietly|softly)\b'''
    threshold = 2
    basis = "manuscript"

    [[rule]]
    id = "the-silence-stretched"
    pattern = '''(?i)\bthe silence stretched\b'''
    threshold = 0
    basis = "manuscript"

    [[rule]]
    id = "her-heart-skipped"
    pattern = '''(?i)\b(?:her|his|their|my|your) heart skipped\b'''
    threshold = 0
    basis = "manuscript"

    [[rule]]
    id = "every-fibre-of-her-being"
    # en-GB "fibre"; allow US "fiber" so imported drafts are still caught.
    pattern = '''(?i)\bevery fib(?:re|er) of (?:her|his|their|my|your) being\b'''
    threshold = 0
    basis = "manuscript"

    [[rule]]
    id = "in-a-world-where"
    pattern = '''(?i)\bin a world where\b'''
    threshold = 0
    basis = "manuscript"

    [[rule]]
    id = "tapestry-of"
    pattern = '''(?i)\btapestry of\b'''
    threshold = 0
    basis = "manuscript"

    [[rule]]
    id = "symphony-of"
    pattern = '''(?i)\bsymphony of\b'''
    threshold = 0
    basis = "manuscript"

    [[rule]]
    id = "a-delicate-balance"
    pattern = '''(?i)\ba delicate balance\b'''
    threshold = 0
    basis = "manuscript"

    [[rule]]
    id = "navigate-the-complexities"
    pattern = '''(?i)\bnavigate the complexities\b'''
    threshold = 0
    basis = "manuscript"

    [[rule]]
    id = "speaks-volumes"
    pattern = '''(?i)\bspeaks volumes\b'''
    threshold = 0
    basis = "manuscript"

    [[rule]]
    id = "paradigm-shift"
    pattern = '''(?i)\bparadigm shift\b'''
    threshold = 0
    basis = "manuscript"

The 24 rule ids form the canonical set the table-driven test asserts:
`it-s-not-just`, `let-out-a-breath`, `shivers-down-spine`, `air-thick-with`,
`found-herself`, `couldnt-help-but`, `em-dash`,
`but-that-was-just-the-beginning`, `and-in-that-moment`, `some-things`,
`a-part-of-her`, `capitalised-abstract-noun`, `smirked`, `verb-ed-adverb`,
`the-silence-stretched`, `her-heart-skipped`, `every-fibre-of-her-being`,
`in-a-world-where`, `tapestry-of`, `symphony-of`, `a-delicate-balance`,
`navigate-the-complexities`, `speaks-volumes`, `paradigm-shift`.

Note the `'''…'''` TOML literal strings: backslashes are **not** escapes in a
TOML literal string, so `\b` reaches `re` intact without doubling. The 5.1.1
loader corpus instead uses *basic* strings with doubled escapes
(`"\\btapestry\\b"` in `tests/data/rulepacks/valid.toml`); either form is valid
TOML and the loader compiles the decoded string identically. Literal strings
are chosen here so the regexes read as written; if the implementer prefers to
match the corpus style, convert to basic strings and double every backslash —
the positive/negative test matrix will catch a mistranscription. Keep the file
under 400 lines (it is ~150).

Stage B tests (`tests/test_offenders_pack.py`, unit):

- `load_rulepack(offenders_pack_path())` succeeds and returns a `RulePack` with
  `pack == "offenders"` and `schema_version == 1`.
- **Rule-id set equality (defect 1):** the set of loaded `rule.id` values
  **equals** the pinned 24-id set above (assert both `==`, so a missing *or*
  extra row fails). This is the atomicity guarantee: the pack is complete or
  the test is red.
- Every rule's `threshold` and `basis` match the §6 table (a table-driven
  assertion keyed by rule id, parametrized over the 24 `(id, threshold, basis)`
  triples transcribed from §6, so a future table edit is caught).
- For each rule, a crafted positive string produces ≥1 `finditer` match and a
  crafted negative produces 0 (the per-rule positive/negative matrix — defends
  Risk row 1). Include the defect-2 cases explicitly: `verb-ed-adverb` matches
  "he smiled sadly" and **does not** match "she said sadly" (the §4 tell, out
  of scope); `shivers-down-spine` matches "a shiver down her spine" and not
  "shivers in the cold"; `capitalised-abstract-noun` matches "a Tapestry of
  light" and not lowercase "tapestry". **`couldnt-help-but` "could not" out of
  scope (round-4 defect):** the rule matches "she couldn't help but smile" and
  "she couldnt help but smile" (≥1) and **does not** match "she could not help
  but smile" (0 hits) — pinning that the expanded hedge is out of scope for the
  §6 contraction row, mirroring the `verb-ed-adverb`/"said sadly" out-of-scope
  pin. Both directions are asserted in the matrix so the chosen reading is
  tested, not merely asserted in the pattern comment. All three strings were
  validated during planning (the pattern matches the two contraction positives
  and not the "could not" negative).
- **`found-herself` "+ verb" semantics (round-3 defect):** the rule matches the
  §6 row's "found [herself] + verb" reading and **rejects** the bare reflexive.
  Pin both directions explicitly in this file's matrix so the chosen reading is
  tested, not just asserted in prose. Positives (≥1 match): "She found herself
  wondering why.", "found herself walking", "He found himself drawn to the
  light." Negatives (0 matches): "She found herself." (sentence-final bare
  reflexive — the exact false positive the round-2 pattern produced), "He found
  himself!", "and so she found herself, alone" (comma immediately after the
  reflexive — no adjacent word token), and "She found her keys." (non-reflexive
  "found her"). Add one more negative pinning the line-by-line scope: a draft
  whose reflexive ends a physical line and whose verb begins the next line
  ("found herself\nwondering") yields 0 hits when fed as two physical lines (the
  `[^\S\n]` continuation cannot cross the break — the documented v1
  single-line limitation, consistent with Work item 1's multi-line negatives).
  All five positive/negative strings were validated during planning (the
  pattern matches the three positives and none of the four single-line
  negatives).
- Exactly one rule has `basis == PER_PAGE` (the `em-dash` rule) with
  `page_words == 300`; all others are `MANUSCRIPT` with no `page_words`.

Add a resolver helper in Work item 4's command module
(`offenders_pack_path() -> Path` via
`importlib.resources.files("novel_ralph_skill.rulepack.packs").joinpath("offenders.toml")`);
pin its final location in the Decision Log when implementing.

Validation: `make all`.

Skills/docs: `python-router` → `python-data-shapes`, `python-testing`
(parametrized table-driven assertions); review design §6.1, §6.2, the
developers-guide "Rule packs" section, and the §6 checklist table.

### Work item 3 — Manuscript/chapter text sourcing

Create `novel_ralph_skill/commands/_desloppify.py` (the command body module,
mirroring `_recount.py`). Add the text-sourcing helper that turns the
`working/` tree into the `Sequence[ScannedChapter]` the core consumes.

Note: `state/wordcount.py:recount_words` returns per-chapter *token counts*,
not the draft *text*, so this helper cannot call it to source text. It reuses
only the two conventions, so the density `total_words` cannot drift from
`recount`: the `chapter-{number:02d}` path-derivation and the
`len(text.split())` token rule (round-1 advisory).

- Resolve `working/state.toml` via
  `pathlib.Path(WORKING_DIR_NAME) / "state.toml"` and load the typed `State`
  through `_load_or_state_error`
  (reused from `novel_state.py`), so a missing/unparseable state is exit 3.
- Read the `[chapters]` manifest (`state.chapters`). For whole-manuscript
  scope, scan every manifest chapter in ascending `number` order; for
  `--chapter N`, scan only that chapter. `--chapter N` not in the manifest is a
  **usage error** → exit 2 (a `RulePackError`-independent usage fault; raise a
  dedicated message routed to `ExitCode.USAGE_ERROR`, not `StateInputError`).
- Read each chapter's `working/manuscript/chapter-NN/draft.md` with
  `Path.read_text(encoding="utf-8")`. Mirror `wordcount._chapter_word_count`'s
  fault boundary: an absent `draft.md` contributes empty text (an undrafted
  chapter has no tics); every other read fault (`PermissionError`,
  `IsADirectoryError`, `UnicodeDecodeError`) is re-raised as `StateInputError`
  → exit 3 via the `STATE_INPUT_ERRORS` tuple, exactly as
  `_recount._recount_or_state_error` does.

Stage B tests (`tests/test_desloppify_sourcing.py`, unit):

- A two-chapter manifest with both drafts present yields two `ScannedChapter`s
  in order with the right text.
- An absent `draft.md` yields an empty-text `ScannedChapter` (not a fault).
- A `--chapter` outside the manifest raises the usage fault (assert the
  exit-2-bound exception type, not exit 3).
- An undecodable draft raises `StateInputError` (exit-3-bound).
- A missing `working/state.toml` raises `StateInputError`.

Validation: `make all`.

Skills/docs: `python-router` → `python-errors-and-logging` (narrow `except`,
`raise … from …`, the exit-2 vs exit-3 split), `python-testing`. Review design
§3.2, §4.1, §5.1; reread `state/wordcount.py` and `_recount.py` for the
fault-boundary precedent.

### Work item 4 — Wire the `desloppify` command and replace the stub

In `_desloppify.py`, add the command body and the Cyclopts app:

        def build_app() -> cyclopts.App:
            app = cyclopts.App(
                name="desloppify",
                result_action="return_value",
                exit_on_error=False,
                print_error=False,
                help_on_error=False,
            )

            @app.default
            def _scan(
                *, chapter: int | None = None, pack: Path | None = None
            ) -> CommandOutcome:
                return _desloppify(chapter=chapter, pack=pack)

            return app

`_desloppify(chapter, pack)`:

1. Load the pack: `load_rulepack(pack or offenders_pack_path())`. Do **not**
   catch `RulePackError`/`RulePackFileError` here — extend the shared `run`
   wrapper's `except` chain (see below) so the two map to exit 2 and exit 3
   respectively, consistent with the design (`developers-guide.md`: "catching
   these two errors (or extending the runner's `except` chain)").
2. Source chapters (Work item 3). A bad `--chapter` raises the usage fault.
3. `report = detect(pack, chapters)`.
4. Build `CommandOutcome`:
   - `code = ExitCode.SUCCESS if report.passed else ExitCode.ACTIONABLE_FINDING`.
   - `result` carries the machine payload: `pack`, `total_words`, and a
     `findings` list of `{rule_id, count, threshold, basis, density, passed,
     lines:[{chapter,line}]}` per design §3.1 ("rule ids and hit counts" belong
     in `result`). Include a top-level `violations` list naming only the failed
     rule ids (the checker read shape, design §3.3 — `desloppify` is a checker).
     **Emit `basis` as an explicit string** (`finding.basis.value`), not the raw
     `RuleBasis` member: `render_machine` calls `json.dumps(ordered)` with no
     `default=` handler (`contract/envelope.py:147`), so although a `StrEnum`
     member serializes as its bare value today, a future change of `RuleBasis`
     to a non-`str` Enum would silently break the contract. The snapshot test
     (Work item 5) asserts `result.findings[].basis` is a `str` to pin this.
   - `messages` carries human prose: one line per failed rule, or "no slop
     detected" on a clean pass.

Extend the runner so the two loader errors reach the right codes. Preferred
approach (keeps `desloppify` declarative and shares the translation): add two
`except` arms to `novel_ralph_skill/contract/runner.py:run` —
`RulePackError → emit USAGE_ERROR (exit 2)` and
`RulePackFileError → emit STATE_ERROR (exit 3)` — guarded so they import from
`rulepack.errors` only inside the `except` (or via a small shared
error-classification map). **If** touching `runner.py` would breach the
interface tolerance or perturb the four other commands, the fallback is to
catch both inside `_desloppify` and convert to `CommandOutcome`(exit 2) /
`StateInputError`(exit 3) respectively. Decide at implementation time and
record in the Decision Log; pin the chosen path with a runner test either way.
The usage fault for a bad `--chapter` is raised as `CycloptsError`-equivalent —
prefer raising a `RulePackError`-free dedicated exit-2 path: return
`CommandOutcome(code=ExitCode.USAGE_ERROR, …)` directly from `_desloppify`
(usage faults the body detects, not the parser, are still the body's to map).

Replace the stub: in `novel_ralph_skill/commands/stub.py`, change
`desloppify()` to the real wiring (mirroring `novel_state()`):

        def desloppify() -> None:
            human, residual = parse_global_flags(sys.argv[1:])
            from novel_ralph_skill.commands import _desloppify
            run(
                _desloppify.build_app(),
                residual,
                RunContext(
                    command=_NAME_FOR["desloppify"],
                    working_dir=WORKING_DIR_NAME,
                    human=human,
                ),
            )

Update `tests/test_command_stubs.py` and `tests/test_console_scripts_e2e.py`'s
`_STILL_STUBBED_NAMES`/`STILL_STUBBED_ENTRY_POINTS` to drop `desloppify` from
the still-stubbed set (it now behaves like `novel-state`: it resolves
`./working/` and exits per its own contract, not the stub's `2`).

Stage C tests (`tests/test_desloppify_command.py`, in-process, the
`test_novel_state_check.py` pattern with `monkeypatch.chdir` + `capsys` +
`run`):

- Clean `working/` (drafts with no offenders) → envelope `ok:true`, empty
  `violations`, exit `0`.
- A draft with an em-dash flood (≥6 per 300 words) → `ok:false`, the em-dash
  rule named in `violations`, exit `4`.
- `desloppify --pack <malformed-content>` (reuse
  `tests/data/rulepacks/bad-pattern.toml`) → exit `2`.
- `desloppify --pack <absent path>` → exit `3`.
- `desloppify --chapter 99` (manifest has fewer) → exit `2`.
- Absent `./working/` → exit `3`.
- The `--help` path exits `0` with no envelope (the shared wrapper behaviour).

Validation: `make all`.

Skills/docs: `python-router` → `python-errors-and-logging`,
`python-types-and-apis` (the optional-keyword Cyclopts signature, already used
by `set_cursor`); review ADR-003, design §3.1-§3.2, §4.4; reread `runner.py`,
`novel_state.py`, `stub.py`, and `test_cyclopts_contract.py` (the four pinned
Cyclopts 4.18.0 behaviours this wiring rests on).

### Work item 5 — Snapshot, error-path, e2e tests, and docs

This item completes design §9's coverage for `desloppify`: snapshot the
machine-mode envelope, assert `--human` presence, pin the exit-code boundaries,
and prove the installed script end-to-end.

Snapshot tests (`tests/test_desloppify_snapshots.py`, `syrupy`, following
`tests/test_contract_envelope_snapshots.py`): snapshot the machine-mode JSON
envelope for (a) a clean pass and (b) a manuscript with exactly one rule one
hit past threshold (the design §9 "hit exactly at threshold / clean pass"
boundary pair). Normalize `working_dir` to the fixed constant; there are no
timestamps or absolute paths in this envelope, but assert that invariant in the
test so a future addition cannot silently churn the snapshot. Pair each
snapshot with semantic assertions (AGENTS.md snapshot rules — the snapshot is
never the only check): assert the exit code and `violations` contents; assert
`result.findings[].basis` is a `str` (the round-1 RuleBasis-serialization
advisory); and assert the `lines` list is in deterministic order (ascending
`chapter`, then ascending `line`, the `finditer` left-to-right +
ordered-chapter invariant) so an ordering change cannot silently churn the
snapshot.

End-to-end test (extend or mirror `tests/test_console_scripts_e2e.py`, marked
`slow`, `@pytest.mark.timeout(180)`, POSIX-only per ADR-006): build the wheel,
install into a throwaway venv, materialize a `working/` tree with a manifest
and one offending draft, then run the installed `desloppify` **by absolute
path** through a cuprum catalogue that **registers that exact path**. The
registration is the gate: `sh.make(prog, catalogue=…)` calls
`catalogue.lookup(prog)` (`cuprum/sh.py:make`), which raises
`UnknownProgramError` unless `prog` is in the catalogue, so the test reuses the
existing `single_program_catalogue` fixture (`tests/conftest.py`) to build a
one-`ProjectSettings` catalogue whose `programs` tuple is exactly
`(Program(str(script_path)),)`. Then
`sh.make(prog, catalogue=catalogue).run_sync(capture=True)` and assert exit `4`
plus the offending rule id in stdout JSON — proving the packaged
`offenders.toml` travels in the wheel (Risk "pack not in wheel"). A clean tree
exits `0`.

Docs:

- `docs/users-guide.md` — move `desloppify` out of the "still stubs" list;
  document its behaviour (default §6 pack, `--chapter N`, optional `--pack`,
  exit codes 0/4/2/3, `--human`), mirroring the `novel-state check` entry.
- `docs/developers-guide.md` — extend the "Rule packs and the loader boundary"
  section: note that task 5.1.2 ships the first pack (`offenders.toml`),
  resolved via `importlib.resources`, and that `desloppify` is the detect-only
  checker built on `load_rulepack` + `detect`.
- `docs/roadmap.md` — tick `5.1.2` (and the slice-4 success line) once landed.
- Confirm no design-doc change is needed (this task implements §4.4/§6.1 as
  written; if implementation discovers a design gap, record it in the design
  doc per AGENTS.md and note it here).

Validation: `make all`; then `make markdownlint` and `make nixie` for the
markdown edits.

Skills/docs: `python-router` → `python-testing` (syrupy snapshots, e2e);
`commit-message` for each commit; review AGENTS.md snapshot/e2e rules, design
§9, ADR-006 (POSIX-only e2e).

## Concrete steps

Run everything from the worktree root
`/data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-5-1-2`.

Per work item:

1. Create the failing test(s) first; run the focused subset and watch it fail:

       uv run pytest tests/test_rulepack_detect.py -q

   Expect failures (collection error or assertion) before the module exists.

2. Implement the production change; rerun the focused subset to green:

       uv run pytest tests/test_rulepack_detect.py -q

3. Run the full gate before committing:

       make all

   Expect: `make all` runs `build check-fmt lint typecheck test` and reports no
   Ruff, interrogate (100% docstring), Pylint, `ty`, or pytest failures.

4. For items touching markdown (Work item 5):

       make markdownlint
       make nixie

   Expect both to pass with no diagnostics.

5. Commit the atomic change with an imperative subject (≤50 chars) and a
   wrapped body explaining what and why, citing the design section and roadmap
   task. Gate every commit on a green `make all`.

Example expected envelope for a failing scan (Work item 4), single line:

    {"command":"desloppify","schema_version":1,"ok":false,"working_dir":"working",
     "result":{"pack":"offenders","total_words":312,"violations":["em-dash"],
     "findings":[{"rule_id":"em-dash","count":7,"threshold":5,"basis":"per_page",
     "density":6.73,"passed":false,"lines":[{"chapter":1,"line":3}, …]}]},
     "messages":["em-dash exceeds threshold (density 6.73 > 5 per 300 words)"]}

## Validation and acceptance

Acceptance is the three observable behaviours from Purpose, each phrased as a
runnable check.

Quality criteria (what "done" means):

- Tests: `make all` passes, including the new
  `tests/test_rulepack_detect.py`, `tests/test_offenders_pack.py`,
  `tests/test_desloppify_sourcing.py`, `tests/test_desloppify_command.py`,
  `tests/test_desloppify_snapshots.py`, and the extended e2e. Each new
  exit-code test fails before its work item and passes after.
- Lint/typecheck: `make check-fmt`, `make lint` (Ruff + interrogate at 100% +
  Pylint), `make typecheck` (`ty`) all green. No file over 400 lines.
- Markdown: `make markdownlint` and `make nixie` pass on the edited docs.
- Behaviour (manual spot check, from a tmp dir with a materialized `working/`):
  - `desloppify` over clean prose prints `ok:true` and `echo $?` is `0`.
  - `desloppify` over an em-dash-flooded draft prints `ok:false`, names
    `em-dash` in `result.violations`, and `echo $?` is `4`.
  - `desloppify --pack /no/such.toml`; `echo $?` is `3`.
  - `desloppify --chapter 99`; `echo $?` is `2`.

Quality method (how we check): run `make all` after each work item; run the
manual spot check after Work item 5 against a throwaway `working/` tree (the
e2e automates this).

## Idempotence and recovery

Every step is re-runnable. `desloppify` writes nothing, so re-running it cannot
drift state. Tests use `tmp_path`/`monkeypatch.chdir`, leaving no residue. If a
work item's `make all` fails, fix forward (the change is uncommitted until the
gate is green); no rollback of disk state is needed because nothing outside the
working tree is mutated. The e2e builds into `tmp_path` and is self-cleaning.

## Artefacts and notes

To be filled with concise transcripts as work proceeds (the failing-then-passing
`pytest` runs, the `make all` summary, and the e2e exit-`4` transcript that
proves the packaged pack travels).

## Interfaces and dependencies

Prescriptive end-state interfaces:

- `novel_ralph_skill/rulepack/detect.py`:

        def detect(
            pack: novel_ralph_skill.rulepack.RulePack,
            chapters: collections.abc.Sequence[ScannedChapter],
        ) -> DetectionReport: …

  with frozen `RuleFinding`, `LineHit`, `DetectionReport`, `ScannedChapter`
  dataclasses as specified in Work item 1.

- `novel_ralph_skill/commands/_desloppify.py`:

        def build_app() -> cyclopts.App: …
        def _desloppify(
            *, chapter: int | None, pack: pathlib.Path | None
        ) -> CommandOutcome: …
        # importlib.resources resolver for the shipped pack
        def offenders_pack_path() -> pathlib.Path: …

- `novel_ralph_skill/commands/stub.py`: `desloppify()` rewired to the real app
  via the shared `run` wrapper.

- `novel_ralph_skill/rulepack/packs/offenders.toml`: the shipped §6 pack
  (`schema_version = 1`, `pack = "offenders"`).

Dependencies (all already present): stdlib `re`, `pathlib`,
`importlib.resources`, `dataclasses`, `enum`; existing `cyclopts` (4.18.0,
behaviour pinned by `tests/test_cyclopts_contract.py`); the existing
`novel_ralph_skill.rulepack`, `.contract`, `.state`, `.commands` packages.
`cuprum` (0.1.0) and `syrupy` (5.2.0) are **test-only**. No new dependency is
added; if one becomes necessary, stop and escalate (Tolerances).

## Revision note

Round 4 (2026-06-24). Revised to resolve the single round-4 design-review
blocking point (`couldnt-help-but` pack comment contradicted its own pattern —
the same defect-class as round-1 defect 2, a `# why` comment asserting a
behaviour the regex lacks). The comment claimed "couldn't / couldnt / could not
all caught", but the pinned pattern `(?i)\bcould\s?n'?t help but\b` does not
match "could not help but" (verified against Python `re`: contraction forms
match, "could not" does not — the `o` of "not" breaks the `\s?n'?t` fragment):

- **NARROWED to the §6 literal (option a).** The §6 table row and the §1
  canonical example are both the contraction ("couldn't help but"), so the
  pattern is kept and the contradictory comment is corrected to state that the
  expanded hedge "could not help but" is deliberately out of scope for this §6
  row. This mirrors the existing `verb-ed-adverb`/"said sadly" out-of-scope pin
  rather than ballooning the faithful §6 transcription.
- **Decision Log entry added** recording the contraction-only reading, the
  verified `re` behaviour, why widening was rejected, and noting that the
  correct widening (had it been chosen) is
  `(?i)\bcould(?:\s?n'?t| not) help but\b` — not the review's candidate
  `\bcould\s?n(?:'?t| not) help but\b`, which is itself buggy (verified to
  still miss "could not help but").
- **Negative test pinned** in Work item 2's `tests/test_offenders_pack.py`
  matrix: "couldn't help but" and "couldnt help but" → ≥1 hit; "could not help
  but" → 0 hits, so the out-of-scope reading is tested, not merely asserted in
  the pattern comment.

Round 3 (2026-06-24). Revised to resolve the single round-3 design-review
blocking point (`found-herself` silently dropped the "+ verb" part of its §6
row, an unpinned reinterpretation matching the bare reflexive):

- **`found-herself` pattern now requires the "+ verb" continuation.** The pinned
  pack pattern changed from
  `(?i)\bfound (?:her|him|them|my|our|your)sel(?:f|ves)\b` (which matched the
  bare reflexive "found herself.") to
  `(?i)\bfound (?:her|him|them|my|our|your)sel(?:f|ves)[^\S\n]+\w` — a
  newline-safe required following word token, the regex-expressible proxy for
  "+ verb" (verified during planning: matches "found herself wondering", "found
  herself walking", "found himself drawn"; rejects "found herself.", "found
  himself!", "found herself, alone", and the non-reflexive "found her keys").
  `[^\S\n]` keeps the continuation on the same physical line, consistent with
  the line-by-line scan.
- **Decision Log entry added** recording the deliberate narrowing of "+ verb"
  to "+ following word token" (stdlib `re` has no POS engine, same constraint
  as the capitalized-abstract-noun row), with the threshold-2 tolerance
  rationale — mirroring the three existing placeholder decisions (shivers,
  verb-ed-adverb, capitalized-noun).
- **Explicit positive/negative tests pinned** in Work item 2's
  `tests/test_offenders_pack.py` matrix: three positives, four single-line
  negatives (including the exact round-2 false positive "found herself."), and
  one multi-line negative pinning the v1 single-line scope.

Round 2 (2026-06-24). Revised to resolve all four round-1 design-review
blocking defects (`docs/execplans/roadmap-5-1-2.review-r1.md`):

- **Defect 1 (incomplete pack):** Work item 2 is now spec-first. The complete
  24-row pack is pinned verbatim as a TOML block (every `id`, `pattern`,
  `threshold`, `basis`, with §6-verbatim thresholds), so the work item is pure
  transcription. The canonical 24-id set is enumerated and a table-driven test
  asserts the loaded rule-id set *equals* it. All 24 patterns were validated
  during planning against positive and negative fixtures.
- **Defect 2 (unpinned/contradictory placeholders):** `shivers-down-spine`
  (`[her]` → possessive/article set) and `verb-ed-adverb` are now pinned. The
  Decision Log records that `verb-ed-adverb` is the literal §6 reading and that
  the §4 "X said with adverbs" tell ("she said sadly", which does not end in
  `-ed`) is deliberately out of scope; a test asserts the rule matches "smiled
  sadly" and **not** "said sadly".
- **Defect 3 (multi-token spans):** detection now scans **line by line**
  (`splitlines()` + per-line `finditer`), multi-token offenders use a bounded
  lazy non-newline window `[^\n]{0,N}?` instead of greedy `.*`, and v1's
  single-line scope is recorded as an explicit limitation. Work item 1 adds a
  multi-line negative and a cross-sentence negative (both verified to yield
  zero hits) plus a single-line positive.
- **Defect 4 (mis-stated cuprum claim):** the Decision Log now describes the
  real mechanism — `cuprum/sh.py:make` (line 528) calls `catalogue.lookup`
  (line 538), which raises `UnknownProgramError` for any unregistered program
  (`cuprum/catalogue.py` line 79); the e2e works because
  `single_program_catalogue` (`tests/conftest.py`) **registers** the exact
  absolute-path `Program`. The false "allowlist admits any string" claim is
  removed; `allowlist` is correctly described as a read-only `frozenset`
  property.

Round-1 advisories also folded in: exit-3 cases cited against design §9 (not
scope creep); `basis` emitted as `.value` and asserted as a `str` in the
snapshot; `recount_words` returns counts not text (only conventions reused);
spaced-en-dash out of scope; snapshot ordering invariant asserted. No open
forks remain.

Initial draft (2026-06-24, superseded above): `desloppify` does not shell out
(design §9) so cuprum is test-only; the §6 pack ships inside the package and is
resolved with `importlib.resources`; scope is `--chapter N` or whole manuscript
off the `[chapters]` manifest; loader errors map to exit 2/4/3 via the shared
`run` wrapper (or a body fallback, pinned by a runner test).

## Addenda (post-merge follow-ups)

Lightweight addendum work items folded back onto this completed task from the
post-merge reviews and audit of step 5.1. Execute each as a small addendum
pass — no plan or design-review cycle: make the change, run `make all` (plus
`make markdownlint`/`make nixie` for Markdown), `coderabbit review --agent`,
commit, and tick the matching roadmap sub-task on merge. The substantial
forward-looking output-contract items (slimming the clean-pass payload, adding a
matched-text span per hit, and giving `RuleFinding`/`LineHit` a canonical
projection) were re-routed to roadmap step 7.1 (tasks 7.1.3–7.1.5) because they
enrich the per-hit contract the §7.1 packs inherit rather than confirming the
settled step-5.1 detection-as-versioned-data hypothesis; the chapter-draft
shared-reader consolidation was re-routed to the new roadmap step 7.10. These
four are the small doc fixes, the localized test refactor, and the coverage gap
only.

- [x] 5.1.2.1 — Document the per-page density behaviour on short or near-empty
  drafts (from review:5.1.2, low; merges the two near-identical density-surprise
  proposals). The §4.5 density formula lets a single `per_page` offender trip the
  threshold on a sub-page draft because a partial page still counts; add a
  one-paragraph note to the `desloppify` users'-guide section so an operator
  scanning an early or short chapter is not surprised by the design-correct
  extrapolation. (An optional minimum-page floor was weighed and left out of this
  lightweight pass: the behaviour is design-correct, so documentation suffices.)
  Gate with `make markdownlint` and `make nixie`.
- [x] 5.1.2.2 — Tighten the snapshot volatile-field guard from a bare slash check
  to a path/timestamp pattern (from review:5.1.2, low).
  `tests/test_desloppify_snapshots.py`'s `_assert_no_volatile_fields` asserts no
  `/` appears in the rendered envelope, so a future rule id, pack name, or
  message carrying a slash would fail spuriously; replace the bare slash check
  with a regex matching absolute-path or timestamp shapes so the guard stays
  durable across packs. Test-only. Gate with `make all`.
- [x] 5.1.2.3 — Reconcile the per-hit `phrase` wording across design §4.4, the
  roadmap, and the emitted envelope (from review:5.1.2, low). The envelope emits
  the rule's authored pattern source under `phrase` while `rule_id` is the
  canonical slug; reconcile the design §4.4 and roadmap 5.1.2 "phrase, count,
  density…" wording (and the users'-guide gloss) with the shipped contract so the
  §7.1 ai-isms and device-ledger packs inherit an unambiguous per-hit output
  vocabulary. Doc-only; the code contract is unchanged here (a matched-text span
  is the separate 7.1.4 reroute). Gate with `make markdownlint` and `make nixie`.
- [x] 5.1.2.4 — Correct the "cannot drift from `recount_words`" docstrings under
  `--chapter` scope and test the per-page density message branch (from
  audit:5.1.2, medium; merges audit Findings 3 and 4). `detect`'s "cannot drift
  from `recount_words`" docstrings are misleading because `--chapter N` computes
  per-page density over one chapter, not the manuscript total; reword them to
  name the actual scope. Add a focused test for the untested per-page density
  branch of `_finding_message` (`commands/_desloppify_report.py`). Both are
  localized to the 5.1.2 surface. Gate with `make all`.
