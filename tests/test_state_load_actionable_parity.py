"""Cross-arm no-raw-leak tripwire over the exit-3 actionable-message formatters.

Roadmap §6.3.8 closes the last raw-OS-text leaks on the state-input (exit-3)
channel: the compile-write, rule-pack-read, and device-ledger-read formatters
join the existing state-load and draft-read formatters in
:mod:`novel_ralph_skill.commands.state_sourcing`, all building actionable prose from
the artefact path rather than from a caught exception's repr (ExecPlan Decision
D2; ``scripting-standards.md`` line 678).

This guard pins that no-raw-leak property *structurally* rather than relying on
per-arm diligence, mirroring the parity-tripwire pattern roadmap 6.3.1.2 and
6.3.2.1 established. It imports the formatters straight from their definition
module ``state_sourcing`` (not the ``novel_state`` re-export) so the guard exercises
the implementation location, then drives every formatter with a faulty path and a
representative caught exception — an ``OSError`` carrying an ``Errno`` and a
:class:`tomllib.TOMLDecodeError` — and asserts each formatter's
``StateInputError.messages``:

- contains no ``Errno``, no ``str(exc)`` substring, and no raw exception class
  name;
- is non-empty actionable prose;

and, for the file/write-fault formatters whose contract is to name the offending
artefact, that the path passed in appears in the message. For the three roadmap
§6.3.8 file-fault arms it additionally pins each arm's stable remedy clause
(``_REMEDY_TOKENS``), so a regression dropping the remedy — which the no-leak and
path-naming guards would not catch — fails here (audit:6.3.8 Finding 6).

The four path-only file-fault formatters render from the artefact path alone and
no longer take the caught exception (audit:6.3.8 Findings 1-2); only
:func:`_state_input_error` still consumes ``(path, exc)``. The guard drives each
through :func:`_render`, which supplies the caught exception only to the
two-argument formatter, so a future formatter regaining a misleading ``exc``
parameter would still be exercised here.

A future formatter (or a regression of any of these) that re-interpolates a
caught exception onto the channel fails this guard. A plain parametrised example
test is the right adversary here (not a property test): the formatters do no
input-dependent branching beyond f-string interpolation, so the input space is
small and enumerable, and the assertions are structural string properties
(``python-verification`` decision surface).
"""

from __future__ import annotations

import tomllib
import typing as typ

import pytest

from novel_ralph_skill.commands.state_sourcing import (
    _compile_write_error,
    _device_ledger_read_error,
    _draft_read_error,
    _rule_pack_read_error,
    _state_input_error,
)
from novel_ralph_skill.contract.runner import StateInputError

if typ.TYPE_CHECKING:
    import collections.abc as cabc
    import pathlib


@pytest.fixture
def faulty_path(tmp_path: pathlib.Path) -> pathlib.Path:
    """Return a guaranteed-absent artefact path under the per-test ``tmp_path``.

    Deriving it from ``tmp_path`` (rather than a hardcoded absolute path) keeps
    the missing-file precondition reliable across hosts. The parent ``working/``
    directory is created and left empty, so the named child is a missing *file*
    (not a missing *directory*) on every run — the scenario the read-fault arms
    actually exercise.
    """
    parent = tmp_path / "working"
    parent.mkdir()
    return parent / "artefact.toml"


def _errno_exception(path: pathlib.Path) -> OSError:
    """Return a real ``FileNotFoundError`` carrying an ``Errno`` and ``path``."""
    try:
        path.read_bytes()
    except OSError as exc:
        return exc
    msg = "expected reading a non-existent path to raise OSError"
    raise AssertionError(msg)


def _toml_decode_exception(path: pathlib.Path) -> tomllib.TOMLDecodeError:
    """Return a real ``TOMLDecodeError`` from decoding broken TOML.

    ``path`` is accepted (and ignored) so both exception builders share one
    signature for the parametrised call sites.
    """
    del path
    try:
        tomllib.loads("schema_version = = 1")
    except tomllib.TOMLDecodeError as exc:
        return exc
    msg = "expected decoding broken TOML to raise TOMLDecodeError"
    raise AssertionError(msg)


# Every exit-3 formatter, held to the no-raw-leak property.
_ALL_FORMATTERS: tuple[tuple[str, cabc.Callable[..., StateInputError]], ...] = (
    ("compile-write", _compile_write_error),
    ("rule-pack-read", _rule_pack_read_error),
    ("device-ledger-read", _device_ledger_read_error),
    ("draft-read", _draft_read_error),
    ("state-input", _state_input_error),
)

# The subset whose contract requires naming the offending artefact path.
# ``_state_input_error`` is excluded: its absent-path case takes its
# absent-working/ arm, which names the cwd rather than the artefact (it is still
# held to no-raw-leak above).
_PATH_NAMING_FORMATTERS: tuple[tuple[str, cabc.Callable[..., StateInputError]], ...] = (
    ("compile-write", _compile_write_error),
    ("rule-pack-read", _rule_pack_read_error),
    ("device-ledger-read", _device_ledger_read_error),
    ("draft-read", _draft_read_error),
)

_EXCEPTIONS: list[cabc.Callable[..., Exception]] = [
    _errno_exception,
    _toml_decode_exception,
]

