# 云服务器部署说明（生产环境）

> 部署时间：2026-10-14 ｜ 服务器：阿里云 ECS（Alibaba Cloud Linux 3）

## 一、访问地址

| 用途 | 地址 |
| --- | --- |
| 应用首页 | http://YOUR_SERVER_IP |
| 接口文档 | http://YOUR_SERVER_IP/docs |
| 健康检查 | http://YOUR_SERVER_IP/api/health |
| 健康探针（Nginx） | http://YOUR_SERVER_IP/healthz |

## 二、服务器信息

| 项目 | 值 |
| --- | --- |
| 公网 IP | YOUR_SERVER_IP |
| 主机名 | sayhello |
| 系统 | Alibaba Cloud Linux 3 (OpenAnolis Edition)，内核 5.10 |
| CPU / 内存 | 2 核 / 1.8 GB（另有 4 GB swap） |
| 磁盘 | 40 GB（已用 43%） |
| 运行环境 | Python 3.11.13（dnf 安装） |

## 三、架构

```
用户浏览器
   │ HTTP :80
   ▼
Nginx  ──┬── 静态资源  /opt/deepseekproject/frontend/dist
         │
         └── /api/ 反向代理 ──► Uvicorn (127.0.0.1:8000)
                                      │
                                      ├── MySQL 8.0 (127.0.0.1:3306, 库 deepseek_chat)
                                      └── api.deepseek.com（外发）
```

- Nginx **不监听** 8080，应用也不直接暴露 8000 端口，全部通过 80 端口统一入口
- SSE 流式输出在 `location /api/` 中关闭了 `proxy_buffering`，否则会退化成一次性返回

## 四、目录与文件

| 路径 | 说明 |
| --- | --- |
| `/opt/deepseekproject` | 应用根目录 |
| `/opt/deepseekproject/backend/app` | 后端分层源码 |
| `/opt/deepseekproject/frontend/dist` | 前端构建产物（Nginx 直接托管） |
| `/opt/deepseekproject/.venv` | Python 虚拟环境 |
| `/opt/deepseekproject/backend/.env` | **环境配置（含密钥）** |
| `/etc/systemd/system/deepseek.service` | systemd 服务单元 |
| `/etc/nginx/conf.d/deepseek.conf` | Nginx 站点配置 |
| `/var/log/deepseek.log` | 应用日志 |
| `/var/log/nginx/deepseek.error.log` | Nginx 错误日志 |
| `/root/nginx-backup/` | 部署前的 Nginx 配置备份 |

## 五、常用运维命令

```bash
# 查看服务状态
systemctl status deepseek

# 重启 / 停止 / 启动
systemctl restart deepseek
systemctl stop deepseek
systemctl start deepseek

# 看实时日志
tail -f /var/log/deepseek.log

# 重载 Nginx（改配置后）
nginx -t && systemctl reload nginx

# 查看资源占用
free -h && ps aux | grep uvicorn
```

## 六、更新代码流程

```bash
# 1. 本机重新打包（或在服务器上直接改）
# 2. 上传
scp deploy.tar.gz root@YOUR_SERVER_IP:/tmp/
# 3. 解压覆盖
cd /opt/deepseekproject && tar -xzf /tmp/deploy.tar.gz
# 4. 重启服务
systemctl restart deepseek
```

改前端时：本机 `npm run build` → 上传 `frontend/dist` → **无需重启后端**，Nginx 直接读新文件。

## 七、修改 DeepSeek API Key

```bash
vi /opt/deepseekproject/backend/.env      # 修改 DEEPSEEK_API_KEY
systemctl restart deepseek
curl -s http://127.0.0.1/api/health       # 确认 api_key_configured: true
```

## 七之二、模型服务说明

本站点通过 **OpenAI 兼容接口**接入模型，不是 DeepSeek 官方域名，配置项在 `backend/.env`：

| 配置 | 值 |
| --- | --- |
| `DEEPSEEK_BASE_URL` | `https://maas.qianwenaiapi.com/compatible-mode/v1` |
| `CHAT_MODEL` | `deepseek-v4.1-flash`（普通对话模式） |
| `REASONER_MODEL` | `deepseek-v4-pro`（深度思考模式） |

说明：
- **普通模式**走 `deepseek-v4.1-flash`：响应快，实测首字约 1.4s、完整回答约 4s
- **深度思考模式**走 `deepseek-v4-pro`：推理更强，实测首字约 0.9s、完整回答约 9s
- 两个模型都会返回 `reasoning_content`（思维链），前端会展示在「深度思考过程」面板中
- 切换模型只需改 `backend/.env` 后重启服务：
  ```bash
  vi /opt/deepseekproject/backend/.env     # 改 CHAT_MODEL / REASONER_MODEL
  systemctl restart deepseek
  ```
- 可用模型列表可通过 `GET {BASE_URL}/models` 查询（当前账号可用 176 个模型）

## 八、数据库

```bash
mysql -uroot -p deepseek_chat

# 应用专用账号（最小权限，非 root，替代 root 直连）
#   用户名: deepseek_app
#   密码:   部署时通过 environment 变量注入，不写入仓库
#   host: localhost
#   priv: ALL ON deepseek_chat.*
```

表结构（由后端启动时自动创建）：
- `users`：id / username(uniq) / hashed_password / created_at
- `sessions`：id / user_id(FK) / title / created_at
- `messages`：id / session_id(FK) / role / content / created_at

## 九、安全注意事项 ⚠️

1. **MySQL root 若使用弱口令，务必尽快修改**：
   ```bash
   mysql -uroot -p -e "ALTER USER 'root'@'localhost' IDENTIFIED BY '新的强密码';"
   # 同时更新 backend/.env 里的 DATABASE_URL
   ```
2. MySQL 监听在 `0.0.0.0:3306`，但阿里云安全组已拦截外网访问（实测公网 3306 不可达）。
   更稳妥的做法是改成只监听本机：编辑 `/etc/my.cnf` 增加 `bind-address = 127.0.0.1` 后重启 mysqld
3. `.env` 权限应收紧：`chmod 600 /opt/deepseekproject/backend/.env`
4. 建议后续接入 HTTPS：申请域名 + Let's Encrypt 证书，把 443 也放行
5. 当前站点为 HTTP 明文传输，登录密码在传输过程中未加密，正式对外请尽快上 HTTPS

## 十、已完成的验证

| 验证项 | 结果 |
| --- | --- |
| 公网首页 / 登录页 / SPA 路由 | 200 ✅ |
| 接口文档 /docs | 200 ✅ |
| 健康检查 | `{"status":"ok","database":"mysql/other"}` ✅ |
| 注册 → 登录 → 建会话 → 流式对话 → 落库 → 自动命名 | 全链路通过 ✅ |
| 未授权访问拦截 | 401 ✅ |
| 数据库表自动创建（MySQL） | 3 张表 ✅ |
| 服务器端单元测试 | 10 passed ✅ |
| 开机自启 | deepseek / nginx / mysqld 均 enabled ✅ |
| 内存占用 | uvicorn 约 99 MB ✅ |
