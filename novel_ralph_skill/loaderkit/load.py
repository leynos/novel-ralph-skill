"""Shared array-extraction, pattern-compilation, and TOML-load primitives.

These are the structural loader bodies the rule-pack and device-ledger boundaries
share, consolidated by roadmap task 7.2.2 (design §6.1, §6.3; ADR-001):

- :func:`entries` extracts the non-empty ``[[rule]]``/``[[device]]`` array as a
  sequence of mappings;
- :func:`compile_pattern` compiles a pattern eagerly, naming the offending entity
  on failure;
- :func:`reject_duplicate_ids` rejects a repeated id in authoring order;
- :func:`load_toml` opens and decodes a TOML resource, translating a file or
  decode fault into the caller's file-error channel.

Each primitive carries no package knowledge: it raises through the caller's
:class:`~novel_ralph_skill.loaderkit.coerce.CoercionErrors` bundle (or, for
:func:`load_toml`, a separate file-error factory), so one body serves every pack
family. The three array-extraction messages travel whole on an
:class:`EntriesMessages` bundle because their container/item nouns are neither of
the :class:`CoercionErrors` nouns (Decision D-ENTRIES).
"""

from __future__ import annotations

import collections.abc as cabc
import dataclasses
import re
import tomllib
import typing as typ

from novel_ralph_skill.loaderkit.coerce import CoercionErrors, Mapping, require, where

if typ.TYPE_CHECKING:
    from importlib.resources.abc import Traversable

    from novel_ralph_skill.contract.errors import EnvelopeMessagesError


@dataclasses.dataclass(frozen=True, kw_only=True, slots=True)
class EntriesMessages:
    """The three verbatim array-extraction fault messages a pack family supplies.

    The array-extraction faults embed nouns the :class:`CoercionErrors` pair
    cannot supply — the quoted array key (``'rule'``/``'device'``), a container
    noun (``pack``/``ledger``), and an item noun (``rule``/``device``) — so
    :func:`entries` is parameterised on the *full* message strings rather than the
    noun pair (Decision D-ENTRIES). Each caller binds these byte-for-byte from its
    former ``_entries`` body, keeping the shared :func:`entries` body noun-free.

    Attributes
    ----------
    not_array : str
        The "must be an array of tables" template, formatted with the observed
        ``type_name`` (for example
        ``"'rule' must be an array of tables, got {type_name}"``).
    empty : str
        The literal empty-array sentence (for example
        ``"'rule' array is empty; a pack must declare at least one rule"``),
        carrying the array key, container noun, and item noun whole.
    non_mapping : str
        The "at index N must be a table" template, formatted with the ``index``
        and the observed ``type_name`` (for example
        ``"rule at index {index} must be a table, got {type_name}"``).
    """

    not_array: str
    empty: str
    non_mapping: str


def entries(
    mapping: Mapping,
    *,
    array_key: str,
    messages: EntriesMessages,
    errors: CoercionErrors,
) -> cabc.Sequence[Mapping]:
    """Return the non-empty ``array_key`` array as a sequence of entry mappings.

    This is the shared *structural* extraction body: it requires the array, rejects
    a non-:class:`collections.abc.Sequence` (or a ``str``/``bytes``), rejects an
    empty array, rejects any non-:class:`collections.abc.Mapping` entry, and casts
    and returns the sequence. Every rejection is a document-level fault
    (``offending_id`` is ``None``) raising the caller's content error with the
    caller-supplied verbatim message, never routing through :func:`where` — the
    array-extraction prose carries container/item nouns the noun pair cannot supply
    (Decision D-ENTRIES).

    The guards match the abstract shapes the boundary advertises — any
    :class:`collections.abc.Sequence` that is not ``str``/``bytes`` for the array,
    and any :class:`collections.abc.Mapping` for each entry — rather than the
    concrete ``list``/``dict`` ``tomllib`` happens to return, so the boundary
    honours the documented ``Mapping`` input contract.

    Parameters
    ----------
    mapping : Mapping
        The decoded document mapping.
    array_key : str
        The key holding the array of tables (``"rule"`` or ``"device"``).
    messages : EntriesMessages
        The three verbatim fault messages for this pack family.
    errors : CoercionErrors
        The bound error factory.

    Returns
    -------
    collections.abc.Sequence[Mapping]
        The decoded entries in authoring order.

    Raises
    ------
    EnvelopeMessagesError
        The caller's content error, if the array is absent, is not an array of
        tables, is empty, or holds a non-mapping entry.
    """
    value = require(mapping, array_key, errors=errors, offending_id=None)
    if isinstance(value, (str, bytes)) or not isinstance(value, cabc.Sequence):
        msg = messages.not_array.format(type_name=type(value).__name__)
        raise errors.content_error(msg, None)
    if not value:
        raise errors.content_error(messages.empty, None)
    for index, entry in enumerate(value):
        if not isinstance(entry, cabc.Mapping):
            msg = messages.non_mapping.format(
                index=index, type_name=type(entry).__name__
            )
            raise errors.content_error(msg, None)
    return typ.cast("cabc.Sequence[Mapping]", value)


