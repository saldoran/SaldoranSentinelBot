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

## 🔧 Протокол Sentinel для ботов

### PID файлы

**Местоположение**: Все PID файлы сохраняются в `/tmp/`  
**Формат**: `/tmp/{bot_name}.pid`  
**Содержимое**: Только PID процесса (число)

### Обязательные скрипты

#### **run_bot.sh** - Скрипт запуска

**Обязательные действия:**
1. **Проверить**, не запущен ли уже бот
2. **Удалить** старый PID файл если процесс не существует
3. **Запустить** бота в фоне
4. **Создать** PID файл `/tmp/{bot_name}.pid`

**Пример правильного run_bot.sh:**
```bash
#!/bin/bash
BOT_NAME="your_bot_name"
PID_FILE="/tmp/${BOT_NAME}.pid"

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

# Запускаем бота в фоне
nohup python3 main.py > logs/output.log 2>&1 &

# Сохраняем PID
echo $! > "$PID_FILE"

echo "Бот $BOT_NAME запущен (PID: $!)"
```

#### **stop_bot.sh** - Скрипт остановки

**Обязательные действия:**
1. **Прочитать** PID из файла
2. **Остановить** процесс (мягко, потом принудительно)
3. **Удалить** PID файл

**Пример правильного stop_bot.sh:**
```bash
#!/bin/bash
BOT_NAME="your_bot_name"
PID_FILE="/tmp/${BOT_NAME}.pid"

# Проверяем существование PID файла
if [ ! -f "$PID_FILE" ]; then
    echo "PID файл не найден. Бот $BOT_NAME не запущен или уже остановлен."
    exit 0
fi

# Читаем PID
PID=$(cat "$PID_FILE")

# Проверяем, существует ли процесс
if ! ps -p "$PID" > /dev/null 2>&1; then
    echo "Процесс с PID $PID не найден. Удаляем PID файл."
    rm -f "$PID_FILE"
    exit 0
fi

echo "Остановка бота $BOT_NAME (PID: $PID)..."

# Пытаемся мягко завершить процесс
kill "$PID"

# Ждем 5 секунд
sleep 5

# Проверяем, завершился ли процесс
if ps -p "$PID" > /dev/null 2>&1; then
    echo "Процесс не завершился мягко, принудительно завершаем..."
    kill -9 "$PID"
    sleep 2
fi

# Проверяем результат
if ps -p "$PID" > /dev/null 2>&1; then
    echo "Ошибка: не удалось остановить бот $BOT_NAME"
    exit 1
else
    echo "Бот $BOT_NAME успешно остановлен"
    rm -f "$PID_FILE"
    exit 0
fi
```

### ⚠️ Важные моменты

1. **Имя бота** в скриптах должно совпадать с именем папки
2. **PID файл** должен создаваться ТОЛЬКО после успешного запуска
3. **PID файл** должен удаляться при остановке бота
4. **run_bot.sh** должен проверять и очищать устаревшие PID файлы
5. **Все скрипты** должны быть исполняемыми: `chmod +x *.sh`

### 🐛 Проблемы с PID файлами

**Проблема**: Бот упал неожиданно, но PID файл остался  
**Симптом**: Sentinel показывает бота как "запущен", но процесс не существует  
**Решение**: Исправить `run_bot.sh` - добавить проверку и очистку устаревших PID файлов

**Проблема**: Несколько экземпляров бота  
**Симптом**: Ошибки при запуске, конфликты портов  
**Решение**: Исправить `run_bot.sh` - добавить проверку на уже запущенный бот

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
- `/resources` - Мониторинг системных ресурсов и процессов
- `/setup` - Настройки системы (перезапуск сервиса, очистка кэша, уровень логирования)
- `/help` - Справка по командам

### Inline кнопки

#### Управление ботами
Для каждого бота доступны кнопки:
- **▶️ Старт** / **⏹️ Стоп** - Запуск/остановка бота
- **🔄 Рестарт** - Перезапуск бота
- **⚡ Force Restart** - Принудительный перезапуск (SIGTERM + SIGKILL)
- **ℹ️ Инфо** - Подробная информация о боте

