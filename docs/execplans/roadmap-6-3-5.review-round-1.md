# Logisphere design review — roadmap 6.3.5 ExecPlan (Round 1)

Verdict: REVISE (proceed-with-conditions once blocking defects are closed).

Reviewer trail: `docs/novel-ralph-harness-design.md` §3.2/§3.4;
`docs/adr-003-shared-interface-contract.md`; `docs/adr-001-...`;
`docs/scripting-standards.md` lines 600-688; `docs/developers-guide.md` line
589; `AGENTS.md` lines 18/24-27/135-165; `docs/execplans/roadmap-6-3-1.md`
(Decisions D6/D7/D8); read of real source for every cited boundary; cuprum
surface corroborated in-tree against
`tests/steps/per_chapter_loop_installed_support.py`.

## Verified accurate (the plan's research holds)

- All eight `{exc}` boundary line-numbers and current strings match source:
  `novel_state.py:156`, `_recount.py:93`, `_wordcount.py:99`,
  `_novel_done.py:92`, `_desloppify.py:210`, `_compile.py:141` & `:211`,
  `_state_mutators.py:146`.
- The formatter's home (`_state_load.py`, imports only from
  `state`/`contract.runner`) cannot form an import cycle; re-export through
  `novel_state` mirrors `_state_input_error`. Sound.
- cuprum is untouched; the behavioural proof is in-process (the
  `state_input_message_bdd` template uses no cuprum). No firecrawl needed; no
  uncited locked-library claim is load-bearing.
- Test templates exist (`tests/test_state_input_message_{unit,bdd,parity}.py`,
  `tests/features/state_input_message.feature`). The matrices carry only
  `_USAGE_ARM`/`_STATE_ARM` (prefix "no novel working/ found in"), no
  draft-read arm — so D5 (new suite, not a matrix edit) is correct.
- The direct assertions to refresh exist verbatim: `test_compile_unit.py:295`
  (`match="cannot read chapter drafts"`), `test_desloppify_sourcing.py:118`.

## Blocking defects (return to planner)

### B1 — Work item 4's red→green guard does not exist

The plan asserts `tests/test_complete_final_pass_unit.py` line 116 carries a
structurally-incomplete *message* assertion to refresh, and lists "the
refreshed structurally-incomplete assertion fails before this item and passes
after" as Work item 4's validation. The real test
(`test_incomplete_state_exits_three`) asserts only
`code == ExitCode.STATE_ERROR` and `envelope["ok"] is False`. The string
`"state is structurally incomplete"` is asserted in **no** test anywhere (it
appears only in that test's docstring and in production code). Work item 4
therefore has **no pre-existing red→green message guard**; its only proof is
the new behavioural suite in Work item 5. Fix: correct Work item 4 to state
this (and either add a message-text unit assertion as the red→green guard, or
pin the proof explicitly to Work item 5), and stop describing line 116 as an
assertion to "update".

### B2 — Dangling Decision D6; the `_compile` write-fault tail is unresolved

The plan references "Decision D6" (lines 317 and 453) to resolve whether the
atomic-write tail `_compile.py:150` (`cannot write {_COMPILED_REL}: {exc}`) is
in scope. The Decision Log defines only D1-D5; **there is no D6 in this plan**
(the other D6 mentions point at the *6.3.1* plan's leaf-split decision). That
tail genuinely interpolates raw `{exc}` on the exit-3 channel, so the scope
question is real. Fix: add the missing decision that either (a) scopes the
write-fault tail out with a stated rationale (it is a *write* fault, not a
draft-read, and arguably wants its own write-remedy prose, not "inspect the
draft"), or (b) brings it in with a write-appropriate formatter — and remove
the dangling forward references.

### B3 — Semantic mismatch: a state-document-coherence fault routed through a *draft-read* formatter

6.3.1 Decision D8 explicitly reasoned that `_state_view_or_state_error` reports
a *parsed-but-structurally-incomplete* `state.toml` — "not a failed load" —
whose remedy "differs", and warned future reviewers not to conflate it with the
load message. 6.3.5 now routes it through `_draft_read_error`, whose D2 message
"names the `working/` tree" and whose Interfaces docstring frames it as "a
corrupt/unreadable draft or an incoherent state document". A structurally-
incomplete `state.toml` is neither a draft nor a generic
artefact-under-working/; the natural home is `_state_input_error`'s
**present-but-corrupt arm** ("`<path>` is unreadable or corrupt; inspect and
repair it"), which already emits the exact inspect/repair semantics the roadmap
asks for and which the plan never considers. The roadmap mandates an
"inspect/repair remedy", not the draft-read formatter specifically. Fix: either
(a) route the view-derivation boundary through `_state_input_error`'s corrupt
arm (passing `state_path()`), reusing 6.3.1's machinery and respecting D8's
distinction; or (b) justify, against D8, why the draft-read formatter is the
right home despite the fault being a state.toml- coherence fault rather than a
draft fault — and rename the formatter and its docstring so "draft-read" no
longer mislabels a state-document fault.

## Advisory (non-blocking)

- A1: Work item 4 step 1 says "import `working_dir` from `novel_state`, already
  available in this module" and calls `working_dir()`. In `_state_mutators.py`
  it is imported **as `_working_dir`** (line 43). The literal call
  `working_dir()` would `NameError`. Use `_working_dir()`.
- A2: Work item 2 step 5 says route both `_compile` tails "using each function's
  resolved `root`". `check_compiled` has **no** `root` local — it calls
  `compiled_matches_drafts(state, working_dir())`. The implementer must pass
  `working_dir()` there.
- A3: Parity (Work item 5 step 2). The existing parity test asserts
  byte-for-byte
  identity because both load boundaries report the **same** cwd. The draft-read
  boundaries pass **different** `reported_dir` values and the message names the
  directory, so byte-for-byte identity holds only under fixed-cwd fixtures.
  Commit to the formatter-owned-remedy-substring parity instead of implying
  byte-for-byte identity across boundaries.
- A4: If B3 is resolved by keeping a single draft-read formatter that also
  serves
  the structurally-incomplete case, the formatter name `_draft_read_error` and
  its docstring should be generalised (e.g. `_present_but_faulted_error`) so
  the vocabulary does not lie about what it covers (Pandalump: names describe
  intent).
