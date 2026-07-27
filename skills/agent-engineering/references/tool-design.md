# Tool (ACI) Design

## 0. Mindset: designing interfaces for agents = designing IDEs for humans

A tool is "a contract between a deterministic system and a non-deterministic agent" — unlike a traditional API: given the same tool, an agent may call it, skip it using common sense, or ask a clarifying question first. SWE-agent's founding argument: LM agents are a new class of end user — humans can freely ignore irrelevant information, but for a model **everything in context has a fixed cost**. When Anthropic built their SWE-bench agent they "spent more time optimizing tools than the overall prompt"; precise refinements to tool descriptions alone pushed Sonnet 3.5 to then-SOTA. **The payoff of interface design is backed by measured numbers** (see §2).

The litmus test (Anthropic): "If a human engineer can't definitively say which tool should be used in a given situation, an AI agent can't be expected to do better."

## 1. Which tools to build

- **Build around workflows, not 1:1 API endpoints.** `schedule_event` (finds availability + books internally) beats `list_users`+`list_events`+`create_event`; `search_contacts` beats `list_contacts` with the agent paging through; `search_logs` (relevant lines + context) beats raw `read_logs`. Any two functions that are always called in sequence should be merged (OpenAI: `query_location()` always followed by `mark_location()` → one function).
- **Never make the model fill in values the code already knows** (OpenAI): "Don't make the model fill arguments you already know" — if `order_id` is in scope, pass it in code. Fewer parameters is better.
- **Keep the bar for adding a tool high**: one more tool = one more option the model must weigh — a burden, not a gift. Claude Code holds at ~20 tools; OpenAI's official guidance is **fewer than 20 tools visible at the start of a turn**; the whitepaper adds that the breaking signal is **overlap**, not raw count — some systems run fine with 15+ tools while others collapse under 10 overlapping ones.
- The fix for too many tools is **progressive disclosure**, not dumping everything: Codex defers MCP tools behind a single tool_search meta-tool; the Agents SDK has `defer_loading`; RAG over tool descriptions has been reported to improve accuracy 3×.
- **Namespacing**: consistent prefixes (`asana_projects_search`, `browser_nav`) draw boundaries and reduce confusion; the prefix also doubles as a sampling-constraint handle (restricting to a tool family = prefilling a prefix). Prefix vs suffix schemes measurably affect evals — decide with your own.
- A minimalist baseline worth remembering: pi ships only **read / write / edit / bash** plus everything else through bash; system prompt + tool definitions total < 1,000 tokens, with Terminal-Bench results in the same tier as Codex/Cursor. Prefer new capabilities as "CLI script + README" rather than new tools (a 225-token README can replace a 21-tool, 13.7k-token MCP server).

## 2. SWE-agent ablations: what interface details are worth in points

On SWE-bench Lite the full ACI scores 18.0%; removing pieces (the hardest evidence for "design tool output for the token budget"):

| Design | Without it |
| --- | --- |
| File viewer with a 100-line window (line numbers + elision hints) | Full file 12.7%, 30-line window 14.3% — both too much and too little hurt |
| `edit` command with lint guardrails (rejects syntax errors, echoes the broken snippet) | No lint 15.0%, no edit command at all 10.3% |
| Compressed search output (file list only; >50 hits → asks to narrow the query) | Vim-style iterative paging 12.0% — **worse than having no search tool (15.7%)** |
| History folding (only the last 5 observations in full) | Full history 15.0% |

Companion finding: 51.7% of trajectories contain at least one failed edit; recovery after a single failure is 90.5%, but after consecutive failures it drops to 57.2% — **build the guardrail into the tool to stop the first error; don't rely on prompt reminders**. When a command produces no output, explicitly return "command ran successfully with no output" so the model doesn't think it's stuck.

## 3. Return-value design

- **Design for the token budget, not for completeness.** Claude Code truncates tool returns at 25,000 tokens by default. Pressure valves: pagination (sane defaults), ranges ("last 10"), filtering, truncation. When truncating, include guidance ("prefer several small targeted searches over one broad search").
- **Semantic identifiers, not bare UUIDs**: replacing arbitrary alphanumeric UUIDs with meaningful names (even 0-indexed IDs) measurably reduces retrieval hallucinations. Strip low-signal fields (uuid, mime_type, thumbnail URLs).
- **Offer `response_format` tiers**: the Slack example — detailed is 206 tokens (with thread_ts etc. for downstream calls) vs concise at 72. XML vs JSON vs Markdown for returns has no universal answer — decide by evals.
- **Write the truncation/continuation contract into the description** (pi): "Output is truncated to last N lines... If truncated, full output is saved to a temp file" — turning hidden behavior into a contract the model can see.
- **Dual-channel returns** (pi): `content` for the model (keep it small), `details` for UI/state reconstruction (as big as you like). UI-layer information never occupies model context.

