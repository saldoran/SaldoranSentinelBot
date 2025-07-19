"""
Telegram-бот интерфейс для SaldoranBotSentinel
"""

import asyncio
from typing import Dict, List
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from telegram.constants import ParseMode

from .config import Config
from .bot_manager import BotManager, BotInfo
from .resource_monitor import ResourceMonitor
from .logger import logger


class SentinelTelegramBot:
    """Telegram-бот для управления SaldoranBotSentinel"""
    
    def __init__(self, bot_manager: BotManager, resource_monitor: ResourceMonitor):
        self.bot_manager = bot_manager
        self.resource_monitor = resource_monitor
        self.admin_id = Config.TELEGRAM_ADMIN_ID
        self.application = None
        
    def _is_admin(self, user_id: int) -> bool:
        """Проверка является ли пользователь администратором"""
        return user_id == self.admin_id
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /start"""
        if not self._is_admin(update.effective_user.id):
            await update.message.reply_text("❌ У вас нет прав доступа к этому боту.")
            return
            
        welcome_text = (
            "🤖 **SaldoranBotSentinel** запущен!\n\n"
            "Доступные команды:\n"
            "• `/list` - Список ботов с управлением\n"
            "• `/status` - Статус системы и ресурсов\n"
            "• `/monitor` - Отчет мониторинга\n"
            "• `/cleanup` - Экстренная очистка памяти\n"
            "• `/help` - Справка по командам"
        )
        
        await update.message.reply_text(welcome_text, parse_mode=ParseMode.MARKDOWN)
        logger.info(f"Пользователь {update.effective_user.username} запустил бота")
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /help"""
        if not self._is_admin(update.effective_user.id):
            return
            
        help_text = (
            "📖 **Справка по командам:**\n\n"
            "🤖 **Управление ботами:**\n"
            "• `/list` - Показать всех ботов с кнопками управления\n"
            "• Кнопки: ▶️/⏹️ (Старт/Стоп), 🔄 (Рестарт), ℹ️ (Инфо)\n\n"
            "📊 **Мониторинг системы:**\n"
            "• `/status` - Краткий статус системы\n"
            "• `/monitor` - Подробный отчет мониторинга\n"
            "• `/cleanup` - Экстренная очистка памяти\n\n"
            "⚙️ **Настройки:**\n"
            f"• Максимум CPU: {Config.MAX_CPU_PERCENT}%\n"
            f"• Минимум свободной RAM: {Config.MIN_FREE_RAM_MB}MB\n"
            f"• Интервал мониторинга: {Config.MONITORING_INTERVAL}с"
        )
        
        await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)
    
    async def list_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /list - показать список ботов"""
        if not self._is_admin(update.effective_user.id):
            return
            
        try:
            bots_info = self.bot_manager.get_all_bots_info()
            
            if not bots_info:
                await update.message.reply_text(
                    "📭 Боты не найдены.\n"
                    f"Проверьте директорию: `{Config.BOTS_DIR}`",
                    parse_mode=ParseMode.MARKDOWN
                )
                return
            
            # Создаем сообщение со списком ботов
            message_text = "🤖 **Список ботов:**\n\n"
            
            for bot_info in bots_info:
                status_emoji = "🟢" if bot_info.is_running else "🔴"
                status_text = "Запущен" if bot_info.is_running else "Остановлен"
                
                message_text += f"{status_emoji} **{bot_info.name}** - {status_text}\n"
                
                if bot_info.is_running and bot_info.pid:
                    message_text += f"   PID: {bot_info.pid}"
                    if bot_info.memory_mb:
                        message_text += f", RAM: {bot_info.memory_mb:.1f}MB"
                    message_text += "\n"
                
                message_text += "\n"
            
            # Создаем inline клавиатуру для каждого бота
            keyboard = []
            for bot_info in bots_info:
                row = []
                
                # Кнопка Старт/Стоп
                if bot_info.is_running:
                    row.append(InlineKeyboardButton("⏹️ Стоп", callback_data=f"stop_{bot_info.name}"))
                else:
                    row.append(InlineKeyboardButton("▶️ Старт", callback_data=f"start_{bot_info.name}"))
                
                # Кнопка Рестарт
                row.append(InlineKeyboardButton("🔄 Рестарт", callback_data=f"restart_{bot_info.name}"))
                
                # Кнопка Инфо
                row.append(InlineKeyboardButton("ℹ️ Инфо", callback_data=f"info_{bot_info.name}"))
                
                keyboard.append(row)
            
            # Добавляем кнопку обновления списка
            keyboard.append([InlineKeyboardButton("🔄 Обновить список", callback_data="refresh_list")])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                message_text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup
            )
            
        except Exception as e:
            logger.error(f"Ошибка в команде /list: {e}")
            await update.message.reply_text("❌ Ошибка при получении списка ботов.")
    
    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /status - краткий статус системы"""
        if not self._is_admin(update.effective_user.id):
            return
            
        try:
            stats = self.resource_monitor.get_system_stats()
            bots_info = self.bot_manager.get_all_bots_info()
            
            running_bots = sum(1 for bot in bots_info if bot.is_running)
            total_bots = len(bots_info)
            
            status_text = (
                f"📊 **Статус системы:**\n\n"
                f"🖥️ **CPU:** {stats.cpu_percent:.1f}%\n"
                f"💾 **Память:** {stats.memory_percent:.1f}% "
                f"({stats.memory_available_mb:.0f}MB свободно)\n"
                f"🤖 **Боты:** {running_bots}/{total_bots} запущено\n\n"
            )
            
            # Проверяем критические состояния
            memory_critical = self.resource_monitor.check_memory_critical()
            cpu_critical, _ = self.resource_monitor.check_cpu_critical()
            
            if memory_critical or cpu_critical:
                status_text += "⚠️ **ВНИМАНИЕ:**\n"
                if memory_critical:
                    status_text += "🔴 Критически мало памяти!\n"
                if cpu_critical:
                    status_text += "🔴 Высокое использование CPU!\n"
            else:
                status_text += "✅ Система работает нормально"
            
            await update.message.reply_text(status_text, parse_mode=ParseMode.MARKDOWN)
            
        except Exception as e:
            logger.error(f"Ошибка в команде /status: {e}")
            await update.message.reply_text("❌ Ошибка при получении статуса системы.")
    
    async def monitor_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /monitor - подробный отчет мониторинга"""
        if not self._is_admin(update.effective_user.id):
            return
            
        try:
            report = self.resource_monitor.get_monitoring_report()
            await update.message.reply_text(report, parse_mode=ParseMode.MARKDOWN)
            
        except Exception as e:
            logger.error(f"Ошибка в команде /monitor: {e}")
            await update.message.reply_text("❌ Ошибка при получении отчета мониторинга.")
    
    async def cleanup_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /cleanup - экстренная очистка памяти"""
        if not self._is_admin(update.effective_user.id):
            return
            
        try:
            await update.message.reply_text("🧹 Запускаю экстренную очистку памяти...")
            
            success = self.resource_monitor.emergency_memory_cleanup()
            
            if success:
                stats = self.resource_monitor.get_system_stats()
                result_text = (
                    f"✅ **Экстренная очистка завершена!**\n\n"
                    f"💾 Доступно памяти: {stats.memory_available_mb:.0f}MB\n"
                    f"📊 Использование: {stats.memory_percent:.1f}%"
                )
            else:
                result_text = "❌ **Экстренная очистка не помогла!**\nТребуется ручное вмешательство."
            
            await update.message.reply_text(result_text, parse_mode=ParseMode.MARKDOWN)
            
        except Exception as e:
            logger.error(f"Ошибка в команде /cleanup: {e}")
            await update.message.reply_text("❌ Ошибка при выполнении очистки памяти.")
    
    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик нажатий на inline кнопки"""
        query = update.callback_query
        await query.answer()
        
        if not self._is_admin(query.from_user.id):
            return
            
        try:
            callback_data = query.data
            action, bot_name = callback_data.split('_', 1)
            
            if action == "start":
                await self._handle_start_bot(query, bot_name)
            elif action == "stop":
                await self._handle_stop_bot(query, bot_name)
            elif action == "restart":
                await self._handle_restart_bot(query, bot_name)
            elif action == "info":
                await self._handle_bot_info(query, bot_name)
            elif callback_data == "refresh_list":
                await self._handle_refresh_list(query)
                
        except Exception as e:
            logger.error(f"Ошибка в обработчике кнопок: {e}")
            await query.edit_message_text("❌ Ошибка при выполнении действия.")
    
    async def _handle_start_bot(self, query, bot_name: str):
        """Обработка запуска бота"""
        await query.edit_message_text(f"▶️ Запускаю бота {bot_name}...")
        
        success = self.bot_manager.start_bot(bot_name)
        
        if success:
            await query.edit_message_text(f"✅ Бот {bot_name} успешно запущен!")
        else:
            await query.edit_message_text(f"❌ Ошибка при запуске бота {bot_name}")
    
    async def _handle_stop_bot(self, query, bot_name: str):
        """Обработка остановки бота"""
        await query.edit_message_text(f"⏹️ Останавливаю бота {bot_name}...")
        
        success = self.bot_manager.stop_bot(bot_name)
        
        if success:
            await query.edit_message_text(f"✅ Бот {bot_name} успешно остановлен!")
        else:
            await query.edit_message_text(f"❌ Ошибка при остановке бота {bot_name}")
    
    async def _handle_restart_bot(self, query, bot_name: str):
        """Обработка перезапуска бота"""
        await query.edit_message_text(f"🔄 Перезапускаю бота {bot_name}...")
        
        success = self.bot_manager.restart_bot(bot_name)
        
        if success:
            await query.edit_message_text(f"✅ Бот {bot_name} успешно перезапущен!")
        else:
            await query.edit_message_text(f"❌ Ошибка при перезапуске бота {bot_name}")
    
    async def _handle_bot_info(self, query, bot_name: str):
        """Обработка запроса информации о боте"""
        bot_info = self.bot_manager.get_bot_info(bot_name)
        
        if not bot_info:
            await query.edit_message_text(f"❌ Информация о боте {bot_name} недоступна")
            return
        
        info_text = f"ℹ️ **Информация о боте {bot_name}:**\n\n"
        
        # Статус
        status_emoji = "🟢" if bot_info.is_running else "🔴"
        status_text = "Запущен" if bot_info.is_running else "Остановлен"
        info_text += f"**Статус:** {status_emoji} {status_text}\n"
        
        # PID и ресурсы
        if bot_info.is_running and bot_info.pid:
            info_text += f"**PID:** {bot_info.pid}\n"
            
            if bot_info.cpu_percent is not None:
                info_text += f"**CPU:** {bot_info.cpu_percent:.1f}%\n"
                
            if bot_info.memory_mb is not None:
                info_text += f"**RAM:** {bot_info.memory_mb:.1f}MB\n"
        
        # Размер логов
        if bot_info.logs_size_mb is not None:
            info_text += f"**Размер логов:** {bot_info.logs_size_mb:.1f}MB\n"
        
        # Git информация
        if bot_info.last_commit:
            info_text += f"**Последний коммит:** `{bot_info.last_commit}`\n"
            
        if bot_info.last_commit_date:
            info_text += f"**Дата коммита:** {bot_info.last_commit_date}\n"
        
        # Путь к боту
        info_text += f"**Путь:** `{bot_info.path}`"
        
        # Кнопка "Назад к списку"
        keyboard = [[InlineKeyboardButton("🔙 Назад к списку", callback_data="refresh_list")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            info_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )
    
    async def _handle_refresh_list(self, query):
        """Обработка обновления списка ботов"""
        try:
            bots_info = self.bot_manager.get_all_bots_info()
            
            if not bots_info:
                await query.edit_message_text(
                    "📭 Боты не найдены.\n"
                    f"Проверьте директорию: `{Config.BOTS_DIR}`",
                    parse_mode=ParseMode.MARKDOWN
                )
                return
            
            # Создаем обновленное сообщение
            message_text = "🤖 **Список ботов:** (обновлено)\n\n"
            
            for bot_info in bots_info:
                status_emoji = "🟢" if bot_info.is_running else "🔴"
                status_text = "Запущен" if bot_info.is_running else "Остановлен"
                
                message_text += f"{status_emoji} **{bot_info.name}** - {status_text}\n"
                
                if bot_info.is_running and bot_info.pid:
                    message_text += f"   PID: {bot_info.pid}"
                    if bot_info.memory_mb:
                        message_text += f", RAM: {bot_info.memory_mb:.1f}MB"
                    message_text += "\n"
                
                message_text += "\n"
            
            # Создаем обновленную клавиатуру
            keyboard = []
            for bot_info in bots_info:
                row = []
                
                if bot_info.is_running:
                    row.append(InlineKeyboardButton("⏹️ Стоп", callback_data=f"stop_{bot_info.name}"))
                else:
                    row.append(InlineKeyboardButton("▶️ Старт", callback_data=f"start_{bot_info.name}"))
                
                row.append(InlineKeyboardButton("🔄 Рестарт", callback_data=f"restart_{bot_info.name}"))
                row.append(InlineKeyboardButton("ℹ️ Инфо", callback_data=f"info_{bot_info.name}"))
                
                keyboard.append(row)
            
            keyboard.append([InlineKeyboardButton("🔄 Обновить список", callback_data="refresh_list")])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                message_text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup
            )
            
        except Exception as e:
            logger.error(f"Ошибка при обновлении списка: {e}")
            await query.edit_message_text("❌ Ошибка при обновлении списка ботов.")
    
    def setup_application(self):
        """Настройка Telegram приложения"""
        self.application = Application.builder().token(Config.TELEGRAM_BOT_TOKEN).build()
        
        # Добавляем обработчики команд
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("list", self.list_command))
        self.application.add_handler(CommandHandler("status", self.status_command))
        self.application.add_handler(CommandHandler("monitor", self.monitor_command))
        self.application.add_handler(CommandHandler("cleanup", self.cleanup_command))
        
        # Добавляем обработчик callback кнопок
        self.application.add_handler(CallbackQueryHandler(self.button_callback))
        
        logger.info("Telegram-бот настроен и готов к работе")
    
    async def start_bot(self):
        """Запуск Telegram-бота"""
        if not self.application:
            self.setup_application()
            
        logger.info("Запускаю Telegram-бота...")
        await self.application.initialize()
        await self.application.start()
        await self.application.updater.start_polling()
        
        logger.info("Telegram-бот запущен и работает")
    
    async def stop_bot(self):
        """Остановка Telegram-бота"""
        if self.application:
            logger.info("Останавливаю Telegram-бота...")
            await self.application.updater.stop()
            await self.application.stop()
            await self.application.shutdown()
            logger.info("Telegram-бот остановлен")