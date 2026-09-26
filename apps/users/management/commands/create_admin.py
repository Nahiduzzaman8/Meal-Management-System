from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from django.core import exceptions
from django.contrib.auth.password_validation import validate_password, get_default_password_validators
from django.conf import settings

import getpass


class Command(BaseCommand):
    help = 'Create the initial admin superuser for the system (only supported creation method)'

    def add_arguments(self, parser):
        parser.add_argument('--username', dest='username', help='Username')
        parser.add_argument('--email', dest='email', help='Email')
        parser.add_argument('--password', dest='password', help='Password')
        parser.add_argument('--noinput', action='store_true', dest='noinput', help='Do not prompt for input')
        parser.add_argument('--force', action='store_true', dest='force', help='Force creation even if a superuser exists')

    def handle(self, *args, **options):
        User = get_user_model()

        # check existing superuser
        existing = User.objects.filter(is_superuser=True).first()
        if existing and not options.get('force'):
            self.stdout.write(self.style.ERROR(f"A superuser already exists: {existing.username}. Use --force to override."))
            return

        username = options.get('username')
        email = options.get('email')
        password = options.get('password')
        noinput = options.get('noinput')

        if noinput:
            if not username or not email or not password:
                raise CommandError('When using --noinput you must provide --username, --email and --password')
        else:
            if not username:
                username = input('Username: ').strip()
            if not email:
                email = input('Email: ').strip()
            if not password:
                while True:
                    pwd = getpass.getpass('Password: ')
                    pwd2 = getpass.getpass('Password (again): ')
                    if pwd != pwd2:
                        self.stdout.write(self.style.ERROR('Passwords do not match.'))
                        continue
                    password = pwd
                    break

        # check duplicates
        if User.objects.filter(username=username).exists():
            raise CommandError('Username already exists')
        if User.objects.filter(email=email).exists():
            raise CommandError('Email already exists')

        # validate password
        try:
            validate_password(password, user=None, password_validators=get_default_password_validators())
        except exceptions.ValidationError as e:
            raise CommandError('; '.join(e.messages))

        # create user
        user = User(username=username, email=email)
        user.set_password(password)
        user.is_superuser = True
        user.is_staff = True
        user.role = User.Roles.ADMIN
        user.must_change_password = False
        user.is_active = True
        user.save()

        self.stdout.write(self.style.SUCCESS(f'Created superuser: {user.username} ({user.email}) role={user.role}'))
