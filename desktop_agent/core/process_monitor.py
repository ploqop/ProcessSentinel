import psutil
from datetime import datetime
import time
import logging
import requests
from .security_policy import SecurityPolicy
import sys
import os
from PIL import Image

logger = logging.getLogger(__name__)

def resource_path(relative_path):
    """ Получить абсолютный путь к ресурсу, работает для dev и для PyInstaller """
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

icon_path = resource_path('gui/icon.png')

if not os.path.exists(icon_path):
    logger.warning(f"Icon not found at {icon_path}. Using default icon.")
    icon_path = None  # Or handle accordingly in your GUI code

class ProcessMonitor:
    def __init__(self, server_url, client_uuid, auth_token=None, status_callback=None, log_callback=None, policy_update_callback=None):
        self.server_url = server_url
        self.client_uuid = client_uuid
        self.auth_token = auth_token
        self.status_callback = status_callback
        self.log_callback = log_callback
        self.policy_update_callback = policy_update_callback
        self.security_policy = SecurityPolicy(server_url, client_uuid, auth_token)
        self.running = False
        self.check_interval = 5  # интервал проверки в секундах
        self.heartbeat_interval = 30  # интервал отправки heartbeat в секундах
        self.last_heartbeat = None
        self.reconnect_interval = 10  # интервал переподключения в секундах
        self.last_connection_check = None
        self.connection_check_interval = 30  # интервал проверки соединения в секундах
        self.is_connected = False
        self.last_policy_update = None
        self.policy_update_interval = 10  # интервал обновления политики в секундах (5 минут)

    def check_connection(self):
        """Проверка соединения с сервером."""
        try:
            # Используем эндпоинт отчета для проверки соединения
            response = self.security_policy.session.post(
                f"{self.server_url}/api/report/",
                json={
                    'client_uuid': self.client_uuid,
                    'event_type': 'heartbeat',
                    'timestamp': datetime.now().isoformat(),
                    'processes': [],
                    'system_stats': {
                        'cpu_percent': 0,
                        'memory_percent': 0,
                        'process_count': 0
                    }
                },
                timeout=5
            )
            new_status = response.status_code == 200
            if new_status != self.is_connected:
                self.is_connected = new_status
                if self.status_callback:
                    self.status_callback(self.is_connected)
            return self.is_connected
        except requests.exceptions.RequestException:
            if self.is_connected:
                self.is_connected = False
                if self.status_callback:
                    self.status_callback(False)
            return False

    def start_monitoring(self):
        """Запуск мониторинга процессов."""
        self.running = True
        self.security_policy.update_policy()  # получаем начальную политику
        
        while self.running:
            try:
                current_time = datetime.now()
                
                # Проверяем соединение
                if not self.last_connection_check or \
                   (current_time - self.last_connection_check).total_seconds() > self.connection_check_interval:
                    self.check_connection()
                    self.last_connection_check = current_time

                # Проверяем все процессы
                for proc in psutil.process_iter(['pid', 'name']):
                    try:
                        pinfo = proc.info
                        process_name = pinfo['name']
                        
                        # Проверяем процесс на соответствие политике
                        if self.security_policy.check_process(process_name):
                            # Завершаем запрещенный процесс
                            if self.security_policy.terminate_process(pinfo['pid']):
                                # Отправляем отчет о нарушении
                                self.security_policy.report_violation(process_name, pinfo['pid'])
                                # Добавляем запись в лог
                                if self.log_callback:
                                    self.log_callback(f"Blocked process: {process_name} (PID: {pinfo['pid']})")
                    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                        continue
                
                # Обновляем политику каждые 5 минут
                if not self.last_policy_update or \
                   (current_time - self.last_policy_update).total_seconds() > self.policy_update_interval:
                    previous_blacklist = set(self.security_policy.blacklist)
                    if self.security_policy.update_policy():
                        self.last_policy_update = current_time
                        # Обновляем UI через callback
                        if self.policy_update_callback:
                            self.policy_update_callback()
                        # Если политика успешно обновилась, добавляем запись в лог
                        current_blacklist = set(self.security_policy.blacklist)
                        if current_blacklist != previous_blacklist:
                            if self.log_callback:
                                added = current_blacklist - previous_blacklist
                                removed = previous_blacklist - current_blacklist
                                if added:
                                    self.log_callback(f"Policy updated: Added to blacklist: {', '.join(added)}")
                                if removed:
                                    self.log_callback(f"Policy updated: Removed from blacklist: {', '.join(removed)}")
                
                # Отправляем heartbeat каждые 30 секунд
                if not self.last_heartbeat or \
                   (current_time - self.last_heartbeat).total_seconds() > self.heartbeat_interval:
                    if self.is_connected and self.security_policy.send_heartbeat():
                        self.last_heartbeat = current_time
                        if self.log_callback:
                            self.log_callback("Heartbeat sent successfully")
                
                time.sleep(self.check_interval)
            except Exception as e:
                logger.error(f"Error in process monitoring: {e}")
                if self.is_connected:
                    self.is_connected = False
                    if self.status_callback:
                        self.status_callback(False)
                    if self.log_callback:
                        self.log_callback(f"Connection lost: {str(e)}")
                time.sleep(self.reconnect_interval)  # Увеличиваем интервал при ошибке

    def stop_monitoring(self):
        """Остановка мониторинга процессов."""
        self.running = False
        if self.is_connected:
            self.is_connected = False
            if self.status_callback:
                self.status_callback(False)
            if self.log_callback:
                self.log_callback("Monitoring stopped")

    def get_processes(self):
        """Получение списка процессов с их характеристиками."""
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'status', 'cpu_percent', 'memory_percent', 'create_time']):
            try:
                pinfo = proc.info
                # Преобразуем время создания в читаемый формат
                create_time = datetime.fromtimestamp(pinfo['create_time']).strftime('%Y-%m-%d %H:%M:%S') if pinfo['create_time'] else 'N/A'
                
                processes.append({
                    'pid': pinfo['pid'],
                    'name': pinfo['name'],
                    'status': pinfo['status'],
                    'cpu_percent': f"{pinfo['cpu_percent']:.1f}%",
                    'memory_percent': f"{pinfo['memory_percent']:.1f}%",
                    'start_time': create_time
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
        
        # Сортируем процессы по использованию CPU
        processes.sort(key=lambda x: float(x['cpu_percent'].rstrip('%')), reverse=True)
        return processes

    def get_process_count(self):
        """Получение количества запущенных процессов."""
        return len(psutil.pids())

    def get_system_stats(self):
        """Получение системной статистики."""
        return {
            'cpu_percent': psutil.cpu_percent(interval=1),
            'memory_percent': psutil.virtual_memory().percent,
            'process_count': self.get_process_count()
        } 