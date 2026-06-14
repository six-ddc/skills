# Layer 3 信号层 — 字段表与端点注意事项

热点题材归因、北向资金、板块归属、资金流、龙虎榜、限售解禁、行业轮动。
源端点跨同花顺与东财两家：同花顺端点用普通 `requests`，**所有东财端点必须走 `em_get`**
（统一限流 + Keep-Alive，防封 IP），不要自建 session。所有 `code` 入参先过 `norm_ticker`。

## 命令

```bash
# 同花顺当日强势股 + 题材归因 reason（人工运营 tags，独家）
uv run scripts/signals.py hot [--date YYYY-MM-DD]

# 北向资金实时分钟流向；--save 把当日收盘 hgt/sgt 写入本地 CSV 缓存
uv run scripts/signals.py northbound [--save YYYY-MM-DD]

# 东财个股所属板块/概念归属（行业+概念+地域混合）
uv run scripts/signals.py blocks <code>

# 东财个股分钟级资金流（单位=元）
uv run scripts/signals.py fundflow <code>

# 个股龙虎榜：上榜记录 + 买卖席位 TOP5 + 机构动向
uv run scripts/signals.py dragon <code> --date YYYY-MM-DD [--look-back 30]

# 全市场龙虎榜（默认今天）
uv run scripts/signals.py market-dragon [--date YYYY-MM-DD] [--min-net-buy FLOAT]

# 限售解禁日历（历史 + 未来 N 天，date 默认今天）
uv run scripts/signals.py lockup <code> [--date YYYY-MM-DD] [--forward-days 90]

# 全行业涨跌幅排名（东财，~100 个行业）
uv run scripts/signals.py industry [--top-n 20]
```

所有子命令支持 `--json` 输出原始 JSON 而非人类可读表格。

---

## 同花顺热点 — 当日强势股 + 题材归因 reason tags（独家）

源：`http://zx.10jqka.com.cn/event/api/getharden/...`（同花顺，**非东财**，普通 requests）。
核心价值：不只告诉你"哪些走强"，还告诉你**"为什么走强"** —— **`reason` 字段是同花顺编辑部
人工运营的题材标签**（如「算力租赁+Token工厂+AI政务」），这是机器算不出、第三方拿不到的独家信号。
做题材归因、热点轮动时优先看 `reason`。实测 73ms 拿到 ~125 只 + 完整字段。`--date` 默认今天。

#### 字段速查

| 原字段 | 中文 | 说明 |
|---|---|---|
| code | 代码 | 6 位股票代码 |
| name | 名称 | 简称 |
| **reason** | **题材归因** | **核心字段，人工运营 tags，如"算力租赁+Token工厂+AI政务"** |
| zhangfu | 涨幅% | 当日涨幅 |
| huanshou | 换手率% | 当日换手 |
| chengjiaoe | 成交额 | 元 |
| chengjiaoliang | 成交量 | 股 |
| ddejingliang | 大单净量 | 主力净流入指标 |
| close | 收盘价 | 元 |
| zhangdie | 涨跌额 | 元 |
| market | 市场 | 沪/深/北 |

---

## 北向资金 — hsgtApi 实时分钟流向 + 本地 CSV 自缓存历史

源：同花顺 `https://data.hexin.cn/market/hsgtApi/method/dayChart/`（**非东财**，普通 requests）。
返回当日实时分钟流向（含集合竞价 09:10–15:00，~262 个时间点），字段 `time / hgt_yi(沪股通累计
净买入) / sgt_yi(深股通累计净买入)`，单位**亿元**。

> **为什么自缓存：** eastmoney 全系北向数据自 **2024-08** 后净买额字段返回 NaN/0，属上游断供
> （行业性问题）。故改为**本地 CSV 自缓存模式**——每次拉实时数据后把当日收盘值写入本地 CSV
> (`~/.tradingagents/cache/northbound_daily.csv`)，历史越跑越丰富，靠日积月累自建一份北向收盘序列。

`--save YYYY-MM-DD` 时：取实时序列里最后一个非空点（当日收盘累计净买入）写入/更新该日期到 CSV。
辅助函数：`_northbound_cache_path()`（缓存路径，自动建目录）、`_save_northbound_snapshot(date,hgt,sgt)`
（按日期去重 upsert，按日期排序回写）、`_load_northbound_history(n)`（读最近 N 天）。

---

## 东财 slist — 个股所属板块/概念归属

源：东财 `https://push2.eastmoney.com/api/qt/slist/get`（`spt=3`，走 `em_get`）。
一次调用拿到个股所属的全部板块（行业 + 概念 + 地域**混在一个列表**），含板块代码（BK 码）、
当日涨跌幅、板块龙头股。返回 `{total, boards:[{name,code(BK码),change_pct,lead_stock}], concept_tags:[板块名...]}`。

> **说明：** 百度 PAE `getrelatedblock` 接口已失效（实测返回 `ResultCode 10003` + 空数组），
> 改用东财 `slist` 个股所属板块接口（一次请求拿全，零鉴权）。东财把行业/概念/地域混在一个列表里返回，
> **板块名本身已自解释**（如「食品饮料」是行业、「贵州板块」是地域、「酿酒概念」是概念），AI 直接用板块名做题材归因即可。

