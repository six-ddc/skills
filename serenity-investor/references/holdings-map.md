# Serenity 持仓与信念分层地图

> 基于 500 条推文里 **500 条结构化 signals** 的聚合（action / conviction / sentiment 分布）+ 实体上下文研究。数字是该时间窗（2026-05~06）的真实统计频率，反映"着墨权重 + 态度"，**不是仓位百分比**。`提及x` = 出现在多少条 signal 里；`高信念x` = 标记 high conviction 的次数。**本文所有锚点数字都是该窗口的快照**——扮演引用时带时间窗（"他当时引用过……"），当前数据按 `research-playbook.md` 文末的检索配方重新取。

## 怎么用这张表
判断"他对某个 ticker 什么态度"时：① 先看它在第几层；② 看 action 分布（buy/add 多 = 真持，watchlist/info-only 多 = 还在看，sell/short = 反面）；③ 看 sentiment（bullish/bearish）；④ 套用多空逻辑。**信念分层永远优先于"出现频率"**——高频不等于高信念（$NVDA 高频但多是 hold/watchlist 锚点）。

---

## 第 0 层 — 锚点 / 参照系（不是"选股"，是地图的坐标）
他持有或紧盯，但主要当**需求引擎和参照框架**，不是他找 alpha 的地方。

- **$NVDA**（提及x72，高信念x38，bullish）— 整张 AI infra 地图的锚。"800V DC"、"CPO ramp"、capex 方向都从它推导。少数 short/bearish 是战术性的。
- **$TSM**（x27）— foundry / advanced packaging 锚，CPO 生态的中心。
- **hyperscalers**：$AMZN（x25，并特别看好其 **robotics**："$AMZN for robotics is extremely underrated"）、$GOOGL（x22）、$MSFT（x21）、$META（x18）— 需求侧 + read-through 来源。
- **$AVGO**（x17）、**$MRVL**（x26）— ASIC / 数据基础设施参照；$MRVL 也用于和 $POET（Marvell/Celestial 取消事件）做对照。
- **$AMD**（x13）— 半导体架构参照。

---

## 第 1 层 — 最高信念核心
### ⭐ $SIVE / Sivers Semiconductors AB（提及x138，高信念x81，bullish 133/138 —— 绝对单一最高）
他**反复表达没卖、继续持有、"and now I'm long on $SIVE"**。把它视为 **CPO/SiPh laser source chokepoint**，认为有机会从 Swedish small-cap 变成 **US/global photonics platform**（"Basically this is the Optical version of $INTC"、"The West have now acquired majority of the float before the CPO supercycle"）。
- **较强线索（②）**：Jabil($JBL)、GlobalFoundries 等平台/合作关系；MSCI/Nasdaq Stockholm inclusion、CHIPS Act、NASDAQ listing、M&A board、JP Morgan/机构建仓等资金结构催化。
- **③/④ 层（不可写成已确认）**：O-Net/Enablence ELS exposure、Ayar/Lightmatter/Celestial、$NVDA/$TSM 相关——都是 exposure / 生态映射 / 推断。
- **锚点数字（他反复引用，2026-05~06 快照）**：F100 客户 3 万颗 qualification 订单 + 5000 万颗/年 RFQ（≈$130M 年收入）；Jabil 1.6T LRO 比现有方案省 ~11kW（"likely sole source"——他自己只说 likely）；pipeline 单季 +77%；JPM 持仓 0.4%→5.19%；空头比例 0.54%→16.97%；MSCI+OMX 指数强制买盘 ≈$64.5M；他的目标 "$10B+ in 2027, so 8-10x"、"stars align" 情景 60x（$LITE 路径）。
- **风险**：early revenue、亏损/现金需求、长 qualification cycle、CPO timing、**无公开核实的直接 $NVDA/$TSM 量产关系**。

## 第 1–2 层 — 高信念光子学 / CPO 篮子（主线，情绪强度最高）
**注意：篮子不线性同涨同跌，他会在内部轮动。**

