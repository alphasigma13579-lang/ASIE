"""File exporters for a persisted funder-report projection.

Exporters consume the already-built projection. They do not calculate finance,
change Snapshot state, or infer missing accounting values.
"""

from __future__ import annotations

from pathlib import Path
import os
import shutil
import subprocess
import tempfile
from zipfile import ZIP_DEFLATED, ZipFile
from typing import Any

try:
    from docx.shared import RGBColor
except ModuleNotFoundError:  # The bundled document runtime is loaded only for export.
    RGBColor = Any  # type: ignore[misc,assignment]


NAVY = "172554"
BLUE = "2563EB"
MUTED = "64748B"


def export_funder_report_pptx(projection: dict[str, Any], output_path: str | Path) -> Path:
    """Create a dependency-free Arabic PPTX from the persisted projection."""
    from xml.sax.saxutils import escape
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    sections = projection.get("sections", [])
    slides = [
        ("حزمة التقرير الجاهز للتمويل", f"Snapshot: {projection.get('snapshot_id', '')}"),
        ("ملخص القرار", f"الحالة: {projection.get('readiness_status', '')}"),
        ("الأقسام", "\n".join(f"{row.get('section_id')}: {row.get('title')}" for row in sections)),
        ("الفجوات قبل الإصدار", "\n".join(str(gap) for gap in projection.get("gaps", [])) or "لا توجد فجوات مسجلة"),
        ("سجل التتبع", f"مدخلات غير معتمدة: {(projection.get('input_traceability') or {}).get('unreviewed_count', 0)}"),
    ]
    def text_shape(name: str, text: str, y: int, size: int) -> str:
        return f'<p:sp><p:nvSpPr><p:cNvPr id="{y}" name="{name}"/><p:cNvSpPr/><p:nvPr/></p:nvSpPr><p:spPr><a:xfrm><a:off x="900000" y="{y}"/><a:ext cx="10300000" cy="4000000"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom></p:spPr><p:txBody><a:bodyPr rtl="1"/><a:lstStyle/><a:p><a:r><a:rPr lang="ar-SA" sz="{size * 100}"/><a:t>{escape(str(text))}</a:t></a:r></a:p></p:txBody></p:sp>'
    def slide_xml(title: str, body: str) -> str:
        return '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><p:sld xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"><p:cSld><p:spTree><p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr><p:grpSpPr/>' + text_shape("Title", title, 700000, 28) + text_shape("Body", body, 2500000, 16) + '</p:spTree></p:cSld><p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr></p:sld>'
    content_types = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/ppt/presentation.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml"/><Override PartName="/ppt/slideMasters/slideMaster1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slideMaster+xml"/><Override PartName="/ppt/slideLayouts/slideLayout1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slideLayout+xml"/>' + ''.join(f'<Override PartName="/ppt/slides/slide{i}.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/>' for i in range(1, len(slides) + 1)) + '</Types>'
    rels = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
    with ZipFile(output, "w", compression=ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", content_types)
        archive.writestr("_rels/.rels", rels + '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="ppt/presentation.xml"/></Relationships>')
        archive.writestr("ppt/presentation.xml", '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><p:presentation xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"><p:sldMasterIdLst><p:sldMasterId id="2147483648" r:id="rId1"/></p:sldMasterIdLst><p:sldIdLst>' + ''.join(f'<p:sldId id="{255 + i}" r:id="rId{i + 1}"/>' for i in range(1, len(slides) + 1)) + '</p:sldIdLst><p:sldSz cx="12192000" cy="6858000" type="screen16x9"/></p:presentation>')
        archive.writestr("ppt/_rels/presentation.xml.rels", rels + '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideMaster" Target="slideMasters/slideMaster1.xml"/>' + ''.join(f'<Relationship Id="rId{i + 1}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide" Target="slides/slide{i}.xml"/>' for i in range(1, len(slides) + 1)) + '</Relationships>')
        archive.writestr("ppt/slideMasters/slideMaster1.xml", '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><p:sldMaster xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"><p:cSld name="Master"><p:spTree><p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr><p:grpSpPr/></p:spTree></p:cSld><p:sldLayoutIdLst><p:sldLayoutId id="1" r:id="rId1"/></p:sldLayoutIdLst></p:sldMaster>')
        archive.writestr("ppt/slideMasters/_rels/slideMaster1.xml.rels", rels + '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout" Target="../slideLayouts/slideLayout1.xml"/></Relationships>')
        archive.writestr("ppt/slideLayouts/slideLayout1.xml", '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><p:sldLayout xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"><p:cSld name="Blank"><p:spTree><p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr><p:grpSpPr/></p:spTree></p:cSld></p:sldLayout>')
        for index, (title, body) in enumerate(slides, 1):
            archive.writestr(f"ppt/slides/slide{index}.xml", slide_xml(title, body))
            archive.writestr(f"ppt/slides/_rels/slide{index}.xml.rels", rels + '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout" Target="../slideLayouts/slideLayout1.xml"/></Relationships>')
    return output


def _set_rtl(paragraph: Any) -> None:
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    paragraph.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    ppr = paragraph._p.get_or_add_pPr()
    bidi = ppr.find(qn("w:bidi"))
    if bidi is None:
        bidi = OxmlElement("w:bidi")
        ppr.append(bidi)


def _set_font(run: Any, *, size: float = 11, color: Any = "1E293B", bold: bool = False) -> None:
    from docx.shared import Pt, RGBColor
    from docx.oxml.ns import qn
    run.font.name = "Arial"
    run._element.get_or_add_rPr().rFonts.set(qn("w:ascii"), "Arial")
    run._element.get_or_add_rPr().rFonts.set(qn("w:hAnsi"), "Arial")
    run._element.get_or_add_rPr().rFonts.set(qn("w:cs"), "Arial")
    run.font.size = Pt(size)
    run.font.color.rgb = RGBColor.from_string(color if isinstance(color, str) else str(color))
    run.bold = bold


def _shade(cell: Any, fill: str) -> None:
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    tcpr = cell._tc.get_or_add_tcPr()
    shd = tcpr.find(qn("w:shd"))
    if shd is None:
        shd = OxmlElement("w:shd")
        tcpr.append(shd)
    shd.set(qn("w:fill"), fill)


def _set_cell_text(cell: Any, text: Any, *, bold: bool = False, color: Any = "1E293B") -> None:
    from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT
    cell.text = ""
    paragraph = cell.paragraphs[0]
    _set_rtl(paragraph)
    run = paragraph.add_run(str(text if text not in (None, "") else "—"))
    _set_font(run, bold=bold, color=color)
    cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER


def _table(doc: Any, headers: list[str], rows: list[list[Any]]) -> Any:
    from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_TABLE_ALIGNMENT
    from docx.shared import Inches
    table = doc.add_table(rows=1, cols=len(headers))
    table.alignment = WD_TABLE_ALIGNMENT.RIGHT
    table.autofit = False
    for index, header in enumerate(headers):
        _set_cell_text(table.rows[0].cells[index], header, bold=True, color=RGBColor(255, 255, 255))
        _shade(table.rows[0].cells[index], "172554")
    for row in rows:
        cells = table.add_row().cells
        for index, value in enumerate(row):
            _set_cell_text(cells[index], value)
            if len(table.rows) % 2 == 0:
                _shade(cells[index], "F8FAFC")
    for row in table.rows:
        for cell in row.cells:
            cell.width = Inches(6.5 / len(headers))
    return table


def export_funder_report_docx(projection: dict[str, Any], output_path: str | Path) -> Path:
    """Create a read-only Arabic DOCX from a funder projection."""
    try:
        from docx import Document
        from docx.oxml.ns import qn
        from docx.shared import Inches, Pt, RGBColor
    except ModuleNotFoundError as exc:
        raise RuntimeError("DOCX export requires the bundled document runtime") from exc
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    doc = Document()
    section = doc.sections[0]
    section.top_margin = Inches(0.75)
    section.bottom_margin = Inches(0.7)
    section.left_margin = Inches(0.8)
    section.right_margin = Inches(0.8)
    section.header_distance = Inches(0.35)
    section.footer_distance = Inches(0.35)
    normal = doc.styles["Normal"]
    normal.font.name = "Arial"
    normal._element.rPr.rFonts.set(qn("w:ascii"), "Arial")
    normal._element.rPr.rFonts.set(qn("w:hAnsi"), "Arial")
    normal._element.rPr.rFonts.set(qn("w:cs"), "Arial")
    normal.font.size = Pt(10.5)

    header = section.header.paragraphs[0]
    _set_rtl(header)
    run = header.add_run("ASIE | حزمة التقرير الجاهز للتمويل")
    _set_font(run, size=9, color=MUTED, bold=True)
    footer = section.footer.paragraphs[0]
    _set_rtl(footer)
    run = footer.add_run(f"Snapshot: {projection.get('snapshot_id', '')} | عقد {projection.get('contract_id', '')}")
    _set_font(run, size=8, color=MUTED)

    title = doc.add_paragraph()
    _set_rtl(title)
    title.paragraph_format.space_after = Pt(4)
    run = title.add_run("حزمة التقرير الجاهز للتمويل")
    _set_font(run, size=24, color=NAVY, bold=True)
    subtitle = doc.add_paragraph()
    _set_rtl(subtitle)
    run = subtitle.add_run(f"حالة الحزمة: {projection.get('readiness_status', 'unknown')} | Profile: {projection.get('profile_id', '')}")
    _set_font(run, size=11, color=BLUE, bold=True)

    note = doc.add_paragraph()
    _set_rtl(note)
    run = note.add_run("تنبيه: هذه الوثيقة إسقاط قراءة من Snapshot محفوظ. لا تعيد الحساب ولا تمثل قبولاً أو ضماناً من أي جهة تمويل.")
    _set_font(run, size=10, color="7C2D12", bold=True)

    h = doc.add_heading("ملخص الحزمة", level=1)
    _set_rtl(h)
    _set_font(h.runs[0], size=16, color=BLUE, bold=True)
    summary = next((row for row in projection.get("sections", []) if row.get("section_id") == "02-executive-summary"), {})
    payload = summary.get("payload") or {}
    _table(doc, ["البند", "القيمة"], [["Snapshot", projection.get("snapshot_id")], ["Run", projection.get("run_id")], ["حالة الجاهزية", projection.get("readiness_status")], ["الحكم", (payload.get("decision") or {}).get("sovereign_verdict", "—")]])

    h = doc.add_heading("ملف الجاهزية التمويلية", level=1)
    _set_rtl(h)
    profile = projection.get("profile_readiness") or {}
    _table(doc, ["المتطلب", "الحالة", "السبب"], [[row.get("label"), row.get("status"), row.get("reason") or "—"] for row in profile.get("checks", [])] or [["—", "not_ready", "لا يوجد ملف تحقق"]])

    h = doc.add_heading("الأقسام الستة عشر", level=1)
    _set_rtl(h)
    rows = [[row.get("section_id"), row.get("title"), row.get("status")] for row in projection.get("sections", [])]
    _table(doc, ["المعرف", "القسم", "الحالة"], rows)

    h = doc.add_heading("التوقعات المالية", level=1)
    _set_rtl(h)
    financial = next((row for row in projection.get("sections", []) if row.get("section_id") == "14-financial-expectations"), {})
    statements = (financial.get("payload") or {}).get("statements") or {}
    years = ((statements.get("income_statement") or {}).get("years") or [])
    _table(doc, ["السنة", "الإيرادات", "إجمالي الربح", "EBITDA", "EBIT", "التدفق التشغيلي"], [[row.get("year"), row.get("revenue"), row.get("gross_profit"), row.get("ebitda"), row.get("ebit"), row.get("net_operating_cashflow")] for row in years] or [["—", "لا توجد توقعات مالية جاهزة", "—", "—", "—", "—"]])

    h = doc.add_heading("الفجوات قبل الإصدار", level=1)
    _set_rtl(h)
    for gap in projection.get("gaps", []):
        paragraph = doc.add_paragraph(style="List Bullet")
        _set_rtl(paragraph)
        run = paragraph.add_run(str(gap))
        _set_font(run, size=10)

    h = doc.add_heading("سجل الأدلة والافتراضات", level=1)
    _set_rtl(h)
    evidence = projection.get("evidence") or {}
    _table(doc, ["البند", "القيمة"], [["Evidence Register", evidence.get("evidence_register_id")], ["Assumption refs", ", ".join(evidence.get("assumption_refs") or [])], ["Lineage entries", len(evidence.get("transformation_lineage") or [])]])
    doc.save(output)
    return output


def export_funder_report_pdf(
    projection: dict[str, Any], output_path: str | Path, renderer_path: str | Path | None = None
) -> Path:
    """Print the canonical Arabic HTML projection with a server-side renderer.

    The client browser is never involved. ``renderer_path`` (or the
    ``ASIE_PDF_RENDERER`` setting) identifies the pinned headless renderer in
    production. Chrome/Edge discovery is retained only as a local development
    fallback; Firefox/Safari/other client browsers can download the result
    identically through the API.
    """
    from backend.funder_report import render_funder_report_html

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    configured = renderer_path or os.environ.get("ASIE_PDF_RENDERER")
    browser = str(configured) if configured else (shutil.which("chrome") or shutil.which("msedge"))
    if browser is None:
        candidates = (
            Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
            Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
        )
        browser = next((str(path) for path in candidates if path.exists()), None)
    if browser is None:
        raise RuntimeError("PDF export requires a configured server-side PDF renderer")
    with tempfile.TemporaryDirectory(prefix="asie-funder-pdf-") as temp_dir:
        html_path = Path(temp_dir) / "funder-report.html"
        html_path.write_text(render_funder_report_html(projection), encoding="utf-8")
        command = [
            browser,
            "--headless",
            "--disable-gpu",
            "--no-sandbox",
            "--no-pdf-header-footer",
            f"--print-to-pdf={output.resolve()}",
            html_path.resolve().as_uri(),
        ]
        subprocess.run(command, check=True, capture_output=True, text=True)
    if not output.exists() or output.stat().st_size == 0:
        raise RuntimeError("PDF renderer returned without creating a file")
    return output
