"""
Модуль конфигурации для SaldoranBotSentinel
"""

import os
import getpass
from pathlib import Path
from dotenv import load_dotenv

# Загружаем переменные окружения из .env файла
load_dotenv()

class Config:
    """Класс конфигурации приложения"""
    
    # Telegram Bot Configuration
    TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    TELEGRAM_ADMIN_ID = int(os.getenv('TELEGRAM_ADMIN_ID', 0))
    
    # Resource Monitoring Limits
    MAX_CPU_PERCENT = float(os.getenv('MAX_CPU_PERCENT', 95))
    MIN_FREE_RAM_MB = int(os.getenv('MIN_FREE_RAM_MB', 40))
    MONITORING_INTERVAL = int(os.getenv('MONITORING_INTERVAL', 60))
    
    # Paths
    _base_dir = Path(__file__).parent.parent  # Корневая директория проекта
    BOTS_DIR = _base_dir / os.getenv('BOTS_DIR', 'test_bot').lstrip('./')
    LOGS_DIR = _base_dir / os.getenv('LOGS_DIR', 'logs').lstrip('./')
    
    # System Configuration
    TARGET_USER = os.getenv('TARGET_USER', getpass.getuser())
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    
    @classmethod
    def validate(cls):
        """Валидация конфигурации"""
        errors = []
        
        if not cls.TELEGRAM_BOT_TOKEN:
            errors.append("TELEGRAM_BOT_TOKEN не установлен")
            
        if cls.TELEGRAM_ADMIN_ID == 0:
            errors.append("TELEGRAM_ADMIN_ID не установлен")
            
        if cls.MIN_FREE_RAM_MB < 10:
            errors.append("MIN_FREE_RAM_MB слишком мал (минимум 10MB)")
            
        if cls.MAX_CPU_PERCENT > 100 or cls.MAX_CPU_PERCENT < 1:
            errors.append("MAX_CPU_PERCENT должен быть между 1 и 100")
            
        if errors:
            raise ValueError(f"Ошибки конфигурации: {'; '.join(errors)}")
            
        return True
    
    @classmethod
    def create_directories(cls):
        """Создание необходимых директорий"""
        cls.LOGS_DIR.mkdir(exist_ok=True)
        cls.BOTS_DIR.mkdir(exist_ok=True)