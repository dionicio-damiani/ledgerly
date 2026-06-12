"""PDF builder split into small composable helpers.

The public surface is :func:`build_pdf`. Every other function is private and
returns ReportLab Flowables for a single section of the document.
"""

from __future__ import annotations

import base64
import io
from decimal import Decimal
from typing import TYPE_CHECKING

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.platypus import (
    HRFlowable,
    Image,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.config import APP_NAME, CURRENCIES
from app.exceptions import PDFGenerationError
from app.pdf.theme import (
    BORDER,
    Theme,
    get_theme,
    style,
)
from app.services.totals import compute_totals

if TYPE_CHECKING:
    from app.models import InvoiceRequest, LineItem

USABLE_WIDTH = A4[0] - 36 * mm


def _fmt(amount: Decimal, symbol: str) -> str:
    return f"{symbol}{amount:,.2f}"


def _fmt_qty(qty: Decimal) -> str:
    """Render a quantity without trailing zeros for whole numbers."""
    normalized = qty.normalize()
    s = format(normalized, "f")
    return s.rstrip("0").rstrip(".") if "." in s else s


def _decode_image_data_url(data_url: str, max_width: float, max_height: float) -> Image:
    """Decode a `data:image/...;base64,...` URL into a sized ReportLab Image.

    The image is scaled to fit within ``max_width`` x ``max_height`` (points)
    while preserving its aspect ratio.
    """
    _, _, b64data = data_url.partition(",")
    raw = base64.b64decode(b64data)
    buf = io.BytesIO(raw)
    reader = ImageReader(buf)
    iw, ih = reader.getSize()
    scale = min(max_width / iw, max_height / ih)
    buf.seek(0)
    return Image(buf, width=iw * scale, height=ih * scale)


def _build_logo(sender_logo: str) -> list:
    img = _decode_image_data_url(sender_logo, max_width=120, max_height=60)
    img.hAlign = "LEFT"
    return [img, Spacer(1, 4 * mm)]


def _build_header(req: InvoiceRequest, theme: Theme) -> Table:
    left = [
        Paragraph(req.doc_type.upper(), style("doc_type", theme)),
        Paragraph(f"# {req.doc_number}", style("doc_number", theme)),
    ]
    right = [Paragraph(req.sender_name, style("sender_name", theme))]
    if req.sender_email:
        right.append(Paragraph(req.sender_email, style("sender_detail", theme)))
    if req.sender_phone:
        right.append(Paragraph(req.sender_phone, style("sender_detail", theme)))
    if req.sender_address:
        for line in req.sender_address.split("\n"):
            if line.strip():
                right.append(Paragraph(line.strip(), style("sender_detail", theme)))

    table = Table([[left, right]], colWidths=[USABLE_WIDTH * 0.55, USABLE_WIDTH * 0.45])
    table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    return table


def _build_billing_block(req: InvoiceRequest, symbol: str, theme: Theme) -> Table:
    bill_to = [
        Paragraph("BILL TO", style("label", theme)),
        Paragraph(req.client_name, style("value_bold", theme)),
    ]
    if req.client_company:
        bill_to.append(Paragraph(req.client_company, style("value", theme)))
    if req.client_email:
        bill_to.append(Paragraph(req.client_email, style("value", theme)))
    if req.client_address:
        for line in req.client_address.split("\n"):
            if line.strip():
                bill_to.append(Paragraph(line.strip(), style("value", theme)))

    dates = [
        Paragraph("ISSUE DATE", style("label", theme)),
        Paragraph(req.issue_date.isoformat(), style("value", theme)),
    ]
    if req.due_date:
        dates.append(Paragraph("DUE DATE", style("label", theme)))
        dates.append(Paragraph(req.due_date.isoformat(), style("value", theme)))
    dates.append(Paragraph("CURRENCY", style("label", theme)))
    dates.append(Paragraph(f"{req.currency} ({symbol})", style("value", theme)))

    table = Table([[bill_to, dates]], colWidths=[USABLE_WIDTH * 0.6, USABLE_WIDTH * 0.4])
    table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BACKGROUND", (0, 0), (-1, -1), theme.secondary),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("ROUNDEDCORNERS", [4, 4, 4, 4]),
            ]
        )
    )
    return table


def _build_items_table(items: list[LineItem], symbol: str, theme: Theme) -> Table:
    col_widths = [USABLE_WIDTH * 0.46, USABLE_WIDTH * 0.12, USABLE_WIDTH * 0.18, USABLE_WIDTH * 0.18]

    rows = [
        [
            Paragraph("DESCRIPTION", style("table_header", theme)),
            Paragraph("QTY", style("table_header", theme)),
            Paragraph("UNIT PRICE", style("table_header", theme)),
            Paragraph("TOTAL", style("table_header", theme)),
        ]
    ]
    for item in items:
        rows.append(
            [
                Paragraph(item.description, style("table_cell", theme)),
                Paragraph(_fmt_qty(item.quantity), style("table_cell", theme)),
                Paragraph(_fmt(item.unit_price, symbol), style("table_cell_right", theme)),
                Paragraph(_fmt(item.total, symbol), style("table_cell_right", theme)),
            ]
        )

    table = Table(rows, colWidths=col_widths, repeatRows=1)
    row_count = len(rows)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), theme.primary),
                ("TOPPADDING", (0, 0), (-1, 0), 7),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 7),
                ("LEFTPADDING", (0, 0), (-1, 0), 8),
                ("RIGHTPADDING", (0, 0), (-1, 0), 8),
                ("TOPPADDING", (0, 1), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 1), (-1, -1), 7),
                ("LEFTPADDING", (0, 1), (-1, -1), 8),
                ("RIGHTPADDING", (0, 1), (-1, -1), 8),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                *[("BACKGROUND", (0, i), (-1, i), theme.secondary) for i in range(2, row_count, 2)],
                ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
                ("LINEBELOW", (0, 0), (-1, -2), 0.5, BORDER),
            ]
        )
    )
    return table


