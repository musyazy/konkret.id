"""Render Dokumen (laporan / CoA) ke Word (.docx) tanpa pustaka tambahan: WordprocessingML ditulis langsung (zipfile),
grafik, stempel, dan QR digambar dengan Pillow."""
from __future__ import annotations

import io
import math
import zipfile
from typing import List, Tuple
from xml.sax.saxutils import escape

from PIL import Image, ImageDraw, ImageFont

from utils.dokumen import STATUS_KATA, Dokumen, Grafik, Tabel

WARNA = {"PASS": "15803D", "WARNING": "B45309", "ERROR": "B91C1C", "INFO": "1D4ED8"}
LEBAR_DXA = 9638          # A4 dengan margin 2 cm


def _font(ukuran: int, tebal: bool = False):
    try:
        return ImageFont.load_default(size=ukuran)
    except TypeError:                                   # Pillow lama
        return ImageFont.load_default()


# ----------------------------------------------------------------------------- gambar (PNG)
def png_gradasi(g: Grafik, w: int = 1500, h: int = 600) -> bytes:
    im = Image.new("RGB", (w, h), "white")
    d = ImageDraw.Draw(im)
    ml, mr, mt, mb = 110, 40, 60, 110
    pw, ph = w - ml - mr, h - mt - mb
    semua = [s for s, _ in g.titik] + [s for s, _ in g.batas_atas + g.batas_bawah]
    lo, hi = math.log10(min(semua)) - 0.04, math.log10(max(semua)) + 0.04
    X = lambda s: ml + (hi - math.log10(s)) / (hi - lo) * pw
    Y = lambda v: mt + ph - max(0.0, min(100.0, v)) / 100 * ph
    f1, f2 = _font(24), _font(30)
    d.rectangle([ml, mt, ml + pw, mt + ph], outline=(100, 100, 100), width=2)
    for v in range(0, 101, 20):
        d.line([ml, Y(v), ml + pw, Y(v)], fill=(220, 220, 220), width=1)
        d.text((ml - 12, Y(v)), str(v), fill="black", font=f1, anchor="rm")
    for s in sorted({s for s, _ in g.titik}):
        d.line([X(s), mt, X(s), mt + ph], fill=(235, 235, 235), width=1)
        d.text((X(s), mt + ph + 10), f"{s:g}", fill="black", font=f1, anchor="mt")
    for pts in (g.batas_atas, g.batas_bawah):
        xy = [(X(s), Y(v)) for s, v in sorted(pts, reverse=True)]
        for (x1, y1), (x2, y2) in zip(xy, xy[1:]):          # garis putus-putus
            n = max(int(math.hypot(x2 - x1, y2 - y1) / 14), 1)
            for i in range(0, n, 2):
                d.line([x1 + (x2 - x1) * i / n, y1 + (y2 - y1) * i / n, x1 + (x2 - x1) * (i + 1) / n, y1 + (y2 - y1) * (i + 1) / n],
                       fill=(185, 28, 28), width=3)
    xy = [(X(s), Y(v)) for s, v in sorted(g.titik, reverse=True)]
    d.line(xy, fill=(30, 58, 138), width=6)
    for x, y in xy:
        d.ellipse([x - 7, y - 7, x + 7, y + 7], fill=(30, 58, 138))
    d.text((w / 2, 12), g.judul, fill="black", font=f2, anchor="mt")
    d.text((ml + pw / 2, h - 40), "Ukuran saringan (mm), skala log", fill="black", font=f1, anchor="mm")
    d.text((22, mt + ph / 2), "Lolos (%)", fill="black", font=f1, anchor="mm")
    d.text((ml, h - 12), "Biru: hasil uji   Merah putus-putus: batas spesifikasi" + (f" ({g.keterangan})" if g.keterangan else ""),
           fill=(80, 80, 80), font=_font(20), anchor="ls")
    buf = io.BytesIO(); im.save(buf, "PNG"); return buf.getvalue()


def png_stempel(dok: Dokumen, ukuran: int = 520) -> bytes:
    im = Image.new("RGBA", (ukuran, ukuran), (255, 255, 255, 0))
    d = ImageDraw.Draw(im)
    biru = (30, 58, 138, 255)
    d.ellipse([8, 8, ukuran - 8, ukuran - 8], outline=biru, width=10)
    d.ellipse([34, 34, ukuran - 34, ukuran - 34], outline=biru, width=3)
    kata, baris, cur = dok.kop["perusahaan"].upper().split(), [], ""
    for k in kata:
        if len(cur) + len(k) + 1 <= 18 or not cur:
            cur = f"{cur} {k}".strip()
        else:
            baris.append(cur); cur = k
    baris = (baris + [cur])[:2]
    y = ukuran / 2 - 95 if len(baris) == 2 else ukuran / 2 - 70
    for b in baris:
        d.text((ukuran / 2, y), b, fill=biru, font=_font(34), anchor="mm"); y += 42
    d.text((ukuran / 2, y + 14), "TERVERIFIKASI", fill=biru, font=_font(44), anchor="mm")
    d.text((ukuran / 2, y + 66), dok.dicetak, fill=biru, font=_font(30), anchor="mm")
    d.text((ukuran / 2, y + 104), dok.kode_verifikasi, fill=biru, font=_font(30), anchor="mm")
    im = im.rotate(8, resample=Image.BICUBIC)
    buf = io.BytesIO(); im.save(buf, "PNG"); return buf.getvalue()


