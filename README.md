# 📖 novel-ralph-skill

[![Ask DeepWiki](https://deepwiki.com/badge.svg)](
https://deepwiki.com/leynos/novel-ralph-skill)

*Write a complete novel under a Ralph Loop harness — one truthful turn at a
time.*

novel-ralph is a Claude Code skill for long-form fiction. It carries a premise
through treatment, character work, conflict analysis, world-building, Save the
Cat beat planning, chapter outlining, scene-and-beat drafting, desloppifying,
and adversarial revision — resuming from disk on every turn until the work
honestly reports done.

______________________________________________________________________

## Why novel-ralph-skill?

A book is too big for one context window. The Ralph Loop answers that by
re-entering the model each turn with no memory beyond what is on disk, so the
work has to be idempotent, resumable, and state-driven.

- **State lives on disk, not in memory.** Every turn reads `working/state.toml`
  and derives its next action from state alone.
- **Done is a predicate, not a feeling.** The harness stops only when the
  completion predicate evaluates true against the manuscript on disk.
- **Determinism is scripted; judgement is delegated.** Word counts, state
  transitions, compilation, and slop detection belong to tested commands.
  Reading prose for quality belongs to the model — and the adversarial reads go
  to a clean-context sub-agent that did not write the chapter.

______________________________________________________________________

## Quick start

novel-ralph is a skill, so the entry point is a request to Claude Code:

```text
Write me a novel about a lighthouse keeper who is afraid of the sea.
```

Claude loads the skill, sets up a `working/` directory with `state.toml`, and
advances the book one bounded unit per turn — a scene drafted, a chapter
critiqued, a beat written — under a harness that keeps re-entering until the
manuscript is finished.

The deterministic spine that makes those turns reproducible — the `novel-state`,
`novel-done`, `novel-compile`, `desloppify`, and `wordcount` commands — is
being rebuilt from the design below. See the [roadmap](docs/roadmap.md) for
current progress.

______________________________________________________________________

## Features

- A phase machine spanning premise through final pass, with strict forward
  ordering.
- Disk-authoritative state: word counts and phase progress re-derived from the
  manuscript, never hand-typed.
- A single-source done predicate evaluated clause-by-clause against disk.
- Deterministic, outline-ordered compilation with a read-only consistency
  check.
- Configurable slop detection, including a per-novel device ledger that rations
  recurring images and motifs.
- A clean-context adversarial pipeline: a spiteful critic, a line editor, a
  knitting circle, and a persistent fangirl.

______________________________________________________________________

## Learn more

- [Documentation contents](docs/contents.md) — the full documentation index.
- [Terms of reference](docs/terms-of-reference.md) — the problem space and
  scope of the rebuild.
- [Harness design](docs/novel-ralph-harness-design.md) — the deterministic
  spine and clean-context sub-agent architecture.
- [Roadmap](docs/roadmap.md) — planned features and progress.
- [Users' guide](docs/users-guide.md) — how to use the generated project.
- [Developers' guide](docs/developers-guide.md) — the contributor workflow.

______________________________________________________________________

## Licence

ISC — see [LICENSE](LICENSE) for details.

______________________________________________________________________

## Contributing

Contributions are welcome. Please see [AGENTS.md](AGENTS.md) for the quality
gates and the contributor workflow.
