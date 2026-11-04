# Vercel + Neon 部署

## 导入设置

仓库根目录 `./`，Application Preset 选择 `Services`。根目录的
`vercel.json` 定义两个服务：`app` 为 Flask，`frontend` 为 Vite。
`/api/:path*` 公开路由到 Flask，保留 `/api/v1/...` 原始路径；其余请求进入
Vite，前端服务中的 SPA rewrite 支持刷新 `/login`、`/items` 等页面。
浏览器直接请求同域名 `/api/v1`；没有服务端调用另一个内部服务，因此无需 bindings。
本地 Vite proxy 不作为线上代理。

## 部署前环境变量

- `DATABASE_URL`：Neon 的完整 PostgreSQL 连接字符串，建议使用 pooled 地址，保留 SSL 参数。
- `SECRET_KEY`：独立随机密钥，至少 32 字符。
- `JWT_SECRET_KEY`：另一份独立随机密钥，至少 32 字符。重新部署时保持不变。

可在本地 Python 中运行两次 `python -c "import secrets; print(secrets.token_hex(32))"`
生成密钥，分别填入 Vercel。不要上传含这些值的文件，也不要分享连接字符串。
同域部署不需要另填 CORS_ORIGINS；如采用其他前端域名再设置该允许来源。
不要用 `VITE_` 前缀存储数据库地址或密钥，它们只供后端使用。

当前界面同时勾选 Production 和 Preview 时，两者会使用同一个数据库；正式使用前
应给 Preview 配置单独的 Neon 数据库/分支，避免测试数据影响正式数据。

## 首次建表与验证

后端 buildCommand 运行 `python deploy_db.py`，只在配置的 PostgreSQL 中创建缺失表，
不删除表、不插入演示账号、不导入本地 SQLite。再次执行不会清空已有数据。
首次部署是空数据库，部署完成后通过网页注册新账号。
以后修改已有表结构应使用专门的迁移，create_all 不会更新已有列。
如果此前已创建 128 字符 password_hash 的 PostgreSQL 表，应在正式迁移中扩展到 255。

部署后验证：`/api/v1/health` 返回 JSON；直接打开并刷新 `/login`；注册、登录、
发布商品，再重新打开页面确认数据持久保存。未连接真实 Neon 前，本地测试不能证明
线上连接成功。

## 功能边界

本地 SQLite 文件原样保留，旧账号、商品、消息等不会自动迁移。本地仍可通过原启动器运行。
离线 mDeBERTa 模型与 ML 依赖未上传；云端智能分类只能在词库足够明确时降级给建议，
其余情况需手动选择，不影响常规发布。
现有 JWT 注销使用进程内存，多实例注销一致性仍是原有实现限制。
当前购买/租赁通过联系物主协商；部署不增加支付或原项目未实现的业务功能。
