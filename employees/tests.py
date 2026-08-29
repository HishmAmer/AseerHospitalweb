from django.contrib.auth.models import User
from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse

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
