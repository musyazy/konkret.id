"""Mix design beton normal mengikuti ACI 211.1-91 (satuan SI).

Langkah: air pencampur & udara (berdasarkan slump + ukuran maks) -> FAS (dari f'cr)
-> semen -> volume agregat kasar (berdasarkan MK pasir & berat isi) -> agregat halus
(metode massa beton atau metode volume absolut) -> koreksi kadar air lapangan.
"""
from __future__ import annotations

from typing import Optional

from standards.base import HasilMixDesign, Komposisi, Langkah, interpolasi
from utils.material_db import Agregat

NAMA = "ACI 211.1-91"
UKURAN_MAKS_TERSEDIA = [9.5, 12.5, 19.0, 25.0, 37.5, 50.0, 75.0, 150.0]   # mm
PAPARAN = ["ringan", "sedang", "ekstrem"]
_IDX = {u: i for i, u in enumerate(UKURAN_MAKS_TERSEDIA)}

# Tabel A1.5.3.3: air pencampur (kg/m3), kolom mengikuti UKURAN_MAKS_TERSEDIA. None = tidak tersedia.
_AIR_NORMAL = {
    "25-50":   [207, 199, 190, 179, 166, 154, 130, 113],
    "75-100":  [228, 216, 205, 193, 181, 169, 145, 124],
    "150-175": [243, 228, 216, 202, 190, 178, 160, None],
}
_AIR_AE = {
    "25-50":   [181, 175, 168, 160, 150, 142, 122, 107],
    "75-100":  [202, 193, 184, 175, 165, 157, 133, 119],
    "150-175": [216, 205, 197, 184, 174, 166, 154, None],
}
_UDARA_TERPERANGKAP = [3, 2.5, 2, 1.5, 1, 0.5, 0.3, 0.2]           # % (beton tanpa tambahan udara)
_UDARA_TOTAL = {                                                   # % (beton dengan tambahan udara)
    "ringan":  [4.5, 4, 3.5, 3, 2.5, 2, 1.5, 1],
    "sedang":  [6, 5.5, 5, 4.5, 4.5, 4, 3.5, 3],
    "ekstrem": [7.5, 7, 6, 6, 5.5, 5, 4.5, 4],
}
# Tabel A1.5.3.4(a): f'cr 28 hari (MPa) -> FAS
_FAS_NORMAL = ([15, 20, 25, 30, 35, 40], [0.79, 0.69, 0.61, 0.54, 0.47, 0.42])
_FAS_AE = ([15, 20, 25, 30, 35], [0.70, 0.60, 0.52, 0.45, 0.39])
# Tabel A1.5.3.6: volume agregat kasar padat kering per m3 beton, untuk MK pasir 2.4 / 2.6 / 2.8 / 3.0
_MK_KOLOM = [2.4, 2.6, 2.8, 3.0]
_VOL_KASAR = [
    [0.50, 0.48, 0.46, 0.44], [0.59, 0.57, 0.55, 0.53], [0.66, 0.64, 0.62, 0.60],
    [0.71, 0.69, 0.67, 0.65], [0.75, 0.73, 0.71, 0.69], [0.78, 0.76, 0.74, 0.72],
    [0.82, 0.80, 0.78, 0.76], [0.87, 0.85, 0.83, 0.81],
]
# Tabel A1.5.3.7.1: perkiraan awal massa beton segar (kg/m3)
_MASSA_NORMAL = [2280, 2310, 2345, 2380, 2410, 2445, 2490, 2530]
_MASSA_AE = [2200, 2190, 2165, 2155, 2120, 2100, 2045, 2000]


def hitung_fcr(fc: float, simpangan_baku: Optional[float] = None, k: float = 1.64) -> float:
    """f'cr = f'c + k*s bila ada data; bila tidak, memakai tabel ACI 318 (versi SI)."""
    if simpangan_baku is not None:
        return fc + k * simpangan_baku
    if fc < 21:
        return fc + 7.0
    if fc <= 35:
        return fc + 8.3
    return 1.10 * fc + 5.0


def _kelas_slump(slump_mm: float) -> str:
    if slump_mm <= 62.5:
        return "25-50"
    return "75-100" if slump_mm <= 125 else "150-175"


