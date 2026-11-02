/**
 * WebApp.gs — نقطة دخول تطبيق الويب.
 *
 * صفحة واحدة تُحمَّل مرة، والتنقّل داخلها بلا إعادة تحميل، لأن كل طلب إلى
 * الخادم في Apps Script يكلّف من حصة التنفيذ اليومية.
 */

function doGet(e) {
  var user = currentUser();

  if (!user) {
    return HtmlService.createTemplateFromFile('NoAccess')
      .evaluate()
      .setTitle('نظام إدارة الكادر الطبي — تجمع عسير الصحي')
      .addMetaTag('viewport', 'width=device-width, initial-scale=1');
  }

  var template = HtmlService.createTemplateFromFile('Index');
  template.bootUser = JSON.stringify({
    name: user.name,
    email: user.email,
    isAdmin: user.isAdmin,
    scope: scopeLabel(user)
  });
  return template.evaluate()
    .setTitle('نظام إدارة الكادر الطبي — تجمع عسير الصحي')
    .addMetaTag('viewport', 'width=device-width, initial-scale=1')
    .setXFrameOptionsMode(HtmlService.XFrameOptionsMode.DEFAULT);
}

/** يُضمّن ملف HTML داخل آخر (الأنماط والسكربتات). */
function include(filename) {
  return HtmlService.createHtmlOutputFromFile(filename).getContent();
}

/** بيانات الإقلاع: هوية المستخدم والقوائم المرجعية في طلب واحد. */
function apiBootstrap() {
  var user = requireUser();
  var reference = apiReferenceData();
  return {
    user: {
      name: user.name, email: user.email,
      isAdmin: user.isAdmin, scope: scopeLabel(user)
    },
    reference: reference
  };
}

/** رابط جدول البيانات — لمدير النظام فقط. */
function apiSpreadsheetUrl() {
  requireAdmin();
  return openBook().getUrl();
}
