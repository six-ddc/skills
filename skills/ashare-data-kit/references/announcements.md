# Layer 7 公告层 — 巨潮 cninfo.com.cn（orgId 坑与字段表）

巨潮公告全文检索（cninfo.com.cn）。**这不是东财系端点**，所以本层用普通
`requests.post`/`requests.get`，**不走 `em_get`**（em_get 是东财专用的限流 +
Keep-Alive session，仅对 eastmoney.com 域名生效，套到巨潮上没有意义）。`code`
入参先过 `norm_ticker`。本层无需 pandas：`output()` 对 list[dict] 会惰性尝试
pandas，没装则回退逐行打印，可接受。

## 命令

```bash
# 巨潮公告全文检索（title / type / date / url）
uv run scripts/announcements.py list <code> [--page-size 30]
```

子命令支持 `--json` 输出原始 JSON 而非人类可读表格。

> **最新公告摘要** 走的是 mootdx F10「最新提示」（含最近公告/分红/股东大会决议等摘要），
> 已并入 Layer 6 的 fundamentals。需要时用：
> `uv run scripts/fundamentals.py f10 <code> --section 最新提示`。本层不重复实现。

---

## 巨潮 orgId 并非统一 `gssx0{code}` 格式

巨潮全文检索接口 `POST https://www.cninfo.com.cn/new/hisAnnouncement/query` 的
`stock` 参数形如 `"{code},{orgId}"`，其中 **orgId 是巨潮内部机构编号，并不是
统一的 `gssh0{code}` / `gssz0{code}` 老格式**。例如：

| code   | 真实 orgId    | 老格式硬编码    | 硬编码结果            |
| ------ | ------------- | --------------- | --------------------- |
| 600519 | gssh0600519   | gssh0600519     | 命中（老股票恰好一致）|
| 601318 | 9900002221    | gssh0601318     | totalAnnouncement=0   |
| 601398 | jjxt0000019   | gssh0601398     | totalAnnouncement=0   |
| 688017 | 9900041602    | gssh0688017     | totalAnnouncement=0   |

若 orgId 填错，接口返回 `totalAnnouncement=0`、`announcements` 为空——表面像
「这只股票没有公告」，实则是 orgId 不匹配。**601xxx 段尤其严重**，大量股票走老格式
全部查不到公告。这就是该问题的症状。

## 动态映射表方案

`_cninfo_orgid(code)` 优先动态拉官方映射表，查不到再回退老格式硬编码：

1. **模块级缓存** `_CNINFO_ORGID_MAP`（dict）：首次调用时拉取一次，全程复用，
   避免每次查询都打一次映射表接口。
2. **动态拉取**：`GET http://www.cninfo.com.cn/new/data/szse_stock.json`，
   按 `stockList[].code → stockList[].orgId` 建映射表。
3. **命中即用**：`_CNINFO_ORGID_MAP.get(code)` 命中则直接返回真实 orgId。
4. **硬编码 fallback**（仅部分老股票如 600519/600036 适用，映射表拉取失败或
   查不到时兜底）：
   - `6` 开头 → `gssh0{code}`
   - `8` / `4` 开头 → `gsbj0{code}`
   - 其余 → `gssz0{code}`

映射表拉取失败时打印 `[WARN] 巨潮 orgId 映射表拉取失败，回退硬编码规则` 并继续走
fallback，不抛异常。

---

## 公告字段表

返回 `[{title, type, date, url}]`，取自响应 `announcements[]`：

| 字段    | 来源                     | 说明                                                          |
| ------- | ------------------------ | ------------------------------------------------------------- |
| `title` | `announcementTitle`      | 公告标题                                                      |
| `type`  | `announcementTypeName`   | 公告类型名                                                    |
| `date`  | `announcementTime`       | **Unix 毫秒整数**，经 `_cninfo_ts_to_date` 转 `YYYY-MM-DD`    |
| `url`   | `announcementId`         | 拼成 `.../new/disclosure/detail?annoId={announcementId}`      |

`_cninfo_ts_to_date(ts)`：`announcementTime` 是 Unix **毫秒** 整数，需
`datetime.fromtimestamp(ts / 1000)` 转日期字符串；非数值时退化取前 10 个字符。

请求要点：`POST .../hisAnnouncement/query`，表单参数 `tabName="fulltext"`、
`pageSize=str(page_size)`、`pageNum="1"`，其余 `column/category/plate/seDate/
searchkey/secid/sortName/sortType` 留空，`isHLtitle="true"`；headers 带
`Content-Type: application/x-www-form-urlencoded`、`Referer` 与 `Origin` 指向
`cninfo.com.cn`。