> **注意：** 东财不区分行业/概念/地域类型（混在一个列表返回）。如需精确分类可按板块名判断，或另查全市场
> 板块清单（`clist` + `m:90+t:1/2/3`）——但后者每次需多发请求、大页易触发风控，不推荐在批量场景用。
> 本接口已内置 try/except 优雅降级：失败时返回 `{total:0, boards:[], concept_tags:[]}` 并打印 `[WARN]`。

---

## 东财 push2 — 个股资金流向（分钟级）

源：东财 `https://push2.eastmoney.com/api/qt/stock/fflow/kline/get`（走 `em_get`）。
盘中实时分钟级资金流（主力/小单/中单/大单/超大单净流入）。返回
`[{time, main_net, small_net, mid_net, large_net, super_net}, ...]`。

> **单位是元（非万元）：** push2 资金流金额单位是**元**，使用时注意换算（÷1e4 得万元）。
> `klt=1` 分钟级，`klt=101` 日级（本命令用 klt=1）。日级资金流见 Layer 4.5 `stock_fund_flow_120d()`。

> **说明：** 百度 PAE `fundflow` 和 `fundsortlist` 接口已于 2026-05 下线（返回 null），改用东财 push2 资金流 API。

本接口**保留原有 try/except 优雅降级**：请求失败时打印 `[WARN]` 到 stderr、返回 `[]`，不中断批量流程。

---

## 龙虎榜席位 — 个股上榜记录 + 买卖席位 TOP5 + 机构动向

源：东财 datacenter（经 `eastmoney_datacenter`）。`dragon <code> --date YYYY-MM-DD [--look-back 30]`。
返回 `{records, seats:{buy,sell}, institution}`：
- `records`：回看窗口内每次上榜（date / reason 上榜原因 / net_buy 万元 / turnover 换手率）。
- `seats`：最近一次上榜的买入/卖出席位 TOP5（营业部 name / 买卖额 / 净额，单位万元）。
- `institution`：从买卖席位明细中筛 `OPERATEDEPT_CODE="0"`（机构专用席位）汇总的买/卖/净额。

涉及报表：`RPT_DAILYBILLBOARD_DETAILSNEW`（上榜记录）、`RPT_BILLBOARD_DAILYDETAILSBUY` / `RPT_BILLBOARD_DAILYDETAILSSELL`（买卖席位明细）。

> **ST 股注意：** 5% 涨跌停更容易触发龙虎榜（"连续三日偏离值累计达 12%"），科创板 20% 涨跌停则较少触发。
> 即同一组上榜规则下，ST 股因涨跌停幅度小、更易累计触发，龙虎榜里 ST 股占比偏高属正常现象，不代表资金异动更强。

---

## 限售解禁日历 — 历史解禁 + 未来 N 天待解禁

源：东财 datacenter 报表 `RPT_LIFT_STAGE`（经 `eastmoney_datacenter`）。`lockup <code> [--date 今天] [--forward-days 90]`。
返回 `{history, upcoming}`，每条含 date(FREE_DATE) / type(限售股类型) / shares(解禁股数) / ratio(解禁占比)。

**限售股类型参考：**
- 首发原股东限售股份（IPO 后 1-3 年）
- 首发机构配售股份（IPO 战略配售）
- 定向增发机构配售股份（6-18 个月）
- 股权激励限售股份

---

## 行业板块排名（同花顺加了反爬 401,故改用东财）

源：东财 `https://push2.eastmoney.com/api/qt/clist/get`（`fs=m:90+t:2`，走 `em_get`）。
全行业涨跌幅排名（~100 个行业），一次调用看全市场行业轮动。返回 `{top, bottom, total}`，每条含
rank / name / change_pct / code / up_count / down_count / leader(领涨股) / leader_change。

> **为何从同花顺换东财：** 同花顺行业板块接口**加了反爬（实测返回 401）**，故行业板块排名改用东财
> `clist` 接口（`m:90+t:2` 即行业板块板块类，零鉴权、一次请求拿全）。注意东财 clist 大页/高频易触发风控，
> 已统一经 `em_get` 限流。

---

## 全市场龙虎榜

源：东财 datacenter `RPT_DAILYBILLBOARD_DETAILSNEW`（经 `eastmoney_datacenter`）。`market-dragon [--date 今天] [--min-net-buy 万元]`。
当日所有触发龙虎榜的股票 + 上榜原因 + 买卖净额 + 换手率。返回
`{date, total_records, stocks:[{code,name,reason,close,change_pct,net_buy_wan,buy_wan,sell_wan,turnover_pct}]}`。
按 `BILLBOARD_NET_AMT` 降序；`--min-net-buy` 按净买入(万元)下限过滤；非交易日/盘后未更新返回带 `note` 的空结果。

---

## 组合用法：题材热度 + 资金验证

把 `hot` 的 `题材归因` 做词频统计找当日热门题材，再用 `fundflow` / `dragon` 验证资金面是否跟上；
`blocks` 把个股映射到板块，`industry` 看板块在全市场的相对强弱——题材、资金、板块三者交叉印证。
