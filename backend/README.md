# Deployment

# Build project for gitlab.registry.com

`docker buildx build --platform linux/amd64,linux/arm64 -t registry.gitlab.com/yroomio/grms:latest --push .`

## if you don't want to --push change this to --load for locally build

### Usefull commands and snippets

`

- docker ps
- docker ps -a
- docker images
- docker images -a
- docker run --rm -it registry.gitlab.com/yroomio/grms:latest bash
- docker logs -f container_name
- docker compose logs -f service_name
- docker exec -it django bash
- docker compose up --build -d
- docker compose down

`
