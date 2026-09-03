"""مطابقة ملف Excel مع سجلات الموظفين في النظام.

المنطق هنا خالٍ من HTTP ومن الاعتماد على الطلب، ليبقى قابلاً للاختبار مباشرة.
العملية للقراءة فقط: لا تُكتب أي بيانات في قاعدة البيانات.
"""

import datetime
import re

import openpyxl

# سقف الصفوف يحمي من ملف ضخم يستهلك الذاكرة. الرقم أكبر بكثير من أي
# كشف موظفين واقعي، وتُبلَّغ التجاوزات للمستخدم بدل تجاهلها بصمت.
MAX_ROWS = 20000
MAX_COLUMNS = 60

# الأرقام العربية الهندية ترد كثيراً في ملفات Excel المحلية.
ARABIC_DIGITS = str.maketrans('٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹', '01234567890123456789')

# ترويسات الملف كما يصدّرها النظام نفسه، مقابل مفاتيح داخلية.
# المطابقة تتم بعد تطبيع النص، فتُقبل الفروق في المسافات والتشكيل الشائع.
COLUMN_ALIASES = {
    'الرقم الوظيفي': 'employee_number',
    'رقم الموظف': 'employee_number',
    'اسم الموظف': 'full_name',
    'الاسم': 'full_name',
    'الاسم الرباعي': 'full_name',
    'رقم الهوية': 'national_id',
    'رقم الهوية / الاقامة': 'national_id',
    'رقم الهوية / الإقامة': 'national_id',
    'الهوية': 'national_id',
    'تاريخ الميلاد': 'dob',
    'الجنسية': 'nationality',
    'نوع المنشاة': 'workplace_type',
    'نوع المنشأة': 'workplace_type',
    'التفرغ': 'time_type',
    'المنشاة الحالية': 'current_workplace',
    'المنشأة الحالية': 'current_workplace',
    'القسم': 'current_department',
    'فئة الموظف (نوع العقد)': 'employee_type',
    'فئة الموظف': 'employee_type',
    'فئة الكادر': 'employee_category',
    'المسمى الوظيفي': 'contract_job_title',
    'حالة الموظف': 'status',
    'الحالة': 'status',
    'تاريخ بداية العقد': 'contract_start_date',
    'تاريخ نهاية العقد': 'contract_end_date',
    'حالة التصنيف': 'is_classified',
    'تاريخ انتهاء التصنيف': 'classification_expiry_date',
}

# الحقول التي تُقارَن، بترتيب عرضها في التقرير.
COMPARED_FIELDS = [
    ('full_name', 'اسم الموظف'),
    ('employee_number', 'الرقم الوظيفي'),
    ('national_id', 'رقم الهوية'),
    ('dob', 'تاريخ الميلاد'),
    ('nationality', 'الجنسية'),
    ('workplace_type', 'نوع المنشأة'),
    ('time_type', 'التفرغ'),
    ('current_workplace', 'المنشأة الحالية'),
    ('current_department', 'القسم'),
    ('employee_type', 'فئة الموظف (نوع العقد)'),
    ('employee_category', 'فئة الكادر'),
    ('contract_job_title', 'المسمى الوظيفي'),
    ('status', 'حالة الموظف'),
    ('contract_start_date', 'تاريخ بداية العقد'),
    ('contract_end_date', 'تاريخ نهاية العقد'),
    ('is_classified', 'حالة التصنيف'),
    ('classification_expiry_date', 'تاريخ انتهاء التصنيف'),
]

DATE_FIELDS = {'dob', 'contract_start_date', 'contract_end_date', 'classification_expiry_date'}

# الحقول التي يُعدّ خلوّها نقصاً يستحق التنبيه.
REQUIRED_FIELDS = [
    ('national_id', 'رقم الهوية'),
    ('employee_number', 'الرقم الوظيفي'),
    ('current_workplace', 'المنشأة الحالية'),
    ('current_department', 'القسم'),
    ('employee_category', 'فئة الكادر'),
    ('contract_end_date', 'تاريخ نهاية العقد'),
]


class ExcelFormatError(Exception):
    """الملف غير صالح للقراءة أو لا يحتوي الأعمدة المطلوبة."""


def normalize_header(value):
    """يوحّد نص الترويسة: مسافات مضغوطة، وهمزات موحّدة، بلا تشكيل."""
    if value is None:
        return ''
    text = str(value).strip()
    text = re.sub(r'[ً-ْـ]', '', text)   # تشكيل وتطويل
    text = re.sub(r'\s+', ' ', text)
    return text


