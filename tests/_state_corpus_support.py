"""Shared helpers for the §5.2 validator corpus-agreement suites.

Both :mod:`tests.test_validate_state_corpus` and
:mod:`tests.test_validate_state_live_draft` drive the production parser and the
§5.2 validator over the §1.3.2 corpus trees. They share the parse-fault
vocabulary, the parse-enforced invariant set, and the two thin wrappers that turn
a materialised ``working/`` tree into a validator verdict (or report that the
parser rejected it first). Lifting them here keeps each test module within the
400-line cap and pins the parse handling to one home so the two suites cannot
drift (the sibling-module split the ExecPlan's Risks section prescribes).
"""

from __future__ import annotations

import typing as typ

from novel_ralph_skill.state import (
    PHASE_IN_ENUM,
    load_state,
    validate_state,
)

if typ.TYPE_CHECKING:
    from pathlib import Path

# The ``phase-in-enum`` invariant is enforced one layer earlier than the
# validator: ``parse_state`` constructs ``Phase(current)`` and raises
# ``ValueError`` on an out-of-enum phase, so a parsed ``State`` can never carry a
# ``phase-in-enum`` violation. The corpus's ``phase-not-in-enum`` variant
# therefore makes ``load_state`` raise (the exit-``3`` state-error channel in
# production) rather than yielding a validator verdict. The agreement suites
# treat such a tree as a parse rejection, asserting the parser enforces the
# invariant the oracle labels.
PARSE_ENFORCED_INVARIANTS: frozenset[str] = frozenset({PHASE_IN_ENUM})

# The exceptions ``parse_state``/``load_state`` raise on a structurally bad or
# out-of-enum ``state.toml`` (the production exit-``3`` channel). This is the
# parse-fault subset of the production ``STATE_INPUT_ERRORS`` vocabulary (the
# corpus trees always exist on disk, so ``OSError`` is not exercised here);
# ``test_parse_errors_subset_of_production_state_input_errors`` pins the subset
# relationship so the two cannot drift (audit:2.1.2 finding 4).
PARSE_ERRORS: tuple[type[Exception], ...] = (ValueError, KeyError, TypeError)


def validator_verdict(working_dir: Path) -> set[str]:
    """Return the set of invariant names the validator reports for a tree."""
    state = load_state(working_dir / "state.toml")
    return {violation.invariant for violation in validate_state(state)}


def load_succeeds(working_dir: Path) -> bool:
    """Return whether ``load_state`` parses the tree's ``state.toml`` (no raise).

    A ``False`` result means the parser rejected the tree (the production exit-``3``
    state-error channel) before the validator could run — the parse-enforced
    ``phase-in-enum`` case.
    """
    try:
        load_state(working_dir / "state.toml")
    except PARSE_ERRORS:
        return False
    return True
