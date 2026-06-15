# /// script
# requires-python = ">=3.10"
# dependencies = ["requests>=2.28", "pandas>=2.0"]
# ///
"""Layer 4 资金面 / 筹码层 (East money datacenter + push2his).

All endpoints go through the throttled em_get / eastmoney_datacenter helpers in
_common (never build a private session — that defeats the global anti-ban
throttle). Codes are normalized with norm_ticker before use.

Commands:
  margin <code> [--page-size 30]        # 融资融券明细 RPTA_WEB_RZRQ_GGMX
  block <code> [--page-size 20]         # 大宗交易 RPT_DATA_BLOCKTRADE (含溢价计算)
  holders <code> [--page-size 10]       # 股东户数变化 RPT_HOLDERNUMLATEST
  dividend <code> [--page-size 20]      # 分红送转 RPT_SHAREBONUS_DET
  fundflow120 <code>                    # 个股资金流 120日 (push2his daykline, 单位:元)

Field tables / gotchas (融资融券字段含义、溢价率算法、住宅 IP 间歇封锁):
references/capital.md
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import requests

from _common import (UA, build_cli, eastmoney_datacenter, em_get, em_push2_get,
                     norm_ticker, output, response_json)


def margin_trading(code: str, page_size: int = 30) -> list[dict]:
    """
    融资融券明细（日级）。
    返回: [{date, rzye(融资余额), rzmre(融资买入), rqye(融券余额), ...}]
    """
    code = norm_ticker(code)
    data = eastmoney_datacenter(
        "RPTA_WEB_RZRQ_GGMX",
        filter_str=f'(SCODE="{code}")',
        page_size=page_size,
        sort_columns="DATE", sort_types="-1",
    )
    rows = []
    for row in data:
        rows.append({
            "date": str(row.get("DATE", ""))[:10],
            "rzye": row.get("RZYE", 0),       # 融资余额(元)
            "rzmre": row.get("RZMRE", 0),      # 融资买入额
            "rzche": row.get("RZCHE", 0),      # 融资偿还额
            "rqye": row.get("RQYE", 0),        # 融券余额(元)
            "rqmcl": row.get("RQMCL", 0),      # 融券卖出量
            "rqchl": row.get("RQCHL", 0),      # 融券偿还量
            "rzrqye": row.get("RZRQYE", 0),    # 融资融券余额合计
        })
    return rows


def block_trade(code: str, page_size: int = 20) -> list[dict]:
    """
    大宗交易记录。
    返回: [{date, price, vol, amount, buyer, seller, premium_pct}]
    """
    code = norm_ticker(code)
    data = eastmoney_datacenter(
        "RPT_DATA_BLOCKTRADE",
        filter_str=f'(SECURITY_CODE="{code}")',
        page_size=page_size,
        sort_columns="TRADE_DATE", sort_types="-1",
    )
    rows = []
    for row in data:
        close = row.get("CLOSE_PRICE") or 0
        deal_price = row.get("DEAL_PRICE") or 0
        premium = ((deal_price / close - 1) * 100) if close else 0
        rows.append({
            "date": str(row.get("TRADE_DATE", ""))[:10],
            "price": deal_price,
            "close": close,
            "premium_pct": round(premium, 2),
            "vol": row.get("DEAL_VOLUME", 0),
            "amount": row.get("DEAL_AMT", 0),
            "buyer": row.get("BUYER_NAME", ""),
            "seller": row.get("SELLER_NAME", ""),
        })
    return rows


def holder_num_change(code: str, page_size: int = 10) -> list[dict]:
    """
    股东户数变化（季度级）。
    返回: [{date, holder_num, change_num, change_ratio, avg_shares}]
    """
    code = norm_ticker(code)
    data = eastmoney_datacenter(
        "RPT_HOLDERNUMLATEST",
        filter_str=f'(SECURITY_CODE="{code}")',
        page_size=page_size,
        sort_columns="END_DATE", sort_types="-1",
    )
    rows = []
    for row in data:
        rows.append({
            "date": str(row.get("END_DATE", ""))[:10],
            "holder_num": row.get("HOLDER_NUM", 0),
            "change_num": row.get("HOLDER_NUM_CHANGE", 0),
            "change_ratio": row.get("HOLDER_NUM_RATIO", 0),  # 环比%
            "avg_shares": row.get("AVG_FREE_SHARES", 0),     # 户均持股
        })
    return rows


def dividend_history(code: str, page_size: int = 20) -> list[dict]:
    """
    分红送转历史。
    返回: [{date, bonus_rmb(每股派息), transfer_ratio(转增比例), bonus_ratio(送股比例)}]
    """
    code = norm_ticker(code)
    data = eastmoney_datacenter(
        "RPT_SHAREBONUS_DET",
        filter_str=f'(SECURITY_CODE="{code}")',
        page_size=page_size,
        sort_columns="EX_DIVIDEND_DATE", sort_types="-1",
    )
    rows = []
    for row in data:
        rows.append({
            "date": str(row.get("EX_DIVIDEND_DATE", ""))[:10],
            "bonus_rmb": row.get("PRETAX_BONUS_RMB", 0),    # 每股派息(税前)
            "transfer_ratio": row.get("TRANSFER_RATIO", 0),  # 每10股转增
            "bonus_ratio": row.get("BONUS_RATIO", 0),        # 每10股送股
            "plan": row.get("ASSIGN_PROGRESS", ""),           # 进度
        })
    return rows


def stock_fund_flow_120d(code: str) -> list[dict]:
    """
    个股资金流（日级，最近120个交易日）。
    返回: [{date, main_net(主力净流入), small_net, mid_net, large_net, super_net}]
    单位: 元
    """
    code = norm_ticker(code)
    market_code = 1 if code.startswith("6") else 0
    url = "https://push2his.eastmoney.com/api/qt/stock/fflow/daykline/get"
    params = {
        "secid": f"{market_code}.{code}",
        "klt": "101",
        "fields1": "f1,f2,f3,f7",
        "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61,f62,f63,f64,f65",
        "lmt": "120",
    }
    headers = {
        "Referer": f"https://quote.eastmoney.com/{'sh' if code.startswith('6') else 'sz'}{code}.html",
        "Origin": "https://quote.eastmoney.com",
    }
    try:
        r = em_push2_get(url, params=params, headers=headers, timeout=15, jsonp=True)
        d = response_json(r)
    except Exception as e:
        print(f"[WARN] push2 资金流请求失败: {e}", file=sys.stderr)
        return sina_fund_flow_daily(code)
    klines = d.get("data", {}).get("klines", [])

    rows = []
    for line in klines:
        parts = line.split(",")
        if len(parts) >= 7:
            rows.append({
                "date": parts[0],
                "main_net": float(parts[1]) if parts[1] != "-" else 0,
                "small_net": float(parts[2]) if parts[2] != "-" else 0,
                "mid_net": float(parts[3]) if parts[3] != "-" else 0,
                "large_net": float(parts[4]) if parts[4] != "-" else 0,
                "super_net": float(parts[5]) if parts[5] != "-" else 0,
            })
    return rows or sina_fund_flow_daily(code)


def sina_fund_flow_daily(code: str, num: int = 120) -> list[dict]:
    """新浪 MoneyFlow 日级兜底；口径不同于东财小/中/大/超大单拆分。"""
    code = norm_ticker(code)
    symbol = ("sh" if code.startswith("6") else "sz") + code
    url = "https://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php/MoneyFlow.ssl_qsfx_zjlrqs"
    params = {"daima": symbol, "page": "1", "num": str(num)}
    try:
        r = requests.get(url, params=params,
                         headers={"User-Agent": UA, "Referer": "https://finance.sina.com.cn/"},
                         timeout=15)
        r.encoding = "gbk"
        data = r.json()
    except Exception as e:
        print(f"[WARN] 新浪资金流日级兜底失败: {e}", file=sys.stderr)
        return []

    rows = []
    for row in data[:num]:
        def f(key):
            try:
                return float(row.get(key) or 0)
            except (TypeError, ValueError):
                return 0.0
        rows.append({
            "date": row.get("opendate", ""),
            "main_net": f("netamount"),
            "small_net": None,
            "mid_net": None,
            "large_net": f("r0_net"),
            "super_net": None,
            "source": "sina_moneyflow",
            "close": f("trade"),
            "change_pct": round(f("changeratio") * 100, 4),
            "turnover": f("turnover"),
            "net_ratio": f("ratioamount"),
            "r0_ratio": f("r0_ratio"),
        })
    return rows


def main():
    parser, sub, common = build_cli("L4 资金面/筹码层 — 东财 datacenter / push2his")

    p = sub.add_parser("margin", parents=[common], help="融资融券明细")
    p.add_argument("code")
    p.add_argument("--page-size", type=int, default=30, dest="page_size")

    p = sub.add_parser("block", parents=[common], help="大宗交易(含溢价)")
    p.add_argument("code")
    p.add_argument("--page-size", type=int, default=20, dest="page_size")

    p = sub.add_parser("holders", parents=[common], help="股东户数变化")
    p.add_argument("code")
    p.add_argument("--page-size", type=int, default=10, dest="page_size")

    p = sub.add_parser("dividend", parents=[common], help="分红送转历史")
    p.add_argument("code")
    p.add_argument("--page-size", type=int, default=20, dest="page_size")

    p = sub.add_parser("fundflow120", parents=[common], help="个股资金流(120日,单位元)")
    p.add_argument("code")

    args = parser.parse_args()

    if args.cmd == "margin":
        output(margin_trading(args.code, args.page_size), args.as_json)
    elif args.cmd == "block":
        output(block_trade(args.code, args.page_size), args.as_json)
    elif args.cmd == "holders":
        output(holder_num_change(args.code, args.page_size), args.as_json)
    elif args.cmd == "dividend":
        output(dividend_history(args.code, args.page_size), args.as_json)
    elif args.cmd == "fundflow120":
        output(stock_fund_flow_120d(args.code), args.as_json)


if __name__ == "__main__":
    main()
