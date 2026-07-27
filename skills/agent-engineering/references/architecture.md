# Architecture: whether to build an agent, how to write the loop, single vs multi

## 1. Workflow vs agent: don't reach for an agent first

The distinction is a single question: **who decides what happens next**. Workflow = LLM and tools follow predefined code paths; agent = the LLM dynamically directs its own process and tool usage.

Anthropic's governing principle: "find the simplest solution possible, and only increase complexity when needed" — for many cases a single LLM call + retrieval + a few examples is enough. OpenAI's whitepaper gives three criteria for when an agent is worth it: complex decision-making (nuanced judgment, many exceptions), rule systems that have become unmaintainable, and heavy unstructured data. Its own reminder: if the criteria aren't met, "a deterministic solution may suffice."

Five workflow patterns (stop at this level if it's enough):

| Pattern | When |
| --- | --- |
| Prompt chaining | Task decomposes cleanly into fixed steps; programmatic gates can validate between steps |
| Routing | Inputs fall into distinct categories and classification is reliable; simple queries can route to a cheaper model |
| Parallelization | Sectioning (independent subtasks concurrently) or voting (same task multiple times for multiple perspectives) |
| Orchestrator-workers | Subtasks can't be predicted upfront; an orchestrator decomposes at runtime |
| Evaluator-optimizer | Clear evaluation criteria exist and iteration measurably helps (human feedback would improve it + an LLM can produce feedback of that quality) |

Most production systems are **hybrids** of workflows and agents, not pure tool-calling while loops.

## 2. The agent loop: the thinner the better

A fully functional coding agent fits in under 400 lines (Thorsten Ball's demo); the mechanism is four steps: tell the model what tools exist → the model says it wants one in its reply → you execute locally → the result goes back into the conversation. Quality differences between products come from "elbow grease" — prompts, tool robustness, feedback mechanisms — not the loop itself.

Loop designs from mature implementations worth copying:

- **pi**: two nested whiles — inner: "keep the turn going while there are tool calls or steering messages"; outer: "check the follow-up queue." **No max-steps parameter** — let the model say when it's done.
- **OpenAI Agents SDK**: LLM produces final output → stop; handoff → switch agent and re-loop; tool calls → execute and re-loop. `max_turns` as a backstop (raises when exceeded).
- **Codex**: Submissions in / Events streamed out, events at delta granularity (that's what gives users the sense it's alive); tool calls execute **concurrently with ordered collection** (`FuturesOrdered`) — a free latency win, provided tools have no implicit ordering dependency; a pending-input queue lets the user interject mid-turn without aborting it.
- **Steering injection timing**: wait until the current batch of tool calls finishes, take effect next turn — never interrupt a half-executed tool batch (pi's approach).

**The tool_choice infinite loop**: with `tool_choice` pinned to a specific tool or `required`, the tool result flows back and the same tool_choice forces another call, forever. The Agents SDK auto-resets to `auto` after one call — a hand-written loop must replicate this.

## 3. Frameworks: low-level control beats high-level abstraction

Anthropic warns directly: frameworks "create extra layers of abstraction that can obscure the underlying prompts and responses, making them harder to debug" — start with raw APIs (many patterns are a few lines of code), and if you do use a framework, understand what's underneath. LangChain itself concedes: the hard part was never "writing the while loop," it's "making sure the LLM has the appropriate context at each step" — any abstraction that makes it hard to see or change what goes into the LLM is a liability. 12-Factor Agents: frameworks get you to 70–80% then wall you in; "good agents are mostly just software" — own your prompts, your context window, your control flow.

The real incremental value of a graph/state machine (LangGraph) is not the loop but: **durable execution** (checkpointer + thread_id → crash recovery / human interrupts / resume), time-travel debugging (note: replay re-executes for real, it doesn't read from cache), and **mandatory reducers** on state keys written by parallel branches — the framework errors out rather than silently picking a winner.

## 4. Long-running agents: persistence is not optional

- Agents are long-lived stateful processes; "minor system failures can be catastrophic." You can't restart from scratch (expensive + duplicated side effects) — build **resume-from-failure**: retry logic + periodic checkpoints.
- Codex's approach: sessions persisted as JSONL; compaction's replacement history is stored inline, so resume replays only the tail after the checkpoint.
- Deploy with **rainbow deployments** — gradual traffic shifting so running agents aren't interrupted.
- Durability has tiers (LangGraph: exit / async / sync) — choose per step cost and repeatability, not blanket synchronous writes everywhere.

## 5. Multi-agent: an anti-pattern by default, with three exceptions

**Costs first**: agents ≈ 4× chat tokens; multi-agent ≈ 15× (Anthropic's measurement); every added agent is another point of failure. Some teams "spent months building complex multi-agent architectures, then found improving a single agent's prompt achieved the same results."

**Cognition's "Don't Build Multi-Agents" core argument**: actions carry implicit decisions (art style, data structures, naming conventions — the things decided "in passing" while working), and parallel agents can't see each other's implicit decisions → irreconcilable outputs (the Flappy Bird example: one subagent built a Mario-style background, the other a bird that matched neither). Sending the full original task text to every subagent doesn't help — the conflicts arise during execution.

**Anthropic's multi-agent research system, the positive data**: Opus 4 lead + Sonnet 4 subagents beat single Opus 4 by 90.2% on their internal research eval; on BrowseComp, token usage alone explains 80% of performance variance.

**Reconciling the two (more useful than either piece alone)**:
- Subagents for **context isolation + read-only investigation** are almost always right — burn tens of thousands of tokens exploring, return only a 1,000–2,000-token distilled summary; the investigation debris never pollutes the main context.
- Subagents for **parallel production of artifacts that must coordinate** are almost always wrong.
- The dividing line: **do the subtasks share implicit decisions?** Research subquestions are independent, so parallelism works; implementation is full of shared conventions, so parallelism collapses.

**Three signals to upgrade to multi-agent** (Anthropic): approaching the context limit with degrading performance; 15–20+ tools confusing each other (consider tool search before splitting agents); genuinely independent parallelizable subtasks.

**Decomposition principle**: split by context boundary, **never by sequential phase** (plan → implement → test shares too much context across phases). The only pattern called out as "consistently effective": a **dedicated verification agent** — black-box checks of the main agent's output with fresh context; the one who did the work doesn't grade itself.

**The orchestrator prompt must give every subagent**: an objective, an output format, guidance on tools and sources, and clear task boundaries. Missing any of these produces duplicated work, gaps, and agents talking over each other. Add an effort scale to prevent overkill: simple fact-finding = 1 agent / 3–10 tool calls; direct comparisons = 2–4 subagents / 10–15 calls each; complex research = 10+ subagents with clearly divided responsibilities.

**Two multi-agent shapes** (OpenAI): Manager (subagents as tools — control never transfers, single entry point for the user) vs decentralized handoffs (control transfers wholesale, good for triage). The split signals are "too many if-else branches" and "high tool overlap," not absolute tool count.

## 6. Human-in-the-loop

- The review point sits between **"proposed tool call" and "execution"**, not after answer generation. Only intercept write / irreversible / outbound actions.
- Four standard responses (LangGraph HITL middleware): approve (execute with original args) / edit (modify args first) / reject (skip and feed the reason back to the LLM) / respond (human message becomes the synthetic tool result).
- Pausing depends on persistence — state must survive the interrupt to resume.
- Escalation triggers (OpenAI whitepaper): exceeding a failure threshold (repeated failure to grasp intent → hand to a human) and high-risk actions (canceling orders, large refunds).
- The flip side of approval prompts is approval fatigue — see `security.md`.

## Sources

- https://www.anthropic.com/engineering/building-effective-agents
- https://claude.com/blog/building-multi-agent-systems-when-and-how-to-use-them
- https://www.anthropic.com/engineering/multi-agent-research-system
- https://cognition.com/blog/dont-build-multi-agents
- https://ampcode.com/how-to-build-an-agent
- https://github.com/openai/codex (codex-rs/core/src/session/turn.rs etc.)
- https://openai.github.io/openai-agents-python/ (running_agents / multi_agent / handoffs)
- https://cdn.openai.com/business-guides-and-resources/a-practical-guide-to-building-agents.pdf
- https://blog.langchain.com/how-to-think-about-agent-frameworks/
- https://docs.langchain.com/oss/python/langgraph/durable-execution
- https://github.com/humanlayer/12-factor-agents
- https://github.com/earendil-works/pi
