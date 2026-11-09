"""Manajemen akses multi-user: permintaan akses, persetujuan admin, sandi admin (utils/auth.py)."""
import hashlib
import json
import os
import tempfile
import threading

import pytest

from utils import auth

_KUNCI = ("MIXDESIGN_EMAIL_IZIN", "MIXDESIGN_DATA_DIR", "MIXDESIGN_EMAIL_ADMIN", "MIXDESIGN_ADMIN_PASSWORD", "MIXDESIGN_ADMIN_PASSWORD_SHA256")


def _siapkan(**kv):
    lama = {k: os.environ.get(k) for k in _KUNCI}
    for k in _KUNCI:
        os.environ.pop(k, None)
    os.environ["MIXDESIGN_DATA_DIR"] = tempfile.mkdtemp()
    os.environ.update(kv)
    return lama


def _pulihkan(lama):
    for k, v in lama.items():
        os.environ.pop(k, None) if v is None else os.environ.__setitem__(k, v)


def test_permintaan_dicatat_tanpa_duplikat_dan_dibersihkan():
    lama = _siapkan(MIXDESIGN_EMAIL_IZIN="tetap@gmail.com")
    try:
        h = auth.ajukan_permintaan("Calon.Satu@GMail.com", "Budi\n\t<b>PT X</b> " + "x" * 200)
        assert h.status == "dicatat"
        d = auth.daftar_permintaan()
        assert len(d) == 1 and d[0]["email"] == "calonsatu@gmail.com" and len(d[0]["keterangan"]) <= 80 and "\n" not in d[0]["keterangan"]
        assert auth.ajukan_permintaan("calonsatu+x@gmail.com").status == "sudah_diajukan"       # varian Gmail yang sama
        assert auth.ajukan_permintaan("tetap@gmail.com").status == "sudah_diizinkan"
        assert auth.ajukan_permintaan("orang@yahoo.com").status == "tidak_valid"
        assert auth.jumlah_permintaan() == 1
    finally:
        _pulihkan(lama)


def test_antrean_dibatasi():
    lama = _siapkan()
    maks = auth.MAKS_PERMINTAAN
    auth.MAKS_PERMINTAAN = 3
    try:
        for i in range(3):
            assert auth.ajukan_permintaan(f"orang{i}@gmail.com").status == "dicatat"
        assert auth.ajukan_permintaan("orang9@gmail.com").status == "penuh"
    finally:
        auth.MAKS_PERMINTAAN = maks
        _pulihkan(lama)


def test_setujui_masuk_whitelist_tolak_dan_cabut():
    lama = _siapkan(MIXDESIGN_EMAIL_ADMIN="admin@gmail.com")
    try:
        for e in ("a@gmail.com", "b@gmail.com"):
            auth.ajukan_permintaan(e)
        assert auth.periksa_akses("a@gmail.com").status == "ditolak"
        assert auth.setujui("A@gmail.com", "admin@gmail.com") is True
        assert auth.periksa_akses("a@gmail.com").status == "diizinkan" and auth.jumlah_permintaan() == 1
        assert [d["email"] for d in auth.daftar_disetujui()] == ["a@gmail.com"] and auth.daftar_disetujui()[0]["oleh"] == "admin@gmail.com"
        assert auth.tolak("b@gmail.com", "admin@gmail.com") is True and auth.jumlah_permintaan() == 0
        assert auth.periksa_akses("b@gmail.com").status == "ditolak" and auth.tolak("b@gmail.com", "x") is False
        assert auth.cabut("a@gmail.com", "admin@gmail.com") is True and auth.periksa_akses("a@gmail.com").status == "ditolak"
        assert auth.cabut("a@gmail.com", "x") is False
    finally:
        _pulihkan(lama)


def test_admin_selalu_diizinkan_dan_tambah_manual():
    lama = _siapkan(MIXDESIGN_EMAIL_ADMIN="Ad.min@gmail.com")
    try:
        assert auth.adalah_admin("admin+x@gmail.com") and not auth.adalah_admin("lain@gmail.com") and not auth.adalah_admin(None)
        assert auth.periksa_akses("admin@gmail.com").status == "diizinkan"
        assert auth.tambah_manual("baru@gmail.com", "admin@gmail.com").status == "dicatat" and auth.periksa_akses("baru@gmail.com").status == "diizinkan"
        assert auth.tambah_manual("baru@gmail.com", "admin@gmail.com").status == "sudah_diizinkan"
        assert auth.tambah_manual("bukan-email", "admin@gmail.com").status == "tidak_valid"
        auth.ajukan_permintaan("antre@gmail.com")
        assert auth.tambah_manual("antre@gmail.com", "admin@gmail.com").status == "dicatat" and auth.jumlah_permintaan() == 0     # antrean ikut dibersihkan
    finally:
        _pulihkan(lama)


def test_sandi_admin():
    lama = _siapkan()
    try:
        assert auth.verifikasi_sandi_admin("apa-saja") is None and not auth.sandi_admin_terkonfigurasi()
        os.environ["MIXDESIGN_ADMIN_PASSWORD"] = "rahasia"
        assert auth.verifikasi_sandi_admin("rahasia") is True and auth.verifikasi_sandi_admin("salah") is False and auth.verifikasi_sandi_admin("") is False
        del os.environ["MIXDESIGN_ADMIN_PASSWORD"]
        os.environ["MIXDESIGN_ADMIN_PASSWORD_SHA256"] = hashlib.sha256("hash-saya".encode()).hexdigest().upper()
        assert auth.verifikasi_sandi_admin("hash-saya") is True and auth.verifikasi_sandi_admin("hash") is False and auth.sandi_admin_terkonfigurasi()
    finally:
        _pulihkan(lama)


def test_permintaan_bersamaan_tidak_hilang():
    lama = _siapkan()
    try:
        ts = [threading.Thread(target=auth.ajukan_permintaan, args=(f"u{i}@gmail.com",)) for i in range(30)]
        [t.start() for t in ts]; [t.join() for t in ts]
        assert auth.jumlah_permintaan() == 30
    finally:
        _pulihkan(lama)


def test_berkas_rusak_diamankan_dan_folder_tak_bisa_ditulis():
    lama = _siapkan()
    try:
        folder = os.environ["MIXDESIGN_DATA_DIR"]
        open(os.path.join(folder, auth.BERKAS_PERMINTAAN), "w").write("{bukan json")
        assert auth.daftar_permintaan() == [] and any(".rusak-" in n for n in os.listdir(folder))     # salinan rusak tersimpan
        assert auth.ajukan_permintaan("pulih@gmail.com").status == "dicatat"
        os.environ["MIXDESIGN_DATA_DIR"] = os.path.join(folder, auth.BERKAS_PERMINTAAN, "tak-bisa")      # induknya berkas: tidak bisa dibuat
        assert auth.ajukan_permintaan("lain@gmail.com").status == "gagal"
    finally:
        _pulihkan(lama)
