"""Validate the shipped §6 offender rule pack (roadmap task 5.1.2).

These pin ``novel_ralph_skill/rulepack/packs/offenders.toml`` — the §6
high-frequency-offender table transcribed one ``[[rule]]`` per row (design §4.4,
§6.1). The suite proves the pack loads, that its rule-id set *equals* the pinned
24-id set (so a missing or extra row is red — defect 1), that every rule's
``threshold`` and ``basis`` match the §6 table, that exactly one rule is
``per_page``, and that each rule's pattern matches a crafted positive and rejects
a crafted negative. The placeholder rows pinned in the ExecPlan Decision Log get
explicit out-of-scope negatives: ``verb-ed-adverb`` rejects the §4 "said sadly"
tell, ``couldnt-help-but`` rejects the expanded "could not help but" hedge, and
``found-herself`` rejects the bare reflexive and a line-wrapped continuation.
"""

from __future__ import annotations

import re
import typing as typ

import pytest

from novel_ralph_skill.commands._desloppify_report import offenders_pack_path
from novel_ralph_skill.rulepack import RuleBasis, load_rulepack

if typ.TYPE_CHECKING:
    from novel_ralph_skill.rulepack import Rule


# The canonical 24-row §6 offender id set. A missing or extra row fails the
# equality assertion below (ExecPlan defect 1 / Risk row 1).
_EXPECTED_IDS: frozenset[str] = frozenset({
    "it-s-not-just",
    "let-out-a-breath",
    "shivers-down-spine",
    "air-thick-with",
    "found-herself",
    "couldnt-help-but",
    "em-dash",
    "but-that-was-just-the-beginning",
    "and-in-that-moment",
    "some-things",
    "a-part-of-her",
    "capitalised-abstract-noun",
    "smirked",
    "verb-ed-adverb",
    "the-silence-stretched",
    "her-heart-skipped",
    "every-fibre-of-her-being",
    "in-a-world-where",
    "tapestry-of",
    "symphony-of",
    "a-delicate-balance",
    "navigate-the-complexities",
    "speaks-volumes",
    "paradigm-shift",
})

# (id, threshold, basis) transcribed verbatim from the §6 table, so a future
# table edit that drifts a threshold or basis is caught here.
_EXPECTED_TRIPLES: tuple[tuple[str, int, RuleBasis], ...] = (
    ("it-s-not-just", 0, RuleBasis.MANUSCRIPT),
    ("let-out-a-breath", 0, RuleBasis.MANUSCRIPT),
    ("shivers-down-spine", 0, RuleBasis.MANUSCRIPT),
    ("air-thick-with", 0, RuleBasis.MANUSCRIPT),
    ("found-herself", 2, RuleBasis.MANUSCRIPT),
    ("couldnt-help-but", 1, RuleBasis.MANUSCRIPT),
    ("em-dash", 5, RuleBasis.PER_PAGE),
    ("but-that-was-just-the-beginning", 0, RuleBasis.MANUSCRIPT),
    ("and-in-that-moment", 0, RuleBasis.MANUSCRIPT),
    ("some-things", 0, RuleBasis.MANUSCRIPT),
    ("a-part-of-her", 1, RuleBasis.MANUSCRIPT),
    ("capitalised-abstract-noun", 1, RuleBasis.MANUSCRIPT),
    ("smirked", 1, RuleBasis.MANUSCRIPT),
    ("verb-ed-adverb", 2, RuleBasis.MANUSCRIPT),
    ("the-silence-stretched", 0, RuleBasis.MANUSCRIPT),
    ("her-heart-skipped", 0, RuleBasis.MANUSCRIPT),
    ("every-fibre-of-her-being", 0, RuleBasis.MANUSCRIPT),
    ("in-a-world-where", 0, RuleBasis.MANUSCRIPT),
    ("tapestry-of", 0, RuleBasis.MANUSCRIPT),
    ("symphony-of", 0, RuleBasis.MANUSCRIPT),
    ("a-delicate-balance", 0, RuleBasis.MANUSCRIPT),
    ("navigate-the-complexities", 0, RuleBasis.MANUSCRIPT),
    ("speaks-volumes", 0, RuleBasis.MANUSCRIPT),
    ("paradigm-shift", 0, RuleBasis.MANUSCRIPT),
)

