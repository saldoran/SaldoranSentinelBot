import os
import sys
import signal
import asyncio
import threading
from dotenv import load_dotenv

from config import Config
from logger import get_logger
from bot_manager import BotManager
from resource_monitor import ResourceMonitor
from telegram_bot import TelegramBot

load_dotenv()
logger = get_logger(__name__)

# Глобальная переменная для отслеживания кода выхода
exit_code = 0

class SentinelService:
    def __init__(self):
        logger.info("Инициализация SentinelService...")
        try:
            logger.info("Загрузка конфигурации...")
            self.config = Config()
            logger.info("Инициализация BotManager...")
            self.bot_manager = BotManager()
            logger.info("Инициализация ResourceMonitor...")
            self.resource_monitor = ResourceMonitor()
            logger.info("Инициализация TelegramBot...")
            self.telegram_bot = TelegramBot(self.config, self.bot_manager, self.resource_monitor)
            self.running = False
            logger.info("SentinelService успешно инициализирован")
        except Exception as e:
            logger.error(f"Ошибка при инициализации SentinelService: {e}")
            raise
        
    async def start(self):
        """Запуск всех компонентов сервиса"""
        try:
            logger.info("Запуск SaldoranSentinelBot...")
            
            # Запускаем мониторинг ресурсов
            await self.resource_monitor.start()
            
            # Запускаем Telegram бота
            await self.telegram_bot.start()
            
            # Отправляем уведомление о запуске
            await self.telegram_bot.send_startup_notification()
            
            self.running = True
            logger.info("SaldoranSentinelBot успешно запущен")
            
        except Exception as e:
            logger.error(f"Ошибка при запуске сервиса: {e}")
            raise
            
    async def shutdown(self, exit_code_param=0):
        """Корректное завершение работы сервиса"""
        try:
            global exit_code
            logger.info("Начало процедуры shutdown...")
            
            # Устанавливаем код выхода
            exit_code = exit_code_param
            logger.info(f"Установлен код выхода: {exit_code}")
            
            self.running = False
            
            # Отправляем уведомление о завершении
            try:
                await self.telegram_bot.send_shutdown_notification()
                logger.info("Уведомление о завершении отправлено в Telegram")
            except Exception as e:
                logger.warning(f"Не удалось отправить уведомление о shutdown: {e}")
            
            # Останавливаем компоненты
            if hasattr(self, 'resource_monitor'):
                await self.resource_monitor.stop()
                
            if hasattr(self, 'telegram_bot'):
                await self.telegram_bot.stop()
                
            # Отменяем задачи
            pending = [t for t in asyncio.all_tasks() 
                      if t is not asyncio.current_task()]
            
            if pending:
                logger.info(f"Отменяем {len(pending)} задач...")
                for task in pending:
                    task.cancel()
                
                try:
                    await asyncio.wait_for(
                        asyncio.gather(*pending, return_exceptions=True),
                        timeout=5.0
                    )
                except asyncio.TimeoutError:
                    logger.warning("Timeout waiting for tasks to cancel")
                    
        except Exception as e:
            logger.error(f"Ошибка при shutdown: {e}")
        finally:
            logger.info("Shutdown завершен")

async def start_service():
    """Инициализация и запуск сервиса"""
    service = SentinelService()
    await service.start()
    return service

def run_service():
    """Основная функция запуска сервиса"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    # События для координации завершения
    shutdown_event = asyncio.Event()
    shutdown_complete = asyncio.Event()
    service = None
    
    async def shutdown_tasks():
        try:
            logger.info("shutdown_tasks: начинаем завершение")
            if service:
                await service.shutdown(0)
            shutdown_complete.set()
        finally:
            loop.stop()
    
    def handle_signals(sig_name=None):
        if shutdown_event.is_set():
            logger.info(f"Игнорирую повторный сигнал завершения {sig_name}")
            return
        shutdown_event.set()
        logger.info(f"Получен сигнал завершения: {sig_name}")
        loop.create_task(shutdown_tasks())
    
    try:
        # Регистрируем обработчики сигналов
        loop.add_signal_handler(signal.SIGTERM, lambda: handle_signals("SIGTERM"))
        loop.add_signal_handler(signal.SIGINT, lambda: handle_signals("SIGINT"))
        
        # Запускаем сервис
        service = loop.run_until_complete(start_service())
        loop.run_forever()
        
    except Exception as e:
        logger.exception("Service crashed: %s", e)
        if not shutdown_event.is_set():
            loop.run_until_complete(shutdown_tasks())
    finally:
        try:
            # Ждем завершения shutdown если он еще не завершен
            if not shutdown_complete.is_set() and loop.is_running():
                loop.run_until_complete(shutdown_complete.wait())
            
            # Отменяем оставшиеся задачи
            pending = asyncio.all_tasks(loop)
            for task in pending:
                task.cancel()
            
            if pending:
                loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
            
            # Закрываем loop
            loop.run_until_complete(loop.shutdown_asyncgens())
            loop.close()
        except Exception as e:
            logger.error(f"Ошибка при закрытии loop: {e}")
        
        logger.info("Программа завершена")
        # Используем глобальную переменную exit_code
        os._exit(exit_code)

if __name__ == "__main__":
    run_service()