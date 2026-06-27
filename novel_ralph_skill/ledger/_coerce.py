"""Bind the shared ``loaderkit`` coercion primitives to the ledger's channel.

Roadmap task 7.2.2 consolidated the scalar-coercion bodies into
:mod:`novel_ralph_skill.loaderkit.coerce`; roadmap task 7.2.7 then collapses the
per-family forwarder shims onto the shared
:func:`~novel_ralph_skill.loaderkit.coerce.bind_coercion` factory. This module is
now a single binding: one :func:`bind_coercion` call builds the ledger's
:class:`~novel_ralph_skill.loaderkit.coerce.BoundCoercion` bundle — raising
:class:`LedgerError` with the ``"device"``/``"device ledger"`` nouns — and exposes
every coercion helper (including ``require``, which ``_fields.py`` uses) with that
bundle bound. ``parse.py`` and ``_fields.py`` call those helpers as
``_COERCION.where(...)``/``_COERCION.require(...)`` rather than importing a
per-family forwarder per helper, so the former bare-``_require`` divergence
between this shim and the rule pack's disappears: the bundle carries the whole
uniform surface for every family.

The ledger's *public* error keyword (``device_id=``) is bound inside the
``content_error`` callable, exactly where it was, so the error contract is
unchanged. The ``_ERRORS`` alias exposes the raw bundle the schema-version,
entry-array, and pattern-compile primitives bind to directly, and ``_Mapping`` is
re-exported under the name the package imports. A third pack family adds one more
``bind_coercion`` call, not a third copy of the helpers.
"""

from __future__ import annotations

from novel_ralph_skill.ledger.errors import LedgerError
from novel_ralph_skill.loaderkit.coerce import Mapping, bind_coercion

# The ledger's binding of the shared coercion seam: a per-device fault names the
# device, a ledger-level fault names the ledger level, and every helper raises
# ``LedgerError`` carrying the offending ``device_id`` (bound inside
# ``content_error`` so the public keyword never leaks onto the bound helpers).
_COERCION = bind_coercion(
    content_error=lambda msg, device_id: LedgerError(msg, device_id=device_id),
    per_id_noun="device",
    per_level_noun="device ledger",
)
# The raw ``CoercionErrors`` the schema-version, entry-array, and pattern-compile
# primitives bind to directly, aliased under the name the package imports.
_ERRORS = _COERCION.errors

# The shared ``Mapping`` alias, re-exported under the name the package imports.
type _Mapping = Mapping
