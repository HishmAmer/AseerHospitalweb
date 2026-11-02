/**
 * Settings.gs — البيانات المرجعية (المنشآت، الأقسام، التخصصات، الجنسيات).
 *
 * تعوّض هذه الوحدة غياب المفاتيح الخارجية في Sheets:
 *   - الحذف يُرفض إن كان العنصر مستخدَماً، بدل أن يترك سجلات موظفين تشير
 *     إلى اسم لم يعد موجوداً.
 *   - إعادة التسمية تُعمَّم على كل السجلات المرتبطة داخل القفل نفسه، وإلا
 *     بقيت السجلات على الاسم القديم.
 * القيم تُخزَّن كأسماء لا كمعرّفات، لأن قابلية قراءة الورقة بالعين سبب
 * أساسي لاختيار Sheets أصلاً.
 */

/** كل البيانات المرجعية دفعة واحدة — تستهلكها القوائم المنسدلة. */
function apiReferenceData() {
  requireUser();
  return {
    workplaces: referenceNames(SHEETS.WORKPLACES),
    departments: referenceNames(SHEETS.DEPARTMENTS),
    generalSpecialties: referenceNames(SHEETS.GENERAL_SPECIALTIES),
    subSpecialties: referenceNames(SHEETS.SUB_SPECIALTIES),
    nationalities: referenceNames(SHEETS.NATIONALITIES),
    choices: {
      status: STATUS_CHOICES,
      gender: GENDER_CHOICES,
      employeeType: EMPLOYEE_TYPE_CHOICES,
      category: CATEGORY_CHOICES,
      classification: CLASSIFICATION_CHOICES,
      workplaceType: WORKPLACE_TYPE_CHOICES,
      timeType: TIME_TYPE_CHOICES,
      yesNo: YES_NO_CHOICES,
      leaveTypes: LEAVE_TYPES,
      roles: ROLE_CHOICES
    },
    limits: {
      maxDob: latestAcceptableDob(),
      minAge: MIN_AGE_YEARS,
      archiveReasonMax: ARCHIVE_REASON_MAX
    }
  };
}

/** صفحة الإعدادات: كل قائمة بعناصرها ومعرّفاتها. */
function apiListSettings() {
  requireAdmin();
  var out = {};
  for (var key in REFERENCE_SHEETS) {
    var rows = readTable(REFERENCE_SHEETS[key]);
    if (key === 'nationality') {
      rows.sort(function (a, b) {
        return (Number(a['ترتيب العرض']) || 0) - (Number(b['ترتيب العرض']) || 0);
      });
    } else {
      rows.sort(function (a, b) {
        return String(a['الاسم']).localeCompare(String(b['الاسم']), 'ar');
      });
    }
    out[key] = rows.map(function (r) { return { id: r['المعرف'], name: r['الاسم'] }; });
  }
  return out;
}

function sheetForType_(itemType) {
  var sheet = REFERENCE_SHEETS[itemType];
  if (!sheet) throw new Error('نوع العنصر غير معروف: ' + itemType);
  return sheet;
}

/** يضيف عنصراً مرجعياً. الجنسية الجديدة تُلحق بنهاية القائمة لا أولها. */
function apiAddSettingItem(itemType, name) {
  var user = requireAdmin();
  var sheet = sheetForType_(itemType);
  var clean = String(name || '').replace(/\s+/g, ' ').trim();
  if (!clean) throw new Error('الاسم إلزامي.');

  return withLock(function () {
    var rows = readTable(sheet);
    for (var i = 0; i < rows.length; i++) {
      if (String(rows[i]['الاسم']).trim() === clean) {
        throw new Error('«' + clean + '» موجود بالفعل في القائمة.');
      }
    }

    var record = { 'الاسم': clean };
    if (itemType === 'nationality') {
      // بالنهاية: لو بدأت من صفر لقفزت فوق «سعودي» في قائمة التسجيل.
      var maxOrder = 0;
      for (var r = 0; r < rows.length; r++) {
        maxOrder = Math.max(maxOrder, Number(rows[r]['ترتيب العرض']) || 0);
      }
      record['ترتيب العرض'] = maxOrder + 1;
    }

    insertRow(sheet, record);
    logActivity_(user, 'نظام', 'تم إضافة ' + clean + ' إلى إعدادات النظام');
    return { message: 'تمت الإضافة بنجاح!' };
  });
}

/**
 * يعيد تسمية عنصر مرجعي ويُعمّم الاسم الجديد على السجلات المرتبطة.
 * هذه الفائدة الأساسية من إدارة القوائم: تصحيح إملائي واحد يسري على الجميع.
 */
