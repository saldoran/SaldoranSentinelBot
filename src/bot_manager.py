"""
Модуль управления ботами для SaldoranBotSentinel
"""

import os
import subprocess
import psutil
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime

from config import Config
from logger import get_logger

logger = get_logger(__name__)


@dataclass
class BotInfo:
    """Информация о боте"""
    name: str
    path: Path
    is_running: bool
    pid: Optional[int] = None
    cpu_percent: Optional[float] = None
    memory_mb: Optional[float] = None
    logs_size_mb: Optional[float] = None
    last_commit: Optional[str] = None
    last_commit_date: Optional[str] = None


class BotManager:
    """Менеджер для управления ботами"""
    
    def __init__(self, telegram_bot=None):
        self.bots_dir = Config.BOTS_DIR
        self.telegram_bot = telegram_bot
        self._ensure_bots_directory()
        
    def _ensure_bots_directory(self):
        """Создание директории для ботов если не существует"""
        if not self.bots_dir.exists():
            self.bots_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Создана директория для ботов: {self.bots_dir}")
    
    def discover_bots(self) -> List[str]:
        """Поиск всех ботов в директории"""
        bots = []
        
        if not self.bots_dir.exists():
            logger.warning(f"Директория ботов не найдена: {self.bots_dir}")
            return bots
            
        for item in self.bots_dir.iterdir():
            if item.is_dir() and not item.name.startswith('.'):
                # Проверяем наличие скрипта run_bot или run_bot.sh
                run_script = item / 'run_bot'
                run_script_sh = item / 'run_bot.sh'
                
                if (run_script.exists() and os.access(run_script, os.X_OK)) or \
                   (run_script_sh.exists() and os.access(run_script_sh, os.X_OK)):
                    bots.append(item.name)
                    logger.debug(f"Найден бот: {item.name}")
                    
        logger.info(f"Обнаружено ботов: {len(bots)}")
        return sorted(bots)
    
    def get_bot_info(self, bot_name: str) -> Optional[BotInfo]:
        """Получение подробной информации о боте"""
        bot_path = self.bots_dir / bot_name
        
        if not bot_path.exists():
            logger.error(f"Бот {bot_name} не найден")
            return None
            
        # Проверяем запущен ли бот
        is_running, pid = self._is_bot_running(bot_name)
        
        bot_info = BotInfo(
            name=bot_name,
            path=bot_path,
            is_running=is_running,
            pid=pid
        )
        
        # Если бот запущен, получаем информацию о ресурсах
        if is_running and pid:
            try:
                process = psutil.Process(pid)
                bot_info.cpu_percent = process.cpu_percent()
                bot_info.memory_mb = process.memory_info().rss / 1024 / 1024
            except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
                logger.warning(f"Не удалось получить информацию о процессе {pid}: {e}")
        
        # Получаем размер логов
        logs_dir = bot_path / 'logs'
        if logs_dir.exists():
            bot_info.logs_size_mb = self._get_directory_size(logs_dir)
            
        # Получаем информацию о Git коммитах
        if (bot_path / '.git').exists():
            bot_info.last_commit = self._get_last_commit_hash(bot_path)
            bot_info.last_commit_date = self._get_last_commit_date(bot_path)
            
        return bot_info
    
    def _is_bot_running(self, bot_name: str) -> Tuple[bool, Optional[int]]:
        """Проверка запущен ли бот"""
        logger.debug(f"Проверка статуса бота {bot_name}, целевой пользователь: {Config.TARGET_USER}")
        
        # Сначала проверяем PID файл (более надежно для наших скриптов)
        pid_file = Path(f"/tmp/{bot_name}.pid")
        logger.debug(f"Проверка PID файла: {pid_file}")
        
        if pid_file.exists():
            try:
                with open(pid_file, 'r') as f:
                    pid = int(f.read().strip())
                
                logger.debug(f"Найден PID в файле: {pid}")
                
                # Проверяем, существует ли процесс с этим PID
                if psutil.pid_exists(pid):
                    try:
                        proc = psutil.Process(pid)
                        proc_user = proc.username()
                        logger.debug(f"Процесс {pid} существует, пользователь: {proc_user}")
                        
                        # Дополнительная проверка, что это наш процесс
                        if proc_user == Config.TARGET_USER:
                            logger.info(f"Бот {bot_name} запущен (PID: {pid})")
                            return True, pid
                        else:
                            logger.debug(f"Процесс {pid} принадлежит другому пользователю: {proc_user}")
                    except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
                        logger.debug(f"Не удалось получить информацию о процессе {pid}: {e}")
                else:
                    logger.debug(f"Процесс с PID {pid} не существует")
                        
            except (ValueError, IOError) as e:
                logger.debug(f"Ошибка чтения PID файла для {bot_name}: {e}")
        else:
            logger.debug(f"PID файл {pid_file} не найден")
        
        # Если PID файл не помог, используем старый метод поиска по процессам
        logger.debug(f"Поиск процессов бота {bot_name} по командной строке...")
        try:
            for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'username']):
                try:
                    if proc.info['username'] != Config.TARGET_USER:
                        continue
                        
                    cmdline = ' '.join(proc.info['cmdline'] or [])
                    if bot_name in cmdline and ('run_bot' in cmdline or f'{bot_name}' in cmdline):
                        logger.info(f"Найден процесс бота {bot_name} (PID: {proc.info['pid']})")
                        return True, proc.info['pid']
                        
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
                    
        except Exception as e:
            logger.error(f"Ошибка при проверке статуса бота {bot_name}: {e}")
        
        logger.debug(f"Бот {bot_name} не запущен")
        return False, None
    
    def _get_directory_size(self, path: Path) -> float:
        """Получение размера директории в MB"""
        total_size = 0
        try:
            for dirpath, dirnames, filenames in os.walk(path):
                for filename in filenames:
                    filepath = os.path.join(dirpath, filename)
                    if os.path.exists(filepath):
                        total_size += os.path.getsize(filepath)
        except Exception as e:
            logger.error(f"Ошибка при подсчете размера директории {path}: {e}")
            
        return total_size / 1024 / 1024  # Конвертируем в MB
    
    def _get_last_commit_hash(self, bot_path: Path) -> Optional[str]:
        """Получение хеша последнего коммита"""
        try:
            result = subprocess.run(
                ['git', 'rev-parse', 'HEAD'],
                cwd=bot_path,
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                return result.stdout.strip()[:8]  # Короткий хеш
        except Exception as e:
            logger.debug(f"Не удалось получить хеш коммита для {bot_path}: {e}")
            
        return None
    
    def _get_last_commit_date(self, bot_path: Path) -> Optional[str]:
        """Получение даты последнего коммита"""
        try:
            result = subprocess.run(
                ['git', 'log', '-1', '--format=%cd', '--date=short'],
                cwd=bot_path,
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except Exception as e:
            logger.debug(f"Не удалось получить дату коммита для {bot_path}: {e}")
            
        return None
    
    async def _send_telegram_notification(self, message: str):
        """Отправка уведомления в Telegram"""
        if self.telegram_bot:
            try:
                await self.telegram_bot.send_notification(message)
            except Exception as e:
                logger.error(f"Ошибка отправки Telegram уведомления: {e}")

    def start_bot(self, bot_name: str) -> bool:
        """Запуск бота"""
        bot_path = self.bots_dir / bot_name
        run_script = bot_path / 'run_bot'
        run_script_sh = bot_path / 'run_bot.sh'
        
        # Определяем какой скрипт использовать
        if run_script_sh.exists() and os.access(run_script_sh, os.X_OK):
            script_to_run = run_script_sh
        elif run_script.exists() and os.access(run_script, os.X_OK):
            script_to_run = run_script
        else:
            error_msg = f"Скрипт run_bot или run_bot.sh не найден для бота {bot_name}"
            logger.error(error_msg)
            
            # Отправляем уведомление об ошибке
            if self.telegram_bot:
                import asyncio
                try:
                    loop = asyncio.get_event_loop()
                    loop.create_task(self._send_telegram_notification(
                        f"❌ <b>Ошибка запуска бота</b>\n\n"
                        f"🤖 Бот: {bot_name}\n"
                        f"📁 Скрипт запуска не найден"
                    ))
                except Exception as e:
                    logger.error(f"Ошибка отправки уведомления: {e}")
            
            return False
            
        # Проверяем, не запущен ли уже бот
        is_running, _ = self._is_bot_running(bot_name)
        if is_running:
            logger.warning(f"Бот {bot_name} уже запущен")
            return True
            
        try:
            result = subprocess.run(
                [str(script_to_run)],
                cwd=bot_path,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                logger.info(f"Бот {bot_name} успешно запущен")
                
                # Отправляем уведомление об успешном запуске
                if self.telegram_bot:
                    import asyncio
                    try:
                        loop = asyncio.get_event_loop()
                        loop.create_task(self._send_telegram_notification(
                            f"✅ <b>Бот запущен</b>\n\n"
                            f"🤖 Бот: {bot_name}\n"
                            f"🚀 Статус: Успешно запущен"
                        ))
                    except Exception as e:
                        logger.error(f"Ошибка отправки уведомления: {e}")
                
                return True
            else:
                error_msg = f"Ошибка запуска бота {bot_name}: {result.stderr}"
                logger.error(error_msg)
                
                # Отправляем уведомление об ошибке
                if self.telegram_bot:
                    import asyncio
                    try:
                        loop = asyncio.get_event_loop()
                        loop.create_task(self._send_telegram_notification(
                            f"❌ <b>Ошибка запуска бота</b>\n\n"
                            f"🤖 Бот: {bot_name}\n"
                            f"📝 Ошибка: {result.stderr[:200]}..."
                        ))
                    except Exception as e:
                        logger.error(f"Ошибка отправки уведомления: {e}")
                
                return False
                
        except subprocess.TimeoutExpired:
            error_msg = f"Таймаут при запуске бота {bot_name}"
            logger.error(error_msg)
            
            # Отправляем уведомление о таймауте
            if self.telegram_bot:
                import asyncio
                try:
                    loop = asyncio.get_event_loop()
                    loop.create_task(self._send_telegram_notification(
                        f"⏰ <b>Таймаут запуска бота</b>\n\n"
                        f"🤖 Бот: {bot_name}\n"
                        f"⚠️ Превышено время ожидания (30 сек)"
                    ))
                except Exception as e:
                    logger.error(f"Ошибка отправки уведомления: {e}")
            
            return False
        except Exception as e:
            error_msg = f"Исключение при запуске бота {bot_name}: {e}"
            logger.error(error_msg)
            
            # Отправляем уведомление об исключении
            if self.telegram_bot:
                import asyncio
                try:
                    loop = asyncio.get_event_loop()
                    loop.create_task(self._send_telegram_notification(
                        f"💥 <b>Критическая ошибка запуска</b>\n\n"
                        f"🤖 Бот: {bot_name}\n"
                        f"🔥 Исключение: {str(e)[:200]}..."
                    ))
                except Exception as e:
                    logger.error(f"Ошибка отправки уведомления: {e}")
            
            return False
    
    def stop_bot(self, bot_name: str) -> bool:
        """Остановка бота"""
        bot_path = self.bots_dir / bot_name
        stop_script = bot_path / 'stop_bot'
        stop_script_sh = bot_path / 'stop_bot.sh'
        
        # Определяем какой скрипт использовать
        if stop_script_sh.exists() and os.access(stop_script_sh, os.X_OK):
            script_to_run = stop_script_sh
        elif stop_script.exists() and os.access(stop_script, os.X_OK):
            script_to_run = stop_script
        else:
            error_msg = f"Скрипт stop_bot или stop_bot.sh не найден для бота {bot_name}"
            logger.error(error_msg)
            
            # Отправляем уведомление об ошибке
            if self.telegram_bot:
                import asyncio
                try:
                    loop = asyncio.get_event_loop()
                    loop.create_task(self._send_telegram_notification(
                        f"❌ <b>Ошибка остановки бота</b>\n\n"
                        f"🤖 Бот: {bot_name}\n"
                        f"📁 Скрипт остановки не найден"
                    ))
                except Exception as e:
                    logger.error(f"Ошибка отправки уведомления: {e}")
            
            return False
            
        try:
            result = subprocess.run(
                [str(script_to_run)],
                cwd=bot_path,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                logger.info(f"Бот {bot_name} успешно остановлен")
                
                # Отправляем уведомление об успешной остановке
                if self.telegram_bot:
                    import asyncio
                    try:
                        loop = asyncio.get_event_loop()
                        loop.create_task(self._send_telegram_notification(
                            f"🛑 <b>Бот остановлен</b>\n\n"
                            f"🤖 Бот: {bot_name}\n"
                            f"✅ Статус: Успешно остановлен"
                        ))
                    except Exception as e:
                        logger.error(f"Ошибка отправки уведомления: {e}")
                
                return True
            else:
                error_msg = f"Ошибка остановки бота {bot_name}: {result.stderr}"
                logger.error(error_msg)
                
                # Отправляем уведомление об ошибке
                if self.telegram_bot:
                    import asyncio
                    try:
                        loop = asyncio.get_event_loop()
                        loop.create_task(self._send_telegram_notification(
                            f"❌ <b>Ошибка остановки бота</b>\n\n"
                            f"🤖 Бот: {bot_name}\n"
                            f"📝 Ошибка: {result.stderr[:200]}..."
                        ))
                    except Exception as e:
                        logger.error(f"Ошибка отправки уведомления: {e}")
                
                return False
                
        except subprocess.TimeoutExpired:
            error_msg = f"Таймаут при остановке бота {bot_name}"
            logger.error(error_msg)
            
            # Отправляем уведомление о таймауте
            if self.telegram_bot:
                import asyncio
                try:
                    loop = asyncio.get_event_loop()
                    loop.create_task(self._send_telegram_notification(
                        f"⏰ <b>Таймаут остановки бота</b>\n\n"
                        f"🤖 Бот: {bot_name}\n"
                        f"⚠️ Превышено время ожидания (30 сек)"
                    ))
                except Exception as e:
                    logger.error(f"Ошибка отправки уведомления: {e}")
            
            return False
        except Exception as e:
            error_msg = f"Исключение при остановке бота {bot_name}: {e}"
            logger.error(error_msg)
            
            # Отправляем уведомление об исключении
            if self.telegram_bot:
                import asyncio
                try:
                    loop = asyncio.get_event_loop()
                    loop.create_task(self._send_telegram_notification(
                        f"💥 <b>Критическая ошибка остановки</b>\n\n"
                        f"🤖 Бот: {bot_name}\n"
                        f"🔥 Исключение: {str(e)[:200]}..."
                    ))
                except Exception as e:
                    logger.error(f"Ошибка отправки уведомления: {e}")
            
            return False
    
    def restart_bot(self, bot_name: str) -> bool:
        """Перезапуск бота"""
        bot_path = self.bots_dir / bot_name
        restart_script = bot_path / 'restart_bot'
        restart_script_sh = bot_path / 'restart_bot.sh'
        
        # Определяем какой скрипт использовать
        script_to_run = None
        if restart_script_sh.exists() and os.access(restart_script_sh, os.X_OK):
            script_to_run = restart_script_sh
        elif restart_script.exists() and os.access(restart_script, os.X_OK):
            script_to_run = restart_script
        
        # Если есть скрипт restart_bot, используем его
        if script_to_run:
            try:
                result = subprocess.run(
                    [str(script_to_run)],
                    cwd=bot_path,
                    capture_output=True,
                    text=True,
                    timeout=60
                )
                
                if result.returncode == 0:
                    logger.info(f"Бот {bot_name} успешно перезапущен")
                    return True
                else:
                    logger.error(f"Ошибка перезапуска бота {bot_name}: {result.stderr}")
                    return False
                    
            except subprocess.TimeoutExpired:
                logger.error(f"Таймаут при перезапуске бота {bot_name}")
                return False
            except Exception as e:
                logger.error(f"Исключение при перезапуске бота {bot_name}: {e}")
                return False
        else:
            # Если нет скрипта restart_bot, делаем stop + start
            logger.info(f"Скрипт restart_bot не найден для {bot_name}, выполняем stop + start")
            if self.stop_bot(bot_name):
                # Небольшая пауза между остановкой и запуском
                import time
                time.sleep(2)
                return self.start_bot(bot_name)
            return False
    
    def get_all_bots_info(self) -> List[BotInfo]:
        """Получение информации о всех ботах"""
        bots = self.discover_bots()
        bots_info = []
        
        for bot_name in bots:
            bot_info = self.get_bot_info(bot_name)
            if bot_info:
                bots_info.append(bot_info)
                
        return bots_info