# /// script
# requires-python = ">=3.10"
# dependencies = ["requests>=2.28", "pandas>=2.0", "mootdx>=0.10"]
# ///
"""Layer 1 行情层 (real-time, does not ban IPs).

Sources, in priority order:
  mootdx (通达信, TCP 7709)  → K线 / 五档盘口 / 逐笔成交        — never bans IP
  腾讯财经 (HTTP GBK)         → 实时价 / PE / PB / 市值 / 涨跌停 — never bans IP
  百度股市通 (HTTP)          → K线自带 MA5/10/20

Commands:
  kline <code> [--period day|week|month|1m|5m|15m|30m|60m] [--count N]
  realtime <code> [<code> ...]          # 腾讯, 也支持指数/ETF
  kline-ma <code> [--start YYYYMMDD]     # 百度, 自带均线
  transaction <code> [--date YYYYMMDD]   # mootdx 逐笔成交 (非交易时段为空)

Field tables / gotchas (e.g. Tencent index 46 = PB, not 43): references/quotes.md
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import requests

from _common import build_cli, df_records, market_symbol, norm_ticker, output


# mootdx category codes for client.bars()
_PERIOD = {"day": 4, "week": 5, "month": 6,
           "1m": 7, "5m": 8, "15m": 9, "30m": 10, "60m": 11}


def mootdx_kline(code: str, period: str = "day", count: int = 10) -> list[dict]:
    """K线 via通达信 TCP. Returns rows: open/close/high/low/vol/amount/datetime."""
    from mootdx.quotes import Quotes               # lazy: only this path needs mootdx
    client = Quotes.factory(market="std")
    df = client.bars(symbol=norm_ticker(code), category=_PERIOD.get(period, 4), offset=count)
    return df_records(df)


def mootdx_transaction(code: str, date: str | None = None) -> list[dict]:
    """逐笔成交 via通达信. date=YYYYMMDD; non-trading time returns empty."""
    from mootdx.quotes import Quotes
    client = Quotes.factory(market="std")
    df = client.transaction(symbol=norm_ticker(code), date=date)
    return df_records(df)


def tencent_quote(codes: list[str]) -> list[dict]:
    """腾讯财经实时行情. Also works for indexes (000001/000300/399006) and ETFs.

    NOTE: uses requests (not urllib) so it relies on certifi's CA bundle — this
    avoids the macOS default-Python `CERTIFICATE_VERIFY_FAILED` that urllib hits.
    GBK-encoded, `~`-delimited; field indices are calibrated in references/quotes.md.
    """
    prefixed = [market_symbol(c) for c in codes]
    url = "https://qt.gtimg.cn/q=" + ",".join(prefixed)
    r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
    r.encoding = "gbk"
    data = r.text

    rows = []
    for line in data.strip().split(";"):
        if not line.strip() or "=" not in line or '"' not in line:
            continue
        key = line.split("=")[0].split("_")[-1]
        vals = line.split('"')[1].split("~")
        if len(vals) < 53:
            continue
        rows.append({
            "code": key[2:],
            "name": vals[1],
            "price": float(vals[3]) if vals[3] else 0,
            "last_close": float(vals[4]) if vals[4] else 0,
            "open": float(vals[5]) if vals[5] else 0,
            "change_pct": float(vals[32]) if vals[32] else 0,
            "high": float(vals[33]) if vals[33] else 0,
            "low": float(vals[34]) if vals[34] else 0,
            "amount_wan": float(vals[37]) if vals[37] else 0,
            "turnover_pct": float(vals[38]) if vals[38] else 0,
            "pe_ttm": float(vals[39]) if vals[39] else 0,
            "amplitude_pct": float(vals[43]) if vals[43] else 0,   # 43 = 振幅, NOT PB
            # idx 44 = 流通市值, idx 45 = 总市值 (实测校准: 中芯国际 44=2497亿 < 45=10007亿).
            # 旧版字段表把这两个写反了——在 总市值≈流通市值 的大白马上看不出来。
            "float_mcap_yi": float(vals[44]) if vals[44] else 0,
            "mcap_yi": float(vals[45]) if vals[45] else 0,
            "pb": float(vals[46]) if vals[46] else 0,              # 46 = PB
            "limit_up": float(vals[47]) if vals[47] else 0,
            "limit_down": float(vals[48]) if vals[48] else 0,
            "vol_ratio": float(vals[49]) if vals[49] else 0,
            "pe_static": float(vals[52]) if vals[52] else 0,
        })
    return rows


def sina_quote(codes: list[str]) -> list[dict]:
    """新浪实时行情快照 (hq.sinajs.cn) — 腾讯之外的第二个不封 IP 行情源,适合做兜底。

    与腾讯互补:新浪提供 现价/开高低/昨收 + 五档盘口(量单位=股,腾讯是手) + 成交量(股)/
    成交额(元),但**不含** PE/PB/换手率/涨跌停(那些用 `realtime` 走腾讯)。也支持指数。

    两个坑(均已处理):①必须带 `Referer: http://finance.sina.com.cn`,否则 403;
    ②编码是 GB18030。这里先 `r.encoding='gb18030'` 解码再按 `,` 切分——解码后的字符串里
    `,` 只出现在真正的分隔位,naive split 安全(裸字节流才有 0x7E/逗号被汉字切碎的风险)。
    """
    syms = [market_symbol(c) for c in codes]
    url = "https://hq.sinajs.cn/list=" + ",".join(syms)
    r = requests.get(url, headers={"Referer": "http://finance.sina.com.cn",
                                   "User-Agent": "Mozilla/5.0"}, timeout=10)
    r.encoding = "gb18030"

    def _f(x):
        try:
            return float(x)
        except (ValueError, TypeError):
            return 0.0

    rows = []
    for line in r.text.strip().split(";"):
        if "=" not in line or '"' not in line:
            continue
        key = line.split("=")[0].split("_")[-1]      # hq_str_sh600519 → sh600519
        f = line.split('"')[1].split(",")
        if len(f) < 32:                              # 空 payload = 坏代码/未上市
            continue
        rows.append({
            "code": key[2:] if key[:2] in ("sh", "sz", "bj") else key,
            "name": f[0],
            "open": _f(f[1]),
            "last_close": _f(f[2]),
            "price": _f(f[3]),
            "change_pct": round((_f(f[3]) - _f(f[2])) / _f(f[2]) * 100, 2) if _f(f[2]) else 0,
            "high": _f(f[4]),
            "low": _f(f[5]),
            "volume": _f(f[8]),       # 成交量(股)
            "amount": _f(f[9]),       # 成交额(元)
            "bid1": _f(f[11]), "bid1_vol": _f(f[10]),   # 买一 价/量(股)
            "ask1": _f(f[21]), "ask1_vol": _f(f[20]),   # 卖一 价/量(股)
            "date": f[30] if len(f) > 30 else "",
            "time": f[31] if len(f) > 31 else "",
        })
    return rows


def baidu_kline_with_ma(code: str, start_time: str = "") -> dict:
    """百度股市通 K线 — returns rows with ma5/ma10/ma20 already computed.

    Defensive: when 百度 PAE blocks the request it sends ResultCode != "0" and
    `Result` becomes an empty LIST (not a dict). The old code did `Result.get(...)`
    and crashed with AttributeError; here we detect a non-dict Result and return
    an empty structure with a warning instead. (Some IPs now get HTTP 403 here.)
    """
    url = "https://finance.pae.baidu.com/selfselect/getstockquotation"
    params = {
        "all": "1", "isIndex": "false", "isBk": "false", "isBlock": "false",
        "isFutures": "false", "isStock": "true", "newFormat": "1",
        "group": "quotation_kline_ab", "finClientType": "pc",
        "code": norm_ticker(code), "start_time": start_time, "ktype": "1",
    }
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/vnd.finance-web.v1+json",
        "Origin": "https://gushitong.baidu.com",
        "Referer": "https://gushitong.baidu.com/",
    }
    r = requests.get(url, params=params, headers=headers, timeout=10)
    d = r.json()
    if str(d.get("ResultCode", -1)) != "0":
        print(f"[WARN] 百度股市通 ResultCode={d.get('ResultCode')} "
              f"(部分 IP 现返回 403/风控)，返回空。", file=sys.stderr)
        return {"keys": [], "rows": []}
    result = d.get("Result")
    if not isinstance(result, dict):       # blocked → Result is [] ; degrade gracefully
        print("[WARN] 百度股市通 Result 非预期结构，返回空。", file=sys.stderr)
        return {"keys": [], "rows": []}
    md = result.get("newMarketData", {}) or {}
    return {"keys": md.get("keys", []),
            "rows": [r for r in md.get("marketData", "").split(";") if r]}


def main():
    parser, sub, common = build_cli("L1 行情层 — mootdx / 腾讯 / 百度")

    p = sub.add_parser("kline", parents=[common], help="mootdx K线")
    p.add_argument("code")
    p.add_argument("--period", default="day", choices=list(_PERIOD))
    p.add_argument("--count", type=int, default=10)

    p = sub.add_parser("realtime", parents=[common], help="腾讯实时行情(个股/指数/ETF,含PE/PB/市值/涨跌停)")
    p.add_argument("codes", nargs="+")

    p = sub.add_parser("sina", parents=[common], help="新浪实时行情(腾讯兜底,含五档盘口,无估值字段)")
    p.add_argument("codes", nargs="+")

    p = sub.add_parser("kline-ma", parents=[common], help="百度K线(自带MA5/10/20)")
    p.add_argument("code")
    p.add_argument("--start", default="")

    p = sub.add_parser("transaction", parents=[common], help="mootdx 逐笔成交")
    p.add_argument("code")
    p.add_argument("--date", default=None)

    args = parser.parse_args()

    if args.cmd == "kline":
        output(mootdx_kline(args.code, args.period, args.count), args.as_json)
    elif args.cmd == "realtime":
        output(tencent_quote(args.codes), args.as_json)
    elif args.cmd == "sina":
        output(sina_quote(args.codes), args.as_json)
    elif args.cmd == "kline-ma":
        output(baidu_kline_with_ma(args.code, args.start), args.as_json)
    elif args.cmd == "transaction":
        output(mootdx_transaction(args.code, args.date), args.as_json)


if __name__ == "__main__":
    main()
