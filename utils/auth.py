"""Izin akses (whitelist) berbasis alamat Gmail. Modul murni tanpa Streamlit.

PEMBUAT APLIKASI mengatur siapa yang boleh masuk lewat salah satu (atau semua) sumber berikut, lalu digabung:
  1. daftar EMAIL_DIIZINKAN di bawah ini (edit file ini);
  2. variabel lingkungan MIXDESIGN_EMAIL_IZIN, dipisah koma:  "a@gmail.com,b@gmail.com";
  3. berkas data/email_izin.txt (satu email per baris, baris berawalan # diabaikan; folder diatur MIXDESIGN_DATA_DIR).

Manajemen akses multi-user:
  * Pengguna yang ditolak dapat mengirim permintaan akses -> data/pending_requests.json.
  * ADMIN (EMAIL_ADMIN di bawah atau MIXDESIGN_EMAIL_ADMIN) selalu diizinkan dan melihat Panel Admin untuk menyetujui/menolak permintaan.
    Persetujuan disimpan di data/approved_emails.json dan otomatis ikut dalam whitelist.
  * Mode `email` tidak memverifikasi pemilik email, sehingga Panel Admin pada mode itu WAJIB sandi admin
    (MIXDESIGN_ADMIN_PASSWORD, atau MIXDESIGN_ADMIN_PASSWORD_SHA256 berisi hash SHA-256 heksadesimal). Mode `google` tidak butuh sandi.

Mode autentikasi (variabel lingkungan MIXDESIGN_AUTH_MODE):
  email   (bawaan) pengguna mengetik Gmail; dicocokkan dengan whitelist. TIDAK memverifikasi kepemilikan email.
  google  login Google (OIDC) lewat st.login (Streamlit >= 1.42); email yang dicocokkan sudah terverifikasi oleh Google.
  off     tanpa login (hanya untuk pengembangan lokal).
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import tempfile
import threading
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set

# >>> TAMBAHKAN email yang diizinkan di sini (contoh: "nama@gmail.com") <<<
EMAIL_DIIZINKAN = [
    # "pembuat@gmail.com",
]

# >>> Email ADMIN (pembuat): selalu diizinkan dan dapat membuka Panel Admin <<<
EMAIL_ADMIN = [
    "bagaskiki1234@gmail.com",
]

BERKAS_PERMINTAAN = "pending_requests.json"
BERKAS_DISETUJUI = "approved_emails.json"
MAKS_PERMINTAAN = 200
_KUNCI = threading.Lock()

MODE_TERSEDIA = ("email", "google", "off")
DOMAIN_GMAIL = ("gmail.com", "googlemail.com")
MAKS_PERCOBAAN = 5
_POLA = re.compile(r"^[a-z0-9][a-z0-9._%+\-]*@[a-z0-9.\-]+\.[a-z]{2,}$")


@dataclass
class HasilAkses:
    status: str            # "diizinkan" | "ditolak" | "tidak_valid"
    email: Optional[str]   # bentuk baku (kanonik) bila valid
    pesan: str


def mode_auth() -> str:
    mode = os.environ.get("MIXDESIGN_AUTH_MODE", "email").strip().lower()
    return mode if mode in MODE_TERSEDIA else "email"


def kanonik_gmail(email: str) -> Optional[str]:
    """Bentuk baku alamat Gmail: huruf kecil, tanpa titik pada nama, tanpa +tag, googlemail.com -> gmail.com.
    None bila bukan alamat Gmail yang valid. (Gmail menganggap a.b+x@gmail.com dan ab@gmail.com satu kotak surat.)"""
    e = (email or "").strip().lower()
    if len(e) > 254 or not _POLA.match(e):
        return None
    lokal, domain = e.rsplit("@", 1)
    if domain not in DOMAIN_GMAIL:
        return None
    lokal = lokal.split("+")[0].replace(".", "")
    return f"{lokal}@gmail.com" if lokal else None


def _folder() -> Path:
    return Path(os.environ.get("MIXDESIGN_DATA_DIR") or Path(__file__).resolve().parent.parent / "data")


def _baca_berkas() -> Iterable[str]:
    folder = _folder()
    try:
        return [b.strip() for b in (folder / "email_izin.txt").read_text(encoding="utf-8").splitlines() if b.strip() and not b.strip().startswith("#")]
    except OSError:
        return []


def muat_daftar_izin() -> Set[str]:
    """Gabungan whitelist (bentuk baku) dari daftar di file ini, variabel lingkungan, dan berkas data/email_izin.txt."""
    mentah = list(EMAIL_DIIZINKAN) + [x for x in os.environ.get("MIXDESIGN_EMAIL_IZIN", "").split(",") if x.strip()] + list(_baca_berkas())
    mentah += [d.get("email", "") for d in _baca_json(BERKAS_DISETUJUI)]
    return {k for k in (kanonik_gmail(x) for x in mentah) if k} | muat_admin()


def periksa_akses(email: str, daftar: Optional[Set[str]] = None, terverifikasi: bool = False) -> HasilAkses:
    """Cocokkan email dengan whitelist. `terverifikasi` = True bila email berasal dari login Google (bukan ketikan)."""
    kanon = kanonik_gmail(email)
    if kanon is None:
        return HasilAkses("tidak_valid", None, "Masukkan alamat Gmail yang valid, contoh: nama@gmail.com.")
    daftar = muat_daftar_izin() if daftar is None else daftar
    if not daftar:
        return HasilAkses("ditolak", kanon, "Akses ditolak. Belum ada email yang diizinkan; pembuat aplikasi perlu mengisi daftar izin.")
    if kanon not in daftar:
        return HasilAkses("ditolak", kanon, f"Akses ditolak. Alamat {email.strip()} belum terdaftar. Hubungi pembuat aplikasi untuk meminta izin akses.")
    return HasilAkses("diizinkan", kanon, "Akses diizinkan.")


def catat_akses(email: str, hasil: str) -> None:
    """Catat percobaan masuk (waktu, email, hasil) ke data/log_akses.csv agar pembuat tahu siapa yang meminta izin. Gagal tulis diabaikan."""
    folder = _folder()
    try:
        folder.mkdir(parents=True, exist_ok=True)
        with open(folder / "log_akses.csv", "a", encoding="utf-8") as f:
            f.write(f"{datetime.now().isoformat(timespec='seconds')},{(email or '').strip().replace(',', ' ')[:80]},{hasil}\n")
    except OSError:
        pass


# ----------------------------------------------------------------------------- penyimpanan JSON
def _baca_json(nama: str) -> List[dict]:
    """Baca daftar dari data/<nama>. Berkas rusak diganti nama (.rusak) agar tidak tertimpa diam-diam; hasil kosong."""
    jalur = _folder() / nama
    try:
        data = json.loads(jalur.read_text(encoding="utf-8"))
        return [d for d in data if isinstance(d, dict)] if isinstance(data, list) else []
    except FileNotFoundError:
        return []
    except (OSError, ValueError):
        try:
            jalur.rename(jalur.with_name(f"{nama}.rusak-{datetime.now():%Y%m%d%H%M%S}"))
        except OSError:
            pass
        return []


def _tulis_json(nama: str, data: List[dict]) -> None:
    """Tulis atomik (berkas sementara lalu os.replace). RuntimeError bila gagal."""
    folder = _folder()
    try:
        folder.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=folder, suffix=".tmp")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=1)
        os.replace(tmp, folder / nama)
    except OSError as e:
        raise RuntimeError(f"Tidak dapat menyimpan {nama}: {e}")


def _bersihkan_teks(teks: str, maks: int = 80) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[\x00-\x1f\x7f]", " ", teks or "")).strip()[:maks]


# ----------------------------------------------------------------------------- admin & permintaan akses
@dataclass
class HasilPermintaan:
    status: str      # dicatat | sudah_diajukan | sudah_diizinkan | tidak_valid | penuh | gagal
    pesan: str


def muat_admin() -> Set[str]:
    mentah = list(EMAIL_ADMIN) + [x for x in os.environ.get("MIXDESIGN_EMAIL_ADMIN", "").split(",") if x.strip()]
    return {k for k in (kanonik_gmail(x) for x in mentah) if k}


def adalah_admin(email: Optional[str]) -> bool:
    kanon = kanonik_gmail(email or "")
    return kanon is not None and kanon in muat_admin()


def sandi_admin_terkonfigurasi() -> bool:
    return bool(os.environ.get("MIXDESIGN_ADMIN_PASSWORD") or os.environ.get("MIXDESIGN_ADMIN_PASSWORD_SHA256"))


def verifikasi_sandi_admin(sandi: str) -> Optional[bool]:
    """True/False bila sandi cocok atau tidak; None bila sandi admin belum dikonfigurasi."""
    polos, hash_ = os.environ.get("MIXDESIGN_ADMIN_PASSWORD"), os.environ.get("MIXDESIGN_ADMIN_PASSWORD_SHA256", "").strip().lower()
    if polos:
        return hmac.compare_digest(sandi.encode("utf-8"), polos.encode("utf-8"))
    if hash_:
        return hmac.compare_digest(hashlib.sha256(sandi.encode("utf-8")).hexdigest(), hash_)
    return None


def daftar_permintaan() -> List[Dict]:
    """Permintaan akses yang menunggu, terlama lebih dulu."""
    with _KUNCI:
        return sorted(_baca_json(BERKAS_PERMINTAAN), key=lambda d: d.get("diminta", ""))


def jumlah_permintaan() -> int:
    return len(daftar_permintaan())


def ajukan_permintaan(email: str, keterangan: str = "") -> HasilPermintaan:
    """Catat permintaan akses ke data/pending_requests.json (tanpa duplikat; maks MAKS_PERMINTAAN)."""
    kanon = kanonik_gmail(email)
    if kanon is None:
        return HasilPermintaan("tidak_valid", "Alamat Gmail tidak valid.")
    if kanon in muat_daftar_izin():
        return HasilPermintaan("sudah_diizinkan", "Email ini sudah diizinkan. Silakan masuk.")
    with _KUNCI:
        daftar = _baca_json(BERKAS_PERMINTAAN)
        if any(kanonik_gmail(d.get("email", "")) == kanon for d in daftar):
            return HasilPermintaan("sudah_diajukan", "Permintaan Anda sudah tercatat dan menunggu persetujuan admin.")
        if len(daftar) >= MAKS_PERMINTAAN:
            return HasilPermintaan("penuh", "Antrean permintaan penuh. Hubungi pembuat aplikasi secara langsung.")
        daftar.append(dict(email=kanon, keterangan=_bersihkan_teks(keterangan), diminta=datetime.now().isoformat(timespec="seconds")))
        try:
            _tulis_json(BERKAS_PERMINTAAN, daftar)
        except RuntimeError:
            return HasilPermintaan("gagal", "Permintaan tidak dapat disimpan. Hubungi pembuat aplikasi.")
    catat_akses(kanon, "minta_akses")
    return HasilPermintaan("dicatat", "Permintaan akses terkirim. Admin akan meninjau; coba masuk lagi setelah disetujui.")


def _hapus_permintaan(daftar: List[dict], kanon: str) -> List[dict]:
    return [d for d in daftar if kanonik_gmail(d.get("email", "")) != kanon]


def setujui(email: str, oleh: str) -> bool:
    """Pindahkan email dari antrean ke data/approved_emails.json. True bila ada perubahan."""
    kanon = kanonik_gmail(email)
    if kanon is None:
        return False
    with _KUNCI:
        antrean = _baca_json(BERKAS_PERMINTAAN)
        disetujui = _baca_json(BERKAS_DISETUJUI)
        ada = any(kanonik_gmail(d.get("email", "")) == kanon for d in antrean)
        if kanon not in {kanonik_gmail(d.get("email", "")) for d in disetujui}:
            disetujui.append(dict(email=kanon, disetujui=datetime.now().isoformat(timespec="seconds"), oleh=oleh))
            _tulis_json(BERKAS_DISETUJUI, disetujui)
            ada = True
        if ada:
            _tulis_json(BERKAS_PERMINTAAN, _hapus_permintaan(antrean, kanon))
    if ada:
        catat_akses(kanon, f"disetujui_oleh_{oleh}")
    return ada


def tolak(email: str, oleh: str) -> bool:
    kanon = kanonik_gmail(email)
    if kanon is None:
        return False
    with _KUNCI:
        antrean = _baca_json(BERKAS_PERMINTAAN)
        sisa = _hapus_permintaan(antrean, kanon)
        if len(sisa) == len(antrean):
            return False
        _tulis_json(BERKAS_PERMINTAAN, sisa)
    catat_akses(kanon, f"ditolak_oleh_{oleh}")
    return True


def daftar_disetujui() -> List[Dict]:
    with _KUNCI:
        return sorted(_baca_json(BERKAS_DISETUJUI), key=lambda d: d.get("disetujui", ""))


def cabut(email: str, oleh: str) -> bool:
    """Hapus email dari persetujuan admin (tidak berlaku untuk whitelist statis/admin)."""
    kanon = kanonik_gmail(email)
    if kanon is None:
        return False
    with _KUNCI:
        daftar = _baca_json(BERKAS_DISETUJUI)
        sisa = _hapus_permintaan(daftar, kanon)
        if len(sisa) == len(daftar):
            return False
        _tulis_json(BERKAS_DISETUJUI, sisa)
    catat_akses(kanon, f"dicabut_oleh_{oleh}")
    return True


def tambah_manual(email: str, oleh: str) -> HasilPermintaan:
    """Admin menambahkan email langsung ke daftar disetujui (tanpa menunggu permintaan)."""
    kanon = kanonik_gmail(email)
    if kanon is None:
        return HasilPermintaan("tidak_valid", "Alamat Gmail tidak valid.")
    if kanon in muat_daftar_izin():
        return HasilPermintaan("sudah_diizinkan", f"{kanon} sudah diizinkan.")
    try:
        setujui(kanon, oleh) if any(kanonik_gmail(d.get("email", "")) == kanon for d in daftar_permintaan()) else _tambah_langsung(kanon, oleh)
    except RuntimeError as e:
        return HasilPermintaan("gagal", str(e))
    return HasilPermintaan("dicatat", f"{kanon} ditambahkan ke daftar izin.")


def _tambah_langsung(kanon: str, oleh: str) -> None:
    with _KUNCI:
        daftar = _baca_json(BERKAS_DISETUJUI)
        daftar.append(dict(email=kanon, disetujui=datetime.now().isoformat(timespec="seconds"), oleh=oleh))
        _tulis_json(BERKAS_DISETUJUI, daftar)
    catat_akses(kanon, f"ditambah_oleh_{oleh}")
