"""Sidebar: simpan dan muat proyek (JSON). Memulihkan seluruh isian aplikasi."""
import streamlit as st

from utils import proyek


def _impor():
    """Callback file_uploader: dijalankan SEBELUM skrip, jadi semua widget belum dibuat dan nilainya bisa diganti."""
    berkas = st.session_state.get("w:impor_proyek")
    if berkas is None:
        return
    try:
        data = proyek.impor(berkas.getvalue())
    except ValueError as e:
        st.session_state["_pesan_proyek"] = ("error", str(e))
        return
    for k, v in data.items():
        st.session_state[proyek.AWALAN + k] = v
        st.session_state.pop("w:" + k, None)          # hapus status widget lama agar nilai awal baru dipakai
    st.session_state["_pesan_proyek"] = ("ok", f"Proyek dimuat ({len(data)} isian dipulihkan).")


def sidebar_proyek(nama_berkas: str = "proyek") -> None:
    with st.sidebar.expander("💾 Simpan / muat proyek", expanded=False):
        pesan = st.session_state.pop("_pesan_proyek", None)
        if pesan:
            {"ok": st.success, "error": st.error}[pesan[0]](pesan[1])
        st.download_button("⬇️ Simpan proyek (JSON)", proyek.ekspor(st.session_state), file_name=f"{nama_berkas or 'proyek'}.json",
                           mime="application/json", key="dl_proyek")
        st.file_uploader("⬆️ Muat proyek (JSON)", type=["json"], key="w:impor_proyek", on_change=_impor)
