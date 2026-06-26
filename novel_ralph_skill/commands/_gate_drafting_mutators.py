"""Body functions and the registrar for the gate and drafting sub-state mutators.

This module hosts the four single-file ``novel-state`` mutators that close the
last hand-edit holes in the harness state (roadmap task 2.2.4; design §4.1, §5.2;
ADR 010): ``set-gate`` (the knitting gates and the final-pass gate), the
``complete-final-pass`` convenience verb, ``set-fangirl``
(``drafting.fangirl.last_chapter_passed``), and ``set-critic-pass``
(``drafting.critic.pass``). It lives beside
:mod:`novel_ralph_skill.commands._state_mutators` — reusing its shared
load/refuse helpers — so neither that module (which already hosts ``set-cursor``
and ``advance-phase``) nor :mod:`novel_ralph_skill.commands.novel_state` (one line
under the 400-line cap) need grow past the AGENTS.md file-size limit (ExecPlan
Decision D11/B4).

Every body follows the ``set_cursor`` skeleton (``_state_mutators.py``): load the
``tomlkit`` document, derive the typed view once to prove the document is
structurally complete, edit the on-disk keys in place, derive the *proposed* view,
run the §5.2 validate-before-persist pass, and write atomically only when the
proposed state is coherent. A refusal writes nothing, so the prior ``state.toml``
is byte-for-byte intact (design §3.4; ExecPlan Constraint "Validate before
persist"). Like ``set-cursor`` — and unlike ``advance-phase`` — none refuses an
*incoherent prior*; that is what lets ``set-gate`` repair a gate that lags its
ratio (Decision D4).

The two §5.2-unconstrained fields carry their own write-time preconditions in
this module, mirroring ``set-chapters``' ``manifest_coherence_violations`` (ADR
008; Decision D6): ``set-fangirl`` requires ``0 <= last_chapter <= len(chapters)``
and ``set-critic-pass`` requires ``pass >= 1``. A breached precondition refuses
with exit ``3`` naming the rule, *before* the §5.2 pass.

The one usage fault these mutators detect themselves — a no-flag ``set-gate``,
which the Cyclopts parser cannot catch because it parses cleanly to ``{}`` — is
routed to exit ``2`` via a domain :class:`GateDraftingUsageError` caught by the
thin :func:`_set_gate_or_usage` adapter, which returns an exit-``2``
:class:`CommandOutcome` directly (never via the runner's ``str(CycloptsError)``
arm, which would crash). This copies the proven
``_desloppify.DesloppifyUsageError`` + ``_scan_or_usage`` precedent (Decision D9;
Surprise S3).
"""

from __future__ import annotations

import dataclasses as dc
import typing as typ

import cyclopts

from novel_ralph_skill.commands._state_mutators import (
    _load_document_or_state_error,
    _refuse_if_incoherent,
    _state_path,
    _state_view_or_state_error,
)
from novel_ralph_skill.contract.errors import EnvelopeMessagesError
from novel_ralph_skill.contract.exit_codes import ExitCode
from novel_ralph_skill.contract.runner import CommandOutcome, StateInputError
from novel_ralph_skill.state import write_document_atomically

if typ.TYPE_CHECKING:
    from tomlkit import TOMLDocument

__all__ = [
    "GateDraftingUsageError",
    "register_gate_drafting_commands",
]

# The on-disk key each ``set-gate`` knitting flag edits, paired with its CLI
# argument name. The final-pass gate lives under ``[gates.final]`` and is handled
# separately because it sits in a different table.
_KNITTING_KEYS: tuple[tuple[str, str], ...] = (
    ("knitting_30", "done_30"),
    ("knitting_50", "done_50"),
    ("knitting_80", "done_80"),
)


@dc.dataclass(frozen=True, kw_only=True)
class GateSelection:
    """The four optional ``set-gate`` flags as one value.

    Bundling them keeps the body and adapter signatures to one argument and gives
    the no-flag check one home (:meth:`any_set`); ``None`` leaves a gate untouched.
    """

    knitting_30: bool | None = None
    knitting_50: bool | None = None
    knitting_80: bool | None = None
    final: bool | None = None

    @property
    def any_set(self) -> bool:
        """Whether at least one flag was supplied (is not ``None``)."""
        flags = (self.knitting_30, self.knitting_50, self.knitting_80, self.final)
        return any(value is not None for value in flags)


