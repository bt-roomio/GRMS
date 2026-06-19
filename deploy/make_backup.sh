#!/usr/bin/env bash
set -euo pipefail

# === SETTINGS ===
BACKUP_DIR="/tmp/backups"
CONTAINER="postgres"

# Path to .env (defaults to the directory where this script lives)
ENV_FILE="${ENV_FILE:-"$(dirname "$(realpath "$0")")/.env"}"

if [[ ! -f "${ENV_FILE}" ]]; then
  echo "[ERROR] .env not found: ${ENV_FILE}" >&2
  exit 1
fi

# Reads a variable value from .env, stripping quotes and inline comments
get_env() {
  grep -m1 "^${1}=" "${ENV_FILE}" | cut -d= -f2- | sed 's/[[:space:]]*#.*//' | tr -d "'\""
}

DB_NAME="$(get_env POSTGRES_DB)"
DB_USER="$(get_env POSTGRES_USER)"
DB_PASSWORD="$(get_env POSTGRES_PASSWORD)"

# Tables to exclude data from (schema only):
EXCLUDE_DATA_TABLES=(
  main_room_history
#  shuttle_ts_kv
)

# === 1) Prepare backup directory ===
mkdir -p "${BACKUP_DIR}"
find "${BACKUP_DIR}" -mindepth 1 -maxdepth 1 -print0 | xargs -0r rm -rf --

# === 2) Dump database ===
TS="$(date +%Y-%m-%d_%H_%M_%S)"
DUMP_PATH="${BACKUP_DIR}/grms_${TS}.backup"

EXCLUDE_ARGS=()
for tbl in "${EXCLUDE_DATA_TABLES[@]}"; do
  EXCLUDE_ARGS+=(--exclude-table-data="${tbl}")
  # TimescaleDB stores hypertable data in internal chunks; exclude those too
  while IFS= read -r chunk; do
    [[ -n "${chunk}" ]] && EXCLUDE_ARGS+=(--exclude-table-data="${chunk}")
  done < <(docker exec -e PGPASSWORD="${DB_PASSWORD}" "${CONTAINER}" \
    psql -U "${DB_USER}" -d "${DB_NAME}" -At -c \
    "SELECT chunk_schema || '.' || chunk_name
       FROM timescaledb_information.chunks
      WHERE hypertable_schema = 'public'
        AND hypertable_name = '${tbl}';" 2>/dev/null)
done

echo "[INFO] Dumping '${DB_NAME}' from container '${CONTAINER}' -> ${DUMP_PATH}"
docker exec -e PGPASSWORD="${DB_PASSWORD}" "${CONTAINER}" \
  pg_dump -U "${DB_USER}" -Fc "${EXCLUDE_ARGS[@]}" "${DB_NAME}" >"${DUMP_PATH}"

echo "[OK] Done: ${DUMP_PATH}"
