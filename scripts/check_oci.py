"""Smoke test for real OCI -- run once before a live demo with MOCK_MODE=false.

Calls the same real-mode functions the app uses, with no mock fallback, on
one of the sample letters: config -> Generative AI -> Document
Understanding OCR -> classify -> extract -> explain (in Chinese) ->
benefits explanation. Prints OK/FAIL per step plus a hint for common
errors. Reads ./.env if present, so it can be run directly:

    .venv/bin/pip install oci        # once
    .venv/bin/python scripts/check_oci.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))


def _load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_dotenv(REPO_ROOT / ".env")

if os.environ.get("MOCK_MODE", "true").lower() not in ("0", "false", "no"):
    print("MOCK_MODE is not false -- this script tests REAL OCI calls.")
    print("Set MOCK_MODE=false (in .env or the environment) and re-run.")
    sys.exit(1)

SAMPLE_IMAGE = REPO_ROOT / "demo" / "ssa_benefit_letter_sample.jpg"
state: dict = {}
results: list[tuple[str, bool]] = []


def hint(exc: Exception) -> str:
    text = f"{type(exc).__name__}: {exc}"
    status = getattr(exc, "status", None)
    code = getattr(exc, "code", "")
    if "No module named 'oci'" in text:
        return "Install the SDK: .venv/bin/pip install oci"
    if "ConfigFileNotFound" in text or "Could not find config file" in text:
        return "No OCI config file. Set OCI_CONFIG_PATH (e.g. ~/.oci/config) -- see the README's OCI section."
    if "InvalidPrivateKey" in text or "key_file" in text:
        return "The key_file in your OCI config doesn't point at a readable private key (.pem)."
    if isinstance(exc, KeyError) and "OCI_" in text:
        return f"Missing env var {exc}. Add it to .env."
    if status == 401:
        return "401 NotAuthenticated: user/fingerprint/key_file in the config don't match an API key on the user."
    if status == 404 or code == "NotAuthorizedOrNotFound":
        return (
            "404: usually the compartment OCID is wrong, the model id isn't offered in this region, "
            "or the user lacks permission. Check OCI_COMPARTMENT_ID and the model list in "
            "Console -> Generative AI for this region."
        )
    if status == 400:
        return "400 Bad request: often an invalid OCI_GENAI_MODEL_ID for chat, or an unsupported feature."
    if status == 429:
        return "429: rate limited -- wait a minute and retry."
    if "Max retries exceeded" in text or "NameResolutionError" in text or "ConnectTimeout" in text:
        return "Network problem, or OCI_REGION isn't a region with this service (use us-chicago-1)."
    return ""


def check(name: str, fn) -> None:
    try:
        detail = fn()
        results.append((name, True))
        print(f"OK    {name}" + (f"\n      {detail}" if detail else ""))
    except Exception as exc:  # noqa: BLE001 -- smoke test, any failure is reportable
        results.append((name, False))
        print(f"FAIL  {name}\n      {type(exc).__name__}: {str(exc)[:400]}")
        tip = hint(exc)
        if tip:
            print(f"      Hint: {tip}")


def check_config():
    import oci

    from app.oci_genai import oci_config

    config = oci_config()
    oci.config.validate_config(config)
    for var in ("OCI_COMPARTMENT_ID", "OCI_GENAI_MODEL_ID"):
        if not os.environ.get(var):
            raise KeyError(var)
    return (
        f"region={config['region']} model={os.environ['OCI_GENAI_MODEL_ID']} "
        f"compartment=...{os.environ['OCI_COMPARTMENT_ID'][-8:]}"
    )


def check_genai():
    from app.oci_genai import genai_chat

    return "reply: " + genai_chat("Reply with exactly one word: OK")[:60]


def check_ocr():
    from app.docs.oci_client import _real_ocr

    ocr = _real_ocr(SAMPLE_IMAGE.read_bytes())
    state["ocr"] = ocr
    return f"{len(ocr.raw_text)} chars, starts: {ocr.raw_text[:60]!r}"


def check_classify():
    from app.docs.oci_client import _real_classify

    letter_type = _real_classify(state["ocr"].raw_text)
    state["type"] = letter_type
    if letter_type.value != "ssa_benefit_letter":
        raise RuntimeError(f"expected ssa_benefit_letter, got {letter_type.value}")
    return letter_type.value


def check_extract():
    from app.docs.oci_client import _real_extract
    from app.docs.schemas import SCHEMA_BY_TYPE

    raw = _real_extract(state["type"], state["ocr"].raw_text, {}, retry_after_invalid=False)
    fields = SCHEMA_BY_TYPE[state["type"]].model_validate(raw).model_dump(mode="json")
    state["fields"] = fields
    if fields["gross_monthly_benefit"] != 1700:
        raise RuntimeError(f"expected gross_monthly_benefit 1700, got {fields['gross_monthly_benefit']}")
    return str(fields)


def check_explain():
    from app.docs.oci_client import _real_explain

    return _real_explain(state["type"], state["fields"], "zh")


def check_benefits_explain():
    from app.explain.oci_client import _real_explain
    from app.rules.engine import Profile, evaluate

    qmb = evaluate(Profile(has_medicare=True, ss_gross_monthly=1700, age=74))[0]
    return _real_explain(qmb, "zh")


def main() -> None:
    print(f"Sample image: {SAMPLE_IMAGE.name}\n")
    steps = [
        ("Config + credentials", check_config),
        ("Generative AI chat", check_genai),
        ("Document Understanding OCR", check_ocr),
        ("Classify letter (GenAI)", check_classify),
        ("Extract fields (GenAI, JSON)", check_extract),
        ("Explain letter in Chinese (GenAI + number guard)", check_explain),
        ("Explain QMB result in Chinese (GenAI + number guard)", check_benefits_explain),
    ]
    for name, fn in steps:
        needs = {"Classify": "ocr", "Extract": "type", "Explain letter": "fields"}
        missing = next((k for k, v in needs.items() if name.startswith(k) and v not in state), None)
        if results and not results[0][1]:
            results.append((name, False))
            print(f"SKIP  {name} (fix the config first)")
            continue
        if missing:
            results.append((name, False))
            print(f"SKIP  {name} (an earlier step failed)")
            continue
        check(name, fn)

    failures = [name for name, ok in results if not ok]
    print()
    if failures:
        print(f"{len(failures)} of {len(results)} checks failed.")
        sys.exit(1)
    print(f"All {len(results)} checks passed -- real OCI mode is working.")


if __name__ == "__main__":
    main()
