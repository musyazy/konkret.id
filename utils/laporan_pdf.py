"""Render Dokumen (laporan / CoA) ke PDF A4 bergaya laporan resmi laboratorium (reportlab)."""
from __future__ import annotations

import io
import math
from typing import Dict
from xml.sax.saxutils import escape as _escape_xml

from reportlab.graphics.barcode.qr import QrCodeWidget
from reportlab.graphics.shapes import Drawing, Line, PolyLine, Rect, String, Circle
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.platypus import Flowable, KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from utils.dokumen import STATUS_KATA, Dokumen, Grafik, Tabel

BIRU = colors.HexColor("#1E3A8A")
ABU = colors.HexColor("#E5E7EB")
GARIS = colors.HexColor("#6B7280")
WARNA_STATUS = {"PASS": "#15803D", "WARNING": "#B45309", "ERROR": "#B91C1C", "INFO": "#1D4ED8"}
LEBAR = A4[0] - 36 * mm
_CACHE: Dict[str, bytes] = {}


def escape(teks: str) -> str:
    """Escape XML untuk Paragraph + pangkat tiga sebagai superskrip (glyph '³' tidak ada di sebagian pembaca PDF)."""
    return _escape_xml(teks).replace("³", "<super>3</super>")


def _t(teks) -> str:
    """Aman untuk font standar PDF (WinAnsi): ganti simbol di luar cp1252."""
    s = str(teks).replace("≤", "<=").replace("≥", ">=").replace("→", "->").replace("−", "-").replace("’", "'")
    return s.encode("cp1252", "replace").decode("cp1252")


def _gaya():
    d = dict(fontName="Helvetica", fontSize=8.5, leading=11)
    return dict(
        normal=ParagraphStyle("n", **d),
        kecil=ParagraphStyle("k", fontName="Helvetica", fontSize=7.8, leading=9.6),
        sel=ParagraphStyle("s", fontName="Helvetica", fontSize=7.8, leading=9.6),
        sel_kanan=ParagraphStyle("sk", fontName="Helvetica", fontSize=7.8, leading=9.6, alignment=TA_RIGHT),
        kepala=ParagraphStyle("h", fontName="Helvetica-Bold", fontSize=7.8, leading=9.6),
        kepala_kanan=ParagraphStyle("hk", fontName="Helvetica-Bold", fontSize=7.8, leading=9.6, alignment=TA_RIGHT),
        judul=ParagraphStyle("j", fontName="Helvetica-Bold", fontSize=13, leading=16, alignment=TA_CENTER),
        sub=ParagraphStyle("sb", fontName="Helvetica", fontSize=9.5, leading=12, alignment=TA_CENTER),
        nomor=ParagraphStyle("nm", fontName="Helvetica", fontSize=8.5, leading=11, alignment=TA_CENTER),
        seksi=ParagraphStyle("sc", fontName="Helvetica-Bold", fontSize=9.5, leading=12, textColor=colors.white),
        ket=ParagraphStyle("kt", fontName="Helvetica-Oblique", fontSize=7.5, leading=9.5, textColor=GARIS),
    )


def _sel(teks, gaya, status_ok=True) -> Paragraph:
    s = escape(_t(teks))
    if status_ok and str(teks) in STATUS_KATA:
        return Paragraph(f'<font color="{WARNA_STATUS[str(teks)]}"><b>{s}</b></font>', gaya)
    return Paragraph(s, gaya)


def _tabel(t: Tabel, g) -> list:
    lebar = t.lebar or [1] * len(t.kolom)
    total = sum(lebar)
    cw = [LEBAR * x / total for x in lebar]
    kanan = set(t.rata_kanan)
    data = [[Paragraph(f"<b>{escape(_t(k))}</b>", g["kepala_kanan"] if i in kanan else g["kepala"]) for i, k in enumerate(t.kolom)]]
    for b in t.baris:
        data.append([_sel(v, g["sel_kanan"] if i in kanan else g["sel"]) for i, v in enumerate(b)])
    tb = Table(data, colWidths=cw, repeatRows=1)
    tb.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), ABU), ("GRID", (0, 0), (-1, -1), 0.4, GARIS),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("TOPPADDING", (0, 0), (-1, -1), 2.2), ("BOTTOMPADDING", (0, 0), (-1, -1), 2.2),
        ("LEFTPADDING", (0, 0), (-1, -1), 4), ("RIGHTPADDING", (0, 0), (-1, -1), 4)]))
    out = []
    if t.judul:
        out.append(Paragraph(f"<b>{escape(_t(t.judul))}</b>", g["normal"]))
    return out + [tb, Spacer(1, 3 * mm)]


