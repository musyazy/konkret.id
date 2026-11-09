"""Laporan & CoA: pratinjau putih siap cetak; unduh PDF, Word, HTML, dan data CSV."""
import pandas as pd
import streamlit as st

from ui import components as ui
from ui import inputs
from utils.dokumen import NAMA_TINGKAT, bangun_coa, bangun_laporan
from utils.laporan_docx import buat_docx
from utils.laporan_html import buat_html
from utils.laporan_pdf import buat_pdf

_DOKUMEN = ["Laporan Pengujian & Mix Design", "Sertifikat Mutu (CoA)"]


def _data_csv(bundle) -> bytes:
    """Hasil perhitungan dalam CSV, termasuk label sumber nilai (estimasi / grafik / manual)."""
    h, p, l = bundle["hasil"], bundle["hasil"].parameter, bundle["hasil"].lapangan
    baris = [("Standar", bundle["standar"]), ("f'c (MPa)", bundle["fc"]), ("Bentuk benda uji f'c", bundle.get("bentuk_uji", "silinder")),
             ("f'cr (MPa)", round(h.fcr, 2)), ("FAS efektif", round(h.fas, 3)),
             ("Semen (kg/m3)", round(l.semen, 1)), ("Air lapangan (kg/m3)", round(l.air, 1)),
             ("Pasir lapangan (kg/m3)", round(l.agregat_halus, 1)), ("Kerikil lapangan (kg/m3)", round(l.agregat_kasar, 1))]
    if bundle["modul_sni"]:
        baris += [("FAS - sumber", p["label_fas"]), (f"Persen pasir (%)", f"{p['persen_halus']:.1f} ({p['label_persen']})"),
                  ("Berat isi beton (kg/m3)", f"{p['berat_isi_beton']:.0f} ({p['label_berat']})")]
    baris += [(d["parameter"], f"{d['nilai']} | {NAMA_TINGKAT[d['tingkat']]}") for d in bundle["pemeriksaan"]]
    return pd.DataFrame(baris, columns=["Parameter", "Nilai"]).to_csv(index=False).encode("utf-8")


def tampilkan_tab_laporan(kop, lab, bundle, prediksi, penerimaan=None):
    if lab is None or bundle is None:
        st.info("Lengkapi data agregat dan hitung mix design terlebih dahulu.")
        return
    laporan = bangun_laporan(kop, lab, bundle, prediksi, penerimaan)
    coa = bangun_coa(kop, lab, bundle)
    nama_file = kop["no_dokumen"].replace("/", "-") or "dokumen"

    with st.container(border=True):
        st.markdown("##### 📥 Unduh dokumen resmi")
        kesimpulan = laporan.kesimpulan
        st.markdown("Status mutu: " + ui.badge(kesimpulan[1], kesimpulan[0]), unsafe_allow_html=True)
        if laporan.draft:
            st.warning(laporan.pesan_draft + ". Lengkapi nama proyek dan penguji di sidebar sebelum dokumen diterbitkan.")
        pilihan = inputs.radio("Dokumen", _DOKUMEN, "pratinjau", horizontal=True)
        dok, awalan = (laporan, "Laporan") if pilihan == _DOKUMEN[0] else (coa, "CoA")
        c = st.columns(4)
        c[0].download_button(f"📄 PDF {awalan}", buat_pdf(dok), file_name=f"{awalan}-{nama_file}.pdf", mime="application/pdf", key="dl_pdf")
        c[1].download_button(f"📝 Word {awalan}", buat_docx(dok), file_name=f"{awalan}-{nama_file}.docx",
                             mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document", key="dl_docx")
        c[2].download_button("🖨️ HTML siap cetak (putih)", buat_html(dok).encode("utf-8"), file_name=f"{awalan}-{nama_file}.html", mime="text/html", key="dl_html")
        c[3].download_button("📊 Data hasil (CSV)", _data_csv(bundle), file_name=f"Data-{nama_file}.csv", mime="text/csv", key="dl_csv")
        st.caption("Stempel digital berupa tanda visual dan kode verifikasi isi dokumen; dokumen tetap perlu ditandatangani penguji "
                   "dan penanggung jawab laboratorium.")

    with st.container(border=True):
        st.markdown("##### 🖨️ Pratinjau cetak (latar putih)")
        try:
            import streamlit.components.v1 as components
            components.html(buat_html(dok), height=980, scrolling=True)
        except Exception:
            st.warning("Pratinjau tidak dapat ditampilkan. Gunakan tombol unduh PDF atau HTML.")
