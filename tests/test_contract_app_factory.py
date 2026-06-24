"""Unit tests for the shared four-flag contract-app factory.

These tests pin :func:`novel_ralph_skill.contract.runner.make_contract_app`: the
single home for the four-flag :func:`~novel_ralph_skill.contract.runner.run`
contract (``result_action="return_value", exit_on_error=False,
print_error=False, help_on_error=False``). The behavioural consequences of those
flags are pinned separately by ``tests/test_cyclopts_contract.py`` (the version
tripwire) and ``tests/test_contract_runner.py`` (the exit-code translation); this
module pins only that the factory carries the four required values and the
supplied name, in their cyclopts 4.18.0 normalised forms.
"""

from __future__ import annotations

import cyclopts
import pytest

from novel_ralph_skill.contract import make_contract_app as make_contract_app_pkg
from novel_ralph_skill.contract.runner import make_contract_app


@pytest.fixture
def contract_app() -> cyclopts.App:
    """Return the ``novel-state`` app the factory builds for assertions."""
    return make_contract_app("novel-state")


def test_make_contract_app_returns_cyclopts_app(contract_app: cyclopts.App) -> None:
    """The factory returns a :class:`cyclopts.App` instance."""
    assert isinstance(contract_app, cyclopts.App)


def test_make_contract_app_carries_the_normalised_name(
    contract_app: cyclopts.App,
) -> None:
    """Cyclopts 4.18.0 tuple-wraps the ``name`` argument on construction."""
    assert contract_app.name == ("novel-state",)


def test_make_contract_app_returns_the_body_value(contract_app: cyclopts.App) -> None:
    """``result_action`` is the tuple-wrapped ``return_value`` cyclopts stores."""
    assert contract_app.result_action == ("return_value",)


@pytest.mark.parametrize("flag", ["exit_on_error", "print_error", "help_on_error"])
def test_make_contract_app_keeps_boolean_flags_false(
    contract_app: cyclopts.App, flag: str
) -> None:
    """The three boolean flags stay plain ``False`` (no cyclopts normalisation).

    ``exit_on_error=False`` makes a usage fault raise rather than exit ``1``;
    ``print_error=False`` and ``help_on_error=False`` suppress the Rich panel so
    the :func:`~novel_ralph_skill.contract.runner.run` wrapper owns the
    diagnostic channel.
    """
    assert getattr(contract_app, flag) is False


def test_make_contract_app_is_re_exported_from_the_package() -> None:
    """The factory is importable from the ``contract`` package, not only ``runner``."""
    assert make_contract_app_pkg is make_contract_app
