#!/usr/bin/env bash
# Установка и обновление АЭРОХАБ на VPS с Ubuntu (запускается от root).
#
#   bash install.sh <архив.tar.gz | папка с git clone> [домен]
#
# Первый запуск: ставит Python, nginx и certbot, спрашивает почту и пароль администратора,
# настраивает автозапуск и HTTPS. Повторный запуск — обновление кода:
# база (aerohub.db), файлы заказов (media/) и настройки (/etc/aerohub.env) не трогаются.
set -euo pipefail

SOURCE="${1:?Укажите архив сайта или папку с клоном репозитория}"
DOMAIN="${2:-aerohub63.ru}"
APP_DIR=/opt/aerohub
APP_USER=aerohub
ENV_FILE=/etc/aerohub.env

say() { printf '\n\033[1;33m==> %s\033[0m\n' "$*"; }

# Кавычки, обратная косая черта и пробелы ломают файл настроек systemd
password_ok() {
  case "$1" in
    *'"'* | *"'"* | *'\'* | *' '*) return 1 ;;
  esac
}

[ "$(id -u)" -eq 0 ] || { echo 'Запустите от root'; exit 1; }

say 'Пакеты: Python, nginx, certbot'
export DEBIAN_FRONTEND=noninteractive
apt-get update -q
apt-get install -y -q python3 python3-venv nginx certbot python3-certbot-nginx

say 'Системный пользователь сайта'
id "$APP_USER" >/dev/null 2>&1 || useradd --system --home "$APP_DIR" --shell /usr/sbin/nologin "$APP_USER"

say "Код сайта → $APP_DIR"
mkdir -p "$APP_DIR"
# Старый код убираем целиком, чтобы не оставались удалённые файлы; база и media лежат рядом и не затрагиваются.
rm -rf "$APP_DIR/app" "$APP_DIR/data" "$APP_DIR/deploy"
if [ -d "$SOURCE" ]; then
  cp -r "$SOURCE/app" "$SOURCE/data" "$SOURCE/requirements.txt" "$APP_DIR/"
else
  tar -xzf "$SOURCE" -C "$APP_DIR"
fi
find "$APP_DIR/app" -name __pycache__ -type d -prune -exec rm -rf {} +

say 'Виртуальное окружение и зависимости'
[ -x "$APP_DIR/.venv/bin/python" ] || python3 -m venv "$APP_DIR/.venv"
"$APP_DIR/.venv/bin/pip" install -q --upgrade pip
"$APP_DIR/.venv/bin/pip" install -q -r "$APP_DIR/requirements.txt"

if [ ! -f "$ENV_FILE" ]; then
  say 'Настройки (только при первой установке)'
  read -rp  'Почта администратора [admin@aerohub.ru]: ' ADMIN_EMAIL
  ADMIN_EMAIL="${ADMIN_EMAIL:-admin@aerohub.ru}"
  while true; do
    read -rsp 'Пароль администратора (от 8 символов): ' ADMIN_PASSWORD; echo
    read -rsp 'Повторите пароль: ' ADMIN_PASSWORD2; echo
    if [ "${#ADMIN_PASSWORD}" -ge 8 ] && [ "$ADMIN_PASSWORD" = "$ADMIN_PASSWORD2" ] \
       && password_ok "$ADMIN_PASSWORD"; then
      break
    fi
    echo 'Пароли не совпадают, короче 8 символов или содержат кавычки, \ или пробел — ещё раз.'
  done
  read -rp  'Код приглашения для регистрации сотрудников [случайный]: ' STAFF_CODE
  STAFF_CODE="${STAFF_CODE:-$(openssl rand -hex 4 | tr a-f A-F)}"
  umask 077
  cat > "$ENV_FILE" <<EOF
AEROHUB_SECRET_KEY=$(openssl rand -hex 32)
AEROHUB_ADMIN_EMAIL=$ADMIN_EMAIL
AEROHUB_ADMIN_PASSWORD=$ADMIN_PASSWORD
AEROHUB_STAFF_CODE=$STAFF_CODE
EOF
  umask 022
  echo "Код приглашения сотрудников: $STAFF_CODE (хранится в $ENV_FILE)"
fi

chown -R "$APP_USER:$APP_USER" "$APP_DIR"
chmod 755 "$APP_DIR"
chmod -R a+rX "$APP_DIR/app/static"   # статику отдаёт nginx

say 'Автозапуск (systemd)'
cat > /etc/systemd/system/aerohub.service <<EOF
[Unit]
Description=AEROHUB portal (FastAPI)
After=network.target

[Service]
User=$APP_USER
Group=$APP_USER
WorkingDirectory=$APP_DIR
EnvironmentFile=$ENV_FILE
# Один процесс: база SQLite, начальное наполнение идёт при старте
ExecStart=$APP_DIR/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --proxy-headers --forwarded-allow-ips=127.0.0.1
Restart=always
RestartSec=3
# База и загруженные файлы не читаются другими пользователями сервера
UMask=0027

[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload
systemctl enable aerohub >/dev/null
systemctl restart aerohub

say "nginx для $DOMAIN"
# Если сертификат уже выпущен, certbot сам дописал HTTPS в этот файл — не перезаписываем его при обновлении.
if [ ! -f /etc/nginx/sites-available/aerohub ] || ! grep -q 'ssl_certificate' /etc/nginx/sites-available/aerohub; then
  cat > /etc/nginx/sites-available/aerohub <<EOF
server {
    listen 80;
    listen [::]:80;
    server_name $DOMAIN www.$DOMAIN;

    # Файлы заказов — до 25 МБ
    client_max_body_size 30m;

    location /static/ {
        alias $APP_DIR/app/static/;
        expires 7d;
        access_log off;
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 60s;
    }
}
EOF
fi
ln -sf /etc/nginx/sites-available/aerohub /etc/nginx/sites-enabled/aerohub
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl reload nginx

if command -v ufw >/dev/null && ufw status | grep -q 'Status: active'; then
  ufw allow 'Nginx Full' >/dev/null
fi

say 'Проверка сайта'
for _ in $(seq 1 30); do
  curl -fsS -o /dev/null http://127.0.0.1:8000/contacts && break
  sleep 1
done
if curl -fsS -o /dev/null http://127.0.0.1:8000/contacts; then
  echo 'Сайт запущен.'
else
  echo 'Сайт не отвечает. Журнал: journalctl -u aerohub -n 50'
  exit 1
fi

if [ ! -d "/etc/letsencrypt/live/$DOMAIN" ]; then
  say 'HTTPS-сертификат Let'"'"'s Encrypt'
  ADMIN_EMAIL_FOR_CERT="$(grep '^AEROHUB_ADMIN_EMAIL=' "$ENV_FILE" | cut -d= -f2-)"
  if certbot --nginx -n --agree-tos --redirect -m "$ADMIN_EMAIL_FOR_CERT" -d "$DOMAIN" -d "www.$DOMAIN"; then
    echo "HTTPS включён: https://$DOMAIN"
  else
    echo "Сертификат не выпущен — скорее всего, домен ещё не смотрит на этот сервер (DNS обновляется до 24 ч)."
    echo "Сайт уже работает по http://$DOMAIN. Когда DNS обновится, выполните:"
    echo "  certbot --nginx --redirect -d $DOMAIN -d www.$DOMAIN"
  fi
fi

say "Готово: https://$DOMAIN"
