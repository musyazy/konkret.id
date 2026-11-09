"""Input Lab: Agregat Halus / Agregat Kasar - kartu data mentah pengujian + analisa saringan."""
import html
from datetime import date

import pandas as pd
import streamlit as st

from ui import components as ui
from ui import inputs
from utils import charts, material_db as mdb, sieve
from utils.checks import tingkat_dari_deviasi

_BI_AWAL = dict(wadah=2.7493, volume=7.1200015730822977e-3, gembur=(12.2, 12.15), padat=(13.15, 13.0))
_TOLERANSI_MK = (2.3, 3.1)
_NAMA = {"ok": "PASS", "warn": "WARNING", "error": "ERROR", "info": "INFO"}


def _num(label, nilai, key, langkah=0.1, fmt="%.2f", maks=100000.0, kolom=None):
    return inputs.angka(label, 0.0, maks, float(nilai), langkah, key, fmt, kolom)


def _kartu_identitas(jenis):
    with st.container(border=True):
        st.markdown("##### 🪪 Identitas sampel")
        c = st.columns(3)
        sumber = mdb.SUMBER_PASIR if jenis == "halus" else mdb.SUMBER_KASAR
        pilihan = inputs.pilih("Sumber / nama agregat", sumber, f"sumber_{jenis}", kolom=c[0])
        nama = inputs.teks("Nama sumber agregat", f"nama_{jenis}", "", kolom=c[1], placeholder="mis. Pasir Kali Putih") \
            if pilihan == mdb.LAINNYA else pilihan
        tanggal = inputs.tanggal("Tanggal pengujian", f"tgl_{jenis}", date.today(), kolom=c[2])
        mentah = inputs.radio("Sumber data uji", ["Data mentah pengujian", "Hasil akhir"], f"mode_{jenis}", horizontal=True) == "Data mentah pengujian"
    return nama or "(tanpa nama)", tanggal, mentah


def _kartu_berat_jenis(jenis, awal, mentah):
    with st.container(border=True):
        st.markdown("##### ⚖️ Berat jenis (SSD) & penyerapan air")
        if mentah:
            if jenis == "halus":
                st.caption("SNI 1970:2016 - metode piknometer")
                c = st.columns(4)
                S = _num("SSD, S (g)", 500.0, "S_h", kolom=c[0])
                A = _num("Kering oven, A (g)", 491.6, "A_h", kolom=c[1])
                B = _num("Piknometer + air, B (g)", 652.9, "B_h", kolom=c[2])
                C = _num("Piknometer + sampel + air, C (g)", 962.5, "C_h", kolom=c[3])
                if S < A:
                    raise ValueError("Berat SSD (S) tidak boleh lebih kecil dari berat kering oven (A).")
                if B + S - C <= 0:
                    raise ValueError("B + S - C harus > 0; periksa penimbangan piknometer.")
                r = mdb.bj_agregat_halus(S, A, B, C)
            else:
                st.caption("SNI 1969:2016")
                c = st.columns(3)
                A = _num("Kering oven, A (g)", 1102.9, "A_k", kolom=c[0])
                B = _num("SSD, B (g)", 1134.1, "B_k", kolom=c[1])
                C = _num("Dalam air, C (g)", 664.8, "C_k", kolom=c[2])
                if B < A:
                    raise ValueError("Berat SSD (B) tidak boleh lebih kecil dari berat kering oven (A).")
                if B - C <= 0 or A - C <= 0:
                    raise ValueError("B - C dan A - C harus > 0; periksa berat dalam air.")
                r = mdb.bj_agregat_kasar(A, B, C)
            sd, ss, sa, sw = r["Sd"], r["Ss"], r["Sa"], r["Sw"]
        else:
            c = st.columns(2)
            sd = inputs.angka("Berat jenis curah kering (Sd)", 1.0, 4.0, awal["bj_curah_kering"], 0.001, f"sd_{jenis}", "%.3f", c[0])
            sw = inputs.angka("Penyerapan air (%)", 0.0, 20.0, awal["penyerapan_pct"], 0.001, f"sw_{jenis}", "%.3f", c[1])
            ss, sa = sd * (1 + sw / 100), None
        m = st.columns(4)
        m[0].metric("BJ curah kering (Sd)", f"{sd:.3f}")
        m[1].metric("BJ curah SSD (Ss)", f"{ss:.3f}")
        m[2].metric("BJ semu (Sa)", "-" if sa is None else f"{sa:.3f}")
        m[3].metric("Penyerapan (%)", f"{sw:.3f}")
        wajar = 2.0 <= sd <= 3.2 and sw <= 10
        st.markdown(ui.badge("Nilai wajar" if wajar else "Periksa data", "ok" if wajar else "warn"), unsafe_allow_html=True)
    return sd, ss, sa, sw


