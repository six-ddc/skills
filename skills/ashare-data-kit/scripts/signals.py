# /// script
# requires-python = ">=3.10"
# dependencies = ["requests>=2.28", "pandas>=2.0"]
# ///
"""Layer 3 信号层 (endpoint-heavy: 同花顺热点/北向 + 东财板块/资金流/龙虎榜/解禁/行业).

Sources, by endpoint:
  同花顺 zx.10jqka.com.cn  → 当日强势股 + 题材归因 reason tags (人工运营, 独家)
  同花顺 data.hexin.cn     → 北向资金 hsgtApi 实时分钟流向 (+ 本地 CSV 自缓存历史)
  东财 push2 slist         → 个股所属板块/概念归属
  东财 push2 fflow         → 个股资金流向 (分钟级, 单位=元)
  东财 datacenter          → 龙虎榜 (个股 / 全市场) / 限售解禁
  东财 push2 clist         → 全行业涨跌幅排名 (同花顺加了反爬 401)

NOTE: 同花顺端点用普通 requests; 所有东财端点必须走 em_get (统一限流, 防封 IP),
      不要自建 session。所有 code 入参先过 norm_ticker。

Commands:
  hot [--date YYYY-MM-DD]                                 # 同花顺当日强势股 + reason
  northbound [--save YYYY-MM-DD]                          # 北向实时分钟; --save 写当日收盘到本地缓存
  blocks <code>                                           # 东财个股所属板块/概念
  fundflow <code>                                         # 东财分钟级资金流 (单位=元)
  dragon <code> --date YYYY-MM-DD [--look-back 30]        # 个股龙虎榜
  market-dragon [--date YYYY-MM-DD] [--min-net-buy FLOAT] # 全市场龙虎榜
  lockup <code> [--date YYYY-MM-DD] [--forward-days 90]   # 限售解禁日历
  industry [--top-n 20]                                   # 全行业涨跌幅排名

Field tables / gotchas (reason=人工运营 tags / 北向自缓存 / push2 单位=元 …): references/signals.md
"""
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
import requests

from _common import (UA, build_cli, df_records, eastmoney_datacenter, em_get,
                     norm_ticker, output)


# ── 3.1 同花顺热点 — 当日强势股 + 题材归因 reason tags (同花顺, 普通 requests) ──
def ths_hot_reason(date: str = None) -> pd.DataFrame:
    """
    同花顺当日强势股归因。
    date: 'YYYY-MM-DD' 格式，None=今天
    返回 DataFrame，含每只股票的题材标签 (reason)。

    实测: 73ms 拿到 ~125 只 + 完整字段
    """
    from datetime import date as _date
    if date is None:
        date = _date.today().strftime("%Y-%m-%d")

    url = (
        f"http://zx.10jqka.com.cn/event/api/getharden/"
        f"date/{date}/orderby/date/orderway/desc/charset/GBK/"
    )
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "Chrome/117.0.0.0 Safari/537.36"
        )
    }
    r = requests.get(url, headers=headers, timeout=10)
    data = r.json()
    if data.get("errocode", 0) != 0:
        raise RuntimeError(f"同花顺热点错误: {data.get('errormsg', '')}")

    rows = data.get("data") or []
    df = pd.DataFrame(rows)
    if df.empty:
        return df

    # 字段重命名（中文友好）
    rename_map = {
        "name": "名称", "code": "代码", "reason": "题材归因",
        "close": "收盘价", "zhangdie": "涨跌额", "zhangfu": "涨幅%",
        "huanshou": "换手率%", "chengjiaoe": "成交额",
        "chengjiaoliang": "成交量", "ddejingliang": "大单净量",
        "market": "市场",
    }
    df = df.rename(columns=rename_map)
    return df


# ── 3.2 同花顺北向资金 — hsgtApi 实时分钟流向 + 本地自缓存历史 (同花顺) ──
HSGT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "Chrome/117.0.0.0 Safari/537.36"
    ),
    "Host": "data.hexin.cn",
    "Referer": "https://data.hexin.cn/",
}


def hsgt_realtime() -> pd.DataFrame:
    """
    沪深股通当日实时分钟流向（含集合竞价 09:10–15:00，262 个时间点）。
    返回字段: time, hgt(沪股通累计净买入), sgt(深股通累计净买入)
    单位: 亿元
    """
    url = "https://data.hexin.cn/market/hsgtApi/method/dayChart/"
    r = requests.get(url, headers=HSGT_HEADERS, timeout=10)
    d = r.json()
    times = d.get("time", [])
    hgt = d.get("hgt", [])
    sgt = d.get("sgt", [])

    n = len(times)
    return pd.DataFrame({
        "time": times,
        "hgt_yi": hgt[:n] + [None] * (n - len(hgt)),
        "sgt_yi": sgt[:n] + [None] * (n - len(sgt)),
    })


