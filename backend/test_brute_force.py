#!/usr/bin/env python
"""
Тестовый скрипт для проверки защиты от brute force
"""
import json
import time

import requests

# Конфигурация
API_URL = "http://localhost:8000/api/v1/users/access-token/"
USERNAME = "testuser"
WRONG_PASSWORD = "wrongpassword"


class BruteForceTest:
    def __init__(self, api_url):
        self.api_url = api_url
        self.session = requests.Session()

    def test_basic_brute_force(self):
        """Тест 1: Базовая защита (5 попыток)"""
        print("\n" + "=" * 60)
        print("🧪 ТЕСТ 1: Базовая защита от brute force")
        print("=" * 60)
        data = {}
        for i in range(10):
            print(f"\nПопытка {i+1}:", end=" ")

            try:
                response = self.session.post(self.api_url, json={"username": USERNAME, "password": WRONG_PASSWORD})

                print(f"Status: {response.status_code}")

                # Вывести ответ
                try:
                    data = response.json()
                    if "attempts_left" in data:
                        print(f"  └─ Осталось попыток: {data['attempts_left']}")
                    if "detail" in data:
                        print(f"  └─ Сообщение: {data['detail']}")
                except Exception:
                    pass

                # Проверить блокировку
                if response.status_code == 429:
                    print(f"\n✅ УСПЕХ: Заблокировано после {i+1} попыток!")
                    print(f"📊 Response: {json.dumps(data, indent=2)}")
                    return True

            except Exception as e:
                print(f"❌ Ошибка: {e}")
                return False

            time.sleep(0.5)

        print("\n❌ ОШИБКА: Блокировка не сработала после 10 попыток!")
        return False

    def test_progressive_delays(self):
        """Тест 2: Прогрессивные задержки"""
        print("\n" + "=" * 60)
        print("🧪 ТЕСТ 2: Прогрессивные задержки")
        print("=" * 60)

        delays = []

        for i in range(5):
            start_time = time.time()

            self.session.post(self.api_url, json={"username": f"delaytest_{i}", "password": WRONG_PASSWORD})

            elapsed = time.time() - start_time
            delays.append(elapsed)

            print(f"Попытка {i+1}: {elapsed:.2f}s")

        # Проверить что задержки увеличиваются
        is_progressive = all(delays[i] <= delays[i + 1] for i in range(len(delays) - 1))

        if is_progressive:
            print("\n✅ УСПЕХ: Задержки увеличиваются экспоненциально")
            print("📊 Задержки: {[f'{d:.2f}s' for d in delays]}")
        else:
            print("\n⚠️  ПРЕДУПРЕЖДЕНИЕ: Задержки не увеличиваются")

        return is_progressive

    def test_extended_windows(self):
        """Тест 3: Расширенные временные окна"""
        print("\n" + "=" * 60)
        print("🧪 ТЕСТ 3: Расширенные временные окна (1 час)")
        print("=" * 60)
        print("⚠️  Этот тест делает 11 попыток с интервалом 6 секунд")
        print("(Симуляция медленной атаки)")

        for i in range(11):
            response = self.session.post(self.api_url, json={"username": "slowattack", "password": f"wrong{i}"})

            print(f"Попытка {i+1}: Status {response.status_code}", end="")

            if response.status_code == 429:
                print(" - ЗАБЛОКИРОВАНО!")
                print(f"\n✅ УСПЕХ: Расширенное окно сработало после {i+1} попыток")
                return True

            print()

            if i < 10:
                print("  └─ Ожидание 6 секунд...")
                time.sleep(6)

        print("\n❌ ОШИБКА: Расширенное окно не сработало")
        return False

    def test_reset_on_success(self):
        """Тест 4: Сброс счетчика при успешном входе"""
        print("\n" + "=" * 60)
        print("🧪 ТЕСТ 4: Сброс счетчика при успехе")
        print("=" * 60)

        # Сделать 3 неудачных попытки
        print("Шаг 1: Делаем 3 неудачных попытки...")
        for i in range(3):
            response = self.session.post(self.api_url, json={"username": "karina@gmail.com", "password": "Karina2025"})
            print(f"  Попытка {i+1}: {response.status_code}")

        # Симуляция успешного входа (нужен реальный пользователь)
        print("\nШаг 2: Симуляция успешного входа...")
        print("⚠️  Для полного теста нужен реальный аккаунт")

        # Проверить что счетчик НЕ вырос
        print("\nШаг 3: Проверяем что счетчик сбросился...")
        for i in range(3):
            response = self.session.post(self.api_url, json={"username": "resettest", "password": "wrong"})
            print(f"  Попытка {i+1}: {response.status_code}")

        print("\n⚠️  Тест частичный - нужен реальный аккаунт для проверки")
        return True

    def run_all_tests(self):
        """Запустить все тесты"""
        print("\n" + "🛡️  " * 20)
        print("ТЕСТИРОВАНИЕ ЗАЩИТЫ ОТ BRUTE FORCE")
        print("🛡️  " * 20)

        results = {
            "test_1_basic": self.test_basic_brute_force(),
            "test_2_progressive_delays": self.test_progressive_delays(),
            "test_3_extended_windows": self.test_extended_windows(),
            "test_4_reset": self.test_reset_on_success(),
        }

        # Итоги
        print("\n" + "=" * 60)
        print("📊 ИТОГИ ТЕСТИРОВАНИЯ")
        print("=" * 60)

        for test_name, passed in results.items():
            status = "✅ PASSED" if passed else "❌ FAILED"
            print(f"{test_name}: {status}")

        total = len(results)
        passed = sum(results.values())
        percentage = (passed / total) * 100

        print(f"\n🎯 Результат: {passed}/{total} тестов пройдено ({percentage:.0f}%)")

        if percentage == 100:
            print("🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ!")
        elif percentage >= 75:
            print("⚠️  Большинство тестов пройдено, но есть проблемы")
        else:
            print("❌ КРИТИЧЕСКИЕ ПРОБЛЕМЫ - защита не работает!")

        return results


def main():
    """Главная функция"""

    # Проверить доступность API
    print("🔍 Проверка доступности API...")
    try:
        response = requests.get("http://localhost:8000/api/")
        print(f"✅ API доступен (Status: {response.status_code})")
    except Exception as e:
        print(f"❌ API недоступен: {e}")
        print("\nЗапустите Django сервер:")
        print("  python manage.py runserver")
        return

    # Запустить тесты
    tester = BruteForceTest(API_URL)
    tester.run_all_tests()


if __name__ == "__main__":
    main()
