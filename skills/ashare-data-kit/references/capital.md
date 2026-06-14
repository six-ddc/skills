# Layer 4 资金面 / 筹码层 — 字段表与端点注意事项

融资融券、大宗交易、股东户数、分红送转、个股资金流（120日）。
源端点全部为东财：融资融券/大宗交易/股东户数/分红走 datacenter（经 `eastmoney_datacenter`），
个股资金流走 push2his daykline（经 `em_get`）。**所有东财端点必须走 `em_get`**（统一限流 +
Keep-Alive，防封 IP），不要自建 session。所有 `code` 入参先过 `norm_ticker`。

## 命令

```bash
# 融资融券明细（日级）
uv run scripts/capital.py margin <code> [--page-size 30]

# 大宗交易记录（含溢价率计算）
uv run scripts/capital.py block <code> [--page-size 20]

# 股东户数变化（季度级）
uv run scripts/capital.py holders <code> [--page-size 10]

# 分红送转历史
uv run scripts/capital.py dividend <code> [--page-size 20]

# 个股资金流（最近120个交易日，单位=元）
uv run scripts/capital.py fundflow120 <code>
```

所有子命令支持 `--json` 输出原始 JSON 而非人类可读表格。

---

## 融资融券明细 — RPTA_WEB_RZRQ_GGMX（日级）

源：东财 datacenter 报表 `RPTA_WEB_RZRQ_GGMX`（filter `(SCODE="<code>")`，按 `DATE` 倒序）。
返回每个交易日的两融余额与买卖偿还明细。

#### 字段速查

| 字段 | 中文 | 说明 |
|---|---|---|
| date | 日期 | 交易日 |
| **rzye** | **融资余额** | 单位元。融资买入后尚未偿还的余额，**最核心指标**：持续攀升=多头加杠杆做多 |
| rzmre | 融资买入额 | 当日新增融资买入（元） |
| rzche | 融资偿还额 | 当日融资偿还（元） |
| **rqye** | **融券余额** | 单位元。融券卖出后尚未偿还的余额，攀升=空头加杠杆做空 |
| rqmcl | 融券卖出量 | 当日融券卖出量（股） |
| rqchl | 融券偿还量 | 当日融券偿还量（股） |
| rzrqye | 融资融券余额合计 | = 融资余额 + 融券余额（元），代表该股两融资金总规模 |

> **读法：** `rzye` 持续放大、`rqye` 低位 → 杠杆资金看多；`rqye` 异常放大 → 有资金借券做空，
> 需警惕。换算成亿元用 `÷1e8`（如 `rzye/1e8`）。

---

## 大宗交易 — RPT_DATA_BLOCKTRADE（含溢价率算法）

源：东财 datacenter 报表 `RPT_DATA_BLOCKTRADE`（filter `(SECURITY_CODE="<code>")`，按 `TRADE_DATE` 倒序）。
返回每笔大宗交易的成交价、量、额与买卖营业部。

#### 溢价率算法

```
premium_pct = (DEAL_PRICE / CLOSE_PRICE - 1) × 100
```

即「大宗成交价 ÷ 当日收盘价 - 1」再乘 100，四舍五入到 2 位小数；`CLOSE_PRICE` 为 0（缺数据）时溢价记 0。
- **正溢价**（成交价高于收盘）：买方愿意溢价接盘，多为机构/产业资本看好，相对偏多信号。
- **负溢价/折价**（成交价低于收盘）：卖方急于出货，常见于股东减持、解禁套现，相对偏空信号。

#### 字段速查

| 字段 | 中文 | 说明 |
|---|---|---|
| date | 日期 | 成交日（TRADE_DATE） |
| price | 成交价 | 大宗成交价（DEAL_PRICE） |
| close | 收盘价 | 当日二级市场收盘价（CLOSE_PRICE），用于算溢价 |
| premium_pct | 溢价率% | 见上方算法，正=溢价、负=折价 |
| vol | 成交量 | DEAL_VOLUME |
| amount | 成交额 | DEAL_AMT |
| buyer | 买方营业部 | BUYER_NAME |
| seller | 卖方营业部 | SELLER_NAME |

---

## 股东户数变化 — RPT_HOLDERNUMLATEST（季度级）

