"""
PDF report matching DYNAMIC SOLUTION sample valuation reports (structure + B-K-D + seal).
Optional logo: place logo.png in backend/static/logo.png
"""

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, HRFlowable, Flowable, Image, KeepTogether
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from reportlab.pdfgen import canvas
from reportlab.graphics.shapes import Drawing, Circle, String, Line
from reportlab.graphics import renderPDF
from io import BytesIO
from typing import Dict, Any, List
import os

GOLD = colors.HexColor("#C9A227")
NAVY = colors.HexColor("#1a365d")
LIGHT_GOLD = colors.HexColor("#FFF3CD")
LIGHT_BLUE = colors.HexColor("#E8F4FD")
SOFT = colors.HexColor("#F7FAFC")
DARK = colors.HexColor("#2D3748")
BLUE_BAR = colors.HexColor("#1e3a5f")

SQM_PER_DHUR = 16.93
SQM_PER_KATTHA = 338.63


def sqm_to_sft(sqm: float) -> float:
    return sqm * 10.7639


def sqm_to_kattha(sqm: float) -> float:
    return sqm / SQM_PER_KATTHA


def sqm_to_bkd(sqm: float) -> str:
    if abs(sqm) < 0.001:
        return "0-0-0"
    b = int(sqm // 6772.6)
    rem = sqm % 6772.6
    k = int(rem // SQM_PER_KATTHA)
    d = round((rem % SQM_PER_KATTHA) / SQM_PER_DHUR, 2)
    return f"{b}-{k}-{d}"


def area_row(label: str, sqm: float) -> List:
    return [
        label,
        f"{sqm:.2f}",
        f"{sqm_to_sft(sqm):.2f}",
        f"{sqm_to_kattha(sqm):.3f}",
        sqm_to_bkd(sqm),
    ]


class CompanySeal(Flowable):
    """Circular company seal matching sample reports."""
    def __init__(self, size=55):
        Flowable.__init__(self)
        self.size = size
        self.width = size
        self.height = size

    def draw(self):
        c = self.canv
        cx, cy = self.size / 2, self.size / 2
        r = self.size / 2 - 2
        c.setStrokeColor(NAVY)
        c.setLineWidth(1.5)
        c.circle(cx, cy, r)
        c.setLineWidth(0.8)
        c.circle(cx, cy, r - 4)
        c.setFillColor(NAVY)
        c.setFont("Helvetica-Bold", 5.5)
        c.drawCentredString(cx, cy + 8, "DYNAMIC")
        c.drawCentredString(cx, cy + 1, "SOLUTION")
        c.setFont("Helvetica", 4.5)
        c.drawCentredString(cx, cy - 8, "PVT. LTD.")
        c.setFont("Helvetica", 3.5)
        c.drawCentredString(cx, cy - 14, "JHAPA")


def make_logo_flowable():
    """Prefer static/logo.png if present, else drawn seal."""
    logo_path = os.path.join(os.path.dirname(__file__), "static", "logo.png")
    if os.path.isfile(logo_path):
        try:
            return Image(logo_path, width=22*mm, height=22*mm)
        except Exception:
            pass
    return CompanySeal(size=55)


def styles():
    s = getSampleStyleSheet()
    s.add(ParagraphStyle(name="MainTitle", fontName="Helvetica-Bold", fontSize=13,
                         alignment=TA_CENTER, textColor=NAVY, spaceAfter=3))
    s.add(ParagraphStyle(name="SectionTitle", fontName="Helvetica-Bold", fontSize=11,
                         alignment=TA_CENTER, textColor=NAVY, spaceBefore=4, spaceAfter=3))
    s.add(ParagraphStyle(name="H2", fontName="Helvetica-Bold", fontSize=9.5,
                         textColor=NAVY, spaceBefore=6, spaceAfter=2))
    s.add(ParagraphStyle(name="Body", fontName="Helvetica", fontSize=8, leading=10.5))
    s.add(ParagraphStyle(name="BodyJ", fontName="Helvetica", fontSize=8, leading=10.5, alignment=TA_JUSTIFY))
    s.add(ParagraphStyle(name="Small", fontName="Helvetica", fontSize=7, leading=9))
    s.add(ParagraphStyle(name="Bold", fontName="Helvetica-Bold", fontSize=8, leading=10.5))
    s.add(ParagraphStyle(name="CenterVal", fontName="Helvetica-Bold", fontSize=10,
                         alignment=TA_CENTER, spaceBefore=2, spaceAfter=1))
    s.add(ParagraphStyle(name="Words", fontName="Helvetica-Oblique", fontSize=7.5,
                         alignment=TA_CENTER, textColor=colors.HexColor("#4a5568")))
    s.add(ParagraphStyle(name="FirmHead", fontName="Helvetica-Bold", fontSize=11,
                         alignment=TA_CENTER, textColor=NAVY))
    s.add(ParagraphStyle(name="FirmSub", fontName="Helvetica", fontSize=7,
                         alignment=TA_CENTER, leading=8.5))
    s.add(ParagraphStyle(name="YellowHead", fontName="Helvetica-Bold", fontSize=9,
                         textColor=colors.white))
    s.add(ParagraphStyle(name="Footer", fontName="Helvetica", fontSize=7,
                         alignment=TA_CENTER, textColor=colors.grey))
    return s


def fmt(n):
    try:
        return f"{int(round(n)):,}"
    except Exception:
        return str(n)


def section_bar(text, st):
    data = [[Paragraph(f"<b>{text}</b>", st["YellowHead"])]]
    t = Table(data, colWidths=[186*mm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), GOLD),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    return t


def kv(rows, c1=48*mm, c2=138*mm):
    t = Table(rows, colWidths=[c1, c2])
    t.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME", (1, 0), (1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 7.5),
        ("BACKGROUND", (0, 0), (0, -1), SOFT),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.grey),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 1.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1.5),
    ]))
    return t


