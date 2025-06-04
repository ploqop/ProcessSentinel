"""
Главный модуль клиентского агента с обработкой ошибок и переоткрытием окна регистрации
"""
import sys
import os
import logging
import threading
import time
from dotenv import load_dotenv

from gui.main_window import MainWindow
from gui.first_run import FirstRunWindow
from config.config import Config
from core.client_manager import ClientManager

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("process_sentinel.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

class Application:
    """
    Главный класс приложения, управляющий жизненным циклом и окнами
    """
    
    def __init__(self):
        """Инициализация приложения"""
        # Загружаем переменные окружения
        load_dotenv()
        
        # Загружаем конфигурацию
        self.config = Config()
        config_data = self.config.load_config()
        
        # Получаем URL сервера из конфигурации или переменных окружения
        self.server_url = config_data.get('server_url') if config_data else None
        if not self.server_url:
            self.server_url = os.getenv('SERVER_URL', 'http://localhost:8000')
            
        # Флаги состояния
        self.is_first_run_window_open = False
        self.is_main_window_open = False
        self.exit_requested = False
        
        # Создаем менеджер клиента
        self.client_manager = ClientManager(self.server_url)
        
        # Устанавливаем колбэки для обработки событий
        self.client_manager.set_registration_required_callback(self.show_first_run_window)
        
        # Переменные для окон
        self.main_window = None
        self.first_run_window = None
        
    def start(self):
        """Запускает приложение"""
        logger.info("Starting application")
        
        # Проверяем регистрацию клиента
        if self.client_manager.check_registration():
            # Если клиент зарегистрирован, показываем главное окно
            self.show_main_window()
        else:
            # Иначе показываем окно первичной настройки
            self.show_first_run_window()
            
        # Основной цикл приложения
        while not self.exit_requested:
            time.sleep(0.1)
            
    def show_main_window(self):
        """Показывает главное окно приложения"""
        if self.is_main_window_open:
            logger.info("Main window already open")
            return
            
        if self.is_first_run_window_open:
            logger.info("Closing first run window before opening main window")
            # TODO: Закрыть окно первичной настройки
            self.is_first_run_window_open = False
            
        logger.info("Opening main window")
        self.is_main_window_open = True
        
        # Создаем и запускаем главное окно в отдельном потоке
        def run_main_window():
            self.main_window = MainWindow(
                self.server_url, 
                self.client_manager.client_uuid, 
                self.client_manager.auth_token
            )
            # Устанавливаем колбэк для обработки ситуации, когда клиент не зарегистрирован
            self.main_window.set_registration_required_callback(self.show_first_run_window)
            self.main_window.run()
            self.is_main_window_open = False
            logger.info("Main window closed")
            
            # Если закрытие окна не связано с запросом на выход, проверяем регистрацию
            if not self.exit_requested:
                if not self.client_manager.is_registered:
                    self.show_first_run_window()
                
        threading.Thread(target=run_main_window, daemon=True).start()
        
    def show_first_run_window(self):
        """Показывает окно первичной настройки"""
        if self.is_first_run_window_open:
            logger.info("First run window already open")
            return
            
        if self.is_main_window_open:
            logger.info("Closing main window before opening first run window")
            # Если главное окно открыто, закрываем его
            if self.main_window:
                self.main_window.quit_application()
            self.is_main_window_open = False
            
        logger.info("Opening first run window")
        self.is_first_run_window_open = True
        
        # Создаем и запускаем окно первичной настройки в отдельном потоке
        def run_first_run_window():
            self.first_run_window = FirstRunWindow(
                self.server_url, 
                self.on_first_run_success
            )
            self.first_run_window.run()
            self.is_first_run_window_open = False
            logger.info("First run window closed")
            
            # Если закрытие окна не связано с успешной регистрацией, выходим
            if not self.client_manager.is_registered and not self.exit_requested:
                logger.info("Exiting application after first run window closed without registration")
                self.exit()
                
        threading.Thread(target=run_first_run_window, daemon=True).start()
        
    def on_first_run_success(self, manager_uuid, client_uuid, token):
        """
        Обрабатывает успешную первичную настройку
        
        Args:
            manager_uuid (str): UUID менеджера
            client_uuid (str): UUID клиента
            token (str): Токен авторизации
        """
        logger.info(f"First run successful: client_uuid={client_uuid}")
        
        # Обновляем данные в менеджере клиента
        self.client_manager.manager_uuid = manager_uuid
        self.client_manager.client_uuid = client_uuid
        self.client_manager.auth_token = token
        self.client_manager.is_registered = True
        
        # Обновляем учетные данные в соединении
        self.client_manager.connection.update_credentials(client_uuid, token)
        
        # Показываем главное окно
        self.show_main_window()
        
    def exit(self):
        """Завершает работу приложения"""
        logger.info("Exiting application")
        self.exit_requested = True
        
        # Закрываем все окна
        if self.main_window:
            self.main_window.quit_application()
        
        # TODO: Закрыть окно первичной настройки
        
        # Завершаем работу
        sys.exit(0)
        
def main():
    """Точка входа в приложение"""
    try:
        app = Application()
        app.start()
    except Exception as e:
        logger.exception(f"Unhandled exception in main: {str(e)}")
        sys.exit(1)
        
if __name__ == '__main__':
    main()