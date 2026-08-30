"""
Tests for CivicSight LLMExtractor service.

These tests mock the Groq client.

No real Groq API calls are made.
No API key is required for the mocked-client tests.
"""

from __future__ import annotations

import json

import pytest

from app.services.llm_extractor import (
    LLMConfigurationError,
    LLMExtractor,
    LLMExtractorError,
    LLMResponseError,
    LLMValidationError,
)


# ============================================================
# Test Helpers
# ============================================================


class FakeMessage:
    """Fake Groq response message."""

    def __init__(self, content):
        self.content = content


class FakeChoice:
    """Fake Groq response choice."""

    def __init__(self, content):
        self.message = FakeMessage(content)


class FakeResponse:
    """Fake Groq chat completion response."""

    def __init__(self, content):
        self.choices = [
            FakeChoice(content)
        ]


class FakeCompletions:
    """Fake Groq completions endpoint."""

    def __init__(
        self,
        response_content,
    ):
        self.response_content = response_content
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)

        return FakeResponse(
            self.response_content
        )


class FakeChat:
    """Fake Groq chat endpoint."""

    def __init__(
        self,
        response_content,
    ):
        self.completions = FakeCompletions(
            response_content
        )


class FakeGroqClient:
    """Fake Groq client."""

    def __init__(
        self,
        response_content,
    ):
        self.chat = FakeChat(
            response_content
        )


class FailingCompletions:
    """Fake endpoint that raises an API error."""

    def create(self, **kwargs):
        raise RuntimeError(
            "simulated Groq API failure"
        )


class FailingChat:
    """Fake chat endpoint with failing completions."""

    def __init__(self):
        self.completions = FailingCompletions()


class FailingGroqClient:
    """Fake Groq client that always fails."""

    def __init__(self):
        self.chat = FailingChat()


# ============================================================
# Fixtures
# ============================================================


@pytest.fixture
def valid_llm_json():
    """Valid structured LLM response."""

    return json.dumps(
        {
            "project_status": "ongoing",
            "duration": "2 months",
            "estimated_completion": "70%",
            "issue": "Road construction is incomplete",
        }
    )


@pytest.fixture
def extractor(valid_llm_json):
    """Extractor using a mocked Groq client."""

    client = FakeGroqClient(
        valid_llm_json
    )

    return LLMExtractor(
        client=client
    )


# ============================================================
# Initialization Tests
# ============================================================


def test_extractor_initializes_with_injected_client(
    valid_llm_json,
):
    """Injected Groq clients should be accepted."""

    client = FakeGroqClient(
        valid_llm_json
    )

    extractor = LLMExtractor(
        client=client
    )

    assert extractor.client is client
    assert extractor.model == LLMExtractor.DEFAULT_MODEL


def test_extractor_accepts_custom_model(
    valid_llm_json,
):
    """Custom model names should be preserved."""

    client = FakeGroqClient(
        valid_llm_json
    )

    extractor = LLMExtractor(
        client=client,
        model="custom-test-model",
    )

    assert extractor.model == "custom-test-model"


def test_extractor_rejects_empty_model(
    valid_llm_json,
):
    """An empty model name should raise configuration error."""

    client = FakeGroqClient(
        valid_llm_json
    )

    with pytest.raises(
        LLMConfigurationError,
        match="model name cannot be empty",
    ):
        LLMExtractor(
            client=client,
            model="   ",
        )


# ============================================================
# Input Validation Tests
# ============================================================


def test_validate_text_accepts_valid_text():
    """Normal report text should be accepted."""

    text = "Road construction is incomplete."

    result = LLMExtractor.validate_text(
        text
    )

    assert result == text


def test_validate_text_strips_whitespace():
    """Leading/trailing whitespace should be removed."""

    result = LLMExtractor.validate_text(
        "   Road construction is incomplete.   "
    )

    assert result == (
        "Road construction is incomplete."
    )


def test_validate_text_rejects_non_string():
    """Input must be a string."""

    with pytest.raises(
        LLMValidationError,
        match="must be a string",
    ):
        LLMExtractor.validate_text(
            123
        )


@pytest.mark.parametrize(
    "invalid_value",
    [
        "",
        " ",
        "   ",
        "\n",
        "\t",
    ],
)
def test_validate_text_rejects_empty_text(
    invalid_value,
):
    """Empty or whitespace-only input must fail."""

    with pytest.raises(
        LLMValidationError,
        match="cannot be empty",
    ):
        LLMExtractor.validate_text(
            invalid_value
        )


def test_validate_text_rejects_text_above_maximum_length():
    """Input larger than MAX_INPUT_LENGTH must fail."""

    text = "x" * (
        LLMExtractor.MAX_INPUT_LENGTH + 1
    )

    with pytest.raises(
        LLMValidationError,
        match="exceeds the maximum",
    ):
        LLMExtractor.validate_text(
            text
        )


