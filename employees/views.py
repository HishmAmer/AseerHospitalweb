from .models import (
    Employee, Workplace, Department, UserProfile, Leave, ActivityLog, 
    GeneralSpecialty, SubSpecialty
)
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import date, datetime, timedelta
import openpyxl
from django.http import HttpResponse
from django.db.models import Q 

from .models import (
    Employee, Workplace, UserProfile, Leave, ActivityLog, 
    GeneralSpecialty, SubSpecialty
)
from .forms import EmployeeForm, LeaveForm

def log_activity(user, action_type, description):
    if user.is_authenticated:
        ActivityLog.objects.create(user=user, action_type=action_type, description=description) 

@login_required(login_url='login')
def dashboard_view(request):
    user_profile = getattr(request.user, 'profile', None)
    today = date.today()
    
    if user_profile and user_profile.workplace:
        base_employees = Employee.objects.filter(is_deleted=False, current_workplace=user_profile.workplace)
        workplace_name = user_profile.workplace.name
        on_leave = Leave.objects.filter(employee__current_workplace=user_profile.workplace, employee__is_deleted=False, employee__status='نشط', start_date__lte=today, end_date__gte=today).count()
    else:
        base_employees = Employee.objects.filter(is_deleted=False)
        workplace_name = "الإدارة العامة"
        on_leave = Leave.objects.filter(employee__is_deleted=False, employee__status='نشط', start_date__lte=today, end_date__gte=today).count()

    active_count = base_employees.filter(status='نشط').count()
    resigned_count = base_employees.filter(status='مستقيل').count()
    terminated_count = base_employees.filter(status='طي القيد').count()
    delegated_count = base_employees.filter(status='إيفاد').count()

    # 🆕 تم التحديث ليعتمد على employee_category
    resident_count = base_employees.filter(status='نشط', employee_category='مقيم').count()
    registrar_count = base_employees.filter(status='نشط', employee_category='نائب').count()
    senior_registrar_count = base_employees.filter(status='نشط', employee_category='نائب أول').count()
    consultant_count = base_employees.filter(status='نشط', employee_category='استشاري').count()

    thirty_days_from_now = today + timedelta(days=30)
    ninety_days_from_now = today + timedelta(days=90) 
    
    expired_employees = base_employees.filter(status='نشط', contract_end_date__lt=today).order_by('contract_end_date')
    expiring_soon_employees = base_employees.filter(status='نشط', contract_end_date__gte=today, contract_end_date__lte=thirty_days_from_now).order_by('contract_end_date')
    
    expired_classifications = base_employees.filter(status='نشط', is_classified='مصنف', classification_expiry_date__lt=today).order_by('classification_expiry_date')
    expiring_soon_classifications = base_employees.filter(status='نشط', is_classified='مصنف', classification_expiry_date__gte=today, classification_expiry_date__lte=ninety_days_from_now).order_by('classification_expiry_date')

    context = {
        'workplace_name': workplace_name,
        'total_employees': active_count,
        'male_count': base_employees.filter(status='نشط', gender='M').count(),
        'female_count': base_employees.filter(status='نشط', gender='F').count(),
        'on_leave_count': on_leave,
        'active_count': active_count,
        'resigned_count': resigned_count,
        'terminated_count': terminated_count,
        'delegated_count': delegated_count,
        'total_all': base_employees.count(), 
        'expired_employees': expired_employees,
        'expiring_soon_employees': expiring_soon_employees,
        'expired_count': expired_employees.count(),
        'expiring_soon_count': expiring_soon_employees.count(),
        'resident_count': resident_count,
        'registrar_count': registrar_count,
        'senior_registrar_count': senior_registrar_count,
        'consultant_count': consultant_count,
        'expired_classifications': expired_classifications,
        'expiring_soon_classifications': expiring_soon_classifications,
        'expired_class_count': expired_classifications.count(),
        'expiring_soon_class_count': expiring_soon_classifications.count(),
        'departments': Department.objects.all(),
    }
    return render(request, 'employees/dashboard.html', context)

