# config/settings/production.py
from .base import *
import os
from dotenv import load_dotenv
DEBUG = True

ALLOWED_HOSTS = ['*']


load_dotenv() 

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('DB_NAME'),
        'USER': os.getenv('DB_USER'),
        'PASSWORD': os.getenv('DB_PASSWORD'),
        'HOST': os.getenv('DB_HOST', 'localhost'),
        'PORT': os.getenv('DB_PORT', '5432'),
    }
}


ASGI_APPLICATION = "config.routing.application"

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [("127.0.0.1", 6379)]
        },
    },
}
CSRF_TRUSTED_ORIGINS = [
    "https://backend.iq-math.uz",
    "https://www.backend.iq-math.uz",
    "http://127.0.0.1:8000",
    "http://localhost:8000",
]
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
X_FRAME_OPTIONS = 'DENY'
