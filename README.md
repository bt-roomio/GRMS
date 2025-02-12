# Deployment Instructions

This guide will help you deploy the project using Docker and Docker Compose on a Linux (Debian/Ubuntu) server.

## Prerequisites

- **Operating System:** Linux (Debian/Ubuntu)
- **Docker:** Installed and running
- **Docker Compose:** Installed and running

## Deployment Steps

### 1. Copy Required Files to the Server

Transfer the following files to the directory on your server where you plan to deploy the project:

- `docker-compose.yml`
- `prod.env.example`
- `nginx.conf`

### 2. Create the Environment File

On your server, create a new environment file by copying the example file:

```bash
cp -n prod.env.example prod.env
```

*Alternatively, you can manually copy `prod.env.example` to `prod.env`.*

### 3. Configure Environment Variables

Edit the `prod.env` file to update the environment variables according to your deployment settings.

### 4. (Optional) Modify the Docker Compose File

If necessary, adjust the `docker-compose.yml` file to fit your deployment requirements.

### 5. Configure Nginx

You can update the `nginx.conf` file to change the domains for the backend and frontend.

#### Backend Domain

In `nginx.conf`, locate the backend server block:

```nginx
server {
    listen 8080; # Do not change
    server_name localhost;  # Change this to your backend domain
    ...
}
```

#### Frontend Domain

Similarly, update the frontend server block:

```nginx
server {
    listen 80; # Do not change
    server_name localhost;  # Change this to your frontend domain
    ...
}
```

#### Port Configuration

Make sure the port mappings in the `docker-compose.yml` file are set correctly:

```yaml
nginx:
  ports:
    - "9000:8080"  # Maps port 9000 on the host to port 8080 in the container (Backend)
    - "8095:80"    # Maps port 8095 on the host to port 80 in the container (Frontend)
```

### 6. Deploy the Project

Build and run the project containers in detached mode with the following command:

```bash
docker-compose up --build -d
```

### 7. Verify the Deployment

After deployment, check that everything is running correctly:

- **Backend:** Open [http://localhost:9000/](http://localhost:9000/) in your browser.
- **Frontend:** Open [http://localhost:8095/](http://localhost:8095/) in your browser.

---

Your application should now be deployed successfully. If you run into any issues, double-check your configuration files and environment variables. Happy deploying!

Usefull commands
`docker compose pull && docker compose down && docker compose up -d;`
