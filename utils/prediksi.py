"""Prediksi kuat tekan 28 hari dari uji umur dini (3 / 7 / 14 hari).

Tiga metode (semua dinormalkan terhadap umur 28 hari):
  1. PBI 1971        : rasio umur tabel (semen biasa / kekuatan awal tinggi)
  2. SNI 03-2834 T.2 : rasio kuat tekan acuan umur t terhadap umur 28 hari
  3. ACI 209R-92     : f(t) = t / (a + b.t) x f28  (a=4,0 b=0,85 Tipe I; a=2,3 b=0,92 Tipe III; perawatan basah)
Hasil adalah PERKIRAAN; kuat tekan umur 28 hari tetap harus dibuktikan dengan pengujian.
"""
from __future__ import annotations

import math
from typing import Dict, List, Optional, Sequence

from standards import sni
from standards.base import interpolasi

UMUR_UJI = [3, 7, 14]
METODE = ["PBI 1971 (rasio umur)", "SNI 03-2834 Tabel 2 (rasio umur)", "ACI 209R-92 (hiperbolik)"]

_PBI = {
    "I/II/V": ([3, 7, 14, 21, 28, 90], [0.40, 0.65, 0.88, 0.95, 1.00, 1.20]),
    "III":    ([3, 7, 14, 21, 28, 90], [0.55, 0.75, 0.90, 0.95, 1.00, 1.15]),
}
_ACI209 = {"I/II/V": (4.0, 0.85), "III": (2.3, 0.92)}


def rasio_umur(metode: str, umur: float, kelompok_semen: str = "I/II/V", bentuk_kasar: str = "batu pecah",
               bentuk_uji: str = "silinder") -> float:
    """Rasio f(umur)/f(28 hari) menurut metode."""
    if metode == METODE[0]:
        xs, ys = _PBI[kelompok_semen]
        return interpolasi(umur, xs, ys)[0]
    if metode == METODE[1]:
        tab = sni.TABEL_2[bentuk_uji][kelompok_semen][bentuk_kasar]
        xs = sorted(tab)
        return interpolasi(umur, xs, [tab[x] / tab[28] for x in xs])[0]
    if metode == METODE[2]:
        a, b = _ACI209[kelompok_semen]
        return (umur / (a + b * umur)) / (28 / (a + b * 28))
    raise ValueError("Metode tidak dikenal.")


def prediksi_28_hari(f_uji: float, umur: float, kelompok_semen: str = "I/II/V",
                     bentuk_kasar: str = "batu pecah", bentuk_uji: str = "silinder") -> Dict[str, float]:
    return {m: f_uji / rasio_umur(m, umur, kelompok_semen, bentuk_kasar, bentuk_uji) for m in METODE}


def kurva_umur(f28: float, metode: str, umur_list: Sequence[float], kelompok_semen: str = "I/II/V",
               bentuk_kasar: str = "batu pecah", bentuk_uji: str = "silinder") -> List[float]:
    return [f28 * rasio_umur(metode, t, kelompok_semen, bentuk_kasar, bentuk_uji) for t in umur_list]


def ke_bentuk(nilai: float, dari: str, ke: str, faktor: float = 0.83) -> float:
    """Konversi kuat tekan antar bentuk benda uji: silinder = faktor x kubus."""
    if dari == ke:
        return nilai
    return nilai * faktor if (dari, ke) == ("kubus", "silinder") else nilai / faktor


def kuat_tekan_dari_beban(beban_kN: float, jenis: str, dimensi_mm: float) -> float:
    """MPa = N / mm2. jenis: 'silinder' (diameter) atau 'kubus' (rusuk)."""
    luas = math.pi * dimensi_mm ** 2 / 4 if jenis == "silinder" else dimensi_mm ** 2
    return beban_kN * 1000 / luas


def evaluasi(f28: float, fc: float, fcr: Optional[float]) -> tuple:
    """(status, pesan) membandingkan prediksi dengan f'c dan f'cr."""
    target = fcr if fcr else fc
    if f28 >= target:
        return "ok", f"Prediksi {f28:.1f} MPa >= target {target:.1f} MPa: kemungkinan besar memenuhi."
    if f28 >= fc:
        return "waspada", (f"Prediksi {f28:.1f} MPa di atas f'c ({fc:g}) tetapi di bawah f'cr ({target:.1f}): "
                           "margin tipis, pantau hasil umur berikutnya.")
    return "bahaya", f"Prediksi {f28:.1f} MPa di bawah f'c ({fc:g}): berisiko tidak memenuhi, pertimbangkan koreksi FAS."


def fas_diperlukan(fas_sekarang: float, f28_prediksi: float, fcr: float, k: float = sni.K_FAS_BAWAAN) -> float:
    """FAS yang disarankan agar f28 mencapai f'cr (model eksponensial yang sama dengan SNI otomatis)."""
    return fas_sekarang - math.log(fcr / f28_prediksi) / k
