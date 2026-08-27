"""Read-only report queries and CSV/PDF rendering for the shared database."""
import csv
from datetime import timedelta
from decimal import Decimal
from io import BytesIO

from django.db import connection
from django.http import HttpResponse
from django.utils import timezone


PERIODS = {"today": 0, "yesterday": 1, "7d": 6, "30d": 29, "3m": 89, "12m": 364}


def report_range(request):
    today = timezone.localdate()
    period = request.GET.get("period", "30d")
    if period == "custom":
        try:
            start = timezone.datetime.fromisoformat(request.GET["start"]).date()
            end = timezone.datetime.fromisoformat(request.GET["end"]).date()
            if end >= start:
                return start, end
        except (KeyError, ValueError):
            pass
    end = today - timedelta(days=1) if period == "yesterday" else today
    return end - timedelta(days=PERIODS.get(period, 29)), end


def query_rows(sql, params=()):
    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        columns = [item[0] for item in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]


def order_rows(start, end):
    return query_rows("""
        SELECT o.id, u.name, u.email, o.created_at, o.total_amount,
               LOWER(o.status::text) AS order_status, LOWER(o.payment_status) AS payment_status,
               o.payment_method, p.transaction_id,
               COALESCE(string_agg(pr.name || ' x' || oi.quantity::text, '; ' ORDER BY pr.name), '') AS products
        FROM orders o JOIN users u ON u.id=o.user_id
        LEFT JOIN payments p ON p.order_id=o.id
        LEFT JOIN order_items oi ON oi.order_id=o.id LEFT JOIN products pr ON pr.id=oi.product_id
        WHERE o.created_at::date BETWEEN %s AND %s
        GROUP BY o.id,u.name,u.email,o.created_at,o.total_amount,o.status,o.payment_status,o.payment_method,p.transaction_id
        ORDER BY o.created_at DESC
    """, (start, end))


def sales_rows(start, end):
    return query_rows("""
        SELECT COALESCE(p.paid_at,p.created_at) AS sale_date, o.id, u.name, u.email,
               p.amount, LOWER(p.status::text) AS payment_status, p.provider, p.transaction_id
        FROM payments p JOIN orders o ON o.id=p.order_id JOIN users u ON u.id=o.user_id
        WHERE LOWER(p.status::text)='paid' AND LOWER(o.status::text) NOT IN ('cancelled','canceled')
          AND COALESCE(p.paid_at,p.created_at)::date BETWEEN %s AND %s
        ORDER BY sale_date DESC
    """, (start, end))


def user_rows(start, end):
    return query_rows("""
        SELECT id, name, email, LOWER(role::text) AS role, is_active, created_at
        FROM users WHERE created_at::date BETWEEN %s AND %s ORDER BY created_at DESC
    """, (start, end))


def csv_response(filename, headers, rows):
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    response.write("\ufeff")  # Excel-friendly UTF-8 BOM.
    writer = csv.writer(response)
    writer.writerow(headers)
    writer.writerows(rows)
    return response


def pdf_response(filename, title, headers, rows, summary=()):
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    buffer = BytesIO()
    document = SimpleDocTemplate(buffer, pagesize=landscape(A4), leftMargin=12*mm, rightMargin=12*mm, topMargin=12*mm, bottomMargin=14*mm)
    styles = getSampleStyleSheet()
    content = [Paragraph("SMART E-COMMERCE", styles["Title"]), Paragraph(title, styles["Heading2"]), Paragraph(f"Generated: {timezone.localtime():%d-%m-%Y %H:%M}", styles["Normal"]), Spacer(1, 8)]
    for line in summary:
        content.append(Paragraph(line, styles["Normal"]))
    if summary:
        content.append(Spacer(1, 8))
    table_data = [headers] + [[Paragraph(str(value or "-"), styles["BodyText"]) for value in row] for row in rows]
    widths = [260 / len(headers) * mm] * len(headers)
    table = Table(table_data, colWidths=widths, repeatRows=1)
    table.setStyle(TableStyle([("BACKGROUND", (0,0), (-1,0), colors.HexColor("#155e75")), ("TEXTCOLOR", (0,0), (-1,0), colors.white), ("GRID", (0,0), (-1,-1), .25, colors.HexColor("#cbd5e1")), ("VALIGN", (0,0), (-1,-1), "TOP"), ("FONTSIZE", (0,0), (-1,-1), 7), ("BOTTOMPADDING", (0,0), (-1,0), 7), ("TOPPADDING", (0,1), (-1,-1), 5), ("BOTTOMPADDING", (0,1), (-1,-1), 5)]))
    content.append(table)
    document.build(content, onFirstPage=_page_number, onLaterPages=_page_number)
    response = HttpResponse(buffer.getvalue(), content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


def _page_number(canvas, document):
    canvas.setFont("Helvetica", 8)
    canvas.drawRightString(document.pagesize[0] - 12 * 2.83465, 8 * 2.83465, f"Page {document.page}")
