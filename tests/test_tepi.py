"""D2: kasus tepi."""
import pytest

from helpers import halus, kasar
from standards import aci, sni
from standards.admixture import Admixture


def _aci(slump, ukuran=37.5, **kw):
    return aci.hitung_mix_design_aci(30, slump, ukuran, halus(), kasar(), simpangan_baku=5, **kw)


def test_pita_slump_aci():
    for slump, air in ((25, 166), (62.5, 166), (62.6, 181), (125, 181), (125.1, 190), (175, 190)):
        assert _aci(slump).parameter["air_awal"] == air, slump
    for slump in (24.9, 175.1):
        with pytest.raises(ValueError):
            _aci(slump)


def test_pita_slump_sni():
    for slump, kelas in ((0, "0-10"), (10, "0-10"), (10.1, "10-30"), (30, "10-30"), (30.1, "30-60"), (60, "30-60"), (60.1, "60-180"), (180, "60-180")):
        assert sni.kelas_slump(slump) == kelas, slump


def test_ukuran_150_dengan_slump_175_tidak_tersedia():
    with pytest.raises(ValueError):
        _aci(175, ukuran=150.0)


def test_admixture_dengan_dan_tanpa_pertahankan_semen():
    adm = Admixture("Tipe A", 0.55, 8.0, 1.10)
    dasar = _aci(100)
    tetap_fas = _aci(100, admixture=adm, pertahankan_semen=False)
    tetap_semen = _aci(100, admixture=adm, pertahankan_semen=True)
    assert tetap_fas.teoritis.semen < dasar.teoritis.semen
    assert tetap_fas.fas == pytest.approx(dasar.fas, rel=1e-6)
    assert tetap_semen.teoritis.semen == pytest.approx(dasar.teoritis.semen, rel=1e-6)
    assert tetap_semen.fas < dasar.fas
    assert tetap_fas.teoritis.admixture > 0 and tetap_semen.teoritis.admixture > tetap_fas.teoritis.admixture


def test_kadar_air_nol():
    for hasil in (aci.hitung_mix_design_aci(30, 100, 37.5, halus(ka=0.0), kasar(ka=0.0), simpangan_baku=5),
                  sni.hitung_mix_design_sni(30, 100, 40, halus(ka=0.0), kasar(ka=0.0), zona_pasir=2)):
        assert hasil.lapangan.air > hasil.teoritis.air              # agregat kering menyerap air campuran
        assert hasil.lapangan.agregat_halus == pytest.approx(hasil.teoritis.agregat_halus * (1 if hasil.kondisi_teoritis == "kering oven" else 1 - 0.017087), rel=1e-3)
