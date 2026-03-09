FROM python:3.11-slim

WORKDIR /app

COPY ./invia_notifiche.py ./invia_notifiche.py
COPY cronjob /etc/cron.d/cronjob

ENV TZ=Europe/Rome
RUN apt-get install -y tzdata

RUN apt-get update && apt-get install -y cron \
    && chmod 0644 /etc/cron.d/cronjob \
    && crontab /etc/cron.d/cronjob

RUN touch /var/log/cron.log

CMD ["cron", "-f"]