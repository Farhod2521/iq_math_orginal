# utils.py

import requests

MULTICARD_AUTH_URL = "https://dev-mesh.multicard.uz/auth"
APPLICATION_ID = "rhmt_test"
SECRET_KEY = "Pw18axeBFo8V7NamKHXX"

def get_multicard_token():
    response = requests.post(MULTICARD_AUTH_URL, json={
        "application_id": APPLICATION_ID,
        "secret": SECRET_KEY
    })
    if response.status_code == 200:
        return response.json().get("token")
    else:
        raise Exception("Multicard token olishda xatolik yuz berdi")
