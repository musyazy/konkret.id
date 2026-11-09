"""Mix design beton normal mengikuti SNI 03-2834-2000 (metode DOE) - otomatis, KONVENSIONAL.

Standar SNI di aplikasi ini murni konvensional: TIDAK menerima bahan tambah (admixture).
Fitur admixture hanya tersedia pada standar ACI 211.1 (standards/aci.py).

Nilai yang pada SNI dibaca dari grafik dihitung dari tabel interpolasi hasil digitalisasi (standards/sni_grafik.py):
  * FAS             : Tabel 2 (kuat tekan pada FAS 0,5, menurut bentuk benda uji) + Grafik 1
  * Persen pasir    : Grafik 14 (20 mm) / Grafik 15 (40 mm) menurut zona pasir, slump, dan FAS
  * Berat isi beton : Grafik 16 menurut kadar air bebas dan berat jenis agregat gabungan
Bila tabel tidak berlaku (mis. ukuran maks 10 mm) dipakai estimasi dan diberi label; semua dapat ditimpa manual.
"""
from __future__ import annotations

import math
from typing import Optional, Tuple

from standards import aci, sni_grafik
from standards.base import HasilMixDesign, Komposisi, Langkah
from utils.material_db import Agregat

NAMA = "SNI 03-2834-2000"
UKURAN_MAKS_TERSEDIA = [10, 20, 40]                       # mm
_PETA_ACI = {10: 9.5, 20: 19.0, 40: 37.5}                 # padanan ukuran pada tabel ACI
K_FAS_BAWAAN = 2.6
UMUR_TERSEDIA = [3, 7, 28, 91]
BENTUK_UJI = ["silinder", "kubus"]
RENTANG_KALIBRASI_FCR = (25.0, 45.0)                      # MPa, batas pendekatan eksponensial k = 2,6
RENTANG_KALIBRASI_FAS = (0.35, 0.65)

LABEL_EST_PERSEN = "estimasi, bukan Grafik 13-15"
LABEL_EST_BERAT = "estimasi, bukan Grafik 16"
LABEL_EST_FAS = "estimasi kurva k = 2,6, bukan Grafik 1"

# Tabel 2: kuat tekan (MPa) pada FAS 0,5 -> [bentuk benda uji][kelompok semen][jenis agregat kasar][umur hari]
TABEL_2 = {
    "silinder": {
        "I/II/V": {"alami": {3: 17, 7: 23, 28: 33, 91: 40}, "batu pecah": {3: 19, 7: 27, 28: 37, 91: 45}},
        "III":    {"alami": {3: 21, 7: 28, 28: 38, 91: 44}, "batu pecah": {3: 25, 7: 33, 28: 44, 91: 48}},
    },
    "kubus": {
        "I/II/V": {"alami": {3: 20, 7: 28, 28: 40, 91: 48}, "batu pecah": {3: 25, 7: 32, 28: 45, 91: 54}},
        "III":    {"alami": {3: 25, 7: 31, 28: 46, 91: 53}, "batu pecah": {3: 30, 7: 40, 28: 53, 91: 60}},
    },
}
# Persyaratan awet (Tabel 4): nama -> (kadar semen minimum kg/m3, FAS maksimum)
LINGKUNGAN = {
    "Dalam ruang bangunan - keadaan non-korosif": (275.0, 0.60),
    "Dalam ruang bangunan - kondensasi / uap korosif": (325.0, 0.52),
    "Luar ruang - tidak terlindung hujan & terik matahari": (325.0, 0.60),
    "Luar ruang - terlindung hujan & terik matahari": (275.0, 0.60),
    "Di dalam tanah - basah & kering berganti-ganti": (325.0, 0.55),
}

# Tabel 3: kadar air bebas (kg/m3) {ukuran: {slump (mm): (batu tak dipecahkan, batu pecah)}}
_TABEL_AIR = {
    10: {"0-10": (150, 180), "10-30": (180, 205), "30-60": (205, 230), "60-180": (225, 250)},
    20: {"0-10": (135, 170), "10-30": (160, 190), "30-60": (180, 210), "60-180": (195, 225)},
    40: {"0-10": (115, 155), "10-30": (140, 175), "30-60": (160, 190), "60-180": (175, 205)},
}


def kelas_slump(slump_mm: float) -> str:
    return "0-10" if slump_mm <= 10 else "10-30" if slump_mm <= 30 else "30-60" if slump_mm <= 60 else "60-180"


