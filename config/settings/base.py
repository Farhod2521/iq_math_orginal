# config/settings/base.py
from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent.parent.parent

SECRET_KEY = 'django-insecure-qt_8=(jct5oh3csd@rq&ns*7mph&3k%xrja7n%m!@+m97@d!n='

INSTALLED_APPS = [
    "jazzmin",
    'modeltranslation',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    ###########  LIBARY ##############
    'rest_framework',
    'rest_framework.authtoken',
    'corsheaders',
    'drf_yasg',
    'rest_framework_simplejwt',
    'ckeditor',
    'ckeditor_uploader',
    'django_user_agents',
    "channels",

    ############## APP ###############
    "django_app.app_user",
    "django_app.app_teacher",
    "django_app.app_student",
    "django_app.app_payments",
    "django_app.app_management",
    "django_app.app_tutor",
    "django_app.app_chat",
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django_user_agents.middleware.UserAgentMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]
REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.AllowAny',
    ],
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
        # 'rest_framework.authentication.BasicAuthentication',
        'rest_framework.authentication.TokenAuthentication',
    ],
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
}
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.memcached.PyMemcacheCache',
        'LOCATION': '127.0.0.1:11211',  # Memcached server IP manzili
    }
}
ROOT_URLCONF = 'config.urls'
CORS_ALLOW_ALL_ORIGINS = True
# CORS_ALLOWED_ORIGINS = [
#     "https://tmsiti.uz", 
#     "https://tmsiti.vercel.app",
#     "http://127.0.0.1:5500",
#     "http://localhost:3000",


# ]
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR,  "templates")],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

LANGUAGE_CODE = 'uz'

TIME_ZONE = 'Asia/Tashkent'

USE_I18N = True
USE_L10N = True

LANGUAGES = (
    ('uz', 'Uzbek'),
    ('ru', 'Russion'),
)

LOCALE_PATHS = [
    BASE_DIR / 'locale/',
]
MODELTRANSLATION_DEFAULT_LANGUAGE = 'uz'

STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'static'),
]
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

AUTH_USER_MODEL = 'app_user.User'








CKEDITOR_UPLOAD_PATH = ""



EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'

EMAIL_HOST = 'smtp.gmail.com'
EMAIL_HOST_USER = 'iqmathuzbekiston@gmail.com'
EMAIL_HOST_PASSWORD = 'yjvncncczivycepn'
EMAIL_PORT = 587

EMAIL_USE_TLS = True
EMAIL_USE_SSL = False

CKEDITOR_BASEPATH = "/static/ckeditor/ckeditor/"

CKEDITOR_ALLOW_NONIMAGE_FILES = True

CKEDITOR_CONFIGS = {
    "default": {
        # 🔧 Asosiy sozlamalar
        "skin": "moono",
        "height": 350,
        "width": "100%",
        "tabSpaces": 4,

        # ❗ IFRAME VA HTMLNI O‘CHIRMASLIK
        "allowedContent": True,
        "extraAllowedContent": "iframe[*]; div[*]; span[*]",

        # 🧰 Toolbar
        "toolbar": "Custom",

        "toolbar_Custom": [
            ["Source", "-", "Undo", "Redo"],
            ["Bold", "Italic", "Underline", "Strike"],
            ["NumberedList", "BulletedList", "-", "Outdent", "Indent"],
            ["JustifyLeft", "JustifyCenter", "JustifyRight", "JustifyBlock"],
            ["Link", "Unlink", "Anchor"],
            ["Image", "Table", "HorizontalRule", "Smiley", "SpecialChar"],
            ["Iframe", "Youtube"],  # 🎬 IFRAME + YOUTUBE
            ["Styles", "Format", "Font", "FontSize"],
            ["TextColor", "BGColor"],
            ["Maximize", "ShowBlocks"],
        ],

        # 🔌 Pluginlar (FAQAT KERAKLILARI)
        "extraPlugins": ",".join([
            "iframe",
            "youtube",
            "uploadimage",
            "autogrow",
            "widget",
            "mathjax",
            "codesnippet",
            "image2",
            "embed",
            "autoembed",
            "embedsemantic",
        ]),

        # 📐 MathJax
        "mathJaxLib": "https://cdn.jsdelivr.net/npm/mathjax@2/MathJax.js?config=TeX-AMS_HTML",

        # 📎 Media embed
        "mediaEmbed": {
            "previewsInData": True
        },
    }
}

CKEDITOR_RESTRICT_BY_USER = True

SESSION_ENGINE = "django.contrib.sessions.backends.db"  # Sessiyalarni bazada saqlash
SESSION_COOKIE_AGE = 86400  # 1 kun (sekundlarda)
SESSION_EXPIRE_AT_BROWSER_CLOSE = True  # Brauzer yopilganda sessiya tugashi
SESSION_SAVE_EVERY_REQUEST = True  # Har bir requestda sessiyani yangilash