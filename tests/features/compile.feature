Feature: novel-compile regenerates compiled.md in chapter-index order
  novel-compile concatenates the chapter drafts in ascending zero-padded
  chapter-index order, joined by one fixed separator, and writes
  working/manuscript/compiled.md atomically. Identical drafts and manifest always
  produce a byte-identical compiled.md regardless of directory-listing order, and
  a second run over unchanged drafts leaves the file byte-for-byte unchanged
  (determinism/idempotence). An absent or empty chapter manifest has no
  authoritative ordering, so the command refuses with exit 3 and writes nothing.
  These are the roadmap 4.1.1 success criteria (design §4.3, §10).

  Scenario: compile regenerates the ordered manuscript and is idempotent
    Given a working tree with three drafted chapters and a stale compiled.md
    When novel-compile runs against that tree
    Then novel-compile exits 0
    And compiled.md equals the manifest-ordered concatenation of the drafts
    And a second novel-compile leaves compiled.md byte-for-byte unchanged

  Scenario: compile refuses an empty chapter manifest with exit 3
    Given a working tree whose chapter manifest is empty
    When novel-compile runs against that tree
    Then novel-compile exits 3
    And no compiled.md is written