def custom_logout(request):
    logout(request)
    return redirect('login')

@login_required(login_url='login')
def employee_list(request):
    user_profile = getattr(request.user, 'profile', None)
    
    if user_profile and user_profile.workplace and not request.user.is_superuser:
        employees = Employee.objects.filter(is_deleted=False, current_workplace=user_profile.workplace)
        workplaces = None 
    else:
        employees = Employee.objects.filter(is_deleted=False)
        workplaces = Workplace.objects.all()

    search_query = request.GET.get('search', '').strip()
    status_filter = request.GET.get('status', '')
    workplace_filter = request.GET.get('workplace', '')

    if search_query:
        employees = employees.filter(
            Q(full_name__icontains=search_query) | 
            Q(national_id__icontains=search_query) | 
            Q(employee_number__icontains=search_query)
        )
        
    if status_filter:
        employees = employees.filter(status=status_filter)
        
    if workplace_filter and request.user.is_superuser:
        employees = employees.filter(current_workplace__id=workplace_filter)

    employees = employees.order_by('full_name')

    context = {
        'employees': employees,
        'search_query': search_query,
        'status_filter': status_filter,
        'workplace_filter': workplace_filter,
        'workplaces': workplaces,
    }
    return render(request, 'employees/employee_list.html', context)

@login_required(login_url='login')
def add_employee(request):
    if request.method == 'POST':
        form = EmployeeForm(request.POST, user=request.user)
        if form.is_valid():
            emp = form.save()
            log_activity(request.user, 'إضافة', f'تم إضافة الموظف: {emp.full_name}')
            messages.success(request, 'تم إضافة الموظف بنجاح!')
            return redirect('employee_list')
    else:
        form = EmployeeForm(user=request.user)
    return render(request, 'employees/add_employee.html', {'form': form})

@login_required(login_url='login')
def edit_employee(request, pk):
    emp = get_object_or_404(Employee, pk=pk)
    
    if not request.user.is_superuser:
        if hasattr(request.user, 'profile') and emp.current_workplace != request.user.profile.workplace:
            messages.error(request, 'عملية مرفوضة: غير مصرح لك بتعديل بيانات هذا الموظف لأنه يتبع لمنشأة أخرى!')
            return redirect('employee_list')

    if request.method == 'POST':
        form = EmployeeForm(request.POST, instance=emp, user=request.user)
        if form.is_valid():
            form.save()
            log_activity(request.user, 'تعديل', f'تم تعديل بيانات الموظف: {emp.full_name}')
            messages.success(request, 'تم تحديث بيانات الموظف بنجاح!')
            return redirect('employee_list')
    else:
        form = EmployeeForm(instance=emp, user=request.user)
    return render(request, 'employees/edit_employee.html', {'form': form, 'employee': emp})

@login_required(login_url='login')
def delete_employee(request, pk):
    employee = get_object_or_404(Employee, pk=pk)
    employee.is_deleted = True
    employee.save()
    log_activity(request.user, 'تعديل', f'تم نقل الموظف للأرشيف: {employee.full_name}')
    messages.success(request, f'تم حذف الموظف {employee.full_name} ونقله للأرشيف.')
    return redirect('employee_list')

