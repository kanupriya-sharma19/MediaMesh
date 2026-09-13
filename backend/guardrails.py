"""Safety checks around user input, tool calls, and model output."""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import Any

from backend.utils.config import load_settings

logger = logging.getLogger(__name__)


class GuardrailViolation(RuntimeError):
    """Raised when a request violates the MediaMesh safety policy."""


def _log_guardrail(guardrail: str, allowed: bool, reason: str) -> None:
    logger.warning(
        "guardrail_event type=%s allowed=%s reason=%s ts=%s",
        guardrail,
        allowed,
        reason,
        datetime.now(timezone.utc).isoformat(),
    )


def _get_max_input_length() -> int:
    return max(1, int(load_settings().max_input_length))


_PROMPT_INJECTION_PATTERNS = [
    r"\bignore\s+(all\s+)?previous\s+instructions?\b",
    r"\bforget\s+your\s+instructions?\b",
    r"\breveal\s+your\s+(?:system|developer|hidden)\s+prompt\b",
    r"\bshow\s+me\s+(?:the\s+)?(?:hidden|system|developer)\s+prompt\b",
    r"\bprint\s+(?:all\s+)?internal\s+instructions?\b",
    r"\byou\s+are\s+now\s+(?:the\s+)?(?:developer|system)\b",
    r"\boverride\s+(?:all\s+)?(?:system|developer)\s+instructions?\b",
    r"\b(?:api\s+keys?|secrets?|tokens?)\s+(?:you\s+have\s+access\s+to|available\s+to\s+your\s+tools)\b",
    r"\b(?:system|developer)\s+(?:prompt|instructions?)\b",
    r"\b(?:hidden|internal)\s+(?:prompt|instructions?)\b",
    r"\bdisregard\s+(?:all\s+)?(?:previous\s+)?instructions?\b",
]

_SECRET_PATTERNS = [
    r"(?i)\b(?:api[_ -]?key|access[_ -]?token|bearer|secret|password|passwd|pwd)\s*[:=]\s*['\"]?[^\s,;]+",
    r"(?i)\b(?:sk_live|sk_test|AIza[0-9A-Za-z\-_]{10,}|ghp_[A-Za-z0-9]{20,}|xox[baprs]-[A-Za-z0-9-]+|AKIA[0-9A-Z]{16})\b",
    r"(?i)\b(?:aws_access_key_id|aws_secret_access_key|github_pat|slack_token)\s*[:=]\s*['\"]?[^\s,;]+",
]

_EMAIL_RE = r"(?i)\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"
_PHONE_RE = r"(?<!\d)(?:\+?1[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?){2}\d{4}(?!\d)"
_CARD_RE = r"(?<!\d)(?:\d[ -]?){13,19}(?!\d)"


def _contains_pattern(text: str, patterns: list[str]) -> bool:
    return any(
        re.search(pattern, text, re.IGNORECASE | re.DOTALL) for pattern in patterns
    )


def _is_prompt_injection_attempt(text: str) -> bool:
    lowered = text.lower()
    if len(lowered) > 0 and "ignore all previous instructions" in lowered:
        return True
    if _contains_pattern(text, _PROMPT_INJECTION_PATTERNS):
        return True
    return False


def _contains_secret_extraction_attempt(text: str) -> bool:
    if re.search(
        r"(?i)\b(?:api[_ -]?key|secret|token|password)\b.*\b(?:show|reveal|give|print|expose|leak|display)\b",
        text,
    ):
        return True
    if re.search(
        r"(?i)\b(?:show|reveal|print|give|expose)\s+(?:me\s+)?(?:the\s+)?(?:api\s+keys?|secrets?|tokens?|credentials?)\b",
        text,
    ):
        return True
    return False


def _contains_secret_like_value(text: str) -> bool:
    if _contains_pattern(text, _SECRET_PATTERNS):
        return True
    return False


def _mask_sensitive_content(text: str) -> str:
    masked = re.sub(_EMAIL_RE, "[REDACTED_EMAIL]", text)
    masked = re.sub(_PHONE_RE, "[REDACTED_PHONE]", masked)
    masked = re.sub(_CARD_RE, "[REDACTED_CARD]", masked)
    masked = re.sub(
        r"(?i)\b(password|passwd|pwd)\s*[:=]\s*['\"]?[^\s,;]+",
        r"\1=[REDACTED_PASSWORD]",
        masked,
    )
    masked = re.sub(
        r"(?i)\b(api[_ -]?key|access[_ -]?token|secret|token|authorization|bearer)\s*[:=]\s*['\"]?[^\s,;]+",
        r"\1=[REDACTED_SECRET]",
        masked,
    )
    return masked


