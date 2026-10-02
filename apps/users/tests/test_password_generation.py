from django.test import TestCase

from apps.users.utils import generate_temp_password


class TemporaryPasswordGenerationTests(TestCase):
    def test_generate_temp_password_excludes_json_breaking_characters(self):
        forbidden = {'\\', '"', "'"}

        for _ in range(100):
            temp = generate_temp_password()
            self.assertEqual(len(temp), 16)
            self.assertTrue(set(temp).isdisjoint(forbidden), f'Generated password contains forbidden JSON chars: {temp!r}')
