"""The validating boundary that builds a typed :class:`RulePack` from TOML.

This module is the single place a decoded rule-pack mapping becomes a typed
:class:`~novel_ralph_skill.rulepack.schema.RulePack`, so no raw
``dict[str, object]`` leaks inward (python-data-shapes: "parse to a schema type
at the boundary"). It mirrors the *structure* of
``novel_ralph_skill/state/parse.py`` — a pure :func:`parse_rulepack` boundary, a
thin :func:`load_rulepack` ``tomllib`` file convenience, every TOML array coerced
to a ``tuple`` — but, unlike ``parse_state``, it is a **validating** boundary.

``parse_state`` narrows with :func:`typing.cast` (which performs no runtime
check) and lets a missing or wrong-typed field surface as a raw ``KeyError`` or
``TypeError``. That discipline cannot satisfy roadmap task 5.1.1's success
criterion — "a pack with an invalid regular expression fails loudly, naming the
rule, rather than silently skipping it". So this module runtime-checks every
field with an ``isinstance``/membership guard and converts every missing,
wrong-typed, or out-of-range fault into a :class:`RulePackError` that names the
offending rule (or is pack-level for a ``schema_version``/``pack``/``rule``-array
fault). A :func:`typing.cast` is used only *after* a runtime guard has already
proven the value's type, to restate that fact for the type checker.

The loader is read-only and detect-only (ADR-001): it compiles each pattern with
the standard-library ``re`` and validates structure, never judging prose. It
calls neither :func:`sys.exit` nor any envelope builder; exit-code translation is
the command body's job (task 5.1.2).
"""

from __future__ import annotations

import re
import tomllib
import typing as typ

from novel_ralph_skill.rulepack.errors import RulePackError, RulePackFileError
from novel_ralph_skill.rulepack.schema import (
    RULEPACK_SCHEMA_VERSION,
    Rule,
    RuleBasis,
    RulePack,
)

if typ.TYPE_CHECKING:
    import collections.abc as cabc
    from pathlib import Path

# A decoded rule pack and each of its ``[[rule]]`` entries is a mapping; a single
# alias documents that shape for the validating helpers below.
type _Mapping = cabc.Mapping[str, object]

# The complete v1 key vocabularies. An unknown key on either the pack table or a
# rule entry is rejected (naming the offending level/rule) rather than silently
# ignored, so a misspelled field (``thresold = 99``) fails loudly — the exact
# "silently skipping a tell" failure mode roadmap 5.1.1 exists to eliminate.
_PACK_KEYS: frozenset[str] = frozenset({"schema_version", "pack", "rule"})
_RULE_KEYS: frozenset[str] = frozenset({
    "id",
    "pattern",
    "threshold",
    "basis",
    "page_words",
})


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


def _entries(raw: _Mapping) -> cabc.Sequence[_Mapping]:
    """Return the non-empty ``rule`` array as a sequence of rule-entry mappings.

    Parameters
    ----------
    raw : collections.abc.Mapping[str, object]
        The decoded rule pack.

    Returns
    -------
    collections.abc.Sequence[collections.abc.Mapping[str, object]]
        The decoded ``[[rule]]`` entries in authoring order.

    Raises
    ------
    RulePackError
        If ``rule`` is absent, is not a list, is empty, or holds a non-mapping
        entry. These are pack-level faults (``rule_id is None``).
    """
    value = _require(raw, "rule", rule_id=None)
    if not isinstance(value, list):
        msg = f"'rule' must be an array of tables, got {type(value).__name__}"
        raise RulePackError(msg, rule_id=None)
    if not value:
        msg = "'rule' array is empty; a pack must declare at least one rule"
        raise RulePackError(msg, rule_id=None)
    for index, entry in enumerate(value):
        if not isinstance(entry, dict):
            msg = f"rule at index {index} must be a table, got {type(entry).__name__}"
            raise RulePackError(msg, rule_id=None)
    return typ.cast("cabc.Sequence[_Mapping]", value)


def _compile_pattern(pattern: str, *, rule_id: str) -> re.Pattern[str]:
    """Compile ``pattern`` or raise :class:`RulePackError` naming ``rule_id``.

    This is the roadmap 5.1.1 headline behaviour: an uncompilable pattern fails
    loudly, naming the offending rule, rather than being silently skipped.
    ``re.compile`` validates eagerly, so a bad pattern is caught at load time.

    Parameters
    ----------
    pattern : str
        The regular-expression source to compile.
    rule_id : str
        The offending rule's ``id``, named in the error on failure.

    Returns
    -------
    re.Pattern[str]
        The compiled pattern.

    Raises
    ------
    RulePackError
        If ``pattern`` does not compile.
    """
    try:
        return re.compile(pattern)
    except re.error as exc:
        msg = f"rule {rule_id!r} has an invalid pattern {pattern!r}: {exc}"
        raise RulePackError(msg, rule_id=rule_id) from exc


