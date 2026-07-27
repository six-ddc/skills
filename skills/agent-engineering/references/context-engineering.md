# Context Engineering & Caching

## 0. Why this is priority number one

- The agent loop is "append one action + one observation, reason again" — input keeps growing while output stays short. Manus measured an **average input:output ratio ≈ 100:1**; cost and time-to-first-token are decided almost entirely on the input side.
- Context isn't free. In a transformer, n tokens create n² pairwise attention relationships — the longer the context, the thinner attention spreads; models have an "attention budget." The empirical name is **context rot**: Chroma tested 18 frontier models and **all of them** degrade as input grows, even on trivial tasks like retrieval and text copying; on LongMemEval, a ~300-token focused prompt vs a ~113k-token full prompt shows a large gap.
- The goal in one sentence (Anthropic): **find "the smallest possible set of high-signal tokens that maximize the likelihood of the desired outcome."**

Four failure modes of context (a diagnostic vocabulary, via Drew Breunig): **Poisoning** (a hallucination enters the context and is treated as fact thereafter), **Distraction** (context volume overwhelms trained knowledge), **Confusion** (irrelevant content sways the output), **Clash** (the context contradicts itself).

## 1. KV-cache: the single most important metric for a production agent

Manus, verbatim: KV-cache hit rate is "the single most important metric for a production-stage AI agent." The price spread: Anthropic cached reads cost **0.1×** the base input price (5-minute-TTL writes 1.25×, 1-hour writes 2.0×); DeepSeek's hit/miss spread is 50–120×. Monitor hit rate continuously as a core ops metric, not an occasional check.

### The three iron rules of prefix stability

