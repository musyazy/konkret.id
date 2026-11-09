"""Mix design beton normal mengikuti SNI 03-2834-2000 (metode DOE).

Catatan: beberapa langkah SNI memakai GRAFIK (FAS dari Grafik 1, persen agregat halus
dari Grafik 13-15, berat isi beton dari Grafik 16). Pada versi awal ini nilai-nilai
tersebut diinput pengguna hasil pembacaan grafik.
"""
from __future__ import annotations

from typing import Optional

from standards.base import HasilMixDesign, Komposisi, Langkah
from utils.material_db import Agregat

NAMA = "SNI 03-2834-2000"
UKURAN_MAKS_TERSEDIA = [10, 20, 40]          # mm
BENTUK_AGREGAT = ["alami", "batu pecah"]

# Tabel 3 SNI 03-2834-2000: perkiraan kadar air bebas (kg/m3)
# {ukuran maks: {rentang slump (mm): (batu tak dipecahkan, batu pecah)}}
_TABEL_AIR = {
    10: {"0-10": (150, 180), "10-30": (180, 205), "30-60": (205, 230), "60-180": (225, 250)},
    20: {"0-10": (135, 170), "10-30": (160, 190), "30-60": (180, 210), "60-180": (195, 225)},
    40: {"0-10": (115, 155), "10-30": (140, 175), "30-60": (160, 190), "60-180": (175, 205)},
}


def _rentang_slump(slump_mm: float) -> str:
    if slump_mm <= 10:
        return "0-10"
    if slump_mm <= 30:
        return "10-30"
    if slump_mm <= 60:
        return "30-60"
    return "60-180"


def nilai_tambah(simpangan_baku: Optional[float], k: float = 1.64) -> float:
    """Margin M = k * s. Bila tidak ada data deviasi standar, SNI memakai M = 12 MPa."""
    return 12.0 if simpangan_baku is None else k * simpangan_baku


def kadar_air_bebas(slump_mm: float, ukuran_maks: int, bentuk_halus: str, bentuk_kasar: str) -> float:
    """W = 2/3 Wh + 1/3 Wk (Wh: air untuk agregat halus, Wk: untuk agregat kasar)."""
    baris = _TABEL_AIR[ukuran_maks][_rentang_slump(slump_mm)]
    wh = baris[0] if bentuk_halus == "alami" else baris[1]
    wk = baris[0] if bentuk_kasar == "alami" else baris[1]
    return 2 / 3 * wh + 1 / 3 * wk


def hitung_mix_design_sni(
    fc: float,                       # f'c (MPa)
    simpangan_baku: Optional[float],
    slump_mm: float,
    ukuran_maks: int,
    halus: Agregat,
    kasar: Agregat,
    fas_grafik: float,               # FAS hasil pembacaan Tabel 2 + Grafik 1
    persen_halus: float,             # % agregat halus terhadap agregat total (Grafik 13-15)
    berat_isi_beton: float,          # kg/m3 (Grafik 16)
    fas_maks: float = 0.60,
    semen_min: float = 275.0,
    semen_maks: Optional[float] = None,
    k: float = 1.64,
) -> HasilMixDesign:
    if ukuran_maks not in _TABEL_AIR:
        raise ValueError(f"Ukuran maksimum agregat harus salah satu dari {UKURAN_MAKS_TERSEDIA} mm.")
    if not 0 < persen_halus < 100:
        raise ValueError("Persen agregat halus harus di antara 0 dan 100.")

    langkah, peringatan = [], []
    add = lambda *a: langkah.append(Langkah(*a))

    margin = nilai_tambah(simpangan_baku, k)
    fcr = fc + margin
    add("Nilai tambah (margin)", round(margin, 2), "MPa",
        "k x s" if simpangan_baku is not None else "tanpa data: 12 MPa")
    add("Kuat tekan rata-rata target f'cr", round(fcr, 2), "MPa", "f'c + margin")

    air = kadar_air_bebas(slump_mm, ukuran_maks, halus.bentuk, kasar.bentuk)
    add("Kadar air bebas", round(air, 2), "kg/m3", "Tabel 3: 2/3 Wh + 1/3 Wk")

    fas = min(fas_grafik, fas_maks)
    add("FAS dipakai", round(fas, 3), "", f"min(FAS grafik {fas_grafik}, FAS maks {fas_maks})")

    semen = air / fas
    add("Kadar semen", round(semen, 2), "kg/m3", "air / FAS")
    if semen < semen_min:
        semen = semen_min
        fas = air / semen
        peringatan.append(f"Kadar semen < minimum, dipakai {semen_min:g} kg/m3 (FAS disesuaikan = {fas:.3f}).")
        add("Kadar semen disesuaikan", round(semen, 2), "kg/m3", "kadar semen minimum")
    if semen_maks is not None and semen > semen_maks:
        peringatan.append(f"Kadar semen {semen:.1f} kg/m3 melebihi batas maksimum {semen_maks:g} kg/m3.")

    p = persen_halus / 100
    bj_gab = p * halus.bj_ssd + (1 - p) * kasar.bj_ssd
    add("Berat jenis relatif agregat gabungan (SSD)", round(bj_gab, 3), "", "p x Ss_halus + (1-p) x Ss_kasar")

    gabungan = berat_isi_beton - semen - air
    halus_ssd = p * gabungan
    kasar_ssd = gabungan - halus_ssd
    add("Kadar agregat gabungan", round(gabungan, 2), "kg/m3", "berat isi beton - semen - air")
    add("Kadar agregat halus (SSD)", round(halus_ssd, 2), "kg/m3", "persen halus x gabungan")
    add("Kadar agregat kasar (SSD)", round(kasar_ssd, 2), "kg/m3", "gabungan - halus")
    if gabungan <= 0:
        raise ValueError("Berat isi beton terlalu kecil: kadar agregat gabungan <= 0. Periksa Grafik 16.")

    # Koreksi kadar air lapangan: air = B - (Ck-Ca)C/100 - (Dk-Da)D/100, dst.
    kor_h = (halus.kadar_air_pct - halus.penyerapan_pct) / 100
    kor_k = (kasar.kadar_air_pct - kasar.penyerapan_pct) / 100
    air_lap = air - kor_h * halus_ssd - kor_k * kasar_ssd
    halus_lap = halus_ssd * (1 + kor_h)
    kasar_lap = kasar_ssd * (1 + kor_k)
    add("Air yang ditambahkan (lapangan)", round(air_lap, 2), "kg/m3", "koreksi kadar air & penyerapan")
    if air_lap < 0:
        peringatan.append("Air lapangan negatif: kadar air agregat terlalu tinggi, periksa input.")

    # Pembanding dengan berat jenis relatif: densitas teoritis tidak dipakai di sini (lihat Grafik 16).
    return HasilMixDesign(
        standar=NAMA, fcr=fcr, fas=fas,
        teoritis=Komposisi(semen, air, halus_ssd, kasar_ssd), kondisi_teoritis="SSD",
        lapangan=Komposisi(semen, air_lap, halus_lap, kasar_lap),
        langkah=langkah, peringatan=peringatan,
    )
