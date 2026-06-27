"""Schema-agnostic scalar-coercion primitives, parameterised on an error factory.

These are the shared bodies the rule-pack and device-ledger validating
boundaries build on: a message-prefix helper (:func:`where`), an unknown-key
rejector (:func:`reject_unknown_keys`), and the ``require*`` family that reads a
key and narrows its value to a concrete scalar type, converting any missing or
wrong-typed fault into *the caller's* content error.

The primitives carry no package knowledge. Each takes a :class:`CoercionErrors`
bundle that decides how to raise (the caller's typed error, with its id kwarg
already bound) and what to name the offending thing (the caller's noun pair), so
one body serves every pack family. Roadmap task 7.2.2 consolidated the formerly
cloned ``rulepack/_coerce.py`` and ``ledger/_coerce.py`` bodies here (design §6.1;
ADR-001).
"""

from __future__ import annotations

import collections.abc as cabc
import dataclasses
import typing as typ

if typ.TYPE_CHECKING:
    from novel_ralph_skill.contract.errors import EnvelopeMessagesError

# A decoded pack/ledger and each of its array entries is a mapping; a single alias
# documents that shape for the validating helpers below.
type Mapping = cabc.Mapping[str, object]


@dataclasses.dataclass(frozen=True, kw_only=True, slots=True)
class CoercionErrors:
    """The error-factory seam a pack family binds to reuse the coercion bodies.

    This is the single point of parameterisation roadmap task 7.2.2 introduces:
    each shared coercion primitive raises through this bundle rather than naming a
    concrete exception, so one body serves every pack family. The rule pack binds
    it to :class:`~novel_ralph_skill.rulepack.errors.RulePackError` with the
    ``"rule"``/``"rule pack"`` nouns; the device ledger binds it to
    :class:`~novel_ralph_skill.ledger.errors.LedgerError` with the
    ``"device"``/``"device ledger"`` nouns. A third pack family adds a third
    bundle, not a third copy of the helpers.

    Attributes
    ----------
    content_error : collections.abc.Callable[[str, str | None], EnvelopeMessagesError]
        Builds the package's content error from ``(message, offending_id)``, with
        the id keyword (``rule_id=``/``device_id=``) already bound by the caller,
        so the bundle hides the kwarg-name difference between the two packages.
    per_id_noun : str
        The per-entity noun for the message prefix: ``"rule"`` or ``"device"``.
    per_level_noun : str
        The whole-document noun for a top-level fault: ``"rule pack"`` or
        ``"device ledger"``.
    """

    content_error: cabc.Callable[[str, str | None], EnvelopeMessagesError]
    per_id_noun: str
    per_level_noun: str


def where(errors: CoercionErrors, offending_id: str | None) -> str:
    """Return a message prefix naming the offending entity, or the document level.

    Every coercion helper's error message starts with this so the message is
    self-describing for the envelope a command body builds — a per-entity fault
    names the entity, a document-level fault says so.

    Parameters
    ----------
    errors : CoercionErrors
        The bound error factory supplying the noun pair.
    offending_id : str | None
        The offending entity's ``id``, or ``None`` for a document-level fault.

    Returns
    -------
    str
        ``"<per_id_noun> '<id>'"`` for a per-entity fault (for example
        ``"rule 'x'"``), or ``per_level_noun`` (for example ``"rule pack"``)
        otherwise.
    """
    if offending_id is not None:
        return f"{errors.per_id_noun} {offending_id!r}"
    return errors.per_level_noun


def reject_unknown_keys(
    mapping: Mapping,
    allowed: frozenset[str],
    *,
    errors: CoercionErrors,
    offending_id: str | None,
) -> None:
    """Raise the caller's content error if ``mapping`` carries an unknown key.

    An unknown key is rejected rather than silently ignored so a misspelled field
    fails loudly, naming the offending entity (or the document level). This is the
    strict loud-failure reading roadmap 5.1.1 demands, shared by every pack family.

    Parameters
    ----------
    mapping : Mapping
        The decoded table or entry to inspect.
    allowed : frozenset[str]
        The complete set of known keys for this level.
    errors : CoercionErrors
        The bound error factory.
    offending_id : str | None
        The offending entity's ``id``, or ``None`` for a document-level fault.

    Raises
    ------
    EnvelopeMessagesError
        The caller's content error, if ``mapping`` carries any key not in
        ``allowed``.
    """
    unknown = sorted(key for key in mapping if key not in allowed)
    if unknown:
        listed = ", ".join(repr(key) for key in unknown)
        permitted = ", ".join(repr(key) for key in sorted(allowed))
        msg = (
            f"{where(errors, offending_id)} has unknown key(s) {listed}; "
            f"allowed keys are {permitted}"
        )
        raise errors.content_error(msg, offending_id)


