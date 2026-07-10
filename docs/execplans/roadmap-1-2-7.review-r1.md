# Logisphere design review — roadmap 1.2.7 ExecPlan (round 1)

Reviewer: adversarial Logisphere crew. Target:
`docs/execplans/roadmap-1-2-7.md` (DRAFT). Read from disk; claims verified
against real source, not the planner's summary.

## Verdict: ⚠️ Proceed with conditions

The design is sound and conformant. Every locked-library claim was
independently verified against real source (cuprum sibling checkout + installed
venv copy + official pytest-timeout PyPI page). No blocking defects. Two
advisory items below would tighten it but do not stop implementation.

## What was verified (and held)

- **cuprum 0.1.0 API** (against
  `/data/leynos/Projects/cuprum/cuprum/catalogue.py`
  and `.venv/.../cuprum/catalogue.py`): `ProgramCatalogue(*, projects=...)`
  keyword-only;
  `ProjectSettings(name, programs, documentation_locations, noise_rules)`
  frozen dataclass; `Program = NewType("Program", str)` with no validation;
  `.allowlist -> frozenset[Program]` is a real property; `UnknownProgramError`
  exists. The plan's `single_program_catalogue(...)` factory and its
  `.allowlist`-based unit test are expressible exactly as written. The
  absolute-path-program assertion (WI-2) is valid — `Program` is a bare `str`
  and the allowlist is the gate.
- **pytest-timeout 2.4.0 precedence** (against the official PyPI "Usage"
  section): ini `timeout` < `PYTEST_TIMEOUT` env < `--timeout` CLI < marker.
  `@pytest.mark.timeout(180)` supersedes the `timeout = 30` ini. The plan cites
  this, not memory. The refactor preserves the marker verbatim; no new
  xdist-timeout behaviour is introduced (the existing green suite already
  exercises it under `-n auto`).
- **Fixture-only approach is collection-safe.** I checked all four static-parse
  modules: every helper call (`_parse_scripts`, `_pyproject`, `_table`,
  `_state_layout_text`) happens *inside test method bodies*, never at module
  level or in `@parametrize`. Fixtures cannot be consumed at collection time —
  so the plan's "all fixtures, zero imports" design does not collide with any
  existing collection-time use. This is the make-or-break structural risk and
  it passes.
- **per-file-ignores glob** (`pyproject.toml:94`): `**/test_*.py` genuinely does
  not match `conftest.py`, so `S101`/`PLR*` apply there. The plan flags this
  and routes guards through `raise AssertionError(...)`. Conversely
  `tests/test_conftest_helpers.py` *does* match the glob, so its bare `assert`s
  are fine.
- **Audit findings** (`audit-1.2.{1,3,4,5,6}.md`) all exist and say what the
  plan
  claims. audit-1.2.3 Finding 2 explicitly proposes the conftest-fixture home
  and warns against the cross-module private import — the plan conforms. The
  Wafflecat alternative (`tests/_helpers.py`) is named in the audit and
  explicitly rejected in the plan's Decision Log with rationale.
- **Design boundary**: zero production-code change; the
  deterministic/judgemental
  boundary (`developers-guide.md` §"The deterministic/judgemental boundary") is
  untouched. The single-source-of-truth `commands/names.py` is preserved.
- Referenced files exist: `adr-006-...md`, `documentation-style-guide.md`,
  `contents.md`, all six audits.

## Crew findings

### Pandalump 🐼 (structure) — pass

Decomposition is clean: three atomic, independently committable WIs ordered by
dependency (static helpers → cuprum/resolver → docs). Boundaries match the
audit findings. The fixture-vs-import decision is the load-bearing wall and it
is correctly placed and justified.

### Wafflecat 🐈🧇 (alternatives) — pass

Two alternatives surfaced and dispositioned: (a) `tests/_helpers.py` importable
module — rejected (more surface than the audits asked, reintroduces imports);
(b) legitimizing the cross-module import via `tests/__init__.py` — rejected
(changes collection semantics for the whole suite; in Tolerances as an escalate
trigger). No stronger alternative exists for a behaviour-preserving test
refactor. 🟢 Improvement: the plan could note that `read_repo_text` as a
*callable-returning fixture* is itself a small design choice with a thinner
alternative (a `repo_text` session-cached value) — but the callable form is
needed because call sites read different files, so the choice is right.

