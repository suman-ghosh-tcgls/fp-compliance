"""Compliance report PDF from the checks files in outputs/.

Reads outputs/floorplan_checks.json + floorplan_graph.png (unit plan) and
outputs/parking_P1_checks.json + parking_P1_check.png (parking), writes
outputs/TowerQ_compliance_report.pdf. Only `checks` are reported (observations stay hidden).
Needs reportlab only (no PDF/geometry libraries): python report_pdf.py
"""
import datetime
import json
import os
from collections import Counter

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (Image, KeepTogether, PageBreak, Paragraph, SimpleDocTemplate,
                                Spacer, Table, TableStyle)

ROOT = os.path.dirname(os.path.abspath(__file__))
OUTPUTS = os.path.join(ROOT, "outputs")
OUT_PDF = os.path.join(OUTPUTS, os.environ.get("REPORT_PDF", "TowerQ_compliance_report.pdf"))
PROJECT = os.environ.get("REPORT_PROJECT", "Tower Q")

# Fonts: Arial (has >=, <= glyphs) if present, else built-in Helvetica.
FONT, FONT_B = "Helvetica", "Helvetica-Bold"
_ttf = "/System/Library/Fonts/Supplemental/"
if os.path.exists(_ttf + "Arial.ttf") and os.path.exists(_ttf + "Arial Bold.ttf"):
    pdfmetrics.registerFont(TTFont("Arial", _ttf + "Arial.ttf"))
    pdfmetrics.registerFont(TTFont("Arial-Bold", _ttf + "Arial Bold.ttf"))
    pdfmetrics.registerFontFamily("Arial", normal="Arial", bold="Arial-Bold",
                                  italic="Arial", boldItalic="Arial-Bold")
    FONT, FONT_B = "Arial", "Arial-Bold"

STATUS_COLOR = {"PASS": "#1b7f3b", "FAIL": "#c62828", "FLAG": "#b26a00",
                "REVIEW": "#b26a00", "CANNOT DETERMINE": "#5f6b7a"}
INK, MUTED, RULE = colors.HexColor("#1f2933"), colors.HexColor("#5f6b7a"), colors.HexColor("#d5dbe1")

ss = getSampleStyleSheet()
S = {
    "title": ParagraphStyle("t", parent=ss["Title"], fontName=FONT_B, fontSize=20, leading=24,
                            textColor=INK, spaceAfter=4),
    "sub": ParagraphStyle("s", fontName=FONT, fontSize=10.5, leading=14, textColor=MUTED),
    "h1": ParagraphStyle("h1", fontName=FONT_B, fontSize=14, leading=18, textColor=INK,
                         spaceBefore=10, spaceAfter=6),
    "h2": ParagraphStyle("h2", fontName=FONT_B, fontSize=11, leading=14, textColor=INK,
                         spaceBefore=8, spaceAfter=4),
    "body": ParagraphStyle("b", fontName=FONT, fontSize=9.5, leading=13, textColor=INK, spaceAfter=4),
    "small": ParagraphStyle("sm", fontName=FONT, fontSize=8, leading=10.5, textColor=MUTED),
    "cell": ParagraphStyle("c", fontName=FONT, fontSize=8.3, leading=10.5, textColor=INK),
    "cellb": ParagraphStyle("cb", fontName=FONT_B, fontSize=8.3, leading=10.5, textColor=INK),
    "head": ParagraphStyle("hd", fontName=FONT_B, fontSize=8.3, leading=10.5, textColor=colors.white),
    "caption": ParagraphStyle("cap", fontName=FONT, fontSize=8, leading=10.5, textColor=MUTED,
                              alignment=TA_CENTER, spaceBefore=3),
}


def esc(s):
    s = str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    if FONT != "Helvetica":
        s = s.replace("&gt;=", "≥").replace("&lt;=", "≤")
    return s


def base_status(st):
    """'PASS (at limit)' -> 'PASS'; used for colour and counts only."""
    for k in STATUS_COLOR:
        if st.startswith(k):
            return k
    return st


def status_cell(st):
    c = STATUS_COLOR.get(base_status(st), "#1f2933")
    return Paragraph(f'<font color="{c}"><b>{esc(st)}</b></font>', S["cellb"])