def _grafik(gr: Grafik, w: float = None, h: float = 62 * mm) -> Drawing:
    w = w or LEBAR
    d = Drawing(w, h)
    ml, mr, mt, mb = 34, 14, 16, 30
    pw, ph = w - ml - mr, h - mt - mb
    semua = [s for s, _ in gr.titik] + [s for s, _ in gr.batas_atas + gr.batas_bawah]
    lo, hi = math.log10(min(semua)), math.log10(max(semua))
    lo, hi = lo - 0.04, hi + 0.04
    X = lambda s: ml + (hi - math.log10(s)) / (hi - lo) * pw
    Y = lambda v: mb + max(0.0, min(100.0, v)) / 100 * ph
    d.add(Rect(ml, mb, pw, ph, strokeColor=GARIS, fillColor=None, strokeWidth=0.6))
    for v in range(0, 101, 20):
        d.add(Line(ml, Y(v), ml + pw, Y(v), strokeColor=colors.HexColor("#D1D5DB"), strokeWidth=0.3))
        d.add(String(ml - 4, Y(v) - 2.5, str(v), fontName="Helvetica", fontSize=6.5, textAnchor="end"))
    for s in sorted({s for s, _ in gr.titik}):
        d.add(Line(X(s), mb, X(s), mb + ph, strokeColor=colors.HexColor("#E5E7EB"), strokeWidth=0.3))
        d.add(String(X(s), mb - 8, f"{s:g}", fontName="Helvetica", fontSize=6.3, textAnchor="middle"))
    for pts in (gr.batas_atas, gr.batas_bawah):
        if len(pts) > 1:
            d.add(PolyLine([c for s, v in sorted(pts, reverse=True) for c in (X(s), Y(v))], strokeColor=colors.HexColor("#B91C1C"),
                           strokeWidth=0.9, strokeDashArray=[3, 2]))
    d.add(PolyLine([c for s, v in sorted(gr.titik, reverse=True) for c in (X(s), Y(v))], strokeColor=BIRU, strokeWidth=1.5))
    for s, v in gr.titik:
        d.add(Circle(X(s), Y(v), 1.6, fillColor=BIRU, strokeColor=BIRU))
    d.add(String(w / 2, h - 9, _t(gr.judul), fontName="Helvetica-Bold", fontSize=8.5, textAnchor="middle"))
    d.add(String(ml + pw / 2, 14, "Ukuran saringan (mm), skala log", fontName="Helvetica", fontSize=7, textAnchor="middle"))
    d.add(String(10, mb + ph / 2, "Lolos (%)", fontName="Helvetica", fontSize=7, textAnchor="middle", angle=90))
    d.add(Line(ml, 6, ml + 14, 6, strokeColor=BIRU, strokeWidth=1.5))
    d.add(String(ml + 17, 4, "Hasil uji", fontName="Helvetica", fontSize=6.5))
    d.add(Line(ml + 60, 6, ml + 74, 6, strokeColor=colors.HexColor("#B91C1C"), strokeWidth=0.9, strokeDashArray=[3, 2]))
    d.add(String(ml + 77, 4, _t(gr.keterangan or "Batas spesifikasi"), fontName="Helvetica", fontSize=6.5))
    return d