### Buzzy Bee 🐝 (scaling) — n/a / pass

Session-scoping `project_root` and `pyproject` (parsed once) is the right call
under `-n auto`; each xdist worker parses once rather than per-test. No
fan-out, no unbounded anything. Correct.

### Telefono ☎️ (contracts) — pass with one advisory

The fixture surface is the new contract. Signatures are precise, no `Any`, and
pinned to the verified cuprum API. WI-3 records the consumption convention
(fixture-by-name, never import) — good contract documentation. Advisory below on
`toml_table`'s `Mapping` vs `dict` parameter typing.

### Doggylump 🐶 (failure modes) — pass

This is additive + refactor with `git revert` per WI; no data migration, no
runtime blast radius. The only "03:00" failure is a green-suite regression,
caught by `make all` per WI and the two `rg` structural gates after WI-2. The
POSIX-skip-count check (Risks) is the right tripwire for the one subtle
behaviour-drift path (catalogue/resolver move changing skip semantics).

### Dinolump 🦕 (long-term) — pass

conftest fixtures are mainstream pytest; zero exotic tech; bus factor
unaffected. WI-3 documents the convention so the seventh test module is cheap.
Conway-aligned (one repo, one test tree, one conftest).

## Pre-mortem (Doggylump)

1. **Most likely failure: a session-scoped fixture silently changes a skip/xfail
   count when the resolver moves.** Blast radius: one module's skip set.
   Mitigation already in plan: explicit skip-count verification on the POSIX
   host (Risks final entry; WI-2 go/no-go). Adequate.
2. **`interrogate` 100% trips on an undocstringed fixture.** Caught by
   `make lint`
   per WI. Mitigation in plan. Adequate.
3. **A future cuprum bump adds `Program` path validation and breaks the
   absolute-path e2e.** The plan adds a guard test pinning the bare-`str`
   behaviour (WI-2) so this fails loudly. Good forward-defence.

## Advisory (non-blocking)

1. **Citation drift, WI-1 "Documentation to read first" (line 310).** The plan
   cites `docs/developers-guide.md` "Quality gates"; there is no such heading.
   The quality-gate content lives under `## Local workflow` (lines 9-16). The
   Purpose section's references are otherwise accurate. Fix the pointer to
   "Local workflow" (or add the heading in WI-3) so the next agent doesn't hunt.
2. **`toml_table` parameter type.** The plan's signature box types the callable
   as `Callable[[Mapping[str, object], str], dict[str, object]]`, but the source
   `_table` it replaces takes `dict[str, object]` and does `parent[key]`. A
   `Mapping` is fine for `[]`-access, but `ty` may flag the widening at call
   sites that pass `dict`. Pin the parameter type to whatever the call sites
   actually pass (they pass the `pyproject` dict and nested tables — all
   `dict`), or keep `Mapping` and confirm `ty` is happy. Minor; the implementer
   resolves it under the existing 3-attempt tolerance.
3. **WI-3 placement unspecified.** The plan says "add a short subsection to
   `docs/developers-guide.md`" without naming the parent heading. Suggest under
   `## Local workflow` or a new `### Shared test scaffolding` after "The five
   commands". Implementation detail, within tolerance.

## Trail for the next agent

Design docs / sources relied on:

- `docs/execplans/roadmap-1-2-7.md` (target)
- `/data/leynos/Projects/cuprum/cuprum/catalogue.py`, `program.py`, `sh.py`
- `.venv/.../cuprum/catalogue.py` (installed locked copy)
- pytest-timeout 2.4.0 PyPI page (precedence, firecrawl-verified)
- `AGENTS.md` §§ Refactoring heuristics, Abstraction/port/helper policy,
  Python verification and testing, Documentation maintenance
- `docs/issues/audit-1.2.{1,3,5,6}.md`
- `pyproject.toml` (per-file-ignores:92-94, interrogate:310, pytest ini:321-323)
- `Makefile` (PYTHON_TARGETS:15, test:115-116)
- `docs/developers-guide.md`, `docs/adr-006-...md`
Skills: logisphere-design-review, python-router→python-testing (fixture scope).