def header_block(st, firm, logo):
    left = [
        [Paragraph(f"<b>{firm.get('firm_name', 'DYNAMIC SOLUTION PVT. LTD.')}</b>", st["FirmHead"])],
        [Paragraph(firm.get("firm_address", ""), st["FirmSub"])],
        [Paragraph(
            f"Regd. No. {firm.get('firm_reg_no', '')}  |  PAN: {firm.get('firm_pan', '')}  |  "
            f"{firm.get('firm_email', '')}  |  {firm.get('firm_phone', '')}",
            st["FirmSub"]
        )],
    ]
    left_t = Table(left, colWidths=[155*mm])
    data = [[left_t, logo]]
    t = Table(data, colWidths=[160*mm, 26*mm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), LIGHT_BLUE),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BOX", (0, 0), (-1, -1), 1, NAVY),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    return t


def area_table(pout, st):
    """Full area calculation with B-K-D on every row (matches sample)."""
    header = ["Area Calculation", "(In Sqm.)", "(In Sft.)", "(In Katthas)", "B-K-D"]
    rows = [header]
    rows.append(area_row("Area in Lalpurja", pout["lalpurja_sqm"]))
    rows.append(area_row("Area as per Cadastral Map", pout["cadastral_sqm"]))
    rows.append(area_row("Non Valuable Area", 0.0))
    rows.append(area_row("Deduction for ROW/ Road", pout["deducted_sqm"]))
    rows.append(area_row("Area Considered For Valuation", pout["considered_sqm"]))
    # Belt 1
    rows.append(area_row("Belt - 1 Area", pout["belt1_raw"]))
    if pout["apply_land_dev"] and pout["belt1_raw"] > 0:
        rows.append(area_row("15 % on land development", pout["belt1_raw"] * 0.15))
        rows.append(area_row("Net Area Considered For Valuation", pout["belt1_net"]))
    else:
        rows.append(area_row("0 % on land development", 0.0))
        rows.append(area_row("Net Area Considered For Valuation", pout["belt1_net"]))
    # Belt 2
    rows.append(area_row("Belt - 2 Area", pout["belt2_raw"]))
    if pout["apply_land_dev"] and pout["belt2_raw"] > 0:
        rows.append(area_row("15 % on land development", pout["belt2_raw"] * 0.15))
        rows.append(area_row("Net Area Considered For Valuation", pout["belt2_net"]))
    else:
        rows.append(area_row("0 % on land development", 0.0))
        rows.append(area_row("Net Area Considered For Valuation", pout["belt2_net"]))
    # Belt 3
    rows.append(area_row("Belt - 3 Area", pout["belt3_raw"]))
    if pout["apply_land_dev"] and pout["belt3_raw"] > 0:
        rows.append(area_row("15 % on land development", pout["belt3_raw"] * 0.15))
        rows.append(area_row("Net Area Considered For Valuation", pout["belt3_net"]))
    else:
        rows.append(area_row("0 % on land development", 0.0))
        rows.append(area_row("Net Area Considered For Valuation", pout["belt3_net"]))

    t = Table(rows, colWidths=[58*mm, 28*mm, 28*mm, 28*mm, 28*mm])
    t.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 7),
        ("BACKGROUND", (0, 0), (-1, 0), LIGHT_BLUE),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.grey),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("TOPPADDING", (0, 0), (-1, -1), 1.2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1.2),
        ("LEFTPADDING", (0, 0), (-1, -1), 2),
    ]))
    return t


