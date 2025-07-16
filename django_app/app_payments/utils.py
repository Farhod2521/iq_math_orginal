# utils.py

import requests

# MULTICARD_AUTH_URL = "https://mesh.multicard.uz/auth"
# APPLICATION_ID = "raqamli_iqtisodiyot_va_agrotexnologiyalar_universiteti"
# SECRET_KEY = "b7lydo1mu8abay9x"


MULTICARD_AUTH_URL = "https://mesh.multicard.uz/auth"
APPLICATION_ID = "udea"
SECRET_KEY = "n4eci720czqjlo2t"
def get_multicard_token():
    response = requests.post(MULTICARD_AUTH_URL, json={
        "application_id": APPLICATION_ID,
        "secret": SECRET_KEY
    })
    if response.status_code == 200:
        return response.json().get("token")
    else:
        raise Exception("Multicard token olishda xatolik yuz berdi")
