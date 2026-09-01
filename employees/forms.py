import re
from datetime import date

from django import forms
from .models import Employee, Leave, Workplace, UserProfile
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import ValidationError

OTHER_WORKPLACE = '__other__'
OTHER_WORKPLACE_TYPE = '__other_type__'

# العمر المقبول: أكبر من 20 عاماً، أي 21 سنة مكتملة فأكثر.
# لتغيير الحدّ لاحقاً يكفي تعديل هذا الرقم وحده.
MIN_AGE_YEARS = 21


def years_since(day):
    """العمر بالسنوات المكتملة — بالحساب نفسه في Employee.age."""
    today = date.today()
    return today.year - day.year - ((today.month, today.day) < (day.month, day.day))


def latest_acceptable_dob():
    """آخر تاريخ ميلاد يبلغ صاحبه الحدّ الأدنى للعمر اليوم.

    date.replace(year=...) يرمي ValueError يوم 29 فبراير من سنة كبيسة لأن
    السنة المقابلة قبل 21 عاماً ليست كبيسة، فتسقط صفحة إضافة موظف في ذلك
    اليوم وحده. 28 فبراير هو التاريخ الصحيح حينها.
    """
    today = date.today()
    try:
        return today.replace(year=today.year - MIN_AGE_YEARS)
    except ValueError:
        return today.replace(year=today.year - MIN_AGE_YEARS, month=2, day=28)


# القيمة كما تُخزَّن في قاعدة البيانات ضمن Employee.EMPLOYEE_TYPE_CHOICES.
# موظفو الخدمة المدنية على بند التوظيف الحكومي فلا عقد لهم أصلاً.
CIVIL_SERVICE = 'خدمة مدنية'


def normalize_workplace_name(name):
    """يوحّد المسافات حتى لا تتكرر المنشأة بفروق شكلية فقط."""
    return re.sub(r'\s+', ' ', (name or '')).strip()


class WorkplaceChoiceField(forms.ModelChoiceField):
    """حقل منشأة يقبل الخيار «أخرى» ويترك حسمه إلى clean() في النموذج.

    ModelChoiceField يرفض أي قيمة ليست مفتاحاً في الجدول، فلولا هذا
    التجاوز لرُفض الخيار قبل أن يصل إلى منطق النموذج.
    """

    def to_python(self, value):
        if value == OTHER_WORKPLACE:
            return None
        return super().to_python(value)


