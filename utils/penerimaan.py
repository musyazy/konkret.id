"""Kriteria penerimaan kuat tekan beton umur 28 hari untuk data uji sebenarnya (SNI 2847 / ACI 318).

Satu 'hasil uji' = rata-rata kuat tekan benda uji dari satu contoh (mis. dua silinder). Beton diterima bila KEDUANYA terpenuhi:
  (a) setiap rata-rata dari tiga hasil uji berurutan >= f'c;
  (b) tidak ada hasil uji individu yang lebih rendah dari f'c sebesar > 3,5 MPa (f'c <= 35 MPa)
      atau > 0,10 f'c (f'c > 35 MPa).
"""
from __future__ import annotations

from typing import Dict, List


def batas_individu(fc: float) -> float:
    return fc - 3.5 if fc <= 35 else 0.90 * fc


def evaluasi_penerimaan(hasil_uji: List[float], fc: float) -> Dict:
    """Evaluasi hasil uji 28 hari terhadap f'c. Mengembalikan dict berisi baris individu, rata-rata 3 berurutan, dan status."""
    hu = [float(x) for x in hasil_uji if x and x > 0]
    bi = batas_individu(fc)
    individu = [dict(no=i + 1, nilai=v, batas=bi, lulus=v >= bi) for i, v in enumerate(hu)]
    rata3 = [dict(rentang=f"{i + 1}-{i + 3}", rata=sum(hu[i:i + 3]) / 3, batas=fc, lulus=sum(hu[i:i + 3]) / 3 >= fc)
             for i in range(len(hu) - 2)]
    cukup = len(hu) >= 3
    lulus_a = all(r["lulus"] for r in rata3) if cukup else None
    lulus_b = all(r["lulus"] for r in individu) if hu else None
    if not cukup:
        status, tingkat = "BELUM CUKUP DATA (minimal 3 hasil uji)", "warn"
    elif lulus_a and lulus_b:
        status, tingkat = "DITERIMA", "ok"
    else:
        status, tingkat = "TIDAK DITERIMA", "error"
    return dict(fc=fc, n=len(hu), hasil=hu, batas_individu=bi, individu=individu, rata3=rata3, lulus_rata3=lulus_a,
                lulus_individu=lulus_b, status=status, tingkat=tingkat,
                rata_total=sum(hu) / len(hu) if hu else None, minimum=min(hu) if hu else None)
