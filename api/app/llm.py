"""Client for the contextual detector (pipeline stage 3c).

This is the only stage that talks to a model, and it is deliberately thin: it
returns *candidate spans and roles*, never an exemption decision. The rulebook
that cites a section is plain Python with no network call in it — see
docs/architecture.md, rule one.

The endpoint is OpenAI-compatible, so the same client drives NVIDIA NIM
(hosted) or a local llama.cpp / Ollama server. Only the base URL changes.
"""

from __future__ import annotations

import json
from typing import Any

import httpx

from app.config import settings

# Roles are spelled out for the model rather than named, because a bare label
# list produces confident nonsense: an early probe classified the patient's
# mother and father as `patient_own`. The fail-safe line at the end matters —
# a third party mislabelled as the applicant's own information is an
# under-redaction, which is the failure mode that cannot be recalled.
SYSTEM_PROMPT = """\
You locate spans in a clinical record that may need redaction and classify each \
span's role RELATIVE TO THE APPLICANT.

Roles (choose exactly one):
  patient_own            = information about the APPLICANT themselves
  third_party            = any other individual: family, another patient, a notifier
  clinician_professional = a treating clinician acting in a professional capacity
  confidential_source    = someone who gave information expecting it stay confidential
  deliberative           = internal opinion or deliberation not part of the clinical record

A family member is NEVER patient_own. When unsure, choose third_party.
Over-flag: missing a span is unacceptable. Do not decide exemptions."""

SPAN_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "spans": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "text": {"type": "string"},
                    "role": {
                        "type": "string",
                        "enum": [
                            "patient_own",
                            "third_party",
                            "clinician_professional",
                            "confidential_source",
                            "deliberative",
                        ],
                    },
                    "rationale": {"type": "string"},
                },
                "required": ["text", "role", "rationale"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["spans"],
    "additionalProperties": False,
}


class DetectorError(RuntimeError):
    pass


def extract_json_object(raw: str) -> dict[str, Any]:
    """Parse the first balanced JSON object in `raw`.

    Nemotron intermittently prefixes a stray opening brace, so the content is
    not reliably `json.loads`-able even under a json_schema response format.
    Scanning for the first *balanced* object tolerates that without masking a
    genuinely malformed body — if nothing parses, we raise rather than guess.
    """
    start = raw.find("{")
    while start != -1:
        depth = 0
        in_string = False
        escaped = False
        for i in range(start, len(raw)):
            ch = raw[i]
            if escaped:
                escaped = False
                continue
            if ch == "\\" and in_string:
                escaped = True
                continue
            if ch == '"':
                in_string = not in_string
                continue
            if in_string:
                continue
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(raw[start : i + 1])
                    except json.JSONDecodeError:
                        break
        start = raw.find("{", start + 1)
    raise DetectorError("no parseable JSON object in model response")


def build_request(page_text: str, request_context: str) -> dict[str, Any]:
    """Assemble the chat-completions body for one page.

    `nvext.guided_json` is silently ignored by nemotron-3-nano/ultra and
    rejected outright by super, so structured output must go through the
    OpenAI-style `response_format`.
    """
    return {
        "model": settings.llm_model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"Applicant: {request_context}\n\nPAGE:\n{page_text}",
            },
        ],
        "response_format": {
            "type": "json_schema",
            "json_schema": {"name": "spans", "schema": SPAN_SCHEMA},
        },
        "max_tokens": settings.llm_max_tokens,
        "temperature": 0,
    }


async def detect_page(
    client: httpx.AsyncClient, page_text: str, request_context: str
) -> list[dict[str, Any]]:
    """Return candidate spans for one page. Raises on an unusable response."""
    response = await client.post(
        "/chat/completions",
        json=build_request(page_text, request_context),
        timeout=settings.llm_timeout_seconds,
    )
    response.raise_for_status()
    payload = response.json()

    choice = payload["choices"][0]
    if choice.get("finish_reason") == "length":
        # Truncation drops spans off the end of the array. Silently accepting a
        # short list here would under-report on exactly the densest pages.
        raise DetectorError(
            f"response truncated at {settings.llm_max_tokens} tokens; "
            "raise QUIRE_LLM_MAX_TOKENS"
        )

    return extract_json_object(choice["message"]["content"])["spans"]


def detector_client() -> httpx.AsyncClient:
    headers = {"Content-Type": "application/json"}
    if settings.llm_api_key:
        headers["Authorization"] = f"Bearer {settings.llm_api_key}"
    return httpx.AsyncClient(base_url=settings.llm_base_url, headers=headers)
