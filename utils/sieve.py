"""Analisa saringan (sieve analysis): % lolos, modulus kehalusan, cek batas gradasi.

Acuan: SNI ASTM C136-2012 (analisa saringan), zona agregat halus SNI 03-2834-2000 (Zona 1-4)
dan batas gradasi agregat kasar ASTM C33. Nilai batas dalam % LOLOS.
"""
from __future__ import annotations

from typing import Dict, Optional, Sequence, Tuple

import pandas as pd

KOLOM = ["Saringan (mm)", "Massa tertahan (g)", "Tertahan (%)", "Tertahan kumulatif (g)", "Tertahan kumulatif (%)", "Lolos (%)"]

LABEL_SARINGAN = {
    75: '3"', 50: '2"', 37.5: '1 1/2"', 25: '1"', 19: '3/4"', 12.5: '1/2"', 9.5: '3/8"',
    4.75: "No. 4", 2.36: "No. 8", 1.18: "No. 16", 0.6: "No. 30", 0.3: "No. 50", 0.15: "No. 100", 0.075: "No. 200",
}

SARINGAN_HALUS = [9.5, 4.75, 2.36, 1.18, 0.6, 0.3, 0.15, 0.075]
SARINGAN_KASAR = [50, 37.5, 25, 19, 12.5, 9.5, 4.75, 2.36, 1.18, 0.6, 0.3, 0.15]
FM_HALUS_STANDAR = [4.75, 2.36, 1.18, 0.6, 0.3, 0.15]               # ASTM C136
FM_KASAR_STANDAR = [37.5, 19, 9.5, 4.75, 2.36, 1.18, 0.6, 0.3, 0.15]

# Data contoh (ganti dengan data pengujian laboratorium)
CONTOH_MASSA_HALUS = {9.5: 69.6, 4.75: 55.4, 2.36: 131.5, 1.18: 261.5, 0.6: 329.7, 0.3: 210.7, 0.15: 229.6, 0.075: 155.7}
CONTOH_PAN_HALUS = 47.2
CONTOH_MASSA_KASAR = {25: 30.6, 19: 164.1, 12.5: 1232.0, 9.5: 894.1, 4.75: 638.7, 2.36: 26.6}
CONTOH_PAN_KASAR = 14.2

# Zona gradasi agregat halus (% lolos): {saringan: (bawah, atas)}
SPEC_HALUS: Dict[str, Dict[float, Tuple[float, float]]] = {
    "Zona 1 (kasar)":       {9.5: (100, 100), 4.75: (90, 100), 2.36: (60, 95), 1.18: (30, 70), 0.6: (15, 34), 0.3: (5, 20), 0.15: (0, 10)},
    "Zona 2 (agak kasar)":  {9.5: (100, 100), 4.75: (90, 100), 2.36: (75, 100), 1.18: (55, 90), 0.6: (35, 59), 0.3: (8, 30), 0.15: (0, 10)},
    "Zona 3 (agak halus)":  {9.5: (100, 100), 4.75: (90, 100), 2.36: (85, 100), 1.18: (75, 100), 0.6: (60, 79), 0.3: (12, 40), 0.15: (0, 10)},
    "Zona 4 (halus)":       {9.5: (100, 100), 4.75: (95, 100), 2.36: (95, 100), 1.18: (90, 100), 0.6: (80, 100), 0.3: (15, 50), 0.15: (0, 15)},
}

