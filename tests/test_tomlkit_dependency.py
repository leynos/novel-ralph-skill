"""Confirm the locked ``tomlkit`` dependency for roadmap task 1.2.2.

This is the dependency-confirmation check for roadmap task 1.2.2 ("Add
``tomlkit`` to the package dependencies and confirm the build"). It proves that
``tomlkit`` resolves, imports, and round-trips comments at the locked version,
so the declared dependency is provably load-bearing and cannot be dropped
silently (the repository has no unused-dependency gate).

The check operates on a small in-test TOML string, *not* on ``state.toml``. The
property-based round-trip over generated states — the state round-trip helper,
the atomic temp-file-and-``Path.replace`` write, and the ``[pending_turn]``
intent record — is roadmap task 2.2.1 (design §9, ADR 002 "Migration plan").
That work is intentionally not implemented here.
"""

from __future__ import annotations

import tomlkit

# why: tracks the version pinned in uv.lock; bump in lockstep with a deliberate
# tomlkit upgrade. This exact pin is the tripwire for the major-version
# round-trip regression named in ADR 002 "Known risks" — a silent
# re-resolution trips it, a deliberate bump updates it visibly.
LOCKED_TOMLKIT_VERSION = "0.15.0"

# A comment-bearing TOML fragment: a standalone comment, an inline comment, and
# a table. Round-trips byte-for-byte through the locked tomlkit.
SRC = '# standalone comment\nkey = "value"  # inline comment\n\n[table]\na = 1\n'


def test_tomlkit_import_and_version() -> None:
    """``tomlkit`` imports and resolves to the locked version.

    Returns
    -------
    None
        The assertions raise on failure.
    """
    assert tomlkit.__version__ == LOCKED_TOMLKIT_VERSION


def test_tomlkit_roundtrip_is_lossless() -> None:
    """A no-op parse/dump round-trips the source byte-for-byte.

    Returns
    -------
    None
        The assertion raises on failure.
    """
    assert tomlkit.dumps(tomlkit.parse(SRC)) == SRC


def test_tomlkit_edit_preserves_comments() -> None:
    """A value edit changes only the target and keeps the comments.

    Returns
    -------
    None
        The assertions raise on failure.
    """
    doc = tomlkit.parse(SRC)
    doc["table"]["a"] = 2
    out = tomlkit.dumps(doc)
    assert "# standalone comment" in out
    assert "# inline comment" in out
    assert "a = 2" in out
