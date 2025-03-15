import requests
import uuid  # Unikal ID yaratish uchun
import os
from dotenv import load_dotenv
def send_sms(phone, sms_code):
    url = os.getenv("SMS_URL")
    headers = {
        "Content-Type": "application/json"
    }

    data = {
        "header": {
            "login": os.getenv("SMS_LOGIN"),
            "pwd": os.getenv("SMS_PASSWORD"),
            "CgPN": "IQMATH"
        },
        "body": {
            "message_id_in": str(uuid.uuid4()),  
            "CdPN": phone, 
            "text": f"IQMATH.UZ Saytidan ro‘yxatdan o‘tish uchun. Diqqat, kodni hech kimga aytmang. "
                    f"Dlya registratsii na sayte IQMATH.UZ. Vnimanie, ne soobshayte kod nikomu. Kod: {sms_code}"
        }
    }

    response = requests.post(url, json=data, headers=headers)

    print(f"SMS Status: {response.status_code}, Response: {response.text}")
    return response.status_code == 200  # True agar muvaffaqiyatli bo‘lsa

def send_sms_resend(phone, sms_code):
    url = os.getenv("SMS_URL")
    headers = {
        "Content-Type": "application/json"
    }

    data = {
        "header": {
            "login": os.getenv("SMS_LOGIN"),
            "pwd": os.getenv("SMS_PASSWORD"),
            "CgPN": "IQMATH"
        },
        "body": {
            "message_id_in": str(uuid.uuid4()),  # Unikal message_id_in
            "CdPN": phone,  # Telefon raqamini to'g'rilang
            "text": f"IQMATH.UZ Saytidagi parolni qayta tiklash uchun. Diqqat! kodni hech kimga aytmang. "
                    f"Dlya vosstanovleniya parolya na sayte IQMATH.UZ. Vnimanie! Ne soobshayte kod nikomu.Kod: {sms_code}"
        }
    }

    response = requests.post(url, json=data, headers=headers)

    print(f"SMS Status: {response.status_code}, Response: {response.text}")
    return response.status_code == 200  # True agar muvaffaqiyatli bo‘lsa



import threading
from django.core.mail import send_mail as django_send_mail
from django.conf import settings

def send_verification_email(email, sms_code):
    subject  = "IQ-MATH.UZ"
    message = f"IQ-MATH.UZ Saytidan ro‘yxatdan o‘tish uchun. Diqqat, kodni hech kimga aytmang. Dlya registratsii na sayte IQMATH.UZ. Vnimanie, ne soobshayte kod nikomu. Kod: {sms_code}"
    
    # Emailni alohida thread orqali jo‘natish
    thread = threading.Thread(target=django_send_mail, args=(subject, message, settings.EMAIL_HOST_USER, [email]))
    thread.start()



def send_login_parol_email(email, login,password):
    subject =  "IQ-MATH.UZ"
    message  = f"IQ-MATH.UZ Saytidan ro‘yxatdan o‘tdingiz.\n Sizning login:{login}, parol: {password}"
    thread = threading.Thread(target=django_send_mail, args=(subject, message, settings.EMAIL_HOST_USER, [email]))
    thread.start()


def send_login_parol_resend_email(email, login,password):
    subject =  "IQ-MATH.UZ"
    message  = f"Hurmatli foydalanuvchi iq-math.uz saytidagi parolingiz yangilandi.\nlogin:{login}\nparol: {password}"
    thread = threading.Thread(target=django_send_mail, args=(subject, message, settings.EMAIL_HOST_USER, [email]))
    thread.start()