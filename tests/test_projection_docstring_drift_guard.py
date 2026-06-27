"""Pin the §7.1 authoritative-docstring + consumer self-projection convention.

Roadmap §7.1 ("Single-source the model, payload, and contract projections")
gives every task the same definition of done: the surviving canonical projection
"is documented as the single source of truth, and a test pins it so it cannot
silently re-fork". Tasks 7.1.1-7.1.4 each extracted one canonical projection and
rerouted consumers through cross-referencing docstrings, but the
documentation-and-test legs of that invariant were themselves left
un-single-sourced (``docs/issues/audit-7.1.2.md`` Findings 2, 3, 5). This module
is that missing drift-guard: it pins, per consolidated projection, that the
*authoritative* docstring carries the full projection table while each *consumer*
docstring carries a resolving defining-module cross-reference and none of the
``state`` re-export spelling.

The guard follows the repository's established in-process prose-guard pattern
(``tests/test_developers_guide_contract_drift_guard.py``,
``tests/test_skill_contract_drift_guard.py``): it imports the relevant symbols
and reads their ``__doc__`` directly — no subprocess, no console-script harness,
no cuprum. The authoritative-versus-consumer distinction is keyed by REGISTRY
POSITION (the authoritative symbol is the row's key), never by counting member
names or scanning the prose for an "authority" token. That choice is forced by
the real tree (Decision Log "WI3 discriminator" in
``docs/execplans/roadmap-7-1-6.md``): ``check_compiled`` names all three
``CompiledComparison`` members and both absent-file polarities, and the phrases
"single production site"/"authoritative … table" appear inside *consumer*
docstrings as references to the canonical site, so neither a member-count nor a
token heuristic can tell authoritative from consumer. This mirrors how
``test_developers_guide_contract_drift_guard.py`` keys its field set off the
imported ``Envelope`` dataclass — by symbol identity, not parsed prose.

The table-marker assertion (compile family: ``MATCHES``/``ABSENT``/``DIVERGES``;
payload: the ``{action, discrepancies, detail}`` field shape) is asserted ONLY
of the authoritative symbol, never of consumers, because real consumers
legitimately name members (``check_compiled`` names all three,
``compile_is_current`` names all three, ``_check_compiled_matches_drafts`` names
two). A future maintainer must NOT "tighten" the table-marker check into a
consumer assertion: it would redden the green tree.

The "no bare re-export" check is the simple invariant "the re-export tail
substring count is zero in each consumer ``__doc__``", NOT a "preceded by" or
"counts equal" rule. The re-export tail (``state.compiled_matches_drafts``) is
NOT a substring of the canonical path
(``novel_ralph_skill.state.compile_model.compiled_matches_drafts`` contains
``state.compile_model.compiled_matches_drafts``), so on the green tree the tail
count is zero while the canonical count is at least one; a counts-equal
assertion would redden the passing tree (Decision Log "no-bare-re-export check
restated").

This is a closed, example-based registry of live symbols and their docstrings,
so ``python-verification`` selects NO adversary: there is no generated input
space and no contract to falsify, so neither Hypothesis, CrossHair, nor mutmut
applies — exactly as ``tests/test_compile_model_seam.py`` records for its closed
three-value enumeration.
"""

from __future__ import annotations

import dataclasses
import typing as typ

import pytest

from novel_ralph_skill.commands._compile import check_compiled
from novel_ralph_skill.commands.novel_state import _render_reconciliation
from novel_ralph_skill.contract.envelope import Envelope, render_machine
from novel_ralph_skill.state.compile_model import (
    compile_is_current,
    compiled_matches_drafts,
)
from novel_ralph_skill.state.disk_evidence import _check_compiled_matches_drafts
from novel_ralph_skill.state.done_predicate import compile_consistent
from novel_ralph_skill.state.reconcile import reconciliation_payload

