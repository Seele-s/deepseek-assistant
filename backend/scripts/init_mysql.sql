-- 切换 MySQL 时在管理员命令行执行：
--   mysql -u root -p < backend/scripts/init_mysql.sql
CREATE DATABASE IF NOT EXISTS deepseek_chat
  DEFAULT CHARACTER SET utf8mb4
  DEFAULT COLLATE utf8mb4_unicode_ci;

-- 表结构由后端启动时自动创建（SQLAlchemy create_all）
-- 注意：跨用户级联删除需要外键约束生效，InnoDB 默认支持