def test_validate_text_accepts_text_at_maximum_length():
    """Input exactly at the configured limit should pass."""

    text = "x" * LLMExtractor.MAX_INPUT_LENGTH

    result = LLMExtractor.validate_text(
        text
    )

    assert len(result) == (
        LLMExtractor.MAX_INPUT_LENGTH
    )


# ============================================================
# Prompt Construction Tests
# ============================================================


def test_build_user_prompt_contains_report():
    """User prompt must contain the supplied report."""

    report = "The bridge is delayed."

    prompt = LLMExtractor._build_user_prompt(
        report
    )

    assert report in prompt
    assert "Extract structured project information" in prompt
    assert "Return ONLY the required JSON object" in prompt


def test_system_prompt_requires_json():
    """System prompt should enforce structured JSON output."""

    prompt = LLMExtractor.SYSTEM_PROMPT

    assert "valid JSON object" in prompt
    assert "NEVER invent facts" in prompt
    assert "NEVER guess missing information" in prompt
    assert "Do not add explanations" in prompt
    assert "Do not return additional fields" in prompt


# ============================================================
# Response Text Extraction Tests
# ============================================================


def test_extract_response_text_returns_content(
    valid_llm_json,
):
    """Valid Groq response content should be extracted."""

    response = FakeResponse(
        valid_llm_json
    )

    result = LLMExtractor._extract_response_text(
        response
    )

    assert result == valid_llm_json


def test_extract_response_text_strips_whitespace():
    """Response content should be stripped."""

    response = FakeResponse(
        "   {\"issue\": \"road damage\"}   "
    )

    result = LLMExtractor._extract_response_text(
        response
    )

    assert result == (
        "{\"issue\": \"road damage\"}"
    )


def test_extract_response_text_rejects_missing_choices():
    """A response without choices must fail."""

    class Response:
        choices = []

    with pytest.raises(
        LLMResponseError,
        match="no choices",
    ):
        LLMExtractor._extract_response_text(
            Response()
        )


def test_extract_response_text_rejects_missing_choices_attribute():
    """Malformed response objects must fail safely."""

    class Response:
        pass

    with pytest.raises(
        LLMResponseError,
        match="invalid response",
    ):
        LLMExtractor._extract_response_text(
            Response()
        )


def test_extract_response_text_rejects_missing_message():
    """Missing message structure must be rejected."""

    class Choice:
        pass

    class Response:
        choices = [Choice()]

    with pytest.raises(
        LLMResponseError,
        match="invalid message structure",
    ):
        LLMExtractor._extract_response_text(
            Response()
        )


def test_extract_response_text_rejects_none_content():
    """None response content must be rejected."""

    response = FakeResponse(
        None
    )

    with pytest.raises(
        LLMResponseError,
        match="empty response",
    ):
        LLMExtractor._extract_response_text(
            response
        )


def test_extract_response_text_rejects_empty_content():
    """Empty response content must be rejected."""

    response = FakeResponse(
        "   "
    )

    with pytest.raises(
        LLMResponseError,
        match="empty response",
    ):
        LLMExtractor._extract_response_text(
            response
        )


# ============================================================
# Markdown Fence Tests
# ============================================================


def test_remove_markdown_json_code_fence():
    """JSON code fences should be removed."""

    content = """```json
{"issue": "road damage"}
```"""

    result = (
        LLMExtractor
        ._remove_markdown_code_fence(content)
    )

    assert result == (
        '{"issue": "road damage"}'
    )


def test_remove_markdown_generic_code_fence():
    """Generic Markdown code fences should also be removed."""

    content = """```
{"issue": "road damage"}
```"""

    result = (
        LLMExtractor
        ._remove_markdown_code_fence(content)
    )

    assert result == (
        '{"issue": "road damage"}'
    )


def test_remove_markdown_code_fence_case_insensitive():
    """JSON fence detection should be case-insensitive."""

    content = """```JSON
{"issue": "road damage"}
```"""

    result = (
        LLMExtractor
        ._remove_markdown_code_fence(content)
    )

    assert result == (
        '{"issue": "road damage"}'
    )


def test_remove_markdown_code_fence_leaves_plain_json_unchanged():
    """Normal JSON should not be modified."""

    content = (
        '{"issue": "road damage"}'
    )

    result = (
        LLMExtractor
        ._remove_markdown_code_fence(content)
    )

    assert result == content


# ============================================================
# JSON Parsing Tests
# ============================================================


def test_parse_json_accepts_valid_object():
    """Valid JSON objects should parse successfully."""

    content = (
        '{"issue": "road damage"}'
    )

    result = LLMExtractor._parse_json(
        content
    )

    assert isinstance(result, dict)
    assert result["issue"] == "road damage"