# The two envelope field-order oracles are imported under non-``test_`` aliases so
# pytest does not re-collect them as tests of this module; they enter the registry
# only as consumer symbols whose docstrings the guard reads.
from tests.cross_command_contract.test_envelope_shape import (
    test_envelope_key_order_is_the_canonical_constant as _envelope_key_order_oracle,
)
from tests.test_contract_envelope import (
    test_envelope_field_order_matches_expected as _envelope_field_order_oracle,
)

if typ.TYPE_CHECKING:
    import collections.abc as cabc


@dataclasses.dataclass(frozen=True)
class ProjectionRow:
    """One consolidated §7.1 projection bound to its consumers.

    A row keys the *authoritative* symbol (which owns the full projection table)
    to the *consumer* symbols that cross-reference it. The authoritative-versus-
    consumer split is the registry shape — ``authoritative`` is the row key —
    never a parsed prose token.
    """

    name: str
    authoritative: object
    consumers: cabc.Sequence[object]
    canonical_path: str
    reexport_tail: str
    table_markers: cabc.Sequence[str]


def _doc(symbol: object) -> str:
    """Return ``symbol.__doc__``, failing loudly when it is missing.

    A symbol with no docstring cannot satisfy the single-authoritative-copy
    invariant, so an absent ``__doc__`` is a guard failure, not a skip.
    """
    doc = getattr(symbol, "__doc__", None)
    if not doc:
        message = f"{symbol!r} has no docstring"
        raise AssertionError(message)
    return doc


def assert_single_authoritative_projection(row: ProjectionRow) -> None:
    """Assert ``row`` keeps a single authoritative, cited copy.

    Three independent assertions, no member-count and no authority-token scan:

    1. (authoritative) every ``row.table_markers`` entry is present in
       ``row.authoritative.__doc__``. Asserted ONLY of the authoritative symbol,
       so a heterogeneous consumer that happens to name members never trips it
       (Decision Log R2-A2).
    2. (consumer cross-reference present) ``row.canonical_path`` is a substring of
       each consumer ``__doc__``. A bare relative ``:func:`name``` does NOT
       satisfy this (Decision Log R2-B1) — the canonical dotted path must appear.
    3. (consumer no bare re-export) ``row.reexport_tail`` does not appear in any
       consumer ``__doc__`` (substring count zero). Independent of assertion 2:
       the tail is not a substring of ``row.canonical_path``, so a green consumer
       carrying only the canonical path genuinely has zero tail occurrences
       (Decision Log R2-B2).
    """
    auth_doc = _doc(row.authoritative)
    missing = [marker for marker in row.table_markers if marker not in auth_doc]
    assert not missing, (
        f"authoritative {row.authoritative!r} docstring is missing table "
        f"marker(s) {missing!r}"
    )
    for consumer in row.consumers:
        consumer_doc = _doc(consumer)
        assert row.canonical_path in consumer_doc, (
            f"consumer {consumer!r} docstring lacks the defining-module "
            f"cross-reference {row.canonical_path!r}"
        )
        assert row.reexport_tail not in consumer_doc, (
            f"consumer {consumer!r} docstring carries the bare re-export tail "
            f"{row.reexport_tail!r}; use the defining-module path instead"
        )