def _kartu_kadar_air(jenis, awal, mentah):
    with st.container(border=True):
        st.markdown("##### 💧 Kadar air (kondisi lapangan)")
        if mentah:
            c = st.columns(2)
            wb = _num("Berat contoh basah (g)", 500.0, f"wb_{jenis}", kolom=c[0])
            wk = _num("Berat contoh kering oven (g)", 474.4 if jenis == "halus" else 490.2, f"wk_{jenis}", kolom=c[1])
            if wk <= 0 or wb < wk:
                raise ValueError("Berat basah harus >= berat kering oven (> 0).")
            ka = mdb.kadar_air(wb, wk)
        else:
            ka = inputs.angka("Kadar air lapangan (%)", 0.0, 30.0, awal["kadar_air_pct"], 0.1, f"ka_{jenis}", "%.2f")
        st.metric("Kadar air", f"{ka:.2f} %")
    return ka


def _kartu_berat_isi(jenis, awal, mentah, sd):
    """Berat isi (SNI 03-4804-1998). Kerikil tanpa nilai awal: kolom kosong 'isi data lab'; nilai None bila belum lengkap."""
    kosong = jenis == "kasar"
    with st.container(border=True):
        st.markdown("##### 📦 Berat isi (SNI 03-4804-1998)")
        if kosong:
            st.caption("Isi data lab. Perhitungan ACI dan estimasi persen pasir SNI membutuhkan berat isi padat kerikil.")
        if mentah:
            c = st.columns(2)
            T = _num("Berat wadah (kg)", 0.0 if kosong else _BI_AWAL["wadah"], f"T_{jenis}", 0.001, "%.4f", kolom=c[0])
            V = _num("Volume wadah (m³)", 0.0 if kosong else _BI_AWAL["volume"], f"V_{jenis}", 0.0001, "%.6f", kolom=c[1])
            g = st.columns(2)
            gembur = [_num(f"Wadah + gembur, uji {i + 1} (kg)", 0.0 if kosong else _BI_AWAL["gembur"][i], f"g{i}_{jenis}", 0.01, kolom=g[i]) for i in range(2)]
            p = st.columns(2)
            padat = [_num(f"Wadah + padat, uji {i + 1} (kg)", 0.0 if kosong else _BI_AWAL["padat"][i], f"p{i}_{jenis}", 0.01, kolom=p[i]) for i in range(2)]
            lengkap = V > 0 and all(x > T for x in gembur + padat)
            if V > 0 and any(0 < x <= T for x in gembur + padat):
                raise ValueError("Berat wadah + agregat harus lebih besar dari berat wadah.")
            bi_g = sum(mdb.berat_isi(x, T, V) for x in gembur) / 2 if lengkap else None
            bi_p = sum(mdb.berat_isi(x, T, V) for x in padat) / 2 if lengkap else None
        else:
            c = st.columns(2)
            bi_g = inputs.angka("Berat isi gembur (kg/m³)", 0.0, 2200.0, 0.0 if kosong else 1323.8, 1.0, f"big_{jenis}", "%.1f", c[0])
            bi_p = inputs.angka("Berat isi padat (kg/m³)", 0.0, 2200.0, 0.0 if kosong else awal.get("berat_isi", 1450.2), 1.0, f"bip_{jenis}", "%.1f", c[1])
            bi_g, bi_p = (bi_g or None), (bi_p or None)
        rg = mdb.rongga_udara(bi_g, sd) if bi_g else None
        rp = mdb.rongga_udara(bi_p, sd) if bi_p else None
        m = st.columns(4)
        fmt = lambda v, u: "isi data lab" if v is None else f"{v:.1f} {u}"
        m[0].metric("Berat isi gembur", fmt(bi_g, "kg/m³"))
        m[1].metric("Berat isi padat", fmt(bi_p, "kg/m³"))
        m[2].metric("Rongga gembur", fmt(rg, "%"))
        m[3].metric("Rongga padat", fmt(rp, "%"))
        if bi_p is None:
            st.markdown(ui.badge("ISI DATA LAB", "warn"), unsafe_allow_html=True)
        elif bi_g is not None and bi_g >= bi_p:
            st.markdown(ui.badge("Gembur ≥ padat: periksa data", "warn"), unsafe_allow_html=True)
    return bi_g, bi_p, rg, rp


