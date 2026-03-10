FROM python:3.11-slim

ENV TZ=Europe/Rome

WORKDIR /daemon

COPY ./requirements.txt ./requirements.txt

RUN pip install -r requirements.txt

COPY ./daemon.py ./daemon.py

CMD ["python","daemon.py"]