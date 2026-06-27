"""The validating boundary that builds a typed :class:`DeviceLedger` from TOML.

This module is the single place a decoded device-ledger mapping becomes a typed
:class:`~novel_ralph_skill.ledger.schema.DeviceLedger`, so no raw
``dict[str, object]`` leaks inward (python-data-shapes: "parse to a schema type
at the boundary"). It mirrors the *structure* of
``novel_ralph_skill/rulepack/parse.py`` — a pure :func:`parse_ledger` boundary, a
thin :func:`load_ledger` ``tomllib`` file convenience, every TOML array coerced
to a ``tuple``, every field runtime-checked with an ``isinstance``/membership
guard — but raises the ledger's own :class:`LedgerError`/:class:`LedgerFileError`
typed channels (not ``RulePackError``), with ``"device '<id>'"`` wording.

The loader enforces the **constraint-combination semantics** the ExecPlan
Decision Log fixes: each device carries at least one of the four rationing
fields; at most one of the three window constraints (``allowed_chapters``,
``retired_after_chapter``, ``reserved_for_chapter``); ``max_count`` may pair with
any one window; a ration-less device or a two-window device is a loud
:class:`LedgerError` naming the device. A ``max_count``/``retired_after_chapter``/
``reserved_for_chapter`` must be a positive integer; ``allowed_chapters`` must be
a non-empty array of positive integers.

The loader is read-only and detect-only (ADR-001): it compiles each pattern with
the standard-library ``re`` and validates structure, never judging prose. It
calls neither :func:`sys.exit` nor any envelope builder; exit-code translation is
the command body's job (task 7.1.2).
"""

from __future__ import annotations

import typing as typ

from novel_ralph_skill.ledger._coerce import (
    _ERRORS,
    _Mapping,
    _reject_unknown_keys,
    _require_str,
)
from novel_ralph_skill.ledger._fields import _rationing_fields
from novel_ralph_skill.ledger.errors import LedgerError, LedgerFileError
from novel_ralph_skill.ledger.schema import (
    LEDGER_SCHEMA_VERSION,
    Device,
    DeviceLedger,
)
from novel_ralph_skill.loaderkit import (
    EntriesMessages,
    build_entries,
    compile_pattern,
    load_toml,
    resolve_schema_version,
)

if typ.TYPE_CHECKING:
    import collections.abc as cabc
    from importlib.resources.abc import Traversable

# The complete v1 key vocabularies. An unknown key on either the ledger table or
# a device entry is rejected (naming the offending level/device) rather than
# silently ignored, so a misspelled field (``max_counts = 3``) fails loudly — the
# same loud-failure discipline the rule-pack loader established (roadmap 5.1.1).
_LEDGER_KEYS: frozenset[str] = frozenset({"schema_version", "device"})
_DEVICE_KEYS: frozenset[str] = frozenset({
    "id",
    "pattern",
    "max_count",
    "allowed_chapters",
    "retired_after_chapter",
    "reserved_for_chapter",
})


# The ledger's verbatim array-extraction messages, bound onto the shared
# ``entries`` primitive (Decision D-ENTRIES). These strings carry the quoted array
# key, the container noun (``ledger``), and the item noun (``device``) whole —
# nouns the ``CoercionErrors`` pair cannot supply — so they live at this call
# site, not in ``loaderkit``.
_ENTRIES_MESSAGES = EntriesMessages(
    not_array="'device' must be an array of tables, got {type_name}",
    empty="'device' array is empty; a ledger must declare at least one device",
    non_mapping="device at index {index} must be a table, got {type_name}",
)


def _device(entry: _Mapping, *, index: int) -> Device:
    """Build one validated :class:`Device` from a decoded device entry.

    Resolves ``id`` first so it can name the device in any subsequent error this
    entry raises; a missing or non-string ``id`` is a ledger-level fault that
    names the device's array ``index`` instead (there is no id to name yet).

    Parameters
    ----------
    entry : collections.abc.Mapping[str, object]
        The decoded ``[[device]]`` table.
    index : int
        The device's zero-based position in the array, named when ``id`` is
        absent.

    Returns
    -------
    Device
        The fully validated, frozen device.

    Raises
    ------
    LedgerError
        On any missing, wrong-typed, or out-of-range field, any unknown key, any
        invalid pattern, or any invalid constraint combination, naming the device
        (or its ``index`` when ``id`` itself is the fault).
    """
    if "id" not in entry or not isinstance(entry["id"], str):
        msg = f"device at index {index} is missing a string 'id'"
        raise LedgerError(msg, device_id=None)
    # The ``isinstance`` guard above has already narrowed ``entry["id"]``.
    device_id = entry["id"]

    _reject_unknown_keys(entry, _DEVICE_KEYS, device_id=device_id)
    pattern = _require_str(entry, "pattern", device_id=device_id)
    max_count, allowed, retired, reserved = _rationing_fields(
        entry, device_id=device_id
    )

    return Device(
        id=device_id,
        pattern=pattern,
        compiled=compile_pattern(pattern, errors=_ERRORS, offending_id=device_id),
        max_count=max_count,
        allowed_chapters=allowed,
        retired_after_chapter=retired,
        reserved_for_chapter=reserved,
    )


