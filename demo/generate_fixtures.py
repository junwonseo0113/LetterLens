"""Generates the four fake "SAMPLE" letter images used by the demo.

These are cosmetic -- MOCK_MODE dispatches canned OCR text by filename
keyword (see app/docs/oci_client.py), it never actually reads these
pixels. The images exist so the demo has something real to photograph /
show on screen, and so their rendered text matches the mock OCR text for
narrative consistency. Every image is watermarked SAMPLE and clearly
marked as not a real government document.

Run with: python demo/generate_fixtures.py
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

DEMO_DIR = Path(__file__).resolve().parent

PAGE_SIZE = (1000, 1300)
MARGIN = 60

_TRUETYPE_CANDIDATES = [
    "/System/Library/Fonts/Supplemental/Arial.ttf",
    "/System/Library/Fonts/Helvetica.ttc",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
]


def _font(size: int) -> ImageFont.FreeTypeFont:
    for path in _TRUETYPE_CANDIDATES:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def _render_letter(filename: str, header: str, body_lines: list[str]) -> None:
    image = Image.new("RGB", PAGE_SIZE, "white")
    draw = ImageDraw.Draw(image)

    banner_font = _font(22)
    header_font = _font(28)
    body_font = _font(24)
    watermark_font = _font(120)

    draw.rectangle([(0, 0), (PAGE_SIZE[0], 50)], fill=(200, 0, 0))
    draw.text(
        (MARGIN, 14),
        "SAMPLE DOCUMENT -- FOR HACKATHON DEMO ONLY, NOT A REAL GOVERNMENT LETTER",
        font=banner_font,
        fill="white",
    )

    y = 100
    draw.text((MARGIN, y), header, font=header_font, fill="black")
    y += 60

    for line in body_lines:
        draw.text((MARGIN, y), line, font=body_font, fill="black")
        y += 42

    watermark = Image.new("RGBA", PAGE_SIZE, (255, 255, 255, 0))
    wm_draw = ImageDraw.Draw(watermark)
    wm_draw.text(
        (PAGE_SIZE[0] * 0.08, PAGE_SIZE[1] * 0.38),
        "SAMPLE",
        font=watermark_font,
        fill=(200, 0, 0, 90),
    )
    watermark = watermark.rotate(30, expand=False, center=(PAGE_SIZE[0] / 2, PAGE_SIZE[1] / 2))
    image = Image.alpha_composite(image.convert("RGBA"), watermark).convert("RGB")

    image.save(DEMO_DIR / filename, "JPEG", quality=90)
    print(f"Wrote {filename}")


def main() -> None:
    _render_letter(
        "ssa_benefit_letter_sample.jpg",
        "SOCIAL SECURITY ADMINISTRATION",
        [
            "Kim, Soon-ja",
            "123 Northern Blvd, Apt 4B",
            "Flushing, NY 11354",
            "",
            "Date: January 2, 2026",
            "",
            "Your monthly benefit amount is $1,700.00.",
            "Medicare Part B premium deduction: $202.90.",
            "Your net payment is $1,497.10.",
            "This change is effective 2026-01-01.",
        ],
    )

    _render_letter(
        "bank_statement_sample.jpg",
        "CHASE BANK -- SAMPLE STATEMENT",
        [
            "Account holder: Kim, Soon-ja",
            "Statement period: Sep 1 - Sep 30, 2026",
            "",
            "Ending balance: $40,000.00",
            "Recurring deposit: SSA TREAS 310   $1,700.00",
        ],
    )

    _render_letter(
        "hra_snap_renewal_notice_sample.jpg",
        "NYC HUMAN RESOURCES ADMINISTRATION (HRA)",
        [
            "SNAP Recertification Notice",
            "",
            "Kim, Soon-ja",
            "Case #: SAMPLE-0001",
            "",
            "Your SNAP case must be recertified by 2026-11-15.",
            "Please submit: proof of income, proof of residence, ID.",
        ],
    )

    _render_letter(
        "medical_bill_sample.jpg",
        "QUEENS GENERAL HOSPITAL -- SAMPLE BILLING STATEMENT",
        [
            "Patient: Kim, Soon-ja",
            "",
            "Provider: Queens General Hospital",
            "Line item: Annual wellness visit copay   $20.00   (copay)",
            "This is a Medicare claim.",
        ],
    )


if __name__ == "__main__":
    main()
