"""Lossless ``tomlkit`` round-trip writer for ``state.toml`` (design §5.3).

This module is the write half of the ``state`` slice: it reads ``state.toml``
into a style-preserving :class:`~tomlkit.TOMLDocument`, lets a caller mutate it
in place, and writes it back through ``tomlkit`` so the file's hand-authored
comments and deliberate layout survive every turn (ADR-002; design §5.3). It is
the seam every later mutator (``init``, ``set-cursor``, ``advance-phase``,
``recount``, ``reconcile``) calls; it has no CLI of its own.

The writer holds the live :class:`~tomlkit.TOMLDocument` as the source of truth
for bytes. :func:`document_to_state` exposes the typed
:class:`~novel_ralph_skill.state.schema.State` only as a *read* view (via
:func:`~novel_ralph_skill.state.parse.parse_state`), never as the write source —
re-serializing from the lossy typed model would defeat ADR-002 (design Decision
Log).

Three disciplines live here, each delegated to a section below:

- **Lossless round-trip.** :func:`load_document` reads bytes into a ``tomlkit``
  document; a no-op write is byte-for-byte stable and a surgical value edit
  rewrites only the touched bytes (ADR-002 Functional req 1-2).
- **Atomic write.** :func:`write_document_atomically` writes a temporary file in
  the target's directory and renames it over the target with ``Path.replace``,
  so a crash before the rename leaves the prior coherent file intact (design §3.4;
  ``docs/scripting-standards.md``).
- **``[pending_turn]`` bracket.** :func:`pending_turn` opens an intent record
  before a multi-file turn touches any other file and clears it on clean exit,
  turning a torn turn into a declared, inspectable state (design §3.4). This
  task owns only the *producer* side; the §5.4 rollback path is ``reconcile``'s
  job (roadmap task 2.3.2).

This module is mechanical (ADR-001; design §1): it moves bytes and structure and
enforces no §5.2 invariant — that is the ``check`` validator (roadmap task
2.1.2).
"""

from __future__ import annotations

import contextlib
import tempfile
import typing as typ
from pathlib import Path

import tomlkit
import tomlkit.items
from tomlkit import TOMLDocument

from novel_ralph_skill.state.parse import parse_state

if typ.TYPE_CHECKING:
    import collections.abc as cabc

    from novel_ralph_skill.state.schema import State

# Prefix for the in-directory temporary file the atomic write creates, so a
# leaked temp file from a failed write is recognisable and assertable (Risk
# "atomic temp file leaks").
_TEMP_PREFIX = ".state.toml."

# The ``[pending_turn]`` table key, named once so the open/clear pair and the
# schema parser key on the same literal (matches ``PendingTurn`` in schema.py).
_PENDING_TURN_KEY = "pending_turn"


def load_document(path: Path) -> TOMLDocument:
    r"""Read ``state.toml`` into a style-preserving ``tomlkit`` document.

    The returned document preserves comments and layout, so a later no-op write
    round-trips byte-for-byte (design §5.3; ADR-002 Functional req 1).

    Parameters
    ----------
    path : pathlib.Path
        The path to a ``state.toml`` file.

    Returns
    -------
    tomlkit.TOMLDocument
        The parsed, style-preserving document.

    Examples
    --------
    >>> from pathlib import Path
    >>> import tempfile, tomlkit
    >>> with tempfile.TemporaryDirectory() as directory:
    ...     state = Path(directory) / "state.toml"
    ...     _ = state.write_text("# kept\nschema_version = 1\n", encoding="utf-8")
    ...     document = load_document(state)
    ...     tomlkit.dumps(document) == "# kept\nschema_version = 1\n"
    True
    """
    return tomlkit.parse(path.read_text(encoding="utf-8"))


