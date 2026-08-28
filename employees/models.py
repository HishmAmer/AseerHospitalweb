from django.db import models
from django.contrib.auth.models import User
from datetime import date

# ==========================================
# 1. الجداول المرجعية (الإعدادات)
# ==========================================
class Workplace(models.Model):
    name = models.CharField(max_length=150, verbose_name='اسم المنشأة')
    def __str__(self):
        return self.name
class Department(models.Model):
    name = models.CharField(max_length=150, verbose_name='القسم / الإدارة')
    def __str__(self):
        return self.name
class GeneralSpecialty(models.Model):
    name = models.CharField(max_length=150, verbose_name='التخصص العام')
    def __str__(self):
        return self.name

class SubSpecialty(models.Model):
    name = models.CharField(max_length=150, verbose_name='التخصص الدقيق')
    def __str__(self):
        return self.name

# ==========================================
# 2. ملف تعريف المستخدم
# ==========================================
class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile', verbose_name='المستخدم')
    workplace = models.ForeignKey(Workplace, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='المنشأة التابع لها')

    def __str__(self):
        return f"ملف: {self.user.username}"

# ==========================================
# 3. سجل النشاطات (Audit Log)
# ==========================================
class ActivityLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name='المستخدم')
    action_type = models.CharField(max_length=50, verbose_name='نوع الإجراء')
    description = models.TextField(verbose_name='التفاصيل')
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name='الوقت والتاريخ')

    def __str__(self):
        return f"{self.user} - {self.action_type}"