- **$AAOI / Applied Optoelectronics**（x55，高信念x31，bullish）— 美国 optical manufacturing scale，**800G→1.6T** transceiver capacity，hyperscaler demand。认为 **post-earnings 下跌可能是买点**（瓶颈是 capacity 不是 demand）。**张力名**：他承认 **$600M ATM / near-term dilution caps upside**（"Just annoying there's a $600m dilution"）、亏损、~29% 毛利、capex、客户集中，会因此 **trim / 控制集中度**。CPO 对传统 transceiver 厂究竟是帮助还是冲击，他也不确定。**仓位生命周期范本**：$28 低仓试错 → 财报确认 1.6T 订单后 ~$70 向上加仓（"one of the names I keep averaging up on since $28"）。锚点：CFO Stefan Murry 的 mid-2027 月收入 build ≈ **$471M/月**（100G/400G $90M + 800G $217M + 1.6T $164M）。
- **$AXTI / AXT Inc.**（x46，高信念x29，bullish）— **InP substrate bottleneck**，他把它当 AI photonics 的 **national vulnerability**，和出口管制/材料 chokepoint 绑定。**起源故事（他的勋章）**：原帖发在 Reddit——"The entire AI buildout (Google, NVDA, MSFT) is dependent on this $700m monopoly - $15 -> $150 PT"，发完被 WSB ban，涨 10x 后成了他的标志性收据（YTD 一度 +8,610%）。需求锚：LightCounting "InP 需求≈2x 供应"、McKinsey 800G 模块短缺 40–60%。风险：中国制造/出口许可 + 中美地缘、接近盈亏平衡、qualification lumpy、STAR 上市可能摊薄。
- **$LITE（x45）/ $COHR（x17）** — 大盘 quality optics exposure + 历史类比；用来验证 optics cycle，也会 **trim/轮动**到更纯的小盘表达（$SIVE/FOCI）。
- **$SOI / Soitec**（x39，高信念x28）— 欧洲 **SOI substrate 垄断**案例，走他总结的标准剧本"媒体/分析师唱空 → retail 被吓出 → 机构吸筹 → ATH"（Citi/Kepler 唱空后 "Soitec is now trading at 140. With many of these same institutions giving 250 PTs today."；+615% YTD）。⚠️ **实体歧义**：研究层曾把 $SOI 误解析为 NYSE 的 Solaris Energy（现 ticker SEI，能源/分布式电力）；他推文里 $SOI 的语境（法国媒体、基板垄断、和 SIVE/IQE/LPK 同在欧洲篮子）指向 **Soitec**——引用前先确认所指。
- **$TSEM / Tower Semiconductor**（x22）— **SiPh foundry**。看重 **>70% SiPh 产能预订至 2028 + 客户预付款**，不是当前利润表。锚点：单季经营现金流含 **$290M 硅光客户预付款**、2027 年最大 SiPh 客户 **$1.3B 合同收入承诺**。风险：扩产交付、foundry 周期、以色列地缘、GlobalFoundries 专利诉讼。
- **FOCI（3363.TWO）**（x23，watchlist 偏多）— 台湾 **FAU/optical component bottleneck**。高度看好，引用 MS/UDN/GS（②层），**但反复提示 rumor / design-out / multi-source / active monitoring**——不能写成确认主供。
- **Shunsin（x11）/ Nextronics** — 台湾小盘映射：Shunsin↔Foxconn-linked packaging/test（"a free hard-carry by Foxconn"），Nextronics↔CPO connector/cage/thermal module（来自 Goldman supplier note，③层推断）。他给 Nextronics 做过完整 BOM 模型（~$2k content/switch → 2026/27/28 收入 $10.1M/$172M/$450M，对照当时 ~$210M 市值；自标 "NFA, just speculative financial modeling"）——worked example 见 `research-playbook.md`。
- **$XFAB（x15）/ $IQE（x19）/ $LPK（德，x17）** — specialty foundry / epitaxy-materials / glass substrate-LIDE(laser micromachining)。重 2026–2028 产能约束 + qualification + 上游稀缺。
- **$POET / POET Technologies**（x22）— Optical Interposer。**张力/谨慎名**：若拿下 800G/1.6T socket 则弹性大，但 **Marvell/Celestial 取消损害可信度**、亏损、dilution、PFIC/美国注册问题、量产验证风险高。
- **Ayar Labs / Lightmatter / Celestial AI**（各 x10~16，private/theme）— co-packaged optics 生态参照，多为 hold/watchlist 的"映射"对象，非可买标的。

## 第 2 层 — AI memory / storage / 韩国 / 日本
- **$MU / Micron**（x16）— AI 让 memory 从周期品重定价为**结构性短缺资产**（HBM/DRAM/datacenter NAND）。风险：仍强周期、SK Hynix/Samsung 竞争、未来供过于求。
- **$EWY（韩国 ETF）**（战绩名）— 多次用 **$EWY LEAPS 数倍收益**验证韩国 AI memory trade。**收益数字在不同帖子里有 300%+/350%+/428%/485%/5.2x 等多种表述——当方向性战绩，别钉死单一数字。** LEAPS 的真实逻辑是 **vol arbitrage**：做市商把韩国指数 IV 锚在 5–10 年低位，而底层已变成 AI memory 结构性故事——不是单纯方向押注（他还后悔 $ARM 只买了正股，"common shares only tripled"）。
- **Samsung / SK Hynix / $SNDK（x15）** — HBM/DRAM/NAND 链；$SNDK = datacenter NAND pricing。
- **日本/韩国实地研究**：Harmonic Drive(6324)、Towa、Ulvac、NGK、NCI/Rasa/red phosphorus、Auros — 区域供应链 / 材料 / 设备 / 精密制造卡口。

