import sys
from unittest import mock

from django.contrib.auth.models import User
from django.core.cache import cache
from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from .forms import EmployeeForm
from .models import Employee, Leave, UserProfile, Workplace


class SecurityTestCase(TestCase):
    def setUp(self):
        cache.clear()
        self.hospital_a = Workplace.objects.create(name='مستشفى أ')
        self.hospital_b = Workplace.objects.create(name='مستشفى ب')

        self.admin = User.objects.create_user(
            username='admin', password='Str0ngAdminPass!', is_superuser=True, is_staff=True
        )
        UserProfile.objects.create(user=self.admin, workplace=None)

        self.branch_user = User.objects.create_user(username='branch_a', password='Str0ngPass!2024')
        UserProfile.objects.create(user=self.branch_user, workplace=self.hospital_a)

        self.own_employee = Employee.objects.create(
            full_name='موظف أ', gender='M', current_workplace=self.hospital_a
        )
        self.other_employee = Employee.objects.create(
            full_name='موظف ب', gender='F', current_workplace=self.hospital_b
        )


class AuthenticationRequiredTests(SecurityTestCase):
    def test_system_settings_rejects_anonymous(self):
        response = self.client.get(reverse('system_settings'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response['Location'])

    def test_system_settings_rejects_non_superuser(self):
        self.client.force_login(self.branch_user)
        response = self.client.get(reverse('system_settings'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response['Location'])

    def test_system_settings_allows_superuser(self):
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(reverse('system_settings')).status_code, 200)


class DestructiveActionsRequirePostTests(SecurityTestCase):
    def test_get_requests_do_not_mutate_data(self):
        self.client.force_login(self.admin)
        leave = Leave.objects.create(
            employee=self.own_employee,
            leave_type='سنوية',
            start_date='2026-01-01',
            end_date='2026-01-05',
        )
        archived = Employee.objects.create(
            full_name='مؤرشف', gender='M', current_workplace=self.hospital_a, is_deleted=True
        )

        get_only_urls = [
            reverse('delete_employee', args=[self.own_employee.pk]),
            reverse('delete_leave', args=[leave.pk]),
            reverse('restore_employee', args=[archived.pk]),
            reverse('hard_delete_employee', args=[archived.pk]),
            reverse('delete_setting_item', args=['workplace', self.hospital_b.pk]),
            reverse('add_setting_item', args=['workplace']),
            reverse('logout'),
        ]
        for url in get_only_urls:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 405)

        self.own_employee.refresh_from_db()
        self.assertFalse(self.own_employee.is_deleted)
        self.assertTrue(Leave.objects.filter(pk=leave.pk).exists())
        self.assertTrue(Workplace.objects.filter(pk=self.hospital_b.pk).exists())
        archived.refresh_from_db()
        self.assertTrue(archived.is_deleted)


