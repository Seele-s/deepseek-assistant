# DeepSeek 智能问答助手

基于 DeepSeek 大模型的智能对话系统，前后端分离架构。
支持多轮对话、SSE 流式输出、深度思考（R1 思维链）、Markdown/LaTeX 渲染、文件上传分析。

> 组员：张宇航（组长）、朱友成 ｜ 原始版本 2025.12 - 2026.01
> 当前版本：v2.0（完成工程化重构）

---

## 一、技术栈

| 层次 | 技术 |
| --- | --- |
| 前端 | Vue 3 + Vite + Pinia + Vue Router + TDesign + markdown-it + highlight.js + KaTeX |
| 后端 | FastAPI + SQLAlchemy 2.x + Pydantic + Uvicorn |
| 数据库 | SQLite（默认，开箱即用）/ MySQL（可一键切换） |
| 鉴权 | JWT（python-jose）+ bcrypt 密码哈希 |
| AI | OpenAI 兼容接口 + DeepSeek 模型（deepseek-v4.1-flash），AsyncOpenAI 异步 SDK |

## 二、核心功能

1. **用户体系**：注册、登录、JWT 无状态鉴权，接口级权限校验
2. **会话管理**：多会话增删改查，历史记录持久化，首条消息自动命名
3. **流式对话**：SSE 逐字输出，首字响应快，不阻塞界面
4. **深度思考模式**：调用 `deepseek-reasoner`，单独展示思维链过程
5. **富文本渲染**：Markdown、代码高亮（含一键复制）、LaTeX 公式
6. **文件分析**：上传文本/代码文件，AI 基于文件内容作答

## 三、目录结构

```
deepseekproject/
├── backend/
│   ├── app/
│   │   ├── main.py          # 应用入口：装配路由、中间件、静态资源
│   │   ├── config.py        # 集中配置（全部读环境变量）
│   │   ├── database.py      # 数据库引擎与会话
│   │   ├── models.py        # 数据模型：User / ChatSession / ChatMessage
│   │   ├── schemas.py       # Pydantic 请求/响应模型
│   │   ├── security.py      # bcrypt 密码哈希 + JWT 签发校验
│   │   ├── deps.py          # 公共依赖：get_db / get_current_user
│   │   ├── routers/         # 路由层：auth / sessions / chat / files
│   │   └── services/        # 业务层：llm（模型调用）/ context（上下文裁剪）
│   ├── tests/               # pytest 接口测试（10 个用例）
│   ├── requirements.txt
│   ├── .env.example         # 配置模板（真实配置在 .env，已被 gitignore）
│   ├── run.py               # python run.py 启动
│   └── legacy_original/     # 重构前的原始代码备份
├── frontend/
│   ├── src/api/index.js     # 统一 API 层（杜绝 URL 硬编码）
│   ├── src/views/           # login / chatlayout
│   ├── src/components/      # ChatWindow（对话主界面）
│   ├── src/stores/user.js   # Pinia 用户状态
│   └── dist/                # 构建产物，由后端同源托管
├── start.ps1                # 一键启动
├── build-frontend.ps1       # 重新构建前端
└── dev-frontend.ps1         # 前端开发模式（热更新）
```

## 四、快速开始

### 1. 启动服务（已配置完毕，直接运行）

```powershell
.\start.ps1
```

打开浏览器访问 **http://127.0.0.1:8000**

- 接口文档（Swagger）：http://127.0.0.1:8000/docs
- 健康检查：http://127.0.0.1:8000/api/health

### 2. 前端开发模式（需要改 Vue 界面时）

```powershell
.\dev-frontend.ps1          # 访问 http://localhost:5173
.\build-frontend.ps1        # 改完后重新打包
```

### 3. 从零部署（换电脑时）

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
cd frontend; npm install; npm run build
cd ..; .\start.ps1
```

## 五、配置说明（backend/.env）

| 变量 | 说明 | 默认值 |
| --- | --- | --- |
| `DEEPSEEK_API_KEY` | DeepSeek 密钥，**必须填** | 无 |
| `SECRET_KEY` | JWT 签名密钥 | 需自行设置 |
| `DATABASE_URL` | 数据库连接串 | SQLite |
| `MAX_CONTEXT_MESSAGES` | 上下文保留的最大历史条数 | 20 |
| `MAX_CONTEXT_CHARS` | 上下文最大字符预算 | 24000 |
| `MAX_UPLOAD_MB` | 上传文件大小上限 | 20 |
| `CORS_ORIGINS` | 允许跨域的来源白名单 | localhost |

### 切换到 MySQL

```powershell
# 1. 以管理员身份启动 MySQL 服务
Start-Service MYSQL80

# 2. 建库
mysql -u root -p < backend\scripts\init_mysql.sql

# 3. 在 backend/.env 中放开并修改这一行
DATABASE_URL=mysql+pymysql://root:你的密码@127.0.0.1:3306/deepseek_chat?charset=utf8mb4

# 4. 重启服务，表结构会自动创建
```

## 六、接口一览

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| POST | `/api/register` | 注册 |
| POST | `/api/token` | 登录，返回 JWT |
| GET | `/api/me` | 当前用户信息 |
| GET | `/api/sessions` | 会话列表 |
| POST | `/api/sessions` | 新建会话 |
| PATCH | `/api/sessions/{id}` | 重命名会话 |
| DELETE | `/api/sessions/{id}` | 删除会话（级联删除消息） |
| GET | `/api/sessions/{id}/messages` | 历史消息 |
| POST | `/api/chat` | 对话（SSE 流式） |
| POST | `/api/upload` | 上传附件 |
| GET | `/api/health` | 健康检查 |

## 七、测试

```powershell
cd backend
..\.venv\Scripts\python.exe -m pytest tests -q
```

覆盖：健康检查、注册登录、重复用户名、弱密码校验、未授权拦截、
会话增删改查、**跨用户越权防护**、上传类型白名单、上下文裁剪。

## 八、安全说明

- 密码使用 bcrypt 加盐哈希存储，不存明文
- 所有会话/消息查询均带 `user_id` 过滤，防止越权访问
- 文件上传有扩展名白名单与大小限制，读取时做路径穿越校验
- CORS 使用来源白名单，不再使用 `*`
- 前端 Markdown 关闭原始 HTML 渲染，规避 XSS
- **`.env` 内含密钥，已被 .gitignore 排除，切勿提交或打包外发**

---

## 九、v2.0 相对 v1.0 的改动

| 类别 | v1.0 | v2.0 |
| --- | --- | --- |
| 后端结构 | 223 行全挤在 main.py | routers / services / schemas 分层 |
| 配置 | 硬编码、密钥入库 | config.py + .env 集中管理 |
| 数据库 | 固定 SQLite | SQLite 默认 + MySQL 可切换 |
| 上下文 | 全量塞给模型（易超限） | 滑动窗口 + 字符预算裁剪 |
| 会话标题 | 手动弹窗输入 | 首条消息自动命名 |
| 前端请求 | URL 硬编码在 4 个文件 | 统一 api 层 + 环境变量 |
| 参数校验 | 无 | Pydantic 校验（长度、类型） |
| 文件上传 | 任意类型任意大小 | 白名单 + 20MB 上限 |
| 错误处理 | 静默失败 | 统一异常提示 |
| 安全 | CORS `*`、HTML 未过滤 | 来源白名单、XSS 防护、越权测试 |
| 测试 | 无 | 10 个 pytest 用例 |
| 部署 | 手动开两个终端 | 单端口一键启动脚本 |
| 文档 | 无 README | 完整 README + Swagger |
