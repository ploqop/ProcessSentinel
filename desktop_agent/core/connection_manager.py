"""
Модуль для управления соединением с сервером и обработки ошибок
"""
import logging
import time
import threading
import requests
import json
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class ConnectionManager:
    """
    Класс для управления соединением с сервером и обработки ошибок
    """
    
    # Коды ошибок
    ERROR_NONE = 0                    # Нет ошибок
    ERROR_NETWORK = 1                 # Ошибка сети
    ERROR_AUTH = 2                    # Ошибка аутентификации
    ERROR_SERVER = 3                  # Ошибка сервера
    ERROR_CLIENT_NOT_FOUND = 4        # Клиент не найден
    ERROR_MANAGER_NOT_FOUND = 5       # Менеджер не найден
    ERROR_UNKNOWN = 6                 # Неизвестная ошибка
    
    def __init__(self, server_url, client_uuid=None, auth_token=None):
        """
        Инициализация менеджера соединений
        
        Args:
            server_url (str): URL сервера
            client_uuid (str, optional): UUID клиента
            auth_token (str, optional): Токен авторизации
        """
        self.server_url = server_url
        self.client_uuid = client_uuid
        self.auth_token = auth_token
        self.is_connected = False
        self.last_connection_check = None
        self.last_error = self.ERROR_NONE
        self.last_error_message = ""
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 5
        self.reconnect_interval = 10  # секунды
        self.backoff_factor = 1.5     # коэффициент увеличения интервала переподключения
        self.session = requests.Session()
        
        # Таймауты для запросов
        self.timeout = (5, 15)  # (connect timeout, read timeout)
        
        # Настраиваем заголовки сессии
        if auth_token:
            self.session.headers.update({'Authorization': f'Token {auth_token}'})
        
        # Колбэки для внешних обработчиков
        self.on_connection_status_change = None
        self.on_error = None
        self.on_client_unregistered = None
        
    def set_connection_status_callback(self, callback):
        """
        Устанавливает колбэк для изменения статуса соединения
        
        Args:
            callback (callable): Функция, принимающая bool параметр
        """
        self.on_connection_status_change = callback
        
    def set_error_callback(self, callback):
        """
        Устанавливает колбэк для обработки ошибок
        
        Args:
            callback (callable): Функция, принимающая код ошибки и сообщение
        """
        self.on_error = callback
        
    def set_client_unregistered_callback(self, callback):
        """
        Устанавливает колбэк для обработки ситуации, когда клиент не зарегистрирован
        
        Args:
            callback (callable): Функция без параметров
        """
        self.on_client_unregistered = callback
        
    def update_credentials(self, client_uuid=None, auth_token=None):
        """
        Обновляет учетные данные клиента
        
        Args:
            client_uuid (str, optional): Новый UUID клиента
            auth_token (str, optional): Новый токен авторизации
        """
        if client_uuid:
            self.client_uuid = client_uuid
        if auth_token:
            self.auth_token = auth_token
            self.session.headers.update({'Authorization': f'Token {auth_token}'})
            
    def refresh_token(self):
        """
        Обновляет токен авторизации
        
        Returns:
            bool: True если токен успешно обновлен, False в противном случае
        """
        if not self.client_uuid:
            logger.error("Cannot refresh token: Client UUID not set")
            return False
            
        try:
            # Удаляем старый токен из заголовков
            self.session.headers.pop('Authorization', None)
            
            # Запрашиваем новый токен
            response = self.session.post(
                f"{self.server_url}/api/clients/token/",
                json={'client_uuid': self.client_uuid},
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                data = response.json()
                if 'auth_token' in data:
                    self.auth_token = data['auth_token']
                    self.session.headers.update({'Authorization': f'Token {self.auth_token}'})
                    logger.info("Token refreshed successfully")
                    return True
                    
            logger.error(f"Failed to refresh token: {response.text}")
            return False
            
        except Exception as e:
            logger.error(f"Error refreshing token: {e}")
            return False
        
    def check_connection(self):
        """
        Проверяет соединение с сервером и статус клиента
        
        Returns:
            bool: True если соединение установлено, False в противном случае
        """
        if not self.client_uuid:
            self._handle_error(self.ERROR_CLIENT_NOT_FOUND, "Client UUID not set")
            return False
            
        try:
            # Проверяем доступность сервера и статус клиента
            response = self.session.get(
                f"{self.server_url}/api/clients/{self.client_uuid}/status/",
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                # Успешное соединение
                data = response.json()
                
                # Проверяем статус клиента
                if data.get('is_registered', False):
                    self._handle_connection_success()
                    return True
                else:
                    # Клиент не зарегистрирован (например, был удален менеджером)
                    self._handle_error(self.ERROR_CLIENT_NOT_FOUND, "Client not registered with manager")
                    if self.on_client_unregistered:
                        self.on_client_unregistered()
                    return False
                    
            elif response.status_code == 401:
                # Ошибка аутентификации
                self._handle_error(self.ERROR_AUTH, "Authentication failed")
                return False
                
            elif response.status_code == 404:
                # Клиент не найден
                self._handle_error(self.ERROR_CLIENT_NOT_FOUND, "Client not found on server")
                if self.on_client_unregistered:
                    self.on_client_unregistered()
                return False
                
            else:
                # Другая ошибка сервера
                self._handle_error(self.ERROR_SERVER, f"Server error: {response.status_code} - {response.text}")
                return False
                
        except requests.exceptions.RequestException as e:
            # Ошибка сети
            self._handle_error(self.ERROR_NETWORK, f"Network error: {str(e)}")
            return False
        except Exception as e:
            # Неизвестная ошибка
            self._handle_error(self.ERROR_UNKNOWN, f"Unknown error: {str(e)}")
            return False
            
    def reconnect(self):
        """
        Пытается переподключиться к серверу с экспоненциальной задержкой
        
        Returns:
            bool: True если переподключение успешно, False в противном случае
        """
        if self.reconnect_attempts >= self.max_reconnect_attempts:
            logger.warning("Maximum reconnection attempts reached")
            return False
            
        # Увеличиваем интервал переподключения с каждой попыткой
        delay = self.reconnect_interval * (self.backoff_factor ** self.reconnect_attempts)
        self.reconnect_attempts += 1
        
        logger.info(f"Reconnection attempt {self.reconnect_attempts}/{self.max_reconnect_attempts} after {delay:.1f}s")
        time.sleep(delay)
        
        # Пробуем переподключиться
        if self.check_connection():
            # Успешное переподключение
            self.reconnect_attempts = 0
            return True
        return False
        
    def _handle_connection_success(self):
        """Обрабатывает успешное подключение"""
        was_connected = self.is_connected
        self.is_connected = True
        self.last_connection_check = datetime.now()
        self.last_error = self.ERROR_NONE
        self.last_error_message = ""
        self.reconnect_attempts = 0
        
        # Уведомляем только при изменении статуса
        if not was_connected and self.on_connection_status_change:
            self.on_connection_status_change(True)
            
    def _handle_error(self, error_code, error_message):
        """
        Обрабатывает ошибку подключения
        
        Args:
            error_code (int): Код ошибки
            error_message (str): Сообщение об ошибке
        """
        was_connected = self.is_connected
        self.is_connected = False
        self.last_connection_check = datetime.now()
        self.last_error = error_code
        self.last_error_message = error_message
        
        logger.error(f"Connection error: [{error_code}] {error_message}")
        
        # Уведомляем при изменении статуса
        if was_connected and self.on_connection_status_change:
            self.on_connection_status_change(False)
            
        # Уведомляем о новой ошибке
        if self.on_error:
            self.on_error(error_code, error_message)
            
    def send_request(self, method, endpoint, data=None, params=None, retry=1):
        """
        Отправляет запрос на сервер с автоматической обработкой ошибок и повторными попытками
        
        Args:
            method (str): HTTP метод ('GET', 'POST', etc.)
            endpoint (str): Конечная точка API (без server_url)
            data (dict, optional): Данные для запроса
            params (dict, optional): Параметры запроса
            retry (int, optional): Количество повторных попыток при ошибке
            
        Returns:
            tuple: (success, data/error_message)
                - success (bool): True если запрос успешен, False в противном случае
                - data: Данные ответа при успехе, или сообщение об ошибке при неудаче
        """
        if not self.is_connected and not self.check_connection():
            return False, f"Not connected to server: {self.last_error_message}"
            
        url = f"{self.server_url}/{endpoint.lstrip('/')}"
        
        try:
            response = None
            if method.upper() == 'GET':
                response = self.session.get(url, params=params, timeout=self.timeout)
            elif method.upper() == 'POST':
                response = self.session.post(url, json=data, params=params, timeout=self.timeout)
            elif method.upper() == 'PUT':
                response = self.session.put(url, json=data, params=params, timeout=self.timeout)
            elif method.upper() == 'DELETE':
                response = self.session.delete(url, params=params, timeout=self.timeout)
            else:
                return False, f"Unsupported HTTP method: {method}"
                
            # Проверяем успешность запроса
            if response.status_code in (200, 201, 204):
                # Обновляем статус соединения
                self._handle_connection_success()
                
                # Если есть данные JSON, возвращаем их
                if response.text:
                    try:
                        return True, response.json()
                    except json.JSONDecodeError:
                        return True, response.text
                return True, None
                
            elif response.status_code == 401:
                # Ошибка аутентификации
                self._handle_error(self.ERROR_AUTH, "Authentication failed")
                return False, "Authentication failed"
                
            elif response.status_code == 404:
                if 'client' in url:
                    # Клиент не найден
                    self._handle_error(self.ERROR_CLIENT_NOT_FOUND, "Client not found")
                    if self.on_client_unregistered:
                        self.on_client_unregistered()
                return False, f"Resource not found: {response.text}"
                
            else:
                # Другая ошибка сервера
                error_msg = f"Server error: {response.status_code} - {response.text}"
                self._handle_error(self.ERROR_SERVER, error_msg)
                
                # Повторяем запрос при ошибке сервера, если осталось попыток
                if retry > 0 and response.status_code >= 500:
                    logger.info(f"Retrying request, {retry} attempts left")
                    time.sleep(1)  # Небольшая задержка перед повторной попыткой
                    return self.send_request(method, endpoint, data, params, retry-1)
                    
                return False, error_msg
                
        except requests.exceptions.RequestException as e:
            # Ошибка сети
            error_msg = f"Network error: {str(e)}"
            self._handle_error(self.ERROR_NETWORK, error_msg)
            
            # Повторяем запрос при ошибке сети, если осталось попыток
            if retry > 0:
                logger.info(f"Retrying request after network error, {retry} attempts left")
                time.sleep(1)
                return self.send_request(method, endpoint, data, params, retry-1)
                
            return False, error_msg
            
        except Exception as e:
            # Неизвестная ошибка
            error_msg = f"Unknown error: {str(e)}"
            self._handle_error(self.ERROR_UNKNOWN, error_msg)
            return False, error_msg