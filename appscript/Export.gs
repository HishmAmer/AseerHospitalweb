/**
 * Export.gs — تصدير سجل الموظفين إلى Excel.
 *
 * الأعمدة الاثنان وعشرون وترتيبها مطابقان لنظام Django، فتبقى الملفات
 * الصادرة من النظامين متبادلة وتقبلها أداة المطابقة في الاثنين.
 *
 * التصدير يحترم التصفية المعروضة ونطاق صلاحية المستخدم: ما تراه هو ما
 * يُصدَّر، لا السجل كاملاً.
 */

var EXPORT_HEADERS = [
  'الرقم الوظيفي', 'اسم الموظف', 'رقم الهوية', 'تاريخ الميلاد', 'العمر', 'الجنسية',
  'نوع المنشأة', 'التفرغ', 'المنشأة الحالية', 'القسم',
  'التخصص العام', 'التخصص الدقيق', 'فئة الموظف (نوع العقد)',
  'فئة الكادر', 'المسمى الوظيفي', 'حالة الموظف',
  'تاريخ بداية العقد', 'تاريخ نهاية العقد',
  'حالة التصنيف', 'رقم التصنيف', 'تاريخ انتهاء التصنيف',
  'مكلف بعمل إداري'
];

/**
 * يحيّد حقن صيغ الجداول.
 * حرف واحد لا يكوّن صيغة، فيُستثنى: الشرطة النائبة عن الخانة الفارغة كانت
 * تخرج ‎'-‎ لأن الفاصلة العليا المكتوبة برمجياً يعرضها إكسل كما هي.
 */
function excelSafe(value) {
  if (typeof value !== 'string') return value;
  if (value.length > 1 && '=+-@\t\r'.indexOf(value.charAt(0)) !== -1) return "'" + value;
  return value;
}

function exportRow_(row) {
  var dash = function (v) { return (v === '' || v === null || v === undefined) ? '-' : v; };
  return [
    dash(row['الرقم الوظيفي']),
    row['الاسم الرباعي'],
    dash(row['رقم الهوية']),
    dash(row['تاريخ الميلاد']),
    row['تاريخ الميلاد'] ? yearsSince(row['تاريخ الميلاد']) : '-',
    dash(row['الجنسية']),
    dash(row['نوع المنشأة']),
    dash(row['التفرغ']),
    dash(row['المنشأة الحالية']),
    dash(row['القسم']),
    dash(row['التخصص العام']),
    dash(row['التخصص الدقيق']),
    dash(row['فئة الموظف']),
    dash(row['فئة الكادر']),
    dash(row['المسمى الوظيفي']),
    row['حالة الموظف'],
    dash(row['تاريخ بداية العقد']),
    dash(row['تاريخ نهاية العقد']),
    row['حالة التصنيف'],
    dash(row['رقم التصنيف']),
    dash(row['تاريخ انتهاء التصنيف']),
    String(row['مكلف بعمل إداري']) === 'نعم' ? 'نعم' : 'لا'
  ].map(excelSafe);
}

/**
 * يبني ملف Excel ويعيد رابط تنزيله.
 * الملف يُنشأ مؤقتاً في Drive ثم يُحذف بعد أخذ بايتاته، فلا تتراكم نسخ
 * من بيانات المنسوبين في Drive بعد كل تصدير.
 */
function apiExportEmployees(filters) {
  var user = requireUser();
  filters = filters || {};

  var rows = scopedEmployees(user, false);
  var search = String(filters.search || '').trim();
  var status = String(filters.status || '').trim();
  var workplace = String(filters.workplace || '').trim();

  var selected = [];
  for (var i = 0; i < rows.length; i++) {
    var r = rows[i];
    if (status && String(r['حالة الموظف']) !== status) continue;
    if (workplace && user.isAdmin && String(r['المنشأة الحالية']) !== workplace) continue;
    if (search) {
      var hay = [r['الاسم الرباعي'], r['رقم الهوية'], r['الرقم الوظيفي']].join(' ');
      if (hay.indexOf(search) === -1) continue;
    }
    selected.push(r);
  }

  var temp = SpreadsheetApp.create('تصدير مؤقت ' + Utilities.getUuid());
  try {
    var sheet = temp.getActiveSheet();
    sheet.setName('بيانات الموظفين');
    sheet.setRightToLeft(true);

    var data = [EXPORT_HEADERS];
    for (var s = 0; s < selected.length; s++) data.push(exportRow_(selected[s]));
    sheet.getRange(1, 1, data.length, EXPORT_HEADERS.length).setValues(data);
    sheet.getRange(1, 1, 1, EXPORT_HEADERS.length)
      .setFontWeight('bold').setBackground('#16624F').setFontColor('#FFFFFF');
    sheet.setFrozenRows(1);
    for (var c = 1; c <= EXPORT_HEADERS.length; c++) sheet.setColumnWidth(c, 140);
    SpreadsheetApp.flush();

    var url = 'https://docs.google.com/spreadsheets/d/' + temp.getId() +
      '/export?format=xlsx&id=' + temp.getId();
    var blob = UrlFetchApp.fetch(url, {
      headers: { Authorization: 'Bearer ' + ScriptApp.getOAuthToken() },
      muteHttpExceptions: true
    }).getBlob();

    var stamp = Utilities.formatDate(new Date(), 'Asia/Riyadh', 'yyyy_MM_dd');
    logActivity_(user, 'نظام',
      'قام بتصدير بيانات الموظفين المفلترة إلى ملف Excel (' + selected.length + ' سجلاً)');

    return {
      fileName: 'Employees_Data_' + stamp + '.xlsx',
      mimeType: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      bytes: Utilities.base64Encode(blob.getBytes()),
      count: selected.length
    };
  } finally {
    // يُحذف دائماً، حتى لو فشل التصدير في منتصفه.
    DriveApp.getFileById(temp.getId()).setTrashed(true);
  }
}
