"""Troubleshooter: koreksi air / semen / superplasticizer bila slump uji tidak sesuai target.
SNI konvensional hanya Opsi A (air + semen); Opsi B (superplasticizer) hanya untuk ACI 211.1."""
import pandas as pd
import streamlit as st

from standards import aci
from ui import inputs
from utils import slump_assistant as sa


def tampilkan_tab_slump(bundle):
    st.subheader("Asisten slump vs w/c (troubleshooter)")
    if bundle is None:
        st.info("Hitung mix design pada tab 'Mix Design' terlebih dahulu.")
        return
    t = bundle["hasil"].teoritis
    st.caption("Koreksi dihitung tanpa mengubah FAS rancangan: air dan semen diubah bersama, atau dosis superplasticizer diubah.")
    for col, (k, v) in zip(st.columns(4), [("Air bebas", f"{t.air:.1f} kg/m³"), ("Semen", f"{t.semen:.1f} kg/m³"),
                                           ("FAS efektif", f"{bundle['fas']:.3f}"), ("Slump rencana", f"{bundle['slump']:g} mm")]):
        col.metric(k, v)

    c = st.columns(2)
    target = inputs.angka("Slump target (mm)", 0.0, 250.0, float(bundle["slump"]), 5.0, "sl_target", kolom=c[0])
    uji = inputs.angka("Slump hasil uji lab (mm)", 0.0, 250.0, float(bundle["slump"]), 5.0, "sl_uji", kolom=c[1])
    with st.expander("Parameter koreksi (kalibrasi dengan trial mix Anda)"):
        e = st.columns(4)
        air10 = inputs.angka("Air per +10 mm slump (kg/m³)", 0.5, 6.0, sa.AIR_PER_10MM, 0.1, "sl_air10", kolom=e[0])
        sp01 = inputs.angka("Slump per +0,1% SP (mm)", 5.0, 100.0, sa.SLUMP_PER_01PCT, 1.0, "sl_sp", kolom=e[1])
        semen_maks = inputs.angka("Semen maksimum (kg/m³)", 350.0, 800.0, 550.0, 10.0, "sl_smaks", kolom=e[2])
        dosis_maks = inputs.angka("Dosis admixture maks (%)", 0.5, 5.0, 2.0, 0.1, "sl_dmaks", kolom=e[3])

    adm = bundle["adm"]
    if bundle["modul"] is not aci:
        st.info("Standar SNI konvensional: koreksi hanya dengan air + semen (FAS tetap). Opsi superplasticizer tersedia pada Standar ACI 211.1.")
    h = sa.hitung_koreksi_slump(
        target, uji, t.air, t.semen, t.agregat_halus, bundle["bj_halus_dasar"], bundle["bj_semen"], bundle["volume_uji"],
        dosis_pct=adm.dosis_pct, bj_admixture=adm.berat_jenis, air_per_10mm=air10, slump_per_01pct=sp01,
        semen_maks=semen_maks, fas_maks=bundle.get("fas_maks"), dosis_maks_pct=dosis_maks,
        izinkan_admixture=bundle["modul"] is aci)

    (st.success if h.dalam_toleransi else st.warning)(
        f"Selisih slump {h.selisih_mm:+.0f} mm (toleransi ±{h.toleransi_mm:.0f} mm).")
    kiri, kanan = st.columns(2)
    if h.opsi_air_semen:
        a = h.opsi_air_semen
        with kiri:
            st.markdown("#### Opsi A - ubah air + semen (FAS tetap)")
            st.dataframe(pd.DataFrame({
                "Bahan": ["Air (kg/m³)", "Semen (kg/m³)", "Pasir (kg/m³)", "FAS"],
                "Semula": [t.air, t.semen, t.agregat_halus, bundle["fas"]],
                "Perubahan": [a["d_air"], a["d_semen"], a["d_halus"], a["fas"] - bundle["fas"]],
                "Baru": [a["air"], a["semen"], a["halus"], a["fas"]]}).round(3), hide_index=True)
            st.caption(f"Untuk campuran uji {bundle['volume_uji']:g} m³: air {a['batch_air']:+.2f} liter, "
                       f"semen {a['batch_semen']:+.2f} kg, pasir {a['batch_halus']:+.2f} kg "
                       "(pasir disesuaikan agar volume tetap 1 m³; berlaku untuk batch berikutnya).")
    if h.opsi_admixture:
        b = h.opsi_admixture
        with kanan:
            st.markdown("#### Opsi B - ubah dosis superplasticizer (air & semen tetap)")
            st.dataframe(pd.DataFrame({
                "Besaran": ["Dosis (% berat semen)", "Admixture (kg/m³)", "Admixture (liter/m³)"],
                "Semula": [b["dosis_lama"], adm.massa(t.semen), adm.volume_liter(t.semen)],
                "Baru": [b["dosis_baru"], b["massa"], b["liter"]]}).round(3), hide_index=True)
            st.caption(f"Untuk campuran uji {bundle['volume_uji']:g} m³: {b['batch_liter']:.3f} liter ({b['batch_massa']:.3f} kg). "
                       f"Perkiraan efek: {b['tercapai']:+.0f} mm.")
    for cat in h.catatan:
        st.warning(cat) if cat.startswith(("Opsi", "Jangan", "FAS")) else st.info(cat)
