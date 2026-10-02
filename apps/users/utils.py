import secrets
import string


def generate_temp_password(length: int = 16) -> str:
    """
    Generate a secure random temporary password. Excludes the backslash,
    double quote, and single quote, which break JSON parsing when this
    password is later submitted in a request body (for example, password change).
    """
    safe_symbols = "!@#$%^&*()-_=+"
    alphabet = string.ascii_letters + string.digits + safe_symbols
    return ''.join(secrets.choice(alphabet) for _ in range(length))
