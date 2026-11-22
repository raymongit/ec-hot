# 电商 HOT · 运行手册

> 面向运营者的操作手册。站点、飞书早报、双仓库三部分日常怎么用、怎么改、坏了怎么排。
> 事实台账在仓库外的 `PROGRESS.md`（`C:\Users\19024\Documents\ecommerce-hot\PROGRESS.md`），每次里程碑追加一条。

## 0. 项目长什么样

```
C:\Users\19024\Documents\ecommerce-hot\
├── AIHOT\                    # 站点（本仓库）：Next/React + PostgreSQL + Docker
│   ├── industry\             # 行业知识：分类、信源、选稿标准、提示词
│   ├── modules\feishu-digest\  # 飞书早报管线（RSS + DeepSeek 精选 + 飞书卡片）
│   ├── docs\sources.md       # 六种信源与配置（权威）
│   ├── docs\selection.md     # 精选与发布规则（权威）
│   └── docker-compose.yml
└── PROGRESS.md               # 跨会话事实台账（DSH 侧与 Multica 侧共享）
```

- **站点**：`http://localhost:3000`，后台 `http://localhost:3000/admin`。跑在 WSL2 的 Docker 里。
- **飞书早报**：Windows 计划任务 `ECHOT-Daily-Feishu`，每天 09:00 跑 `modules/feishu-digest/aihot.py` 推到群「电商 HOT 日报」。
- **双仓库**：GitHub `raymongit/ec-hot`（origin）+ Gitee `raymongit/ec-hot`（gitee），上游是 `KKKKhazix/AIHOT`（upstream）。

## 1. 站点：起、停、看

Docker 在 WSL2 的 Ubuntu-24.04 里（本机 Windows 没有 Docker）。从 Windows 打开终端后先进 WSL（`/etc/wsl.conf` 已开 `systemd=true`，WSL 重启后 docker 会自动起来）：

```powershell
wsl -d Ubuntu-24.04
```

然后（路径是 Windows 盘挂载进来的）：

```bash
cd /mnt/c/Users/19024/Documents/ecommerce-hot/AIHOT

# 起（首次/改代码后都要 --build）——国内网络加两个镜像参数
docker compose build \
  --build-arg NPM_REGISTRY=https://registry.npmmirror.com \
  --build-arg DEBIAN_MIRROR=mirrors.aliyun.com
docker compose up -d

# 看状态 / 日志
docker compose ps
docker compose logs -f web api worker     # 分别看 web / api / worker

# 停 / 清数据（清数据不可逆，先确认）
docker compose down          # 停，保留数据卷
docker compose down -v       # 停并删数据卷（数据库、抓取内容全清，慎用）
```

启动后：

- 首页：`http://localhost:3000`
- 后台：`http://localhost:3000/admin`（密码在 `.env` 的 `ADMIN_PASSWORD`，不写进仓库）

首次启动会自动跑 `scripts/migrate.ts` + `scripts/seed.ts`，把 `industry/sources.json` 的 25 个信源导入；`COLLECT_ENABLED=true` 时 worker 会开始自动采集，`MODEL_CALLS_ENABLED=true` 时会用 DeepSeek 评分与写作（花 API 额度）。

## 2. 加信源

两种方式，二选一：

- **后台加（推荐，可先试抓）**：`/admin/sources/new`，填 ID、名称，选类型（rss / web_list / json_list / x_search / mp_account / external），粘贴采集配置，先点「预览抓取」看能不能取到真实条目，再创建。
- **批量加**：改 `industry/sources.json`，然后重启让 seed 重新导入；或后台手动逐条建。

每种信源怎么配、选择器怎么写，看 `docs/sources.md`（权威）。要点：

- `web_list` 的关键是 `itemSelector` 选中「每条新闻」而不是包住所有新闻的容器；平台官方规则页（淘宝/京东/拼多多/抖音）多是 SPA/登录墙，直抓拿不到，需 Jina Reader（`.env` 配 `JINA_API_KEY`，`url` 写成 `https://r.jina.ai/https://目标站/路径`）或改接其开放平台 JSON 接口（`json_list`）。
- 改完后台「试抓」验证；抓取失败会标红并显示原因。

## 3. 改选稿标准

选稿标准分三层：

