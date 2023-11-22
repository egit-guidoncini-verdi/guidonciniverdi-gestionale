import requests
import json
import base64

url = "https://guidonciniverdi.it/wp-json/wp/v2"

user = "admin"
passwd = "API_CODE"

creds = user + ":" + passwd

token = base64.b64encode(creds.encode())

header = {"Authorization": "Basic" + token.decode("utf-8")}

dati = {
    "username": "alati",
    "email": "123@gmail.com",
    "password": "ciaomondo"
    }

response = requests.post(url+"/users", headers=header, json=dati)

print(response.json())
