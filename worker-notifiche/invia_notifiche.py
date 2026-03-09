import requests
import json
import os

url = os.environ["URL_NOTIFICHE"]

api_key = os.environ["API_KEY"]

form = {"api_key": api_key, "tipologia": "iabz"}

response = requests.post(url, data=form)

print(response.json())