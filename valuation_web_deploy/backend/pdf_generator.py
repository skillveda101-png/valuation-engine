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
from reportlab.graphics.shapes import Drawing, Circle, String, Line, Rect, Polygon, Group
from reportlab.graphics import renderPDF
from io import BytesIO
from typing import Dict, Any, List, Optional, Tuple
import os
import re
import math
import urllib.request

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


def make_logo_flowable(size_mm=22):
    """Prefer static/logo.png (company logo), else drawn seal."""
    logo_path = os.path.join(os.path.dirname(__file__), "static", "logo.png")
    if os.path.isfile(logo_path):
        try:
            return Image(logo_path, width=size_mm*mm, height=size_mm*mm)
        except Exception:
            pass
    return CompanySeal(size=int(size_mm * 2.5))


def _photo_paths_from_data(data: Dict[str, Any]) -> List[str]:
    """Resolve absolute paths for site photos stored under backend/data/photos/."""
    names = data.get("site_photo_paths") or []
    photos_dir = os.path.join(os.path.dirname(__file__), "data", "photos")
    paths = []
    for n in names:
        if not n:
            continue
        p = n if os.path.isabs(n) else os.path.join(photos_dir, os.path.basename(n))
        if os.path.isfile(p):
            paths.append(p)
    return paths


def _make_photo_flowables(paths: List[str], max_w_mm=85, max_h_mm=65) -> List:
    """Create Image flowables for up to 6 photos, 2 per row."""
    out = []
    for p in paths[:6]:
        try:
            img = Image(p)
            # scale to fit
            iw, ih = img.imageWidth, img.imageHeight
            if iw <= 0 or ih <= 0:
                continue
            scale = min((max_w_mm * mm) / iw, (max_h_mm * mm) / ih, 1.0)
            img.drawWidth = iw * scale
            img.drawHeight = ih * scale
            out.append(img)
        except Exception:
            continue
    return out


