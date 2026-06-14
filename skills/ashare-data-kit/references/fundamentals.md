# Layer 6 基础数据层 — 字段表与端点注意事项

财务快照（37字段季报）、F10 公司文本（9大类）、东财个股基本面、新浪财报三表
（资产负债表/利润表/现金流量表）。

源端点：
- `finance` / `f10` 走 **mootdx**（通达信 TCP 7709），`from mootdx.quotes import Quotes`
  在函数内部惰性导入；不封 IP。
- `info` 走 **东财 push2 stock/get**，经 `em_get`（统一限流 + Keep-Alive，防封 IP），
  不要自建 session。
- `report` 走 **新浪财报 openapi**，普通 `requests.get`（非东财，不经 em_get）。

所有 `code` 入参先过 `norm_ticker`。

## 命令

```bash
# 东财个股基本面（行业/股本/市值/上市日/价格）
uv run scripts/fundamentals.py info <code>

# mootdx 37字段财务快照（季报）
uv run scripts/fundamentals.py finance <code>

# mootdx F10 公司文本（9大类，--section 默认 公司概况）
uv run scripts/fundamentals.py f10 <code> [--section 公司概况]

# 新浪财报三表（--table fzb/lrb/llb，--num 取最近 N 期）
uv run scripts/fundamentals.py report <code> [--table lrb] [--num 8]
```

所有子命令支持 `--json` 输出原始 JSON 而非人类可读表格（`f10` 返回纯文本字符串，
`output` 对 str 原样打印）。

---

## info — 东财个股基本面（push2 stock/get）

源：`https://push2.eastmoney.com/api/qt/stock/get`，`secid=<market_code>.<code>`
（6 开头 = 1 上海，其余 = 0 深圳），`fltt=2 invt=2`，
`fields=f57,f58,f84,f85,f127,f116,f117,f189,f43`。

东财字段含义：

| 字段 | 返回键 | 含义 |
| --- | --- | --- |
| f57  | code         | 股票代码 |
| f58  | name         | 股票名称 |
| f127 | industry     | 所属行业 |
| f84  | total_shares | 总股本（股） |
| f85  | float_shares | 流通股（股） |
| f116 | mcap         | 总市值（元） |
| f117 | float_mcap   | 流通市值（元） |
| f189 | list_date    | 上市日期 YYYYMMDD（转成 str 返回） |
| f43  | price        | 当前价 |

> **风控与优雅降级（必读）：** 东财 push2 在**部分大陆住宅 IP** 上有风控，握手阶段
> 直接断连（`RemoteDisconnected` / `ConnectionError`）。旧 §6.3 代码没有 try/except，
> 遇到风控会直接抛异常崩溃。现已用 `try/except` 包住 `em_get` + `.json()`，失败时
> 打印 `[WARN] ... {e}` 到 **stderr** 并返回空 dict `{}`（优雅降级，不中断上层流程）。

---

## finance — mootdx 财务快照（37字段季报）

`client.finance(symbol=...)` 返回一行 37 字段的季报快照 DataFrame，经 `df_records`
转 list[dict]。主要字段：

- `liutongguben`（流通股本）、`zongguben`（总股本）
- `eps`（每股收益）、`bvps`（每股净资产）、`roe`（净资产收益率 %）
- `profit`（净利润）、`income`（主营收入）
- `meigujingzichan`（每股净资产）、`meigugongjijin`（每股公积金）
- `meiguweifeipeili`（每股未分配利润）
- 等共 37 个季报财务字段

> mootdx 的 `market` 约定：0 = 深圳，1 = 上海（factory 用 `market='std'`，
> symbol 直接传 6 位代码即可）。

---

## f10 — mootdx F10 公司文本（9大类）

`client.F10(symbol=..., name=<section>)` 返回纯文本字符串，`output` 原样打印。
9 大类 section 取值：

```
最新提示  公司概况  财务分析
股东研究  股本结构  资本运作
业内点评  行业分析  公司大事
```

`--section` 默认 `公司概况`。

> **省 token 优化提示（§6.2）：** "股东研究" 中的【4.股东变化】章节含大量历史十大
> 股东列表，实测 16000+ chars。如只需最新持仓结构，建议只保留最新一期，可省约 70%
> token。

---

## report — 新浪财报三表（fzb / lrb / llb）

源：`https://quotes.sina.cn/cn/api/openapi.php/CompanyFinanceService.getFinanceReport2022`
（普通 `requests.get`，非东财）。`paperCode=<sh|sz><code>`（6 开头 = sh，其余 = sz），
`source=<table>`，`type=0`，`page=1`，`num=<N>`。

`--table` 取值：`fzb`（资产负债表）/ `lrb`（利润表）/ `llb`（现金流量表）。

### report_list 结构

新浪实际返回结构为：`result.data.report_list` 是一个**「按报告期（如 `'20260331'`）
为键」的 dict**，而非列表。每期对象的 `data` 字段才是行项列表
`[{item_title, item_value, item_tongbi}]`。

解析逻辑：按报告期键倒序取最近 `num` 期，每期产出一条 dict：

```
{"报告期": "2026-03-31", "<科目>": "<值>", "<科目>_同比": <同比>, ...}
```

- `报告期` 由键 `YYYYMMDD` 格式化为 `YYYY-MM-DD`。
- `item_value` 为新浪原始字符串数值，原样写入 `rec[item_title]`。
- 仅当 `item_tongbi` 非空（不在 `None`/`""`）时，附加 `"<科目>_同比"` 键。
- `item_title` 为空或 `item_value` 为 None 的行项跳过。
