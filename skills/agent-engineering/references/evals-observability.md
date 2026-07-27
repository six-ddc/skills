# Evals & Observability

## 0. One iron rule first

**The agent must have a verification loop it can run itself** — a test suite, build exit codes, a linter, a diff against fixtures, rendered screenshots. Without a runnable check, "looks done" is the only signal, and you personally become the verification loop. Demand evidence (test output, command results, screenshots), not "it worked" assertions. Feedback quality ranking (Claude Agent SDK): **rule-based feedback (lint/tests that say which rule failed and why) > visual feedback (for UI work) > LLM-as-judge (officially "generally not a very robust method")**.

## 1. What to measure: outcome + necessary tool set, not step-by-step trajectory

Three eval layers, each with a role: **final response / outcome** (black-box, closest to the user, but slow and can't localize which step failed), **single-step** (precise but doesn't compose into overall performance), **trajectory** (the full tool-call sequence).

The key trap: **strict trajectory matching is brittle** — most tasks have multiple equally correct paths; exact-matching tool names misses real differences, ignores tool inputs, and can't distinguish "one step off" from "completely lost." The correction (Anthropic): test "**were all the necessary tools called (order-agnostic)**" + "**was the environment's end state achieved**." Keep the transcript (process) and outcome (end state) separate: code agents judge outcome with unit tests first, then layer heuristics for quality; conversational agents check both that state actually changed (was the refund actually processed) and interaction quality.

## 2. Known LLM-as-judge biases

- Prefer **code-based graders** (fast, cheap, objective, reproducible); use an LLM judge only for open-ended judgment, with human evaluation as the gold standard for calibrating it.
- **Position bias**: swapping the presentation order of two candidates can swing win rates by 10–15 points → evaluate both orders and average.
- **Verbosity bias**: all model judges favor longer answers (+17.3%, worse than human judges' +12.9%).
- **Self-preference bias**: a model judging its own generations favors its own style → **never use the model that ran the agent as its judge**.
- Use **binary or few-level criteria**, judge each dimension separately (composite scores hallucinate), and provide an "unsure" escape.
- **Read the transcripts and grades yourself** — otherwise you can't tell whether the grader is inflating or drifting.

## 3. Stability: pass^k, not pass@k

pass@k asks "probability of getting lucky once in k tries" (approaches 1 as k grows); **pass^k asks "does it succeed every time across k runs"** (≈ p^k, exponential decay). τ-bench's finding: the strongest function-calling agents of the time succeeded under 50% per attempt; retail-domain pass^8 fell **below 25%** — **appearing able ≠ reliably able**.

Selection guide: internal tooling that just needs a solution → pass@k; anything user-facing that needs reliability → pass^k (75% single-run success → only 42% for three consecutive passes). Hence agent evals **must run every case multiple times and report variance** — one green run is one sample masquerading as a distribution. Agents have far more nondeterminism sources than plain calls: sampling, tool/environment intermediate state, error accumulation across steps.

## 4. The eval set: small and real, grown from failures

- **20–50 real cases are enough to start** (Anthropic's multi-agent system began with ~20 queries); don't wait for a perfect large set. Source priority: the checklist you already verify by hand before releases > real user-reported failures (ranked by impact) > synthetic.
- The bar for a good task: **two domain experts would independently reach the same pass/fail verdict** — ambiguous task descriptions are the leading cause of false failures.
- **Always include negatives** (requests that should be refused) **and dangerous-action cases** (irreversible operations, privilege overreach) — otherwise a high pass rate just means the questions never got pointed.
- Close the loop from production traces: an expert picks an underperforming live trace, adds the expected output, and it becomes a regression case; the golden dataset should **keep growing from production failures**, never freeze.
- Evals **saturate** (everything passable passes, no more improvement signal) → add harder tasks; pair low-pass-rate "capability" evals with high-pass-rate "regression" evals — they catch different failures.
- **Cost and latency are evaluated metrics too** (token counts, per-task cost, time-to-first-token) — otherwise "more accurate but 3× slower and 5× pricier" gets misread as pure progress.
- Cadence: run a subset per commit, the full set periodically; when a new model ships, revalidate within days using the existing evals.

(When a real-LLM eval gets flaky, attribute in this order: fixture/test-case decay first, then model capability, and only then the code.)

## 5. Tracing: agents are nondeterministic — the only replayable artifact is the full context at the time

You can't "reproduce the bug" — the same prompt takes different paths on different runs. Logging only the final answer logs nothing, because it can't answer "what did the model see, and why did it decide that."

**What to record**:
- The **full request** every turn: system prompt, all messages, tool schemas, model parameters
- Tool inputs and **raw returns** (the text as it entered the model)
- Token buckets (input / output / cache_read, mutually exclusive so nothing double-counts) and cost attribution per call
- Latency breakdown: time-to-first-token, per-token time — nested spans are what let you answer "why was this turn slow" instead of "it was slow overall"
- **Prompt name and version**
- The context-length curve across turns (early warning for context bloat)
- **Cache hit rate** (cache_read share) as a core ops metric

**Structure**: nest as `invoke_agent → chat/generation → execute_tool` (OTel GenAI semantic conventions / Langfuse trace→observation / LangSmith trace→run are all this shape); don't flatten. Trace-level user_id/session_id/tags propagate to every node; multi-turn conversations chain traces under a session.

**Practical traps**:
- Full messages/tool arguments are sensitive, large payloads — **opt-in, never default-on**; in production store externally with only a reference on the span, or your observability backend becomes a second data-leak surface.
- Truncating huge payloads must **preserve JSON structure**; hard-cutting strings makes replay unparseable.
- SDKs report asynchronously in batches; short-lived processes must flush explicitly or lose data.
- Monitor **decision patterns and interaction structure** rather than conversation content — the precedent for balancing privacy with debugging (Anthropic).

## 6. Self-check list when an agent underperforms

(The Claude Agent SDK's four questions + context-pollution checks)

1. **Misunderstanding**: does the retrieval/tool return structure deny it the information it needs?
2. **Repeated failures**: can a formal rule (lint/validation) in the tool layer detect and correct them?
3. **Can't recover from errors**: are the tools flexible enough to allow a different route?
4. **Unstable performance**: is there a representative test set with programmatic evals?
5. **Is the context polluted**: piled-up failed attempts (two corrections → restart), a tool output flooding the window, a few-shot rhythm gone mechanical.

## Sources

- https://code.claude.com/docs/en/best-practices (verification loops)
- https://claude.com/blog/building-agents-with-the-claude-agent-sdk (feedback ranking, four questions)
- https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents
- https://docs.langchain.com/langsmith/evaluation-approaches
- https://arxiv.org/abs/2406.12045 (τ-bench, pass^k)
- https://arxiv.org/pdf/2306.05685 (MT-Bench, judge biases)
- https://arxiv.org/abs/2410.21819 (self-preference bias)
- https://github.com/open-telemetry/semantic-conventions-genai
- https://langfuse.com/docs/observability/data-model , https://langfuse.com/docs/evaluation/experiments/datasets
- https://www.anthropic.com/engineering/multi-agent-research-system (tracing and production reliability)