def document_to_state(document: TOMLDocument) -> State:
    """Return the typed :class:`State` read view of ``document``.

    Delegates to :func:`novel_ralph_skill.state.parse.parse_state` over the
    document's plain mapping. This is a *read* view only; the document remains
    the source of truth for the bytes written back (design Decision Log).

    Parameters
    ----------
    document : tomlkit.TOMLDocument
        A ``state.toml`` document, typically from :func:`load_document`.

    Returns
    -------
    State
        The fully typed, frozen state object.
    """
    return parse_state(document)


def write_text_atomically(text: str, path: Path) -> None:
    """Write ``text`` to ``path`` atomically (design §3.4).

    Writes ``text`` to a temporary file in ``path.parent`` then renames it over
    ``path`` with ``Path.replace``, so on POSIX a reader sees either the whole
    old file or the whole new file, never a torn half. On any failure before the
    replace the temporary file is unlinked, so no stray temp file survives.

    This is the single home of the temp-file/rename/unlink discipline (design
    §3.4; ``docs/scripting-standards.md``): :func:`write_document_atomically`
    delegates to it after serialising its ``tomlkit`` document, and the
    ``novel-compile`` write path (roadmap task 4.1.1) uses it directly for the
    pre-rendered ``compiled.md`` string.

    Parameters
    ----------
    text : str
        The pre-rendered text to write.
    path : pathlib.Path
        The target file path. Its parent must already exist.
    """
    # The temp file shares the target's directory so the rename stays on one
    # filesystem and is atomic on POSIX (design §3.4; scripting-standards). It is
    # created with ``delete=False`` because the handle is closed before the
    # rename; on any failure before the rename the temp file is unlinked so no
    # stray file survives (Risk "atomic temp file leaks").
    with tempfile.NamedTemporaryFile(
        "w",
        delete=False,
        dir=path.parent,
        prefix=_TEMP_PREFIX,
        suffix=".tmp",
        encoding="utf-8",
    ) as handle:
        temp_path = Path(handle.name)
        handle.write(text)
    try:
        temp_path.replace(path)
    except OSError:
        # Clean up the temp file before propagating, so a failed write leaves
        # only the prior coherent target file and no orphaned temp file.
        temp_path.unlink(missing_ok=True)
        raise


def write_document_atomically(document: TOMLDocument, path: Path) -> None:
    """Serialize ``document`` to ``path`` atomically (design §3.4).

    Serialises ``tomlkit.dumps(document)`` and delegates to
    :func:`write_text_atomically`, so the temp-file-plus-``Path.replace``
    discipline lives in exactly one place (ExecPlan Decision Log D-WRITER). A
    reader sees either the whole old file or the whole new file, never a torn
    half; on any failure before the replace the temporary file is unlinked, so
    no stray temp file survives.

    Parameters
    ----------
    document : tomlkit.TOMLDocument
        The document to serialize.
    path : pathlib.Path
        The target ``state.toml`` path. Its parent must already exist.
    """
    write_text_atomically(tomlkit.dumps(document), path)


def build_inline_table(pairs: cabc.Mapping[str, object]) -> tomlkit.items.InlineTable:
    """Return a fresh ``tomlkit`` inline table populated from ``pairs``.

    This is the single home of the inline-table materialisation idiom the
    ``state`` slice re-derives ``[word_counts].by_chapter``,
    ``[drafting.critic].last_finding_counts``, and the ``[[chapters]]`` entries
    from (design §5.3; ADR-002; roadmap task 7.2.1). It builds an empty inline
    table and updates it with ``pairs`` **in the mapping's iteration order**, so
    a caller that hands an order-stable mapping gets an order-stable
    table — the property ``recount`` relies on for a byte-for-byte deterministic
    write (``_recount`` docstring; design §5.2 invariant 3). The returned table
    does not alias ``pairs``: ``tomlkit`` copies the values in, so a later
    mutation of ``pairs`` does not change the table.

    Parameters
    ----------
    pairs : collections.abc.Mapping[str, object]
        The key-value pairs to materialise, in iteration order. Values may be of
        mixed type (e.g. the ``[[chapters]]`` entry's ``int`` and ``str``
        values); the widest read-only ``Mapping`` covers every call site.

    Returns
    -------
    tomlkit.items.InlineTable
        The populated inline table, ready to assign into a document.
    """
    table = tomlkit.inline_table()
    table.update(pairs)
    return table


