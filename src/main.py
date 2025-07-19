"""
Главный модуль SaldoranBotSentinel
"""

import asyncio
import signal
import sys
from typing import Optional
from datetime import datetime

from .config import Config
from .logger import logger
from .bot_manager import BotManager
from .resource_monitor import ResourceMonitor
from .telegram_bot import SentinelTelegramBot


class SentinelService:
    """Главный сервис SaldoranBotSentinel"""
    
    def __init__(self):
        self.bot_manager: Optional[BotManager] = None
        self.resource_monitor: Optional[ResourceMonitor] = None
        self.telegram_bot: Optional[SentinelTelegramBot] = None
        self.monitoring_task: Optional[asyncio.Task] = None
        self.running = False
        
    async def initialize(self):
        """Инициализация всех компонентов сервиса"""
        try:
            logger.info("🚀 Инициализация SaldoranBotSentinel...")
            
            # Валидация конфигурации
            Config.validate()
            logger.info("✅ Конфигурация валидна")
            
            # Создание необходимых директорий
            Config.create_directories()
            logger.info("✅ Директории созданы")
            
            # Инициализация компонентов
            self.bot_manager = BotManager()
            logger.info("✅ BotManager инициализирован")
            
            self.resource_monitor = ResourceMonitor()
            logger.info("✅ ResourceMonitor инициализирован")
            
            self.telegram_bot = SentinelTelegramBot(self.bot_manager, self.resource_monitor)
            self.telegram_bot.setup_application()
            logger.info("✅ TelegramBot инициализирован")
            
            logger.info("🎉 Все компоненты успешно инициализированы!")
            
        except Exception as e:
            logger.critical(f"❌ Критическая ошибка при инициализации: {e}")
            raise
    
    async def start_monitoring_loop(self):
        """Запуск цикла мониторинга ресурсов"""
        logger.info(f"🔄 Запуск цикла мониторинга (интервал: {Config.MONITORING_INTERVAL}с)")
        
        while self.running:
            try:
                # Выполняем мониторинг
                monitoring_result = self.resource_monitor.monitor_resources()
                
                # Логируем результаты мониторинга
                actions = monitoring_result.get('actions_taken', [])
                if actions:
                    logger.warning(f"Выполнены действия мониторинга: {', '.join(actions)}")
                
                # Если была экстренная очистка памяти, уведомляем админа
                if 'emergency_memory_cleanup' in actions:
                    await self._notify_admin_emergency_cleanup(monitoring_result)
                
                # Ждем до следующей проверки
                await asyncio.sleep(Config.MONITORING_INTERVAL)
                
            except Exception as e:
                logger.error(f"Ошибка в цикле мониторинга: {e}")
                await asyncio.sleep(Config.MONITORING_INTERVAL)
    
    async def _notify_admin_emergency_cleanup(self, monitoring_result):
        """Уведомление администратора об экстренной очистке памяти"""
        try:
            if self.telegram_bot and self.telegram_bot.application:
                stats = monitoring_result['stats']
                timestamp = monitoring_result['timestamp']
                
                message = (
                    f"🚨 **ЭКСТРЕННАЯ ОЧИСТКА ПАМЯТИ**\n\n"
                    f"⏰ Время: {timestamp.strftime('%H:%M:%S %d.%m.%Y')}\n"
                    f"💾 Доступно памяти: {stats.memory_available_mb:.0f}MB\n"
                    f"📊 Использование: {stats.memory_percent:.1f}%\n\n"
                    f"Система автоматически завершила процессы-пожиратели памяти "
                    f"и очистила кэш."
                )
                
                await self.telegram_bot.application.bot.send_message(
                    chat_id=Config.TELEGRAM_ADMIN_ID,
                    text=message,
                    parse_mode='Markdown'
                )
                
        except Exception as e:
            logger.error(f"Ошибка при отправке уведомления админу: {e}")
    
    async def start(self):
        """Запуск сервиса"""
        try:
            self.running = True
            logger.info("🚀 Запуск SaldoranBotSentinel...")
            
            # Инициализируем компоненты
            await self.initialize()
            
            # Запускаем Telegram-бота
            await self.telegram_bot.start_bot()
            
            # Запускаем цикл мониторинга в отдельной задаче
            self.monitoring_task = asyncio.create_task(self.start_monitoring_loop())
            
            # Отправляем уведомление о запуске
            await self._notify_startup()
            
            logger.info("✅ SaldoranBotSentinel успешно запущен!")
            
            # Ждем завершения работы
            await self.monitoring_task
            
        except Exception as e:
            logger.critical(f"❌ Критическая ошибка при запуске сервиса: {e}")
            await self.stop()
            raise
    
    async def _notify_startup(self):
        """Уведомление о запуске сервиса"""
        try:
            if self.telegram_bot and self.telegram_bot.application:
                # Получаем статистику системы
                stats = self.resource_monitor.get_system_stats()
                bots_info = self.bot_manager.get_all_bots_info()
                
                running_bots = sum(1 for bot in bots_info if bot.is_running)
                total_bots = len(bots_info)
                
                startup_message = (
                    f"🟢 **SaldoranBotSentinel запущен!**\n\n"
                    f"⏰ Время запуска: {datetime.now().strftime('%H:%M:%S %d.%m.%Y')}\n"
                    f"🖥️ CPU: {stats.cpu_percent:.1f}%\n"
                    f"💾 Память: {stats.memory_percent:.1f}% "
                    f"({stats.memory_available_mb:.0f}MB свободно)\n"
                    f"🤖 Боты: {running_bots}/{total_bots} запущено\n\n"
                    f"Мониторинг активен каждые {Config.MONITORING_INTERVAL}с"
                )
                
                await self.telegram_bot.application.bot.send_message(
                    chat_id=Config.TELEGRAM_ADMIN_ID,
                    text=startup_message,
                    parse_mode='Markdown'
                )
                
        except Exception as e:
            logger.error(f"Ошибка при отправке уведомления о запуске: {e}")
    
    async def stop(self):
        """Остановка сервиса"""
        logger.info("🛑 Остановка SaldoranBotSentinel...")
        
        self.running = False
        
        # Останавливаем задачу мониторинга
        if self.monitoring_task and not self.monitoring_task.done():
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
        
        # Останавливаем Telegram-бота
        if self.telegram_bot:
            await self.telegram_bot.stop_bot()
        
        # Отправляем уведомление об остановке
        await self._notify_shutdown()
        
        logger.info("✅ SaldoranBotSentinel остановлен")
    
    async def _notify_shutdown(self):
        """Уведомление об остановке сервиса"""
        try:
            if self.telegram_bot and self.telegram_bot.application:
                shutdown_message = (
                    f"🔴 **SaldoranBotSentinel остановлен**\n\n"
                    f"⏰ Время остановки: {datetime.now().strftime('%H:%M:%S %d.%m.%Y')}\n"
                    f"Мониторинг системы приостановлен."
                )
                
                await self.telegram_bot.application.bot.send_message(
                    chat_id=Config.TELEGRAM_ADMIN_ID,
                    text=shutdown_message,
                    parse_mode='Markdown'
                )
                
        except Exception as e:
            logger.error(f"Ошибка при отправке уведомления об остановке: {e}")


# Глобальный экземпляр сервиса
sentinel_service = SentinelService()


def signal_handler(signum, frame):
    """Обработчик сигналов для graceful shutdown"""
    logger.info(f"Получен сигнал {signum}, начинаю остановку...")
    
    # Создаем новый event loop если его нет
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    # Запускаем остановку сервиса
    loop.create_task(sentinel_service.stop())


async def main():
    """Главная функция"""
    try:
        # Настраиваем обработчики сигналов
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # Запускаем сервис
        await sentinel_service.start()
        
    except KeyboardInterrupt:
        logger.info("Получен сигнал прерывания от пользователя")
        await sentinel_service.stop()
    except Exception as e:
        logger.critical(f"Неожиданная ошибка: {e}")
        await sentinel_service.stop()
        sys.exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Программа прервана пользователем")
    except Exception as e:
        logger.critical(f"Критическая ошибка при запуске: {e}")
        sys.exit(1)