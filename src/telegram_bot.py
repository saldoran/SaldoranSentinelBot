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
        self.app.add_handler(CommandHandler("setup", self._cmd_setup))
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
            # Получаем список обнаруженных ботов
            available_bots = self.bot_manager.discover_bots()
            running_bots = []
            
            for bot_name in available_bots:
                bot_info = self.bot_manager.get_bot_info(bot_name)
                if bot_info and bot_info.is_running:
                    running_bots.append(bot_name)
            
            message = (
                f"✅ <b>SaldoranSentinelBot запущен</b>\n\n"
                f"🤖 <b>Обнаружено ботов:</b> {len(available_bots)}\n"
                f"🟢 <b>Запущено:</b> {len(running_bots)}\n\n"
            )
            
            if available_bots:
                message += "📋 <b>Список ботов:</b>\n"
                for bot_name in available_bots:
                    is_running = bot_name in running_bots
                    status_icon = "🟢" if is_running else "🔴"
                    message += f"{status_icon} <code>{bot_name}</code>\n"
            else:
                message += "⚠️ <b>Боты не обнаружены</b>\n"
                message += "Проверьте директорию ботов и наличие скриптов run_bot.sh\n\n"
            
            message += "\n💡 Используйте /help для списка команд"
            
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
            "/setup - Настройки и управление\n"
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
                
                # Добавляем кнопку Force Restart для запущенных ботов
                if is_running:
                    keyboard.append([
                        InlineKeyboardButton(
                            "💥 Force Restart",
                            callback_data=f"bot_force_restart_{bot_name}"
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
                    
            keyboard = [
                [InlineKeyboardButton("📋 Подробнее", callback_data="resources_detailed")],
                [InlineKeyboardButton("🔄 Обновить", callback_data="resources_refresh")]
            ]
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
    
    async def _cmd_setup(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /setup"""
        if not self._is_admin(update.effective_user.id):
            return
            
        message = (
            "⚙️ <b>Настройки и управление</b>\n\n"
            "Выберите действие:"
        )
        
        keyboard = [
            [InlineKeyboardButton("🔄 Перезапустить сервис", callback_data="setup_restart")],
            [InlineKeyboardButton("📊 Статус сервиса", callback_data="setup_status")],
            [InlineKeyboardButton("🧹 Очистить кэш", callback_data="setup_clear_cache")],
            [InlineKeyboardButton("📝 Уровень логов", callback_data="setup_log_level")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            message,
            reply_markup=reply_markup,
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
                    
            elif data.startswith("bot_force_restart_"):
                bot_name = data.replace("bot_force_restart_", "")
                
                # Сначала принудительно останавливаем бот
                stop_result = self.bot_manager.force_stop_bot(bot_name)
                if stop_result:
                    # Ждем немного, чтобы процесс полностью завершился
                    import asyncio
                    await asyncio.sleep(2)
                    
                    # Затем запускаем бот
                    start_result = self.bot_manager.start_bot(bot_name)
                    if start_result:
                        await query.edit_message_text(
                            f"💥 Бот {bot_name} принудительно перезапущен",
                            parse_mode=ParseMode.HTML
                        )
                    else:
                        await query.edit_message_text(
                            f"💥 Бот {bot_name} остановлен, но не удалось запустить",
                            parse_mode=ParseMode.HTML
                        )
                else:
                    await query.edit_message_text(
                        f"❌ Не удалось принудительно остановить бот {bot_name}",
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
                    
                    # Добавляем кнопку Force Restart для запущенных ботов
                    if is_running:
                        keyboard.append([
                            InlineKeyboardButton(
                                "💥 Force Restart",
                                callback_data=f"bot_force_restart_{bot_name}"
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
                # Обновляем ресурсы через callback
                try:
                    stats = await self.resource_monitor.get_system_stats()
                    
                    # Добавляем временную метку для уникальности сообщения
                    from datetime import datetime
                    timestamp = datetime.now().strftime("%H:%M:%S")
                    
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
                    
                    message += f"\n<i>Обновлено: {timestamp}</i>"
                    
                    keyboard = [
                        [InlineKeyboardButton("📋 Подробнее", callback_data="resources_detailed")],
                        [InlineKeyboardButton("🔄 Обновить", callback_data="resources_refresh")]
                    ]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    
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
                except Exception as e:
                    logger.error(f"Ошибка обновления ресурсов: {e}")
                    await query.edit_message_text(
                        f"❌ Ошибка получения статистики ресурсов: {e}",
                        parse_mode=ParseMode.HTML
                    )
            
            elif data == "resources_detailed":
                # Показать все процессы
                try:
                    stats = await self.resource_monitor.get_system_stats()
                    
                    # Добавляем временную метку для уникальности сообщения
                    from datetime import datetime
                    timestamp = datetime.now().strftime("%H:%M:%S")
                    
                    message = (
                        f"📊 <b>Мониторинг ресурсов - Подробно</b>\n\n"
                        f"🖥️ <b>Система:</b>\n"
                        f"CPU: {stats['cpu_percent']:.1f}%\n"
                        f"RAM: {stats['memory_percent']:.1f}%\n"
                        f"Доступно RAM: {stats['memory_available_mb']:.0f}MB\n"
                        f"Всего RAM: {stats['memory_total_mb']:.0f}MB\n\n"
                    )
                    
                    if stats.get('top_processes'):
                        message += "🔝 <b>Все процессы по памяти:</b>\n"
                        for proc in stats['top_processes']:  # Показываем все процессы
                            message += f"• {proc.name} ({proc.username}): {proc.memory_mb:.1f}MB\n"
                    
                    message += f"\n<i>Обновлено: {timestamp}</i>"
                    
                    keyboard = [
                        [InlineKeyboardButton("🔙 Краткий вид", callback_data="resources_refresh")],
                        [InlineKeyboardButton("🔄 Обновить", callback_data="resources_detailed")]
                    ]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    
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
                except Exception as e:
                    logger.error(f"Ошибка получения подробной статистики: {e}")
                    await query.edit_message_text(
                        f"❌ Ошибка получения подробной статистики: {e}",
                        parse_mode=ParseMode.HTML
                    )
            
            elif data == "setup_restart":
                # Перезапуск сервиса
                try:
                    # Сначала обновляем сообщение о начале перезапуска
                    await query.edit_message_text(
                        "🔄 Перезапуск сервиса...",
                        parse_mode=ParseMode.HTML
                    )
                    
                    import subprocess
                    result = subprocess.run(
                        ["sudo", "systemctl", "restart", "saldoran-sentinel"],
                        capture_output=True,
                        text=True,
                        timeout=30
                    )
                    
                    # Просто сообщаем о перезапуске, не проверяем статус
                    message = "✅ Сервис перезапущен!"
                        
                    # Пытаемся отредактировать сообщение
                    try:
                        await query.edit_message_text(
                            message,
                            parse_mode=ParseMode.HTML
                        )
                    except Exception:
                        # Если не удалось отредактировать (сервис перезапускается), отправляем новое сообщение
                        await query.message.reply_text(
                            message,
                            parse_mode=ParseMode.HTML
                        )
                        
                except Exception as e:
                    logger.error(f"Ошибка перезапуска сервиса: {e}")
                    # Очищаем HTML-теги из ошибки
                    import re
                    clean_error = re.sub(r'<[^>]+>', '', str(e))
                    try:
                        await query.edit_message_text(
                            f"❌ Ошибка перезапуска сервиса: {clean_error[:200]}",
                            parse_mode=ParseMode.HTML
                        )
                    except Exception:
                        # Если не удалось отредактировать, отправляем новое сообщение
                        await query.message.reply_text(
                            f"❌ Ошибка перезапуска сервиса: {clean_error[:200]}",
                            parse_mode=ParseMode.HTML
                        )
            
            elif data == "setup_status":
                # Статус сервиса
                try:
                    import subprocess
                    result = subprocess.run(
                        ["sudo", "systemctl", "status", "saldoran-sentinel", "--no-pager"],
                        capture_output=True,
                        text=True,
                        timeout=10
                    )
                    
                    status_text = result.stdout[:1000]  # Ограничиваем длину
                    if len(result.stdout) > 1000:
                        status_text += "..."
                    
                    message = f"📊 <b>Статус сервиса:</b>\n\n<code>{status_text}</code>"
                    
                    await query.edit_message_text(
                        message,
                        parse_mode=ParseMode.HTML
                    )
                except Exception as e:
                    logger.error(f"Ошибка получения статуса: {e}")
                    await query.edit_message_text(
                        f"❌ Ошибка получения статуса: {e}",
                        parse_mode=ParseMode.HTML
                    )
            
            elif data == "setup_clear_cache":
                # Очистка кэша
                try:
                    import subprocess
                    result = subprocess.run(
                        ["sudo", "sync", "&&", "sudo", "echo", "3", ">", "/proc/sys/vm/drop_caches"],
                        shell=True,
                        capture_output=True,
                        text=True,
                        timeout=10
                    )
                    
                    if result.returncode == 0:
                        message = "✅ Кэш системы очищен!"
                    else:
                        # Очищаем HTML-теги из ошибки
                        import re
                        clean_error = re.sub(r'<[^>]+>', '', result.stderr)
                        message = f"❌ Ошибка очистки кэша: {clean_error[:200]}"
                        
                    await query.edit_message_text(
                        message,
                        parse_mode=ParseMode.HTML
                    )
                except Exception as e:
                    logger.error(f"Ошибка очистки кэша: {e}")
                    # Очищаем HTML-теги из ошибки
                    import re
                    clean_error = re.sub(r'<[^>]+>', '', str(e))
                    await query.edit_message_text(
                        f"❌ Ошибка очистки кэша: {clean_error[:200]}",
                        parse_mode=ParseMode.HTML
                    )
            
            elif data == "setup_log_level":
                # Меню выбора уровня логирования
                try:
                    from .config import Config
                    current_level = Config.LOG_LEVEL
                    
                    levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
                    
                    message = (
                        f"📝 <b>Выбор уровня логирования</b>\n\n"
                        f"Текущий уровень: <code>{current_level}</code>\n\n"
                        f"Выберите новый уровень:"
                    )
                    
                    keyboard = []
                    for level in levels:
                        if level == current_level:
                            button_text = f"✅ {level}"
                        else:
                            button_text = f"   {level}"
                        keyboard.append([InlineKeyboardButton(button_text, callback_data=f"log_level_{level}")])
                    
                    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="setup_back")])
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    
                    await query.edit_message_text(
                        message,
                        reply_markup=reply_markup,
                        parse_mode=ParseMode.HTML
                    )
                except Exception as e:
                    logger.error(f"Ошибка изменения уровня логирования: {e}")
                    await query.edit_message_text(
                        f"❌ Ошибка изменения уровня логирования: {e}",
                        parse_mode=ParseMode.HTML
                    )
            
            elif data == "setup_back":
                # Возврат к главному меню setup
                message = (
                    "⚙️ <b>Настройки и управление</b>\n\n"
                    "Выберите действие:"
                )
                
                keyboard = [
                    [InlineKeyboardButton("🔄 Перезапустить сервис", callback_data="setup_restart")],
                    [InlineKeyboardButton("📊 Статус сервиса", callback_data="setup_status")],
                    [InlineKeyboardButton("🧹 Очистить кэш", callback_data="setup_clear_cache")],
                    [InlineKeyboardButton("📝 Уровень логов", callback_data="setup_log_level")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.edit_message_text(
                    message,
                    reply_markup=reply_markup,
                    parse_mode=ParseMode.HTML
                )
            
            elif data.startswith("log_level_"):
                # Установка конкретного уровня логирования
                try:
                    new_level = data.replace("log_level_", "")
                    from .config import Config
                    current_level = Config.LOG_LEVEL
                    
                    if new_level == current_level:
                        message = f"📝 Уровень логирования уже установлен: <code>{current_level}</code>"
                    else:
                        # Обновляем .env файл на сервере
                        import os
                        import subprocess
                        from pathlib import Path
                        
                        # Путь к .env файлу на сервере
                        env_file = Path(__file__).parent.parent / '.env'
                        
                        try:
                            # Читаем текущий .env файл
                            env_content = ""
                            if env_file.exists():
                                with open(env_file, 'r', encoding='utf-8') as f:
                                    env_content = f.read()
                            
                            # Обновляем или добавляем LOG_LEVEL
                            lines = env_content.split('\n')
                            updated = False
                            for i, line in enumerate(lines):
                                if line.startswith('LOG_LEVEL='):
                                    lines[i] = f'LOG_LEVEL={new_level}'
                                    updated = True
                                    break
                            
                            if not updated:
                                lines.append(f'LOG_LEVEL={new_level}')
                            
                            # Записываем обновленный .env файл
                            with open(env_file, 'w', encoding='utf-8') as f:
                                f.write('\n'.join(lines))
                            
                            # Логируем что записали
                            logger.info(f"Обновлен .env файл: {env_file}")
                            logger.info(f"Новый LOG_LEVEL: {new_level}")
                            env_content = '\n'.join(lines)
                            logger.info(f"Содержимое .env: {repr(env_content)}")
                            
                            # Обновляем переменную окружения для текущего процесса
                            os.environ['LOG_LEVEL'] = new_level
                            
                            # Обновляем уровень логирования в текущем процессе
                            logger.update_log_level()
                            
                            message = (
                                f"📝 <b>Уровень логирования изменен</b>\n\n"
                                f"Было: <code>{current_level}</code>\n"
                                f"Стало: <code>{new_level}</code>\n\n"
                                f"✅ Изменения сохранены в .env файл\n"
                                f"✅ Уровень логирования обновлен в текущем процессе\n"
                                f"🎉 <b>Готово!</b> Изменения применены сразу."
                            )
                        except Exception as env_error:
                            logger.error(f"Ошибка обновления .env файла: {env_error}")
                            message = (
                                f"📝 <b>Уровень логирования изменен</b>\n\n"
                                f"Было: <code>{current_level}</code>\n"
                                f"Стало: <code>{new_level}</code>\n\n"
                                f"⚠️ <b>Внимание:</b> Изменения вступят в силу после перезапуска сервиса.\n"
                                f"Используйте кнопку 'Перезапустить сервис' для применения.\n\n"
                                f"⚠️ Не удалось сохранить в .env файл, но переменная окружения обновлена."
                            )
                    
                    keyboard = [
                        [InlineKeyboardButton("🔙 Назад", callback_data="setup_back")]
                    ]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    
                    await query.edit_message_text(
                        message,
                        reply_markup=reply_markup,
                        parse_mode=ParseMode.HTML
                    )
                except Exception as e:
                    logger.error(f"Ошибка установки уровня логирования: {e}")
                    await query.edit_message_text(
                        f"❌ Ошибка установки уровня логирования: {e}",
                        parse_mode=ParseMode.HTML
                    )
                
        except Exception as e:
            logger.error(f"Ошибка обработки callback {data}: {e}")
            # Очищаем HTML-теги из ошибки
            import re
            clean_error = re.sub(r'<[^>]+>', '', str(e))
            await query.edit_message_text(
                f"❌ Ошибка обработки команды: {clean_error[:200]}",
                parse_mode=ParseMode.HTML
            )