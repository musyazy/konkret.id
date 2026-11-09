"""Render Dokumen ke HTML berlatar putih bersih untuk pratinjau dan cetak fisik (Ctrl+P / tombol Cetak)."""
from __future__ import annotations

import html
import math

try:
    from reportlab.graphics.barcode.qr import QrCodeWidget
except ImportError:
    QrCodeWidget = None

from utils.dokumen import STATUS_KATA, Dokumen, Grafik, Tabel

_KELAS = {"PASS": "pass", "WARNING": "warn", "ERROR": "err", "INFO": "info"}

CSS = """
*{box-sizing:border-box} html{overflow-y:auto;overscroll-behavior:auto} body{margin:0;background:#fff;color:#111;font-family:Arial,Helvetica,sans-serif;font-size:10.5pt}
.halaman{max-width:190mm;margin:0 auto;padding:8mm 4mm 10mm}
.bar{display:flex;justify-content:flex-end;gap:8px;margin-bottom:8px}
.bar button{background:#1E3A8A;color:#fff;border:0;border-radius:6px;padding:8px 16px;font-weight:700;cursor:pointer}
.kop{text-align:center;border-bottom:3px double #1E3A8A;padding-bottom:6px;margin-bottom:10px}
.kop .n{font-size:20pt;font-weight:800;color:#1E3A8A;letter-spacing:.04em}
.kop .d{font-size:11pt;font-weight:700;margin-top:2px}.kop .a{font-size:9pt;margin-top:2px}
h1{font-size:14pt;text-align:center;margin:10px 0 2px}.sub{text-align:center;font-size:10.5pt;margin:0}.no{text-align:center;font-size:9.5pt;margin:2px 0 10px}
table{width:100%;border-collapse:collapse;margin:4px 0 10px}
th,td{border:1px solid #666;padding:3px 6px;font-size:9pt;vertical-align:middle}
th{background:#E5E7EB;text-align:left}.r{text-align:right}
.meta td.k{background:#E5E7EB;font-weight:700;width:17%}
h2{background:#1E3A8A;color:#fff;font-size:10.5pt;margin:12px 0 6px;padding:3px 8px}
.cap{font-weight:700;font-size:9.5pt;margin:6px 0 2px}
.pass{color:#15803D;font-weight:700}.warn{color:#B45309;font-weight:700}.err{color:#B91C1C;font-weight:700}.info{color:#1D4ED8;font-weight:700}
.kes{border:2px solid;margin:6px 0 10px}.kes .l{text-align:center;font-weight:800;font-size:13pt;background:#E5E7EB;padding:4px}
.kes .t{padding:6px 10px;font-size:10pt}
.catatan{font-size:9pt}.ttd{table-layout:fixed}.ttd td{height:44mm;vertical-align:top;text-align:center;padding:6px}
.ttd .nama{margin-top:22mm;font-weight:700;text-decoration:underline}.ttd .jab{color:#555;font-size:8.5pt}
.stempel{width:34mm;height:34mm;margin:4px auto;border:3px double #1E3A8A;border-radius:50%;color:#1E3A8A;transform:rotate(-8deg);
display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;font-size:6.5pt;font-weight:700;line-height:1.5;padding:4mm}
.stempel .v{font-size:8.5pt}.kv{font-size:7.5pt;color:#555}
.foot{border-top:1px solid #666;margin-top:10px;padding-top:3px;font-size:8pt;color:#555;display:flex;justify-content:space-between}
svg text{font-family:Arial,Helvetica,sans-serif}
.draft{border:1px solid #B91C1C;background:#FEE2E2;color:#B91C1C;font-weight:700;text-align:center;padding:4px;margin-bottom:8px}
.wm{position:fixed;top:38%;left:12%;font-size:130px;font-weight:800;color:rgba(185,28,28,.10);transform:rotate(-30deg);pointer-events:none;z-index:0}
@page{size:A4;margin:14mm 14mm 16mm}
@media print{.bar{display:none}.halaman{max-width:none;padding:0} h2,.kes,.ttd,table{break-inside:avoid} svg{break-inside:avoid}}
"""


def _e(x) -> str:
    return html.escape(str(x))


def _sel(v) -> str:
    v = str(v)
    return f'<span class="{_KELAS[v]}">{_e(v)}</span>' if v in STATUS_KATA else _e(v)


