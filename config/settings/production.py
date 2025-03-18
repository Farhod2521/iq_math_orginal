# config/settings/production.py
from .base import *
import os
from dotenv import load_dotenv
DEBUG = False

ALLOWED_HOSTS = ['*']


load_dotenv() 

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': os.getenv('DB_NAME'),
        'USER': os.getenv('DB_USER'),
        'PASSWORD': os.getenv('DB_PASSWORD'),
        'HOST': os.getenv('DB_HOST', 'localhost'),
        'PORT': os.getenv('DB_PORT', '3306'),
        'OPTIONS': {
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES'"
        }
    }
}

CSRF_TRUSTED_ORIGINS = [
    "https://backend.iq-math.uz",
    "https://www.backend.iq-math.uz",
    "http://127.0.0.1:8000",
    "http://localhost:8000",
]
# SECURE_BROWSER_XSS_FILTER = True
# SECURE_CONTENT_TYPE_NOSNIFF = True
# SESSION_COOKIE_SECURE = True
# CSRF_COOKIE_SECURE = True
# X_FRAME_OPTIONS = 'DENY'
