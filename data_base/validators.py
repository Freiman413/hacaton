import re
from datetime import date as dt

def validate_name(name: str):
    name = name.strip()
    if not name.isalpha():
        raise ValueError(f"Name '{name}' must contain letters only.")
    if len(name) < 3:
        raise ValueError(f"Name '{name}' is too short (minimum 3 characters).")
    return name


def validate_email(email: str):
    email = email.strip().lower()
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        raise ValueError(f"'{email}' is not a valid email address.")
    return email

def validate_hour(hour: str):
    parts = hour.strip().split(":")
    h = int(parts[0])
    if h < 8 or h > 20:
        raise ValueError("Hour must be between 08:00 and 20:00.")
    return hour.strip()

def validate_future_date(date: str):
    parsed = dt.fromisoformat(date.strip())
    if parsed <= dt.today():
        raise ValueError(f"Date '{date}' must be in the future.")
    return date.strip()

def validate_exam_name(name: str):
    name = name.strip()
    if len(name) < 3:
        raise ValueError(f"Exam name '{name}' is too short (minimum 3 characters).")
    for c in name:
        if not c.isalpha() and not c.isspace():
            raise ValueError(f"Exam name '{name}' must contain letters and spaces only.")
    return name


def validate_passwords_match(password: str, confirm: str):
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters.")
    if password != confirm:
        raise ValueError("Passwords do not match.")
    return password