def _tabel(t: Tabel) -> str:
    kanan = set(t.rata_kanan)
    kepala = "".join(f'<th class="{"r" if i in kanan else ""}">{_e(k)}</th>' for i, k in enumerate(t.kolom))
    baris = "".join("<tr>" + "".join(f'<td class="{"r" if i in kanan else ""}">{_sel(v)}</td>' for i, v in enumerate(b)) + "</tr>" for b in t.baris)
    cap = f'<div class="cap">{_e(t.judul)}</div>' if t.judul else ""
    return f"{cap}<table><thead><tr>{kepala}</tr></thead><tbody>{baris}</tbody></table>"


def _svg_gradasi(g: Grafik, w: int = 680, h: int = 270) -> str:
    ml, mr, mt, mb = 46, 14, 26, 52
    pw, ph = w - ml - mr, h - mt - mb
    semua = [s for s, _ in g.titik] + [s for s, _ in g.batas_atas + g.batas_bawah]
    lo, hi = math.log10(min(semua)) - 0.04, math.log10(max(semua)) + 0.04
    X = lambda s: ml + (hi - math.log10(s)) / (hi - lo) * pw
    Y = lambda v: mt + ph - max(0.0, min(100.0, v)) / 100 * ph
    o = [f'<svg viewBox="0 0 {w} {h}" width="100%" xmlns="http://www.w3.org/2000/svg">',
         f'<rect x="{ml}" y="{mt}" width="{pw}" height="{ph}" fill="none" stroke="#666"/>',
         f'<text x="{w / 2}" y="16" text-anchor="middle" font-size="12" font-weight="700">{_e(g.judul)}</text>']
    for v in range(0, 101, 20):
        o.append(f'<line x1="{ml}" x2="{ml + pw}" y1="{Y(v):.1f}" y2="{Y(v):.1f}" stroke="#ddd"/>'
                 f'<text x="{ml - 6}" y="{Y(v) + 3:.1f}" text-anchor="end" font-size="9">{v}</text>')
    for s in sorted({s for s, _ in g.titik}):
        o.append(f'<line x1="{X(s):.1f}" x2="{X(s):.1f}" y1="{mt}" y2="{mt + ph}" stroke="#eee"/>'
                 f'<text x="{X(s):.1f}" y="{mt + ph + 13}" text-anchor="middle" font-size="9">{s:g}</text>')
    for pts in (g.batas_atas, g.batas_bawah):
        if len(pts) > 1:
            o.append('<polyline fill="none" stroke="#B91C1C" stroke-width="1.3" stroke-dasharray="5,3" points="'
                     + " ".join(f"{X(s):.1f},{Y(v):.1f}" for s, v in sorted(pts, reverse=True)) + '"/>')
    o.append('<polyline fill="none" stroke="#1E3A8A" stroke-width="2.2" points="'
             + " ".join(f"{X(s):.1f},{Y(v):.1f}" for s, v in sorted(g.titik, reverse=True)) + '"/>')
    o += [f'<circle cx="{X(s):.1f}" cy="{Y(v):.1f}" r="2.6" fill="#1E3A8A"/>' for s, v in g.titik]
    o.append(f'<text x="{ml + pw / 2}" y="{h - 22}" text-anchor="middle" font-size="10">Ukuran saringan (mm), skala log</text>'
             f'<text x="12" y="{mt + ph / 2}" font-size="10" text-anchor="middle" transform="rotate(-90 12 {mt + ph / 2})">Lolos (%)</text>'
             f'<line x1="{ml}" x2="{ml + 22}" y1="{h - 8}" y2="{h - 8}" stroke="#1E3A8A" stroke-width="2.2"/>'
             f'<text x="{ml + 27}" y="{h - 5}" font-size="9">Hasil uji</text>'
             f'<line x1="{ml + 90}" x2="{ml + 112}" y1="{h - 8}" y2="{h - 8}" stroke="#B91C1C" stroke-width="1.3" stroke-dasharray="5,3"/>'
             f'<text x="{ml + 117}" y="{h - 5}" font-size="9">{_e(g.keterangan or "Batas spesifikasi")}</text></svg>')
    return "".join(o)


def _svg_qr(data: str, ukuran: int = 84) -> str:
    w = QrCodeWidget(data)
    w.qr.make()
    m = w.qr.modules
    n = len(m)
    sel = ukuran / (n + 2)
    kotak = "".join(f'<rect x="{(c + 1) * sel:.2f}" y="{(r + 1) * sel:.2f}" width="{sel:.2f}" height="{sel:.2f}"/>'
                    for r, baris in enumerate(m) for c, v in enumerate(baris) if v)
    return f'<svg width="{ukuran}" height="{ukuran}" viewBox="0 0 {ukuran} {ukuran}" xmlns="http://www.w3.org/2000/svg"><g fill="#000">{kotak}</g></svg>'


