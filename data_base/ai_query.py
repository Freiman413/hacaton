from .query import get_db
from datetime import date, timedelta





def get_student_name(student_id: int):
    with get_db() as conn:
        row = conn.execute("SELECT first_name FROM Students WHERE student_id = ?", (student_id,)).fetchone()
    if not row:
        raise ValueError("Student not found.")
    return row["first_name"]



def get_student_courses(student_id: int):
    with get_db() as conn:
        today = date.today().isoformat()
        rows = conn.execute("""SELECT c.* FROM Courses c JOIN Student_Courses sc ON sc.course_id = c.course_id 
               WHERE sc.student_id = ? AND ? BETWEEN c.start_date AND c.end_date""", (student_id, today)).fetchall()
    if not rows:
        raise ValueError("you has no active courses.")
    return [dict(r) for r in rows]


def get_exams_by_course(course_id: int) -> list:
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM Exams WHERE course_id = ?",(course_id,)).fetchall()
    if not rows:
        raise ValueError("Exam date not yet updated.")
    return [dict(r) for r in rows]



def get_rooms_by_course(course_id: int) -> dict:
    with get_db() as conn:
        lessons = conn.execute("SELECT * FROM Lessons WHERE course_id = ?", (course_id,)).fetchall()
        exams = conn.execute("SELECT * FROM Exams WHERE course_id = ?", (course_id,)).fetchall()
    if lessons:
        lessons_data = [dict(r) for r in lessons]
    else:
        lessons_data = "No lessons found."
    
    if exams:
        exams_data = [dict(r) for r in exams]
    else:
        exams_data = "No exams found."
    return {
        "lessons": lessons_data,
        "exams": exams_data
    }


def get_office_hours_by_course(course_id: int) -> dict:
    with get_db() as conn:
        lecturer = conn.execute("""
            SELECT l.email, l.first_name, l.last_name 
            FROM Lecturers l
            JOIN Courses c ON c.lecturer_id = l.lecturer_id
            WHERE c.course_id = ?
        """, (course_id,)).fetchone()
        
        office_hours = conn.execute("""
            SELECT oh.* FROM Office_Hours oh
            JOIN Courses c ON c.lecturer_id = oh.lecturer_id
            WHERE c.course_id = ?
        """, (course_id,)).fetchall()
    
    if not lecturer:
        raise ValueError("Lecturer not found.")
    
    if not office_hours:
        office_hours_data = "No office hours found."
    else:
        office_hours_data = [dict(r) for r in office_hours]
    
    return {
        "lecturer": dict(lecturer),
        "office_hours": office_hours_data
    }


def get_lessons_by_course(course_id: int):
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM Lessons WHERE course_id = ?",(course_id,)).fetchall()
    if rows:
        return [dict(r) for r in rows]
    else:
        return "No class schedule found."
    


def get_grades_by_course(course_id: int, student_id: int):
    with get_db() as conn:
        rows = conn.execute("""
            SELECT e.exam_name, e.weight_percentage, e.exam_attempt, 
            e.is_final_grade_component, e.exam_group, g.grade_received
            FROM Exams e
            LEFT JOIN Grades g ON g.exam_id = e.exam_id AND g.student_id = ?
            WHERE e.course_id = ?
            ORDER BY e.exam_name, e.exam_attempt""", (student_id, course_id)).fetchall()
    
    if rows:
        return [dict(r) for r in rows]
    else:
        return "No exams found."
    

def get_schedule_by_student(student_id: int) -> dict:
    with get_db() as conn:
        today = date.today().isoformat()
        week_end = (date.today() + timedelta(days=7)).isoformat()
        
        lessons = conn.execute("""
            SELECT l.*, c.course_name FROM Lessons l
            JOIN Courses c ON c.course_id = l.course_id
            JOIN Student_Courses sc ON sc.course_id = l.course_id
            WHERE sc.student_id = ? AND l.date BETWEEN ? AND ?
            ORDER BY l.date, l.hour""", (student_id, today, week_end)).fetchall()
        
        exams = conn.execute("""
            SELECT e.*, c.course_name FROM Exams e
            JOIN Courses c ON c.course_id = e.course_id
            JOIN Student_Courses sc ON sc.course_id = e.course_id
            WHERE sc.student_id = ? AND e.date BETWEEN ? AND ?
            ORDER BY e.date, e.hour""", (student_id, today, week_end)).fetchall()
    if lessons:
        lessons_data = [dict(r) for r in lessons]
    else:
        lessons_data = "No lessons found for this week."
    
    if exams:
        exams_data = [dict(r) for r in exams]
    else:
        exams_data = "No exams found for this week."
    
    return {
        "lessons": lessons_data,
        "exams": exams_data
    }