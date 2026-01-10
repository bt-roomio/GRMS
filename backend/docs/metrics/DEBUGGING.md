План: Отладка mq_async.py с breakpoints

Цель

Настроить локальную среду для отладки mq_async.py с возможностью:
- Использования breakpoints (pdb/IDE debugger)
- Анализа производительности batch processing
- Отслеживания ошибок обработки сообщений
- Проверки работы 2-tier кэширования устройств
- Понимания общего потока данных

Предварительные условия

- RabbitMQ должен быть запущен (для получения сообщений)
- Redis должен быть запущен (для кэширования устройств)
- PostgreSQL с данными (для запросов устройств)
- Данные тестовых устройств в базе данных

Стратегия: Многоуровневая отладка

Уровень 1: Подготовка окружения

1.1. Запуск зависимостей через Docker Compose

# Запустить только инфраструктурные сервисы (без django)
cd /Users/bakhodir/Projects/GRMS
docker compose up -d postgres redis rabbitmq mqtt-broker

1.2. Настройка переменных окружения

Создать файл .env.debug для локального запуска:
# Database
POSTGRES_HOST=localhost
POSTGRES_PORT=5433
POSTGRES_DB=grms
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379

# RabbitMQ
RABBIT_LOGIN=guest
RABBIT_PASSWORD=guest
RABBIT_HOST=localhost
RABBIT_PORT=5672

# Django
DJANGO_SECRET_KEY=your-secret-key
DJANGO_DEBUG=True
DJANGO_SETTINGS_MODULE=config.settings

1.3. Загрузка переменных окружения

export $(cat backend/.env.debug | xargs)

Уровень 2: Включение DEBUG логирования

2.1. Временно изменить уровень логирования в mq_async.py

Файл: backend/apps/core/management/commands/mq_async.py

Добавить после строки 78 (logger = logging.getLogger("core")):
logger = logging.getLogger("core")
# ВРЕМЕННО для отладки - установить DEBUG уровень
logger.setLevel(logging.DEBUG)

# Добавить handler с детальным форматом
debug_handler = logging.StreamHandler()
debug_handler.setLevel(logging.DEBUG)
debug_formatter = logging.Formatter(
    '%(levelname)s %(asctime)s [%(name)s:%(lineno)d] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
debug_handler.setFormatter(debug_formatter)
logger.addHandler(debug_handler)

Эффект: Все logger.debug() вызовы начнут выводиться с указанием строки кода.

2.2. Добавить метрики производительности

Добавить после импортов:
import time
from collections import defaultdict

# Метрики для отладки
batch_processing_times = defaultdict(list)
device_cache_stats = {"memory_hits": 0, "redis_hits": 0, "db_hits": 0}

Уровень 3: Отладка с breakpoints

3.1. Использование Python pdb (встроенный отладчик)

Ключевые места для breakpoints:

1. Начало обработки batch (строка 260):
async def process_batch(self, batch: list[aio_pika.IncomingMessage]):
    import pdb; pdb.set_trace()  # BREAKPOINT 1: Старт обработки
    logger.debug(f"[{self.queue_name}] Processing batch: {len(batch)} messages")

2. Валидация сообщений (строка 274):
for message in batch:
    try:
        import pdb; pdb.set_trace()  # BREAKPOINT 2: Валидация каждого сообщения
        device, msg = await validate_body(message.body)

3. Кэширование устройств (строка 87 в функции get_device):
async def get_device(device_id: str, tenant_id=None) -> DeviceType | None:
    import pdb; pdb.set_trace()  # BREAKPOINT 3: Проверка кэша
    current_time = get_mil_sec() // 1000

4. Batch telemetry processing (строка 293):
if telemetry_batch:
    try:
        import pdb; pdb.set_trace()  # BREAKPOINT 4: Обработка телеметрии
        data_only = [(d, t, data) for d, t, data, _ in telemetry_batch]

3.2. Использование IDE Debugger (VS Code / PyCharm)

VS Code Launch Configuration (backend/.vscode/launch.json):
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Debug mq_async",
      "type": "python",
      "request": "launch",
      "program": "${workspaceFolder}/apps/core/management/commands/mq_async.py",
      "console": "integratedTerminal",
      "cwd": "${workspaceFolder}",
      "env": {
        "DJANGO_SETTINGS_MODULE": "config.settings",
        "POSTGRES_HOST": "localhost",
        "POSTGRES_PORT": "5433",
        "REDIS_HOST": "localhost",
        "REDIS_PORT": "6379",
        "RABBIT_HOST": "localhost",
        "RABBIT_PORT": "5672"
      },
      "justMyCode": false
    }
  ]
}

