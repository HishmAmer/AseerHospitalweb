/**
 * Auth.gs — الهوية والصلاحيات ونطاق البيانات.
 *
 * النشر يكون «التنفيذ باسمي» (USER_DEPLOYING)، أي أن السكربت يعمل بصلاحية
 * المالك ويصل إلى جدول البيانات كاملاً مهما كان المستخدم. لذلك فصل بيانات
 * المنشآت ليس خاصية من خصائص Google، بل مفروض في هذه الشيفرة وحدها:
 * كل دالة تعيد بيانات موظفين تمرّ على scopedEmployees().
 *
 * لا تُخزَّن كلمات مرور إطلاقاً: الهوية من حساب Google، والجدول يربط
 * البريد بالصلاحية والمنشأة فقط.
 */

/** بريد المستخدم الحالي، أو '' إن تعذّر (نشر خاطئ أو مستخدم مجهول). */
function currentEmail() {
  try {
    var email = Session.getActiveUser().getEmail();
    return email ? String(email).trim().toLowerCase() : '';
  } catch (err) {
    return '';
  }
}

/**
 * سجل المستخدم الحالي من ورقة المستخدمين، أو null.
 *
 * الفشل مغلق: بريد غير مسجَّل، أو حساب معطَّل، أو حساب فرعي بلا منشأة
 * — كلها تُعامَل كـ «بلا صلاحية»، لا كـ «صلاحية كاملة».
 */
function currentUser() {
  var email = currentEmail();
  if (!email) return null;

  var rows = readTable(SHEETS.USERS);
  for (var i = 0; i < rows.length; i++) {
    if (String(rows[i]['البريد الإلكتروني'] || '').trim().toLowerCase() !== email) continue;
    if (String(rows[i]['الحالة']) !== 'مفعَّل') return null;

    var role = String(rows[i]['الصلاحية'] || '').trim();
    var workplace = String(rows[i]['المنشأة التابع لها'] || '').trim();

    // حساب فرعي بلا منشأة لا يرى شيئاً — لا كل شيء.
    if (role !== 'admin' && !workplace) return null;

    return {
      id: rows[i]['المعرف'],
      email: email,
      name: String(rows[i]['الاسم'] || '') || email,
      role: role,
      isAdmin: role === 'admin',
      workplace: role === 'admin' ? '' : workplace
    };
  }
  return null;
}

/** يعيد المستخدم الحالي أو يرمي خطأ مفهوماً. */
function requireUser() {
  var user = currentUser();
  if (!user) {
    throw new Error(
      'حسابك (' + (currentEmail() || 'غير معروف') + ') غير مصرَّح له بالدخول. ' +
      'راجع مدير النظام لإضافته.'
    );
  }
  return user;
}

/** يعيد المستخدم الحالي بشرط أن يكون مدير نظام. */
function requireAdmin() {
  var user = requireUser();
  if (!user.isAdmin) throw new Error('هذه الصفحة متاحة لمدير النظام فقط.');
  return user;
}

/** اسم النطاق المعروض في الواجهة. */
function scopeLabel(user) {
  return user.isAdmin ? 'الإدارة العامة' : user.workplace;
}

/**
 * الموظفون الذين يحق للمستخدم الاطلاع عليهم.
 * @param {Object} user   المستخدم الحالي.
 * @param {boolean} archived  true للأرشيف، false للسجل النشط.
 */
function scopedEmployees(user, archived) {
  var wantArchived = !!archived;
  var rows = readTable(SHEETS.EMPLOYEES);
  var out = [];

  for (var i = 0; i < rows.length; i++) {
    var row = rows[i];
    if (isTruthy_(row['مؤرشف']) !== wantArchived) continue;
    if (!user.isAdmin && String(row['المنشأة الحالية'] || '').trim() !== user.workplace) continue;
    out.push(row);
  }

  out.sort(function (a, b) {
    return String(a['الاسم الرباعي']).localeCompare(String(b['الاسم الرباعي']), 'ar');
  });
  return out;
}

/** يجلب موظفاً ضمن نطاق المستخدم، أو يرمي خطأ. لا يكشف وجوده خارج النطاق. */
function scopedEmployee(user, id, archived) {
  var rows = scopedEmployees(user, archived);
  for (var i = 0; i < rows.length; i++) {
    if (Number(rows[i]['المعرف']) === Number(id)) return rows[i];
  }
  throw new Error('الموظف غير موجود، أو خارج نطاق صلاحيتك.');
}

/** يتحقق أن المنشأة المختارة مسموحة لهذا المستخدم. */
function assertWorkplaceAllowed_(user, workplace) {
  var name = String(workplace || '').trim();
  if (user.isAdmin) return name;
  if (name && name !== user.workplace) {
    throw new Error('لا يمكنك تسجيل موظف في منشأة غير منشأتك.');
  }
  return user.workplace;
}

/** تحويل قيم الورقة المنطقية (TRUE / 'نعم' / 1) إلى boolean. */
function isTruthy_(value) {
  if (value === true) return true;
  if (value === false || value === '' || value === null || value === undefined) return false;
  var text = String(value).trim().toLowerCase();
  return text === 'true' || text === 'نعم' || text === '1' || text === 'yes';
}
