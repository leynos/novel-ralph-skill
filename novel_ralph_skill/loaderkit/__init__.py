"""The single home for the schema-agnostic loader primitives both packs share.

The rule pack (:mod:`novel_ralph_skill.rulepack`) and the device ledger
(:mod:`novel_ralph_skill.ledger`) were built as deliberate parallels, which left
six near-verbatim primitives cloned between them: the scalar-coercion family, the
array-of-tables extractor, the eager pattern compiler, the duplicate-id rejector,
the file-fault TOML loader, and the per-line scan. They differed only in their
typed error channel and a noun ("rule"/"rule pack" versus "device"/"device
ledger"). Roadmap task 7.2.2 consolidates them here so exactly one body of each
primitive survives (design §6; ADR-001), and roadmap 7.2.3 relocates the per-line
scan's two neutral shapes — :class:`ScannedChapter` and :class:`LineHit` — here
too, so a third pack family inherits them rather than cloning or cross-importing
them.

Each primitive is **parameterised on an error factory** rather than hard-wired to
one package's exception: a caller binds a small :class:`CoercionErrors` bundle of
callables and nouns that decides *how* to raise and *what to call the offending
thing*. The rule pack binds it to :class:`RulePackError` with "rule"/"rule pack"
nouns; the ledger binds it to :class:`LedgerError` with "device"/"device ledger"
nouns; a third pack family inherits the primitives by binding one more bundle
rather than cloning a third copy.

The two-class failure *shape* every family raises lives here too (roadmap task
7.2.5): :class:`~novel_ralph_skill.loaderkit.errors.PackError` (the exit-``2``
content base) and :class:`~novel_ralph_skill.loaderkit.errors.PackFileError` (the
exit-``3`` file base). Each pack binds these by subclassing them with its own
typed channel name and id keyword (``RulePackError``/``RulePackFileError`` with
``rule_id``; ``LedgerError``/``LedgerFileError`` with ``device_id``), so a third
family inherits the hierarchy rather than re-spelling a third near-identical
pair, exactly as it inherits the coercion bundle.

This module depends only on the ``contract`` layer (for the
:class:`~novel_ralph_skill.contract.errors.EnvelopeMessagesError` base it
type-hints against) and the standard library. It imports neither ``rulepack`` nor
``ledger`` at runtime, so both may depend on it without an import cycle (design
§3.1; ADR-003).
"""

from __future__ import annotations

from novel_ralph_skill.loaderkit.coerce import (
    CoercionErrors,
    Mapping,
    reject_unknown_keys,
    require,
    require_int,
    require_str,
    where,
)
from novel_ralph_skill.loaderkit.errors import PackError, PackFileError
from novel_ralph_skill.loaderkit.load import (
    EntriesMessages,
    compile_pattern,
    entries,
    load_toml,
    reject_duplicate_ids,
)
from novel_ralph_skill.loaderkit.scan import LineHit, ScannedChapter, scan_pattern

__all__ = [
    "CoercionErrors",
    "EntriesMessages",
    "LineHit",
    "Mapping",
    "PackError",
    "PackFileError",
    "ScannedChapter",
    "compile_pattern",
    "entries",
    "load_toml",
    "reject_duplicate_ids",
    "reject_unknown_keys",
    "require",
    "require_int",
    "require_str",
    "scan_pattern",
    "where",
]