# One crafted positive (>= 1 match) and one crafted negative (0 matches) per
# rule, including the Decision-Log out-of-scope cases. ``found-herself`` and
# ``couldnt-help-but`` carry their full positive/negative matrices below.
_PATTERN_CASES: dict[str, tuple[str, str]] = {
    "it-s-not-just": ("It's not just cold, it's freezing.", "It is plainly cold."),
    "let-out-a-breath": ("She let out a breath.", "She drew a deep breath."),
    "shivers-down-spine": (
        "a shiver down her spine",
        "shivers in the cold",
    ),
    "air-thick-with": ("the air was thick with smoke", "the room was bright"),
    "em-dash": ("a pause—then nothing", "a pause, then nothing"),
    "but-that-was-just-the-beginning": (
        "—but that was just the beginning.",
        "and that was the end.",
    ),
    "and-in-that-moment": ("And in that moment she knew.", "At that point she knew."),
    "some-things": ("Some things never change.", "He noticed some things were odd."),
    "a-part-of-her": ("A part of her wanted to scream.", "A part of the engine broke."),
    "capitalised-abstract-noun": (
        "a Tapestry of light",
        "a tapestry of light",
    ),
    "smirked": ("He smirked at her.", "He smiled at her."),
    "the-silence-stretched": ("the silence stretched on", "the music played on"),
    "her-heart-skipped": ("her heart skipped a beat", "her pulse stayed steady"),
    "every-fibre-of-her-being": (
        "with every fibre of her being",
        "with all of her strength",
    ),
    "in-a-world-where": ("In a world where dragons rule.", "On a day when it rained."),
    "tapestry-of": ("a tapestry of stories", "a basket of apples"),
    "symphony-of": ("a symphony of colour", "a chorus of voices"),
    "a-delicate-balance": ("a delicate balance of forces", "a sturdy table of oak"),
    "navigate-the-complexities": (
        "navigate the complexities of grief",
        "untangle the knot of string",
    ),
    "speaks-volumes": ("her silence speaks volumes", "her speech ran long"),
    "paradigm-shift": ("a paradigm shift in thought", "a gentle shift in tone"),
    # The §4 "said sadly" tell does not end in -ed, so the §6 row must miss it.
    "verb-ed-adverb": ("he smiled sadly", "she said sadly"),
}

_FOUND_HERSELF_POSITIVES: tuple[str, ...] = (
    "She found herself wondering why.",
    "found herself walking",
    "He found himself drawn to the light.",
)
_FOUND_HERSELF_NEGATIVES: tuple[str, ...] = (
    "She found herself.",
    "He found himself!",
    "and so she found herself, alone",
    "She found her keys.",
)
_COULDNT_HELP_BUT_POSITIVES: tuple[str, ...] = (
    "she couldn't help but smile",
    "she couldnt help but smile",
)
_COULDNT_HELP_BUT_NEGATIVE = "she could not help but smile"


def _rules_by_id() -> dict[str, Rule]:
    """Return the loaded offender rules keyed by id."""
    pack = load_rulepack(offenders_pack_path())
    return {rule.id: rule for rule in pack.rules}


def test_offenders_pack_loads() -> None:
    """The shipped pack loads with the expected name and schema version."""
    pack = load_rulepack(offenders_pack_path())
    assert pack.pack == "offenders", f"unexpected pack name {pack.pack!r}"
    assert pack.schema_version == 1, f"unexpected schema version {pack.schema_version}"


def test_offenders_rule_id_set_equals_expected() -> None:
    """The loaded rule-id set equals the pinned 24-id §6 set (defect 1)."""
    ids = frozenset(_rules_by_id())
    assert ids == _EXPECTED_IDS, (
        f"missing {_EXPECTED_IDS - ids} / extra {ids - _EXPECTED_IDS}"
    )


