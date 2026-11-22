# 电商 HOT · 每日飞书早报

每天 09:00 自动把电商热点精选推送到飞书群「电商 HOT 日报」。本目录是从 `ai-hot-feishu`（AI 行业版）**复制改名**出来的独立副本，改信源和提示词即可，不重写逻辑。

> 原目录 `C:\Users\19024\Documents\deepseek-harness\default-workspace\ai-hot-feishu` 和它的计划任务 `AIHOT-Daily-Feishu` **只读、不要改**。本项目的计划任务是 `ECHOT-Daily-Feishu`。

## 工作流程

抓 RSS/Atom → 30 小时时间窗 + URL/标题去重（含历史 `state/seen.json`）→ DeepSeek 打分 1–10 + 写中文标题/摘要/事件标签 → 事件级去重 → 飞书交互卡片推送。

## 目录结构

```
ec-hot-feishu/
├── aihot.py               # 主程序（SYSTEM_PROMPT 在这里改选稿标准）
├── config.json            # 信源、入选门槛、模型/飞书配置
├── .env                   # 密钥（不进版本库，已 gitignore）
├── install_schedule.ps1   # 注册/卸载 Windows 计划任务
├── logs/aihot-YYYY-MM-DD.log   # 每次运行的日志
└── state/                 # seen.json 去重历史、card-preview.json 最近一期卡片
```

## 密钥（.env，绝不进代码/issue）

```
FEISHU_APP_ID=...          # 应用「徐梓芸的生活管家（DSH）」
FEISHU_APP_SECRET=...
FEISHU_RECEIVE_ID=...      # 群「电商 HOT 日报」的 chat_id
DEEPSEEK_API_KEY=...
```

## 手动运行

```powershell
cd C:\Users\19024\Documents\ecommerce-hot\ec-hot-feishu
# 用 dsh 自带 Python：
#   C:\Users\19024\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe

python aihot.py --dry-run     # 只抓取+精选，卡片写到 state/card-preview.json，不推送
python aihot.py               # 正式跑一次并推送到飞书群
python aihot.py --test        # 发一张测试卡片，验证飞书链路
python aihot.py --list-chats  # 列出机器人所在的群，拿 chat_id
python aihot.py --resend      # 重发 state/card-preview.json 里最近一期卡片（补发用）
```

## 日志在哪

`logs/aihot-YYYY-MM-DD.log`。每行带时间戳，关键信息：

- `抓取完成：12/12 个信源正常，原始 N 条，去重筛选后 M 条候选` —— 源健康度与候选量
- `信源异常：<源名>: <原因>` —— 哪个源挂了
- `大模型返回：prompt=... completion=...` —— 每次的 token 用量
- `精选出 K 条` 及逐条 `[分数] 标题 —— 来源` —— 最终入选

## 怎么改

| 想改什么 | 改哪里 |
|---|---|
| 信源（增删 RSS） | `config.json` 的 `sources` 数组：`id/name/url/tier`，url 必须是 RSS/Atom |
| 入选门槛 | `config.json` 的 `min_score`（默认 6）、`max_items`（12）、`max_candidates`（150）、`max_per_source`（3） |
| 选稿标准（什么该选/不选） | `aihot.py` 里的 `SYSTEM_PROMPT` 和 `USER_TEMPLATE` |
| 推送时间 | 重跑计划任务：`powershell -File .\install_schedule.ps1 -Time 07:30` |

## 计划任务

```powershell
# 注册（默认每天 09:00，任务名 ECHOT-Daily-Feishu）
powershell -ExecutionPolicy Bypass -File .\install_schedule.ps1

# 改时间
powershell -ExecutionPolicy Bypass -File .\install_schedule.ps1 -Time 07:30

# 立即试跑一次
schtasks /Run /TN ECHOT-Daily-Feishu

# 查看下次运行时间
schtasks /Query /TN ECHOT-Daily-Feishu /V /FO LIST

# 卸载
powershell -ExecutionPolicy Bypass -File .\install_schedule.ps1 -Remove
```

任务用 `pythonw.exe` 无窗口运行，仅在用户已登录（InteractiveToken）时触发；电脑关机/睡眠错过 09:00 不会补跑，可次日手动 `python aihot.py` 补发。

## 已知限制（重要）

本管线只吃 **RSS/Atom**，而电商信源里最有价值的平台官方规则源（淘宝/京东/拼多多/抖音/快手/小红书等）都是网页列表（`web_list`），没有公开 RSS。因此飞书早报目前只能稳定产出 **5–7 条/天**（已实测多轮）。要稳定 8–12 条并覆盖平台规则，需依赖 AIHOT 站点引擎的 `web_list` 抓取能力（Phase B 站点版，见 RAY-56），飞书早报是站点版上线前的轻量出口。

## 去重

`state/seen.json` 记录近 14 天内已推过的 URL 与标题，正式推送（非 dry-run）后写入，避免第二天重复推昨天内容。清空该文件可强制重新推送历史内容。
