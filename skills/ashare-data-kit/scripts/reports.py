# /// script
# requires-python = ">=3.10"
# dependencies = ["requests>=2.28", "pandas>=2.0", "lxml"]
# ///
"""Layer 2 研报层 (research reports).

Sources, in priority order:
  东财 reportapi (reportapi.eastmoney.com) → 研报列表 + PDF下载    — A级公开JSON, 免费无key
  同花顺 basic.10jqka.com.cn               → 机构一致预期EPS       — 直连HTML表格
  iwencai (openapi.iwencai.com)            → NL语义搜索研报(唯一能力) — 需 API Key + X-Claw

All eastmoney.com requests go through em_get() (shared throttle, anti-ban).
同花顺 / iwencai are NOT eastmoney → plain requests.

Commands:
  list <code> [--max-pages N]              # 东财研报列表
  pdf <info_code> [--out PATH]             # 下载单份研报 PDF (需 Referer)
  eps <code>                               # 同花顺机构一致预期 EPS
  iwencai <query> [--channel report] [--size 50]   # NL 语义搜索研报

Field tables / API Key 申请 / X-Claw / 踩坑: references/reports.md
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import requests

from _common import build_cli, df_records, em_get, norm_ticker, output


# ── East money 研报 (A级公开JSON API, 免费无key) ──────────────────────────
REPORT_API = "https://reportapi.eastmoney.com/report/list"
PDF_TPL = "https://pdf.dfcfw.com/pdf/H3_{info_code}_1.pdf"


def eastmoney_reports(code: str, max_pages: int = 5) -> list[dict]:
    """拉取指定股票的研报列表"""
    code = norm_ticker(code)
    all_records = []
    for page in range(1, max_pages + 1):
        params = {
            "industryCode": "*", "pageSize": "100", "industry": "*",
            "rating": "*", "ratingChange": "*",
            "beginTime": "2000-01-01", "endTime": "2030-01-01",
            "pageNo": str(page), "fields": "", "qType": "0",
            "orgCode": "", "code": code, "rcode": "",
            "p": str(page), "pageNum": str(page), "pageNumber": str(page),
        }
        r = em_get(REPORT_API, params=params,
                   headers={"Referer": "https://data.eastmoney.com/"}, timeout=30)  # 已内置限流
        d = r.json()
        rows = d.get("data") or []
        if not rows:
            break
        all_records.extend(rows)
        if page >= (d.get("TotalPage", 1) or 1):
            break
    return all_records


def _dfcfw_bot_cookies(html: str) -> dict:
    """Parse the lightweight pdf.dfcfw.com cookie challenge."""
    nums = dict((name, int(value))
                for name, value in re.findall(r"(WTKkN|bOYDu|wyeCN):(\d+)", html))
    ssid = re.search(r't,(\d+)\)', html)
    if not ssid or not all(k in nums for k in ("WTKkN", "bOYDu", "wyeCN")):
        return {}
    return {
        "__tst_status": f"{nums['WTKkN'] + nums['bOYDu'] + nums['wyeCN']}#",
        "EO_Bot_Ssid": ssid.group(1),
    }


def download_pdf(info_code: str, out_path: str | None = None) -> dict:
    """下载单份研报 PDF (按 infoCode), 返回保存路径与字节数。

    PDF 走 pdf.dfcfw.com, 必须带 Referer: https://data.eastmoney.com/。
    若返回轻量 JS cookie 挑战, 解析 cookie 后经 em_get 重试一次。
    """
    from pathlib import Path

    target = Path(out_path) if out_path else Path(f"./{info_code}.pdf")
    url = PDF_TPL.format(info_code=info_code)
    headers = {"Referer": "https://data.eastmoney.com/"}
    r = em_get(url, headers=headers, timeout=60)
    challenge_solved = False
    if r.status_code == 200 and r.content.lstrip().startswith(b"<script>"):
        cookies = _dfcfw_bot_cookies(r.text)
        if cookies:
            r = em_get(url, headers=headers, cookies=cookies, timeout=60)
            challenge_solved = True

    is_pdf = r.content.lstrip().startswith(b"%PDF")
    if r.status_code == 200 and is_pdf and len(r.content) >= 1024:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(r.content)
        return {"path": str(target), "bytes": len(r.content),
                "status": r.status_code, "challenge_solved": challenge_solved}
    return {"path": None, "bytes": len(r.content),
            "status": r.status_code,
            "warning": "下载失败(非200、非PDF或内容过小)",
            "challenge_solved": challenge_solved}


# ── 同花顺机构一致预期EPS (直连 basic.10jqka.com.cn, 非东财) ───────────────
def ths_eps_forecast(code: str):
    """
    同花顺机构一致预期EPS。
    直连 basic.10jqka.com.cn，解析HTML表格。
    返回 DataFrame: 年度, 预测机构数, 最小值, 均值, 最大值
    "均值" = 机构一致预期EPS
    """
    import pandas as pd
    from io import StringIO

    code = norm_ticker(code)
    url = f"https://basic.10jqka.com.cn/new/{code}/worth.html"
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        "Referer": "https://basic.10jqka.com.cn/",
    }
    r = requests.get(url, headers=headers, timeout=15)
    r.encoding = "gbk"
    try:
        dfs = pd.read_html(StringIO(r.text))
    except Exception as e:
        print(f"[WARN] 同花顺一致预期表格解析失败/为空: {e}", file=sys.stderr)
        return pd.DataFrame()
    # 找含"每股收益"的表格
    for df in dfs:
        cols = [str(c) for c in df.columns]
        if any("每股收益" in c or "均值" in c for c in cols):
            return df
    # fallback: 返回第一个表
    return dfs[0] if dfs else pd.DataFrame()


# ── iwencai NL 语义搜索 (openapi.iwencai.com, 需 API Key + X-Claw) ─────────
IWENCAI_BASE = os.environ.get("IWENCAI_BASE_URL", "https://openapi.iwencai.com")
IWENCAI_KEY = os.environ.get("IWENCAI_API_KEY", "")


def _claw_headers(call_type: str = "normal") -> dict:
    """SkillHub 2.0 必须的 X-Claw 鉴权头"""
    import secrets

    return {
        "X-Claw-Call-Type": call_type,
        "X-Claw-Skill-Id": "report-search",
        "X-Claw-Skill-Version": "2.0.0",
        "X-Claw-Plugin-Id": "none",
        "X-Claw-Plugin-Version": "none",
        "X-Claw-Trace-Id": secrets.token_hex(32),
    }


def iwencai_search(query: str, channel: str = "report", size: int = 50) -> list[dict]:
    """
    iwencai 语义搜索。
    channel: "report"(研报) / "announcement"(公告) / "news"(新闻)
    size: 默认10, 实测可调到50（隐藏参数）
    """
    headers = {
        "Authorization": f"Bearer {IWENCAI_KEY}",
        "Content-Type": "application/json",
        **_claw_headers(),
    }
    payload = {
        "channels": [channel],
        "app_id": "AIME_SKILL",
        "query": query,
        "size": size,
    }
    r = requests.post(
        f"{IWENCAI_BASE}/v1/comprehensive/search",
        json=payload, headers=headers, timeout=30,
    )
    if r.status_code != 200:
        raise RuntimeError(f"iwencai HTTP {r.status_code}: {r.text[:200]}")
    data = r.json()
    if data.get("status_code", 0) != 0:
        raise RuntimeError(f"iwencai error: {data.get('status_msg', '')}")
    return data.get("data") or []


def dedup_articles(articles: list[dict]) -> list[dict]:
    """同一uid仅保留score最高的段落"""
    best = {}
    for a in articles:
        uid = a.get("uid", "") or f"{a.get('title','')}|{a.get('publish_date','')}"
        score = float(a.get("score", 0))
        if uid not in best or score > float(best[uid].get("score", 0)):
            best[uid] = a
    return sorted(best.values(), key=lambda x: x.get("publish_date", ""), reverse=True)


def main():
    parser, sub, common = build_cli("L2 研报层 — 东财 reportapi / 同花顺 / iwencai")

    p = sub.add_parser("list", parents=[common], help="东财研报列表")
    p.add_argument("code")
    p.add_argument("--max-pages", type=int, default=5)

    p = sub.add_parser("pdf", parents=[common], help="下载单份研报 PDF (按 infoCode)")
    p.add_argument("info_code")
    p.add_argument("--out", default=None, help="保存路径, 默认 ./{info_code}.pdf")

    p = sub.add_parser("eps", parents=[common], help="同花顺机构一致预期 EPS")
    p.add_argument("code")

    p = sub.add_parser("iwencai", parents=[common], help="iwencai NL 语义搜索研报")
    p.add_argument("query")
    p.add_argument("--channel", default="report",
                   help="report(研报) / announcement(公告) / news(新闻)")
    p.add_argument("--size", type=int, default=50)

    args = parser.parse_args()

    if args.cmd == "list":
        output(eastmoney_reports(args.code, args.max_pages), args.as_json)
    elif args.cmd == "pdf":
        output(download_pdf(args.info_code, args.out), args.as_json)
    elif args.cmd == "eps":
        output(df_records(ths_eps_forecast(args.code)), args.as_json)
    elif args.cmd == "iwencai":
        if not IWENCAI_KEY:
            print("[ERROR] 未设置 IWENCAI_API_KEY 环境变量。\n"
                  "iwencai 走 SkillHub 2.0, 需要申请 API Key。\n"
                  "请到 https://www.iwencai.com/skillhub 申请, 然后:\n"
                  "  export IWENCAI_API_KEY=your_key\n"
                  "  (可选) export IWENCAI_BASE_URL=https://openapi.iwencai.com",
                  file=sys.stderr)
            sys.exit(2)
        articles = iwencai_search(args.query, args.channel, args.size)
        articles = dedup_articles(articles)
        output(articles, args.as_json)


if __name__ == "__main__":
    main()
