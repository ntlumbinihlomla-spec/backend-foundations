from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas


ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "docs" / "csv-report-pilot-one-pager.pdf"
DASHBOARD_IMAGE = ROOT / "frontend" / "assets" / "fiverr-dashboard-screenshot.png"


def draw_wrapped(pdf, text, x, y, width, font="Helvetica", size=10, leading=14):
    words = text.split()
    line = ""
    pdf.setFont(font, size)
    for word in words:
        candidate = f"{line} {word}".strip()
        if pdf.stringWidth(candidate, font, size) <= width:
            line = candidate
            continue
        pdf.drawString(x, y, line)
        y -= leading
        line = word
    if line:
        pdf.drawString(x, y, line)
        y -= leading
    return y


def draw_section(pdf, title, items, x, y, width):
    pdf.setFillColor(colors.HexColor("#0d6f57"))
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(x, y, title)
    y -= 15
    pdf.setFillColor(colors.HexColor("#1b2b39"))
    for item in items:
        pdf.circle(x + 3, y + 4, 2, fill=1, stroke=0)
        y = draw_wrapped(pdf, item, x + 12, y, width - 12, size=9.5, leading=12)
        y -= 2
    return y - 6


def main():
    OUTPUT.parent.mkdir(exist_ok=True)
    pdf = canvas.Canvas(str(OUTPUT), pagesize=A4)
    width, height = A4

    margin = 18 * mm
    x = margin
    y = height - margin
    usable_width = width - (2 * margin)

    pdf.setFillColor(colors.HexColor("#f8f5ee"))
    pdf.rect(0, 0, width, height, fill=1, stroke=0)

    pdf.setFillColor(colors.HexColor("#1b2b39"))
    pdf.setFont("Helvetica-Bold", 24)
    pdf.drawString(x, y, "CSV Source To Client Report Pilot")

    y -= 18
    pdf.setFillColor(colors.HexColor("#0d6f57"))
    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(x, y, "R2,800 fixed pilot | Remote delivery | 3 to 7 days")

    y -= 22
    pdf.setFillColor(colors.HexColor("#1b2b39"))
    y = draw_wrapped(
        pdf,
        "I build a simple dashboard/report flow for SMEs, accountants, bookkeepers, and consultants. "
        "Upload a sanitized CSV or connect a CSV source URL, choose the important numeric column, "
        "then export a clean client-ready report.",
        x,
        y,
        usable_width,
        size=10.5,
        leading=14,
    )

    y -= 8
    left_width = (usable_width / 2) - 8
    right_x = x + left_width + 18
    section_y = y

    left_y = draw_section(
        pdf,
        "Included",
        [
            "CSV upload or source-link setup.",
            "Summary cards for totals, averages, ranges, and row counts.",
            "Batch analytics and contribution bars.",
            "Exportable client-ready report.",
            "One revision after the first delivery.",
        ],
        x,
        section_y,
        left_width,
    )

    right_y = draw_section(
        pdf,
        "What I Need",
        [
            "One sanitized CSV file or CSV source link.",
            "The main column to analyze, such as amount, sales, expenses, revenue, payroll, or profit.",
            "The report name for the client or management team.",
            "Payment confirmation: R2,800 upfront or R1,400 deposit.",
        ],
        right_x,
        section_y,
        left_width,
    )

    y = min(left_y, right_y) - 6
    pdf.setFillColor(colors.HexColor("#1b2b39"))
    pdf.roundRect(x, y - 44, usable_width, 44, 8, fill=0, stroke=1)
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(x + 12, y - 16, "Best fit")
    pdf.setFont("Helvetica", 9.5)
    draw_wrapped(
        pdf,
        "Monthly reports, management accounts, bookkeeping packs, payroll exports, sales reports, "
        "expense analysis, client-facing finance summaries, and CSV cleanup/reporting workflows.",
        x + 12,
        y - 30,
        usable_width - 24,
        size=9.5,
        leading=11,
    )

    image_top = y - 60
    if DASHBOARD_IMAGE.exists():
        image_width = usable_width
        image_height = 92 * mm
        pdf.drawImage(
            str(DASHBOARD_IMAGE),
            x,
            image_top - image_height,
            width=image_width,
            height=image_height,
            preserveAspectRatio=True,
            anchor="c",
            mask="auto",
        )
        y = image_top - image_height - 10
    else:
        y = image_top - 12

    pdf.setFillColor(colors.HexColor("#0d6f57"))
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(x, y, "Next step")
    y -= 15
    pdf.setFillColor(colors.HexColor("#1b2b39"))
    draw_wrapped(
        pdf,
        "Send one sanitized CSV or CSV source link, and I will confirm the pilot scope. "
        "Once payment or deposit is confirmed, I start the dashboard/report setup.",
        x,
        y,
        usable_width,
        size=10,
        leading=13,
    )

    pdf.setFont("Helvetica", 9)
    pdf.setFillColor(colors.HexColor("#5f6d78"))
    pdf.drawRightString(width - margin, margin - 4, "Regards, Hlomla")

    pdf.save()
    print(OUTPUT)


if __name__ == "__main__":
    main()
