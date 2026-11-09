"""Autentikasi: whitelist Gmail (modul murni utils/auth.py)."""
import os
import tempfile

import pytest

from utils import auth


def _lingkungan(**nilai):
    lama = {k: os.environ.get(k) for k in ("MIXDESIGN_EMAIL_IZIN", "MIXDESIGN_DATA_DIR", "MIXDESIGN_AUTH_MODE")}
    for k in lama:
        os.environ.pop(k, None)
    os.environ.update(nilai)
    return lama


def _pulihkan(lama):
    for k, v in lama.items():
        os.environ.pop(k, None) if v is None else os.environ.__setitem__(k, v)


def test_kanonik_gmail():
    assert auth.kanonik_gmail("  Nama.Satu+Tes@GMail.com ") == "namasatu@gmail.com"
    assert auth.kanonik_gmail("abc@googlemail.com") == "abc@gmail.com"
    for buruk in ("", "tanpa-at", "a@yahoo.com", "a@gmail.co", "@gmail.com", "a b@gmail.com", "+x@gmail.com", None):
        assert auth.kanonik_gmail(buruk) is None, buruk


def test_periksa_akses():
    daftar = {"pembuat@gmail.com", "rekan@gmail.com"}
    assert auth.periksa_akses("Pembuat@Gmail.com", daftar).status == "diizinkan"
    assert auth.periksa_akses("pem.buat+x@gmail.com", daftar).status == "diizinkan"        # varian yang sama di Gmail
    hasil = auth.periksa_akses("orang@gmail.com", daftar)
    assert hasil.status == "ditolak" and "izin" in hasil.pesan.lower() and "orang@gmail.com" in hasil.pesan
    assert auth.periksa_akses("orang@yahoo.com", daftar).status == "tidak_valid"
    assert auth.periksa_akses("pembuat@gmail.com", set()).status == "ditolak"               # daftar kosong: semua ditolak


def test_sumber_daftar_izin_digabung():
    folder = tempfile.mkdtemp()
    open(os.path.join(folder, "email_izin.txt"), "w").write("# komentar\nberkas@gmail.com\n\nBukan-Gmail@yahoo.com\n")
    lama = _lingkungan(MIXDESIGN_EMAIL_IZIN="env1@gmail.com, Env.Dua@gmail.com", MIXDESIGN_DATA_DIR=folder)
    auth.EMAIL_DIIZINKAN.append("Kode@Gmail.com")
    try:
        assert auth.muat_daftar_izin() == {"env1@gmail.com", "envdua@gmail.com", "berkas@gmail.com", "kode@gmail.com"}
    finally:
        auth.EMAIL_DIIZINKAN.remove("Kode@Gmail.com")
        _pulihkan(lama)


def test_mode_auth():
    lama = _lingkungan()
    try:
        assert auth.mode_auth() == "email"
        for nilai, harap in (("google", "google"), (" OFF ", "off"), ("aneh", "email")):
            os.environ["MIXDESIGN_AUTH_MODE"] = nilai
            assert auth.mode_auth() == harap
    finally:
        _pulihkan(lama)


def test_catat_akses():
    folder = tempfile.mkdtemp()
    lama = _lingkungan(MIXDESIGN_DATA_DIR=folder)
    try:
        auth.catat_akses("orang@gmail.com", "ditolak")
        auth.catat_akses("a,b@gmail.com", "diizinkan")                      # koma tidak merusak format CSV
        baris = open(os.path.join(folder, "log_akses.csv")).read().splitlines()
        assert len(baris) == 2 and baris[0].endswith("orang@gmail.com,ditolak") and all(b.count(",") == 2 for b in baris)
        os.environ["MIXDESIGN_DATA_DIR"] = os.path.join(folder, "log_akses.csv", "x")   # tidak dapat ditulis: tidak boleh melempar
        auth.catat_akses("x@gmail.com", "ditolak")
    finally:
        _pulihkan(lama)
