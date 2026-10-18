"""Shared OCI helpers for real mode (MOCK_MODE=false).

Lazily imports the oci SDK so it's only required when MOCK_MODE=false.
Used by app/docs, app/explain and app/protect.
"""

from __future__ import annotations

import json
import os
import re

# Prompts name the language in English; the model handles a name far more
# reliably than a bare code like "zh".
LANGUAGE_NAMES = {
    "en": "English",
    "zh": "Simplified Chinese",
    "ko": "Korean",
    "es": "Spanish",
    "ru": "Russian",
}


def language_name(code: str) -> str:
    return LANGUAGE_NAMES.get((code or "").lower(), code)


def oci_config() -> dict:
    import oci

    config_path = os.environ.get("OCI_CONFIG_PATH", "~/.oci/config")
    profile = os.environ.get("OCI_CONFIG_PROFILE", "DEFAULT")
    config = oci.config.from_file(file_location=config_path, profile_name=profile)
    # Generative AI only runs in a few regions (us-chicago-1 in the US), which
    # may not be the account's home region in the config file.
    if os.environ.get("OCI_REGION"):
        config["region"] = os.environ["OCI_REGION"]
    return config


def genai_chat(prompt: str, json_mode: bool = False) -> str:
    import oci
    from oci.generative_ai_inference.models import (
        ChatDetails,
        CohereChatRequest,
        CohereResponseJsonFormat,
        OnDemandServingMode,
    )

    client = oci.generative_ai_inference.GenerativeAiInferenceClient(oci_config(), timeout=(10, 60))
    chat_request = CohereChatRequest(
        message=prompt,
        max_tokens=800,
        temperature=0.2,
        response_format=CohereResponseJsonFormat() if json_mode else None,
    )
    details = ChatDetails(
        compartment_id=os.environ["OCI_COMPARTMENT_ID"],
        serving_mode=OnDemandServingMode(model_id=os.environ["OCI_GENAI_MODEL_ID"]),
        chat_request=chat_request,
    )
    response = client.chat(details)
    text = response.data.chat_response.text
    if not text or not text.strip():
        raise RuntimeError("OCI Generative AI returned an empty response")
    return text.strip()


_MARKDOWN_RE = re.compile(r"\*\*|__|`|^#+\s*", re.MULTILINE)


def plain_text(text: str) -> str:
    """Strip markdown (bold, code, headings) -- the app shows plain text."""
    return _MARKDOWN_RE.sub("", text).strip()


_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.IGNORECASE)


def parse_json_object(text: str) -> dict:
    """Parse a JSON object from model output, tolerating ```json fences or a
    sentence before/after the object."""
    cleaned = _FENCE_RE.sub("", text.strip())
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        start, end = cleaned.find("{"), cleaned.rfind("}")
        if start == -1 or end <= start:
            raise
        return json.loads(cleaned[start : end + 1])