@login_required(login_url='login')
def export_employees_excel(request):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "بيانات الموظفين"
    ws.sheet_view.rightToLeft = True 

    # 🆕 تم إضافة الأعمدة الجديدة والعمر
    headers = [
        'الرقم الوظيفي', 'اسم الموظف', 'رقم الهوية', 'تاريخ الميلاد', 'العمر', 'الجنسية', 
        'نوع المنشأة', 'التفرغ', 'المنشأة الحالية', 'القسم', 'فئة الموظف (نوع العقد)', 
        'فئة الكادر', 'المسمى الوظيفي', 'حالة الموظف', 
        'تاريخ بداية العقد', 'تاريخ نهاية العقد', 'حالة التصنيف', 'تاريخ انتهاء التصنيف'
    ]
    ws.append(headers)

    user_profile = getattr(request.user, 'profile', None)
    if user_profile and user_profile.workplace and not request.user.is_superuser:
        employees = Employee.objects.filter(is_deleted=False, current_workplace=user_profile.workplace)
    else:
        employees = Employee.objects.filter(is_deleted=False)

    search_query = request.GET.get('search', '').strip()
    status_filter = request.GET.get('status', '')
    workplace_filter = request.GET.get('workplace', '')

    if search_query:
        from django.db.models import Q
        employees = employees.filter(
            Q(full_name__icontains=search_query) | 
            Q(national_id__icontains=search_query) | 
            Q(employee_number__icontains=search_query)
        )
        
    if status_filter:
        employees = employees.filter(status=status_filter)
        
    if workplace_filter and request.user.is_superuser:
        employees = employees.filter(current_workplace__id=workplace_filter)

    employees = employees.order_by('full_name')

    for emp in employees:
        ws.append([
            emp.employee_number or '-',
            emp.full_name,
            emp.national_id or '-',
            emp.dob.strftime('%Y-%m-%d') if emp.dob else '-',
            emp.age if emp.age is not None else '-',
            emp.nationality or '-',
            emp.workplace_type or '-',
            emp.time_type or '-',
            emp.current_workplace.name if emp.current_workplace else '-',
            emp.current_department.name if emp.current_department else '-',
            emp.employee_type or '-',
            emp.employee_category or '-',
            emp.contract_job_title or '-',
            emp.status,
            emp.contract_start_date.strftime('%Y-%m-%d') if emp.contract_start_date else '-',
            emp.contract_end_date.strftime('%Y-%m-%d') if emp.contract_end_date else '-',
            emp.is_classified,
            emp.classification_expiry_date.strftime('%Y-%m-%d') if emp.classification_expiry_date else '-'
        ])

    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    filename = f'Employees_Data_{datetime.now().strftime("%Y_%m_%d")}.xlsx'
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    wb.save(response)
    
    log_activity(request.user, 'نظام', 'قام بتصدير بيانات الموظفين المفلترة إلى ملف Excel')
    return response

@login_required(login_url='login')
def leave_list(request):
    user_profile = getattr(request.user, 'profile', None)
    today = date.today()
    if user_profile and user_profile.workplace:
        base_query = Leave.objects.filter(employee__current_workplace=user_profile.workplace, employee__is_deleted=False)
    else:
        base_query = Leave.objects.filter(employee__is_deleted=False)

    active_leaves = base_query.filter(end_date__gte=today).order_by('start_date')
    history_leaves = base_query.filter(end_date__lt=today).order_by('-end_date')
    return render(request, 'employees/leave_list.html', {'active_leaves': active_leaves, 'history_leaves': history_leaves})

@login_required(login_url='login')
def add_leave(request):
    if request.method == 'POST':
        form = LeaveForm(request.POST)
        if form.is_valid():
            leave = form.save()
            log_activity(request.user, 'إضافة', f'تم تسجيل إجازة للموظف: {leave.employee.full_name}')
            messages.success(request, 'تم تسجيل الإجازة بنجاح!')
            return redirect('leave_list')
    else:
        form = LeaveForm()

    user_profile = getattr(request.user, 'profile', None)
    if user_profile and user_profile.workplace:
        form.fields['employee'].queryset = Employee.objects.filter(current_workplace=user_profile.workplace, is_deleted=False)
    else:
        form.fields['employee'].queryset = Employee.objects.filter(is_deleted=False)
    return render(request, 'employees/add_leave.html', {'form': form})

