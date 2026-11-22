# 电商 HOT · 进展台账

> 这份文件是 DSH 侧（会话）和 Multica 侧 agent 之间的**共享事实源**。
> 两边都能读写，每次有里程碑就追加一条，格式固定。

## 2026-11-22 11:55

### 局域网已打通

| 项 | 结果 |
|---|---|
| 端口转发 | `0.0.0.0:3000 -> 127.0.0.1:3000`（netsh portproxy） |
| 防火墙 | 规则 `EC-HOT 3000`，入站放行，Profile = Domain, Private |
| 本机验证 | http://127.0.0.1:3000 → 200 |
| 局域网验证 | **http://192.168.1.2:3000 → 200** |
| 执行方式 | 用户以管理员运行 `tools/open-lan.ps1`（脚本自动申请 UAC） |

### 数据量（11:55）

| 表 | 数量 |
|---|---|
| articles | 936 |
| facts | 86 |
| stories | 85 |
| publications | 685 |
| 首页今日精选 | 10 条 |

### 已完成清单

- [x] 站点本机可访问（localhost:3000）
- [x] 后台可登录（/admin）
- [x] 局域网可访问（192.168.1.2:3000，手机/平板可用）
- [x] 采集全量跑通（25 源 23 成功）
- [x] GitHub + Gitee 双仓同步（HEAD 一致）
- [x] 每天 9:00 飞书推送任务（ECHOT-Daily-Feishu，Next Run 2026-11-23 09:00）
- [x] 开机自启（Startup 里的 ECHOT-StartSite.vbs）

### 待办

- [x] 修 2 个坏源：`web-zfzj`（站点下线，域名/备案过期）、`web-thepaper`（标题在 img alt 读不到）——均已 `enabled:false`（commit `fc81cba`）
- [x] 核精选门槛：`industry/selection.ts` T2 76→60，精选 2→18 条；**平台规则占比 0%**（整个内容池仅 2 条 platform-rules，根因是淘宝/京东/拼多多/抖音官方规则页 SPA 抓不到，非门槛问题）
- [x] 运行手册 `docs/电商HOT-运行手册.md`（重启/备份/排障/改时间/加源/改标准/双推）
- [ ] 内容质量校准（标注样本 + 精确率）——需 `JINA_API_KEY` 接平台官方源 + 电商标注样本，走 `scripts/eval-selection.ts`

### 常用命令

```bash
# 进 WSL 看状态
wsl -d Ubuntu-24.04 -u root
cd /mnt/c/Users/19024/Documents/ecommerce-hot/AIHOT
docker compose ps
docker compose logs --tail=50 worker

# 手动跑一轮采集
wsl -d Ubuntu-24.04 -u root -- bash /mnt/c/Users/19024/Documents/ecommerce-hot/AIHOT/tools/collect-now.sh
```
