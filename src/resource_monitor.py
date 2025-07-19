"""
Модуль мониторинга системных ресурсов для SaldoranBotSentinel
"""

import psutil
import subprocess
import time
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime

from .config import Config
from .logger import logger


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
    
    def __init__(self):
        self.target_user = Config.TARGET_USER
        self.max_cpu_percent = Config.MAX_CPU_PERCENT
        self.min_free_ram_mb = Config.MIN_FREE_RAM_MB
        self.monitoring_interval = Config.MONITORING_INTERVAL
        self._last_check_time = None
        
    def get_system_stats(self) -> SystemStats:
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
        
        return SystemStats(
            cpu_percent=cpu_percent,
            memory_total_mb=memory_total_mb,
            memory_available_mb=memory_available_mb,
            memory_used_mb=memory_used_mb,
            memory_percent=memory_percent,
            top_processes=top_processes
        )
    
    def _get_top_memory_processes(self, limit: int = 10) -> List[ProcessInfo]:
        """Получение топ процессов по использованию памяти"""
        processes = []
        
        try:
            for proc in psutil.process_iter(['pid', 'name', 'username', 'memory_info', 'cmdline']):
                try:
                    # Фильтруем только процессы целевого пользователя
                    if proc.info['username'] != self.target_user:
                        continue
                        
                    memory_mb = proc.info['memory_info'].rss / 1024 / 1024
                    cmdline = ' '.join(proc.info['cmdline'] or [])
                    
                    # Получаем CPU процент для процесса
                    cpu_percent = proc.cpu_percent()
                    
                    process_info = ProcessInfo(
                        pid=proc.info['pid'],
                        name=proc.info['name'],
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
        memory = psutil.virtual_memory()
        available_mb = memory.available / 1024 / 1024
        
        is_critical = available_mb < self.min_free_ram_mb
        
        if is_critical:
            logger.warning(f"КРИТИЧЕСКОЕ состояние памяти! "
                          f"Доступно: {available_mb:.1f}MB, "
                          f"Минимум: {self.min_free_ram_mb}MB")
        
        return is_critical
    
    def check_cpu_critical(self) -> Tuple[bool, float]:
        """Проверка критического использования CPU"""
        cpu_percent = psutil.cpu_percent(interval=1)
        is_critical = cpu_percent > self.max_cpu_percent
        
        if is_critical:
            logger.warning(f"КРИТИЧЕСКОЕ использование CPU! "
                          f"Текущее: {cpu_percent:.1f}%, "
                          f"Максимум: {self.max_cpu_percent}%")
        
        return is_critical, cpu_percent
    
    def emergency_memory_cleanup(self) -> bool:
        """Экстренная очистка памяти"""
        logger.critical("ЗАПУСК ЭКСТРЕННОЙ ОЧИСТКИ ПАМЯТИ!")
        
        success = False
        
        # 1. Находим и убиваем самый жрущий процесс
        memory_hog = self.find_memory_hog_process()
        if memory_hog:
            if self.kill_process(memory_hog.pid, memory_hog.name):
                success = True
                logger.info(f"Убит процесс-пожиратель памяти: {memory_hog.name} (PID: {memory_hog.pid})")
                
                # Ждем немного после убийства процесса
                time.sleep(2)
        
        # 2. Очищаем кэш памяти
        if self.clear_memory_cache():
            success = True
            
        # 3. Проверяем результат
        time.sleep(1)
        memory_after = psutil.virtual_memory()
        available_after_mb = memory_after.available / 1024 / 1024
        
        logger.info(f"После экстренной очистки доступно памяти: {available_after_mb:.1f}MB")
        
        if available_after_mb >= self.min_free_ram_mb:
            logger.info("Экстренная очистка памяти УСПЕШНА!")
            return True
        else:
            logger.error("Экстренная очистка памяти НЕ ПОМОГЛА!")
            return False
    
    def monitor_resources(self) -> Dict:
        """Основной цикл мониторинга ресурсов"""
        self._last_check_time = datetime.now()
        
        # Получаем статистику системы
        stats = self.get_system_stats()
        
        # Логируем текущее состояние
        logger.info(f"Мониторинг: CPU={stats.cpu_percent:.1f}%, "
                   f"RAM={stats.memory_percent:.1f}% "
                   f"({stats.memory_available_mb:.1f}MB свободно)")
        
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
        report += f"💾 **Память:** {stats.memory_percent:.1f}% "
        report += f"({stats.memory_available_mb:.0f}MB свободно)\n"
        report += f"📈 **Всего памяти:** {stats.memory_total_mb:.0f}MB\n\n"
        
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