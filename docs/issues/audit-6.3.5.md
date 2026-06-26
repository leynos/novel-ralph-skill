# Post-merge audit — roadmap task 6.3.5

Task 6.3.5 made the six *draft-read* (exit-3) boundaries actionable (commit
`f5bbfda`), extending 6.3.1's state.toml-load polish to the draft-read faults. It
adds a `_draft_read_error(reported_dir, exc)` formatter to the dependency-free
leaf module `novel_ralph_skill/commands/_state_load.py` — the draft-read sibling
of `_state_input_error` — and routes the six boundaries through it:
`_disk_evidence_or_state_error` (in `novel_state.py`), `_recount`, `_wordcount`,
`_novel_done`, `_desloppify.source_chapters`, and both of `_compile`'s draft-read
tails. The mutator view-derivation boundary (`_state_view_or_state_error`) is
re-pointed at `_state_input_error`'s present-but-corrupt arm instead, because a
structurally-incomplete `state.toml` is a state-document fault, not a draft
fault. New parity, unit, and BDD coverage prove every exit-3 draft-read boundary
emits the one formatter-owned remedy clause, and the developers' guide documents
the two-formatter split.

This audit reviews the merged state at `origin/main` (commit `f5bbfda`) for
refactoring opportunities, duplication, complex conditionals, ergonomic
awkwardness, high-similarity functions, inconsistencies, separation-of-concerns
and command/query-segregation issues, and gaps in documentation comments,
developer/user documentation, and behavioural/unit test coverage. Each finding
records a location and a concrete proposed fix.

The 6.3.5 change itself is well-targeted and well-documented: `_draft_read_error`
is a single-arm formatter with a thorough docstring, the scope boundary against
the write/rule-pack/ledger faults is deliberate and explained, and the parity
test pins the shared remedy clause so a one-sided re-wording fails. The material
findings concern the *boundary the change drew*. The headline finding is that
6.3.5 propagated the same cwd-relative-path-in-the-message pattern that the
6.3.4 audit already flagged (`docs/issues/audit-6.3.4.md` Findings 1 and 2),
adding six more relative-path message sites without resolving the open polarity
decision — so 6.3.5 widened, rather than closed, that inconsistency. The
remaining findings are pre-existing duplication and CQS-adjacent friction the
6.3.5 surface now sits on top of, most of which is already queued on the roadmap
(7.3.3, 7.3.4, 7.4.1) but whose scope should be extended to cover the new
`_draft_read_error` call argument.

## 1. `_draft_read_error` is fed cwd-relative paths, re-opening the 6.3.4 field-vs-message polarity gap

- **Category:** inconsistency
- **Severity:** medium
- **Location:** `novel_ralph_skill/commands/_compile.py:145,220`,
  `novel_ralph_skill/commands/_novel_done.py:94`,
  `novel_ralph_skill/commands/novel_state.py:163`,
  `novel_ralph_skill/commands/_recount.py:99`,
  `novel_ralph_skill/commands/_wordcount.py:103`,
  `novel_ralph_skill/commands/_desloppify.py:214` (all call sites);
  `novel_ralph_skill/commands/_state_load.py:138` (the formatter)

Task 6.3.4 added `resolved_working_dir()` (`_state_load.py:50`) precisely so a
misresolution becomes visible — a stray `cd` into `working/` shows
`.../working/working` rather than failing silently — and stamped that absolute
path into the envelope `working_dir` field and `init`'s `result.working_dir`.
The 6.3.4 audit then flagged (Finding 1) that every *message* naming the same
directory was still cwd-relative, leaving the open decision: thread
`resolved_working_dir()` into the message builders, or document that messages are
relative by design. That decision was never taken and was not folded into the
roadmap.

6.3.5 then routed six boundaries through `_draft_read_error`, passing the bare
relative `working_dir()` (or `pathlib.Path(WORKING_DIR_NAME)`) at every site, so
the new actionable message names a relative `working` token rather than the
resolved absolute path. The footgun 6.3.4 set out to surface stays silent in the
message channel exactly when an operator most needs it — a fault has occurred and
they are reading the prose, not parsing JSON. 6.3.5 widened the inconsistency the
prior audit raised by adding six more relative-path message sites.