def png_qr(data: str, sel: int = 8) -> bytes:
    from reportlab.graphics.barcode.qr import QrCodeWidget
    w = QrCodeWidget(data); w.qr.make(); m = w.qr.modules; n = len(m)
    im = Image.new("RGB", ((n + 2) * sel,) * 2, "white"); d = ImageDraw.Draw(im)
    for r, baris in enumerate(m):
        for c, v in enumerate(baris):
            if v:
                d.rectangle([(c + 1) * sel, (r + 1) * sel, (c + 2) * sel - 1, (r + 2) * sel - 1], fill="black")
    buf = io.BytesIO(); im.save(buf, "PNG"); return buf.getvalue()


# ----------------------------------------------------------------------------- WordprocessingML
def _run(teks, tebal=False, miring=False, ukuran=19, warna=None, garis_bawah=False) -> str:
    rpr = ("<w:b/>" if tebal else "") + ("<w:i/>" if miring else "") + ("<w:u w:val=\"single\"/>" if garis_bawah else "") \
        + (f'<w:color w:val="{warna}"/>' if warna else "") + f'<w:sz w:val="{ukuran}"/><w:szCs w:val="{ukuran}"/>'
    return f'<w:r><w:rPr>{rpr}</w:rPr><w:t xml:space="preserve">{escape(str(teks))}</w:t></w:r>'


def _para(runs: str, rata="left", sesudah=60, sebelum=0, shade=None, batas=None) -> str:
    ppr = f'<w:spacing w:before="{sebelum}" w:after="{sesudah}"/><w:jc w:val="{rata}"/>'
    if shade:
        ppr = f'<w:shd w:val="clear" w:color="auto" w:fill="{shade}"/>' + ppr
    if batas:
        ppr = f'<w:pBdr><w:bottom w:val="single" w:sz="{batas[0]}" w:space="1" w:color="{batas[1]}"/></w:pBdr>' + ppr
    return f"<w:p><w:pPr>{ppr}</w:pPr>{runs}</w:p>"


def _sel_teks(v, tebal=False, ukuran=16) -> str:
    v = str(v)
    if v in STATUS_KATA:
        return _run(v, True, ukuran=ukuran, warna=WARNA[v])
    return _run(v, tebal, ukuran=ukuran)


def _tabel(t: Tabel) -> str:
    lebar = t.lebar or [1] * len(t.kolom)
    tot = sum(lebar)
    cw = [int(LEBAR_DXA * x / tot) for x in lebar]
    kanan = set(t.rata_kanan)
    tepi = "".join(f'<w:{s} w:val="single" w:sz="4" w:space="0" w:color="6B7280"/>' for s in ("top", "left", "bottom", "right", "insideH", "insideV"))
    xml = [f'<w:tbl><w:tblPr><w:tblW w:w="{sum(cw)}" w:type="dxa"/><w:tblBorders>{tepi}</w:tblBorders><w:tblLayout w:type="fixed"/>'
           f'<w:tblCellMar><w:left w:w="70" w:type="dxa"/><w:right w:w="70" w:type="dxa"/></w:tblCellMar></w:tblPr><w:tblGrid>'
           + "".join(f'<w:gridCol w:w="{c}"/>' for c in cw) + "</w:tblGrid>"]

    def baris(sel, kepala=False):
        out = '<w:tr><w:trPr><w:cantSplit/>' + ("<w:tblHeader/>" if kepala else "") + "</w:trPr>"
        for i, (v, c) in enumerate(zip(sel, cw)):
            shade = '<w:shd w:val="clear" w:color="auto" w:fill="E5E7EB"/>' if kepala else ""
            out += (f'<w:tc><w:tcPr><w:tcW w:w="{c}" w:type="dxa"/>{shade}<w:vAlign w:val="center"/></w:tcPr>'
                    + _para(_sel_teks(v, kepala), "right" if i in kanan else "left", sesudah=0) + "</w:tc>")
        return out + "</w:tr>"
    xml.append(baris(t.kolom, True))
    xml += [baris(b) for b in t.baris]
    xml.append("</w:tbl>")
    cap = _para(_run(t.judul, True, ukuran=18), sesudah=40) if t.judul else ""
    return cap + "".join(xml) + _para("", sesudah=80)


