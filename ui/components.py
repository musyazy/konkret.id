"""Komponen tampilan bersama: badge status, tabel HTML bersih, format Rupiah."""
import html

import pandas as pd
import streamlit as st

from utils import format_id
from utils.checks import tingkat_dari_deviasi  # noqa: F401  (dipakai modul UI lain)

_NAMA = {"ok": "PASS", "warn": "WARNING", "error": "ERROR", "info": "INFO"}


def badge(teks=None, tingkat: str = "ok") -> str:
    """Badge HTML. tingkat: ok (hijau) | warn (amber) | error (merah) | info (biru)."""
    return f'<span class="badge {tingkat}">{html.escape(str(teks or _NAMA[tingkat]))}</span>'


def gabung_tingkat(daftar) -> str:
    daftar = list(daftar)
    return "error" if "error" in daftar else "warn" if "warn" in daftar else "ok"


def _sel(v, desimal):
    if isinstance(v, float):
        return "-" if v != v else f"{v:.{desimal}f}"
    return html.escape(str(v))


def tabel_html(df: pd.DataFrame, kolom_html=(), desimal: int = 2) -> str:
    """Tabel HTML satu baris (tanpa spasi awal agar tidak terbaca sebagai blok kode Markdown).
    Kolom di `kolom_html` berisi HTML (mis. badge) dan tidak di-escape."""
    kepala = "".join(f"<th>{html.escape(str(c))}</th>" for c in df.columns)
    baris = []
    for _, r in df.iterrows():
        sel = "".join(f"<td>{r[c] if c in kolom_html else _sel(r[c], desimal)}</td>" for c in df.columns)
        baris.append(f"<tr>{sel}</tr>")
    return f'<div class="tbl-wrap"><table class="tbl"><thead><tr>{kepala}</tr></thead><tbody>{"".join(baris)}</tbody></table></div>'


def tampilkan_tabel(df: pd.DataFrame, kolom_html=(), desimal: int = 2) -> None:
    st.markdown(tabel_html(df, kolom_html, desimal), unsafe_allow_html=True)


def format_rp(nilai: float) -> str:
    """Rupiah bulat tanpa desimal, mis. Rp 1.400."""
    return format_id.rupiah(nilai)
