from django.urls import path
from . import views

urlpatterns = [
    # ==========================================
    # لوحة القيادة وتسجيل الخروج
    # ==========================================
    path('', views.dashboard_view, name='dashboard'),
    path('logout/', views.custom_logout, name='logout'),

    # ==========================================
 
    # إدارة الموظفين
    # ==========================================
    path('employees/', views.employee_list, name='employee_list'),
    path('employees/add/', views.add_employee, name='add_employee'),
    path('employees/edit/<int:pk>/', views.edit_employee, name='edit_employee'),
    path('employees/delete/<int:pk>/', views.delete_employee, name='delete_employee'),
    path('employees/export/', views.export_employees_excel, name='export_employees_excel'), # الرابط الجديد
    # ==========================================
    # إدارة الإجازات
    # ==========================================
    path('leaves/', views.leave_list, name='leave_list'),
    path('leaves/add/', views.add_leave, name='add_leave'),
    path('leaves/edit/<int:pk>/', views.edit_leave, name='edit_leave'),
    path('leaves/delete/<int:pk>/', views.delete_leave, name='delete_leave'),

    # ==========================================
    # أرشيف الموظفين (سلة المحذوفات)
    # ==========================================
    path('archive/', views.archived_employee_list, name='archived_employee_list'),
    path('archive/restore/<int:pk>/', views.restore_employee, name='restore_employee'),
    path('archive/hard-delete/<int:pk>/', views.hard_delete_employee, name='hard_delete_employee'),

    # ==========================================
    # إدارة المستخدمين والصلاحيات
    # ==========================================
    path('users/', views.user_list, name='user_list'),
    path('users/add/', views.add_user, name='add_user'),
    path('users/edit/<int:pk>/', views.edit_user_permissions, name='edit_user'),
    # (تم إزالة مسار toggle_user_status القديم لأنه أصبح مدمجاً في صفحة التعديل)

    # ==========================================
    # إعدادات النظام (البيانات المرجعية)
    # ==========================================
    path('settings/', views.system_settings, name='system_settings'),
    path('settings/add/<str:item_type>/', views.add_setting_item, name='add_setting_item'),
    path('settings/delete/<str:item_type>/<int:pk>/', views.delete_setting_item, name='delete_setting_item'),

    # ==========================================
    # سجل المراقبة (Audit Log)
    # ==========================================
    path('audit-log/', views.activity_log_list, name='activity_log_list'),
]