# roomio GRMS — Active-Passive Georedundancy Documentation

> **Last updated:** 2026-07-03
> **Cluster:** roomio-db
> **Stack:** PostgreSQL 16 + TimescaleDB 2.28.1, Patroni 4.1.3, etcd 3.4.30, HAProxy, Docker Compose

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Server Inventory](#2-server-inventory)
3. [WireGuard VPN](#3-wireguard-vpn)
4. [etcd Cluster](#4-etcd-cluster)
5. [Patroni — PostgreSQL HA](#5-patroni--postgresql-ha)
6. [HAProxy — Database Routing](#6-haproxy--database-routing)
7. [pgbouncer — Connection Pooling](#7-pgbouncer--connection-pooling)
8. [Application Stack (Docker Compose)](#8-application-stack-docker-compose)
9. [roomio-watchdog](#9-roomio-watchdog)
10. [Cloudflare DNS Failover](#10-cloudflare-dns-failover)
11. [Failover Scenarios](#11-failover-scenarios)
12. [Recovery Procedures](#12-recovery-procedures)
13. [Monitoring & Health Checks](#13-monitoring--health-checks)
14. [Backup & Restore](#14-backup--restore)
15. [Emergency Runbook](#15-emergency-runbook)

---

## 1. Architecture Overview

roomio uses an **Active-Passive** georedundancy setup across two Contabo VPS servers located in different datacenters. The design philosophy:

- **PostgreSQL HA is fully automatic** — Patroni + etcd handle failover in ~15–30 seconds with no human intervention
- **Application stack activation is automatic** — roomio-watchdog detects Patroni leadership change and starts/stops Docker accordingly
- **DNS switching is automatic** — Cloudflare API updates A records when the active node changes
- **Split-brain protection** — etcd is the single source of truth; if etcd is unreachable, neither node activates

### High-Level Topology

```
                         server.com
                       Cloudflare DNS (TTL=60)
                              │
              ┌───────────────┴───────────────┐
              │                               │
    api.server.com                  (failover target)
    111.222.333.444 (eric)               555.666.777.888 (amigo)
              │                               │
┌─────────────▼──────────────┐  ┌────────────▼────────────────┐
│          ERIC               │  │          AMIGO               │
│    vmiXXXXXXX [ACTIVE]      │  │    vmiYYYYYYY [PASSIVE]      │
│                             │  │                              │
│  ┌─────────────────────┐    │  │  ┌──────────────────────┐   │
│  │   Docker Compose    │    │  │  │  Docker (STOPPED)    │   │
│  │  Django / Celery    │    │  │  │  (ready to start)    │   │
│  │  Redis / RabbitMQ   │    │  │  └──────────────────────┘   │
│  │  MQTT / Nginx       │    │  │                              │
│  │  pgbouncer          │    │  │  ┌──────────────────────┐   │
│  └──────────┬──────────┘    │  │  │  HAProxy             │   │
│             │               │  │  │  :5000 write         │   │
│  ┌──────────▼──────────┐    │  │  │  :5001 read          │   │
│  │  HAProxy            │    │  │  └──────────┬───────────┘   │
│  │  :5000 write        │    │  │             │               │
│  │  :5001 read         │    │  │  ┌──────────▼───────────┐   │
│  └──────────┬──────────┘    │  │  │  Patroni node2       │   │
│             │               │  │  │  PostgreSQL REPLICA   │   │
│  ┌──────────▼──────────┐    │  │  │  TimescaleDB 2.28.1  │   │
│  │  Patroni node1      │    │  │  └──────────────────────┘   │
│  │  PostgreSQL PRIMARY  │    │  │                              │
│  │  TimescaleDB 2.28.1 │    │  │  ┌──────────────────────┐   │
│  └──────────┬──────────┘    │  │  │  etcd node2          │   │
│             │               │  │  │  :2379/:2380          │   │
│  ┌──────────▼──────────┐    │  │  └──────────────────────┘   │
│  │  etcd node1         │    │  │                              │
│  │  :2379/:2380        │    │  │  ┌──────────────────────┐   │
│  └─────────────────────┘    │  │  │  roomio-watchdog     │   │
│                             │  │  │  (monitoring eric)   │   │
│  ┌─────────────────────┐    │  │  └──────────────────────┘   │
│  │  roomio-watchdog    │    │  │                              │
│  │  (monitoring amigo) │    │  │  ┌──────────────────────┐   │
│  └─────────────────────┘    │  │  │  WireGuard wg0       │   │
│                             │  │  │  10.0.0.2/30         │   │
│  ┌─────────────────────┐    │  │  └──────────────────────┘   │
│  │  WireGuard wg0      │    │  └──────────────────────────────┘
│  │  10.0.0.1/30        │◄───────────────────────────────────►│
│  └─────────────────────┘    │     WireGuard tunnel (UDP 51820)
└─────────────────────────────┘     WAL replication (TCP 5432)
                                    etcd Raft (TCP 2380)
                                    Patroni REST (TCP 8008)
```

### Request Flow (Normal State)

```
Client → Cloudflare → eric:443 (nginx-proxy)
       → Django (backend container)
       → pgbouncer → HAProxy:5000
       → Patroni health check (/master)
       → PostgreSQL PRIMARY on eric:5432
```

### Failover Flow

```
eric DOWN detected by Patroni (etcd TTL expires ~15 sec)
       ↓
amigo Patroni acquires etcd lock → promotes to PRIMARY
       ↓
roomio-watchdog on amigo detects leader=node2 via /cluster API
       ↓
activate_self(): Docker up → DNS switch via Cloudflare API
       ↓
Client → Cloudflare → amigo:443 (new DNS, TTL=60 sec)
```

---

## 2. Server Inventory

| Parameter         | eric (Active)               | amigo (Passive)             |
| ----------------- | --------------------------- | --------------------------- |
| VPS ID            | vmiXXXXXXX                  | vmiYYYYYYY                  |
| Public IP         | 111.222.333.444             | 555.666.777.888             |
| WireGuard IP      | 10.0.0.1                    | 10.0.0.2                    |
| Patroni node name | node1                       | node2                       |
| Normal DB role    | Leader (PRIMARY)            | Replica (STREAMING)         |
| Normal app role   | ACTIVE (Docker up)          | PASSIVE (Docker down)       |
| OS                | Debian/Ubuntu               | Debian/Ubuntu               |
| PostgreSQL        | 16 + TimescaleDB 2.28.1     | 16 + TimescaleDB 2.28.1     |
| data_dir          | /var/lib/postgresql/16/main | /var/lib/postgresql/16/main |
| config_dir        | /etc/postgresql/16/main     | /etc/postgresql/16/main     |

---

## 3. WireGuard VPN

WireGuard provides the encrypted private channel between eric and amigo. **All HA-sensitive traffic flows through this tunnel** — etcd Raft consensus, Patroni REST API, PostgreSQL WAL streaming replication. Without WireGuard the cluster cannot function.

### Configuration

**Config path:** `/etc/wireguard/wg0.conf`
**Service:** `wg-quick@wg0` (systemd)

**On eric (`/etc/wireguard/wg0.conf`):**

```ini
[Interface]
Address = 10.0.0.1/30
ListenPort = 51820
PrivateKey = <ERIC_PRIVATE_KEY>

[Peer]
PublicKey = <AMIGO_PUBLIC_KEY>
AllowedIPs = 10.0.0.2/32
Endpoint = 555.666.777.888:51820
PersistentKeepalive = 25
```

**On amigo (`/etc/wireguard/wg0.conf`):**

```ini
[Interface]
Address = 10.0.0.2/30
ListenPort = 51820
PrivateKey = <AMIGO_PRIVATE_KEY>

[Peer]
PublicKey = <ERIC_PUBLIC_KEY>
AllowedIPs = 10.0.0.1/32
Endpoint = 111.222.333.444:51820
PersistentKeepalive = 25
```

### Management Commands

```bash
# Status
sudo wg show

# Restart tunnel
sudo systemctl restart wg-quick@wg0

# Check connectivity
ping -c 4 10.0.0.2   # from eric
ping -c 4 10.0.0.1   # from amigo

# Check traffic
sudo wg show wg0      # shows transfer stats, last handshake
```

### Required Firewall Rules

```bash
# Port 51820 must be open on public interface (both servers)
sudo ufw allow 51820/udp

# OR with iptables
sudo iptables -I INPUT -p udp --dport 51820 -j ACCEPT
```

> **Important:** If the WireGuard handshake is older than 3 minutes, the tunnel may be degraded. `PersistentKeepalive = 25` prevents this by sending keepalive packets every 25 seconds.

---

## 4. etcd Cluster

etcd is the distributed key-value store used by Patroni as its DCS (Distributed Configuration Store). It stores the leader lock, cluster configuration, and member state. Patroni cannot function without etcd.

### Architecture Note

With only 2 etcd nodes, the cluster requires **both nodes** to be available for writes (no quorum without majority). This means:

- If one node goes down → etcd cluster becomes **read-only**
- Patroni can still read current state but **cannot write** (cannot change leader)
- The existing PostgreSQL primary continues serving traffic
- New failover elections are blocked until etcd recovers

This is an accepted limitation for the current scale. The alternative (3rd etcd node) would require an additional VPS.

### Installation

```bash
ETCD_VER=v3.5.17
curl -L https://github.com/etcd-io/etcd/releases/download/${ETCD_VER}/etcd-${ETCD_VER}-linux-amd64.tar.gz \
  | tar xz -C /usr/local/bin --strip-components=1 \
    etcd-${ETCD_VER}-linux-amd64/etcd \
    etcd-${ETCD_VER}-linux-amd64/etcdctl
```

### Systemd Service

**On eric (`/etc/systemd/system/etcd.service`):**

```ini
[Unit]
Description=etcd
After=network.target

[Service]
Type=notify
ExecStart=/usr/local/bin/etcd \
  --name node1 \
  --data-dir /var/lib/etcd \
  --listen-peer-urls http://10.0.0.1:2380 \
  --listen-client-urls http://10.0.0.1:2379,http://127.0.0.1:2379 \
  --advertise-client-urls http://10.0.0.1:2379 \
  --initial-advertise-peer-urls http://10.0.0.1:2380 \
  --initial-cluster node1=http://10.0.0.1:2380,node2=http://10.0.0.2:2380 \
  --initial-cluster-token roomio-etcd-cluster \
  --initial-cluster-state new
Restart=always
RestartSec=5s

[Install]
WantedBy=multi-user.target
```

**On amigo** — same config, change:

- `--name node2`
- `--listen-peer-urls http://10.0.0.2:2380`
- `--listen-client-urls http://10.0.0.2:2379,http://127.0.0.1:2379`
- `--advertise-client-urls http://10.0.0.2:2379`
- `--initial-advertise-peer-urls http://10.0.0.2:2380`

### Health Checks

```bash
# Cluster status table
etcdctl --endpoints=http://10.0.0.1:2379,http://10.0.0.2:2379 endpoint status -w table

# Expected output:
# +----------------------+------------------+---------+---------+-----------+
# |       ENDPOINT       |        ID        | VERSION | DB SIZE | IS LEADER |
# +----------------------+------------------+---------+---------+-----------+
# | http://10.0.0.1:2379 | aaaaaaaaaaaaaaaa |  3.4.30 |   20 kB |      true |
# | http://10.0.0.2:2379 | bbbbbbbbbbbbbbbb |  3.4.30 |   20 kB |     false |
# +----------------------+------------------+---------+---------+-----------+

# Health check
etcdctl --endpoints=http://10.0.0.1:2379,http://10.0.0.2:2379 endpoint health

# List all Patroni keys in etcd
etcdctl --endpoints=http://10.0.0.1:2379 get /db/roomio-db --prefix --keys-only
```

### Required Firewall Ports

```bash
# Between servers (WireGuard interface)
sudo ufw allow from 10.0.0.0/30 to any port 2379
sudo ufw allow from 10.0.0.0/30 to any port 2380
```

---

## 5. Patroni — PostgreSQL HA

Patroni manages the entire PostgreSQL lifecycle: initialization, configuration, replication setup, health monitoring, and automatic failover. It uses etcd as the consensus backend.

### How Patroni Failover Works

1. Each Patroni node holds a TTL-based lease in etcd (TTL = 30 seconds)
2. The Primary node continuously renews this lease (every `loop_wait` = 10 seconds)
3. If the Primary fails to renew → lease expires after TTL (30 sec)
4. Replica nodes race to acquire the lock
5. Winner promotes itself to PRIMARY via `pg_ctl promote`
6. `pg_rewind` is used to reconcile diverged timelines if needed

### Installation

```bash
sudo pip3 install patroni[etcd3] psycopg2-binary --break-system-packages
```

### Configuration

**Config path:** `/etc/patroni/patroni.yml`

**On eric:**

```yaml
scope: roomio-db
namespace: /db/
name: node1

restapi:
  listen: 10.0.0.1:8008
  connect_address: 10.0.0.1:8008

etcd3:
  hosts:
    - 10.0.0.1:2379
    - 10.0.0.2:2379

bootstrap:
  dcs:
    ttl: 30
    loop_wait: 10
    retry_timeout: 10
    maximum_lag_on_failover: 10485760 # 10 MB max WAL lag for failover candidate
    postgresql:
      use_pg_rewind: true
      use_slots: true
      parameters:
        shared_preload_libraries: timescaledb
        wal_level: replica
        max_wal_senders: 10
        max_replication_slots: 5
        max_worker_processes: 23
        max_locks_per_transaction: 128
        wal_keep_size: 512MB
        hot_standby: on
        wal_log_hints: on
        timescaledb.telemetry_level: "off"

postgresql:
  listen: 10.0.0.1:5432
  connect_address: 10.0.0.1:5432
  data_dir: /var/lib/postgresql/16/main
  bin_dir: /usr/lib/postgresql/16/bin
  config_dir: /etc/postgresql/16/main
  pgpass: /tmp/pgpass0
  authentication:
    replication:
      username: replicator
      password: "STRONG_REPL_PASSWORD"
    superuser:
      username: postgres
      password: "POSTGRES_PASSWORD"
  parameters:
    shared_preload_libraries: timescaledb

tags:
  nofailover: false
  noloadbalance: false
  clonefrom: false
  nosync: false
```

**On amigo** — change:

- `name: node2`
- `restapi.listen: 10.0.0.2:8008`
- `restapi.connect_address: 10.0.0.2:8008`
- `postgresql.listen: 10.0.0.2:5432`
- `postgresql.connect_address: 10.0.0.2:5432`

> **Debian note:** On Debian/Ubuntu, `postgresql.conf` lives in `/etc/postgresql/16/main/`, not in `data_dir`. The `config_dir` parameter is mandatory — without it Patroni tries to rename `postgresql.conf` inside `data_dir` and fails with `FileNotFoundError`.

### Systemd Service

**`/etc/systemd/system/patroni.service` (both servers):**

```ini
[Unit]
Description=Patroni PostgreSQL HA
After=network.target etcd.service
Wants=etcd.service

[Service]
User=postgres
Group=postgres
ExecStart=/usr/local/bin/patroni /etc/patroni/patroni.yml
ExecReload=/bin/kill -s HUP $MAINPID
Restart=always
RestartSec=5s
KillMode=process
TimeoutStopSec=30

[Install]
WantedBy=multi-user.target
```

### Cluster Management Commands

```bash
# Current cluster state
patronictl -c /etc/patroni/patroni.yml list

# Expected output (normal state):
# + Cluster: roomio-db ----+----+-----------+----+-----------+
# | Member | Host      | Role    | State     | TL | Lag in MB |
# +--------+-----------+---------+-----------+----+-----------+
# | node1  | 10.0.0.1  | Leader  | running   | 17 |           |
# | node2  | 10.0.0.2  | Replica | streaming | 17 |         0 |
# +--------+-----------+---------+-----------+----+-----------+

# Show DCS configuration
patronictl -c /etc/patroni/patroni.yml show-config

# Edit DCS configuration
patronictl -c /etc/patroni/patroni.yml edit-config

# Reload config (no restart)
patronictl -c /etc/patroni/patroni.yml reload roomio-db --force

# Rolling restart (replica first, then leader — minimal downtime)
patronictl -c /etc/patroni/patroni.yml restart roomio-db --force

# Planned switchover (graceful — waits for replica to sync)
patronictl -c /etc/patroni/patroni.yml switchover roomio-db \
  --master node1 --candidate node2 --force

# Emergency failover (immediate — possible data loss if replica lagged)
patronictl -c /etc/patroni/patroni.yml failover roomio-db \
  --master node1 --candidate node2 --force

# Reinitialize a diverged replica
patronictl -c /etc/patroni/patroni.yml reinit roomio-db node1 --force

# Failover history (shows timeline changes)
patronictl -c /etc/patroni/patroni.yml history

# Pause automatic failover (maintenance mode)
patronictl -c /etc/patroni/patroni.yml pause roomio-db

# Resume automatic failover
patronictl -c /etc/patroni/patroni.yml resume roomio-db
```

### Patroni REST API Endpoints

Patroni exposes a REST API on `${SELF_WG_IP}:8008`. HAProxy uses these for health checks.

```bash
# Full cluster info (used by roomio-watchdog)
curl -s http://10.0.0.1:8008/cluster | python3 -m json.tool

# Node health — 200 on any live node
curl -sv http://10.0.0.1:8008/health

# Primary check — 200 only on current PRIMARY
curl -sv http://10.0.0.1:8008/master

# Replica check — 200 only on REPLICA
curl -sv http://10.0.0.2:8008/replica

# Full node status JSON
curl -s http://10.0.0.1:8008/patroni | python3 -m json.tool
```

### pg_hba.conf — Required Entries

Both servers must have these entries in `/etc/postgresql/16/main/pg_hba.conf`:

```
# Patroni replication via WireGuard
host    replication     replicator      10.0.0.0/30     scram-sha-256
host    all             all             10.0.0.0/30     scram-sha-256
```

---

## 6. HAProxy — Database Routing

HAProxy runs on **both servers** and routes database connections using Patroni REST API health checks. pgbouncer always connects to HAProxy — this makes database failover completely transparent to the application.

### Configuration

**`/etc/haproxy/haproxy.cfg` (both servers, identical):**

```haproxy
global
    maxconn 200

defaults
    mode tcp
    retries 3
    timeout connect 5s
    timeout client 30s
    timeout server 30s
    timeout check 5s

# Stats dashboard
listen stats
    bind *:7000
    mode http
    stats enable
    stats uri /
    stats refresh 5s

# WRITE port — routes to current PRIMARY only
# HAProxy checks Patroni /master endpoint (HTTP 200 = is primary)
frontend pg_write
    bind *:5000
    default_backend pg_primary

backend pg_primary
    option httpchk GET /master
    http-check expect status 200
    server node1 10.0.0.1:5432 check port 8008 inter 3s fall 2 rise 2
    server node2 10.0.0.2:5432 check port 8008 inter 3s fall 2 rise 2

# READ port — routes to REPLICA, falls back to PRIMARY if replica is down
frontend pg_read
    bind *:5001
    default_backend pg_replica

backend pg_replica
    option httpchk GET /replica
    http-check expect status 200
    server node2 10.0.0.2:5432 check port 8008 inter 3s fall 2 rise 2
    server node1 10.0.0.1:5432 check port 8008 inter 3s fall 2 rise 2 backup
```

### Health Check Logic

- HAProxy checks each server's Patroni REST API every **3 seconds**
- `fall 2` — server marked DOWN after 2 consecutive failed checks (~6 sec)
- `rise 2` — server marked UP after 2 consecutive successful checks (~6 sec)
- After Patroni failover, HAProxy detects the new primary within **~6–12 seconds**

### Management Commands

```bash
# Verify HAProxy is listening
sudo ss -tlnp | grep haproxy
# Expected: 0.0.0.0:5000, 0.0.0.0:5001, 0.0.0.0:7000

# Test write route (should connect to current PRIMARY)
psql -h 127.0.0.1 -p 5000 -U postgres -d grms_db \
  -c "SELECT inet_server_addr(), pg_is_in_recovery();"
# pg_is_in_recovery = false → confirmed PRIMARY

# Test read route (should connect to REPLICA)
psql -h 127.0.0.1 -p 5001 -U postgres -d grms_db \
  -c "SELECT inet_server_addr(), pg_is_in_recovery();"
# pg_is_in_recovery = true → confirmed REPLICA

# Stats page
curl -s http://127.0.0.1:7000/
```

### Docker Network Access

Docker containers cannot reach HAProxy on `127.0.0.1` or `host-gateway` by default because `iptables INPUT policy = DROP`. The `roomio_net` bridge uses `172.19.0.0/16`.

```bash
# Allow Docker containers to reach HAProxy
sudo iptables -I INPUT -s 172.19.0.0/16 -p tcp --dport 5000 -j ACCEPT
sudo iptables -I INPUT -s 172.19.0.0/16 -p tcp --dport 5001 -j ACCEPT

# Persist rules across reboots
sudo apt install -y iptables-persistent
sudo netfilter-persistent save
```

---

## 7. pgbouncer — Connection Pooling

pgbouncer sits between the Django application and HAProxy. It maintains a pool of persistent PostgreSQL connections, reducing overhead from frequent connect/disconnect cycles.

### Configuration in docker-compose.yml

```yaml
pgbouncer:
  image: edoburu/pgbouncer:v1.25.1-p0
  environment:
    DB_HOST: host.docker.internal # resolves to roomio_net bridge gateway
    DB_PORT: 5000 # HAProxy write port (PRIMARY)
    DB_NAME: grms_db
    DB_USER: postgres
    DB_PASSWORD: ${POSTGRES_PASSWORD}
    POOL_MODE: transaction
    MAX_CLIENT_CONN: 1000
    DEFAULT_POOL_SIZE: 50
    MIN_POOL_SIZE: 10
    RESERVE_POOL_SIZE: 10
    SERVER_IDLE_TIMEOUT: 600
    AUTH_TYPE: scram-sha-256
  extra_hosts:
    - "host.docker.internal:host-gateway"
```

### Connection Chain

```
Django app
    ↓ connects to pgbouncer:5432 (inside Docker network)
pgbouncer
    ↓ connects to host.docker.internal:5000 (HAProxy on host)
HAProxy :5000
    ↓ checks Patroni /master, routes to
PostgreSQL PRIMARY :5432
```

> **Why transaction pool mode?** Django uses short-lived queries. Transaction mode allows pgbouncer to reuse connections across different clients, maximizing efficiency. Note: `mq-async` bypasses pgbouncer and connects directly to PostgreSQL (`postgres:5432`) because it uses long-lived async connections incompatible with transaction pool mode.

---

## 8. Application Stack (Docker Compose)

### Services Overview

| Service         | Image                    | Role                 | Notes                           |
| --------------- | ------------------------ | -------------------- | ------------------------------- |
| pgbouncer       | edoburu/pgbouncer        | DB connection pooler | Connects to HAProxy:5000        |
| redis           | redis:7-alpine           | Cache                | allkeys-lru, no persistence     |
| redis-broker    | redis:7-alpine           | Celery broker        | appendonly yes, noeviction      |
| rabbitmq        | rabbitmq:3.13-management | Message queue        | IoT/MQTT pipeline               |
| backend         | grms image               | Django/Daphne        | REST API + WebSocket            |
| celery-critical | grms image               | Task worker          | Queue: critical, concurrency=2  |
| celery-default  | grms image               | Task worker          | Queue: default, concurrency=4   |
| celery-low      | grms image               | Task worker          | Queue: low, concurrency=1       |
| celery-beat     | grms image               | Scheduler            | DatabaseScheduler               |
| mq-async        | grms image               | Async consumer       | 2 replicas, bypasses pgbouncer  |
| mews-websocket  | grms image               | Mews PMS WS          | Connects to api.mews.com        |
| pms-handler     | grms image               | PMS events           | Processes Mews events           |
| mqtt            | mqtt-broker image        | IoT bridge           | Connects to RabbitMQ            |
| frontend-nginx  | nginx:1.27-alpine        | SPA server           | Serves pre-built Vue.js dist    |
| proxy           | nginxproxy/nginx-proxy   | Reverse proxy        | HTTP/HTTPS routing              |
| letsencrypt     | acme-companion           | SSL certs            | Auto-renew via ACME             |
| ~~frontend~~    | grms_front               | Vue.js builder       | **NOT started during failover** |

### Activation Startup Order

During failover, services are started in two phases to respect health dependencies:

**Phase 1 — Infrastructure:**

```bash
docker compose up -d pgbouncer redis redis-broker rabbitmq
# Wait for pgbouncer healthy (pg_isready check, max 60 sec)
```

**Phase 2 — Application:**

```bash
docker compose up -d \
  backend \
  celery-critical celery-default celery-low celery-beat \
  mq-async mews-websocket pms-handler \
  mqtt \
  frontend-nginx \
  proxy letsencrypt
```

> **Why not `docker compose up -d` (all services)?** The `frontend` (vue-builder) service runs `yarn install && yarn build` which takes 5–15 minutes. During an emergency failover, this is unacceptable. The pre-built `frontend_dist` volume from the last deployment already contains the SPA — `frontend-nginx` serves it directly.

### Useful Docker Commands

```bash
# Status of all services
docker compose ps

# Follow logs for specific service
docker compose logs -f --tail=100 backend

# Restart single service
docker compose restart backend

# Check resource usage
docker stats --no-stream

# Start only infrastructure
make up-infra

# Start everything except frontend builder
make up-app

# Full start
make up-all
```

---

## 9. roomio-watchdog

### Purpose

roomio-watchdog is a **symmetric** bash script — the same file runs on both eric and amigo. It continuously monitors Patroni leadership state and automatically manages the Docker application stack and DNS to match who is the current PostgreSQL primary.

### Key Design Decisions

- **Single source of truth: Patroni /cluster endpoint** (not ping, not public IP, not WireGuard tunnel check). This prevents split-brain — if the network between servers breaks but eric is still up, amigo won't accidentally activate because it can verify leadership through its local etcd
- **Self-identifying by hostname** — the script checks `$(hostname)` to determine its node identity
- **Self-restoring** — when the failed node recovers and Patroni leadership returns to it, the previously-activated standby deactivates itself automatically without any manual intervention
- **etcd-safe** — if Patroni/etcd is unreachable, the script does nothing and sends a single Telegram alert

### Installation

```bash
# Copy script to both servers
sudo cp roomio-watchdog.sh /usr/local/bin/roomio-watchdog.sh
sudo chmod +x /usr/local/bin/roomio-watchdog.sh

# Create log file
sudo touch /var/log/roomio-watchdog.log
sudo chmod 644 /var/log/roomio-watchdog.log

# Fill in secrets
sudo sed -i 's|__CF_TOKEN__|your_cloudflare_token|g' /usr/local/bin/roomio-watchdog.sh
sudo sed -i 's|__CF_RECORD_MQTT__|mqtt_record_id|g' /usr/local/bin/roomio-watchdog.sh
sudo sed -i 's|__TELEGRAM_BOT_TOKEN__|your_bot_token|g' /usr/local/bin/roomio-watchdog.sh
sudo sed -i 's|__TELEGRAM_CHAT_ID__|your_chat_id|g' /usr/local/bin/roomio-watchdog.sh
```

### Systemd Service

**`/etc/systemd/system/roomio-watchdog.service` (both servers):**

```ini
[Unit]
Description=roomio Active-Passive Watchdog
After=network.target patroni.service etcd.service
Wants=patroni.service

[Service]
Type=simple
ExecStart=/usr/local/bin/roomio-watchdog.sh
Restart=always
RestartSec=10s
StandardOutput=append:/var/log/roomio-watchdog.log
StandardError=append:/var/log/roomio-watchdog.log

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now roomio-watchdog
```

### Configuration Variables

| Variable         | Value                          | Description                                     |
| ---------------- | ------------------------------ | ----------------------------------------------- |
| `CHECK_INTERVAL` | 30                             | Seconds between each Patroni leadership check   |
| `COMPOSE_DIR`    | `/home/$(whoami)/GRMS/deploy`  | Path to docker-compose project                  |
| `STATE_FILE`     | `/tmp/roomio_watchdog.state`   | Contains "ACTIVE" if this node activated Docker |
| `LOG_FILE`       | `/var/log/roomio-watchdog.log` | Watchdog activity log                           |
| `CF_ZONE_ID`     | `CF_ZONE_ID_PLACEHOLDER`       | Cloudflare zone for server.com                  |
| `SELF_WG_IP`     | `10.0.0.1` / `10.0.0.2`        | WireGuard IP (auto-detected by hostname)        |

### Decision Matrix

On every 30-second iteration:

| Patroni leader? | I am Leader | Docker running | Action                             |
| --------------- | ----------- | -------------- | ---------------------------------- |
| Unreachable     | —           | —              | Do nothing, send alert once        |
| node1           | ✅ yes      | ❌ no          | `activate_self()`                  |
| node1           | ✅ yes      | ✅ yes         | Nothing (normal active state)      |
| node2           | ❌ no       | ✅ yes         | `deactivate_self()` (self-restore) |
| node2           | ❌ no       | ❌ no          | Nothing (normal passive state)     |

### activate_self() Sequence

```
1. Telegram: "🚨 FAILOVER — nodeX became Patroni Leader"
2. cd $COMPOSE_DIR
3. docker compose up -d pgbouncer redis redis-broker rabbitmq
4. Wait for pgbouncer pg_isready (max 60 sec, check every 3 sec)
5. docker compose up -d backend celery-* mq-async mews-websocket pms-handler mqtt frontend-nginx proxy letsencrypt
6. switch_dns_to_self() → Cloudflare API updates A records
7. echo "ACTIVE" > $STATE_FILE
8. Telegram: "✅ nodeX ACTIVE — services up, DNS switched"
```

### deactivate_self() Sequence

```
1. Telegram: "♻️ nodeX restoring to passive — peer recovered"
2. cd $COMPOSE_DIR
3. docker compose down
4. rm $STATE_FILE
5. Telegram: "✅ nodeX PASSIVE — Docker stopped"
```

### Telegram Alerts Reference

| Emoji | Alert                | Meaning                                    |
| ----- | -------------------- | ------------------------------------------ |
| 👁     | watchdog запущен     | Service started on a node                  |
| 🚨    | FAILOVER             | Node became Leader, activation starting    |
| ✅    | ACTIVE               | Node fully activated, DNS switched         |
| ♻️    | restoring to passive | Peer recovered, self-deactivation started  |
| ✅    | PASSIVE              | Docker stopped, back to standby            |
| ⚠️    | WARNING              | Patroni/etcd unreachable — watchdog paused |

### Log File

```bash
# Follow live
tail -f /var/log/roomio-watchdog.log

# Sample log during failover:
# [2026-07-02 07:12:23] [node2] roomio symmetric watchdog started
# [2026-07-02 07:12:53] [node2] ACTIVATING node2 (became Patroni Leader)
# [2026-07-02 07:12:53] [node2] Starting infra services...
# [2026-07-02 07:13:08] [node2] Infra healthy ✓
# [2026-07-02 07:13:08] [node2] Starting app services...
# [2026-07-02 07:13:28] [node2] DNS api (proxied=true) -> 555.666.777.888: OK
# [2026-07-02 07:13:29] [node2] DNS server.com (proxied=true) -> 555.666.777.888: OK
# [2026-07-02 07:13:29] [node2] DNS mqtt (proxied=false) -> 555.666.777.888: OK
# [2026-07-02 07:13:29] [node2] ACTIVATION COMPLETE
```

---

## 10. Cloudflare DNS Failover

### Setup

Domain `server.com` uses Cloudflare nameservers:

- `ns1.cloudflare.com`
- `ns2.cloudflare.com`

All A records have **TTL = 60 seconds** (effectively ~30 seconds with Cloudflare proxy), enabling fast DNS propagation during failover.

### DNS Records

| Record                 | ID                                | Proxied  | Purpose           |
| ---------------------- | --------------------------------- | -------- | ----------------- |
| `api.server.com`       | `CF_RECORD_API_PLACEHOLDER`       | ✅ true  | Django REST API   |
| `server.com`           | `CF_RECORD_FRONT_PLACEHOLDER`     | ✅ true  | Frontend SPA      |
| `portainer.server.com` | `CF_RECORD_PORTAINER_PLACEHOLDER` | ✅ true  | Portainer UI      |
| `mqtt.server.com`      | `__CF_RECORD_MQTT__`              | ❌ false | MQTT broker (TCP) |

> **Why mqtt proxied=false?** Cloudflare proxy only supports HTTP/HTTPS. MQTT uses raw TCP on port 9000. If proxied=true, Cloudflare would try to proxy TCP which it cannot do on the free plan — clients would fail to connect.

### Cloudflare API

**Zone ID:** `CF_ZONE_ID_PLACEHOLDER`
**API token scope:** `Edit zone DNS` for `server.com`

#### Get record IDs

```bash
export CF_TOKEN="your_token"
export CF_ZONE_ID="CF_ZONE_ID_PLACEHOLDER"

curl -s "https://api.cloudflare.com/client/v4/zones/${CF_ZONE_ID}/dns_records?type=A" \
  -H "Authorization: Bearer ${CF_TOKEN}" | python3 -m json.tool | grep -E '"id"|"name"|"content"'
```

#### Manual switch to amigo

```bash
# Switch single record
curl -s -X PUT \
  "https://api.cloudflare.com/client/v4/zones/${CF_ZONE_ID}/dns_records/CF_RECORD_API_PLACEHOLDER" \
  -H "Authorization: Bearer ${CF_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"type":"A","name":"api","content":"555.666.777.888","ttl":60,"proxied":true}' \
  | python3 -m json.tool | grep -E '"success"|"content"'
```

#### Manual switch back to eric

```bash
curl -s -X PUT \
  "https://api.cloudflare.com/client/v4/zones/${CF_ZONE_ID}/dns_records/CF_RECORD_API_PLACEHOLDER" \
  -H "Authorization: Bearer ${CF_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"type":"A","name":"api","content":"111.222.333.444","ttl":60,"proxied":true}' \
  | python3 -m json.tool | grep -E '"success"|"content"'
```

#### Verify DNS propagation

```bash
dig api.server.com +short
# Should return 555.666.777.888 (amigo) or 111.222.333.444 (eric)

# Check from multiple locations
curl -s "https://dns.google/resolve?name=api.server.com&type=A" | python3 -m json.tool
```

---

## 11. Failover Scenarios

### Scenario 1 — Unplanned (eric crashes)

**What happens automatically:**

```
T+0 sec   eric server becomes unreachable
T+15 sec  Patroni TTL expires — amigo acquires etcd leader lock
T+15 sec  PostgreSQL on amigo promotes to PRIMARY (pg_ctl promote)
T+30 sec  roomio-watchdog on amigo: get_current_leader() returns "node2"
T+30 sec  activate_self() begins
T+35 sec  Docker infra services starting (pgbouncer, redis, redis-broker, rabbitmq)
T+50 sec  pgbouncer healthy — application services starting
T+70 sec  All services up — Cloudflare DNS switch via API
T+130 sec DNS propagated (TTL=60) — clients hitting amigo
```

**Estimated total downtime: 60–130 seconds**

**Telegram notifications:**

1. `🚨 FAILOVER — node2 became Leader` (at T+30)
2. `✅ node2 ACTIVE` (at T+70)

### Scenario 2 — Planned (maintenance on eric)

Use `patronictl switchover` for zero-data-loss planned maintenance:

```bash
# On any server
patronictl -c /etc/patroni/patroni.yml switchover roomio-db \
  --master node1 --candidate node2 --force

# Patroni waits for replica to fully sync before switching
# No data loss guaranteed
# Application downtime: ~5–10 seconds (HAProxy detects new primary)
```

After switchover:

- amigo watchdog detects `leader=node2` → `activate_self()`
- eric watchdog detects `leader≠node1` → `deactivate_self()`

### Scenario 3 — etcd cluster down

If both etcd nodes are unreachable:

- Patroni enters "pause-like" state — existing PostgreSQL primary continues serving
- No new failover elections possible
- roomio-watchdog sends `⚠️ WARNING` alert and does nothing
- **Recovery:** restore etcd on both nodes, Patroni resumes automatically

### Scenario 4 — WireGuard tunnel down (but both servers alive)

- etcd cluster becomes unreachable from each node's perspective
- Patroni on both nodes cannot communicate
- **Existing primary continues serving traffic** (no failover)
- roomio-watchdog on both nodes: `get_current_leader()` returns empty → do nothing
- **Recovery:** restore WireGuard tunnel — cluster resumes automatically

> **This is correct behavior.** If watchdog used ping/public IP check instead of etcd, both nodes could simultaneously decide to activate, causing split-brain (two writers to the same database). Using etcd as the single source of truth prevents this.

---

## 12. Recovery Procedures

### Restoring eric after unplanned failover

After eric is repaired and back online:

**Step 1: Verify eric's Patroni joined as replica**

```bash
patronictl -c /etc/patroni/patroni.yml list
# node1 should show: Role=Replica, State=streaming, Lag=0 (or small)
```

**Step 2: Verify replication is caught up**

```bash
# On eric, check WAL replay
psql -h 10.0.0.1 -p 5432 -U postgres -c "
SELECT
  pg_is_in_recovery() as is_replica,
  pg_last_wal_receive_lsn() as received_lsn,
  pg_last_wal_replay_lsn() as replayed_lsn,
  pg_last_xact_replay_timestamp() as last_replay;
"
```

**Step 3: Switchover PostgreSQL leadership back to eric (optional)**

```bash
patronictl -c /etc/patroni/patroni.yml switchover roomio-db \
  --master node2 --candidate node1 --force
```

After switchover:

- eric watchdog detects `leader=node1` → `activate_self()` → Docker up + DNS switch to eric
- amigo watchdog detects `leader≠node2` → `deactivate_self()` → Docker down

**This is fully automatic — no manual steps needed after `patronictl switchover`.**

### Reinitializing a replica after data divergence

If a replica's data directory diverged from primary (e.g., after an improper shutdown), `pg_rewind` cannot fix it:

```bash
# Force full reinit from primary via pg_basebackup
patronictl -c /etc/patroni/patroni.yml reinit roomio-db node1 --force

# Or manually:
sudo systemctl stop patroni   # on eric
sudo -u postgres rm -rf /var/lib/postgresql/16/main/*
sudo systemctl start patroni   # Patroni will run pg_basebackup automatically
```

---

## 13. Monitoring & Health Checks

### Quick Dashboard

```bash
# All-in-one status check (run on any server)
echo "=== PATRONI ===" && patronictl -c /etc/patroni/patroni.yml list
echo "=== ETCD ===" && etcdctl --endpoints=http://10.0.0.1:2379,http://10.0.0.2:2379 endpoint status -w table
echo "=== HAPROXY ===" && sudo ss -tlnp | grep haproxy
echo "=== WATCHDOG ===" && sudo systemctl status roomio-watchdog --no-pager -l
echo "=== DOCKER ===" && docker compose ps 2>/dev/null || echo "Docker not running on this node"
```

### Individual Service Checks

```bash
# Patroni cluster
patronictl -c /etc/patroni/patroni.yml list

# etcd cluster
etcdctl --endpoints=http://10.0.0.1:2379,http://10.0.0.2:2379 endpoint status -w table
etcdctl --endpoints=http://10.0.0.1:2379,http://10.0.0.2:2379 endpoint health

# Patroni REST API
curl -s http://10.0.0.1:8008/cluster | python3 -m json.tool
curl -s http://10.0.0.2:8008/cluster | python3 -m json.tool

# HAProxy — verify routing
psql -h 127.0.0.1 -p 5000 -U postgres -d grms_db -c "SELECT inet_server_addr(), pg_is_in_recovery();"
psql -h 127.0.0.1 -p 5001 -U postgres -d grms_db -c "SELECT inet_server_addr(), pg_is_in_recovery();"

# Replication lag
psql -h 127.0.0.1 -p 5000 -U postgres -c "
SELECT
  client_addr,
  state,
  sent_lsn,
  write_lsn,
  flush_lsn,
  replay_lsn,
  (sent_lsn - replay_lsn) AS lag_bytes
FROM pg_stat_replication;
"

# WireGuard
sudo wg show

# Watchdog log
tail -f /var/log/roomio-watchdog.log

# Docker services
docker compose ps
docker compose logs -f --tail=50
```

### Prometheus Metrics

roomio exports metrics via `django-prometheus`. Prometheus scrapes:

- Django metrics: `host.docker.internal:8000/metrics`
- Node metrics: `node-exporter:9100`
- RabbitMQ metrics: `rabbitmq:15692`

```bash
# Prometheus UI
http://your-server:9090

# Grafana UI
http://your-server:9060  # admin/admin

# AlertManager
http://your-server:9093
```

Prometheus alert rules:

- `django.yml` — `GatewayDeviceOffline` (offline gateway devices)
- `services.yml` — `InstanceDown` (any monitored service down >1 min)
- `node-exporter.yml` — disk space, CPU, memory alerts
- `rabbitmq.yml` — queue depth alerts

---

## 14. Backup & Restore

### Creating a Backup

Always backup from the current PRIMARY via HAProxy write port:

```bash
# Full database backup
sudo -u postgres pg_dump \
  --host=127.0.0.1 \
  --port=5000 \
  --username=postgres \
  --format=custom \
  --compress=9 \
  --dbname=grms_db \
  --file=grms_$(date +%Y-%m-%d_%H_%M_%S).backup

# Verify backup
pg_restore --list grms_backup_file.backup | head -20

# Check backup size
ls -lh grms_*.backup
```

### Restoring a Backup

> **TimescaleDB version note:** If the backup was made with TimescaleDB 2.21.0 but the target has 2.28.1 (or vice versa), the `_timescaledb_*` catalog schemas are incompatible. Always exclude them and let TimescaleDB initialize its own catalogs.

**Step 1: Create database on current PRIMARY**

```bash
sudo -u postgres psql -h 127.0.0.1 -p 5000 -U postgres <<'EOF'
CREATE DATABASE grms_db;
\c grms_db
CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;
EOF
```

**Step 2: Copy backup to server (if restoring from external source)**

```bash
scp backup.backup user@111.222.333.444:/tmp/grms.backup
sudo chmod 644 /tmp/grms.backup
```

**Step 3: Restore**

```bash
sudo -u postgres pg_restore \
  --host=127.0.0.1 \
  --port=5000 \
  --username=postgres \
  --dbname=grms_db \
  --no-owner \
  --no-privileges \
  --exclude-schema=_timescaledb_catalog \
  --exclude-schema=_timescaledb_internal \
  --exclude-schema=_timescaledb_config \
  --exclude-schema=_timescaledb_cache \
  --verbose \
  /tmp/grms.backup 2>&1 | tee /tmp/restore.log

# Check for errors
grep -E "ERROR|error" /tmp/restore.log | grep -v "^pg_restore:"
```

**Step 4: Verify**

```bash
sudo -u postgres psql -h 127.0.0.1 -p 5000 -U postgres -d grms_db <<'EOF'
-- Table count
SELECT count(*) as table_count FROM information_schema.tables
WHERE table_schema = 'public';

-- TimescaleDB hypertables
SELECT hypertable_name, num_chunks FROM timescaledb_information.hypertables;

-- Row counts for key tables
SELECT 'main_room' as tbl, count(*) FROM main_room
UNION ALL SELECT 'main_guest', count(*) FROM main_guest
UNION ALL SELECT 'main_device', count(*) FROM main_device;
EOF
```

> **After restore, Patroni streaming replication automatically replicates all data to the replica.** No manual sync needed — WAL streaming handles it.

---

## 15. Emergency Runbook

### Case 1: eric is down, amigo should activate automatically

In most cases the watchdog handles this automatically within ~90 seconds. Check Telegram first.

If watchdog did NOT activate amigo:

```bash
# On amigo — check why watchdog didn't activate
sudo systemctl status roomio-watchdog
tail -50 /var/log/roomio-watchdog.log

# Check Patroni state
patronictl -c /etc/patroni/patroni.yml list

# If node2 is not Leader yet — force failover
patronictl -c /etc/patroni/patroni.yml failover roomio-db \
  --master node1 --candidate node2 --force

# If watchdog is broken — start Docker manually
cd ~/GRMS/deploy
docker compose up -d pgbouncer redis redis-broker rabbitmq
sleep 20
docker compose up -d backend celery-critical celery-default celery-low celery-beat \
  mq-async mews-websocket pms-handler mqtt frontend-nginx proxy letsencrypt

# Switch DNS manually
export CF_TOKEN="your_token"
export CF_ZONE_ID="CF_ZONE_ID_PLACEHOLDER"
for RECORD_ID in "CF_RECORD_API_PLACEHOLDER" "CF_RECORD_FRONT_PLACEHOLDER" "CF_RECORD_PORTAINER_PLACEHOLDER"; do
  curl -s -X PUT "https://api.cloudflare.com/client/v4/zones/${CF_ZONE_ID}/dns_records/${RECORD_ID}" \
    -H "Authorization: Bearer ${CF_TOKEN}" \
    -H "Content-Type: application/json" \
    -d "{\"type\":\"A\",\"content\":\"555.666.777.888\",\"ttl\":60,\"proxied\":true}"
done

# Verify
curl -sf https://api.server.com/health/ && echo "OK"
```

### Case 2: Patroni shows "Pending restart"

```bash
patronictl -c /etc/patroni/patroni.yml list
# If Pending restart column shows * with reason

# Fix DCS config to match pg_controldata values
patronictl -c /etc/patroni/patroni.yml edit-config
# Update parameters to match actual values shown in "Pending restart reason"

# Apply via rolling restart
patronictl -c /etc/patroni/patroni.yml reload roomio-db --force
patronictl -c /etc/patroni/patroni.yml restart roomio-db --force
```

### Case 3: High replication lag

```bash
# Check lag
psql -h 127.0.0.1 -p 5000 -U postgres -c "
SELECT client_addr, state, (sent_lsn - replay_lsn) AS lag_bytes
FROM pg_stat_replication;"

# If replica is lagging due to high write load, check:
# 1. Network bandwidth between servers
sudo iftop -i wg0

# 2. Disk write speed on replica
sudo iostat -x 1 5

# 3. Replica PostgreSQL logs
sudo journalctl -u patroni --no-pager -n 100 | grep -i error
```

### Case 4: Docker service fails to start on amigo

```bash
# Check logs for failing service
docker compose logs --tail=100 backend

# Check pgbouncer connectivity
docker compose exec pgbouncer psql -h 172.19.0.1 -p 5000 -U postgres -d grms_db -c "SELECT 1;"

# If pgbouncer can't reach HAProxy — check iptables
sudo iptables -L INPUT -n | grep -E "172.19|5000|ACCEPT"
# If missing:
sudo iptables -I INPUT -s 172.19.0.0/16 -p tcp --dport 5000 -j ACCEPT
sudo iptables -I INPUT -s 172.19.0.0/16 -p tcp --dport 5001 -j ACCEPT
sudo netfilter-persistent save
```

### Case 5: Both watchdogs think they should be active (split-brain scenario)

This should NOT happen with the etcd-based design, but if it does:

```bash
# On BOTH servers immediately
sudo systemctl stop roomio-watchdog

# Check Patroni — there can only be ONE primary
patronictl -c /etc/patroni/patroni.yml list

# Stop Docker on the node that is NOT the Patroni Leader
# If node1 is NOT leader:
cd ~/GRMS/deploy && docker compose down   # on eric

# Restart watchdogs
sudo systemctl start roomio-watchdog   # on both servers
```

### Service Restart Quick Reference

```bash
# Watchdog
sudo systemctl restart roomio-watchdog
sudo systemctl status roomio-watchdog

# Patroni
sudo systemctl restart patroni
patronictl -c /etc/patroni/patroni.yml list

# etcd
sudo systemctl restart etcd
etcdctl --endpoints=http://10.0.0.1:2379,http://10.0.0.2:2379 endpoint health

# HAProxy
sudo systemctl restart haproxy
sudo ss -tlnp | grep haproxy

# WireGuard
sudo systemctl restart wg-quick@wg0
sudo wg show

# Docker full restart
cd ~/GRMS/deploy
docker compose down
docker compose up -d
```

---

_roomio GRMS — Active-Passive Documentation v1.0_
_Generated: 2026-07-03_
