"""
Модуль для управления клиентским агентом
"""
import logging
import os
import uuid
import time
import threading
from datetime import datetime

from .connection_manager import ConnectionManager
from ..config.config import Config

logger = logging.getLogger(__name__)

class ClientManager:
    """
    Класс для управления жизненным циклом клиентского агента
    """
    
    def __init__(self, server_url):
        """
        Инициализация менеджера клиента
        
        Args:
            server_url (str): URL сервера
        """
        self.server_url = server_url
        self.config = Config()
        self.client_uuid = None
        self.auth_token = None
        self.manager_uuid = None
        self.connection = None
        self.is_registered = False
        self.registration_lock = threading.Lock()
        
        # Колбэки для обработки событий
        self.on_registration_required = None
        self.on_connection_status_change = None
        self.on_error = None
        
        # Загружаем конфигурацию
        self._load_config()
        
        # Инициализируем соединение
        self._init_connection()
        
    def set_registration_required_callback(self, callback):
        """
        Устанавливает колбэк для обработки необходимости регистрации
        
        Args:
            callback (callable): Функция без параметров
        """
        self.on_registration_required = callback
        
    def set_connection_status_callback(self, callback):
        """
        Устанавливает колбэк для обработки изменения статуса соединения
        
        Args:
            callback (callable): Функция, принимающая bool параметр
        """
        self.on_connection_status_change = callback
        if self.connection:
            self.connection.set_connection_status_callback(callback)
        
    def set_error_callback(self, callback):
        """
        Устанавливает колбэк для обработки ошибок
        
        Args:
            callback (callable): Функция, принимающая код ошибки и сообщение
        """
        self.on_error = callback
        if self.connection:
            self.connection.set_error_callback(callback)
        
    def _load_config(self):
        """Загружает конфигурацию клиента"""
        config_data = self.config.load_config()
        if config_data:
            self.client_uuid = config_data.get('client_uuid')
            self.auth_token = config_data.get('auth_token')
            self.manager_uuid = config_data.get('manager_uuid')
            logger.info(f"Loaded config: client_uuid={self.client_uuid}, manager_uuid={self.manager_uuid}")
        else:
            logger.warning("Failed to load config or config is empty")
            
    def _init_connection(self):
        """Инициализирует соединение с сервером"""
        self.connection = ConnectionManager(
            self.server_url, 
            self.client_uuid, 
            self.auth_token
        )
        
        # Устанавливаем колбэки
        if self.on_connection_status_change:
            self.connection.set_connection_status_callback(self.on_connection_status_change)
            
        if self.on_error:
            self.connection.set_error_callback(self.on_error)
            
        # Устанавливаем колбэк для обработки ситуации, когда клиент не зарегистрирован
        self.connection.set_client_unregistered_callback(self._handle_client_unregistered)
        
    def check_registration(self):
        """
        Проверяет регистрацию клиента на сервере
        
        Returns:
            bool: True если клиент зарегистрирован, False в противном случае
        """
        # Если нет UUID клиента, значит он не зарегистрирован
        if not self.client_uuid or not self.manager_uuid:
            logger.warning("Client not registered: Missing UUID or manager UUID")
            self._handle_client_unregistered()
            return False
            
        # Проверяем соединение с сервером
        if not self.connection.check_connection():
            # Если ошибка связана с тем, что клиент не найден, нужна повторная регистрация
            if self.connection.last_error == ConnectionManager.ERROR_CLIENT_NOT_FOUND:
                logger.warning("Client not found on server, registration required")
                self._handle_client_unregistered()
                return False
                
            # Если это просто ошибка соединения, пробуем переподключиться
            logger.warning(f"Connection error: {self.connection.last_error_message}")
            return False
            
        # Если соединение установлено, клиент зарегистрирован
        logger.info("Client registration verified")
        self.is_registered = True
        return True
        
    def register_client(self, manager_uuid=None, client_name=None):
        """
        Регистрирует клиента на сервере
        
        Args:
            manager_uuid (str, optional): UUID менеджера для регистрации
            client_name (str, optional): Имя клиента
            
        Returns:
            bool: True если регистрация успешна, False в противном случае
        """
        with self.registration_lock:
            # Используем переданный UUID менеджера или из конфигурации
            manager_uuid = manager_uuid or self.manager_uuid
            if not manager_uuid:
                logger.error("Cannot register client: Missing manager UUID")
                return False
                
            # Если имя клиента не указано, используем имя компьютера
            if not client_name:
                client_name = os.environ.get('COMPUTERNAME', 'Unknown')
                
            logger.info(f"Registering client with manager {manager_uuid}, name: {client_name}")
            
            try:
                # Отправляем запрос на регистрацию
                success, data = self.connection.send_request(
                    'POST',
                    '/api/clients/',
                    {
                        'manager_uuid': manager_uuid,
                        'name': client_name
                    }
                )
                
                if success:
                    # Сохраняем полученные данные
                    self.client_uuid = data.get('client_uuid')
                    token = data.get('token')
                    if token:
                        self.auth_token = token
                        
                    # Обновляем конфигурацию
                    self.config.update_config(
                        client_uuid=self.client_uuid,
                        auth_token=self.auth_token,
                        manager_uuid=manager_uuid
                    )
                    
                    # Обновляем учетные данные в соединении
                    self.connection.update_credentials(self.client_uuid, self.auth_token)
                    
                    logger.info(f"Client registered successfully: {self.client_uuid}")
                    self.is_registered = True
                    return True
                else:
                    logger.error(f"Failed to register client: {data}")
                    return False
                    
            except Exception as e:
                logger.error(f"Error during client registration: {str(e)}")
                return False
                
    def _handle_client_unregistered(self):
        """Обрабатывает ситуацию, когда клиент не зарегистрирован"""
        logger.warning("Client not registered with manager, opening registration window")
        self.is_registered = False
        
        # Вызываем колбэк для открытия окна регистрации
        if self.on_registration_required:
            self.on_registration_required()
            
    def update_policy(self):
        """
        Обновляет политику безопасности с сервера
        
        Returns:
            tuple: (success, policy_data/error_message)
        """
        if not self.is_registered and not self.check_registration():
            return False, "Client not registered"
            
        if not self.auth_token:
            return False, "No auth token available"
            
        success, data = self.connection.send_request(
            'GET',
            f'/api/policy/',
            params={'client_uuid': self.client_uuid}
        )
        
        if not success and self.connection.last_error == ConnectionManager.ERROR_UNAUTHORIZED:
            # Если токен истек, пробуем получить новый
            if self.connection.refresh_token():
                # Повторяем запрос с новым токеном
                success, data = self.connection.send_request(
                    'GET',
                    f'/api/policy/',
                    params={'client_uuid': self.client_uuid}
                )
                
        return success, data
        
    def send_heartbeat(self, processes=None, system_stats=None):
        """
        Отправляет сигнал активности на сервер
        
        Args:
            processes (list, optional): Список запущенных процессов
            system_stats (dict, optional): Статистика системы
            
        Returns:
            bool: True если сигнал отправлен успешно, False в противном случае
        """
        if not self.is_registered and not self.check_registration():
            return False
            
        if not self.auth_token:
            return False
            
        if processes is None:
            processes = []
        if system_stats is None:
            system_stats = {}
            
        success, _ = self.connection.send_request(
            'POST',
            '/api/client/heartbeat/',
            {
                'client_uuid': self.client_uuid,
                'processes': processes,
                'system_stats': system_stats,
                'timestamp': datetime.now().isoformat()
            }
        )
        
        if not success and self.connection.last_error == ConnectionManager.ERROR_UNAUTHORIZED:
            # Если токен истек, пробуем получить новый
            if self.connection.refresh_token():
                # Повторяем запрос с новым токеном
                success, _ = self.connection.send_request(
                    'POST',
                    '/api/client/heartbeat/',
                    {
                        'client_uuid': self.client_uuid,
                        'processes': processes,
                        'system_stats': system_stats,
                        'timestamp': datetime.now().isoformat()
                    }
                )
        
        return success
        
    def report_violation(self, process_name, process_id):
        """
        Отправляет отчет о нарушении политики
        
        Args:
            process_name (str): Имя процесса
            process_id (int): ID процесса
            
        Returns:
            bool: True если отчет отправлен успешно, False в противном случае
        """
        if not self.is_registered and not self.check_registration():
            return False
            
        if not self.auth_token:
            return False
            
        success, _ = self.connection.send_request(
            'POST',
            '/api/client/violation/',
            {
                'client_uuid': self.client_uuid,
                'process_name': process_name,
                'process_id': process_id,
                'timestamp': datetime.now().isoformat()
            }
        )
        
        if not success and self.connection.last_error == ConnectionManager.ERROR_UNAUTHORIZED:
            # Если токен истек, пробуем получить новый
            if self.connection.refresh_token():
                # Повторяем запрос с новым токеном
                success, _ = self.connection.send_request(
                    'POST',
                    '/api/client/violation/',
                    {
                        'client_uuid': self.client_uuid,
                        'process_name': process_name,
                        'process_id': process_id,
                        'timestamp': datetime.now().isoformat()
                    }
                )
        
        return success