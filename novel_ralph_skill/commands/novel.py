"""The ``novel`` multiplexer dispatcher and its console-script entry point.

ADR 007 (superseding ADR 005) fixes the final command surface as a single
``novel`` multiplexer: ``novel state …``, ``novel done``, ``novel compile``,
``novel desloppify``, and ``novel wordcount``. This module delivers the parent
app that mounts the five leaf/state sub-apps and the :func:`main` entry point that
drives it through the contract-level :func:`novel_ralph_skill.contract.runner.drive`
seam (which owns the build-``RunContext``-then-call-``run`` plumbing once and
forwards to the shared ``run`` wrapper; roadmap task 7.3.5). It is a pure dispatch
layer: it adds no command logic, reuses each operation's existing ``build_app``
unchanged, and emits the same envelope and exit codes the contract demands.

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

from novel_ralph_skill.commands.names import (
    MULTIPLEXER_NAME,
    SUBCOMMAND_NAMES,
    verb_for,
)
from novel_ralph_skill.commands.state_sourcing import resolved_working_dir
from novel_ralph_skill.contract import drive, parse_global_flags
from novel_ralph_skill.contract.runner import make_contract_app

if typ.TYPE_CHECKING:
    import collections.abc as cabc

    import cyclopts

# The mount name (``state``/``done``/…) for each spaced subcommand name, resolved
# through the registry accessor so the dispatcher never re-spells the verbs inline
# (Decision Log D4; roadmap task 7.3.8). ``"novel done"`` -> ``"done"``.
_VERB_FOR_SUBCOMMAND: dict[str, str] = {
    name: verb_for(name) for name in SUBCOMMAND_NAMES
}
# The reverse: the leading non-flag token (``"state"``) -> its spaced registry
# name (``"novel state"``). Consulted by :func:`_command_name_for`.
_SUBCOMMAND_FOR_VERB: dict[str, str] = {
    verb: name for name, verb in _VERB_FOR_SUBCOMMAND.items()
}


def _build_mount_table() -> dict[str, cabc.Callable[[], cyclopts.App]]:
    """Return the verb-keyed construction table for the five mounted leaves.

    The table maps each mount verb to its leaf module's ``build_app`` *factory*
    (the bound function, not its return value), so the mount loop calls each
    factory exactly once at mount time — the same "build then mount" sequencing
    the hand-copied lines used. The keys are the registry's **bare verbs**
    (``"state"``, ``"done"``, …) — the values ``_VERB_FOR_SUBCOMMAND`` maps each
    spaced name to, and the keys ``_SUBCOMMAND_FOR_VERB`` carries — in the ADR 007
    surface order.

    The five leaf imports live inside this helper, not at module scope, so
    importing :mod:`novel_ralph_skill.commands.novel` pulls in no leaf module;
    only calling this helper does. This preserves the per-command import laziness
    the retired ``stub.py`` relied on (ExecPlan Decision Log D2).

    Returns
    -------
    dict[str, cabc.Callable[[], cyclopts.App]]
        An ordered mapping of bare mount verb to the leaf module's ``build_app``
        factory, in registry/surface order.
    """
    # Deferred imports: mirror the retired ``stub.py``'s per-command laziness so
    # building the table is the only place that pulls the five leaf modules in.
    from novel_ralph_skill.commands import (
        _compile,
        _desloppify,
        _novel_done,
        _wordcount,
        novel_state,
    )

    return {
        "state": novel_state.build_app,
        "done": _novel_done.build_app,
        "compile": _compile.build_app,
        "desloppify": _desloppify.build_app,
        "wordcount": _wordcount.build_app,
    }


def build_multiplexer() -> cyclopts.App:
    """Build the ``novel`` parent app mounting state and the four leaf verbs.

    The parent is itself a contract app (built by
    :func:`novel_ralph_skill.contract.runner.make_contract_app`), so it carries
    the four-flag contract and returns each mounted leaf's
    :class:`~novel_ralph_skill.contract.runner.CommandOutcome` to ``run``
    unchanged. Rather than re-spelling each verb in a hand-copied
    ``app.command(...)`` line, the five leaves are mounted by iterating a single
    registry-driven construction table (:func:`_build_mount_table`) in
    ``_SUBCOMMAND_FOR_VERB`` order: each verb comes from the registry (no inline
    verb literals survive), so the names the dispatcher mounts cannot drift from
    the names it stamps. A verb the registry names but the table omits raises a
    loud, test-caught ``KeyError`` rather than silently dropping a mount.

    The deferred leaf imports live in :func:`_build_mount_table`, so importing
    this module still pulls in no leaf module; the import-laziness profile is
    unchanged. Mounting a child via ``app.command(child, name=…)`` copies only the
    child's group and version defaults, never its contract flags (verified against
    the locked Cyclopts 4.18.0), so each mounted leaf keeps its four-flag
    contract.

    Returns
    -------
    cyclopts.App
        The configured ``novel`` parent app exposing ``state``, ``done``,
        ``compile``, ``desloppify``, and ``wordcount`` as sub-apps.
    """
    app = make_contract_app(MULTIPLEXER_NAME)
    table = _build_mount_table()
    for verb in _SUBCOMMAND_FOR_VERB:
        app.command(table[verb](), name=verb)
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

    The first non-flag token is treated as the verb on the assumption that every
    *global* flag is value-less (it carries no separate value token). That holds
    today: ``--human`` is the only global flag and
    :func:`novel_ralph_skill.contract.runner.parse_global_flags` strips it whole.
    Should a future global flag carry its own value (``--config foo.toml``), that
    value would survive into the residual argv and be misread here as the verb.
    The guard below pins the assumption: it resolves only registry-known verbs,
    falling back to the bare ``"novel"`` surface name for any unrecognised token,
    so a stray value can never be stamped as a subcommand name. A value-carrying
    global flag must therefore strip its value in ``parse_global_flags`` *and* be
    routed here explicitly before this function can see it.

    Parameters
    ----------
    residual : list[str]
        The argv with every value-less global flag (today only ``--human``)
        already split off (the tokens ``run`` parses).

    Returns
    -------
    str
        The spaced subcommand name (``"novel state"`` …) or the bare ``"novel"``.
    """
    verb = next((token for token in residual if not token.startswith("-")), None)
    if verb is None:
        return MULTIPLEXER_NAME
    # Resolve only registry-known verbs; any other token (an unknown verb, or a
    # stray value left by a hypothetical value-carrying global flag) falls back
    # to the bare surface name rather than being stamped as a subcommand.
    return _SUBCOMMAND_FOR_VERB.get(verb, MULTIPLEXER_NAME)


