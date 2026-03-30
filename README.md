# Skills

My personal collection of Claude Code skills.

## Skills

| Skill | Description |
|-------|-------------|
| [office-hours](office-hours/) | Product Office Hours — structured product thinking partner. Two modes: **Startup mode** uses six forcing questions to expose demand reality, status quo, user specificity, narrowest wedge, observation gaps, and future-fit. **Builder mode** offers design thinking brainstorming for side projects, hackathons, learning, and open source. Produces a design doc, never code. Inspired by [GStack office-hours](https://github.com/garrytan/gstack). |
| [sub-claude](sub-claude/) | Batch-process CSV/JSONL data by spawning parallel `claude -p` processes. Subagents are model-driven — context accumulates with each row causing cascading cost, error handling depends on the model's judgment, and you have little control over execution. For 10-1000+ rows of uniform processing (classify, translate, extract, etc.), this script-driven approach gives you isolated per-row execution (no context bleed), deterministic concurrency/retry/checkpoint behavior, and precise control over model, effort, cost budget per invocation. Includes a ready-to-use `sub_claude.py`. |

## Installation

Symlink a skill directory into `~/.claude/skills/`:

```bash
ln -s /path/to/skills/<skill-name> ~/.claude/skills/<skill-name>
```