class _Gambar:
    def __init__(self):
        self.berkas: List[Tuple[str, bytes]] = []

    def tambah(self, png: bytes, lebar_cm: float, tinggi_cm: float, nama: str) -> str:
        n = len(self.berkas) + 1
        self.berkas.append((f"image{n}.png", png))
        cx, cy = int(lebar_cm * 360000), int(tinggi_cm * 360000)
        return (f'<w:r><w:drawing><wp:inline distT="0" distB="0" distL="0" distR="0"><wp:extent cx="{cx}" cy="{cy}"/>'
                f'<wp:docPr id="{n}" name="{escape(nama)}"/><a:graphic xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">'
                f'<a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture"><pic:pic xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture">'
                f'<pic:nvPicPr><pic:cNvPr id="{n}" name="{escape(nama)}"/><pic:cNvPicPr/></pic:nvPicPr><pic:blipFill><a:blip r:embed="rIdImg{n}"/>'
                f'<a:stretch><a:fillRect/></a:stretch></pic:blipFill><pic:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm>'
                f'<a:prstGeom prst="rect"><a:avLst/></a:prstGeom></pic:spPr></pic:pic></a:graphicData></a:graphic></wp:inline></w:drawing></w:r>')


def _sel_ttd(isi: str, lebar: int) -> str:
    return (f'<w:tc><w:tcPr><w:tcW w:w="{lebar}" w:type="dxa"/></w:tcPr>{isi}</w:tc>')


