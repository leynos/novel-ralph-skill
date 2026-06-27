"""The shared validating-parse skeleton both pack families bind, as a head/tail pair.

The rule-pack and device-ledger ``parse_*`` boundaries carry a structurally
identical *validating parse* orchestration: reject an unknown top-level key,
resolve and reject an unsupported ``schema_version``, extract the non-empty entry
array, build one validated entry per element in authoring order, reject duplicate
ids, and construct the frozen result. Roadmap task 7.2.6 lifts that orchestration
here so exactly one body survives, leaving each ``parse_*`` a thin binding (design
§6.1, §6.3; ADR-001/003), mirroring how task 7.2.2 consolidated the coercion and
scan bodies and task 7.2.5 the error hierarchy.

The skeleton is a **head/tail pair**, not a single all-in-one call, so the rule
pack can interleave its top-level ``pack`` read at the original mid-orchestration
seam and preserve its live ``pack``-before-``entries`` fault precedence (Decision
D-SKELETON-HEAD-TAIL):

- :func:`resolve_schema_version` (the *head*) rejects unknown top-level keys,
  requires ``schema_version``, and rejects any value bar the family constant,
  returning the resolved version.
- :func:`build_entries` (the *tail*) extracts the non-empty entry array, builds
  each entry via the caller's builder in authoring order, rejects duplicate ids,
  and returns the built entry tuple.

Neither half names a pack result type. Following Decision D-RESULT-CALLBACK the
skeleton returns only *neutral* products — the resolved ``schema_version`` int and
the built entry tuple — so each caller constructs its own
:class:`~novel_ralph_skill.rulepack.schema.RulePack`/
:class:`~novel_ralph_skill.ledger.schema.DeviceLedger` at its own call site, where
the rule pack additionally reads its extra top-level ``pack`` string. The two
result arities (the rule pack carries ``pack``, the ledger does not) mean a
skeleton that built the result itself would have to import both pack types,
violating the neutral-leaf invariant.

This module imports only the :mod:`novel_ralph_skill.loaderkit` siblings
(``coerce``, ``load``) it sequences and the standard library; it imports neither
``rulepack`` nor ``ledger`` at runtime or under ``TYPE_CHECKING``, so both packs
may depend on it without an import cycle (design §3.1; ADR-003).
"""

from __future__ import annotations

import typing as typ

from novel_ralph_skill.loaderkit.coerce import (
    CoercionErrors,
    Mapping,
    reject_unknown_keys,
    require_int,
)
from novel_ralph_skill.loaderkit.load import (
    EntriesMessages,
    entries,
    reject_duplicate_ids,
)

if typ.TYPE_CHECKING:
    import collections.abc as cabc


class _HasId(typ.Protocol):
    """The minimal shape the default id projection reads: an ``id`` string.

    Every family's built entry (``Rule``/``Device``) carries a string ``id``, so
    this structural bound lets :func:`_entry_id` serve as ``build_entries``'s
    default ``entry_id`` without the skeleton naming any concrete pack type.
    """

    @property
    def id(self) -> str:
        """The entry's unique id."""


