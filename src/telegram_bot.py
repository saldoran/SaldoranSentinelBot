import asyncio
from typing import Dict, List, Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from telegram.constants import ParseMode

from .config import Config
from .logger import get_logger
from .bot_manager import BotManager
from .resource_monitor import ResourceMonitor

logger = get_logger(__name__)

class TelegramBot:
    def __init__(self, config: Config, bot_manager: BotManager, resource_monitor: ResourceMonitor):
        self.config = config
        self.bot_manager = bot_manager
        self.resource_monitor = resource_monitor
        
        # Application с post_init
        self.app: Application = (
            Application.builder()
            .token(config.TELEGRAM_BOT_TOKEN)
            .post_init(self._post_init)
            .build()
        )
        
        # Регистрируем обработчики
        self._register_handlers()
        
    def _register_handlers(self):
        """Регистрация всех обработчиков команд и callback'ов"""
        # Команды
        self.app.add_handler(CommandHandler("start", self._cmd_start))
        self.app.add_handler(CommandHandler("help", self._cmd_help))
        self.app.add_handler(CommandHandler("status", self._cmd_status))
        self.app.add_handler(CommandHandler("bots", self._cmd_bots))
        self.app.add_handler(CommandHandler("resources", self._cmd_resources))
        self.app.add_handler(CommandHandler("logs", self._cmd_logs))
        
        # Callback обработчики
        self.app.add_handler(CallbackQueryHandler(self._handle_callback))
        
    async def _post_init(self, app: Application):
        """Инициализация после создания приложения"""
        logger.info("Инициализация Telegram бота...")
        
    async def start(self):
        """Запуск Telegram бота"""
        try:
            logger.info("Запуск Telegram бота...")
            await self.app.initialize()
            await self.app.updater.start_polling()
            await self.app.start()
            logger.info("Telegram бот успешно запущен")
        except Exception as e:
            logger.error(f"Ошибка при запуске Telegram бота: {e}")
            raise
            
    async def stop(self):
        """Остановка Telegram бота"""
        try:
            logger.info("Остановка Telegram бота...")
            await self.app.updater.stop()
            await self.app.stop()
            await self.app.shutdown()
            logger.info("Telegram бот остановлен")
        except Exception as e:
            logger.error(f"Ошибка при остановке Telegram бота: {e}")
            
    async def send_startup_notification(self):
        """Отправка уведомления о запуске"""
        try:
            message = "✅ SaldoranSentinelBot запущен\n\nИспользуйте /help для списка команд"
            await self.app.bot.send_message(
                chat_id=self.config.TELEGRAM_ADMIN_ID,
                text=message,
                parse_mode=ParseMode.HTML
            )
        except Exception as e:
            logger.error(f"Ошибка при отправке уведомления о запуске: {e}")
            
    async def send_shutdown_notification(self):
        """Отправка уведомления о завершении"""
        try:
            message = "🔄 SaldoranSentinelBot завершает работу..."
            await self.app.bot.send_message(
                chat_id=self.config.TELEGRAM_ADMIN_ID,
                text=message,
                parse_mode=ParseMode.HTML
            )
        except Exception as e:
            logger.error(f"Ошибка при отправке уведомления о завершении: {e}")
            
    async def send_notification(self, message: str):
        """Отправка уведомления администратору"""
        try:
            await self.app.bot.send_message(
                chat_id=self.config.TELEGRAM_ADMIN_ID,
                text=message,
                parse_mode=ParseMode.HTML
            )
        except Exception as e:
            logger.error(f"Ошибка при отправке уведомления: {e}")
            
    def _is_admin(self, user_id: int) -> bool:
        """Проверка прав администратора"""
        return user_id == self.config.TELEGRAM_ADMIN_ID
        
    async def _cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /start"""
        if not self._is_admin(update.effective_user.id):
            return
            
        message = (
            "🤖 <b>SaldoranSentinelBot</b>\n\n"
            "Система мониторинга и управления ботами\n\n"
            "Используйте /help для списка команд"
        )
        await update.message.reply_text(message, parse_mode=ParseMode.HTML)
        
    async def _cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /help"""
        if not self._is_admin(update.effective_user.id):
            return
            
        message = (
            "📋 <b>Доступные команды:</b>\n\n"
            "/start - Запуск бота\n"
            "/help - Справка\n"
            "/status - Общий статус системы\n"
            "/bots - Управление ботами\n"
            "/resources - Мониторинг ресурсов\n"
            "/logs - Просмотр логов\n"
        )
        await update.message.reply_text(message, parse_mode=ParseMode.HTML)
        
    async def _cmd_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /status"""
        if not self._is_admin(update.effective_user.id):
            return
            
        try:
            # Получаем статус системы
            system_stats = await self.resource_monitor.get_system_stats()
            available_bots = self.bot_manager.discover_bots()
            
            message = (
                f"📊 <b>Статус системы</b>\n\n"
                f"🖥️ <b>Ресурсы:</b>\n"
                f"CPU: {system_stats['cpu_percent']:.1f}%\n"
                f"RAM: {system_stats['memory_percent']:.1f}%\n\n"
                f"🤖 <b>Боты:</b>\n"
                f"Найдено: {len(available_bots)}\n"
            )
            
            if available_bots:
                message += "\n<b>Доступные боты:</b>\n"
                for bot_name in available_bots:
                    message += f"• {bot_name}\n"
                    
        except Exception as e:
            message = f"❌ Ошибка получения статуса: {e}"
            
        await update.message.reply_text(message, parse_mode=ParseMode.HTML)
        
    async def _cmd_bots(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /bots"""
        if not self._is_admin(update.effective_user.id):
            return
            
        try:
            available_bots = self.bot_manager.discover_bots()
            
            # Получаем информацию о всех ботах и определяем запущенные
            running_bots = []
            for bot_name in available_bots:
                bot_info = self.bot_manager.get_bot_info(bot_name)
                if bot_info and bot_info.is_running:
                    running_bots.append(bot_name)
            
            keyboard = []
            
            # Кнопки для каждого бота
            for bot_name in available_bots:
                is_running = bot_name in running_bots
                status_icon = "🟢" if is_running else "🔴"
                action = "stop" if is_running else "start"
                action_text = "Остановить" if is_running else "Запустить"
                
                keyboard.append([
                    InlineKeyboardButton(
                        f"{status_icon} {bot_name}",
                        callback_data=f"bot_info_{bot_name}"
                    ),
                    InlineKeyboardButton(
                        action_text,
                        callback_data=f"bot_{action}_{bot_name}"
                    )
                ])
                
            # Кнопка обновления
            keyboard.append([
                InlineKeyboardButton("🔄 Обновить", callback_data="bots_refresh")
            ])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            message = (
                f"🤖 <b>Управление ботами</b>\n\n"
                f"Найдено ботов: {len(available_bots)}\n"
                f"Запущено: {len(running_bots)}\n"
            )
            
            await update.message.reply_text(
                message,
                reply_markup=reply_markup,
                parse_mode=ParseMode.HTML
            )
            
        except Exception as e:
            await update.message.reply_text(
                f"❌ Ошибка получения списка ботов: {e}",
                parse_mode=ParseMode.HTML
            )
            
    async def _cmd_resources(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /resources"""
        if not self._is_admin(update.effective_user.id):
            return
            
        try:
            stats = await self.resource_monitor.get_system_stats()
            
            message = (
                f"📊 <b>Мониторинг ресурсов</b>\n\n"
                f"🖥️ <b>Система:</b>\n"
                f"CPU: {stats['cpu_percent']:.1f}%\n"
                f"RAM: {stats['memory_percent']:.1f}%\n"
                f"Доступно RAM: {stats['memory_available_mb']:.0f}MB\n"
                f"Всего RAM: {stats['memory_total_mb']:.0f}MB\n\n"
            )
            
            if stats.get('top_processes'):
                message += "🔝 <b>Топ процессов по памяти:</b>\n"
                for proc in stats['top_processes'][:5]:
                    message += f"• {proc.name} ({proc.username}): {proc.memory_mb:.1f}MB\n"
                    
            keyboard = [[
                InlineKeyboardButton("🔄 Обновить", callback_data="resources_refresh")
            ]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                message,
                reply_markup=reply_markup,
                parse_mode=ParseMode.HTML
            )
            
        except Exception as e:
            await update.message.reply_text(
                f"❌ Ошибка получения статистики ресурсов: {e}",
                parse_mode=ParseMode.HTML
            )
            
    async def _cmd_logs(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /logs"""
        if not self._is_admin(update.effective_user.id):
            return
            
        try:
            # Получаем последние строки лога
            log_lines = []
            # Формируем имя файла лога на текущую дату
            from datetime import datetime
            today = datetime.now().strftime("%d%m%Y")
            log_file = self.config.LOGS_DIR / f"sentinel_{today}.log"
            
            try:
                with open(log_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    log_lines = lines[-20:]  # Последние 20 строк
            except FileNotFoundError:
                log_lines = ["Лог файл не найден"]
                
            message = "📋 <b>Последние записи лога:</b>\n\n"
            message += "<code>" + "".join(log_lines) + "</code>"
            
            # Ограничиваем длину сообщения
            if len(message) > 4000:
                message = message[:4000] + "...</code>"
                
            await update.message.reply_text(message, parse_mode=ParseMode.HTML)
            
        except Exception as e:
            await update.message.reply_text(
                f"❌ Ошибка получения логов: {e}",
                parse_mode=ParseMode.HTML
            )
            
    async def _handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка callback запросов"""
        query = update.callback_query
        await query.answer()
        
        if not self._is_admin(query.from_user.id):
            return
            
        data = query.data
        
        try:
            if data.startswith("bot_start_"):
                bot_name = data.replace("bot_start_", "")
                result = self.bot_manager.start_bot(bot_name)
                if result:
                    await query.edit_message_text(
                        f"✅ Бот {bot_name} запущен",
                        parse_mode=ParseMode.HTML
                    )
                else:
                    await query.edit_message_text(
                        f"❌ Ошибка запуска бота {bot_name}",
                        parse_mode=ParseMode.HTML
                    )
                    
            elif data.startswith("bot_stop_"):
                bot_name = data.replace("bot_stop_", "")
                result = self.bot_manager.stop_bot(bot_name)
                if result:
                    await query.edit_message_text(
                        f"✅ Бот {bot_name} остановлен",
                        parse_mode=ParseMode.HTML
                    )
                else:
                    await query.edit_message_text(
                        f"❌ Ошибка остановки бота {bot_name}",
                        parse_mode=ParseMode.HTML
                    )
                    
            elif data.startswith("bot_info_"):
                bot_name = data.replace("bot_info_", "")
                bot_info = self.bot_manager.get_bot_info(bot_name)
                
                if bot_info:
                    message = (
                        f"🤖 <b>Информация о боте {bot_name}</b>\n\n"
                        f"Статус: {'🟢 Запущен' if bot_info.is_running else '🔴 Остановлен'}\n"
                        f"PID: {bot_info.pid or 'N/A'}\n"
                        f"Память: {bot_info.memory_mb:.1f}MB\n" if bot_info.memory_mb else ""
                        f"Путь: {bot_info.path}\n"
                    )
                else:
                    message = f"🤖 <b>Бот {bot_name}</b>\n\nБот не найден"
                    
                await query.edit_message_text(message, parse_mode=ParseMode.HTML)
                
            elif data == "bots_refresh":
                # Для обновления создаем новое сообщение вместо редактирования
                available_bots = self.bot_manager.discover_bots()
                
                # Получаем информацию о всех ботах и определяем запущенные
                running_bots = []
                for bot_name in available_bots:
                    bot_info = self.bot_manager.get_bot_info(bot_name)
                    if bot_info and bot_info.is_running:
                        running_bots.append(bot_name)
                
                keyboard = []
                
                # Кнопки для каждого бота
                for bot_name in available_bots:
                    is_running = bot_name in running_bots
                    status_icon = "🟢" if is_running else "🔴"
                    action = "stop" if is_running else "start"
                    action_text = "Остановить" if is_running else "Запустить"
                    
                    keyboard.append([
                        InlineKeyboardButton(
                            f"{status_icon} {bot_name}",
                            callback_data=f"bot_info_{bot_name}"
                        ),
                        InlineKeyboardButton(
                            action_text,
                            callback_data=f"bot_{action}_{bot_name}"
                        )
                    ])
                    
                # Кнопка обновления
                keyboard.append([
                    InlineKeyboardButton("🔄 Обновить", callback_data="bots_refresh")
                ])
                
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                # Добавляем временную метку для уникальности сообщения
                from datetime import datetime
                timestamp = datetime.now().strftime("%H:%M:%S")
                
                message = (
                    f"🤖 <b>Управление ботами</b>\n\n"
                    f"Найдено ботов: {len(available_bots)}\n"
                    f"Запущено: {len(running_bots)}\n"
                    f"<i>Обновлено: {timestamp}</i>"
                )
                
                try:
                    await query.edit_message_text(
                        message,
                        reply_markup=reply_markup,
                        parse_mode=ParseMode.HTML
                    )
                except Exception as e:
                    # Если не удалось отредактировать, отправляем новое сообщение
                    await query.message.reply_text(
                        message,
                        reply_markup=reply_markup,
                        parse_mode=ParseMode.HTML
                    )
                
            elif data == "resources_refresh":
                # Для callback нужно создать fake update с message
                fake_update = type('obj', (object,), {
                    'effective_user': update.effective_user,
                    'message': type('obj', (object,), {
                        'reply_text': query.edit_message_text
                    })()
                })()
                await self._cmd_resources(fake_update, context)
                
        except Exception as e:
            logger.error(f"Ошибка обработки callback {data}: {e}")
            await query.edit_message_text(
                f"❌ Ошибка обработки команды: {e}",
                parse_mode=ParseMode.HTML
            )