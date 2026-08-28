

from __future__ import annotations

import json
import logging
import re
from typing import Any, Optional

from groq import Groq

from app.config import settings
from app.models.issue_models import IssueExtractionResponse


logger = logging.getLogger(__name__)


# Exceptions


class LLMExtractorError(Exception):
    """Base exception for LLM extraction errors."""


class LLMConfigurationError(LLMExtractorError):
    """Raised when LLM configuration is missing or invalid."""


class LLMValidationError(LLMExtractorError):
    """Raised when input or extracted output fails validation."""


class LLMResponseError(LLMExtractorError):
    """Raised when the LLM response is unusable."""


# LLM Extractor


class LLMExtractor:
    """
    Extract structured project information using Groq.

    The service accepts unstructured citizen/field reports and
    converts them into the stable IssueExtractionResponse contract.

    The LLM is instructed to:
        - extract only supported information
        - never invent facts
        - never guess missing information
        - return null for unavailable information
        - return exactly four required fields
        - return valid JSON only
    """

    DEFAULT_MODEL = "openai/gpt-oss-120b"

    MAX_INPUT_LENGTH = 10_000

    REQUIRED_FIELDS = frozenset(
        {
            "project_status",
            "duration",
            "estimated_completion",
            "issue",
        }
    )

    ALLOWED_STATUS_VALUES = frozenset(
        {
            "planned",
            "ongoing",
            "delayed",
            "completed",
            "halted",
            "abandoned",
            "unknown",
        }
    )

    
    # System prompt

    SYSTEM_PROMPT = """
You are the CivicSight infrastructure intelligence
extraction engine.

Extract structured information from citizen reports
and field-officer descriptions.

Return ONLY one valid JSON object.

The JSON object MUST contain exactly these fields:

{
    "project_status": string or null,
    "duration": string or null,
    "estimated_completion": string or null,
    "issue": string or null
}

Allowed project_status values:

- planned
- ongoing
- delayed
- completed
- halted
- abandoned
- unknown

Rules:

1. NEVER invent facts.
2. NEVER guess missing information.
3. Extract only information explicitly supported by the input.
4. If information is unavailable, return null.
5. Always return all four required fields.
6. Do not return additional fields.
7. project_status must be one of:
   planned, ongoing, delayed, completed, halted, abandoned, unknown.
8. Return ONLY valid JSON.
9. Do not return Markdown.
10. Do not add explanations.
""".strip()

    USER_PROMPT_TEMPLATE = """
Extract structured project information from this report.

REPORT:
{report}

Return ONLY the required JSON object.
""".strip()

    # Initialization

    def __init__(
        self,
        client: Optional[Groq] = None,
        model: Optional[str] = None,
    ) -> None:
        """
        Initialize the extractor.

        A Groq client can be injected for testing. If no client is
        supplied, the configured GROQ_API_KEY is used.
        """

        selected_model = (
            model
            if model is not None
            else self.DEFAULT_MODEL
        )

        if (
            not isinstance(
                selected_model,
                str,
            )
            or not selected_model.strip()
        ):
            raise LLMConfigurationError(
                "Groq model name cannot be empty."
            )

        self.model = selected_model.strip()

        # Dependency injection is intentionally supported.
        if client is not None:
            self.client = client
            return

        api_key = self._get_api_key()

        try:
            self.client = Groq(
                api_key=api_key
            )

        except Exception as exc:
            logger.exception(
                "Failed to initialize Groq client."
            )

            raise LLMConfigurationError(
                "Unable to initialize the Groq client."
            ) from exc

    # Configuration

    @staticmethod
    def _get_api_key() -> str:
        """
        Read and validate the Groq API key from application settings.
        """

        try:
            secret = settings.groq_api_key

        except AttributeError as exc:
            raise LLMConfigurationError(
                "groq_api_key is not defined in application settings."
            ) from exc

        if secret is None:
            raise LLMConfigurationError(
                "GROQ_API_KEY is not configured."
            )

        try:
            api_key = secret.get_secret_value()

        except AttributeError as exc:
            raise LLMConfigurationError(
                "groq_api_key must be configured as SecretStr."
            ) from exc

        if (
            not isinstance(
                api_key,
                str,
            )
            or not api_key.strip()
        ):
            raise LLMConfigurationError(
                "GROQ_API_KEY is empty."
            )

        return api_key.strip()

    # Input validation

    @classmethod
    def validate_text(
        cls,
        text: str,
    ) -> str:
        """
        Validate and normalize input report text.
        """

        if not isinstance(
            text,
            str,
        ):
            raise LLMValidationError(
                "Input description must be a string."
            )

        normalized = text.strip()

        if not normalized:
            raise LLMValidationError(
                "Input description cannot be empty."
            )

        if len(normalized) > cls.MAX_INPUT_LENGTH:
            raise LLMValidationError(
                "Input description exceeds the maximum "
                f"allowed length of "
                f"{cls.MAX_INPUT_LENGTH} characters."
            )

        return normalized

    @classmethod
    def _build_user_prompt(
        cls,
        text: str,
    ) -> str:
        """Build the user-facing extraction prompt."""

        return cls.USER_PROMPT_TEMPLATE.format(
            report=text
        )

    # Groq response extraction

    @staticmethod
    def _extract_response_text(
        response: Any,
    ) -> str:
        """
        Extract assistant message content from a Groq response.
        """

        try:
            choices = response.choices

        except AttributeError as exc:
            raise LLMResponseError(
                "Groq returned an invalid response."
            ) from exc

        if not choices:
            raise LLMResponseError(
                "Groq returned no choices."
            )

        try:
            message = choices[0].message
            content = message.content

        except (
            AttributeError,
            IndexError,
            TypeError,
        ) as exc:
            raise LLMResponseError(
                "Groq returned an invalid message structure."
            ) from exc

        if content is None:
            raise LLMResponseError(
                "Groq returned an empty response."
            )

        content = str(
            content
        ).strip()

        if not content:
            raise LLMResponseError(
                "Groq returned an empty response."
            )

        return content

    # Markdown cleanup

    @staticmethod
    def _remove_markdown_code_fence(
        content: str,
    ) -> str:
        """
        Remove an accidental Markdown JSON code fence.

        Accepted:

            ```json
            {...}
            ```

        and:

            ```
            {...}
            ```

        Plain JSON is returned unchanged.
        """

        cleaned = content.strip()

        pattern = re.compile(
            r"^```(?:json)?\s*(.*?)\s*```$",
            re.IGNORECASE | re.DOTALL,
        )

        match = pattern.match(
            cleaned
        )

        if match:
            return match.group(1).strip()

        return cleaned
    # JSON parsing

    @classmethod
    def _parse_json(
        cls,
        content: str,
    ) -> dict[str, Any]:
        """
        Parse the LLM response as a JSON object.

        No heuristic extraction of arbitrary text is performed.
        """

        cleaned = (
            cls._remove_markdown_code_fence(
                content
            )
        )

        try:
            parsed = json.loads(
                cleaned
            )

        except json.JSONDecodeError as exc:
            raise LLMResponseError(
                "Groq returned malformed JSON."
            ) from exc

        if not isinstance(
            parsed,
            dict,
        ):
            raise LLMResponseError(
                "Groq response must be a JSON object."
            )

        return parsed

    # Output validation

    @classmethod
    def _validate_output(
        cls,
        data: dict[str, Any],
    ) -> IssueExtractionResponse:
        """
        Validate the complete extracted output.

        Missing information is represented by null.

        Example of valid output:

            {
                "project_status": "ongoing",
                "duration": null,
                "estimated_completion": null,
                "issue": "road damage"
            }

        Missing keys are invalid.

        Example:

            {
                "project_status": "ongoing"
            }

        Extra keys are also invalid.
        """

        if not isinstance(
            data,
            dict,
        ):
            raise LLMValidationError(
                "LLM output must be a JSON object."
            )

        keys = set(
            data.keys()
        )

        missing = (
            cls.REQUIRED_FIELDS
            - keys
        )

        extra = (
            keys
            - cls.REQUIRED_FIELDS
        )

        if missing:
            missing_fields = ", ".join(
                sorted(
                    missing
                )
            )

            raise LLMValidationError(
                "LLM output failed schema validation: "
                "missing required fields: "
                f"{missing_fields}"
            )

        if extra:
            extra_fields = ", ".join(
                sorted(
                    extra
                )
            )

            raise LLMValidationError(
                "LLM output failed schema validation: "
                "unsupported fields: "
                f"{extra_fields}"
            )

        status = data.get(
            "project_status"
        )

        if status is not None:

            if not isinstance(
                status,
                str,
            ):
                raise LLMValidationError(
                    "LLM output failed schema validation: "
                    "Invalid project_status."
                )

            normalized_status = (
                status.strip().lower()
            )

            if (
                normalized_status
                not in cls.ALLOWED_STATUS_VALUES
            ):
                raise LLMValidationError(
                    "LLM output failed schema validation: "
                    "Invalid project_status."
                )

            # Normalize allowed status values so downstream
            # services always receive the canonical representation.
            data = dict(data)

            data[
                "project_status"
            ] = normalized_status

        # Pydantic validation

        try:

            if hasattr(
                IssueExtractionResponse,
                "model_validate",
            ):
                return (
                    IssueExtractionResponse
                    .model_validate(
                        data
                    )
                )

            return (
                IssueExtractionResponse
                .parse_obj(
                    data
                )
            )

        except Exception as exc:

            raise LLMValidationError(
                "LLM output failed schema validation."
            ) from exc

    # Main extraction

    def extract(
        self,
        text: str,
    ) -> IssueExtractionResponse:
        """
        Extract structured information from a report.
        """

        validated_text = (
            self.validate_text(
                text
            )
        )

        user_prompt = (
            self._build_user_prompt(
                validated_text
            )
        )

        # Groq request

        try:

            response = (
                self.client
                .chat
                .completions
                .create(
                    model=self.model,
                    messages=[
                        {
                            "role": "system",
                            "content": (
                                self.SYSTEM_PROMPT
                            ),
                        },
                        {
                            "role": "user",
                            "content": user_prompt,
                        },
                    ],
                    temperature=0,
                    response_format={
                        "type": "json_object"
                    },
                )
            )

        except Exception as exc:

            logger.exception(
                "Groq extraction request failed."
            )

            raise LLMExtractorError(
                "LLM extraction request failed."
            ) from exc

        # Parse response

        content = (
            self._extract_response_text(
                response
            )
        )

        parsed = (
            self._parse_json(
                content
            )
        )

        # Validate response

        return self._validate_output(
            parsed
        )

    # Dictionary API

    def extract_dict(
        self,
        text: str,
    ) -> dict[str, Any]:
        """
        Extract structured information and return a dictionary.

        Useful for service-to-service integration where a plain
        dictionary is required.
        """

        result = self.extract(
            text
        )

        if hasattr(
            result,
            "model_dump",
        ):
            return result.model_dump()

        return result.dict()


# Public exports


__all__ = [
    "LLMExtractor",
    "LLMExtractorError",
    "LLMConfigurationError",
    "LLMValidationError",
    "LLMResponseError",
]