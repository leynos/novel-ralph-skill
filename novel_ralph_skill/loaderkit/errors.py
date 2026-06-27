"""The shared two-class failure shape every loader family binds (design §6).

The rule-pack loader (:mod:`novel_ralph_skill.rulepack.errors`) and the
device-ledger loader (:mod:`novel_ralph_skill.ledger.errors`) split a load
failure onto the same two exit codes (design §4.4, §3.2, §10): a *content* fault
(exit ``2``, naming an offending entity) and a *file* fault (exit ``3``, an
absent, unreadable, or undecodable file). Each loader formerly spelt out its own
near-identical pair of
:class:`~novel_ralph_skill.contract.errors.EnvelopeMessagesError` subclasses,
differing only in the id keyword (``rule_id`` versus ``device_id``), the
human-facing noun, and the class name. Roadmap task 7.2.5 lifts that shared shape
here so a third pack family (design §8.1's per-novel packs) *binds* one base each
rather than hand-copying a third pair.

The shape is delivered as two base classes the per-family concrete errors
subclass (Decision D-BASE-MIXIN in ``docs/execplans/roadmap-7-2-5.md``), not a
runtime ``type(...)`` synthesiser: the concrete classes stay literal ``class``
statements so ``interrogate`` (AST-based, 100% docstring coverage) sees their
docstrings and Sphinx ``:class:`` cross-references resolve to real, importable
names.

- :class:`PackError` — the exit-``2`` content base. Each family keeps a one-line
  ``__init__(self, *messages, <family>_id=None)`` that records its public id
  attribute and delegates the prose to this base, so the id keyword stays a
  per-package literal rather than a generic name.
- :class:`PackFileError` — the exit-``3`` file base: a bare
  :class:`~novel_ralph_skill.contract.errors.EnvelopeMessagesError` subclass each
  family inherits unchanged, so the file-error class is handed straight to
  :func:`~novel_ralph_skill.loaderkit.load.load_toml` as its
  ``file_error=`` callable (the ``Callable[[str], EnvelopeMessagesError]``
  contract).

This module depends only on the ``contract`` layer (for the
:class:`~novel_ralph_skill.contract.errors.EnvelopeMessagesError` base) and the
standard library. It imports neither ``rulepack`` nor ``ledger`` at runtime or
under ``TYPE_CHECKING``, so both may depend on it without an import cycle (design
§3.1, §6.3; ADR-003).
"""

from __future__ import annotations

from novel_ralph_skill.contract.errors import EnvelopeMessagesError


class PackError(EnvelopeMessagesError):
    """The shared exit-``2`` content-error base for every loader family.

    A *content* fault means a decoded pack is structurally valid but violates its
    schema; the command layer maps it to ``ExitCode.USAGE_ERROR`` (exit ``2``),
    naming the offending entity. This base supplies only the shared
    :class:`~novel_ralph_skill.contract.errors.EnvelopeMessagesError` storage of
    the human-prose ``messages``; it deliberately does **not** name an id keyword,
    because the keyword is public and per-family (``rule_id`` for
    :class:`~novel_ralph_skill.rulepack.errors.RulePackError`, ``device_id`` for
    :class:`~novel_ralph_skill.ledger.errors.LedgerError`). Each concrete subclass
    keeps a one-line ``__init__(self, *messages, <family>_id=None)`` that records
    its own public id attribute and calls ``super().__init__(*messages)`` to
    delegate the prose here, so the de-duplicated base behaviour lives once while
    the id name stays a literal at the leaf.
    """


class PackFileError(EnvelopeMessagesError):
    """The shared exit-``3`` file-error base: absent, unreadable, undecodable.

    A *file* fault means the pack file is missing, cannot be read, or holds TOML
    that ``tomllib`` cannot decode; the command layer maps it to
    ``ExitCode.STATE_ERROR`` (exit ``3``), kept distinct from a structurally valid
    file that violates the schema (a :class:`PackError`). This base adds nothing
    to :class:`~novel_ralph_skill.contract.errors.EnvelopeMessagesError`: a
    concrete file error inherits the bare ``__init__(self, *messages)`` shape so
    it is handed straight to
    :func:`~novel_ralph_skill.loaderkit.load.load_toml` as its ``file_error=``
    argument and called as ``file_error(msg)`` (the
    ``Callable[[str], EnvelopeMessagesError]`` contract). It is a distinct sibling
    of :class:`PackError`, never a subclass, so a content catch and a file catch
    stay separable.
    """