def make_qr_flowable(url: str, size_mm=28):
    """QR code linking to public verification URL."""
    if not url:
        return Spacer(1, size_mm*mm)
    try:
        import qrcode
        from reportlab.lib.utils import ImageReader
        qr = qrcode.QRCode(version=2, box_size=6, border=1)
        qr.add_data(url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buf = BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        return Image(buf, width=size_mm*mm, height=size_mm*mm)
    except Exception:
        return Paragraph(f"<font size='6'>Verify: {url}</font>", getSampleStyleSheet()["Normal"])



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




def valuator_response_page(story, st, data, req, client, summary, plots):
    """Page matching sample 'Valuator Response' checklist (SN 1–56 style)."""
    story.append(PageBreak())
    story.append(Paragraph("<b>VALUATOR RESPONSE</b>", st["MainTitle"]))
    story.append(HRFlowable(width="100%", thickness=1, color=NAVY))
    story.append(Spacer(1, 4))
    bldg = data.get("building") or {}
    bd = bldg.get("details") or {}
    pin0 = req["plots"][0] if req.get("plots") else {}
    plot_nos = " & ".join(p["plot_no"] for p in plots)
    roads = " / ".join(filter(None, [p.get("road_width") or p.get("road_type") for p in req.get("plots", [])]))
    fronts = " / ".join(filter(None, [p.get("frontage") for p in req.get("plots", [])]))
    landmarks = " / ".join(filter(None, [p.get("nearest_landmark") for p in req.get("plots", [])]))
    rows = [
        ["SN", "Description", "Valuator Response"],
        ["1", "Name of the owner", client.get("owner_name", "")],
        ["2", "Name of the client", client.get("client_name", "")],
        ["3", "FMV of the property", f"{summary.get('total_fmv', 0):,.2f}"],
        ["4", "DV of the property", f"{summary.get('total_distress', 0):,.2f}"],
        ["5", "Nearest Land Mark", landmarks or "-"],
        ["6", "Land title deed", pin0.get("title_deed_type", "Normal Sale")],
        ["7", "Original Blue print of land / trace map", pin0.get("original_blueprint", "Yes")],
        ["8", "Type of road", pin0.get("road_type", "") or roads],
        ["9", "Width of road", roads],
        ["10", "Motorable road", pin0.get("motorable", "Yes")],
        ["11", "Road expansion activity", pin0.get("road_expansion", "No")],
        ["12", "Uses of land", pin0.get("importance", "Residential")],
        ["13", "Shape of land", pin0.get("shape", "Regular")],
        ["14", "Frontage of land", fronts],
        ["15", "Plot number", plot_nos],
        ["16", "Address of Land as per Charkilla", client.get("owner_address_charkilla", "")],
        ["17", "Type of Land", pin0.get("land_type", "Residential")],
        ["18", "Area as per Lal purja (sq. m)", ", ".join(f"{p['lalpurja_sqm']:.2f}" for p in plots)],
        ["19", "Area as per Actual measurement (sq. m)", ", ".join(f"{p['site_sqm']:.2f}" for p in plots)],
        ["20", "Area as per cadastral map (sq.m)", ", ".join(f"{p['cadastral_sqm']:.2f}" for p in plots)],
        ["21", "Area considered for valuation (Sq. m)", ", ".join(f"{p['considered_sqm']:.2f}" for p in plots)],
        ["22", "Area deducted for valuation (sq.m)", ", ".join(f"{p['deducted_sqm']:.2f}" for p in plots)],
        ["23", "High tension line", pin0.get("high_tension", "NOT PASSING")],
        ["24", "Type of building", bd.get("building_type", "NA") if bd else "NA"],
        ["25", "No of storey", str(bd.get("storeys", "NA")) if bd else "NA"],
        ["26", "Built up area", str(bd.get("built_up_sft", "NA")) if bd else "NA"],
        ["27", "Year of completion", bd.get("year", "NA") if bd else "NA"],
        ["28", "Naksa pass", bd.get("naksa_pass", "NA") if bd else "NA"],
        ["29", "Construction completion certificate", bd.get("completion_certificate", "NA") if bd else "NA"],
        ["30", "Building constructed as per approved drawings", bd.get("constructed_as_per_drawing", "NA") if bd else "NA"],
        ["31", "Original four boundary certificate", pin0.get("original_charkilla", "")],
        ["32", "Municipal four boundary certificate", pin0.get("municipal_charkilla", "")],
        ["33", "Anticipated life of building", str(bd.get("anticipated_life_years", "NA")) if bd else "NA"],
        ["34", "Pillar of building", bd.get("pillar_size", "NA") if bd else "NA"],
        ["35", "Type of construction", bd.get("type", "NA") if bd else "NA"],
        ["36", "Type of ownership", pin0.get("ownership_type", "Single")],
        ["37", "More than two joint owners of land", pin0.get("joint_owners", "No")],
        ["38", "Date of registration", pin0.get("reg_date", "")],
        ["39", "Land registration done by way of", pin0.get("title_deed_type", "Normal Sale")],
        ["40", "Legal litigation period", "No"],
        ["41", "ROW deducted as per govt rules", "Yes"],
        ["42", "Collateral within protected heritage area", "No"],
        ["43", "River/stream/lakes near collateral", pin0.get("near_river", "No")],
        ["44", "Within 200 m of international border", pin0.get("near_border", "No")],
        ["45", "Sewage/dumping/hazardous features affecting", "No"],
        ["46", "Irregular shape (>6 sides)", pin0.get("irregular_shape", "No")],
        ["47", "Land inclination > 40 degree", pin0.get("high_inclination", "No")],
        ["48", "Area of land < 79.5 sq.m", "No"],
        ["49", "Too many scattered plots", "No"],
        ["50", "Political disrupted area", "No"],
        ["51", "Low salability prospects", "No"],
        ["52", "Adjoined with sukumbasi tole", pin0.get("sukumbasi", "No")],
        ["53", "Area > 2 bigha terai / 20 ropani hills", "No"],
        ["54", "Road access as per blue print", pin0.get("access_at_blueprint", "No")],
        ["55", "Road access as per four boundary certificate", pin0.get("road_access_charkilla", "Yes")],
        ["56", "Property in the name of guthi", pin0.get("guthi", "No")],
    ]
    t = Table(rows, colWidths=[12*mm, 95*mm, 75*mm])
    t.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 6.5),
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 1),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
        ("LEFTPADDING", (0, 0), (-1, -1), 2),
    ]))
    story.append(t)




