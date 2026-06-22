"""Read-only normalisers for frozen-dataclass mapping and sequence fields.

A ``frozen=True`` dataclass freezes the field *binding*, but a
``collections.abc.Mapping`` or ``collections.abc.Sequence`` field still aliases
whatever container the caller passed, so a plain ``dict`` or ``list`` stays
mutable through that reference and the documented immutability guarantee leaks.

Call these from ``__post_init__`` (via ``object.__setattr__``, because the
dataclass is frozen) to copy and wrap such a field once, at construction, so the
guarantee holds for every construction path rather than only the parse boundary.
The wrapped containers are immutable and therefore unhashable — the intended
house style (see :mod:`novel_ralph_skill.contract.envelope`): these objects are
values to read, never dict keys or set members. A serialisation boundary that
needs a plain container copies it back out (``dict(...)`` / ``list(...)``), as
:func:`novel_ralph_skill.contract.envelope.render_machine` does.
"""

from __future__ import annotations

import types
import typing as typ

if typ.TYPE_CHECKING:
    import collections.abc as cabc


def freeze_mapping[K, V](mapping: cabc.Mapping[K, V]) -> cabc.Mapping[K, V]:
    """Return an immutable, copied view of ``mapping`` as a ``MappingProxyType``."""
    return types.MappingProxyType(dict(mapping))


def freeze_sequence[T](sequence: cabc.Sequence[T]) -> tuple[T, ...]:
    """Return an immutable, copied ``tuple`` of ``sequence``."""
    return tuple(sequence)
