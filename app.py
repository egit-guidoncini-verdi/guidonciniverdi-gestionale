from flask import Flask, render_template, redirect, jsonify, request, url_for, flash, send_from_directory, send_file
from flask_login import UserMixin, login_user, LoginManager, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from flask_sqlalchemy import SQLAlchemy
from flask_ckeditor import CKEditor
import smtplib, ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import pandas as pd
from datetime import datetime
import requests
import secrets
import string
import base64
import random
import json

with open("credenziali.json", "r") as f:
    cr = json.load(f)

# generazione dell'elenco gruppi
gruppi = {}
df = pd.read_csv("gruppi.csv")

for i in list(set(df["zona"].tolist())):
    gruppi[i] = []

for i in df.index:
    gruppi[df["zona"][i]].append(df["Denominazione Gruppo"][i])

# costanti varie
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

# Inizializza app e servizi
app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] =  "sqlite:///gv_db.db"
app.config["SECRET_KEY"] = secrets.token_hex()
db = SQLAlchemy(app)

login_manager = LoginManager(app)
login_manager.login_view = "login"

ckeditor = CKEditor(app)

# Classi Database
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(128), nullable=False, unique=True)
    password = db.Column(db.String(128), nullable=False)
    mail = db.Column(db.String(128), nullable=False)
    zona = db.Column(db.String(128), nullable=True)
    livello = db.Column(db.String(128), nullable=False)
    telegram_id = db.Column(db.String(128), nullable=True)

