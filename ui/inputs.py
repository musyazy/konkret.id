"""Pembungkus widget agar isian TIDAK hilang saat berpindah menu sidebar.
Setiap nilai disalin ke st.session_state['v:<key>'] (non-widget) dan dipakai kembali sebagai nilai awal."""
import streamlit as st

from utils import format_id


def _ambil(key, default):
    return st.session_state.get("v:" + key, default)


def _simpan(key, nilai):
    st.session_state["v:" + key] = nilai
    return nilai


def angka(label, minimum, maksimum, default, langkah, key, fmt=None, kolom=None, **kw):
    w = kolom if kolom is not None else st
    nilai = min(max(_ambil(key, default), minimum), maksimum)
    if fmt:
        kw["format"] = fmt
    return _simpan(key, w.number_input(label, minimum, maksimum, nilai, langkah, key="w:" + key, **kw))


def pilih(label, opsi, key, indeks=0, kolom=None, **kw):
    w = kolom if kolom is not None else st
    opsi = list(opsi)
    tersimpan = _ambil(key, None)
    idx = opsi.index(tersimpan) if tersimpan in opsi else indeks
    return _simpan(key, w.selectbox(label, opsi, index=idx, key="w:" + key, **kw))


def radio(label, opsi, key, indeks=0, kolom=None, **kw):
    w = kolom if kolom is not None else st
    opsi = list(opsi)
    tersimpan = _ambil(key, None)
    idx = opsi.index(tersimpan) if tersimpan in opsi else indeks
    return _simpan(key, w.radio(label, opsi, index=idx, key="w:" + key, **kw))


def centang(label, key, default=False, kolom=None, **kw):
    w = kolom if kolom is not None else st
    return _simpan(key, w.checkbox(label, value=_ambil(key, default), key="w:" + key, **kw))


def teks(label, key, default="", kolom=None, **kw):
    w = kolom if kolom is not None else st
    return _simpan(key, w.text_input(label, value=_ambil(key, default), key="w:" + key, **kw))


def tanggal(label, key, default, kolom=None, **kw):
    w = kolom if kolom is not None else st
    return _simpan(key, w.date_input(label, value=_ambil(key, default), key="w:" + key, **kw))


def banyak_pilih(label, opsi, key, default=None, kolom=None, **kw):
    w = kolom if kolom is not None else st
    opsi = list(opsi)
    tersimpan = [x for x in _ambil(key, default if default is not None else []) if x in opsi]
    return _simpan(key, w.multiselect(label, opsi, default=tersimpan, key="w:" + key, **kw))


def rupiah(label, key, default, kolom=None):
    """Isian Rupiah bulat bergaya Indonesia: ketik 250000 -> tampil 250.000 (tanpa desimal)."""
    w = kolom if kolom is not None else st
    simpan = int(_ambil(key, default))

    def _terapkan():
        baru = format_id.baca_rupiah(st.session_state.get("w:" + key, ""))
        if baru is not None:
            st.session_state["v:" + key] = baru

    mentah = w.text_input(label, value=format_id.ribuan(simpan), key="w:" + key, on_change=_terapkan)
    nilai = format_id.baca_rupiah(mentah)
    if nilai is None:
        w.caption("⚠️ Masukkan angka, contoh: 250.000")
        nilai = simpan
    return _simpan(key, nilai)
