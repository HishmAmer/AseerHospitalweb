/**
 * Employees.gs — سجل الموظفين: القراءة والتحقق والحفظ والأرشفة.
 *
 * قواعد التحقق هنا مطابقة لنظام Django، ومفروضة في الخادم لا في المتصفح:
 * الواجهة تُخفي الحقول غير اللازمة تيسيراً، لكن الرفض الحقيقي يقع هنا،
 * فيصمد حتى لو استُدعيت الدالة من خارج الواجهة.
 */

/** العمر بالسنوات المكتملة حتى اليوم. */
function yearsSince(dateString) {
  var dob = parseDateOnly_(dateString);
  if (!dob) return null;
  var today = new Date();
  var age = today.getFullYear() - dob.getFullYear();
  var monthDiff = today.getMonth() - dob.getMonth();
  if (monthDiff < 0 || (monthDiff === 0 && today.getDate() < dob.getDate())) age--;
  return age;
}

/**
 * أقصى تاريخ ميلاد مقبول (أي أصغر عمر مسموح).
 * يُحسب بطرح الشهور لا بتبديل السنة: 29 فبراير لا وجود له في سنة غير كبيسة.
 */
function latestAcceptableDob() {
  var d = new Date();
  d.setFullYear(d.getFullYear() - MIN_AGE_YEARS);
  return Utilities.formatDate(d, 'Asia/Riyadh', 'yyyy-MM-dd');
}

function parseDateOnly_(value) {
  var text = toDateString(value);
  if (!text) return null;
  var parts = text.split('-');
  var d = new Date(Number(parts[0]), Number(parts[1]) - 1, Number(parts[2]));
  return isNaN(d.getTime()) ? null : d;
}

/**
 * يتحقق من بيانات موظف ويعيد سجلاً نظيفاً جاهزاً للحفظ.
 * يرمي خطأً واحداً يجمع كل المشاكل، حتى لا يصلح المستخدم خطأً في كل محاولة.
 */