def open_pending_turn(
    document: TOMLDocument, *, operation: str, paths: cabc.Sequence[str]
) -> None:
    """Add a ``[pending_turn]`` intent record to ``document`` in place.

    Parameters
    ----------
    document : tomlkit.TOMLDocument
        The document to mutate in place.
    operation : str
        The operation in flight (``[pending_turn].operation``).
    paths : collections.abc.Sequence[str]
        The paths the operation will write (``[pending_turn].paths``).

    Notes
    -----
    The keys match :class:`~novel_ralph_skill.state.schema.PendingTurn`, so
    :func:`~novel_ralph_skill.state.parse.parse_state` reads the record back.
    ``paths`` is copied into a fresh ``tomlkit`` array so the document does not
    alias the caller's sequence.
    """
    record = tomlkit.table()
    record["operation"] = operation
    record["paths"] = tomlkit.array().multiline(multiline=False)
    record["paths"].extend(paths)
    document[_PENDING_TURN_KEY] = record


def clear_pending_turn(document: TOMLDocument) -> None:
    """Remove the ``[pending_turn]`` record from ``document`` in place.

    Idempotent: clearing a document that carries no ``[pending_turn]`` is a
    no-op, so a clean exit and a recovery path may both call it safely.

    Parameters
    ----------
    document : tomlkit.TOMLDocument
        The document to mutate in place.
    """
    if _PENDING_TURN_KEY in document:
        del document[_PENDING_TURN_KEY]


@contextlib.contextmanager
def pending_turn(
    path: Path, *, operation: str, paths: cabc.Sequence[str]
) -> cabc.Iterator[TOMLDocument]:
    """Bracket a multi-file mutation with a ``[pending_turn]`` intent record.

    Loads ``state.toml`` from ``path``, writes a ``[pending_turn]`` record
    atomically *before* yielding, yields the document for the caller's artefact
    work, then on clean exit clears the record and writes atomically. On an
    exception the record is left populated on disk for the next turn's
    ``reconcile`` (design §3.4).

    The yielded document is the *single write source* for the clean-exit write:
    the clear-and-write re-dumps the same document the caller mutated in-bracket,
    so an in-bracket value edit survives a clean exit (design Decision Log). This
    helper owns only the *producer* side; the §5.4 rollback path is
    ``reconcile``'s job (roadmap task 2.3.2).

    Parameters
    ----------
    path : pathlib.Path
        The path to the ``state.toml`` to bracket.
    operation : str
        The operation in flight (``[pending_turn].operation``).
    paths : collections.abc.Sequence[str]
        The paths the operation will write (``[pending_turn].paths``).

    Yields
    ------
    tomlkit.TOMLDocument
        The loaded document, for the caller to mutate in place.
    """
    document = load_document(path)
    open_pending_turn(document, operation=operation, paths=paths)
    # Persist the intent before yielding, so a crash during the caller's
    # artefact work leaves the populated record on disk (design §3.4).
    write_document_atomically(document, path)
    # The unprotected yield is deliberate: the clear-and-write below must run
    # *only* on a clean exit. An exception inside the bracket propagates with the
    # record left populated for the next turn's ``reconcile`` (design §3.4, §5.4;
    # ExecPlan Decision log — this helper owns only the producer side). A
    # try/finally would wrongly clear the record on the error path, so RUF075's
    # "wrap the yield" advice does not apply here.
    yield document  # noqa: RUF075 - leave-on-error is the design §3.4 contract
    clear_pending_turn(document)
    write_document_atomically(document, path)