class Stempel(Flowable):
    """Stempel digital laboratorium (lingkaran ganda) dengan nama laboratorium, status, tanggal, dan kode."""

    def __init__(self, dok: Dokumen, ukuran=36 * mm):
        super().__init__()
        self.dok, self.ukuran = dok, ukuran
        self.width = self.height = ukuran

    def wrap(self, *_):
        return self.width, self.height

    def draw(self):
        c, r = self.canv, self.ukuran / 2
        c.saveState()
        c.translate(r, r)
        c.rotate(8)
        c.setStrokeColor(BIRU)
        c.setFillColor(BIRU)
        c.setLineWidth(1.6)
        c.circle(0, 0, r - 1.5, stroke=1, fill=0)
        c.setLineWidth(0.6)
        c.circle(0, 0, r - 4.5, stroke=1, fill=0)
        nama = _t(self.dok.kop["perusahaan"]).upper()
        kata, baris, cur = nama.split(), [], ""
        for k in kata:                                   # bungkus nama maks. 2 baris
            if len(cur) + len(k) + 1 <= 20 or not cur:
                cur = f"{cur} {k}".strip()
            else:
                baris.append(cur)
                cur = k
        baris = (baris + [cur])[:2]
        y = 13 if len(baris) == 2 else 9
        c.setFont("Helvetica-Bold", 5.8)
        for b_ in baris:
            c.drawCentredString(0, y, b_)
            y -= 7
        c.setFont("Helvetica-Bold", 7.2)
        c.drawCentredString(0, y - 3, "TERVERIFIKASI")
        c.setFont("Helvetica", 5.6)
        c.drawCentredString(0, y - 11, _t(self.dok.dicetak))
        c.drawCentredString(0, y - 18, self.dok.kode_verifikasi)
        c.restoreState()


def _qr(data: str, ukuran=22 * mm) -> Drawing:
    w = QrCodeWidget(data)
    x0, y0, x1, y1 = w.getBounds()
    d = Drawing(ukuran, ukuran, transform=[ukuran / (x1 - x0), 0, 0, ukuran / (y1 - y0), 0, 0])
    d.add(w)
    return d


def _kop(dok: Dokumen, g) -> list:
    kop = dok.kop
    isi = [[Paragraph(f"<b>{escape(_t(kop['perusahaan']))}</b>", ParagraphStyle("kp", fontName="Helvetica-Bold", fontSize=16, leading=19, alignment=TA_CENTER, textColor=BIRU))],
           [Paragraph(f"<b>{escape(_t(kop['divisi']))}</b>", ParagraphStyle("kd", fontName="Helvetica-Bold", fontSize=9.5, leading=12, alignment=TA_CENTER))]]
    if kop.get("alamat"):
        isi.append([Paragraph(escape(_t(kop["alamat"])), ParagraphStyle("ka", fontName="Helvetica", fontSize=8, leading=10, alignment=TA_CENTER))])
    tb = Table(isi, colWidths=[LEBAR])
    tb.setStyle(TableStyle([("LINEBELOW", (0, -1), (-1, -1), 2.2, BIRU), ("BOTTOMPADDING", (0, -1), (-1, -1), 5),
                            ("TOPPADDING", (0, 0), (-1, -1), 1), ("BOTTOMPADDING", (0, 0), (-1, -2), 1)]))
    return [tb, Spacer(1, 1.2 * mm), Table([[""]], colWidths=[LEBAR], rowHeights=[0.6], style=[("LINEBELOW", (0, 0), (-1, -1), 0.6, BIRU)]),
            Spacer(1, 4 * mm)]


def _meta(dok: Dokumen, g) -> Table:
    pasang = [dok.meta[i:i + 2] for i in range(0, len(dok.meta), 2)]
    data = []
    for p in pasang:
        baris = []
        for k, v in p:
            baris += [Paragraph(f"<b>{escape(_t(k))}</b>", g["sel"]), Paragraph(escape(_t(v)), g["sel"])]
        while len(baris) < 4:
            baris += ["", ""]
        data.append(baris)
    tb = Table(data, colWidths=[LEBAR * 0.17, LEBAR * 0.33, LEBAR * 0.17, LEBAR * 0.33])
    tb.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.4, GARIS), ("BACKGROUND", (0, 0), (0, -1), ABU), ("BACKGROUND", (2, 0), (2, -1), ABU),
                            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("TOPPADDING", (0, 0), (-1, -1), 2.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5)]))
    return tb


