"""Rationing-field validation for the device-ledger boundary (design §6.3).

This leaf module carries the constraint-combination semantics the ExecPlan
Decision Log fixes, extracted from ``parse.py`` purely to keep that module under
the AGENTS.md 400-line file cap. It validates the four rationing fields of one
``[[device]]`` entry — ``max_count``, ``allowed_chapters``,
``retired_after_chapter``, ``reserved_for_chapter`` — and enforces that a device
carries at least one of them and at most one window constraint, raising
:class:`LedgerError` naming the offending device on any violation.

Every name is underscore-prefixed (no public surface); ``parse.py`` imports the
:func:`_rationing_fields` aggregate (and the helpers it needs are private to this
module).
"""

from __future__ import annotations

import collections.abc as cabc

from novel_ralph_skill.ledger._coerce import (
    _Mapping,
    _require,
    _require_int,
    _where,
)
from novel_ralph_skill.ledger.errors import LedgerError

# The three chapter-window constraints. A device may carry at most one of these
# (ExecPlan Decision Log "constraint combination semantics"). ``max_count`` is
# not a window constraint: it may pair with any one of these.
_WINDOW_KEYS: tuple[str, ...] = (
    "allowed_chapters",
    "retired_after_chapter",
    "reserved_for_chapter",
)


def _positive_int(entry: _Mapping, key: str, *, device_id: str) -> int:
    """Return ``entry[key]`` as a positive integer or raise naming the device.

    Parameters
    ----------
    entry : collections.abc.Mapping[str, object]
        The decoded device entry.
    key : str
        The numeric key (``max_count``/``retired_after_chapter``/
        ``reserved_for_chapter``).
    device_id : str
        The offending device's ``id``, named in any error.

    Returns
    -------
    int
        The positive integer value at ``key``.

    Raises
    ------
    LedgerError
        If the value is not an integer or is not positive.
    """
    value = _require_int(entry, key, device_id=device_id)
    if value <= 0:
        msg = f"{_where(device_id)} {key!r} must be positive, got {value}"
        raise LedgerError(msg, device_id=device_id)
    return value


def _allowed_chapters(entry: _Mapping, *, device_id: str) -> tuple[int, ...]:
    """Return ``allowed_chapters`` as a non-empty tuple of positive ints.

    The TOML array is coerced to a ``tuple`` at this boundary, every element
    runtime-checked to be a positive integer (rejecting ``bool``, as
    :func:`_require_int` does), and the array must be non-empty (an empty allowed
    set would forbid the device everywhere, a no-op the author did not intend).

    Parameters
    ----------
    entry : collections.abc.Mapping[str, object]
        The decoded device entry.
    device_id : str
        The offending device's ``id``, named in any error.

    Returns
    -------
    tuple[int, ...]
        The allowed chapters, in authoring order.

    Raises
    ------
    LedgerError
        If ``allowed_chapters`` is not an array, is empty, or holds a non-positive
        or non-integer element.
    """
    value = _require(entry, "allowed_chapters", device_id=device_id)
    if isinstance(value, (str, bytes)) or not isinstance(value, cabc.Sequence):
        msg = (
            f"{_where(device_id)} 'allowed_chapters' must be an array of "
            f"positive integers, got {type(value).__name__}"
        )
        raise LedgerError(msg, device_id=device_id)
    if not value:
        msg = f"{_where(device_id)} 'allowed_chapters' must be non-empty"
        raise LedgerError(msg, device_id=device_id)
    chapters: list[int] = []
    for element in value:
        if isinstance(element, bool) or not isinstance(element, int):
            msg = (
                f"{_where(device_id)} 'allowed_chapters' elements must be "
                f"integers, got {type(element).__name__}"
            )
            raise LedgerError(msg, device_id=device_id)
        if element <= 0:
            msg = (
                f"{_where(device_id)} 'allowed_chapters' elements must be "
                f"positive, got {element}"
            )
            raise LedgerError(msg, device_id=device_id)
        chapters.append(element)
    return tuple(chapters)


def _present_windows(entry: _Mapping) -> tuple[str, ...]:
    """Return the window-constraint keys present on ``entry``, in canonical order.

    Parameters
    ----------
    entry : collections.abc.Mapping[str, object]
        The decoded device entry.

    Returns
    -------
    tuple[str, ...]
        The subset of :data:`_WINDOW_KEYS` present on ``entry``.
    """
    return tuple(key for key in _WINDOW_KEYS if key in entry)


def _rationing_fields(
    entry: _Mapping, *, device_id: str
) -> tuple[int | None, tuple[int, ...] | None, int | None, int | None]:
    """Validate and return the four rationing fields for one device entry.

    Enforces the constraint-combination semantics (ExecPlan Decision Log): a
    device must carry at least one of the four rationing fields; at most one of
    the three window constraints. ``max_count`` may co-exist with any one window.
    A ration-less device or a two-window device is a :class:`LedgerError` naming
    the device.

    Parameters
    ----------
    entry : collections.abc.Mapping[str, object]
        The decoded device entry.
    device_id : str
        The offending device's ``id``, named in any error.

    Returns
    -------
    tuple[int | None, tuple[int, ...] | None, int | None, int | None]
        The validated ``(max_count, allowed_chapters, retired_after_chapter,
        reserved_for_chapter)``.

    Raises
    ------
    LedgerError
        If the device carries no ration, carries two window constraints, or any
        present bound is non-positive or wrong-typed.
    """
    windows = _present_windows(entry)
    if len(windows) > 1:
        listed = ", ".join(repr(key) for key in windows)
        msg = (
            f"{_where(device_id)} carries more than one window constraint "
            f"({listed}); a device may carry at most one of "
            f"'allowed_chapters', 'retired_after_chapter', 'reserved_for_chapter'"
        )
        raise LedgerError(msg, device_id=device_id)
    has_max = "max_count" in entry
    if not has_max and not windows:
        msg = (
            f"{_where(device_id)} carries no ration; declare at least one of "
            f"'max_count', 'allowed_chapters', 'retired_after_chapter', "
            f"'reserved_for_chapter'"
        )
        raise LedgerError(msg, device_id=device_id)
    max_count = (
        _positive_int(entry, "max_count", device_id=device_id) if has_max else None
    )
    allowed = (
        _allowed_chapters(entry, device_id=device_id)
        if "allowed_chapters" in entry
        else None
    )
    retired = (
        _positive_int(entry, "retired_after_chapter", device_id=device_id)
        if "retired_after_chapter" in entry
        else None
    )
    reserved = (
        _positive_int(entry, "reserved_for_chapter", device_id=device_id)
        if "reserved_for_chapter" in entry
        else None
    )
    return max_count, allowed, retired, reserved