def test_parse_json_accepts_fenced_json():
    """Fenced JSON should be accepted after cleanup."""

    content = """```json
{
    "issue": "road damage"
}
```"""

    result = LLMExtractor._parse_json(
        content
    )

    assert result["issue"] == "road damage"


def test_parse_json_rejects_malformed_json():
    """Malformed JSON must raise LLMResponseError."""

    content = (
        '{"issue": "road damage"'
    )

    with pytest.raises(
        LLMResponseError,
        match="malformed JSON",
    ):
        LLMExtractor._parse_json(
            content
        )


@pytest.mark.parametrize(
    "content",
    [
        "[]",
        '"text"',
        "123",
        "true",
        "null",
    ],
)
def test_parse_json_rejects_non_object_json(
    content,
):
    """Only JSON objects are accepted."""

    with pytest.raises(
        LLMResponseError,
        match="JSON object",
    ):
        LLMExtractor._parse_json(
            content
        )


# ============================================================
# Output Validation Tests
# ============================================================


def test_validate_output_accepts_valid_data(
    valid_llm_json,
):
    """Valid extracted data should pass the Pydantic model."""

    data = json.loads(
        valid_llm_json
    )

    result = LLMExtractor._validate_output(
        data
    )

    assert result.project_status == "ongoing"
    assert result.duration == "2 months"
    assert result.estimated_completion == "70%"
    assert result.issue == (
        "Road construction is incomplete"
    )


def test_validate_output_rejects_invalid_status():
    """Unsupported project status must fail schema validation."""

    data = {
        "project_status": "random_status",
        "duration": None,
        "estimated_completion": None,
        "issue": "Road damage",
    }

    with pytest.raises(
        LLMValidationError,
        match="failed schema validation",
    ):
        LLMExtractor._validate_output(
            data
        )


def test_validate_output_rejects_missing_required_fields():
    """Missing schema fields must fail validation."""

    data = {
        "project_status": "ongoing",
    }

    with pytest.raises(
        LLMValidationError,
        match="failed schema validation",
    ):
        LLMExtractor._validate_output(
            data
        )


def test_validate_output_rejects_extra_fields():
    """
    The extraction contract requires exactly the expected fields.

    The underlying Pydantic model should reject unexpected fields.
    """

    data = {
        "project_status": "ongoing",
        "duration": "2 months",
        "estimated_completion": "70%",
        "issue": "Road damage",
        "unexpected_field": "must not be accepted",
    }

    with pytest.raises(
        LLMValidationError,
        match="failed schema validation",
    ):
        LLMExtractor._validate_output(
            data
        )


# ============================================================
# Full extract() Tests
# ============================================================


def test_extract_returns_validated_response(
    extractor,
):
    """extract() should return a validated Pydantic response."""

    result = extractor.extract(
        "The road project is ongoing for 2 months and is 70% complete."
    )

    assert result.project_status == "ongoing"
    assert result.duration == "2 months"
    assert result.estimated_completion == "70%"
    assert result.issue == (
        "Road construction is incomplete"
    )


def test_extract_strips_input_before_sending_to_llm(
    valid_llm_json,
):
    """Whitespace should be normalized before prompt construction."""

    client = FakeGroqClient(
        valid_llm_json
    )

    extractor = LLMExtractor(
        client=client
    )

    extractor.extract(
        "   Road project is ongoing.   "
    )

    calls = client.chat.completions.calls

    assert len(calls) == 1

    user_message = calls[0]["messages"][1]

    assert (
        "Road project is ongoing."
        in user_message["content"]
    )

    assert (
        "   Road project is ongoing.   "
        not in user_message["content"]
    )


def test_extract_uses_configured_model(
    extractor,
):
    """Groq call must use the configured model."""

    extractor.extract(
        "Road construction is ongoing."
    )

    call = (
        extractor.client
        .chat
        .completions
        .calls[0]
    )

    assert call["model"] == extractor.model


def test_extract_uses_temperature_zero(
    extractor,
):
    """Extraction should use deterministic temperature."""

    extractor.extract(
        "Road construction is ongoing."
    )

    call = (
        extractor.client
        .chat
        .completions
        .calls[0]
    )

    assert call["temperature"] == 0


def test_extract_requests_json_response(
    extractor,
):
    """Groq call must request JSON object output."""

    extractor.extract(
        "Road construction is ongoing."
    )

    call = (
        extractor.client
        .chat
        .completions
        .calls[0]
    )

    assert call["response_format"] == {
        "type": "json_object"
    }


def test_extract_sends_system_and_user_messages(
    extractor,
):
    """LLM request should contain both required messages."""

    extractor.extract(
        "Road construction is ongoing."
    )

    call = (
        extractor.client
        .chat
        .completions
        .calls[0]
    )

    messages = call["messages"]

    assert len(messages) == 2

    assert messages[0]["role"] == "system"
    assert messages[1]["role"] == "user"

    assert (
        messages[0]["content"]
        == LLMExtractor.SYSTEM_PROMPT
    )


