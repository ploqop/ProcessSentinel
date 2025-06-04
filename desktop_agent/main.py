import sys
import os
import logging
from dotenv import load_dotenv
from gui.main_window import MainWindow
from gui.first_run import FirstRunWindow
from config.config import Config

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def on_registration_success(manager_uuid, client_uuid, token):
    """Обработчик успешной регистрации клиента."""
    # Сохраняем полученные данные в конфигурацию
    config = Config()
    config.update_config(
        client_uuid=client_uuid,
        auth_token=token,
        manager_uuid=manager_uuid
    )
    logger.info(f"Saved new client registration: UUID={client_uuid}")
    # Получаем URL сервера из конфигурации или переменных окружения
    config_data = config.load_config()
    server_url = config_data.get('server_url') or os.getenv('SERVER_URL', 'http://localhost:8000')
    
    # Запускаем главное окно
    window = MainWindow(server_url, client_uuid, token)
    window.run()

def main():
    # Загружаем переменные окружения
    load_dotenv()

    # Загружаем конфигурацию
    config = Config()
    config_data = config.load_config()

    if not config_data:
        print("Error: Could not load configuration")
        return

    # Получаем URL сервера из конфигурации или переменных окружения
    server_url = config_data.get('server_url') or os.getenv('SERVER_URL', 'http://localhost:8000')

    # Получаем UUID клиента из конфигурации
    client_uuid = config_data.get('client_uuid')
    auth_token = config_data.get('auth_token')

    if not client_uuid or not auth_token:
        logger.info("Client UUID or auth token not found. Starting first run setup...")
        # Очищаем конфигурацию перед первичной настройкой
        config.update_config(
            client_uuid=None,
            auth_token=None,
            manager_uuid=None
        )
        # Запускаем окно первичной настройки
        first_run = FirstRunWindow(server_url, on_registration_success)
        first_run.run()
    else:
        try:
            # Создаем и запускаем главное окно
            window = MainWindow(server_url, client_uuid, auth_token)
            window.run()
        except Exception as e:
            logger.error(f"Error running main window: {e}")
            # В случае ошибки запускаем первичную настройку
            first_run = FirstRunWindow(server_url, on_registration_success)
            first_run.run()

if __name__ == '__main__':
    main()
