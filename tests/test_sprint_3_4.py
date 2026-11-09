"""Sprint 3-4: dokumen, proyek JSON, trial mix, gradasi gabungan, tabel digitalisasi, penerimaan, checks."""
import io
import json
import re
import zipfile
from datetime import date
from xml.dom import minidom

import pytest

from helpers import KOP, bundle_uji, lab_uji
from standards import sni, sni_grafik
from utils import checks, gradasi_gabungan, penerimaan, proyek, trialmix
from utils.dokumen import bangun_coa, bangun_laporan
from utils.laporan_docx import buat_docx
from utils.laporan_html import buat_html
from utils.laporan_pdf import buat_pdf


def test_c2_laporan_pdf_word_html():
    lab = lab_uji(); b = bundle_uji(lab, True)
    dok = bangun_laporan(KOP, lab, b)
    assert not dok.draft and buat_pdf(dok)[:5] == b"%PDF-"
    z = zipfile.ZipFile(io.BytesIO(buat_docx(dok)))
    minidom.parseString(z.read("word/document.xml"))                                 # XML valid
    assert any(n.startswith("word/media/") for n in z.namelist())
    assert "Rumus" in "".join(re.findall(r"<w:t[^>]*>([^<]*)</w:t>", z.read("word/document.xml").decode()))
    assert "Kode verifikasi" in buat_html(dok)


def test_c2_draft_bila_proyek_atau_penguji_kosong():
    lab = lab_uji(); b = bundle_uji(lab, True)
    for kosong in ("proyek", "penguji"):
        dok = bangun_laporan({**KOP, kosong: ""}, lab, b)
        assert dok.draft and "DRAFT - data belum lengkap" in dok.pesan_draft and "DRAFT" in buat_html(dok)
        assert bangun_coa({**KOP, kosong: ""}, lab, b).draft
    assert bangun_laporan(KOP, lab, b).kode_verifikasi != bangun_laporan({**KOP, "proyek": ""}, lab, b).kode_verifikasi


def test_c3_proyek_pulih_utuh():
    state = {"v:fc": 35.0, "v:tgl": date(2026, 11, 5), "v:daftar": ["a", "b"], "v:ya": True, "v:stok_jumlah": 9.0, "bukan_input": 1}
    pulih = proyek.impor(proyek.ekspor(state))
    assert pulih == {"fc": 35.0, "tgl": date(2026, 11, 5), "daftar": ["a", "b"], "ya": True}
    for buruk in (b"bukan json", b'{"aplikasi":"lain","data":{}}', json.dumps(dict(aplikasi="MixDesignBeton", versi=99, data={})).encode()):
        with pytest.raises(ValueError):
            proyek.impor(buruk)


def test_c4_trial_mix_menurunkan_fas_bila_kuat_tekan_kurang():
    lab = lab_uji(); b = bundle_uji(lab, True); h = b["hasil"]; t = h.teoritis
    arg = dict(air=t.air, semen=t.semen, halus=t.agregat_halus, kasar=t.agregat_kasar, fas=h.fas, fcr=h.fcr, fc=30, bj_semen=3.15, bj_halus=2.63,
               volume_uji=0.05, slump_target=100, umur=7, kelompok_semen="I/II/V", bentuk_kasar="batu pecah", fas_maks=0.6, semen_min=275)
    r = trialmix.saran_trial_mix(slump_uji=60, f_uji=15.0, **arg)
    assert r["usulan"]["fas"] < r["awal"]["fas"] and r["usulan"]["air"] > r["awal"]["air"] and r["usulan"]["semen"] > r["awal"]["semen"]
    assert r["usulan"]["fas"] == pytest.approx(r["usulan"]["air"] / r["usulan"]["semen"], rel=1e-6)
    ok = trialmix.saran_trial_mix(slump_uji=100, f_uji=None, **arg)                     # tanpa koreksi
    assert ok["usulan"]["semen"] == pytest.approx(t.semen) and ok["rata28"] is None


def test_c5_optimasi_gradasi_gabungan():
    lab = lab_uji()
    r = gradasi_gabungan.optimasi_rasio(lab["fine"]["sieve"]["df"], lab["coarse"]["sieve"]["df"], 37.5, 0.366)
    assert 0.2 <= r["p_halus"] <= 0.7 and r["rmse"] <= r["rmse_desain"] + 1e-9
    assert len(r["sieves"]) == len(r["fuller"]) == len(r["optimal"])


def test_c6_tabel_digitalisasi():
    assert sni_grafik.fas_dari_grafik1(38.2, 37, "I/II/V") == pytest.approx(0.489, abs=0.005)
    assert sni_grafik.fas_dari_grafik1(90, 37, "I/II/V") is None                                # di luar grafik
    lo, hi, luar = sni_grafik.persen_pasir_grafik(40, "60-180", 2, 0.49)
    assert (lo, hi) == (pytest.approx(32.6, abs=0.1), pytest.approx(40.6, abs=0.1)) and not luar
    assert sni_grafik.persen_pasir_grafik(10, "60-180", 2, 0.49) is None
    rho, luar = sni_grafik.berat_isi_grafik16(185, 2508.7)
    assert rho == pytest.approx(2307, abs=2) and not luar
    assert sni_grafik.berat_isi_grafik16(300, 2508.7)[1]


def test_c6_di_luar_grafik_kembali_ke_estimasi_berlabel():
    r = sni.hitung_mix_design_sni(60, 100, 40, lab_uji()["halus"], lab_uji()["kasar"], zona_pasir=2)
    assert r.parameter["sumber_fas"] == "estimasi" and any("di luar jangkauan Grafik 1" in p for p in r.peringatan)


def test_c7_kriteria_penerimaan():
    assert penerimaan.evaluasi_penerimaan([31, 32, 33], 30)["status"] == "DITERIMA"
    assert penerimaan.evaluasi_penerimaan([31, 26.4, 33], 30)["status"] == "TIDAK DITERIMA"          # individu < f'c - 3,5
    assert penerimaan.evaluasi_penerimaan([28, 29, 29.5, 33], 30)["rata3"][0]["lulus"] is False       # rata-rata 3 berurutan < f'c
    assert penerimaan.evaluasi_penerimaan([41, 42, 43], 40)["status"] == "DITERIMA"
    assert penerimaan.evaluasi_penerimaan([41, 35.9, 50], 40)["status"] == "TIDAK DITERIMA"           # f'c > 35: batas 0,90 f'c = 36
    assert penerimaan.evaluasi_penerimaan([35, 36], 30)["status"].startswith("BELUM CUKUP")


def test_b6_checks_tanpa_streamlit():
    import inspect
    assert "streamlit" not in inspect.getsource(checks)
    lab = lab_uji(no200_halus=dict(nilai=5.97, sumber="uji cuci SNI 03-4142"))
    daftar = checks.periksa_mutu(True, bundle_uji(lab, True)["hasil"], bundle_uji(lab, True)["extra"], lab)
    baris = [d for d in daftar if "No. 200 (agregat halus)" in d["parameter"]][0]
    assert baris["tingkat"] == "warn" and "uji cuci" in baris["nilai"]