PyCharm Run Configuration:
- Script path: /Users/bakhodir/Projects/GRMS/backend/apps/core/management/commands/mq_async.py
- Working directory: /Users/bakhodir/Projects/GRMS/backend
- Environment variables: загрузить из .env.debug

Уровень 4: Специфичные отладочные инструменты

4.1. Профилирование batch processing

Добавить декоратор для измерения времени:
def timing_decorator(func_name):
    def decorator(func):
        async def wrapper(*args, **kwargs):
            start = time.perf_counter()
            result = await func(*args, **kwargs)
            elapsed = time.perf_counter() - start
            batch_processing_times[func_name].append(elapsed)
            logger.info(f"[TIMING] {func_name}: {elapsed:.4f}s")
            return result
        return wrapper
    return decorator

# Применить к batch функциям
@timing_decorator("sync_telemetry_batch")
async def timed_sync_telemetry_batch(data):
    return await sync_telemetry_batch_async(data)

4.2. Отслеживание кэш-статистики устройств

Модифицировать функцию get_device (строка 87):
async def get_device(device_id: str, tenant_id=None) -> DeviceType | None:
    logger.debug(f"[CACHE] Getting device: {device_id}")

    # Tier 1: Memory cache
    current_time = get_mil_sec() // 1000
    cache_entry = _DEVICE_MEMORY_CACHE.get(device_id)
    if cache_entry and (current_time - cache_entry["cached_at"]) < _MEMORY_CACHE_TTL:
        device_cache_stats["memory_hits"] += 1
        logger.debug(f"[CACHE] Memory HIT for {device_id} | Stats: {device_cache_stats}")
        return cache_entry["data"]

    # Tier 2: Redis cache
    cache_key = f"prs_msg:device_cache:{device_id}"
    cached_device_raw = await redis_client.get(cache_key)
    cached_device = cached_device_raw.decode("utf-8") if isinstance(cached_device_raw, bytes) else None

    if cached_device:
        device_cache_stats["redis_hits"] += 1
        logger.debug(f"[CACHE] Redis HIT for {device_id} | Stats: {device_cache_stats}")
        data = json.loads(cached_device)
        _update_memory_cache(device_id, data)
        return data

    # Tier 3: Database
    device_cache_stats["db_hits"] += 1
    logger.debug(f"[CACHE] Database query for {device_id} | Stats: {device_cache_stats}")
    # ... остальной код

4.3. Отслеживание ошибок и requeue

Модифицировать acknowledge_messages (строка 353):
async def acknowledge_messages(self, batch: list, message_status: dict):
    success_count = 0
    failure_requeue_count = 0
    failure_no_requeue_count = 0

    for message in batch:
        try:
            status = message_status.get(message.delivery_tag, "failure_requeue")

            if status == "success":
                await message.ack()
                success_count += 1
            elif status == "failure_requeue":
                await message.nack(requeue=True)
                failure_requeue_count += 1
                logger.warning(f"[ACK] Message {message.delivery_tag} REQUEUED")
            else:
                await message.nack(requeue=False)
                failure_no_requeue_count += 1
                logger.error(f"[ACK] Message {message.delivery_tag} REJECTED (no requeue)")

        except Exception as e:
            logger.error(f"[ACK] Failed to ack/nack message {message.delivery_tag}: {e}")

    logger.info(
        f"[ACK SUMMARY] Success: {success_count}, "
        f"Requeue: {failure_requeue_count}, "
        f"Rejected: {failure_no_requeue_count}"
    )

Уровень 5: Запуск и отладка

5.1. Запуск локально с логами

cd /Users/bakhodir/Projects/GRMS/backend
python apps/core/management/commands/mq_async.py

5.2. Запуск с pdb

cd /Users/bakhodir/Projects/GRMS/backend
python -m pdb apps/core/management/commands/mq_async.py

PDB команды:
- n (next) - следующая строка
- s (step) - войти в функцию
- c (continue) - продолжить до следующего breakpoint
- p variable - вывести значение переменной
- pp variable - красиво вывести переменную
- l - показать текущий код
- w - показать call stack
- q - выйти

5.3. Генерация тестовых сообщений

Использовать sim_message.py для создания тестовых сообщений:
cd /Users/bakhodir/Projects/GRMS/backend
./manage.py shell

# В shell
from apps.core.management.commands.sim_message import Command
cmd = Command()
# Отправить тестовое сообщение телеметрии
cmd.telemetry(value=25.5, device_id="00136d0a-f59b-4049-a35d-01bf86b07d3e")

