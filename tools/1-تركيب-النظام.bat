@echo off
chcp 65001 >nul
cd /d "%~dp0.."
echo ================================================
echo   تركيب نظام إدارة الموارد البشرية
echo ================================================
echo.

where python >nul 2>&1
if errorlevel 1 (
    echo [خطأ] لم يُعثر على Python.
    echo نزّله من https://www.python.org/downloads/
    echo واحرص على تفعيل خيار "Add Python to PATH" اثناء التركيب.
    pause & exit /b 1
)

echo [1/4] إنشاء البيئة المعزولة...
if not exist venv python -m venv venv || (echo [خطأ] فشل إنشاء البيئة & pause & exit /b 1)

echo [2/4] تركيب المكتبات...
venv\Scripts\python -m pip install --quiet --upgrade pip
venv\Scripts\pip install --quiet -r requirements.txt || (echo [خطأ] فشل تركيب المكتبات & pause & exit /b 1)

echo [3/4] تجهيز الملفات الثابتة...
venv\Scripts\python manage.py collectstatic --no-input >nul || (echo [خطأ] راجع ملف .env & pause & exit /b 1)

echo [4/4] تجهيز قاعدة البيانات...
venv\Scripts\python manage.py migrate || (echo [خطأ] فشل تجهيز قاعدة البيانات & pause & exit /b 1)

echo.
echo ================================================
echo   تم التركيب بنجاح
echo   الخطوة التالية: شغّل  2-إنشاء-حساب-مدير.bat
echo ================================================
pause