class GateDraftingUsageError(EnvelopeMessagesError):
    """A body-detected usage fault routed to exit ``2`` (design §3.2).

    Raised when a gate/drafting mutator is invoked in a way the Cyclopts parser
    cannot catch — specifically a no-flag ``set-gate``, which parses cleanly to
    ``{}``. The registrar wrapper raises it and :func:`_set_gate_or_usage` returns
    an exit-``2`` :class:`~novel_ralph_skill.contract.runner.CommandOutcome`
    directly, never via the runner's ``str(CycloptsError)`` arm (which would crash
    on a bare ``cyclopts.ValidationError``; ExecPlan Surprise S3, Decision D9).
    This copies the ``_desloppify.DesloppifyUsageError`` precedent in shape; the
    optional ``messages`` payload (recorded once by
    :class:`~novel_ralph_skill.contract.errors.EnvelopeMessagesError`) carries the
    human prose for the emitted envelope.
    """


def _apply_gate_edits(
    document: TOMLDocument, selection: GateSelection
) -> dict[str, object]:
    """Edit the named gate booleans in ``document`` and return the changed keys.

    Each non-``None`` field of ``selection`` edits its matching on-disk key in
    place; the returned mapping is the write-shaped ``result`` naming only the
    gates actually changed (design §3.3 — a mutator names what it changed).
    """
    knitting_changed: dict[str, bool] = {}
    knitting_args = (
        selection.knitting_30,
        selection.knitting_50,
        selection.knitting_80,
    )
    for (_arg_name, disk_key), value in zip(_KNITTING_KEYS, knitting_args, strict=True):
        if value is not None:
            document["gates"]["knitting"][disk_key] = value
            knitting_changed[disk_key] = value
    result: dict[str, object] = {}
    if knitting_changed:
        result["knitting"] = knitting_changed
    if selection.final is not None:
        document["gates"]["final"]["final_pass_complete"] = selection.final
        result["final"] = {"final_pass_complete": selection.final}
    return {"gates": result}


def _set_gate(selection: GateSelection) -> CommandOutcome:
    """Assert gate booleans to their ratio-mandated value; refuse a clash exit ``3``.

    The repair mutator for a gate that lags its ratio (Decision D4). Following the
    ``set_cursor`` skeleton — which does **not** refuse an incoherent prior — it
    edits each named gate and validates only the *proposed* state. The §5.2
    ``gate-ratio-consistent`` invariant binds the three knitting gates to
    ``drafted_ratio >= threshold``, so asserting a knitting gate true below its
    threshold (or false once crossed) is refused with exit ``3``;
    ``final_pass_complete`` has no §5.2 binding. The legitimate observable flip is
    the incoherent→coherent repair (a gate the ratio has crossed but the boolean
    still lags); from an already-coherent prior it is an idempotent no-op. A
    no-flag call is handled by :func:`_set_gate_or_usage` (exit ``2``), so this
    body always has a flag set.

    Returns
    -------
    CommandOutcome
        ``ExitCode.SUCCESS`` once the coherent gates are written, carrying the
        changed gates in a write-shaped ``result`` (only the keys actually set).

    Raises
    ------
    StateInputError
        When the state is missing/unparseable/incomplete, or a proposed gate
        contradicts the drafted ratio (each the exit-``3`` channel).
    """
    path = _state_path()
    document = _load_document_or_state_error(path)
    # Derive the typed view first to prove the document is structurally complete
    # (a missing ``[gates]`` table would otherwise make the edit below raise
    # uncaught -> exit 1, breaching the exit-3 contract). The view is discarded;
    # the document remains the write source.
    _state_view_or_state_error(document)
    result = _apply_gate_edits(document, selection)
    proposed = _state_view_or_state_error(document)
    _refuse_if_incoherent(proposed, context="set-gate")
    write_document_atomically(document, path)
    return CommandOutcome(
        code=ExitCode.SUCCESS,
        result=result,
        messages=["gate flags asserted to their ratio-mandated value"],
    )


