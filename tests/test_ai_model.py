"""Tests for local model communication, JSON parsing, and error handling."""
import pytest
from unittest.mock import patch, MagicMock
from ai.local_model import (
    LocalModelService,
    OllamaServiceError,
    ModelNotFoundError,
    ModelResponseError
)

def test_json_repair_clean():
    raw = '{"summary": "All good", "tasks": []}'
    parsed = LocalModelService._repair_and_parse_json(raw)
    assert parsed == {"summary": "All good", "tasks": []}

def test_json_repair_markdown_code_block():
    raw = """Here is the extracted information:
```json
{
  "summary": "Quarterly review",
  "key_points": ["Point 1", "Point 2"],
  "tasks": []
}
```
Let me know if you need anything else!"""
    parsed = LocalModelService._repair_and_parse_json(raw)
    assert parsed is not None
    assert parsed["summary"] == "Quarterly review"
    assert len(parsed["key_points"]) == 2

def test_json_repair_trailing_commas():
    raw = """{
        "summary": "Trailing comma test",
        "key_points": [
            "Point 1",
            "Point 2",
        ],
        "tasks": [],
    }"""
    parsed = LocalModelService._repair_and_parse_json(raw)
    assert parsed is not None
    assert parsed["summary"] == "Trailing comma test"

def test_json_repair_invalid_non_json():
    raw = "I am sorry, but I cannot process this document."
    parsed = LocalModelService._repair_and_parse_json(raw)
    assert parsed is None

@patch("requests.get")
def test_status_connected(mock_get):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"models": [{"name": "qwen2.5:3b"}]}
    mock_get.return_value = mock_resp

    service = LocalModelService(model_name="qwen2.5:3b")
    status = service.check_status()
    assert status["state"] == "connected"
    assert status["is_running"] is True
    assert status["model_available"] is True

@patch("requests.get")
def test_status_model_missing(mock_get):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"models": [{"name": "llama3.2:latest"}]}
    mock_get.return_value = mock_resp

    service = LocalModelService(model_name="qwen2.5:3b")
    status = service.check_status()
    assert status["state"] == "model_missing"
    assert status["model_available"] is False
    assert "ollama pull qwen2.5:3b" in status["install_command"]

@patch("requests.get")
def test_status_unavailable(mock_get):
    import requests
    mock_get.side_effect = requests.RequestException("Connection refused")

    service = LocalModelService(model_name="qwen2.5:3b")
    status = service.check_status()
    assert status["state"] == "unavailable"
    assert status["is_running"] is False

@patch("requests.post")
@patch("requests.get")
def test_generate_structured_success(mock_get, mock_post):
    mock_get_resp = MagicMock()
    mock_get_resp.status_code = 200
    mock_get_resp.json.return_value = {"models": [{"name": "qwen2.5:3b"}]}
    mock_get.return_value = mock_get_resp

    mock_post_resp = MagicMock()
    mock_post_resp.status_code = 200
    mock_post_resp.json.return_value = {
        "response": '{"summary": "Test", "tasks": [{"title": "Action", "priority": "high"}]}'
    }
    mock_post.return_value = mock_post_resp

    service = LocalModelService(model_name="qwen2.5:3b")
    result = service.generate_structured("Analyze this text")
    assert result["summary"] == "Test"
    assert len(result["tasks"]) == 1