@pytest.mark.parametrize(
    ("rule_id", "threshold", "basis"),
    _EXPECTED_TRIPLES,
    ids=[triple[0] for triple in _EXPECTED_TRIPLES],
)
def test_offenders_threshold_and_basis(
    rule_id: str, threshold: int, basis: RuleBasis
) -> None:
    """Each rule's threshold and basis match the §6 table verbatim."""
    rule = _rules_by_id()[rule_id]
    assert rule.threshold == threshold, (
        f"{rule_id} threshold {rule.threshold} != {threshold}"
    )
    assert rule.basis is basis, f"{rule_id} basis {rule.basis} != {basis}"


def test_exactly_one_per_page_rule() -> None:
    """Only ``em-dash`` is ``per_page`` (``page_words == 300``); others are not."""
    rules = _rules_by_id()
    per_page = [rule for rule in rules.values() if rule.basis is RuleBasis.PER_PAGE]
    assert [rule.id for rule in per_page] == ["em-dash"], (
        f"unexpected per_page rules {[rule.id for rule in per_page]}"
    )
    assert rules["em-dash"].page_words == 300, (
        f"em-dash page_words {rules['em-dash'].page_words} != 300"
    )
    for rule in rules.values():
        if rule.basis is RuleBasis.MANUSCRIPT:
            assert rule.page_words is None, (
                f"{rule.id} manuscript rule carries page_words {rule.page_words}"
            )


@pytest.mark.parametrize(
    ("rule_id", "positive", "negative"),
    [(rule_id, *cases) for rule_id, cases in _PATTERN_CASES.items()],
    ids=list(_PATTERN_CASES),
)
def test_offenders_pattern_positive_negative(
    rule_id: str, positive: str, negative: str
) -> None:
    """Each rule matches its crafted positive and rejects its crafted negative."""
    compiled = _rules_by_id()[rule_id].compiled
    assert compiled.search(positive), f"{rule_id} missed positive {positive!r}"
    assert not compiled.search(negative), (
        f"{rule_id} wrongly matched negative {negative!r}"
    )


@pytest.mark.parametrize("text", _FOUND_HERSELF_POSITIVES)
def test_found_herself_matches_verb_continuation(text: str) -> None:
    """``found-herself`` matches the "+ verb" reading (round-3 defect)."""
    compiled = _rules_by_id()["found-herself"].compiled
    assert compiled.search(text), f"found-herself missed {text!r}"


@pytest.mark.parametrize("text", _FOUND_HERSELF_NEGATIVES)
def test_found_herself_rejects_bare_reflexive(text: str) -> None:
    """``found-herself`` rejects the bare reflexive and "found her" (round-3)."""
    compiled = _rules_by_id()["found-herself"].compiled
    assert not compiled.search(text), f"found-herself wrongly matched {text!r}"


def test_found_herself_line_wrap_undetected() -> None:
    """A reflexive whose verb begins the next physical line yields 0 hits (v1)."""
    compiled = _rules_by_id()["found-herself"].compiled
    # Fed as two physical lines, mirroring the line-by-line scan: the [^\S\n]
    # continuation cannot cross the break (documented single-line limitation).
    lines = "found herself\nwondering".splitlines()
    assert not any(compiled.search(line) for line in lines), (
        "found-herself must not span a hard line break in v1"
    )


@pytest.mark.parametrize("text", _COULDNT_HELP_BUT_POSITIVES)
def test_couldnt_help_but_matches_contraction(text: str) -> None:
    """``couldnt-help-but`` matches both contraction forms (round-4 defect)."""
    compiled = _rules_by_id()["couldnt-help-but"].compiled
    assert compiled.search(text), f"couldnt-help-but missed {text!r}"


def test_couldnt_help_but_rejects_expanded_hedge() -> None:
    """``couldnt-help-but`` rejects "could not help but" — out of scope (round-4)."""
    compiled = _rules_by_id()["couldnt-help-but"].compiled
    assert not compiled.search(_COULDNT_HELP_BUT_NEGATIVE), (
        "'could not help but' is deliberately out of scope for the §6 row"
    )


def test_offenders_patterns_compile_without_flags() -> None:
    """Every pattern compiles under ``re.compile`` with no flags (loader parity)."""
    for rule in _rules_by_id().values():
        # The loader compiles with no flags; recompiling here proves the literal
        # strings reach ``re`` intact (no TOML escape doubling surprise).
        assert re.compile(rule.pattern), f"{rule.id} pattern failed to compile"
