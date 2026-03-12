import sqlite3
from .db import get_db_path
from .validators import validate_name, validate_email, validate_passwords_match


def get_db():
    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row
    return conn


def complete_student_registration(email, first_name, last_name, age, phone, password, password2):
    email      = validate_email(email)
    first_name = validate_name(first_name)
    last_name  = validate_name(last_name)
    password   = validate_passwords_match(password, password2)

    if age < 18 or age > 99:
        raise ValueError("Age must be between 16 and 99.")
    if not phone.strip():
        raise ValueError("Phone cannot be empty.")

    with get_db() as conn:
        row = conn.execute(
            "SELECT student_id, password_hash FROM Students WHERE email = ?", (email,)).fetchone()
        if row is None:
            raise ValueError("not_approved")

        if row["password_hash"]:
            raise ValueError("exists")

        conn.execute(
            """UPDATE Students
               SET first_name = ?, last_name = ?, age = ?, phone = ?, password_hash = ?
               WHERE email = ?""",
            (first_name, last_name, age, phone.strip(), password, email))
        conn.commit()
        result = conn.execute("SELECT student_id, first_name, last_name, email FROM Students WHERE email = ?",(email,)).fetchone()

    return dict(result)