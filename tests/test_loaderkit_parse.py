"""Unit tests for the shared ``loaderkit`` validating-parse skeleton (roadmap 7.2.6).

These pin the head/tail pair
:func:`~novel_ralph_skill.loaderkit.parse.resolve_schema_version` and
:func:`~novel_ralph_skill.loaderkit.parse.build_entries` against a test-local
third-family binding — a ``_Thing`` entry with **no** extra top-level field —
proving a third pack family inherits the skeleton rather than cloning a third
``parse_*`` orchestration (the roadmap Success criterion).

The pins follow the sentinel-bundle and verbatim-prose idioms
``tests/test_loaderkit_load.py`` established. They cover: a happy path composing
both halves; every fault routed through the bundle (both unsupported-version
sentences pinned verbatim for both family nouns); the build/``entry_id`` callbacks
honoured verbatim; **head/tail seam independence** (the head never reaches the
array, the tail never inspects the top-level keys/version), which is what buys the
rule pack's ``pack``-before-``entries`` precedence; and an AST guard that the
module imports no pack domain.
"""

from __future__ import annotations

import ast
import dataclasses
import pathlib

import pytest

from novel_ralph_skill.contract.errors import EnvelopeMessagesError
from novel_ralph_skill.loaderkit.coerce import CoercionErrors, Mapping
from novel_ralph_skill.loaderkit.load import EntriesMessages
from novel_ralph_skill.loaderkit.parse import build_entries, resolve_schema_version

_THING_VERSION = 1


class _SentinelError(EnvelopeMessagesError):
    """A test-local content error recording the offending id the bundle passed."""

    def __init__(self, *messages: str, offending_id: str | None = None) -> None:
        """Record the messages and the offending id for assertions."""
        super().__init__(*messages)
        self.offending_id: str | None = offending_id


def _bundle(
    *, per_id_noun: str = "thing", per_level_noun: str = "thing pack"
) -> CoercionErrors:
    """Build a :class:`CoercionErrors` raising :class:`_SentinelError`."""
    return CoercionErrors(
        content_error=lambda msg, oid: _SentinelError(msg, offending_id=oid),
        per_id_noun=per_id_noun,
        per_level_noun=per_level_noun,
    )


# A test-local third-family binding: a ``_Thing`` entry with **no** extra top-level
# field (unlike the rule pack's ``pack``), so the skeleton serves an arbitrary
# third family without an import of any real pack type.
_THING_KEYS: frozenset[str] = frozenset({"schema_version", "thing"})
_THING_MESSAGES = EntriesMessages(
    not_array="'thing' must be an array of tables, got {type_name}",
    empty="'thing' array is empty; a pack must declare at least one thing",
    non_mapping="thing at index {index} must be a table, got {type_name}",
)


@dataclasses.dataclass(frozen=True, kw_only=True, slots=True)
class _Thing:
    """A test-local built entry standing in for ``Rule``/``Device``."""

    id: str
    value: int


def _build_thing(entry: Mapping, *, index: int) -> _Thing:
    """Build one ``_Thing`` from a decoded entry, naming ``index`` on a missing id.

    Keyword-only ``index`` mirrors the real ``_rule``/``_device`` builders, so the
    happy-path and duplicate-id tests bind it directly as ``build_entry=_build_thing``
    (no identity lambda), proving a third family inherits the keyword-builder seam.
    """
    raw_id = entry.get("id")
    if not isinstance(raw_id, str):
        msg = f"thing at index {index} is missing a string 'id'"
        raise _SentinelError(msg, offending_id=None)
    raw_value = entry.get("value")
    value = raw_value if isinstance(raw_value, int) else 0
    return _Thing(id=raw_id, value=value)


def test_head_then_tail_compose_for_valid_mapping() -> None:
    """The head resolves the version and the tail builds the entries, composed.

    This composes both halves the way a real binding does — ``version =
    resolve_schema_version(...)`` then ``built = build_entries(..., build_entry=...)``
    — for an arbitrary third family with no pack import.
    """
    bundle = _bundle()
    raw = {
        "schema_version": _THING_VERSION,
        "thing": [{"id": "a", "value": 1}, {"id": "b", "value": 2}],
    }
    version = resolve_schema_version(
        raw,
        allowed_keys=_THING_KEYS,
        schema_version_constant=_THING_VERSION,
        unsupported_noun="thing-pack",
        errors=bundle,
    )
    built = build_entries(
        raw,
        array_key="thing",
        entries_messages=_THING_MESSAGES,
        errors=bundle,
        build_entry=_build_thing,
    )
    assert version == _THING_VERSION
    assert built == (_Thing(id="a", value=1), _Thing(id="b", value=2))