def _parse_gps(gps_text: str) -> Optional[Tuple[float, float]]:
    """Parse 'lat, lng' or 'lat lng' into floats."""
    if not gps_text:
        return None
    m = re.search(r"(-?\d{1,3}\.\d+)\s*[,\s]\s*(-?\d{1,3}\.\d+)", str(gps_text))
    if not m:
        return None
    try:
        lat, lng = float(m.group(1)), float(m.group(2))
        if -90 <= lat <= 90 and -180 <= lng <= 180:
            return lat, lng
    except Exception:
        pass
    return None


def _deg2num(lat: float, lon: float, zoom: int):
    n = 2.0 ** zoom
    xtile = int((lon + 180.0) / 360.0 * n)
    lat_rad = math.radians(lat)
    ytile = int((1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n)
    return xtile, ytile


def _fetch_osm_tile(z: int, x: int, y: int) -> Optional[bytes]:
    url = f"https://tile.openstreetmap.org/{z}/{x}/{y}.png"
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "DynamicSolutionValuation/4.0 (location-plan)"},
        )
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = resp.read()
            if data and len(data) > 200:
                return data
    except Exception:
        return None
    return None


def _fetch_static_map(lat: float, lng: float, zoom: int = 16, width: int = 640, height: int = 400) -> Optional[bytes]:
    """
    Build a Google Earth–style overview by stitching OpenStreetMap tiles
    around the GPS point and drawing a red pin. No API key required.
    """
    try:
        from PIL import Image, ImageDraw
    except Exception:
        return None

    tile_size = 256
    # 3x3 tiles centered near point
    cx, cy = _deg2num(lat, lng, zoom)
    n = 2 ** zoom
    tiles = []
    for dy in (-1, 0, 1):
        row = []
        for dx in (-1, 0, 1):
            tx = (cx + dx) % n
            ty = cy + dy
            if ty < 0 or ty >= n:
                row.append(None)
                continue
            raw = _fetch_osm_tile(zoom, tx, ty)
            if not raw:
                row.append(None)
                continue
            try:
                row.append(Image.open(BytesIO(raw)).convert("RGB"))
            except Exception:
                row.append(None)
        tiles.append(row)

    if not any(im for row in tiles for im in row if im is not None):
        return None

    mosaic = Image.new("RGB", (tile_size * 3, tile_size * 3), (232, 240, 232))
    for j, row in enumerate(tiles):
        for i, im in enumerate(row):
            if im is not None:
                mosaic.paste(im, (i * tile_size, j * tile_size))

    # Pixel position of lat/lng within center tile, then offset by one tile
    def latlon_to_pixel(la, lo, z):
        nn = 2.0 ** z
        x = (lo + 180.0) / 360.0 * nn * tile_size
        la_r = math.radians(la)
        y = (1.0 - math.asinh(math.tan(la_r)) / math.pi) / 2.0 * nn * tile_size
        return x, y

    px, py = latlon_to_pixel(lat, lng, zoom)
    # origin of mosaic = (cx-1, cy-1) tile
    origin_x = (cx - 1) * tile_size
    origin_y = (cy - 1) * tile_size
    pin_x = int(px - origin_x)
    pin_y = int(py - origin_y)

    draw = ImageDraw.Draw(mosaic)
    r = 10
    # pin shadow
    draw.ellipse((pin_x - r + 2, pin_y - r + 2, pin_x + r + 2, pin_y + r + 2), fill=(0, 0, 0))
    draw.ellipse((pin_x - r, pin_y - r, pin_x + r, pin_y + r), fill=(220, 38, 38), outline=(127, 29, 29), width=2)
    draw.line((pin_x, pin_y, pin_x, pin_y + 18), fill=(185, 28, 28), width=3)
    # label bar
    label = f"{lat:.5f}, {lng:.5f}"
    draw.rectangle((8, 8, 8 + 7 * len(label) + 16, 28), fill=(30, 58, 95))
    try:
        draw.text((14, 12), label, fill=(255, 255, 255))
    except Exception:
        pass

    # crop/resize to requested size
    out = mosaic.resize((width, height), Image.Resampling.LANCZOS)
    buf = BytesIO()
    out.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