def _resolve_basis(value: str, *, rule_id: str) -> RuleBasis:
    """Resolve ``value`` to a :class:`RuleBasis` member or raise naming the rule.

    Parameters
    ----------
    value : str
        The decoded ``basis`` string.
    rule_id : str
        The offending rule's ``id``, named in the error on failure.

    Returns
    -------
    RuleBasis
        The resolved basis member.

    Raises
    ------
    RulePackError
        If ``value`` is not a :class:`RuleBasis` member (the closed-set check).
    """
    try:
        return RuleBasis(value)
    except ValueError as exc:
        allowed = ", ".join(repr(str(member)) for member in RuleBasis)
        msg = f"rule {rule_id!r} has unknown basis {value!r}; allowed: {allowed}"
        raise RulePackError(msg, rule_id=rule_id) from exc


def _resolve_page_words(
    entry: _Mapping, *, basis: RuleBasis, rule_id: str
) -> int | None:
    """Validate ``page_words`` against ``basis`` for one rule entry.

    ``page_words`` is required and a positive integer when ``basis`` is
    :attr:`RuleBasis.PER_PAGE`, and must be absent otherwise (the strict reading,
    advisory A3: a stray ``page_words`` on a non-``per_page`` rule is rejected,
    not ignored).

    Parameters
    ----------
    entry : collections.abc.Mapping[str, object]
        The decoded rule entry.
    basis : RuleBasis
        The rule's resolved basis.
    rule_id : str
        The offending rule's ``id``, named in any error.

    Returns
    -------
    int | None
        The positive page size for a ``per_page`` rule, or ``None`` otherwise.

    Raises
    ------
    RulePackError
        If a ``per_page`` rule omits ``page_words`` or gives a non-positive
        value, or a non-``per_page`` rule carries a stray ``page_words``.
    """
    if basis is RuleBasis.PER_PAGE:
        page_words = _require_int(entry, "page_words", rule_id=rule_id)
        if page_words <= 0:
            msg = f"rule {rule_id!r} 'page_words' must be positive, got {page_words}"
            raise RulePackError(msg, rule_id=rule_id)
        return page_words
    if "page_words" in entry:
        msg = (
            f"rule {rule_id!r} carries 'page_words' but its basis is "
            f"{str(basis)!r}; 'page_words' is only valid for 'per_page'"
        )
        raise RulePackError(msg, rule_id=rule_id)
    return None


def _rule(entry: _Mapping, *, index: int) -> Rule:
    """Build one validated :class:`Rule` from a decoded rule entry.

    Resolves ``id`` first so it can name the rule in any subsequent error this
    entry raises; a missing or non-string ``id`` is a pack-level fault that names
    the rule's array ``index`` instead (there is no id to name yet).

    Parameters
    ----------
    entry : collections.abc.Mapping[str, object]
        The decoded ``[[rule]]`` table.
    index : int
        The rule's zero-based position in the array, named when ``id`` is absent.

    Returns
    -------
    Rule
        The fully validated, frozen rule.

    Raises
    ------
    RulePackError
        On any missing, wrong-typed, or out-of-range field, or any unknown key,
        naming the rule (or its ``index`` when ``id`` itself is the fault).
    """
    if "id" not in entry or not isinstance(entry["id"], str):
        msg = f"rule at index {index} is missing a string 'id'"
        raise RulePackError(msg, rule_id=None)
    # The ``isinstance`` guard above has already narrowed ``entry["id"]``.
    rule_id = entry["id"]

    _reject_unknown_keys(entry, _RULE_KEYS, rule_id=rule_id)
    pattern = _require_str(entry, "pattern", rule_id=rule_id)
    threshold = _require_int(entry, "threshold", rule_id=rule_id)
    if threshold < 0:
        msg = f"rule {rule_id!r} 'threshold' must be non-negative, got {threshold}"
        raise RulePackError(msg, rule_id=rule_id)
    basis = _resolve_basis(
        _require_str(entry, "basis", rule_id=rule_id), rule_id=rule_id
    )
    page_words = _resolve_page_words(entry, basis=basis, rule_id=rule_id)

    return Rule(
        id=rule_id,
        pattern=pattern,
        compiled=_compile_pattern(pattern, rule_id=rule_id),
        threshold=threshold,
        basis=basis,
        page_words=page_words,
    )


