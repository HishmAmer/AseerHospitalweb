/**
 * Users.gs — إدارة الحسابات والصلاحيات.
 *
 * لا كلمات مرور: الهوية من حساب Google. الجدول يربط البريد بالصلاحية
 * والمنشأة فقط، فلا يوجد ما يُسرَّب لو اطّلع أحد على الورقة.
 */

function apiListUsers() {
  var me = requireAdmin();
  var rows = readTable(SHEETS.USERS);
  rows.sort(function (a, b) {
    return String(a['البريد الإلكتروني']).localeCompare(String(b['البريد الإلكتروني']));
  });
  return rows.map(function (r) {
    return {
      id: r['المعرف'],
      email: r['البريد الإلكتروني'],
      name: r['الاسم'],
      role: r['الصلاحية'],
      roleLabel: r['الصلاحية'] === 'admin' ? 'مدير النظام' : 'حساب منشأة',
      workplace: r['المنشأة التابع لها'],
      active: String(r['الحالة']) === 'مفعَّل',
      isSelf: String(r['البريد الإلكتروني']).trim().toLowerCase() === me.email
    };
  });
}

/** يتحقق من اتساق الصلاحية مع المنشأة. */
function resolveAccountWorkplace_(role, workplace) {
  var name = String(workplace || '').trim();
  if (role === 'admin') {
    if (name) throw new Error('خطأ: حساب الإدارة (الأدمن) لا يجب أن يرتبط بمنشأة محددة.');
    return '';
  }
  if (!name) throw new Error('إجباري: يجب اختيار المنشأة للحسابات الفرعية.');
  if (referenceNames(SHEETS.WORKPLACES).indexOf(name) === -1) {
    throw new Error('المنشأة المختارة غير موجودة.');
  }
  return name;
}

function normalizeEmail_(email) {
  var clean = String(email || '').trim().toLowerCase();
  if (!clean) throw new Error('البريد الإلكتروني مطلوب.');
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(clean)) {
    throw new Error('صيغة البريد الإلكتروني غير صحيحة.');
  }
  return clean;
}

function apiCreateUser(input) {
  var me = requireAdmin();
  var email = normalizeEmail_(input.email);
  var role = String(input.role || '').trim();
  if (['admin', 'branch'].indexOf(role) === -1) throw new Error('الصلاحية غير صحيحة.');
  var workplace = resolveAccountWorkplace_(role, input.workplace);

  return withLock(function () {
    var rows = readTable(SHEETS.USERS);
    for (var i = 0; i < rows.length; i++) {
      if (String(rows[i]['البريد الإلكتروني']).trim().toLowerCase() === email) {
        throw new Error('هذا البريد مسجَّل بالفعل لمستخدم آخر.');
      }
    }
    insertRow(SHEETS.USERS, {
      'البريد الإلكتروني': email,
      'الاسم': String(input.name || '').trim() || email.split('@')[0],
      'الصلاحية': role,
      'المنشأة التابع لها': workplace,
      'الحالة': input.active === false ? 'معطَّل' : 'مفعَّل',
      'تاريخ الإنشاء': nowIso()
    });
    logActivity_(me, 'إضافة', 'تم إنشاء مستخدم جديد: ' + email);
    return { message: 'تم إنشاء المستخدم (' + email + ') وربطه بنجاح!' };
  });
}

function apiUpdateUser(id, input) {
  var me = requireAdmin();
  var role = String(input.role || '').trim();
  if (['admin', 'branch'].indexOf(role) === -1) throw new Error('الصلاحية غير صحيحة.');

  return withLock(function () {
    var target = findById(SHEETS.USERS, id);
    if (!target) throw new Error('المستخدم غير موجود.');
    var targetEmail = String(target['البريد الإلكتروني']).trim().toLowerCase();
    var isSelf = targetEmail === me.email;

    // حماية من أن يُقفل المدير على نفسه خارج النظام.
    if (isSelf && input.active === false) {
      throw new Error('عملية مرفوضة: لا يمكنك تعطيل حسابك الشخصي أثناء استخدامه!');
    }
    if (isSelf && role !== 'admin') {
      throw new Error('عملية مرفوضة: لا يمكنك سحب صلاحيات الإدارة من حسابك الشخصي!');
    }

    var workplace = resolveAccountWorkplace_(role, input.workplace);
    var newEmail = targetEmail;
    if (input.email) {
      newEmail = normalizeEmail_(input.email);
      if (newEmail !== targetEmail) {
        var rows = readTable(SHEETS.USERS);
        for (var i = 0; i < rows.length; i++) {
          if (Number(rows[i]['المعرف']) === Number(id)) continue;
          if (String(rows[i]['البريد الإلكتروني']).trim().toLowerCase() === newEmail) {
            throw new Error('هذا البريد مسجَّل بالفعل لمستخدم آخر.');
          }
        }
      }
    }

    updateRow(SHEETS.USERS, id, {
      'البريد الإلكتروني': newEmail,
      'الاسم': String(input.name || '').trim() || target['الاسم'],
      'الصلاحية': role,
      'المنشأة التابع لها': workplace,
      'الحالة': input.active === false ? 'معطَّل' : 'مفعَّل'
    });
    logActivity_(me, 'تعديل', 'تم تعديل بيانات وصلاحيات المستخدم: ' + newEmail);
    return { message: 'تم تحديث بيانات المستخدم (' + newEmail + ') بنجاح!' };
  });
}

function apiDeleteUser(id) {
  var me = requireAdmin();
  return withLock(function () {
    var target = findById(SHEETS.USERS, id);
    if (!target) throw new Error('المستخدم غير موجود.');
    var email = String(target['البريد الإلكتروني']).trim().toLowerCase();
    if (email === me.email) {
      throw new Error('عملية مرفوضة: لا يمكنك حذف حسابك الشخصي.');
    }
    // آخر مدير نظام لا يُحذف، وإلا صار النظام بلا من يديره.
    if (String(target['الصلاحية']) === 'admin') {
      var admins = readTable(SHEETS.USERS).filter(function (r) {
        return String(r['الصلاحية']) === 'admin' && String(r['الحالة']) === 'مفعَّل';
      });
      if (admins.length <= 1) throw new Error('لا يمكن حذف آخر حساب مدير نظام.');
    }
    deleteRow(SHEETS.USERS, id);
    logActivity_(me, 'حذف', 'تم حذف المستخدم: ' + email);
    return { message: 'تم حذف المستخدم.' };
  });
}
