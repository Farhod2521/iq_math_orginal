# config/settings/production.py
from .base import *
import os

DEBUG = False

ALLOWED_HOSTS = ['yourdomain.com']

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',  # MySQL drayveri
        'NAME': os.getenv('DB_NAME'),         # MySQL ma'lumotlar bazasi nomi
        'USER': os.getenv('DB_USER'),         # MySQL foydalanuvchi nomi
        'PASSWORD': os.getenv('DB_PASSWORD'), # MySQL paroli
        'HOST': os.getenv('DB_HOST', 'localhost'), # Server manzili
        'PORT': os.getenv('DB_PORT', '3306'), # MySQL standart porti
        'OPTIONS': {
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES'"  # Ma'lumotlar integratsiyasini saqlash uchun
        }
    }
}
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
X_FRAME_OPTIONS = 'DENY'