def _judul_seksi(teks: str, g) -> Table:
    tb = Table([[Paragraph(escape(_t(teks)), g["seksi"])]], colWidths=[LEBAR])
    tb.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), BIRU), ("TOPPADDING", (0, 0), (-1, -1), 2.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5)]))
    return tb


def _kesimpulan(dok: Dokumen, g) -> list:
    lv, label, teks = dok.kesimpulan
    warna = {"ok": "#15803D", "warn": "#B45309", "error": "#B91C1C"}[lv]
    kotak = Table([[Paragraph(f'<font size="12" color="{warna}"><b>{escape(_t(label))}</b></font>', ParagraphStyle("kl", alignment=TA_CENTER, leading=15))],
                   [Paragraph(escape(_t(teks)), g["normal"])]], colWidths=[LEBAR])
    kotak.setStyle(TableStyle([("BOX", (0, 0), (-1, -1), 1.2, colors.HexColor(warna)), ("BACKGROUND", (0, 0), (-1, 0), ABU),
                               ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4)]))
    return [_judul_seksi("KESIMPULAN" if dok.jenis == "laporan" else "PERNYATAAN MUTU", g), Spacer(1, 2 * mm), kotak, Spacer(1, 3 * mm)]


def _tanda_tangan(dok: Dokumen, g) -> Table:
    p = dok.penandatangan
    sel_ttd = lambda peran, nama, jab: [
        Paragraph(f"<b>{escape(_t(peran))}</b>", ParagraphStyle("t", fontName="Helvetica", fontSize=8, alignment=TA_CENTER)), Spacer(1, 21 * mm),
        Paragraph(f"<b><u>{escape(_t(nama)) if nama else '&nbsp;' * 28}</u></b>", ParagraphStyle("tn", fontName="Helvetica", fontSize=8.2, alignment=TA_CENTER)),
        Paragraph(escape(_t(jab)), ParagraphStyle("tj", fontName="Helvetica", fontSize=7.5, alignment=TA_CENTER, textColor=GARIS))]
    stempel = [Paragraph("<b>Stempel Digital</b>", ParagraphStyle("t3", fontName="Helvetica", fontSize=8, alignment=TA_CENTER)), Spacer(1, 1.5 * mm),
               Stempel(dok), Spacer(1, 1 * mm),
               Paragraph("Kode verifikasi: " + dok.kode_verifikasi, ParagraphStyle("kv", fontName="Helvetica", fontSize=6.8, alignment=TA_CENTER, textColor=GARIS))]
    qr = [Paragraph("<b>Verifikasi</b>", ParagraphStyle("t4", fontName="Helvetica", fontSize=8, alignment=TA_CENTER)), Spacer(1, 1.5 * mm),
          _qr(f"{dok.kop['perusahaan']} | {dok.nomor} | {dok.kode_verifikasi}"), Spacer(1, 1 * mm),
          Paragraph("Pindai untuk kode dokumen", ParagraphStyle("qs", fontName="Helvetica", fontSize=6.8, alignment=TA_CENTER, textColor=GARIS))]
    tb = Table([[sel_ttd(*p[0]), sel_ttd(*p[1]), stempel, qr]], colWidths=[LEBAR * 0.28, LEBAR * 0.30, LEBAR * 0.24, LEBAR * 0.18])
    tb.setStyle(TableStyle([("BOX", (0, 0), (-1, -1), 0.5, GARIS), ("INNERGRID", (0, 0), (-1, -1), 0.5, GARIS),
                            ("VALIGN", (0, 0), (-1, -1), "TOP"), ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                            ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 5)]))
    return tb


