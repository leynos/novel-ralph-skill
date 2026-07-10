# Logisphere design review — roadmap 2.3.5 ExecPlan (Round 1)

Verdict: REVISE. The provenance, ADR mapping, no-code-change rationale, and
D-CUPRUM/D-NO-FIRECRAWL decisions are all verified true against source. But the
plan's load-bearing deliverable — the Work item 3 regression test — rests on a
false token-arithmetic premise and is, as specified, unrealisable.

## Blocking defects

### B1 (Pandalump / Telefono): the "compiled tokens diverge from drafted sum" premise is false for a byte-exact compiled.md

`DRAFT_SEPARATOR = "\n\n"` (`compile_model.py:30`) is whitespace, and
`str.split()` collapses every whitespace run. Therefore, for any byte-exact
`concatenate_drafts(bodies)` output:

    len(concatenate_drafts(bodies).split()) == sum(len(b.split()) for b in bodies)

always — separator joins and trailing/leading whitespace never change the token
count. Verified empirically across boundary cases. The plan asserts the opposite
in Purpose (lines 17-20), Constraints, Risk #2/#3, the Decision Log, and the
Work item 3 fixtures ("the difference arising from the `\n\n` separator join
and/or trailing whitespace").

`_check_compiled_matches_drafts` (`disk_evidence.py:173-191`) does a **byte-exact**
compare: `compiled.read_text() == concatenate_drafts(present_bodies)`. The only
`compiled.md` that does NOT fire that REFUSE is one byte-identical to the
concatenation — whose token count provably equals the drafted sum.

### B2 (Doggylump): Work item 3 case 2 / Risk #3 orthogonality is self-contradictory

Case 2 requires simultaneously: (a) `compiled.md` "absent or an exact
`concatenate_drafts`" so `compiled-matches-drafts` does not REFUSE, and (b) the
tree's "`compiled.md` token count diverges from the drafted sum." By B1 these
are mutually exclusive. The plan's own Risk #3 says "If the orthogonality cannot
be realized, escalate" — it cannot, as written. Case 2 can still test
recount==reconcile agreement, but the "compiled token count diverges" leg must
be dropped from the case-2 tree (it belongs only to a tree with a deliberately
non-concatenation `compiled.md`, which forces REFUSE and so cannot reach the
RECOUNT write — see B3).

### B3 (Pandalump): Work item 3 case 1 precondition assertion would error on arrange

Case 1 instructs constructing a `compiled.md` whose token count differs from the
drafted sum "from the `\n\n` separator join and/or trailing whitespace" and then
"assert this precondition so the test cannot pass vacuously." With a
concatenation-derived `compiled.md` that precondition is FALSE, so the arrange
assertion fails and the test errors. Case 1 is only salvageable by giving
`compiled.md` an extra **non-whitespace** token (recount ignores `compiled.md`,
so recount still writes the drafted sum) — but the plan must say so explicitly,
because that `compiled.md` is then a non-concatenation that would REFUSE under
`check`/`reconcile`. recount does not run the disk-evidence detector, so case 1
is fine for recount in isolation; the plan must stop attributing the divergence
to the separator and state the real mechanism (an injected extra token).

### B4 (Wafflecat / structural): the plan does not name the actually-divergent quantity

The genuine, design-faithful divergence is not token-count vs drafted-sum; it is
that a **stale or hand-edited** `compiled.md` (different words, dropped/added
content) has a token count unrelated to the drafts — and that is exactly the
`compiled-matches-drafts` REFUSE case. The decision the task settles ("compiled
tokens are never a `current` source") is sound and already implemented; but the
test that "pins" it must be rebuilt around the real distinction:

- recount/reconcile both write `sum(by_chapter)` regardless of `compiled.md`;
- a `compiled.md` that diverges (in bytes) is surfaced as the
  `compiled-matches-drafts` finding (exit 4), never a `current` source.

The "neither equals the compiled token count" assertion is only meaningful when
the test deliberately makes the compiled token count differ via injected
non-whitespace content — which simultaneously is the REFUSE tree. The plan must
reconcile these two facts into a coherent, non-contradictory fixture matrix.

## Required revisions

1. Strike every claim that the `\n\n` separator join or trailing whitespace can
   make `len(compiled.split()) != sum(len(draft.split()))`. Replace with the
   correct statement: for a byte-exact concatenation the token counts are equal;
   divergence requires a `compiled.md` that is not the concatenation (extra or
   altered non-whitespace content), which is precisely the
   `compiled-matches-drafts` REFUSE condition.
2. Rewrite Work item 3 so case 1's "compiled token count" leg uses an injected
   non-whitespace token (and drop the false separator/whitespace precondition);
   keep case 1 scoped to recount, which never reads `compiled.md`.
3. Rewrite case 2 to assert only recount==reconcile agreement on a stale-table /
   coherent-(or absent)-`compiled.md` tree; remove the impossible "compiled
   token count diverges" requirement from that tree.
4. Fold case 1's "not the compiled token count" assertion into case 3 (the
   REFUSE tree), since that is the only tree where a divergent compiled token
   count legitimately exists, and prove there that `current` is untouched.
5. Re-state Risk #2/#3 mitigations against the corrected arithmetic.

## Verified-sound aspects (no action needed)

- Provenance: design §4.1 (lines 283-290), §5.2 invariant 3 (line 466), §5.4 +
  v1-scope subsection all confirmed; the prose edits proposed are additive and
  do not perturb the RECOUNT/REFUSE dispositions.
- Both contradiction sites confirmed verbatim: `state-layout.md:114`,
  `schema.py:237`. Dev guide line 585 is the correct canonical wording.
- D-NO-CODE-CHANGE: `recount_words` returns `sum(by_chapter.values())` by
  construction (`wordcount.py`); `disk_word_counts` delegates to it
  (`disk_evidence.py:244`); reconcile RECOUNT carries `recounted_current` from
  the same source. recount and reconcile genuinely share one helper.
- D-CUPRUM: verified no `cuprum`/`sh`/`subprocess` import in `wordcount.py`,
  `_recount.py`, `disk_evidence.py`, `reconcile.py`, `_reconcile.py`. No cuprum
  behaviour is asserted, so cuprum source need not be cited. Correct.
- D-NO-FIRECRAWL: the only external-library behaviour relied on is
  `str.split`/`tomlkit`/`pytest`, all standard and locked. No uncited
  memory-based claim about Cyclopts, pytest-timeout/xdist, or uv is load-bearing
  — verified none appears. Acceptable.
- Completeness of the two-site reconciliation: the other "(or sum of drafts)"
  hits are execplan history and the roadmap task text quoting the old wording;
  leaving them is correct. The acceptance criterion correctly targets the two
  live sites plus the design prose.
