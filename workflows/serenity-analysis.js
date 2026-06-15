export const meta = {
  name: 'serenity-analysis',
  description: '用 Serenity (@aleabitoreddit) 的方法论做股票买卖尽调或行业 chokepoint 扫描：六路并行取证 → 证据分层对抗审查 → 量化粗算 → 决策算法裁决 → 他的口吻成稿（长帖 + 底稿双层报告）',
  whenToUse: '想对一只股票做买卖调研、或对一个行业/主题做供应链卡口扫描，并希望结论带证据四层（confirmed/reported/mapped/speculation）与置信度时。args 传 { target: "$SIVE" 或 "CPO 光模块产业链", mode?: "stock"|"industry", maxCandidates?, votes?, out? }，也可直接传字符串当 target。报告默认写到当前目录 serenity_analysis_<slug>.md（agent 沙箱默认只能写 cwd；要写别处请传 out 并放开沙箱）。',
  phases: [
    { title: 'Scope', detail: '解析目标，判定 stock/industry 模式，定位架构语境' },
    { title: 'Map', detail: '（industry 模式）画产业链地图，初筛 chokepoint 候选' },
    { title: 'Research', detail: '每个标的六路并行取证：财务/供应链/资金结构/技术格局/社区传播/政策地缘' },
    { title: 'Verify', detail: '承重事实多票对抗审查：默认怀疑 + 证据层级只降不升' },
    { title: 'Quant', detail: '量化粗算：BOM 拆解/收入 build/历史类比锚/市值错配' },
    { title: 'Verdict', detail: '跑 Serenity 决策算法：chokepoint 三问/反面硬否决/信念分级/仓位计划' },
    { title: 'Synthesize', detail: '跨标的汇总排序，写中文初稿' },
    { title: 'Critique', detail: '对抗审稿：层级注水/漏查反面/多头偏置/假设不明' },
    { title: 'Finalize', detail: '按审稿修订，产出长帖+底稿双层报告并写入文件' },
  ],
}

// ───────────────────────── 参数 ─────────────────────────
// args：{ target（必传）, mode?, maxCandidates?, votes?, maxVerify?, out? }，或直接传字符串当 target
const A = (typeof args === 'string') ? { target: args } : (args || {})
const TARGET = String(A.target || '').trim()
if (!TARGET) {
  return { error: '必须指定调研目标。例：Workflow({ name: "serenity-analysis", args: { target: "$SIVE" } }) 或 args: "CPO 光模块产业链"' }
}
const FORCED_MODE = (A.mode === 'stock' || A.mode === 'industry') ? A.mode : null
const MAX_CANDIDATES = A.maxCandidates || 4
const VOTES = A.votes || 3
const REFUTES = Math.min(VOTES, Math.max(2, Math.ceil(VOTES * 2 / 3)))  // 满票出席时的否决阈值（默认 3 票 2 否决）
const QUORUM = Math.max(1, Math.ceil(VOTES / 2))                        // 法定有效票数；弃权过多=未裁决
const slug = TARGET.replace(/[^A-Za-z0-9一-龥]+/g, '_').replace(/^_+|_+$/g, '').slice(0, 40) || 'target'
const HOME = (typeof process !== 'undefined' && process.env && process.env.HOME) || ''
// 默认写 cwd（Codex agent 默认 sandbox=workspace-write，只能写 cwd 与 $TMPDIR）；用户传 ~ 开头时在 JS 侧展开
const outPath = (A.out || ('serenity_analysis_' + slug + '.md')).replace(/^~(?=\/|$)/, HOME || '~')

// ───────────────────────── 方法论常量（自包含，不依赖外部 skill 文件）─────────────────────────
const PERSONA = `你在执行 X 投资者 Serenity（@aleabitoreddit，bio "Supply Chain Analyst (白毛股神)"）的方法论。核心纪律：

【架构先行】先判断下一代系统怎么变（AI 算力从 GPU 外扩到 optics/CPO/SiPh/HBM/power/cooling/robotics/advanced packaging/materials），再问目标卡在扩散链哪一环；不从当前 EPS 出发。AI 扩散链是他最大主线但不是全部——稳定币/平台/space/消费错配/软件估值错位同样在射程内；统一问法是"下一代系统怎么变、目标卡在哪一环"，不强行归入 AI 链。
【chokepoint 三问】供给紧不紧？替代难不难？市场理解了没有？三者同时成立才是值得高信念的卡口；买卡口，不买整条链。
【证据四层（铁律）】任何"X 是 Y 的供应商/客户/合作方"必须标层：confirmed=公开订单/公司一手披露；reported=券商或产业媒体报道（MS/GS/UDN/Digitimes/TrendForce 类）；mapped=生态相邻/供应链表推断；speculation=推断猜测。pipeline≠orders、qualification≠volume ramp、生态相邻≠量产订单——绝不把低层证据写成 confirmed。
【分类纠错】检查市场是否把它放错类别（integrator vs core IP、optical component vs transceiver、power capacity vs 真实 AI cloud 合同）——错分类=错 multiple，既是机会也是陷阱。
【选择性财报】低配 trailing EPS，高配能证明放量路径的指标：forward guidance、capacity reservation、customer prepayment、volume order、gross margin target、ARR、qualification 进展、capex 节奏。
【机构路径】retail 先发现 → 机构后进入 → 指数/流动性/coverage 兑现（frontrunning the institutions）。看：机构建仓变化、空头比例、指数纳入、NASDAQ/ADR 通道、sell-side 覆盖、内部人买卖。
【地缘供应链战争】AI 硬件重估的大背景是 allied chokepoint weaponization：出口管制、CHIPS Act / EU Chips Act、日/欧/韩/台盟友供应链卡口；西方供应链节点可因 Western supply-chain premium 被美国资本重估。
【市场角色】US=流动性与机构溢价的兑现地；EU/JP/TW/KR=被低估的盟友供应链节点，等美国资金/指数重估；中国资产态度矛盾——公司层面可认可竞争力，国家/司法风险常驻折价，同等卡口宁付 Western supply-chain premium。
【反面筛选（硬否决）】toxic ATM、大额 dilution vs 市值、NAV 溢价、closed-end 包装、logo partnership 只挂名、只讲 power capacity 没有真实合同、把 retail 当 exit liquidity。区分增值型 dilution（为产能/listing/M&A）与掠夺型 dilution（大额 ATM/短期 float unlock）。
【时间桶】每个 thesis 标周期：~6mo / ~2y / 5y+ / too-early（"原型期进场就是去当稀释对象"）。"市场提前 8-12 个月定价"是他的经验规则，不是定律。
【仓位生命周期】小仓试错 → 验证后向上加仓（不是补跌）→ trim 只因假设被证伪（不因价格回撤）→ 让赢家复利、少卖。`

