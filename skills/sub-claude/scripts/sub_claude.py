#!/usr/bin/env python3
"""
sub_claude.py — Batch-process CSV/JSONL data by calling `claude -p` in parallel.

Supports concurrency control, output field mapping (`_.` namespace),
checkpoint/resume, and argument passthrough.

Usage:
    python sub_claude.py input.csv \
        --prompt "Translate: {description}" \
        --output-map "translation={_.result}" "cost={_.total_cost_usd}" "id={id}" \
        --output output.csv \
        --concurrency 5 \
        -- --model sonnet --effort low
"""

import argparse
import asyncio
import csv
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------

def parse_args() -> tuple[argparse.Namespace, list[str]]:
    """Parse script args; collect unrecognized args as passthrough list."""
    p = argparse.ArgumentParser(
        description="Batch-process CSV/JSONL data via claude -p",
        allow_abbrev=False,
    )
    p.add_argument("input_file", help="Input file path (.csv or .jsonl)")
    p.add_argument("--prompt", required=True,
                    help="Prompt template string, or path to a .txt/.md file containing the template. "
                         "Use {col} for input columns, {_index} etc. for context")
    p.add_argument("--output", required=True,
                    help="Output file path (format detected by extension)")
    p.add_argument("--output-map", nargs="*", default=[], metavar="COL={PLACEHOLDER}",
                    help='Output mapping, e.g. "sentiment={_.result}" "id={id}"')
    p.add_argument("--output-column", default=None, metavar="COLUMN",
                    help='Shorthand: equivalent to --output-map "COLUMN={_.result}"')
    p.add_argument("--concurrency", type=int, default=3,
                    help="Max concurrency (default: 3)")
    p.add_argument("--work-dir", default=None,
                    help="Claude working directory (also available as {_work_dir} placeholder)")
    p.add_argument("--retry", type=int, default=0,
                    help="Max retries per row on recoverable errors (default: 0, exponential backoff)")
    p.add_argument("--limit", type=int, default=None,
                    help="Only process the first N rows (useful for testing)")
    p.add_argument("--dry-run", action="store_true",
                    help="Preview mode, no execution")

    args, passthrough = p.parse_known_args()

    # Strip leading "--" separator if present
    if passthrough and passthrough[0] == "--":
        passthrough = passthrough[1:]

    return args, passthrough


# ---------------------------------------------------------------------------
# Format detection & I/O
# ---------------------------------------------------------------------------

def detect_format(path: str) -> str:
    """Detect format by file extension."""
    ext = Path(path).suffix.lower()
    if ext == ".csv":
        return "csv"
    elif ext in (".jsonl", ".ndjson"):
        return "jsonl"
    else:
        raise ValueError(f"Unsupported file format: {ext} (supported: .csv / .jsonl / .ndjson)")


def load_input(path: str, fmt: str) -> list[dict]:
    """Load input data as list[dict]."""
    rows = []
    with open(path, encoding="utf-8") as f:
        if fmt == "csv":
            reader = csv.DictReader(f)
            rows = list(reader)
        else:  # jsonl
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError as e:
                    print(f"Warning: line {line_num} JSON parse failed: {e}", file=sys.stderr)
    return rows


# ---------------------------------------------------------------------------
# Output mapping
# ---------------------------------------------------------------------------

def build_output_map(args: argparse.Namespace) -> dict[str, str]:
    """Build output mapping {column_name: placeholder}.

    --output-column is shorthand, equivalent to --output-map "COLUMN={_.result}".
    If neither is specified, defaults to {"ai_result": "{_.result}"}.
    """
    output_map: dict[str, str] = {}

    if args.output_map:
        for item in args.output_map:
            if "=" not in item:
                raise ValueError(f"Invalid output-map format (expected COL={{PLACEHOLDER}}): {item}")
            col, placeholder = item.split("=", 1)
            output_map[col.strip()] = placeholder.strip()

    if args.output_column and not output_map:
        output_map[args.output_column] = "{_.result}"
    elif not output_map:
        output_map["ai_result"] = "{_.result}"

    return output_map


def resolve_dot_path(obj: Any, path: str) -> Any:
    """Traverse nested dict by dot-separated path. Returns None if not found."""
    parts = path.split(".")
    current = obj
    for part in parts:
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return None
    return current