def test_head_rejects_unknown_top_level_key() -> None:
    """The head rejects an unknown top-level key through the bundle."""
    bundle = _bundle()
    with pytest.raises(_SentinelError) as excinfo:
        resolve_schema_version(
            {"schema_version": _THING_VERSION, "thing": [], "bogus": 1},
            allowed_keys=_THING_KEYS,
            schema_version_constant=_THING_VERSION,
            unsupported_noun="thing-pack",
            errors=bundle,
        )
    assert "unknown key(s) 'bogus'" in excinfo.value.messages[0]


def test_head_rejects_missing_schema_version() -> None:
    """The head rejects an absent ``schema_version`` through the bundle."""
    bundle = _bundle()
    with pytest.raises(_SentinelError) as excinfo:
        resolve_schema_version(
            {"thing": []},
            allowed_keys=_THING_KEYS,
            schema_version_constant=_THING_VERSION,
            unsupported_noun="thing-pack",
            errors=bundle,
        )
    assert "missing required key 'schema_version'" in excinfo.value.messages[0]


@pytest.mark.parametrize(
    ("unsupported_noun", "expected"),
    [
        ("rule-pack", "unsupported rule-pack schema_version 2; expected 1"),
        ("device-ledger", "unsupported device-ledger schema_version 2; expected 1"),
    ],
)
def test_head_pins_unsupported_version_sentence(
    unsupported_noun: str, expected: str
) -> None:
    """The head pins both unsupported-version sentences verbatim for both nouns.

    The per-family hyphenated noun (``rule-pack``/``device-ledger``) is a distinct
    string the ``CoercionErrors`` pair cannot supply, so a skeleton that hard-coded
    either noun would drift one family's snapshot. Pinning the full string for both
    closes that silent-drift hazard.
    """
    bundle = _bundle()
    with pytest.raises(_SentinelError) as excinfo:
        resolve_schema_version(
            {"schema_version": 2, "thing": []},
            allowed_keys=_THING_KEYS,
            schema_version_constant=_THING_VERSION,
            unsupported_noun=unsupported_noun,
            errors=bundle,
        )
    assert excinfo.value.messages[0] == expected
    assert excinfo.value.offending_id is None


def test_tail_rejects_absent_entry_array() -> None:
    """The tail rejects an absent entry array through the ``EntriesMessages`` bundle."""
    bundle = _bundle()
    with pytest.raises(_SentinelError) as excinfo:
        build_entries(
            {"schema_version": _THING_VERSION},
            array_key="thing",
            entries_messages=_THING_MESSAGES,
            errors=bundle,
            build_entry=_build_thing,
        )
    assert "missing required key 'thing'" in excinfo.value.messages[0]


def test_tail_pins_empty_array_sentence() -> None:
    """The tail pins the empty-array sentence verbatim from ``EntriesMessages``."""
    bundle = _bundle()
    with pytest.raises(_SentinelError) as excinfo:
        build_entries(
            {"thing": []},
            array_key="thing",
            entries_messages=_THING_MESSAGES,
            errors=bundle,
            build_entry=_build_thing,
        )
    assert (
        excinfo.value.messages[0]
        == "'thing' array is empty; a pack must declare at least one thing"
    )


def test_tail_rejects_non_mapping_entry() -> None:
    """The tail rejects a non-mapping entry through the ``EntriesMessages`` bundle."""
    bundle = _bundle()
    with pytest.raises(_SentinelError) as excinfo:
        build_entries(
            {"thing": [7]},
            array_key="thing",
            entries_messages=_THING_MESSAGES,
            errors=bundle,
            build_entry=_build_thing,
        )
    assert "thing at index 0 must be a table, got int" in excinfo.value.messages[0]


def test_tail_rejects_duplicate_id() -> None:
    """The tail rejects a duplicate id through ``reject_duplicate_ids``."""
    bundle = _bundle()
    with pytest.raises(_SentinelError) as excinfo:
        build_entries(
            {"thing": [{"id": "x", "value": 1}, {"id": "x", "value": 2}]},
            array_key="thing",
            entries_messages=_THING_MESSAGES,
            errors=bundle,
            build_entry=_build_thing,
        )
    assert "'x' is defined more than once" in excinfo.value.messages[0]
    assert excinfo.value.offending_id == "x"


