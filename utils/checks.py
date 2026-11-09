"""Pemeriksaan mutu hasil uji agregat dan mix design -> daftar status (ok / warn / error / info)."""
from __future__ import annotations

from typing import List

from utils.format_id import angka


def tingkat_dari_deviasi(deviasi: float, batas_warn: float = 5.0) -> str:
    """0 -> ok; hingga batas_warn poin persen di luar batas -> warn; lebih -> error."""
    if deviasi <= 1e-9:
        return "ok"
    return "warn" if deviasi <= batas_warn else "error"


def _tingkat_gabung(daftar) -> str:
    daftar = list(daftar)
    return "error" if "error" in daftar else "warn" if "warn" in daftar else "ok"


BATAS_NO200 = {"halus": 5.0, "kasar": 1.0}     # % maks. (ASTM C33: pasir 5%, kerikil 1%)


def lolos_no200(sieve: dict):
    """(persen lolos No. 200, sumber). Memakai uji cuci SNI 03-4142 bila ada; jika belum diisi,
    estimasi dari massa pan (kurang akurat)."""
    info = sieve.get("no200")
    if info and info.get("nilai") is not None:
        return float(info["nilai"]), "uji cuci SNI 03-4142"
    df = sieve["df"].set_index("Saringan (mm)")
    return (float(df.loc[0.075, "Lolos (%)"]) if 0.075 in df.index else 0.0), "estimasi dari massa pan (isi uji cuci)"


def tingkat_no200(nilai: float, jenis: str) -> str:
    batas = BATAS_NO200[jenis]
    return "ok" if nilai <= batas else "warn" if nilai <= batas * 1.4 else "error"


def periksa_mutu(modul_sni: bool, hasil, extra: dict, lab: dict) -> List[dict]:
    """Daftar pemeriksaan: dict(parameter, nilai, batas, tingkat). tingkat: ok | warn | error | info."""
    baris = []
    add = lambda p, n, b, t: baris.append(dict(parameter=p, nilai=n, batas=b, tingkat=t))

    fas_maks = extra.get("fas_maks")
    if fas_maks:
        add("FAS efektif", angka(hasil.fas, 3), f"maks. {angka(fas_maks, 2)}", "ok" if hasil.fas <= fas_maks + 1e-9 else "error")
    semen = hasil.lapangan.semen
    if modul_sni:
        smin = extra["semen_min"]
        add("Kadar semen minimum", f"{angka(semen, 1)} kg/m³", f"min. {angka(smin, 0)} kg/m³", "ok" if semen >= smin - 1e-6 else "error")
    add("Kadar semen (batas praktis)", f"{angka(semen, 1)} kg/m³", "maks. 550 kg/m³",
        "ok" if semen <= 550 else "warn" if semen <= 600 else "error")

    sh, sk = lab["sieve_halus"], lab["sieve_kasar"]
    add("Gradasi agregat halus", sh["spec_nama"], "dalam batas zona", sh["level"])
    add("Modulus kehalusan agregat halus", angka(sh["mk"], 2), "2,30 - 3,10", sh["level_mk"])
    for jenis, sv_, nama in (("halus", sh, "agregat halus"), ("kasar", sk, "agregat kasar")):
        v, sumber = lolos_no200(sv_)
        add(f"Material lolos No. 200 ({nama})", f"{angka(v, 2)} % ({sumber})", f"maks. {angka(BATAS_NO200[jenis], 0)} %", tingkat_no200(v, jenis))
        if jenis == "halus":
            add("Gradasi agregat kasar", sk["spec_nama"], "dalam batas ASTM C33", sk["level"])
    add("Air yang ditambahkan (lapangan)", f"{angka(hasil.lapangan.air, 1)} kg/m³", "min. 0", "ok" if hasil.lapangan.air >= 0 else "error")
    for p in hasil.peringatan:
        add("Catatan perhitungan", p, "", "warn")
    return baris


def tingkat_keseluruhan(daftar: List[dict]) -> str:
    return _tingkat_gabung(d["tingkat"] for d in daftar if d["tingkat"] != "info")
