from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
import anthropic
import json
import os
from dotenv import load_dotenv
from datetime import date, timedelta

from .utils_ai_server import (
    get_student_context, check_edge_case, filter_courses,
    fetch_data, build_system_prompt,
    get_weekly_schedule, auto_resolve_exams, find_conflicts,
    set_dominant_course, add_personal_event, build_schedule_data,
    match_course
)
from .prompts import (
    CLASSIFIER_SYSTEM_PROMPT, TRANSLATE_ONLY_PROMPT,
    CLAUDE_SYSTEM_PROMPT_V1, CLAUDE_SCHEDULE_PROMPT
)

load_dotenv()

router = APIRouter()
client = anthropic.Anthropic(api_key=os.getenv("API_KEY"))
MODEL = os.getenv("AI_MODEL", "claude-sonnet-4-20250514")

FALLBACK_KEYWORD = "INSUFFICIENT_DATA"
FALLBACK_MESSAGE = (
    "I couldn't find enough information to answer your question accurately. "
    "Please contact your lecturer or the department office for assistance."
)


def detect_hebrew(text):
    for char in text:
        if '\u0590' <= char <= '\u05FF':
            return True
    return False


def call_classifier(user_message):
    try:
        response = client.messages.create(
            model=MODEL,
            max_tokens=300,
            system=CLASSIFIER_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}],
        )
        raw = response.content[0].text.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        result = json.loads(raw)
        return result
    except Exception as e:
        print(f"CLASSIFIER ERROR: {e}")
        lang = "hebrew" if detect_hebrew(user_message) else "english"
        return {
            "original_language": lang,
            "translated_text": user_message,
            "category": "general",
            "edge_case": "none",
            "respond_in_language": lang,
            "edge_case_message": ""
        }


def call_translate_only(user_message):
    try:
        response = client.messages.create(
            model=MODEL,
            max_tokens=200,
            system=TRANSLATE_ONLY_PROMPT,
            messages=[{"role": "user", "content": user_message}],
        )
        raw = response.content[0].text.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        result = json.loads(raw)
        return result
    except Exception as e:
        print(f"TRANSLATE ERROR: {e}")
        lang = "hebrew" if detect_hebrew(user_message) else "english"
        return {
            "original_language": lang,
            "translated_text": user_message,
            "respond_in_language": lang
        }


