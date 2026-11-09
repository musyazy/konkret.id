"""Model dokumen resmi (Laporan Pengujian & Mix Design, Sertifikat Mutu/CoA) yang netral terhadap format.
Dirender ke PDF (laporan_pdf.py) dan HTML siap cetak (laporan_html.py) dari model yang sama."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import date
from typing import List, Optional, Tuple

from utils import sieve as sv
from utils.format_id import angka, tanggal_id
from utils.checks import periksa_mutu, tingkat_dari_deviasi, tingkat_keseluruhan

NAMA_TINGKAT = {"ok": "PASS", "warn": "WARNING", "error": "ERROR", "info": "INFO"}
STATUS_KATA = set(NAMA_TINGKAT.values())


@dataclass
class Tabel:
    kolom: List[str]
    baris: List[List[str]]
    judul: str = ""
    lebar: Optional[List[float]] = None          # proporsi lebar kolom
    rata_kanan: Tuple[int, ...] = ()             # indeks kolom bernilai angka


@dataclass
class Grafik:
    judul: str
    titik: List[Tuple[float, float]]             # (saringan mm, % lolos)
    batas_bawah: List[Tuple[float, float]] = field(default_factory=list)
    batas_atas: List[Tuple[float, float]] = field(default_factory=list)
    keterangan: str = ""


@dataclass
class Seksi:
    judul: str
    paragraf: List[str] = field(default_factory=list)
    tabel: List[Tabel] = field(default_factory=list)
    grafik: Optional[Grafik] = None


@dataclass
class Dokumen:
    jenis: str                                    # "laporan" | "coa"
    judul: str
    subjudul: str
    nomor: str
    kop: dict
    meta: List[Tuple[str, str]]
    seksi: List[Seksi]
    kesimpulan: Optional[Tuple[str, str, str]] = None   # (tingkat, label, teks)
    catatan: List[str] = field(default_factory=list)
    penandatangan: List[Tuple[str, str, str]] = field(default_factory=list)   # (peran, nama, jabatan)
    kode_verifikasi: str = ""
    dicetak: str = ""
    draft: bool = False
    pesan_draft: str = ""


# ----------------------------------------------------------------------------- pembantu
def _kode(dok: Dokumen) -> str:
    inti = dict(jenis=dok.jenis, nomor=dok.nomor, meta=dok.meta, dicetak=dok.dicetak,
                draft=dok.draft,
                seksi=[(s.judul, s.paragraf, [(t.kolom, t.baris) for t in s.tabel],
                        s.grafik.titik if s.grafik else None) for s in dok.seksi], kesimpulan=dok.kesimpulan)
    h = hashlib.sha256(json.dumps(inti, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")).hexdigest().upper()
    return f"{h[:4]}-{h[4:8]}-{h[8:12]}"


def _meta(kop: dict, bundle: dict, nomor: str) -> List[Tuple[str, str]]:
    return [("No. Dokumen", nomor), ("Tanggal Pengujian", tanggal_id(kop["tanggal"])),
            ("Proyek", kop["proyek"] or "-"), ("Klien", kop["klien"] or "-"),
            ("Standar Perhitungan", bundle["standar"]), ("Tanggal Cetak", tanggal_id(date.today()))]


def _penandatangan(kop: dict):
    return [("Penguji", kop["penguji"], "Teknisi Laboratorium"),
            ("Penanggung Jawab Laboratorium", kop["penanggung_jawab"], kop["jabatan_pj"])]


def _tabel_agregat(lab: dict) -> Tabel:
    f, c = lab["fine"], lab["coarse"]
    n = lambda v, d=3: "-" if v is None else angka(v, d)
    st_ = lambda lv: NAMA_TINGKAT[lv]
    baris = [
        ["Sumber / nama agregat", f["nama"], c["nama"]],
        ["Tanggal pengujian", tanggal_id(f["tanggal"]), tanggal_id(c["tanggal"])],
        ["Berat jenis curah kering (Sd)", n(f["sd"]), n(c["sd"])],
        ["Berat jenis curah SSD (Ss)", n(f["ss"]), n(c["ss"])],
        ["Berat jenis semu (Sa)", n(f["sa"]), n(c["sa"])],
        ["Penyerapan air (%)", n(f["sw"]), n(c["sw"])],
        ["Kadar air (%)", n(f["ka"], 2), n(c["ka"], 2)],
        ["Berat isi gembur (kg/m³)", n(f["bi_gembur"], 1), n(c["bi_gembur"], 1)],
        ["Berat isi padat (kg/m³)", n(f["bi_padat"], 1), n(c["bi_padat"], 1)],
        ["Rongga udara padat (%)", n(f["rongga_padat"], 1), n(c["rongga_padat"], 1)],
        ["Modulus kehalusan (MK)", n(f["sieve"]["mk"]), n(c["sieve"]["mk"])],
        ["Lolos No. 200, uji cuci SNI 03-4142 (%)", n((f["sieve"].get("no200") or {}).get("nilai"), 2), n((c["sieve"].get("no200") or {}).get("nilai"), 2)],
        ["Acuan gradasi", f["sieve"]["spec_nama"], c["sieve"]["spec_nama"]],
        ["Status gradasi", st_(f["sieve"]["level"]), st_(c["sieve"]["level"])],
    ]
    return Tabel(["Pengujian", "Agregat Halus (Pasir)", "Agregat Kasar (Split/Kerikil)"], baris,
                 lebar=[3.2, 2.4, 2.4], rata_kanan=(1, 2))


def _tabel_saringan(hasil: dict, halus: bool) -> Tabel:
    sv_ = hasil["sieve"]
    df, spec, cek = sv_["df"], sv_["spec"], sv_["tabel_cek"].set_index("Saringan (mm)")
    abaikan = (9.5,) if halus else ()
    pan = float(hasil["sieve"].get("pan", 0.0))
    total = float(df["Massa tertahan (g)"].sum()) + pan
    baris = []
    for _, r in df.iterrows():
        s = float(r["Saringan (mm)"])
        bawah, atas = spec.get(s, (None, None))
        if s in cek.index and s not in abaikan:
            row = cek.loc[s]
            status = "-" if row["Status"] == "tidak diuji" else NAMA_TINGKAT[tingkat_dari_deviasi(float(row["Deviasi (%)"]))]
        else:
            status = "INFO" if (s in abaikan and bawah is not None) else "-"
        baris.append([f"{s:g}", sv.LABEL_SARINGAN.get(s, ""), angka(r["Massa tertahan (g)"], 1), angka(r["Tertahan (%)"], 2),
                      angka(r["Tertahan kumulatif (%)"], 2), angka(r["Lolos (%)"], 2),
                      "-" if bawah is None else angka(bawah, 0), "-" if atas is None else angka(atas, 0), status])
    baris.append(["Pan", "", angka(pan, 1), angka(pan / total * 100 if total else 0, 2), "100,00", "0,00", "-", "-", "-"])
    baris.append(["Total", "", angka(total, 1), "", "", "", "", "", ""])
    return Tabel(["Saringan (mm)", "No.", "Massa Tertahan (g)", "Tertahan (%)", "Kumulatif Tertahan (%)", "Lolos (%)",
                  "Batas Bawah (%)", "Batas Atas (%)", "Status"], baris,
                 lebar=[1.1, 1.0, 1.4, 1.2, 1.5, 1.1, 1.2, 1.2, 1.1], rata_kanan=(0, 2, 3, 4, 5, 6, 7))


def _grafik(hasil: dict, judul: str) -> Grafik:
    sv_ = hasil["sieve"]
    df, spec = sv_["df"], sv_["spec"]
    return Grafik(judul, [(float(a), float(b)) for a, b in zip(df["Saringan (mm)"], df["Lolos (%)"])],
                  [(s, spec[s][0]) for s in sorted(spec)], [(s, spec[s][1]) for s in sorted(spec)],
                  keterangan=f"Batas acuan: {sv_['spec_nama']}")


def _tabel_material(bundle: dict) -> Tabel:
    h, v = bundle["hasil"], bundle["volume_uji"]
    t, l = h.teoritis, h.lapangan
    baris = [["Semen", angka(t.semen, 1), angka(l.semen, 1), angka(l.semen * v, 2)],
             ["Air", angka(t.air, 1), angka(l.air, 1), angka(l.air * v, 2)],
             [f"Agregat halus - {bundle['halus'].nama}", angka(t.agregat_halus, 1), angka(l.agregat_halus, 1), angka(l.agregat_halus * v, 2)],
             [f"Agregat kasar - {bundle['kasar'].nama}", angka(t.agregat_kasar, 1), angka(l.agregat_kasar, 1), angka(l.agregat_kasar * v, 2)]]
    if l.admixture > 0:
        baris.append([f"Admixture - {bundle['adm'].nama}", angka(t.admixture, 2), angka(l.admixture, 2), angka(l.admixture * v, 3)])
    baris.append(["Total", angka(t.total(), 1), angka(l.total(), 1), angka(l.total() * v, 2)])
    return Tabel(["Bahan", f"Teoritis ({h.kondisi_teoritis}) kg/m³", "Lapangan kg/m³", f"Campuran uji {angka(v, 3)} m³ (kg)"],
                 baris, lebar=[3.4, 1.7, 1.5, 1.8], rata_kanan=(1, 2, 3))


def _tabel_parameter(bundle: dict) -> Tabel:
    h, p = bundle["hasil"], bundle["hasil"].parameter
    sni_ = bundle["modul_sni"]
    baris = [["Standar perhitungan", bundle["standar"]],
             ["Kuat tekan rencana f'c", f"{angka(bundle['fc'], 1)} MPa ({bundle.get('bentuk_uji', 'silinder')})"],
             ["Kuat tekan rata-rata target f'cr", f"{angka(h.fcr, 2)} MPa"]]
    if sni_:
        baris.append(["Bentuk benda uji f'c (Tabel 2 SNI)", bundle.get("bentuk_uji", "silinder").capitalize()])
    baris += [["Slump rencana", f"{angka(bundle['slump'], 0)} mm"],
              ["Ukuran maksimum agregat kasar", f"{bundle['ukuran']:g} mm"],
              ["Jenis semen", bundle["semen_nama"]],
              ["Jenis agregat halus / kasar", f"{bundle['halus'].bentuk} / {bundle['kasar'].bentuk}"],
              ["Faktor air semen (FAS) efektif", angka(h.fas, 3) + (f" ({p['label_fas']})" if sni_ else "")],
              ["Air bebas", f"{angka(h.teoritis.air, 1)} kg/m³"],
              ["Kadar udara", f"{angka(p['udara_pct'], 1)} %"]]
    if sni_:
        pita = f"; pita {angka(p['persen_batas'][0], 1)}-{angka(p['persen_batas'][1], 1)} %" if p.get("persen_batas") else ""
        baris += [["Persen agregat halus", f"{angka(p['persen_halus'], 1)} % ({p['label_persen']}{pita})"],
                  ["Berat isi beton basah", f"{angka(p['berat_isi_beton'], 0)} kg/m³ ({p['label_berat']})"]]
    else:
        baris += [["Volume agregat kasar (ACI)", f"{angka(p['vol_kasar'], 3)} m³"],
                  ["Massa beton segar (tabel ACI)", f"{angka(p['massa_beton'], 0)} kg/m³"]]
        a_ = bundle["adm"]
        if a_.aktif:
            baris += [["Admixture", a_.nama], ["Dosis / reduksi air", f"{angka(a_.dosis_pct, 2)} % berat semen / {angka(a_.reduksi_air_pct, 1)} %"]]
    return Tabel(["Parameter", "Nilai"], baris, lebar=[3, 4.2])


def _tabel_pemeriksaan(daftar: List[dict]) -> Tabel:
    return Tabel(["Parameter", "Nilai", "Batas", "Status"],
                 [[d["parameter"], d["nilai"], d["batas"] or "-", NAMA_TINGKAT[d["tingkat"]]] for d in daftar],
                 lebar=[3.0, 2.6, 1.9, 1.1])


def _tabel_langkah(hasil) -> Tabel:
    def nilai(v):
        return angka(v, 3 if abs(v) < 10 else 2) if isinstance(v, (int, float)) else str(v)
    return Tabel(["Uraian", "Nilai", "Satuan", "Tabel / grafik", "Rumus", "Substitusi"],
                 [[l.uraian, nilai(l.nilai), l.satuan, l.sumber, l.rumus, l.substitusi] for l in hasil.langkah],
                 lebar=[2.6, 1.0, 0.9, 2.4, 2.6, 3.0], rata_kanan=(1,))


def _seksi_penerimaan(pn: dict) -> Seksi:
    st_ = {"ok": "PASS", "warn": "WARNING", "error": "ERROR"}
    ind = Tabel(["No.", "Hasil uji (MPa)", "Batas individu (MPa)", "Status"],
                [[str(r["no"]), angka(r["nilai"], 1), angka(r["batas"], 1), "PASS" if r["lulus"] else "ERROR"] for r in pn["individu"]],
                judul="Hasil uji individu", lebar=[0.8, 1.6, 1.8, 1.2], rata_kanan=(0, 1, 2))
    tabel = [ind]
    if pn["rata3"]:
        tabel.append(Tabel(["Hasil uji ke-", "Rata-rata 3 berurutan (MPa)", "Batas f'c (MPa)", "Status"],
                           [[r["rentang"], angka(r["rata"], 1), angka(r["batas"], 1), "PASS" if r["lulus"] else "ERROR"] for r in pn["rata3"]],
                           judul="Rata-rata tiga hasil uji berurutan", lebar=[1.2, 2.2, 1.6, 1.2], rata_kanan=(1, 2)))
    return Seksi("Evaluasi Penerimaan Kuat Tekan Umur 28 Hari",
                 [f"Kriteria SNI 2847 / ACI 318: rata-rata tiga hasil uji berurutan >= f'c ({angka(pn['fc'], 1)} MPa) dan tidak ada hasil individu "
                  f"di bawah {angka(pn['batas_individu'], 1)} MPa. Status: {pn['status']}."], tabel)


def _seksi_prediksi(pr: dict) -> Seksi:
    baris = [["Umur pengujian", f"{pr['umur']} hari"], ["Jumlah benda uji", str(pr["jumlah"])],
             ["Kuat tekan rata-rata (setara silinder)", f"{angka(pr['rata'], 1)} MPa"]]
    baris += [[f"Prediksi 28 hari - {m}", f"{angka(v, 1)} MPa"] for m, v in pr["f28"].items()]
    baris += [["Prediksi 28 hari (rata-rata metode)", f"{angka(pr['rata28'], 1)} MPa"], ["Evaluasi", NAMA_TINGKAT[pr["tingkat"]]]]
    return Seksi("Prediksi Kuat Tekan 28 Hari dari Uji Umur Dini", [pr["pesan"]], [Tabel(["Parameter", "Nilai"], baris, lebar=[3.4, 2.6])])


def _kesimpulan(bundle: dict) -> Tuple[str, str, str]:
    daftar = bundle["pemeriksaan"]
    lv = tingkat_keseluruhan(daftar)
    label = {"ok": "MEMENUHI", "warn": "MEMENUHI DENGAN CATATAN", "error": "TIDAK MEMENUHI"}[lv]
    teks = (f"Berdasarkan hasil pengujian agregat dan perhitungan rancangan campuran sesuai {bundle['standar']}, "
            f"material dan rancangan campuran dinyatakan {label}.")
    if lv != "ok":
        teks += " Butir yang perlu perhatian: " + "; ".join(
            f"{d['parameter']} ({NAMA_TINGKAT[d['tingkat']]})" for d in daftar if d["tingkat"] in ("warn", "error")
            and d["parameter"] != "Catatan perhitungan") + "."
    return lv, label, teks


def _lengkapi(dok: Dokumen) -> Dokumen:
    dok.dicetak = tanggal_id(date.today())
    dok.kode_verifikasi = _kode(dok)
    return dok


# ----------------------------------------------------------------------------- pembangun dokumen
def siapkan_bundle(bundle: dict, lab: dict) -> dict:
    """Lengkapi bundle dengan daftar pemeriksaan mutu (dipakai UI dan dokumen)."""
    bundle["pemeriksaan"] = periksa_mutu(bundle["modul_sni"], bundle["hasil"], bundle["extra"], lab)
    return bundle


def _draft(kop: dict, dok: Dokumen) -> Dokumen:
    kosong = [n for n, k in (("Proyek", "proyek"), ("Penguji", "penguji")) if not str(kop.get(k, "")).strip()]
    dok.draft = bool(kosong)
    dok.pesan_draft = f"DRAFT - data belum lengkap ({', '.join(kosong)} masih kosong)" if kosong else ""
    return dok


def bangun_laporan(kop: dict, lab: dict, bundle: dict, prediksi: Optional[dict] = None, penerimaan: Optional[dict] = None) -> Dokumen:
    nomor = kop["no_dokumen"]
    lv, label, teks = _kesimpulan(bundle)
    seksi = [
        Seksi("A. Hasil Pengujian Agregat", ["Pengujian berat jenis, penyerapan air, kadar air, berat isi, dan lolos saringan No. 200 agregat."],
              [_tabel_agregat(lab)]),
        Seksi("B. Analisa Saringan Agregat Halus", [], [_tabel_saringan(lab["fine"], True)], _grafik(lab["fine"], "Kurva gradasi agregat halus")),
        Seksi("C. Analisa Saringan Agregat Kasar", [], [_tabel_saringan(lab["coarse"], False)], _grafik(lab["coarse"], "Kurva gradasi agregat kasar")),
        Seksi("D. Parameter dan Hasil Perencanaan Campuran Beton", [], [_tabel_parameter(bundle), _tabel_material(bundle)]),
        Seksi("E. Pemeriksaan Mutu", [], [_tabel_pemeriksaan(bundle["pemeriksaan"])]),
        Seksi("F. Rincian Langkah Perhitungan (Rumus dan Substitusi)", [], [_tabel_langkah(bundle["hasil"])]),
    ]
    if prediksi:
        seksi.append(_seksi_prediksi(prediksi))
    if penerimaan and penerimaan.get("n"):
        seksi.append(_seksi_penerimaan(penerimaan))
    dok = Dokumen("laporan", "LAPORAN PENGUJIAN AGREGAT DAN PERENCANAAN CAMPURAN BETON", f"Mix Design {bundle['standar']}", nomor, kop,
                  _meta(kop, bundle, nomor), seksi, (lv, label, teks),
                  ["Rancangan campuran bersifat teoritis; verifikasi dengan campuran percobaan (trial mix) dan uji kuat tekan umur 28 hari.",
                   "Laporan ini hanya berlaku untuk sampel yang diuji."], _penandatangan(kop))
    return _lengkapi(_draft(kop, dok))


def bangun_coa(kop: dict, lab: dict, bundle: dict) -> Dokumen:
    nomor = f"{kop['no_dokumen']}/CoA"
    lv, label, teks = _kesimpulan(bundle)
    acuan = ["SNI 1970:2016 (berat jenis & penyerapan agregat halus)", "SNI 1969:2016 (berat jenis & penyerapan agregat kasar)",
             "SNI ASTM C136:2012 (analisa saringan)", "SNI 03-4804-1998 (berat isi agregat)",
             "SNI 03-2834-2000 (perencanaan campuran beton normal)" if bundle["modul_sni"] else "ACI 211.1-91 (proporsi campuran beton normal)"]
    f, c = lab["fine"], lab["coarse"]
    ident = Tabel(["Material", "Sumber / nama", "Tanggal pengujian"],
                  [["Agregat halus (pasir)", f["nama"], tanggal_id(f["tanggal"])],
                   ["Agregat kasar (split/kerikil)", c["nama"], tanggal_id(c["tanggal"])]], lebar=[2.6, 3, 2])
    seksi = [
        Seksi("1. Identifikasi Material", [], [ident]),
        Seksi("2. Ringkasan Hasil Uji Agregat", [], [_tabel_agregat(lab)]),
        Seksi("3. Rancangan Campuran Beton", [], [_tabel_parameter(bundle), _tabel_material(bundle)]),
        Seksi("4. Pemeriksaan Mutu", [], [_tabel_pemeriksaan(bundle["pemeriksaan"])]),
        Seksi("5. Metode dan Standar Acuan", ["; ".join(acuan) + "."]),
    ]
    dok = Dokumen("coa", "SERTIFIKAT MUTU (CERTIFICATE OF ANALYSIS)", "Hasil Uji Agregat dan Rancangan Campuran Beton", nomor, kop,
                  _meta(kop, bundle, nomor), seksi, (lv, label, teks),
                  ["Sertifikat ini diterbitkan berdasarkan data pengujian laboratorium yang diinput dan berlaku untuk sampel yang diuji.",
                   "Rancangan campuran bersifat teoritis dan harus diverifikasi dengan campuran percobaan serta uji kuat tekan beton."],
                  _penandatangan(kop))
    return _lengkapi(_draft(kop, dok))
