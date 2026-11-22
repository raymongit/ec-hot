// 这个行业的分类体系：类别、标签词表、平台/公司（主体）名录，以及防止张冠李戴的身份词典。
// 模型按这里的词表打标签，主题页（topics.json）按标签归类，筛选栏按类别分组。
// 换行业时：类别的 key 会出现在网址里（/all?category=…），上线后就不要再改；标签和名录可以随时增减。

/**
 * 网页上的类别（筛选栏、卡片角标、RSS 分类订阅）。key 是网址和接口里的身份，上线后不要改。
 * section 是日报里的分节标题（几个类别可以共用一节，按这里的顺序排）；guide 告诉结构抽取模型这一类收什么、
 * 和相邻类别的边界在哪（总的归类原则写在 prompts/structure.md 里）。
 * tagColor 是飞书推送卡片里跟在标题后面的这一类小标签的颜色（飞书 text_tag 的颜色名）。
 * feedLabel 是分类 RSS 标题里的名字（不写就用 label）。
 * 电商行业没有“评论类”栏目，故不设 commentary。
 */
export const CATEGORIES = [
  { key: "platform-rules", tagColor: "indigo", label: "平台规则", section: "平台规则", guide: "平台官方发布或媒体确证的规则、政策、费率、入口、治理的实质变化，直接影响商家经营成本与动作。" },
  { key: "promotions", tagColor: "orange", label: "大促玩法", section: "大促与流量", guide: "618、双 11、年货节等大促节奏，平台补贴、流量分配与算法机制变化。" },
  { key: "category-trends", tagColor: "turquoise", label: "品类趋势", section: "品类与供给", guide: "新品类机会、爆品、白牌与品牌格局、零售业态变化，以及融资并购、组织调整、新业务等竞对与行业格局变化。" },
  { key: "cross-border", tagColor: "violet", label: "跨境", section: "跨境", guide: "Temu、SHEIN、TikTok Shop、亚马逊、Shopee 等跨境平台的规则、市场、物流与政策变化。" },
  { key: "livestream", tagColor: "red", label: "直播达人", section: "直播与达人", guide: "头部主播、直播玩法、达人生态、MCN 与内容电商变化。" },
  { key: "logistics-payment", tagColor: "green", label: "物流支付", section: "物流与支付", guide: "物流价格与时效、支付牌照、收单费率、履约方式变化。" },
  { key: "regulation", tagColor: "purple", label: "监管", section: "监管与合规", guide: "市场监管总局、商务部、网信办等监管处罚、新规、执法动作，影响经营合规成本。" },
  { key: "data-reports", tagColor: "blue", label: "数据报告", section: "数据报告", guide: "权威一手数据（社零、平台财报、行业报告），本身是新事实。" },
] as const satisfies ReadonlyArray<{ key: string; tagColor: string; label: string; feedLabel?: string; section: string; guide: string; commentary?: true }>;

/**
 * 这个行业最受关注的一类发布（AI 行业是新模型）：日报报头的“N 个新模型”、改分类后修订已出的报告都按它数。
 * 电商行业没有像“新模型”那样边界清晰、能统一计数的单一发布类型，设为 null，报头不显示这个数。
 */
export const RELEASE: { category: string; tag: string; unit: string } | null = null;

/** 周报月报的总述可以直接写、不必在报道里找到出处的行业通用词（小写）。站名会自动算进去。 */
export const PLAIN_TERMS: readonly string[] = ["gmv", "sku", "spu", "roi", "cpm", "o2o", "dau", "mau", "erp", "crm", "mcn", "618", "双11", "双十二", "年货节", "直播电商", "跨境电商", "即时零售", "仅退款", "白牌"];

/**
 * 内容理解一步给每篇资料判的“内容类型”（写在 prompts/content-understanding.md 里，改了类型要同步改那份提示词）。
 * 评分提示词（prompts/selection-score.md）按类型给五个维度不同的权重。
 * 注意：内容类型是“体裁”，类别（CATEGORIES）是“领域”；一条跨境监管新闻的类别是“跨境/监管”，内容类型是 regulatory_action。
 */
export const ITEM_TYPES = [
  "platform_rule",
  "promotion_campaign",
  "industry_event",
  "regulatory_action",
  "category_trend",
  "data_report",
  "opinion_analysis",
  "tutorial_explainer",
] as const;

// ── 标签词表 ────────────────────────────────────────────────────────────────────────────

