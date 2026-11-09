"""Identitas & data uji material agregat.

Modul ini TIDAK bergantung pada Streamlit, sehingga mudah diuji sendiri.
Satuan: berat jenis (tanpa satuan), penyerapan & kadar air (%), berat isi (kg/m3).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class Agregat:
    nama: str                              # mis. "Pasir Merapi"
    jenis: str                             # "halus" | "kasar"
    bj_curah_kering: float                 # Sd (berat jenis curah kering oven)
    penyerapan_pct: float                  # Sw, dalam %
    kadar_air_pct: float                   # kadar air lapangan, dalam %
    berat_isi: Optional[float] = None      # kg/m3 (kasar: kondisi padat/dry-rodded)
    modulus_kehalusan: Optional[float] = None   # MK (dipakai untuk agregat halus)
    bentuk: str = "alami"                  # "alami" | "batu pecah" (dipakai SNI)

    @property
    def bj_ssd(self) -> float:
        """Berat jenis curah jenuh kering permukaan: Ss = Sd * (1 + Sw)."""
        return self.bj_curah_kering * (1 + self.penyerapan_pct / 100)


# --- Nama sumber agregat yang tersedia di dropdown (tambahkan sesuai kebutuhan) ---
LAINNYA = "Lainnya (ketik manual)"
SUMBER_PASIR = ["Pasir Merapi", "Pasir Progo", LAINNYA]
SUMBER_KASAR = ["Split / Kerikil lokal", LAINNYA]

# --- Jenis semen: nama -> (berat jenis, kelompok pada Tabel 2 SNI) ---
# BJ PCC (3.05) hanya perkiraan; gunakan data dari produsen/uji lab bila ada.
JENIS_SEMEN = {
    "Tipe I / PC biasa (OPC)": dict(bj=3.15, kelompok="I/II/V"),
    "Tipe II": dict(bj=3.15, kelompok="I/II/V"),
    "Tipe III (kekuatan awal tinggi)": dict(bj=3.15, kelompok="III"),
    "Tipe V": dict(bj=3.15, kelompok="I/II/V"),
    "PCC (Portland Composite Cement)": dict(bj=3.05, kelompok="I/II/V"),
}

# --- Nilai awal contoh (ganti dengan data pengujian laboratorium) ---
CONTOH_HALUS = dict(bj_curah_kering=2.582, penyerapan_pct=1.709, kadar_air_pct=5.4,
                    modulus_kehalusan=2.792, bentuk="alami")
CONTOH_KASAR = dict(bj_curah_kering=2.350, penyerapan_pct=2.829, kadar_air_pct=2.0,
                    berat_isi=1450.2, bentuk="batu pecah")


def nilai_awal(jenis: str) -> dict:
    return dict(CONTOH_HALUS if jenis == "halus" else CONTOH_KASAR)


# --- Pengolahan data mentah pengujian lab (untuk dipakai pada pengembangan berikutnya) ---
def bj_agregat_halus(S: float, A: float, B: float, C: float) -> dict:
    """SNI 1970:2016. S=berat SSD, A=kering oven, B=piknometer+air, C=piknometer+benda uji+air."""
    vol = B + S - C
    return dict(Sd=A / vol, Ss=S / vol, Sa=A / (B + A - C), Sw=(S - A) / A * 100)


def bj_agregat_kasar(A: float, B: float, C: float) -> dict:
    """SNI 1969:2016. A=kering oven, B=SSD, C=berat dalam air."""
    return dict(Sd=A / (B - C), Ss=B / (B - C), Sa=A / (A - C), Sw=(B - A) / A * 100)


def berat_isi(berat_wadah_isi: float, berat_wadah: float, volume_wadah: float) -> float:
    """SNI 03-4804-1998. Berat isi (kg/m3) = (G - T) / V."""
    return (berat_wadah_isi - berat_wadah) / volume_wadah


def kadar_air(berat_basah: float, berat_kering: float) -> float:
    """Kadar air agregat (%) = (W - W1) / W1 x 100."""
    return (berat_basah - berat_kering) / berat_kering * 100


def rongga_udara(berat_isi_agregat: float, bj_curah_kering: float, rapat_air: float = 998.0) -> float:
    """Rongga udara (%) = (1 - M / (Sd x rapat air)) x 100  (SNI 03-4804-1998)."""
    return (1 - berat_isi_agregat / (bj_curah_kering * rapat_air)) * 100