def extract_output_fields(
    claude_json: dict,
    output_map: dict[str, str],
    input_row: dict,
    src_index: int,
) -> dict:
    """Extract fields from claude JSON and input row based on output_map."""
    result: dict[str, Any] = {"_src_index": src_index}
    placeholder_re = re.compile(r"^\{(.+)\}$")

    for col_name, placeholder_str in output_map.items():
        m = placeholder_re.match(placeholder_str)
        if not m:
            # Not a placeholder, treat as literal value
            result[col_name] = placeholder_str
            continue

        key = m.group(1)

        if key.startswith("_."):
            # Output field
            field = key[2:]  # Strip "_." prefix
            value = _extract_cli_field(claude_json, field)
        else:
            # Input field pass-through
            value = input_row.get(key)

        # Serialize complex types (dict/list) as JSON strings
        if isinstance(value, (dict, list)):
            value = json.dumps(value, ensure_ascii=False)
        result[col_name] = value

    return result


def _extract_cli_field(claude_json: dict, field: str) -> Any:
    """Extract a field from claude JSON output.

    Special handling:
    - "model": extract from modelUsage keys
    - "structured.*": parse result as JSON then traverse
    """
    if field == "model":
        model_usage = claude_json.get("modelUsage", {})
        return next(iter(model_usage.keys()), None)

    if field.startswith("structured."):
        sub_path = field[len("structured."):]
        # Prefer structured_output field (directly provided by claude)
        structured = claude_json.get("structured_output")
        if structured is None:
            # Fallback: try parsing the result field
            result_text = claude_json.get("result", "")
            try:
                structured = json.loads(result_text)
            except (json.JSONDecodeError, TypeError):
                return None
        return resolve_dot_path(structured, sub_path) if isinstance(structured, dict) else None

    # Generic dot-path traversal
    return resolve_dot_path(claude_json, field)


# ---------------------------------------------------------------------------
# Prompt rendering
# ---------------------------------------------------------------------------

def render_prompt(template: str, row: dict, index: int, work_dir: str, input_file: str) -> str:
    """Replace {xxx} placeholders in template with corresponding values."""
    builtins = {
        "_index": str(index),
        "_work_dir": work_dir,
        "_input_file": input_file,
    }

    def replacer(match: re.Match) -> str:
        key = match.group(1)
        if key in builtins:
            return builtins[key]
        if key in row:
            val = row[key]
            # Serialize complex types so nested objects render as JSON
            if isinstance(val, (dict, list)):
                return json.dumps(val, ensure_ascii=False)
            return str(val)
        # Dot-path traversal for nested JSONL fields (e.g. {user.name})
        dot_val = resolve_dot_path(row, key)
        if dot_val is not None:
            if isinstance(dot_val, (dict, list)):
                return json.dumps(dot_val, ensure_ascii=False)
            return str(dot_val)
        return match.group(0)  # unrecognized placeholder, keep as-is

    return re.sub(r"\{([^}]+)\}", replacer, template)


# ---------------------------------------------------------------------------
# Claude invocation
# ---------------------------------------------------------------------------

# Errors matching these keywords are NOT worth retrying.
# Verified sources:
#   - "not logged in"  : tested with --bare mode (CLI output)
#   - "may not exist"  : tested with invalid model name (CLI output)
#   - "invalid_request_error" : API 400 error type (error-codes.md)
#   - "authentication_error"  : API 401 error type (error-codes.md)
#   - "permission_error"      : API 403 error type (error-codes.md)
#   - "not_found_error"       : API 404 error type (error-codes.md)
#   - "request_too_large"     : API 413 error type (error-codes.md)
# Everything else (rate limit, server error, timeout, etc.) will be retried.
_NON_RECOVERABLE_KEYWORDS = [
    "not logged in",           # CLI: auth failure
    "may not exist",           # CLI: invalid model
    "invalid_request_error",   # API: 400
    "authentication_error",    # API: 401
    "permission_error",        # API: 403
    "not_found_error",         # API: 404
    "request_too_large",       # API: 413
]


