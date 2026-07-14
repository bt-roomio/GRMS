# Стек мониторинга GRMS

Observability-стек на базе Prometheus + Grafana с алертами в Telegram.

## Сервисы

| Сервис            | Образ                            | Порт | Описание                                   |
| ----------------- | -------------------------------- | ---- | ------------------------------------------ |
| **prometheus**    | `prom/prometheus:v2.53.0`        | 9090 | Сбор и хранение метрик (retention 30 дней) |
| **grafana**       | `grafana/grafana:11.1.0`         | 3000 | Дашборды и визуализация                    |
| **alertmanager**  | `prom/alertmanager:v0.27.0`      | 9093 | Маршрутизация алертов → Telegram           |
| **node-exporter** | `prom/node-exporter:v1.8.2`      | 9100 | Системные метрики хоста                    |
| **blackbox**      | `prom/blackbox-exporter:v0.25.0` | 9115 | HTTP/HTTPS проверки доступности            |

Все сервисы работают в общей сети `roomio_net` (внешняя, создаётся основным `docker-compose.yml`).

## Быстрый старт

```bash
# Из директории deploy/monitoring/

# 1. Создать .env и targets/blackbox-https.yml из примеров
make init
# Заполнить значения в .env (см. раздел «Переменные окружения»)
# Добавить свои домены в targets/blackbox-https.yml

# 2. Запустить стек
make up
```

## Переменные окружения (`.env`)

| Переменная               | Описание                                  |
| ------------------------ | ----------------------------------------- |
| `GRAFANA_VIRTUAL_HOST`   | Домен Grafana (`grafana.domain.com`)      |
| `GRAFANA_ADMIN_PASSWORD` | Пароль администратора Grafana             |
| `TELEGRAM_BOT_TOKEN`     | Токен Telegram-бота для алертов           |
| `TELEGRAM_CHAT_ID`       | ID чата/канала для получения алертов      |
| `LETSENCRYPT_EMAIL`      | Email для Let's Encrypt (SSL-сертификаты) |

> `.env` **не коммитить** в git.

## Источники метрик (scrape)

| Job              | Цель                                     | Интервал |
| ---------------- | ---------------------------------------- | -------- |
| `prometheus`     | `prometheus:9090`                        | 30 с     |
| `node-exporter`  | `node-exporter:9100`                     | 30 с     |
| `django`         | `django:8000`                            | 30 с     |
| `rabbitmq`       | `rabbitmq:15692`                         | 30 с     |
| `blackbox-login` | `django:8000/api/v1/users/access-token/` | 60 с     |
| `blackbox-https` | из `targets/blackbox-https.yml`          | 30 с     |

Django-метрики фильтруются через `metric_relabel_configs` — сохраняются только `offline_gateway_*`, `django_*`, `python_*`, `mq_*`, `up`.

## Алерты

Правила находятся в `rules/`. Все алерты доставляются в Telegram через Alertmanager.

| Файл                | Алерт                         | Условие                                             |
| ------------------- | ----------------------------- | --------------------------------------------------- |
| `backend.yml`       | `TenantGatewaysOffline`       | `offline_gateway_devices_total > 0` в течение 2 мин |
| `node-exporter.yml` | `HostHighCpuLoad`             | CPU > 80% в течение 10 мин                          |
|                     | `HostOutOfMemory`             | Свободная память < 10% в течение 5 мин              |
|                     | `HostOutOfDiskSpace`          | Свободное место на диске < 10% в течение 5 мин      |
|                     | `HostDiskWillFillIn24Hours`   | Диск заполнится за 24 ч (по тренду за 6 ч)          |
| `services.yml`      | `ServiceDown`                 | `up == 0` в течение 2 мин                           |
| `login.yml`         | `LoginEndpointDown`           | POST /api/v1/users/access-token/ падает 2 мин       |
| `rabbitmq.yml`      | `RabbitmqQueueBacklog`        | Очередь > 1000 готовых сообщений за 5 мин           |
|                     | `RabbitmqHighUnackedMessages` | > 1000 неподтверждённых сообщений за 5 мин          |
| `ssl_expiry.yml`    | `TLSCertExpiringSoon`         | SSL-сертификат истекает менее чем через 30 дней     |

## Структура файлов

```
monitoring/
├── docker-compose.yml          # Определение сервисов
├── prometheus.yml              # Конфигурация Prometheus (scrape + alerting)
├── env.example                # Шаблон переменных окружения
│
├── rules/                      # Правила алертов Prometheus
│   ├── backend.yml             # Алерты по IoT-устройствам (gateway offline)
│   ├── node-exporter.yml       # Системные алерты (CPU, RAM, диск)
│   ├── services.yml            # Доступность сервисов (up/down)
│   ├── login.yml               # Проверка эндпоинта авторизации
│   ├── rabbitmq.yml            # Алерты очередей RabbitMQ
│   └── ssl_expiry.yml          # Истечение SSL-сертификатов
│
├── targets/
│   ├── blackbox-https.example.yml  # Шаблон списка HTTPS-доменов
│   └── blackbox-https.yml          # Рабочий список доменов (gitignored)
│
├── alertmanager/
│   └── alertmanager.yml        # Маршрутизация и шаблон Telegram-сообщений
│
├── blackbox/
│   └── blackbox.yml            # Модули проверок (https_2xx, https_relaxed, login_post)
│
└── grafana/
    ├── dashboards/             # JSON-дашборды (django, node_exporter, rabbitmq)
    └── provisioning/           # Автоматическая провизия datasources и дашбордов
```

## Добавление HTTPS-доменов для мониторинга

Файл `targets/blackbox-https.yml` gitignored. Prometheus перечитывает его каждые **5 минут** без рестарта.

```yaml
# targets/blackbox-https.yml
- targets:
    - https://api.your-domain.com
    - https://your-domain.com
```

## Перезагрузка конфигурации Prometheus без рестарта

```bash
make reload
# или напрямую:
# curl -X POST http://localhost:9090/-/reload
```

## Grafana

Grafana доступна по адресу `https://$GRAFANA_VIRTUAL_HOST`. Дашборды и datasource провизируются автоматически из `grafana/provisioning/` при старте.

Встроенные дашборды: **Django**, **Node Exporter**, **RabbitMQ**.
