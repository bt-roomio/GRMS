# Мониторинг Gateway Устройств - Документация

## Обзор

Система мониторинга gateway устройств собирает метрики о статусе устройств и экспортирует их в Prometheus через endpoint `/metrics`.

## Конфигурация

### Переменные окружения

#### 1. `DJANGO_IS_MONITORING_GATEWAYS`

**Описание**: Включает/выключает мониторинг gateway устройств

**Значения**:
- `True`, `true`, `1`, `yes` - мониторинг включен (по умолчанию)
- `False`, `false`, `0`, `no` - мониторинг выключен

**Пример**:
```bash
# В .env файле
DJANGO_IS_MONITORING_GATEWAYS=True

# Или в docker-compose.yml
environment:
  - DJANGO_IS_MONITORING_GATEWAYS=True
```

**Эффект**:
- Если `False`, функция `update_device_metrics()` не будет выполняться
- Метрики не будут обновляться при запросах к `/metrics`

---

#### 2. `DJANGO_MONITORING_EXCLUDED_GATEWAYS`

**Описание**: Список UUID gateway устройств, которые нужно исключить из мониторинга

**Формат**: UUID через запятую или пробел

**Примеры**:
```bash
# Через запятую
DJANGO_MONITORING_EXCLUDED_GATEWAYS=14a2bd4b-6f3d-405e-910a-04feb36bb70e,47aef21b-6cc9-4ec5-8573-1a6f491940c0

# Через пробелы
DJANGO_MONITORING_EXCLUDED_GATEWAYS="14a2bd4b-6f3d-405e-910a-04feb36bb70e 47aef21b-6cc9-4ec5-8573-1a6f491940c0"

# Смешанный формат (работает)
DJANGO_MONITORING_EXCLUDED_GATEWAYS="14a2bd4b-6f3d-405e-910a-04feb36bb70e, 47aef21b-6cc9-4ec5-8573-1a6f491940c0"
```

**Эффект**:
- Устройства из списка не будут попадать в метрики
- Их статус (online/offline) не будет отслеживаться

---

## Метрики

### 1. `devices_offline_total`

**Тип**: Gauge
**Описание**: Статус каждого gateway устройства (0 = online, 1 = offline)
**Labels**:
- `tenant_id` - UUID тенанта
- `tenant_name` - Название тенанта
- `device_id` - UUID устройства

**Пример в Prometheus**:
```promql
# Все offline устройства
devices_offline_total{device_id="14a2bd4b-6f3d-405e-910a-04feb36bb70e"} 1.0

# Все online устройства
devices_offline_total{device_id="47aef21b-6cc9-4ec5-8573-1a6f491940c0"} 0.0
```

**Запросы для Grafana**:
```promql
# Количество offline устройств по тенантам
sum by (tenant_name) (devices_offline_total)

# Список offline устройств
devices_offline_total == 1

# Процент offline устройств
(sum(devices_offline_total) / count(devices_offline_total)) * 100
```

---

### 2. `offline_gateway_devices_count`

**Тип**: Gauge
**Описание**: Общее количество offline gateway устройств
**Labels**: нет

**Пример в Prometheus**:
```promql
offline_gateway_devices_count 3.0
```

**Запросы для Grafana**:
```promql
# Простое отображение числа
offline_gateway_devices_count

# Алерт если больше 5 offline устройств
offline_gateway_devices_count > 5
```

---

## Примеры использования

### Сценарий 1: Мониторинг всех устройств

```bash
# .env
DJANGO_IS_MONITORING_GATEWAYS=True
DJANGO_MONITORING_EXCLUDED_GATEWAYS=
```

**Результат**:
- Все активные gateway устройства мониторятся
- Все offline устройства попадают в метрики

---

### Сценарий 2: Исключить тестовые устройства

```bash
# .env
DJANGO_IS_MONITORING_GATEWAYS=True
DJANGO_MONITORING_EXCLUDED_GATEWAYS=14a2bd4b-6f3d-405e-910a-04feb36bb70e,47aef21b-6cc9-4ec5-8573-1a6f491940c0
```

**Результат**:
- Устройства `14a2bd4b-6f3d-405e-910a-04feb36bb70e` и `47aef21b-6cc9-4ec5-8573-1a6f491940c0` не попадут в метрики
- Остальные устройства мониторятся нормально

---

### Сценарий 3: Полное отключение мониторинга

```bash
# .env
DJANGO_IS_MONITORING_GATEWAYS=False
```

**Результат**:
- Мониторинг полностью отключен
- Метрики не обновляются
- Middleware выходит сразу при запросе к `/metrics`

---

## Логирование

### Уровни логов