def test_extract_rejects_invalid_input_before_api_call(
    extractor,
):
    """Validation failure must happen before contacting Groq."""

    with pytest.raises(
        LLMValidationError,
    ):
        extractor.extract(
            ""
        )

    assert (
        len(
            extractor.client
            .chat
            .completions
            .calls
        )
        == 0
    )


def test_extract_rejects_oversized_input_before_api_call(
    extractor,
):
    """Oversized input must not reach the API."""

    text = "x" * (
        LLMExtractor.MAX_INPUT_LENGTH + 1
    )

    with pytest.raises(
        LLMValidationError,
    ):
        extractor.extract(
            text
        )

    assert (
        len(
            extractor.client
            .chat
            .completions
            .calls
        )
        == 0
    )


def test_extract_converts_api_failure_to_llm_extractor_error():
    """Groq failures should be wrapped in LLMExtractorError."""

    extractor = LLMExtractor(
        client=FailingGroqClient()
    )

    with pytest.raises(
        LLMExtractorError,
        match="LLM extraction request failed",
    ):
        extractor.extract(
            "The road project is delayed."
        )


def test_extract_propagates_response_error():
    """Malformed Groq responses should become LLMResponseError."""

    client = FakeGroqClient(
        "not valid json"
    )

    extractor = LLMExtractor(
        client=client
    )

    with pytest.raises(
        LLMResponseError,
        match="malformed JSON",
    ):
        extractor.extract(
            "Road damage reported."
        )


def test_extract_handles_fenced_json_response():
    """The extractor should tolerate accidental Markdown fences."""

    content = """```json
{
    "project_status": "completed",
    "duration": "3 months",
    "estimated_completion": "100%",
    "issue": "Road work completed"
}
```"""

    extractor = LLMExtractor(
        client=FakeGroqClient(content)
    )

    result = extractor.extract(
        "The road work has been completed."
    )

    assert result.project_status == "completed"
    assert result.duration == "3 months"
    assert result.estimated_completion == "100%"
    assert result.issue == (
        "Road work completed"
    )


# ============================================================
# extract_dict() Tests
# ============================================================


def test_extract_dict_returns_dictionary(
    extractor,
):
    """extract_dict() should return a plain dictionary."""

    result = extractor.extract_dict(
        "The road project is ongoing."
    )

    assert isinstance(
        result,
        dict,
    )


def test_extract_dict_contains_expected_fields(
    extractor,
):
    """Dictionary output should contain the API contract fields."""

    result = extractor.extract_dict(
        "The road project is ongoing."
    )

    assert set(result.keys()) == {
        "project_status",
        "duration",
        "estimated_completion",
        "issue",
    }


def test_extract_dict_values_are_serializable(
    extractor,
):
    """Dictionary output should be suitable for API serialization."""

    result = extractor.extract_dict(
        "The road project is ongoing."
    )

    encoded = json.dumps(
        result
    )

    decoded = json.loads(
        encoded
    )

    assert decoded == result


# ============================================================
# Exception Hierarchy Tests
# ============================================================


def test_configuration_error_inherits_from_extractor_error():
    """Configuration errors should belong to the service hierarchy."""

    assert issubclass(
        LLMConfigurationError,
        LLMExtractorError,
    )


def test_validation_error_inherits_from_extractor_error():
    """Validation errors should belong to the service hierarchy."""

    assert issubclass(
        LLMValidationError,
        LLMExtractorError,
    )


def test_response_error_inherits_from_extractor_error():
    """Response errors should belong to the service hierarchy."""

    assert issubclass(
        LLMResponseError,
        LLMExtractorError,
    )


# ============================================================
# Boundary / Regression Tests
# ============================================================


@pytest.mark.parametrize(
    "status",
    [
        "planned",
        "ongoing",
        "delayed",
        "completed",
        "halted",
        "abandoned",
        "unknown",
    ],
)
def test_validate_output_accepts_all_allowed_statuses(
    status,
):
    """Every status documented by LLMExtractor should be accepted."""

    data = {
        "project_status": status,
        "duration": None,
        "estimated_completion": None,
        "issue": "Infrastructure issue",
    }

    result = LLMExtractor._validate_output(
        data
    )

    assert result.project_status == status


def test_validate_output_accepts_null_optional_values():
    """Missing factual information may be represented by null."""

    data = {
        "project_status": "unknown",
        "duration": None,
        "estimated_completion": None,
        "issue": None,
    }

    result = LLMExtractor._validate_output(
        data
    )

    assert result.project_status == "unknown"
    assert result.duration is None
    assert result.estimated_completion is None
    assert result.issue is None