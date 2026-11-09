"""Gerbang login: pengguna harus diizinkan pembuat sebelum aplikasi tampil. Pengguna yang ditolak dapat mengirim
permintaan akses; tombol keluar di sidebar."""
import os

import streamlit as st

from utils import auth

_KUNCI_EMAIL = "auth_email"
_KUNCI_GAGAL = "auth_gagal"
_KUNCI_DITOLAK = "auth_ditolak"        # (email baku, pesan) setelah percobaan masuk ditolak
_KUNCI_MINTA = "auth_minta"            # jumlah permintaan akses dari sesi ini
MAKS_PERMINTAAN_SESI = 3


def _kartu_masuk():
    _, tengah, _ = st.columns([1, 1.4, 1])
    return tengah


def auth_provider():
    return os.environ.get("MIXDESIGN_AUTH_PROVIDER") or None


def _bagian_minta_akses(email: str) -> None:
    """Form permintaan akses untuk email yang ditolak. Permintaan dicatat di data/pending_requests.json."""
    st.markdown(f"**Belum punya izin?** Kirim permintaan akses untuk `{email}`; admin akan meninjaunya.")
    with st.form("form_minta"):
        keterangan = st.text_input("Nama / keterangan (opsional)", key="minta_ket", max_chars=80, placeholder="mis. nama dan instansi")
        kirim = st.form_submit_button("Kirim Permintaan Akses")
    if not kirim:
        return
    if st.session_state.get(_KUNCI_MINTA, 0) >= MAKS_PERMINTAAN_SESI:
        st.error("Terlalu banyak permintaan dari sesi ini. Hubungi pembuat aplikasi.")
        return
    st.session_state[_KUNCI_MINTA] = st.session_state.get(_KUNCI_MINTA, 0) + 1
    hasil = auth.ajukan_permintaan(email, keterangan)
    if hasil.status in ("dicatat", "sudah_diajukan"):
        st.success(hasil.pesan)
    elif hasil.status == "sudah_diizinkan":
        st.session_state.pop(_KUNCI_DITOLAK, None)
        st.success(hasil.pesan)
    else:
        st.error(hasil.pesan)


def _gerbang_email() -> str:
    if st.session_state.get(_KUNCI_EMAIL):
        return st.session_state[_KUNCI_EMAIL]
    with _kartu_masuk():
        with st.container(border=True):
            st.markdown("### 🔐 Masuk")
            st.caption("Aplikasi ini dibatasi. Masukkan alamat Gmail yang telah diizinkan pembuat aplikasi.")
            if st.session_state.get(_KUNCI_GAGAL, 0) >= auth.MAKS_PERCOBAAN:
                st.error("Terlalu banyak percobaan gagal. Muat ulang halaman untuk mencoba lagi atau hubungi pembuat aplikasi.")
                st.stop()
            with st.form("form_login"):
                email = st.text_input("Alamat Gmail", key="login_email", placeholder="nama@gmail.com")
                kirim = st.form_submit_button("Masuk", type="primary")
            if kirim:
                hasil = auth.periksa_akses(email)
                auth.catat_akses(email, hasil.status)
                if hasil.status == "diizinkan":
                    for k in (_KUNCI_DITOLAK, _KUNCI_GAGAL):
                        st.session_state.pop(k, None)
                    st.session_state[_KUNCI_EMAIL] = hasil.email
                    st.rerun()
                st.session_state[_KUNCI_GAGAL] = st.session_state.get(_KUNCI_GAGAL, 0) + 1
                if hasil.status == "ditolak":
                    st.session_state[_KUNCI_DITOLAK] = (hasil.email, hasil.pesan)
                else:
                    st.session_state.pop(_KUNCI_DITOLAK, None)
                    st.error(hasil.pesan)
            ditolak = st.session_state.get(_KUNCI_DITOLAK)
            if ditolak:
                st.warning(ditolak[1])
                _bagian_minta_akses(ditolak[0])
    st.stop()


def _gerbang_google() -> str:
    if not hasattr(st, "login") or not hasattr(st, "user"):
        with _kartu_masuk():
            st.error("Mode login Google membutuhkan Streamlit 1.42 atau lebih baru (pip install \"streamlit[auth]>=1.42\") "
                     "dan konfigurasi [auth] pada .streamlit/secrets.toml. Atau gunakan MIXDESIGN_AUTH_MODE=email.")
        st.stop()
    if not getattr(st.user, "is_logged_in", False):
        with _kartu_masuk():
            with st.container(border=True):
                st.markdown("### 🔐 Masuk")
                st.caption("Masuk dengan akun Google. Hanya email yang diizinkan pembuat aplikasi yang dapat memakai aplikasi ini.")
                if st.button("Masuk dengan Google", type="primary", key="btn_login_google"):
                    provider = auth_provider()
                    st.login(provider) if provider else st.login()
        st.stop()
    email = st.user.get("email", "")
    diverifikasi = bool(st.user.get("email_verified", True))
    hasil = auth.periksa_akses(email, terverifikasi=diverifikasi)
    if hasil.status != "diizinkan" or not diverifikasi:
        auth.catat_akses(email, "ditolak" if diverifikasi else "email_belum_terverifikasi")
        with _kartu_masuk():
            with st.container(border=True):
                st.warning(hasil.pesan if diverifikasi else "Akses ditolak. Email Google Anda belum terverifikasi.")
                if diverifikasi and hasil.email:                   # email terverifikasi Google: boleh meminta akses
                    _bagian_minta_akses(hasil.email)
                st.button("Keluar", on_click=st.logout, key="btn_logout_ditolak")
        st.stop()
    return hasil.email


def gerbang_login() -> str:
    """Panggil di awal app.py. Mengembalikan email pengguna yang diizinkan; menghentikan skrip bila belum masuk / ditolak."""
    mode = auth.mode_auth()
    if mode == "off":
        return "(autentikasi nonaktif)"
    return _gerbang_google() if mode == "google" else _gerbang_email()


def _keluar():
    if auth.mode_auth() == "google" and hasattr(st, "logout"):
        st.logout()
    for k in list(st.session_state.keys()):         # bersihkan seluruh isian agar tidak terbaca pengguna berikutnya
        try:
            del st.session_state[k]
        except Exception:                            # kunci widget yang sedang diproses callback
            pass


def tombol_logout(email: str) -> None:
    """Info pengguna dan tombol keluar di sidebar (tidak tampil bila autentikasi nonaktif)."""
    if auth.mode_auth() == "off":
        return
    with st.sidebar:
        st.divider()
        st.caption(f"👤 Masuk sebagai **{email}**" + (" · admin" if auth.adalah_admin(email) else ""))
        st.button("🚪 Keluar", key="btn_logout", on_click=_keluar)
