# Skills

My personal collection of Claude Code skills and workflows.

## Skills

Skill directories live in [`skills/`](skills/).

| Skill | Description |
|-------|-------------|
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

## Installation

Symlink a skill into `~/.claude/skills/`:

```bash
ln -s /path/to/skills/skills/<skill-name> ~/.claude/skills/<skill-name>
```

Symlink a workflow into `~/.claude/workflows/`:

```bash
ln -s /path/to/skills/workflows/<workflow-name>.js ~/.claude/workflows/<workflow-name>.js
```
