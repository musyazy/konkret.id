"""Tab 4: Inventory Stock (Masuk/Keluar) - Semen, Pasir, Split, Admixture. Data tersimpan di data/stok_material.csv."""
import pandas as pd
import streamlit as st

from ui import components as ui
from ui import inputs
from utils import inventory as inv


def _pesan_flash():
    pesan = st.session_state.pop("stok_pesan", None)
    if pesan:
        {"ok": st.success, "error": st.error}[pesan[0]](pesan[1])


def _ringkasan(stok, df):
    sisa, ambang = stok.sisa(df), stok.ambang()
    ikon = {"Semen": "🧱", "Pasir": "🏖️", "Split": "🪨", "Admixture": "🧴"}
    with st.container(border=True):
        st.markdown("##### 📊 Sisa stok saat ini")
        for col, b in zip(st.columns(4), inv.BAHAN):
            label, tingkat = inv.tingkat_stok(sisa[b], ambang[b])
            col.metric(f"{ikon[b]} {b}", f"{sisa[b]:,.1f} kg".replace(",", " "))
            col.markdown(ui.badge(label, tingkat) + f' <span style="color:#94A3B8;font-size:.75rem">min {ambang[b]:g} kg</span>',
                         unsafe_allow_html=True)
        with st.expander("Atur ambang stok minimum (kg)"):
            baru = {}
            for col, b in zip(st.columns(4), inv.BAHAN):
                baru[b] = inputs.angka(b, 0.0, 1e9, float(ambang[b]), 10.0, f"ambang_{b}", kolom=col)
            if st.button("Simpan ambang", key="btn_ambang"):
                try:
                    stok.simpan_ambang(baru)
                    st.session_state["stok_pesan"] = ("ok", "Ambang stok disimpan.")
                    st.rerun()
                except RuntimeError as e:
                    st.error(str(e))
    return sisa


def _kartu_transaksi(stok, lab, bundle):
    bi = {"Pasir": lab["fine"]["bi_gembur"] if lab else 1400.0, "Split": lab["coarse"]["bi_gembur"] if lab else 1400.0}
    bj_adm = bundle["adm"].berat_jenis if bundle else 1.10
    with st.container(border=True):
        st.markdown("##### ✍️ Catat transaksi")
        c = st.columns(4)
        bahan = inputs.pilih("Bahan", inv.BAHAN, "stok_bahan", kolom=c[0])
        jenis = inputs.radio("Jenis", inv.JENIS, "stok_jenis", horizontal=True, kolom=c[1])
        satuan = inputs.pilih("Satuan", inv.SATUAN[bahan], f"stok_satuan_{bahan}", kolom=c[2])
        jumlah = inputs.angka("Jumlah", 0.0, 1e9, 0.0, 1.0, "stok_jumlah", kolom=c[3])
        ket = inputs.teks("Keterangan (supplier / no. nota / proyek)", "stok_ket", "")
        if st.button("Simpan transaksi", type="primary", key="btn_stok"):
            try:
                kg = inv.ke_kg(satuan, jumlah, bi.get(bahan), bj_adm)
                stok.tambah(bahan, jenis, kg, f"{jumlah:g} {satuan}", ket)
                st.session_state["v:stok_jumlah"] = 0.0
                st.session_state["v:stok_ket"] = ""
                st.session_state["stok_pesan"] = ("ok", f"{jenis} {jumlah:g} {satuan} {bahan} tercatat ({kg:,.1f} kg).")
                st.rerun()
            except (ValueError, RuntimeError) as e:
                st.error(str(e))
        if satuan == "m³":
            st.caption(f"Konversi m³ memakai berat isi gembur dari tab uji agregat: {bi[bahan]:.0f} kg/m³.")


