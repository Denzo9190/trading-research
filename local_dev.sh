#!/bin/bash
# Скрипт для локальной разработки: останавливает сервисы на сервере,
# запускает локального бота, после завершения обновляет код и перезапускает сервисы.

SERVER_IP="141.147.21.46"            # твой публичный IP
SSH_KEY="$HOME/.ssh/id_rsa"          # путь к приватному ключу
REMOTE_PATH="~/trading-research"     # путь к проекту на сервере

echo "🛑 Останавливаем сервисы на сервере..."
ssh -i "$SSH_KEY" ubuntu@$SERVER_IP "sudo systemctl stop tv-alert.service email-listener.service"

echo "🚀 Запускаем локального бота (Ctrl+C для остановки)..."
cd "$(dirname "$0")"
source venv/bin/activate
python telegram_intelligence/tv_alert_relay/tv_alert_handler.py

echo "🔄 Обновляем код на сервере и перезапускаем сервисы..."
ssh -i "$SSH_KEY" ubuntu@$SERVER_IP "cd $REMOTE_PATH && git pull && sudo systemctl start tv-alert.service email-listener.service"

echo "✅ Готово."