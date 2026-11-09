"""Kop surat / header perusahaan di bagian atas aplikasi dan identitas dokumen (diatur di sidebar)."""
import html
from datetime import date

import streamlit as st

from ui import inputs
from utils.format_id import tanggal_id


def input_kop_sidebar() -> dict:
    """Form identitas dokumen di sidebar. Nilai tersimpan saat berpindah menu."""
    with st.sidebar.expander("📝 Kop surat & identitas dokumen", expanded=False):
        return dict(
            perusahaan=inputs.teks("Nama perusahaan", "kop_perusahaan", "PT. CIPTA KARYA UTAMA"),
            divisi=inputs.teks("Laboratorium / divisi", "kop_divisi", "LABORATORIUM BAHAN BANGUNAN & STRUKTUR"),
            alamat=inputs.teks("Alamat (opsional)", "kop_alamat", ""),
            no_dokumen=inputs.teks("Nomor dokumen", "kop_nodok", "LAB/MD/001/2026"),
            proyek=inputs.teks("Proyek / pekerjaan", "kop_proyek", ""),
            klien=inputs.teks("Klien / pemberi tugas", "kop_klien", ""),
            tanggal=inputs.tanggal("Tanggal pengujian", "kop_tanggal", date.today()),
            penguji=inputs.teks("Penguji / teknisi lab", "kop_penguji", ""),
            penanggung_jawab=inputs.teks("Penanggung jawab lab", "kop_pj", ""),
            jabatan_pj=inputs.teks("Jabatan penanggung jawab", "kop_jabatan", "Manajer Teknis Laboratorium"),
        )


def tampilkan_kop(kop: dict, standar: str) -> None:
    e = lambda v: html.escape(str(v)) if v else "-"
    alamat = f'<div class="alamat">{html.escape(kop["alamat"])}</div>' if kop["alamat"] else ""
    st.markdown(
        f'<div class="kop"><div class="nama">{html.escape(kop["perusahaan"])}</div>'
        f'<div class="divisi">{html.escape(kop["divisi"])}</div>{alamat}</div>'
        f'<table class="kop-meta">'
        f'<tr><td class="k">No. Dokumen</td><td>{e(kop["no_dokumen"])}</td><td class="k">Tanggal Pengujian</td><td>{tanggal_id(kop["tanggal"])}</td></tr>'
        f'<tr><td class="k">Proyek</td><td>{e(kop["proyek"])}</td><td class="k">Klien</td><td>{e(kop["klien"])}</td></tr>'
        f'<tr><td class="k">Pekerjaan</td><td>Perencanaan Campuran Beton (Mix Design)</td><td class="k">Standar</td><td>{html.escape(standar)}</td></tr>'
        f'</table>',
        unsafe_allow_html=True,
    )
