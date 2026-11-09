"""Mix Design: parameter dasar -> semua nilai standar dihitung otomatis.
SNI = konvensional (tanpa admixture). ACI 211.1 = boleh memakai admixture."""
import dataclasses

import pandas as pd
import streamlit as st

from standards import aci, sni
from standards.admixture import TIPE_ADMIXTURE, Admixture, nilai_awal_tipe
from ui import components as ui
from ui import inputs
from ui.tab_agregat import rekap_lab
from utils import material_db as mdb
from utils.dokumen import NAMA_TINGKAT, bangun_laporan, siapkan_bundle
from utils.laporan_pdf import buat_pdf

_FMT_BENTUK = lambda b: "Alami (sungai/gunung)" if b == "alami" else "Batu pecah (mesin)"


def kartu_dasar(modul):
    """Parameter dasar (dirender di atas tab). Mengembalikan dict."""
    with st.container(border=True):
        st.markdown("##### 🎯 Parameter dasar")
        c = st.columns(4)
        fc = inputs.angka("Kuat tekan rencana f'c (MPa)", 10.0, 80.0, 30.0, 0.5, "fc", kolom=c[0])
        slump = inputs.angka("Slump rencana (mm)", 0.0, 250.0, 100.0, 5.0, "slump", kolom=c[1])
        ukuran_opsi = modul.UKURAN_MAKS_TERSEDIA
        ukuran = inputs.pilih("Ukuran maks. agregat kasar (mm)", ukuran_opsi, f"ukuran_{modul.__name__}",
                              min(2, len(ukuran_opsi) - 1), kolom=c[2])
        semen = inputs.pilih("Jenis semen", list(mdb.JENIS_SEMEN), "jenis_semen", kolom=c[3])
        d = st.columns(4)
        bentuk_h = inputs.radio("Jenis agregat halus", ["alami", "batu pecah"], "bentuk_h", 0, d[0], horizontal=True, format_func=_FMT_BENTUK)
        bentuk_k = inputs.radio("Jenis agregat kasar", ["alami", "batu pecah"], "bentuk_k", 1, d[1], horizontal=True, format_func=_FMT_BENTUK)
        if modul is sni:
            bentuk_uji = inputs.radio("Bentuk benda uji f'c", sni.BENTUK_UJI, "bentuk_uji", 0, d[2], horizontal=True, format_func=str.capitalize)
        else:
            bentuk_uji = "silinder"
            d[2].markdown("**Benda uji f'c**<br>Silinder (ACI)", unsafe_allow_html=True)
        volume_uji = inputs.angka("Volume campuran uji (m³)", 0.001, 10.0, 0.05, 0.005, "volume_uji", "%.3f", d[3])
    return dict(fc=fc, slump=slump, ukuran=ukuran, semen_nama=semen, bentuk_h=bentuk_h, bentuk_k=bentuk_k,
                volume_uji=volume_uji, bentuk_uji=bentuk_uji)


