"""Trial mix & koreksi otomatis: slump uji + kuat tekan umur dini -> saran air/semen/pasir campuran berikutnya."""
import pandas as pd
import streamlit as st

from standards import aci
from ui import components as ui
from ui import inputs
from utils import prediksi, trialmix
from utils.format_id import angka


def tampilkan_tab_trialmix(bundle):
    if bundle is None:
        st.info("Hitung mix design terlebih dahulu.")
        return
    t = bundle["hasil"].teoritis
    with st.container(border=True):
        st.markdown("##### 🧪 Hasil campuran percobaan (trial mix)")
        c = st.columns(4)
        target = inputs.angka("Slump target (mm)", 0.0, 250.0, float(bundle["slump"]), 5.0, "tm_target", kolom=c[0])
        uji = inputs.angka("Slump hasil uji (mm)", 0.0, 250.0, float(bundle["slump"]), 5.0, "tm_uji", kolom=c[1])
        umur = inputs.pilih("Umur uji kuat tekan (hari)", prediksi.UMUR_UJI, "tm_umur", 1, c[2])
        f_uji = inputs.angka("Kuat tekan rata-rata (MPa)", 0.0, 120.0, 0.0, 0.5, "tm_f", kolom=c[3])
        st.caption(f"Kuat tekan dalam bentuk benda uji f'c ({bundle.get('bentuk_uji', 'silinder')}). Kosongkan (0) bila hanya mengoreksi slump.")
    try:
        r = trialmix.saran_trial_mix(
            air=t.air, semen=t.semen, halus=t.agregat_halus, kasar=t.agregat_kasar, fas=bundle["fas"], fcr=bundle["fcr"], fc=bundle["fc"],
            bj_semen=bundle["bj_semen"], bj_halus=bundle["bj_halus_dasar"], volume_uji=bundle["volume_uji"], slump_target=target, slump_uji=uji,
            f_uji=f_uji or None, umur=umur, kelompok_semen=bundle["kelompok_semen"], bentuk_kasar=bundle["bentuk_kasar"],
            bentuk_uji=bundle.get("bentuk_uji", "silinder"), fas_maks=bundle.get("fas_maks"),
            semen_min=bundle["extra"].get("semen_min"), izinkan_admixture=bundle["modul"] is aci, dosis_pct=bundle["adm"].dosis_pct)
    except ValueError as e:
        st.error(str(e))
        return
    with st.container(border=True):
        st.markdown("##### 🧭 Saran koreksi campuran berikutnya")
        m = st.columns(4)
        m[0].metric("Selisih slump", f"{r['slump'].selisih_mm:+.0f} mm")
        m[1].metric("Kuat tekan 28 hari (prediksi)", "-" if r["rata28"] is None else f"{r['rata28']:.1f} MPa")
        m[2].metric("FAS awal → usulan", f"{r['awal']['fas']:.3f} → {r['usulan']['fas']:.3f}")
        with m[3]:
            st.caption("Status")
            if r["status"]:
                st.markdown(ui.badge({"ok": "PASS", "waspada": "WARNING", "bahaya": "ERROR"}[r["status"]], {"ok": "ok", "waspada": "warn", "bahaya": "error"}[r["status"]]),
                            unsafe_allow_html=True)
        nama = {"air": "Air", "semen": "Semen", "halus": "Pasir", "kasar": "Kerikil", "fas": "FAS"}
        v = bundle["volume_uji"]
        tabel = pd.DataFrame([[nama[k], angka(r["awal"][k], 3 if k == "fas" else 1), angka(r["usulan"][k], 3 if k == "fas" else 1),
                               ("+" if r["perubahan"][k] > 0 else "") + angka(r["perubahan"][k], 3 if k == "fas" else 1),
                               angka(r["batch"][k], 2) if k in r["batch"] else "-"] for k in nama],
                             columns=["Bahan", "Campuran awal (kg/m³)", "Campuran usulan (kg/m³)", "Perubahan", f"Batch {v:g} m³ (kg)"])
        ui.tampilkan_tabel(tabel)
        if r["pesan"]:
            {"ok": st.success, "waspada": st.warning, "bahaya": st.error}[r["status"]](r["pesan"])
        for cat in r["catatan"]:
            st.info(cat)
