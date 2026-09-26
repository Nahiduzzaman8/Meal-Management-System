# Meal Management System

After running `python manage.py migrate`, create the initial Admin user using:

```bash
source venv/bin/activate
python manage.py create_admin
```

This command is the ONLY supported way to create an Admin account. There is no API endpoint to create Admin users.
