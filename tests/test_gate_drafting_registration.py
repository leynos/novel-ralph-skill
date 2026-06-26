"""Registration of the gate/drafting subcommands on ``novel-state`` (roadmap 2.2.4).

Proves the four subcommands — ``set-gate``, ``complete-final-pass``,
``set-fangirl``, ``set-critic-pass`` — are wired onto the ``novel-state`` app by
:func:`novel_ralph_skill.commands._gate_drafting_mutators.register_gate_drafting_commands`,
which :func:`novel_ralph_skill.commands.novel_state.build_app` invokes (Decision
D11/B4 — the registrar lives off ``novel_state.py`` so the file stays under the
400-line cap). The registrar is independently testable: it registers onto any
:class:`cyclopts.App` regardless of the defining module, so a fresh
``make_contract_app("novel-state")`` gains all four. The ``--pass`` flag for
``set-critic-pass`` binds the body's ``pass_number`` parameter (A2 — one name end
to end via :class:`cyclopts.Parameter`).
"""

from __future__ import annotations

from novel_ralph_skill.commands._gate_drafting_mutators import (
    register_gate_drafting_commands,
)
from novel_ralph_skill.commands.novel_state import build_app
from novel_ralph_skill.contract.runner import make_contract_app

_EXPECTED = ("set-gate", "complete-final-pass", "set-fangirl", "set-critic-pass")


def test_build_app_exposes_the_four_subcommands() -> None:
    """``build_app`` registers all four gate/drafting subcommands."""
    commands = set(build_app())
    for name in _EXPECTED:
        assert name in commands, f"{name} must be registered on the novel-state app"


def test_registrar_registers_onto_a_fresh_app() -> None:
    """``register_gate_drafting_commands`` wires the four onto any app it is given."""
    app = make_contract_app("novel-state")
    register_gate_drafting_commands(app)
    commands = set(app)
    for name in _EXPECTED:
        assert name in commands, f"the registrar must add {name} to the passed-in app"


def test_set_critic_pass_binds_pass_flag_to_pass_number() -> None:
    """``--pass 2`` binds the body's ``pass_number`` parameter (one name end to end)."""
    app = build_app()
    _command, bound, _ignored = app.parse_args(
        ["set-critic-pass", "--pass", "2"], exit_on_error=False
    )
    assert bound.kwargs.get("pass_number") == 2, (
        "the --pass flag must bind the pass_number parameter to 2"
    )
