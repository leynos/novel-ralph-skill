"""Per-family wiring pins for the collapsed ``_coerce.py`` bindings (roadmap 7.2.7).

Roadmap task 7.2.7 collapses the two per-family ``_coerce.py`` forwarder shims
onto the shared
:func:`~novel_ralph_skill.loaderkit.coerce.bind_coercion` factory, repointing
every ``_where``/``_require*``/``_reject_unknown_keys`` call site at the
:class:`~novel_ralph_skill.loaderkit.coerce.BoundCoercion` bundle. The bundle
exposes only the private ``offending_id``; each family's *public* error keyword
(``rule_id=``/``device_id=``) is bound inside the ``content_error`` callable the
shim supplies.

These tests drive the repointed sites directly through the real loaders and
assert the raised error is the family's own typed channel carrying its own
populated id. They are the backstop for the round-1 transposition hazard: had a
repoint passed ``offending_id`` positionally or dropped the keyword bind, the id
would surface wrong (or the call would raise ``TypeError``) here, before the
snapshot pins even run. The ``allowed_chapters`` element fault in particular
exercises the ``_fields.py`` ``_COERCION.require``/``_COERCION.where`` sites that
the existing fixture suites do not negatively pin.
"""

from __future__ import annotations

import pytest

from novel_ralph_skill.ledger.errors import LedgerError
from novel_ralph_skill.ledger.parse import parse_ledger
from novel_ralph_skill.rulepack.errors import RulePackError
from novel_ralph_skill.rulepack.parse import parse_rulepack


def test_rulepack_bad_basis_names_rule_via_bound_where() -> None:
    """An unknown ``basis`` raises ``RulePackError`` naming the rule.

    Exercises the repointed ``_COERCION.where`` site in ``_resolve_basis`` and
    proves the public ``rule_id`` survives the bind.
    """
    raw = {
        "schema_version": 1,
        "pack": "demo",
        "rule": [{"id": "alpha", "pattern": "x", "threshold": 1, "basis": "bogus"}],
    }
    with pytest.raises(RulePackError, match=r"rule 'alpha'") as excinfo:
        parse_rulepack(raw)
    assert excinfo.value.rule_id == "alpha"


def test_ledger_bad_allowed_chapters_element_names_device() -> None:
    """A non-integer ``allowed_chapters`` element raises ``LedgerError`` naming it.

    Exercises the repointed ``_COERCION.require``/``_COERCION.where`` sites in
    ``ledger/_fields.py``'s ``_allowed_chapters`` and proves the public
    ``device_id`` survives the bind.
    """
    raw = {
        "schema_version": 1,
        "device": [
            {"id": "sternum", "pattern": "x", "allowed_chapters": [1, "two", 3]}
        ],
    }
    with pytest.raises(LedgerError, match=r"device 'sternum'") as excinfo:
        parse_ledger(raw)
    assert excinfo.value.device_id == "sternum"
