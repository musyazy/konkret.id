"""Pembuat grafik (Plotly). Bila Plotly tidak terpasang, fungsi mengembalikan None
dan UI memakai st.line_chart sebagai cadangan."""
from __future__ import annotations

from typing import Dict, List, Optional, Sequence, Tuple

try:
    import plotly.graph_objects as go
    ADA_PLOTLY = True
except ImportError:  # pragma: no cover
    go = None
    ADA_PLOTLY = False

_WARNA = ["#38BDF8", "#34D399", "#FBBF24", "#A78BFA", "#F472B6"]
_LAYOUT = dict(margin=dict(l=10, r=10, t=50, b=10), legend=dict(orientation="h", y=-0.25),
               template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="#1E293B")


def grafik_gradasi(df, spec: Optional[Dict[float, Tuple[float, float]]], nama_spec: str, judul: str):
    """Kurva gradasi hasil uji (% lolos) terhadap batas spesifikasi, sumbu-x log."""
    if not ADA_PLOTLY:
        return None
    fig = go.Figure()
    if spec:
        xs = sorted(spec)
        fig.add_trace(go.Scatter(x=xs, y=[spec[x][1] for x in xs], mode="lines", name="Batas atas",
                                 line=dict(color="#F87171", dash="dash")))
        fig.add_trace(go.Scatter(x=xs, y=[spec[x][0] for x in xs], mode="lines", name=f"Batas bawah ({nama_spec})",
                                 line=dict(color="#F87171", dash="dash"), fill="tonexty",
                                 fillcolor="rgba(248,113,113,0.10)"))
    fig.add_trace(go.Scatter(x=df["Saringan (mm)"], y=df["Lolos (%)"], mode="lines+markers", name="Hasil uji",
                             line=dict(color="#38BDF8", width=3)))
    ticks = sorted(df["Saringan (mm)"])
    fig.update_xaxes(type="log", autorange="reversed", title="Ukuran saringan (mm), skala log",
                     tickvals=ticks, ticktext=[f"{t:g}" for t in ticks])
    fig.update_yaxes(range=[0, 102], title="Persen lolos (%)")
    fig.update_layout(title=judul, hovermode="x unified", **_LAYOUT)
    return fig


def grafik_fas_fcr(kurva: List[Tuple[str, Sequence[float], Sequence[float]]], fcr: float, fas: float, label_titik: str):
    """Hubungan FAS (sumbu-x) terhadap f'cr (sumbu-y). kurva = [(nama, FAS list, f list), ...]."""
    if not ADA_PLOTLY:
        return None
    fig = go.Figure()
    for i, (nama, xs, ys) in enumerate(kurva):
        fig.add_trace(go.Scatter(x=list(xs), y=list(ys), mode="lines+markers", name=nama,
                                 line=dict(color=_WARNA[i % len(_WARNA)])))
    fig.add_trace(go.Scatter(x=[fas], y=[fcr], mode="markers+text", name=label_titik, text=[f"FAS {fas:.3f}"],
                             textposition="top right", marker=dict(symbol="star", size=16, color="#F87171")))
    fig.update_xaxes(title="Faktor air semen (FAS)")
    fig.update_yaxes(title="Kuat tekan rata-rata target f'cr (MPa)")
    fig.update_layout(title="Hubungan FAS terhadap kuat tekan", hovermode="closest", **_LAYOUT)
    return fig


def grafik_prediksi(umur: Sequence[float], kurva: Dict[str, Sequence[float]], titik_uji: Tuple[float, float],
                    f28: Dict[str, float], fc: float, fcr: Optional[float]):
    """Perkembangan kuat tekan terhadap umur untuk tiap metode + titik uji + garis f'c / f'cr."""
    if not ADA_PLOTLY:
        return None
    fig = go.Figure()
    for i, (nama, ys) in enumerate(kurva.items()):
        fig.add_trace(go.Scatter(x=list(umur), y=list(ys), mode="lines", name=nama.split(" (")[0],
                                 line=dict(color=_WARNA[i % len(_WARNA)])))
        fig.add_trace(go.Scatter(x=[28], y=[f28[nama]], mode="markers", showlegend=False,
                                 marker=dict(color=_WARNA[i % len(_WARNA)], size=9)))
    fig.add_trace(go.Scatter(x=[titik_uji[0]], y=[titik_uji[1]], mode="markers", name="Hasil uji",
                             marker=dict(symbol="star", size=16, color="#F87171")))
    fig.add_hline(y=fc, line_dash="dash", annotation_text=f"f'c {fc:g}", line_color="gray")
    if fcr:
        fig.add_hline(y=fcr, line_dash="dot", annotation_text=f"f'cr {fcr:.1f}", line_color="black")
    fig.update_xaxes(title="Umur beton (hari)")
    fig.update_yaxes(title="Kuat tekan (MPa)")
    fig.update_layout(title="Prediksi perkembangan kuat tekan", hovermode="x unified", **_LAYOUT)
    return fig


def grafik_biaya(label: Sequence[str], nilai: Sequence[float]):
    """Porsi biaya material (donat)."""
    if not ADA_PLOTLY:
        return None
    fig = go.Figure(go.Pie(labels=list(label), values=list(nilai), hole=0.55, marker=dict(colors=_WARNA)))
    fig.update_layout(title="Porsi biaya material", **_LAYOUT)
    return fig


def grafik_gabungan(sieves, fuller, optimal, desain, rasio_opt: str, rasio_desain: str):
    """Gradasi gabungan: kurva ideal Fuller, rasio optimal, dan rasio rancangan."""
    if not ADA_PLOTLY:
        return None
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=list(sieves), y=list(fuller), mode="lines", name="Fuller (ideal)", line=dict(color="#F87171", dash="dash")))
    fig.add_trace(go.Scatter(x=list(sieves), y=list(optimal), mode="lines+markers", name=f"Optimal ({rasio_opt})", line=dict(color="#34D399", width=3)))
    if desain is not None:
        fig.add_trace(go.Scatter(x=list(sieves), y=list(desain), mode="lines+markers", name=f"Rancangan ({rasio_desain})", line=dict(color="#38BDF8")))
    fig.update_xaxes(type="log", autorange="reversed", title="Ukuran saringan (mm), skala log", tickvals=list(sieves), ticktext=[f"{t:g}" for t in sieves])
    fig.update_yaxes(range=[0, 102], title="Persen lolos (%)")
    fig.update_layout(title="Gradasi agregat gabungan", hovermode="x unified", **_LAYOUT)
    return fig
