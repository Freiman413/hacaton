import sqlite3
from .db import get_db_path
from .validators import validate_name, validate_email, validate_future_date, validate_hour

def get_db():
    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row
    return conn

def create_student(first_name: str, last_name: str, email: str, course_id: int):
    first_name = validate_name(first_name)
    last_name  = validate_name(last_name)
    email = validate_email(email)

    with get_db() as conn:
        row = conn.execute("SELECT student_id FROM Students WHERE email = ?", (email,)).fetchone()

        if row:
            student_id = row["student_id"]
        else:
            cur = conn.execute(
                "INSERT INTO Students (first_name, last_name, email) VALUES (?, ?, ?)",(first_name, last_name, email))
            student_id = cur.lastrowid

        conn.execute("INSERT OR IGNORE INTO Student_Courses (student_id, course_id) VALUES (?, ?)",(student_id, course_id))
        conn.commit()

        result = conn.execute(
            """SELECT s.student_id, s.first_name, s.last_name, s.email, sc.course_id
               FROM Students s
               JOIN Student_Courses sc ON sc.student_id = s.student_id
               WHERE s.student_id = ? AND sc.course_id = ?""",(student_id, course_id)).fetchone()

    return dict(result)

def create_lesson(course_id: int, date: str, hour: str, building_number: int, room_number: int):
    date = validate_future_date(date)
    hour = validate_hour(hour)
    with get_db() as conn:
        cur = conn.execute(
            "INSERT INTO Lessons (course_id, date, hour, building_number, room_number) VALUES (?, ?, ?, ?, ?)",(course_id, date, hour, building_number, room_number))
        conn.commit()
        row = conn.execute("SELECT * FROM Lessons WHERE lesson_id = ?", (cur.lastrowid,)).fetchone()
    return dict(row)

def delete_lesson(lesson_id: int, course_id: int) -> bool:
    with sqlite3.connect(get_db_path()) as conn:
        conn.execute("DELETE FROM Lessons WHERE lesson_id = ?", (lesson_id,))
        conn.commit()
    return True

def delete_exam(exam_id: int, course_id: int):
    with sqlite3.connect(get_db_path()) as conn:
        conn.execute("DELETE FROM Grades WHERE exam_id = ?", (exam_id,))
        conn.execute("DELETE FROM Exams WHERE exam_id = ?", (exam_id,))
        conn.commit()
    return True