def buat_docx(dok: Dokumen) -> bytes:
    gb = _Gambar()
    kop = dok.kop
    b: List[str] = []
    if dok.draft:
        b.append(_para(_run(dok.pesan_draft, True, ukuran=22, warna="B91C1C"), "center", shade="FEE2E2"))
    b.append(_para(_run(kop["perusahaan"], True, ukuran=34, warna="1E3A8A"), "center", sesudah=0))
    b.append(_para(_run(kop["divisi"], True, ukuran=20), "center", sesudah=0))
    if kop.get("alamat"):
        b.append(_para(_run(kop["alamat"], ukuran=16), "center", sesudah=0))
    b.append(_para("", sesudah=60, batas=(18, "1E3A8A")))
    b.append(_para(_run(dok.judul, True, ukuran=26), "center", sesudah=20, sebelum=120))
    b.append(_para(_run(dok.subjudul, ukuran=19), "center", sesudah=0))
    b.append(_para(_run(f"Nomor: {dok.nomor}", ukuran=17), "center", sesudah=100))
    pasang = [dok.meta[i:i + 2] for i in range(0, len(dok.meta), 2)]
    baris_meta = []
    for p in pasang:
        r = []
        for k, v in p:
            r += [k, v]
        while len(r) < 4:
            r += ["", ""]
        baris_meta.append(r)
    b.append(_tabel(Tabel(["Keterangan", "Isi", "Keterangan", "Isi"], baris_meta, lebar=[1.7, 3.3, 1.7, 3.3])))

    def kesimpulan():
        lv, label, teks = dok.kesimpulan
        warna = {"ok": "15803D", "warn": "B45309", "error": "B91C1C"}[lv]
        return (_para(_run("KESIMPULAN" if dok.jenis == "laporan" else "PERNYATAAN MUTU", True, ukuran=20, warna="FFFFFF"), shade="1E3A8A", sebelum=100)
                + _para(_run(label, True, ukuran=28, warna=warna), "center", shade="E5E7EB", sesudah=20)
                + _para(_run(teks, ukuran=19), sesudah=100))
    if dok.jenis == "coa":
        b.append(kesimpulan())
    for s in dok.seksi:
        b.append(_para(_run(s.judul, True, ukuran=20, warna="FFFFFF"), shade="1E3A8A", sebelum=100))
        b += [_para(_run(p, ukuran=18)) for p in s.paragraf]
        b += [_tabel(t) for t in s.tabel]
        if s.grafik:
            b.append(_para(gb.tambah(png_gradasi(s.grafik), 16.0, 6.4, s.grafik.judul), "center"))
    if dok.jenis == "laporan":
        b.append(kesimpulan())
    if dok.catatan:
        b.append(_para(_run("Catatan", True, ukuran=18)))
        b += [_para(_run(f"{i}. {c}", ukuran=16), sesudah=20) for i, c in enumerate(dok.catatan, 1)]
    b.append(_para(_run("Disahkan oleh:", True, ukuran=18), sebelum=160))
    (p1, n1, j1), (p2, n2, j2) = dok.penandatangan
    qr = png_qr(f"{kop['perusahaan']} | {dok.nomor} | {dok.kode_verifikasi}")
    k = [2300, 2500, 2700, 2138]
    ttd = lambda peran, nama, jab: (_para(_run(peran, True, ukuran=17), "center") + _para("", sesudah=900)
                                    + _para(_run(nama or " " * 26, True, ukuran=17, garis_bawah=True), "center", sesudah=0)
                                    + _para(_run(jab, ukuran=15, warna="6B7280"), "center", sesudah=0))
    stempel = (_para(_run("Stempel Digital", True, ukuran=17), "center") + _para(gb.tambah(png_stempel(dok), 3.2, 3.2, "stempel"), "center", sesudah=0)
               + _para(_run("Kode verifikasi: " + dok.kode_verifikasi, ukuran=14, warna="6B7280"), "center", sesudah=0))
    qrx = (_para(_run("Verifikasi", True, ukuran=17), "center") + _para(gb.tambah(qr, 2.2, 2.2, "qr"), "center", sesudah=0)
           + _para(_run("Pindai untuk kode dokumen", ukuran=14, warna="6B7280"), "center", sesudah=0))
    tepi = "".join(f'<w:{s} w:val="single" w:sz="4" w:space="0" w:color="6B7280"/>' for s in ("top", "left", "bottom", "right", "insideH", "insideV"))
    b.append(f'<w:tbl><w:tblPr><w:tblW w:w="{sum(k)}" w:type="dxa"/><w:tblBorders>{tepi}</w:tblBorders><w:tblLayout w:type="fixed"/></w:tblPr><w:tblGrid>'
             + "".join(f'<w:gridCol w:w="{c}"/>' for c in k) + "</w:tblGrid><w:tr><w:trPr><w:cantSplit/></w:trPr>"
             + _sel_ttd(ttd(p1, n1, j1), k[0]) + _sel_ttd(ttd(p2, n2, j2), k[1]) + _sel_ttd(stempel, k[2]) + _sel_ttd(qrx, k[3]) + "</w:tr></w:tbl>")
    b.append(_para(""))

    ns = ('xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
          'xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"')
    sect = ('<w:sectPr><w:footerReference w:type="default" r:id="rIdFooter"/><w:pgSz w:w="11906" w:h="16838"/>'
            '<w:pgMar w:top="1134" w:right="1134" w:bottom="1134" w:left="1134" w:header="567" w:footer="567" w:gutter="0"/></w:sectPr>')
    dokumen = f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:document {ns}><w:body>{"".join(b)}{sect}</w:body></w:document>'
    fld = lambda instr: (f'<w:r><w:fldChar w:fldCharType="begin"/></w:r><w:r><w:instrText xml:space="preserve"> {instr} </w:instrText></w:r>'
                         f'<w:r><w:fldChar w:fldCharType="separate"/></w:r>{_run("1", ukuran=14)}<w:r><w:fldChar w:fldCharType="end"/></w:r>')
    footer = (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:ftr {ns}><w:p><w:pPr><w:pBdr><w:top w:val="single" w:sz="4" w:space="1" w:color="6B7280"/></w:pBdr>'
              f'<w:tabs><w:tab w:val="right" w:pos="{LEBAR_DXA}"/></w:tabs></w:pPr>{_run(f"{dok.nomor} | Kode verifikasi {dok.kode_verifikasi}", ukuran=14, warna="6B7280")}'
              f'<w:r><w:tab/></w:r>{_run("Halaman ", ukuran=14, warna="6B7280")}{fld("PAGE")}{_run(" dari ", ukuran=14, warna="6B7280")}{fld("NUMPAGES")}</w:p></w:ftr>')
    styles = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
              '<w:docDefaults><w:rPrDefault><w:rPr><w:rFonts w:ascii="Arial" w:hAnsi="Arial" w:cs="Arial"/><w:sz w:val="19"/></w:rPr></w:rPrDefault></w:docDefaults>'
              '<w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/></w:style></w:styles>')
    rel = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
           '<Relationship Id="rIdStyles" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>'
           '<Relationship Id="rIdFooter" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/footer" Target="footer1.xml"/>'
           + "".join(f'<Relationship Id="rIdImg{i}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="media/{n}"/>'
                     for i, (n, _) in enumerate(gb.berkas, 1)) + "</Relationships>")
    tipe = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/>'
            '<Default Extension="png" ContentType="image/png"/>'
            '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
            '<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>'
            '<Override PartName="/word/footer1.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.footer+xml"/></Types>')
    root = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>')
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", tipe); z.writestr("_rels/.rels", root); z.writestr("word/document.xml", dokumen)
        z.writestr("word/styles.xml", styles); z.writestr("word/footer1.xml", footer); z.writestr("word/_rels/document.xml.rels", rel)
        for n, data in gb.berkas:
            z.writestr(f"word/media/{n}", data)
    return buf.getvalue()
