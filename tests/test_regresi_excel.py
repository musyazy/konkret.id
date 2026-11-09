"""D1: regresi terhadap angka pada file Excel referensi."""
import pytest

from helpers import halus, kasar
from standards import aci, sni
from utils import material_db as mdb, sieve


def test_sni_proporsi_sesuai_excel():
    r = sni.hitung_mix_design_sni(30, 100, 40, halus(), kasar(), fas_manual=0.49, persen_halus_manual=36, berat_isi_beton_manual=2315)
    t = r.teoritis
    assert t.semen == pytest.approx(377.6, abs=0.1)
    assert t.air == pytest.approx(185.0, abs=0.01)
    assert t.agregat_halus == pytest.approx(630.9, abs=0.1)
    assert t.agregat_kasar == pytest.approx(1121.6, abs=0.1)


def test_berat_jenis_pasir():
    assert mdb.bj_agregat_halus(500, 491.6, 652.9, 962.5)["Sd"] == pytest.approx(2.582, abs=0.001)


def test_modulus_kehalusan_pasir():
    d = sieve.data_awal("halus")
    df = sieve.analisa_saringan(d["Saringan (mm)"], d["Massa tertahan (g)"], sieve.CONTOH_PAN_HALUS)
    assert sieve.modulus_kehalusan(df, [9.5] + sieve.FM_HALUS_STANDAR) == pytest.approx(2.7924, abs=0.001)


def test_air_aci_slump100_37_5mm():
    r = aci.hitung_mix_design_aci(24, 100, 37.5, halus(), kasar(), simpangan_baku=0)
    assert r.parameter["air_awal"] == 181


def test_uji_cuci_no200_sesuai_excel():
    rata = (sieve.persen_lolos_cuci(450, 430) + sieve.persen_lolos_cuci(400, 370)) / 2
    assert rata == pytest.approx(5.97, abs=0.01)


def test_digitalisasi_mendekati_pembacaan_excel():
    r = sni.hitung_mix_design_sni(30, 100, 40, halus(), kasar(), zona_pasir=2)
    assert r.fas == pytest.approx(0.49, abs=0.005)                       # Excel: 0,49
    lo, hi = r.parameter["persen_batas"]
    assert lo < 36 < hi                                                    # Excel memakai 36% (pita zona 2)
    assert r.parameter["berat_isi_beton"] == pytest.approx(2315, rel=0.01)  # Excel: 2315 (selisih < 1%)
