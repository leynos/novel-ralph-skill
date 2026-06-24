"""Validate the shipped ai-isms rule pack (roadmap task 7.1.1).

These pin ``novel_ralph_skill/rulepack/packs/ai-isms.toml`` — the opt-in AI-ism
tell pack (design §6.2). The suite proves the pack loads, that its rule-id set
*equals* the pinned five-id set (so a missing or extra row is red), that every
rule's ``(id, threshold, basis)`` triple matches the pack, that the ai-isms ids
are *disjoint* from the offenders ids (so the two packs never double-count), and
that each pattern matches a crafted positive while rejecting at least two crafted
negatives — one the deliberate out-of-scope negative the narrowing implies, and
one a sentence of ordinary fiction using the rule's surface tokens in a non-AI
way, so the rule is shown not to fire on baseline English (not merely on a
self-selected straw negative).

The suite also pins the deliberate casing divergence (ExecPlan Decision Log):
every pattern compiles under ``re.compile`` with no flags — inline ``(?i)`` only,
never a compile flag — and the cross-pack ownership cases assert that
``a-testament-to`` owns "is a testament to" while ``stands-as-a-testament`` owns
the "stands/serves as a testament" template, with neither firing on the other's
surface form.
"""

from __future__ import annotations

import re
import typing as typ

import pytest

from novel_ralph_skill.commands._desloppify_report import (
    ai_isms_pack_path,
    offenders_pack_path,
)
from novel_ralph_skill.rulepack import RuleBasis, load_rulepack

if typ.TYPE_CHECKING:
    from novel_ralph_skill.rulepack import Rule


# The canonical five-row ai-isms id set. A missing or extra row fails the
# equality assertion below (Risk row "duplicates an offenders row" / membership).
_EXPECTED_IDS: frozenset[str] = frozenset({
    "load-bearing",
    "a-testament-to",
    "stands-as-a-testament",
    "rich-tapestry",
    "vital-role",
})

# (id, threshold, basis) transcribed verbatim from the pack, so a future edit
# that drifts a threshold or basis is caught here.
_EXPECTED_TRIPLES: tuple[tuple[str, int, RuleBasis], ...] = (
    ("load-bearing", 0, RuleBasis.MANUSCRIPT),
    ("a-testament-to", 0, RuleBasis.MANUSCRIPT),
    ("stands-as-a-testament", 0, RuleBasis.MANUSCRIPT),
    ("rich-tapestry", 0, RuleBasis.MANUSCRIPT),
    ("vital-role", 0, RuleBasis.MANUSCRIPT),
)

# One crafted positive (>= 1 match) and two crafted negatives (0 matches) per
# rule: (a) the deliberate out-of-scope negative the narrowing implies, and (b)
# a sentence of ordinary fiction using the rule's surface tokens in a non-AI way.
_PATTERN_CASES: dict[str, tuple[str, tuple[str, ...]]] = {
    "load-bearing": (
        "this assumption is load-bearing",
        (
            # (a) the bare noun "bearing", not the compound tell.
            "the ball bearing spun loose",
            # (b) ordinary fiction using "load" and "bearing" apart.
            "she steadied the load, bearing its weight without complaint",
        ),
    ),
    "a-testament-to": (
        "the scar is a testament to that night",
        (
            # (a) "stands as a testament" with no "to" — owned by
            # stands-as-a-testament; a-testament-to must miss it.
            "the bridge stands as a testament, weathered and proud",
            # (b) "testament" as the legal/literal noun in fiction.
            "the lawyer read out his last will and testament",
        ),
    ),
    "stands-as-a-testament": (
        "the bridge stands as a testament to the city",
        (
            # (a) the live "is a testament to" — owned by a-testament-to.
            "this is a testament to her skill",
            # (b) "stands" and "testament" in ordinary fiction, not the template.
            "he stands by the window, his last testament unsigned",
        ),
    ),
    "rich-tapestry": (
        "a rich tapestry of myth and memory",
        (
            # (a) the bare "tapestry of" — owned by offenders.toml tapestry-of.
            "a tapestry of light fell across the floor",
            # (b) "rich" and "tapestry" apart in ordinary fiction.
            "the rich merchant hung a tapestry on the wall",
        ),
    ),
    "vital-role": (
        "she plays a vital role in the rebellion",
        (
            # (a) "role" without the verb+adjective collocation.
            "a crucial decision, but no role to play",
            # (b) ordinary fiction: an actor rehearsing a part.
            "she rehearsed her role until the small hours",
        ),
    ),
}


def _ai_isms_rules_by_id() -> dict[str, Rule]:
    """Return the loaded ai-isms rules keyed by id."""
    pack = load_rulepack(ai_isms_pack_path())
    return {rule.id: rule for rule in pack.rules}


def _offenders_ids() -> frozenset[str]:
    """Return the offenders pack's rule-id set."""
    pack = load_rulepack(offenders_pack_path())
    return frozenset(rule.id for rule in pack.rules)


def test_ai_isms_pack_loads() -> None:
    """The shipped pack loads with name ``ai-isms`` and schema version ``1``."""
    pack = load_rulepack(ai_isms_pack_path())
    assert pack.pack == "ai-isms", f"unexpected pack name {pack.pack!r}"
    assert pack.schema_version == 1, f"unexpected schema version {pack.schema_version}"


