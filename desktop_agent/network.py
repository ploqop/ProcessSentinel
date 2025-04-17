import requests

SERVER_URL = 'https://yourserver.com/api'

def validate_key(key):
    try:
        response = requests.post(f'{SERVER_URL}/validate/', json={'key': key})
        response.raise_for_status()
        return response.json()['valid']
    except Exception as ex:
        print("Ошибка проверки ключа:", ex)
        return False

def send_report(report):
    try:
        response = requests.post(f'{SERVER_URL}/report/', json=report)
        response.raise_for_status()
        return True
    except Exception as ex:
        print("Ошибка отправки отчёта:", ex)
        return False
