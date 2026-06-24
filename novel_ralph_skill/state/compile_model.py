"""The §4.3/§9 draft-concatenation model the disk-evidence detector shares.

The ``compiled-matches-drafts`` disk-evidence invariant (roadmap task 2.3.2)
decides whether ``working/manuscript/compiled.md`` is the ordered concatenation
of the present chapter drafts. It needs only the *divergence verdict*: the full
compile-and-hash command is roadmap task 4.1.1's. This module owns the one join
rule that verdict recomputes — the ordered draft bodies joined by a single fixed
separator (design §4.3 "consistent separators"; §9 lines 705-711).

:func:`concatenate_drafts` is the production twin of the corpus helper
``tests/working_corpus/_specs.py::concatenate_drafts``. The two are deliberate
twins (developers' guide twin policy): production must agree with the corpus
byte-for-byte, pinned by a test (``test_disk_evidence.py``), but neither imports
the other. The separator constant is the single source of truth on the
production side; the corpus keeps its own copy on purpose so a drift is a
finding, not a silent alignment.
"""

from __future__ import annotations

import typing as typ

if typ.TYPE_CHECKING:
    import collections.abc as cabc

# The single separator the ordered draft bodies are joined with when recomputing
# the expected ``compiled.md``. The design names "consistent separators" (§4.3)
# but pins no exact bytes, so this module owns the production copy; the corpus's
# ``CORPUS_SEPARATOR`` is its independent twin (pinned equal by test).
DRAFT_SEPARATOR = "\n\n"


def concatenate_drafts(drafts: cabc.Sequence[str]) -> str:
    """Return the ordered concatenation of ``drafts`` joined by the separator.

    This is the production stand-in for the §4.3 compile routine (the ordered
    concatenation of the present drafts with consistent separators) that roadmap
    task 4.1.1 implements in full. The disk-evidence detector uses it to recompute
    the expected ``compiled.md`` for the content-divergence verdict, comparing the
    result byte-for-byte against the on-disk ``compiled.md`` (§4.3 lines 320-344;
    §9 lines 705-711).

    Parameters
    ----------
    drafts : collections.abc.Sequence[str]
        The present chapter draft bodies, already in ascending chapter order.

    Returns
    -------
    str
        The ordered concatenation joined by :data:`DRAFT_SEPARATOR`.
    """
    return DRAFT_SEPARATOR.join(drafts)
