"""
PDF ticket generation using ReportLab.
Produces a branded A5 ticket with QR code.
"""
import io
import logging
from pathlib import Path

import qrcode
from django.conf import settings
from django.core.files.base import ContentFile
from reportlab.lib import colors
from reportlab.lib.pagesizes import A5
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.platypus import Image, Paragraph

from apps.orders.models import Ticket

logger = logging.getLogger(__name__)

BRAND_COLOR = colors.HexColor("#1A1A2E")
ACCENT_COLOR = colors.HexColor("#E94560")
LIGHT_GRAY = colors.HexColor("#F4F4F8")

PAGE_W, PAGE_H = A5

# Встроенные шрифты ReportLab (Helvetica и т.п.) не содержат кириллицу —
# русский текст рисовался квадратиками. Регистрируем DejaVu Sans, в котором
# кириллица есть, и используем его вместо Helvetica везде в этом модуле.
FONT_REGULAR = "DejaVuSans"
FONT_BOLD = "DejaVuSans-Bold"

_FONTS_DIR = Path(settings.BASE_DIR) / "static" / "fonts"
if FONT_REGULAR not in pdfmetrics.getRegisteredFontNames():
    pdfmetrics.registerFont(TTFont(FONT_REGULAR, _FONTS_DIR / "DejaVuSans.ttf"))
    pdfmetrics.registerFont(TTFont(FONT_BOLD, _FONTS_DIR / "DejaVuSans-Bold.ttf"))
    pdfmetrics.registerFontFamily(FONT_REGULAR, normal=FONT_REGULAR, bold=FONT_BOLD)


def generate_pdf(ticket: Ticket) -> None:
    """Render PDF, store in ticket.pdf_file."""
    order = ticket.order
    customer = order.customer
    event = order.ticket_type.event

    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A5)
    c.setTitle(f"Билет {ticket.ticket_number}")

    # ── Background ────────────────────────────────────────────────
    c.setFillColor(BRAND_COLOR)
    c.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)

    # ── Header stripe ─────────────────────────────────────────────
    c.setFillColor(ACCENT_COLOR)
    c.rect(0, PAGE_H - 30 * mm, PAGE_W, 30 * mm, fill=1, stroke=0)

    c.setFillColor(colors.white)
    c.setFont(FONT_BOLD, 18)
    c.drawCentredString(PAGE_W / 2, PAGE_H - 18 * mm, settings.SITE_NAME.upper())

    # ── Event title ───────────────────────────────────────────────
    c.setFont(FONT_BOLD, 14)
    c.setFillColor(colors.white)
    _draw_wrapped(c, event.title, PAGE_W / 2, PAGE_H - 42 * mm, 12, PAGE_W - 20 * mm)

    # ── Event details ─────────────────────────────────────────────
    c.setFont(FONT_REGULAR, 10)
    c.setFillColor(LIGHT_GRAY)
    y = PAGE_H - 60 * mm
    details = [
        f"Дата: {event.starts_at.strftime('%d.%m.%Y  %H:%M')}",
        f"Место: {event.venue_name}",
        f"Адрес: {event.venue_address}",
    ]
    for line in details:
        c.drawCentredString(PAGE_W / 2, y, line)
        y -= 6 * mm

    # ── Divider ───────────────────────────────────────────────────
    c.setStrokeColor(ACCENT_COLOR)
    c.setLineWidth(0.5)
    c.setDash(3, 3)
    c.line(10 * mm, y - 3 * mm, PAGE_W - 10 * mm, y - 3 * mm)
    c.setDash()
    y -= 8 * mm

    # ── Buyer info ────────────────────────────────────────────────
    c.setFont(FONT_BOLD, 10)
    c.setFillColor(colors.white)
    c.drawString(10 * mm, y, customer.full_name)
    y -= 5 * mm

    c.setFont(FONT_REGULAR, 9)
    c.setFillColor(LIGHT_GRAY)
    c.drawString(10 * mm, y, f"Тип: {order.ticket_type.name}")
    y -= 5 * mm
    c.drawString(10 * mm, y, f"Заказ: {order.order_number}")
    y -= 5 * mm
    c.drawString(10 * mm, y, f"Билет: {ticket.ticket_number}")

    # ── QR Code ───────────────────────────────────────────────────
    qr_img = _make_qr_image(ticket.get_qr_data(), size=35 * mm)
    qr_x = PAGE_W - 45 * mm
    qr_y = y - 25 * mm
    c.drawImage(qr_img, qr_x, qr_y, 35 * mm, 35 * mm)

    # Verify code below QR
    c.setFont(FONT_BOLD, 8)
    c.setFillColor(LIGHT_GRAY)
    c.drawCentredString(qr_x + 17.5 * mm, qr_y - 5 * mm, ticket.verify_code)

    # ── Footer ────────────────────────────────────────────────────
    c.setFillColor(ACCENT_COLOR)
    c.rect(0, 0, PAGE_W, 10 * mm, fill=1, stroke=0)
    c.setFont(FONT_REGULAR, 7)
    c.setFillColor(colors.white)
    c.drawCentredString(PAGE_W / 2, 3.5 * mm, f"ЭЛЕКТРОННЫЙ БИЛЕТ • {settings.SITE_NAME}")

    c.save()

    buffer.seek(0)
    file_name = f"ticket_{ticket.ticket_number}.pdf"
    ticket.pdf_file.save(file_name, ContentFile(buffer.read()), save=True)
    logger.info("pdf_generated", extra={"ticket_number": ticket.ticket_number})


def _make_qr_image(data: str, size: float):
    """Return a ReportLab-compatible ImageReader from QR data."""
    from reportlab.lib.utils import ImageReader

    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=2,
    )
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return ImageReader(buf)


def _draw_wrapped(c, text: str, x: float, y: float, font_size: int, max_width: float):
    """Naive word-wrap for canvas.drawString."""
    c.setFont(FONT_BOLD, font_size)
    words = text.split()
    line = ""
    for word in words:
        test = f"{line} {word}".strip()
        if c.stringWidth(test, FONT_BOLD, font_size) <= max_width:
            line = test
        else:
            c.drawCentredString(x, y, line)
            y -= font_size * 1.4
            line = word
    if line:
        c.drawCentredString(x, y, line)
