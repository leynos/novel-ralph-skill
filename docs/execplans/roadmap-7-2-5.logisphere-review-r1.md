# Logisphere design review — roadmap 7.2.5, round 1

Verdict: PROCEED (no blocking defects). Adversarial review against real source.

## What was verified against the codebase (not the planner's summary)

- `contract/errors.py`: `EnvelopeMessagesError.__init__(self, *messages)` stores
  `self.messages: tuple[str, ...]`. Matches the plan's Stage A go/no-go premise
  exactly, so the base-mixin shape needs no re-derivation.
- `rulepack/errors.py` / `ledger/errors.py`: both are the structural twins the
  plan describes — `RulePackError(*messages, rule_id=None)` /
  `LedgerError(*messages, device_id=None)`, plus bare `*FileError`. Confirmed.
- `loaderkit/load.py:206`: `file_error: cabc.Callable[[str],
  EnvelopeMessagesError]`. The file-error subclasses keep a one-arg call; the
  contract holds when they subclass `PackFileError` (still an
  `EnvelopeMessagesError`).
- `loaderkit/coerce.py:57`: `content_error: Callable[[str, str | None],
  EnvelopeMessagesError]`. The bound type targets the base, not the concrete
  class, so an intermediate `PackError` base does not break `ty`.
- `_coerce.py` bindings (rulepack:33, ledger:37) construct the content error with
  the package id keyword via lambda. Unchanged by the plan. Confirmed.
- Catch sites: `_desloppify.py:258/263` and `_desloppify_ledger.py:83/88` catch
  by concrete name (`except RulePackError` / `except RulePackFileError`), never
  the new shared base. No too-broad arm is introduced.
- Import-direction guard: `tests/test_loaderkit_scan.py:285` globs
  `package_dir.glob("*.py")` — it picks up `errors.py` automatically. The plan's
  claim is correct; the belt-and-braces assertion in Work item 4 is optional but
  harmless.
- `test_contract_errors.py:58-72` already pins `issubclass(RulePackError,
  EnvelopeMessagesError)` and the non-subclassing of `RulePackError`/
  `RulePackFileError`; both still hold after the refactor and run unchanged.
- `interrogate fail-under = 100` (pyproject.toml:309) confirmed — D-STATIC-CLASSES
  is correctly motivated: a runtime `type()` synthesizer would fail the gate.
- Pylint runs `disable=["all"]` with an enable allowlist; `R0903`
  (too-few-public-methods) and `R0801` (duplicate-code) are NOT enabled, so the
  empty `PackFileError` and thin `PackError` will not trip lint.
- Ruff selects `D` and `ANN`; the empty-bodied file-error subclass with a literal
  docstring and the annotated thin `__init__` satisfy both.
- Citations checked: design §6/§6.3, ADR-001/003, developers-guide ~line 1779
  ("parameterized on an error factory"), roadmap 7.2.5 entry, and the 8.1.9 seam
  all say what the plan claims.
- D-NO-EXTERNAL-RESEARCH is correct: this task touches only stdlib + the
  `contract` layer. No cuprum shell execution, no Cyclopts/pytest-timeout/uv
  behaviour. The firecrawl/cuprum-pinning obligation does not apply.

## Panel findings

- Pandalump (structure): boundaries hold. `loaderkit` stays a neutral leaf; the
  acyclic `pack -> loaderkit -> contract` direction is preserved and guarded.
- Telefono (contracts): the two callable contracts (`file_error`,
  `content_error`) are typed against `EnvelopeMessagesError`, so inserting an
  intermediate base is contract-safe. Public names, keywords, attributes, and
  exit-code mapping are untouched.
- Doggylump (failure modes): pre-mortem — the realistic failure is a snapshot
  diff caused by an accidental message-string change. The plan forbids
  `--snapshot-update` and runs the rulepack/ledger/cross-command suites
  unchanged, which is the correct tripwire. No 03:00 page risk: pure refactor,
  no runtime path changes.
- Buzzy Bee / Dinolump: no scaling or long-term-viability concerns; this REDUCES
  the per-family cost the 8.1.9 seam will pay.

## Advisory (non-blocking)

- ADVISORY-1 (Wafflecat / honest accounting): the `PackError` content-error base
  earns very little. The plan itself concedes each subclass keeps a literal
  `__init__(self, *messages, rule_id=None)` that calls `super().__init__()` and
  assigns the attribute — byte-identical to today's direct
  `EnvelopeMessagesError` subclass. The only genuine deduplication is
  `PackFileError` (the empty file-error base). The plan is honest about this
  ("not the elimination of the two tiny id-bearing inits"), and the roadmap
  mandates the shared home for the 8.1.9 seam regardless, so this is acceptable.
  But Work item 1 should ensure `PackError` provides at least one real shared
  affordance (e.g. a documented `record_offending_id` helper that the thin
  `__init__` delegates to) so the `_SampleError(PackError)` test pins something
  the bare `EnvelopeMessagesError` does not already give. If the chosen "minimal
  mechanism" is just inheriting `EnvelopeMessagesError.__init__` unchanged, then
  `PackError` is a pure marker and the test asserts nothing new — flag that
  honestly in the Decision log rather than over-claiming deduplication.

- ADVISORY-2 (PLR6301): if the shared affordance on `PackError` is a method that
  does not use `self`, Ruff `PLR6301` (no-self-use) is enabled and will flag it.
  Prefer an instance method that genuinely uses `self` (it will, since it stores
  the id), or accept that the base is a marker. Settle this in Work item 1
  against `make lint`, as the plan already says.

- ADVISORY-3 (ledger symmetry gap, pre-existing): there is no
  `not issubclass(LedgerError, LedgerFileError)` assertion anywhere in the suite
  (only the rulepack equivalent in `test_contract_errors.py`). The plan does not
  introduce this gap (the four classes stay distinct literal `class` statements),
  but Work item 3 is the natural place to close it cheaply, mirroring the
  rulepack pins. Optional.

## Trail for the next agent

Design §6/§6.3 and ADR-001/003 (neutral leaf, acyclic layering);
developers-guide "The shared loader primitives (`loaderkit`)" ~line 1779;
roadmap 7.2.5 + the 8.1.9 seam; precedent execplan roadmap-7-2-2 (D-FACTORY).
Source verified: `contract/errors.py`, `rulepack/errors.py`, `ledger/errors.py`,
`loaderkit/{__init__,load,coerce}.py`, `commands/_desloppify*.py`,
`tests/test_loaderkit_scan.py` (guard), `tests/test_contract_errors.py`,
`tests/test_loaderkit_coerce.py` (sentinel idiom). Skill: logisphere-design-review.
