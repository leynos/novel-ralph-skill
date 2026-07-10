# Logisphere design review — roadmap 1.2.8 (Round 1)

Verdict: REVISE (proceed with conditions once blocking defects are fixed).

Reviewer: adversarial design panel (Pandalump, Wafflecat, Buzzy Bee, Telefono,
Doggylump, Dinolump) plus pre-mortem and alternatives checkpoint.

The plan's core approach — a fence-scoped, `re`-based static scanner that
forbids any direct `state.toml`-write recipe inside an executable code fence —
is sound and design-conformant (design §4.1, ADR-002). The deterministic
boundary is respected (pure text predicate, no judgement). But several factual
claims about the protected file are wrong, and one instruction violates
AGENTS.md's committing policy. These must be corrected before implementation.

## Blocking defects

1. **Commits a gate-failing change (AGENTS.md violation).** Work item 1
   instructs committing "red" tests that fail `make test` ("this commit carries
   failing *new* tests by design"). AGENTS.md "Change quality and committing"
   (lines 100, 108) states: "Only changes that meet all quality gates should be
   committed" and "Do not commit changes that fail any quality gate."
   `make test` is a gate. The plan only offers this as a conditional ("if your
   gating policy forbids committing red tests, fold items 1 and 2"). The repo
   policy is not optional: fold the red tests and the predicate into a single
   commit (TDD red-then-green stays within one working session and one commit).
   Remove the separate "Add red tests…" commit and its caveat.

2. **False claim: an atomic-write `text` *fence* at lines 212-228.** The plan
   (Risks; Surprises & discoveries; Context; Work item 1 test #2) repeatedly
   asserts that `state-layout.md` lines 212-228 contain "a `text` fence"
   "describing the atomic rename discipline". This is wrong. Line 212 is a
   Markdown heading `## Atomic writes`; lines 214-228 are prose plus a numbered
   list. There is **no fenced code block** there. The two real `text` fences
   are at 234-243 (Initialization) and 249-257 (Resumption); neither describes
   the write/rename discipline. The atomic-write language the guard must not
   flag lives in **prose** (lines 60-61 and 214-228), which is already outside
   any fence and therefore already safe under fence-scoped scanning. Correct
   every line-number and "text fence" assertion, and rewrite Work item 1 test
   #2 to feed the real prose (not a non-existent fence) — or relabel it as a
   synthetic fixture, but do not claim it mirrors the file.

3. **`make all` does not run audit / markdownlint / nixie.** The Makefile
   defines `all: build check-fmt lint typecheck test` (Makefile line 28). It
   excludes `audit`, `markdownlint`, and `nixie`. The plan says "or simply
   `make all` if it chains them" (Work item 2) and "a final `make all` to
   confirm the whole suite is green end to end" / "Then a final `make all`"
   (Work item 3, Concrete steps, Validation). Following that as written would
   skip the audit and Markdown gates the same plan requires. Replace the
   "`make all` chains them" claims with the explicit sequence: `make all`
   followed by `make audit`, `make markdownlint`, `make nixie` (run
   sequentially, never parallel).

## Advisory (strongly recommended, non-blocking)

1. **Predicate spec is internally inconsistent on `open(`.** Decision Log (c)
   says "`open(` paired with `state.toml` and a `.write`"; Work item 2 step 3
   says "`open(` with a write mode". These differ and risk a false positive on
   a legitimate *read* of the file (e.g. a future validation example doing
   `tomllib.load(open("working/state.toml","rb"))` — `open(` + `state.toml`
   present, but read-only). Pin one rule: require a write signal (write mode
   such as `"w"`/`"a"`/`"x"`/`"wb"`, or a paired `.write(`/`.writelines(`), not
   bare `open(`. State it once and make the planted-recipe table include a
   read-only `open(... "rb")` / `tomllib.load` *negative* case that must NOT be
   flagged. This guards the green-on-current invariant against 6.2.3's prose
   rewrite, which may add read examples.

2. **6.2.3 collision mitigation rests on an unverified premise.** The plan
   assumes 6.2.3 may add a `novel-state` example fence. Roadmap 6.2.3 (lines
   468-476) actually says it points prose at the commands, reduces the
   done-predicate copies, and removes the dead `plan.md` reference — it does
   not promise a `novel-state` code fence. The positive test (a `novel-state`
   `sh` fence passes) is still worth keeping as a forward guard, but drop the
   claim that 6.2.3 "shows an example invocation"; frame it as defensive.

3. **Redirect/shell tokens need anchoring to the path to avoid noise.** The
   backstop and shell rules (`>`, `>>`, `tee`, `cat >`) must be tied to the
   `state.toml` path, else any unrelated future shell fence with a redirect
   trips them. The Decision Log already says "targeting the state file"; ensure
   the implementation and a negative test (a `sh` fence with `> /tmp/foo`
   passes) enforce that, so the rule is path-anchored, not redirect-anywhere.

4. **Captured-line-count / fixture provenance.** Because of defect 2, the
   "Surprises & discoveries" evidence ("listing the fences shows kinds
   text/toml/markdown only; no python or sh fence touches state.toml") is the
   *correct* basis for green-on-current — keep that — but delete the
   contradictory "text pseudocode fence describing the atomic rename discipline
   (lines 212-228)" sentence, which contradicts it.

## What is correct (do not regress in revision)

- Fence-scoped scanning over executable info strings
  (`python|py|sh|bash|shell|console`) is the right structural choice; it is the
  only approach satisfying both green-on-current and catch-real-recipes
  (Pandalump, Telefono concur).
- `re`-based scanner over a Markdown-AST dependency is justified under the
  no-new-dep constraint for one file with a closed fence grammar (Wafflecat's
  alternative — `markdown-it-py` AST — trades a dependency for negligible
  robustness gain here; reject it, but record why).
- Token surface (tomli_w historical, tomlkit.dump/dumps, raw write primitives,
  shell redirects, path-anchored backstop) is complete for the enumerable
  hand-edit forms; tomlkit 0.15.0 and read-only stdlib `tomllib` are correctly
  characterized (verified against pyproject/uv.lock).
- Keeping the two `tomli_w` substring tests as additive regressions is right.
- Not pre-empting 1.2.7's shared `conftest` keeps the task atomic — correct.
- No uncited memory-based locked-library behavioural claim requires
  firecrawl verification: the plan's pytest-xdist/timeout statements are
  limited to "they are in the locked dev set" (true), and the tests are pure
  in-process predicates with no xdist-sensitive fixtures.

## Pre-mortem (Doggylump)

- Six months on: a contributor adds a `python` example that *reads*
  `state.toml` to validate it; the over-broad `open(`/`.write(` rule flags it,
  `make test` goes red on a legitimate doc, and the contributor deletes the
  helpful example to get green. Prevention: defect 4 (write-signal, not bare
  `open(`; negative read test).
- Alternatively: 6.2.3 lands first and the line numbers this plan hard-codes
  drift; an implementer trusting the plan's "lines 212-228" wires a fixture to
  the wrong content and the test passes for the wrong reason. Prevention:
  defect 2 (stop citing fragile line numbers; assert by content/info-string).

## Alternatives checkpoint (Wafflecat)

Strongest alternative: parse with `markdown-it-py` to get exact fence
boundaries and info strings. Trades a new dev dependency (breaching the plan's
own dependency tolerance and AGENTS' lean-deps posture) for marginally more
robust fence detection on a single, well-formed file. Not worth it — the `re`
scanner is adequate provided the closing-fence and info-string capture is
tested against the real file. Rejecting the alternative is the right call.