def resolve_schema_version(  # noqa: PLR0913  # pylint: disable=too-many-arguments
    raw: Mapping,
    *,
    allowed_keys: frozenset[str],
    schema_version_constant: int,
    unsupported_noun: str,
    errors: CoercionErrors,
) -> int:
    """Reject unknown keys, require ``schema_version``, and reject an unsupported one.

    This is the *head* of the shared validating-parse skeleton. It performs, in
    order: reject any top-level key outside ``allowed_keys``; require an integer
    ``schema_version``; and reject any value other than ``schema_version_constant``
    with the per-family unsupported-version sentence. It never inspects the entry
    array or the top-level string fields, so a caller may interleave arbitrary work
    (the rule pack's ``pack`` read) between this head and :func:`build_entries` and
    head faults strictly precede tail faults (Decision D-SKELETON-HEAD-TAIL).

    Parameters
    ----------
    raw : Mapping
        The decoded document mapping.
    allowed_keys : frozenset[str]
        The complete set of known top-level keys for this family.
    schema_version_constant : int
        The only ``schema_version`` this family supports.
    unsupported_noun : str
        The hyphenated family noun for the unsupported-version sentence
        (``"rule-pack"`` or ``"device-ledger"``), a distinct string the
        ``CoercionErrors`` noun pair does not carry.
    errors : CoercionErrors
        The bound error factory.

    Returns
    -------
    int
        The resolved, supported ``schema_version``.

    Raises
    ------
    EnvelopeMessagesError
        The caller's content error, if ``raw`` carries an unknown top-level key, if
        ``schema_version`` is absent or not an integer, or if it differs from
        ``schema_version_constant``.
    """
    reject_unknown_keys(raw, allowed_keys, errors=errors, offending_id=None)
    schema_version = require_int(
        raw, "schema_version", errors=errors, offending_id=None
    )
    if schema_version != schema_version_constant:
        msg = (
            f"unsupported {unsupported_noun} schema_version {schema_version}; "
            f"expected {schema_version_constant}"
        )
        raise errors.content_error(msg, None)
    return schema_version


def _entry_id(entry: _HasId) -> str:
    """Return ``entry.id`` — the default id projection :func:`build_entries` uses.

    The duplicate-id pass projects each built entry to its ``id`` through this
    callable, so the skeleton names no concrete pack attribute in its signature
    while every family's built entry (``Rule``/``Device``) carries an ``id``. A
    family whose entry names its id differently passes its own ``entry_id``.

    Parameters
    ----------
    entry : _HasId
        A built entry exposing a string ``id`` attribute.

    Returns
    -------
    str
        The entry's ``id``.
    """
    return entry.id


def build_entries[T: _HasId](  # noqa: PLR0913  # pylint: disable=too-many-arguments
    raw: Mapping,
    *,
    array_key: str,
    entries_messages: EntriesMessages,
    errors: CoercionErrors,
    build_entry: cabc.Callable[[Mapping, int], T],
    entry_id: cabc.Callable[[T], str] = _entry_id,
) -> tuple[T, ...]:
    """Extract, build, and de-duplicate the entry array, returning the built tuple.

    This is the *tail* of the shared validating-parse skeleton. It performs, in
    order: extract the non-empty ``array_key`` array via :func:`entries`; build each
    entry via the caller's ``build_entry`` in authoring order; and reject duplicate
    ids via :func:`reject_duplicate_ids` over the per-family ``entry_id`` projection.
    It never inspects ``schema_version`` or the top-level key set, so it builds an
    array regardless of any head-level fault, leaving the head/tail seam free for a
    caller to interleave work (Decision D-SKELETON-HEAD-TAIL). The id projection is
    a parameter so the skeleton names no concrete pack attribute.

    Parameters
    ----------
    raw : Mapping
        The decoded document mapping.
    array_key : str
        The key holding the array of tables (``"rule"`` or ``"device"``).
    entries_messages : EntriesMessages
        The three verbatim array-extraction fault messages for this family.
    errors : CoercionErrors
        The bound error factory.
    build_entry : collections.abc.Callable[[Mapping, int], T]
        The per-family builder, called ``build_entry(entry, index)`` once per array
        element in authoring order; the skeleton never inspects entry fields itself.
    entry_id : collections.abc.Callable[[T], str], optional
        Projects a built entry to its ``id`` for the duplicate-id pass. Defaults to
        :func:`_entry_id` (``entry.id``); the entry type ``T`` is bound to
        :class:`_HasId`, so the default always type-checks while a family may still
        supply its own projection.

    Returns
    -------
    tuple[T, ...]
        The built entries in authoring order.

    Raises
    ------
    EnvelopeMessagesError
        The caller's content error, if the array is absent, not an array of tables,
        empty, or holds a non-mapping entry; if the builder rejects an entry; or if
        two entries share an ``id``.
    """
    raw_entries = entries(
        raw, array_key=array_key, messages=entries_messages, errors=errors
    )
    built = tuple(build_entry(entry, index) for index, entry in enumerate(raw_entries))
    reject_duplicate_ids((entry_id(entry) for entry in built), errors=errors)
    return built
