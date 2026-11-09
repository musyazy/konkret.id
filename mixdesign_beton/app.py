"""Kalkulator Mix Design Beton - antarmuka Streamlit.

Jalankan:  streamlit run app.py
Logika perhitungan ada di standards/ (sni.py, aci.py); data material di utils/material_db.py.
"""
import pandas as pd
import streamlit as st

from standards import aci, sni
from utils import material_db as mdb

st.set_page_config(page_title="Mix Design Beton", page_icon="🧱", layout="wide")

STANDAR = {"Standar SNI (03-2834-2000)": sni, "Standar ACI 211.1": aci}


# ----------------------------------------------------------------------------------
# Komponen input
# ----------------------------------------------------------------------------------
def input_agregat(jenis: str) -> mdb.Agregat:
    """Form identitas + data lab satu jenis agregat. Mengembalikan objek Agregat."""
    awal = mdb.nilai_awal(jenis)
    sumber = mdb.SUMBER_PASIR if jenis == "halus" else mdb.SUMBER_KASAR
    judul = "Agregat Halus (Pasir)" if jenis == "halus" else "Agregat Kasar (Split/Kerikil)"
    st.subheader(judul)

    pilihan = st.selectbox("Sumber / nama agregat", sumber, key=f"sumber_{jenis}")
    nama = st.text_input("Nama sumber", key=f"nama_{jenis}", placeholder="mis. Pasir Kali Putih") \
        if pilihan == mdb.LAINNYA else pilihan

    bj = st.number_input("Berat jenis curah kering (Sd)", 1.0, 4.0, awal["bj_curah_kering"], 0.001, format="%.3f", key=f"bj_{jenis}")
    sw = st.number_input("Penyerapan air (%)", 0.0, 20.0, awal["penyerapan_pct"], 0.001, format="%.3f", key=f"sw_{jenis}")
    ka = st.number_input("Kadar air lapangan (%)", 0.0, 30.0, awal["kadar_air_pct"], 0.1, format="%.2f", key=f"ka_{jenis}")
    bentuk = st.radio("Bentuk agregat", ["alami", "batu pecah"], index=0 if awal["bentuk"] == "alami" else 1,
                      horizontal=True, key=f"bentuk_{jenis}")
    bi = mk = None
    if jenis == "halus":
        mk = st.number_input("Modulus kehalusan (MK)", 1.0, 4.0, awal["modulus_kehalusan"], 0.01, format="%.2f", key="mk_halus")
    else:
        bi = st.number_input("Berat isi padat (kg/m³)", 800.0, 2200.0, awal["berat_isi"], 1.0, format="%.1f", key="bi_kasar")
    return mdb.Agregat(nama or "(tanpa nama)", jenis, bj, sw, ka, berat_isi=bi, modulus_kehalusan=mk, bentuk=bentuk)


# ----------------------------------------------------------------------------------
# Sidebar
# ----------------------------------------------------------------------------------
with st.sidebar:
    st.title("🧱 Mix Design Beton")
    nama_standar = st.radio("Pilih standar perhitungan", list(STANDAR))
    modul = STANDAR[nama_standar]
    st.divider()
    nama_proyek = st.text_input("Nama proyek / pekerjaan", placeholder="opsional, untuk laporan")
    volume_uji = st.number_input("Volume campuran uji (m³)", 0.001, 10.0, 0.05, 0.005, format="%.3f")
    st.caption("Semua hasil utama dalam kg per 1 m³ beton.")

st.title(f"Perencanaan Campuran Beton — {modul.NAMA}")

# ----------------------------------------------------------------------------------
# Input
# ----------------------------------------------------------------------------------
tab_input, tab_hasil = st.tabs(["1. Input data", "2. Hasil perhitungan"])

