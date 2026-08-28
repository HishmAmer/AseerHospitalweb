import os
from pathlib import Path
import dj_database_url

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# ==========================================
# 1. إعدادات الأمان (Security)
# ==========================================
# قراءة المفتاح السري من بيئة السيرفر، مع مفتاح احتياطي لبيئة التطوير
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'django-insecure-kn-@%idya*ms!dbtko(@*o#%8s#zubfbb8j(9908+@*jhf=1=')

# إذا كنا على السيرفر الحقيقي، يمكنك جعل DJANGO_DEBUG=False لتفعيل وضع الإنتاج والأمان
DEBUG = True
# النطاقات المسموح بها (يقبل الكل للسيرفر الداخلي أو الشبكة المحلية)
ALLOWED_HOSTS = ['*'] if DEBUG else ['*']

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
    'whitenoise.middleware.WhiteNoiseMiddleware', # 👈 تم إضافته لعرض الملفات الثابتة بكفاءة على السيرفر الداخلي
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
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
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
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# ==========================================
# 5. كلمات المرور واللغة (Localization)
# ==========================================
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',},
]

LANGUAGE_CODE = 'ar' 
TIME_ZONE = 'Africa/Cairo' 
USE_I18N = True
USE_TZ = True

# ==========================================
# 6. الملفات الثابتة والمرفقات (Static & Media)
# ==========================================
STATIC_URL = 'static/'
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'static'),
]
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

# إعدادات WhiteNoise لتخزين وضغط الملفات الثابتة تلقائياً في وضع الإنتاج
if not DEBUG:
    STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# إعدادات المرفقات
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# ==========================================
# 7. إعدادات متنوعة
# ==========================================
MAILERS = {
    'default': {
        'BACKEND': 'django.core.mail.backends.console.EmailBackend',
    },
}

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'dashboard'
LOGOUT_REDIRECT_URL = 'login'