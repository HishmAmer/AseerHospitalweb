#!/usr/bin/env bash
# تركيب النظام على خادم Linux
set -o errexit
cd "$(dirname "$0")/.."

echo "== تركيب نظام إدارة الموارد البشرية =="

command -v python3 >/dev/null || { echo "[خطأ] Python 3 غير مثبّت."; exit 1; }
[ -f .env ] || { echo "[خطأ] ملف .env غير موجود. انسخ .env.example إلى .env وعدّله."; exit 1; }

echo "[1/4] البيئة المعزولة..."
[ -d venv ] || python3 -m venv venv

echo "[2/4] المكتبات..."
venv/bin/pip install --quiet --upgrade pip
venv/bin/pip install --quiet -r requirements.txt

echo "[3/4] الملفات الثابتة..."
venv/bin/python manage.py collectstatic --no-input >/dev/null

echo "[4/4] قاعدة البيانات..."
venv/bin/python manage.py migrate

echo
echo "تم التركيب. الخطوة التالية:"
echo "  venv/bin/python manage.py createsuperuser"