def test_ai_isms_rule_id_set_equals_expected() -> None:
    """The loaded rule-id set equals the pinned five-id set, with no duplicates.

    The row-count assertion guards against a duplicated ``[[rule]]`` id, which the
    set-equality check alone would silently collapse (CodeRabbit WI2 finding).
    """
    rules = load_rulepack(ai_isms_pack_path()).rules
    row_ids = [rule.id for rule in rules]
    assert len(row_ids) == len(_EXPECTED_IDS), (
        f"expected {len(_EXPECTED_IDS)} rows, found {len(row_ids)}: {row_ids}"
    )
    ids = frozenset(row_ids)
    assert ids == _EXPECTED_IDS, (
        f"missing {_EXPECTED_IDS - ids} / extra {ids - _EXPECTED_IDS}"
    )


def test_ai_isms_ids_disjoint_from_offenders() -> None:
    """The ai-isms ids are disjoint from the offenders ids (no double-counting)."""
    ai_isms = frozenset(_ai_isms_rules_by_id())
    overlap = ai_isms & _offenders_ids()
    assert not overlap, f"ai-isms and offenders share ids {overlap}"


@pytest.mark.parametrize(
    ("rule_id", "threshold", "basis"),
    _EXPECTED_TRIPLES,
    ids=[triple[0] for triple in _EXPECTED_TRIPLES],
)
def test_ai_isms_threshold_and_basis(
    rule_id: str, threshold: int, basis: RuleBasis
) -> None:
    """Each rule's threshold and basis match the pack verbatim."""
    rule = _ai_isms_rules_by_id()[rule_id]
    assert rule.threshold == threshold, (
        f"{rule_id} threshold {rule.threshold} != {threshold}"
    )
    assert rule.basis is basis, f"{rule_id} basis {rule.basis} != {basis}"


def test_ai_isms_all_manuscript_basis_no_page_words() -> None:
    """Every ai-isms rule is ``manuscript`` basis and carries no ``page_words``."""
    for rule in _ai_isms_rules_by_id().values():
        assert rule.basis is RuleBasis.MANUSCRIPT, (
            f"{rule.id} basis {rule.basis} is not manuscript"
        )
        assert rule.page_words is None, (
            f"{rule.id} manuscript rule carries page_words {rule.page_words}"
        )


@pytest.mark.parametrize(
    ("rule_id", "positive"),
    [(rule_id, cases[0]) for rule_id, cases in _PATTERN_CASES.items()],
    ids=list(_PATTERN_CASES),
)
def test_ai_isms_pattern_positive(rule_id: str, positive: str) -> None:
    """Each rule matches its crafted positive."""
    compiled = _ai_isms_rules_by_id()[rule_id].compiled
    assert compiled.search(positive), f"{rule_id} missed positive {positive!r}"


@pytest.mark.parametrize(
    ("rule_id", "negative"),
    [
        (rule_id, negative)
        for rule_id, cases in _PATTERN_CASES.items()
        for negative in cases[1]
    ],
    ids=[
        f"{rule_id}-neg{index}"
        for rule_id, cases in _PATTERN_CASES.items()
        for index in range(len(cases[1]))
    ],
)
def test_ai_isms_pattern_negative(rule_id: str, negative: str) -> None:
    """Each rule rejects both its crafted negatives, including ordinary fiction."""
    compiled = _ai_isms_rules_by_id()[rule_id].compiled
    assert not compiled.search(negative), (
        f"{rule_id} wrongly matched negative {negative!r}"
    )


def test_a_testament_to_owns_the_is_a_testament_to_phrase() -> None:
    """``a-testament-to`` fires on "is a testament to …" (the live phrase it owns)."""
    compiled = _ai_isms_rules_by_id()["a-testament-to"].compiled
    assert compiled.search("this is a testament to her skill"), (
        "a-testament-to must own the live 'is a testament to' phrase"
    )


def test_a_testament_to_misses_bare_stands_as_a_testament() -> None:
    """``a-testament-to`` does not fire on "stands as a testament" without a "to"."""
    compiled = _ai_isms_rules_by_id()["a-testament-to"].compiled
    assert not compiled.search("the bridge stands as a testament"), (
        "a-testament-to must not fire on the 'stands as a testament' template"
    )


def test_rich_tapestry_disjoint_from_tapestry_of() -> None:
    """``rich-tapestry`` misses the bare "tapestry of" offenders.toml owns."""
    compiled = _ai_isms_rules_by_id()["rich-tapestry"].compiled
    assert not compiled.search("a tapestry of light fell across the floor"), (
        "rich-tapestry must not fire on the bare 'tapestry of' (offenders owns it)"
    )


def test_ai_isms_patterns_compile_without_flags() -> None:
    """Every pattern compiles under ``re.compile`` with no flags (loader parity).

    This pins the deliberate casing divergence (ExecPlan Decision Log): the
    divergence is the inline ``(?i)`` carried in each pattern source, never a
    compile flag. Recompiling here proves the literal strings reach ``re`` intact.
    """
    for rule in _ai_isms_rules_by_id().values():
        compiled = re.compile(rule.pattern)
        assert compiled.flags & re.IGNORECASE, (
            f"{rule.id} must carry inline (?i), found flags {compiled.flags}"
        )