def _static_map_flowable(lat: float, lng: float, max_w_mm: float = 170, max_h_mm: float = 95):
    raw = _fetch_static_map(lat, lng)
    if not raw:
        return None
    try:
        from reportlab.lib.utils import ImageReader
        bio = BytesIO(raw)
        img = Image(bio)
        iw, ih = img.imageWidth, img.imageHeight
        if iw <= 0 or ih <= 0:
            return None
        scale = min((max_w_mm * mm) / iw, (max_h_mm * mm) / ih, 1.0)
        img.drawWidth = iw * scale
        img.drawHeight = ih * scale
        return img
    except Exception:
        return None



def make_site_plan_drawing(
    plot: Dict[str, Any],
    gps_text: str = "",
    width: float = 500,
    height: float = 520,
) -> Drawing:
    """
    Engineering-style SITE PLAN matching sample valuation drawings:
    access road spine, distance labels, landmarks, subject plot, compass.
    Black linework on white.
    """
    d = Drawing(width, height)
    # Outer content area is plain white; border drawn by page frame
    d.add(Rect(0, 0, width, height, fillColor=colors.white, strokeColor=colors.black, strokeWidth=0.8))

    def trunc(s, n=32):
        s = str(s or "")
        return s if len(s) <= n else s[: n - 1] + "…"

    plot_no = str(plot.get("plot_no") or "")
    road = (plot.get("road_width") or plot.get("road_type") or "").strip()
    road_ft = plot.get("road_width_ft") or 0
    road_label = road or (f"{road_ft} Ft Road" if road_ft else "Access Road")
    landmark = (plot.get("nearest_landmark") or "").strip()
    dist = (plot.get("distance_to_market") or "").strip()
    east = trunc(plot.get("east") or "East", 24)
    west = trunc(plot.get("west") or "West", 24)
    north = trunc(plot.get("north") or "North", 24)
    south = trunc(plot.get("south") or "South", 24)
    frontage = (plot.get("frontage") or "").strip()

    # --- Compass (top-right) ---
    cx, cy, R = width - 55, height - 55, 28
    d.add(Circle(cx, cy, R, fillColor=colors.white, strokeColor=colors.black, strokeWidth=1.2))
    d.add(Circle(cx, cy, 3, fillColor=colors.black, strokeColor=colors.black, strokeWidth=0.5))
    # N arrow
    d.add(Polygon([cx, cy + R - 4, cx - 5, cy + 6, cx + 5, cy + 6],
                  fillColor=colors.black, strokeColor=colors.black, strokeWidth=0.5))
    d.add(Line(cx, cy - R + 4, cx, cy + 6, strokeColor=colors.black, strokeWidth=1))
    d.add(Line(cx - R + 4, cy, cx + R - 4, cy, strokeColor=colors.black, strokeWidth=0.8))
    d.add(String(cx, cy + R + 8, "N", fontName="Helvetica-Bold", fontSize=10, fillColor=colors.black, textAnchor="middle"))
    d.add(String(cx, cy - R - 10, "S", fontName="Helvetica-Bold", fontSize=8, fillColor=colors.black, textAnchor="middle"))
    d.add(String(cx + R + 8, cy - 3, "E", fontName="Helvetica-Bold", fontSize=8, fillColor=colors.black, textAnchor="middle"))
    d.add(String(cx - R - 8, cy - 3, "W", fontName="Helvetica-Bold", fontSize=8, fillColor=colors.black, textAnchor="middle"))

    # --- Main access road (vertical spine then horizontal, like sample) ---
    # Coordinates in drawing space (origin bottom-left)
    # Horizontal main road near bottom third
    road_y = 140
    d.add(Line(40, road_y, width - 40, road_y, strokeColor=colors.black, strokeWidth=2.2))
    # double line for road edge
    d.add(Line(40, road_y - 6, width - 40, road_y - 6, strokeColor=colors.black, strokeWidth=0.9))
    d.add(Line(40, road_y + 6, width - 180, road_y + 6, strokeColor=colors.black, strokeWidth=0.9))

    # Vertical approach road going up from junction
    jx = 160
    d.add(Line(jx - 5, road_y, jx - 5, height - 90, strokeColor=colors.black, strokeWidth=1.6))
    d.add(Line(jx + 5, road_y, jx + 5, height - 90, strokeColor=colors.black, strokeWidth=1.6))
    # center dashed
    y = road_y + 10
    while y < height - 95:
        d.add(Line(jx, y, jx, min(y + 8, height - 95), strokeColor=colors.HexColor("#666666"), strokeWidth=0.6))
        y += 14

    # Subject property (hatched box) along upper part of approach — like sample
    sub_x, sub_y, sub_w, sub_h = jx - 42, height - 160, 36, 48
    d.add(Rect(sub_x, sub_y, sub_w, sub_h, fillColor=colors.HexColor("#E5E5E5"),
               strokeColor=colors.black, strokeWidth=1.5))
    # hatch
    for i in range(0, int(sub_h), 5):
        d.add(Line(sub_x, sub_y + i, sub_x + sub_w, sub_y + i, strokeColor=colors.HexColor("#999999"), strokeWidth=0.4))
    d.add(String(sub_x + sub_w / 2, sub_y + sub_h / 2 - 3, "SITE", fontName="Helvetica-Bold",
                 fontSize=8, fillColor=colors.black, textAnchor="middle"))
    d.add(String(sub_x + sub_w / 2, sub_y - 12, f"Plot {plot_no}" if plot_no else "Subject",
                 fontName="Helvetica", fontSize=7, fillColor=colors.black, textAnchor="middle"))

    # Dimension ticks on approach road (approximate chainage style)
    dims = [
        (sub_y + sub_h + 8, "APX. 120 M."),
        (sub_y - 40, "APX. 370 M."),
        ((sub_y + road_y) / 2, "APX. 560 M."),
    ]
    for yy, label in dims:
        d.add(Line(jx + 12, yy, jx + 28, yy, strokeColor=colors.black, strokeWidth=0.7))
        d.add(String(jx + 32, yy - 3, label, fontName="Helvetica", fontSize=7, fillColor=colors.black))

    # Horizontal distance along main road
    d.add(Line(jx + 20, road_y + 18, jx + 160, road_y + 18, strokeColor=colors.black, strokeWidth=0.7))
    d.add(Line(jx + 20, road_y + 14, jx + 20, road_y + 22, strokeColor=colors.black, strokeWidth=0.7))
    d.add(Line(jx + 160, road_y + 14, jx + 160, road_y + 22, strokeColor=colors.black, strokeWidth=0.7))
    d.add(String(jx + 90, road_y + 22, dist if dist else "APX. 380 M.", fontName="Helvetica",
                 fontSize=7, fillColor=colors.black, textAnchor="middle"))

    # Landmark boxes (hospital / petrol style)
    # Upper landmark near site
    lm1_x, lm1_y = jx - 95, height - 175
    d.add(Rect(lm1_x, lm1_y, 48, 22, fillColor=colors.HexColor("#DDDDDD"), strokeColor=colors.black, strokeWidth=1))
    lm1 = trunc(landmark, 18) if landmark else "Landmark"
    d.add(String(lm1_x + 24, lm1_y + 8, lm1, fontName="Helvetica", fontSize=6.5,
                 fillColor=colors.black, textAnchor="middle"))

    # Lower landmark near junction (e.g. petrol pump)
    lm2_x, lm2_y = jx - 70, road_y - 55
    d.add(Rect(lm2_x, lm2_y, 50, 22, fillColor=colors.HexColor("#DDDDDD"), strokeColor=colors.black, strokeWidth=1))
    d.add(String(lm2_x + 25, lm2_y + 8, "Petrol / Shop", fontName="Helvetica", fontSize=6.5,
                 fillColor=colors.black, textAnchor="middle"))

    # Chowk / junction label
    d.add(Circle(jx + 160, road_y, 5, fillColor=colors.white, strokeColor=colors.black, strokeWidth=1))
    d.add(String(jx + 160, road_y + 14, "Chowk", fontName="Helvetica", fontSize=7,
                 fillColor=colors.black, textAnchor="middle"))

    # Way direction labels
    d.add(String(jx + 70, road_y - 18, "Way To Charali", fontName="Helvetica-Oblique",
                 fontSize=7, fillColor=colors.black, textAnchor="middle"))
    d.add(String(jx + 220, road_y - 18, "Way To Main Town", fontName="Helvetica-Oblique",
                 fontSize=7, fillColor=colors.black, textAnchor="middle"))

    # Road name
    d.add(String(jx + 40, road_y + 32, trunc(road_label, 40), fontName="Helvetica",
                 fontSize=7, fillColor=colors.black))

    # Charkilla notes (right panel)
    info_x = width - 175
    info_y = height - 130
    d.add(String(info_x, info_y, "FOUR BOUNDARIES", fontName="Helvetica-Bold", fontSize=8, fillColor=colors.black))
    d.add(String(info_x, info_y - 14, f"North: {north}", fontName="Helvetica", fontSize=7, fillColor=colors.black))
    d.add(String(info_x, info_y - 26, f"East: {east}", fontName="Helvetica", fontSize=7, fillColor=colors.black))
    d.add(String(info_x, info_y - 38, f"South: {south}", fontName="Helvetica", fontSize=7, fillColor=colors.black))
    d.add(String(info_x, info_y - 50, f"West: {west}", fontName="Helvetica", fontSize=7, fillColor=colors.black))
    if frontage:
        d.add(String(info_x, info_y - 66, f"Frontage: {trunc(frontage, 22)}", fontName="Helvetica", fontSize=7, fillColor=colors.black))
    if gps_text:
        d.add(String(info_x, info_y - 82, f"GPS: {trunc(gps_text, 28)}", fontName="Helvetica-Bold", fontSize=7, fillColor=colors.black))

    # Title
    d.add(String(width / 2, 28, "SITE PLAN", fontName="Helvetica-Bold", fontSize=12,
                 fillColor=colors.black, textAnchor="middle"))
    d.add(String(width / 2, 14, "(Not to cadastral scale — for valuation location context)",
                 fontName="Helvetica", fontSize=6.5, fillColor=colors.HexColor("#444444"), textAnchor="middle"))
    return d