def _build_totals_table(req: InvoiceRequest, symbol: str, totals, theme: Theme) -> Table:
    rows = [
        [
            "",
            Paragraph("SUBTOTAL", style("totals_label", theme)),
            Paragraph(_fmt(totals.subtotal, symbol), style("totals_value", theme)),
        ],
    ]
    if req.discount_percent > 0:
        rows.append(
            [
                "",
                Paragraph(f"DISCOUNT ({req.discount_percent:.1f}%)", style("totals_label", theme)),
                Paragraph(f"- {_fmt(totals.discount_amount, symbol)}", style("totals_value", theme)),
            ]
        )
    if req.tax_rate > 0:
        rows.append(
            [
                "",
                Paragraph(f"TAX ({req.tax_rate:.1f}%)", style("totals_label", theme)),
                Paragraph(_fmt(totals.tax_amount, symbol), style("totals_value", theme)),
            ]
        )

    table = Table(rows, colWidths=[USABLE_WIDTH * 0.52, USABLE_WIDTH * 0.28, USABLE_WIDTH * 0.20])
    table.setStyle(
        TableStyle(
            [
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LINEABOVE", (1, 0), (-1, 0), 0.5, BORDER),
            ]
        )
    )
    return table


def _build_grand_total_banner(req: InvoiceRequest, symbol: str, grand_total: Decimal, theme: Theme) -> Table:
    label = "TOTAL DUE" if req.doc_type == "Invoice" else "TOTAL"
    table = Table(
        [
            [
                "",
                Paragraph(label, style("grand_label", theme)),
                Paragraph(_fmt(grand_total, symbol), style("grand_value", theme)),
            ]
        ],
        colWidths=[USABLE_WIDTH * 0.52, USABLE_WIDTH * 0.28, USABLE_WIDTH * 0.20],
    )
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), theme.primary),
                ("TOPPADDING", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ROUNDEDCORNERS", [4, 4, 4, 4]),
            ]
        )
    )
    return table


def _build_notes(notes: str, theme: Theme) -> list:
    return [
        Spacer(1, 6 * mm),
        HRFlowable(width=USABLE_WIDTH, thickness=0.5, color=BORDER),
        Spacer(1, 3 * mm),
        Paragraph("NOTES", style("notes_label", theme)),
        Spacer(1, 1 * mm),
        Paragraph(notes, style("notes_text", theme)),
    ]


def _build_signature(req: InvoiceRequest, theme: Theme) -> list:
    right_width = USABLE_WIDTH * 0.4
    left_width = USABLE_WIDTH - right_width

    if req.signature_image:
        cell = _decode_image_data_url(req.signature_image, max_width=160, max_height=80)
        line_style: list = []
    elif req.signature_text:
        cell = Paragraph(req.signature_text, style("signature_text", theme))
        line_style = [("LINEABOVE", (1, 0), (1, 0), 0.75, BORDER)]
    else:
        return []

    table = Table([["", cell]], colWidths=[left_width, right_width])
    table.setStyle(
        TableStyle(
            [
                ("ALIGN", (1, 0), (1, 0), "RIGHT"),
                ("VALIGN", (0, 0), (-1, -1), "BOTTOM"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                *line_style,
            ]
        )
    )
    return [Spacer(1, 10 * mm), table]


def _build_footer(req: InvoiceRequest, theme: Theme) -> list:
    return [
        Spacer(1, 8 * mm),
        HRFlowable(width=USABLE_WIDTH, thickness=0.5, color=BORDER),
        Spacer(1, 2 * mm),
        Paragraph(
            f"Generated with {APP_NAME} \u00b7 {req.doc_type} #{req.doc_number}",
            style("footer", theme),
        ),
    ]


def build_pdf(request: InvoiceRequest) -> bytes:
    """Render the invoice/quote as a PDF and return its bytes.

    Raises:
        PDFGenerationError: if anything inside ReportLab fails.
    """
    try:
        symbol = CURRENCIES[request.currency]
        totals = compute_totals(request)
        theme = get_theme(request)

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            leftMargin=18 * mm,
            rightMargin=18 * mm,
            topMargin=14 * mm,
            bottomMargin=14 * mm,
            title=f"{request.doc_type} {request.doc_number}",
            author=request.sender_name,
        )

        story: list = []
        if request.sender_logo:
            story.extend(_build_logo(request.sender_logo))

        story += [
            _build_header(request, theme),
            Spacer(1, 5 * mm),
            HRFlowable(width=USABLE_WIDTH, thickness=1.5, color=theme.primary, spaceAfter=5 * mm),
            _build_billing_block(request, symbol, theme),
            Spacer(1, 6 * mm),
            _build_items_table(request.items, symbol, theme),
            Spacer(1, 4 * mm),
            _build_totals_table(request, symbol, totals, theme),
            Spacer(1, 2 * mm),
            _build_grand_total_banner(request, symbol, totals.grand_total, theme),
        ]
        if request.notes:
            story.extend(_build_notes(request.notes, theme))
        story.extend(_build_signature(request, theme))
        story.extend(_build_footer(request, theme))

        doc.build(story)
        buffer.seek(0)
        return buffer.read()
    except PDFGenerationError:
        raise
    except Exception as exc:
        raise PDFGenerationError(str(exc)) from exc
