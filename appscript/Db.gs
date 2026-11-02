/**
 * Db.gs — طبقة تعامل مع أوراق جدول البيانات كأنها جداول قاعدة بيانات.
 *
 * Google Sheets ليست قاعدة بيانات: لا تفرُّد ولا مفاتيح خارجية ولا معاملات.
 * هذه الطبقة تعوّض ذلك في الشيفرة:
 *   - كل كتابة داخل قفل (LockService) وإلا مرّ تعديلان متزامنان معاً.
 *   - المعرّف عمود صريح لا موضع صف، لأن الصفوف تتزحزح عند الحذف والفرز.
 *   - فحص التفرُّد يتم داخل القفل نفسه، وإلا نجح فحصان متزامنان ثم أُدرج
 *     سجلان بالرقم نفسه.
 * الضمانات هنا أضعف من ضمانات قاعدة بيانات حقيقية، وهذا حدّ المنصّة.
 */

/** يفتح جدول البيانات المرتبط، أو يرمي خطأ واضحاً إن لم يُهيّأ بعد. */
function openBook() {
  var id = PropertiesService.getScriptProperties().getProperty(PROP_SPREADSHEET_ID);
  if (!id) {
    throw new Error(
      'النظام غير مُهيّأ بعد. شغّل الدالة setupSystem مرة واحدة من محرر Apps Script.'
    );
  }
  try {
    return SpreadsheetApp.openById(id);
  } catch (err) {
    throw new Error('تعذّر فتح جدول البيانات (' + id + '). تأكد أنه لم يُحذف من Drive.');
  }
}

/** يعيد ورقة باسمها، وينشئها بترويستها إن كانت مفقودة. */
function getSheet(name) {
  var book = openBook();
  var sheet = book.getSheetByName(name);
  if (!sheet) {
    sheet = book.insertSheet(name);
    writeHeader_(sheet, name);
  }
  return sheet;
}

function writeHeader_(sheet, name) {
  var headers = COLUMNS[name];
  if (!headers) throw new Error('ورقة غير معروفة: ' + name);
  sheet.getRange(1, 1, 1, headers.length).setValues([headers]);
  sheet.getRange(1, 1, 1, headers.length)
    .setFontWeight('bold')
    .setBackground('#16624F')
    .setFontColor('#FFFFFF');
  sheet.setFrozenRows(1);
  sheet.setRightToLeft(true);
}

/**
 * يقرأ الورقة كلها كمصفوفة كائنات مفاتيحها أسماء الأعمدة.
 * يضيف _row = رقم الصف في الورقة، للكتابة المباشرة لاحقاً.
 * التواريخ تُحوَّل إلى نص yyyy-MM-dd حتى تعبر إلى المتصفح بلا مفاجآت
 * منطقة زمنية.
 */
function readTable(name) {
  var sheet = getSheet(name);
  var lastRow = sheet.getLastRow();
  if (lastRow < 2) return [];

  var headers = COLUMNS[name];
  var values = sheet.getRange(2, 1, lastRow - 1, headers.length).getValues();
  var rows = [];

  for (var i = 0; i < values.length; i++) {
    var raw = values[i];
    // صف فارغ تماماً (أثر حذف يدوي) يُتجاوَز بدل أن يصير سجلاً بلا بيانات.
    if (raw.join('') === '') continue;

    var obj = { _row: i + 2 };
    for (var c = 0; c < headers.length; c++) {
      obj[headers[c]] = normalizeCell_(headers[c], raw[c]);
    }
    rows.push(obj);
  }
  return rows;
}

function normalizeCell_(header, value) {
  if (value === null || value === undefined) return '';
  if (DATE_FIELDS.indexOf(header) !== -1) return toDateString(value);
  if (header === 'الوقت والتاريخ' || header === 'تاريخ الإنشاء' || header === 'تاريخ التحديث') {
    return value instanceof Date ? value.toISOString() : String(value);
  }
  if (header === 'المعرف' || header === 'معرف الموظف' || header === 'ترتيب العرض' ||
      header === 'عدد الأيام') {
    return value === '' ? '' : Number(value);
  }
  return typeof value === 'string' ? value.trim() : value;
}

/** يحوّل أي قيمة تاريخ إلى yyyy-MM-dd، أو '' إن كانت فارغة أو غير صالحة. */
function toDateString(value) {
  if (!value && value !== 0) return '';
  if (value instanceof Date) {
    if (isNaN(value.getTime())) return '';
    return Utilities.formatDate(value, 'Asia/Riyadh', 'yyyy-MM-dd');
  }
  var text = String(value).trim();
  if (!text) return '';
  var m = text.match(/^(\d{4})-(\d{2})-(\d{2})/);
  if (m) return m[1] + '-' + m[2] + '-' + m[3];
  var parsed = new Date(text);
  if (isNaN(parsed.getTime())) return '';
  return Utilities.formatDate(parsed, 'Asia/Riyadh', 'yyyy-MM-dd');
}

