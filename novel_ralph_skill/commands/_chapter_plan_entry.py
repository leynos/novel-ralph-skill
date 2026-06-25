"""The ``set-chapters`` CLI input shape, in a dependency-free leaf module.

:class:`ChapterPlanEntry` is the Cyclopts input dataclass for ``set-chapters``
(roadmap task 2.2.3). It lives in its own leaf module — importing nothing from the
``commands`` or ``state`` packages — so both the command builder
(:mod:`novel_ralph_skill.commands.novel_state`) and the mutator body
(:mod:`novel_ralph_skill.commands._set_chapters`) can import it as a *runtime*
module global without the circular import the ``_set_chapters`` ->
``_state_mutators`` -> ``novel_state`` chain would otherwise create. Cyclopts must
resolve the ``list[ChapterPlanEntry]`` annotation against the command function's
``__globals__`` (``get_type_hints``), which is why the name has to be a real
import in ``novel_state`` rather than a deferred or type-checking-only one.
"""

from __future__ import annotations

import dataclasses


@dataclasses.dataclass(frozen=True, kw_only=True, slots=True)
class ChapterPlanEntry:
    """One chapter the agent plans: the CLI input shape for ``set-chapters``.

    This is the *input* shape, distinct from
    :class:`novel_ralph_skill.state.schema.ChapterEntry` (the on-disk shape): they
    share fields but serve different layers, so they are not conflated. It is a
    frozen, slotted, keyword-only domain shape (python-data-shapes), and it must
    **not** be union'd with ``str`` so Cyclopts parses a ``list[ChapterPlanEntry]``
    keyword from a JSON array (ExecPlan Surprise S1).

    Attributes
    ----------
    number : int
        The one-based chapter number; the manifest is ordered ascending by it.
    slug : str
        The filesystem-safe chapter identifier.
    title : str
        The chapter title.
    target_words : int
        The planned word count for the chapter.
    """

    number: int
    slug: str
    title: str
    target_words: int