def _reject_duplicate_ids(rules: cabc.Sequence[Rule]) -> None:
    """Raise :class:`RulePackError` if two rules share an ``id``.

    Rule ids must be unique so a :class:`RulePackError` (or a later detection
    fault in task 5.1.2) that names ``rule_id`` unambiguously identifies one
    rule. The design does not pin id-uniqueness, so the strictest loud-failure
    reading rejects the collision, naming the duplicated id.

    Parameters
    ----------
    rules : collections.abc.Sequence[Rule]
        The validated rules in authoring order.

    Raises
    ------
    RulePackError
        If any ``id`` appears on more than one rule; the error names that id.
    """
    seen: set[str] = set()
    for rule in rules:
        if rule.id in seen:
            msg = f"rule {rule.id!r} is defined more than once; ids must be unique"
            raise RulePackError(msg, rule_id=rule.id)
        seen.add(rule.id)


def parse_rulepack(raw: cabc.Mapping[str, object]) -> RulePack:
    """Construct a validated :class:`RulePack` from a decoded TOML mapping.

    Pure — a decoded mapping in, a validated :class:`RulePack` out — so any pack
    consumer can reuse it without a filesystem. Every field is runtime-checked
    and every TOML array is coerced to a ``tuple`` at this boundary. A malformed
    pack raises :class:`RulePackError`, naming the offending rule (or pack-level
    for a ``schema_version``/``pack``/``rule``-array fault).

    Parameters
    ----------
    raw : collections.abc.Mapping[str, object]
        The decoded rule-pack mapping, as ``tomllib.load`` returns.

    Returns
    -------
    RulePack
        The fully validated, frozen rule pack.

    Raises
    ------
    RulePackError
        If ``schema_version`` is absent, wrong-typed, or unexpected; if ``pack``
        is absent or non-string; if the ``rule`` array is absent, empty, or holds
        a malformed rule; if any rule field is missing, wrong-typed, or out of
        range; if the pack or any rule carries an unknown key; or if two rules
        share an ``id``.
    """
    _reject_unknown_keys(raw, _PACK_KEYS, rule_id=None)
    schema_version = _require_int(raw, "schema_version", rule_id=None)
    if schema_version != RULEPACK_SCHEMA_VERSION:
        msg = (
            f"unsupported rule-pack schema_version {schema_version}; "
            f"expected {RULEPACK_SCHEMA_VERSION}"
        )
        raise RulePackError(msg, rule_id=None)
    pack = _require_str(raw, "pack", rule_id=None)
    rules = tuple(
        _rule(entry, index=index) for index, entry in enumerate(_entries(raw))
    )
    _reject_duplicate_ids(rules)
    return RulePack(schema_version=schema_version, pack=pack, rules=rules)


def load_rulepack(path: Path) -> RulePack:
    """Read and parse a rule pack from ``path`` with ``tomllib``.

    A thin convenience over :func:`parse_rulepack`: it opens ``path`` in binary
    mode, decodes it with the standard-library ``tomllib``, and delegates the
    validated construction. A file fault (absent, unreadable) or an undecodable
    TOML is the exit-3 channel and raises :class:`RulePackFileError`; a
    structurally valid TOML that violates the schema propagates as the exit-2
    :class:`RulePackError` from :func:`parse_rulepack`.

    Parameters
    ----------
    path : pathlib.Path
        The path to a rule-pack TOML file.

    Returns
    -------
    RulePack
        The fully validated, frozen rule pack parsed from ``path``.

    Raises
    ------
    RulePackFileError
        If ``path`` is absent or unreadable, or its bytes are not decodable TOML.
    RulePackError
        If the decoded pack violates the schema (propagated unchanged).
    """
    try:
        with path.open("rb") as handle:
            raw = tomllib.load(handle)
    except (OSError, tomllib.TOMLDecodeError) as exc:
        # OSError covers FileNotFoundError and PermissionError; TOMLDecodeError
        # is the undecodable-bytes case. All three are the exit-3 file channel.
        msg = f"cannot read rule pack at {path}: {exc}"
        raise RulePackFileError(msg) from exc
    return parse_rulepack(raw)
