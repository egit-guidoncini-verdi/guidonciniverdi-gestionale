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
import random
import base64
import json
import os

specialita = [
    "Alpinismo",
    "Artigianato",
    "Campismo",
    "Civitas",
    "Esplorazione",
    "Espressione",
    "Giornalismo",
    "Internazionale",
    "Natura",
    "Nautica",
    "Olimpia",
    "Pronto intervento"
]

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

class CodaTelegram(Base):
    __tablename__ = "coda_telegram"
    id = Column(Integer, primary_key=True)
    data = Column(DateTime, nullable=False)
    stato = Column(String(255), nullable=False)
    chat_id = Column(Integer, nullable=False)
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

class SysOption(Base):
    __tablename__ = "system_option"
    key = Column(String(128), primary_key=True)
    value = Column(String(128), nullable=False)

engine = create_engine(uri, pool_pre_ping=True, pool_recycle=3600)
Session = sessionmaker(bind=engine)

demone_mail = True
demone_telegram = True
demone_notifiche = True
demone_wordpress = True

def manda_mail(indirizzi, copia, titolo, testo, regione):
    session.add(CodaMail(data=datetime.now(), stato="PENDING", regione=regione, indirizzi=indirizzi, indirizzi_copia=copia, titolo=f"Guidoncini Verdi {session.query(SysOption).filter_by(key='AnnoCorrente').first().value} - {titolo}", testo=testo))
    session.commit()
    return True

def manda_telegram(chat_id, titolo, testo):
    session.add(CodaTelegram(data=datetime.now(), stato="PENDING", chat_id=chat_id, titolo=f"Guidoncini Verdi {session.query(SysOption).filter_by(key='AnnoCorrente').first().value} - {titolo}", testo=testo))
    session.commit()
    return True

def genera_password_sq():
    nomi = ["Akela", "Baloo", "Chil", "Kaa", "Raksha", "Arcanda", "Sciba", "Scoiattoli", "Mi", "Mowgli"]
    colori = ["Rosso", "Blu", "Verde", "Giallo", "Arancione", "Viola", "Rosa", "Marrone", "Grigio", "Nero"]
    return f"{random.choice(nomi)}{random.choice(colori)}"

def crea_utente(id_iscrizione, header, dati):
    try:
        response = requests.post(os.environ["WORDPRESS_URL"]+"/users", headers=header, json=dati)
        id_autore = response.json()["id"]
    except Exception as e:
        print(e)
        return False
    session = Session()
    utente = WordpressUser(data=str(datetime.now()), iscrizioni_id=int(id_iscrizione), wordpress_id=int(id_autore), username=dati["username"], password=dati["password"], meta=dati)
    session.add(utente)
    session.commit()
    return id_autore

def crea_post(id_iscrizione, id_autore, header, dati, tipo):
    try:
        response = requests.post(os.environ["WORDPRESS_URL"]+"/posts", headers=header, json=dati)
        id_post = response.json()["id"]
    except:
        return False
    session = Session()
    utente = session.query(WordpressUser).filter_by(wordpress_id=int(id_autore)).first()
    post = WordpressPost(data=str(datetime.now()), iscrizioni_id=int(id_iscrizione), wordpress_user_id=utente.id, wordpress_id=int(id_post), tipo=tipo, meta=dati)
    session.add(post)
    session.commit()
    return id_post

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

