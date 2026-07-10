# Logisphere design review — roadmap 6.3.1 (round 1)

Adversarial pre-implementation review of `docs/execplans/roadmap-6-3-1.md`.
Plan read from disk; load-bearing claims verified against the worktree source,
the installed cuprum wheel, the roadmap, and AGENTS.md. Trail:
`logisphere-design-review` skill, `docs/roadmap.md` §6.3.1 (lines 2127-2149),
`AGENTS.md` (lines 141-178), `docs/scripting-standards.md` (lines 604-605,
678), the source files cited below.

## Verdict: PROCEED WITH CONDITIONS

The plan is structurally sound, correctly scoped to the two producers the
roadmap names, and its cuprum/library claims verify against the installed
wheel. No blocking defect prevents implementation as written. Three advisory
items should be folded in by the planner before or during implementation.

## What was verified true (the plan's spine holds)

- The two producers exist exactly as described:
  `novel_state.py:139-167` (`_load_or_state_error`, message at `:166`) and
  `_state_mutators.py:78-106` (`_load_document_or_state_error`, message at
  `:105`). Both build `f"cannot load {path}: {exc}"`.
- `STATE_INPUT_ERRORS` is at `novel_state.py:130-136`; accessors `working_dir`
  (`:102`), `state_path` (`:113`) as cited.
- Import direction confirmed: `_state_mutators` imports from `novel_state`
  one-way (`:35-43`); `novel_state` imports `_state_mutators` only lazily
  inside the builder (`:346`). Placing the helper in `novel_state` adds no new
  edge.
- D2's existence premise holds on BOTH paths: `load_state` opens via
  `path.open("rb")` (`parse.py:246`) and `load_document` via
  `path.read_text(...)` (`document.py:91`), so a missing file raises
  `FileNotFoundError` before parsing on each.
- The `grep -rn "cannot load"` sweep returns exactly 6 hits; the plan's four
  test sites are complete and the line numbers (matrix `:220`, e2e `:138`,
  `test_compile_unit.py:278`, `test_desloppify_sourcing.py:128`) are accurate.
- Both matrices assert by `startswith(message_prefix)` (matrix `:448`, e2e
  `:282`/`:336`), so the variable `{cwd}` after the stable prefix
  `no novel working/ found in` does not break the assertion.
- The in-process matrix `_READ_REGISTRY` (`:127`) excludes mutators
  (docstring `:29-30`), so Work item 3's claim that a separate mutator proof is
  needed is correct.
- Cuprum D5 surface verified against the INSTALLED wheel:
  `SafeCmd.run_sync(self, *, capture=True, echo=False, context=ExecutionContext|None=None)`,
  `ExecutionContext` carries `cwd`. The plan correctly pins to the installed
  surface, warns off the diverged source tree, and adds no new cuprum call.

## Findings

### Advisory 1 (Telefono ☎️, correctness) — the "missing" message can lie

D2 specifies: if `path.parent` (working/) OR `state.toml` does not exist, emit
`no novel working/ found in {cwd}`. But a present-but-empty `working/`
(working/ exists, `state.toml` absent — a partially-initialized tree) satisfies
the OR via the second disjunct, so the agent is told `working/` is absent when
it is not. The remedy (`novel state init`) is still correct (`init` creates
`state.toml` when only it is missing; it refuses only when `state.toml` already
exists — `novel_state.py:296`), but the diagnostic text is inaccurate for that
sub-case. The plan defers final wording to the unit test, so this is fixable,
but the plan should explicitly name the empty-`working/` sub-case and either
(a) re-word to `no novel state found in {cwd}` (true for both the
absent-working/ and absent-state.toml cases) or (b) branch the two sub-cases.
Add a unit case for present-`working/`/absent-`state.toml`.

### Advisory 2 (Pandalump 🐼, scope honesty) — Purpose overclaims "every command"

The Purpose says "The same actionable message appears for **every** command …"
and "both boundaries emit the identical message." That is true only for the
`cannot load {path}` load boundary. There are OTHER exit-3 `StateInputError`
producers the plan (correctly) leaves out of scope because they emit a
DIFFERENT string: `_compile.py:96,141-142,151,211-212` and
`_wordcount.py:99-100` raise `cannot read chapter drafts: {exc}` (raw errno
included) when a `draft.md` is unreadable. The roadmap §6.3.1 explicitly scopes
the task to the two `cannot load {path}` producers, so excluding the draft-read
producers is design-conformant — but the Purpose prose should not claim
universality it does not deliver. Re-word the Purpose to "every command that
loads `state.toml`" (readers, checkers, mutators), and add one Tolerances/Risks
line acknowledging that the `cannot read chapter drafts` exit-3 messages remain
raw and are out of scope for 6.3.1.

