"""Prediksi kuat tekan 28 hari dari pengujian umur dini (3 / 7 / 14 hari)."""
import pandas as pd
import streamlit as st

from ui import inputs
from utils import charts, prediksi

_UMUR_GRAFIK = [3, 7, 14, 21, 28, 45, 60, 90]
_TINGKAT = {"ok": "ok", "waspada": "warn", "bahaya": "error"}


def tampilkan_tab_prediksi(bundle):
    """Render tab; mengembalikan ringkasan prediksi (untuk laporan) atau None."""
    st.caption("Masukkan hasil uji benda uji umur 3, 7, atau 14 hari. Hasil berupa perkiraan; "
               "kepastian tetap dari pengujian umur 28 hari.")
    with st.container(border=True):
        st.markdown("##### 🧪 Data benda uji")
        c = st.columns(4)
        umur = inputs.pilih("Umur pengujian (hari)", prediksi.UMUR_UJI, "pr_umur", 1, c[0])
        jenis = inputs.pilih("Benda uji", ["silinder", "kubus"], "pr_jenis", 0, c[1])
        dimensi = inputs.angka("Diameter / rusuk (mm)", 50.0, 300.0, 150.0, 5.0, "pr_dim", kolom=c[2])
        faktor = inputs.angka("Faktor kubus → silinder", 0.70, 1.00, 0.83, 0.01, "pr_faktor", kolom=c[3])
        if bundle is not None:
            kel, bentuk, fc, fcr = bundle["kelompok_semen"], bundle["bentuk_kasar"], bundle["fc"], bundle["fcr"]
            bentuk_fc = bundle.get("bentuk_uji", "silinder")
            st.caption(f"Jenis semen, agregat, f'c, dan f'cr mengikuti tab Mix Design (f'c {fc:g} MPa benda uji {bentuk_fc}, f'cr {fcr:.1f} MPa).")
        else:
            d = st.columns(3)
            kel = inputs.pilih("Kelompok semen", ["I/II/V", "III"], "pr_kel", 0, d[0])
            bentuk = inputs.pilih("Agregat kasar", ["alami", "batu pecah"], "pr_bentuk", 1, d[1])
            fc = inputs.angka("f'c rencana (MPa)", 10.0, 80.0, 30.0, 0.5, "pr_fc", kolom=d[2])
            fcr = None
            bentuk_fc = "silinder"
        mode = inputs.radio("Data masukan", ["Kuat tekan (MPa)", "Beban hancur (kN)"], "pr_mode", horizontal=True)
        mpa_mode = mode.startswith("Kuat")
        awal = [24.0, 25.2, 23.5, 0.0, 0.0, 0.0] if mpa_mode else [400.0, 430.0, 415.0, 0.0, 0.0, 0.0]
        st.caption("Isi hingga 6 benda uji. Nilai 0 = tidak dipakai.")
        kol, nilai = st.columns(6), []
        for i in range(6):
            nilai.append(inputs.angka(f"Benda uji {i + 1}", 0.0, 100000.0, awal[i], 0.1, f"pr_{'mpa' if mpa_mode else 'kn'}_{i}", "%.1f", kol[i]))
    nilai = [v for v in nilai if v > 0]
    if not nilai:
        st.info("Isi minimal satu hasil uji.")
        return None

    mpa = [v if mpa_mode else prediksi.kuat_tekan_dari_beban(v, jenis, dimensi) for v in nilai]
    ekuiv = [prediksi.ke_bentuk(m, jenis, bentuk_fc, faktor) for m in mpa]
    rata = sum(ekuiv) / len(ekuiv)
    f28 = prediksi.prediksi_28_hari(rata, umur, kel, bentuk, bentuk_fc)
    rata28 = sum(f28.values()) / len(f28)
    status, pesan = prediksi.evaluasi(rata28, fc, fcr)

    with st.container(border=True):
        st.markdown("##### 🔮 Hasil prediksi")
        if len(ekuiv) > 1 and (max(ekuiv) - min(ekuiv)) / rata > 0.15:
            st.warning("Selisih hasil antar benda uji lebih dari 15% dari rata-rata: periksa pembuatan, perawatan, dan penekanan benda uji.")
        st.dataframe(pd.DataFrame({"Kuat tekan terukur (MPa)": mpa, f"Setara {bentuk_fc} (MPa)": ekuiv}).round(2))
        cols = st.columns(4)
        cols[0].metric(f"Rata-rata umur {umur} hari", f"{rata:.1f} MPa")
        for col, (m, v) in zip(cols[1:], f28.items()):
            col.metric(m.split(" (")[0], f"{v:.1f} MPa")
        st.metric("Perkiraan kuat tekan 28 hari (rata-rata 3 metode)", f"{rata28:.1f} MPa",
                  f"rentang {min(f28.values()):.1f} - {max(f28.values()):.1f} MPa", delta_color="off")
        {"ok": st.success, "waspada": st.warning, "bahaya": st.error}[status](pesan)
        if status != "ok" and bundle is not None:
            baru = prediksi.fas_diperlukan(bundle["fas"], rata28, bundle["fcr"])
            st.info(f"Agar mencapai f'cr {bundle['fcr']:.1f} MPa, FAS disarankan sekitar {baru:.3f} (saat ini {bundle['fas']:.3f}). "
                    "Verifikasi dengan campuran percobaan.")
        kurva = {m: prediksi.kurva_umur(v, m, _UMUR_GRAFIK, kel, bentuk, bentuk_fc) for m, v in f28.items()}
        fig = charts.grafik_prediksi(_UMUR_GRAFIK, kurva, (umur, rata), f28, fc, fcr)
        if fig is not None:
            st.plotly_chart(fig)
        else:
            st.line_chart(pd.DataFrame({m.split(" (")[0]: pd.Series(v, index=_UMUR_GRAFIK) for m, v in kurva.items()}))
    return dict(umur=umur, jumlah=len(nilai), rata=rata, f28=f28, rata28=rata28, tingkat=_TINGKAT[status], pesan=pesan)