/** 每篇资料的第一个标签必须是这些“分类标签”之一（与 CATEGORIES 的 label 对齐，最后一个是兜底）。 */
export const CATEGORY_TAGS = [
  "平台规则", "大促玩法", "品类趋势", "跨境", "直播达人", "物流支付", "监管", "数据报告", "其他",
] as const;

/** 可选的主题标签（玩法与机制）。 */
export const TOPIC_TAGS = [
  "直播电商", "内容电商", "货架电商", "仅退款", "即时零售", "跨境电商", "品牌出海", "私域运营", "全托管", "半托管", "白牌", "AI电商", "本地生活", "618", "双11", "年货节",
] as const;

/** 可选的实体标签（平台、公司、机构）。 */
export const ENTITY_TAGS = ["淘宝天猫", "京东", "拼多多", "抖音电商", "快手电商", "小红书", "微信小店", "Temu", "SHEIN", "TikTok Shop", "亚马逊", "Shopee", "Lazada", "美团"] as const;

/** 模型常写的近义词，统一成词表里的写法。 */
export const TAG_SYNONYMS: Readonly<Record<string, string>> = {
  // 平台/实体统一
  "淘宝": "淘宝天猫", "天猫": "淘宝天猫", "taobao": "淘宝天猫", "tmall": "淘宝天猫", "淘宝/天猫": "淘宝天猫",
  "京东": "京东", "jd": "京东", "京东商城": "京东",
  "拼多多": "拼多多", "pdd": "拼多多", "拼夕夕": "拼多多",
  "抖音": "抖音电商", "抖音商城": "抖音电商", "抖音小店": "抖音电商", "douyin": "抖音电商",
  "快手": "快手电商", "快手小店": "快手电商", "kuaishou": "快手电商",
  "小红书": "小红书", "xiaohongshu": "小红书",
  "视频号": "微信小店", "视频号小店": "微信小店", "微信小店": "微信小店", "微信视频号": "微信小店",
  "temu": "Temu", "拼多多temu": "Temu",
  "shein": "SHEIN", "希音": "SHEIN",
  "tiktok shop": "TikTok Shop", "tiktokshop": "TikTok Shop", "tiktok": "TikTok Shop",
  "亚马逊": "亚马逊", "amazon": "亚马逊",
  "shopee": "Shopee", "虾皮": "Shopee",
  "lazada": "Lazada", "来赞达": "Lazada",
  "美团": "美团", "美团闪购": "美团", "meituan": "美团",
  // 分类标签统一
  "规则": "平台规则", "政策": "平台规则", "新规": "平台规则", "费率": "平台规则", "平台政策": "平台规则", "平台新规": "平台规则",
  "大促": "大促玩法", "促销": "大促玩法", "补贴": "大促玩法", "流量机制": "大促玩法", "流量分配": "大促玩法",
  "品类": "品类趋势", "爆品": "品类趋势", "趋势": "品类趋势", "供给": "品类趋势", "行业格局": "品类趋势",
  "出海": "跨境", "海外": "跨境",
  "直播": "直播达人", "达人": "直播达人", "主播": "直播达人", "直播带货": "直播达人", "带货主播": "直播达人",
  "物流": "物流支付", "快递": "物流支付", "支付": "物流支付", "收单": "物流支付", "履约": "物流支付", "配送": "物流支付",
  "监管": "监管", "合规": "监管", "处罚": "监管", "执法": "监管", "政策/监管": "监管",
  "数据": "数据报告", "报告": "数据报告", "财报": "数据报告", "社零": "数据报告",
  "其他": "其他",
};

// ── 平台与主体 ──────────────────────────────────────────────────────────────────────────

/**
 * 平台主题：id → 显示名、卡片上显示的标签（null 表示只用 entity:<id> 归类）、别名。
 * aliases 给结构抽取模型看；orgNames 是这家平台发消息时开头用的组织名（平台、集团、事业部），
 * 在它自己的主题页上读者知道说的是谁，可以省去；otherNames 是平台的其他称呼（官方账号名、子品牌）。
 * 所有这些名字都用来认出说的是哪家平台，比如把事实的主体对到发布方。
 */