def _input_saringan(jenis, halus):
    saringan = sieve.SARINGAN_HALUS if halus else sieve.SARINGAN_KASAR
    contoh = sieve.CONTOH_MASSA_HALUS if halus else sieve.CONTOH_MASSA_KASAR
    st.caption("Massa tertahan pada tiap saringan (gram):")
    kol, massa = st.columns(4), []
    for i, s in enumerate(saringan):
        massa.append(_num(f"{s:g} mm ({sieve.LABEL_SARINGAN.get(s, '')})", contoh.get(s, 0.0), f"sv_{jenis}_{s}", 0.1, "%.1f", kolom=kol[i % 4]))
    return pd.DataFrame({"Saringan (mm)": saringan, "Massa tertahan (g)": massa})


def _kartu_cuci(jenis):
    """Uji cuci lolos No. 200 (SNI 03-4142-1996): dua pengujian W1 (awal) dan W2 (setelah dicuci)."""
    st.markdown("**Uji cuci lolos saringan No. 200** (SNI 03-4142-1996)")
    kosong = jenis == "kasar"
    awal = [(450.0, 430.0), (400.0, 370.0)]
    kol, hasil = st.columns(4), []
    for i in range(2):
        w1 = _num(f"W1 uji {i + 1}: berat awal (g)", 0.0 if kosong else awal[i][0], f"w1_{jenis}_{i}", 1.0, "%.1f", kolom=kol[2 * i])
        w2 = _num(f"W2 uji {i + 1}: setelah cuci (g)", 0.0 if kosong else awal[i][1], f"w2_{jenis}_{i}", 1.0, "%.1f", kolom=kol[2 * i + 1])
        if w1 > 0:
            try:
                hasil.append(sieve.persen_lolos_cuci(w1, w2))
            except ValueError as e:
                st.error(f"Uji {i + 1}: {e}")
    if not hasil:
        st.caption("Isi data uji cuci. Sebelum diisi, kadar lolos No. 200 tidak dinilai.")
        return None
    nilai = sum(hasil) / len(hasil)
    st.metric("Lolos No. 200 (rata-rata)", f"{nilai:.2f} %")
    return dict(nilai=nilai, sumber="uji cuci SNI 03-4142", uji=hasil)


