"""Sprint 1-2: bentuk benda uji, berat isi kerikil, kalibrasi FAS, label estimasi, gradasi kerikil, uji cuci, slump, rumus."""
import pytest

from helpers import halus, kasar
from standards import aci, sni
from utils import checks, sieve


def test_a1_bentuk_benda_uji_mengubah_fas_dan_tampil():
    sil = sni.hitung_mix_design_sni(30, 100, 40, halus(), kasar(), zona_pasir=2, bentuk_uji="silinder")
    kub = sni.hitung_mix_design_sni(30, 100, 40, halus(), kasar(), zona_pasir=2, bentuk_uji="kubus")
    assert kub.fas != pytest.approx(sil.fas, abs=0.01)
    assert kub.parameter["bentuk_uji"] == "kubus" and kub.parameter["f0"] == 45
    assert any("kubus" in l.sumber for l in kub.langkah)


def test_a1_tabel_2_kubus_sesuai_excel():
    t = sni.TABEL_2["kubus"]
    assert t["I/II/V"]["alami"] == {3: 20, 7: 28, 28: 40, 91: 48} and t["I/II/V"]["batu pecah"] == {3: 25, 7: 32, 28: 45, 91: 54}
    assert t["III"]["alami"] == {3: 25, 7: 31, 28: 46, 91: 53} and t["III"]["batu pecah"] == {3: 30, 7: 40, 28: 53, 91: 60}


def test_a2_aci_menolak_bila_berat_isi_kerikil_kosong():
    with pytest.raises(ValueError) as e:
        aci.hitung_mix_design_aci(30, 100, 37.5, halus(), kasar(berat_isi=None), simpangan_baku=5)
    assert "Berat isi agregat kasar belum diisi" in str(e.value)


def test_a3_peringatan_kalibrasi_fas():
    r50 = sni.hitung_mix_design_sni(50, 100, 40, halus(), kasar(), gunakan_tabel=False)
    assert any("kalibrasi" in p for p in r50.peringatan)
    r20 = sni.hitung_mix_design_sni(20, 100, 40, halus(), kasar(), gunakan_tabel=False)      # f'cr 28,2 MPa, FAS 0,60: masih dalam rentang
    assert not any("kalibrasi" in p for p in r20.peringatan)
    r_luar = sni.hitung_mix_design_sni(70, 100, 40, halus(), kasar(), gunakan_tabel=False)
    assert sum("kalibrasi" in p for p in r_luar.peringatan) == 2                               # f'cr dan FAS keduanya di luar rentang


def test_a4_label_estimasi_dan_grafik():
    est = sni.hitung_mix_design_sni(30, 100, 40, halus(), kasar(), gunakan_tabel=False).parameter
    assert est["label_persen"] == sni.LABEL_EST_PERSEN and est["label_berat"] == sni.LABEL_EST_BERAT
    tab = sni.hitung_mix_design_sni(30, 100, 40, halus(), kasar(), zona_pasir=2).parameter
    assert "Grafik 15" in tab["label_persen"] and "Grafik 16" in tab["label_berat"] and tab["sumber_fas"] == "grafik1"
    man = sni.hitung_mix_design_sni(30, 100, 40, halus(), kasar(), fas_manual=0.49, persen_halus_manual=36, berat_isi_beton_manual=2315).parameter
    assert man["sumber_persen"] == man["sumber_berat"] == man["sumber_fas"] == "manual"


def test_a4_ukuran_10mm_tetap_estimasi():
    p = sni.hitung_mix_design_sni(30, 100, 10, halus(), kasar(), zona_pasir=2).parameter        # Grafik 13 tidak tersedia
    assert p["sumber_persen"] == "estimasi" and p["label_persen"] == sni.LABEL_EST_PERSEN


def test_a5_gradasi_kerikil_mengikuti_ukuran_maks():
    assert sieve.spec_kasar_untuk_ukuran(40) == ("No. 467 (37,5 - 4,75 mm)", True)
    assert sieve.spec_kasar_untuk_ukuran(19) == ("No. 67 (19 - 4,75 mm)", True)
    assert sieve.spec_kasar_untuk_ukuran(25)[0].startswith("No. 57")
    assert sieve.spec_kasar_untuk_ukuran(75)[1] is False
    assert all(n in sieve.SPEC_KASAR for n, _ in map(sieve.spec_kasar_untuk_ukuran, (10, 12.5, 20, 37.5, 50)))


def test_a6_no200_memakai_uji_cuci():
    cuci = dict(nilai=5.97, sumber="uji cuci SNI 03-4142")
    nilai, sumber = checks.lolos_no200(dict(df=None, no200=cuci))
    assert nilai == 5.97 and "uji cuci" in sumber
    assert checks.tingkat_no200(5.97, "halus") == "warn" and checks.tingkat_no200(4.9, "halus") == "ok" and checks.tingkat_no200(1.2, "kasar") == "warn"
    pesan = sieve.validasi_saringan(sieve.analisa_saringan([4.75, 2.36, 0.15], [10, 20, 30], 5), 5, True, 2.8, cuci)
    assert any("uji cuci SNI 03-4142" in p and "5,0" not in p for p in pesan) or any("5.97" in p for p in pesan)


def test_a7_slump_di_luar_rentang_aci():
    for slump in (0, 250):
        with pytest.raises(ValueError) as e:
            aci.hitung_mix_design_aci(30, slump, 37.5, halus(), kasar(), simpangan_baku=5)
        assert "25-175" in str(e.value)


def test_b1_selisih_metode_massa_vs_volume():
    r = aci.hitung_mix_design_aci(30, 100, 37.5, halus(), kasar(), simpangan_baku=5)
    assert r.parameter["selisih_metode_pct"] > 5
    assert any("metode massa" in p and "volume" in p for p in r.peringatan)


def test_b3_setiap_langkah_punya_rumus_dan_substitusi():
    for r in (sni.hitung_mix_design_sni(30, 100, 40, halus(), kasar(), zona_pasir=2),
              sni.hitung_mix_design_sni(30, 100, 40, halus(), kasar(), gunakan_tabel=False),
              aci.hitung_mix_design_aci(30, 100, 37.5, halus(), kasar(), simpangan_baku=5)):
        assert r.langkah and all(l.rumus and l.substitusi and l.latex for l in r.langkah), [l.uraian for l in r.langkah if not (l.rumus and l.substitusi)]


def test_b4_lingkungan_aci_mengisi_fas_maks():
    assert aci.LINGKUNGAN["Tanpa paparan khusus"] is None
    r = aci.hitung_mix_design_aci(20, 100, 37.5, halus(), kasar(), simpangan_baku=5, fas_maks=aci.LINGKUNGAN["Air laut / sulfat - penampang tipis"])
    assert r.fas <= 0.40 + 1e-9