def parse_ledger(raw: cabc.Mapping[str, object]) -> DeviceLedger:
    """Construct a validated :class:`DeviceLedger` from a decoded TOML mapping.

    Pure — a decoded mapping in, a validated :class:`DeviceLedger` out — so any
    ledger consumer can reuse it without a filesystem. Every field is
    runtime-checked and every TOML array is coerced to a ``tuple`` at this
    boundary. A malformed ledger raises :class:`LedgerError`, naming the offending
    device (or ledger-level for a ``schema_version``/``device``-array fault).

    Parameters
    ----------
    raw : collections.abc.Mapping[str, object]
        The decoded device-ledger mapping, as ``tomllib.load`` returns.

    Returns
    -------
    DeviceLedger
        The fully validated, frozen device ledger.

    Raises
    ------
    LedgerError
        If ``schema_version`` is absent, wrong-typed, or unexpected; if the
        ``device`` array is absent, empty, or holds a malformed device; if any
        device field is missing, wrong-typed, or out of range; if a device's
        pattern will not compile; if a device carries no ration or two window
        constraints; if the ledger or any device carries an unknown key; or if two
        devices share an ``id``.

    Notes
    -----
    :class:`LedgerError` is the *only* exception this pure boundary raises: every
    malformed-content fault is converted into it. File and decode faults are not
    this function's concern — they belong to :func:`load_ledger`, which raises
    :class:`LedgerFileError`. Task 7.1.2 can therefore catch exactly these two
    types and map each to its exit code.

    The orchestration is the shared ``loaderkit`` validating-parse skeleton
    (roadmap 7.2.6): the head
    :func:`~novel_ralph_skill.loaderkit.parse.resolve_schema_version` rejects
    unknown keys and resolves the version, then the tail
    :func:`~novel_ralph_skill.loaderkit.parse.build_entries` extracts the array,
    builds each :class:`Device`, and rejects duplicate ids. Unlike the rule pack
    the ledger has **no** top-level string field, so the head and tail run
    back-to-back with nothing read at the seam — there is no precedence question
    and no asymmetry to preserve. The :class:`DeviceLedger` construction stays
    here, at the leaf (the skeleton names no pack type).
    """
    schema_version = resolve_schema_version(
        raw,
        allowed_keys=_LEDGER_KEYS,
        schema_version_constant=LEDGER_SCHEMA_VERSION,
        unsupported_noun="device-ledger",
        errors=_ERRORS,
    )
    devices = build_entries(
        raw,
        array_key="device",
        entries_messages=_ENTRIES_MESSAGES,
        errors=_ERRORS,
        build_entry=lambda entry, index: _device(entry, index=index),
    )
    return DeviceLedger(schema_version=schema_version, devices=devices)


def load_ledger(path: Traversable) -> DeviceLedger:
    """Read and parse a device ledger from ``path`` with ``tomllib``.

    A thin convenience over :func:`parse_ledger`: it opens ``path`` in binary
    mode, decodes it with the standard-library ``tomllib``, and delegates the
    validated construction. A file fault (absent, unreadable) or an undecodable
    TOML is the exit-3 channel and raises :class:`LedgerFileError`; a structurally
    valid TOML that violates the schema propagates as the exit-2
    :class:`LedgerError` from :func:`parse_ledger`.

    ``path`` is typed as :class:`~importlib.resources.abc.Traversable` rather than
    :class:`pathlib.Path` for signature symmetry with ``load_rulepack``; the
    device ledger is per-novel user data supplied as a filesystem
    :class:`pathlib.Path` (which *is* a ``Traversable``), never a packaged
    resource, and this function only needs the ``.open("rb")`` the protocol
    guarantees.

    Parameters
    ----------
    path : importlib.resources.abc.Traversable
        The device-ledger TOML resource: a filesystem :class:`pathlib.Path` from
        ``--ledger``.

    Returns
    -------
    DeviceLedger
        The fully validated, frozen device ledger parsed from ``path``.

    Raises
    ------
    LedgerFileError
        If ``path`` is absent or unreadable, or its bytes are not decodable TOML.
    LedgerError
        If the decoded ledger violates the schema (propagated unchanged).
    """
    raw = load_toml(path, noun="device ledger", file_error=LedgerFileError)
    return parse_ledger(raw)
