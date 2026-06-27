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

import typing as typ

from novel_ralph_skill.loaderkit import (
    EntriesMessages,
    build_entries,
    compile_pattern,
    load_toml,
    resolve_schema_version,
)
from novel_ralph_skill.rulepack._coerce import _COERCION, _ERRORS, _Mapping
from novel_ralph_skill.rulepack.errors import RulePackError, RulePackFileError
from novel_ralph_skill.rulepack.schema import (
    RULEPACK_SCHEMA_VERSION,
    Rule,
    RuleBasis,
    RulePack,
)

if typ.TYPE_CHECKING:
    import collections.abc as cabc
    from importlib.resources.abc import Traversable

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


# The rule pack's verbatim array-extraction messages, bound onto the shared
# ``entries`` primitive (Decision D-ENTRIES). These strings carry the quoted array
# key, the container noun (``pack``), and the item noun (``rule``) whole — nouns
# the ``CoercionErrors`` pair cannot supply — so they live at this call site, not
# in ``loaderkit``.
_ENTRIES_MESSAGES = EntriesMessages(
    not_array="'rule' must be an array of tables, got {type_name}",
    empty="'rule' array is empty; a pack must declare at least one rule",
    non_mapping="rule at index {index} must be a table, got {type_name}",
)


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
        # ``str(member)`` is deliberate: ``RuleBasis`` is a ``StrEnum`` but its
        # ``__repr__`` is the Enum form (``<RuleBasis.PER_PAGE: 'per_page'>``),
        # not the string value, so ``str(member)`` renders the bare ``'per_page'``
        # a pack author actually types.
        allowed = ", ".join(repr(str(member)) for member in RuleBasis)
        msg = (
            f"{_COERCION.where(rule_id)} has unknown basis {value!r}; "
            f"allowed: {allowed}"
        )
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
        page_words = _COERCION.require_int(entry, "page_words", offending_id=rule_id)
        if page_words <= 0:
            msg = (
                f"{_COERCION.where(rule_id)} 'page_words' must be positive, "
                f"got {page_words}"
            )
            raise RulePackError(msg, rule_id=rule_id)
        return page_words
    if "page_words" in entry:
        # ``str(basis)`` is deliberate: a ``StrEnum``'s ``__repr__`` is the Enum
        # form, so ``str(basis)`` renders the bare ``'manuscript'`` value here.
        msg = (
            f"{_COERCION.where(rule_id)} carries 'page_words' but its basis is "
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

    _COERCION.reject_unknown_keys(entry, _RULE_KEYS, offending_id=rule_id)
    pattern = _COERCION.require_str(entry, "pattern", offending_id=rule_id)
    threshold = _COERCION.require_int(entry, "threshold", offending_id=rule_id)
    if threshold < 0:
        msg = (
            f"{_COERCION.where(rule_id)} 'threshold' must be non-negative, "
            f"got {threshold}"
        )
        raise RulePackError(msg, rule_id=rule_id)
    basis = _resolve_basis(
        _COERCION.require_str(entry, "basis", offending_id=rule_id), rule_id=rule_id
    )
    page_words = _resolve_page_words(entry, basis=basis, rule_id=rule_id)

    return Rule(
        id=rule_id,
        pattern=pattern,
        compiled=compile_pattern(pattern, errors=_ERRORS, offending_id=rule_id),
        threshold=threshold,
        basis=basis,
        page_words=page_words,
    )


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

    Notes
    -----
    :class:`RulePackError` is the *only* exception this pure boundary raises:
    every malformed-content fault is converted into it. File and decode faults
    are not this function's concern — they belong to :func:`load_rulepack`, which
    raises :class:`RulePackFileError`. Task 5.1.2 can therefore catch exactly
    these two types and map each to its exit code.

    The orchestration is the shared ``loaderkit`` validating-parse skeleton
    (roadmap 7.2.6): the head
    :func:`~novel_ralph_skill.loaderkit.parse.resolve_schema_version` rejects
    unknown keys and resolves the version, then the ``pack`` string is read **at
    the head/tail seam** — between the version resolve and the entry-array
    extraction, exactly where the original reads it — so a simultaneously
    missing-``pack`` and bad-``rule``-array input still raises the missing-``pack``
    fault, not the entry-array one. The tail
    :func:`~novel_ralph_skill.loaderkit.parse.build_entries` extracts the array,
    builds each :class:`Rule`, and rejects duplicate ids. The :class:`RulePack`
    construction stays here, at the leaf (the skeleton names no pack type).
    """
    schema_version = resolve_schema_version(
        raw,
        allowed_keys=_PACK_KEYS,
        schema_version_constant=RULEPACK_SCHEMA_VERSION,
        unsupported_noun="rule-pack",
        errors=_ERRORS,
    )
    # Read ``pack`` at the head/tail seam, preserving the live
    # ``pack``-before-``entries`` fault precedence (Decision D-SKELETON-HEAD-TAIL).
    pack = _COERCION.require_str(raw, "pack", offending_id=None)
    rules = build_entries(
        raw,
        array_key="rule",
        entries_messages=_ENTRIES_MESSAGES,
        errors=_ERRORS,
        build_entry=_rule,
    )
    return RulePack(schema_version=schema_version, pack=pack, rules=rules)


def load_rulepack(path: Traversable) -> RulePack:
    """Read and parse a rule pack from ``path`` with ``tomllib``.

    A thin convenience over :func:`parse_rulepack`: it opens ``path`` in binary
    mode, decodes it with the standard-library ``tomllib``, and delegates the
    validated construction. A file fault (absent, unreadable) or an undecodable
    TOML is the exit-3 channel and raises :class:`RulePackFileError`; a
    structurally valid TOML that violates the schema propagates as the exit-2
    :class:`RulePackError` from :func:`parse_rulepack`.

    ``path`` is typed as :class:`~importlib.resources.abc.Traversable` rather than
    :class:`pathlib.Path` so a packaged rule pack resolved through
    :func:`importlib.resources.files` (the §6 ``offenders.toml`` task 5.1.2 ships)
    loads without an unsafe cast — a ``Path`` *is* a ``Traversable``, and this
    function only needs the ``.open("rb")`` the protocol guarantees.

    Parameters
    ----------
    path : importlib.resources.abc.Traversable
        The rule-pack TOML resource: a filesystem :class:`pathlib.Path` (from
        ``--pack``) or a packaged resource (the shipped default).

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
    raw = load_toml(path, noun="rule pack", file_error=RulePackFileError)
    return parse_rulepack(raw)
