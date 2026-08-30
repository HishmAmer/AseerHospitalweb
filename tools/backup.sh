#!/usr/bin/env bash
# نسخة احتياطية من قاعدة البيانات
set -o errexit
cd "$(dirname "$0")/.."
mkdir -p backups
STAMP=$(date +%Y-%m-%d_%H%M)

if [ -f db.sqlite3 ]; then
    cp db.sqlite3 "backups/db_${STAMP}.sqlite3"
    echo "تم الحفظ: backups/db_${STAMP}.sqlite3"
    # الإبقاء على آخر 30 نسخة فقط
    ls -1t backups/db_*.sqlite3 2>/dev/null | tail -n +31 | xargs -r rm --
else
    echo "[تنبيه] لا يوجد db.sqlite3 — إن كنت تستخدم PostgreSQL فاستخدم pg_dump."
fi
