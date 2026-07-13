# Skills

My personal collection of Claude Code skills and workflows.

## Skills

Skill directories live in [`skills/`](skills/).

| Skill | Description |
|-------|-------------|
| [artifact-design](skills/artifact-design/) | Design process and taste guidance for building distinctive, production-grade frontend interfaces (Claude Artifacts, web components, pages, apps) — brainstorm a token system, critique it, commit the palette, then build, with render-verified mechanics so output never reads as a generic template. |
| [office-hours](skills/office-hours/) | Product Office Hours — a structured product thinking partner. **Startup mode** runs six forcing questions (demand reality, status quo, specificity, narrowest wedge, observation, future-fit); **Builder mode** does design-thinking brainstorming for side projects, hackathons, learning, and open source. Produces a design doc, never code. Inspired by [GStack office-hours](https://github.com/garrytan/gstack). |
| [serenity-investor](skills/serenity-investor/) | Analyze any stock, theme, or market through the full investing persona, decision framework, and voice of X/Twitter investor @aleabitoreddit ("Serenity") — the AI-supply-chain / photonics / chokepoint lens (`$SIVE`, `$AAOI`, `$NBIS`, CPO, HBM, humanoid robotics, 800V DC, …). A persona-simulation skill: output reads like his own analysis, not a neutral third-party report. Pairs with the `serenity-analysis` workflow. |
| [sub-claude](skills/sub-claude/) | Batch-process CSV/JSONL data by spawning parallel `claude -p` agents. Each worker is a full Claude agent with tool access (read files, run commands, call APIs) — not just text generation. For 10–1000+ rows of uniform processing where you need fine-grained control over concurrency, retries, cost budget, and structured output. Includes a ready-to-use `sub_claude.py`. |

## Workflows

Workflow scripts live in [`workflows/`](workflows/). By default they run on Claude Code's native dynamic workflows (the `Workflow` tool).

They're also portable via [six-ddc/codex-dynamic-workflows](https://github.com/six-ddc/codex-dynamic-workflows) — a Claude Code-compatible port that runs the same scripts on other agent CLIs: OpenAI Codex, Gemini CLI, or [pi](https://github.com/badlogic/pi-mono) (a general-purpose agent CLI spanning many more model providers) — with a live web run viewer.

| Workflow | Description |
|----------|-------------|
| [code-review-extracted](workflows/code-review-extracted.js) | Workflow-backed code review — one finder agent per review angle, an independent verifier for every candidate, then a ranked, capped findings report. Launched by the `/code-review` skill at high / xhigh / max effort. |
| [deep-research-extracted](workflows/deep-research-extracted.js) | Deep research harness — fan-out web searches, fetch sources, adversarially verify claims, and synthesize a cited report. |
| [serenity-analysis](workflows/serenity-analysis.js) | Runs Serenity's (@aleabitoreddit) methodology for stock due-diligence or industry chokepoint scans: six-way parallel evidence gathering → tiered adversarial review → rough quant → decision-algorithm verdict → write-up in his voice. Findings are tagged across four evidence tiers (confirmed / reported / mapped / speculation). Pairs with the `serenity-investor` skill. |

## Commands & Agents

An orchestrator command paired with model-pinned subagents for running a session with Claude Fable 5 as the lead. Command lives in [`commands/`](commands/), agents in [`agents/`](agents/).

| File | Description |
|------|-------------|
| [fable](commands/fable.md) | `/fable` — puts the session in orchestrator mode: the main model only plans, dispatches, adjudicates, and synthesizes. Work is routed by role (`deep-reasoner` / `fast-worker` / `verifier` / `Explore`) and scaled by model tier via the Agent `model` override; nontrivial changes get independent verification by `verifier`, with intensity scaled to risk. |
| [deep-reasoner](agents/deep-reasoner.md) | Pinned to Opus at `xhigh` effort. Architecture design, complex-bug root-cause analysis, algorithm design, trade-off analysis. |
| [fast-worker](agents/fast-worker.md) | Pinned to Sonnet at `medium` effort. Boilerplate, well-specified changes, running tests/lint/build, batch operations. |
| [verifier](agents/verifier.md) | Pinned to Sonnet at `high` effort (pass `model: opus` for critical changes). Falsification-oriented: re-runs tests and checks each acceptance criterion with fresh context rather than trusting the implementer's self-report. |

## Installation

Symlink a skill into `~/.claude/skills/`:

```bash
ln -s /path/to/skills/skills/<skill-name> ~/.claude/skills/<skill-name>
```

Symlink a workflow into `~/.claude/workflows/`:

```bash
ln -s /path/to/skills/workflows/<workflow-name>.js ~/.claude/workflows/<workflow-name>.js
```

Symlink the command and agents into `~/.claude/commands/` and `~/.claude/agents/`:

```bash
ln -s /path/to/skills/commands/fable.md ~/.claude/commands/fable.md
ln -s /path/to/skills/agents/<agent-name>.md ~/.claude/agents/<agent-name>.md
```
