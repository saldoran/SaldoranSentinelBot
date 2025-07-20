#!/usr/bin/env python3

"""
Диагностический скрипт для проверки токенов ботов
"""

import os
import sys
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

def main():
    print("🔍 Диагностика токенов ботов...")
    print("=" * 50)
    
    # Проверяем токен стража
    sentinel_env = Path(".env")
    sentinel_token, sentinel_status = check_env_file(sentinel_env)
    
    print(f"🛡️  SaldoranSentinelBot:")
    print(f"   📁 Файл: {sentinel_env.absolute()}")
    print(f"   🔑 Токен: {sentinel_token}")
    print(f"   📊 Статус: {sentinel_status}")
    print()
    
    # Проверяем токен ShadowShort
    # Пытаемся найти ShadowShort в разных местах
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
            
            print(f"🌑 ShadowShort:")
            print(f"   📁 Файл: {shadow_env.absolute()}")
            print(f"   🔑 Токен: {shadow_token}")
            print(f"   📊 Статус: {shadow_status}")
            print()
            
            # Сравниваем токены
            if sentinel_token and shadow_token:
                if sentinel_token == shadow_token:
                    print("❌ ПРОБЛЕМА: Токены одинаковые!")
                    print("   Это объясняет, почему сообщения ShadowShort приходят в стража")
                else:
                    print("✅ Токены разные - это правильно")
            break
    
    if not shadowshort_found:
        print("🌑 ShadowShort:")
        print("   📁 Файл .env не найден в стандартных местах")
        print("   🔍 Проверенные пути:")
        for path in possible_paths:
            print(f"      - {path}")
        print()
        print("❌ ПРОБЛЕМА: ShadowShort может использовать токен стража по умолчанию!")
    
    print("=" * 50)
    print("💡 Рекомендации:")
    print("1. Убедитесь, что у ShadowShort есть собственный .env файл")
    print("2. Создайте отдельного бота в @BotFather для ShadowShort")
    print("3. Используйте уникальный токен для каждого бота")

if __name__ == "__main__":
    main()