#### Мониторинг ресурсов
- **🔄 Обновить** - Обновить статистику ресурсов
- **📊 Подробнее** - Показать все процессы (не только топ-5)
- **📋 Краткий вид** - Вернуться к краткому виду (топ-5 процессов)

#### Настройки системы
- **🔄 Перезапустить сервис** - Перезапуск Sentinel
- **📊 Статус сервиса** - Проверка статуса systemd сервиса
- **🧹 Очистить кэш** - Очистка системного кэша памяти
- **📝 Уровень логирования** - Изменение уровня логирования (DEBUG, INFO, WARNING, ERROR, CRITICAL)

## 🔧 Мониторинг системы

### Автоматический мониторинг

Сервис автоматически каждые 60 секунд:

1. **Проверяет использование CPU** (лимит: 95%)
2. **Проверяет свободную RAM** (минимум: 40MB)
3. **При критическом состоянии памяти:**
   - Находит самый "жрущий" процесс пользователя ubuntu
   - Принудительно завершает его
   - Очищает кэш памяти: `sudo sysctl -w vm.drop_caches=3`
   - Отправляет уведомление в Telegram

### Мониторинг ботов

- **Автоматическое обнаружение** новых ботов в `~/bots/`
- **Отслеживание статуса** всех ботов (запущен/остановлен)
- **Уведомления** о запуске/остановке ботов
- **Управление PID файлами** - автоматическая очистка устаревших файлов

### Мониторинг процессов

Команда `/resources` показывает:
- **Системные ресурсы**: CPU, RAM, диск
- **Топ процессов** по использованию памяти
- **Идентификация ботов**: Python процессы отображаются с именами ботов (🤖 bot_name)
- **Детальный вид**: все процессы или только топ-5

## 📊 Информация о боте

При нажатии кнопки **ℹ️ Инфо** отображается:

- **Статус**: Запущен/Остановлен
- **PID**: Идентификатор процесса
- **CPU**: Использование процессора в %
- **RAM**: Использование памяти в MB
- **Размер логов**: Размер папки logs/ в MB
- **Последний коммит**: Короткий хеш Git коммита
- **Дата коммита**: Дата последнего коммита

## 📝 Управление логированием

### Динамическое изменение уровня логирования

Через команду `/setup` → **📝 Уровень логирования** можно изменить уровень логирования без перезапуска сервиса:

- **DEBUG** - Все сообщения (отладка, информация, предупреждения, ошибки)
- **INFO** - Информационные сообщения и выше
- **WARNING** - Предупреждения и ошибки
- **ERROR** - Только ошибки
- **CRITICAL** - Только критические ошибки

### Автоматическое применение

- Изменения сохраняются в `.env` файл
- Уровень логирования обновляется в текущем процессе
- **Не требует перезапуска** сервиса
- Меню остается активным для дальнейших изменений

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

### Изменение уровня логирования

**Через Telegram:**
1. Отправьте команду `/setup`
2. Нажмите **📝 Уровень логирования**
3. Выберите нужный уровень (рекомендуется DEBUG для отладки)

**Через файл .env:**
```bash
nano .env
# Измените LOG_LEVEL=DEBUG
sudo systemctl restart saldoran-sentinel
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

# Проверка PID файлов
ls -la /tmp/*.pid
```

### Диагностика проблем с ботами

**Проблема**: Бот показывается как "запущен", но процесс не существует
```bash
# Проверяем PID файл
cat /tmp/bot_name.pid

# Проверяем, существует ли процесс
ps -p $(cat /tmp/bot_name.pid)

# Если процесс не существует, удаляем PID файл
rm -f /tmp/bot_name.pid
```

**Проблема**: Бот не обнаруживается
```bash
# Проверяем структуру папки бота
ls -la ~/bots/bot_name/

# Проверяем права на скрипты
ls -la ~/bots/bot_name/*.sh

# Делаем скрипты исполняемыми
chmod +x ~/bots/bot_name/*.sh
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