# The stable remedy clause each of the three roadmap §6.3.8 file-fault arms must
# carry. The no-leak and path-naming guards above pin *what the message omits* and
# *that it names the artefact*, but neither pins the remedy that makes the message
# actionable, so a regression dropping the remedy would still pass. Each token is a
# distinctive, stable substring of the arm's remedy clause (audit:6.3.8 Finding 6).
_REMEDY_TOKENS: tuple[tuple[str, cabc.Callable[..., StateInputError], str], ...] = (
    (
        "compile-write",
        _compile_write_error,
        "working/manuscript/ exists",
    ),
    (
        "rule-pack-read",
        _rule_pack_read_error,
        "omit --pack to use the shipped default pack",
    ),
    (
        "device-ledger-read",
        _device_ledger_read_error,
        "check the --ledger path",
    ),
)

# ``_state_input_error`` reads both the path and the caught exception; the four
# path-only file-fault formatters now render from the path alone. The guard
# enumerates the two-argument formatters by identity so it threads ``exc`` only
# where the trimmed signatures still accept it.
_TWO_ARG_FORMATTERS: frozenset[cabc.Callable[..., StateInputError]] = frozenset(
    {_state_input_error},
)


def _render(
    formatter: cabc.Callable[..., StateInputError],
    path: pathlib.Path,
    exc: Exception,
) -> StateInputError:
    """Call ``formatter`` with the arity its trimmed signature accepts.

    Supplies ``exc`` only to the two-argument :func:`_state_input_error`; the four
    path-only formatters take the artefact path alone after audit:6.3.8.
    """
    if formatter in _TWO_ARG_FORMATTERS:
        return formatter(path, exc)
    return formatter(path)


@pytest.mark.parametrize(("label", "formatter"), _ALL_FORMATTERS)
@pytest.mark.parametrize("make_exc", _EXCEPTIONS)
def test_formatter_never_leaks_raw_os_text(
    label: str,
    formatter: cabc.Callable[..., StateInputError],
    make_exc: cabc.Callable[[pathlib.Path], Exception],
    faulty_path: pathlib.Path,
) -> None:
    """Every exit-3 formatter builds clean prose, never the caught exception repr.

    Drives one formatter with the faulty path and one representative caught
    exception, then asserts the rendered ``messages`` carry no ``Errno``, no
    ``str(exc)`` fragment, and no raw exception class name, and are non-empty.
    """
    exc = make_exc(faulty_path)
    error = _render(formatter, faulty_path, exc)
    assert isinstance(error, StateInputError), (
        f"the {label} formatter must return a StateInputError, "
        f"got {type(error).__name__}"
    )
    text = "\n".join(error.messages)

    assert text.strip(), f"the {label} formatter must emit non-empty prose"
    assert "Errno" not in text, f"the {label} formatter leaked an Errno: {text!r}"
    assert type(exc).__name__ not in text, (
        f"the {label} formatter leaked the exception class name: {text!r}"
    )
    # ``str(exc)`` is the raw repr the channel must never carry. Guard against the
    # whole repr leaking; a stray short token shared by chance is not the concern.
    raw = str(exc)
    assert raw, "the test fixture exception must have a non-empty repr"
    assert raw not in text, f"the {label} formatter re-interpolated str(exc): {text!r}"


@pytest.mark.parametrize(("label", "formatter"), _PATH_NAMING_FORMATTERS)
@pytest.mark.parametrize("make_exc", _EXCEPTIONS)
def test_file_fault_formatter_names_the_artefact_path(
    label: str,
    formatter: cabc.Callable[..., StateInputError],
    make_exc: cabc.Callable[[pathlib.Path], Exception],
    faulty_path: pathlib.Path,
) -> None:
    """Every file/write-fault formatter names the offending artefact path.

    The actionability contract requires the operator to see *which* artefact
    faulted, so each file/write-fault formatter must interpolate the path it was
    handed into its ``messages``.
    """
    error = _render(formatter, faulty_path, make_exc(faulty_path))
    text = "\n".join(error.messages)
    assert str(faulty_path) in text, (
        f"the {label} formatter must name the artefact path: {text!r}"
    )


@pytest.mark.parametrize(
    "arm", _REMEDY_TOKENS, ids=[label for label, _, _ in _REMEDY_TOKENS]
)
@pytest.mark.parametrize("make_exc", _EXCEPTIONS)
def test_file_fault_formatter_carries_its_remedy(
    arm: tuple[str, cabc.Callable[..., StateInputError], str],
    make_exc: cabc.Callable[[pathlib.Path], Exception],
    faulty_path: pathlib.Path,
) -> None:
    """Each §6.3.8 file-fault arm carries its actionable remedy clause.

    The no-leak and path-naming guards pin what the message omits and that it
    names the artefact, but not the remedy that makes it actionable; without this
    guard a regression dropping the remedy clause would still pass. Asserts the
    arm's stable remedy substring survives in the rendered ``messages``
    (audit:6.3.8 Finding 6).
    """
    label, formatter, remedy = arm
    error = _render(formatter, faulty_path, make_exc(faulty_path))
    text = "\n".join(error.messages)
    assert remedy in text, (
        f"the {label} formatter must carry its remedy clause {remedy!r}: {text!r}"
    )