@router.post("/api/chat")
async def chat(request: Request):
    try:
        body = await request.json()
        messages = body.get("messages", [])
        if not messages:
            return JSONResponse(status_code=400, content={"error": "No messages provided."})
        last_message = messages[-1]["content"]

        schedule_mode = body.get("schedule_mode", False)
        schedule_items = body.get("schedule_items", None)
        schedule_conflicts = body.get("schedule_conflicts", None)
        dominant_course = body.get("dominant_course", "none")

        student_context = get_student_context(request)
        student_id = student_context["student_id"]
        courses = student_context["courses"]

        if schedule_mode:
            translate_result = call_translate_only(last_message)

            if schedule_items is None:
                items = get_weekly_schedule(student_id)
                items = auto_resolve_exams(items)
                conflicts = find_conflicts(items)
            else:
                items = schedule_items
                conflicts = schedule_conflicts or []

            translated = translate_result["translated_text"]
            matched = match_course(translated, courses)
            if matched and conflicts:
                items, conflicts = set_dominant_course(items, conflicts, matched[0]["course_name"])
                dominant_course = matched[0]["course_name"]

            schedule_data = build_schedule_data(items, conflicts)

            system = CLAUDE_SCHEDULE_PROMPT.format(
                name=student_context["name"],
                student_id=student_id,
                courses=", ".join(student_context["course_names"]),
                original_language=translate_result["original_language"],
                respond_in_language=translate_result["respond_in_language"],
                schedule_data=json.dumps(schedule_data["items"], indent=2),
                conflicts_data=json.dumps(conflicts, indent=2),
                dominant_course=dominant_course,
            )

            claude_messages = []
            for msg in messages:
                if msg["role"] in ("user", "assistant"):
                    claude_messages.append({"role": msg["role"], "content": msg["content"]})

            response = client.messages.create(
                model=MODEL,
                max_tokens=1024,
                system=system,
                messages=claude_messages,
            )

            reply = response.content[0].text
            if "ADD_EVENT|" in reply:
                lines = reply.split("\n")
                clean_lines = []
                for line in lines:
                    if line.strip().startswith("ADD_EVENT|"):
                        parts = line.strip().split("|")
                        if len(parts) == 5:
                            try:
                                duration = int(parts[3])
                            except ValueError:
                                duration = 60
                            items = add_personal_event(items, parts[1], parts[2], parts[4], duration)
                        elif len(parts) == 4:
                            items = add_personal_event(items, parts[1], parts[2], parts[3])
                    else:
                        clean_lines.append(line)
                reply = "\n".join(clean_lines).strip()
                conflicts = find_conflicts(items)
                schedule_data = build_schedule_data(items, conflicts)
            if "EXIT_SCHEDULE" in reply:
                clean = reply.replace("EXIT_SCHEDULE", "").strip()
                return {
                    "reply": clean if clean else "Back to regular chat. How can I help?",
                    "category": "exit_schedule",
                    "schedule_mode": False,
                }

            if "SCHEDULE_COMPLETE" in reply:
                clean = reply.replace("SCHEDULE_COMPLETE", "").strip()
                return {
                    "reply": clean if clean else "Your schedule is ready!",
                    "category": "schedule_complete",
                    "schedule_mode": False,
                    "schedule_items": items,
                    "schedule_days": schedule_data["days"],
                }

            return {
                "reply": reply,
                "category": "schedule",
                "schedule_mode": True,
                "schedule_items": items,
                "schedule_conflicts": conflicts,
                "dominant_course": dominant_course,
            }

        classifier_result = call_classifier(last_message)
        print(f"CLASSIFIER: {classifier_result}")

        edge_message = check_edge_case(
            classifier_result["edge_case"],
            classifier_result.get("edge_case_message", "")
        )
        if edge_message:
            return {"reply": edge_message, "category": "blocked"}

        if classifier_result["category"] == "schedule" and classifier_result["edge_case"] == "schedule_builder":
            items = get_weekly_schedule(student_id)
            items = auto_resolve_exams(items)
            conflicts = find_conflicts(items)
            schedule_data = build_schedule_data(items, conflicts)

            system = CLAUDE_SCHEDULE_PROMPT.format(
                name=student_context["name"],
                student_id=student_id,
                courses=", ".join(student_context["course_names"]),
                original_language=classifier_result["original_language"],
                respond_in_language=classifier_result["respond_in_language"],
                schedule_data=json.dumps(schedule_data["items"], indent=2),
                conflicts_data=json.dumps(conflicts, indent=2),
                dominant_course="none",
            )

            claude_messages = []
            for msg in messages:
                if msg["role"] in ("user", "assistant"):
                    claude_messages.append({"role": msg["role"], "content": msg["content"]})

            response = client.messages.create(
                model=MODEL,
                max_tokens=1024,
                system=system,
                messages=claude_messages,
            )

            reply = response.content[0].text

            return {
                "reply": reply,
                "category": "schedule",
                "schedule_mode": True,
                "schedule_items": items,
                "schedule_conflicts": conflicts,
                "dominant_course": "none",
            }

        courses_to_fetch = filter_courses(
            classifier_result["translated_text"],
            courses,
            classifier_result["edge_case"]
        )

        data_block = fetch_data(
            classifier_result["category"],
            student_id,
            courses_to_fetch
        )

        system = build_system_prompt(
            student_context,
            classifier_result,
            data_block,
            CLAUDE_SYSTEM_PROMPT_V1
        )

        claude_messages = []
        for msg in messages:
            if msg["role"] in ("user", "assistant"):
                claude_messages.append({"role": msg["role"], "content": msg["content"]})

        response = client.messages.create(
            model=MODEL,
            max_tokens=1024,
            system=system,
            messages=claude_messages,
        )

        reply = response.content[0].text

        if FALLBACK_KEYWORD in reply:
            reply = FALLBACK_MESSAGE

        return {"reply": reply, "category": classifier_result["category"]}

    except ValueError as e:
        return JSONResponse(status_code=401, content={"error": str(e)})
    except anthropic.APIError:
        return JSONResponse(status_code=502, content={"error": "AI service is currently unavailable. Please try again."})
    except Exception as e:
        print(f"CHAT ERROR: {e}")
        return JSONResponse(status_code=500, content={"error": "Something went wrong. Please try again."})