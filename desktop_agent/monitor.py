import psutil
import threading
import time
from network import send_report

BLACKLIST = ['notepad.exe', 'calc.exe']

def monitor_processes(interval=5):
    while True:
        # Получаем текущие процессы
        processes = [(p.pid, p.name()) for p in psutil.process_iter(['name'])]
        for pid, name in processes:
            if name.lower() in BLACKLIST:
                print(f"Запрещённый процесс обнаружен: {name} (PID: {pid}). Завершаем...")
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

def start_monitoring(interval=5):
    t = threading.Thread(target=monitor_processes, args=(interval,), daemon=True)
    t.start()
