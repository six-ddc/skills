# 数据源优先级 · 东财防封 · 环境 · FAQ

**先读这个文件**,再调任何东财(eastmoney)接口。

## 数据源优先级:能用通达信/腾讯,就别用东财

| 优先级 | 数据源 | 协议 | 封 IP | 覆盖 |
|--------|--------|------|-------|------|
| **1 首选** | **mootdx(通达信)** | TCP 7709 | **不封** | K线/五档/逐笔/财务快照/F10 |
| **2** | **腾讯财经** | HTTP GBK | **不封** | 价/PE/PB/市值/换手率/涨跌停/指数/ETF |
| **2** | **新浪行情** | HTTP GB18030 | **不封** | 价 + 五档盘口(腾讯兜底) |
| **3** | 新浪财报 / 巨潮 / 同花顺 / 百度 | HTTP | 低 | 财报三表/公告/一致预期/热点/板块 |
| **4 仅独有数据才用** | **东财 eastmoney** | HTTP | **有风控,会封** | 见下 |

凡是行情/K线/实时价/市值/财务三表能从 mootdx 或腾讯/新浪拿到的,一律走它们。

### 东财只用于它「独有、别处拿不到」的数据
> 龙虎榜席位 · 全市场龙虎榜 · 限售解禁 · 融资融券 · 大宗交易 · 股东户数 · 分红送转 · 个股资金流(分钟/日) · 行业板块排名 · 研报列表/PDF · 个股新闻 · 全球资讯 · 板块归属

## 东财防封(调用东财时必须遵守)

风控阈值(社区实测):每秒 >5 次 / 单 IP 并发 ≥10 / 1 分钟 ≥200 次 / 5 分钟 ≥300 次 → 临时封 IP(几分钟到几小时,表现为 `403`/`429`/超时/空数据)。

**铁律:**
1. **串行,不并发** —— 绝不对东财开多线程/协程。
2. **每次间隔 ≥1 秒 + 抖动**(QPS ≤2),批量调到 1.5~2 秒。
3. **复用 HTTP 会话**(Keep-Alive)。
4. **带正常 UA + Referer**(脚本已配好)。
5. **批量循环每只之间 sleep** —— AI 跑批量(如逐个拉 100 只龙虎榜)是被封头号元凶。

### 已内置:所有东财请求走 `em_get()`
`scripts/_common.py` 的 `em_get()` 自动做:串行限流(`EM_MIN_INTERVAL=1.0s` + 随机抖动)+ 复用 `EM_SESSION`(Keep-Alive)+ 默认 UA。**所有 eastmoney.com 端点代码都已走 `em_get`,直接跑即自带防封。** 批量任务把 `EM_MIN_INTERVAL` 调大即可。

> **已知环境性问题(非代码 bug):** 部分**大陆住宅宽带 IP** 被东财 push2 系列(尤其 `stock/get`、`stock/fflow/kline`)间歇风控,表现为 `RemoteDisconnected` / `HTTP 000` / 空数据。同一脚本换网络/时段实测正常。脚本已对这类失败优雅降级(打印 `[WARN]` 到 stderr、返回空)。遇到时:隔几分钟重试 / 换网络(手机热点)/ 调大 `EM_MIN_INTERVAL`。

## 环境与运行

```bash
# 安装 uv (一次性):  https://docs.astral.sh/uv/
curl -LsSf https://astral.sh/uv/install.sh | sh
```

脚本用 **PEP 723 内联依赖** —— `uv run scripts/<layer>.py <command>` 首次自动建临时环境装依赖(requests/pandas/mootdx/lxml 按脚本各取所需),之后走缓存,**无需手动 pip**。

- **iwencai**(仅语义搜索需要 key):`export IWENCAI_API_KEY=...`(申请:https://www.iwencai.com/skillhub)。其余源全部免费无 key。
- mootdx 走 TCP,**需国内 IP**;海外环境走代理(腾讯/新浪/百度/东财 HTTP 不受影响)。

### Ticker 归一(`_common.norm_ticker`)
`688017` / `SH688017` / `688017.SH` / `sz000001` / `BJ832000` 都归一为纯 6 位。需要交易所前缀时用 `market_symbol()`(尊重显式 `sh/sz/bj` 前缀,避免指数代码 `sh000001` 与深股 `sz000001` 撞车)。

## FAQ

- **iwencai 401** → 检查 key 有效 + 是否带 X-Claw Headers(脚本已带)。
- **同花顺一致预期返回空** → 该股无机构覆盖(小盘/次新/ST 常见),可 fallback 东财研报的 `predictThisYearEps`。
- **东财 PDF 403** → 必须带 `Referer: https://data.eastmoney.com/`(脚本已带)。
- **腾讯返回乱码** → GBK 编码,脚本已 `r.encoding="gbk"`。
- **腾讯字段 43 是 PB 吗?** → 不是,43=振幅,46=PB(详见 [quotes.md](quotes.md))。
- **北向历史只有最近几天?** → eastmoney 北向自 2024-08 断供,改本地 CSV 自缓存,越跑越多(详见 [signals.md](signals.md))。
- **行业板块为何用东财不用同花顺?** → 同花顺该接口加了反爬 401,东财 `m:90+t:2` 零鉴权且字段更丰富。
- **财联社快讯?** → 已下线(cls.cn 迁 Next.js,旧 API 404),改用东财全球资讯(详见 [news.md](news.md))。
- **不用 Claude Code 能用吗?** → 能。脚本是标准 PEP 723 Python,任何环境 `uv run` 即可,或把函数 import 进自己的程序。