Уровень 6: Анализ результатов

6.1. Метрики производительности

После обработки нескольких batch'ей, добавить в shutdown_gracefully:
async def shutdown_gracefully(self):
    logger.info("Shutting down gracefully...")

    # Вывести статистику
    logger.info("=" * 60)
    logger.info("PERFORMANCE METRICS:")
    for func_name, times in batch_processing_times.items():
        if times:
            avg_time = sum(times) / len(times)
            max_time = max(times)
            min_time = min(times)
            logger.info(f"  {func_name}:")
            logger.info(f"    Avg: {avg_time:.4f}s, Min: {min_time:.4f}s, Max: {max_time:.4f}s")

    logger.info("CACHE STATISTICS:")
    total_requests = sum(device_cache_stats.values())
    if total_requests > 0:
        logger.info(f"  Total requests: {total_requests}")
        logger.info(f"  Memory hits: {device_cache_stats['memory_hits']} ({device_cache_stats['memory_hits']/total_requests*100:.1f}%)")
        logger.info(f"  Redis hits: {device_cache_stats['redis_hits']} ({device_cache_stats['redis_hits']/total_requests*100:.1f}%)")
        logger.info(f"  DB hits: {device_cache_stats['db_hits']} ({device_cache_stats['db_hits']/total_requests*100:.1f}%)")
    logger.info("=" * 60)

    # Остальной код shutdown...

6.2. Проверка потока данных

Добавить трассировку сообщений:
# В начале validate_body (строка 137)
async def validate_body(body: bytes):
    msg = json.loads(body)
    logger.debug(f"[FLOW] Received message: topic={msg.get('topic')}, device={msg.get('sourceDeviceUUID')}")
    device = await get_device(msg.get("sourceDeviceUUID"))
    if not device:
        logger.error(f"[FLOW] Device not found: {msg.get('sourceDeviceUUID')}")
        raise ValueError(f"Device not found: {msg.get('sourceDeviceUUID')}")
    logger.debug(f"[FLOW] Device validated: {device['name']} (tenant={device['tenant_id']})")
    return device, msg

Критические файлы для отладки

1. Основной файл: backend/apps/core/management/commands/mq_async.py
2. Кэш устройств: backend/apps/core/management/mq/device_cache.py
3. Batch обработчики:
  - backend/apps/core/management/mq/telemetry.py
  - backend/apps/core/management/mq/attributes.py
  - backend/apps/core/management/mq/state_device_batch_async.py
4. Конфигурация: backend/config/settings.py (LOGGING)
5. Симуляция: backend/apps/core/management/commands/sim_message.py

Порядок выполнения

1. ✅ Запустить инфраструктуру (postgres, redis, rabbitmq)
2. ✅ Загрузить тестовые данные (устройства, tenant)
3. ✅ Настроить .env.debug с правильными параметрами
4. ✅ Добавить DEBUG logging в mq_async.py
5. ✅ Добавить метрики производительности и кэш-статистику
6. ✅ Установить breakpoints в ключевых местах
7. ✅ Запустить mq_async.py локально через IDE debugger
8. ✅ Сгенерировать тестовые сообщения через sim_message.py
9. ✅ Проанализировать логи и метрики
10. ✅ Итерировать: добавить breakpoints в проблемные места

Альтернативные подходы

Подход A: Асинхронный профайлер (для продакшена)

Использовать aiomonitor для подключения к работающему процессу:
import aiomonitor
aiomonitor.start_monitor(loop=asyncio.get_event_loop(), port=50101)

Подход B: Structured logging (для продакшена)

Заменить простые логи на structured JSON logs:
import structlog
logger = structlog.get_logger()
logger.info("batch_processed", batch_size=len(batch), duration=elapsed)

Подход C: Отладка в Docker с удаленным debugger

Использовать debugpy для подключения VS Code к процессу в контейнере:
import debugpy
debugpy.listen(("0.0.0.0", 5678))
logger.info("Waiting for debugger attach...")
debugpy.wait_for_client()

Ожидаемые результаты

После выполнения плана вы сможете:
- ✅ Ставить breakpoints и пошагово выполнять код
- ✅ Видеть детальные логи всех операций (batch, cache, db)
- ✅ Измерять время обработки каждого batch'а
- ✅ Отслеживать hit rate кэша устройств (memory/redis/db)
- ✅ Понимать почему сообщения requeue или reject
- ✅ Анализировать полный поток данных от RabbitMQ до БД

