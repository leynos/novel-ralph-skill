# Post-merge audit — roadmap task 7.3.8

Audit of the codebase after roadmap task 7.3.8 ("Hoist the spaced-name-to-verb
derivation into `names.py`") merged to `main` at commit `490d77e`. The slice
lifts the `name.split(" ", 1)[1]` idiom — previously re-spelled by the
multiplexer dispatcher and the console-scripts e2e suite — into a single
contract-layer home. It adds the derived
[`SUBCOMMAND_VERBS`](../../novel_ralph_skill/contract/names.py) tuple and a
[`verb_for(spaced)`](../../novel_ralph_skill/contract/names.py) registry accessor
backed by a strict-zipped `_VERB_BY_SUBCOMMAND` lookup, re-exports both through
[`commands/names.py`](../../novel_ralph_skill/commands/names.py) for
back-compatibility, routes the dispatcher
([`novel.py`](../../novel_ralph_skill/commands/novel.py)) and the e2e suite
through the accessor, and pins the invariant with a durable guard
([`tests/test_verb_derivation_home.py`](../../tests/test_verb_derivation_home.py))
plus unit coverage
([`tests/test_contract_names_home.py`](../../tests/test_contract_names_home.py)).

The slice is sound and discharges its success criterion: the spaced-name-to-verb
split is now derived in exactly one place, the two tuples are pinned in lockstep
by `zip(..., strict=True)`, the accessor fails loudly on an unknown name, and no
inline `split(" ", 1)` survives outside the registry. The docstrings on the new
symbols are exemplary. The findings below are tidy-ups; none is a blocking
defect, and none weakens the new home or its guard. The headline opportunity is
unrelated to 7.3.8's own change: the `loaderkit.scan.scan_pattern` primitive
still carries a `line_hit` constructor parameter that both call sites satisfy
with the byte-identical `lambda chapter, line: LineHit(...)`, even though
`LineHit` now lives in `loaderkit` alongside the primitive — the injection seam
the parameter was added for no longer has a reason to exist.

This audit reviews the merged state at `origin/main` (commit `490d77e`) for
refactoring opportunities, duplication, complex conditionals, ergonomic
awkwardness, high-similarity functions, inconsistencies, separation-of-concerns
and command/query-separation (CQS) issues, and gaps in documentation comments,
developer/user documentation, and behavioural/unit test coverage. Each finding
records a category, a location, a description, a concrete proposed fix, and a
severity. The trail: design §6.1 and §6.3, ADR 003 (shared interface contract),
ADR 007 (the `novel` multiplexer surface),
[`docs/developers-guide.md`](../developers-guide.md), `AGENTS.md`, and the
execplan [`docs/execplans/roadmap-7-3-8.md`](../execplans/roadmap-7-3-8.md).
Navigation used `leta` and history used `sem`.

## Finding 1 — `scan_pattern`'s `line_hit` constructor parameter is now a vestigial injection seam both call sites satisfy identically

- Category: ergonomics
- Severity: medium
- Location:
  [`novel_ralph_skill/loaderkit/scan.py`](../../novel_ralph_skill/loaderkit/scan.py)
  (`scan_pattern`, lines 65-104) and its two call sites
  [`novel_ralph_skill/rulepack/detect.py`](../../novel_ralph_skill/rulepack/detect.py)
  (line 207) and
  [`novel_ralph_skill/ledger/detect.py`](../../novel_ralph_skill/ledger/detect.py)
  (line 245).

`scan_pattern` takes a keyword-only `line_hit: Callable[[int, int], LineHit]`
constructor, and both production callers — and every test caller — pass the
byte-identical `lambda chapter, line: LineHit(chapter=chapter, line=line)`. The
parameter's docstring justifies it as keeping the primitive free of a "pack-domain
hit type": "this module never imports a pack-domain hit type at runtime". That
rationale is stale. Roadmap 7.2.3 relocated `LineHit` (and `ScannedChapter`) out
of the pack domain *into* `loaderkit.scan` itself — `scan_pattern` is defined in
the same module as `LineHit` and the module already references it in the return
type annotation `tuple[int, tuple[LineHit, ...]]`. The callable is therefore an
injection seam with nothing left to inject: it cannot decouple the primitive from
a type it co-defines. The cost is a real one — three identical lambdas (two in
production, several in tests), a wider signature, and a docstring paragraph
defending an abstraction that no longer earns its keep.

Proposed fix: drop the `line_hit` parameter and have `scan_pattern` construct
`LineHit(chapter=chapter.number, line=index)` directly in its hit-accumulation
loop, since both already live in `loaderkit.scan`. Update the two `detect.py`
call sites to `scan_pattern(rule.compiled, chapters)` /
`scan_pattern(device.compiled, chapters)` and delete the duplicated lambdas;
simplify `test_loaderkit_scan.py` accordingly (the `recording_line_hit` test that
exercises the injection point can be retired or re-expressed as a direct
assertion on the returned `LineHit` tuple). If a future third detector genuinely
needs a different hit shape, re-introduce the seam then — but the present two
callers prove it is not needed now (YAGNI). If the seam is deliberately retained
to keep `scan_pattern` generic ahead of a known need, record that need in the
docstring instead of the now-inaccurate "never imports a pack-domain hit type"
justification.

## Finding 2 — `novel.py` rebuilds the spaced-name-to-verb map `verb_for` already holds internally, calling the accessor per name

- Category: duplication
- Severity: low
- Location:
  [`novel_ralph_skill/commands/novel.py`](../../novel_ralph_skill/commands/novel.py)
  (`_VERB_FOR_SUBCOMMAND`, lines 53-55) versus
  [`novel_ralph_skill/contract/names.py`](../../novel_ralph_skill/contract/names.py)
  (`_VERB_BY_SUBCOMMAND`, lines 75-77, and `SUBCOMMAND_VERBS`, lines 61-63).

The dispatcher builds `_VERB_FOR_SUBCOMMAND = {name: verb_for(name) for name in
SUBCOMMAND_NAMES}` — a dict mapping each spaced name to its bare verb. But the
contract registry already holds exactly this mapping as the private
`_VERB_BY_SUBCOMMAND = dict(zip(SUBCOMMAND_NAMES, SUBCOMMAND_VERBS, strict=True))`
that `verb_for` wraps. The dispatcher reconstructs that dict one `verb_for(name)`
call at a time, paying a per-name dictionary lookup to rebuild the dictionary the
accessor reads from. The result is the same data spelled twice — once strictly
zipped in the contract, once comprehension-rebuilt in the dispatcher — which is
the precise "names derived in two places can drift" smell task 7.3.8 set out to
close, surviving one consumer up. (It cannot drift today because both derive from
`SUBCOMMAND_NAMES`, but the second derivation is gratuitous.)

Proposed fix: build the dispatcher's map directly from the registry's two pinned
tuples — `_VERB_FOR_SUBCOMMAND = dict(zip(SUBCOMMAND_NAMES, SUBCOMMAND_VERBS,
strict=True))` (re-exporting `SUBCOMMAND_VERBS` is already done) — so the
dispatcher consumes the derived verbs rather than re-deriving them through the
scalar accessor. Alternatively, expose the mapping itself from the registry (a
`verb_map() -> Mapping[str, str]` accessor returning a read-only view of
`_VERB_BY_SUBCOMMAND`) and have the dispatcher consume that, so the spaced→verb
*and* verb→spaced relation is owned in exactly one place. `verb_for` then remains
the scalar convenience for single lookups (`_command_name_for` uses the reverse
map, not `verb_for`).

## Finding 3 — `_desloppify.py` imports `WORKING_DIR_NAME` through the back-compat re-export rather than its canonical contract home

- Category: inconsistency
- Severity: low
- Location:
  [`novel_ralph_skill/commands/_desloppify.py`](../../novel_ralph_skill/commands/_desloppify.py)
  (line 47, importing `WORKING_DIR_NAME` from
  `novel_ralph_skill.commands.state_sourcing`) versus
  [`novel_ralph_skill/contract/names.py`](../../novel_ralph_skill/contract/names.py)
  (lines 109-118, the canonical home).

Roadmap task 7.3.6 relocated `WORKING_DIR_NAME` to `contract.names` as a
*contract* fact and left a back-compatibility re-export on
`commands.state_sourcing`. `state_sourcing.py` itself and the package surface
`contract/__init__.py` both import it from the canonical `contract.names`, but
`_desloppify.py` reaches for it through the `state_sourcing` re-export — the
back-compat shim, not the source of truth. This is a small consistency wrinkle:
the one constant has a designated home, yet one consumer routes through the
forwarder, so a future reader cannot tell from the import whether `_desloppify`
treats the token as a command-layer detail or a contract fact (it is the latter).

Proposed fix: repoint `_desloppify.py`'s `WORKING_DIR_NAME` import to
`from novel_ralph_skill.contract.names import WORKING_DIR_NAME` (or the package
surface `from novel_ralph_skill.contract import WORKING_DIR_NAME`), matching how
`state_sourcing.py` and `contract/__init__.py` already source it, and leaving the
`state_sourcing` re-export purely for external back-compat. If the back-compat
re-export is intended to remain the in-tree import path for command modules
(so the contract relocation stays invisible to the command layer), state that
convention in the `state_sourcing` re-export's docstring so the divergent import
reads as deliberate.

## Finding 4 — Sibling command modules import the underscore-private `_rule_pack_read_error` / `_device_ledger_read_error` across module boundaries

- Category: separation-of-concerns
- Severity: low
- Location:
  [`novel_ralph_skill/commands/_desloppify.py`](../../novel_ralph_skill/commands/_desloppify.py)
  (line 50, importing `_rule_pack_read_error`) and
  [`novel_ralph_skill/commands/_desloppify_ledger.py`](../../novel_ralph_skill/commands/_desloppify_ledger.py)
  (line 35, importing `_device_ledger_read_error`) — both defined in
  [`novel_ralph_skill/commands/state_sourcing.py`](../../novel_ralph_skill/commands/state_sourcing.py)
  (lines 302 and 339).

`state_sourcing.py` defines `_rule_pack_read_error` and
`_device_ledger_read_error` with a leading underscore — the Python convention for
"module-private, not part of this module's surface" — yet both are imported by
sibling command modules. A name that is imported across a module boundary is, by
definition, package-internal API, not module-private; the underscore advertises
an encapsulation the call graph contradicts. (Contrast `draft_read_guard` and
`load_or_state_error` in the same module, which are public-named precisely because
they are shared.) This is the same de-facto-public-but-underscore-named smell that
a linter's "private member accessed" rule would flag, and it makes the
`state_sourcing` surface read as smaller than it is.

Proposed fix: rename the two cross-imported helpers to public names
(`rule_pack_read_error`, `device_ledger_read_error`), matching the public-named
`draft_read_guard`/`load_or_state_error` they sit beside, and update the two
import sites and their docstring `:func:` cross-references. The change is purely
cosmetic to behaviour but aligns the name with the actual visibility. If the
underscore is kept to signal "internal to the `commands` package, not the public
console surface", document that package-private convention in the
`state_sourcing.py` module docstring so the cross-module import of an
underscore-named symbol reads as intentional.

## Finding 5 — `_rule_pack_read_error` and `_device_ledger_read_error` are near-identical operator-path read-error formatters

- Category: similarity
- Severity: low
- Location:
  [`novel_ralph_skill/commands/state_sourcing.py`](../../novel_ralph_skill/commands/state_sourcing.py)
  (`_rule_pack_read_error`, lines 302-336, and `_device_ledger_read_error`,
  lines 339-369).

The two formatters reduce to the same shape: build the message
`"cannot read {noun} {path}; check the --{flag} path is correct and readable{suffix}"`
and delegate the wrap to `_file_fault_error`. They differ only in the noun
(`"rule pack"` versus `"device ledger"`), the flag (`--pack` versus `--ledger`),
and a trailing remedy clause (the rule-pack message adds ", or omit --pack to use
the shipped default pack"). The shared *tail* (`_file_fault_error`) is already
single-homed (audit:6.3.8), but the message *body* — the
"cannot read … check the --flag path" template that distinguishes an
operator-supplied path fault from the `working/`-tree `_draft_read_error` — is
spelled twice. A third operator-supplied-path artefact would clone the template
a third time.

Proposed fix: extract a shared `_operator_path_read_error(*, noun: str, flag:
str, path: object, remedy: str = "")` (or accept the assembled remedy suffix)
that builds the `"cannot read {noun} {path}; check the --{flag} path is correct
and readable{remedy}"` body once and delegates to `_file_fault_error`. The two
formatters become one-line calls — `_operator_path_read_error(noun="rule pack",
flag="pack", path=pack_path, remedy=", or omit --pack to use the shipped default
pack")` and the bare-remedy ledger variant — so the operator-path template lives
in one place beside `_draft_read_error`'s `working/`-tree template. This is a
small, optional tidy; if the two messages are kept separate so each can diverge
freely in wording, the duplication is acceptable and no change is needed.

## Finding 6 — `verb_for`'s `KeyError`-raising contract is not surfaced in the developers' guide alongside the registry it documents

- Category: docs-gap
- Severity: low
- Location:
  [`docs/developers-guide.md`](../developers-guide.md) (the command-name registry
  prose) versus
  [`novel_ralph_skill/contract/names.py`](../../novel_ralph_skill/contract/names.py)
  (`verb_for`, lines 80-106).

The 7.3.8 ExecPlan's documentation sweep updated the guide's headings, but the
new public contract accessor `verb_for` — and specifically its deliberate
"`KeyError` on an unregistered name makes the registry the sole authority"
behaviour — is documented only in the function docstring. The developers' guide
describes the command-name vocabulary (`SUBCOMMAND_NAMES`,
`ENVELOPE_COMMAND_NAMES`) but does not yet name `SUBCOMMAND_VERBS` / `verb_for`
or explain that callers must pass a registry-known spaced name and that a typo
fails loudly rather than being silently split. A maintainer reading the guide to
understand the registry surface would not learn the accessor exists or that its
failure mode is load-bearing (the e2e suite and dispatcher both depend on it).

Proposed fix: add a short paragraph to the developers' guide's command-name
registry section naming `SUBCOMMAND_VERBS` and `verb_for`, stating that the bare
mount verbs are derived once from `SUBCOMMAND_NAMES` (so the split lives in one
place) and that `verb_for` raises `KeyError` on any non-registry name, making the
registry the sole authority for the spaced→verb relation. Cross-reference the
guard test (`test_verb_derivation_home.py`) so the "no `split(" ", 1)` survives
outside the registry" invariant is discoverable from the guide, mirroring how the
guide already cross-references other single-home guards.