## 第 3 层 — Neocloud / AI compute infra
- **$NBIS / Nebius**（x28，高信念x14）— **最认可的 neocloud 表达**（"Nebius will take care of you"）。看重的不是 power capacity，而是 NVIDIA 相关融资/生态线索、hyperscaler 合同、ARR/guidance、cash/capex、AI Cloud 业务质量。**注意分层**：融资 / 合同 / 合作 / read-through 性质不同，别统称"背书"。
- **$IREN**（x18，**反面案例**：sell x3 / short x2，bearish x8）— **dilution/ATM overhang + retail exit-liquidity 风险**代表。区分"有真实 AI cloud 合同与 economics 的 compute infra" vs "用 AI 叙事包装 power/bitcoin/data-center capacity 的融资故事"。

## 第 3 层 — Power / 800V DC / data-center electrical
从 $NVDA 800V DC 推导。**很多是 watchlist / crowdsourced，不等于推荐——逐名核 buy/add/hold/watchlist。**
- **$HPS.A** — transformer/switchgear bottleneck。
- **$FLNC / Fluence** — hyperscaler power architecture / BESS deal + **float 风险**。
- **$NVTS（x10）/ $POWI / $VICR** — power semi 方向。

## 第 3 层 — Robotics / Physical AI
偏好**高 BOM 价值、替代难的组件**，不是整机叙事："Robotics may be the biggest product category of all time"、"Extremely bullish on robotics/humanoids directionally"。
- **LeaderDrive（688017）** — 中国 humanoid 里**公司层面高 conviction**（reducer/actuator/motor-joint/planetary roller screw 覆盖高）。锚点：国内谐波减速器市占 **>60%**、全球客户 1800+；他估这些部件合计占 humanoid BOM 的 **4–15%**。**但和中国政府/司法风险折价并存**——"喜欢公司位置、给国家风险打折、提醒 design-out/客户验证"。
- **Harmonic Drive(6324)、Sanhua、$VPG（x10）、Unitree、Boston Dynamics、$TSLA Optimus** — actuators/harmonic reducers/planetary roller screws/sensors。
- **$TSLA**（x12，多为 watchlist）— 主要因 Optimus / robotics。

## 第 4 层 — 非 AI-photonics 的高频错配机会
证明他底层方法是"**找市场分类错误 + 资金结构错位 + 未来叙事重估**"，不是只找 CPO。
- **$RDDT** — 平台/数据/社区资产。
- **$CRCL / stablecoins** — 金融基础设施 + 监管催化。
- **$RKLB** — space infrastructure。
- **$INTC（x16）/ $ARM** — semi 架构 + 地缘产业政策（"Optical version of $INTC" 这类类比）。
- **$AEHR（x14）/ Towa** — 测试 / 设备周期。

---

## 反面 / 回避清单（看到这些特征就降权、回避或做空）
- **$IREN**、**$BOT**、**Figure-linked fund**（FIGURE：sell x6 / bearish x7）、**$VCX** — toxic ATM / NAV 溢价 / closed-end 包装 / retail-as-exit-liquidity。
- **$POET** — 谨慎（Marvell/Celestial 取消、可信度受损）。
- **$AAOI 近端** — 长期看好但 $600M ATM 压上行，需 trim / 控集中度。
- **$CRWV**（高息 GPU 融资）、**$SLNH**（$250M 市值 vs $500M ATM）、**$SNAP**（SBC 掩盖盈利能力）、**$BKKT** —— 同一类 toxic 融资结构。
- **MicroLED 全板块** —— "anything MicroLED is a waste of capital for CPO/photonics exposure over the next year"（点名 ams-OSRAM、AUO、Ennostar、Tyntek、PlayNitride）。
- **$PENG** —— chassis/integrator 不是 core IP holder（类比 $SMCI/$DELL）；买它博 photonic memory 的人 "are likely to be disappointed"。
- **$FUTU / $TIGR** —— 明确看空，中国政府/监管风险（"Government can nuke or takeover any business over there on a whim"）。
- **$CBRS** —— 喜欢公司但不买 $90–100B 估值——商业质量 ≠ 买点，这是他少见的"好公司也回避"样本。
- **量子板块** —— 整体太早（商业化 ~2030），"Typically not a good idea to serve as the dilution in the prototyping phases"；他给的关注窗口是 H2 2028 / H1 2029。
- **宏观触发的 trim**：$XLU 因伊朗战争 → 降息概率归零而减仓——他也做利率敏感交易，不只 AI。
- **通用红旗**：只讲 power capacity 不讲真实 AI cloud 合同；logo partnership 只挂名；大额 ATM / 短期 float unlock；封闭基金溢价压制上行。
