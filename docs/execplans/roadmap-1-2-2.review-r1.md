# Logisphere design review — roadmap 1.2.2 ExecPlan, round 1

Verdict: REVISE. One blocking defect (B1) plus several advisory items.

## Verified empirically (plan claims that hold)

- `tomlkit` is declared in `pyproject.toml` `[project.dependencies] =
  ["cyclopts", "tomlkit"]` and locked to `0.15.0` in `uv.lock` (lines 639-640).
- Synced env imports `tomlkit` and reports `__version__ == "0.15.0"`;
  `tomlkit.__version__` is a valid attribute.
- The round-trip behaviour the test asserts is real against the locked
  version: `dumps(parse(SRC)) == SRC` byte-for-byte; a value edit through the
  document model preserves the standalone and inline comments and changes the
  target value. All four sub-assertions verified.
- Makefile targets match the plan: `all: build check-fmt lint typecheck test`;
  `build = uv sync`; `audit = uv run pip-audit`; `test = uv run pytest -n auto`.
- No unused-dependency gate exists (`deptry` absent; `pip-audit` is vuln-only).
  The "confirmation test makes the dependency load-bearing" rationale holds.
- The `tomli_w` snippet is genuinely still present at
  `skill/novel-ralph/references/state-layout.md:229,235`.
- Design §5.3 (line 465) and ADR 002 "Decision outcome" (line 77) both assert
  the snippet "is removed" — an overstatement, as the plan says.
- ADR 002 "Migration plan" (lines 91-92) does split 1.2.2 (add) from 2.2.1
  (exercise), supporting the confirmation/property-suite boundary.

## Blocking

### B1 — Work Item 2 invents a false cross-reference; 6.2.3 does **not** own the snippet removal

The plan's Constraints, Decision Log, Surprises, and Work Item 2 all assert
that "design §8 explicitly assigns the `state-layout.md` prose corrections /
the `tomli_w` snippet removal to roadmap task 6.2.3". This is false.

Design §8 (lines 644-664) enumerates exactly three defects owned by 6.2.3:
the `SKILL.md:107` phase mislabel, the two-source done predicate, and the dead
`state-layout.md:38` `plan.md` spec. Roadmap task 6.2.3 (lines 424-432) lists
the same three and nothing else. The `tomli_w` snippet removal is assigned to
6.2.3 nowhere in `docs/` (`grep -rn tomli_w docs/` confirms: every other hit is
in the execplan itself). Its removal is, in fact, currently **unassigned** in
the roadmap.

Consequence: Work Item 2 would rewrite design §5.3 and ADR 002 line 77 to
forward-reference 6.2.3 as the owner of a task 6.2.3 does not own — injecting a
false reference into the very documents the plan claims to keep truthful. This
inverts the task's stated purpose.

The underlying observation (the "is removed" claim is premature) is valid and
worth fixing. But the fix must not assert ownership that does not exist.
Required: either (a) drop Work Item 2 from this task entirely and raise the
unassigned-ownership gap to the roadmap owner; or (b) correct the design/ADR
claim to a neutral statement that the snippet's removal is **pending / not yet
scheduled** (no manufactured 6.2.3 reference) AND get the snippet removal
explicitly assigned to a roadmap task first. As written, every variant of Work
Item 2 in the plan points at 6.2.3 and is therefore wrong.

## Advisory

### A1 — Work Item 2 is scope creep against the roadmap success criterion

Roadmap 1.2.2 success (line 102) is narrow: "`make test` and the quality gates
in AGENTS.md pass against the extended dependency set." Doc reconciliation of a
design/ADR overstatement is not within that criterion. Even with a correct
ownership story, folding a documentation-truth fix into a dependency-confirm
task couples two unrelated concerns. Prefer raising it separately. (Advisory,
because AGENTS.md "keep docs truthful" gives it a defensible home — but the
false-reference defect B1 must be resolved regardless.)

### A2 — ADR 002 internal inconsistency left half-fixed

ADR 002 line 22 (Context) says the reference "carries" the snippet (present),
while line 77 (Decision outcome) says it "is removed" (past). The plan only
touches line 77. If Work Item 2 proceeds in any form, reconcile both so the ADR
is internally consistent, or the document still contradicts itself.

### A3 — Version pin is a maintenance tripwire, accept consciously

`assert tomlkit.__version__ == "0.15.0"` couples the test to the lock floor.
The plan argues this is intentional (a tripwire for ADR 002's major-version
regression risk) and the `# why:` comment documents the lockstep update. This
is a reasonable, eyes-open choice — recorded here so a future reviewer does not
"helpfully" relax it to `>=`.

### A4 — Three behaviours per one `# why`-annotated test module is fine

Work Item 1 is atomic, ordered, testable, and self-contained. No defect.