def add_page_number(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(colors.grey)
    canvas.drawCentredString(A4[0] / 2, 8 * mm, f"DYNAMIC SOLUTION PVT. LTD.    |    Page {doc.page}")
    canvas.restoreState()


def generate_valuation_pdf(data: Dict[str, Any]) -> bytes:
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=12*mm, rightMargin=12*mm,
        topMargin=10*mm, bottomMargin=14*mm
    )
    st = styles()
    story = []
    logo = make_logo_flowable()

    req = data["request"]
    client = req["client"]
    summary = data["summary"]
    plots = data["plots"]
    bank = data["bank"]
    firm = req

    prop_type = "Land & Building" if data["building"]["fmv"] > 0 else "Land"
    plot_nos = " & ".join(p["plot_no"] for p in plots) if len(plots) > 1 else plots[0]["plot_no"]

    # ========== 1. COVER ==========
    story.append(Paragraph("REPORT OF PROPERTY VALUATION OF FIXED ASSETS", st["MainTitle"]))
    story.append(Spacer(1, 3))
    story.append(section_bar("CLIENT", st))
    story.append(kv([
        ["Name", client["client_name"]],
        ["Address as per Citizenship", client["client_address_citizenship"]],
        ["Phone No", client["contact_no"]],
    ]))
    story.append(Spacer(1, 3))
    story.append(section_bar("Property Owner", st))
    story.append(kv([
        ["Name", client["owner_name"]],
        ["Address as per Charkilla", client["owner_address_charkilla"]],
    ]))
    story.append(Spacer(1, 3))
    story.append(section_bar("Property to be valued", st))
    gps_rows = [["Plot No.", plot_nos], ["Address", client["owner_address_charkilla"]]]
    if req.get("gps"):
        gps_rows.append(["GPS Co-ordinate", req["gps"]])
    story.append(kv(gps_rows))
    story.append(Spacer(1, 6))
    story.append(Paragraph("<b>Site Photograph</b>", st["SectionTitle"]))
    story.append(Paragraph("(Attach site photographs here / Annex 3)", st["Words"]))
    story.append(Spacer(1, 8))
    story.append(Paragraph("<b>SUBMITTED TO:</b>", st["SectionTitle"]))
    story.append(Paragraph(f"<b>{req['bank_name']}</b>", st["CenterVal"]))
    story.append(Paragraph(f"Branch Office {req['branch']}", st["Body"]))
    story.append(Spacer(1, 8))
    # Submitted by with logo
    sub = [[
        Paragraph(f"<b>SUBMITTED BY:</b><br/><b>{firm.get('firm_name')}</b><br/>"
                  f"{firm.get('firm_address', '')}<br/>"
                  f"Contact: {firm.get('firm_phone', '')}<br/>"
                  f"EMAIL: {firm.get('firm_email', '')}", st["FirmSub"]),
        logo
    ]]
    t = Table(sub, colWidths=[150*mm, 30*mm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), BLUE_BAR),
        ("TEXTCOLOR", (0, 0), (0, -1), colors.white),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    # Override text color for paragraph inside dark bar - use white style
    story.append(t)

    # ========== 2. TOC ==========
    story.append(PageBreak())
    story.append(Paragraph("<u>Table of Contents</u>", st["MainTitle"]))
    story.append(Spacer(1, 6))
    for line in [
        "1.  Cover Page with Photograph",
        "2.  Table of contents",
        "3.  Valuation Certificate",
        "4.  Summary of Valuation Report",
        "5.  Remarks & Limiting Conditions",
        "6.  Consent & Declaration of Property Owner",
        "7.  Valuator opinion",
        "8.  Valuation of Land",
        "9.  Accessibility & other misc. particular of land",
        "10. Details of Property to be mortgage",
        "11. Legal Status",
        "12. Calculation of Land Area",
        "13. Field Visit Team",
        "14. Annex",
        "     Annex 1  List of Documents used & attached in this valuation report",
        "     Annex 2  DRAWINGS of Land & Site plan Map",
        "     Annex 3  PHOTOGRAPHS",
        "     Annex 4  DOCUMENTS",
    ]:
        story.append(Paragraph(line, st["Body"]))
        story.append(Spacer(1, 1.5))

    # ========== 3. VALUATION CERTIFICATE ==========
    story.append(PageBreak())
    story.append(header_block(st, firm, logo))
    story.append(Spacer(1, 3))
    story.append(Paragraph("<b><u>Valuation Certificate</u></b>", st["SectionTitle"]))
    story.append(Paragraph(f"<b>Date:</b> {req['valuation_date']}", st["Body"]))
    story.append(Paragraph("To,  The Bank Manager", st["Body"]))
    story.append(Paragraph(f"<b>{req['bank_name']}</b> — Branch Office {req['branch']}", st["Bold"]))
    story.append(Paragraph("<b>Subject : Submission of Valuation Report</b>", st["Bold"]))
    story.append(Paragraph(
        "We are submitting the valuation report of the property which is intended to be mortgaged to the bank by the client. "
        "We have taken all care to arrive at the fair market value of the following property as directed by the client.",
        st["BodyJ"]))
    story.append(Spacer(1, 2))
    story.append(kv([
        ["Client", client["client_name"]],
        ["Address as per Citizenship", client["client_address_citizenship"]],
        ["The property consist of", prop_type],
        ["Plot No", plot_nos],
        ["Owner of Property", client["owner_name"]],
        ["Address of Owner as per Charkilla", client["owner_address_charkilla"]],
        ["Address as Per citizenship", client["owner_address_citizenship"]],
        ["Citizenship No. & Date of issue", f"{client['owner_citizenship_no']}  &  {client['owner_citizenship_date']}"],
        ["Land Address as Per Dhanipurja", client["owner_address_dhanipurja"]],
        ["Loan Types", req.get("loan_type", "Education Loan Only")],
        ["GPS Co-ordinate", req.get("gps") or "-"],
        ["Field Visit Date", req["field_visit_date"]],
        ["Agreement Date", req.get("agreement_date", "")],
    ], 52*mm, 134*mm))
    story.append(Spacer(1, 3))

    # Property area summary
    story.append(Paragraph("<b>Property Area Summary</b>", st["H2"]))
    h = ["S.No.", "Type", "Location", "Owner", "Plot", "Cadastral", "Lalpurja", "Net sq.m", "Remarks"]
    rows = [h]
    for i, (pin, pout) in enumerate(zip(req["plots"], plots), 1):
        rows.append([
            str(i), "Land", client["owner_address_charkilla"][:22],
            client["owner_name"][:16], pout["plot_no"],
            f"{pout['cadastral_sqm']:.2f}", f"{pout['lalpurja_sqm']:.2f}",
            f"{pout['net_sqm']:.2f}", pin.get("ownership_type", "Single") + " Ownership",
        ])
    t = Table(rows, colWidths=[10*mm, 12*mm, 36*mm, 28*mm, 14*mm, 18*mm, 18*mm, 18*mm, 28*mm])
    t.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 6.5),
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.grey),
        ("ALIGN", (5, 1), (7, -1), "RIGHT"),
        ("TOPPADDING", (0, 0), (-1, -1), 1.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1.5),
    ]))
    story.append(t)
    story.append(Spacer(1, 3))

    # Belting rates
    story.append(Paragraph("<b>Belting & Weighted Rates (70% MR + 30% GR)</b>", st["H2"]))
    bh = ["Belt", "Net Area", "Plot", "Market Rate", "Govt Rate", "FMV Rate", "Unit"]
    brows = [bh]
    for pout in plots:
        for belt, net, rate in [(1, pout["belt1_net"], pout["rate1"]),
                                (2, pout["belt2_net"], pout["rate2"]),
                                (3, pout["belt3_net"], pout["rate3"])]:
            if net > 0.01 or belt == 1:
                brows.append([str(belt), f"{net:.2f}", pout["plot_no"],
                              f"{pout['market_per_sqm']:,.2f}", f"{pout['govt_per_sqm']:,.2f}",
                              f"{rate:,.2f}", "Sq.M."])
    t = Table(brows, colWidths=[12*mm, 24*mm, 20*mm, 30*mm, 28*mm, 30*mm, 18*mm])
    t.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 6.5),
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.grey),
        ("ALIGN", (1, 1), (-2, -1), "RIGHT"),
        ("TOPPADDING", (0, 0), (-1, -1), 1.2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1.2),
    ]))
    story.append(t)
    story.append(Spacer(1, 3))

    story.append(Paragraph("<b>We hereby clarify and declare that:</b>", st["Bold"]))
    for d in [
        f"1. Valuation carried out as per agreement with the bank dated: {req.get('agreement_date', '')}",
        f"2. Physically inspected, verified, photographed & measured on {req['field_visit_date']}",
        "3. No direct or indirect interest in the said property or the client.",
        "4. Bank may inspect the property and reserves the right to accept or reject this report.",
        "5. Valuation for establishing Fair Market value for mortgaging purpose.",
        "6. Firm is fully authorized under prevalent laws and competent to carry out valuation.",
        "7. Valuation guidelines of the bank have been fully complied with.",
        "8. Belting carried out: Belt-2 = 66% of Belt-1 market rate; Belt-3 = 50% of Belt-1 market rate.",
        "9. Area more than 508.737 sq.m → 15% deduction for land development (where applicable).",
    ]:
        story.append(Paragraph(d, st["Small"]))

    story.append(Spacer(1, 3))
    story.append(Paragraph("<b>Summary of the Valuation</b>", st["H2"]))
    story.append(kv([
        ["1. Fair Market value of the land FMV (Rs)", f"=  {fmt(summary['land_fmv'])}"],
        ["2. Market value of the land MV (Rs)", f"=  {fmt(summary.get('land_mv', 0))}"],
        ["3. Fair market value of the building (Rs)", f"=  {fmt(summary['building_fmv']) if summary['building_fmv'] else '-'}"],
        ["4. Total fair market value (Rs)", f"=  {fmt(summary['total_fmv'])}"],
        ["Total distress value (Rs)", f"=  {fmt(summary['total_distress'])}"],
    ], 85*mm, 70*mm))
    story.append(Paragraph(f"<i>Distress value in words: {summary['distress_words']}</i>", st["Words"]))
    story.append(Spacer(1, 6))
    story.append(Paragraph("Sincerely Yours", st["Body"]))
    story.append(Spacer(1, 10))
    story.append(Paragraph(f"<b>{req.get('valuator_name', 'Er. Yogesh Bhattarai')}</b>", st["Bold"]))
    story.append(Paragraph(req.get("valuator_nec", 'NEC No. 14163 civil "A"'), st["Small"]))

    # ========== 4. SUMMARY OF VALUATION REPORT ==========
    story.append(PageBreak())
    story.append(Paragraph("<b>SUMMARY OF VALUATION REPORT</b>", st["MainTitle"]))
    story.append(HRFlowable(width="100%", thickness=1, color=NAVY))
    story.append(Paragraph("<b>1. Information of Client</b>", st["H2"]))
    story.append(kv([
        ["Plot No", plot_nos],
        ["Name of client", client["client_name"]],
        ["Address as per Citizenship", client["client_address_citizenship"]],
        ["Name of Property Owner", client["owner_name"]],
        ["Relation", client["relationship"]],
        ["Location as Per Charkilla", client["owner_address_charkilla"]],
    ]))
    story.append(Paragraph(f"<b>2. Type of Property Valuated:</b>  {prop_type}", st["H2"]))
    story.append(Paragraph("<b>3. Particulars of Land : Area Calculation</b>", st["H2"]))

    for pin, pout in zip(req["plots"], plots):
        story.append(Paragraph(
            f"<b>Plot No. {pout['plot_no']}</b> — Owner: {client['owner_name']} — "
            f"{client['owner_address_charkilla']}", st["Bold"]))
        story.append(area_table(pout, st))
        story.append(Spacer(1, 4))

    # ========== Accessibility & Charkilla ==========
    story.append(Paragraph("<b>4. Accessibility & Other Misc. Particulars of Land</b>", st["H2"]))
    acc = [["S.No", "Plot No.", "Importance", "Access at Site", "Frontage"]]
    for i, pin in enumerate(req["plots"], 1):
        acc.append([str(i), pin["plot_no"], pin.get("importance", "Residential"),
                    pin.get("road_width", "") or pin.get("road_type", ""),
                    pin.get("frontage", "")[:40]])
    t = Table(acc, colWidths=[12*mm, 22*mm, 28*mm, 65*mm, 55*mm])
    t.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 7),
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.grey),
        ("TOPPADDING", (0, 0), (-1, -1), 1.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1.5),
    ]))
    story.append(t)

    story.append(Paragraph("<b>5. Four Boundaries of Land (Charkilla)</b>", st["H2"]))
    b = [["S.No", "Plot", "East", "West", "North", "South"]]
    for i, pin in enumerate(req["plots"], 1):
        b.append([str(i), pin["plot_no"], pin.get("east", "")[:28], pin.get("west", "")[:22],
                  pin.get("north", "")[:22], pin.get("south", "")[:22]])
    t = Table(b, colWidths=[10*mm, 16*mm, 40*mm, 35*mm, 35*mm, 35*mm])
    t.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 6.5),
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.grey),
        ("TOPPADDING", (0, 0), (-1, -1), 1.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1.5),
    ]))
    story.append(t)

    # ========== Weighted rates & FMV tables ==========
    story.append(PageBreak())
    story.append(header_block(st, firm, logo))
    story.append(Paragraph("<b>6. Weighted Rate of Land</b>", st["H2"]))
    wh = ["Belt", "Plot", "Area for val", "FMV RATE", "FMV", "Unit"]
    wrows = [wh]
    for pout in plots:
        for belt, net, rate, fmv in [
            (1, pout["belt1_net"], pout["rate1"], pout["fmv1"]),
            (2, pout["belt2_net"], pout["rate2"], pout["fmv2"]),
            (3, pout["belt3_net"], pout["rate3"], pout["fmv3"]),
        ]:
            if net > 0.01:
                wrows.append([str(belt), pout["plot_no"], f"{net:.2f}", f"{rate:,.2f}", f"{fmv:,.0f}", "Sq.M."])
            else:
                wrows.append([str(belt), pout["plot_no"], "-", f"{rate:,.2f}", "-", "Sq.M."])
    wrows.append(["", "", "Total FMV", "", f"{summary['land_fmv']:,}", ""])
    wrows.append(["", "", "Say Value", "", f"{summary['land_fmv']:,}", ""])
    t = Table(wrows, colWidths=[14*mm, 22*mm, 30*mm, 32*mm, 35*mm, 20*mm])
    t.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME", (0, -2), (-1, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 7),
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("BACKGROUND", (0, -2), (-1, -1), LIGHT_GOLD),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.grey),
        ("ALIGN", (2, 1), (4, -1), "RIGHT"),
        ("TOPPADDING", (0, 0), (-1, -1), 1.2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1.2),
    ]))
    story.append(t)

    story.append(Paragraph("<b>8. Total Distress Value of the Land</b>", st["H2"]))
    story.append(kv([
        ["Land FMV", f"NRs. {fmt(summary['land_fmv'])}"],
        ["Building FMV", f"NRs. {fmt(summary['building_fmv'])}" if summary["building_fmv"] else "-"],
        ["Total FMV", f"NRs. {fmt(summary['total_fmv'])}"],
        ["Distress %", f"{bank['distress_factor']*100:.0f}%"],
        ["Total Distress Value", f"NRs. {fmt(summary['total_distress'])}"],
        ["In words", summary["distress_words"]],
    ]))

    if data["building"]["fmv"] > 0:
        bd = data["building"]["details"]
        story.append(Paragraph("<b>Building Valuation</b>", st["H2"]))
        story.append(kv([
            ["Built-up Area", f"{bd['built_up_sqm']} sq.m / {bd['built_up_sft']} sft"],
            ["Rate", f"NRs. {bd['cost_per_sft']} per sq.ft"],
            ["Type / Storeys", f"{bd['type']} / {bd['storeys']}"],
            ["Year (BS)", bd["year"]],
            ["Building FMV", f"NRs. {fmt(data['building']['fmv'])}"],
        ]))

    # ========== 5. Remarks & Limiting Conditions ==========
    story.append(PageBreak())
    story.append(header_block(st, firm, logo))
    story.append(Paragraph("<b>Special comments</b>", st["H2"]))
    sc = [
        ["1. ROW deducted as per government rules", "Yes"],
        ["2. No danger of flood & land slide", "Yes"],
        ["3. Statements of fact are true and correct", "Yes"],
        ["4. No interest in the transaction of property", "Yes"],
        ["5. Inspection of the property has been done", "Yes"],
        ["6. Building constructed as per approval drawing", "NA" if data["building"]["fmv"] == 0 else "Yes"],
    ]
    t = Table(sc, colWidths=[140*mm, 40*mm])
    t.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.grey),
        ("BACKGROUND", (1, 0), (1, -1), SOFT),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    story.append(t)

    story.append(Paragraph("<b>Remarks & Limiting Conditions</b>", st["H2"]))
    for r in [
        "1. Opinions of value are based upon facts and assumptions identified in this report. The valuer takes no responsibility for changes in market conditions.",
        "2. Stated opinions of value are effective as of the date of value. Values may change substantially with time.",
        "3. Property has been only physically checked; no structural design and geotechnical analysis is available.",
        "4. To the best of our knowledge, all matters of factual nature discussed are true and correct.",
        "5. Property has been physically checked to ascertain whether the land in the field tallies with Govt. Survey Map.",
    ]:
        story.append(Paragraph(r, st["Small"]))
        story.append(Spacer(1, 2))

    story.append(Paragraph("<b>Consent & Declaration of the Property Owner</b>", st["H2"]))
    story.append(Paragraph(
        "I hereby declare that all the legal documents provided to the engineer are true, correct and not manipulated. "
        "I also declare that the valuation is acceptable to me regarding the value of my property and other relevant details.",
        st["BodyJ"]))
    story.append(Spacer(1, 12))
    story.append(Paragraph("Signature of the Property Owner: _______________________", st["Body"]))
    story.append(Paragraph(f"Name: {client['owner_name']}", st["Body"]))

    # ========== 7. Valuator opinion + methodology ==========
    story.append(PageBreak())
    story.append(header_block(st, firm, logo))
    story.append(Paragraph("<b>9. Valuator's opinion</b>", st["H2"]))
    story.append(Paragraph(
        "Provided all the remarks on relevant headings are fulfilled. The fair market value of the properties as per "
        "the guidelines of the bank have been proposed after the scrutiny of all the relevant documents and physical "
        "verification of property at location.",
        st["BodyJ"]))
    story.append(Paragraph(f"<b>9.1 Distress value of Land (DV):</b> Nrs {fmt(summary['total_distress'])}", st["Body"]))
    story.append(Paragraph(
        "<b>9.2 Remarks & Observation:</b> In our opinion, this property is secured mortgage for the amount recommended "
        "in the valuation certificate.",
        st["Body"]))

    story.append(Paragraph("<b>10. Valuation Theory & Methodology</b>", st["H2"]))
    story.append(Paragraph("<b>Valuation Of Land</b>", st["Bold"]))
    story.append(Paragraph(
        "Land value determined by weighted average method: 30% weight to government rate and 70% weight to commercial/"
        "market rate. Commercial value fixed on the basis of market survey.",
        st["BodyJ"]))
    story.append(Paragraph("<b>Unit of Measurement</b>", st["Bold"]))
    story.append(Paragraph(
        "1 Bigha = 20 Katthas = 72900 Sqft = 6772.63 Sqm<br/>"
        "1 Kattha = 20 Dhur = 3645 Sqft = 338.63 Sqm<br/>"
        "1 Dhur = 182.25 Sqft = 16.93 Sqm",
        st["Small"]))
    story.append(Paragraph(
        f"<b>Valuation Methodology:</b> Fair Market value based on {bank['grv_pct']*100:.0f}% Government rate & "
        f"{bank['mrv_pct']*100:.0f}% Market Rate. Distress value = {bank['distress_factor']*100:.0f}% of Weighted Value. "
        f"Belt-2 market = 66% of Belt-1; Belt-3 = 50% of Belt-1. 15% land development deduction when area > 508.737 sq.m.",
        st["BodyJ"]))

    # ========== Legal Status ==========
    story.append(Paragraph("<b>11. Legal Status / Land Registration</b>", st["H2"]))
    legal_rows = [["Item"] + [p["plot_no"] for p in req["plots"]]]
    fields = [
        ("Title deed type", "title_deed_type"),
        ("Registration date", "reg_date"),
        ("Cooling-off period", "cooling_off"),
        ("Ownership type", "ownership_type"),
        ("Access at blueprint", "access_at_blueprint"),
        ("Motorable road", "motorable"),
        ("High tension line", "high_tension"),
        ("Near river", "near_river"),
        ("Near border (200m)", "near_border"),
        ("Guthi", "guthi"),
        ("Original charkilla", "original_charkilla"),
    ]
    for label, key in fields:
        legal_rows.append([label] + [p.get(key, "")[:18] for p in req["plots"]])
    ncols = 1 + len(req["plots"])
    col_w = [50*mm] + [(136*mm) / len(req["plots"])] * len(req["plots"])
    t = Table(legal_rows, colWidths=col_w)
    t.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 7),
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("BACKGROUND", (0, 0), (0, -1), SOFT),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.grey),
        ("TOPPADDING", (0, 0), (-1, -1), 1.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1.5),
    ]))
    story.append(t)

    # ========== Per-plot LAND AREA CHECKING pages ==========
    for pin, pout in zip(req["plots"], plots):
        story.append(PageBreak())
        story.append(header_block(st, firm, logo))
        story.append(Paragraph("<b>LAND AREA CHECKING</b>", st["SectionTitle"]))
        story.append(kv([
            ["Plot no", pout["plot_no"]],
            ["Plot Address as per Charkilla", client["owner_address_charkilla"]],
            ["Land Owner's Name", client["owner_name"]],
        ]))
        story.append(Spacer(1, 2))
        story.append(area_table(pout, st))
        story.append(Spacer(1, 4))
        story.append(Paragraph("<b>LAND RATE</b>", st["H2"]))
        rate_h = ["", "Belt - 1", "Belt - 2", "Belt - 3"]
        rate_rows = [
            rate_h,
            ["1. Rate adopted by Government / Sq.M.", f"{pout['govt_per_sqm']:,.2f}",
             f"{pout['govt_per_sqm']:,.2f}", f"{pout['govt_per_sqm']:,.2f}"],
            ["2. Market Rate / Sq.M.", f"{pout['market_per_sqm']:,.2f}",
             f"{pout['market_per_sqm']*0.66:,.2f}", f"{pout['market_per_sqm']*0.5:,.2f}"],
            ["3. Weighted average / Sq.M.", f"{pout['rate1']:,.2f}", f"{pout['rate2']:,.2f}", f"{pout['rate3']:,.2f}"],
            ["4. Land Rate adopted in this valuation", f"{pout['rate1']:,.2f}", f"{pout['rate2']:,.2f}", f"{pout['rate3']:,.2f}"],
        ]
        t = Table(rate_rows, colWidths=[70*mm, 35*mm, 35*mm, 35*mm])
        t.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 7),
            ("BACKGROUND", (0, 0), (-1, 0), LIGHT_BLUE),
            ("GRID", (0, 0), (-1, -1), 0.3, colors.grey),
            ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
            ("TOPPADDING", (0, 0), (-1, -1), 1.5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 1.5),
        ]))
        story.append(t)
        story.append(Paragraph(
            "5. Land Rate Analysis: Weighted average as per Bank Norms — 30% Government rate + 70% Market Rate.",
            st["Small"]))
        story.append(Spacer(1, 4))
        story.append(Paragraph("<b>Valuation Table of Land</b>", st["H2"]))
        vt = [
            ["", "Belt-1", "Belt-2", "Belt-3"],
            ["Area considered after deduction", f"{pout['belt1_net']:.2f}", f"{pout['belt2_net']:.2f}", f"{pout['belt3_net']:.2f}"],
            ["Land Rate adopted", f"{pout['rate1']:,.2f}", f"{pout['rate2']:,.2f}", f"{pout['rate3']:,.2f}"],
            ["Fair Market Value (Rs.)", f"{pout['fmv1']:,.0f}", f"{pout['fmv2']:,.0f}", f"{pout['fmv3']:,.0f}"],
            ["Net Value of Land", f"{pout['fmv1']:,.0f}", f"{pout['fmv2']:,.0f}", f"{pout['fmv3']:,.0f}"],
            ["Total / Say Value", f"{pout['fmv']:,}", "", ""],
        ]
        t = Table(vt, colWidths=[70*mm, 35*mm, 35*mm, 35*mm])
        t.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 7),
            ("BACKGROUND", (0, 0), (-1, 0), LIGHT_BLUE),
            ("BACKGROUND", (0, -1), (-1, -1), LIGHT_GOLD),
            ("GRID", (0, 0), (-1, -1), 0.3, colors.grey),
            ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
            ("TOPPADDING", (0, 0), (-1, -1), 1.5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 1.5),
        ]))
        story.append(t)

    # ========== Field Visit Team ==========
    story.append(PageBreak())
    story.append(header_block(st, firm, logo))
    story.append(Paragraph("<b>FIELD VISIT TEAM & DECLARATION</b>", st["MainTitle"]))
    story.append(Paragraph("<b>The Field Visit Team</b>", st["H2"]))
    for line in ["1. Authorized Engineer", "2. Staff of Consultancy", "3. Bank Staff", "4. Property Owner"]:
        story.append(Paragraph(line, st["Body"]))
    story.append(Spacer(1, 6))
    story.append(Paragraph(
        "This valuation report has been prepared based on the documents provided by the client, site inspection, "
        "and prevailing market rates. The valuator is not responsible for legal disputes regarding ownership or title. "
        "Bank should verify all original documents before loan disbursement.",
        st["BodyJ"]))
    story.append(Spacer(1, 14))
    story.append(Paragraph("_______________________________", st["Body"]))
    story.append(Paragraph("Signature of Valuator", st["Small"]))
    story.append(Paragraph(f"{req.get('valuator_name', '')} — {req.get('valuator_nec', '')}", st["Small"]))
    story.append(Spacer(1, 10))
    story.append(Paragraph("_______________________________", st["Body"]))
    story.append(Paragraph("Signature of Property Owner / Client", st["Small"]))
    story.append(Paragraph(client["owner_name"], st["Small"]))

    # ========== Annex placeholders ==========
    story.append(PageBreak())
    story.append(header_block(st, firm, logo))
    story.append(Paragraph("<b>ANNEX</b>", st["MainTitle"]))
    story.append(Paragraph("<b>Annex 1 — List of Documents</b>", st["H2"]))
    docs = [
        ["S.No.", "Particulars", "Obtained"],
        ["1", "Location plan and site plan of the property", "Yes"],
        ["2", "Photos of Property showing access road and all side views", "Yes"],
        ["3", "Copy of booklet page depicting minimum government rate of Land", "Yes"],
        ["4", "Citizenship certificate of proprietor", "Yes"],
        ["5", "Copy of Land ownership certificate (Lalpurja)", "Yes"],
        ["6", "Land revenue receipt (Malpot Tireko Rashid)", "Yes"],
        ["7", "Certificate of Four Sites (Char Killa)", "Yes"],
        ["8", "Ward map / File map of the plots", "Yes"],
        ["9", "Land Ownership Transfer deed (Rajinama etc.)", "NA"],
        ["10", "Approved map / Completion certificate (if building)", "NA" if data["building"]["fmv"] == 0 else "Yes"],
    ]
    t = Table(docs, colWidths=[12*mm, 130*mm, 25*mm])
    t.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 7.5),
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.grey),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    story.append(t)
    story.append(Spacer(1, 8))
    story.append(Paragraph("<b>Annex 2 — DRAWINGS of Land & Site plan Map</b>", st["H2"]))
    story.append(Paragraph("(Attach cadastral / site plan drawings here)", st["Words"]))
    story.append(Spacer(1, 8))
    story.append(Paragraph("<b>Annex 3 — PHOTOGRAPHS</b>", st["H2"]))
    story.append(Paragraph("(Attach site photographs — access road and all side views)", st["Words"]))
    story.append(Spacer(1, 8))
    story.append(Paragraph("<b>Annex 4 — DOCUMENTS</b>", st["H2"]))
    story.append(Paragraph("(Attach Lalpurja, Charkilla, Malpot receipt, Citizenship copies)", st["Words"]))

    doc.build(story, onFirstPage=add_page_number, onLaterPages=add_page_number)
    buf.seek(0)
    return buf.read()
