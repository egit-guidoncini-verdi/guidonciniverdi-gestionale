FROM python

WORKDIR /gestionale_gv

COPY requirements.txt .

RUN pip install -r requirements.txt

COPY ./app.py ./app.py
COPY ./templates ./templates
COPY ./static ./static

CMD ["gunicorn",  "-w 2", "-b 0.0.0.0",  "app:app"]
