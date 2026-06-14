"""PDF visual theme: colors and paragraph styles, instantiated once per palette."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import TYPE_CHECKING, Final

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet

if TYPE_CHECKING:
    from app.models import InvoiceRequest

DEFAULT_PRIMARY_COLOR: Final = "#0F4C81"
DEFAULT_SECONDARY_COLOR: Final = "#EBF2FA"
DEFAULT_TEXT_COLOR: Final = "#1A1A2E"

TEXT_MID: Final = colors.HexColor("#4A4A6A")
TEXT_LIGHT: Final = colors.HexColor("#8A8AAA")
BORDER: Final = colors.HexColor("#D0D8E8")
WHITE: Final = colors.white

ON_PRIMARY_DARK: Final = colors.HexColor("#1A1A2E")

# WCAG 2.1 relative-luminance threshold below which a light background needs
# dark text to keep a >= 4.5:1 contrast ratio (AA) for white text.
CONTRAST_THRESHOLD: Final = 0.179


@dataclass(frozen=True)
class Theme:
    """Resolved PDF color palette for a single document."""

    primary_hex: str = DEFAULT_PRIMARY_COLOR
    secondary_hex: str = DEFAULT_SECONDARY_COLOR
    text_hex: str = DEFAULT_TEXT_COLOR

    @property
    def primary(self) -> colors.Color:
        return colors.HexColor(self.primary_hex)

    @property
    def secondary(self) -> colors.Color:
        return colors.HexColor(self.secondary_hex)

    @property
    def text(self) -> colors.Color:
        return colors.HexColor(self.text_hex)


DEFAULT_THEME: Final = Theme()


def get_theme(request: InvoiceRequest) -> Theme:
    """Resolve the document's color palette from the request, falling back to defaults."""
    custom = request.theme
    if custom is None:
        return DEFAULT_THEME

    return Theme(
        primary_hex=custom.primary_color or DEFAULT_PRIMARY_COLOR,
        secondary_hex=custom.secondary_color or DEFAULT_SECONDARY_COLOR,
        text_hex=custom.text_color or DEFAULT_TEXT_COLOR,
    )


def relative_luminance(hex_color: str) -> float:
    """Compute the WCAG 2.1 relative luminance of a color (0.0 = black, 1.0 = white)."""

    def channel(value: float) -> float:
        return value / 12.92 if value <= 0.03928 else ((value + 0.055) / 1.055) ** 2.4

    color = colors.HexColor(hex_color)
    r, g, b = channel(color.red), channel(color.green), channel(color.blue)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def on_primary_text_color(primary_hex: str) -> colors.Color:
    """Pick white or dark text for legibility on top of `primary_hex`."""
    return ON_PRIMARY_DARK if relative_luminance(primary_hex) > CONTRAST_THRESHOLD else WHITE


@lru_cache(maxsize=32)
def _styles(theme: Theme) -> dict[str, ParagraphStyle]:
    """Build the full stylesheet for a given color palette and cache it."""
    base = getSampleStyleSheet()
    accent = theme.primary
    text_dark = theme.text
    on_primary = on_primary_text_color(theme.primary_hex)

    def s(name: str, **kwargs) -> ParagraphStyle:
        return ParagraphStyle(name, parent=base["Normal"], **kwargs)

    return {
        "doc_type": s("DocType", fontSize=28, textColor=accent, fontName="Helvetica-Bold", leading=32),
        "doc_number": s("DocNumber", fontSize=10, textColor=TEXT_MID, fontName="Helvetica", leading=14),
        "sender_name": s(
            "SenderName",
            fontSize=13,
            textColor=text_dark,
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
        "value": s("Value", fontSize=9.5, textColor=text_dark, fontName="Helvetica", leading=13),
        "value_bold": s(
            "ValueBold", fontSize=9.5, textColor=text_dark, fontName="Helvetica-Bold", leading=13
        ),
        "table_header": s(
            "TableHeader", fontSize=8, textColor=on_primary, fontName="Helvetica-Bold", leading=10
        ),
        "table_cell": s("TableCell", fontSize=9, textColor=text_dark, fontName="Helvetica", leading=12),
        "table_cell_right": s(
            "TableCellRight",
            fontSize=9,
            textColor=text_dark,
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
            textColor=text_dark,
            fontName="Helvetica-Bold",
            leading=12,
            alignment=TA_RIGHT,
        ),
        "grand_label": s(
            "GrandLabel",
            fontSize=11,
            textColor=on_primary,
            fontName="Helvetica-Bold",
            leading=14,
            alignment=TA_RIGHT,
        ),
        "grand_value": s(
            "GrandValue",
            fontSize=13,
            textColor=on_primary,
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
            textColor=text_dark,
            fontName="Helvetica-Oblique",
            leading=14,
            alignment=TA_RIGHT,
        ),
    }


def style(name: str, theme: Theme = DEFAULT_THEME) -> ParagraphStyle:
    """Lookup a cached paragraph style by short name for the given color palette."""
    return _styles(theme)[name]
