from fastapi import APIRouter, Request
from dotenv import load_dotenv
import os

load_dotenv()
from fastapi.responses import JSONResponse
from jose import jwt, JWTError
import sqlite3

from data_base.db import get_db_path
from data_base.crud import (create_lesson, delete_lesson, create_exam, delete_exam, create_grade, update_grade, delete_grade, create_student, create_office_hour, delete_office_hour)
from data_base.query import get_lessons, get_exams, get_grades, get_students, get_office_hours

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM  = os.getenv("ALGORITHM", "HS256")

router = APIRouter(prefix="/api")


def get_current_course(request: Request):
    token = request.cookies.get("access_token")
    if not token:
        raise ValueError("Not authenticated")
    try:
        payload     = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        lecturer_id = int(payload.get("sub"))
    except (JWTError, TypeError, ValueError):
        raise ValueError("Invalid token")

    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT course_id FROM Courses WHERE lecturer_id = ? LIMIT 1",(lecturer_id,)).fetchone()
    conn.close()

    if not row:
        raise ValueError("No course found for this lecturer")
    return row["course_id"]

def auth_error(e: Exception):
    return JSONResponse(status_code=401, content={"error": str(e)})

@router.get("/lessons")
async def api_get_lessons(request: Request):
    try:
        course_id = get_current_course(request)
        return [dict(r) for r in get_lessons(course_id)]
    except ValueError as e:
        return auth_error(e)

@router.post("/lessons")
async def api_create_lesson(request: Request):
    try:
        course_id = get_current_course(request)
        body = await request.json()
        row = create_lesson(
            course_id=course_id,
            date=body["date"],
            hour=body["hour"],
            building_number=body["building_number"],
            room_number=body["room_number"],
        )
        return dict(row)
    except ValueError as e:
        return JSONResponse(status_code=400, content={"error": str(e)})


@router.delete("/lessons/{lesson_id}")
async def api_delete_lesson(lesson_id: int, request: Request):
    try:
        course_id = get_current_course(request)
        deleted = delete_lesson(lesson_id, course_id)
        if not deleted:
            return JSONResponse(status_code=404, content={"error": "Lesson not found"})
        return {"deleted": lesson_id}
    except ValueError as e:
        return auth_error(e)


@router.get("/exams")
async def api_get_exams(request: Request):
    try:
        course_id = get_current_course(request)
        return [dict(r) for r in get_exams(course_id)]
    except ValueError as e:
        return auth_error(e)


@router.post("/exams")
async def api_create_exam(request: Request):
    try:
        course_id = get_current_course(request)
        body = await request.json()
        row = create_exam(
            course_id=course_id,
            exam_name=body["exam_name"],
            date=body["date"],
            hour=body["hour"],
            exam_duration=body["exam_duration"],
            building_number=body["building_number"],
            room_number=body["room_number"],
            weight_percentage=body["weight_percentage"],
            exam_attempt=body["exam_attempt"],
            is_final_grade_component=body["is_final_grade_component"],
            include_in_semester_avg=body["include_in_semester_avg"],
        )
        return dict(row)
    except ValueError as e:
        return JSONResponse(status_code=400, content={"error": str(e)})


@router.delete("/exams/{exam_id}")
async def api_delete_exam(exam_id: int, request: Request):
    try:
        course_id = get_current_course(request)
        deleted = delete_exam(exam_id, course_id)
        if not deleted:
            return JSONResponse(status_code=404, content={"error": "Exam not found"})
        return {"deleted": exam_id}
    except ValueError as e:
        return auth_error(e)


@router.get("/grades")
async def api_get_grades(request: Request):
    try:
        course_id = get_current_course(request)
        return [dict(r) for r in get_grades(course_id)]
    except ValueError as e:
        return auth_error(e)

@router.post("/grades")
async def api_create_grade(request: Request):
    try:
        course_id = get_current_course(request)
        body = await request.json()
        row = create_grade(
            student_id=body["student_id"],
            exam_id=body["exam_id"],
            grade_received=body["grade_received"],
            course_id=course_id,
        )
        return dict(row)
    except ValueError as e:
        return JSONResponse(status_code=400, content={"error": str(e)})

@router.put("/grades/{grade_id}")
async def api_update_grade(grade_id: int, request: Request):
    try:
        course_id = get_current_course(request)
        body = await request.json()
        row = update_grade(
            grade_id=grade_id,
            grade_received=body["grade_received"],
            course_id=course_id,
        )
        return dict(row)
    except ValueError as e:
        return JSONResponse(status_code=400, content={"error": str(e)})


@router.delete("/grades/{grade_id}")
async def api_delete_grade(grade_id: int, request: Request):
    try:
        course_id = get_current_course(request)
        deleted = delete_grade(grade_id, course_id)
        if not deleted:
            return JSONResponse(status_code=404, content={"error": "Grade not found"})
        return {"deleted": grade_id}
    except ValueError as e:
        return auth_error(e)


@router.get("/students")
async def api_get_students(request: Request):
    try:
        course_id = get_current_course(request)
        return [dict(r) for r in get_students(course_id)]
    except ValueError as e:
        return auth_error(e)


@router.post("/students")
async def api_create_student(request: Request):
    try:
        course_id = get_current_course(request)
        body = await request.json()
        row = create_student(
            first_name=body["first_name"],
            last_name=body["last_name"],
            email=body["email"],
            course_id=course_id,
        )
        return dict(row)
    except ValueError as e:
        return JSONResponse(status_code=400, content={"error": str(e)})
    
@router.get("/office_hours")
async def api_get_office_hours(request: Request):
    try:
        lecturer_id = get_current_lecturer(request)
        return [dict(r) for r in get_office_hours(lecturer_id)]
    except ValueError as e:
        return auth_error(e)


@router.post("/office_hours")
async def api_create_office_hour(request: Request):
    try:
        lecturer_id = get_current_lecturer(request)
        body = await request.json()
        row = create_office_hour(
            lecturer_id=lecturer_id,
            date=body["date"],
            hour=body["hour"],
            location=body["location"]
        )
        return dict(row)
    except ValueError as e:
        return JSONResponse(status_code=400, content={"error": str(e)})


@router.delete("/office_hours/{office_hour_id}")
async def api_delete_office_hour(office_hour_id: int, request: Request):
    try:
        get_current_lecturer(request) 
        
        deleted = delete_office_hour(office_hour_id)
        if not deleted:
            return JSONResponse(status_code=404, content={"error": "Office hour not found"})
        return {"deleted": office_hour_id}
    except ValueError as e:
        return auth_error(e)