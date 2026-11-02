/**
 * Reconcile.gs — مطابقة ملف Excel خارجي بسجلات النظام.
 *
 * العملية للقراءة فقط: لا تُنشئ ولا تُعدّل ولا تحذف أي سجل. الملف المرفوع
 * يُحوَّل مؤقتاً في Drive ثم يُحذف فور قراءته، فلا تبقى نسخة من كشف
 * المنسوبين في Drive.
 *
 * متاحة لمدير النظام وحده: المطابقة تكشف سجلات التجمع كاملة.
 */

/** الأرقام العربية الهندية ترد كثيراً في الملفات المحلية. */
var ARABIC_DIGITS = { '٠':'0','١':'1','٢':'2','٣':'3','٤':'4','٥':'5','٦':'6','٧':'7','٨':'8','٩':'9',
                      '۰':'0','۱':'1','۲':'2','۳':'3','۴':'4','۵':'5','۶':'6','۷':'7','۸':'8','۹':'9' };

/** ترويسات الملف مقابل حقول النظام. تُقبل فروق المسافات والهمزات الشائعة. */
var COLUMN_ALIASES = {
  'الرقم الوظيفي': 'employeeNumber', 'رقم الموظف': 'employeeNumber',
  'اسم الموظف': 'fullName', 'الاسم': 'fullName', 'الاسم الرباعي': 'fullName',
  'رقم الهوية': 'nationalId', 'رقم الهوية / الاقامة': 'nationalId',
  'رقم الهوية / الإقامة': 'nationalId', 'الهوية': 'nationalId',
  'تاريخ الميلاد': 'dob',
  'الجنسية': 'nationality',
  'نوع المنشاة': 'workplaceType', 'نوع المنشأة': 'workplaceType',
  'التفرغ': 'timeType',
  'المنشاة الحالية': 'workplace', 'المنشأة الحالية': 'workplace',
  'القسم': 'department',
  'التخصص العام': 'generalSpecialty',
  'التخصص الدقيق': 'subSpecialty',
  'فئة الموظف (نوع العقد)': 'employeeType', 'فئة الموظف': 'employeeType',
  'فئة الكادر': 'category',
  'المسمى الوظيفي': 'jobTitle',
  'حالة الموظف': 'status', 'الحالة': 'status',
  'تاريخ بداية العقد': 'contractStart',
  'تاريخ نهاية العقد': 'contractEnd',
  'حالة التصنيف': 'isClassified',
  'رقم التصنيف': 'classificationNumber',
  'تاريخ انتهاء التصنيف': 'classificationExpiry'
};

/** الحقول المقارَنة بترتيب عرضها في التقرير. */
var COMPARED_FIELDS = [
  ['fullName', 'اسم الموظف'], ['employeeNumber', 'الرقم الوظيفي'],
  ['nationalId', 'رقم الهوية'], ['dob', 'تاريخ الميلاد'],
  ['nationality', 'الجنسية'], ['workplaceType', 'نوع المنشأة'],
  ['timeType', 'التفرغ'], ['workplace', 'المنشأة الحالية'],
  ['department', 'القسم'], ['generalSpecialty', 'التخصص العام'],
  ['subSpecialty', 'التخصص الدقيق'], ['employeeType', 'فئة الموظف (نوع العقد)'],
  ['category', 'فئة الكادر'], ['jobTitle', 'المسمى الوظيفي'],
  ['status', 'حالة الموظف'], ['contractStart', 'تاريخ بداية العقد'],
  ['contractEnd', 'تاريخ نهاية العقد'], ['isClassified', 'حالة التصنيف'],
  ['classificationNumber', 'رقم التصنيف'], ['classificationExpiry', 'تاريخ انتهاء التصنيف']
];

var DATE_KEYS = ['dob', 'contractStart', 'contractEnd', 'classificationExpiry'];

/** الحقول التي يُعدّ خلوّها نقصاً يستحق التنبيه. */
var REQUIRED_KEYS = [
  ['nationalId', 'رقم الهوية'], ['employeeNumber', 'الرقم الوظيفي'],
  ['dob', 'تاريخ الميلاد'], ['workplace', 'المنشأة الحالية']
];

function normalizeText_(value) {
  if (value === null || value === undefined) return '';
  var text = String(value).trim();
  text = text.replace(/[٠-٩۰-۹]/g, function (d) { return ARABIC_DIGITS[d] || d; });
  return text.replace(/\s+/g, ' ').replace(/[أإآ]/g, 'ا').replace(/ة/g, 'ه');
}

function normalizeHeader_(value) {
  return normalizeText_(value);
}

function resolveHeader_(value) {
  var wanted = normalizeHeader_(value);
  for (var key in COLUMN_ALIASES) {
    if (normalizeHeader_(key) === wanted) return COLUMN_ALIASES[key];
  }
  return null;
}

