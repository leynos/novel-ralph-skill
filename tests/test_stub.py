"""Tests for the generated package stub."""

from __future__ import annotations

import novel_ralph_skill


def test_hello_returns_stub_greeting() -> None:
    """The generated package exposes a working greeting."""
    assert novel_ralph_skill.hello() == "hello from Python"
