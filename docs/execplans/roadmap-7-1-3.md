# Single-source the `Reconciliation` payload projection

This ExecPlan (execution plan) is a living document. The sections
`Constraints`, `Tolerances`, `Risks`, `Progress`, `Surprises & Discoveries`,
`Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work
proceeds.

Status: DELIVERED

## Purpose / big picture

Today the serialisation of a `Reconciliation` into its `{action,
discrepancies, detail}` payload dict — plus the optional `current`/`by_chapter`
recount pair — is hand-written at four sites across two command modules, even
though `Reconciliation` already has a natural owner in
`novel_ralph_skill/state/reconcile.py` (the module that defines the dataclass
and the one pure `derive_reconciliation` derivation both `check` and `reconcile`
share).

The four sites that independently spell the same dict shape are:

1. `_render_reconciliation`
   (`novel_ralph_skill/commands/novel_state.py:129`) — the read-shaped `check`
   payload: the base three keys plus the recount pair when
   `recounted_by_chapter is not None`.
2. `_write_outcome` (`novel_ralph_skill/commands/_reconcile.py:215`) — the
   write-shaped `reconcile` success `result`: the same base three keys plus the
   same guarded recount pair as `_render_reconciliation`, with one textual
   difference that is value-identical today — `_write_outcome` serialises its
   `action` *parameter* (`str(action)`, line 225), not the attribute
   `str(reconciliation.action)`. Both `_write_outcome` callers pass
   `action == reconciliation.action` (line 322 passes `action`, bound to
   `reconciliation.action` at line 291; line 313 passes the literal
   `RECREATE_LOG`, which equals `reconciliation.action` because
   `derive_reconciliation` builds that `Reconciliation` with
   `action=RECREATE_LOG`, `reconcile.py:332-333`), so the two spellings produce
   the same string and routing through the projection is behaviour-preserving
   (Work Item 3 records the caller invariant; `tests/test_reconcile.py:262` pins
   the literal-passing `RECREATE_LOG` case).
3. `_refuse_outcome` (`novel_ralph_skill/commands/_reconcile.py:237`) — the
   exit-`4` refusal `result`: the base three keys only (a `REFUSE` never carries
   a recount pair).
4. The `NONE` arm of `reconcile`
   (`novel_ralph_skill/commands/_reconcile.py:293`) — the coherent-tree no-op
   `result`: the base three keys with an empty `discrepancies` list inlined.

Because `derive_reconciliation` already guarantees that `check` and `reconcile`
re-derive an *identical* `Reconciliation` for the same tree (Decision Log
D-SHARED, pinned by the cross-check test), the only remaining way the two
commands can drift is by serialising that identical object into *different*
dict shapes. A field added to the reported reconciliation, or a rename of
`discrepancies`, is shotgun surgery across four call sites in two modules, and a
partial edit would silently let `check` and `reconcile` report different shapes
for the same derivation — the very divergence D-SHARED exists to prevent
(audit-2.3.2 Finding 2).

After this change `reconcile.py` owns one canonical projection —
`reconciliation_payload(reconciliation)` (a free function beside the dataclass,
mirroring the module's existing free-function vocabulary `derive_reconciliation`
rather than introducing a method) — that returns the base `{action,
discrepancies, detail}` dict plus the optional recount pair, and all four arms
route through it. The "the read shape and the write shape serialise an identical
`Reconciliation` identically" invariant becomes structurally enforced (one
projection) rather than only test-pinned.

This is deliberately the *serialisation* only. The audit (audit-2.3.2 Finding 2;
carried from audit-2.2.2 Finding 2) is explicit that `check`'s read shape and
`reconcile`'s write shape keep distinct *vocabulary* and *envelope code*: the
exit codes (`check` exits `0`/`4`; `reconcile` success exits `0` and refusal
exits `4`), the `messages` lists, the `CommandOutcome` construction, and the
read-versus-write framing all stay exactly where they are. Only the
`Reconciliation`-to-dict serialisation is centralised.

You can observe success three ways. The observables below are scoped to the
*executable* dict-construction form `"action": str(` — the literal key string
each arm uses to begin the base dict — because that is the duplicated
serialisation this task removes. They deliberately exclude docstring prose that
mentions `action`/`discrepancies`/`detail` (those describe the shape and are
correct to keep).

1. `git grep -n '"action": str(' novel_ralph_skill/` returns exactly one hit,
   inside `reconciliation_payload` in
   `novel_ralph_skill/state/reconcile.py`. None of `novel_state.py`,
   `_reconcile.py` constructs the base dict by hand any more (each calls
   `reconciliation_payload`, then `check`/`reconcile` add only their
   command-specific envelope — `messages`, exit code, and, where they genuinely
   differ, extra `result` keys).
2. `git grep -n 'reconciliation_payload' novel_ralph_skill/` resolves the
   definition to `state/reconcile.py`, the re-export to
   `state/__init__.py`, and exactly four consumer call sites
   (`_render_reconciliation`, `_write_outcome`, `_refuse_outcome`, the `NONE`
   arm).
3. `make all` is green with **no pre-existing test edited for new behaviour**:
   every reconcile, check, disk-evidence, derivation, refusal, integration,
   BDD, e2e, and snapshot suite stays green unchanged, plus one small new test
   that pins the projection (its dict shape across the recount-bearing and
   recount-absent cases). This is a pure no-behaviour-change refactor (roadmap
   7.1.3 success criterion: "no behaviour changes").

## Scope and explicit non-goals

This task is an internal **DRY refactor** of pure Python: it consolidates one
serialisation into `novel_ralph_skill/state/reconcile.py` and routes four arms
in `novel_ralph_skill/commands/` through it. It changes no exit code, no
envelope shape, no message text, no on-disk path, and no public console-script
behaviour.

In scope (roadmap 7.1.3; audit-2.3.2 Finding 2):

- A single free function
  `reconciliation_payload(reconciliation: Reconciliation) -> dict[str, object]`
  in `state/reconcile.py`, beside the `Reconciliation` dataclass, returning the
  base `{action, discrepancies, detail}` dict plus the optional
  `current`/`by_chapter` recount pair when `recounted_by_chapter is not None`.
- Exporting `reconciliation_payload` from
  `novel_ralph_skill/state/__init__.py` beside the existing `Reconciliation` /
  `ReconcileAction` / `derive_reconciliation` exports.
- Routing the four arms through it: `_render_reconciliation`
  (`novel_state.py`), and `_write_outcome`, `_refuse_outcome`, and the `NONE`
  arm (`_reconcile.py`).
- One focused unit test pinning the projection (the base shape; the recount-pair
  extension present iff `recounted_by_chapter is not None`).

Explicit non-goals (other roadmap tasks / audit findings own these; do **not**
touch them):

- The **CQS read/write vocabulary split** between `check`'s `violations` read
  shape and `reconcile`'s write-shaped `result`. The audit is explicit
  (audit-2.3.2 Finding 2; audit-2.2.2 Finding 2): the *envelope code* and *exit
  codes* "genuinely differ" and stay where they are. Only the
  `Reconciliation`-to-dict serialisation is centralised. The read and write
  *framing* docstrings stay (trim only the redundant inline-dict comment, not
  the read/write distinction).
- The **exit-code policy.** `check` exits `0`/`4`; `reconcile` success exits
  `0`, refusal exits `4`. `reconciliation_payload` returns a *dict only* — it
  constructs no `CommandOutcome` and chooses no exit code. The four arms keep
  their own `CommandOutcome(code=…, result=…, messages=…)` construction.
- The `_RECONCILE_PATHS` `working/`-prefix inconsistency (audit-2.3.2
  Finding 3), the call-time `disk_word_counts` import (Finding 4), the
  blended-CQS `edit` callback (Finding 5), and the self-recovery test gaps
  (Finding 6) — none is this task; do not touch them.
- The compile-currency seam (roadmap 7.1.1, delivered) and the
  finding-outcome envelope builder (roadmap 7.1.4).

If, while implementing, it emerges that routing an arm through the projection
forces a behaviour change (an exit code, an envelope field, a message string,
or a snapshot byte to move), **stop and escalate** (see `Tolerances`): the task
is defined as *no behavioural change*, so any required change is a signal the
projection shape is wrong, not licence to edit a snapshot.

## Constraints

Hard invariants that must hold throughout implementation. Violation requires
escalation, not a workaround.

- **No behaviour change.** No exit code, envelope field, `result` key, message
  string, or on-disk path may change. Every existing test must pass **without
  edit** (snapshots included). The roadmap 7.1.3 success criterion is explicit:
  "the CQS read/write vocabulary split and the exit-code policy are unchanged;
  no behaviour changes; and the check, reconcile, and disk-evidence suites stay
  green." (design §3.3, §5.4; ADR-003 shared interface contract.)
- **`reconciliation_payload` lives in `state/reconcile.py`**, beside the
  `Reconciliation` dataclass and `derive_reconciliation` (the module the roadmap
  and audit name: "a small free function beside it in `state/reconcile.py`").
- **It returns a dict, not a `CommandOutcome`.** The projection has no knowledge
  of exit codes, `messages`, or the read/write framing; those stay at the four
  call sites. This preserves the CQS read/write split (non-goals).
- **The base-dict order is preserved** — `action`, then `discrepancies`, then
  `detail`, then (when present) `current`, then `by_chapter` — matching the
  current insertion order at all four sites, and Python dict iteration is
  insertion-ordered. Two distinct mechanisms guard this order, and they cover
  different paths, so read them precisely:
  - The **only** snapshot that pins *insertion order* is
    `tests/__snapshots__/test_novel_state_check_disk.ambr`. It is rendered by
    `render_machine` (`novel_ralph_skill/contract/envelope.py:151`,
    `json.dumps(ordered)` with **no** `sort_keys`) and asserted with
    `raw == snapshot` (`tests/test_novel_state_check_disk.py:234,248`), so the
    code's insertion order leaks through verbatim. Its stored
    `reconciliation` blocks show `{action, discrepancies, detail[, current,
    by_chapter]}` — the code order, not the alphabetical order. This is the
    insertion-order backstop, but it covers **only the READ (`check`) path**
    (it pins both the `recount` and `refuse` classes, but only as `check`
    *reports* them, never the write-side `reconcile` `result`).
  - `tests/__snapshots__/test_reconcile_refuse.ambr` does **not** pin
    insertion order. `tests/test_reconcile_refuse.py:187` asserts
    `json.dumps(env, sort_keys=True) == snapshot`, so the stored bytes are
    **alphabetically sorted** (`{action, detail, discrepancies}` —
    `detail` before `discrepancies`, the opposite of the code's insertion
    order). It pins the *field set* of the write-side `REFUSE` envelope, not
    its order. A reordered projection would still serialise to the same sorted
    bytes and pass this snapshot.
  - The **named primary order pin** for the write-side `REFUSE`/`NONE`
    `result` envelope is therefore the Work Item 2 unit test's
    `list(reconciliation_payload(...).items()) == [...]` ordered assertion. It
    is the *only* check that fails if the write-side projection reorders its
    keys, because no snapshot does (the refuse snapshot is sorted, and the
    `check_disk` snapshot covers only the read path). Do not weaken or remove
    it: without it, a future reorder bug could ship green on the write path.
- **The recount pair is gated exactly as today** — added iff
  `reconciliation.recounted_by_chapter is not None`, with `current` taken from
  `recounted_current` and `by_chapter` from `dict(recounted_by_chapter)`. The
  `REFUSE` and `NONE` arms never carry it (they have no recount pair to add), so
  routing them through the same projection is a behaviour-preserving no-op for
  those keys.
- **Detect-only / mutator boundary unchanged (§3.3, ADR-001):** `check` still
  writes nothing; `reconcile` still drives the same D-SELF bracket. The
  projection is pure (a dict over an immutable dataclass) and touches no disk.
- **en-GB Oxford spelling** ("-ize"/"-yse"/"-our") in all new prose, comments,
  docstrings, and commit messages (workflow standing rule;
  `docs/documentation-style-guide.md`).
- **Quality gates:** 100% docstring coverage (`interrogate`, `pyproject.toml`
  `[tool.interrogate] fail-under = 100`); module line cap 400
  (`[tool.pylint.main] max-module-lines = 400` — `reconcile.py` is at 342 lines,
  so the projection plus its docstring must fit under 400; check after the
  addition); Ruff line-length 88; Markdown prose wrapped at 80 columns
  (AGENTS.md "Markdown guidance").

## Tolerances (exception triggers)

- **Behaviour drift:** if any existing test (including either snapshot
  `.ambr`) must be edited to keep green, stop and escalate — that means the
  projection moved behaviour (Constraints "No behaviour change").
- **Scope:** if the refactor requires editing any module beyond
  `state/reconcile.py`, `commands/novel_state.py`, `commands/_reconcile.py`,
  and `state/__init__.py` (plus adding/extending one test file), stop and
  escalate — it has drifted beyond the four named arms.
- **CQS contamination:** if it appears the projection should also fold in the
  `messages`, the exit code, or the read/write framing, stop and escalate — the
  audit explicitly keeps those distinct (non-goals).
- **Line cap:** if `reconcile.py` would exceed 400 lines after the addition,
  stop and escalate rather than splitting the module ad hoc.
- **Dependencies:** if any new third-party dependency is required, stop and
  escalate. None is expected — this is internal Python with no new imports.
- **Iterations:** if `make all` still fails after 3 focused attempts on a work
  item, stop and escalate.

## Risks

    - Risk: the projection reorders the dict keys (or the recount pair lands
      before ``detail``), so the snapshot-pinned JSON envelope byte moves and a
      ``.ambr`` snapshot fails.
      Severity: high
      Likelihood: medium
      Mitigation: Constraint "base-dict order is preserved" fixes the order
      ``action, discrepancies, detail[, current, by_chapter]`` to match the
      current insertion order at all four sites. The PRIMARY order pin is Work
      Item 2's unit test, which asserts the projection's key order against an
      explicit expected sequence (compared by ``list(payload.items())``, not
      just ``==``, since two dicts compare equal regardless of order). This
      ``items()`` assertion is the **only** order check covering the write-side
      ``REFUSE``/``NONE`` ``result`` envelope, so it must not be weakened.
      The snapshot backstop is asymmetric and covers only part of the surface:
      only ``test_novel_state_check_disk.ambr`` pins *insertion* order (it
      renders through ``render_machine``'s ``json.dumps`` with no ``sort_keys``
      and asserts ``raw == snapshot``), and it covers only the READ (``check``)
      path. ``test_reconcile_refuse.ambr`` does **not** pin order at all: its
      assertion is ``json.dumps(env, sort_keys=True)``, so the stored bytes are
      alphabetically sorted and a reordered projection would still pass it.
      The write-side order is therefore guarded by the Work Item 2 ``items()``
      pin alone — that is why it is named the primary pin.

    - Risk: the projection is introduced but an arm keeps an inline
      ``{"action": str(...), ...}`` (incomplete routing), so the duplication the
      task removes survives at one of the four sites — most easily the inlined
      ``NONE`` arm, which is a literal dict in the ``reconcile`` body rather than
      a named helper.
      Severity: medium
      Likelihood: medium
      Mitigation: the success observation is a ``git grep '"action": str('``
      that must return exactly one hit (the projection's own definition); Work
      Item 3's validation runs it. The ``NONE`` arm is explicitly enumerated as
      the fourth site in Work Item 3.

    - Risk: routing the ``REFUSE`` or ``NONE`` arm through the projection
      accidentally adds the recount pair (or drops the empty ``discrepancies``
      list), changing the refusal/no-op ``result`` shape.
      Severity: high
      Likelihood: low
      Mitigation: the projection gates the recount pair on
      ``recounted_by_chapter is not None``; a ``REFUSE``/``NONE``
      ``Reconciliation`` has ``recounted_by_chapter = None`` (the dataclass
      default), so the projection yields exactly the base three keys for them —
      identical to today. Work Item 2 pins both a recount-bearing and a
      recount-absent case. ``tests/test_reconcile_refuse.py`` (and its snapshot)
      pins the ``REFUSE`` *field set and values* (the ``sort_keys=True``
      assertion catches an added ``current``/``by_chapter`` pair or a dropped
      ``discrepancies`` key — this risk is about the field set, not order, so
      the sorted snapshot is a valid backstop here); the ``NONE`` shape is
      pinned by the reconcile integration/derivation suites.

    - Risk: ``reconciliation_payload`` is added to ``state/reconcile.py`` but not
      exported from ``state/__init__.py``, so the two command modules importing
      from the package surface (``from novel_ralph_skill.state import ...``)
      cannot reach it.
      Severity: low
      Likelihood: medium
      Mitigation: Work Item 1 adds ``reconciliation_payload`` to both the
      ``from novel_ralph_skill.state.reconcile import (...)`` block and the
      ``__all__`` of ``state/__init__.py``, mirroring the existing
      ``derive_reconciliation`` entry; ``make all`` (pyright/ty + import
      resolution) catches a missed export.

## Progress

    - [x] Work Item 1: add ``reconciliation_payload`` to
      ``state/reconcile.py``; export it from ``state/__init__.py``.
      (commit ``45243c8``; ``make all`` green; ``reconcile.py`` now 366
      lines, under the 400-line cap. The recount-absent base shape prints
      ``{'action': 'none', 'discrepancies': [], 'detail': 'ok'}`` as the
      plan validation requires.)
    - [x] Work Item 2: pin the projection with a focused unit test (base shape;
      recount-pair present iff ``recounted_by_chapter is not None``; key order),
      red first. (commit ``c4e821a``; ``make all`` green. Red demonstrated by
      temporarily removing the ``state/__init__.py`` export — collection failed
      with ``ImportError: cannot import name 'reconciliation_payload'`` — then
      restored to green (4 passed). The defensive-copy assertion was reshaped to
      an identity check (``payload["by_chapter"] is not by_chapter``) because the
      ``ty`` checker narrows an ``isinstance``-guarded ``object`` to
      ``list[Unknown]``/``dict[Unknown, Unknown]`` and then rejects mutation
      through that narrowed local; the identity/equality form pins the same
      defensive-copy invariant without the narrowing. CodeRabbit (run 2) asked
      for assert messages and a test class; messages were added, but the
      module-level function form was kept — it is the codebase's dominant
      convention (114 module-function files vs 13 class files).)
    - [x] Work Item 3: route the four arms through the projection
      (``_render_reconciliation``, ``_write_outcome``, ``_refuse_outcome``, the
      ``NONE`` arm); confirm the single-source greps are clean. (commit
      ``0f77915``; ``make all`` green with **no test edited**.
      ``git grep '"action": str('`` returns exactly one hit
      (``reconcile.py:170``, the projection). ``reconciliation_payload`` resolves
      to its definition, the ``state/__init__.py`` re-export, the two command
      imports, and four call sites. The runtime import landed in
      ``novel_state.py``'s line-80 ``state`` block beside
      ``derive_reconciliation`` (not the ``TYPE_CHECKING`` block), as the plan's
      B2 correction required. ``_write_outcome``'s ``action`` parameter is now
      unread by the dict body but kept: Ruff does not flag it (ARG rules off),
      callers still pass it, and tightening the signature is out of scope.)

## Surprises & discoveries

    - Observation: the file previously at this path was a stale round-3 ExecPlan
      titled "Decide and pin the desloppify clean-pass findings contract", a
      different task from the current roadmap entry 7.1.3 ("Extract a single
      ``Reconciliation`` payload projection and route the four arms through it").
      Evidence: ``docs/roadmap.md`` line 2513 names the reconciliation-projection
      task; the on-disk file described a desloppify findings-list contract.
      Impact: the stale file was discarded and rewritten for the actual task
      (Decision Log), exactly as the sibling ``roadmap-7-1-1.md`` plan recorded
      after the same roadmap renumbering.

    - Observation: the two reconciliation snapshots pin different things, and
      only one pins key *order*. ``test_novel_state_check_disk.ambr`` stores
      ``reconciliation`` as ``{action, discrepancies, detail[, current,
      by_chapter]}`` (the code's insertion order); ``test_reconcile_refuse.ambr``
      stores ``result`` as ``{action, detail, discrepancies}`` (alphabetical).
      Evidence: ``test_novel_state_check_disk.py:234,248`` assert
      ``raw == snapshot`` against ``render_machine``'s unsorted ``json.dumps``
      (``contract/envelope.py:151``); ``test_reconcile_refuse.py:187`` asserts
      ``json.dumps(env, sort_keys=True) == snapshot``. Inspecting both ``.ambr``
      files confirms the differing stored orders.
      Impact: only the check_disk snapshot is an insertion-order backstop, and
      only for the READ (``check``) path; the write-side ``REFUSE``/``NONE``
      order is guarded solely by the Work Item 2 ``items()`` assertion. The
      round-1 plan's claim that both snapshots are the order backstop was false
      and was corrected (Decision Log, round 2).

    - Observation: ``novel_state.py`` imports ``Reconciliation`` ONLY under
      ``TYPE_CHECKING`` (line 108), not at runtime, because the module has
      ``from __future__ import annotations`` (line 41) and uses
      ``Reconciliation`` solely in the ``_render_reconciliation`` annotation. The
      runtime ``state`` import block (line 80) imports ``derive_reconciliation``
      but not ``Reconciliation``. ``_reconcile.py`` differs: its runtime block
      (line 55) imports both ``Reconciliation`` and ``derive_reconciliation``.
      Evidence: reading ``novel_state.py:41,80,108`` and ``_reconcile.py:55-63``.
      Impact: ``reconciliation_payload`` is *called* at runtime in both modules,
      so it must join each module's **runtime** ``state`` import — line 80 in
      ``novel_state.py`` (beside ``derive_reconciliation``) and line 55 in
      ``_reconcile.py``. A "follow where ``Reconciliation`` is imported"
      heuristic would wrongly place it in ``novel_state.py``'s ``TYPE_CHECKING``
      block and raise ``NameError`` (round-3 B2; corrected in Work Item 3).

    - Observation: ``_write_outcome`` serialises its ``action`` *parameter*
      (``str(action)``, ``_reconcile.py:225``), not the attribute
      ``str(reconciliation.action)`` the projection uses. They are value-identical
      at every call site only because both callers pass
      ``action == reconciliation.action`` (``:322`` passes ``action``, bound to
      ``reconciliation.action`` at ``:291``; ``:313`` passes the literal
      ``RECREATE_LOG``, equal to ``reconciliation.action`` because
      ``derive_reconciliation`` builds that ``Reconciliation`` with
      ``action=RECREATE_LOG`` at ``reconcile.py:332-333``).
      Evidence: reading ``_reconcile.py:215-234,286-322`` and
      ``reconcile.py:331-336``; the literal-passing case is pinned by
      ``tests/test_reconcile.py:262`` (``result["action"] == "recreate-log"``).
      Impact: the round-1/2 plan called the ``_write_outcome`` body
      "byte-identical" to ``_render_reconciliation``, which is textually false on
      the action key; corrected to "value-identical, given the caller invariant"
      (round-3 B3) so the implementer understands *why* the substitution is safe
      and which test pins it.

## Decision log

    - Decision: the stale desloppify-findings ExecPlan previously occupying this
      file was discarded and the file rewritten for the actual roadmap 7.1.3
      task.
      Rationale: the roadmap was renumbered; the on-disk
      ``docs/execplans/roadmap-7-1-3.md`` described a desloppify clean-pass
      findings-contract task that no longer maps to roadmap entry 7.1.3. The plan
      must match the task it is named for (the same situation
      ``roadmap-7-1-1.md`` recorded).
      Date/Author: 2026-06-27, planning agent.

    - Decision: the projection is a free function ``reconciliation_payload`` in
      ``state/reconcile.py``, not a ``Reconciliation.to_payload()`` method.
      Rationale: the module's established vocabulary is free functions over the
      dataclass (``derive_reconciliation``, ``_refuse``, ``_recount``), and the
      sibling consolidation precedent (roadmap 7.1.1) added free functions
      (``compile_is_current``, ``compiled_manuscript_path``) beside their
      dataclass/enum rather than methods. The roadmap success criterion names
      either form ("``to_payload()`` / ``reconciliation_payload()``"); the free
      function keeps the dataclass a pure data shape (``python-data-shapes``:
      frozen ``slots`` dataclass, no behaviour) and matches the module's grain.
      Date/Author: 2026-06-27, planning agent.

    - Decision: the projection returns a ``dict[str, object]`` only — no
      ``CommandOutcome``, no exit code, no ``messages``.
      Rationale: audit-2.3.2 Finding 2 is explicit that the read/write
      *envelope code* and *exit codes* "genuinely differ" and stay at the call
      sites; only the ``Reconciliation``-to-dict serialisation is centralised.
      Folding the envelope in would collapse the CQS read/write split the slice
      deliberately maintains (audit-2.2.2 Finding 2).
      Date/Author: 2026-06-27, planning agent.

    - Decision: the Purpose-section success observable is the executable
      dict-opening form ``"action": str(`` (one hit after the change), not a
      grep for the field names ``action``/``discrepancies``/``detail``.
      Rationale: the field names appear legitimately in docstrings that describe
      the payload shape (and in the read/write framing prose), which this task
      keeps; only the hand-built dict construction is removed. Scoping the
      observable to the dict-opening literal makes the stated end state match the
      actual (correct) one, mirroring the 7.1.1 plan's executable-form scoping.
      Date/Author: 2026-06-27, planning agent.

    - Decision: the round-1 reviewer's B1 is correct and resolved by prose-only
      edits (no design change). The write-side ``REFUSE``/``NONE`` ``result``
      key order is NOT guarded by any snapshot — ``test_reconcile_refuse.ambr``
      is ``sort_keys=True`` and ``test_novel_state_check_disk.ambr`` covers only
      the READ path — so the Work Item 2 ``list(payload.items())`` assertion is
      named the primary order pin and marked load-bearing (must not be
      weakened).
      Rationale: verified against source —
      ``render_machine`` (``contract/envelope.py:151``) emits
      ``json.dumps(ordered)`` with no ``sort_keys`` and is asserted
      ``raw == snapshot`` (``test_novel_state_check_disk.py:234,248``), whereas
      ``test_reconcile_refuse.py:187`` asserts
      ``json.dumps(env, sort_keys=True) == snapshot`` and the stored bytes read
      ``{action, detail, discrepancies}`` (alphabetical), proving the refuse
      snapshot does not pin insertion order. The design is sound; only the
      backstop claims were wrong, so the fix is prose.
      Date/Author: 2026-06-27, planning agent (round 2).

    - Decision: the round-3 reviewer's B2 and B3 are correct and resolved by
      prose-only edits (no design change). B2 — ``reconciliation_payload`` must
      be imported into ``novel_state.py``'s **runtime** ``state`` block at line
      80 (beside ``derive_reconciliation``), NOT the ``TYPE_CHECKING`` block at
      line 108 where ``Reconciliation`` is imported; the prior "where
      ``Reconciliation`` is imported" heuristic was wrong under
      ``from __future__ import annotations`` and would raise a runtime
      ``NameError``. B3 — the ``_write_outcome`` "byte-identical" claim was
      textually false: ``_write_outcome`` serialises its ``action`` *parameter*
      (``str(action)``, ``_reconcile.py:225``) while the projection serialises
      ``str(reconciliation.action)``; they are value-identical only because both
      callers pass ``action == reconciliation.action``, and that caller
      invariant (with its pin ``test_reconcile.py:262``) is now stated.
      Rationale: verified against source — ``novel_state.py:41`` carries
      ``from __future__ import annotations``; ``:80`` is the runtime ``state``
      import (``derive_reconciliation``, not ``Reconciliation``); ``:108`` is the
      ``TYPE_CHECKING`` ``Reconciliation`` import. ``_reconcile.py:225``
      serialises ``str(action)``; callers at ``:313``/``:322`` pass
      ``action == reconciliation.action`` (``:291`` binds
      ``action = reconciliation.action``; ``derive_reconciliation`` builds the
      RECREATE_LOG ``Reconciliation`` with ``action=RECREATE_LOG`` at
      ``reconcile.py:332-333``); ``test_reconcile.py:262`` asserts
      ``result["action"] == "recreate-log"``. The design (one projection, four
      arms, dict-only return, no behaviour change) is unchanged; only the
      import-block direction and the action-key provenance prose were corrected.
      Date/Author: 2026-06-27, planning agent (round 3).

## Outcomes & retrospective

    - Delivered in three gated commits: ``45243c8`` (projection + export),
      ``c4e821a`` (projection unit test, red-first), ``0f77915`` (route the four
      arms). ``make all`` is green at HEAD; the two ``.ambr`` snapshots and every
      pre-existing reconcile/check/disk-evidence/derivation/refusal/integration/
      BDD/e2e suite passed **unedited** — the no-behaviour-change guarantee held.
    - The single-source observables resolved exactly as the plan predicted:
      ``git grep '"action": str('`` returns one hit (the projection itself), and
      ``reconciliation_payload`` has one definition, one re-export, and four
      routed consumers.
    - Two real deviations, both prose/test-shape only, no design change:
      (1) the defensive-copy test used an identity assertion
      (``payload["by_chapter"] is not by_chapter``) rather than mutating a
      narrowed ``isinstance`` local, because ``ty`` narrows an
      ``isinstance``-guarded ``object`` to ``list[Unknown]``/``dict[Unknown,
      Unknown]`` and then rejects mutation through it; the invariant pinned is
      unchanged. (2) CodeRabbit asked for a test class and assert messages —
      messages were added, the class was declined as counter to the codebase's
      dominant module-level-function convention (114 vs 13).
    - CodeRabbit raised no actionable finding against any of the three code
      commits; all of its findings targeted untracked ``*review*.md`` scratch
      files outside this task's scope.

## Context and orientation

Read these before starting. They are the source of truth.

- `docs/novel-ralph-harness-design.md` §3.3 (command/query segregation — the
  checker/mutator split that keeps `check` read-only and `reconcile` the only
  writer; the read/write vocabulary distinction this task must preserve) and
  §5.4 (disk-authoritative reconciliation — `check` reports the reconciliation a
  stale tree implies and exits 4; `reconcile` enacts it, recomputing
  independently; "loud, never silent" — the `result` payload and the `log.md`
  receipt). These establish *why* the projection is one shared fact and why the
  read and write *framing* are deliberately distinct.
- `docs/issues/audit-2.3.2.md` — the originating audit. Finding 2 (the
  `{action, discrepancies, detail}` payload is hand-built in four places; give
  `Reconciliation` a single `to_payload()` / `reconciliation_payload()`
  projection beside it and route all four sites through it; keep the read/write
  envelope code and exit codes where they are). Findings 1, 3, 4, 5, 6 are
  **not** this task (non-goals).
- `docs/adr-001-deterministic-judgemental-boundary.md` (detect-only;
  `check` writes nothing — the projection is a pure read of an immutable
  dataclass).
- `docs/adr-003-shared-interface-contract.md` (the envelope and exit-code
  contract this refactor must not perturb).
- `AGENTS.md` "Python verification and testing" (unit/behavioural/property
  discipline; the snapshot rule — keep snapshots on stable boundaries, pair them
  with semantic assertions, no snapshot-only coverage for logic assertable
  directly) and "Markdown guidance".
- `docs/scripting-standards.md` and `docs/documentation-style-guide.md` for
  prose/comment conventions and Oxford spelling.
- `docs/execplans/roadmap-7-1-1.md` — the delivered sibling consolidation
  (a single canonical projection extracted into the state-layer owner module,
  four consumers routed through it, no behaviour change). This plan mirrors its
  structure and discipline.

Key code, by full path:

- `novel_ralph_skill/state/reconcile.py` — defines `ReconcileAction` (enum,
  line 108), the frozen `Reconciliation` dataclass (line 119, fields `action`,
  `discrepancies`, `detail`, `recounted_current`, `recounted_by_chapter`,
  `operation`, `missing_paths`), the `_refuse` / `_classify_pending_turn` /
  `_recount` builders, and `derive_reconciliation` (line 283). The new
  `reconciliation_payload` lands here, beside the dataclass.
- `novel_ralph_skill/commands/novel_state.py` — `_render_reconciliation`
  (line 129) builds the read-shaped payload (base three keys + recount pair);
  it is called from `_check` at line 213 to attach `result["reconciliation"]`.
  Route it through `reconciliation_payload`.
- `novel_ralph_skill/commands/_reconcile.py` — three write-side arms:
  `_write_outcome` (line 215, base three keys + recount pair, same shape as
  `_render_reconciliation` but serialising its `action` *parameter*
  `str(action)` rather than `str(reconciliation.action)` — value-identical
  because every caller passes `action == reconciliation.action`; see "Verified
  external facts"),
  `_refuse_outcome` (line 237, base three
  keys only), and the `NONE` arm inlined in `reconcile` (line 293, base three
  keys with an empty `discrepancies` list). Each wraps the dict in a
  `CommandOutcome` with its own exit code and `messages`; route only the dict
  through `reconciliation_payload`, leaving the `CommandOutcome` construction in
  place.
- `novel_ralph_skill/state/__init__.py` — re-exports the `reconcile` symbols
  (import block line 63-67: `ReconcileAction`, `Reconciliation`,
  `derive_reconciliation`; `__all__` line 137-149). Add
  `reconciliation_payload` to both.

Terms defined:

- *Reconciliation payload*: the JSON-serialisable dict the `check` `result`
  reports under `reconciliation` and the `reconcile` `result` returns directly —
  the base `{action, discrepancies, detail}` plus a `current`/`by_chapter` pair
  for a `RECOUNT`.
- *Read shape / write shape*: `check`'s read-only payload reports a *finding*
  (what `reconcile` *would* do); `reconcile`'s write-shaped `result` reports the
  *action taken*. The audit keeps their *vocabulary* and *exit codes* distinct;
  this task shares only the dict serialisation, which is identical.
- *CQS*: command/query segregation (§3.3) — checkers (`check`) read and report;
  mutators (`reconcile`) write. The split this task must not blur.

## Verified external facts (do not re-derive)

- **No external library behaviour is load-bearing for this task.** This is a
  pure internal-Python refactor: it adds no subprocess, no new console-script
  path, no new `--flag`, and no new third-party import. The four arms are
  reached either by direct function call in unit tests
  (`reconciliation_payload`, `_render_reconciliation`) or through the
  already-existing `run(build_app(), …)` / installed-script harness in the
  reconcile and check suites; this task adds neither a new invocation surface
  nor a new subprocess. The standing cuprum / Cyclopts / `pytest-timeout` /
  `uv run` research the workflow mandates therefore has **no bearing on any work
  item here** — there is no place in this plan where a cuprum catalogue, a
  Cyclopts argument, or a `pytest-timeout` override is exercised by a code
  change. (Verified by inspection of the four arms and their callers
  — `novel_state.py:129,213`, `_reconcile.py:215,237,293` — and by the
  parallel finding in the delivered `docs/execplans/roadmap-7-1-1.md` "Verified
  external facts" for the same class of pure-Python state-layer refactor.) The
  existing e2e suite (`tests/test_reconcile_e2e.py`) already pins the installed
  behaviour through cuprum, and it must stay green **unedited**, which is
  precisely the no-behaviour-change guarantee. This is stated explicitly rather
  than hedged: there is no undecided external-library fork in this plan.
- The reconciliation JSON envelope is snapshot-pinned at
  `tests/__snapshots__/test_novel_state_check_disk.ambr` (the `check` read
  shape) and `tests/__snapshots__/test_reconcile_refuse.ambr` (the `REFUSE`
  write shape). (Verified by `grep` for `reconciliation`/`discrepancies` in
  `tests/__snapshots__/`.) The projection must reproduce these bytes exactly;
  the snapshots are the no-behaviour-change backstop for the *field set* and
  *values* and must stay green unedited. Their *order-pinning* power is
  asymmetric, and the plan relies on the precise difference (see Constraints
  "base-dict order is preserved"):
  - `test_novel_state_check_disk.ambr` is rendered by `render_machine`
    (`novel_ralph_skill/contract/envelope.py:151`, `json.dumps(ordered)` with
    no `sort_keys`) and asserted `raw == snapshot`
    (`tests/test_novel_state_check_disk.py:234,248`), so it pins *insertion
    order* — but only for the READ (`check`) path. Its stored `reconciliation`
    blocks read `{action, discrepancies, detail[, current, by_chapter]}` (code
    order). (Verified by inspecting the `.ambr` and `render_machine`.)
  - `test_reconcile_refuse.ambr` is asserted `json.dumps(env, sort_keys=True)
    == snapshot` (`tests/test_reconcile_refuse.py:187`), so its stored bytes
    are alphabetically sorted (`result` reads `{action, detail,
    discrepancies}` — `detail` before `discrepancies`, NOT the code's
    insertion order). It pins the field set of the write-side `REFUSE`
    envelope, **not** its order: a reordered projection would still pass it.
    (Verified by inspecting the `.ambr` line and the `sort_keys=True`
    assertion.) The write-side order pin is the Work Item 2 `items()` test.
- The state package already re-exports the `reconcile` surface
  (`novel_ralph_skill/state/__init__.py:63-67` import, `:137-149` `__all__`),
  so adding one name there is the established pattern, not a new mechanism.
  (Verified by reading `state/__init__.py`.)
- `_render_reconciliation` and `_write_outcome` build the same dict shape (base
  three keys + the `recounted_by_chapter is not None`-guarded recount pair), but
  their `action` key is **not** spelled identically: `_render_reconciliation`
  uses `str(reconciliation.action)` (`novel_state.py:139`), while
  `_write_outcome` uses `str(action)` — its *parameter* (`_reconcile.py:225`).
  The projection uses `str(reconciliation.action)`, so routing `_write_outcome`
  through it changes the *source* of the action string from the parameter to the
  attribute.
  This is behaviour-preserving because both `_write_outcome` callers pass
  `action == reconciliation.action`:
  - `_reconcile.py:322` passes `action`, bound at `_reconcile.py:291` to
    `reconciliation.action` (`action = reconciliation.action`).
  - `_reconcile.py:313` passes the literal `ReconcileAction.RECREATE_LOG`, which
    equals `reconciliation.action` because `derive_reconciliation` builds that
    `Reconciliation` with `action=ReconcileAction.RECREATE_LOG`
    (`reconcile.py:332-333`).
  So `str(action)` and `str(reconciliation.action)` are the same string for
  every call today. The one nominally-distinct (literal-passing) case is the
  `RECREATE_LOG` path, pinned by `tests/test_reconcile.py:262`
  (`result["action"] == "recreate-log"`), which stays green unedited.
  `_refuse_outcome` and the `NONE` arm build only the base three keys (no
  recount pair), and both already serialise `str(reconciliation.action)` /
  `str(action)` where `action == reconciliation.action` on those arms too.
  (Verified by reading `novel_state.py:129-146`, `_reconcile.py:215-256`,
  `_reconcile.py:286-322`, `reconcile.py:331-336`, and
  `tests/test_reconcile.py:250-270`.)

## Plan of work

Three ordered, independently committable work items. Stage B (the projection +
its test) precedes Stage C (routing), so the routing edits land against a
pinned-and-green projection. The new-structure test is written red first (Work
Item 2); the routing (Work Item 3) is a behaviour-preserving substitution the
**existing, unedited** suites and snapshots already cover.

### Work Item 1 — add `reconciliation_payload` to `reconcile.py` and export it (Stage B)

In `novel_ralph_skill/state/reconcile.py`, add one free function beside the
`Reconciliation` dataclass (after the dataclass definition; keep it close to the
dataclass, before the private builders):

        def reconciliation_payload(
            reconciliation: Reconciliation,
        ) -> dict[str, object]:
            """Project a ``Reconciliation`` into its payload dict.

            The single source of the ``{action, discrepancies, detail}`` base
            shape both ``check`` reports (read shape) and ``reconcile`` returns
            (write shape), plus the ``current``/``by_chapter`` recount pair for a
            ``RECOUNT`` (added iff ``recounted_by_chapter`` is present). It
            serialises only; the exit code, the ``messages``, and the
            read-versus-write framing stay at each call site, so the CQS
            read/write split (design §3.3) is preserved (audit-2.3.2 Finding 2).
            Key order is fixed — ``action``, ``discrepancies``, ``detail``, then
            the recount pair — because the JSON envelope is snapshot-pinned.
            """
            payload: dict[str, object] = {
                "action": str(reconciliation.action),
                "discrepancies": list(reconciliation.discrepancies),
                "detail": reconciliation.detail,
            }
            if reconciliation.recounted_by_chapter is not None:
                payload["current"] = reconciliation.recounted_current
                payload["by_chapter"] = dict(reconciliation.recounted_by_chapter)
            return payload

This is byte-for-byte the body already in `_render_reconciliation` (which
serialises `str(reconciliation.action)`), lifted to its owner module. It is
*value*-identical to `_write_outcome`'s body, which serialises its `action`
*parameter* (`str(action)`); the projection canonicalises on the attribute
`reconciliation.action`, and Work Item 3 records why that substitution is
behaviour-preserving (both `_write_outcome` callers pass
`action == reconciliation.action`). Export it from
`novel_ralph_skill/state/__init__.py`: add `reconciliation_payload` to the
`from novel_ralph_skill.state.reconcile import (...)` block (line 63-67) and to
`__all__` (line 137-149), beside `derive_reconciliation` / `Reconciliation`.

Validation:

- `uv run python -c "from novel_ralph_skill.state import reconciliation_payload,
  Reconciliation, ReconcileAction; r =
  Reconciliation(action=ReconcileAction.NONE, discrepancies=(), detail='ok');
  print(reconciliation_payload(r))"` prints
  `{'action': 'none', 'discrepancies': [], 'detail': 'ok'}` (the base shape, no
  recount pair).
- `make all` green; commit (gate first).

Docs to read: design §3.3, §5.4; `audit-2.3.2.md` Finding 2; `reconcile.py` as
the structural template (mirror its docstring style and the
`derive_reconciliation` free-function grain).
Skills to load: `python-router` → `python-data-shapes` (the frozen-dataclass
projection shape; why a free function over a method keeps the data shape pure)
and `python-types-and-apis` (the `Reconciliation -> dict[str, object]`
signature).

### Work Item 2 — pin the projection with a focused unit test (Stage B, red first)

Add the projection's pins to a new `tests/test_reconciliation_payload.py`
(prefer a dedicated file for a clean boundary; do not put unit tests in the
package tree — AGENTS.md). It must:

- Assert the **base shape and key order** for a recount-absent reconciliation
  (e.g. a `REFUSE` or `NONE`): build a `Reconciliation(action=…,
  discrepancies=(…,), detail=…)`, call `reconciliation_payload`, and assert
  `list(payload.items()) == [("action", "<value>"), ("discrepancies", [...]),
  ("detail", "...")]` — comparing `items()` (ordered), not just `==` (which
  ignores order), so a reordered projection is red here. This `items()`
  assertion is the **NAMED PRIMARY order pin** for the write-side
  `REFUSE`/`NONE` `result` envelope: it is the *only* test that fails on a
  write-side key reorder, because neither snapshot guards it. The
  `check_disk` snapshot pins insertion order for the READ (`check`) path only,
  and the `reconcile_refuse` snapshot is `sort_keys=True` (it pins the field
  set, not the order — see Constraints "base-dict order is preserved" and Risk
  "reorders the dict keys"). Treat this assertion as load-bearing: it must not
  be weakened or removed in any future edit, or a write-side reorder bug could
  ship green.
- Assert the **recount pair is absent** when `recounted_by_chapter is None`
  (the projection has exactly the three base keys).
- Assert the **recount pair is present and correct** when
  `recounted_by_chapter is not None`: build a
  `Reconciliation(action=ReconcileAction.RECOUNT, …, recounted_current=N,
  recounted_by_chapter={...})` and assert the payload's `current` equals `N`,
  `by_chapter` equals the mapping (as a plain `dict`), and the key order places
  `current`/`by_chapter` *after* `detail`.
- Assert `discrepancies` and `by_chapter` are **independent copies** (the
  projection uses `list(...)` / `dict(...)`), so mutating the payload does not
  alias the frozen dataclass's tuple/mapping — a `python-data-shapes`
  defensive-copy pin.

These are unit/example tests over a pure function — no `working/` tree, no
subprocess, no snapshot. The input space is a small set of `Reconciliation`
shapes (recount-bearing vs recount-absent), so example-based tests suffice;
Hypothesis/CrossHair/mutmut are **not** required (`python-verification`: there
is no generated input space and the logic is a fixed-shape projection of a
closed dataclass). Write them **red first** against the not-yet-exported symbol
(import error), then green after Work Item 1 — or, if WI1 and WI2 are committed
together, demonstrate the red by temporarily removing the `reconciliation_payload`
export from `state/__init__.py`, then restore it (record the red/green
transcript in `Progress`/`Surprises`, as the 7.1.1 plan did).

Validation:

- `uv run pytest tests/test_reconciliation_payload.py -q` passes.
- `make all` green; commit.

Docs to read: AGENTS.md "Python verification and testing" (unit + example
discipline; snapshots only for stable boundaries — this is *not* a snapshot
test; pair semantic assertions with the existing snapshot suites);
`tests/test_reconcile_derivation.py` as the `Reconciliation`-construction
template.
Skills to load: `python-router` → `python-testing` (parametrization over the
recount-bearing/recount-absent cases, ids) and `python-verification` (to confirm
the fixed-shape projection needs no Hypothesis/CrossHair/mutmut adversary).

### Work Item 3 — route the four arms through the projection (Stage C)

Behaviour-preserving substitution. After this, no hand-built `{"action": str(…),
"discrepancies": list(…), "detail": …}` dict remains outside
`reconciliation_payload`.

1. `novel_ralph_skill/commands/novel_state.py` — in `_render_reconciliation`
   (line 129), replace the hand-built `payload` (lines 138-145) with
   `return reconciliation_payload(reconciliation)`. Trim the docstring to keep
   the **read-shape framing** ("renders a `Reconciliation` as the read-only
   `check` payload … carries no write-shaped success vocabulary") but drop the
   now-redundant by-hand-field description; point at `reconciliation_payload`
   for the shape. Add `reconciliation_payload` to the **runtime**
   `from novel_ralph_skill.state import (...)` block at `novel_state.py:80` —
   the block that already imports `derive_reconciliation` at runtime — and
   **not** the `TYPE_CHECKING` block at `novel_state.py:108`. This matters
   because `novel_state.py` has `from __future__ import annotations` (line 41)
   and imports `Reconciliation` **only** as a type-checking name in the
   `if typ.TYPE_CHECKING:` block at line 108 (it is used solely in the
   `_render_reconciliation` *annotation*), whereas the line-80 runtime block
   imports `derive_reconciliation` (alongside `build_initial_document`,
   `check_disk_evidence`, `validate_state`, `write_document_atomically`) but
   **not** `Reconciliation`. `reconciliation_payload` is *called* at runtime, so
   it must be a runtime import. Do **not** apply a "put it where
   `Reconciliation` is imported" heuristic: that resolves to the line-108
   `TYPE_CHECKING` block, where the name is absent at runtime, and the call
   would raise `NameError`. Place it in the line-80 block beside
   `derive_reconciliation`. (Confirm the two blocks with
   `leta show novel_ralph_skill.commands.novel_state`: the runtime `state`
   import is at line 80; the `TYPE_CHECKING` `Reconciliation` import at line
   108.) If `_render_reconciliation` now collapses to a one-line passthrough,
   that is the intended end state — keep it as a named function so the
   read-shape framing docstring and the call site at line 213 are unchanged.
2. `novel_ralph_skill/commands/_reconcile.py` —
   - `_write_outcome` (line 215): replace the hand-built `result` dict
     (lines 224-231) with `result = reconciliation_payload(reconciliation)`;
     keep the `CommandOutcome(code=ExitCode.SUCCESS, result=result,
     messages=[reconciliation.detail])` construction and the write-shape framing
     docstring unchanged. **Note the one non-byte-identical detail and why the
     substitution is still safe.** `_write_outcome` currently serialises its
     `action` *parameter* (`str(action)`, `_reconcile.py:225`), whereas
     `reconciliation_payload` serialises the *attribute*
     `str(reconciliation.action)`. These differ textually but are
     value-identical at both call sites, because both callers pass
     `action == reconciliation.action`:
     - `_reconcile.py:322` passes `action`, which is
       `reconciliation.action` (bound at `_reconcile.py:291`,
       `action = reconciliation.action`), so they are the same object.
     - `_reconcile.py:313` passes the literal
       `ReconcileAction.RECREATE_LOG`, which equals `reconciliation.action`
       because `derive_reconciliation` builds that `Reconciliation` with
       `action=ReconcileAction.RECREATE_LOG` (`reconcile.py:332-333`).
     So `str(action)` and `str(reconciliation.action)` evaluate to the same
     string for every `_write_outcome` call today; the substitution is
     behaviour-preserving on the action key. The one nominally-distinct case —
     the literal-passing `RECREATE_LOG` caller — is pinned by
     `tests/test_reconcile.py:262` (`result["action"] == "recreate-log"`), which
     stays green unedited and is the regression proof for this specific
     substitution. (`_write_outcome`'s `action` parameter is no longer read by
     the dict after the swap — it is consulted only for the value the projection
     now reads from `reconciliation.action` — but leave the signature unchanged:
     callers still pass it, and tightening the signature is out of scope.)
   - `_refuse_outcome` (line 237): replace the inline three-key `result=` dict
     (lines 250-254) with `reconciliation_payload(reconciliation)`; keep the
     `_append_recovery_entry` receipt, the `ExitCode.ACTIONABLE_FINDING`, and
     the `messages` unchanged. (A `REFUSE` has `recounted_by_chapter = None`, so
     the projection yields exactly the base three keys — identical to today.)
   - the `NONE` arm in `reconcile` (line 293-302): replace the inlined
     `result={"action": str(action), "discrepancies": [], "detail":
     reconciliation.detail}` with `result=reconciliation_payload(reconciliation)`;
     keep the `CommandOutcome(code=ExitCode.SUCCESS, …, messages=…)`. (A `NONE`
     reconciliation has `discrepancies = ()` and `recounted_by_chapter = None`,
     so the projection yields `{"action": "none", "discrepancies": [], "detail":
     …}` — identical to the inlined dict, including the empty list.)
   - Add `reconciliation_payload` to the existing
     `from novel_ralph_skill.state import (...)` block (lines 55-63, which
     already imports `Reconciliation`, `ReconcileAction`,
     `derive_reconciliation`).

No test is edited for new behaviour: the existing reconcile, check,
disk-evidence, derivation, refusal, integration, BDD, e2e, and snapshot suites
are the regression net and must stay green **unedited**. That is the
no-behaviour-change proof.

Validation:

- `git grep -n '"action": str(' novel_ralph_skill/` returns exactly one hit,
  inside `reconciliation_payload` in `state/reconcile.py`.
- `git grep -n 'reconciliation_payload' novel_ralph_skill/` resolves to the
  definition (`state/reconcile.py`), the re-export (`state/__init__.py`), and
  four consumer call sites.
- `uv run pytest tests/test_reconcile.py tests/test_reconcile_refuse.py
  tests/test_reconcile_derivation.py tests/test_reconcile_integration.py
  tests/test_novel_state_check_disk.py tests/test_disk_evidence.py -q` passes
  unchanged.
- `make all` green (full suite, including the two `.ambr` snapshot suites, BDD,
  and e2e, all unedited); commit.

Docs to read: `audit-2.3.2.md` Finding 2 (the CQS read/write envelope and exit
codes stay where they are); design §3.3 (the read/write split the framing
docstrings preserve); `tests/test_reconcile_refuse.py` and
`tests/test_novel_state_check_disk.py` (the snapshot suites that pin the two
envelope shapes the projection must reproduce byte-for-byte).
Skills to load: `python-router` → `python-testing` (to confirm the existing
suites are the right regression net). Use `leta refs Reconciliation` and
`leta grep '"action": str'` to confirm every hand-built-dict site is accounted
for before editing, and `leta` for the import checks.

## Concrete steps

Run everything from the worktree root
`/data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-7-1-3`.

1. Confirm the branch and a clean tree:

        $ git branch --show
        roadmap-7-1-3
        $ git status --porcelain   # expect empty before starting

2. Work Item 1: add `reconciliation_payload` to `reconcile.py`, export from
   `state/__init__.py`. Verify:

        $ uv run python -c "$(printf '%s\n' \
            'from novel_ralph_skill.state import (reconciliation_payload,' \
            '    Reconciliation, ReconcileAction)' \
            'r = Reconciliation(action=ReconcileAction.NONE,' \
            '    discrepancies=(), detail=\"ok\")' \
            'print(reconciliation_payload(r))')"
        {'action': 'none', 'discrepancies': [], 'detail': 'ok'}

   Then `make all`; commit (gate first).

3. Work Item 2: add `tests/test_reconciliation_payload.py`, red first, then
   green:

        $ uv run pytest tests/test_reconciliation_payload.py -q
        ... passed

   Then `make all`; commit.

4. Work Item 3: route the four arms; then verify the duplication is gone:

        $ git grep -n '"action": str(' novel_ralph_skill/
        novel_ralph_skill/state/reconcile.py: ...   # only the projection itself
        $ git grep -n 'reconciliation_payload' novel_ralph_skill/
        # definition + re-export + four call sites

   Then `make all` (full suite, all unedited); commit.

Each commit is gated by `make all` per the workflow standing rule. There are no
Markdown changes in Work Items 1-3, so `make markdownlint` / `make nixie` are
**not** required for the code commits; they are required only for the ExecPlan
file itself (this document), run once when the plan is committed. Commit only
when the user has approved the plan and asked to proceed.

## Validation and acceptance

Quality criteria (what "done" means):

- Tests: `tests/test_reconciliation_payload.py` passes (and failed red before
  Work Item 1's symbol existed). Every pre-existing reconcile, check,
  disk-evidence, derivation, refusal, integration, BDD, e2e, and snapshot suite
  passes **without edit** — that is the no-behaviour-change proof (roadmap 7.1.3
  success criterion).
- Lint/typecheck: `make all` (build, check-fmt, lint, typecheck, test) is green
  — Ruff, `interrogate` 100% (the new function carries a docstring), Pylint
  (`reconcile.py` under the 400-line cap after the addition), `pyright`/`ty`
  (the new signature and the new export resolve).
- Structural: the two `git grep` checks in Work Item 3 confirm the
  serialisation has exactly one home (`reconciliation_payload` in
  `reconcile.py`) and four routed consumers.
- en-GB Oxford spelling throughout the new docstring and comments.

Quality method (how we check):

- Local: `make all` after each work item; the same gates run in CI
  (`.github/workflows/ci.yml`).
- Markdown gates: `make markdownlint` and `make nixie` on this ExecPlan file
  (the only Markdown this task touches). No Mermaid is added; `make nixie` is
  run per the workflow rule for Markdown changes.
- Behaviour acceptance: the two snapshot suites
  (`tests/test_novel_state_check_disk.py`,
  `tests/test_reconcile_refuse.py`) still pass, proving the `check` read shape
  and the `reconcile` `REFUSE` write shape are byte-identical to before — now
  backed by one shared `reconciliation_payload` projection rather than four
  hand-built dicts. Note the asymmetry: `test_novel_state_check_disk.py`
  asserts the *unsorted* `render_machine` bytes (`raw == snapshot`), so it
  also pins key order for the READ path; `test_reconcile_refuse.py` asserts
  `json.dumps(env, sort_keys=True)`, so it pins the write-side field set and
  values but not order. The write-side `REFUSE`/`NONE` key order is pinned by
  the Work Item 2 `items()` unit assertion, not by a snapshot.

## Idempotence and recovery

- Every edit is a behaviour-preserving substitution or an additive symbol;
  re-running any work item is safe. No `working/` tree, `state.toml`, or
  `log.md` is mutated by any step (the projection is a pure read of an immutable
  dataclass; ADR-001).
- If a commit's gate fails, fix forward on the same work item; do not advance.
  If a snapshot moves (it must not), treat it as a Tolerance breach (behaviour
  drift) — stop and escalate rather than re-recording the snapshot.
- The new test file is additive; deleting it leaves the tree buildable. The
  routing edits are reversible by restoring the inline dicts, but there is no
  reason to.

## Interfaces and dependencies

- New, in `novel_ralph_skill/state/reconcile.py` (and re-exported from
  `novel_ralph_skill/state/__init__.py`):

        def reconciliation_payload(
            reconciliation: Reconciliation,
        ) -> dict[str, object]:
            """Project a ``Reconciliation`` into its JSON-serialisable payload …"""

- Reused, unchanged: `Reconciliation`, `ReconcileAction`,
  `derive_reconciliation`; the `_render_reconciliation` read-shape framing and
  its call site in `_check`; the `_write_outcome` / `_refuse_outcome` /
  `NONE`-arm `CommandOutcome` construction, exit codes, and `messages`; the
  D-SELF reconcile bracket; the `novel-state`/`reconcile` Cyclopts apps and the
  shared `run`/envelope machinery (all untouched).
- Dependencies: **no new third-party dependency**; the only new import crossing
  a module boundary is `reconciliation_payload`. No external library behaviour
  (cuprum, Cyclopts, `pytest-timeout`, `uv run`) is exercised by any code change
  in this task (see "Verified external facts").

## Revision note

- 2026-06-27: initial DRAFT. The file previously held a stale round-3 ExecPlan
  ("Decide and pin the desloppify clean-pass findings contract") that did not
  match the renumbered roadmap entry 7.1.3; it was discarded (Decision Log) and
  rewritten for the actual task — extracting a single `reconciliation_payload`
  projection into `state/reconcile.py` and routing the four arms through it
  (audit-2.3.2 Finding 2). Decomposed into three ordered, gate-passable work
  items (projection + export; projection test red-first; route the four arms).
  Pinned the load-bearing facts against source: the four hand-built sites and
  their exact bodies (`_render_reconciliation` / `_write_outcome`
  byte-identical; `_refuse_outcome` / `NONE` base-only), the two `.ambr`
  snapshots that pin the read and `REFUSE` field sets (the no-behaviour-change
  backstop), the key-order constraint — pinned for the READ path by
  `test_novel_state_check_disk.ambr` (`render_machine`'s unsorted
  `json.dumps`), while `test_reconcile_refuse.ambr` is `sort_keys=True` and so
  pins the field set only, leaving the write-side `REFUSE`/`NONE` order to the
  Work Item 2 `items()` pin — the CQS
  projection returns a dict, not a `CommandOutcome`), and the established
  `state/__init__.py` re-export pattern. Followed the delivered
  `docs/execplans/roadmap-7-1-1.md` structure and its executable-form observable
  scoping. Stated explicitly that no external-library behaviour is load-bearing
  for this internal refactor — there is no undecided external fork.
- 2026-06-27 (round 2, prose-only): the design reviewer flagged B1 — the plan
  misrepresented `test_reconcile_refuse.ambr` as an insertion-order backstop,
  but `tests/test_reconcile_refuse.py:187` asserts
  `json.dumps(env, sort_keys=True) == snapshot` (keys SORTED), and the stored
  snapshot shows `result` as the alphabetical `{action, detail, discrepancies}`,
  not the code's insertion order `{action, discrepancies, detail}`. Verified
  against source: `render_machine` (`contract/envelope.py:151`) is
  `json.dumps(ordered)` with no `sort_keys`, asserted `raw == snapshot` at
  `test_novel_state_check_disk.py:234,248` (so only the check_disk recount and
  refuse snapshots pin *insertion order*, and only on the READ path); the
  reconcile_refuse snapshot is sorted (pins the field set, not order). Corrected
  the Constraints "base-dict order is preserved" bullet, Risk 1, the "Verified
  external facts" snapshot entry, Risk 3, the Validation behaviour-acceptance
  bullet, and this revision note, and elevated the Work Item 2
  `list(payload.items())` ordered assertion to the NAMED PRIMARY order pin for
  the write-side `REFUSE`/`NONE` `result` envelope (the only check that fails on
  a write-side reorder, since no snapshot guards it). No design change: the
  projection, the four-arm routing, the work-item decomposition, and the
  no-behaviour-change guarantee are unchanged; only the order-backstop prose was
  corrected.
- 2026-06-27 (round 3, prose-only): the design reviewer flagged B2 and B3, both
  prose-only. B2 — Work Item 3's import-block guidance misdirected
  `novel_state.py`: it told the implementer to add `reconciliation_payload` to
  "the block that already imports `Reconciliation`", but `novel_state.py` has
  `from __future__ import annotations` (line 41) and imports `Reconciliation`
  **only** in the `TYPE_CHECKING` block at line 108; the runtime `state` import
  block is at line 80 (it imports `derive_reconciliation`, not
  `Reconciliation`). Since `reconciliation_payload` is *called* at runtime, the
  literal heuristic
  would place it in the line-108 `TYPE_CHECKING` block and raise `NameError`.
  Fixed Work Item 3 step 1 to direct the implementer to the runtime block at
  line 80 (beside `derive_reconciliation`), explicitly **not** the line-108
  `TYPE_CHECKING` block, and dropped the misdirecting "where `Reconciliation` is
  imported" heuristic. The `_reconcile.py` guidance (the line-55 runtime block,
  which imports `Reconciliation` **and** `derive_reconciliation` at runtime) was
  already correct and is unchanged. Verified against source:
  `novel_state.py:41` (`from __future__ import annotations`), `:80` (runtime
  `state` import, no `Reconciliation`), `:108` (`TYPE_CHECKING` `Reconciliation`
  import); `_reconcile.py:55-63` (runtime block with `Reconciliation`).
  B3 — the "byte-identical" claim for `_write_outcome` rested on an unstated,
  unpinned invariant: `_write_outcome` serialises its `action` *parameter*
  (`str(action)`, `_reconcile.py:225`), while the projection serialises
  `str(reconciliation.action)`; they are value-identical only because both
  `_write_outcome` callers pass `action == reconciliation.action`
  (`_reconcile.py:322` passes `action`, bound to `reconciliation.action` at
  `:291`; `:313` passes the literal `RECREATE_LOG`, equal to
  `reconciliation.action` because `derive_reconciliation` builds that
  `Reconciliation` with `action=RECREATE_LOG`, `reconcile.py:332-333`). The plan
  stated something textually false ("byte-identical body") and never named the
  parameter-vs-attribute distinction or the caller invariant. Fixed: recorded
  the distinction and the caller invariant in Work Item 3's `_write_outcome`
  step, the Purpose section, the Context orientation, Work Item 1's lifting
  note, and the "Verified external facts" entry, and named
  `tests/test_reconcile.py:262` (`result["action"] == "recreate-log"`) as the
  pin for the one nominally-distinct (literal-passing `RECREATE_LOG`) case. No
  design change: the
  projection, the four-arm routing, the work-item decomposition, and the
  no-behaviour-change guarantee are unchanged; only the import-block direction
  and the action-key provenance prose were corrected.

## Addenda

Lightweight, no-plan corrections folded onto this completed task after its
reviews and audits, triaged at the §7.1 step boundary.

- [x] **7.1.3.1 — Drop the now-vestigial `action` parameter from `_write_outcome`**
  (from review:7.1.3; severity: low). After this task routed `_write_outcome`
  through `reconciliation_payload`, the `action` parameter is no longer read by
  the body — the projection reads `reconciliation.action`. Remove the parameter
  and simplify its two callers (`commands/_reconcile.py:299,308`), removing the
  surface where a caller could pass an `action` inconsistent with
  `reconciliation.action`. The 7.1.3 plan explicitly deferred this as
  out-of-scope scope-discipline; it is now actioned as a lightweight pass.
- [x] **7.1.3.2 — Replace US `serialize` with en-GB `serialise`**
  (from review:7.1.4; severity: low). `docs/developers-guide.md:1425` carries
  `serialize`, a US spelling introduced by this task, violating the AGENTS.md
  en-GB Oxford convention ("-ise"/"-yse"/"-our"). Correct the single occurrence
  to `serialise`; no other prose in the clean-pass section is affected.