# === 自缓存辅助函数 ===

def _northbound_cache_path() -> Path:
    """北向资金本地 CSV 缓存路径"""
    p = Path.home() / ".tradingagents" / "cache" / "northbound_daily.csv"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def _save_northbound_snapshot(date: str, hgt: float, sgt: float):
    """写入/更新当天北向收盘数据到 CSV"""
    path = _northbound_cache_path()
    rows = {}
    if path.exists():
        for line in path.read_text().strip().split("\n")[1:]:
            parts = line.split(",")
            if len(parts) == 3:
                rows[parts[0]] = line
    rows[date] = f"{date},{hgt},{sgt}"
    with open(path, "w") as f:
        f.write("date,hgt,sgt\n")
        for d in sorted(rows.keys()):
            f.write(rows[d] + "\n")


def _load_northbound_history(n: int = 20) -> pd.DataFrame:
    """读取最近 N 天北向历史"""
    path = _northbound_cache_path()
    if not path.exists():
        return pd.DataFrame()
    df = pd.read_csv(path)
    return df.tail(n)


# ── 3.3 东财 slist — 个股所属板块/概念归属 (走 em_get) ──
def eastmoney_concept_blocks(code: str) -> dict:
    """
    个股所属板块/概念归属（东财 slist，一次请求拿全，已内置限流）。
    返回: {total, boards: [{name, code(BK码), change_pct, lead_stock}], concept_tags: [板块名...]}
    boards 混合 行业/概念/地域，板块名自解释；concept_tags 是所有板块名的便捷列表。
    """
    code = norm_ticker(code)
    market_code = 1 if code.startswith("6") else 0
    params = {
        "fltt": "2", "invt": "2",
        "secid": f"{market_code}.{code}",
        "spt": "3", "pi": "0", "pz": "200", "po": "1",
        "fields": "f12,f14,f3,f128",
    }
    headers = {"User-Agent": UA, "Referer": "https://quote.eastmoney.com/"}
    try:
        r = em_get("https://push2.eastmoney.com/api/qt/slist/get",
                   params=params, headers=headers, timeout=15)
        d = r.json()
    except Exception as e:
        print(f"[WARN] 东财板块归属请求失败: {e}")
        return {"total": 0, "boards": [], "concept_tags": []}

    diff = (d.get("data") or {}).get("diff") or {}
    items = diff.values() if isinstance(diff, dict) else diff
    boards = []
    for it in items:
        boards.append({
            "name": it.get("f14", ""),         # 板块名
            "code": it.get("f12", ""),         # BK 板块代码
            "change_pct": it.get("f3", ""),    # 板块当日涨跌幅
            "lead_stock": it.get("f128", ""),  # 板块龙头股
        })
    return {
        "total": len(boards),
        "boards": boards,
        "concept_tags": [b["name"] for b in boards],
    }


# ── 3.4 东财 push2 — 个股资金流向 (分钟级, 单位=元, 走 em_get) ──
def eastmoney_fund_flow_minute(code: str) -> list[dict]:
    """
    个股资金流向（分钟级，当日盘中）。
    code: 6位股票代码
    返回: [{time, main_net, small_net, mid_net, large_net, super_net}, ...]
    单位: 元
    """
    code = norm_ticker(code)
    secid = f"1.{code}" if code.startswith("6") else f"0.{code}"
    url = "https://push2.eastmoney.com/api/qt/stock/fflow/kline/get"
    params = {
        "secid": secid, "klt": 1,
        "fields1": "f1,f2,f3,f7",
        "fields2": "f51,f52,f53,f54,f55,f56,f57",
    }
    headers = {
        "User-Agent": UA,
        "Referer": "https://quote.eastmoney.com/",
        "Origin": "https://quote.eastmoney.com",
    }
    try:
        r = em_get(url, params=params, headers=headers, timeout=10)
        d = r.json()
    except Exception as e:
        print(f"[WARN] push2 资金流请求失败: {e}", file=sys.stderr)
        return []

    rows = []
    for line in d.get("data", {}).get("klines", []):
        parts = line.split(",")
        if len(parts) >= 6:
            rows.append({
                "time": parts[0],
                "main_net": float(parts[1]),
                "small_net": float(parts[2]),
                "mid_net": float(parts[3]),
                "large_net": float(parts[4]),
                "super_net": float(parts[5]),
            })
    return rows


