import PyInstaller.__main__
import os
from create_icon import create_icon

# Создаем иконку
create_icon()

# Получаем путь к текущей директории
current_dir = os.path.dirname(os.path.abspath(__file__))

# Путь к иконке
icon_path = os.path.join(current_dir, 'gui', 'icon.png')

# Аргументы для PyInstaller
args = [
    'main.py',  # основной файл
    '--name=ProcessSentinel',  # имя выходного файла
    '--onefile',  # создать один exe файл
    '--noconsole',  # не показывать консоль
    '--clean',  # очистить кэш перед сборкой
    '--add-data=config;config',  # добавить директорию с конфигурацией
    '--add-data=gui/icon.png;gui',  # добавить иконку как data file
    f'--icon={icon_path}',  # иконка приложения
    '--hidden-import=PIL._tkinter_finder',  # необходимые скрытые импорты
]

# Запускаем сборку
PyInstaller.__main__.run(args) 