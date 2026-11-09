"""Halaman Pekerjaan Beton: parameter dasar, input lab, mix design SNI & ACI, bandingkan, grafik, prediksi, trial mix,
troubleshooter slump, penerimaan 28 hari, laporan & CoA."""
import streamlit as st

from ui.tab_agregat import gabung_lab, tampilkan_tab_agregat
from ui.tab_bandingkan import tampilkan_tab_bandingkan
from ui.tab_grafik import tampilkan_tab_grafik
from ui.tab_laporan import tampilkan_tab_laporan
from ui.tab_mix import kartu_dasar, tampilkan_tab_mix
from ui.tab_penerimaan import tampilkan_tab_penerimaan
from ui.tab_prediksi import tampilkan_tab_prediksi
from ui.tab_slump import tampilkan_tab_slump
from ui.tab_trialmix import tampilkan_tab_trialmix


def halaman_beton(modul, kop):
    """Render halaman dan simpan hasil (_lab, _bundle, _prediksi, _penerimaan) untuk menu Inventory & Cost Estimation."""
    st.subheader("🏗️ Pekerjaan Beton")
    dasar = kartu_dasar(modul)            # di atas tab: ukuran maks mempengaruhi acuan gradasi kerikil
    tabs = st.tabs(["🧮 Mix Design", "⚖️ SNI vs ACI", "🧪 Agregat Halus", "🧪 Agregat Kasar", "📈 Grafik", "🔮 Prediksi Umur Dini",
                    "🧫 Trial Mix", "🛠️ Slump vs W/C", "✅ Penerimaan 28 Hari", "🖨️ Laporan & CoA"])
    # Data lab dihitung lebih dulu karena dipakai tab lain.
    with tabs[2]:
        fine = tampilkan_tab_agregat("halus")
    with tabs[3]:
        coarse = tampilkan_tab_agregat("kasar", dasar["ukuran"])
    lab = gabung_lab(fine, coarse)
    with tabs[0]:
        bundle = tampilkan_tab_mix(modul, lab, kop, dasar)
    with tabs[1]:
        tampilkan_tab_bandingkan(lab, dasar)
    with tabs[4]:
        tampilkan_tab_grafik(lab, bundle)
    with tabs[5]:
        prediksi = tampilkan_tab_prediksi(bundle)
    with tabs[6]:
        tampilkan_tab_trialmix(bundle)
    with tabs[7]:
        tampilkan_tab_slump(bundle)
    with tabs[8]:
        penerimaan = tampilkan_tab_penerimaan(bundle)
    with tabs[9]:
        tampilkan_tab_laporan(kop, lab, bundle, prediksi, penerimaan)
    st.session_state.update(_lab=lab, _bundle=bundle, _prediksi=prediksi, _penerimaan=penerimaan)
