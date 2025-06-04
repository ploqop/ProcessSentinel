import os
import json
import getpass
from pathlib import Path

class Config:
    def __init__(self):
        self.config_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config')
        self.config_file = os.path.join(self.config_dir, 'config.json')
        self.ensure_config_exists()

    def ensure_config_exists(self):
        """Создает конфигурационный файл, если он не существует."""
        if not os.path.exists(self.config_file):
            config = {
                'client_uuid': None,
                'server_url': 'http://localhost:8000',
                'client_name': getpass.getuser(),  # Имя пользователя Windows по умолчанию
                'auth_token': None,
                'manager_uuid': None  # Добавляем поле для UUID менеджера
            }
            os.makedirs(self.config_dir, exist_ok=True)
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=4)

    def load_config(self):
        """Загружает конфигурацию из файла."""
        try:
            with open(self.config_file, 'r') as f:
                config = json.load(f)
                # Ensure all required fields exist
                required_fields = ['client_uuid', 'server_url', 'client_name', 'auth_token', 'manager_uuid']
                for field in required_fields:
                    if field not in config:
                        config[field] = None
                return config
        except Exception as e:
            print(f"Error loading config: {e}")
            return None

    def save_config(self, config):
        """Сохраняет конфигурацию в файл."""
        try:
            # Ensure all required fields exist
            required_fields = ['client_uuid', 'server_url', 'client_name', 'auth_token', 'manager_uuid']
            for field in required_fields:
                if field not in config:
                    config[field] = None
            
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=4)
            return True
        except Exception as e:
            print(f"Error saving config: {e}")
            return False

    def update_config(self, **kwargs):
        """Обновляет конфигурацию."""
        config = self.load_config()
        if config:
            config.update(kwargs)
            return self.save_config(config)
        return False 