def _kartu_lanjutan(modul, semen_nama):
    """Pengaturan opsional. Mengembalikan (s, extra kwargs untuk fungsi standar)."""
    info = mdb.JENIS_SEMEN[semen_nama]
    with st.container(border=True):
        st.markdown("##### ⚙️ Pengaturan lanjutan (opsional)")
        with st.expander("Buka pengaturan"):
            c = st.columns(3)
            ada_s = inputs.centang("Deviasi standar (s) diketahui", "ada_s", True, c[0])
            s = inputs.angka("Deviasi standar s (MPa)", 0.0, 20.0, 5.0, 0.1, "s", kolom=c[1]) if ada_s else None
            bj_semen = inputs.angka("Berat jenis semen", 2.8, 3.4, float(info["bj"]), 0.01, f"bjs_{semen_nama}", kolom=c[2])
            if not ada_s:
                st.caption("Tanpa data s: SNI memakai margin 12 MPa; ACI memakai tabel nilai tambah ACI 318.")

            if modul is sni:
                lingk = inputs.pilih("Kondisi lingkungan (FAS maksimum & semen minimum)", list(sni.LINGKUNGAN) + ["Manual"], "lingk")
                if lingk == "Manual":
                    e = st.columns(2)
                    semen_min = inputs.angka("Kadar semen minimum (kg/m³)", 200.0, 500.0, 275.0, 5.0, "semen_min", kolom=e[0])
                    fas_maks = inputs.angka("FAS maksimum", 0.20, 1.00, 0.60, 0.01, "fas_maks", kolom=e[1])
                else:
                    semen_min, fas_maks = sni.LINGKUNGAN[lingk]
                    st.caption(f"Semen minimum {semen_min:g} kg/m³ · FAS maksimum {fas_maks:g}")
                umur = inputs.pilih("Umur kuat tekan rencana (hari)", sni.UMUR_TERSEDIA, "umur_rencana", 2)
                st.caption("Isi manual bila ingin mengikuti pembacaan grafik SNI.")
                g = st.columns(3)
                fas_manual = inputs.angka("FAS (Grafik 1)", 0.20, 1.00, 0.49, 0.01, "fas_manual", kolom=g[0]) \
                    if inputs.centang("FAS manual", "chk_fas", False, g[0]) else None
                persen = inputs.angka("Persen pasir % (Grafik 13-15)", 10.0, 90.0, 36.0, 0.5, "persen_manual", kolom=g[1]) \
                    if inputs.centang("Persen pasir manual", "chk_persen", False, g[1]) else None
                berat = inputs.angka("Berat isi beton (Grafik 16)", 2000.0, 2600.0, 2315.0, 5.0, "berat_manual", kolom=g[2]) \
                    if inputs.centang("Berat isi manual", "chk_berat", False, g[2]) else None
                extra = dict(kelompok_semen=info["kelompok"], umur=umur, bj_semen=bj_semen, fas_maks=fas_maks,
                             semen_min=semen_min, fas_manual=fas_manual, persen_halus_manual=persen,
                             berat_isi_beton_manual=berat)
            else:
                e = st.columns(3)
                metode = inputs.radio("Metode berat pasir", ["volume", "massa"], "metode_halus", 0, e[0], horizontal=True,
                                      format_func=lambda m: "Volume absolut" if m == "volume" else "Massa beton")
                ae = inputs.centang("Beton dengan tambahan udara (AE)", "ae", False, e[1])
                paparan = inputs.pilih("Tingkat paparan", aci.PAPARAN, "paparan", kolom=e[2]) if ae else "ringan"
                lingk = inputs.pilih("Kondisi paparan (FAS maksimum, Tabel A1.5.3.4(b))", list(aci.LINGKUNGAN) + ["Manual"], "lingk_aci")
                if lingk == "Manual":
                    fas_maks = inputs.angka("FAS maksimum", 0.20, 1.00, 0.50, 0.01, "fas_maks_aci")
                else:
                    fas_maks = aci.LINGKUNGAN[lingk]
                    st.caption("Tanpa batas FAS khusus." if fas_maks is None else f"FAS maksimum {fas_maks:g}")
                extra = dict(bj_semen=bj_semen, metode_halus=metode, beton_ae=ae, paparan=paparan, fas_maks=fas_maks)
    return s, extra


def _kartu_admixture(modul):
    """Admixture hanya untuk ACI 211.1; SNI konvensional."""
    with st.container(border=True):
        st.markdown("##### 🧴 Bahan tambah kimia (admixture)")
        if modul is sni:
            st.markdown(ui.badge("SNI KONVENSIONAL", "info") + " &nbsp; Standar SNI tidak menggunakan bahan tambah. "
                        "Pilih Standar ACI 211.1 di sidebar untuk memakai admixture.", unsafe_allow_html=True)
            return Admixture(), False
        tipe = inputs.pilih("Jenis admixture", list(TIPE_ADMIXTURE), "adm_tipe")
        awal = nilai_awal_tipe(tipe)
        if awal["kode"] == "-":
            st.caption("Tanpa admixture.")
            return Admixture(), False
        k = awal["kode"]
        merk = inputs.teks("Merek / nama produk (opsional)", f"adm_merk_{k}", "")
        c = st.columns(4)
        dosis = inputs.angka("Dosis (% berat semen)", 0.0, 5.0, awal["dosis_pct"], 0.05, f"adm_dosis_{k}", "%.2f", c[0])
        reduksi = inputs.angka("Reduksi air (%)", 0.0, 40.0, awal["reduksi_air_pct"], 0.5, f"adm_red_{k}", "%.1f", c[1])
        bj = inputs.angka("Berat jenis (kg/liter)", 0.9, 1.5, awal["berat_jenis"], 0.01, f"adm_bj_{k}", "%.2f", c[2])
        air = inputs.angka("Air dalam admixture (%)", 0.0, 100.0, 0.0, 1.0, f"adm_air_{k}", kolom=c[3])
        st.caption("Nilai bawaan berupa perkiraan umum. Sesuaikan dengan datasheet produk atau hasil campuran percobaan.")
        pertahankan = inputs.centang("Pertahankan kadar semen (reduksi air dipakai untuk menurunkan FAS)", "adm_pertahankan", False,
                                     help="Bila tidak dicentang: FAS tetap, sehingga semen ikut turun mengikuti air.")
        return Admixture(f"Tipe {k}" + (f" - {merk}" if merk else ""), dosis, reduksi, bj, air), pertahankan


