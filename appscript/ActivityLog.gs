/**
 * ActivityLog.gs — سجل التدقيق.
 *
 * يسجّل من فعل ماذا ومتى. صياغة «منذ كم يوم» تتبع تمييز العدد في العربية:
 * المفرد والمثنى والجمع وصيغة 11–99 ثم 100 فأكثر — لكل منها صورة مختلفة،
 * و«منذ 2 يوم» خطأ لغوي لا يليق بنظام رسمي.
 */

function logActivity_(user, actionType, description) {
  try {
    insertRow(SHEETS.ACTIVITY, {
      'المستخدم': user ? user.email : 'نظام',
      'نوع الإجراء': actionType,
      'التفاصيل': description,
      'الوقت والتاريخ': nowIso()
    });
  } catch (err) {
    // فشل التسجيل لا يُسقط العملية نفسها، لكنه يُدوَّن في سجلات المنصّة.
    console.error('تعذّر كتابة سجل النشاط: ' + err.message);
  }
}

/**
 * عبارة «منذ ...» بصيغة عربية صحيحة.
 * 0 → اليوم | 1 → أمس | 2 → يومين | 3–10 → أيام | 11–99 → يوماً | 100+ → يوم
 */
function arabicDaysAgo(days) {
  var n = Math.floor(Number(days));
  if (isNaN(n) || n < 0) return '';
  if (n === 0) return 'اليوم';
  if (n === 1) return 'أمس';
  if (n === 2) return 'منذ يومين';
  if (n <= 10) return 'منذ ' + n + ' أيام';
  if (n <= 99) return 'منذ ' + n + ' يوماً';
  return 'منذ ' + n + ' يوم';
}

function apiListActivity() {
  requireAdmin();
  var cutoff = new Date();
  cutoff.setDate(cutoff.getDate() - ACTIVITY_LOG_DAYS);

  var rows = readTable(SHEETS.ACTIVITY);
  var out = [];
  var today = new Date();

  for (var i = 0; i < rows.length; i++) {
    var stamp = new Date(rows[i]['الوقت والتاريخ']);
    if (isNaN(stamp.getTime()) || stamp < cutoff) continue;

    var days = Math.floor((startOfDay_(today) - startOfDay_(stamp)) / 86400000);
    out.push({
      id: rows[i]['المعرف'],
      user: rows[i]['المستخدم'],
      actionType: rows[i]['نوع الإجراء'],
      description: rows[i]['التفاصيل'],
      when: Utilities.formatDate(stamp, 'Asia/Riyadh', 'yyyy-MM-dd HH:mm'),
      daysAgo: arabicDaysAgo(days)
    });
  }

  out.sort(function (a, b) { return a.when > b.when ? -1 : 1; });
  return { logs: out, days: ACTIVITY_LOG_DAYS };
}

function startOfDay_(date) {
  return new Date(date.getFullYear(), date.getMonth(), date.getDate()).getTime();
}