def test_tail_calls_build_entry_per_entry_in_authoring_order() -> None:
    """The tail calls ``build_entry`` once per entry, in order, using its returns.

    A recording double asserts ``build_entries`` calls the builder once per entry
    in authoring order with the right ``(entry, index)`` pairs and uses its return
    values verbatim (the ``line_hit``-callback idiom from
    ``tests/test_loaderkit_scan.py``). The builder's ``index`` is **keyword-only**
    (``*, index``), so the test also fails if ``build_entries`` were to revert to
    calling the builder positionally — pinning the keyword-call convention the
    ``build_entry=_rule`` direct bind depends on.
    """
    bundle = _bundle()
    calls: list[tuple[Mapping, int]] = []
    entry_a = {"id": "a", "value": 1}
    entry_b = {"id": "b", "value": 2}

    def recording_build(entry: Mapping, *, index: int) -> _Thing:
        """Record each ``(entry, index)`` call and return a derived ``_Thing``."""
        calls.append((entry, index))
        return _Thing(id=str(entry["id"]), value=index)

    built = build_entries(
        {"thing": [entry_a, entry_b]},
        array_key="thing",
        entries_messages=_THING_MESSAGES,
        errors=bundle,
        build_entry=recording_build,
    )
    assert calls == [(entry_a, 0), (entry_b, 1)]
    assert built == (_Thing(id="a", value=0), _Thing(id="b", value=1))


def test_tail_projects_ids_via_supplied_entry_id() -> None:
    """The duplicate-id pass projects ids via the supplied ``entry_id``, not ``.id``.

    Building entries whose ``.id`` differs but whose ``entry_id`` projection
    collides proves the projection is the supplied callable, not a hard-coded
    ``.id``.
    """
    bundle = _bundle()
    projected: list[_Thing] = []

    def project_value(thing: _Thing) -> str:
        """Project a ``_Thing`` to its ``value`` as the dedup key, not its ``id``."""
        projected.append(thing)
        return str(thing.value)

    with pytest.raises(_SentinelError) as excinfo:
        build_entries(
            {"thing": [{"id": "a", "value": 5}, {"id": "b", "value": 5}]},
            array_key="thing",
            entries_messages=_THING_MESSAGES,
            errors=bundle,
            build_entry=_build_thing,
            entry_id=project_value,
        )
    assert "'5' is defined more than once" in excinfo.value.messages[0]
    assert [thing.id for thing in projected] == ["a", "b"]


def test_head_raises_version_fault_without_reaching_array() -> None:
    """The head raises the version fault even when the entry array is malformed.

    Seam independence: passing a mapping whose ``thing`` array is malformed but
    whose ``schema_version`` is unsupported proves the head raises the *version*
    fault and never reaches the array. This is what lets a caller interleave its
    ``pack`` read at the seam and keep head faults strictly ahead of tail faults.
    """
    bundle = _bundle()
    with pytest.raises(_SentinelError) as excinfo:
        resolve_schema_version(
            {"schema_version": 99, "thing": 7},
            allowed_keys=_THING_KEYS,
            schema_version_constant=_THING_VERSION,
            unsupported_noun="thing-pack",
            errors=bundle,
        )
    assert "unsupported thing-pack schema_version 99" in excinfo.value.messages[0]


def test_tail_builds_without_inspecting_top_level_keys_or_version() -> None:
    """The tail builds the array regardless of a bad/extra top-level key or version.

    Seam independence: passing a mapping with an unknown top-level key and an absent
    ``schema_version`` but a valid entry array proves the tail builds it without
    complaint — it inspects neither the top-level key set nor the version.
    """
    bundle = _bundle()
    built = build_entries(
        {"bogus": 1, "thing": [{"id": "a", "value": 1}]},
        array_key="thing",
        entries_messages=_THING_MESSAGES,
        errors=bundle,
        build_entry=_build_thing,
    )
    assert built == (_Thing(id="a", value=1),)


def test_parse_module_imports_no_pack_domain() -> None:
    """``loaderkit/parse.py`` imports nothing from a pack domain (belt and braces).

    This complements the package-wide glob guard in
    ``tests/test_loaderkit_scan.py``: an AST scan of the module's own source asserts
    the neutral-leaf invariant directly for the new module.
    """
    from novel_ralph_skill.loaderkit import parse

    source = pathlib.Path(parse.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    package = "novel_ralph_skill.loaderkit"
    imported: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            # Resolve a relative ``from . import x`` against ``loaderkit`` so a
            # sibling-pack import cannot slip through unqualified; ``level`` counts
            # the leading dots, ``module`` is the absolute tail (or ``None``).
            if node.level:
                base = (
                    package.rsplit(".", node.level - 1)[0]
                    if node.level > 1
                    else package
                )
                prefix = f"{base}.{node.module}" if node.module else base
                imported.extend(f"{prefix}.{alias.name}" for alias in node.names)
            elif node.module:
                imported.append(node.module)
        elif isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
    banned = ("novel_ralph_skill.rulepack", "novel_ralph_skill.ledger")
    assert not [module for module in imported if module.startswith(banned)]