def main() -> None:
    """``novel`` console-script entry point: parse ``--human``, delegate to ``drive``.

    A thin entry point that owns no drive plumbing of its own: it splits the
    single ``--human`` global flag off ``sys.argv`` (before the seam is reached,
    because the run wrapper stamps the human selection into every envelope,
    including the body-less arms), derives the spaced command name from the
    residual argv, and delegates to the contract-level
    :func:`novel_ralph_skill.contract.runner.drive` seam, the single home for the
    build-``RunContext``-then-call-``run`` plumbing (roadmap task 7.3.5). The seam
    forwards to ``run``, which owns every ``sys.exit`` and every envelope
    emission; ``main`` re-spells none of that plumbing inline (pinned by
    ``tests/test_entry_point_single_home.py``).

    The ``working_dir`` it stamps is the *absolute, resolved* path the command
    looked at (``resolved_working_dir()``), not the bare ``"working"`` token, so
    a misresolution — for example a stray ``cd`` into ``working/`` — is visible
    in the envelope field the agent already reads as ``.../working/working``
    rather than failing silently (roadmap §6.3.4; Decision Log D2). Resolution
    semantics are unchanged: the path stays cwd-relative (rule at
    ``state_sourcing.py:52-67``); only the *reported* value becomes absolute.
    """
    human, residual = parse_global_flags(sys.argv[1:])
    name = _command_name_for(residual)
    drive(
        build_multiplexer(),
        residual,
        command=name,
        working_dir=str(resolved_working_dir()),
        human=human,
    )
