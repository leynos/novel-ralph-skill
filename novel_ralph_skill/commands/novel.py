"""The ``novel`` multiplexer dispatcher and its console-script entry point.

ADR 007 (superseding ADR 005) fixes the final command surface as a single
``novel`` multiplexer: ``novel state …``, ``novel done``, ``novel compile``,
``novel desloppify``, and ``novel wordcount``. This module delivers the parent
app that mounts the five leaf/state sub-apps and the :func:`main` entry point that
drives it through the shared :func:`novel_ralph_skill.contract.runner.run`
wrapper. It is a pure dispatch layer: it adds no command logic, reuses each
operation's existing ``build_app`` unchanged, and emits the same envelope and
exit codes the five legacy entry points already produce.

The mechanism is verified against the locked Cyclopts 4.18.0 (ExecPlan Decision
Log D2/D3): mounting a child via ``parent.command(child, name=…)`` copies only
the child's group and version defaults, never its contract flags, so each mounted
leaf keeps its four-flag contract and the parent (also a contract app) returns the
leaf body's :class:`~novel_ralph_skill.contract.runner.CommandOutcome` to ``run``
unchanged. A usage fault (unknown subcommand, extra positional, unknown option)
raises a ``CycloptsError`` subclass that ``run`` maps to exit ``2``; ``--help``/
``--version`` and a bare ``novel`` return ``None``, which ``run`` treats as the
help/version path (exit ``0``, no envelope).

The entry point resolves the spaced subcommand name from the residual argv
*before* ``run`` is called, because ``run`` stamps ``RunContext.command`` into
every envelope, including the body-less exit-2/exit-3 arms (Decision Log D4). The
name is derived from the leading non-flag token through the command-name registry
(:mod:`novel_ralph_skill.commands.names`), defaulting to the bare ``"novel"``
surface name when no subcommand token is present.
"""

from __future__ import annotations

import sys
import typing as typ

from novel_ralph_skill.commands.names import MULTIPLEXER_NAME, SUBCOMMAND_NAMES
from novel_ralph_skill.commands.novel_state import WORKING_DIR_NAME
from novel_ralph_skill.contract import RunContext, parse_global_flags, run
from novel_ralph_skill.contract.runner import make_contract_app

if typ.TYPE_CHECKING:
    import cyclopts

# The mount name (``state``/``done``/…) for each spaced subcommand name, derived
# once from the registry so the dispatcher never re-spells the verbs inline
# (Decision Log D4). ``"novel done"`` -> ``"done"``.
_VERB_FOR_SUBCOMMAND: dict[str, str] = {
    name: name.split(" ", 1)[1] for name in SUBCOMMAND_NAMES
}
# The reverse: the leading non-flag token (``"state"``) -> its spaced registry
# name (``"novel state"``). Consulted by :func:`_command_name_for`.
_SUBCOMMAND_FOR_VERB: dict[str, str] = {
    verb: name for name, verb in _VERB_FOR_SUBCOMMAND.items()
}


def build_multiplexer() -> cyclopts.App:
    """Build the ``novel`` parent app mounting state and the four leaf verbs.

    The parent is itself a contract app (built by
    :func:`novel_ralph_skill.contract.runner.make_contract_app`), so it carries
    the four-flag contract and returns each mounted leaf's
    :class:`~novel_ralph_skill.contract.runner.CommandOutcome` to ``run``
    unchanged. The five ``build_app`` builders are imported inside this function
    so the dispatcher preserves the per-command import laziness ``stub.py``
    already relies on (the leaf modules pull in their state/predicate machinery
    only when the multiplexer is actually built).

    Returns
    -------
    cyclopts.App
        The configured ``novel`` parent app exposing ``state``, ``done``,
        ``compile``, ``desloppify``, and ``wordcount`` as sub-apps.
    """
    # Deferred imports: mirror ``stub.py``'s per-command laziness so building the
    # multiplexer is the only place that pulls the five leaf modules in.
    from novel_ralph_skill.commands import (
        _compile,
        _desloppify,
        _novel_done,
        _wordcount,
        novel_state,
    )

    app = make_contract_app(MULTIPLEXER_NAME)
    app.command(novel_state.build_app(), name="state")
    app.command(_novel_done.build_app(), name="done")
    app.command(_compile.build_app(), name="compile")
    app.command(_desloppify.build_app(), name="desloppify")
    app.command(_wordcount.build_app(), name="wordcount")
    return app


def _command_name_for(residual: list[str]) -> str:
    """Map the residual argv to its spaced registry name (Decision Log D4).

    The leading non-flag token is the subcommand verb; it is looked up in the
    registry-derived verb map and resolved to its spaced name (``"state"`` ->
    ``"novel state"``). When no subcommand token is present — a bare ``novel`` or
    a leading global flag such as ``--help`` — or the token is not a registered
    verb (a usage fault the parser will reject), the bare ``"novel"`` surface name
    is returned so the body-less help/version/usage arms still stamp a
    registry-valid command name.

    Parameters
    ----------
    residual : list[str]
        The argv with ``--human`` already split off (the tokens ``run`` parses).

    Returns
    -------
    str
        The spaced subcommand name (``"novel state"`` …) or the bare ``"novel"``.
    """
    verb = next((token for token in residual if not token.startswith("-")), None)
    if verb is None:
        return MULTIPLEXER_NAME
    return _SUBCOMMAND_FOR_VERB.get(verb, MULTIPLEXER_NAME)


def main() -> None:
    """``novel`` console-script entry point: parse ``--human``, drive via ``run``.

    Generalises the ``_drive`` shape ``stub.py`` uses: it splits the single
    ``--human`` global flag off ``sys.argv`` (before ``run`` is reached, because
    ``run`` stamps the human selection into every envelope, including the
    body-less arms), derives the spaced command name from the residual argv, and
    drives the whole multiplexer through ``run`` exactly once. ``run`` owns every
    ``sys.exit`` and every envelope emission.
    """
    human, residual = parse_global_flags(sys.argv[1:])
    name = _command_name_for(residual)
    run(
        build_multiplexer(),
        residual,
        RunContext(command=name, working_dir=WORKING_DIR_NAME, human=human),
    )
