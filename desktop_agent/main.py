# TODO: разбить по файликам
# TODO: кодировка
import threading
import time
import json
import os
import psutil
import requests
import dearpygui.dearpygui as dpg
from PIL import Image, ImageDraw
import pystray

# ========================
# 1. Конфигурация и вспомогательные функции
# ========================

CONFIG_FILE = "config.json"
SERVER_URL = "https://yourserver.com/api"  # Замените на адрес вашего сервера

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_config(config):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4)

def validate_key(key):
    # Пример проверки ключа; замените на реальную логику с запросом к серверу
    try:
        # response = requests.post(f"{SERVER_URL}/validate/", json={"key": key})
        # response.raise_for_status()
        # return response.json()["valid"]
        return bool(key)  # если ключ не пустой, считаем его валидным
    except Exception as ex:
        print("Ошибка при проверке ключа:", ex)
        return False

def send_report(report):
    # Пример отправки отчёта на сервер.
    try:
        # response = requests.post(f"{SERVER_URL}/report/", json=report)
        # response.raise_for_status()
        # return True
        print("Отчет отправлен:", report)
        return True
    except Exception as ex:
        print("Ошибка отправки отчёта:", ex)
        return False

# ========================
# 2. Фоновый мониторинг процессов
# ========================

# Локальный список запрещённых процессов (можно расширить загрузкой из конфига)
GLOBAL_BLACKLIST = ["notepad.exe", "calc.exe"]

def monitor_processes(interval=5):
    while True:
        processes = [(proc.pid, proc.name()) for proc in psutil.process_iter(['name'])]
        for pid, name in processes:
            # Сравнение в нижнем регистре для надёжности
            if name.lower() in [p.lower() for p in GLOBAL_BLACKLIST]:
                print(f"Обнаружен запрещённый процесс: {name} (PID: {pid}). Завершаем...")
                try:
                    psutil.Process(pid).terminate()
                    report = {
                        'event': 'process_terminated',
                        'process': name,
                        'pid': pid,
                        'timestamp': time.time()
                    }
                    send_report(report)
                except Exception as ex:
                    print(f"Ошибка завершения процесса {name}: {ex}")
        time.sleep(interval)

# ========================
# 3. Реализация системного трея через pystray
# ========================

def create_tray_image():
    # Создаем простую иконку 64x64 пикселей с квадратом
    width = 64
    height = 64
    image = Image.new('RGB', (width, height), color=(0, 0, 0))
    dc = ImageDraw.Draw(image)
    dc.rectangle([width//4, height//4, width*3//4, height*3//4], fill=(255,255,255))
    return image

def on_tray_open(icon, item):
    # При выборе "Открыть" восстанавливаем главное окно
    dpg.show_item("main_window")

def on_tray_exit(icon, item):
    # При выборе "Выход" завершаем приложение
    icon.stop()
    dpg.stop_dearpygui()

def create_tray_icon():
    menu = (pystray.MenuItem("Открыть", on_tray_open),
            pystray.MenuItem("Выход", on_tray_exit))
    icon = pystray.Icon("client_agent", create_tray_image(), "Клиентский агент", menu)
    icon.run()

def start_tray_icon():
    tray_thread = threading.Thread(target=create_tray_icon, daemon=True)
    tray_thread.start()

# ========================
# 4. DearPyGui: графический интерфейс
# ========================

global_state = {
    "connected": False,
    "key": None,
    "blacklist": GLOBAL_BLACKLIST
}

def login_callback(sender, app_data, user_data):
    key = dpg.get_value("login_input")
    if validate_key(key):
        global_state["connected"] = True
        global_state["key"] = key
        # Сохраняем ключ в конфигурации
        config = load_config()
        config["key"] = key
        save_config(config)
        # Переключаем окно: удаляем окно входа, создаем основное окно
        dpg.delete_item("login_window")
        create_main_window()
        # Запускаем фоновый мониторинг процессов
        threading.Thread(target=monitor_processes, args=(5,), daemon=True).start()
        # Запускаем системный трей
        start_tray_icon()
    else:
        dpg.set_value("error_text", "Неверный ключ или ошибка подключения")

def create_login_window():
    with dpg.window(tag="login_window", label="Вход", width=400, height=200):
        dpg.add_text("Введите ключ подключения (UUID управляющего):")
        dpg.add_input_text(tag="login_input", width=300)
        dpg.add_button(label="Подключиться", callback=login_callback)
        dpg.add_text("", tag="error_text", color=[255, 0, 0])

def update_status_callback(sender, app_data, user_data):
    # Пример обновления статуса – можно расширять проверки подключения
    dpg.set_value("status_text", "Статус соединения: Подключено")

def hide_to_tray_callback(sender, app_data, user_data):
    dpg.hide_item("main_window")

def create_main_window():
    with dpg.window(tag="main_window", label="Клиентский агент", width=600, height=400):
        dpg.add_text("Статус соединения:", tag="status_text", default_value="Статус соединения: Подключено")
        dpg.add_separator()
        dpg.add_text("Запрещённые процессы:")
        # Список запрещённых процессов
        dpg.add_listbox(global_state["blacklist"], tag="blacklist_list", num_items=4, width=200)
        dpg.add_spacing(count=2)
        dpg.add_button(label="Добавить процесс", callback=lambda: print("Добавить процесс"))
        dpg.add_same_line()
        dpg.add_button(label="Удалить процесс", callback=lambda: print("Удалить процесс"))
        dpg.add_spacing(count=2)
        dpg.add_button(label="Обновить статус", callback=update_status_callback)
        dpg.add_same_line()
        dpg.add_button(label="Свернуть в трей", callback=hide_to_tray_callback)
        dpg.add_button(label="Выход", callback=lambda: dpg.stop_dearpygui())

def main():
    dpg.create_context()
    create_login_window()
    dpg.create_viewport(title="Клиентский агент", width=800, height=600)
    dpg.setup_dearpygui()
    dpg.show_viewport()
    dpg.start_dearpygui()  # Главный цикл отрисовки
    dpg.destroy_context()

if __name__ == '__main__':
    main()