# ==========================================
# 4. جدول الموظفين الأساسي
# ==========================================
class Employee(models.Model): 
    STATUS_CHOICES = (
        ('نشط', 'نشط'), ('مستقيل', 'مستقيل'), 
        ('طي القيد', 'طي القيد'), ('إيفاد', 'إيفاد'),
    )
    
    # 🆕 قائمة الكادر (التي كانت المسمى الوظيفي سابقاً)
    CATEGORY_CHOICES = (
        ('مقيم', 'طبيب مقيم'), ('نائب', 'طبيب نائب'),
        ('نائب أول', 'نائب أول'), ('استشاري', 'طبيب استشاري'),
    )
    
    NATIONALITY_CHOICES = (
        ('سعودي', 'سعودي'), ('مصري', 'مصري'), ('أردني', 'أردني'), 
        ('سوداني', 'سوداني'), ('سوري', 'سوري'), ('فلسطيني', 'فلسطيني'), 
        ('يمني', 'يمني'), ('لبناني', 'لبناني'), ('عراقي', 'عراقي'), 
        ('تونسي', 'تونسي'), ('مغربي', 'مغربي'), ('جزائري', 'جزائري'), 
        ('ليبي', 'ليبي'), ('عماني', 'عماني'), ('إماراتي', 'إماراتي'), 
        ('كويتي', 'كويتي'), ('بحريني', 'بحريني'), ('قطري', 'قطري'), 
        ('هندي', 'هندي'), ('فلبيني', 'فلبيني'), ('باكستاني', 'باكستاني'), 
        ('بنغلاديشي', 'بنغلاديشي'), ('إندونيسي', 'إندونيسي'), 
        ('سريلانكي', 'سريلانكي'), ('نيبالي', 'نيبالي'), ('ماليزي', 'ماليزي'), 
        ('أمريكي', 'أمريكي'), ('بريطاني', 'بريطاني'), ('كندي', 'كندي'), 
        ('أسترالي', 'أسترالي'), ('جنوب أفريقي', 'جنوب أفريقي'), 
        ('نيجيري', 'نيجيري'), ('كينى', 'كينى'), ('تركي', 'تركي'), 
        ('أخرى', 'أخرى')
    )

    EMPLOYEE_TYPE_CHOICES = (
        ('تشغيل ذاتي', 'تشغيل ذاتي'),
        ('خدمة مدنية', 'خدمة مدنية'),
        ('عقود الصحة القابضة', 'عقود الصحة القابضة')
    )

    CLASSIFICATION_CHOICES = (
        ('مصنف', 'مصنف'), ('غير مصنف', 'غير مصنف'),
    )

    WORKPLACE_TYPE_CHOICES = (
        ('مستشفى عام', 'مستشفى عام'),
        ('مدن طبية', 'مدن طبية'),
        ('جامعة الملك خالد', 'جامعة الملك خالد'),
    )
    
    TIME_TYPE_CHOICES = (
        ('جزئي', 'جزئي'), ('كلي', 'كلي'),
    )

    YES_NO_CHOICES = (
        ('نعم', 'نعم'), ('لا', 'لا'),
    )

    full_name = models.CharField(max_length=150, verbose_name='الاسم الرباعي')
    national_id = models.CharField(max_length=20, unique=True, null=True, blank=True, verbose_name='رقم الهوية / الإقامة')
    employee_number = models.CharField(max_length=20, unique=True, null=True, blank=True, verbose_name='الرقم الوظيفي')
    
    nationality = models.CharField(max_length=50, choices=NATIONALITY_CHOICES, default='سعودي', verbose_name='الجنسية')
    dob = models.DateField(null=True, blank=True, verbose_name='تاريخ الميلاد')
    gender = models.CharField(max_length=10, choices=(('M', 'ذكر'), ('F', 'أنثى')), verbose_name='الجنس')
    mobile_number = models.CharField(max_length=20, null=True, blank=True, verbose_name='رقم الجوال')

    # 🆕 تفاصيل المنشأة
    workplace_type = models.CharField(max_length=50, choices=WORKPLACE_TYPE_CHOICES, null=True, blank=True, verbose_name='نوع المنشأة')
    time_type = models.CharField(max_length=20, choices=TIME_TYPE_CHOICES, null=True, blank=True, verbose_name='التفرغ')
    current_workplace = models.ForeignKey(Workplace, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='المنشأة الحالية')
    current_department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='القسم الذي يعمل به')
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='نشط', verbose_name='حالة الموظف')
    employee_type = models.CharField(max_length=50, choices=EMPLOYEE_TYPE_CHOICES, null=True, blank=True, verbose_name='فئة الموظف')
    
    general_specialty = models.ForeignKey(GeneralSpecialty, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='التخصص العام')
    has_sub_specialty = models.CharField(max_length=10, choices=YES_NO_CHOICES, default='لا', verbose_name='هل يوجد تخصص دقيق؟')
    sub_specialty = models.ForeignKey(SubSpecialty, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='التخصص الدقيق')
    
    is_classified = models.CharField(max_length=20, choices=CLASSIFICATION_CHOICES, default='غير مصنف', verbose_name='حالة التصنيف')
    classification_expiry_date = models.DateField(verbose_name='تاريخ انتهاء التصنيف', null=True, blank=True, db_index=True)

    # 🆕 الفئة والمسمى
    employee_category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, null=True, blank=True, verbose_name='فئة الموظف (الكادر)')
    contract_job_title = models.CharField(max_length=150, null=True, blank=True, verbose_name='المسمى الوظيفي بالعقد')
    
    contract_start_date = models.DateField(null=True, blank=True, verbose_name='تاريخ بداية العقد')
    contract_end_date = models.DateField(null=True, blank=True, verbose_name='تاريخ نهاية العقد')

    is_admin_assigned = models.BooleanField(default=False, verbose_name='يوجد تكليف إداري؟')
    admin_work_details = models.TextField(null=True, blank=True, verbose_name='تفاصيل العمل الإداري')

    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # 🆕 دالة حساب العمر تلقائياً
    @property
    def age(self):
        if self.dob:
            today = date.today()
            return today.year - self.dob.year - ((today.month, today.day) < (self.dob.month, self.dob.day))
        return None

    def __str__(self):
        return self.full_name

# ==========================================
# 5. جدول الإجازات
# ==========================================
class Leave(models.Model):
    LEAVE_TYPES = (
        ('سنوية', 'سنوية'),
        ('مرضية', 'مرضية'),
        ('اضطرارية', 'اضطرارية'),
        ('أخرى', 'أخرى'),
    )
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, verbose_name='الموظف')
    leave_type = models.CharField(max_length=50, choices=LEAVE_TYPES, verbose_name='نوع الإجازة')
    start_date = models.DateField(verbose_name='تاريخ البداية')
    end_date = models.DateField(verbose_name='تاريخ النهاية')
    notes = models.TextField(null=True, blank=True, verbose_name='ملاحظات')

    @property
    def duration_days(self):
        if self.start_date and self.end_date:
            return (self.end_date - self.start_date).days + 1
        return 0

    def __str__(self):
        return f"{self.employee.full_name} - {self.leave_type}"