def _kartu_saringan(jenis, ukuran_maks=None):
    """Kartu analisa saringan. Mengembalikan dict atau None."""
    halus = jenis == "halus"
    with st.container(border=True):
        st.markdown("##### 🔬 Analisa saringan (SNI ASTM C136-2012)")
        df_in = _input_saringan(jenis, halus)
        c = st.columns(2)
        pan = _num("Massa di pan (g)", sieve.CONTOH_PAN_HALUS if halus else sieve.CONTOH_PAN_KASAR, f"pan_{jenis}", kolom=c[0])
        awal = _num("Massa awal benda uji (g), opsional", 0.0, f"awal_{jenis}", 1.0, kolom=c[1])
        try:
            df = sieve.analisa_saringan(df_in["Saringan (mm)"], df_in["Massa tertahan (g)"], pan)
        except ValueError as e:
            st.error(str(e))
            return None
        pesan = []
        if (msg := sieve.cek_massa(df, pan, awal)):
            pesan.append(msg)
        no200 = _kartu_cuci(jenis)

        if halus:
            incl = inputs.centang("Sertakan saringan 9,5 mm dalam perhitungan MK", "mk_incl_95", True,
                                  help="SNI ASTM C136 menghitung MK dari saringan No. 4 sampai No. 100.")
            mk = sieve.modulus_kehalusan(df, ([9.5] if incl else []) + sieve.FM_HALUS_STANDAR)
            zona, _ = sieve.evaluasi_zona(df)
            spec_nama = inputs.pilih("Zona gradasi acuan (SNI)", list(sieve.SPEC_HALUS), "spec_halus", list(sieve.SPEC_HALUS).index(zona))
            spec, abaikan = sieve.SPEC_HALUS[spec_nama], (9.5,)
            st.caption("Saringan 9,5 mm: ikut dalam MK bila kotak dicentang, tetapi tidak menentukan lulus atau tidaknya zona "
                       "(batas 100% pada 9,5 mm hanya acuan; butiran tertahan di sini ditandai INFO).")
        else:
            mk = sieve.modulus_kehalusan(df, sieve.FM_KASAR_STANDAR)
            otomatis = "Otomatis (sesuai ukuran maks)"
            pilihan = inputs.pilih("Batas gradasi acuan (ASTM C33)", [otomatis] + list(sieve.SPEC_KASAR), "spec_kasar")
            if pilihan == otomatis:
                spec_nama, tepat = sieve.spec_kasar_untuk_ukuran(ukuran_maks or 40)
                st.caption(f"Acuan otomatis untuk ukuran maks {ukuran_maks:g} mm: {spec_nama}." if ukuran_maks else f"Acuan otomatis: {spec_nama}.")
                if not tepat:
                    pesan.append(f"Ukuran maks {ukuran_maks:g} mm tidak punya gradasi tunggal ASTM C33; dipakai {spec_nama}. Pilih acuan manual bila perlu.")
            else:
                spec_nama = pilihan
            spec, abaikan = sieve.SPEC_KASAR[spec_nama], ()

        pesan += sieve.validasi_saringan(df, pan, halus, mk, no200)
        cek, lulus = sieve.cek_spesifikasi(df, spec, abaikan)
        nilai_cek = cek[~cek["Saringan (mm)"].isin(abaikan)]
        level = tingkat_dari_deviasi(float(nilai_cek["Deviasi (%)"].max()) if len(nilai_cek) else 0.0)
        if halus:
            lvl_mk = "ok" if _TOLERANSI_MK[0] <= mk <= _TOLERANSI_MK[1] else (
                "warn" if _TOLERANSI_MK[0] - 0.2 <= mk <= _TOLERANSI_MK[1] + 0.2 else "error")
        else:
            lvl_mk = "info"

        m = st.columns(4)
        m[0].metric("Modulus kehalusan (MK)", f"{mk:.3f}")
        m[1].metric("Total massa benda uji", f"{df['Massa tertahan (g)'].sum() + pan:.1f} g")
        with m[2]:
            st.caption("Status MK")
            st.markdown(ui.badge(f"{_NAMA[lvl_mk]} · MK {mk:.2f}" if halus else "INFO · tanpa batas SNI", lvl_mk), unsafe_allow_html=True)
        with m[3]:
            st.caption("Status gradasi")
            st.markdown(ui.badge(_NAMA[level], level), unsafe_allow_html=True)

        tampil = df.copy()
        tampil.insert(1, "Saringan", [sieve.LABEL_SARINGAN.get(x, "") for x in tampil["Saringan (mm)"]])
        ui.tampilkan_tabel(tampil)

        fig = charts.grafik_gradasi(df, spec, spec_nama, "Kurva gradasi" + (" agregat halus" if halus else " agregat kasar"))
        if fig is not None:
            st.plotly_chart(fig)
        else:
            data = pd.DataFrame({"Hasil uji": df.set_index("Saringan (mm)")["Lolos (%)"]})
            data["Batas bawah"] = pd.Series({k: v[0] for k, v in spec.items()})
            data["Batas atas"] = pd.Series({k: v[1] for k, v in spec.items()})
            st.line_chart(data.sort_index())

        with st.expander("Pengecekan per saringan terhadap batas spesifikasi"):
            tabel = cek.copy()
            tabel["Status"] = [ui.badge("TIDAK DIUJI", "info") if s == "tidak diuji"
                               else ui.badge(_NAMA[tingkat_dari_deviasi(d)], tingkat_dari_deviasi(d)) for s, d in zip(cek["Status"], cek["Deviasi (%)"])]
            ui.tampilkan_tabel(tabel.drop(columns=["Deviasi (%)"]), kolom_html=["Status"])
            st.caption("PASS: dalam batas · WARNING: di luar batas hingga 5 poin persen · ERROR: lebih dari 5 poin.")
        for m_ in pesan:
            st.warning(m_)
    return dict(df=df, mk=mk, spec_nama=spec_nama, spec=spec, lulus=lulus, tabel_cek=cek, level=level, level_mk=lvl_mk, pan=pan, no200=no200)