def require(
    mapping: Mapping,
    key: str,
    *,
    errors: CoercionErrors,
    offending_id: str | None,
) -> object:
    """Return ``mapping[key]`` or raise the caller's content error naming the gap.

    Used in place of ``mapping[key]`` so a missing field never surfaces as a raw
    ``KeyError``; the raised error names ``key`` and the offending entity.

    Parameters
    ----------
    mapping : Mapping
        The decoded table or entry to read.
    key : str
        The required key.
    errors : CoercionErrors
        The bound error factory.
    offending_id : str | None
        The offending entity's ``id``, or ``None`` for a document-level fault.

    Returns
    -------
    object
        The value at ``key``.

    Raises
    ------
    EnvelopeMessagesError
        The caller's content error, if ``key`` is absent from ``mapping``.
    """
    if key not in mapping:
        msg = f"{where(errors, offending_id)} is missing required key {key!r}"
        raise errors.content_error(msg, offending_id)
    return mapping[key]


def require_str(
    mapping: Mapping,
    key: str,
    *,
    errors: CoercionErrors,
    offending_id: str | None,
) -> str:
    """Return ``mapping[key]`` as a ``str`` or raise naming the non-string field.

    Parameters
    ----------
    mapping : Mapping
        The decoded table or entry to read.
    key : str
        The required key.
    errors : CoercionErrors
        The bound error factory.
    offending_id : str | None
        The offending entity's ``id``, or ``None`` for a document-level fault.

    Returns
    -------
    str
        The string value at ``key``.

    Raises
    ------
    EnvelopeMessagesError
        The caller's content error, if ``key`` is absent or its value is not a
        ``str``.
    """
    value = require(mapping, key, errors=errors, offending_id=offending_id)
    if not isinstance(value, str):
        msg = (
            f"{where(errors, offending_id)} key {key!r} must be a string, "
            f"got {type(value).__name__}"
        )
        raise errors.content_error(msg, offending_id)
    # The runtime guard above has already narrowed ``value`` to ``str``.
    return value


def require_int(
    mapping: Mapping,
    key: str,
    *,
    errors: CoercionErrors,
    offending_id: str | None,
) -> int:
    """Return ``mapping[key]`` as an ``int`` or raise naming the non-integer field.

    Rejects ``bool`` explicitly: ``isinstance(True, int)`` is ``True`` in Python,
    so a TOML ``true`` would otherwise be accepted as ``1``. A TOML float or string
    for a numeric field raises rather than being coerced.

    Parameters
    ----------
    mapping : Mapping
        The decoded table or entry to read.
    key : str
        The required key.
    errors : CoercionErrors
        The bound error factory.
    offending_id : str | None
        The offending entity's ``id``, or ``None`` for a document-level fault.

    Returns
    -------
    int
        The integer value at ``key``.

    Raises
    ------
    EnvelopeMessagesError
        The caller's content error, if ``key`` is absent, its value is a ``bool``,
        or its value is not an ``int``.
    """
    value = require(mapping, key, errors=errors, offending_id=offending_id)
    if isinstance(value, bool) or not isinstance(value, int):
        msg = (
            f"{where(errors, offending_id)} key {key!r} must be an integer, "
            f"got {type(value).__name__}"
        )
        raise errors.content_error(msg, offending_id)
    # The runtime guard above has already narrowed ``value`` to ``int``.
    return value


