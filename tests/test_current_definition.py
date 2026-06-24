"""Pin the authoritative ``current`` definition (roadmap task 2.3.5).

``[word_counts].current`` is the **drafted sum** ``sum(by_chapter.values())``,
where each ``by_chapter[NN]`` is ``len(draft_text.split())`` for
``chapter-NN/draft.md``. The compiled token count is never a ``current`` source.
This module guards that rule as a cross-command regression so a future refactor
cannot silently reintroduce a compiled-token ``current`` in either ``recount`` or
the ``reconcile`` RECOUNT path:

- ``recount`` writes the drafted-sum ``current`` irrespective of ``compiled.md``
  (it never reads the compiled artefact), even when ``compiled.md`` is a
  bytes-divergent file whose token count genuinely differs from the drafted sum;
- the ``reconcile`` RECOUNT path writes the identical drafted-sum ``current``,
  equal to a single ``recount_words(...)[0]`` oracle, so the two commands cannot
  disagree;
- a bytes-divergent ``compiled.md`` — the only tree whose compiled token count
  can differ from the drafted sum (the blank-line separator and any whitespace
  never change ``str.split()`` token counts; ExecPlan D-TOKEN-EQUALITY) — is
  surfaced by ``check`` as the ``compiled-matches-drafts`` finding (exit ``4``)
  with ``current`` left byte-for-byte untouched, never redefined.

The corpus/``WorkingTreeSpec`` builders are taken by the sanctioned
``working_corpus as wc`` value import (ADR-002: ``state.toml`` is serialised
through ``tomlkit`` by the builder, never hand-written here). Every command call
is preceded by ``monkeypatch.chdir`` into the materialised tree's parent because
the mutators resolve a cwd-relative ``working/state.toml`` (D-CWD).
"""

from __future__ import annotations

import contextlib
import io
import json
import typing as typ

import pytest
import working_corpus as wc

from novel_ralph_skill.commands._reconcile import reconcile
from novel_ralph_skill.commands._recount import recount
from novel_ralph_skill.commands.novel_state import build_app
from novel_ralph_skill.contract.exit_codes import ExitCode
from novel_ralph_skill.contract.runner import RunContext, run
from novel_ralph_skill.state import (
    COMPILED_MATCHES_DRAFTS,
    load_state,
    recount_words,
)

if typ.TYPE_CHECKING:
    from pathlib import Path

_COMMAND = "novel-state"
_TARGET_WORDS = 80000
# The completed phase prefix for a coherent ``drafting``-phase tree.
_DRAFTING_PREFIX = wc.PHASE_ORDER[:8]


def _drafted_sum(working: Path) -> int:
    """Return the drafted sum ``recount_words(...)[0]`` over the tree's manifest.

    This is the one counting rule the whole task pins ``current`` to; it reads
    only the chapter drafts and never ``compiled.md``.
    """
    manifest = load_state(working / "state.toml").chapters
    total, _by_chapter = recount_words(working, manifest)
    return total


def _compiled_token_count(working: Path) -> int:
    """Return ``len(compiled.md.split())`` for the tree's compiled artefact."""
    compiled = working / "manuscript" / "compiled.md"
    return len(compiled.read_text(encoding="utf-8").split())


def _chapter(number: int, draft_words: int) -> wc.ChapterSpec:
    """Return a minimal coherent :class:`ChapterSpec` drafting ``draft_words``."""
    return wc.ChapterSpec(
        number=number,
        slug=f"chapter-{number:02d}",
        title=f"Chapter {number}",
        target_words=20000,
        draft_words=draft_words,
        has_done_flag=False,
        write_draft=True,
    )


def _stale_tree_with_divergent_compiled(tmp_path: Path) -> wc.WorkingTreeSpec:
    """Return a stale-table spec carrying a bytes-divergent ``compiled.md``.

    The two chapters draft three and five words on disk, but the hand-typed
    ``[word_counts]`` records a deliberately wrong total so ``recount`` has
    something to correct. ``compiled.md`` holds injected **non-whitespace**
    content unrelated to the drafts, so its token count genuinely differs from the
    drafted sum (eight) — the divergence is realised by non-whitespace content,
    not by the separator or whitespace (D-TOKEN-EQUALITY).
    """
    return wc.WorkingTreeSpec(
        phase_current="drafting",
        phase_completed=_DRAFTING_PREFIX,
        chapters=(_chapter(1, 3), _chapter(2, 5)),
        target_words=_TARGET_WORDS,
        consecutive_clean=0,
        convergence_target=1,
        current_chapter=2,
        by_chapter_override={"01": 999, "02": 999},
        current_words_override=1998,
        compiled="injected words not in the drafts",
    )


