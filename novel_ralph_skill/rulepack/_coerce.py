"""Bind the shared ``loaderkit`` coercion primitives to the rule pack's channel.

Roadmap task 7.2.2 consolidated the formerly cloned scalar-coercion bodies into
:mod:`novel_ralph_skill.loaderkit.coerce`; roadmap task 7.2.7 then collapses the
per-family forwarder shims onto the shared
:func:`~novel_ralph_skill.loaderkit.coerce.bind_coercion` factory. This module is
now a single binding: one :func:`bind_coercion` call builds the rule pack's
:class:`~novel_ralph_skill.loaderkit.coerce.BoundCoercion` bundle — raising
:class:`RulePackError` with the ``"rule"``/``"rule pack"`` nouns — and exposes
every coercion helper with that bundle bound. ``parse.py`` calls those helpers as
``_COERCION.where(...)``/``_COERCION.require_str(...)`` rather than importing a
per-family forwarder per helper.

The rule pack's *public* error keyword (``rule_id=``) is bound inside the
``content_error`` callable, exactly where it was, so the error contract is
unchanged. The ``_ERRORS`` alias exposes the raw bundle the schema-version,
entry-array, and pattern-compile primitives bind to directly, and ``_Mapping`` is
re-exported under the name ``parse.py`` imports. A third pack family adds one more
``bind_coercion`` call, not a third copy of the helpers.
"""

from __future__ import annotations

from novel_ralph_skill.loaderkit.coerce import Mapping, bind_coercion
from novel_ralph_skill.rulepack.errors import RulePackError

# The rule pack's binding of the shared coercion seam: a per-rule fault names the
# rule, a pack-level fault names the pack level, and every helper raises
# ``RulePackError`` carrying the offending ``rule_id`` (bound inside
# ``content_error`` so the public keyword never leaks onto the bound helpers).
_COERCION = bind_coercion(
    content_error=lambda msg, rule_id: RulePackError(msg, rule_id=rule_id),
    per_id_noun="rule",
    per_level_noun="rule pack",
)
# The raw ``CoercionErrors`` the schema-version, entry-array, and pattern-compile
# primitives bind to directly, aliased under the name ``parse.py`` imports.
_ERRORS = _COERCION.errors

# The shared ``Mapping`` alias, re-exported under the name ``parse.py`` imports.
type _Mapping = Mapping
