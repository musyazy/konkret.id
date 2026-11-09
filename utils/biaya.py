"""Estimasi biaya material beton per m3 dan untuk volume pekerjaan."""
from __future__ import annotations

from typing import Optional

import pandas as pd

from standards.base import Komposisi

HARGA_CONTOH = dict(semen_kg=1400, pasir_m3=250000, split_m3=300000, air_m3=15000, admixture_liter=30000)


def hitung_biaya(k: Komposisi, bi_gembur_pasir: float, bi_gembur_split: float, harga: dict,
                 susut_pct: float = 5.0, overhead_pct: float = 10.0, ppn_pct: float = 11.0) -> dict:
    """k = komposisi lapangan per 1 m3 beton. Mengembalikan tabel rincian dan total per m3."""
    f = 1 + susut_pct / 100
    bp, bs = max(bi_gembur_pasir, 1.0), max(bi_gembur_split, 1.0)
    baris = [
        ("Semen", k.semen * f, "kg", harga["semen_kg"]),
        ("Pasir", k.agregat_halus * f / bp, "m³", harga["pasir_m3"]),
        ("Split / Kerikil", k.agregat_kasar * f / bs, "m³", harga["split_m3"]),
        ("Air", k.air * f / 1000, "m³", harga["air_m3"]),
    ]
    if k.admixture_liter > 0:
        baris.append(("Admixture", k.admixture_liter * f, "liter", harga["admixture_liter"]))
    df = pd.DataFrame(baris, columns=["Material", "Kebutuhan / m³ beton", "Satuan", "Harga satuan"])
    df["Biaya / m³ beton"] = df["Kebutuhan / m³ beton"] * df["Harga satuan"]
    subtotal = float(df["Biaya / m³ beton"].sum())
    df["Porsi (%)"] = df["Biaya / m³ beton"] / subtotal * 100 if subtotal > 0 else 0.0
    overhead = subtotal * overhead_pct / 100
    ppn = (subtotal + overhead) * ppn_pct / 100
    return dict(rincian=df, subtotal=subtotal, overhead=overhead, ppn=ppn, total=subtotal + overhead + ppn)
