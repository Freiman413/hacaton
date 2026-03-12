import os
import sqlite3
from dotenv import load_dotenv

load_dotenv()


def get_db_path():
    db_name = os.getenv("DB_name")
    if db_name is None:
        raise ValueError("DB_name variable is missing from .env")
    db_name = db_name.strip('"').strip("'").strip()
    current_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(current_dir, db_name)


def init_database():
    db_path = get_db_path()

    if not os.path.exists(db_path):
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.executescript("""
                CREATE TABLE Students (
                student_id INTEGER PRIMARY KEY,
                first_name TEXT NOT NULL,
                last_name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                age INTEGER,
                phone TEXT,
                password_hash TEXT
                );

                CREATE TABLE Lecturers (
                    lecturer_id INTEGER PRIMARY KEY,
                    first_name TEXT NOT NULL,
                    last_name TEXT NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    department TEXT NOT NULL
                );
                                 
                CREATE TABLE Courses (
                    course_id INTEGER PRIMARY KEY,
                    course_name TEXT NOT NULL,
                    start_date TEXT NOT NULL,
                    end_date TEXT NOT NULL,
                    course_year INTEGER NOT NULL,
                    degree_type TEXT NOT NULL,
                    lecturer_id INTEGER,
                    FOREIGN KEY (lecturer_id) REFERENCES Lecturers(lecturer_id)
                );

                CREATE TABLE Exams (
                    exam_id INTEGER PRIMARY KEY,
                    course_id INTEGER NOT NULL,
                    exam_name TEXT NOT NULL,
                    exam_group INTEGER NOT NULL,
                    date TEXT NOT NULL,
                    hour INTEGER NOT NULL,
                    exam_duration INTEGER NOT NULL,           
                    building_number INTEGER NOT NULL,
                    room_number INTEGER NOT NULL,
                    weight_percentage REAL NOT NULL,
                    exam_attempt TEXT NOT NULL CHECK(exam_attempt IN ('A', 'B')),
                    is_final_grade_component INTEGER NOT NULL CHECK(is_final_grade_component IN (0, 1)),
                    include_in_semester_avg INTEGER NOT NULL CHECK(include_in_semester_avg IN (0, 1)),
                    FOREIGN KEY (course_id) REFERENCES Courses(course_id)
                );

                CREATE TABLE Grades (
                    grade_id INTEGER PRIMARY KEY,
                    student_id INTEGER NOT NULL,
                    exam_id INTEGER NOT NULL,
                    grade_received INTEGER,
                    FOREIGN KEY (student_id) REFERENCES Students(student_id),
                    FOREIGN KEY (exam_id) REFERENCES Exams(exam_id)
                );

                CREATE TABLE Lessons (
                    lesson_id INTEGER PRIMARY KEY,
                    course_id INTEGER NOT NULL,
                    date TEXT NOT NULL,
                    hour INTEGER NOT NULL,
                    building_number INTEGER NOT NULL,
                    room_number INTEGER NOT NULL,
                    FOREIGN KEY (course_id) REFERENCES Courses(course_id)
                );

                CREATE TABLE Office_Hours (
                    office_hour_id INTEGER PRIMARY KEY,
                    lecturer_id INTEGER NOT NULL,
                    date TEXT NOT NULL,
                    hour INTEGER NOT NULL,
                    location TEXT NOT NULL,
                    FOREIGN KEY (lecturer_id) REFERENCES Lecturers(lecturer_id)
                );

                CREATE TABLE Student_Courses (
                    registration_id INTEGER PRIMARY KEY,
                    student_id INTEGER NOT NULL,
                    course_id INTEGER NOT NULL,
                    FOREIGN KEY (student_id) REFERENCES Students(student_id),
                    FOREIGN KEY (course_id) REFERENCES Courses(course_id),
                    UNIQUE (student_id, course_id)
                );
            """)
            conn.commit()
           

if __name__ == "__main__":
    init_database()
    print(f"Database ready at: {get_db_path()}")