def hitung_mix_design_aci(
    fc: float,
    slump_mm: float,
    ukuran_maks: float,
    halus: Agregat,
    kasar: Agregat,
    bj_semen: float = 3.15,
    simpangan_baku: Optional[float] = None,
    beton_ae: bool = False,
    paparan: str = "ringan",
    fas_maks: Optional[float] = None,
    metode_halus: str = "volume",        # "volume" (volume absolut) | "massa" (perkiraan massa beton)
    k: float = 1.64,
) -> HasilMixDesign:
    if ukuran_maks not in _IDX:
        raise ValueError(f"Ukuran maksimum agregat harus salah satu dari {UKURAN_MAKS_TERSEDIA} mm.")
    if kasar.berat_isi is None or halus.modulus_kehalusan is None:
        raise ValueError("ACI 211.1 membutuhkan berat isi agregat kasar dan modulus kehalusan pasir.")

    i = _IDX[ukuran_maks]
    langkah, peringatan = [], []
    add = lambda *a: langkah.append(Langkah(*a))

    # 1. Kuat tekan target
    fcr = hitung_fcr(fc, simpangan_baku, k)
    add("Kuat tekan rata-rata target f'cr", round(fcr, 2), "MPa", "f'c + k.s" if simpangan_baku is not None else "tabel ACI 318 (tanpa data)")

    # 2. Air pencampur & udara
    kelas = _kelas_slump(slump_mm)
    if slump_mm < 25 or slump_mm > 175:
        peringatan.append("Slump di luar rentang 25-175 mm pada tabel ACI; dipakai rentang terdekat.")
    air = (_AIR_AE if beton_ae else _AIR_NORMAL)[kelas][i]
    if air is None:
        raise ValueError("Kombinasi slump 150-175 mm dan ukuran maks 150 mm tidak tersedia pada tabel ACI.")
    udara = _UDARA_TOTAL[paparan][i] if beton_ae else _UDARA_TERPERANGKAP[i]
    add("Air pencampur", air, "kg/m3", f"Tabel A1.5.3.3 (slump {kelas} mm, {ukuran_maks:g} mm)")
    add("Kadar udara", udara, "%", "udara total (AE)" if beton_ae else "udara terperangkap")

    # 3. FAS
    xs, ys = _FAS_AE if beton_ae else _FAS_NORMAL
    fas, ekstra = interpolasi(fcr, xs, ys)
    if ekstra:
        peringatan.append(f"f'cr {fcr:.1f} MPa di luar rentang Tabel A1.5.3.4(a) ({xs[0]}-{xs[-1]} MPa); FAS diekstrapolasi, mohon diverifikasi.")
    if fas_maks is not None:
        fas = min(fas, fas_maks)
    add("Faktor air semen", round(fas, 3), "", "Tabel A1.5.3.4(a), interpolasi linear")

    # 4. Semen
    semen = air / fas
    add("Kadar semen", round(semen, 2), "kg/m3", "air / FAS")

    # 5. Agregat kasar
    mk = halus.modulus_kehalusan
    if not _MK_KOLOM[0] <= mk <= _MK_KOLOM[-1]:
        peringatan.append(f"Modulus kehalusan {mk:.2f} di luar 2.4-3.0 (Tabel A1.5.3.6); nilai ditahan pada batas tabel.")
    vol_kasar, _ = interpolasi(min(max(mk, 2.4), 3.0), _MK_KOLOM, _VOL_KASAR[i])
    kasar_kering = vol_kasar * kasar.berat_isi
    add("Volume agregat kasar padat kering", round(vol_kasar, 4), "m3", "Tabel A1.5.3.6")
    add("Berat agregat kasar (kering)", round(kasar_kering, 2), "kg/m3", "volume x berat isi")

    # 6. Agregat halus: dua metode
    massa_beton = (_MASSA_AE if beton_ae else _MASSA_NORMAL)[i]
    halus_massa = massa_beton - air - semen - kasar_kering
    vol_bahan = (air / 1000 + semen / (bj_semen * 1000)
                 + kasar_kering / (kasar.bj_curah_kering * 1000) + udara / 100)
    halus_volume = (1 - vol_bahan) * halus.bj_curah_kering * 1000
    add("Perkiraan massa beton segar", massa_beton, "kg/m3", "Tabel A1.5.3.7.1")
    add("Agregat halus - metode massa beton", round(halus_massa, 2), "kg/m3", "massa beton - air - semen - kasar")
    add("Agregat halus - metode volume absolut", round(halus_volume, 2), "kg/m3", "(1 - volume bahan lain) x Sd x 1000")
    halus_kering = halus_volume if metode_halus == "volume" else halus_massa
    if halus_kering <= 0:
        raise ValueError("Berat agregat halus <= 0. Periksa input (berat isi, berat jenis, ukuran maks).")

    # 7. Koreksi kadar air lapangan
    sw_h = (halus.kadar_air_pct - halus.penyerapan_pct) / 100     # air permukaan pasir
    sw_k = (kasar.kadar_air_pct - kasar.penyerapan_pct) / 100
    air_lap = air - sw_h * halus_kering - sw_k * kasar_kering
    halus_lap = halus_kering * (1 + halus.kadar_air_pct / 100)
    kasar_lap = kasar_kering * (1 + kasar.kadar_air_pct / 100)
    add("Air yang ditambahkan (lapangan)", round(air_lap, 2), "kg/m3", "air - air permukaan agregat")
    if air_lap < 0:
        peringatan.append("Air lapangan negatif: kadar air agregat terlalu tinggi, periksa input.")

    return HasilMixDesign(
        standar=NAMA, fcr=fcr, fas=fas,
        teoritis=Komposisi(semen, air, halus_kering, kasar_kering), kondisi_teoritis="kering oven",
        lapangan=Komposisi(semen, air_lap, halus_lap, kasar_lap),
        langkah=langkah, peringatan=peringatan,
    )