- **Proposed fix:** Take the deferred 6.3.4 polarity decision now and apply it to
  both formatters. Preferred: give `_draft_read_error` and `_state_input_error`
  the resolved path by calling `reported_dir.resolve()` (or threading
  `resolved_working_dir()` at the call sites), matching the absolute path the
  envelope field already carries and honouring the "visible misresolution" goal
  the design doc asserts. Alternatively, document explicitly that messages stay
  cwd-relative and the field is the canonical machine signal, and add the
  one-line note to the design doc and developers' guide. Either way, fold the
  decision into the roadmap (see proposed item below) so it does not drift across
  a third audit.

## 2. No test pins the directory token in the draft-read message; the relative form is locked in

- **Category:** test-gap
- **Severity:** medium
- **Location:** `tests/test_draft_read_message_unit.py:57-63`,
  `tests/test_draft_read_message_parity.py:87`,
  `tests/steps/draft_read_message_steps.py:108`

The 6.3.5 suite asserts the *remedy clause* substring and that the message names
*a* `working/` token (`assert str(reported_dir) in message`), but nothing pins
whether that token is the resolved absolute path or the bare relative `working`.
Every test drives the boundary from `working.parent` with a relative
`working_dir="working"`, and the unit test constructs `reported_dir =
pathlib.Path("working")` — so the relative form is pinned by omission, mirroring
the 6.3.4 audit's Finding 2 about the message channel. There is no analogue of
6.3.4's `test_main_surfaces_inside_working_footgun` for the draft-read message:
no test proves (or denies) that a stray `cd` into `working/` surfaces as
`.../working/working` in the *message*.

- **Proposed fix:** Once Finding 1's polarity is settled, add a test that drives
  a draft-read boundary from *inside* `working/` and asserts the message
  surfaces the resolved `.../working/working` path (if option a) or explicitly
  asserts the relative token is intended (if option b). This closes the
  message-channel coverage hole the parity and unit tests leave open and makes
  the chosen polarity load-bearing rather than incidental.

## 3. `_desloppify.source_chapters` rebuilds the `working/` and `state.toml` paths inline rather than via the shared accessors

- **Category:** duplication
- **Severity:** low
- **Location:** `novel_ralph_skill/commands/_desloppify.py:202-203,214`

