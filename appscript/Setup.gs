/**
 * Setup.gs — تهيئة النظام مرة واحدة.
 *
 * شغّل setupSystem() من محرر Apps Script قبل أي استخدام. تنشئ جدول
 * البيانات وأوراقه وترويساته، وتزرع الجنسيات، وتجعل من يشغّلها أول مدير
 * نظام. آمنة التكرار: لا تمسح بيانات قائمة.
 */

/**
 * قائمة الجنسيات الابتدائية، مرتّبة حسب المنطقة لا أبجدياً («سعودي» أولاً)
 * حتى تبقى القائمة مألوفة لمن يُدخل البيانات. تُضاف الجنسيات وتُصحَّح
 * لاحقاً من صفحة إعدادات النظام.
 */
var SEED_NATIONALITIES = [
   'سعودي', 'إماراتي', 'كويتي', 'قطري', 'عماني', 'بحريني', 'مصري', 'يمني', 'سوداني', 'أردني',
   'سوري', 'فلسطيني', 'لبناني', 'عراقي', 'تونسي', 'مغربي', 'جزائري', 'ليبي', 'صومالي',
   'موريتاني', 'جيبوتي', 'قمري', 'هندي', 'فلبيني', 'باكستاني', 'بنغلاديشي', 'إندونيسي',
   'سريلانكي', 'نيبالي', 'ماليزي', 'أفغاني', 'ميانماري', 'صيني', 'ياباني', 'كوري',
   'كوري شمالي', 'تايلاندي', 'فيتنامي', 'سنغافوري', 'تركي', 'إيراني', 'أوزبكي', 'طاجيكي',
   'كازاخي', 'قيرغيزي', 'تركماني', 'أذربيجاني', 'أرميني', 'جورجي', 'منغولي', 'كمبودي',
   'لاوسي', 'بروناوي', 'تيموري', 'مالديفي', 'بوتاني', 'قبرصي', 'جنوب أفريقي', 'نيجيري',
   'كينى', 'إثيوبي', 'إريتري', 'تشادي', 'غاني', 'أوغندي', 'مالي', 'سنغالي', 'كوت ديفوار',
   'كاميروني', 'رواندي', 'جنوب سوداني', 'تنزاني', 'زامبي', 'زيمبابوي', 'موزمبيقي', 'أنغولي',
   'ناميبي', 'بوتسواني', 'ملاوي', 'بوروندي', 'كونغولي', 'كونغولي برازافيل', 'غابوني', 'غيني',
   'بيساوي', 'غيني استوائي', 'بنيني', 'توغولي', 'بوركيني', 'نيجري', 'سيراليوني', 'ليبيري',
   'غامبي', 'رأس أخضر', 'مدغشقري', 'موريشيوسي', 'سيشلي', 'أفريقي وسطي', 'ليسوتي', 'إسواتيني',
   'ساوتومي', 'بريطاني', 'فرنسي', 'ألماني', 'إيطالي', 'إسباني', 'هولندي', 'سويدي', 'سويسري',
   'نمساوي', 'بلجيكي', 'برتغالي', 'دانماركي', 'نرويجي', 'فنلندي', 'بولندي', 'يوناني', 'روسي',
   'أوكراني', 'بوسني', 'ألباني', 'روماني', 'أيرلندي', 'آيسلندي', 'تشيكي', 'سلوفاكي', 'مجري',
   'بلغاري', 'صربي', 'كرواتي', 'سلوفيني', 'مقدوني', 'جبل أسود', 'كوسوفي', 'ليتواني', 'لاتفي',
   'إستوني', 'بيلاروسي', 'مولدوفي', 'مالطي', 'لوكسمبورغي', 'ليختنشتايني', 'موناكي', 'أندوري',
   'سان ماريني', 'أمريكي', 'كندي', 'برازيلي', 'أرجنتيني', 'فنزويلي', 'مكسيكي', 'كولومبي',
   'كوبي', 'تشيلي', 'بيروفي', 'إكوادوري', 'بوليفي', 'أوروغواياني', 'باراغواياني', 'غوياني',
   'سورينامي', 'بنمي', 'كوستاريكي', 'نيكاراغوي', 'هندوراسي', 'سلفادوري', 'غواتيمالي', 'بليزي',
   'دومينيكاني', 'هايتي', 'جامايكي', 'ترينيدادي', 'بربادوسي', 'بهامي', 'أسترالي', 'نيوزيلندي',
   'بابوي', 'فيجي', 'ساموي', 'تونغي', 'فانواتي', 'سليماني', 'كيريباتي', 'ميكرونيزي', 'بالاوي',
   'ناوروي', 'توفالي', 'مارشالي', 'بدون جنسية', 'أخرى',
];

