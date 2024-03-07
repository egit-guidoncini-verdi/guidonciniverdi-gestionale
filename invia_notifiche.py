#!/bin/python3

import requests
import json

url = "https://guidonciniverdi.pythonanywhere.com/notifica"

with open("credenziali_notifiche.json", "r") as f:
    dati = f.read()

api_key = json.loads(dati)["api_key"]

form = {"api_key": api_key, "tipologia": "admin"}

response = requests.post(url, data=form)

print(response.json())
