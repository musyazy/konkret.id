"""Kalkulator Mix Design Beton - aplikasi laboratorium teknik sipil (Streamlit, tema dark).

Jalankan dari folder proyek:  streamlit run app.py

Menu sidebar:
  Pekerjaan Beton   ui/halaman_beton.py  (Mix Design SNI & ACI, input lab, prediksi umur dini, laporan & CoA)
  Inventory Stock   ui/tab_inventory.py
  Cost Estimation   ui/tab_biaya.py
Logika: standards/ (sni, aci, admixture) dan utils/ (material_db, sieve, prediksi, slump_assistant, inventory,
biaya, dokumen, laporan_pdf, laporan_html, charts).
"""
import streamlit as st

from standards import aci, sni
from utils import auth
from ui import inputs
from ui.admin import tampilkan_panel_admin
from ui.halaman_beton import halaman_beton
from ui.login import gerbang_login, tombol_logout
from ui.header import input_kop_sidebar, tampilkan_kop
from ui.proyek_ui import sidebar_proyek
from ui.navigasi import MENU_ADMIN, MENU_BETON, MENU_BIAYA, MENU_INVENTORY, navigasi_sidebar
from ui.tab_biaya import tampilkan_tab_biaya
from ui.tab_inventory import tampilkan_tab_inventory
from ui.theme import terapkan_tema

st.set_page_config(page_title="Mix Design Beton", page_icon="🧱", layout="wide")
terapkan_tema()
pengguna = gerbang_login()      # menghentikan skrip bila belum masuk atau belum diizinkan pembuat

STANDAR = {"Standar SNI (03-2834-2000) - konvensional": sni, "Standar ACI 211.1 - boleh admixture": aci}

admin = auth.adalah_admin(pengguna)
menu = navigasi_sidebar(admin, auth.jumlah_permintaan() if admin else 0)
if menu == MENU_BETON:
    with st.sidebar:
        st.markdown('<div class="nav-judul">Standar perhitungan</div>', unsafe_allow_html=True)
        modul = STANDAR[inputs.radio("Standar perhitungan", list(STANDAR), "standar", label_visibility="collapsed")]
else:
    modul = STANDAR[st.session_state.get("v:standar", list(STANDAR)[0])]

kop = input_kop_sidebar()
sidebar_proyek(kop["no_dokumen"].replace("/", "-"))
tombol_logout(pengguna)
tampilkan_kop(kop, modul.NAMA)

if menu == MENU_BETON:
    halaman_beton(modul, kop)
elif menu == MENU_INVENTORY:
    tampilkan_tab_inventory()
elif menu == MENU_BIAYA:
    tampilkan_tab_biaya()
elif menu == MENU_ADMIN and admin:
    tampilkan_panel_admin(pengguna)
