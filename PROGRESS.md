# 电商 HOT · 进展台账

> 这份文件是 DSH 侧（我这个会话）和 Multica 侧 agent 之间的**共享事实源**。
> 两边都能读写，每次有里程碑就追加一条，格式固定。

## 2026-11-22 10:16

### 已完成（DSH 侧）

| 项 | 结果 | 证据 |
|---|---|---|
| 飞书群 | 「电商 HOT 日报」已建，用户已进群 | chat_id `oc_843ef4e03d0f94becbdbc263cfcdb9fb`，群成员 用户1/机器人1 |
| 电商版首推 | 已发 5 条卡片 | `ec-hot-feishu/logs/aihot-2026-11-22.log` 10:05:35 推送成功 |
| Docker | WSL2 Ubuntu 24.04 内 Docker Engine 29.1.3 + Compose 2.40.3 | `docker run hello-world` 通过；镜像源已配 |
| SSH | GitHub/Gitee 均验证通过（raymongit） | `Hi raymongit! You've successfully authenticated` |
| 仓库 | 待用户建空仓库 `ec-hot` | 未完成 |

### 已完成（Multica 侧）

| Issue | 内容 | 状态 |
|---|---|---|
| RAY-51 | 电商信源清单 + 选稿标准 | in_review，25 源实测 |
| RAY-52 | AIHOT 脚手架 + 环境判定 | in_review，代码已克隆 |
| RAY-53 | 领域改造 | in_review |
| RAY-57 | 双远端镜像 | backlog，等仓库 |

### 当前卡点

1. 用户还没在两个平台建空仓库 `ec-hot`（SSH 不能建仓库）
2. 平台官方规则源（淘宝/京东/拼多多/抖音）没有 RSS，只有站点引擎的 web_list 能抓 —— 推送版覆盖不到
3. 电商版 9:00 定时任务尚未创建（等推送内容验收后再定）

### 下一步（按顺序）

1. 用户建仓库 → 推 RAY-57 双推
2. 站点部署：`docker compose up -d --build`（Docker 已就绪）
3. 内容验收后建 `ECHOT-Daily-Feishu` 计划任务

## 2026-11-22 10:57（Multica RAY-58 首轮）

### 已完成（Multica 侧）

| 项 | 结果 | 证据 |
|---|---|---|
| 站点部署 | `docker compose up -d --build` 成功，首页 200、/admin 可登录 | web 容器 0.0.0.0:3000；98 迁移、25 源 seed |
| 采集 | worker 自动采集 171 篇（24/25 源成功） | fetch_runs：web_list 13 源 ok，仅 web-thepaper 选择器不匹配 |
| web_list 试抓 | 后台 API 试抓「商务部电子商务司」返回 17 条真实公告 | `POST /api/admin/sources/web-dzsws/preview` |
| 计划任务 | `ECHOT-Daily-Feishu` 已注册，下次 2026-11-23 09:00 | schtasks /Query，Task To Run 指向 ec-hot-feishu/aihot.py |
| 运行手册 | `docs/电商HOT-运行手册.md` 已写 | 加源/改标准/改时间/双推/排障/红线 |
| 提交 | `75c6e3b` Dockerfile 国内镜像参数 + 手册 | 已 commit，待推 |

### 当前卡点（不变）

1. **仓库仍未建**：GitHub `raymongit/ec-hot` 与 Gitee `raymongit/ec-hot` 均不存在，SSH 不能建仓，需平台 Token 或用户手动建空仓 → 双推（deliverable 4）阻塞
2. **平台官方源（淘宝/京东/拼多多/抖音）**：确认全部 SPA/登录墙（jos.jd.com 6.4KB 空壳、open.taobao.com 2.4KB、open.pinduoduo.com 1.7KB、抖音 announcement 无服务端渲染），直抓 `no items matched`；需 `JINA_API_KEY`（.env 未配）用 Jina web_list 补齐

### 下一步

1. 用户建两平台空仓库（或提供 Token）→ 跑 `scripts/sync-mirror.ps1` 完成首次双推
2. 若用户提供 Jina key → 在后台加淘宝/京东/拼多多/抖音的 Jina web_list 源并试抓
3. web-thepaper 选择器微调或删除（可选噪音源，非阻塞）