def _is_recoverable(claude_json: dict) -> bool:
    """Check if the error is recoverable (worth retrying).

    Strategy: assume errors are recoverable unless we recognize them as
    non-recoverable. This is safer than matching recoverable keywords,
    since we can't predict all CLI error message formats for 429/500/529.
    """
    if not claude_json.get("is_error", False):
        return False
    result_text = str(claude_json.get("result", "")).lower()
    return not any(kw in result_text for kw in _NON_RECOVERABLE_KEYWORDS)


async def call_claude(
    prompt: str,
    passthrough_args: list[str],
    work_dir: str | None,
    max_retries: int = 0,
) -> dict:
    """Call claude -p and return the parsed JSON dict. Retries on recoverable errors."""
    cmd = ["claude", "-p", prompt, "--output-format", "json", "--no-session-persistence", "--dangerously-skip-permissions"]
    cmd += passthrough_args

    for attempt in range(max_retries + 1):
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=work_dir,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()

        stdout_text = stdout.decode().strip()
        stderr_text = stderr.decode().strip()

        # Forward subprocess stderr so the user sees startup errors, auth failures, etc.
        if stderr_text:
            print(stderr_text, file=sys.stderr)

        # Try parsing stdout JSON first (claude outputs JSON even on non-zero exit)
        try:
            parsed = json.loads(stdout_text)
        except (json.JSONDecodeError, TypeError):
            # Construct synthetic error
            err_msg = stderr_text[:500] or stdout_text[:500] or f"exit code {proc.returncode}"
            parsed = {
                "type": "result",
                "subtype": "error",
                "is_error": True,
                "result": f"PROCESS_ERROR: {err_msg}",
                "stop_reason": "error",
                "duration_ms": 0,
                "duration_api_ms": 0,
                "num_turns": 0,
                "total_cost_usd": 0,
                "usage": {"input_tokens": 0, "output_tokens": 0},
                "modelUsage": {},
                "session_id": "",
                "uuid": "",
            }

        # If success or non-recoverable error, return immediately
        if not _is_recoverable(parsed) or attempt >= max_retries:
            return parsed

        # Exponential backoff: 1s, 2s, 4s, 8s, ...
        delay = 2 ** attempt
        print(
            f"  Retrying ({attempt + 1}/{max_retries}), "
            f"waiting {delay}s...",
            file=sys.stderr,
        )
        await asyncio.sleep(delay)

    return parsed  # Should not reach here, but just in case


# ---------------------------------------------------------------------------
# Checkpoint / Resume
# ---------------------------------------------------------------------------

def load_checkpoint(output_path: str, fmt: str) -> set[int]:
    """Load set of completed _src_index values for checkpoint/resume."""
    completed: set[int] = set()
    if not os.path.exists(output_path):
        return completed

    try:
        with open(output_path, encoding="utf-8") as f:
            if fmt == "csv":
                reader = csv.DictReader(f)
                if "_src_index" not in (reader.fieldnames or []):
                    return completed
                for row in reader:
                    idx_str = row.get("_src_index", "")
                    if idx_str.isdigit():
                        completed.add(int(idx_str))
            else:  # jsonl
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        obj = json.loads(line)
                        if "_src_index" in obj:
                            completed.add(int(obj["_src_index"]))
                    except (json.JSONDecodeError, ValueError):
                        continue
    except Exception:
        pass

    return completed


# ---------------------------------------------------------------------------
# Output writing
# ---------------------------------------------------------------------------

def _read_csv_header(path: str) -> list[str] | None:
    """Read the header row from an existing CSV file. Returns None if unreadable."""
    try:
        with open(path, encoding="utf-8") as f:
            reader = csv.reader(f)
            return next(reader, None)
    except Exception:
        return None


