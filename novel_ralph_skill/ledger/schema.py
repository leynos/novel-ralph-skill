"""Frozen, typed dataclasses for a per-novel device ledger (design §6.3).

A *device ledger* is a per-novel TOML file that rations a novel's signature
devices — a recurring image, a key phrase, a bookend line — each of which is
meant to land a fixed number of times, in a fixed set of chapters, and nowhere
else (design §6.3). Each :class:`Device` names a regular-expression ``pattern``
and exactly one chapter-window constraint (or a bare ``max_count``), so the
deterministic enforcer ``desloppify --ledger`` (roadmap task 7.1.2) can report,
per device, whether the manuscript on disk has overspent its ration.

This module carries the *shapes* only: the per-device :class:`Device` and the
whole :class:`DeviceLedger`. It performs no parsing and no validation; the
validating boundary that builds these from a decoded TOML mapping lives in
:mod:`novel_ralph_skill.ledger.parse`, mirroring how
``novel_ralph_skill/rulepack/schema.py`` carries shapes while
``novel_ralph_skill/rulepack/parse.py`` constructs them.

The objects follow the frozen, slotted, keyword-only house style of
``novel_ralph_skill/rulepack/schema.py``. Unlike the rule-pack schema, a device
ledger carries no ``pack`` name (design §6.3's example has only
``schema_version`` and ``[[device]]`` tables), and a device's ration is
chapter-aware: the four rationing fields express *which* chapters a device may
be spent in, a vocabulary the closed v1 rule-pack schema cannot carry (ExecPlan
Decision Log "model the device ledger as a NEW package").
"""

from __future__ import annotations

import dataclasses
import typing as typ

if typ.TYPE_CHECKING:
    import re


LEDGER_SCHEMA_VERSION: int = 1
"""The current device-ledger schema version (design §6.3).

This version is independent of the envelope's, ``state.toml``'s, and the rule
pack's ``schema_version`` numbers (design §3.1, §6.1): a device ledger carries
its own version, so the device vocabulary can evolve without forcing an
envelope, state, or rule-pack bump. The loader validates this value rather than
silently coercing it.
"""


@dataclasses.dataclass(frozen=True, kw_only=True, slots=True)
class Device:
    """One rationed narrative device of a device ledger (design §6.3).

    A device carries exactly one chapter-window constraint among
    :attr:`allowed_chapters`, :attr:`retired_after_chapter`, and
    :attr:`reserved_for_chapter`, with :attr:`max_count` optionally pairing with
    one of them; a bare :attr:`max_count` is also valid (the loader enforces this
    combination, ExecPlan Decision Log "constraint combination semantics"). At
    least one of the four is always set: a ration-less device is a no-op the
    author did not intend, so the loader rejects it.

    Attributes
    ----------
    id : str
        The device's stable identifier, named in any structured output and in any
        loader error that flags this device.
    pattern : str
        The regular-expression source, kept verbatim for reporting so the
        emitted finding can echo the authored pattern.
    compiled : re.Pattern[str]
        The compiled form of :attr:`pattern`, compiled once at load time so the
        detection logic (task 7.1.2) never recompiles per match.
    max_count : int | None
        The maximum total number of hits across the whole manuscript, a positive
        integer when set, ``None`` otherwise.
    allowed_chapters : tuple[int, ...] | None
        The chapters the device may be spent in; every hit's chapter must be in
        this set. A non-empty tuple of positive ints when set, ``None`` otherwise.
    retired_after_chapter : int | None
        The last chapter the device may appear in; no hit may fall in a later
        chapter. A positive integer when set, ``None`` otherwise.
    reserved_for_chapter : int | None
        The single chapter the device is reserved for; every hit must fall in
        this chapter. A positive integer when set, ``None`` otherwise.
    """

    id: str
    pattern: str
    compiled: re.Pattern[str]
    max_count: int | None
    allowed_chapters: tuple[int, ...] | None
    retired_after_chapter: int | None
    reserved_for_chapter: int | None


@dataclasses.dataclass(frozen=True, kw_only=True, slots=True)
class DeviceLedger:
    """A whole versioned device ledger (design §6.3).

    Attributes
    ----------
    schema_version : int
        The device-ledger schema version (currently
        :data:`LEDGER_SCHEMA_VERSION`), independent of the envelope, state, and
        rule-pack versions (design §3.1, §6.1).
    devices : tuple[Device, ...]
        The devices in authoring order. The tuple is already immutable, so no
        further freezing is needed.
    """

    schema_version: int
    devices: tuple[Device, ...]
