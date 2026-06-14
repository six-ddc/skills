# /// script
# requires-python = ">=3.10"
# dependencies = ["requests>=2.28", "pandas>=2.0", "mootdx>=0.10"]
# ///
"""Layer 6 基础数据层 — 财务快照 / F10 / 个股基本面 / 财报三表.

Sources:
  mootdx (通达信, TCP 7709)  → finance 37字段季报快照 / F10 9大类文本   — never bans IP
  东财 push2 stock/get        → 个股基本面 (行业/股本/市值/上市日/价格) — 部分大陆住宅 IP 风控
  新浪财报 openapi            → 资产负债表/利润表/现金流量表 三表

Commands:
  info <code>                              # 东财个股基本面 (走 em_get, 风控时优雅降级)
  finance <code>                           # mootdx 37字段财务快照
  f10 <code> [--section 公司概况]          # mootdx F10 9大类文本
  report <code> [--table lrb] [--num 8]    # 新浪三表 fzb/lrb/llb

Field tables / F10 9大类 / report_list 结构: references/fundamentals.md
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import requests

from _common import UA, build_cli, df_records, em_get, norm_ticker, output


def eastmoney_stock_info(code: str) -> dict:
    """东财个股基本面信息 (push2 stock/get, 走 em_get).

    返回: {code, name, industry, total_shares, float_shares, mcap, float_mcap,
           list_date, price}

    Defensive: 东财 push2 在部分大陆住宅 IP 上有风控，握手阶段直接断连
    (RemoteDisconnected / ConnectionError)，旧 §6.3 代码没有 try/except 会直接
    崩溃。这里用 try/except 包住请求 + .json()，失败时打印 [WARN] 到 stderr 并
    优雅降级返回 {}。
    """
    code = norm_ticker(code)
    market_code = 1 if code.startswith("6") else 0
    url = "https://push2.eastmoney.com/api/qt/stock/get"
    params = {
        "fltt": "2", "invt": "2",
        "fields": "f57,f58,f84,f85,f127,f116,f117,f189,f43",
        "secid": f"{market_code}.{code}",
    }
    headers = {"User-Agent": UA}
    try:
        r = em_get(url, params=params, headers=headers, timeout=10)
        d = r.json().get("data", {}) or {}
    except Exception as e:
        print(f"[WARN] 东财个股基本面请求失败 (部分大陆住宅 IP 被 push2 风控): {e}",
              file=sys.stderr)
        return {}
    return {
        "code": d.get("f57", ""),
        "name": d.get("f58", ""),
        "industry": d.get("f127", ""),
        "total_shares": d.get("f84", 0),     # 总股本(股)
        "float_shares": d.get("f85", 0),     # 流通股(股)
        "mcap": d.get("f116", 0),            # 总市值(元)
        "float_mcap": d.get("f117", 0),      # 流通市值(元)
        "list_date": str(d.get("f189", "")), # 上市日期 YYYYMMDD
        "price": d.get("f43", 0),
    }


def mootdx_finance(code: str) -> list[dict]:
    """mootdx 财务快照 (37字段季报). 返回 DataFrame → list[dict]."""
    from mootdx.quotes import Quotes               # lazy: only this path needs mootdx
    client = Quotes.factory(market="std")
    df = client.finance(symbol=norm_ticker(code))
    return df_records(df)


def mootdx_f10(code: str, section: str = "公司概况") -> str:
    """mootdx F10 公司文本资料.

    9 大类: 最新提示/公司概况/财务分析/股东研究/股本结构/资本运作/业内点评/
    行业分析/公司大事. 返回文本字符串.
    """
    from mootdx.quotes import Quotes               # lazy: only this path needs mootdx
    client = Quotes.factory(market="std")
    return client.F10(symbol=norm_ticker(code), name=section)


def sina_financial_report(code: str, report_type: str = "lrb", num: int = 8) -> list[dict]:
    """新浪财报三表 (普通 requests, 非东财).

    code: 6位代码
    report_type: "fzb"(资产负债表) / "lrb"(利润表) / "llb"(现金流量表)
    num: 取最近 N 期（默认 8 期）
    返回: 按报告期倒序的记录列表，每期一条 dict：
          {"报告期": "2026-03-31", "<科目>": "<值>", "<科目>_同比": <同比>, ...}
          （item_value 为新浪原始字符串数值，仅在有同比时附 "_同比" 键）
    """
    code = norm_ticker(code)
    prefix = "sh" if code.startswith("6") else "sz"
    paper_code = f"{prefix}{code}"
    url = "https://quotes.sina.cn/cn/api/openapi.php/CompanyFinanceService.getFinanceReport2022"
    params = {
        "paperCode": paper_code,
        "source": report_type,
        "type": "0",
        "page": "1",
        "num": str(num),
    }
    headers = {"User-Agent": UA}
    r = requests.get(url, params=params, headers=headers, timeout=15)
    # 新浪实际结构: result.data.report_list 是「按报告期(如 '20260331')为键」的 dict,
    # 每期对象的 data 字段才是行项列表 [{item_title, item_value, item_tongbi}]。
    report_list = r.json().get("result", {}).get("data", {}).get("report_list", {}) or {}

    rows = []
    for period in sorted(report_list.keys(), reverse=True)[:num]:
        obj = report_list[period]
        rec = {"报告期": f"{period[:4]}-{period[4:6]}-{period[6:8]}"}
        for it in obj.get("data", []) or []:
            title = it.get("item_title", "")
            if not title or it.get("item_value") is None:
                continue
            rec[title] = it.get("item_value")
            tongbi = it.get("item_tongbi")
            if tongbi not in (None, ""):
                rec[title + "_同比"] = tongbi
        rows.append(rec)
    return rows


def main():
    parser, sub, common = build_cli("L6 基础数据层 — mootdx finance/F10 / 东财基本面 / 新浪三表")

    p = sub.add_parser("info", parents=[common], help="东财个股基本面 (push2 stock/get)")
    p.add_argument("code")

    p = sub.add_parser("finance", parents=[common], help="mootdx 37字段财务快照")
    p.add_argument("code")

    p = sub.add_parser("f10", parents=[common], help="mootdx F10 9大类文本")
    p.add_argument("code")
    p.add_argument("--section", default="公司概况",
                   help="最新提示/公司概况/财务分析/股东研究/股本结构/资本运作/业内点评/行业分析/公司大事")

    p = sub.add_parser("report", parents=[common], help="新浪财报三表 fzb/lrb/llb")
    p.add_argument("code")
    p.add_argument("--table", default="lrb", choices=["fzb", "lrb", "llb"],
                   help="fzb=资产负债表 / lrb=利润表 / llb=现金流量表")
    p.add_argument("--num", type=int, default=8)

    args = parser.parse_args()

    if args.cmd == "info":
        output(eastmoney_stock_info(args.code), args.as_json)
    elif args.cmd == "finance":
        output(mootdx_finance(args.code), args.as_json)
    elif args.cmd == "f10":
        output(mootdx_f10(args.code, args.section), args.as_json)
    elif args.cmd == "report":
        output(sina_financial_report(args.code, args.table, args.num), args.as_json)


if __name__ == "__main__":
    main()
