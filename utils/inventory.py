"""Pencatatan stok material laboratorium (buku besar masuk/keluar).

Sisa stok = jumlah masuk - jumlah keluar per bahan; semua jumlah dalam kg. Penyimpanan dapat dipilih lewat variabel lingkungan:

    MIXDESIGN_STOK_BACKEND = csv (bawaan) | sqlite | supabase
    MIXDESIGN_DATA_DIR     = folder data CSV (bawaan: <proyek>/data)
    MIXDESIGN_STOK_DB      = berkas SQLite (bawaan: <folder data>/stok.db)
    SUPABASE_URL, SUPABASE_KEY = alamat proyek dan kunci API Supabase

Skema Supabase (SQL):
    create table stok_material (id bigint generated always as identity primary key, waktu text, bahan text, jenis text,
                                jumlah_kg double precision, input text, keterangan text);
    create table stok_ambang (bahan text primary key, nilai double precision);
"""
from __future__ import annotations

import json
import os
import sqlite3
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd

BAHAN = ["Semen", "Pasir", "Split", "Admixture"]
SATUAN = {
    "Semen": ["kg", "sak 40 kg", "sak 50 kg", "ton"],
    "Pasir": ["kg", "ton", "m³"],
    "Split": ["kg", "ton", "m³"],
    "Admixture": ["kg", "liter"],
}
KOLOM = ["Waktu", "Bahan", "Jenis", "Jumlah (kg)", "Input", "Keterangan"]
JENIS = ["Masuk", "Keluar"]
AMBANG_BAWAAN = {"Semen": 500.0, "Pasir": 2000.0, "Split": 2000.0, "Admixture": 20.0}


def folder_data() -> Path:
    env = os.environ.get("MIXDESIGN_DATA_DIR")
    return Path(env) if env else Path(__file__).resolve().parent.parent / "data"


def ke_kg(satuan: str, jumlah: float, bi_gembur: Optional[float] = None, bj_admixture: float = 1.10) -> float:
    """Konversi satuan input ke kg. m3 memakai berat isi gembur (kg/m3); liter memakai berat jenis admixture."""
    faktor = {"kg": 1.0, "ton": 1000.0, "sak 40 kg": 40.0, "sak 50 kg": 50.0}
    if satuan in faktor:
        return jumlah * faktor[satuan]
    if satuan == "m³":
        if not bi_gembur or bi_gembur <= 0:
            raise ValueError("Berat isi gembur belum tersedia untuk konversi m³.")
        return jumlah * bi_gembur
    if satuan == "liter":
        return jumlah * bj_admixture
    raise ValueError(f"Satuan tidak dikenal: {satuan}")


def tingkat_stok(sisa: float, ambang: float) -> Tuple[str, str]:
    """(label, tingkat badge): Habis (error) | Menipis (warn) | Aman (ok)."""
    if sisa <= 1e-9:
        return "HABIS", "error"
    if sisa < ambang:
        return "MENIPIS", "warn"
    return "AMAN", "ok"


def _bersihkan(df: pd.DataFrame) -> pd.DataFrame:
    for k in KOLOM:
        if k not in df.columns:
            df[k] = ""
    df["Jumlah (kg)"] = pd.to_numeric(df["Jumlah (kg)"], errors="coerce").fillna(0.0)
    df[["Input", "Keterangan"]] = df[["Input", "Keterangan"]].fillna("")
    return df[KOLOM]


# ----------------------------------------------------------------------------- penyimpanan
class PenyimpananCSV:
    def __init__(self, folder: Optional[Path] = None):
        self.folder = Path(folder) if folder else folder_data()
        self.file = self.folder / "stok_material.csv"
        self.file_ambang = self.folder / "stok_ambang.json"
        self.label = f"CSV lokal ({self.file})"

    def baca(self) -> pd.DataFrame:
        return pd.DataFrame(columns=KOLOM) if not self.file.exists() else _bersihkan(pd.read_csv(self.file))

    def tambah(self, baris: List[list]) -> None:
        try:
            self.folder.mkdir(parents=True, exist_ok=True)
            pd.concat([self.baca(), pd.DataFrame(baris, columns=KOLOM)], ignore_index=True).to_csv(self.file, index=False)
        except OSError as e:
            raise RuntimeError(f"Tidak dapat menulis data stok ({self.file}): {e}")

    def hapus_terakhir(self) -> bool:
        df = self.baca()
        if df.empty:
            return False
        try:
            df.iloc[:-1].to_csv(self.file, index=False)
        except OSError as e:
            raise RuntimeError(f"Tidak dapat menulis data stok: {e}")
        return True

    def baca_ambang(self) -> Dict[str, float]:
        try:
            return json.loads(self.file_ambang.read_text()) if self.file_ambang.exists() else {}
        except (OSError, ValueError):
            return {}

    def simpan_ambang(self, ambang: Dict[str, float]) -> None:
        try:
            self.folder.mkdir(parents=True, exist_ok=True)
            self.file_ambang.write_text(json.dumps(ambang))
        except OSError as e:
            raise RuntimeError(f"Tidak dapat menulis pengaturan ambang: {e}")


