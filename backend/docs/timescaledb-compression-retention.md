# Compression и retention для `shuttle_ts_kv`

Runbook для прода: как включить сжатие (compression) и срок хранения (retention) TimescaleDB для
телеметрии, в каком порядке, как контролировать и как откатить.

## Содержание

1. [Контекст](#1-контекст)
2. [Решение и порядок шагов](#2-решение-и-порядок-шагов)
3. [Как выполнять ручные команды](#3-как-выполнять-ручные-команды)
4. [Шаг 0. Подготовка](#4-шаг-0-подготовка)
5. [Шаг 1. Убрать DELETE-задачи](#5-шаг-1-убрать-delete-задачи)
6. [Шаг 2. Пилот на одном чанке](#6-шаг-2-пилот-на-одном-чанке)
7. [Шаг 3. Миграция: compression и политика](#7-шаг-3-миграция-compression-и-политика)
8. [Шаг 4. Сжатие бэклога](#8-шаг-4-сжатие-бэклога)
9. [Шаг 5. Retention](#9-шаг-5-retention)
10. [Мониторинг](#10-мониторинг)
11. [Откат](#11-откат)
12. [Ограничения после включения](#12-ограничения-после-включения)

---

## 1. Контекст

Оба окружения: TimescaleDB 2.21.0, PostgreSQL 16, compression и retention не настроены.

| | `grms` (2026-11-10) | `cloud` (2026-11-05) |
|---|---|---|
| БД целиком | 46 GB | 121 GB |
| `shuttle_ts_kv` heap | 14,8 GB (~83 байт/строку, норма) | 50 GB (~14 GB данных, ~36 GB пустоты) |
| `shuttle_ts_kv` индексы | 31 GB (2/3 таблицы) | 69 GB (~30 GB нужных, ~39 GB пустоты) |
| Строк | ~191 млн | ~214 млн |
| Данные с | 2025-02 | 2025-10 |
| Рост | ~4,2 GB в месяц (~1,5 GB heap + ~2,7 GB индексов) | |
| Логи `*_LOGS` | ~2–3 тыс. строк в неделю, незначительно | ~107 тыс. строк в сутки, 42% байт записи |
| Bloat heap (самый большой чанк) | 31% свободного места | 91% свободного места |

**`grms`: проблема в объёме и индексах, а не в bloat.** Телеметрия хранится построчно, на каждую строку
приходится ~83 байта heap и ~175 байт в четырёх индексах. Таблица растёт на ~50 GB в год. Compression
решает это напрямую: колоночный формат и отсутствие построчных индексов на старых чанках.

**`cloud`: проблема в bloat от удалённых логов.** Причины:

- Логи устройств (ключи `*_LOGS`) пишутся в `shuttle_ts_kv` вместе с телеметрией: ~14% строк, ~42% байт
  (~107 тыс. строк и ~33 MB в сутки). `delete_old_logs` удалял их через 7 дней `DELETE`-ом. Место в старых
  дневных чанках освобождалось, но не переиспользовалось: новые строки пишутся только в текущий чанк.
  На июльском чанке `pgstattuple_approx` показал 91% свободного места, плотность индексов 10–57%.
- `aggregate_table_ts_kv` (дедуп) и `delete_old_logs` каждую ночь падают по `task_soft_time_limit=300`.
  `delete_old_logs` — один `DELETE` в одной транзакции, при таймауте он откатывается целиком.
- Compression и retention не настроены, таблица растёт без ограничений.

Термины:

- **Compression**: TimescaleDB перекладывает старый чанк в колоночный формат. Строки группируются по
  `segmentby`, сортируются по `orderby` и упаковываются пачками до 1000 значений, каждая колонка
  сжимается своим алгоритмом. Построчные B-tree индексы сжатому чанку не нужны. Данные пишутся в новую
  внутреннюю таблицу, исходный чанк очищается (truncate), место возвращается ОС, bloat исчезает. Чтение
  прозрачно для кода. В TimescaleDB ≥ 2.18 это называется *columnstore*, старые имена функций ниже
  работают как алиасы.
- **Retention**: фоновая задача удаляет чанки старше заданного возраста через `drop_chunks`, то есть
  `DROP TABLE` чанка целиком. Это мгновенно, место возвращается сразу. Удаляется **всё** в чанке.

---

## 2. Решение и порядок шагов

**Логи не удаляются и не выносятся в отдельную таблицу.** Они остаются в `shuttle_ts_kv`, сжимаются вместе
с телеметрией и живут столько же. Регулярных `DELETE` по таблице больше нет, поэтому новый bloat не
появляется, а старый уходит при сжатии.

Цена решения:

- логи копятся: ~33 MB в сутки несжатыми, после сжатия порядка 2–5 GB в год (уточнить на пилоте);
- срок хранения у логов и телеметрии общий (шаг 5);
- мусорные ключи (`Test_LOGS`, `f_LOGS`, дубли `RoomIo`/`roomio`/`Roomio`, `KNX`/`knx`, `Fanvil`/`fanvil`)
  тоже хранятся. Их надо убирать на стороне шлюзов, а не удалением из БД.

Порядок:

| Шаг | Что | Как | Риск |
|---|---|---|---|
| 0 | Бэкап вне сервера, проверки | вручную | — |
| 1 | Убрать `delete_old_logs` и `aggregate_table_ts_kv` | деплой кода | нет: задачи и так не работают |
| 2 | Включить compression и сжать **один** чанк, замерить | вручную, ночью | низкий, откат одной командой |
| 3 | Миграция: compression (идемпотентно) + политика с лимитом чанков за запуск | деплой кода | низкий |
| 4 | Политика постепенно сжимает бэклог; наблюдать, поднимать лимит | наблюдение | средний: нагрузка ночью |
| 5 | Retention | миграция после решения бизнеса | необратимо |

Шаг 1 обязательно раньше шага 3: compression несовместим с регулярными `DELETE` по старым данным.

**Ветки и деплой.** Прод собирается из `stable` (образ `latest`) и выкатывается ручными CI-джобами
`cloud-backend` и `grms-backend` (`make $MAKE_ENV deploy-backend`). Изменения шагов 1 и 3 делаются в
`stable` и потом вливаются в `dev`. Пути в этом документе указаны для `stable`. В `dev` настройки
разнесены по `config/settings/components/`, поэтому при слиянии `stable` → `dev` будет конфликт:
`CELERY_BEAT_SCHEDULE` в `dev` лежит в `config/settings/components/celery.py`.

**Миграция применяется на каждом окружении**, куда выкатывается образ (`entrypoint.sh` → `migrate`
при старте `backend`). Это произойдёт при **любом** следующем деплое `stable`, не только при
целевом. Поэтому бэклог сжимает сама политика с ограничением чанков за запуск, а не ручной скрипт: на
любом окружении сжатие идёт постепенно, без разового прохода по всей таблице. Порядок выкатки:
сначала `grms` (пилот, миграция, несколько ночей наблюдения), затем `cloud`. Перед деплоем шага 3 на
каждом окружении выполнить шаг 0. Пока `cloud` не готов, не выкатывать на него `stable` с миграцией.

---

## 3. Как выполнять ручные команды

Подключаться **напрямую к Postgres**, не через PgBouncer (transaction pooling не подходит для
долгих операций и `SET` на сессию):

```bash
cd ~/GRMS/deploy
docker exec -it postgres psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"
```

В начале каждой сессии, где что-то меняется:

```sql
SET lock_timeout = '5s';        -- fail fast instead of queueing behind other locks (and blocking inserts)
SET statement_timeout = 0;
\timing on
```

Если команда упала по `lock_timeout`, повторить позже. Ждать блокировку на проде нельзя: пока
`ALTER`/`compress_chunk` стоит в очереди, за ним встают вставки mq-async.

Изменяющие команды выполнять **не во время бэкапа**: `make_backup.sh` запускает `pg_dump` в 00:00 (по
времени сервера). `pg_dump` держит блокировку на все таблицы до конца дампа, и `compress_chunk` будет
ждать его.

---

## 4. Шаг 0. Подготовка

**1. Бэкап вне сервера.** `make_backup.sh` хранит один дамп в `/tmp/backups` на том же сервере и удаляет
его перед следующим запуском. Перед началом скопировать последний дамп за пределы сервера
(`scp`/`rsync`), убедиться, что он полный. Восстановление дампа TimescaleDB — только через
`SELECT timescaledb_pre_restore();` … `SELECT timescaledb_post_restore();` и в ту же версию расширения.

**2. Длительность бэкапа.** Нужна, чтобы выбрать окно для сжатия (по умолчанию 03:00):

```bash
ls -l --time-style=full-iso /tmp/backups/
```

Время в имени файла — старт `pg_dump`, mtime — окончание.

**3. Версия и фоновые задачи TimescaleDB:**

```sql
SELECT extversion FROM pg_extension WHERE extname = 'timescaledb';   -- 2.21.x
SHOW timescaledb.max_background_workers;                             -- default 16
SELECT job_id, application_name, proc_name, hypertable_name, schedule_interval
FROM timescaledb_information.jobs;
```

**4. Место на диске:**

```bash
df -h /var/lib/docker
docker exec postgres du -sh /var/lib/postgresql/data/pg_wal
```

Само сжатие места почти не требует: сжатая копия маленькая, исходник очищается сразу после.
Место нужно на **откат**: распаковка возвращает несжатый размер (без bloat). Полный откат — до ~45 GB.

**5. Замеры «до»** (сохранить вывод):

```sql
SELECT pg_size_pretty(pg_database_size(current_database()));
SELECT * FROM hypertable_detailed_size('shuttle_ts_kv');
SELECT count(*) FROM show_chunks('shuttle_ts_kv');
```

**6. Нет ли реплик и слотов** (иначе WAL от сжатия будет копиться):

```sql
SELECT slot_name, active, pg_size_pretty(pg_wal_lsn_diff(pg_current_wal_lsn(), restart_lsn)) AS lag
FROM pg_replication_slots;
```

---

## 5. Шаг 1. Убрать DELETE-задачи

Изменения в коде (ветка `stable`):

- `config/settings.py`: удалить из `CELERY_BEAT_SCHEDULE` `clean_logs` (00:00) и `aggregate-ts-kv` (03:00);
- `config/celery.py`: удалить их маршруты из `task_routes`;
- `apps/shuttle/tasks.py`: удалить `delete_old_logs`, `aggregate_table_ts_kv` и `deduplicate_ts_kv`
  (других вызовов нет).

`celery-beat` запускается как `celery -A config beat` без `--scheduler`, `CELERY_BEAT_SCHEDULER` не
задан. Значит, работает `PersistentScheduler` из настроек, а не `django_celery_beat` (приложение
установлено, но не используется). После перезапуска с новым конфигом удалённые записи пропадают из
расписания сами. Деплой: CI-джобы `cloud-backend`, `grms-backend`.

Если на окружении между деплоями останется задача из старого образа в очереди `low`, воркер с новым
кодом отклонит её как незарегистрированную (`Received unregistered task`). Это безвредно.

Проверка на следующий день (в 00:00 и 03:00 задач быть не должно):

```bash
docker logs celery-low --since 24h 2>&1 | grep -E "delete_old_logs|aggregate_table_ts_kv|Dedup ts_kv"
```

---

## 6. Шаг 2. Пилот на одном чанке

Цель: проверить сжатие на реальных данных, получить коэффициент и убедиться, что запросы не
деградируют. Выполнять ночью, после окончания бэкапа (раздел 3).

**1. Включить compression на таблице.** Это только метаданные, данные не трогаются. Настройки должны
совпадать с миграцией шага 3 один в один:

```sql
ALTER TABLE shuttle_ts_kv SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'entity_id, key',
    timescaledb.compress_orderby   = 'ts DESC'
);
```

- `segmentby = 'entity_id, key'`: почти все запросы фильтруют по устройству и ключу (`get_history`,
  `get_history_v2`, `tag_logs`, `gateway_logs`). Значения хранятся один раз на пачку, по ним строится
  индекс сжатого чанка.
- `orderby = 'ts DESC'`: диапазоны по времени и `ORDER BY ts DESC LIMIT n` (`Meta.ordering = ("-ts",)`).
- Вместе они покрывают все колонки PK `(ts, key, entity_id)`, это требование TimescaleDB для
  уникальных ограничений на сжатых данных (`ON CONFLICT` из mq-async продолжит работать).

**2. Выбрать чанк:** старше 14 дней и типичный по размеру. Имена чанков на каждом окружении свои.
Ниже в примерах — `grms`, `_hyper_1_599_chunk` (2026-09-03, ~58 MB heap + ~106 MB индексов). На `cloud`
выбрать аналогичный, не самый большой (24 мая).

```sql
SELECT chunk_schema || '.' || chunk_name AS chunk, range_start::date
FROM timescaledb_information.chunks
WHERE hypertable_name = 'shuttle_ts_kv' AND range_start::date = '2026-09-03';
```

**3. Запросы «до».** `EXPLAIN (ANALYZE, BUFFERS)` 3–4 типовых запросов на этот день: история одного ключа
устройства, tag logs устройства, gateway logs, среднее по тенанту для одного ключа. Это только `SELECT`.
Сохранить время.

**4. Сжать:**

```sql
SELECT compress_chunk('_timescaledb_internal._hyper_1_599_chunk');

SELECT chunk_name,
       pg_size_pretty(before_compression_total_bytes) AS before,
       pg_size_pretty(after_compression_total_bytes)  AS after
FROM chunk_compression_stats('shuttle_ts_kv')
WHERE compression_status = 'Compressed';
```

`before` включает старый bloat. Для честного коэффициента сравнивать `after` с живыми данными
(`approx_tuple_len` из `pgstattuple_approx` этого чанка) плюс индексы по ~140 байт на строку.

**5. Запросы «после».** Те же `EXPLAIN (ANALYZE, BUFFERS)`. В плане должен быть `DecompressChunk`
с фильтром по `entity_id`/`key`. Время сопоставимо или лучше.

**6. Проверить запись в сжатый чанк** (имитация опоздавшего показания, в транзакции с откатом):

```sql
BEGIN;
INSERT INTO shuttle_ts_kv (ts, entity_id, key, long_v)
SELECT ts, entity_id, key, long_v FROM shuttle_ts_kv
WHERE ts >= '2026-09-03' AND ts < '2026-09-04' LIMIT 1
ON CONFLICT DO NOTHING;   -- expect INSERT 0 0, no error
ROLLBACK;
```

**7. Замерить время.** `\timing` у `compress_chunk` даёт длительность сжатия одного чанка, по ней
выбирается `maxchunks_to_compress` (шаг 3).

**8. Только `cloud`: оценить объём логов.** Сжать также один свежий чанк старше 7 дней (в нём логи ещё
не удалены) и сравнить `after` с чанком без логов. На `grms` логов почти нет, пункт не нужен.

Если что-то не так:

```sql
SELECT decompress_chunk('_timescaledb_internal._hyper_1_599_chunk');
-- and, if compression is abandoned entirely (no compressed chunks left):
ALTER TABLE shuttle_ts_kv SET (timescaledb.compress = false);
```

---

## 7. Шаг 3. Миграция: compression и политика

Миграция создаётся в `stable` через `./manage.py makemigrations shuttle --empty -n tskv_compression`
(после `0028_alter_tskvlatest_entity_and_more`, в `dev` номер тот же) и заполняется
`migrations.RunSQL`. Требования:

- **Идемпотентно включать compression.** На проде он уже включён на шаге 2, повторный `ALTER` при
  наличии сжатых чанков может упасть. На других окружениях `ALTER` выполнится впервые.
- **Политика с ограничением чанков за запуск** (`maxchunks_to_compress`): бэклог сжимается постепенно,
  на любом окружении.
- **Время запуска после бэкапа** (03:00 UTC, поправить по результату шага 0).

```sql
DO $$
BEGIN
    IF NOT (SELECT compression_enabled FROM timescaledb_information.hypertables
            WHERE hypertable_schema = 'public' AND hypertable_name = 'shuttle_ts_kv') THEN
        ALTER TABLE shuttle_ts_kv SET (
            timescaledb.compress,
            timescaledb.compress_segmentby = 'entity_id, key',
            timescaledb.compress_orderby   = 'ts DESC'
        );
    END IF;
END $$;

SELECT add_compression_policy(
    'shuttle_ts_kv',
    compress_after    => INTERVAL '14 days',
    schedule_interval => INTERVAL '1 day',
    initial_start     => date_trunc('day', now()) + INTERVAL '1 day 3 hours',
    if_not_exists     => true
);

-- Compress at most N chunks per run so the backlog is processed gradually
SELECT alter_job(job_id, config => config || '{"maxchunks_to_compress": 10}')
FROM timescaledb_information.jobs
WHERE proc_name = 'policy_compression' AND hypertable_name = 'shuttle_ts_kv';
```

`reverse_sql`: `SELECT remove_compression_policy('shuttle_ts_kv', if_exists => true);`. Отключение
compression в обратную миграцию не включать: при наличии сжатых чанков оно упадёт (откат — раздел 11).

Окно в 14 дней: опоздавшие данные и `temp_change` пишут в несжатые чанки.

Перед деплоем на каждом окружении: шаг 0 (бэкап, место, длительность `pg_dump`). Миграцию прогнать
локально и в CI (TimescaleDB 2.21): политика создаётся, `alter_job` применяется.

Проверка после деплоя:

```sql
SELECT job_id, schedule_interval, next_start, config
FROM timescaledb_information.jobs WHERE proc_name = 'policy_compression';
```

---

## 8. Шаг 4. Сжатие бэклога

Политика каждую ночь сжимает до `maxchunks_to_compress` чанков старше 14 дней, каждый в своей
транзакции. Сколько это займёт:

- `grms`: ~640 чанков, все до ~60 MB heap + ~110 MB индексов. При 10 за ночь — ~2 месяца, поэтому
  лимит стоит поднять до 30–50, если пилот покажет сжатие чанка за секунды–десятки секунд.
- `cloud`: ~370 чанков, есть большие (до 2,8 GB heap в мае). При 10 за ночь — ~5 недель.

Самые старые чанки обычно маленькие и сжимаются быстро.

Каждое утро проверять:

```sql
-- Last run
SELECT job_id, last_run_status, last_run_started_at, last_run_duration, total_failures, next_start
FROM timescaledb_information.job_stats WHERE hypertable_name = 'shuttle_ts_kv';

-- Progress
SELECT compression_status, count(*) FROM chunk_compression_stats('shuttle_ts_kv') GROUP BY 1;
SELECT pg_size_pretty(pg_database_size(current_database()));
```

И в Grafana: время ответа API и WebSocket, нагрузка CPU и IO БД в окне запуска, задержки mq-async.

Если несколько ночей прошли чисто и запуск укладывается в окно до утра, поднять лимит:

```sql
SELECT alter_job(job_id, config => config || '{"maxchunks_to_compress": 30}')
FROM timescaledb_information.jobs
WHERE proc_name = 'policy_compression' AND hypertable_name = 'shuttle_ts_kv';
```

Когда бэклог сжат (`Uncompressed` остались только чанки моложе 14 дней), лимит можно оставить: в
обычном режиме политика сжимает один чанк в сутки.

Ускорить вручную (по желанию, ночью, в сессии из раздела 3; по одному чанку на транзакцию):

```sql
SELECT format('SELECT compress_chunk(%L);', format('%I.%I', chunk_schema, chunk_name))
FROM timescaledb_information.chunks
WHERE hypertable_name = 'shuttle_ts_kv' AND NOT is_compressed
  AND range_end < now() - INTERVAL '14 days'
ORDER BY range_start
LIMIT 10
\gexec
```

---

## 9. Шаг 5. Retention

Срок хранения истории — решение бизнеса (отчёты, договоры с отелями, аудит). Он действует и на
телеметрию, и на логи. Если в логах есть персональные данные гостей, срок нужно согласовать и с этим.

Сначала посмотреть, что будет удалено (пример — 2 года):

```sql
SELECT show_chunks('shuttle_ts_kv', older_than => INTERVAL '730 days');
```

Затем миграцией:

```sql
SELECT add_retention_policy('shuttle_ts_kv', INTERVAL '730 days', if_not_exists => true);
```

`drop_chunks` удаляет и сжатые чанки. **Необратимо**: удалённые данные есть только в бэкапах.

---

## 10. Мониторинг

```sql
-- Overall effect
SELECT pg_size_pretty(pg_database_size(current_database()));
SELECT * FROM hypertable_detailed_size('shuttle_ts_kv');
SELECT pg_size_pretty(before_compression_total_bytes) AS before,
       pg_size_pretty(after_compression_total_bytes)  AS after
FROM hypertable_compression_stats('shuttle_ts_kv');

-- Policy health
SELECT job_id, last_run_status, last_successful_finish, total_failures, next_start
FROM timescaledb_information.job_stats WHERE hypertable_name = 'shuttle_ts_kv';

-- Uncompressed chunks older than 15 days (after the backlog is done: should be 0)
SELECT count(*) FROM timescaledb_information.chunks
WHERE hypertable_name = 'shuttle_ts_kv' AND NOT is_compressed AND range_end < now() - INTERVAL '15 days';

-- Log volume for yesterday (watch for growth)
SELECT count(*), pg_size_pretty(sum(pg_column_size(t.*)))
FROM shuttle_ts_kv t JOIN shuttle_ts_kv_dictionary d ON d.key_id = t.key
WHERE d.key LIKE '%\_LOGS' AND t.ts >= date_trunc('day', now()) - INTERVAL '1 day'
  AND t.ts < date_trunc('day', now());
```

Ошибки фоновых задач TimescaleDB пишутся в лог Postgres (`make logs s=postgres`, Loki). Добавить алерт
на `total_failures > 0` и на рост `pg_database_size`.

---

## 11. Откат

| Что откатить | Как | Условия |
|---|---|---|
| Приостановить сжатие | `SELECT alter_job(<job_id>, scheduled => false);` | мгновенно |
| Удалить политику | `SELECT remove_compression_policy('shuttle_ts_kv');` | мгновенно |
| Распаковать чанк | `SELECT decompress_chunk('<chunk>');` | по одному, ночью; места ≈ несжатый размер чанка без bloat |
| Отключить compression | распаковать **все** чанки, затем `ALTER TABLE shuttle_ts_kv SET (timescaledb.compress = false);` | до ~45 GB свободного места |
| Retention | `SELECT remove_retention_policy('shuttle_ts_kv');` | удалённые чанки не вернуть |
| Задачи шага 1 | вернуть код | только переписав их на узкое окно, иначе снова таймауты и bloat |

---

## 12. Ограничения после включения

- **Изменения в сжатых данных.** `INSERT`/`UPDATE`/`DELETE` в сжатый чанк работают (включая
  `bulk_create(ignore_conflicts=True)` → `ON CONFLICT DO NOTHING`), но затронутые пачки распаковываются.
  Единичные опоздавшие показания допустимы, массовые изменения старых данных — нет. Одна транзакция не
  может распаковать больше `timescaledb.max_tuples_decompressed_per_dml_transaction` строк (по умолчанию
  100 000), иначе ошибка. Новый код, удаляющий или правящий историю (в том числе «почистить логи»),
  писать с этим расчётом.
- **Изменение схемы.** Добавить nullable-колонку можно. Сменить тип колонки (как в
  `0026_alter_tskv_str_v_to_textfield.py`), удалить колонку или поменять `segmentby` нельзя, пока есть
  сжатые чанки: сначала распаковать, потом мигрировать.
- **Индексы.** Индексы hypertable (`pkey`, `entity_id_ts_idx`, `key_ts_idx`, `ts_idx`) действуют только на
  несжатые чанки. После сжатия вопрос об удалении `ts_idx`/`key_ts_idx` касается только последних 14 дней.
  Решать по данным `pg_stat_statements`.
- **Запросы по старым данным без `entity_id`/`key`.** Фильтр только по времени на сжатых днях распаковывает
  все пачки в диапазоне. Кто сейчас активно использует `ts_idx` (726 тыс. сканов за 18 дней), неизвестно:
  при деградации смотреть медленные запросы в логе Postgres.
- **Бэкап и восстановление.** `pg_dump` сжатой hypertable работает. Восстановление — только с
  `timescaledb_pre_restore()` / `timescaledb_post_restore()` и в ту же версию TimescaleDB.
- **Тесты.** CI использует TimescaleDB 2.21, политика из миграции создаётся и в тестовой БД. Фоновые
  воркеры там данные не сжимают: чанки свежие.
- **Расширение `pgstattuple`** было создано на проде во время анализа. Оно ничего не меняет, при желании:
  `DROP EXTENSION pgstattuple;`.