## 4. Error handling

- **An error message teaches the agent how to fix the call**, it does not report an incident. Give actionable guidance: `The 'user' parameter requires format user_id=12345. Try: search_user(user_id=12345)` — no stack traces or error codes. Error messages can also teach token-efficient usage (nudge toward filters, pagination).
- Implementation convention (pi): **throw on tool failure; never return error text as normal content** — unified error path, UI can distinguish outcomes, no per-tool error-format conventions.
- Changing the arguments beats documenting the pitfall (poka-yoke): the model kept fumbling relative paths after cd → force absolute paths and it "used the method flawlessly."

## 5. Schemas and descriptions

- **Write descriptions like onboarding docs for a new teammate**: make implicit knowledge explicit — proprietary query formats, niche terminology, relationships between resources; the agent can't guess these. Unambiguous parameter names (`user_id`, not `user`). The "intern test": with only what the model can see, could a new hire use this correctly?
- **Layered placement** (GPT-5.1 guide): tool **capability** goes in the tool definition's description; **when to call it / what to do about missing parameters** — policy — stays in the system prompt. Never duplicate one instruction in both places.
- Enums and structured objects prevent illegal state combinations; OpenAI strict mode (structured outputs) is officially "always enable." Hard requirements: `additionalProperties: false`, every field in `required` (emulate optional with union + null); no allOf/if-then-else. **First use of a new schema pays a grammar-compilation delay** (~10s simple, minutes for complex; cached 24h) — don't assemble schemas dynamically at runtime.
- **Structured outputs are incompatible with parallel tool calls** — set `parallel_tool_calls: false` when strict mode is on.
- Diff/edit tools should **never rely on line numbers** — model-generated line numbers drift inevitably. Codex's apply_patch uses "3 lines of context + `@@` function anchors"; naive string replacement (pushing the matching complexity onto the model) is also a proven approach. Format-choice criteria (Anthropic): give the model tokens to think before committing, stay close to formats it has seen in the wild, no bookkeeping overhead (don't make it count lines, don't make it escape code inside JSON).

## 6. MCP, CLI, or scripts

- Controlled comparison (120 eval runs): the same tool as MCP vs CLI is "a wash" — **the protocol isn't the problem, bad wrappers are** ("badly designed wrappers that dump unnecessary JSON everywhere").
- MCP's real cost is resident context: Playwright MCP = 21 tools / 13.7k tokens (~7% of a window), Chrome DevTools MCP = 26 tools / 18k. And MCP results can only be transformed inside the model's context; CLIs/scripts can write files, pipe, and change output formats freely.
- Practical guidance: building a tool from scratch for users who have a shell → make a good CLI; lots of small composable operations → a script collection + a short README; reserve MCP for integrations that need standardized distribution/managed auth. Prefer plain-text output over JSON; prefer one tool with an `action` field over one tool per subcommand.
- Be clear-eyed about plan/todo tools: Codex source comments state update_plan "does not constrain the model" — it is progress visualization for the user. Don't expect it to make the agent more disciplined.

## 7. The iteration method

The prototype → eval → iterate loop (Anthropic):
1. Wrap a quick prototype; find the rough edges by hand.
2. Build eval tasks: **strong tasks are grounded in real data and take dozens of tool calls** ("schedule with Jane + attach last meeting's notes + book a room"); weak tasks are toys with the real constraints removed.
3. Run programmatically (a simple while loop suffices), collecting more than accuracy: **total runtime per task, tool-call counts, token consumption, tool-error distribution**.
4. **Read the raw transcripts**, not just summaries — redundant calls mean add pagination; frequent parameter errors mean the description is unclear.
5. Let the agent improve its own tools: feed the full eval transcripts to Claude Code to analyze and refactor tool descriptions (Anthropic admits most of their tool-writing advice came from exactly this); hold out a test set against overfitting.

A dedicated tool-testing agent that found and fixed ambiguities in tool descriptions cut subsequent agents' task completion time by 40% (Anthropic multi-agent system, measured).

## Sources

- https://www.anthropic.com/engineering/writing-tools-for-agents
- https://www.anthropic.com/engineering/building-effective-agents (ACI appendix)
- https://claude.com/blog/seeing-like-an-agent
- https://arxiv.org/abs/2405.15793 (SWE-agent, Table 3 ablations)
- https://platform.openai.com/docs/guides/function-calling
- https://platform.openai.com/docs/guides/structured-outputs
- https://github.com/openai/codex (apply-patch/parser.rs, mcp_tool_exposure.rs, plan_tool.rs)
- https://mariozechner.at/posts/2025-11-02-what-if-you-dont-need-mcp/
- https://mariozechner.at/posts/2025-08-15-mcp-vs-cli/
- https://github.com/earendil-works/pi (AgentTool interface, four-tool baseline)
