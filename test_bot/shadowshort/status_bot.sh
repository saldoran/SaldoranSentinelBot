#!/bin/bash

# Скрипт проверки статуса тестового бота shadowshort

BOT_NAME="shadowshort"
PID_FILE="/tmp/${BOT_NAME}.pid"
LOG_DIR="$(dirname "$0")/logs"

echo "=== Статус бота $BOT_NAME ==="

# Проверяем PID файл
if [ ! -f "$PID_FILE" ]; then
    echo "Статус: ОСТАНОВЛЕН (PID файл не найден)"
    exit 1
fi

# Читаем PID
PID=$(cat "$PID_FILE")

# Проверяем, существует ли процесс
if ps -p "$PID" > /dev/null 2>&1; then
    echo "Статус: ЗАПУЩЕН"
    echo "PID: $PID"
    
    # Показываем информацию о процессе
    echo "Информация о процессе:"
    ps -p "$PID" -o pid,ppid,cmd,etime,%cpu,%mem
    
    # Показываем размер логов если есть
    if [ -d "$LOG_DIR" ]; then
        LOG_SIZE=$(du -sh "$LOG_DIR" 2>/dev/null | cut -f1)
        echo "Размер логов: $LOG_SIZE"
        
        # Показываем последние строки лога
        if [ -f "$LOG_DIR/bot.log" ]; then
            echo "Последние записи в логе:"
            tail -n 3 "$LOG_DIR/bot.log"
        fi
    fi
    
    exit 0
else
    echo "Статус: ОСТАНОВЛЕН (процесс с PID $PID не найден)"
    # Удаляем устаревший PID файл
    rm -f "$PID_FILE"
    exit 1
fi