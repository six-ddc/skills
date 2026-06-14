# Layer 5 新闻层 — 字段表与端点注意事项

东财个股新闻、东财全球资讯（7×24 滚动）。两个端点都属东财系，**必须走 `em_get`**
（统一限流 + Keep-Alive，防封 IP），不要自建 session。`code` 入参先过 `norm_ticker`。
本层无需 pandas：`output()` 对 list[dict] 会惰性尝试 pandas，没装则回退逐行打印，可接受。

## 命令

```bash
# 东财个股新闻（JSONP，search-api-web）
uv run scripts/news.py stock <code> [--page-size 20]

# 东财全球资讯（7×24 滚动快讯，免费无 key）
uv run scripts/news.py global [--page-size 50]
```

所有子命令支持 `--json` 输出原始 JSON 而非人类可读表格。

> **注意：** `global` 是 Python 关键字，但作为 argparse 子命令名是普通字符串、无冲突；
> 代码内分支判断用 `args.cmd == "global"`。

---

## 东财个股新闻（stock）

源：`https://search-api-web.eastmoney.com/search/jsonp`（JSONP 接口）。
请求带 `cb=jQuery_news` 回调名，`param` 是一段内嵌 JSON（指定 `keyword`、
`type=["cmsArticleWebOld"]`、分页等）。响应是 `jQuery_news(...)` 包裹的 JSONP，
代码取首个 `(` 与末个 `)` 之间的子串再 `json.loads`。

返回字段 `[{title, content, time, source, url}]`：

| 字段      | 来源                | 说明                              |
| --------- | ------------------- | --------------------------------- |
| `title`   | `title`             | 已用正则 `<[^>]+>` 去除 HTML 标签 |
| `content` | `content`           | 去标签后截断 200 字               |
| `time`    | `date`              | 发布时间                          |
| `source`  | `mediaName`         | 媒体来源                          |
| `url`     | `url`               | 原文链接                          |

文章列表取自 `result.cmsArticleWebOld`——**东财实际返回里它直接就是文章列表数组**
（非 `{list:[...]}` 嵌套），代码对此做了直接处理，空时安全返回 `[]`。

> **⚠️ 间歇性返回空：** 部分大陆住宅 IP 调本接口会只拿到 `passportWeb`（股民资料）
> 而无 `cmsArticleWebOld`（文章列表）——这是东财对该 IP 的间歇风控，**非代码 bug**
> （同一代码在其他网络/时段实测正常）。代码已对空结果安全返回 `[]`；遇到时隔几分钟、
> 换网络环境（如手机热点）或降低请求频率（调大 `EM_MIN_INTERVAL`）后重试即可。

---

## 东财全球资讯（global）

源：`https://np-weblist.eastmoney.com/comm/web/getFastNewsList`（7×24 滚动快讯）。
固定参数 `client=web`、`biz=web_724`、`fastColumn=102`、`sortEnd=""`，外加
`pageSize` 与每次随机生成的 `req_trace`（`uuid.uuid4()`）。免费、无需 key。

返回字段 `[{title, summary, time}]`，取自 `data.fastNewsList`：

| 字段      | 来源        | 说明              |
| --------- | ----------- | ----------------- |
| `title`   | `title`     | 快讯标题          |
| `summary` | `summary`   | 摘要，截断 200 字 |
| `time`    | `showTime`  | 展示时间          |

---

## 财联社快讯（cls_telegraph）— ⚠️ 已下线，不提供子命令

> **⚠️ 2026-05 已失效：** 财联社网站迁移到 Next.js 架构，旧版公开接口
> `cls.cn/nodeapi/telegraphList` 全面下线（返回 404），新版 API 需签名认证，无法
> 公开 HTTP 调用。因此本脚本**不提供财联社子命令**。**全市场实时快讯请改用上文
> 「东财全球资讯」（`global` 子命令）**——7×24 滚动，免费无 key。

历史接口仅作参考（已不可用）：旧版 `GET cls.cn/nodeapi/telegraphList?rn=<n>&page=1`
返回 `data.roll_data[]`，字段映射为 `{title, content, time}`
（`title`/`content` 缺失时回退 `brief`，`time` 取 `ctime`）。
