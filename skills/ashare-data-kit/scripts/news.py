# /// script
# requires-python = ">=3.10"
# dependencies = ["requests>=2.28"]
# ///
"""Layer 5 新闻层 (East money news feeds).

This layer needs no pandas — output() lazily tries pandas for list[dict] and
falls back to line-by-line printing when it's absent, which is fine here.

Sources:
  东财 search-api-web (JSONP)  → 个股新闻
  东财 np-weblist             → 全球资讯 7×24 滚动

Commands:
  stock <code> [--page-size 20]   # 东财个股新闻 (JSONP)
  global [--page-size 50]         # 东财全球资讯 (7×24)

NOTE: 财联社 cls_telegraph 已下线 (cls.cn 迁 Next.js, 旧 API 404), 不再提供子命令；
全市场实时快讯请改用 `global`。详见 references/news.md。

Field tables / gotchas (个股新闻间歇返回空等): references/news.md
"""
import json
import os
import re
import sys
import uuid
from html import unescape

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import requests

from _common import build_cli, em_get, market_symbol, norm_ticker, output, UA, response_json


def eastmoney_stock_news(code: str, page_size: int = 20) -> list[dict]:
    """东财个股新闻（JSONP 接口）。
    返回: [{title, content, time, source, url}]
    """
    keywords = [norm_ticker(code)]
    try:
        from quotes import tencent_quote
        q = tencent_quote([code])
        if q and q[0].get("name"):
            keywords.extend([q[0]["name"], f"{norm_ticker(code)} {q[0]['name']}"])
    except Exception:
        pass
    if str(code).strip() not in keywords:
        keywords.append(str(code).strip())

    rows = []
    seen = set()
    for keyword in dict.fromkeys(k for k in keywords if k):
        for type_name in ("cmsArticleWebOld", "cmsArticleWeb"):
            for item in _search_stock_news(keyword, type_name, page_size):
                key = item.get("url") or f"{item.get('title')}|{item.get('time')}"
                if key in seen:
                    continue
                seen.add(key)
                rows.append(item)
                if len(rows) >= page_size:
                    return rows
    return rows or sina_stock_news(code, page_size)


def _search_stock_news(keyword: str, type_name: str, page_size: int) -> list[dict]:
    cb = "jQuery_news"
    url = "https://search-api-web.eastmoney.com/search/jsonp"
    inner_params = json.dumps({
        "uid": "",
        "keyword": keyword,
        "type": [type_name],
        "client": "web",
        "clientType": "web",
        "clientVersion": "curr",
        "param": {type_name: {"searchScope": "default", "sort": "default",
                  "pageIndex": 1, "pageSize": page_size, "preTag": "", "postTag": ""}},
    }, separators=(',', ':'))
    params = {"cb": cb, "param": inner_params}
    headers = {"User-Agent": UA, "Referer": "https://so.eastmoney.com/"}
    try:
        r = em_get(url, params=params, headers=headers, timeout=15)
        d = response_json(r)
    except Exception as e:
        print(f"[WARN] 东财个股新闻搜索失败 keyword={keyword} type={type_name}: {e}", file=sys.stderr)
        return []
    rows = []
    result = d.get("result", {}) or {}
    articles = result.get(type_name, []) or []
    if isinstance(articles, dict):
        articles = articles.get("list") or articles.get("data") or []
    for a in articles:
        rows.append({
            "title": re.sub(r'<[^>]+>', '', a.get("title", "")),
            "content": re.sub(r'<[^>]+>', '', a.get("content", ""))[:200],
            "time": a.get("date", ""),
            "source": a.get("mediaName", ""),
            "url": a.get("url", ""),
        })
    return rows


def sina_stock_news(code: str, page_size: int = 20) -> list[dict]:
    """新浪个股资讯页兜底。"""
    symbol = market_symbol(code)
    url = f"https://vip.stock.finance.sina.com.cn/corp/go.php/vCB_AllNewsStock/symbol/{symbol}.phtml"
    try:
        r = requests.get(url, headers={"User-Agent": UA, "Referer": "https://finance.sina.com.cn/"},
                         timeout=15)
        r.encoding = "gb2312"
    except Exception as e:
        print(f"[WARN] 新浪个股新闻兜底失败: {e}", file=sys.stderr)
        return []

    rows = []
    seen = set()
    for href, title in re.findall(r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', r.text, flags=re.S):
        title = re.sub(r"<[^>]+>", "", title)
        title = unescape(title).strip()
        href = unescape(href).strip()
        if not title or len(title) < 6:
            continue
        if "realstock/company" in href or "javascript:" in href:
            continue
        if not href.startswith("http"):
            continue
        if href in seen:
            continue
        seen.add(href)
        m = re.search(r"/(\d{4}-\d{2}-\d{2})/", href)
        rows.append({
            "title": title,
            "content": "",
            "time": m.group(1) if m else "",
            "source": "新浪财经",
            "url": href,
        })
        if len(rows) >= page_size:
            break
    return rows


def eastmoney_global_news(page_size: int = 50) -> list[dict]:
    """东方财富全球财经资讯（7x24 滚动）。
    返回: [{title, summary, time}]
    """
    url = "https://np-weblist.eastmoney.com/comm/web/getFastNewsList"
    params = {
        "client": "web", "biz": "web_724",
        "fastColumn": "102", "sortEnd": "",
        "pageSize": str(page_size),
        "req_trace": str(uuid.uuid4()),
    }
    headers = {"User-Agent": UA, "Referer": "https://kuaixun.eastmoney.com/"}
    r = em_get(url, params=params, headers=headers, timeout=10)
    d = r.json()

    rows = []
    for item in d.get("data", {}).get("fastNewsList", []):
        rows.append({
            "title": item.get("title", ""),
            "summary": item.get("summary", "")[:200],
            "time": item.get("showTime", ""),
        })
    return rows


def main():
    parser, sub, common = build_cli("L5 新闻层 — 东财个股新闻 / 全球资讯")

    p = sub.add_parser("stock", parents=[common], help="东财个股新闻 (JSONP)")
    p.add_argument("code")
    p.add_argument("--page-size", type=int, default=20)

    p = sub.add_parser("global", parents=[common], help="东财全球资讯 (7×24 滚动)")
    p.add_argument("--page-size", type=int, default=50)

    args = parser.parse_args()

    if args.cmd == "stock":
        output(eastmoney_stock_news(args.code, args.page_size), args.as_json)
    elif args.cmd == "global":
        output(eastmoney_global_news(args.page_size), args.as_json)


if __name__ == "__main__":
    main()