/** يحوّل الموظف إلى الشكل المقارَن. */
function employeeSnapshot_(row) {
  return {
    fullName: row['الاسم الرباعي'], employeeNumber: row['الرقم الوظيفي'],
    nationalId: row['رقم الهوية'], dob: row['تاريخ الميلاد'],
    nationality: row['الجنسية'], workplaceType: row['نوع المنشأة'],
    timeType: row['التفرغ'], workplace: row['المنشأة الحالية'],
    department: row['القسم'], generalSpecialty: row['التخصص العام'],
    subSpecialty: row['التخصص الدقيق'], employeeType: row['فئة الموظف'],
    category: row['فئة الكادر'], jobTitle: row['المسمى الوظيفي'],
    status: row['حالة الموظف'], contractStart: row['تاريخ بداية العقد'],
    contractEnd: row['تاريخ نهاية العقد'], isClassified: row['حالة التصنيف'],
    classificationNumber: row['رقم التصنيف'],
    classificationExpiry: row['تاريخ انتهاء التصنيف']
  };
}

function valuesMatch_(key, fileValue, systemValue) {
  if (DATE_KEYS.indexOf(key) !== -1) {
    return toDateString(fileValue) === toDateString(systemValue);
  }
  return normalizeText_(fileValue) === normalizeText_(systemValue);
}

function display_(value) {
  var text = (value === null || value === undefined) ? '' : String(value).trim();
  return text === '' ? '(فارغ)' : text;
}

/**
 * يطابق ملفاً مرفوعاً بسجلات النظام.
 * @param {Object} upload {fileName, mimeType, bytes} — bytes بترميز base64.
 */
