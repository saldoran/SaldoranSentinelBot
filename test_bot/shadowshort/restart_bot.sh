#!/bin/bash

# Скрипт перезапуска тестового бота shadowshort

BOT_NAME="shadowshort"
SCRIPT_DIR="$(dirname "$0")"

echo "Перезапуск бота $BOT_NAME..."

# Останавливаем бот
echo "Остановка бота..."
"$SCRIPT_DIR/stop_bot.sh"

# Ждем немного
sleep 2

# Запускаем бот
echo "Запуск бота..."
"$SCRIPT_DIR/run_bot.sh"

if [ $? -eq 0 ]; then
    echo "Бот $BOT_NAME успешно перезапущен"
    exit 0
else
    echo "Ошибка при перезапуске бота $BOT_NAME"
    exit 1
fi