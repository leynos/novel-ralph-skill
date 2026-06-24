Feature: reconcile repairs a stale state.toml from the on-disk drafts
  When state.toml claims a chapter is done that the on-disk drafts do not
  corroborate, novel-state check detects the drift (exit 4) and reports the
  recount it implies, novel-state reconcile carries that recount out (exit 0),
  rewrites [word_counts] from the drafts, appends a recovery receipt to log.md,
  removes no working/ file, and a follow-up check is coherent (exit 0). This is
  the roadmap success clause (design §3.4, §4.1, §5.4).

  Scenario: a stale done-claim tree is detected by check, repaired, and re-checked clean
    Given a settled tree whose state claims a done chapter the drafts deny
    When check runs against that tree
    Then check exits 4 reporting a recount reconciliation
    When reconcile runs against that tree
    Then reconcile exits 0 and rewrites the word counts from the drafts
    And reconcile removes no working file and logs a recount recovery entry
    And a follow-up check exits 0

  Scenario: a partial-init tree (state.toml present, log.md absent) is repaired by reconcile
    Given a partial-init tree whose log.md is absent beside a present state.toml
    When reconcile runs against that tree
    Then reconcile exits 0 and recreates log.md
    And reconcile removes no working file and logs a recreate-log recovery entry
    And a follow-up check exits 0
