#!/usr/bin/env python3

"""
Диагностический скрипт для проверки токенов ботов на сервере
"""

import os
import sys
import subprocess
from pathlib import Path

def check_env_file(env_path):
    """Проверка .env файла на наличие токена"""
    if not env_path.exists():
        return None, "Файл .env не найден"
    
    try:
        with open(env_path, 'r') as f:
            content = f.read()
        
        token = None
        for line in content.split('\n'):
            if line.startswith('TELEGRAM_BOT_TOKEN='):
                token = line.split('=', 1)[1].strip()
                break
        
        if token:
            # Показываем только первые и последние символы токена для безопасности
            masked_token = f"{token[:10]}...{token[-10:]}" if len(token) > 20 else "***"
            return masked_token, "Найден"
        else:
            return None, "Токен не найден в файле"
            
    except Exception as e:
        return None, f"Ошибка чтения файла: {e}"

def check_system_env():
    """Проверка системных переменных окружения"""
    token = os.environ.get('TELEGRAM_BOT_TOKEN')
    if token:
        masked_token = f"{token[:10]}...{token[-10:]}" if len(token) > 20 else "***"
        return masked_token, "Найден в системных переменных"
    return None, "Не найден в системных переменных"

def check_bot_script(script_path):
    """Проверка скрипта запуска бота на наличие токена"""
    if not script_path.exists():
        return None, "Скрипт не найден"
    
    try:
        with open(script_path, 'r') as f:
            content = f.read()
        
        # Ищем упоминания токена в скрипте
        if 'TELEGRAM_BOT_TOKEN' in content:
            return "Найден", "Скрипт содержит упоминание TELEGRAM_BOT_TOKEN"
        else:
            return None, "Токен не упоминается в скрипте"
            
    except Exception as e:
        return None, f"Ошибка чтения скрипта: {e}"

def main():
    print("🔍 Диагностика токенов ботов на сервере...")
    print("=" * 60)
    
    # Проверяем токен стража
    sentinel_env = Path(".env")
    sentinel_token, sentinel_status = check_env_file(sentinel_env)
    
    print(f"🛡️  SaldoranSentinelBot:")
    print(f"   📁 Файл: {sentinel_env.absolute()}")
    print(f"   🔑 Токен: {sentinel_token}")
    print(f"   📊 Статус: {sentinel_status}")
    print()
    
    # Проверяем системные переменные окружения
    sys_token, sys_status = check_system_env()
    print(f"🌐 Системные переменные окружения:")
    print(f"   🔑 TELEGRAM_BOT_TOKEN: {sys_token}")
    print(f"   📊 Статус: {sys_status}")
    print()
    
    # Проверяем токен ShadowShort в разных местах
    possible_paths = [
        Path("/home/ubuntu/bots/shadowshort/.env"),
        Path("/home/ubuntu/bots/ShadowShort/.env"),
        Path("../ShadowShort/.env"),
        Path("/Users/saldoran/Documents/projects/ShadowShort/.env")
    ]
    
    shadowshort_found = False
    for shadow_env in possible_paths:
        if shadow_env.exists():
            shadowshort_found = True
            shadow_token, shadow_status = check_env_file(shadow_env)
            
            print(f"🌑 ShadowShort (.env файл):")
            print(f"   📁 Файл: {shadow_env.absolute()}")
            print(f"   🔑 Токен: {shadow_token}")
            print(f"   📊 Статус: {shadow_status}")
            print()
            
            # Проверяем скрипт запуска
            script_path = shadow_env.parent / "run_bot.sh"
            script_token, script_status = check_bot_script(script_path)
            print(f"🌑 ShadowShort (скрипт запуска):")
            print(f"   📁 Скрипт: {script_path}")
            print(f"   🔑 Токен: {script_token}")
            print(f"   📊 Статус: {script_status}")
            print()
            
            # Сравниваем токены
            if sentinel_token and shadow_token:
                if sentinel_token == shadow_token:
                    print("❌ ПРОБЛЕМА: Токены в .env файлах одинаковые!")
                    print("   Это объясняет, почему сообщения ShadowShort приходят в стража")
                else:
                    print("✅ Токены в .env файлах разные - это правильно")
            
            # Проверяем, не использует ли ShadowShort системные переменные
            if sys_token and sentinel_token and sys_token == sentinel_token:
                print("⚠️  ВНИМАНИЕ: Системная переменная совпадает с токеном стража!")
                print("   ShadowShort может использовать системную переменную вместо своего .env")
            
            break
    
    if not shadowshort_found:
        print("🌑 ShadowShort:")
        print("   📁 Файл .env не найден в стандартных местах")
        print("   🔍 Проверенные пути:")
        for path in possible_paths:
            print(f"      - {path}")
        print()
        print("❌ ПРОБЛЕМА: ShadowShort может использовать системные переменные!")
        
        if sys_token and sentinel_token and sys_token == sentinel_token:
            print("❌ КРИТИЧЕСКАЯ ПРОБЛЕМА: Системная переменная = токен стража!")
    
    print("=" * 60)
    print("💡 Рекомендации для исправления:")
    print("1. Убедитесь, что у ShadowShort есть собственный .env файл с уникальным токеном")
    print("2. Проверьте, что скрипт run_bot.sh загружает .env из правильной директории")
    print("3. Очистите системные переменные TELEGRAM_BOT_TOKEN если они установлены")
    print("4. Перезапустите ShadowShort после исправления конфигурации")
    print()
    print("🔧 Команды для проверки на сервере:")
    print("   env | grep TELEGRAM_BOT_TOKEN  # проверить системные переменные")
    print("   cat /home/ubuntu/bots/shadowshort/.env  # проверить .env ShadowShort")
    print("   cat /home/ubuntu/bots/shadowshort/run_bot.sh  # проверить скрипт запуска")

if __name__ == "__main__":
    main()