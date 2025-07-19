# SaldoranBotSentinel

🤖 **Система управления и мониторинга ботов** для Ubuntu Server

SaldoranBotSentinel - это Python-сервис, который автоматически управляет другими ботами, мониторит системные ресурсы и предоставляет удобный Telegram-интерфейс для управления.

## 🚀 Основные возможности

- **Управление ботами**: Запуск, остановка, перезапуск ботов через Telegram
- **Мониторинг ресурсов**: Автоматическое отслеживание CPU/RAM каждые 60 секунд
- **Защита системы**: Автоматическое завершение процессов при критическом состоянии памяти
- **Telegram-интерфейс**: Удобное управление через inline-кнопки
- **Автозапуск**: Запуск с системой через systemd
- **Логирование**: Ротация логов по дням

## 📋 Требования

- Ubuntu 22.04 LTS
- Python 3.8+
- sudo права для очистки кэша памяти
- Telegram Bot Token

## 🛠️ Установка

### 1. Клонирование репозитория

```bash
cd /home/ubuntu
git clone <repository_url> SaldoranSentinelBot
cd SaldoranSentinelBot
```

### 2. Создание виртуального окружения

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Настройка конфигурации

Создайте файл `.env` на основе примера:

```bash
cp .env.example .env
nano .env
```

Настройте параметры в `.env`:

```env
# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_ADMIN_ID=your_admin_user_id

# Resource Monitoring Limits
MAX_CPU_PERCENT=95
MIN_FREE_RAM_MB=40
MONITORING_INTERVAL=60

# Paths
BOTS_DIR=~/bots
LOGS_DIR=./logs

# System Configuration
TARGET_USER=ubuntu
LOG_LEVEL=INFO
```

**Важно**: Замените `your_bot_token_here` на реальный токен вашего Telegram-бота и `your_admin_user_id` на ваш Telegram ID.

### 4. Создание директории для ботов

```bash
mkdir -p ~/bots
```

### 5. Настройка systemd сервиса

```bash
sudo cp systemd/saldoran-sentinel.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable saldoran-sentinel
```

### 6. Настройка sudo для очистки кэша

Добавьте в sudoers возможность выполнения команды очистки кэша без пароля:

```bash
sudo visudo
```

Добавьте строку:
```
ubuntu ALL=(ALL) NOPASSWD: /sbin/sysctl -w vm.drop_caches=3
```

## 🎯 Структура бота

Каждый бот должен находиться в отдельной папке внутри `~/bots/` и содержать исполняемые скрипты:

```
~/bots/
└── your_bot_name/
    ├── run_bot.sh      # Скрипт запуска (обязательно)
    ├── stop_bot.sh     # Скрипт остановки (обязательно)
    ├── restart_bot.sh  # Скрипт перезапуска (опционально)
    ├── status_bot.sh   # Скрипт статуса (опционально)
    ├── logs/           # Папка с логами (опционально)
    └── .git/           # Git репозиторий (опционально)
```

### Пример скриптов

**run_bot.sh:**
```bash
#!/bin/bash
# Ваш код запуска бота
nohup python3 bot.py > logs/output.log 2>&1 &
echo $! > /tmp/your_bot_name.pid
```

**stop_bot.sh:**
```bash
#!/bin/bash
PID_FILE="/tmp/your_bot_name.pid"
if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    kill "$PID"
    rm -f "$PID_FILE"
fi
```

Не забудьте сделать скрипты исполняемыми:
```bash
chmod +x ~/bots/your_bot_name/*.sh
```

## 🚀 Запуск

### Ручной запуск (для тестирования)

```bash
cd /home/ubuntu/SaldoranSentinelBot
source venv/bin/activate
python -m src.main
```

### Запуск через systemd

```bash
sudo systemctl start saldoran-sentinel
sudo systemctl status saldoran-sentinel
```

### Просмотр логов

```bash
# Логи systemd
sudo journalctl -u saldoran-sentinel -f

# Логи приложения
tail -f logs/sentinel_$(date +%d%m%Y).log
```

## 📱 Telegram команды

- `/start` - Запуск бота и приветствие
- `/list` - Список всех ботов с кнопками управления
- `/status` - Краткий статус системы
- `/monitor` - Подробный отчет мониторинга
- `/cleanup` - Экстренная очистка памяти
- `/help` - Справка по командам