class OutputWriter:
    """Incremental writer supporting CSV and JSONL. Thread-safe via asyncio.Lock."""

    def __init__(self, path: str, fmt: str, fieldnames: list[str], append: bool = False):
        self.path = path
        self.fmt = fmt
        self.fieldnames = fieldnames
        self.lock = asyncio.Lock()

        if append and os.path.exists(path):
            # Validate CSV header consistency on resume
            if fmt == "csv":
                existing = _read_csv_header(path)
                if existing is not None and existing != fieldnames:
                    raise ValueError(
                        f"Output map changed since last run.\n"
                        f"  Existing header: {existing}\n"
                        f"  Current header:  {fieldnames}\n"
                        f"Delete the output file to restart, or use the same --output-map."
                    )
            self.file = open(path, "a", newline="", encoding="utf-8")
            self._needs_header = False
        else:
            self.file = open(path, "w", newline="", encoding="utf-8")
            self._needs_header = True

        if self.fmt == "csv":
            self.csv_writer = csv.DictWriter(
                self.file, fieldnames=fieldnames, extrasaction="ignore"
            )
            if self._needs_header:
                self.csv_writer.writeheader()
                self.file.flush()

    async def write_row(self, row: dict):
        """Write one row and flush immediately."""
        async with self.lock:
            if self.fmt == "csv":
                self.csv_writer.writerow(row)
            else:  # jsonl
                self.file.write(json.dumps(row, ensure_ascii=False) + "\n")
            self.file.flush()

    def close(self):
        self.file.close()


def compute_fieldnames(output_map: dict[str, str]) -> list[str]:
    """Compute output column names. _src_index first, _error last."""
    return ["_src_index"] + list(output_map.keys()) + ["_error"]


# ---------------------------------------------------------------------------
# Progress tracking
# ---------------------------------------------------------------------------

class Stats:
    """Progress tracker."""

    def __init__(self, total: int, skipped: int = 0):
        self.total = total
        self.completed = 0
        self.succeeded = 0
        self.failed = 0
        self.skipped = skipped
        self.total_cost = 0.0
        self.start_time = time.time()
        self.lock = asyncio.Lock()

    async def record(self, cost: float, success: bool):
        async with self.lock:
            self.completed += 1
            self.total_cost += cost
            if success:
                self.succeeded += 1
            else:
                self.failed += 1

    def progress_line(self) -> str:
        elapsed = time.time() - self.start_time
        rate = (self.completed / elapsed * 60) if elapsed > 0 else 0
        remaining = self.total - self.completed
        eta = (remaining / (self.completed / elapsed)) if self.completed > 0 else 0
        return (
            f"[{self.completed}/{self.total}] "
            f"{rate:.1f}/min | ETA {eta:.0f}s | "
            f"ok:{self.succeeded} err:{self.failed} skip:{self.skipped} | "
            f"${self.total_cost:.4f}"
        )

    def summary(self) -> str:
        elapsed = time.time() - self.start_time
        return (
            f"\nDone! {self.total} rows total, {self.succeeded} succeeded, "
            f"{self.failed} failed, {self.skipped} skipped, "
            f"{elapsed:.1f}s elapsed, ${self.total_cost:.4f} spent"
        )


# ---------------------------------------------------------------------------
# Row processing
# ---------------------------------------------------------------------------

async def process_row(
    sem: asyncio.Semaphore,
    row: dict,
    idx: int,
    passthrough_args: list[str],
    work_dir: str,
    input_file: str,
    prompt_template: str,
    output_map: dict[str, str],
    stats: Stats,
    writer: OutputWriter,
    max_retries: int = 0,
):
    """Process one row: render prompt -> call claude -> extract fields -> write output."""
    async with sem:
        try:
            prompt = render_prompt(prompt_template, row, idx, work_dir, input_file)
        except KeyError as e:
            print(f"[row {idx}] prompt render failed: {e}", file=sys.stderr)
            error_row = {"_src_index": idx, "_error": str(e)}
            for col in output_map:
                error_row.setdefault(col, None)
            await writer.write_row(error_row)
            await stats.record(0, False)
            return

        claude_json = await call_claude(prompt, passthrough_args, work_dir, max_retries)

        output_row = extract_output_fields(claude_json, output_map, row, idx)

        is_error = claude_json.get("is_error", False)
        cost = claude_json.get("total_cost_usd", 0) or 0

        # Populate _error field: empty on success, error message on failure
        if is_error:
            output_row["_error"] = claude_json.get("result", "unknown error")
        else:
            output_row["_error"] = ""

        await writer.write_row(output_row)
        await stats.record(cost, not is_error)

        if is_error:
            err_msg = claude_json.get("result", "unknown error")
            print(f"[row {idx}] ERR | {stats.progress_line()}\n  Error: {err_msg}", file=sys.stderr)
        else:
            print(f"[row {idx}] OK | {stats.progress_line()}", file=sys.stderr)


