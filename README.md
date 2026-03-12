# Smart Campus Assistant

An AI-powered academic assistant for university students. Students interact through a chat interface to ask questions about their schedule, grades, exams, and office hours. The system uses a two-stage Claude pipeline: a classifier that routes and translates the question, and a responder that answers strictly from database records.

## Tech Stack

- **Backend:** Python 3.14, FastAPI, Uvicorn
- **Database:** SQLite via raw `sqlite3`
- **AI:** Anthropic Claude Sonnet
- **Auth:** JWT via `python-jose`, stored in HTTP-only cookies
- **Frontend:** Jinja2 templates, vanilla JS, CSS custom properties with dark/light theme support
- **Testing:** Pytest, `unittest.mock`

## Project Structure

```
project/
├── main.py
├── requirements.txt
├── .env
├── .gitignore
├── README.md
│
├── ai_server/
│   ├── __init__.py
│   ├── main_server.py
│   ├── utils_ai_server.py
│   ├── test_main.py
│   └── prompts/
│       ├── __init__.py
│       └── prompts_final.py
│
├── data_base/
│   ├── __init__.py
│   ├── db.py
│   ├── query.py
│   ├── crud.py
│   ├── ai_query.py
│   ├── auth.py
│   ├── register.py
│   └── validators.py
│
├── router/
│   ├── __init__.py
│   ├── pages.py
│   ├── admin.py
│   └── lecturer_dashboard.py
│
├── static/
│   └── style.css
│
└── templates/
    ├── base.html
    ├── landing.html
    ├── login.html
    ├── register.html
    ├── dashboard.html
    ├── admin.html
    └── lecturer_dashboard.html
```

## How It Works

Every student message sent from `dashboard.html` hits `POST /api/chat` in `main_server.py`. The request goes through an 8-step pipeline:

1. **Auth** — JWT cookie is decoded and the student ID is extracted
2. **Context** — Student name and active courses are fetched from the database
3. **Classify** — The message is sent to Claude with `CLASSIFIER_SYSTEM_PROMPT`. Returns a JSON object containing the detected language, English translation, category (`exams`, `grades`, `schedule`, `office_hours`, `rooms`, `general`), and edge case flag
4. **Edge case check** — If the edge case is `off_topic`, `empty_input`, or `security_risk`, a reply is returned immediately. No database query runs and no second Claude call is made
5. **Course filter** — If the student is enrolled in multiple courses, the relevant one is matched from the translated question text
6. **Data fetch** — The correct database query runs based on the category. For grades questions, target-grade calculations are pre-computed in Python and appended to the data block before it reaches Claude
7. **Respond** — The data block is injected into `CLAUDE_SYSTEM_PROMPT_V1` and sent to Claude. Claude answers strictly from what is in the data block and responds in the student's detected language. If the data block does not contain enough information, Claude returns the keyword `INSUFFICIENT_DATA`
8. **Fallback** — If `INSUFFICIENT_DATA` appears in the reply, it is replaced with a safe message directing the student to their lecturer

### Schedule Builder

When the classifier detects `schedule_builder` as the edge case, the system switches into an interactive multi-turn mode. Claude receives the student's full weekly schedule (lessons and exams combined), with conflicts already auto-resolved (exams always override overlapping lessons). Claude guides the student through any remaining conflicts and allows them to add personal events.

Personal events are returned by Claude as pipe-delimited commands in the format `ADD_EVENT|date|hour|duration_minutes|description`. These are parsed server-side and added to the schedule state. The full schedule state is passed back and forth through the frontend on every turn since the server is stateless. The session ends when Claude returns `SCHEDULE_COMPLETE` or `EXIT_SCHEDULE`.

## Database

The database is initialized automatically on first run by `db.py` if the `.db` file does not exist.

| Table | Description |
|---|---|
| `Students` | Student accounts: name, email, age, phone, password hash |
| `Lecturers` | Lecturer accounts: name, email, department, password hash |
| `Courses` | Courses with start and end dates, year, degree type, assigned lecturer |
| `Student_Courses` | Enrollment: many-to-many between students and courses |
| `Lessons` | Individual class sessions: date, hour, building, room |
| `Exams` | Exams with weight percentage, attempt A or B, duration, building, room |
| `Grades` | Student grades per exam, linked to both student and exam |
| `Office_Hours` | Lecturer availability: date, hour, location |

## Roles and Permissions

The system has three roles managed through JWT claims. Each role is routed to a different interface after login.

**Master** is defined in `.env` and has no database record. The master account can create lecturer accounts and assign a course to each one through the admin interface at `/admin/create-lecturer`.

**Lecturers** are created by master. After logging in at `/lecturer`, a lecturer can manage everything related to their course: add and delete lessons, create and delete exams, enroll students by adding their email, and enter or update grades per student per exam. All CRUD operations go through the REST API in `lecturer_dashboard.py` under the `/api/` prefix. Every endpoint verifies the JWT and confirms the resource belongs to the lecturer's course before performing any write.

**Students** register at `/register`. Registration only completes if the student's email was already added to the database by their lecturer. The registration form fills in the remaining fields (name, age, phone, password) and links the account to the pre-existing record.

## API Endpoints

| Method | Path | Role | Description |
|---|---|---|---|
| POST | `/api/chat` | Student | Main AI chat endpoint |
| GET | `/api/lessons` | Lecturer | Get all lessons for course |
| POST | `/api/lessons` | Lecturer | Add a lesson |
| DELETE | `/api/lessons/{id}` | Lecturer | Delete a lesson |
| GET | `/api/exams` | Lecturer | Get all exams for course |
| POST | `/api/exams` | Lecturer | Add an exam |
| DELETE | `/api/exams/{id}` | Lecturer | Delete an exam |
| GET | `/api/grades` | Lecturer | Get all grades for course |
| POST | `/api/grades` | Lecturer | Add a grade |
| PUT | `/api/grades/{id}` | Lecturer | Update a grade |
| DELETE | `/api/grades/{id}` | Lecturer | Delete a grade |
| GET | `/api/students` | Lecturer | Get enrolled students |
| POST | `/api/students` | Lecturer | Enroll a student |
| GET | `/api/office_hours` | Lecturer | Get all office hours |
| POST | `/api/office_hours` | Lecturer | Add an office hour slot |
| DELETE | `/api/office_hours/{id}` | Lecturer | Delete an office hour slot |
| POST | `/api/admin/create-lecturer` | Master | Create lecturer and course |

## Setup

```bash
pip install -r requirements.txt
```

Create a `.env` file in the project root:

```env
APP_NAME=main:app
HOST=127.0.0.1
PORT=8000
DEBUG=true

DB_name=app.db

SECRET_KEY=your-secret-key
ALGORITHM=HS256

MASTER_EMAIL=your-master-email
MASTER_PASSWORD=your-master-password

API_KEY=your-anthropic-api-key
AI_MODEL=claude-sonnet-4-20250514
```

```bash
uvicorn main:app --reload
```

## Tests

```bash
pytest ai_server/test_main.py -v
```

5 unit tests covering Hebrew detection, grade average calculation, edge case blocking, and the `/api/chat` endpoint with a mocked Anthropic client and mocked database context.