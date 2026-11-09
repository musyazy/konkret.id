"""Struktur data hasil & fungsi bantu yang dipakai bersama oleh sni.py dan aci.py."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Sequence, Tuple, Union


def interpolasi(x: float, xs: Sequence[float], ys: Sequence[float]) -> Tuple[float, bool]:
    """Interpolasi linear (xs harus menaik). Di luar rentang dilakukan ekstrapolasi
    dari segmen terdekat; nilai kedua = True bila terjadi ekstrapolasi."""
    if len(xs) != len(ys) or len(xs) < 2:
        raise ValueError("Data interpolasi tidak valid.")
    ekstrapolasi = x < xs[0] or x > xs[-1]
    if x <= xs[0]:
        i = 0
    elif x >= xs[-1]:
        i = len(xs) - 2
    else:
        i = max(j for j in range(len(xs) - 1) if xs[j] <= x)
    x0, x1, y0, y1 = xs[i], xs[i + 1], ys[i], ys[i + 1]
    return y0 + (y1 - y0) * (x - x0) / (x1 - x0), ekstrapolasi


@dataclass
class Langkah:
    uraian: str
    nilai: Union[float, str]
    satuan: str = ""
    sumber: str = ""          # tabel / grafik yang dipakai
    rumus: str = ""           # rumus (teks biasa)
    substitusi: str = ""      # angka yang disubstitusikan
    latex: str = ""           # rumus untuk st.latex


@dataclass
class Komposisi:
    """Kebutuhan material per 1 m3 beton (kg/m3). Admixture dalam kg (dan liter)."""
    semen: float
    air: float
    agregat_halus: float
    agregat_kasar: float
    admixture: float = 0.0
    admixture_liter: float = 0.0

    def total(self) -> float:
        return self.semen + self.air + self.agregat_halus + self.agregat_kasar + self.admixture


@dataclass
class HasilMixDesign:
    standar: str
    fcr: float
    fas: float                 # FAS efektif (air bebas setelah reduksi / semen)
    teoritis: Komposisi
    kondisi_teoritis: str      # "SSD" (SNI) atau "kering oven" (ACI)
    lapangan: Komposisi        # sudah dikoreksi kadar air lapangan
    langkah: List[Langkah] = field(default_factory=list)
    peringatan: List[str] = field(default_factory=list)
    parameter: dict = field(default_factory=dict)   # nilai otomatis (untuk panel ringkasan & grafik)