def tampilkan_tab_agregat(jenis: str, ukuran_maks=None):
    """Render tab pengujian satu agregat. Mengembalikan dict hasil atau None bila input tidak valid."""
    awal = mdb.nilai_awal(jenis)
    st.caption("Nilai awal berupa contoh data. Ganti dengan hasil pengujian laboratorium Anda.")
    nama, tanggal, mentah = _kartu_identitas(jenis)
    try:
        sd, ss, sa, sw = _kartu_berat_jenis(jenis, awal, mentah)
        ka = _kartu_kadar_air(jenis, awal, mentah)
        bi_g, bi_p, rg, rp = _kartu_berat_isi(jenis, awal, mentah, sd)
    except (ZeroDivisionError, ValueError) as e:
        st.error(f"Data mentah tidak valid: {e}")
        return None
    sv = _kartu_saringan(jenis, ukuran_maks)
    if sv is None:
        return None
    return dict(jenis=jenis, nama=nama, tanggal=tanggal, sd=sd, ss=ss, sa=sa, sw=sw, ka=ka,
                bi_gembur=bi_g, bi_padat=bi_p, rongga_gembur=rg, rongga_padat=rp, sieve=sv)


def gabung_lab(fine, coarse):
    """Gabungkan hasil dua tab menjadi data lab untuk perhitungan. None bila salah satu belum valid."""
    if fine is None or coarse is None:
        return None
    halus = mdb.Agregat(fine["nama"], "halus", fine["sd"], fine["sw"], fine["ka"], berat_isi=fine["bi_padat"],
                        modulus_kehalusan=fine["sieve"]["mk"], bentuk="alami")
    kasar = mdb.Agregat(coarse["nama"], "kasar", coarse["sd"], coarse["sw"], coarse["ka"], berat_isi=coarse["bi_padat"],
                        modulus_kehalusan=coarse["sieve"]["mk"], bentuk="batu pecah")
    return dict(halus=halus, kasar=kasar, sieve_halus=fine["sieve"], sieve_kasar=coarse["sieve"], fine=fine, coarse=coarse)


def rekap_lab(lab) -> pd.DataFrame:
    """Tabel rekap data uji kedua agregat dengan badge. Semua sel sudah di-escape: tampilkan dengan kolom_html."""
    f, c = lab["fine"], lab["coarse"]
    n = lambda v, d=3: "-" if v is None else f"{v:.{d}f}"
    bd = lambda lvl: ui.badge(_NAMA[lvl], lvl)
    baris = [
        ("Nama / sumber agregat", html.escape(f["nama"]), html.escape(c["nama"])),
        ("Berat jenis curah kering (Sd)", n(f["sd"]), n(c["sd"])),
        ("Berat jenis curah SSD (Ss)", n(f["ss"]), n(c["ss"])),
        ("Berat jenis semu (Sa)", n(f["sa"]), n(c["sa"])),
        ("Penyerapan air (%)", n(f["sw"]), n(c["sw"])),
        ("Kadar air (%)", n(f["ka"], 2), n(c["ka"], 2)),
        ("Berat isi gembur (kg/m³)", n(f["bi_gembur"], 1), n(c["bi_gembur"], 1)),
        ("Berat isi padat (kg/m³)", n(f["bi_padat"], 1), n(c["bi_padat"], 1)),
        ("Rongga udara padat (%)", n(f["rongga_padat"], 1), n(c["rongga_padat"], 1)),
        ("Modulus kehalusan (MK)", n(f["sieve"]["mk"]), n(c["sieve"]["mk"])),
        ("Lolos No. 200, uji cuci (%)", n((f["sieve"]["no200"] or {}).get("nilai"), 2), n((c["sieve"]["no200"] or {}).get("nilai"), 2)),
        ("Acuan gradasi", html.escape(f["sieve"]["spec_nama"]), html.escape(c["sieve"]["spec_nama"])),
        ("Status MK", bd(f["sieve"]["level_mk"]), bd(c["sieve"]["level_mk"])),
        ("Status gradasi", bd(f["sieve"]["level"]), bd(c["sieve"]["level"])),
    ]
    return pd.DataFrame(baris, columns=["Pengujian", "Agregat halus (pasir)", "Agregat kasar (split/kerikil)"])
