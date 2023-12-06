from flask import Flask, render_template, redirect, jsonify, request, url_for, flash, send_from_directory, send_file
from flask_login import UserMixin, login_user, LoginManager, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from flask_sqlalchemy import SQLAlchemy
#from apiclient import discovery
#from httplib2 import Http
#from oauth2client import client, file, tools
import pprint
import pickle
import pandas as pd
import datetime
import requests
import secrets
import base64
import json

pp = pprint.PrettyPrinter(indent=4)

with open("credenziali.json", "r") as f:
    cr = json.load(f)

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
    form_id = db.Column(db.Integer, nullable=False)
    nome = db.Column(db.String(128), nullable=False)
    mail = db.Column(db.String(128), nullable=False)
    zona = db.Column(db.String(128), nullable=False)
    gruppo = db.Column(db.String(128), nullable=False)
    specialita = db.Column(db.String(128), nullable=False)
    # tipo indica se conquista o conferma => True se conferma
    tipo = db.Column(db.Boolean, nullable=False)

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
    '''
    store = file.Storage("token.json")
    creds = None
    if not creds or creds.invalid:
        flow = client.flow_from_clientsecrets("credentials.json", cr["form"]["scopes"])
        creds = tools.run_flow(flow, store)

    service = discovery.build(
        "forms",
        "v1",
        http=creds.authorize(Http()),
        discoveryServiceUrl=cr["form"]["discovery_doc"],
        static_discovery=False,
    )

    # Prints the responses of your specified form:
    #form_id = "1sWrdk6uWvrEKqo0ozD3TJQXi2XDTjdNDAEgCjgE0WyM"
    # result = service.forms().responses().list(formId=form_id).execute()
    result = service.forms().responses().list(formId=cr["form"]["form_id"]).execute()
    pp.pprint(result)
    '''
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

if __name__ == "__main__":
    app.run(port=8000, host="0.0.0.0")
