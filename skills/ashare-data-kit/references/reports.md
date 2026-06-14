# Layer 2 研报层 — reports.py 参考

研报数据三路来源:

- **东财 reportapi** (`reportapi.eastmoney.com`) — A级公开 JSON API, 免费无 key, 走共享限流 `em_get`。按标的拉研报列表 + 下载 PDF。**主力来源, 最稳定。**
- **同花顺** (`basic.10jqka.com.cn`) — 直连 HTML 表格, 机构一致预期 EPS。非东财, 用普通 `requests`。
- **iwencai** (`openapi.iwencai.com`) — NL 语义搜索研报。需 API Key + X-Claw 头。非东财。**唯一价值在跨主题语义检索。**

## 命令

```bash
# 1) 东财研报列表 (默认翻 5 页, 每页 100 篇)
uv run scripts/reports.py list 688017
uv run scripts/reports.py list 688017 --max-pages 3 --json

# 2) 下载单份研报 PDF (按 infoCode, 从 list 结果取 infoCode 字段)
uv run scripts/reports.py pdf AP202401011234567890
uv run scripts/reports.py pdf AP202401011234567890 --out ./reports/foo.pdf

# 3) 同花顺机构一致预期 EPS
uv run scripts/reports.py eps 688017

# 4) iwencai NL 语义搜索研报 (需 IWENCAI_API_KEY)
uv run scripts/reports.py iwencai "人形机器人 行星滚柱丝杠 2026"
uv run scripts/reports.py iwencai "光模块 1.6T 量产" --channel report --size 50 --json
```

所有子命令支持 `--json`（输出原始 JSON 而非人类可读表格）。

## 2.1 东财研报列表 + PDF 下载 (主力)

`list <code>` → `eastmoney_reports()`。逐页拉 `reportapi.eastmoney.com/report/list`,
每页 `pageSize=100`, 默认最多 `--max-pages 5`。遇到空页或翻到 `TotalPage` 即停。
所有请求走 `em_get`（共享限流会话, 防东财封 IP）, 并带 `Referer: https://data.eastmoney.com/`。

### 研报 record 关键字段

| 字段 | 含义 |
|------|------|
| title | 研报标题 |
| publishDate | 发布日期 |
| orgSName | 机构简称 |
| infoCode | 用于拼 PDF URL (`pdf` 子命令的入参) |
| predictThisYearEps | 今年 EPS 预测 |
| predictNextYearEps | 明年 EPS 预测 |
| predictNextTwoYearEps | 后年 EPS 预测 |
| emRatingName | 评级 (买入 / 增持 / ...) |
| indvInduName | 行业分类 |

### PDF 下载

`pdf <info_code>` → URL 模板 `https://pdf.dfcfw.com/pdf/H3_{info_code}_1.pdf`。
默认存到 `./{info_code}.pdf`, 可用 `--out` 指定路径; 打印保存路径与字节数。

**踩坑: PDF 必须带 `Referer: https://data.eastmoney.com/`**, 否则 `pdf.dfcfw.com` 风控,
返回非 200 或极小的占位内容。本脚本经 `em_get` 复用限流会话并自动带该 Referer。
仅当 `status_code == 200` 且内容 `>= 1024` 字节时才落盘, 否则返回 warning。

## 2.2 同花顺机构一致预期 EPS (直连 basic.10jqka.com.cn)

`eps <code>` → `ths_eps_forecast()`。直连 `https://basic.10jqka.com.cn/new/{code}/worth.html`,
**非东财, 用普通 `requests.get`（不走 `em_get`）**。

踩坑要点:
- 页面是 **GBK 编码** → 必须 `r.encoding = "gbk"` 再 `pd.read_html`。
- `pd.read_html(StringIO(r.text))` 需要 `lxml`（已写进 PEP 723 依赖）。
- 在多个表格中找含 "每股收益" 或 "均值" 的那张; 找不到则 fallback 第一张。
- 返回 DataFrame: 年度 / 预测机构数 / 最小值 / **均值** / 最大值。**"均值" = 机构一致预期 EPS**。
- **"预测机构数" < 3 的要谨慎**（样本太少, 一致预期不可靠）。
- 脚本内用 `df_records(df)` 把 DataFrame 转 `list[dict]` 再 `output`。

## 2.3 iwencai — NL 语义搜索研报 (唯一能力)

`iwencai <query>` → `iwencai_search()`。POST `{IWENCAI_BASE}/v1/comprehensive/search`。

### API Key 申请

iwencai 走 SkillHub 2.0, 强制要求 API Key + X-Claw 鉴权头。
- 到 **https://www.iwencai.com/skillhub** 申请 Key。
- 设置环境变量:
  ```bash
  export IWENCAI_API_KEY=your_key
  export IWENCAI_BASE_URL=https://openapi.iwencai.com   # 可选, 默认即此值
  ```
- 未设置 `IWENCAI_API_KEY` 时, 脚本打印友好提示到 stderr 并 `exit(2)`, 不发请求。

### X-Claw 鉴权头 (SkillHub 2.0 强制)

每次请求除 `Authorization: Bearer <key>` 外, 还必须带一组 `X-Claw-*` 头 (`_claw_headers()`):

| Header | 值 |
|--------|----|
| X-Claw-Call-Type | `normal` |
| X-Claw-Skill-Id | `report-search` |
| X-Claw-Skill-Version | `2.0.0` |
| X-Claw-Plugin-Id | `none` |
| X-Claw-Plugin-Version | `none` |
| X-Claw-Trace-Id | `secrets.token_hex(32)`（每次随机生成） |

### 参数与去重

- `channel`: `report`(研报) / `announcement`(公告) / `news`(新闻), 默认 `report`。
- `size`: 默认 10, **实测可调到 50（隐藏参数）**, 本脚本默认 50。
- payload 里固定 `app_id = "AIME_SKILL"`。
- HTTP 非 200 或返回体 `status_code != 0` 时抛 `RuntimeError`。
- `dedup_articles()`: 同一 `uid` 仅保留 `score` 最高的段落, 再按 `publish_date` 倒序。
  无 `uid` 时回退用 `title|publish_date` 作 key。脚本默认对结果去重后输出。

### iwencai 的唯一价值

**NL 主题搜索。** "人形机器人 行星滚柱丝杠" 这种跨主题/跨标的检索只有 iwencai 能做。
**按单一标的搜研报走东财 `reportapi`（`list` 子命令）更稳定**, 别用 iwencai 干这活。
