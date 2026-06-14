---
name: ashare-data-kit
description: A股全栈数据工具包 — 七层数据源(行情/研报/信号/资金面/新闻/基础数据/公告),代码以 uv 可执行脚本(scripts/)+ PEP723 自动装依赖提供,渐进式披露按需读 references/。优先用通达信(mootdx)/腾讯/新浪(不封IP),东财接口已内置限流防封。覆盖个股估值、研报检索、题材归因、龙虎榜跟踪、解禁预警、行业轮动、融资融券、筹码分析、产业链调研、批量筛选。当用户要查 A 股个股估值/一致预期/PE/PEG/市值、实时行情/K线/盘口/涨跌停价、研报(按主题/标的/行业/下PDF)、当日强势股/题材/概念热点、北向资金(沪股通/深股通)、概念板块归属、个股资金流向(主力/超大单)、龙虎榜/营业部席位、全市场龙虎榜、限售解禁日历、行业横向对比/轮动、融资融券/两融、大宗交易、股东户数/筹码集中、分红送转、指数/ETF行情、个股新闻/全球资讯、巨潮公告全文,或做产业链调研/批量筛选时,使用本 skill。关键词:估值、一致预期、机构预测、市盈率、PEG、市值、研报、产业链、行业研究、K线、盘口、公告、新闻、强势股、题材、热点、概念归因、北向资金、沪股通、深股通、概念板块、资金流向、主力、龙虎榜、席位、营业部、净买入、解禁、限售、行业对比、行业轮动、融资融券、两融、大宗交易、股东户数、筹码集中、分红、派息、送股、指数、ETF。
---

# A股全栈数据工具包

七层数据架构,覆盖主板/中小板/科创板/北交所/ST。**所有能力都是 `scripts/` 下的可执行脚本**——用 `uv run` 调用,首次自动装依赖,无需手动 pip;详细字段表/踩坑/语义按需读 `references/`。

## 运行方式(重要)

```bash
uv run scripts/<layer>.py <command> [args] [--json]
```

- 首次运行某脚本时,`uv` 按其 PEP 723 声明**自动建临时环境装依赖**(requests/pandas/mootdx/lxml 各取所需),之后走缓存。没装 uv 见 `references/data-sources.md`。
- 默认输出**人类可读表格/摘要**;加 `--json` 输出原始 JSON(便于二次处理/管道)。
- 仅 iwencai 语义搜索需 `export IWENCAI_API_KEY=...`,其余数据源免费无 key。
- 代码入参的股票代码支持 `688017 / SH688017 / 688017.SH / 000001` 等格式,内部归一为 6 位。

## 数据源优先级 & 防封(先读)

**能用通达信(mootdx)/腾讯/新浪就别用东财** —— 前者不封 IP,可高频;东财有风控会封 IP,仅用于其独有数据(龙虎榜/解禁/融资融券/大宗/股东户数/分红/资金流/行业排名/研报/新闻/板块归属)。所有东财请求已统一走内置限流入口 `em_get()`(串行 + 间隔 ≥1s + 抖动 + 会话复用),抄了就自带防封。**调东财前务必读 [`references/data-sources.md`](references/data-sources.md)**(优先级表、风控阈值、铁律、大陆住宅 IP 间歇风控说明)。

## 七层数据地图

```
行情层  quotes.py        mootdx K线/盘口/逐笔 · 腾讯价/PE/PB/市值/涨跌停 · 新浪盘口(兜底) · 百度K线带MA   [不封IP]
研报层  reports.py       东财研报列表+PDF+EPS预测 · 同花顺一致预期 · iwencai NL语义搜索
信号层  signals.py       同花顺热点题材归因 · 北向资金 · 板块归属 · 资金流分钟级 · 龙虎榜(个股+全市场) · 解禁 · 行业排名
资金面  capital.py       融资融券 · 大宗交易 · 股东户数 · 分红送转 · 个股资金流120日
新闻层  news.py          东财个股新闻 · 全球资讯7×24 (财联社已下线)
基础层  fundamentals.py  东财个股信息 · mootdx财务快照/F10 · 新浪财报三表
公告层  announcements.py 巨潮公告全文检索(动态 orgId)
估值    valuation.py     前向PE/PEG/PE消化公式 + 单票综合调研流程
```

## 命令速查表