def create_exam(course_id: int, exam_name: str, date: str, hour: str,exam_duration: int, building_number: int, room_number: int,
                weight_percentage: float, exam_attempt: str, is_final_grade_component: int, include_in_semester_avg: int, exam_group: int = None):
    exam_name = validate_name(exam_name)
    date = validate_future_date(date)
    hour = validate_hour(hour)
    if exam_duration < 20:
        raise ValueError("Exam duration must be at least 20 minutes.")
    if not (0 < weight_percentage <= 100):
        raise ValueError("Weight must be between 1 and 100.")
    if exam_attempt not in ("A", "B"):
        raise ValueError("Attempt must be A or B.")

    if exam_group is None:
        with get_db() as conn:
            existing = conn.execute(
                "SELECT exam_group FROM Exams WHERE course_id = ? AND exam_name = ?",
                (course_id, exam_name.strip())).fetchone()
            if existing:
                exam_group = existing["exam_group"]
            else:
                row = conn.execute("SELECT COALESCE(MAX(exam_group), 0) + 1 AS next_group FROM Exams WHERE course_id = ?", (course_id,)).fetchone()
                exam_group = row["next_group"]

    with get_db() as conn:
        cur = conn.execute(
            """INSERT INTO Exams (course_id, exam_name, date, hour, exam_duration,
               building_number, room_number, weight_percentage, exam_attempt,
               is_final_grade_component, include_in_semester_avg, exam_group)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (course_id, exam_name.strip(), date, hour, exam_duration, building_number, room_number, weight_percentage, exam_attempt, is_final_grade_component, include_in_semester_avg, exam_group))
        conn.commit()
        row = conn.execute("SELECT * FROM Exams WHERE exam_id = ?", (cur.lastrowid,)).fetchone()
    return dict(row)

def create_grade(student_id: int, exam_id: int, grade_received: int, course_id: int):
    if not (0 <= grade_received <= 100):
        raise ValueError("Grade must be between 0 and 100.")

    with get_db() as conn:
        exam = conn.execute(
            "SELECT exam_id FROM Exams WHERE exam_id = ? AND course_id = ?", (exam_id, course_id)).fetchone()
        if not exam:
            raise ValueError("Exam does not belong to this course.")

        cur = conn.execute("INSERT INTO Grades (student_id, exam_id, grade_received) VALUES (?, ?, ?)",(student_id, exam_id, grade_received))
        conn.commit()
        row = conn.execute("SELECT * FROM Grades WHERE grade_id = ?", (cur.lastrowid,)).fetchone()
    return dict(row)

def update_grade(grade_id: int, grade_received: int, course_id: int):
    if not (0 <= grade_received <= 100):
        raise ValueError("Grade must be between 0 and 100.")
    with get_db() as conn:
        cur = conn.execute("UPDATE Grades SET grade_received = ? WHERE grade_id = ? AND exam_id IN (SELECT exam_id FROM Exams WHERE course_id = ?)",(grade_received, grade_id, course_id)).rowcount
        conn.commit()
    return cur> 0

def create_lecturer(first_name, last_name, email, password, department):
    first_name = validate_name(first_name)
    last_name  = validate_name(last_name)
    email = validate_email(email)
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters.")

    with get_db() as conn:
        row = conn.execute("SELECT lecturer_id FROM Lecturers WHERE email = ?", (email,)).fetchone()
        if row:
            raise ValueError("A lecturer with this email already exists.")
        cur = conn.execute("INSERT INTO Lecturers (first_name, last_name, email, password_hash, department) VALUES (?, ?, ?, ?, ?)",(first_name, last_name, email, password, department.strip()))
        conn.commit()
        result = conn.execute("SELECT * FROM Lecturers WHERE lecturer_id = ?", (cur.lastrowid,)).fetchone()
    return dict(result)

def create_course(course_name: str, start_date: str, end_date: str,
                  course_year: int, degree_type: str, lecturer_id: int):
    if not course_name.strip():
        raise ValueError("Course name cannot be empty.")
    if not degree_type.strip():
        raise ValueError("Degree type cannot be empty.")
    with get_db() as conn:
        cur = conn.execute("INSERT INTO Courses (course_name, start_date, end_date, course_year, degree_type, lecturer_id) VALUES (?, ?, ?, ?, ?, ?)",(course_name.strip(), start_date, end_date, course_year, degree_type.strip(), lecturer_id))
        conn.commit()
        row = conn.execute("SELECT * FROM Courses WHERE course_id = ?", (cur.lastrowid,)).fetchone()
    return dict(row)

def create_lecturer_with_course(first_name: str, last_name: str, email: str, password: str, department: str, course_name: str,
                                start_date: str, end_date: str, course_year: int, degree_type: str):
    lecturer = create_lecturer(first_name, last_name, email, password, department)
    course   = create_course(course_name, start_date, end_date, course_year, degree_type, lecturer["lecturer_id"])
    return {"lecturer": lecturer, "course": course}

def delete_grade(grade_id: int, course_id: int):
    with sqlite3.connect(get_db_path()) as conn:
        conn.execute("DELETE FROM Grades WHERE grade_id = ?", (grade_id,))
        conn.commit()
    return True

def create_office_hour(lecturer_id: int, date: str, hour: str, location: str):
    with get_db() as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.execute("INSERT INTO Office_Hours (lecturer_id, date, hour, location) VALUES (?, ?, ?, ?) RETURNING office_hour_id, date, hour, location",(lecturer_id, date, hour, location))
        conn.commit()
        return cur.fetchone()

def delete_office_hour(office_hour_id: int):
    with get_db() as conn:
        cur = conn.execute("DELETE FROM Office_Hours WHERE office_hour_id = ?", (office_hour_id,))
        if cur.rowcount == 0:
            raise ValueError("Office hour not found")
        conn.commit()
    return True