class WorkplaceScopingTests(SecurityTestCase):
    def test_cannot_view_other_workplace_employee(self):
        self.client.force_login(self.branch_user)
        response = self.client.get(reverse('edit_employee', args=[self.other_employee.pk]))
        self.assertEqual(response.status_code, 404)

    def test_cannot_delete_other_workplace_employee(self):
        self.client.force_login(self.branch_user)
        response = self.client.post(reverse('delete_employee', args=[self.other_employee.pk]))
        self.assertEqual(response.status_code, 404)
        self.other_employee.refresh_from_db()
        self.assertFalse(self.other_employee.is_deleted)

    def test_cannot_delete_other_workplace_leave(self):
        leave = Leave.objects.create(
            employee=self.other_employee,
            leave_type='سنوية',
            start_date='2026-01-01',
            end_date='2026-01-05',
        )
        self.client.force_login(self.branch_user)
        self.assertEqual(
            self.client.post(reverse('delete_leave', args=[leave.pk])).status_code, 404
        )
        self.assertTrue(Leave.objects.filter(pk=leave.pk).exists())

    def test_cannot_file_leave_for_other_workplace_employee(self):
        self.client.force_login(self.branch_user)
        self.client.post(reverse('add_leave'), {
            'employee': self.other_employee.pk,
            'leave_type': 'سنوية',
            'start_date': '2026-01-01',
            'end_date': '2026-01-05',
            'notes': '',
        })
        self.assertFalse(Leave.objects.filter(employee=self.other_employee).exists())

    def test_export_excludes_other_workplace_employees(self):
        self.client.force_login(self.branch_user)
        response = self.client.get(reverse('export_employees_excel'))
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('موظف ب'.encode(), response.content)

    def test_user_without_profile_sees_nothing(self):
        orphan = User.objects.create_user(username='orphan', password='Str0ngPass!2024')
        self.client.force_login(orphan)
        response = self.client.get(reverse('employee_list'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(list(response.context['employees']), [])

    def test_hard_delete_restricted_to_superuser(self):
        archived = Employee.objects.create(
            full_name='مؤرشف أ', gender='M', current_workplace=self.hospital_a, is_deleted=True
        )
        self.client.force_login(self.branch_user)
        self.client.post(reverse('hard_delete_employee', args=[archived.pk]))
        self.assertTrue(Employee.objects.filter(pk=archived.pk).exists())


class AccountManagementTests(SecurityTestCase):
    def test_weak_password_is_rejected(self):
        self.client.force_login(self.admin)
        self.client.post(reverse('add_user'), {
            'username': 'weakling',
            'password': '123456',
            'first_name': 'Test',
            'role': 'branch',
            'status': 'active',
            'workplace': self.hospital_a.pk,
        })
        self.assertFalse(User.objects.filter(username='weakling').exists())

    def test_strong_password_is_accepted(self):
        self.client.force_login(self.admin)
        self.client.post(reverse('add_user'), {
            'username': 'newuser',
            'password': 'Str0ngPass!2024',
            'first_name': 'Test',
            'role': 'branch',
            'status': 'active',
            'workplace': self.hospital_a.pk,
        })
        self.assertTrue(User.objects.filter(username='newuser').exists())

    def test_unknown_workplace_does_not_error(self):
        self.client.force_login(self.admin)
        response = self.client.post(reverse('add_user'), {
            'username': 'ghost',
            'password': 'Str0ngPass!2024',
            'role': 'branch',
            'status': 'active',
            'workplace': '999999',
        })
        self.assertEqual(response.status_code, 302)
        self.assertFalse(User.objects.filter(username='ghost').exists())

    def test_admin_cannot_revoke_own_admin_rights(self):
        self.client.force_login(self.admin)
        self.client.post(reverse('edit_user', args=[self.admin.pk]), {
            'username': 'admin',
            'role': 'branch',
            'status': 'active',
            'workplace': self.hospital_a.pk,
        })
        self.admin.refresh_from_db()
        self.assertTrue(self.admin.is_superuser)

    def test_non_superuser_cannot_manage_users(self):
        self.client.force_login(self.branch_user)
        response = self.client.get(reverse('user_list'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response['Location'])


class LoginThrottleTests(SecurityTestCase):
    def test_repeated_failures_lock_the_account_out(self):
        url = reverse('login')
        for _ in range(10):
            self.client.post(url, {'username': 'branch_a', 'password': 'wrong'})

        response = self.client.post(url, {'username': 'branch_a', 'password': 'Str0ngPass!2024'})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.wsgi_request.user.is_authenticated)

    def test_successful_login_clears_the_counter(self):
        url = reverse('login')
        self.client.post(url, {'username': 'branch_a', 'password': 'wrong'})
        response = self.client.post(url, {'username': 'branch_a', 'password': 'Str0ngPass!2024'})
        self.assertEqual(response.status_code, 302)


class ExcelExportTests(SecurityTestCase):
    def test_formula_is_neutralised(self):
        from .views import excel_safe

        self.assertEqual(excel_safe('=cmd|calc'), "'=cmd|calc")
        self.assertEqual(excel_safe('+1+1'), "'+1+1")
        self.assertEqual(excel_safe('محمد'), 'محمد')
        self.assertEqual(excel_safe(42), 42)


class HostConfigurationTests(SimpleTestCase):
    """Guards the deployment contract: a build must not need a hostname it
    cannot know, and a serving process must never run without one."""

    def test_pasted_urls_reduce_to_a_bare_hostname(self):
        from core.settings import as_hostname

        for value in ('https://app.onrender.com/', 'app.onrender.com:443', 'App.onrender.com.'):
            self.assertEqual(as_hostname(value), 'app.onrender.com')

    def test_ipv6_literal_keeps_its_brackets(self):
        from core.settings import as_hostname

        self.assertEqual(as_hostname('[::1]:8000'), '[::1]')

    def test_csrf_origin_gains_a_scheme_and_is_lowercased(self):
        from core.settings import as_origin

        self.assertEqual(as_origin('App.onrender.com', 'https'), 'https://app.onrender.com')
        self.assertEqual(as_origin('http://10.0.0.15/', 'https'), 'http://10.0.0.15')

    def test_build_commands_do_not_require_allowed_hosts(self):
        from core.settings import will_serve_requests

        for argv in (['manage.py', 'collectstatic'], ['manage.py', 'migrate']):
            with mock.patch.object(sys, 'argv', argv):
                self.assertFalse(will_serve_requests())

    def test_serving_processes_require_allowed_hosts(self):
        from core.settings import will_serve_requests

        with mock.patch.object(sys, 'argv', ['manage.py', 'runserver']):
            self.assertTrue(will_serve_requests())
        # gunicorn imports settings without manage.py on argv.
        with mock.patch.object(sys, 'argv', ['/usr/bin/gunicorn', 'core.wsgi']):
            self.assertTrue(will_serve_requests())


def build_workbook(rows, headers=None):
    """ملف Excel في الذاكرة، بترويسات التصدير الافتراضية."""
    import io
    import openpyxl

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(headers or ['اسم الموظف', 'رقم الهوية', 'الرقم الوظيفي', 'حالة الموظف'])
    for row in rows:
        ws.append(row)
    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    buffer.name = 'test.xlsx'
    return buffer


class ExcelReconcileTests(SecurityTestCase):
    def setUp(self):
        super().setUp()
        self.own_employee.national_id = '1010101010'
        self.own_employee.employee_number = 'EMP-1'
        self.own_employee.save()

        self.other_employee.national_id = '2020202020'
        self.other_employee.employee_number = 'EMP-2'
        self.other_employee.save()

        self.url = reverse('reconcile_employees')

    def post_file(self, buffer, user='branch_a', password='Str0ngPass!2024'):
        self.client.login(username=user, password=password)
        return self.client.post(self.url, {'excel_file': buffer})

    def test_page_requires_login(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response['Location'])

    def test_row_absent_from_system_is_reported(self):
        buffer = build_workbook([['موظف جديد', '3030303030', 'EMP-9', 'نشط']])
        report = self.post_file(buffer).context['report']

        self.assertEqual(len(report['missing_in_system']), 1)
        self.assertEqual(report['missing_in_system'][0]['national_id'], '3030303030')

    def test_employee_absent_from_file_is_reported(self):
        buffer = build_workbook([['موظف أ', '1010101010', 'EMP-1', 'نشط']])
        report = self.post_file(buffer).context['report']

        self.assertEqual(report['matched_count'], 1)
        self.assertEqual(list(report['missing_in_file']), [])

    def test_differing_value_is_reported(self):
        buffer = build_workbook([['موظف أ', '1010101010', 'EMP-1', 'مستقيل']])
        report = self.post_file(buffer).context['report']

        self.assertEqual(len(report['differences']), 1)
        changed = report['differences'][0]['fields']
        self.assertEqual([f['label'] for f in changed], ['حالة الموظف'])
        self.assertEqual(changed[0]['system'], 'نشط')
        self.assertEqual(changed[0]['file'], 'مستقيل')

    def test_branch_user_never_sees_another_workplace(self):
        """صف يخصّ منشأة أخرى يُعدّ غير مسجّل، ولا يُكشف سجلها."""
        buffer = build_workbook([['موظف ب', '2020202020', 'EMP-2', 'نشط']])
        report = self.post_file(buffer).context['report']

        self.assertEqual(report['total_system'], 1)
        self.assertEqual(len(report['missing_in_system']), 1)
        names = [e.full_name for e in report['missing_in_file']]
        self.assertNotIn('موظف ب', names)

    def test_arabic_digits_and_numeric_cells_match(self):
        """رقم الهوية كرقم أو بأرقام عربية يطابق النص المخزَّن."""
        buffer = build_workbook([['موظف أ', 1010101010, 'EMP-1', 'نشط']])
        self.assertEqual(self.post_file(buffer).context['report']['matched_count'], 1)

        buffer = build_workbook([['موظف أ', '١٠١٠١٠١٠١٠', 'EMP-1', 'نشط']])
        self.assertEqual(self.post_file(buffer).context['report']['matched_count'], 1)

    def test_duplicate_row_is_flagged_not_double_counted(self):
        buffer = build_workbook([
            ['موظف أ', '1010101010', 'EMP-1', 'نشط'],
            ['موظف أ', '1010101010', 'EMP-1', 'نشط'],
        ])
        report = self.post_file(buffer).context['report']

        self.assertEqual(report['matched_count'], 1)
        self.assertEqual(len(report['unreadable_rows']), 1)
        self.assertIn('مكرر', report['unreadable_rows'][0]['reason'])

    def test_row_without_any_identifier_is_flagged(self):
        buffer = build_workbook([['بلا معرّف', None, None, 'نشط']])
        report = self.post_file(buffer).context['report']

        self.assertEqual(len(report['unreadable_rows']), 1)
        self.assertEqual(report['missing_in_system'], [])

    def test_file_without_identifier_column_is_rejected(self):
        buffer = build_workbook([['موظف أ', 'نشط']], headers=['اسم الموظف', 'حالة الموظف'])
        response = self.post_file(buffer)

        self.assertIsNone(response.context['report'])
        self.assertContains(response, 'رقم الهوية', status_code=200)

    def test_non_xlsx_upload_is_rejected(self):
        import io

        fake = io.BytesIO(b'name,id\nfoo,1\n')
        fake.name = 'employees.csv'
        response = self.post_file(fake)

        self.assertIsNone(response.context['report'])

    def test_comparison_never_writes_to_the_database(self):
        before = list(Employee.objects.values_list('full_name', 'status', 'national_id'))
        buffer = build_workbook([
            ['اسم مختلف تماماً', '1010101010', 'EMP-1', 'مستقيل'],
            ['موظف جديد', '9090909090', 'EMP-99', 'نشط'],
        ])
        self.post_file(buffer)

        self.assertEqual(before, list(Employee.objects.values_list('full_name', 'status', 'national_id')))

    def test_template_download_is_an_xlsx(self):
        self.client.login(username='branch_a', password='Str0ngPass!2024')
        response = self.client.get(reverse('reconcile_template'))

        self.assertEqual(response.status_code, 200)
        self.assertIn('spreadsheetml', response['Content-Type'])


class OtherWorkplaceTests(SecurityTestCase):
    """خيار «أخرى» في المنشأة الحالية: يُنشئ منشأة حقيقية، ولمدير النظام وحده."""

    def base_payload(self, **overrides):
        payload = {
            'full_name': 'موظف جديد',
            'gender': 'M',
            'nationality': 'سعودي',
            'status': 'نشط',
            'is_classified': 'غير مصنف',
            'has_sub_specialty': 'لا',
            'current_workplace': '__other__',
            'new_workplace_name': 'مستشفى خميس مشيط العام',
        }
        payload.update(overrides)
        return payload

    def test_admin_creates_the_workplace_by_name(self):
        self.client.login(username='admin', password='Str0ngAdminPass!')
        response = self.client.post(reverse('add_employee'), self.base_payload())

        self.assertEqual(response.status_code, 302)
        workplace = Workplace.objects.get(name='مستشفى خميس مشيط العام')
        employee = Employee.objects.get(full_name='موظف جديد')
        self.assertEqual(employee.current_workplace, workplace)

    def test_existing_workplace_is_reused_not_duplicated(self):
        self.client.login(username='admin', password='Str0ngAdminPass!')
        self.client.post(self.base_payload_url(), self.base_payload(
            new_workplace_name='  مستشفى   أ  '))          # مسافات زائدة

        self.assertEqual(Workplace.objects.filter(name__iexact='مستشفى أ').count(), 1)
        self.assertEqual(Employee.objects.get(full_name='موظف جديد').current_workplace,
                         self.hospital_a)

    def base_payload_url(self):
        return reverse('add_employee')

    def test_blank_name_is_rejected(self):
        self.client.login(username='admin', password='Str0ngAdminPass!')
        response = self.client.post(
            reverse('add_employee'), self.base_payload(new_workplace_name='   ')
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(Employee.objects.filter(full_name='موظف جديد').exists())
        self.assertIn('new_workplace_name', response.context['form'].errors)

    def test_nothing_is_created_when_another_field_fails(self):
        """المنشأة تُنشأ عند الحفظ لا أثناء التحقق، فلا تبقى معلّقة عند الفشل."""
        self.client.login(username='admin', password='Str0ngAdminPass!')
        before = Workplace.objects.count()
        response = self.client.post(reverse('add_employee'), self.base_payload(
            full_name='',                                   # حقل مطلوب فارغ
            new_workplace_name='منشأة لا يجب أن تُنشأ',
        ))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Workplace.objects.count(), before)
        self.assertFalse(Workplace.objects.filter(name='منشأة لا يجب أن تُنشأ').exists())

    def test_branch_user_cannot_use_other(self):
        """مستخدم الفرع محصور بمنشأته — وإلا أنشأ موظفاً يختفي عنه فوراً."""
        self.client.login(username='branch_a', password='Str0ngPass!2024')
        before = Workplace.objects.count()
        response = self.client.post(reverse('add_employee'), self.base_payload())

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Workplace.objects.count(), before)
        self.assertFalse(Employee.objects.filter(full_name='موظف جديد').exists())

    def test_option_is_absent_for_a_branch_user(self):
        # النص يرد في سكربت الصفحة لكل المستخدمين؛ المهم غيابه كخيار في القائمة.
        self.client.login(username='branch_a', password='Str0ngPass!2024')
        self.assertNotContains(
            self.client.get(reverse('add_employee')), 'value="__other__"'
        )

    def test_option_is_offered_to_the_admin(self):
        self.client.login(username='admin', password='Str0ngAdminPass!')
        self.assertContains(
            self.client.get(reverse('add_employee')), 'value="__other__"'
        )

    def test_normal_selection_still_works(self):
        self.client.login(username='admin', password='Str0ngAdminPass!')
        before = Workplace.objects.count()
        self.client.post(reverse('add_employee'), self.base_payload(
            current_workplace=str(self.hospital_b.pk),
            new_workplace_name='لا يجب استخدامه',
        ))

        self.assertEqual(Workplace.objects.count(), before)
        self.assertEqual(Employee.objects.get(full_name='موظف جديد').current_workplace,
                         self.hospital_b)


class OtherWorkplaceTypeTests(SecurityTestCase):
    """خيار «أخرى» في نوع المنشأة: النص المكتوب يُخزَّن في الحقل نفسه."""

    def payload(self, **overrides):
        data = {
            'full_name': 'موظف نوع مخصص',
            'gender': 'M',
            'nationality': 'سعودي',
            'status': 'نشط',
            'is_classified': 'غير مصنف',
            'has_sub_specialty': 'لا',
            'current_workplace': str(self.hospital_a.pk),
            'workplace_type': '__other_type__',
            'other_workplace_type': 'قطاع خاص',
        }
        data.update(overrides)
        return data

    def test_typed_type_is_stored_on_the_employee(self):
        self.client.login(username='admin', password='Str0ngAdminPass!')
        response = self.client.post(reverse('add_employee'), self.payload())

        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            Employee.objects.get(full_name='موظف نوع مخصص').workplace_type, 'قطاع خاص'
        )

    def test_whitespace_is_collapsed(self):
        self.client.login(username='admin', password='Str0ngAdminPass!')
        self.client.post(reverse('add_employee'),
                         self.payload(other_workplace_type='  قطاع   خاص  '))

        self.assertEqual(
            Employee.objects.get(full_name='موظف نوع مخصص').workplace_type, 'قطاع خاص'
        )

    def test_blank_typed_type_is_rejected(self):
        self.client.login(username='admin', password='Str0ngAdminPass!')
        response = self.client.post(reverse('add_employee'),
                                    self.payload(other_workplace_type='  '))

        self.assertEqual(response.status_code, 200)
        self.assertIn('other_workplace_type', response.context['form'].errors)
        self.assertFalse(Employee.objects.filter(full_name='موظف نوع مخصص').exists())

    def test_listed_type_still_saves_normally(self):
        self.client.login(username='admin', password='Str0ngAdminPass!')
        self.client.post(reverse('add_employee'), self.payload(
            workplace_type='مدن طبية', time_type='كلي',
            other_workplace_type='يجب تجاهله',
        ))

        self.assertEqual(
            Employee.objects.get(full_name='موظف نوع مخصص').workplace_type, 'مدن طبية'
        )

    def test_editing_a_custom_type_preselects_other(self):
        """بدون هذا يظهر الحقل فارغاً فتضيع القيمة المحفوظة عند أول حفظ."""
        employee = Employee.objects.create(
            full_name='موظف قائم', gender='M',
            current_workplace=self.hospital_a, workplace_type='قطاع خاص',
        )
        form = EmployeeForm(instance=employee, user=self.admin)

        self.assertEqual(form.initial['workplace_type'], '__other_type__')
        self.assertEqual(form.initial['other_workplace_type'], 'قطاع خاص')

    def test_editing_a_listed_type_is_untouched(self):
        employee = Employee.objects.create(
            full_name='موظف قائم', gender='M',
            current_workplace=self.hospital_a, workplace_type='مدن طبية',
        )
        form = EmployeeForm(instance=employee, user=self.admin)

        self.assertNotIn('other_workplace_type', form.initial)

    def test_branch_user_may_type_a_type(self):
        """نوع المنشأة وصف لا يحدّد صلاحية، فلا سبب لحصره بمدير النظام."""
        self.client.login(username='branch_a', password='Str0ngPass!2024')
        response = self.client.post(reverse('add_employee'), self.payload())

        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            Employee.objects.get(full_name='موظف نوع مخصص').workplace_type, 'قطاع خاص'
        )


