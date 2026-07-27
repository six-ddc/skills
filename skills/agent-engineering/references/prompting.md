# Prompting for Agents

## 1. Write at the right altitude

The two failure extremes of a system prompt (Anthropic):
- **Too brittle**: complex hardcoded if-else logic baked into the prompt — fragile, unmaintainable, fights real inputs.
- **Too vague**: high-level slogans with no concrete signals, or the false assumption that the model shares your background.

Target zone: "specific enough to guide behavior effectively, yet flexible enough to provide strong heuristics." In practice:
- Split into clear sections with XML tags or Markdown headers (background / instructions / tool guidance / output format).
- Aim for "the minimal set of information that fully outlines expected behavior."
- **Development order: start with a minimal prompt on the strongest model, and derive additions from observed failure modes** — don't front-load rules.

Frontier models have been RL-trained hard on "how an agent should work" — don't teach them what they already know. pi's entire system prompt + tool definitions fit under 1,000 tokens with Terminal-Bench results in the same tier as the big harnesses. Pruning test for resident instructions (Claude Code): "Would removing this cause mistakes?" If not, delete — **bloated resident instructions cause the model to ignore your actual instructions**; if a rule you wrote isn't being followed, it's usually because the file is so long the rule drowned.

## 2. Contradictory instructions cost more than you think

A reasoning model doesn't respond to contradictions by picking one at random — it **burns reasoning tokens trying to reconcile them** (GPT-5 guide: contradictory prompts are "more damaging to GPT-5 than to other models"). Canonical case: "never schedule an appointment without explicit patient consent" coexisting with "auto-assign without contacting the patient."

- Fix: give instructions explicit **priorities and exception clauses** ("skip the lookup step in emergencies"); "prioritized" beats "exhaustive."
- Diagnostic heuristic: **malformed tool calls (garbled output) → check the prompt for internal contradictions first.**
- Never repeat one instruction in both the system prompt and a tool description — duplication is a breeding ground for contradictions; tool matters live in tool descriptions only.

## 3. Controlling agentic eagerness

Both directions have standard recipes (GPT-5 prompting guide; portable to any model):

**Dial down** (less thrashing, faster results): lower the reasoning effort; bound the exploration scope and give **early-stop criteria** ("stop once top hits converge on one area"); set a tool-call budget ("absolute maximum of 2 tool calls"). Crucially, pair with an **escape hatch** — "proceed even if it might not be fully correct" — otherwise a capped exploration budget leaves the model frozen, afraid to act.

**Dial up** (persistence, against giving up early):
```
- You are an agent - keep going until the query is completely resolved,
  before ending your turn.
- Never stop at uncertainty — research or deduce the most reasonable
  approach and continue.
- Do not ask the human to confirm assumptions — decide the most
  reasonable one, proceed, document it for reference after acting.
```
"Biased for action": if the user asks "should we do X" and the answer is yes, just do X.

**Overthinking signal** (a simple answer yet endless exploration, tools never called) → lower effort + give "act early" criteria. **Laziness signal** (skipped steps, missing reasoning) → raise effort or add a self-check rubric.

**Tool preambles / progress narration**: restate the goal and outline the plan before calling tools; narrate briefly while executing. Not just UX — it's an officially listed **perceived-latency reducer**. You can specify cadence and content ("an update every 8 tool calls; each update must contain at least one concrete finding").

## 4. Examples: curate, don't enumerate

Don't stuff a long list of edge cases into the prompt. Use "a curated set of diverse, canonical examples" — for an LLM, examples are the picture worth a thousand words.

One step further (the Claude 5-era direction, for the strongest models): examples themselves **constrain the model to an exploration space**; whatever can be expressed through interface design shouldn't be expressed through examples (let parameter enums imply expected behavior). The overall trend is subtraction: Anthropic cut over 80% of Claude Code's system prompt for the Claude 5 generation with no measurable loss — **rules → judgment, examples → interface design, up-front context → progressive disclosure, deduplicate everything**.

## 5. Recitation: pin the goal inside the attention window

In long tasks (Manus averages ~50 tool calls) the model drifts or forgets the original objective. Technique: maintain a todo.md, rewrite it after every step, and place it at the **end** of the context — constantly pulling attention back to the global plan, with zero architecture changes. Note that plan/todo tools place zero constraints on model behavior (Codex source comments say so outright); their value is recitation plus progress display for the user.

## 6. What belongs in resident context (CLAUDE.md / AGENTS.md-style files)

| Write | Don't write |
| --- | --- |
| Commands the model can't guess, environment quirks, required env vars | Anything discoverable by reading the code |
| Style rules that differ from defaults | Standard language conventions, "write clean code" truisms |
| Repo etiquette (branch naming, commit conventions) | Detailed API docs (link instead) |
| Common traps and non-obvious behavior | Per-file codebase descriptions, frequently changing info |

Domain knowledge relevant only to some tasks → move it into on-demand skills/docs, not resident context.

Engineering detail (Codex's AGENTS.md implementation): files merge root → cwd, but under **one shared global byte budget** (default 32 KiB) — later files get truncated. Put the most important constraints in the root file; don't count on deep subdirectory addenda making it in.

## 7. Prompts need versions and evals too

- Write the prompt version into every trace (without it, "did this prompt change cause the regression" is unanswerable).
- Metaprompting is legitimate: models are decent prompt engineers, able to diagnose why an agent fails and suggest fixes. Two-step: first diagnosis only (structured failure modes, no fixes), then small explicit edits ("keep the structure and overall length roughly similar") — no rewrites from scratch. Run the metaprompt several times, keep only recurring improvements, validate with evals.
- For orchestrator prompts in multi-agent systems, see `architecture.md` §5.

## Sources

- https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents
- https://cookbook.openai.com/examples/gpt-5/gpt-5_prompting_guide (plus gpt-5-1 / gpt-5-2 / troubleshooting series)
- https://claude.com/blog/the-new-rules-of-context-engineering-for-claude-5-generation-models
- https://code.claude.com/docs/en/best-practices
- https://github.com/openai/codex (codex-rs/core/src/agents_md.rs)
- https://manus.im/blog/Context-Engineering-for-AI-Agents-Lessons-from-Building-Manus
- https://mariozechner.at/posts/2025-11-30-pi-coding-agent/
