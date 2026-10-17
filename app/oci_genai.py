"""Shared OCI GenAI chat helper (real mode only -- unverified skeleton).

Lazily imports the oci SDK so it's only required when MOCK_MODE=false.
Used by both app/docs/oci_client.py (classify/extract/explain-letter) and
app/explain/oci_client.py (explain-program-result).
"""

from __future__ import annotations

import os


def oci_config():
    import oci

    config_path = os.environ.get("OCI_CONFIG_PATH", "~/.oci/config")
    profile = os.environ.get("OCI_CONFIG_PROFILE", "DEFAULT")
    return oci.config.from_file(file_location=config_path, profile_name=profile)


def genai_chat(prompt: str) -> str:
    import oci
    from oci.generative_ai_inference.models import ChatDetails, CohereChatRequest, OnDemandServingMode

    config = oci_config()
    client = oci.generative_ai_inference.GenerativeAiInferenceClient(config)
    chat_request = CohereChatRequest(message=prompt, max_tokens=600, temperature=0.2)
    details = ChatDetails(
        compartment_id=os.environ["OCI_COMPARTMENT_ID"],
        serving_mode=OnDemandServingMode(model_id=os.environ["OCI_GENAI_MODEL_ID"]),
        chat_request=chat_request,
    )
    response = client.chat(details)
    return response.data.chat_response.text
