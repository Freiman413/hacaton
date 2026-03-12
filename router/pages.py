import sqlite3
from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates

from data_base.auth import login, decode_token
from data_base.db import get_db_path
from data_base.register import complete_student_registration
from data_base.query import get_lecturers_with_courses

router = APIRouter()
templates = Jinja2Templates(directory="templates")

def get_db():
    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row
    return conn

def get_current_user(request):
    token = request.cookies.get("access_token")
    if not token:
        return None
    try:
        payload = decode_token(token)
    except ValueError:
        return None

    role = payload.get("role")
    sub  = payload.get("sub")

    if role == "master":
        return {"first_name": "Master", "last_name": "", "full_name": "Master",
                "email": "", "role": "master", "department": "", "courses": []}

    conn = get_db()
    try:
        if role == "lecturer":
            row = conn.execute("SELECT * FROM Lecturers WHERE lecturer_id = ?", (sub,)).fetchone()
            if not row:
                return None
            return {
                "first_name": row["first_name"],
                "last_name":  row["last_name"],
                "full_name":  row["first_name"] + " " + row["last_name"],
                "email":      row["email"],
                "role":       "lecturer",
                "department": row["department"],
                "courses":    [],
            }

        if role == "student":
            row = conn.execute("SELECT * FROM Students WHERE student_id = ?", (sub,)).fetchone()
            if not row:
                return None
            return {
                "first_name": row["first_name"],
                "last_name":  row["last_name"],
                "full_name":  row["first_name"] + " " + row["last_name"],
                "email":      row["email"],
                "student_id": row["student_id"],
                "role":       "student",
                "department": "",
                "courses":    [],
            }
    finally:
        conn.close()

    return None

@router.get("/", response_class=HTMLResponse)
async def landing(request: Request):
    try:
        return templates.TemplateResponse("landing.html", {"request": request})
    except Exception as e:
        print(f"Error in landing: {e}")
        return HTMLResponse(content="Internal Server Error", status_code=500)

@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    try:
        return templates.TemplateResponse("login.html", {"request": request})
    except Exception as e:
        print(f"Error in login_page: {e}")
        return HTMLResponse(content="Internal Server Error", status_code=500)

@router.post("/login", response_class=HTMLResponse)
async def login_post(request: Request, email: str = Form(...), password: str = Form(...)):
    try:
        result = login(email, password)
        role = result["role"]
        token = result["token"]

        if role == "master":
            redirect_url = "/admin/create-lecturer"
        elif role == "lecturer":
            redirect_url = "/lecturer"
        else:
            redirect_url = "/dashboard"

        response = RedirectResponse(url=redirect_url, status_code=303)
        response.set_cookie(key="access_token", value=token, httponly=True, samesite="lax", max_age=86400)
        return response
    except ValueError as exc:
        return templates.TemplateResponse("login.html", {"request": request, "error": str(exc)}, status_code=400)
    except Exception as e:
        print(f"Error in login_post: {e}")
        return HTMLResponse(content="Internal Server Error", status_code=500)

@router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    try:
        return templates.TemplateResponse("register.html", {"request": request, "form": {}})
    except Exception as e:
        print(f"Error in register_page: {e}")
        return HTMLResponse(content="Internal Server Error", status_code=500)

@router.post("/register", response_class=HTMLResponse)
async def register_post(
    request: Request,
    email:      str = Form(...),
    first_name: str = Form(...),
    last_name:  str = Form(...),
    age:        int = Form(...),
    phone:      str = Form(...),
    password:   str = Form(...),
    password2:  str = Form(...),
):
    form_data = {
        "email":      email,
        "first_name": first_name,
        "last_name":  last_name,
        "age":        age,
        "phone":      phone,
    }

    try:
        complete_student_registration(email, first_name, last_name, age, phone, password, password2)
        return RedirectResponse(url="/login", status_code=303)
    except ValueError as e:
        error_code = str(e)
        if error_code not in ("not_approved", "exists"):
            error_code = "generic"
        return templates.TemplateResponse("register.html", {"request": request, "error": error_code, "form": form_data}, status_code=400)
    except Exception as e:
        print(f"Error in register_post: {e}")
        return HTMLResponse(content="Internal Server Error", status_code=500)

@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    try:
        current_user = get_current_user(request)
        if not current_user:
            return RedirectResponse(url="/login", status_code=303)
        return templates.TemplateResponse("dashboard.html", {"request": request, "current_user": current_user})
    except Exception as e:
        print(f"Error in dashboard: {e}")
        return HTMLResponse(content="Internal Server Error", status_code=500)

@router.get("/lecturer", response_class=HTMLResponse)
async def lecturer_page(request: Request):
    try:
        current_user = get_current_user(request)
        if not current_user or current_user.get("role") not in ("lecturer", "master"):
            return Response(status_code=204)
        return templates.TemplateResponse("lecturer_dashboard.html", {"request": request, "current_user": current_user})
    except Exception as e:
        print(f"Error in lecturer_page: {e}")
        return Response(status_code=204)

@router.get("/admin/create-lecturer", response_class=HTMLResponse)
async def admin_page(request: Request):
    try:
        current_user = get_current_user(request)
        if not current_user or current_user.get("role") != "master":
            return Response(status_code=204)
        lecturers = get_lecturers_with_courses()
        return templates.TemplateResponse(
            "admin.html", 
            {
                "request": request,
                "current_user": current_user,
                "lecturers": [dict(r) for r in lecturers]
            }
        )
    except Exception as e:
        print(f"Error in admin_page: {e}")
        return Response(status_code=204)

@router.get("/logout")
async def logout():
    try:
        response = RedirectResponse(url="/", status_code=303)
        response.delete_cookie("access_token")
        return response
    except Exception as e:
        print(f"Error in logout: {e}")
        return HTMLResponse(content="Internal Server Error", status_code=500)