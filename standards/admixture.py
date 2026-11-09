"""Logika bahan tambah kimia (admixture / 'obat' beton) yang ditetapkan.

Pengaruh yang dihitung:
  1. Reduksi air bebas:      W' = W x (1 - r/100)
  2. Dosis (terhadap semen): m_adm = dosis% x semen/100  (kg),  V_adm = m_adm / BJ  (liter)
  3. Koreksi volume:         volume cairan admixture ikut dalam volume absolut campuran
  4. Air dalam admixture:    m_adm x kadar air% dikurangkan dari air yang ditambahkan di lapangan

Nilai bawaan reduksi air mengacu pada syarat minimum ASTM C494 (Tipe A/D/E >= 5%, Tipe F/G >= 12%)
dan dosis tipikal; SELALU ganti dengan data teknis (datasheet) produk yang dipakai.
"""
from __future__ import annotations

from dataclasses import dataclass

# nama tampilan -> (kode, dosis bawaan %, reduksi air bawaan %, BJ bawaan kg/liter)
TIPE_ADMIXTURE = {
    "Tanpa admixture": ("-", 0.0, 0.0, 1.00),
    "Tipe A - Water Reducer / Plastisizer": ("A", 0.55, 8.0, 1.10),
    "Tipe B - Retarder": ("B", 0.30, 0.0, 1.10),
    "Tipe C - Accelerator": ("C", 1.00, 0.0, 1.15),
    "Tipe D - Water Reducer + Retarder": ("D", 0.55, 8.0, 1.10),
    "Tipe E - Water Reducer + Accelerator": ("E", 0.55, 8.0, 1.10),
    "Tipe F - Superplastisizer (HRWR)": ("F", 1.20, 20.0, 1.10),
    "Tipe G - HRWR + Retarder": ("G", 1.20, 20.0, 1.10),
}


@dataclass
class Admixture:
    nama: str = "Tanpa admixture"
    dosis_pct: float = 0.0            # % terhadap berat semen
    reduksi_air_pct: float = 0.0      # % pengurangan air bebas
    berat_jenis: float = 1.10         # kg/liter
    kadar_air_pct: float = 0.0        # % air di dalam cairan admixture (0 = diabaikan)

    @property
    def aktif(self) -> bool:
        return self.dosis_pct > 0 or self.reduksi_air_pct > 0

    def massa(self, semen: float) -> float:
        return semen * self.dosis_pct / 100

    def volume_liter(self, semen: float) -> float:
        return self.massa(semen) / self.berat_jenis

    def air_terkandung(self, semen: float) -> float:
        return self.massa(semen) * self.kadar_air_pct / 100


def air_setelah_reduksi(air: float, adm: Admixture) -> float:
    return air * (1 - adm.reduksi_air_pct / 100)


def nilai_awal_tipe(nama_tipe: str) -> dict:
    kode, dosis, reduksi, bj = TIPE_ADMIXTURE[nama_tipe]
    return dict(kode=kode, dosis_pct=dosis, reduksi_air_pct=reduksi, berat_jenis=bj)