def zona_dari_spec(nama_spec: str):
    """'Zona 2 (agak kasar)' -> 2"""
    try:
        return int(nama_spec.split()[1])
    except (IndexError, ValueError):
        return None


def _hitung(modul, fc, slump, ukuran, halus, kasar, s, extra, adm, pertahankan, bentuk_uji="silinder", zona=None):
    if modul is sni:   # SNI konvensional: tanpa admixture
        return sni.hitung_mix_design_sni(fc, slump, ukuran, halus, kasar, simpangan_baku=s, bentuk_uji=bentuk_uji,
                                         zona_pasir=zona, **extra)
    return aci.hitung_mix_design_aci(fc, slump, ukuran, halus, kasar, simpangan_baku=s, admixture=adm,
                                     pertahankan_semen=pertahankan, **extra)


_TAG = {"grafik": "Grafik", "grafik1": "Grafik 1", "estimasi": "estimasi", "manual": "manual"}


def _panel_otomatis(modul, hasil):
    p = hasil.parameter
    if modul is sni:
        item = [(f"f'cr target ({p['bentuk_uji']})", f"{hasil.fcr:.1f} MPa"), (f"FAS ({_TAG[p['sumber_fas']]})", f"{hasil.fas:.3f}"),
                ("Air bebas", f"{hasil.teoritis.air:.1f} kg/m³"), ("Udara", f"{p['udara_pct']:g} %"),
                (f"Persen pasir ({_TAG[p['sumber_persen']]})", f"{p['persen_halus']:.1f} %"),
                (f"Berat isi beton ({_TAG[p['sumber_berat']]})", f"{p['berat_isi_beton']:.0f} kg/m³")]
    else:
        item = [("f'cr target (silinder)", f"{hasil.fcr:.1f} MPa"), ("FAS dipakai", f"{hasil.fas:.3f}"),
                ("Air pencampur", f"{hasil.teoritis.air:.1f} kg/m³"), ("Udara", f"{p['udara_pct']:g} %"),
                ("Vol. agregat kasar", f"{p['vol_kasar']:.3f} m³"), ("Massa beton (tabel)", f"{p['massa_beton']:.0f} kg/m³")]
    with st.container(border=True):
        st.markdown("##### 🤖 Nilai yang dihitung otomatis dari standar")
        for col, (k, v) in zip(st.columns(len(item)), item):
            col.metric(k, v)
        if modul is sni:
            st.caption(f"FAS: {p['label_fas']} · Persen pasir: {p['label_persen']}"
                       + (f" (pita {p['persen_batas'][0]:.1f}-{p['persen_batas'][1]:.1f}%)" if p.get("persen_batas") else "")
                       + f" · Berat isi beton: {p['label_berat']} · Bentuk benda uji f'c: {p['bentuk_uji']} (Tabel 2)")


def _tabel_pemeriksaan(daftar):
    return pd.DataFrame([[d["parameter"], d["nilai"], d["batas"], ui.badge(NAMA_TINGKAT[d["tingkat"]], d["tingkat"])] for d in daftar],
                        columns=["Parameter", "Nilai", "Batas", "Status"])


def _tabel_langkah(hasil):
    return pd.DataFrame([[l.uraian, l.nilai, l.satuan, l.sumber, l.rumus, l.substitusi] for l in hasil.langkah],
                        columns=["Uraian", "Nilai", "Satuan", "Tabel / grafik", "Rumus", "Substitusi"]).astype({"Nilai": str})