@login_required(login_url='login')
def edit_leave(request, pk):
    leave = get_object_or_404(Leave, pk=pk)
    if request.method == 'POST':
        form = LeaveForm(request.POST, instance=leave)
        if form.is_valid():
            form.save()
            log_activity(request.user, 'تعديل', f'تم تعديل إجازة الموظف: {leave.employee.full_name}')
            messages.success(request, 'تم تعديل بيانات الإجازة بنجاح!')
            return redirect('leave_list')
    else:
        form = LeaveForm(instance=leave)

    user_profile = getattr(request.user, 'profile', None)
    if user_profile and user_profile.workplace:
        form.fields['employee'].queryset = Employee.objects.filter(current_workplace=user_profile.workplace, is_deleted=False)
    else:
        form.fields['employee'].queryset = Employee.objects.filter(is_deleted=False)
    return render(request, 'employees/edit_leave.html', {'form': form, 'leave': leave})

@login_required(login_url='login')
def delete_leave(request, pk):
    leave = get_object_or_404(Leave, pk=pk)
    emp_name = leave.employee.full_name
    leave.delete()
    log_activity(request.user, 'حذف', f'تم إلغاء إجازة الموظف: {emp_name}')
    messages.success(request, 'تم حذف الإجازة بنجاح.')
    return redirect('leave_list')

@login_required(login_url='login')
def archived_employee_list(request):
    user_profile = getattr(request.user, 'profile', None)
    if user_profile and user_profile.workplace:
        archived_emps = Employee.objects.filter(is_deleted=True, current_workplace=user_profile.workplace)
    else:
        archived_emps = Employee.objects.filter(is_deleted=True)
    return render(request, 'employees/archive_list.html', {'employees': archived_emps})

@login_required(login_url='login')
def restore_employee(request, pk):
    emp = get_object_or_404(Employee, pk=pk)
    emp.is_deleted = False
    emp.save()
    log_activity(request.user, 'استعادة', f'تم استعادة الموظف للعمل: {emp.full_name}')
    messages.success(request, f'تم استعادة الموظف {emp.full_name} وإعادته للسجل بنجاح!')
    return redirect('archived_employee_list')

@login_required(login_url='login')
@user_passes_test(lambda u: u.is_superuser)
def hard_delete_employee(request, pk):
    emp = get_object_or_404(Employee, pk=pk)
    emp_name = emp.full_name
    emp.delete()
    log_activity(request.user, 'حذف', f'تم مسح الموظف نهائياً من قاعدة البيانات: {emp_name}')
    messages.success(request, 'تم حذف الموظف من قاعدة البيانات نهائياً.')
    return redirect('archived_employee_list')

@login_required(login_url='login')
@user_passes_test(lambda u: u.is_superuser)
def user_list(request):
    users = User.objects.all().select_related('profile', 'profile__workplace')
    return render(request, 'employees/user_list.html', {'users': users})

@login_required(login_url='login')
@user_passes_test(lambda u: u.is_superuser)
def add_user(request):
    workplaces = Workplace.objects.all()
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        first_name = request.POST.get('first_name')
        role = request.POST.get('role')
        status = request.POST.get('status')
        workplace_id = request.POST.get('workplace')

        if User.objects.filter(username=username).exists():
            messages.error(request, 'اسم المستخدم هذا موجود مسبقاً!')
            return redirect('add_user')

        new_user = User.objects.create_user(username=username, password=password, first_name=first_name)
        if role == 'admin':
            new_user.is_superuser = True
            new_user.is_staff = True
        if status == 'inactive':
            new_user.is_active = False
        new_user.save()
        
        workplace = Workplace.objects.get(id=workplace_id) if workplace_id else None
        UserProfile.objects.create(user=new_user, workplace=workplace)

        log_activity(request.user, 'إضافة', f'تم إنشاء مستخدم جديد: {username}')
        messages.success(request, f'تم إنشاء المستخدم ({username}) وربطه بنجاح!')
        return redirect('user_list')
    return render(request, 'employees/add_user.html', {'workplaces': workplaces})

