# Logisphere design review — roadmap 1.2.14 (round 1)

Adversarial pre-implementation review of `docs/execplans/roadmap-1-2-14.md`.
Verdict: **Proceed with conditions**. The plan is sound and unusually
well-evidenced; the blocking items below are scope/gate refinements, not
structural rework. Trail: `logisphere-design-review` skill; roadmap.md tasks
1.2.14/1.2.16/1.2.17; ADR 007; `names.py`; `novel.py`; `make markdownlint`,
`make nixie`, `uv run novel --version` run live in the worktree.

## What was verified against ground truth (not the planner's summary)

- `pyproject.toml` ships exactly `novel = …` (one `[project.scripts]`). ✓
- `names.py` `SUBCOMMAND_NAMES` is exactly the five spaced forms; the plan's
  surface vocabulary is correct. ✓
- `uv run novel --version` exits 0 and prints `0.1.0` (no envelope). The Setup
  install-check replacement is empirically valid. ✓
- Grep counts: design 44 hyphenated-only / 65 incl. desloppify+wordcount;
  SKILL 33 occurrences over 26 lines; `desloppify-checklist` design 1 / SKILL 3.
- `make markdownlint` (260 files) and `make nixie` are currently green, so the
  plan's gates are runnable as-is.
- §4 is genuinely mixed (headings spaced, body nouns hyphenated) — the plan's
  "do not trust §4 body" caveat is justified.
- Roadmap 1.2.17 success criterion explicitly preserves the noun-form
  `desloppify` pass; merged 1.2.16 retained a bare code-identifier
  (`installed_desloppify`) while converting invocations. The plan's
  noun-vs-script decision is vindicated by the roadmap and by merged precedent.

## Blocking defects (return to planner)

B1. **Scope enumeration is incomplete: §2.3 and §3.1 carry hyphenated
    references the plan never names.** Lines 112 and 115 (`novel-state`
    validator, `novel-done` returns) sit in **§2.3 Verification scope**; line
    148 (`"command": "novel-done"`) sits in **§3.1 Output modes**. Work item 2's
    narrative sweeps "§3 tables and prose, §4 body, §5, §9, §10" and the Purpose
    names "§3 … §4 body, §5, §9, §10" — neither lists §2.3 or §3.1. The
    work-item-1 grep and the surface gate will surface these, so it is not
    silent, but an implementer following the section list will miss them and hit
    a gate failure. Add §2.3 and §3.1 to the convert scope explicitly.

B2. **The JSON envelope `command` field is an un-named, contract-sensitive
    convert target.** Lines 148 (§3.1) and 358 (§4.2) contain
    `"command": "novel-done"`. The multiplexer stamps `"novel done"` (spaced)
    per `ENVELOPE_COMMAND_NAMES`/`SUBCOMMAND_NAMES`. These must become
    `"command": "novel done"`, verified character-for-character against
    `names.py`. The plan converts command literals but never calls out the
    envelope `command` field, where exactness matters most. Add an explicit
    anchor and tie it to `names.py`.

B3. **The surface gate is asymmetric: it cannot catch over-sweep of an
    operation noun.** Work items 3/5 subtract `novel (state|done|compile|
    desloppify|wordcount)` before printing survivors, so an over-swept noun
    (`desloppify` → `novel desloppify`) is invisible to the gate. Over-sweep is
    the plan's own higher-likelihood Risk 2, yet the only mechanical defence
    runs in the under-sweep direction; over-sweep is defended solely by human
    classification in work item 1. The Outcomes section asserts "operation-noun
    mentions are intact at their original counts" but **no gate checks this
    count**. Add a preserve-noun count/membership assertion: after subtracting
    the named convert anchors, pin the expected surviving bare-noun count
    (current baseline: design 14 bare `desloppify` + 7 bare `wordcount` minus
    the convert anchors; SKILL per work-item-1 classification) and assert the
    post-sweep survivor list equals it. Without this, an over-sweep merges green.

## Advisory (non-blocking)

A1. Purpose §1 (line 28-32) miscites its own evidence: it says the design
    "carries 44 lines … (grep … returns 44 **including** desloppify/wordcount
    hits)". 44 is the hyphenated-**only** count; including desloppify+wordcount
    the count is 65. Correct the parenthetical so the evidence is trustworthy.

A2. SKILL.md hit-line count is 26, not the "23 lines" stated in Purpose §2 and
    inherited from the roadmap wording. Minor, but the plan should state the
    figure it actually verified.

A3. Line 924 ("`desloppify` exits 2") is classified preserve-noun but reads as
    a runtime-contract statement (invocation-adjacent), making it the most
    debatable preserve anchor. The plan's Tolerance (stop-and-record on
    ambiguity) covers it; flag it in the work-item-1 record as a knowingly
    close call so the implementer does not silently flip it.

A4. Mermaid: `B[desloppify: detect]` retains a colon inside the label and is
    preserved — valid. `G[novel state recount / novel done / novel wordcount]`
    is valid Mermaid. No issue; the plan's Mermaid reasoning is correct.

## Pre-mortem (Doggylump)

Six months on, the plausible failure is **a silently over-swept operation
noun** that escaped review: the design now reads as though `desloppify` is
invoked everywhere it is merely named, the merged docs drift from the 1.2.17
reference-file discipline, and no gate ever flagged it because converted forms
are subtracted before survivors print (B3). Mitigation: the preserve-noun count
gate in B3. Secondary failure: an implementer trusts work item 2's section list,
misses §2.3/§3.1 (B1), the gate fails, and the "atomic, ordered" promise of the
two commits is broken mid-stream — mitigated by B1.

## Alternatives checkpoint (Wafflecat)

The plan's file-by-file, gate-behind-each-commit structure is the right shape
for a documentation sweep; no structurally different alternative improves on it.
The one worth noting: rather than human-classify every bare noun, derive the
preserve set mechanically from the merged 1.2.16/1.2.17 outputs (the guides and
reference files already encode the noun-vs-script verdict for the same tokens),
then diff. This trades a little setup for a reproducible oracle and directly
supplies the count baseline B3 needs. Not required, but it strengthens the gate.

## Library / locked-dependency check

No cuprum, Cyclopts, pytest-timeout, pytest-xdist, or uv API is exercised — the
task touches no Python. The only library-behaviour claim
(`novel --version` → exit 0, no envelope) was verified live, not from memory.
No uncited memory-based claim remains. ✓