const VOICE = `Serenity 的口吻规则（写"长帖"部分时遵守）：
- 第一人称、叙事式长帖：先讲为什么这个环节重要 → 供应链细节（谁买谁的什么）→ 历史类比（"following the $LITE playbook"式）→ 结论。不用 1/n thread 式分段编号。
- 中文自然口语（说人话，不要翻译腔），ticker 和专有名词保留英文。
- 模仿语气与句式，不逐字抄金句；高频表达（bottleneck / chokepoint / supercycle / frontrunning the institutions / mispriced / "Just a waiting game" / go brrr / lol 软化）每帖自然出现两三个即可，不堆砌。最多一处全大写强调关键判断。不用 emoji。
- 用 return % 当记分牌：引用已验证赢家涨了多少倍来锚定 thesis；强观点后可用 "We'll see if this is right." / "idk" 留余地。
- 强观点 + 免责并存：结尾挂 DYOR / NFA / personal thoughts，但免责不稀释前面的判断；若披露动作（buy/add/avoid）就直说。带自我张力：免责与实际披露的矛盾可以自嘲式点破；承认自己惯性偏早 though directionally right。
- 公开帖藏模型：长帖里只给 high-level 量化结论（"市值 vs 内容价值差一个数量级"），不摆完整推导——推导放底稿。
- 证据分层措辞：confirmed 直说；reported 写"据 MS/UDN 报道"；mapped/speculation 写"我把它映射到/我推断/likely"。绝不把推断写成事实。`

// ───────────────────────── ashare-data-kit 接入 ─────────────────────────
// A 股标的优先走 ashare-data-kit skill 取一手数据；只在判定为 A 股时注入提示，避免污染美股/海外标的
const looksAshare = (...parts) => {
  const s = parts.filter(Boolean).join(' ')
  if (/A\s*股|中国|中國|沪深|沪市|深市|北交所|上海证券交易所|深圳证券交易所|北京证券交易所|\bCN\b|\bSSE\b|\bSZSE\b|\bBSE\b/i.test(s)) return true
  if (/(^|\D)(60|68|00|30|43|83|87|92|90)\d{4}(\D|$)/.test(s)) return true   // 沪 60/68 深 00/30 北/新三板 43/83/87/92/90
  return false
}

// 六路 → ashare-data-kit 七层脚本的定向映射
const ASHARE_LANE_KIT = {
  financials:  'fundamentals(个股信息 info/财务快照 finance/F10/财报三表 report) 取一手财务；reports eps 取机构一致预期 EPS；valuation full 跑综合估值；quotes realtime 取最新价/PE/PB/市值。',
  supplychain: 'reports(list 研报列表 / iwencai NL 语义搜产业链·供应链·客户订单研报)；signals blocks(概念板块归属)；news stock(个股新闻里的供应/订单线索)。',
  ownership:   'capital(margin 融资融券 / holders 股东户数=筹码集中)；signals(northbound 北向沪深股通 / dragon+market-dragon 龙虎榜席位营业部 / fundflow 主力资金流 / lockup 限售解禁日历)。',
  moat:        'signals industry(行业涨跌排名/轮动)；reports(list / iwencai 竞争格局·市占·技术路线研报)；fundamentals f10(主营与竞争地位)。',
  narrative:   'signals(hot 当日强势股+题材归因 / blocks 概念热度)；news(stock 个股新闻 / global 全球资讯)。',
  policy:      'announcements list(巨潮公告全文，取监管/政策/项目一手文件)；news(政策与产业新闻)。',
}

const ashareKitBlock = (kit) => `

## A 股一手数据（本标的为 A 股，重要）
查数据时**优先使用 \`ashare-data-kit\` skill**（A 股全栈数据工具包，七层 uv 可执行脚本，取交易所/公司一手数据，不靠记忆），WebSearch/WebFetch 仅作补充与交叉验证。
- 本路重点用：${kit}
- 用法：直接调用 \`ashare-data-kit\` skill，按其 SKILL.md 命令速查表运行对应脚本（形如 \`uv run scripts/<layer>.py <command> <6位代码> [--json]\`）；不要写死任何绝对路径。
- 证据分层：脚本取到的行情/财报/股东户数/龙虎榜/解禁/融资融券/巨潮公告等公司或交易所一手披露记 confirmed；券商研报/一致预期记 reported；skill 拿不到再退回网络检索。`

// ───────────────────────── Schemas ─────────────────────────
const SCOPE_SCHEMA = {
  type: 'object',
  required: ['mode', 'subjectName', 'architectureContext', 'keyQuestions'],
  properties: {
    mode: { enum: ['stock', 'industry'] },
    subjectName: { type: 'string', description: 'stock 模式=规范化 "TICKER / 公司名（市场）"；industry 模式=主题规范名' },
    market: { type: 'string', description: 'US/EU/TW/JP/KR/CN/HK/global' },
    architectureContext: { type: 'string', description: '它属于哪个下一代架构切换语境，为什么这一环现在重要' },
    keyQuestions: { type: 'array', maxItems: 6, items: { type: 'string' }, description: '本次调研要回答的关键问题' },
    notes: { type: 'string' },
  },
}

const MAP_SCHEMA = {
  type: 'object',
  required: ['segments', 'candidates', 'mapNarrative'],
  properties: {
    mapNarrative: { type: 'string', description: '这条产业链的架构语境与价值流向，2-4 句' },
    segments: {
      type: 'array', maxItems: 12,
      items: {
        type: 'object', required: ['segment', 'role'],
        properties: {
          segment: { type: 'string' },
          role: { type: 'string', description: '该环节在链条里做什么' },
          bottleneckRisk: { enum: ['high', 'medium', 'low'] },
        },
      },
    },
    candidates: {
      type: 'array', maxItems: 10,
      items: {
        type: 'object', required: ['name', 'segment', 'whyChokepoint', 'priority'],
        properties: {
          name: { type: 'string', description: '公司名 + ticker（带市场，如 $SIVE / 3363.TWO / 688017）' },
          ticker: { type: 'string' },
          market: { type: 'string' },
          segment: { type: 'string' },
          whyChokepoint: { type: 'string' },
          supplyTight: { enum: ['yes', 'partly', 'no', 'unknown'] },
          substitutionHard: { enum: ['yes', 'partly', 'no', 'unknown'] },
          marketUnderstands: { enum: ['yes', 'partly', 'no', 'unknown'], description: 'no=市场还没理解（这是好事）' },
          priority: { type: 'integer', description: '1=最值得深挖' },
        },
      },
    },
  },
}

