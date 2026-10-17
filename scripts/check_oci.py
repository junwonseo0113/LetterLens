"""Smoke test for real OCI connectivity -- run this once before a live demo
if you intend to show MOCK_MODE=false. Calls OCI Document Understanding and
OCI Generative AI once each with real credentials and prints OK/FAIL.

This only tests that credentials/network/SDK plumbing works. It does not
replace the test suite (which runs entirely in MOCK_MODE, no network) and
it does not verify the real-mode code paths are bug-free beyond "did the
call return without raising" -- see the README's note that the real-mode
implementations are unverified against a live tenancy.

Run with:
    MOCK_MODE=false OCI_CONFIG_PATH=... OCI_COMPARTMENT_ID=... \\
        OCI_GENAI_MODEL_ID=... python3 scripts/check_oci.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

if os.environ.get("MOCK_MODE", "true").lower() not in ("0", "false", "no"):
    print("MOCK_MODE is not set to false -- this script tests REAL OCI calls.")
    print("Set MOCK_MODE=false and the OCI_* env vars, then re-run.")
    sys.exit(1)

SAMPLE_IMAGE = REPO_ROOT / "demo" / "ssa_benefit_letter_sample.jpg"

results: list[tuple[str, bool, str]] = []


def check(name: str, fn) -> None:
    try:
        fn()
        results.append((name, True, ""))
        print(f"OK   {name}")
    except Exception as exc:  # noqa: BLE001 -- smoke test, any failure is reportable
        results.append((name, False, str(exc)))
        print(f"FAIL {name}: {exc}")


def check_genai_chat() -> None:
    from app.oci_genai import genai_chat

    output = genai_chat("Reply with exactly one word: OK")
    if not output or not output.strip():
        raise RuntimeError("empty response from OCI Generative AI")


def check_document_understanding() -> None:
    from app.docs.oci_client import _real_ocr

    image_bytes = SAMPLE_IMAGE.read_bytes()
    result = _real_ocr(image_bytes)
    if not result.raw_text:
        raise RuntimeError("OCI Document Understanding returned no text")


def main() -> None:
    print(f"Sample image: {SAMPLE_IMAGE}")
    check("OCI Generative AI (chat)", check_genai_chat)
    check("OCI Document Understanding (analyze_document)", check_document_understanding)

    failures = [name for name, ok, _ in results if not ok]
    print()
    if failures:
        print(f"{len(failures)} of {len(results)} checks failed: {', '.join(failures)}")
        sys.exit(1)
    print(f"All {len(results)} checks passed.")


if __name__ == "__main__":
    main()
