# Logisphere design review — roadmap-1-2-6 ExecPlan, round 2

Verdict: REVISE (one blocking self-contradiction in the acceptance criteria).

Reviewer trail: read the plan from disk; verified every load-bearing
line-number claim against the real files (`state-layout.md`, `adr-002`, design
§3.4/§4.1/§5.3/§8, `roadmap.md` 1.2.6 and 6.2.3, `scripting-standards.md`,
`audit-1.2.2.md`, `test_interrogate_gate.py`, `Makefile`, `AGENTS.md`). Skills:
`logisphere-design-review`.

## Blocking

1. **Self-contradictory acceptance criterion (Purpose, lines 57-58).** The plan
   states success is observable via
   `grep -rn 'tomli_w' skill/ docs/adr-002* docs/novel-ralph-harness-design.md`
   returning **nothing**. That command cannot return nothing after the work,
   because WI2 *deliberately keeps* the truthful "is removed" sentences, both
   of which contain the literal token `tomli_w`:
   - `docs/adr-002-toml-round-trip-tomlkit.md:77` ("the failed `tomli_w` snippet
     is removed from the reference material") — WI2 explicitly leaves line 77.
   - `docs/novel-ralph-harness-design.md:466` ("The failed `tomli_w` snippet in
     the current reference is removed.") — WI2 explicitly leaves it.
   This contradicts the plan's own (correct) final cross-document check at
   lines 588-591 ("expect: no output from skill/; design and ADR show only
   truthful references"). The danger is concrete: an implementer who treats
   line 57-58 as the acceptance gate, sees the grep return two matches, and
   "fixes" it by deleting the truthful sentences would re-open the inaccuracy
   this task closes and exceed scope. Fix: scope the "returns nothing" claim to
   `skill/` only (or to the absence of the *snippet*, not the word), and align
   it with the lines 588-591 wording.

## Advisory (non-blocking)

- Design §5.3 "is removed" verb sits on line **467**; the sentence begins on
  466.
  The plan's "§5.3 line 466-467" (WI2) spans the sentence correctly, and its
  note reconciling the audit's `:464` is fair. No change required, but
  "466-467" is the right citation throughout (the Context block at line 284
  says "line 466", which is the sentence start — acceptable).
- The WI3 guard reads only `state-layout.md`; the optional ADR-002
  cross-document
  assertion is sound and appropriately tolerant. Keeping the guard
  substring-specific to `tomli_w` is justified by scope; the residual-risk note
  (a future `tomlkit` hand-edit passing green) is honestly recorded and
  correctly deferred to 6.2.3.

## What checks out (no action)

- Scope boundary verified: roadmap 1.2.6 (124-131) owns this removal; 6.2.3
  (452-460) and design §8 (655-666) own the SKILL.md:107, done-predicate, and
  `state-layout.md:38` `plan.md` defects — none overlap.
- Delete-vs-rewrite fork correctly resolved to *delete*: design §4.1 (248-249)
  eliminates direct editing of `state.toml`; a `tomlkit` rewrite would
  re-demonstrate the forbidden pattern.
- Line facts verified: snippet at 226-238, `import tomli_w` at 229,
  `tomli_w.dump`
  at 235; lines 224/240 carry no `state.toml.new` token; line 61 is the sole
  preserved `state.toml.new` mention; the four-item renumber to `1. 2. 3. 4.`
  is the only coherent post-deletion list. The round-2 fix of the round-1
  BLOCKING preserve-vs-rewrite contradiction is genuine and correct.
- No locked-library memory claims: the Decision Log correctly records no cuprum
  API (verified against design §4 lines 240-241 — cuprum only where a command
  shells out; none in v1) and no new dependency. The guard test is pure
  `pathlib`, mirroring `test_interrogate_gate.py`. No Cyclopts / pytest-timeout
  / pytest-xdist / uv behaviour is asserted, so nothing needs firecrawl
  citation.
- Gates match the Makefile: `make all` = build check-fmt lint typecheck test;
  `make test` = `pytest -v -n $(PYTEST_XDIST_WORKERS)` with default `auto` (so
  the plan's "-n auto" resolves correctly); `markdownlint` and `nixie` exist.
- Work items are atomic, ordered (WI1 removal → WI2 truthful → WI3 lock),
  independently committable, and each carries its own validation. Test
  placement (top-level `tests/`), en-GB Oxford spelling, and 100% interrogate
  docstring coverage all conform to AGENTS.md.