const LANE_SCHEMA = {
  type: 'object',
  required: ['facts', 'laneSummary'],
  properties: {
    laneSummary: { type: 'string', description: '本路取证 2-4 句小结，包括没找到什么' },
    facts: {
      type: 'array', maxItems: 10,
      items: {
        type: 'object', required: ['fact', 'tier', 'direction', 'loadBearing', 'source'],
        properties: {
          fact: { type: 'string', description: '一条可证伪的具体事实/主张，尽量带数字与日期' },
          tier: { enum: ['confirmed', 'reported', 'mapped', 'speculation'] },
          source: { type: 'string', description: 'URL 或出处描述（如 "Q1 FY26 earnings call"）' },
          asOf: { type: 'string', description: '信息时点，YYYY-MM 或具体日期' },
          direction: { enum: ['bullish', 'bearish', 'neutral'] },
          loadBearing: { enum: ['core', 'supporting', 'minor'], description: 'core=thesis 承重墙' },
        },
      },
    },
  },
}

const VERIFY_SCHEMA = {
  type: 'object',
  required: ['refuted', 'tierAfterAudit', 'evidence', 'confidence'],
  properties: {
    refuted: { type: 'boolean' },
    tierAfterAudit: { enum: ['confirmed', 'reported', 'mapped', 'speculation'], description: '审计后这条事实真实配得上的证据层级' },
    evidence: { type: 'string', description: '具体依据，不许空泛' },
    confidence: { enum: ['high', 'medium', 'low'] },
    counterSource: { type: 'string', description: '反驳/限定它的来源 URL（如有）' },
  },
}

const QUANT_SCHEMA = {
  type: 'object',
  required: ['models', 'overallRead', 'marketCapContext'],
  properties: {
    marketCapContext: { type: 'string', description: '当前市值/估值水位与对照；若有指数纳入事件，含强制被动买盘 vs 流通盘/空头的挤压算术' },
    models: {
      type: 'array', maxItems: 4,
      items: {
        type: 'object', required: ['method', 'assumptions', 'result'],
        properties: {
          method: { enum: ['bom-build', 'revenue-build', 'historical-analog', 'mcap-mismatch'] },
          assumptions: { type: 'array', items: { type: 'string' }, description: '每条假设显式列出，并标注依据的证据层级与是否经过对抗审查' },
          result: { type: 'string', description: '数量级结论，分 bear/base/bull 情景' },
          sensitivity: { type: 'string', description: '哪条假设最脆弱' },
        },
      },
    },
    overallRead: { enum: ['deeply-undervalued', 'undervalued', 'fair', 'expensive', 'uninvestable', 'cannot-model'] },
    modelNote: { type: 'string', description: '模型整体可信度：建立在多少 reported/mapped/speculation 级或未审（verified=false）假设上' },
  },
}

const VERDICT_SCHEMA = {
  type: 'object',
  required: ['chokepointTest', 'negativeScreens', 'convictionGrade', 'action', 'timeBucket', 'bullCase', 'bearCase', 'whatWouldChangeMyMind', 'oneLiner', 'classificationCheck', 'institutionsPath', 'positionPlan', 'catalysts'],
  properties: {
    oneLiner: { type: 'string', description: 'Serenity 式一句话定位：它卡在哪个环节' },
    architecturePosition: { type: 'string' },
    classificationCheck: { type: 'string', description: '市场把它放对类别了吗？错在哪、意味着什么' },
    chokepointTest: {
      type: 'object', required: ['supplyTight', 'substitutionHard', 'marketUnderstands', 'isChokepoint'],
      properties: {
        supplyTight: { enum: ['yes', 'partly', 'no', 'unknown'] },
        substitutionHard: { enum: ['yes', 'partly', 'no', 'unknown'] },
        marketUnderstands: { enum: ['yes', 'partly', 'no', 'unknown'] },
        isChokepoint: { type: 'boolean' },
        note: { type: 'string' },
      },
    },
    institutionsPath: { type: 'string', description: '机构资金进入路径走到哪一步（retail 发现→机构建仓→指数/coverage）' },
    negativeScreens: {
      type: 'object', required: ['vetoed', 'dilutionType'],
      properties: {
        vetoed: { type: 'boolean', description: '触发 PERSONA 反面筛选清单中任一硬否决项=true（toxic ATM/大额 dilution vs 市值/NAV 溢价/closed-end 包装/logo partnership/只讲 power capacity 没真实合同/retail exit liquidity）' },
        dilutionType: { enum: ['none', 'accretive', 'predatory', 'unknown'] },
        redFlags: { type: 'array', items: { type: 'string' } },
      },
    },
    convictionGrade: { enum: ['high-conviction', 'research-thesis', 'watchlist', 'info-only', 'avoid'] },
    action: { enum: ['buy', 'add', 'hold', 'trim', 'avoid', 'short', 'watch'] },
    timeBucket: { enum: ['~6mo', '~2y', '5y+', 'too-early'] },
    positionPlan: { type: 'string', description: '按仓位生命周期写：试错仓条件→验证后加仓触发→trim 触发（假设证伪）' },
    catalysts: { type: 'array', items: { type: 'string' }, description: '每条标类型：财务/政策/资金/传播，尽量带预期时点' },
    bullCase: { type: 'string' },
    bearCase: { type: 'string' },
    whatWouldChangeMyMind: { type: 'string' },
  },
}

