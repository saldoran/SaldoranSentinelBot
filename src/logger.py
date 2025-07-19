"""
Система логирования с ротацией по дням для SaldoranBotSentinel
"""

import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from config import Config


class DailyRotatingLogger:
    """Логгер с ротацией файлов по дням"""
    
    def __init__(self, name: str = "SentinelBot"):
        self.name = name
        self.logger = logging.getLogger(name)
        self.logger.setLevel(getattr(logging, Config.LOG_LEVEL))
        
        # Убираем существующие обработчики
        self.logger.handlers.clear()
        
        # Создаем директорию для логов
        Config.LOGS_DIR.mkdir(exist_ok=True)
        
        # Настраиваем обработчики
        self._setup_handlers()
        
    def _setup_handlers(self):
        """Настройка обработчиков логирования"""
        # Форматтер для логов
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # Файловый обработчик с ротацией по дням
        log_filename = self._get_log_filename()
        file_handler = logging.FileHandler(log_filename, encoding='utf-8')
        file_handler.setFormatter(formatter)
        file_handler.setLevel(logging.INFO)
        
        # Консольный обработчик
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        console_handler.setLevel(logging.INFO)
        
        # Добавляем обработчики
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
        
    def _get_log_filename(self) -> Path:
        """Получение имени файла лога на текущую дату"""
        today = datetime.now().strftime("%d%m%Y")
        return Config.LOGS_DIR / f"sentinel_{today}.log"
        
    def _check_date_rotation(self):
        """Проверка необходимости ротации файла"""
        current_log_file = self._get_log_filename()
        
        # Если файл изменился (новый день), обновляем обработчик
        for handler in self.logger.handlers:
            if isinstance(handler, logging.FileHandler):
                if Path(handler.baseFilename) != current_log_file:
                    self.logger.removeHandler(handler)
                    handler.close()
                    
                    # Создаем новый файловый обработчик
                    formatter = logging.Formatter(
                        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S'
                    )
                    new_handler = logging.FileHandler(current_log_file, encoding='utf-8')
                    new_handler.setFormatter(formatter)
                    new_handler.setLevel(logging.INFO)
                    self.logger.addHandler(new_handler)
                    break
    
    def info(self, message: str):
        """Логирование информационного сообщения"""
        self._check_date_rotation()
        self.logger.info(message)
        
    def warning(self, message: str):
        """Логирование предупреждения"""
        self._check_date_rotation()
        self.logger.warning(message)
        
    def error(self, message: str):
        """Логирование ошибки"""
        self._check_date_rotation()
        self.logger.error(message)
        
    def critical(self, message: str):
        """Логирование критической ошибки"""
        self._check_date_rotation()
        self.logger.critical(message)
        
    def debug(self, message: str):
        """Логирование отладочной информации"""
        self._check_date_rotation()
        self.logger.debug(message)


def get_logger(name: str = "SentinelBot") -> DailyRotatingLogger:
    """Получение экземпляра логгера"""
    return DailyRotatingLogger(name)

# Глобальный экземпляр логгера
logger = DailyRotatingLogger()