### Advisory 3 (Doggylump 🐶, gate completeness) — Work item 5 omits `make fmt`

AGENTS.md line 178 requires `make fmt` after Markdown documentation changes (to
format Markdown and fix table markup). Work item 5 lists `make markdownlint` and
`make nixie` but not `make fmt`. Add `make fmt` to Work item 5's validation
steps so the developers'-guide edit lands formatted and does not trip the gate.

### Improvement 1 (Telefono ☎️) — prove corrupt-arm parity, not just missing-arm

Work item 2's byte-for-byte parity test drives both producers from a
`working/`-less directory, which exercises only the MISSING arm (where the
message interpolates `{cwd}` only and is path-independent, so parity is
trivial). The CORRUPT arm "names the path", and the two producers can be handed
different path spellings. Both currently pass `working/state.toml`, so parity
holds today, but the plan's own anti-drift mandate is strongest if the parity
test also covers the corrupt arm (a present-but-unparseable `state.toml`,
asserting both producers emit identical corrupt-arm text). Add that case.

### Improvement 2 (Doggylump 🐶) — pin the unreadable-but-present (PermissionError) case

`STATE_INPUT_ERRORS` includes `OSError`, so a `PermissionError` on an existing
`state.toml` is caught. The helper's existence check sees the file present and
routes to the CORRUPT message ("inspect/repair", no `init`). That is arguably
right, but it is an untested edge the plan does not name. Note it in the
Decision Log so the corrupt-arm wording does not assume "parse failure" when
the real fault may be "permission denied".

## Pre-mortem (Doggylump leads)

It is six months on; a dogfooding agent silently mis-recovered. Working back:

1. Most likely failure: a partially-initialized `working/` (state.toml deleted,
   directory kept) printed "no novel working/ found", the agent ran from the
   right root, saw the message blame the directory, and concluded its cwd was
   wrong — chasing the wrong remedy. Mitigation: Advisory 1.
2. Second path: `novel compile`/`wordcount` hit an unreadable `draft.md`, still
   emitted raw `[Errno 13]` via `cannot read chapter drafts`, and the agent
   read it as noise — the exact incident class 6.3 exists to close, but for a
   message string 6.3.1 does not touch. Blast radius bounded to
   compile/wordcount; signal missed because the Purpose implied all exit-3
   messages were now actionable. Mitigation: Advisory 2 (scope honesty), and a
   follow-up roadmap item for the draft-read producers.
3. Third path: a future edit to one producer's path argument silently diverges
   the corrupt-arm text from the other producer; the missing-arm-only parity
   test stays green. Mitigation: Improvement 1.

## Alternatives checkpoint (Wafflecat leads)

Strongest alternative: collapse BOTH producers into a single load function that
already raises `StateInputError` (push the try/except down into `load_state`/
`load_document`'s callers' shared seam, or a new `load_state_or_error` in the
`state` package), rather than keeping two thin wrappers that each call a shared
message helper. Trade-off: it would eliminate the "two boundaries that must
agree" problem at the root instead of papering it with a shared string. But it
crosses the deterministic-spine module boundary (`state/` vs `commands/`),
risks the import-cycle the plan carefully avoids, and expands the diff well
past the plan's 6-file/150-line tolerance. The plan's choice — one message
helper, two callers — is the smaller, lower-risk move and is the one the
roadmap text prescribes ("Route both through one shared actionable-message
helper"). No change recommended; the plan is on solid ground.

## Conditions to clear before/at implementation

1. Advisory 1: name the empty-`working/` sub-case and fix the message so it does
   not claim `working/` is absent when only `state.toml` is; add the unit case.
2. Advisory 2: re-word the Purpose to scope-honest language and record the
   out-of-scope `cannot read chapter drafts` producers in Risks/Tolerances.
3. Advisory 3: add `make fmt` to Work item 5's validation.

Improvements 1-2 are recommended but not gating.
