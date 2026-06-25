# The installed per-chapter loop re-drive (roadmap 6.2.2; design §9 lines
# 835-847). This feature crosses the real wheel/venv packaging boundary the
# in-process feature cannot reach: it builds a wheel, installs every
# console-script into a throwaway venv, and re-drives the headline clean pass and
# the stale-compile catch through the installed binaries an operator and the
# harness actually invoke (ADR-003; ADR-006). It is @slow and POSIX-only; its
# binder (tests/test_per_chapter_loop_installed_bdd.py) carries the slow, timeout,
# and POSIX-skip marks on its @scenario-decorated function so no marker leaks onto
# the cross-platform in-process scenarios (ExecPlan Decision D-INSTALLED-SPLIT).
Feature: the installed per-chapter loop crosses the packaging boundary
  The harness invokes the deterministic spine through installed console-scripts,
  not the in-process app. This scenario proves the harness-trusted exit codes
  hold at the real wheel/venv boundary: the composed clean pass exits 0
  throughout and the stale-compile catch exits 4, neither emitting a traceback.

  Scenario: the installed loop passes clean and catches a stale compile
    Given an installed loop tree that passes clean
    When the installed spine runs over the clean tree
    Then every installed loop command exits 0 with no traceback
    And the installed wordcount reports all three knitting gates crossed
    And the installed compile reports the compile is not diverged
    Given an installed loop tree whose compiled.md is byte-divergent
    When the installed novel-done and compile run over the stale tree
    Then the installed novel-done exits 4 and the compile exits 4 diverged
