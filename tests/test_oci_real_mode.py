"""Real-mode (MOCK_MODE=false) parsing, tested offline with fake SDK
responses -- no network, no credentials. scripts/check_oci.py is the live
counterpart."""

from types import SimpleNamespace

import pytest

from app.docs import oci_client as docs_oci
from app.docs.schemas import LetterType
from app.oci_genai import language_name, parse_json_object


@pytest.mark.parametrize(
    "text",
    [
        '{"a": 1}',
        '```json\n{"a": 1}\n```',
        '```\n{"a": 1}\n```',
        'Here is the JSON:\n{"a": 1}\nLet me know if you need more.',
    ],
)
def test_parse_json_object_tolerates_fences_and_chatter(text):
    assert parse_json_object(text) == {"a": 1}


@pytest.mark.parametrize(
    "reply,expected",
    [
        ("ssa_benefit_letter", LetterType.SSA_BENEFIT_LETTER),
        ("ssa_benefit_letter.", LetterType.SSA_BENEFIT_LETTER),
        ('"bank_statement"', LetterType.BANK_STATEMENT),
        ("Label: hra_renewal_notice", LetterType.HRA_RENEWAL_NOTICE),
        ("I'm not sure", LetterType.OTHER),
    ],
)
def test_real_classify_tolerates_extra_text(monkeypatch, reply, expected):
    monkeypatch.setattr(docs_oci, "genai_chat", lambda prompt, json_mode=False: reply)
    assert docs_oci._real_classify("some letter") == expected


def test_real_extract_asks_for_json_mode_and_parses_fenced_reply(monkeypatch):
    calls = {}

    def fake_chat(prompt, json_mode=False):
        calls["json_mode"] = json_mode
        return '```json\n{"gross_monthly_benefit": 1700, "part_b_deduction": 202.9, ' \
               '"net_payment": 1497.1, "effective_date": "2026-01-01"}\n```'

    monkeypatch.setattr(docs_oci, "genai_chat", fake_chat)
    fields = docs_oci._real_extract(LetterType.SSA_BENEFIT_LETTER, "text", {}, retry_after_invalid=False)
    assert calls["json_mode"] is True
    assert fields["gross_monthly_benefit"] == 1700


def test_real_explain_names_the_language_and_guards_numbers(monkeypatch):
    seen = {}

    def fake_chat(prompt, json_mode=False):
        seen["prompt"] = prompt
        return "您每月领 $1,700.00。"

    monkeypatch.setattr(docs_oci, "genai_chat", fake_chat)
    out = docs_oci._real_explain(LetterType.SSA_BENEFIT_LETTER, {"gross_monthly_benefit": 1700.0}, "zh")
    assert "Simplified Chinese" in seen["prompt"]
    assert "1,700" in out

    monkeypatch.setattr(docs_oci, "genai_chat", lambda prompt, json_mode=False: "您每月领 $9,999。")
    with pytest.raises(ValueError):
        docs_oci._real_explain(LetterType.SSA_BENEFIT_LETTER, {"gross_monthly_benefit": 1700.0}, "zh")


def test_real_ocr_reads_lines_and_requests_text_extraction_only(monkeypatch):
    import oci

    captured = {}

    class FakeClient:
        def __init__(self, config, **kwargs):
            captured["region"] = config["region"]

        def analyze_document(self, analyze_document_details):
            captured["features"] = [f.feature_type for f in analyze_document_details.features]
            page = SimpleNamespace(lines=[SimpleNamespace(text="Social Security Administration"),
                                          SimpleNamespace(text="Full monthly benefit $1,700.00")])
            return SimpleNamespace(data=SimpleNamespace(pages=[page]))

    monkeypatch.setattr(oci.ai_document, "AIServiceDocumentClient", FakeClient)
    monkeypatch.setattr(docs_oci, "oci_config", lambda: {"region": "us-chicago-1"})
    monkeypatch.setenv("OCI_COMPARTMENT_ID", "ocid1.compartment.test")

    ocr = docs_oci._real_ocr(b"fake-jpeg")
    assert ocr.raw_text == "Social Security Administration\nFull monthly benefit $1,700.00"
    assert captured["features"] == ["TEXT_EXTRACTION"]


def test_oci_region_env_overrides_config_file(monkeypatch, tmp_path):
    import oci

    from app.oci_genai import oci_config

    monkeypatch.setattr(
        oci.config, "from_file", lambda file_location, profile_name: {"region": "us-ashburn-1", "user": "u"}
    )
    monkeypatch.setenv("OCI_REGION", "us-chicago-1")
    assert oci_config()["region"] == "us-chicago-1"
    monkeypatch.delenv("OCI_REGION")
    assert oci_config()["region"] == "us-ashburn-1"


def test_failed_real_call_falls_back_and_logs(monkeypatch, caplog):
    from app.trace import call_with_fallback

    monkeypatch.setenv("MOCK_MODE", "false")

    def boom():
        raise RuntimeError("NotAuthorizedOrNotFound")

    with caplog.at_level("WARNING", logger="letterlens.oci"):
        assert call_with_fallback(boom, lambda: "mock") == "mock"
    assert "offline fallback" in caplog.text
    assert "NotAuthorizedOrNotFound" in caplog.text


def test_language_names():
    assert language_name("zh") == "Simplified Chinese"
    assert language_name("xx") == "xx"


def test_genai_chat_builds_a_valid_cohere_request(monkeypatch):
    import oci

    from app import oci_genai

    sent = {}

    class FakeClient:
        def __init__(self, config, **kwargs):
            sent["timeout"] = kwargs.get("timeout")

        def chat(self, details):
            sent["body"] = oci.util.to_dict(details)
            return SimpleNamespace(data=SimpleNamespace(chat_response=SimpleNamespace(text=' {"ok": true} ')))

    monkeypatch.setattr(oci.generative_ai_inference, "GenerativeAiInferenceClient", FakeClient)
    monkeypatch.setattr(oci_genai, "oci_config", lambda: {"region": "us-chicago-1"})
    monkeypatch.setenv("OCI_COMPARTMENT_ID", "ocid1.tenancy.oc1..test")
    monkeypatch.setenv("OCI_GENAI_MODEL_ID", "cohere.command-a-03-2025")

    assert oci_genai.genai_chat("hi", json_mode=True) == '{"ok": true}'
    body = sent["body"]
    assert body["serving_mode"] == {"serving_type": "ON_DEMAND", "model_id": "cohere.command-a-03-2025"}
    assert body["chat_request"]["api_format"] == "COHERE"
    assert body["chat_request"]["response_format"]["type"] == "JSON_OBJECT"
    assert sent["timeout"] == (10, 60)

    oci_genai.genai_chat("hi")
    assert sent["body"]["chat_request"].get("response_format") is None