function validateEmployee_(user, input, existing) {
  var errors = [];
  var clean = {};

  function text(key) { return String(input[key] == null ? '' : input[key]).trim(); }

  /* ── الاسم إلزامي ── */
  clean['الاسم الرباعي'] = text('الاسم الرباعي');
  if (!clean['الاسم الرباعي']) errors.push('الاسم الرباعي إلزامي.');

  clean['رقم الهوية'] = text('رقم الهوية');
  clean['الرقم الوظيفي'] = text('الرقم الوظيفي');
  clean['رقم الجوال'] = text('رقم الجوال');

  /* ── الجنس إلزامي ومن القائمة ── */
  clean['الجنس'] = text('الجنس');
  if (!clean['الجنس']) {
    errors.push('الجنس إلزامي.');
  } else if (!GENDER_CHOICES.some(function (g) { return g.value === clean['الجنس']; })) {
    errors.push('قيمة الجنس غير صحيحة.');
  }

  /* ── العمر: أكبر من 20 عاماً ── */
  clean['تاريخ الميلاد'] = toDateString(input['تاريخ الميلاد']);
  if (clean['تاريخ الميلاد']) {
    var age = yearsSince(clean['تاريخ الميلاد']);
    if (age === null) {
      errors.push('تاريخ الميلاد غير صالح.');
    } else if (age < MIN_AGE_YEARS) {
      errors.push(
        'يجب أن يكون عمر الموظف أكبر من ' + (MIN_AGE_YEARS - 1) +
        ' عاماً — العمر المحسوب ' + age + '.'
      );
    }
  }

  /* ── قوائم مغلقة ── */
  clean['الجنسية'] = assertInList_(errors, text('الجنسية'), referenceNames(SHEETS.NATIONALITIES), 'الجنسية', false);
  clean['حالة الموظف'] = assertInList_(errors, text('حالة الموظف') || 'نشط', STATUS_CHOICES, 'حالة الموظف', true);
  clean['التفرغ'] = assertInList_(errors, text('التفرغ'), TIME_TYPE_CHOICES, 'التفرغ', false);
  clean['فئة الكادر'] = assertInList_(errors, text('فئة الكادر'), CATEGORY_CHOICES, 'فئة الكادر', false);
  clean['نوع المنشأة'] = assertInList_(errors, text('نوع المنشأة'), WORKPLACE_TYPE_CHOICES, 'نوع المنشأة', false);
  clean['القسم'] = assertInList_(errors, text('القسم'), referenceNames(SHEETS.DEPARTMENTS), 'القسم', false);
  clean['التخصص العام'] = assertInList_(errors, text('التخصص العام'), referenceNames(SHEETS.GENERAL_SPECIALTIES), 'التخصص العام', false);
  clean['المسمى الوظيفي'] = text('المسمى الوظيفي');

  /* ── المنشأة: الحساب الفرعي محصور بمنشأته ── */
  var workplace = assertInList_(errors, text('المنشأة الحالية'), referenceNames(SHEETS.WORKPLACES), 'المنشأة الحالية', false);
  clean['المنشأة الحالية'] = assertWorkplaceAllowed_(user, workplace);
  if (!clean['المنشأة الحالية']) errors.push('المنشأة الحالية إلزامية.');

  /* ── التخصص الدقيق مشروط بوجوده ── */
  clean['يوجد تخصص دقيق'] = assertInList_(errors, text('يوجد تخصص دقيق') || 'لا', YES_NO_CHOICES, 'يوجد تخصص دقيق', true);
  if (clean['يوجد تخصص دقيق'] === 'نعم') {
    clean['التخصص الدقيق'] = assertInList_(errors, text('التخصص الدقيق'), referenceNames(SHEETS.SUB_SPECIALTIES), 'التخصص الدقيق', false);
    if (!clean['التخصص الدقيق']) errors.push('اخترت وجود تخصص دقيق، فيجب تحديده.');
  } else {
    // يُمحى وإلا بقي تخصص دقيق قديم في سجل أُلغي عنه.
    clean['التخصص الدقيق'] = '';
  }

  /* ── العقد مرتبط بفئة الموظف ── */
  clean['فئة الموظف'] = assertInList_(errors, text('فئة الموظف'), EMPLOYEE_TYPE_CHOICES, 'فئة الموظف', false);
  var start = toDateString(input['تاريخ بداية العقد']);
  var end = toDateString(input['تاريخ نهاية العقد']);

  if (clean['فئة الموظف'] === CIVIL_SERVICE) {
    // خدمة مدنية: لا عقد. يُمحى ما كان مسجَّلاً عند تغيير الفئة.
    clean['تاريخ بداية العقد'] = '';
    clean['تاريخ نهاية العقد'] = '';
  } else {
    clean['تاريخ بداية العقد'] = start;
    clean['تاريخ نهاية العقد'] = end;
    if (clean['فئة الموظف'] && !end) {
      errors.push('تاريخ نهاية العقد إلزامي لغير موظفي الخدمة المدنية.');
    }
    if (start && end && end < start) {
      errors.push('تاريخ نهاية العقد لا يمكن أن يكون قبل تاريخ البداية.');
    }
  }

  /* ── التصنيف المهني: الرقم والتاريخ يلزمان معاً ── */
  clean['حالة التصنيف'] = assertInList_(errors, text('حالة التصنيف') || 'غير مصنف', CLASSIFICATION_CHOICES, 'حالة التصنيف', true);
  if (clean['حالة التصنيف'] === 'مصنف') {
    clean['رقم التصنيف'] = text('رقم التصنيف');
    clean['تاريخ انتهاء التصنيف'] = toDateString(input['تاريخ انتهاء التصنيف']);
    if (!clean['رقم التصنيف']) errors.push('يجب إدخال رقم التصنيف بما أن الموظف (مصنف).');
    if (!clean['تاريخ انتهاء التصنيف']) errors.push('يجب إدخال تاريخ انتهاء التصنيف بما أن الموظف (مصنف).');
  } else {
    // يُمحيان معاً حتى لا يبقى رقم تصنيف قديم في سجل أُلغي تصنيفه.
    clean['رقم التصنيف'] = '';
    clean['تاريخ انتهاء التصنيف'] = '';
  }

  /* ── التكليف الإداري ── */
  var assigned = isTruthy_(input['مكلف بعمل إداري']);
  clean['مكلف بعمل إداري'] = assigned ? 'نعم' : 'لا';
  clean['تفاصيل العمل الإداري'] = assigned ? text('تفاصيل العمل الإداري') : '';

  if (errors.length) throw new Error(errors.join('\n'));
  return clean;
}

