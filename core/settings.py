import os
from pathlib import Path

import dj_database_url
from django.core.exceptions import ImproperlyConfigured

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


def env_bool(name, default=False):
    return os.environ.get(name, str(default)).strip().lower() in ('1', 'true', 'yes', 'on')


def env_list(name):
    return [item.strip() for item in os.environ.get(name, '').split(',') if item.strip()]


def as_hostname(value):
    """Reduce a pasted URL to the bare hostname ALLOWED_HOSTS matches against.

    'https://app.onrender.com/' and 'app.onrender.com:443' both become
    'app.onrender.com'. Django compares ALLOWED_HOSTS against the Host header
    with the port already stripped, so a scheme or trailing slash left in the
    environment variable silently rejects every request with a bare 400.
    """
    host = value.split('://', 1)[-1].split('/', 1)[0].strip().rstrip('.').lower()
    if host.startswith('['):  # bracketed IPv6 literal, e.g. [::1]:8000
        return host.split(']', 1)[0] + ']'
    return host.rsplit(':', 1)[0] if host.count(':') == 1 else host


def as_origin(value, default_scheme):
    """Ensure a CSRF trusted origin carries a scheme, as Django 4+ requires.

    Django matches trusted origins as exact strings, so the scheme and host are
    lowercased to keep a capitalised environment value from failing to match.
    """
    value = value.strip().rstrip('/').lower()
    return value if '://' in value else f'{default_scheme}://{value}'


# ==========================================
# 1. إعدادات الأمان (Security)
# ==========================================
DEBUG = env_bool('DJANGO_DEBUG', False)

SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY')
if not SECRET_KEY:
    if not DEBUG:
        raise ImproperlyConfigured(
            'DJANGO_SECRET_KEY must be set when DJANGO_DEBUG is off. '
            'Generate one with: python -c "from django.core.management.utils '
            'import get_random_secret_key; print(get_random_secret_key())"'
        )
    SECRET_KEY = 'django-insecure-development-only-do-not-use-in-production'

ALLOWED_HOSTS = [as_hostname(host) for host in env_list('DJANGO_ALLOWED_HOSTS')]

# Render publishes the service's own hostname. Trusting it removes the most
# common deployment failure: a mistyped DJANGO_ALLOWED_HOSTS turning every
# request into a bare 400. Any other platform still configures it explicitly.
PLATFORM_HOSTNAME = os.environ.get('RENDER_EXTERNAL_HOSTNAME', '').strip()
if PLATFORM_HOSTNAME:
    PLATFORM_HOSTNAME = as_hostname(PLATFORM_HOSTNAME)
    if PLATFORM_HOSTNAME not in ALLOWED_HOSTS:
        ALLOWED_HOSTS.append(PLATFORM_HOSTNAME)

if not ALLOWED_HOSTS:
    if not DEBUG:
        raise ImproperlyConfigured(
            'DJANGO_ALLOWED_HOSTS must list the hostnames this server answers on, '
            'e.g. DJANGO_ALLOWED_HOSTS=hr.aseer.local,10.0.0.15'
        )
    ALLOWED_HOSTS = ['localhost', '127.0.0.1', '[::1]']

# Set DJANGO_SECURE_SSL=True once the site is served over HTTPS. It is off by
# default because the internal deployment may still be plain HTTP, and marking
# cookies Secure there would silently break every login.
USE_HTTPS = env_bool('DJANGO_SECURE_SSL', False)

# Origins trusted for POST/CSRF, e.g. https://hr.aseer.local,http://10.0.0.15
CSRF_TRUSTED_ORIGINS = [
    as_origin(origin, 'https' if USE_HTTPS else 'http')
    for origin in env_list('DJANGO_CSRF_TRUSTED_ORIGINS')
]
if PLATFORM_HOSTNAME:
    platform_origin = f'https://{PLATFORM_HOSTNAME}'
    if platform_origin not in CSRF_TRUSTED_ORIGINS:
        CSRF_TRUSTED_ORIGINS.append(platform_origin)

SESSION_COOKIE_SECURE = USE_HTTPS
CSRF_COOKIE_SECURE = USE_HTTPS
SECURE_SSL_REDIRECT = USE_HTTPS
if USE_HTTPS:
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True

SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_SAMESITE = 'Lax'
SESSION_COOKIE_AGE = 60 * 60 * 8
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_SAVE_EVERY_REQUEST = True

SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = 'same-origin'
X_FRAME_OPTIONS = 'DENY'

# Bound request bodies so a crafted form cannot exhaust memory.
DATA_UPLOAD_MAX_NUMBER_FIELDS = 1000
DATA_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024

# Failed-login attempts allowed per username+IP before a temporary lockout.
LOGIN_ATTEMPT_LIMIT = int(os.environ.get('DJANGO_LOGIN_ATTEMPT_LIMIT', '10'))
LOGIN_ATTEMPT_TIMEOUT = int(os.environ.get('DJANGO_LOGIN_ATTEMPT_TIMEOUT', '900'))

# ==========================================
# 2. التطبيقات والبرمجيات الوسيطة
# ==========================================
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # تطبيقاتنا
    'employees',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'core.urls'

# ==========================================
# 3. إعدادات القوالب (Templates)
# ==========================================
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'core.wsgi.application'

# ==========================================
# 4. قاعدة البيانات (Database)
# ==========================================
DATABASES = {
    'default': dj_database_url.config(
        default='sqlite:///' + str(BASE_DIR / 'db.sqlite3'),
        conn_max_age=600,
        ssl_require=env_bool('DJANGO_DB_SSL_REQUIRE', False),
    )
}

# ==========================================
# 5. كلمات المرور واللغة (Localization)
# ==========================================
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {'min_length': 10},
    },
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'ar'
TIME_ZONE = 'Asia/Riyadh'
USE_I18N = True
USE_TZ = True

# ==========================================
# 6. الملفات الثابتة والمرفقات (Static & Media)
# ==========================================
STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

if not DEBUG:
    STORAGES = {
        'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
        'staticfiles': {'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage'},
    }

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# ==========================================
# 7. إعدادات متنوعة
# ==========================================
EMAIL_BACKEND = os.environ.get(
    'DJANGO_EMAIL_BACKEND', 'django.core.mail.backends.console.EmailBackend'
)

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'dashboard'
LOGOUT_REDIRECT_URL = 'login'

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {'class': 'logging.StreamHandler'},
    },
    'root': {'handlers': ['console'], 'level': 'INFO'},
    'loggers': {
        'django.security': {'handlers': ['console'], 'level': 'WARNING', 'propagate': False},
    },
}
