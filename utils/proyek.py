"""Simpan dan muat proyek (JSON): semua isian aplikasi (agregat, parameter, admixture, kop, harga) dipulihkan.

Isian disimpan di st.session_state dengan awalan 'v:' (lihat ui/inputs.py). Modul ini murni (tanpa Streamlit)."""
from __future__ import annotations

import json
from datetime import date, datetime
from typing import Dict

VERSI = 1
AWALAN = "v:"
DIKECUALIKAN = ("stok_", "pratinjau")          # isian transaksi stok tidak bagian dari proyek
MAKS_BYTE = 2_000_000


def _kode(nilai):
    if isinstance(nilai, bool) or nilai is None or isinstance(nilai, (int, float, str)):
        return nilai
    if isinstance(nilai, datetime):
        return {"__tanggal__": nilai.date().isoformat()}
    if isinstance(nilai, date):
        return {"__tanggal__": nilai.isoformat()}
    if isinstance(nilai, (list, tuple)):
        return [_kode(x) for x in nilai]
    raise TypeError(type(nilai).__name__)


def _dekode(nilai):
    if isinstance(nilai, dict) and set(nilai) == {"__tanggal__"}:
        return date.fromisoformat(nilai["__tanggal__"])
    if isinstance(nilai, list):
        return [_dekode(x) for x in nilai]
    if isinstance(nilai, (bool, int, float, str)) or nilai is None:
        return nilai
    raise ValueError("Tipe nilai tidak didukung.")


def ekspor(state) -> bytes:
    """Serialisasi isian (kunci berawalan 'v:') menjadi JSON."""
    data = {}
    for k, v in state.items():
        if isinstance(k, str) and k.startswith(AWALAN) and not any(k[len(AWALAN):].startswith(x) for x in DIKECUALIKAN):
            try:
                data[k[len(AWALAN):]] = _kode(v)
            except TypeError:
                continue
    return json.dumps(dict(aplikasi="MixDesignBeton", versi=VERSI, dibuat=datetime.now().isoformat(timespec="seconds"), data=data),
                      ensure_ascii=False, indent=1).encode("utf-8")


def impor(isi: bytes) -> Dict[str, object]:
    """Baca JSON proyek -> {kunci tanpa awalan: nilai}. ValueError bila format tidak valid."""
    if len(isi) > MAKS_BYTE:
        raise ValueError("Berkas proyek terlalu besar.")
    try:
        obj = json.loads(isi.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as e:
        raise ValueError(f"Berkas bukan JSON yang valid: {e}")
    if not isinstance(obj, dict) or obj.get("aplikasi") != "MixDesignBeton" or not isinstance(obj.get("data"), dict):
        raise ValueError("Berkas bukan proyek Mix Design Beton.")
    if obj.get("versi", 0) > VERSI:
        raise ValueError("Versi berkas proyek lebih baru dari aplikasi ini.")
    return {str(k): _dekode(v) for k, v in obj["data"].items()}
