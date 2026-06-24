"""Generic scalar-coercion helpers for the rule-pack validating boundary.

These are the schema-agnostic primitives the loader in
``novel_ralph_skill/rulepack/parse.py`` builds on: a message-prefix helper
(:func:`_where`), an unknown-key rejector (:func:`_reject_unknown_keys`), and the
``_require*`` family that reads a key and narrows its value to a concrete scalar
type, converting any missing or wrong-typed fault into a :class:`RulePackError`
that names the offending rule (or the pack level).

They are extracted into this leaf module purely to keep ``parse.py`` under the
AGENTS.md 400-line file cap; they carry no public surface (every name is
underscore-prefixed) and ``parse.py`` re-imports what it needs.
"""

from __future__ import annotations

import collections.abc as cabc

from novel_ralph_skill.rulepack.errors import RulePackError

# A decoded rule pack and each of its ``[[rule]]`` entries is a mapping; a single
# alias documents that shape for the validating helpers below.
type _Mapping = cabc.Mapping[str, object]


def _where(rule_id: str | None) -> str:
    """Return a message prefix naming the offending rule, or the pack level.

    Every helper's error message starts with this so the message is
    self-describing for the envelope task 5.1.2 builds — a per-rule fault names
    the rule, a pack-level fault says so.

    Parameters
    ----------
    rule_id : str | None
        The offending rule's ``id``, or ``None`` for a pack-level fault.

    Returns
    -------
    str
        ``"rule '<id>'"`` for a per-rule fault, or ``"rule pack"`` otherwise.
    """
    return f"rule {rule_id!r}" if rule_id is not None else "rule pack"


def _reject_unknown_keys(
    mapping: _Mapping, allowed: frozenset[str], *, rule_id: str | None
) -> None:
    """Raise :class:`RulePackError` if ``mapping`` carries any key outside ``allowed``.

    An unknown key is rejected rather than silently ignored so a misspelled
    field (for example a rule carrying ``thresold`` or a pack carrying a stray
    top-level ``extra``) fails loudly, naming the offending rule (or the pack
    level). This is the strict loud-failure reading roadmap 5.1.1 demands.

    Parameters
    ----------
    mapping : collections.abc.Mapping[str, object]
        The decoded pack table or rule entry to inspect.
    allowed : frozenset[str]
        The complete set of known keys for this level.
    rule_id : str | None
        The offending rule's ``id``, or ``None`` for a pack-level fault.

    Raises
    ------
    RulePackError
        If ``mapping`` carries any key not in ``allowed``.
    """
    unknown = sorted(key for key in mapping if key not in allowed)
    if unknown:
        listed = ", ".join(repr(key) for key in unknown)
        permitted = ", ".join(repr(key) for key in sorted(allowed))
        msg = (
            f"{_where(rule_id)} has unknown key(s) {listed}; "
            f"allowed keys are {permitted}"
        )
        raise RulePackError(msg, rule_id=rule_id)


def _require(mapping: _Mapping, key: str, *, rule_id: str | None) -> object:
    """Return ``mapping[key]`` or raise :class:`RulePackError` naming the gap.

    Used in place of ``mapping[key]`` so a missing field never surfaces as a raw
    ``KeyError``; the raised error names ``key`` and the offending ``rule_id``.

    Parameters
    ----------
    mapping : collections.abc.Mapping[str, object]
        The decoded pack or rule entry to read.
    key : str
        The required key.
    rule_id : str | None
        The offending rule's ``id``, or ``None`` for a pack-level fault.

    Returns
    -------
    object
        The value at ``key``.

    Raises
    ------
    RulePackError
        If ``key`` is absent from ``mapping``.
    """
    if key not in mapping:
        msg = f"{_where(rule_id)} is missing required key {key!r}"
        raise RulePackError(msg, rule_id=rule_id)
    return mapping[key]


def _require_str(mapping: _Mapping, key: str, *, rule_id: str | None) -> str:
    """Return ``mapping[key]`` as a ``str`` or raise naming the non-string field.

    Parameters
    ----------
    mapping : collections.abc.Mapping[str, object]
        The decoded pack or rule entry to read.
    key : str
        The required key.
    rule_id : str | None
        The offending rule's ``id``, or ``None`` for a pack-level fault.

    Returns
    -------
    str
        The string value at ``key``.

    Raises
    ------
    RulePackError
        If ``key`` is absent or its value is not a ``str``.
    """
    value = _require(mapping, key, rule_id=rule_id)
    if not isinstance(value, str):
        msg = (
            f"{_where(rule_id)} key {key!r} must be a string, "
            f"got {type(value).__name__}"
        )
        raise RulePackError(msg, rule_id=rule_id)
    # The runtime guard above has already narrowed ``value`` to ``str``.
    return value


def _require_int(mapping: _Mapping, key: str, *, rule_id: str | None) -> int:
    """Return ``mapping[key]`` as an ``int`` or raise naming the non-integer field.

    Rejects ``bool`` explicitly: ``isinstance(True, int)`` is ``True`` in Python,
    so a TOML ``true`` would otherwise be accepted as ``1``. A TOML float or
    string for a numeric field raises rather than being coerced.

    Parameters
    ----------
    mapping : collections.abc.Mapping[str, object]
        The decoded pack or rule entry to read.
    key : str
        The required key.
    rule_id : str | None
        The offending rule's ``id``, or ``None`` for a pack-level fault.

    Returns
    -------
    int
        The integer value at ``key``.

    Raises
    ------
    RulePackError
        If ``key`` is absent, its value is a ``bool``, or its value is not an
        ``int``.
    """
    value = _require(mapping, key, rule_id=rule_id)
    if isinstance(value, bool) or not isinstance(value, int):
        msg = (
            f"{_where(rule_id)} key {key!r} must be an integer, "
            f"got {type(value).__name__}"
        )
        raise RulePackError(msg, rule_id=rule_id)
    # The runtime guard above has already narrowed ``value`` to ``int``.
    return value
