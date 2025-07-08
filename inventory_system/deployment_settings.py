import os
import dj_database_url
from .settings import *
from .settings import BASE_DIR

ALLOWED_HOSTS = [os.environ.get('RENDER_EXTERNAL_HOSTNAME')]

DEBUG = False

# Handle missing SECRET_KEY gracefully
SECRET_KEY = os.environ.get('SECRET_KEY')

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.middleware.common.CommonMiddleware',
    # 'django.middleware.csrf.CsrfViewMiddleware',  # Removed CSRF middleware
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

STORAGES = {
    "default": {
        "BACKEND" : "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles" : {
        "BACKEND" : "whitenoise.storage.CompressedStaticFilesStorage"
    },
}

DATABASE_URL = os.environ.get('DATABASE_URL')

DATABASES = {
        'default' : dj_database_url.config(
            default = DATABASE_URL,
            conn_max_age = 600
        )
    }

CORS_ALLOWED_ORIGINS = [
    'https://inventory-frontend-odle.onrender.com',
    'https://inventory-frontend-odle.onrender.com',
    'https://inventory-frontend-odle.onrender.com',
]

CORS_ALLOW_CREDENTIALS = True

# Additional CORS settings for production
CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOWED_ORIGIN_REGEXES = [
    r"^https://.*\.onrender\.com$",
]
