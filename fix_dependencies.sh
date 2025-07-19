#!/bin/bash

# Скрипт для исправления проблем с зависимостями python-telegram-bot

echo "🔧 Исправление зависимостей SaldoranBotSentinel..."

# Проверяем виртуальное окружение
if [ ! -d "venv" ]; then
    echo "❌ Виртуальное окружение не найдено. Создаем новое..."
    python3 -m venv venv
fi

# Активируем виртуальное окружение
echo "🔄 Активация виртуального окружения..."
source venv/bin/activate

# Удаляем старые версии
echo "🗑️ Удаление старых версий python-telegram-bot..."
pip uninstall -y python-telegram-bot

# Очищаем кэш pip
echo "🧹 Очистка кэша pip..."
pip cache purge

# Обновляем pip
echo "⬆️ Обновление pip..."
pip install --upgrade pip

# Устанавливаем точные версии зависимостей
echo "📦 Установка зависимостей..."
pip install "python-telegram-bot>=22.1"
pip install "psutil>=5.9.0"
pip install "python-dotenv>=1.0.0"

# Проверяем установку
echo "✅ Проверка установленных пакетов:"
pip list | grep -E "(python-telegram-bot|psutil|python-dotenv)"

echo ""
echo "🎉 Исправление зависимостей завершено!"
echo ""
echo "Теперь можно запустить:"
echo "  source venv/bin/activate"
echo "  python -m src.main"