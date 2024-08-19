FROM python:3.11

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt


RUN apt-get update && apt-get install -y supervisor

RUN mkdir -p /var/log/django
RUN chmod -R 755 /var/log/django

COPY . .

COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

CMD ["supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
