#!/bin/bash

# Скрипт запуска тестового бота shadowshort
# Этот скрипт имитирует запуск бота для тестирования SaldoranBotSentinel

BOT_NAME="shadowshort"
PID_FILE="/tmp/${BOT_NAME}.pid"
LOG_DIR="$(dirname "$0")/logs"

# Создаем директорию для логов если не существует
mkdir -p "$LOG_DIR"

# Проверяем, не запущен ли уже бот
if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if ps -p "$PID" > /dev/null 2>&1; then
        echo "Бот $BOT_NAME уже запущен (PID: $PID)"
        exit 1
    else
        # Удаляем старый PID файл
        rm -f "$PID_FILE"
    fi
fi

echo "Запуск бота $BOT_NAME..."

# Имитируем работу бота через бесконечный цикл
# В реальности здесь был бы запуск Python скрипта бота
nohup bash -c '
    while true; do
        echo "$(date): Bot shadowshort is running..." >> "'$LOG_DIR'/bot.log"
        sleep 30
    done
' > "$LOG_DIR/output.log" 2>&1 &

# Сохраняем PID
echo $! > "$PID_FILE"

echo "Бот $BOT_NAME запущен (PID: $!)"
echo "Логи: $LOG_DIR/"