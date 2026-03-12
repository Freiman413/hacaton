import json
import pytest
import sys
import os
from unittest.mock import patch, MagicMock
from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from ai_server.main_server import router, detect_hebrew
from ai_server.utils_ai_server import calculate_current_average, check_edge_case

app = FastAPI()
app.include_router(router)
client = TestClient(app)

MOCK_STUDENT_CONTEXT = {
    "student_id": 1,
    "name": "Noam",
    "course_ids": [101],
    "course_names": ["Python"],
    "courses": [{"course_id": 101, "course_name": "Python"}]
}

MOCK_CLASSIFIER_RESPONSE = json.dumps({
    "original_language": "english",
    "translated_text": "What are my grades?",
    "category": "grades",
    "edge_case": "none",
    "respond_in_language": "english",
    "edge_case_message": ""
})

def _make_mock_anthropic_response(text: str) -> MagicMock:
    mock_content = MagicMock()
    mock_content.text = text
    mock_response = MagicMock()
    mock_response.content = [mock_content]
    return mock_response

def test_detect_hebrew():
    assert detect_hebrew("שלום") is True
    assert detect_hebrew("Hello") is False

def test_calculate_average():
    sample_grades = [
        {"grade_received": 90, "weight_percentage": 50},
        {"grade_received": 70, "weight_percentage": 50},
    ]
    result = calculate_current_average(sample_grades)
    assert result == 80.0

def test_calculate_average_empty():
    result = calculate_current_average([])
    assert result == 0.0

def test_check_edge_case_off_topic():
    result = check_edge_case("off_topic", "")
    assert result is not None
    assert "campus-related" in result.lower()

def test_check_edge_case_none():
    result = check_edge_case("none", "")
    assert result is None

@patch("ai_server.main_server.get_student_context", return_value=MOCK_STUDENT_CONTEXT)
@patch("ai_server.main_server.client")
@patch("ai_server.main_server.fetch_data", return_value="Mocked Grade Data")
def test_chat_endpoint(mock_fetch, mock_anthropic_client, mock_get_student_context):

    mock_anthropic_client.messages.create.return_value = _make_mock_anthropic_response(
        MOCK_CLASSIFIER_RESPONSE
    )
    
    payload = {"messages": [{"role": "user", "content": "Hello"}]}
    response = client.post("/api/chat", json=payload)
    
    assert response.status_code == 200
    data = response.json()
    assert "reply" in data