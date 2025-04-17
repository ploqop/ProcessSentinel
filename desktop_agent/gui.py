import PySimpleGUI as sg

def show_login_window():
    layout = [[sg.Text("Введите ключ подключения (UUID управляющего):")],
              [sg.Input(key='-KEY-')],
              [sg.Button("Подключиться")]]
    return sg.Window("Вход", layout, finalize=True)

def show_main_window(connection_status, blacklist):
    layout = [
        [sg.Text(f"Статус соединения: {connection_status}", key='-STATUS-')],
        [sg.Frame("Запрещённые процессы", [[sg.Listbox(values=blacklist, size=(30, 5), key='-BLIST-')]])],
        [sg.Button("Добавить"), sg.Button("Удалить"), sg.Button("Обновить"), sg.Exit()]
    ]
    return sg.Window("Клиентский агент", layout, finalize=True)
