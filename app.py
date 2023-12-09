from flask import Flask, render_template, redirect, jsonify, request, url_for, flash, send_from_directory, send_file
from flask_login import UserMixin, login_user, LoginManager, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from flask_sqlalchemy import SQLAlchemy
import smtplib, ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import pandas as pd
import datetime
import requests
import secrets
import base64
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

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] =  "sqlite:///gv_db.db"
app.config["SECRET_KEY"] = secrets.token_hex()
db = SQLAlchemy(app)

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(128), nullable=False, unique=True)
    password = db.Column(db.String(128), nullable=False)
    mail = db.Column(db.String(128), nullable=False)
    zona = db.Column(db.String(128), nullable=True)
    livello = db.Column(db.String(128), nullable=False)

class IscrizioniEG(db.Model):
    id = db.Column(db.Integer, primary_key=True)
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
    iscrizioni_id = db.Column(db.Integer, nullable=False)
    wordpress_id = db.Column(db.Integer, nullable=False)
    username = db.Column(db.String(128), nullable=False)
    meta = db.Column(db.JSON, nullable=False)

class WordpressPost(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    iscrizioni_id = db.Column(db.Integer, nullable=False)
    wordpress_user_id = db.Column(db.Integer, nullable=False)
    wordpress_id = db.Column(db.Integer, nullable=False)
    # campo di testo per indicare se "presentazione", "prima_impresa", "seconda_impresa", "missione", "extra"
    tipo = db.Column(db.String(128), nullable=False)
    meta = db.Column(db.JSON, nullable=False)

with app.app_context():
    db.create_all()

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def manda_mail(indirizzo, titolo, testo):
    message = MIMEMultipart("alternative")
    message["Subject"] = f"Guidoncini Verdi 2024 - {titolo}"
    message["From"] = cr["mail"]["sender_email"]
    message["To"] = indirizzo

    text = f"{titolo}\n{testo}"
    html = render_template("mail_base.html", titolo=titolo, testo=testo)

    part1 = MIMEText(text, "plain")
    part2 = MIMEText(html, "html")

    message.attach(part1)
    message.attach(part2)

    context = ssl.create_default_context()
    try:
        with smtplib.SMTP(cr["mail"]["smtp_server"], cr["mail"]["port"]) as server:
            server.ehlo()  # Can be omitted
            server.starttls(context=context)
            server.ehlo()  # Can be omitted
            server.login(cr["mail"]["sender_email"], cr["mail"]["passwd"])
            server.sendmail(cr["mail"]["sender_email"], indirizzo, message.as_string())
        return True
    except:
        return False

@app.route("/")
def index():
    return redirect(url_for("iscriviti"))

@app.route("/dashboard")
@login_required
def dashboard():
    return render_template("dashboard.html")

@app.route("/iscrizioni")
@login_required
def iscrizioni():
    limita = False
    if current_user.livello == "iabz":
        limita = True
    iscritti = []
    tmp_iscritti=IscrizioniEG.query.all()
    utenti_wp=WordpressUser.query.all()
    for i in utenti_wp:
        print(i.iscrizioni_id)
    for i in tmp_iscritti:
        abilitato = False
        for y in utenti_wp:
            if y.iscrizioni_id == i.id:
                abilitato = y
        if limita and i.zona != current_user.zona:
            continue
        iscritti.append({"iscrizione": i, "utente_wp": abilitato})
    return render_template("iscrizioni.html", iscritti=iscritti)

@app.route("/dettagli/<id_iscrizione>")
@login_required
def dettagli(id_iscrizione):
    return render_template("dettaglio_iscrizione.html", iscrizione=IscrizioniEG.query.filter_by(id=int(id_iscrizione)).first())

@app.route("/abilita/<id_iscrizione>")
@login_required
def abilita(id_iscrizione):
    creds = f"{cr['wordpress']['user']}:{cr['wordpress']['passwd']}"
    token = base64.b64encode(creds.encode())
    header = {"Authorization": f"Basic {token.decode('utf-8')}"}
    tmp_iscrizione = IscrizioniEG.query.filter_by(id=id_iscrizione).first()
    tmp_username = f"{tmp_iscrizione.nome}_{tmp_iscrizione.gruppo}".replace(" ", "_").lower()

    response = requests.get(cr["wordpress"]["url"]+"/users", headers=header)
    valid_username = True
    for i in response.json():
        if i["slug"] == tmp_username:
            valid_username = False
    return render_template("abilita.html", iscrizione=tmp_iscrizione, username=tmp_username, valid_username=valid_username).first())

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
            if request.form["passwd"] == request.form["conferma_passwd"]:
                if utente is None:
                    password = generate_password_hash(request.form["passwd"])
                    if request.form["livello"] == "iabz":
                        utente = User(username=request.form["username"], password=password, mail=request.form["mail"], livello=request.form["livello"], zona=request.form["zona"])
                    else:
                        utente = User(username=request.form["username"], password=password, mail=request.form["mail"], livello=request.form["livello"])
                    db.session.add(utente)
                    db.session.commit()
                    flash("Utente inserito con successo!", "success")
                else:
                    flash(f"Esiste già l'utente {request.form['username']}!", "warning")
            else:
                flash("Le password non coincidono!", "warning")
        return redirect(url_for("admin"))
    return render_template("admin.html", utenti=User.query.all(), gruppi=gruppi)