/** التهيئة الكاملة — شغّلها مرة واحدة. */
function setupSystem() {
  var props = PropertiesService.getScriptProperties();
  var existingId = props.getProperty(PROP_SPREADSHEET_ID);
  var book;

  if (existingId) {
    book = SpreadsheetApp.openById(existingId);
    Logger.log('جدول بيانات قائم: ' + book.getUrl());
  } else {
    book = SpreadsheetApp.create('نظام إدارة الكادر الطبي — تجمع عسير الصحي');
    props.setProperty(PROP_SPREADSHEET_ID, book.getId());
    Logger.log('أُنشئ جدول بيانات جديد: ' + book.getUrl());
  }

  ensureSchema_(book);
  seedNationalities_();
  var admin = ensureFirstAdmin_();

  var report = [
    'اكتملت التهيئة.',
    'جدول البيانات: ' + book.getUrl(),
    'مدير النظام الأول: ' + admin,
    '',
    'الخطوة التالية: Deploy ← New deployment ← Web app',
    '  Execute as: Me',
    '  Who has access: Anyone with Google account'
  ].join('\n');
  Logger.log(report);
  return report;
}

/**
 * ينشئ الأوراق الناقصة ويصحّح الترويسات.
 * إضافة عمود جديد في Config يُكتب هنا تلقائياً دون المساس بالبيانات.
 */
function ensureSchema_(book) {
  var names = [];
  for (var key in SHEETS) names.push(SHEETS[key]);

  for (var i = 0; i < names.length; i++) {
    var name = names[i];
    var sheet = book.getSheetByName(name);
    if (!sheet) sheet = book.insertSheet(name);

    var headers = COLUMNS[name];
    var width = Math.max(sheet.getLastColumn(), headers.length);
    if (sheet.getMaxColumns() < headers.length) {
      sheet.insertColumnsAfter(sheet.getMaxColumns(), headers.length - sheet.getMaxColumns());
    }
    sheet.getRange(1, 1, 1, headers.length).setValues([headers]);
    sheet.getRange(1, 1, 1, headers.length)
      .setFontWeight('bold').setBackground('#16624F').setFontColor('#FFFFFF');
    sheet.setFrozenRows(1);
    sheet.setRightToLeft(true);
    for (var c = 1; c <= headers.length; c++) sheet.setColumnWidth(c, 150);
  }

  // الورقة الافتراضية الفارغة التي ينشئها Google مع الملف الجديد.
  var blank = book.getSheetByName('Sheet1') || book.getSheetByName('ورقة1');
  if (blank && book.getSheets().length > 1) book.deleteSheet(blank);
}

/** يزرع الجنسيات الناقصة فقط — لا يمسّ ما أُضيف أو عُدِّل يدوياً. */
function seedNationalities_() {
  return withLock(function () {
    var existing = {};
    var rows = readTable(SHEETS.NATIONALITIES);
    for (var i = 0; i < rows.length; i++) existing[String(rows[i]['الاسم']).trim()] = true;

    var sheet = getSheet(SHEETS.NATIONALITIES);
    var nextId = rows.length ? nextId_(SHEETS.NATIONALITIES) : 1;
    var toAppend = [];

    for (var n = 0; n < SEED_NATIONALITIES.length; n++) {
      var name = SEED_NATIONALITIES[n];
      if (existing[name]) continue;
      toAppend.push([nextId++, name, n + 1]);
    }
    if (toAppend.length) {
      sheet.getRange(sheet.getLastRow() + 1, 1, toAppend.length, 3).setValues(toAppend);
    }
    Logger.log('جنسيات مضافة: ' + toAppend.length);
    return toAppend.length;
  });
}

/** يجعل مُشغِّل التهيئة أول مدير نظام، إن لم يكن هناك مدير بعد. */
function ensureFirstAdmin_() {
  var email = currentEmail() || Session.getEffectiveUser().getEmail();
  if (!email) throw new Error('تعذّر تحديد بريدك الإلكتروني. شغّل الدالة من محرر Apps Script.');
  email = String(email).trim().toLowerCase();

  return withLock(function () {
    var rows = readTable(SHEETS.USERS);
    for (var i = 0; i < rows.length; i++) {
      if (String(rows[i]['البريد الإلكتروني']).trim().toLowerCase() === email) {
        // موجود: اضمن أنه مدير مفعَّل حتى لا يُقفل على نفسه خارج النظام.
        updateRow(SHEETS.USERS, rows[i]['المعرف'], {
          'الصلاحية': 'admin', 'المنشأة التابع لها': '', 'الحالة': 'مفعَّل'
        });
        return email + ' (كان مسجَّلاً — أُعيد ضبطه كمدير نظام)';
      }
    }
    insertRow(SHEETS.USERS, {
      'البريد الإلكتروني': email,
      'الاسم': email.split('@')[0],
      'الصلاحية': 'admin',
      'المنشأة التابع لها': '',
      'الحالة': 'مفعَّل',
      'تاريخ الإنشاء': nowIso()
    });
    return email;
  });
}

/** يعيد رابط جدول البيانات — للرجوع إليه بعد التهيئة. */
function showSpreadsheetUrl() {
  var url = openBook().getUrl();
  Logger.log(url);
  return url;
}
