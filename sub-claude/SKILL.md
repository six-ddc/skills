---
name: sub-claude
description: "Batch-process data (CSV/JSONL) through Claude CLI (`claude -p`) via Python script. Use this instead of subagents when processing 10+ rows where you need fine-grained control over concurrency, model, retries, cost budget, or structured output schema — subagents are simpler for <10 items but lack these controls. Supports parallel execution, output field mapping (`_.` namespace), checkpoint/resume, and argument passthrough. Trigger on: batch processing, process each row, parallel claude calls, bulk classify/translate/extract, or scripting claude CLI."
---

# Sub-Claude — Batch-Process Data via Claude CLI

When you need to process large volumes of data (tens to thousands of rows) with AI, writing a Python script that calls `claude -p` is more flexible and controllable than using subagents. This skill provides a ready-to-use wrapper script `sub_claude.py` and usage guide.

## When to Use What

| Volume | Recommended | Why |
|--------|-------------|-----|
| < 10 items | subagent | Simple and fast, no script needed |
| 10-500 items | **sub_claude.py** (this skill) | Fine-grained concurrency, model, retry, budget control |
| 500+ items, not urgent | Anthropic Batch API | 50% discount, returns within 24h |

## Quick Start

### Example 1: Simple — CSV Translation

```bash
python sub_claude.py products.csv \
  --prompt "Translate this product description to English: {description}" \
  --output-column english_desc \
  --output results.csv \
  -- --model haiku --effort low
```

Each row's `description` column is sent to claude; the result is written to the `english_desc` column in `results.csv`. Everything after `--` is passed through to `claude -p`.

### Example 2: Structured Extraction + Multi-Field Mapping

```bash
python sub_claude.py resumes.csv \
  --prompt "Extract resume info: {raw_text}" \
  --output-map \
    "id={id}" \
    "name={_.structured.name}" \
    "email={_.structured.email}" \
    "years={_.structured.years_of_exp}" \
    "cost={_.total_cost_usd}" \
  --output results.csv \
  --concurrency 5 \
  -- --model sonnet --json-schema '{"type":"object","properties":{"name":{"type":"string"},"email":{"type":"string"},"years_of_exp":{"type":"number"}},"required":["name","email","years_of_exp"]}'
```

Note: `{id}` is an input column pass-through (preserves correlation), `{_.structured.*}` are JSON schema structured output fields, `{_.total_cost_usd}` is CLI output metadata.

### Example 3: JSONL I/O + Full Monitoring

```bash
python sub_claude.py logs.jsonl \
  --prompt "Analyze whether this log entry is anomalous and explain why: {message}" \
  --output-map \
    "log_id={log_id}" \
    "analysis={_.result}" \
    "is_error={_.is_error}" \
    "tokens_in={_.usage.input_tokens}" \
    "tokens_out={_.usage.output_tokens}" \
    "cost={_.total_cost_usd}" \
    "duration={_.duration_ms}" \
    "model={_.model}" \
  --output analysis.jsonl \
  --concurrency 3 \
  -- --model sonnet --effort medium --max-budget-usd 0.10
```

## Placeholders

Placeholders use `{...}` syntax. There are two contexts with different rules:

**In `--prompt`** — reference input data and built-in context:

| Placeholder | Description |
|-------------|-------------|
| `{column_name}` | CSV column or JSONL field from input data |
| `{_index}` | Current row index (0-based) |
| `{_work_dir}` | Working directory (`--work-dir` or cwd) |
| `{_input_file}` | Input file path |

**In `--output-map`** — reference both input data and CLI output. The `_.` prefix distinguishes them:

