"""Tabel interpolasi hasil digitalisasi grafik SNI 03-2834-2000 (Grafik 1, 14, 15, 16).

Sumber: gambar grafik pada file referensi APLIKOM_BETON.xlsx (sheet 'GRAFIK DAN TABEL FAS'), dibaca piksel demi piksel
dan dikalibrasi pada garis grid/penanda sumbu. Ketelitian: +-0,5 MPa (Grafik 1), +-0,3 poin persen (Grafik 14/15),
+-3 kg/m3 (Grafik 16). Grafik 13 (ukuran maks 10 mm) tidak ada pada file sehingga tidak tersedia.
Gambar Grafik 14 pada file tidak berjudul; pemetaan ke 20 mm berdasarkan urutan nilai terhadap Grafik 15 (40 mm).
"""
from __future__ import annotations

from typing import Dict, List, Optional, Tuple

import numpy as np

FAS_GRID = [round(0.30 + 0.05 * i, 2) for i in range(15)]

# Grafik 1: kuat tekan (MPa) pada FAS_GRID untuk kurva umur 3/7/28/91 hari. Kelompok semen: I/II/V (garis tegas), III (putus-putus).
GRAFIK_1: Dict[str, Dict[int, List[float]]] = {
    "I/II/V": {
        3: [26.2, 20.9, 16.8, 13.5, 11, 9, 7.4, 6.1, 5.1, 4.2, 3.6, 3.1, 2.6, 2.3, 2],
        7: [37.6, 32.7, 28, 23.8, 20.1, 16.9, 14.2, 11.9, 10, 8.5, 7.3, 6.3, 5.6, 5, 4.5],
        28: [54.6, 47.5, 41.2, 35.6, 30.8, 26.5, 22.9, 19.7, 17.1, 14.8, 12.8, 11.2, 9.8, 8.6, 7.6],
        91: [64.2, 57.7, 51.2, 45.1, 39.3, 34.1, 29.6, 25.6, 22.2, 19.3, 16.9, 15, 13.4, 12.1, 11.1],
    },
    "III": {
        3: [34.1, 29.2, 24.7, 20.8, 17.4, 14.5, 12.1, 10.1, 8.4, 7.1, 6, 5.1, 4.4, 3.8, 3.3],
        7: [44.1, 38.9, 33.8, 29.1, 24.8, 21, 17.8, 15, 12.7, 10.8, 9.2, 8, 6.9, 6.2, 5.5],
        28: [59.7, 52.7, 46.1, 40, 34.6, 29.8, 25.6, 22.1, 19.1, 16.6, 14.6, 12.9, 11.6, 10.6, 9.8],
        91: [68.4, 61, 54, 47.5, 41.6, 36.3, 31.6, 27.5, 24, 21.1, 18.5, 16.4, 14.7, 13.2, 12.1],
    },
}

# Grafik 14/15: persen pasir terhadap agregat total; tiap panel (kelas slump) = 5 garis lurus [(p di FAS 0,3; p di FAS 0,9)].
# Zona pasir z (1-4) = daerah antara garis ke-z dan ke-(z+1) dari atas.
PERSEN_PASIR: Dict[int, Dict[str, List[Tuple[float, float]]]] = {
    20: {
        "0-10": [(38.0, 53.0), (30.0, 43.25), (25.0, 35.0), (21.0, 29.25), (18.25, 25.25)],
        "10-30": [(32.75, 50.0), (27.25, 40.75), (21.75, 32.0), (18.0, 27.25), (16.25, 23.0)],
        "30-60": [(43.75, 59.75), (36.0, 49.75), (28.75, 39.0), (24.0, 33.25), (21.25, 29.0)],
        "60-180": [(51.0, 68.0), (42.0, 55.25), (33.0, 44.0), (28.0, 37.0), (24.0, 32.0)],
    },
    40: {
        "0-10": [(30.75, 47.0), (25.0, 38.5), (20.0, 30.25), (16.0, 25.25), (14.25, 22.0)],
        "10-30": [(40.0, 57.25), (33.0, 47.0), (27.0, 37.0), (22.0, 31.25), (18.75, 27.0)],
        "30-60": [(37.0, 53.25), (31.0, 44.0), (24.75, 35.0), (19.75, 29.25), (17.25, 25.5)],
        "60-180": [(43.75, 60.75), (36.25, 50.0), (29.0, 40.5), (23.75, 33.0), (20.25, 28.25)],
    },
}

