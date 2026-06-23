# Post-merge audit — roadmap task 1.3.4

Audit of the codebase after roadmap task 1.3.4 ("Extract shared
`EnvelopeMessagesError` base for domain errors") merged to `main` at commit
`08fa690`. The slice introduces
[`contract/errors.py`](../../novel_ralph_skill/contract/errors.py): a single
`EnvelopeMessagesError` base in the neutral `contract` layer that records
`self.messages: tuple[str, ...]` once. `StateInputError`
([`contract/runner.py`](../../novel_ralph_skill/contract/runner.py)),
`RulePackError`, and `RulePackFileError`
([`rulepack/errors.py`](../../novel_ralph_skill/rulepack/errors.py)) now
subclass it, with `RulePackError` adding `rule_id`. The base is re-exported from
[`contract/__init__.py`](../../novel_ralph_skill/contract/__init__.py) and
guarded by
[`tests/test_contract_errors.py`](../../tests/test_contract_errors.py).

The slice is sound and discharges its goal: the three domain exceptions now fan
out from one base, pinning the cross-layer dependency direction
(`rulepack` → `contract`, never the reverse; design §3.1, ADR-003). The unit
tests pin the round-trip, the `Exception` base, the dual import path, the
subclass relationships, the sibling independence of the two rule-pack errors,
and the per-subclass payload. None of the findings below is a blocking defect;
they are tidy-up, consistency, and coverage opportunities.

Trail followed: explored with `leta` (`show`, `grep`, `files`) over the
`contract` and `rulepack` packages, `_freeze.py`, `commands/novel_state.py`,
and `tests/test_contract_errors.py`; traced history with `git show 08fa690` and
`git log origin/main`. Source of truth consulted:
`docs/novel-ralph-harness-design.md` §3.1, `docs/adr-003-shared-interface-contract.md`,
`docs/developers-guide.md`, and `AGENTS.md`. Each finding records a category, a
location, a description, a concrete proposed fix, and a severity.

## Finding 1 — Redundant `list(exc.messages)` round-trip in the runner

- Category: ergonomics
- Severity: low
- Location:
  [`novel_ralph_skill/contract/runner.py`](../../novel_ralph_skill/contract/runner.py)
  line 206 (and the analogous `messages=[str(exc)]` shape at line 199).

`run` translates a caught `StateInputError` with
`CommandOutcome(code=ExitCode.STATE_ERROR, messages=list(exc.messages))`. After
1.3.4, `exc.messages` is already an immutable `tuple[str, ...]` recorded by the
`EnvelopeMessagesError` base, and `CommandOutcome.__post_init__` immediately
re-freezes whatever sequence it receives through `freeze_sequence` (which calls
`tuple(...)`). The explicit `list(...)` therefore allocates a throwaway list
that is copied straight back into a tuple — a needless round-trip that also
slightly obscures the fact that the payload is already in its final immutable
form.

Proposed fix: pass `messages=exc.messages` directly (the field accepts any
`collections.abc.Sequence[str]`, and a tuple satisfies it). This removes the
redundant allocation and makes the immutable-throughout intent legible. If a
defensive copy is still wanted at the seam, prefer the shared
`freeze_sequence(exc.messages)` over an ad-hoc `list(...)` for consistency with
the rest of the contract layer.

## Finding 2 — Developers' guide does not mention the shared base

- Category: docs-gap
- Severity: low
- Location:
  [`docs/developers-guide.md`](../../docs/developers-guide.md) (the exit-code
  channel prose around lines 254–257 and the rule-pack error prose around
  lines 437–445).

The guide describes `StateInputError`, `RulePackError`, and `RulePackFileError`
as three independent channels, but 1.3.4 unified their `messages` storage under
`EnvelopeMessagesError`. A reader of the guide cannot learn that the three
errors now share a base, where that base lives, or why the dependency points
`rulepack` → `contract`. The base is currently documented only in the ExecPlan,
the roadmap, and the module docstring of `contract/errors.py`. The design doc
(§3.1) is the authority for the `messages` contract but predates the extraction,
so it too omits the shared base.

Proposed fix: add a short paragraph to the developers' guide (in the contract
section that already covers `StateInputError`) noting that the three domain
errors subclass a single `EnvelopeMessagesError` base in
`novel_ralph_skill.contract.errors`, that the base owns the `messages` storage
once, and that the subclassing pins the cross-layer dependency direction. A
one-line cross-reference from the design §3.1 `messages` discussion to ADR-003
and the base would keep the source-of-truth chain intact.

## Finding 3 — `EnvelopeMessagesError` stores `messages` without the shared `freeze_sequence` helper

- Category: inconsistency
- Severity: low
- Location:
  [`novel_ralph_skill/contract/errors.py`](../../novel_ralph_skill/contract/errors.py)
  line 40, against
  [`novel_ralph_skill/_freeze.py`](../../novel_ralph_skill/_freeze.py) and the
  `__post_init__` of `CommandOutcome`/`Envelope` in
  [`contract/runner.py`](../../novel_ralph_skill/contract/runner.py) and
  [`contract/envelope.py`](../../novel_ralph_skill/contract/envelope.py).

Every other contract-layer `messages` field is frozen through the shared
`freeze_sequence` normaliser (`CommandOutcome.__post_init__`,
`Envelope.__post_init__`). The base instead relies on the incidental fact that
`*messages` varargs already arrives as a `tuple`, assigning
`self.messages: tuple[str, ...] = messages` directly. The module docstring even
calls this "the freeze-on-construct decision", yet it does not route through the
one helper that names that decision elsewhere. The behaviour is correct today
(varargs are always tuples), but the codebase now has two ways of expressing
"freeze a messages sequence", and a future refactor that changed the base to
accept a `Sequence[str]` parameter (rather than varargs) could silently drop the
immutability guarantee.

Proposed fix: either (a) add a brief comment on the assignment noting that
`*messages` is already an immutable tuple so no `freeze_sequence` call is needed,
explicitly tying the line to the shared freeze convention; or (b) if the base is
ever generalised to take a `Sequence[str]`, store
`self.messages = freeze_sequence(messages)` so the one normaliser owns the
guarantee. Option (a) is the lighter-touch fix for the current varargs API.

## Finding 4 — No test pins the base's empty-messages and immutability guarantees

- Category: test-gap
- Severity: low
- Location:
  [`tests/test_contract_errors.py`](../../tests/test_contract_errors.py).

The new unit suite is thorough on round-trip, hierarchy, and per-subclass
payload, but it does not assert two properties the base and its docstring imply:
that constructing with no messages yields an empty tuple
(`EnvelopeMessagesError().messages == ()`), and that the stored `messages`
attribute is genuinely immutable (a `tuple`, not a list aliased from a caller).
The "is an immutable tuple" claim is asserted only for the two-element case via
`isinstance(..., tuple)`; the zero-argument boundary — the common shape for a
fault with no extra prose — is untested.

Proposed fix: add a `test_empty_messages_round_trip` asserting
`EnvelopeMessagesError().messages == ()` and that `RulePackError(rule_id="r")`
(no positional prose) yields `messages == ()` with `rule_id == "r"`. This pins
the zero-prose path the runner exercises whenever a fault carries only an exit
code.

## Summary

The 1.3.4 extraction is clean, well-tested, and correctly directed across the
`contract`/`rulepack` boundary. The findings are all low-severity polish: one
redundant allocation in the runner seam, one documentation gap in the
developers' guide, one consistency note on the freeze idiom, and one
boundary-case test gap. No finding blocks the slice or threatens the contract.