def _set_gate_or_usage(selection: GateSelection) -> CommandOutcome:
    """Run :func:`_set_gate`, mapping the no-flag usage fault to exit ``2``.

    A no-flag ``set-gate`` parses cleanly to ``{}`` (Cyclopts does not reject it),
    so the :meth:`GateSelection.any_set` check here is what raises
    :class:`GateDraftingUsageError`; this thin adapter — not the runner — owns the
    exit-``2`` envelope, mirroring ``_desloppify._scan_or_usage`` (ExecPlan
    Decision D9; Surprise S3).

    Returns
    -------
    CommandOutcome
        The ``set-gate`` outcome, or an ``ExitCode.USAGE_ERROR`` outcome when no
        flag was supplied.
    """
    try:
        return _set_gate(_require_any_flag(selection))
    except GateDraftingUsageError as exc:
        return CommandOutcome(
            code=ExitCode.USAGE_ERROR, messages=list(exc.messages) or [str(exc)]
        )


def _require_any_flag(selection: GateSelection) -> GateSelection:
    """Return ``selection`` unchanged, or raise the no-flag usage fault.

    Extracted from :func:`_set_gate_or_usage` so the ``raise`` does not sit inside
    that function's ``try`` block (Ruff ``TRY301``).
    """
    if not selection.any_set:
        msg = "set-gate requires at least one flag"
        raise GateDraftingUsageError(msg)
    return selection


def _complete_final_pass() -> CommandOutcome:
    """Flip ``[gates.final].final_pass_complete`` true; idempotent (design §4.1).

    The convenience verb for the common final-pass flip (``set-gate --final`` is
    the general form). Following the ``set_cursor`` skeleton: load, prove
    structural completeness, set the gate true, run the §5.2 validate-before-persist
    pass (defence in depth — the final gate has no §5.2 binding), and write
    atomically. Re-running on an already-true state re-writes the same value and
    exits ``0``.

    Returns
    -------
    CommandOutcome
        ``ExitCode.SUCCESS`` once ``final_pass_complete`` is written true, with a
        write-shaped ``result``.

    Raises
    ------
    StateInputError
        When the state is missing/unparseable/incomplete (the exit-``3`` channel).
    """
    path = _state_path()
    document = _load_document_or_state_error(path)
    _state_view_or_state_error(document)
    document["gates"]["final"]["final_pass_complete"] = True
    proposed = _state_view_or_state_error(document)
    _refuse_if_incoherent(proposed, context="complete-final-pass")
    write_document_atomically(document, path)
    return CommandOutcome(
        code=ExitCode.SUCCESS,
        result={"gates": {"final": {"final_pass_complete": True}}},
        messages=["final pass marked complete"],
    )


def _set_fangirl(*, last_chapter: int) -> CommandOutcome:
    """Set ``drafting.fangirl.last_chapter_passed``; refuse out-of-manifest exit ``3``.

    Write-time precondition (Decision D6): ``0 <= last_chapter <= len(chapters)`` —
    a fangirl pass cannot have run on a chapter the manifest does not contain, and
    ``0`` means no pass yet. The precondition is checked *before* the §5.2
    validate-before-persist pass, mirroring ``set-chapters``'
    ``manifest_coherence_violations`` (ADR 008). A breach refuses with exit ``3``
    naming ``fangirl-chapter-in-manifest`` and writes nothing.

    Returns
    -------
    CommandOutcome
        ``ExitCode.SUCCESS`` once the value is written, with a write-shaped
        ``result``.

    Raises
    ------
    StateInputError
        When the state is missing/unparseable/incomplete, or ``last_chapter`` is
        outside ``[0, len(chapters)]`` (each the exit-``3`` channel).
    """
    path = _state_path()
    document = _load_document_or_state_error(path)
    prior = _state_view_or_state_error(document)
    chapter_count = len(prior.chapters)
    if not 0 <= last_chapter <= chapter_count:
        summary = (
            "set-fangirl refuses an out-of-manifest chapter: "
            "fangirl-chapter-in-manifest"
        )
        detail = (
            f"last_chapter={last_chapter} is outside [0, {chapter_count}] for the "
            f"current manifest"
        )
        raise StateInputError(summary, detail)
    document["drafting"]["fangirl"]["last_chapter_passed"] = last_chapter
    proposed = _state_view_or_state_error(document)
    _refuse_if_incoherent(proposed, context="set-fangirl")
    write_document_atomically(document, path)
    return CommandOutcome(
        code=ExitCode.SUCCESS,
        result={"drafting": {"fangirl": {"last_chapter_passed": last_chapter}}},
        messages=[f"fangirl last chapter passed set to {last_chapter}"],
    )


