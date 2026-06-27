"""Contract-owned naming constants the contract layer enforces.

This module is the single home for the *contract*-level naming data the
``contract`` package owns and validates against (ADR 003; roadmap task 7.3.6).
It carries the command-name vocabulary the envelope guard checks every
``command`` field against, and (once roadmap task 7.3.6 WI2 lands it) the
``working/`` directory name the envelope stamps into every ``working_dir``
field. Both are *contract* facts: the set of valid envelope command names and
the working-directory token are dictated by the shared interface contract, not
by any one command, so they live below the command layer in the ``contract``
package the guard reads.

This module also owns the spaced-name-to-verb derivation
(:data:`SUBCOMMAND_VERBS` and :func:`verb_for`): the bare mount verbs are a pure
function of :data:`SUBCOMMAND_NAMES`, so they are the same class of contract data
and are derived here once rather than re-spelled by each consumer (roadmap task
7.3.8). This module imports nothing from :mod:`novel_ralph_skill.commands`; it is
pure naming data (string literals, derived tuples, and a registry accessor) with
no command dependency, so no ``contract`` -> ``commands`` cycle is possible
(roadmap 7.3.6 ExecPlan Decision Log D1). The console-script binding (``NOVEL_MODULE``,
:func:`~novel_ralph_skill.commands.names.project_scripts_table`) stays in
:mod:`novel_ralph_skill.commands.names`, which *consumes* this vocabulary in the
deliberate downward direction.
"""

from __future__ import annotations

# The bare multiplexer surface name. ``novel`` is the sole console-script the
# package ships and the bare command name the body-less help/version arms stamp
# (ADR 007).
MULTIPLEXER_NAME: str = "novel"
"""The bare ``novel`` multiplexer command name (ADR 007)."""

# The spaced subcommand names the multiplexer stamps into its envelopes, one per
# operation, in the ADR 007 surface order. These are the single source the
# dispatcher's ``_command_name_for`` consults, so it never re-spells the names
# inline (ExecPlan Decision Log D4).
SUBCOMMAND_NAMES: tuple[str, ...] = (
    "novel state",
    "novel done",
    "novel compile",
    "novel desloppify",
    "novel wordcount",
)
"""The five spaced ``novel <verb>`` subcommand names, in surface order."""

# The envelope command-name guard superset: the five spaced subcommand names and
# the bare ``"novel"`` surface (stamped on the body-less help/version arms,
# Decision Log D4). De-duplicated while preserving first-seen order so the guard's
# diagnostic lists the names deterministically.
ENVELOPE_COMMAND_NAMES: tuple[str, ...] = tuple(
    dict.fromkeys((*SUBCOMMAND_NAMES, MULTIPLEXER_NAME))
)
"""The spaced ``novel <verb>`` names plus the bare ``"novel"`` surface."""

# The five bare mount verbs (``"state"``/``"done"``/…), derived once from the
# spaced names so the spaced-name-to-verb split lives in exactly one place. Every
# consumer (the dispatcher, the e2e suite) reads :data:`SUBCOMMAND_VERBS` or
# :func:`verb_for` rather than re-spelling ``split(" ", 1)[1]`` inline
# (audit:1.2.13 Finding 3; audit:1.2.15 Finding 1; roadmap task 7.3.8).
SUBCOMMAND_VERBS: tuple[str, ...] = tuple(
    name.split(" ", 1)[1] for name in SUBCOMMAND_NAMES
)
"""The five bare mount verbs (``"state"`` …), in surface order.

The single derivation of a spaced ``novel <verb>`` name to its bare mount verb.
Every consumer (the dispatcher, the e2e suite) reads this or :func:`verb_for`
rather than re-spelling ``split(" ", 1)[1]`` inline (audit:1.2.13 Finding 3;
audit:1.2.15 Finding 1).
"""

# The spaced-name-to-verb lookup the registry exposes through :func:`verb_for`.
# ``strict=True`` pins the two tuples in lockstep so a future divergence (a name
# without a derived verb, or vice versa) fails loudly at import time.
_VERB_BY_SUBCOMMAND: dict[str, str] = dict(
    zip(SUBCOMMAND_NAMES, SUBCOMMAND_VERBS, strict=True)
)


def verb_for(spaced: str) -> str:
    """Return the bare mount verb for a spaced subcommand name.

    Parameters
    ----------
    spaced : str
        A spaced subcommand name from :data:`SUBCOMMAND_NAMES`, e.g.
        ``"novel state"``.

    Returns
    -------
    str
        The bare mount verb, e.g. ``"state"``.

    Raises
    ------
    KeyError
        If ``spaced`` is not a registered subcommand name. The lookup makes the
        registry the sole authority: only registry-known names resolve, so a typo
        or a non-registry string fails loudly rather than being silently split.

    Examples
    --------
    >>> verb_for("novel desloppify")
    'desloppify'
    """
    return _VERB_BY_SUBCOMMAND[spaced]


# The fixed cwd-relative working directory the design records (design line 151);
# the same constant the entry point stamps into the ``RunContext.working_dir``,
# so the file ``check`` reads and the envelope's ``working_dir`` field cannot
# drift (Decision Log B4/B5). There is no ``--working-dir`` flag. It is a
# *contract* fact — the token every envelope stamps into ``working_dir`` — so it
# is owned here in the contract package and re-exported from
# :mod:`novel_ralph_skill.commands.state_sourcing` for back-compatibility
# (roadmap 7.3.6 WI2).
WORKING_DIR_NAME: str = "working"
"""The fixed cwd-relative ``working/`` directory name (design line 151)."""

__all__ = [
    "ENVELOPE_COMMAND_NAMES",
    "MULTIPLEXER_NAME",
    "SUBCOMMAND_NAMES",
    "SUBCOMMAND_VERBS",
    "WORKING_DIR_NAME",
    "verb_for",
]
