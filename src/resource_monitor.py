"""
Модуль мониторинга системных ресурсов для SaldoranBotSentinel
"""

import asyncio
import os
import psutil
import re
import subprocess
import time
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime

from .config import Config
from .logger import get_logger

logger = get_logger(__name__)


@dataclass
class ProcessInfo:
    """Информация о процессе"""
    pid: int
    name: str
    username: str
    cpu_percent: float
    memory_mb: float
    cmdline: str


@dataclass
class SystemStats:
    """Статистика системы"""
    cpu_percent: float
    memory_total_mb: float
    memory_available_mb: float
    memory_used_mb: float
    memory_percent: float
    top_processes: List[ProcessInfo]


class ResourceMonitor:
    """Монитор системных ресурсов"""
    
    def __init__(self, telegram_bot=None):
        self.target_user = Config.TARGET_USER
        self.max_cpu_percent = Config.MAX_CPU_PERCENT
        self.min_free_ram_mb = Config.MIN_FREE_RAM_MB
        self.monitoring_interval = Config.MONITORING_INTERVAL
        self._last_check_time = None
        self._monitoring_task = None
        self.telegram_bot = telegram_bot
        
    async def start(self):
        """Запуск мониторинга ресурсов"""
        logger.info("Запуск мониторинга ресурсов...")
        # Запускаем периодический мониторинг
        self._monitoring_task = asyncio.create_task(self._monitoring_loop())
        
    async def _monitoring_loop(self):
        """Основной цикл мониторинга ресурсов"""
        logger.info(f"Запуск цикла мониторинга с интервалом {self.monitoring_interval} секунд")
        
        while True:
            try:
                await asyncio.sleep(self.monitoring_interval)
                
                # Проверяем критическое состояние памяти
                if self.check_memory_critical():
                    logger.warning("Обнаружено критическое состояние памяти!")
                    self.emergency_memory_cleanup()
                
                # Проверяем критическое использование CPU
                cpu_critical, cpu_percent = self.check_cpu_critical()
                if cpu_critical:
                    logger.warning("Обнаружено критическое использование CPU!")
                    # CPU уведомление уже отправляется в check_cpu_critical()
                
            except asyncio.CancelledError:
                logger.info("Цикл мониторинга остановлен")
                break
            except Exception as e:
                logger.error(f"Ошибка в цикле мониторинга: {e}")
                await asyncio.sleep(10)  # Пауза перед повтором при ошибке
        
    async def stop(self):
        """Остановка мониторинга ресурсов"""
        logger.info("Остановка мониторинга ресурсов...")
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
        
    async def get_system_stats(self) -> Dict:
        """Получение статистики системы"""
        # CPU статистика
        cpu_percent = psutil.cpu_percent(interval=1)
        
        # Память
        memory = psutil.virtual_memory()
        memory_total_mb = memory.total / 1024 / 1024
        memory_available_mb = memory.available / 1024 / 1024
        memory_used_mb = memory.used / 1024 / 1024
        memory_percent = memory.percent
        
        # Топ процессов по использованию памяти
        top_processes = self._get_top_memory_processes(limit=10)
        
        return {
            'cpu_percent': cpu_percent,
            'memory_total_mb': memory_total_mb,
            'memory_available_mb': memory_available_mb,
            'memory_used_mb': memory_used_mb,
            'memory_percent': memory_percent,
            'top_processes': top_processes
        }
    
    def _get_top_memory_processes(self, limit: int = 10) -> List[ProcessInfo]:
        """Получение топ процессов по использованию памяти"""
        processes = []
        
        def safe_encode_string(s: str) -> str:
            """Безопасное кодирование строки для избежания ошибок с surrogates"""
            if not s:
                return ""
            try:
                # Удаляем проблемные символы и кодируем в UTF-8
                return s.encode('utf-8', errors='ignore').decode('utf-8')
            except Exception:
                return "unknown"
        
        try:
            for proc in psutil.process_iter(['pid', 'ppid', 'name', 'username', 'memory_info', 'cmdline']):
                try:
                        
                    memory_mb = proc.info['memory_info'].rss / 1024 / 1024
                    
                    # Безопасно обрабатываем имя процесса и командную строку
                    process_name = safe_encode_string(proc.info['name'] or "unknown")
                    cmdline_list = proc.info['cmdline'] or []
                    cmdline = safe_encode_string(' '.join(str(arg) for arg in cmdline_list))
                    
                    # Пытаемся определить имя бота для Python процессов
                    bot_name = self._get_bot_name_for_process(
                        proc.info['pid'],
                        proc.info.get('ppid'),
                        process_name,
                        cmdline,
                    )
                    if bot_name:
                        process_name = f"🤖 {bot_name}"
                    
                    # Получаем CPU процент для процесса
                    cpu_percent = proc.cpu_percent()
                    
                    process_info = ProcessInfo(
                        pid=proc.info['pid'],
                        name=process_name,
                        username=proc.info['username'],
                        cpu_percent=cpu_percent,
                        memory_mb=memory_mb,
                        cmdline=cmdline[:100]  # Ограничиваем длину командной строки
                    )
                    
                    processes.append(process_info)
                    
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue
                    
        except Exception as e:
            logger.error(f"Ошибка при получении списка процессов: {e}")
            
        # Сортируем по использованию памяти (по убыванию)
        processes.sort(key=lambda x: x.memory_mb, reverse=True)
        return processes[:limit]
    
    def _get_bot_name_for_process(
        self,
        pid: int,
        ppid: Optional[int],
        process_name: str,
        cmdline: str,
    ) -> Optional[str]:
        """Определение имени бота по процессу"""
        try:
            # Проверяем только Python процессы
            if process_name.lower() not in ['python', 'python3', 'python3.10', 'python3.11', 'python3.12']:
                return None
            
            # Метод 1: Проверяем PID файлы ботов в /tmp
            tmp_dir = Path('/tmp')
            for pid_file in tmp_dir.glob('*.pid'):
                try:
                    with open(pid_file, 'r') as f:
                        file_pid = int(f.read().strip())
                        if file_pid == pid:
                            bot_name = pid_file.stem  # Имя файла без расширения
                            logger.debug(f"Найден бот {bot_name} по PID файлу для процесса {pid}")
                            return bot_name
                        if ppid is not None and file_pid == ppid:
                            bot_name = pid_file.stem  # Имя файла без расширения
                            logger.debug(f"Найден бот {bot_name} по PID файлу для PPID {ppid} (PID={pid})")
                            return f"{bot_name}_sub"
                except (ValueError, IOError):
                    continue
            
            # Метод 2: Анализируем командную строку для поиска имени бота
            # Ищем в test_bot директории
            match = re.search(r'/test_bot/([^/]+)/', cmdline)
            if match:
                potential_bot_name = match.group(1)
                logger.debug(f"Найден бот {potential_bot_name} по пути test_bot для процесса {pid}")
                return potential_bot_name
            
            # Ищем паттерны типа /path/to/bot_name/run_bot.sh
            match = re.search(r'/([^/]+)/run_bot', cmdline)
            if match:
                potential_bot_name = match.group(1)
                logger.debug(f"Найден бот {potential_bot_name} по run_bot скрипту для процесса {pid}")
                return potential_bot_name
            
            # Ищем паттерны типа python /path/to/bot_name/main.py
            match = re.search(r'/([^/]+)/main\.py', cmdline)
            if match:
                potential_bot_name = match.group(1)
                logger.debug(f"Найден бот {potential_bot_name} по main.py для процесса {pid}")
                return potential_bot_name
            
            return None
            
        except Exception as e:
            logger.debug(f"Ошибка при определении имени бота для PID {pid}: {e}")
            return None
    
    
    def find_memory_hog_process(self) -> Optional[ProcessInfo]:
        """Поиск самого 'жрущего' процесса пользователя"""
        top_processes = self._get_top_memory_processes(limit=1)
        
        if top_processes:
            heaviest_process = top_processes[0]
            logger.info(f"Самый 'жрущий' процесс: PID={heaviest_process.pid}, "
                       f"Memory={heaviest_process.memory_mb:.1f}MB, "
                       f"Name={heaviest_process.name}")
            return heaviest_process
            
        return None
    
    def kill_process(self, pid: int, process_name: str = "unknown") -> bool:
        """Принудительное завершение процесса"""
        try:
            process = psutil.Process(pid)
            
            # Сначала пытаемся мягко завершить
            logger.info(f"Попытка мягкого завершения процесса {process_name} (PID: {pid})")
            process.terminate()
            
            # Ждем 5 секунд
            try:
                process.wait(timeout=5)
                logger.info(f"Процесс {process_name} (PID: {pid}) успешно завершен")
                return True
            except psutil.TimeoutExpired:
                # Если не завершился мягко, убиваем принудительно
                logger.warning(f"Принудительное завершение процесса {process_name} (PID: {pid})")
                process.kill()
                process.wait(timeout=3)
                logger.info(f"Процесс {process_name} (PID: {pid}) принудительно завершен")
                return True
                
        except psutil.NoSuchProcess:
            logger.info(f"Процесс {process_name} (PID: {pid}) уже не существует")
            return True
        except psutil.AccessDenied:
            logger.error(f"Нет прав для завершения процесса {process_name} (PID: {pid})")
            return False
        except Exception as e:
            logger.error(f"Ошибка при завершении процесса {process_name} (PID: {pid}): {e}")
            return False
    
    def clear_memory_cache(self) -> bool:
        """Очистка кэша памяти системы"""
        try:
            logger.info("Выполняется очистка кэша памяти...")
            
            # Выполняем команду очистки кэша
            result = subprocess.run(
                ['sudo', 'sysctl', '-w', 'vm.drop_caches=3'],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                logger.info("Кэш памяти успешно очищен")
                return True
            else:
                logger.error(f"Ошибка при очистке кэша: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            logger.error("Таймаут при очистке кэша памяти")
            return False
        except Exception as e:
            logger.error(f"Исключение при очистке кэша памяти: {e}")
            return False
    
    def check_memory_critical(self) -> bool:
        """Проверка критического состояния памяти"""
        # Перезагружаем конфиг для актуальных настроек
        Config.reload_config()
        
        memory = psutil.virtual_memory()
        available_mb = memory.available / 1024 / 1024
        memory_percent = memory.percent
        
        # Проверяем по проценту (новые настройки) или по минимуму MB (старые настройки)
        is_critical_percent = memory_percent > Config.RAM_THRESHOLD
        is_critical_mb = available_mb < self.min_free_ram_mb
        is_critical = is_critical_percent or is_critical_mb
        
        if is_critical:
            logger.warning(f"КРИТИЧЕСКОЕ состояние памяти! "
                          f"Использовано: {memory_percent:.1f}% (порог: {Config.RAM_THRESHOLD}%), "
                          f"Доступно: {available_mb:.1f}MB")
            
            # Отправляем уведомление в Telegram если включено
            if Config.NOTIFY_RAM_ENABLED and self.telegram_bot:
                try:
                    loop = asyncio.get_event_loop()
                    message = (
                        f"💾 Критическое использование RAM!\n\n"
                        f"📊 Использовано: {memory_percent:.1f}%\n"
                        f"⚠️ Порог: {Config.RAM_THRESHOLD}%\n"
                        f"🆓 Доступно: {available_mb:.1f}MB\n\n"
                        f"🔍 Проверьте процессы командой /resources"
                    )
                    loop.create_task(self._send_telegram_alert(message))
                except Exception as e:
                    logger.error(f"Ошибка отправки RAM уведомления: {e}")
        
        return is_critical
    
    def check_cpu_critical(self) -> Tuple[bool, float]:
        """Проверка критического использования CPU"""
        # Перезагружаем конфиг для актуальных настроек
        Config.reload_config()
        
        cpu_percent = psutil.cpu_percent(interval=1)
        is_critical = cpu_percent > Config.CPU_THRESHOLD
        
        if is_critical:
            logger.warning(f"КРИТИЧЕСКОЕ использование CPU! "
                          f"Текущее: {cpu_percent:.1f}%, "
                          f"Порог: {Config.CPU_THRESHOLD}%")
            
            # Отправляем уведомление в Telegram если включено
            if Config.NOTIFY_CPU_ENABLED and self.telegram_bot:
                try:
                    loop = asyncio.get_event_loop()
                    message = (
                        f"🔥 Критическое использование CPU!\n\n"
                        f"📊 Текущее: {cpu_percent:.1f}%\n"
                        f"⚠️ Порог: {Config.CPU_THRESHOLD}%\n\n"
                        f"🔍 Проверьте процессы командой /resources"
                    )
                    loop.create_task(self._send_telegram_alert(message))
                except Exception as e:
                    logger.error(f"Ошибка отправки CPU уведомления: {e}")
        
        return is_critical, cpu_percent
    
    async def _send_telegram_alert(self, message: str):
        """Отправка критического уведомления в Telegram"""
        if self.telegram_bot:
            try:
                alert_message = f"🚨 <b>КРИТИЧЕСКОЕ УВЕДОМЛЕНИЕ</b>\n\n{message}"
                await self.telegram_bot.send_notification(alert_message)
            except Exception as e:
                logger.error(f"Ошибка отправки Telegram уведомления: {e}")

    def emergency_memory_cleanup(self) -> bool:
        """Экстренная очистка памяти"""
        logger.critical("ЗАПУСК ЭКСТРЕННОЙ ОЧИСТКИ ПАМЯТИ!")
        
        # Отправляем уведомление о начале экстренной очистки
        if self.telegram_bot:
            try:
                loop = asyncio.get_event_loop()
                loop.create_task(self._send_telegram_alert(
                    "⚠️ Критически мало памяти!\n"
                    "🔧 Запуск экстренной очистки памяти..."
                ))
            except Exception as e:
                logger.error(f"Ошибка отправки уведомления: {e}")
        
        success = False
        killed_process = None
        
        # 1. Находим и убиваем самый жрущий процесс
        memory_hog = self.find_memory_hog_process()
        if memory_hog:
            if self.kill_process(memory_hog.pid, memory_hog.name):
                success = True
                killed_process = memory_hog
                logger.info(f"Убит процесс-пожиратель памяти: {memory_hog.name} (PID: {memory_hog.pid})")
                
                # Ждем немного после убийства процесса
                time.sleep(2)
        
        # 2. Очищаем кэш памяти
        cache_cleared = self.clear_memory_cache()
        if cache_cleared:
            success = True
            
        # 3. Проверяем результат
        time.sleep(1)
        memory_after = psutil.virtual_memory()
        available_after_mb = memory_after.available / 1024 / 1024
        
        logger.info(f"После экстренной очистки доступно памяти: {available_after_mb:.1f}MB")
        
        # Отправляем результат в Telegram
        if self.telegram_bot:
            try:
                loop = asyncio.get_event_loop()
                if available_after_mb >= self.min_free_ram_mb:
                    logger.info("Экстренная очистка памяти УСПЕШНА!")
                    result_message = (
                        "✅ Экстренная очистка памяти УСПЕШНА!\n\n"
                        f"💾 Доступно памяти: {available_after_mb:.1f}MB\n"
                    )
                    if killed_process:
                        result_message += f"🔪 Убит процесс: {killed_process.name} (PID: {killed_process.pid}, {killed_process.memory_mb:.1f}MB)\n"
                    if cache_cleared:
                        result_message += "🧹 Кэш памяти очищен\n"
                else:
                    logger.error("Экстренная очистка памяти НЕ ПОМОГЛА!")
                    result_message = (
                        "❌ Экстренная очистка памяти НЕ ПОМОГЛА!\n\n"
                        f"💾 Доступно памяти: {available_after_mb:.1f}MB\n"
                        f"⚠️ Требуется ручное вмешательство!"
                    )
                
                loop.create_task(self._send_telegram_alert(result_message))
            except Exception as e:
                logger.error(f"Ошибка отправки результата: {e}")
        
        return available_after_mb >= self.min_free_ram_mb
    
    def monitor_resources(self) -> Dict:
        """Основной цикл мониторинга ресурсов"""
        self._last_check_time = datetime.now()
        
        # Получаем статистику системы
        stats = self.get_system_stats()
        
        # Логируем текущее состояние
        logger.info(f"Мониторинг: CPU={stats.cpu_percent:.1f}%, "
                   f"RAM={stats.memory_used_mb:.0f}/{stats.memory_total_mb:.0f}MB ({stats.memory_percent:.1f}%)")
        
        actions_taken = []
        
        # Проверяем критическое состояние памяти
        if self.check_memory_critical():
            logger.warning("Обнаружено критическое состояние памяти!")
            if self.emergency_memory_cleanup():
                actions_taken.append("emergency_memory_cleanup")
            else:
                actions_taken.append("emergency_memory_cleanup_failed")
        
        # Проверяем критическое использование CPU
        cpu_critical, cpu_percent = self.check_cpu_critical()
        if cpu_critical:
            logger.warning("Обнаружено критическое использование CPU!")
            # Здесь можно добавить дополнительные действия при высоком CPU
            actions_taken.append("cpu_critical_detected")
        
        return {
            'timestamp': self._last_check_time,
            'stats': stats,
            'actions_taken': actions_taken,
            'memory_critical': self.check_memory_critical(),
            'cpu_critical': cpu_critical
        }
    
    def get_monitoring_report(self) -> str:
        """Получение отчета о мониторинге для Telegram"""
        stats = self.get_system_stats()
        
        report = f"📊 **Мониторинг системы**\n\n"
        report += f"🖥️ **CPU:** {stats.cpu_percent:.1f}%\n"
        report += f"💾 **Память:** {stats.memory_used_mb:.0f}/{stats.memory_total_mb:.0f}MB ({stats.memory_percent:.1f}%)\n"
        report += f"🆓 **Свободно:** {stats.memory_available_mb:.0f}MB\n\n"
        
        if stats.top_processes:
            report += "🔝 **Топ процессов по памяти:**\n"
            for i, proc in enumerate(stats.top_processes[:5], 1):
                report += f"{i}. {proc.name} - {proc.memory_mb:.1f}MB\n"
        
        # Статус критичности
        memory_critical = self.check_memory_critical()
        cpu_critical, _ = self.check_cpu_critical()
        
        if memory_critical or cpu_critical:
            report += "\n⚠️ **ВНИМАНИЕ:**\n"
            if memory_critical:
                report += "🔴 Критически мало свободной памяти!\n"
            if cpu_critical:
                report += "🔴 Критически высокое использование CPU!\n"
        else:
            report += "\n✅ Система работает в нормальном режиме"
        
        return report