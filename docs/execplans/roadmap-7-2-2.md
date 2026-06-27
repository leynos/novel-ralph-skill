# Consolidate the rule-pack and device-ledger loader and scan primitives

This ExecPlan (execution plan) is a living document. The sections `Constraints`,
`Tolerances`, `Risks`, `Progress`, `Surprises & Discoveries`, `Decision Log`,
and `Outcomes & Retrospective` must be kept up to date as work proceeds.

Status: DRAFT (round 2 — round-1 design review resolved; see Revision note)

## Purpose / big picture

Roadmap task 7.2.2 removes a near-verbatim duplication that today spans the
`novel_ralph_skill/rulepack/` and `novel_ralph_skill/ledger/` packages. Six
primitives are cloned between them, differing only in their typed error channel
and a noun ("rule"/"rule pack" versus "device"/"device ledger"):

1. the whole scalar-coercion family in each package's `_coerce.py` — `_where`,
   `_reject_unknown_keys`, `_require`, `_require_str`, `_require_int` (the
   `ledger/_coerce.py` module docstring itself calls this "a deliberate
   near-copy");
2. the array-of-tables extractor `_entries` in each `parse.py`;
3. the eager pattern compiler `_compile_pattern` in each `parse.py`;
4. the duplicate-id rejector `_reject_duplicate_ids` in each `parse.py`;
5. the `load_*` file-fault body in each `parse.py` (the `try/open/tomllib.load`
   wrapped in an `(OSError, TOMLDecodeError)` → `*FileError` translation); and
6. the per-line scan `_scan_rule` / `_scan_device` in each `detect.py` (these
   two are byte-identical apart from the parameter name).

The roadmap entry's success criterion is precise: "one shared module owns the
coercion, entry-extraction, pattern-compilation, duplicate-id, file-fault, and
per-line scan primitives; both the rule-pack and ledger packages consume them
rather than carrying near-verbatim copies; **each package's typed error type,
exit-code mapping, and operator messages are unchanged**; and the rule-pack and
ledger suites stay green." The whole difficulty of the task is that last
clause: the two packages must keep raising **their own** `RulePackError`/
`RulePackFileError` versus `LedgerError`/`LedgerFileError` (the command bodies
route on the exception *type*), and must keep their own per-noun message prose,
**while** the body of each primitive lives in exactly one place.

The mechanism this plan commits to is **error-factory parameterisation**, the
exact phrasing the roadmap and the existing `ledger/_coerce.py` docstring use:
each shared primitive takes a small bundle of callables and nouns that decide
*how* to raise and *what to call the offending thing*, and is otherwise sole. A
caller in the `rulepack` package binds the bundle to `RulePackError` with
"rule"/"rule pack" nouns; a caller in the `ledger` package binds it to
`LedgerError` with "device"/"device ledger" nouns. A third pack family (roadmap
§8.1's per-novel packs) then inherits the primitives by binding one more bundle
instead of cloning a third copy.

After this change a reader can observe success three ways. First, exactly one
definition of each of the six primitives survives, in a new shared leaf module
(`novel_ralph_skill/loaderkit/`, see Decision D-HOME); the former per-package
copies are gone, and the package `_coerce.py`/`parse.py`/`detect.py` modules
are visibly shorter, holding only their schema-specific glue. Second, **every
existing rule-pack and ledger test stays green with no change to its assertions
and no snapshot regeneration** — the loaders raise the same typed errors with
the same `rule_id`/`device_id` payloads and the same message strings, and the
detectors produce identical reports. Third, a new unit test pins the shared
primitives' contract directly — that each one raises *whatever error the bundle
supplies* with the bundle's noun, proving the parameterisation is the single
seam a third pack family would bind — so the primitives cannot silently re-fork.

This is a pure refactor. No new command, flag, library, dependency, schema
field, envelope key, exit code, or observable message is introduced, and no
loader or detector output changes for any input either package accepts today.

## Constraints

Hard invariants that must hold throughout implementation. Violation requires
escalation, not a workaround.

- Each package keeps its own two typed failure channels and their semantics:
  `RulePackError`/`RulePackFileError` (exit 2 / exit 3) and `LedgerError`/
  `LedgerFileError` (exit 2 / exit 3). The command bodies catch on the concrete
  type (design §3.2, §10; `rulepack/errors.py`, `ledger/errors.py` docstrings),
  so a shared primitive must **never** raise a generic or cross-package
  exception that leaks past the boundary; it raises only what the caller's
  factory supplies. The `RulePackError(rule_id=...)` and
  `LedgerError(device_id= ...)` constructor kwargs and the
  `EnvelopeMessagesError` base are unchanged.
- Operator message prose is byte-for-byte unchanged for every fault either
  loader raises today. The per-id prefix stays `rule '<id>'` / `device '<id>'`
  and the per-level prefix stays `rule pack` / `device ledger` (the `_where`
  output); every "must be a string/integer", "missing required key", "unknown
  key(s) … allowed keys are …", "invalid pattern", "is defined more than once",
  "must be an array of tables", "array is empty", and "cannot read … at …"
  message is reproduced verbatim. The existing loader suites assert substrings
  of *most* of these (`tests/test_rulepack_loader.py`,
  `tests/test_ledger_command.py`), so wording drift in those branches reddens a
  suite. **Caveat (round-2 finding):** the three `entries` messages ("must be
  an array of tables", "array is empty …", "at index N must be a table") and
  the duplicate-id message are **not** asserted by any existing test (verified:
  only `tests/test_rulepack_loader.py:315` asserts the substring
  `"array of tables"`, which the `array_key` substitution preserves; the
  empty-array, at-index, and duplicate-id strings have no existing pin).
  Therefore the new `loaderkit` unit tests (work item 2) MUST pin these four
  message strings **in full, verbatim, for both noun sets**, so the shared
  primitives cannot drift them silently. The empty-array message in particular
  carries three independent lexical axes — the quoted array key (`'rule'`/
  `'device'`), a **container noun** (`pack`/`ledger`), and an **item noun**
  (`rule`/`device`) — none of which routes through the `_where` prefix, so
  `entries` is parameterised on the *full* message strings (Decision
  D-ENTRIES), not on the `CoercionErrors` noun pair. A drift here is the
  escalation signal.
- The loaders stay read-only and detect-only (ADR-001): they compile patterns
  with the standard-library `re` (no flags) and validate structure, never
  judging prose, never calling `sys.exit`, never building an envelope. The
  shared scan primitive scans line by line with `re.Pattern.finditer` exactly
  as both detectors do today (the `.` cannot cross `\n` discipline;
  `rulepack/ detect.py` and `ledger/detect.py` module docstrings; design §6.1,
  §6.3).
- Package layering is respected (design §3.1; ADR-003). The new shared module
  depends only on the `contract` layer (for the `EnvelopeMessagesError` type it
  type-hints against) and the standard library; it must **not** import
  `rulepack`, `ledger`, `state`, or `commands`, so both packages may depend on
  it without a cycle. (`ledger` already depends on `rulepack.detect` for
  `ScannedChapter`/`LineHit`; this plan does not add to or rely on that edge —
  see Decision D-SCANTYPES.)
- The `ScannedChapter`/`LineHit` shapes the scan primitive reads and writes stay
  defined in `rulepack/detect.py` and are **not** moved (moving them is a wider
  change outwith this task; the `ledger` package already imports them from
  `rulepack.detect`). The shared scan takes the precompiled `re.Pattern[str]`
  and the `ScannedChapter` sequence and returns the
  `(count, tuple[LineHit, ...])` pair both `_scan_*` produce today.
- This task touches **no** `cuprum` API. `cuprum` is the harness's subprocess
  catalogue/runner; both the rule-pack and device-ledger loaders and detectors
  are pure in-process `tomllib`/`re` code that never shells out (verified:
  `grep -rn cuprum novel_ralph_skill/rulepack novel_ralph_skill/ledger` returns
  nothing). No catalogue, allowlist, executable-path, or run/output option is
  in scope. There is no `cuprum` claim to pin because the plan leans on none.
- This task leans on **no** external-library behaviour beyond the standard
  library it already uses (`tomllib`, `re`, `collections.abc`, `typing`) and
  the in-repo `novel_ralph_skill.contract.errors.EnvelopeMessagesError` base.
  `tomllib.load` and `re.compile`/`re.Pattern.finditer` behaviour is unchanged
  because the plan *moves* the existing calls verbatim, not rewrites them.
  There is therefore no Cyclopts, `uv run`, or `pytest-timeout` behaviour to
  research: the plan adds no CLI surface, no new test-timeout, and no new
  dependency.
- en-GB Oxford spelling ("-ize"/"-yse"/"-our") in all prose, comments,
  docstrings, and commit messages (AGENTS.md).
- No code file exceeds 400 lines (AGENTS.md). The new shared module is split
  into small leaves if needed (coercion, scan) to stay well under the cap; the
  per-package modules only shrink.

## Tolerances (exception triggers)

- Scope: if the change touches more than 16 files or more than ~520 net lines,
  stop and escalate. (Expected: 2-3 new shared-module files plus 1-2 new test
  files; edits to `rulepack/_coerce.py`, `rulepack/parse.py`,
  `rulepack/detect.py`, `ledger/_coerce.py`, `ledger/parse.py`,
  `ledger/_fields.py`, `ledger/detect.py`; and two docs. The reroutes *remove*
  lines; the net add is the shared module, its tests, and the docs notes.)
- Interface: the shared primitives' public signatures are fixed by this plan
  (see `## Interfaces and dependencies`). If a consumer needs a different
  signature than the bundle-plus-args shape specified, stop and escalate rather
  than improvising a second shape.
- Behaviour: if **any** existing rule-pack or ledger test requires an assertion
  edit, an error-type change, or a snapshot regeneration (`--snapshot-update`)
  to pass, stop and escalate — that signals an observable change this refactor
  must not cause. The single permitted test change is the *addition* of new
  tests pinning the shared primitives.
- Dependencies: if any new external dependency is required, stop and escalate.
- Iterations: if `make all` still fails after 3 fix attempts on a work item,
  stop and escalate.
- Scope creep into the schema-specific logic: the `_resolve_basis`,
  `_resolve_page_words`, and `_rule` glue (rulepack) and the `_rationing_fields`
  / `_window`/`_window_offenders` glue (ledger) are **schema-specific**, not
  duplicated, and stay in their packages. If unifying tempts the implementer to
  fold any of these into the shared module, stop — that is outwith this task.
- Scope creep into moving `ScannedChapter`/`LineHit`: if the scan-primitive work
  tempts a move of these shapes out of `rulepack/detect.py`, stop and escalate
  (a wider re-layering, not this task).

## Risks

    - Risk: an error-factory abstraction that raises through an indirect callable
      changes the exception's traceback origin or drops the `rule_id`/`device_id`
      payload, so a command body that catches on type or reads `.rule_id` breaks
      subtly.
      Severity: high
      Likelihood: medium
      Mitigation: the factory bundle's raise callable is the package's own
      `RulePackError`/`LedgerError` constructor (bound with its id kwarg), so the
      raised instance is exactly today's type carrying today's payload. The
      shared primitive `raise`s the *instance the factory returns* with
      `raise factory.error(msg, offending_id) from exc` where relevant, so the
      `from exc` chaining (`re.error`, `OSError`/`TOMLDecodeError`) is preserved.
      Work item 1's unit tests assert: (a) a sentinel error subtype supplied by a
      test bundle is the type raised; (b) the offending id reaches the raised
      instance; and (c) the existing loader suites — which assert `.rule_id`/
      `.device_id` and message substrings — stay green unchanged after each
      reroute. Each reroute work item ends with the package's full suite green.

    - Risk: message prose drifts when the `_where`-equivalent prefix moves into a
      shared helper parameterised on a noun pair, because a mis-ordered or
      mis-quoted noun changes `rule '<id>'` to `rule "<id>"` or `rule pack` to
      `rulepack`.
      Severity: high
      Likelihood: medium
      Mitigation: the shared prefix helper takes the *exact* two noun strings
      each package uses today (`("rule", "rule pack")` and
      `("device", "device ledger")`) and reproduces the `f"{noun} {id!r}"` /
      bare-level form verbatim; the implementer copies the format string from the
      existing `_where`, not retypes it. The existing tests assert the offending
      id and key appear in the message (`"broken" in message`,
      `"thresold" in message`); a new shared-helper unit test pins the full
      prefix strings for both noun pairs. Any drift reddens the loader suites.

    - Risk: the three `entries` messages and the duplicate-id message drift
      because they are NOT covered by any existing test (verified round 2: only
      `tests/test_rulepack_loader.py:315` asserts the substring `"array of
      tables"`; the empty-array, at-index, and duplicate-id strings have no
      existing pin), and the empty-array message's **container noun**
      (`pack`/`ledger`) and **item noun** (`rule`/`device`) are NEITHER of the
      `CoercionErrors` nouns (`per_id_noun` = `rule`/`device`, `per_level_noun` =
      `rule pack`/`device ledger`). A bundle-only `entries` would therefore emit
      `"a rule pack must declare at least one rule"` for the rule pack instead of
      the verbatim `"a pack must declare at least one rule"`, and no gate would
      catch it.
      Severity: high
      Likelihood: high (if left bundle-only)
      Mitigation: `entries` is parameterised on the FULL verbatim message strings,
      not the noun pair (Decision D-ENTRIES): each caller passes its own three
      format strings (or a tiny `EntriesMessages` bundle carrying them), copied
      byte-for-byte from the existing `_entries`. None of the three routes through
      `where`. Work item 2's new `loaderkit` unit tests pin all three `entries`
      strings AND the duplicate-id string in full, for BOTH noun sets, so any
      drift reddens the new suite even though no existing suite covers them
      (closes the round-1 silent-drift hazard). See Work item 2 and D-ENTRIES.

    - Risk: the file-fault body's message differs between the two packages
      (`"cannot read rule pack at {path}"` versus
      `"cannot read device ledger at {path}"`), so a naive shared `load_*` would
      collapse the two nouns and change one package's message.
      Severity: medium
      Likelihood: medium
      Mitigation: the shared file-load primitive takes the noun phrase
      (`"rule pack"` / `"device ledger"`) and the `*FileError` factory as
      parameters and returns the decoded mapping (or raises the supplied
      `*FileError`); the per-package `load_rulepack`/`load_ledger` wrap it,
      passing their own noun and error type and then delegating to their own
      `parse_*`. The two messages stay distinct because the noun is a parameter.
      Pinned by the existing `test_absent_file_is_the_state_channel` /
      `test_undecodable_toml_is_the_state_channel` and the ledger equivalents.

    - Risk: blind import removal. After deleting a package's private `_coerce`
      copy, that package's `parse.py` (and, for the ledger, `_fields.py`) still
      import `_Mapping`, `_where`, `_require`, `_require_int`, `_require_str`,
      and `_reject_unknown_keys` from the old leaf; the import lines must be
      repointed at the shared module (or at a thin per-package binding), not
      deleted outright, or `ty check`/Ruff F401 fails.
      Severity: medium
      Likelihood: medium
      Mitigation: each reroute work item names exactly which symbols each module
      imports and from where, and instructs the implementer to confirm with
      `leta refs` / `grep -n '_coerce\|_require\|_where' <file>` before touching
      any import line. `make all`'s Ruff F401 + `ty check` catch a wrong call
      either way. See Decision D-BINDING for the per-package binding shape that
      keeps each `parse.py`'s call sites terse (no bundle threaded through every
      call) while the body lives once in the shared module.

    - Risk: the `ledger/_coerce.py` module docstring explicitly *justifies* the
      near-copy as deliberate (citing an ExecPlan Tolerance trip and a round-1
      review condition); leaving that docstring in place after the consolidation
      leaves a stale, now-false rationale in the tree.
      Severity: low
      Likelihood: high
      Mitigation: the work item that retires the ledger `_coerce` copy rewrites
      or removes that docstring so it no longer claims a deliberate near-copy,
      and the documentation work item records that 7.2.2 superseded the earlier
      "keep a copy" decision (the earlier Tolerance trip was about not editing a
      *frozen* loader; 7.2.2 is the sanctioned consolidation pass).

    - Risk: `interrogate` 100% docstring coverage fails because the new shared
      primitives or their parameter bundle are under-documented.
      Severity: low
      Likelihood: medium
      Mitigation: every new public function and dataclass/Protocol in the shared
      module carries a full NumPy-style docstring (the house style in both
      packages); work item 1 lands them fully documented and `make all` (which
      runs `interrogate`) gates each commit.

## Progress

    - [x] Work item 1: add the shared `loaderkit` coercion primitives and their
      error-factory seam, fully documented, and pin them with a focused unit
      test (the sentinel-bundle contract). (done 2026-06-27: `loaderkit/__init__.py`
      + `loaderkit/coerce.py` with `CoercionErrors`, `where`,
      `reject_unknown_keys`, `require`, `require_str`, `require_int`;
      `tests/test_loaderkit_coerce.py` pins the sentinel-bundle contract and both
      `where` noun pairs. `make all` green. Example tests sufficed — the coercion
      narrowing has a small enumerable type space, so no `hypothesis` property was
      added. CodeRabbit run 1: applied the multi-unknown-key sort fix; skipped the
      class/fixture-grouping suggestion as the flat module-level layout matches the
      existing `tests/` convention.)
    - [x] Work item 2: add the shared `loaderkit` `entries` (with the
      `EntriesMessages` full-string bundle, D-ENTRIES), `compile_pattern`,
      `reject_duplicate_ids` (authoring-order first-duplicate), and file-load
      primitives; pin the empty-array, at-index, and duplicate-id messages
      verbatim for BOTH noun sets (closes review B1/B2/B3). (done 2026-06-27:
      `loaderkit/load.py` holds `EntriesMessages`, `entries`, `compile_pattern`,
      `reject_duplicate_ids`, `load_toml`; `tests/test_loaderkit_load.py` pins the
      not-array, empty-array, at-index, and duplicate-id messages verbatim for both
      the `'rule'`/`pack`/`rule` and `'device'`/`ledger`/`device` sets, the
      first-duplicate-wins behaviour (`["a","b","a","b"]` names `'a'`), and the
      `load_toml` noun + `__cause__` chaining for both nouns. `make all` green.
      CodeRabbit run 2: tightened the missing-array test with a `match=` on the
      require-fault prose; skipped two findings against the frozen review-r1/r2
      artifacts.)
    - [x] Work item 3: add the shared `loaderkit` per-line `scan_pattern`
      primitive (TYPE_CHECKING-only shape import + `line_hit` callable, the single
      D-SCANTYPES mechanism proven against `ty 0.0.51`; closes review B4); pin it
      against the byte-identical `_scan_rule`/`_scan_device` behaviour. (done
      2026-06-27: `loaderkit/scan.py` holds `scan_pattern` with the
      `from __future__ import annotations` + `TYPE_CHECKING`-only
      `ScannedChapter`/`LineHit` import and the `line_hit` callback, so there is no
      runtime `loaderkit → rulepack` edge; `ty check` passes. The body is the
      verbatim `splitlines()`/enumerate/`finditer` loop. `tests/test_loaderkit_scan.py`
      pins the two-hits-one-line, hits-across-chapters, multi-line-negative, and
      scan-order cases plus a `hypothesis` line-attribution property (fast tier,
      `max_examples=100`). `make all` green. CodeRabbit run 3: **rejected** the two
      `splitlines()` → `split("\n")` findings — switching would diverge from the
      frozen `_scan_*` behaviour the task must preserve byte-for-byte (the
      detectors and ledger snapshot stay green precisely because the scan stays
      `splitlines()`-based); the test oracle deliberately mirrors `splitlines()` for
      the same reason. Skipped two findings against the frozen review-r1/r2
      artifacts.)
    - [x] Work item 4: reroute the `rulepack` package onto the shared primitives
      (delete `rulepack/_coerce.py`'s bodies, repoint `parse.py`/`detect.py`),
      package suite green. (done 2026-06-27: `rulepack/_coerce.py` is now a thin
      binding building the `_ERRORS` `CoercionErrors` bundle and re-exporting the
      `_where`/`_require*`/`_reject_unknown_keys` wrappers; `parse.py` calls the
      shared `entries` (with `_ENTRIES_MESSAGES`), `compile_pattern`,
      `reject_duplicate_ids`, and `load_toml`; `detect.py` calls `scan_pattern`.
      Removed the now-unused `re`/`tomllib` imports and moved `cabc` under
      `TYPE_CHECKING`. Structure checks pass: no `re.compile(`/`tomllib.load(`/
      `.splitlines()` survive in rulepack code. Every rule-pack suite stayed green
      with **no** assertion edit and **no** snapshot regeneration (1460 passed).
      `make all` green. CodeRabbit run 4: no code findings; skipped two frozen
      review-r1/r2 artifact findings.)
    - [x] Work item 5: reroute the `ledger` package onto the shared primitives
      (delete `ledger/_coerce.py`'s bodies, repoint `parse.py`/`_fields.py`/
      `detect.py`, rewrite the stale "deliberate near-copy" docstring), package
      suite green. (done 2026-06-27: `ledger/_coerce.py` is now a thin binding
      building the `_ERRORS` `CoercionErrors` bundle (LedgerError /
      "device"/"device ledger") and re-exporting the wrappers `parse.py` and
      `_fields.py` import — its module docstring is rewritten so it no longer claims
      a deliberate near-copy (D-COERCE-DOCSTRING). `_fields.py` needed no edit (the
      binding re-exports `_Mapping`/`_require`/`_require_int`/`_where` unchanged).
      `parse.py` calls the shared `entries` (with `_ENTRIES_MESSAGES`),
      `compile_pattern`, `reject_duplicate_ids`, `load_toml`; `detect.py` calls
      `scan_pattern` reusing the existing runtime `LineHit` import. Structure checks
      pass: no `re.compile(`/`tomllib.load(`/`.splitlines()` survive in ledger code.
      Every ledger suite stayed green including `test_ledger_snapshots.ambr` with
      **no** `--snapshot-update` (1460 passed). `make all` green. CodeRabbit run 5:
      no code findings; skipped three frozen review-r1/r2 artifact findings.)
    - [x] Work item 6: documentation single-home note (design §6 and the
      developers-guide loader/ledger sections) and markdown gates. (done
      2026-06-27: design §6.3 gains a single-home sentence naming
      `novel_ralph_skill/loaderkit/` and the error-factory binding; the
      developers' guide gains a "The shared loader primitives (`loaderkit`)"
      subsection recording the six primitives, the `CoercionErrors` binding seam,
      the `EntriesMessages`/`scan_pattern` twists, the two existing bindings, the
      third-pack-family path, and the supersession of the `ledger/_coerce.py`
      near-copy rationale. Edited the two files directly (no wholesale `make fmt`,
      per the churn trap); wrapped the two pre-existing over-length execplan code
      snippets so `make markdownlint` passes. `make markdownlint`, `make nixie`,
      and `make all` all green. CodeRabbit run 6: no findings on the touched docs;
      skipped three frozen review-r1/r2 artifact findings.)

## Surprises & discoveries

    - Observation: the `TYPE_CHECKING`-only scan-layering mechanism type-checks
      cleanly under the locked `ty 0.0.51`, so the round-1 fallback (a runtime
      cycle broken by a function-local import) is unnecessary.
      Evidence: during round-2 planning a spike module of the exact proposed
      shape — `from __future__ import annotations`; `ScannedChapter`/`LineHit`
      imported only under `typing.TYPE_CHECKING`; signature `scan_pattern(pattern,
      chapters: cabc.Sequence[ScannedChapter], *, line_hit: cabc.Callable[[int,
      int], LineHit]) -> tuple[int, tuple[LineHit, …]]`; body constructing hits
      via `line_hit(...)` — was placed under `novel_ralph_skill/loaderkit/` and
      `make typecheck` printed `ty 0.0.51` then `All checks passed!`. The spike was
      removed afterwards (tree left clean).
      Impact: closes review B4 — Work item 3 and D-SCANTYPES now specify ONE
      mechanism, proven, with no implementation-time fork.

    - Observation: the three `entries` messages and the duplicate-id message are
      not asserted by any existing test; only `tests/test_rulepack_loader.py:315`
      asserts the substring `"array of tables"`.
      Evidence: `grep -rn "array is empty|array of tables|at index|must declare at
      least one|is defined more than once" tests/` returns only that one source
      assertion plus two data-file comments.
      Impact: the round-1 "existing suites catch any drift" safety net does NOT
      hold for `entries`/duplicate-id (review B3); Work item 2 now pins those
      strings verbatim for both noun sets so the new suite catches drift.

## Decision log

    - Decision (D-HOME): the shared primitives live in a **new** top-level
      package `novel_ralph_skill/loaderkit/`, not inside `rulepack` or `ledger`.
      Rationale: the roadmap names "one shared module" that "both the rule-pack
      and ledger packages consume", and explicitly wants "a third pack family
      [to] inherit the primitives instead of cloning a third copy". Placing the
      module inside `rulepack` would make `ledger` (and any future pack) depend
      on `rulepack` for generic coercion — coupling unrelated pack families
      through one — and inside `ledger` would be worse (the rule pack predates
      it). A neutral leaf package depending only on `contract` + stdlib keeps the
      dependency direction clean (design §3.1; ADR-003): `rulepack → loaderkit`,
      `ledger → loaderkit`, both acyclic. The name `loaderkit` reads as "the kit
      of loader primitives" and avoids the misleading `_coerce`-only framing
      (the module also owns scan and file-load primitives). The existing
      `ledger → rulepack.detect` edge (for `ScannedChapter`/`LineHit`) is
      untouched and orthogonal to this decision (D-SCANTYPES).
      Date/Author: 2026-06-27, planning agent (round 1).

    - Decision (D-FACTORY): each shared primitive is parameterised on an
      **error factory**, realised as a small frozen dataclass bundle, not on a
      bare exception class. The bundle carries (1) a `content_error` callable
      `(message: str, offending_id: str | None) -> EnvelopeMessagesError` that
      constructs the package's content error with its id kwarg already bound, and
      (2) the noun pair `(per_id_noun, per_level_noun)` for the message prefix.
      Rationale: the two packages' content errors differ in *both* the type
      (`RulePackError` vs `LedgerError`) and the constructor kwarg name
      (`rule_id=` vs `device_id=`). A bare-class parameter cannot bridge the
      kwarg-name difference; a callable that closes over the kwarg can. The noun
      pair drives the `_where`-equivalent prefix so the message prose is
      parameter-driven, not branched. The roadmap's literal phrase is
      "error-factory-parameterised helpers", which this realises directly. The
      file-load primitive takes the package's *file* error factory separately
      (the `*FileError` has no id kwarg; D-FILELOAD).
      Date/Author: 2026-06-27, planning agent (round 1).

    - Decision (D-ENTRIES): the `entries` primitive is parameterised on the
      **full verbatim message strings**, not on the `CoercionErrors` noun pair.
      The shared body owns only the *structural* logic — `require` the array,
      reject a non-`Sequence` (or `str`/`bytes`), reject an empty array, reject a
      non-`Mapping` entry, and `cast`/return the sequence — and raises
      `errors.content_error(message, offending_id=None)` with whichever message
      string the caller supplied for that branch. The three messages travel as a
      tiny frozen, slotted, keyword-only `EntriesMessages` bundle:
      `not_array: str` (the "must be an array of tables" template, taking the
      observed type name), `empty: str` (the literal empty-array sentence), and
      `non_mapping: str` (the "at index N must be a table" template, taking the
      index and the observed type name). The rule-pack caller binds, verbatim from
      today's `_entries`:
      `not_array="'rule' must be an array of tables, got {type_name}"`,
      `empty="'rule' array is empty; a pack must declare at least one rule"`,
      `non_mapping="rule at index {index} must be a table, got {type_name}"`; the
      ledger caller binds the `'device'`/`ledger`/`device` equivalents.
      Rationale (round-2, closing review B1/B2): the empty-array message has THREE
      independent lexical axes between packages — the quoted array key
      (`'rule'`/`'device'`), a **container noun** (`pack`/`ledger`), and an
      **item noun** (`rule`/`device`). The container noun is NEITHER
      `per_id_noun` (`rule`/`device`) NOR `per_level_noun` (`rule pack`/`device
      ledger`) carried by `CoercionErrors`, so a bundle-only `entries` (the
      round-1 shape) physically cannot reproduce `"a pack must declare at least
      one rule"` byte-for-byte. Verified further (B2): NONE of the three `entries`
      messages call `_where` today — the "must be an array of tables" and "array
      is empty" branches embed the *quoted array key* and the "at index" branch
      embeds the *bare item noun*, never the `where(errors, None)` per-level noun.
      Routing them through `where` (the round-1 WI2 instruction) would inject the
      wrong noun. Passing the full strings is therefore the only drift-proof
      shape; it keeps the structural guards single-homed (the "one home" goal)
      while guaranteeing verbatim prose. `offending_id` is always `None` for these
      pack/ledger-level faults, matching today.
      Alternative considered and rejected: keep a thin per-package `_entries`
      shell calling a shared *structural-only* guard (Wafflecat's A-alt). Rejected
      because the `EntriesMessages` bundle achieves the same verbatim guarantee
      while keeping the empty-array and at-index *control flow* (which order the
      guards run, when each raises) single-homed too; a per-package shell would
      re-fork that control flow, which is exactly what 7.2.2 removes.
      Date/Author: 2026-06-27, planning agent (round 2).

    - Decision (D-BINDING): each package keeps a **thin per-package binding
      module** that constructs its factory bundle once and re-exports terse
      package-local wrappers, so existing call sites in `parse.py`/`_fields.py`
      keep their current ergonomics (`_require_str(entry, key, rule_id=...)`)
      rather than threading a bundle argument through every call.
      Rationale: the loaders call `_require*`/`_reject_unknown_keys` dozens of
      times with the `rule_id=`/`device_id=` keyword. Forcing a `bundle=` arg on
      every call would bloat the call sites and invite drift. Instead each
      package's (now near-empty) `_coerce.py` becomes a *binding*: it imports the
      shared primitives, builds its one bundle, and exposes the same
      underscore-named wrappers the package already imports, each forwarding to
      the shared body with the bound bundle. The package's `parse.py`/`_fields.py`
      import lines change only their *target body* (the shared module via the
      binding), not their *call shape*. This keeps the diff minimal, preserves
      the 400-line cap headroom, and means the shared bodies are the single
      home while the per-package wrappers are one-line forwarders (which a test
      can confirm carry no logic). The keyword name stays `rule_id`/`device_id`
      at the package wrapper so no caller in `parse.py` changes.
      Date/Author: 2026-06-27, planning agent (round 1).

    - Decision (D-FILELOAD): the shared file-load primitive returns the decoded
      `dict[str, object]` (or raises the supplied `*FileError`), and the
      per-package `load_rulepack`/`load_ledger` remain the public entry points
      that call it then delegate to their own `parse_*`. The primitive takes the
      noun phrase (`"rule pack"`/`"device ledger"`) and a
      `file_error: Callable[[str], EnvelopeMessagesError]` factory.
      Rationale: the file-fault body (`try / path.open("rb") /
      tomllib.load / except (OSError, TOMLDecodeError)`) is identical bar the
      noun in the message and the error type. Returning the decoded mapping (not
      the parsed object) keeps the schema-specific `parse_*` call in the package,
      so the primitive carries zero schema knowledge. `load_*` stays the public
      name both `__init__.py`s re-export, so no public surface moves.
      Date/Author: 2026-06-27, planning agent (round 1).

    - Decision (D-SCANTYPES): **one mechanism, decided now (round 2).** The
      `scan_pattern` primitive lives in `loaderkit/scan.py` and takes a
      precompiled `re.Pattern[str]`, the `cabc.Sequence[ScannedChapter]`, and a
      keyword-only `line_hit: cabc.Callable[[int, int], LineHit]` constructor; it
      returns `tuple[int, tuple[LineHit, ...]]`. `loaderkit/scan.py` imports
      `ScannedChapter`/`LineHit` from `rulepack.detect` **only under
      `typing.TYPE_CHECKING`** (used solely in the annotations under `from
      __future__ import annotations`), and at runtime constructs each hit via the
      `line_hit` callable the caller supplies. The shapes are NOT moved. The two
      detectors import `scan_pattern` at module level (no function-local import,
      no runtime cycle).
      Rationale: `_scan_rule` and `_scan_device` are byte-identical apart from the
      parameter name; the loop dereferences `rule.compiled`/`device.compiled`
      before iterating and constructs `LineHit(chapter=…, line=…)`. Passing the
      precompiled pattern plus a `line_hit` callable keeps `scan_pattern` free of
      any `Rule`/`Device` *and* any runtime `rulepack` import, so `loaderkit.scan`
      has **zero** runtime dependency on `rulepack`: the import direction is
      `rulepack.detect → loaderkit.scan` and `ledger.detect → loaderkit.scan`,
      both acyclic, with the shapes referenced only in `TYPE_CHECKING`
      annotations.
      The round-1 plan left two competing mechanisms (TYPE_CHECKING import +
      `line_hit`, versus a runtime `loaderkit.scan → rulepack.detect` import
      broken by a function-local import in `rulepack.detect`). Round 2 picks the
      former and **rejects** the latter: a function-local import to break a
      runtime cycle is the weaker option (it hides a real dependency from the
      module graph and from `ty`'s view). The chosen mechanism is **proven**, not
      asserted: a spike module of exactly this shape (TYPE_CHECKING-only import of
      `ScannedChapter`/`LineHit`, `line_hit: Callable[[int, int], LineHit]`
      parameter, `tuple[int, tuple[LineHit, ...]]` return) was placed under
      `novel_ralph_skill/loaderkit/` and `make typecheck` (`ty 0.0.51`, the locked
      version) reported `All checks passed!` on 2026-06-27; the spike was then
      removed. The caller's `line_hit` is `lambda chapter, line:
      LineHit(chapter=chapter, line=line)`; `ledger/detect.py:34` already imports
      `LineHit` from `rulepack.detect` at runtime, so the ledger reuses that
      import for its lambda and the rule pack constructs `LineHit` from its own
      module-local class. See Work item 3 (now stating the single mechanism) and
      the "scan layering" Risk.
      Date/Author: 2026-06-27, planning agent (round 1; mechanism decided and
      spiked round 2).

    - Decision (D-COERCE-DOCSTRING): the `ledger/_coerce.py` module docstring,
      which today justifies the near-copy as deliberate ("refactoring the
      rulepack helpers to take an error factory — would edit the frozen rule-pack
      loader, which is an ExecPlan Tolerance trip"), is rewritten when the ledger
      copy is retired. 7.2.2 *is* the sanctioned "take an error factory"
      refactor the old docstring foresaw and deferred; the earlier Tolerance
      protected a frozen loader during the ledger's own build, which no longer
      applies once a dedicated consolidation task owns the change.
      Rationale: leaving the old rationale in place would assert a falsehood (a
      deliberate copy that no longer exists). The documentation work item records
      the supersession.
      Date/Author: 2026-06-27, planning agent (round 1).

## Outcomes & retrospective

Completed 2026-06-27. Outcome against Purpose:

- **One shared home per primitive.** All six primitives live once in
  `novel_ralph_skill/loaderkit/`: the coercion family (`where`,
  `reject_unknown_keys`, `require`, `require_str`, `require_int`) and the
  `CoercionErrors` bundle in `coerce.py`; `entries`, `compile_pattern`,
  `reject_duplicate_ids`, `load_toml`, and `EntriesMessages` in `load.py`;
  `scan_pattern` in `scan.py`. The structure greps confirm no `re.compile(`,
  `tomllib.load(`, or `.splitlines()` survives in `rulepack`/`ledger` code; the
  former per-package bodies are gone (the reroutes net-removed ~570 lines).
- **Both packages consume them.** `rulepack` and `ledger` each import `loaderkit`
  in their `_coerce.py` binding, `parse.py`, and `detect.py`; the bindings build
  one `CoercionErrors` bundle each and re-export the terse underscore wrappers.
- **Every typed error, exit-code mapping, and operator message unchanged.** No
  rule-pack or ledger test assertion was edited and no snapshot regenerated
  (`test_ledger_snapshots.ambr` stayed byte-identical); their staying green is the
  contract-preservation proof. The `RulePackError`/`LedgerError` types,
  `rule_id`/`device_id` payloads, and message prose are reproduced verbatim.
- **New tests pin the parameterisation seam.** `tests/test_loaderkit_coerce.py`,
  `tests/test_loaderkit_load.py`, and `tests/test_loaderkit_scan.py` (1460 passed
  overall) pin the sentinel-bundle contract, both `where` noun pairs, the full
  verbatim entries/duplicate-id messages for both noun sets, first-duplicate-wins,
  the `load_toml` noun + `__cause__` chaining, and the scan line-attribution
  invariant (a `hypothesis` property), so the primitives cannot silently re-fork.

Deviations: none of substance. The `coerce.py` merge landed ~250 lines (under the
~320 split threshold), so no split was needed. The `scan_pattern` `splitlines()`
body was deliberately **kept** (CodeRabbit suggested `split("\n")`; rejected to
preserve the frozen detector behaviour). The recurring `make fmt` markdown-reflow
churn was parked to a stash rather than committed, and the two markdown docs were
edited directly per the standing churn-trap guidance.

Surprise: CodeRabbit repeatedly flagged first-person voice in the frozen
`roadmap-7-2-2.review-r1/r2.md` planning artifacts. Those are historical review
snapshots, not part of the 7.2.2 deliverable, so the findings were skipped each
run (recorded in Open issues for a future docs-voice sweep if desired).

## Context and orientation

`novel desloppify` reads versioned TOML configuration so detection rules are
data, not code (design §6). Two sibling pack families exist:

- The **rule pack** (`novel_ralph_skill/rulepack/`, design §6.1-6.2): a
  versioned TOML file of prose-detection rules. Its loader builds a frozen
  `RulePack` of `Rule`s, each carrying a compiled `re` pattern, a `threshold`,
  and a counting `basis`. Faults raise `RulePackError` (malformed content, exit
  2) or `RulePackFileError` (absent/undecodable file, exit 3).
- The **device ledger** (`novel_ralph_skill/ledger/`, design §6.3): a per-novel
  TOML file that rations a novel's signature devices. Its loader builds a frozen
  `DeviceLedger` of `Device`s, each carrying a compiled pattern and a
  rationing constraint (`max_count`, `allowed_chapters`,
  `retired_after_chapter`, `reserved_for_chapter`). Faults raise `LedgerError`
  (exit 2) or `LedgerFileError` (exit 3).

Both packages follow the same `schema.py` → `parse.py` → `detect.py` shape, and
the ledger was built (roadmap 7.1.x) as a deliberate parallel to the rule pack.
That parallelism left the following near-verbatim duplication, which 7.2.2
removes (line numbers are the worktree state on 2026-06-27):

1. **The coercion family** — `novel_ralph_skill/rulepack/_coerce.py` (181 lines)
   and `novel_ralph_skill/ledger/_coerce.py` (193 lines) define the same five
   helpers: `_where(id) -> str` (the message prefix), `_reject_unknown_keys`,
   `_require`, `_require_str`, `_require_int`, plus the `type _Mapping` alias.
   They differ only in raising `RulePackError(rule_id=...)` versus
   `LedgerError(device_id=...)` and in the nouns `"rule"/"rule pack"` versus
   `"device"/"device ledger"`. The `ledger/_coerce.py` *module docstring*
   (lines 10-18) explicitly flags itself as "a deliberate near-copy" and names
   the error-factory refactor 7.2.2 now performs.
2. **`_entries`** — `rulepack/parse.py` lines 68-107 and `ledger/parse.py` lines
   69-107: extract the non-empty `[[rule]]`/`[[device]]` array as a sequence of
   mappings, with identical Sequence/Mapping guards, differing only in the
   array key (`"rule"`/`"device"`), the noun, and the error type.
3. **`_compile_pattern`** — `rulepack/parse.py` lines 110-138 and
   `ledger/ parse.py` lines 110-139: `re.compile(pattern)` wrapped to raise the
   package's
   error naming the offending id on `re.error`.
4. **`_reject_duplicate_ids`** — `rulepack/parse.py` lines 272-295 and
   `ledger/ parse.py` lines 192-215: reject a repeated `id` naming the
   duplicate.
5. **The file-fault body** — `rulepack/parse.py` `load_rulepack` lines 350-392
   and `ledger/parse.py` `load_ledger` lines 270-313: open in binary,
   `tomllib. load`, translate `(OSError, TOMLDecodeError)` into the package's
   `*FileError` with a `"cannot read <noun> at {path}"` message, then delegate
   to `parse_*`.
6. **The per-line scan** — `rulepack/detect.py` `_scan_rule` lines 148-180 and
   `ledger/detect.py` `_scan_device` lines 107-137: byte-identical apart from
   the parameter name; split each chapter into physical lines and accumulate one
   `LineHit(chapter, line)` per `finditer` match, returning `(count, tuple)`.

What is **not** duplicated (and stays in its package): the schema-specific glue
— `rulepack`'s `_resolve_basis`, `_resolve_page_words`, `_rule`, the
`schema_version`/`pack` checks, and the per-page density `_finding`; `ledger`'s
`_rationing_fields`/`_positive_int`/`_allowed_chapters`/`_present_windows`
(`_fields.py`), `_window`/`_window_offenders`/`_finding` (`detect.py`), and the
constraint-combination semantics. These differ in substance, not just nouns, so
they remain in their packages.

Key files:

- `novel_ralph_skill/contract/errors.py` — defines `EnvelopeMessagesError`, the
  base both `RulePackError` and `LedgerError` extend. The shared module
  type-hints against this base only; it constructs no concrete error itself.
- `novel_ralph_skill/rulepack/errors.py`, `novel_ralph_skill/ledger/errors.py` —
  the four typed errors, with `RulePackError(*messages, rule_id=None)` and
  `LedgerError(*messages, device_id=None)` constructors.
- `novel_ralph_skill/rulepack/detect.py` — defines `ScannedChapter` and
  `LineHit`, the scan input/output shapes the ledger detector already imports.

The single-home target is a new package `novel_ralph_skill/loaderkit/`. The
package's public surface (its `__init__.py`) re-exports the shared primitives;
both `rulepack` and `ledger` consume them through thin per-package bindings
(Decision D-BINDING).

Import-graph facts (verified this round with `grep`/`leta`): `rulepack/_coerce`
is imported only by `rulepack/parse.py`; `ledger/_coerce` is imported by
`ledger/parse.py` and `ledger/_fields.py`; `_scan_rule`/`_scan_device` are
private to their `detect.py`; `ledger` already imports `ScannedChapter`/
`LineHit` from `rulepack.detect`; neither package imports the other's
`_coerce`. So every reroute's import is acyclic once `loaderkit` depends only on
`contract` plus the standard library.

Terms used:

- *Error factory*: a callable (here a small frozen dataclass bundle of
  callables and nouns) the caller passes to a shared primitive so the primitive
  raises *the caller's* typed error with *the caller's* noun, without the
  primitive knowing which package it serves.
- *Coercion primitive*: a schema-agnostic helper that reads a key from a decoded
  mapping and narrows its value to a scalar type, converting any missing or
  wrong-typed fault into the caller's content error.
- *Per-line scan*: splitting each chapter into physical lines and running a
  precompiled pattern's `finditer` per line, so line numbers are exact and `.`
  cannot cross `\n` (the v1 single-line-coverage discipline).

## Plan of work

Six atomic, independently committable and gate-passable work items. Items 1-3
land the shared `loaderkit` primitives and their tests **first**, so each
reroute has a verified target; items 4-5 reroute one package each; item 6 is
the documentation single-home note and markdown gates. Each item ends with
`make all` green (items touching markdown additionally run `make markdownlint`
and `make nixie`).

Read before starting any item: this ExecPlan in full; `AGENTS.md` (testing
rules, en-GB spelling, 400-line cap, abstraction/helper sweep policy);
`docs/adr-001-deterministic-judgemental-boundary.md` (read-only, detect-only
loader); `docs/adr-003-shared-interface-contract.md` (the frozen rule-pack
contract and the ledger-as-parallel rationale); design §6.1, §6.2, §6.3 and
§3.1 (layering). Load the `python-router` skill and follow it to the smaller
skills it routes to: `python-types-and-apis` (the factory-bundle signatures,
`Protocol`/`Callable` shapes, and `TypeAlias`), `python-data-shapes` (the
frozen dataclass bundle and the read-only `Mapping` boundary),
`python-errors-and- logging` (the `raise … from …` chaining and the
narrow-`except` discipline the file-load and compile primitives preserve), and
`python-testing` (the sentinel-bundle fixture and parametrization shape). For
the new shared primitives' invariants, load `python-verification` to decide
whether a `hypothesis` property is warranted (see the per-item testing notes);
if it confirms a property adds coverage, load `hypothesis` for the scan
primitive's line-attribution invariant.

### Work item 1: add the `loaderkit` coercion primitives and the factory seam

Implements: roadmap 7.2.2 ("one shared module owns the coercion … primitives …
parameterised on an error factory"); design §6.1 (the validating boundary);
ADR-001 (detect-only); AGENTS.md "Use functions and composition / Abstraction
policy".

Docs to read: `rulepack/_coerce.py` and `ledger/_coerce.py` in full (the bodies
to merge and the near-copy docstring); `contract/errors.py` (the
`EnvelopeMessagesError` base). Skills: `python-router` →
`python-types-and-apis` (the bundle dataclass and `Callable` field types),
`python-data-shapes` (frozen bundle, read-only `Mapping`),
`python-errors-and-logging`, `python-testing`; `python-verification` for the
property-test go/no-go.

Create `novel_ralph_skill/loaderkit/__init__.py` (package docstring naming it
the single home of the schema-agnostic loader primitives both pack families
consume, design §6, ADR-001) and `novel_ralph_skill/loaderkit/coerce.py`
containing:

1. The `type Mapping = cabc.Mapping[str, object]` alias (the shared shape both
   `_coerce.py`s declare today as `_Mapping`).
2. A frozen, slotted, keyword-only dataclass `CoercionErrors` (the factory
   bundle) with fields:
   - `content_error: Callable[[str, str | None], EnvelopeMessagesError]` —
     builds
     the package's content error from `(message, offending_id)`, with the id
     kwarg already bound by the caller (so the bundle hides the
     `rule_id=`/`device_id=` difference).
   - `per_id_noun: str` and `per_level_noun: str` — `"rule"`/`"rule pack"` and
     `"device"`/`"device ledger"`.
   Its docstring records that this is the single seam a pack family binds to
   reuse the coercion bodies, naming the two existing bindings and noting a
   third pack family adds a third bundle, not a third copy.
3. `where(errors: CoercionErrors, offending_id: str | None) -> str` — the
   `_where` body, returning `f"{errors.per_id_noun} {offending_id!r}"` for a
   per-id fault or `errors.per_level_noun` otherwise. Copy the format string
   verbatim from the existing `_where` so prose is byte-identical.
4. `reject_unknown_keys(mapping, allowed, *, errors, offending_id)` — the
   `_reject_unknown_keys` body, raising
   `errors.content_error(msg, offending_id)`.
5. `require(mapping, key, *, errors, offending_id) -> object` — the `_require`
   body.
6. `require_str(mapping, key, *, errors, offending_id) -> str` — the
   `_require_str` body.
7. `require_int(mapping, key, *, errors, offending_id) -> int` — the
   `_require_int` body (including the explicit `bool` rejection).

Every message string is copied verbatim from the existing helpers, with the
prefix produced by `where(errors, …)`. Each function carries a full NumPy-style
docstring (mirroring the existing ones) so `interrogate` stays at 100%.

Export these from `loaderkit/__init__.py` (`__all__`). `loaderkit/__init__.py`
and `loaderkit/coerce.py` each carry a module docstring (advisory A3) so
`interrogate` stays at 100%. The two source files are ~180 lines each and merge
to one ~200-line module, but with the `CoercionErrors` dataclass and full NumPy
docstrings the merged `coerce.py` could grow; **if it lands over ~320 lines,
split by default** — the `CoercionErrors` bundle into `loaderkit/factory.py`
and the helpers into `loaderkit/coerce.py` (each with its own module docstring)
— rather than waiting for the 400-line cap to force a last-minute scramble
(advisory A4). Escalate only if the split itself breaches a Tolerance.

Tests to add (top-level `tests/` per AGENTS.md): a new
`tests/test_loaderkit_coerce.py` with a sentinel-bundle fixture — a
`CoercionErrors` whose `content_error` constructs a test-local
`EnvelopeMessagesError` subclass carrying the id — asserting:

1. `require` returns the value when present and raises the sentinel type naming
   the key and the offending id when absent;
2. `require_str` raises the sentinel naming the non-string field (and the type
   name in the message), and returns the narrowed `str` otherwise;
3. `require_int` rejects `bool` (a TOML `true`) and a `str`/`float`, raising the
   sentinel, and returns the narrowed `int` otherwise;
4. `reject_unknown_keys` raises the sentinel listing the unknown key(s) and the
   allowed set, sorted, and is silent when every key is allowed;
5. `where` produces `"rule 'x'"` for `("rule", "rule pack")` with id `"x"`,
   `"rule pack"` for that pair with `None`, `"device 'y'"` and
   `"device ledger"` for the device pair — pinning both noun pairs verbatim
   (the load-bearing prose claim).

These are example-based unit tests. Consider a `hypothesis` property only if
`python-verification` confirms it adds coverage the examples do not — the
coercion narrowing has a small, enumerable type space, so examples likely
suffice; do not add a property unless it earns its place. Keep any property in
the fast tier.

Validation: `make all`. The new tests fail before `loaderkit/coerce.py` exists
(import error) and pass after; note this red→green in the commit body.

### Work item 2: add the `loaderkit` entries, compile, duplicate-id, and file-load primitives

Implements: roadmap 7.2.2 ("entry-extraction, pattern-compilation,
duplicate-id, file-fault … primitives"); design §6.1, §6.3; ADR-001.

Docs to read: `rulepack/parse.py` `_entries`/`_compile_pattern`/
`_reject_duplicate_ids`/`load_rulepack` and the `ledger/parse.py` equivalents;
`python-errors-and-logging` (the `raise … from exc` chaining). Skills:
`python-router` → `python-types-and-apis`, `python-errors-and-logging`,
`python-testing`.

Add to `loaderkit` (in `loaderkit/load.py`, keeping `coerce.py` focused). The
module needs `import tomllib`, `import re`, `import dataclasses`,
`import collections.abc as cabc`, and — for the `path` annotation under
`from __future__ import annotations` —
`from importlib.resources.abc import Traversable` guarded by
`typing.TYPE_CHECKING` (matching both `load_*` today; advisory A2). It also
needs a module docstring (advisory A3) so `interrogate` stays at 100%.

1. A frozen, slotted, keyword-only `EntriesMessages` bundle (Decision D-ENTRIES)
   carrying the THREE verbatim message templates for the array-extraction
   faults:

   - `not_array: str` — the "must be an array of tables" template, formatted
     with
     the observed type name (today: `"'rule' must be an array of tables, got
     {type_name}"`);
   - `empty: str` — the literal empty-array sentence (today: `"'rule' array is
     empty; a pack must declare at least one rule"`), carrying the array key, the
     container noun, and the item noun all at once — NONE of which the
     `CoercionErrors` noun pair can supply (review B1), so it is passed whole;
   - `non_mapping: str` — the "at index N must be a table" template, formatted
     with
     the index and the observed type name (today: `"rule at index {index} must be
     a table, got {type_name}"`).

   `entries(mapping, *, array_key, messages, errors)` returns
   `cabc.Sequence[Mapping]` — the `_entries` *structural* body only:
   `value = require(mapping, array_key, errors=errors, offending_id=None)`;
   reject a `str`/`bytes` or non-`Sequence` with `messages.not_array`; reject
   an empty `value` with `messages.empty`; reject any non-`Mapping` entry with
   `messages.non_mapping`; else `cast` and return. Each rejection raises
   `errors.content_error(message, None)` (the pack/ledger-level fault,
   `offending_id=None`). The fault **never** routes through `where` — verified
   (review B2): no `entries` message used `_where` today; the strings come
   whole from `messages`. The implementer copies each format string
   byte-for-byte from the existing `_entries` into the per-package
   `EntriesMessages` binding (work items 4/5), not into `loaderkit` (the
   strings are caller-supplied), so the shared body stays noun-free.
2. `compile_pattern(pattern, *, errors, offending_id) -> re.Pattern[str]` — the
   `_compile_pattern` body, `re.compile(pattern)` with `re.error` translated to
   `errors.content_error(msg, offending_id) from exc`, the message produced with
   `where(errors, offending_id)`. (This one DID use `_where` today — the
   per-id "has an invalid pattern" branch — so the noun pair is correct here.)
3. `reject_duplicate_ids(ids, *, errors) -> None` — the `_reject_duplicate_ids`
   body generalised to take an *iterable of ids* (the two callers pass
   `rule.id for rule in rules` / `device.id for device in devices`), so the
   primitive carries no `Rule`/`Device` knowledge. It **preserves
   authoring-order first-duplicate detection** (advisory A1): it iterates the
   ids in order, tracking a `seen: set[str]`, and raises on the FIRST id
   already in `seen` — it must NOT be rewritten with a `Counter`/set-difference
   that could name a different id. It raises `errors.content_error` naming that
   first repeat via `where(errors, id)`, with the verbatim message
   `"{where} is defined more than once; ids must be unique"` (copied
   byte-for-byte from today's `_reject_duplicate_ids`).
4. `load_toml(path, *, noun, file_error) -> dict[str, object]` — the file-fault
   body: open `path` binary, `tomllib.load`, translate
   `(OSError, TOMLDecode Error)` into
   `file_error(f"cannot read {noun} at {path}: {exc}") from exc`, and return
   the decoded mapping. `file_error` is
   `Callable[[str], EnvelopeMessagesError]` (the `*FileError` constructor;
   D-FILELOAD). `path` is typed `Traversable` (the `TYPE_CHECKING`-guarded
   import named above; A2).

Each function fully documented. Export from `loaderkit/__init__.py`.

Tests to add: extend `tests/test_loaderkit_coerce.py` or add
`tests/test_loaderkit_load.py` (whichever keeps each file under 400 lines)
asserting, with sentinel bundles and a sentinel file-error type:

1. `entries` returns the sequence for a valid array, and raises the sentinel for
   a missing array, a non-Sequence, a `str`/`bytes` "array", an empty array,
   and a non-Mapping entry — for **both** the rule-pack `EntriesMessages`
   (array key `"rule"`) and the ledger `EntriesMessages` (array key
   `"device"`). Because NO existing suite asserts the empty-array or at-index
   strings (verified: only `tests/test_rulepack_loader.py:315` asserts
   `"array of tables"`; review B3), this test MUST pin the FULL message strings
   **verbatim** for both noun sets — bind the two `EntriesMessages` bundles
   with the literal strings from `rulepack/parse.py`/`ledger/parse.py` and
   assert the raised `.messages[0]` (or substring-of-the-full-string) equals,
   byte-for-byte:
   `"'rule' array is empty; a pack must declare at least one rule"` and
   `"'device' array is empty; a ledger must declare at least one device"` for
   the empty case; `"rule at index 0 must be a table, got int"` /
   `"device at index 0 must be a table, got int"` for a non-mapping entry; and
   `"'rule' must be an array of tables, got int"` /
   `"'device' must be an array of tables, got int"` for the not-array case.
   This is the load-bearing prose pin that closes the round-1 silent-drift
   hazard (B1/ B3); without it the container-noun (`pack`/`ledger`) drift would
   ship green.
2. `compile_pattern` returns a compiled pattern for a valid regex and raises the
   sentinel (naming the id and embedding the `re.error` text, with `__cause__`
   set) for an invalid one;
3. `reject_duplicate_ids` is silent for distinct ids; for a collision it raises
   the sentinel naming the **first** repeat in authoring order (advisory A1:
   feed `["a", "b", "a", "b"]` and assert the message names `'a'`, not `'b'`,
   proving first-duplicate-wins is preserved), and pins the full message
   verbatim for both noun sets:
   `"rule 'a' is defined more than once; ids must be unique"` and
   `"device 'a' is defined more than once; ids must be unique"` (no existing
   suite asserts this string either; review A1);
4. `load_toml` returns the decoded mapping for a valid TOML file (use
   `tmp_path`), and raises the sentinel file-error (with the noun in the
   message and `__cause__` set) for an absent path and for undecodable bytes —
   for both `noun="rule pack"` and `noun="device ledger"`, pinning the
   `"cannot read {noun} at {path}: …"` prefix for each.

Validation: `make all`. New tests red before the primitives exist, green after.

### Work item 3: add the `loaderkit` per-line `scan_pattern` primitive

Implements: roadmap 7.2.2 ("per-line scan primitives"); design §6.1, §6.3;
ADR-001 (detect-only, line-by-line); the v1 single-line-coverage discipline
(`rulepack/detect.py`, `ledger/detect.py` module docstrings).

Docs to read: `rulepack/detect.py` `_scan_rule` and the module docstring's
per-line rationale; `ledger/detect.py` `_scan_device`;
`python-iterators-and- generators` (the per-line accumulation). Skills:
`python-router` → `python-types-and-apis`, `python-testing`;
`python-verification` → `hypothesis` *if* the line-attribution invariant
warrants a property.

Add `loaderkit/scan.py` with
`scan_pattern(pattern, chapters, *, line_hit) -> tuple[int, tuple[LineHit, ...]]`
where:

- `pattern: re.Pattern[str]` is the precompiled pattern (the caller dereferences
  `rule.compiled`/`device.compiled` before calling, so the primitive holds no
  `Rule`/`Device` knowledge — D-SCANTYPES).
- `chapters: cabc.Sequence[ScannedChapter]` is the scan input.
- `line_hit: Callable[[int, int], LineHit]` constructs a `LineHit` from
  `(chapter_number, line_index)`; the caller passes
  `lambda chapter, line: LineHit(chapter=chapter, line=line)`. This callable
  keeps `loaderkit.scan` from importing `LineHit` at runtime, so the direction
  stays `rulepack.detect → loaderkit.scan` and
  `ledger.detect → loaderkit.scan`, both acyclic. The body is the verbatim
  `splitlines()`-enumerate-`finditer` loop both `_scan_*` share, constructing
  each hit via `line_hit(chapter.number, index)`.

**Single mechanism, decided and proven (round 2; D-SCANTYPES).**
`loaderkit/scan.py` opens with `from __future__ import annotations` and imports
`ScannedChapter`/ `LineHit` from `rulepack.detect` **only under
`typing.TYPE_CHECKING`** (used solely in the `chapters`, `line_hit`, and return
annotations). At runtime it constructs no `LineHit` itself and imports nothing
from `rulepack`, so there is NO runtime `loaderkit → rulepack` edge and NO
cycle; the two detectors import `scan_pattern` at module level (no
function-local import). The round-1 fallback — a runtime
`loaderkit.scan → rulepack.detect` import broken by a lazy import inside
`_scan_rule` — is **rejected** (it hides a real edge from the module graph).
This is not asserted but **verified**: a spike module of exactly this shape was
placed under `novel_ralph_skill/loaderkit/` and `make typecheck` (`ty 0.0.51`,
the locked version) reported `All checks passed!` on 2026-06-27, then the spike
was removed (see Surprises & discoveries and D-SCANTYPES).
`ledger/detect.py:34` already imports `LineHit` from `rulepack.detect` at
runtime, so the ledger's `line_hit` lambda reuses that import; the rule pack's
lambda uses its module-local `LineHit`. Acceptance: `_scan_rule` and
`_scan_device` both call `scan_pattern` and the detect suites (and the ledger
snapshot) stay green.

Fully document the function. Export from `loaderkit/__init__.py`.

Tests to add: `tests/test_loaderkit_scan.py` asserting (constructing
`ScannedChapter`/`LineHit` directly, as `tests/test_rulepack_detect.py` does):

1. a pattern with two hits on one line yields two `LineHit`s with the same line
   number (the `test_two_hits_one_line_carry_same_line_number` invariant);
2. hits across two chapters carry the right chapter number
   (`test_hits_across_chapters_carry_right_chapter`);
3. a multi-line span yields zero hits because `.` cannot cross `\n`
   (`test_multi_line_span_split_yields_zero_hits`) — the load-bearing v1
   discipline;
4. the count equals `len(lines)` and the lines are in scan order (ascending
   chapter, then line, then left-to-right).

`python-verification` go/no-go: the line-attribution invariant ("every emitted
`LineHit.line` equals the 1-based index of the physical line the match fell on,
for arbitrary multi-line chapter text") is a genuine range-of-inputs invariant,
so a `hypothesis` property over generated chapter texts is justified — load
`hypothesis` and add it in the fast tier if `python-verification` confirms.
Keep the example tests regardless.

Validation: `make all`. New tests red before `scan_pattern` exists, green after.

### Work item 4: reroute the `rulepack` package onto the shared primitives

Implements: roadmap 7.2.2 (rule pack is one of the two named consumers);
ADR-003 (the rule-pack contract stays frozen — only its *internal* primitives
move, no schema, error type, message, or exit code changes); design §6.1.

Docs to read: `rulepack/_coerce.py`, `rulepack/parse.py`, `rulepack/detect.py`;
this plan's D-BINDING and D-FACTORY. Skills: `python-router` →
`python-data-shapes`, `python-errors-and-logging`, `python-testing`.

Edits:

1. Replace `novel_ralph_skill/rulepack/_coerce.py`'s bodies with a thin
   **binding** (D-BINDING): import the shared primitives from `loaderkit`,
   build the one `CoercionErrors` bundle —
   `content_error=lambda msg, rid: RulePackError(msg, rule_id=rid)`,
   `per_id_noun="rule"`, `per_level_noun="rule pack"` — and expose the same
   underscore-named wrappers `parse.py` imports today (`_Mapping`, `_where`,
   `_reject_unknown_keys`, `_require`, `_require_str`, `_require_int`), each a
   one-line forwarder binding the bundle (and, for `_where`, forwarding to
   `loaderkit.where`). Keep the `rule_id=` keyword on each wrapper so no call
   site in `parse.py` changes. Rewrite the module docstring: it is now a
   binding of the shared `loaderkit` coercion primitives to the rule pack's
   error channel, not a self-contained leaf.
2. In `novel_ralph_skill/rulepack/parse.py`:
   - define a module-level `_ENTRIES_MESSAGES = EntriesMessages(...)` binding
     the
     THREE verbatim strings copied byte-for-byte from today's `_entries`
     (`not_array="'rule' must be an array of tables, got {type_name}"`,
     `empty="'rule' array is empty; a pack must declare at least one rule"`,
     `non_mapping="rule at index {index} must be a table, got {type_name}"`;
     D-ENTRIES), then replace `_entries`'s body with `loaderkit.entries(raw,
     array_key="rule", messages=_ENTRIES_MESSAGES, errors=<bundle>)` (or delete
     `_entries` and call the shared `entries` directly at the one call site —
     prefer the latter if it keeps `parse.py` terse; confirm the single call site
     with `leta refs _entries`). The strings live at the call site, NOT in
     `loaderkit`, so `loaderkit.entries` stays noun-free (review B1/B2);
   - replace `_compile_pattern`'s body with `loaderkit.compile_pattern(pattern,
     errors=<bundle>, offending_id=rule_id)` (or call the shared one directly);
   - replace `_reject_duplicate_ids`'s body with
     `loaderkit.reject_duplicate_ids((rule.id for rule in rules), errors=
     <bundle>)`;
   - replace `load_rulepack`'s file-fault body with
     `raw = loaderkit.load_toml(path, noun="rule pack",
     file_error=RulePackFileError)` then `return parse_rulepack(raw)`.
   Repoint the imports: the
   `from novel_ralph_skill.rulepack._coerce import (…)` group still imports the
   wrapper names from the binding; add the shared `entries`/`compile_pattern`/
   `reject_duplicate_ids`/`load_toml` imports from `loaderkit` (or via the
   binding). Remove now-unused `re`/`tomllib`/`cabc` imports only if the shared
   calls absorbed every use — confirm with
   `grep -n 're\.\|tomllib\|cabc' novel_ralph_skill/rulepack/parse.py` before
   touching any import line (Risk "blind import removal"). `re` is likely still
   used by `_resolve_basis`-adjacent code and the `re.Pattern` return
   annotation; `tomllib` likely goes once `load_toml` owns the decode.
3. In `novel_ralph_skill/rulepack/detect.py`: replace `_scan_rule`'s body with a
   call to `loaderkit.scan_pattern(rule.compiled, chapters, line_hit=...)`, where
   the `line_hit` is `lambda chapter, line: LineHit(chapter=chapter, line=line)`
   (keep `_scan_rule` as a one-line wrapper if `detect` reads cleaner, or
   inline the call at the single call site in `detect`). Add the module-level
   `from novel_ralph_skill.loaderkit.scan import scan_pattern` import (the
   decided mechanism from work item 3 / D-SCANTYPES needs no function-local
   import; the import is acyclic because `loaderkit.scan` references the shapes
   only under `TYPE_CHECKING`).

Tests to add/update: **no assertion edits.** Every existing rule-pack suite
must stay green unchanged — `tests/test_rulepack_loader.py`,
`tests/test_rulepack_schema.py`, `tests/test_rulepack_properties.py`,
`tests/test_rulepack_detect.py`, and any `desloppify` command suite that loads
a pack. These already assert the typed error, the `rule_id` payload, and
message substrings, so their staying green *is* the proof the reroute preserved
the contract. If any reddens, stop and escalate (Tolerances → Behaviour). No
new rule-pack test is required (the shared primitives are pinned by items 1-3);
add one only if the reroute reveals an untested edge.

Validation: `make all`. Expect every rule-pack suite green with no
`--snapshot-update`.

### Work item 5: reroute the `ledger` package onto the shared primitives

Implements: roadmap 7.2.2 (device ledger is the second named consumer); design
§6.3; supersedes the `ledger/_coerce.py` "deliberate near-copy" rationale
(D-COERCE-DOCSTRING).

Docs to read: `ledger/_coerce.py` (including the now-superseded near-copy
docstring), `ledger/parse.py`, `ledger/_fields.py`, `ledger/detect.py`. Skills:
`python-router` → `python-data-shapes`, `python-errors-and-logging`,
`python-testing`.

Edits, mirroring work item 4 with the ledger's error channel and nouns:

1. Replace `novel_ralph_skill/ledger/_coerce.py`'s bodies with the thin binding:
   bundle `content_error=lambda msg, did: LedgerError(msg, device_id=did)`,
   `per_id_noun="device"`, `per_level_noun="device ledger"`; expose the same
   wrappers `parse.py` and `_fields.py` import (`_Mapping`, `_where`,
   `_require`, `_require_int`, `_require_str`, `_reject_unknown_keys`), each
   forwarding to the shared body with the bundle and the `device_id=` keyword
   preserved. **Rewrite the module docstring** so it no longer claims a
   deliberate near-copy: it is a binding of the shared `loaderkit` coercion
   primitives to the ledger's error channel, and 7.2.2 performed the
   error-factory refactor the old docstring foresaw (D-COERCE-DOCSTRING).
2. In `novel_ralph_skill/ledger/parse.py`: define a module-level
   `_ENTRIES_MESSAGES = EntriesMessages(...)` binding the THREE verbatim ledger
   strings copied byte-for-byte from today's `_entries`
   (`not_array="'device' must be an array of tables, got {type_name}"`,
   `empty="'device' array is empty; a ledger must declare at least one device"`,
   `non_mapping="device at index {index} must be a table, got {type_name}"`;
   D-ENTRIES), then reroute `_entries`
   (`loaderkit.entries(raw, array_key="device", messages=_ENTRIES_MESSAGES, errors=<bundle>)`),
   `_compile_pattern` (`offending_id=device_id`), `_reject_duplicate_ids`
   (`(device.id for device in devices)`), and `load_ledger`'s file-fault body
   (`loaderkit.load_toml(path, noun="device ledger", file_error=LedgerFileError)`),
   then `return parse_ledger(raw)`. Repoint and prune imports as in work item
   4, confirming each with `grep`.
3. `novel_ralph_skill/ledger/_fields.py` imports `_Mapping`, `_require`,
   `_require_int`, `_where` from `ledger/_coerce`; because the binding
   re-exports those names unchanged, `_fields.py` needs **no edit** beyond
   confirming the import still resolves (it imports from the binding, which now
   forwards to `loaderkit`). Confirm with `leta refs` that `_fields.py`'s call
   sites are unaffected.
4. In `novel_ralph_skill/ledger/detect.py`: reroute `_scan_device` onto
   `loaderkit.scan_pattern(device.compiled, chapters, line_hit=...)`, with the
   same `lambda chapter, line: LineHit(chapter=chapter, line=line)` constructor,
   and add the module-level
   `from novel_ralph_skill.loaderkit.scan import scan_pattern` import (the
   decided D-SCANTYPES mechanism; no function-local import). `ledger/detect.py`
   already imports `LineHit` from `rulepack.detect` at runtime (line 34), so the
   `line_hit` lambda reuses that existing import.

Tests to add/update: **no assertion edits.** Every existing ledger suite must
stay green unchanged — `tests/test_ledger_command.py`,
`tests/test_ledger_detect.py`, `tests/test_ledger_properties.py`, and
`tests/test_ledger_snapshots.py` (the detection-report snapshot
`tests/__snapshots__/test_ledger_snapshots.ambr`). The snapshot captures the
detection report, which the scan reroute must leave byte-identical; if it
churns, stop and escalate (Tolerances → Behaviour, no `--snapshot-update`). The
loader suites assert the `device_id` payload and message substrings; their
staying green proves the coercion/file/compile reroutes preserved the contract.

Validation: `make all`. Expect every ledger suite (including the snapshot)
green with no `--snapshot-update`.

### Work item 6: documentation single-home note and markdown gates

Implements: AGENTS.md "Documentation maintenance" / "Abstraction … re-use
policy: record the decision in architecture, design, or developers-guide docs";
design §6 ownership; the §7.2 DoD ("it is documented as the single source of
truth").

Docs to read: design §6.1-6.3; `docs/developers-guide.md` "Rule packs and the
loader boundary" (line ~1403) and "The device ledger and per-novel rationing"
(line ~1608); the existing single-home note style in the developers' guide (the
`tomlkit` array-builder single-home note at line ~1318, added by 7.2.1.1, is
the closest precedent to mirror). Skills: none beyond en-GB; this item is
markdown only.

Edits:

1. In `docs/novel-ralph-harness-design.md` §6 (after §6.3, or in §6.1 where the
   loader boundary is introduced), add a single-home sentence recording that
   the rule-pack and device-ledger loaders share one home for their
   schema-agnostic primitives — `novel_ralph_skill/loaderkit/` (coercion,
   entry-extraction, pattern-compilation, duplicate-id, file-load, and per-line
   scan) — each pack family binding the primitives to its own typed error
   channel via an error factory, so a third pack family inherits them instead
   of cloning a third copy. Keep it to the existing §6 prose density.
2. In `docs/developers-guide.md`, add a short note under (or between) the two
   loader sections recording: the shared `loaderkit` home; the six primitives
   it owns; the `CoercionErrors` factory bundle as the binding seam; the two
   existing bindings (`rulepack`, `ledger`) and how a third pack family adds a
   third bundle; and that 7.2.2 superseded the earlier `ledger/_coerce.py`
   "deliberate near-copy" rationale (the error-factory refactor that earlier
   Tolerance deferred). Mirror the array-builder single-home note's style (line
   ~1318).

Tests: none (documentation only). Validation: `make markdownlint` and
`make nixie` (no Mermaid changes expected, but `make nixie` is required for any
markdown touch per the standing rules), plus `make all` to confirm nothing else
regressed. Do **not** run `make fmt` wholesale (it mdformat-reflows every
tracked markdown file — a known churn trap recorded on prior branches); use
`make markdownlint`/`make nixie` for validation and edit the two files directly.

## Concrete steps

Run all commands from the worktree root
`/data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-7-2-2`.

Per work item:

1. Make the edits described above (use `leta show`/`leta refs` to navigate and
   confirm the call sites and that no import cycle or surviving private copy
   remains; `grep -n 're\.\|tomllib\|cabc\|_coerce' <file>` before touching any
   import line).
2. Run the gate `make all`. Expect the tail to report the Ruff format check,
   `ruff check`, `interrogate` at 100%, Pylint, `ty check`, and `pytest` all
   passing. A representative green tail:

        ==== N passed in T.Ts ====

3. For work item 6 (markdown), additionally run `make markdownlint` and
   `make nixie`. Expect both to exit 0 with no findings.
4. Commit the work item with a file-based message (use the `commit-message`
   skill; never `-m`), en-GB imperative subject ≤ ~50 chars, body explaining
   what and why, noting the red→green for any new test.

After each commit, re-read this plan's `Progress` section and tick the
completed item with a timestamp.

## Validation and acceptance

Quality criteria (what "done" means):

- Tests: `make test` passes; the new `loaderkit` unit tests
  (`tests/test_ loaderkit_coerce.py`, `tests/test_loaderkit_load.py` if split,
  `tests/test_ loaderkit_scan.py`) fail before their primitives exist and pass
  after; **every
  existing rule-pack and ledger suite stays green with no assertion edit and no
  snapshot regeneration** (`tests/test_rulepack_loader.py`,
  `test_rulepack_ schema.py`, `test_rulepack_properties.py`,
  `test_rulepack_detect.py`, `tests/test_ledger_command.py`,
  `test_ledger_detect.py`, `test_ledger_ properties.py`,
  `test_ledger_snapshots.py`).
- Lint/typecheck/format: `make check-fmt`, `make lint` (Ruff + 100%
  `interrogate` + Pylint), and `make typecheck` (`ty check`) all pass.
- Audit: `make audit` (`pip-audit`) passes (no new dependency added).
- Markdown (work item 6): `make markdownlint` and `make nixie` pass.
- Structure: exactly one definition of each of the six primitives exists, in
  `loaderkit`; the former per-package bodies are gone (replaced by one-line
  binding forwarders or removed).

Quality method (how we check) — mechanically checkable, not eyeballed:

1. The shared primitives are defined exactly once each. Each of these greps must
   return **exactly one match**, all under `novel_ralph_skill/loaderkit/`:

        rg -n 'def where\(|def reject_unknown_keys\(|def require\(|def require_str\(|def require_int\(' novel_ralph_skill/loaderkit
        rg -n 'def entries\(|def compile_pattern\(|def reject_duplicate_ids\(|def load_toml\(' novel_ralph_skill/loaderkit
        rg -n 'def scan_pattern\(' novel_ralph_skill/loaderkit

2. The per-package private copies no longer carry a body. In each former copy
   the
   helper either is gone or is a one-line forwarder to `loaderkit`; assert the
   substantive logic moved by confirming the `re.compile(`, `tomllib.load(`, and
   `splitlines()` calls live in `loaderkit`, not duplicated:

        rg -n 're\.compile\(' novel_ralph_skill/rulepack novel_ralph_skill/ledger

   must return **no matches** outside a `re.Pattern` type annotation (the
   `re.compile` call now lives only in `loaderkit/load.py`); confirm by reading
   any hit. Likewise:

        rg -n 'tomllib\.load\(' novel_ralph_skill/rulepack novel_ralph_skill/ledger

   must return **no matches** (the decode lives only in `loaderkit.load_toml`);
   and

        rg -n '\.splitlines\(\)' novel_ralph_skill/rulepack novel_ralph_skill/ledger

   must return **no matches** (the per-line scan lives only in
   `loaderkit/scan.py`).

3. Both packages consume the shared module:

        rg -n 'from novel_ralph_skill.loaderkit|import.*loaderkit' novel_ralph_skill/rulepack novel_ralph_skill/ledger

   must list the binding/parse/detect imports in **both** packages.

4. `leta refs` on each shared primitive lists the two package bindings (and, for
   `scan_pattern`, the two `detect.py` call sites) plus the `loaderkit` tests —
   confirming both pack families reach the body through one symbol. This is the
   companion to checks 1-3, not a substitute.

Acceptance is observable: after the change, both loaders raise byte-identical
typed errors with identical `rule_id`/`device_id` payloads and identical
message prose for every fault, both detectors produce identical reports (every
existing loader and detector suite and the ledger snapshot green without
regeneration), and exactly one home owns each of the six primitives (checks 1-3
pass). Step 7.2's DoD — "the duplication is removed, exactly one canonical
implementation survives under one name, it is documented as the single source
of truth, and a test pins it so it cannot silently re-fork" — is met by the
single `loaderkit` home, the work-item-6 docs notes, and the work-item-1/2/3
unit tests respectively.

## Idempotence and recovery

Every work item is a pure structural refactor with no destructive disk
operation; re-running an item's edits is safe (the edits are idempotent string
replacements, and `make all` is re-runnable). Items 1-3 are additive (new
module, new tests) and land first so each reroute has a verified target. If a
reroute (item 4 or 5) reddens a loader/detector suite or the ledger snapshot,
that is the escalation signal (Tolerances → Behaviour): revert that work item's
commit (`git revert`) and escalate rather than editing the test or regenerating
the snapshot. Because items 4 and 5 reroute distinct packages, a failure in one
does not block committing the other.

## Artifacts and notes

The single load-bearing snippet is the factory bundle and one representative
primitive (the rest follow the same shape — body once, noun/error via the
bundle):

        @dataclasses.dataclass(frozen=True, kw_only=True, slots=True)
        class CoercionErrors:
            content_error: cabc.Callable[[str, str | None], EnvelopeMessagesError]
            per_id_noun: str
            per_level_noun: str


        def where(errors: CoercionErrors, offending_id: str | None) -> str:
            if offending_id is not None:
                return f"{errors.per_id_noun} {offending_id!r}"
            return errors.per_level_noun


        def require_int(
            mapping: Mapping, key: str, *, errors: CoercionErrors,
            offending_id: str | None,
        ) -> int:
            value = require(mapping, key, errors=errors, offending_id=offending_id)
            if isinstance(value, bool) or not isinstance(value, int):
                msg = (
                    f"{where(errors, offending_id)} key {key!r} must be an "
                    f"integer, got {type(value).__name__}"
                )
                raise errors.content_error(msg, offending_id)
            return value

The rule-pack binding (mirrored for the ledger with `LedgerError`/`device_id`/
`"device"`/`"device ledger"`):

        _ERRORS = CoercionErrors(
            content_error=lambda msg, rid: RulePackError(msg, rule_id=rid),
            per_id_noun="rule",
            per_level_noun="rule pack",
        )

        def _require_int(mapping, key, *, rule_id):
            return require_int(mapping, key, errors=_ERRORS, offending_id=rule_id)

## Interfaces and dependencies

No new external dependency. The only libraries involved are the standard library
(`tomllib`, `re`, `collections.abc`, `dataclasses`, `typing`) and the in-repo
`novel_ralph_skill.contract.errors.EnvelopeMessagesError` base — all already in
use; the plan *moves* their existing call sites, introducing no new API
surface. This task uses **no** `cuprum` API (see Constraints).

New package `novel_ralph_skill/loaderkit/`, depending only on `contract` and
the standard library. It defines (final signatures):

        # loaderkit/coerce.py
        type Mapping = cabc.Mapping[str, object]

        @dataclasses.dataclass(frozen=True, kw_only=True, slots=True)
        class CoercionErrors:
            content_error: cabc.Callable[[str, str | None], EnvelopeMessagesError]
            per_id_noun: str
            per_level_noun: str

        def where(errors: CoercionErrors, offending_id: str | None) -> str: …
        def reject_unknown_keys(
            mapping: Mapping, allowed: frozenset[str], *,
            errors: CoercionErrors, offending_id: str | None,
        ) -> None: …
        def require(
            mapping: Mapping, key: str, *, errors: CoercionErrors,
            offending_id: str | None,
        ) -> object: …
        def require_str(
            mapping: Mapping, key: str, *, errors: CoercionErrors,
            offending_id: str | None,
        ) -> str: …
        def require_int(
            mapping: Mapping, key: str, *, errors: CoercionErrors,
            offending_id: str | None,
        ) -> int: …

        # loaderkit/load.py
        # path annotation needs, under TYPE_CHECKING (A2):
        #     from importlib.resources.abc import Traversable
        @dataclasses.dataclass(frozen=True, kw_only=True, slots=True)
        class EntriesMessages:
            not_array: str       # "'<key>' must be an array of tables, got {type_name}"
            empty: str           # "'<key>' array is empty; a <container> must declare …"
            non_mapping: str     # "<item> at index {index} must be a table, got {type_name}"

        def entries(
            mapping: Mapping, *, array_key: str, messages: EntriesMessages,
            errors: CoercionErrors,
        ) -> cabc.Sequence[Mapping]: …
        def compile_pattern(
            pattern: str, *, errors: CoercionErrors, offending_id: str | None,
        ) -> re.Pattern[str]: …
        def reject_duplicate_ids(
            ids: cabc.Iterable[str], *, errors: CoercionErrors,
        ) -> None: …
        def load_toml(
            path: Traversable, *, noun: str,
            file_error: cabc.Callable[[str], EnvelopeMessagesError],
        ) -> dict[str, object]: …

        # loaderkit/scan.py
        def scan_pattern(
            pattern: re.Pattern[str],
            chapters: cabc.Sequence[ScannedChapter], *,
            line_hit: cabc.Callable[[int, int], LineHit],
        ) -> tuple[int, tuple[LineHit, …]]: …

Consumed by:

- `novel_ralph_skill/rulepack/_coerce.py` (binding: builds the `RulePackError`
  bundle, re-exports the underscore wrappers `parse.py` imports);
- `novel_ralph_skill/rulepack/parse.py` (`entries`, `compile_pattern`,
  `reject_duplicate_ids`, `load_toml`, via the binding/shared module);
- `novel_ralph_skill/rulepack/detect.py` (`scan_pattern`);
- `novel_ralph_skill/ledger/_coerce.py` (binding: builds the `LedgerError`
  bundle, re-exports the wrappers `parse.py`/`_fields.py` import);
- `novel_ralph_skill/ledger/parse.py` (`entries`, `compile_pattern`,
  `reject_duplicate_ids`, `load_toml`);
- `novel_ralph_skill/ledger/detect.py` (`scan_pattern`).

`ScannedChapter`/`LineHit` stay defined in
`novel_ralph_skill/rulepack/detect.py` (D-SCANTYPES); `loaderkit/scan.py`
references them **only under `TYPE_CHECKING`** and constructs each hit via the
`line_hit` callable, so `loaderkit.scan` has no runtime `rulepack` import and
the direction `rulepack.detect → loaderkit.scan` /
`ledger.detect → loaderkit.scan` is acyclic. This is the single, decided
mechanism (D-SCANTYPES), proven against `ty 0.0.51` by a removed spike — there
is no implementation-time fork.

The per-package `EntriesMessages` bundles (the three verbatim strings each)
live at the `rulepack`/`ledger` call sites, NOT in `loaderkit`, so
`loaderkit.entries` carries no noun (D-ENTRIES, closing review B1/B2).

## Revision note

Round 1 (2026-06-27): initial draft. Pinned the mechanism to error-factory
parameterisation via a frozen `CoercionErrors` bundle (D-FACTORY) with
per-package thin bindings (D-BINDING), a neutral `loaderkit` home (D-HOME), a
noun-parameter file-load primitive (D-FILELOAD), and a schema-agnostic
`scan_pattern` taking a precompiled pattern and a `line_hit` constructor
(D-SCANTYPES). Verified against the worktree source that the six primitives are
the duplicated set, that the schema-specific glue is genuinely distinct and
stays in-package, that the loaders use no `cuprum` and no external library
beyond stdlib + the `contract` base, and that the existing suites assert on the
typed errors / id payloads / message substrings (so their staying green is the
contract-preservation proof). One sub-decision remains explicitly scoped to
implementation: the precise scan-layering mechanism (TYPE_CHECKING import +
`line_hit` callable, or function-local import to break a runtime cycle) — work
item 3 requires the implementer to pick **one** and record it, not leave both
live.

Round 2 (2026-06-27): resolved all four blocking points from the round-1
Logisphere review (`docs/execplans/roadmap-7-2-2.review-r1.md`).

- B1 (`entries` under-parameterised, cannot reproduce the empty-array message):
  added Decision D-ENTRIES and a new `EntriesMessages` bundle so `entries`
  takes the THREE full verbatim message strings, not the `CoercionErrors` noun
  pair. The empty-array message's container noun (`pack`/`ledger`) is carried
  whole in `messages.empty`, so both packages keep byte-identical prose.
  Updated Constraints, Risks (new entries-drift risk), the Interfaces
  signature, and work items 2/4/5.
- B2 (`where(errors, None)` is the wrong source; entries never used `_where`):
  rewrote work item 2 so the three entries faults raise the caller-supplied
  strings directly and **never** route through `where`; recorded in D-ENTRIES
  and the WI2 primitive description that none of the three messages used
  `_where` today.
- B3 (the safety net does not catch entries drift — no existing test pins those
  messages): work item 2's new `loaderkit` tests now pin the FULL empty-array,
  at-index, must-be-array-of-tables, and duplicate-id messages verbatim for
  both noun sets; recorded the missing-coverage finding in Surprises &
  discoveries and Constraints.
- B4 (two live scan mechanisms; the chosen one unproven against `ty`): picked
  the
  single TYPE_CHECKING-only-import + `line_hit`-callable mechanism, removed the
  function-local-import fallback, and **proved** it type-checks by spiking a
  module of the exact shape under `novel_ralph_skill/loaderkit/` and running
  `make typecheck` (`ty 0.0.51`, `All checks passed!`), then removing the
  spike. Recorded in D-SCANTYPES, Surprises & discoveries, and work items 3/4/5.

Advisories also actioned: A1 (duplicate-id authoring-order first-duplicate
preserved and its message pinned verbatim), A2 (named the
`TYPE_CHECKING`-guarded `from importlib.resources.abc import Traversable`
import for `load_toml`), A3 (named the `load.py`/`scan.py` module docstrings for
`interrogate`), A4 (the `coerce.py` split fallback is the default if the merge
lands over ~320 lines). This round changes no scope, dependency, or public
surface; it only sharpens the `entries` shape, the scan mechanism, and the test
pins.

## Addenda

Surgical follow-ups filed against this completed task. Each runs as a
lightweight, no-plan, no-review addendum pass and is mirrored by a nested
sub-task on the roadmap under task 7.2.2.

- 7.2.2.1 — Harden the `loaderkit` scan property test with an independent
  line-model oracle (from review:7.2.2; low). The Hypothesis property added by
  this task recomputes the expected per-line hits with `splitlines()`, the same
  call `scan_pattern` uses, so it cannot catch a class of line-splitting
  regressions (a future move to `split("\n")` or a universal-newline edge case).
  Add a second property that derives the expected hits from an independent
  newline model, leaving the existing freeze property in place, so the
  line-attribution contract is pinned against the implementation's own splitting
  choice rather than merely echoing it.
