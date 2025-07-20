# 🔧 Исправление конфликта токенов ботов

## Проблема
ShadowShort отправляет сообщения в бота-стража вместо собственного бота. Это происходит из-за использования одинакового `TELEGRAM_BOT_TOKEN`.

## Диагностика

### 1. Запустите диагностику на сервере:
```bash
cd ~/SaldoranSentinelBot
python diagnose_server_tokens.py
```

### 2. Проверьте системные переменные:
```bash
env | grep TELEGRAM_BOT_TOKEN
```

### 3. Проверьте конфигурацию ShadowShort:
```bash
# Проверьте .env файл ShadowShort
cat /home/ubuntu/bots/shadowshort/.env

# Проверьте скрипт запуска
cat /home/ubuntu/bots/shadowshort/run_bot.sh
```

## Возможные причины

### Причина 1: Отсутствует .env файл у ShadowShort
**Решение:**
```bash
# Создайте .env файл для ShadowShort
cd /home/ubuntu/bots/shadowshort
nano .env
```

Добавьте в файл:
```env
TELEGRAM_BOT_TOKEN=YOUR_SHADOWSHORT_BOT_TOKEN_HERE
# Другие настройки ShadowShort...
```

### Причина 2: Системная переменная окружения
**Решение:**
```bash
# Удалите системную переменную (если установлена)
unset TELEGRAM_BOT_TOKEN

# Или проверьте файлы профиля
grep -r "TELEGRAM_BOT_TOKEN" ~/.bashrc ~/.profile /etc/environment
```

### Причина 3: Скрипт запуска использует неправильный .env
**Решение:**
Проверьте `run_bot.sh` ShadowShort и убедитесь, что он загружает правильный .env:

```bash
#!/bin/bash
cd "$(dirname "$0")"  # Переходим в директорию скрипта
source .env           # Загружаем локальный .env
python main.py        # Запускаем бота
```

### Причина 4: ShadowShort наследует переменные от стража
**Решение:**
Убедитесь, что ShadowShort запускается в изолированной среде:

```bash
# В run_bot.sh добавьте очистку переменных
#!/bin/bash
unset TELEGRAM_BOT_TOKEN  # Очищаем системную переменную
cd "$(dirname "$0")"
source .env               # Загружаем локальный .env
python main.py
```

## Пошаговое исправление

### Шаг 1: Создайте отдельного бота для ShadowShort
1. Перейдите к [@BotFather](https://t.me/BotFather) в Telegram
2. Создайте нового бота: `/newbot`
3. Получите уникальный токен для ShadowShort

### Шаг 2: Настройте конфигурацию ShadowShort
```bash
cd /home/ubuntu/bots/shadowshort

# Создайте или отредактируйте .env
nano .env
```

Добавьте:
```env
TELEGRAM_BOT_TOKEN=YOUR_NEW_SHADOWSHORT_TOKEN
# Остальные настройки...
```

### Шаг 3: Обновите скрипт запуска
```bash
nano run_bot.sh
```

Убедитесь, что скрипт выглядит так:
```bash
#!/bin/bash

# Переходим в директорию бота
cd "$(dirname "$0")"

# Очищаем возможные системные переменные
unset TELEGRAM_BOT_TOKEN

# Загружаем локальный .env файл
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
else
    echo "Ошибка: .env файл не найден!"
    exit 1
fi

# Запускаем бота
python main.py
```

### Шаг 4: Перезапустите ShadowShort
```bash
# Остановите бота через стража или вручную
pkill -f shadowshort

# Запустите заново
cd /home/ubuntu/bots/shadowshort
./run_bot.sh
```

### Шаг 5: Проверьте результат
1. Отправьте сообщение в бота ShadowShort
2. Убедитесь, что ответ приходит от правильного бота
3. Проверьте, что сообщения не дублируются в стража

## Проверка исправления

### Команды для проверки:
```bash
# Проверьте процессы
ps aux | grep python

# Проверьте логи ShadowShort
tail -f /home/ubuntu/bots/shadowshort/logs/latest.log

# Проверьте логи стража
sudo journalctl -u saldoran-sentinel -f
```

### Признаки успешного исправления:
- ✅ ShadowShort отвечает в своем чате
- ✅ Страж не получает сообщения от ShadowShort
- ✅ Каждый бот работает независимо

## Предотвращение проблемы в будущем

1. **Всегда используйте уникальные токены** для каждого бота
2. **Создавайте локальные .env файлы** в директории каждого бота
3. **Избегайте системных переменных** TELEGRAM_BOT_TOKEN
4. **Тестируйте изоляцию** после запуска новых ботов

---

💡 **Совет:** Используйте `diagnose_server_tokens.py` для регулярной проверки конфигурации ботов.