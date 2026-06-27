"""Shared envelope-skeleton and type assertions for the cross-command suite.

These helpers express the *identity* claim every cross-command module asserts:
that a parsed machine envelope carries the six contract-fixed keys in order
(:data:`ENVELOPE_KEY_ORDER`), with the contract field types, the fixed
``working_dir`` constant, ``schema_version == 1``, and ``ok`` true if and only
if the exit code is ``0`` (design §3.1, §3.2; ADR-003 Table 2). They are
imported by name across the package (a sibling-module runtime import within one
test package, sanctioned because these are package-internal assertion helpers,
not cross-module fixture or scaffolding values) so the envelope-shape, ok/exit,
error-channel, and mutator-identity modules assert one identity contract rather
than re-spelling it.

This module is inside ``PYTHON_TARGETS`` (``Makefile``), so it carries a module
docstring, a docstring on every helper, and raises :class:`AssertionError`
directly rather than using a bare ``assert``.
"""

from __future__ import annotations

import typing as typ

from novel_ralph_skill.commands.names import ENVELOPE_COMMAND_NAMES
from novel_ralph_skill.contract.envelope import ENVELOPE_SCHEMA_VERSION
from novel_ralph_skill.contract.exit_codes import ExitCode

from . import ENVELOPE_KEY_ORDER, WORKING_DIR_CONSTANT


def _require(condition: bool, message: str) -> None:  # noqa: FBT001
    """Raise :class:`AssertionError` with ``message`` when ``condition`` is false.

    A contract-assertion helper for this non-``test_*`` module: the envelope
    failures it guards are contract violations, not type errors, so they raise
    :class:`AssertionError` (the project convention for helper bodies) rather
    than ``TypeError``. Routing the type checks through one boolean condition
    keeps the call sites free of the ``isinstance``-then-``raise`` shape Ruff's
    ``TRY004`` would otherwise flag, while preserving the contract-assertion
    intent.

    Parameters
    ----------
    condition : bool
        The contract invariant that must hold.
    message : str
        The diagnostic raised when ``condition`` is false.

    Raises
    ------
    AssertionError
        When ``condition`` is false.
    """
    if not condition:
        raise AssertionError(message)


def assert_envelope_skeleton(
    envelope: dict[str, object],
    *,
    command: str,
    code: int,
    working_dir: str = WORKING_DIR_CONSTANT,
) -> None:
    """Assert ``envelope`` carries the shared contract skeleton and field types.

    Asserts the six keys in :data:`ENVELOPE_KEY_ORDER` (``result`` before
    ``messages``), ``command`` equal to ``command`` and a member of
    ``ENVELOPE_COMMAND_NAMES``, ``schema_version`` equal to the contract
    constant, ``ok`` a ``bool`` equal to ``(code == 0)``, ``working_dir`` equal
    to ``working_dir``, ``result`` a mapping, and ``messages`` a sequence of
    ``str``. The ``result`` *contents* are command-specific and asserted
    elsewhere; this helper pins only the shared skeleton and types.

    Parameters
    ----------
    envelope : dict[str, object]
        The parsed machine-mode envelope.
    command : str
        The spaced console name the envelope must name.
    code : int
        The exit code the command exited with; ``ok`` must equal ``(code == 0)``.
    working_dir : str, optional
        The ``working_dir`` value the envelope must stamp. Defaults to
        :data:`WORKING_DIR_CONSTANT`, the fixed token the in-process suite
        asserts. The installed boundary passes the resolved-absolute path
        (roadmap 6.3.4) so its identity mirror can reuse this helper rather than
        re-spell the skeleton inline.

    Raises
    ------
    AssertionError
        If any skeleton, ordering, or type invariant is breached.
    """
    keys = tuple(envelope)
    _require(
        keys == ENVELOPE_KEY_ORDER,
        f"envelope key order {keys!r} != contract order {ENVELOPE_KEY_ORDER!r}",
    )
    _require(
        envelope["command"] == command,
        f"envelope command {envelope['command']!r} != expected {command!r}",
    )
    _require(
        command in ENVELOPE_COMMAND_NAMES,
        f"command {command!r} is not a registered envelope command name",
    )
    _require(
        envelope["schema_version"] == ENVELOPE_SCHEMA_VERSION,
        f"schema_version {envelope['schema_version']!r} != {ENVELOPE_SCHEMA_VERSION!r}",
    )
    ok = envelope["ok"]
    # why: the contract is ``ok`` true iff the exit code is 0 (design §3.1; the
    # roadmap's "0/1 benign" grouping is the harness *response* class, not the
    # ``ok`` field, so benign-negative code 1 stays ``ok: false``). Do not
    # "correct" this to make code 1 ``ok: true``.
    _require(isinstance(ok, bool), f"ok {ok!r} is not a bool")
    _require(
        ok is (code == ExitCode.SUCCESS),
        f"ok {ok!r} does not mirror code {code!r} (ok is true iff code == 0)",
    )
    _require(
        envelope["working_dir"] == working_dir,
        f"working_dir {envelope['working_dir']!r} != {working_dir!r}",
    )
    _require(
        isinstance(envelope["result"], dict),
        f"result {envelope['result']!r} is not a mapping",
    )
    messages = envelope["messages"]
    _require(isinstance(messages, list), f"messages {messages!r} is not a sequence")
    for message in typ.cast("list[object]", messages):
        _require(isinstance(message, str), f"message element {message!r} is not a str")


def redact_skeleton(envelope: dict[str, object]) -> dict[str, object]:
    """Return ``envelope`` with ``result`` and ``messages`` redacted to tokens.

    Reduces a machine envelope to its contract-fixed skeleton so a snapshot pins
    only the shared field set, order, and types and cannot churn on a command's
    payload wording. The per-command ``result`` is pinned separately where its
    shape is stable.

    Parameters
    ----------
    envelope : dict[str, object]
        The parsed machine-mode envelope.

    Returns
    -------
    dict[str, object]
        A new envelope with ``result`` replaced by ``"<result>"`` and
        ``messages`` replaced by ``["<messages>"]``, the other four fields kept.
    """
    return {**envelope, "result": "<result>", "messages": ["<messages>"]}
