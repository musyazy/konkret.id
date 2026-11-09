"""Asisten slump vs w/c: koreksi air / semen / superplasticizer saat slump uji tidak sesuai target,
tanpa mengubah FAS rancangan.

Dua opsi:
  A. Air + semen: air diubah, semen diubah proporsional (FAS TETAP); volume pasta yang berubah
     dikompensasi dengan mengurangi/menambah pasir (volume 1 m3 tetap).
  B. Superplasticizer: dosis diubah, air dan semen TETAP (FAS tetap).
Aturan praktis (bisa diubah di UI; kalibrasi dengan trial mix):
  * ACI 211: ~10 lb air/yd3 per 1 in. slump = 2,33 kg/m3 per 10 mm.
  * Efektivitas SP: bawaan 25 mm per 0,1% dosis (sangat bergantung produk & semen).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

AIR_PER_10MM = 2.33
SLUMP_PER_01PCT = 25.0


def toleransi_slump(target_mm: float) -> float:
    """Toleransi slump ASTM C94: <=50 mm: +-15; 50-100: +-25; >100: +-40."""
    return 15.0 if target_mm <= 50 else 25.0 if target_mm <= 100 else 40.0


@dataclass
class KoreksiSlump:
    selisih_mm: float
    toleransi_mm: float
    dalam_toleransi: bool
    opsi_air_semen: Optional[dict] = None
    opsi_admixture: Optional[dict] = None
    catatan: List[str] = field(default_factory=list)


def hitung_koreksi_slump(
    slump_target: float, slump_uji: float,
    air: float, semen: float, halus_massa: float, bj_halus: float, bj_semen: float,
    volume_uji: float, dosis_pct: float = 0.0, bj_admixture: float = 1.10,
    air_per_10mm: float = AIR_PER_10MM, slump_per_01pct: float = SLUMP_PER_01PCT,
    semen_maks: float = 550.0, fas_maks: Optional[float] = None, dosis_maks_pct: float = 2.0,
    izinkan_admixture: bool = True,
) -> KoreksiSlump:
    fas = air / semen
    selisih = slump_target - slump_uji
    tol = toleransi_slump(slump_target)
    hasil = KoreksiSlump(selisih, tol, abs(selisih) <= tol)
    if hasil.dalam_toleransi:
        hasil.catatan.append(f"Selisih {selisih:+.0f} mm masih dalam toleransi +-{tol:.0f} mm (ASTM C94): tidak perlu koreksi.")
        return hasil

    # Opsi A: air + semen (FAS tetap)
    d_air = selisih / 10 * air_per_10mm
    d_semen = d_air / fas
    d_vol = d_air / 1000 + d_semen / (bj_semen * 1000)            # m3 pasta bertambah (+) / berkurang (-)
    d_halus = -d_vol * 1000 * bj_halus
    a = dict(d_air=d_air, d_semen=d_semen, d_halus=d_halus,
             air=air + d_air, semen=semen + d_semen, halus=halus_massa + d_halus, fas=(air + d_air) / (semen + d_semen),
             batch_air=d_air * volume_uji, batch_semen=d_semen * volume_uji, batch_halus=d_halus * volume_uji)
    hasil.opsi_air_semen = a
    if a["semen"] > semen_maks:
        hasil.catatan.append(f"Opsi A: semen {a['semen']:.0f} kg/m3 melebihi {semen_maks:g} kg/m3 (panas hidrasi, susut, biaya).")
    if a["halus"] <= 0 or a["semen"] <= 0 or a["air"] <= 0:
        hasil.catatan.append("Opsi A tidak layak: hasil koreksi bernilai nol/negatif.")
        hasil.opsi_air_semen = None

    # Opsi B: dosis superplasticizer (air & semen tetap) - hanya bila standar mengizinkan admixture (ACI)
    if izinkan_admixture:
        d_dosis = selisih / slump_per_01pct * 0.1
        dosis_baru = max(0.0, dosis_pct + d_dosis)
        massa = dosis_baru * semen / 100
        hasil.opsi_admixture = dict(
            d_dosis=dosis_baru - dosis_pct, dosis_lama=dosis_pct, dosis_baru=dosis_baru, massa=massa,
            liter=massa / bj_admixture, d_massa=(dosis_baru - dosis_pct) * semen / 100,
            batch_massa=massa * volume_uji, batch_liter=massa / bj_admixture * volume_uji,
            tercapai=(dosis_baru - dosis_pct) / 0.1 * slump_per_01pct)
        if dosis_baru > dosis_maks_pct:
            hasil.catatan.append(f"Opsi B: dosis {dosis_baru:.2f}% melebihi batas {dosis_maks_pct:g}% (risiko bleeding/segregasi, retardasi); "
                                 "kombinasikan dengan Opsi A atau cek ulang produk.")
        if selisih < 0 and dosis_pct <= 0:
            hasil.catatan.append("Opsi B tidak berlaku untuk menurunkan slump karena belum ada admixture; gunakan Opsi A.")
            hasil.opsi_admixture = None
    else:
        hasil.catatan.append("Standar SNI konvensional: tanpa bahan tambah, hanya Opsi A (air + semen, FAS tetap) yang berlaku.")
    if fas_maks is not None and fas > fas_maks:
        hasil.catatan.append(f"FAS rancangan {fas:.3f} sudah melebihi FAS maksimum {fas_maks:g}.")
    if selisih > 0:
        hasil.catatan.append("Jangan menambah air saja di lapangan: itu menaikkan FAS dan menurunkan kuat tekan/durabilitas.")
    else:
        hasil.catatan.append("Slump terlalu tinggi: periksa kadar air agregat, bleeding, dan segregasi sebelum koreksi.")
    hasil.catatan.append("Cek dulu penyebab non-rancangan: kadar air pasir/kerikil, waktu & kecepatan pengadukan, suhu, penyerapan agregat.")
    return hasil