def normalize_text(value):
    """يحوّل قيمة خلية إلى نص مُطبَّع، أو None إن كانت فارغة فعلياً."""
    if value is None:
        return None

    if isinstance(value, float) and value.is_integer():
        value = int(value)          # 1010101010.0 -> 1010101010

    if isinstance(value, (datetime.datetime, datetime.date)):
        return to_date(value)

    text = str(value).strip()
    text = text.translate(ARABIC_DIGITS)
    text = re.sub(r'\s+', ' ', text)

    # الشرطة علامة "لا قيمة" في ملفات التصدير.
    if text in ('', '-', '—', 'None', 'null'):
        return None
    return text


def to_date(value):
    """يحوّل قيمة إلى date، أو يعيدها كما هي إن تعذّر ذلك."""
    if isinstance(value, datetime.datetime):
        return value.date()
    if isinstance(value, datetime.date):
        return value

    text = normalize_text(value)
    if text is None or isinstance(text, datetime.date):
        return text

    for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%Y/%m/%d', '%d-%m-%Y'):
        try:
            return datetime.datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return text        # نص غير قابل للتحويل — يُعرض كما هو ويُعدّ اختلافاً


def normalize_id(value):
    """مفتاح المطابقة: أرقام لاتينية، بلا مسافات أو شرطات."""
    text = normalize_text(value)
    if text is None or isinstance(text, datetime.date):
        return None
    return re.sub(r'[\s\-_]', '', str(text))


def read_rows(file_obj):
    """يقرأ الملف ويعيد (صفوف، ترويسات معروفة، ترويسات مجهولة).

    كل صف قاموس {مفتاح الحقل: قيمة مُطبَّعة} مضافاً إليه رقم السطر.
    """
    try:
        workbook = openpyxl.load_workbook(file_obj, read_only=True, data_only=True)
    except Exception as exc:                       # ملف تالف أو ليس xlsx
        raise ExcelFormatError(
            'تعذّرت قراءة الملف. تأكد أنه بصيغة Excel حديثة (.xlsx) وغير تالف.'
        ) from exc

    try:
        sheet = workbook.worksheets[0]
        rows = sheet.iter_rows(values_only=True)

        header_row = None
        for row in rows:
            if any(cell is not None and str(cell).strip() for cell in row):
                header_row = row
                break

        if header_row is None:
            raise ExcelFormatError('الملف فارغ — لا يحتوي على أي بيانات.')

        header_row = header_row[:MAX_COLUMNS]
        mapping, unknown = {}, []
        for index, cell in enumerate(header_row):
            name = normalize_header(cell)
            if not name:
                continue
            field = COLUMN_ALIASES.get(name)
            if field:
                mapping.setdefault(field, index)
            else:
                unknown.append(name)

        if 'national_id' not in mapping and 'employee_number' not in mapping:
            raise ExcelFormatError(
                'لم يُعثر على عمود «رقم الهوية» ولا «الرقم الوظيفي». '
                'أحدهما مطلوب للمطابقة — استخدم ملف التصدير من النظام كقالب.'
            )

        records, truncated = [], False
        for line_number, row in enumerate(rows, start=2):
            if len(records) >= MAX_ROWS:
                truncated = True
                break
            if not any(cell is not None and str(cell).strip() for cell in row):
                continue

            record = {'_row': line_number}
            for field, index in mapping.items():
                value = row[index] if index < len(row) else None
                record[field] = to_date(value) if field in DATE_FIELDS else normalize_text(value)
            records.append(record)

        return records, set(mapping), unknown, truncated
    finally:
        workbook.close()


def employee_snapshot(employee):
    """يمثّل سجل موظف بنفس شكل صف الملف، ليصح المقارنة بينهما."""
    return {
        'full_name': employee.full_name,
        'employee_number': employee.employee_number or None,
        'national_id': employee.national_id or None,
        'dob': employee.dob,
        'nationality': employee.nationality.name if employee.nationality else None,
        'workplace_type': employee.workplace_type or None,
        'time_type': employee.time_type or None,
        'current_workplace': employee.current_workplace.name if employee.current_workplace else None,
        'current_department': employee.current_department.name if employee.current_department else None,
        'employee_type': employee.employee_type or None,
        'employee_category': employee.employee_category or None,
        'contract_job_title': employee.contract_job_title or None,
        'status': employee.status or None,
        'contract_start_date': employee.contract_start_date,
        'contract_end_date': employee.contract_end_date,
        'is_classified': employee.is_classified or None,
        'classification_expiry_date': employee.classification_expiry_date,
    }