`source_chapters` constructs `working_dir = pathlib.Path(WORKING_DIR_NAME)` and
`working_dir / "state.toml"` inline, then passes that same inline `working_dir`
to `_draft_read_error`. This bypasses the documented single-source `working_dir()`
and `state_path()` accessors in `_state_load.py` — the very consolidation
audit:1.3.5 and audit:2.2.2 (Finding 3) established to construct the canonical
paths in exactly one place. 6.3.5 added a *third* consumer of this inline path
(the `_draft_read_error` argument), so the inline reconstruction now also decides
what the actionable message names, compounding the cost of the divergence: a
future change to the resolution rule (e.g. Finding 1's `resolve()`) must be
applied at the accessor *and* at this inline site, or `desloppify`'s message will
silently drift from the other five boundaries.

- **Proposed fix:** Already queued as roadmap task 7.3.4 (route `_desloppify` and
  `_wordcount` through the shared `working_dir`/`state_path` accessors). Extend
  that task's scope to note that the accessor must also feed the
  `_draft_read_error` argument, so the formatter receives a canonical path from
  a single source. No new roadmap item is needed; record here that 6.3.5 added a
  new dependent (the message argument) to the inline-path debt 7.3.4 already
  tracks.

## 4. The six `_draft_read_error` call sites compute `reported_dir` six different ways

- **Category:** inconsistency
- **Severity:** low
- **Location:** `_compile.py:138,145` (`root = working_dir()`),
  `_compile.py:220` (`working_dir()` recomputed),
  `_novel_done.py:87,94` (`root = working_dir()`),
  `novel_state.py:163` (`working_dir` parameter),
  `_recount.py:97,99` (`_working_dir()` called twice),
  `_wordcount.py:103` (`working_dir` parameter),
  `_desloppify.py:202,214` (`pathlib.Path(WORKING_DIR_NAME)`)

The formatter is shared, but the argument it receives is derived through five
distinct idioms: a `root` local, a re-invoked `working_dir()`/`_working_dir()`,
a passed-through parameter, and an inline `pathlib.Path(WORKING_DIR_NAME)`. They
all currently resolve to the same relative `working`, so the messages match
today, but the divergence is latent: the parity test deliberately does *not*
assert cross-boundary directory identity (it pins only the remedy clause), so a
one-sided change to any one of these derivations would not be caught. `_recount`
additionally calls `_working_dir()` twice — once for the read, once for the error
arm — which is harmless (the accessor is pure) but redundant and reads as if the
two could differ.

- **Proposed fix:** Largely absorbed by roadmap tasks 7.3.3 (consolidate the
  draft-read state-error wrapper shared by `wordcount`, `recount`, `desloppify`)
  and 7.3.4 (route through the shared accessors). When 7.3.3 lifts the
  `try/except STATE_INPUT_ERRORS` tail into one `read_drafts_or_state_error`
  helper, that helper should own the single `reported_dir` derivation and pass it
  to `_draft_read_error`, collapsing the five idioms to one. In `_recount`,
  capture `_working_dir()` once into a local and reuse it for both the read and
  the error arm. No new roadmap item is needed beyond extending 7.3.3's scope to
  carry the `_draft_read_error` argument.

## 5. Exit-3 rule-pack, device-ledger, and compile-write faults still interpolate raw `{exc}`

- **Category:** inconsistency
- **Severity:** low
- **Location:** `novel_ralph_skill/commands/_desloppify.py:270`
  (`cannot read rule pack: {exc}`),
  `novel_ralph_skill/commands/_desloppify_ledger.py:90`
  (`cannot read device ledger: {exc}`),
  `novel_ralph_skill/commands/_compile.py:156`
  (`cannot write {_COMPILED_REL}: {exc}`)

6.3.1 and 6.3.5 set out to stop exit-3 messages leaking raw OS text (an `Errno`,
a `{exc}` repr). They covered the state.toml-load and draft-read faults, but
three other exit-3 arms still interpolate the caught exception's repr. 6.3.5
deliberately scopes these out of `_draft_read_error` (the prose "inspect the
`working/` tree" would mislead for a `--pack` file or a write), and that scoping
is correct — but scoping out of *one formatter* is not the same as making the
message actionable. These three arms still violate `scripting-standards.md` line
678 ("Production code should present friendly error messages") in the same way
the draft-read arms did before 6.3.5: a `RulePackFileError`/`LedgerFileError`
stringifies to OS-shaped text, and the compile-write arm interpolates the raw
`OSError`. The actionable-message standard has been applied unevenly across the
exit-3 channel.

- **Proposed fix:** Mint write- and file-shaped sibling formatters (analogous to
  `_draft_read_error`) so the rule-pack/device-ledger read faults name the pack/
  ledger path and ask for inspect/repair, and the compile-write fault names the
  target and offers a write-shaped remedy (check the `manuscript/` directory
  exists, permissions), without leaking the `{exc}` repr. This is a natural
  follow-on to 6.3.1/6.3.5 and is not yet on the roadmap; see the proposed item
  below. Coordinate with 7.3.9 (unify the desloppify and ledger pack-detect
  pipelines), which touches the same pack/ledger surface.

## 6. The users' guide describes exit-3 *conditions* but not the now-actionable *messages*

- **Category:** docs-gap
- **Severity:** low
- **Location:** `docs/users-guide.md:104,118,182,252,442,490`

The developers' guide gained a thorough description of the two-formatter split
and the actionable prose (commit `f5bbfda`), but the users' guide — the document
the operator who actually *reads* the exit-3 message consults — still describes
only the *conditions* that trigger exit 3 ("an unreadable or undecodable draft …
likewise exits `3`"). It does not tell the operator what the message will say or
what to do (inspect and repair the offending `draft.md`/`compiled.md`, or restore
from a known-good copy). The actionable-message work is invisible to its primary
audience.

- **Proposed fix:** Add a short note to the users' guide exit-codes section
  stating that exit-3 messages are actionable — they name the `working/` tree (or
  `state.toml`) and tell the operator to inspect, repair, or restore the named
  artefact — so an operator knows the message is the remedy, not raw OS noise.
  Keep it brief; the developers' guide carries the formatter detail.
