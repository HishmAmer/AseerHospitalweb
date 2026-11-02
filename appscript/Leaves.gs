/**
 * Leaves.gs — تسجيل الإجازات ومتابعتها.
 * الإجازة مربوطة بالموظف بمعرّفه، والاسم مخزَّن معها لقراءة الورقة بلا
 * مطابقة يدوية. إعادة تسمية الموظف تُحدّث إجازاته تلقائياً عبر syncLeaveNames_.
 */

function validateLeave_(user, input) {
  var errors = [];
  var clean = {};

  var employeeId = Number(input.employeeId);
  if (!employeeId) {
    errors.push('يجب اختيار الموظف.');
  } else {
    // داخل النطاق فقط: لا يسجّل حساب فرعي إجازة لموظف منشأة أخرى.
    var employee = scopedEmployee(user, employeeId, false);
    clean['معرف الموظف'] = employee['المعرف'];
    clean['اسم الموظف'] = employee['الاسم الرباعي'];
  }

  clean['نوع الإجازة'] = assertInList_(errors, String(input.leaveType || '').trim(), LEAVE_TYPES, 'نوع الإجازة', true);

  var start = toDateString(input.startDate);
  var end = toDateString(input.endDate);
  if (!start) errors.push('تاريخ بداية الإجازة إلزامي.');
  if (!end) errors.push('تاريخ نهاية الإجازة إلزامي.');
  if (start && end && end < start) {
    errors.push('تاريخ نهاية الإجازة لا يمكن أن يكون قبل تاريخ البداية.');
  }
  clean['تاريخ البداية'] = start;
  clean['تاريخ النهاية'] = end;
  clean['عدد الأيام'] = (start && end) ? daysBetween_(start, end) : '';
  clean['ملاحظات'] = String(input.notes || '').trim();

  if (errors.length) throw new Error(errors.join('\n'));
  return clean;
}

/** عدد أيام الإجازة شاملاً الطرفين. */
function daysBetween_(startString, endString) {
  var a = parseDateOnly_(startString);
  var b = parseDateOnly_(endString);
  if (!a || !b) return '';
  return Math.round((b - a) / 86400000) + 1;
}

function apiListLeaves() {
  var user = requireUser();

  // نطاق الإجازات تابع لنطاق الموظفين: يُبنى فهرس بالموظفين المرئيين.
  var visible = {};
  var scoped = scopedEmployees(user, false);
  for (var i = 0; i < scoped.length; i++) visible[Number(scoped[i]['المعرف'])] = true;

  var today = toDateString(new Date());
  var active = [];
  var history = [];
  var rows = readTable(SHEETS.LEAVES);

  for (var r = 0; r < rows.length; r++) {
    if (!visible[Number(rows[r]['معرف الموظف'])]) continue;
    var item = {
      id: rows[r]['المعرف'],
      employeeId: rows[r]['معرف الموظف'],
      employeeName: rows[r]['اسم الموظف'],
      leaveType: rows[r]['نوع الإجازة'],
      startDate: rows[r]['تاريخ البداية'],
      endDate: rows[r]['تاريخ النهاية'],
      days: rows[r]['عدد الأيام'],
      notes: rows[r]['ملاحظات']
    };
    (item.endDate >= today ? active : history).push(item);
  }

  active.sort(function (a, b) { return a.startDate < b.startDate ? -1 : 1; });
  history.sort(function (a, b) { return a.endDate > b.endDate ? -1 : 1; });
  return { active: active, history: history };
}

function apiGetLeave(id) {
  var user = requireUser();
  var leave = findById(SHEETS.LEAVES, id);
  if (!leave) throw new Error('الإجازة غير موجودة.');
  scopedEmployee(user, leave['معرف الموظف'], false);  // يتحقق من النطاق
  return {
    id: leave['المعرف'],
    employeeId: leave['معرف الموظف'],
    leaveType: leave['نوع الإجازة'],
    startDate: leave['تاريخ البداية'],
    endDate: leave['تاريخ النهاية'],
    notes: leave['ملاحظات']
  };
}

function apiCreateLeave(input) {
  var user = requireUser();
  return withLock(function () {
    var clean = validateLeave_(user, input);
    clean['تاريخ الإنشاء'] = nowIso();
    var saved = insertRow(SHEETS.LEAVES, clean);
    logActivity_(user, 'إضافة', 'تم تسجيل إجازة للموظف: ' + saved['اسم الموظف']);
    return { id: saved['المعرف'], message: 'تم تسجيل الإجازة بنجاح!' };
  });
}

function apiUpdateLeave(id, input) {
  var user = requireUser();
  return withLock(function () {
    var existing = findById(SHEETS.LEAVES, id);
    if (!existing) throw new Error('الإجازة غير موجودة.');
    scopedEmployee(user, existing['معرف الموظف'], false);

    var clean = validateLeave_(user, input);
    updateRow(SHEETS.LEAVES, id, clean);
    logActivity_(user, 'تعديل', 'تم تعديل إجازة الموظف: ' + clean['اسم الموظف']);
    return { message: 'تم تعديل بيانات الإجازة بنجاح!' };
  });
}

function apiDeleteLeave(id) {
  var user = requireUser();
  return withLock(function () {
    var existing = findById(SHEETS.LEAVES, id);
    if (!existing) throw new Error('الإجازة غير موجودة.');
    scopedEmployee(user, existing['معرف الموظف'], false);

    var name = existing['اسم الموظف'];
    deleteRow(SHEETS.LEAVES, id);
    logActivity_(user, 'حذف', 'تم إلغاء إجازة الموظف: ' + name);
    return { message: 'تم حذف الإجازة بنجاح.' };
  });
}

/** الموظفون المتاحون لاختيارهم في نموذج الإجازة. */
function apiLeaveEmployeeOptions() {
  var user = requireUser();
  return scopedEmployees(user, false).map(function (r) {
    return { id: r['المعرف'], name: r['الاسم الرباعي'] };
  });
}