| 改什么 | 改哪里 |
|---|---|
| 入选门槛（多少分算入选） | `industry/selection.ts` 的 `thresholds`（当前 T1=60、T1_5=65、T2=76） |
| 评分标准（什么该选/不选） | `industry/prompts/selection-score.md` 与 `industry/prompts/` 下相关提示词 |
| 类别/标签/主体名录 | `industry/taxonomy.ts`、`industry/topics.json` |

改动后重新构建并跑评测再上线：`scripts/eval-selection.ts`（见 `docs/selection.md`）。

飞书早报的选稿标准是**另一套**：改 `modules/feishu-digest/aihot.py` 里的 `SYSTEM_PROMPT`/`USER_TEMPLATE`，门槛改 `modules/feishu-digest/config.json` 的 `min_score`。

## 4. 改推送时间

飞书早报时间是 Windows 计划任务决定的，改时间重新注册即可：

```powershell
cd C:\Users\19024\Documents\ecommerce-hot\AIHOT\modules\feishu-digest
powershell -ExecutionPolicy Bypass -File .\install_schedule.ps1 -Time 07:30   # 改成 07:30
schtasks /Query /TN ECHOT-Daily-Feishu /V /FO LIST                            # 看下次运行时间
schtasks /Run /TN ECHOT-Daily-Feishu                                           # 立即试跑
```

任务只在用户已登录时触发；关机/睡眠错过 09:00 不会补跑，次日手动补发：

```powershell
cd C:\Users\19024\Documents\ecommerce-hot\AIHOT\modules\feishu-digest
C:\Users\19024\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe aihot.py   # 正式推一次
C:\Users\19024\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe aihot.py --dry-run  # 只抓不推
```

站点自身的日报出刊时间（09:00）在 `site/site.ts` 的 `EDITION_TIMES.daily`，改完 `docker compose up --build`。

## 5. 双仓库推送（GitHub + Gitee）

git 是唯一事实源，改动先 commit 再双推：

```powershell
cd C:\Users\19024\Documents\ecommerce-hot\AIHOT
git add -A && git commit -m "..."       # 提交
powershell -NoProfile -File scripts/sync-mirror.ps1    # 检查 + dry-run + 推 origin 和 gitee
powershell -NoProfile -File scripts/sync-mirror.ps1 -NoPush   # 只检查不推
```

脚本会先做发布前检查（`.env`/`state`/`logs` 不提交、无密钥），再推 `main` + tags 到两个远端。两个远端（GitHub/Gitee 的 `ec-hot`）已建好并 public，推完后两个平台的 `main` 应指向同一 commit。

## 6. 排障

| 现象 | 先看 | 常见处理 |
|---|---|---|
| 站点打不开 | `wsl -d Ubuntu-24.04` 里 `docker compose ps` / `logs web` | 容器没起来看日志；端口被占用改 `.env` 的 `PORT` |
| 后台抓取失败/标红 | 后台「信源」页的失败原因 | 选择器不匹配 → 试抓微调；SPA 页 → Jina；网络 → 检查代理 |
| 早报没收到 | `modules/feishu-digest/logs/aihot-YYYY-MM-DD.log` | 看 `信源异常`/`推送成功`；重跑 `schtasks /Run` |
| 早报内容少（5–7 条/天） | 同上日志 | 正常：飞书版只吃 RSS，平台官方源是 SPA 抓不到，等站点 web_list 补齐 |
| 推送失败 | 计划任务 `Last Result` | `schtasks /Query /TN ECHOT-Daily-Feishu /V /FO LIST` 看错误码 |
| 双推失败 | `scripts/sync-mirror.ps1` 的报错 | 它会把 git 报错翻译成人话（仓库不存在 / SSH / 网络 / 冲突） |
| 站点想清空重来 | `docker compose down -v` | 删数据卷不可逆，先确认再执行 |

## 7. 密钥与红线

- 密钥只在各目录的 `.env`（站点 `AIHOT/.env`、早报 `AIHOT/modules/feishu-digest/.env`），均已 gitignore，**绝不写进 issue、代码或本手册**。
- 站名统一「电商 HOT」，不用 AIHOT 的名字和 Logo。
- `ai-hot-feishu`（AI 版）只读不改；本项目的早报是 `modules/feishu-digest`。
- 装软件、对外发布、删数据这类不可逆动作先确认再做。