@login_required(login_url='login')
@user_passes_test(lambda u: u.is_superuser)
def edit_user_permissions(request, pk):
    target_user = get_object_or_404(User, pk=pk)
    workplaces = Workplace.objects.all()
    
    if request.method == 'POST':
        new_username = request.POST.get('username')
        if new_username and new_username != target_user.username:
            if User.objects.filter(username=new_username).exists():
                messages.error(request, 'اسم المستخدم هذا مسجل بالفعل لمستخدم آخر!')
                return redirect('edit_user', pk=target_user.pk)
            target_user.username = new_username
        
        new_password = request.POST.get('password')
        if new_password:
            target_user.set_password(new_password)
            
        role = request.POST.get('role')
        status = request.POST.get('status')
        workplace_id = request.POST.get('workplace')
        
        if target_user == request.user and status == 'inactive':
            messages.error(request, 'عملية مرفوضة: لا يمكنك تعطيل حسابك الشخصي أثناء استخدامه!')
            return redirect('user_list')
        
        if role == 'admin':
            target_user.is_superuser = True
            target_user.is_staff = True
        else:
            target_user.is_superuser = False
            target_user.is_staff = False
            
        if status == 'active':
            target_user.is_active = True
        else:
            target_user.is_active = False
            
        target_user.save()
        
        workplace = Workplace.objects.get(id=workplace_id) if workplace_id else None
        if hasattr(target_user, 'profile'):
            target_user.profile.workplace = workplace
            target_user.profile.save()
        else:
            UserProfile.objects.create(user=target_user, workplace=workplace)

        log_activity(request.user, 'تعديل', f'تم تعديل بيانات وصلاحيات المستخدم: {target_user.username}')
        messages.success(request, f'تم تحديث بيانات المستخدم ({target_user.username}) بنجاح!')
        return redirect('user_list')
        
    return render(request, 'employees/edit_user.html', {'target_user': target_user, 'workplaces': workplaces})

@login_required(login_url='login')
@user_passes_test(lambda u: u.is_superuser)
def system_settings(request):
    context = {
        'workplaces': Workplace.objects.all(),
        'departments': Department.objects.all(), # 👈 السطر ده كان ناقص عشان الأقسام تظهر
        'general_specialties': GeneralSpecialty.objects.all(),
        'sub_specialties': SubSpecialty.objects.all(),
    }
    return render(request, 'employees/settings.html', context)

@login_required(login_url='login')
@user_passes_test(lambda u: u.is_superuser)
def add_setting_item(request, item_type):
    if request.method == 'POST':
        name = request.POST.get('name')
        if name:
            if item_type == 'workplace': Workplace.objects.create(name=name)
            elif item_type == 'general_specialty': GeneralSpecialty.objects.create(name=name)
            elif item_type == 'sub_specialty': SubSpecialty.objects.create(name=name)
            elif item_type == 'department': Department.objects.create(name=name)
            
            log_activity(request.user, 'نظام', f'تم إضافة {name} إلى إعدادات النظام')
            messages.success(request, f'تمت الإضافة بنجاح!')
    return redirect('system_settings')

@login_required(login_url='login')
@user_passes_test(lambda u: u.is_superuser)
def delete_setting_item(request, item_type, pk):
    try:
        name = ""
        if item_type == 'workplace': 
            obj = Workplace.objects.get(pk=pk)
        elif item_type == 'general_specialty': 
            obj = GeneralSpecialty.objects.get(pk=pk)
        elif item_type == 'sub_specialty':     
            obj = SubSpecialty.objects.get(pk=pk)
        elif item_type == 'department': 
            obj = Department.objects.get(pk=pk)    
            
        name = obj.name
        obj.delete()
            
        log_activity(request.user, 'نظام', f'تم حذف {name} من إعدادات النظام')
        messages.success(request, 'تم الحذف بنجاح.')
    except Exception:
        messages.error(request, 'لا يمكن الحذف! هذا العنصر مرتبط ببيانات موظفين حاليين.')
    return redirect('system_settings')

@login_required(login_url='login')
@user_passes_test(lambda u: u.is_superuser)
def activity_log_list(request):
    thirty_days_ago = timezone.now() - timedelta(days=30)
    logs = ActivityLog.objects.filter(timestamp__gte=thirty_days_ago).order_by('-timestamp')
    return render(request, 'employees/activity_log.html', {'logs': logs})