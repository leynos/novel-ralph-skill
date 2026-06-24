"""Packaged rule packs shipped inside the wheel (roadmap task 5.1.2).

This empty package marker makes
``importlib.resources.files("novel_ralph_skill.rulepack.packs")`` resolve at
runtime, so the shipped ``offenders.toml`` — the §6 high-frequency-offender table
(design §4.4, §6.1) — travels in the built wheel and the installed ``desloppify``
console-script can read it. hatchling includes the non-``.py`` ``offenders.toml``
under this already-shipped package directory by default
(``pyproject`` ``packages = ["novel_ralph_skill"]``), so no build-config change is
needed (ExecPlan Decision Log "the §6 offender pack ships at …packs/offenders.toml").
"""

from __future__ import annotations