def values_match(field, file_value, db_value):
    if file_value is None or db_value is None:
        return file_value == db_value
    if field in ('national_id', 'employee_number'):
        return normalize_id(file_value) == normalize_id(db_value)
    if isinstance(file_value, datetime.date) or isinstance(db_value, datetime.date):
        return file_value == db_value
    return str(file_value).strip() == str(db_value).strip()


def display(value):
    if value is None:
        return '—'
    if isinstance(value, datetime.date):
        return value.strftime('%Y-%m-%d')
    return str(value)


def compare(file_obj, employees):
    """يقارن ملف Excel بمجموعة موظفين ويعيد تقريراً مفصّلاً.

    `employees` مجموعة استعلام أو قائمة سجلات ضمن نطاق صلاحية المستخدم،
    فلا يكشف التقرير أي بيانات خارج ذلك النطاق.
    """
    records, present_fields, unknown_headers, truncated = read_rows(file_obj)

    by_national_id, by_employee_number = {}, {}
    for employee in employees:
        if employee.national_id:
            by_national_id[normalize_id(employee.national_id)] = employee
        if employee.employee_number:
            by_employee_number[normalize_id(employee.employee_number)] = employee

    missing_in_system = []   # في الملف وغير موجود في النظام
    differences = []         # موجود في الاثنين لكن القيم مختلفة
    unreadable_rows = []     # صفوف بلا معرّف أو مكررة
    matched_ids = set()
    seen_keys = {}

    for record in records:
        national_key = normalize_id(record.get('national_id'))
        number_key = normalize_id(record.get('employee_number'))

        if not national_key and not number_key:
            unreadable_rows.append({
                'row': record['_row'],
                'name': display(record.get('full_name')),
                'reason': 'لا يحتوي الصف على رقم هوية ولا رقم وظيفي',
            })
            continue

        key = national_key or number_key
        if key in seen_keys:
            unreadable_rows.append({
                'row': record['_row'],
                'name': display(record.get('full_name')),
                'reason': f'مكرر في الملف — ورد سابقاً في السطر {seen_keys[key]}',
            })
            continue
        seen_keys[key] = record['_row']

        employee = by_national_id.get(national_key) or by_employee_number.get(number_key)

        if employee is None:
            missing_in_system.append({
                'row': record['_row'],
                'full_name': display(record.get('full_name')),
                'national_id': display(record.get('national_id')),
                'employee_number': display(record.get('employee_number')),
                'current_workplace': display(record.get('current_workplace')),
                'current_department': display(record.get('current_department')),
                'employee_category': display(record.get('employee_category')),
            })
            continue

        matched_ids.add(employee.pk)
        snapshot = employee_snapshot(employee)
        changed = [
            {'label': label, 'file': display(record[field]), 'system': display(snapshot[field])}
            for field, label in COMPARED_FIELDS
            if field in present_fields and field in record
            and not values_match(field, record[field], snapshot[field])
        ]
        if changed:
            differences.append({
                'row': record['_row'],
                'employee': employee,
                'fields': changed,
            })

    # في النظام ولم يرد في الملف
    missing_in_file = [e for e in employees if e.pk not in matched_ids]

    # سجلات النظام الناقصة بيانات جوهرية
    incomplete = []
    for employee in employees:
        snapshot = employee_snapshot(employee)
        blanks = [label for field, label in REQUIRED_FIELDS if snapshot[field] in (None, '')]
        if blanks:
            incomplete.append({'employee': employee, 'blanks': blanks})

    return {
        'total_rows': len(records),
        'total_system': len(employees),
        'matched_count': len(matched_ids),
        'missing_in_system': missing_in_system,
        'missing_in_file': missing_in_file,
        'differences': differences,
        'unreadable_rows': unreadable_rows,
        'incomplete': incomplete,
        'unknown_headers': unknown_headers,
        'ignored_fields': [
            label for field, label in COMPARED_FIELDS if field not in present_fields
        ],
        'truncated': truncated,
        'max_rows': MAX_ROWS,
    }
