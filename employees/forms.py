import re

from django import forms
from .models import Employee, Leave, Workplace, UserProfile
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import ValidationError

OTHER_WORKPLACE = '__other__'


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

        # 1. تحقق التواريخ
        start_date = cleaned_data.get('contract_start_date')
        end_date = cleaned_data.get('contract_end_date')
        if start_date and end_date:
            if end_date < start_date:
                raise ValidationError("خطأ: تاريخ نهاية العقد لا يمكن أن يكون قبل تاريخ البداية!")
                
        # 2. تحقق التصنيف المهني
        is_classified = cleaned_data.get('is_classified')
        classification_expiry_date = cleaned_data.get('classification_expiry_date')
        if is_classified == 'مصنف' and not classification_expiry_date:
            self.add_error('classification_expiry_date', 'يجب إدخال تاريخ انتهاء التصنيف بما أن الموظف (مصنف).')
        elif is_classified == 'غير مصنف':
            cleaned_data['classification_expiry_date'] = None
            
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