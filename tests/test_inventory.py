"""D3: penyimpanan stok CSV, SQLite, dan Supabase (server tiruan PostgREST lokal)."""
import json
import os
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

import pytest

from utils import inventory as inv


def _uji_penyimpanan(p):
    s = inv.Stok(penyimpanan=p)
    s.tambah("Semen", "Masuk", 1000, "25 sak 40 kg", "nota 1")
    s.tambah("Semen", "Keluar", 300)
    assert s.sisa()["Semen"] == pytest.approx(700)
    with pytest.raises(ValueError):
        s.tambah("Semen", "Keluar", 5000)
    with pytest.raises(ValueError):                                   # atomik: tidak ada yang tercatat bila salah satu gagal
        s.tambah_banyak([dict(bahan="Semen", jenis="Keluar", jumlah_kg=100), dict(bahan="Split", jenis="Keluar", jumlah_kg=1)])
    assert s.sisa()["Semen"] == pytest.approx(700) and len(s.muat()) == 2
    s.simpan_ambang({"Semen": 123.0})
    assert s.ambang()["Semen"] == 123.0 and s.ambang()["Pasir"] == inv.AMBANG_BAWAAN["Pasir"]
    assert s.hapus_terakhir() and s.sisa()["Semen"] == pytest.approx(1000)
    assert s.hapus_terakhir() and s.hapus_terakhir() is False                     # buku besar kosong: tidak ada yang dihapus
    assert all(v == 0 for v in s.sisa().values())


def test_csv():
    _uji_penyimpanan(inv.PenyimpananCSV(tempfile.mkdtemp()))


def test_sqlite():
    _uji_penyimpanan(inv.PenyimpananSQLite(os.path.join(tempfile.mkdtemp(), "stok.db")))


class _Tiruan(BaseHTTPRequestHandler):
    stok, ambang = [], {}

    def log_message(self, *a):
        pass

    def _kirim(self, data, kode=200):
        isi = json.dumps(data).encode()
        self.send_response(kode); self.send_header("Content-Type", "application/json"); self.send_header("Content-Length", str(len(isi))); self.end_headers(); self.wfile.write(isi)

    def do_GET(self):
        u = urlparse(self.path); q = parse_qs(u.query)
        if u.path.endswith("stok_ambang"):
            return self._kirim([dict(bahan=b, nilai=v) for b, v in self.ambang.items()])
        rows = sorted(self.stok, key=lambda r: r["id"], reverse=q.get("order", [""])[0] == "id.desc")
        self._kirim(rows[:int(q["limit"][0])] if "limit" in q else rows)

    def do_POST(self):
        u = urlparse(self.path); data = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        if u.path.endswith("stok_ambang"):
            self.ambang.update({d["bahan"]: d["nilai"] for d in data})
        else:
            for d in data:
                self.stok.append({**d, "id": (max([r["id"] for r in self.stok]) + 1) if self.stok else 1})
        self._kirim([], 201)

    def do_DELETE(self):
        n = int(parse_qs(urlparse(self.path).query)["id"][0].split(".")[1])
        type(self).stok = [r for r in self.stok if r["id"] != n]
        self._kirim([], 204)


def test_supabase_dengan_server_tiruan():
    _Tiruan.stok, _Tiruan.ambang = [], {}
    srv = HTTPServer(("127.0.0.1", 0), _Tiruan)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        _uji_penyimpanan(inv.PenyimpananSupabase(f"http://127.0.0.1:{srv.server_port}", "kunci-uji", timeout=5))
    finally:
        srv.shutdown()


def test_pilihan_backend_dari_lingkungan():
    lama = {k: os.environ.get(k) for k in ("MIXDESIGN_STOK_BACKEND", "MIXDESIGN_STOK_DB", "SUPABASE_URL", "SUPABASE_KEY")}
    try:
        os.environ["MIXDESIGN_STOK_BACKEND"] = "sqlite"; os.environ["MIXDESIGN_STOK_DB"] = os.path.join(tempfile.mkdtemp(), "x.db")
        assert isinstance(inv.buat_penyimpanan(), inv.PenyimpananSQLite)
        os.environ["MIXDESIGN_STOK_BACKEND"] = "supabase"; os.environ.pop("SUPABASE_URL", None)
        with pytest.raises(RuntimeError):
            inv.buat_penyimpanan()
        os.environ["MIXDESIGN_STOK_BACKEND"] = "lainnya"
        with pytest.raises(ValueError):
            inv.buat_penyimpanan()
    finally:
        for k, v in lama.items():
            os.environ.pop(k, None) if v is None else os.environ.__setitem__(k, v)
