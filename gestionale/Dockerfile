FROM python:3.11-slim

WORKDIR /gestionale_gv

COPY ./requirements.txt ./requirements.txt

RUN pip install -r requirements.txt

COPY ./app.py ./app.py
COPY ./templates ./templates
COPY ./static ./static
COPY ./migrations ./migrations
COPY ./docker-entrypoint.sh ./docker-entrypoint.sh

RUN chmod +x ./docker-entrypoint.sh

ENTRYPOINT ["./docker-entrypoint.sh"]