/** يعيد سجلاً واحداً بمعرّفه، أو null. */
function findById(name, id) {
  var wanted = Number(id);
  var rows = readTable(name);
  for (var i = 0; i < rows.length; i++) {
    if (Number(rows[i]['المعرف']) === wanted) return rows[i];
  }
  return null;
}

/**
 * أكبر معرّف مستخدم + 1. يُحسب من الورقة نفسها لا من عدّاد محفوظ،
 * فيبقى صحيحاً حتى لو عُدِّلت الورقة يدوياً أو استُعيدت من نسخة.
 * يجب استدعاؤه داخل قفل.
 */
function nextId_(name) {
  var rows = readTable(name);
  var max = 0;
  for (var i = 0; i < rows.length; i++) {
    var id = Number(rows[i]['المعرف']);
    if (!isNaN(id) && id > max) max = id;
  }
  return max + 1;
}

/** يبني صفاً بترتيب الأعمدة من كائن. */
function toRowArray_(name, obj) {
  var headers = COLUMNS[name];
  var row = [];
  for (var i = 0; i < headers.length; i++) {
    var v = obj[headers[i]];
    row.push(v === undefined || v === null ? '' : v);
  }
  return row;
}

/** يُدرج سجلاً ويعيده بمعرّفه. يجب استدعاؤه داخل قفل. */
function insertRow(name, obj) {
  var sheet = getSheet(name);
  obj['المعرف'] = nextId_(name);
  sheet.appendRow(toRowArray_(name, obj));
  return obj;
}

/** يحدّث سجلاً بمعرّفه. يجب استدعاؤه داخل قفل. */
function updateRow(name, id, changes) {
  var existing = findById(name, id);
  if (!existing) throw new Error('السجل غير موجود (معرف ' + id + ').');

  var headers = COLUMNS[name];
  var merged = {};
  for (var i = 0; i < headers.length; i++) {
    merged[headers[i]] = headers[i] in changes ? changes[headers[i]] : existing[headers[i]];
  }
  merged['المعرف'] = existing['المعرف'];

  getSheet(name)
    .getRange(existing._row, 1, 1, headers.length)
    .setValues([toRowArray_(name, merged)]);
  return merged;
}

/** يحذف سجلاً نهائياً بمعرّفه. يجب استدعاؤه داخل قفل. */
function deleteRow(name, id) {
  var existing = findById(name, id);
  if (!existing) throw new Error('السجل غير موجود (معرف ' + id + ').');
  getSheet(name).deleteRow(existing._row);
  return existing;
}

/**
 * ينفّذ دالة داخل قفل السكربت.
 * كل عملية كتابة تمرّ من هنا. بدونه يمكن لتعديلين متزامنين أن يجتازا
 * فحص التفرُّد معاً، أو أن يكتب أحدهما فوق الآخر.
 */
function withLock(fn) {
  var lock = LockService.getScriptLock();
  try {
    lock.waitLock(LOCK_TIMEOUT_MS);
  } catch (err) {
    throw new Error('النظام مشغول بعملية حفظ أخرى. حاول بعد لحظات.');
  }
  try {
    return fn();
  } finally {
    lock.releaseLock();
  }
}

/**
 * يتحقق من عدم تكرار قيمة في عمود، باستثناء سجل بعينه (عند التعديل).
 * يجب استدعاؤه داخل القفل نفسه الذي ستتم الكتابة فيه.
 */
function assertUnique_(name, column, value, exceptId) {
  var text = String(value || '').trim();
  if (!text) return;
  var rows = readTable(name);
  for (var i = 0; i < rows.length; i++) {
    if (exceptId && Number(rows[i]['المعرف']) === Number(exceptId)) continue;
    if (String(rows[i][column] || '').trim() === text) {
      throw new Error(column + ' «' + text + '» مسجَّل بالفعل لموظف آخر.');
    }
  }
}

/** يعيد أسماء عناصر ورقة مرجعية مرتّبة. */
function referenceNames(sheetName) {
  var rows = readTable(sheetName);
  if (sheetName === SHEETS.NATIONALITIES) {
    rows.sort(function (a, b) {
      var oa = Number(a['ترتيب العرض']) || 0;
      var ob = Number(b['ترتيب العرض']) || 0;
      if (oa !== ob) return oa - ob;
      return String(a['الاسم']).localeCompare(String(b['الاسم']), 'ar');
    });
  } else {
    rows.sort(function (a, b) {
      return String(a['الاسم']).localeCompare(String(b['الاسم']), 'ar');
    });
  }
  return rows.map(function (r) { return r['الاسم']; });
}

/** الآن بصيغة ISO، للأعمدة الزمنية. */
function nowIso() {
  return new Date().toISOString();
}
