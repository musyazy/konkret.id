"""Kriteria penerimaan kuat tekan 28 hari (SNI 2847 / ACI 318) untuk data uji sebenarnya."""
import pandas as pd
import streamlit as st

from ui import components as ui
from ui import inputs
from utils import prediksi
from utils.format_id import angka
from utils.penerimaan import evaluasi_penerimaan

_NAMA = {"ok": "PASS", "warn": "WARNING", "error": "ERROR"}


def tampilkan_tab_penerimaan(bundle):
    """Render tab; mengembalikan hasil evaluasi (dict) bila ada data, atau None."""
    with st.container(border=True):
        st.markdown("##### ✅ Data uji kuat tekan umur 28 hari")
        st.caption("Satu hasil uji = rata-rata benda uji dari satu contoh (mis. dua silinder). Isi minimal 3 hasil uji; nilai 0 = tidak dipakai.")
        c = st.columns(3)
        if bundle is not None:
            fc, bentuk_fc = bundle["fc"], bundle.get("bentuk_uji", "silinder")
            c[0].markdown(f"**f'c rencana**<br>{fc:g} MPa ({bentuk_fc})", unsafe_allow_html=True)
        else:
            fc = inputs.angka("f'c rencana (MPa)", 10.0, 80.0, 30.0, 0.5, "pn_fc", kolom=c[0])
            bentuk_fc = "silinder"
        jenis = inputs.pilih("Bentuk benda uji data", ["silinder", "kubus"], "pn_jenis", 0, c[1])
        faktor = inputs.angka("Faktor kubus → silinder", 0.70, 1.00, 0.83, 0.01, "pn_faktor", kolom=c[2])
        kol, nilai = st.columns(4), []
        for i in range(12):
            nilai.append(inputs.angka(f"Hasil uji {i + 1} (MPa)", 0.0, 200.0, 0.0, 0.1, f"pn_{i}", "%.1f", kol[i % 4]))
    hu = [prediksi.ke_bentuk(v, jenis, bentuk_fc, faktor) for v in nilai if v > 0]
    if not hu:
        st.info("Belum ada hasil uji.")
        return None
    hasil = evaluasi_penerimaan(hu, fc)
    with st.container(border=True):
        st.markdown("##### 🧾 Evaluasi penerimaan")
        m = st.columns(4)
        m[0].metric("Jumlah hasil uji", str(hasil["n"]))
        m[1].metric("Rata-rata", f"{hasil['rata_total']:.1f} MPa")
        m[2].metric("Hasil terendah", f"{hasil['minimum']:.1f} MPa", f"batas individu {hasil['batas_individu']:.1f}", delta_color="off")
        with m[3]:
            st.caption("Keputusan")
            st.markdown(ui.badge(hasil["status"], hasil["tingkat"]), unsafe_allow_html=True)
        ind = pd.DataFrame([[r["no"], angka(r["nilai"], 1), angka(r["batas"], 1), ui.badge("PASS" if r["lulus"] else "ERROR", "ok" if r["lulus"] else "error")]
                            for r in hasil["individu"]], columns=["No.", "Hasil uji (MPa)", "Batas individu (MPa)", "Status"])
        ui.tampilkan_tabel(ind, kolom_html=["Status"])
        if hasil["rata3"]:
            r3 = pd.DataFrame([[r["rentang"], angka(r["rata"], 1), angka(r["batas"], 1), ui.badge("PASS" if r["lulus"] else "ERROR", "ok" if r["lulus"] else "error")]
                               for r in hasil["rata3"]], columns=["Hasil uji ke-", "Rata-rata 3 berurutan (MPa)", "Batas f'c (MPa)", "Status"])
            ui.tampilkan_tabel(r3, kolom_html=["Status"])
        st.caption("Kriteria: rata-rata tiga hasil uji berurutan >= f'c, dan tidak ada hasil individu di bawah f'c - 3,5 MPa (f'c <= 35 MPa) "
                   "atau 0,90 f'c (f'c > 35 MPa).")
    return hasil
