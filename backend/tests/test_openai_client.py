import httpx
import pytest

from app.services.openai_client import (
    OpenAIGenerationError,
    extract_response_text,
    parse_answer_text,
)


def test_parse_openai_json_answer():
    draft = parse_answer_text(
        '{"answer":"Evidence supports volume overload [1].","confidence":"high","limits":[]}'
    )

    assert draft.answer == "Evidence supports volume overload [1]."
    assert draft.confidence == "high"
    assert draft.limits == []


def test_parse_openai_unstructured_answer():
    draft = parse_answer_text("The source notes are incomplete.")

    assert draft.answer == "The source notes are incomplete."
    assert draft.confidence == "medium"
    assert draft.limits == ["Model returned unstructured text; verify citations manually."]


def test_extract_response_text_from_output_items():
    payload = {
        "output": [
            {
                "content": [
                    {
                        "type": "output_text",
                        "text": '{"answer":"Grounded answer.","confidence":"medium","limits":[]}',
                    }
                ]
            }
        ]
    }

    assert extract_response_text(payload).startswith('{"answer"')


def test_extract_response_text_rejects_missing_text():
    with pytest.raises(OpenAIGenerationError):
        extract_response_text({"output": []})


def test_httpx_error_response_shape_is_available():
    response = httpx.Response(
        status_code=401,
        json={"error": {"message": "invalid api key"}},
        request=httpx.Request("POST", "https://api.openai.com/v1/responses"),
    )

    assert response.status_code == 401