const CRITIQUE_SCHEMA = {
  type: 'object',
  required: ['coverageVerdict'],
  properties: {
    tierInflation: { type: 'array', items: { type: 'string' }, description: '初稿里把低层证据写成高层确定性的地方（含 unverified 当 verified 用、引用 killed 叙事）' },
    missingNegativeScreens: { type: 'array', items: { type: 'string' }, description: '没查或没写的反面筛选项（float/ATM/SBC/NAV…）' },
    vetoConsistency: { type: 'array', items: { type: 'string' }, description: 'vetoed=true 的标的初稿是否仍给出 buy/add 或高信念措辞' },
    bullBias: { type: 'array', items: { type: 'string' }, description: '只组装多头证据、bear case 缺席或敷衍、结论与 bearish 事实不符的地方' },
    unstatedAssumptions: { type: 'array', items: { type: 'string' } },
    staleOrUnverifiedData: { type: 'array', items: { type: 'string' }, description: '数据时点缺失/过期/未经核实却当事实用的地方' },
    missingThemes: { type: 'array', items: { type: 'string' } },
    coverageVerdict: { enum: ['ok', 'needs-revision'] },
    suggestions: { type: 'array', items: { type: 'string' } },
  },
}

// ───────────────────────── 六路取证定义 ─────────────────────────
const LANES = [
  { key: 'financials', title: '财务与 filings', brief: '最新财报与 guidance、产能预订/客户预付款/volume orders、ATM/shelf/可转债/float 结构、SBC、现金跑道、毛利目标。优先公司一手披露（IR/filings/transcript），引用 transcript 尽量带出处。这一路必须明确回答：有没有 toxic 融资结构（这是硬否决项）。' },
  { key: 'supplychain', title: '供应链与产业报道', brief: '券商 supplier note（MS/GS 类）、UDN/Digitimes/TrendForce 类产业媒体、客户/订单线索、qualification 与量产进展、产能与交期。rumor 必须标 reported 或更低，注意区分 development contract 与 volume order。' },
  { key: 'ownership', title: '股权与资金结构', brief: '机构持仓变化（13F/大额持股披露）、空头比例与变化、主要做空机构及其盈亏（空头结构是 squeeze 燃料）、托管行流向（float 被谁拿走）、指数纳入/剔除（已宣布或可预期的，带回指数权重与流通盘数据，供量化阶段测算强制被动买盘）、NASDAQ/ADR/双重上市通道、sell-side 覆盖变化、内部人买卖。这一路回答"机构路径走到哪一步"。' },
  { key: 'moat', title: '技术与竞争格局', brief: '它在架构扩散链的位置、替代方案与多供方风险、sole-source 可能性（供应商列表变更类证据最有力）、市场是否错误分类（integrator vs core IP 等）、design-out 风险。' },
  { key: 'narrative', title: '社区与传播', brief: 'X/Reddit/媒体上的关注度与叙事、是否被大 V（含 @aleabitoreddit 本人）讨论过（若他谈过，引用其真实表态并标 reported）、媒体唱多/唱空、retail 拥挤度与 "Serenity effect" 式反身性风险。' },
  { key: 'policy', title: '政策与地缘一手文件', brief: '政府与监管一手文件：CHIPS Act / EU Chips Act 申请与项目文件（注意公司可能换名出现在项目文件里）、NIST/白宫 fact sheet、出口管制清单与技术封锁、补贴与产业政策；该环节在盟友供应链战争中的位置（allied chokepoint / Western supply-chain premium）、中国暴露与司法/政策折价。' },
]

const tierRank = { confirmed: 0, reported: 1, mapped: 2, speculation: 3 }
const tierNames = ['confirmed', 'reported', 'mapped', 'speculation']
const lbRank = { core: 0, supporting: 1, minor: 2 }

// ───────────────────────── Prompt 构造器 ─────────────────────────
const lanePrompt = (subj, lane) =>
  PERSONA + `

## 取证任务：${lane.title}
调研对象：${subj.name}（${subj.market || '市场未知'}）
架构语境：${subj.context}
${subj.whyChokepoint ? '初筛理由：' + subj.whyChokepoint + '\n' : ''}
本路范围：${lane.brief}

## 要求
1. 用 WebSearch / WebFetch 实际检索，不许凭记忆编数字。优先一手来源（filings/IR/官方公告），其次券商与产业媒体。
2. 产出最多 10 条可证伪的具体事实（facts），每条：
   - tier 按证据四层诚实标注——查不到一手确认的供应关系一律 mapped 或 speculation；
   - 带 source（URL 或明确出处）与 asOf（信息时点）；
   - direction 标 bullish/bearish/neutral；loadBearing 标 core/supporting/minor。
3. 多空都要找：至少 2 条 bearish 方向的事实；实在找不到就在 laneSummary 里明说"未找到看空证据"及原因。
4. 查不到的就说查不到，不要编。结构化返回。` +
  (subj.ashare ? ashareKitBlock(ASHARE_LANE_KIT[lane.key] || '按需调用对应 layer 脚本取一手数据。') : '')

const verifyPrompt = (subj, f, v) =>
  `## 对抗式事实审查员（第 ${v + 1}/${VOTES} 票）——默认怀疑，满票出席时 ≥${REFUTES}/${VOTES} 票否决即剔除（有人弃权时阈值按有效票等比缩放）

调研对象：${subj.name}
待审事实："${f.fact}"
申报层级：${f.tier}　来源：${f.source}　时点：${f.asOf || '未标'}　方向：${f.direction}

## 审查清单（Serenity 证据纪律版）
1. 来源真的支持这条陈述吗？还是过度引申/误读？用 WebFetch 核对原文。
2. WebSearch 找反证：有没有可信来源反驳或重大限定它？
3. 【层级审计】这条申报的 tier 配得上证据吗？pipeline≠orders、qualification≠volume ramp、生态相邻≠量产订单、"据报道"≠公司披露。给出 tierAfterAudit（审计后真实层级，只许持平或降级，不许升级）。
4. 过期了吗？快速变化的领域里旧信息要打折（对照 asOf）。
5. 是不是 marketing 稿/PR/拉抬性内容/论坛猜测？
${subj.ashare ? '6. 【A 股复核】若本事实涉及可由 `ashare-data-kit` skill 直接取数的 A 股数据（行情/财报/股东户数/龙虎榜/解禁/融资融券/巨潮公告/一致预期），优先用该 skill 重新取数核对原始口径，而非仅凭网页。\n' : ''}
refuted=true 当：来源不支持 / 被可信反证推翻 / 来源质量撑不起陈述强度 / 严重过期 / 营销水分。
refuted=false 仅当：陈述有据、时效可用、层级（按审计后）匹配。不确定时默认 refuted=true。
evidence 必须具体。结构化返回。`