源：东财 datacenter 报表 `RPT_HOLDERNUMLATEST`（filter `(SECURITY_CODE="<code>")`，按 `END_DATE` 倒序）。
返回各报告期股东户数及其环比变化、户均持股。

#### 字段速查

| 字段 | 中文 | 说明 |
|---|---|---|
| date | 报告期 | END_DATE |
| holder_num | 股东户数 | 期末股东总户数 |
| change_num | 户数变化 | 较上期增减户数（HOLDER_NUM_CHANGE） |
| change_ratio | 环比% | 户数环比变化百分比（HOLDER_NUM_RATIO） |
| avg_shares | 户均持股 | 户均流通股数（AVG_FREE_SHARES） |

> **核心读法（筹码集中度）：股东户数持续减少 = 筹码集中 = 主力吸筹信号。** 总股本不变下，户数下降
> 意味着户均持股上升、筹码向少数账户集中，常对应主力资金低位吸筹/控盘。反之户数连续放大 = 筹码分散
> = 散户进场/主力派发。结合 `avg_shares` 走势一起看更稳。

---

## 分红送转历史 — RPT_SHAREBONUS_DET

源：东财 datacenter 报表 `RPT_SHAREBONUS_DET`（filter `(SECURITY_CODE="<code>")`，按 `EX_DIVIDEND_DATE` 倒序）。
返回历次分红送转方案与进度。

#### 字段速查

| 字段 | 中文 | 说明 |
|---|---|---|
| date | 除权除息日 | EX_DIVIDEND_DATE |
| bonus_rmb | 每股派息(税前) | PRETAX_BONUS_RMB，单位元/股 |
| transfer_ratio | 每10股转增 | 资本公积转增比例（TRANSFER_RATIO） |
| bonus_ratio | 每10股送股 | 送红股比例（BONUS_RATIO） |
| plan | 进度 | 方案进度（ASSIGN_PROGRESS，如预案/股东大会通过/实施） |

> **读法：** `bonus_rmb` 反映现金分红力度（结合股价算股息率）；`transfer_ratio` / `bonus_ratio` 是高送转，
> 仅做股本扩张、不改变股东权益总额，常被炒作为题材。`plan` 区分方案是预案还是已实施。

---

## 个股资金流（120日，日级）— push2his daykline

源：东财 `https://push2his.eastmoney.com/api/qt/stock/fflow/daykline/get`（走 `em_get`）。
`secid` 由 `1.<code>`（沪市，code 以 6 开头）/ `0.<code>`（其余）拼成；`lmt=120` 取最近 120 个交易日。
返回 `[{date, main_net(主力净流入), small_net, mid_net, large_net, super_net}, ...]`。

> **单位是元（非万元）：** 与 push2 分钟级资金流一致，金额单位是**元**，使用时注意换算
> （÷1e4 得万元、÷1e8 得亿元）。本命令是日级（daykline）；分钟级日内资金流见 Layer 3 `signals.py fundflow`。

> **优雅降级：** 本接口**保留原有 try/except 优雅降级** —— push2his 请求失败时打印
> `[WARN] push2 资金流请求失败: ...` 到 **stderr**、返回 `[]`，不中断批量流程。`klines` 每行按逗号切，
> 字段不足 7 个的行跳过；分量值为 `"-"` 记 0。

#### 字段速查

| 字段 | 中文 | 说明 |
|---|---|---|
| date | 日期 | 交易日 |
| main_net | 主力净流入 | 元。常用「近20日累计主力净流入」判断主力进出 |
| small_net | 小单净流入 | 元，散户盘 |
| mid_net | 中单净流入 | 元 |
| large_net | 大单净流入 | 元 |
| super_net | 超大单净流入 | 元，机构/大资金盘 |

---

## ⚠️ 大陆住宅 IP 间歇封锁

push2/push2his 系列对**部分大陆住宅宽带 IP** 有连接级风控，表现为偶发 `HTTP 000`（连接被拒/超时）
或返回空——**这不是代码问题**（同一代码在其他网络/时段实测正常）。遇到时：

1. 隔几分钟重试；
2. 换网络环境（如手机热点）；
3. 降低请求频率（调大 `EM_MIN_INTERVAL`）。

日级资金流务实替代：仍可用 mootdx 算量价，或换时段重试。`RemoteDisconnected` / `HTTP 000` 属同一类
连接级风控现象，遇到不要当作代码 bug 排查。
