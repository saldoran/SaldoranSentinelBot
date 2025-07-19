#!/bin/bash

# Скрипт развертывания SaldoranBotSentinel
# Автор: Saldoran

set -e

echo "🚀 Развертывание SaldoranBotSentinel..."

# Проверяем, что мы в правильной директории
if [ ! -f "src/main.py" ]; then
    echo "❌ Ошибка: Запустите скрипт из корневой директории проекта"
    exit 1
fi

# Проверяем наличие Python 3
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 не найден. Установите Python 3.8+"
    exit 1
fi

# Создаем виртуальное окружение если не существует
if [ ! -d "venv" ]; then
    echo "📦 Создание виртуального окружения..."
    python3 -m venv venv
fi

# Активируем виртуальное окружение
echo "🔧 Активация виртуального окружения..."
source venv/bin/activate

# Устанавливаем зависимости
echo "📥 Установка зависимостей..."
pip install --upgrade pip
pip install -r requirements.txt

# Проверяем конфигурацию
echo "⚙️ Проверка конфигурации..."
if [ ! -f ".env" ]; then
    echo "❌ Файл .env не найден. Создайте его на основе примера в README.md"
    exit 1
fi

# Валидируем конфигурацию
python -c "from src.config import Config; Config.validate(); print('✅ Конфигурация валидна')"

# Создаем необходимые директории
echo "📁 Создание директорий..."
python -c "from src.config import Config; Config.create_directories(); print('✅ Директории созданы')"

# Создаем директорию для ботов если не существует
mkdir -p ~/bots

# Копируем тестового бота если директория пуста
if [ ! -d "~/bots/shadowshort" ] && [ -d "test_bot/shadowshort" ]; then
    echo "🤖 Копирование тестового бота..."
    cp -r test_bot/shadowshort ~/bots/
    chmod +x ~/bots/shadowshort/*.sh
    echo "✅ Тестовый бот shadowshort скопирован в ~/bots/"
fi

# Настройка systemd сервиса
echo "🔧 Настройка systemd сервиса..."
if [ -f "systemd/saldoran-sentinel.service" ]; then
    # Обновляем пути в сервисе
    CURRENT_DIR=$(pwd)
    sed "s|/home/ubuntu/SaldoranSentinelBot|$CURRENT_DIR|g" systemd/saldoran-sentinel.service > /tmp/saldoran-sentinel.service
    
    sudo cp /tmp/saldoran-sentinel.service /etc/systemd/system/
    sudo systemctl daemon-reload
    sudo systemctl enable saldoran-sentinel
    echo "✅ Systemd сервис настроен"
else
    echo "⚠️ Файл systemd сервиса не найден"
fi

# Проверяем sudo права для очистки кэша
echo "🔐 Проверка sudo прав для очистки кэша..."
if sudo -n sysctl -w vm.drop_caches=3 >/dev/null 2>&1; then
    echo "✅ Sudo права для очистки кэша настроены"
else
    echo "⚠️ Необходимо настроить sudo права для очистки кэша:"
    echo "   sudo visudo"
    echo "   Добавьте строку: $USER ALL=(ALL) NOPASSWD: /sbin/sysctl -w vm.drop_caches=3"
fi

# Тестовый запуск
echo "🧪 Тестовый запуск..."
timeout 10s python -m src.main || true

echo ""
echo "🎉 Развертывание завершено!"
echo ""
echo "📋 Следующие шаги:"
echo "1. Убедитесь, что настроены sudo права для очистки кэша"
echo "2. Запустите сервис: sudo systemctl start saldoran-sentinel"
echo "3. Проверьте статус: sudo systemctl status saldoran-sentinel"
echo "4. Просмотрите логи: sudo journalctl -u saldoran-sentinel -f"
echo ""
echo "📱 Telegram команды:"
echo "   /start - Запуск бота"
echo "   /list - Список ботов"
echo "   /status - Статус системы"
echo "   /help - Справка"
echo ""
echo "✅ SaldoranBotSentinel готов к работе!"