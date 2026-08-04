# Skills

My personal collection of Claude Code skills and workflows.

## Skills

Skill directories live in [`skills/`](skills/).

| Skill | Description |
|-------|-------------|
| [agent-engineering](skills/agent-engineering/) | Reference for LLM agent development pitfalls and best practices — context engineering, KV-cache / prompt-caching prefix stability, tool (ACI) design, agent loop architecture, multi-agent trade-offs, evals, observability, and security. Distilled from primary sources (Anthropic, OpenAI/Codex, Manus, Cognition, pi, LangGraph, SWE-agent) with load-bearing numbers and citations; a decision-ladder + checklist entry point with six topic references loaded on demand. |
| [artifact-design](skills/artifact-design/) | Design guidance and fundamentals for Artifacts / frontend pages — read the request first (utilitarian vs editorial treatment), fundamentals for every artifact (typeface pairing, chosen neutrals, dual-theme tokens, layout-driven spacing, avoiding the telltale AI looks, copywriting), then a token-system design plan and editorial principles when the request calls for a distinctive identity. Extracted verbatim from the Claude Code binary's built-in `artifact-design` skill (v2.1.221), with the runtime `dataviz` callout placeholder rendered inline. |
| [office-hours](skills/office-hours/) | Product Office Hours — a structured product thinking partner. **Startup mode** runs six forcing questions (demand reality, status quo, specificity, narrowest wedge, observation, future-fit); **Builder mode** does design-thinking brainstorming for side projects, hackathons, learning, and open source. Produces a design doc, never code. Inspired by [GStack office-hours](https://github.com/garrytan/gstack). |
| [sub-claude](skills/sub-claude/) | Batch-process CSV/JSONL data by spawning parallel `claude -p` agents. Each worker is a full Claude agent with tool access (read files, run commands, call APIs) — not just text generation. For 10–1000+ rows of uniform processing where you need fine-grained control over concurrency, retries, cost budget, and structured output. Includes a ready-to-use `sub_claude.py`. |

## Workflows

Workflow scripts live in [`workflows/`](workflows/). By default they run on Claude Code's native dynamic workflows (the `Workflow` tool).

They're also portable via [six-ddc/codex-dynamic-workflows](https://github.com/six-ddc/codex-dynamic-workflows) — a Claude Code-compatible port that runs the same scripts on other agent CLIs: OpenAI Codex, Gemini CLI, or [pi](https://github.com/badlogic/pi-mono) (a general-purpose agent CLI spanning many more model providers) — with a live web run viewer.

| Workflow | Description |
|----------|-------------|
| [code-review-extracted](workflows/code-review-extracted.js) | Workflow-backed code review — one finder per correctness angle plus one finder covering all cleanup angles (reuse / simplification / efficiency / altitude / CLAUDE.md conventions), an independent verifier per distinct (file, line) location across the pooled candidates, then an index-based synthesis into a ranked, capped findings report. The `/code-review` high / xhigh / max engine. Extracted verbatim from the Claude Code binary (v2.1.221), with the build-time constant interpolations resolved inline. |
| [deep-research-extracted](workflows/deep-research-extracted.js) | Deep research harness — fan-out web searches, fetch sources, adversarially verify claims (3-vote panels; infra failures reported as *unverified*, never as refuted), and synthesize a cited report. Extracted verbatim from the Claude Code binary (v2.1.221). |

## Commands & Agents

An orchestrator command paired with model-pinned subagents for running a session with Claude Fable 5 as the lead. Command lives in [`commands/`](commands/), agents in [`agents/`](agents/).

| File | Description |
|------|-------------|
| [fable](commands/fable.md) | `/fable` — puts the session in orchestrator mode: the main model only plans, dispatches, adjudicates, and synthesizes. Work is routed by role (`deep-reasoner` / `fast-worker` / `verifier` / `Explore`) and scaled by model tier via the Agent `model` override; nontrivial changes get independent verification by `verifier`, with intensity scaled to risk. |
| [handoff](commands/handoff.md) | `/handoff` — distills the current session into a self-contained handoff document (`handoff-YYYY-MM-DD-<slug>.md` in the working directory): task state, key trade-off decisions at full fidelity, background constraints, and next steps, so a fresh session or agent can pick up the work without re-asking. Sources from the conversation context only — no investigation to fill gaps. |
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
