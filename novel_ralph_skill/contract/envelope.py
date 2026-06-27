"""The shared JSON envelope and its two renderings.

Every command emits one machine-mode JSON object on stdout by default and a
human-readable rendering under ``--human`` (design 3.1, ADR 003). The envelope's
field set and order are fixed by the contract: ``command``, ``schema_version``,
``ok``, ``working_dir``, ``result``, ``messages``. ``ok`` mirrors the exit code
(``True`` only on :data:`~novel_ralph_skill.contract.exit_codes.ExitCode.SUCCESS`);
``result`` holds machine-actionable data the harness reads, while ``messages``
holds human prose the harness never parses.
"""

from __future__ import annotations

import dataclasses
import json
import typing as typ

from novel_ralph_skill._freeze import freeze_mapping, freeze_sequence
from novel_ralph_skill.commands.names import ENVELOPE_COMMAND_NAMES
from novel_ralph_skill.contract.exit_codes import ExitCode, is_ok

if typ.TYPE_CHECKING:
    import collections.abc as cabc

ENVELOPE_SCHEMA_VERSION: int = 1
"""The envelope contract version (design 3.1).

Independent of the ``state.toml`` and rule-pack schema versions; a single
integer constant bumped only when the envelope contract itself changes.
"""


@dataclasses.dataclass(frozen=True, kw_only=True)
class Envelope:
    """An immutable command output envelope in the fixed contract field order.

    Attributes
    ----------
    command : str
        The console-script name that produced the envelope.
    schema_version : int
        The envelope contract version (:data:`ENVELOPE_SCHEMA_VERSION`).
    ok : bool
        ``True`` if and only if the exit code is
        :data:`~novel_ralph_skill.contract.exit_codes.ExitCode.SUCCESS`.
    working_dir : str
        The working directory the command operated on.
    result : collections.abc.Mapping[str, object]
        The machine-actionable structured payload the harness reads.
    messages : collections.abc.Sequence[str]
        Human-oriented notes for the ``--human`` rendering and the log; never
        parsed by the harness.
    """

    command: str
    schema_version: int
    ok: bool
    working_dir: str
    result: cabc.Mapping[str, object]
    messages: cabc.Sequence[str]

    def __post_init__(self) -> None:
        """Freeze ``result``/``messages`` to read-only containers at construction."""
        object.__setattr__(self, "result", freeze_mapping(self.result))
        object.__setattr__(self, "messages", freeze_sequence(self.messages))


ENVELOPE_FIELD_ORDER: typ.Final[tuple[str, ...]] = tuple(
    field.name for field in dataclasses.fields(Envelope)
)
"""The envelope's fixed contract field order, derived from :class:`Envelope`.

This is the single source of truth for the six-name order (``command``,
``schema_version``, ``ok``, ``working_dir``, ``result``, ``messages``; design
3.1, ADR 003). :func:`render_machine` and the contract and cross-command test
oracles all read this rather than re-spelling the order, so a field added,
dropped, renamed, or reordered in :class:`Envelope` propagates to every
consumer.
"""


def build_envelope(  # noqa: PLR0913  # pylint: disable=too-many-arguments
    # why: the five envelope fields are fixed by ADR 003 and design 3.1; this
    # constructor maps one keyword-only parameter per contract field.
    *,
    command: str,
    working_dir: str,
    code: ExitCode,
    result: cabc.Mapping[str, object],
    messages: cabc.Sequence[str],
) -> Envelope:
    """Build an :class:`Envelope`, deriving ``ok`` from ``code``.

    ``ok`` is derived from :func:`is_ok` so a caller cannot set it
    inconsistently with the exit code, and ``command`` is validated against the
    single source of truth
    (:data:`novel_ralph_skill.commands.names.ENVELOPE_COMMAND_NAMES`). That guard
    is the spaced ``novel <verb>`` subcommand names plus the bare ``"novel"``
    surface, so every name the multiplexer stamps validates (ADR 007; ExecPlan
    Decision Log D1).

    Parameters
    ----------
    command : str
        The console-script or spaced subcommand name; must be a member of
        ``ENVELOPE_COMMAND_NAMES``.
    working_dir : str
        The working directory the command operated on.
    code : ExitCode
        The command's exit code; ``ok`` is derived from it.
    result : collections.abc.Mapping[str, object]
        The machine-actionable structured payload.
    messages : collections.abc.Sequence[str]
        Human-oriented notes.

    Returns
    -------
    Envelope
        The assembled envelope with ``schema_version`` stamped and ``ok``
        derived from ``code``.

    Raises
    ------
    ValueError
        If ``command`` is not one of the registered command names.
    """
    if command not in ENVELOPE_COMMAND_NAMES:
        msg = f"unknown command {command!r}; expected one of {ENVELOPE_COMMAND_NAMES}"
        raise ValueError(msg)
    return Envelope(
        command=command,
        schema_version=ENVELOPE_SCHEMA_VERSION,
        ok=is_ok(code),
        working_dir=working_dir,
        result=result,
        messages=messages,
    )


_FIELD_COERCIONS: typ.Final[dict[str, cabc.Callable[[object], object]]] = {
    "result": lambda value: dict(typ.cast("cabc.Mapping[str, object]", value)),
    "messages": lambda value: list(typ.cast("cabc.Sequence[str]", value)),
}
"""Per-field coercions applied before JSON serialisation in :func:`render_machine`.

``result`` and ``messages`` are stored frozen (a read-only mapping and a tuple)
by :meth:`Envelope.__post_init__`; :func:`json.dumps` must see a plain ``dict``
and ``list`` to reproduce today's wire output. Every other field passes through
unchanged.
"""


def render_machine(env: Envelope) -> str:
    """Render ``env`` as a single-line JSON object in the fixed field order.

    The ordered mapping is built by iterating
    :data:`novel_ralph_skill.contract.envelope.ENVELOPE_FIELD_ORDER` -- the order
    declared on the :class:`Envelope` dataclass -- so the renderer cannot diverge
    from the contract it renders. ``result`` and ``messages`` are coerced to a
    plain ``dict``/``list`` via :data:`_FIELD_COERCIONS` so the frozen read-only
    containers serialise to the same JSON as before.

    Parameters
    ----------
    env : Envelope
        The envelope to serialise.

    Returns
    -------
    str
        The machine-mode JSON rendering with keys in contract order.
    """
    ordered: dict[str, object] = {}
    for name in ENVELOPE_FIELD_ORDER:
        value = getattr(env, name)
        coerce = _FIELD_COERCIONS.get(name)
        ordered[name] = coerce(value) if coerce is not None else value
    return json.dumps(ordered)


def render_human(env: Envelope) -> str:
    """Render ``env`` as a readable multi-line human rendering.

    The human channel surfaces ``ok``, the working directory, and each message
    on its own line. It omits the raw ``result`` payload: ``messages`` is the
    human channel per design 3.1, while ``result`` is the machine channel.

    Parameters
    ----------
    env : Envelope
        The envelope to render.

    Returns
    -------
    str
        A multi-line human-readable rendering.
    """
    lines = [
        f"command: {env.command}",
        f"ok: {env.ok}",
        f"working_dir: {env.working_dir}",
    ]
    if env.messages:
        lines.append("messages:")
        lines.extend(f"  - {message}" for message in env.messages)
    else:
        lines.append("messages: (none)")
    return "\n".join(lines)