def _stempel(dok: Dokumen) -> str:
    return (f'<div class="stempel"><div>{_e(dok.kop["perusahaan"].upper())}</div><div class="v">TERVERIFIKASI</div>'
            f'<div>{_e(dok.dicetak)}</div><div>{_e(dok.kode_verifikasi)}</div></div>')


def _ttd(dok: Dokumen) -> str:
    a, b = dok.penandatangan
    sel = lambda p: (f'<td><b>{_e(p[0])}</b><div class="nama">{_e(p[1]) or "&nbsp;" * 30}</div><div class="jab">{_e(p[2])}</div></td>')
    qr = _svg_qr(f"{dok.kop['perusahaan']} | {dok.nomor} | {dok.kode_verifikasi}")
    return (f'<table class="ttd"><tr>{sel(a)}{sel(b)}<td><b>Stempel Digital</b>{_stempel(dok)}<div class="kv">Kode verifikasi: {_e(dok.kode_verifikasi)}</div></td>'
            f'<td><b>Verifikasi</b><div style="margin-top:6px">{qr}</div><div class="kv">Pindai untuk kode dokumen</div></td></tr></table>')


def _kesimpulan(dok: Dokumen) -> str:
    lv, label, teks = dok.kesimpulan
    warna = {"ok": "#15803D", "warn": "#B45309", "error": "#B91C1C"}[lv]
    judul = "KESIMPULAN" if dok.jenis == "laporan" else "PERNYATAAN MUTU"
    return (f'<h2>{judul}</h2><div class="kes" style="border-color:{warna}"><div class="l" style="color:{warna}">{_e(label)}</div>'
            f'<div class="t">{_e(teks)}</div></div>')


def buat_html(dok: Dokumen) -> str:
    kop = dok.kop
    alamat = f'<div class="a">{_e(kop["alamat"])}</div>' if kop.get("alamat") else ""
    pasang = [dok.meta[i:i + 2] for i in range(0, len(dok.meta), 2)]
    meta = "".join("<tr>" + "".join(f'<td class="k">{_e(k)}</td><td>{_e(v)}</td>' for k, v in p) + ("<td></td><td></td>" if len(p) < 2 else "") + "</tr>"
                   for p in pasang)
    isi = ([f'<div class="wm">DRAFT</div><div class="draft">{_e(dok.pesan_draft)}</div>'] if dok.draft else []) + [f'<div class="bar"><button onclick="window.print()">🖨️ Cetak / Simpan PDF</button></div>',
           f'<div class="kop"><div class="n">{_e(kop["perusahaan"])}</div><div class="d">{_e(kop["divisi"])}</div>{alamat}</div>',
           f'<h1>{_e(dok.judul)}</h1><p class="sub">{_e(dok.subjudul)}</p><p class="no">Nomor: {_e(dok.nomor)}</p>',
           f'<table class="meta">{meta}</table>']
    if dok.jenis == "coa":
        isi.append(_kesimpulan(dok))
    for s in dok.seksi:
        isi.append(f"<h2>{_e(s.judul)}</h2>")
        isi += [f"<p>{_e(p)}</p>" for p in s.paragraf]
        isi += [_tabel(t) for t in s.tabel]
        if s.grafik:
            isi.append(_svg_gradasi(s.grafik))
    if dok.jenis == "laporan":
        isi.append(_kesimpulan(dok))
    if dok.catatan:
        isi.append('<div class="catatan"><b>Catatan</b><ol>' + "".join(f"<li>{_e(c)}</li>" for c in dok.catatan) + "</ol></div>")
    isi += ["<p><b>Disahkan oleh:</b></p>", _ttd(dok),
            f'<div class="foot"><span>{_e(dok.nomor)} | Kode verifikasi {_e(dok.kode_verifikasi)}</span><span>Dicetak {_e(dok.dicetak)}</span></div>']
    return (f'<!DOCTYPE html><html lang="id"><head><meta charset="utf-8"><title>{_e(dok.judul)} - {_e(dok.nomor)}</title>'
            f'<style>{CSS}</style></head><body><div class="halaman">{"".join(isi)}</div></body></html>')
