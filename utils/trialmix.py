"""Trial mix: saran koreksi campuran berikutnya dari slump uji dan kuat tekan umur dini.

Langkah: (1) koreksi slump dengan air + semen pada FAS tetap (utils.slump_assistant); (2) prediksi kuat tekan 28 hari dari
umur dini (utils.prediksi) dan FAS yang diperlukan untuk mencapai f'cr; (3) campuran usulan = air hasil langkah 1 dengan FAS
baru (semen = air / FAS), pasir disesuaikan agar volume tetap 1 m3.
"""
from __future__ import annotations

from typing import Dict, List, Optional

from utils import prediksi, slump_assistant as sa


def saran_trial_mix(*, air: float, semen: float, halus: float, kasar: float, fas: float, fcr: float, fc: float,
                    bj_semen: float, bj_halus: float, volume_uji: float, slump_target: float, slump_uji: float,
                    f_uji: Optional[float], umur: int, kelompok_semen: str, bentuk_kasar: str, bentuk_uji: str = "silinder",
                    fas_maks: Optional[float] = None, semen_min: Optional[float] = None, semen_maks: float = 550.0,
                    izinkan_admixture: bool = False, dosis_pct: float = 0.0, air_per_10mm: float = sa.AIR_PER_10MM,
                    slump_per_01pct: float = sa.SLUMP_PER_01PCT) -> Dict:
    catatan: List[str] = []
    # 1. slump
    k = sa.hitung_koreksi_slump(slump_target, slump_uji, air, semen, halus, bj_halus, bj_semen, volume_uji, dosis_pct=dosis_pct,
                                air_per_10mm=air_per_10mm, slump_per_01pct=slump_per_01pct, semen_maks=semen_maks,
                                fas_maks=fas_maks, izinkan_admixture=izinkan_admixture)
    catatan += [c for c in k.catatan if c.startswith(("Opsi", "Jangan", "Standar", "Selisih"))]
    a = k.opsi_air_semen
    w1, c1, h1 = (a["air"], a["semen"], a["halus"]) if a else (air, semen, halus)

    # 2. kuat tekan (dilewati bila f_uji belum diisi)
    fas_sekarang = w1 / c1
    fas_baru = fas_sekarang
    f28, rata28, status, pesan = {}, None, "", ""
    if f_uji:
        f28 = prediksi.prediksi_28_hari(f_uji, umur, kelompok_semen, bentuk_kasar, bentuk_uji)
        rata28 = sum(f28.values()) / len(f28)
        status, pesan = prediksi.evaluasi(rata28, fc, fcr)
        if rata28 < fcr:
            fas_baru = prediksi.fas_diperlukan(fas_sekarang, rata28, fcr)
        elif rata28 > fcr * 1.15:
            fas_baru = prediksi.fas_diperlukan(fas_sekarang, rata28, fcr * 1.05)        # peluang hemat semen
            catatan.append("Kuat tekan prediksi > 115% f'cr: FAS dapat dinaikkan untuk menghemat semen (verifikasi dengan trial mix).")
    if fas_maks is not None and fas_baru > fas_maks:
        catatan.append(f"FAS saran {fas_baru:.3f} melebihi FAS maksimum {fas_maks:g}; dibatasi.")
        fas_baru = fas_maks

    # 3. campuran usulan: air tetap (slump), semen = air / FAS baru, pasir menyesuaikan volume
    c2 = w1 / fas_baru
    if semen_min is not None and c2 < semen_min:
        c2, fas_baru = semen_min, w1 / semen_min
        catatan.append(f"Semen dinaikkan ke minimum {semen_min:g} kg/m3.")
    d_vol = (c2 - c1) / (bj_semen * 1000)
    h2 = h1 - d_vol * 1000 * bj_halus
    if c2 > semen_maks:
        catatan.append(f"Semen usulan {c2:.0f} kg/m3 melebihi {semen_maks:g} kg/m3: pertimbangkan admixture pereduksi air atau mutu agregat lain.")
    if h2 <= 0:
        raise ValueError("Pasir usulan <= 0; koreksi tidak layak.")
    awal = dict(air=air, semen=semen, halus=halus, kasar=kasar, fas=fas)
    usulan = dict(air=w1, semen=c2, halus=h2, kasar=kasar, fas=w1 / c2)
    return dict(slump=k, f28=f28, rata28=rata28, status=status, pesan=pesan, awal=awal, usulan=usulan,
                perubahan={n: usulan[n] - awal[n] for n in awal}, catatan=catatan,
                batch={n: usulan[n] * volume_uji for n in ("air", "semen", "halus", "kasar")})