function apiReconcile(upload) {
  var user = requireAdmin();
  if (!upload || !upload.bytes) throw new Error('يرجى اختيار ملف Excel أولاً.');

  var name = String(upload.fileName || '');
  if (!/\.xlsx$/i.test(name)) {
    throw new Error(
      'الصيغة غير مدعومة. يجب أن يكون الملف بامتداد ‎.xlsx‎ ' +
      '(من Excel: حفظ باسم ← Excel Workbook).'
    );
  }

  var bytes = Utilities.base64Decode(upload.bytes);
  if (bytes.length > MAX_UPLOAD_BYTES) {
    throw new Error(
      'حجم الملف ' + Math.round(bytes.length / 1048576) + ' ميجابايت، والحد الأقصى ' +
      Math.round(MAX_UPLOAD_BYTES / 1048576) + ' ميجابايت.'
    );
  }

  var blob = Utilities.newBlob(bytes, upload.mimeType ||
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', name);

  var converted = null;
  try {
    converted = Drive.Files.insert(
      { title: 'مطابقة مؤقتة ' + Utilities.getUuid(), mimeType: MimeType.GOOGLE_SHEETS },
      blob
    );
    var values = SpreadsheetApp.openById(converted.id).getSheets()[0]
      .getDataRange().getValues();
    var report = compareValues_(values, user);
    report.fileName = name;

    logActivity_(user, 'نظام',
      'طابق ملف Excel (' + name + ') مع بيانات الموظفين: ' +
      report.missingInSystem.length + ' غير مسجّل، ' +
      report.differences.length + ' به اختلافات');
    return report;
  } catch (err) {
    throw new Error('تعذّر قراءة الملف: ' + err.message);
  } finally {
    // يُحذف دائماً: كشف المنسوبين لا يبقى في Drive بعد المطابقة.
    if (converted && converted.id) {
      try { DriveApp.getFileById(converted.id).setTrashed(true); } catch (e) {}
    }
  }
}

function compareValues_(values, user) {
  if (!values || values.length < 2) {
    throw new Error('الملف فارغ أو لا يحتوي على صفوف بيانات تحت الترويسة.');
  }
  if (values.length - 1 > MAX_RECONCILE_ROWS) {
    throw new Error('عدد صفوف الملف يتجاوز الحد المسموح (' + MAX_RECONCILE_ROWS + ' صفاً).');
  }

  var headerRow = values[0];
  var fieldByColumn = {};
  var presentFields = {};
  var unknownHeaders = [];

  for (var c = 0; c < headerRow.length; c++) {
    var raw = String(headerRow[c] || '').trim();
    if (!raw) continue;
    var field = resolveHeader_(raw);
    if (field) {
      fieldByColumn[c] = field;
      presentFields[field] = true;
    } else {
      unknownHeaders.push(raw);
    }
  }

  if (!presentFields.nationalId && !presentFields.employeeNumber && !presentFields.fullName) {
    throw new Error(
      'لم يُعثر على عمود يُطابَق به (رقم الهوية أو الرقم الوظيفي أو اسم الموظف). ' +
      'نزّل القالب الفارغ واستخدم ترويساته.'
    );
  }

  /* فهارس السجلات ضمن نطاق المستخدم */
  var employees = scopedEmployees(user, false);
  var byNationalId = {}, byEmployeeNumber = {}, byName = {};
  for (var e = 0; e < employees.length; e++) {
    var emp = employees[e];
    var nid = normalizeText_(emp['رقم الهوية']);
    var num = normalizeText_(emp['الرقم الوظيفي']);
    var nm = normalizeText_(emp['الاسم الرباعي']);
    if (nid) byNationalId[nid] = emp;
    if (num) byEmployeeNumber[num] = emp;
    if (nm) byName[nm] = emp;
  }

  var matchedIds = {};
  var missingInSystem = [];
  var differences = [];

  for (var r = 1; r < values.length; r++) {
    var rowValues = values[r];
    if (String(rowValues.join('')).trim() === '') continue;

    var record = { _row: r + 1 };
    for (var col in fieldByColumn) {
      record[fieldByColumn[col]] = rowValues[col];
    }

    var match =
      byNationalId[normalizeText_(record.nationalId)] ||
      byEmployeeNumber[normalizeText_(record.employeeNumber)] ||
      byName[normalizeText_(record.fullName)] ||
      null;

    if (!match) {
      missingInSystem.push({
        row: record._row,
        fullName: display_(record.fullName),
        nationalId: display_(record.nationalId),
        employeeNumber: display_(record.employeeNumber),
        workplace: display_(record.workplace)
      });
      continue;
    }

    matchedIds[Number(match['المعرف'])] = true;
    var snapshot = employeeSnapshot_(match);
    var changed = [];
    for (var f = 0; f < COMPARED_FIELDS.length; f++) {
      var key = COMPARED_FIELDS[f][0];
      var label = COMPARED_FIELDS[f][1];
      if (!presentFields[key]) continue;
      if (!(key in record)) continue;
      if (valuesMatch_(key, record[key], snapshot[key])) continue;
      changed.push({ label: label, file: display_(record[key]), system: display_(snapshot[key]) });
    }
    if (changed.length) {
      differences.push({
        row: record._row,
        employeeId: match['المعرف'],
        employeeName: match['الاسم الرباعي'],
        fields: changed
      });
    }
  }

  /* نواقص البيانات في سجلات النظام */
  var incomplete = [];
  for (var i = 0; i < employees.length; i++) {
    var snap = employeeSnapshot_(employees[i]);
    var blanks = [];
    for (var q = 0; q < REQUIRED_KEYS.length; q++) {
      var k = REQUIRED_KEYS[q][0];
      if (!snap[k] && snap[k] !== 0) blanks.push(REQUIRED_KEYS[q][1]);
    }
    if (blanks.length) {
      incomplete.push({
        employeeId: employees[i]['المعرف'],
        employeeName: employees[i]['الاسم الرباعي'],
        missing: blanks
      });
    }
  }

  /* موجود في النظام وغير وارد في الملف */
  var missingInFile = [];
  for (var m = 0; m < employees.length; m++) {
    if (matchedIds[Number(employees[m]['المعرف'])]) continue;
    missingInFile.push({
      employeeId: employees[m]['المعرف'],
      employeeName: employees[m]['الاسم الرباعي'],
      workplace: employees[m]['المنشأة الحالية']
    });
  }

  return {
    scope: scopeLabel(user),
    generatedAt: Utilities.formatDate(new Date(), 'Asia/Riyadh', 'yyyy-MM-dd HH:mm'),
    totalFileRows: values.length - 1,
    totalSystemRows: employees.length,
    unknownHeaders: unknownHeaders,
    missingInSystem: missingInSystem,
    differences: differences,
    incomplete: incomplete,
    missingInFile: missingInFile
  };
}

/** قالب Excel فارغ بترويسات المطابقة. */
function apiReconcileTemplate() {
  requireAdmin();
  var temp = SpreadsheetApp.create('قالب مطابقة ' + Utilities.getUuid());
  try {
    var sheet = temp.getActiveSheet();
    sheet.setName('قالب المطابقة');
    sheet.setRightToLeft(true);
    var headers = COMPARED_FIELDS.map(function (f) { return f[1]; });
    sheet.getRange(1, 1, 1, headers.length).setValues([headers]);
    sheet.getRange(1, 1, 1, headers.length)
      .setFontWeight('bold').setBackground('#16624F').setFontColor('#FFFFFF');
    sheet.setFrozenRows(1);
    for (var c = 1; c <= headers.length; c++) sheet.setColumnWidth(c, 140);
    SpreadsheetApp.flush();

    var url = 'https://docs.google.com/spreadsheets/d/' + temp.getId() +
      '/export?format=xlsx&id=' + temp.getId();
    var blob = UrlFetchApp.fetch(url, {
      headers: { Authorization: 'Bearer ' + ScriptApp.getOAuthToken() },
      muteHttpExceptions: true
    }).getBlob();

    return {
      fileName: 'Reconcile_Template.xlsx',
      mimeType: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      bytes: Utilities.base64Encode(blob.getBytes())
    };
  } finally {
    DriveApp.getFileById(temp.getId()).setTrashed(true);
  }
}