# ── 3.5 龙虎榜席位 — 个股上榜记录 + 买卖席位 TOP5 + 机构动向 (东财 datacenter) ──
def dragon_tiger_board(code: str, trade_date: str, look_back: int = 30) -> dict:
    """
    龙虎榜数据聚合。
    trade_date: YYYY-MM-DD
    look_back: 回看天数
    返回: {records: [...], seats: {buy: [...], sell: [...]}, institution: {...}}
    """
    code = norm_ticker(code)
    start = datetime.strptime(trade_date, "%Y-%m-%d") - timedelta(days=look_back)
    start_str = start.strftime("%Y-%m-%d")

    # 1. 上榜记录
    records = []
    data = eastmoney_datacenter(
        "RPT_DAILYBILLBOARD_DETAILSNEW",
        filter_str=f"(TRADE_DATE>='{start_str}')(TRADE_DATE<='{trade_date}')(SECURITY_CODE=\"{code}\")",
        page_size=50,
        sort_columns="TRADE_DATE", sort_types="-1",
    )
    for row in data:
        records.append({
            "date": str(row.get("TRADE_DATE", ""))[:10],
            "reason": row.get("EXPLANATION", ""),
            "net_buy": round((row.get("BILLBOARD_NET_AMT") or 0) / 10000, 1),
            "turnover": round(float(row.get("TURNOVERRATE") or 0), 2),
        })

    # 2. 最近上榜的买卖席位
    seats = {"buy": [], "sell": []}
    buy_data, sell_data = [], []
    if records:
        latest_date = records[0]["date"]
        # 买入席位
        buy_data = eastmoney_datacenter(
            "RPT_BILLBOARD_DAILYDETAILSBUY",
            filter_str=f"(TRADE_DATE='{latest_date}')(SECURITY_CODE=\"{code}\")",
            page_size=10,
            sort_columns="BUY", sort_types="-1",
        )
        for row in buy_data[:5]:
            seats["buy"].append({
                "name": row.get("OPERATEDEPT_NAME", ""),
                "buy_amt": round((row.get("BUY") or 0) / 10000, 1),
                "sell_amt": round((row.get("SELL") or 0) / 10000, 1),
                "net": round((row.get("NET") or 0) / 10000, 1),
            })
        # 卖出席位
        sell_data = eastmoney_datacenter(
            "RPT_BILLBOARD_DAILYDETAILSSELL",
            filter_str=f"(TRADE_DATE='{latest_date}')(SECURITY_CODE=\"{code}\")",
            page_size=10,
            sort_columns="SELL", sort_types="-1",
        )
        for row in sell_data[:5]:
            seats["sell"].append({
                "name": row.get("OPERATEDEPT_NAME", ""),
                "buy_amt": round((row.get("BUY") or 0) / 10000, 1),
                "sell_amt": round((row.get("SELL") or 0) / 10000, 1),
                "net": round((row.get("NET") or 0) / 10000, 1),
            })

    # 3. 机构买卖统计（从买卖席位明细中筛选 OPERATEDEPT_CODE="0" 即机构专用席位）
    institution = {"buy_amt": 0, "sell_amt": 0, "net_amt": 0}
    for detail_data, side in [(buy_data, "buy"), (sell_data, "sell")]:
        for row in detail_data:
            if str(row.get("OPERATEDEPT_CODE", "")) == "0":
                amt = (row.get("BUY") or 0) if side == "buy" else (row.get("SELL") or 0)
                if side == "buy":
                    institution["buy_amt"] += amt
                else:
                    institution["sell_amt"] += amt
    institution["buy_amt"] = round(institution["buy_amt"] / 10000, 1)
    institution["sell_amt"] = round(institution["sell_amt"] / 10000, 1)
    institution["net_amt"] = round(institution["buy_amt"] - institution["sell_amt"], 1)

    return {"records": records, "seats": seats, "institution": institution}


