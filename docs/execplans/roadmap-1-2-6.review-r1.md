# Logisphere adversarial design review — roadmap-1-2-6 — Round 1

Reviewer: Logisphere crew (Pandalump, Wafflecat, Buzzy Bee, Telefono,
Doggylump, Dinolump) plus pre-mortem and alternatives checkpoint. Plan under
review: `docs/execplans/roadmap-1-2-6.md` (Status: DRAFT).

Verdict: **Revise** — one blocking self-contradiction in WI1's edit
instruction, plus advisory tightening. Every other load-bearing claim in the
plan was verified against source and holds.

## What was verified against source (all confirmed true)

- `state-layout.md`: `tomli_w` import at line 229, `tomli_w.dump(...)` at
  line 235, fenced ```` ```bash ```` block spans lines 226–238. Confirmed.
- `state-layout.md:61` carries "(write to `state.toml.new`, fsync, rename)";
  preservation is correct and necessary.
- ADR-002 line 22 ("even carries", present tense) and line 77 ("is removed",
  present tense) confirmed; the self-contradiction the plan describes is real.
- design §5.3: the "is removed" sentence spans lines 466–467 (the audit cites
  it as `:464`; the plan's 466 is the more precise figure — harmless).
- design §4.1 lines 248–249 ("Direct editing of `state.toml` is eliminated.")
  and §3.4 lines 217–235 (mutator-owned tmp→`Path.replace`) confirmed.
- design §4 lines 240–241 confirm cuprum is required only where a v1 command
  shells out and none do; the "no cuprum API exercised" decision is sound.
- `scripting-standards.md` lines 397–415 carry the tmp→replace pattern; the
  library-neutral replacement prose is faithful to it.
- `tests/test_interrogate_gate.py` is the genuine precedent: `pathlib`,
  `Path(__file__).resolve().parent.parent` root resolution, class form,
  one-line docstrings, no shelling out. WI3's shape mirrors it correctly.
- Makefile gates `all = build check-fmt lint typecheck test`, `markdownlint`,
  `nixie`, and `test` (`pytest -v -n $(PYTEST_XDIST_WORKERS)`) confirmed.
- `pytest-timeout` global `timeout = 30` (pyproject line 323) under xdist
  poses no risk to a millisecond file-read guard; the plan makes no uncited
  library claim about timeout/xdist behaviour. No locked-library memory claim
  is left unverified.
- roadmap 1.2.6 (lines 124–131) explicitly states "no existing task owns this
  removal"; 6.2.3 (lines 452–460) enumerates three *different* skill defects.
  The scoping boundary is correct.

## BLOCKING

1. **WI1's "preserve lines 224 and 240 unchanged" instruction contradicts its
   own edit and is factually wrong about those lines.** Line 224 reads "Write
   state.toml via temp file + rename:" — a colon-terminated *lead-in* to the
   fenced block WI1 deletes; line 240 reads "Append to log.md last…". Neither
   line carries the `state.toml.new` token (that token lives only at the
   deleted lines 234/236 and at the untouched line 61). Yet WI1 (and the
   Context section, plan lines 304–305) instruct the implementer to "Preserve …
   the `state.toml.new`/rename narrative at lines 224 and 240 unchanged" while
   *also* instructing them to replace step 3's worked example with one
   library-neutral sentence. Followed literally, "preserve line 224 unchanged"
   leaves a dangling "via temp file + rename:" colon introducing nothing after
   the block is deleted. The plan must (a) correct the false claim that lines
   224/240 contain a `state.toml.new` narrative, and (b) state explicitly that
   line 224's trailing colon and lead-in must be rewritten into the
   self-contained step-3 sentence (no dangling colon, no orphaned list item),
   so the four-step list renders coherently. As written, WI1 gives the
   implementer mutually exclusive instructions for the exact line it edits.

## ADVISORY

- WI1 deletes a fenced block sitting *between* list item `3.` (line 224) and a
  trailing `1.` (line 240) that Markdown currently renders as item 4 via
  list-continuation. Removing the interrupting fence can change list rendering
  or renumbering. The plan flags markdownlint/mdformat reflow as a low risk and
  mandates `make markdownlint` + `make fmt`; acceptable, but WI1 should state
  the intended post-edit list as an explicit four-item ordered list so the
  implementer does not leave a `3.` then `1.` sequence that mdformat may
  renumber unexpectedly.
- "Red/green, refactor per AGENTS.md" (plan lines 415–416) is slightly
  misattributed: AGENTS.md mandates running suites before and after each change
  but does not name a red-green-refactor cycle. The fixture/stash red-evidence
  approach is sound regardless; drop or re-attribute the citation.
- The audit cites design §5.3 at `:464`; the plan silently uses `:466`. Both
  point at the same sentence; a one-line note reconciling the figure would stop
  a later reader thinking the plan mis-cited the audit.
- WI3's optional cross-document assertion (ADR-002 line-22 phrase) is correctly
  hedged as droppable-if-brittle, with the choice to be recorded in the
  Decision Log — good. No change required.

## Pre-mortem (Doggylump)

Most likely six-months-on failure: a future contributor adds a *different*
direct-edit recipe (e.g. `tomlkit`-based) to the same Atomic-writes section.
WI3's guard pins only the literal `tomli_w`/`import tomli_w`/`tomli_w.dump(`
substrings, so a `tomlkit` hand-edit recipe sails through green while
re-opening the §4.1 "direct editing eliminated" violation the task exists to
foreclose. Blast radius: an agent copies the new recipe, hand-edits
`state.toml`, and corrupts comments/formatting — the exact harm ADR-002
rejects. This is a *scope* observation, not a blocker: the plan's stated
deliverable is Finding 1 (the `tomli_w` snippet), and broadening the guard to
any direct-edit code fence would exceed the surgical scope and risk colliding
with 6.2.3. Recommend the plan note this residual gap in Risks (it currently
lists only "`tomli_w` reappears") so the next reader knows the guard is
substring-specific by design.

## Alternatives checkpoint (Wafflecat)

The roadmap offered delete-vs-rewrite-to-`tomlkit`; the plan resolves to delete
and the resolution is correct (§4.1 forbids demonstrating any direct edit, so a
`tomlkit` rewrite would re-introduce the forbidden pattern). The only credible
*structural* alternative is to fold the guard test's invariant into the existing
`test_interrogate_gate.py`-style suite as a parametrized "reference-files
carry no direct-edit recipe" check rather than a new module — but that broadens
scope toward the pre-mortem gap and 6.2.3's territory, so the plan's
separate-module choice is the right trade for a surgical doc fix. No stronger
alternative exists; the approach is on solid ground.

## Resolution required

Set satisfied only after BLOCKING item 1 is fixed: WI1 must stop claiming lines
224/240 carry a `state.toml.new` narrative and must explicitly rewrite line
224's lead-in colon into the self-contained step-3 sentence, leaving a coherent
four-item ordered list with no dangling colon.
