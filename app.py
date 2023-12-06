from flask import Flask, render_template, redirect, jsonify, request, url_for, flash, send_from_directory, send_file
from flask_login import UserMixin, login_user, LoginManager, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from flask_sqlalchemy import SQLAlchemy
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

@app.route("/")
@login_required
def index():
    return render_template("index.html")

@app.route("/iscrizioni")
@login_required
def iscrizioni():
    return render_template("iscrizioni.html")

@app.route("/upload_iscrizioni", methods=["POST"])
@login_required
def upload_iscrizioni():
    soci = pd.read_excel(request.files["file"])
    print(soci)
    flash("File caricato con successo!", "success")
    return redirect(url_for("iscrizioni"))

@app.route("/login", methods=["GET", "POST"])
def login():
    if len(User.query.all()) == 0:
        return render_template("welcome.html")
    if request.method == "POST":
        utente = User.query.filter_by(username=request.form["username"]).first()
        if utente:
            if check_password_hash(utente.password, request.form["passwd"]):
                login_user(utente)
                return redirect(url_for("index"))
            else:
                flash("Username o Password errati!", "warning")
        else:
            flash("Utente inesistente!", "warning")
    return render_template("login.html")

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("index"))

@app.route("/admin", methods=["GET", "POST"])
@login_required
def admin():
    if request.method == "POST":
        if request.form["id_form"] == "nuovo_utente":
            utente = User.query.filter_by(username=request.form["username"]).first()
            if utente is None:
                password = generate_password_hash(request.form["passwd"])
                utente = User(username=request.form["username"], password=password)
                db.session.add(utente)
                db.session.commit()
                flash("Utente inserito con successo!", "success")
            else:
                flash("Esiste già l'utente "+request.form["username!"], "warning")
    return render_template("admin.html", utenti=User.query.all())

@app.route("/welcome", methods=["POST"])
def welcome():
    if len(User.query.all()) > 0:
        return redirect(url_for("login"))
    if request.form["passwd"] == request.form["conferma_passwd"]:
        password = generate_password_hash(request.form["passwd"])
        utente = User(username=request.form["username"], password=password)
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
        return redirect(url_for("iscriviti_success"))
    return render_template("iscriviti.html", gruppi=gruppi, specialita=specialita)

@app.route("/iscriviti_success")
def iscriviti_success():
    return render_template("iscriviti_success.html")

if __name__ == "__main__":
    app.run(port=8000, host="0.0.0.0")