_REGISTRY: tuple[ProjectionRow, ...] = (
    ProjectionRow(
        name="compiled_matches_drafts",
        authoritative=compiled_matches_drafts,
        consumers=(
            compile_is_current,
            compile_consistent,
            _check_compiled_matches_drafts,
            check_compiled,
        ),
        canonical_path=(
            "novel_ralph_skill.state.compile_model.compiled_matches_drafts"
        ),
        reexport_tail="state.compiled_matches_drafts",
        table_markers=("MATCHES", "ABSENT", "DIVERGES"),
    ),
    ProjectionRow(
        name="reconciliation_payload",
        authoritative=reconciliation_payload,
        consumers=(_render_reconciliation,),
        canonical_path=("novel_ralph_skill.state.reconcile.reconciliation_payload"),
        reexport_tail="state.reconciliation_payload",
        table_markers=("{action, discrepancies, detail}",),
    ),
    # The envelope field-order projection (roadmap 7.1.5). ``ENVELOPE_FIELD_ORDER``
    # is the consolidated constant, but it is a module-level tuple whose runtime
    # ``__doc__`` is the built-in tuple docstring, not its PEP 224 attribute
    # docstring; the guard reads ``symbol.__doc__``, so the authoritative table is
    # keyed off the :class:`Envelope` dataclass it is derived from — whose
    # docstring enumerates the six fields — exactly as
    # ``test_developers_guide_contract_drift_guard.py`` keys its field set off the
    # imported ``Envelope`` by symbol identity. The ``canonical_path`` is the
    # ``ENVELOPE_FIELD_ORDER`` dotted path the consumers cite, and ``reexport_tail``
    # is the ``contract``-package façade that bypasses the defining ``.envelope``
    # module; it is not a substring of ``canonical_path`` (no ``.envelope.``
    # segment), so the tail check is non-vacuous on the green tree.
    ProjectionRow(
        name="envelope_field_order",
        authoritative=Envelope,
        consumers=(
            render_machine,
            _envelope_field_order_oracle,
            _envelope_key_order_oracle,
        ),
        canonical_path="novel_ralph_skill.contract.envelope.ENVELOPE_FIELD_ORDER",
        reexport_tail="novel_ralph_skill.contract.ENVELOPE_FIELD_ORDER",
        table_markers=(
            "command",
            "schema_version",
            "ok",
            "working_dir",
            "result",
            "messages",
        ),
    ),
)


@pytest.mark.parametrize("row", _REGISTRY, ids=lambda row: row.name)
def test_projection_is_single_authoritative(row: ProjectionRow) -> None:
    """Each §7.1 projection keeps a single authoritative, cited copy.

    Pins, per consolidated projection, that the authoritative docstring carries
    the full projection table and every consumer carries the defining-module
    cross-reference with no bare re-export spelling. Re-expanding a consumer's
    cross-reference into the re-export path, breaking it, or hollowing the
    authoritative table reddens the matching row.
    """
    assert_single_authoritative_projection(row)


# Synthetic docstring fixtures for the unit assertions below. These are planted
# strings, never production docstrings; the compile-family canonical path and
# re-export tail are reused so the helper is exercised exactly as on the tree.
_CANON = "novel_ralph_skill.state.compile_model.compiled_matches_drafts"
_TAIL = "state.compiled_matches_drafts"
_REEXPORT_FULL = "novel_ralph_skill.state.compiled_matches_drafts"
_MARKERS = ("MATCHES", "ABSENT", "DIVERGES")


def _consumer(doc: str) -> object:
    """Wrap a planted docstring in an object the helper can read as a consumer."""

    def _fixture() -> None:
        pass

    _fixture.__doc__ = doc
    return _fixture


# A docstring that carries every table marker, so the authoritative-marker
# assertion never trips while the consumer assertions are exercised.
_AUTH_OK = _consumer(f"Owns the table: {' '.join(_MARKERS)} verdicts.")


def _row(
    *,
    authoritative: object = _AUTH_OK,
    consumers: tuple[object, ...] = (),
) -> ProjectionRow:
    """Build a planted compile-family ``ProjectionRow`` for a helper unit test."""
    return ProjectionRow(
        name="planted",
        authoritative=authoritative,
        consumers=consumers,
        canonical_path=_CANON,
        reexport_tail=_TAIL,
        table_markers=_MARKERS,
    )


