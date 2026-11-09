"""Tab Grafik: kurva gradasi, hubungan FAS - kuat tekan, komposisi campuran."""
import pandas as pd
import streamlit as st

from standards import aci, sni, sni_grafik
from ui import components as ui
from utils import charts, gradasi_gabungan


def _gradasi(judul: str, hs: dict):
    df, spec = hs["df"], hs["spec"]
    fig = charts.grafik_gradasi(df, spec, hs["spec_nama"], judul)
    if fig is not None:
        st.plotly_chart(fig)
    else:  # cadangan bila Plotly belum terpasang
        data = pd.DataFrame({"Hasil uji": df.set_index("Saringan (mm)")["Lolos (%)"]})
        data["Batas bawah"] = pd.Series({k: v[0] for k, v in spec.items()})
        data["Batas atas"] = pd.Series({k: v[1] for k, v in spec.items()})
        st.line_chart(data.sort_index())
    st.caption(f"Acuan: {hs['spec_nama']} · MK = {hs['mk']:.3f} · "
               f"{'memenuhi' if hs['lulus'] else 'tidak memenuhi'} batas spesifikasi")


def tampilkan_tab_grafik(lab, bundle):
    st.subheader("Kurva gradasi agregat vs batas spesifikasi")
    if lab is None:
        st.info("Data analisa saringan belum lengkap.")
    else:
        kiri, kanan = st.columns(2)
        with kiri:
            _gradasi("Gradasi agregat halus (pasir)", lab["sieve_halus"])
        with kanan:
            _gradasi("Gradasi agregat kasar (split/kerikil)", lab["sieve_kasar"])

    st.subheader("Hubungan FAS terhadap kuat tekan (f'cr)")
    if bundle is None:
        st.info("Hitung mix design pada tab 'Mix Design' terlebih dahulu.")
        return
    f0 = sni.kuat_tekan_acuan(bundle["kelompok_semen"], bundle["bentuk_kasar"], 28, bundle.get("bentuk_uji", "silinder"))
    g1x, g1y = sni_grafik.kurva_grafik1(f0, bundle["kelompok_semen"])
    aci_n, aci_ae = aci.kurva_fas(False), aci.kurva_fas(True)
    kurva = [(f"SNI Grafik 1 (digitalisasi, f0 = {f0:g} MPa)", g1x, g1y), ("ACI 211.1 tanpa udara", aci_n[1], aci_n[0]),
             ("ACI 211.1 dengan udara", aci_ae[1], aci_ae[0])]
    fig = charts.grafik_fas_fcr(kurva, bundle["fcr"], bundle["fas"], f"Rancangan ({bundle['standar']})")
    if fig is not None:
        st.plotly_chart(fig)
    else:
        data = pd.DataFrame({nama: pd.Series(list(y), index=[round(v, 3) for v in x]) for nama, x, y in kurva})
        st.line_chart(data.sort_index())
    st.caption("Kurva SNI = Grafik 1 hasil digitalisasi, dibentuk melalui (FAS 0,5; f0 Tabel 2); kurva ACI dari Tabel A1.5.3.4(a). "
               "Bintang = FAS efektif dan f'cr hasil rancangan.")

    st.subheader("Optimasi gradasi gabungan (kurva ideal Fuller)")
    if lab is None:
        return
    try:
        dmaks = float(bundle["ukuran"])
        p_des = bundle["hasil"].parameter.get("persen_halus")
        p_des = p_des / 100 if p_des else (bundle["hasil"].teoritis.agregat_halus / (bundle["hasil"].teoritis.agregat_halus + bundle["hasil"].teoritis.agregat_kasar))
        opt = gradasi_gabungan.optimasi_rasio(lab["sieve_halus"]["df"], lab["sieve_kasar"]["df"], dmaks, p_des)
    except ValueError as e:
        st.warning(str(e))
        return
    with st.container(border=True):
        m = st.columns(4)
        m[0].metric("Rasio pasir : kerikil rekomendasi", opt["rasio"])
        m[1].metric("Rasio rancangan", f"{p_des * 100:.0f} : {(1 - p_des) * 100:.0f}")
        m[2].metric("Selisih RMS rekomendasi", f"{opt['rmse']:.2f} poin")
        m[3].metric("Selisih RMS rancangan", f"{opt['rmse_desain']:.2f} poin")
        figg = charts.grafik_gabungan(opt["sieves"], opt["fuller"], opt["optimal"], opt["desain"], opt["rasio"], f"{p_des * 100:.0f} : {(1 - p_des) * 100:.0f}")
        if figg is not None:
            st.plotly_chart(figg)
        else:
            st.line_chart(pd.DataFrame({"Fuller": opt["fuller"], "Optimal": opt["optimal"], "Rancangan": opt["desain"]}, index=opt["sieves"]).sort_index())
        st.caption(f"Acuan: kurva Fuller untuk ukuran maks {dmaks:g} mm (selisih terkecil terhadap Fuller). Batas gradasi gabungan SNI belum tersedia di aplikasi; "
                   "rasio rekomendasi adalah saran awal, pilih dengan mempertimbangkan kelecakan dan hasil campuran percobaan.")

    st.subheader("Komposisi campuran per 1 m³ (kondisi lapangan)")
    lap = bundle["hasil"].lapangan
    st.bar_chart(pd.DataFrame({"kg/m³": [lap.semen, lap.air, lap.agregat_halus, lap.agregat_kasar]}, index=["Semen", "Air", "Pasir", "Kerikil"]))
