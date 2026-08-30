@echo off
chcp 65001 >nul
cd /d "%~dp0.."
echo ================================================
echo   نظام إدارة الموارد البشرية — قيد التشغيل
echo ================================================
echo.
echo لا تغلق هذه النافذة أثناء استخدام النظام.
echo للإيقاف: اضغط Ctrl + C
echo.
venv\Scripts\python manage.py migrate >nul 2>&1
venv\Scripts\waitress-serve --host=0.0.0.0 --port=8000 core.wsgi:application
echo.
echo توقّف النظام.
pause