def send_telegram():
    def task():
        scheduler = schedule.Scheduler()
        def job():
            session = Session()
            tmp_telegram = session.query(CodaTelegram).filter_by(stato="PENDING").first()
            if tmp_telegram:
                tmp_telegram.stato = "SENDING"
                session.commit()
                try:
                    text = quote(f"{tmp_telegram.titolo}\n{tmp_telegram.testo}")
                    t_url = f"https://api.telegram.org/bot{os.environ['TELEGRAM_TOKEN']}/sendMessage?chat_id={tmp_telegram.chat_id}&text={text}"
                    requests.get(t_url, timeout=20)
                    
                    tmp_telegram.stato = "SENT"

                except Exception as e:
                    print(e)
                    tmp_telegram.stato = "FAILED"
                session.commit()
            session.close()

        scheduler.every(10).seconds.do(job)

        global demone_telegram
        while demone_telegram:
            scheduler.run_pending()
            sleep(1)
    threading.Thread(target=task, name="send_telegram", daemon=True).start()

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
                    anno = session.query(SysOption).filter_by(key="AnnoCorrente").first().value
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
                        indirizzi = [x for x in indirizzi if x != ""]

                    text = f"{tmp_mail.titolo}\n{tmp_mail.testo}"
                    part1 = MIMEText(text, "plain")
                    part2 = MIMEText(html, "html")
                    message.attach(part1)
                    message.attach(part2)

                    with smtplib.SMTP(smtp_host, smtp_port) as server:
                        response = server.sendmail(sender_address, indirizzi, message.as_string())
                    
                    refused_count = len(response)
                    sent_count = len(indirizzi) - refused_count
                    if refused_count:
                        print(f"Mail {tmp_mail.id}: destinatari rifiutati dal server SMTP: {response}")

                    if sent_count > 0:
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
        scheduler = schedule.Scheduler()
        creds = f"{os.environ['WORDPRESS_USER']}:{os.environ['WORDPRESS_PASSWORD']}"
        token = base64.b64encode(creds.encode())
        header = {"Authorization": f"Basic {token.decode('utf-8')}"}
        session = Session()
        tmp_iscrizioni = session.query(IscrizioniEG).filter_by(stato="in_abilitazione")
        for i in tmp_iscrizioni:
            i.stato = "da_abilitare"
        tmp_jobs = session.query(JobWordpress).filter_by(stato="SENDING")
        for i in tmp_jobs:
            i.stato = "PENDING"
        session.commit()
        session.close()

        def job():
            session = Session()
            tmp_job = session.query(JobWordpress).filter_by(stato="PENDING").first()
            if tmp_job:
                tmp_job.stato = "SENDING"
                session.commit()
                
                if tmp_job.dati["tipo"] == "crea_sq":
                    tmp_iscrizione = session.query(IscrizioniEG).filter_by(id=tmp_job.dati["iscrizione"]).first()
                    tmp_iscrizione.stato = "in_abilitazione"
                    session.commit()
                    tmp_passwd = genera_password_sq()
                    dati = {
                        "username": tmp_job.dati["username"],
                        "name": tmp_iscrizione.nome.capitalize(),
                        "email": f"{tmp_job.dati['username']}@guidonciniverdi.it",
                        "password": tmp_passwd,
                        "meta": tmp_job.dati["meta"]
                        }

                    id_autore = crea_utente(tmp_job.dati["iscrizione"], header, dati)
                    if not id_autore:
                        tmp_job.stato = "FAILED"
                        tmp_iscrizione.stato = "failed_user"
                    tmp_ok = True
                    tmp_content = requests.get(f"{os.environ['WORDPRESS_URL']}/posts/{session.query(SysOption).filter_by(key='TemplatePost').first().value}?context=edit", headers=header, verify=False).json()["content"]["raw"]

                    specialita_wordpress = requests.get(f"{os.environ['WORDPRESS_URL']}/specialita?per_page=100", headers=header, verify=False).json()
                    tmp_specialita = {}
                    for i in specialita_wordpress:
                        tmp_specialita[i["name"]] = i["id"]
                    categorie_wordpress = requests.get(f"{os.environ['WORDPRESS_URL']}/categories?per_page=100", headers=header, verify=False).json()
                    tmp_id_categoria = 0
                    for i in categorie_wordpress:
                        if i["name"] == "Pagina unica":
                            tmp_id_categoria = i["id"]

                    dati = {
                        "author": int(id_autore),
                        "categories": [tmp_id_categoria],
                        "content": tmp_content,
                        "meta": tmp_job.dati["meta"],
                        "specialita": [tmp_specialita[tmp_iscrizione.specialita.title()]],
                        "title": f"{tmp_job.dati['meta']['squadriglia']}",
                        "status": "publish"
                        }
                    id_post = crea_post(tmp_job.dati["iscrizione"], int(id_autore), header, dati, "posts")
                    if not id_post:
                        tmp_ok = False

                    if not tmp_ok:
                        try:
                            testo_telegram = f"Squadriglia {tmp_iscrizione.nome}\n{tmp_iscrizione.gruppo} - {tmp_iscrizione.zona}\nNon tutti i post sono stati correttamente creati"
                            manda_telegram(User.query.filter_by(username="egm").first().telegram_id, "Problema tecnico!!", testo_telegram)
                            manda_telegram(User.query.filter_by(username="admin").first().telegram_id, "Problema tecnico!!", testo_telegram)
                        except:
                            print("Errore")
                        tmp_job.stato = "FAILED"
                        tmp_iscrizione.stato = "failed_post"
                    else:
                        tmp_job.stato = "DONE"
                        tmp_iscrizione.link = requests.get(f"{os.environ['WORDPRESS_URL']}/posts/{str(id_post)}", headers=header).json()["link"]
                        tmp_iscrizione.stato = "abilitato"

                        testo_mail_sq = f"Congratulazioni {tmp_iscrizione.nome},<br>ecco le credenziali per il Diario di Bordo Digitale, potete accedere <a href=\"https://guidonciniverdi.it/wp-login.php\" target=\"_blank\">cliccando qui</a> oppure scaricando la app.<br><a href=\"https://play.google.com/store/apps/details?id=org.wordpress.android\" target=\"_blank\">Clicca qui per scaricare la app per Android</a><br><a href=\"https://apps.apple.com/it/app/wordpress-website-builder/id335703880\" target=\"_blank\">Clicca qui per scaricare la app per iOS</a><br>Trovate maggiori info qui: <a href=\"https://guidonciniverdi.it/come-funziona/\" target=\"_blank\">guidonciniverdi.it/come-funziona/</a><br><h4><strong>Credenziali</strong></h4>Username: {tmp_job.dati['username']}<br>Password: {tmp_passwd}"
                        manda_mail([tmp_iscrizione.mail], [tmp_iscrizione.mail_capo1, tmp_iscrizione.mail_capo2], "Credenziali Diario di Bordo!", testo_mail_sq, tmp_iscrizione.regione)
                    session.commit()

                session.commit()
            session.close()

        scheduler.every(10).seconds.do(job)

        global demone_wordpress
        while demone_wordpress:
            scheduler.run_pending()
            sleep(1)
    threading.Thread(target=task, name="job_wordpress", daemon=True).start()

while True:
    session = Session()
    demoni = {d.key: d.value for d in session.query(Demone).all()}
    session.close()
    demone_mail = demoni["send_mail"]
    demone_telegram = demoni["send_telegram"]
    demone_notifiche = demoni["send_notifiche"]
    demone_wordpress = demoni["job_wordpress"]
    session.close()
    mail_seen = False
    telegram_seen = False
    notifiche_seen = False
    wordpress_seen = False
    for i in threading.enumerate():
        if i.name == "send_mail":
            mail_seen = True
        if i.name == "send_telegram":
            telegram_seen = True
        if i.name == "send_notifiche":
            notifiche_seen = True
        if i.name == "job_wordpress":
            wordpress_seen = True
    if demone_mail and not mail_seen:
        send_mail()
    if demone_telegram and not telegram_seen:
        send_telegram()
    if demone_notifiche and not notifiche_seen:
        send_notifiche()
    if demone_wordpress and not wordpress_seen:
        job_wordpress()
    sleep(30)