class EmployeeForm(forms.ModelForm):
    other_workplace_type = forms.CharField(
        required=False,
        max_length=50,
        label='نوع المنشأة (اكتبه)',
        widget=forms.TextInput(attrs={'placeholder': 'اكتب نوع المنشأة…'}),
    )
    new_workplace_name = forms.CharField(
        required=False,
        max_length=150,
        label='اسم المنشأة الجديدة',
        widget=forms.TextInput(attrs={'placeholder': 'اكتب اسم المنشأة كاملاً…'}),
    )

    class Meta:
        model = Employee
        exclude = ['is_deleted', 'created_at', 'updated_at']
        
        widgets = {
            'dob': forms.DateInput(attrs={'type': 'date'}),
            'contract_start_date': forms.DateInput(attrs={'type': 'date'}),
            'contract_end_date': forms.DateInput(attrs={'type': 'date'}),
            'classification_expiry_date': forms.DateInput(attrs={'type': 'date'}), 
            'admin_work_details': forms.Textarea(attrs={'rows': 2}),
            
            'workplace_type': forms.Select(attrs={'class': 'form-select'}),
            'time_type': forms.Select(attrs={'class': 'form-select'}),
            'has_sub_specialty': forms.Select(attrs={'class': 'form-select'}),
            
            'employee_type': forms.Select(attrs={'class': 'form-select'}),
            'employee_category': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'gender': forms.Select(attrs={'class': 'form-select'}),
            'is_classified': forms.Select(attrs={'class': 'form-select'}),
            'nationality': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super(EmployeeForm, self).__init__(*args, **kwargs)
        
        for field_name, field in self.fields.items():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs['class'] = 'form-check-input'
            elif isinstance(field.widget, forms.Select):
                field.widget.attrs['class'] = 'form-select'
            else:
                field.widget.attrs['class'] = 'form-control'
        
        # أقصى تاريخ ميلاد مقبول، ليقصر منتقي التاريخ نفسه على المدى الصحيح.
        # إرشاد للمستخدم لا تحقّق: النموذج يحمل novalidate، والفحص في clean_dob.
        self.fields['dob'].widget.attrs['max'] = latest_acceptable_dob().isoformat()

        # نوع المنشأة: قائمة ثابتة يُضاف إليها «أخرى» لكتابة نوع غير مدرج.
        known_types = [(value, label) for value, label in Employee.WORKPLACE_TYPE_CHOICES]
        self.fields['workplace_type'] = forms.ChoiceField(
            required=False,
            label=Employee._meta.get_field('workplace_type').verbose_name,
            choices=[('', '--------- ')] + known_types + [(OTHER_WORKPLACE_TYPE, 'أخرى')],
            widget=forms.Select(attrs={'class': 'form-select'}),
        )

        # عند تعديل موظف نوعه مكتوب يدوياً: تُختار «أخرى» ويُملأ الحقل النصي،
        # وإلا ظهرت القائمة فارغة وضاعت القيمة المحفوظة عند أول حفظ.
        saved_type = self.instance.workplace_type if self.instance else None
        if saved_type and saved_type not in dict(known_types):
            self.initial['workplace_type'] = OTHER_WORKPLACE_TYPE
            self.initial['other_workplace_type'] = saved_type

        # استبدال حقل المنشأة بنسخة تقبل الخيار «أخرى»
        workplace_field = self.fields['current_workplace']
        self.fields['current_workplace'] = WorkplaceChoiceField(
            queryset=workplace_field.queryset,
            required=False,
            label=workplace_field.label,
            empty_label=workplace_field.empty_label,
            widget=forms.Select(attrs={'class': 'form-select'}),
        )

        if self.user and not self.user.is_superuser:
            if hasattr(self.user, 'profile') and self.user.profile.workplace:
                self.fields['current_workplace'].queryset = Workplace.objects.filter(id=self.user.profile.workplace.id)
                self.fields['current_workplace'].initial = self.user.profile.workplace
        elif self.user and self.user.is_superuser:
            # «أخرى» لمدير النظام وحده: مستخدم الفرع محصور بمنشأته، ولو أنشأ
            # موظفاً في منشأة أخرى لاختفى عنه فوراً بحكم نطاق الصلاحيات.
            field = self.fields['current_workplace']
            field.widget.choices = list(field.choices) + [
                (OTHER_WORKPLACE, 'أخرى — منشأة غير مدرجة'),
            ]

    def clean_dob(self):
        """تاريخ الميلاد اختياري، لكنه إن وُجد فالعمر أكبر من 20 عاماً.

        يُحسب بالطريقة نفسها في Employee.age حتى لا يقبل النموذج تاريخاً
        يعرضه سجل الموظف بعد الحفظ بعمر مرفوض. التاريخ المستقبلي يعطي
        عمراً سالباً فيسقط في الشرط نفسه.
        """
        dob = self.cleaned_data.get('dob')
        if not dob:
            return dob

        age = years_since(dob)
        if age < MIN_AGE_YEARS:
            raise ValidationError(
                f'يجب أن يكون عمر الموظف أكبر من {MIN_AGE_YEARS - 1} عاماً — '
                f'العمر المحسوب من هذا التاريخ {age} عاماً.'
            )
        return dob

    def clean(self):
        cleaned_data = super().clean()

        # 0. المنشأة: الخيار «أخرى» يعني إنشاء منشأة باسم مكتوب.
        # الإنشاء مؤجَّل إلى save() حتى لا يبقى سجل معلّق إذا فشل التحقق لاحقاً.
        if self.data.get('current_workplace') == OTHER_WORKPLACE:
            if not (self.user and self.user.is_superuser):
                self.add_error('current_workplace', 'غير مصرح لك بإضافة منشأة جديدة.')
            else:
                name = normalize_workplace_name(cleaned_data.get('new_workplace_name'))
                if not name:
                    self.add_error(
                        'new_workplace_name',
                        'اخترت «أخرى»، يرجى كتابة اسم المنشأة.',
                    )
                else:
                    cleaned_data['new_workplace_name'] = name
        else:
            cleaned_data['new_workplace_name'] = ''

        # 0-ب. نوع المنشأة: «أخرى» تعني تخزين النص المكتوب في الحقل نفسه.
        if cleaned_data.get('workplace_type') == OTHER_WORKPLACE_TYPE:
            typed = normalize_workplace_name(cleaned_data.get('other_workplace_type'))
            if not typed:
                self.add_error(
                    'other_workplace_type',
                    'اخترت «أخرى»، يرجى كتابة نوع المنشأة.',
                )
                cleaned_data['workplace_type'] = None
            else:
                cleaned_data['workplace_type'] = typed
                cleaned_data['other_workplace_type'] = typed
        else:
            cleaned_data['other_workplace_type'] = ''

        # 1. العقد مرتبط بفئة الموظف:
        #    - خدمة مدنية: لا عقد، فيُمحى أي تاريخ (يهمّ عند تعديل موظف
        #      غُيِّرت فئته، وإلا بقيت تواريخ عقد قديمة معلّقة في سجله).
        #    - غير ذلك: تاريخ نهاية العقد إلزامي.
        #    الفئة الفارغة لا تُلزم بشيء لأن الحقل نفسه اختياري.
        employee_type = cleaned_data.get('employee_type')
        start_date = cleaned_data.get('contract_start_date')
        end_date = cleaned_data.get('contract_end_date')

        if employee_type == CIVIL_SERVICE:
            cleaned_data['contract_start_date'] = None
            cleaned_data['contract_end_date'] = None
            start_date = end_date = None
        elif employee_type and not end_date:
            self.add_error(
                'contract_end_date',
                'تاريخ نهاية العقد إلزامي لغير موظفي الخدمة المدنية.',
            )

        # add_error بدل raise: الرفع يقطع clean() فلا تُفحص بقية الحقول،
        # فيرى المستخدم خطأً واحداً في كل محاولة حفظ.
        if start_date and end_date and end_date < start_date:
            self.add_error(
                'contract_end_date',
                'تاريخ نهاية العقد لا يمكن أن يكون قبل تاريخ البداية.',
            )

        # 2. التصنيف المهني: رقم التصنيف وتاريخ انتهائه يلزمان معاً للمصنَّف،
        #    ويُمحيان لغير المصنَّف حتى لا يبقى رقم تصنيف قديم في سجل من
        #    أُلغي تصنيفه.
                # 2. التصنيف المهني: رقم التصنيف وتاريخ انتهائه يلزمان معاً للمصنَّف،
        #    ويُمحيان لغير المصنَّف حتى لا يبقى رقم تصنيف قديم في سجل من
        #    أُلغي تصنيفه.
        is_classified = cleaned_data.get('is_classified')
        classification_expiry_date = cleaned_data.get('classification_expiry_date')
        classification_number = (cleaned_data.get('classification_number') or '').strip()

        if is_classified == 'مصنف':
            if not classification_number:
                self.add_error(
                    'classification_number',
                    'يجب إدخال رقم التصنيف بما أن الموظف (مصنف).',
                )
            else:
                cleaned_data['classification_number'] = classification_number
            if not classification_expiry_date:
                self.add_error(
                    'classification_expiry_date',
                    'يجب إدخال تاريخ انتهاء التصنيف بما أن الموظف (مصنف).',
                )
        elif is_classified == 'غير مصنف':
            cleaned_data['classification_expiry_date'] = None
            cleaned_data['classification_number'] = None
            
        # 3. تحقق نوع المنشأة
        workplace_type = cleaned_data.get('workplace_type')
        time_type = cleaned_data.get('time_type')
        if workplace_type in ['مدن طبية', 'جامعة الملك خالد'] and not time_type:
            self.add_error('time_type', 'يجب تحديد نوع التفرغ (كلي/جزئي) بناءً على نوع المنشأة المختار.')
        elif workplace_type == 'مستشفى عام':
            cleaned_data['time_type'] = None

        # 4. تحقق التخصص الدقيق
        has_sub = cleaned_data.get('has_sub_specialty')
        sub_specialty = cleaned_data.get('sub_specialty')
        if has_sub == 'نعم' and not sub_specialty:
            self.add_error('sub_specialty', 'لقد اخترت وجود تخصص دقيق، يرجى تحديده من القائمة.')
        elif has_sub == 'لا':
            cleaned_data['sub_specialty'] = None

        return cleaned_data

    def save(self, commit=True):
        """يُنشئ المنشأة المكتوبة عند الحفظ، أو يعيد استخدام منشأة قائمة بنفس الاسم."""
        name = self.cleaned_data.get('new_workplace_name')
        if name:
            workplace = Workplace.objects.filter(name__iexact=name).first()
            if workplace is None:
                workplace = Workplace.objects.create(name=name)
            self.instance.current_workplace = workplace
        return super().save(commit=commit)


class LeaveForm(forms.ModelForm):
    class Meta:
        model = Leave
        fields = ['employee', 'leave_type', 'start_date', 'end_date', 'notes']
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
            'notes': forms.Textarea(attrs={'rows': 3, 'placeholder': 'تفاصيل أو مبررات الإجازة (اختياري)...'}),
        }
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            if isinstance(field.widget, forms.Select):
                field.widget.attrs['class'] = 'form-select'
            elif isinstance(field.widget, (forms.DateInput, forms.Textarea, forms.TextInput)):
                field.widget.attrs['class'] = 'form-control'

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')

        if start_date and end_date:
            if end_date < start_date:
                raise ValidationError("خطأ: تاريخ نهاية الإجازة لا يمكن أن يكون قبل تاريخ بدايتها!")
        return cleaned_data