```python
# Мониторинг отключен
logger.debug("Мониторинг gateway устройств отключен (DJANGO_IS_MONITORING_GATEWAYS=False)")

# Начало обновления
logger.info("Обновление метрик устройств...")

# Исключенные устройства
logger.info(f"Исключено gateway устройств из мониторинга: 2 (['uuid1', 'uuid2'])")

# Успешное завершение
logger.info("Метрики устройств успешно обновлены")

# Ошибка
logger.error(f"Ошибка при обновлении метрик: {e}", exc_info=True)
```

### Просмотр логов

```bash
# Docker
docker compose logs -f backend | grep "метрик"

# Локально
tail -f logs/django.log | grep "метрик"
```

---

## Troubleshooting

### Метрики не обновляются

**Проблема**: Метрики показывают старые значения

**Решение**:
1. Проверьте `DJANGO_IS_MONITORING_GATEWAYS=True`
2. Перезапустите backend: `docker compose restart backend`
3. Проверьте логи: `docker compose logs backend | grep "Обновление метрик"`
4. Очистите старые метрики: `rm -f /tmp/prometheus_multiproc/gauge_*.db`

---

### Устройство не исключается

**Проблема**: Устройство из `DJANGO_MONITORING_EXCLUDED_GATEWAYS` все еще в метриках

**Решение**:
1. Убедитесь, что UUID правильный (полный UUID, не короткий ID)
2. Проверьте формат: UUID через запятую или пробел
3. Перезапустите backend после изменения .env
4. Проверьте логи на наличие сообщения "Исключено gateway устройств"

**Проверка**:
```bash
# Зайдите в Django shell
docker exec -it django python manage.py shell

# Проверьте настройки
from django.conf import settings
print(settings.DJANGO_MONITORING_EXCLUDED_GATEWAYS)
# Должен вернуть: ['uuid1', 'uuid2', ...]
```

---

### Метрики с задержкой

**Проблема**: После изменения `device.status` метрики обновляются не сразу

**Решение**: Это было исправлено изменением `multiprocess_mode` с `max` на `mostrecent`

**Проверка**:
```bash
# Убедитесь что в metrics.py используется mostrecent
grep "multiprocess_mode" apps/main/metrics.py
# Должно быть: multiprocess_mode="mostrecent"
```

---

## Внутренняя реализация

### Файлы

- `apps/main/metrics.py` - Основная логика метрик
- `apps/main/middlewares/device.py` - Middleware для обновления метрик
- `config/settings.py` - Конфигурация (строки 109-113)

### Алгоритм работы

1. **Запрос к `/metrics`**
   ```
   ↓
   DeviceMetricsMiddleware.__call__()
   ↓
   update_device_metrics()
   ```

2. **Проверка настроек**
   ```python
   if not settings.DJANGO_IS_MONITORING_GATEWAYS:
       return  # Выход без обновления
   ```

3. **Очистка метрик**
   ```python
   _clear_metrics():
       - Получить все gateway устройства
       - Исключить DJANGO_MONITORING_EXCLUDED_GATEWAYS
       - Установить все метрики в 0
   ```

4. **Обновление метрик**
   ```python
   _update_device_status_metrics():
       - Получить offline gateway устройства
       - Исключить DJANGO_MONITORING_EXCLUDED_GATEWAYS
       - Установить метрики в 1 для offline устройств
       - Посчитать общее количество offline
   ```

---

## Тестирование

### Ручное тестирование

```bash
# 1. Получить список gateway устройств
docker exec -it django python manage.py shell -c "
from main.models import Device
gateways = Device.objects.filter(is_active=True, additional_info__gateway=True)
for gw in gateways:
    print(f'{gw.id} | {gw.name} | Status: {gw.status}')
"

# 2. Изменить статус устройства
docker exec -it django python manage.py shell -c "
from main.models import Device
device = Device.objects.get(id='YOUR_DEVICE_UUID')
device.status = False  # или True
device.save()
"

# 3. Проверить метрики
curl http://localhost:8000/metrics | grep offline_gateway

# 4. Снова изменить статус и сразу проверить
# Метрики должны обновиться мгновенно!
```

---

## Changelog

### v2.0 (Current)
- ✅ Добавлена поддержка `DJANGO_IS_MONITORING_GATEWAYS`
- ✅ Добавлена поддержка `DJANGO_MONITORING_EXCLUDED_GATEWAYS`
- ✅ Исправлена задержка обновления метрик (`mostrecent` вместо `max`)
- ✅ Добавлено логирование исключенных устройств
- ✅ Добавлена агрегированная метрика `offline_gateway_devices_count`

### v1.0
- Базовый мониторинг gateway устройств
- Метрика `devices_offline_total`
- Использовал `multiprocess_mode="max"` (проблема с задержкой)
