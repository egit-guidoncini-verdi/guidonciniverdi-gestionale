FROM python:3.11-slim

ENV TZ=Europe/Rome

WORKDIR /app

COPY ./invia_notifiche.py ./invia_notifiche.py

RUN apt-get update \
    && apt-get install -y cron tzdata \
    && ln -snf /usr/share/zoneinfo/$TZ /etc/localtime \
    && echo $TZ > /etc/timezone \
    && rm -rf /var/lib/apt/lists/*

COPY cronjob /etc/cron.d/cronjob

RUN chmod 0644 /etc/cron.d/cronjob \
    && touch /var/log/cron.log

CMD ["cron","-f"]