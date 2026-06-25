# The installed per-chapter loop re-drive (roadmap 6.2.2, 6.2.9; design §9 lines
# 835-847). This feature crosses the real wheel/venv packaging boundary the
# in-process feature cannot reach: it builds a wheel, installs every
# console-script into a throwaway venv, and re-drives the deterministic decisions
# through the installed binaries an operator and the harness actually invoke
# (ADR-003; ADR-006). It re-drives the headline clean pass (which folds in the
# crossed knitting gate via the installed wordcount gates-crossed assertion), the
# stale-compile catch, and — closing audit-6.2.2 Finding 7 — the refused
# out-of-order advance-phase (design §3.2, §4.1, §5.4: the mutator refuses the
# write, exits 3, and leaves state.toml byte-for-byte intact). It is @slow and
# POSIX-only; its binder (tests/test_per_chapter_loop_installed_bdd.py) carries
# the slow, timeout, and POSIX-skip marks on each @scenario-decorated function so
# no marker leaks onto the cross-platform in-process scenarios (ExecPlan Decision
# D-INSTALLED-SPLIT).
Feature: the installed per-chapter loop crosses the packaging boundary
  The harness invokes the deterministic spine through installed console-scripts,
  not the in-process app. These scenarios prove the harness-trusted exit codes
  hold at the real wheel/venv boundary: the composed clean pass exits 0
  throughout, the stale-compile catch exits 4, and the refused out-of-order
  advance exits 3, none emitting a traceback.

  Scenario: the installed loop passes clean and catches a stale compile
    Given an installed loop tree that passes clean
    When the installed spine runs over the clean tree
    Then every installed loop command exits 0 with no traceback
    And the installed wordcount reports all three knitting gates crossed
    And the installed compile reports the compile is not diverged
    Given an installed loop tree whose compiled.md is byte-divergent
    When the installed novel-done and compile run over the stale tree
    Then the installed novel-done exits 4 and the compile exits 4 diverged

  Scenario: the installed loop refuses an out-of-order advance-phase
    Given an installed loop tree whose phase.completed skips the in-order prefix
    When the installed advance-phase runs over the out-of-order tree
    Then the installed advance-phase exits 3 with state.toml byte-for-byte intact and no traceback
