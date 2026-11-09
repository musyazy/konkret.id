"""Data uji bersama: agregat contoh dan pembangun lab/bundle tanpa Streamlit."""
from datetime import date

from standards import aci, sni
from standards.admixture import Admixture
from utils import material_db as mdb, sieve
from utils.checks import tingkat_dari_deviasi
from utils.dokumen import siapkan_bundle

KOP = dict(perusahaan="PT. CIPTA KARYA UTAMA", divisi="LABORATORIUM BAHAN BANGUNAN & STRUKTUR", alamat="Jl. Contoh No. 1",
           no_dokumen="LAB/MD/001/2026", proyek="Gedung Serbaguna", klien="Dinas PUPR", tanggal=date(2026, 11, 5), penguji="Andi Pratama",
           penanggung_jawab="Ir. Budi Santoso, M.T.", jabatan_pj="Manajer Teknis Laboratorium")


def halus(ka=5.4, bentuk="alami", **kw):
    return mdb.Agregat("Pasir", "halus", 2.5819327731092425, 1.7087062652563011, ka, modulus_kehalusan=2.792407270776041, bentuk=bentuk, **kw)


def kasar(ka=2.0, bentuk="batu pecah", berat_isi=1450.2384436314014):
    return mdb.Agregat("Split", "kasar", 2.3500958874920097, 2.8289056124761822, ka, berat_isi=berat_isi, bentuk=bentuk)


def sieve_dict(jenis, no200=None):
    halus_ = jenis == "halus"
    d = sieve.data_awal(jenis)
    pan = sieve.CONTOH_PAN_HALUS if halus_ else sieve.CONTOH_PAN_KASAR
    df = sieve.analisa_saringan(d["Saringan (mm)"], d["Massa tertahan (g)"], pan)
    if halus_:
        mk = sieve.modulus_kehalusan(df, [9.5] + sieve.FM_HALUS_STANDAR)
        nama, _ = sieve.evaluasi_zona(df)
        spec, abaikan = sieve.SPEC_HALUS[nama], (9.5,)
    else:
        mk = sieve.modulus_kehalusan(df, sieve.FM_KASAR_STANDAR)
        nama = "No. 57 (25 - 4,75 mm)"
        spec, abaikan = sieve.SPEC_KASAR[nama], ()
    cek, lulus = sieve.cek_spesifikasi(df, spec, abaikan)
    nc = cek[~cek["Saringan (mm)"].isin(abaikan)]
    level = tingkat_dari_deviasi(float(nc["Deviasi (%)"].max()))
    return dict(df=df, mk=mk, spec_nama=nama, spec=spec, lulus=lulus, tabel_cek=cek, level=level,
                level_mk=("ok" if 2.3 <= mk <= 3.1 else "warn") if halus_ else "info", pan=pan, no200=no200)


def lab_uji(no200_halus=None, no200_kasar=None):
    def ag(jenis, nama, sd, sw, ka, no200):
        return dict(jenis=jenis, nama=nama, tanggal=date(2026, 11, 5), sd=sd, ss=sd * (1 + sw / 100), sa=None, sw=sw, ka=ka, bi_gembur=1323.8,
                    bi_padat=1450.2, rongga_gembur=45.0, rongga_padat=38.2, sieve=sieve_dict(jenis, no200))
    f = ag("halus", "Pasir Merapi", 2.582, 1.709, 5.4, no200_halus)
    c = ag("kasar", "Split lokal", 2.350, 2.829, 2.0, no200_kasar)
    return dict(halus=halus(), kasar=kasar(), sieve_halus=f["sieve"], sieve_kasar=c["sieve"], fine=f, coarse=c)


def bundle_uji(lab, sni_=True, **kw):
    H, K = lab["halus"], lab["kasar"]
    if sni_:
        extra = dict(kelompok_semen="I/II/V", umur=28, bj_semen=3.15, fas_maks=0.60, semen_min=275.0, fas_manual=None,
                     persen_halus_manual=None, berat_isi_beton_manual=None)
        hasil = sni.hitung_mix_design_sni(30, 100, 40, H, K, simpangan_baku=5.0, zona_pasir=2, **extra)
        adm, ukuran, modul = Admixture(), 40, sni
    else:
        extra = dict(bj_semen=3.15, metode_halus="volume", beton_ae=False, paparan="ringan", fas_maks=None)
        adm, ukuran, modul = Admixture("Tipe F", 1.2, 20.0, 1.10), 19.0, aci
        hasil = aci.hitung_mix_design_aci(30, 100, 19.0, H, K, simpangan_baku=5.0, admixture=adm, **extra)
    b = dict(hasil=hasil, hasil_dasar=None, standar=hasil.standar, modul=modul, modul_sni=sni_, extra=extra, fc=30.0, fcr=hasil.fcr, fas=hasil.fas,
             slump=100.0, ukuran=ukuran, halus=H, kasar=K, adm=adm, bj_semen=3.15, kelompok_semen="I/II/V", semen_nama="Tipe I / PC biasa (OPC)",
             bentuk_kasar="batu pecah", bentuk_uji="silinder", volume_uji=0.05, bj_halus_dasar=2.6, beton_ae=False, fas_maks=extra.get("fas_maks"))
    b.update(kw)
    return siapkan_bundle(b, lab)
