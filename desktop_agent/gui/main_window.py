import dearpygui.dearpygui as dpg
import threading
import time
import logging
import os
from PIL import Image
import pystray
from core.process_monitor import ProcessMonitor
from core.security_policy import SecurityPolicy
from .first_run import FirstRunWindow
from config.config import Config

logger = logging.getLogger(__name__)

class MainWindow:
    def __init__(self, server_url: str, client_uuid: str, auth_token: str = None):
        self.server_url = server_url
        self.client_uuid = client_uuid
        self.auth_token = auth_token
        self.monitor = None
        self.is_connected = False
        self.setup_window()
        self.setup_tray()

    def setup_window(self):
        dpg.create_context()
        dpg.create_viewport(title="Process Sentinel", width=800, height=600)
        
        # Create main window
        with dpg.window(label="Process Sentinel", tag="Primary Window", width=780, height=580, no_resize=True):
            # Connection status
            with dpg.group(horizontal=True):
                dpg.add_text("Status:")
                dpg.add_text("Offline", tag="status_text", color=(255, 0, 0))
                dpg.add_spacer(width=10)
                dpg.add_loading_indicator(tag="status_loading", show=False)
            
            # Client information
            with dpg.group(horizontal=True):
                dpg.add_text("Client UUID:")
                dpg.add_text(self.client_uuid)
            
            # Last policy update
            with dpg.group(horizontal=True):
                dpg.add_text("Last Policy Update:")
                dpg.add_text("Never", tag="last_update_text")
            
            # Blacklisted processes
            dpg.add_text("Blacklisted Processes:")
            with dpg.child_window(tag="blacklist_window", height=200, border=True):
                dpg.add_text("No blacklisted processes", tag="blacklist_text")
            
            # Control buttons
            with dpg.group(horizontal=True):
                dpg.add_button(label="Update Policy", callback=self.update_policy)
                dpg.add_loading_indicator(tag="button_loading", show=False)
            
            # Event log
            dpg.add_text("Event Log:")
            with dpg.child_window(tag="log_window", height=200, border=True):
                dpg.add_text("", tag="log_text", wrap=700)

        # Add window close handler
        dpg.set_exit_callback(self.on_exit)

    def setup_tray(self):
        """Настройка иконки в системном трее."""
        # Создаем временное изображение для иконки
        icon_path = os.path.join(os.path.dirname(__file__), "icon.png")
        if not os.path.exists(icon_path):
            # Создаем простое изображение, если файл не существует
            img = Image.new('RGB', (64, 64), color='red')
            img.save(icon_path)

        # Создаем меню для иконки в трее
        menu = (
            pystray.MenuItem('Show', self.show_window),
            pystray.MenuItem('Exit', self.quit_application)
        )

        # Создаем иконку в трее
        self.icon = pystray.Icon("Process Sentinel", Image.open(icon_path), "Process Sentinel", menu)
        
        # Запускаем иконку в отдельном потоке
        threading.Thread(target=self.icon.run, daemon=True).start()

    def show_window(self):
        """Показать главное окно."""
        dpg.show_viewport()
        dpg.set_primary_window("Primary Window", True)

    def on_exit(self):
        """Обработчик закрытия окна."""
        # dpg.hide_viewport()
        return False  # Предотвращаем закрытие приложения

    def quit_application(self):
        """Полное закрытие приложения."""
        if self.monitor:
            self.monitor.stop_monitoring()
        if self.icon:
            self.icon.stop()
        dpg.stop_dearpygui()
        dpg.destroy_context()

    def update_connection_status(self, is_connected: bool):
        """Обновление статуса подключения."""
        self.is_connected = is_connected
        if is_connected:
            dpg.set_value("status_text", "Online")
            dpg.configure_item("status_text", color=(0, 255, 0))
            self.add_log_entry("Connected to server")
            # При подключении обновляем политику
            self.update_policy()
        else:
            dpg.set_value("status_text", "Offline")
            dpg.configure_item("status_text", color=(255, 0, 0))
            self.add_log_entry("Disconnected from server")

    def show_loading(self, show: bool):
        """Показать/скрыть индикатор загрузки."""
        dpg.configure_item("status_loading", show=show)
        dpg.configure_item("button_loading", show=show)

    def update_policy(self):
        try:
            self.show_loading(True)
            if self.monitor:
                if self.monitor.security_policy.update_policy():
                    # Обновляем время последнего обновления
                    last_update = self.monitor.security_policy.last_update
                    if last_update:
                        dpg.set_value("last_update_text", last_update.strftime("%Y-%m-%d %H:%M:%S"))
                    # Обновляем отображение черного списка
                    self.update_blacklist()
                    self.add_log_entry("Policy updated successfully")
                else:
                    self.add_log_entry("Failed to update policy")
        except Exception as e:
            logger.error(f"Failed to update policy: {e}")
            self.add_log_entry(f"Error updating policy: {str(e)}")
        finally:
            self.show_loading(False)

    def update_blacklist(self):
        """Обновление отображения черного списка."""
        if self.monitor and self.monitor.security_policy.blacklist:
            blacklist_text = "\n".join(f"- {process}" for process in sorted(self.monitor.security_policy.blacklist))
            dpg.set_value("blacklist_text", blacklist_text)
        else:
            dpg.set_value("blacklist_text", "No blacklisted processes")

    def add_log_entry(self, message: str):
        """Добавление записи в лог."""
        current_log = dpg.get_value("log_text")
        timestamp = time.strftime("%H:%M:%S")
        new_entry = f"[{timestamp}] {message}"
        if current_log:
            dpg.set_value("log_text", f"{new_entry}\n{current_log}")
        else:
            dpg.set_value("log_text", new_entry)

    def start_monitoring(self):
        try:
            self.monitor = ProcessMonitor(
                server_url=self.server_url,
                client_uuid=self.client_uuid,
                auth_token=self.auth_token,
                status_callback=self.update_connection_status,
                log_callback=self.add_log_entry,
                policy_update_callback=self.update_policy_ui
            )
            # Загружаем начальную политику
            if self.monitor.security_policy.update_policy():
                self.update_blacklist()
                last_update = self.monitor.security_policy.last_update
                if last_update:
                    dpg.set_value("last_update_text", last_update.strftime("%Y-%m-%d %H:%M:%S"))
            self.monitor.start_monitoring()
            self.add_log_entry("Process monitoring started")
        except Exception as e:
            logger.error(f"Failed to start monitoring: {e}")
            self.update_connection_status(False)
            self.add_log_entry(f"Error starting monitoring: {str(e)}")

    def update_policy_ui(self):
        """Обновление UI при изменении политики."""
        try:
            if self.monitor:
                # Обновляем время последнего обновления
                last_update = self.monitor.security_policy.last_update
                if last_update:
                    dpg.set_value("last_update_text", last_update.strftime("%Y-%m-%d %H:%M:%S"))
                # Обновляем отображение черного списка
                self.update_blacklist()
        except Exception as e:
            logger.error(f"Failed to update policy UI: {e}")
            self.add_log_entry(f"Error updating policy UI: {str(e)}")

    def check_initial_connection(self):
        """Проверка начального подключения к серверу."""
        try:
            # Создаем временный SecurityPolicy для проверки
            policy = SecurityPolicy(self.server_url, self.client_uuid, self.auth_token)
            # Пробуем получить политику
            if not policy.update_policy():
                # Если не удалось получить политику, пробуем перерегистрировать клиента
                if not policy.register_client():
                    # Если регистрация не удалась, значит клиент был удален
                    logger.info("Client was deleted, triggering re-registration")
                    # Очищаем конфигурацию
                    config = Config()
                    config.update_config(
                        client_uuid=None,
                        auth_token=None,
                        manager_uuid=None
                    )
                    # Закрываем текущее окно
                    self.quit_application()
                    # Запускаем окно первичной настройки
                    first_run = FirstRunWindow(self.server_url, self.on_registration_success)
                    first_run.run()
                    return False
            return True
        except Exception as e:
            logger.error(f"Error checking initial connection: {e}")
            # В случае ошибки также запускаем первичную настройку
            config = Config()
            config.update_config(
                client_uuid=None,
                auth_token=None,
                manager_uuid=None
            )
            self.quit_application()
            first_run = FirstRunWindow(self.server_url, self.on_registration_success)
            first_run.run()
            return False

    def run(self):
        """Запуск главного окна."""
        try:
            # Проверяем начальное подключение
            if not self.check_initial_connection():
                return

            # Setup and show viewport
            dpg.setup_dearpygui()
            dpg.show_viewport()
            dpg.set_primary_window("Primary Window", True)

            # Start monitoring in a separate thread
            threading.Thread(target=self.start_monitoring, daemon=True).start()

            # Main event loop
            while dpg.is_dearpygui_running():
                dpg.render_dearpygui_frame()
                time.sleep(0.01)

        except Exception as e:
            logger.error(f"Error in main window: {e}")
            # В случае ошибки запускаем первичную настройку
            config = Config()
            config.update_config(
                client_uuid=None,
                auth_token=None,
                manager_uuid=None
            )
            self.quit_application()
            first_run = FirstRunWindow(self.server_url, self.on_registration_success)
            first_run.run()
        finally:
            # Cleanup
            if self.monitor:
                self.monitor.stop_monitoring()
            if self.icon:
                self.icon.stop()
            dpg.destroy_context()

    def on_registration_success(self, manager_uuid: str, client_uuid: str, token: str):
        """Callback при успешной регистрации."""
        # Сохраняем полученные данные в конфигурацию
        config = Config()
        config.update_config(
            client_uuid=client_uuid,
            auth_token=token,
            manager_uuid=manager_uuid
        )
        logger.info(f"Saved new client registration: UUID={client_uuid}")
        
        # Обновляем текущие значения
        self.client_uuid = client_uuid
        self.auth_token = token
        
        # Запускаем основное окно заново
        self.run() 