# ── 3.6 限售解禁日历 — 历史解禁 + 未来 N 天待解禁 (东财 datacenter) ──
def lockup_expiry(code: str, trade_date: str, forward_days: int = 90) -> dict:
    """
    限售解禁日历。
    返回: {history: [...], upcoming: [...]}
    """
    code = norm_ticker(code)
    # 1. 历史解禁记录
    history_data = eastmoney_datacenter(
        "RPT_LIFT_STAGE",
        filter_str=f"(SECURITY_CODE=\"{code}\")",
        page_size=15,
        sort_columns="FREE_DATE", sort_types="-1",
    )
    history = []
    for row in history_data:
        history.append({
            "date": str(row.get("FREE_DATE", ""))[:10],
            "type": row.get("LIMITED_STOCK_TYPE", ""),
            "shares": row.get("FREE_SHARES_NUM", 0),
            "ratio": row.get("FREE_RATIO", 0),
        })

    # 2. 未来待解禁
    end_date = datetime.strptime(trade_date, "%Y-%m-%d") + timedelta(days=forward_days)
    end_str = end_date.strftime("%Y-%m-%d")
    upcoming_data = eastmoney_datacenter(
        "RPT_LIFT_STAGE",
        filter_str=f"(SECURITY_CODE=\"{code}\")(FREE_DATE>='{trade_date}')(FREE_DATE<='{end_str}')",
        page_size=20,
        sort_columns="FREE_DATE", sort_types="1",
    )
    upcoming = []
    for row in upcoming_data:
        upcoming.append({
            "date": str(row.get("FREE_DATE", ""))[:10],
            "type": row.get("LIMITED_STOCK_TYPE", ""),
            "shares": row.get("FREE_SHARES_NUM", 0),
            "ratio": row.get("FREE_RATIO", 0),
        })

    return {"history": history, "upcoming": upcoming}


# ── 3.7 行业板块排名 (同花顺加了反爬 401, 走 em_get) ──
def industry_comparison(top_n: int = 20) -> dict:
    """
    全行业涨跌幅排名（东财行业板块，~100 个行业）。
    返回: {top: [...], bottom: [...], total: int}
    """
    url = "https://push2.eastmoney.com/api/qt/clist/get"
    params = {
        "pn": "1", "pz": "100", "po": "1", "np": "1",
        "fltt": "2", "invt": "2",
        "fs": "m:90+t:2",
        "fields": "f2,f3,f4,f12,f13,f14,f104,f105,f128,f136,f140,f141,f207",
    }
    headers = {"User-Agent": UA}
    try:
        r = em_get(url, params=params, headers=headers, timeout=15)
        d = r.json()
    except Exception as e:
        # push2 对部分大陆住宅 IP 间歇风控(RemoteDisconnected),优雅降级而非崩溃
        print(f"[WARN] push2 行业板块请求失败: {e}", file=sys.stderr)
        return {"top": [], "bottom": [], "total": 0}
    items = d.get("data", {}).get("diff", [])
    if not items:
        return {"top": [], "bottom": [], "total": 0}

    rows = []
    for i, item in enumerate(items):
        rows.append({
            "rank": i + 1,
            "name": item.get("f14", ""),
            "change_pct": item.get("f3", 0),
            "code": item.get("f12", ""),
            "up_count": item.get("f104", 0),
            "down_count": item.get("f105", 0),
            "leader": item.get("f140", ""),
            "leader_change": item.get("f136", 0),
        })

    return {
        "top": rows[:top_n],
        "bottom": rows[-top_n:],
        "total": len(rows),
    }


# ── 3.8 全市场龙虎榜 (东财 datacenter) ──
def daily_dragon_tiger(trade_date: str = None, min_net_buy: float = None) -> dict:
    """
    全市场龙虎榜。
    trade_date: YYYY-MM-DD（默认当日）
    min_net_buy: 净买入下限（万元），None 不过滤
    返回: {date, total_records, stocks: [{code, name, reason, close, change_pct,
           net_buy_wan, buy_wan, sell_wan, turnover_pct}]}
    """
    if trade_date is None:
        trade_date = datetime.now().strftime("%Y-%m-%d")

    data = eastmoney_datacenter(
        "RPT_DAILYBILLBOARD_DETAILSNEW",
        filter_str=f"(TRADE_DATE>='{trade_date}')(TRADE_DATE<='{trade_date}')",
        page_size=500,
        sort_columns="BILLBOARD_NET_AMT", sort_types="-1",
    )
    if not data:
        return {"date": trade_date, "total_records": 0, "stocks": [],
                "note": "无数据（非交易日或盘后未更新）"}

    actual_date = str(data[0].get("TRADE_DATE", ""))[:10] if data else trade_date
    stocks = []
    for row in data:
        net_buy = (row.get("BILLBOARD_NET_AMT") or 0) / 10000
        if min_net_buy is not None and net_buy < min_net_buy:
            continue
        stocks.append({
            "code": row.get("SECURITY_CODE", ""),
            "name": row.get("SECURITY_NAME_ABBR", ""),
            "reason": row.get("EXPLANATION", ""),
            "close": row.get("CLOSE_PRICE") or 0,
            "change_pct": round(float(row.get("CHANGE_RATE") or 0), 2),
            "net_buy_wan": round(net_buy, 1),
            "buy_wan": round((row.get("BILLBOARD_BUY_AMT") or 0) / 10000, 1),
            "sell_wan": round((row.get("BILLBOARD_SELL_AMT") or 0) / 10000, 1),
            "turnover_pct": round(float(row.get("TURNOVERRATE") or 0), 2),
        })
    return {"date": actual_date, "total_records": len(stocks), "stocks": stocks}