def nilai_tambah(simpangan_baku: Optional[float], k: float = 1.64) -> float:
    """Margin M = k * s; bila tidak ada data deviasi standar, SNI memakai M = 12 MPa."""
    return 12.0 if simpangan_baku is None else k * simpangan_baku


def wh_wk(slump_mm: float, ukuran_maks: int, bentuk_halus: str, bentuk_kasar: str) -> Tuple[float, float]:
    """(Wh, Wk): kadar air tabel untuk agregat halus dan agregat kasar."""
    baris = _TABEL_AIR[ukuran_maks][kelas_slump(slump_mm)]
    return (baris[0] if bentuk_halus == "alami" else baris[1]), (baris[0] if bentuk_kasar == "alami" else baris[1])


def kadar_air_bebas(slump_mm: float, ukuran_maks: int, bentuk_halus: str, bentuk_kasar: str) -> float:
    """W = 2/3 Wh + 1/3 Wk."""
    wh, wk = wh_wk(slump_mm, ukuran_maks, bentuk_halus, bentuk_kasar)
    return 2 / 3 * wh + 1 / 3 * wk


def kuat_tekan_acuan(kelompok_semen: str, bentuk_kasar: str, umur: int = 28, bentuk_uji: str = "silinder") -> float:
    return float(TABEL_2[bentuk_uji][kelompok_semen][bentuk_kasar][umur])


def fas_dari_kuat_tekan(fcr: float, f0: float, k: float = K_FAS_BAWAAN) -> float:
    """Estimasi eksponensial (cadangan): kebalikan f = f0 * exp(-k (FAS - 0,5))."""
    return 0.5 - math.log(fcr / f0) / k


def kurva_fas(f0: float, k: float = K_FAS_BAWAAN, n: int = 11):
    """Titik kurva FAS - kuat tekan estimasi eksponensial: (FAS list, f list)."""
    xs = [0.30 + 0.05 * i for i in range(n)]
    return xs, [f0 * math.exp(-k * (x - 0.5)) for x in xs]