class PenyimpananSQLite:
    def __init__(self, path):
        self.path = str(path)
        self.label = f"SQLite ({self.path})"
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        with self._sambung() as c:
            c.execute("create table if not exists stok (id integer primary key autoincrement, waktu text, bahan text, jenis text, "
                      "jumlah_kg real, input text, keterangan text)")
            c.execute("create table if not exists ambang (bahan text primary key, nilai real)")

    def _sambung(self):
        return sqlite3.connect(self.path)

    def baca(self) -> pd.DataFrame:
        with self._sambung() as c:
            baris = c.execute("select waktu, bahan, jenis, jumlah_kg, input, keterangan from stok order by id").fetchall()
        return _bersihkan(pd.DataFrame(baris, columns=KOLOM))

    def tambah(self, baris: List[list]) -> None:
        try:
            with self._sambung() as c:       # satu transaksi: semua atau tidak sama sekali
                c.executemany("insert into stok (waktu, bahan, jenis, jumlah_kg, input, keterangan) values (?,?,?,?,?,?)", baris)
        except sqlite3.Error as e:
            raise RuntimeError(f"Gagal menulis ke SQLite: {e}")

    def hapus_terakhir(self) -> bool:
        with self._sambung() as c:
            r = c.execute("select max(id) from stok").fetchone()
            if r[0] is None:
                return False
            c.execute("delete from stok where id = ?", (r[0],))
        return True

    def baca_ambang(self) -> Dict[str, float]:
        with self._sambung() as c:
            return {b: v for b, v in c.execute("select bahan, nilai from ambang")}

    def simpan_ambang(self, ambang: Dict[str, float]) -> None:
        with self._sambung() as c:
            c.executemany("insert or replace into ambang (bahan, nilai) values (?, ?)", list(ambang.items()))


class PenyimpananSupabase:
    """Supabase (PostgREST) lewat HTTPS; hanya memakai pustaka standar."""

    def __init__(self, url: str, key: str, timeout: float = 15.0):
        self.url, self.key, self.timeout = url.rstrip("/"), key, timeout
        self.label = f"Supabase ({self.url})"

    def _minta(self, metode: str, jalur: str, badan=None, header=None):
        req = urllib.request.Request(self.url + "/rest/v1/" + jalur, method=metode,
                                     data=None if badan is None else json.dumps(badan).encode("utf-8"),
                                     headers={"apikey": self.key, "Authorization": f"Bearer {self.key}", "Content-Type": "application/json", **(header or {})})
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as r:
                isi = r.read()
        except urllib.error.HTTPError as e:
            raise RuntimeError(f"Supabase menolak permintaan ({e.code}): {e.read().decode('utf-8', 'replace')[:200]}")
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            raise RuntimeError(f"Tidak dapat menghubungi Supabase: {e}")
        return json.loads(isi) if isi else None

    def baca(self) -> pd.DataFrame:
        data = self._minta("GET", "stok_material?select=*&order=id.asc") or []
        return _bersihkan(pd.DataFrame([[d.get("waktu"), d.get("bahan"), d.get("jenis"), d.get("jumlah_kg"), d.get("input"), d.get("keterangan")]
                                        for d in data], columns=KOLOM))

    def tambah(self, baris: List[list]) -> None:
        self._minta("POST", "stok_material", [dict(zip(["waktu", "bahan", "jenis", "jumlah_kg", "input", "keterangan"], b)) for b in baris],
                    {"Prefer": "return=minimal"})

    def hapus_terakhir(self) -> bool:
        data = self._minta("GET", "stok_material?select=id&order=id.desc&limit=1") or []
        if not data:
            return False
        self._minta("DELETE", f"stok_material?id=eq.{int(data[0]['id'])}", header={"Prefer": "return=minimal"})
        return True

    def baca_ambang(self) -> Dict[str, float]:
        return {d["bahan"]: float(d["nilai"]) for d in (self._minta("GET", "stok_ambang?select=*") or [])}

    def simpan_ambang(self, ambang: Dict[str, float]) -> None:
        self._minta("POST", "stok_ambang?on_conflict=bahan", [dict(bahan=b, nilai=v) for b, v in ambang.items()],
                    {"Prefer": "resolution=merge-duplicates,return=minimal"})