def table(rows, widths, header):
    data = [[Paragraph(esc(h), S["head"]) for h in header]] + rows
    t = Table(data, colWidths=widths, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#33414e")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f4f6f8")]),
        ("LINEBELOW", (0, 0), (-1, -1), 0.4, RULE),
        ("LEFTPADDING", (0, 0), (-1, -1), 4), ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    return t


def summary_line(statuses):
    n = Counter(base_status(s) for s in statuses)
    parts = [f'<font color="{STATUS_COLOR[k]}"><b>{n[k]} {k}</b></font>'
             for k in STATUS_COLOR if n.get(k)]
    return Paragraph(f"{len(statuses)} checks: " + ", ".join(parts), S["body"])


def figure(path, width, caption):
    from reportlab.lib.utils import ImageReader
    iw, ih = ImageReader(path).getSize()
    h = width * ih / iw
    max_h = 150 * mm
    if h > max_h:
        width, h = width * max_h / h, max_h
    return KeepTogether([Image(path, width=width, height=h), Paragraph(caption, S["caption"])])


def mtime(path):
    return datetime.datetime.fromtimestamp(os.path.getmtime(path)).strftime("%d %b %Y")


def on_page(canvas, doc):
    canvas.saveState()
    canvas.setFont(FONT, 7.5)
    canvas.setFillColor(MUTED)
    canvas.drawString(18 * mm, 10 * mm, f"{PROJECT} - UDCPR compliance check (automated, draft rules)")
    canvas.drawRightString(A4[0] - 18 * mm, 10 * mm, f"Page {doc.page}")
    canvas.restoreState()


def build():
    unit_json = os.path.join(OUTPUTS, "floorplan_checks.json")
    park_json = os.path.join(OUTPUTS, "parking_P1_checks.json")
    unit_png = os.path.join(OUTPUTS, "floorplan_graph.png")
    park_png = os.path.join(OUTPUTS, "parking_P1_check.png")
    unit = json.load(open(unit_json)) if os.path.exists(unit_json) else None
    park = json.load(open(park_json)) if os.path.exists(park_json) else None
    if not unit and not park:
        raise SystemExit("no checks files in outputs/ - run the pipelines first")

    doc = SimpleDocTemplate(OUT_PDF, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm,
                            topMargin=16 * mm, bottomMargin=18 * mm,
                            title=f"{PROJECT} UDCPR compliance report", author="fp_compliance")
    W = A4[0] - 36 * mm
    st = []

    # ---- cover / summary
    st += [Paragraph(f"{PROJECT}: UDCPR compliance check", S["title"]),
           Paragraph("Automated check of architectural drawings against selected UDCPR (Maharashtra) "
                     f"regulations. Report date {datetime.date.today():%d %b %Y}.", S["sub"]),
           Spacer(1, 8)]

    src = []
    if unit:
        src.append([Paragraph("Unit plan", S["cellb"]), Paragraph(esc(unit["source"]), S["cell"]),
                    Paragraph(f"{unit['scale_m_per_pt']:.4f} m/pt, fitted to labelled room dimensions", S["cell"]),
                    Paragraph(mtime(unit_json), S["cell"])])
    if park:
        sc = park["scale"]
        src.append([Paragraph("Parking P1", S["cellb"]), Paragraph(esc(park["source"]), S["cell"]),
                    Paragraph(f"{sc['m_per_pt']:.4f} m/pt; {esc(sc['basis'])}", S["cell"]),
                    Paragraph(mtime(park_json), S["cell"])])
    st += [Paragraph("Drawings checked", S["h2"]),
           table(src, [22 * mm, 58 * mm, 72 * mm, 22 * mm], ["Drawing", "Source file", "Scale", "Checked on"])]

    # overall result table
    allrows = []
    if unit:
        for rule in dict.fromkeys(c["rule"] for c in unit["checks"]):
            sts = [c["status"] for c in unit["checks"] if c["rule"] == rule]
            allrows.append(("Unit plan", rule, "Natural lighting of habitable rooms and kitchens", sts))
    if park:
        for c in park["checks"]:
            rid, _, req = c["rule"].partition(" ")
            allrows.append(("Parking P1", rid, f"{req} ({c['item']})", [c["status"]]))
    st += [Paragraph("Summary", S["h2"])]
    rows = []
    for drw, rid, what, sts in allrows:
        n = Counter(base_status(s) for s in sts)
        res = ", ".join(f'<font color="{STATUS_COLOR[k]}"><b>{n[k]} {k}</b></font>' if len(sts) > 1
                        else f'<font color="{STATUS_COLOR[k]}"><b>{esc(sts[0])}</b></font>'
                        for k in STATUS_COLOR if n.get(k))
        rows.append([Paragraph(drw, S["cell"]), Paragraph(esc(rid), S["cellb"]),
                     Paragraph(esc(what), S["cell"]), Paragraph(res, S["cell"])])
    st.append(table(rows, [22 * mm, 26 * mm, 70 * mm, 56 * mm], ["Drawing", "Rule", "Requirement", "Result"]))

    st += [Paragraph("Result meanings", S["h2"]),
           Paragraph("<b>PASS</b> requirement met on the measured geometry. <b>FAIL</b> requirement not met. "
                     "<b>REVIEW</b> a judgement is needed that the drawing alone cannot settle. "
                     "<b>CANNOT DETERMINE</b> the drawing does not contain the data the rule needs; "
                     "this is never reported as PASS. A qualifier in brackets, e.g. PASS (at limit), "
                     "limits the PASS and is explained in the detail column.", S["body"]),
           Paragraph("Basis and limitations", S["h2"]),
           Paragraph("Rule values are draft records taken from a summary of UDCPR regulations, not yet "
                     "verified against the notified text; some conditions (e.g. small-plot exceptions) "
                     "are not encoded. Geometry is extracted automatically from plotted PDF drawings; "
                     "lengths carry the scale uncertainty stated per drawing. This report is an aid to "
                     "plan scrutiny and does not replace review by the competent authority.", S["body"])]

    # ---- unit plan
    if unit:
        st += [PageBreak(), Paragraph("1. Unit plan: UDCPR 9.20.1 natural lighting", S["h1"]),
               Paragraph("Each habitable room and kitchen needs openings of at least 1/10 of its floor area "
                         "to the exterior or an open deck (opening_ratio), and no part of the room may be "
                         "more than 7.5 m from such an opening (depth).", S["body"]),
               summary_line([c["status"] for c in unit["checks"]])]
        if os.path.exists(unit_png):
            st.append(figure(unit_png, W, "Figure 1. Extracted rooms and connections. Rooms circled in red "
                                          "have a FAIL or REVIEW result. Edge labels are door leaf widths "
                                          "or glazing widths in metres."))
        rows = []
        for c in unit["checks"]:
            area = f"{c['area_m2']:.2f}" if "area_m2" in c else ""
            rows.append([Paragraph(esc(c["space"]), S["cellb"]), Paragraph(area, S["cell"]),
                         Paragraph(esc(c["check"]).replace("_", " "), S["cell"]),
                         status_cell(c["status"]), Paragraph(esc(c["detail"]), S["cell"])])
        st += [Paragraph("Results by room", S["h2"]),
               table(rows, [30 * mm, 14 * mm, 20 * mm, 26 * mm, 84 * mm],
                     ["Room", "Area m²", "Check", "Result", "Detail"])]
        st.append(Paragraph("Data needed to resolve CANNOT DETERMINE: window and door head and sill heights "
                            "(elevations or a window schedule). The minimum average opening height each room "
                            "needs is given in the detail column.", S["small"]))

    # ---- parking
    if park:
        st += [PageBreak(), Paragraph("2. Parking level P1: UDCPR 8.1.1 and 9.12.2", S["h1"]),
               Paragraph(f"{len(park.get('bays', []))} car bays detected; drive aisle clear width "
                         f"{park['aisle']['typical_clear_width_m']:.2f} m typical, "
                         f"{park['aisle']['min_clear_width_m']:.2f} m minimum.", S["body"]),
               summary_line([c["status"] for c in park["checks"]])]
        if os.path.exists(park_png):
            st.append(figure(park_png, W * 0.72,
                             "Figure 2. Parking level P1. Yellow: drive aisle clear area; the line along the "
                             "aisle is its centreline, coloured by clear width; the narrowest point is marked "
                             "in metres. Bay shading is a drawing-review aid and is not a rule result."))
        rows = []
        for c in park["checks"]:
            rid, _, req = c["rule"].partition(" ")
            rows.append([Paragraph(esc(rid), S["cellb"]), Paragraph(esc(req), S["cell"]),
                         Paragraph(esc(c["item"]), S["cell"]), status_cell(c["status"]),
                         Paragraph(esc(c["detail"]), S["cell"])])
        st += [Paragraph("Results", S["h2"]),
               table(rows, [25 * mm, 32 * mm, 20 * mm, 26 * mm, 71 * mm],
                     ["Rule", "Requirement", "Item", "Result", "Detail"])]
        st.append(Paragraph("Data needed to resolve CANNOT DETERMINE: plans of all parking levels, building "
                            "sections with ramp levels, plot area, and individual two-wheeler bays.",
                            S["small"]))

    doc.build(st, onFirstPage=on_page, onLaterPages=on_page)
    print("wrote", OUT_PDF)


if __name__ == "__main__":
    build()