class _Kanvas(canvas.Canvas):
    """Kanvas dengan nomor halaman 'i dari N' dan header kecil pada halaman lanjutan."""
    dok: Dokumen = None

    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self._hal = []

    def showPage(self):
        self._hal.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        total = len(self._hal)
        for i, state in enumerate(self._hal, 1):
            self.__dict__.update(state)
            self._hiasan(i, total)
            super().showPage()
        super().save()

    def _hiasan(self, i, total):
        dok = self.dok
        self.setFont("Helvetica", 7.2)
        self.setFillColor(GARIS)
        self.setStrokeColor(GARIS)
        self.setLineWidth(0.4)
        self.line(18 * mm, 13 * mm, A4[0] - 18 * mm, 13 * mm)
        self.drawString(18 * mm, 9 * mm, _t(f"{dok.nomor}  |  Kode verifikasi {dok.kode_verifikasi}"))
        self.drawRightString(A4[0] - 18 * mm, 9 * mm, f"Halaman {i} dari {total}")
        if dok.draft:
            self.saveState()
            self.setFillColor(colors.HexColor("#B91C1C"))
            self.setFillAlpha(0.10)
            self.setFont("Helvetica-Bold", 110)
            self.translate(A4[0] / 2, A4[1] / 2)
            self.rotate(35)
            self.drawCentredString(0, 0, "DRAFT")
            self.restoreState()
        if i > 1:
            self.drawString(18 * mm, A4[1] - 11 * mm, _t(f"{dok.kop['perusahaan']}  |  {dok.nomor}"))
            self.line(18 * mm, A4[1] - 12.5 * mm, A4[0] - 18 * mm, A4[1] - 12.5 * mm)


def buat_pdf(dok: Dokumen) -> bytes:
    """PDF A4 bergaya laporan resmi. Hasil di-cache berdasarkan kode verifikasi isi dokumen."""
    kunci = f"{dok.jenis}:{dok.kode_verifikasi}"
    if kunci in _CACHE:
        return _CACHE[kunci]
    g = _gaya()
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=17 * mm, bottomMargin=19 * mm,
                            title=_t(dok.judul), author=_t(dok.kop["perusahaan"]), subject=_t(dok.nomor))
    isi = []
    if dok.draft:
        banner = Table([[Paragraph(f'<font color="#B91C1C"><b>{escape(_t(dok.pesan_draft))}</b></font>', ParagraphStyle("dr", fontName="Helvetica", fontSize=9.5, leading=12, alignment=TA_CENTER))]],
                       colWidths=[LEBAR])
        banner.setStyle(TableStyle([("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#B91C1C")), ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FEE2E2")),
                                    ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]))
        isi += [banner, Spacer(1, 3 * mm)]
    isi += _kop(dok, g)
    isi += [Paragraph(f"<b>{escape(_t(dok.judul))}</b>", g["judul"]), Spacer(1, 1 * mm), Paragraph(escape(_t(dok.subjudul)), g["sub"]),
            Paragraph(f"Nomor: {escape(_t(dok.nomor))}", g["nomor"]), Spacer(1, 3 * mm), _meta(dok, g), Spacer(1, 4 * mm)]
    if dok.jenis == "coa":                       # sertifikat: pernyataan di bagian atas
        isi += _kesimpulan(dok, g)
    for s in dok.seksi:
        bagian = [_judul_seksi(s.judul, g), Spacer(1, 2 * mm)]
        for p in s.paragraf:
            bagian += [Paragraph(escape(_t(p)), g["normal"]), Spacer(1, 2 * mm)]
        isi.append(KeepTogether(bagian + (_tabel(s.tabel[0], g) if s.tabel and len(s.tabel[0].baris) < 18 else [])))
        for i, t in enumerate(s.tabel):
            if i == 0 and len(t.baris) < 18:
                continue
            isi += _tabel(t, g)
        if s.grafik:
            isi += [_grafik(s.grafik), Spacer(1, 3 * mm)]
    if dok.jenis == "laporan":
        isi += _kesimpulan(dok, g)
    if dok.catatan:
        isi += [Paragraph("<b>Catatan</b>", g["normal"])] + [Paragraph(f"{i}. {escape(_t(c))}", g["kecil"]) for i, c in enumerate(dok.catatan, 1)]
        isi.append(Spacer(1, 4 * mm))
    isi.append(KeepTogether([Paragraph("Disahkan oleh:", g["normal"]), Spacer(1, 1.5 * mm), _tanda_tangan(dok, g)]))

    kanvas = type("KanvasDok", (_Kanvas,), {"dok": dok})
    doc.build(isi, canvasmaker=kanvas)
    if len(_CACHE) > 8:
        _CACHE.pop(next(iter(_CACHE)))
    _CACHE[kunci] = buf.getvalue()
    return _CACHE[kunci]