# Batas gradasi agregat kasar (ASTM C33, % lolos)
SPEC_KASAR: Dict[str, Dict[float, Tuple[float, float]]] = {
    "No. 357 (50 - 4,75 mm)":   {50: (95, 100), 25: (35, 70), 12.5: (10, 30), 4.75: (0, 5)},
    "No. 8 (9,5 - 2,36 mm)":    {12.5: (100, 100), 9.5: (85, 100), 4.75: (10, 30), 2.36: (0, 10), 1.18: (0, 5)},
    "No. 7 (12,5 - 4,75 mm)":   {19: (100, 100), 12.5: (90, 100), 9.5: (40, 70), 4.75: (0, 15), 2.36: (0, 5)},
    "No. 467 (37,5 - 4,75 mm)": {50: (100, 100), 37.5: (95, 100), 19: (35, 70), 9.5: (10, 30), 4.75: (0, 5)},
    "No. 4 (37,5 - 19 mm)":     {50: (100, 100), 37.5: (90, 100), 25: (20, 55), 19: (0, 15), 9.5: (0, 5)},
    "No. 5 (25 - 12,5 mm)":     {37.5: (100, 100), 25: (90, 100), 19: (20, 55), 12.5: (0, 10), 9.5: (0, 5)},
    "No. 56 (25 - 9,5 mm)":     {37.5: (100, 100), 25: (90, 100), 19: (40, 85), 12.5: (10, 40), 9.5: (0, 15), 4.75: (0, 5)},
    "No. 57 (25 - 4,75 mm)":    {37.5: (100, 100), 25: (95, 100), 12.5: (25, 60), 4.75: (0, 10), 2.36: (0, 5)},
    "No. 6 (19 - 9,5 mm)":      {25: (100, 100), 19: (90, 100), 9.5: (20, 55), 4.75: (0, 15), 2.36: (0, 5)},
    "No. 67 (19 - 4,75 mm)":    {25: (100, 100), 19: (90, 100), 9.5: (20, 55), 4.75: (0, 10), 2.36: (0, 5)},
}


def data_awal(jenis: str) -> pd.DataFrame:
    """Tabel isian awal (kolom saringan + massa tertahan)."""
    saringan = SARINGAN_HALUS if jenis == "halus" else SARINGAN_KASAR
    contoh = CONTOH_MASSA_HALUS if jenis == "halus" else CONTOH_MASSA_KASAR
    return pd.DataFrame({"Saringan (mm)": saringan, "Massa tertahan (g)": [float(contoh.get(x, 0.0)) for x in saringan]})


def analisa_saringan(saringan: Sequence[float], massa: Sequence[float], pan: float = 0.0) -> pd.DataFrame:
    """Hitung tertahan kumulatif & % lolos. Total massa = jumlah massa tertahan + pan."""
    df = pd.DataFrame({"Saringan (mm)": list(saringan), "Massa tertahan (g)": [float(m) for m in massa]})
    if (df["Massa tertahan (g)"] < 0).any() or pan < 0:
        raise ValueError("Massa tertahan tidak boleh negatif.")
    total = df["Massa tertahan (g)"].sum() + pan
    if total <= 0:
        raise ValueError("Total massa benda uji harus > 0.")
    df = df.sort_values("Saringan (mm)", ascending=False).reset_index(drop=True)
    df["Tertahan (%)"] = df["Massa tertahan (g)"] / total * 100
    df["Tertahan kumulatif (g)"] = df["Massa tertahan (g)"].cumsum()
    df["Tertahan kumulatif (%)"] = df["Tertahan kumulatif (g)"] / total * 100
    df["Lolos (%)"] = 100 - df["Tertahan kumulatif (%)"]
    return df[KOLOM]


def cek_massa(df: pd.DataFrame, pan: float, massa_awal: Optional[float]) -> Optional[str]:
    """ASTM C136: selisih jumlah massa tertahan + pan terhadap massa awal maksimum 0,3%."""
    if not massa_awal:
        return None
    total = df["Massa tertahan (g)"].sum() + pan
    selisih = abs(total - massa_awal) / massa_awal * 100
    return f"Selisih massa {selisih:.2f}% terhadap massa awal (batas 0,3%)." if selisih > 0.3 else None


def modulus_kehalusan(df: pd.DataFrame, saringan_fm: Sequence[float]) -> float:
    """MK = jumlah % tertahan kumulatif pada saringan standar / 100."""
    d = df.set_index("Saringan (mm)")["Tertahan kumulatif (%)"]
    return float(sum(d[s] for s in saringan_fm if s in d.index) / 100)


