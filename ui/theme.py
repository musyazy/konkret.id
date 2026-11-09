"""Tema dark mode (civil engineering dashboard): CSS global untuk kartu, tab, metrik, badge, tabel, dan kop surat.
Tema dasar juga diatur di .streamlit/config.toml; CSS ini memastikan tampilan tetap konsisten."""
import streamlit as st

CSS = """
<style>
:root {--bg:#0F172A; --card:#1E293B; --border:#334155; --text:#E2E8F0; --muted:#94A3B8; --accent:#38BDF8;}
.stApp {background:var(--bg); color:var(--text);}
[data-testid="stHeader"] {background:transparent;}
[data-testid="stSidebar"] {background:#0B1220; border-right:1px solid var(--border);}
.block-container {padding-top:1.2rem; max-width:1500px;}
h1,h2,h3,h4,h5 {color:var(--text); letter-spacing:.01em;}
[data-testid="stCaptionContainer"], .stCaption {color:var(--muted);}

/* kartu = container(border=True) */
[data-testid="stVerticalBlockBorderWrapper"] {background:var(--card); border:1px solid var(--border) !important;
  border-radius:12px; padding:2px 6px;}
[data-testid="stVerticalBlockBorderWrapper"] [data-testid="stVerticalBlockBorderWrapper"] {background:rgba(15,23,42,.45);}

/* metrik */
[data-testid="stMetric"] {background:rgba(15,23,42,.55); border:1px solid var(--border); padding:10px 14px; border-radius:10px;}
[data-testid="stMetricLabel"] {color:var(--muted);}
[data-testid="stMetricValue"] {font-size:1.3rem; color:var(--text);}

/* tab navigasi */
.stTabs [data-baseweb="tab-list"] {gap:4px; border-bottom:1px solid var(--border);}
.stTabs button[data-baseweb="tab"] {font-weight:600; color:var(--muted); background:transparent; border-radius:8px 8px 0 0; padding:8px 16px;}
.stTabs button[data-baseweb="tab"][aria-selected="true"] {color:var(--accent); background:var(--card);}
.stTabs [data-baseweb="tab-highlight"] {background-color:var(--accent);}

/* badge status */
.badge {display:inline-block; padding:2px 10px; border-radius:999px; font-size:.72rem; font-weight:700;
  letter-spacing:.04em; border:1px solid transparent; white-space:nowrap;}
.badge.ok {background:rgba(16,185,129,.15); color:#34D399; border-color:rgba(16,185,129,.45);}
.badge.warn {background:rgba(245,158,11,.15); color:#FBBF24; border-color:rgba(245,158,11,.45);}
.badge.error {background:rgba(239,68,68,.15); color:#F87171; border-color:rgba(239,68,68,.45);}
.badge.info {background:rgba(56,189,248,.15); color:#38BDF8; border-color:rgba(56,189,248,.45);}

/* tabel bersih */
.tbl-wrap {overflow-x:auto; border:1px solid var(--border); border-radius:10px; margin:4px 0 10px 0;}
.tbl {width:100%; border-collapse:collapse; font-size:.85rem;}
.tbl th {background:#0F172A; color:var(--muted); text-align:left; padding:8px 12px; border-bottom:1px solid var(--border); font-weight:600;}
.tbl td {padding:7px 12px; border-bottom:1px solid #263449; color:var(--text);}
.tbl tr:last-child td {border-bottom:none;}
.tbl tr:hover td {background:rgba(56,189,248,.05);}

/* navigasi sidebar */
.nav-judul {font-size:.72rem; font-weight:700; letter-spacing:.12em; text-transform:uppercase; color:var(--muted);
  margin:14px 0 6px 2px;}
[data-testid="stSidebar"] .stButton > button {width:100%; justify-content:flex-start; text-align:left; border-radius:8px;
  padding:.55rem .9rem; font-weight:600;}

/* kop surat */
.kop {background:linear-gradient(90deg,#1E3A8A,#0C4A6E); color:#fff; padding:16px 24px; border-radius:12px 12px 0 0;
  text-align:center; border:1px solid var(--border); border-bottom:3px solid var(--accent);}
.kop .nama {font-size:1.5rem; font-weight:800; letter-spacing:.05em;}
.kop .divisi {font-size:.95rem; font-weight:600; letter-spacing:.07em; margin-top:2px; color:#BAE6FD;}
.kop .alamat {font-size:.78rem; opacity:.85; margin-top:4px;}
.kop-meta {width:100%; border-collapse:collapse; margin-bottom:14px; font-size:.85rem; background:var(--card);
  border:1px solid var(--border);}
.kop-meta td {border:1px solid var(--border); padding:6px 12px; color:var(--text);}
.kop-meta td.k {font-weight:600; width:15%; background:#0F172A; color:var(--muted);}

/* scroll: halaman selalu dapat digulir; roda mouse di atas input tidak mengunci halaman */
html, body {overflow-y: auto !important; height: auto !important; overscroll-behavior-y: auto;}
[data-testid="stApp"], [data-testid="stAppViewContainer"], [data-testid="stMain"], section.main, .main {overflow-y: auto !important; overscroll-behavior-y: auto;}
[data-testid="stMainBlockContainer"], .block-container {overflow: visible !important;}
[data-testid="stNumberInput"] input, [data-testid="stTextInput"] input, [data-testid="stSelectbox"] {overscroll-behavior: auto; touch-action: manipulation;}
input[type=number] {-moz-appearance: textfield; appearance: textfield;}
input[type=number]::-webkit-outer-spin-button, input[type=number]::-webkit-inner-spin-button {-webkit-appearance: none; margin: 0;}
.tbl-wrap {overflow-y: hidden;}
[data-testid="stPlotlyChart"], .js-plotly-plot, .plotly {touch-action: pan-y;}
iframe {overscroll-behavior: auto;}
div.element-container:has(> iframe[height="0"]) {height: 0; margin: 0; padding: 0; overflow: hidden; position: absolute;}

/* mode cetak fisik: latar putih bersih, tanpa sidebar/navigasi */
@media print {
  .stApp, body {background:#fff !important; color:#000 !important;}
  [data-testid="stSidebar"], [data-testid="stHeader"], [data-testid="stToolbar"], .stTabs [data-baseweb="tab-list"],
  .stButton, [data-testid="stDownloadButton"] {display:none !important;}
  [data-testid="stVerticalBlockBorderWrapper"], [data-testid="stMetric"] {background:#fff !important; border:1px solid #bbb !important;}
  h1,h2,h3,h4,h5,p,label,span,td,th {color:#000 !important;}
  .kop {background:#fff !important; color:#000 !important; border:1px solid #000 !important; border-bottom:3px solid #000 !important;}
  .kop .divisi, .kop .alamat {color:#000 !important;}
  .kop-meta td, .kop-meta td.k, .tbl th, .tbl td {background:#fff !important; border-color:#999 !important;}
}
</style>
"""


# Roda mouse pada input angka yang sedang fokus mengubah nilainya dan menahan gulir halaman. Skrip ini melepas fokus
# (blur) saat roda digulir sehingga halaman tetap bergulir dan nilai tidak berubah. <script> tidak dijalankan lewat
# st.markdown, jadi disuntikkan lewat komponen HTML tak terlihat yang mengakses dokumen induk (same-origin).
JS_SCROLL = """
<script>
(function () {
  try {
    var d = window.parent.document;
    if (d.__mdbScrollFix) return;
    d.__mdbScrollFix = true;
    d.addEventListener('wheel', function () {
      var a = d.activeElement;
      if (a && a.tagName === 'INPUT' && a.type === 'number') { a.blur(); }
    }, { passive: true, capture: true });
  } catch (e) { /* dokumen induk tidak dapat diakses: abaikan */ }
})();
</script>
"""


def terapkan_tema() -> None:
    st.markdown(CSS, unsafe_allow_html=True)
    try:
        import streamlit.components.v1 as components
        components.html(JS_SCROLL, height=0)
    except Exception:
        pass