### Inline кнопки

Для каждого бота доступны кнопки:
- **▶️ Старт** / **⏹️ Стоп** - Запуск/остановка бота
- **🔄 Рестарт** - Перезапуск бота
- **ℹ️ Инфо** - Подробная информация о боте

## 🔧 Мониторинг системы

Сервис автоматически каждые 60 секунд:

1. **Проверяет использование CPU** (лимит: 95%)
2. **Проверяет свободную RAM** (минимум: 40MB)
3. **При критическом состоянии памяти:**
   - Находит самый "жрущий" процесс пользователя ubuntu
   - Принудительно завершает его
   - Очищает кэш памяти: `sudo sysctl -w vm.drop_caches=3`
   - Отправляет уведомление в Telegram

## 📊 Информация о боте

При нажатии кнопки **ℹ️ Инфо** отображается:

- **Статус**: Запущен/Остановлен
- **PID**: Идентификатор процесса
- **CPU**: Использование процессора в %
- **RAM**: Использование памяти в MB
- **Размер логов**: Размер папки logs/ в MB
- **Последний коммит**: Короткий хеш Git коммита
- **Дата коммита**: Дата последнего коммита

## 🛡️ Безопасность

- Доступ только для указанного TELEGRAM_ADMIN_ID
- Ограниченные права systemd сервиса
- Защищенные пути для чтения/записи
- Таймауты для всех операций

## 🔄 Обновление

```bash
cd /home/ubuntu/SaldoranSentinelBot
git pull
sudo systemctl restart saldoran-sentinel
```

## 🐛 Отладка

### Проверка статуса сервиса

```bash
sudo systemctl status saldoran-sentinel
```

### Просмотр логов

```bash
# Последние логи systemd
sudo journalctl -u saldoran-sentinel --no-pager -l

# Логи приложения
ls -la logs/
cat logs/sentinel_$(date +%d%m%Y).log
```

### Тестирование конфигурации

```bash
cd /home/ubuntu/SaldoranSentinelBot
source venv/bin/activate
python -c "from src.config import Config; Config.validate(); print('Конфигурация валидна')"
```

### Проверка ботов

```bash
# Список найденных ботов
python -c "
from src.bot_manager import BotManager
bm = BotManager()
bots = bm.discover_bots()
print('Найденные боты:', bots)
"
```

## 📁 Структура проекта

```
SaldoranSentinelBot/
├── src/
│   ├── __init__.py
│   ├── main.py              # Точка входа
│   ├── config.py            # Конфигурация
│   ├── bot_manager.py       # Управление ботами
│   ├── resource_monitor.py  # Мониторинг ресурсов
│   ├── telegram_bot.py      # Telegram интерфейс
│   └── logger.py            # Система логирования
├── systemd/
│   └── saldoran-sentinel.service
├── test_bot/                # Тестовый бот для проверки
│   └── shadowshort/
├── logs/                    # Логи сервиса
├── .env                     # Конфигурация
├── requirements.txt
└── README.md
```

## 🍎 Локальное тестирование на macOS

Для тестирования на macOS создайте `.env` файл с настройками:

```env
# Telegram Bot Configuration  
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_ADMIN_ID=your_admin_user_id

# Resource Monitoring Limits
MAX_CPU_PERCENT=95
MIN_FREE_RAM_MB=100
MONITORING_INTERVAL=60

# Paths (для локального тестирования)
BOTS_DIR=./test_bot
LOGS_DIR=./logs

# System Configuration (ваш пользователь macOS)
TARGET_USER=your_macos_username
LOG_LEVEL=INFO
```

Затем запустите:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python -m src.main
```

**Примечание**: Команда очистки кэша `sudo sysctl -w vm.drop_caches=3` не работает на macOS, но остальной функционал будет работать полностью.

## 🤝 Поддержка

При возникновении проблем:

1. Проверьте логи: `sudo journalctl -u saldoran-sentinel -f`
2. Убедитесь в правильности конфигурации `.env`
3. Проверьте права доступа к файлам и директориям
4. Убедитесь, что Telegram Bot Token действителен

---

**Автор**: Saldoran  
**Версия**: 1.0.0  
**Лицензия**: MIT