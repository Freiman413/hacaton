
from data_base.ai_query import (get_student_name, get_student_courses, get_exams_by_course, get_rooms_by_course, get_office_hours_by_course, get_grades_by_course, get_schedule_by_student)
from data_base.auth import get_student_id_from_request


def get_student_context(request):
    student_id = get_student_id_from_request(request)
    name = get_student_name(student_id)
    courses = get_student_courses(student_id)
    return {
        "student_id": student_id,
        "name": name,
        "course_ids": [c["course_id"] for c in courses],
        "course_names": [c["course_name"] for c in courses],
        "courses": courses
    }
    

def validate_weights(grades_data: list):
    total = sum(e["weight_percentage"] for e in grades_data)
    return round(total) == 100

def filter_best_attempt(grades_data: list):
    groups = {}
    for exam in grades_data:
        group = exam["exam_group"]
        if group not in groups:
            groups[group] = exam
        else:
            existing = groups[group]
            if exam["exam_attempt"] == "B" and exam["grade_received"] is not None:
                groups[group] = exam
            elif existing["exam_attempt"] == "B" and existing["grade_received"] is not None:
                pass
            elif exam["exam_attempt"] == "A":
                groups[group] = exam
    return list(groups.values())


def split_done_vs_remaining(grades_data: list):
    done = [e for e in grades_data if e["grade_received"] is not None]
    remaining = [e for e in grades_data if e["grade_received"] is None]
    return done, remaining


def calculate_current_average(done: list):
    if not done:
        return 0.0
    total_weight = sum(e["weight_percentage"] for e in done)
    if total_weight == 0:
        return 0.0
    weighted_sum = sum(e["grade_received"] * e["weight_percentage"] for e in done)
    return weighted_sum / total_weight


def calculate_required_score(done: list, remaining: list, target: float):
    remaining_weight = sum(e["weight_percentage"] for e in remaining)
    done_weight = sum(e["weight_percentage"] for e in done)

    if target < 1:
        target = target * 100

    if not remaining:
        current = calculate_current_average(done)
        return {
            "possible": False,
            "message": f"No remaining exams. Current average: {round(current, 2)}"
        }

    weighted_done = sum(e["grade_received"] * e["weight_percentage"] for e in done)
    required = (target * 100 - weighted_done) / remaining_weight
    max_possible = (weighted_done + remaining_weight * 100) / 100

    if required > 100:
        return {
            "possible": False,
            "max_possible": round(max_possible, 2),
            "message": f"Target is mathematically impossible. Maximum possible grade: {round(max_possible, 2)}"
        }

    return {
        "possible": True,
        "required_score": round(required, 2),
        "remaining_weight": remaining_weight,
        "current_weighted": round(weighted_done / done_weight, 2) if done_weight else 0
    }


def calculate_target_grade(grades_data: list, target: float):
    if not validate_weights(grades_data):
        return {
            "possible": False,
            "message": "Exam weights do not sum to 100. Cannot calculate target grade."
        }

    filtered = filter_best_attempt(grades_data)
    done, remaining = split_done_vs_remaining(filtered)
    current_avg = calculate_current_average(done)
    result = calculate_required_score(done, remaining, target)

    return {
        "target": target,
        "current_average": round(current_avg, 2),
        "exams_done": len(done),
        "exams_remaining": len(remaining),
        **result
    }


def check_edge_case(edge_case, gemini_message=""):
    if edge_case in ("off_topic", "empty_input", "security_risk"):
        if gemini_message:
            return gemini_message
        if edge_case == "off_topic":
            return "I can only help with campus-related questions like exams, schedules, grades, office hours, and rooms."
        if edge_case == "empty_input":
            return "I didn't receive a valid question. Please try again."
        if edge_case == "security_risk":
            return "I can only show your own grades and information."
    return None


def match_course(translated_text, courses):
    translated_lower = translated_text.lower()
    matched = []
    for course in courses:
        if course["course_name"].lower() in translated_lower:
            matched.append(course)
    return matched


def filter_courses(translated_text, courses, edge_case):
    if len(courses) == 1:
        return courses
    
    matched = match_course(translated_text, courses)
    if matched:
        return matched

    if edge_case == "ambiguous_course":
        return courses

    return courses


def fetch_data(category, student_id, courses):
    blocks = []

    if category == "schedule":
        try:
            schedule = get_schedule_by_student(student_id)
            blocks.append(f"Weekly Schedule:\n{schedule}")
        except ValueError as e:
            blocks.append(f"Schedule: {e}")

    elif category == "exams":
        for course in courses:
            try:
                exams = get_exams_by_course(course["course_id"])
                blocks.append(f"Exams for {course['course_name']}:\n{exams}")
            except ValueError as e:
                blocks.append(f"Exams for {course['course_name']}: {e}")

    elif category == "grades":
        for course in courses:
            try:
                grades = get_grades_by_course(course["course_id"], student_id)
                blocks.append(f"Grades for {course['course_name']}:\n{grades}")
                if isinstance(grades, list):
                    for target in [56, 70, 80, 90]:
                        result = calculate_target_grade(grades, target)
                        blocks.append(f"Target {target} for {course['course_name']}: {result}")
            except ValueError as e:
                blocks.append(f"Grades for {course['course_name']}: {e}")

    elif category == "office_hours":
        for course in courses:
            try:
                info = get_office_hours_by_course(course["course_id"])
                blocks.append(f"Office hours for {course['course_name']}:\n{info}")
            except ValueError as e:
                blocks.append(f"Office hours for {course['course_name']}: {e}")

    elif category == "rooms":
        for course in courses:
            try:
                rooms = get_rooms_by_course(course["course_id"])
                blocks.append(f"Rooms for {course['course_name']}:\n{rooms}")
            except ValueError as e:
                blocks.append(f"Rooms for {course['course_name']}: {e}")

    else:
        blocks.append("I wasn't sure what you meant. Could you try asking again more specifically?")

    return "\n\n".join(blocks) if blocks else "No data was found for your question. Try asking about a specific course by name."
    



