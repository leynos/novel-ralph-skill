"""Import-contract smoke test for the ``reconcile`` mutator (roadmap 2.3.2).

This was Work item 0's red-baseline marker: it imports the ``reconcile`` mutator
body and asserts it is callable. Work item 4 lands the body, so the marker is now
a plain green smoke test — the import spine the behavioural suites build on. The
import goes through :func:`importlib.import_module` so the contract is a runtime
one (the static type-checker is exercised by the behavioural suites that import
the body directly).
"""

from __future__ import annotations

import importlib


def test_reconcile_body_is_importable_and_callable() -> None:
    """The ``reconcile`` mutator body imports and is a callable."""
    module = importlib.import_module("novel_ralph_skill.commands._reconcile")
    assert callable(module.reconcile), "reconcile must be a callable"
