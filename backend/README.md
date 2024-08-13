# Docker

Configure postgresql image:
1. `docker run --name postgres -p 5432:5432 -e POSTGRES_USER=DB_USER -e POSTGRES_PASSWORD=DB_PASSWORD -d postgres`
2. `docker exec -it postgres bash`
3. `psql -U DB_USER`
4. `create database DB_NAME owner DB_USER;`

# Celery

### Commands

```celery -A config worker -l INFO```

```celery -A config beat -l INFO```