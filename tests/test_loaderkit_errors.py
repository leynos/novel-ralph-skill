"""Unit tests for the shared ``loaderkit`` error-hierarchy bases (roadmap 7.2.5).

These pin the two-class failure shape both loader families share:
:class:`~novel_ralph_skill.loaderkit.errors.PackError` (the exit-``2`` content
base carrying an optional offending-entity id) and
:class:`~novel_ralph_skill.loaderkit.errors.PackFileError` (the exit-``3``
file base carrying only ``messages``). The roadmap success criterion is that a
*third* pack family inherits these primitives rather than cloning a third copy,
so the tests construct test-local subclasses with an arbitrary id keyword
(``sample_id``) — proving the bases support a per-family id name of any spelling
without naming ``rule_id``/``device_id`` here.

The idiom mirrors :mod:`tests.test_loaderkit_coerce`: a test-local
:class:`~novel_ralph_skill.contract.errors.EnvelopeMessagesError` subclass
stands in for a real pack channel, so the bases are pinned without depending on
the rule-pack or ledger error modules.
"""

from __future__ import annotations

import ast
import pathlib

import pytest

from novel_ralph_skill.contract.errors import EnvelopeMessagesError
from novel_ralph_skill.loaderkit import errors as errors_module
from novel_ralph_skill.loaderkit.errors import PackError, PackFileError


class _SampleError(PackError):
    """A test-local content error recording an arbitrary per-family id."""

    def __init__(self, *messages: str, sample_id: str | None = None) -> None:
        """Record the messages and the offending ``sample_id`` for assertions."""
        super().__init__(*messages)
        self.sample_id: str | None = sample_id


class _SampleFileError(PackFileError):
    """A test-local file error proving the bare ``*messages`` shape inherits."""


def test_pack_error_subclass_records_id_and_messages() -> None:
    """A :class:`PackError` subclass stores its own id keyword and the messages.

    Pins the third-family contract: the base supports a per-family id keyword of
    arbitrary name (``sample_id`` here), so a third pack binds its own
    ``<family>_id`` without the base hard-coding ``rule_id``/``device_id``.
    """
    error = _SampleError("first note", "second note", sample_id="alpha")
    assert error.sample_id == "alpha"
    assert error.messages == ("first note", "second note")


def test_pack_error_subclass_defaults_id_to_none() -> None:
    """A :class:`PackError` subclass leaves its id ``None`` when none is passed."""
    error = _SampleError("note")
    assert error.sample_id is None
    assert error.messages == ("note",)


def test_pack_file_error_is_one_arg_callable() -> None:
    """:class:`PackFileError` satisfies the ``load_toml`` ``file_error`` contract.

    ``load_toml`` calls its ``file_error`` argument as ``file_error(msg)`` (a
    one-arg call typed ``Callable[[str], EnvelopeMessagesError]``), so a
    :class:`PackFileError` subclass must construct from a single message and
    record it on ``.messages``.
    """
    file_error: object = _SampleFileError
    assert callable(file_error)
    error = _SampleFileError("missing file")
    assert isinstance(error, EnvelopeMessagesError)
    assert error.messages == ("missing file",)


def test_bases_subclass_envelope_messages_error() -> None:
    """Both bases subclass :class:`EnvelopeMessagesError` for the envelope prose."""
    assert issubclass(PackError, EnvelopeMessagesError)
    assert issubclass(PackFileError, EnvelopeMessagesError)


def test_bases_reject_family_id_keyword() -> None:
    """The bases name no id keyword; the per-family keyword lives at the leaf.

    :class:`PackError` and :class:`PackFileError` inherit the bare
    ``__init__(self, *messages)`` from
    :class:`~novel_ralph_skill.contract.errors.EnvelopeMessagesError`, so passing
    a family-specific ``sample_id`` to a *base* is a ``TypeError``. The keyword is
    introduced only by a concrete subclass (proven by :class:`_SampleError`), so
    the base cannot silently absorb an arbitrary id name.
    """
    with pytest.raises(TypeError, match="sample_id"):
        PackError("note", sample_id="alpha")  # ty: ignore[unknown-argument]
    with pytest.raises(TypeError, match="sample_id"):
        PackFileError("note", sample_id="alpha")  # ty: ignore[unknown-argument]


def test_content_and_file_bases_are_distinct() -> None:
    """:class:`PackError` and :class:`PackFileError` are unrelated siblings.

    Neither base subclasses the other, so a content catch (``except PackError``)
    and a file catch (``except PackFileError``) stay separable — the exit-``2``
    and exit-``3`` channels never collapse into one.
    """
    assert not issubclass(PackError, PackFileError)
    assert not issubclass(PackFileError, PackError)


def test_errors_module_imports_no_pack_domain() -> None:
    """``loaderkit.errors`` imports nothing from a pack domain (neutral leaf).

    A focused belt-and-braces pin of the neutral-leaf invariant (design §6/§6.3,
    ADR-003) for the new module, complementing the package-wide glob guard in
    :mod:`tests.test_loaderkit_scan`: the error bases must depend only on
    ``contract`` and the standard library, so both packs can subclass them
    without an import cycle.
    """
    source = pathlib.Path(errors_module.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            imported.append(node.module)
        elif isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
    banned = ("novel_ralph_skill.rulepack", "novel_ralph_skill.ledger")
    assert not [module for module in imported if module.startswith(banned)]
