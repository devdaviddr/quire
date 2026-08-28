"""Offline tests for the detector client — no network, no API key."""

import pytest

from app.llm import DetectorError, build_request, extract_json_object


def test_parses_clean_object():
    assert extract_json_object('{"spans": []}') == {"spans": []}


def test_tolerates_nemotron_stray_leading_brace():
    # Observed intermittently from nemotron-3-super under response_format:
    # the content begins with a duplicated opening brace.
    raw = '{\n{\n  "spans": [{"text": "Sandra", "role": "third_party", "rationale": "mother"}]\n}'
    assert extract_json_object(raw)["spans"][0]["text"] == "Sandra"


def test_tolerates_prose_around_the_object():
    raw = 'Here are the spans:\n{"spans": []}\nLet me know if you need more.'
    assert extract_json_object(raw) == {"spans": []}


def test_braces_inside_strings_do_not_break_balancing():
    raw = '{"spans": [{"text": "note {redacted}", "role": "third_party", "rationale": "x"}]}'
    assert extract_json_object(raw)["spans"][0]["text"] == "note {redacted}"


def test_raises_rather_than_guessing_on_unparseable_body():
    with pytest.raises(DetectorError):
        extract_json_object("no object here at all")


def test_request_uses_response_format_not_nvext():
    # nvext.guided_json is silently ignored by nemotron-3-nano/ultra and
    # rejected by super — structured output must go via response_format.
    body = build_request("page text", "self, adult former patient")
    assert body["response_format"]["type"] == "json_schema"
    assert "nvext" not in body
    assert body["temperature"] == 0


def test_role_enum_has_no_default_that_could_under_redact():
    body = build_request("page", "self")
    roles = body["response_format"]["json_schema"]["schema"]["properties"]["spans"][
        "items"
    ]["properties"]["role"]["enum"]
    assert "third_party" in roles
    assert "patient_own" in roles