1. **Byte-stable prefix.** One differing token invalidates everything after it. The classic mistake: a second-precision timestamp in the system prompt → every request misses, you pay the write premium forever and never see the discounted read price. If you must give the time, put it at the end of the messages or use date granularity only.
2. **Append-only.** Never rewrite past actions/observations; to "update" state, append a new version at the end. Hidden trap: **JSON serialization must be deterministic** (many languages don't guarantee dict key order — Python needs `sort_keys=True`; Swift/Go runtimes shuffle tool_use JSON key order).
3. **Everything volatile goes last**: static → semi-static → dynamic, strictly front to back.

### Anthropic manual-breakpoint details

- The cache hierarchy is strictly **tools → system → messages**. **Changing a tool definition invalidates all three layers**; toggling web search/citations invalidates system+messages; changing tool_choice or adding/removing images invalidates messages. This is the root reason for "never dynamically add/remove tools."
- Core rule: **place the breakpoint on the last block whose prefix is identical across requests.** At most 4 explicit breakpoints per request; on lookup the system walks back up to 20 blocks from a breakpoint to find a previously written cache entry (note: it can only find positions that were actually written by earlier requests — "the content is stable" is not by itself enough).
- Prompts below the per-model minimum cacheable size (512–4096 tokens depending on model) are **silently not cached** — the classic "thought it was on but it wasn't." Verify via usage fields: `cache_read_input_tokens` / `cache_creation_input_tokens`; `input_tokens` counts only what comes after the last breakpoint.
- When mixing TTLs, 1-hour blocks must precede 5-minute blocks. You can pre-warm the cache with a `max_tokens: 0` request (requires explicit breakpoints).
- Hits within TTL refresh it for free; the cache becomes available only after the first response begins — concurrent cold-start requests will all miss.

### OpenAI / self-hosted differences

- OpenAI is fully automatic prefix matching: the first 1,024 tokens must match character-for-character, then increments of 128; routing hashes roughly the first 256 tokens. Above ~15 req/min on one `prompt_cache_key` it starts missing — spread across keys with a stable key↔prefix mapping.
- Self-hosted inference (vLLM): explicitly enable prefix caching and **route by session ID** so the same conversation lands on the same machine — otherwise the cache lives on a box you never hit.

## 2. Tool availability: mask, don't remove

As tools multiply, the temptation is to add/remove available tools per state — wrong. Two failure modes: tool definitions sit at the front of the cache, any change invalidates everything after; and past observations still reference removed tools, confusing the model into hallucination.

The right approach (Manus): keep tools **resident in full**, and mask at sampling time via constrained decoding / logits masking / `tool_choice`/`allowed_tools`. Supporting design: **consistent name prefixes** (`browser_*`, `shell_*`) so "restrict to a tool family" degenerates into prefilling a prefix. OpenAI's `allowed_tools` parameter states the motive explicitly: restrict the subset **without changing the tools list**, preserving cache hits.

## 3. The three techniques for long tasks

Pick by task shape (Anthropic):

| Technique | Fits | Key points |
| --- | --- | --- |
| **Compaction** | Conversational flows with lots of back-and-forth | Trigger lines: Claude Code at 95% of the window, Codex at 90%. Tuning order: **maximize recall first** (the summary prompt captures every relevant fact in the trace), then raise precision. Lowest-hanging fruit: clear raw tool results deep in history. Failure fallback: trim the oldest history item and retry (Codex). Repeated compaction degrades accuracy — Codex tells the user so, verbatim |
| **Structured notes** | Iterative work with clear milestones | Persist state outside the window (NOTES.md / todo files), read it back after resets. Claude playing Pokémon maintained precise counts across thousands of steps this way |
| **Subagents** | Research/analysis where parallel exploration pays | A subagent burns tens of thousands of tokens exploring but **returns only a 1,000–2,000-token distilled summary**; the investigation debris stays inside the subagent |

**The filesystem as ultimate context** (Manus): no window fits a whole PDF observation. Key principle: **compression must be restorable** — drop the page body but keep the URL, drop the document content but keep the path; the model re-reads on demand.

**Recitation** (Manus; tasks average ~50 tool calls): maintain a todo.md, rewrite it after each step, and keep it at the **end** of the context — continually pulling the global plan back into the model's most recent attention span, countering lost-in-the-middle, with zero architecture changes.

**Just-in-time retrieval beats pre-loading**: the agent holds lightweight identifiers (paths, queries, URLs) and loads on demand with grep/head/tail instead of stuffing everything in before inference. Metadata is itself signal (a file named the same under `tests/` vs `src/` means different things). Anthropic's explicit ranking: agentic search (grep) is usually slower than semantic search but more accurate, easier to maintain, and more transparent. Hybrids are legitimate: small always-relevant files (CLAUDE.md-style) dropped in up front, everything else just-in-time.

**Progressive disclosure**: skill/tool metadata (~100 tokens) stays resident; the body loads on trigger; scripts and resources load on demand — the amount of context you can attach this way is "effectively unbounded." Same for tool definitions: Codex's tool_search, the Agents SDK's defer_loading — "give a directory first, fetch full text on use."

## 4. Errors and few-shot

- **Keep failure records in context** (Manus's most counterintuitive rule): erasing failure erases the evidence — the model can't update its priors to avoid the same mistake. The compromise with "keep context short": keep **compressed error summaries** (12-Factor, Factor 9).
- **Don't get few-shotted**: a run of same-shaped action-observation pairs locks the model into that rhythm of mechanical repetition (the résumé-screening example). Fix: introduce controlled diversity in serialization templates/wording.
- **Two failed corrections → restart the context** (Claude Code best practices): continuing to correct inside a context polluted by failed attempts is negative-return; fold what you learned into a better initial prompt and start over.

## 5. Preserve reasoning context across turns

For reasoning models doing function calling: pass the returned reasoning items back on subsequent requests (or use server-side session state). OpenAI measured Tau-Bench Retail going **73.9% → 78.2%** — purely an API-usage change, no prompt change. When handing off across providers, thinking blocks can only degrade to text (pi's approach); "anything that actually matters for correctness or recovery has to live with you."

## Sources

- https://manus.im/blog/Context-Engineering-for-AI-Agents-Lessons-from-Building-Manus
- https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents
- https://platform.claude.com/docs/en/build-with-claude/prompt-caching
- https://learn.microsoft.com/en-us/azure/foundry/openai/how-to/prompt-caching
- https://api-docs.deepseek.com/guides/kv_cache
- https://www.trychroma.com/research/context-rot
- https://www.langchain.com/blog/context-engineering-for-agents (write/select/compress/isolate)
- https://github.com/humanlayer/12-factor-agents
- https://cookbook.openai.com/examples/gpt-5/gpt-5_prompting_guide (reasoning-item reuse)
- https://github.com/openai/codex (codex-rs/core/src/compact.rs)
- https://code.claude.com/docs/en/best-practices