def build_location_plan_story(data: Dict[str, Any], st) -> List:
    """
    Full-page SITE / LOCATION PLAN with thick outer border and header strip
    matching sample valuation drawings (client / owner / address / checked-drawn by).
    """
    req = data.get("request") or {}
    client = req.get("client") or {}
    plots_req = req.get("plots") or []
    plot = plots_req[0] if plots_req else {}
    gps_global = (req.get("gps") or "").strip()
    gps_text = gps_global or (plot.get("gps") or "")
    if not gps_text:
        for p in plots_req:
            if p.get("gps"):
                gps_text = p["gps"]
                break

    firm_name = req.get("firm_name") or "DYNAMIC SOLUTION PVT. LTD."
    valuator = req.get("valuator_name") or "Er. Yogesh Bhattarai"
    address = (
        client.get("owner_address_charkilla")
        or client.get("owner_address_dhanipurja")
        or client.get("client_address_citizenship")
        or ""
    )
    client_name = client.get("client_name") or ""
    owner_name = client.get("owner_name") or client_name
    plot_nos = ", ".join(str(p.get("plot_no") or "") for p in plots_req if p.get("plot_no"))

    out: List = []
    # Full-page feel: page break before annex is already done by caller

    # Thick outer border using nested tables (≈1 inch visual frame via padding + double line)
    # Header bar like sample image 2
    header_style = ParagraphStyle(
        name="SitePlanHead",
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=10,
        textColor=colors.black,
    )
    header_small = ParagraphStyle(
        name="SitePlanSmall",
        fontName="Helvetica",
        fontSize=7,
        leading=9,
        textColor=colors.black,
    )

    head_data = [
        [
            Paragraph("<b>VALUATION DRAWING</b>", header_style),
            Paragraph(f"<b>LAND ADDRESS:</b> {address or '—'}", header_small),
            Paragraph(f"<b>CHECKED BY:</b><br/>{valuator}", header_small),
        ],
        [
            Paragraph(f"<b>CLIENT'S INFO:</b><br/>{client_name or '—'}", header_small),
            Paragraph(f"<b>OWNER'S INFO:</b><br/>{owner_name or '—'}", header_small),
            Paragraph(f"<b>DRAWN BY:</b><br/>{firm_name}", header_small),
        ],
        [
            Paragraph("<b>SITE / LOCATION PLAN</b>", header_style),
            Paragraph(f"<b>PLOT NO(S):</b> {plot_nos or '—'}", header_small),
            Paragraph(f"<b>GPS:</b> {gps_text or '—'}", header_small),
        ],
    ]
    head = Table(head_data, colWidths=[60*mm, 70*mm, 50*mm])
    head.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 1.2, colors.black),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F0F0F0")),
        ("BACKGROUND", (0, 2), (-1, 2), colors.HexColor("#F5F5F5")),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))

    # Drawing
    drawing = make_site_plan_drawing(plot, gps_text=gps_text, width=500, height=500)

    # Optional OSM map under schematic if GPS available (smaller)
    map_block = []
    coords = _parse_gps(gps_text)
    if coords:
        lat, lng = coords
        map_img = _static_map_flowable(lat, lng, max_w_mm=170, max_h_mm=70)
        if map_img:
            map_block = [
                Spacer(1, 4),
                Paragraph(
                    f"<b>Satellite / street context (OSM)</b> — pin at {lat:.6f}, {lng:.6f}",
                    st["Small"],
                ),
                map_img,
            ]

    # Assemble with thick double border (outer thick + inner)
    inner = [head, Spacer(1, 6), drawing] + map_block
    inner_tbl = Table([[x] for x in inner], colWidths=[180*mm])
    inner_tbl.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 2.5, colors.black),  # strong inner box
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))

    # Outer frame ≈ inch-like heavy border using another box with larger stroke
    outer = Table([[inner_tbl]], colWidths=[190*mm])
    outer.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 4, colors.black),  # thick outer border
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))

    out.append(outer)
    out.append(Spacer(1, 6))
    out.append(Paragraph(
        "Note: Site plan is prepared for valuation location context from field inspection notes, "
        "GPS and declared distances/landmarks. It does not replace cadastral or survey maps.",
        st["Words"],
    ))
    return out