with tab_input:
    st.subheader("Parameter desain")
    c1, c2, c3 = st.columns(3)
    fc = c1.number_input("Mutu beton rencana f'c (MPa)", 10.0, 80.0, 30.0, 0.5)
    slump = c2.number_input("Slump rencana (mm)", 0.0, 250.0, 100.0, 5.0)
    ukuran = c3.selectbox("Ukuran maks. agregat kasar (mm)", modul.UKURAN_MAKS_TERSEDIA,
                          index=min(2, len(modul.UKURAN_MAKS_TERSEDIA) - 1))

    st.subheader("Parameter khusus standar")
    ada_s = st.checkbox("Deviasi standar (s) diketahui dari data lapangan", value=True)
    s = st.number_input("Deviasi standar s (MPa)", 0.0, 20.0, 5.0, 0.1) if ada_s else None

    if modul is sni:
        d1, d2, d3 = st.columns(3)
        fas_grafik = d1.number_input("FAS dari Tabel 2 + Grafik 1", 0.20, 1.00, 0.49, 0.01)
        fas_maks = d2.number_input("FAS maksimum (persyaratan)", 0.20, 1.00, 0.60, 0.01)
        semen_min = d3.number_input("Kadar semen minimum (kg/m³)", 200.0, 500.0, 275.0, 5.0)
        e1, e2 = st.columns(2)
        persen_halus = e1.number_input("Persen agregat halus (Grafik 13-15) %", 10.0, 90.0, 36.0, 0.5)
        berat_beton = e2.number_input("Berat isi beton (Grafik 16) kg/m³", 2000.0, 2600.0, 2315.0, 5.0)
        extra = dict(fas_grafik=fas_grafik, fas_maks=fas_maks, semen_min=semen_min,
                     persen_halus=persen_halus, berat_isi_beton=berat_beton)
    else:
        d1, d2 = st.columns(2)
        bj_semen = d1.number_input("Berat jenis semen", 2.8, 3.4, 3.15, 0.01)
        metode = d2.radio("Metode berat agregat halus", ["volume", "massa"], horizontal=True,
                          format_func=lambda m: "Volume absolut" if m == "volume" else "Perkiraan massa beton")
        ae = st.checkbox("Beton dengan tambahan udara (air-entrained)")
        paparan = st.selectbox("Tingkat paparan", aci.PAPARAN) if ae else "ringan"
        pakai_fas_maks = st.checkbox("Batasi FAS maksimum (durabilitas)")
        fas_maks = st.number_input("FAS maksimum", 0.20, 1.00, 0.50, 0.01) if pakai_fas_maks else None
        extra = dict(bj_semen=bj_semen, metode_halus=metode, beton_ae=ae, paparan=paparan, fas_maks=fas_maks)

    st.subheader("Identitas & data uji agregat")
    kiri, kanan = st.columns(2)
    with kiri:
        halus = input_agregat("halus")
    with kanan:
        kasar = input_agregat("kasar")

    hitung = st.button("Hitung mix design", type="primary")

# ----------------------------------------------------------------------------------
# Hasil
# ----------------------------------------------------------------------------------
with tab_hasil:
    if not hitung and "hasil" not in st.session_state:
        st.info("Isi data pada tab 'Input data', lalu klik **Hitung mix design**.")
    else:
        if hitung:
            try:
                if modul is sni:
                    hasil = sni.hitung_mix_design_sni(fc, s, slump, ukuran, halus, kasar, **extra)
                else:
                    hasil = aci.hitung_mix_design_aci(fc, slump, ukuran, halus, kasar, simpangan_baku=s, **extra)
                st.session_state["hasil"] = (hasil, halus, kasar, fc, slump, ukuran, nama_proyek, volume_uji)
            except ValueError as e:
                st.session_state.pop("hasil", None)
                st.error(f"Input tidak valid: {e}")
        if "hasil" in st.session_state:
            hasil, halus, kasar, fc_, slump_, ukuran_, proyek, vol = st.session_state["hasil"]

            st.subheader("Kebutuhan material per 1 m³ beton (kondisi lapangan)")
            lap = hasil.lapangan
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Semen", f"{lap.semen:.1f} kg")
            m2.metric("Air (ditambahkan)", f"{lap.air:.1f} kg")
            m3.metric(f"Pasir ({halus.nama})", f"{lap.agregat_halus:.1f} kg")
            m4.metric(f"Kerikil ({kasar.nama})", f"{lap.agregat_kasar:.1f} kg")

            tabel = pd.DataFrame({
                "Bahan": ["Semen", "Air", f"Agregat halus — {halus.nama}", f"Agregat kasar — {kasar.nama}"],
                f"Teoritis ({hasil.kondisi_teoritis}) kg/m³": [hasil.teoritis.semen, hasil.teoritis.air,
                                                             hasil.teoritis.agregat_halus, hasil.teoritis.agregat_kasar],
                "Lapangan kg/m³": [lap.semen, lap.air, lap.agregat_halus, lap.agregat_kasar],
                f"Campuran uji {vol:g} m³ (kg)": [lap.semen * vol, lap.air * vol,
                                                  lap.agregat_halus * vol, lap.agregat_kasar * vol],
            }).round(2)
            st.dataframe(tabel, hide_index=True, use_container_width=True)
            st.caption(f"f'cr = {hasil.fcr:.2f} MPa · FAS = {hasil.fas:.3f}")

            for p in hasil.peringatan:
                st.warning(p)

            with st.expander("Rincian langkah perhitungan"):
                st.dataframe(pd.DataFrame([vars(l) for l in hasil.langkah]).rename(
                    columns={"uraian": "Uraian", "nilai": "Nilai", "satuan": "Satuan", "sumber": "Tabel / rumus"}),
                    hide_index=True, use_container_width=True)

            laporan = tabel.copy()
            laporan.insert(0, "Standar", hasil.standar)
            laporan.insert(1, "Proyek", proyek or "-")
            st.download_button("Unduh laporan (CSV)", laporan.to_csv(index=False).encode("utf-8"),
                               file_name="mix_design_beton.csv", mime="text/csv")
