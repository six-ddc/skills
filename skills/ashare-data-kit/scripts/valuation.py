# /// script
# requires-python = ">=3.10"
# dependencies = ["requests>=2.28", "pandas>=2.0", "lxml"]
# ///
"""估值计算 + 单票综合调研流程.

Note on deps: this imports `quotes` and `reports` (siblings). The `full` path
only touches 腾讯行情 (requests) + 同花顺一致预期 (pandas + lxml via read_html);
mootdx is imported lazily inside quotes.py and is NOT on this path, so it is
intentionally absent from the PEP 723 block — `uv run valuation.py full` won't
pull the heavy mootdx dependency.

公式:
  forward_pe(price, eps)          前向PE = 股价 / 未来一致预期EPS
  calc_peg(pe, cagr)              PEG = 前向PE / (CAGR*100)
  pe_digestion(pe, cagr, target)  当前PE消化到 target(默认30x) 需要几年

命令:
  full <code>                     腾讯实时估值 + 同花顺一致预期 → PE_fwd/PEG/PE消化
  peg --pe X --cagr Y             纯计算 PEG (cagr 为小数, 0.3 = 30%)
  pe-digest --pe X --cagr Y [--target 30]

投资框架 (壁垒→增速→PE消化→PEG校验 / 30x 锚点 / 期权定价例外) 与完整调研流程
A–D 见 references/valuation.md。
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pandas as pd

from _common import build_cli, norm_ticker, output
from quotes import tencent_quote
from reports import ths_eps_forecast


def forward_pe(price: float, eps_forecast) -> float:
    """前向PE = 当前股价 / 未来年度一致预期EPS。eps<=0 视为无意义 → inf。"""
    if eps_forecast is None or eps_forecast <= 0:
        return float("inf")
    return price / eps_forecast


def calc_peg(pe: float, cagr: float) -> float:
    """PEG = 前向PE / (CAGR*100). <1 便宜 / 1–1.5 合理 / >1.5 贵。"""
    if cagr <= 0:
        return float("inf")
    return pe / (cagr * 100)


def pe_digestion(current_pe: float, cagr: float, target_pe: float = 30) -> float:
    """当前PE按 cagr 增长消化到 target_pe 需要多少年。target 默认 30x(A股成长股锚点)。"""
    if current_pe <= target_pe:
        return 0.0
    if cagr <= 0:
        return float("inf")
    return math.log(current_pe / target_pe) / math.log(1 + cagr)


def full_valuation(code: str) -> dict:
    """单票完整估值:腾讯实时(价/市值/PE/PB) + 同花顺一致预期EPS → 前向PE/CAGR/PEG/PE消化。"""
    code = norm_ticker(code)
    q = tencent_quote([code])
    if not q:
        return {"code": code, "error": "腾讯行情为空(可能停牌/代码错/网络)"}
    q = q[0]
    price, mcap, pe_ttm, pb = q["price"], q["mcap_yi"], q["pe_ttm"], q["pb"]

    # 同花顺一致预期表: 列约定 [年度, 预测机构数, 最小值, 均值, 最大值]; "均值"=一致预期EPS。
    # 第 0 行≈当年, 第 1 行≈次年。列结构偶有变化, 故宽松解析、失败留空。
    df = ths_eps_forecast(code)
    eps_cur = eps_next = None
    analyst_count = 0
    if df is not None and not df.empty and len(df.columns) >= 3:
        try:
            for i, row in df.reset_index(drop=True).iterrows():
                if i == 0:
                    eps_cur = float(row.iloc[2]) if pd.notna(row.iloc[2]) else None
                    analyst_count = int(row.iloc[1]) if pd.notna(row.iloc[1]) else 0
                elif i == 1:
                    eps_next = float(row.iloc[2]) if pd.notna(row.iloc[2]) else None
                else:
                    break
        except (ValueError, IndexError, TypeError):
            pass

    pe_fwd = forward_pe(price, eps_cur)
    cagr = (eps_next / eps_cur - 1) if (eps_cur and eps_next) else 0
    peg = calc_peg(pe_fwd, cagr)
    digest = pe_digestion(pe_fwd, cagr)

    def fin(x):           # inf → None for clean output
        return None if x == float("inf") else x

    return {
        "code": code, "name": q["name"], "price": price,
        "mcap_yi": mcap, "pe_ttm": pe_ttm, "pb": pb,
        "eps_cur": eps_cur, "eps_next": eps_next,
        "pe_fwd": round(pe_fwd, 1) if fin(pe_fwd) is not None else None,
        "cagr_pct": round(cagr * 100, 0) if cagr else None,
        "peg": round(peg, 2) if fin(peg) is not None else None,
        "digest_years": round(digest, 1) if fin(digest) is not None else None,
        "analyst_count": analyst_count,
    }


def main():
    parser, sub, common = build_cli("估值计算 + 单票综合调研 (腾讯 + 同花顺)")

    p = sub.add_parser("full", parents=[common], help="单票完整估值")
    p.add_argument("code")

    p = sub.add_parser("peg", parents=[common], help="纯计算 PEG")
    p.add_argument("--pe", type=float, required=True)
    p.add_argument("--cagr", type=float, required=True, help="小数, 0.3 = 30%")

    p = sub.add_parser("pe-digest", parents=[common], help="PE 消化到目标所需年数")
    p.add_argument("--pe", type=float, required=True)
    p.add_argument("--cagr", type=float, required=True, help="小数, 0.3 = 30%")
    p.add_argument("--target", type=float, default=30)

    args = parser.parse_args()
    if args.cmd == "full":
        output(full_valuation(args.code), args.as_json)
    elif args.cmd == "peg":
        output({"pe": args.pe, "cagr": args.cagr,
                "peg": round(calc_peg(args.pe, args.cagr), 3)}, args.as_json)
    elif args.cmd == "pe-digest":
        output({"pe": args.pe, "cagr": args.cagr, "target": args.target,
                "digest_years": round(pe_digestion(args.pe, args.cagr, args.target), 2)},
               args.as_json)


if __name__ == "__main__":
    main()
