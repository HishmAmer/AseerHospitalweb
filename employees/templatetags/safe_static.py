"""وسم ثابت لا يُسقط الصفحة عند غياب الملف.

مع ManifestStaticFilesStorage في الإنتاج، يرفع {% static %} استثناء
ValueError إذا لم يكن الملف مُجمَّعاً — فيتحوّل شعار ناقص إلى خطأ 500
يمنع الدخول إلى النظام بالكامل. هذا الوسم يعيد نصاً فارغاً بدلاً من ذلك،
فيغيب الشعار وحده ويبقى النظام يعمل.
"""

from django import template
from django.contrib.staticfiles.storage import staticfiles_storage

register = template.Library()


@register.simple_tag
def static_if_exists(path):
    try:
        return staticfiles_storage.url(path)
    except ValueError:
        return ''
