# The per-chapter deterministic-loop scenario (roadmap 6.2.2; design §7.2,
# Figure 3, and §9 lines 814-847). It drives the deterministic spine — recount,
# novel-done, wordcount, desloppify, and novel-compile --check — over real
# working/ trees through the shared command boundary, proving the commands
# compose. Beyond the clean pass it pins the three §9 success criteria as
# focused scenarios, each over the corpus tree that exhibits exactly its gated
# decision: a stale compile is caught (§4.2, §4.3, §10), a crossed knitting gate
# is reported (§4.5), and an out-of-order phase advance is refused (§3.2, §4.1).
# One incoherent tree cannot exhibit all three, so the deterministic decisions
# that gate the loop are modelled as separate scenarios (ExecPlan Decision Log).
Feature: the per-chapter deterministic loop composes the spine
  The harness drives one chapter through the deterministic spine in a fixed
  order — recount, novel-done, wordcount, desloppify, novel-compile --check —
  and branches on each command's exit code. These scenarios prove that ordered
  drive over a real working/ tree at the command boundary: a coherent tree
  passes clean, and each gated decision the loop turns on is caught.

  Scenario: a coherent chapter passes the deterministic loop clean
    Given a coherent fully-drafted working tree
    When recount runs against the loop tree
    Then recount exits 0 and reports the drafted by-chapter counts
    When novel-done runs against the loop tree
    Then novel-done exits 0 and every done clause holds
    When wordcount runs against the loop tree
    Then wordcount exits 0 and reports all three knitting gates crossed
    When desloppify runs against the loop tree
    Then desloppify exits 0 with no violations over the drafted total
    When novel-compile --check runs against the loop tree
    Then novel-compile --check exits 0 and reports the compile is not diverged

  Scenario: a stale compile is caught
    Given an otherwise-complete working tree whose compiled.md is byte-divergent
    When novel-done runs against the loop tree
    Then novel-done exits 4 reporting the compile is not consistent
    When novel-compile --check runs against the loop tree
    Then novel-compile --check exits 4 reporting the compile is diverged

  Scenario: a crossed knitting gate is reported
    Given a coherent fully-drafted working tree
    When wordcount runs against the loop tree
    Then wordcount exits 0 and reports all three knitting gates crossed

  Scenario: an out-of-order phase advance is refused
    Given a working tree whose phase.completed skips the in-order prefix
    When advance-phase runs against the loop tree
    Then advance-phase exits 3 and leaves state.toml byte-for-byte intact
