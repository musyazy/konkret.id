"""Navigasi sidebar utama: Pekerjaan Beton dipisah dari Manajemen (Inventory & Biaya)."""
import streamlit as st

MENU_BETON, MENU_INVENTORY, MENU_BIAYA, MENU_ADMIN = "beton", "inventory", "biaya", "admin"


def _pilih(menu: str) -> None:
    st.session_state["menu"] = menu


def _tombol(menu: str, label: str, aktif: str) -> None:
    st.button(label, key=f"nav_{menu}", on_click=_pilih, args=(menu,),
              type="primary" if aktif == menu else "secondary")


def navigasi_sidebar(admin: bool = False, jumlah_permintaan: int = 0) -> str:
    """Render menu sidebar dan kembalikan menu aktif. Menu Admin hanya untuk admin."""
    aktif = st.session_state.get("menu", MENU_BETON)
    if aktif == MENU_ADMIN and not admin:
        aktif = MENU_BETON
    with st.sidebar:
        st.markdown("## 🧱 Mix Design Beton")
        st.markdown('<div class="nav-judul">Pekerjaan Beton</div>', unsafe_allow_html=True)
        _tombol(MENU_BETON, "🏗️ Pekerjaan Beton", aktif)
        st.caption("Mix Design SNI & ACI · Input lab · Prediksi umur dini · Laporan & CoA")
        st.markdown('<div class="nav-judul">Manajemen</div>', unsafe_allow_html=True)
        _tombol(MENU_INVENTORY, "📦 Inventory Stock", aktif)
        _tombol(MENU_BIAYA, "💰 Cost Estimation", aktif)
        if admin:
            st.markdown('<div class="nav-judul">Admin</div>', unsafe_allow_html=True)
            _tombol(MENU_ADMIN, "🛡️ Panel Admin" + (f" ({jumlah_permintaan})" if jumlah_permintaan else ""), aktif)
        st.divider()
    return aktif
