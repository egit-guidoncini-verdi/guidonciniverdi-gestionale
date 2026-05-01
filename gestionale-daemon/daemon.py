from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, JSON, Boolean, ForeignKey, UnicodeText
from sqlalchemy.orm import declarative_base, sessionmaker
from jinja2 import Environment, FileSystemLoader
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from urllib.parse import quote
from datetime import datetime
from time import sleep
import threading
import schedule
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

class User(Base):
    __tablename__ = "user"
    id = Column(Integer, primary_key=True)
    username = Column(String(255), nullable=False, unique=True)
    password = Column(String(255), nullable=False)
    mail = Column(String(255), nullable=False)
    regione = Column(Integer, ForeignKey("regioni.id"), nullable=True)
    zona = Column(Integer, ForeignKey("zone.id"), nullable=True)
    livello = Column(String(255), nullable=False)
    telegram_id = Column(String(255), nullable=True)

class IscrizioniEG(Base):
    __tablename__ = "iscrizioniEG"
    id = Column(Integer, primary_key=True)
    data = Column(DateTime, nullable=False)
    stato = Column(String(255), nullable=False)
    nome = Column(String(255), nullable=False)
    mail = Column(String(255), nullable=False)
    regione = Column(Integer, nullable=False)
    zona = Column(Integer, ForeignKey("zone.id"), nullable=False)
    gruppo = Column(Integer, ForeignKey("gruppi.id"), nullable=False)
    specialita = Column(String(255), nullable=False)
    # tipo indica se conquista o conferma => True se conferma
    tipo = Column(String(255), nullable=False)
    # Contatti
    nome_capo_sq = Column(String(255), nullable=False)
    nome_capo1 = Column(String(255), nullable=False)
    mail_capo1 = Column(String(255), nullable=False)
    cell_capo1 = Column(String(255), nullable=False)
    nome_capo2 = Column(String(255), nullable=False)
    mail_capo2 = Column(String(255), nullable=False)
    cell_capo2 = Column(String(255), nullable=False)
    sesso = Column(String(2), nullable=False)
    link = Column(Text, nullable=False)

class WordpressUser(Base):
    __tablename__ = "wordpress_user"
    id = Column(Integer, primary_key=True)
    data = Column(DateTime, nullable=False)
    iscrizioni_id = Column(Integer, ForeignKey("iscrizioniEG.id"), nullable=False)
    wordpress_id = Column(Integer, nullable=False)
    username = Column(String(255), nullable=False)
    password = Column(String(255), nullable=False)
    meta = Column(JSON, nullable=False)

class WordpressPost(Base):
    __tablename__ = "wordpress_post"
    id = Column(Integer, primary_key=True)
    data = Column(DateTime, nullable=False)
    iscrizioni_id = Column(Integer, ForeignKey("iscrizioniEG.id"), nullable=False)
    wordpress_user_id = Column(Integer, ForeignKey("wordpress_user.id"), nullable=False)
    wordpress_id = Column(Integer, nullable=False)
    tipo = Column(String(255), nullable=False)
    meta = Column(JSON, nullable=False)

class RelazioniPuglia(Base):
    __tablename__ = "relazioni_puglia"
    id = Column(Integer, primary_key=True)
    data = Column(DateTime, nullable=False)
    stato = Column(JSON, nullable=False)
    iscrizioni_id = Column(Integer, ForeignKey("iscrizioniEG.id"), nullable=False)
    dati = Column(JSON, nullable=False)

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

class JobWordpress(Base):
    __tablename__ = "job_wordpress"
    id = Column(Integer, primary_key=True)
    data = Column(DateTime, nullable=False)
    stato = Column(String(255), nullable=False)
    dati = Column(JSON, nullable=False)

class StatusPercorso(Base):
    __tablename__ = "status_percorso"
    id = Column(Integer, primary_key=True)
    anno = Column(String(4), nullable=True)
    iscrizioni = Column(JSON, nullable=False)
    abilitazioni = Column(JSON, nullable=False)
    regione = Column(Integer, ForeignKey("regioni.id"), nullable=True)
    data_apertura = Column(DateTime, nullable=True)
    data_chiusura = Column(DateTime, nullable=True)

class Regione(Base):
    __tablename__ = "regioni"
    id = Column(Integer, primary_key=True)
    regione = Column(String(255), nullable=False)
    mail = Column(String(255), nullable=True)

class Zona(Base):
    __tablename__ = "zone"
    id = Column(Integer, primary_key=True)
    zona = Column(String(255), nullable=False)
    regione = Column(Integer, ForeignKey("regioni.id"), nullable=False)

