"""عرض «منذ كم يوم» بصيغة عربية سليمة.

فلتر timesince في جانغو يعطي صيغة واحدة لكل عدد، بينما العربية تميّز
المفرد والمثنى والجمع القليل والتمييز المفرد.
"""

from django import template
from django.utils import timezone

register = template.Library()


def arabic_days(count):
    """تمييز العدد الصحيح للأيام، في سياق يسبقه حرف الجرّ «منذ».

    القاعدة: المثنى مجرور بعد «منذ» (يومين لا يومان)، و3-10 جمع مجرور
    (أيام)، و11-99 مفرد منصوب (يوماً)، و100 فأكثر مفرد مجرور (يوم).
    """
    if count == 1:
        return 'يوم واحد'
    if count == 2:
        return 'يومين'
    if 3 <= count <= 10:
        return '{} أيام'.format(count)
    if count < 100:
        return '{} يوماً'.format(count)
    return '{} يوم'.format(count)


@register.filter
def days_ago(value):
    """كم يوماً مضى على هذا التاريخ، بصيغة عربية مقروءة.

    الفرق يُحسب بين التاريخين لا بالساعات، فحدثٌ الساعة 11 مساءً أمس
    يُقرأ «أمس» لا «اليوم» لمجرد أن الفارق أقل من 24 ساعة.
    """
    if not value:
        return ''

    # timestamp مخزَّن بالتوقيت العالمي؛ التحويل للتوقيت المحلي أولاً
    # وإلا انزاح اليوم ثلاث ساعات في توقيت الرياض.
    if timezone.is_aware(value):
        value = timezone.localtime(value)
    today = timezone.localdate()
    delta = (today - value.date()).days

    if delta < 0:
        return 'تاريخ لاحق'
    if delta == 0:
        return 'اليوم'
    if delta == 1:
        return 'أمس'
    return 'منذ {}'.format(arabic_days(delta))
