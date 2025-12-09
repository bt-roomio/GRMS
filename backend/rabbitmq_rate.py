import time

import requests

my_queue = "toGRMS"  # "%2Fattributes"
RABBITMQ_API_URL = f"http://localhost:15672/api/queues/%2F/{my_queue}"
AUTH = ("guest", "guest")
INTERVAL = 1


def get_delivery_rate():
    try:
        response = requests.get(RABBITMQ_API_URL, auth=AUTH)
        response.raise_for_status()
        data = response.json()
        rate = data.get("message_stats", {}).get("deliver_get_details", {}).get("rate", 0.0)
        return rate
    except requests.RequestException as e:
        print(f"❌ Ошибка при запросе: {e}")
        return None


def monitor():
    print("📡 Мониторинг скорости обработки сообщений (deliver_get_details.rate):\n")
    while True:
        rate = get_delivery_rate()
        if rate is not None:
            print(f"⚙️  Текущая скорость: {rate:.2f} msg/sec")
        else:
            print("🚫 Не удалось получить данные.")
        time.sleep(INTERVAL)


if __name__ == "__main__":
    monitor()