class TestHelperRejectsDrift:
    """Pin the helper's discriminating power against planted drift shapes."""

    def test_omitted_cross_reference_raises(self) -> None:
        """A consumer naming no cross-reference reds on assertion 2."""
        consumer = _consumer("Mentions the verdict but cites no defining module.")
        with pytest.raises(AssertionError, match="defining-module cross-reference"):
            assert_single_authoritative_projection(_row(consumers=(consumer,)))

    def test_bare_reexport_only_raises_on_cross_reference(self) -> None:
        """A consumer naming ONLY the bare re-export full path reds on assertion 2.

        ``novel_ralph_skill.state.compiled_matches_drafts`` lacks the
        ``.compile_model.`` segment, so it does NOT contain the canonical
        substring; the helper reds on "cross-reference present", proving a bare
        re-export full path is NOT an acceptable cross-reference. This is the
        SEPARATE "cross-reference absent" case, distinct from the tail-branch
        proof below (Decision Log "tail-isolating fixture co-locates both
        spellings").
        """
        assert _CANON not in _REEXPORT_FULL  # the canonical segment is absent
        consumer = _consumer(f"See {_REEXPORT_FULL} for the table.")
        with pytest.raises(AssertionError, match="defining-module cross-reference"):
            assert_single_authoritative_projection(_row(consumers=(consumer,)))

    def test_colocated_canonical_and_tail_raises_on_tail(self) -> None:
        """A co-located canonical+tail consumer reds on assertion 3 (B3-1).

        The fixture names BOTH the canonical path and the bare re-export tail
        simultaneously, so assertion 2 (cross-reference present) is satisfied by
        the canonical substring and the ONLY branch that can red is assertion 3
        (no bare re-export tail). This proves the tail check fires and is
        non-vacuous — a bare-re-export-only fixture would red on assertion 2 and
        never reach the tail branch.
        """
        doc = f"See :func:`~{_CANON}` (re-exported as {_REEXPORT_FULL})."
        # Both spellings are co-located so assertion 2 passes and only
        # assertion 3 (the tail branch) can red.
        assert _CANON in doc
        assert _TAIL in doc
        consumer = _consumer(doc)
        with pytest.raises(AssertionError, match="bare re-export tail"):
            assert_single_authoritative_projection(_row(consumers=(consumer,)))

    def test_bare_relative_reference_raises_on_cross_reference(self) -> None:
        """A consumer whose only reference is the bare relative role reds on 2.

        Mirrors ``compile_is_current``'s *pre-normalisation* shape: a bare
        relative ``:func:`compiled_matches_drafts``` carries no dotted path, so
        the canonical substring is absent and the helper reds on assertion 2.
        Pins that an intra-module relative reference is NOT an acceptable
        cross-reference (Decision Log R2-B1).
        """
        consumer = _consumer("See :func:`compiled_matches_drafts` for the table.")
        with pytest.raises(AssertionError, match="defining-module cross-reference"):
            assert_single_authoritative_projection(_row(consumers=(consumer,)))

    def test_hollowed_authoritative_raises(self) -> None:
        """An authoritative docstring stripped of its table markers reds on 1."""
        hollow = _consumer("The verdict; see the consumers for the polarities.")
        with pytest.raises(AssertionError, match="table marker"):
            assert_single_authoritative_projection(_row(authoritative=hollow))


class TestHelperAcceptsLegitimateConsumers:
    """Prove the helper does NOT false-positive on real consumer shapes."""

    def test_canonical_only_consumer_passes(self) -> None:
        """A consumer carrying only the canonical path passes (tail-isolation half).

        The positive half of the tail-isolation pair: a green consumer genuinely
        has zero re-export-tail occurrences, so the helper must accept it.
        """
        consumer = _consumer(f"See :func:`~{_CANON}` for the table.")
        assert_single_authoritative_projection(_row(consumers=(consumer,)))

    def test_check_compiled_shaped_consumer_passes(self) -> None:
        """A three-member consumer with a correct cross-reference passes (anti-B2).

        Built from ``check_compiled``'s real docstring shape — it names all three
        members and both absent-file polarities AND carries the defining-module
        cross-reference. A legitimate three-member consumer must NOT red; this is
        the regression-proof against the member-count heuristic the round-1
        review rejected.
        """
        doc = (
            "Only MATCHES is current; both ABSENT and DIVERGES are actionable "
            "findings, inverting the §5.4 detector's absent-file polarity. See "
            f":func:`~{_CANON}` for the authoritative three-valued table."
        )
        consumer = _consumer(doc)
        assert_single_authoritative_projection(_row(consumers=(consumer,)))
