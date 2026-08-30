#!/usr/bin/env bash
# تشغيل النظام على خادم Linux
set -o errexit
cd "$(dirname "$0")/.."
venv/bin/python manage.py migrate
exec venv/bin/gunicorn core.wsgi:application \
     --bind 0.0.0.0:8000 --workers 3 --timeout 120