# ---------------------------------------------------------------------------
# Dry run
# ---------------------------------------------------------------------------

def dry_run(
    args: argparse.Namespace,
    passthrough_args: list[str],
    rows: list[dict],
    output_map: dict[str, str],
    work_dir: str,
):
    """Preview mode, no actual execution."""
    print("=" * 60)
    print("DRY RUN — Preview Mode")
    print("=" * 60)
    print(f"Input file:  {args.input_file} ({len(rows)} rows)")
    print(f"Output file: {args.output}")
    print(f"Concurrency: {args.concurrency}")
    print(f"Work dir:    {work_dir}")
    print(f"Passthrough: {' '.join(passthrough_args) if passthrough_args else '(none)'}")
    if args.limit is not None:
        print(f"Limit:       {args.limit} rows")
    print()

    print("Output mapping:")
    for col, placeholder in output_map.items():
        print(f"  {col} <- {placeholder}")
    print()

    if rows:
        sample_prompt = render_prompt(args.prompt, rows[0], 0, work_dir, args.input_file)
        print("First prompt preview:")
        print("-" * 40)
        print(sample_prompt)
        print("-" * 40)

    print()
    print("Example command:")
    cmd = ["claude", "-p", "<prompt>", "--output-format", "json", "--no-session-persistence", "--dangerously-skip-permissions"]
    cmd += passthrough_args
    print(f"  {' '.join(cmd)}")
    if args.work_dir:
        print(f"  (executed in directory: {args.work_dir})")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def resolve_prompt(prompt_arg: str) -> str:
    """If prompt_arg looks like a file path and the file exists, read its content; otherwise return as-is."""
    # Quick reject: real prompts almost always contain spaces/newlines/placeholders
    if "\n" in prompt_arg or len(prompt_arg) > 500:
        return prompt_arg
    p = Path(prompt_arg)
    if p.suffix.lower() in (".txt", ".md", ".prompt") and p.is_file():
        content = p.read_text(encoding="utf-8").strip()
        print(f"Prompt loaded from file: {prompt_arg} ({len(content)} chars)", file=sys.stderr)
        return content
    return prompt_arg


async def main():
    args, passthrough_args = parse_args()
    work_dir = args.work_dir or os.getcwd()

    # Resolve prompt (inline string or file path)
    args.prompt = resolve_prompt(args.prompt)

    # Detect formats
    input_fmt = detect_format(args.input_file)
    output_fmt = detect_format(args.output)

    # Load input
    rows = load_input(args.input_file, input_fmt)
    if not rows:
        print("Input file is empty, nothing to process.", file=sys.stderr)
        return

    # --limit: only take first N rows
    if args.limit is not None:
        rows = rows[:args.limit]

    # Build output mapping
    output_map = build_output_map(args)

    # Dry run
    if args.dry_run:
        dry_run(args, passthrough_args, rows, output_map, work_dir)
        return

    # Checkpoint/resume
    checkpoint = load_checkpoint(args.output, output_fmt)
    pending = [(i, row) for i, row in enumerate(rows) if i not in checkpoint]

    if not pending:
        print("All rows already processed (checkpoint check).", file=sys.stderr)
        return

    print(
        f"Processing: {len(pending)} rows pending"
        + (f" ({len(checkpoint)} skipped)" if checkpoint else "")
        + f", concurrency={args.concurrency}",
        file=sys.stderr,
    )

    # Output file
    fieldnames = compute_fieldnames(output_map)
    writer = OutputWriter(args.output, output_fmt, fieldnames, append=bool(checkpoint))

    # Execute
    stats = Stats(total=len(pending), skipped=len(checkpoint))
    sem = asyncio.Semaphore(args.concurrency)

    tasks = [
        process_row(
            sem, row, idx, passthrough_args, work_dir,
            args.input_file, args.prompt, output_map, stats, writer,
            args.retry,
        )
        for idx, row in pending
    ]

    await asyncio.gather(*tasks)

    writer.close()
    print(stats.summary(), file=sys.stderr)


if __name__ == "__main__":
    asyncio.run(main())