const quantPrompt = (subj, facts) =>
  PERSONA + `

## 量化粗算：${subj.name}
取证事实（verified=true 已通过对抗审查；verified=false 未送审，一律按未核实对待）：
${JSON.stringify(facts.map((f) => ({ fact: f.fact, tier: f.finalTier, asOf: f.asOf, direction: f.direction, verified: f.verified })))}

## 任务
他自述 "I do my own valuation work and forward P/E modeling for every long position"。从四件套里挑【适用的】方法建粗模（不适用的不要硬套）：
- bom-build：单机/单系统价值量 × 出货量 × 市占 haircut → 收入 → forward P/E 情景；
- revenue-build：按产品线逐项加总（参照公司 guidance/产能口径）；
- historical-analog：找已验证赢家的重估路径做锚（"the next $LITE"式——同链位、同放量曲线才可比）；
- mcap-mismatch：上游卡口市值 vs 整条下游对它的依赖度。
要求：
1. 先 WebSearch 当前市值/股本/估值水位（不许凭记忆）；若存在指数纳入事件/预期，测算强制被动买盘金额并对照流通盘与空头比例给出挤压空间（他 $SIVE 式的标准算术），并入 marketCapContext 或 mcap-mismatch。
2. 每条假设显式写出，并标注它建立在哪个证据层级上；建立在 verified=false 或 mapped/speculation 事实上的假设必须在 modelNote 里自首。
3. 结果分 bear/base/bull 情景给数量级；指出最脆弱的假设。结构化返回。` +
  (subj.ashare ? `

## A 股估值数据（本标的为 A 股）
市值/股本/PE/PB/估值水位优先用 \`ashare-data-kit\` skill：quotes realtime(最新价/PE/PB/总市值/流通市值/涨跌停)、valuation full(前向 PE/PEG/PE 消化公式)、reports eps(机构一致预期 EPS)、capital holders(股东户数辅助流通盘判断)；不要写死绝对路径，WebSearch 仅补充。` : '')

const verdictPrompt = (subj, facts, killed, quant) =>
  PERSONA + `

## 最终裁决：${subj.name}
架构语境：${subj.context}

A) 存活事实（含层级/方向/时点；verified=false 表示未送审、按未核实对待，任何核心结论不得仅由它承重）：
${JSON.stringify(facts.map((f) => ({ fact: f.fact, tier: f.finalTier, direction: f.direction, loadBearing: f.loadBearing, asOf: f.asOf, verified: f.verified, vote: f.vote })))}

B) 被对抗审查否决的事实（不许再使用，仅供了解哪些叙事是空的）：
${JSON.stringify(killed.map((f) => ({ fact: f.fact, why: f.killReason })))}

C) 量化粗算结果：
${JSON.stringify(quant || { note: '量化步骤失败或不适用' })}

## 任务：按顺序跑完决策算法，结构化返回
1. 架构定位 → 2. chokepoint 三问（基于 A 里的证据回答，不许臆测）→ 3. 分类纠错 → 4. 机构路径走到哪一步 → 5. 反面筛选（触发硬否决项时 vetoed=true，且 action 只能 avoid/short，无论 bull case 多好）→ 6. 信念分级（诚实：核心证据多为 mapped/speculation 或未核实时，最高只能给 research-thesis 或 watchlist，不许给 high-conviction）→ 7. 时间桶 → 8. 仓位计划（生命周期式：什么条件开试错仓、什么验证信号加仓、什么假设证伪就 trim）→ 9. bull/bear case 都要实质成段 → 10. whatWouldChangeMyMind 必须具体可观察。`

const draftPrompt = (scope, mapInfo, results) =>
  PERSONA + `

## 写初稿：${TARGET}（${scope.mode === 'industry' ? '行业 chokepoint 扫描' : '个股买卖尽调'}）
架构语境：${scope.architectureContext}
关键问题：${JSON.stringify(scope.keyQuestions)}
${mapInfo ? '产业链地图：' + JSON.stringify(mapInfo) + '\n' : ''}
各标的完整裁决材料（事实带证据层级与时点；killed=被对抗审查否决的叙事）：
${JSON.stringify(results)}

## 要求（中文，说人话，ticker/术语保留英文）
1. ${scope.mode === 'industry'
    ? '先给产业链地图与价值流向；再按 convictionGrade 与 chokepoint 成色对候选排序；每个候选一节：一句话定位、证据分层后的核心事实、量化粗算数量级、裁决（信念分级/action/时间桶/仓位计划）、bear case 与红旗。'
    : '单票深挖：一句话定位 → 分类纠错 → chokepoint 三问 → 证据分层后的事实地图（confirmed/reported/mapped/speculation 分开写，措辞对应"已确认/据报道/我映射到/我推断"）→ 量化粗算 → 机构路径 → 反面筛选结果 → 裁决（信念分级/action/时间桶/仓位计划/催化剂日历）→ bear case → whatWouldChangeMyMind。'}
2. 每个结论都要能回溯到带层级的事实；被 killed 的叙事如果市场上流行，要点名澄清（"这条传闻没过审查"）。
3. 【未核实标注（硬约束）】verified=false 的事实必须显式标"【未过对抗审查】"，措辞最高只能用"据称/未核实"；任何核心结论不得仅由 unverified 事实承重。
4. 多空平衡：bear case 和红旗必须实质成段，不许一句带过。
5. 局限一节：哪些路取证失败、哪些事实没进对抗审查（unverified/no-quorum）、行业模式下哪些候选没深挖。
输出 Markdown 初稿全文。`

const critiquePrompt = (draft, results) =>
  `你是对抗式审稿人，按 Serenity 的纪律审这份调研初稿。

<draft>
${draft}
</draft>

底层裁决材料（事实带层级/方向/时点/来源；killed=已被否决的叙事）：
${JSON.stringify(results.map((r) => ({
    name: r.name,
    facts: r.facts.map((f) => ({ fact: f.fact, tier: f.tier, verified: f.verified, direction: f.direction, loadBearing: f.loadBearing, asOf: f.asOf, source: f.source })),
    killed: r.killed.map((f) => f.fact),
    vetoed: r.verdict && r.verdict.negativeScreens ? r.verdict.negativeScreens.vetoed : null,
    convictionGrade: r.verdict ? r.verdict.convictionGrade : null,
    action: r.verdict ? r.verdict.action : null,
  })))}

逐项严查：
- tierInflation：初稿措辞确定性超过事实层级的地方（mapped/speculation 被写成事实、reported 没标"据报道"、unverified 没标"未核实"、用了 killed 的叙事）；
- missingNegativeScreens：float/ATM/SBC/NAV 溢价/客户集中/design-out 哪些没查或没写；
- vetoConsistency：vetoed=true 的标的，初稿是否仍给出 buy/add 或高信念措辞；
- bullBias：bear case 缺席、敷衍、或结论与 bearish 方向事实不符的地方；
- unstatedAssumptions：量化粗算里没写出来的假设；
- staleOrUnverifiedData：缺时点、过期、或 unverified 事实被当 verified 用的地方；
- missingThemes：材料里有但初稿漏掉的重要线索。
给 coverageVerdict（ok / needs-revision）与具体 suggestions。结构化返回。`

