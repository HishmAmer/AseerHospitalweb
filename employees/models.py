from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
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

    def clean(self):
        super().clean()
        
        if hasattr(self, 'user'):
            # 1. لو الحساب أدمن (Superuser)
            if self.user.is_superuser and self.workplace:
                raise ValidationError({'workplace': 'حساب الإدارة (الأدمن) لا يجب أن يرتبط بمنشأة محددة.'})
            
            # 2. لو الحساب فرعي (ليس أدمن)
            if not self.user.is_superuser and not self.workplace:
                raise ValidationError({'workplace': 'إجباري: يجب اختيار المنشأة للحسابات الفرعية.'})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

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
    
    CATEGORY_CHOICES = (
        ('مقيم', 'طبيب مقيم'), ('نائب', 'طبيب نائب'),
        ('نائب أول', 'نائب أول'), ('استشاري', 'طبيب استشاري'),
    )
    
    NATIONALITY_CHOICES = (
        # ملاحظة: القيمة اليسرى مخزَّنة في قاعدة البيانات — لا تُعدَّل ولا تُحذف
        # لأي جنسية قائمة، وإلا فقدت سجلات الموظفين المرتبطة بها قيمتها.
        # الإضافة الجديدة آمنة تماماً.

        # --- دول الخليج ---
        ('سعودي', 'سعودي'), ('إماراتي', 'إماراتي'), ('كويتي', 'كويتي'),
        ('قطري', 'قطري'), ('عماني', 'عماني'), ('بحريني', 'بحريني'),

        # --- الدول العربية ---
        ('مصري', 'مصري'), ('يمني', 'يمني'), ('سوداني', 'سوداني'),
        ('أردني', 'أردني'), ('سوري', 'سوري'), ('فلسطيني', 'فلسطيني'),
        ('لبناني', 'لبناني'), ('عراقي', 'عراقي'), ('تونسي', 'تونسي'),
        ('مغربي', 'مغربي'), ('جزائري', 'جزائري'), ('ليبي', 'ليبي'),
        ('صومالي', 'صومالي'), ('موريتاني', 'موريتاني'), ('جيبوتي', 'جيبوتي'),
        ('قمري', 'قمري'),

        # --- آسيا (الجنسيات الأكثر توظيفاً) ---
        ('هندي', 'هندي'), ('فلبيني', 'فلبيني'), ('باكستاني', 'باكستاني'),
        ('بنغلاديشي', 'بنغلاديشي'), ('إندونيسي', 'إندونيسي'), ('سريلانكي', 'سريلانكي'),
        ('نيبالي', 'نيبالي'), ('ماليزي', 'ماليزي'), ('أفغاني', 'أفغاني'),
        ('ميانماري', 'ميانماري'),

        # --- آسيا (بقية الدول) ---
        ('صيني', 'صيني'), ('ياباني', 'ياباني'), ('كوري', 'كوري (كوريا الجنوبية)'),
        ('كوري شمالي', 'كوري شمالي'), ('تايلاندي', 'تايلاندي'), ('فيتنامي', 'فيتنامي'),
        ('سنغافوري', 'سنغافوري'), ('تركي', 'تركي'), ('إيراني', 'إيراني'),
        ('أوزبكي', 'أوزبكي'), ('طاجيكي', 'طاجيكي'), ('كازاخي', 'كازاخي'),
        ('قيرغيزي', 'قيرغيزي'), ('تركماني', 'تركماني'), ('أذربيجاني', 'أذربيجاني'),
        ('أرميني', 'أرميني'), ('جورجي', 'جورجي'), ('منغولي', 'منغولي'),
        ('كمبودي', 'كمبودي'), ('لاوسي', 'لاوسي'), ('بروناوي', 'بروناوي'),
        ('تيموري', 'تيموري (تيمور الشرقية)'), ('مالديفي', 'مالديفي'), ('بوتاني', 'بوتاني'),
        ('قبرصي', 'قبرصي'),

        # --- أفريقيا ---
        ('جنوب أفريقي', 'جنوب أفريقي'), ('نيجيري', 'نيجيري (نيجيريا)'),
        ('كينى', 'كيني'), ('إثيوبي', 'إثيوبي'), ('إريتري', 'إريتري'),
        ('تشادي', 'تشادي'), ('غاني', 'غاني'), ('أوغندي', 'أوغندي'),
        ('مالي', 'مالي'), ('سنغالي', 'سنغالي'), ('كوت ديفوار', 'كوت ديفوار'),
        ('كاميروني', 'كاميروني'), ('رواندي', 'رواندي'),
        ('جنوب سوداني', 'جنوب سوداني'), ('تنزاني', 'تنزاني'), ('زامبي', 'زامبي'),
        ('زيمبابوي', 'زيمبابوي'), ('موزمبيقي', 'موزمبيقي'), ('أنغولي', 'أنغولي'),
        ('ناميبي', 'ناميبي'), ('بوتسواني', 'بوتسواني'), ('ملاوي', 'ملاوي'),
        ('بوروندي', 'بوروندي'), ('كونغولي', 'كونغولي (الكونغو الديمقراطية)'),
        ('كونغولي برازافيل', 'كونغولي (برازافيل)'), ('غابوني', 'غابوني'),
        ('غيني', 'غيني (غينيا)'), ('بيساوي', 'بيساوي (غينيا بيساو)'),
        ('غيني استوائي', 'غيني استوائي'), ('بنيني', 'بنيني'), ('توغولي', 'توغولي'),
        ('بوركيني', 'بوركيني (بوركينا فاسو)'), ('نيجري', 'نيجري (النيجر)'),
        ('سيراليوني', 'سيراليوني'), ('ليبيري', 'ليبيري'), ('غامبي', 'غامبي'),
        ('رأس أخضر', 'رأس أخضر'), ('مدغشقري', 'مدغشقري'), ('موريشيوسي', 'موريشيوسي'),
        ('سيشلي', 'سيشلي'), ('أفريقي وسطي', 'أفريقي وسطي'), ('ليسوتي', 'ليسوتي'),
        ('إسواتيني', 'إسواتيني'), ('ساوتومي', 'ساوتومي'),

        # --- أوروبا ---
        ('بريطاني', 'بريطاني'), ('فرنسي', 'فرنسي'), ('ألماني', 'ألماني'),
        ('إيطالي', 'إيطالي'), ('إسباني', 'إسباني'), ('هولندي', 'هولندي'),
        ('سويدي', 'سويدي'), ('سويسري', 'سويسري'), ('نمساوي', 'نمساوي'),
        ('بلجيكي', 'بلجيكي'), ('برتغالي', 'برتغالي'), ('دانماركي', 'دانماركي'),
        ('نرويجي', 'نرويجي'), ('فنلندي', 'فنلندي'), ('بولندي', 'بولندي'),
        ('يوناني', 'يوناني'), ('روسي', 'روسي'), ('أوكراني', 'أوكراني'),
        ('بوسني', 'بوسني'), ('ألباني', 'ألباني'), ('روماني', 'روماني'),
        ('أيرلندي', 'أيرلندي'), ('آيسلندي', 'آيسلندي'), ('تشيكي', 'تشيكي'),
        ('سلوفاكي', 'سلوفاكي'), ('مجري', 'مجري'), ('بلغاري', 'بلغاري'),
        ('صربي', 'صربي'), ('كرواتي', 'كرواتي'), ('سلوفيني', 'سلوفيني'),
        ('مقدوني', 'مقدوني (مقدونيا الشمالية)'), ('جبل أسود', 'جبل أسود'),
        ('كوسوفي', 'كوسوفي'), ('ليتواني', 'ليتواني'), ('لاتفي', 'لاتفي'),
        ('إستوني', 'إستوني'), ('بيلاروسي', 'بيلاروسي'), ('مولدوفي', 'مولدوفي'),
        ('مالطي', 'مالطي'), ('لوكسمبورغي', 'لوكسمبورغي'), ('ليختنشتايني', 'ليختنشتايني'),
        ('موناكي', 'موناكي'), ('أندوري', 'أندوري'), ('سان ماريني', 'سان ماريني'),

        # --- الأمريكتان ---
        ('أمريكي', 'أمريكي'), ('كندي', 'كندي'), ('برازيلي', 'برازيلي'),
        ('أرجنتيني', 'أرجنتيني'), ('فنزويلي', 'فنزويلي'), ('مكسيكي', 'مكسيكي'),
        ('كولومبي', 'كولومبي'), ('كوبي', 'كوبي'), ('تشيلي', 'تشيلي'),
        ('بيروفي', 'بيروفي'), ('إكوادوري', 'إكوادوري'), ('بوليفي', 'بوليفي'),
        ('أوروغواياني', 'أوروغواياني'), ('باراغواياني', 'باراغواياني'),
        ('غوياني', 'غوياني'), ('سورينامي', 'سورينامي'), ('بنمي', 'بنمي'),
        ('كوستاريكي', 'كوستاريكي'), ('نيكاراغوي', 'نيكاراغوي'), ('هندوراسي', 'هندوراسي'),
        ('سلفادوري', 'سلفادوري'), ('غواتيمالي', 'غواتيمالي'), ('بليزي', 'بليزي'),
        ('دومينيكاني', 'دومينيكاني'), ('هايتي', 'هايتي'), ('جامايكي', 'جامايكي'),
        ('ترينيدادي', 'ترينيدادي'), ('بربادوسي', 'بربادوسي'), ('بهامي', 'بهامي'),

        # --- أوقيانوسيا ---
        ('أسترالي', 'أسترالي'), ('نيوزيلندي', 'نيوزيلندي'),
        ('بابوي', 'بابوي (بابوا غينيا الجديدة)'), ('فيجي', 'فيجي'), ('ساموي', 'ساموي'),
        ('تونغي', 'تونغي'), ('فانواتي', 'فانواتي'), ('سليماني', 'سليماني (جزر سليمان)'),
        ('كيريباتي', 'كيريباتي'), ('ميكرونيزي', 'ميكرونيزي'), ('بالاوي', 'بالاوي'),
        ('ناوروي', 'ناوروي'), ('توفالي', 'توفالي'), ('مارشالي', 'مارشالي'),

        # --- حالات خاصة ---
        ('بدون جنسية', 'بدون جنسية'),
        ('أخرى', 'أخرى'),
    )

    EMPLOYEE_TYPE_CHOICES = (
        ('تشغيل ذاتي', 'تشغيل ذاتي'),
        ('خدمة مدنية', 'خدمة مدنية'),
    )

    CLASSIFICATION_CHOICES = (
        ('مصنف', 'مصنف'), ('غير مصنف', 'غير مصنف'),
    )

    WORKPLACE_TYPE_CHOICES = (
        ('تجمع عسير الصحي', 'تجمع عسير الصحي'),
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

    # بلا choices على مستوى النموذج: الخيار «أخرى» في الواجهة يسمح بكتابة نوع
    # غير مدرج، فيُخزَّن النص المكتوب هنا مباشرة. القائمة أعلاه تبني قائمة
    # الاختيار في النموذج، والتحقق يتم هناك.
    workplace_type = models.CharField(max_length=50, null=True, blank=True, verbose_name='نوع المنشأة')
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

    employee_category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, null=True, blank=True, verbose_name='فئة الموظف (الكادر)')
    contract_job_title = models.CharField(max_length=150, null=True, blank=True, verbose_name='المسمى الوظيفي بالعقد')
    
    contract_start_date = models.DateField(null=True, blank=True, verbose_name='تاريخ بداية العقد')
    contract_end_date = models.DateField(null=True, blank=True, verbose_name='تاريخ نهاية العقد')

    is_admin_assigned = models.BooleanField(default=False, verbose_name='يوجد تكليف إداري؟')
    admin_work_details = models.TextField(null=True, blank=True, verbose_name='تفاصيل العمل الإداري')

    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

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