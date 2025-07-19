#!/bin/bash

# Скрипт для исправления systemd сервиса на EC2

echo "🔧 Исправление systemd сервиса SaldoranBotSentinel..."

# Проверяем, что мы в правильной директории
if [ ! -f "systemd/saldoran-sentinel.service" ]; then
    echo "❌ Ошибка: файл systemd/saldoran-sentinel.service не найден"
    echo "Убедитесь, что вы находитесь в директории SaldoranSentinelBot"
    exit 1
fi

# Останавливаем сервис
echo "⏹️  Остановка сервиса..."
sudo systemctl stop saldoran-sentinel

# Копируем обновленный файл сервиса
echo "📋 Копирование обновленного файла сервиса..."
sudo cp systemd/saldoran-sentinel.service /etc/systemd/system/

# Перезагружаем systemd
echo "🔄 Перезагрузка systemd daemon..."
sudo systemctl daemon-reload

# Включаем сервис для автозапуска
echo "✅ Включение автозапуска сервиса..."
sudo systemctl enable saldoran-sentinel

# Запускаем сервис
echo "🚀 Запуск сервиса..."
sudo systemctl start saldoran-sentinel

# Ждем немного для инициализации
sleep 3

# Проверяем статус
echo "📊 Проверка статуса сервиса..."
sudo systemctl status saldoran-sentinel --no-pager -l

echo ""
echo "🔍 Последние логи сервиса:"
sudo journalctl -u saldoran-sentinel --no-pager -l -n 20

echo ""
echo "✨ Готово! Если сервис запустился успешно, проверьте Telegram бота."
echo "📱 Отправьте команду /start в Telegram для проверки работы."