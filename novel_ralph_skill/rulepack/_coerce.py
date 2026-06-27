"""Bind the shared ``loaderkit`` coercion primitives to the rule pack's channel.

Roadmap task 7.2.2 consolidated the formerly cloned scalar-coercion bodies into
:mod:`novel_ralph_skill.loaderkit.coerce`. This module is now a thin **binding**
rather than a self-contained leaf: it builds the rule pack's one
:class:`~novel_ralph_skill.loaderkit.coerce.CoercionErrors` bundle — raising
:class:`RulePackError` with the ``"rule"``/``"rule pack"`` nouns — and re-exports
the underscore-named wrappers ``parse.py`` imports, each a one-line forwarder to
the shared body with the bundle bound.

Keeping the wrappers' ``rule_id=`` keyword means no call site in ``parse.py``
changes; the shared body lives in one place while the per-package seam is a single
bundle. A third pack family adds another bundle here, not a third copy of the
helpers.
"""

from __future__ import annotations

from novel_ralph_skill.loaderkit.coerce import (
    CoercionErrors,
    Mapping,
    reject_unknown_keys,
    require_int,
    require_str,
    where,
)
from novel_ralph_skill.rulepack.errors import RulePackError

# The rule pack's binding of the shared coercion seam: a per-rule fault names the
# rule, a pack-level fault names the pack level, and every helper raises
# ``RulePackError`` carrying the offending ``rule_id``.
_ERRORS = CoercionErrors(
    content_error=lambda msg, rule_id: RulePackError(msg, rule_id=rule_id),
    per_id_noun="rule",
    per_level_noun="rule pack",
)

# The shared ``Mapping`` alias, re-exported under the name ``parse.py`` imports.
type _Mapping = Mapping


def _where(rule_id: str | None) -> str:
    """Return the rule-pack message prefix for ``rule_id`` (see :func:`where`)."""
    return where(_ERRORS, rule_id)


def _reject_unknown_keys(
    mapping: _Mapping, allowed: frozenset[str], *, rule_id: str | None
) -> None:
    """Reject any key outside ``allowed`` (see :func:`reject_unknown_keys`)."""
    reject_unknown_keys(mapping, allowed, errors=_ERRORS, offending_id=rule_id)


def _require_str(mapping: _Mapping, key: str, *, rule_id: str | None) -> str:
    """Return ``mapping[key]`` as a ``str`` (see :func:`require_str`)."""
    return require_str(mapping, key, errors=_ERRORS, offending_id=rule_id)


def _require_int(mapping: _Mapping, key: str, *, rule_id: str | None) -> int:
    """Return ``mapping[key]`` as an ``int`` (see :func:`require_int`)."""
    return require_int(mapping, key, errors=_ERRORS, offending_id=rule_id)
