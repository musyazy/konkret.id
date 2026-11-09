"""Tab 5: Cost Estimation - biaya material beton per m³ dan untuk volume pekerjaan."""
import pandas as pd
import streamlit as st

from ui import components as ui
from ui import inputs
from utils import biaya, charts


def ambil_harga() -> dict:
    """Harga & faktor biaya tersimpan (atau nilai contoh) tanpa merender widget."""
    g = lambda k, d: st.session_state.get("v:" + k, d)
    c = biaya.HARGA_CONTOH
    return dict(harga=dict(semen_kg=int(g("h_semen", c["semen_kg"])), pasir_m3=int(g("h_pasir", c["pasir_m3"])), split_m3=int(g("h_split", c["split_m3"])),
                           air_m3=int(g("h_air", c["air_m3"])), admixture_liter=int(g("h_adm", c["admixture_liter"]))),
                susut=float(g("susut", 5.0)), overhead=float(g("overhead", 10.0)), ppn=float(g("ppn", 11.0)))


def biaya_per_m3(komposisi, lab) -> dict:
    """Biaya total per m3 untuk komposisi lapangan, memakai harga tersimpan."""
    f = ambil_harga()
    bi_p = ((lab or {}).get("fine", {}).get("bi_gembur")) or 1400.0
    bi_s = ((lab or {}).get("coarse", {}).get("bi_gembur")) or 1400.0
    return biaya.hitung_biaya(komposisi, bi_p, bi_s, f["harga"], f["susut"], f["overhead"], f["ppn"])


def tampilkan_tab_biaya(bundle=None, lab=None):
    bundle = bundle if bundle is not None else st.session_state.get("_bundle")
    lab = lab if lab is not None else st.session_state.get("_lab")
    st.subheader("💰 Cost Estimation")
    if bundle is None:
        st.info("Buka menu Pekerjaan Beton dan hitung mix design terlebih dahulu.")
        return
    h = bundle["hasil"].lapangan
    st.caption("Kebutuhan material diambil dari hasil mix design (kondisi lapangan). Harga bawaan berupa contoh; sesuaikan dengan harga lokal.")

    with st.container(border=True):
        st.markdown("##### 💰 Harga satuan lokal")
        c = st.columns(5)
        harga = dict(
            semen_kg=inputs.rupiah("Semen (Rp/kg)", "h_semen", biaya.HARGA_CONTOH["semen_kg"], c[0]),
            pasir_m3=inputs.rupiah("Pasir (Rp/m³)", "h_pasir", biaya.HARGA_CONTOH["pasir_m3"], c[1]),
            split_m3=inputs.rupiah("Split (Rp/m³)", "h_split", biaya.HARGA_CONTOH["split_m3"], c[2]),
            air_m3=inputs.rupiah("Air (Rp/m³)", "h_air", biaya.HARGA_CONTOH["air_m3"], c[3]),
            admixture_liter=inputs.rupiah("Admixture (Rp/liter)", "h_adm", biaya.HARGA_CONTOH["admixture_liter"], c[4]))
        st.caption("Ketik angka tanpa desimal, mis. 250000 atau 250.000. Semen Rp 56.000 per sak 40 kg setara Rp 1.400/kg.")
    with st.container(border=True):
        st.markdown("##### 📐 Volume & faktor biaya")
        d = st.columns(4)
        volume = inputs.angka("Volume beton (m³)", 0.01, 1e6, 1.0, 0.5, "vol_biaya", kolom=d[0])
        susut = inputs.angka("Susut / waste material (%)", 0.0, 30.0, 5.0, 0.5, "susut", kolom=d[1])
        overhead = inputs.angka("Overhead & keuntungan (%)", 0.0, 100.0, 10.0, 1.0, "overhead", kolom=d[2])
        ppn = inputs.angka("PPN (%)", 0.0, 25.0, 11.0, 0.5, "ppn", kolom=d[3])

    bi_p = ((lab or {}).get("fine", {}).get("bi_gembur")) or 1400.0
    bi_s = ((lab or {}).get("coarse", {}).get("bi_gembur")) or 1400.0
    r = biaya.hitung_biaya(h, bi_p, bi_s, harga, susut, overhead, ppn)

    with st.container(border=True):
        st.markdown("##### 🧾 Estimasi biaya")
        m = st.columns(4)
        m[0].metric("Biaya material / m³", ui.format_rp(r["subtotal"]))
        m[1].metric("Total / m³ (+overhead, PPN)", ui.format_rp(r["total"]))
        m[2].metric(f"Total untuk {volume:g} m³", ui.format_rp(r["total"] * volume))
        m[3].metric("Rp per m³ per MPa (f'c)", ui.format_rp(r["total"] / bundle["fc"]))

        rinci = r["rincian"].copy()
        tabel = pd.DataFrame({
            "Material": rinci["Material"],
            "Kebutuhan / m³": [f"{q:,.3f} {s}".replace(",", " ") for q, s in zip(rinci["Kebutuhan / m³ beton"], rinci["Satuan"])],
            "Harga satuan": [ui.format_rp(x) for x in rinci["Harga satuan"]],
            "Biaya / m³": [ui.format_rp(x) for x in rinci["Biaya / m³ beton"]],
            f"Biaya {volume:g} m³": [ui.format_rp(x * volume) for x in rinci["Biaya / m³ beton"]],
            "Porsi (%)": rinci["Porsi (%)"].astype(float),
        })
        ui.tampilkan_tabel(tabel, desimal=1)
        ringkas = pd.DataFrame({
            "Komponen": ["Subtotal material", f"Overhead & keuntungan ({overhead:g}%)", f"PPN ({ppn:g}%)", "TOTAL"],
            "Per m³": [ui.format_rp(x) for x in (r["subtotal"], r["overhead"], r["ppn"], r["total"])],
            f"Untuk {volume:g} m³": [ui.format_rp(x * volume) for x in (r["subtotal"], r["overhead"], r["ppn"], r["total"])]})
        ui.tampilkan_tabel(ringkas)

        dasar = bundle.get("hasil_dasar")
        if dasar is not None:
            r0 = biaya.hitung_biaya(dasar.lapangan, bi_p, bi_s, harga, susut, overhead, ppn)
            sel = r["total"] - r0["total"]
            st.info(f"Dibanding campuran ACI tanpa admixture: {'lebih mahal' if sel > 0 else 'lebih hemat'} "
                    f"{ui.format_rp(abs(sel))} per m³ (total {ui.format_rp(r0['total'])} per m³ tanpa admixture).")

    with st.container(border=True):
        st.markdown("##### 🥧 Porsi biaya material")
        fig = charts.grafik_biaya(rinci["Material"], rinci["Biaya / m³ beton"])
        if fig is not None:
            st.plotly_chart(fig)
        else:
            st.bar_chart(pd.DataFrame({"Rp/m³": list(rinci["Biaya / m³ beton"])}, index=list(rinci["Material"])))
        csv = tabel.assign(**{"Standar": bundle["standar"], "f'c (MPa)": bundle["fc"]}).to_csv(index=False).encode("utf-8")
        st.download_button("Unduh estimasi biaya (CSV)", csv, file_name="estimasi_biaya_beton.csv", mime="text/csv")