@app.route("/utente", methods=["GET", "POST"])
@login_required
def utente():
    if current_user.livello != "admin":
        return redirect(url_for("dashboard"))
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
        utente = User(username=request.form["username"], password=password, mail=request.form["mail"], livello="admin")
        db.session.add(utente)
        db.session.commit()
        flash("Utente creato con successo!", "success")
    else:
        flash("Le password non coincidono!", "warning")
    return redirect(url_for("login"))

@app.route("/iscriviti", methods=["GET", "POST"])
def iscriviti():
    if request.method == "POST":
        try:
            iscrizione = IscrizioniEG(nome=request.form["nome_squadriglia"], mail=request.form["mail_squadriglia"], zona=request.form["zona"], gruppo=request.form["gruppo"], specialita=request.form["specialita"], tipo=request.form["conquista_conferma"], nome_capo_sq=request.form["nome_capo_squadriglia"], nome_capo1=request.form["nome_capo_rep1"], mail_capo1=request.form["mail_rep1"], cell_capo1=request.form["numero_rep1"], nome_capo2=request.form["nome_capo_rep2"], mail_capo2=request.form["mail_rep2"], cell_capo2=request.form["numero_rep2"])
            db.session.add(iscrizione)
            db.session.commit()
        except:
            flash("Iscrizione fallita.<br>Riprovaci!", "warning")
            return redirect(url_for("iscriviti"))

        testo_mail_sq = f"Congratulazioni {iscrizione.nome},<br>la vostra iscrizione al percorso Guidoncini Verdi 2024 è stata registrata!<br>Nelle prossime settimane riceverete una mail con le credenziali per accere al vostro Diario di Bordo Digitale, nell'attesa potete iniziare a scoprire il nostro nuovissimo sito <a href=\"guidonciniverdi.it\" target=\"_blank\">guidonciniverdi.it</a>.<hr><h4><strong>Dettagli Iscrizione</strong></h4>Zona: {iscrizione.zona}<br>Gruppo: {iscrizione.gruppo}<br>Ambito scelto: {iscrizione.specialita} - {iscrizione.tipo}"
        manda_mail(iscrizione.mail, "Iscrizione completata!", testo_mail_sq)

        testo_mail_capo1 = f"Congratulazioni {iscrizione.nome_capo1},<br>la squadriglia {iscrizione.nome} si è correttamente iscritta al percorso Guidoncini Verdi 2024<br>Se ritieni si tratti di un errore contattaci.<hr><h4><strong>Dettagli Iscrizione</strong></h4>Zona: {iscrizione.zona}<br>Gruppo: {iscrizione.gruppo}<br>Ambito scelto: {iscrizione.specialita} - {iscrizione.tipo}"
        manda_mail(iscrizione.mail_capo1, "Nuova Iscrizione", testo_mail_capo1)
        testo_mail_capo2 = f"Congratulazioni {iscrizione.nome_capo2},<br>la squadriglia {iscrizione.nome} si è correttamente iscritta al percorso Guidoncini Verdi 2024<br>Se ritieni si tratti di un errore contattaci.<hr><h4><strong>Dettagli Iscrizione</strong></h4>Zona: {iscrizione.zona}<br>Gruppo: {iscrizione.gruppo}<br>Ambito scelto: {iscrizione.specialita} - {iscrizione.tipo}"
        manda_mail(iscrizione.mail_capo2, "Nuova Iscrizione", testo_mail_capo2)


        return redirect(url_for("iscriviti_success"))
    return render_template("iscriviti.html", gruppi=gruppi, specialita=specialita)

@app.route("/iscriviti_success")
def iscriviti_success():
    return render_template("iscriviti_success.html")

if __name__ == "__main__":
    app.run(port=8000, host="0.0.0.0")