/** يتحقق أن القيمة ضمن قائمة مغلقة. القيمة الفارغة مقبولة إلا إن كانت إلزامية. */
function assertInList_(errors, value, allowed, label, required) {
  if (!value) {
    if (required) errors.push(label + ' إلزامي.');
    return '';
  }
  if (allowed.indexOf(value) === -1) {
    errors.push(label + ' «' + value + '» غير موجود في القائمة.');
    return '';
  }
  return value;
}

/* ══════════════ الواجهة المستدعاة من المتصفح ══════════════ */

/** قائمة الموظفين ضمن النطاق، مع بحث وتصفية. */
function apiListEmployees(filters) {
  var user = requireUser();
  filters = filters || {};
  var rows = scopedEmployees(user, false);

  var search = String(filters.search || '').trim();
  var status = String(filters.status || '').trim();
  var workplace = String(filters.workplace || '').trim();

  var out = [];
  for (var i = 0; i < rows.length; i++) {
    var r = rows[i];
    if (status && String(r['حالة الموظف']) !== status) continue;
    if (workplace && user.isAdmin && String(r['المنشأة الحالية']) !== workplace) continue;
    if (search) {
      var hay = [r['الاسم الرباعي'], r['رقم الهوية'], r['الرقم الوظيفي']].join(' ');
      if (hay.indexOf(search) === -1) continue;
    }
    out.push(publicEmployee_(r));
  }
  return { employees: out, total: out.length, scope: scopeLabel(user) };
}

/** سجل موظف واحد للتعديل. */
function apiGetEmployee(id) {
  var user = requireUser();
  return publicEmployee_(scopedEmployee(user, id, false));
}

/** يُنشئ موظفاً جديداً. */
function apiCreateEmployee(input) {
  var user = requireUser();
  return withLock(function () {
    var clean = validateEmployee_(user, input, null);
    assertUnique_(SHEETS.EMPLOYEES, 'رقم الهوية', clean['رقم الهوية'], null);
    assertUnique_(SHEETS.EMPLOYEES, 'الرقم الوظيفي', clean['الرقم الوظيفي'], null);

    clean['مؤرشف'] = 'لا';
    clean['سبب النقل للأرشيف'] = '';
    clean['تاريخ الإنشاء'] = nowIso();
    clean['تاريخ التحديث'] = nowIso();

    var saved = insertRow(SHEETS.EMPLOYEES, clean);
    logActivity_(user, 'إضافة', 'تم إضافة الموظف: ' + saved['الاسم الرباعي']);
    return { id: saved['المعرف'], message: 'تم إضافة الموظف بنجاح!' };
  });
}

/** يحدّث بيانات موظف قائم. */
function apiUpdateEmployee(id, input) {
  var user = requireUser();
  return withLock(function () {
    var existing = scopedEmployee(user, id, false);
    var clean = validateEmployee_(user, input, existing);
    assertUnique_(SHEETS.EMPLOYEES, 'رقم الهوية', clean['رقم الهوية'], id);
    assertUnique_(SHEETS.EMPLOYEES, 'الرقم الوظيفي', clean['الرقم الوظيفي'], id);

    clean['تاريخ التحديث'] = nowIso();
    updateRow(SHEETS.EMPLOYEES, id, clean);
    logActivity_(user, 'تعديل', 'تم تعديل بيانات الموظف: ' + clean['الاسم الرباعي']);
    return { id: Number(id), message: 'تم تحديث بيانات الموظف بنجاح!' };
  });
}

/**
 * ينقل موظفاً إلى الأرشيف. السبب إلزامي: النافذة في المتصفح تفرضه، لكن
 * الاستدعاء قد يصل بدونها، فالرفض هنا هو ما يضمن ألّا يدخل الأرشيف سجل
 * بلا سبب.
 */
function apiArchiveEmployee(id, reason) {
  var user = requireUser();
  var text = String(reason || '').replace(/\s+/g, ' ').trim();
  if (!text) throw new Error('يجب كتابة سبب النقل للأرشيف.');
  if (text.length > ARCHIVE_REASON_MAX) {
    throw new Error('سبب النقل طويل جداً (الحد ' + ARCHIVE_REASON_MAX + ' حرفاً).');
  }

  return withLock(function () {
    var employee = scopedEmployee(user, id, false);
    updateRow(SHEETS.EMPLOYEES, id, {
      'مؤرشف': 'نعم',
      'سبب النقل للأرشيف': text,
      'تاريخ التحديث': nowIso()
    });
    logActivity_(user, 'تعديل',
      'تم نقل الموظف للأرشيف: ' + employee['الاسم الرباعي'] + ' — السبب: ' + text);
    return { message: 'تم نقل الموظف ' + employee['الاسم الرباعي'] + ' للأرشيف.' };
  });
}

