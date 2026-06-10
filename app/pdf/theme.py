"""PDF visual theme: colors and paragraph styles, instantiated once."""

from __future__ import annotations

from functools import lru_cache
from typing import Final

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet

ACCENT: Final = colors.HexColor("#0F4C81")
ACCENT_LIGHT: Final = colors.HexColor("#EBF2FA")
TEXT_DARK: Final = colors.HexColor("#1A1A2E")
TEXT_MID: Final = colors.HexColor("#4A4A6A")
TEXT_LIGHT: Final = colors.HexColor("#8A8AAA")
BORDER: Final = colors.HexColor("#D0D8E8")
WHITE: Final = colors.white


@lru_cache(maxsize=1)
def _styles() -> dict[str, ParagraphStyle]:
    """Build the full stylesheet exactly once and cache it."""
    base = getSampleStyleSheet()

    def s(name: str, **kwargs) -> ParagraphStyle:
        return ParagraphStyle(name, parent=base["Normal"], **kwargs)

    return {
        "doc_type": s("DocType", fontSize=28, textColor=ACCENT, fontName="Helvetica-Bold", leading=32),
        "doc_number": s("DocNumber", fontSize=10, textColor=TEXT_MID, fontName="Helvetica", leading=14),
        "sender_name": s(
            "SenderName",
            fontSize=13,
            textColor=TEXT_DARK,
            fontName="Helvetica-Bold",
            leading=16,
            alignment=TA_RIGHT,
        ),
        "sender_detail": s(
            "SenderDetail",
            fontSize=8.5,
            textColor=TEXT_MID,
            fontName="Helvetica",
            leading=12,
            alignment=TA_RIGHT,
        ),
        "label": s(
            "Label", fontSize=7.5, textColor=TEXT_LIGHT, fontName="Helvetica-Bold", leading=10, spaceBefore=4
        ),
        "value": s("Value", fontSize=9.5, textColor=TEXT_DARK, fontName="Helvetica", leading=13),
        "value_bold": s(
            "ValueBold", fontSize=9.5, textColor=TEXT_DARK, fontName="Helvetica-Bold", leading=13
        ),
        "table_header": s("TableHeader", fontSize=8, textColor=WHITE, fontName="Helvetica-Bold", leading=10),
        "table_cell": s("TableCell", fontSize=9, textColor=TEXT_DARK, fontName="Helvetica", leading=12),
        "table_cell_right": s(
            "TableCellRight",
            fontSize=9,
            textColor=TEXT_DARK,
            fontName="Helvetica",
            leading=12,
            alignment=TA_RIGHT,
        ),
        "totals_label": s(
            "TotalsLabel",
            fontSize=9,
            textColor=TEXT_MID,
            fontName="Helvetica",
            leading=12,
            alignment=TA_RIGHT,
        ),
        "totals_value": s(
            "TotalsValue",
            fontSize=9,
            textColor=TEXT_DARK,
            fontName="Helvetica-Bold",
            leading=12,
            alignment=TA_RIGHT,
        ),
        "grand_label": s(
            "GrandLabel",
            fontSize=11,
            textColor=WHITE,
            fontName="Helvetica-Bold",
            leading=14,
            alignment=TA_RIGHT,
        ),
        "grand_value": s(
            "GrandValue",
            fontSize=13,
            textColor=WHITE,
            fontName="Helvetica-Bold",
            leading=16,
            alignment=TA_RIGHT,
        ),
        "notes_label": s(
            "NotesLabel", fontSize=8, textColor=TEXT_LIGHT, fontName="Helvetica-Bold", leading=10
        ),
        "notes_text": s("NotesText", fontSize=9, textColor=TEXT_MID, fontName="Helvetica", leading=13),
        "footer": s(
            "Footer",
            fontSize=7.5,
            textColor=TEXT_LIGHT,
            fontName="Helvetica",
            leading=10,
            alignment=TA_CENTER,
        ),
        "signature_text": s(
            "SignatureText",
            fontSize=11,
            textColor=TEXT_DARK,
            fontName="Helvetica-Oblique",
            leading=14,
            alignment=TA_RIGHT,
        ),
    }


def style(name: str) -> ParagraphStyle:
    """Lookup a cached paragraph style by short name."""
    return _styles()[name]
