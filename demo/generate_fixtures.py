"""Generates the four fake "SAMPLE" letter images used by the demo.

Layout conventions (letterhead badge + reference-number block, bold
section headers, boxed claim/cost summaries, checkbox document lists)
are modeled on real official formats for visual authenticity:
  - SSA Benefit Verification Letter (ssa.gov sample)
  - CMS Medicare Summary Notice for Part B (cms.gov sample)
  - NYC HRA Mail-in Recertification/Eligibility Questionnaire (Form M-327h)
  - Medicare Rights Center MSP application coversheet

These are cosmetic -- MOCK_MODE dispatches canned OCR text by filename
keyword (see app/docs/oci_client.py), it never actually reads these
pixels. No real agency seal/logo is reproduced (badges below are generic
placeholders, not the actual SSA/HHS/NYC marks) and every image carries
a SAMPLE watermark plus a banner stating it is not a real government
document -- this must never be mistaken for an actual letter.

Run with: python demo/generate_fixtures.py
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

DEMO_DIR = Path(__file__).resolve().parent

PAGE_SIZE = (1000, 1300)
MARGIN = 70
INK = (30, 30, 30)
MUTED = (90, 90, 90)
RULE = (190, 190, 190)

_TRUETYPE_CANDIDATES = [
    "/System/Library/Fonts/Supplemental/Arial.ttf",
    "/System/Library/Fonts/Helvetica.ttc",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
]
_BOLD_CANDIDATES = [
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "/System/Library/Fonts/Helvetica.ttc",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
]


def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    candidates = _BOLD_CANDIDATES if bold else _TRUETYPE_CANDIDATES
    for path in candidates:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


class Letter:
    """Small drawing helper so each fixture reads as a sequence of
    layout blocks (letterhead, section header, body, box, checklist)
    instead of raw coordinate math."""

    def __init__(self):
        self.image = Image.new("RGB", PAGE_SIZE, "white")
        self.draw = ImageDraw.Draw(self.image)
        self.y = 0

    def letterhead(self, badge_text: str, badge_color, org_lines: list[str], ref_lines: list[str]) -> None:
        cx, cy, r = MARGIN + 36, 96, 36
        self.draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=badge_color)
        bf = _font(20, bold=True)
        bbox = self.draw.textbbox((0, 0), badge_text, font=bf)
        self.draw.text(
            (cx - (bbox[2] - bbox[0]) / 2, cy - (bbox[3] - bbox[1]) / 2 - bbox[1]),
            badge_text,
            font=bf,
            fill="white",
        )

        tx = MARGIN + 90
        ty = 56
        for i, line in enumerate(org_lines):
            f = _font(30, bold=True) if i == 0 else _font(22)
            self.draw.text((tx, ty), line, font=f, fill=INK)
            ty += 38 if i == 0 else 28

        ry = 56
        rf = _font(20)
        for line in ref_lines:
            w = self.draw.textlength(line, font=rf)
            self.draw.text((PAGE_SIZE[0] - MARGIN - w, ry), line, font=rf, fill=MUTED)
            ry += 26

        self.y = 170
        self.draw.line([(MARGIN, self.y), (PAGE_SIZE[0] - MARGIN, self.y)], fill=RULE, width=2)
        self.y += 24

    def address_block(self, lines: list[str]) -> None:
        f = _font(22)
        for line in lines:
            self.draw.text((MARGIN, self.y), line, font=f, fill=INK)
            self.y += 28
        self.y += 20

    def section_header(self, text: str) -> None:
        self.draw.text((MARGIN, self.y), text, font=_font(23, bold=True), fill=INK)
        self.y += 34

    def body(self, lines: list[str]) -> None:
        f = _font(22)
        for line in lines:
            self.draw.text((MARGIN, self.y), line, font=f, fill=INK)
            self.y += 32
        self.y += 14

    def box(self, rows: list[tuple[str, str]], title: str | None = None) -> None:
        pad = 20
        row_h = 36
        title_h = 36 if title else 0
        box_h = title_h + len(rows) * row_h + pad * 2
        x0, y0 = MARGIN, self.y
        x1 = PAGE_SIZE[0] - MARGIN
        self.draw.rectangle([x0, y0, x1, y0 + box_h], outline=RULE, width=2)

        ty = y0 + pad
        if title:
            self.draw.text((x0 + pad, ty), title, font=_font(22, bold=True), fill=INK)
            ty += title_h

        label_f = _font(21)
        value_f = _font(21, bold=True)
        for label, value in rows:
            self.draw.text((x0 + pad, ty), label, font=label_f, fill=MUTED)
            vw = self.draw.textlength(value, font=value_f)
            self.draw.text((x1 - pad - vw, ty), value, font=value_f, fill=INK)
            ty += row_h

        self.y = y0 + box_h + 24

    def checklist(self, items: list[str]) -> None:
        f = _font(21)
        box = 20
        for item in items:
            self.draw.rectangle(
                [MARGIN, self.y + 3, MARGIN + box, self.y + 3 + box], outline=INK, width=2
            )
            self.draw.text((MARGIN + box + 14, self.y), item, font=f, fill=INK)
            self.y += 36

    def barcode_strip(self) -> None:
        import random

        rng = random.Random(42)
        x = 20
        while x < 50:
            w = rng.choice([2, 2, 4])
            self.draw.rectangle([x, 40, x + w, 240], fill="black")
            x += w + rng.choice([3, 5])

    def finish(self, filename: str) -> None:
        banner_font = _font(20, bold=True)
        self.draw.rectangle([(0, 0), (PAGE_SIZE[0], 44)], fill=(190, 0, 0))
        self.draw.text(
            (MARGIN, 12),
            "SAMPLE -- FOR HACKATHON DEMO ONLY, NOT A REAL GOVERNMENT DOCUMENT",
            font=banner_font,
            fill="white",
        )

        watermark_font = _font(130, bold=True)
        watermark = Image.new("RGBA", PAGE_SIZE, (255, 255, 255, 0))
        wm_draw = ImageDraw.Draw(watermark)
        wm_draw.text(
            (PAGE_SIZE[0] * 0.06, PAGE_SIZE[1] * 0.42),
            "SAMPLE",
            font=watermark_font,
            fill=(200, 0, 0, 80),
        )
        watermark = watermark.rotate(28, expand=False, center=(PAGE_SIZE[0] / 2, PAGE_SIZE[1] / 2))
        image = Image.alpha_composite(self.image.convert("RGBA"), watermark).convert("RGB")

        image.save(DEMO_DIR / filename, "JPEG", quality=90)
        print(f"Wrote {filename}")


def make_ssa_benefit_letter() -> None:
    l = Letter()
    l.barcode_strip()
    l.letterhead(
        "SSA",
        (0, 90, 60),
        ["Social Security Administration", "Benefit Verification Letter"],
        ["Date: January 2, 2026", "BNC#: SAMPLE-0001", "REF: KIM-SOONJA"],
    )
    l.address_block(["Kim, Soon-ja", "123 Northern Blvd, Apt 4B", "Flushing, NY 11354"])
    l.body(
        [
            "You asked us for information from your record. The information",
            "that you requested is shown below.",
        ]
    )
    l.section_header("Information About Current Social Security Benefits")
    l.box(
        [
            ("Full monthly benefit before deductions", "$1,700.00"),
            ("Medicare Part B premium deduction", "$202.90"),
            ("Your net payment", "$1,497.10"),
            ("Effective", "2026-01-01"),
        ]
    )
    l.body(["Social Security benefits are paid the month after they are due."])
    l.section_header("Social Security Administration")
    l.finish("ssa_benefit_letter_sample.jpg")


def make_bank_statement() -> None:
    l = Letter()
    l.letterhead(
        "BK",
        (20, 60, 140),
        ["Sample Community Bank", "Checking Account Statement"],
        ["Statement period:", "Sep 1 - Sep 30, 2026"],
    )
    l.address_block(["Account holder: Kim, Soon-ja", "123 Northern Blvd, Apt 4B", "Flushing, NY 11354"])
    l.section_header("Account Summary")
    l.box(
        [
            ("Beginning balance", "$38,312.10"),
            ("Deposits this period", "$1,700.00"),
            ("Ending balance", "$40,000.00"),
        ]
    )
    l.section_header("Recurring Deposits")
    l.body(["09/03/2026   SSA TREAS 310 SOC SEC          $1,700.00"])
    l.finish("bank_statement_sample.jpg")


def make_hra_renewal_notice() -> None:
    l = Letter()
    l.letterhead(
        "HRA",
        (150, 90, 0),
        ["NYC Human Resources Administration", "Mail-in Recertification / Eligibility Notice"],
        ["Form SAMPLE-M327", "Date: October 1, 2026"],
    )
    l.box(
        [
            ("Case Name", "Kim, Soon-ja"),
            ("Case Number", "SAMPLE-0001"),
            ("Program", "SNAP"),
        ]
    )
    l.section_header("SNAP Recertification Notice")
    l.body(
        [
            "To determine your continued eligibility for SNAP, you must",
            "answer every question, sign, date, and return this form by:",
        ]
    )
    l.draw.text(
        (MARGIN, l.y), "Due: 2026-11-15", font=_font(24, bold=True), fill=(150, 0, 0)
    )
    l.y += 44
    l.section_header("Please submit:")
    l.checklist(["Proof of income", "Proof of residence", "ID"])
    l.finish("hra_snap_renewal_notice_sample.jpg")


def make_medical_bill() -> None:
    l = Letter()
    l.letterhead(
        "QGH",
        (0, 80, 160),
        ["Queens General Hospital", "Billing Statement"],
        ["Statement date: Oct 5, 2026", "Account: SAMPLE-0001"],
    )
    l.address_block(["Patient: Kim, Soon-ja", "123 Northern Blvd, Apt 4B", "Flushing, NY 11354"])
    l.section_header("Your Claims & Costs This Period")
    l.box(
        [
            ("Service", "Annual wellness visit"),
            ("Category", "Copay"),
            ("Total You May Be Billed", "$20.00"),
        ],
        title="Provider: Queens General Hospital",
    )
    l.body(["This is a Medicare claim."])
    l.finish("medical_bill_sample.jpg")


def main() -> None:
    make_ssa_benefit_letter()
    make_bank_statement()
    make_hra_renewal_notice()
    make_medical_bill()


if __name__ == "__main__":
    main()