@dataclasses.dataclass(frozen=True, kw_only=True, slots=True)
class BoundCoercion:
    """One :class:`CoercionErrors` bundle exposing every coercion helper pre-bound.

    A pack family obtains this from :func:`bind_coercion` instead of cloning a
    per-family ``_coerce.py`` forwarder module (roadmap 7.2.7). Each method
    delegates to the matching module-level free function with this bundle's
    :attr:`errors` already supplied, so a family calls
    ``coercion.require_str(entry, "pattern", offending_id=id)`` rather than
    re-spelling a one-line ``errors=_ERRORS`` forwarder per helper. The
    :attr:`errors` attribute is the raw :class:`CoercionErrors` the
    array-extraction, schema-version, and pattern-compile primitives bind to
    directly, so a family keeps one ``_ERRORS = bundle.errors`` alias rather than
    repointing those raw-bundle call sites.

    The family's *public* error keyword (``rule_id=``/``device_id=``) is bound
    inside the ``content_error`` callable :func:`bind_coercion` receives, so it
    never appears on these methods; the methods expose only the private
    ``offending_id``. On the multi-argument helpers ``offending_id`` is
    **keyword-only**, so a positional transposition with ``key`` is a
    ``TypeError`` at the call site rather than a silent wrong-id message.

    Attributes
    ----------
    errors : CoercionErrors
        The bound error factory, exposed for the raw-bundle primitives
        (``resolve_schema_version``, ``build_entries``, ``compile_pattern``).
    """

    errors: CoercionErrors

    def where(self, offending_id: str | None) -> str:
        """Return the message prefix for ``offending_id`` (see :func:`where`)."""
        return where(self.errors, offending_id)

    def reject_unknown_keys(
        self, mapping: Mapping, allowed: frozenset[str], *, offending_id: str | None
    ) -> None:
        """Reject any key outside ``allowed`` (see :func:`reject_unknown_keys`)."""
        reject_unknown_keys(
            mapping, allowed, errors=self.errors, offending_id=offending_id
        )

    def require(
        self, mapping: Mapping, key: str, *, offending_id: str | None
    ) -> object:
        """Return ``mapping[key]`` or raise naming the gap (see :func:`require`)."""
        return require(mapping, key, errors=self.errors, offending_id=offending_id)

    def require_str(
        self, mapping: Mapping, key: str, *, offending_id: str | None
    ) -> str:
        """Return ``mapping[key]`` as a ``str`` (see :func:`require_str`)."""
        return require_str(mapping, key, errors=self.errors, offending_id=offending_id)

    def require_int(
        self, mapping: Mapping, key: str, *, offending_id: str | None
    ) -> int:
        """Return ``mapping[key]`` as an ``int`` (see :func:`require_int`)."""
        return require_int(mapping, key, errors=self.errors, offending_id=offending_id)


def bind_coercion(
    *,
    content_error: cabc.Callable[[str, str | None], EnvelopeMessagesError],
    per_id_noun: str,
    per_level_noun: str,
) -> BoundCoercion:
    """Bind the coercion helpers to one family's error channel and noun pair.

    Builds the family's single :class:`CoercionErrors` and returns a
    :class:`BoundCoercion` exposing every helper with that bundle already
    supplied. This is the one binding a third pack family makes instead of cloning
    a per-family ``_coerce.py`` forwarder module (roadmap 7.2.7, design §6.1;
    ADR-003): the family supplies its ``content_error`` (with the public
    ``rule_id=``/``device_id=`` keyword bound inside it) and noun pair once, and
    inherits the whole uniform helper surface rather than re-spelling it.

    Parameters
    ----------
    content_error : collections.abc.Callable[[str, str | None], EnvelopeMessagesError]
        Builds the family's content error from ``(message, offending_id)``, with
        the public id keyword (``rule_id=``/``device_id=``) already bound, so the
        returned bundle hides the kwarg-name difference between families.
    per_id_noun : str
        The per-entity noun for the message prefix (``"rule"``/``"device"``).
    per_level_noun : str
        The whole-document noun for a top-level fault (``"rule pack"``/
        ``"device ledger"``).

    Returns
    -------
    BoundCoercion
        The bundle exposing every coercion helper with ``errors`` bound, plus the
        raw :class:`CoercionErrors` as :attr:`BoundCoercion.errors`.
    """
    return BoundCoercion(
        errors=CoercionErrors(
            content_error=content_error,
            per_id_noun=per_id_noun,
            per_level_noun=per_level_noun,
        )
    )
