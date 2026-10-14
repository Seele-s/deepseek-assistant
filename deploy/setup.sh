#!/bin/bash
# ============================================================
#  DeepSeek 智能问答助手 —— 一键部署脚本
#  适用：Alibaba Cloud Linux 3 / CentOS 8 / RHEL 8 系（dnf）
#  用法：sudo bash setup.sh
#  说明：密钥不写死在脚本里，全部通过环境变量或交互输入获取
# ============================================================
set -e

APP_DIR=/opt/deepseekproject
SRC_DIR=$(cd "$(dirname "$0")/.." && pwd)          # 项目根目录

# ---------- 可配置项（也可用环境变量覆盖）----------
DB_NAME=${DB_NAME:-deepseek_chat}
DB_USER=${DB_USER:-deepseek_app}
DB_PASS=${DB_PASS:-}
GATEWAY_USER=${GATEWAY_USER:-admin}
GATEWAY_PASS=${GATEWAY_PASS:-}
PUBLIC_HOST=${PUBLIC_HOST:-$(curl -s --max-time 5 ifconfig.me || echo localhost)}

if [ -z "$DB_PASS" ] || [ -z "$GATEWAY_PASS" ]; then
  echo "用法：DB_PASS=xxx GATEWAY_PASS=yyy bash setup.sh"
  echo "  DB_PASS       应用专用数据库账号密码"
  echo "  GATEWAY_PASS  网站访问网关密码"
  echo "  DB_NAME/DB_USER/GATEWAY_USER/PUBLIC_HOST 可选"
  exit 1
fi

echo "===== 1. 安装运行环境（Python 3.11）====="
dnf install -y python3.11 python3.11-pip python3.11-devel nginx httpd-tools

echo "===== 2. 部署代码到 $APP_DIR ====="
mkdir -p $APP_DIR
cp -r "$SRC_DIR/backend" "$SRC_DIR/frontend" "$SRC_DIR/deploy" $APP_DIR/
[ -f "$SRC_DIR/README.md" ] && cp "$SRC_DIR/README.md" $APP_DIR/

echo "===== 3. 创建虚拟环境并安装依赖 ====="
cd $APP_DIR
python3.11 -m venv .venv
.venv/bin/python -m pip install -q --upgrade pip
.venv/bin/python -m pip install -q -r backend/requirements.txt

echo "===== 4. 配置环境变量（backend/.env）====="
if [ ! -f backend/.env ]; then
  cp backend/.env.example backend/.env
fi
sed -i "s|^DATABASE_URL=.*|DATABASE_URL=mysql+pymysql://$DB_USER:$DB_PASS@127.0.0.1:3306/$DB_NAME?charset=utf8mb4|" backend/.env
sed -i "s|^SECRET_KEY=.*|SECRET_KEY=$(openssl rand -hex 32)|" backend/.env
sed -i "s|^CORS_ORIGINS=.*|CORS_ORIGINS=http://$PUBLIC_HOST|" backend/.env
chmod 600 backend/.env
echo "  ⚠️  请手动编辑 backend/.env，填入 DEEPSEEK_API_KEY"

echo "===== 5. 创建数据库与最小权限账号 ====="
read -rsp "MySQL root 密码: " ROOT_PW; echo
mysql -uroot -p"$ROOT_PW" <<SQL
CREATE DATABASE IF NOT EXISTS $DB_NAME DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS '$DB_USER'@'localhost' IDENTIFIED BY '$DB_PASS';
GRANT ALL PRIVILEGES ON $DB_NAME.* TO '$DB_USER'@'localhost';
FLUSH PRIVILEGES;
SQL

echo "===== 6. 安装 systemd 服务 ====="
cp deploy/systemd/deepseek.service /etc/systemd/system/deepseek.service
systemctl daemon-reload
systemctl enable deepseek

echo "===== 7. 安装 Nginx 配置 ====="
# 限流 zone（写进 http 段，只需一次）
if ! grep -q "limit_req_zone.*deepseek_api" /etc/nginx/nginx.conf; then
  sed -i '/^http {/a\    limit_req_zone $binary_remote_addr zone=deepseek_api:10m rate=30r/m;' /etc/nginx/nginx.conf
fi
cp deploy/nginx/deepseek.conf /etc/nginx/conf.d/deepseek.conf

echo "===== 8. 生成访问网关密码 ====="
htpasswd -bc /etc/nginx/.htpasswd_deepseek "$GATEWAY_USER" "$GATEWAY_PASS"
chmod 640 /etc/nginx/.htpasswd_deepseek
chown root:nginx /etc/nginx/.htpasswd_deepseek 2>/dev/null || true

echo "===== 9. 安装维护页与一键启停工具 ====="
mkdir -p /var/www/maintenance
cp deploy/maintenance/index.html /var/www/maintenance/index.html
cp deploy/dsctl /usr/local/bin/dsctl && chmod +x /usr/local/bin/dsctl

echo "===== 10. 启动 ====="
nginx -t && systemctl reload nginx
systemctl restart deepseek
sleep 3
dsctl status

echo
echo "=============================================="
echo " 部署完成"
echo " 访问地址 : http://$PUBLIC_HOST"
echo " 网关账号 : $GATEWAY_USER"
echo
echo " 下一步：编辑 $APP_DIR/backend/.env 填入 DEEPSEEK_API_KEY，"
echo "         然后执行 systemctl restart deepseek"
echo "=============================================="
