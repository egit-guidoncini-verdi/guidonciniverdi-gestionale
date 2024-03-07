#!/bin/python3

import requests
import json

url = "http://127.0.0.1:5000/notifica"

with open("credenziali_notifiche.json", "r") as f:
    dati = f.read()

api_key = json.loads(dati)["api_key"]

form = {"api_key": api_key, "tipologia": "admin"}

response = requests.post(url, data=form)

print(response.json())