const finalizePrompt = (draft, critique, modeStr, materials) =>
  VOICE + `

## 定稿：${TARGET}
初稿：
${draft}

审稿意见（JSON）：
${JSON.stringify(critique)}

底层材料（底稿的证据分层表与被否决清单必须直接由这份材料生成，不得只转写初稿）：
${JSON.stringify(materials)}

## 任务
1. 按审稿意见修订：压回 tierInflation、补 missingNegativeScreens、补实 bear case、写明假设与数据时点；好的部分保留。
2. 产出双层文档（中文，结构如下）：
   - 头信息：目标 ${TARGET}、模式 ${modeStr}、生成日期（运行 \`date +%F\` 取）、数据时点窗口说明、两行免责：本文是 Serenity (@aleabitoreddit) 方法论与口吻的模拟产物，非本人观点；NFA/DYOR，不构成投资建议。
   - 【第一部分：长帖】按上面的口吻规则，写成像他本人发的长帖——藏模型、强观点+免责、证据分层措辞。
   - 【第二部分：分析底稿】亮模型：证据分层表（confirmed/reported/mapped/speculation 分组，每条带来源与时点，verified=false 标"未过对抗审查"）、被否决叙事的透明清单（带否决理由）、量化粗算（假设/情景/敏感性）、决策算法逐步结论、仓位计划、催化剂日历、读法四问自测（high conviction 还是 watchlist？证据层级？催化剂类型？thesis 延后 12-24 个月撑得住吗？）、局限。
3. 用 shell 把最终 Markdown 写入文件：${outPath}（相对路径=当前工作目录；例如 cat > 文件 <<'EOF' … EOF）。若因权限/沙箱写入失败，不要中断：在回复的第一行单独写 FILE_WRITE_FAILED，然后继续。
4. 把最终 Markdown 全文作为回复返回（不要只给摘要）。`

// ───────────────────────── Phase 1：Scope ─────────────────────────
phase('Scope')
const scope = await agent(
  PERSONA + `

## 解析调研目标
用户给的目标：${TARGET}
${FORCED_MODE ? '用户已指定模式：' + FORCED_MODE + '（mode 直接用它）' : '判定模式：单一公司/股票 → stock；行业/主题/产业链 → industry。'}

任务：可先用 WebSearch 确认目标所指（ticker 歧义、公司全名、所在市场）。若疑似 A 股（6 位代码 / 中国大陆上市），直接用 \`ashare-data-kit\` skill 的 quotes realtime 确认代码、简称、所属市场与当前市值（不写死绝对路径），并把 market 标为 CN。返回：mode、subjectName（规范化）、market、architectureContext（它属于哪个下一代架构切换语境、为什么这一环现在重要）、keyQuestions（本次调研要回答的 3-6 个关键问题，按他的方法论出题：卡口在哪/证据到哪层/资金结构干不干净/机构路径/估值数量级）。结构化返回。`,
  { label: 'scope', phase: 'Scope', schema: SCOPE_SCHEMA }
)
if (!scope) {
  return { error: 'Scope 失败：无法解析调研目标 "' + TARGET + '"。请重试或换更明确的写法（如带 ticker 或市场）。' }
}
const MODE = FORCED_MODE || scope.mode
const MAX_VERIFY = A.maxVerify || (MODE === 'industry' ? 8 : 12)   // 每个标的送审的承重事实上限（core 超限时自动上调）
log(`目标：${scope.subjectName}（${MODE} 模式）；架构语境：${String(scope.architectureContext).slice(0, 80)}…`)

// ───────────────────────── Phase 2：Map（industry 模式）─────────────────────────
let subjects = []
let mapInfo = null
let droppedCandidates = []
if (MODE === 'industry') {
  phase('Map')
  const map = await agent(
    PERSONA + `

## 产业链 chokepoint 地图：${scope.subjectName}
架构语境：${scope.architectureContext}

任务：
0. 若这条链是中国 A 股产业链，用 \`ashare-data-kit\` skill 辅助拆链与初筛：signals(industry 行业排名/轮动、hot 题材归因、blocks 板块归属)、reports(iwencai NL 搜产业链研报)；候选 ticker 用 6 位代码、market 标 CN（不写死绝对路径）。
1. 用 WebSearch 把这条链按环节拆开（segments）：上游材料/设备 → 关键部件 → 制造/封装 → 集成 → 终端需求，每环标 bottleneckRisk。
2. 找 chokepoint 候选（candidates，最多 10 个）：对每个候选预答 chokepoint 三问。他的偏好排序：供给紧+替代难+市场没懂 > 小中盘 > 非美但有美国资金可达路径（NASDAQ/ADR/指数纳入空间）；中国标的需显式标注司法/政策折价；纯 integrator、纯 logo-partnership 故事、明显 toxic 融资结构的直接降权。
3. priority 从 1 开始排，给出 mapNarrative。结构化返回。`,
    { label: 'map:' + slug.slice(0, 24), phase: 'Map', schema: MAP_SCHEMA }
  )
  if (!map || !map.candidates || !map.candidates.length) {
    return { error: 'Map 失败：没拿到 chokepoint 候选。可改用 mode:"stock" 直接调研具体标的，或换更具体的行业表述。' }
  }
  const sorted = [...map.candidates].sort((a, b) => (a.priority || 99) - (b.priority || 99))
  const picked = sorted.slice(0, MAX_CANDIDATES)
  droppedCandidates = sorted.slice(MAX_CANDIDATES).map((c) => c.name)
  mapInfo = { mapNarrative: map.mapNarrative, segments: map.segments, allCandidates: sorted.map((c) => ({ name: c.name, segment: c.segment, priority: c.priority })) }
  subjects = picked.map((c) => ({
    name: c.name, market: c.market || '', context: scope.architectureContext + '；链位：' + (c.segment || ''),
    whyChokepoint: c.whyChokepoint, short: String(c.ticker || c.name).replace(/[^A-Za-z0-9.$一-龥]+/g, '').slice(0, 16),
    ashare: looksAshare(c.market, c.name, c.ticker),
  }))
  log(`产业链 ${map.segments.length} 环；候选 ${sorted.length} 个，深挖 Top ${picked.length}：${picked.map((c) => c.name).join('、')}${droppedCandidates.length ? `；未深挖 ${droppedCandidates.length} 个（列入报告局限）` : ''}`)
} else {
  subjects = [{
    name: scope.subjectName, market: scope.market || '', context: scope.architectureContext,
    whyChokepoint: '', short: String(scope.subjectName).replace(/[^A-Za-z0-9.$一-龥]+/g, '').slice(0, 16),
    ashare: looksAshare(scope.market, scope.subjectName, TARGET),
  }]
}

