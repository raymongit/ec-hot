# 电商 HOT · 进展台账

> 这份文件是 DSH 侧（会话）和 Multica 侧 agent 之间的**共享事实源**。
> 两边都能读写，每次有里程碑就追加一条，格式固定。

## 2026-11-22 12:35 · 公网临时地址已打通

### 当前可用入口

| 入口 | 地址 | 说明 |
|---|---|---|
| 本机 | http://127.0.0.1:3000 | 直连 web 容器 |
| 局域网 | http://192.168.1.2:3000 | 同 WiFi 的手机/平板 |
| 公网（临时） | `https://<随机>.serveousercontent.com` | SSH 隧道 → Caddy(3001) → web(3000)，进程在则有效 |
| 公网后台 | 同上 + `/admin` | Basic Auth：`ecadmin` / 密码在 `.env` 的 `EDGE_ADMIN_PASSWORD` |

### 公网入口架构

```
公网 → serveo.net (SSH 反向隧道) → 本机 :3001 (Caddy) → web:3000
                                      └─ /admin* 需 Basic Auth
```

- `deploy/Caddyfile.public`：反代 + `/admin*`、`/api/admin*` 的 Basic Auth
- `docker-compose.public.yml`：叠加层，单独起 `edge` 服务，不动原本的 compose
- `tools/start-tunnel.ps1` / `tools/stop-tunnel.ps1`：临时公网隧道开关

### 试过但没走通的路

| 方案 | 结果 |
|---|---|
| WSL `networkingMode=mirrored` | 该 WSL 版本（3.0.5）不生效，端口没暴露，已回退 |
| Cloudflare Tunnel（cloudflared） | 二进制从 GitHub 下载被限速/重置（60MB 卡在 3MB），暂时放弃 |
| localhost.run / pinggy | 连上了但不打印地址（需要 TTY），放弃 |
| **serveo.net** | ✅ 可用，本次采用 |

### 数据量（12:30）

articles 936 / facts 86 / stories 85 / publications 685，首页今日 10 条。

### 待办

- [x] 修 2 个坏源：`web-zfzj`（站点下线）、`web-thepaper`（标题在 img alt）→ 均已 `enabled:false`（commit `fc81cba`）
- [x] 核精选门槛与平台规则占比：门槛 T2 76→60，精选 2→18；**平台规则占比 0%**（根因是四家平台官方规则页 SPA 抓不到，需 Jina key）
- [x] 运行手册 `docs/电商HOT-运行手册.md`（重启/备份/排障/改时间/加源/改标准/双推）
- [ ] 正式对外：买域名（`ecommerce.news` 待查）+ 云服务器 + 备案（需用户拍板）
- [ ] 有域名后可换回 Cloudflare Tunnel（需要能下载 cloudflared 时）

## 2026-11-22 13:10 · 隧道加守护（修 502）

### 502 的原因
不是站点挂了（当时本机 3000 / 3001 都返回 200），是 SSH 隧道进程断了，serveo 连不到后端。

### 现在的做法

| 件 | 作用 |
|---|---|
| `tools/tunnel-supervisor.ps1` | 守护进程：ssh 退出 5 秒后自动重连，把当前地址写进 `%TEMP%\echot-public-url.txt` |
| Startup 里的 `ECHOT-Tunnel.vbs` | 登录后自动拉起守护进程（隐藏窗口） |
| `%TEMP%\echot-tunnel.log` | 重连日志 |

查当前地址：

```powershell
Get-Content $env:TEMP\echot-public-url.txt
```

### 稳定性边界
- 进程活着就一直可用，掉线会自动重连，但**地址会变**
- 要固定地址：给 serveo 注册 SSH 公钥后可申请子域名（如 `echot.serveo.net`）
- 要真正稳定：域名 + 云服务器 + 备案；或能下载 cloudflared 后换 Cloudflare Tunnel

### 公网入口验证（Multica 侧 12:40）

- `edge` 容器 Up，`0.0.0.0:3001->3001`
- `http://127.0.0.1:3001/` → 200（公开可读）
- `http://127.0.0.1:3001/admin` → 401、`/api/admin/me` → 401（Basic Auth 生效）
- `.env` 含 `EDGE_ADMIN_PASSWORD` / `EDGE_ADMIN_HASH`，均已 gitignore，未入库
