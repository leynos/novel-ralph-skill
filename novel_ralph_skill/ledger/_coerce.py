"""Generic scalar-coercion helpers for the device-ledger validating boundary.

These are the schema-agnostic primitives the loader in
``novel_ralph_skill/ledger/parse.py`` builds on: a message-prefix helper
(:func:`_where`), an unknown-key rejector (:func:`_reject_unknown_keys`), and the
``_require*`` family that reads a key and narrows its value to a concrete scalar
type, converting any missing or wrong-typed fault into a :class:`LedgerError`
that names the offending device (or the ledger level).

This is a deliberate near-copy of ``novel_ralph_skill/rulepack/_coerce.py``
rather than a reuse of it: every helper there hard-raises ``RulePackError`` with
``"rule '<id>'"`` wording, so importing them would emit the wrong typed error
(the command routes on the exception type) and the wrong device-naming prose. The
alternative — refactoring the rulepack helpers to take an error factory — would
edit the frozen rule-pack loader, which is an ExecPlan Tolerance trip (the
rule-pack path must stay byte-for-byte unchanged). So the ledger carries its own
``_coerce`` raising :class:`LedgerError` with ``"device '<id>'"`` wording
(ExecPlan WI1 Decision Log; round-1 review condition 1).

They are extracted into this leaf module purely to keep ``parse.py`` under the
AGENTS.md 400-line file cap; they carry no public surface (every name is
underscore-prefixed) and ``parse.py`` re-imports what it needs.
"""

from __future__ import annotations

import collections.abc as cabc

from novel_ralph_skill.ledger.errors import LedgerError

# A decoded device ledger and each of its ``[[device]]`` entries is a mapping; a
# single alias documents that shape for the validating helpers below.
type _Mapping = cabc.Mapping[str, object]


def _where(device_id: str | None) -> str:
    """Return a message prefix naming the offending device, or the ledger level.

    Every helper's error message starts with this so the message is
    self-describing for the envelope task 7.1.2 builds — a per-device fault names
    the device, a ledger-level fault says so.

    Parameters
    ----------
    device_id : str | None
        The offending device's ``id``, or ``None`` for a ledger-level fault.

    Returns
    -------
    str
        ``"device '<id>'"`` for a per-device fault, or ``"device ledger"``
        otherwise.
    """
    return f"device {device_id!r}" if device_id is not None else "device ledger"


def _reject_unknown_keys(
    mapping: _Mapping, allowed: frozenset[str], *, device_id: str | None
) -> None:
    """Raise :class:`LedgerError` if ``mapping`` carries any key outside ``allowed``.

    An unknown key is rejected rather than silently ignored so a misspelled field
    (for example a device carrying ``max_counts`` or a ledger carrying a stray
    top-level ``extra``) fails loudly, naming the offending device (or the ledger
    level). This is the strict loud-failure reading the rule-pack loader
    established (roadmap 5.1.1), carried over to the ledger.

    Parameters
    ----------
    mapping : collections.abc.Mapping[str, object]
        The decoded ledger table or device entry to inspect.
    allowed : frozenset[str]
        The complete set of known keys for this level.
    device_id : str | None
        The offending device's ``id``, or ``None`` for a ledger-level fault.

    Raises
    ------
    LedgerError
        If ``mapping`` carries any key not in ``allowed``.
    """
    unknown = sorted(key for key in mapping if key not in allowed)
    if unknown:
        listed = ", ".join(repr(key) for key in unknown)
        permitted = ", ".join(repr(key) for key in sorted(allowed))
        msg = (
            f"{_where(device_id)} has unknown key(s) {listed}; "
            f"allowed keys are {permitted}"
        )
        raise LedgerError(msg, device_id=device_id)


def _require(mapping: _Mapping, key: str, *, device_id: str | None) -> object:
    """Return ``mapping[key]`` or raise :class:`LedgerError` naming the gap.

    Used in place of ``mapping[key]`` so a missing field never surfaces as a raw
    ``KeyError``; the raised error names ``key`` and the offending ``device_id``.

    Parameters
    ----------
    mapping : collections.abc.Mapping[str, object]
        The decoded ledger or device entry to read.
    key : str
        The required key.
    device_id : str | None
        The offending device's ``id``, or ``None`` for a ledger-level fault.

    Returns
    -------
    object
        The value at ``key``.

    Raises
    ------
    LedgerError
        If ``key`` is absent from ``mapping``.
    """
    if key not in mapping:
        msg = f"{_where(device_id)} is missing required key {key!r}"
        raise LedgerError(msg, device_id=device_id)
    return mapping[key]


def _require_str(mapping: _Mapping, key: str, *, device_id: str | None) -> str:
    """Return ``mapping[key]`` as a ``str`` or raise naming the non-string field.

    Parameters
    ----------
    mapping : collections.abc.Mapping[str, object]
        The decoded ledger or device entry to read.
    key : str
        The required key.
    device_id : str | None
        The offending device's ``id``, or ``None`` for a ledger-level fault.

    Returns
    -------
    str
        The string value at ``key``.

    Raises
    ------
    LedgerError
        If ``key`` is absent or its value is not a ``str``.
    """
    value = _require(mapping, key, device_id=device_id)
    if not isinstance(value, str):
        msg = (
            f"{_where(device_id)} key {key!r} must be a string, "
            f"got {type(value).__name__}"
        )
        raise LedgerError(msg, device_id=device_id)
    # The runtime guard above has already narrowed ``value`` to ``str``.
    return value


def _require_int(mapping: _Mapping, key: str, *, device_id: str | None) -> int:
    """Return ``mapping[key]`` as an ``int`` or raise naming the non-integer field.

    Rejects ``bool`` explicitly: ``isinstance(True, int)`` is ``True`` in Python,
    so a TOML ``true`` would otherwise be accepted as ``1``. A TOML float or
    string for a numeric field raises rather than being coerced.

    Parameters
    ----------
    mapping : collections.abc.Mapping[str, object]
        The decoded ledger or device entry to read.
    key : str
        The required key.
    device_id : str | None
        The offending device's ``id``, or ``None`` for a ledger-level fault.

    Returns
    -------
    int
        The integer value at ``key``.

    Raises
    ------
    LedgerError
        If ``key`` is absent, its value is a ``bool``, or its value is not an
        ``int``.
    """
    value = _require(mapping, key, device_id=device_id)
    if isinstance(value, bool) or not isinstance(value, int):
        msg = (
            f"{_where(device_id)} key {key!r} must be an integer, "
            f"got {type(value).__name__}"
        )
        raise LedgerError(msg, device_id=device_id)
    # The runtime guard above has already narrowed ``value`` to ``int``.
    return value