def build_system_prompt(context, gemini_result, data_block, prompt_template):
    return prompt_template.format(
        name=context["name"],
        student_id=context["student_id"],
        courses=", ".join(context["course_names"]),
        category=gemini_result["category"],
        translated_text=gemini_result["translated_text"],
        original_language=gemini_result["original_language"],
        edge_case=gemini_result["edge_case"],
        data_block=data_block,
        respond_in_language=gemini_result["respond_in_language"],
    )


def parse_time_to_minutes(hour_val):
    hour_str = str(hour_val).strip()
    if ":" in hour_str:
        parts = hour_str.split(":")
        return int(parts[0]) * 60 + int(parts[1])
    return int(hour_str) * 60


def get_weekly_schedule(student_id):
    schedule = get_schedule_by_student(student_id)
    lessons = schedule.get("lessons", [])
    exams = schedule.get("exams", [])
    all_items = []

    if isinstance(lessons, list):
        for lesson in lessons:
            all_items.append({
                "type": "lesson",
                "course_name": lesson.get("course_name", ""),
                "date": lesson.get("date", ""),
                "hour": lesson.get("hour", ""),
                "building": lesson.get("building_number", ""),
                "room": lesson.get("room_number", ""),
                "duration": 60,
            })

    if isinstance(exams, list):
        for exam in exams:
            all_items.append({
                "type": "exam",
                "course_name": exam.get("course_name", ""),
                "date": exam.get("date", ""),
                "hour": exam.get("hour", ""),
                "building": exam.get("building_number", ""),
                "room": exam.get("room_number", ""),
                "duration": exam.get("exam_duration", 120),
            })

    return all_items


def auto_resolve_exams(items):
    exams = [i for i in items if i["type"] == "exam"]
    lessons = [i for i in items if i["type"] != "exam"]
    keep = []

    for lesson in lessons:
        dominated = False
        lesson_start = parse_time_to_minutes(lesson["hour"])
        lesson_end = lesson_start + lesson.get("duration", 60)

        for exam in exams:
            if exam["date"] != lesson["date"]:
                continue
            exam_start = parse_time_to_minutes(exam["hour"])
            exam_end = exam_start + exam.get("duration", 120)

            if lesson_start < exam_end and lesson_end > exam_start:
                dominated = True
                break

        if not dominated:
            keep.append(lesson)

    return exams + keep


def find_conflicts(items):
    conflicts = []
    for i in range(len(items)):
        for j in range(i + 1, len(items)):
            if items[i]["date"] != items[j]["date"]:
                continue

            start_a = parse_time_to_minutes(items[i]["hour"])
            end_a = start_a + items[i].get("duration", 60)
            start_b = parse_time_to_minutes(items[j]["hour"])
            end_b = start_b + items[j].get("duration", 60)

            if start_a < end_b and start_b < end_a:
                conflicts.append({
                    "date": items[i]["date"],
                    "hour_a": items[i]["hour"],
                    "hour_b": items[j]["hour"],
                    "course_a": items[i]["course_name"],
                    "course_b": items[j]["course_name"],
                })
    return conflicts


def set_dominant_course(items, conflicts, dominant_name):
    dominant_lower = dominant_name.lower()
    resolved = []
    remove_slots = set()

    for conflict in conflicts:
        if conflict["course_a"].lower() == dominant_lower:
            remove_slots.add((conflict["date"], str(conflict["hour_b"]), conflict["course_b"]))
            resolved.append(conflict)
        elif conflict["course_b"].lower() == dominant_lower:
            remove_slots.add((conflict["date"], str(conflict["hour_a"]), conflict["course_a"]))
            resolved.append(conflict)

    filtered = []
    for item in items:
        key = (item["date"], str(item["hour"]), item["course_name"])
        if key not in remove_slots:
            filtered.append(item)

    remaining_conflicts = [c for c in conflicts if c not in resolved]
    return filtered, remaining_conflicts

def resolve_date(raw_date):
    """Convert day names (English) to ISO date for the upcoming week."""
    raw = raw_date.strip()
    if len(raw) >= 10 and raw[4] == '-' and raw[7] == '-':
        return raw

    day_map = {
        "sunday": 6, "monday": 0, "tuesday": 1,
        "wednesday": 2, "thursday": 3, "friday": 4, "saturday": 5,
    }

    key = raw.lower()
    if key in day_map:
        from datetime import date, timedelta
        today = date.today()
        target = day_map[key]
        current = today.weekday()
        diff = (target - current) % 7
        return (today + timedelta(days=diff)).isoformat()

    return raw

def add_personal_event(items, date, hour, description, duration=60):
    items.append({
        "type": "personal",
        "course_name": description,
        "date": resolve_date(date),
        "hour": hour,
        "building": "",
        "room": "",
        "duration": duration,
    })
    return items


def build_schedule_data(items, conflicts):
    return {
        "items": items,
        "conflicts": conflicts,
        "days": sorted(set(i["date"] for i in items)),
    }