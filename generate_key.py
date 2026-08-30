"""يولّد مفتاحاً سرياً جديداً لملف .env

الاستخدام:
    python generate_key.py

انسخ السطر الناتج والصقه في ملف .env مكان DJANGO_SECRET_KEY.
"""

import secrets

CHARS = 'abcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*(-_=+)'

key = ''.join(secrets.choice(CHARS) for _ in range(50))

print()
print('=' * 66)
print('  المفتاح السري — انسخ السطر التالي كاملاً إلى ملف .env')
print('=' * 66)
print()
print(f'DJANGO_SECRET_KEY={key}')
print()
print('=' * 66)
print('  تحذير: لا تشارك هذا المفتاح، ولا تستخدمه في أكثر من تركيب.')
print('=' * 66)
print()