def _kartu_pemakaian(stok, bundle, sisa):
    with st.container(border=True):
        st.markdown("##### 🧪 Catat pemakaian campuran uji (dari Mix Design)")
        if bundle is None:
            st.info("Buka menu Pekerjaan Beton dan hitung mix design terlebih dahulu.")
            return
        v, lap = bundle["volume_uji"], bundle["hasil"].lapangan
        butuh = {"Semen": lap.semen * v, "Pasir": lap.agregat_halus * v, "Split": lap.agregat_kasar * v}
        if lap.admixture > 0:
            butuh["Admixture"] = lap.admixture * v
        baris = []
        for b, kg in butuh.items():
            cukup = sisa[b] >= kg - 1e-9
            baris.append([b, kg, sisa[b], ui.badge("CUKUP", "ok") if cukup else ui.badge("KURANG", "error")])
        ui.tampilkan_tabel(pd.DataFrame(baris, columns=["Bahan", f"Kebutuhan {v:g} m³ (kg)", "Sisa stok (kg)", "Status"]),
                           kolom_html=["Status"])
        if st.button("Kurangi stok untuk campuran ini", key="btn_pakai"):
            try:
                stok.tambah_banyak([dict(bahan=b, jenis="Keluar", jumlah_kg=kg, input=f"{kg:.1f} kg",
                                         keterangan=f"Campuran uji {v:g} m³ ({bundle['standar']})") for b, kg in butuh.items()])
                st.session_state["stok_pesan"] = ("ok", "Pemakaian campuran uji dicatat sebagai barang keluar.")
                st.rerun()
            except (ValueError, RuntimeError) as e:
                st.error(str(e))


def _kartu_riwayat(stok, df):
    with st.container(border=True):
        st.markdown("##### 📒 Riwayat transaksi")
        if df.empty:
            st.caption("Belum ada transaksi.")
            return
        pilih = inputs.banyak_pilih("Filter bahan", inv.BAHAN, "stok_filter", default=inv.BAHAN)
        tampil = df[df["Bahan"].isin(pilih)].iloc[::-1].head(300)
        tampil = tampil.assign(Jenis=[ui.badge(j.upper(), "ok" if j == "Masuk" else "warn") for j in tampil["Jenis"]])
        tampil["Keterangan"] = tampil["Keterangan"].astype(str)
        tampil["Input"] = tampil["Input"].astype(str)
        ui.tampilkan_tabel(tampil, kolom_html=["Jenis"], desimal=1)
        c = st.columns([1, 1, 2])
        c[0].download_button("Unduh riwayat (CSV)", df.to_csv(index=False).encode("utf-8"),
                             file_name="stok_material.csv", mime="text/csv")
        if inputs.centang("Konfirmasi hapus transaksi terakhir", "stok_konfirmasi", False, c[1]) and \
                c[1].button("Hapus transaksi terakhir", key="btn_hapus"):
            try:
                stok.hapus_terakhir()
                st.session_state["stok_pesan"] = ("ok", "Transaksi terakhir dihapus.")
                st.rerun()
            except (ValueError, RuntimeError) as e:
                st.error(str(e))


def tampilkan_tab_inventory(bundle=None, lab=None):
    bundle = bundle if bundle is not None else st.session_state.get("_bundle")
    lab = lab if lab is not None else st.session_state.get("_lab")
    st.subheader("📦 Inventory Stock")
    try:
        stok = inv.Stok()
    except (RuntimeError, ValueError) as e:
        st.error(f"Penyimpanan stok tidak dapat dibuka: {e}")
        return
    st.caption("Stok tersimpan otomatis dan diperbarui seketika setiap transaksi. Semua jumlah dalam kg.")
    st.caption(f"Penyimpanan: {stok.label}")
    _pesan_flash()
    try:
        df = stok.muat()
    except Exception as e:  # file rusak / terkunci
        st.error(f"Gagal membaca data stok: {e}")
        return
    sisa = _ringkasan(stok, df)
    kiri, kanan = st.columns(2)
    with kiri:
        _kartu_transaksi(stok, lab, bundle)
    with kanan:
        _kartu_pemakaian(stok, bundle, sisa)
    _kartu_riwayat(stok, df)