| 需求 | 命令 |
|------|------|
| 实时价/PE/PB/市值/涨跌停 | `uv run scripts/quotes.py realtime 600519` |
| 实时价+五档盘口(腾讯兜底) | `uv run scripts/quotes.py sina 600519` |
| K线 | `uv run scripts/quotes.py kline 600519 --period day --count 60` |
| K线带均线 | `uv run scripts/quotes.py kline-ma 600519` |
| 逐笔成交 | `uv run scripts/quotes.py transaction 600519 --date 20260612` |
| 指数/ETF | `uv run scripts/quotes.py realtime sh000001 sh000300 sh510050` |
| 研报列表+EPS预测 | `uv run scripts/reports.py list 600519` |
| 研报PDF下载 | `uv run scripts/reports.py pdf <infoCode>` |
| 机构一致预期EPS | `uv run scripts/reports.py eps 600519` |
| NL语义搜研报 | `uv run scripts/reports.py iwencai "人形机器人 丝杠 2026"` |
| 当日强势股+题材归因 | `uv run scripts/signals.py hot --date 2026-06-12` |
| 北向资金分钟流向 | `uv run scripts/signals.py northbound` |
| 概念板块归属 | `uv run scripts/signals.py blocks 600519` |
| 个股资金流(分钟) | `uv run scripts/signals.py fundflow 600519` |
| 龙虎榜(个股) | `uv run scripts/signals.py dragon 002475 --date 2026-06-12` |
| 全市场龙虎榜 | `uv run scripts/signals.py market-dragon --date 2026-06-12` |
| 限售解禁日历 | `uv run scripts/signals.py lockup 600519` |
| 行业涨跌排名 | `uv run scripts/signals.py industry` |
| 融资融券 | `uv run scripts/capital.py margin 600519` |
| 大宗交易 | `uv run scripts/capital.py block 600519` |
| 股东户数变化 | `uv run scripts/capital.py holders 600519` |
| 分红送转历史 | `uv run scripts/capital.py dividend 600519` |
| 个股资金流(120日) | `uv run scripts/capital.py fundflow120 600519` |
| 个股新闻 | `uv run scripts/news.py stock 600519` |
| 全球财经资讯 | `uv run scripts/news.py global` |
| 个股基本面信息 | `uv run scripts/fundamentals.py info 600519` |
| 财务快照(37字段) | `uv run scripts/fundamentals.py finance 600519` |
| F10公司资料 | `uv run scripts/fundamentals.py f10 600519 --section 公司概况` |
| 财报三表 | `uv run scripts/fundamentals.py report 600519 --table lrb` |
| 巨潮公告 | `uv run scripts/announcements.py list 600519` |
| 单票完整估值 | `uv run scripts/valuation.py full 600519` |
| PEG/PE消化计算 | `uv run scripts/valuation.py peg --pe 20 --cagr 0.3` |

> 每个命令加 `--help` 看全部参数,加 `--json` 输出原始 JSON。

## references 索引(按需读)

| 文件 | 何时读 |
|------|--------|
| [`data-sources.md`](references/data-sources.md) | **调东财前必读**:优先级、防封铁律、风控阈值、uv 环境、ticker 归一、FAQ |
| [`quotes.md`](references/quotes.md) | 行情字段:腾讯88字段索引(PB在46/总市值在45)、新浪vs腾讯、mootdx周期、指数代码歧义 |
| [`reports.md`](references/reports.md) | 研报 record 字段、iwencai key 申请与 X-Claw |
| [`signals.md`](references/signals.md) | 热点 reason、北向自缓存、板块归属、龙虎榜ST注意、解禁类型、行业字段 |
| [`capital.md`](references/capital.md) | 融资融券/大宗/股东户数/分红字段语义、push2 大陆IP风控 |
| [`news.md`](references/news.md) | 个股新闻间歇空、财联社下线、全球资讯字段 |
| [`fundamentals.md`](references/fundamentals.md) | mootdx 37字段、F10 9类、新浪三表结构、东财info字段 |
| [`announcements.md`](references/announcements.md) | 巨潮 orgId 坑、公告字段 |
| [`valuation.md`](references/valuation.md) | 估值公式详解、投资框架30x锚点、完整调研流程 A–D |

## 已知环境性限制(非代码问题)

- **mootdx 需国内 IP**(TCP 直连通达信),海外走代理;腾讯/新浪/百度/东财 HTTP 不受影响。
- **部分大陆住宅 IP** 被东财 push2 `stock/*` 间歇风控(`RemoteDisconnected`/空)——脚本已优雅降级,换网络/时段重试即可,详见 `references/data-sources.md`。
- **百度 K线** 部分 IP 现返回 403(风控)——脚本不崩、返回空;要均线可改用 mootdx K线本地算。
- **财联社快讯**已下线,用 `news.py global` 替代。
