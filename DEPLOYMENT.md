# 🚀 Развертывание SaldoranSentinelBot на EC2

## Быстрое развертывание

### 1. Подключение к серверу
```bash
ssh -i your-key.pem ubuntu@your-ec2-ip
```

### 2. Клонирование проекта
```bash
git clone <your-repo-url> SaldoranSentinelBot
cd SaldoranSentinelBot
```

### 3. Настройка конфигурации
```bash
# Копируем пример конфигурации
cp .env.example .env

# Редактируем конфигурацию
nano .env
```

**Обязательно укажите:**
- `TELEGRAM_BOT_TOKEN` - токен вашего Telegram бота
- `TELEGRAM_ADMIN_ID` - ваш Telegram ID

### 4. Автоматическое развертывание
```bash
chmod +x deploy.sh
./deploy.sh
```

### 5. Запуск сервиса
```bash
# Запуск
sudo systemctl start saldoran-sentinel

# Проверка статуса
sudo systemctl status saldoran-sentinel

# Просмотр логов
sudo journalctl -u saldoran-sentinel -f
```

## Управление сервисом

```bash
# Остановка
sudo systemctl stop saldoran-sentinel

# Перезапуск
sudo systemctl restart saldoran-sentinel

# Отключение автозапуска
sudo systemctl disable saldoran-sentinel

# Включение автозапуска
sudo systemctl enable saldoran-sentinel
```

## Telegram команды

- `/start` - Запуск бота
- `/help` - Справка по командам
- `/status` - Статус системы
- `/bots` - Управление ботами
- `/resources` - Мониторинг ресурсов
- `/logs` - Просмотр логов

## Структура директорий на сервере

```
/home/ubuntu/
├── SaldoranSentinelBot/     # Основной проект
│   ├── src/                 # Исходный код
│   ├── logs/                # Логи системы
│   ├── venv/                # Виртуальное окружение
│   └── .env                 # Конфигурация
└── bots/                    # Директория ваших ботов
    └── shadowshort/         # Тестовый бот (пример)
```

## Добавление своих ботов

1. Создайте директорию в `~/bots/your-bot-name/`
2. Добавьте скрипты:
   - `run_bot.sh` - запуск бота
   - `stop_bot.sh` - остановка бота
   - `status_bot.sh` - проверка статуса
   - `restart_bot.sh` - перезапуск (опционально)

3. Сделайте скрипты исполняемыми:
```bash
chmod +x ~/bots/your-bot-name/*.sh
```

## Мониторинг

- **Логи системы**: `~/SaldoranSentinelBot/logs/`
- **Systemd логи**: `sudo journalctl -u saldoran-sentinel`
- **Статус через Telegram**: команда `/status`

## Безопасность

- Сервис запускается под пользователем `ubuntu`
- Ограниченные права доступа к файловой системе
- Логи ротируются ежедневно
- Автоматический перезапуск при сбоях

## Устранение неполадок

### ❌ Ошибка systemd status=226/NAMESPACE
Если сервис не запускается с ошибкой `status=226/NAMESPACE`, выполните:

```bash
# 1. Диагностика проблемы
cd ~/SaldoranSentinelBot
./diagnose_systemd.sh

# 2. Исправление конфигурации systemd
./fix_systemd.sh
```

**Альтернативное решение вручную:**
```bash
# Остановить сервис
sudo systemctl stop saldoran-sentinel

# Обновить конфигурацию
sudo cp systemd/saldoran-sentinel.service /etc/systemd/system/
sudo systemctl daemon-reload

# Запустить заново
sudo systemctl start saldoran-sentinel
sudo systemctl status saldoran-sentinel
```

### Сервис не запускается (другие ошибки)
```bash
# Проверить логи
sudo journalctl -u saldoran-sentinel -n 50

# Проверить конфигурацию
cd ~/SaldoranSentinelBot
python -c "from src.config import Config; Config.validate()"
```

### Telegram бот не отвечает
1. Проверьте токен в `.env`
2. Убедитесь, что бот запущен: `/start` в чате с ботом
3. Проверьте ваш TELEGRAM_ADMIN_ID

### Боты не обнаруживаются
1. Проверьте путь `BOTS_DIR` в `.env`
2. Убедитесь, что скрипты `run_bot.sh` исполняемые
3. Проверьте права доступа к директории ботов

---

✅ **Система готова к работе!** Используйте Telegram команды для управления ботами и мониторинга системы.