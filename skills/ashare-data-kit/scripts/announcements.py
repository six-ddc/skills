# /// script
# requires-python = ">=3.10"
# dependencies = ["requests>=2.28"]
# ///
"""Layer 7 公告层 (巨潮 cninfo.com.cn, 直连 — NOT eastmoney).

Source, in priority order:
  巨潮 cninfo.com.cn (HTTP)  → 公告全文检索 (title / type / date / url)

巨潮 is NOT an eastmoney domain, so this script uses plain requests.post/get
(NOT em_get / the throttled EM_SESSION). The only shared helpers it needs are
norm_ticker / UA / output / build_cli.

Commands:
  list <code> [--page-size 30]          # 巨潮公告全文检索

NOTE: 最新公告摘要 (公告/分红/股东大会决议等) is the mootdx F10「最新提示」section,
which lives in Layer 6 — use `fundamentals.py f10 <code> --section 最新提示`.
This script intentionally does NOT duplicate it.

orgId 坑 / 字段表 / 动态映射表方案: references/announcements.md
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import requests
from datetime import datetime

from _common import UA, build_cli, norm_ticker, output


def _cninfo_ts_to_date(ts):
    """巨潮 announcementTime 返回 Unix 毫秒整数，需转换为日期字符串。"""
    if isinstance(ts, (int, float)):
        return datetime.fromtimestamp(ts / 1000).strftime("%Y-%m-%d")
    return str(ts)[:10] if ts else ""


# 巨潮 股票→orgId 映射（模块级缓存，首次调用时拉取一次，全程复用）
_CNINFO_ORGID_MAP = {}


def _cninfo_orgid(code: str) -> str:
    """查股票真实 orgId。巨潮 orgId 并非统一 `gssx0{code}` 格式（如 601318→9900002221、
    601398→jjxt0000019、688017→9900041602），硬编码会导致大量股票（尤其 601xxx 段）
    返回 totalAnnouncement=0、查不到公告。优先动态查官方映射表，查不到再回退硬编码。"""
    global _CNINFO_ORGID_MAP
    if not _CNINFO_ORGID_MAP:
        try:
            r = requests.get("http://www.cninfo.com.cn/new/data/szse_stock.json",
                             headers={"User-Agent": UA}, timeout=15)
            _CNINFO_ORGID_MAP = {s["code"]: s["orgId"]
                                 for s in r.json().get("stockList", [])}
        except Exception as e:
            print(f"[WARN] 巨潮 orgId 映射表拉取失败，回退硬编码规则: {e}")
    org = _CNINFO_ORGID_MAP.get(code)
    if org:
        return org
    # fallback：老格式（仅部分老股票如 600519/600036 适用）
    if code.startswith("6"):
        return f"gssh0{code}"
    elif code.startswith("8") or code.startswith("4"):
        return f"gsbj0{code}"
    return f"gssz0{code}"


def cninfo_announcements(code: str, page_size: int = 30) -> list[dict]:
    """
    巨潮公告全文检索。
    返回: [{title, type, date, url}]
    """
    code = norm_ticker(code)
    url = "https://www.cninfo.com.cn/new/hisAnnouncement/query"
    org_id = _cninfo_orgid(code)   # 动态查真实 orgId(自带硬编码 fallback)

    payload = {
        "stock": f"{code},{org_id}",
        "tabName": "fulltext",
        "pageSize": str(page_size),
        "pageNum": "1",
        "column": "",
        "category": "",
        "plate": "",
        "seDate": "",
        "searchkey": "",
        "secid": "",
        "sortName": "",
        "sortType": "",
        "isHLtitle": "true",
    }
    headers = {
        "User-Agent": UA,
        "Content-Type": "application/x-www-form-urlencoded",
        "Referer": "https://www.cninfo.com.cn/new/disclosure",
        "Origin": "https://www.cninfo.com.cn",
    }
    r = requests.post(url, data=payload, headers=headers, timeout=15)
    d = r.json()

    rows = []
    for item in d.get("announcements", []) or []:
        rows.append({
            "title": item.get("announcementTitle", ""),
            "type": item.get("announcementTypeName", ""),
            "date": _cninfo_ts_to_date(item.get("announcementTime")),
            "url": f"https://www.cninfo.com.cn/new/disclosure/detail?annoId={item.get('announcementId', '')}",
        })
    return rows


def main():
    parser, sub, common = build_cli("L7 公告层 — 巨潮 cninfo.com.cn")

    p = sub.add_parser("list", parents=[common], help="巨潮公告全文检索")
    p.add_argument("code")
    p.add_argument("--page-size", type=int, default=30, dest="page_size")

    args = parser.parse_args()

    if args.cmd == "list":
        output(cninfo_announcements(args.code, args.page_size), args.as_json)


if __name__ == "__main__":
    main()
