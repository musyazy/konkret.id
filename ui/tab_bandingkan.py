"""Mode Bandingkan SNI vs ACI: satu set input dasar, hasil dua standar berdampingan beserta selisih dan biaya per m³."""
import pandas as pd
import streamlit as st

from standards import aci, sni
from standards.admixture import TIPE_ADMIXTURE, Admixture, nilai_awal_tipe
from ui import components as ui
from ui import inputs
from ui.tab_biaya import biaya_per_m3
from ui.tab_mix import zona_dari_spec
from utils import material_db as mdb
from utils.format_id import angka, rupiah

PADANAN = {"10 mm (SNI) / 9,5 mm (ACI)": (10, 9.5), "20 mm (SNI) / 19 mm (ACI)": (20, 19.0), "40 mm (SNI) / 37,5 mm (ACI)": (40, 37.5)}


def _admixture_aci():
    tipe = inputs.pilih("Admixture untuk kolom ACI", list(TIPE_ADMIXTURE), "cmp_adm_tipe")
    awal = nilai_awal_tipe(tipe)
    if awal["kode"] == "-":
        return Admixture()
    c = st.columns(3)
    k = awal["kode"]
    return Admixture(f"Tipe {k}", inputs.angka("Dosis (% berat semen)", 0.0, 5.0, awal["dosis_pct"], 0.05, f"cmp_dosis_{k}", "%.2f", c[0]),
                     inputs.angka("Reduksi air (%)", 0.0, 40.0, awal["reduksi_air_pct"], 0.5, f"cmp_red_{k}", "%.1f", c[1]),
                     inputs.angka("Berat jenis (kg/liter)", 0.9, 1.5, awal["berat_jenis"], 0.01, f"cmp_bj_{k}", "%.2f", c[2]))


def _baris(nama, a, b, fmt):
    if a is None or b is None:
        return [nama, "-" if a is None else fmt(a), "-" if b is None else fmt(b), "-", "-"]
    selisih = b - a
    return [nama, fmt(a), fmt(b), ("+" if selisih > 0 else "") + fmt(selisih) if fmt is not rupiah else ("+" if selisih > 0 else "") + rupiah(selisih),
            "-" if abs(a) < 1e-9 else f"{selisih / a * 100:+.1f} %"]


def tampilkan_tab_bandingkan(lab, dasar):
    if lab is None:
        st.info("Lengkapi data agregat terlebih dahulu.")
        return
    keys = list(PADANAN)
    awal = next((i for i, k in enumerate(keys) if dasar["ukuran"] in PADANAN[k]), 2)
    with st.container(border=True):
        st.markdown("##### ⚖️ Satu input, dua standar")
        st.caption(f"Memakai parameter dasar di atas (f'c {dasar['fc']:g} MPa, slump {dasar['slump']:g} mm, semen {dasar['semen_nama']}). "
                   "Pengaturan lanjutan memakai nilai bawaan tiap standar.")
        c = st.columns(2)
        uk_sni, uk_aci = PADANAN[inputs.pilih("Ukuran maks. agregat kasar (padanan)", keys, "cmp_ukuran", awal, c[0])]
        bentuk_uji = inputs.radio("Bentuk benda uji f'c (kolom SNI)", sni.BENTUK_UJI, "cmp_bentuk_uji", 0, c[1], horizontal=True, format_func=str.capitalize)
        adm = _admixture_aci()

    info = mdb.JENIS_SEMEN[dasar["semen_nama"]]
    halus = lab["halus"].__class__(**{**lab["halus"].__dict__, "bentuk": dasar["bentuk_h"]})
    kasar = lab["kasar"].__class__(**{**lab["kasar"].__dict__, "bentuk": dasar["bentuk_k"]})
    s = st.session_state.get("v:s", 5.0) if st.session_state.get("v:ada_s", True) else None
    lingk = st.session_state.get("v:lingk")
    semen_min, fas_maks_sni = sni.LINGKUNGAN.get(lingk, next(iter(sni.LINGKUNGAN.values())))
    zona = zona_dari_spec(lab["sieve_halus"]["spec_nama"])
    hasil, galat = {}, {}
    try:
        hasil["SNI"] = sni.hitung_mix_design_sni(dasar["fc"], dasar["slump"], uk_sni, halus, kasar, kelompok_semen=info["kelompok"], simpangan_baku=s,
                                                 fas_maks=fas_maks_sni, semen_min=semen_min, bj_semen=info["bj"], bentuk_uji=bentuk_uji, zona_pasir=zona)
    except ValueError as e:
        galat["SNI"] = str(e)
    try:
        hasil["ACI"] = aci.hitung_mix_design_aci(dasar["fc"], dasar["slump"], uk_aci, halus, kasar, bj_semen=info["bj"], simpangan_baku=s,
                                                 fas_maks=aci.LINGKUNGAN.get(st.session_state.get("v:lingk_aci")), admixture=adm)
    except ValueError as e:
        galat["ACI"] = str(e)
    for k, e in galat.items():
        st.error(f"Kolom {k}: {e}")
    if len(hasil) < 2:
        return

    a, b = hasil["SNI"], hasil["ACI"]
    ba, bb = biaya_per_m3(a.lapangan, lab), biaya_per_m3(b.lapangan, lab)
    f1 = lambda v: angka(v, 1)
    baris = [_baris("f'cr (MPa)", a.fcr, b.fcr, f1), _baris("FAS efektif", a.fas, b.fas, lambda v: angka(v, 3)),
             _baris("Air bebas (kg/m³)", a.teoritis.air, b.teoritis.air, f1), _baris("Semen (kg/m³)", a.lapangan.semen, b.lapangan.semen, f1),
             _baris("Air lapangan (kg/m³)", a.lapangan.air, b.lapangan.air, f1), _baris("Pasir lapangan (kg/m³)", a.lapangan.agregat_halus, b.lapangan.agregat_halus, f1),
             _baris("Kerikil lapangan (kg/m³)", a.lapangan.agregat_kasar, b.lapangan.agregat_kasar, f1),
             _baris("Admixture (kg/m³)", a.lapangan.admixture, b.lapangan.admixture, lambda v: angka(v, 2)),
             _baris("Biaya total / m³", ba["total"], bb["total"], rupiah)]
    with st.container(border=True):
        st.markdown("##### 📊 Hasil berdampingan (kondisi lapangan)")
        ui.tampilkan_tabel(pd.DataFrame(baris, columns=["Parameter", "SNI 03-2834-2000", "ACI 211.1", "Selisih (ACI - SNI)", "Selisih (%)"]))
        d = bb["total"] - ba["total"]
        st.info(f"Biaya ACI {'lebih mahal' if d > 0 else 'lebih hemat'} {rupiah(abs(d))} per m³ dibanding SNI (harga satuan dari menu Cost Estimation).")
        st.bar_chart(pd.DataFrame({"SNI": [a.lapangan.semen, a.lapangan.agregat_halus, a.lapangan.agregat_kasar, a.lapangan.air],
                                   "ACI": [b.lapangan.semen, b.lapangan.agregat_halus, b.lapangan.agregat_kasar, b.lapangan.air]},
                                  index=["Semen", "Pasir", "Kerikil", "Air"]))
        for nama, h in (("SNI", a), ("ACI", b)):
            for p in h.peringatan:
                st.warning(f"{nama}: {p}")
