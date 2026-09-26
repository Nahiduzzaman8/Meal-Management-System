from django.test import TestCase
from django.contrib.auth import get_user_model

from apps.users.permissions import ROLE_CAPABILITIES, MANAGER_CAPABILITIES
from apps.months.models import Month, ManagerAssignment

User = get_user_model()


class PermissionTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create(username='admin', is_superuser=False, role='ADMIN')
        self.member = User.objects.create(username='member', role='MEMBER')
        # create an open month and assign manager later
        self.open_month = Month.objects.create(name='2026-09', start_date='2026-09-01', end_date='2026-09-30', status=Month.Status.OPEN, created_by=self.admin)

    def test_admin_has_every_capability(self):
        for code in list(ROLE_CAPABILITIES.get('ADMIN', [])) + list(MANAGER_CAPABILITIES):
            self.assertTrue(self.admin.has_capability(code))

    def test_member_has_base_caps_only(self):
        for code in ROLE_CAPABILITIES.get('MEMBER', []):
            self.assertTrue(self.member.has_capability(code))
        for code in MANAGER_CAPABILITIES:
            self.assertFalse(self.member.has_capability(code))

    def test_member_becomes_manager_gets_manager_caps(self):
        ManagerAssignment.objects.create(month=self.open_month, user=self.member, assigned_by=self.admin)
        for code in MANAGER_CAPABILITIES:
            self.assertTrue(self.member.has_capability(code))

    def test_unassigned_member_loses_manager_caps(self):
        ma = ManagerAssignment.objects.create(month=self.open_month, user=self.member, assigned_by=self.admin)
        # unassign
        ma.unassigned_at = '2026-09-15T00:00:00'
        ma.save()
        for code in MANAGER_CAPABILITIES:
            self.assertFalse(self.member.has_capability(code))
