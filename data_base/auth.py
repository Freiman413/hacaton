import os
from datetime import datetime, timezone, timedelta

from dotenv import load_dotenv
from jose import jwt, JWTError

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
MASTER_EMAIL = os.getenv("MASTER_EMAIL")
MASTER_PASSWORD = os.getenv("MASTER_PASSWORD")
TOKEN_TTL_HOURS = 24


def _make_token(sub, role):
    exp = datetime.now(timezone.utc) + timedelta(hours=TOKEN_TTL_HOURS)
    payload = {"sub": sub, "role": role, "exp": exp}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def _get_db():
    import sqlite3
    from data_base.db import get_db_path
    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row
    return conn


def login(email, password):
    email = email.strip().lower()

    if email == (MASTER_EMAIL or "").strip().lower() and password == MASTER_PASSWORD:
        token = _make_token("master", "master")
        return {"token": token, "role": "master"}

    try:
        conn = _get_db()
    except Exception as exc:
        raise ValueError(f"Database error: {exc}") from exc

    try:
        row = conn.execute(
            "SELECT lecturer_id, password_hash FROM Lecturers WHERE email = ?",
            (email,)
        ).fetchone()
        if row and password == row["password_hash"]:
            token = _make_token(str(row["lecturer_id"]), "lecturer")
            return {"token": token, "role": "lecturer"}

        row = conn.execute(
            "SELECT student_id, password_hash FROM Students WHERE email = ?",
            (email,)
        ).fetchone()
        if row and row["password_hash"] and password == row["password_hash"]:
            token = _make_token(str(row["student_id"]), "student")
            return {"token": token, "role": "student"}

    except Exception as e:
        raise ValueError(f"invalid: {e}")
    finally:
        conn.close()

    raise ValueError("Invalid email or password.")


def decode_token(token):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError as exc:
        raise ValueError(f"Invalid or expired token: {exc}") from exc


def get_role_from_request(request):
    token = request.cookies.get("access_token")
    if not token:
        raise ValueError("Not authenticated.")
    payload = decode_token(token)
    role = payload.get("role")
    if not role:
        raise ValueError("Token has no role.")
    return role


def get_student_id_from_request(request):
    token = request.cookies.get("access_token")
    if not token:
        raise ValueError("No access allowed.")
    payload = decode_token(token)
    student_id = payload.get("sub")
    if not student_id:
        raise ValueError("No student ID found in token.")
    return int(student_id)