class ContractDatesByEmployeeTypeTests(SecurityTestCase):
    """تواريخ العقد تتبع «فئة الموظف» لا «فئة الموظف (الكادر)».

    خدمة مدنية: لا عقد، فأي تاريخ يُرسل يُمحى.
    غير ذلك:    تاريخ نهاية العقد إلزامي.
    """

    def payload(self, **overrides):
        data = {
            'full_name': 'موظف عقد',
            'gender': 'M',
            'nationality': 'سعودي',
            'status': 'نشط',
            'is_classified': 'غير مصنف',
            'has_sub_specialty': 'لا',
            'current_workplace': self.hospital_a.pk,
        }
        data.update(overrides)
        return data

    def test_civil_service_saves_without_contract_dates(self):
        self.client.login(username='admin', password='Str0ngAdminPass!')
        response = self.client.post(
            reverse('add_employee'), self.payload(employee_type='خدمة مدنية')
        )

        self.assertEqual(response.status_code, 302)
        employee = Employee.objects.get(full_name='موظف عقد')
        self.assertIsNone(employee.contract_end_date)

    def test_civil_service_discards_dates_sent_anyway(self):
        """الإخفاء في المتصفح لا يمنع إرسال الحقلين يدوياً."""
        self.client.login(username='admin', password='Str0ngAdminPass!')
        self.client.post(reverse('add_employee'), self.payload(
            employee_type='خدمة مدنية',
            contract_start_date='2026-01-01',
            contract_end_date='2026-12-31',
        ))

        employee = Employee.objects.get(full_name='موظف عقد')
        self.assertIsNone(employee.contract_start_date)
        self.assertIsNone(employee.contract_end_date)

    def test_other_type_requires_an_end_date(self):
        self.client.login(username='admin', password='Str0ngAdminPass!')
        response = self.client.post(
            reverse('add_employee'), self.payload(employee_type='تشغيل ذاتي')
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(Employee.objects.filter(full_name='موظف عقد').exists())
        self.assertIn('contract_end_date', response.context['form'].errors)

    def test_other_type_saves_with_an_end_date(self):
        self.client.login(username='admin', password='Str0ngAdminPass!')
        response = self.client.post(reverse('add_employee'), self.payload(
            employee_type='تشغيل ذاتي',
            contract_start_date='2026-01-01',
            contract_end_date='2026-12-31',
        ))

        self.assertEqual(response.status_code, 302)
        employee = Employee.objects.get(full_name='موظف عقد')
        self.assertEqual(str(employee.contract_end_date), '2026-12-31')

    def test_blank_type_requires_nothing(self):
        """الحقل نفسه اختياري، فلا يُلزم من تركه فارغاً بتاريخ عقد."""
        self.client.login(username='admin', password='Str0ngAdminPass!')
        response = self.client.post(reverse('add_employee'), self.payload())

        self.assertEqual(response.status_code, 302)
        self.assertIsNone(Employee.objects.get(full_name='موظف عقد').contract_end_date)

    def test_end_before_start_is_still_rejected(self):
        self.client.login(username='admin', password='Str0ngAdminPass!')
        response = self.client.post(reverse('add_employee'), self.payload(
            employee_type='تشغيل ذاتي',
            contract_start_date='2026-12-31',
            contract_end_date='2026-01-01',
        ))

        self.assertEqual(response.status_code, 200)
        self.assertIn('contract_end_date', response.context['form'].errors)

    def test_switching_to_civil_service_clears_stored_dates(self):
        """موظف بعقد قائم غُيِّرت فئته: لا تبقى تواريخ عقد معلّقة."""
        employee = Employee.objects.create(
            full_name='موظف قائم', gender='M', current_workplace=self.hospital_a,
            employee_type='تشغيل ذاتي',
            contract_start_date='2025-01-01', contract_end_date='2025-12-31',
        )
        self.client.login(username='admin', password='Str0ngAdminPass!')
        response = self.client.post(
            reverse('edit_employee', args=[employee.pk]),
            self.payload(full_name='موظف قائم', employee_type='خدمة مدنية'),
        )

        self.assertEqual(response.status_code, 302)
        employee.refresh_from_db()
        self.assertIsNone(employee.contract_start_date)
        self.assertIsNone(employee.contract_end_date)
