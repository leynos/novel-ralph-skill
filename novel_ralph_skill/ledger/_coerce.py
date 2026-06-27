"""Bind the shared ``loaderkit`` coercion primitives to the ledger's channel.

Roadmap task 7.2.2 consolidated the scalar-coercion bodies into
:mod:`novel_ralph_skill.loaderkit.coerce`, performing the error-factory refactor
this module's earlier docstring foresaw and deferred. That earlier ExecPlan
Tolerance protected the *frozen* rule-pack loader during the ledger's own build,
so the ledger then carried a deliberate near-copy; 7.2.2 is the sanctioned
consolidation pass that owns the change, so the near-copy is retired and this
module is now a thin **binding** rather than a self-contained leaf.

It builds the ledger's one
:class:`~novel_ralph_skill.loaderkit.coerce.CoercionErrors` bundle — raising
:class:`LedgerError` with the ``"device"``/``"device ledger"`` nouns — and
re-exports the underscore-named wrappers ``parse.py`` and ``_fields.py`` import,
each a one-line forwarder to the shared body with the bundle bound. Keeping the
wrappers' ``device_id=`` keyword means no call site changes; a third pack family
adds another bundle here, not a third copy of the helpers.
"""

from __future__ import annotations

from novel_ralph_skill.ledger.errors import LedgerError
from novel_ralph_skill.loaderkit.coerce import (
    CoercionErrors,
    Mapping,
    reject_unknown_keys,
    require,
    require_int,
    require_str,
    where,
)

# The ledger's binding of the shared coercion seam: a per-device fault names the
# device, a ledger-level fault names the ledger level, and every helper raises
# ``LedgerError`` carrying the offending ``device_id``.
_ERRORS = CoercionErrors(
    content_error=lambda msg, device_id: LedgerError(msg, device_id=device_id),
    per_id_noun="device",
    per_level_noun="device ledger",
)

# The shared ``Mapping`` alias, re-exported under the name the package imports.
type _Mapping = Mapping


def _where(device_id: str | None) -> str:
    """Return the ledger message prefix for ``device_id`` (see :func:`where`)."""
    return where(_ERRORS, device_id)


def _reject_unknown_keys(
    mapping: _Mapping, allowed: frozenset[str], *, device_id: str | None
) -> None:
    """Reject any key outside ``allowed`` (see :func:`reject_unknown_keys`)."""
    reject_unknown_keys(mapping, allowed, errors=_ERRORS, offending_id=device_id)


def _require(mapping: _Mapping, key: str, *, device_id: str | None) -> object:
    """Return ``mapping[key]`` or raise naming the gap (see :func:`require`)."""
    return require(mapping, key, errors=_ERRORS, offending_id=device_id)


def _require_str(mapping: _Mapping, key: str, *, device_id: str | None) -> str:
    """Return ``mapping[key]`` as a ``str`` (see :func:`require_str`)."""
    return require_str(mapping, key, errors=_ERRORS, offending_id=device_id)


def _require_int(mapping: _Mapping, key: str, *, device_id: str | None) -> int:
    """Return ``mapping[key]`` as an ``int`` (see :func:`require_int`)."""
    return require_int(mapping, key, errors=_ERRORS, offending_id=device_id)
