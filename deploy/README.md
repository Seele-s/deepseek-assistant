# 部署与运维说明

本项目已在阿里云 ECS（Alibaba Cloud Linux 3）完成生产级部署，本文档记录完整部署方案。

## 一、部署架构

```
用户浏览器
   │ HTTP :80
   ▼
Nginx ──┬── 静态资源  /opt/deepseekproject/frontend/dist
        │
        └── /api/ 反向代理 ──► Uvicorn (127.0.0.1:8000)
                                      │
                                      ├── MySQL 8.0 (127.0.0.1:3306)
                                      └── 模型服务（外发 HTTPS）
```

**几个关键设计：**

| 设计 | 目的 |
| --- | --- |
| 应用只监听 `127.0.0.1:8000` | 不对外暴露，外部流量统一经 Nginx，减少攻击面 |
| Nginx 同时托管前端与反代接口 | **单端口部署**，无需再开第二个端口、也无跨域问题 |
| Nginx Basic Auth 访问网关 | 外人不输密码连页面都看不到 |
| 应用 JWT 走自定义头 `X-Auth-Token` | 避免与网关的 `Authorization` 头冲突（见下） |
| 应用使用独立的最小权限 MySQL 账号 | 替代 root 直连，降低泄露风险 |

## 二、目录说明

```
deploy/
├── setup.sh                          # 一键部署脚本
├── dsctl                             # 一键启停工具
├── nginx/
│   ├── deepseek.conf                 # 站点配置（正式运行）
│   └── deepseek-maintenance.conf     # 站点配置（停止 / 维护）
├── systemd/
│   └── deepseek.service              # 服务单元（进程守护 + 开机自启）
└── maintenance/
    └── index.html                    # 「服务已暂停」页面
```

文件安装位置：

| 仓库内 | 服务器位置 |
| --- | --- |
| `nginx/deepseek.conf` | `/etc/nginx/conf.d/deepseek.conf` |
| `systemd/deepseek.service` | `/etc/systemd/system/deepseek.service` |
| `maintenance/index.html` | `/var/www/maintenance/index.html` |
| `dsctl` | `/usr/local/bin/dsctl` |

## 三、一键部署

```bash
DB_PASS='你的数据库密码' GATEWAY_PASS='你的网关口令' bash deploy/setup.sh
```

脚本会完成：安装 Python 3.11 / Nginx → 部署代码 → 建虚拟环境装依赖 →
创建数据库与最小权限账号 → 装 systemd 服务 → 装 Nginx 配置 →
生成网关密码 → 安装维护页与 dsctl → 启动并自检。

部署后**必须手动做一件事**：编辑 `/opt/deepseekproject/backend/.env`，
填入 `DEEPSEEK_API_KEY`，然后 `systemctl restart deepseek`。

## 四、常用运维命令

```bash
dsctl start             # 启动（对外可访问）
dsctl stop              # 停止（显示维护页，不消耗 API 额度）
dsctl restart           # 只重启后端
dsctl status            # 查看运行状态
dsctl log 100           # 查看最近 100 行日志
dsctl passwd <新密码>    # 修改访问网关密码

systemctl status deepseek
tail -f /var/log/deepseek.log
nginx -t && systemctl reload nginx
```

`dsctl stop` 做了三件事：停掉后端进程 → Nginx 切到维护页 → 关闭开机自启。
这样即使服务器重启，服务也不会被意外拉起。

## 五、⚠️ 踩过的三个坑（部署时最容易出错的地方）

### 1. SSE 流式输出被 Nginx 缓冲，退化成"一次性返回"

**现象**：本地测试正常，上线后 AI 回答不是逐字出现，而是等全部生成完才一次性显示。

**原因**：Nginx 默认开启 `proxy_buffering`，会把后端响应缓冲后一次性发出去。

**解决**：在 `/api/` 的 location 中关闭缓冲：

```nginx
proxy_buffering off;
proxy_cache off;
proxy_read_timeout 300s;
proxy_set_header Connection '';
chunked_transfer_encoding on;
```

验证方式：一次对话产生的流式数据块数应远大于 1（实测 50+）。

### 2. 两种认证抢占同一个 `Authorization` 请求头

**现象**：加上 Nginx Basic Auth 网关后，接口全部返回 401 Not authenticated。

**原因**：网关用 `Authorization: Basic xxx`，应用 JWT 也用 `Authorization: Bearer xxx`，
浏览器在收到 401 挑战时会用缓存的 Basic 凭据覆盖应用设置的 Bearer，两者互相踩踏。

**解决**：把应用自身的 JWT 挪到自定义请求头，与网关彻底隔离：

```
网关      →  Authorization: Basic ...      （浏览器自动携带）
应用 JWT  →  X-Auth-Token: Bearer ...      （前端显式携带）
```

后端同时兼容标准 `Authorization: Bearer`，方便 Swagger 调试。

### 3. 小内存服务器被 OOM Killer 杀掉进程

2 核 2G 的机器同时跑 Nginx + MySQL + Python 应用，内存余量有限。

**解决**：配置 swap 兜底，并实测应用本身内存占用（uvicorn 约 100MB）。

```bash
fallocate -l 2G /swapfile && chmod 600 /swapfile
mkswap /swapfile && swapon /swapfile
echo '/swapfile none swap sw 0 0' >> /etc/fstab
```

## 六、安全建议

1. **`.env` 权限设为 `600`**，且绝不提交到 Git（仓库已用 `.gitignore` 排除）
2. **不要用 root 直连数据库**，为应用创建最小权限账号
3. **限制 3306 端口对外暴露**（在云安全组层面拦截），或让 MySQL 只监听 127.0.0.1
4. **配置 HTTPS**：当前为 HTTP 明文，登录密码在传输中未加密，
   有域名后建议用 Let's Encrypt 免费证书启用 443
5. **给云厂商 API Key 设置消费限额**，防止被刷

## 七、资源占用参考（2 核 2G 实测）

| 项目 | 占用 |
| --- | --- |
| Uvicorn（应用） | 约 100 MB |
| Nginx | 约 20 MB |
| MySQL 8.0 | 约 300~500 MB |
| 系统 + 其他 | 约 250 MB |
| **合计** | **约 0.8~1 GB**，剩余内存充足 |

并发瓶颈不在 CPU，而在带宽与模型服务侧——本机只做转发与静态资源服务。
