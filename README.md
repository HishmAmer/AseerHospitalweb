# نظام إدارة الموارد البشرية | تجمع عسير الصحي

تطبيق Django لإدارة بيانات الموظفين والإجازات والصلاحيات عبر منشآت التجمع.

## التشغيل محلياً (Local development)

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
export DJANGO_DEBUG=True
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

## التشغيل على السيرفر (Production)

الإعدادات تُقرأ من متغيرات البيئة. انسخ `.env.example` إلى `.env` واملأ القيم.
التطبيق **يرفض الإقلاع** بدون `DJANGO_SECRET_KEY` و `DJANGO_ALLOWED_HOSTS` عندما
يكون `DJANGO_DEBUG=False`، وهذا مقصود حتى لا يعمل السيرفر بإعدادات غير آمنة.

| المتغير | مطلوب | الوصف |
| --- | --- | --- |
| `DJANGO_SECRET_KEY` | ✅ | مفتاح التوقيع. ولّده بأمر `get_random_secret_key()` ولا تضعه في المستودع |
| `DJANGO_ALLOWED_HOSTS` | ✅ | أسماء النطاقات/العناوين مفصولة بفاصلة |
| `DJANGO_DEBUG` | — | `False` افتراضياً |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | — | مصادر إرسال النماذج مع البروتوكول |
| `DJANGO_SECURE_SSL` | — | فعّله بعد تشغيل HTTPS: يفعّل الكوكيز الآمنة و HSTS والتحويل إلى HTTPS |
| `DATABASE_URL` | — | افتراضياً SQLite محلي |
| `DJANGO_LOGIN_ATTEMPT_LIMIT` / `_TIMEOUT` | — | حد محاولات الدخول الفاشلة ومدة الإيقاف |

```bash
./build.sh                                   # تثبيت، تجميع الملفات الثابتة، ترحيل قاعدة البيانات
gunicorn core.wsgi:application --bind 0.0.0.0:8000
```

### النشر على Render

اضبط المتغيرات من **Dashboard ← Environment** قبل أول نشر، وإلا يفشل `build.sh`
عند `collectstatic` برسالة `ImproperlyConfigured`:

| المتغير | القيمة |
| --- | --- |
| `DJANGO_SECRET_KEY` | مفتاح مولّد (لا تضعه في المستودع) |
| `DJANGO_ALLOWED_HOSTS` | `<اسم-المشروع>.onrender.com` — بدون `https://` أو `/` |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | `https://<اسم-المشروع>.onrender.com` |
| `DJANGO_SECURE_SSL` | `True` |
| `PYTHON_VERSION` | `3.13.7` |

- **لا تضف `DJANGO_DEBUG`** — تركه غير مضبوط يعني `False`، وهو المطلوب.
- `PYTHON_VERSION` ضروري: Render يستخدم Python 3.14 افتراضياً وهو غير مدعوم
  رسمياً في Django 5.2 (المدعوم 3.10–3.13).
- اربط قاعدة بيانات Postgres ليضبط Render متغير `DATABASE_URL` تلقائياً. بدونها
  يستخدم التطبيق ملف SQLite داخل نظام ملفات مؤقت **تُفقد بياناته مع كل نشر**.

> تحديد محاولات الدخول يعتمد على الـ cache. الإعداد الافتراضي (`LocMemCache`) منفصل
> لكل عملية، لذلك عند التشغيل بعدة عمال (workers) اضبط cache مشترك مثل Redis أو
> قاعدة البيانات ليصبح الحد فعّالاً على مستوى السيرفر كله.

## الاختبارات

```bash
DJANGO_DEBUG=True python manage.py test employees
DJANGO_SECRET_KEY=... DJANGO_ALLOWED_HOSTS=... python manage.py check --deploy
```

## الصلاحيات

- **حساب الإدارة (superuser):** يرى كل المنشآت، ويدير المستخدمين وإعدادات النظام وسجل النشاطات.
- **الحساب الفرعي:** مرتبط بمنشأة واحدة إجبارياً ولا يرى أو يعدّل بيانات المنشآت الأخرى.
