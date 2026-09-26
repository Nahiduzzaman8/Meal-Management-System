from django.test import TestCase
from django.contrib.auth import get_user_model

from apps.months.models import Month, ManagerAssignment

User = get_user_model()


class UserManagementEndpointTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username='admin',
            email='admin@example.com',
            password='AdminPass!234',
            role='ADMIN',
            must_change_password=False,
        )
        self.admin_token = self._get_token_for_user(self.admin)

        self.manager = User.objects.create_user(
            username='manager',
            email='manager@example.com',
            password='ManagerPass!234',
            role='MEMBER',
            must_change_password=False,
        )
        self.month = Month.objects.create(
            name='2026-09',
            start_date='2026-09-01',
            end_date='2026-09-30',
            status=Month.Status.OPEN,
            created_by=self.admin,
        )
        self.assignment = ManagerAssignment.objects.create(
            month=self.month,
            user=self.manager,
            assigned_by=self.admin,
        )

    def _get_token_for_user(self, user):
        response = self.client.post(
            '/api/auth/login/',
            {'username': user.username, 'password': 'AdminPass!234' if user.username == 'admin' else 'ManagerPass!234'},
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200, response.content)
        return response.json()['access']

    def _auth(self, token):
        return {'HTTP_AUTHORIZATION': f'Bearer {token}'}

    def test_create_user_returns_one_time_temporary_password_and_never_reappears(self):
        payload = {
            'username': 'newmember',
            'email': 'newmember@example.com',
            'role': 'MEMBER',
            'first_name': 'New',
            'last_name': 'Member',
            'phone': '5551234',
        }

        response = self.client.post('/api/users/', payload, content_type='application/json', **self._auth(self.admin_token))
        self.assertEqual(response.status_code, 201, response.content)
        body = response.json()
        self.assertIn('temporary_password', body)
        temp = body['temporary_password']
        self.assertTrue(temp)

        created = User.objects.get(username='newmember')
        self.assertTrue(created.check_password(temp))
        self.assertTrue(created.must_change_password)

        detail_response = self.client.get(f'/api/users/{created.pk}/', **self._auth(self.admin_token))
        self.assertEqual(detail_response.status_code, 200)
        self.assertNotIn('temporary_password', detail_response.json())

        list_response = self.client.get('/api/users/', **self._auth(self.admin_token))
        self.assertEqual(list_response.status_code, 200)
        self.assertNotIn('temporary_password', list_response.json()['results'][0])

    def test_deactivating_active_manager_of_open_month_is_blocked(self):
        response = self.client.post(f'/api/users/{self.manager.pk}/deactivate/', **self._auth(self.admin_token))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['code'], 'cannot_deactivate_active_manager')

        self.manager.refresh_from_db()
        self.assertTrue(self.manager.is_active)

    def test_username_is_immutable_via_patch_even_by_admin(self):
        target = User.objects.create_user(
            username='targetuser',
            email='target@example.com',
            password='TargetPass!234',
            role='MEMBER',
            must_change_password=False,
        )

        response = self.client.patch(
            f'/api/users/{target.pk}/',
            {'username': 'changedname'},
            content_type='application/json',
            **self._auth(self.admin_token),
        )

        self.assertEqual(response.status_code, 400, response.content)
        self.assertIn('username', response.json())

        target.refresh_from_db()
        self.assertEqual(target.username, 'targetuser')

    def test_reset_password_re_arms_must_change_password(self):
        target = User.objects.create_user(
            username='resetme',
            email='resetme@example.com',
            password='OldPass!234',
            role='MEMBER',
            must_change_password=False,
        )

        response = self.client.post(f'/api/users/{target.pk}/reset-password/', **self._auth(self.admin_token))
        self.assertEqual(response.status_code, 200, response.content)
        body = response.json()
        self.assertIn('temporary_password', body)
        temp = body['temporary_password']

        target.refresh_from_db()
        self.assertTrue(target.must_change_password)
        self.assertTrue(target.check_password(temp))