class AccountCreationForm(UserCreationForm):
    is_superuser = forms.BooleanField(
        required=False, 
        label='منح صلاحيات الإدارة (أدمن)',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    workplace = forms.ModelChoiceField(
        queryset=Workplace.objects.all(),
        required=False,
        label='المنشأة التابع لها',
        empty_label='--- اختر المنشأة ---',
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    class Meta:
        model = User
        fields = ('username', 'is_superuser')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            if isinstance(field.widget, forms.TextInput) or isinstance(field.widget, forms.PasswordInput):
                field.widget.attrs['class'] = 'form-control'

    def clean(self):
        cleaned_data = super().clean()
        is_superuser = cleaned_data.get('is_superuser')
        workplace = cleaned_data.get('workplace')

        if is_superuser and workplace:
            self.add_error('workplace', 'حساب الإدارة (الأدمن) لا يجب أن يرتبط بمنشأة محددة.')
            
        if not is_superuser and not workplace:
            self.add_error('workplace', 'إجباري: يجب اختيار المنشأة للحسابات الفرعية.')

        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.is_superuser = self.cleaned_data.get('is_superuser')
        
        if user.is_superuser:
            user.is_staff = True 
        
        if commit:
            user.save()
            workplace = self.cleaned_data.get('workplace')
            UserProfile.objects.create(user=user, workplace=workplace)
            
        return user