export const ENTITIES: Record<string, { name: string; displayTag: string | null; aliases: string[]; orgNames?: string[]; otherNames?: string[] }> = {
  "taobao": { name: "淘宝天猫", displayTag: "淘宝天猫", aliases: ["淘宝", "天猫", "淘宝天猫", "Taobao", "Tmall"], orgNames: ["淘宝", "天猫", "淘天集团", "阿里巴巴"] },
  "jd": { name: "京东", displayTag: "京东", aliases: ["京东", "JD", "京东商城", "京东零售"], orgNames: ["京东", "京东集团"] },
  "pinduoduo": { name: "拼多多", displayTag: "拼多多", aliases: ["拼多多", "PDD", "拼多多集团"], orgNames: ["拼多多"] },
  "douyin": { name: "抖音电商", displayTag: "抖音电商", aliases: ["抖音电商", "抖音商城", "抖音小店", "抖音", "字节跳动"], orgNames: ["抖音电商", "抖音", "字节跳动"] },
  "kuaishou": { name: "快手电商", displayTag: "快手电商", aliases: ["快手电商", "快手小店", "快手"], orgNames: ["快手", "快手电商"] },
  "xiaohongshu": { name: "小红书", displayTag: "小红书", aliases: ["小红书", "RED", "小红书电商"], orgNames: ["小红书"] },
  "wechat": { name: "微信小店", displayTag: "微信小店", aliases: ["微信小店", "视频号小店", "视频号", "微信视频号"], orgNames: ["微信小店", "视频号", "微信"] },
  "temu": { name: "Temu", displayTag: "Temu", aliases: ["Temu", "TEMU", "拼多多海外"], orgNames: ["Temu"] },
  "shein": { name: "SHEIN", displayTag: "SHEIN", aliases: ["SHEIN", "Shein", "希音"], orgNames: ["SHEIN", "希音"] },
  "tiktokshop": { name: "TikTok Shop", displayTag: "TikTok Shop", aliases: ["TikTok Shop", "TikTok", "抖音国际"], orgNames: ["TikTok Shop"] },
  "amazon": { name: "亚马逊", displayTag: "亚马逊", aliases: ["亚马逊", "Amazon", "亚马逊全球开店"], orgNames: ["Amazon", "亚马逊"] },
  "shopee": { name: "Shopee", displayTag: "Shopee", aliases: ["Shopee", "虾皮"], orgNames: ["Shopee", "虾皮"] },
  "lazada": { name: "Lazada", displayTag: "Lazada", aliases: ["Lazada", "来赞达"], orgNames: ["Lazada"] },
  "meituan": { name: "美团", displayTag: "美团", aliases: ["美团", "美团闪购", "美团外卖"], orgNames: ["美团"] },
};

/**
 * 身份词典：摘要和标题里出现的平台/公司，必须在原文里也出现过，否则退回原标题、丢掉摘要（防止模型张冠李戴）。
 */
export const IDENTITY_LEXICON: ReadonlyArray<{ id: string; name: string; patterns: RegExp[] }> = [
  { id: "taobao", name: "淘宝/天猫", patterns: [/淘宝|天猫|淘天|taobao|tmall/i] },
  { id: "jd", name: "京东", patterns: [/京东|京东商城|\bjd\.com\b/i] },
  { id: "pinduoduo", name: "拼多多", patterns: [/拼多多|pinduoduo|\bpdd\b/i] },
  { id: "douyin", name: "抖音电商", patterns: [/抖音|douyin|bytedance|字节跳动/i] },
  { id: "kuaishou", name: "快手", patterns: [/快手|kuaishou/i] },
  { id: "xiaohongshu", name: "小红书", patterns: [/小红书|xiaohongshu|\bred\b/i] },
  { id: "wechat", name: "微信小店/视频号", patterns: [/微信小店|视频号|微信视频号/i] },
  { id: "temu", name: "Temu", patterns: [/\btemu\b/i] },
  { id: "shein", name: "SHEIN", patterns: [/\bshein\b|希音/i] },
  { id: "tiktokshop", name: "TikTok Shop", patterns: [/tiktok\s?shop/i] },
  { id: "amazon", name: "亚马逊", patterns: [/亚马逊|amazon/i] },
  { id: "shopee", name: "Shopee", patterns: [/shopee|虾皮/i] },
  { id: "lazada", name: "Lazada", patterns: [/lazada|来赞达/i] },
  { id: "meituan", name: "美团", patterns: [/美团|meituan/i] },
];

/** 这些域名上的文章，发布方就是对应的平台（托管平台不算）。 */
export const PUBLISHER_DOMAINS: ReadonlyArray<{ entityId: string; domains: readonly string[] }> = [
  { entityId: "amazon", domains: ["aboutamazon.com"] },
];

/** 原文里的这些写法也算提到了对应平台。 */
export const IDENTITY_CONTEXT_ALIASES: ReadonlyArray<{ entityId: string; pattern: RegExp }> = [];