class Gruppo(Base):
    __tablename__ = "gruppi"
    id = Column(Integer, primary_key=True)
    gruppo = Column(String(255), nullable=True)
    zona = Column(Integer, ForeignKey("zone.id"), nullable=False)
    regione = Column(Integer, ForeignKey("regioni.id"), nullable=False)

class Demone(Base):
    __tablename__ = "demoni"
    key = Column(String(255), primary_key=True)
    value = Column(Boolean, nullable=False)

class AnnoCorrente(Base):
    __tablename__ = "anno_corrente"
    value = Column(String(4), primary_key=True)

engine = create_engine(uri, pool_pre_ping=True, pool_recycle=3600)
Session = sessionmaker(bind=engine)

demone_mail = True
demone_notifiche = True
demone_wordpress = True

def manda_telegram(chat_id, titolo, testo):
    text = quote(f"{titolo}\n{testo}")
    t_url = f"https://api.telegram.org/bot{os.environ['TELEGRAM_TOKEN']}/sendMessage?chat_id={chat_id}&text={text}"
    try:
        requests.get(t_url, timeout=20)
    except Exception as e:
        print(e)

def send_notifiche():
    def task():
        scheduler = schedule.Scheduler()
        def job():
            session = Session()
            try:
                tmp_utenti = session.query(User).filter_by(livello="iabr").all()
                tmp_utenti.extend(session.query(User).filter_by(livello="pattuglia").all())
                for i in tmp_utenti:
                    non_abilitate = session.query(IscrizioniEG).filter_by(stato="da_abilitare").filter_by(regione=i.regione).count()
                    abilitate = session.query(IscrizioniEG).filter_by(stato="abilitato").filter_by(regione=i.regione).count()
                    testo_telegram = f"Da abilitare: {non_abilitate}\nAbilitate: {abilitate}"
                    if non_abilitate > 0:
                        manda_telegram(i.telegram_id, f"Report {i.regione.capitalize()}", testo_telegram)

                tmp_utenti = session.query(User).filter_by(livello="iabz").all()
                for i in tmp_utenti:
                    non_abilitate = session.query(IscrizioniEG).filter_by(stato="da_abilitare").filter_by(zona=i.zona).count()
                    abilitate = session.query(IscrizioniEG).filter_by(stato="abilitato").filter_by(zona=i.zona).count()
                    testo_telegram = f"Da abilitare: {non_abilitate}\nAbilitate: {abilitate}"
                    if non_abilitate > 0:
                        manda_telegram(i.telegram_id, f"Report {i.zona}", testo_telegram)
            except Exception as e:
                print(e)
            session.close()

        scheduler.every().saturday.at("10:00").do(job)

        global demone_notifiche
        while demone_notifiche:
            scheduler.run_pending()
            sleep(1)
    threading.Thread(target=task, name="send_notifiche", daemon=True).start()

def send_mail():
    def task():
        env = Environment(loader=FileSystemLoader("."))
        template = env.get_template("mail_base.html")
        scheduler = schedule.Scheduler()
        def job():
            session = Session()
            tmp_mail = session.query(CodaMail).filter_by(stato="PENDING").first()
            if tmp_mail:
                tmp_mail.stato = "SENDING"
                session.commit()
                try:
                    tmp_regione = session.query(Regione).filter_by(id=tmp_mail.regione).first()
                    anno = session.query(AnnoCorrente).all[0].value
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
            session.close()

        scheduler.every(10).seconds.do(job)

        global demone_mail
        while demone_mail:
            scheduler.run_pending()
            sleep(1)
    threading.Thread(target=task, name="send_mail", daemon=True).start()

def job_wordpress():
    def task():
        global demone_wordpress
        while demone_wordpress:
            sleep(10)
    threading.Thread(target=task, name="job_wordpress", daemon=True).start()

while True:
    session = Session()
    demoni = {d.key: d.value for d in session.query(Demone).all()}
    session.close()
    demone_mail = demoni["send_mail"]
    demone_notifiche = demoni["send_notifiche"]
    demone_wordpress = demoni["job_wordpress"]
    session.close()
    mail_seen = False
    notifiche_seen = False
    wordpress_seen = False
    for i in threading.enumerate():
        if i.name == "send_mail":
            mail_seen = True
        if i.name == "send_notifiche":
            notifiche_seen = True
        if i.name == "job_wordpress":
            wordpress_seen = True
    if demone_mail and not mail_seen:
        send_mail()
    if demone_notifiche and not notifiche_seen:
        send_notifiche()
    if demone_wordpress and not wordpress_seen:
        job_wordpress()
    sleep(30)