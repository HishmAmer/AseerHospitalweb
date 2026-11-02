/**
 * Dashboard.gs — الإحصاءات وبطاقات التنبيه.
 *
 * بطاقة التنبيه لا تظهر إن كان عددها صفراً: وجود بطاقة يعني وجود ما يستحق
 * التصرّف، فلا تتعوّد العين على تجاهلها.
 */

function apiDashboard() {
  var user = requireUser();
  var rows = scopedEmployees(user, false);
  var today = toDateString(new Date());
  var contractCutoff = shiftDays_(today, CONTRACT_ALERT_DAYS);
  var classCutoff = shiftDays_(today, CLASSIFICATION_ALERT_DAYS);

  var counts = {
    total: rows.length, active: 0, male: 0, female: 0,
    resigned: 0, terminated: 0, delegated: 0,
    resident: 0, registrar: 0, seniorRegistrar: 0, consultant: 0
  };

  var expiredContracts = [];
  var expiringContracts = [];
  var expiredClassifications = [];
  var expiringClassifications = [];

  for (var i = 0; i < rows.length; i++) {
    var r = rows[i];
    var status = String(r['حالة الموظف']);

    if (status === 'نشط') {
      counts.active++;
      if (r['الجنس'] === 'ذكر') counts.male++;
      if (r['الجنس'] === 'أنثى') counts.female++;
      switch (String(r['فئة الكادر'])) {
        case 'مقيم': counts.resident++; break;
        case 'نائب': counts.registrar++; break;
        case 'نائب أول': counts.seniorRegistrar++; break;
        case 'استشاري': counts.consultant++; break;
      }
    }
    if (status === 'مستقيل') counts.resigned++;
    if (status === 'طي القيد') counts.terminated++;
    if (status === 'إيفاد') counts.delegated++;

    if (status !== 'نشط') continue;

    var end = r['تاريخ نهاية العقد'];
    if (end) {
      if (end < today) expiredContracts.push(alertItem_(r, end));
      else if (end <= contractCutoff) expiringContracts.push(alertItem_(r, end));
    }

    if (String(r['حالة التصنيف']) === 'مصنف') {
      var exp = r['تاريخ انتهاء التصنيف'];
      if (exp) {
        if (exp < today) expiredClassifications.push(alertItem_(r, exp));
        else if (exp <= classCutoff) expiringClassifications.push(alertItem_(r, exp));
      }
    }
  }

  var byDate = function (a, b) { return a.date < b.date ? -1 : 1; };
  expiredContracts.sort(byDate);
  expiringContracts.sort(byDate);
  expiredClassifications.sort(byDate);
  expiringClassifications.sort(byDate);

  return {
    scope: scopeLabel(user),
    user: { name: user.name, email: user.email, isAdmin: user.isAdmin },
    counts: counts,
    onLeave: countOnLeave_(user, today),
    alerts: {
      expiredContracts: expiredContracts,
      expiringContracts: expiringContracts,
      expiredClassifications: expiredClassifications,
      expiringClassifications: expiringClassifications,
      contractDays: CONTRACT_ALERT_DAYS,
      classificationDays: CLASSIFICATION_ALERT_DAYS
    }
  };
}

function alertItem_(row, date) {
  return {
    id: row['المعرف'],
    name: row['الاسم الرباعي'],
    workplace: row['المنشأة الحالية'],
    date: date
  };
}

function countOnLeave_(user, today) {
  var visible = {};
  var scoped = scopedEmployees(user, false);
  for (var i = 0; i < scoped.length; i++) {
    if (String(scoped[i]['حالة الموظف']) === 'نشط') {
      visible[Number(scoped[i]['المعرف'])] = true;
    }
  }
  var leaves = readTable(SHEETS.LEAVES);
  var count = 0;
  for (var l = 0; l < leaves.length; l++) {
    if (!visible[Number(leaves[l]['معرف الموظف'])]) continue;
    if (leaves[l]['تاريخ البداية'] <= today && leaves[l]['تاريخ النهاية'] >= today) count++;
  }
  return count;
}

/** تاريخ بعد عدد أيام، بصيغة yyyy-MM-dd. */
function shiftDays_(dateString, days) {
  var d = parseDateOnly_(dateString);
  d.setDate(d.getDate() + days);
  return Utilities.formatDate(d, 'Asia/Riyadh', 'yyyy-MM-dd');
}
