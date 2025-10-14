FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt


RUN apt-get update && apt-get install -y supervisor htop vim

RUN mkdir -p /var/log/django
RUN chmod -R 755 /var/log/django

RUN mkdir -p /prom_mp

COPY . .

COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["/entrypoint.sh"]

