import pystray
from PIL import Image
import os
import sys
from datetime import datetime

class TrayIcon:
    def __init__(self, process_monitor):
        self.process_monitor = process_monitor
        self.icon = None
        self.setup_tray()

    def setup_tray(self):
        """Создание иконки в системном трее."""
        # Создаем простое изображение для иконки (красный круг)
        image = Image.new('RGB', (64, 64), color='red')
        
        # Создаем меню
        menu = pystray.Menu(
            pystray.MenuItem(
                'Status: Running',
                lambda: None,
                enabled=False
            ),
            pystray.MenuItem(
                'Last Policy Update: Never',
                lambda: None,
                enabled=False
            ),
            pystray.MenuItem(
                'Exit',
                self.on_exit
            )
        )
        
        # Создаем иконку
        self.icon = pystray.Icon(
            "Process Sentinel",
            image,
            "Process Sentinel Agent",
            menu
        )

    def update_status(self, status, last_update=None):
        """Обновление статуса в меню."""
        if self.icon:
            self.icon.menu = pystray.Menu(
                pystray.MenuItem(
                    f'Status: {status}',
                    lambda: None,
                    enabled=False
                ),
                pystray.MenuItem(
                    f'Last Policy Update: {last_update or "Never"}',
                    lambda: None,
                    enabled=False
                ),
                pystray.MenuItem(
                    'Exit',
                    self.on_exit
                )
            )

    def on_exit(self):
        """Обработка выхода из приложения."""
        self.process_monitor.stop_monitoring()
        self.icon.stop()
        os._exit(0)

    def run(self):
        """Запуск иконки в трее."""
        self.icon.run() 