def generate_valuation_pdf(data: Dict[str, Any]) -> bytes:
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=12*mm, rightMargin=12*mm,
        topMargin=10*mm, bottomMargin=14*mm
    )
    st = styles()
    story = []
    logo = make_logo_flowable(24)
    verify_url = data.get("verify_url") or ""
    report_id = data.get("report_id") or ""
    qr = make_qr_flowable(verify_url, 26)

    req = data["request"]
    client = req["client"]
    summary = data["summary"]
    plots = data["plots"]
    bank = data["bank"]
    any_belting = data.get("any_belting", any(p.get("use_belting") for p in plots))
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
    cover_photos = _photo_paths_from_data(data)
    if cover_photos:
        imgs = _make_photo_flowables(cover_photos[:2], max_w_mm=80, max_h_mm=55)
        if imgs:
            # one or two photos side by side
            if len(imgs) == 1:
                story.append(imgs[0])
            else:
                tph = Table([[imgs[0], imgs[1]]], colWidths=[90*mm, 90*mm])
                tph.setStyle(TableStyle([
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 2),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 2),
                ]))
                story.append(tph)
        story.append(Paragraph("<i>See Annex 3 for additional photographs</i>", st["Words"]))
    else:
        story.append(Paragraph("<i>Site photographs are included in Annex 3 when available.</i>", st["Words"]))
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
    # Verification strip on cover
    if report_id:
        vrows = [[
            qr,
            Paragraph(
                f"<b>Report ID:</b> {report_id}<br/>"
                f"<b>Scan QR to verify</b> this report online.<br/>"
                f"<font size='7'>If values differ from verification page, document may be altered.</font><br/>"
                f"<font size='6'>{verify_url}</font>",
                st["Small"],
            ),
        ]]
        vt = Table(vrows, colWidths=[32*mm, 150*mm])
        vt.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("BOX", (0, 0), (-1, -1), 0.5, NAVY),
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F0FFF4")),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(Spacer(1, 6))
        story.append(vt)
        story.append(Paragraph("<i>Scan to verify authenticity — Dynamic Solution registry</i>", st["Words"]))

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
        "     Annex 2  SITE / LOCATION PLAN",
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
        ( "8. Belting carried out: Belt-2 = 66% of Belt-1 market rate; Belt-3 = 50% of Belt-1 market rate." if any_belting else "8. Belting not applied for this property." ),
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
    story.append(PageBreak())
    for flowable in build_location_plan_story(data, st):
        story.append(flowable)
    story.append(PageBreak())
    story.append(Paragraph("<b>Annex 3 — PHOTOGRAPHS</b>", st["H2"]))
    all_photos = _photo_paths_from_data(data)
    if all_photos:
        story.append(Paragraph(
            "Photographs of the property (access road and site views) captured during field inspection:",
            st["Words"],
        ))
        story.append(Spacer(1, 4))
        imgs = _make_photo_flowables(all_photos, max_w_mm=85, max_h_mm=65)
        # Arrange in rows of 2
        row = []
        for i, img in enumerate(imgs):
            row.append(img)
            if len(row) == 2 or i == len(imgs) - 1:
                while len(row) < 2:
                    row.append(Paragraph("", st["Words"]))
                tph = Table([row], colWidths=[90*mm, 90*mm])
                tph.setStyle(TableStyle([
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ("BOX", (0, 0), (0, 0), 0.3, colors.grey),
                    ("BOX", (1, 0), (1, 0), 0.3, colors.grey),
                ]))
                story.append(tph)
                row = []
    else:
        story.append(Paragraph(
            "Site photographs were reviewed during inspection. Digital copies are retained in the office file.",
            st["Words"],
        ))
    story.append(Spacer(1, 8))
    story.append(Paragraph("<b>Annex 4 — DOCUMENTS</b>", st["H2"]))
    story.append(Paragraph(
        "Supporting documents (Lalpurja, Charkilla, Malpot receipt, Citizenship copies, etc.) "
        "as listed in Annex 1 are retained in the office file and form part of this report.",
        st["Words"],
    ))

    doc.build(story, onFirstPage=add_page_number, onLaterPages=add_page_number)
    buf.seek(0)
    return buf.read()
