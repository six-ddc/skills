# 估值公式 · 投资框架 · 完整调研流程

对应脚本:`scripts/valuation.py`。

## 命令

```bash
uv run scripts/valuation.py full 600519              # 腾讯实时 + 同花顺一致预期 → PE_fwd/PEG/PE消化
uv run scripts/valuation.py peg --pe 20 --cagr 0.3   # 纯计算 PEG (cagr 小数, 0.3=30%)
uv run scripts/valuation.py pe-digest --pe 50 --cagr 0.3 --target 30
```

`full` 返回:`name/price/mcap_yi/pe_ttm/pb/eps_cur/eps_next/pe_fwd/cagr_pct/peg/digest_years/analyst_count`。
`analyst_count < 3` 时一致预期参考价值低。

## 公式

| 指标 | 公式 | 解读 |
|------|------|------|
| 前向PE | 当前股价 / 未来年度一致预期EPS | — |
| CAGR | 次年EPS / 当年EPS − 1 | 增速 |
| PEG | 前向PE / (CAGR×100) | <1 便宜 / 1–1.5 合理 / >1.5 贵 |
| PE消化 | `ln(PE/30) / ln(1+CAGR)` 年 | 当前PE按增速消化到 30x 需几年 |

```python
def forward_pe(price, eps):     return float("inf") if eps<=0 else price/eps
def calc_peg(pe, cagr):         return float("inf") if cagr<=0 else pe/(cagr*100)
def pe_digestion(pe, cagr, target=30):
    if pe<=target: return 0.0
    if cagr<=0:    return float("inf")
    return math.log(pe/target)/math.log(1+cagr)
```

## 投资框架速查

```
壁垒 → 增速 → PE消化 → PEG校验
1. 有壁垒吗?(tech_moat / capacity_moat) → 没有则排除
2. 增速多少?(CAGR > 30% 才有意义)
3. PE多久消化到30x?(< 2年合理, > 4年太贵)
4. PEG多少?(< 1 便宜, 1–1.5 合理, > 1.5 贵)
```

- **30x PE 锚点:** A 股成长股合理估值的重力线,所有行业统一用 30x。
- **期权定价例外:** PEG > 3 但壁垒极深时,本质是看涨期权,不适用 PEG 框架。

## 完整调研流程

### 流程 A:单票完整估值(30 秒)
`uv run scripts/valuation.py full <code>` —— 一条命令拿到 PE_fwd/PEG/PE消化/机构覆盖。

### 流程 B:批量估值对比
```bash
for c in 688017 300308 300476 002463; do uv run scripts/valuation.py full $c --json; done
```

### 流程 C:主题研报批量检索
```bash
uv run scripts/reports.py iwencai "人形机器人 行星滚柱丝杠 2026" --size 50   # NL 语义搜索(唯一能力)
uv run scripts/reports.py list 688017                                       # 按标的拉东财研报+EPS预测
```
iwencai 做跨主题 NL 检索,东财 `list` 按标的更稳;两者互补。

### 流程 D:新标的快速调研(组合多层)
```bash
uv run scripts/reports.py    eps 688017          # 1. 有无机构覆盖
uv run scripts/quotes.py     realtime 688017     # 2. 实时估值 PE/PB/市值
uv run scripts/valuation.py  full 688017         # 3+4. PE消化 + PEG
uv run scripts/signals.py    blocks 688017       # 5. 概念板块归属
uv run scripts/signals.py    fundflow 688017     # 6. 当日分钟资金流
uv run scripts/capital.py    fundflow120 688017  # 7. 近120日主力净流入
uv run scripts/signals.py    dragon 688017 --date 2026-06-12   # 8. 龙虎榜
uv run scripts/signals.py    lockup 688017       # 9. 解禁预警
uv run scripts/capital.py    margin 688017       # 10. 融资融券
uv run scripts/capital.py    holders 688017      # 11. 股东户数(筹码集中度)
```

> 信号层组合(题材热度词频 + 北向 + 行业轮动)见 [signals.md](signals.md)。
