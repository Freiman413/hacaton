from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from data_base.crud import create_lecturer_with_course
from data_base.auth import get_role_from_request

router = APIRouter()

@router.post("/api/admin/create-lecturer")
async def api_create_lecturer(request: Request):
    try:
        role = get_role_from_request(request)
        if role != "master":
            return JSONResponse(status_code=403, content={"error": "Not authorized"})
    except ValueError as e:
        return JSONResponse(status_code=401, content={"error": str(e)})

    body = await request.json()
    try:
        result = create_lecturer_with_course(
            first_name=body["first_name"],
            last_name=body["last_name"],
            email=body["email"],
            password=body["password"],
            department=body["department"],
            course_name=body["course_name"],
            start_date=body["start_date"],
            end_date=body["end_date"],
            course_year=int(body["course_year"]),
            degree_type=body["degree_type"],
        )
        return result
    except ValueError as e:
        return JSONResponse(status_code=400, content={"error": str(e)})