/** قائمة الأرشيف ضمن النطاق. */
function apiListArchive() {
  var user = requireUser();
  var rows = scopedEmployees(user, true);
  return {
    employees: rows.map(publicEmployee_),
    total: rows.length,
    scope: scopeLabel(user)
  };
}

/**
 * يستعيد موظفاً من الأرشيف.
 * السبب يُفرَّغ حتى لا يُنسب سبب أرشفة قديم إلى أرشفة لاحقة؛ نصّه محفوظ
 * في سجل النشاطات قبل المسح.
 */
function apiRestoreEmployee(id) {
  var user = requireUser();
  return withLock(function () {
    var employee = scopedEmployee(user, id, true);
    var previousReason = String(employee['سبب النقل للأرشيف'] || '');
    updateRow(SHEETS.EMPLOYEES, id, {
      'مؤرشف': 'لا',
      'سبب النقل للأرشيف': '',
      'تاريخ التحديث': nowIso()
    });
    logActivity_(user, 'استعادة',
      'تم استعادة الموظف للعمل: ' + employee['الاسم الرباعي'] +
      (previousReason ? ' — سبب أرشفته كان: ' + previousReason : ''));
    return { message: 'تم استعادة الموظف ' + employee['الاسم الرباعي'] + ' بنجاح!' };
  });
}

/** الحذف النهائي — لمدير النظام وحده، ولا تراجع عنه. */
function apiHardDeleteEmployee(id) {
  var user = requireAdmin();
  return withLock(function () {
    var employee = findById(SHEETS.EMPLOYEES, id);
    if (!employee || !isTruthy_(employee['مؤرشف'])) {
      throw new Error('الحذف النهائي متاح للسجلات المؤرشفة فقط.');
    }
    var name = employee['الاسم الرباعي'];
    // الإجازات المرتبطة تُحذف معه، وإلا بقيت إجازات معلّقة بلا موظف.
    var leaves = readTable(SHEETS.LEAVES);
    for (var i = leaves.length - 1; i >= 0; i--) {
      if (Number(leaves[i]['معرف الموظف']) === Number(id)) {
        deleteRow(SHEETS.LEAVES, leaves[i]['المعرف']);
      }
    }
    deleteRow(SHEETS.EMPLOYEES, id);
    logActivity_(user, 'حذف', 'تم مسح الموظف نهائياً من قاعدة البيانات: ' + name);
    return { message: 'تم حذف الموظف من قاعدة البيانات نهائياً.' };
  });
}

/** يحوّل صف الورقة إلى الشكل الذي تستهلكه الواجهة. */
function publicEmployee_(row) {
  return {
    id: row['المعرف'],
    fullName: row['الاسم الرباعي'],
    nationalId: row['رقم الهوية'],
    employeeNumber: row['الرقم الوظيفي'],
    nationality: row['الجنسية'],
    dob: row['تاريخ الميلاد'],
    age: row['تاريخ الميلاد'] ? yearsSince(row['تاريخ الميلاد']) : null,
    gender: row['الجنس'],
    mobile: row['رقم الجوال'],
    workplaceType: row['نوع المنشأة'],
    timeType: row['التفرغ'],
    workplace: row['المنشأة الحالية'],
    department: row['القسم'],
    status: row['حالة الموظف'],
    employeeType: row['فئة الموظف'],
    generalSpecialty: row['التخصص العام'],
    hasSubSpecialty: row['يوجد تخصص دقيق'],
    subSpecialty: row['التخصص الدقيق'],
    isClassified: row['حالة التصنيف'],
    classificationNumber: row['رقم التصنيف'],
    classificationExpiry: row['تاريخ انتهاء التصنيف'],
    category: row['فئة الكادر'],
    jobTitle: row['المسمى الوظيفي'],
    contractStart: row['تاريخ بداية العقد'],
    contractEnd: row['تاريخ نهاية العقد'],
    isAdminAssigned: String(row['مكلف بعمل إداري']) === 'نعم',
    adminWorkDetails: row['تفاصيل العمل الإداري'],
    archiveReason: row['سبب النقل للأرشيف']
  };
}