def tampilkan_tab_mix(modul, lab, kop, dasar):
    """Render tab; mengembalikan bundle hasil (dipakai tab lain dan dokumen) atau None."""
    if lab is None:
        st.info("Lengkapi data pada tab Agregat Halus dan Agregat Kasar terlebih dahulu.")
        return None
    fc, slump, ukuran, semen_nama = dasar["fc"], dasar["slump"], dasar["ukuran"], dasar["semen_nama"]
    volume_uji, bentuk_uji = dasar["volume_uji"], dasar["bentuk_uji"]
    halus = dataclasses.replace(lab["halus"], bentuk=dasar["bentuk_h"])
    kasar = dataclasses.replace(lab["kasar"], bentuk=dasar["bentuk_k"])
    s, extra = _kartu_lanjutan(modul, semen_nama)
    adm, pertahankan = _kartu_admixture(modul)
    zona = zona_dari_spec(lab["sieve_halus"]["spec_nama"])

    try:
        hasil = _hitung(modul, fc, slump, ukuran, halus, kasar, s, extra, adm, pertahankan, bentuk_uji, zona)
        dasar_h = _hitung(modul, fc, slump, ukuran, halus, kasar, s, extra, Admixture(), False, bentuk_uji, zona) \
            if (modul is aci and adm.aktif) else None
    except ValueError as e:
        st.error(f"Input tidak valid: {e}")
        return None

    bundle = dict(hasil=hasil, hasil_dasar=dasar_h, standar=hasil.standar, modul=modul, modul_sni=modul is sni, extra=extra,
                  fc=fc, fcr=hasil.fcr, fas=hasil.fas, slump=slump, ukuran=ukuran, halus=halus, kasar=kasar, adm=adm,
                  bj_semen=extra["bj_semen"], kelompok_semen=mdb.JENIS_SEMEN[semen_nama]["kelompok"], semen_nama=semen_nama,
                  bentuk_kasar=dasar["bentuk_k"], bentuk_uji=bentuk_uji, volume_uji=volume_uji, simpangan_baku=s,
                  bj_halus_dasar=halus.bj_ssd if modul is sni else halus.bj_curah_kering,
                  beton_ae=bool(extra.get("beton_ae", False)), fas_maks=extra.get("fas_maks"))
    siapkan_bundle(bundle, lab)

    _panel_otomatis(modul, hasil)
    lap, t = hasil.lapangan, hasil.teoritis
    with st.container(border=True):
        st.markdown("##### 🧱 Kebutuhan material per 1 m³ beton (kondisi lapangan)")
        cols = st.columns(5 if adm.aktif else 4)
        cols[0].metric("Semen", f"{lap.semen:.1f} kg")
        cols[1].metric("Air (ditambahkan)", f"{lap.air:.1f} kg")
        cols[2].metric(f"Pasir - {halus.nama}", f"{lap.agregat_halus:.1f} kg")
        cols[3].metric(f"Kerikil - {kasar.nama}", f"{lap.agregat_kasar:.1f} kg")
        if adm.aktif:
            cols[4].metric(adm.nama, f"{lap.admixture:.2f} kg", f"{lap.admixture_liter:.2f} liter", delta_color="off")
        bahan = ["Semen", "Air", f"Agregat halus - {halus.nama}", f"Agregat kasar - {kasar.nama}"]
        teor = [t.semen, t.air, t.agregat_halus, t.agregat_kasar]
        lapa = [lap.semen, lap.air, lap.agregat_halus, lap.agregat_kasar]
        if adm.aktif:
            bahan.append(f"Admixture - {adm.nama}")
            teor.append(t.admixture)
            lapa.append(lap.admixture)
        tabel = pd.DataFrame({"Bahan": bahan, f"Teoritis ({hasil.kondisi_teoritis}) kg/m³": teor, "Lapangan kg/m³": lapa,
                              f"Campuran uji {volume_uji:g} m³ (kg)": [x * volume_uji for x in lapa]})
        ui.tampilkan_tabel(tabel)
        st.caption(f"Total massa teoritis {t.total():.0f} kg/m³ · semen : pasir : kerikil = "
                   f"1 : {lap.agregat_halus / lap.semen:.2f} : {lap.agregat_kasar / lap.semen:.2f} · air/semen lapangan {lap.air / lap.semen:.2f}")
        if dasar_h is not None:
            ds, da = dasar_h.lapangan.semen - lap.semen, dasar_h.lapangan.air - lap.air
            st.info(f"Dibanding tanpa admixture: semen {'-' if ds >= 0 else '+'}{abs(ds):.1f} kg/m³, "
                    f"air lapangan {'-' if da >= 0 else '+'}{abs(da):.1f} kg/m³.")

    with st.container(border=True):
        st.markdown("##### ✅ Pemeriksaan mutu & status")
        ui.tampilkan_tabel(_tabel_pemeriksaan(bundle["pemeriksaan"]), kolom_html=["Status"])
    with st.expander("Rincian langkah perhitungan (rumus dan substitusi)"):
        st.dataframe(_tabel_langkah(hasil), hide_index=True)
        if inputs.centang("Tampilkan rumus bentuk LaTeX", "tampil_latex", False):
            for l in hasil.langkah:
                if l.latex:
                    st.caption(f"{l.uraian}  ·  {l.substitusi}  ·  hasil {l.nilai} {l.satuan}")
                    st.latex(l.latex)
    with st.expander("Rekap data uji laboratorium agregat"):
        ui.tampilkan_tabel(rekap_lab(lab), kolom_html=["Agregat halus (pasir)", "Agregat kasar (split/kerikil)"])

    laporan = bangun_laporan(kop, lab, bundle, st.session_state.get("_prediksi"), st.session_state.get("_penerimaan"))
    if laporan.draft:
        st.warning(laporan.pesan_draft)
    st.download_button("📄 Unduh laporan lengkap (PDF)", buat_pdf(laporan), file_name=f"Laporan-{kop['no_dokumen'].replace('/', '-') or 'mix-design'}.pdf",
                       mime="application/pdf", key="dl_laporan_mix")
    return bundle
