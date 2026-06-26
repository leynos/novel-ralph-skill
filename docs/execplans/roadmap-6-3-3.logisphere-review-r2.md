# Logisphere design review — roadmap 6.3.3, round 2

Adversarial pre-implementation review of
`docs/execplans/roadmap-6-3-3.md` (DRAFT, round 2). Read from disk; every
load-bearing claim re-verified against real source, the live lint gate, and the
official uv docs (firecrawl). Trail signposted at the end.

## Verdict

⚠️ **Proceed with conditions.** The plan is implementable and design-conformant
as written. Both round-1 blocking points are genuinely resolved and independently
re-verified. No new blocking defects. Two precise advisory fixes would harden it;
neither blocks implementation.

## Independent verification of round-2 claims

Every cited source line was checked against the actual file in the worktree:

- `is_ok` returns `code is ExitCode.SUCCESS` — confirmed
  (`novel_ralph_skill/contract/exit_codes.py`, the `return` line).
- The envelope binds `ok=is_ok(code)` — confirmed
  (`novel_ralph_skill/contract/envelope.py`, in `build_envelope`).
  Together these prove `ok` is `true` iff exit 0, so `ok` cannot carry the
  1-versus-4 distinction. The plan's round-2 pivot is correct.
- `--help`/`--version` exit 0 with no envelope — confirmed in both
  `contract/runner.py` ("it exits `0` with no envelope") and
  `commands/novel.py` ("exit `0`, no envelope").
- ADR-003 Table 2 (five-code table) and the six-field envelope list —
  confirmed verbatim at the cited lines.
- Design §3.2 exit-code table and the "load-bearing 1-versus-4" statement —
  confirmed; the design itself says code 1 is "the steady-state 'not finished'
  the loop expects every turn".
- Developers' guide "The shared JSON envelope" and "Disambiguated exit codes"
  ("The 1-versus-4 distinction is load-bearing") — confirmed at the cited
  ranges.
- SKILL.md "Done predicate (short form)" pointer pattern, "Setup" install line
  `uv tool install --from . novel-ralph-skill`, and the four-requirement
  "Harness contract" — all confirmed; the precedents the plan leans on are real.
- markdownlint baseline — reproduced live: exactly one error,
  `docs/developers-guide.md:149 MD012/no-multiple-blanks`, two blank lines at
  148-149 before `### The cross-command...`. Tree clean but for this execplan.
- uv semantics — re-scraped <https://docs.astral.sh/uv/concepts/tools/> via
  firecrawl. The plan's three quotes match the live docs verbatim: "use the
  installed version by default"; "upgraded via `uv tool upgrade`, or re-created
  entirely via subsequent `uv tool install` operations"; "The `--force` flag can
  be used to override this behavior." The plan does **not** claim a plain
  re-install upgrades. Locked-library claim properly cited and accurate.

## Panel findings

🐼 Pandalump (structural integrity): Work items are atomic, ordered, and
independently committable; the ordering (lint green → contract table → discipline
that references it → install note) is correct.

🐈🧇 Wafflecat (alternatives): The inline-table-plus-pointer choice is explicitly
decided with a bounded pure-pointer fallback; both are roadmap-conformant
("`SKILL.md` (or a reference it links once)"). No structurally-different
alternative remains uncovered.

🐝 Buzzy Bee (scaling): N/A — documentation-only. The only scale dimension (277
Markdown files through the gate) is accounted for.

☎️ Telefono (contracts): The contract documentation is correct and the `ok`
trap is closed. See advisory 1 for a roadmap-text tension the plan should name.

🐶 Doggylump (failure modes): Reflow churn, baseline drift, and the iteration cap
are all handled with escalation triggers. `make nixie` no-op is correctly
predicted (no Mermaid added).

🦕 Dinolump (long-term viability): The single-source discipline (convenience
restatement + canonical pointer) is the right posture to prevent the fourth
drifting copy that step 6.3 exists to eliminate.

## Pre-mortem

- Scenario A — drift reintroduced. A later contract change edits ADR-003 and the
  developers' guide but not SKILL.md's inline restatement. Mitigated by the
  plan's mandatory "mark as a convenience restatement of the cited canonical
  source" labelling and the conditional Work item 4 note. Acceptable.
- Scenario B — uncaptioned table ships. markdownlint does not enforce captions
  (style-guide-only), so a missing caption passes the gate. Mitigated by the
  explicit caption instruction, but weakened by precedent — see advisory 2.

## Advisories (non-blocking; fold in if cheap)

1. ☎️ Roadmap-text divergence is silent. The roadmap body (lines 2170-2173)
   itself says "check the exit code **and** the envelope `ok`; a non-zero exit
   (**or** `ok:false`) is a stop-and-fix." That literal wording is wrong: it
   would halt on benign exit 1. The plan correctly diverges to exit-code-
   authoritative gating but never states that it is *correcting the roadmap's own
   loose acceptance wording*. The roadmap success criterion (lines 2176-2178)
   says only "check-exit-code discipline", so there is no contradiction with the
   binding criterion — but an implementer cross-reading the roadmap body could be
   confused. Add one sentence to the Decision Log noting the plan honours
   ADR-003/design §3.2 over the roadmap body's looser "or ok:false" phrasing,
   which conflates the two signals.

2. 🦕 Existing SKILL.md table is uncaptioned. The current "Reference files" table
   (SKILL.md ~line 98) carries no caption, contrary to the style guide
   (caption every table). The plan correctly instructs the implementer to caption
   the new table, but the in-file precedent is contrary, so the new captioned
   table will sit beside an uncaptioned one. Note this in Work item 1 so the
   implementer follows the style guide (caption) rather than the local
   precedent, and does not "tidy" the existing table under cover of this task
   (out of scope).

3. 🐼 Work item 0 line-label inconsistency. Constraints (line 86-88) calls line
   148 "the second blank"; Concrete steps (line 808-809) calls line 148 "the
   first of the pair". Both say delete line 148, so the action is unambiguous and
   either deletion clears MD012 — but the labels contradict. Align the wording to
   avoid an implementer second-guessing which blank to remove.

## Trail

Skills: `logisphere-design-review` (this), `firecrawl` (uv doc re-verification).
Source of truth consulted: `docs/roadmap.md` (2164-2178),
`docs/adr-003-shared-interface-contract.md` (43-95),
`docs/novel-ralph-harness-design.md` §3.2 (203-233),
`docs/developers-guide.md` (144-152, 522-595),
`docs/documentation-style-guide.md` (35-65), `.markdownlint-cli2.jsonc`,
`skill/novel-ralph/SKILL.md` (front matter, Setup, Harness contract, Reference
files, Done predicate), and `novel_ralph_skill/contract/{exit_codes,envelope,
runner}.py`, `novel_ralph_skill/commands/novel.py`. Live `make markdownlint` and
a firecrawl scrape of the uv tools docs corroborated the baseline and install
claims respectively.