class IscrizioniEG(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    data = db.Column(db.String(128), nullable=False)
    stato = db.Column(db.String(128), nullable=False)
    nome = db.Column(db.String(128), nullable=False)
    mail = db.Column(db.String(128), nullable=False)
    zona = db.Column(db.String(128), nullable=False)
    gruppo = db.Column(db.String(128), nullable=False)
    specialita = db.Column(db.String(128), nullable=False)
    # tipo indica se conquista o conferma => True se conferma
    tipo = db.Column(db.String(128), nullable=False)
    # Contatti
    nome_capo_sq = db.Column(db.String(128), nullable=False)
    nome_capo1 = db.Column(db.String(128), nullable=False)
    mail_capo1 = db.Column(db.String(128), nullable=False)
    cell_capo1 = db.Column(db.String(128), nullable=False)
    nome_capo2 = db.Column(db.String(128), nullable=False)
    mail_capo2 = db.Column(db.String(128), nullable=False)
    cell_capo2 = db.Column(db.String(128), nullable=False)

class WordpressUser(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    data = db.Column(db.String(128), nullable=False)
    iscrizioni_id = db.Column(db.Integer, nullable=False)
    wordpress_id = db.Column(db.Integer, nullable=False)
    username = db.Column(db.String(128), nullable=False)
    meta = db.Column(db.JSON, nullable=False)

class WordpressPost(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    data = db.Column(db.String(128), nullable=False)
    iscrizioni_id = db.Column(db.Integer, nullable=False)
    wordpress_user_id = db.Column(db.Integer, nullable=False)
    wordpress_id = db.Column(db.Integer, nullable=False)
    # campo di testo per indicare se "presentazione", "prima_impresa", "seconda_impresa", "missione", "extra"
    tipo = db.Column(db.String(128), nullable=False)
    meta = db.Column(db.JSON, nullable=False)

class TestiMail(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    data = db.Column(db.String(128), nullable=False)
    stato = db.Column(db.JSON, nullable=False)
    destinatari = db.Column(db.JSON, nullable=False)
    titolo = db.Column(db.String(128), nullable=False)
    testo = db.Column(db.UnicodeText, nullable=False)

class StatusPercorso(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    stato = db.Column(db.JSON, nullable=False)
    data_apertura = db.Column(db.String(128), nullable=False)
    data_chiusura = db.Column(db.String(128), nullable=False)

with app.app_context():
    db.create_all()

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def manda_mail(indirizzi, copia, titolo, testo):
    message = MIMEMultipart("alternative")
    message["Subject"] = f"Guidoncini Verdi 2024 - {titolo}"
    message["From"] = cr["mail"]["sender_email"]
    message["To"] = ", ".join(indirizzi)
    if copia:
        message["Cc"] = ", ".join(copia)
        indirizzi.extend(copia)

    text = f"{titolo}\n{testo}"
    html = render_template("mail_base.html", titolo=titolo, testo=testo)

    part1 = MIMEText(text, "plain")
    part2 = MIMEText(html, "html")

    message.attach(part1)
    message.attach(part2)

    context = ssl.create_default_context()
    try:
        with smtplib.SMTP(cr["mail"]["smtp_server"], cr["mail"]["port"]) as server:
            server.ehlo()
            server.starttls(context=context)
            server.ehlo()
            server.login(cr["mail"]["sender_email"], cr["mail"]["passwd"])
            server.sendmail(cr["mail"]["sender_email"], indirizzi, message.as_string())
            server.quit()
        return True
    except:
        return False

def manda_telegram(chat_id, titolo, testo):
    text = f"{titolo}\n{testo}"
    t_url = f"https://api.telegram.org/bot{cr['telegram']['token']}/sendMessage?chat_id={chat_id}&text={text}"
    try:
        requests.get(t_url)
        return True
    except:
        return False

def genera_password_sq():
    nomi = ["Akela", "Baloo", "Chil", "Kaa", "Raksha", "Arcanda", "Sciba", "Scoiattoli", "Mi", "Mowgli"]
    colori = ["Rosso", "Blu", "Verde", "Giallo", "Arancione", "Viola", "Rosa", "Marrone", "Grigio", "Nero"]
    return f"{random.choice(nomi)}{random.choice(colori)}"

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/dashboard")
@login_required
def dashboard():
    return render_template("dashboard.html", stato=StatusPercorso.query.all()[0].stato)

@app.route("/stato_iscrizioni", methods=["GET", "POST"])
@login_required
def stato_iscrizioni():
    if current_user.livello == "iabz" or current_user.livello == "pattuglia":
        return redirect(url_for("dashboard"))
    stato = StatusPercorso.query.all()[0]
    if request.method == "POST":
        if request.form["stato"] == "sospendi":
            stato.stato = False
            db.session.commit()
        if request.form["stato"] == "apri":
            stato.stato = True
            db.session.commit()
        return redirect(url_for("stato_iscrizioni"))
    return render_template("stato_iscrizioni.html", stato=stato.stato)

@app.route("/iscrizioni")
@login_required
def iscrizioni():
    limita = False
    if current_user.livello == "iabz":
        limita = True
    iscritti = []
    tmp_iscritti=IscrizioniEG.query.all()
    for i in tmp_iscritti:
        if limita and i.zona != current_user.zona:
            continue
        iscritti.append(i)
    return render_template("iscrizioni.html", iscritti=iscritti)

@app.route("/dettagli/<id_iscrizione>")
@login_required
def dettagli(id_iscrizione):
    return render_template("dettaglio_iscrizione.html", iscrizione=IscrizioniEG.query.filter_by(id=int(id_iscrizione)).first())

@app.route("/elimina/<id_iscrizione>", methods=["GET", "POST"])
@login_required
def elimina(id_iscrizione):
    if request.method == "POST":
        return redirect(url_for("iscrizioni"))
    return render_template("elimina.html", iscrizione=IscrizioniEG.query.filter_by(id=int(id_iscrizione)).first())

# Endpoint da terminare!
@app.route("/abilita/<id_iscrizione>", methods=["GET", "POST"])
@login_required
def abilita(id_iscrizione):
    creds = f"{cr['wordpress']['user']}:{cr['wordpress']['passwd']}"
    token = base64.b64encode(creds.encode())
    header = {"Authorization": f"Basic {token.decode('utf-8')}"}
    tmp_iscrizione = IscrizioniEG.query.filter_by(id=id_iscrizione).first()
    tmp_username = f"{tmp_iscrizione.nome}_{tmp_iscrizione.gruppo}".replace(" ", "_").lower()
    tmp_passwd = genera_password_sq()
    response = requests.get(cr["wordpress"]["url"]+"/users", headers=header)
    valid_username = True
    for i in response.json():
        if i["slug"] == tmp_username:
            valid_username = False
    if request.method == "POST":
        try:
            print(request.form["username"])
        except KeyError:
            print(tmp_username)
        valid_username = False
    return render_template("abilita.html", iscrizione=tmp_iscrizione, username=tmp_username, valid_username=valid_username)

@app.route("/mail")
@login_required
def mail():
    if (current_user.livello != "iabr") and (current_user.livello != "admin"):
        print(current_user.livello)
        return redirect(url_for("dashboard"))
    return render_template("testi_mail.html", testi_mail=TestiMail.query.all())

@app.route("/crea_mail", methods=["GET", "POST"])
@login_required
def crea_mail():
    if (current_user.livello != "iabr") and (current_user.livello != "admin"):
        return redirect(url_for("dashboard"))
    if request.method == 'POST':
        testo_mail = TestiMail(data=str(datetime.now()), stato=False, destinatari=False, titolo=request.form["titolo"], testo=request.form["ckeditor"])
        db.session.add(testo_mail)
        db.session.commit()
    return render_template("testo_mail.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if len(User.query.all()) == 0:
        return render_template("welcome.html")
    if request.method == "POST":
        utente = User.query.filter_by(username=request.form["username"]).first()
        if utente:
            if check_password_hash(utente.password, request.form["passwd"]):
                login_user(utente)
                return redirect(url_for("dashboard"))
            else:
                flash("Username o Password errati!", "warning")
        else:
            flash("Utente inesistente!", "warning")
    return render_template("login.html")

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("dashboard"))

@app.route("/admin", methods=["GET", "POST"])
@login_required
def admin():
    if current_user.livello != "admin":
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        if request.form["id_form"] == "nuovo_utente":
            utente = User.query.filter_by(username=request.form["username"]).first()
            if utente is None:
                alphabet = string.ascii_letters + string.digits
                tmp_password = ''.join(secrets.choice(alphabet) for i in range(12))
                password = generate_password_hash(tmp_password)
                if request.form["livello"] == "iabz":
                    utente = User(username=request.form["username"], password=password, mail=request.form["mail"], livello=request.form["livello"], zona=request.form["zona"], telegram_id=request.form["telegram_id"])
                else:
                    utente = User(username=request.form["username"], password=password, mail=request.form["mail"], livello=request.form["livello"], telegram_id=request.form["telegram_id"])
                db.session.add(utente)
                db.session.commit()
                flash("Utente inserito con successo!", "success")

                testo_mail = f"Benvenuto {utente.username},<br>la presente per confermarti la creazione dell'account sul Gestionale Guidoncini Verdi 2024!<br>Il Gestionale è la piattaforma usata per gestire le iscrizioni dei ragazzi e il nuovissimo sito <a href=\"guidonciniverdi.it\" target=\"_blank\">guidonciniverdi.it</a>.<hr><h4><strong>Dettagli Iscrizione</strong></h4><br>Username: {utente.username}<br>Password provvisoria: {tmp_password}<br>Per accedere al gestionale puoi cliccare a questo <a href=\"guidonciniverdi.pythonanywhere.com/dashboard\" target=\"_blank\">link</a>"

                if manda_mail([utente.mail], [], "Conferma Creazione Account", testo_mail):
                    flash("Mail inviata!", "success")
                else:
                    flash("Qualcosa è andato storto con la mail...", "warning")
                if utente.telegram_id:
                    testo_telegram = f"Benvenuto {utente.username},\nla presente per confermarti la creazione dell'account sul Gestionale Guidoncini Verdi 2024!\nIl Gestionale è la piattaforma usata per gestire le iscrizioni dei ragazzi e il nuovissimo sito guidonciniverdi.it.\n\nDettagli Iscrizione\nUsername: {utente.username}\nPassword provvisoria: {tmp_password}\nPer accedere al gestionale puoi cliccare a questo link: guidonciniverdi.pythonanywhere.com/dashboard"
                    if manda_telegram(utente.telegram_id, "Conferma Creazione Account", testo_telegram):
                        flash("Notifica telegram inviata!", "success")
                    else:
                        flash("Qualcosa è andato storto con la notifica telegram...", "warning")
            else:
                flash(f"Esiste già l'utente {request.form['username']}!", "warning")
        return redirect(url_for("admin"))
    return render_template("admin.html", utenti=User.query.all(), gruppi=gruppi)

@app.route("/utente", methods=["GET", "POST"])
@login_required
def utente():
    if request.method == "POST":
        if request.form["id_form"] == "aggiorna_utente":
            utente = User.query.filter_by(username=current_user.username).first()
            if request.form["passwd"] == request.form["conferma_passwd"] and check_password_hash(utente.password, request.form["old_passwd"]):
                utente.password = generate_password_hash(request.form["passwd"])
                db.session.commit()
            else:
                flash("Le password non coincidono!", "warning")
        return redirect(url_for("utente"))
    return render_template("utente.html")

@app.route("/welcome", methods=["POST"])
def welcome():
    if len(User.query.all()) > 0:
        return redirect(url_for("login"))
    if request.form["passwd"] == request.form["conferma_passwd"]:
        password = generate_password_hash(request.form["passwd"])
        utente = User(username=request.form["username"], password=password, mail=request.form["mail"], livello="admin", telegram_id=request.form["telegram_id"])
        db.session.add(utente)
        status = StatusPercorso(stato=False, data_apertura="", data_chiusura="")
        db.session.add(status)
        db.session.commit()
        flash("Utente creato con successo!", "success")
    else:
        flash("Le password non coincidono!", "warning")
    return redirect(url_for("login"))

@app.route("/iscriviti", methods=["GET", "POST"])
def iscriviti():
    if request.method == "POST":
        try:
            iscrizione = IscrizioniEG(data=str(datetime.now()), stato="da_abilitare", nome=request.form["nome_squadriglia"].capitalize(), mail=request.form["mail_squadriglia"], zona=request.form["zona"], gruppo=request.form["gruppo"], specialita=request.form["specialita"], tipo=request.form["conquista_conferma"], nome_capo_sq=request.form["nome_capo_squadriglia"], nome_capo1=request.form["nome_capo_rep1"], mail_capo1=request.form["mail_rep1"], cell_capo1=request.form["numero_rep1"], nome_capo2=request.form["nome_capo_rep2"], mail_capo2=request.form["mail_rep2"], cell_capo2=request.form["numero_rep2"])
            db.session.add(iscrizione)
            db.session.commit()
        except:
            flash("Iscrizione fallita. Riprovaci!", "warning")
            return redirect(url_for("iscriviti"))

        testo_mail_sq = f"Congratulazioni {iscrizione.nome},<br>la vostra iscrizione al percorso Guidoncini Verdi 2024 è stata registrata!<br>Nelle prossime settimane riceverete una mail con le credenziali per accere al vostro Diario di Bordo Digitale, nell'attesa potete iniziare a scoprire il nostro nuovissimo sito <a href=\"https://guidonciniverdi.it/\" target=\"_blank\">guidonciniverdi.it</a>.<hr><h4><strong>Dettagli Iscrizione</strong></h4>Zona: {iscrizione.zona}<br>Gruppo: {iscrizione.gruppo}<br>Ambito scelto: {iscrizione.specialita} - {iscrizione.tipo}"
        manda_mail([iscrizione.mail], [iscrizione.mail_capo1, iscrizione.mail_capo2], "Iscrizione completata!", testo_mail_sq)

        return redirect(url_for("iscriviti_success"))
    if not StatusPercorso.query.all()[0].stato:
        stato = StatusPercorso.query.all()[0]
        msg = ""
        if stato.data_apertura == "":
            msg = "Le iscrizioni apriranno nei prossimi giorni!"
        elif stato.data_chiusura == "":
            msg = "Le iscrizioni sono momentaneamente chiuse per problemi tecnici, riapriranno a breve!"
        else:
            msg = "Ops, le iscrizioni sono già terminate!"
        return render_template("iscriviti_chiuse.html", msg=msg)
    return render_template("iscriviti.html", gruppi=gruppi, specialita=specialita)

@app.route("/iscriviti_success")
def iscriviti_success():
    return render_template("iscriviti_success.html")

@app.errorhandler(404)
def page_not_found(e):
    return render_template("errore_generico.html"), 404

@app.errorhandler(405)
def internal_error(e):
    return render_template("errore_generico.html"), 405

@app.errorhandler(500)
def internal_error(e):
    return render_template("errore_generico.html"), 500

if __name__ == "__main__":
    app.run(port=8000, host="0.0.0.0")
