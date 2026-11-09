"""Panel Admin: tinjau permintaan akses, setujui/tolak, kelola pengguna yang disetujui."""
import pandas as pd
import streamlit as st

from ui import components as ui
from utils import auth

_KUNCI_ADMIN_OK = "admin_ok"
_KUNCI_GAGAL = "admin_gagal"
_MAKS_GAGAL = 5


def _pesan_flash():
    p = st.session_state.pop("admin_pesan", None)
    if p:
        {"ok": st.success, "error": st.error, "info": st.info}[p[0]](p[1])


def _gerbang_sandi() -> bool:
    """Mode email tidak memverifikasi pemilik email: Panel Admin wajib sandi. Mode google: email terverifikasi sudah cukup."""
    if auth.mode_auth() != "email" or st.session_state.get(_KUNCI_ADMIN_OK):
        return True
    with st.container(border=True):
        st.markdown("##### 🔑 Verifikasi admin")
        if not auth.sandi_admin_terkonfigurasi():
            st.error("Panel Admin dinonaktifkan pada mode email sampai sandi admin diatur: isi variabel lingkungan MIXDESIGN_ADMIN_PASSWORD "
                     "(atau MIXDESIGN_ADMIN_PASSWORD_SHA256), atau gunakan MIXDESIGN_AUTH_MODE=google.")
            return False
        if st.session_state.get(_KUNCI_GAGAL, 0) >= _MAKS_GAGAL:
            st.error("Terlalu banyak percobaan sandi. Muat ulang halaman.")
            return False
        st.caption("Email Anda terdaftar sebagai admin. Masukkan sandi admin untuk membuka panel.")
        with st.form("form_admin"):
            sandi = st.text_input("Sandi admin", type="password", key="admin_pw")
            buka = st.form_submit_button("Buka Panel Admin", type="primary")
        if buka:
            if auth.verifikasi_sandi_admin(sandi):
                st.session_state[_KUNCI_ADMIN_OK] = True
                st.session_state.pop(_KUNCI_GAGAL, None)
                st.rerun()
            st.session_state[_KUNCI_GAGAL] = st.session_state.get(_KUNCI_GAGAL, 0) + 1
            auth.catat_akses("(admin)", "sandi_admin_salah")
            st.error("Sandi salah.")
    return False


def _aksi(fungsi, *args, sukses: str):
    try:
        ok = fungsi(*args)
        st.session_state["admin_pesan"] = ("ok", sukses) if ok else ("info", "Tidak ada perubahan.")
    except RuntimeError as e:
        st.session_state["admin_pesan"] = ("error", str(e))
    st.rerun()


def tampilkan_panel_admin(email_admin: str) -> None:
    st.subheader("🛡️ Panel Admin")
    if not auth.adalah_admin(email_admin):                     # pengaman: halaman ini hanya untuk admin
        st.error("Halaman ini hanya untuk admin.")
        return
    if not _gerbang_sandi():
        return
    _pesan_flash()
    permintaan, disetujui = auth.daftar_permintaan(), auth.daftar_disetujui()
    with st.container(border=True):
        m = st.columns(3)
        m[0].metric("Permintaan menunggu", str(len(permintaan)))
        m[1].metric("Pengguna disetujui", str(len(disetujui)))
        m[2].metric("Whitelist total", str(len(auth.muat_daftar_izin())))

    with st.container(border=True):
        st.markdown("##### 📨 Permintaan akses")
        if not permintaan:
            st.caption("Tidak ada permintaan yang menunggu.")
        for d in permintaan:
            email = d.get("email", "")
            c = st.columns([3, 3, 2, 1, 1])
            c[0].markdown(f"`{email}`")
            c[1].caption(d.get("keterangan") or "-")
            c[2].caption(d.get("diminta", "").replace("T", " "))
            if c[3].button("Setujui", key=f"setujui_{email}", type="primary"):
                _aksi(auth.setujui, email, email_admin, sukses=f"{email} disetujui dan ditambahkan ke whitelist.")
            if c[4].button("Tolak", key=f"tolak_{email}"):
                _aksi(auth.tolak, email, email_admin, sukses=f"Permintaan {email} ditolak.")

    with st.container(border=True):
        st.markdown("##### ✅ Pengguna yang disetujui admin")
        if not disetujui:
            st.caption("Belum ada.")
        for d in disetujui:
            email = d.get("email", "")
            c = st.columns([3, 3, 2, 1])
            c[0].markdown(f"`{email}`")
            c[1].caption(f"disetujui oleh {d.get('oleh', '-')}")
            c[2].caption(d.get("disetujui", "").replace("T", " "))
            if c[3].button("Cabut", key=f"cabut_{email}"):
                _aksi(auth.cabut, email, email_admin, sukses=f"Akses {email} dicabut.")

    with st.container(border=True):
        st.markdown("##### ➕ Tambah email langsung")
        with st.form("form_tambah"):
            baru = st.text_input("Alamat Gmail", key="admin_tambah", placeholder="nama@gmail.com")
            tambah = st.form_submit_button("Tambahkan ke whitelist")
        if tambah:
            hasil = auth.tambah_manual(baru, email_admin)
            st.session_state["admin_pesan"] = ("ok" if hasil.status == "dicatat" else "error" if hasil.status in ("tidak_valid", "gagal") else "info", hasil.pesan)
            st.rerun()

    with st.expander("Whitelist statis (dari file/variabel lingkungan) dan admin"):
        statis = auth.muat_daftar_izin() - {kanon for kanon in (auth.kanonik_gmail(d.get("email", "")) for d in disetujui) if kanon}
        ui.tampilkan_tabel(pd.DataFrame({"Email": sorted(statis), "Peran": ["admin" if e in auth.muat_admin() else "whitelist statis" for e in sorted(statis)]}))
        st.caption("Daftar ini diatur pembuat di utils/auth.py, MIXDESIGN_EMAIL_IZIN, atau data/email_izin.txt dan tidak diubah dari panel.")