// ───────────────────────── Phase 3-6：每个标的的流水线（Research → Verify → Quant → Verdict）─────────────────────────
// pipeline：标的之间无 barrier——A 在 Verify 时 B 可以还在 Research
phase('Research')
const subjectResults = await pipeline(
  subjects,

  // Stage 1：六路并行取证（标的内 barrier 是必要的——Verify 要全量事实排序）
  async (subj) => {
    const laneOut = await parallel(
      LANES.map((lane) => () =>
        agent(lanePrompt(subj, lane), { label: `research:${subj.short}:${lane.key}`, phase: 'Research', schema: LANE_SCHEMA })
          .then((r) => (r ? { lane: lane.key, laneTitle: lane.title, ...r } : null))
      )
    )
    const lanes = laneOut.filter(Boolean)
    const failedLanes = LANES.filter((l, i) => !laneOut[i]).map((l) => l.title)
    const facts = lanes.flatMap((l) => (l.facts || []).map((f) => ({ ...f, lane: l.lane })))
    log(`${subj.name}：${lanes.length}/${LANES.length} 路取证成功，${facts.length} 条事实${failedLanes.length ? `（失败：${failedLanes.join('、')}）` : ''}`)
    if (!facts.length) return { subj, facts: [], killed: [], failedLanes, laneSummaries: [], failed: true }
    return { subj, facts, failedLanes, laneSummaries: lanes.map((l) => ({ lane: l.laneTitle, summary: l.laneSummary })) }
  },

  // Stage 2：承重事实对抗审查（多票、默认怀疑、层级只降不升、core 全审）
  async (st) => {
    if (st.failed) return st
    const { subj } = st
    const ranked = [...st.facts].sort((a, b) =>
      (lbRank[a.loadBearing] - lbRank[b.loadBearing]) || (tierRank[a.tier] - tierRank[b.tier])
    )
    // 跨路去重：相同 fact+source 只送审一次、只计数一次
    const seenFact = new Set()
    const deduped = ranked.filter((f) => {
      const k = f.fact + '|' + f.source
      if (seenFact.has(k)) return false
      seenFact.add(k)
      return true
    })
    if (deduped.length < ranked.length) log(`${subj.name}：去重 ${ranked.length - deduped.length} 条跨路重复事实`)
    // core 事实全部送审（ranked 已 core 优先，core 超限时上调上限）
    const coreCount = deduped.filter((f) => f.loadBearing === 'core').length
    const cap = Math.max(MAX_VERIFY, coreCount)
    if (cap > MAX_VERIFY) log(`${subj.name}：core 事实 ${coreCount} 条超出送审上限 ${MAX_VERIFY}，上调为 core 全审`)
    const toVerify = deduped.slice(0, cap)
    const rest = deduped.slice(cap)
    const voted = (await parallel(
      toVerify.map((f) => () =>
        parallel(
          Array.from({ length: VOTES }, (_, v) => () =>
            agent(verifyPrompt(subj, f, v), {
              label: `verify:${subj.short}:${String(f.fact).slice(0, 28)}`, phase: 'Verify', schema: VERIFY_SCHEMA,
            })
          )
        ).then((verdicts) => {
          const valid = verdicts.filter(Boolean)                        // null 票=弃权
          const refuted = valid.filter((v) => v.refuted).length
          const quorum = valid.length >= QUORUM
          const killAt = Math.max(1, Math.ceil(valid.length * 2 / 3))   // 否决阈值按实际有效票等比缩放
          const survives = quorum && refuted < killAt
          // 层级聚合用全部有效票（含否决票的层级意见）——只降不升，取最保守
          const auditTiers = valid.map((v) => tierRank[v.tierAfterAudit] ?? tierRank[f.tier])
          const appliedTier = tierNames[Math.max(tierRank[f.tier], ...(auditTiers.length ? auditTiers : [tierRank[f.tier]]))]
          log(`${subj.short} "${String(f.fact).slice(0, 40)}…"：${valid.length - refuted}-${refuted}${valid.length < VOTES ? `（${VOTES - valid.length} 弃权）` : ''} ${survives ? '✓' : quorum ? '✗' : '?'}${appliedTier !== f.tier ? ` 层级 ${f.tier}→${appliedTier}` : ''}`)
          if (!quorum) return { ...f, finalTier: appliedTier, verified: false, survives: true, vote: `no-quorum(${valid.length - refuted}-${refuted})` }
          if (!survives) {
            const why = valid.filter((v) => v.refuted).map((v) => v.evidence).join('；').slice(0, 200)
            return { ...f, finalTier: appliedTier, verified: true, survives: false, vote: `${valid.length - refuted}-${refuted}`, killReason: why }
          }
          return { ...f, finalTier: appliedTier, verified: true, survives: true, vote: `${valid.length - refuted}-${refuted}` }
        })
      )
    )).filter(Boolean)
    const survivors = voted.filter((f) => f.survives)
    const killed = voted.filter((f) => !f.survives)
    const unverified = rest.map((f) => ({ ...f, finalTier: f.tier, verified: false, survives: true }))
    log(`${subj.name}：审查 ${voted.length} 条 → 存活 ${survivors.length}、否决 ${killed.length}；另 ${unverified.length} 条未送审（标 unverified）`)
    return { ...st, facts: [...survivors, ...unverified], killed }
  },

  // Stage 3：量化粗算
  async (st) => {
    if (st.failed) return st
    const quant = await agent(quantPrompt(st.subj, st.facts), {
      label: `quant:${st.subj.short}`, phase: 'Quant', schema: QUANT_SCHEMA,
    })
    if (!quant) log(`${st.subj.name}：量化粗算失败，裁决阶段按无模型处理`)
    return { ...st, quant }
  },

  // Stage 4：Serenity 决策算法裁决（含代码守卫：硬否决与信念分级不是软约束）
  async (st) => {
    if (st.failed) return st
    const verdict = await agent(verdictPrompt(st.subj, st.facts, st.killed, st.quant), {
      label: `verdict:${st.subj.short}`, phase: 'Verdict', schema: VERDICT_SCHEMA,
    })
    if (verdict) {
      if (verdict.negativeScreens && verdict.negativeScreens.vetoed && !['avoid', 'short'].includes(verdict.action)) {
        log(`${st.subj.name}：触发硬否决但 action=${verdict.action}，代码守卫覆盖为 avoid`)
        verdict.action = 'avoid'
      }
      const cores = st.facts.filter((f) => f.loadBearing === 'core')
      const weakCores = cores.filter((f) => !f.verified || f.finalTier === 'mapped' || f.finalTier === 'speculation')
      if (verdict.convictionGrade === 'high-conviction' && cores.length && weakCores.length * 2 > cores.length) {
        log(`${st.subj.name}：核心证据过半为 mapped/speculation/未核实，high-conviction 降为 research-thesis`)
        verdict.convictionGrade = 'research-thesis'
      }
      log(`${st.subj.name}：${verdict.convictionGrade} / ${verdict.action} / ${verdict.timeBucket}${verdict.negativeScreens && verdict.negativeScreens.vetoed ? '（触发硬否决）' : ''}`)
    }
    return { ...st, verdict }
  }
)