def cek_spesifikasi(df: pd.DataFrame, spec: Dict[float, Tuple[float, float]],
                    abaikan: Sequence[float] = ()) -> Tuple[pd.DataFrame, bool]:
    """Bandingkan % lolos dengan batas bawah-atas. `abaikan` = saringan yang tidak ikut menentukan lulus."""
    lolos = df.set_index("Saringan (mm)")["Lolos (%)"]
    baris, lulus = [], True
    for s in sorted(spec, reverse=True):
        bawah, atas = spec[s]
        if s not in lolos.index:
            baris.append([s, bawah, atas, None, "tidak diuji", 0.0])
            continue
        v = float(lolos[s])
        if v < bawah - 1e-9:
            status = "di bawah batas"
        elif v > atas + 1e-9:
            status = "di atas batas"
        else:
            status = "OK"
        if status != "OK" and s not in abaikan:
            lulus = False
        dev = max(bawah - v, v - atas, 0.0)
        baris.append([s, bawah, atas, v, status, dev])
    return pd.DataFrame(baris, columns=["Saringan (mm)", "Batas bawah (%)", "Batas atas (%)", "Lolos (%)", "Status",
                                        "Deviasi (%)"]), lulus


def evaluasi_zona(df: pd.DataFrame, abaikan: Sequence[float] = (9.5,)) -> Tuple[str, bool]:
    """Zona agregat halus yang sesuai. Bila tidak ada yang lulus, kembalikan zona dengan pelanggaran paling sedikit."""
    terbaik, pelanggaran_min = "", 10**9
    for nama, spec in SPEC_HALUS.items():
        tabel, lulus = cek_spesifikasi(df, spec, abaikan)
        if lulus:
            return nama, True
        n = int(((tabel["Status"] != "OK") & (~tabel["Saringan (mm)"].isin(abaikan))).sum())
        if n < pelanggaran_min:
            terbaik, pelanggaran_min = nama, n
    return terbaik, False


def validasi_saringan(df: pd.DataFrame, pan: float, halus: bool, mk: float, no200: dict = None) -> list:
    """Daftar peringatan otomatis untuk hasil analisa saringan. Material lolos No. 200 memakai uji cuci SNI 03-4142
    bila tersedia (batas ASTM C33: pasir 5%, kerikil 1%); bila belum diisi, tidak dinilai dari massa pan."""
    pesan = []
    if halus and not 2.3 <= mk <= 3.1:
        pesan.append(f"MK {mk:.2f} di luar rentang 2,3-3,1 (ASTM C33).")
    if no200 and no200.get("nilai") is not None:
        batas = 5.0 if halus else 1.0
        if no200["nilai"] > batas:
            pesan.append(f"Material lolos No. 200 {no200['nilai']:.2f}% (uji cuci SNI 03-4142) melebihi batas {batas:g}%: "
                         + ("cuci pasir." if halus else "cuci kerikil."))
    else:
        pesan.append("Uji cuci No. 200 (SNI 03-4142) belum diisi; kadar lolos No. 200 belum dinilai dari uji cuci.")
    if (df["Massa tertahan (g)"] > 0).sum() < 3:
        pesan.append("Kurang dari 3 saringan terisi; periksa input.")
    return pesan


# Ukuran maksimum nominal (mm) -> gradasi acuan ASTM C33
SPEC_KASAR_UKURAN = {9.5: "No. 8 (9,5 - 2,36 mm)", 10: "No. 8 (9,5 - 2,36 mm)", 12.5: "No. 7 (12,5 - 4,75 mm)",
                     19: "No. 67 (19 - 4,75 mm)", 20: "No. 67 (19 - 4,75 mm)", 25: "No. 57 (25 - 4,75 mm)",
                     37.5: "No. 467 (37,5 - 4,75 mm)", 40: "No. 467 (37,5 - 4,75 mm)", 50: "No. 357 (50 - 4,75 mm)"}


def spec_kasar_untuk_ukuran(ukuran_maks: float) -> Tuple[str, bool]:
    """(nama gradasi acuan, tepat). Ukuran > 50 mm (75, 150) tidak punya gradasi tunggal ASTM C33: dipakai No. 357 (tepat=False)."""
    if ukuran_maks in SPEC_KASAR_UKURAN:
        return SPEC_KASAR_UKURAN[ukuran_maks], True
    return SPEC_KASAR_UKURAN[50], False


def persen_lolos_cuci(w1: float, w2: float) -> float:
    """SNI 03-4142-1996: persen lolos No. 200 = (W1 - W2) / W1 x 100 (W1 = berat awal kering, W2 = setelah dicuci)."""
    if w1 <= 0 or w2 < 0 or w2 > w1:
        raise ValueError("Berat awal harus > 0 dan berat setelah pencucian 0 s.d. berat awal.")
    return (w1 - w2) / w1 * 100