def test_recount_writes_drafted_sum_irrespective_of_compiled(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``recount`` writes the drafted sum, ignoring a bytes-divergent ``compiled.md``.

    ``recount`` never reads ``compiled.md`` and never runs the disk-evidence
    detector, so even a divergent compile (which would REFUSE under
    ``check``/``reconcile``) does not perturb the recount: it writes
    ``sum(by_chapter)`` and not the compiled token count.
    """
    working = wc.build_working_tree(
        _stale_tree_with_divergent_compiled(tmp_path), tmp_path
    )
    drafted_sum = _drafted_sum(working)
    compiled_tokens = _compiled_token_count(working)
    # Arrange-time precondition: the compiled token count genuinely differs from
    # the drafted sum because ``compiled.md`` carries injected non-whitespace
    # content — not because of the separator or whitespace.
    assert compiled_tokens != drafted_sum, (
        "the divergent compile must have a token count unequal to the drafted sum"
    )

    monkeypatch.chdir(working.parent)
    outcome = recount()

    assert outcome.code == ExitCode.SUCCESS
    written = load_state(working / "state.toml").word_counts.current
    assert written == drafted_sum, "recount must write the drafted sum"
    assert written != compiled_tokens, "recount must not write the compiled token count"


def test_reconcile_recount_writes_same_current_as_recount(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The ``reconcile`` RECOUNT path writes the same drafted-sum ``current``.

    The ``done-flag-real-draft-undercount`` tree has a stale ``by_chapter``
    (firing ``word-counts-match-drafts``) and a coherent-or-absent ``compiled.md``
    (so ``compiled-matches-drafts`` does not REFUSE). ``reconcile`` therefore takes
    the RECOUNT path; the written ``current`` must equal the single
    ``recount_words(...)[0]`` oracle — the same value ``recount`` writes. This
    asserts recount==reconcile agreement only; it makes no compiled-token claim
    (there is no divergent compiled token count on this tree).
    """
    spec, _expected = wc.INCOHERENT_VARIANTS["done-flag-real-draft-undercount"]
    working = wc.build_working_tree(spec, tmp_path)
    drafted_sum = _drafted_sum(working)

    monkeypatch.chdir(working.parent)
    outcome = reconcile()

    assert outcome.code == ExitCode.SUCCESS
    written = load_state(working / "state.toml").word_counts.current
    assert written == drafted_sum, (
        "the reconcile RECOUNT path must write the drafted-sum current, equal to "
        "the recount_words oracle (recount==reconcile agreement)"
    )


def test_compiled_divergence_is_a_finding_not_a_current_source(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A bytes-divergent ``compiled.md`` is the finding, not a ``current`` source.

    The ``compiled-not-concatenation-of-drafts`` tree is the only one whose
    ``compiled.md`` token count diverges from the drafted sum (injected
    non-whitespace tokens). ``check`` reports ``compiled-matches-drafts`` and exits
    ``4`` while writing nothing, so ``state.toml``'s ``current`` is byte-for-byte
    unchanged; the drafted sum differs from the compiled token count here, proving
    the "not the compiled token count" property on the one tree where a divergent
    compiled token count actually exists.
    """
    spec, expected = wc.INCOHERENT_VARIANTS["compiled-not-concatenation-of-drafts"]
    assert expected == COMPILED_MATCHES_DRAFTS, (
        "the case-3 variant must surface the compiled-matches-drafts finding"
    )
    working = wc.build_working_tree(spec, tmp_path)
    drafted_sum = _drafted_sum(working)
    compiled_tokens = _compiled_token_count(working)
    assert drafted_sum != compiled_tokens, (
        "this tree's compiled token count must genuinely differ from the drafted "
        "sum (injected non-whitespace content)"
    )

    state_path = working / "state.toml"
    before = state_path.read_bytes()

    monkeypatch.chdir(working.parent)
    stream = io.StringIO()
    with contextlib.redirect_stdout(stream), pytest.raises(SystemExit) as excinfo:
        run(
            build_app(),
            ["check"],
            RunContext(command=_COMMAND, working_dir="working", human=False),
        )

    assert excinfo.value.code == ExitCode.ACTIONABLE_FINDING
    result = typ.cast("dict[str, object]", json.loads(stream.getvalue())["result"])
    assert COMPILED_MATCHES_DRAFTS in typ.cast("list[str]", result["violations"])
    assert state_path.read_bytes() == before, (
        "check must write nothing, leaving current byte-for-byte untouched"
    )
