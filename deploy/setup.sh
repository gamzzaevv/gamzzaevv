#!/usr/bin/env bash
# =============================================================
# Скрипт установки MMA Start на reg.ru VPS (Ubuntu 22.04/24.04)
# Запуск: sudo bash setup.sh
# =============================================================
set -euo pipefail

PROJECT_DIR="/var/www/mmastart"
PROJECT_USER="mmastart"
PYTHON_VERSION="3.12"
DOMAIN="mmastart.ru"

echo "==> [1/9] Обновляем пакеты и ставим зависимости..."
apt-get update -q
apt-get install -y --no-install-recommends \
    python${PYTHON_VERSION} python${PYTHON_VERSION}-venv python${PYTHON_VERSION}-dev \
    python3-pip \
    build-essential pkg-config \
    default-libmysqlclient-dev \
    libffi-dev libssl-dev \
    libcairo2 libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf2.0-0 \
    nginx \
    redis-server \
    mysql-server \
    certbot python3-certbot-nginx \
    git curl

echo "==> [2/9] Создаём системного пользователя ${PROJECT_USER}..."
if ! id "${PROJECT_USER}" &>/dev/null; then
    useradd --system --create-home --shell /bin/bash "${PROJECT_USER}"
fi

echo "==> [3/9] Создаём директории проекта..."
mkdir -p "${PROJECT_DIR}" /var/log/mmastart
chown -R "${PROJECT_USER}:${PROJECT_USER}" "${PROJECT_DIR}" /var/log/mmastart

echo "==> [4/9] Копируем файлы проекта..."
# Если запускаете из директории с архивом:
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "${SCRIPT_DIR}")"
rsync -a --exclude='.git' --exclude='__pycache__' --exclude='*.pyc' \
    --exclude='venv' --exclude='staticfiles' --exclude='media' \
    --exclude='db.sqlite3' \
    "${PROJECT_ROOT}/" "${PROJECT_DIR}/"
chown -R "${PROJECT_USER}:${PROJECT_USER}" "${PROJECT_DIR}"

echo "==> [5/9] Создаём .env из шаблона..."
if [ ! -f "${PROJECT_DIR}/.env" ]; then
    cp "${PROJECT_DIR}/.env.example" "${PROJECT_DIR}/.env"
    # Генерируем случайный SECRET_KEY
    SECRET=$(python3 -c "import secrets,string; print(''.join(secrets.choice(string.ascii_letters+string.digits+'!@#%^&*(-_=+)') for _ in range(50)))")
    sed -i "s|change-me-to-50-random-chars|${SECRET}|" "${PROJECT_DIR}/.env"
    echo ""
    echo "  !! Откройте ${PROJECT_DIR}/.env и заполните:"
    echo "     DATABASE_URL, YOOKASSA_*, EMAIL_*, REDIS_URL"
    echo "  Нажмите Enter когда будете готовы..."
    read -r
fi

echo "==> [6/9] Настраиваем MySQL..."
mysql -u root <<EOF
CREATE DATABASE IF NOT EXISTS ticket_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS 'ticket_user'@'localhost' IDENTIFIED BY 'CHANGE_ME_PASSWORD';
GRANT ALL PRIVILEGES ON ticket_db.* TO 'ticket_user'@'localhost';
FLUSH PRIVILEGES;
EOF
echo "  !! Обязательно смените пароль ticket_user в MySQL и обновите DATABASE_URL в .env"

echo "==> [7/9] Настраиваем Python virtualenv и устанавливаем зависимости..."
sudo -u "${PROJECT_USER}" python${PYTHON_VERSION} -m venv "${PROJECT_DIR}/venv"
sudo -u "${PROJECT_USER}" "${PROJECT_DIR}/venv/bin/pip" install --upgrade pip wheel
sudo -u "${PROJECT_USER}" "${PROJECT_DIR}/venv/bin/pip" install -r "${PROJECT_DIR}/requirements/production.txt"

echo "==> Применяем миграции и собираем статику..."
cd "${PROJECT_DIR}"
sudo -u "${PROJECT_USER}" "${PROJECT_DIR}/venv/bin/python" manage.py migrate --noinput
sudo -u "${PROJECT_USER}" "${PROJECT_DIR}/venv/bin/python" manage.py collectstatic --noinput
sudo -u "${PROJECT_USER}" "${PROJECT_DIR}/venv/bin/python" manage.py createsuperuser

echo "==> [8/9] Устанавливаем systemd-сервисы..."
DEPLOY_DIR="${PROJECT_DIR}/deploy"
cp "${DEPLOY_DIR}/gunicorn.service"      /etc/systemd/system/mmastart-gunicorn.service
cp "${DEPLOY_DIR}/celery_worker.service" /etc/systemd/system/mmastart-celery-worker.service
cp "${DEPLOY_DIR}/celery_beat.service"   /etc/systemd/system/mmastart-celery-beat.service

systemctl daemon-reload
systemctl enable  mmastart-gunicorn mmastart-celery-worker mmastart-celery-beat
systemctl start   mmastart-gunicorn mmastart-celery-worker mmastart-celery-beat

echo "==> [9/9] Настраиваем nginx и SSL (Let's Encrypt)..."
cp "${DEPLOY_DIR}/nginx.conf" /etc/nginx/sites-available/${DOMAIN}
ln -sf /etc/nginx/sites-available/${DOMAIN} /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl reload nginx

# Выдаём SSL-сертификат (домен уже должен указывать на этот сервер)
certbot --nginx -d ${DOMAIN} -d www.${DOMAIN} --non-interactive --agree-tos --email admin@${DOMAIN} --redirect || \
    echo "  !! SSL не удалось получить автоматически. Запустите вручную: certbot --nginx -d ${DOMAIN} -d www.${DOMAIN}"

echo ""
echo "======================================================"
echo " Готово! Сайт должен открываться на https://${DOMAIN}"
echo " Логи: journalctl -u mmastart-gunicorn -f"
echo "======================================================"