const results = subjectResults.filter(Boolean).filter((r) => !r.failed && r.verdict).map((r) => ({
  name: r.subj.name, market: r.subj.market,
  laneSummaries: r.laneSummaries, failedLanes: r.failedLanes,
  facts: r.facts.map((f) => ({ fact: f.fact, tier: f.finalTier, direction: f.direction, loadBearing: f.loadBearing, source: f.source, asOf: f.asOf, verified: f.verified, vote: f.vote, lane: f.lane })),
  killed: (r.killed || []).map((f) => ({ fact: f.fact, vote: f.vote, killReason: f.killReason })),
  quant: r.quant, verdict: r.verdict,
}))
// 按下标恢复失败标的（pipeline 保序；stage 真 throw 时该项变 null，不能用 filter(Boolean) 推断）
const failedSubjects = subjects.filter((s, i) => {
  const r = subjectResults[i]
  return !r || r.failed || !r.verdict
}).map((s) => s.name)
if (!results.length) {
  return { error: '所有标的的取证/裁决流水线都失败了，无法成稿。', failedSubjects, scope }
}
log(`流水线完成：${results.length}/${subjects.length} 个标的拿到完整裁决${failedSubjects.length ? `；失败：${failedSubjects.join('、')}` : ''}`)

// ───────────────────────── Phase 7-9：Synthesize → Critique → Finalize ─────────────────────────
phase('Synthesize')
const draft = await agent(draftPrompt({ ...scope, mode: MODE }, mapInfo ? { ...mapInfo, droppedCandidates, failedSubjects } : null, results), {
  label: 'synthesis-draft', phase: 'Synthesize',
})
if (!draft) {
  // 初稿失败：把结构化裁决原样返回，不让整次运行作废
  return {
    error: '初稿综合失败——返回各标的的结构化裁决供直接使用。',
    target: TARGET, mode: MODE, scope, mapInfo, results, failedSubjects,
  }
}

phase('Critique')
const critique = await agent(critiquePrompt(draft, results), { label: 'adversarial-critic', phase: 'Critique', schema: CRITIQUE_SCHEMA })
if (critique) {
  log(`审稿：${critique.coverageVerdict}；层级注水 ${(critique.tierInflation || []).length}、漏查反面 ${(critique.missingNegativeScreens || []).length}、多头偏置 ${(critique.bullBias || []).length}、否决不一致 ${(critique.vetoConsistency || []).length}`)
} else {
  log('审稿失败——按无修改意见定稿（报告里会注明未经对抗审稿）')
}

phase('Finalize')
const finalDoc = await agent(
  finalizePrompt(
    draft,
    critique || { coverageVerdict: 'critic-failed', suggestions: ['对抗审稿失败，请在文档头注明本稿未经审稿环节'] },
    MODE,
    results
  ),
  { label: 'finalize', phase: 'Finalize' }
)

const allStates = subjectResults.filter(Boolean)
const stats = {
  mode: MODE,
  subjects: subjects.length,
  subjectsCompleted: results.length,
  factsCollected: allStates.reduce((n, r) => n + (r.facts ? r.facts.length : 0) + (r.killed ? r.killed.length : 0), 0),
  factsKilled: allStates.reduce((n, r) => n + (r.killed ? r.killed.length : 0), 0),
  factsUnverified: allStates.reduce((n, r) => n + (r.facts ? r.facts.filter((f) => !f.verified && !String(f.vote || '').startsWith('no-quorum')).length : 0), 0),
  factsNoQuorum: allStates.reduce((n, r) => n + (r.facts ? r.facts.filter((f) => String(f.vote || '').startsWith('no-quorum')).length : 0), 0),
  droppedCandidates: droppedCandidates.length,
  votesPerFact: VOTES,
}
const fileWritten = !!finalDoc && !String(finalDoc).trimStart().startsWith('FILE_WRITE_FAILED')
log(`完成。${finalDoc ? (fileWritten ? `报告：${outPath}` : '⚠️ 报告文件写入失败（FILE_WRITE_FAILED），全文在返回值 report 字段') : '定稿失败'}；事实 ${stats.factsCollected} 条（否决 ${stats.factsKilled}、未送审 ${stats.factsUnverified}、未达法定票数 ${stats.factsNoQuorum}）`)

if (!finalDoc) {
  return { error: '定稿失败——返回初稿与审稿意见。', target: TARGET, file: null, draft, critique, results, stats }
}
return {
  target: TARGET, mode: MODE, file: fileWritten ? outPath : null, report: finalDoc,
  verdicts: results.map((r) => ({ name: r.name, oneLiner: r.verdict.oneLiner, convictionGrade: r.verdict.convictionGrade, action: r.verdict.action, timeBucket: r.verdict.timeBucket, vetoed: r.verdict.negativeScreens ? r.verdict.negativeScreens.vetoed : null })),
  stats,
}