- **No prefix** → input field pass-through (copied as-is for correlation): `{id}`, `{name}`
- **`_.` prefix** → CLI output field (Claude's response metadata): `{_.result}`, `{_.total_cost_usd}`

```bash
--output-map "original_id={id}" "translation={_.result}" "cost={_.total_cost_usd}"
```

Available `_.` output fields:

| Placeholder | Type | Description |
|-------------|------|-------------|
| `{_.result}` | string | Model's final text response |
| `{_.is_error}` | bool | Whether an error occurred |
| `{_.subtype}` | string | `"success"` / `"error"` |
| `{_.stop_reason}` | string | `"end_turn"` / `"max_tokens"` / `"max_turns"` |
| `{_.duration_ms}` | number | Total duration (ms) |
| `{_.duration_api_ms}` | number | API-only duration (ms) |
| `{_.num_turns}` | number | Conversation turns |
| `{_.total_cost_usd}` | number | Cost per invocation (USD) |
| `{_.usage.input_tokens}` | number | Input token count |
| `{_.usage.output_tokens}` | number | Output token count |
| `{_.usage.cache_read_input_tokens}` | number | Cache hit tokens |
| `{_.usage.cache_creation_input_tokens}` | number | Cache creation tokens |
| `{_.session_id}` | string | Session ID |
| `{_.uuid}` | string | Result unique ID |
| `{_.model}` | string | Actual model name used |
| `{_.structured.field}` | any | JSON schema field (requires `--json-schema`) |
| `{_.structured.nested.field}` | any | Nested schema field, dot-separated |

## CLI Parameters

The script only recognizes the following parameters; all others are passed through to `claude -p`:

| Parameter | Description | Default |
|-----------|-------------|---------|
| `INPUT_FILE` | Input file (.csv / .jsonl) | (required) |
| `--prompt` | Prompt template | (required) |
| `--output` | Output file path | (required) |
| `--output-map` | Output mapping `"col={placeholder}"` | `ai_result={_.result}` |
| `--output-column` | Shorthand, equivalent to `--output-map "COL={_.result}"` | — |
| `--concurrency` | Max concurrency | `3` |
| `--work-dir` | Claude working directory + `{_work_dir}` placeholder | cwd |
| `--retry` | Max retries per row on recoverable errors (rate limit, server error, timeout). Exponential backoff: 1s, 2s, 4s... | `0` |
| `--limit` | Only process the first N rows (useful for testing) | all |
| `--dry-run` | Preview mode, no execution | — |

**Passthrough Parameters** (after `--`, or any unrecognized parameters):

Passed directly to `claude -p`. Common ones include:

| Parameter | Description |
|-----------|-------------|
| `--model` | Model selection (sonnet / opus / haiku) |
| `--effort` | Reasoning effort (low / medium / high / max) |
| `--system-prompt` | Custom system prompt |
| `--json-schema` | Force JSON schema output |
| `--max-budget-usd` | Per-row budget cap |
| `--bare` | Minimal mode (skip hooks/plugins) |
| `--tools ""` | Disable tools (pure Q&A) |
| `--fallback-model` | Fallback model on overload |

## Checkpoint & Resume

The script writes each completed row to the output file immediately. Output automatically includes a `_src_index` column (input row number).

If the script is interrupted (Ctrl+C, crash, network loss), simply re-run the same command. The script will:
1. Read the existing output file
2. Skip rows whose `_src_index` already exists
3. Only process remaining rows

Note: Due to concurrent execution, output rows may not be in input order. Sort by `_src_index` to restore order.

## Error Handling

A single row failure does not abort the entire batch. Failed rows:
- Are still written to the output file
- Have `_error` column populated with the error message
- Have `{_.is_error}` set to `true`

You can filter failed rows by `_error` and re-process them afterward.

## FAQ

**Q: What concurrency should I use?**
Start with 3. If you don't see 429 errors, increase to 5-10. API key users can go higher.

**Q: What if it's interrupted?**
Re-run the same command. Already completed rows are automatically skipped.

**Q: Output rows are out of order?**
Expected behavior due to concurrency. Sort by `_src_index` column.

**Q: How to retry only failed rows?**
Failed rows are written with `_error` populated. Currently requires manual filtering and re-processing.
