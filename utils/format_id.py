"""Format angka & Rupiah gaya Indonesia: pemisah ribuan titik, desimal koma. Rupiah tanpa desimal."""
from __future__ import annotations

import re


def angka(nilai: float, desimal: int = 2) -> str:
    """1234.5 -> '1.234,50'"""
    teks = f"{nilai:,.{desimal}f}"
    return teks.replace(",", "\0").replace(".", ",").replace("\0", ".")


def rupiah(nilai: float) -> str:
    """1400 -> 'Rp 1.400' (selalu bulat, tanpa desimal)."""
    n = int(round(nilai))
    return ("-" if n < 0 else "") + "Rp " + f"{abs(n):,}".replace(",", ".")


def ribuan(nilai: float) -> str:
    """250000 -> '250.000'"""
    return f"{int(round(nilai)):,}".replace(",", ".")


def baca_rupiah(teks: str):
    """Baca isian pengguna ('Rp 250.000', '1.400', '1400', '1.400,50') menjadi int. None bila tidak valid."""
    s = re.sub(r"(?i)rp|\s", "", str(teks))
    if not s:
        return None
    s = s.replace(".", "").replace(",", ".") if "," in s else s.replace(".", "")
    try:
        n = float(s)
    except ValueError:
        return None
    return max(0, int(n + 0.5))


_BULAN = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus",
          "September", "Oktober", "November", "Desember"]


def tanggal_id(d) -> str:
    """date -> '5 November 2026'"""
    return f"{d.day} {_BULAN[d.month - 1]} {d.year}"