def buat_penyimpanan(folder: Optional[str] = None):
    """Pilih penyimpanan dari variabel lingkungan (bawaan: CSV lokal)."""
    jenis = os.environ.get("MIXDESIGN_STOK_BACKEND", "csv").strip().lower()
    if jenis == "csv":
        return PenyimpananCSV(folder)
    if jenis == "sqlite":
        return PenyimpananSQLite(os.environ.get("MIXDESIGN_STOK_DB") or (Path(folder) if folder else folder_data()) / "stok.db")
    if jenis == "supabase":
        url, key = os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_KEY")
        if not url or not key:
            raise RuntimeError("Backend Supabase membutuhkan variabel lingkungan SUPABASE_URL dan SUPABASE_KEY.")
        return PenyimpananSupabase(url, key)
    raise ValueError(f"MIXDESIGN_STOK_BACKEND tidak dikenal: {jenis} (pilihan: csv, sqlite, supabase)")


# ----------------------------------------------------------------------------- buku besar
class Stok:
    def __init__(self, folder: Optional[str] = None, penyimpanan=None):
        self.p = penyimpanan or buat_penyimpanan(folder)
        self.label = self.p.label

    def muat(self) -> pd.DataFrame:
        return self.p.baca()

    def sisa(self, df: Optional[pd.DataFrame] = None) -> Dict[str, float]:
        df = self.muat() if df is None else df
        hasil = {}
        for b in BAHAN:
            d = df[df["Bahan"] == b]
            hasil[b] = float(d.loc[d["Jenis"] == "Masuk", "Jumlah (kg)"].sum() - d.loc[d["Jenis"] == "Keluar", "Jumlah (kg)"].sum())
        return hasil

    def ambang(self) -> Dict[str, float]:
        data = dict(AMBANG_BAWAAN)
        try:
            data.update({k: float(v) for k, v in self.p.baca_ambang().items() if k in BAHAN})
        except (RuntimeError, ValueError):
            pass
        return data

    def simpan_ambang(self, ambang: Dict[str, float]) -> None:
        self.p.simpan_ambang({k: float(v) for k, v in ambang.items() if k in BAHAN})

    def tambah_banyak(self, transaksi: List[dict]) -> None:
        """Tambah beberapa transaksi sekaligus (semua berhasil atau tidak sama sekali).
        Tiap item: bahan, jenis, jumlah_kg, input, keterangan (opsional waktu)."""
        sisa = self.sisa()
        baris = []
        for t in transaksi:
            b, j, kg = t["bahan"], t["jenis"], float(t["jumlah_kg"])
            if b not in BAHAN or j not in JENIS:
                raise ValueError("Bahan atau jenis transaksi tidak valid.")
            if kg <= 0:
                raise ValueError("Jumlah harus lebih dari 0.")
            sisa[b] += kg if j == "Masuk" else -kg
            if sisa[b] < -1e-9:
                raise ValueError(f"Stok {b} tidak cukup: kekurangan {-sisa[b]:.1f} kg.")
            baris.append([t.get("waktu") or datetime.now().strftime("%Y-%m-%d %H:%M"), b, j, kg, t.get("input", ""), t.get("keterangan", "")])
        self.p.tambah(baris)

    def tambah(self, bahan: str, jenis: str, jumlah_kg: float, input_txt: str = "", keterangan: str = "") -> None:
        self.tambah_banyak([dict(bahan=bahan, jenis=jenis, jumlah_kg=jumlah_kg, input=input_txt, keterangan=keterangan)])

    def hapus_terakhir(self) -> bool:
        df = self.muat()
        if df.empty:
            return False
        if min(self.sisa(df.iloc[:-1]).values()) < -1e-9:
            raise ValueError("Transaksi terakhir tidak bisa dihapus karena membuat stok bahan lain negatif.")
        return self.p.hapus_terakhir()