function apiRenameSettingItem(itemType, id, newName) {
  var user = requireAdmin();
  var sheet = sheetForType_(itemType);
  var clean = String(newName || '').replace(/\s+/g, ' ').trim();
  if (!clean) throw new Error('الاسم إلزامي.');

  return withLock(function () {
    var item = findById(sheet, id);
    if (!item) throw new Error('العنصر غير موجود.');
    var oldName = String(item['الاسم']).trim();
    if (oldName === clean) return { message: 'لا تغيير.' };

    var rows = readTable(sheet);
    for (var i = 0; i < rows.length; i++) {
      if (Number(rows[i]['المعرف']) === Number(id)) continue;
      if (String(rows[i]['الاسم']).trim() === clean) {
        throw new Error('«' + clean + '» موجود بالفعل في القائمة.');
      }
    }

    updateRow(sheet, id, { 'الاسم': clean });
    var touched = cascadeRename_(itemType, oldName, clean);

    logActivity_(user, 'نظام',
      'تم تغيير ' + oldName + ' إلى ' + clean + ' (تأثّر ' + touched + ' سجلاً)');
    return { message: 'تم التعديل، وسرى على ' + touched + ' سجلاً.' };
  });
}

/** يحدّث الاسم في كل السجلات المرتبطة. يجب استدعاؤه داخل قفل. */
function cascadeRename_(itemType, oldName, newName) {
  var column = REFERENCE_USAGE[itemType];
  var touched = 0;

  var employees = readTable(SHEETS.EMPLOYEES);
  var sheet = getSheet(SHEETS.EMPLOYEES);
  var colIndex = COLUMNS[SHEETS.EMPLOYEES].indexOf(column) + 1;
  for (var i = 0; i < employees.length; i++) {
    if (String(employees[i][column] || '').trim() !== oldName) continue;
    sheet.getRange(employees[i]._row, colIndex).setValue(newName);
    touched++;
  }

  // ربط حسابات المستخدمين بالمنشأة يتبع الاسم أيضاً، وإلا فقد الحساب نطاقه.
  if (itemType === 'workplace') {
    var users = readTable(SHEETS.USERS);
    var userSheet = getSheet(SHEETS.USERS);
    var userCol = COLUMNS[SHEETS.USERS].indexOf('المنشأة التابع لها') + 1;
    for (var u = 0; u < users.length; u++) {
      if (String(users[u]['المنشأة التابع لها'] || '').trim() !== oldName) continue;
      userSheet.getRange(users[u]._row, userCol).setValue(newName);
      touched++;
    }
  }
  return touched;
}

/**
 * يحذف عنصراً مرجعياً — ويرفض إن كان مستخدَماً.
 * بديل المفتاح الخارجي PROTECT: الحذف الصامت كان سيترك موظفين بلا منشأة
 * فيختفون عن حساب فرعهم بلا أثر.
 */
function apiDeleteSettingItem(itemType, id) {
  var user = requireAdmin();
  var sheet = sheetForType_(itemType);

  return withLock(function () {
    var item = findById(sheet, id);
    if (!item) throw new Error('العنصر غير موجود.');
    var name = String(item['الاسم']).trim();

    var usage = countReferenceUsage_(itemType, name);
    if (usage > 0) {
      throw new Error(
        'لا يمكن الحذف! «' + name + '» مرتبط ببيانات ' + usage + ' موظف' +
        (usage === 1 ? '' : 'اً') + ' حالياً.'
      );
    }
    if (itemType === 'workplace') {
      var users = readTable(SHEETS.USERS);
      for (var u = 0; u < users.length; u++) {
        if (String(users[u]['المنشأة التابع لها'] || '').trim() === name) {
          throw new Error('لا يمكن الحذف! «' + name + '» مرتبط بحساب مستخدم.');
        }
      }
    }

    deleteRow(sheet, id);
    logActivity_(user, 'نظام', 'تم حذف ' + name + ' من إعدادات النظام');
    return { message: 'تم الحذف بنجاح.' };
  });
}

/** عدد الموظفين (بما فيهم المؤرشفون) المرتبطين بقيمة مرجعية. */
function countReferenceUsage_(itemType, name) {
  var column = REFERENCE_USAGE[itemType];
  var rows = readTable(SHEETS.EMPLOYEES);
  var count = 0;
  for (var i = 0; i < rows.length; i++) {
    if (String(rows[i][column] || '').trim() === name) count++;
  }
  return count;
}