def hitung_mix_design_sni(
    fc: float,
    slump_mm: float,
    ukuran_maks: int,
    halus: Agregat,
    kasar: Agregat,
    kelompok_semen: str = "I/II/V",
    umur: int = 28,
    simpangan_baku: Optional[float] = 5.0,
    k: float = 1.64,
    fas_maks: float = 0.60,
    semen_min: float = 275.0,
    semen_maks: Optional[float] = None,
    bj_semen: float = 3.15,
    udara_pct: Optional[float] = None,
    fas_manual: Optional[float] = None,
    persen_halus_manual: Optional[float] = None,
    berat_isi_beton_manual: Optional[float] = None,
    k_fas: float = K_FAS_BAWAAN,
    bentuk_uji: str = "silinder",
    zona_pasir: Optional[int] = None,
    gunakan_tabel: bool = True,
) -> HasilMixDesign:
    if ukuran_maks not in _TABEL_AIR:
        raise ValueError(f"Ukuran maksimum agregat harus salah satu dari {UKURAN_MAKS_TERSEDIA} mm.")
    if bentuk_uji not in TABEL_2:
        raise ValueError("Bentuk benda uji harus 'silinder' atau 'kubus'.")
    if persen_halus_manual is not None and not 0 < persen_halus_manual < 100:
        raise ValueError("Persen agregat halus harus di antara 0 dan 100.")

    langkah, peringatan = [], []
    add = lambda *a, **kw: langkah.append(Langkah(*a, **kw))
    ukuran_aci = _PETA_ACI[ukuran_maks]
    kelas = kelas_slump(slump_mm)

    # 1. Kuat tekan target
    margin = nilai_tambah(simpangan_baku, k)
    fcr = fc + margin
    if simpangan_baku is not None:
        add("Nilai tambah (margin)", round(margin, 2), "MPa", "", "M = k x s", f"{k:g} x {simpangan_baku:g}", r"M = k\,s")
    else:
        add("Nilai tambah (margin)", round(margin, 2), "MPa", "tanpa data", "M = 12 MPa", "12", r"M = 12\ \mathrm{MPa}")
    add("Kuat tekan rata-rata target f'cr", round(fcr, 2), "MPa", f"benda uji {bentuk_uji}", "f'cr = f'c + M", f"{fc:g} + {margin:.2f}", r"f'_{cr} = f'_c + M")

    # 2. Air bebas
    wh, wk = wh_wk(slump_mm, ukuran_maks, halus.bentuk, kasar.bentuk)
    air = 2 / 3 * wh + 1 / 3 * wk
    add("Kadar air bebas", round(air, 2), "kg/m3", f"Tabel 3 (slump {kelas} mm, {ukuran_maks} mm)", "W = 2/3 Wh + 1/3 Wk",
        f"2/3 x {wh:g} + 1/3 x {wk:g}", r"W = \tfrac{2}{3}W_h + \tfrac{1}{3}W_k")

    # 3. FAS (Grafik 1 / estimasi / manual)
    f0 = kuat_tekan_acuan(kelompok_semen, kasar.bentuk, umur, bentuk_uji)
    sumber_fas = "manual"
    if fas_manual is not None:
        fas_grafik = fas_manual
        add("FAS dari kuat tekan", round(fas_grafik, 3), "", "input manual (Grafik 1)", "FAS = pembacaan Grafik 1", f"{fas_manual:g}", r"FAS = FAS_{Grafik\ 1}")
    else:
        fas_g1 = sni_grafik.fas_dari_grafik1(fcr, f0, kelompok_semen) if gunakan_tabel else None
        if fas_g1 is not None:
            fas_grafik, sumber_fas = fas_g1, "grafik1"
            add("FAS dari kuat tekan", round(fas_grafik, 3), "", f"Grafik 1 (tabel digitalisasi); f0 = {f0:g} MPa Tabel 2, umur {umur} hr, {bentuk_uji}",
                "FAS = kurva Grafik 1 melalui (0,5; f0), dibaca pada f'cr", f"f0 = {f0:g}; f'cr = {fcr:.2f} -> {fas_grafik:.3f}",
                r"FAS = G_1^{-1}\left(f'_{cr};\ f_0\right)")
        else:
            fas_grafik, sumber_fas = fas_dari_kuat_tekan(fcr, f0, k_fas), "estimasi"
            if gunakan_tabel:
                peringatan.append(f"f'cr {fcr:.1f} MPa di luar jangkauan Grafik 1; FAS memakai {LABEL_EST_FAS}.")
            add("FAS dari kuat tekan", round(fas_grafik, 3), "", f"{LABEL_EST_FAS}; f0 = {f0:g} MPa (Tabel 2)",
                "FAS = 0,5 - ln(f'cr / f0) / k", f"0,5 - ln({fcr:.2f} / {f0:g}) / {k_fas:g}", r"FAS = 0{,}5 - \dfrac{\ln(f'_{cr}/f_0)}{k}")
            lo, hi = RENTANG_KALIBRASI_FCR
            if not lo <= fcr <= hi:
                peringatan.append(f"f'cr {fcr:.1f} MPa di luar rentang kalibrasi rumus FAS (sekitar {lo:g}-{hi:g} MPa); FAS = estimasi, verifikasi dengan Grafik 1.")
            if not RENTANG_KALIBRASI_FAS[0] <= fas_grafik <= RENTANG_KALIBRASI_FAS[1]:
                peringatan.append(f"FAS estimasi {fas_grafik:.3f} di luar rentang kalibrasi {RENTANG_KALIBRASI_FAS[0]:g}-{RENTANG_KALIBRASI_FAS[1]:g}; verifikasi dengan Grafik 1.")
    fas = min(fas_grafik, fas_maks)
    add("FAS dipakai", round(fas, 3), "", "", "FAS = min(FAS kuat tekan, FAS maks)", f"min({fas_grafik:.3f}, {fas_maks:g})", r"FAS = \min(FAS_{f'cr},\ FAS_{maks})")

    # 4. Semen
    semen = air / fas
    add("Kadar semen", round(semen, 2), "kg/m3", "", "C = W / FAS", f"{air:.2f} / {fas:.3f}", r"C = \dfrac{W}{FAS}")
    if semen < semen_min:
        semen = semen_min
        peringatan.append(f"Kadar semen < minimum, dipakai {semen_min:g} kg/m3.")
        add("Kadar semen disesuaikan", round(semen, 2), "kg/m3", "kadar semen minimum", "C = C min", f"{semen_min:g}", r"C = C_{min}")
    if semen_maks is not None and semen > semen_maks:
        peringatan.append(f"Kadar semen {semen:.1f} kg/m3 melebihi batas maksimum {semen_maks:g} kg/m3.")
    fas_efektif = air / semen
    add("FAS efektif", round(fas_efektif, 3), "", "", "FAS = W / C", f"{air:.2f} / {semen:.2f}", r"FAS = \dfrac{W}{C}")

    # 5. Persen pasir (manual / Grafik 14-15 / estimasi) dan berat isi beton (manual / Grafik 16 / estimasi)
    udara = aci.udara_terperangkap(ukuran_aci) if udara_pct is None else udara_pct
    vol_lain = air / 1000 + semen / (bj_semen * 1000) + udara / 100
    add("Kadar udara terperangkap", udara, "%", "Tabel ACI" if udara_pct is None else "input", "A = nilai tabel", f"{udara:g}", r"A = A_{tabel}")

    persen_batas = None
    sumber_persen, label_persen = "estimasi", LABEL_EST_PERSEN
    p_tetap = None
    if persen_halus_manual is not None:
        p_tetap, sumber_persen, label_persen = persen_halus_manual / 100, "manual", "input manual dari Grafik 13-15"
    elif gunakan_tabel and zona_pasir is not None:
        hasil_g = sni_grafik.persen_pasir_grafik(ukuran_maks, kelas, zona_pasir, fas)
        if hasil_g is not None:
            lo, hi, luar = hasil_g
            p_tetap, persen_batas, sumber_persen = (lo + hi) / 200, (lo, hi), "grafik"
            nomor = 14 if ukuran_maks == 20 else 15
            label_persen = f"Grafik {nomor} (tabel digitalisasi), zona {zona_pasir}, titik tengah pita"
            if luar:
                peringatan.append(f"FAS {fas:.2f} di luar sumbu Grafik {nomor} (0,3-0,9); persen pasir diekstrapolasi.")
    if persen_halus_manual is None and p_tetap is None and (kasar.berat_isi is None or kasar.berat_isi <= 0 or halus.modulus_kehalusan is None):
        raise ValueError("Estimasi persen pasir butuh berat isi kerikil dan MK pasir (atau isi persen pasir manual / pilih zona pasir).")
    kasar_dasar = None
    if p_tetap is None:
        kasar_dasar = aci.volume_agregat_kasar(ukuran_aci, halus.modulus_kehalusan) * kasar.berat_isi * (1 + kasar.penyerapan_pct / 100)

    sumber_berat, label_berat, g16_luar = "estimasi", LABEL_EST_BERAT, False

    def rho(p: float) -> float:
        nonlocal g16_luar
        bj = p * halus.bj_ssd + (1 - p) * kasar.bj_ssd
        if berat_isi_beton_manual is not None:
            return berat_isi_beton_manual
        if gunakan_tabel:
            nilai, luar = sni_grafik.berat_isi_grafik16(air, bj * 1000)
            g16_luar = luar
            return nilai
        return semen + air + (1 - vol_lain) * bj * 1000

    p = p_tetap if p_tetap is not None else 0.40
    for _ in range(60):
        gabungan = rho(p) - semen - air
        if p_tetap is not None or gabungan <= 0:
            break
        p_baru = min(max(1 - kasar_dasar / gabungan, 0.20), 0.55)
        if abs(p_baru - p) < 1e-7:
            p = p_baru
            break
        p = p_baru
    if gabungan <= 0:
        raise ValueError("Kadar agregat gabungan <= 0. Periksa berat isi beton manual atau data agregat.")
    if p_tetap is None and p in (0.20, 0.55):
        peringatan.append("Persen pasir hasil estimasi menyentuh batas 20%/55%; baca Grafik 13-15 dan isi manual.")
    bj_gab = p * halus.bj_ssd + (1 - p) * kasar.bj_ssd
    berat_isi_beton = rho(p)
    if berat_isi_beton_manual is not None:
        sumber_berat, label_berat = "manual", "input manual dari Grafik 16"
    elif gunakan_tabel:
        sumber_berat, label_berat = "grafik", "Grafik 16 (tabel digitalisasi, asumsi batu pecah)"
        if g16_luar:
            peringatan.append("Kadar air atau berat jenis agregat gabungan di luar sumbu Grafik 16 (100-260 kg/m3; 2,4-2,9); berat isi diekstrapolasi.")

    ket_p = (f"({persen_batas[0]:.1f} + {persen_batas[1]:.1f}) / 2" if persen_batas else f"{p * 100:.1f}")
    add("Persen agregat halus", round(p * 100, 1), "%", label_persen,
        "p = rata-rata batas bawah & atas zona" if persen_batas else ("p = input manual" if sumber_persen == "manual" else "p = 1 - (Vk x BI x (1+Ab)) / agregat gabungan"),
        ket_p, r"p = \dfrac{p_{bawah} + p_{atas}}{2}" if persen_batas else r"p = 1 - \dfrac{M_k}{M_{gab}}")
    add("Berat jenis relatif agregat gabungan (SSD)", round(bj_gab, 3), "", "", "BJ gab = p x Ss halus + (1 - p) x Ss kasar",
        f"{p:.3f} x {halus.bj_ssd:.3f} + {1 - p:.3f} x {kasar.bj_ssd:.3f}", r"BJ_{gab} = p\,S_{s,h} + (1-p)\,S_{s,k}")
    add("Berat isi beton basah", round(berat_isi_beton, 1), "kg/m3", label_berat,
        "rho = Grafik 16(W, BJ gab)" if sumber_berat == "grafik" else ("rho = input manual" if sumber_berat == "manual" else "rho = W + C + (1 - W/1000 - C/(Cs x 1000) - A/100) x BJ gab x 1000"),
        f"W = {air:.1f}; BJ gab = {bj_gab * 1000:.0f}" if sumber_berat == "grafik" else f"{berat_isi_beton:.1f}",
        r"\rho = G_{16}(W,\ BJ_{gab})" if sumber_berat == "grafik" else r"\rho = W + C + \left(1 - \tfrac{W}{1000} - \tfrac{C}{1000\,C_s} - \tfrac{A}{100}\right)BJ_{gab}\,1000")
    halus_ssd = p * gabungan
    kasar_ssd = gabungan - halus_ssd
    add("Kadar agregat gabungan", round(gabungan, 2), "kg/m3", "", "M gab = rho - C - W", f"{berat_isi_beton:.1f} - {semen:.2f} - {air:.2f}", r"M_{gab} = \rho - C - W")
    add("Kadar agregat halus (SSD)", round(halus_ssd, 2), "kg/m3", "", "Mh = p x M gab", f"{p:.4f} x {gabungan:.2f}", r"M_h = p\,M_{gab}")
    add("Kadar agregat kasar (SSD)", round(kasar_ssd, 2), "kg/m3", "", "Mk = M gab - Mh", f"{gabungan:.2f} - {halus_ssd:.2f}", r"M_k = M_{gab} - M_h")

    # 6. Koreksi kadar air lapangan
    kor_h = (halus.kadar_air_pct - halus.penyerapan_pct) / 100
    kor_k = (kasar.kadar_air_pct - kasar.penyerapan_pct) / 100
    air_lap = air - kor_h * halus_ssd - kor_k * kasar_ssd
    halus_lap, kasar_lap = halus_ssd * (1 + kor_h), kasar_ssd * (1 + kor_k)
    add("Air yang ditambahkan (lapangan)", round(air_lap, 2), "kg/m3", "koreksi kadar air & penyerapan", "W lap = W - (KAh - Abh) Mh - (KAk - Abk) Mk",
        f"{air:.2f} - {kor_h:.4f} x {halus_ssd:.1f} - {kor_k:.4f} x {kasar_ssd:.1f}", r"W_{lap} = W - (KA_h - Ab_h)M_h - (KA_k - Ab_k)M_k")
    if air_lap < 0:
        peringatan.append("Air lapangan negatif: kadar air agregat terlalu tinggi, periksa input.")

    return HasilMixDesign(
        standar=NAMA, fcr=fcr, fas=fas_efektif,
        teoritis=Komposisi(semen, air, halus_ssd, kasar_ssd), kondisi_teoritis="SSD",
        lapangan=Komposisi(semen, air_lap, halus_lap, kasar_lap),
        langkah=langkah, peringatan=peringatan,
        parameter=dict(air_awal=air, udara_pct=udara, persen_halus=p * 100, berat_isi_beton=berat_isi_beton,
                       fas_tabel=fas_grafik, f0=f0, umur=umur, bj_gabungan=bj_gab, halus_massa=halus_ssd,
                       bentuk_uji=bentuk_uji, sumber_fas=sumber_fas, sumber_persen=sumber_persen, sumber_berat=sumber_berat,
                       label_persen=label_persen, label_berat=label_berat,
                       label_fas="Grafik 1 (tabel digitalisasi)" if sumber_fas == "grafik1" else ("input manual dari Grafik 1" if sumber_fas == "manual" else LABEL_EST_FAS),
                       persen_batas=persen_batas, zona_pasir=zona_pasir),
    )
