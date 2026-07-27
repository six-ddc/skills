---
name: agent-engineering
description: Reference for LLM agent development pitfalls and best practices — context engineering, KV-cache / prompt-caching prefix stability, tool (ACI) design, agent loop architecture, multi-agent trade-offs, evals, observability (tracing), and security (prompt injection / sandboxing / permissions). Distilled from primary sources including Anthropic, OpenAI (Codex), Manus, Cognition, pi, LangGraph, and SWE-agent, with load-bearing numbers and citations. Use this skill whenever designing, implementing, reviewing, or optimizing any LLM agent / agentic system / tool-calling app / chatbot-with-tools — including writing system prompts, defining tool schemas, choosing orchestration architecture (single agent vs multi-agent vs workflow), cutting token costs, fixing agents that drift / loop forever / blow up their context, building agent evals or tracing, or adding human-in-the-loop approval. Trigger phrases: agent development, build an agent, tool design, context engineering, prompt caching, KV cache, cache hit rate, multi-agent, subagent architecture, agent evals, agent security, LangGraph, too many MCP tools, token cost optimization, agent loop.
---

# LLM Agent Development Notes

An engineering reference distilled from primary industry sources. The core judgment first:

> **The architecture itself is simple — one LLM, one loop, a set of tools; a working agent fits in 400 lines. The quality gap lives in three things: what goes into the context each turn (context engineering), how usable the tools are (ACI design), and whether there is a verification loop (evals).** Don't spend your effort on orchestration-framework tricks.

## How to use this skill

This is a reference library — read on demand, not cover to cover:

| What you're doing | Read |
| --- | --- |
| Choosing architecture: agent or not, single vs multi, framework or not | `references/architecture.md` |
| Writing system prompts / instructions, controlling agent eagerness | `references/prompting.md` |
| Managing context: cache hits, compaction, long tasks, token costs | `references/context-engineering.md` |
| Designing/refactoring tools, integrating MCP, defining schemas | `references/tool-design.md` |
| Building evals, debugging flaky agents, setting up tracing | `references/evals-observability.md` |
| Permissions, sandboxing, prompt injection, approval flows | `references/security.md` |

When reviewing a design or answering questions, scan the checklist below first to locate the problem domain, then open the matching reference for details and numbers.

## Decision order: the complexity ladder

Always start at the bottom of the ladder and climb one rung only when you have evidence of failure:

1. **Single LLM call** (+ retrieval + a few canonical examples) — enough for most cases
2. **Workflow** (predefined code paths chaining LLM calls: chaining / routing / parallelization / evaluator-optimizer) — when the task decomposes cleanly and you need predictability
3. **Single agent** (LLM using tools autonomously in a loop) — only when step count is unpredictable, the path can't be hardcoded, and you have some trust in the model's decisions
4. **Multi-agent** — only when one of three signals appears: approaching the context limit with degrading performance; 15–20+ tools confusing each other; genuinely independent parallel subtasks (no shared implicit decisions)

Agentic systems trade latency and cost for task performance (agent ≈ 4× chat tokens; multi-agent ≈ 15×). If the task value doesn't cover that price, don't pay it.

## Core checklist

**Context & caching** (agent input:output ratio often hits 100:1 — cost lives almost entirely on the input side; cached reads cost ~0.1× full price)
- [ ] System prompt prefix is byte-stable: no timestamps, no random IDs, no counters
- [ ] Context ordering: static → semi-static → dynamic; append-only, never rewrite history
- [ ] Tool definitions never added/removed dynamically per state (kills the cache); JSON serialization has deterministic key order
- [ ] Cache hit rate (`cache_read_input_tokens` share) monitored as a core ops metric
- [ ] Long-task strategy in place: compaction (max recall first, then precision) / external notes / subagents returning only 1–2k-token summaries
- [ ] Failure records kept in context (compressed) — the model updates its priors from them

**Tools**
- [ ] Tools built around workflows, not 1:1 API endpoints; two calls that always happen together get merged into one
- [ ] Fewer than 20 tools visible at the start of a turn; beyond that use tool search / deferred loading, never dump everything
- [ ] Returns designed for the token budget: semantic IDs (no bare UUIDs), pagination, concise/detailed modes, hard truncation caps
- [ ] Error messages teach the model how to fix the call (actionable guidance), never raw stack traces
- [ ] Guardrails built into the tool layer (parameter validation, lint feedback, forced absolute paths), not entrusted to prompt reminders
- [ ] Values the code already knows are never delegated to the model as parameters

**Prompting**
- [ ] Written at the right altitude: no brittle hardcoded if-else, no vague platitudes; start minimal and add based on observed failure modes
- [ ] No self-contradicting instructions (reasoning models burn tokens reconciling contradictions instead of picking one; malformed tool calls → check for prompt contradictions first)
- [ ] Tool capabilities live in the tool description; when-to-call policy lives in the system prompt; no duplication

**Verification & evals**
- [ ] The agent has a verification loop it can run itself (tests/lint/diff/screenshots) — otherwise "looks done" is the only signal
- [ ] Evals start from 20–50 real failure cases, scoring outcome + whether the necessary tools were called (not step-by-step trajectory matching)
- [ ] User-facing reliability measured as pass^k, not pass@k; every case run multiple times with variance reported
- [ ] LLM judge is never the same model that ran the agent; binary criteria, per-dimension scoring, an explicit "unsure" escape
- [ ] Tracing captures everything: full messages, tool schemas, raw tool returns, tokens/cost, prompt version

**Security**
- [ ] All external content returned by tools is treated as untrusted input (the main prompt-injection channel)
- [ ] Lethal-trifecta check: private data + untrusted content + exfiltration channel — if all three are present, cut one edge
- [ ] Permission checks live in tool-layer code, not in the prompt; read-only by default, allowlist not blocklist
- [ ] Approval points are few and precise (only irreversible / outbound / money-or-permission actions) to avoid approval fatigue

## The five most common traps

1. **Timestamp in the system prompt** — the entire cache misses on every request: you pay the 1.25× write premium forever and never see the 0.1× read price.
2. **Dynamically adding/removing tools** — tool definitions sit at the front of the cache hierarchy (tools → system → messages); touching them invalidates everything after. Constrain with tool_choice/allowed_tools or logits masking instead of editing the list.
3. **Forcing tool_choice and forgetting to reset it** — the tool result flows back, the same forced tool_choice fires again, infinite loop. Reset to auto after one call.
4. **Splitting multi-agent by sequential phase** (plan → implement → test as separate agents) — phases share massive implicit decisions; splitting them guarantees context loss. Split by context boundary instead (independent research paths, black-box verification).
5. **Blaming the model for a drifting agent** — first check: is the context polluted by failed attempts (time to restart), did a tool output flood the window, has a repetitive few-shot rhythm locked the model into mimicry.

## Sources

Each reference lists primary-source URLs at the end. Main sources: Anthropic engineering blog (Building Effective Agents / Writing Tools for Agents / Context Engineering / Multi-Agent Research System), Anthropic prompt-caching docs, OpenAI codex-rs source and Agents SDK docs, OpenAI "A Practical Guide to Building Agents", GPT-5 series prompting guides, Manus "Context Engineering for AI Agents", Cognition "Don't Build Multi-Agents", pi agent (earendil-works/pi) source and author blog, LangGraph docs, SWE-agent ACI paper (arXiv:2405.15793), τ-bench (arXiv:2406.12045), Chroma context-rot research, Simon Willison (lethal trifecta), 12-Factor Agents. Researched 2026-07.
