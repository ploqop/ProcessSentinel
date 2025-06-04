import psutil
import requests
from datetime import datetime
import json
import os
import logging
import queue
import threading
import time
from config.config import Config

logger = logging.getLogger(__name__)

class SecurityPolicy:
    def __init__(self, server_url, client_uuid, auth_token=None):
        self.server_url = server_url
        self.client_uuid = client_uuid
        self.auth_token = auth_token
        self.blacklist = set()
        self.last_update = None
        self.config = Config()
        self.session = requests.Session()
        if auth_token:
            self.session.headers.update({'Authorization': f'Token {auth_token}'})
        
        # Очередь для отложенных отчетов
        self.report_queue = queue.Queue()
        self.report_thread = threading.Thread(target=self._process_report_queue, daemon=True)
        self.report_thread.start()
        
        logger.info(f"Initialized SecurityPolicy for client {client_uuid} with server {server_url}")

    def _update_session_token(self, token):
        """Обновление токена в сессии."""
        self.auth_token = token
        self.session.headers.update({'Authorization': f'Token {token}'})
        self.config.update_config(auth_token=token)

    def register_client(self):
        """Регистрация клиента на сервере."""
        try:
            config = self.config.load_config()
            manager_uuid = config.get('manager_uuid')
            client_name = config.get('client_name', 'Unknown')
            
            if not manager_uuid:
                logger.error("No manager UUID available")
                return False
            
            # Create a new session without authentication for registration
            session = requests.Session()
            response = session.post(
                f"{self.server_url}/api/clients/",
                json={
                    'manager_uuid': manager_uuid,
                    'name': client_name,
                    'uuid': self.client_uuid
                }
            )
            
            if response.status_code in [201, 200]:
                # Клиент успешно зарегистрирован или уже существует
                data = response.json()
                self.client_uuid = data.get('uuid')
                if self.client_uuid:
                    self.config.update_config(client_uuid=self.client_uuid)
                    # Update the main session with the new client UUID
                    self.session.headers.update({'X-Client-UUID': self.client_uuid})
                    
                    # Handle token if present in response
                    if 'token' in data:
                        self._update_session_token(data['token'])
                    
                return True
            else:
                logger.error(f"Failed to register client: {response.text}")
                return False
        except Exception as e:
            logger.error(f"Error registering client: {e}")
            return False

    def get_client_token(self):
        """Получение токена для существующего клиента."""
        try:
            # Создаем новую сессию без токена для запроса нового токена
            session = requests.Session()
            response = session.post(
                f"{self.server_url}/api/clients/token/",
                json={'uuid': self.client_uuid}
            )
            
            if response.status_code == 200:
                data = response.json()
                if 'token' in data:
                    self._update_session_token(data['token'])
                    return True
            elif response.status_code == 404:
                # Клиент не найден - нужно перерегистрироваться
                logger.info("Client not found, triggering re-registration")
                # Очищаем конфигурацию
                self.config.update_config(
                    client_uuid=None,
                    auth_token=None,
                    manager_uuid=None
                )
                # Возвращаем False, чтобы вызвать перерегистрацию
                return False
            logger.error(f"Failed to get client token: {response.text}")
            return False
        except Exception as e:
            logger.error(f"Error getting client token: {e}")
            return False

    def update_policy(self):
        """Обновление политики безопасности."""
        if not self.auth_token:
            logger.error("No auth token available")
            if not self.get_client_token():
                # Если не удалось получить токен, пробуем перерегистрироваться
                if not self.register_client():
                    return False
                # После успешной регистрации пробуем получить токен снова
                if not self.get_client_token():
                    return False

        try:
            # Ensure we have the token in the session headers
            self.session.headers.update({'Authorization': f'Token {self.auth_token}'})
            
            response = self.session.get(f"{self.server_url}/api/clients/{self.client_uuid}/policy/")
            if response.status_code == 200:
                data = response.json()
                # Преобразуем список политик в список имен процессов
                self.blacklist = set(data.get('blacklist', []))
                self.last_update = datetime.now()
                return True
            elif response.status_code in [401, 404]:
                # Если токен истек или клиент не найден
                if self.get_client_token():
                    # Повторяем запрос с новым токеном
                    self.session.headers.update({'Authorization': f'Token {self.auth_token}'})
                    response = self.session.get(f"{self.server_url}/api/clients/{self.client_uuid}/policy/")
                    if response.status_code == 200:
                        data = response.json()
                        self.blacklist = set(data.get('blacklist', []))
                        self.last_update = datetime.now()
                        return True
            logger.error(f"Failed to update policy: {response.status_code} - {response.text}")
            return False
        except Exception as e:
            logger.error(f"Error updating policy: {e}")
            return False

    def check_process(self, process_name):
        """Проверка процесса на соответствие политике."""
        return process_name in self.blacklist

    def terminate_process(self, pid):
        """Завершение процесса."""
        try:
            process = psutil.Process(pid)
            process.terminate()
            return True
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            return False

    def report_violation(self, process_name, pid):
        """Отправка отчета о нарушении."""
        if not self.auth_token:
            logger.error("No auth token available")
            return False

        try:
            response = self.session.post(
                f"{self.server_url}/api/report/",
                json={
                    'client_uuid': self.client_uuid,
                    'event_type': 'policy_violation',
                    'timestamp': datetime.now().isoformat(),
                    'process_name': process_name,
                    'process_id': pid
                }
            )
            if response.status_code == 401:
                # Если токен истек, пробуем получить новый
                if self.get_client_token():
                    # Повторяем запрос с новым токеном
                    response = self.session.post(
                        f"{self.server_url}/api/report/",
                        json={
                            'client_uuid': self.client_uuid,
                            'event_type': 'policy_violation',
                            'timestamp': datetime.now().isoformat(),
                            'process_name': process_name,
                            'process_id': pid
                        }
                    )
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Error reporting violation: {e}")
            return False

    def send_heartbeat(self):
        """Отправка heartbeat на сервер."""
        if not self.auth_token:
            logger.error("No auth token available")
            return False

        try:
            response = self.session.post(
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
                }
            )
            if response.status_code == 401:
                # Если токен истек, пробуем получить новый
                if self.get_client_token():
                    # Повторяем запрос с новым токеном
                    response = self.session.post(
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
                        }
                    )
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Error sending heartbeat: {e}")
            return False

    def _validate_policy_data(self, policy_data):
        """Валидация данных политики."""
        if not isinstance(policy_data, dict):
            raise ValueError("Policy data must be a dictionary")
        
        blacklist = policy_data.get('blacklist', [])
        if not isinstance(blacklist, list):
            raise ValueError("Blacklist must be a list")
        
        # Проверяем каждый элемент черного списка
        for process in blacklist:
            if not isinstance(process, str):
                raise ValueError("Process names must be strings")
            if not process.strip():
                raise ValueError("Process names cannot be empty")
        
        return True

    def _save_policy(self):
        """Сохранение политики в локальный файл."""
        try:
            os.makedirs('config', exist_ok=True)
            with open(self.policy_file, 'w') as f:
                json.dump({
                    'blacklist': list(self.blacklist),
                    'last_update': self.last_update.isoformat() if self.last_update else None
                }, f)
            logger.info(f"Saved policy to {self.policy_file}")
        except Exception as e:
            logger.error(f"Error saving policy: {e}")

    def _load_policy(self):
        """Загрузка политики из локального файла."""
        try:
            if os.path.exists(self.policy_file):
                with open(self.policy_file, 'r') as f:
                    data = json.load(f)
                    if self._validate_policy_data(data):
                        self.blacklist = set(data.get('blacklist', []))
                        last_update = data.get('last_update')
                        self.last_update = datetime.fromisoformat(last_update) if last_update else None
                        logger.info(f"Loaded policy from {self.policy_file}")
        except Exception as e:
            logger.error(f"Error loading policy: {e}")

    def _process_report_queue(self):
        """Обработка очереди отчетов."""
        while True:
            try:
                # Получаем отчет из очереди
                report = self.report_queue.get()
                # Пробуем отправить отчет
                success = self._send_report(report)
                if not success:
                    # Если не удалось отправить, возвращаем в очередь
                    self.report_queue.put(report)
                    time.sleep(5)  # Ждем перед следующей попыткой
            except Exception as e:
                logger.error(f"Error processing report queue: {e}")
                time.sleep(5)

    def _send_report(self, report):
        """Отправка отчета на сервер."""
        try:
            response = self.session.post(
                f"{self.server_url}/api/report/",
                json=report,
                timeout=5
            )
            if response.status_code != 200:
                logger.error(f"Failed to send report: {response.status_code} - {response.text}")
                return False
            logger.info("Successfully sent report")
            return True
        except requests.exceptions.RequestException as e:
            logger.error(f"Error sending report: {e}")
            return False 