# Grafik 16: berat isi beton basah (kg/m3) pada kadar air bebas 100 dan 260 kg/m3 untuk berat jenis agregat gabungan SSD
# (garis lurus). Asumsi agregat batu pecah.
GRAFIK_16: Dict[int, Tuple[float, float]] = {
    2400: (2308.8, 2162.7),
    2500: (2394.5, 2218.3),
    2600: (2475.2, 2275.7),
    2700: (2559.3, 2327.9),
    2800: (2646.8, 2388.6),
    2900: (2724.6, 2449.1),
}


_X = np.linspace(0.30, 1.00, 701)


def _kurva(kelompok: str, umur: int) -> np.ndarray:
    return np.interp(_X, FAS_GRID, GRAFIK_1[kelompok][umur])


def fas_dari_grafik1(fcr: float, f0: float, kelompok: str) -> Optional[float]:
    """FAS dari Grafik 1: kurva melalui (FAS 0,5; f0) dibentuk proporsional di antara dua kurva umur terdekat
    (prosedur menggambar kurva pada grafik cetak), lalu dibaca pada kuat tekan fcr.
    None bila fcr berada di luar jangkauan grafik (FAS 0,3-1,0)."""
    umur = sorted(GRAFIK_1[kelompok])
    c05 = [float(np.interp(0.5, FAS_GRID, GRAFIK_1[kelompok][u])) for u in umur]
    j = max(i for i in range(len(umur) - 1) if c05[i] <= f0 or i == 0) if f0 < c05[-1] else len(umur) - 2
    j = min(j, len(umur) - 2)
    t = (f0 - c05[j]) / (c05[j + 1] - c05[j])
    y = _kurva(kelompok, umur[j]) + t * (_kurva(kelompok, umur[j + 1]) - _kurva(kelompok, umur[j]))
    if not y[-1] <= fcr <= y[0]:
        return None
    return float(np.interp(fcr, y[::-1], _X[::-1]))


def kurva_grafik1(f0: float, kelompok: str) -> Tuple[List[float], List[float]]:
    """Titik kurva FAS - kuat tekan yang melalui (0,5; f0), untuk grafik di UI."""
    umur = sorted(GRAFIK_1[kelompok])
    c05 = [float(np.interp(0.5, FAS_GRID, GRAFIK_1[kelompok][u])) for u in umur]
    j = min(max(i for i in range(len(umur) - 1) if c05[i] <= f0 or i == 0) if f0 < c05[-1] else len(umur) - 2, len(umur) - 2)
    t = (f0 - c05[j]) / (c05[j + 1] - c05[j])
    y = _kurva(kelompok, umur[j]) + t * (_kurva(kelompok, umur[j + 1]) - _kurva(kelompok, umur[j]))
    return [round(float(x), 3) for x in _X[::10]], [round(float(v), 2) for v in y[::10]]


def persen_pasir_grafik(ukuran_maks: int, kelas_slump: str, zona: int, fas: float) -> Optional[Tuple[float, float, bool]]:
    """(batas bawah, batas atas, di_luar_rentang_FAS) persen pasir untuk zona 1-4, atau None bila grafik tidak tersedia."""
    if ukuran_maks not in PERSEN_PASIR or zona not in (1, 2, 3, 4):
        return None
    garis = PERSEN_PASIR[ukuran_maks][kelas_slump]
    nilai = [a + (b - a) * (fas - 0.3) / 0.6 for a, b in garis]
    return nilai[zona], nilai[zona - 1], not 0.3 <= fas <= 0.9


def berat_isi_grafik16(air_bebas: float, bj_gabungan_ssd: float) -> Tuple[float, bool]:
    """(berat isi beton basah kg/m3, di_luar_rentang) dari Grafik 16; bj_gabungan_ssd dalam kg/m3 (mis. 2508,7)."""
    sg = sorted(GRAFIK_16)
    pada_w = [GRAFIK_16[s][0] + (GRAFIK_16[s][1] - GRAFIK_16[s][0]) * (air_bebas - 100) / 160 for s in sg]
    nilai = float(np.interp(bj_gabungan_ssd, sg, pada_w))
    if bj_gabungan_ssd < sg[0] or bj_gabungan_ssd > sg[-1]:      # ekstrapolasi linear dari dua garis terdekat
        i = 0 if bj_gabungan_ssd < sg[0] else len(sg) - 2
        nilai = pada_w[i] + (pada_w[i + 1] - pada_w[i]) * (bj_gabungan_ssd - sg[i]) / (sg[i + 1] - sg[i])
    return nilai, not (100 <= air_bebas <= 260 and sg[0] <= bj_gabungan_ssd <= sg[-1])
