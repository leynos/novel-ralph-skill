# Logisphere adversarial design review — roadmap 7.1.3 (round 1)

Verdict: REVISE. One blocking completeness defect; otherwise the design is
sound.

Reviewed against: `_desloppify_report.py` (line 182), `ledger/report.py`
(line 131), `tests/test_command_surface_matrix.py`, the three `.ambr`
snapshots, the design §3.1/§3.3/§4.4, the developers' guide rule-pack
section, roadmap 7.1.3, and the locked cuprum source.

## BLOCKING

### B1 — Consumer inventory is incomplete; a full-trail envelope consumer is omitted

The plan's premise ("the only `result.findings` consumers are the two
projection functions and their two snapshot suites; the skill and harness
read `violations`/`ok` only") is FALSE. A third envelope consumer reads the
full trail:

- `tests/test_command_surface_matrix.py::test_desloppify_shape_across_phases`
  (line 717) hard-asserts `len(result["findings"]) == 24` across all eleven
  phases, each with `violations == []`. These are clean passes. Under
  violations-only slimming every one becomes `findings == []`, so this
  assertion fails for all eleven phases.
- `tests/__snapshots__/test_command_surface_matrix.ambr` captures the full
  per-rule trail in the eleven `test_machine_envelope_matrix[desloppify-*]`
  blocks (264 `rule_id` rows total; all eleven desloppify cases have empty
  `violations`). Each clean block must regenerate to `findings: []`.

Neither file appears in Work item 2's edit list, nor in Work item 0's
inventory, nor in the Risk register. As written, `make all` is red after
Work item 2 — the plan is not implementable.

Fix: Work item 0 must grep `tests/` exhaustively (not just `skill/`) and add
`test_command_surface_matrix.py` + its `.ambr` to the inventory. Work item 2
must (a) change the `== 24` assertion to assert `findings == []` for clean
phases and `set(result)` membership unchanged, and (b) regenerate
`tests/__snapshots__/test_command_surface_matrix.ambr` alongside the other
two snapshots. The Tolerance "more than 6 files" must be re-evaluated: the
edit set is now ~7-8 files (2 source, 3 `.ambr`,
`test_command_surface_matrix.py`, the two named snapshot suites, plus new
unit tests and docs), which itself may breach the stated scope tolerance and
warrant an explicit note.

## NON-BLOCKING / advisory

- A2 (Telefono): The Tolerance "Ambiguity — if a second envelope consumer
  (beyond the two projections) is found to read passing findings, stop and
  escalate" is, strictly read, already tripped by B1:
  `test_desloppify_shape_across_phases` reads passing findings. The plan
  should treat that test as an expected, mechanical snapshot/assertion update
  rather than an escalation, and say so, so the implementer does not halt on
  a Tolerance that the plan itself should have pre-resolved.
- A3 (Pandalump): cuprum API claims (ProjectSettings fields,
  ProgramCatalogue, `make` @528, `SafeCmd` @349, `run_sync` @441,
  `exit_code: int`, `stdout: str | None`) all verified accurate against the
  locked source; the e2e layer is genuinely unaffected (assertions read
  `violations`/`ok`). No defect.
- A4 (Doggylump): the `ai_isms_e2e` clean case (line 250) and
  `test_desloppify_command.py` clean case read `violations`, not `findings`;
  safe under the slimming. Confirmed.
- A5 (Wafflecat, alternatives): violations-only is well-justified against
  §3.1 and is the scaling choice the roadmap asks for; the roadmap success
  criterion is decision-neutral, so the choice is in bounds. No stronger
  alternative — full-audit-trail is the status quo the roadmap exists to
  revisit.
- A6 (Dinolump): detection cores correctly left untouched (counts cannot
  drift); the slimming is a pure projection trim. Sound long-term shape.
