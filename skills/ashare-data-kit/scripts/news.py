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

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from _common import build_cli, em_get, norm_ticker, output, UA


def eastmoney_stock_news(code: str, page_size: int = 20) -> list[dict]:
    """东财个股新闻（JSONP 接口）。
    返回: [{title, content, time, source, url}]
    """
    # 构造 JSONP 参数
    cb = "jQuery_news"
    url = "https://search-api-web.eastmoney.com/search/jsonp"
    inner_params = json.dumps({
        "uid": "",
        "keyword": norm_ticker(code),
        "type": ["cmsArticleWebOld"],
        "client": "web",
        "clientType": "web",
        "clientVersion": "curr",
        "param": {"cmsArticleWebOld": {"searchScope": "default", "sort": "default",
                  "pageIndex": 1, "pageSize": page_size, "preTag": "", "postTag": ""}},
    }, separators=(',', ':'))
    params = {"cb": cb, "param": inner_params}
    headers = {"User-Agent": UA, "Referer": "https://so.eastmoney.com/"}
    r = em_get(url, params=params, headers=headers, timeout=15)

    # 解析 JSONP
    text = r.text
    json_str = text[text.index("(") + 1 : text.rindex(")")]
    d = json.loads(json_str)

    rows = []
    # 东财实际返回里 result.cmsArticleWebOld 直接就是文章列表（非 {list:[...]} 嵌套）
    articles = d.get("result", {}).get("cmsArticleWebOld", []) or []
    for a in articles:
        rows.append({
            "title": re.sub(r'<[^>]+>', '', a.get("title", "")),
            "content": re.sub(r'<[^>]+>', '', a.get("content", ""))[:200],
            "time": a.get("date", ""),
            "source": a.get("mediaName", ""),
            "url": a.get("url", ""),
        })
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