def _set_critic_pass(*, pass_number: int) -> CommandOutcome:
    """Set ``drafting.critic.pass``; refuse ``pass < 1`` with exit ``3``.

    Write-time precondition (Decision D6): ``pass >= 1`` (passes are numbered from
    1; state-layout.md "Critic sub-state"). Checked *before* the §5.2
    validate-before-persist pass, mirroring ``set-chapters``'
    ``manifest_coherence_violations`` (ADR 008). A breach refuses with exit ``3``
    naming ``critic-pass-at-least-one`` and writes nothing. The §5.2 critic
    sub-rules bound ``consecutive_clean``/``convergence_target``, not ``pass``, so
    a coherent prior stays coherent (the pass is the on-disk ``pass`` key; the
    typed attribute is ``CriticState.pass_number``). The CLI flag is ``--pass``.

    Returns
    -------
    CommandOutcome
        ``ExitCode.SUCCESS`` once the value is written, with a write-shaped
        ``result``.

    Raises
    ------
    StateInputError
        When the state is missing/unparseable/incomplete, or ``pass_number`` is
        below 1 (each the exit-``3`` channel).
    """
    path = _state_path()
    document = _load_document_or_state_error(path)
    _state_view_or_state_error(document)
    if pass_number < 1:
        summary = "set-critic-pass refuses a pass below 1: critic-pass-at-least-one"
        detail = f"pass={pass_number} is below the minimum of 1"
        raise StateInputError(summary, detail)
    document["drafting"]["critic"]["pass"] = pass_number
    proposed = _state_view_or_state_error(document)
    _refuse_if_incoherent(proposed, context="set-critic-pass")
    write_document_atomically(document, path)
    return CommandOutcome(
        code=ExitCode.SUCCESS,
        result={"drafting": {"critic": {"pass": pass_number}}},
        messages=[f"critic pass set to {pass_number}"],
    )


def register_gate_drafting_commands(app: cyclopts.App) -> None:
    """Register the four gate/drafting subcommands on ``app`` (design §4.1).

    Defines the four ``@app.command`` wrappers on the passed-in ``app``, keeping
    the registration off :mod:`novel_ralph_skill.commands.novel_state` so that
    module stays under the 400-line cap (Decision D11/B4). ``@app.command``
    registers a decorated function onto any :class:`cyclopts.App` regardless of the
    defining module, so the wrappers may be defined here and applied to the app
    :func:`~novel_ralph_skill.commands.novel_state.build_app` passes in. The
    ``set-gate`` wrapper calls :func:`_set_gate_or_usage` (so the no-flag exit-``2``
    guard is always in the path); ``set-critic-pass`` exposes its ``pass_number``
    body parameter under the ``--pass`` CLI flag via an explicit
    :class:`cyclopts.Parameter`.

    Parameters
    ----------
    app : cyclopts.App
        The ``novel-state`` app to register the four subcommands on.
    """

    @app.command(name="set-gate")
    def set_gate(
        *,
        knitting_30: bool | None = None,
        knitting_50: bool | None = None,
        knitting_80: bool | None = None,
        final: bool | None = None,
    ) -> CommandOutcome:
        """Assert gate booleans to their ratio-mandated value; refuse a clash exit 3."""
        return _set_gate_or_usage(
            GateSelection(
                knitting_30=knitting_30,
                knitting_50=knitting_50,
                knitting_80=knitting_80,
                final=final,
            )
        )

    @app.command(name="complete-final-pass")
    def complete_final_pass() -> CommandOutcome:
        """Flip ``gates.final.final_pass_complete`` true (idempotent)."""
        return _complete_final_pass()

    @app.command(name="set-fangirl")
    def set_fangirl(*, last_chapter: int) -> CommandOutcome:
        """Set ``drafting.fangirl.last_chapter_passed``; refuse out-of-manifest."""
        return _set_fangirl(last_chapter=last_chapter)

    @app.command(name="set-critic-pass")
    def set_critic_pass(
        *,
        pass_number: typ.Annotated[int, cyclopts.Parameter(name="--pass")],
    ) -> CommandOutcome:
        """Set ``drafting.critic.pass``; refuse ``pass < 1`` with exit 3."""
        return _set_critic_pass(pass_number=pass_number)
