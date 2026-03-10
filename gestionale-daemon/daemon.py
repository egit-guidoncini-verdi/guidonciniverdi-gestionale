from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, JSON, Boolean, ForeignKey, UnicodeText
from sqlalchemy.orm import declarative_base, sessionmaker
from jinja2 import Environment, FileSystemLoader
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime
from time import sleep
import threading
import requests
import smtplib
import json
import os


sender_address = os.environ["MAIL_USERNAME"]
smtp_host = os.environ["MAIL_HOST"]
smtp_port = os.environ["MAIL_PORT"]

drivers = {
    "sqlite": "sqlite:///",
    "postgresql": "postgresql://",
    "mariadb": "mysql+pymysql://",
}

db_type = os.environ["DB_TYPE"]
if db_type not in drivers:
    print("Tipo di database non supportato")
    raise RuntimeError("Tipo di database non supportato")

if db_type == "sqlite":
    uri = f"{drivers[db_type]}{os.environ['DB_NAME']}"
else:
    uri = (
        f"{drivers[db_type]}"
        f"{os.environ['DB_USER']}:"
        f"{os.environ['DB_PASSWORD']}@"
        f"{os.environ['DB_HOST']}:"
        f"{os.environ['DB_PORT']}/"
        f"{os.environ['DB_NAME']}"
    )

Base = declarative_base()

class CodaMail(Base):
    __tablename__ = "coda_mail"
    id = Column(Integer, primary_key=True)
    data = Column(DateTime, nullable=False)
    stato = Column(String(255), nullable=False)
    regione = Column(Integer, ForeignKey("regioni.id"), nullable=False)
    indirizzi = Column(JSON, nullable=False)
    indirizzi_copia = Column(JSON, nullable=False)
    titolo = Column(String(255), nullable=False)
    testo = Column(UnicodeText, nullable=False)

class Regione(Base):
    __tablename__ = "regioni"
    id = Column(Integer, primary_key=True)
    regione = Column(String(255), nullable=False)
    mail = Column(String(255), nullable=True)

class Demone(Base):
    __tablename__ = "demoni"
    key = Column(String(255), primary_key=True)
    value = Column(Boolean, nullable=False)

class AnnoCorrente(Base):
    __tablename__ = "anno_corrente"
    value = Column(String(4), primary_key=True)

engine = create_engine(uri)
Session = sessionmaker(bind=engine)

def invia_notifiche():
    url = os.environ["URL_NOTIFICHE"]
    api_key = os.environ["API_KEY"]
    response = requests.post(url, data={"api_key": api_key, "tipologia": "iabz"})
    print(response.json())

def send_mail():
    def task():
        demone_mail = True
        while demone_mail:
            env = Environment(loader=FileSystemLoader("."))
            template = env.get_template("mail_base.html")
            session = Session()
            demone_mail = session.query(Demone).filter_by(key="send_mail").first().value

            try:
                tmp_mail = session.query(CodaMail).filter_by(stato="PENDING").first()
                tmp_mail.stato = "SENDING"
                session.commit()
                try:
                    tmp_regione = session.query(Regione).filter_by(id=tmp_mail.regione).first()
                    anno = session.query(AnnoCorrente).all()[0].value
                    html = template.render(anno=anno, titolo=tmp_mail.titolo, testo=tmp_mail.testo, mail_regione=tmp_regione.mail)
                    indirizzi = tmp_mail.indirizzi.copy()
                    message = MIMEMultipart("alternative")
                    message["Subject"] = f"Guidoncini Verdi {anno} - {tmp_mail.titolo}"
                    message["From"] = sender_address
                    message["Reply-To"] = tmp_regione.mail
                    message["To"] = ", ".join(tmp_mail.indirizzi)
                    if tmp_mail.indirizzi_copia:
                        message["Cc"] = ", ".join(tmp_mail.indirizzi_copia)
                        indirizzi.extend(tmp_mail.indirizzi_copia)

                    text = f"{tmp_mail.titolo}\n{tmp_mail.testo}"
                    part1 = MIMEText(text, "plain")
                    part2 = MIMEText(html, "html")
                    message.attach(part1)
                    message.attach(part2)

                    with smtplib.SMTP(smtp_host, smtp_port) as server:
                        response = server.sendmail(sender_address, indirizzi, message.as_string())
                    
                    if response == {}:
                        tmp_mail.stato = "SENT"
                    else:
                        tmp_mail.stato = "FAILED"

                except Exception as e:
                    print(e)
                    tmp_mail.stato = "FAILED"
                session.commit()
            except:
                pass
            session.close()
            sleep(30)
    threading.Thread(target=task, name="send_mail", daemon=True).start()

send_mail()
while True:
    pass