def guard_user_input(user_input: str) -> str:
    """Validate user input and redact ordinary PII before it reaches the model."""
    if not isinstance(user_input, str):
        raise GuardrailViolation("Your request is invalid.")

    text = user_input.strip()
    if not text:
        raise GuardrailViolation("Please enter a media-related question.")

    max_length = _get_max_input_length()
    if len(text) > max_length:
        _log_guardrail("input_length", False, "too_large")
        raise GuardrailViolation("Your request is too large to process.")

    if _is_prompt_injection_attempt(text):
        _log_guardrail("input_prompt_injection", False, "prompt_injection_attempt")
        raise GuardrailViolation(
            "I can't process that request because it conflicts with the application's safety rules."
        )

    if _contains_secret_extraction_attempt(text):
        _log_guardrail("input_sensitive_data", False, "secret_or_credential_detected")
        raise GuardrailViolation(
            "Your request contains sensitive information that can't be processed."
        )

    redacted = _mask_sensitive_content(text)
    _log_guardrail("input_allowed", True, "clean_or_redacted")
    return redacted


def validate_tool_call(server: str, tool: str, arguments: Any) -> dict[str, Any]:
    """Validate tool invocation arguments before contacting an MCP server."""
    if not isinstance(server, str) or not server.strip():
        raise GuardrailViolation("The selected tool server is invalid.")
    if not isinstance(tool, str) or not tool.strip():
        raise GuardrailViolation("The selected tool is invalid.")
    if not isinstance(arguments, dict):
        raise GuardrailViolation("Tool arguments must be provided as an object.")

    for key, value in arguments.items():
        if isinstance(key, str) and re.search(
            r"(?i)\b(?:api[_ -]?key|secret|token|password|authorization|auth)\b",
            key,
        ):
            _log_guardrail("tool_argument_auth", False, "sensitive_argument_name")
            raise GuardrailViolation(
                "Tool arguments contain unsafe authorization data."
            )
        if isinstance(value, str):
            if _is_prompt_injection_attempt(value):
                _log_guardrail(
                    "tool_prompt_injection", False, "prompt_injection_in_tool_args"
                )
                raise GuardrailViolation(
                    "Tool arguments conflict with MediaMesh safety rules."
                )
            if _contains_secret_extraction_attempt(
                value
            ) or _contains_secret_like_value(value):
                _log_guardrail(
                    "tool_sensitive_data", False, "secret_detected_in_tool_args"
                )
                raise GuardrailViolation(
                    "Tool arguments contain sensitive data that cannot be used."
                )

    _log_guardrail("tool_allowed", True, "validated_tool_call")
    return arguments


def validate_final_output(
    response: str, evidence: list[dict[str, Any]] | None = None
) -> str:
    """Validate final output before returning it to the user."""
    if not isinstance(response, str):
        raise GuardrailViolation("The model returned an invalid final response.")

    sanitized = response.strip()
    if not sanitized:
        return sanitized

    if _contains_pattern(
        sanitized,
        [
            r"(?i)\b(?:system|developer)\s+(?:prompt|instructions?)\b",
            r"(?i)\b(?:hidden|internal)\s+(?:prompt|instructions?)\b",
            r"(?i)\breveal\s+your\s+(?:system|developer|hidden)\s+prompt\b",
        ],
    ):
        _log_guardrail("output_prompt_leak", False, "internal_prompt_referenced")
        raise GuardrailViolation(
            "I can't provide internal instructions or hidden prompts."
        )

    if _contains_secret_like_value(sanitized):
        _log_guardrail("output_sensitive_data", False, "secret_or_credential_detected")
        raise GuardrailViolation(
            "The response contains sensitive information that can't be shared."
        )

    if evidence is not None:
        grounded = _ground_tool_claims(sanitized, evidence)
        if grounded != sanitized:
            _log_guardrail("output_grounding", True, "removed_ungrounded_tool_claim")
        sanitized = grounded

    _log_guardrail("output_allowed", True, "validated_final_output")
    return sanitized


def _ground_tool_claims(response: str, evidence: list[dict[str, Any]]) -> str:
    seen_servers = {
        str(item.get("server", "")).strip()
        for item in evidence
        if isinstance(item, dict)
    }
    for server in ("TMDB", "MusicBrainz", "GoogleBooks"):
        if server in response and server not in seen_servers:
            response = response.replace(server, "")
            response = re.sub(
                r"(?i)\bI\s+(?:searched|checked|queried|used|looked\s+at)\s+"
                + re.escape(server)
                + r"\b\s*",
                "",
                response,
            )
            response = re.sub(r"\s{2,}", " ", response).strip()
            response = re.sub(
                r"\s+and\s+found\b", " found", response, flags=re.IGNORECASE
            )
    return response
