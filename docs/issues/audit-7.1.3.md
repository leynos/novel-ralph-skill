# Post-merge audit — roadmap task 7.1.3

Audit of the codebase after task 7.1.3 ("Extract a single `Reconciliation`
payload projection and route the four arms through it") merged to `main` at
commit `4f997c2`. The task replaced the four-site duplication of the
`Reconciliation`-to-dict serialisation with one shared projection,
`reconciliation_payload`, added to the state layer
(`novel_ralph_skill/state/reconcile.py`) and exported from
`novel_ralph_skill/state/__init__.py`. The four arms now route through it: the
read-shape `check` arm (`_render_reconciliation` in
`novel_ralph_skill/commands/novel_state.py`) and the three write-shape
`reconcile` arms (`_write_outcome`, `_refuse_outcome`, and the `NONE` arm in
`novel_ralph_skill/commands/_reconcile.py`). The projection serialises only —
the exit code, the `messages`, and the read-versus-write framing stay at each
call site — so the CQS read/write split (design §3.3) is preserved. The change
pinned the projection with a dedicated unit file
(`tests/test_reconciliation_payload.py`) and closes audit-2.3.2 Finding 2.

Note on file provenance: the file previously at this path described a *different*
task 7.1.3 ("Slim the desloppify clean-pass findings trail" at commit `641e46c`)
— the roadmap was rerouted/renumbered between audits, and the earlier file was
written against the older meaning of "7.1.3". This file replaces it with the
audit of the task that actually merged as 7.1.3 (the reconciliation payload
projection). The desloppify clean-pass findings work and its findings remain
tracked under their own roadmap lane and audit history.

Trail followed: `docs/novel-ralph-harness-design.md` §3.3 and §5.4;
`docs/developers-guide.md` (the reconciliation derivation and disk-evidence
sections); `docs/issues/audit-2.3.2.md` (Finding 2); the ADRs (ADR-001
detect-only boundary, ADR-003 shared interface contract, ADR-005 five-script
surface); `AGENTS.md` (quality gates, 400-line file cap, CQS, en-GB Oxford
spelling); the three Logisphere review rounds recorded as ExecPlan artefacts
(`docs/execplans/roadmap-7-1-3.logisphere-review-r1/r2/r3.md`); the
`python-router`/`leta`/`sem` and `en-gb-oxendict` skills for navigation,
history, and prose. Files inspected:
`novel_ralph_skill/state/reconcile.py`,
`novel_ralph_skill/state/__init__.py`,
`novel_ralph_skill/commands/_reconcile.py`,
`novel_ralph_skill/commands/novel_state.py`;
`tests/test_reconciliation_payload.py`, `tests/test_reconcile_refuse.py`;
`pyproject.toml` (ruff `select`); `docs/roadmap.md` §7.1.

The merged change is high quality: the projection is a small, total, fixed-shape
function placed beside its `Reconciliation` dataclass; the docstring states the
CQS rationale and the snapshot-pinned key-order invariant; the four arms route
through it cleanly; and the new unit file is the named primary write-side
key-order pin (the `REFUSE` snapshot is `sort_keys=True` and pins the field set,
not the order). The findings below are minor: a **dead parameter left by the
refactor** (Finding 1, the substantive one), a **redundant pass-through wrapper**
(Finding 2), a **missing lint rule that would have caught Finding 1** (Finding
3), and a **documentation gap for the new exported projection** (Finding 4).

## Finding 1 — `_write_outcome`'s `action` parameter is dead after the refactor (severity: low)

**Category:** ergonomics

**Location:** `novel_ralph_skill/commands/_reconcile.py:216-228` (`_write_outcome`);
callers at `:299` and `:308`.

Before 7.1.3, `_write_outcome` built `"action": str(action)` from its `action`
parameter. The refactor replaced that body with
`result = reconciliation_payload(reconciliation)`, and the projection reads
`str(reconciliation.action)` — so `action` (the parameter at line 217) is now
never referenced in the function body. The round-2 Logisphere review (B3,
`docs/execplans/roadmap-7-1-3.logisphere-review-r2.md:80-114`) verified that the
substitution is behaviour-preserving precisely *because* every caller passes
`action == reconciliation.action`, but the now-redundant parameter was left in
place. It is a latent trap: a future caller could pass an `action` that disagrees
with `reconciliation.action`, silently doing nothing (the parameter is ignored)
and lulling the author into believing the discrepancy is honoured. The two
current callers (`:299` passing `ReconcileAction.RECREATE_LOG`, `:308` passing
the derived `action`) both already hold the invariant, so this is not a live bug.

**Proposed fix:** Remove the `action` parameter from `_write_outcome`, giving it
the signature `_write_outcome(reconciliation: Reconciliation) -> CommandOutcome`,
and drop the argument at both call sites (`:299` becomes
`_write_outcome(reconciliation)`; `:308` likewise). This deletes the dead
parameter and the invariant the r2 review had to reason about, leaving
`reconciliation.action` the single source of the serialised action — exactly what
the projection already enforces. The `RECREATE_LOG` path keeps its literal action
only where it is actually used (the `_append_recovery_entry` log line at `:298`),
which is unaffected.

## Finding 2 — `_render_reconciliation` is now a single-line pass-through wrapper (severity: low)

**Category:** complexity

**Location:** `novel_ralph_skill/commands/novel_state.py:130-140`
(`_render_reconciliation`); sole caller at `:207`.

After the refactor `_render_reconciliation` is `return
reconciliation_payload(reconciliation)` — a one-line delegation with a single
caller. Its remaining value is the docstring, which carries the read-side CQS
framing ("`check` reports the reconciliation a stale `state.toml` *implies*
without enacting it … `check` writes nothing"). That framing is genuine, but a
named, exported-shadowing private wrapper around a one-line call is borderline
redundant indirection: the four-site duplication the projection eliminated no
longer exists, so the wrapper's only job is to host a comment.

**Proposed fix:** Either (a) inline the call at `:207` —
`result["reconciliation"] = reconciliation_payload(derive_reconciliation(state,
root))` — and move the read-side CQS rationale to a comment at the call site or
into `reconciliation_payload`'s docstring (which already documents both shapes);
or (b) keep the wrapper but add a one-line note that it exists purely to host the
read-side framing, so the next reader does not mistake it for behaviour the
projection lacks. Option (a) is preferred: the projection docstring already owns
the read-versus-write narrative, so the wrapper adds a hop without adding
behaviour. This is a judgement call, not a defect — flag, do not force.

## Finding 3 — ruff `ARG` (unused-argument) is not in the lint `select`, so Finding 1 was not caught (severity: low)

**Category:** test-gap

**Location:** `pyproject.toml:35-85` (`[tool.ruff.lint] select`).

The ruff `select` list is extensive (F, B, RUF, PLR, ANN, D, and many more) but
does not include `ARG` (flake8-unused-arguments). That is why the dead `action`
parameter in Finding 1 passed the gates: nothing flags a function parameter that
is never read. Given the codebase's heavy functional style — many small pure
projections and mutators threaded through call sites — a refactor that hollows
out a parameter (exactly what 7.1.3 did) is a recurring risk that `ARG` would
catch cheaply.

**Proposed fix:** Add `"ARG"` to the ruff `select` list. Expect to triage a small
number of intentional unused arguments (protocol/callback conformance, abstract
overrides); silence those locally with `# noqa: ARG00x` and a one-line reason, or
the conventional leading-underscore parameter name where the signature is fixed
by an interface. The immediate payoff is that Finding 1 (and any future
refactor-orphaned parameter) becomes a gate failure rather than an audit finding.

## Finding 4 — the new exported `reconciliation_payload` projection is undocumented in the developers' guide (severity: low)

**Category:** docs-gap

**Location:** `novel_ralph_skill/state/__init__.py:159` (`__all__` export);
`docs/developers-guide.md` (no mention).

`reconciliation_payload` is a new public, exported symbol that owns the
machine-payload key order for both the `check` read shape and the `reconcile`
write shapes — a contract concern. The developers' guide documents the sibling
state-layer contract helpers by name where they carry contract weight
(`derive_reconciliation` at `developers-guide.md:532`/`:905`,
`compile_model.compiled_matches_drafts` at `:654`/`:1021`/`:1037`), but it does
not mention `reconciliation_payload`. A maintainer reading the guide learns that
`check` and `reconcile` share a payload shape only by reading the code; the
single-source guarantee — the whole point of 7.1.3 — has no prose home outside
the function docstring and the roadmap entry. The function docstring itself is
thorough, so this is a guide-completeness gap, not a code-comment gap.

**Proposed fix:** Add a short paragraph to the developers' guide, beside the
existing reconciliation derivation material, naming `reconciliation_payload` as
the single source of the `{action, discrepancies, detail}` (+ optional
`current`/`by_chapter`) payload shared by the `check` read shape and the
`reconcile` write shapes, and noting that the read/write distinction lives in the
envelope (exit code, `messages`), not in the projected dict. Cross-reference the
key-order pin in `tests/test_reconciliation_payload.py` so the next editor knows
where the order invariant is enforced.

## Proposed roadmap items (proposal only — the root agent owns the roadmap)

1. **Enable ruff `ARG` (unused-argument) in the lint `select`** (severity: low).
   Add `"ARG"` to `pyproject.toml` `[tool.ruff.lint] select`, triage the existing
   intentional unused arguments with local `# noqa: ARG00x` plus a reason (or the
   leading-underscore convention for interface-fixed signatures), and remove
   `_write_outcome`'s dead `action` parameter (Finding 1) as the first
   beneficiary. Rationale: the codebase's functional style makes
   refactor-orphaned parameters a recurring risk that a gate should catch, not an
   audit.