def main():
    parser, sub, common = build_cli(
        "L3 信号层 — 同花顺热点/北向 + 东财板块/资金流/龙虎榜/解禁/行业")

    p = sub.add_parser("hot", parents=[common], help="同花顺当日强势股 + 题材归因 reason")
    p.add_argument("--date", default=None, help="YYYY-MM-DD, 默认今天")

    p = sub.add_parser("northbound", parents=[common],
                       help="同花顺北向资金实时分钟流向 (+ 本地自缓存历史)")
    p.add_argument("--save", default=None, metavar="YYYY-MM-DD",
                   help="把当日收盘 hgt/sgt 写入本地 CSV 缓存")

    p = sub.add_parser("blocks", parents=[common], help="东财个股所属板块/概念归属")
    p.add_argument("code")

    p = sub.add_parser("fundflow", parents=[common], help="东财个股分钟级资金流 (单位=元)")
    p.add_argument("code")

    p = sub.add_parser("dragon", parents=[common], help="个股龙虎榜 (上榜记录+席位+机构)")
    p.add_argument("code")
    p.add_argument("--date", required=True, help="YYYY-MM-DD")
    p.add_argument("--look-back", type=int, default=30, dest="look_back")

    p = sub.add_parser("market-dragon", parents=[common], help="全市场龙虎榜")
    p.add_argument("--date", default=None, help="YYYY-MM-DD, 默认今天")
    p.add_argument("--min-net-buy", type=float, default=None, dest="min_net_buy",
                   help="净买入下限(万元), 不填不过滤")

    p = sub.add_parser("lockup", parents=[common], help="限售解禁日历")
    p.add_argument("code")
    p.add_argument("--date", default=None, help="YYYY-MM-DD, 默认今天")
    p.add_argument("--forward-days", type=int, default=90, dest="forward_days")

    p = sub.add_parser("industry", parents=[common], help="全行业涨跌幅排名 (东财)")
    p.add_argument("--top-n", type=int, default=20, dest="top_n")

    args = parser.parse_args()

    if args.cmd == "hot":
        output(df_records(ths_hot_reason(args.date)), args.as_json)
    elif args.cmd == "northbound":
        df = hsgt_realtime()
        if args.save and not df.empty:
            sub_df = df.dropna()
            if not sub_df.empty:
                last = sub_df.iloc[-1]
                _save_northbound_snapshot(args.save, last["hgt_yi"], last["sgt_yi"])
                print(f"[OK] 已缓存 {args.save} 收盘北向: "
                      f"hgt={last['hgt_yi']} sgt={last['sgt_yi']} 亿元", file=sys.stderr)
        output(df_records(df), args.as_json)
    elif args.cmd == "blocks":
        output(eastmoney_concept_blocks(args.code), args.as_json)
    elif args.cmd == "fundflow":
        output(eastmoney_fund_flow_minute(args.code), args.as_json)
    elif args.cmd == "dragon":
        output(dragon_tiger_board(args.code, args.date, args.look_back), args.as_json)
    elif args.cmd == "market-dragon":
        output(daily_dragon_tiger(args.date, args.min_net_buy), args.as_json)
    elif args.cmd == "lockup":
        date = args.date or datetime.now().strftime("%Y-%m-%d")
        output(lockup_expiry(args.code, date, args.forward_days), args.as_json)
    elif args.cmd == "industry":
        output(industry_comparison(args.top_n), args.as_json)


if __name__ == "__main__":
    main()