def compile_pattern(
    pattern: str, *, errors: CoercionErrors, offending_id: str
) -> re.Pattern[str]:
    r"""Compile ``pattern`` with no flags, or raise naming ``offending_id``.

    This is the roadmap 5.1.1 headline behaviour shared by every pack family: an
    uncompilable pattern fails loudly, naming the offending entity, rather than
    being silently skipped. ``re.compile`` validates eagerly, so a bad pattern is
    caught at load time; no flags means ``.`` cannot cross ``\n``, matching the
    line-by-line scan the detectors rely on.

    Parameters
    ----------
    pattern : str
        The regular-expression source to compile.
    errors : CoercionErrors
        The bound error factory.
    offending_id : str
        The offending entity's ``id``, named in the error on failure.

    Returns
    -------
    re.Pattern[str]
        The compiled pattern.

    Raises
    ------
    EnvelopeMessagesError
        The caller's content error, if ``pattern`` does not compile. The original
        :class:`re.error` is chained as ``__cause__``.
    """
    try:
        return re.compile(pattern)
    except re.error as exc:
        msg = f"{where(errors, offending_id)} has an invalid pattern {pattern!r}: {exc}"
        raise errors.content_error(msg, offending_id) from exc


def reject_duplicate_ids(ids: cabc.Iterable[str], *, errors: CoercionErrors) -> None:
    """Raise the caller's content error if two entries share an ``id``.

    Ids must be unique so a content error (or a later detection finding) that names
    the id unambiguously identifies one entity. Iterates ``ids`` in authoring
    order, tracking a ``seen`` set, and raises on the **first** id already seen, so
    the named duplicate is the first repeat in authoring order — not whichever id a
    ``Counter`` or set-difference happens to surface.

    Parameters
    ----------
    ids : collections.abc.Iterable[str]
        The validated entity ids, in authoring order.
    errors : CoercionErrors
        The bound error factory.

    Raises
    ------
    EnvelopeMessagesError
        The caller's content error, if any id appears more than once; the error
        names the first repeated id.
    """
    seen: set[str] = set()
    for entity_id in ids:
        if entity_id in seen:
            msg = (
                f"{where(errors, entity_id)} is defined more than once; "
                f"ids must be unique"
            )
            raise errors.content_error(msg, entity_id)
        seen.add(entity_id)


def load_toml(
    path: Traversable,
    *,
    noun: str,
    file_error: cabc.Callable[[str], EnvelopeMessagesError],
) -> dict[str, object]:
    """Read and decode a TOML resource, or raise the caller's file error.

    Opens ``path`` in binary mode and decodes it with the standard-library
    ``tomllib``, returning the decoded mapping. A file fault (absent, unreadable)
    or an undecodable TOML is translated into the caller's file-error channel with
    a ``"cannot read {noun} at {path}"`` message; the noun (``"rule pack"`` /
    ``"device ledger"``) is a parameter so the two packages keep distinct prose.
    Schema validation is the caller's concern, performed on the returned mapping.

    Parameters
    ----------
    path : importlib.resources.abc.Traversable
        The TOML resource: a filesystem :class:`pathlib.Path` or a packaged
        resource. Only the ``.open("rb")`` the protocol guarantees is used.
    noun : str
        The noun phrase naming the resource in a fault message.
    file_error : collections.abc.Callable[[str], EnvelopeMessagesError]
        The caller's file-error constructor (the ``*FileError`` type).

    Returns
    -------
    dict[str, object]
        The decoded TOML mapping.

    Raises
    ------
    EnvelopeMessagesError
        The caller's file error, if ``path`` is absent or unreadable, or its bytes
        are not decodable TOML. The original fault is chained as ``__cause__``.
    """
    try:
        with path.open("rb") as handle:
            return tomllib.load(handle)
    except (OSError, tomllib.TOMLDecodeError) as exc:
        # OSError covers FileNotFoundError and PermissionError; TOMLDecodeError
        # is the undecodable-bytes case. All three are the exit-3 file channel.
        msg = f"cannot read {noun} at {path}: {exc}"
        raise file_error(msg) from exc
