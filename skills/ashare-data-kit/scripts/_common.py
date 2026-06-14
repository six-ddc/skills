"""Shared helpers for the ashare-data-kit scripts.

This module is NOT a standalone script — it is imported by the per-layer entry
scripts in this directory (quotes.py / signals.py / ...). Those entry scripts
carry the PEP 723 dependency block; this file only assumes `requests` (and
`pandas` lazily, only when rendering tables).

Why a shared module: every East money endpoint must go through the same
throttled session to avoid IP bans, and every script normalizes tickers and
renders output the same way. Centralizing that keeps behavior consistent and
the per-layer scripts thin.
"""
import argparse
import json as _json
import random
import time

import requests


# ── Ticker / market helpers ──────────────────────────────────────────────
def norm_ticker(s: str) -> str:
    """Normalize the many ticker formats users paste into a bare 6-digit code.

    688017 / SH688017 / sh688017 / 688017.SH / 688017.sh / SZ000001 / BJ832000
    all collapse to the 6 digits. Anything without digits is returned uppercased
    so the caller still gets something usable rather than a crash.
    """
    s = str(s).strip().upper()
    if "." in s:                       # strip suffix like 688017.SH
        s = s.split(".")[0]
    for p in ("SH", "SZ", "BJ"):       # strip prefix like SH688017
        if s.startswith(p):
            s = s[len(p):]
            break
    digits = "".join(ch for ch in s if ch.isdigit())
    return digits.zfill(6) if digits else s


def get_prefix(code: str) -> str:
    """6-digit code → market prefix used by Tencent/Sina (sh / sz / bj)."""
    code = norm_ticker(code)
    if code.startswith(("6", "9")):
        return "sh"
    if code.startswith("8"):
        return "bj"
    return "sz"


def market_symbol(code: str) -> str:
    """Code → exchange-prefixed symbol for Tencent/Sina (sh600519 / sz000001 / bj920002).

    Respects an explicit sh/sz/bj prefix (or .SH/.SZ/.BJ suffix) in the input, so
    index codes like sh000001 (上证指数) don't collide with sz000001 (平安银行).
    Falls back to deriving the prefix from the number when none is given.
    """
    s = str(code).strip().lower()
    for p in ("sh", "sz", "bj"):
        if s.startswith(p):
            return f"{p}{norm_ticker(code)}"
    base, _, suf = s.partition(".")
    if suf in ("sh", "sz", "bj"):
        return f"{suf}{norm_ticker(base)}"
    code6 = norm_ticker(code)
    return f"{get_prefix(code6)}{code6}"


def secid(code: str) -> str:
    """6-digit code → East money secid (1.xxx for SH, 0.xxx for SZ/others)."""
    code = norm_ticker(code)
    return f"1.{code}" if code.startswith(("6", "9")) else f"0.{code}"


# ── East money anti-ban: global throttle + session reuse ─────────────────
# East money HTTP endpoints (push2 / datacenter / reportapi / search / np-weblist)
# have rate-control: >5 req/s, ≥10 concurrent conns, or ≥200 req/min from one IP
# triggers a temporary block. Every eastmoney.com request goes through em_get():
# serial throttle (min interval + jitter) + Keep-Alive session reuse. Batch jobs
# should raise EM_MIN_INTERVAL. See references/data-sources.md for the full rules.
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
DATACENTER_URL = "https://datacenter-web.eastmoney.com/api/data/v1/get"

EM_SESSION = requests.Session()
EM_SESSION.headers.update({"User-Agent": UA})
EM_MIN_INTERVAL = 1.0          # min seconds between eastmoney calls; raise to 1.5~2 for batch
_em_last_call = [0.0]


def em_get(url, params=None, headers=None, timeout=15, **kwargs):
    """Throttled East money GET. All eastmoney.com endpoints must use this."""
    wait = EM_MIN_INTERVAL - (time.time() - _em_last_call[0])
    if wait > 0:
        time.sleep(wait + random.uniform(0.1, 0.5))
    try:
        return EM_SESSION.get(url, params=params, headers=headers, timeout=timeout, **kwargs)
    finally:
        _em_last_call[0] = time.time()


def eastmoney_datacenter(report_name, columns="ALL", filter_str="", page_size=50,
                         sort_columns="", sort_types="-1"):
    """East money datacenter unified query — shared by 龙虎榜/解禁/融资融券/大宗交易/
    股东户数/分红. Returns the `result.data` list, or [] when empty/blocked."""
    params = {
        "reportName": report_name, "columns": columns,
        "filter": filter_str, "pageNumber": "1", "pageSize": str(page_size),
        "sortColumns": sort_columns, "sortTypes": sort_types,
        "source": "WEB", "client": "WEB",
    }
    r = em_get(DATACENTER_URL, params=params, timeout=15)
    d = r.json()
    if d.get("result") and d["result"].get("data"):
        return d["result"]["data"]
    return []


def df_records(df) -> list[dict]:
    """DataFrame → list[dict], promoting a named index to a column only when it
    carries info and won't collide (mootdx bars already has a `datetime` column,
    so a blind reset_index() raises 'cannot insert datetime, already exists')."""
    if df is None or len(df) == 0:
        return []
    if df.index.name and df.index.name not in df.columns:
        df = df.reset_index()
    return df.to_dict("records")


# ── Output rendering ─────────────────────────────────────────────────────
def output(obj, as_json: bool = False):
    """Render a CLI result.

    --json  → pretty UTF-8 JSON (machine-friendly, for chaining/re-parsing).
    default → human-readable: list[dict] as a pandas table, dict as key: value
              lines (nested values shown compactly), scalars as-is.
    """
    if as_json:
        print(_json.dumps(obj, ensure_ascii=False, indent=2, default=str))
        return

    if isinstance(obj, list):
        if not obj:
            print("(空 / no data)")
            return
        if isinstance(obj[0], dict):
            try:
                import pandas as pd
                with pd.option_context("display.max_rows", None,
                                       "display.max_columns", None,
                                       "display.width", 220,
                                       "display.unicode.east_asian_width", True):
                    print(pd.DataFrame(obj).to_string(index=False))
                return
            except Exception:
                pass
        for it in obj:
            print(it)
        return

    if isinstance(obj, dict):
        for k, v in obj.items():
            if isinstance(v, (list, dict)):
                print(f"{k}: {_json.dumps(v, ensure_ascii=False, default=str)[:600]}")
            else:
                print(f"{k}: {v}")
        return

    print(obj)


# ── Argparse scaffolding ─────────────────────────────────────────────────
def build_cli(description: str):
    """Return (parser, subparsers, common_parent).

    `common_parent` carries the global --json flag; add every subcommand with
    `parents=[common_parent]` so `... <cmd> <args> --json` works after the
    subcommand (the natural place users type it).
    """
    parser = argparse.ArgumentParser(description=description)
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--json", action="store_true", dest="as_json",
                        help="输出原始 JSON 而非人类可读表格")
    sub = parser.add_subparsers(dest="cmd", required=True)
    return parser, sub, common
