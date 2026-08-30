@echo off
chcp 65001 >nul
cd /d "%~dp0.."
if not exist backups mkdir backups
for /f "tokens=2 delims==" %%I in ('wmic os get localdatetime /value') do set dt=%%I
set STAMP=%dt:~0,4%-%dt:~4,2%-%dt:~6,2%_%dt:~8,2%%dt:~10,2%
echo ================================================
echo   أخذ نسخة احتياطية
echo ================================================
if exist db.sqlite3 (
    copy /Y db.sqlite3 "backups\db_%STAMP%.sqlite3" >nul
    echo تم الحفظ: backups\db_%STAMP%.sqlite3
) else (
    echo [تنبيه] لم يُعثر على db.sqlite3
    echo إن كنت تستخدم PostgreSQL فالنسخ يتم بأداة pg_dump.
)
echo.
pause
