"""
Django settings for ASMS project.
"""

from pathlib import Path
from django.utils.translation import gettext_lazy as _
from django.conf.locale import LANG_INFO
import dj_database_url 
import os # <--- ADDED FOR ENVIRONMENT VARIABLES

# ─────────────────────────────────────────────
# BASE
# ─────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent

# ─────────────────────────────────────────────
# SECURITY
# ─────────────────────────────────────────────
# Use environment variable for SECRET_KEY if available, otherwise use the insecure one for local dev
SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-replace-this-with-a-secure-key-in-production')

# Turn off DEBUG for production
DEBUG = os.environ.get('DEBUG', 'False') == 'True'

ALLOWED_HOSTS = ['*'] 

# ── NEW: FIX FOR 403 CSRF ERROR ──
# This tells Django to trust forms coming from your live Render URL
CSRF_TRUSTED_ORIGINS = [
    'https://asms-yute.onrender.com',
    'http://127.0.0.1:8000',
    'http://localhost:8000',
]

# ─────────────────────────────────────────────
# APPLICATIONS
# ─────────────────────────────────────────────
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'applications.apps.ApplicationsConfig',
]

# ─────────────────────────────────────────────
# MIDDLEWARE
# ─────────────────────────────────────────────
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware', 
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# ─────────────────────────────────────────────
# URLS & TEMPLATES
# ─────────────────────────────────────────────
ROOT_URLCONF = 'ASMS.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.template.context_processors.i18n',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'ASMS.wsgi.application'

# ─────────────────────────────────────────────
# DATABASE
# ─────────────────────────────────────────────
DATABASES = {
    'default': dj_database_url.config(
        default='sqlite:///' + str(BASE_DIR / 'db.sqlite3'),
        conn_max_age=600
    )
}

# ─────────────────────────────────────────────
# PASSWORD VALIDATION
# ─────────────────────────────────────────────
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# ─────────────────────────────────────────────
# CUSTOM USER MODEL
# ─────────────────────────────────────────────
AUTH_USER_MODEL = 'applications.User'

# ─────────────────────────────────────────────
# AUTHENTICATION BACKENDS
# ─────────────────────────────────────────────
AUTHENTICATION_BACKENDS = [
    'applications.backends.EmailOrPhoneOrUsernameBackend',
    'django.contrib.auth.backends.ModelBackend',
]

# ─────────────────────────────────────────────
# INTERNATIONALIZATION (LANGUAGES)
# ─────────────────────────────────────────────
LANGUAGE_CODE = 'en'

LANGUAGES = [
    ('en', _('English')),
    ('rw', _('Kinyarwanda')),
    ('fr', _('French')),
    ('sw', _('Swahili')),
]

LANG_INFO['rw'] = LANG_INFO['sw'].copy()
LANG_INFO['rw']['code'] = 'rw'
LANG_INFO['rw']['name'] = 'Kinyarwanda'
LANG_INFO['rw']['name_local'] = 'Ikinyarwanda'

LOCALE_PATHS = [
    BASE_DIR / 'locale',
]

TIME_ZONE = 'Africa/Kigali'
USE_I18N = True
USE_TZ = True

# ─────────────────────────────────────────────
# STATIC & MEDIA FILES
# ─────────────────────────────────────────────
STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# ─────────────────────────────────────────────
# DEFAULT PRIMARY KEY
# ─────────────────────────────────────────────
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ─────────────────────────────────────────────
# AUTH REDIRECTS
# ─────────────────────────────────────────────
LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'dashboard'
LOGOUT_REDIRECT_URL = 'login'

# ─────────────────────────────────────────────
# REAL EMAIL SETTINGS (GMAIL SMTP)
# ─────────────────────────────────────────────
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'vuganezaj5@gmail.com'
# Use environment variable for the password, or the hardcoded one for local testing
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', 'klsuatmgmfmlbncm')
DEFAULT_FROM_EMAIL = 'ASMS REMA <vuganezaj5@gmail.com>'

PASSWORD_RESET_TIMEOUT = 3600 
EMAIL_TIMEOUT = 10 

# ─────────────────────────────────────────────
# ASMS SYSTEM IDENTITY
# ─────────────────────────────────────────────
SYSTEM_NAME = "Authorization of Second-Hand Motorcycles System"
SYSTEM_SHORT_NAME = "ASMS"
SYSTEM_OWNER = "Rwanda Environment Management Authority (REMA)"
SYSTEM_VERSION = "1.0.0"