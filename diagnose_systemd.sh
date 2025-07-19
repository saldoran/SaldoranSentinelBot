#!/bin/bash

# Скрипт для диагностики проблем с systemd сервисом

echo "🔍 Диагностика systemd сервиса SaldoranBotSentinel..."
echo "=================================================="

# Проверяем статус сервиса
echo "📊 Статус сервиса:"
sudo systemctl status saldoran-sentinel --no-pager -l
echo ""

# Проверяем логи сервиса
echo "📋 Последние 50 строк логов сервиса:"
sudo journalctl -u saldoran-sentinel --no-pager -l -n 50
echo ""

# Проверяем системные логи на предмет ошибок
echo "⚠️  Системные ошибки связанные с сервисом:"
sudo journalctl --no-pager -l -n 100 | grep -i "saldoran-sentinel\|namespace\|permission"
echo ""

# Проверяем права доступа к файлам
echo "🔐 Проверка прав доступа:"
echo "Права на директорию проекта:"
ls -la /home/ubuntu/ | grep SaldoranSentinelBot
echo ""
echo "Права на main.py:"
ls -la /home/ubuntu/SaldoranSentinelBot/main.py
echo ""
echo "Права на виртуальное окружение:"
ls -la /home/ubuntu/SaldoranSentinelBot/venv/bin/python
echo ""

# Проверяем существование необходимых файлов
echo "📁 Проверка существования файлов:"
files=(
    "/home/ubuntu/SaldoranSentinelBot/main.py"
    "/home/ubuntu/SaldoranSentinelBot/venv/bin/python"
    "/home/ubuntu/SaldoranSentinelBot/.env"
    "/home/ubuntu/SaldoranSentinelBot/src/config.py"
)

for file in "${files[@]}"; do
    if [ -f "$file" ]; then
        echo "✅ $file - существует"
    else
        echo "❌ $file - НЕ НАЙДЕН"
    fi
done
echo ""

# Проверяем переменные окружения
echo "🌍 Переменные окружения в .env:"
if [ -f "/home/ubuntu/SaldoranSentinelBot/.env" ]; then
    echo "Файл .env найден, содержимое (без секретов):"
    grep -v "TOKEN\|SECRET\|PASSWORD" /home/ubuntu/SaldoranSentinelBot/.env || echo "Файл пустой или содержит только секреты"
else
    echo "❌ Файл .env не найден!"
fi
echo ""

# Проверяем Python зависимости
echo "🐍 Проверка Python зависимостей:"
/home/ubuntu/SaldoranSentinelBot/venv/bin/python -c "
import sys
print(f'Python версия: {sys.version}')
try:
    import telegram
    print(f'python-telegram-bot версия: {telegram.__version__}')
except ImportError as e:
    print(f'❌ Ошибка импорта telegram: {e}')

try:
    import psutil
    print(f'psutil версия: {psutil.__version__}')
except ImportError as e:
    print(f'❌ Ошибка импорта psutil: {e}')
"
echo ""

# Проверяем сетевые подключения
echo "🌐 Проверка сетевого подключения:"
echo "Проверка подключения к Telegram API:"
curl -s --connect-timeout 5 https://api.telegram.org/bot || echo "❌ Нет подключения к Telegram API"
echo ""

echo "✨ Диагностика завершена!"
echo "Если обнаружены проблемы, исправьте их и запустите ./fix_systemd.sh"