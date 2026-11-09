"""Optimasi gradasi agregat gabungan: rasio pasir : kerikil terbaik terhadap kurva ideal Fuller.

Fuller: P(d) = 100 x sqrt(d / D), D = ukuran maksimum agregat. Gradasi gabungan: P = p x P_pasir + (1 - p) x P_kerikil.
Rasio terbaik meminimumkan jumlah kuadrat selisih (solusi kuadrat terkecil, dibatasi p_min - p_maks).
Batas gradasi gabungan SNI (Grafik 3-9) belum tersedia sebagai tabel di aplikasi ini, sehingga acuan = kurva Fuller.
"""
from __future__ import annotations

import math
from typing import Dict, List

import numpy as np
import pandas as pd


def lolos_pada(df: pd.DataFrame, s: float) -> float:
    """% lolos pada saringan s (mm) dari tabel analisa saringan; interpolasi linear pada skala log."""
    xs = np.log10(df["Saringan (mm)"].to_numpy(dtype=float)[::-1])         # menaik
    ys = df["Lolos (%)"].to_numpy(dtype=float)[::-1]
    if s >= 10 ** xs[-1]:
        return 100.0 if s > 10 ** xs[-1] else float(ys[-1])
    return float(np.interp(math.log10(s), xs, ys))


def kurva_fuller(d: float, dmaks: float) -> float:
    return min(100.0, 100.0 * math.sqrt(d / dmaks))


def saringan_gabungan(df_halus: pd.DataFrame, df_kasar: pd.DataFrame, dmaks: float, dmin: float = 0.15) -> List[float]:
    """Saringan acuan: gabungan kedua tabel, dibatasi dmin <= s <= D, menurun."""
    s = set(df_halus["Saringan (mm)"]) | set(df_kasar["Saringan (mm)"])
    return sorted((x for x in s if dmin <= x <= dmaks), reverse=True)


def gabungan(df_halus: pd.DataFrame, df_kasar: pd.DataFrame, p_halus: float, sieves: List[float]) -> List[float]:
    return [p_halus * lolos_pada(df_halus, s) + (1 - p_halus) * lolos_pada(df_kasar, s) for s in sieves]


def optimasi_rasio(df_halus: pd.DataFrame, df_kasar: pd.DataFrame, dmaks: float, p_desain: float = None,
                   p_min: float = 0.20, p_maks: float = 0.70) -> Dict:
    """Rasio pasir (fraksi massa) terbaik terhadap kurva Fuller. p_desain (fraksi) opsional untuk perbandingan."""
    sieves = saringan_gabungan(df_halus, df_kasar, dmaks)
    if len(sieves) < 3:
        raise ValueError("Saringan acuan kurang dari 3; lengkapi data analisa saringan.")
    pf = np.array([lolos_pada(df_halus, s) for s in sieves])
    pk = np.array([lolos_pada(df_kasar, s) for s in sieves])
    pt = np.array([kurva_fuller(s, dmaks) for s in sieves])
    pembagi = float(np.sum((pf - pk) ** 2))
    p_opt = float(np.sum((pt - pk) * (pf - pk)) / pembagi) if pembagi > 1e-9 else 0.4
    p_opt = min(max(p_opt, p_min), p_maks)
    rmse = lambda p: float(np.sqrt(np.mean((p * pf + (1 - p) * pk - pt) ** 2)))
    return dict(sieves=sieves, p_halus=p_opt, rasio=f"{p_opt * 100:.0f} : {(1 - p_opt) * 100:.0f}", rmse=rmse(p_opt),
                fuller=pt.tolist(), optimal=(p_opt * pf + (1 - p_opt) * pk).tolist(),
                desain=(p_desain * pf + (1 - p_desain) * pk).tolist() if p_desain is not None else None,
                rmse_desain=rmse(p_desain) if p_desain is not None else None, p_desain=p_desain, dmaks=dmaks)
