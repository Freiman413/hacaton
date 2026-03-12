import sqlite3
from .db import get_db_path



def get_db():
    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row
    return conn

def get_lecturers_with_courses():
    with get_db() as conn:
        rows = conn.execute("""
            SELECT l.lecturer_id, l.first_name, l.last_name, l.email, l.department,
                   c.course_name, c.degree_type, c.course_year
            FROM Lecturers l
            LEFT JOIN Courses c ON c.lecturer_id = l.lecturer_id
            ORDER BY l.last_name
        """).fetchall()
    return rows

def get_students(course_id: int):
    with get_db() as conn:
        rows = conn.execute(
            """SELECT s.student_id, s.first_name, s.last_name, s.email, sc.course_id
               FROM Students s
               JOIN Student_Courses sc ON sc.student_id = s.student_id
               WHERE sc.course_id = ?
               ORDER BY s.last_name, s.first_name""",(course_id,)).fetchall()
    return [dict(r) for r in rows]

def get_lessons(course_id: int):
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM Lessons WHERE course_id = ? ORDER BY date, hour",(course_id,)).fetchall()
    return [dict(r) for r in rows]

def get_exams(course_id: int):
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM Exams WHERE course_id = ? ORDER BY date, hour",(course_id,)).fetchall()
    return [dict(r) for r in rows]

def get_grades(course_id: int):
    with get_db() as conn:
        rows = conn.execute(
            """SELECT g.grade_id, g.student_id, g.exam_id, g.grade_received,
                      s.first_name || ' ' || s.last_name AS student_name
               FROM Grades g
               JOIN Students s ON s.student_id = g.student_id
               JOIN Exams e    ON e.exam_id = g.exam_id
               WHERE e.course_id = ?
               ORDER BY e.exam_id, s.last_name""", (course_id,)).fetchall()
    return [dict(r) for r in rows]

def get_office_hours(lecturer_id: int):
    with sqlite3.connect(get_db_path()) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.execute("SELECT office_hour_id, date, hour, location FROM Office_Hours WHERE lecturer_id = ?",(lecturer_id,))
        return cur.fetchall()
    

